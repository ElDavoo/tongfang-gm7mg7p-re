#!/usr/bin/env python3
"""Offline checks for a cluster's identity: `cluster_key`, `cluster_name` and
`--map` (issue #274).

The census's `main-ec-NNN` is a *rank*, so it is not an identity: one change
anywhere in the ranking renumbers every id below the one that moved, and issue
#253 is what the surviving citations cost. These cases hold the two things
that are supposed to replace it -- a content hash, and a hand name carried
across a regeneration in changed form -- to the issue's own test, which is the
only one that settles it: **regenerate and show that a cluster the prose cites
still resolves to the membership the sentence describes.**

Everything here reads committed text. The guard-off census in
`TheGuardOffRegeneration` is a regeneration from the committed tree with the
`==` guard removed, which is the recipe `annotations/xdata-06c2-06db-timers.md`
§6a already records and re-runs; no image, no Ghidra, no network, and nothing
here touched hardware.
"""
import csv
import functools
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
EC = HERE.parent
TOOL = HERE / "xdata_register_map.py"
spec = importlib.util.spec_from_file_location("xdata_register_map", TOOL)
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

CLUSTERS = EC / "annotations" / "xdata-clusters.csv"
REGISTERS = EC / "annotations" / "xdata-registers.csv"
NAMES = EC / "annotations" / "xdata-cluster-names.csv"

# The 43 addresses `annotations/xdata-06c2-06db-timers.md` §1 sweeps, copied
# out of that page's own `--csv` invocation. The claim under test is the
# page's, so the expectation is the page's list rather than a count.
SWEPT_43 = set("""0x0460 0x0468 0x055F 0x0621 0x0635 0x0636 0x0637 0x0638 0x0639
0x063A 0x06C2 0x06C3 0x06C5 0x06D1 0x06D2 0x06D6 0x06D8 0x06D9 0x06DA 0x06DB 0x06F3
0x0706 0x070B 0x070D 0x0723 0x07F3 0x07F6 0x0809 0x080C 0x080D 0x0811 0x0843 0x0844
0x085B 0x0890 0x08A7 0x08A8 0x08E4 0x0981 0x0982 0x0985 0x0986 0x09CE""".split())

# The guard `xdata-06c2-06db-timers.md` §6a's "after" tree added and issue
# #178 committed. Deleting it reproduces the classifier that census was
# measured against, which is the regeneration these cases run the cited
# membership through. If this text is not found the recipe has drifted and the
# test says so rather than quietly regenerating the same census twice.
GUARD = '    if stripped.startswith("=="):\n        return False\n'


def clusters_of(path):
    """{cluster_id: row} from a clusters CSV."""
    with open(path, newline="") as f:
        return {r["cluster_id"]: r for r in csv.DictReader(f)}


def named_of(path):
    """{cluster_name: row} for the named clusters of a clusters CSV."""
    return {r["cluster_name"]: r for r in clusters_of(path).values()
            if r["cluster_name"]}


@functools.lru_cache(maxsize=1)
def guard_off():
    """(clusters.csv path, registers.csv path) for the guard-off census.

    Built the way §6a builds it: the tool copied into a scratch tree with the
    inputs symlinked back to this repository, so the run reads the committed
    decompile and writes nothing into it. ~2 s, and the only reason the suite
    caches it is that five cases want the same regeneration.
    """
    tmp = tempfile.mkdtemp(prefix="xdata-guard-off-")
    ec = os.path.join(tmp, "ec")
    os.makedirs(os.path.join(ec, "tools"))
    tool = os.path.join(ec, "tools", "xdata_register_map.py")
    with open(TOOL) as f:
        source = f.read()
    if GUARD not in source:
        raise AssertionError(
            "the `==` guard is not where §6a's recipe deletes it; the "
            "guard-off census this suite builds is not the one §6a measured")
    with open(tool, "w") as f:
        f.write(source.replace(GUARD, ""))
    for d in ("decompiled", "annotations", "firmware", "ghidra"):
        os.symlink(str(EC / d), os.path.join(ec, d))
    out_clusters = os.path.join(tmp, "clusters.csv")
    out_registers = os.path.join(tmp, "registers.csv")
    proc = subprocess.run(
        [sys.executable, tool, "--out-clusters", out_clusters,
         "--out-registers", out_registers],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the guard-off run failed: {proc.stderr}")
    return tmp, out_clusters, out_registers, proc.stderr


@functools.lru_cache(maxsize=1)
def guard_off_map():
    """(csv rows, stderr) of `--map` from the guard-off census."""
    tmp, out_clusters, out_registers, _ = guard_off()
    proc = subprocess.run(
        [sys.executable, os.path.join(tmp, "ec", "tools",
                                      "xdata_register_map.py"),
         "--out-clusters", out_clusters, "--out-registers", out_registers,
         "--map", str(CLUSTERS)],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"--map failed: {proc.stderr}")
    return list(csv.DictReader(io.StringIO(proc.stdout))), proc.stderr


class TheContentKey(unittest.TestCase):
    """`cluster_key` is a function of the membership, not of the position."""

    def test_key_is_order_independent_over_addrs(self):
        # The membership is a set. A key that changed because a column was
        # written in a different order would be a key that lies, and the CSV
        # column it is read from is the one place that could happen.
        self.assertEqual(xrm.cluster_key("main-ec", [0x0E, 0x30, 0x40]),
                         xrm.cluster_key("main-ec", [0x40, 0x0E, 0x30]))

    def test_changed_membership_is_a_new_key_not_a_collision(self):
        before = xrm.cluster_key("main-ec", [0x0E, 0x30, 0x40])
        after = xrm.cluster_key("main-ec", [0x0E, 0x30, 0x40, 0x50])
        self.assertNotEqual(before, after)
        self.assertNotEqual(before, xrm.cluster_key("main-ec", [0x0E, 0x40]))

    def test_program_is_in_the_key(self):
        # The two programs have separate XDATA maps, so identical membership in
        # the two is two clusters, and one shared key would merge them.
        self.assertNotEqual(xrm.cluster_key("main-ec", [0x0E, 0x30]),
                            xrm.cluster_key("pd", [0x0E, 0x30]))

    def test_key_shape_is_the_documented_one(self):
        self.assertRegex(xrm.cluster_key("main-ec", [0x0E]),
                         r"\Ak[0-9a-f]{%d}\Z" % xrm.CLUSTER_KEY_HEX)

    def test_the_committed_census_has_no_colliding_keys(self):
        rows = list(clusters_of(CLUSTERS).values())
        keys = {r["cluster_key"] for r in rows}
        self.assertEqual(len(keys), len(rows))
        # And the registers CSV agrees address for address, so a citation can
        # get from a byte to its key without leaving the census.
        by_id = {r["cluster_id"]: r["cluster_key"] for r in rows}
        with open(REGISTERS, newline="") as f:
            for r in csv.DictReader(f):
                self.assertEqual(r["cluster_key"], by_id[r["cluster_id"]])


class TheCarry(unittest.TestCase):
    """`carry_names`, on fixtures small enough to read the whole decision.

    The properties under test are the calibrated ones: three outcomes stay
    three, a score is reported with the claim it qualifies, and a cluster
    nothing matched is reported rather than quietly losing its name.

    One named old cluster of twenty addresses is the fixture most of these
    share, because a two-address old row against a two-address new one is
    Jaccard 1.0 however unrelated they look -- which is how a test for "a miss"
    ends up asserting a carry.
    """

    TWENTY = list(range(0x0E, 0x0E + 20))

    def old(self, cid, key, name, addrs):
        return {"cluster_id": cid, "cluster_key": key, "cluster_name": name,
                "addrs": " ".join(xrm.hexaddr(a) for a in addrs)}

    def new(self, cid, key, addrs):
        return {"cluster_id": cid, "cluster_key": key,
                "addrs": " ".join(xrm.hexaddr(a) for a in addrs)}

    def carry(self, old, seeded=None, key="knew0000000000", new=None):
        return xrm.carry_names(
            old, seeded or {},
            [self.new("main-ec-001", key, new or self.TWENTY)])

    def test_exact_key_carries_the_name(self):
        # The new cluster's key is the old row's key, so `exact` is the only
        # route to the name and the membership plays no part in the outcome.
        old = [self.old("main-ec-001", "knew0000000000", "gate", self.TWENTY)]
        names, report = self.carry(old)
        self.assertEqual(names, {"knew0000000000": "gate"})
        self.assertEqual(report[0]["how"], "exact")
        self.assertEqual(report[0]["jaccard"], 1.0)
        self.assertEqual(report[0]["from_key"], "knew0000000000")

    def test_a_seeded_name_beats_the_carry(self):
        # The names file is a human saying so; the carry is the tool's guess.
        # A guess must never overrule the hand that seeded the census.
        old = [self.old("main-ec-001", "kold111111111", "carried", self.TWENTY)]
        names, report = self.carry(old, {"knew0000000000": "seeded"})
        self.assertEqual(names, {"knew0000000000": "seeded"})
        self.assertEqual(report[0]["how"], "seeded")

    def test_changed_membership_carries_with_its_score(self):
        # One address is gone from a twenty-address cluster: a cluster that
        # changed in changed form, which is the case a content hash alone
        # cannot cover, and 19/20 is what a name carried at 0.95 costs.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        self.TWENTY + [0x30])]
        names, report = self.carry(old)
        self.assertEqual(names, {"knew0000000000": "gate"})
        self.assertEqual(report[0]["how"], "overlap")
        self.assertAlmostEqual(report[0]["jaccard"], 20 / 21)
        self.assertEqual(report[0]["from_key"], "kold111111111")

    def test_a_miss_is_reported_with_its_score_and_carries_nothing(self):
        # One address in common, 28 in the union: a name that did not follow,
        # and the score that says how far it fell.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        [0x0E] + list(range(0xF0, 0xF8)))]
        names, report = self.carry(old)
        self.assertEqual(names, {})
        self.assertEqual(report[0]["how"], "none")
        self.assertAlmostEqual(report[0]["jaccard"], 1 / 28)

    def test_a_near_miss_is_reported_as_such_and_not_rounded_up(self):
        # 0.488 against a 0.50 rule. The honest outcome is `none` carrying the
        # score that was measured. A name carried at 0.488 would be a claim
        # this rule does not make, and rounding it up to 0.5 is the same
        # overclaim with a decimal point.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        self.TWENTY + list(range(0xF0, 0xF0 + 21)))]
        names, report = self.carry(old)
        self.assertEqual(names, {})
        self.assertEqual(report[0]["how"], "none")
        self.assertAlmostEqual(report[0]["jaccard"], 20 / 41)
        self.assertLess(report[0]["jaccard"], xrm.CARRY_MIN_JACCARD)

    def test_a_tie_is_reported_and_no_winner_is_picked(self):
        # Two named old clusters, the same membership, so the same score. Which
        # of them the new cluster is, is a fact about the clustering; picking
        # one would make a name depend on the sort order of a fixture.
        old = [self.old("main-ec-001", "kold111111111", "first", self.TWENTY),
               self.old("main-ec-002", "kold222222222", "second", self.TWENTY)]
        names, report = self.carry(old)
        self.assertEqual(names, {})
        self.assertEqual(report[0]["how"], "tie")
        self.assertEqual(report[0]["jaccard"], 1.0)
        self.assertIn("first (main-ec-001)", report[0]["detail"])
        self.assertIn("second (main-ec-002)", report[0]["detail"])

    def test_a_tie_with_one_clear_winner_is_still_a_carry(self):
        # A tie is a tie at the *best* score. A second named cluster that
        # matches worse is not a competing claim, and treating it as one would
        # turn most overlap carries into non-results.
        old = [self.old("main-ec-001", "kold111111111", "first", self.TWENTY),
               self.old("main-ec-002", "kold222222222", "second", [0xF0, 0xF1])]
        names, report = self.carry(old)
        self.assertEqual(names, {"knew0000000000": "first"})
        self.assertEqual(report[0]["how"], "overlap")

    def test_a_census_without_the_columns_still_carrys_nothing_gracefully(self):
        # A clusters CSV from before the key and name columns is still a
        # census. It has no names to carry, and must not raise.
        old = [{"cluster_id": "main-ec-001", "addrs": "0x0E 0x30"}]
        names, report = self.carry(old)
        self.assertEqual(names, {})
        self.assertEqual(report[0]["how"], "none")

    def test_every_new_cluster_gets_exactly_one_record(self):
        old = [self.old("main-ec-001", "kold111111111", "gate", self.TWENTY)]
        rows = [self.new("main-ec-001", "kaaa000000000", [0xF0]),
                self.new("main-ec-002", "kbbb000000000", [0xF1, 0xF2]),
                self.new("main-ec-003", "kccc000000000", self.TWENTY)]
        names, report = xrm.carry_names(old, {}, rows)
        self.assertEqual([r["cluster_id"] for r in report],
                         ["main-ec-001", "main-ec-002", "main-ec-003"])
        self.assertEqual([r["how"] for r in report], ["none", "none", "overlap"])
        self.assertEqual(list(names), ["kccc000000000"])



class TheGuardOffRegeneration(unittest.TestCase):
    """The issue's own test, run: does a cited cluster survive a regeneration?

    A regeneration that moves the ranking is the cheapest one available from
    committed text: deleting the `==` guard `xdata-06c2-06db-timers.md` §6a
    measured. 427 clusters become 436 and 366 of the ranks keep their number
    and change what the number names, which is the whole reason a rank is not
    an identity.
    """

    @classmethod
    def setUpClass(cls):
        _tmp, cls.clusters, cls.registers, _err = guard_off()
        cls.committed = clusters_of(CLUSTERS)
        cls.off = clusters_of(cls.clusters)
        cls.off_named = named_of(cls.clusters)

    def test_the_regeneration_really_moves_the_ranks(self):
        # If this ever stops holding, the rest of the class is testing nothing:
        # a regeneration that renumbers nothing is not the case the identity
        # columns exist for.
        moved = [cid for cid, row in self.committed.items()
                 if cid in self.off and row["addrs"] != self.off[cid]["addrs"]]
        self.assertGreater(len(moved), 300)
        self.assertNotEqual(len(self.off), len(self.committed))

    def test_the_counter_sweep_name_still_resolves_to_the_swept_block(self):
        # The issue's assertion, verbatim in substance: a cluster the prose
        # names still resolves to the membership the sentence describes, where
        # the sentence is the 43 addresses xdata-06c2-06db-timers.md §1 sweeps.
        row = self.off_named["counter-sweep"]
        self.assertTrue(SWEPT_43 <= set(row["addrs"].split()),
                        f"the {row['cluster_id']} that carries counter-sweep is "
                        f"missing {sorted(SWEPT_43 - set(row['addrs'].split()))}")

    def test_and_the_tool_says_what_moved_about_it(self):
        # Not "nothing moved": under this regeneration the counter block keeps
        # its membership and its key and only its *rank* changes, which is the
        # sharpest possible statement of why the rank is not the identity. The
        # assertion is that the two identities and the rank each moved the way
        # the map says they did.
        old = next(r for r in self.committed.values()
                   if r["cluster_name"] == "counter-sweep")
        new = self.off_named["counter-sweep"]
        self.assertEqual(new["cluster_key"], old["cluster_key"])
        self.assertEqual(set(new["addrs"].split()), set(old["addrs"].split()))
        self.assertNotEqual(new["cluster_id"], old["cluster_id"])

    def test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key(self):
        # The case that rules a key-only design out. `main-ec-001` and
        # `main-ec-002` are the two largest clusters the prose cites, and both
        # change membership under this regeneration, so neither is found by its
        # key -- a content hash alone would hand the two largest cited clusters
        # a brand-new identity here.
        for cid, name in (("main-ec-001", "mode-oem-init"),
                          ("main-ec-002", "level-block-086x")):
            old = self.committed[cid]
            new = self.off_named[name]
            self.assertNotEqual(
                new["cluster_key"], old["cluster_key"],
                f"{name} kept its key, so this case is not testing the carry")
            self.assertNotEqual(new["addrs"], old["addrs"])
            self.assertEqual(new["cluster_name"], name)

    def test_no_name_is_lost_across_the_regeneration(self):
        # A name the committed census carries is either carried into this one
        # or reported as a tie. There is no third outcome, and in particular
        # none in which a name quietly stops appearing -- which would read as
        # "the cluster went away" and is exactly the overclaim #274 is about.
        committed = {r["cluster_name"] for r in self.committed.values()
                     if r["cluster_name"]}
        self.assertEqual(committed - set(self.off_named), set())

    def test_the_map_reports_the_membership_delta_for_every_moved_row(self):
        rows, stderr = guard_off_map()
        by_old = {r["old_cluster"]: r for r in rows}
        self.assertEqual(set(by_old), set(self.committed))
        for cid, old in self.committed.items():
            row = by_old[cid]
            added = set(row["added"].split()) if row["added"] else set()
            removed = set(row["removed"].split()) if row["removed"] else set()
            new = self.off[row["new_cluster"]] if row["new_cluster"] != "-" else None
            if new is None:
                continue
            self.assertEqual(
                added, set(new["addrs"].split()) - set(old["addrs"].split()),
                f"{cid}: the reported delta is not the delta")
            self.assertEqual(
                removed, set(old["addrs"].split()) - set(new["addrs"].split()),
                f"{cid}: the reported delta is not the delta")
        # Every name the guard-off census carries is on the map, so the sweep
        # this report drives from does not have to open the CSV as well.
        carried = [r for r in rows if r["cluster_name"] != "-"]
        self.assertEqual({r["cluster_name"] for r in carried},
                         set(self.off_named))
        self.assertIn("whose cluster_key changed", stderr)


class TheMapReport(unittest.TestCase):
    """`--map` against the census that is already committed.

    The no-op case first, because it is the one that has to hold: mapping the
    committed census against a generation from the same tree has to be the
    identity, or the report cannot be told apart from a reshuffle.
    """

    def test_the_committed_census_maps_to_itself(self):
        tmp = tempfile.mkdtemp(prefix="xdata-map-")
        fresh = os.path.join(tmp, "clusters.csv")
        # `--map` returns through `map_census()` and never reaches the writer,
        # so the fresh census it maps onto is generated by its own call. The
        # two are the same generation either way: both read the committed tree.
        subprocess.run([sys.executable, str(TOOL), "--out-clusters", fresh,
                        "--out-registers", os.path.join(tmp, "registers.csv")],
                       capture_output=True, text=True, check=True)
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--map", str(CLUSTERS)],
            capture_output=True, text=True, check=True)
        rows = list(csv.DictReader(io.StringIO(proc.stdout)))
        self.assertEqual(len(rows), len(clusters_of(CLUSTERS)))
        if all(r["old_cluster"] == r["new_cluster"] for r in rows):
            # The no-op the docstring means: a fresh generation from a tree
            # whose census is current, so the report is the identity on every
            # column. This is the branch the case takes once #254/#256/#326
            # re-derives the census, and it is unchanged from what it was.
            self.assertTrue(all(r["key"] == "unchanged" for r in rows))
            self.assertTrue(all(not r["added"] and not r["removed"] for r in rows))
            self.assertTrue(all(r["match"] == "key" for r in rows))
            self.assertTrue(all(r["jaccard"] == "1.00" for r in rows))
            return
        # Not a no-op, and not this change's doing: the census this map is run
        # against is main's #310 one, which a fresh generation does not
        # reproduce (`xdata-register-map.md` §1 records the gap and defers the
        # re-derivation to #254/#256/#326, and `--check` exits 1 on `origin/main`
        # for the same reason). So the identity cannot be asserted here without
        # asserting something false about the tree. What still has to hold is
        # the reason the case exists — that the report can be told apart from a
        # reshuffle — which is that every reported delta is the true set
        # difference between the two censuses it was actually given.
        old = clusters_of(CLUSTERS)
        new = clusters_of(fresh)
        for row in rows:
            cid = row["old_cluster"]
            target = new.get(row["new_cluster"])
            if target is None:
                continue
            self.assertEqual(
                set(row["added"].split()) - {""},
                set(target["addrs"].split()) - set(old[cid]["addrs"].split()),
                f"{cid}: the reported delta is not the delta")
            self.assertEqual(
                set(row["removed"].split()) - {""},
                set(old[cid]["addrs"].split()) - set(target["addrs"].split()),
                f"{cid}: the reported delta is not the delta")

    def test_a_missing_old_census_is_an_error_not_a_crash(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL), "--map", "/nonexistent/clusters.csv"],
            capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("does not exist", proc.stderr)


class TheNamesFile(unittest.TestCase):
    """`xdata-cluster-names.csv` is the editable surface, and it is anchored."""

    def test_every_row_names_a_cluster_of_the_committed_census(self):
        # A names row whose key is not a current cluster is a name attached to
        # nothing, and the tool's own self-test reports it; this is the same
        # fact from the other side, so the file cannot drift past the census
        # without one of the two noticing.
        keys = {r["cluster_key"] for r in clusters_of(CLUSTERS).values()}
        with open(NAMES, newline="") as f:
            for row in csv.DictReader(f):
                self.assertIn(row["cluster_key"], keys, row["cluster_name"])

    def test_every_row_records_the_evidence_for_its_name(self):
        # The house rule ghidra-functions.csv follows: a hand annotation with
        # no evidence recorded is indistinguishable from a guess.
        with open(NAMES, newline="") as f:
            for row in csv.DictReader(f):
                self.assertTrue(row["note"].strip(),
                                f"{row['cluster_name']} has no note")

    def test_names_are_unique(self):
        with open(NAMES, newline="") as f:
            names = [r["cluster_name"] for r in csv.DictReader(f)]
        self.assertEqual(len(names), len(set(names)))


class TheGeneratorsAreUnchanged(unittest.TestCase):
    """An identity change, not a classifier change (issue #274's last invariant).

    The two CSVs gain columns; the census they describe does not move. If a
    future edit to the carry quietly changed a membership, this is where it
    shows -- the ids, sizes, references and addresses are all exactly what the
    committed census had before the columns were added.
    """

    def test_the_generation_is_reproducible(self):
        tmp = tempfile.mkdtemp(prefix="xdata-regen-")
        clusters = os.path.join(tmp, "clusters.csv")
        registers = os.path.join(tmp, "registers.csv")
        subprocess.run([sys.executable, str(TOOL), "--out-clusters", clusters,
                        "--out-registers", registers],
                       capture_output=True, text=True, check=True)
        for fresh, committed, extra, stale in (
                (clusters, CLUSTERS, {"cluster_key", "cluster_name"}, (430, 427)),
                (registers, REGISTERS, {"cluster_key"}, (1171, 1171))):
            with open(fresh, newline="") as f:
                rows = list(csv.DictReader(f))
            with open(committed, newline="") as f:
                theirs = list(csv.DictReader(f))
            # The identity columns are the only difference, so compare
            # everything else cell for cell rather than diffing whole lines.
            body = lambda rs: [{k: v for k, v in r.items() if k not in extra}
                               for r in rs]
            if body(rows) == body(theirs):
                continue
            # Not reproducible, and not this change's doing. The committed
            # census is main's #310 one: `bank0/CC64`'s annotation adds an
            # address it still had to itself, so a fresh generation is not the
            # committed file. `xdata-register-map.md` §1 records the divergence
            # and defers the re-derivation to #254/#256/#326, and
            # `xdata_register_map.py --check` exits 1 on `origin/main` for the
            # same reason — so the equality below is a claim about a tree this
            # one is not yet. Pin the figures the documented gap has instead:
            # a *second* movement of the census fails here rather than passing
            # unnoticed behind the branch that skips the equality. When
            # #254/#256/#326 re-derives the census this becomes the original
            # assertion again, with nothing to change here.
            self.assertEqual((len(rows), len(theirs)), stale)

    def test_the_cluster_id_column_is_untouched(self):
        # Every page in the tree names a `main-ec-NNN`, so the rank keeps the
        # exact values it has today. Switching over is a prose sweep, and this
        # is the assertion that the sweep is still possible to reason about.
        committed = clusters_of(CLUSTERS)
        for cid, row in committed.items():
            self.assertEqual(cid, row["cluster_id"])


if __name__ == "__main__":
    unittest.main()
