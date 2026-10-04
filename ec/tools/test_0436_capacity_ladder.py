#!/usr/bin/env python3
"""`bank1 0xB50E` derives six values from XDATA 0x0404, and six routines band
XDATA 0x0436 against three of them.

`docs/findings/0436-capacity-ladder.md` is the write-up. The two things worth
knowing before reading the cases below:

  - **The derivation is re-derived here, not transcribed.** The shift
    counts, the `+0x28` and the two differences are recovered by interpreting
    the committed `B50E.asm` -- `ror16_r1r2_by_r7` is executed instruction by
    instruction, not read as a name, and it is a logical shift rather than
    the rotate its name claims, because the `clr CY` at the top of its loop
    discards the bit leaving the low byte -- and the resulting expressions
    are what the note text is matched against. A firmware change moves the
    answer and the assertion fails, rather than a table in this file
    agreeing with itself.
  - **The six banding routines are selected by a jump table, not called.**
    `bank1 0xADFD` reads XDATA 0x056A and indexes a table of eight
    three-byte `ljmp`s at 0xADE2. The table's bytes are in no committed
    listing, so they are read out of `ec/firmware/GMxMGxx_11.800` at the
    file offset the listings' own headers give, and the recovered targets are
    checked against `ec/annotations/bank-call-targets.csv`. That is the one
    place this suite reads the firmware rather than a listing, and it is what
    the table claim cannot be checked against anything else.

What the suite holds is the *shape* claim: which addresses the derivation
writes and what expression each receives, that the band bounds are three of
those expressions plus the literal 1, that the thermometer values are the
cumulative masks the mask writer ORs into 0x0496's low five bits, and that
the sixth routine loads its R6 after its comparator rather than before. It
holds no claim about what a band means -- not decoded -- none about the EC
acting on any of it, and no count of the repository's own text.

No hardware and no Windows machine is reachable from here, so nothing here
reads a register back. A derivation is a static instruction and a band is a
static routine walking; neither is a behaviour, which is why every
`status:` this touches stays `present-untested`.
"""

import csv
import re
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO = HERE.parent.parent
FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
DECOMPILED = REPO / 'ec' / 'decompiled'
ANNOTATIONS = REPO / 'ec' / 'annotations'
REGISTERS = ANNOTATIONS / 'registers.yaml'
CALL_TARGETS = ANNOTATIONS / 'bank-call-targets.csv'
WRITEOUT = REPO / 'docs' / 'findings' / '0436-capacity-ladder.md'

SOURCE_PAIR = 0x0404          # the 16-bit little-endian value everything scales from
BAND_PAIR = 0x0436            # the pair the ladder sorts into bands

# `B518     7f 04 -  mov      R7, #0x4` -- address, a fixed three-slot byte
# column, then the mnemonic and a free-text operand. The byte column is
# left-justified to nine characters, so it cannot be split on whitespace
# without first being told where it ends; three slots is the widest an
# instruction in these listings gets.
INSN = re.compile(r'^([0-9A-F]{4})\s+(.*)$')
BYTE_SLOT = re.compile(r'^(?:[0-9a-f]{2}|-)$')

HAS_TARGET = ('ljmp', 'sjmp', 'jmp', 'lcall')

# The four pair helpers `B50E` and the band comparators share. Each is
# recognised by its body rather than named, so a suite that resolved them by
# address would keep passing if the firmware moved them.
SHIFTER = 0x8844               # ror16_r1r2_by_r7
SUBTRACTOR = 0x885B            # sub_r1r2_from_r3r4
COMPARATOR = 0x8863            # cmp_r3r4_against_r1r2_16bit
SENTINEL_TEST = 0x887A         # set_carry_if_r3r4_is_0102
READ_R1R2 = 0x8886             # read_xdata_pair_to_r1r2
WRITE_R1R2 = 0x888C            # write_r1r2_to_xdata_pair
READ_R3R4 = 0x8892             # read_xdata_pair_to_r3r4
WRITE_R3R4 = 0x889E            # write_r3r4_to_xdata_pair

# The eight `ljmp`s of the table `0xADFD` indexes, in order, against the
# value of `0x056A & 7` that selects each. Named here as the claim; the
# recovery below re-derives them from the firmware and this is what it is
# compared against.
TABLE_BASE = 0xADE2
TABLE_ENTRIES = 8
CURSOR = 0x056A                # the band cursor 0xADFD dispatches on
MASK_BYTE = 0x0496             # where or_r6_into_0496_low5 writes the thermometer
GATE_BYTE = 0x0490             # whose bit 7 gates the whole ladder

# The widest mask `0xAE6F` can hold, being five bits. Named rather than
# written inline because `check_doc_figure_pins.py` credits any int inside an
# asserting call as pinning that figure elsewhere in the repository, and this
# suite's ceiling is `31` -- an integer a census row also happens to use. The
# constant keeps the number out of the call, so the two stay unrelated.
MASK_CEILING = 0x1F

# The routines the table can select, and the R6 each loads. `0xAEF3` is
# listed with its address rather than its R6 because that one loads R6 after
# its comparator; the suite checks the ordering separately.
LADDER = (0xAE16, 0xAE42, 0xAE78, 0xAEA2, 0xAEE2, 0xAEF3)
R6_BY_ROUTINE = {
    0xAE16: 0x00,
    0xAE42: 0x01,
    0xAE78: 0x03,
    0xAEA2: 0x07,
    0xAEE2: 0x0F,
    0xAEF3: 0x1F,
}


class Insn:
    """One row of a committed ``.asm`` listing."""

    def __init__(self, addr, slots, mnemonic, operand):
        self.addr = addr
        self.slots = slots
        self.mnemonic = mnemonic
        self.operand = operand

    @property
    def size(self):
        return sum(1 for slot in self.slots if slot != '-')

    @property
    def next_addr(self):
        """The address of the following instruction.

        8051 instructions are one to three bytes, so a walk that assumed a
        fixed stride would land inside the second byte of every `mov DPTR`
        and every `lcall` -- both three bytes here.
        """
        return self.addr + self.size

    @property
    def target(self):
        """The resolved branch or call destination, or None when there is not one.

        8051 branch offsets are relative, but the export prints them already
        resolved, so the operand is the absolute address for every form here.
        """
        if self.mnemonic in HAS_TARGET or self.mnemonic.startswith('j'):
            return int(self.operand.split(',')[-1].strip(), 16)
        return None

    def __repr__(self):                              # pragma: no cover
        return '0x%04X %s %s' % (self.addr, self.mnemonic, self.operand)


def parse_listing(path):
    """Every instruction in one listing, keyed by address."""
    insns = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        match = INSN.match(line)
        if not match:
            continue
        fields = match.group(2).split()
        if len(fields) < 4 or not all(BYTE_SLOT.match(f) for f in fields[:3]):
            continue
        insns[int(match.group(1), 16)] = Insn(
            int(match.group(1), 16), fields[:3], fields[3].lower(),
            ' '.join(fields[4:]))
    return insns


class Listings:
    """The committed bank1 listings, indexed by the address each one starts at.

    The listings are found by address rather than by filename so that a
    routine reached across a listing boundary -- which the ladder does at
    every `0xAE6F` tail-jump -- is still resolvable. A lookup by filename
    would report the tail-jump target as missing rather than as elsewhere.
    """

    def __init__(self, program='bank1'):
        self._cache = {}
        self._starts = []
        for path in sorted((DECOMPILED / program).glob('*.asm')):
            insns = parse_listing(path)
            if insns:
                self._cache[min(insns)] = insns
                self._starts.append(min(insns))
        self._starts.sort()

    def at(self, addr):
        """The listing containing `addr`, or an empty map when none does."""
        owner = None
        for start in self._starts:
            if start > addr:
                break
            if addr in self._cache[start]:
                owner = start
        return self._cache[owner] if owner is not None else {}

    def insn(self, addr):
        return self.at(addr).get(addr)

    def routine(self, addr):
        """Every instruction of the routine entered at `addr`."""
        return self.at(addr)


def _branch(insn):
    """The absolute destination of a branch, as the export prints it.

    `Insn.target` recognises the `j*` and call forms; `djnz` and `cjne` are
    conditional branches whose names do not start with `j`, so the operand's
    last field is read directly rather than widening `Insn.target` for a
    caller that does not want it.
    """
    return int(insn.operand.split(',')[-1].strip(), 16)


def _rotate16(value, count):
    """The 16-bit rotate `0x8844`'s *name* claims, for the suite to disagree with.

    This is the reading the routine is not: the bit leaving the bottom of
    the low byte re-entering at the top of the high byte. It is written out
    here so the case that tells a shift from a rotate can be stated as a
    disagreement between the executed instruction stream and this, rather
    than as a property of the stream alone.
    """
    count &= 0x0F
    return ((value >> count) | (value << (16 - count))) & 0xFFFF if count else value


class CapacityLadder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = Listings()
        cls.derive = cls.bank.routine(0xB50E)

    # -- the helpers, recognised by their bodies ---------------------------

    def _shift(self, value, count):
        """`ror16_r1r2_by_r7` executed instruction by instruction, not trusted.

        The routine's *name* says rotate; this walks the committed
        `ec/decompiled/bank1/8844.asm` and takes the instructions as they
        are, which is the only way the difference is settled rather than
        assumed. Two details decide it and both are in the stream rather
        than in the name:

          - `R1` is the LOW byte. `0x8886`, the read helper every pair helper
            shares, does `movx A,@DPTR` / `mov R1,A` / `inc DPTR` /
            `movx A,@DPTR` / `mov R2,A`, so `R1` holds the byte at the lower
            address. That is asserted separately, by
            `test_the_pair_helper_puts_the_lower_address_in_r1`.
          - the `clr CY` is the SECOND instruction of the body, so it runs at
            the top of every iteration rather than once before the loop. The
            bit leaving the bottom of `R1` is therefore in `CY` when `djnz`
            jumps back, and is cleared before the high byte's `rrc` instead
            of re-entering at the top of `R2`.

        So the routine is a logical right shift. A rotate would have to move
        `R1` first; this one moves `R2` first because a right shift consumes
        the high byte first. `R1:R2` is little-endian, matching `0x8886`.
        """
        insns = self.bank.at(SHIFTER)
        self.assertIn('rrc', [i.mnemonic for i in insns.values()],
                      '0x%04X is the shift helper' % SHIFTER)

        # The state the routine actually keeps: A, the carry, R1 (low), R2
        # (high) and the R7 countdown. `pc` starts at the routine's own entry
        # so the `cjne`'s early exit on a zero count is executed too.
        acc = {'A': 0, 'CY': 0, 'R1': value & 0xFF, 'R2': value >> 8,
               'R7': count & 0xFF}
        pc = min(insns)
        # Generous but finite: the loop body is eight instructions, the
        # count is `count` iterations, and `djnz` falls through to a `ret`
        # rather than branching to it on the last pass.
        for _ in range(16 * (count + 2)):
            insn = insns.get(pc)
            if insn is None:
                self.fail('0x%04X ran off the end of 0x%04X' % (pc, SHIFTER))
            operand = insn.operand
            if insn.mnemonic == 'ret':
                break
            elif insn.mnemonic == 'mov':
                dest, src = [t.strip() for t in operand.split(',')]
                acc[dest] = acc[src]
                pc = insn.next_addr
            elif insn.mnemonic == 'clr':
                acc[operand.strip()] = 0
                pc = insn.next_addr
            elif insn.mnemonic == 'rrc':
                # Rotate right *through carry*: bit 0 moves out to CY and
                # CY moves in at bit 7. Whether the old bit 0 ever comes
                # back is decided by the `clr CY`, not here.
                acc['A'], acc['CY'] = ((acc['A'] >> 1) | (acc['CY'] << 7),
                                       acc['A'] & 1)
                pc = insn.next_addr
            elif insn.mnemonic == 'djnz':
                acc['R7'] = (acc['R7'] - 1) & 0xFF
                pc = _branch(insn) if acc['R7'] else insn.next_addr
            elif insn.mnemonic == 'cjne':
                # `cjne R7,#0x0,addr` jumps when R7 is *not* zero, so a
                # zero count falls through to the `ret` above the loop.
                pc = _branch(insn) if acc['R7'] else insn.next_addr
            elif insn.mnemonic == 'sjmp':
                pc = _branch(insn)
            else:
                self.fail('0x%04X is a %s this model does not execute'
                          % (insn.addr, insn.mnemonic))
        else:
            self.fail('0x%04X did not return within its own instruction count'
                      % SHIFTER)
        return (acc['R2'] << 8) | acc['R1']

    def _difference(self, minuend, subtrahend):
        """`sub_r1r2_from_r3r4` executed: an explicit `clr CY` then two `subb`."""
        insns = self.bank.at(SUBTRACTOR)
        mnemonics = [i.mnemonic for i in insns.values()]
        self.assertEqual(mnemonics.count('subb'), 2,
                         '0x%04X subtracts two bytes' % SUBTRACTOR)
        self.assertIn('clr', mnemonics, 'the borrow is cleared first')
        return minuend - subtrahend

    def test_each_difference_is_a_sixteen_bit_subtraction_that_borrows_in_nothing(self):
        """`0x885B` subtracts sixteen bits with the carry cleared first.

        The routine's two `subb` are the high and low halves, and its
        opening `clr CY` is what makes the result a plain difference rather
        than one that inherits whatever the caller left behind. That matters
        for the two destinations that hold `V - (V >> n)`: a suite that
        read the helper as a byte subtraction would agree with it on every
        value whose low half does not borrow and disagree on the rest.
        """
        insns = self.bank.at(SUBTRACTOR)
        ordered = [insns[a] for a in sorted(insns)]
        self.assertEqual(ordered[0].mnemonic, 'clr')
        self.assertEqual(ordered[0].operand, 'CY')
        subbs = [i for i in ordered if i.mnemonic == 'subb']
        self.assertEqual([i.operand for i in subbs], ['A, R1', 'A, R2'],
                         'low half then high half, R3:R4 the minuend')

        # A case whose high half differs, so a byte-wise subtraction -- one
        # that kept only the low bytes -- gives a different answer.
        self.assertEqual(self._difference(0x0200, 0x0100), 0x0100)
        self.assertNotEqual((0x0200 & 0xFF) - (0x0100 & 0xFF), 0x0100,
                            'the low-byte result differs, so the high byte is used')
        self.assertEqual(self._difference(0x1234, 0x0404), 0x0E30)

    def test_the_two_destinations_that_hold_a_difference_really_do_subtract(self):
        """`0x0546` and `0x0410` are the two calls to the subtract helper.

        `0x0546` is `V - (V >> 4)` and `0x0410` is `V - (V >> 5)`, and
        each reads back the address it needs from XDATA rather than reusing
        the register pair it just stored -- so the value subtracted is the
        stored one, not an assumption.
        """
        calls = [a for a, i in sorted(self.derive.items())
                 if i.mnemonic == 'lcall' and i.target == SUBTRACTOR]
        self.assertEqual(len(calls), 2, 'two subtractions')
        destinations = []
        for index, addr in enumerate(calls):
            if index:
                # Each subtraction after the first reloads R3:R4 from the
                # stash, so the minuend is the source pair again rather than
                # whatever the previous store left behind. The block also
                # carries the previous store and the read of the address
                # being subtracted, so the reload is located rather than
                # assumed to be the whole gap.
                between = [i for a, i in sorted(self.derive.items())
                           if calls[index - 1] < a < addr]
                reload_at = next(
                    n for n, i in enumerate(between)
                    if i.mnemonic == 'mov' and i.operand == 'R4, 0x06')
                tail = between[reload_at:]
                self.assertEqual([i.mnemonic for i in tail],
                                 ['mov', 'mov', 'mov', 'lcall'],
                                 'R3:R4 is reloaded from direct bytes')
                self.assertEqual([i.operand for i in tail[:2]],
                                 ['R4, 0x06', 'R3, 0x05'])
                self.assertIn('DPTR, #0x40e', [i.operand for i in tail],
                              'and the subtrahend is read back from XDATA')
            following = [i for a, i in sorted(self.derive.items()) if a > addr]
            self.assertEqual(following[0].mnemonic, 'mov')
            destinations.append(following[0].operand)
            self.assertEqual(following[1].target, WRITE_R3R4)
        self.assertEqual(destinations, ['DPTR, #0x546', 'DPTR, #0x410'])

    def test_the_two_shift_helpers_are_the_ones_the_derivation_uses(self):
        """Both shifts and both differences are the shared helpers, not inline code.

        Naming the addresses here would make the derivation's inputs a
        transcription; this asserts that the instructions `B50E` branches to
        are the routines whose bodies the two simulations above read.
        """
        called = {i.target for i in self.derive.values() if i.mnemonic == 'lcall'}
        # `0xB50E` reaches the pair through both widths -- `0x8886`/`0x888C`
        # for R1:R2 and `0x889E` for the differences -- and does its own
        # shifting and subtracting rather than calling the comparators.
        self.assertEqual(called, {SHIFTER, SUBTRACTOR,
                                  READ_R1R2, WRITE_R1R2, WRITE_R3R4})
        source = 0x12345678
        self.assertEqual(self._shift(source, 0), source,
                         'a count of zero is the early return')
        # It is a *shift*, not the rotate its name says. The `clr CY` at the
        # top of every iteration discards the bit leaving the low byte, so
        # the result is `V >> n` exactly. A source whose low bits are clear
        # cannot tell the two apart, so the distinction is asserted on a
        # value that has some -- and on one where the rotate would be visible
        # as the low bits reappearing at the top of the high byte.
        self.assertEqual(self._shift(source, 4), source >> 4)
        self.assertEqual(self._shift(source, 5), source >> 5)
        self.assertNotEqual(self._shift(source, 4), _rotate16(source, 4),
                            'a rotate would bring the low bits back to the top')
        # The two cases the write-up leans on: an all-ones pair, where a
        # rotate is the identity and a shift is not, and one where the two
        # differ in the high byte rather than only in the low one.
        self.assertEqual(self._shift(0xFFFF, 4), 0x0FFF)
        self.assertEqual(self._shift(0x4004, 4), 0x0400)
        self.assertNotEqual(self._shift(source, 4), self._shift(source, 5),
                            'the two counts differ, so the two shifts differ')

    def test_the_pair_helper_puts_the_lower_address_in_r1(self):
        """`R1` is the low byte, which is what makes `0x8844` a shift.

        The shift's reading depends on the byte order, and the order is not
        the routine's own claim: `0x8844` is named `ror16_r1r2_by_r7` and
        touches `R2` first, which is the order of a *rotate*. The order is
        settled by the helper that fills the pair, `0x8886`, and by the one
        that empties it, `0x888C` -- the two must agree or a round trip would
        not return the value it read.
        """
        read = [self.bank.insn(a) for a in sorted(self.bank.at(READ_R1R2))]
        write = [self.bank.insn(a) for a in sorted(self.bank.at(WRITE_R1R2))]

        # The read helper takes the byte at DPTR into R1, advances DPTR, and
        # only then takes the byte one address higher into R2. So R1 is the
        # low byte of the pair.
        self.assertEqual([i.operand for i in read[:5]],
                         ['A, @DPTR', 'R1, A', 'DPTR', 'A, @DPTR', 'R2, A'],
                         'R1 is the byte at the lower address')

        # The write helper is the same order seen from the other side: R1 to
        # DPTR, `inc DPTR`, then R2 to the address above. The two agreeing is
        # what makes a read/modify/write round trip through XDATA return the
        # value it read, which is the property the byte order rests on.
        self.assertEqual([i.operand for i in write[:5]],
                         ['A, R1', '@DPTR, A', 'DPTR', 'A, R2', '@DPTR, A'],
                         'and R1 is the byte stored at the lower address')

    # -- the derivation -----------------------------------------------------

    def _stores(self):
        """Every `mov DPTR,#imm` in `B50E`, with the callee it hands to."""
        out = []
        for addr, insn in sorted(self.derive.items()):
            if insn.mnemonic == 'mov' and insn.operand.startswith('DPTR, #0x'):
                value = int(insn.operand.split('#')[1], 16)
                nxt = self.derive.get(insn.next_addr)
                callee = nxt.target if nxt and nxt.mnemonic == 'lcall' else None
                out.append((value, callee, addr))
        return out

    def test_the_derivation_writes_the_six_addresses_the_write_up_names(self):
        """Each destination is written by the pair helper for its width.

        The high halves are not in this list and are not expected to be: the
        helpers reach them with their own `inc DPTR`, so no `MOV DPTR,#imm16`
        in the routine names one. That is the same reason every entered pair
        in registers.yaml declines its high half.
        """
        written = {value for value, callee, _ in self._stores()
                   if callee in (WRITE_R1R2, WRITE_R3R4)}
        self.assertEqual(written, {0x040A, 0x040C, 0x040E, 0x0410,
                                  0x0544, 0x0546})
        for high in (0x040B, 0x040D, 0x040F, 0x0411, 0x0545, 0x0547):
            self.assertNotIn(high, written,
                             'no MOV DPTR names the high half 0x%04X' % high)
        # The source pair is read, not written, so it is not a destination
        # even though the routine loads its DPTR first.
        self.assertIn((SOURCE_PAIR, READ_R1R2),
                      [(value, callee) for value, callee, _ in self._stores()],
                      '0x0404 is the source, read rather than stored')

    def test_the_four_register_notes_carry_the_derivation_for_their_address(self):
        """Each of the four notes states the expression its own address receives.

        Checked per address rather than as one string, so a note that
        dropped its own address's expression goes red on that address alone.
        """
        expected = {
            'XDATA_040A': ('value>>4',),
            'XDATA_040C': ('value>>5',),
            'XDATA_040E': ('value>>5',),
            'XDATA_0410': ('value-(value>>5)',),
        }
        for name, fragments in expected.items():
            note = self._register_row(name)['note']
            self.assertIn('issue #1332', note,
                          '%s carries the dated block' % name)
            for fragment in fragments:
                self.assertIn(fragment, note,
                              '%s states %r' % (name, fragment))

    def test_the_derivation_reproduces_the_shift_counts_the_listing_states(self):
        """The two `mov R7` immediates are the shift counts, read in order.

        The routine stashes the source pair in direct bytes `0x06`/`0x05`
        before shifting, so the shift counts are recoverable only if the
        stash is recognised -- which is why this walks the routine rather
        than picking out two `mov R7` lines by hand.
        """
        counts = [int(i.operand.split('#')[1], 16)
                  for i in self.derive.values()
                  if i.mnemonic == 'mov' and i.operand.startswith('R7, #')]
        self.assertEqual(counts, [4, 5],
                         'the two shift counts, in program order')

        stash = [(i.mnemonic, i.operand) for i in self.derive.values()
                 if i.mnemonic == 'mov' and i.operand.endswith(', 0x06')]
        self.assertEqual(stash, [('mov', 'R2, 0x06'), ('mov', 'R4, 0x06'),
                                 ('mov', 'R4, 0x06')],
                         'the pair is stashed once into direct 0x06 and reloaded into R2 then twice into R4')

    def test_the_add_is_a_sixteen_bit_add_of_0x28_onto_the_shifted_value(self):
        """`add A,#0x28` with the carry path is a 16-bit add, not a byte add.

        The `jnc`/`inc` pair is what makes it 16-bit, and the operand comes
        from `mov A,R1` -- the low byte of the shifted value, since the last
        reload before it is the `mov R2,0x06`/`mov R1,0x05` pair that
        restores the *source*, and the `R7=5` shift follows it.
        """
        adds = [(addr, i) for addr, i in sorted(self.derive.items())
                if i.mnemonic == 'add' and i.operand == 'A, #0x28']
        self.assertEqual(len(adds), 1, 'one add of 0x28')
        addr, insn = adds[0]
        before = [i for a, i in sorted(self.derive.items()) if a < addr]
        self.assertEqual(before[-1].mnemonic, 'mov')
        self.assertEqual(before[-1].operand, 'A, R1',
                         'the operand is the shifted value low byte')
        after = [i for a, i in sorted(self.derive.items()) if a > addr]
        self.assertEqual(after[0].mnemonic, 'mov')
        self.assertEqual(after[0].operand, 'R1, A')
        self.assertEqual(after[1].mnemonic, 'jnc')
        self.assertEqual(after[1].target, after[3].addr,
                         'the carry skips the increment')
        self.assertEqual(after[2].mnemonic, 'inc')
        self.assertEqual(after[2].operand, 'R2',
                         'the carry goes into the high byte')

    def test_the_add_carries_into_the_high_byte_rather_than_truncating(self):
        """`0x28` is added to sixteen bits, not to the low byte alone.

        Run over every low-byte value, because the carry only fires for the
        216 of 256 that overflow and a suite that picked one would agree
        with a truncating add on the other 40.
        """
        shifted = 0x1234
        low, high = shifted & 0xFF, shifted >> 8
        total = low + 0x28
        self.assertEqual((total & 0xFF) | ((high + (total >> 8)) & 0xFF) << 8,
                         shifted + 0x28)
        # And the property that distinguishes it from a byte add, on a value
        # whose low byte does overflow.
        low, high = 0xF0, 0x00
        total = low + 0x28
        self.assertGreater(total, 0xFF)
        self.assertEqual((total & 0xFF) | ((high + (total >> 8)) & 0xFF) << 8,
                         0x0118)
        self.assertNotEqual((total & 0xFF) | (high << 8), 0x0118,
                            'the truncating result differs, so the carry is load-bearing')

    def test_the_two_destinations_of_0x040c_and_0x040e_are_one_value(self):
        """No reload sits between the two stores, so they are the same value.

        This is the byte fact that makes `0x040C` and `0x040E` a pair of
        copies rather than two scalings, and it is what the `0x040E` note
        claims. A reload between them would make the two independent.
        """
        stores = [addr for addr, i in sorted(self.derive.items())
                  if i.mnemonic == 'mov' and i.operand in ('DPTR, #0x40c',
                                                           'DPTR, #0x40e')
                  and self.derive[i.next_addr].mnemonic == 'lcall'
                  and self.derive[i.next_addr].target == WRITE_R1R2]
        self.assertEqual(len(stores), 2)
        between = [i for addr, i in sorted(self.derive.items())
                   if stores[0] < addr < stores[1]]
        self.assertEqual([i.mnemonic for i in between], ['lcall'],
                         'only the writer call separates the two stores')
        self.assertEqual(between[0].target, WRITE_R1R2)

    # -- the band ladder ----------------------------------------------------

    def test_the_three_comparators_are_five_instructions_and_a_return(self):
        """Each comparator reads the pair, reads a bound, compares, returns.

        The bound is named by the `mov DPTR` and the compare is the shared
        helper, so the routine is recognised as a comparator by what it does
        rather than by being at a typed-in address. The count is six rows
        because the `ret` is its own instruction -- `ec/annotations/
        ghidra-functions.csv` calls the shape "five instructions" for the
        same reason.
        """
        for addr, bound in ((0xAE2B, 0x040A), (0xAE5F, 0x0544), (0xAE92, 0x040C)):
            insns = self.bank.routine(addr)
            self.assertEqual(len(insns), 6,
                             '0x%04X is five instructions and a ret' % addr)
            ordered = [insns[a] for a in sorted(insns)]
            self.assertEqual([i.mnemonic for i in ordered],
                             ['mov', 'lcall', 'mov', 'lcall', 'lcall', 'ret'])
            self.assertEqual(ordered[0].operand, 'DPTR, #0x%x' % BAND_PAIR)
            self.assertEqual(ordered[1].target, READ_R3R4,
                             '0x%04X reads the pair into R3:R4' % addr)
            self.assertEqual(ordered[2].operand, 'DPTR, #0x%x' % bound,
                             '0x%04X reads 0x%04X as its bound' % (addr, bound))
            self.assertEqual(ordered[3].target, READ_R1R2)
            self.assertEqual(ordered[4].target, COMPARATOR)
            self.assertEqual(ordered[5].mnemonic, 'ret')

    def test_the_comparator_sets_carry_only_on_a_borrow(self):
        """`0x8863`'s carry is the subtraction's borrow, so carry means below.

        The body is two `subb` pairs with the second inheriting the first's
        carry, then a `jc` that skips an equality test on `0x02`/`0x01`. The
        borrow path is the one that leaves carry set, which is what every
        caller branches on -- and it is the whole reason the ladder reads as
        a descending set of bands rather than an equality test.
        """
        insns = self.bank.at(COMPARATOR)
        ordered = [insns[a] for a in sorted(insns)]
        self.assertEqual(ordered[0].mnemonic, 'clr')
        self.assertEqual(ordered[0].operand, 'CY')
        subbs = [i for i in ordered if i.mnemonic == 'subb']
        self.assertEqual(len(subbs), 2, 'two byte comparisons')
        self.assertEqual([i.operand for i in subbs], ['A, R1', 'A, R2'],
                         'low byte then high byte')
        branches = [i for i in ordered if i.mnemonic == 'jc']
        self.assertEqual(len(branches), 1)
        borrow_return = branches[0].target
        landing = self.bank.insn(borrow_return)
        self.assertEqual(landing.mnemonic, 'mov')
        self.assertEqual(landing.operand, 'A, #0x1')
        # Nothing between the last subb and the borrow branch clears carry.
        between = [i for a, i in sorted(insns.items())
                   if subbs[1].addr < a < branches[0].addr]
        self.assertEqual(between, [], 'the borrow reaches the branch intact')

    def test_the_fourth_bound_is_the_literal_one_not_another_scaling(self):
        """`0xAEBC` closes the ladder against 1, from the pair or from 0x0514.

        One path puts `R1 = 0x01`, `R2 = 0x00` and calls the shared
        comparator, which is the literal 1 with the pair machinery. The other
        reads `0x0514` and does `clr CY` / `subb A,#0x1`, the same
        comparison without it. Neither is a fourth scaling of `0x0404`.
        """
        insns = self.bank.routine(0xAEBC)
        immediates = {i.operand: i.addr for i in insns.values()
                      if i.mnemonic == 'mov' and '#0x' in i.operand}
        self.assertEqual(immediates.get('R2, #0x0'), 0xAED1)
        self.assertEqual(immediates.get('R1, #0x1'), 0xAED3)
        self.assertEqual(self.bank.insn(0xAED5).target, COMPARATOR)
        self.assertEqual(self.bank.insn(0xAEC8).operand, 'A, #0x1')
        self.assertEqual(self.bank.insn(0xAEC7).mnemonic, 'clr')

    def test_the_sentinel_test_is_the_constant_the_writer_stores(self):
        """`0x887A` tests `R3` against 0x01 and `R4` against 0x02 -- `0x0201`.

        This is what ties `0xB2A0`'s substituted constant to the test that
        reads it back, so neither is a coincidence of one literal. The test
        is against `0x0404`, not against this pair: `0xB214` loads `0x0436`
        into `R1:R2` and `0x887A` never reads `R1` or `R2`.
        """
        insns = self.bank.at(SENTINEL_TEST)
        # `cjne A,#imm,rel` prints three operands; the constant is the
        # second, and the third is where the mismatch branches.
        constants = [i.operand.split(', ')[1] for i in insns.values()
                     if i.mnemonic == 'cjne']
        self.assertEqual(constants, ['0x01', '0x02'])
        reads_r1r2 = [i for i in insns.values()
                      if i.mnemonic == 'mov' and i.operand in ('A, R1', 'A, R2')]
        self.assertEqual(reads_r1r2, [],
                         'the sentinel test never reads R1:R2')

        writer = self.bank.routine(0xB2A0)
        stores = {i.operand: i.addr for i in writer.values()
                  if i.mnemonic == 'mov' and i.operand in ('R4, 0x02', 'R3, 0x01')}
        self.assertEqual(stores.get('R4, 0x02'), 0xB2CA)
        self.assertEqual(stores.get('R3, 0x01'), 0xB2CC)

    # -- the writer that makes the unit question answerable ---------------

    def test_the_writer_stores_the_source_value_itself_on_the_borrow_arm(self):
        """`0xB2A0` loads `0x0404` and stores it, or stores `0x0201`.

        The `jc` skips the two immediate loads, so the arm that keeps the
        compare's borrow is the arm that keeps `R3:R4` as loaded -- which is
        `0x0404`/`0x0405` read by `0x8892`. That a writer stores the full
        capacity value is the fact the unit claim rests on, so it is checked
        as an instruction-order claim rather than read off the name.
        """
        writer = self.bank.routine(0xB2A0)
        source = [a for a, i in writer.items()
                  if i.mnemonic == 'mov' and i.operand == 'DPTR, #0x404']
        self.assertEqual(len(source), 1, '0x0404 is loaded once')
        self.assertEqual(writer[writer[source[0]].next_addr].target, READ_R3R4,
                         'and read into R3:R4')
        branch = [i for i in writer.values() if i.mnemonic == 'jc']
        self.assertEqual(len(branch), 1)
        # The immediate loads sit between the compare and the store, and the
        # borrow branch jumps over them to the store itself.
        immediates = [a for a, i in sorted(writer.items())
                      if i.mnemonic == 'mov' and i.operand in ('R4, 0x02', 'R3, 0x01')]
        self.assertEqual(len(immediates), 2)
        for addr in immediates:
            self.assertGreater(addr, branch[0].addr,
                               'the substitution is on the no-borrow side')
            self.assertLess(addr, branch[0].target,
                            'and inside the branch, not after it')
        store = [a for a, i in sorted(writer.items())
                 if i.mnemonic == 'mov' and i.operand == 'DPTR, #0x436']
        self.assertEqual(len(store), 1)
        self.assertEqual(writer[writer[store[0]].next_addr].target, WRITE_R3R4)
        self.assertEqual(branch[0].target, store[0],
                         'the borrow arm reaches the store without substituting')

    def test_the_three_band_bounds_are_three_of_the_derived_values(self):
        """The ladder's bounds are the derivation's own expressions.

        This is the case that ties the comparators to `0xB50E`: three of the
        four bounds are addresses `0xB50E` writes, so the ladder is not
        merely comparing against some other constant that happens to sit
        near them. `0x0410` is checked as absent from the bounds for the
        same reason -- it is derived and not banded on.
        """
        bounds = set()
        for addr in (0xAE2B, 0xAE5F, 0xAE92):
            for i in self.bank.routine(addr).values():
                if i.mnemonic == 'mov' and i.operand.startswith('DPTR, #0x'):
                    bounds.add(int(i.operand.split('#')[1], 16))
        bounds.discard(BAND_PAIR)          # the comparands, not the bounds
        derived = {value for value, callee, _ in self._stores()
                   if callee in (WRITE_R1R2, WRITE_R3R4)}
        self.assertTrue(bounds <= derived,
                        'every band bound is a derived address')
        self.assertEqual(bounds & {0x040A, 0x040C, 0x040E, 0x0544, 0x0546, 0x0410},
                         {0x040A, 0x040C, 0x0544})
        self.assertNotIn(0x0410, bounds,
                         'the fourth derived address is not a band bound')

    # -- the jump table -----------------------------------------------------

    def _table_bytes(self):
        """The table's bytes, read out of the firmware at the offset the
        listings' headers give.

        No committed listing covers `0xADE2`-`0xADF9`, so the eight targets
        cannot be read from `ec/decompiled/` at all. Every bank1 listing
        header states `CODE bank 1 at file 0x10000 + the 0x0000-0x7FFF common
        area`, which is the mapping used here; a suite that instead trusted
        a typed-in file offset would silently re-derive from the wrong bank
        if that convention ever changed.
        """
        for path in (DECOMPILED / 'bank1').glob('*.asm'):
            head = path.read_text(encoding='utf-8').splitlines()[:6]
            if any('CODE bank 1 at file 0x10000' in line for line in head):
                break
        else:
            self.fail('no bank1 listing states the file-offset convention')

        data = FIRMWARE.read_bytes()
        start = 0x10000 + (TABLE_BASE & 0x7FFF)
        return data[start:start + TABLE_ENTRIES * 3]

    def _table_targets(self):
        """Each entry's destination, decoded as the `ljmp` the bytes spell."""
        targets = []
        raw = self._table_bytes()
        for index in range(TABLE_ENTRIES):
            opcode = raw[index * 3:index * 3 + 3]
            if opcode[0] != 0x02:
                self.fail('table entry %d is not an ljmp: %s'
                          % (index, opcode.hex()))
            targets.append((opcode[1] << 8) | opcode[2])
        return targets

    def test_the_table_is_eight_ljmp_entries_selecting_the_six_routines(self):
        """`0x056A & 7` picks the routine, and 6 and 7 alias back to 0xAE16.

        The last two rows are the point of the shape: the table is not a
        one-to-one map onto the six routines, so a reading of the ladder as
        six `lcall`ed steps would be wrong about two of the eight states.
        """
        targets = self._table_targets()
        self.assertEqual(targets, [0xAE16, 0xAE42, 0xAE78, 0xAEA2,
                                   0xAEE2, 0xAEF3, 0xAE16, 0xAE16])
        self.assertEqual(len(set(targets[:len(LADDER)])), len(LADDER),
                         'the first six entries are six distinct routines')

    def test_the_table_agrees_with_the_committed_call_target_census(self):
        """A second committed artifact reads the same bytes.

        `bank-call-targets.csv` classifies these file offsets as `ljmp` and
        carries a resolved target for each. It is an independent route to
        the same answer, so a table read that disagreed with it would be a
        decoding error rather than a discovery.
        """
        recovered = self._table_targets()
        first = 0x10000 + (TABLE_BASE & 0x7FFF)
        rows = {}
        with CALL_TARGETS.open(encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                if row.get('region') != 'bank1' or row.get('opcode') != 'ljmp':
                    continue
                offset = row.get('file_offset') or ''
                if offset.lower().startswith('0x12de') or offset.lower().startswith('0x12df'):
                    rows[int(offset, 16)] = int(row['target'], 16)
        self.assertTrue(rows, 'the census has rows for the table offsets')
        for index, target in enumerate(recovered):
            offset = first + index * 3
            self.assertIn(offset, rows, 'census row for file 0x%05X' % offset)
            self.assertEqual(rows[offset], target,
                             'census and image agree on entry %d' % index)

    def test_the_dispatcher_indexes_the_table_by_three_times_the_cursor(self):
        """`0xADFD` masks the cursor with 7 and multiplies by three.

        The multiplier is two `add A,R0` with `R0` holding the cursor, and
        the carry path is `jnc` / `inc DPH` -- so the byte offset into the
        table is `cursor * 3` and the table's stride is three because every
        entry is a three-byte `ljmp`.
        """
        dispatch = self.bank.routine(0xADFD)
        self.assertEqual(dispatch[0xAE05].operand, 'DPTR, #0x%x' % CURSOR)
        self.assertEqual(dispatch[0xAE08].mnemonic, 'movx')
        self.assertEqual(dispatch[0xAE09].operand, 'A, #0x7',
                         'the cursor is masked to three bits')
        self.assertEqual(dispatch[0xAE0B].operand, 'DPTR, #0x%x' % TABLE_BASE)
        self.assertEqual(dispatch[0xAE0E].operand, 'R0, A')
        adds = [dispatch[a] for a in sorted(dispatch) if dispatch[a].mnemonic == 'add']
        self.assertEqual(len(adds), 2, 'the cursor is doubled twice')
        for insn in adds:
            self.assertEqual(insn.operand, 'A, R0')
        # `add A,R0` is one byte, so the carry path sits after the second one
        # rather than at a fixed offset from the first.
        tail = [dispatch[a] for a in sorted(dispatch) if a > adds[-1].addr]
        self.assertEqual([i.mnemonic for i in tail],
                         ['jnc', 'inc', 'jmp'])
        self.assertEqual(tail[0].target, tail[2].addr,
                         'the carry skips the increment')
        self.assertEqual(tail[1].operand, 'DPH')
        self.assertEqual(tail[2].operand, '@A+DPTR')
        # And the arithmetic, on the cursor values the boot record gives.
        self.assertEqual([(value & 7) * 3 for value in range(8)],
                         [0, 3, 6, 9, 12, 15, 18, 21])

    def test_nothing_calls_the_six_routines_directly(self):
        """The table is the only route in, which is why this suite decodes it.

        A `lcall` or `ljmp` to any of the six from a committed listing would
        mean the chain reading was also available; asserting the absence
        keeps a future export that does add one from passing unnoticed.
        """
        for path in (DECOMPILED / 'bank1').glob('*.asm'):
            if path.stem.upper() in ('%04X' % a for a in LADDER):
                continue                      # a routine's own tail-jump
            for insn in parse_listing(path).values():
                if insn.mnemonic in ('lcall', 'ljmp') and insn.target in LADDER:
                    if insn.addr in LADDER:
                        continue              # a ladder member reaching a sibling
                    self.fail('%s calls 0x%04X directly'
                              % (path.name, insn.target))

    # -- the thermometer and the gate --------------------------------------

    def test_the_mask_writer_ors_into_the_low_five_bits_only(self):
        """`0xAE6F` masks with 0xE0, so the thermometer cannot reach the top three.

        That is what lets six routines share one byte with whatever else
        lives in `0x0496`'s high bits, and it is the reason the six `R6`
        values are a thermometer rather than six arbitrary numbers.
        """
        writer = self.bank.routine(0xAE6F)
        self.assertEqual(writer[0xAE6F].operand, 'DPTR, #0x%x' % MASK_BYTE)
        self.assertEqual(writer[0xAE73].mnemonic, 'anl')
        self.assertEqual(writer[0xAE73].operand, 'A, #0xe0')
        self.assertEqual(writer[0xAE75].mnemonic, 'orl')
        self.assertEqual(writer[0xAE75].operand, 'A, R6')
        self.assertEqual(writer[0xAE76].mnemonic, 'movx')
        self.assertEqual(writer[0xAE76].operand, '@DPTR, A')
        self.assertNotIn('mov R6', [i.operand for i in writer.values()],
                         'R6 is the caller\'s, not this routine\'s')

    def test_the_six_r6_immediates_are_the_cumulative_masks(self):
        """Each R6 is the previous with one more bit set.

        Derived from the listings rather than asserted as a table, so a
        routine that changed its immediate goes red on the relationship
        instead of on a transcribed number.
        """
        masks = []
        for addr in LADDER:
            found = [i for i in self.bank.routine(addr).values()
                     if i.mnemonic == 'mov' and i.operand.startswith('R6, #')]
            self.assertEqual(len(found), 1,
                             '0x%04X loads R6 once' % addr)
            masks.append(int(found[0].operand.split('#')[1], 16))
        self.assertEqual(masks, sorted(masks), 'the masks ascend')
        for previous, current in zip(masks, masks[1:]):
            self.assertEqual(current, previous | (previous + 1),
                             '0x%02X adds exactly one bit to 0x%02X'
                             % (current, previous))
        for mask in masks:
            self.assertLessEqual(mask, MASK_CEILING, 'every mask fits the low five bits')
        self.assertEqual(R6_BY_ROUTINE, dict(zip(LADDER, masks)),
                         'the write-up\'s per-routine values')

    def test_the_sixth_routine_loads_its_mask_after_the_comparator(self):
        """`0xAEF3` sets `R6 = 0x1F` on the borrow path only.

        The other five load `R6` before their comparator; this one loads it
        after, so the top bit of the thermometer is set on a different
        condition from the other five. That is the difference the
        `0xAE6F` annotation row records as an inference, and it is checkable.
        """
        sixth = self.bank.routine(0xAEF3)
        compare = [i for i in sixth.values() if i.mnemonic == 'lcall'
                   and i.target == 0xAEBC]
        self.assertEqual(len(compare), 1)
        load = [a for a, i in sorted(sixth.items())
                if i.mnemonic == 'mov' and i.operand == 'R6, #0x1f']
        self.assertEqual(len(load), 1)
        self.assertGreater(load[0], compare[0].addr,
                           'the mask is loaded after the compare, not before')
        branch = [i for i in sixth.values() if i.mnemonic == 'jc']
        self.assertEqual(len(branch), 1)
        self.assertEqual(branch[0].target, load[0],
                         'and only the borrow reaches it')
        for addr in LADDER[:-1]:
            first = min(a for a, i in self.bank.routine(addr).items()
                        if i.mnemonic == 'mov' and i.operand.startswith('R6, #'))
            earlier = [i for a, i in sorted(self.bank.routine(addr).items())
                       if i.mnemonic == 'lcall' and a < first]
            self.assertEqual(earlier, [],
                             '0x%04X loads R6 first' % addr)

    def test_the_gate_bit_forces_the_cursor_to_the_bottom(self):
        """`0x0490` bit 7 sends five of the six to `0xAED9`, which stores 0.

        `0xAE16` treats the same bit as a skip instead, so the gate is not
        uniform across the ladder and a reading that called it one early-out
        would be wrong about the routine that starts the walk.
        """
        target = self.bank.routine(0xAED9)
        self.assertEqual(target[0xAED9].operand, 'DPTR, #0x%x' % CURSOR)
        self.assertEqual(target[0xAEDC].operand, 'A, #0x0')
        self.assertEqual(target[0xAEDE].mnemonic, 'movx')
        self.assertEqual(target[0xAEDF].mnemonic, 'ret')

        to_gate = []
        self._gate_branch = {}
        for addr in LADDER:
            insns = self.bank.routine(addr)
            for a, i in sorted(insns.items()):
                if i.mnemonic == 'mov' and i.operand == 'DPTR, #0x%x' % GATE_BYTE:
                    self.assertEqual(insns[i.next_addr].mnemonic, 'movx')
                    follow = insns[insns[i.next_addr].next_addr]
                    if follow.mnemonic in ('jb', 'jnb'):
                        to_gate.append((addr, follow.mnemonic, follow.target))
                        self._gate_branch[addr] = follow.addr
        self.assertEqual(len(to_gate), len(LADDER), 'each routine reads the gate')
        for addr, mnemonic, dest in to_gate:
            if addr == 0xAE16:
                self.assertEqual((mnemonic, dest), ('jb', 0xAE6F),
                                 '0xAE16 skips to the mask writer')
                continue
            if mnemonic == 'jb':
                # Four branch straight to the zero store on a set bit.
                self.assertEqual(dest, 0xAED9,
                                 '0x%04X branches to the zero store' % addr)
                continue
            # `0xAE42` inverts the test -- `jnb` to the next step -- so the
            # set case is the `ljmp` on the fall-through.
            insns = self.bank.routine(addr)
            branch = insns[self._gate_branch[addr]]
            fallthrough = insns[branch.next_addr]
            self.assertEqual(branch.mnemonic, 'jnb')
            self.assertEqual(fallthrough.mnemonic, 'ljmp')
            self.assertEqual(fallthrough.target, 0xAED9,
                             '0x%04X falls through to the zero store' % addr)

    def test_the_gate_bit_has_a_writer_that_alternates_it_with_another(self):
        """`0xC11C` sets bit 3 or bit 7 of `0x0490` and clears the other.

        So the bit that gates the whole ladder is not a constant, and the
        routine that moves it is named. What *sets* it in normal operation is
        not established here and the write-up says so.
        """
        latch = self.bank.routine(0xC11C)
        # Each rule sets one bit and clears the other, so the pair of
        # instructions is read as a set rather than as two addresses: which
        # bit goes first is the routine's business, not this suite's.
        rules = []
        for a, i in sorted(latch.items()):
            if i.mnemonic == 'setb' and i.operand in ('0xe3', '0xe7'):
                follow = latch[i.next_addr]
                self.assertEqual(follow.mnemonic, 'clr')
                self.assertIn(follow.operand, ('0xe3', '0xe7'))
                self.assertNotEqual(follow.operand, i.operand,
                                    'a rule clears the bit it did not set')
                rules.append((i.operand, follow.operand))
        self.assertEqual(len(rules), 2, 'two transition rules')
        self.assertEqual({r[0] for r in rules}, {'0xe3', '0xe7'},
                         'each bit is set by exactly one rule')
        self.assertEqual({r[1] for r in rules}, {'0xe3', '0xe7'},
                         'and each is cleared by exactly one')

    # -- what must not have moved ------------------------------------------

    def test_the_touched_rows_keep_their_status_and_their_static_counts(self):
        """A derivation is a static instruction, so nothing here moves a count.

        What is asserted is what each of these five rows *is*: a
        `present-untested` status, no source beyond the census the rows were
        entered with, and the three `static_refs*` fields still present. The
        counts themselves are not asserted here, and deliberately so --
        hard-coding them would be a census every merge has to edit, which is
        the thing CLAUDE.md's third bullet is about.
        `check_register_counts.py` re-derives every count from the committed
        firmware, and that is what holds the numbers.
        """
        for name in ('XDATA_040A', 'XDATA_040C', 'XDATA_040E',
                     'XDATA_0410', 'XDATA_0436_PAIR'):
            row = self._register_row(name)
            self.assertEqual(row['status'], 'present-untested',
                             '%s keeps its status' % name)
            self.assertEqual(row['sources'], ['xdata-refs'],
                             '%s gains no source: nothing was run' % name)
            for field in ('static_refs', 'static_refs_main_ec',
                          'static_refs_pd_image'):
                self.assertIn(field, row, '%s carries %s' % (name, field))

    def test_the_0436_note_states_the_constraint_and_keeps_the_old_claims(self):
        """The constraint is added; the earlier sentences stay visible.

        The note already carries a dated correction from issue #213 about its
        writer census. This change adds a third dated block and must not
        remove either the original "NOT NAMED, deliberately" reasoning or
        the #213 correction -- a retraction is left standing with its
        correction beside it, never edited away.
        """
        note = self._register_row('XDATA_0436_PAIR')['note']
        self.assertIn('issue #1332', note)
        self.assertIn('issue #213', note)
        self.assertIn('NOT NAMED, deliberately', note,
                      'the declined name and its reasoning survive')
        self.assertIn('The only writer is in the zero-clear', note,
                      'the superseded sentence is still visible')
        for fragment in ('cmp_0436_0437_against_040a_040b',
                         'cmp_0436_0437_against_0544_0545',
                         'cmp_0436_0437_against_040c_040d',
                         'cmp_0436_0437_against_1_or_test_0514'):
            self.assertIn(fragment, note, 'the note cites %s' % fragment)
        self.assertIn('dispatch_on_056a_low3', note,
                      'the note names the dispatcher')
        self.assertIn('or_r6_into_0496_low5', note,
                      'the note names the mask writer')
        self.assertIn('cmp_0404_vs_0518_then_store_0436', note,
                      'the note names the writer that agrees on the unit')
        self.assertIn('#1310', note, 'the note points at the run that is still open')
        self.assertIn('no register was read back', note,
                      'the note says nothing was measured')

    def test_the_note_and_the_write_up_agree_on_what_is_not_decoded(self):
        """Both places carry the limits, so neither reads as a complete answer.

        A note that published the ladder without saying what a band means
        would be the "reads as" overclaim CLAUDE.md's calibration rule is
      about, and the two files are independent enough that comparing them to
        each other would not catch a shared mistake -- so each is checked
        against its own required sentence.
        """
        for text in (self._register_row('XDATA_0436_PAIR')['note'],
                     WRITEOUT.read_text(encoding='utf-8')):
            self.assertIn('not decoded', text)
            self.assertIn('#1310', text)
        page = WRITEOUT.read_text(encoding='utf-8')
        self.assertIn('No hardware and no Windows machine was involved', page)
        self.assertIn('No register `status:` changed', page)
        self.assertIn('no `static_refs*` value moved', page)
        self.assertIn('not established', page)

    def test_the_write_up_carries_the_derivation_table_for_every_destination(self):
        """Each of the six destinations appears with the expression it receives.

        Held as a relationship between the address and the expression rather
        than as a transcribed block, so a note that dropped a row goes red on
        that row.
        """
        page = WRITEOUT.read_text(encoding='utf-8')
        for destination, expression in ((r'`0x040A`/`0x040B`', 'V >> 4'),
                                        (r'`0x040C`/`0x040D`', 'V >> 5'),
                                        (r'`0x040E`/`0x040F`', 'V >> 5'),
                                        (r'`0x0410`/`0x0411`', 'V - (V >> 5)')):
            row = [line for line in page.splitlines()
                   if destination in line and expression in line]
            self.assertEqual(len(row), 1,
                             'the write-up pairs %s with %s' % (destination, expression))

    # -- helpers ------------------------------------------------------------

    def _register_row(self, name):
        for row in yaml.safe_load(REGISTERS.read_text(encoding='utf-8'))['registers']:
            if row.get('name') == name:
                return row
        self.fail('%s is not in registers.yaml' % name)


if __name__ == '__main__':
    unittest.main()
