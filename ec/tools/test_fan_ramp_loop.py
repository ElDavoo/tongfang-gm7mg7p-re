#!/usr/bin/env python3
"""The fan ramp is a closed loop, and this suite holds the citations that say so.

`docs/findings/fan-ramp-control-loop.md` is the write-up. It is a static
reading of `ec/firmware/GMxMGxx_11.800` and nothing in this suite runs on
hardware, reads a register back, or observes a fan; what is checked here is
that the write-up's per-site reading still matches the committed listings it
cites, which is the calibration rule made mechanical.

**Why a citation check and not a decode.** The write-up's claim is a reading of
specific instructions at specific addresses -- `0x8B32 lcall 0xBB5E` is the
setpoint lookup, `0x8B76 jnb 0xe7` picks the integrator's direction, `0x8B11
ljmp 0x8C46` publishes. A prose sentence asserting those cannot fail when the
firmware or an export moves under it, so each is transcribed here as
(address, mnemonic) and resolved against the listing the write-up names. An
instruction that moves, changes opcode or disappears reds here instead of
silently making the write-up wrong.

**Nothing here is asserted as a count of the tree.** No test holds how many
addresses the write-up cites, how many listings it opens, or how many
instructions the loop has; those are values every landing branch would have to
edit (CLAUDE.md, "No totals of the repository's own text"). The cases hold
relations and properties: each cited address exists, each cited mnemonic is the
one there, the two controllers are reached from the arms the write-up says,
and the gate that separates them is the pair of enable bits.

**The image check is scoped to the one claim a listing cannot carry.** The
`0xBB56`/`0xBBDE` ordering claim rests on `B5D3.asm`, whose own header says the
function boundary is a byte-scan hypothesis. So that window — one of the five
ladders §3a reads, and the one it decodes from the image — is additionally
decoded straight out of the committed firmware with `disasm8051.py` and the
result compared, which is what catches an export that has drifted from the
image. `--converge` is asked for and its answer printed rather than asserted to
a figure: it measures how many nearby anchors decode onto an offset, which is
evidence about framing and not proof of it.

This suite is not in `.github/scripts/agent-gates.sh`, and cannot be from an
agent branch; it is run by `bash tools/run-tests.sh`, which discovers every
`test_*.py` in the tree.
"""

import csv
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
DECOMPILED = REPO / 'ec' / 'decompiled'
BANK0 = DECOMPILED / 'bank0'
ANNOTATIONS = REPO / 'ec' / 'annotations'
FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
FUNCTIONS_CSV = ANNOTATIONS / 'ghidra-functions.csv'
WRITEOUT = REPO / 'docs' / 'findings' / 'fan-ramp-control-loop.md'
DISASM = HERE / 'disasm8051.py'

# `8B32     12 bb 5e lcall    0xbb5e` -- address, a fixed three-slot byte
# column, then the mnemonic and a free-text operand. The byte column is
# left-justified to nine characters, so it cannot be split on whitespace
# without being told where it ends; three slots is the widest an instruction
# in these listings gets.
INSN = re.compile(r'^([0-9A-F]{4})\s+(.*)$')
BYTE_SLOT = re.compile(r'^(?:[0-9a-f]{2}|-)$')

# The two integrator bytes both controllers step, and the two controller
# routines that step them.
CPU_INTEGRATOR = 0x0460
GPU_INTEGRATOR = 0x0468

# (listing stem, address, mnemonic, operand) for each instruction the
# write-up's per-site reading names, grouped by the section that reads it so
# a red case says which reading broke rather than only which address moved.
# The operand is checked as well as the mnemonic: `lcall 0xBDE6` and
# `lcall 0xBCDA` are the same instruction reading two different tables, and a
# mnemonic-only check would not tell those apart.
BLOCK_FIVE = [
    ('8931', 0x8A25, 'mov', 'DPTR, #0x741'),
    ('8931', 0x8A29, 'jb', '0xe0, 0x8a2f'),
    ('8931', 0x8A2C, 'ljmp', '0x8b14'),
    ('8931', 0x8A33, 'jb', '0xe2, 0x8a39'),
    ('8931', 0x8A36, 'ljmp', '0x8b14'),
    ('8931', 0x8A39, 'mov', 'DPTR, #0x460'),
    ('8931', 0x8A40, 'jnc', '0x8a98'),
    ('8931', 0x8A42, 'lcall', '0xbde6'),
    ('8931', 0x8A9B, 'lcall', '0xbde6'),
    ('8931', 0x8A9F, 'mov', 'DPTR, #0x43e'),
    ('8931', 0x8AA4, 'subb', 'A, R7'),
    ('8931', 0x8AAB, 'inc', 'A'),
    ('8931', 0x8ABD, 'mov', 'DPTR, #0x460'),
    ('8931', 0x8ACF, 'mov', 'DPTR, #0x468'),
    ('8931', 0x8ADD, 'lcall', '0xbdf2'),
    ('8931', 0x8AE6, 'inc', 'A'),
    ('8931', 0x8AF8, 'lcall', '0xbdf2'),
    ('8931', 0x8B01, 'dec', 'A'),
    # The DPTR half of the publish. `clr A` at 0x8B0B is opcode 0xE4 and clears
    # only the accumulator, leaving CY as `add A,#0x50` at 0x8B07 set it, so
    # `addc A,#0xf` at 0x8B0C adds the low half's overflow into the high one.
    # Read without those two, `mov DPH, A` looks like it copies the same byte
    # into both halves of DPTR, so these are transcribed whole rather than only
    # at the two `mov`s.
    ('8931', 0x8B09, 'mov', 'DPL, A'),
    ('8931', 0x8B0B, 'clr', 'A'),
    ('8931', 0x8B0E, 'mov', 'DPH, A'),
    ('8931', 0x8B10, 'movx', 'A, @DPTR'),
    ('8931', 0x8B11, 'ljmp', '0x8c46'),
]

DWELL_ARM = [
    ('8B14', 0x8B14, 'mov', 'DPTR, #0x460'),
    ('8B14', 0x8B18, 'setb', 'CY'),
    ('8B14', 0x8B19, 'subb', 'A, #0x3'),
    ('8B14', 0x8B1B, 'jnc', '0x8b88'),
    ('8B14', 0x8B1D, 'mov', 'DPTR, #0xa47'),
    ('8B14', 0x8B20, 'lcall', '0xb987'),
    ('8B14', 0x8B23, 'lcall', '0xbce9'),
    ('8B14', 0x8B26, 'push', 'DPH'),
    ('8B14', 0x8B2A, 'mov', 'DPTR, #0x460'),
    ('8B14', 0x8B30, 'pop', 'DPH'),
    ('8B14', 0x8B32, 'lcall', '0xbb5e'),
    ('8B14', 0x8B35, 'mov', 'R5, A'),
    ('8B14', 0x8B36, 'mov', 'DPTR, #0x43e'),
    ('8B14', 0x8B3B, 'subb', 'A, R5'),
    ('8B14', 0x8B3E, 'lcall', '0xbc5f'),
    ('8B14', 0x8B44, 'mov', 'A, #0x80'),
    ('8B14', 0x8B4B, 'xrl', 'A, #0x3'),
    ('8B14', 0x8B52, 'mov', 'A, #0xff'),
    # The two `sjmp`s are what keep the up arm out of the down one: 0x8B55
    # leaves the integrator-3 force for the gate, and 0x8B7C leaves the `inc`
    # for the clear. Without either transcribed, the block reads as one arm
    # falling into the other.
    ('8B14', 0x8B55, 'sjmp', '0x8b6d'),
    ('8B14', 0x8B6D, 'lcall', '0xbeaa'),
    ('8B14', 0x8B70, 'jc', '0x8bbc'),
    ('8B14', 0x8B76, 'jnb', '0xe7, 0x8b7e'),
    ('8B14', 0x8B7A, 'inc', 'A'),
    # The up arm does not fall into the down arm. `0x8B7C` jumps over it to the
    # clear at `0x8B81`; without this row transcribed, a listing that lost the
    # `sjmp` would still pass while the write-up's block read as `inc`
    # immediately followed by `dec` back into the same byte.
    ('8B14', 0x8B7C, 'sjmp', '0x8b81'),
    ('8B14', 0x8B7F, 'dec', 'A'),
    ('8B14', 0x8B85, 'movx', '@DPTR, A'),
]

# 0xBC4F's correction, transcribed whole: the routine copies two bytes. The
# negative half of that claim -- that it computes no offset -- is held by the
# arithmetic case below rather than by an absence here, because `inc DPTR`
# does appear and is the pointer walk rather than a value offset.
BC4F_COPY = [
    (0xBC4F, 'mov', 'DPTR, #0x8e6'),
    (0xBC52, 'movx', 'A, @DPTR'),
    (0xBC56, 'mov', 'DPTR, #0xa47'),
    (0xBC59, 'xch', 'A, R7'),
    (0xBC5C, 'mov', 'A, R7'),
    (0xBC5E, 'ret', ''),
]

# The two dereferences between `0x8B1D`'s `mov DPTR, #0xa47` and the setpoint
# lookup at `0xBB5E`, transcribed from the listings the write-up names.
#
# Both calls are split by the byte-scan seeding, each into two census entries
# that between them hold the routine and neither of which reaches its `ret`:
# `0xB987` is two bytes and runs on into `0xB989`, and `0xBCE9` is five and runs
# on into `0xBCEE`. Reading either entry as the whole routine is what makes the
# XDATA byte at `0x0A47` look discarded -- `0xBCE9` does overwrite R6 three
# bytes later, but with a CODE byte and after `0xB98D` has already moved the
# XDATA one into DPH -- which in turn makes the pair look like a CODE address
# rather than an XDATA one. The test below holds both halves of that.
POINTER_PAIR_READ = [
    ('B987', 0xB987, 'movx', 'A, @DPTR'),
    ('B987', 0xB988, 'mov', 'R6, A'),
    ('B989', 0xB989, 'inc', 'DPTR'),
    ('B989', 0xB98A, 'movx', 'A, @DPTR'),
    ('B989', 0xB98B, 'mov', 'DPL, A'),
    ('B989', 0xB98D, 'mov', 'DPH, R6'),
    ('B989', 0xB98F, 'ret', ''),
]

POINTER_DEREFERENCE = [
    ('BCE9', 0xBCE9, 'clr', 'A'),
    ('BCE9', 0xBCEA, 'movc', 'A, @A+DPTR'),
    ('BCE9', 0xBCEB, 'mov', 'R6, A'),
    ('BCEE', 0xBCEE, 'movc', 'A, @A+DPTR'),
    ('BCEE', 0xBCEF, 'mov', 'R7, A'),
    ('BCEE', 0xBCF0, 'mov', 'DPL, A'),
    ('BCEE', 0xBCF2, 'mov', 'DPH, R6'),
    ('BCEE', 0xBCF4, 'ret', ''),
]

# The ladder that orders 0xBB56 against 0xBBDE, in the listing the write-up
# cites and, independently, in the image (see the image case below). The
# `mov DPL,R7` / `mov DPH,R6` restore is transcribed rather than elided: both
# routines leave DPTR at 0x043E / 0x044F, so without it the second
# `movc A,@A+DPTR` could not index the same table.
LADDER = [
    (0xB6F4, 'mov', 'A, #0x7'),
    (0xB6F7, 'lcall', '0xbb56'),
    (0xB6FA, 'jnc', '0xb736'),
    (0xB6FC, 'mov', 'DPL, R7'),
    (0xB6FE, 'mov', 'DPH, R6'),
    (0xB700, 'mov', 'A, #0x8'),
    (0xB703, 'lcall', '0xbbde'),
    (0xB706, 'jnc', '0xb736'),
    (0xB70E, 'mov', 'A, #0x9'),
    (0xB711, 'lcall', '0xbda6'),
    (0xB714, 'jnc', '0xb736'),
]

# The other four ladders §3a reads, each with the listing that owns it.
#
# `0xBB55` and `0xBB56` are one routine and `0xBBDD` and `0xBBDE` another, each
# split by the byte-scan seeding: 0xBB55 is `setb CY` at the byte before
# 0xBB56's `movc A,@A+DPTR`, and 0xBBDD is the same byte before 0xBBDE. The
# census carries a row per entry byte, so an inbound count against 0xBB56 and
# 0xBBDE alone misses every site that entered a byte earlier -- the reason
# §3a collects its callers over all four entry bytes and finds five ladders in
# three seeded routines rather than three sites in two.
#
# What is held here is the property, not that census: each site below resolves
# to the listing named beside it, and the five do not share one.
LADDER_B4A8 = [
    (0xB50B, 'lcall', '0xb93d'),
    (0xB50E, 'clr', 'A'),
    (0xB50F, 'lcall', '0xbb55'),
    (0xB512, 'jnc', '0xb522'),
    (0xB514, 'mov', 'DPL, R7'),
    (0xB516, 'mov', 'DPH, R6'),
    (0xB518, 'mov', 'A, #0x1'),
    (0xB51A, 'lcall', '0xbbde'),
    (0xB51D, 'jnc', '0xb522'),
    (0xB51F, 'ljmp', '0xb5d2'),
]

LADDER_B4A8_SECOND = [
    (0xB56B, 'mov', 'A, #0x2'),
    (0xB56D, 'lcall', '0xbb55'),
    (0xB570, 'jc', '0xb59c'),
    (0xB572, 'mov', 'DPL, R7'),
    (0xB574, 'mov', 'DPH, R6'),
    (0xB576, 'mov', 'A, #0x3'),
    (0xB578, 'lcall', '0xbbdd'),
    (0xB57B, 'jc', '0xb59c'),
]

LADDER_B5D3_FIRST = [
    (0xB668, 'mov', 'A, #0x4'),
    (0xB66A, 'lcall', '0xbb55'),
    (0xB66D, 'jnc', '0xb672'),
    (0xB672, 'mov', 'DPL, R7'),
    (0xB674, 'mov', 'DPH, R6'),
    (0xB676, 'mov', 'A, #0x5'),
    (0xB678, 'lcall', '0xbbdd'),
    (0xB67B, 'jnc', '0xb680'),
    (0xB686, 'mov', 'A, #0x6'),
    (0xB688, 'lcall', '0xbda5'),
]

LADDER_B737 = [
    (0xB7C8, 'mov', 'A, #0xc'),
    (0xB7CA, 'lcall', '0xbb55'),
    (0xB7CD, 'jc', '0xb7fc'),
    (0xB7CF, 'mov', 'DPL, R7'),
    (0xB7D1, 'mov', 'DPH, R6'),
    (0xB7D3, 'mov', 'A, #0xd'),
    (0xB7D5, 'lcall', '0xbbdd'),
    (0xB7D8, 'jc', '0xb835'),
    (0xB7E0, 'mov', 'A, #0xe'),
    (0xB7E3, 'lcall', '0xbc37'),
]

# How many instructions `disasm8051.py` is asked for when the window that
# carries the whole ladder is decoded from its first instruction. Derived
# from the listing rather than tuned: it is the span of LADDER's addresses,
# so a row added above widens this with it rather than silently falling off
# the end of the decode.
LADDER_SPAN = (LADDER[-1][0] - LADDER[0][0]) // 2 + 1


def parse_listing(path):
    """Every instruction in one listing, keyed by address.

    Mirrors the parser `test_044b_mode_stepper.py` uses, so a listing that
    one suite reads is read the same way here: the byte column is three
    fixed slots and anything that does not match is not an instruction.
    """
    insns = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        match = INSN.match(line)
        if not match:
            continue
        fields = match.group(2).split()
        if len(fields) < 4 or not all(BYTE_SLOT.match(f) for f in fields[:3]):
            continue
        insns[int(match.group(1), 16)] = (fields[3].lower(),
                                          ' '.join(fields[4:]))
    return insns


class ListingCache:
    """Parsed listings, read once and shared by every case that wants one."""

    def __init__(self):
        self._cache = {}

    def get(self, stem):
        if stem not in self._cache:
            path = BANK0 / (stem + '.asm')
            if not path.exists():
                raise AssertionError('no committed listing at %s' % path)
            self._cache[stem] = parse_listing(path)
        return self._cache[stem]


LISTINGS = ListingCache()


def cited_insn(stem, addr, mnemonic, operand):
    """Assert one cited instruction is in the listing, and return it.

    The operand is compared too, because the write-up quotes these operands
    and a mnemonic-only match would let them drift unnoticed. Both sides are
    case-folded: the export prints register names upper case (`A, R7`,
    `@DPTR, A`) and the citations above are written the same way, so folding
    keeps the comparison about the operand rather than about capitalisation.
    """
    insns = LISTINGS.get(stem)
    if addr not in insns:
        raise AssertionError(
            '%s.asm has no instruction at 0x%04X, which '
            'docs/findings/fan-ramp-control-loop.md cites there'
            % (stem, addr))
    found_mnemonic, found_operand = insns[addr]
    if found_mnemonic != mnemonic:
        raise AssertionError(
            '0x%04X in %s.asm is %r, not the %r the write-up cites'
            % (addr, stem, found_mnemonic, mnemonic))
    if operand is not None and found_operand.lower() != operand.lower():
        raise AssertionError(
            '0x%04X in %s.asm has operand %r, not the %r the write-up cites'
            % (addr, stem, found_operand, operand))
    return found_mnemonic, found_operand


class FanRampCitations(unittest.TestCase):
    """Every address the write-up's per-site reading names, resolved."""

    def test_block_five_of_8931_is_the_xdata_table_controller(self):
        for stem, addr, mnemonic, operand in BLOCK_FIVE:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn(stem, addr, mnemonic, operand)

    def test_the_dwell_arm_of_8b14_is_the_code_table_controller(self):
        for stem, addr, mnemonic, operand in DWELL_ARM:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn(stem, addr, mnemonic, operand)

    def test_bc4f_copies_two_bytes_and_computes_no_offset(self):
        for addr, mnemonic, operand in BC4F_COPY:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn('BC4F', addr, mnemonic, operand)

    def test_the_pointer_pair_is_xdata_on_both_sides(self):
        """`0xBC4F` writes XDATA `0x0A47`/`0x0A48`; `0x8B14` reads XDATA too.

        This is the linkage §5 draws, and the address space is the whole of
        it: same number, one space, so the routine that writes the pair is on
        the path that decides where this controller reads its setpoints from.
        Held as three relations rather than as prose, each of which fails if
        the firmware or an export moves.

        The load is `movx`, not `movc`, at both ends -- `0xBC4F` stores with
        `movx @DPTR, A` and `0xB987` loads with `movx A, @DPTR`. A `movc` on
        either side would put the two in different address spaces at the same
        numeric address and break the claim.
        """
        for addr, mnemonic, operand in BC4F_COPY:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn('BC4F', addr, mnemonic, operand)
        self.assertEqual(LISTINGS.get('BC4F')[0xBC5A][0], 'movx',
                         '0xBC4F must store the pair with movx into XDATA')
        self.assertEqual(LISTINGS.get('B987')[0xB987][0], 'movx',
                         '0x8B14 must read the pair with movx from XDATA')

        # And nothing between `0x8B1D` and the `push` reads CODE at 0x0A47, so
        # the same address in the other address space is not what the setpoint
        # path uses. A `movc` here would fetch the CODE bytes at 0x0A47 and
        # make the pair a CODE address instead of an XDATA one.
        window = {addr: insn for addr, insn in LISTINGS.get('8B14').items()
                  if 0x8B1D <= addr <= 0x8B26}
        self.assertTrue(window, '8B14.asm has nothing in the window at all')
        for addr, (mnemonic, _) in sorted(window.items()):
            with self.subTest(addr='0x%04X' % addr):
                self.assertNotEqual(mnemonic, 'movc',
                                    '0x%04X reads CODE at DPTR before the table '
                                    'pointer is pushed' % addr)

    def test_the_setpoint_path_dereferences_the_pair_twice(self):
        """The two calls each run past their census entry into the next one.

        `0xB987` is seeded at two bytes and `0xBCE9` at five, neither with a
        `ret`, so both listings stop mid-routine and each run-on lands in the
        entry seeded at the next address -- `0xB989 finish_dptr_be16_load` and
        `0xBCEE dptr_from_code_be16`. Taking either entry as the whole routine
        drops the run-on: `0xB987` alone looks like a bare XDATA read whose R6
        is then overwritten three bytes later by `0xBCE9`, which would make the
        XDATA load dead and the pair a CODE address.

        So each seed is held to being shorter than its routine, and the `ret`
        that ends each routine is held to be the one in the entry the run-on
        landed in.
        """
        for stem, addr, mnemonic, operand in POINTER_PAIR_READ:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn(stem, addr, mnemonic, operand)
        for stem, addr, mnemonic, operand in POINTER_DEREFERENCE:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn(stem, addr, mnemonic, operand)

        # The seed is shorter than the routine: the run-on is what is missing
        # from the seeded range, so a census entry that grew to cover its own
        # `ret` would mean the split this reading depends on is gone.
        self.assertNotIn(0xB98F, LISTINGS.get('B987'),
                         'B987.asm now reaches its own ret, so the two census '
                         'entries have been merged')
        self.assertNotIn(0xBCF4, LISTINGS.get('BCE9'),
                         'BCE9.asm now reaches its own ret, so the seeded '
                         'entry is no longer short of its routine')
        self.assertIn(0xB989, LISTINGS.get('B989'),
                      'B989.asm should carry the run-on of 0xB987')
        self.assertIn(0xBCEE, LISTINGS.get('BCEE'),
                      'BCEE.asm should carry the run-on of 0xBCE9')

        # And the XDATA byte is consumed by the run-on, not left in R6 for
        # 0xBCE9 to overwrite: `0xB98D` is what puts it in DPH.
        self.assertEqual(LISTINGS.get('B989')[0xB98D][1].lower(), 'dph, r6',
                         'the run-on must move the XDATA byte into DPH, or the '
                         'pair 0xBC4F writes is not what 0x8B14 reads')
        # The second dereference is CODE, which is why the pair is a pointer
        # to a pointer rather than the table itself.
        self.assertEqual(LISTINGS.get('BCE9')[0xBCEA][0], 'movc',
                         '0xBCE9 must read CODE, or there is no second '
                         'dereference')

    def test_the_ladder_reads_the_same_pair_as_a_second_consumer(self):
        """§3a's ladder reads the pair too, so it is not `0x8B14`'s alone."""
        cited_insn('B5D3', 0xB6EE, 'mov', 'DPTR, #0xa47')
        cited_insn('B5D3', 0xB6F1, 'lcall', '0xb93d')
        cited_insn('B93D', 0xB93D, 'movx', 'A, @DPTR')
        cited_insn('B93D', 0xB946, 'ret', '')

    def test_the_ladder_orders_the_two_threshold_routines_in_code_order(self):
        for addr, mnemonic, operand in LADDER:
            with self.subTest(addr='0x%04X' % addr):
                cited_insn('B5D3', addr, mnemonic, operand)

    def test_the_five_ladders_sit_in_three_seeded_routines(self):
        """The caller set is five ladders, not the three sites a count gives.

        An inbound-call count cannot tell you which routine made a call, and
        counted against `0xBB56`/`0xBBDE` alone it also misses every site that
        entered at `0xBB55`/`0xBBDD`, the byte before each. So §3a collects its
        callers over all four entry bytes and gets five ladders in three
        routines; what is held here is that each one resolves to the listing
        named beside it and that the five do not share one.
        """
        for ladder, (stem, first) in (
                (LADDER_B4A8, ('B4A8', 0xB50F)),
                (LADDER_B4A8_SECOND, ('B4A8', 0xB56D)),
                (LADDER, ('B5D3', 0xB6F7)),
                (LADDER_B5D3_FIRST, ('B5D3', 0xB66A)),
                (LADDER_B737, ('B737', 0xB7CA))):
            for addr, mnemonic, operand in ladder:
                with self.subTest(listing=stem, addr='0x%04X' % addr):
                    cited_insn(stem, addr, mnemonic, operand)
            with self.subTest(site='0x%04X' % first):
                self.assertEqual(BANK0_OWNER[first], 'bank0/%s.asm' % stem)

    def test_each_entry_byte_is_one_routine_with_its_neighbour(self):
        """Why the caller set is counted over four addresses, not two.

        `0xBB55` is `setb CY` at the byte before `0xBB56`, and `0xBBDD` the
        same byte before `0xBBDE`: each pair is one routine the byte-scan
        seeding split, and the census carries a row per entry byte. If either
        pairing stopped holding, a caller count against `0xBB56`/`0xBBDE` alone
        would again be a complete-looking subset of the real one.
        """
        for entry, body in ((0xBB55, 0xBB56), (0xBBDD, 0xBBDE)):
            with self.subTest(entry='0x%04X' % entry):
                self.assertEqual(LISTINGS.get('%04X' % entry)[entry],
                                 ('setb', 'CY'))
                # The body is seeded separately and does not reach back, so the
                # byte before it is a `setb CY` and not part of that listing.
                self.assertEqual(min(LISTINGS.get('%04X' % body)), body)
                self.assertEqual(LISTINGS.get('%04X' % body)[body],
                                 ('movc', 'A, @A+DPTR'))
                self.assertEqual(entry + 1, body)

    def test_the_dptr_restore_between_the_two_calls_is_present_in_every_ladder(self):
        """The elision this section used to hide: the restore is load-bearing.

        `0xBB55` and `0xBBDE` both leave DPTR at `0x043E` / `0x044F`, so the
        second `movc A,@A+DPTR` can only index the same table if DPTR is put
        back first. Each ladder is therefore held to a `mov DPL, R7` /
        `mov DPH, R6` restore *between* its CPU and GPU calls -- the property,
        not a count of what else the ladder does in between, which is the
        guard and the next index load and differs per ladder.
        """
        for stem, cpu, gpu in (('B5D3', 0xB6F7, 0xB703),
                               ('B4A8', 0xB50F, 0xB51A),
                               ('B4A8', 0xB56D, 0xB578),
                               ('B5D3', 0xB66A, 0xB678),
                               ('B737', 0xB7CA, 0xB7D5)):
            insns = LISTINGS.get(stem)
            with self.subTest(listing=stem, pair='0x%04X/0x%04X' % (cpu, gpu)):
                restores = sorted(a for a in insns if cpu < a < gpu
                                  and insns[a] in (('mov', 'DPL, R7'),
                                                   ('mov', 'DPH, R6')))
                self.assertEqual(len(restores), 2,
                                 'expected one DPTR restore pair between the '
                                 'calls, found %r' % restores)
                dpl, dph = restores
                self.assertEqual(insns[dpl], ('mov', 'DPL, R7'))
                self.assertEqual(insns[dph], ('mov', 'DPH, R6'))
                self.assertEqual(dph - dpl, 2,
                                 'the restore halves are not adjacent')

    def test_no_arithmetic_is_done_on_either_value_in_bc4f(self):
        """The correction is that 0xBC4F computes no offset, not that it has no `inc`.

        A `base + 0x00` reading came from the call site; these ten
        instructions are a copy of two bytes. `inc DPTR` does appear, twice,
        and is not a counter-example: it walks the destination pointer from
        `0x0A47` to `0x0A48` and touches neither value copied. So the
        property held is that no arithmetic instruction has a *register or
        immediate* operand -- an `add`/`subb` on A or R7 would mean the
        routine had become arithmetic and §5 and the corrected annotation row
        would both be describing the wrong thing.
        """
        arithmetic = {'add', 'addc', 'subb', 'inc', 'dec', 'mul', 'rlc', 'rr',
                      'xch'}
        insns = LISTINGS.get('BC4F')
        on_a_value = sorted(
            '0x%04X %s %s' % (addr, mnemonic, operand)
            for addr, (mnemonic, operand) in insns.items()
            if mnemonic in arithmetic
            and not operand.upper().startswith(('DPTR', 'DPH', 'DPL', 'A, R7')))
        self.assertEqual(on_a_value, [])
        # And the two `inc`s it does have are both the pointer walk.
        self.assertEqual([hex(a) for a, (m, _) in insns.items()
                          if m == 'inc'], ['0xbc54', '0xbc5b'])
        self.assertEqual(insns[0xBC54], ('inc', 'DPTR'))
        self.assertEqual(insns[0xBC5B], ('inc', 'DPTR'))

    def test_bc4f_returns_nothing_in_a(self):
        """§5 says a caller reading A gets 0x08E7 rather than a status.

        That is a claim about what is *not* computed, so it is checked as the
        absence of a write to A: the two instructions that store do so through
        DPTR, and the `mov A, R7` at `0xBC5C` is the 0x08E7 the write-up says
        is left behind.
        """
        insns = LISTINGS.get('BC4F')
        writers = sorted('0x%04X %s %s' % (addr, mnemonic, operand)
                         for addr, (mnemonic, operand) in insns.items()
                         if mnemonic == 'mov' and operand.startswith('A,')
                         and addr != 0xBC5C)
        self.assertEqual(writers, [])
        self.assertEqual(insns[0xBC5C], ('mov', 'A, R7'))


class ControlLoopShape(unittest.TestCase):
    """The relations the write-up's claim rests on, read off the listings."""

    def test_the_two_controllers_share_both_integrator_bytes(self):
        """Not two loops over one byte: each drives the byte the write-up names.

        Both `0x8931` block five and `0x8B14` read-modify-write `0x0460` and
        `0x0468`. The claim is that the pair is *shared*, so each `inc A` /
        `dec A` in either controller is resolved to the byte it steps by
        taking the last `mov DPTR, #0x...` before it -- which is what DPTR
        holds at that point, these listings being a linear decode with no
        branch inside the sequence. The walk is bounded by the routine's own
        seeded extent rather than by a byte window, so it cannot run off the
        end of the function or be tuned to one instruction's distance.
        """
        starts = {'8931': 0x8931, '8B14': 0x8B14}
        # Spelled the way the listings spell an immediate -- `0x460`, not
        # `0x0460` -- because the comparison is against operand text and the
        # export does not zero-pad these.
        integrators = sorted('0x%x' % b
                             for b in (CPU_INTEGRATOR, GPU_INTEGRATOR))
        for stem, start in starts.items():
            insns = LISTINGS.get(stem)
            resolved = {}
            for addr, (mnemonic, operand) in sorted(insns.items()):
                if mnemonic not in ('inc', 'dec') or operand != 'A':
                    continue
                live = None
                for back in range(addr - 1, start - 1, -1):
                    if back not in insns:
                        continue
                    found, text = insns[back]
                    if found == 'mov' and 'DPTR, #0x' in text:
                        live = text.split('#')[-1].strip().lower()
                        break
                resolved[addr] = live
                with self.subTest(listing=stem, addr='0x%04X' % addr):
                    self.assertIn(live, integrators,
                                  '0x%04X %s in %s.asm steps %r, not an '
                                  'integrator byte'
                                  % (addr, mnemonic, stem, live))
            # Both integrators, in both controllers: that is the sharing.
            self.assertEqual(sorted(set(resolved.values())), integrators,
                             '%s.asm does not step both integrator bytes' % stem)

    def test_both_controllers_converge_on_the_same_publisher(self):
        """`0x8931` tail-jumps to `0x8C46`; `0x8B14` falls into it.

        The convergence is the reason the write-up can call them two
        instantiations of one loop, so it is read rather than asserted: the
        seeded extent of `0x8B14` plus one must land on `0x8C46`'s own
        address, and `0x8931`'s last instruction must name it.
        """
        with INDEX.open(encoding='utf-8') as handle:
            sizes = {row['addr']: int(row['size']) for row in
                     csv.DictReader(handle)
                     if row['program'] == 'bank0'}
        self.assertEqual(0x8B14 + sizes['8B14'], 0x8C46)
        insns = LISTINGS.get('8931')
        self.assertEqual(max(insns), 0x8B11)
        self.assertEqual(insns[0x8B11], ('ljmp', '0x8c46'))

    def test_the_gate_between_the_two_controllers_is_the_two_enable_bits(self):
        """Both `ljmp 0x8B14` sites are the *failed* arms of block five's gate.

        Read off `0x8931.asm`: each `ljmp` must be the instruction after the
        `jb` on an enable bit, so the write-up's "either bit clear reaches
        `0x8B14`, both set reaches block five" is a reading of the branch
        order and not a claim about which bit means what.
        """
        insns = LISTINGS.get('8931')
        for jb_addr, jmp_addr in ((0x8A29, 0x8A2C), (0x8A33, 0x8A36)):
            mnemonic, operand = insns[jb_addr]
            self.assertEqual(mnemonic, 'jb')
            self.assertIn(operand.split(',')[1].strip(), ('0x8a2f', '0x8a39'))
            self.assertEqual(insns[jb_addr + 3], ('ljmp', '0x8b14'))
            self.assertEqual(insns[jmp_addr], ('ljmp', '0x8b14'))

    def test_the_dwell_gate_is_the_byte_09e4_and_its_top_bit_is_direction(self):
        """The dwell and the direction bit are one byte, read two ways.

        `0xBEAA` masks bit 7 off before comparing, and the `jnb 0xe7` that
        picks `inc` over `dec` tests bit 7 of the value `0xBC5F` returned --
        so the counter and the sign share `0x09E4`. The write-up's claim is
        that they are separable, which is what the mask in the callee and the
        bit test at the call site jointly establish.
        """
        insns = LISTINGS.get('BEAA')
        self.assertEqual(insns[0xBEAE], ('anl', 'A, #0x7f'))
        self.assertEqual(insns[0xBEB0], ('setb', 'CY'))
        self.assertEqual(insns[0xBEB1], ('subb', 'A, #0x32'))
        # 0xBC5F is what puts the incremented byte in A for that bit test.
        self.assertEqual(LISTINGS.get('BC5F')[0xBC63], ('inc', 'A'))

    def test_the_move_needs_the_low_seven_bits_to_reach_the_threshold(self):
        """The dwell is the arithmetic, not a transcribed count of ticks.

        The write-up states a pass count, and a figure asserted here would be a
        second copy of it that goes stale on its own. What is held instead is
        the relation the count follows from, simulated over the instructions
        the listings actually hold: `0xBC5F` increments and returns, the
        `jb 0xe7` at `0x8B41` skips the force-to-`0x80` only when bit 7 is
        set, and `0xBEAA` opens the gate once the low seven bits reach the
        value its `subb` compares against. Simulating those from the clear at
        `0x8B85` is what produces the pass count the write-up quotes, so a
        listing that changed the threshold or the saturation would move this
        and leave the prose to be re-measured rather than silently wrong.

        The `mov A, #0x80` and the `subb` operand are read out of the listings
        rather than written here, so the simulation cannot drift from them.
        """
        beaa = LISTINGS.get('BEAA')
        arm = LISTINGS.get('8B14')

        # The gate: `anl A,#0x7f` / `setb CY` / `subb A,#0xNN` carries iff the
        # masked byte is below NN+1, so NN+1 is what the low bits must reach.
        mask = int(beaa[0xBEAE][1].split('#')[1], 16)
        threshold = int(beaa[0xBEB1][1].split('#')[1], 16) + 1
        self.assertEqual(mask, 0x7F)

        # The saturation: `mov A,#0x80` stored unless `jb 0xe7` skips it.
        forced = int(arm[0x8B44][1].split('#')[1], 16)
        self.assertEqual(arm[0x8B41], ('jb', '0xe7, 0x8b47'))

        value = 0                      # 0x09E4 after the clear -- `clr A` at
        passes = 0                     # 0x8B81, stored by 0x8B85
        while True:
            passes += 1
            value = (value + 1) & 0xFF        # 0xBC5F
            if not value & forced:            # bit 7 clear -> the store fires
                value = forced
            if (value & mask) >= threshold:   # 0xBEAA: carry clear -> move
                break
            self.assertLess(passes, 0x100,
                            'the counter never reaches the threshold')

        # The first increment is spent on the force-to-`0x80`, whose low seven
        # bits are zero, so the move lands one pass later than the threshold is
        # wide. That offset is the whole of the count, and it is a relation
        # between the two constants above rather than a number of its own.
        self.assertEqual(value & mask, threshold)
        self.assertEqual(passes, threshold - (forced & mask) + 1)

        # And the byte the gate opened on is the one the direction bit reads.
        self.assertTrue(value & 0x80,
                        'the move must land with bit 7 set, or the jnb at '
                        '0x8B76 would pick the down arm on the next pass')


INDEX = DECOMPILED / 'index.csv'


def _bank0_owner():
    """Map every seeded bank0 address to the listing that covers it.

    Read off `index.csv`'s own `size` rather than by opening each listing, so
    the write-up's bare `0xNNNN` mentions can be resolved. A mid-function
    address like `0x8B76` has no listing of its own and belongs to `8B14.asm`;
    an XDATA byte like `0x0460` belongs to no listing at all, which is what
    tells the two apart.
    """
    owner = {}
    with INDEX.open(encoding='utf-8') as handle:
        for row in csv.DictReader(handle):
            if row['program'] != 'bank0':
                continue
            start = int(row['addr'], 16)
            for addr in range(start, start + int(row['size'])):
                owner[addr] = row['out_file'].replace('.c', '.asm')
    return owner


BANK0_OWNER = _bank0_owner()


# The listings name DPTR's halves by register and `disasm8051.py` by their SFR
# addresses, so an operand naming one of them is compared in the decoder's
# spelling. `mov DPL, R7` and `mov 0x82,r7` are the same instruction.
IMAGE_OPERAND = {'DPL': '0x82', 'DPH': '0x83'}


def _image_operand(operand):
    """The operand's first token as the linear decoder spells it."""
    first = operand.split(',')[0].strip()
    return IMAGE_OPERAND.get(first, first).lower()


class AgainstTheImage(unittest.TestCase):
    """The one claim a listing cannot carry on its own, re-decoded."""

    def test_the_ladder_window_still_decodes_out_of_the_committed_firmware(self):
        """`B5D3.asm`'s own header calls its boundary a hypothesis.

        So the window the ordering claim rests on is decoded straight out of
        `ec/firmware/GMxMGxx_11.800` with `disasm8051.py` and compared against
        the same call pair. A tool change, a re-export that drifted from the
        image, or a firmware edit all land here rather than quietly changing
        what §3a of the write-up says.
        """
        out = self._disasm('0xB6F4', LADDER_SPAN)
        for addr, mnemonic, operand in LADDER:
            line = self._line_at(out, addr)
            self.assertIsNotNone(
                line, 'disasm8051.py printed nothing at 0x%04X\n%s'
                % (addr, out))
            self.assertIn(mnemonic, line.split(),
                          '0x%04X is not %r in the image: %s'
                          % (addr, mnemonic, line))
            # An `lcall`'s operand is the target address in both printers; a
            # branch's is a resolved address in the listing and a relative
            # displacement in the decoder, and the branch destinations are
            # resolved and compared in the case below rather than matched here.
            if not mnemonic.startswith('j'):
                self.assertIn(_image_operand(operand), line.lower(),
                              '0x%04X does not name %r in the image: %s'
                              % (addr, operand, line))

    def test_the_ladder_branches_all_leave_to_the_same_place(self):
        """The ordering claim rests on the three `jnc`s sharing a destination.

        `B5D3.asm` prints those destinations resolved (`jnc 0xb736`); the
        linear decoder prints the encoded displacement (`jnc +0x3a`), so the
        two are compared by resolving the displacement rather than by string.
        The claim is that all three guards leave the chain the same way, which
        is what makes it a gate chain rather than three separate tests.
        """
        out = self._disasm('0xB6F4', LADDER_SPAN)
        targets = set()
        for addr, mnemonic, operand in LADDER:
            if not mnemonic.startswith('j'):
                continue
            line = self._line_at(out, addr)
            self.assertIsNotNone(line, 'no decoded line at 0x%04X' % addr)
            self.assertTrue(mnemonic in line.split(),
                            '0x%04X is not %r in the image: %s'
                            % (addr, mnemonic, line))
            disp = line.split()[-1]
            self.assertTrue(disp.startswith('+'),
                            '0x%04X did not decode to a displacement: %s'
                            % (addr, line))
            # The displacement is relative to the byte after the branch, and
            # the encoder column gives that instruction's width.
            width = len(line.split()[1]) // 2
            targets.add(addr + width + int(disp[1:], 16))
        self.assertEqual(len(targets), 1,
                         'the three guards leave to %r, not to one place'
                         % sorted(targets))
        self.assertEqual(targets.pop(), 0xB736)

    def test_the_ladder_window_decodes_the_same_way_from_two_anchors(self):
        """The same instructions, decoded from a second anchor further back.

        `disasm8051.py` is a linear decoder and says so: it cannot tell you
        that the byte you pointed it at starts an instruction. Two anchors
        that agree about the instructions between them are evidence about
        framing, and the write-up's §3a claim is the one that most needs it,
        because `B5D3`'s boundary is a byte-scan hypothesis. Which anchors
        are used is not pinned -- only that they decode alike.
        """
        near = self._disasm('0xB6F4', LADDER_SPAN)
        far = self._disasm('0xB6F1', LADDER_SPAN + 3)
        for addr, mnemonic, _operand in LADDER:
            a = self._line_at(near, addr)
            b = self._line_at(far, addr)
            self.assertIsNotNone(a, 'missing at 0x%04X from the near anchor'
                                 % addr)
            self.assertIsNotNone(b, 'missing at 0x%04X from the far anchor'
                                 % addr)
            self.assertEqual(a.split()[2:], b.split()[2:],
                             '0x%04X decodes differently from the two anchors'
                             % addr)

    def test_the_convergence_measurement_is_reported_not_pinned(self):
        """`--converge` is asked for and its answer must report a measurement.

        Pinning the number would be pinning a property of the decoder's
        window rather than of this repository, and it moves when the tool
        does. What is held is the shape of the report -- that the flag still
        answers with an anchor count for the address asked about -- so a tool
        change that silently stopped measuring reds here. (`--converge`
        replaces the decode rather than accompanying it, hence its own run.)
        """
        proc = subprocess.run(
            [sys.executable, str(DISASM), '--at', '0x8B14', '--converge',
             str(FIRMWARE)],
            capture_output=True, text=True, check=True)
        out = proc.stdout
        self.assertIn('0x08B14', out)
        self.assertRegex(out, r'\d+ of \d+ preceding anchors decode onto it')

    @staticmethod
    def _disasm(at, n):
        proc = subprocess.run(
            [sys.executable, str(DISASM), '--at', at, '-n', str(n),
             str(FIRMWARE)],
            capture_output=True, text=True, check=True)
        return proc.stdout

    @staticmethod
    def _line_at(out, addr):
        """The decoded line for `addr`, or None.

        `disasm8051.py` prints bank0 addresses as five hex digits
        (`0x0b6f4`), so the needle is built from the width the tool uses
        rather than from the four-digit form the listings use.
        """
        needle = '0x%05x' % addr
        return next((ln for ln in out.splitlines()
                     if ln.startswith(needle)), None)


class AnnotationRowAndWriteup(unittest.TestCase):
    """The corrected row and the write-up that cites it."""

    def test_the_bc4f_row_parses_with_a_hand_decoded_basis_and_real_evidence(self):
        """Issue item 4: the one `inferred` row in the §6 group is corrected.

        Checked as a property of the row rather than as its text: it parses,
        its basis is `hand-decoded`, its evidence is non-empty, and every file
        it names exists. A row whose evidence named a file this change deleted
        would pass a basis check and fail this one.
        """
        with FUNCTIONS_CSV.open(encoding='utf-8') as handle:
            rows = [r for r in csv.DictReader(handle)
                    if r['scope'] == 'bank0' and r['addr'] == '0xBC4F']
        self.assertEqual(len(rows), 1, 'expected exactly one 0xBC4F row')
        row = rows[0]
        self.assertEqual(row['basis'], 'hand-decoded')
        self.assertTrue(row['evidence'].strip(),
                        'the 0xBC4F row has an empty evidence cell')
        for path in row['evidence'].split(';'):
            path = path.strip()
            self.assertTrue(path, 'an empty path in the evidence cell')
            self.assertTrue((REPO / path).exists(),
                            'evidence names %s, which does not exist' % path)

    def test_no_row_in_the_fan_group_is_left_on_an_inferred_basis(self):
        """The §6 group as a whole, not just the row this issue names.

        `subsystems.md` §6 singled 0xBC4F out as the only `inferred` row in
        the group. If a later branch seeds another one, that sentence is
        stale and the write-up's §5 claim about the group is too -- so the
        property is held here rather than as the sentence.
        """
        group = ('0x8653', '0x888D', '0xBB40', '0xBC4F', '0xCA4C', '0xBAD4',
                 '0xBAE5', '0xBB56', '0xBBDE', '0xBDF2', '0xCCFC')
        with FUNCTIONS_CSV.open(encoding='utf-8') as handle:
            bases = {r['addr']: r['basis'] for r in csv.DictReader(handle)
                     if r['scope'] == 'bank0' and r['addr'] in group}
        self.assertTrue(bases, 'no §6 group rows found in the annotations CSV')
        self.assertEqual([a for a, b in bases.items() if b == 'inferred'], [])

    def test_the_twin_rows_both_name_the_be16_copy(self):
        """`0xBC4F` and `0xBCCB` are described as the same kind of routine.

        The §5 claim is that `0xBC4F` is the no-argument twin of `0xBCCB`, and
        that claim is only as good as the two rows agreeing about it -- so the
        twin relationship is read from the rows rather than asserted from the
        write-up. Only the *description* is held, not the `type` column: it
        still reads `math`, and changing it moves the row between groups in
        `function-groups.csv`, which is a derived file whose regeneration
        rewrites rows this change has nothing to do with. That is a separate
        edit for whoever next regenerates it.
        """
        wanted = ('0xBC4F', '0xBCCB')
        with FUNCTIONS_CSV.open(encoding='utf-8') as handle:
            rows = {r['addr']: r for r in csv.DictReader(handle)
                    if r['scope'] == 'bank0' and r['addr'] in wanted}
        for addr in wanted:
            self.assertIn(addr, rows, 'the %s row is gone' % addr)
            comment = rows[addr]['comment']
            # Both rows must say the pair is the subject, which is what makes
            # them twins rather than two unrelated two-byte stores.
            self.assertIn('0x0A47', comment,
                          '%s does not name the pair it writes' % addr)
            self.assertIn('0x08E6', comment,
                          '%s does not name the bytes it copies' % addr)

    def test_the_writeup_carries_a_hash_one_title(self):
        """What `gen_findings_index.py --check` holds, held here as well.

        The index that tool renders is generated and not committed, so a
        write-up with no `# ` title is invisible rather than broken. The
        check is the shape, not the wording.
        """
        text = WRITEOUT.read_text(encoding='utf-8')
        titles = [ln for ln in text.splitlines() if ln.startswith('# ')]
        self.assertEqual(len(titles), 1, 'expected one `# ` title')

    def test_every_code_address_the_writeup_cites_is_in_a_committed_listing(self):
        """Each `0xNNNN` the write-up cites as code resolves to a real listing.

        The per-site cases above check the instructions the reading turns on.
        This one is the broader half, over *every* code address in the prose
        rather than the ones the reading depends on: an address whose owning
        listing is not on disk is a citation that has gone stale.

        The XDATA/code distinction is drawn by ownership rather than by a
        range, because a mid-function address like `0x8B76` belongs to
        `8B14.asm` and must not be reported as missing, while `0x0460` belongs
        to no listing at all -- which is exactly why it is a register and not
        a code address. Only addresses that *are* owned are checked, so a
        register the write-up cites correctly is not flagged by not existing
        as code.
        """
        text = WRITEOUT.read_text(encoding='utf-8')
        cited = {int(t, 16) for t in re.findall(r'`(0x[0-9A-F]{4})`', text)}
        cited.update(int(s, 16)
                     for s in re.findall(r'`([0-9A-F]{4})\.asm`', text))
        owned = {a for a in cited if a in BANK0_OWNER}
        self.assertTrue(owned, 'no code addresses cited at all')
        missing = sorted({BANK0_OWNER[a] for a in owned
                          if not (DECOMPILED / BANK0_OWNER[a]).exists()})
        self.assertEqual(missing, [],
                         'cited addresses resolve to listings that are gone: '
                         + ', '.join(missing))

    def test_a_mid_function_address_resolves_to_the_listing_that_owns_it(self):
        """The mechanism the case above rests on, checked where it is load-bearing.

        The write-up cites `0x8B76` and `0x8B85`, which are inside `0x8B14`
        and have no listing of their own; `0x0460` is an XDATA byte and is in
        no listing at all. If `index.csv`'s `size` stopped covering a routine
        the way this assumes, every such citation would silently drop out of
        the check above rather than fail, so the resolution is pinned here at
        a boundary address and at a register.
        """
        # 0x8B85 is three bytes before the seeded end of 0x8B14, so it is
        # inside it and not in a listing of its own.
        self.assertEqual(BANK0_OWNER[0x8B85], 'bank0/8B14.asm')
        self.assertEqual(BANK0_OWNER[0x8C45], 'bank0/8B14.asm')
        # The first byte past that routine belongs to whatever comes next.
        self.assertNotEqual(BANK0_OWNER[0x8C46], 'bank0/8B14.asm')
        self.assertEqual(BANK0_OWNER[0x8C46], 'bank0/8C46.asm')
        # And an XDATA byte is owned by nothing, which is what separates it.
        for register in (CPU_INTEGRATOR, GPU_INTEGRATOR, 0x09E4, 0x0A47):
            self.assertNotIn(register, BANK0_OWNER)


if __name__ == '__main__':
    unittest.main()
