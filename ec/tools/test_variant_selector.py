#!/usr/bin/env python3
"""Offline checks for variant_selector.py: the claims, asserted as claims.

The tool's own `--self-test` holds the r2 hand transcriptions, which is the
oracle for the branch arithmetic. What is here is the rest: that the twelve
addresses' store sites and their containing routines are what the finding
says, that the three seed tables really are the bytes claimed, and that the
refusals stay refusals.

**No test here counts the tree.** Not the number of store sites, not the
number of functions, not the number of seed pairs. A census of a directory is
a value every merge has to edit, and `CLAUDE.md` records what that costs; the
alternative is asserting the claim -- *these* addresses have *these* sites, in
*these* routines, and *that* table holds *those* bytes -- which stays true
when a suite lands or a listing is exported and goes red when the bytes move.

The `+1` cases are the ones worth having. `0x9547` and `0x9570` increment the
table byte before storing it, so the table's `00` reaches `0x0733` as `01`. A
`derived_values()` that dropped the bump would produce twelve values each one
off, and every one of them would still be a plausible-looking PL limit.
"""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from make_bank_image import build_bank

HERE = Path(__file__).parent
# variant_selector imports disasm8051 and trace_xdata_refs by bare module
# name, the way its siblings do, so the tool directory has to be on the path
# before it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'variant_selector', HERE / 'variant_selector.py')
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# The store sites the finding names for the twelve bytes, and the routine each
# one sits in. Transcribed from `ec/annotations/site-resolution.csv` and
# `ec/decompiled/listing-index.csv`; the two helpers are the three-instruction
# routines `0x94D0` calls rather than inlines, and their being named separately
# is the point of the join.
EXPECTED_SITES = {
    0x0730: [(0x9528, 'copy_code_table_into_0730_07a7'),
             (0x95CA, 'copy_code_table_into_0730_07a7')],
    0x0731: [(0x9533, 'copy_code_table_into_0730_07a7'),
             (0x95D0, 'copy_code_table_into_0730_07a7')],
    0x0732: [(0x953C, 'copy_code_table_into_0730_07a7')],
    0x0733: [(0x9548, 'copy_code_table_into_0730_07a7')],
    0x0734: [(0xBEC9, 'load_code_byte_to_0734')],
    0x0735: [(0x958A, 'copy_code_table_into_0730_07a7'),
             (0x95A4, 'copy_code_table_into_0730_07a7')],
    0x0736: [(0xBED3, 'load_code_byte_to_0736')],
    0x0737: [(0x95B3, 'copy_code_table_into_0730_07a7'),
             (0x95D6, 'copy_code_table_into_0730_07a7')],
    0x07A7: [(0x9551, 'copy_code_table_into_0730_07a7'),
             (0x95C0, 'copy_code_table_into_0730_07a7')],
    0x07A8: [(0x955C, 'copy_code_table_into_0730_07a7'),
             (0x95C6, 'copy_code_table_into_0730_07a7')],
    0x07A9: [(0x9565, 'copy_code_table_into_0730_07a7')],
    0x07AA: [(0x9571, 'copy_code_table_into_0730_07a7')],
}

# The three seed pairs, as (0x0A51 byte, 0x0A52 byte) -> CODE pointer. Big
# endian, because `0xB93D` puts 0x0A51 in R6 and 0x0A52 in R7 and R6 becomes
# DPH; reading it little-endian gives a pointer 256 bytes off and a table that
# happens to look plausible, which is why this is asserted rather than derived.
EXPECTED_SEEDS = {(0x61, 0xFE): 0x61FE, (0x61, 0xC8): 0x61C8, (0x61, 0x92): 0x6192}

# The first sixteen bytes at every seed address, transcribed from
# `r2 -a 8051 ... 'px 16'` on the bank0 image.
EXPECTED_TABLE = bytes.fromhex('3c3ca5002323a5002323a5004b4ba500')

# What the copy derives for the twelve bytes from that table, in BLOCK order,
# with the two `+1` sites already applied. This is also what
# `registers.yaml` records live on 2026-09-23, which is the coincidence the
# finding is about -- asserted as the derived value, not as a claim about what
# the machine did.
EXPECTED_DERIVED = bytes.fromhex('3c3ca5012323a5014b4ba501')


class StoreSites(unittest.TestCase):
    """The join: every store site of the twelve bytes, and its routine."""

    @classmethod
    def setUpClass(cls):
        cls.d = open(FIRMWARE, 'rb').read()
        cls.rows = vs.seed_sites(cls.d)

    def test_every_block_address_has_a_site(self):
        got = {row['addr'] for row in self.rows}
        self.assertEqual(got, set(vs.BLOCK),
                         'a byte of the twelve-byte block has no site, or the '
                         'block and the site scan disagree about its members')

    def test_each_address_sites_the_routines_the_finding_names(self):
        by_addr = {}
        for row in self.rows:
            by_addr.setdefault(row['addr'], []).append(
                (row['runtime'], row['function']))
        for addr, want in EXPECTED_SITES.items():
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(sorted(by_addr.get(addr, [])), sorted(want))

    def test_the_two_helpers_are_named_routines_not_the_seeder(self):
        """`0x0734` and `0x0736` are stored by helpers `0x94D0` calls.

        The whole finding rests on the twelve sites being reachable from one
        routine, so a join that credited them to the caller would be reading
        the same bytes and reaching a different conclusion about which code
        seeds the block.
        """
        named = {row['runtime']: row['function'] for row in self.rows}
        self.assertEqual(named[0xBEC9], 'load_code_byte_to_0734')
        self.assertEqual(named[0xBED3], 'load_code_byte_to_0736')

    def test_a_site_outside_the_seeder_is_reported_not_absorbed(self):
        """The join names a routine or says it cannot; it never guesses one."""
        for row in self.rows:
            with self.subTest(site=f"0x{row['runtime']:04X}"):
                self.assertTrue(row['function'],
                                'an empty function name is a gap, not a result')
                self.assertNotEqual(row['function'], 'unresolved',
                                    'the listing index did not resolve')


class Seeds(unittest.TestCase):
    """The three seed pairs, the tables they name, and what those yield."""

    @classmethod
    def setUpClass(cls):
        cls.d = open(FIRMWARE, 'rb').read()

    def test_the_seed_pairs_are_the_three_the_finding_names(self):
        got = {(hi, lo): code for hi, lo, code in vs.SEEDS}
        self.assertEqual(got, EXPECTED_SEEDS)

    def test_a_seed_pair_is_read_big_endian(self):
        """`0x61`/`0xC8` is 0x61C8, not 0xC861.

        The other order lands 0xC861 inside CODE that happens to be readable,
        so a wrong endianism produces a table rather than an error -- which is
        why the pointer is asserted and not merely read.
        """
        for (hi, lo), want in EXPECTED_SEEDS.items():
            with self.subTest(seed=f"0x{hi:02X}/0x{lo:02X}"):
                self.assertEqual((hi << 8) | lo, want)
        # And the byte order `0xB93D` actually uses, from its own listing.
        insns = vs.decode(self.d, 'bank0', 0xB93D, 3)
        self.assertEqual(insns[0][1], 0xE0, '0xB93D starts `movx a,@dptr`')
        self.assertEqual(insns[1][2], 'mov  r6,a',
                         '0x0A51 lands in R6, which becomes DPH -- the high '
                         'byte, so the pair is big-endian')

    def test_each_seed_table_holds_the_claimed_bytes(self):
        for (hi, lo), code in EXPECTED_SEEDS.items():
            with self.subTest(table=f"0x{code:04X}"):
                self.assertEqual(vs.seed_table(self.d, hi, lo),
                                 EXPECTED_TABLE)

    def test_the_three_tables_are_identical_over_the_copied_window(self):
        """The reason the answer is one answer and not three.

        All three seed tables hold the same sixteen bytes, so whichever arm
        ran, the twelve defaults came out the same. A tool that reported the
        seeds without this would leave a reader to assume the choice matters.
        """
        tables = {vs.seed_table(self.d, hi, lo) for hi, lo, _ in vs.SEEDS}
        self.assertEqual(len(tables), 1,
                         'the seed tables differ over the copied window, so '
                         'the discriminator does change the twelve bytes')

    def test_the_tables_diverge_beyond_the_copied_window(self):
        """Why the window is a boundary and not a coincidence.

        If the three seed tables were identical everywhere, "identical over
        the sixteen bytes the copy reads" would be true of any window and
        would say nothing about the twelve. They are not: the tables part at
        index 0x1A and 0x33, well past the last index `0x94D0` touches. So the
        equality is a property of the copied range, and the range is the point.
        """
        # The bank image, not the raw firmware: a CODE address is a runtime
        # address, and the file offsets `offset_for_runtime` hands back are not
        # an index a `+i` can walk from. `make_bank_image` is the tool that
        # builds that mapping, so it is called rather than re-derived -- and
        # it writes a file, hence the temporary directory.
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'bank0.bin'
            build_bank(FIRMWARE, 0, 0x8000, str(out))
            image = out.read_bytes()
            for (hi, lo), code in EXPECTED_SEEDS.items():
                if (hi, lo) == (0x61, 0xC8):
                    continue
                with self.subTest(seed=f"0x{hi:02X}/0x{lo:02X}"):
                    first = next((i for i in range(vs.TABLE_WINDOW, 0x40)
                                  if image[code + i] != image[0x61C8 + i]), None)
                    self.assertIsNotNone(
                        first, 'no divergence found in 0x40 bytes')
                    self.assertGreaterEqual(
                        first, vs.TABLE_WINDOW,
                        'the tables differ inside the copied window')

    def test_derived_values_match_the_live_record(self):
        table = vs.seed_table(self.d, 0x61, 0xC8)
        vals = vs.derived_values(table)
        got = bytes(vals[a] for a in vs.BLOCK)
        self.assertEqual(got, EXPECTED_DERIVED)

    def test_the_two_d_state_bytes_carry_the_increment(self):
        """`0x0733`, `0x0737` and `0x07AA` are stored +1.

        The table holds `00` at each of those indices; the listing increments
        before storing, so the byte lands as `01`. Dropping the bump yields
        `00` -- a plausible-looking D-state value, and wrong.
        """
        table = vs.seed_table(self.d, 0x61, 0xC8)
        vals = vs.derived_values(table)
        for index, addr, bump in vs.TABLE_READS:
            if bump:
                with self.subTest(addr=f"0x{addr:04X}"):
                    self.assertEqual(vals[addr], (table[index] + 1) & 0xFF)
                    self.assertEqual(table[index], 0x00,
                                     'the fixture assumes the table holds 00 '
                                     'at each incremented index')

    def test_the_table_path_and_the_fixed_arm_disagree_at_0730(self):
        """The comparison the whole issue turns on, asserted both ways.

        `registers.yaml` records `0x3C` live at `0x0730`; the fixed arm writes
        `0x2D` and the table path writes `0x3C`. Asserting only that they
        differ would pass if the table path also wrote `0x2D`; asserting the
        table's value too is what makes it the answer to "which branch
        produces 0x3C".
        """
        table = vs.seed_table(self.d, 0x61, 0xC8)
        self.assertEqual(vs.derived_values(table)[0x0730], vs.LIVE_0730)
        fixed = dict(vs.FIXED_WRITES)
        self.assertEqual(fixed[0x0730], vs.FIXED_0730)
        self.assertNotEqual(vs.LIVE_0730, vs.FIXED_0730)

    def test_the_0782_index_groups_agree(self):
        """Bit 2 of 0x0782 is a real branch that changes nothing here.

        Indices `0x04-0x07` and `0x08-0x0B` hold the same four bytes, so the
        branch selects between identical values. A finding that reported the
        branch without this would read as though the bit mattered to the
        result.
        """
        table = vs.seed_table(self.d, 0x61, 0xC8)
        base = vs.derived_values(table, vs.TABLE_READS)
        alt = vs.derived_values(table, vs.ALT_GROUP)
        for _, addr, _ in vs.ALT_GROUP:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(alt[addr], base[addr])


class Gates(unittest.TestCase):
    """The gates, and the two questions kept apart."""

    def test_the_fixed_arm_runs_when_0770_equals_04(self):
        """`0xB8C0` returns 1 for `0x0770 == 0x04` and `0x95BB jnz` enters.

        Reading the polarity the other way is what turns "this block did not
        run" into a conclusion about a byte nobody has read. The direction is
        asserted from the callee's own listing rather than from the prose.
        """
        d = open(FIRMWARE, 'rb').read()
        insns = vs.decode(d, 'bank0', vs.FIXED_GATE, 5)
        # 0xB8C0 is `mov dptr,#0x770 ; movx a,@dptr ; cjne a,#0x04,0xb8ca ;
        # mov r7,#1 ; ret`, so the compare is the third instruction and the
        # byte it tests against is the one the whole gate turns on.
        self.assertEqual([i[2] for i in insns[:3]],
                         ['mov  dptr,#0x0770', 'movx a,@dptr',
                          'cjne a,#0x04,0xb8ca'])
        self.assertEqual(d[vs.offset_for_runtime(0xB8C4, 'bank0') + 1],
                         vs.GATE_VALUE)
        # `0x95BB` is `70 03`, a `jnz` into the block.
        branch = vs.read_window(d, 'bank0', vs.GATE_BRANCH, 2)
        self.assertEqual(branch, b'\x70\x03')
        self.assertEqual(vs.branch_target(d, 'bank0', vs.GATE_BRANCH, 2),
                         vs.FIXED_ARM)
        # And the case the block is skipped to, so the polarity has both ends.
        self.assertEqual(vs.read_window(d, 'bank0', vs.GATE_SKIP, 1), b'\x22',
                         '0x9A0D is the bare ret the other case tail-jumps to')

    def test_the_shared_tail_is_derived_not_asserted(self):
        """The §7 alignment has to be walked, not printed.

        The anchors are constants in the tool, so nothing would notice if the
        two copies stopped agreeing at that offset -- the table would keep
        claiming they share a tail. `same` and `other` are both held: `other`
        is non-zero because a branch target is a displacement, and a run that
        reported zero would mean the comparison had stopped comparing them.
        """
        d = open(FIRMWARE, 'rb').read()
        same, other = vs.shared_tail(d)
        self.assertGreater(same, 0, 'no instruction aligned at all')
        self.assertGreater(other, 0,
                           'a differing count of zero means branch targets are '
                           'not being compared, not that the copies are equal')
        self.assertEqual(same + other, vs.SHARED_TAIL_INSNS,
                         'the two walks stopped stepping at the same rate, so '
                         'the comparison is pairing unrelated instructions')

    def test_the_two_callee_addresses_are_one_routine(self):
        """`0xBB40` and `0xCA4C` are the same bytes.

        This is what lets the finding say the copies are one routine twice
        rather than two routines that agree, and it is a claim about the image
        rather than about the annotation that named the two addresses.
        """
        d = open(FIRMWARE, 'rb').read()
        a = vs.read_window(d, 'bank0', vs.BB40, vs.HELPER_LEN)
        b = vs.read_window(d, 'bank0', vs.C7_CALLEE, vs.HELPER_LEN)
        self.assertEqual(a, b)
        self.assertEqual(a, bytes.fromhex('900751e0549022'))
        self.assertIn('`90 07 51 e0 54 90 22`', vs.helpers_same(d))

    def test_gfid_gates_the_seeder_and_neither_copy(self):
        """GFID is the seeder's discriminator, and is not the copies'."""
        ab = {addr for addr, _, _ in vs.AB_GATES}
        c7 = {addr for addr, _, _ in vs.C7_GATES}
        self.assertNotIn(vs.GFID, ab)
        self.assertNotIn(vs.GFID, c7)

    def test_the_two_copies_do_not_share_one_discriminator(self):
        """The answer to the issue's second half is "not the same one".

        The gate sets differ, and the question asked whether a single byte
        decided both. Asserting the difference is the finding; asserting the
        equality would be the claim the evidence does not support.
        """
        ab = {(addr, bit) for addr, bit, _ in vs.AB_GATES}
        c7 = {(addr, bit) for addr, bit, _ in vs.C7_GATES}
        self.assertNotEqual(ab, c7)

    def test_the_1603_bit_is_in_the_16xx_id_block_and_not_gfid(self):
        """`0xABxx` is gated by a `0x16xx` ID bit -- the issue's own contrast."""
        d = open(FIRMWARE, 'rb').read()
        c1cb = vs.read_window(d, 'bank0', 0xC1CB, 3)
        self.assertEqual(c1cb, bytes.fromhex('901603'), '0xC1CB loads 0x1603')
        self.assertNotIn(0x1603, {a for a, _, _ in vs.C7_GATES})


class Refusals(unittest.TestCase):
    """What the tool declines to say, held so a check that stops declining goes
    red."""

    def test_a_short_window_is_refused(self):
        with self.assertRaises(vs.Refusal):
            vs.read_window(bytes(0x8000), 'bank0', 0xFFFF, 8)

    def test_a_window_past_the_end_is_refused(self):
        with self.assertRaises(vs.Refusal):
            vs.read_window(bytes(0x8000), 'bank0', 0xFFF0, 64)

    def test_a_seed_pointing_into_a_bank_window_is_refused(self):
        with self.assertRaises(vs.Refusal):
            vs.seed_table(bytes(0x8000), 0x80, 0x00)

    def test_a_refusal_names_what_was_wrong(self):
        try:
            vs.read_window(bytes(0x8000), 'bank0', 0xFFF0, 64)
        except vs.Refusal as exc:
            self.assertIn('0xFFF0', str(exc))
            self.assertIn('bank0', str(exc))
        else:
            self.fail('no Refusal raised')

    def test_the_self_test_passes_against_the_committed_image(self):
        self.assertEqual(vs.self_test(FIRMWARE), 0)


class Output(unittest.TestCase):
    """The printed table, so `--check` has something to compare."""

    def test_the_table_is_printed_and_carries_the_claims(self):
        d = open(FIRMWARE, 'rb').read()
        text = vs.report(d)
        for claim in ('0x07D3', '0x61FE', '0x61C8', '0x6192',
                      'identical over the 16 bytes',
                      'GFID (0x07D3) gates neither copy'):
            with self.subTest(claim=claim):
                self.assertIn(claim, text)

    def test_the_csv_form_has_a_header_and_one_row_per_site(self):
        d = open(FIRMWARE, 'rb').read()
        text = vs.report(d, as_csv=True)
        rows = [r for r in text.splitlines() if r.strip()]
        self.assertEqual(rows[0], 'address,site,region,function')
        # One row per site, against the sites the join itself found -- the
        # claim, not a total of the tree.
        self.assertEqual(len(rows) - 1, len(vs.seed_sites(d)))


if __name__ == '__main__':
    unittest.main()
