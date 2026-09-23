#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

manual_fan_ctrl_probe.py imports ecrw, which binds kernel32 at import time and
so only loads on Windows -- the fake below stands in for the whole module,
which is also what lets the two arms be scripted byte by byte.

The script is keyed on the arm and the sweep within it, not on a timestamp, so
what a byte does is an assertion about the run's shape -- the no-op moves PWM,
the write moves the other one, both move the temperature -- and not about how
many sweeps a given hold happens to buy.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ORIG = 0x10
TARGET = 0xA0

# addr -> (values by sweep in the control arm, values by sweep in the write
# arm), the last entry repeating. 0x075B drifts under the no-op and 0x075C
# under the write, and neither moves in the other arm, which is what makes
# "the two arms' PWM motion stayed apart" checkable rather than asserted.
# Both temperature bytes move in both arms, which is the "did 0x043E hold
# steady across both" reading §4.5 needs.
SCRIPT = {
    0x075B: ([0x10, 0x28, 0x30], [0x30, 0x30, 0x30]),
    0x075C: ([0x00, 0x00, 0x00], [0x00, 0x50, 0x70]),
    0x043E: ([0x40, 0x42, 0x43], [0x43, 0x45, 0x46]),
    0x044F: ([0x50, 0x52, 0x53], [0x53, 0x55, 0x56]),
}

fake_ecrw = types.ModuleType('ecrw')
fake_ecrw.Ec = lambda: None
sys.modules.setdefault('ecrw', fake_ecrw)

spec = importlib.util.spec_from_file_location(
    'manual_fan_ctrl_probe', Path(__file__).with_name('manual_fan_ctrl_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class FakeEc:
    """A watch set where a sweep ends at its last address.

    snap() reads every address of the set in order, so the last one closes the
    sweep. Keying off that rather than off a raw read count keeps the two bare
    0x0751 reads -- the original and the final readback -- from shifting every
    value the arms see. A write starts a new arm, which is what makes the
    script's two lists mean what they say.
    """

    def __init__(self, orig=ORIG, boom_at=None):
        self.mode = orig
        self.writes = []        # (addr, value) in order, restore last
        self.writes_at = []     # bytes already read when each write landed
        self.reads = 0
        self.boom_at = boom_at
        self._sweep = 0         # within the current arm
        self._last = probe.ALL[-1]

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
    """A counter for time.time, so a hold buys a fixed number of sweeps."""

    def __init__(self, step=0.1):
        self.t = 0.0
        self.step = step

    def time(self):
        self.t += self.step
        return self.t

    def sleep(self, _s):
        pass


class ProbeTests(unittest.TestCase):
    def run_probe(self, argv=('0xA0', '30'), ec=None, **kw):
        ec = ec if ec is not None else FakeEc(**kw)
        clock = Clock()
        out = io.StringIO()
        with patch.object(probe, 'Ec', lambda: ec), \
             patch.object(probe.time, 'time', clock.time), \
             patch.object(probe.time, 'sleep', clock.sleep), \
             contextlib.redirect_stdout(out):
            probe.main(list(argv))
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
        with patch.object(probe, 'Ec', lambda: opened.append(1)), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                probe.main(['0xE0'])
        self.assertEqual(opened, [])

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

    # The tool states a measurement, not a verdict.
    def test_summary_grades_nothing(self):
        _, out = self.run_probe()
        self.assertNotIn("confirmed-working", out)
        self.assertNotIn("confirmed-inert", out)

    # A drifting byte reports the arm's net, first to last, with the count --
    # the arithmetic the grader prints as a `window delta`. Reporting the last
    # step instead would understate a slow drift by the movement between the
    # first and second change, which is the part §4.4 compares.
    def test_a_drifting_byte_reports_its_net_not_its_last_step(self):
        _, out = self.run_probe()
        control = out[out.index("control arm --"):out.index("write under test --")]
        self.assertIn("0x075B: 0x10 -> 0x30 (2 changes)", control)
        self.assertIn("0x043E: 0x40 -> 0x43 (2 changes)", control)


if __name__ == '__main__':
    unittest.main()
