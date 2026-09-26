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
`==` rejection off, via `--no-eq-guard`, which is the flag
`annotations/xdata-06c2-06db-timers.md` §6a already re-runs; no image, no
Ghidra, no network, and nothing here touched hardware.
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
    off" (`xdata_register_map.py:263`) and the mechanism that page re-runs its
    figures from. The flag refuses to be given the committed output paths, so
    both CSVs go to a scratch directory the tool is pointed at by name and the
    run reads the committed decompile and writes nothing into it. ~2 s, and the
    only reason the suite caches it is that six cases want the same
    regeneration.
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
    measurement rather than a description, so it is held by
    `test_the_census_is_the_one_6a_measured` instead of by a paragraph.

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
        # The only case in this class that holds the run to a published figure
        # rather than to itself. Every value below is one
        # `xdata-06c2-06db-timers.md` §6a prints, compared against the CSVs the
        # run above wrote -- not against a fresh run of the same recipe, which
        # would agree with itself by construction and would go on agreeing
        # after the recipe changed underneath it. That distinction is the whole
        # reason this case exists (#753: the recipe had been re-pointed three
        # times and a `source.replace()` that stopped matching failed
        # silently). §6b prints the derivation of the first three at
        # `xdata-06c2-06db-timers.md:952`; the 2026-09-25 re-derivation
        # recorded beside it is what put them at their current values.
        #
        # `test_xdata_register_map.py::AcceptedWrite` holds the same flag and
        # deliberately asserts *direction* instead of these counts, because it
        # has to survive an unrelated re-derivation. The two are not in
        # conflict: that suite is the flag's refusal contract and wants to
        # keep passing, this one is the census-identity claim and wants to go
        # red when the census it names has moved.
        off = registers_of(self.registers)
        on = registers_of(REGISTERS)
        # The two runs are over one address universe -- §6a compares them cell
        # for cell across "1,326 register rows" -- so a run that gained or
        # dropped an address is not the same measurement in a small way.
        self.assertEqual(set(off), set(on))

        # 833: §6a's "references entering `write`, all three programs", the
        # figure its table prints in bold. The word was "leaving" and the
        # arithmetic was a signed sum of `off - on` throughout, so the label
        # named a direction the sum did not check; it is corrected in place at
        # `xdata-06c2-06db-timers.md:785` and at
        # `docs/findings/xdata-write-direction-correction.md`, and the figure
        # itself is unchanged, because the terms are all non-negative and a net
        # that happens to equal a gross is a property of these 1,326 rows
        # rather than of the sum.
        self.assertEqual(
            sum(int(off[a]["write"]) - int(on[a]["write"]) for a in off), 833)

        # The half of that the figure alone cannot say: not one of the 1,326
        # addresses has a *lower* `write` under the guard-off run. The 833
        # above is a net, and a net cannot distinguish "833 arrived, none left"
        # from "900 arrived and 67 left" -- the two are the same number with
        # opposite meanings for what the guard does, and only the per-address
        # sign separates them. A decrease would be a defect rather than a
        # renumbering: the guard can only lift a rejection, so lifting it adds
        # `==` occurrences the pre-#178 classifier counted as stores and cannot
        # take one away. The direction is measured here and asserted as what it
        # is -- a property of this census against this flag -- which is what
        # makes 833 a gross figure a reader can bank rather than a net that
        # happens to agree with one.
        decreased = {a: (int(on[a]["write"]), int(off[a]["write"]))
                     for a in on if int(off[a]["write"]) < int(on[a]["write"])}
        self.assertEqual(
            decreased, {},
            f"§6a: {len(decreased)} address(es) have a lower `write` under "
            f"--no-eq-guard, which the guard's own removal of the `==` "
            f"rejection cannot cause")

        # 210 of 1,326, and 0 of 1,326: the other two lines of the heredoc, with
        # the denominators it prints alongside them. The 0 is the load-bearing
        # half of §6a's whole claim -- the guard moves references between
        # direction buckets and out of none of them, which is what makes every
        # row of §2a's 43-address table guard-invariant -- and a `refs` total
        # that moved would mean something other than this guard had moved too.
        # The denominators are pinned with the numerators because a
        # re-derivation that changes them has changed what §6a measured, and
        # the response to that is to re-derive §6a, not to move a number here.
        # That response is written out -- the eleven figures below (seven
        # before #850 added the four per-subset direction rows), §6b's two
        # per-program cluster counts one class down, the eighteen §2b of the
        # checklist measures, and the order to run the checks in -- at
        # docs/findings/xdata-census-rederivation-checklist.md, which is where
        # the export instruction and §6a itself now point. **§2b's held/unheld
        # split is a command's output, not prose**: `check_doc_figure_pins.py
        # --section 2b` measures all eighteen of its figures held since #849
        # read `OWNERSHIP["main_refs"]` and #850 added the rows above, and the
        # two it cannot see are named beside it -- the `157`/`858` §6b prints
        # for its *de-duplicated* run, which `ORACLE["extmem_pd_*"]` holds for
        # the default census instead, and the guard-off pd cluster count `51`,
        # which §6a does not print and so is not in that section's tables. An
        # `unheld` there is "not found by this method", never "absent".
        self.assertEqual(
            (sum(1 for a in on if off[a]["write"] != on[a]["write"]), len(on)),
            (210, 1326), "§6a: 'addresses whose write changes: 210 of 1326'")
        self.assertEqual(
            (sum(1 for a in on if off[a]["refs"] != on[a]["refs"]), len(on)),
            (0, 1326), "§6a: 'addresses whose refs changes: 0 of 1326'")

        # The four direction rows above the bold ones, each over one arm of the
        # `program` partition rather than over all 1,326 rows
        # (xdata-06c2-06db-timers.md:781-784). `program` is a partition --
        # every register row is `main-ec`, `pd` or `both`, and the three arms
        # sum to the same 1,326 the 210/0 denominators above already pin -- so
        # these are the *terms* of the 833 rather than a second reading of it.
        # That is what makes a re-export which moves a direction between the PD
        # set and the main-EC set go red here: on its own it moves a pair of
        # per-subset figures and leaves every aggregate above it standing.
        # §6a prints each figure over a stated denominator, so the denominator
        # is pinned in the same assertion, for the same reason the 210 and the
        # 0 are: a re-derivation that changes it changed what the row is over.
        # Each denominators assertion says which figures the page prints and
        # which are this assertion's, because the three arms are not alike
        # there: :781 carries the main-EC arm's parenthetical and :783 the pd
        # arm's, while :784 names the 49 both-image addresses with no refs
        # figure at all. A message that sends a re-deriver to a line without
        # the figure they are looking for is the failure this whole case is
        # about.
        #
        # **Four blocks rather than one loop over a table of cases, and the
        # expected pair is a literal inside each assertion rather than a `for`
        # header.** That is what #850's merge with #849 turned out to need, and
        # it is a claim about a second file: `check_doc_figure_pins.py` decides
        # a figure is `held` by finding it inside a `check()`/numeric-`assert*`
        # call, so a figure that only ever appears in a `for` header measures
        # `unheld` however many cases hold it. The checklist's §2b verdict
        # column is that command's own output and is re-run by
        # `test_check_doc_figure_pins.py::TheCommittedChecklist`, so a table
        # loop here would have sent every re-deriver to redo work this case
        # does. Nothing about *what* is asserted changes; the two shared
        # helpers below are what the loop body used to be.
        def arm_sum(program, direction):
            """(guard-off, committed) for one arm of the `program` partition."""
            return tuple(sum(int(r[direction]) for r in rows.values()
                             if r["program"] == program)
                         for rows in (off, on))

        def arm_denominators(program, rows):
            """(addresses, refs) over one arm -- the denominator §6a states."""
            arm = [r for r in rows.values() if r["program"] == program]
            return (len(arm), sum(int(r["refs"]) for r in arm))

        with self.subTest(program="main-ec", direction="write"):
            measured = arm_sum("main-ec", "write")
            self.assertEqual(
                measured, (3948, 3206),
                f"§6a 'main-ec `write` references', guard removed / as "
                f"committed: measured {measured[0]} / {measured[1]} against "
                f"the page's 3948 / 3206")
            for rows, label in ((off, "guard-off"), (on, "committed")):
                denominators = arm_denominators("main-ec", rows)
                self.assertEqual(
                    denominators, (1169, 13891),
                    f"§6a 'main-ec' denominators (1169 addresses, 13891 refs): "
                    f"measured {denominators[0]} / {denominators[1]} in the "
                    f"{label} census -- §6a:781 prints both, on the `write` "
                    f"row. The `0 of {len(on)}` above is the same fact over all "
                    "three arms, so this localises it to one")

        with self.subTest(program="main-ec", direction="read"):
            measured = arm_sum("main-ec", "read")
            self.assertEqual(
                measured, (7189, 7935),
                f"§6a 'main-ec `read` references', guard removed / as "
                f"committed: measured {measured[0]} / {measured[1]} against "
                f"the page's 7189 / 7935")
            for rows, label in ((off, "guard-off"), (on, "committed")):
                denominators = arm_denominators("main-ec", rows)
                self.assertEqual(
                    denominators, (1169, 13891),
                    f"§6a 'main-ec' denominators (1169 addresses, 13891 refs): "
                    f"measured {denominators[0]} / {denominators[1]} in the "
                    f"{label} census -- §6a:781 prints both, for the arm rather "
                    f"than for the row. The `0 of {len(on)}` above is the same "
                    "fact over all three arms, so this localises it to one")

        with self.subTest(program="pd", direction="write"):
            measured = arm_sum("pd", "write")
            self.assertEqual(
                measured, (193, 142),
                f"§6a 'pd `write` references', guard removed / as committed: "
                f"measured {measured[0]} / {measured[1]} against the page's "
                f"193 / 142")
            for rows, label in ((off, "guard-off"), (on, "committed")):
                denominators = arm_denominators("pd", rows)
                self.assertEqual(
                    denominators, (108, 603),
                    f"§6a 'pd' denominators (108 addresses, 603 refs): "
                    f"measured {denominators[0]} / {denominators[1]} in the "
                    f"{label} census -- §6a:783 prints both. The `0 of "
                    f"{len(on)}` above is the same fact over all three arms, so "
                    "this localises it to one")

        with self.subTest(program="both", direction="write"):
            measured = arm_sum("both", "write")
            self.assertEqual(
                measured, (279, 239),
                f"§6a 'both `write` references', guard removed / as committed: "
                f"measured {measured[0]} / {measured[1]} against the page's "
                f"279 / 239")
            for rows, label in ((off, "guard-off"), (on, "committed")):
                denominators = arm_denominators("both", rows)
                self.assertEqual(
                    denominators, (49, 1202),
                    f"§6a 'both' denominators (49 addresses, 1202 refs): "
                    f"measured {denominators[0]} / {denominators[1]} in the "
                    f"{label} census -- §6a:784 prints the address count and "
                    "no refs figure; the refs total is this assertion's -- the "
                    "sum of `refs` over the `program=both` rows -- and is not "
                    "printed there. The `0 of "
                    f"{len(on)}` above is the same fact over all three arms, so "
                    "this localises it to one")

        # 833 is the sum of the three `write` arms, which §6a states rather
        # than shows. Asserted because it is a claim about the partition: a
        # `program` column that stopped partitioning would leave the total at
        # 833 and the terms not adding to it, which is the shape a table takes
        # when a row has been transcribed from the wrong column.
        deltas = [sum(int(off[a]["write"]) - int(on[a]["write"]) for a in off
                      if off[a]["program"] == program)
                  for program in ("main-ec", "pd", "both")]
        self.assertEqual(
            sum(deltas), 833,
            "§6a 'references entering `write`, all three programs' (`:785`): the "
            f"three per-program deltas are {deltas}, which sum to "
            f"{sum(deltas)}; the page prints that sum in bold, so a set that "
            "does not add up to it has a row transcribed from the wrong column "
            "rather than a total that moved. Re-derive §6a; do not move this "
            "number")

        # The two named rows of §6a's table, where the totals above are visible
        # address by address. Both are addresses the sweep covers, so they are
        # also the two rows in the prose rather than only in the census.
        for addr, guard_off_rw, committed_rw in (
                ("0x08A8", ("84", "44"), ("126", "2")),
                ("0x0843", ("84", "42"), ("126", "0"))):
            with self.subTest(addr=addr):
                self.assertEqual((off[addr]["read"], off[addr]["write"]),
                                 guard_off_rw)
                self.assertEqual((on[addr]["read"], on[addr]["write"]),
                                 committed_rw)

        # 394 against 389: §6a's "main-EC clusters at threshold 0.50", and the
        # row the rest of this class is downstream of. The renumbering these
        # cases are about exists because the guard-off census has five more
        # main-EC clusters to sort ahead of the committed one, and five rows
        # that appear in one census and not the other is where the ranks
        # `test_the_regeneration_really_moves_the_ranks` counts come from.
        self.assertEqual(
            len([r for r in self.off.values() if r["program"] == "main-ec"]), 394)
        self.assertEqual(
            len([r for r in self.committed.values() if r["program"] == "main-ec"]),
            389)

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
        # `counter-sweep` is not one of them. It is at `main-ec-003` in both
        # censuses now; the `main-ec-002` the paragraph above leaves it at is
        # itself a superseded reading, kept here rather than edited out for the
        # same reason. It is the most-cited cluster in the tree all the same
        # (`xdata-register-map.md:1156` records the count that line was written
        # against — `grep -rl 'main-ec-003\b' --include=*.md .` naming nine
        # files, against seven for `main-ec-002` — and the tenth is
        # `docs/findings/xdata-cluster-names-guard-off-recipe.md`, whose
        # comparison transcript names `counter-sweep` on both sides, so the
        # numeral is that line's figure rather than a current one), so
        # the exhibit this case fell back on is the one the ranking happens to
        # spare. The assertion stays `assertTrue(movers, …)`
        # on purpose: pinning the count would be the hazard this class's own
        # docstring exists to record — a total pasted into a file is a snapshot
        # of the merge it was measured on — and it would go red on any
        # re-derivation for a reason that says nothing about the design being
        # argued here. The count is recorded as prose in
        # `docs/findings/xdata-cluster-names-guard-off-recipe.md`, which is
        # where the derivation behind it is printed; the floor this case does
        # hold is the census-wide one in
        # `test_the_regeneration_really_moves_the_ranks`.
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

    `OWNERSHIP["clusters"]` holds the 440 that `--export-ownership` produces
    and `--self-test` asserts it against an after-census built in-process
    (`xdata_register_map.py:4347-4354`), so five clusters moving from one program
    to the other left every assertion in the tree green and both lines of
    §6b's console block wrong at once. A *separate* class rather than another
    case in `TheGuardOffRegeneration`, for two reasons: it is a different
    flag's census, so the two regenerations are not the same measurement and
    one class would read as though they were; and `docs/findings.md` §50 calls
    the other class's seventh case "a seventh case", so an eighth there would
    falsify a sentence this change did not set out to touch.
    """

    @classmethod
    def setUpClass(cls):
        _tmp, cls.clusters, _registers, cls.stdout = export_ownership_census()
        cls.rows = list(clusters_of(cls.clusters).values())

    def test_the_440_splits_the_way_6b_prints_it(self):
        counts = collections.Counter(r["program"] for r in self.rows)
        self.assertEqual(
            dict(counts), {"main-ec": 390, "pd": 50},
            "§6b: 'main-ec: 1218 distinct addresses, 9320 references, 390 "
            f"clusters at threshold 0.5' and its `pd` line's 50 -- measured "
            f"{dict(counts)} across the {len(self.rows)} cluster rows the run "
            "wrote")
        # And the split is held to the total it is the breakdown of, so the two
        # cannot drift apart: OWNERSHIP is the 440, this is the division of it.
        self.assertEqual(
            sum(counts.values()), xrm.OWNERSHIP["clusters"],
            "§6b 'wrote ...: 440 rows' is the sum of those two console lines, "
            f"and OWNERSHIP['clusters'] holds it (now "
            f"{xrm.OWNERSHIP['clusters']}); the split {dict(counts)} sums to "
            f"{sum(counts.values())}, so the breakdown and the total have "
            "drifted apart. Re-derive §6b; do not move either number")

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


if __name__ == "__main__":
    unittest.main()
