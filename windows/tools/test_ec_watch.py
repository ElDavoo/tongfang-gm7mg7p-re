#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

ec_watch.py imports ecrw, which binds kernel32 at import time and so only
loads on Windows -- the fake below stands in for the whole module, which is
also what lets the sweep be scripted byte by byte.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

ADDRS = [0x0700, 0x0701, 0x0702, 0x0703]

# Sweep 0 is the baseline ec_watch takes before its loop; 1 and 2 each move a
# different byte, and the mark is forced to land between them.
SWEEPS = [
    {0x0700: 0x00, 0x0701: 0x00, 0x0702: 0x00, 0x0703: 0x00},
    {0x0700: 0x00, 0x0701: 0x11, 0x0702: 0x00, 0x0703: 0x00},
    {0x0700: 0x00, 0x0701: 0x11, 0x0702: 0x22, 0x0703: 0x00},
]


class FakeEcError(RuntimeError):
    pass


class FakeEc:
    """Returns SWEEPS[n] for sweep n, and stops the run after the last one.

    The two events pin the interleaving: without them "did the MARK row land
    between the two change rows" would be a race against the sweep timer, and
    the test would pass on a build where marks never reach the CSV at all.
    """

    def __init__(self):
        self.at_last_sweep = threading.Event()
        self.marked = threading.Event()
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
        return SWEEPS[sweep][addr]


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


fake_ecrw = types.ModuleType('ecrw')
fake_ecrw.Ec = FakeEc
fake_ecrw.EcError = FakeEcError
sys.modules.setdefault('ecrw', fake_ecrw)

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


if __name__ == '__main__':
    unittest.main()
