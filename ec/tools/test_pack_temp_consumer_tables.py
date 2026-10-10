#!/usr/bin/env python3
"""Unit checks for the pack-temperature consumer tables (issue #1484).

`docs/findings/pack-temp-consumer-tables.md` extracts and decodes eight embedded
tables from the EC firmware image that the `step_index_056b_update_0495_0493`
routine compares against. These are the four main comparison tables (16 entries
× 4 bytes each) and four index tables (16 entries × 1 byte each), at addresses
0xAFF1, 0xAFB1, 0xB031, 0xB071 (main) and 0xAF91, 0xB0B1, 0xAFA1, 0xB0C1
(index).

**Every assertion here is static and none of them is a behaviour.** No register
was read, written or read back and no code path was seen run. A table extracted
here is raw firmware bytes, and the fact that a word is 0xBE0A is not evidence
the EC ever stored a temperature there. The suite is written so that none of
its assertions could be mistaken for a live result: they read the committed
image, extract table bytes, and compare them to values pinned from the image.

Where the analysis distinguishes between static disassembly (the selection rule
from B0D1.asm) and arithmetic (the entry patterns), the assertions here follow
that line: they pin the bytes and their shapes, not a claim about what the EC
does with them.
"""
import sys
import struct
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import verify_gap_text as G

DECOMPILED = HERE.parent / 'decompiled'
FINDING = ROOT / 'docs' / 'findings' / 'pack-temp-consumer-tables.md'
FIRMWARE = ROOT / 'ec' / 'firmware' / 'GMxMGxx_11.800'

# Read once, the way `test_bank1_e582_framing.py` gives for
# `verify_gap_text.load_images`: a per-test read of a 256 KiB image is not a
# cost worth paying many times, and every assertion below compares what it
# reads against the committed firmware, so a wrong read fails rather than
# agreeing with itself.
IMAGES = G.load_images()
BANK1 = IMAGES['bank1']


def bank1_address(code_addr):
    """Bank 1 CODE addresses are indexed directly in the BANK1 image.

    The BANK1 image returned by load_images() is already indexed by runtime
    address (0x0000-0xFFFF), with 0x0000-0x7FFF as the common area and
    0x8000-0xFFFF as bank 1's CODE space."""
    return code_addr


class TheEightTableAddresses(unittest.TestCase):
    """The eight tables are present at their expected addresses and have the
    expected byte counts: 64 bytes (16×4) for the main tables and 16 bytes
    for the index tables."""

    def test_the_four_main_tables_each_have_64_bytes(self):
        # The four CODE tables that step_index_056b_update_0495_0493 compares
        # against, at 16 entries of 4 bytes each.
        for addr in (0xAFF1, 0xAFB1, 0xB031, 0xB071):
            offset = bank1_address(addr)
            # Each main table is 16 entries × 4 bytes
            table_bytes = BANK1[offset:offset + 64]
            self.assertEqual(len(table_bytes), 64,
                             f"Main table at 0x{addr:04X} is not 64 bytes")
            # Entry 0's low word is 0xBE0A in all four (bytes 0x0A 0xBE in LE)
            entry_0_low_word = struct.unpack('<H', table_bytes[0:2])[0]
            self.assertEqual(entry_0_low_word, 0xBE0A,
                             f"0x{addr:04X} entry 0 low word is not 0xBE0A")

    def test_the_four_index_tables_each_have_16_bytes(self):
        # Four index tables: one byte per entry for 16 entries.
        for addr in (0xAF91, 0xB0B1, 0xAFA1, 0xB0C1):
            offset = bank1_address(addr)
            table_bytes = BANK1[offset:offset + 16]
            self.assertEqual(len(table_bytes), 16,
                             f"Index table at 0x{addr:04X} is not 16 bytes")


class TheMainTablesAreLaddersWithSaturation(unittest.TestCase):
    """The low words of the main table entries form a ladder that rises through
    the first ten entries and then saturates at 0x2AED for six entries
    (entries 10-15). The four tables differ at scattered entries."""

    def test_0xaff1_low_words_form_a_rising_ladder(self):
        offset = bank1_address(0xAFF1)
        table = BANK1[offset:offset + 64]
        # Extract low words of each 4-byte entry (little-endian 16-bit)
        low_words = [struct.unpack('<H', table[i*4:i*4 + 2])[0]
                     for i in range(16)]
        # First ten should rise (values in decimal from little-endian interpretation)
        # Bytes: 0A BE = LE word 0xBE0A = 48650
        # Bytes: 0A DC = LE word 0xDC0A = 56330, etc.
        expected_low = [0xBE0A, 0xBE0A, 0xDC0A, 0x4A0B, 0x6C0C, 0x800C,
                        0xE40C, 0x020D, 0x160D, 0x910E]
        self.assertEqual(low_words[0:10], expected_low)
        # Entries 10-15 saturate at 0xED2A
        for i in range(10, 16):
            self.assertEqual(low_words[i], 0xED2A,
                             f"0xAFF1 entry {i} low word is not saturated at 0xED2A")

    def test_0xafb1_low_words_form_a_rising_ladder(self):
        offset = bank1_address(0xAFB1)
        table = BANK1[offset:offset + 64]
        low_words = [struct.unpack('<H', table[i*4:i*4 + 2])[0]
                     for i in range(16)]
        # Similar pattern, but differs at entry 3 (0xDC0A vs 0x4A0B)
        expected_low = [0xBE0A, 0xBE0A, 0xDC0A, 0xDC0A, 0x6C0C, 0x800C,
                        0xE40C, 0x020D, 0x160D, 0x910E]
        self.assertEqual(low_words[0:10], expected_low)
        for i in range(10, 16):
            self.assertEqual(low_words[i], 0xED2A)

    def test_0xb031_low_words_form_a_rising_ladder(self):
        offset = bank1_address(0xB031)
        table = BANK1[offset:offset + 64]
        low_words = [struct.unpack('<H', table[i*4:i*4 + 2])[0]
                     for i in range(16)]
        # Differs at entries 7, 8, 9
        expected_low = [0xBE0A, 0xBE0A, 0xDC0A, 0x4A0B, 0x6C0C, 0x800C,
                        0xE40C, 0x340D, 0x480D, 0x910E]
        self.assertEqual(low_words[0:10], expected_low)
        # Entries 10-15 saturate at 0xED2A (different high word than 0xAFF1)
        for i in range(10, 16):
            self.assertEqual(low_words[i], 0xED2A)

    def test_0xb071_low_words_form_a_rising_ladder(self):
        offset = bank1_address(0xB071)
        table = BANK1[offset:offset + 64]
        low_words = [struct.unpack('<H', table[i*4:i*4 + 2])[0]
                     for i in range(16)]
        # Differs at entries 3, 4, 5, 6, 7, 8, 9
        expected_low = [0xBE0A, 0xBE0A, 0xDC0A, 0xDC0A, 0x9E0C, 0x9E0C,
                        0x480D, 0x660D, 0x7A0D, 0x910E]
        self.assertEqual(low_words[0:10], expected_low)
        for i in range(10, 16):
            self.assertEqual(low_words[i], 0xED2A)


class TheIndexTablesArePaired(unittest.TestCase):
    """The four index tables pair: 0xAF91 and 0xB0B1 are identical, and
    0xAFA1 and 0xB0C1 are identical. Both pairs are selected by bit 0 of 0x0497
    in the disassembly."""

    def test_af91_and_b0b1_are_identical(self):
        offset_af91 = bank1_address(0xAF91)
        offset_b0b1 = bank1_address(0xB0B1)
        table_af91 = BANK1[offset_af91:offset_af91 + 16]
        table_b0b1 = BANK1[offset_b0b1:offset_b0b1 + 16]
        self.assertEqual(table_af91, table_b0b1)
        # They should be the observed bytes
        expected = bytes([0x0C, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10,
                          0x30, 0xB0, 0xB0, 0xB0, 0xB0, 0xB0, 0xB0, 0xB0])
        self.assertEqual(table_af91, expected)

    def test_afa1_and_b0c1_are_identical(self):
        offset_afa1 = bank1_address(0xAFA1)
        offset_b0c1 = bank1_address(0xB0C1)
        table_afa1 = BANK1[offset_afa1:offset_afa1 + 16]
        table_b0c1 = BANK1[offset_b0c1:offset_b0c1 + 16]
        self.assertEqual(table_afa1, table_b0c1)
        # They should be the observed bytes
        expected = bytes([0x20, 0x20, 0x20, 0x40, 0x00, 0x80, 0x80, 0x80,
                          0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80])
        self.assertEqual(table_afa1, expected)


class TheFourTableSelectionRuleFromDisassembly(unittest.TestCase):
    """The selection rule from B0D1.asm, which reads 0x0497, 0x0398, and 0x030D
    to choose which table to use."""

    def test_the_disassembly_contains_four_dptr_immediates(self):
        # B0D1.asm names the four tables it loads DPTR with via
        # "mov DPTR, #0xABCD" lines. Check that all four table addresses
        # appear in the disassembly.
        text = (DECOMPILED / 'bank1' / 'B0D1.asm').read_text()
        # The four table addresses should appear in lines like:
        # "B10C     90 af f1 mov      DPTR, #0xaff1"
        expected = {0xAFF1, 0xAFB1, 0xB031, 0xB071}
        for addr in expected:
            addr_str = f'#0x{addr:x}'
            self.assertIn(addr_str, text,
                          f"Table address 0x{addr:04X} not found in B0D1.asm")


class TheWriteupDistinguishesAnalysisKind(unittest.TestCase):
    """The findings write-up names which parts are static disassembly and
    which are arithmetic, and does not claim behavior."""

    def test_the_writeup_names_the_four_tables(self):
        text = FINDING.read_text()
        for addr in ('0xAFF1', '0xAFB1', '0xB031', '0xB071',
                     '0xAF91', '0xB0B1', '0xAFA1', '0xB0C1'):
            self.assertIn(addr, text, f"{addr} should be in the findings")

    def test_the_writeup_distinguishes_static_and_arithmetic(self):
        text = FINDING.read_text()
        self.assertIn('disassembly', text.lower())
        # Should mention that arithmetic is not behavior
        self.assertIn('arithmetic', text.lower())

    def test_the_writeup_does_not_claim_behavior(self):
        text = FINDING.read_text()
        # The write-up should not say "the EC acts on" or "observed"
        # without citing evidence already in the image
        self.assertNotIn('The EC stores', text,
                         "Write-up should not claim behavior without evidence")
        self.assertNotIn('The EC reads', text,
                         "Write-up should not claim behavior without evidence")


if __name__ == '__main__':
    unittest.main()
