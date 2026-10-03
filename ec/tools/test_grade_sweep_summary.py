#!/usr/bin/env python3
"""The refusals and the classification of `grade_sweep_summary.py`, offline.

Stands in for reading a per-address sweep summary the way
`evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv` has to be read: one
row per address, the change total in a `change_count` column, and no word in
the format for a byte that moved and came back. Nothing here opens an EC,
reads a register back, or re-applies anything to a capture a human took. The
hand-built refusals are written into `tempfile.TemporaryDirectory()`s rather
than committed beside the two fixtures that grade cleanly, so that a fixture
in the directory is by definition one some run reads -- the same reason
`test_grade_gpu_door.py` keeps its refused captures out of its own.

The reader imports `check_capture_claims`, so this directory has to be the
import root. `unittest discover -s ec/tools` already puts it there, which is
how `tools/run-tests.sh` runs this file; the insert below is so the suite also
runs from an editor or a bare `python3` on its own.
"""
import contextlib
import csv
import importlib.util
import io
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'summary', HERE / 'grade_sweep_summary.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)

TESTDATA = HERE / 'testdata'
COMMITTED = summary.SUMMARY

# The fixtures, by the branch each one reaches. `FIXTURES` is what
# `FixtureCoverageTests` holds against the directory, so a fixture added
# without a case reaching it fails rather than sitting there looking covered.
MOVED_AND_RETURNED = str(
    TESTDATA / 'sweep-summary-example-moved-and-returned.csv')
UNRECONCILED = str(TESTDATA / 'sweep-summary-example-unreconciled.csv')
CHANGE_LOG = str(TESTDATA / 'sweep-summary-example-change-log.csv')
FIXTURES = (MOVED_AND_RETURNED, UNRECONCILED, CHANGE_LOG)

# The phrases a row that moved must never be described with. `net` is not in
# the list for the reason the middle of `classify()` is a refusal: the net is
# an endpoint statistic and this tool prints it *beside* the count, never
# instead of it.
NOT_FOR_A_MOVER = ('held', 'unchanged', 'quiet')


def run(*args):
    """(exit code, stdout, stderr) for one invocation of the tool."""
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = summary.main([str(a) for a in args])
    return rc, buf.getvalue(), err.getvalue()


def write_summary(directory, name, rows, header=()):
    """A file in this shape, built from `(addr, count, first, last)` tuples.

    The `#` block is written first and the header second, which is the order
    every reader of this format has to cope with: `csv.DictReader` takes the
    first line it is given as the fieldnames unless the comment block is
    dropped before the header is read, which is the one parse
    `check_capture_claims.capture_lines` is imported for. `header` is empty in
    most of the cases below because the `#` block is not what they are about;
    the one that is writes it.
    """
    lines = [f"# {line}" for line in header]
    lines.append("addr,change_count,first_old,last_new")
    lines += [f"{a},{c},{f},{l}" for a, c, f, l in rows]
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


def committed_rows():
    """The committed summary's `(addr, count, first, last)` rows, read here.

    Parsed by this file rather than taken from the tool, so an expectation
    about the committed file is a fact about the file and not a second run of
    the code under test. `capture_lines` is the reader both use, and there is
    no second `#` filter to fall out of step.
    """
    with open(COMMITTED, newline="", encoding="utf-8") as handle:
        lines = [line for line in handle if not line.lstrip().startswith("#")]
    return [(row["addr"], int(row["change_count"]), row["first_old"],
             row["last_new"]) for row in csv.DictReader(lines)]


class CommittedSummaryTests(unittest.TestCase):
    """The one committed capture in this shape, read the way issue #276 did not.

    The properties here are asserted over the file rather than against a count
    of its rows: a count would move on the next capture a human commits, and
    the claim worth holding -- a byte that moved is never described as one
    that held -- is a claim about every row rather than about how many there
    are.
    """

    def setUp(self):
        self.rows = committed_rows()
        self.rc, self.report, self.err = run(COMMITTED)
        self.assertEqual(self.rc, 0, self.report + self.err)

    def line_for(self, address):
        """The report's one line about an address, or '' when it has none."""
        return next((line for line in self.report.splitlines()
                     if line.strip().startswith(address)), '')

    def test_a_row_with_changes_is_never_described_as_held(self):
        returned = [row for row in self.rows
                    if row[1] > 0 and row[2] == row[3]]
        self.assertTrue(
            returned,
            'no row in the committed summary has equal endpoints and a '
            'non-zero change_count, so the refusal this tool exists for would '
            'be asserted against an empty set and would pass whatever the '
            'classifier printed.')
        for address, count, _first, _last in returned:
            with self.subTest(address=address):
                line = self.line_for(address)
                self.assertTrue(line, f'no report line for {address}')
                for word in NOT_FOR_A_MOVER:
                    self.assertNotIn(
                        word, line.lower(),
                        f'{address} moved {count} time(s) and its report line '
                        f'reads {line!r}, which is the #276 reading this tool '
                        'is here to refuse')

    def test_the_07C6_row_is_read_as_a_move_and_returned(self):
        # Its own case rather than one more subtest: this is the row issue
        # #276's retraction is about, and a future edit that broke the general
        # rule would be caught by the property above with a different address
        # in the failure message than the one the repository discusses.
        row = next((r for r in self.rows if r[0] == '0x07C6'), None)
        self.assertIsNotNone(row, 'the committed summary has no 0x07C6 row')
        self.assertGreater(row[1], 0)
        self.assertEqual(row[2], row[3])
        line = self.line_for('0x07C6')
        self.assertIn('moved', line.lower())
        self.assertIn('returned to its first recorded value', line)
        for word in NOT_FOR_A_MOVER:
            self.assertNotIn(word, line.lower())

    def test_a_row_whose_endpoints_differ_reads_as_a_net(self):
        differing = [row for row in self.rows if row[2] != row[3]]
        self.assertTrue(differing, 'no row in the committed summary has two '
                                   'endpoints that differ')
        for address, _count, first, last in differing:
            with self.subTest(address=address):
                self.assertIn('moved, net', self.line_for(address))

    def test_the_column_total_is_the_sum_of_the_rows_own_counts(self):
        # The figure the reconciliation prints is checked against the file,
        # so a change to the column is a change to the report rather than a
        # stale number in a test.
        total = sum(row[1] for row in self.rows)
        self.assertIn(f"the change_count column sums to {total}", self.report)

    def test_both_reconciliation_figures_are_reported_and_they_differ(self):
        # The header's figure is read out of the file's own `#` block rather
        # than written here, so this does not restate a number a commit could
        # move; what it holds is that the report carries both and does not
        # pick one.
        with open(COMMITTED, encoding="utf-8") as handle:
            comments = "".join(line for line in handle if line.startswith("#"))
        stated = [m.group(1) for m in re.finditer(r"\b(\d[\d,]*)-row\b", comments)]
        self.assertTrue(stated, 'the committed summary states no source-log '
                                'row count in its `#` block')
        self.assertIn(f"the header states the source log had "
                      f"{int(stated[0].replace(',', ''))} row(s)", self.report)
        self.assertIn('they do not reconcile', self.report)
        # Not adjudicated. A tool that chose between the two would be reporting
        # a fact about the 32,499-row log, which is not in this tree.
        self.assertIn('not settled here', self.report)

    def test_the_reference_point_is_named_and_worked_on_a_row_of_the_file(self):
        # The worked row is picked out of the file here rather than named in
        # the tool: a tool must not carry one file's address, and the rule the
        # tool uses -- the first single-change row whose endpoints differ --
        # is re-derived here from the same rows the tool read.
        self.assertIn('what first_old is measured against', self.report)
        self.assertIn("the value at the window's first sweep", self.report)
        self.assertIn('pre-image', self.report)
        example = next((row for row in self.rows
                        if row[1] == 1 and row[2] != row[3]), None)
        self.assertIsNotNone(example, 'the committed summary has no '
                                     'single-change row with two endpoints '
                                     'that differ')
        self.assertIn(example[0], self.report)
        self.assertIn(example[2], self.report)
        self.assertIn(example[3], self.report)

    def test_absence_is_stated_as_not_found_and_not_as_never_written(self):
        self.assertIn('not found to move in this file', self.report)
        self.assertIn('does not', self.report)
        # The four things the format has no word for are named, so a reader
        # is told rather than left to discover that the net is all there is.
        for missing in ('intermediate values', 'timestamps', 'order'):
            self.assertIn(missing, self.report)

    def test_the_closing_line_says_it_is_not_hardware_evidence(self):
        self.assertIn('no EC was opened', self.report)


class ClassificationTests(unittest.TestCase):
    """The three classes, and the reachability of each.

    The refusal in `CommittedSummaryTests` is satisfied by a classifier that
    says `moved` about everything, which is why the `held` arm has a case of
    its own here: a byte with no recorded change and equal endpoints is the
    one thing that reads `held`, and if nothing ever does, the refusal is
    vacuous rather than true.
    """

    def setUp(self):
        self.rc, self.report, self.err = run(MOVED_AND_RETURNED)
        self.assertEqual(self.rc, 0, self.report + self.err)

    def test_only_a_zero_count_row_ever_reads_held(self):
        held = [line for line in self.report.splitlines()
                if line.rstrip().endswith('  held')]
        self.assertTrue(held, 'no row in the fixture reads held, so the one '
                              'class this tool is allowed to print is not '
                              'reachable and its refusal is vacuous')
        for line in held:
            self.assertIn(' 0 change(s) ', line)

    def test_a_returned_row_and_a_moved_row_are_told_apart(self):
        self.assertIn('0x07C6  0x04 -> 0x04  2 change(s)  moved 2 times, '
                      'returned to its first recorded value', self.report)
        self.assertIn('0x07C4  0x08 -> 0x38  2 change(s)  moved, net +0x30',
                      self.report)

    def test_a_file_whose_only_row_moved_and_came_back_is_still_never_held(self):
        # The one-row form of the refusal, which is what makes a collapse
        # legible: if the classifier answered `held` for every equal-endpoint
        # row, this file has nothing else in it to be read as a pass.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'only-row.csv',
                                 [('0x07C6', 2, '0x04', '0x04')])
            rc, report, err = run(path)
        self.assertEqual(rc, 0, report + err)
        line = next(line for line in report.splitlines()
                    if line.strip().startswith('0x07C6'))
        self.assertIn('moved 2 times, returned to its first recorded value', line)
        for word in NOT_FOR_A_MOVER:
            self.assertNotIn(word, line.lower())
        # The census counts the row as returned, not as held -- which is the
        # other half of a collapse, a classifier that said `moved` about
        # everything would print `1 moved` here.
        self.assertIn('1 row(s): 0 moved, 1 moved and returned, 0 held', report)

    def test_a_comment_block_is_dropped_before_the_header_is_read(self):
        # The committed summary opens with a `#` block, and so does every
        # fixture; this is the same parse over a file written here, because a
        # reader that took a comment as the fieldnames would find no `addr`
        # column and report the file as carrying no addresses -- which reads
        # as a fact about the file rather than as a parser that skipped what it
        # should not have. `capture_lines` is what the tool imports for it.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(
                tmp, 'commented.csv', [('0x07C6', 2, '0x04', '0x04')],
                header=('derived from a sweep, 2026-01-01.',
                        'Full 2-row log not committed.'))
            rc, report, err = run(path)
        self.assertEqual(rc, 0, report + err)
        self.assertIn('what the file\'s own header says', report)
        self.assertIn('0x07C6  0x04 -> 0x04  2 change(s)  moved 2 times, '
                      'returned to its first recorded value', report)
        self.assertIn('they agree', report)

    def test_a_value_column_is_read_however_it_is_spelled(self):
        # The committed file pads every value to two digits. Requiring that of
        # a future summary would be a rule about spelling, not about meaning,
        # and `0x04`, `04` and `4` are one byte in three of them.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'spelling.csv')
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("addr,change_count,first_old,last_new\n")
                handle.write("0x07C4,1,8,0x38\n")     # a move, 0x08 -> 0x38
                handle.write("0x07C6,2,04,4\n")       # returned
            rc, report, err = run(path)
        self.assertEqual(rc, 0, report + err)
        self.assertIn('0x07C4  0x08 -> 0x38  1 change(s)  moved, net +0x30',
                      report)
        self.assertIn('0x07C6  0x04 -> 0x04  2 change(s)  moved 2 times, '
                      'returned to its first recorded value', report)

    def test_a_zero_count_row_with_equal_endpoints_is_held_in_a_whole_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'quiet.csv',
                                 [('0x07C0', 0, '0x11', '0x11')])
            rc, report, err = run(path)
        self.assertEqual(rc, 0, report + err)
        self.assertIn('0x07C0  0x11 -> 0x11  0 change(s)  held', report)


class ReconciliationTests(unittest.TestCase):
    """`--strict` is a question for a human holding the source log, not a gate."""

    def test_the_default_exit_is_zero_on_a_pair_that_does_not_reconcile(self):
        rc, report, err = run(UNRECONCILED)
        self.assertEqual(rc, 0, report + err)
        self.assertIn('they do not reconcile', report)

    def test_strict_exits_non_zero_on_the_same_file(self):
        rc, report, err = run(UNRECONCILED, '--strict')
        self.assertEqual(rc, 1, report + err)

    def test_strict_exits_zero_where_the_two_figures_agree(self):
        rc, report, err = run(MOVED_AND_RETURNED, '--strict')
        self.assertEqual(rc, 0, report + err)
        self.assertIn('they agree', report)

    def test_a_header_with_no_figure_is_reported_rather_than_read_as_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'silent.csv',
                                 [('0x07C4', 1, '0x08', '0x38')])
            rc, report, err = run(path, '--strict')
        self.assertEqual(rc, 0, report + err)
        self.assertIn('states no source-log row count', report)


class RefusalTests(unittest.TestCase):
    """One per way the file can fail to be a summary worth grading.

    Every refusal is a sentence rather than a status, because the operator who
    handed in the wrong file has to be told what shape it is and where the
    reader for that shape lives; an exit code with no reason is a refusal that
    sends them looking for a tool to run instead of a shape to fix.
    """

    def refused(self, *args):
        rc, out, err = run(*args)
        self.assertEqual(rc, 1, out + err)
        self.assertIn('not a sweep summary', err)
        return err

    def test_a_change_log_names_the_readers_that_own_it(self):
        err = self.refused(CHANGE_LOG)
        for tool in ('grade_gpu_door.py', 'grade_0751_isolation.py',
                     'fan_pair_correlation.py', 'check_capture_claims.py'):
            self.assertIn(tool, err)
        # Not graded: a change log's `old`/`new` are two steps of one sweep,
        # so a row tally over it would answer a question nobody asked.
        self.assertIn('change log', err)

    def test_a_malformed_value_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("addr,change_count,first_old,last_new\n")
                handle.write("0x07C4,1,0xZZ,0x38\n")
            err = self.refused(path)
        self.assertIn("first_old reads '0xZZ'", err)

    def test_a_value_outside_a_byte_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "wide.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("addr,change_count,first_old,last_new\n")
                handle.write("0x07C4,1,0x1FF,0x38\n")
            err = self.refused(path)
        self.assertIn('0x1FF', err)

    def test_zero_changes_with_two_endpoints_is_a_file_that_contradicts_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'contradiction.csv',
                                 [('0x07C4', 0, '0x08', '0x38')])
            err = self.refused(path)
        self.assertIn('change_count is 0', err)
        self.assertIn('contradicts', err)

    def test_a_duplicate_address_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'twice.csv',
                                 [('0x07C4', 1, '0x08', '0x38'),
                                  ('0x07C4', 2, '0x38', '0x00')])
            err = self.refused(path)
        self.assertIn('0x07C4', err)
        self.assertIn('one row per address', err)

    def test_a_file_of_neither_shape_is_refused_with_both_shapes_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "other.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("offset,value\n")
                handle.write("0x07C4,8\n")
            err = self.refused(path)
        self.assertIn('offset,value', err)
        self.assertIn('first_old', err)

    def test_an_address_that_is_not_one_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'short.csv',
                                 [('0x07C', 1, '0x08', '0x38')])
            err = self.refused(path)
        self.assertIn('four-digit', err)

    def test_a_missing_file_is_named_rather_than_read(self):
        rc, out, err = run(os.path.join(str(TESTDATA), 'no-such-file.csv'))
        self.assertEqual(rc, 1)
        self.assertIn('no such file', err)

    def test_one_bad_row_refuses_the_whole_file(self):
        # A report printed over the rows before the refusal is a half-right
        # report, and the operator has to be told before any of it is read.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_summary(tmp, 'late-bad.csv',
                                 [('0x07C4', 1, '0x08', '0x38'),
                                  ('0x07C6', 2, '0x04', '0x04'),
                                  ('0x07D7', 1, 'nope', '0x00')])
            rc, out, err = run(path)
        self.assertEqual(rc, 1)
        self.assertEqual(out, '')
        self.assertIn('row 3', err)

    def test_a_summary_with_no_rows_reports_nothing_to_classify(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "empty.csv")
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write("addr,change_count,first_old,last_new\n")
            rc, report, err = run(path)
        self.assertEqual(rc, 0, report + err)
        self.assertIn('nothing to classify', report)


class FixtureCoverageTests(unittest.TestCase):
    """Every committed fixture in this tool's naming is a case below.

    Without this a fixture could sit in `testdata/` being read by nothing, and
    the index row that names it would be the only thing claiming it is covered
    -- which is the defect `check_testdata_index.py`'s docstring is about in
    the shape this suite can actually close.
    """

    def test_every_committed_fixture_is_reached(self):
        on_disk = {str(path) for path in TESTDATA.glob('sweep-summary-example-*.csv')}
        self.assertTrue(on_disk, 'no sweep-summary-example-*.csv under '
                                 'testdata/, so this suite would pass against '
                                 'nothing')
        unreached = sorted(os.path.basename(p) for p in on_disk - set(FIXTURES))
        self.assertFalse(
            unreached,
            f'{unreached} are in ec/tools/testdata/ and no case here names '
            'them. Add a case, or drop the fixture: a file in this directory '
            'that nothing reads is covered only by its index row.')


class SelfTestModeTests(unittest.TestCase):
    """The mode a gate would call, driven through its `run` seam.

    Driven through the seam rather than launched for real: a case that ran the
    mode would have the mode run this suite, which contains the case, which
    runs the mode. The real discovery is what
    `python3 ec/tools/grade_sweep_summary.py --self-test` and the prepared
    gate patch do, and this file is not either of them.
    """

    def discovery(self, returncode, said):
        def fake_run(cmd, **kw):
            return subprocess.CompletedProcess(cmd, returncode, said)
        return fake_run

    def test_the_mode_runs_the_committed_suite_by_file_name(self):
        seen = []

        def record(cmd, **kw):
            seen.append(cmd)
            return subprocess.CompletedProcess(
                cmd, 0, '....\nRan 3 tests in 0.002s\n\nOK\n')

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(summary.self_test(run=record), 0)
        printed = buf.getvalue()
        self.assertEqual(seen, [[sys.executable, '-m', 'unittest', 'discover',
                                 '-s', str(summary.TOOL_DIR),
                                 '-p', summary.SUITE_FILE]])
        self.assertEqual(Path(seen[0][seen[0].index('-s') + 1]).resolve(),
                         Path(__file__).parent.resolve())
        # The count decorates and does not decide, and the mode says what it is
        # not: no EC is opened and no register read back.
        self.assertIn('3 tests, passed', printed)
        self.assertIn('no EC is opened', printed)

    def test_a_discovery_that_matched_nothing_is_not_a_pass(self):
        # `unittest discover` exits 0 and prints OK for a pattern that no file
        # matches, which from outside is indistinguishable from a suite that
        # passed. A renamed file or a moved `-s` turns a gate green without
        # running anything.
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(
                summary.self_test(run=self.discovery(0, 'Ran 0 tests in 0.000s\n\nOK\n')),
                1)
        self.assertIn('no test ran, which is not a pass', buf.getvalue())

    def test_a_failing_suite_passes_its_own_output_through(self):
        said = '....\nRan 3 tests in 0.002s\n\nFAILED (failures=1)\n'
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(summary.self_test(run=self.discovery(1, said)), 1)
        printed = buf.getvalue()
        self.assertIn('FAILED', printed)
        # What the discovery said is passed on rather than swallowed, so a
        # failing gate's log carries the failure rather than a verdict.
        self.assertIn(said.splitlines()[0], printed)

    def test_the_flag_is_dispatched_before_the_parser(self):
        # `summary` is still a required positional, and `--self-test` with no
        # file behind it reaches the mode rather than argparse's usage error.
        # The mode is stubbed rather than run: calling it for real here would
        # have it discover this suite, which contains this case, which calls
        # it again.
        with mock.patch.object(summary, 'self_test', return_value=0) as stub:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(summary.main(['--self-test', '--help']), 0)
        stub.assert_called_once_with()
        self.assertEqual(buf.getvalue(), '')

    def test_a_command_line_with_no_file_is_still_a_usage_error(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                summary.main([])
        self.assertNotEqual(cm.exception.code, 0)


if __name__ == '__main__':
    unittest.main()