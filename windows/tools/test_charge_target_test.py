#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

charge_target_test.py imports ecrw, which binds kernel32 at import time and so
only loads on Windows, and shells out to powershell for its WMI line. The fakes
below stand in for both, which is what lets the branches no committed artifact
shows run here: the three refusals and the restore in the finally.

The register map keeps what is written to it, because a byte map is what makes
the restore's readback checkable at all. That is a property of this fixture and
nothing more: docs/findings.md §4m measured the real EC taking 0x0522 back in
under 100 us, so nothing here is evidence about whether a host write holds.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ORIGINAL = 16400     # 0x4010, the value 0x0522 reads on this pack (§4m)
TARGET = 16300       # 0x3FAC, the value the three live runs wrote (§4m)
FLOOR = 12000        # charge_target_test.py:146, the 4S units check

# A run that gets all the way through: lower the target, sample once,
# acknowledge the write. --seconds 0 breaks the loop on its first pass, so the
# write history is exactly the target and then the restore.
BASE = ('--target-mv', str(TARGET), '--seconds', '0', '--i-mean-it')

# Both bytes differ between the two values, so a restore that wrote them the
# other way round, or only the low byte, fails on the readback instead of
# passing.
TARGET_WRITES = [(0x0522, 0xAC), (0x0523, 0x3F)]
RESTORE_WRITES = [(0x0522, 0x10), (0x0523, 0x40)]

# charge_target_test.py builds this list inside main(), so it cannot be
# imported and checked against itself. The copy here is the assertion, and it
# fails on a rename in the tool -- which is the point: these are the columns
# the committed battery traces and anything reading them depend on.
COLS = ["ts", "phase", "t_s", "target_written_mv", "target_readback_mv",
        "held", "requested_mv", "ec_current_ma", "ec_voltage_mv",
        "profile_07a6", "gate_0490", "ac", "charging", "capacity",
        "remaining_mwh", "wmi_rate_mw"]

# The bytes 0x0522 and 0x030E are read as little-endian pairs, so the map is
# keyed by byte address. The values are the first row of
# evidence/battery-traces/2026-09-21-0522-follow.csv -- the CV run, AC and
# charging at 82% -- so a fixture value traces to a committed measurement
# instead of being invented here.
REGS = {
    0x0522: 0x10, 0x0523: 0x40,   # 16400 mV, the EC's own target
    0x030E: 0x0E, 0x030F: 0x44,   # 17400 mV, what the pack requests
    0x0434: 0x2E, 0x0435: 0x05,   # 1326 mA
    0x0438: 0x52, 0x0439: 0x40,   # 16466 mV
    0x07A6: 0x08,                 # High capacity
    0x0490: 0x0F,                 # the derating routine's gate byte
}

# The six tokens WMI_QUERY formats, in the order wmi() zips them onto its keys.
WMI_TOKENS = "1 1 0 24928 22394 82"


class FakeEcError(RuntimeError):
    pass


class FakeEc:
    """A byte map, so the tool's own u16/w16 pair is the one under test.

    Every read and write goes through the map rather than a scripted table,
    because 0x0522 is the one register this tool changes: a write has to land
    where a later read can see it, or the restore's readback asserts nothing.
    The context manager is here rather than incidental -- the tool opens the
    device with `with Ec() as ec:` -- and __exit__ returns None so a failure
    partway through still propagates to the finally that restores the target.
    """

    def __init__(self):
        self.regs = dict(REGS)
        self.writes = []   # (addr, value), in the order the tool wrote them
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        self.reads += 1
        return self.regs.get(addr, 0x00)

    def write(self, addr, val):
        self.writes.append((addr, val))
        self.regs[addr] = val


class FakeWmi:
    """Canned WMI lines, optionally raised out of on a chosen call.

    Keyed on the call index rather than on a read count, because the two calls
    are a semantic boundary: the first is the baseline the tool prints before
    any write, the second is inside the loop, after the target has been written
    and inside the try whose finally restores it. That is what makes an injected
    failure genuinely partway rather than merely early.
    """

    def __init__(self, boom_on=None, exc=None):
        self.calls = 0
        self.boom_on = boom_on
        self.exc = exc

    def run(self, argv, **kw):
        index = self.calls
        self.calls += 1
        if index == self.boom_on:
            raise self.exc
        return types.SimpleNamespace(stdout=WMI_TOKENS)


class Clock:
    """A counter for time.time, so --seconds 0 buys exactly one loop pass.

    The tool takes t0 at the first call, the row's t_s at the second and the
    seconds check at the third, so a step of any size breaks after one
    iteration. `slept` records what the run asked to sleep for, which is how
    "one pass and no interval" is asserted rather than counted out.
    """

    def __init__(self, step=0.1):
        self.t = 0.0
        self.step = step
        self.slept = []

    def time(self):
        self.t += self.step
        return self.t

    def sleep(self, s):
        self.slept.append(s)


fake_ecrw = types.ModuleType('ecrw')
fake_ecrw.Ec = lambda: None
# charge_target_test.py:59 imports both names, so this shell has to export
# both: an EcError the fakes raise has to be the class the tool bound at
# import, or `except EcError` never sees it.
fake_ecrw.EcError = FakeEcError
sys.modules.setdefault('ecrw', fake_ecrw)

spec = importlib.util.spec_from_file_location(
    'charge_target_test', Path(__file__).with_name('charge_target_test.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class ChargeTargetTests(unittest.TestCase):
    def run_tool(self, argv, ec=None, clock=None, wmi=None):
        ec = ec if ec is not None else FakeEc()
        clock = clock if clock is not None else Clock()
        wmi = wmi if wmi is not None else FakeWmi()
        out, err = io.StringIO(), io.StringIO()
        # Only subprocess.run is replaced, so the tool's own wmi() runs and the
        # six-token parse and the dict(zip(keys, ...)) the CSV row is built
        # from are covered along with it.
        with patch.object(tool, 'Ec', lambda: ec), \
             patch.object(tool, 'subprocess',
                          types.SimpleNamespace(run=wmi.run)), \
             patch.object(tool.time, 'time', clock.time), \
             patch.object(tool.time, 'sleep', clock.sleep), \
             contextlib.redirect_stdout(out), \
             contextlib.redirect_stderr(err):
            rc = tool.main(list(argv))
        return rc, ec, out.getvalue(), err.getvalue()

    # 1. The three refusals, each asserted on which one fired. A bare rc == 2
    #    passes for a mistyped flag or any other early exit, so the message is
    #    part of the claim (the same lesson as
    #    test_manual_fan_ctrl_probe.py:180-188).
    def test_a_target_at_the_value_just_read_is_refused(self):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, err = self.run_tool(
                ('--target-mv', str(ORIGINAL), '--seconds', '0',
                 '--csv', str(path)), ec=ec)
            self.assertEqual(rc, 2)
            self.assertEqual(
                err.strip(),
                f"refusing: target {ORIGINAL} mV is not below the current "
                f"{ORIGINAL} mV (lower only).")
            # Equality is the boundary, not just a clearly-higher value. A
            # refused run does read the EC -- that read is how it learns what it
            # is refusing to exceed -- so the claim here is about writes.
            self.assertGreater(ec.reads, 0)
            self.assertEqual(ec.writes, [])
            self.assertFalse(path.exists())

    def test_a_target_below_the_floor_is_refused_on_units(self):
        # Below ORIGINAL, so this passes the lower-only check and is the one
        # that gets to say the target is implausible for a 4S pack.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, err = self.run_tool(
                ('--target-mv', str(FLOOR - 1000), '--seconds', '0',
                 '--i-mean-it', '--csv', str(path)))
            self.assertEqual(rc, 2)
            self.assertEqual(
                err.strip(),
                f"refusing: target {FLOOR - 1000} mV is implausibly low for a "
                "4S pack; check units.")
            self.assertEqual(ec.writes, [])
            self.assertFalse(path.exists())

    def test_writing_without_i_mean_it_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, err = self.run_tool(
                ('--target-mv', str(TARGET), '--seconds', '0', '--csv', str(path)))
            self.assertEqual(rc, 2)
            self.assertEqual(err.strip(), "refusing to write without --i-mean-it")
            self.assertEqual(ec.writes, [])
            self.assertFalse(path.exists())

    # 2. The refusals come after the read they are judged against, and the
    #    safety one is checked first: a run that is both too high and
    #    unacknowledged is refused for the reason that protects the cell.
    def test_the_lower_only_refusal_precedes_the_i_mean_it_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, err = self.run_tool(
                ('--target-mv', str(ORIGINAL), '--seconds', '0', '--csv', str(path)))
            self.assertEqual(rc, 2)
            self.assertIn("(lower only)", err)
            self.assertNotIn("--i-mean-it", err)
            self.assertEqual(ec.writes, [])

    # 3. The ordering itself, positively: on a run that goes all the way, the
    #    target is written first and the restore last, with nothing between
    #    them. One pass of the loop is all this is, so this is the whole write
    #    history -- move the refusals below the first write and the list grows.
    def test_the_restore_is_the_last_thing_written(self):
        clock = Clock()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, _ = self.run_tool([*BASE, '--csv', str(path)], clock=clock)
            self.assertEqual(rc, 0)
            self.assertEqual(ec.writes, TARGET_WRITES + RESTORE_WRITES)
            # Breaks on the seconds check before the interval is ever slept,
            # which is the "exactly one pass" above being true.
            self.assertEqual(clock.slept, [])

    # 4. The restore, and the line the tool prints off its own readback rather
    #    than a value the test worked out for it.
    def test_a_clean_run_restores_the_original_and_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, out, _ = self.run_tool([*BASE, '--csv', str(path)])
            self.assertEqual(rc, 0)
            self.assertEqual(tool.u16(ec, tool.ADDR_TARGET), ORIGINAL)
            self.assertIn(f"restored 0x0522 -> {ORIGINAL} mV, "
                          f"readback = {ORIGINAL} mV", out)
            # The write's own verdict is deliberately not asserted past the
            # numbers: this fake holds what is written to it, and §4m measured
            # the real EC doing the opposite.
            self.assertIn(f"wrote 0x0522 = {TARGET} mV, immediate "
                          f"readback = {TARGET} mV", out)

    # 5. The same restore when the run fails. boom_on=1 is the in-loop WMI
    #    call, which is after the write and inside the try the finally belongs
    #    to -- and the raise is the fake module's own EcError, because the tool
    #    binds that name at import and a plain RuntimeError would go out of
    #    main() instead of becoming a return code.
    def test_an_ec_error_partway_still_restores_the_target(self):
        ec = FakeEc()
        wmi = FakeWmi(boom_on=1, exc=FakeEcError("WMI query failed"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, out, err = self.run_tool([*BASE, '--csv', str(path)],
                                             ec=ec, wmi=wmi)
            self.assertEqual(rc, 1)
            self.assertEqual(err.strip(), "error: WMI query failed")
            self.assertEqual(ec.writes, TARGET_WRITES + RESTORE_WRITES)
            self.assertIn(f"restored 0x0522 -> {ORIGINAL} mV", out)
            # An errored run still leaves a CSV a reader can parse.
            rows = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(rows, [COLS])

    def test_ctrl_c_partway_still_restores_the_target(self):
        ec = FakeEc()
        wmi = FakeWmi(boom_on=1, exc=KeyboardInterrupt())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            with self.assertRaises(KeyboardInterrupt):
                self.run_tool([*BASE, '--csv', str(path)], ec=ec, wmi=wmi)
            # KeyboardInterrupt is a BaseException, so `except EcError` cannot
            # catch it and it leaves main() uncaught. What puts the target back
            # is the finally, which is why that arm is a finally rather than an
            # except clause.
            self.assertEqual(ec.writes, TARGET_WRITES + RESTORE_WRITES)

    # 6. The CSV's shape, read off a file the tool actually wrote.
    def test_the_csv_header_is_the_pinned_column_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, _, _, _ = self.run_tool([*BASE, '--csv', str(path)])
            rows = list(csv.reader(path.read_text().splitlines()))
            self.assertEqual(rc, 0)
            self.assertEqual(rows[0], COLS)
            self.assertEqual(len(rows), 2)          # header, and the one sample
            self.assertEqual(len(rows[1]), len(COLS))
            self.assertEqual(rows[1][COLS.index("target_written_mv")], str(TARGET))

    def test_the_committed_0522_traces_share_that_header(self):
        traces = sorted((Path(__file__).parents[2] / "evidence" / "battery-traces")
                        .glob("2026-09-21-0522-*.csv"))
        # A glob that matches nothing would make the loop below vacuous, which
        # is the one thing it must not be.
        self.assertTrue(traces, "no committed 0x0522 trace to check the header of")
        for trace in traces:
            with self.subTest(trace=trace.name):
                header = next(csv.reader(trace.read_text().splitlines()))
                self.assertEqual(header, COLS)


if __name__ == '__main__':
    unittest.main()
