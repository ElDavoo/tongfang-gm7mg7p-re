#!/usr/bin/env python3
"""Unit checks for the bank-switch forwarder target census (issue #465).

`docs/findings/forwarder-target-bank-census.md` re-measures the family of BL51
forwarders whose `imm16` operand #255 established is resolved *after* the bank
switch, and lands the replacement for the 19 / 7 / 22 figure
`ec/annotations/ghidra-functions.csv` `bank1,19A8` withdrew. This file holds
that measurement to things it cannot be graded against by the tool that made
it.

**What it grades against, and why each one is a different thing.**

  * **the image.** The bytes of a forwarder entry, and of a bank window at the
    same offset, are read from `ec/firmware/GMxMGxx_11.800` and compared with
    constants transcribed here. That is the common-area finding, and it is
    pinned as two byte strings rather than as a rule so a refactor of the rule
    cannot quietly stop asserting it. The entry population is the whole image:
    `trampolines` defaults to a `0x8000` limit, and a census bounded there
    could not contain a forwarder in a bank's own window, so "every entry is
    common area" would hold for the bound rather than for the firmware.
  * **the committed listings.** Every oracle row's class is re-derived from the
    named `.asm` with `citation_callers.iter_instructions`, not from the tool's
    own coverage map, so a coverage map that stopped covering what it claims to
    is caught rather than agreeing with itself.
  * **a negative control.** Two of the oracle addresses are an instruction
    start in one bank and an operand byte in the other. A classifier that lost
    the bank argument would answer one class for both and fail; one that lost
    the *listing* argument would answer `entry` for all four and fail. The
    control is what makes "the class is a property of the address in a named
    bank" mean something.

**What it deliberately does not do.** It does not re-run the scan that produced
`ec/annotations/forwarder-targets.csv` and then grade the tool against that
same run -- the omission `test_paged_trampoline_framing.py` gives, for the same
reason: a regenerated census would then be free to disagree with the image.
And it asserts no count of the tree. The subset moves when an annotation row
lands, the family does not move at all, and a test that pinned either number
would be a value every merge had to edit. What is asserted instead is the claim
each figure rests on -- that the rows and the image agree, that the classes are
drawn from a declared vocabulary, and that a `no-listing` is not an absence.

**And the correction is checked where it landed.** §4a wants the withdrawn
figure visible beside its replacement, so both are asserted present in the rows
that carry them: `19A8` for the census, `198A` and `ghidra-variables.csv`
`bank1,0xA389` for the two residuals #255 left in place. Those assertions are on
the text staying, which is the one thing a correction is for.
"""
import csv
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import census_forwarder_targets as census
from audit_call_targets import STUB_SITES, bank_switch_stubs, trampolines
from build_ec_decompile import BANK_WINDOWS, COMMON_END, file_offset
from citation_callers import iter_instructions, norm_addr

ANNOTATIONS = HERE.parent / 'annotations'
DECOMPILED = HERE.parent / 'decompiled'
FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
FUNCTIONS_CSV = ANNOTATIONS / 'ghidra-functions.csv'
VARIABLES_CSV = ANNOTATIONS / 'ghidra-variables.csv'
CENSUS_CSV = ANNOTATIONS / 'forwarder-targets.csv'
WRITEUP = ROOT / 'docs' / 'findings' / 'forwarder-target-bank-census.md'

FIRMWARE_BYTES = FIRMWARE.read_bytes()

# The eight addresses the write-up, the three annotation rows and the issue all
# name, with what each bank's committed listings say about them:
# `(class, covering listing, that listing's own entry address)`, and `None`
# where no committed listing covers the address in that bank.
#
# Transcribed by reading the listings rather than by importing the tool's
# coverage map -- a table generated from the thing it grades is not an oracle.
# Two of the eight are the cross-bank control: `C389` is its own listing's entry
# in bank 0 and the third byte of the `lcall 0xc41d` at `0xC387` in bank 1, and
# `AA04` is the mirror of that. Everything else is here because something quotes
# it.
ORACLE = {
    0xC1E7: {'bank0': ('entry', 'C1E7', 0xC1E7),
             'bank1': ('entry', 'C1E7', 0xC1E7)},      # `bank1,198A`
    0xC118: {'bank0': ('entry', 'C118', 0xC118),
             'bank1': ('operand', 'C0A8', 0xC117)},    # `bank1,19A8`
    0xC10C: {'bank0': ('no-listing', None, None),
             'bank1': ('operand', 'C0A8', 0xC10B)},    # `bank1,1984`
    0xC389: {'bank0': ('entry', 'C389', 0xC389),
             'bank1': ('operand', 'C352', 0xC387)},    # `bank1,19B4`, cross-bank
    0xAA04: {'bank0': ('no-listing', None, None),
             'bank1': ('entry', 'A9B4', 0xAA04)},      # `bank1,1A14`, cross-bank
    0xC0AD: {'bank0': ('entry', 'C0AD', 0xC0AD),
             'bank1': ('operand', 'C0A8', 0xC0AC)},
    0x8294: {'bank0': ('entry', '8294', 0x8294),
             'bank1': ('no-listing', None, None)},
    0xC349: {'bank0': ('entry', 'C349', 0xC349),
             'bank1': ('no-listing', None, None)},
}

# The two banks' differing answers for one address, named separately so the
# negative control reads as a control rather than as two table rows that happen
# to disagree. Both shapes are here on purpose: `C389` is an operand byte in
# one bank and an entry in the other, and `AA04` has no listing at all in one
# and is an instruction start inside another listing in the other. A classifier
# that dropped the bank argument would answer one class for both banks; one
# that dropped the listing argument would answer `entry` for all sixteen cells.
CROSS_BANK_CONTROL = (0xC389, 0xAA04)

# The common-area finding, as bytes rather than as arithmetic. `0x198A` is
# `bank1,198A`'s address, and the pair is the whole of it: the forwarder's six
# bytes are at file `0x198A`, and bank 1's own region at the same offset into
# that window is unrelated code. Pinned so the finding survives a refactor of
# whatever rule derives it.
COMMON_AREA_BYTES = bytes.fromhex('90 c1 e7 02 11 00')
BANK1_OWN_WINDOW_BYTES = bytes.fromhex('70 0f 90 1c 04 e0')
BANK1_WINDOW_AT_198A = 0x1198A

# The longer byte transcriptions of the two targets the annotation rows read off
# the image by hand, which are also the only two anyone has read that way. The
# census prints eight bytes of every target, so each of these is checked as a
# *prefix* rather than an equality -- the row it belongs to quotes twelve bytes
# and the CSV is not going to be widened to match.
HAND_READ_TARGETS = {
    0xC118: '12 c0 e7 ef 60 03 7f 01 22 7f 00 22',
    0xC10C: '12 c0 c9 ef 60 03 7f 01 22 7f 00 22',
}

# Words no reason may contain, at any strength. `no-listing` means this method
# did not find a listing; "absent" and "undecodable" are claims about the
# firmware, and an unexported function is the first thing in this tree that
# makes them.
OVERCLAIMING = ('absent', 'undecodable', 'not code', 'no code')


def csv_rows(path):
    with open(path, newline='') as handle:
        return list(csv.DictReader(handle))


def annotation_row(scope, addr):
    for row in csv_rows(FUNCTIONS_CSV):
        if row['scope'] == scope and norm_addr(row['addr']) == norm_addr(addr):
            return row
    raise AssertionError('no ghidra-functions.csv row for %s,%s' % (scope, addr))


def variable_row(scope, addr):
    for row in csv_rows(VARIABLES_CSV):
        if row['scope'] == scope and norm_addr(row['addr']) == norm_addr(addr):
            return row
    raise AssertionError('no ghidra-variables.csv row for %s,%s' % (scope, addr))


def listing_starts(program, listing):
    """The instruction start addresses of one committed listing."""
    return [int(parts[0], 16)
            for parts in iter_instructions(DECOMPILED / program / (listing + '.asm'))]


def squeezed(text):
    """`text` with its runs of whitespace collapsed, for phrase assertions."""
    return ' '.join(text.split())


class TheImageUnderneath(unittest.TestCase):
    """The bytes, before any rule is applied to them."""

    def test_the_stub_map_is_the_audit_tools_own(self):
        # Imported rather than restated: `STUB_SITES` is audit_call_targets.py's
        # pinned answer and a copy of it here would be a second thing to keep
        # right, and a disagreement would then be two correct-looking answers
        # rather than one failure.
        self.assertEqual(dict(STUB_SITES), bank_switch_stubs(FIRMWARE_BYTES))

    def test_every_forwarder_entry_is_a_trampoline_in_the_shared_area(self):
        # Every entry, not the one the write-up quotes. The claim is that the
        # whole block sits below COMMON_END and each entry's own bytes are the
        # `mov DPTR,#imm16 ; ljmp stub` shape naming the imm16 the scan read --
        # so this holds as rows land, and a bank-private entry would red it.
        #
        # The whole image is scanned, not `trampolines`'s default `0x8000`
        # bound, and that is what makes the assertion above load-bearing rather
        # than a tautology: bounded at `0x8000`, every entry it returns is
        # below `COMMON_END` by construction, so a bank-private entry could
        # never be in the population this grades. Asked for the file length
        # here rather than through the tool's own wrapper, so the bound under
        # test is visible at the call site and not inherited from the code
        # being graded.
        stubs = bank_switch_stubs(FIRMWARE_BYTES)
        entries = trampolines(FIRMWARE_BYTES, stubs, limit=len(FIRMWARE_BYTES))
        self.assertTrue(entries, 'no forwarder found in this image')
        for entry, (bank, imm16) in sorted(entries.items()):
            with self.subTest(entry='0x%04X' % entry):
                self.assertLess(entry, COMMON_END)
                stub = next(a for a, b in stubs.items() if b == bank)
                self.assertEqual(
                    FIRMWARE_BYTES[entry:entry + 6],
                    census.trampoline_bytes(imm16, stub))

    def test_198a_is_the_common_area_and_not_bank_1s_own_code(self):
        # The finding, as two byte strings. `ec/decompiled/bank1/198A.asm`
        # reads like a bank-1 listing because a bank program is its own region
        # plus the shared `0x0000`-`0x7FFF`; the bytes are at file `0x198A`, and
        # what bank 1's own region holds at that offset is unrelated.
        self.assertEqual(FIRMWARE_BYTES[0x198A:0x198A + 6], COMMON_AREA_BYTES)
        self.assertEqual(FIRMWARE_BYTES[BANK1_WINDOW_AT_198A:
                                       BANK1_WINDOW_AT_198A + 6],
                         BANK1_OWN_WINDOW_BYTES)

    def test_the_bank_window_read_is_not_the_common_area_read(self):
        # The two halves of the pair above, as the rule that derives them. The
        # contrast has to be a real read: a bank's own region at the same
        # offset is a different file offset, so `placement()` is asking about
        # different bytes rather than re-reading the ones it already has.
        resolved, own = census.placement(FIRMWARE_BYTES, 0x198A,
                                         COMMON_AREA_BYTES)
        self.assertEqual(set(resolved.values()), {0x198A})
        self.assertEqual(resolved['bank1'], file_offset('bank1', 0x198A))
        self.assertEqual(BANK1_WINDOW_AT_198A,
                         BANK_WINDOWS['bank1'] + 0x198A)
        self.assertFalse(any(own.values()))

    def test_the_stub_each_row_names_is_the_stub_its_bytes_jump_to(self):
        # The subset's rule and the image, joined. A row whose comment named a
        # stub other than the one its listing tail-jumps to would be selected by
        # the rule and wrong about the bank, which is the failure the rule is
        # there to prevent.
        stubs = bank_switch_stubs(FIRMWARE_BYTES)
        entries = trampolines(FIRMWARE_BYTES, stubs, limit=len(FIRMWARE_BYTES))
        inside, _outside = census.annotated_rows(FIRMWARE_BYTES, stubs, entries)
        self.assertTrue(inside, 'the subset rule selected nothing')
        for scope, addr, _name, _type, imm16, stub in inside:
            with self.subTest(row='%s,%s' % (scope, addr)):
                self.assertEqual(entries[int(addr, 16)],
                                 (stubs[int(stub, 16)], int(imm16, 16)))


class TheClassifier(unittest.TestCase):
    """Each oracle address against the committed listings of each bank."""

    def test_every_oracle_address_classifies_as_transcribed(self):
        covers = census.coverage_for_banks()
        for addr, banks in sorted(ORACLE.items()):
            for program, want in sorted(banks.items()):
                with self.subTest(addr='0x%04X' % addr, bank=program):
                    cls, listing, start = census.classify(program, addr,
                                                         covers[program])
                    self.assertEqual((cls, listing, start), want)

    def test_each_oracle_class_comes_out_of_the_listing_it_names(self):
        # Re-derived from the `.asm` itself. `classify()` builds its answer out
        # of a coverage map, and a map that quietly stopped covering the bytes
        # would agree with its own expectations for ever.
        for addr, banks in sorted(ORACLE.items()):
            for program, (cls, listing, start) in sorted(banks.items()):
                if cls == 'no-listing':
                    continue
                with self.subTest(addr='0x%04X' % addr, bank=program):
                    starts = listing_starts(program, listing)
                    self.assertIn(start, starts)
                    if cls == 'entry':
                        self.assertIn(addr, starts)
                    else:
                        self.assertNotIn(addr, starts)

    def test_the_two_banks_actually_disagree_about_the_control_addresses(self):
        # The negative control, stated as its own test so a reader is not left
        # to infer it from four table rows. Both addresses answer differently in
        # the two banks, which is what makes the bank argument load-bearing, and
        # one of them answers non-`entry` in both, which is what makes the
        # listing argument load-bearing.
        covers = census.coverage_for_banks()
        not_an_entry_everywhere = False
        for addr in CROSS_BANK_CONTROL:
            with self.subTest(addr='0x%04X' % addr):
                first = census.classify('bank0', addr, covers['bank0'])[0]
                second = census.classify('bank1', addr, covers['bank1'])[0]
                self.assertNotEqual(first, second)
                not_an_entry_everywhere |= first != 'entry' or second != 'entry'
        self.assertTrue(not_an_entry_everywhere,
                        'both control addresses are an entry in one of the two '
                        'banks and in no other, so a classifier that answered '
                        '`entry` everywhere would pass')

    def test_the_selected_bank_has_no_operand_answers_at_all(self):
        # The correction's sharpest form, as a property rather than a pair of
        # numbers: over the whole family, no forwarder target is an operand
        # byte in the bank its stub selects. Every one of them is either the
        # entry of its own committed listing or has no listing -- so the 22
        # "operand" answers the withdrawn count recorded were not a property of
        # these addresses in *any* bank, only of the wrong one.
        rows, _stubs, _inside, _outside = census.survey(FIRMWARE_BYTES)
        operands = [r for r in rows if r['class'] == 'operand']
        self.assertEqual([('0x%04X' % r['target']) for r in operands], [])

    def test_every_target_lands_in_the_declared_vocabulary(self):
        # Three answers and no fourth, over the census as a whole rather than
        # over the oracle -- a class name invented by a later edit would not
        # fail the oracle and would pass every other case.
        for row in csv_rows(CENSUS_CSV):
            with self.subTest(forwarder=row['forwarder']):
                self.assertIn(row['class'], census.CLASSES)


class TheCalibration(unittest.TestCase):
    """What a `no-listing` is allowed to say."""

    def test_every_no_listing_row_carries_bytes_and_names_the_program(self):
        rows = csv_rows(CENSUS_CSV)
        unlisted = [r for r in rows if r['class'] == 'no-listing']
        self.assertTrue(unlisted, 'the census found no unlisted target to hold')
        for row in unlisted:
            with self.subTest(target=row['target']):
                self.assertEqual(len(row['bytes'].split()), census.TARGET_BYTES)
                self.assertIn('bank%d' % int(row['bank']), row['reason'])
                self.assertEqual(row['listing'], '')
                self.assertEqual(row['listing_entry'], '')

    def test_no_row_claims_more_than_this_method_found(self):
        for row in csv_rows(CENSUS_CSV):
            with self.subTest(target=row['target']):
                reason = row['reason'].lower()
                for word in OVERCLAIMING:
                    self.assertNotIn(word, reason)

    def test_the_hand_read_targets_are_the_bytes_the_census_prints(self):
        # Two addresses someone transcribed off the image by hand before this
        # census existed, in the rows that still carry the transcription. The
        # census must agree with them rather than supersede them silently.
        rows = {r['target']: r for r in csv_rows(CENSUS_CSV)}
        for addr, want in sorted(HAND_READ_TARGETS.items()):
            with self.subTest(target='0x%04X' % addr):
                printed = rows['0x%04X' % addr]['bytes']
                self.assertTrue(want.startswith(printed),
                                'the census prints %r, the hand transcription '
                                'is %r' % (printed, want))

    def test_no_register_status_is_named_by_this_change(self):
        registers = (ANNOTATIONS / 'registers.yaml').read_text()
        for token in ('forwarder-targets', 'census_forwarder_targets'):
            self.assertNotIn(token, registers)


class TheCommittedCensus(unittest.TestCase):
    """`ec/annotations/forwarder-targets.csv` is the tool's own output."""

    def test_the_committed_file_is_what_the_writer_produces(self):
        # Byte for byte, because it is a generated file with no other consumer
        # and nothing else would notice a stale regeneration. Regenerate with
        # `python3 ec/tools/census_forwarder_targets.py --csv`, which is what
        # the module docstring records.
        buf = io.StringIO()
        with redirect_stdout(buf):
            census.write_csv(census.survey(FIRMWARE_BYTES)[0])
        # Bytes, not text: `csv.writer` terminates with CRLF, as the call-target
        # census beside it does, and a text-mode read would translate them away
        # on both sides and compare two things neither of them holds.
        self.assertEqual(buf.getvalue().encode(), CENSUS_CSV.read_bytes())

    def test_the_resolved_bank_per_row_is_the_stub_that_row_names(self):
        # The column `bank-call-targets.csv` sets as a precedent: the bank is
        # the one the forwarder's own tail-jump selects, not the one the entry
        # is filed under.
        stubs = bank_switch_stubs(FIRMWARE_BYTES)
        for row in csv_rows(CENSUS_CSV):
            with self.subTest(forwarder=row['forwarder']):
                self.assertEqual(int(row['bank']), stubs[int(row['stub'], 16)])

    def test_both_directions_are_in_the_file(self):
        # The mirror direction is a result, not an omission, so its presence is
        # what a reader of the file has to be able to see.
        stubs = {r['stub'] for r in csv_rows(CENSUS_CSV)}
        self.assertEqual(stubs, {'0x%04X' % addr for addr, bank in STUB_SITES
                                 if bank in (0, 1)})


class TheCorrection(unittest.TestCase):
    """§4a: the withdrawn text stays visible beside its replacement."""

    def test_the_19a8_row_keeps_the_withdrawn_split_and_names_the_command(self):
        row = annotation_row('bank1', '19A8')
        self.assertIn('19 on an instruction start, 7 not covered by any '
                      'committed bank1 listing at all, and 22 on an operand '
                      'byte', row['comment'])
        self.assertIn('census_forwarder_targets.py', row['comment'])

    def test_the_198a_row_corrects_the_bank_it_named(self):
        row = annotation_row('bank1', '198A')
        # The old name stays -- §4a -- so the assertion is that bank 0's name
        # and the correction are there too, not that the bank-1 one is gone.
        self.assertIn('latch_0498_bit1_or_bit3', row['comment'])
        self.assertIn('test_1664_bit0', row['comment'])
        self.assertIn('CORRECTION', row['comment'])

    def test_the_variables_row_cites_the_listing_and_keeps_the_stale_clause(self):
        row = variable_row('bank1', '0xA389')
        self.assertIn('ec/decompiled/bank0/C389.asm', row['evidence'])
        self.assertTrue((ROOT / 'ec/decompiled/bank0/C389.asm').is_file())
        self.assertIn('clear_1607_bit2', row['comment'])
        # The "unexported" reading was true when written and false now; §4a
        # puts the correction beside it rather than over it.
        self.assertIn('unexported', row['comment'])
        self.assertIn('CORRECTION', row['comment'])

    def test_no_subset_row_resolves_its_target_in_the_bank_it_is_filed_under(self):
        # Every subset row is filed under bank1 and every one of them routes to
        # the bank-0 stub, so none of them may resolve its imm16 in bank 1 --
        # which is the shape #255 withdrew. Asserted against the census's own
        # answer and not against the prose, because thirty of these rows say
        # "tail-jumps to 0x1100" and never spell the stub out.
        rows, _stubs, inside, _outside = census.survey(FIRMWARE_BYTES)
        subset = census.subset_rows(rows, inside)
        self.assertTrue(subset, 'the subset rule selected nothing')
        for row in subset:
            with self.subTest(row=row['annotation']):
                self.assertNotEqual(row['bank'], 1)

    def test_the_withdrawn_operand_reading_survives_nowhere(self):
        # The correction's substance, stated as a property rather than as a
        # pair of numbers: no address the withdrawn column called an operand
        # byte in bank 1 is an operand byte in bank 0. Both figures in the
        # 19 / 7 / 22 are counts that move when a row lands; this holds as they
        # move, and a census that had quietly been re-derived against bank 1
        # again would fail it.
        rows, _stubs, inside, _outside = census.survey(FIRMWARE_BYTES)
        withdrawn_operands = [r for r in census.subset_rows(rows, inside)
                             if r['reclassified'] == 'operand']
        self.assertTrue(withdrawn_operands, 'nothing was withdrawn as an operand')
        for row in withdrawn_operands:
            with self.subTest(target='0x%04X' % row['target']):
                self.assertNotEqual(row['class'], 'operand')

    def test_the_two_columns_are_not_one_column_written_twice(self):
        # A correction that changed nothing would print as two identical
        # columns. Asserted over the census as a whole: the set of addresses
        # that are an instruction start in one bank is not the set that is an
        # instruction start in the other, so the column really is reading
        # somewhere else.
        rows, _stubs, _inside, _outside = census.survey(FIRMWARE_BYTES)
        here = {r['target'] for r in rows if r['class'] == 'entry'}
        there = {r['target'] for r in rows if r['reclassified'] == 'entry'}
        self.assertNotEqual(here, there)


class TheWriteup(unittest.TestCase):
    """The document a reader is sent to, checked for the things that make it one."""

    def test_it_leads_with_the_common_area_finding(self):
        text = squeezed(WRITEUP.read_text())
        lead = squeezed(''.join(WRITEUP.read_text().split('\n#', 1)[0]))
        self.assertIn('common area', lead)
        self.assertIn('bank1,198A', text)

    def test_it_quotes_the_withdrawn_figure_beside_the_replacement(self):
        text = squeezed(WRITEUP.read_text())
        self.assertIn('19 / 7 / 22', text)
        self.assertIn('census_forwarder_targets.py', text)

    def test_it_carries_the_mirror_direction(self):
        text = squeezed(WRITEUP.read_text())
        self.assertIn('0x1114', text)

    def test_it_states_the_calibration_limit_and_makes_no_behavioural_claim(self):
        text = squeezed(WRITEUP.read_text())
        for phrase in ('not found by this method', 'behavioural claim',
                       'Nothing was observed on hardware'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()