#!/usr/bin/env python3
"""Offline checks on `ec_watch.py`'s fan-page exclusion and its per-read gap.

`ec_watch.py` imports ecrw -- `ecrw_fake.py` stands in for the whole module,
installed by assignment so this file is not a party to the `setdefault`
ordering accident `docs/findings.md` §16 records. What sits on top of it here
is a scripted `Ec` that records every address it is asked for, because the
whole of what the exclusion is worth is *which* addresses a sweep reaches, and
a printed banner cannot show that.

Two things are pinned that a flag being accepted would not settle:

  * **the pacing, by a recorded `time.sleep`.** `--gap-ms` on the command line
    proves nothing about whether anything sleeps; the calls recorded here are
    the sleep calls the sweep actually made, and their count is the number of
    reads it made. `--interval 0` is forced below so the sweep-to-sweep sleep
    records as a zero and cannot be mistaken for the gap.
  * **the exclusion under `--block`, by the covered bytes.** `readmany` covers
    a run with the aligned blocks enclosing it and reads the bytes on both
    sides of what was asked for, so an exclusion that worked on the per-byte
    path and not here would still read the page without ever naming an address
    in it. What is asserted is the byte set, not the call count.

Nothing here opens an EC or a driver, and nothing here says anything about
what these reads do to a fan on the machine.
`docs/findings/ec-read-pacing-fan-page.md` is the write-up, and it is explicit
that 6 ms is a sibling board's figure and not one measured here.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import ecrw_fake

PAGE = set(range(0x0460, 0x0470))
DEFAULT_LEN = 0x0800


class ScriptedEc:
    """Records what a sweep asked for, then ends the run the way Ctrl-C does.

    `stop_after` counts reads rather than sweeps, so a case can say "one sweep
    of this range" without having to know how the range decomposes.

    A block run is recorded only when it was read whole. The alternative --
    recording the call and then stopping partway through it -- makes the block
    list a record of attempts rather than of accesses, and "one gap per run"
    cannot be asserted against a list holding a run that never happened.
    """

    def __init__(self, stop_after):
        self.reads = []
        self.blocks = []
        self._left = stop_after

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        if self._left <= 0:
            raise KeyboardInterrupt
        self._left -= 1
        self.reads.append(addr)
        return 0x00

    def readmany(self, start, length):
        if self._left < length:
            raise KeyboardInterrupt
        self.blocks.append((start, length))
        return {a: self.read(a) for a in range(start, start + length)}


def covered_by(blocks):
    """Every byte `blocks` reaches, enclosing overshoot included."""
    out = set()
    for start, length in blocks:
        out.update(range(start & ~3, ((start + length - 1) & ~3) + 4))
    return out


ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'ec_watch', Path(__file__).with_name('ec_watch.py'))
ec_watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec_watch)


class PacingTests(unittest.TestCase):
    """The two defaults, from the outside: which addresses, and how long."""

    def run_watch(self, stop_after, *argv):
        """One run, with every `time.sleep` recorded rather than taken."""
        ec = ScriptedEc(stop_after)
        out = io.StringIO()
        slept = []

        with patch.object(ec_watch, 'Ec', lambda: ec), \
             patch('time.sleep', slept.append), \
             contextlib.redirect_stdout(out):
            rc = ec_watch.main(['--interval', '0', *argv])
        return rc, ec, out.getvalue(), slept

    def gaps(self, slept):
        """The recorded sleeps that are not the sweep-to-sweep one.

        `--interval 0` is forced in `run_watch`, so a zero in the record is
        the sweep-to-sweep sleep and anything else is a gap.
        """
        return [s for s in slept if s != 0.0]

    # 1. The exclusion, on the per-byte path. The range is this tool's own
    #    default, so these are the bare invocation rather than a built one.
    def test_the_default_sweep_reads_no_fan_tach_byte(self):
        _, ec, out, _ = self.run_watch(DEFAULT_LEN - len(PAGE))
        self.assertEqual(set(ec.reads) & PAGE, set())
        self.assertEqual(len(ec.reads), DEFAULT_LEN - len(PAGE))
        self.assertIn("not reading 16 byte(s)", out)
        self.assertIn("0x0460-0x046F", out)
        self.assertIn("--include-fan-tach", out)

    def test_the_opt_in_reads_the_page(self):
        _, ec, out, _ = self.run_watch(DEFAULT_LEN, "--include-fan-tach")
        self.assertEqual(set(ec.reads) & PAGE, PAGE)
        self.assertEqual(len(ec.reads), DEFAULT_LEN)
        # And nothing says the page was skipped, because nothing was. A banner
        # that always names the page teaches an operator to read past it.
        self.assertNotIn("not reading", out)

    def test_a_range_inside_the_page_refuses_rather_than_reporting_a_baseline(self):
        # The failure this exists for: an empty sweep that prints a baseline
        # reads as "nothing moved", which is a result. A refusal naming the
        # opt-in is not.
        ec = ScriptedEc(len(PAGE))
        out = io.StringIO()
        with patch.object(ec_watch, 'Ec', lambda: ec), \
             patch('time.sleep', lambda s: None), \
             contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as caught:
                ec_watch.main(['--interval', '0',
                               '--start', '0x0460', '--len', '0x4'])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(ec.reads, [])
        self.assertEqual(out.getvalue(), "")

    def test_a_range_straddling_the_page_keeps_both_sides(self):
        # A range that covers the page and continues past it drops the middle
        # and keeps the rest: the exclusion is the page, not "give up on any
        # range that touches it".
        _, ec, _, _ = self.run_watch(0x20, "--start", "0x0450", "--len", "0x30")
        self.assertEqual(set(ec.reads) & PAGE, set())
        self.assertEqual(set(ec.reads),
                         set(range(0x0450, 0x0460)) | set(range(0x0470, 0x0480)))

    # 2. The exclusion under --block, which is the one that can read the page
    #    without naming an address in it.
    def test_no_block_byte_of_the_default_sweep_is_a_fan_tach_byte(self):
        _, ec, _, _ = self.run_watch(DEFAULT_LEN - len(PAGE), "--block")
        self.assertEqual(covered_by(ec.blocks) & PAGE, set())
        # The two runs the split produces, rather than the one the whole range
        # would have been: readmany's overshoot is what the split has to
        # survive, so the split itself is worth pinning.
        self.assertEqual(ec.blocks[0], (0x0000, 0x460))
        self.assertEqual(ec.blocks[1], (0x0470, 0x390))

    def test_the_block_opt_in_reads_the_page(self):
        _, ec, _, _ = self.run_watch(DEFAULT_LEN, "--block",
                                     "--include-fan-tach")
        self.assertEqual(covered_by(ec.blocks) & PAGE, PAGE)

    def test_a_block_range_straddling_the_page_does_not_read_it(self):
        _, ec, _, _ = self.run_watch(8, "--start", "0x0458", "--len", "0x10",
                                     "--block")
        self.assertEqual(covered_by(ec.blocks) & PAGE, set())
        # And the run it did issue is the one below the page alone: the split
        # is by address, so a run ending at 0x045F is covered by blocks that
        # end at 0x045F and not one block further.
        self.assertEqual(ec.blocks, [(0x0458, 0x8)])

    # 3. The gap. A flag the tool accepts is not a sleep it takes.
    NARROW = ("--start", "0x0700", "--len", "0x4")

    def test_the_default_gap_sleeps_after_every_read(self):
        _, ec, _, slept = self.run_watch(4, *self.NARROW)
        self.assertEqual(self.gaps(slept), [0.006] * 4)
        self.assertEqual(len(self.gaps(slept)), len(ec.reads))

    def test_the_gap_default_is_six_milliseconds(self):
        # Read off what the tool slept rather than off its argparse default:
        # the module's own default would be the same number by construction,
        # and would stay green if the sleep were dropped from `sweep`.
        _, _, _, slept = self.run_watch(4, *self.NARROW)
        self.assertEqual({round(s * 1000, 6) for s in self.gaps(slept)}, {6.0})

    def test_a_narrower_gap_reaches_the_sleep(self):
        _, _, _, slept = self.run_watch(4, *self.NARROW, "--gap-ms", "1.5")
        self.assertEqual(self.gaps(slept), [0.0015] * 4)

    def test_a_zero_gap_sleeps_between_reads_not_at_all(self):
        _, ec, _, slept = self.run_watch(4, *self.NARROW, "--gap-ms", "0")
        self.assertEqual(self.gaps(slept), [])
        self.assertEqual(len(ec.reads), 4)

    def test_the_block_path_sleeps_once_per_run(self):
        # One gap per `readmany`, not per IOCTL: a run covers four bytes and
        # the loop above it never sees the blocks inside. Pinned because it is
        # the granularity this path has, and a run count of zero would be a
        # sweep that paced itself not at all.
        _, ec, _, slept = self.run_watch(DEFAULT_LEN - len(PAGE), "--block")
        self.assertEqual(len(ec.blocks), 2)
        self.assertEqual(len(self.gaps(slept)), len(ec.blocks))

    # 4. The banner, which is where an operator is told rather than left to
    #    divide the gap by the address count.
    def test_the_banner_projects_the_sweep_time_from_the_reads_it_has(self):
        # The figure is three significant figures rather than one decimal
        # place, because a narrow range's projection is milliseconds and
        # `%.1f` printed that as `0.0s` -- a sweep that does sleep, told to
        # the operator as one that does not.
        _, _, out, _ = self.run_watch(4, *self.NARROW)
        self.assertIn("about 0.024s of sleeping per sweep over 4 reads", out)

    def test_the_banner_projects_the_time_a_wide_sweep_would_take(self):
        # The figure an operator planning a run needs, on the range they get
        # by default rather than on a constructed one.
        _, _, out, _ = self.run_watch(DEFAULT_LEN - len(PAGE), "--gap-ms", "10")
        reads = DEFAULT_LEN - len(PAGE)
        self.assertIn(f"about {reads * 10 / 1000:.3g}s of sleeping per sweep",
                      out)
        self.assertIn(f"over {reads} reads", out)

    def test_the_banner_says_which_path_the_gap_is_on(self):
        _, _, out, _ = self.run_watch(4, *self.NARROW)
        self.assertIn("--gap-ms 6 after every read", out)

    # 5. The banner under --block, where the projection and the sleeps have to
    #    agree about what a sweep is made of.
    def test_the_block_banner_projects_runs_not_addresses(self):
        # The banner used to print `len(addrs) * gap_ms` on both paths, which
        # overstated this one by the number of bytes a run covers -- 12.2 s
        # promised where the sweep takes two gaps. It is held here against the
        # sleeps the sweep actually took, not against a literal, so a figure
        # that drifts from the loop fails rather than a banner that drifts
        # from it.
        _, ec, out, slept = self.run_watch(DEFAULT_LEN - len(PAGE), "--block")
        gaps = self.gaps(slept)
        self.assertIn(f"about {sum(gaps):.3g}s of sleeping per sweep", out)
        self.assertIn(f"over {len(gaps)} runs", out)
        self.assertIn("--gap-ms 6 after every run", out)
        # And it is not the per-byte figure: 2032 addresses over two runs is
        # the whole of the disagreement this case exists for.
        self.assertNotIn(f"{len(ec.reads) * 0.006:.3g}s", out)

    def test_the_block_banner_agrees_with_the_per_byte_one_on_a_narrow_range(self):
        # A range the split leaves as a single run, so the two paths differ
        # only in how they got there -- and the banner has to follow the path.
        _, _, out, slept = self.run_watch(
            0x100, "--block", "--start", "0x0700", "--len", "0x100")
        gaps = self.gaps(slept)
        self.assertEqual(len(gaps), 1)
        self.assertIn("over 1 run.", out)
        self.assertIn(f"about {sum(gaps):.3g}s of sleeping per sweep", out)


if __name__ == '__main__':
    unittest.main()