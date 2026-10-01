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
from datetime import timedelta
import importlib.util
import io
import os
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
# The two-capture pair, as two entries because `FIXTURES` is a list of files
# some run grades and each of these is graded on its own by the cases below as
# well as beside its sibling. They are a day apart and neither file's rows
# fall between the other's marks, so one invocation over both is two runs.
TWO_FILES_A = str(TESTDATA / 'gpu-door-example-two-files-a.csv')
TWO_FILES_B = str(TESTDATA / 'gpu-door-example-two-files-b.csv')
FIXTURES = (ACPI_FIRST, HOST_FIRST, ONE_BLOCK, QUIET, MOVED_AND_BACK,
            CLOSE_MARKS, TWO_FILES_A, TWO_FILES_B)

# The 24 addresses the watcher sweeps, read off the grader's own bounds rather
# than typed out, so a bounds edit on either side moves the expected line count
# with it instead of leaving a stale 24 behind.
WATCHED = sum(hi - lo + 1 for _, lo, hi in door.WINDOWS)

# `ec_watch.py`'s `now()` and `ec_timer_capture.py`'s are both this, and a
# capture whose rows are spelled at microseconds is not the schema §3 takes.
MS = "milliseconds"

# The pair the collision tests are over: two labels on the same instant, in
# §3's own vocabulary. `write_capture` puts the change rows after them. Built
# into a temporary directory rather than added to testdata/ because every
# capture the collision tests use is one the grader is asked to *refuse*, and a
# file in `FIXTURES` is by definition one some run grades -- which is what
# `test_every_door_fixture_is_one_this_suite_runs` holds the directory equal
# to.
COLLIDING_MARKS = (
    ('2026-01-01T12:00:10.000+01:00', 'fn mode balanced->performance'),
    ('2026-01-01T12:00:10.000+01:00', 'gpu tgp 115W->130W'),
)
# 2026-01-01T12:00:10.000+01:00 is the placeholder instant testdata/README.md
# reserves for constructed inputs, so a real capture pasted over one of these
# would change the date before anything else.


def write_capture(directory, name, marks):
    """A §3-schema capture: `marks` as (ts, label) pairs, then two change rows.

    The rows land 0.4 s and 1.9 s after the *first* mark rather than at fixed
    timestamps, so the capture stays a capture whichever instant the caller
    wrote its marks on -- which is the whole question the spelling variants
    turn on. A capture that keeps both windows therefore reports a 1500 ms
    ordering, and that is the figure the single-mark control has to come out
    with: the phantom is a property of the duplicate mark, not of the rows
    around it.

    `parse_ts` is the grader's own, so the timestamps here go through the same
    reader the capture will, and the rows are written at
    `timespec="milliseconds"` because that is the spelling `ec_watch.py`'s
    `now()` puts in a capture and this one is meant to be in that schema.
    """
    first = door.fan.parse_ts(marks[0][0])
    rows = ['ts,addr,old,new']
    rows += [f'{ts},MARK,,{label}' for ts, label in marks]
    rows += [f'{(first + timedelta(milliseconds=ms)).isoformat(timespec=MS)},'
             f'{row}'
             for ms, row in ((400, '0x07C4,0x08,0x28'),
                             (1900, '0x0743,0x00,0x0A'))]
    path = Path(directory) / name
    path.write_text('\n'.join(rows) + '\n')
    return str(path)


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
            # fixture would change it. It is read from the text because that is
            # where the header writes it down, and the two-capture pair's
            # second file is a day later: what it carries is its own header
            # naming the first file's date, so that file is reached here
            # through its header and not through its rows. The header's "not a
            # prediction" clause is what keeps the shape above it from being
            # read as a claim about the machine, so it is checked by the one
            # word every header carries rather than by the sentence, which the
            # 72-column wrap can break anywhere.
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


class TwoCaptureTests(unittest.TestCase):
    """A path may name more than one capture, and each is its own run.

    The whole class is over one invocation of the pair in `TWO_FILES_A` /
    `TWO_FILES_B`, which is the command line the issue reports: two captures
    a day apart, each with its own marks, concatenated before the windows were
    cut. The defect was that `b.csv`'s two change rows were filed under
    `a.csv`'s `ac unplug` mark, 21 hours earlier, with nothing in the report
    saying two captures had been handed in at all.
    """

    def setUp(self):
        # One graded run of the pair, read by every case below. Held on the
        # case rather than re-run per assertion so a case can be read on its
        # own without each one repeating the invocation, and so the exit code
        # is checked once, here, by the case the class is about.
        self.rc, self.out, self.err = run(TWO_FILES_A, TWO_FILES_B)

    def test_no_window_carries_a_change_row_from_another_capture(self):
        # The issue's Done criterion, walked over the data rather than over
        # the printed report: `w.source` against `c.source` for every change
        # row on every window, through `capture_key` because that is the
        # comparison the module's own rule is written in terms of. A text
        # search would pass on a report that filed the row correctly and
        # printed a neighbouring line that mentioned the other file.
        self.assertEqual(self.rc, 0, self.out + self.err)
        marks, changes = [], []
        for path in (TWO_FILES_A, TWO_FILES_B):
            m, c = door.fan.read_capture(path)
            marks += m
            changes += c
        runs = door.capture_runs((TWO_FILES_A, TWO_FILES_B), marks, changes)
        # Built once, because `build_windows` appends to each window's own
        # `changes` list rather than replacing it: a second call over the same
        # runs would file every row twice, and the count below would be
        # reading the grader's mutation rather than the grader.
        built = door.build_windows(runs)
        # Two marks and one, so three windows over the pair: a count, not a
        # census, and it is here to fail if `capture_runs` produced one run
        # for the pair rather than two, which would make the walk below pass
        # over a single window set and check nothing.
        self.assertEqual(sum(len(ws) for _, ws in built), 3)
        seen = 0
        for source, windows in built:
            for w in windows:
                for c in w.changes:
                    seen += 1
                    self.assertEqual(door.fan.capture_key(c.source),
                                     door.fan.capture_key(w.source),
                                     f'{Path(source).name} window at '
                                     f'{w.ts.isoformat()} carries a row from '
                                     f'{Path(c.source).name}')
        # And the walk is not vacuous: the two captures carry three change rows
        # between them, one inside a window and two before `b.csv`'s only
        # mark, where they set its level instead. A grader that dropped every
        # row would satisfy the equality above over an empty set.
        self.assertEqual(seen, 1)
        self.assertEqual(len(changes), 3)

    def test_the_report_says_which_capture_each_figure_is_from(self):
        # The window count is per capture and names the file, the "runs to"
        # line names the file it runs to, and no offset in the report is the
        # 21 hours the concatenated pass produced.
        self.assertEqual(self.rc, 0, self.out + self.err)
        self.assertIn(f'=== 2 window(s), one per mark, none merged === '
                      f'({TWO_FILES_A})', self.out)
        self.assertIn(f'=== 1 window(s), one per mark, none merged === '
                      f'({TWO_FILES_B})', self.out)
        # The last window of a capture runs to that capture's end. Under the
        # concatenation this line read "the end of the capture" over a
        # sequence that ended 21 hours later, so it was true of the run and
        # false of the window.
        self.assertIn(f'window runs to the next mark in {TWO_FILES_A}',
                      self.out)
        self.assertIn(f'window runs to the end of {TWO_FILES_A}', self.out)
        self.assertIn(f'window runs to the end of {TWO_FILES_B}', self.out)
        # `b.csv`'s two rows set the level its own window opened on, near its
        # own mark. The 21-hour figure the issue reported -- the absorption at
        # `+75562.0s` -- is not in the report at all, and neither is any
        # offset over an hour, which is the width a day-apart pair would
        # produce if a row were still crossing the boundary.
        self.assertNotIn('+75562.0s', self.out)
        self.assertIn('window delta  0x07C6  0x01 -> 0x01  net +0  total 0  '
                      'max 0  (0 changes)', self.out)
        self.assertIn('window delta  0x07C4  0x38 -> 0x38  net +0  total 0  '
                      'max 0  (0 changes)', self.out)
        for line in self.out.splitlines():
            found = re.search(r'\(\+(\d+)\.(\d)s\)', line)
            if found:
                self.assertLess(float(found.group(1)), 3600, line)

    def test_a_file_boundary_is_noted_where_the_two_captures_meet(self):
        # `report_close_marks` fires on a file boundary the way it fires on a
        # 5 s gap: naming both files, the distance, and the fact that the two
        # are two runs. Read unwrapped, for the reason `unwrapped` gives.
        self.assertEqual(self.rc, 0, self.out + self.err)
        note = unwrapped(self.out.split('  note  ')[1])
        self.assertIn(f'{TWO_FILES_A} ends at \'ac unplug\'', note)
        self.assertIn(f'{TWO_FILES_B} begins at \'gpu tgp 115W->130W\'', note)
        self.assertIn('They are two captures and two runs', note)
        # The gap is printed, and it is a day rather than the 5 s the
        # threshold check would have wanted: this pair is two runs and the
        # distance is a fact about the command line, not about pacing.
        self.assertRegex(note, r'75580\.0s apart')
        # And the 5 s note is not fired on it. A boundary is not a pair of
        # marks one console typed close together, and saying so is what keeps
        # the two checks from being one check.
        self.assertNotIn('flag threshold', note)
        self.assertNotIn('They stay two windows', note)
        # The threshold check itself still runs inside a capture: the close-
        # marks fixture over one file is the case for that, and it is a
        # different test on purpose rather than this one.
        rc, out, _ = run(CLOSE_MARKS)
        self.assertEqual(rc, 0)
        self.assertIn("are 1.0s apart, inside the 5s flag threshold", out)
        # The same pair named the other way round. The walk follows the order
        # the command line gave rather than the order the captures happened,
        # so the later capture's last mark comes first and the gap would come
        # out negative; it is printed as a distance, which has no sign. The
        # note itself is the same either way -- a boundary is a fact about the
        # command line, not about which file is older.
        rc, out, err = run(TWO_FILES_B, TWO_FILES_A)
        self.assertEqual(rc, 0, out + err)
        reversed_note = unwrapped(out.split('  note  ')[1])
        self.assertIn('They are two captures and two runs', reversed_note)
        # The distance is printed as a distance, so the figure carries no
        # sign whichever file is named first. Which pair of marks the
        # boundary falls between is not asserted here: naming the files the
        # other way round puts the walk at a different mark pair, and the gap
        # above is that walk's, not this one's.
        self.assertNotRegex(reversed_note, r'-\d[\d.]*s apart')
        self.assertRegex(reversed_note, r'(?<![\d.-])\d[\d.]*s apart')

    def test_the_closing_counts_each_capture_separately(self):
        # A closing per capture, over its own windows. Summed over the pair
        # the two would read as one run's "3 of 3", which is the figure this
        # change exists to stop being printed; here they are 1 of 2 and a
        # different branch entirely, because `b.csv`'s one window is quiet.
        self.assertEqual(self.rc, 0, self.out + self.err)
        close = unwrapped(self.out.split('=== what this does and does not '
                                         'settle ===')[1])
        self.assertIn(f'-- {TWO_FILES_A} --', close)
        self.assertIn(f'-- {TWO_FILES_B} --', close)
        self.assertIn('No window had both blocks moving (1 of 2 moved one '
                      'block only)', close)
        # `b.csv`'s own closing is the third bullet, over its one window. The
        # pair's is not: `a.csv` moved a block twice, so a closing over both
        # would have reached for "no movement at all" on a capture in which
        # the ACPI half moved.
        self.assertIn('Neither block moved in any window above', close)
        self.assertNotIn('Neither block moved in any window above, so §6\'s '
                         'third bullet', close.split(f'-- {TWO_FILES_B} --')[0])
        # And the denominators are each capture's, which is the claim: no
        # count in the section is taken over the pair's three windows.
        self.assertNotIn('of 3 ', close)
        # The caveats below are shared rather than repeated per capture, so a
        # reader is not handed the same three a second time, and the note
        # that says so is printed for a two-capture run and not for one.
        self.assertIn('The 2 captures above are separate runs', close)
        rc, out, _ = run(ONE_BLOCK)
        self.assertEqual(rc, 0)
        self.assertNotIn('captures above are separate runs', out)

    def test_a_capture_with_rows_and_no_marks_is_refused(self):
        # Not the issue's case, and not reachable before the per-`source` cut:
        # a file with change rows and no MARK row used to have those rows
        # filed under another capture's marks, which is the defect. Under the
        # cut they belong to no window at all, so the run is refused by name
        # rather than reported over with a figure missing.
        with tempfile.TemporaryDirectory() as tmp:
            marks = _write_rows(Path(tmp) / 'marks.csv',
                                (('2026-01-01T12:00:10.000+01:00', 'ac plug'),
                                 ('2026-01-01T12:00:40.000+01:00',
                                  'ac unplug')),
                                [('2026-01-01T12:00:11.000+01:00',
                                  '0x07C4,0x08,0x28')])
            rows = _write_rows(Path(tmp) / 'rows.csv', (),
                               [('2026-01-03T09:00:11.000+01:00',
                                 '0x07C4,0x08,0x28')])
            rc, out, err = run(str(marks), str(rows))
        self.assertEqual(rc, 1)
        self.assertIn('has change rows and no MARK rows', err)
        # And the refusal says the rows cannot be read as the other capture's
        # either, which is what the per-`source` cut changed and the reason
        # this is a refusal rather than a silently shorter report.
        self.assertIn('its rows cannot be read as', unwrapped(err))
        self.assertNotIn('window delta', out)

    def test_a_capture_with_nothing_in_it_is_still_a_run(self):
        # The other side of the same line: a file the operator named and that
        # holds neither a mark nor a change row is not refused, and not
        # dropped from the report either. It gets a window count of zero and
        # a §6 reading that says what is missing -- a missing §6 reading would
        # read as a capture whose bytes held still, which is the §4c shape.
        with tempfile.TemporaryDirectory() as tmp:
            good = _write_rows(Path(tmp) / 'marks.csv',
                               (('2026-01-01T12:00:10.000+01:00', 'ac plug'),
                                ('2026-01-01T12:00:40.000+01:00',
                                 'ac unplug')),
                               [('2026-01-01T12:00:11.000+01:00',
                                 '0x07C4,0x08,0x28')])
            empty = Path(tmp) / 'empty.csv'
            empty.write_text('ts,addr,old,new\n')
            rc, out, err = run(str(good), str(empty))
        self.assertEqual(rc, 0, out + err)
        self.assertIn(f'=== 0 window(s), one per mark, none merged === '
                      f'({empty})', out)
        close = unwrapped(out.split('=== what this does and does not settle '
                                    '===')[1])
        self.assertIn(f'-- {empty} --', close)
        # The sentence is about the file and not about the bytes, and says so
        # both ways round: "nothing was recorded" is not "nothing moved".
        self.assertIn('no MARK row and no change row', close)
        self.assertIn('nothing was recorded, which is not the same as nothing '
                      'moved', close)
        # And it does not reach for §6's third bullet, which reads "no
        # movement at all" and would be a verdict over a capture with no
        # window to have found movement in.
        self.assertNotIn('third bullet', close.split(f'-- {empty} --')[1])

    def test_rows_that_interleave_another_captures_marks_are_graded(self):
        # Two captures whose marks overlap in wall-clock time, which is the
        # shape two watchers running at once produce and which this grades.
        # Built in a temporary directory rather than added to testdata/, for
        # the reason the `COLLIDING_MARKS` comment gives: the pair has to
        # interleave, and the committed fixtures are a day apart so that
        # neither can fall inside the other's marks.
        a = ('2026-01-01T12:00:10.000+01:00', 'gpu tgp 115W->130W')
        b = ('2026-01-01T12:00:40.000+01:00', 'ac unplug')
        c = ('2026-01-01T12:00:20.000+01:00', 'fn mode balanced')
        d = ('2026-01-01T12:00:50.000+01:00', 'gpu tgp 130W->115W')
        with tempfile.TemporaryDirectory() as tmp:
            first = _write_rows(Path(tmp) / 'first.csv', (a, b),
                                [('2026-01-01T12:00:11.000+01:00',
                                  '0x07C4,0x08,0x28')])
            # The second capture's marks fall between the first capture's two,
            # and its rows fall inside the first capture's window. Each is
            # filed under a mark of its own capture.
            second = _write_rows(Path(tmp) / 'second.csv', (c, d),
                                 [('2026-01-01T12:00:25.000+01:00',
                                   '0x07C6,0x00,0x01'),
                                  ('2026-01-01T12:00:45.000+01:00',
                                   '0x07D3,0x40,0x50')])
            rc, out, err = run(str(first), str(second))
            # The data walk is inside the temporary directory rather than
            # after it, so the two files it re-reads are still there.
            marks, changes = [], []
            for path in (first, second):
                m, c = door.fan.read_capture(path)
                marks += m
                changes += c
            runs = door.capture_runs((str(first), str(second)), marks, changes)
            for _, own, _ in runs:
                own.sort(key=lambda w: w.ts)
            built = door.build_windows(runs)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(err, '')
        # Each capture is a run of its own, with its own window count.
        self.assertIn(f'=== 2 window(s), one per mark, none merged === '
                      f'({first})', out)
        self.assertIn(f'=== 2 window(s), one per mark, none merged === '
                      f'({second})', out)
        # Walked over the data rather than over the report, for the reason
        # `test_no_window_carries_a_change_row_from_another_capture` gives.
        seen = 0
        for _source, windows in built:
            for w in windows:
                for c in w.changes:
                    seen += 1
                    self.assertEqual(door.fan.capture_key(c.source),
                                     door.fan.capture_key(w.source),
                                     f'window at {w.ts.isoformat()} carries a '
                                     f'row from {Path(c.source).name}')
        # All three rows are filed, one under the first capture's mark and
        # two under the second's, so the walk above is not vacuous.
        self.assertEqual(seen, len(changes))
        self.assertEqual(len(changes), 3)
        # And the second capture's rows are reported against its own marks,
        # seconds after them -- the offsets are the second capture's mark to
        # its own rows, not the first capture's mark to them.
        self.assertIn('0x07C6  0x00 -> 0x01   (+5.0s)', out)
        self.assertIn('0x07D3  0x40 -> 0x50   (+25.0s)', out)

    def test_each_capture_of_the_pair_is_a_run_on_its_own(self):
        # The control: each file graded alone still reports what it did
        # before, so the refusal and the per-capture figures are pinned to
        # the multi-capture command line and not to the fixture. What each
        # file says is the same whether or not the other was handed in --
        # which is the whole claim, read one file at a time.
        for path, windows, closing in ((TWO_FILES_A, 2, '1 of 2'),
                                       (TWO_FILES_B, 1, None)):
            with self.subTest(Path(path).name):
                rc, out, err = run(path)
                self.assertEqual(rc, 0, out + err)
                self.assertEqual(err, '')
                self.assertIn(f'=== {windows} window(s), one per mark, none '
                              f'merged === ({path})', out)
                self.assertIn(f'window runs to the end of {path}', out)
                self.assertNotIn(TWO_FILES_B if path == TWO_FILES_A
                                 else TWO_FILES_A, out)
                if closing:
                    self.assertIn(f'No window had both blocks moving '
                                  f'({closing} moved one block only)', out)
                else:
                    self.assertIn('Neither block moved in any window above',
                                  out)
        # And the control is a real grading rather than an empty one: every
        # address in every window has its line, as in any other run.
        self.assertEqual(self.out.count('window delta'),
                         WATCHED * (windows_in(TWO_FILES_A)
                                    + windows_in(TWO_FILES_B)))


def _write_rows(path, marks, rows):
    """A §3-schema capture: `marks` as (ts, label) pairs, then `rows`.

    `rows` are `(ts, '0xNNNN,0xAA,0xBB')` pairs rather than `write_capture`'s
    fixed two, because the interleaving case is a question about *where* a row
    falls -- between two marks of the other file, rather than 0.4 s and 1.9 s
    after the first -- and a helper that places rows for the caller cannot
    state it. The header line and the schema are the same ones
    `write_capture` writes, so the two are the same shape to the reader.
    """
    lines = ['ts,addr,old,new']
    lines += [f'{ts},MARK,,{label}' for ts, label in marks]
    lines += [f'{ts},{row}' for ts, row in rows]
    path.write_text('\n'.join(lines) + '\n')
    return path


class RefusalTests(unittest.TestCase):
    # One file agreeing with itself is a §3 run that never happened, and this
    # grader turns it into something that reads like one: two marks become four
    # windows, the duplicate windows are zero-length and empty, every change
    # row is counted twice, and `report_close_marks` prints the 0.0s gap as a
    # question for the reader about the operator's pacing. §5's millisecond
    # figure is the one thing a repeat does *not* move, so the refusal message
    # says that too, and a test that only checked the wrong things would let the
    # stronger claim back in.
    def test_a_capture_given_twice_is_refused(self):
        rc, out, err = run(ONE_BLOCK, ONE_BLOCK)
        self.assertEqual(rc, 1)
        self.assertIn(f'{ONE_BLOCK!r} is given twice', err)
        self.assertIn('A capture given twice is one console and not two', err)
        # Refused before a single mark is read, so there is no report to be
        # half-right: no per-file counts, no window count, no per-address
        # lines. Each of those is a different section of the report, so one
        # being absent does not stand in for the others.
        for absent in ('mark(s),', 'window(s), one per mark', 'window delta',
                       '=== §5\'s ten columns ==='):
            self.assertNotIn(absent, out)
        # The message names this grader's own damage, and the one figure a
        # repeat leaves alone, so a reader is not sent looking for the wrong
        # figure. `first_change` takes the earliest timestamp, so rows
        # duplicated at one timestamp collapse.
        for named in ('four windows', '????', '2 change rows', '0.0s apart',
                      "§5's millisecond figure"):
            self.assertIn(named, err)
        # One file is one console however many times it is listed, and that
        # holds for a single-mark capture as much as for a two-mark one.
        rc, out, err = run(QUIET, QUIET)
        self.assertEqual(rc, 1)
        self.assertIn('is given twice', err)
        self.assertNotIn('window delta', out)

        # Identity is by resolved path, not by the string: `./x.csv` and
        # `x.csv` are one file, and so is a symlink to it. Copied into a
        # temporary directory rather than spelled inside the fixture tree,
        # which `test_every_door_fixture_is_one_this_suite_runs` holds equal to
        # the suite's list and must not gain a name.
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / Path(ONE_BLOCK).name
            copy.write_bytes(Path(ONE_BLOCK).read_bytes())
            dotted = os.path.join(tmp, '.', copy.name)
            rc, out, err = run(str(copy), dotted)
            self.assertEqual(rc, 1)
            # Both spellings, and the one file they are, so the operator can
            # see which of the two their command line dropped.
            self.assertIn(f'{dotted!r} and {str(copy)!r}', err)
            self.assertIn(os.path.realpath(copy), err)
            self.assertNotIn('window(s), one per mark', out)
            os.symlink(copy, Path(tmp) / 'linked.csv')
            rc, out, err = run(str(copy), str(Path(tmp) / 'linked.csv'))
            self.assertEqual(rc, 1)
            self.assertIn('linked.csv', err)
            self.assertIn(os.path.realpath(copy), err)
            self.assertNotIn('window(s), one per mark', out)

        # And the same command line without the repeat is the graded run it
        # would have been: the refusal is pinned to the duplicate, not to this
        # invocation.
        rc, out, _ = run(ONE_BLOCK)
        self.assertEqual(rc, 0)
        self.assertIn('=== 2 window(s), one per mark, none merged ===', out)

    def test_two_marks_at_one_timestamp_are_refused(self):
        # A shared timestamp is what `build_windows` cannot grade, and it is
        # reachable from one file: the repeat refusal above is positional and
        # says nothing about a command line that is perfectly well formed.
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, err = run(write_capture(tmp, 'collide.csv',
                                             COLLIDING_MARKS))
        self.assertEqual(rc, 1)
        # Both labels and the instant they share, so the operator can see which
        # pair of marks to look at rather than being told only that there is
        # one.
        self.assertIn("'fn mode balanced->performance' and 'gpu tgp 115W->130W'"
                      " are both 2026-01-01T12:00:10+01:00", err)
        # The consequences are this grader's own, so a reader is not sent
        # looking for damage somewhere else, and the one figure a collision
        # leaves alone is named as firmly as those that move.
        for named in ('????', '0.0s apart', "§5's millisecond figure"):
            self.assertIn(named, err)
        self.assertIn(f'all {WATCHED} watched addresses', err)
        # And it does not claim the movement was absent where there was a
        # window to have found it. A window that spans no sweep has no level to
        # print; that is a different sentence, and it is the one used.
        for word in ('absent', 'unused', 'unreferenced'):
            self.assertNotIn(word, err)
        # Refused before any window is built, so there is no report to be
        # half-right. The four window sections are checked as four: one being
        # absent does not stand in for the others.
        for absent in ('window(s), one per mark', 'window delta',
                       "=== §5's ten columns ===",
                       '=== what this does and does not settle ==='):
            self.assertNotIn(absent, out)
        # The per-file line is *not* on that list, and its being on stdout is
        # the placement rather than a leak: this refusal needs the marks, so it
        # runs after `read_capture` where the repeat refusal above cannot. The
        # #491 test asserts `mark(s),` absent; this one asserts it present, and
        # neither is right for the other.
        self.assertIn('mark(s),', out)

    def test_the_single_mark_control_of_a_collided_capture_is_graded(self):
        # The same capture with the second mark deleted, which is the control
        # the issue asks for: the phantom belongs to the duplicate mark, not
        # to the change rows or the labels around it.
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, _ = run(write_capture(tmp, 'control.csv',
                                           COLLIDING_MARKS[:1]))
        self.assertEqual(rc, 0)
        self.assertIn('=== 1 window(s), one per mark, none merged ===', out)
        # The one window carries the movement the collided pair would have put
        # in the second of the two, with the offsets it really has.
        self.assertIn('0x07C4  0x08 -> 0x28   (+0.4s)   DBEN b3, DBST b5', out)
        self.assertIn('0x0743  0x00 -> 0x0A   (+1.9s)   GNEN b0, ECDC b1', out)
        # Every address gets its line, as in any window: a refusal upstream is
        # not a reason to drop the address table the control is here to check.
        self.assertEqual(out.count('window delta'), WATCHED)
        # And the figure the refusal's message says a collision does not move
        # is in this one-window report, so the claim is checkable against
        # something rather than asserted.
        self.assertEqual(ordering_lines(out), [
            '    which block moved first: 0x07C4-0x07D7 (0x07C4, +0.4s after '
            'the mark)',
            '      led 0x0743-0x0746 (0x0743, +1.9s after the mark) by 1500 ms',
        ])

    def test_two_marks_a_millisecond_apart_are_two_windows(self):
        # The near-miss guard, and the reason the check compares for equality
        # rather than for proximity. A widened check would take over
        # `CLOSE_MARKS_SECONDS`' job and undo "marks are not merged, on
        # purpose"; this holds the width at nothing at all.
        near = (COLLIDING_MARKS[0],
                ('2026-01-01T12:00:10.001+01:00', 'gpu tgp 115W->130W'))
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, err = run(write_capture(tmp, 'near.csv', near))
        self.assertEqual(rc, 0)
        self.assertEqual(err, '')
        self.assertIn('=== 2 window(s), one per mark, none merged ===', out)
        # The one-millisecond window is still a window: 1 ms is a small
        # fraction of the 0.25 s `--interval` that decides what a sweep is, so
        # it takes no change row and says so, and a merge would have hidden
        # exactly that.
        self.assertIn('no ordering to report: neither block moved in this '
                      'window', out)
        # The movement is in the second window, and the ms figure the refusal
        # says a collision does not move is the same one the control reported.
        self.assertEqual(ordering_lines(out), [
            '    which block moved first: 0x07C4-0x07D7 (0x07C4, +0.4s after '
            'the mark)',
            '      led 0x0743-0x0746 (0x0743, +1.9s after the mark) by 1500 ms',
        ])

    def test_a_collision_written_two_ways_is_one_instant(self):
        # The check is on the parsed datetime, not on the string, which is what
        # "assembled by hand from two files" means in practice: the same
        # instant written without its milliseconds, and again at another UTC
        # offset. A string compare would call each of these two marks and
        # report a run whose windows cannot be told apart.
        spellings = (
            ('no milliseconds', '2026-01-01T12:00:10+01:00'),
            ('another UTC offset', '2026-01-01T11:00:10.000+00:00'),
        )
        for why, second_ts in spellings:
            with self.subTest(why):
                marks = (COLLIDING_MARKS[0], (second_ts, 'gpu tgp 115W->130W'))
                with tempfile.TemporaryDirectory() as tmp:
                    rc, out, err = run(write_capture(tmp, 'spelled.csv',
                                                     marks))
                self.assertEqual(rc, 1, why)
                self.assertIn("'fn mode balanced->performance' and "
                              "'gpu tgp 115W->130W' are both", err)
                self.assertNotIn('window(s), one per mark', out)
        # And the near-miss half of the same spelling question: a real
        # millisecond at either spelling is still a millisecond, so the
        # equality is on the instant and not on a canonical string.
        for second_ts in ('2026-01-01T12:00:10.001+01:00',
                          '2026-01-01T11:00:10.001+00:00'):
            with self.subTest(second_ts):
                marks = (COLLIDING_MARKS[0], (second_ts, 'gpu tgp 115W->130W'))
                with tempfile.TemporaryDirectory() as tmp:
                    rc, out, _ = run(write_capture(tmp, 'offset.csv', marks))
                self.assertEqual(rc, 0, second_ts)
                self.assertIn('=== 2 window(s), one per mark, none merged ===',
                              out)


if __name__ == '__main__':
    unittest.main()
