#!/usr/bin/env python3
"""Offline checks on `ecrw.py dump`'s fan-page exclusion and its per-read gap.

The fixture comes from `test_ecrw.py` rather than being written again here:
that module already stands a fake kernel32 in front of the *real* `ecrw.py`,
and that is the only boundary worth having this checked at. A `dump` that
still issued an `ECRR` for `0x0464` after this change would show up in
`K32.calls` -- on the wire -- rather than in printed output, and a suite built
on a stand-in for `ecrw` would only be able to check the stand-in.
`tools/run-tests.sh` gives each suite file its own interpreter, so importing it
here cannot decide anything for the suites that follow.

Every case reads `K32.calls` for the access and the printed output for the
accounting, because the two are separate claims: the gap is the sleep, and the
notice about dropped bytes is the operator's only way to know the run was not
the one they asked for.

Nothing here opens a driver or an EC, and nothing here says anything about
what these reads do to a fan on the machine.
`docs/findings/ec-read-pacing-fan-page.md` is the write-up, and it is explicit
that 6 ms is a sibling board's figure and not one measured here.
"""
import contextlib
import io
import unittest
from unittest.mock import patch

import test_ecrw

ecrw = test_ecrw.ecrw
K32 = test_ecrw.K32
FAN_TACH = set(range(0x0460, 0x0470))


def ecrr_offsets():
    """Every EC offset read one byte at a time, in the order they were issued."""
    return [int.from_bytes(buf[:2], "little")
            for code, buf in K32.calls if code == test_ecrw.FAKE_IOCTL_ECRR]


def mmrd_offsets():
    """Every EC offset read through a block, overshoot included."""
    return [o for o in K32.offsets() if 0 <= o < ecrw.EC_SIZE]


def covered_by_mmrds():
    """Every EC byte a block read reached, its four-byte overshoot included."""
    out = set()
    for off in mmrd_offsets():
        out.update(range(off, off + 4))
    return out


class DumpPacingTests(unittest.TestCase):
    def setUp(self):
        K32.calls = []
        K32.ram = bytes(range(256)) * 256

    def dump(self, *argv, at_default_gap=False):
        """`dump` with stdout and stderr captured, and the sleep taken out.

        `--gap-ms 0` is added unless the case is about the default: a 2 KiB
        dump at 6 ms is twelve seconds of real `time.sleep`, which is the whole
        point of the flag and no use to a case about the exclusion. A case that
        does want the default passes `at_default_gap` and patches `time.sleep`
        itself, so what the tool slept is recorded rather than waited out.
        """
        if not at_default_gap and "--gap-ms" not in argv:
            argv = (*argv, "--gap-ms", "0")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(ecrw.main(["dump", *argv]), 0)
        return out.getvalue(), err.getvalue()

    # 1. The exclusion, asserted on the wire rather than in the output.
    def test_a_wide_dump_issues_no_read_of_a_fan_tach_byte(self):
        self.dump("0x0000", "0x0800")
        self.assertEqual(set(ecrr_offsets()) & FAN_TACH, set())
        # And the reads it did make are the rest of the range, not a shorter
        # run of some other set: an exclusion that shortened the sweep rather
        # than cutting a hole in it would pass the assertion above.
        self.assertEqual(len(ecrr_offsets()), 0x0800 - len(FAN_TACH))

    def test_the_opt_in_reads_the_page(self):
        self.dump("0x0000", "0x0800", "--include-fan-tach")
        self.assertEqual(set(ecrr_offsets()) & FAN_TACH, FAN_TACH)

    def test_the_block_path_issues_no_mmrd_reaching_the_page(self):
        # The half that a per-byte assertion cannot reach: a block read names
        # one offset and returns four bytes, so `ecrr_offsets` would see
        # nothing at all while the sweep read straight over the page.
        self.dump("0x0000", "0x0800", "--block")
        self.assertEqual(covered_by_mmrds() & FAN_TACH, set())
        self.assertEqual(len(covered_by_mmrds()), 0x0800 - len(FAN_TACH))

    def test_the_block_opt_in_reads_the_page(self):
        self.dump("0x0000", "0x0800", "--block", "--include-fan-tach")
        self.assertEqual(covered_by_mmrds() & FAN_TACH, FAN_TACH)

    def test_a_block_range_straddling_the_page_does_not_read_it(self):
        # readmany covers a run with the blocks enclosing it and reads past on
        # both sides. A run ending at 0x045F and one starting at 0x0470 are
        # both aligned, so neither overshoots onto the page -- which is what
        # makes the exclusion exact here rather than approximate.
        self.dump("0x0450", "0x30", "--block")
        self.assertEqual(covered_by_mmrds() & FAN_TACH, set())

    def test_a_range_the_page_splits_keeps_both_sides(self):
        self.dump("0x0450", "0x30")
        self.assertEqual(set(ecrr_offsets()),
                         set(range(0x0450, 0x0460)) | set(range(0x0470, 0x0480)))

    # 2. The accounting, because a hole in a hexdump that nothing says so
    #    reads as a range that ended there.
    def test_a_dropped_page_is_named_on_stderr(self):
        out, err = self.dump("0x0000", "0x0800")
        self.assertIn("16 byte(s)", err)
        self.assertIn("0x0460-0x046F", err)
        self.assertIn("--include-fan-tach", err)
        # Nothing on stdout: the hexdump is still a hexdump, and the accounting
        # for it does not go into the middle of one.
        self.assertNotIn("not reading", out)

    def test_a_dropped_byte_prints_as_a_gap_rather_than_as_nothing(self):
        out, _ = self.dump("0x0450", "0x30")
        rows = {line[:4]: line.split(": ", 1)[1].split()
                for line in out.splitlines()}
        self.assertEqual(rows["0460"], ["--"] * 16)
        # Its neighbours are real bytes, so the hole is a hole and not a row
        # the tool declined to print: the address range stays on screen and
        # what is missing from it is marked rather than gone.
        self.assertNotIn("--", rows["0450"])
        self.assertNotIn("--", rows["0470"])

    def test_a_range_inside_the_page_says_nothing_was_read(self):
        out, err = self.dump("0x0460", "0x10")
        self.assertIn("nothing was read", err)
        # The row is printed so the addresses stay visible, and every cell in
        # it is the gap marker rather than a byte -- a row of `00` would be a
        # page of zeros that did not move, which is a result.
        self.assertEqual(out, "0460: " + " ".join(["--"] * 16) + "\n")
        self.assertEqual(K32.calls, [])

    def test_a_dump_off_the_page_says_nothing_about_it(self):
        out, err = self.dump("0x0750", "0x20")
        self.assertEqual(err, "")
        self.assertNotIn("--", out)

    # 3. The gap. A flag the tool accepts is not a sleep it takes.
    def test_the_default_gap_sleeps_after_every_read(self):
        slept = []
        with patch("time.sleep", slept.append):
            self.dump("0x0750", "0x20", at_default_gap=True)
        self.assertEqual(len(slept), 0x20)
        self.assertEqual({round(s * 1000, 6) for s in slept}, {6.0})

    def test_the_gap_default_is_six_milliseconds(self):
        # Read off the sleep rather than off the argparse default: the
        # module's own default is the same number by construction, and would
        # stay green if the sleep were dropped from the read loop.
        slept = []
        with patch("time.sleep", slept.append):
            self.dump("0x0750", "0x20", at_default_gap=True)
        self.assertEqual({round(s * 1000, 6) for s in slept}, {6.0})

    def test_a_narrower_gap_reaches_the_sleep(self):
        slept = []
        with patch("time.sleep", slept.append):
            self.dump("0x0750", "0x20", "--gap-ms", "2")
        self.assertEqual({round(s * 1000, 6) for s in slept}, {2.0})

    def test_a_zero_gap_sleeps_not_at_all(self):
        slept = []
        with patch("time.sleep", slept.append):
            self.dump("0x0750", "0x20", "--gap-ms", "0")
        self.assertEqual(slept, [])
        self.assertEqual(len(K32.calls), 0x20)

    def test_the_block_path_sleeps_once_per_run(self):
        # One gap per `readmany` rather than per IOCTL, because a run is four
        # bytes and the loop above it never sees the blocks inside one. Pinned
        # because a run count of zero would be a dump that paced itself not
        # at all.
        slept = []
        with patch("time.sleep", slept.append):
            self.dump("0x0750", "0x20", "--block", at_default_gap=True)
        self.assertEqual(len(slept), 2)
        self.assertEqual(len(K32.calls), 8)


if __name__ == '__main__':
    unittest.main()