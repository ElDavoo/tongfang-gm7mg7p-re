#!/usr/bin/env python3
"""The byte facts behind issue #732's three 16-bit entries, and the note shape
they have to keep.

`docs/findings/xdata-04a0-run-elapsed-counters.md` reads `0x04A0`/`0x04A1` as a
16-bit mirror of `0x0524`/`0x0525`, reads `0x04AE`/`0x04AF` and
`0x04BE`/`0x04BF` as up-counters that the `0x0490` gate arms and clears, and
reports that issue #732's own premise -- "no committed routine has been read
setting them non-zero" -- does not survive the check the issue asked for.
This file pins the bytes that reading stands on, and the two sentences each
`registers.yaml` note has to carry.

**Every case here is static and none of them is a behaviour.** No register was
read, written or read back and no site was seen run. A `write` asserted below
is an instruction, not evidence the EC acted on the byte, and `0x3C == 60` is
arithmetic on the committed decompiles, never a measurement. The assertions
read the committed image and the committed listings, and nothing here watches a
byte move.

Two things it deliberately does not do. It does not re-run the scan that wrote
`xdata-registers.csv` or `xdata-inc-dptr-only.csv`: `check_register_counts.py`
and `inc_dptr_sites.py --check` already hold those against fresh generations,
and asserting a census here would make this suite red for a change to the
decompiled tree that has nothing to do with the reading. And it asserts no
count of the repository's own text -- the three entries exist, the bytes are
where the listings put them, the notes carry the wording. What a merge adds is
not this suite's business.

Where a listing and the image could drift, both are read: the operand text from
the `.asm`, the bytes from the image at the runtime address, and they are
compared against each other. A raw `90 hi lo` scan is deliberately not used --
the same three bytes occur inside data in a 64 KiB image -- so every byte
assertion below is at an address a committed listing names.

**The note-shape cases are the calibration rule made mechanical.** This is the
closest thing in the tree to a check on a claim rather than on a file: each of
the three notes has to name the functions it rests on, carry both sentences the
write-up's last bullet carries, and refuse a unit on the same line it would
otherwise be tempted to give one. A unit word may appear in a note, but only in
a sentence that also refuses the unit -- which is the difference between saying
"this is not named in seconds or minutes" and saying "60 seconds".
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import verify_gap_text as G  # noqa: E402

DECOMPILED = HERE.parent / 'decompiled'
ANNOTATIONS = ROOT / 'ec' / 'annotations'
REGISTERS = ANNOTATIONS / 'registers.yaml'
OVERRIDES = ROOT / 'ec' / 'ghidra' / 'xdata-overrides.csv'
FINDING = ROOT / 'docs' / 'findings' / 'xdata-04a0-run-elapsed-counters.md'

# Read once, the way `test_pack_temp_producer_chain.py` gives: a per-case read
# of three 64 KiB images is not a cost worth paying repeatedly, and every byte
# assertion below compares what it reads against a committed listing, so a
# wrong read fails rather than agreeing with itself. `load_images` returns one
# image per program already indexed by *runtime* address, which is what
# `make_bank_image.py` arranges and why no case here does offset arithmetic.
IMAGES = G.load_images()
BANK0, BANK1 = IMAGES['bank0'], IMAGES['bank1']

# The three entries, and the runtime addresses the listings use. Named once so
# a case says which pair it is about rather than repeating four hex literals.
ENTRIES = {
    'XDATA_04A0_MIRROR_OF_0524': (0x04A0, 0x04A1),
    'XDATA_04AE_COUNTER_A': (0x04AE, 0x04AF),
    'XDATA_04BE_COUNTER_B': (0x04BE, 0x04BF),
}

# The refusal the write-up's last bullet requires of every note, and the unit
# claim it must never make. A time-unit *word* is not banned outright --
# "not named in seconds or minutes" is the sentence this tree wants, and
# ordinary English puts "second" in front of "path" -- so what is checked is
# the claim (a number with a unit) and the refusal (stated somewhere in the
# note), not the vocabulary.
UNIT_CLAIM = re.compile(r'\b\d+\s*(seconds?|minutes?)\b', re.I)
UNIT_REFUSAL = re.compile(r'no unit is claimed|not named in|no unit\b', re.I)
NOT_OBSERVED = re.compile(r'no register was read,? written or read back', re.I)
# Matched on the operative half only. What precedes "not thereby" names what
# the EC does with the pair -- it arms and disarms the counters, it keeps the
# mirror in step -- and that is not the same sentence for both, so a note that
# got its own register's writers right still has to land the refusal.
NOT_A_WRITE_TARGET = re.compile(r'not thereby a linux driver should write', re.I)


def source(name):
    """One committed `.c` or `.asm` under `ec/decompiled/`."""
    return (DECOMPILED / name).read_text(errors='replace')


def lines(name):
    """[(address, bytes, text)] for every instruction line of a listing.

    Read here rather than through a shared parser, for the reason
    `test_pack_temp_producer_chain.py` gives: a reader that mis-parsed the
    byte column could not pass quietly, because the cases below compare what
    comes back against the image.
    """
    out = []
    for line in source(name).splitlines():
        if line.startswith(';') or not line.strip():
            continue
        cols = line.split()
        raw = bytes(int(b, 16) for b in cols[1:4] if b != '-')
        out.append((int(cols[0], 16), raw, ' '.join(cols[4:])))
    return out


def operands(name):
    """{runtime address: operand text} for one listing, mnemonic dropped."""
    return {a: ' '.join(t.split()[1:]) for a, _raw, t in lines(name)}


def registers():
    """{name: entry} out of the committed `registers.yaml`."""
    import yaml
    with REGISTERS.open() as f:
        return {e['name']: e for e in yaml.safe_load(f)['registers']}


def note_of(entry):
    """The folded single-line text of an entry's `note:`."""
    return ' '.join(entry['note'].split())


class TheZeroing(unittest.TestCase):
    """The two arming routines, read out of the listings and the image."""

    def test_b841_clears_the_gate_bits_and_zeroes_04ae_in_one_run(self):
        # The claim is that these two things are adjacent in the *machine
        # code*, not merely near each other in the decompile, so the case is on
        # the contiguous bytes from the `mov DPTR,#0x490` that precedes the
        # `anl` to the `lcall 0x888c` that stores the pair.
        self.assertEqual(BANK1[0xB860:0xB877].hex(' '),
                         '90 04 90 e0 54 f9 f0 12 b8 8c 12 b9 37 '
                         '79 00 7a 00 90 04 ae 12 88 8c')
        ops = operands('bank1/B841.asm')
        # 0xf9 is bits 0, 1, 2 and 6; bit 1 is the gate
        # `charge_target_update` is reached on, and the mask is asserted as the
        # byte rather than as a reading, so a re-derived listing that cleared a
        # different set of bits fails here.
        self.assertEqual(ops[0xB864], 'A, #0xf9')
        self.assertEqual(ops[0xB871], 'DPTR, #0x4ae')
        self.assertEqual(ops[0xB874], '0x888c')

    def test_b8e1_is_the_same_shape_on_bit_5_for_04be(self):
        self.assertEqual(BANK1[0xB900:0xB917].hex(' '),
                         '90 04 90 e0 54 9f f0 12 b9 1b 12 b9 62 '
                         '79 00 7a 00 90 04 be 12 88 8c')
        ops = operands('bank1/B8E1.asm')
        self.assertEqual(ops[0xB904], 'A, #0x9f')
        self.assertEqual(ops[0xB911], 'DPTR, #0x4be')
        self.assertEqual(ops[0xB914], '0x888c')

    def test_bfd9_is_the_same_two_stores_and_nothing_else(self):
        # `zero_04ae_and_04be` is named for what it does, so the name is the
        # claim: three instructions, two stores, one of each pair, and a
        # return. A third store here would make the name a half-truth.
        self.assertEqual(BANK1[0xBFD9:0xBFE9].hex(' '),
                         '79 00 7a 00 90 04 ae 12 88 8c 90 04 be 12 88 8c')
        self.assertEqual(BANK1[0xBFE9], 0x22)  # ret

    def test_bit_1_of_0490_is_the_branch_into_charge_target_update(self):
        # `20 e1 10` is `jb ACC.1, +0x10` from 0xB148, which is 0xB158 --
        # `charge_target_update`. The offset is checked rather than read off
        # the mnemonic, because the write-up's whole placement rests on this
        # being the bit-1 gate rather than some other bit of the same byte.
        self.assertEqual(BANK0[0xB141:0xB148].hex(' '),
                         '90 04 90 e0 20 e1 10')
        self.assertEqual(0xB148 + 0x10, 0xB158)
        self.assertIn('Reached by a conditional branch from 0xB141',
                      source('bank0/B158.c'))
        # The listing spells the branch with its own column padding, so the
        # operand text is compared after the reader drops the mnemonic and
        # rejoins the rest -- which is what `operands()` is for.
        self.assertEqual(operands('bank0/B12C.asm')[0xB145], '0xe1, 0xb158')


class TheIncrements(unittest.TestCase):
    """What displaces issue #732's "no committed routine sets them non-zero"."""

    def test_bfbb_counts_the_byte_in_front_and_carries_into_the_word(self):
        c = source('bank1/BFBB.c')
        # The byte in front is counted first and reset at 0x3c, and only then
        # is the word counted -- once per 0x3c ticks, which is the whole of the
        # claim. Both halves asserted separately so a re-export that dropped
        # one leaves it visible which.
        self.assertIn('DAT_EXTMEM_04ad = DAT_EXTMEM_04ad + 1;', c)
        self.assertIn('if ((DAT_EXTMEM_04ad != 0x3c) && (DAT_EXTMEM_04ad < 0x3c)) {',
                      c)
        self.assertIn('DAT_EXTMEM_04ad = 0;', c)
        # The carry into the high byte is what makes this a 16-bit +1 rather
        # than two independent byte increments, so `bVar1` and its use are
        # pinned together.
        self.assertIn('bVar1 = DAT_EXTMEM_04ae == -1;', c)
        self.assertIn("DAT_EXTMEM_04ae = DAT_EXTMEM_04ae + '\\x01';", c)
        self.assertIn('bVar3 = DAT_EXTMEM_04af + bVar1;', c)
        self.assertIn('if (!CARRY1(DAT_EXTMEM_04af,bVar1)) {', c)

    def test_c0a8_is_the_same_counter_on_the_04bd_column(self):
        c = source('bank1/C0A8.c')
        self.assertIn('DAT_EXTMEM_04bd = DAT_EXTMEM_04bd + 1;', c)
        self.assertIn('if ((DAT_EXTMEM_04bd != 0x3c) && (DAT_EXTMEM_04bd < 0x3c)) {',
                      c)
        self.assertIn('bVar1 = DAT_EXTMEM_04be == -1;', c)
        self.assertIn('bVar4 = DAT_EXTMEM_04bf + bVar1;', c)

    def test_0x3c_is_the_multiplier_in_both_comparisons(self):
        # `(ushort)bVar3 * 0x3c` -- the byte in front times 60. Asserted for
        # both routines because the write-up says "both", and the reason the
        # name carries no unit is exactly that this factor is the only number
        # here that could have supplied one.
        for name in ('bank1/BFBB.c', 'bank1/C0A8.c'):
            c = source(name)
            self.assertIn('0x3c', c, name)
            self.assertRegex(c, r'\* 0x3c',
                             f'{name} does not multiply by 0x3c')

    def test_the_comparison_feeds_0494_and_049c(self):
        # The +0x08 pair the write-up's column section names, pinned from both
        # ends: each routine's flag byte is reached with `& 0xf3 |`.
        self.assertIn('DAT_EXTMEM_0494 = DAT_EXTMEM_0494 & 0xf3', source('bank1/BFBB.c'))
        self.assertIn('DAT_EXTMEM_049c = DAT_EXTMEM_049c & 0xf3', source('bank1/C0A8.c'))
        self.assertEqual(0x0494 + 0x08, 0x049C)


class TheMirror(unittest.TestCase):
    """`0x04A0`/`0x04A1` as a mirror rather than a staging slot."""

    def test_d0c4_mirrors_0524_into_04a0_and_clears_04a1(self):
        c = source('bank1/D0C4.c')
        self.assertIn('DAT_EXTMEM_04a0 = DAT_EXTMEM_0524;', c)
        self.assertIn('DAT_EXTMEM_04a1 = 0;', c)
        # The same routine takes 0x0524 to 0x0526 in the adjacent statement,
        # which is what makes 0x04A0 a second copy of one source rather than a
        # slot something is staged through.
        self.assertIn('DAT_EXTMEM_0526 = DAT_EXTMEM_0524;', c)
        self.assertIn('DAT_EXTMEM_04a0 = 0x20;', c)

    def test_b2d5_stores_the_word_at_0524_through_the_16bit_writer(self):
        # `lcall 0x888c` is the 16-bit store helper, so this is a copy of the
        # word at 0x0524/0x0525 and not of a byte.
        ops = operands('bank1/B2D5.asm')
        self.assertEqual(ops[0xB2E5], 'DPTR, #0x524')
        self.assertEqual(ops[0xB2E8], '0xb6c9')
        self.assertEqual(ops[0xB2ED], 'DPTR, #0x4a0')
        self.assertEqual(ops[0xB2F0], '0x888c')

    def test_the_readers_test_individual_bits_across_both_bytes(self):
        # The bit tests are what displace the "staging area" reading, so each
        # is pinned where the write-up puts it. A reader that took the whole
        # word, or only one byte, would satisfy none of these.
        for name, expr in (('bank1/B2A0.c', r'DAT_EXTMEM_04a0 >> 5 & 1'),
                           ('bank1/AD8B.c', r'DAT_EXTMEM_04a0 >> 5 & 1'),
                           ('bank1/BA43.c', r'DAT_EXTMEM_04a1 >> 6 & 1'),
                           ('bank1/BA43.c', r'DAT_EXTMEM_04a1 & 0x90'),
                           ('bank1/C11C.c', r'DAT_EXTMEM_04a1 & 0x90')):
            self.assertRegex(source(name), expr,
                             f'{name} no longer tests {expr}')

    def test_ba43_reads_04a0_beside_the_04a1_bit_test_and_does_not_compare_them(self):
        # The write-up and the note used to say `0xBA43` "compares 0x04A0
        # against 0x0524 directly", which is a misreading of the decompile:
        # `0x04A0` is assigned into `param_1` and the comparison is
        # `DAT_EXTMEM_0524 == BANK0_R1`. Both halves are pinned here because
        # the correction is the claim -- a reader that came back comparing the
        # two bytes to each other would be a different, and wrong, sentence.
        c = source('bank1/BA43.c')
        self.assertRegex(c, r'param_1 = DAT_EXTMEM_04a0')
        self.assertRegex(c, r'DAT_EXTMEM_0524 == ')
        self.assertNotRegex(c, r'DAT_EXTMEM_04a0 ==')


class TheEntries(unittest.TestCase):
    """What `registers.yaml` and the override file have to say about the three."""

    def test_each_entry_is_a_pair_entered_as_one_name(self):
        regs = registers()
        for name, addrs in ENTRIES.items():
            self.assertIn(name, regs, f'no registers.yaml entry for {name}')
            entry = regs[name]
            self.assertEqual(entry['addr'], list(addrs), name)
            self.assertEqual(entry['status'], 'present-untested', name)
            # The count columns are `check_register_counts.py`'s to hold; the
            # case is here only because a ragged list would break that tool
            # with a message about this entry rather than about the image.
            for key in ('static_refs', 'static_refs_main_ec',
                        'static_refs_pd_image'):
                self.assertEqual(len(entry[key]), 2, f'{name}: {key}')

    def test_the_overrides_name_both_bytes_by_address_order(self):
        # Never `_LO`/`_HI`: an endianness claim baked into a symbol outlives
        # the note that would correct it, which is the reason the 0x0438 row of
        # this file gives. The `_0`/`_1` here is address order and nothing else.
        import csv
        with OVERRIDES.open() as f:
            rows = {int(r['addr'], 16): r for r in csv.DictReader(f)}
        for name, addrs in ENTRIES.items():
            for i, addr in enumerate(addrs):
                self.assertIn(addr, rows, f'no override row for 0x{addr:04X}')
                self.assertEqual(rows[addr]['name'], f'{name}_{i}')
                self.assertNotRegex(rows[addr]['name'],
                                    r'_(LO|HI|HIGH|LOW|BYTE0|BYTE1)$')

    def test_04a1_pd_sites_are_recorded_as_another_programs_bytes(self):
        # The three PD-image sites of 0x04A1 are a different program's bytes at
        # the same address number, split rather than summed. The note has to
        # say so, or a reader of the `static_refs_pd_image` column would take
        # them for this EC's high half.
        note = note_of(registers()['XDATA_04A0_MIRROR_OF_0524'])
        self.assertRegex(note, r'another program')


class TheNoteShape(unittest.TestCase):
    """The calibration rule, on the three notes this change wrote.

    Every case here is about the *text*, and that is deliberate: this is the
    closest thing in the tree to a check on a claim. The write-up's own last
    bullet says no part of this was observed live and that a register the EC
    arms and disarms is not thereby one a Linux driver should write, and a note
    that dropped either sentence would be making a claim the evidence does not
    carry. Both are required of all three notes, so one weak note cannot be
    carried by two strong ones.
    """

    def test_each_note_names_the_functions_it_rests_on(self):
        # A note that cites no function is asserting a reading with nothing
        # under it; `docs/findings.md` §4 is this repository's retracted case
        # of a claim that read stronger than its evidence. The bar is a
        # bank/address spelling of a routine, not a filename.
        for name in ENTRIES:
            self.assertRegex(note_of(registers()[name]),
                             r'bank[01] 0x[0-9A-Fa-f]{4}',
                             f'{name} names no decompiled routine')

    def test_each_note_carries_both_required_sentences(self):
        for name in ENTRIES:
            note = note_of(registers()[name])
            self.assertRegex(note, NOT_OBSERVED,
                             f'{name} does not say nothing was observed live')
            self.assertRegex(
                note, NOT_A_WRITE_TARGET,
                f'{name} does not refuse the driver-write-target reading')

    def test_no_note_asserts_a_unit(self):
        # Two halves, and the first is the one that bites. A note that says
        # "60 seconds" has made the claim; a note that says "no unit is
        # claimed" has not. The bare word is not evidence either way --
        # `0xBFBB`'s note says "on the second path" and means the second one --
        # so the word is left alone and the number-with-a-unit is not.
        #
        # What this does *not* catch, and says so rather than pretending: a
        # note that asserted a unit with no number beside it ("this is a
        # minutes counter") would pass. The per-note refusal below is what
        # catches it in practice, because a note that has decided the unit is
        # not the one carrying the refusal.
        for name in ENTRIES:
            note = note_of(registers()[name])
            self.assertNotRegex(note, UNIT_CLAIM,
                                f'{name} asserts a unit with a number')
        # The refusal is required of the two counters and not of the mirror.
        # `XDATA_04A0_MIRROR_OF_0524` reads a copied value rather than counting
        # one, so there is no tick rate for it to decline and a note that
        # carried the sentence anyway would be claiming a question was open
        # when it is not -- the same overclaim in the other direction.
        for name in ('XDATA_04AE_COUNTER_A', 'XDATA_04BE_COUNTER_B'):
            self.assertRegex(note_of(registers()[name]), UNIT_REFUSAL,
                             f'{name} does not state that no unit is claimed')

    def test_the_names_carry_no_unit(self):
        # The same refusal at the layer above the prose: a symbol is read by
        # every future grep, and `COUNTER_SECONDS` would assert the unit in a
        # place no note can correct. Here the bare word *is* the claim, because
        # a symbol has no sentence around it to decline in.
        for name in ENTRIES:
            self.assertNotRegex(name, UNIT_CLAIM, name)
            self.assertNotRegex(name, r'\b(seconds?|minutes?)\b', name)
        import csv
        with OVERRIDES.open() as f:
            for row in csv.DictReader(f):
                self.assertNotRegex(row['name'], r'\b(seconds?|minutes?)\b',
                                    row['addr'])


class TheWriteUp(unittest.TestCase):
    """The file the entries cite exists and keeps its own two sentences."""

    def test_it_exists_and_says_nothing_was_observed(self):
        text = FINDING.read_text()
        self.assertIn('Nothing here was observed on hardware', text)

    def test_every_note_points_at_it(self):
        # A note that cites a write-up nobody can find is a citation that
        # checks nothing, so the path is asserted rather than trusted.
        for name in ENTRIES:
            self.assertIn('xdata-04a0-run-elapsed-counters.md',
                          note_of(registers()[name]), name)

    def test_it_records_the_issue_premise_that_did_not_survive(self):
        # Issue #732 asked for the opposite sentence and the check it asked
        # for falsifies it. Leaving the check visible is the point: a reader
        # who finds the entries named as counters should be able to find here
        # that the issue's phrasing was checked and rejected, not silently
        # dropped.
        text = FINDING.read_text()
        self.assertRegex(text, r'does not survive|not the whole of it|'
                               r'fails that sentence')
        self.assertIn('increment', text)


if __name__ == '__main__':
    unittest.main()