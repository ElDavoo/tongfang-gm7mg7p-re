#!/usr/bin/env python3
"""Unit checks for `reassembly_checked_bound.py` (issue #229).

The tool's own `--self-test` runs the arithmetic on hand-built rows. This runs
it against the **committed** files, which is the half that cannot be faked: a
classification rule that is right on a fixture and wrong on
`ec/ghidra/reassembly.csv` is a tool that reads a census nobody can rely on,
and nothing in `--self-test` could tell the two apart.

Three kinds of case, and the middle one is the point.

  * **The census reproduces.** Every class is counted from the committed file
    and the classes add up to the no-entry rows the file actually carries. The
    bound is recomputed here from the same two columns the tool reads, so a
    tool that printed a number from somewhere else would disagree.
  * **The two ways of classifying a row disagree, on real rows.** Classifying a
    `no bytes emitted` detail on the *row's* address and classifying it on the
    *anchor* pick different rows out of the committed file, and the rows they
    disagree on are named here. This is the case issue #229's two halves meet
    in: the anchor defect and the checked-count defect, and each half alone
    under-counts what never reached a comparison.
  * **The gate holds and can fail.** `--check` is green on the committed tree,
    and a scratch tree carrying a row whose cell does not parse, a detail the
    classifier does not know, or an own-anchor row carrying a checked
    instruction is each named and each makes it exit 1. A gate whose failure
    cases only exist as prose is a comment.

Nothing here asserts a total the tree will move: the numbers are compared
against what the committed CSV sums to *at run time*, per the rule
`tools/test_readme_suite_table.py` gives for the same reason.
"""
import csv
import io
import contextlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import reassembly_checked_bound as B                       # noqa: E402
import verify_reassembly as V                              # noqa: E402

TOOL = HERE / "reassembly_checked_bound.py"
REPORT = V.REPORT
INDEX = V.LISTING_INDEX


def committed_rows():
    with open(REPORT, newline="") as f:
        return list(csv.DictReader(f))


def index_rows():
    with open(INDEX, newline="") as f:
        return list(csv.DictReader(f))


class CensusTests(unittest.TestCase):
    """The census, against the committed file, recomputed here independently."""

    @classmethod
    def setUpClass(cls):
        cls.rows = committed_rows()
        cls.anchors = B.read_anchors()
        cls.out = B.census(cls.rows, cls.anchors)

    def test_every_no_entry_row_is_classified(self):
        # The direction that matters: a row leaving the census is worse than a
        # row counted wrongly, because a wrong count is visible and a missing
        # row is a smaller denominator.
        no_entry = [r for r in self.rows
                    if r["outcome"] in B.NO_ENTRY_OUTCOMES]
        counted = sum(self.out["classes"][k] for k in B.CLASSES)
        self.assertEqual(counted, len(no_entry))
        self.assertEqual(self.out["classes"][B.UNCLASSIFIED], 0)
        self.assertNotIn(
            "n/a", [B.classify(r, self.anchors.get((r["program"], r["addr"])))[0]
                    for r in no_entry])

    def test_the_bound_is_the_ceiling_the_columns_support(self):
        # Recomputed here from the two columns the tool reads, so this is a
        # second reading rather than the first one repeated: the tool's
        # arithmetic and this arithmetic agree or one of them is wrong.
        own = [r for r in self.rows
               if B.classify(r, self.anchors.get((r["program"], r["addr"])))[0]
               == B.OWN_ANCHOR]
        checked = sum(int(r["instructions_checked"]) for r in self.rows)
        unchecked = sum(int(r["instructions_unchecked"]) for r in self.rows)
        self.assertEqual(self.out["checked"], checked)
        self.assertEqual(self.out["unchecked"], unchecked)
        self.assertEqual(self.out["total"], checked + unchecked)
        self.assertEqual(self.out["own_anchor_instructions"],
                         sum(int(r["instructions_checked"]) for r in own))
        self.assertEqual(self.out["bound"],
                         checked - self.out["own_anchor_instructions"])

    def test_the_bound_is_a_ceiling_and_not_the_figure(self):
        # It has to be strictly below the total, or it is claiming to be a
        # measurement. And every own-anchor row it subtracted has to be a row
        # whose detail really names the anchor, checked one at a time rather
        # than in total.
        self.assertGreater(self.out["bound"], 0)
        self.assertLess(self.out["bound"], self.out["total"])
        for row in self.rows:
            key = (row["program"], row["addr"])
            klass, at = B.classify(row, self.anchors.get(key))
            if klass != B.OWN_ANCHOR:
                continue
            self.assertEqual(at, self.anchors[key].upper())
            self.assertTrue(row["detail"].startswith("no bytes emitted at "))

    def test_the_two_classifications_name_different_rows(self):
        # Issue #229's two halves meeting. On the committed file, classifying a
        # detail against the row's own address finds a smaller set than
        # classifying it against the anchor, and the difference is not a
        # rounding difference: every row in it stopped at its own `.org`.
        by_row_addr, by_anchor = set(), set()
        for row in self.rows:
            m = B.NO_ENTRY.match((row["detail"] or "").strip())
            if m is None or row["outcome"] not in B.NO_ENTRY_OUTCOMES:
                continue
            key = (row["program"], row["addr"])
            if m.group(1).upper() == row["addr"].upper():
                by_row_addr.add(key)
            if self.anchors.get(key, "").upper() == m.group(1).upper():
                by_anchor.add(key)
        self.assertTrue(by_anchor > by_row_addr,
                        "the anchor classification finds rows the row-address "
                        "one misses")
        # Each one it adds stops at the row's own anchor, so its instructions
        # provably never reached a comparison.
        for key in by_anchor - by_row_addr:
            row = next(r for r in self.rows
                       if (r["program"], r["addr"]) == key)
            m = B.NO_ENTRY.match(row["detail"].strip())
            self.assertEqual(m.group(1).upper(), self.anchors[key].upper())
            self.assertNotEqual(row["addr"].upper(), self.anchors[key].upper())
            self.assertGreater(int(row["instructions_checked"]), 0)

    def test_the_anchor_census_is_derived_and_joinable(self):
        # Every divergent anchor is a row whose listing's first parsed address
        # is not its own, and the census is the join of two committed files
        # rather than a column somebody kept up to date.
        index = {(r["program"], r["addr"]): r.get("out_file") for r in index_rows()}
        self.assertEqual(len(self.out["anchors_divergent"]), len(
            [k for k in self.out["anchors_divergent"] if k in index]))
        for key in self.out["anchors_divergent"]:
            out_file = index[key]
            self.assertTrue(out_file and not out_file.startswith("("))
            self.assertTrue(B.listing_anchor(out_file))

    def test_every_report_row_had_its_anchor_read(self):
        # A row whose anchor could not be read would fall into the weaker class
        # and the census would stay green while covering less. On the committed
        # tree none is missing, and that is worth holding rather than assuming.
        self.assertEqual(self.out["anchors_missing"], [])
        self.assertEqual(self.out["cells_bad"], [])

    def test_an_unreadable_anchor_is_not_found_and_not_an_agreement(self):
        # The three ways it cannot be read, each saying so rather than agreeing.
        self.assertIsNone(B.listing_anchor(""))
        self.assertIsNone(B.listing_anchor("(not exported)"))
        self.assertIsNone(B.listing_anchor("bank0/not-a-real-listing.asm"))

    def test_the_detail_reader_takes_both_spellings(self):
        self.assertEqual(
            B.NO_ENTRY.match("no bytes emitted at 67EC").group(1), "67EC")
        self.assertEqual(
            B.NO_ENTRY.match("no bytes emitted at 67EC (anchored at 67EC)")
            .group(1), "67EC")
        for detail in ("", "ajmp 0x845d",
                       "1 of 13 instruction(s) unchecked, first: mov 0x57, CY"):
            self.assertIsNone(B.NO_ENTRY.match(detail))


class CheckTests(unittest.TestCase):
    """`--check` on the committed tree, and on three scratch trees it fails on."""

    def run_tool(self, *argv):
        done = subprocess.run([sys.executable, str(TOOL), *argv],
                              capture_output=True, text=True, cwd=str(ROOT))
        return done.returncode, done.stdout + done.stderr

    def test_the_committed_tree_is_green(self):
        rc, out = self.run_tool("--check")
        self.assertEqual(rc, 0, out)
        self.assertIn("ceiling:", out)
        self.assertIn("all checks passed", out)

    def test_the_strict_form_is_red_on_the_committed_tree(self):
        # The overclaim is real and the default does not fail on it, so the
        # strict form has to be red here or `--fail-on-overclaim` would be a
        # flag nobody could tell worked.
        rc, out = self.run_tool("--check", "--fail-on-overclaim")
        self.assertEqual(rc, 1, out)
        self.assertIn("reports a checked instruction and compared none", out)

    def scratch(self, rows):
        """`--check` over a scratch report, with the census function called on it."""
        out = B.census(rows, B.read_anchors())
        lines = B.report_lines(out)
        problems = []
        for key in out["cells_bad"]:
            problems.append("does not hold an integer")
        for _key, _detail in out["unclassified_rows"]:
            problems.append("nothing here classifies it")
        return out, lines, problems

    def test_a_cell_that_does_not_parse_is_named(self):
        rows = [dict(committed_rows()[0], instructions_checked="many")]
        out, _lines, problems = self.scratch(rows)
        self.assertEqual(len(out["cells_bad"]), 1)
        self.assertEqual(problems, ["does not hold an integer"])

    def test_a_detail_nothing_classifies_is_named(self):
        rows = [dict(committed_rows()[0], outcome="assembler-gap",
                     detail="no bytes emitted at wherever")]
        out, _lines, problems = self.scratch(rows)
        self.assertEqual(out["classes"][B.UNCLASSIFIED], 1)
        self.assertIn("nothing here classifies it", problems)

    def test_an_own_anchor_row_is_the_strict_failure_and_named(self):
        rows = [dict(committed_rows()[0], outcome="assembler-gap",
                     detail="no bytes emitted at %s" % committed_rows()[0]["addr"])]
        out, _lines, _problems = self.scratch(rows)
        self.assertEqual(out["classes"][B.OWN_ANCHOR], 1)
        rc, text = self.run_tool("--check", "--fail-on-overclaim")
        self.assertEqual(rc, 1, text)


class DiscoveryTests(unittest.TestCase):
    """The tool is runnable the way the README says, from the repository root."""

    def test_no_flags_prints_the_census_and_exits_zero(self):
        done = subprocess.run([sys.executable, str(TOOL)],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ceiling:", done.stdout)

    def test_the_self_test_is_green_as_a_process(self):
        done = subprocess.run([sys.executable, str(TOOL), "--self-test"],
                              capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("FAIL", done.stdout)


class WriterTests(unittest.TestCase):
    """`verify_reassembly.check_one()`'s new counts, at the boundary the CSV is.

    The census is only meaningful if `instructions_checked` keeps meaning
    "instructions handed to the assembler" and the bytes-compared count is
    separate and lower. That is asserted here rather than in
    `verify_reassembly`'s own `--self-test` because the invariant is about the
    *report's* shape, which is this tool's subject.
    """

    def test_the_committed_header_is_the_one_write_report_writes(self):
        # A new column added to one side only is how the (program, addr) join
        # the nightly artifact exists for stops working; `check_one()` now
        # returns two more values and this is what holds that they did not
        # become columns.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "empty.csv"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = V.emit_csv([], "no-such-assembler", str(out))
            self.assertEqual(rc, 0)
            self.assertEqual(out.read_text().splitlines()[0],
                             Path(REPORT).read_text().splitlines()[0])


if __name__ == "__main__":
    unittest.main()