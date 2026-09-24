#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

ec_watch.py imports ecrw, which binds kernel32 at import time and so only
loads on Windows -- ecrw_fake.py stands in for the whole module, and the
FakeEc below scripts the sweep byte by byte on top of it.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import ecrw_fake

ADDRS = [0x0700, 0x0701, 0x0702, 0x0703]

# Sweep 0 is the baseline ec_watch takes before its loop; 1 and 2 each move a
# different byte, and the mark is forced to land between them.
SWEEPS = [
    {0x0700: 0x00, 0x0701: 0x00, 0x0702: 0x00, 0x0703: 0x00},
    {0x0700: 0x00, 0x0701: 0x11, 0x0702: 0x00, 0x0703: 0x00},
    {0x0700: 0x00, 0x0701: 0x11, 0x0702: 0x22, 0x0703: 0x00},
]


class FakeEc:
    """Returns SWEEPS[n] for sweep n, and stops the run after the last one.

    The two events pin the interleaving: without them "did the MARK row land
    between the two change rows" would be a race against the sweep timer, and
    the test would pass on a build where marks never reach the CSV at all.

    `readmany` is the --block path's, and it is a whole sweep rather than four
    bytes: ADDRS is one aligned block, so a real readmany of it is exactly one
    IOCTL and this stands in for that. `blocks` is the recording that makes
    "one IOCTL per sweep" checkable rather than asserted.
    """

    def __init__(self):
        self.at_last_sweep = threading.Event()
        self.marked = threading.Event()
        self.blocks = []
        self._reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def read(self, addr):
        sweep, offset = divmod(self._reads, len(ADDRS))
        if sweep == len(SWEEPS) - 1 and offset == 0:
            self.at_last_sweep.set()
            self.marked.wait(5)
        if sweep >= len(SWEEPS):
            raise KeyboardInterrupt
        self._reads += 1
        # The .get is for the --block cases' ranges, which are not ADDRS: an
        # address the script does not name reads as 0x00 rather than raising,
        # so a case can put its range on the fan-tach page and still run.
        return SWEEPS[sweep].get(addr, 0x00)

    def readmany(self, start, length):
        self.blocks.append((start, length))
        return {addr: self.read(addr) for addr in range(start, start + length)}


class FakeStdin:
    """One mark, stamped once the sweep loop reaches the last sweep.

    The second readline() is the proof the mark is fully committed -- Marker
    only asks for another line after writing the previous one -- so that is
    where the sweep loop is released.
    """

    def __init__(self, ec, label):
        self._ec = ec
        self._label = label
        self._sent = False

    def readline(self):
        self._ec.at_last_sweep.wait(5)
        if not self._sent:
            self._sent = True
            return self._label + "\n"
        self._ec.marked.set()
        return ""


ecrw_fake.install()

spec = importlib.util.spec_from_file_location(
    'ec_watch', Path(__file__).with_name('ec_watch.py'))
ec_watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ec_watch)


class MarkCsvTests(unittest.TestCase):
    def run_watch(self, *extra):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 patch.object(ec_watch.sys, 'stdin', FakeStdin(ec, 'wrote 0x0751=0xA0')), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                    '--interval', '0', '--csv', str(out),
                                    *extra])
            return rc, out.read_text().splitlines()

    def test_mark_lands_in_the_csv_between_the_change_rows(self):
        rc, rows = self.run_watch('--mark')
        self.assertEqual(rc, 0)
        self.assertEqual(rows[0], 'ts,addr,old,new')
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         ['0x0701,0x00,0x11',
                          'MARK,,wrote 0x0751=0xA0',
                          '0x0702,0x00,0x22'])

    def test_mark_row_parses_as_the_grader_expects(self):
        _, rows = self.run_watch('--mark')
        mark = [r for r in rows if ',MARK,' in r][0]
        ts, addr, old, label = mark.split(',')
        self.assertEqual((addr, old, label), ('MARK', '', 'wrote 0x0751=0xA0'))
        # The grader keys every window off this timestamp.
        self.assertTrue(ts.startswith('20'))

    def test_without_mark_the_csv_holds_changes_only(self):
        ec = FakeEc()
        ec.marked.set()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            with patch.object(ec_watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(io.StringIO()):
                ec_watch.main(['--start', '0x0700', '--len', '0x4',
                               '--interval', '0', '--csv', str(out)])
            rows = out.read_text().splitlines()
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         ['0x0701,0x00,0x11', '0x0702,0x00,0x22'])


class BlockPathTests(unittest.TestCase):
    """--block: opt-in, off the per-byte path, and loud about the fan-tach page.

    Every case here runs the real `ec_watch.main` against the FakeEc above, so
    what is under test is which method the tool calls, not a reimplementation
    of the decision.
    """

    def run_watch(self, *argv):
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with patch.object(ec_watch, 'Ec', lambda: ec), \
             contextlib.redirect_stdout(out):
            rc = ec_watch.main(['--start', '0x0700', '--len', '0x4',
                                '--interval', '0', *argv])
        return rc, ec, out.getvalue()

    def test_the_flag_is_opt_in(self):
        # The default has to be the per-byte path: this is what says the block
        # path is an addition rather than a replacement, and it is the run the
        # committed captures were taken with.
        _, ec, out = self.run_watch()
        self.assertEqual(ec.blocks, [])
        self.assertNotIn("--block:", out)

    def test_block_sweeps_through_readmany(self):
        rc, ec, _ = self.run_watch('--block')
        self.assertEqual(rc, 0)
        # The whole four-byte range in one call. The first is the baseline and
        # the last is the sweep the fake cuts the run off in, so the run's
        # length stays the fake's business and not this case's.
        self.assertEqual(set(ec.blocks), {(0x0700, 0x4)})
        self.assertEqual(ec.blocks[0], (0x0700, 0x4))

    def test_the_banner_says_which_path_and_that_it_is_unverified(self):
        _, ec, out = self.run_watch('--block')
        # The operator is being asked to trust a path that has never met the
        # driver, so the banner has to say that where it is read rather than
        # leaving it to a help page nobody opens.
        self.assertIn("4 bytes per IOCTL (MMRD) instead of 1 (ECRR)", out)
        self.assertIn("never been run against the driver", out)
        self.assertIn("not a safety improvement", out)
        # And the sweep behind it is still the one IOCTL for four bytes.
        self.assertEqual(set(ec.blocks), {(0x0700, 0x4)})

    def test_a_block_sweep_reports_the_same_changes(self):
        _, ec, out = self.run_watch('--block')
        self.assertIn("0x0701: 0x00 -> 0x11", out)
        self.assertIn("0x0702: 0x00 -> 0x22", out)

    def test_the_fan_tach_warning_names_the_issue_and_the_page(self):
        # 0x0460-0x046F stalled the fans on a sibling board through ECRR
        # (#94). A 4-byte read that covers the page is a different access
        # shape, not a smaller one, so the warning has to say so rather than
        # let "fewer IOCTLs" read as "safer".
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with patch.object(ec_watch, 'Ec', lambda: ec), \
             contextlib.redirect_stdout(out):
            ec_watch.main(['--start', '0x0460', '--len', '0x4',
                           '--interval', '0', '--block'])
        text = out.getvalue()
        self.assertIn("0x0460-0x046F", text)
        self.assertIn("#94", text)
        self.assertIn("not a safer one", text)
        # No refusal: the run happened, and the warning did not stop it.
        self.assertEqual(set(ec.blocks), {(0x0460, 0x4)})

    def test_a_range_off_the_page_is_not_warned_about(self):
        _, ec, out = self.run_watch('--block')
        self.assertNotIn("#94", out)
        self.assertNotIn("0x0460-0x046F", out)

    def test_the_default_range_contains_the_page_so_the_warning_is_the_point(self):
        # 0x0000-0x07FF is this tool's default, and 0x0460-0x046F is inside it.
        # Pinned because the warning is otherwise easy to "fix" by narrowing a
        # default nobody asked to narrow.
        self.assertTrue(set(range(0x0000, 0x0800)) & set(ec_watch.FAN_TACH))


if __name__ == '__main__':
    unittest.main()
