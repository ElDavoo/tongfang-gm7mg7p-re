#!/usr/bin/env python3
"""The carry line's advice is scoped to the census the names file is anchored to
(issue #851).

`print_carry` is printed by every mode that builds a census, and its overlap
branch used to end `-- re-key annotations/xdata-cluster-names.csv if the name
moved` in every one of them. But the names file is anchored to the *committed*
census, and the two scratch runs the re-derivation recipe prescribes
(`annotations/xdata-06c2-06db-timers.md` §6b's `--export-ownership`, and
§4's `--no-eq-guard`) re-cluster, so their overlap carries are arithmetic over
ids that were never the committed ones. `--export-ownership` breaks 5 of the
hand names outright, so a line saying three names moved cannot be describing a
moved name.

The cases here are all in-process, with a synthetic carry report and no census
run: the property under test is which clause a shape gets, and that is a
function of the flags, not of the firmware. Reading committed text only -- no
image, no Ghidra, no network, no hardware.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import types
import unittest

HERE = Path(__file__).parent
EC = HERE.parent
spec = importlib.util.spec_from_file_location(
    "xdata_register_map", HERE / "xdata_register_map.py")
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

NAMES_REL = "annotations/xdata-cluster-names.csv"

# The clause the committed census has always printed, character for character.
# Pinned rather than computed, because "unchanged for the committed shape" is
# only checkable against a copy of the old string: recomputing it from
# `carry_advice("")` would pass on any rewording of the re-key request, which
# is the one thing a committed-shape transcript in the tree must not lose.
COMMITTED_TAIL = " -- re-key annotations/xdata-cluster-names.csv if the name moved"

# A census shape is the flags that move the ids off the committed pair, so the
# fixtures carry every one of them plus the ones that must not be counted. The
# threshold is the tool's own default rather than a literal, so moving
# `DEFAULT_THRESHOLD` turns "the committed shape" red here rather than quietly
# leaving this suite testing a threshold the tool no longer defaults to.
def shape(**kw):
    args = types.SimpleNamespace(threshold=xrm.DEFAULT_THRESHOLD,
                                 no_eq_guard=False, export_ownership=False,
                                 no_writer_axis=False)
    for k, v in kw.items():
        setattr(args, k, v)
    return args


# One report record per outcome `print_carry` can print a line for, in the
# order it prints them. The ids and names are the ones the §6b run really
# reports (see `annotations/xdata-06c2-06db-timers.md` §6b), so a reader can
# match the output to a committed transcript rather than to a shape invented
# for the test.
REPORT = [
    {"cluster_id": "main-ec-001", "name": "flags-8bit",
     "how": "seeded", "jaccard": 1.0, "from_key": "k1", "detail": ""},
    {"cluster_id": "main-ec-002", "name": "mode-oem-init",
     "how": "overlap", "jaccard": 0.97, "from_key": "kefb63d82f8c7", "detail": ""},
    {"cluster_id": "pd-003", "name": "pd-mask",
     "how": "exact", "jaccard": 1.0, "from_key": "k2", "detail": ""},
    {"cluster_id": "main-ec-009", "name": "tied-one",
     "how": "tie", "jaccard": 0.60, "from_key": "",
     "detail": "tied-one (main-ec-004) == tied-two (main-ec-005)"},
]


def stderr_of(report, shape_label):
    """`print_carry`'s stderr for one report under one census shape."""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        xrm.print_carry(report, shape_label)
    return buf.getvalue()


class TheShape(unittest.TestCase):
    """`census_shape`: which runs are the census the names file is anchored to.

    The anchor is the committed pair of CSVs -- the `==` guard on, no
    `--export-ownership`, `--threshold 0.5` -- which is what `--check`
    reproduces. Everything here is about which flag combination matches that
    and which does not.
    """

    def test_the_default_run_is_the_committed_census(self):
        self.assertEqual(xrm.census_shape(shape()), "")

    def test_each_re_clustering_flag_is_named(self):
        # Three flags, and they are the predicate in both directions: each one
        # alone is enough to put the run off the anchor, so each one alone has
        # to reach the line. A flag missing from this set is one whose run will
        # still be told to re-key a file it cannot judge.
        self.assertEqual(xrm.census_shape(shape(export_ownership=True)),
                         "--export-ownership")
        self.assertEqual(xrm.census_shape(shape(no_eq_guard=True)),
                         "--no-eq-guard")
        self.assertEqual(xrm.census_shape(shape(threshold=0.6)),
                         "--threshold 0.6")

    def test_combined_flags_are_named_in_a_stated_order(self):
        # `census_shape`'s docstring says the order is `main()`'s own
        # declaration order, so a reader can check it against the parser rather
        # than having to trust it. Asserted in that order, and in the reverse,
        # because a set would pass on a reordering that changes the line.
        self.assertEqual(
            xrm.census_shape(shape(threshold=0.6, export_ownership=True,
                                   no_eq_guard=True)),
            "--threshold 0.6 --no-eq-guard --export-ownership")
        self.assertEqual(
            xrm.census_shape(shape(export_ownership=True, no_eq_guard=True,
                                   threshold=0.6)),
            "--threshold 0.6 --no-eq-guard --export-ownership")

    def test_the_writer_axis_flag_is_not_part_of_the_shape(self):
        # `build()` calls `components(groups[g], threshold)` with the writer
        # axis on unconditionally, and the flag's own help scopes it to
        # `--threshold-sweep` -- so a census built with it clusters exactly as a
        # default run does. Naming it would put a flag on a carry line that
        # never moved a key, which is the overclaim this change exists to stop.
        self.assertEqual(xrm.census_shape(shape(no_writer_axis=True)), "")

    def test_a_threshold_that_merges_to_the_default_is_the_committed_shape(self):
        # 0.50 and 0.5 are the same floor, so a run that spells it the other
        # way is still the committed census. Comparing to the constant rather
        # than to the string keeps that from depending on how argparse printed
        # it.
        self.assertEqual(xrm.census_shape(shape(threshold=0.50)), "")


class TheAdvice(unittest.TestCase):
    """`carry_advice`: the clause, on both sides of the anchor.

    The committed side is pinned to the old string. The other side has to say
    three things or it is still a re-key request in different words: which flag
    took the run off the anchor, which file is anchored, and that the line is
    not advising a re-key.
    """

    def test_the_committed_clause_is_byte_identical_to_the_old_string(self):
        # Every committed-shape transcript in the tree carries this clause, so
        # changing it would invalidate those transcripts for no gain. The
        # committed census is the one run where the re-key request is correct:
        # its keys are the committed ones, so a name arriving by overlap is a
        # name whose membership moved.
        self.assertEqual(xrm.carry_advice(""), COMMITTED_TAIL)

    def test_the_committed_clause_is_a_re_key_request(self):
        self.assertIn("-- re-key ", xrm.carry_advice(""))
        self.assertIn(NAMES_REL, xrm.carry_advice(""))

    def test_a_non_committed_run_is_not_told_to_re_key(self):
        for label in ("--export-ownership", "--no-eq-guard", "--threshold 0.6"):
            with self.subTest(shape=label):
                advice = xrm.carry_advice(label)
                self.assertNotIn("-- re-key ", advice)
                self.assertIn(label, advice)
                self.assertIn(NAMES_REL, advice)
                self.assertIn("not a re-key request", advice)

    def test_a_non_committed_clause_names_the_anchor_it_is_not(self):
        # The clause has to say what the file *is* anchored to, not only that
        # this run is not it. Without that half a reader is left to supply the
        # census themselves, which is the inference the issue is about.
        self.assertIn("anchored to the committed one", xrm.carry_advice("--no-eq-guard"))

    def test_the_clause_claims_nothing_about_the_names_being_right(self):
        # Calibrated: the carries are arithmetic over a different clustering.
        # The clause must not imply the names are wrong, gone, or invalid --
        # only that this run cannot judge them. "arithmetic over a different
        # clustering" is what was measured; "absent" would not be.
        advice = xrm.carry_advice("--export-ownership")
        self.assertIn("arithmetic over a different clustering", advice)
        for word in ("wrong", "gone", "invalid", "stale", "absent", "obsolete"):
            self.assertNotIn(word, advice)


class TheLine(unittest.TestCase):
    """`print_carry` end to end, on a synthetic report.

    The line is where a reader actually reads the advice, so the split between
    the mode-independent facts and the mode-dependent one is asserted on the
    printed output rather than on the two helpers' return values.
    """

    def test_the_two_shapes_differ_only_in_the_overlap_tails(self):
        committed = stderr_of(REPORT, "")
        other = stderr_of(REPORT, "--export-ownership")
        self.assertEqual(committed.count("\n"), other.count("\n"))
        # The tally and the tie line have to be identical strings, and the
        # overlap line identical up to its tail. Built by replacing rather than
        # by comparing a prefix, so this fails if the *whole* line changed
        # rather than only the clause appended to it.
        self.assertEqual(
            other.replace(xrm.carry_advice("--export-ownership"),
                          xrm.carry_advice("")),
            committed)

    def test_the_tally_line_is_the_same_in_both_shapes(self):
        # The tally is a fact about this run's own report -- four names, one of
        # them carried by overlap -- and it does not stop being true because
        # the run used a flag. Making it mode-dependent would lose a fact for
        # no gain, so it is asserted identical, not merely similar.
        for report, want in ((REPORT, "carried by overlap 1"),
                             (REPORT[:1], "carried by overlap 0")):
            with self.subTest(want=want):
                self.assertIn(want, stderr_of(report, ""))
                self.assertIn(want, stderr_of(report, "--export-ownership"))

    def test_the_tie_line_is_the_same_in_both_shapes(self):
        line = ("    main-ec-009 is claimed by two names at Jaccard 0.60 "
                "(tied-one (main-ec-004) == tied-two (main-ec-005)); not "
                "carried by this method\n")
        self.assertIn(line, stderr_of(REPORT, ""))
        self.assertIn(line, stderr_of(REPORT, "--export-ownership"))

    def test_only_the_overlap_line_mentions_the_names_file(self):
        # A `none` is "this rule did not fire", not a name that went away, and
        # it prints no line at all; `seeded` and `exact` are not claims that
        # moved. So the names file is named only where the advice is.
        committed = stderr_of(REPORT, "")
        self.assertEqual(committed.count(NAMES_REL), 1)
        self.assertEqual(stderr_of(REPORT, "--export-ownership").count(NAMES_REL), 1)

    def test_a_seeded_run_prints_the_tally_and_nothing_else(self):
        out = stderr_of(REPORT[:1], "")
        self.assertIn("names: seeded 1, exact 0, carried by overlap 0, "
                      "tied, not carried 0, with no name 0", out)
        self.assertEqual(out.count("\n"), 1)


if __name__ == "__main__":
    unittest.main()
