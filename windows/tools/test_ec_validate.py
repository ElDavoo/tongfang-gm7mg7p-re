#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

ec_validate.py imports ecrw, which binds kernel32 at import time and so only
loads on Windows -- the fake below stands in for the whole module, exactly as
test_ec_watch.py does. WMI is the other thing that cannot run here, so
wmi_battery is driven from the frames below instead: each frame is one
sample's worth of both sides at once.

What these check is the 0x0436 capacity arm's own rules -- the one-directional
exact-copy scoring, the full-capacity bound, the CSV, and the page assertion --
plus the invariant that the arm reports rather than concludes. None of it says
what 0x0436 *is*; that is a human's, per
docs/hardware-tests/remain-capacity-0436.md.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

FIELDS = ("voltage_mv", "remaining_mwh", "charge_mw", "discharge_mw",
          "ac_online")


class FakeEc:
    """A flat EC RAM the test writes into; `read` is a dict lookup."""

    def __init__(self, mem=None):
        self.mem = dict(mem or {})

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        return self.mem.get(addr, 0xFF)


fake_ecrw = types.ModuleType('ecrw')
fake_ecrw.Ec = FakeEc
sys.modules.setdefault('ecrw', fake_ecrw)

spec = importlib.util.spec_from_file_location(
    'ec_validate', Path(__file__).with_name('ec_validate.py'))
ec_validate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec_validate)


def frame(ec, **wmi):
    """One sample, seen from both sides: the EC's bytes and what WMI reports."""
    w = dict.fromkeys(FIELDS, 0)
    w.update(wmi)
    return {"ec": ec, "wmi": w}


def be16(value):
    return value & 0xFF, value >> 8


def voltage_frame(v, wmi_v, cpu=0x40, gpu=0x40, cycles=449):
    """One sample of the §4g arm: a 16-bit mV pair, and the value WMI held."""
    lo, hi = be16(v)
    return frame({ec_validate.ADDR_VOLTAGE: lo,
                  ec_validate.ADDR_VOLTAGE + 1: hi,
                  ec_validate.ADDR_CPU_TEMP: cpu,
                  ec_validate.ADDR_GPU_TEMP: gpu,
                  **{a: b for a, b in zip((ec_validate.ADDR_CYCLES,
                                           ec_validate.ADDR_CYCLES + 1),
                                          be16(cycles))}},
                 voltage_mv=wmi_v)


def capacity_frame(v, wmi_mwh, full=0x2A00, design=0x2800, current=0x0BB8,
                   voltage=0x3EB0, ac=0, discharge_mw=0, charge_mw=0):
    """One sample of the 0x0436 arm, with the context a verdict would need."""
    pairs = dict(zip((0x0436, 0x0437, 0x0402, 0x0403, 0x0404, 0x0405,
                      0x0434, 0x0435, 0x0438, 0x0439),
                     be16(v) + be16(design) + be16(full) + be16(current)
                     + be16(voltage)))
    return frame(pairs, remaining_mwh=wmi_mwh, ac_online=ac,
                 charge_mw=charge_mw, discharge_mw=discharge_mw)


def run_arm(frames, samples=None, sink=None, interval=0):
    """Run one arm over `frames` and return (rows, matched, over_bound).

    ec_validate asks WMI at the top of every sample, before it reads the EC, so
    driving the fake EC's memory from the wmi_battery stand-in is what puts a
    boundary between two frames -- the fake does not have to know how many reads
    a sample is, which is the coupling that would make this suite brittle.
    """
    ec = FakeEc()
    pending = list(frames)

    def wmi_battery():
        f = pending.pop(0)
        ec.mem.update(f["ec"])
        return dict(f["wmi"])

    out = io.StringIO()
    with patch.object(ec_validate, "wmi_battery", wmi_battery), \
         patch.object(ec_validate, "Ec", lambda: ec), \
         patch.object(ec_validate.time, "sleep"), \
         contextlib.redirect_stdout(out):
        rows, matched, over = ec_validate.capacity_arm(
            ec, len(frames) if samples is None else samples, interval, sink)
    return rows, matched, over, out.getvalue()


class ExactCopyTests(unittest.TestCase):
    def test_a_wmi_value_the_ec_only_showed_later_is_not_credited(self):
        # WMI serves a cached value, so it can lag the EC. The guard is one
        #-directional on purpose: 200 at sample 0 is a value the EC had NOT
        # held yet, and crediting it would be matching on noise.
        rows, matched, _, _ = run_arm([
            capacity_frame(100, 200),
            capacity_frame(200, 100),
            capacity_frame(300, 300),
        ])
        self.assertEqual([r["exact_copy"] for r in rows], [False, True, True])
        self.assertEqual(matched, 2)

    def test_an_exact_copy_is_credited_on_the_sample_that_shows_it(self):
        rows, matched, _, _ = run_arm([
            capacity_frame(100, 100),
            capacity_frame(200, 100),
        ])
        self.assertEqual([r["exact_copy"] for r in rows], [True, True])
        self.assertEqual(matched, 2)

    def test_a_counter_fails_the_same_test_a_capacity_would(self):
        # The reason the arm does not grade: +0x14 every sample, and WMI never
        # repeating one, is what a counter looks like here. Recorded as 0/N.
        rows, matched, _, text = run_arm([
            capacity_frame(0x70 + 0x14 * i, 0x2A00 - 3 * i)
            for i in range(4)
        ])
        self.assertEqual(matched, 0)
        self.assertIn("exact-copy matches: 0/4", text)

    def test_the_score_is_reported_as_an_observation(self):
        _, _, _, text = run_arm([capacity_frame(1, 9)])
        self.assertIn("A counter fails the exact-copy test the same way", text)


class BoundTests(unittest.TestCase):
    def test_a_pair_above_the_full_capacity_reading_is_flagged(self):
        rows, _, over, _ = run_arm([
            capacity_frame(0x2000, 0x2000, full=0x2A00),
            capacity_frame(0x2B00, 0x2B00, full=0x2A00),
            capacity_frame(0x2A00, 0x2A00, full=0x2A00),
        ])
        self.assertEqual([r["within_bound"] for r in rows],
                         [True, False, True])
        # The first breach, not the last -- which one it is matters when a human
        # is looking for where in the capture the pair left the page.
        self.assertEqual(over["ec_0436"], 0x2B00)

    def test_equal_to_the_bound_is_within_it(self):
        rows, _, over, _ = run_arm([capacity_frame(0x2A00, 0x2A00, full=0x2A00)])
        self.assertTrue(rows[0]["within_bound"])
        self.assertIsNone(over)

    def test_the_bound_prints_as_a_yes_or_a_no(self):
        _, _, _, inside = run_arm([capacity_frame(0x100, 0x100, full=0x2A00)])
        _, _, _, outside = run_arm([capacity_frame(0x3000, 0x3000,
                                                   full=0x2A00)])
        self.assertIn("on every sample: yes", inside)
        self.assertIn("on every sample: no", outside)


class PageBoundTests(unittest.TestCase):
    def test_the_capacity_arm_addresses_are_all_on_the_page(self):
        self.assertEqual(ec_validate.check_page(ec_validate.CAP_ADDRS),
                         list(ec_validate.CAP_ADDRS))

    def test_a_fan_tach_address_is_refused(self):
        # 0x0460-0x046F stalled the fans on a sibling board (issue #94).
        with self.assertRaises(ValueError) as cm:
            ec_validate.check_page([0x0464])
        self.assertIn("0x0464", str(cm.exception))
        self.assertIn("fan-tach", str(cm.exception))

    def test_the_last_byte_of_the_page_is_refused_too(self):
        # 0x045F is on the page; the byte after it is not, and a 16-bit read of
        # 0x045F reaches 0x0460. The bound is on the pair for that reason.
        ec_validate.check_page([ec_validate.PAGE_LAST - 1])
        with self.assertRaises(ValueError):
            ec_validate.check_page([ec_validate.PAGE_LAST])

    def test_main_refuses_before_opening_the_ec(self):
        with patch.object(ec_validate, "check_page",
                          side_effect=ValueError("0x0460 is out")) as check, \
             patch.object(ec_validate, "Ec", side_effect=AssertionError(
                 "the EC was opened despite the page bound")) as opener, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ec_validate.main(["--samples", "1"]), 2)
        check.assert_called_once()
        opener.assert_not_called()


class CsvTests(unittest.TestCase):
    def capture(self, frames, tmp):
        out = Path(tmp) / "capture.csv"
        sink = ec_validate.SampleCsv(str(out))
        try:
            run_arm(frames, sink=sink)
        finally:
            sink.close()
        return out.read_text().splitlines()

    def test_header_then_one_row_per_sample(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = self.capture([capacity_frame(100 + i, 100) for i in range(3)],
                                tmp)
        self.assertEqual(rows[0], ",".join(ec_validate.CAP_COLUMNS))
        self.assertEqual(len(rows), 4)
        self.assertEqual([r.split(",")[1] for r in rows[1:]], ["100", "101",
                                                                "102"])

    def test_a_second_run_appends_without_repeating_the_header(self):
        # The ec_watch.py --csv convention: a run stopped and resumed extends
        # the capture, so a finished run can be committed as the file it was
        # written to.
        with tempfile.TemporaryDirectory() as tmp:
            self.capture([capacity_frame(100 + i, 100) for i in range(2)], tmp)
            rows = self.capture([capacity_frame(200 + i, 200) for i in range(2)],
                                tmp)
        self.assertEqual(rows[0], ",".join(ec_validate.CAP_COLUMNS))
        self.assertEqual(sum(1 for r in rows if r.startswith("ts,")), 1)
        self.assertEqual(len(rows), 5)

    def test_a_row_carries_the_context_a_verdict_would_need(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = self.capture([capacity_frame(0x1234, 4321, full=0x2A00,
                                                design=0x2800, current=0x0BB8,
                                                voltage=0x3EB0, ac=1,
                                                discharge_mw=31000)], tmp)
        record = dict(zip(rows[0].split(","), rows[1].split(",")))
        self.assertEqual(record["ec_0436"], str(0x1234))
        self.assertEqual(record["wmi_remaining_mwh"], "4321")
        self.assertEqual(record["ec_0404_full"], str(0x2A00))
        self.assertEqual(record["ec_0402_design"], str(0x2800))
        self.assertEqual(record["ec_0434_ma"], str(0x0BB8))
        self.assertEqual(record["ac"], "1")
        self.assertEqual(record["discharge_mw"], "31000")


class MainTests(unittest.TestCase):
    def frames_for(self, n_v, n_c, v_off=0, c_off=0):
        """n_v voltage-arm samples then n_c capacity-arm samples."""
        return ([voltage_frame(0x3500 + v_off + i, 0x3500 + v_off + i)
                 for i in range(n_v)]
                + [capacity_frame(0x70 + c_off + 0x14 * i, 1 + c_off + i)
                   for i in range(n_c)])

    def run_main(self, frames, *extra):
        ec = FakeEc()
        pending = list(frames)

        def wmi_battery():
            f = pending.pop(0)
            ec.mem.update(f["ec"])
            return dict(f["wmi"])

        sink = Path(tempfile.mkdtemp()) / "capture.csv"
        with patch.object(ec_validate, "wmi_battery", wmi_battery), \
             patch.object(ec_validate, "Ec", lambda: ec), \
             patch.object(ec_validate.time, "sleep"), \
             contextlib.redirect_stdout(io.StringIO()):
            rc = ec_validate.main(["--samples", "3", "--interval", "0",
                                   "--csv", str(sink), *extra])
        return rc, sink.read_text().splitlines()

    def test_the_voltage_arm_still_scores_its_own_ten_of_ten(self):
        # The committed §4g result has to survive the flags landing next to it.
        rc, rows = self.run_main(self.frames_for(ec_validate.SAMPLES, 3))
        self.assertEqual(rc, 0)
        self.assertEqual(rows[0].split(","),
                         list(ec_validate.CAP_COLUMNS))
        self.assertEqual(len(rows), 4)

    def test_a_capacity_arm_that_matches_nothing_does_not_fail_the_run(self):
        # The invariant this PR exists to keep: the arm reports, and the exit
        # code stays the voltage arm's 10/10 finding.
        frames = [voltage_frame(0x3500 + i, 0x3500 + i)
                  for i in range(ec_validate.SAMPLES)]
        frames += [capacity_frame(0x70 + 0x14 * i, 0xFFFF)
                   for i in range(3)]
        rc, _ = self.run_main(frames)
        self.assertEqual(rc, 0)

    def test_the_bare_invocation_still_reproduces_4g(self):
        # main() builds its own parser, so the defaults are read off the module
        # constants the flagless invocation used before the flags existed:
        # 10 samples at 2.0 s is what the committed 10/10 was taken at.
        self.assertEqual((ec_validate.SAMPLES, ec_validate.INTERVAL), (10, 2.0))
        self.assertEqual((ec_validate.CAP_SAMPLES, ec_validate.CAP_INTERVAL),
                         (10, 1.0))


if __name__ == "__main__":
    unittest.main()
