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
`TheGuardOffRegeneration` and `TheGuardOffKeyDistinctness` is a regeneration
from the committed tree with the `==` rejection off, via `--no-eq-guard`, which
is the flag `annotations/xdata-06c2-06db-timers.md` §6a already re-runs; no
image, no Ghidra, no network, and nothing here touched hardware.
"""
import collections
import csv
import functools
import importlib.util
import io
import os
from pathlib import Path
import re
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

# The second tool, for `duplicate_keys()` and nothing else: that is the
# predicate every `cluster_key unique ... / COLLISION` line in a report is
# printed from. Sharing it is the point rather than a convenience -- a suite
# checking its own re-derived `len()` compare would be testing something the
# report does not print, and the two could only agree by accident.
_moved_spec = importlib.util.spec_from_file_location(
    "xdata_moved_ranks", HERE / "xdata_moved_ranks.py")
ranks = importlib.util.module_from_spec(_moved_spec)
_moved_spec.loader.exec_module(ranks)

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


def clusters_of(path):
    """{cluster_id: row} from a clusters CSV."""
    with open(path, newline="") as f:
        return {r["cluster_id"]: r for r in csv.DictReader(f)}


def named_of(path):
    """{cluster_name: row} for the named clusters of a clusters CSV."""
    return {r["cluster_name"]: r for r in clusters_of(path).values()
            if r["cluster_name"]}


def registers_of(path):
    """{addr: row} from a per-address registers CSV."""
    with open(path, newline="") as f:
        return {r["addr"]: r for r in csv.DictReader(f)}


@functools.lru_cache(maxsize=1)
def guard_off():
    """(tmp dir, clusters.csv path, registers.csv path, stderr) for the
    guard-off census.

    Built the way §6a builds it: the committed tool run with `--no-eq-guard`,
    which is the switch that "re-runs the census with the `==` rejection turned
    off" (`xdata_register_map.py:4481`) and the mechanism that page re-runs its
    figures from. The flag refuses to be given the committed output paths, so
    both CSVs go to a scratch directory the tool is pointed at by name and the
    run reads the committed decompile and writes nothing into it. ~2 s, and the
    only reason the suite caches it is that every class here that wants a
    second census wants *this* one: `TheGuardOffRegeneration`,
    `TheGuardOffKeyDistinctness`, `TheKeyIsTheHashOfItsRow`. The number of
    cases was named here and is not named now, for the reason `CLAUDE.md`
    gives: a count of this file's own cases is a value every merge that adds
    one has to edit, so the total is deleted rather than updated and the
    classes are named in its place.

    Correction, 2026-10-04 (issue #1128): the `--no-eq-guard` citation read
    `xdata_register_map.py:263`, which is `--map`'s docstring on `cluster_id`,
    so the sentence pointed a re-deriver of §6a at a paragraph that never
    declared the flag. It is `ap.add_argument("--no-eq-guard", ...)` at `:4481`;
    the quoted phrase is the tool's own module docstring at `:289`, which is
    where the wording comes from and not what the citation is for. Held by
    `ec/tools/check_py_citations.py`.
    """
    tmp = tempfile.mkdtemp(prefix="xdata-guard-off-")
    out_clusters = os.path.join(tmp, "clusters.csv")
    out_registers = os.path.join(tmp, "registers.csv")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--no-eq-guard", "--out-clusters",
         out_clusters, "--out-registers", out_registers],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the guard-off run failed: {proc.stderr}")
    return tmp, out_clusters, out_registers, proc.stderr


@functools.lru_cache(maxsize=1)
def guard_off_map():
    """(csv rows, stderr) of `--map` from the guard-off census."""
    _tmp, out_clusters, out_registers, _ = guard_off()
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--no-eq-guard", "--out-clusters",
         out_clusters, "--out-registers", out_registers, "--map", str(CLUSTERS)],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"--map failed: {proc.stderr}")
    return list(csv.DictReader(io.StringIO(proc.stdout))), proc.stderr


@functools.lru_cache(maxsize=1)
def export_ownership_census():
    """(tmp dir, clusters.csv path, registers.csv path, stdout) for the
    de-duplicated census.

    Built the way §6b builds it: the committed tool run with
    `--export-ownership`, which reads each routine once from the export that
    owns it, so bank1:0x8001's 42 overlapping exports are not counted 42
    times. Both of that flag's refusals apply here as they do to `guard_off()`
    above — refused with `--check` and `--self-test`, and refused without
    scratch outputs, which is why both `--out-` paths go to a temp dir rather
    than the committed pair. ~1 s, and the only reason this is cached rather
    than built per case is that two cases want the same regeneration.

    The last slot is **stdout**, where `guard_off()` returns stderr: §6b's
    per-program totals are printed on stdout, and the only thing worth
    checking them against is the CSV this same run wrote.
    """
    tmp = tempfile.mkdtemp(prefix="xdata-export-ownership-")
    out_clusters = os.path.join(tmp, "clusters.csv")
    out_registers = os.path.join(tmp, "registers.csv")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--export-ownership", "--out-clusters",
         out_clusters, "--out-registers", out_registers],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(f"the export-ownership run failed: {proc.stderr}")
    return tmp, out_clusters, out_registers, proc.stdout


class TheContentKey(unittest.TestCase):
    """`cluster_key` is a function of the membership, not of the position.

    **The coverage split, because "the census" is two of the four censuses a
    view can re-key.** This class holds the *committed* pair: the
    `annotations/xdata-clusters.csv` read off disk, and the key on every
    register row read back out of it, in
    `test_the_committed_census_has_no_colliding_keys`. With the two `check()`s
    inside `xdata_register_map.py`'s `self_test()` it also holds a fresh
    **guard-on** generation -- the tool's own, over the tree it just read.
    `TheGuardOffKeyDistinctness` adds the **guard-off** regeneration, which
    neither of those can be pointed at: `--no-eq-guard` is refused together
    with `--check` and `--self-test`, and refused without scratch outputs.

    The fourth census is held by none of this and is named here so that no
    reader counts four: the 430-row pair at `e169a0e4`, whose committed census
    and whose guard-off regeneration both need that commit's decompiled tree,
    which no case in this suite has. Its two rows of
    `docs/findings/xdata-guard-off-key-distinctness.md` §4 are hand-measured
    transcripts, and a re-derivation of them is a human's job.
    """

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
    committed text: the `==` rejection turned off with `--no-eq-guard`, which is
    the switch `xdata-06c2-06db-timers.md` §6a measured. 427 clusters become
    439, 48 of the ranks survive intact and 379 keep their number and change
    what the number names, which is the whole reason a rank is not an identity.

    Those three figures are issue #274's, measured against the census as it
    stood then, and they are kept as the record they are. The committed census
    has since been re-derived twice -- `xdata-register-map.md` §1's second
    correction, and then #279's, whose §6a re-derivation is the one that took
    it to 439 clusters over 1,326 register rows -- so the same regeneration
    over the census in the tree now gives 439 → 445 with 124 ranks intact and
    315 changed. The pair between the two, 430 → 439 with 64 intact and 366
    changed, was current when this docstring was last written and is no longer
    so, for the same reason this is being corrected in place rather than
    edited out: a total pasted into a file is a snapshot of the merge it was
    measured on, and the tree moved under two of them. Nothing below depends
    on any of the three; what depends on them is the prose, and that is where
    the figures are recorded. The fall from the middle pair to the last one is
    measured, with the cluster ids named, in
    `docs/findings/xdata-moved-ranks-fall.md` -- which is also where the floor
    `test_the_regeneration_really_moves_the_ranks` holds is argued from that
    measurement rather than from its headroom. §6a is the exception: it is a
    measurement rather than a description; `test_the_census_is_the_one_6a_measured`
    holds the relations it rests on, and its figures are what it measured.

    Which of the three is the set this class runs on is the last, and it is
    worth saying plainly: 439 → 445 is what the tree this suite is committed in
    gives, and a reader who took either older pair for the current reading
    would go looking for a total the class does not compute. The assertions are
    threshold-based for the same reason -- `> 300` moved ranks, and §6a's
    figures held to §6a rather than to a rank count here -- so a re-derivation
    moves all three of these without turning the class red.
    """

    @classmethod
    def setUpClass(cls):
        _tmp, cls.clusters, cls.registers, _err = guard_off()
        cls.committed = clusters_of(CLUSTERS)
        cls.off = clusters_of(cls.clusters)
        cls.off_named = named_of(cls.clusters)

    def test_the_census_is_the_one_6a_measured(self):
        # §6a's claim, held as the relations it rests on rather than as the
        # figures it printed (2026-10-04); the name is kept because write-ups
        # cite the case by it. This case used to pin every §6a
        # figure -- the 834, the 211 of 1,326, the four per-arm pairs and their
        # denominators, the 394/389 and 51/50 cluster pairs -- so that it went
        # red whenever the census moved. Seeding one routine moves it: #1849
        # turned the 834 into 840. CLAUDE.md's rule for the XDATA census is that
        # no figure of it goes back into a test; the figures stay in §6a as
        # what it measured, and `check_census_figures.py --print` prints them
        # for any tree. What is true of every tree is held here.
        off = registers_of(self.registers)
        on = registers_of(REGISTERS)
        # One address universe: the two runs differ by a flag, not by input.
        self.assertEqual(set(off), set(on))

        # The guard can only lift a rejection, so lifting it adds `==`
        # occurrences the pre-#178 classifier counted as stores and cannot take
        # one away. A net delta cannot tell "N arrived, none left" from "more
        # arrived and some left"; the per-address sign can.
        decreased = {a: (int(on[a]["write"]), int(off[a]["write"]))
                     for a in on if int(off[a]["write"]) < int(on[a]["write"])}
        self.assertEqual(
            decreased, {},
            f"§6a: {len(decreased)} address(es) have a lower `write` under "
            f"--no-eq-guard, which the guard's own removal of the `==` "
            f"rejection cannot cause")
        self.assertTrue(any(off[a]["write"] != on[a]["write"] for a in on),
                        "the guard-off run moved no reference into `write`, "
                        "so this case is no longer about the guard")

        # The load-bearing half of §6a: the guard moves references between
        # direction buckets and out of none of them, which is what makes every
        # row of §2a's 43-address table guard-invariant.
        moved_refs = sorted(a for a in on if off[a]["refs"] != on[a]["refs"])
        self.assertEqual(moved_refs, [],
                         "§6a: the guard-off run changed `refs` for these "
                         "addresses, so it moved something other than a "
                         "direction")

        # `program` partitions the rows, and each arm's denominators are the
        # same on both sides of the flag; the per-arm deltas are the terms of
        # the total, so a column that stopped partitioning shows up here.
        arms = ("main-ec", "pd", "both")
        self.assertEqual({r["program"] for r in on.values()}, set(arms))
        for program in arms:
            with self.subTest(program=program):
                denominators = [
                    (len(arm), sum(int(r["refs"]) for r in arm))
                    for rows in (off, on)
                    for arm in [[r for r in rows.values()
                                 if r["program"] == program]]]
                self.assertEqual(denominators[0], denominators[1])
        deltas = [sum(int(off[a]["write"]) - int(on[a]["write"]) for a in off
                      if off[a]["program"] == program)
                  for program in arms]
        self.assertEqual(
            sum(deltas),
            sum(int(off[a]["write"]) - int(on[a]["write"]) for a in off))

        # The renumbering the rest of this class is about exists because the
        # guard-off census sorts a different set of main-EC clusters ahead of
        # the committed one. Held as "the two censuses differ", not as the
        # 394/389 pair §6a printed.
        def per_program(clusters):
            return {p: sum(1 for r in clusters.values() if r["program"] == p)
                    for p in ("main-ec", "pd")}
        self.assertNotEqual(per_program(self.off), per_program(self.committed))

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
        # Not "nothing moved": under this regeneration a named cluster keeps
        # its membership and its key and only its *rank* changes, which is the
        # sharpest possible statement of why the rank is not the identity. The
        # assertion is that the two identities and the rank each moved the way
        # the map says they did — over the named clusters rather than over one
        # of them, because *which* name demonstrates it is a property of the
        # ranking and not of the design. `counter-sweep` was the exhibit when
        # this was written (it was `main-ec-003` in the census then, and moved);
        # the 2026-09-24 re-derivation had already put it at `main-ec-002`,
        # which is where the guard-off census leaves it, so it no longer moves
        # and is a weaker exhibit rather than a wrong one. If a future
        # regeneration leaves every named rank standing, this fails, which is
        # the same guard `test_the_regeneration_really_moves_the_ranks` puts on
        # the whole census.
        #
        # The margin, since "weaker" is doing a lot of work in that sentence:
        # **three** of the nine names move rank with key and membership intact
        # — `countdown-06c6`, `fan-step-08a0`, `flag-pair-0442` — and
        # `counter-sweep` is not one of them, which the derivation settles
        # without a count of anything:
        # `docs/findings/xdata-cluster-names-guard-off-recipe.md:258-268` reads
        # `counter-sweep` `main-ec-003` in the committed column and in the
        # guard-off one with `same same same`, and closes with `movers: 3 of 9`
        # naming the three. It is at `main-ec-003` in both censuses now; the
        # `main-ec-002` the paragraph above leaves it at is itself a superseded
        # reading, kept here rather than edited out for the same reason. What
        # the cluster *is* is a question a file answers and a tally does not:
        # `main-ec-003` is `counter-sweep` in the committed census —
        # `ec/annotations/xdata-clusters.csv`, `cluster_name=counter-sweep` at
        # `cluster_key=k733222e83898`, 43 addresses — and
        # `ec/annotations/xdata-06c2-06db-timers.md` is the page that makes a
        # membership claim about that block, §1 sweeping exactly those 43. A
        # most-cited-cluster count stood in this comment until 2026-09-28: it
        # quoted one `grep` and two figures the `grep` does not give, taken
        # over two different file sets, and neither figure survives the next
        # merge. The retraction and the measurement are in
        # `docs/findings/xdata-most-cited-cluster-count.md`. So the exhibit
        # this case fell back on is the one the ranking happens to spare. The
        # assertion stays `assertTrue(movers, …)`
        # on purpose: pinning the count would be the hazard this class's own
        # docstring exists to record — a total pasted into a file is a snapshot
        # of the merge it was measured on — and it would go red on any
        # re-derivation for a reason that says nothing about the design being
        # argued here. The mover set is derived in
        # `docs/findings/xdata-cluster-names-guard-off-recipe.md`, which prints
        # both the script and the transcript; the floor this case does hold is
        # the census-wide one in `test_the_regeneration_really_moves_the_ranks`.
        old_by_name = {r["cluster_name"]: r for r in self.committed.values()
                       if r["cluster_name"]}
        movers = sorted(
            name for name, new in self.off_named.items()
            if name in old_by_name
            and new["cluster_key"] == old_by_name[name]["cluster_key"]
            and set(new["addrs"].split()) == set(old_by_name[name]["addrs"].split())
            and new["cluster_id"] != old_by_name[name]["cluster_id"])
        self.assertTrue(
            movers,
            "no named cluster kept its membership and its key while its rank "
            "moved, so nothing here shows that a rank is not an identity: "
            f"committed names {sorted(old_by_name)}, guard-off names "
            f"{sorted(self.off_named)}")

    def test_every_name_the_key_cannot_find_is_carried_by_overlap(self):
        # The case that rules a key-only design out, over every name the key
        # fails to find rather than over two of them picked in advance. The
        # exhibits are the tool's own carry report, so `how == "overlap"` is by
        # construction "a named committed row whose key did not match this one
        # and whose membership did" -- which is the whole claim. A content hash
        # alone hands each of these a brand-new identity, and only the overlap
        # score brings the name along.
        #
        # Derived rather than typed, because a typed pair goes stale silently
        # and this one did. #279's pair-accessor pass (`6bf9c234`) moved
        # `mode-oem-init` to `main-ec-002` and `level-block-086x` to
        # `main-ec-004`, and the case went on comparing `main-ec-001` against
        # `main-ec-002` and passing -- over two *disjoint* clusters, Jaccard
        # 0.0000 between them. `assertNotEqual` on two cluster keys is true of
        # any two distinct clusters, so it could not fail for the reason the
        # name claimed: it compared the largest cluster in the census, which
        # carries no name at all, against an unrelated one. Nothing here reads
        # an id or a name, so the next re-key moves the exhibits rather than
        # breaking them. The measured set -- one name, `mode-oem-init` at
        # Jaccard 0.9681, out of the 445 clusters the run above generated -- is
        # prose in `docs/findings/xdata-two-largest-case-restatement.md` and
        # stays prose: `assertEqual(len(carried), 1)` would go red on any
        # re-derivation for a reason that says nothing about the design being
        # argued here, the hazard `assertTrue(movers, ...)` already avoids one
        # case up.
        #
        # `carry_names` reads the committed census as `old_rows` and returns one
        # record per row of `new_rows`, so this reads the tool's own decision
        # rather than a second implementation of it, and it does not write back
        # -- `self.off` is untouched for the cases after this one.
        _names, report = xrm.carry_names(
            list(self.committed.values()), {}, list(self.off.values()))
        carried = [r for r in report if r["how"] == "overlap"]
        committed_named = {r["cluster_name"] for r in self.committed.values()
                           if r["cluster_name"]}
        self.assertTrue(
            carried,
            "no committed name reached the guard-off census on membership "
            "overlap, so nothing here shows a cluster_key is not a sufficient "
            f"identity: {len(committed_named)} committed names "
            f"{sorted(committed_named)}, {len(self.off_named)} in the "
            "guard-off census, and none of them cleared "
            f"{xrm.CARRY_MIN_JACCARD} against a cluster whose key had changed")
        by_key = {r["cluster_key"]: r for r in self.committed.values()}
        for record in carried:
            with self.subTest(cluster=record["cluster_id"]):
                # The rule, stated once: a key alone would not have found it.
                # `exact` records carry `from_key == cluster_key` by
                # construction, so a set that admitted one fails here.
                self.assertNotEqual(
                    record["from_key"], record["cluster_key"],
                    f"{record['name']} was found by its key, so it is not one "
                    "of the clusters a content hash alone would have lost")
                self.assertGreaterEqual(
                    record["jaccard"], xrm.CARRY_MIN_JACCARD,
                    f"{record['name']} is recorded as an overlap at "
                    f"{record['jaccard']}, below the {xrm.CARRY_MIN_JACCARD} "
                    "the tool applies")
                # And the two things that make the record a fact about *this*
                # census rather than a plausible-looking dict: the guard-off row
                # carries the name, and the key it was carried from resolves to
                # a committed row carrying the same one.
                self.assertEqual(
                    self.off[record["cluster_id"]]["cluster_name"],
                    record["name"],
                    f"{record['cluster_id']} does not carry the name the carry "
                    "report carried into it")
                self.assertEqual(
                    by_key[record["from_key"]]["cluster_name"], record["name"],
                    f"{record['name']} was carried from committed key "
                    f"{record['from_key']}, whose row carries another name")

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
        # this report drives from does not have to open the CSV as well. Two
        # sets and not two lists, and the difference is not cosmetic: the map
        # carries a name on 10 rows over 9 distinct names, because
        # `mode-oem-init` arrives on two of them -- the two old clusters the
        # guard-off generation merged into the new `main-ec-002` are both its
        # sources. A reader who "fixes" this to compare counts turns the case
        # red over a correct report, so the merge is named here instead.
        carried = [r for r in rows if r["cluster_name"] != "-"]
        self.assertEqual({r["cluster_name"] for r in carried},
                         set(self.off_named))
        self.assertIn("whose cluster_key changed", stderr)


class TheExportOwnershipClusters(unittest.TestCase):
    """§6b's per-program cluster counts: a split that was held only as a total.

    `OWNERSHIP["clusters"]` held the 440 that `--export-ownership` produces
    and `--self-test` asserts it against an after-census built in-process
    (`xdata_register_map.py:3794-3797`), so five clusters moving from one program
    to the other left every assertion in the tree green and both lines of
    §6b's console block wrong at once. A *separate* class rather than another
    case in `TheGuardOffRegeneration`, for two reasons: it is a different
    flag's census, so the two regenerations are not the same measurement and
    one class would read as though they were; and `docs/findings.md` §50 calls
    the other class's seventh case "a seventh case", so an eighth there would
    falsify a sentence this change did not set out to touch.

    Correction, 2026-10-04 (issue #1128): this citation read
    `xdata_register_map.py:4347`, which was the after-census build then and is
    now `print_carry()`'s stderr tail -- a right citation that decayed like any
    other, which is why it is held rather than merely re-pointed. It is
    `own_map = load_ownership()` at `:3794` and the `scan()` call under it. Held
    by `ec/tools/check_py_citations.py`.
    """

    @classmethod
    def setUpClass(cls):
        _tmp, cls.clusters, _registers, cls.stdout = export_ownership_census()
        cls.rows = list(clusters_of(cls.clusters).values())

    def test_the_clusters_split_by_program_and_never_span_one(self):
        # The split itself is not pinned: every seeded routine moves it. What
        # holds at any size is that each cluster row belongs to exactly one of
        # the two programs and that both programs are present.
        counts = collections.Counter(r["program"] for r in self.rows)
        self.assertEqual(set(counts), {"main-ec", "pd"},
                         f"cluster rows by program: {dict(counts)}")

    def test_the_console_block_agrees_with_the_csv_it_wrote(self):
        # §6b's block is a transcript, and the correction at `:917-931` exists
        # because a transcript there once carried ids and counts from two
        # different runs. The two cluster figures it prints are this run's own
        # stdout, so they can be read back against the CSV the same run wrote
        # -- which is the only way a half-renumbered transcript is caught
        # rather than believed, and the reason the numbers above are not
        # simply restated here.
        printed = {program: int(n) for program, n in re.findall(
            r"^\s*(\S+): \d+ distinct addresses, \d+ references, (\d+) clusters"
            r" at threshold", self.stdout, re.M)}
        self.assertEqual(
            printed, dict(collections.Counter(r["program"] for r in self.rows)),
            "§6b's console block: the two 'N clusters at threshold 0.5' figures "
            f"the run printed are {printed}, and the clusters CSV that run "
            f"wrote splits {dict(collections.Counter(r['program'] for r in self.rows))}")


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
                # 430, not the 427 of the census #274 was written against: the
                # 2026-09-24 re-derivation committed the fresh generation, so
                # both censuses are 430 rows now and this pair is the net for
                # a further movement rather than a record of the old one.
                (clusters, CLUSTERS, {"cluster_key", "cluster_name"}, (430, 430)),
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
            # census used to be main's #310 one: `bank0/CC64`'s annotation adds
            # an address it still had to itself, so a fresh generation was not
            # the committed file, and the equality above was a claim about a
            # tree this one was not yet. The 2026-09-24 re-derivation
            # (#254/#256/#326, landed with issue #134's merge) closed that gap,
            # so the equality is the assertion again and this fallback is the
            # net for a *further* movement: the figures are now the two
            # censuses' current lengths, and a second movement fails here
            # rather than passing unnoticed behind the branch that skips the
            # equality. `xdata-register-map.md` §1 carries both gaps.
            self.assertEqual((len(rows), len(theirs)), stale)

    def test_the_cluster_id_column_is_untouched(self):
        # Every page in the tree names a `main-ec-NNN`, so the rank keeps the
        # exact values it has today. Switching over is a prose sweep, and this
        # is the assertion that the sweep is still possible to reason about.
        committed = clusters_of(CLUSTERS)
        for cid, row in committed.items():
            self.assertEqual(cid, row["cluster_id"])


def key_disagreements(clusters_rows, registers_rows):
    """{addr: (the row's cluster_key, its cluster's cluster_key)} for the
    register rows carrying a key their own clusters CSV does not give them.

    Offenders rather than an assertion, so the case that holds this and the
    forgery that shows it capable of going red ask one question of one
    implementation. Not beside `clusters_of`/`registers_of` above because
    those read one file and this compares two: the pair is the claim, and a
    reader checking the question itself should find it in one place.
    """
    by_id = {cid: row["cluster_key"] for cid, row in clusters_rows.items()}
    bad = {}
    for r in registers_rows:
        expected = by_id[r["cluster_id"]]
        if r["cluster_key"] != expected:
            bad[r["addr"]] = (r["cluster_key"], expected)
    return bad


def programs_not_mentioned(clusters_rows, registers_rows):
    """Sorted programs the clusters CSV has that the registers CSV never names.

    Set coverage rather than a row count, and the difference is the point: a
    count is a symptom of a collision and the whole of a coverage claim, which
    is why a registers CSV that lost every row of one program answers a
    per-program count exactly as well as one that kept them. The two CSVs are
    also not a per-program mirror of one another -- see
    `docs/findings/xdata-registers-agreement-vacuity.md` -- so a per-program
    count compared across the two is not a claim this repository satisfies.
    """
    mentioned = {r["program"] for r in registers_rows}
    return sorted({row["program"] for row in clusters_rows.values()} - mentioned)


class TheGuardOffKeyDistinctness(unittest.TestCase):
    """The guard-off generation's own key uniqueness, held by a case.

    The other half of `TheContentKey`, and the half that had no case. The
    committed census is read off disk and a fresh guard-on generation is built
    in-process by `--self-test`, so those two censuses are held; the guard-off
    generation is written to a scratch directory by a flag that is *refused*
    together with `--check` and `--self-test` (`xdata_register_map.py`'s
    refusal contract, held by `test_xdata_register_map.py::Refusals` and
    written up in `docs/findings/xdata-no-eq-guard-refusal-contract.md`), so
    no producer check could ever be aimed at it. That is the gap
    `xdata-moved-ranks-collision-scope.md` §5 recorded in as many words --
    "nothing holds *its* key uniqueness between runs" -- and the census it
    left uncovered is not an incidental one. `cause_report` re-keys the
    guard-off pair for its population, and that population is the `N
    guard-off key(s)` figure in the report's header, the `population` column
    every rate divides by, and `holders_by_program`'s per-program index. A
    collision there does not fail a run; it makes a count quietly too small.

    A separate class rather than an eighth case in
    `TheGuardOffRegeneration`, for the reason `TheExportOwnershipClusters`
    gives for itself: `docs/findings.md` §50 calls that class's seventh case
    "a seventh case", and an eighth would falsify a sentence this change has
    no business touching. The regeneration is the one `guard_off()` already
    caches, so this costs no second run -- the two classes share it.

    **The property is the claim; the totals are not -- and that is reasoning
    about a collision, not about the registers case.** Nothing here pins 445
    or 439. `duplicate_keys()` answers "are these distinct", and a re-
    derivation that moved the count would not have anything to say about the
    design being defended. The row count appears in the failure message, where
    a reader who is chasing a collision sees it, and nowhere else. That is the
    same reasoning `TheGuardOffRegeneration` applies to its `> 300` floor and
    `assertTrue(movers, ...)` to its exhibit, and for the same reason.

    **A count is the wrong witness for coverage, and coverage is the other
    half of what the registers case holds.** "Every register row the
    generation wrote carries its cluster's key" has a shorter witness than
    "every register row agrees", and the shorter one is the one that can
    shrink without anything going red: a registers CSV with no rows at all
    satisfies a row count, and one missing every `pd` row satisfies a
    per-program count, while the byte-to-key comparison over the rows that
    survive is simply true of both. So what the case below floors is a *set* --
    the CSV is non-empty, and it names every program its clusters CSV has --
    and no figure from either census is written into it.

    **The committed pair is held differently, and the difference is
    mechanical rather than editorial.** `TheContentKey`'s registers loop is
    left as it is because `xdata_register_map.py --check` regenerates both
    committed CSVs from the committed tree and byte-compares them, and the
    cheap gate runs it; a truncated, emptied or half-programmed committed
    `xdata-registers.csv` is a byte diff there, which is a stronger floor than
    one added here could be. This pair has no such floor *by construction* --
    `--no-eq-guard` is refused together with `--check` and refused again
    without scratch outputs, which is the whole reason this class exists -- so
    the floors go here instead.
    `docs/findings/xdata-registers-agreement-vacuity.md` measures both halves.

    The fourth census is not here: see `TheContentKey`'s docstring, which
    names the `e169a0e4` pair as held by none of this.
    """

    @classmethod
    def setUpClass(cls):
        _tmp, cls.clusters, cls.registers, _err = guard_off()
        cls.rows = clusters_of(cls.clusters)

    def test_the_guard_off_census_has_no_colliding_keys(self):
        # `duplicate_keys()` rather than a `len()` comparison, for the reason
        # the module-level import gives: this is the same predicate the
        # report's own `cluster_key unique ...` line is printed from, so a
        # disagreement here is a disagreement about the census rather than
        # about two implementations of the same question. And the message
        # names the keys and their ranks -- "N collisions" sends a reader to
        # the tool to find out which, which is the tool's job and not the
        # failure message's.
        dups = ranks.duplicate_keys(self.rows)
        self.assertEqual(
            dups, {},
            f"{len(dups)} colliding cluster_key(s) over the {len(self.rows)} "
            "guard-off row(s) -- "
            + ("; ".join(f"{k} on {', '.join(ranks_)}"
                         for k, ranks_ in sorted(dups.items()))
               or "none, which is a bug in this message rather than a result"))

    def test_the_guard_off_registers_csv_agrees_with_its_clusters(self):
        # The second half of `TheContentKey`'s case, over the pair this
        # generation actually wrote rather than the pair on disk. The reason
        # to hold it twice is that these are the CSVs nobody reads: they land
        # in a scratch directory and are gone with the next run, so a registers
        # CSV that disagreed with its own clusters CSV would break the
        # byte-to-key lookup here and be caught by nothing. The committed pair
        # gets read by people and by `--check`; this one gets read by nothing
        # but the tool that wrote it.
        #
        # **The two floors come first, because the comparison they guard is
        # vacuous without them.** `key_disagreements()` asks over the rows
        # there are: a CSV with none -- a header and nothing else, or a writer
        # that failed partway -- returns no offenders, and one missing every
        # row of a program returns no offenders for the rows of the others.
        # Both are cases this loop was written to catch and neither is a
        # disagreement, which is the difference between a claim about a
        # census and a claim about a file that happened to be readable.
        with open(self.registers, newline="") as f:
            registers_rows = list(csv.DictReader(f))
        self.assertTrue(
            registers_rows,
            "the guard-off registers CSV has a header and no data row, so the "
            "byte-to-key comparison below has nothing to compare and passes "
            "on the emptiness rather than on the agreement: the clusters CSV "
            f"it was written beside holds {len(self.rows)} cluster(s) over "
            f"{sorted({r['program'] for r in self.rows.values()})}")
        missing = programs_not_mentioned(self.rows, registers_rows)
        self.assertEqual(
            missing, [],
            "the guard-off registers CSV never names the program(s) "
            f"{missing}, so every cluster of those in its own clusters CSV is "
            "unchecked: the agreement asserted below is over the programs "
            "that survived the CSV, not over the census")
        bad = key_disagreements(self.rows, registers_rows)
        self.assertEqual(
            bad, {},
            f"{len(bad)} of {len(registers_rows)} guard-off register row(s) "
            "carry a cluster_key their own clusters CSV does not give them -- "
            + ("; ".join(
                f"{addr} carries {carried}, its cluster holding {held}"
                for addr, (carried, held) in sorted(bad.items()))
               or "none, which is a bug in this message rather than a result"))

    def test_a_duplicated_key_is_named_with_both_its_ranks(self):
        # The negative control, as a permanent case rather than a transcript.
        # The two above can only be *shown* capable of going red by handing
        # them a census that collides, and this is that census: copy one row's
        # key onto a second and ask the predicate what it makes of the result.
        # The fixture is a forgery -- `cluster_key` is a content hash over the
        # program and the sorted membership, so two different memberships
        # sharing one key is not something the tool emits -- and that is the
        # point rather than a flaw in the fixture. A collision worth holding a
        # case against cannot come from the generator; it comes from a census
        # assembled by something else, which is exactly the shape the
        # precondition is there to catch.
        rows = {cid: dict(row) for cid, row in self.rows.items()}
        donor, victim = sorted(rows)[:2]
        key = rows[donor]["cluster_key"]
        rows[victim]["cluster_key"] = key
        self.assertEqual(
            ranks.duplicate_keys(rows), {key: [donor, victim]},
            f"the forged collision was not reported as {key} on {donor} and "
            f"{victim}")

        # And the forgery stayed in the copy. `setUpClass` hands the same
        # regeneration to `TheGuardOffRegeneration`, so a case that wrote
        # through to the shared rows would leave a real collision behind for
        # whatever ran next -- and the assertion above would be a lie about
        # which census it had just checked.
        self.assertEqual(ranks.duplicate_keys(self.rows), {})

    def test_each_registers_forgery_is_caught_by_the_assertion_that_catches_it(self):
        # The negative control for the floors and the comparison above, and
        # what gives them their meaning: a hold case that has never gone red
        # has never been shown capable of it. One forgery per way the case can
        # be passed without having checked anything, each aimed at the
        # assertion that ought to catch it -- so a floor that has gone quiet
        # and a loop that has gone vacuous are distinguishable rather than
        # both silent.
        #
        # The fixture is a forgery for the same reason the collision above is:
        # `xdata_register_map.py` wrote this CSV and would not write a
        # half-written one. Each is written to a scratch file and read back,
        # because what is being modelled is the *file* a run left behind: a
        # writer that failed partway leaves a well-formed CSV that still
        # parses, which is precisely why nothing about reading it complains.
        tmp = tempfile.mkdtemp(prefix="xdata-forged-registers-")
        with open(self.registers, newline="") as f:
            reader = csv.DictReader(f)
            header, pristine = reader.fieldnames, list(reader)

        def forged(name, rows):
            """A scratch CSV carrying `rows`, read back the way the case
            above reads the real one."""
            path = os.path.join(tmp, name)
            with open(path, "w", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
            with open(path, newline="") as f:
                return list(csv.DictReader(f))

        # A row carrying another cluster's key: the disagreement the
        # byte-to-key comparison exists to catch, and the only one it can
        # catch by itself.
        #
        # The donor is picked by *cluster*, not by row, because a registers
        # CSV holds several rows per cluster: two neighbouring rows can share
        # a `cluster_id`, and copying that cluster's key onto the other would
        # forge nothing at all.
        victim = pristine[0]
        donor = next(r for r in pristine
                     if r["cluster_id"] != victim["cluster_id"])
        rows = [dict(r) for r in pristine]
        rows[0]["cluster_key"] = self.rows[donor["cluster_id"]]["cluster_key"]
        self.assertEqual(
            key_disagreements(self.rows, forged("wrong-key.csv", rows)),
            {victim["addr"]: (rows[0]["cluster_key"],
                              self.rows[victim["cluster_id"]]["cluster_key"])},
            f"a register row carrying {donor['cluster_id']}'s key was not "
            f"reported as {victim['addr']} disagreeing, and nothing else in "
            "the CSV does")

        # Every row deleted. The comparison returns nothing over an empty
        # list, which is asserted rather than argued. Two floors reach this
        # forgery, not one: the coverage floor below names every program,
        # because an empty CSV mentions none, so dropping the non-empty
        # assertion does not leave the case able to pass here. What the
        # non-empty assertion adds is the diagnosis -- it says the file has
        # no rows, where the coverage floor can only say which programs went
        # missing -- so it is kept for the message rather than for the red,
        # and a case that claimed otherwise in a comment it has not checked
        # is the failure the transcript in
        # `docs/findings/xdata-registers-agreement-vacuity.md` §3 exists to
        # prevent.
        empty = forged("empty.csv", [])
        self.assertEqual(
            key_disagreements(self.rows, empty), {},
            "the byte-to-key comparison is not what catches an empty CSV; if "
            "it does, the non-empty assertion ahead of it is unreachable and "
            "this message is wrong about which assertion holds what")
        self.assertEqual(
            programs_not_mentioned(self.rows, empty),
            sorted({r["program"] for r in self.rows.values()}),
            "a registers CSV with no data row leaves every program of its "
            "clusters CSV unmentioned, and the coverage floor did not name "
            "them")

        # And the per-program hole, over *every* program the clusters CSV
        # has rather than a typed one, so a census that grew a program or
        # lost one changes which hole this punches instead of quietly punching
        # nothing. The `assertNotEqual` is the guard for that: a forgery that
        # removed nothing would make the floor below pass on the strength of
        # a deletion that never happened.
        #
        # The registers CSV carries a program of its own that the clusters
        # CSV does not have, so it is deliberately absent from this loop: a
        # registers CSV with every one of *those* rows deleted still names
        # every program of the clusters CSV, and the coverage floor has
        # nothing to say about it. That is not an oversight in the floor but
        # a property of the pair, and it is measured in
        # `docs/findings/xdata-registers-agreement-vacuity.md`.
        for program in sorted({r["program"] for r in self.rows.values()}):
            with self.subTest(dropped=program):
                kept = [r for r in pristine if r["program"] != program]
                self.assertNotEqual(
                    kept, pristine,
                    f"no {program} row to drop, so this forgery is not the "
                    "half-written CSV it claims to be")
                self.assertEqual(
                    key_disagreements(self.rows, kept), {},
                    f"a registers CSV with every {program} row deleted still "
                    "agrees with its clusters CSV about every row it kept, "
                    "which is the hole this case is about")
                self.assertEqual(
                    programs_not_mentioned(self.rows, kept), [program],
                    f"a registers CSV with every {program} row deleted was not "
                    f"reported as not naming {program}, and nothing else went "
                    "with it")

        # And every forgery stayed in its own scratch copy. `setUpClass` hands
        # the same regeneration to `TheGuardOffRegeneration`, so a case that
        # wrote through to `self.registers` would leave a real disagreement
        # behind for whatever ran next -- and the assertions above would be a
        # lie about which CSV they had just checked.
        with open(self.registers, newline="") as f:
            self.assertEqual(
                list(csv.DictReader(f)), pristine,
                "a forgery wrote through to the shared guard-off registers "
                "CSV rather than to its own copy")


class TheNamesShape(unittest.TestCase):
    """`cluster_name_shape.py`'s four rules, each shown capable of refusing.

    A name is read as a citation wherever its words appear in a unit that makes
    a membership claim (`check_cluster_citations.py`'s `name_re()`), so the
    eleventh row of a file `ec/README.md` says is "a one-row edit" is the place
    this surfaces. `TheNamesFile` holds the file to the census; this class holds
    it to a shape, one case per refusal and two over the whole set.

    **Each case adds one constructed row to the committed names rather than
    replacing them, for the reason `TheGuardOffKeyDistinctness`'s forged
    collision gives: a rule that has only ever returned an empty list has not
    been shown capable of returning anything else.** The committed nine are in
    the set every time, so a case also fails if the rule it is testing has
    started firing on a name the file is supposed to keep -- which is the
    failure that would make the check unusable and get it deleted.

    The four refusal cases each call their own rule rather than `problems()`, so
    a rule that has gone quiet is distinguishable from a name that happened to
    trip a different one. The last two call `problems()`, because the wiring is
    its own thing to be wrong.

    **This class was last in the file, and that is load-bearing rather than
    incidental** -- see `setUpClass` below. `TheKeyIsTheHashOfItsRow` is
    appended below it, and that is the whole of what changed: the new class
    sits *under* this one, so every pin into this file still resolves to the
    line it was written against, and "last in the file" now means last of the
    classes that hold a rule rather than last outright. A class inserted above
    this one would move all of them.
    """

    @classmethod
    def setUpClass(cls):
        # Loaded here rather than at module scope, and last in the file rather
        # than beside the class it shares a subject with. Both are the same
        # constraint: `test_census_test_line_pins.py` censuses the prose pins
        # into this file's line numbers, so **any** line added above an
        # existing class lands each of those pins on a different line and moves
        # a set of figures four other files hold. The module-level loaders for
        # `xrm` and `ranks` sit at the top for the same reason, and this class
        # and the loader below it go at the end for the same reason again --
        # which is why the sibling tool is loaded in a `setUpClass` where the
        # file's own idiom would put it at line 34.
        spec_ = importlib.util.spec_from_file_location(
            "cluster_name_shape", HERE / "cluster_name_shape.py")
        shape = importlib.util.module_from_spec(spec_)
        spec_.loader.exec_module(shape)
        cls.shape = shape
        with open(NAMES, newline="") as f:
            cls.committed = [r["cluster_name"] for r in csv.DictReader(f)]
        cls.identifiers, cls.addresses = shape.vocabulary()

    def refused(self, rule, name, *rest):
        """`{offender: what_would_pass}` for one rule over the committed names
        plus `name`."""
        return dict(rule([*self.committed, name], *rest))

    def test_a_single_token_name_is_refused(self):
        # `gate` is the shape the issue means: a word, not a name. It is also
        # the word prefix of a long list of real functions, so the case names
        # R1's own reason rather than accepting whatever the rule happened to
        # report for it.
        found = self.refused(self.shape.multi_slug, "gate")
        self.assertIn("gate", found)
        self.assertIn("multi-slug", found["gate"])

    def test_a_name_inside_another_name_is_refused(self):
        # `level-block` is inside the committed `level-block-086x`, and
        # `name_re()` keeps the two apart today by sorting longest-first rather
        # than by any rule. The refusal names both halves, because a message
        # naming only the offender leaves the person choosing a name unable to
        # see which committed name to move.
        found = self.refused(self.shape.inside_another_name, "level-block")
        self.assertIn("level-block", found)
        self.assertIn("level-block-086x", found["level-block"])
        # And the longer one is not itself the offender: it is the container.
        self.assertNotIn("level-block-086x", found)

    def test_a_name_colliding_with_a_symbol_or_an_address_is_refused(self):
        # Two sub-shapes of one rule, both constructed to trip nothing else, so
        # a change to R1 or R4 cannot be what made this case pass.
        for name, because in (("xdata-0442", "XDATA_0442"),
                              ("0x0442-target", "0x0442")):
            with self.subTest(name=name):
                self.assertNotIn(name, self.shape.multi_slug(self.committed + [name]),
                                 f"{name} is a refusal R1 already makes, so "
                                 "it cannot show R3")
                found = self.refused(self.shape.collides_with_a_known_token, name,
                                     self.identifiers, self.addresses)
                self.assertIn(name, found)
                self.assertIn(because, found[name],
                              "the refusal has to name what it collided with, "
                              "not only that it collided")

    def test_a_word_prefix_of_a_known_identifier_is_refused(self):
        # The issue's own example, and the reason R4 exists. `charge-target` is
        # two slugs, is inside nothing committed and is not an address, so the
        # three rules the issue spells out all pass it; what the tree already
        # uses the same words for is the thing that catches it.
        found = self.refused(self.shape.prefixes_a_known_identifier, "charge-target",
                             self.identifiers)
        self.assertIn("charge-target", found)
        # Both halves of the vocabulary, which is the claim: the function the
        # issue names and the symbol at 0x0522/0x0523.
        for because in ("charge_target_update", "CHARGE_TARGET_MV_0"):
            self.assertIn(because, found["charge-target"])
        # And equality would not have caught it, which is why the rule is a
        # prefix rule: the name is strictly shorter than every identifier it
        # collides with.
        self.assertEqual(
            self.shape.collides_with_a_known_token(
                self.committed + ["charge-target"],
                self.identifiers, self.addresses),
            [],
            "if the equality rule now refuses charge-target, the word-prefix "
            "rule is doing nothing R3 was not already doing")

    def test_every_committed_name_passes_all_four_rules(self):
        # The claim the gate makes, held here as a case so a name that trips a
        # rule is caught by the suite and not only by the next
        # `xdata_register_map.py --self-test` run. Asserted over the rules
        # rather than a count of names: a tenth row is a legitimate edit, and a
        # tenth row that trips a rule is not.
        self.assertEqual(
            self.shape.problems(self.committed), [],
            f"{len(self.committed)} committed name(s) do not pass the four "
            f"shape rules: {self.shape.problems(self.committed)}")

    def test_and_fan_level_is_still_refused_by_nothing(self):
        # The issue's second example, and the one this change does not close.
        # Asserted rather than left as a sentence in a docstring, because a
        # stated limit nobody checks is a limit that quietly stops being true
        # in either direction: a reader cannot tell whether the tool grew a
        # rule that catches it or the file grew a name that does.
        #
        # **Red here is an improvement, not a defect.** It would mean one of
        # the four rules had started reading something it does not read today,
        # and the response is to move the exemption out of the docstring --
        # `cluster_name_shape.py`'s and `docs/findings/name-shape.md`'s
        # -- not to weaken the rule that caught it.
        self.assertEqual(
            self.shape.problems(self.committed + ["fan-level"]), [],
            "fan-level is now refused; a name this generic is what the rules "
            "were for, so record it in cluster_name_shape.py and "
            "docs/findings/name-shape.md and drop the claim that it is "
            "not caught")


class TheKeyIsTheHashOfItsRow(unittest.TestCase):
    """Every census row's `cluster_key` is the hash of that row's own columns.

    **The property, and why distinctness is not it.**
    `TheContentKey` and `TheGuardOffKeyDistinctness` each ask whether a
    census's keys are *distinct*, and distinctness is the wrong question for
    the two `b.get(k) or a[k]` reads
    `docs/findings/xdata-moved-ranks-second-count.md` §6 left alone on the
    strength of `cluster_key` being a content hash. A set of distinct keys
    passes both of those cases with every `program` and `addrs` cell in it
    wrong, so nothing behind them would notice a row that is not the cluster its
    own key names -- and `flip_table()`'s `shared`, `across_report()`'s `by
    construction` line and the `program` column all read the row rather than
    the key.

    **This recomputes the write path rather than a second reading of it.**
    `cluster_rows_build` writes `"program": g` and `"addrs"` from the same
    `members` the minting site hashed, `cluster_key` is that program and the
    `hexaddr`-sorted join of that membership, and `hexaddr` is the tool's one
    `f"0x{addr:04X}"` -- so `int(a, 16)` over the `addrs` cell inverts it
    exactly rather than approximately. What these cases evaluate is the
    expression the tool evaluated, over the cells the tool wrote; the CSV round
    trip is the only step between.

    **Two censuses, and why these two.** `TheContentKey` reads the committed
    pair off disk and the two `check()`s inside `self_test()` cover a fresh
    guard-on generation, but neither producer check can be pointed anywhere
    else: `--no-eq-guard` is refused together with `--check` and `--self-test`,
    and refused again without scratch outputs. So the committed census and the
    guard-off regeneration are the two a `keyed_by()`/`flip_table()` pair is
    built from, and they are the two here. The regeneration is the `guard_off()`
    this module already caches, so the second case costs no second run.

    **Distinctness is a different property, and neither class implies the
    other.** An earlier draft of this docstring argued that the round-trip *did*
    imply it -- that two rows carrying one membership under two keys would each
    have to disagree with their own row -- and that argument is false, and its
    witness is the last case below. A row copied verbatim under a second id is
    self-consistent: its key genuinely is the hash of its own columns, so
    `key_mismatches()` reports nothing and `duplicate_keys()` reports the two
    ranks sharing one key. The other direction is the shape the issue
    describes, a set of distinct keys none of which is the hash of its own row.
    Distinctness is therefore not re-asserted here, but for a reason that does
    not depend on that argument: `TheContentKey` and
    `TheGuardOffKeyDistinctness` already hold it over these same two censuses,
    and the two neighbours assert a *view's* precondition where these assert
    the writer's arithmetic.

    **The property is the claim; the totals are not.** Nothing here pins 439 or
    445. The row count appears in the failure message, where a reader chasing a
    bad row sees it, and nowhere else -- the reasoning
    `TheGuardOffKeyDistinctness` states for itself, and the hazard `CLAUDE.md`
    names: a test that asserts a count of the tree is a value every merge has to
    edit.

    **The `e169a0e4` pair is still held by nothing**, and this class does not
    make it look otherwise. `TheContentKey`'s docstring names that census and
    its guard-off regeneration as the fourth, unreached one; counting the
    classes instead of reading them would put the wrong number on the censuses
    this suite reaches, which is why that docstring says so.
    """

    @classmethod
    def setUpClass(cls):
        cls.committed = clusters_of(CLUSTERS)
        # Slot 1 of `guard_off()`'s tuple, reached by index rather than
        # unpacked: `TheGuardOffKeyDistinctness` names all four slots and this
        # wants the clusters CSV alone.
        cls.guard_off = clusters_of(guard_off()[1])

    def key_mismatches(self, rows):
        """{cluster_id: (stored, recomputed)} for the rows whose stored
        `cluster_key` is not the hash of their own `program` and `addrs`.

        One copy of the question, for both censuses and both forgeries alike.
        A second one would already be `xdata-moved-ranks-second-count.md` §3's
        shape -- two places that know how a row is built and can disagree about
        it -- and the disagreement would be invisible, because each would still
        be a correct re-derivation of something.
        """
        bad = {}
        for cid, row in sorted(rows.items()):
            addrs = [int(a, 16) for a in row["addrs"].split()]
            recomputed = xrm.cluster_key(row["program"], addrs)
            if recomputed != row["cluster_key"]:
                bad[cid] = (row["cluster_key"], recomputed)
        return bad

    def census_holds_its_own_keys(self, rows, which):
        """`rows` every one the hash of its own columns. `which` names the
        census in the failure message and nowhere else."""
        bad = self.key_mismatches(rows)
        self.assertEqual(
            bad, {},
            f"{which} census: {len(bad)} of {len(rows)} row(s) whose stored "
            "cluster_key is not the hash of their own program and addrs -- "
            + ("; ".join(
                f"{cid} holds {stored}, its own row hashing to {recomputed}"
                for cid, (stored, recomputed) in sorted(bad.items()))
               or "none, which is a bug in this message rather than a result"))

    def test_the_committed_census_holds_its_own_keys(self):
        # The census `xdata_register_map.py --check` re-derives and people read.
        self.census_holds_its_own_keys(self.committed, "committed")

    def test_the_guard_off_census_holds_its_own_keys(self):
        # The census `cause_report` re-keys for its population, and the half of
        # the pair no producer check can be aimed at.
        self.census_holds_its_own_keys(self.guard_off, "guard-off")

    def test_a_forged_row_is_named_with_both_keys(self):
        # The negative control, and what gives the two above their meaning: a
        # hold case that has never gone red has never been shown capable of it.
        # Two forgeries, one per direction a hand edit of a census goes -- the
        # `addrs` cell changed under a key left alone, which is the edit the
        # issue describes, and its inverse, a key copied onto a row that is not
        # the cluster it names. Both are forgeries `cluster_key`'s own content
        # hash would never emit, which is the point rather than a flaw in the
        # fixture: the row these cases exist to catch cannot come from the
        # generator, only from a census something else assembled.
        victim, donor = sorted(self.committed)[:2]
        # The two lowest ids, so a reader can find them at the top of the CSV
        # and neither is a single-address cluster, so dropping one from it
        # leaves a membership behind. The *last* address is the one dropped
        # because that is the edit which leaves the cell in the sorted order
        # `cluster_rows_build` writes it in -- a plausible hand edit rather
        # than an arbitrary corruption.
        for what, forge in (
            ("a hand-edited addrs cell", lambda row: row.update(
                addrs=" ".join(row["addrs"].split()[:-1]))),
            ("a copied cluster_key", lambda row: row.update(
                cluster_key=self.committed[donor]["cluster_key"])),
        ):
            with self.subTest(forged=what):
                rows = {cid: dict(r) for cid, r in self.committed.items()}
                forge(rows[victim])
                bad = self.key_mismatches(rows)
                self.assertEqual(
                    sorted(bad), [victim],
                    f"a row with {what} was not reported as the one row whose "
                    f"key disagrees with its own columns: {bad}")

        # And the forgeries stayed in the copies. `setUpClass` hands the same
        # committed census to `TheContentKey`, so a case that wrote through
        # would leave a real mismatch behind for whatever ran next -- and the
        # assertions above would be a lie about which census they had checked.
        self.assertEqual(self.key_mismatches(self.committed), {})

        # A third forgery, the one that goes in the other direction: a row
        # copied *verbatim* under a second id. The copy is self-consistent --
        # same program, same `addrs`, and a key that genuinely is the hash of
        # its own columns -- so `key_mismatches()` has nothing to report, and
        # `duplicate_keys()` names it. This is the witness that the round-trip
        # does not imply distinctness, held as a case rather than argued in the
        # write-up: an assertion the helper is expected to *fail* to make. Only
        # these two rows carry the key, so the rank list is exactly these two
        # whatever their relative order.
        twin = victim + "-dup"
        rows = {cid: dict(r) for cid, r in self.committed.items()}
        rows[twin] = dict(rows[victim], cluster_id=twin)
        key = rows[victim]["cluster_key"]
        self.assertEqual(
            self.key_mismatches(rows), {},
            "a census whose only defect is a row duplicated under a second id "
            "is self-consistent, so the round-trip has nothing to report; if "
            "this ever reports one, the helper is wrong rather than the census")
        self.assertEqual(
            {k: sorted(v) for k, v in ranks.duplicate_keys(rows).items()},
            {key: sorted([victim, twin])},
            f"the duplicated row was not reported as {key} on both {victim} "
            f"and {twin}, and nothing else in the census collides")


if __name__ == "__main__":
    unittest.main()
