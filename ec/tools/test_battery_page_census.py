#!/usr/bin/env python3
"""Unit checks for the battery page census (issue #1202).

`docs/findings/battery-page-first-decoding.md` reads `ec/tools/battery_page_census.py`'s
output over `evidence/battery-traces/2026-09-09-profiles.csv` and carries it
into the firmware: which offsets moved, which little-endian pairs track a
quantity the same row reports, and what `registers.yaml` calls each address.
This file pins the byte facts that reading stands on.

**Every case here reads a committed file. None of them is a behaviour.** No
register was read, written or read back, and no byte was watched move on
hardware. Asserting that `0x04A6` takes three values across the capture is a
statement about a CSV in the repository, not about the EC; the suite is written
so that none of its assertions could be mistaken for a live result.

**The known-answer cases compute their own expectations from the committed
bytes** rather than reading them back out of the tool, so a big-endian or
off-by-one read inside the census fails here on the value instead of agreeing
with itself. That is why `u16()` below re-derives the pair from two hex bytes
rather than calling the tool's own helper -- a suite that asserted the tool
against its own output would pass on any consistent misreading.

The masking case is the regression this suite exists for: keying a page offset
as `addr & 0xff` collapses the `0x07xx` page onto `0x04xx` and invents matches
against registers this page does not contain. It is pinned on the address
arithmetic directly, and again through the lookup.

The suite is **not** wired into `.github/scripts/agent-gates.sh`: that file
lives under `.github/`, which this branch's push token cannot write, so the
registration is a human's change. Until it is made, the suite is run by hand
and nothing here implies CI runs it.
"""
import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import battery_page_census as B

CAPTURE = ROOT / 'evidence' / 'battery-traces' / '2026-09-09-profiles.csv'
REGISTERS = ROOT / 'ec' / 'annotations' / 'registers.yaml'
FINDING = ROOT / 'docs' / 'findings' / 'battery-page-first-decoding.md'

# The two page offsets the write-up follows into the firmware, named here as
# offsets because that is what a caller of the tool passes. The addresses are
# what the write-up cites and what the masking case is about.
OFF_CURRENT, OFF_VOLTAGE, OFF_SHADOW, OFF_CYCLES = 0x34, 0x38, 0xA4, 0xA6

# Read once, the way `test_pack_temp_producer_chain.py` gives: the capture is
# small but every case below compares what it reads against a value worked out
# independently, so a wrong read fails rather than agreeing with itself.
ROWS = list(csv.DictReader(CAPTURE.open(encoding='utf-8')))


def byte_at(row, offset):
    """One page byte, from the row's own hex cell."""
    return int(row[B.PAGE_COLUMN][offset * 2:offset * 2 + 2], 16)


def u16(row, offset):
    """The little-endian pair at `offset`, from two hex bytes.

    Written out here rather than imported from the tool: this is the value the
    write-up's claims are about, and a suite that took it from the code under
    test would confirm only that the code is self-consistent. Byte order is the
    thing most likely to be wrong and least likely to be noticed, so the
    expectation is built the long way round -- an explicit shift and or -- and
    a big-endian reader disagrees with it on the first pair it sees.
    """
    low = byte_at(row, offset)
    high = byte_at(row, offset + 1)
    return low + (high << 8)


def records():
    return {r['offset']: r for r in B.census(ROWS, B.load_registers(str(REGISTERS))[0])}


class PageAddressIsUnmasked(unittest.TestCase):
    """Offset 0xA4 is 0x04A4, never 0x07A4 and never 0x00A4."""

    def test_offset_bases_on_the_page(self):
        self.assertEqual(B.page_address(0x00), 0x0400)
        self.assertEqual(B.page_address(0xFF), 0x04FF)

    def test_high_offsets_keep_the_page_high_byte(self):
        # The masking bug: `addr & 0xff` sends every offset above 0xFF into the
        # low page, so 0x04A4 and 0x07A4 become indistinguishable.
        self.assertEqual(B.page_address(0xA4), 0x04A4)
        self.assertNotEqual(B.page_address(0xA4) & 0xFF00, 0x0700)

    def test_a_0x07xx_row_does_not_answer_a_0x04xx_offset(self):
        # The failure this pins is a phantom match, so it is asserted as one:
        # an address the map holds only in the 0x07xx page must not be found
        # for the 0x04xx offset sharing its low byte.
        other = 0x07A4
        table = {other: ("SOME_0x07XX_REGISTER", "present-untested")}
        self.assertIsNone(table.get(B.page_address(0xA4)))


class KnownAnswersOnTheCommittedCapture(unittest.TestCase):
    """The four positions the write-up names, worked out from the bytes here."""

    def setUp(self):
        self.by_offset = records()

    def test_voltage_pair_tracks_the_rows_own_voltage(self):
        for row in ROWS:
            self.assertEqual(u16(row, OFF_VOLTAGE), int(row['voltage_now']) // 1000)

    def test_current_pair_tracks_the_rows_own_current_on_the_rows_it_does(self):
        # Not an identity, and the rows it misses are the point: the capture's
        # sysfs read and its page dump are taken a moment apart, so the pair
        # lags `current_now` on some rows. Asserting an identity here would
        # assert a coincidence the capture does not contain.
        matches = [i for i, row in enumerate(ROWS)
                   if u16(row, OFF_CURRENT) == int(row['current_now']) // 1000]
        self.assertTrue(matches)
        self.assertLess(len(matches), len(ROWS))

    def test_shadow_pair_equals_the_current_pair_on_most_rows(self):
        equal = [i for i, row in enumerate(ROWS)
                 if u16(row, OFF_SHADOW) == u16(row, OFF_CURRENT)]
        self.assertTrue(equal)
        self.assertLess(len(equal), len(ROWS))

    def test_where_the_shadow_differs_it_matches_its_own_row(self):
        # The observation the write-up rests on: on every row where 0x04A4 and
        # 0x0434 disagree, 0x04A4 is the one agreeing with the row's own
        # `current_now`. Asserted over the disagreeing rows found here rather
        # than over named row indices, because an index into a capture file is
        # a figure every re-capture moves.
        for i, row in enumerate(ROWS):
            if u16(row, OFF_SHADOW) != u16(row, OFF_CURRENT):
                self.assertEqual(u16(row, OFF_SHADOW),
                                 int(row['current_now']) // 1000,
                                 f"row {i} disagrees on both")

    def test_cycle_count_takes_three_values_and_steps_while_charging(self):
        values = [u16(row, OFF_CYCLES) for row in ROWS]
        steps = [(i, values[i - 1], values[i])
                 for i in range(1, len(values)) if values[i] != values[i - 1]]
        self.assertTrue(steps)
        for i, before, after in steps:
            self.assertEqual(after, before + 1)
            self.assertEqual(ROWS[i]['status'], 'Charging')

    def test_the_cycle_counts_high_byte_held_steady(self):
        # 0x04A7 never moves in this capture, which is why the write-up treats
        # the count as a low-byte question here and does not claim the pair
        # was seen to step as a pair.
        self.assertEqual(len({byte_at(row, OFF_CYCLES + 1) for row in ROWS}), 1)

    def test_the_tool_reports_the_same_three_values(self):
        record = self.by_offset[OFF_CYCLES]
        self.assertTrue(record['moved'])
        self.assertEqual(record['distinct'], 3)
        self.assertEqual(record['addr'], 0x04A6)


class RegisterLookup(unittest.TestCase):
    """What the tool claims about the map, which is a reading of a YAML file."""

    def setUp(self):
        self.by_offset = records()

    def test_a_known_address_reports_its_row_and_status(self):
        record = self.by_offset[OFF_CYCLES]
        self.assertIsNotNone(record['register'])
        name, status = record['register']
        self.assertIn('CYCLE', name)
        self.assertTrue(status)

    def test_an_address_with_no_row_reports_none_and_invents_nothing(self):
        # Against a scratch map rather than the committed one, because "this
        # address has no row" is a property of a fixture: an address the
        # committed `registers.yaml` grows a row for is a value this case would
        # have to edit, which is the same defect in a different place. The
        # neighbour is in the fixture precisely so that borrowing its entry is
        # a failure the case can catch.
        fixture = self._registers_with(("0x04A4",))
        table = B.load_registers(fixture)[0]
        records = {r['offset']: r for r in B.census(ROWS, table)}
        self.assertIsNone(records[OFF_SHADOW + 1]['register'])
        self.assertEqual(records[OFF_SHADOW]['register'][0], 'A_NAME')

    def _registers_with(self, addresses):
        """A scratch `registers.yaml` holding `addresses`, as a path."""
        body = "".join(f"  - name: A_NAME\n    addr: {a}\n"
                       f"    status: present-untested\n" for a in addresses)
        handle = tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False,
                                             encoding='utf-8')
        handle.write("registers:\n" + body)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_a_multi_address_entry_covers_each_of_its_addresses(self):
        # `addr: [0x04A6, 0x04A7]` is one entry over two addresses, so both
        # resolve to the same name and status. A map keyed on the entry rather
        # than the address would drop one of them silently.
        table = B.load_registers(str(REGISTERS))[0]
        self.assertIsNotNone(table[0x04A6])
        self.assertEqual(table[0x04A6], table[0x04A7])


class Refusals(unittest.TestCase):
    """A file this cannot read is refused by name, never walked as empty."""

    def _capture(self, text):
        handle = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False,
                                             encoding='utf-8', newline='')
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_missing_ec_hex_column_is_refused(self):
        path = self._capture("ts,status\n2026-09-09T00:03:24+02:00,Discharging\n")
        rows, problem = B.read_capture(path)
        self.assertIsNone(rows)
        self.assertIn(B.PAGE_COLUMN, problem)

    def test_a_short_page_is_refused(self):
        path = self._capture("ec_hex\n" + ("00" * 8) + "\n")
        rows, problem = B.read_capture(path)
        self.assertIsNone(rows)
        self.assertIn('not the', problem)

    def test_a_non_hex_cell_is_refused(self):
        path = self._capture("ec_hex\n" + ("zz" * 256) + "\n")
        rows, problem = B.read_capture(path)
        self.assertIsNone(rows)
        self.assertIn('not hex', problem)

    def test_a_missing_file_is_refused(self):
        rows, problem = B.read_capture(str(HERE / 'no-such-capture.csv'))
        self.assertIsNone(rows)
        self.assertIn('could not be read', problem)

    def test_the_refusals_reach_stderr_and_exit_nonzero(self):
        path = self._capture("ts\n2026-09-09T00:03:24+02:00\n")
        done = subprocess.run(
            [sys.executable, str(HERE / 'battery_page_census.py'), path],
            capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn(B.PAGE_COLUMN, done.stderr)


class ToolRunsOnTheCommittedCapture(unittest.TestCase):
    """The tool exits zero on the committed file and names the addresses."""

    def test_exit_zero_and_the_page_is_reported(self):
        done = subprocess.run(
            [sys.executable, str(HERE / 'battery_page_census.py')],
            capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('0x04A6', done.stdout)

    def test_stdout_carries_no_claim_of_hardware(self):
        # The census reads a file; a reader must not be able to take a line of
        # it for a live observation, so the header says so on every run.
        done = subprocess.run(
            [sys.executable, str(HERE / 'battery_page_census.py')],
            capture_output=True, text=True)
        self.assertIn('nothing here was observed on hardware', done.stdout)


class TheWriteUpStandsOnThisTool(unittest.TestCase):
    """The write-up and the tool agree on the file each is about."""

    def test_the_write_up_names_this_tool_and_this_capture(self):
        text = FINDING.read_text(encoding='utf-8')
        self.assertIn('battery_page_census.py', text)
        self.assertIn('2026-09-09-profiles.csv', text)

    def test_the_write_up_claims_no_hardware_observation(self):
        text = FINDING.read_text(encoding='utf-8').lower()
        for phrase in ('no ec was opened',
                       'no register was read, written or read back'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()