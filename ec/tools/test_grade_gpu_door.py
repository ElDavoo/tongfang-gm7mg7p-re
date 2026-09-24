#!/usr/bin/env python3
"""Offline checks against the constructed captures in testdata/; no hardware
is involved, no real capture is read, and no EC is opened.

The grader does `import grade_0751_isolation` for its CSV vocabulary, so this
directory has to be the import root. `unittest discover -s ec/tools` already
puts it there, which is how tools/run-tests.sh runs this file; the insert below
is so the suite also runs from an editor or a bare `python3` on its own.

The eighth check is the one that keeps a second copy honest. The grader cannot
import windows/tools/gpu_block_watch.py -- that module does `from ecrw import
Ec, EcError`, and `ecrw` binds kernel32 at import time, so it loads only on
Windows and an offline grader that imported it would be Windows-only. So the
grader states its own two window bounds and its own 24 DSDT field-list names,
and windows/tools/test_gpu_block_watch.py holds both against the watcher's
WATCH. That is the same shape of hold as the one that caught the procedure's
four stale cells in #266: two copies of a table, and one test that fails when
they disagree.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'door', HERE / 'grade_gpu_door.py')
door = importlib.util.module_from_spec(spec)
spec.loader.exec_module(door)

TESTDATA = HERE / 'testdata'
# One fixture per branch the report has, all in the schema §3's
# `gpu_block_watch.py --csv --mark` writes. `FIXTURES` is what the first test
# holds equal to the directory, so a fixture added without a test reaching it
# fails rather than sitting there looking covered.
ACPI_FIRST = str(TESTDATA / 'gpu-door-example-acpi-first.csv')
HOST_FIRST = str(TESTDATA / 'gpu-door-example-host-first.csv')
ONE_BLOCK = str(TESTDATA / 'gpu-door-example-one-block.csv')
QUIET = str(TESTDATA / 'gpu-door-example-quiet.csv')
MOVED_AND_BACK = str(TESTDATA / 'gpu-door-example-moved-and-back.csv')
CLOSE_MARKS = str(TESTDATA / 'gpu-door-example-close-marks.csv')
FIXTURES = (ACPI_FIRST, HOST_FIRST, ONE_BLOCK, QUIET, MOVED_AND_BACK,
            CLOSE_MARKS)

# The 24 addresses the watcher sweeps, read off the grader's own bounds rather
# than typed out, so a bounds edit on either side moves the expected line count
# with it instead of leaving a stale 24 behind.
WATCHED = sum(hi - lo + 1 for _, lo, hi in door.WINDOWS)


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = door.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def unwrapped(section):
    """A report section as one line, so a check is on the sentence.

    The report is printed to ~72 columns, which means a phrase can be split
    anywhere; the §4.4/§4.5 checks in test_grade_0751_isolation.py read their
    sections the same way for the same reason.
    """
    return " ".join(section.split())


def windows_in(path):
    rc, out, _ = run(path)
    assert rc == 0, out
    return int(re.search(r'=== (\d+) window\(s\)', out).group(1))


def ordering_lines(out):
    """The per-window ordering lines, as printed.

    Cut by their indent rather than searched for as substrings: the leading-
    block line is at four spaces and the "led" line at six, and the word `led`
    also turns up inside "filled" further down, so a substring test for it
    would pass on a report that reported no ordering at all.
    """
    return [l for l in out.splitlines()
            if l.startswith('    which block moved first:')
            or l.startswith('      led ')]


class FixtureTests(unittest.TestCase):
    def test_every_door_fixture_is_one_this_suite_runs(self):
        # The vacuity guard test_gpu_block_watch.py:333 sets for its table
        # reader: a suite that silently stopped reaching a fixture would still
        # be green, and a fixture nobody grades is a fixture that reads as
        # coverage. Equality, not existence, both ways.
        on_disk = {p.name for p in TESTDATA.glob('gpu-door-example-*.csv')}
        self.assertTrue(on_disk, "no gpu-door-example-*.csv in testdata/")
        self.assertEqual(on_disk, {Path(p).name for p in FIXTURES})

    def test_each_fixture_is_a_constructed_capture_with_marks(self):
        for path in FIXTURES:
            text = Path(path).read_text()
            self.assertTrue(door.fan.read_capture(path)[0],
                            f"{Path(path).name} has no MARK row")
            # The header is what keeps a fixture from being mistaken for a
            # run, and read_capture skips `#` lines to allow it. A fixture
            # whose header went would parse exactly the same way, which is why
            # it is asserted rather than assumed.
            self.assertIn('CONSTRUCTED INPUT, NOT A CAPTURE', text,
                          Path(path).name)
            # 2026-01-01 is the placeholder date this directory's README
            # reserves for constructed inputs, so a real capture pasted over a
            # fixture would change the date before anything else. The header's
            # "not a prediction" clause is what keeps the shape above it from
            # being read as a claim about the machine, so it is checked by the
            # one word every header carries rather than by the sentence, which
            # the 72-column wrap can break anywhere.
            self.assertIn('2026-01-01T', text, Path(path).name)
            self.assertIn('prediction', text, Path(path).name)

    def test_the_watched_set_is_the_two_blocks_and_nothing_else(self):
        self.assertEqual(
            {a for _, lo, hi in door.WINDOWS for a in range(lo, hi + 1)},
            set(range(0x0743, 0x0747)) | set(range(0x07C4, 0x07D8)))
        self.assertEqual(WATCHED, 24)
        # Every DS_NAMES entry is inside a declared window, so `name_of` can
        # never fall off the end while a change row is being printed.
        for addr, _ in door.DS_NAMES:
            self.assertIn(door.window_of(addr), {lbl for lbl, _, _ in
                                                 door.WINDOWS}, addr)

    def test_window_of_refuses_an_address_outside_both_blocks(self):
        # 0x0747 is one past the host half and 0x07C3 one before the ACPI
        # half; both are addresses the watcher does not sweep, and the
        # watcher's own `window_of` raises on one. A grader that returned
        # something for them would be classifying a row from another tool's
        # capture.
        for addr in (0x0742, 0x0747, 0x07C3, 0x07D8):
            with self.assertRaises(KeyError):
                door.window_of(addr)


class ReportTests(unittest.TestCase):
    def test_the_acpi_block_leading_is_reported_with_its_delta(self):
        rc, out, _ = run(ACPI_FIRST)
        self.assertEqual(rc, 0)
        self.assertEqual(ordering_lines(out), [
            '    which block moved first: 0x07C4-0x07D7 (0x07C4, +0.4s after '
            'the mark)',
            '      led 0x0743-0x0746 (0x0745, +1.2s after the mark) by 800 ms',
            '    which block moved first: 0x07C4-0x07D7 (0x07D3, +30.3s after '
            'the mark)',
            '      led 0x0743-0x0746 (0x0746, +31.6s after the mark) by 1300 ms',
        ])
        # The ms figure is the delta between the two blocks' *first* changes,
        # not between any pair of rows, and the addresses are on the line so
        # the number is checkable against the rows above it.
        self.assertIn('0x07C4  0x08 -> 0x28   (+0.4s)   DBEN b3, DBST b5', out)
        self.assertIn('0x0745  0x00 -> 0x0A   (+1.2s)   DBCT', out)

    def test_the_host_block_leading_is_reported_with_its_delta(self):
        rc, out, _ = run(HOST_FIRST)
        self.assertEqual(rc, 0)
        self.assertEqual(ordering_lines(out), [
            '    which block moved first: 0x0743-0x0746 (0x0743, +0.2s after '
            'the mark)',
            '      led 0x07C4-0x07D7 (0x07D0, +0.9s after the mark) by 650 ms',
            '    which block moved first: 0x0743-0x0746 (0x0744, +0.4s after '
            'the mark)',
            '      led 0x07C4-0x07D7 (0x07D4, +1.4s after the mark) by 950 ms',
        ])
        # The DSDT-name column is what makes a hit fillable into §5's third
        # cell, including on the DO-NOT-WRITE-BLIND pair the question is about.
        self.assertIn('0x07D0  0x00 -> 0x37   (+0.9s)   DBD1', out)
        self.assertIn('0x07D4  0x20 -> 0x28   (+1.4s)   CPUA', out)

    def test_one_block_moving_reports_no_ordering(self):
        rc, out, _ = run(ONE_BLOCK)
        self.assertEqual(rc, 0)
        self.assertEqual(ordering_lines(out), [])
        # Stated per window, not omitted: "no ordering" and "no data" have to
        # be different answers, and a one-block run is a real §6 shape.
        self.assertEqual(
            out.count('no ordering to report: only 0x07C4-0x07D7 moved, and '
                      'one block cannot lead'), 2)
        self.assertEqual(out.count('nothing in this block moved by this '
                                   'method under this action'), 2)
        # And the closing does not reach for §6's third bullet -- "no movement
        # at all" -- on a capture in which the ACPI half moved twice. That
        # would be the tool making the human's call. Unwrapped, for the same
        # reason the §5 columns below are.
        close = unwrapped(out.split('=== what this does and does not settle')[1])
        self.assertIn("matches none of §6's three readings as written", close)
        self.assertNotIn("§6's third bullet -- no movement at", close)

    def test_a_quiet_capture_states_a_zero_for_every_address(self):
        rc, out, _ = run(QUIET)
        self.assertEqual(rc, 0)
        self.assertEqual(windows_in(QUIET), 3)
        # Three windows x 24 addresses. The count is read off the grader's own
        # bounds, so a bounds edit that dropped addresses would move it rather
        # than leaving a 72 that no longer describes the table.
        self.assertEqual(out.count('window delta'), WATCHED * 3)
        # Every one of them is a zero line, and all of them say their level is
        # not in evidence rather than filling something in: a change-row
        # capture records transitions, not values, so a byte that never
        # appears is known to have held still and its level is unknown.
        self.assertEqual(out.count('net +0  total 0  max 0  (0 changes, level '
                                   'not in these captures)'), WATCHED * 3)
        self.assertEqual(
            out.count('no ordering to report: neither block moved in this '
                      'window'), 3)
        self.assertIn("§6's third bullet -- no movement at", out)
        # The one that would have been silent: this is a result, and it reads
        # like one. §5's column 5 has no number in it because there was no
        # ordering, which is different from there being no capture.
        self.assertIn('Neither block moved in any window above', out)

    def test_every_address_gets_a_line_in_every_window(self):
        for path in FIXTURES:
            rc, out, _ = run(path)
            self.assertEqual(rc, 0, path)
            self.assertEqual(out.count('window delta'),
                             WATCHED * windows_in(path), path)
            # Both blocks, always: a block whose addresses went unlisted would
            # read as "nothing moved" where the truth is "not printed".
            self.assertEqual(out.count('every watched address, moved or not'),
                             windows_in(path), path)

    def test_a_byte_that_moved_and_came_back_is_not_read_as_held(self):
        rc, out, _ = run(MOVED_AND_BACK)
        self.assertEqual(rc, 0)
        # The endpoint line is 0x00 -> 0x00, which is the shape a held byte
        # has; total 112 and max 56 are what say otherwise, and all three are
        # on one line because none of them answers the question on its own.
        self.assertIn('window delta  0x07D0  0x00 -> 0x00  net +0  total 112 '
                      ' max 56  (3 changes)', out)
        # Each step is on its own row, so the three are countable by eye and
        # the figure is checkable against something.
        self.assertIn('0x07D0  0x00 -> 0x28   (+0.3s)   DBD1', out)
        self.assertIn('0x07D0  0x28 -> 0x38   (+0.9s)   DBD1', out)
        self.assertIn('0x07D0  0x38 -> 0x00   (+1.5s)   DBD1', out)
        # One address moved, over three rows: counted as rows it would print
        # "3 of 20 addresses moved", which is the same overclaim in a number.
        self.assertIn('0x07C4-0x07D7: 1 of 20 addresses moved, 3 change rows',
                      out)
        # And the block still moved, so the ordering is unaffected: a byte
        # that came back is not a byte that did not move.
        self.assertEqual(len(ordering_lines(out)), 2)

    def test_close_marks_are_flagged_and_never_fused(self):
        rc, out, _ = run(CLOSE_MARKS)
        self.assertEqual(rc, 0)
        self.assertIn('=== 3 window(s), one per mark, none merged ===', out)
        # The first window is one second long and empty, and it survives as a
        # window. A merge would have hidden exactly that.
        self.assertIn('no ordering to report: neither block moved in this '
                      'window', out)
        # The distance is printed so a reader can see they were close...
        self.assertIn("are 1.0s apart, inside the 5s flag threshold", out)
        self.assertIn('They stay two windows', out)
        # ...and so can be shown the other way round: the 0751 grader, whose
        # MARK_MERGE_SECONDS is the 5 s in the message, really does fuse these
        # two marks into one. The constraint is tested rather than asserted in
        # a comment, and it is the reason the two graders cannot be merged.
        marks, _ = door.fan.read_capture(CLOSE_MARKS)
        self.assertEqual(len(marks), 3)
        self.assertEqual(len(door.fan.coalesce_marks(marks)), 2)

    def test_changes_before_the_first_mark_belong_to_no_window(self):
        rc, out, _ = run(ACPI_FIRST)
        self.assertEqual(rc, 0)
        # 0x07CC moves eight seconds before the first mark, so it is in no
        # window's change list and no row carries a negative offset.
        self.assertNotIn('(+-', out)
        # It still sets the level both windows opened on, which is the half
        # that keeps a held byte from printing `????` -- so it appears once per
        # window, as a zero line, and nowhere else.
        self.assertEqual(out.count('0x07CC'), 2)
        self.assertEqual(out.count('window delta  0x07CC  0x05 -> 0x05  net +0'
                                   '  total 0  max 0  (0 changes)'), 2)

    def test_a_capture_without_marks_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'nomarks.csv'
            p.write_text('ts,addr,old,new\n'
                         '2026-01-01T12:00:02.000+01:00,0x07C4,0x08,0x28\n')
            rc, out, err = run(str(p))
        self.assertEqual(rc, 1)
        self.assertIn('no MARK rows', err)
        # Refused before any report, rather than a report over zero windows:
        # with no mark a window has no start, and which action a movement
        # belongs to is not knowable.
        self.assertNotIn('window delta', out)

    def test_the_report_names_the_five_columns_it_fills_and_the_five_it_does_not(self):
        rc, out, _ = run(QUIET)
        self.assertEqual(rc, 0)
        section = unwrapped(out.split("=== §5's ten columns ===")[1])
        for col in range(1, 11):
            self.assertIn(f'col {col}', section)
        # The five that come out of the capture, named as filled...
        for name in ('mark label', 'mark ts',
                     '0x07C4-0x07D7 addresses moved',
                     '0x0743-0x0746 addresses moved',
                     'which block first, and by how many ms'):
            self.assertIn(name, section)
        # ...and the five that do not, named as not, so a table carrying only
        # the first five cannot read as a finished one. Four are §4a's
        # Windows `.PML`; the fifth is a judgement.
        self.assertIn('NOT filled here', section)
        self.assertIn("Columns 6-9 are §4a's ProcMon half", section)
        for name in ('ProcMon PID', 'process image',
                     'IOCTL code on the \\.\\ACPIDriver',
                     'modules loaded at that instant'):
            self.assertIn(name, section)
        self.assertIn("column 10 is the human's call against §6", section)

    def test_no_report_moves_a_status_or_claims_an_absence(self):
        # docs/findings.md §4c retracted a "does not exist" claim built on a
        # zero-reference scan. The report body must not make one either way, so
        # the absence words are checked over everything above the closing
        # section -- where they are the closing section's own prohibition and
        # so are required there. The per-window header says the same thing
        # without the words, which is what lets the split here be exact.
        for path in FIXTURES:
            rc, out, _ = run(path)
            self.assertEqual(rc, 0, path)
            body = out.split('=== what this does and does not settle')[0]
            for word in ('absent', 'unused', 'unreferenced',
                         'confirmed-working', 'confirmed-inert'):
                self.assertNotIn(word, body, f"{Path(path).name}: {word}")
            # The three caveats §5 carries next to the table are carried, not
            # weakened: a zero's meaning, a readback's meaning, and the
            # resolution the ms figure is actually good to. Read unwrapped,
            # since the ~72-column wrap breaks them wherever it lands.
            flat = unwrapped(out)
            self.assertIn("never 'absent', 'unused' or 'unreferenced'", flat)
            self.assertIn('A readback is not an effect', flat)
            self.assertIn('has a write path', flat)
            # The write-path refusal is stated, because 0x07D0/0x07D1 are
            # DO-NOT-WRITE-BLIND and a grader that could be talked into writing
            # would be a new hazard rather than a reader of the capture.
            self.assertIn('DO-NOT-WRITE-BLIND', flat)
            # And the ms figure is not sold as finer than the sweep that
            # produced it, which is the calibration §5's millisecond column
            # would otherwise invite a reader to skip.
            self.assertIn("good to about one `--interval` (0.25 s by default)",
                          flat)


if __name__ == '__main__':
    unittest.main()
