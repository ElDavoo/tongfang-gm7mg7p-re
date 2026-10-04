#!/usr/bin/env python3
"""Offline checks for check_capture_marks.py: refusals on a scratch index, and
the committed one green.

The tool holds one property of `evidence/ec-watch/` that nothing else on the
tree reads: **every committed capture says, in the index, whether a timing
claim over it is mechanical or inferred.** A refusal nothing checks is a
refusal with no teeth, so what is pinned below is that each of the four
refusals fires, on a scratch index built for it -- the committed tree cannot
show any of them, because on it they are all satisfied.

The committed-tree case is a **tripwire, not a floor**: it asserts emptiness
(no capture without a row, no count disagreement, no row for a file that is
not there), so the corpus grows without turning a case red while a capture
that loses its row does. Nothing here counts rows or captures, for the reason
`CLAUDE.md` gives and `tools/test_readme_suite_table.py` already states: a
test that holds a count of the tree is a value every merge has to edit.

**What these cases are not.** They read a directory listing and a markdown
table. No EC is opened, no capture is taken, no register is read and no mark
is typed; the files below are a few lines of text written by the case itself.
And they say nothing about whether a capture *should* have had marks -- a
capture legitimately has none, which is why the rule is for a recorded reason
and not for marks. `docs/findings/capture-mark-provenance.md` is the
write-up.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
# Loaded by path for the reason `test_check_capture_names.py` loads its tool
# the same way, and the directory is the sys.path entry the tool's own
# `from check_capture_claims import WATCH` resolves against.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_capture_marks', HERE / 'check_capture_marks.py')
ccm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccm)

# A capture with one MARK row and one without, spelled as the difference
# rather than as a pair of good names, so a case that adds a third file has to
# say which side of the line it is on.
MARKED = "2026-09-24-06c2-06db-perturb-linux.csv"
UNMARKED = "2026-09-18-profile-switch-0700-07ff.csv"
ABSENT = "2026-01-01-never-committed.csv"

ONE_MARK = ("ts,addr,old,new\n"
            "2026-01-01T00:00:00.000+01:00,MARK,,settled\n"
            "2026-01-01T00:00:02.000+01:00,0x0700,0x00,0x01\n")
NO_MARK = ("ts,addr,old,new\n"
           "2026-01-01T00:00:02.000+01:00,0x0700,0x00,0x01\n")
# A capture whose `#` block names the writer and whose data rows follow it, so
# a case can show the `#` filter is what lets the header through rather than
# the file having none.
WITH_COMMENTS = ("# ec/tools/ec_timer_capture.py, read-only\n"
                 "# baseline 2026-01-01T00:00:00.000+01:00: 0x0700=0x00\n"
                 "ts,addr,old,new\n"
                 "2026-01-01T00:00:02.000+01:00,0x0700,0x00,0x01\n")

HEADER = ("| capture | `MARK` rows | why none, if none |\n"
          "|---|---|---|\n")


class ScratchIndex(unittest.TestCase):
    """A throwaway capture root and index, and the check over them."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.index = os.path.join(self.root, "README.md")

    def capture(self, name, text=NO_MARK):
        """A capture at `name` under the scratch root."""
        with open(os.path.join(self.root, name), "w", encoding="utf-8") as f:
            f.write(text)
        return name

    def rows(self, body):
        """The rows `index_rows()` reads out of a table carrying `body`."""
        return ccm.index_rows(self.text_of(body))

    def text_of(self, body):
        """A whole index carrying `body` under the table's header."""
        with open(self.index, "w", encoding="utf-8") as f:
            f.write("# Evidence\n\n" + HEADER + body)
        with open(self.index, encoding="utf-8") as f:
            return f.read()

    def check(self, body, csvs):
        """(refusals, stderr) for a table carrying `body` over `csvs`."""
        problems = ccm.check(self.root,
                             ccm.index_rows(self.text_of(body)), csvs)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            ccm.report(problems, "scratch")
        return problems, err.getvalue()


class TheFourRefusals(ScratchIndex):
    """Each mistake refused, and refused in its own words."""

    def test_a_capture_with_no_row_is_refused(self):
        # The refusal the tool exists for. Every other case below is about a
        # row that is present; this is the one where the index says nothing,
        # so a reader cannot tell a mechanical placement from an inferred one.
        self.capture(UNMARKED)
        problems, err = self.check(f"| `{UNMARKED}` | 0 | a real reason |\n",
                                   [UNMARKED])
        self.assertEqual(problems, [])

        self.capture(MARKED, ONE_MARK)
        problems, err = self.check(f"| `{UNMARKED}` | 0 | a real reason |\n",
                                   [MARKED, UNMARKED])
        self.assertEqual(len(problems), 1)
        self.assertIn(MARKED, problems[0])
        self.assertIn("no row in the index's mark table", problems[0])

    def test_a_count_that_disagrees_with_the_file_is_refused_by_both_numbers(self):
        # The staleness direction a hand-typed table drifts into, and the only
        # refusal that can catch it in both directions at once: the index
        # saying more than the file holds, and less.
        self.capture(MARKED, ONE_MARK)
        for said, held in ((0, 1), (5, 1)):
            problems, _ = self.check(
                f"| `{MARKED}` | {said} | a reason |\n", [MARKED])
            self.assertEqual(len(problems), 1, problems)
            self.assertIn(f"the index says {said} MARK row(s) and the file "
                          f"holds {held}", problems[0])

    def test_a_zero_row_with_an_empty_reason_is_refused(self):
        # What makes the count column worth having. A checker holding counts
        # alone would pass this corpus, which is right about the arithmetic
        # and silent about the one thing a reader needs.
        self.capture(UNMARKED)
        problems, _ = self.check(f"| `{UNMARKED}` | 0 | |\n", [UNMARKED])
        self.assertEqual(len(problems), 1)
        self.assertIn("empty reason cell", problems[0])
        # And the reason is not required where there is something to place --
        # a marked capture's row needs no explanation of an absence.
        self.capture(MARKED, ONE_MARK)
        problems, _ = self.check(f"| `{MARKED}` | 1 | |\n", [MARKED])
        self.assertEqual(problems, [])

    def test_a_row_for_a_file_that_is_not_on_disk_is_refused(self):
        # A capture that was renamed, merged or dropped leaves its row behind,
        # and the row is then a claim about a file nobody can open. The root
        # holds a capture the table says nothing about as well, so this case
        # asks for the stale row by name rather than for a count.
        self.capture(UNMARKED)
        self.capture(MARKED, ONE_MARK)
        problems, _ = self.check(f"| `{ABSENT}` | 0 | a real reason |\n"
                                 f"| `{MARKED}` | 1 |\n"
                                 f"| `{UNMARKED}` | 0 | a real reason |\n",
                                 [MARKED, UNMARKED])
        stale = [p for p in problems if ABSENT in p]
        self.assertEqual(len(stale), 1, problems)
        self.assertIn("no such file is on disk", stale[0])

    def test_a_cell_that_is_not_a_count_is_refused_rather_than_skipped(self):
        # A row this tool cannot read is a row that records nothing, and
        # skipping it would leave the corpus looking conformant. The
        # `mark_count` disagreement below is a *count* refusal; this one is
        # the row being unreadable in the first place.
        self.capture(MARKED, ONE_MARK)
        problems, _ = self.check(f"| `{MARKED}` | some | a reason |\n", [MARKED])
        self.assertEqual(len(problems), 1)
        self.assertIn("not a count", problems[0])

    def test_two_rows_for_one_capture_are_refused(self):
        # Which of the two a reader is to believe is not stated by the table,
        # so the corpus is ambiguous rather than merely stale. Both rows here
        # agree with the file, so the ambiguity is the only thing wrong: a
        # case whose duplicate rows also disagreed would be testing the count
        # refusal twice over.
        self.capture(MARKED, ONE_MARK)
        problems, _ = self.check(
            f"| `{MARKED}` | 1 | first |\n| `{MARKED}` | 1 | second |\n",
            [MARKED])
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("rows in the index's mark table", problems[0])


class WhatTheCountReads(ScratchIndex):
    """`mark_count`, over the row shapes a committed capture really has.

    The rule has to agree with the readers' or the index is held to a number
    the graders would not agree with, so the cases are drawn from the shapes
    the tree holds: a plain change log, one with a `#` block naming its
    writer, and one with a MARK row written before the header is seen.
    """

    def test_the_count_is_the_marks_and_not_the_rows(self):
        self.capture(UNMARKED, ONE_MARK)
        self.assertEqual(ccm.mark_count(os.path.join(self.root, UNMARKED)), 1)
        self.capture(MARKED, NO_MARK)
        self.assertEqual(ccm.mark_count(os.path.join(self.root, MARKED)), 0)

    def test_a_hash_block_and_a_header_are_not_marks(self):
        # `2026-09-24-06c2-06db-sweep-linux.csv` opens with a `#` block whose
        # words name a mark-bearing writer, and its baseline line is not a
        # mark either. A count that read either would report a capture with no
        # marks as holding some.
        self.capture(MARKED, WITH_COMMENTS)
        self.assertEqual(ccm.mark_count(os.path.join(self.root, MARKED)), 0)

    def test_a_derived_summary_is_counted_over_its_own_schema(self):
        # `2026-09-18-ac-plugin-sweep-summary.csv` is `addr,change_count,…`
        # with no `ts` column at all. A mark is `row[1]`, so a file whose
        # second column is a count cannot hold one by this rule -- which is
        # the right answer for the right reason, and the index's reason cell
        # says why rather than leaving it to look like an accident.
        self.capture(MARKED, "addr,change_count,first_old,last_new\n"
                             "0x07C4,2,0x08,0x38\n")
        self.assertEqual(ccm.mark_count(os.path.join(self.root, MARKED)), 0)

    def test_an_empty_capture_counts_zero_rather_than_raising(self):
        # A capture committed before anything was written to it, which the
        # census has to report as a file that exists.
        self.capture(MARKED, "")
        self.assertEqual(ccm.mark_count(os.path.join(self.root, MARKED)), 0)


class TheTable(ScratchIndex):
    """How the index's own markdown is read.

    A parser that finds its table by position is a parser that breaks when a
    bullet above the table grows, so the header is what identifies it -- the
    same discipline `resolve()` applies to a citation line in
    `measure_mark_provenance.py`, and the same reason.
    """

    def test_the_table_is_found_by_its_header_and_not_its_position(self):
        rows = self.rows(f"| `{MARKED}` | 1 | a reason |\n")
        self.assertEqual(rows, [ccm.Row(MARKED, 1, "a reason")])

    def test_a_table_ends_at_the_first_line_that_is_not_a_row(self):
        rows = self.rows(f"| `{MARKED}` | 1 | a reason |\n"
                         "\n"
                         "Some prose after the table.\n"
                         f"| `{UNMARKED}` | 0 | another |\n")
        self.assertEqual(rows, [ccm.Row(MARKED, 1, "a reason")])

    def test_another_three_column_table_is_not_read_as_this_one(self):
        # The index holds other tables. One whose first column is not
        # `capture` is not this tool's, and reading it would produce rows
        # naming files that do not exist.
        with open(self.index, "w", encoding="utf-8") as f:
            f.write("# Evidence\n\n"
                    "| suite | what it stands in for |\n"
                    "|---|---|\n"
                    "| `ec/tools/test_x.py` | unrelated |\n\n"
                    + HEADER + f"| `{MARKED}` | 1 | a reason |\n")
        with open(self.index, encoding="utf-8") as f:
            self.assertEqual(ccm.index_rows(f.read()),
                             [ccm.Row(MARKED, 1, "a reason")])

    def test_a_row_of_the_wrong_width_is_refused_rather_than_indexed(self):
        # A two-cell row under a three-column header. Padding it would invent
        # a reason cell the index never wrote, and indexing `cells[2]` would
        # end the run in an IndexError naming a list rather than the line that
        # caused it -- so the width is carried into the row and refused by it.
        self.capture(MARKED, ONE_MARK)
        rows = self.rows(f"| `{MARKED}` | 1 |\n")
        self.assertEqual(rows[0].capture, MARKED)
        self.assertEqual(rows[0].marks, "2 cells, not 3")
        problems, _ = self.check(f"| `{MARKED}` | 1 |\n", [MARKED])
        self.assertEqual(len(problems), 1)
        self.assertIn("not a count", problems[0])

    def test_a_missing_header_is_distinguished_from_an_empty_table(self):
        # The two failures `main()` reports separately: nothing was read, or
        # every row was. Reading both as "no rows" would let a renamed column
        # pass as a corpus that needs no work.
        self.assertTrue(ccm.table_header_found(HEADER))
        self.assertFalse(ccm.table_header_found("| a | b |\n|---|---|\n"))
        self.assertTrue(ccm.table_header_found(HEADER))
        self.assertEqual(ccm.index_rows("no table here\n"), [])

    def test_the_separator_row_is_not_read_as_a_capture(self):
        rows = self.rows(f"| `{MARKED}` | 1 | a reason |\n")
        self.assertNotIn("", [r.capture for r in rows])

    def test_a_code_span_around_the_filename_and_count_is_read_through(self):
        rows = self.rows(f"| `{MARKED}` | `1` | a reason |\n")
        self.assertEqual(rows, [ccm.Row(MARKED, 1, "a reason")])


class TheCaptureRoot(ScratchIndex):
    """`captures()`: the `.csv` set the rule is over, and the `.txt` files it
    reports as outside it.

    The scope is `*.csv`, so a `.txt` capture raises no refusal -- but
    "outside the rule" must not read the same as "checked and conformant",
    which is why `captures()` returns them rather than filtering them away.
    """

    def test_a_txt_capture_is_reported_rather_than_counted_as_a_csv(self):
        self.capture(MARKED, ONE_MARK)
        with open(os.path.join(self.root, "2026-09-23-0751-isolation.txt"),
                  "w", encoding="utf-8") as f:
            f.write("# a console log, not a capture in the grader's schema\n")
        csvs, txts = ccm.captures(self.root)
        self.assertEqual((csvs, txts), ([MARKED],
                                        ["2026-09-23-0751-isolation.txt"]))

    def test_a_root_that_cannot_be_listed_answers_none_rather_than_empty(self):
        # The vacuity guard. "Every capture conforms" over a root nobody read
        # is a checker that passed by checking nothing, which is the §14b
        # defect `run-tests.sh` guards at the suite level.
        missing = os.path.join(tempfile.mkdtemp(), "ec-watch")
        self.addCleanup(shutil.rmtree, os.path.dirname(missing))
        self.assertIsNone(ccm.captures(missing))

    def test_a_directory_in_the_root_is_not_a_capture(self):
        # `os.path.isfile`, the same predicate `carried_by()` uses, so the set
        # here is the set a reader would open.
        os.mkdir(os.path.join(self.root, "2026-09-24-nested"))
        self.capture(MARKED, ONE_MARK)
        self.assertEqual(ccm.captures(self.root)[0], [MARKED])


class TheCommittedIndex(unittest.TestCase):
    """The real thing: every committed capture is accounted for.

    **These assert emptiness, not a figure.** No count of captures and no
    count of rows appears in either, so committing a new capture does not
    turn a case red -- while committing one without a row, or with a stale
    count, does. That asymmetry is the cost written down rather than designed
    away: the second is a refusal, and a refusal that nothing can fail is not
    one.
    """

    def setUp(self):
        self.census = ccm.captures(ccm.ROOT)
        with open(ccm.INDEX, encoding="utf-8") as f:
            self.text = f.read()
        self.rows = ccm.index_rows(self.text)

    def test_the_capture_root_could_be_listed_at_all(self):
        self.assertIsNotNone(
            self.census,
            f"{ccm.WATCH}/ could not be listed, so nothing was checked. That "
            f"is a broken census, not an empty one.")

    def test_the_index_carries_the_table(self):
        self.assertTrue(ccm.table_header_found(self.text),
                        "evidence/README.md carries no mark table, so every "
                        "capture below is unrecorded rather than conformant")

    def test_no_capture_is_missing_its_row_and_no_row_names_a_missing_file(self):
        # The two directions of one join, which is what "every committed
        # capture says" means. Walked rather than counted, so the corpus is
        # free to grow.
        named = {r.capture for r in self.rows}
        on_disk = set(self.census[0])
        self.assertEqual(sorted(on_disk - named), [],
                         "a committed capture with no row in the index's mark "
                         "table, so nothing records whether a timing claim "
                         "over it is mechanical or inferred")
        self.assertEqual(sorted(named - on_disk), [],
                         "the index has a row for a capture that is not on "
                         "disk, so the row is a claim about a file nobody can "
                         "open")

    def test_every_row_is_readable_and_every_count_agrees_with_its_file(self):
        self.assertEqual(ccm.check(ccm.ROOT, self.rows, self.census[0]), [])

    def test_every_capture_holding_none_records_a_reason(self):
        # Asserted over the files rather than over the table, so it is the
        # corpus that is checked and not the table's own arithmetic.
        for name in self.census[0]:
            with self.subTest(capture=name):
                if ccm.mark_count(os.path.join(ccm.ROOT, name)):
                    continue
                reasons = [r.reason for r in self.rows if r.capture == name]
                self.assertEqual(len(reasons), 1)
                self.assertTrue(reasons[0].strip(),
                                f"{name} holds no MARK row and the index "
                                f"records no reason, so a reader cannot tell "
                                f"whether the absence is deliberate")


class TheCommandLine(unittest.TestCase):
    """`--check` and the default run, over a scratch tree.

    The tool is both a census and a refusal and the two have different
    standing, so the exit code is part of what it says: read by hand the run
    prints the census and the refusals and exits 0, and only `--check` makes a
    refusal the verdict. Pinned because that asymmetry is a decision rather
    than an accident, and an exit code nobody looks at is one nobody relies
    on.
    """

    def scratch(self, body, csvs):
        """A root and index the patched `main()` will read."""
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        for name in csvs:
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write(ONE_MARK if name == MARKED else NO_MARK)
        index = os.path.join(root, "README.md")
        with open(index, "w", encoding="utf-8") as f:
            f.write("# Evidence\n\n" + HEADER + body)
        return root, index

    def run_main(self, root, index, *argv):
        """(exit code, stdout, stderr) for `main()` over a scratch tree."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(ccm, 'ROOT', root), \
                mock.patch.object(ccm, 'INDEX', index), \
                mock.patch.object(sys, 'argv',
                                  ['check_capture_marks.py', *argv]), \
                contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            return ccm.main(), out.getvalue(), err.getvalue()

    def test_check_fails_on_an_unrecorded_capture(self):
        root, index = self.scratch(f"| `{MARKED}` | 1 |\n", [MARKED, UNMARKED])
        rc, _, err = self.run_main(root, index, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("no row in the index's mark table", err)

    def test_check_fails_on_a_missing_table(self):
        root, index = self.scratch("", [MARKED])
        with open(index, "w", encoding="utf-8") as f:
            f.write("# Evidence\n\nno table here\n")
        rc, _, err = self.run_main(root, index, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("carries no mark table", err)

    def test_check_fails_on_a_root_that_cannot_be_listed(self):
        missing = os.path.join(tempfile.mkdtemp(), "ec-watch")
        self.addCleanup(shutil.rmtree, os.path.dirname(missing))
        root, index = self.scratch("", [])
        rc, _, err = self.run_main(missing, index, "--check")
        self.assertEqual(rc, 1)
        self.assertIn("broken census, not an empty one", err)

    def test_the_default_run_prints_the_census_and_exits_zero(self):
        # The standing, in both halves: a refusal it has printed is still not
        # the verdict unless `--check` asked for it, so the tool is useful
        # read by hand -- which is how a writer checks a capture it is about
        # to commit.
        root, index = self.scratch("", [MARKED, UNMARKED])
        rc, out, err = self.run_main(root, index)
        self.assertEqual(rc, 0)
        self.assertIn("2 capture(s)", out)
        self.assertIn("no row in the index's mark table", err)

    def test_check_passes_over_the_committed_index(self):
        rc, out, err = self.run_main(ccm.ROOT, ccm.INDEX, "--check")
        self.assertEqual(rc, 0, err)
        self.assertIn("agrees with the index", out)
        # And the `.txt` captures are named as out of scope rather than
        # passed over in silence, which is the half a reader cannot see.
        self.assertIn("outside this rule's scope", out)


if __name__ == '__main__':
    unittest.main()