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


class FakeEc:
    """A watch set where a sweep ends at its last address.

    snap() reads every address of the set in order, so the last one closes the
    sweep. Keying off that rather than off a raw read count keeps the two bare
    0x0751 reads -- the original and the final readback -- from shifting every
    value the arms see. A write starts a new arm, which is what makes the
    script's two lists mean what they say.

    `addrs` is the set the run was asked for, because --level-block makes the
    watch set a runtime choice and this closes its sweeps on whichever address
    that choice ends at.
    """

    def __init__(self, orig=ORIG, boom_at=None, addrs=None):
        self.mode = orig
        self.writes = []        # (addr, value) in order, restore last
        self.writes_at = []     # bytes already read when each write landed
        self.reads = 0
        self.boom_at = boom_at
        self._sweep = 0         # within the current arm
        self._last = (addrs if addrs is not None else probe.ALL)[-1]

    def read(self, addr):
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

    def __init__(self, step=0.1, base=1700000000.0):
        self.t = 0.0
        self.base = base
        self.step = step
        self.slept = []

    def time(self):
        self.t += self.step
        return self.t

    def now(self):
        return (datetime.datetime.fromtimestamp(self.base + self.t)
                .astimezone().isoformat(timespec="milliseconds"))

    def sleep(self, s):
        self.slept.append(s)


class ProbeTests(unittest.TestCase):
    def run_probe(self, argv=('0xA0', '30'), ec=None, clock=None, **kw):
        argv = list(argv)
        ec = ec if ec is not None else FakeEc(
            addrs=probe.watch_set('--level-block' in argv), **kw)
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
        # Named one at a time rather than as a range, because 0x046A is the
        # destination of the 0x9CA6 sync the level-block doc is not allowed to
        # read (docs/hardware-tests/level-block-0860-086e.md §6): a byte that
        # is both a level-block answer and on the forbidden page is the one
        # this has to keep out, and asserting the range's endpoints would miss
        # it.
        for a in (0x0460, 0x046A, 0x046F):
            self.assertNotIn(a, probe.ALL)
            self.assertNotIn(a, probe.watch_set(level_block=True))

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
    #     on the two arm boundaries. This is #124's attachment point, and the
    #     reason to check it is the grader, not the writer: a mark in the wrong
    #     place windows every change under the wrong arm and still exits zero.
    def capture(self, argv):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            self.run_probe(argv=list(argv) + ['--csv', str(path)])
            return path.read_text()

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
        self.assertEqual([m.label for m in marks],
                         ["no-op wrote 0x0751=0x10", "wrote 0x0751=0xA0"])
        self.assertTrue(changes)
        self.assertTrue(all(0 <= c.addr <= 0xFFFF for c in changes))

    def test_each_arm_s_change_rows_land_in_its_own_window(self):
        text = self.capture(('0xA0', '--level-block'))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            path.write_text(text)
            windows = grader.build_windows(*grader.read_capture(str(path)))
        self.assertEqual(len(windows), 2)
        control, written = windows
        # 0x075B drifts under the no-op and 0x075C under the write, and the
        # two arms' movement stayed apart: attributing either to the other
        # mark is exactly the defect a mislabelled mark produces.
        self.assertTrue(any(c.addr == 0x075B for c in control.changes))
        self.assertFalse(any(c.addr == 0x075C for c in control.changes))
        self.assertTrue(any(c.addr == 0x075C for c in written.changes))
        # The level block's own row, in the write arm's window.
        self.assertTrue(any(c.addr == 0x0860 and c.new == 0xFF
                            for c in written.changes))

    def test_a_second_run_appends_to_the_same_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            # One clock for both runs, so the second run's rows are stamped
            # after the first's the way a real second run's are.
            clock = Clock()
            self.run_probe(argv=['0xA0', '--csv', str(path)], clock=clock)
            first = path.read_text()
            self.run_probe(argv=['0x00', '--csv', str(path)], clock=clock)
            both = path.read_text()
            marks, changes = grader.read_capture(str(path))
        self.assertTrue(both.startswith(first))
        self.assertEqual(both.count("ts,addr,old,new"), 1)
        self.assertIn("wrote 0x0751=0x00", both)
        # §4 wants three modes in one session, so the third run's two arms
        # have to extend the file rather than replace it. The second run's
        # control arm re-writes 0x10, not 0x00, because the first run's
        # finally restored 0x0751 -- a fresh Clock does not get to pretend
        # otherwise, or the restore would be untested here too.
        self.assertEqual(both.count(",MARK,"), 4)
        self.assertEqual([m.label for m in marks],
                         ["no-op wrote 0x0751=0x10", "wrote 0x0751=0xA0",
                          "no-op wrote 0x0751=0x10", "wrote 0x0751=0x00"])
        self.assertEqual(len(grader.build_windows(marks, changes)), 4)

    def test_no_capture_is_written_without_the_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.csv"
            self.run_probe(argv=['0xA0'])
            self.assertFalse(path.exists())

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


if __name__ == '__main__':
    unittest.main()
