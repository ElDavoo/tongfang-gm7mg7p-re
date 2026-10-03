#!/usr/bin/env python3
r"""Offline checks for the fan-tach exclusion and `--gap-ms`; no EC is opened.

What this stands in for is the question `ec_watch.py` answers by *not* reading
`0x0460-0x046F`, and by sleeping between the reads it does make. HydroControl
reports that ECRR reads of that page stalled the fans on a sibling board and
that the OEM software and `uniwill-laptop` sleep about 6 ms after every EC
access (#94, `docs/related-projects.md`); neither the stall nor the 6 ms has
been observed or measured on this machine, so what is pinned here is that the
tool's defaults are what those sources describe, not that they are right.

The evidence is the addresses that reached the wire, not the text on screen.
`RecordingEc` below answers every read as `0x00` and writes down what it was
asked for, so a sweep that quietly issued a read of `0x0464` is caught even
though every byte it brought back looks the same. `test_ecrw.py` holds the same
question for `ecrw.py dump` against a fake kernel32, which is the only way to
see the IOCTLs themselves.

Nothing here opens a driver, reads a register or touches Windows. The gap is
recorded rather than slept, so a case asking for the default 6 ms costs
no 6 ms.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import time as real_time
import unittest
from unittest.mock import patch

import ecrw_fake

# Written out here rather than read off the tool, because every case below
# compares against it: `TheConstantTests` is what holds the two together, so a
# page that moved in the tool without moving here is a red run rather than a
# suite quietly passing against a range nothing reads.
FAN_TACH = set(range(0x0460, 0x0470))


class RecordingEc:
    """Every read one sweep issued, and `0x00` for all of them.

    Recording rather than answering from a script is what these cases are for:
    what moved is not under test, and a fixture with bytes in it would turn
    "which addresses" into "what did they hold". The run ends when a sweep
    starts a second time -- recognized by a read the fake has already answered
    since the last one began -- and the `KeyboardInterrupt` is the one `main`
    already catches. That keeps the sweep's length out of every case below,
    which is the thing most of them would otherwise have to restate.
    """

    def __init__(self):
        self.reads = []
        self.blocks = []
        self._seen = set()
        self._runs = set()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        if addr in self._seen:
            raise KeyboardInterrupt
        self._seen.add(addr)
        self.reads.append(addr)
        return 0x00

    def readmany(self, start, length):
        if (start, length) in self._runs:
            raise KeyboardInterrupt
        self._runs.add((start, length))
        self.blocks.append((start, length))
        return {a: 0x00 for a in range(start, start + length)}


class FakeTime:
    """`time` with the sleeps written down instead of taken.

    `--gap-ms` defaults to a few milliseconds, and a case that took it for real
    would cost its own runtime multiplied by the reads in it. What has to be
    pinned is that the value reaches `time.sleep`, so it is recorded there.
    `time.time` is the real one: the run's own elapsed time and its
    `--seconds` deadline both read it.
    """

    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    @staticmethod
    def time():
        return real_time.time()


ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'ec_watch_pacing', Path(__file__).with_name('ec_watch.py'))
ec_watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec_watch)


def run_watch(*argv, interval="0", clock=None):
    """`(rc, ec, stdout, stderr)` for one run against a `RecordingEc`.

    `--gap-ms 0` unless a case asks otherwise, so a case that does not care
    about pacing does not pay for it; `clock` is what stands in for
    `time.sleep`, and without one the default really is slept.
    """
    ec = RecordingEc()
    out, err = io.StringIO(), io.StringIO()
    with patch.object(ec_watch, 'Ec', lambda: ec), \
         contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        if clock is not None:
            with patch.object(ec_watch, 'time', clock):
                rc = ec_watch.main(['--interval', interval, *argv])
        else:
            rc = ec_watch.main(['--interval', interval, *argv])
    return rc, ec, out.getvalue(), err.getvalue()


class TheConstantTests(unittest.TestCase):
    def test_the_tool_leaves_out_the_page_this_file_names(self):
        self.assertEqual(set(ec_watch.FAN_TACH), FAN_TACH)


class ExclusionTests(unittest.TestCase):
    """The default sweep does not read the page, and the flag puts it back.

    The dangerous failure is not that the page is read -- that is what the flag
    is for -- but that a range which was to be swept silently becomes an empty
    one and prints a baseline followed by "nothing moved", which reads as an
    observation about the EC. Every case here is about which addresses reached
    the wire.
    """

    def test_the_default_range_reads_no_fan_tach_byte(self):
        rc, ec, _, _ = run_watch('--start', '0x0000', '--len', '0x0800',
                                 '--gap-ms', '0')
        self.assertEqual(rc, 0)
        self.assertTrue(ec.reads)
        self.assertEqual(set(ec.reads) & FAN_TACH, set())
        # The rest of the range really was read, so this is not passing because
        # the sweep did nothing at all.
        self.assertIn(0x045F, ec.reads)
        self.assertIn(0x0470, ec.reads)

    def test_a_range_straddling_the_page_reads_only_what_it_named(self):
        _, ec, _, _ = run_watch('--start', '0x0450', '--len', '0x40',
                                '--gap-ms', '0')
        self.assertEqual(sorted(ec.reads),
                         list(range(0x0450, 0x0460))
                         + list(range(0x0470, 0x0490)))

    def test_the_flag_reads_the_page(self):
        _, ec, out, _ = run_watch('--start', '0x0460', '--len', '0x10',
                                  '--gap-ms', '0', '--include-fan-tach')
        self.assertEqual(set(ec.reads), FAN_TACH)
        # And says so where the operator is looking rather than leaving it to
        # a help page nobody opened.
        self.assertIn('0x0460-0x046F', out)
        self.assertIn('#94', out)

    def test_the_default_run_names_the_page_as_left_out_not_as_a_warning(self):
        _, _, out, _ = run_watch('--start', '0x0000', '--len', '0x0800',
                                 '--gap-ms', '0')
        self.assertIn('left out', out)
        self.assertIn('0x0460-0x046F', out)
        # The banner is reporting what was not read. It is the warning the
        # opt-in carries that an operator reads as a hazard, and a run that
        # never read the page must not be dressed as one that did.
        self.assertNotIn('warning', out)

    def test_a_range_entirely_inside_the_page_is_reported_not_swept(self):
        rc, ec, out, err = run_watch('--start', '0x0460', '--len', '0x10',
                                     '--gap-ms', '0')
        self.assertNotEqual(rc, 0)
        self.assertEqual(ec.reads, [])
        # Said rather than printed as a normal sweep: an empty baseline and a
        # "nothing moved" would read as an observation about the EC.
        self.assertNotIn('baseline', out)
        self.assertIn('nothing to sweep', err)
        self.assertIn('0x0460-0x046F', err)
        self.assertIn('--include-fan-tach', err)

    def test_a_range_entirely_inside_the_page_runs_with_the_flag(self):
        rc, ec, _, _ = run_watch('--start', '0x0460', '--len', '0x10',
                                 '--gap-ms', '0', '--include-fan-tach')
        self.assertEqual(rc, 0)
        self.assertEqual(set(ec.reads), FAN_TACH)

    def test_a_range_off_the_page_is_untouched(self):
        _, ec, out, _ = run_watch('--start', '0x0700', '--len', '0x100',
                                  '--gap-ms', '0')
        self.assertEqual(ec.reads, list(range(0x0700, 0x0800)))
        # Nothing was left out of it, so the notice does not fire.
        self.assertNotIn('left out', out)


class BlockExclusionTests(unittest.TestCase):
    """`--block` reads runs of the *kept* addresses, so none crosses the page.

    The exactness is arithmetic rather than luck: `0x0460` is dword-aligned and
    the page is sixteen bytes, so every block holding a fan-tach byte lies
    wholly inside it. A run ending at `0x045F` is covered by blocks up to
    `0x045C` and a run starting at `0x0470` by blocks from `0x0470`, so neither
    can have one read in for it -- which is what lets the tool promise the
    exclusion under `--block` rather than only on the byte path.
    """

    def covered(self, ec):
        """Every EC byte a set of `(start, length)` reads brought back.

        The blocks a run covers are the aligned ones enclosing it, which is
        `ecrw.Ec.readmany`'s cover and more than the run's own length: a run
        that does not end on a block boundary reads the block past it.
        """
        out = set()
        for start, length in ec.blocks:
            out.update(range(start & ~3, ((start + length - 1) & ~3) + 4))
        return out

    def test_the_default_range_splits_into_two_runs_around_the_page(self):
        rc, ec, _, _ = run_watch('--start', '0x0000', '--len', '0x0800',
                                 '--gap-ms', '0', '--block')
        self.assertEqual(rc, 0)
        self.assertEqual(ec.blocks, [(0x0000, 0x460), (0x0470, 0x390)])
        self.assertEqual(self.covered(ec) & FAN_TACH, set())

    def test_the_block_runs_carry_the_whole_range_but_the_page(self):
        _, ec, _, _ = run_watch('--start', '0x0000', '--len', '0x0800',
                                '--gap-ms', '0', '--block')
        read = set()
        for start, length in ec.blocks:
            read.update(range(start, start + length))
        self.assertEqual(read & FAN_TACH, set())
        # The page is the only thing missing, so this is an exclusion and not
        # a sweep that quietly covers less than it was asked for.
        self.assertEqual(read | FAN_TACH, set(range(0x0000, 0x0800)))

    def test_a_range_straddling_the_page_still_reads_no_page_byte(self):
        _, ec, _, _ = run_watch('--start', '0x0450', '--len', '0x40',
                                '--gap-ms', '0', '--block')
        self.assertEqual(ec.blocks, [(0x0450, 0x10), (0x0470, 0x20)])
        self.assertEqual(self.covered(ec) & FAN_TACH, set())

    def test_the_flag_reads_the_page_as_blocks(self):
        _, ec, _, _ = run_watch('--start', '0x0460', '--len', '0x10',
                                '--gap-ms', '0', '--block',
                                '--include-fan-tach')
        self.assertEqual(ec.blocks, [(0x0460, 0x10)])


class GapTests(unittest.TestCase):
    """`--gap-ms` reaches `time.sleep`, at the default and at the operator's.

    Pinned by what was recorded rather than by the flag being accepted: a
    `--gap-ms` parsed and then dropped would satisfy every other case here.
    The default is asserted as a value this file carries, not read back out of
    the argparse default under test.

    Every run below asks for a `--interval` that is *not* the gap, because the
    loop's own sleep is a second caller of the same function and a case that
    could not tell the two apart would pass with the interval silently taking
    the gap's place.
    """

    # HydroControl's figure for the OEM software and uniwill-laptop, and this
    # repository's default. Not measured on this machine.
    DEFAULT_MS = 6
    INTERVAL = "0.25"

    def test_the_default_gap_reaches_the_sleep(self):
        clock = FakeTime()
        run_watch('--start', '0x0700', '--len', '0x4',
                  interval=self.INTERVAL, clock=clock)
        self.assertEqual(clock.sleeps, [self.DEFAULT_MS / 1000] * 4
                         + [float(self.INTERVAL)])

    def test_the_gap_is_paid_per_read_and_not_per_sweep(self):
        # Four reads, four gaps. A gap taken once per sweep would have slept
        # 6 ms for 2 KiB of EC, which is the unpaced tool this default stopped
        # being, and the banner's per-read projection would be a fiction.
        clock = FakeTime()
        run_watch('--start', '0x0700', '--len', '0x4',
                  interval=self.INTERVAL, clock=clock)
        self.assertEqual(clock.sleeps.count(self.DEFAULT_MS / 1000), 4)

    def test_the_gap_flag_is_what_the_operator_asked_for(self):
        clock = FakeTime()
        run_watch('--start', '0x0700', '--len', '0x4', '--gap-ms', '12.5',
                  interval=self.INTERVAL, clock=clock)
        self.assertEqual(clock.sleeps, [0.0125] * 4 + [0.25])

    def test_zero_is_the_unpaced_tool(self):
        clock = FakeTime()
        run_watch('--start', '0x0700', '--len', '0x4', '--gap-ms', '0',
                  interval=self.INTERVAL, clock=clock)
        self.assertEqual(clock.sleeps, [0.0] * 4 + [0.25])

    def test_the_block_path_pays_the_gap_per_block_read(self):
        # Two runs, two block reads, two gaps -- not one per address, which
        # is the difference between the two paths' cost and the reason the
        # banner counts reads rather than addresses.
        clock = FakeTime()
        run_watch('--start', '0x0000', '--len', '0x0800', '--gap-ms', '6',
                  '--block', interval=self.INTERVAL, clock=clock)
        self.assertEqual(clock.sleeps, [0.006] * 2 + [0.25])

    def test_the_interval_is_a_different_axis_and_stays_where_it_was(self):
        # The loop's own sleep appears once and is not multiplied by the
        # reads: `--interval` paces sweeps, `--gap-ms` paces reads, and a gap
        # that quietly covered the interval would be pacing the wrong thing.
        clock = FakeTime()
        run_watch('--start', '0x0700', '--len', '0x4', '--gap-ms', '0',
                  interval=self.INTERVAL, clock=clock)
        self.assertEqual(clock.sleeps.count(float(self.INTERVAL)), 1)


class BannerTests(unittest.TestCase):
    """The cost is printed before the loop, and it is a count of reads.

    An operator who cannot see what a paced full-range sweep costs decides it
    from the docstring instead, or from how long the run seems to take to stop.
    """

    def banner_seconds(self, *argv):
        # A FakeTime rather than a real sleep: the banner quotes `args.gap_ms`
        # and not the clock, so recording the gap changes nothing it prints,
        # and a case that let the default through would cost this suite the
        # seconds the projection is about.
        _, _, out, _ = run_watch(*argv, clock=FakeTime())
        line = [ln for ln in out.splitlines() if 'per sweep' in ln]
        self.assertEqual(len(line), 1, out)
        return float(line[0].split('about ')[1].split('s a sweep')[0])

    def test_the_projection_is_the_read_calls_times_the_gap(self):
        args = ('--start', '0x0000', '--len', '0x0800', '--gap-ms', '6')
        _, ec, _, _ = run_watch(*args, clock=FakeTime())
        # `RecordingEc` holds one sweep, so this is the count the banner
        # projects from rather than a figure the test made up.
        self.assertTrue(ec.reads)
        self.assertAlmostEqual(self.banner_seconds(*args),
                               len(ec.reads) * 6 / 1000, places=1)

    def test_the_banner_counts_read_calls_and_not_addresses(self):
        args = ('--start', '0x0000', '--len', '0x0800', '--gap-ms', '6',
                '--block')
        _, ec, _, _ = run_watch(*args, clock=FakeTime())
        # Two calls into the driver for the same range the byte path reads
        # 2032 times. The gap is paid per call -- a `readmany` issues one
        # IOCTL per four bytes without coming back here, so 508 of them fall
        # under the two gaps -- so the banner has to quote calls or it quotes
        # the byte path's cost for a `--block` sweep, which is a thousand times
        # the time actually spent. It is also why --block is not the paced
        # path and this one is.
        self.assertEqual(len(ec.blocks), 2)
        self.assertAlmostEqual(self.banner_seconds(*args), 2 * 6 / 1000,
                               places=1)

    def test_the_banner_names_the_reads_and_the_gap_it_used(self):
        _, _, out, _ = run_watch('--start', '0x0700', '--len', '0x4',
                                 '--gap-ms', '12.5')
        self.assertIn('4 read call(s) per sweep', out)
        self.assertIn('12.5 ms apart', out)

    def test_the_notice_says_how_many_addresses_were_left_out(self):
        _, _, out, _ = run_watch('--start', '0x0000', '--len', '0x0800',
                                 '--gap-ms', '0')
        notice = [ln for ln in out.splitlines() if 'left out' in ln]
        self.assertEqual(len(notice), 1)
        self.assertIn('16 of this range', notice[0])

    def test_the_baseline_byte_count_is_what_is_swept(self):
        # The range is 2048 bytes and the page is 16 of them, so a baseline
        # still quoting the range would be quoting a sweep that does not
        # happen.
        _, _, out, _ = run_watch('--start', '0x0000', '--len', '0x0800',
                                 '--gap-ms', '0')
        self.assertIn('(2032 bytes)', out)


if __name__ == '__main__':
    unittest.main()