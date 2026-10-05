#!/usr/bin/env python3
r"""Offline checks on `charge_target_test.py --hold`, the mode two of its live runs took.

`--hold` is what the tool recommends for itself ("Use `--interval 0.2` or so",
in the `--hold` help), and it is the mode `holdcheck_battery` and
`follow_cv_highcap` were run in -- the runs that produced docs/findings.md
§4m's answer. `test_charge_target_test.py` covers the non-hold arm: the three
refusals, the restore in the `finally`, and a write history of exactly the
target and then the restore. Three shapes exist only under `--hold` and none of
them is reachable from that fixture:

  * the inner re-assert loop, which re-writes the target for a whole interval
    and sleeps `--hold-ms` between attempts, spending as much of the interval as
    it can at our value;
  * the write-then-immediate-readback sample after it, one per loop pass, which
    exists precisely to catch a byte that holds only momentarily;
  * the negative arm of `if not args.hold: time.sleep(args.interval)` -- the
    interval sleep that hold mode must never take, because the inner loop has
    already spent the interval.

It is the last of those that decides the shape of every case here. That line
sits *below* the `if time.time() - t0 >= args.seconds: break`, so a run short
enough to break on its first pass never reaches it: with the fixture's own
`--seconds 0`, deleting the guard changes nothing at all and a suite built on
that would assert a property of a line that never ran. Every case below
therefore runs long enough for the loop to iterate, and
`test_the_loop_iterates_before_the_never_sleep_arm` is what holds that, so
retuning the values here into a vacuous run goes red instead of quietly
passing.

The fixtures come from `test_charge_target_test.py` rather than being written
again here, following `test_ecrw_pacing.py`'s cross-import: the register map
in particular is what makes the restore's readback checkable at all, and a
second copy of it would be a second source of truth. Importing that module also
runs its `ecrw_fake.install()`, which is the only way a suite in this directory
is allowed to put the fake `ecrw` in place, so this file never writes
`sys.modules` itself. `tools/run-tests.sh` gives each suite file its own
interpreter, so importing it here decides nothing for the suites that follow.

Nothing here opens an EC, reads a register back, or spawns a `powershell`. The
register map keeps what is written to it, which is a property of that fixture
and nothing more: §4m measured the real EC reclaiming `0x0522` faster than a
single ~100 µs host round-trip, so nothing in this file is evidence about
whether a host write holds, and the "held" column the tool logs is not asserted
past the numbers.
"""
import contextlib
import csv
import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import test_charge_target_test as base

FakeEc = base.FakeEc
ORIGINAL = base.ORIGINAL
RESTORE_WRITES = base.RESTORE_WRITES
TARGET = base.TARGET
TARGET_WRITES = base.TARGET_WRITES
tool = base.tool

# The three knobs a hold run needs, chosen against the clock's step below so the
# loop iterates rather than breaking on its first pass. Nothing else about the
# run is pinned: the assertions are relations over what the run actually did --
# the sleeps it took and the rows it wrote -- so these can be retuned without a
# figure anywhere having to move with them.
INTERVAL = 0.25
HOLD_MS = 20
SECONDS = 1.5

# The fake clock's step. Explicit rather than inherited from `base.Clock`'s
# default because the arithmetic below -- how many loop passes these values buy
# -- is a relation between the interval and this step, and a reader checking it
# needs both numbers in front of them.
STEP = 0.1


class BoomEc(FakeEc):
    """A fake EC that raises once, on a chosen write, and never again.

    Which write is what puts the raise *inside the inner re-assert loop*: the
    tool writes the target once before the loop, then `w16` per inner
    iteration, so an index past the first `w16` lands among the re-asserts. The
    index is a write ordinal, not an address, because the ordinal is what says
    "the third write the tool made", which is the thing being placed.

    The latch is load-bearing. Without it the raise fires a second time inside
    the `finally`'s own restore write, the restore dies partway, and the case
    reports a restore failure the tool does not have -- a fixture artefact that
    looks exactly like the defect this suite is for. It fails silently: the
    write list still ends in a plausible shape, just not the right one.
    """

    def __init__(self, boom_on, exc):
        super().__init__()
        self.boom_on = boom_on
        self.exc = exc
        self.fired = False

    def write(self, addr, val):
        if not self.fired and len(self.writes) == self.boom_on:
            self.fired = True
            raise self.exc
        super().write(addr, val)


def run_tool(argv, ec=None, clock=None, wmi=None):
    """`main()` with the device, the WMI line and the clock stood in for.

    Mirrors `test_charge_target_test.ChargeTargetTests.run_tool` rather than
    calling it: that one is a method that never touches `self`, and reaching
    through a TestCase to borrow it would tie this file's cases to a class they
    have nothing else in common with. Written out again so a failure here reads
    on its own, in this file, without the reader opening the other one.

    Only `subprocess.run` is replaced, so the tool's own `wmi()` runs and the
    six-token parse and the `dict(zip(keys, ...))` the CSV row is built from are
    covered along with it.
    """
    ec = ec if ec is not None else FakeEc()
    clock = clock if clock is not None else base.Clock()
    wmi = wmi if wmi is not None else base.FakeWmi()
    out, err = io.StringIO(), io.StringIO()
    with patch.object(tool, 'Ec', lambda: ec), \
         patch.object(tool, 'subprocess',
                      types.SimpleNamespace(run=wmi.run)), \
         patch.object(tool.time, 'time', clock.time), \
         patch.object(tool.time, 'sleep', clock.sleep), \
         contextlib.redirect_stdout(out), \
         contextlib.redirect_stderr(err):
        rc = tool.main(list(argv))
    return rc, ec, clock, out.getvalue(), err.getvalue()


def csv_rows(path):
    """The rows the tool wrote, read off the file rather than off the run."""
    return list(csv.reader(path.read_text(encoding="utf-8").splitlines()))


def hold_argv(path):
    """A hold-mode command line, from the knobs above.

    Held in one place rather than spelled at each call site so that the flag
    names the tool actually parses are asserted once: `--hold-ms` is what sets
    each sleep and `--interval` what bounds the inner loop, and a case that
    passed the wrong flag would quietly stop being a hold run.
    """
    return ['--target-mv', str(TARGET), '--hold', '--i-mean-it',
            '--interval', str(INTERVAL), '--hold-ms', str(HOLD_MS),
            '--seconds', str(SECONDS), '--csv', str(path)]


class ChargeTargetHoldTests(unittest.TestCase):
    # 1. The write history. Every re-assert is exactly one `--hold-ms` sleep, so
    #    the sleep list is what the re-assert count is read off -- and each loop
    #    pass adds the write-then-readback sample on top of its re-asserts, which
    #    is why the pass count is a term of its own here. One w16 is the initial
    #    write, one the restore, and `passes` the samples: the whole history is
    #    that many writes of the target followed by the restore, so however many
    #    repeats there were the last two writes are still the restore.
    #
    #    `passes` is counted off the CSV rather than written down, so this is a
    #    relation over the run -- a retune of INTERVAL or SECONDS moves the
    #    fixture's step and the two sides together.
    def test_the_restore_is_the_last_thing_written_however_many_repeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, clock, _, _ = run_tool(hold_argv(path),
                                           clock=base.Clock(step=STEP))
            passes = len(csv_rows(path)) - 1      # less the header row
            self.assertEqual(rc, 0)
            self.assertEqual(
                ec.writes[:-len(RESTORE_WRITES)],
                TARGET_WRITES * (1 + len(clock.slept) + passes))
            self.assertEqual(ec.writes[-len(RESTORE_WRITES):], RESTORE_WRITES)
            self.assertEqual(tool.u16(ec, tool.ADDR_TARGET), ORIGINAL)

    # 2. ... and the precondition that makes case 1 say anything. The
    #    never-sleep arm sits below the `--seconds` break, so a run that breaks
    #    on its first pass never reaches it, and a fixture tuned into that shape
    #    would leave every other case here asserting a line that did not run.
    def test_the_loop_iterates_before_the_never_sleep_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            clock = base.Clock(step=STEP)
            rc, _, _, _, _ = run_tool(hold_argv(path), clock=clock)
            self.assertEqual(rc, 0)
            self.assertGreater(len(csv_rows(path)) - 1, 1,
                               "the loop broke on its first pass, so the "
                               "never-sleep arm below the --seconds check never "
                               "ran")
            # ... and the re-assert loop itself, not just the loop around it: a
            # run whose inner loop never iterated would satisfy the relation in
            # case 1 with the inner loop entirely untested.
            self.assertTrue(clock.slept,
                            "hold mode took no --hold-ms sleep, so the inner "
                            "re-assert loop never ran")

    # 3. The never-sleep property itself. Deliberately *not* "hold mode never
    #    sleeps": it does, `--hold-ms` at a time, and that is the point of the
    #    flag. What must never happen is the interval sleep -- hold mode has
    #    already spent the interval inside the inner loop, and taking it again
    #    would double every sample's spacing. Asserted over the whole sleep list
    #    rather than against a count, so a run that iterated a different number
    #    of times is still held to it.
    def test_hold_mode_never_sleeps_the_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            clock = base.Clock(step=STEP)
            rc, _, _, _, _ = run_tool(hold_argv(path), clock=clock)
            self.assertEqual(rc, 0)
            self.assertTrue(clock.slept)
            self.assertEqual(set(clock.slept), {HOLD_MS / 1000.0},
                             f"hold mode slept for something other than "
                             f"--hold-ms: {sorted(set(clock.slept))}")
            self.assertNotIn(INTERVAL, clock.slept)

    # 4. The same restore when the run fails from *inside* the inner loop
    #    rather than at the WMI call. This is the write-heaviest point in the
    #    tool -- every byte of every `w16` is a live charge-voltage target --
    #    and the one the `finally` most needs: without it the target is left
    #    wherever the EC or the last partial write put it.
    #
    #    `boom_on` is past the first `w16` (the pre-loop write) and lands on the
    #    low byte of the second re-assert, so the raise happens between two
    #    `w16` calls with the register already at the target. The raise is the
    #    fake module's own EcError, because the tool binds that name at import
    #    and any other class of the same shape -- `ecrw_fake.EcError`'s own base
    #    included -- would go out of main() instead of becoming a return code.
    def test_an_ec_error_inside_the_re_assert_loop_still_restores(self):
        ec = BoomEc(boom_on=4, exc=base.ecrw_fake.EcError("EC write failed"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            rc, ec, _, out, err = run_tool(hold_argv(path), ec=ec,
                                           clock=base.Clock(step=STEP))
            self.assertEqual(rc, 1)
            self.assertEqual(err.strip(), "error: EC write failed")
            self.assertEqual(ec.writes[-len(RESTORE_WRITES):], RESTORE_WRITES)
            self.assertEqual(tool.u16(ec, tool.ADDR_TARGET), ORIGINAL)
            self.assertIn(f"restored 0x0522 -> {ORIGINAL} mV", out)

    # 5. ... and on Ctrl-C from the same point, which is the arm that has to be
    #    a `finally` rather than an `except`: KeyboardInterrupt is a
    #    BaseException, so `except EcError` cannot catch it and it leaves
    #    `main()` uncaught. What puts the target back is the finally, and this
    #    is the interruption point that most needs it.
    def test_ctrl_c_inside_the_re_assert_loop_still_restores(self):
        ec = BoomEc(boom_on=4, exc=KeyboardInterrupt())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run.csv'
            with self.assertRaises(KeyboardInterrupt):
                run_tool(hold_argv(path), ec=ec, clock=base.Clock(step=STEP))
            self.assertEqual(ec.writes[-len(RESTORE_WRITES):], RESTORE_WRITES)
            self.assertEqual(tool.u16(ec, tool.ADDR_TARGET), ORIGINAL)


if __name__ == '__main__':
    unittest.main()