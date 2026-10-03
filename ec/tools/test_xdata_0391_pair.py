#!/usr/bin/env python3
"""Byte checks for the 0x0390/0x0391 reading (issue #295).

`docs/findings/xdata-0390-0391-filter-pair.md` reads the pair the EC keeps as
two accumulator bytes behind the `0x9EA1` filter: what the filter's input pair
is, what the comparison in `FUN_CODE_e100` selects, and where the value in
`0x0391` comes from. This file pins the byte facts that reading stands on, out
of the committed image and the committed tables.

It asserts against the image rather than by re-running the scan that wrote
`annotations/site-resolution.csv` -- that would assert the tool against itself,
and a regenerated census would then be free to disagree with the firmware. It
also pins the one instruction the `E100` branch argument turns on, because that
argument is the write-up's one *correction* of a committed decompile and the
instruction is what settles it.

The one thing asserted here that is not a byte is the calibration: the write-up
and the new `registers.yaml` note must not claim a live observation. Neither
byte has one, and this suite is where that stays enforced rather than left to
the author's good intentions.
"""
import csv
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051
import verify_gap_text as G
import yaml

ANNOTATIONS = ROOT / 'ec' / 'annotations'
REGISTERS = ANNOTATIONS / 'registers.yaml'
SITE_RESOLUTION = ANNOTATIONS / 'site-resolution.csv'
CENSUS = ANNOTATIONS / 'xdata-registers.csv'
FINDINGS = ROOT / 'docs' / 'findings' / 'xdata-0390-0391-filter-pair.md'

# Loaded once rather than per test, for the reason test_bank1_e582_framing.py
# gives: the reader leaves an unclosed file and unittest's warning filters would
# put the ResourceWarning on a shared tool this suite is not here to fix.
#
# Address == image offset in each of these flat per-bank images, which is what
# make_bank_image.py arranges: the common area at 0x0000-0x7FFF and the bank's
# own window at 0x8000-0xFFFF. So a runtime address from a `.asm` listing is
# spelled out as itself below and no offset arithmetic happens anywhere in this
# file.
IMAGES = G.load_images()

# The three EC-side `mov dptr,#0x391` sites, as runtime addresses, with the
# access byte that follows each -- 0xF0 is `movx @dptr,a`, a write; 0xE0 is
# `movx a,@dptr`, a read. Transcribed from the listings rather than recomputed
# from a scan, because the point of the set comparison is to fail when the image
# and this list drift apart. check_register_counts.py is what licenses the
# method's recall on this image: it reproduces every `static_refs` field of
# every registers.yaml row from the same firmware.
SITES = {
    0xDBC5: 0xF0,   # FUN_CODE_db0b
    0xE171: 0xE0,   # FUN_CODE_e100
    0xE26A: 0xE0,   # gate_1c00_init_defaults
}

# The two `0x9EA1` callers, as the three bytes of the `lcall`.
CALLERS = (0xE182, 0xE276)


def sites_for(image, addr):
    """Every offset in `image` holding `90 <hi> <lo>`.

    The raw byte pattern rather than `trace_xdata_refs.sites_for()`, which
    applies walk-window rules; the reading is about which addresses the EC names
    at all, and those rules decide how a site is *labelled* rather than whether
    it exists.
    """
    needle = bytes((0x90, addr >> 8, addr & 0xFF))
    return {i for i in range(len(image) - 2) if image[i:i + 3] == needle}


def registers():
    with open(REGISTERS) as f:
        return {e['name']: e for e in yaml.safe_load(f)['registers']}


def census_addrs():
    with open(CENSUS) as f:
        return {row['addr'] for row in csv.DictReader(f)}


class TheSiteSet(unittest.TestCase):
    """Three EC-side sites for 0x0391, one write and two reads.

    Asserted as a set of (site, access byte) pairs rather than as a count, so a
    site that appeared or moved is a failure rather than silent drift. The
    direction is read out of the byte after the three-byte load, which is what
    makes the `registers.yaml` row's read/write columns a reading of the image
    rather than an assertion about it.
    """

    def test_the_three_sites_and_their_directions(self):
        self.assertEqual(sites_for(IMAGES['bank1'], 0x0391), set(SITES))
        for addr, access in SITES.items():
            self.assertEqual(
                IMAGES['bank1'][addr + 3], access,
                "0x%04X is not the %s the row claims" % (addr, access))

    def test_no_pd_site_and_the_other_banks_are_covered(self):
        # The split `trace_xdata_refs.py` makes is what keeps a site in the
        # ITE8850-PD image out of the EC-side set; 0x0391 having none is a
        # property of the image, and the per-bank comparison is what makes it
        # one rather than an absence of looking.
        for program in ('bank0', 'pd'):
            self.assertEqual(sites_for(IMAGES[program], 0x0391), set(),
                             "0x0391 has a site in the %s image" % program)

    def test_each_site_is_one_byte_wide(self):
        # Width: the load is followed immediately by the access, with no
        # `inc dptr` between them, so none of the three is the seed of a
        # sequential pair walk. That is the claim the row's one-byte reading
        # rests on; a walk would make the direction a question about the walk
        # rather than about the two bytes named here.
        for addr in SITES:
            self.assertNotEqual(IMAGES['bank1'][addr + 4], 0xA3,
                                "0x%04X starts a pair walk" % addr)


class WhatTheWriterStores(unittest.TestCase):
    """`0x0391` takes the block poll's result, not the routine's argument.

    This is the write-up's second correction of a committed decompile:
    `DB0B.c:73` reads `DAT_EXTMEM_0391 = param_1`, and `param_1` is R3 only
    until the poll above the store overwrites it. Three byte facts make the
    correction rather than an assertion.
    """

    def test_the_store_takes_r3(self):
        # DB0B.asm:100-102 -- `mov a,r3` immediately before `mov dptr,#0x391`
        # and `movx @dptr,a`.
        self.assertEqual(IMAGES['bank1'][0xDBC4:0xDBC9],
                         bytes((0xEB, 0x90, 0x03, 0x91, 0xF0)))

    def test_the_poll_overwrites_r3_from_1c04(self):
        # C4F0.asm:36-38 -- `mov dptr,#0x1c04`, `movx a,@dptr`, `mov r3,a`.
        self.assertEqual(IMAGES['bank1'][0xC52C:0xC531],
                         bytes((0x90, 0x1C, 0x04, 0xE0, 0xFB)))

    def test_nothing_between_the_poll_and_the_store_touches_r3(self):
        # The poll's only callee on the way out is 0xC541, which opens
        # `mov r7,#0x06` / `clr a` -- R7 and A only. Ghidra renders that call
        # with two arguments (C4F0.c:36), which is how R3 and R4 stay visible
        # in the C while the listing shows them being loaded here.
        self.assertEqual(IMAGES['bank1'][0xC541:0xC543],
                         bytes((0x7F, 0x06)))

    def test_carry_clear_is_the_success_return(self):
        # C4F0.asm:28-33 is the failure path and ends `setb cy`; :34-47 is the
        # success path and ends `clr cy`. DB0B.asm:98's `jnc 0xdbc4` therefore
        # lands on the store, which is the write-up's claim about which arm
        # writes the byte.
        self.assertEqual(IMAGES['bank1'][0xC526], 0xD3)   # setb cy
        self.assertEqual(IMAGES['bank1'][0xC53F], 0xC3)   # clr cy
        self.assertEqual(IMAGES['bank1'][0xDBBD:0xDBC1],
                         bytes((0x50, 0x05, 0x80, 0x39)))


class TheBranchInstruction(unittest.TestCase):
    """`E100.asm:81` is `85 01 00`, and direct `0x00` is bank-0 R0 here.

    The write-up resolves the aliasing question the committed decompile answers
    two ways, and it resolves it from two independent byte facts: the opcode's
    own operand order, and the register-pair moves at `A5E6` that only
    type-check if `0x00`-`0x07` are the bank-0 registers. Both are asserted,
    because the conclusion (`0x0386` receives the larger of the two) is the
    strongest new statement in the write-up and rests on them.
    """

    def test_the_branch_is_mov_direct_direct(self):
        self.assertEqual(IMAGES['bank1'][0xE18A:0xE18D],
                         bytes((0x85, 0x01, 0x00)))

    def test_r0_is_written_and_read_around_it(self):
        # `mov r0,a` at E100.asm:69 and `mov a,r0` at :91, with the branch
        # between them. This is what makes the branch live rather than a store
        # to a byte nothing reads -- the same argument the sibling XDATA_0390
        # row makes for its own dead R2 store.
        self.assertEqual(IMAGES['bank1'][0xE175], 0xF8)   # mov r0,a
        self.assertEqual(IMAGES['bank1'][0xE1A0], 0xE8)   # mov a,r0

    def test_the_aliasing_crosscheck_moves_register_pairs(self):
        # A5E6.asm:41-44, read by A5E6.c:44-47 as BANK0_R2 = BANK0_R5 and the
        # three beside it. Four back-to-back `mov direct,direct` over
        # 0x00-0x07 are register moves -- R2:=R5, R1:=R0, R4:=R7, R3:=R6, two
        # 16-bit ones, not a swap; anything but the bank-0 register file would
        # make those bytes a scratch area and the sequence meaningless. The
        # order is asserted rather than the reading: it is what decides whether
        # R0 is written at all, which is the half a swap gets wrong.
        self.assertEqual(IMAGES['bank1'][0xA613:0xA61F],
                         bytes((0x85, 0x05, 0x02, 0x85, 0x00, 0x01,
                                0x85, 0x07, 0x04, 0x85, 0x06, 0x03)))

    def test_nothing_switches_the_register_bank_between_them(self):
        # The aliasing the previous three tests rely on spans `mov r0,a` at
        # E100.asm:69 through `mov a,r0` at :91, so the absence of a PSW write
        # is asserted over that whole span rather than over the branch window
        # alone. Decoded instruction by instruction rather than by scanning for
        # opcode bytes, because a byte cannot be told from an operand: 0x85 is
        # the branch under test and 0xc5 is the low byte of the `mov dptr,#0x03c5`
        # at :75, and neither is the opcode being looked for.
        #
        # What is excluded, in disasm8051.py's own vocabulary: anything naming
        # `psw`, and any instruction whose direct operand is in 0xD0-0xD7 --
        # `mov`/`push`/`pop`/`xch`/`clr` all take a direct, and the decoder
        # prints it bare (`pop  0xd0`, `clr  0xd4`), with or without a trailing
        # comma depending on the form. Only `setb` renders through BIT_SFR
        # (`setb psw.0`), so both spellings are checked. 0xD5 is
        # `djnz direct,rel` here and is not a PSW writer; checking the decoded
        # operand rather than a tuple of opcode bytes is what keeps this from
        # needing that tuple kept in step with the decoder by hand, and it is
        # what lets the check see a `pop`/`push` of PSW at all.
        body = list(disasm8051.decode(IMAGES['bank1'], 0xE175, count=30,
                                      addr=0xE175))
        body = [ins for ins in body if ins[0] <= 0xE1A0]
        self.assertTrue(body)
        psw_bit = re.compile(r'\bpsw\.')
        psw_direct = re.compile(r'\b0xd[0-7]\b')
        for addr, _, text in body:
            self.assertIsNone(psw_bit.search(text),
                              "0x%04X writes a PSW bit: %s" % (addr, text))
            if text.split()[0] in ('mov', 'push', 'pop', 'xch', 'clr'):
                self.assertIsNone(
                    psw_direct.search(text),
                    "0x%04X writes PSW: %s" % (addr, text))
        # The two bit tests are ACC bits, not PSW bits: 0xE0-0xE7 is the
        # accumulator and 0xD0-0xD7 is PSW, per disasm8051.py's BIT_SFR. They
        # are read, not written, and cannot affect aliasing either way -- this
        # asserts they are the ACC tests the write-up says they are, so a
        # reading that made them bank selectors would fail here.
        self.assertEqual(IMAGES['bank1'][0xE196:0xE199],
                         bytes((0x20, 0xE4, 0x3B)))
        self.assertEqual(IMAGES['bank1'][0xE19D:0xE1A0],
                         bytes((0x20, 0xE3, 0x34)))
        acc_tests = {ins[2].split()[1].split(',')[0]
                     for ins in body if ins[2].startswith('jb')}
        self.assertEqual(acc_tests, {'acc.3', 'acc.4'})
        # The write-up's claim about this span is a claim about its calls, so
        # it is asserted rather than read off the listing: `lcall 0x9ea1` at
        # :76 is the only one. A call that returned without touching PSW would
        # slip past the loop above, which is why the call set is checked and
        # not just the absence of a bank write.
        self.assertEqual({ins[2].split()[1] for ins in body
                          if ins[2].split()[0] == 'lcall'},
                         {'0x9ea1'})

    def test_the_filter_does_not_switch_the_bank_either(self):
        # The `lcall 0x9ea1` at E100.asm:76 is the only call inside the R0
        # span, so the write-up's "no instruction writes PSW" claim covers the
        # callee's 39 instructions too. It keeps its accumulator in R5 and its
        # address in direct 0x83/0x82, and touches neither PSW nor 0xD0.
        callee = list(disasm8051.decode(IMAGES['bank1'], 0x9EA1, count=39,
                                        addr=0x9EA1))
        self.assertEqual(len(callee), 39)
        for addr, _, text in callee:
            self.assertNotIn('psw', text,
                             "0x%04X writes a PSW bit: %s" % (addr, text))
            self.assertIsNone(re.search(r'\b0xd[0-7]\b', text),
                              "0x%04X names PSW: %s" % (addr, text))

    def test_the_other_callee_does_not_switch_the_bank_either(self):
        # The write-up claims more than the R0 span: that no instruction in
        # FUN_CODE_e100's whole listing extent writes PSW. That claim needs the
        # routine's other calls accounted for, not just its filter call --
        # `lcall 0x888c` at E100.asm:106 and :108. So the call set is pinned
        # rather than assumed: any callee beyond these two, anywhere in the
        # extent, would reopen the claim, and the assertion below is what fails.
        listing = [ins for ins in
                   disasm8051.decode(IMAGES['bank1'], 0xE100, count=300,
                                     addr=0xE100)
                   if ins[0] <= 0xE1D4]
        # The window has to reach the last instruction of the listing extent,
        # or "every call in the extent" would be a claim about a prefix.
        self.assertEqual(listing[-1][0], 0xE1D4)
        self.assertEqual({ins[2].split()[1] for ins in listing
                          if ins[2].split()[0] == 'lcall'},
                         {'0x9ea1', '0x888c'})
        # 0x888C is six instructions that move R1 and R2 out to the XDATA pair
        # at DPTR; it names no PSW and no direct 0xD0, which is what lets the
        # wider claim stand.
        callee = list(disasm8051.decode(IMAGES['bank1'], 0x888C, count=6,
                                        addr=0x888C))
        self.assertEqual(len(callee), 6)
        self.assertEqual(callee[-1][2].split()[0], 'ret')
        for addr, _, text in callee:
            self.assertNotIn('psw', text,
                             "0x%04X writes a PSW bit: %s" % (addr, text))
            self.assertIsNone(re.search(r'\b0xd[0-7]\b', text),
                              "0x%04X names PSW: %s" % (addr, text))


class TheFilterAndItsCallers(unittest.TestCase):
    """`0x9EA1` is 39 instructions, has two callers, and never reads R2."""

    def test_two_callers_and_no_others(self):
        lcall = bytes((0x12, 0x9E, 0xA1))
        found = {i for i in range(len(IMAGES['bank1']) - 2)
                 if IMAGES['bank1'][i:i + 3] == lcall}
        self.assertEqual(found, set(CALLERS))

    def test_each_caller_hands_over_its_own_pair_and_accumulator(self):
        # E100.asm:75-76 loads DPTR 0x03C5 and calls; E237.asm:38-39 loads
        # 0x03C7. The accumulators are R3:R4, built by the `mov r4,dph` /
        # `mov r3,dpl` pair (0xAC 0x83 / 0xAB 0x82) either site.
        self.assertEqual(IMAGES['bank1'][0xE17F:0xE185],
                         bytes((0x90, 0x03, 0xC5, 0x12, 0x9E, 0xA1)))
        self.assertEqual(IMAGES['bank1'][0xE273:0xE279],
                         bytes((0x90, 0x03, 0xC7, 0x12, 0x9E, 0xA1)))
        for addr in (0xE17B, 0xE26F):
            self.assertEqual(IMAGES['bank1'][addr:addr + 4],
                             bytes((0xAC, 0x83, 0xAB, 0x82)))

    def test_thirty_nine_instructions_and_the_pair_shift(self):
        body = list(disasm8051.decode(IMAGES['bank1'], 0x9EA1, count=39,
                                      addr=0x9EA1))
        self.assertEqual(len(body), 39)
        self.assertEqual(body[-1][2].split()[0], 'ret')
        # 9EA1.asm:9-15: R1 into the low byte of the pair, `inc dptr`, the old
        # low byte into the high byte. This is the two-byte shift with a byte
        # injected that the write-up's first section is about, and it is why
        # 0x03C6 and 0x03C8 need no literal site of their own.
        self.assertEqual(IMAGES['bank1'][0x9EA3:0x9EAA],
                         bytes((0xE9, 0xF0, 0xA3, 0xE0, 0xFF, 0xEE, 0xF0)))

    def test_it_never_reads_r2(self):
        # The dead-store argument, for both accumulators' rows: 0x9EA1's
        # operands are R1, R3, R4, R5, R6 and R7 and none of its 39
        # instructions names R2 (0xEA is `mov a,r2`).
        body = IMAGES['bank1'][0x9EA1:0x9ED4]
        self.assertNotIn(0xEA, body)

    def test_e237s_r2_store_is_the_dead_one(self):
        # E237.asm:35 is `mov r2,a` right after the read, and :100 has no
        # consumer for it -- the call's return goes to 0x0387 instead.
        self.assertEqual(IMAGES['bank1'][0xE26E:0xE273],
                         bytes((0xFA, 0xAC, 0x83, 0xAB, 0x82)))
        self.assertEqual(IMAGES['bank1'][0xE279:0xE27D],
                         bytes((0x90, 0x03, 0x87, 0xF0)))


class TheTablesCarryTheRow(unittest.TestCase):
    """Both bytes have a registers.yaml row and the three site rows."""

    def test_both_rows_are_present_untested(self):
        table = registers()
        for name in ('XDATA_0390', 'XDATA_0391'):
            self.assertIn(name, table)
            self.assertEqual(table[name]['status'], 'present-untested')
            for key in ('static_refs', 'static_refs_main_ec',
                        'static_refs_pd_image'):
                self.assertIn(key, table[name])

    def test_the_new_row_matches_its_sites(self):
        row = registers()['XDATA_0391']
        self.assertEqual(row['static_refs'], len(SITES))
        self.assertEqual(row['static_refs_main_ec'], len(SITES))
        self.assertEqual(row['static_refs_pd_image'], 0)

    def test_site_resolution_carries_one_row_per_site(self):
        with open(SITE_RESOLUTION) as f:
            rows = [r for r in csv.DictReader(f) if r['addr'] == '0x0391']
        self.assertEqual(
            {(int(r['runtime'], 16), r['resolution']) for r in rows},
            {(addr, 'write' if acc == 0xF0 else 'read')
             for addr, acc in SITES.items()})

    def test_the_0390_pin_still_holds(self):
        # #259's row is in registers.yaml while the census still reaches the
        # address by no C-level token, so the two disagree on purpose. A
        # re-export would close that gap and move the census, and this test is
        # the tripwire saying that is a scope expansion rather than a cleanup.
        self.assertIn('XDATA_0390', registers())
        self.assertNotIn('0x0390', census_addrs())
        self.assertIn('0x0391', census_addrs())


# Phrasings that assert an observation was made at the machine. Each is
# affirmative by construction, so a sentence that *denies* one -- which is what
# both documents must do -- cannot match it. The point is that the calibration
# rule is enforced here rather than trusted to the author: there is no laptop in
# this pipeline, so any affirmative form here is a fabrication.
LIVE_CLAIMS = re.compile(
    r"we observed"
    r"|observed on the (?:machine|laptop|hardware)"
    r"|live test (?:confirm|show|proved|verif|establish)"
    r"|readback (?:confirm|match|show)"
    r"|confirmed on the (?:machine|laptop|hardware)"
    r"|(?:on|at) the (?:real |actual )?(?:machine|laptop|hardware),"
    r"|(?:reading|reading back) (?:it |them |the byte )?on the (?:machine|hardware)",
    re.IGNORECASE)


class TheCalibration(unittest.TestCase):
    """Neither document claims a live observation, and both say so."""

    def assertNoLiveClaim(self, text, what):
        hit = LIVE_CLAIMS.search(text)
        self.assertIsNone(hit, "%s asserts a live observation: %r"
                          % (what, hit.group(0) if hit else ''))

    def test_the_write_up_denies_one_instead_of_claiming_one(self):
        text = FINDINGS.read_text()
        self.assertNoLiveClaim(text, "the write-up")
        self.assertIn("No live test was run", text)

    def test_the_register_note_denies_one_too(self):
        note = registers()['XDATA_0391']['note']
        self.assertNoLiveClaim(note, "the XDATA_0391 note")
        self.assertIn("no live test was run", note)


if __name__ == '__main__':
    unittest.main()