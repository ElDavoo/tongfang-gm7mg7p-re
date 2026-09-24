#!/usr/bin/env python3
"""Offline checks; no EC is opened and the vendor driver is never called.

gpu_block_watch.py imports ecrw, which binds kernel32 at import time and so
only loads on Windows -- windows/tools/ecrw_fake.py stands in for the whole
module, installed by assignment, so this suite is not a party to the
`setdefault` ordering accident docs/findings.md §16 records. The fake also makes
the sweep scriptable byte by byte.

Unlike most of the `windows/tools` suites this one reads committed inputs,
`evidence/acpi/dsdt.dsl` and `ec/annotations/registers.yaml`, resolved relative
to this file. It therefore has to run from inside the repository, which
`tools/run-tests.sh` guarantees (it cds to the repo root), and a suite copied
to a scratch directory outside the tree will fail to find them.

The first two classes are the ones that matter: the tool's watch table is the
citation list docs/hardware-tests/gpu-tgp-07c4-07d7-door.md §7 is graded
against, so it is checked here against the two committed inputs it transcribes
-- the DSDT ECMG field list and ec/annotations/registers.yaml -- rather than
being a hand-typed table nothing holds still.
"""
import contextlib
import importlib
import io
from pathlib import Path
import re
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import yaml

TOOLS = Path(__file__).parent
REPO = TOOLS.parent.parent
DSDT = REPO / "evidence" / "acpi" / "dsdt.dsl"
REGISTERS = REPO / "ec" / "annotations" / "registers.yaml"

# The tool's own `from ec_watch import ...` has to resolve, and the directory
# is the import root whether or not the runner was started from here.
sys.path.insert(0, str(TOOLS))


# The shared offline stand-in for `ecrw` (windows/tools/ecrw_fake.py), installed
# by assignment like the probe and ec_watch suites do, so this suite cannot lose
# -- or win -- a `setdefault` race against them. `Ec` only has to exist as a
# name: every run rebinds the tool's own copy.
import ecrw_fake  # noqa: E402  (needs the sys.path entry above)
ecrw_fake.install()

watch = importlib.import_module('gpu_block_watch')

# The watch set the change rows are keyed against, in the order a sweep reads
# them. Sweep 0 is the baseline the tool takes before its loop; 1 moves a byte
# in the 0x07C4 block and 2 a byte in the 0x0743 block, and the mark is forced
# to land between them -- one change from each window either side of it, which
# is the "both blocks, one capture" shape the procedure's result table reads.
ADDRS = [a for a, *_ in watch.WATCH]
ACPI, HOST = 0x07D0, 0x0745
SWEEPS = [
    dict.fromkeys(ADDRS, 0x00),
    {**dict.fromkeys(ADDRS, 0x00), ACPI: 0x37},
    {**dict.fromkeys(ADDRS, 0x00), ACPI: 0x37, HOST: 0x0A},
]


def parse_ecmg_fields(text):
    """The ECMG field list as {addr: [(name, first_bit, last_bit)]}.

    Translated out of the ASL rather than transcribed: an `Offset (0xNNN)`
    restarts the bit count at that byte, and every following `Name, width`
    (or unnamed `, width`) takes the next `width` bits of it. One Offset
    group spans as many bytes as its fields add up to, so each field is
    filed under every byte it covers -- a 16-bit field names each half, and
    the two windows this tool watches hold no field wider than a byte.
    """
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines)
                 if l.strip().startswith("Field (ECMG"))
    out, addr, bit = {}, None, 0
    for line in lines[start + 1:]:
        line = line.split("//")[0].strip()
        if line == "}":
            break
        m = re.fullmatch(r"Offset \((0x[0-9A-Fa-f]+)\),\s*", line)
        if m:
            addr, bit = int(m.group(1), 16), 0
            continue
        m = re.fullmatch(r"([A-Za-z0-9_]*)\s*,\s*(\d+),\s*", line)
        if m and addr is not None:
            name, width = m.group(1), int(m.group(2))
            if name:
                lo, hi = bit, bit + width - 1
                for b in range(lo // 8, hi // 8 + 1):
                    out.setdefault(addr + b, []).append(
                        (name, max(lo, b * 8) % 8, min(hi, b * 8 + 7) % 8))
            bit += width
    return out


def field_list_text(fields):
    """The tool's spelling of one byte's fields, formatted from the DSDT.

    An 8-bit field is its name alone and a sub-byte field carries its bit or
    bit span -- the tool's column, not a restatement of the ASL's order.
    """
    if not fields:
        return "(no DSDT field)"
    parts = []
    for name, lo, hi in fields:
        if lo == 0 and hi == 7:
            parts.append(name)
        elif lo == hi:
            parts.append(f"{name} b{lo}")
        else:
            parts.append(f"{name} b{lo}-{hi}")
    return ", ".join(parts)


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

    def write(self, addr, val):
        # The tool has no write path. A run that reached this would be a
        # regression against docs/findings.md §4o, which is why the refusal
        # is here and not left to review.
        raise AssertionError(f"gpu_block_watch wrote 0x{addr:04X}=0x{val:02X}")


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


class CitationTableTests(unittest.TestCase):
    """The table is checked against the inputs it claims to transcribe."""

    @classmethod
    def setUpClass(cls):
        cls.fields = parse_ecmg_fields(DSDT.read_text(encoding="utf-8",
                                                      errors="replace"))
        cls.statuses = {}
        for r in yaml.safe_load(REGISTERS.read_text())["registers"]:
            addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
            for a in addrs:
                if isinstance(a, int):
                    cls.statuses.setdefault(a, r["status"])

    def test_the_dsdt_field_list_the_table_is_checked_against_was_parsed(self):
        # A parser that found nothing would make the check below vacuous, and
        # a vacuous drift test is the one thing worse than none. The two
        # offsets the tool watches are 60 entries apart, so reaching the
        # second of them is itself the proof the walk got past the first.
        self.assertIn(0x0743, self.fields)
        self.assertIn(0x07C4, self.fields)
        self.assertEqual(self.fields[0x07D0], [("DBD1", 0, 7)])
        self.assertEqual(self.fields[0x07D1], [("DBD2", 0, 7)])

    def test_every_dsdt_name_and_bit_matches_the_field_list(self):
        for addr, name, _, _ in watch.WATCH:
            self.assertEqual(name, field_list_text(self.fields.get(addr, [])),
                             f"0x{addr:04X}")

    def test_every_registers_yaml_status_is_verbatim(self):
        for addr, _, status, _ in watch.WATCH:
            expected = self.statuses.get(addr, watch.NO_ROW)
            self.assertEqual(status, expected, f"0x{addr:04X}")

    def test_no_row_is_never_spelled_as_absence(self):
        # docs/findings.md §4c retracted a "does not exist" reading of a
        # zero-reference scan, and the watch table is where that phrasing
        # would come back from: sixteen cells saying "no row" is sixteen
        # chances to be read back as sixteen claims of absence. Each one
        # here is checked to mean what it says, both ways.
        rows = {addr for addr, _, status, _ in watch.WATCH
                if status == watch.NO_ROW}
        self.assertTrue(rows)
        for addr, _, status, _ in watch.WATCH:
            if addr in rows:
                self.assertNotIn(addr, self.statuses, f"0x{addr:04X}")
            else:
                self.assertIn(addr, self.statuses, f"0x{addr:04X}")
        self.assertIn("registers.yaml", watch.NO_ROW)

    def test_every_citation_names_the_file_it_comes_from(self):
        for addr, _, _, cite in watch.WATCH:
            self.assertIn("dsdt.dsl:", cite, f"0x{addr:04X}")
            if self.statuses.get(addr):
                self.assertIn("registers.yaml", cite, f"0x{addr:04X}")

    def test_the_watch_set_is_the_two_windows_and_nothing_else(self):
        # The check that stops the tool quietly growing into a third
        # full-range 0x0700-0x07FF sweep, which is #94's problem to own.
        self.assertEqual(set(ADDRS), set(range(0x0743, 0x0747))
                         | set(range(0x07C4, 0x07D8)))
        self.assertEqual(len(ADDRS), 24)
        self.assertEqual(len(set(ADDRS)), len(ADDRS))
        # Every address falls in exactly one declared window, so a change line
        # always carries a tag and window_of() can never fall off the end.
        for a in ADDRS:
            covering = [label for label, s, e in watch.WINDOWS if s <= a <= e]
            self.assertEqual(covering, [watch.window_of(a)], f"0x{a:04X}")


class NamesOnlyTests(unittest.TestCase):
    def test_names_only_prints_the_table_and_opens_no_ec(self):
        out = io.StringIO()
        with patch.object(watch, 'Ec', lambda: self.fail("opened an EC")), \
             contextlib.redirect_stdout(out):
            rc = watch.main(['--names-only'])
        text = out.getvalue()
        self.assertEqual(rc, 0)
        for addr, name, status, cite in watch.WATCH:
            self.assertIn(f"0x{addr:04X}", text)
            self.assertIn(name, text)
            self.assertIn(status, text)
            self.assertIn(cite, text)
        self.assertIn("not about the address", text)

    def test_the_table_is_printed_before_a_run_starts_too(self):
        # A capture is evidence, and evidence that does not record what was
        # watched is a capture of nothing in particular.
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(out):
                watch.main(['--interval', '0', '--csv',
                            str(Path(tmp) / 'c.csv')])
        text = out.getvalue()
        for addr, name, _, cite in watch.WATCH:
            self.assertIn(f"0x{addr:04X}  {name}", text)
            self.assertIn(cite, text)
        self.assertIn("no interval here is validated", text)


class MarkCsvTests(unittest.TestCase):
    def run_watch(self, *extra):
        ec = FakeEc()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'capture.csv'
            with patch.object(watch, 'Ec', lambda: ec), \
                 patch.object(watch.sys, 'stdin',
                              FakeStdin(ec, 'gpu tgp 115W->130W')), \
                 contextlib.redirect_stdout(io.StringIO()):
                rc = watch.main(['--interval', '0', '--csv', str(out), *extra])
            return rc, out.read_text().splitlines()

    def test_mark_lands_in_the_csv_between_the_change_rows(self):
        rc, rows = self.run_watch('--mark')
        self.assertEqual(rc, 0)
        # ec_watch.py's schema exactly: a downstream reader of a mark-delimited
        # capture (issue #168) must not need a parser written for this file.
        self.assertEqual(rows[0], 'ts,addr,old,new')
        self.assertEqual([r.split(',', 1)[1] for r in rows[1:]],
                         [f'0x{ACPI:04X},0x00,0x37',
                          'MARK,,gpu tgp 115W->130W',
                          f'0x{HOST:04X},0x00,0x0A'])

    def test_both_windows_are_in_one_capture(self):
        _, rows = self.run_watch('--mark')
        addrs = [r.split(',', 1)[1].split(',')[0] for r in rows[1:]]
        self.assertIn(f"0x{ACPI:04X}", addrs)
        self.assertIn(f"0x{HOST:04X}", addrs)

    def test_the_summary_reports_both_windows_and_grades_neither(self):
        ec = FakeEc()
        ec.marked.set()
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(watch, 'Ec', lambda: ec), \
                 contextlib.redirect_stdout(out):
                watch.main(['--interval', '0', '--csv',
                            str(Path(tmp) / 'c.csv')])
        # The startup table prints the status column, so the grading words are
        # checked against the summary -- what the run concluded, not what it
        # was told to look at. A zero in a capture is "not moved by this
        # method under this action"; #168 owns the reading.
        summary = out.getvalue()[out.getvalue().index("=== "):]
        self.assertIn("window 0x07C4-0x07D7", summary)
        self.assertIn("window 0x0743-0x0746", summary)
        self.assertIn("not a verdict", summary)
        for word in ("absent", "confirmed-working", "confirmed-inert",
                     "unused", "unreferenced"):
            self.assertNotIn(word, summary)


if __name__ == '__main__':
    unittest.main()
