#!/usr/bin/env python3
"""Every row of the names file gets an outcome, not every new cluster
(issue #881).

`carry_names()` appends one record per new **cluster**, so a hand name whose
key is not a cluster of this run and which no new cluster reaches at
`CARRY_MIN_JACCARD` was in no record and in no cell of the tally: the five
counters summed clusters that carried a name, which is not the number of names
in `annotations/xdata-cluster-names.csv`. A reader of a re-clustering run could
not tell "every name is accounted for" from "two names fell under the floor".
`xdata_name_coverage.py` is the transpose, one record per names-file row, and
this is the suite that holds it there.

The cases are in-process on synthetic fixtures, with one exception at the end
that reads the committed CSVs directly. The property is about the *shape* of the
report -- which names are accounted for, which are written twice, what a name
with no membership says -- and none of it is a fact about the firmware, so a
census run would only add a minute of waiting to a suite about arithmetic. No
image, no Ghidra, no hardware, no Windows, no network.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import unittest

HERE = Path(__file__).parent
EC = HERE.parent


def load(name):
    """A tool module by path, the way the sibling suites load this one.

    `sys.path` is not touched: `xdata_name_coverage` has no imports of its own
    to resolve, and `xdata_register_map` inserts `TOOL_DIR` into `sys.path`
    itself, so importing it here is enough to make its own `import
    xdata_name_coverage` find the same file this loaded.
    """
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


xnc = load("xdata_name_coverage")
xrm = load("xdata_register_map")

# The line the committed census has printed since #851, character for
# character. Pinned rather than recomputed from the counters, for the reason
# `test_xdata_carry_notice.py` pins its own clause: "the committed shape is
# unchanged" is only checkable against a copy of the old string. Recomputing it
# from `print_carry` would pass on any rewording of the tally, which is the
# one thing a transcript in the tree must not lose.
# The committed census's tally line, with its two census counts left as slots:
# how many names the names file seeds, and how many clusters carry none. The
# second moves whenever seeding re-forms the clusters (#1849 took it from 430 to
# 437), so it is derived from the committed CSV rather than typed (2026-10-04);
# the wording around it is still held literally.
COMMITTED_TALLY = ("  names: seeded {seeded}, exact 0, carried by overlap 0, tied, "
                   "not carried 0, with no name {unnamed}\n")

NAMES_CSV = EC / "annotations/xdata-cluster-names.csv"
CLUSTERS_CSV = EC / "annotations/xdata-clusters.csv"


class Fixture(unittest.TestCase):
    """One named old cluster of twenty addresses, the shared starting point.

    Twenty rather than two, because a two-address old row against a two-address
    new one is Jaccard 1.0 however unrelated they look, which is how a fixture
    meant to test a miss ends up asserting a carry.
    """

    TWENTY = list(range(0x0E, 0x0E + 20))

    def old(self, cid, key, name, addrs):
        return {"cluster_id": cid, "cluster_key": key, "cluster_name": name,
                "addrs": " ".join(xrm.hexaddr(a) for a in addrs)}

    def new(self, cid, key, addrs):
        return {"cluster_id": cid, "cluster_key": key,
                "addrs": " ".join(xrm.hexaddr(a) for a in addrs)}

    def carry(self, old, seeded, new):
        """`(names, report, coverage)` for one fixture.

        Through `carry_names()` rather than through `coverage()` alone, because
        the two halves are supposed to agree: the coverage list reads the
        report, and a caller that built one without the other would test a
        shape the tool never produces.
        """
        names, report = xrm.carry_names(old, seeded, new)
        cov = xnc.coverage(old, seeded, new, report, xrm.CARRY_MIN_JACCARD)
        return names, report, cov

    def stderr_of(self, report, cov, shape_label=""):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            xrm.print_carry(report, cov, shape_label)
        return buf.getvalue()

    def coverage_stderr(self, cov):
        buf = io.StringIO()
        xnc.print_coverage(cov, xrm.CARRY_MIN_JACCARD, buf)
        return buf.getvalue()

    def pair(self):
        """The `flag-pair-0442` shape as it really occurs, for the duplicate.

        A two-address name whose two addresses a higher threshold splits into
        two one-address clusters, each of which then scores exactly 0.50
        against the pair it came from. This is the mirror of a `tie` -- one
        name, two clusters, where the cluster pass has no way to prefer either.
        """
        old = [self.old("main-ec-125", "kb07a0f522a7d", "flag-pair-0442",
                        [0x0442, 0x0801])]
        new = [self.new("main-ec-317", "k41700000000", [0x0442]),
               self.new("main-ec-329", "k42900000000", [0x0801])]
        return old, {"kb07a0f522a7d": "flag-pair-0442"}, new


class TheNameIsAccountedFor(Fixture):
    """`len(coverage) == len(names file)`, on the case that broke it.

    A name nothing reaches is the whole reason the list exists. Before it,
    that name was in no cluster's record and in no tally cell; the block could
    not tell a reader it had been looked for and not found.
    """

    def test_a_name_nothing_claims_is_in_coverage_and_absent_from_the_report(self):
        # One address in common, 28 in the union: under the floor, so the
        # cluster pass says `none` about the *cluster* and never names the
        # `gate` name at all. The name is the one the census carries and this
        # run has lost, and it is exactly the name no cluster record mentions.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        [0x0E] + list(range(0xF0, 0xF8)))]
        new = [self.new("main-ec-317", "knew0000000000", [0x0E, 0xF0])]
        names, report, cov = self.carry(old, {"kold111111111": "gate"}, new)

        self.assertEqual(len(cov), 1)
        self.assertEqual(cov[0]["name"], "gate")
        self.assertEqual(cov[0]["how"], "none")
        self.assertAlmostEqual(cov[0]["jaccard"], 2 / 9)
        self.assertEqual(cov[0]["carried_to"], "")
        # The other half of the claim: it really is absent from the report, so
        # the coverage list is adding information rather than restating.
        self.assertEqual(names, {})
        self.assertEqual([r["name"] for r in report if r["name"]], [])

    def test_the_records_are_one_per_names_file_row(self):
        # The property as a length rather than as a case: a name dropped from
        # the list is a shorter list, and every other case here would still
        # pass. Four names, four records, whatever the run did with them.
        old = [self.old("main-ec-001", "kold111111111", "carried", self.TWENTY),
               self.old("main-ec-002", "kold222222222", "dropped",
                        [0x0E] + list(range(0xF0, 0xF8)))]
        seeded = {"kold111111111": "carried", "kold222222222": "dropped",
                  "kgone00000000": "never-in-this-census", "knew0000000000": "fresh"}
        new = [self.new("main-ec-001", "knew0000000000", self.TWENTY),
               self.new("main-ec-317", "ksplit00000000", [0xF0])]
        _names, _report, cov = self.carry(old, seeded, new)
        self.assertEqual(len(cov), len(seeded))
        self.assertEqual([r["name"] for r in cov], sorted(seeded.values()))

    def test_a_name_that_cleared_the_floor_is_not_said_to_be_under_it(self):
        # A name whose best score clears CARRY_MIN_JACCARD and is still on no
        # cluster: the cluster it matched took a different name. Printing "under
        # the floor" here would be false, and naming what that cluster carries
        # would be a claim about a record this half never read -- a cluster that
        # reached a *tie* carries nothing at all. So the line states only what
        # is provable from the name's own side.
        # `other` is the cluster exactly, at 1.0, and `gate` is that cluster
        # plus one address, at 0.95. The cluster goes to `other`; `gate` scored
        # well and is on nothing.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        self.TWENTY + [0x30]),
               self.old("main-ec-002", "kold222222222", "other", self.TWENTY)]
        _names, _report, cov = self.carry(
            old, {"kold111111111": "gate", "kold222222222": "other"},
            [self.new("main-ec-317", "knew0000000000", self.TWENTY)])
        gate = next(r for r in cov if r["name"] == "gate")
        self.assertEqual(gate["how"], "none")
        self.assertGreaterEqual(gate["jaccard"], xrm.CARRY_MIN_JACCARD)
        out = self.coverage_stderr([gate])
        self.assertNotIn("under the", out)
        self.assertNotIn("under the floor", out)
        self.assertIn("main-ec-317", out)
        self.assertIn("none of them", out)

    def test_a_name_under_the_floor_prints_its_score_and_says_not_carried(self):
        # The wording is the finding. A reader has to be able to tell "nothing
        # came close" from "nothing was even looked for", and the score is the
        # only thing in the line that does it.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        [0x0E] + list(range(0xF0, 0xF8)))]
        new = [self.new("main-ec-317", "knew0000000000", [0x0E, 0xF0])]
        _names, report, cov = self.carry(old, {"kold111111111": "gate"}, new)
        out = self.stderr_of(report, cov)
        self.assertIn(
            "    gate (kold111111111) is not carried by this run: best Jaccard "
            f"0.22 against any of the {len(new)} clusters, under the "
            f"{xrm.CARRY_MIN_JACCARD:.2f} floor\n", out)
        self.assertIn("not carried by this method", out)

    def test_a_near_miss_is_reported_as_a_miss_and_not_rounded_up(self):
        # 20 addresses against 41 in the union -- 0.488, printed as `0.49` --
        # against a 0.50 rule. The score is printed as measured rather than
        # rounded down to the floor or up past it, and the line says it is
        # under the floor rather than implying it cleared it.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        self.TWENTY + list(range(0xF0, 0xF0 + 21)))]
        new = [self.new("main-ec-317", "knew0000000000", self.TWENTY)]
        _names, report, cov = self.carry(old, {"kold111111111": "gate"}, new)
        record = cov[0]
        self.assertEqual(record["how"], "none")
        self.assertLess(record["jaccard"], xrm.CARRY_MIN_JACCARD)
        self.assertIn("0.49 against", self.coverage_stderr(cov))
        self.assertIn("under the 0.50 floor", self.coverage_stderr(cov))


class TheDuplicate(Fixture):
    """One name, two new clusters, and the refusal between them.

    The mirror of the `tie` branch: a `tie` is two names for one cluster and
    picks neither, and this is one name for two clusters. Both are facts about
    the clustering rather than questions this rule may answer, so an *undecidable*
    one picks none -- a hand claim still wins outright and unequal scores still
    pick the better cluster, which is what the last two cases here hold.
    """

    def test_two_new_clusters_claiming_one_name_is_a_duplicate(self):
        _names, _report, cov = self.carry(*self.pair())
        self.assertEqual(len(cov), 1)
        self.assertEqual(cov[0]["how"], "duplicate")
        self.assertEqual(cov[0]["carried_to"], "")

    def test_the_name_is_written_to_at_most_one_cluster(self):
        # The consequence that matters. Before the second pass this name landed
        # on two rows of `xdata-clusters.csv` and the two rows disagreed about
        # which cluster the pair is.
        old, seeded, new = self.pair()
        names, _report, _cov = self.carry(old, seeded, new)
        self.assertEqual(names, {})

    def test_both_losing_records_keep_the_name_and_say_who_else_claimed_it(self):
        # `name` is kept on the losers so the report says *which* name was
        # refused; a record stripped of its name says only that some name was,
        # which is the same information as printing nothing.
        old, seeded, new = self.pair()
        _names, report, _cov = self.carry(old, seeded, new)
        losers = [r for r in report if r["how"] == "duplicate"]
        self.assertEqual(len(losers), 2)
        for r in losers:
            self.assertEqual(r["name"], "flag-pair-0442")
            self.assertIn("main-ec-317", r["detail"])
            self.assertIn("main-ec-329", r["detail"])

    def test_the_duplicate_line_names_both_clusters_and_refuses_to_pick(self):
        _names, report, cov = self.carry(*self.pair())
        out = self.stderr_of(report, cov)
        self.assertIn(
            "    flag-pair-0442 (kb07a0f522a7d) is claimed by 2 clusters at "
            "Jaccard 0.50 (main-ec-317, main-ec-329); carried to none, because "
            "the rule will not pick between them\n", out)

    def test_a_duplicate_is_not_two_independent_carries(self):
        # The failure this closes. A name on two rows reads as two claims that
        # both succeeded; one row and a refusal reads as one judgement about
        # the clustering. Asserted on the written rows, not on the report.
        old, seeded, new = self.pair()
        names, _report, _cov = self.carry(old, seeded, new)
        written = [k for k, n in names.items() if n == "flag-pair-0442"]
        self.assertLessEqual(len(written), 1)

    def test_an_unequal_pair_gives_the_name_to_the_better_cluster(self):
        # The refusal is for a *tie* between the claimants, not for a
        # multi-claim as such. Two clusters reaching one name is not yet a
        # disagreement when one of them reached it more clearly.
        old = [self.old("main-ec-125", "kpair00000000", "pair", self.TWENTY)]
        new = [self.new("main-ec-317", "kfull00000000", self.TWENTY),
               self.new("main-ec-318", "kwider000000", self.TWENTY + [0x30])]
        names, _report, cov = self.carry(old, {"kpair00000000": "pair"}, new)
        self.assertEqual(cov[0]["how"], "overlap")
        self.assertEqual(cov[0]["carried_to"], "main-ec-317")
        self.assertEqual(names, {"kfull00000000": "pair"})

    def test_a_hand_claim_outranks_a_guess_at_the_same_score(self):
        # A `seeded` record is a human saying which cluster this name is. A
        # guess of the same score does not overrule the file this exists to
        # report on, so the seeded cluster keeps the name.
        old = [self.old("main-ec-125", "kpair00000000", "pair", [0x0E, 0x0F])]
        new = [self.new("main-ec-317", "kseed00000000", [0x0E, 0x0F]),
               self.new("main-ec-318", "kguess0000000", [0x0E, 0x0F])]
        names, _report, cov = self.carry(old, {"kseed00000000": "pair"}, new)
        self.assertEqual(names, {"kseed00000000": "pair"})
        self.assertEqual(cov[0]["how"], "seeded")
        self.assertEqual(cov[0]["carried_to"], "main-ec-317")


class TheTally(Fixture):
    """The tally has to say which number it is summing.

    Its five counters sum the clusters that carried a name. On a run that
    re-clusters, that is not the number of names in the file, and a tally that
    reads as complete when two names fell under the floor is the overclaim
    issue #881 is about.
    """

    def test_a_committed_run_gets_no_clause_at_all(self):
        self.assertEqual(xnc.tally_clauses([], "annotations/x.csv"), "")

    def test_a_name_the_method_did_not_carry_is_named_on_the_tally_line(self):
        _names, report, cov = self.carry(
            [self.old("main-ec-001", "kold111111111", "gate",
                      [0x0E] + list(range(0xF0, 0xF8)))],
            {"kold111111111": "gate"},
            [self.new("main-ec-317", "knew0000000000", [0x0E, 0xF0])])
        out = self.stderr_of(report, cov)
        self.assertIn(
            "and 1 of the 1 names in annotations/xdata-cluster-names.csv "
            "are not carried by this method", out)

    def test_a_duplicate_is_counted_separately_from_a_miss(self):
        # Two different questions, so two cells: how many names more than one
        # cluster reached and the rule refused, and how many of the file's
        # names went unwritten. A duplicate is in the second and not the first.
        #
        # The wording is the assertion. This cell counts a *refusal* --
        # `resolve_duplicate()` took the tie and carried the name to none of
        # the claimants -- so a clause reading "carried to two clusters" would
        # state the opposite of what the same run's per-name line and its
        # written CSV say. Pinned here as a substring so a reword back to a
        # claim of carrying fails this suite.
        _names, report, cov = self.carry(*self.pair())
        out = self.stderr_of(report, cov)
        self.assertIn("claimed by more than one cluster, not carried 1", out)
        self.assertNotIn("carried to two clusters", out)
        self.assertIn("and 1 of the 1 names in", out)

    def test_a_name_carried_somewhere_is_not_in_the_unwritten_count(self):
        # The count is of names, not of records, and a name the run carried is
        # not among them however many clusters guessed at it.
        cov = [{"name": "gate", "key": "k1", "how": "overlap", "jaccard": 0.9,
                "carried_to": "main-ec-317", "detail": "", "clusters": 2},
               {"name": "other", "key": "k2", "how": "none", "jaccard": 0.1,
                "carried_to": "", "detail": "", "clusters": 2}]
        self.assertNotIn("claimed by more than one cluster",
                         xnc.tally_clauses(cov, "x"))
        self.assertIn("and 1 of the 2 names in x", xnc.tally_clauses(cov, "x"))


class TheKeyThatIsNotACluster(Fixture):
    """A names-file key the committed census does not have.

    `CLAUDE.md`'s rule for a static scan applies here: a key with no
    membership to score is **not found by this method**, and a `0.00` in a
    report is a reading of it. A name compared against every cluster and
    matching none is a different finding from a name there was nothing to
    compare.
    """

    def test_a_key_the_committed_census_lacks_has_no_membership_to_score(self):
        old = [self.old("main-ec-001", "kold111111111", "carried", self.TWENTY)]
        _names, _report, cov = self.carry(
            old, {"kold111111111": "carried", "kgone00000000": "never-there"},
            [self.new("main-ec-001", "kold111111111", self.TWENTY)])
        gone = next(r for r in cov if r["name"] == "never-there")
        self.assertEqual(gone["how"], "key-not-found")
        # `None`, not `0.0`. A score of zero is a measurement; this is the
        # absence of one, and a report that prints both as `0.00` cannot tell
        # a reader which it is looking at.
        self.assertIsNone(gone["jaccard"])
        self.assertEqual(gone["carried_to"], "")

    def test_the_line_says_it_cannot_say_rather_than_scoring_it_zero(self):
        cov = [{"name": "never-there", "key": "kgone00000000",
                "how": "key-not-found", "jaccard": None, "carried_to": "",
                "detail": "", "clusters": 3}]
        out = self.coverage_stderr(cov)
        self.assertIn("no membership in the committed census to score against",
                      out)
        self.assertNotIn("0.00", out)

    def test_it_counts_as_not_carried(self):
        # It is unwritten, so the tally has to say so. A name the method
        # cannot judge is not a name the method carried.
        cov = [{"name": "never-there", "key": "kgone00000000",
                "how": "key-not-found", "jaccard": None, "carried_to": "",
                "detail": "", "clusters": 3}]
        self.assertIn("and 1 of the 1 names in x", xnc.tally_clauses(cov, "x"))


class TheUnchangedOutcomes(Fixture):
    """The five outcomes the cluster-indexed half already had still print what
    they printed, and the new half does not restate them."""

    def test_a_seeded_name_prints_no_per_name_line(self):
        old = [self.old("main-ec-001", "kold111111111", "gate", self.TWENTY)]
        _names, report, cov = self.carry(
            old, {"kold111111111": "gate"},
            [self.new("main-ec-001", "kold111111111", self.TWENTY)])
        self.assertEqual(cov[0]["how"], "seeded")
        self.assertEqual(cov[0]["carried_to"], "main-ec-001")
        self.assertEqual(self.coverage_stderr(cov), "")
        # The tally and nothing else, which is what `--check` prints today.
        self.assertEqual(self.stderr_of(report, cov).count("\n"), 1)

    def test_a_tie_keeps_its_own_line_and_its_own_wording(self):
        # #851's line, unchanged: two names for one cluster is still a `tie`
        # and still prints as one. The name-indexed half does not absorb it,
        # because a tie is a claim about a cluster and has no name-indexed
        # spelling.
        old = [self.old("main-ec-001", "kold111111111", "first", self.TWENTY),
               self.old("main-ec-002", "kold222222222", "second", self.TWENTY)]
        _names, report, _cov = self.carry(
            old, {"kold111111111": "first", "kold222222222": "second"},
            [self.new("main-ec-317", "knew0000000000", self.TWENTY)])
        self.assertEqual([r["how"] for r in report], ["tie"])
        self.assertIn(
            "    main-ec-317 is claimed by two names at Jaccard 1.00 "
            "(first (main-ec-001) == second (main-ec-002)); not carried by this "
            "method\n", self.stderr_of(report, []))

    def test_an_overlap_line_keeps_its_advice_clause(self):
        # `test_xdata_carry_notice.py` owns the advice; this asserts only that
        # adding a name-indexed half did not move it.
        old = [self.old("main-ec-001", "kold111111111", "gate",
                        self.TWENTY + [0x30])]
        _names, report, cov = self.carry(
            old, {"kold111111111": "gate"},
            [self.new("main-ec-317", "knew0000000000", self.TWENTY)])
        self.assertEqual(cov[0]["how"], "overlap")
        out = self.stderr_of(report, cov)
        self.assertIn(xrm.carry_advice(""), out)

    def test_every_coverage_record_has_the_seven_fields_and_a_known_how(self):
        old = [self.old("main-ec-125", "kb07a0f522a7d", "flag-pair-0442",
                        [0x0442, 0x0801]),
               self.old("main-ec-001", "kold111111111", "gate",
                        [0x0E] + list(range(0xF0, 0xF8)))]
        seeded = {"kb07a0f522a7d": "flag-pair-0442",
                  "kold111111111": "gate", "kgone00000000": "never-there"}
        new = [self.new("main-ec-317", "k41700000000", [0x0442]),
               self.new("main-ec-329", "k42900000000", [0x0801])]
        _names, _report, cov = self.carry(old, seeded, new)
        fields = {"name", "key", "how", "jaccard", "carried_to", "detail",
                  "clusters"}
        for r in cov:
            with self.subTest(name=r["name"]):
                self.assertEqual(set(r), fields)
                self.assertIn(r["how"], ("seeded", "exact", "overlap",
                                         "duplicate", "none", "key-not-found"))
                # `carried_to` and `how` cannot disagree: a name with no cluster
                # is not in `CARRIED`, and a carried one names its cluster.
                self.assertEqual(bool(r["carried_to"]), r["how"] in xnc.CARRIED)


class TheCommittedCensus(unittest.TestCase):
    """The committed shape, read straight from the two CSVs.

    No census run: the property here is what the committed files *say*, and
    running the tool to learn it would be a much more expensive way of asking
    the same question. Cheap enough to run in every suite, and it is the case
    whose output has to stay byte-identical, so it is the one that has to be
    asserted against the files rather than against a fixture.
    """

    @classmethod
    def setUpClass(cls):
        with open(CLUSTERS_CSV, newline="") as f:
            cls.old_rows = list(csv.DictReader(f))
        with open(NAMES_CSV, newline="") as f:
            cls.seeded = {r["cluster_key"].strip(): r["cluster_name"].strip()
                          for r in csv.DictReader(f) if r["cluster_key"].strip()}
        _names, cls.report = xrm.carry_names(cls.old_rows, cls.seeded,
                                             cls.old_rows)
        cls.cov = xnc.coverage(cls.old_rows, cls.seeded, cls.old_rows,
                               cls.report, xrm.CARRY_MIN_JACCARD)

    def test_every_names_file_row_has_a_coverage_record(self):
        self.assertEqual(len(self.cov), len(self.seeded))

    def test_the_committed_shape_prints_the_line_it_always_printed(self):
        # The constraint #851 left in place, and the reason the two additions
        # are clauses rather than two more counters: a sixth cell would change
        # this line on every run in the tree's transcripts. Its wording is
        # pinned as a literal, so a rewording of the tally fails here; its two
        # counts are derived from the committed CSVs. This is the one case
        # the literal can be checked against, because the counters in it are
        # the committed census's own -- a fixture would only pin a fixture.
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            xrm.print_carry(self.report, self.cov, "")
        unnamed = sum(1 for r in self.old_rows if not r["cluster_name"])
        self.assertEqual(buf.getvalue(), COMMITTED_TALLY.format(
            seeded=len(self.seeded), unnamed=unnamed))

    def test_no_name_is_unwritten_and_none_is_duplicated(self):
        # The property the whole exercise rests on: on the committed census
        # every hand name is `seeded`, so both tally clauses are empty and the
        # line is the one every transcript in the tree carries. If a name here
        # stopped being carried, `--check` would still pass and this would go
        # red, which is the direction the two halves are supposed to fail in.
        unwritten = [r["name"] for r in self.cov if r["how"] not in xnc.CARRIED]
        self.assertEqual(unwritten, [])
        self.assertEqual([r["name"] for r in self.cov if r["how"] == "duplicate"],
                         [])
        self.assertEqual(xnc.tally_clauses(self.cov, "x"), "")

    def test_no_name_is_written_to_two_clusters_of_the_committed_census(self):
        written = [r["cluster_name"] for r in self.old_rows if r["cluster_name"]]
        self.assertEqual(sorted(n for n in set(written)
                                if written.count(n) > 1), [])

    def test_the_record_shaped_census_still_prints_one_line(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            xrm.print_carry(self.report, self.cov, "")
        self.assertEqual(buf.getvalue().count("\n"), 1)


if __name__ == "__main__":
    unittest.main()
