#!/usr/bin/env python3
"""Unit checks for the 0x0834 staging word and the 0x0836 word it is
compared against (issue #715).

`docs/findings/charge-stage-word-0834.md` reads the two 16-bit words at
`0x0834`/`0x0835` and `0x0836`/`0x0837` out of the four routines that read,
write or compare them, and `ec/annotations/registers.yaml` now carries a row
for each under the names `CHARGE_STAGE_WORD` and `CHARGE_STAGE_CMP_WORD`.
This file pins the byte facts that reading stands on, and the relations
between the two naming steps (`xdata-overrides.csv` and the generated
`xdata-symbols.csv`) and the entry they name.

**Every case here is static and none of them is a behaviour.** No register was
read, written or read back, no byte was watched move, and no site was seen run
on the laptop: this pipeline has no hardware. A `write` asserted below is an
instruction that stores to an address, not evidence the EC acts on it, and
`present-untested` on either entry is the static scan's grade and nothing more.
The cases are written so none of them could be mistaken for a live result --
they read the committed image, the committed listings and the committed
tables, and nothing here observes anything.

Two things it deliberately does not do. It does not re-run the scans that
wrote `xdata-registers.csv` or `site-resolution.csv`: that would assert a tool
against itself, and a regenerated census would then be free to disagree with
the image. Where a count is asserted it is recomputed here from
`ec/firmware/GMxMGxx_11.800` and compared to what the committed table says,
so a table that moved fails by address. And it does not assert how many rows,
suites, files or lines anything has: every assertion is a relation between
values that are derived, so another branch that names a register or seeds a
routine moves the numbers this reads without moving the ones it holds.

The byte cases are the ones worth having. Everything else -- the per-program
counts, the symbol spelling, the annotation comments -- is a naming layer over
those bytes, and it is the bytes that would decide the questions the entry
leaves open.

It writes no `test_*.py:<line>` citation and names no other test file by line,
for the reason `test_pack_temp_producer_chain.py` gives: that spelling is a
shared-file diff this change has no reason to cause.
"""
import csv
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import yaml

import disasm8051
import verify_gap_text as G
from check_status_vocabulary import declared_statuses, split_status
from trace_xdata_refs import PD_MARKER, region_of, sites_for

ANNOTATIONS = HERE.parent / 'annotations'
GHIDRA = HERE.parent / 'ghidra'
DECOMPILED = HERE.parent / 'decompiled'
REGISTERS = ANNOTATIONS / 'registers.yaml'
SYMBOLS = GHIDRA / 'xdata-symbols.csv'
OVERRIDES = GHIDRA / 'xdata-overrides.csv'
CENSUS = ANNOTATIONS / 'xdata-registers.csv'
SITES = ANNOTATIONS / 'site-resolution.csv'
FUNCTIONS = ANNOTATIONS / 'ghidra-functions.csv'
LISTING_INDEX = DECOMPILED / 'listing-index.csv'
FINDING = ROOT / 'docs' / 'findings' / 'charge-stage-word-0834.md'
FIRMWARE = ROOT / 'ec' / 'firmware' / 'GMxMGxx_11.800'

# Read once, for the reason `test_pack_temp_producer_chain.py` gives: every
# assertion below compares what it reads against a committed table or against
# the image, so a wrong read fails rather than agreeing with itself.
IMAGES = G.load_images()
BANK1 = IMAGES['bank1']

STAGE, STAGE_HI = 0x0834, 0x0835
CMP, CMP_HI = 0x0836, 0x0837
PAIRS = ((STAGE, STAGE_HI), (CMP, CMP_HI))
PAIR_ADDRS = tuple(a for pair in PAIRS for a in pair)

# The shared accessors the whole reading turns on, named once. Which one a site
# calls is what makes it a load, a store or a compare -- `mov DPTR,#imm` is the
# same instruction either way -- so a case below that says which one it is
# saying something the mnemonic alone does not.
LOAD_R3R4, LOAD_BA, STORE_R3R4 = 0x8892, 0x8898, 0x889E
COMPARE_16BIT = 0x8863
LOAD_R1R2, STORE_R1R2 = 0x8886, 0x888C

# A `_LO`/`_HI` spelling bakes an endianness claim into a symbol, which is the
# one claim here the listings do not settle: the pair helpers put the low byte
# at the lower address and `dispatch_0832_event_bits` reads the two bytes into
# R6 and R7 without a helper. So the vocabulary of endings is asserted absent
# rather than a particular one asserted present.
ENDNESS_SUFFIX = re.compile(r'_(LO|HI|HIGH|LOW|MSB|LSB|BYTE\d?)$')


def strip_parens(name):
    """The entry name as `gen_xdata_symbols.py` derives it: any trailing
    `(...)` removed. Restated rather than imported because the generator
    builds a whole table out of it and this wants one name; the rule is a
    regex, and the case below is what would drift."""
    return re.sub(r'\s*\(.*\)\s*$', '', name).strip()


def registers():
    with REGISTERS.open() as f:
        return yaml.safe_load(f)['registers']


def entry_for(addr):
    for entry in registers():
        addrs = entry['addr'] if isinstance(entry['addr'], list) else [entry['addr']]
        if addr in addrs:
            return entry
    raise AssertionError('no registers.yaml entry covers 0x%04X' % addr)


def read_csv(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def symbol_rows():
    return {int(r['addr'], 16): r for r in read_csv(SYMBOLS)}


def census_row(addr):
    for row in read_csv(CENSUS):
        if int(row['addr'], 16) == addr:
            return row
    raise AssertionError('no xdata-registers.csv row for 0x%04X' % addr)


def annotation(name):
    for row in read_csv(FUNCTIONS):
        if row['name'] == name:
            return row
    raise AssertionError('no ghidra-functions.csv row named %r' % name)


def image_counts(addr):
    """(file-wide, main-EC, PD-image) `MOV DPTR,#addr` site counts, from the image.

    `check_register_counts.py`'s own computation, imported rather than copied:
    the YAML's numbers are the numbers the image actually contains, and a copy
    of the rule here would be a second rule that could drift from the first.
    """
    from check_register_counts import MAIN_EC_REGIONS, PD_REGION
    d = FIRMWARE.read_bytes()
    total = main = pd = 0
    for off in sites_for(d, addr):
        total += 1
        region = region_of(off, d[PD_MARKER[0]:PD_MARKER[0] + len(PD_MARKER[1])]
                           == PD_MARKER[1])[0]
        if region in MAIN_EC_REGIONS:
            main += 1
        elif region == PD_REGION:
            pd += 1
    return total, main, pd


def listing_size_covers(program, addr):
    """Which exported function of `program`, if any, contains `addr`?

    Read off `ec/decompiled/listing-index.csv`, whose `size` column is the one
    `ghidra-functions.csv` lacks. The question the write-up turns on is where
    `0xBB40` -- the block `stage_0577_against_0834_0836` jumps to when the
    staging word is zero -- lands: inside that routine's own listing, or
    outside it. The write-up's original claim was that it had no listing at
    all; main seeded it as `stage_0834_from_0403_threshold_and_0497` (#1849),
    so the assertion is now the narrower one that survives.
    """
    for row in read_csv(LISTING_INDEX):
        if row['program'] != program:
            continue
        start = int(row['addr'], 16)
        if start <= addr < start + int(row['size']):
            return row['name']
    return None


class TheTwoEntries(unittest.TestCase):
    """One entry per word, `status:` drawn from the header's own vocabulary,
    and counts that the image reproduces. Nothing here says the words exist as
    charge limits; it says the file grades them the way its vocabulary defines
    and counts them the way its scan finds."""

    def test_each_address_has_an_entry_with_a_declared_status(self):
        values, suffixes = declared_statuses(str(REGISTERS))
        for addr in PAIR_ADDRS:
            entry = entry_for(addr)
            base, suffix = split_status(entry['status'], suffixes)
            with self.subTest(addr='0x%04X' % addr):
                self.assertIn(base, values)

    def test_the_entries_cover_the_pairs_and_not_a_neighbour(self):
        self.assertEqual(
            tuple(sorted(a for a in entry_for(STAGE)['addr'])), PAIRS[0])
        self.assertEqual(
            tuple(sorted(a for a in entry_for(CMP)['addr'])), PAIRS[1])
        for neighbour in (0x0832, 0x0838, 0x083E):
            with self.subTest(addr='0x%04X' % neighbour):
                self.assertNotIn(neighbour, entry_for(STAGE)['addr'])

    def test_each_entry_records_both_per_program_counts(self):
        for addr in PAIR_ADDRS:
            entry = entry_for(addr)
            with self.subTest(addr='0x%04X' % addr):
                self.assertIn('static_refs_main_ec', entry)
                self.assertIn('static_refs_pd_image', entry)

    def test_the_recorded_counts_split_and_reproduce_the_image(self):
        for addr in PAIR_ADDRS:
            entry = entry_for(addr)
            index = list(entry['addr']).index(addr)
            recorded = entry['static_refs'][index]
            main = entry['static_refs_main_ec'][index]
            pd = entry['static_refs_pd_image'][index]
            total, main_ec, pd_image = image_counts(addr)
            with self.subTest(addr='0x%04X' % addr):
                self.assertEqual((total, main_ec, pd_image), (recorded, main, pd))
                self.assertEqual(recorded, main + pd)

    def test_the_grade_rests_on_an_ec_side_site_that_resolves(self):
        # `present-untested` rule 2 and rule 3, held here as relations rather
        # than delegated: the entry says the EC touches the byte, and the
        # census says at least one EC-side site settles which way.
        resolutions = {}
        for row in read_csv(SITES):
            resolutions.setdefault(int(row['addr'], 16), set()).add(row['resolution'])
        for addr in PAIR_ADDRS:
            entry = entry_for(addr)
            if not entry['status'].startswith('present-untested'):
                continue
            index = list(entry['addr']).index(addr)
            with self.subTest(addr='0x%04X' % addr):
                self.assertGreaterEqual(entry['static_refs_main_ec'][index], 1)
                self.assertTrue(
                    {'read', 'write', 'read+write'} & resolutions[addr],
                    'no EC-side site of 0x%04X resolves to a direction' % addr)


class TheNames(unittest.TestCase):
    """`xdata-overrides.csv` is the hand-maintained escape hatch and
    `xdata-symbols.csv` is generated from it, so the relation between the two
    and the entry they name is recomputed here rather than transcribed: the
    `_0`/`_1` split is by address order, which is what `gen_xdata_symbols.py`
    prescribes and what no `_LO`/`_HI` reading would be."""

    def test_every_address_has_one_override_and_one_symbol_row(self):
        overrides = {int(r['addr'], 16): r for r in read_csv(OVERRIDES)}
        symbols = symbol_rows()
        for addr in PAIR_ADDRS:
            with self.subTest(addr='0x%04X' % addr):
                self.assertIn(addr, overrides)
                self.assertIn(addr, symbols)
                self.assertTrue(overrides[addr]['reason'].strip())

    def test_each_symbol_is_the_entry_name_indexed_by_address_order(self):
        symbols = symbol_rows()
        for lo, hi in PAIRS:
            entry = entry_for(lo)
            base = strip_parens(entry['name'])
            for index, addr in enumerate((lo, hi)):
                with self.subTest(addr='0x%04X' % addr):
                    self.assertEqual(symbols[addr]['name'], '%s_%d' % (base, index))
                    self.assertEqual(symbols[addr]['register_status'],
                                     entry['status'])

    def test_no_symbol_carries_an_endianness_suffix(self):
        for addr in PAIR_ADDRS:
            with self.subTest(addr='0x%04X' % addr):
                self.assertIsNone(ENDNESS_SUFFIX.search(symbol_row_name(addr)))

    def test_the_index_is_the_lower_address_that_carries_the_zero(self):
        # The one claim the `_0`/`_1` split does make, and it is a claim about
        # the addresses and not about the bytes in them.
        for lo, hi in PAIRS:
            self.assertLess(lo, hi)
            self.assertTrue(symbol_row_name(lo).endswith('_0'))
            self.assertTrue(symbol_row_name(hi).endswith('_1'))

    def test_the_symbol_table_names_no_program_the_pd_image_is_not_in(self):
        for addr in PAIR_ADDRS:
            with self.subTest(addr='0x%04X' % addr):
                self.assertNotIn('pd', symbol_rows()[addr]['programs'].split(';'))


def symbol_row_name(addr):
    return symbol_rows()[addr]['name']


class ThePdHalfKeepsNoName(unittest.TestCase):
    """The two programs are separate address spaces with separate XDATA maps,
    so a name for the EC's 0x0834 is not a claim about the PD image's. That
    holds by construction of the generator and by the exporter skipping the PD
    program, and these are the cases that would notice it stopping to hold."""

    def test_the_census_names_no_pd_row_with_an_ec_register_name(self):
        for addr in PAIR_ADDRS:
            row = census_row(addr)
            with self.subTest(addr='0x%04X' % addr):
                for half in row['spellings_by_program'].split(';'):
                    program, _, spelling = half.partition('=')
                    if program == 'pd':
                        self.assertEqual(spelling, 'DAT_EXTMEM')

    def test_no_exported_pd_source_spells_either_name(self):
        names = tuple(symbol_row_name(a) for a in PAIR_ADDRS)
        for path in sorted((DECOMPILED / 'pd').glob('*.c')):
            body = path.read_text(errors='replace')
            for name in names:
                with self.subTest(path=path.name, name=name):
                    self.assertNotIn(name, body)

    def test_the_counterpart_table_records_the_lookup_beside_the_spelling(self):
        # `ec/ghidra/c-asm-counterpart.csv`'s `symbol` column is a lookup of the
        # EC's name for an address, so a `pd` row that reaches one of these
        # picks the new name up. That is the column's existing shape -- it
        # already reads USB_C_POWER_PRIORITY on `pd` rows -- and what keeps it
        # from being a name for the PD byte is the `spellings` column beside it,
        # which is what the PD text actually says. Both are asserted here, so a
        # tool change that started spelling the name into the PD program would
        # fail rather than pass quietly.
        names = tuple(symbol_row_name(a) for a in PAIR_ADDRS)
        counterpart = GHIDRA / 'c-asm-counterpart.csv'
        seen = 0
        for row in read_csv(counterpart):
            if row['program'] != 'pd':
                continue
            if int(row['xdata_addr'], 16) not in PAIR_ADDRS:
                continue
            seen += 1
            with self.subTest(function=row['addr'], addr=row['xdata_addr']):
                self.assertIn(row['symbol'], names)
                self.assertNotIn(row['symbol'], row['spellings'])
                self.assertIn(row['xdata_addr'][2:].upper(), row['spellings'])
        self.assertTrue(seen, 'the PD image reaches none of these addresses')

    def test_the_pd_image_has_its_own_sites_at_these_addresses(self):
        # The reason the split is not vacuous: the PD image does reach these
        # addresses, and naming them there would be a category error rather
        # than a harmless extra label.
        for addr in (STAGE, CMP):
            _total, _main, pd = image_counts(addr)
            with self.subTest(addr='0x%04X' % addr):
                self.assertGreater(pd, 0)


class TheAnnotationComments(unittest.TestCase):
    """Two of these comments said the addresses were undocumented, which the
    rows make false; the third described what the routine stages without saying
    otherwise. All three now name the register. The hedges they carried are the
    part that must survive: the names say the role the instructions show and no
    more."""

    def rows(self):
        return [annotation(n) for n in
                ('stage_0577_against_0834_0836', 'clear_0834_word_when_nonzero',
                 'guard_then_store_pair_0834')]

    def test_each_comment_names_the_new_registers_and_cites_the_issue(self):
        for row in self.rows():
            with self.subTest(name=row['name']):
                self.assertIn('CHARGE_STAGE_WORD', row['comment'])
                self.assertIn('#715', row['comment'])

    def test_no_comment_calls_either_word_undocumented(self):
        # The claim is not "these three comments stopped saying it" -- it is
        # that no clause listing addresses as undocumented names one of the
        # four this change gave a row. Held over the addresses rather than
        # over the sentences, so rewording a clause does not have to come back
        # here. `registers.yaml` is not consulted for the rule, so a clause
        # about an address outside this change stays this change's business
        # only where it says so.
        for row in self.rows():
            for clause in re.split(r'[.;]', row['comment']):
                if 'not documented' not in clause:
                    continue
                for addr in PAIR_ADDRS:
                    with self.subTest(name=row['name'], addr='0x%04X' % addr):
                        self.assertNotIn('0x%04X' % addr, clause)

    def test_the_hedges_survive(self):
        # `guard_then_store_pair_0834`'s own words: nothing in those
        # instructions ties the compares to the charge target's meaning. A
        # comment update that dropped this would be the overclaim.
        guard = annotation('guard_then_store_pair_0834')
        self.assertIn('nothing in these instructions ties the compares',
                      guard['comment'])
        stage = annotation('stage_0577_against_0834_0836')
        self.assertIn('nothing in them ties either word to a unit',
                      stage['comment'])

    def test_no_comment_gives_either_word_a_unit(self):
        # `CHARGE_TARGET_MV` is the neighbouring register's name and carries a
        # millivolt; the check is that neither *new* name acquires one, which
        # is what a unit claim on these two would look like. Nothing committed
        # establishes 0x0180, 0x0400 or 0x3138 as the same quantity as a
        # millivolt target, so a suffix here would be the overclaim.
        for row in self.rows():
            with self.subTest(name=row['name']):
                self.assertIsNone(
                    re.search(r'CHARGE_STAGE_(?:CMP_)?WORD_[A-Z]', row['comment']))

    def test_every_row_carries_non_empty_evidence(self):
        for row in self.rows():
            with self.subTest(name=row['name']):
                self.assertTrue(row['evidence'].strip())


class ThePairHelpers(unittest.TestCase):
    """Four tiny routines the whole reading is built on, asserted as bytes.
    They are what makes the word a word: without `inc dptr` between the two
    halves there is no pair to name, and without the store's order there is
    no byte order to state."""

    def test_the_load_reads_the_first_byte_into_r3_then_the_second_into_r4(self):
        self.assertEqual(BANK1[LOAD_R3R4:LOAD_R3R4 + 7],
                         b'\xe0\xfb\xa3\xe0\xfc\x22\xe0')
        self.assertEqual((listing('bank1', '8892.asm')[1][2],
                          listing('bank1', '8892.asm')[2][2]),
                         ('mov R3, A', 'inc DPTR'))

    def test_the_store_writes_r3_then_increments_then_writes_r4(self):
        self.assertEqual(BANK1[STORE_R3R4:STORE_R3R4 + 6],
                         b'\xeb\xf0\xa3\xec\xf0\x22')
        self.assertEqual((listing('bank1', '889E.asm')[0][2],
                          listing('bank1', '889E.asm')[1][2],
                          listing('bank1', '889E.asm')[2][2]),
                         ('mov A, R3', 'movx @DPTR, A', 'inc DPTR'))

    def test_the_other_two_pair_helpers_have_the_same_shape(self):
        # Read as R1:R2 and written as R1:R2, byte for byte the same sequence
        # with the register number raised by two -- which is why the three
        # staging sites can use either and mean either.
        self.assertEqual(BANK1[LOAD_R1R2:LOAD_R1R2 + 6], b'\xe0\xf9\xa3\xe0\xfa\x22')
        self.assertEqual(BANK1[STORE_R1R2:STORE_R1R2 + 6], b'\xe9\xf0\xa3\xea\xf0\x22')

    def test_the_load_into_b_and_a_returns_the_second_byte_in_a(self):
        self.assertEqual(BANK1[LOAD_BA:LOAD_BA + 6], b'\xe0\xf5\xf0\xa3\xe0\x22')

    def test_the_sixteen_bit_compare_sets_carry_on_the_smaller_operand(self):
        # The routine the guards branch on: `subb` low then `subb` high, carry
        # out meaning first operand below second. The 0x0001 special case is
        # why its callers test the accumulator's bit 0 in one place and the
        # carry in another, and it is asserted here so the write-up's reading
        # of that cannot drift from the bytes.
        self.assertEqual(BANK1[COMPARE_16BIT:COMPARE_16BIT + 9],
                         b'\xc3\xeb\x99\xec\x9a\x40\x0d\xec\xb5')
        at = {addr: text for addr, _raw, text in listing('bank1', '8863.asm')}
        self.assertEqual((at[0x8865], at[0x8867]), ('subb A, R1', 'subb A, R2'))
        self.assertEqual((at[0x8868], at[0x8872], at[0x8877]),
                         ('jc 0x8877', 'mov A, #0x0', 'mov A, #0x1'))


def decode(start, length):
    """[(runtime address, operand text)] for a straight-line window of bank 1.

    The repository's own decoder rather than a pattern search, so a case can
    ask what a block *does* in the order it does it and be wrong loudly if the
    answer is wrong. Branches are not followed -- this is a linear walk, the
    same limit `trace_xdata_refs.py` records -- so a case below reads a block
    that is straight-line or reads an order its arms share.
    """
    return [(addr, ' '.join(text.split()))
            for addr, _raw, text in
            disasm8051.decode(BANK1, start, length, addr=start)]


def listing(bank, name):
    """[(address, bytes, text)] for every instruction line of one listing.

    Read here rather than through a shared parser, for the reason
    `test_pack_temp_producer_chain.py` gives: the assertions above compare what
    comes back against the image, so a reader that mis-parsed the byte column
    would fail rather than pass quietly.
    """
    out = []
    for line in (DECOMPILED / bank / name).read_text(errors='replace').splitlines():
        if line.startswith(';') or not line.strip():
            continue
        cols = line.split()
        out.append((int(cols[0], 16),
                    bytes(int(b, 16) for b in cols[1:4] if b != '-'),
                    ' '.join(cols[4:])))
    return out


class TheClearAndTheCountdown(unittest.TestCase):
    """`clear_0834_word_when_nonzero` and
    `reload_083e_when_0834_is_zero`, which disagree about which side of the
    zero/non-zero test does the interesting thing. The second reloads 0x083E
    when the word is *zero* and lets it count down when it is not -- the
    opposite way round from what the name suggests at a glance, and the bytes
    are what settle it."""

    def test_the_clear_returns_on_zero_and_otherwise_zeroes_and_flags(self):
        self.assertEqual(BANK1[0xBD20:0xBD20 + 0x25], bytes([
            0x90, 0x08, 0x34, 0x12, 0x88, 0x98,        # mov DPTR,#0x834; lcall 0x8898
            0x45, 0xf0, 0x60, 0x1a,                    # orl A,B; jz -> ret
            0x74, 0x02, 0x90, 0x08, 0xe4, 0xf0,        # A=2; DPTR=0x08E4; store
            0x90, 0x00, 0x00, 0xac, 0x83, 0xab, 0x82,  # DPTR=0; R4=DPH; R3=DPL
            0x90, 0x08, 0x34, 0x12, 0x88, 0x9e,        # DPTR=0x834; lcall 0x889E
            0x90, 0x08, 0x32, 0xe0, 0x44, 0x01, 0xf0,  # DPTR=0x832; orl A,#1; store
            0x22]))

    def test_the_countdown_reloads_when_the_word_is_zero_and_decrements_otherwise(self):
        # The `jz` at 0xC4B7 leaves for 0xC4CB, which is the reload; the
        # decrement is on the fall-through. Asserted as the branch target and
        # the two blocks separately, because "which side reloads" is the whole
        # claim and a byte string would not say it.
        rows = listing('bank1', 'C4AF.asm')
        at = {addr: text for addr, _raw, text in rows}
        self.assertEqual(at[0xC4B7], 'jz 0xc4cb')
        self.assertEqual(at[0xC4BD], 'dec A')
        self.assertEqual(at[0xC4CE], 'mov A, #0x3c')
        self.assertEqual(at[0xC4D0], 'movx @DPTR, A')
        # ...and the reload's own store is to 0x083E, not to the staging word.
        self.assertEqual(at[0xC4CB], 'mov DPTR, #0x83e')


class TheClampIsAnImmediate(unittest.TestCase):
    """`guard_then_store_pair_0834` clamps its input to "0x0400" by loading
    DPTR with the immediate and copying DPTR's own bytes into the compare
    operands. It never reads the register at 0x0400, so the clamp ceiling is
    a constant and not a value the pack reports -- which is why no unit is
    claimed for the word it stores."""

    CLAMP = (0xBF42, 0xBF59)

    def test_the_ceiling_is_built_from_dptr_and_never_read(self):
        body = BANK1[self.CLAMP[0]:self.CLAMP[1]]
        self.assertEqual(body[:7], bytes([0x90, 0x04, 0x00, 0xab, 0x82, 0xac, 0x83]))
        self.assertEqual(body[-7:], bytes([0x90, 0x04, 0x00, 0xad, 0x82, 0xae, 0x83]))
        # `movx` is the only way this firmware reads an XDATA byte, and there
        # is none between the two: the clamp never touches 0x0400.
        self.assertNotIn(0xe0, body)
        self.assertNotIn(0xf0, body)

    def test_the_ceiling_is_the_number_the_compare_is_given(self):
        rows = listing('bank1', 'BF3A.asm')
        at = {addr: text for addr, _raw, text in rows}
        self.assertEqual(at[0xBF4D], 'lcall 0x8863')
        self.assertEqual(at[0xBF50], 'jnc 0xbf59')
        self.assertEqual(at[0xBF57], 'mov R6, DPH')


class TheStagingOrder(unittest.TestCase):
    """The claim the second entry rests on: wherever the staging word is
    written from zero, the compare word is written first, and 0x0832 bit 1 is
    set before bit 0. It holds at three sites, and one of the three is in no
    committed listing.

    The cases walk each block with the repository's own decoder rather than
    scanning for byte patterns: a window long enough to hold `0xBB40`'s two
    arms also holds whatever follows them, and a pattern search over it picks
    up stores that are not part of the claim.
    """

    # Each site is the first instruction of the block, and each length is the
    # block's own extent as the listings give it -- `0xBB40` reaches to the
    # `ret` at 0xBBA3 because its two arms are both in the walk.
    STAGING_SITES = ((0xBB40, 0x64), (0xBF96, 0x25), (0xBC77, 0x33))

    def test_the_compare_word_is_stored_before_the_staging_word_at_every_site(self):
        for start, length in self.STAGING_SITES:
            with self.subTest(site='0x%04X' % start):
                self.assertEqual(self.stores(start, length)[:2], [CMP, STAGE])

    def test_bit_one_of_0832_is_set_before_bit_zero_at_every_site(self):
        for start, length in self.STAGING_SITES:
            with self.subTest(site='0x%04X' % start):
                self.assertEqual(self.flags(start, length)[:2], [0x02, 0x01])

    def stores(self, start, length):
        """Addresses written through `write_r3r4_to_xdata_pair`, in order."""
        out, dptr = [], None
        for _addr, text in decode(start, length):
            if text.startswith('mov dptr,'):
                dptr = int(text.split('#')[1], 16)
            elif text == 'lcall 0x889e' and dptr is not None:
                out.append(dptr)
        return out

    def flags(self, start, length):
        """`orl a,#imm` values written through the 0x0832 read-or-write, in order."""
        out, dptr = [], None
        for _addr, text in decode(start, length):
            if text.startswith('mov dptr,'):
                dptr = int(text.split('#')[1], 16)
            elif text.startswith('orl a,#') and dptr == 0x0832:
                out.append(int(text.split('#')[1], 16))
        return out

    def test_two_of_the_three_sites_choose_the_source_and_one_does_not(self):
        # `0xBB40` and `0xBC77` read the literal 0x3138 unless bit 0 of 0x0497
        # sends them to CHARGE_TARGET_MV; `guard_then_store_pair_0834` reads
        # CHARGE_TARGET_MV with no test at all. The entry says so, and this is
        # what would notice it being edited to say otherwise.
        for start, length in ((0xBB40, 0x30), (0xBC77, 0x18)):
            body = ' '.join(text for _addr, text in decode(start, length))
            with self.subTest(site='0x%04X' % start):
                self.assertIn('mov dptr,#0x3138', body)
                self.assertIn('mov dptr,#0x0497', body)
                self.assertIn('mov dptr,#0x0522', body)
        untested = ' '.join(text for _addr, text in decode(0xBF96, 0x25))
        self.assertIn('mov dptr,#0x0522', untested)
        self.assertNotIn('mov dptr,#0x3138', untested)

    def test_the_third_site_is_the_second_with_a_source_selection_in_front(self):
        # `0xBC77` and `0xBF96` are the same bytes from the `CHARGE_TARGET_MV`
        # load onward; `0xBC77` has the `0x3138`/`0x0497` selection in front
        # and `0xBF96` does not. That is what makes the ordering a pattern
        # rather than three separate accidents, so it is asserted over the
        # bytes rather than over a transcription of them.
        start = BANK1.index(b'\x90\x05\x22\x12\x88\x92', 0xBC77, 0xBC90)
        self.assertEqual(BANK1[start:start + 0x25],
                         BANK1[0xBF96:0xBF96 + 0x25])

    def test_the_first_site_is_outside_the_listing_that_reaches_it(self):
        # 0xBB40 is where `stage_0577_against_0834_0836`'s own `jz` at 0xBAE6
        # lands when the staging word is zero, and that routine's listing ends
        # at 0xBB3C, so the block that stages the word is not part of it. It
        # used to have no listing of its own either; main seeds it as
        # `stage_0834_from_0403_threshold_and_0497` (#1849), so the assertion
        # is now the narrower one that survives, and the block's bytes are the
        # committed listing's rather than only this suite's reading of them.
        self.assertNotEqual(listing_size_covers('bank1', 0xBB40),
                            'stage_0577_against_0834_0836')
        self.assertEqual(listing_size_covers('bank1', 0xBB40),
                         'stage_0834_from_0403_threshold_and_0497')
        self.assertEqual(annotation('stage_0577_against_0834_0836')['scope'], 'bank1')
        self.assertEqual(BANK1[0xBAE6:0xBAE8], bytes([0x60, 0x58]))

    def test_the_committed_listing_agrees_with_the_transcription(self):
        # The write-up transcribed these bytes from the image because there was
        # no listing to cite. There is one now, and it must say the same thing
        # instruction for instruction -- otherwise the transcription was a
        # second, divergent reading rather than a restatement of the export.
        listing = (DECOMPILED / 'bank1' / 'BB40.asm').read_text()
        for addr, mnemonics in ((0xBB40, 'mov      DPTR, #0x3138'),
                                (0xBB54, 'mov      DPTR, #0x836'),
                                (0xBB57, 'lcall    0x889e'),
                                (0xBB5A, 'mov      DPTR, #0x832'),
                                (0xBB5E, 'orl      A, #0x2'),
                                (0xBB60, 'movx     @DPTR, A')):
            with self.subTest(addr='0x%04X' % addr):
                line = next(l for l in listing.splitlines()
                            if l[:4].upper() == '%04X' % addr)
                self.assertIn(mnemonics, line)

    def test_the_two_blocks_it_selects_are_the_same_instructions(self):
        # 0xBB7A and 0xBB8F are the arms of the 0x0403/0x0539 test. Byte for
        # byte they are the same sequence, so the test has no observable
        # effect -- which is the annotation's claim, and is why this is a pair
        # of identical arms rather than two different sources.
        self.assertEqual(BANK1[0xBB7A:0xBB8F], BANK1[0xBB8F:0xBBA4])
        self.assertEqual(BANK1[0xBB7A:0xBB7D], bytes([0x90, 0x01, 0x80]))


class TheByteOrderIsOnlyHalfSettled(unittest.TestCase):
    """Why the symbols are indexed by address order. The pair helpers put the
    low byte at the lower address, and `dispatch_0832_event_bits` reads the two
    bytes one at a time into R6 and R7 with no helper -- so the helper reading
    is a property of the helpers, not a settled property of the word."""

    def test_the_helpers_put_the_lower_address_first(self):
        # `inc dptr` between the two halves is the whole of it.
        load = BANK1[LOAD_R3R4:LOAD_R3R4 + 7]
        store = BANK1[STORE_R3R4:STORE_R3R4 + 6]
        self.assertEqual(load[2], 0xA3)
        self.assertEqual(store[2], 0xA3)

    def test_the_dispatcher_reads_the_two_bytes_one_at_a_time(self):
        rows = {addr: text for addr, _raw, text in listing('bank1', 'A750.asm')}
        self.assertEqual(rows[0xA787], 'mov DPTR, #0x834')
        self.assertEqual(rows[0xA78A], 'movx A, @DPTR')
        self.assertEqual(rows[0xA78B], 'mov R6, A')
        self.assertEqual(rows[0xA78C], 'mov DPTR, #0x835')
        self.assertEqual(rows[0xA78F], 'movx A, @DPTR')
        self.assertEqual(rows[0xA790], 'mov R7, A')
        # No helper between them, which is the whole difference.
        self.assertNotIn('lcall', rows[0xA78B])
        self.assertNotIn('lcall', rows[0xA790])

    def test_the_writeup_leaves_the_byte_order_open(self):
        text = FINDING.read_text()
        self.assertIn('not settled', text)


class TheWriteup(unittest.TestCase):
    """The write-up is the finding; these are the properties that keep it a
    calibration rather than a claim. Its own last line has to say that nothing
    was observed live, because that is the sentence a reader skims."""

    def setUp(self):
        self.text = FINDING.read_text()

    def test_it_has_a_title_for_the_findings_index(self):
        self.assertTrue(self.text.startswith('# '))

    def test_it_says_no_register_was_read_back(self):
        self.assertIn('read back', self.text)

    def test_it_names_the_unit_it_is_not_claiming(self):
        self.assertIn('No unit is claimed', self.text)

    def test_it_records_the_already_named_04a2_pair(self):
        self.assertIn('PACK_TEMP_DK', self.text)
        self.assertIn('#1425', self.text)

    def test_it_names_the_block_the_staging_reading_cannot_cite(self):
        self.assertIn('0xBB40', self.text)


class ThisSuiteIsStatic(unittest.TestCase):
    """The suite's own module docstring has to say what every case above is,
    because a reader who opens one test and not the docstring should still
    meet the caveat. `tools/run-tests.sh` collects docstrings, and a suite
    whose docstring overstates what it does is the overclaim this repository
    checks for everywhere else."""

    def test_the_docstring_says_nothing_was_read_back(self):
        doc = (__import__(__name__).__doc__ or '')
        self.assertIn('read back', doc)
        self.assertIn('static', doc)


if __name__ == '__main__':
    unittest.main()