#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

manual_fan_ctrl_probe.py imports ecrw, which binds kernel32 at import time and
so only loads on Windows -- ecrw_fake.py stands in for the whole module, and
the FakeEc below scripts the two arms byte by byte on top of it.

The script is keyed on the arm and the sweep within it, not on a timestamp, so
what a byte does is an assertion about the run's shape -- the no-op moves PWM,
the write moves the other one, both move the temperature -- and not about how
many sweeps a given hold happens to buy.
"""
import contextlib
import csv
import datetime
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ecrw_fake

ORIG = 0x10
TARGET = 0xA0

# addr -> (values by sweep in the control arm, values by sweep in the write
# arm), the last entry repeating. 0x075B drifts under the no-op and 0x075C
# under the write, and neither moves in the other arm, which is what makes
# "the two arms' PWM motion stayed apart" checkable rather than asserted.
# Both temperature bytes move in both arms, which is the "did 0x043E hold
# steady across both" reading §4.5 needs.
#
# The 0x086x entries are inert without --level-block, which is what makes
# "the flag is opt-in" checkable: the default run never reads these addresses
# and its output is unchanged by their being here. 0x0860 is given the busy
# mark and its return to idle inside the write arm, 0x086B and 0x086E are both
# given a clamp value, and 0x086C is left holding one value for the whole run
# -- three different report lines, and the one that proves a byte which never
# moved is still reported as seen.
SCRIPT = {
    0x075B: ([0x10, 0x28, 0x30], [0x30, 0x30, 0x30]),
    0x075C: ([0x00, 0x00, 0x00], [0x00, 0x50, 0x70]),
    0x043E: ([0x40, 0x42, 0x43], [0x43, 0x45, 0x46]),
    0x044F: ([0x50, 0x52, 0x53], [0x53, 0x55, 0x56]),
    0x0860: ([0x00], [0x00, 0xFF, 0x00]),
    0x086B: ([0x1F], [0x1F, 0x23]),
    0x086C: ([0x20], [0x20]),
    0x086E: ([0x22], [0x22, 0x23]),
}

ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'manual_fan_ctrl_probe', Path(__file__).with_name('manual_fan_ctrl_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

# The grader the --csv capture is written for, imported by path the way the
# probe's own --self-test imports it. What a MARK row means to the tool and
# what it means to the reader are two things, and only the second one settles
# whether the capture is the shape the reader already has.
GRADER_PATH = Path(__file__).resolve().parents[2] / "ec" / "tools" \
    / "grade_0751_isolation.py"
grader_spec = importlib.util.spec_from_file_location(
    'grade_0751_isolation', GRADER_PATH)
grader = importlib.util.module_from_spec(grader_spec)
grader_spec.loader.exec_module(grader)


def run_grader(*argv):
    """The real grader over `argv`, as (rc, stdout, stderr).

    `run` in the grader's own suite, for the same reason: the probe's
    `--self-test` walks the block by hand, and the case that matters is the
    one the whole report and the exit code come from, neither of which
    exists until `main` has run.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = grader.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


# §6's label forms with the value blanked out, so "is one of the forms §6
# fixes" is a question about the words and not about the one value §6's
# example happens to carry: a run taken from 0xE0 writes
# `no-op wrote 0x0751=0xE0`, which is equal to no entry of the grader's own
# REQUIRED_LABEL_FORMS and is still the form.
REQUIRED_FORMS = {grader.MARK_VALUE.sub("0x<value>", f)
                  for f in grader.REQUIRED_LABEL_FORMS}


def is_required_form(label):
    """Whether `label` is one of the grader's required forms, value aside."""
    return grader.MARK_VALUE.sub("0x<value>", label) in REQUIRED_FORMS


class FakeEc:
    """A watch set where a sweep ends at its last address.

    snap() reads every address of the set in order, so the last one closes the
    sweep. Keying off that rather than off a raw read count keeps the two bare
    0x0751 reads -- the original and the final readback -- from shifting every
    value the arms see. A write starts a new arm, which is what makes the
    script's two lists mean what they say.

    `addrs` is the set the run was asked for, because --level-block and
    --watch-page both make the watch set a runtime choice and this closes its
    sweeps on whichever address that choice ends at. `block` moves that
    boundary: --block reads the set as ascending runs, so the address the
    sweep closes on is the set's highest rather than the last of the list, and
    a fake that kept the list order would advance the script one address early
    and fail as wrong values.

    The list order is kept rather than only its set, because the byte path's
    boundary is `addrs[-1]` -- the last address `snap` reads -- and a fake that
    took the boundary from a module constant would close a page-arm run's
    sweeps on a page it never sweeps, landing every scripted value on the
    wrong sweep. `test_the_sweep_ends_on_the_same_address_in_every_set` holds
    the tool's side of that.

    `readmany` is the --block path's, and it is a whole run rather than four
    bytes: the per-address path underneath is the byte path's, with the bytes
    a block covered but the set did not ask for skipped, so both paths see the
    same values and the same sweep boundaries.
    """

    def __init__(self, orig=ORIG, boom_at=None, addrs=None, block=False):
        self.mode = orig
        self.writes = []        # (addr, value) in order, restore last
        self.writes_at = []     # bytes already read when each write landed
        self.reads = 0
        self.boom_at = boom_at
        self.blocks = []        # (start, length) per readmany call
        self.point_reads = []   # addresses that came through read() alone
        self._addrs = list(addrs if addrs is not None else probe.ALL)
        self._set = set(self._addrs)
        self._sweep = 0         # within the current arm
        self._last = max(self._addrs) if block else self._addrs[-1]

    def read(self, addr):
        self.point_reads.append(addr)
        return self._read(addr)

    def _read(self, addr):
        if self.boom_at is not None and self.reads == self.boom_at:
            raise RuntimeError("observation failed mid-run")
        if addr == self._last:
            self._sweep += 1
        self.reads += 1
        if addr == 0x0751:
            return self.mode
        values = SCRIPT.get(addr)
        if values is None:
            return 0x00
        arm = values[0] if len(self.writes) < 2 else values[1]
        return arm[min(self._sweep, len(arm) - 1)]

    def readmany(self, start, length):
        self.blocks.append((start, length))
        return {a: self._read(a) for a in range(start, start + length)
                if a in self._set}

    def write(self, addr, val):
        self.writes.append((addr, val))
        self.writes_at.append(self.reads)
        if addr == 0x0751:
            self.mode = val
            self._sweep = 0


class Clock:
    """A counter for time.time, so a hold buys a fixed number of sweeps.

    `slept` records what the run asked to sleep for, so the cadence can be
    asserted without counting sweeps: the sweep interval is a number the
    operator chose, and the only place it becomes visible is the argument
    time.sleep gets.

    `now` stamps the capture off the same timeline, and it has to: the two
    arm boundaries are a hold apart on this clock but microseconds apart on the
    wall clock, and the grader's `coalesce_marks` folds marks within five
    seconds of each other into one window. A capture written with real
    timestamps under a fake clock would put both arms in a single window and
    the windowing tests would pass for the wrong reason. One clock for a
    second run is therefore also what makes an appended capture's rows ordered
    the way a real one is.
    """

    def __init__(self, step=0.1, base=1700000000.0, stamp=0.001):
        self.t = 0.0
        self.base = base
        self.step = step
        # What one `now()` call moves the clock by, and it moves it because
        # the wall clock does: two stamps taken in a row are never the same
        # instant. The early-exit row is the one that depends on it -- it is
        # written after the last sweep of the arm and before the restore's
        # mark, with nothing in between to advance a counter -- so on a clock
        # that stood still it would carry the restore's timestamp and land in
        # the restore's window, which is the window it was written before.
        self.stamp = stamp
        self.slept = []

    def time(self):
        self.t += self.step
        return self.t

    def now(self):
        here = (datetime.datetime.fromtimestamp(self.base + self.t)
                .astimezone().isoformat(timespec="milliseconds"))
        self.t += self.stamp
        return here

    def sleep(self, s):
        self.slept.append(s)


class ProbeTests(unittest.TestCase):
    def run_probe(self, argv=('0xA0', '30'), ec=None, clock=None, **kw):
        argv = list(argv)
        ec = ec if ec is not None else FakeEc(
            addrs=probe.watch_set('--level-block' in argv,
                                  '--watch-page' in argv),
            block='--block' in argv, **kw)
        clock = clock if clock is not None else Clock()
        out = io.StringIO()
        with patch.object(probe, 'Ec', lambda: ec), \
             patch.object(probe.time, 'time', clock.time), \
             patch.object(probe.time, 'sleep', clock.sleep), \
             patch.object(probe, 'now', clock.now), \
             contextlib.redirect_stdout(out):
            probe.main(argv)
        return ec, out.getvalue()

    # 1. The control window opens before the write, and restores last.
    def test_control_write_precedes_the_write_under_test(self):
        ec, _ = self.run_probe()
        self.assertEqual(ec.writes,
                         [(0x0751, ORIG), (0x0751, TARGET), (0x0751, ORIG)])

    def test_a_full_sweep_is_observed_between_the_two_writes(self):
        ec, _ = self.run_probe()
        control, target = ec.writes_at[0], ec.writes_at[1]
        self.assertGreaterEqual(target - control, len(probe.ALL))

    # 2. The no-op is labelled so the grader can tell it apart. Dropping the
    #    "no-op " prefix is the regression grade_0751_isolation.py cannot
    #    survive: it windows on marks.
    def test_no_op_mark_is_distinguishable_from_the_write(self):
        _, out = self.run_probe()
        lines = out.splitlines()
        self.assertIn("no-op wrote 0x0751=0x10", lines)
        self.assertIn("wrote 0x0751=0xA0", lines)
        self.assertTrue([l for l in lines
                         if l.startswith("wrote ") and not l.startswith("no-op ")])

    # 3. The temperature bytes the PWM reading is taken against are watched.
    def test_both_temperature_bytes_move_in_both_arms(self):
        _, out = self.run_probe()
        control = out[out.index("no-op wrote"):out.index("wrote 0x0751=0xA0")]
        written = out[out.index("wrote 0x0751=0xA0"):out.index("SUMMARY")]
        for arm in (control, written):
            for a in (0x043E, 0x044F):
                self.assertIn(f"0x{a:04X}:", arm)

    def test_summary_carries_a_line_per_temperature_byte(self):
        _, out = self.run_probe()
        for a, name in ((0x043E, "CPU_TEMP"), (0x044F, "GPU_TEMP")):
            line = [l for l in out.splitlines() if l.startswith(f"{name} 0x{a:04X}:")]
            self.assertEqual(len(line), 1)
            self.assertIn("control", line[0])
            self.assertIn("write", line[0])

    # 4. Never the fan-tach bytes (issue #94).
    def test_watch_set_stops_before_the_fan_tach(self):
        self.assertEqual(set(probe.ALL) & set(range(0x0460, 0x0470)), set())
        self.assertIn(0x045F, probe.ALL)
        self.assertNotIn(0x0460, probe.ALL)
        # Every set the tool can be asked for, not just the default one: each
        # of these flags widens what a run reads, and a widening that reached
        # the page is a wider access to it rather than a safer one. Named one
        # at a time rather than as a range, because 0x046A is the
        # destination of the 0x9CA6 sync the level-block doc is not allowed to
        # read (docs/hardware-tests/level-block-0860-086e.md §6): a byte that
        # is both a level-block answer and on the forbidden page is the one
        # this has to keep out, and asserting the range's endpoints would miss
        # it.
        sets = (probe.watch_set(), probe.watch_set(level_block=True),
                probe.watch_set(watch_page=True),
                probe.watch_set(level_block=True, watch_page=True))
        for addrs in sets:
            self.assertIn(0x045F, addrs)
            for a in (0x0460, 0x046A, 0x046F):
                self.assertNotIn(a, addrs)
            self.assertEqual(set(addrs) & set(range(0x0460, 0x0470)), set())

    # 5. The whitelist constrains the value under test, not the control arm's
    #    re-write: a board sitting in a mode the tool does not target still
    #    runs, and a target outside the vendor set is refused before any EC is
    #    opened.
    def test_control_write_is_not_gated_on_the_whitelist(self):
        ec, out = self.run_probe(ec=FakeEc(orig=0xE0))
        self.assertEqual(ec.writes[0], (0x0751, 0xE0))
        self.assertIn("no-op wrote 0x0751=0xE0", out)

    def test_target_outside_the_vendor_set_is_refused_before_opening_the_ec(self):
        opened = []
        with patch.object(probe, 'Ec', lambda: opened.append(1)):
            with self.assertRaises(SystemExit) as cm:
                probe.main(['0xE0'])
        # The refusal itself, not any SystemExit: argparse exits 2 on a
        # mistyped flag, so the bare assertion would pass for a run that never
        # looked at the value. `sys.exit(msg)` carries the message as the
        # exception's code, and only prints it if nothing catches it.
        self.assertEqual(cm.exception.code,
                         "value 0xE0 not in the vendor set {0x00,0x10,0xA0}")
        self.assertEqual(opened, [])

    def test_a_mistyped_flag_is_a_usage_error_not_a_whitelist_refusal(self):
        with patch.object(probe, 'Ec', lambda: self.fail("opened an EC")), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                probe.main(['0xA0', '--intervl', '0.5'])
        self.assertEqual(cm.exception.code, 2)

    # 6. The restore is the outermost guard, so it runs even when the control
    #    arm's observation blows up.
    def test_restore_runs_when_the_control_arm_raises(self):
        ec = FakeEc(boom_at=len(probe.ALL) + 2)
        with self.assertRaises(RuntimeError):
            self.run_probe(ec=ec)
        self.assertEqual(ec.writes, [(0x0751, ORIG), (0x0751, ORIG)])

    # 7. The SUMMARY names the control arm's movement the baseline the write
    #    has to beat, and does not merge the two arms' PWM motion.
    def test_summary_reports_the_control_arm_as_the_baseline(self):
        _, out = self.run_probe()
        summary = out[out.index("SUMMARY"):]
        control = summary[:summary.index("write under test --")]
        written = summary[summary.index("write under test --"):]
        self.assertIn("the baseline the write under test has to beat", control)
        self.assertIn("0x075B", control)
        self.assertNotIn("0x075B", written)
        self.assertNotIn("0x075C", control)
        self.assertIn("0x075C", written)

    # 8. The defaults are the procedure's, and this is what stops the two files
    #    that each claim to be §3 from carrying different numbers again (#146).
    def test_the_default_hold_is_the_procedures_thirty_seconds(self):
        _, out = self.run_probe(argv=('0xA0',))
        # Read off the banner rather than counted out of 300 fake sweeps: the
        # default is a number the operator reads before pressing anything, so
        # that is where it has to be right.
        self.assertIn("holding 30s each", out)

    def test_the_default_cadence_is_the_procedures_half_second(self):
        clock = Clock()
        _, out = self.run_probe(argv=('0xA0',), clock=clock)
        self.assertIn("sweeping every 0.5s", out)
        # 0.4 is the restore's settle sleep rather than the sweep cadence, so
        # it is excluded instead of comparing the whole recorded set.
        self.assertEqual(set(clock.slept) - {0.4}, {0.5})

    def test_the_interval_flag_reaches_the_sweep(self):
        clock = Clock()
        _, out = self.run_probe(argv=('0xA0', '30', '--interval', '1.25'),
                                clock=clock)
        self.assertIn("sweeping every 1.25s", out)
        self.assertEqual(set(clock.slept) - {0.4}, {1.25})

    def test_the_banner_carries_the_unvalidated_interval_caveat(self):
        _, out = self.run_probe(argv=('0xA0',))
        # 0.5 s is a starting point and nothing more -- #94 is the open work
        # that would make these tools safe by default -- so the run has to say
        # so where the operator is deciding whether to leave it there.
        self.assertIn("no interval here is validated", out)
        self.assertIn("fans audibly change, stop", out)

    # The tool states a measurement, not a verdict.
    def test_summary_grades_nothing(self):
        _, out = self.run_probe()
        self.assertNotIn("confirmed-working", out)
        self.assertNotIn("confirmed-inert", out)

    # A drifting byte reports the arm's net, first to last, with the count --
    # one of the three movement figures the grader prints as a `window delta`,
    # and the one that reads best on a clean monotonic step. Reporting the
    # last step instead would understate a slow drift by the movement between
    # the first and second change. §4.4 keys its control-vs-write comparison
    # on *total* movement rather than on this net, which the grader prints and
    # this tool leaves to the reader to sum from the change rows.
    def test_a_drifting_byte_reports_its_net_not_its_last_step(self):
        _, out = self.run_probe()
        control = out[out.index("control arm --"):out.index("write under test --")]
        self.assertIn("0x075B: 0x10 -> 0x30 (2 changes)", control)
        self.assertIn("0x043E: 0x40 -> 0x43 (2 changes)", control)

    # 9. The level block (#252). Opt-in, so the #99/#122 run's footprint is
    #    still the 206 the committed run was taken at, and 222 with the flag.
    def test_the_level_block_is_opt_in(self):
        self.assertEqual(len(probe.ALL), 206)
        self.assertEqual(len(probe.watch_set(level_block=True)), 222)
        for a in (0x0860, 0x0865, 0x086B, 0x086E, 0x06E6):
            self.assertNotIn(a, probe.watch_set())
            self.assertIn(a, probe.watch_set(level_block=True))
        # xdata-086x-dispatch.md's clamp guards and gates ride along in TEMP
        # rather than costing 16 more reads: a doc that added them again would
        # be reading
        # the same bytes twice per sweep.
        for a in (0x0440, 0x0442):
            self.assertIn(a, probe.watch_set(level_block=True))
        self.assertEqual(len(set(probe.LEVEL) & set(probe.ALL)), 0)

    def test_the_widen_sweep_closes_on_the_last_added_address(self):
        # The FakeEc's sweep boundary is the last address read, so a set whose
        # tail is the fan table while the run's is the level block would make
        # every scripted value land on the wrong sweep. Worth its own case: it
        # fails as a wrong number rather than as a crash. The tail is 0x06E6
        # and not 0x086E, because the gate byte is appended after the run.
        self.assertEqual(probe.watch_set(level_block=True)[-1], 0x06E6)
        self.assertEqual(probe.watch_set()[-1], 0x045F)

    def test_the_banner_states_the_widened_sweep_and_the_read_only_path(self):
        _, out = self.run_probe(argv=('0xA0', '--level-block'))
        self.assertIn("222 ECRR reads per sweep", out)
        self.assertIn("0x0860-0x086E and 0x06E6", out)
        self.assertIn("nothing there is written", out)

    def test_the_level_block_report_keeps_the_clamped_results_apart(self):
        # §5 of xdata-086x-dispatch.md gives 0x086B and 0x086C the three
        # clamps and 0x086E none. The script is given the same value on 0x086B
        # and 0x086E, so one line reading "clamp value(s) 0x23" and the other
        # reading the same thing is the failure this pins.
        _, out = self.run_probe(argv=('0xA0', '--level-block'))
        report = out[out.index("level block (--level-block)"):]
        self.assertIn("0x086B  seen at 0x1F 0x23  -- clamp value(s) 0x23",
                      report)
        self.assertIn("0x086C  seen at 0x20  -- clamp values 0x23/0x14/0x0F: "
                      "none", report)
        self.assertIn("0x086E  seen at 0x22 0x23  -- no clamps: 0x23/0x14/0x0F "
                      "mean nothing here", report)

    def test_the_busy_mark_line_names_the_window_it_was_seen_in(self):
        _, out = self.run_probe(argv=('0xA0', '--level-block'))
        report = out[out.index("level block (--level-block)"):]
        self.assertIn("control arm -- no-op wrote 0x0751=0x10", report)
        self.assertIn("write under test -- wrote 0x0751=0xA0", report)
        # 0x0860 is scripted 0x00 -> 0xFF -> 0x00 under the write and 0x00
        # throughout the control arm, so the two arms have to disagree about
        # the busy mark rather than the report naming it once.
        arms = report.split("write under test --")
        self.assertIn("busy mark 0xFF: not seen", arms[0])
        self.assertIn("0x0860  seen at 0x00 0xFF  -- busy mark 0xFF: SEEN",
                      arms[1])
        # ...and the gap it cannot close has to be on the report, because a
        # "not seen" line with no caveat reads as an absence rather than as
        # "not found at this interval" (CLAUDE.md, calibrate don't overclaim).
        self.assertIn("between two sweeps leaves no row", report)
        self.assertIn("--interval is the only lever", report)

    def test_a_level_byte_that_never_moves_is_still_reported_as_seen(self):
        # 0x086C holds one value for the whole run, so it produces no change
        # row anywhere. A report built on the change rows would print it as
        # never read, which is the opposite of what a level block does.
        _, out = self.run_probe(argv=('0xA0', '--level-block'))
        self.assertIn("0x086C  seen at 0x20", out)
        self.assertNotIn("(never read)", out)

    def test_no_level_block_report_without_the_flag(self):
        # The four bytes are outside the default set, so reporting them
        # unconditionally would either be a KeyError or, worse, four lines
        # claiming a reading the run never took.
        _, out = self.run_probe()
        self.assertNotIn("level block (--level-block)", out)
        self.assertNotIn("0x0860", out)

    # 10. --csv writes the capture the grader already reads, and its marks land
    #     on the two arm boundaries and the restore. This is #124's attachment
    #     point, and the reason to check it is the grader, not the writer: a
    #     mark in the wrong place windows every change under the wrong arm and
    #     still exits zero, and a mark that is not written at all refuses the
    #     whole block.
    def capture_path(self, argv, ec=None, clock=None):
        """(path, stdout) for a `--csv` run, in a file this case owns.

        The path rather than the text, because the case that matters hands it
        to the real grader as a file, and a fresh one per call so a case
        cannot be reading a capture a previous case left behind. The
        directory is `addCleanup`ed rather than a `with`, so the file is still
        there for the assertions after the run.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "capture.csv"
        _, out = self.run_probe(argv=list(argv) + ['--csv', str(path)],
                                ec=ec, clock=clock)
        return path, out

    def capture(self, argv, **kw):
        path, _ = self.capture_path(argv, **kw)
        return path.read_text()

    def mark_rows(self, path):
        """The labels on a capture's `MARK` rows, in the order they landed."""
        return [r[3] for r in csv.reader(path.read_text().splitlines())
                if len(r) == 4 and r[1] == "MARK"]

    def test_the_capture_is_the_shape_the_grader_reads(self):
        text = self.capture(('0xA0', '--level-block'))
        rows = list(csv.reader(text.splitlines()))
        self.assertEqual(rows[0], ["ts", "addr", "old", "new"])
        for row in rows[1:]:
            self.assertEqual(len(row), 4, row)
        # And through the real reader, not just past a shape assertion.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            path.write_text(text)
            marks, changes = grader.read_capture(str(path))
        # All three, the restore included: the reader has read two of these
        # and rejected none, which is exactly why the third going missing was
        # invisible until the block walk was added (#457).
        self.assertEqual([m.label for m in marks],
                         list(probe.arm_labels(ORIG, TARGET)))
        self.assertTrue(changes)
        self.assertTrue(all(0 <= c.addr <= 0xFFFF for c in changes))

    def test_the_marks_are_the_ones_the_grader_windows_on(self):
        path, _ = self.capture_path(('0xA0',))
        labels = self.mark_rows(path)
        # What the tool writes, and nothing else: a second spelling of a label
        # is a spelling that agrees today and drifts tomorrow, and a drifted
        # one is a mark `parse_mark` cannot place, which refuses a whole run.
        self.assertEqual(labels, list(probe.arm_labels(ORIG, TARGET)))
        self.assertEqual([grader.parse_mark(l) for l in labels],
                         [("control", ORIG), ("write", TARGET),
                          ("restore", ORIG)])
        for label in labels:
            self.assertTrue(is_required_form(label), label)
        # The restore names the value being put back, not the one that was
        # under test, and it is the block's last mark: both are what the
        # grader's void check turns on.
        self.assertEqual(labels[-1],
                         f"restored 0x{probe.MODE:04X}=0x{ORIG:02X}")
        self.assertNotEqual(labels[-1], labels[1])

    def test_a_probe_capture_passes_the_real_grader_end_to_end(self):
        # The issue's done-condition: a capture this tool wrote, read by the
        # grader the runbook points at, coming back one block, intact, three
        # roles, every window printed and exit 0. Before the restore mark this
        # was the same run reported VOID with both arms withheld, in the
        # format §7's `confirmed-inert` call would otherwise have quoted.
        path, _ = self.capture_path(('0xA0',))
        rc, out, err = run_grader(str(path))
        self.assertEqual(rc, 0, err)
        self.assertIn("block 1/1: intact", out)
        self.assertIn("value under test 0xA0; roles control, write, restore",
                      out)
        # Every window printed, in the windowed report rather than in place of
        # it, and nothing anywhere says one of them was withheld.
        for n in (1, 2, 3):
            self.assertIn(f"--- mark {n}/3:", out)
        # `NOT GRADED` in capitals is the block and withheld-window marker,
        # and nothing else in the report spells it that way -- the
        # "context, not graded here" banner over the duty and temperature
        # bytes is printed on every window of every run and means the
        # opposite.
        self.assertNotIn("NOT GRADED", out)

    def test_each_arm_s_change_rows_land_in_its_own_window(self):
        path, _ = self.capture_path(('0xA0', '--level-block'))
        windows = grader.build_windows(*grader.read_capture(str(path)))
        self.assertEqual(len(windows), 3)
        control, written, restored = windows
        # 0x075B drifts under the no-op and 0x075C under the write, and the
        # two arms' movement stayed apart: attributing either to the other
        # mark is exactly the defect a mislabelled mark produces.
        self.assertTrue(any(c.addr == 0x075B for c in control.changes))
        self.assertFalse(any(c.addr == 0x075C for c in control.changes))
        self.assertTrue(any(c.addr == 0x075C for c in written.changes))
        # The level block's own row, in the write arm's window.
        self.assertTrue(any(c.addr == 0x0860 and c.new == 0xFF
                            for c in written.changes))
        # And the restore's window is the restore's, carrying neither arm's
        # movement: it opens after the write arm's last sweep, so a row filed
        # in it is a row attributed to an action that did not cause it.
        self.assertEqual(grader.parse_mark(restored.label), ("restore", ORIG))
        self.assertFalse([c.addr for c in restored.changes])

    def test_the_restore_line_and_the_capture_row_are_the_same_string(self):
        # §3's by-eye check is a reader looking at the terminal and the file
        # at once, so the two have to say the same thing. A restore that
        # reached the screen and not the CSV is the case the void check
        # exists for, and a readback standing in for the mark is how that
        # happens without anybody noticing.
        path, out = self.capture_path(('0xA0',))
        restored = self.mark_rows(path)[-1]
        self.assertIn(restored, out.splitlines())
        # The readback stays a line of its own and says what it is: four
        # matching readbacks are a statement about writes, not about what the
        # EC did with the byte (CLAUDE.md).
        readback = [l for l in out.splitlines() if "readback" in l]
        self.assertEqual(len(readback), 1)
        self.assertIn("not evidence the EC acted on it", readback[0])
        self.assertNotIn(restored, readback[0])

    def crashed_capture(self, argv=('0xA0',)):
        """(path, ec) for a `--csv` run that dies part way through the write.

        A crash far enough in that the three marks are still more than the
        grader's `MARK_MERGE_SECONDS` apart, which is what keeps the capture
        three windows rather than one coalesced label. A crash on the arm's
        first sweep coalesces the write and the restore into one window
        instead, and the block reads VOID; the grader is right to say so
        there, and these cases are about the one it used to miss. Where the
        crash goes is learned from a run that did not crash rather than
        counted here, because the number of reads a sweep costs is the fake's
        own.
        """
        plain = FakeEc()
        self.run_probe(argv=list(argv), ec=plain, clock=Clock(step=0.5))
        crashed = FakeEc(boom_at=plain.writes_at[1] + 1 + 30 * len(probe.ALL))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "capture.csv"
        with self.assertRaises(RuntimeError):
            self.run_probe(argv=list(argv) + ['--csv', str(path)], ec=crashed,
                           clock=Clock(step=0.5))
        return path, crashed

    def test_a_crashed_run_records_why_and_still_closes_its_block(self):
        path, crashed = self.crashed_capture()
        # The capture is flushed per row and closed through the readback's own
        # `finally`, so this is the whole of what the operator would find in
        # the file: the three marks, the row, and the restore's mark.
        self.assertEqual(self.mark_rows(path),
                         list(probe.arm_labels(ORIG, TARGET)))
        self.assertEqual(crashed.writes[-1], (probe.MODE, ORIG))
        rc, out, err = run_grader(str(path))
        windows = grader.build_windows(*grader.read_capture(str(path)))
        # Exit 1, where this case used to pin 0 over a write window cut at 30
        # sweeps. The restore landed, so its mark landed, so the block is
        # intact -- and the row the handler wrote is the whole of the
        # difference between that and a block that ran its hold. Both facts
        # are on the block line, which is where they read alike.
        self.assertEqual(rc, 1, err)
        self.assertIn("block 1/1: intact", out)
        self.assertIn("roles control, write, restore", out)
        self.assertIn("NOT GRADED, its windows are not printed", out)
        # The read line counts it, on the path where the "no MARK rows"
        # refusal fires before anything else this tool prints.
        self.assertIn("capture.csv: 3 mark(s), ", out)
        self.assertIn("1 early-exit row(s)", out)
        # And the section above the windows names it, with the window and the
        # block it fell in and the reason quoted rather than summarised. The
        # report wraps at 72 columns, so the prose is read flat.
        flat = " ".join(out.split())
        self.assertIn("=== early-exit rows (a run that did not reach its "
                      "hold) ===", out)
        self.assertIn("in mark 2/3 ('wrote 0x0751=0xA0') of block 0xA0 "
                      "(block 1 of 1)", flat)
        self.assertIn("manual_fan_ctrl_probe: RuntimeError: observation "
                      "failed mid-run", flat)
        # The whole block's windows are withheld, not the one the row fell in:
        # the capture cannot say which arms before the cut are still worth
        # reading, and the control arm's was a full hold -- which is why the
        # section, not a per-window line, is what says the run stopped.
        self.assertEqual(len(windows), 3)
        for n in (1, 2, 3):
            self.assertIn(f"--- mark {n}/3:", out)
        self.assertEqual(out.count("block: 0xA0 (block 1 of 1) -- NOT GRADED"),
                         3)
        self.assertNotIn("no watched byte moved in this window", out)
        # The write window really is short, and the report above says so where
        # the arithmetic cannot: it runs to the crash rather than to the end of
        # the hold. The change rows are the same count either way, the script
        # having saturated after three sweeps, which is the point -- the
        # truncation is not a thing the windows can show, and a grader that
        # printed them anyway would be grading the short window in the same
        # format as the long one.
        full, _ = self.capture_path(('0xA0',), clock=Clock(step=0.5))
        held = grader.build_windows(*grader.read_capture(str(full)))
        self.assertLess((windows[2].ts - windows[1].ts).total_seconds(),
                        (held[2].ts - held[1].ts).total_seconds())
        self.assertEqual(len(windows[1].changes), len(held[1].changes))

    # The row the writer writes and the rule the reader applies have to agree
    # on *where* the run stopped, not only that one of them knows it stopped.
    def test_the_early_exit_row_lands_in_the_arm_that_raised(self):
        path, _ = self.crashed_capture()
        early = grader.read_early_exits(str(path))
        self.assertEqual(len(early), 1)
        control, written, restored = grader.build_windows(
            *grader.read_capture(str(path)))
        # The row is stamped off the same clock as the marks, so the reader's
        # rule -- the last window at or before the row -- puts it in the write
        # arm, which is where the fake raised. The restore's mark is after it,
        # which is what leaves the block intact rather than void.
        self.assertGreater(early[0].ts, control.ts)
        self.assertGreaterEqual(early[0].ts, written.ts)
        self.assertLess(early[0].ts, restored.ts)
        # And the reason is the exception, not the tag: the grader quotes it
        # and claims nothing about who wrote the row.
        self.assertEqual(early[0].reason,
                         "manual_fan_ctrl_probe: RuntimeError: observation "
                         "failed mid-run")

    # The two spellings of the tag cannot be one constant -- `ecrw` binds
    # kernel32 at import time, so the grader cannot import this tool -- and a
    # drift between them fails nowhere else: the grader would match no row and
    # every crashed run's capture would grade as one that finished. Pinned
    # here against the real grader, by path, and again in the `--self-test` a
    # human runs at the box.
    def test_the_early_exit_tag_is_the_phrase_the_grader_reads(self):
        self.assertEqual(probe.EARLY_EXIT_TAG, grader.EARLY_EXIT_TAG)

    def test_a_second_run_appends_to_the_same_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            # One clock for both runs, so the second run's rows are stamped
            # after the first's the way a real second run's are.
            clock = Clock()
            self.run_probe(argv=['0xA0', '--csv', str(path)], clock=clock)
            first = path.read_text()
            # The second run opens a session later, the way a §3 day does.
            # One clock keeps the two runs' rows in order, which is what it
            # was for; the later epoch is the gap between them, and without it
            # the second run's first mark lands on the first run's last and
            # the grader's coalescing folds the two into one window -- a
            # capture shape no operator produces, since starting the next run
            # is a thing that takes seconds.
            self.run_probe(argv=['0x00', '--csv', str(path)],
                           clock=Clock(base=clock.base + 600))
            both = path.read_text()
            marks, changes = grader.read_capture(str(path))
            windows = grader.build_windows(marks, changes)
            blocks, unplaced = grader.assign_blocks(windows)
        self.assertTrue(both.startswith(first))
        self.assertEqual(both.count("ts,addr,old,new"), 1)
        self.assertIn("wrote 0x0751=0x00", both)
        # §4 wants three modes in one session, so the third run's two arms
        # have to extend the file rather than replace it. The second run's
        # control arm re-writes 0x10, not 0x00, because the first run's
        # finally restored 0x0751 -- a later epoch does not get to pretend
        # otherwise, or the restore would be untested here too. Each run
        # appends a whole block, so both are there to be read.
        self.assertEqual(both.count(",MARK,"), 6)
        self.assertEqual([m.label for m in marks],
                         list(probe.arm_labels(ORIG, TARGET))
                         + list(probe.arm_labels(ORIG, 0x00)))
        self.assertEqual(len(windows), 6)
        # Two blocks rather than one long one, each closed by its own
        # restore: the cheapest proof the block walk survives being appended
        # to, and the shape a three-value session is.
        self.assertEqual(len(blocks), 2)
        self.assertFalse(unplaced)
        self.assertEqual([b.roles for b in blocks],
                         [["control", "write", "restore"]] * 2)
        self.assertEqual([grader.block_verdict(b) for b in blocks],
                         ["intact"] * 2)

    def test_no_capture_is_written_without_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            self.run_probe(argv=['0xA0'])
            self.assertFalse(path.exists())

    # A `--csv` run's hold is held to the grader's mark-merge window (#665).
    # The three marks are this tool's own -- one per arm, one `hold` apart --
    # so it knows which captures its own reader cannot read, and the failure
    # is total and late: one coalesced window, no block, and the operator
    # finds out at the grading. That is what makes it a refusal above the EC
    # rather than a note in the help, and what the cases below pin.
    def refused(self, argv):
        """(exit code, ECs opened, capture path) for a run that should refuse.

        `--csv` is appended rather than passed in, because the guard is
        conditional on it and a case that supplied it would be exercising a
        different run. The `opened` recorder is the whitelist case's trick: a
        refusal that still opened the EC is a refusal that ran the hardware
        first, and the path is a tempdir one so a guard that stopped firing
        leaves a file in nobody's working tree.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        opened = []
        path = Path(tmp.name) / "capture.csv"
        with patch.object(probe, 'Ec', lambda: opened.append(1)):
            with self.assertRaises(SystemExit) as cm:
                probe.main(list(argv) + ['--csv', str(path)])
        return cm.exception.code, opened, path

    def test_a_short_hold_is_refused_before_opening_the_ec(self):
        code, opened, path = self.refused(['0xA0', '3'])
        # The refusal and not any SystemExit: argparse exits 2 on a mistyped
        # flag, so a bare assertRaises would pass for a run that never looked
        # at the hold. `sys.exit(msg)` carries the message as the code.
        self.assertIsInstance(code, str)
        self.assertIn("hold 3s is at or under", code)
        self.assertIn(f"MARK_MERGE_SECONDS ({probe.MARK_MERGE_SECONDS:g}s)",
                      code)
        # Both ways out are named, because they are different decisions: one
        # is a longer run, the other is dropping the flag the operator asked
        # for.
        self.assertIn("drop --csv", code)
        self.assertEqual(opened, [])
        # And nothing was written either. The refusal is above the EC *and*
        # above the capture, so a refused run leaves no header-only file for
        # the next `--csv` run to append its rows to.
        self.assertFalse(path.exists())

    def test_a_hold_exactly_at_the_window_is_refused_too(self):
        # `coalesce_marks` closes a group at `<= MARK_MERGE_SECONDS`, so the
        # window itself folds the marks and the guard has to be `<=` and not
        # `<`. A `<` would let a hold of exactly the window straight through to
        # the one-window capture the block walk cannot read.
        code, opened, _ = self.refused(
            ['0xA0', f'{probe.MARK_MERGE_SECONDS:g}'])
        self.assertIsInstance(code, str)
        self.assertIn("at or under", code)
        self.assertEqual(opened, [])

    def test_the_hold_refusal_is_not_a_usage_error(self):
        # The counterpart of the mistyped-flag case in section 5, because the
        # two codes are the whole distinction. argparse's 2 means a typo; this
        # is a value the tool will not honour, the same class as an out-of-set
        # target, and that is why it is `sys.exit(msg)` and not `ap.error`.
        code, _, _ = self.refused(['0xA0', '3'])
        self.assertNotEqual(code, 2)
        self.assertIsInstance(code, str)

    def test_a_hold_just_above_the_window_still_grades_clean(self):
        # The other side of the `<=`, on the run rather than on the guard. Half
        # a second over the window the three marks are clear of each other,
        # the capture is three windows, and the real grader comes back one
        # intact block -- a guard that refused this would be refusing a
        # capture its own reader reads.
        hold = probe.MARK_MERGE_SECONDS + 0.5
        path, _ = self.capture_path(('0xA0', f'{hold:g}'))
        rc, out, err = run_grader(str(path))
        self.assertEqual(rc, 0, err)
        self.assertIn("block 1/1: intact", out)
        self.assertIn("value under test 0xA0; roles control, write, restore",
                      out)
        self.assertNotIn("NOT GRADED", out)
        self.assertEqual(len(grader.build_windows(
            *grader.read_capture(str(path)))), 3)

    def test_a_short_hold_without_a_capture_is_not_refused(self):
        # The narrowing, and the reason the guard is conditional on --csv:
        # without it there is no MARK row to coalesce and no capture to
        # misread, so a floor here would refuse a run that cannot fail, which
        # is the overclaim docs/findings.md §4 is written against. The hold
        # stays the operator's.
        ec, out = self.run_probe(argv=('0xA0', '3'))
        self.assertIn("holding 3s each", out)
        self.assertEqual(ec.writes,
                         [(0x0751, ORIG), (0x0751, TARGET), (0x0751, ORIG)])

    def test_the_restated_window_is_the_graders(self):
        # Restated rather than imported because main() runs next to ecrw.py on
        # the Windows box and must not depend on the repository layout to know
        # a number. This is what makes the restatement safe: a window that
        # moves in the grader fails here, by name, instead of quietly
        # widening the floor the tool refuses on. The direction of the pin
        # matters -- the probe's copy is what follows the grader, not the
        # other way round.
        self.assertEqual(probe.MARK_MERGE_SECONDS, grader.MARK_MERGE_SECONDS)

    def test_the_self_test_checks_the_hold_floor(self):
        # The row a human with no driver can run: the floor is the grader's
        # window, a hold at it is refused, the next value up is not, and this
        # tool's own 30 s hold clears it.
        code, out = self.run_self_test()
        self.assertEqual(code, 0)
        self.assertIn("would fold the three marks and is refused", out)

    # 11. --self-test: the checkable half, on the tool's own logic. No EC.
    def run_self_test(self):
        out = io.StringIO()
        with patch.object(probe, 'Ec', lambda: self.fail("opened an EC")), \
             contextlib.redirect_stdout(out):
            code = probe.main(['0xA0', '--self-test'])
        return code, out.getvalue()

    def test_the_self_test_passes_without_opening_an_ec(self):
        code, out = self.run_self_test()
        self.assertEqual(code, 0)
        self.assertIn("self-test passed", out)
        self.assertIn("no EC, no driver", out)

    def test_the_self_test_says_it_is_not_hardware_evidence(self):
        _, out = self.run_self_test()
        self.assertIn("No EC was opened, no register was read", out)
        self.assertIn("nothing here\nsays anything about the machine", out)

    def test_the_self_test_reads_the_grader_out_of_the_repository(self):
        # Not a format assertion on this file's own idea of the shape: the
        # check is only worth anything if the reader is the real one, and the
        # real one is at a path relative to the probe rather than to the cwd
        # it happens to be run from.
        self.assertTrue(GRADER_PATH.is_file())
        self.assertEqual(GRADER_PATH.name, "grade_0751_isolation.py")
        self.assertEqual(grader.read_capture.__module__,
                         "grade_0751_isolation")

    def test_the_self_test_runs_before_the_whitelist_refuses(self):
        # The target is a dry run's way of satisfying a required positional, and
        # it is not read. Dispatching after the whitelist check would send a
        # reader who typed --self-test first at a refusal about a value the
        # self-test never used.
        code, out = self.run_self_test()
        self.assertEqual(code, 0)
        self.assertNotIn("not in the vendor set", out)

    # 12. --block (#147). Opt-in, and the default run is the one the committed
    #     #99/#122 captures were taken with, so "the flag is off" is the first
    #     thing to hold.
    def test_the_block_path_is_opt_in(self):
        ec, _ = self.run_probe()
        self.assertEqual(ec.blocks, [])

    def test_block_sweeps_through_readmany(self):
        ec, _ = self.run_probe(argv=('0xA0', '--block'))
        # The seven runs the default set decomposes into, 0x0400's temperature
        # range first. Written out rather than recomputed with the function
        # under test, so a drift in the decomposition fails here.
        self.assertEqual(ec.blocks[:7], [
            (0x0400, 0x60), (0x0743, 4), (0x0751, 1), (0x075B, 2),
            (0x0783, 5), (0x07C5, 2), (0x0F00, 0x60)])
        # Every sweep is those seven again, so the count has to divide by them
        # -- and one of those sweeps is 56 blocks, which is the figure the
        # banner quotes.
        self.assertGreater(len(ec.blocks), 7)
        self.assertEqual(len(ec.blocks) % 7, 0)
        self.assertEqual(probe.block_ioctls(probe.watch_set()), 56)

    def test_block_reports_the_same_movement_as_the_byte_path(self):
        # The two paths have to produce the same report or a capture reads
        # differently depending on a flag, which is the one thing a default-off
        # optimisation is not allowed to do. Compared whole, from the control
        # arm's label on: everything before that is the banner, and the banner
        # is where the two runs are *meant* to differ.
        def report(out):
            return out[out.index("no-op wrote"):]

        _, plain = self.run_probe()
        _, blocked = self.run_probe(argv=('0xA0', '--block'))
        self.assertEqual(report(blocked), report(plain))
        self.assertIn("0x075B: 0x10 -> 0x30 (2 changes)", report(blocked))

    def test_block_still_restores_and_still_brackets_the_write(self):
        ec, out = self.run_probe(argv=('0xA0', '--block'))
        self.assertEqual(ec.writes,
                         [(0x0751, ORIG), (0x0751, TARGET), (0x0751, ORIG)])
        self.assertIn("no-op wrote 0x0751=0x10", out)
        self.assertIn("wrote 0x0751=0xA0", out)

    def test_block_leaves_the_mode_byte_to_the_point_read(self):
        # `read` is not gone with --block: the original and the restore
        # readback are point reads of one byte, and they are the only reads
        # left outside the sweeps. A flag that swept the mode byte through a
        # block would change what the EC sees around the write for no gain.
        ec, _ = self.run_probe(argv=('0xA0', '--block'))
        self.assertEqual(ec.point_reads, [probe.MODE, probe.MODE])

    def test_without_block_every_swept_byte_is_a_point_read(self):
        ec, _ = self.run_probe()
        self.assertEqual(set(ec.point_reads), set(probe.ALL) | {probe.MODE})

    def test_the_block_banner_names_both_figures_and_the_unverified_path(self):
        _, out = self.run_probe(argv=('0xA0', '--block'))
        # 56 against 206, and the honest part: the path has never met the
        # driver, and the flag is not the thing that makes a run safe (#94 is).
        self.assertIn("56 MMRD IOCTLs per sweep instead of 206 ECRR reads",
                      out)
        self.assertIn("never been run against the driver", out)

    def test_no_block_banner_without_the_flag(self):
        _, out = self.run_probe()
        self.assertNotIn("MMRD IOCTLs per sweep", out)

    def test_block_widens_with_the_level_block_to_61(self):
        ec, out = self.run_probe(argv=('0xA0', '--level-block', '--block'))
        self.assertIn("61 MMRD IOCTLs per sweep instead of 222 ECRR reads", out)
        self.assertIn((0x0860, 15), ec.blocks)
        self.assertIn((0x06E6, 1), ec.blocks)

    def test_the_self_test_checks_the_block_arithmetic(self):
        # 56 and 61 are figures the docstring quotes, so the self-test a human
        # can run without a driver is where they are pinned; the run passing
        # means both held.
        code, out = self.run_self_test()
        self.assertEqual(code, 0)
        self.assertIn("not the 52 a contiguous 206 would give", out)

    def test_the_self_test_checks_no_block_reaches_the_fan_tach_page(self):
        code, out = self.run_self_test()
        self.assertEqual(code, 0)
        self.assertIn("no block of any of the four sets covers a fan-tach "
                      "byte", out)

    # 13. --watch-page (issue #666). Opt-in, substitutes for WATCH rather than
    #     adding to it, and read-only like every other set this tool sweeps.
    def test_the_whole_page_arm_is_opt_in(self):
        # The default set is the footprint the committed 2026-09-23 run was
        # taken at, so "the flag is off" is the first thing to hold -- and the
        # two ends of the page are the addresses only a run that asked for
        # them can have read.
        self.assertEqual(len(probe.watch_set()), 206)
        self.assertNotIn(0x0700, probe.watch_set())
        self.assertNotIn(0x07FF, probe.watch_set())
        paged = probe.watch_set(watch_page=True)
        self.assertEqual(len(paged), 448)
        self.assertIn(0x0700, paged)
        self.assertIn(0x07FF, paged)

    def test_the_page_arm_is_section_3s_three_watchers(self):
        # §3's three commands in one process: `0x100 + 0x60 + 0x60 = 448`.
        # Written as the three ranges rather than as the count, so a set that
        # hit 448 with the wrong addresses would fail here.
        self.assertEqual(set(probe.watch_set(watch_page=True)),
                         set(range(0x0400, 0x0460))
                         | set(range(0x0700, 0x0800))
                         | set(range(0x0F00, 0x0F60)))
        # Substituting rather than adding: all 14 WATCH addresses are already
        # inside the page, so a set that took both would dedup to the page and
        # any code counting the concatenation rather than the set would report
        # a 270 that no configuration sweeps.
        self.assertLessEqual(set(probe.WATCH), set(probe.PAGE))
        self.assertEqual(len(probe.PAGE) + len(probe.FANTBL) + len(probe.TEMP),
                         448)

    def test_the_page_arm_still_writes_only_the_mode_byte(self):
        # On the fake's own write list, not on a docstring sentence: this is
        # the claim that makes a 448-address sweep the same kind of read as a
        # 206-address one, and a bigger sweep is exactly where it deserves a
        # check rather than a sentence.
        ec, _ = self.run_probe(argv=('0xA0', '--watch-page'))
        self.assertEqual(ec.writes,
                         [(0x0751, ORIG), (0x0751, TARGET), (0x0751, ORIG)])
        # And the mode byte is still left to a point read under --block,
        # where the 448 are swept through MMRD instead.
        blocked, _ = self.run_probe(argv=('0xA0', '--watch-page', '--block'))
        self.assertEqual(blocked.point_reads, [probe.MODE, probe.MODE])
        self.assertEqual(blocked.writes, ec.writes)

    def test_the_page_arm_reports_what_the_default_reports(self):
        # Same scripted values, same sweeps, same arms. The four addresses
        # SCRIPT moves are all inside the page or inside TEMP, so a run that
        # appended the page instead of substituting it, or that let the sweep
        # boundary move to 0x07FF, would land them on different sweeps and
        # this would catch it as wrong values -- which is how the ordering
        # invariant in watch_set fails if it is ever broken.
        def report(out):
            return out[out.index("no-op wrote"):]

        _, plain = self.run_probe()
        _, paged = self.run_probe(argv=('0xA0', '--watch-page'))
        self.assertEqual(report(paged), report(plain))
        self.assertIn("0x075B: 0x10 -> 0x30 (2 changes)", report(paged))
        self.assertIn("0x075C: 0x00 -> 0x70 (2 changes)", report(paged))

    def test_every_set_closes_its_sweep_on_the_address_the_fake_expects(self):
        # `addrs[-1]` is the address the fake closes a byte-path sweep on, so
        # it is the tool's half of the same fact: the page arm ends on 0x045F
        # like the default rather than on 0x07FF, and --level-block's own tail
        # is the gate byte it appends last.
        for level_block, watch_page, tail in ((False, False, 0x045F),
                                              (True, False, 0x06E6),
                                              (False, True, 0x045F),
                                              (True, True, 0x06E6)):
            self.assertEqual(
                probe.watch_set(level_block=level_block,
                                watch_page=watch_page)[-1], tail)

    def test_the_banner_states_the_whole_page_and_the_read_only_path(self):
        _, out = self.run_probe(argv=('0xA0', '--watch-page'))
        self.assertIn("0x0700-0x07FF in place of WATCH's 14", out)
        self.assertIn("448 ECRR reads per sweep", out)
        self.assertIn("Nothing in the page is written", out)
        # The #94 caveat is on this banner too, and 2.2x the reads is what
        # makes it more load-bearing rather than less.
        self.assertIn("no interval here is validated", out)
        self.assertIn("fans audibly change, stop", out)

    def test_no_page_banner_without_the_flag(self):
        # A default run whose output read "answers §4.4" would be the
        # confident-sounding overclaim the flag exists to avoid, so the line
        # is on the page arm's banner and nowhere else.
        _, out = self.run_probe()
        self.assertNotIn("0x0700-0x07FF", out)
        self.assertNotIn("whole page", out)

    def test_the_page_arm_block_sweep_is_three_whole_runs(self):
        ec, out = self.run_probe(argv=('0xA0', '--watch-page', '--block'))
        # The three §3 ranges, each read as one run and each already
        # 4-aligned, so the sweep is the 112 that `448/4` suggests -- unlike
        # the default set's 56 against the 52 the same arithmetic gives there.
        self.assertEqual(ec.blocks[:3],
                         [(0x0400, 0x60), (0x0700, 0x100), (0x0F00, 0x60)])
        self.assertEqual(len(ec.blocks) % 3, 0)
        self.assertEqual(probe.block_ioctls(probe.watch_set(watch_page=True)),
                         112)
        self.assertEqual(probe.block_ioctls(
            probe.watch_set(level_block=True, watch_page=True)), 117)
        self.assertIn("112 MMRD IOCTLs per sweep instead of 448 ECRR reads",
                      out)

    def test_a_page_arm_capture_passes_the_real_grader_end_to_end(self):
        # The same done-condition as the default run's case, on the wider set:
        # one block, intact, three roles, every window printed, exit 0. A
        # 448-address capture that the grader could not read would make the
        # flag worse than the gap it closes.
        path, _ = self.capture_path(('0xA0', '--watch-page'))
        rc, out, err = run_grader(str(path))
        self.assertEqual(rc, 0, err)
        self.assertIn("block 1/1: intact", out)
        self.assertIn("value under test 0xA0; roles control, write, restore",
                      out)
        for n in (1, 2, 3):
            self.assertIn(f"--- mark {n}/3:", out)
        self.assertNotIn("NOT GRADED", out)

    def test_a_page_arm_capture_keeps_its_ungraded_rows_visible(self):
        # Every change row outside the grader's WATCHED and CONTEXT groups
        # lands on one `other addresses that moved (N), not graded here` line
        # rather than being dropped, and a page arm is where that line gets
        # long -- up to 240 addresses on a real run, against the one here.
        # 0x0790 is inside the page and in neither group, and is given a move
        # for this case alone; the cleanup puts SCRIPT back before the next
        # case reads it. The count is 2 rather than 1 because 0x0751 lands in
        # the same bucket -- it is the byte the run itself wrote, and the
        # grader grades none of it, which is the same already-calibrated
        # landing a page-arm row takes.
        SCRIPT[0x0790] = ([0x00], [0x00, 0x5A])
        self.addCleanup(SCRIPT.pop, 0x0790)
        path, _ = self.capture_path(('0xA0', '--watch-page'))
        rc, out, err = run_grader(str(path))
        self.assertEqual(rc, 0, err)
        self.assertIn("other addresses that moved (2), not graded here", out)
        self.assertIn("0x0751 0x0790", out)

    def test_the_self_test_checks_the_page_arms_figures(self):
        # 448, 112 and 464 are figures the docstring quotes, so the self-test
        # a human can run without a driver is where they are pinned; the run
        # passing means all three held.
        code, out = self.run_self_test()
        self.assertEqual(code, 0)
        self.assertIn("448 addresses, and 0x0700-0x07FF", out)
        self.assertIn("112 IOCTLs for the page arm's 448", out)


if __name__ == '__main__':
    unittest.main()
