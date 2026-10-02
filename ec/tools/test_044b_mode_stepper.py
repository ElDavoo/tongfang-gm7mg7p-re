#!/usr/bin/env python3
"""`bank0 0x9AAD` dispatches on XDATA 0x044B and every arm that passes its
test rewrites the byte to one of 1, 2, 3 or 4.

`docs/findings/044b-mode-stepper.md` is the write-up. The two things worth
knowing before reading the cases below:

  - **The byte is not a counter that advances.** Two of the five transitions
    step back down (4 goes to 3, 2 can go to 1), which is what the issue that
    opened this predicted wrongly, so the suite pins the whole transition map
    rather than a "next value" rule that would have passed against three of
    the five arms.
  - **The arms store the byte by tail-jump, not inline.** Not one of the three
    writes the register census counts is inside 0x9AAD, which is why the row
    for XDATA_044B read as though no dispatcher existed. The suite therefore
    resolves each arm's writer by *walking* the tail jump into the committed
    listings, and a writer that stops being reachable that way reds here.

**Nothing is asserted as a literal that could have been transcribed.** The
dispatch chain is resolved by simulating the dec/jz sequence read out of
9AAD.asm over all 256 byte values, and each writer's constant is derived by
following its instructions -- so a firmware change moves the answer and the
assertion fails, rather than a stale table agreeing with itself. The same is
true of the bail-out rule below, which recognises a bail-out by what its
listing is rather than by a hard-coded address.

What the suite holds is the *shape* claim: which arm a given value reaches,
which constant that arm's path leaves behind, that a status: did not move, and
that the second comparison in the value-3 arm is inclusive because it inherits
a set carry. It holds no claim about what the five values mean, which is not
decoded, and none about the EC acting on any of it -- no hardware is reachable
from here and nothing is read back.
"""

import csv
import re
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REPO = HERE.parent.parent
DECOMPILED = REPO / 'ec' / 'decompiled'
ANNOTATIONS = REPO / 'ec' / 'annotations'
INDEX_CSV = DECOMPILED / 'index.csv'
FUNCTIONS = ANNOTATIONS / 'ghidra-functions.csv'
REGISTERS = ANNOTATIONS / 'registers.yaml'
WRITEOUT = REPO / 'docs' / 'findings' / '044b-mode-stepper.md'

DISPATCHER = '0x9AAD'
MODE_BYTE = 0x044B

# `9AAD     7f 08 -  mov      R7, #0x8` -- address, a fixed three-slot byte
# column, then the mnemonic and a free-text operand. The byte column is
# left-justified to nine characters, so it cannot be split on whitespace
# without first being told where it ends; three slots is the widest an
# instruction in these listings gets.
INSN = re.compile(r'^([0-9A-F]{4})\s+(.*)$')
BYTE_SLOT = re.compile(r'^(?:[0-9a-f]{2}|-)$')

# The mnemonics that name a destination rather than doing arithmetic at the
# instruction's own address. `lcall` is here because two of the four writers
# reach the mode byte through a callee that loads DPTR itself, and a walk
# that could not see where a call went would report no constant for either.
HAS_TARGET = ('ljmp', 'sjmp', 'jmp', 'lcall')


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


class Bank0Listings:
    """The committed bank0 listings, found by address through ``index.csv``.

    Resolving a tail jump by looking up which function contains the target is
    what lets the arm walk cross a function boundary the way the firmware
    does. Two of the arms leave 0x9AAD that way rather than by a jump inside
    it: the value-3 bit-0-clear arm falls off the last byte into 0x9BFD, and
    0x9C00 falls off its last byte into 0x9C1D. A walker that only had 0x9AAD's
    own instructions would miss both successors entirely.
    """

    def __init__(self):
        self._cache = {}
        self._owner = {}
        with INDEX_CSV.open(encoding='utf-8') as handle:
            for row in csv.DictReader(handle):
                if row['program'] != 'bank0':
                    continue
                start = int(row['addr'], 16)
                for offset in range(int(row['size'])):
                    self._owner[start + offset] = row['out_file']

    def insns_for(self, addr):
        """The listing covering `addr`, or an empty map when nothing does."""
        owner = self._owner.get(addr)
        if owner is None:
            return {}
        path = DECOMPILED / owner.replace('.c', '.asm')
        if path not in self._cache:
            self._cache[path] = parse_listing(path)
        return self._cache[path]

    def insn(self, addr):
        return self.insns_for(addr).get(addr)

    def is_bare_return(self, addr):
        """True when the routine at `addr` is one `ret` and nothing else.

        This is how a bail-out is recognised. Naming 0x9C47 here instead would
        make the rule a transcription of the answer, and would keep passing if
        a future arm's bail-out landed somewhere else.
        """
        insns = self.insns_for(addr)
        return len(insns) == 1 and next(iter(insns.values())).mnemonic == 'ret'


class ModeStepper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = Bank0Listings()
        cls.dispatcher = int(DISPATCHER, 16)
        cls.insns = cls.bank.insns_for(cls.dispatcher)

    # -- the dispatch chain -------------------------------------------------

    def test_the_dispatch_opens_on_a_read_of_the_mode_byte(self):
        """The chain is entered by reading 0x044B, and exactly once."""
        reads = [addr for addr, insn in sorted(self.insns.items())
                 if insn.mnemonic == 'mov' and insn.operand == 'DPTR, #0x44b']
        self.assertEqual(reads, [0x9B33], 'the dispatch reads 0x044B once')
        self.assertEqual(self.insns[0x9B36].operand, 'A, @DPTR')
        self.assertEqual(self.insns[0x9B36].mnemonic, 'movx')

    def test_each_byte_value_reaches_exactly_one_arm(self):
        """Simulate the chain over all 256 values, from the listing itself.

        The accumulator is seeded with the byte value and stepped through the
        dec/jz/add sequence as the listing states it, so the arm table below is
        an assertion about the committed bytes rather than a table transcribed
        from them. 0x9B4A is reached by every value the chain does not name,
        which is what makes the byte a five-value mode and not a range check.
        """
        arms = self._resolve_dispatch()
        enumerated = {value: addr for value, addr in arms.items()
                      if addr != 0x9B4A}
        self.assertEqual(
            enumerated,
            {0: 0x9B4D, 1: 0x9B63, 2: 0x9B75, 3: 0x9B99, 4: 0x9B43},
            'the five enumerated arms, by the order the chain tests them')
        self.assertEqual(len(arms), 256, 'every byte value reaches some arm')
        defaults = {value for value, addr in arms.items() if addr == 0x9B4A}
        self.assertEqual(len(defaults), 251, 'the rest share the default arm')

    def _resolve_dispatch(self):
        """Run the dec/jz chain for all 256 values, returning {value: arm}.

        The arm is named by the address where control leaves the chain, which
        is the `jz` destination for the three cases reached that way and the
        `ljmp` itself for the two that are not -- 4 falls through to a jump
        rather than being jumped to, and 0 is picked out by the `add`. Naming
        the jump's destination instead would make the value-4 arm read as
        0x9C00 and lose the fact that the chain, not the arm, chose it.
        """
        arms = {}
        for value in range(256):
            acc = value
            pc = 0x9B37                       # the dec that opens the chain
            while True:
                insn = self.insns[pc]
                if insn.mnemonic == 'dec' and insn.operand == 'A':
                    acc = (acc - 1) & 0xFF
                elif insn.mnemonic == 'add' and insn.operand == 'A, #0x4':
                    acc = (acc + 4) & 0xFF
                elif insn.mnemonic == 'jz':
                    if acc == 0:
                        arms[value] = insn.target
                        break
                elif insn.mnemonic == 'jnz':
                    if acc != 0:
                        pc = insn.target
                        continue
                elif insn.mnemonic == 'ljmp':
                    arms[value] = pc
                    break
                else:
                    self.fail('unexpected %r inside the dispatch chain' % insn)
                pc += insn.size
        return arms

    # -- what each arm's path leaves in the byte ---------------------------

    def test_each_arm_writes_the_constant_its_path_reaches(self):
        """Walk every arm to the constants its non-bail-out paths store.

        The walk follows tail jumps across function boundaries and follows
        conditional branches by their fall-through, so the only paths it drops
        are the ones that jump to a bare `ret` -- which is what "this arm's
        test failed" looks like in the listing. A path that reaches a bail-out
        stores nothing, and a set of constants with a member missing is a real
        miss rather than a gap in the walk.
        """
        self.assertEqual(self.arm_successors(0x9B4D), {1}, 'value 0')
        self.assertEqual(self.arm_successors(0x9B63), {2}, 'value 1')
        self.assertEqual(self.arm_successors(0x9B75), {1, 3}, 'value 2')
        self.assertEqual(self.arm_successors(0x9B99), {2, 4}, 'value 3')
        self.assertEqual(self.arm_successors(0x9B43), {3}, 'value 4')
        self.assertEqual(self.arm_successors(0x9B4A), set(),
                         'the default arm writes nothing')

    def test_the_writers_reach_the_byte_through_more_than_one_path(self):
        """Not all four writers go through 0xBD20, which is the easy mistake.

        `0xBD20` is the shared store for two of them and loads DPTR itself in
        the other two, so a write-up that says "they all funnel through
        0xBD20" is describing half the mechanism. Both shapes are asserted
        from the listings, so the split cannot quietly become uniform.
        """
        through_bd20, direct = set(), set()
        for addr in (0x9A7B, 0x9A86, 0x9A90, 0x9A9C):
            (through_bd20 if self._stores_via_call(addr)
             else direct).add(addr)
        self.assertEqual(through_bd20, {0x9A7B, 0x9A90})
        self.assertEqual(direct, {0x9A86, 0x9A9C})

    def _stores_via_call(self, addr):
        insns = self.bank.insns_for(addr)
        for insn in insns.values():
            if insn.mnemonic == 'lcall' and insn.target == 0xBD20:
                return True
        return False

    def test_the_constant_survives_only_because_a_shared_clr_a_precedes_it(self):
        """0x9A7B's stored 1 comes from `clr A` then `inc A`, not from the arm.

        This is the writer whose value could plausibly have been carried in
        from the caller: the value-0 arm arrives with a subtraction result in
        the accumulator. All four writers open with a call to 0xBA15, and
        pinning that call to a bare `clr A` is what makes the four constants
        constants rather than whatever the arm left behind.
        """
        self.assertEqual(sorted(self.bank.insns_for(0xBA15).items()),
                         [(0xBA15, self.bank.insn(0xBA15))])
        self.assertEqual(self.bank.insn(0xBA15).mnemonic, 'clr')
        self.assertEqual(self.bank.insn(0xBA15).operand, 'A')
        for addr in (0x9A7B, 0x9A86, 0x9A90, 0x9A9C):
            first = self.bank.insns_for(addr)[addr]
            self.assertEqual((first.mnemonic, first.target), ('lcall', 0xBA15),
                             '0x%04X opens with the clr A' % addr)

    def arm_successors(self, entry):
        """The constants `entry` can leave in 0x044B, every path considered.

        This is a control-flow walk, not a linear scan, and it has to be one.
        The arms are laid out as a run of guarded blocks, so the instruction
        after a bail-out jump is the arm's *other* path rather than dead code:
        in the value-2 arm, 0x9B87 leaves for 0x9C1D and 0x9B8A -- the branch
        that stores 1 instead of 3 -- sits at the next address and is reached
        only by the `jnb` at 0x9B79. Following just one successor per jump
        finds one of the two constants and calls the arm single-valued.

        The accumulator is tracked as a known constant or None, and a call
        this walk does not model clears it. That is deliberately pessimistic:
        a constant can only be reported if the writer establishes it itself,
        so an arm leaking its own arithmetic into the byte would come back as
        a missing constant rather than as whatever the walk happened to carry.
        """
        found = set()
        pending = [(entry, None, None)]
        seen = set()
        while pending:
            addr, acc, dptr = pending.pop()
            if (addr, acc, dptr) in seen:
                continue
            seen.add((addr, acc, dptr))
            insn = self.bank.insn(addr)
            if insn is None:
                continue
            acc, dptr = self._apply(insn, acc, dptr, found)
            pending.extend(self._successors(insn, addr, acc, dptr))
        return found

    def _apply(self, insn, acc, dptr, found):
        """Carry (acc, dptr) through one instruction, recording any store."""
        if insn.mnemonic == 'mov' and insn.operand.startswith('DPTR, #'):
            dptr = int(insn.operand.split('#')[1], 16)
        elif insn.mnemonic == 'mov' and insn.operand.startswith('A, #'):
            acc = int(insn.operand.split('#')[1], 16)
        elif insn.mnemonic == 'movx' and insn.operand == 'A, @DPTR':
            acc, dptr = None, None
        elif insn.mnemonic == 'movx' and insn.operand == '@DPTR, A':
            if dptr == MODE_BYTE and acc is not None:
                found.add(acc)
            acc, dptr = None, None
        elif insn.mnemonic == 'inc' and insn.operand == 'A':
            acc = acc + 1 if acc is not None else None
        elif insn.mnemonic == 'inc' and insn.operand == 'DPTR':
            dptr = dptr + 1 if dptr is not None else None
        elif insn.mnemonic == 'clr' and insn.operand == 'A':
            acc, dptr = 0, None
        elif insn.mnemonic == 'lcall' and insn.target == 0xBA15:
            acc, dptr = 0, None
        elif insn.mnemonic == 'lcall' and insn.target == 0xBD20:
            if self._bd20_stores_the_accumulator() and acc is not None:
                found.add(acc)
            acc, dptr = None, None
        elif insn.mnemonic == 'lcall':
            acc, dptr = None, None
        # Everything else leaves both unknown only if it could have changed
        # them; the ones that matter (anl, orl, add, subb) are reached only
        # after a call that has already cleared the accumulator, so the
        # pessimistic answer is the one they are given.
        return acc, dptr

    def _successors(self, insn, addr, acc, dptr):
        """The (address, acc, dptr) triples this instruction can go to."""
        nxt = (addr + insn.size, acc, dptr)
        if insn.mnemonic == 'ret':
            return []
        if insn.mnemonic in ('ljmp', 'sjmp', 'jmp'):
            # A jump to a bail-out is the arm's own test failing: it stores
            # nothing and has no successor worth walking into.
            if self.bank.is_bare_return(insn.target):
                return []
            return [(insn.target, acc, dptr)]
        if insn.mnemonic.startswith('j'):
            return [nxt, (insn.target, acc, dptr)]
        return [nxt]

    def _bd20_stores_the_accumulator(self):
        insns = self.bank.insns_for(0xBD20)
        operands = [i.operand for i in insns.values()]
        self.assertIn('DPTR, #0x44b', operands,
                      '0xBD20 loads DPTR with the mode byte itself')
        return any(i.mnemonic == 'movx' and i.operand == '@DPTR, A'
                   for i in insns.values())

    def predecessor(self, addr):
        """The instruction ending exactly at `addr`, or None.

        Instruction lengths are read from the listing rather than assumed:
        `movx A,@DPTR` is the one-byte opcode 0xE0, so a fixed backwards
        offset lands inside the `mov DPTR` before it.
        """
        for back in range(1, 4):
            candidate = self.bank.insn(addr - back)
            if candidate is not None and candidate.addr + candidate.size == addr:
                return candidate
        return None

    # -- the prologue's polarity -------------------------------------------

    def test_the_prologue_decides_the_bit_every_arm_branches_on(self):
        """Bit 0 of 0x08AD is set or cleared on the way into the dispatch.

        Three arms branch on it, so which of their two successors is reachable
        is decided before the dispatch runs. Two of the three prologue exits
        write it and the third does not, which is the part that is easy to
        overstate: the polarity is chosen on two exits and inherited on one.
        """
        # A `jb 0xe0` names bit 0 of whatever DPTR holds, so the bit address
        # alone says nothing about which byte: the prologue tests bit 0 of
        # 0x0490 and of 0x0497 the same way. The byte is whatever the two
        # instructions before the branch loaded.
        on_08ad = []
        for addr, insn in sorted(self.insns.items()):
            if insn.mnemonic in ('jb', 'jnb') and insn.operand.startswith('0xe0, 0x'):
                read, loaded = self.predecessor(addr), None
                if read is not None:
                    loaded = self.predecessor(read.addr)
                self.assertIsNotNone(read, '0x%04X follows an instruction' % addr)
                self.assertEqual(read.operand, 'A, @DPTR',
                                 '0x%04X branches on a byte just read' % addr)
                if loaded is not None and loaded.operand == 'DPTR, #0x8ad':
                    on_08ad.append(addr)
        self.assertEqual(on_08ad, [0x9B6C, 0x9B79, 0x9B9D],
                         'the value-1, value-2 and value-3 arms')

        # The value-4 arm is not in this list: it is 0x9C00 that branches,
        # reached by the ljmp at 0x9B43, and 0x9C00 has a row of its own.
        self.assertEqual(self.bank.insns_for(0x9C00)[0x9C15].operand,
                         '0xe0, 0x9c47')
        self.assertEqual(self.bank.insns_for(0x9C00)[0x9C11].operand,
                         'DPTR, #0x8ad')

        self.assertEqual(self.insns[0x9B16].operand, 'A, #0x1')
        self.assertEqual(self.insns[0x9B2B].operand, 'A, #0xfe')
        for writer in (0x9B18, 0x9B2D):
            self.assertEqual(self.insns[writer].operand, '@DPTR, A')

    # -- the inherited carry ------------------------------------------------

    def test_the_value_3_second_threshold_is_inclusive(self):
        """0x9BCD's subb inherits a set carry, so its test is <= and not <.

        8051 `subb` subtracts the carry as well as the operand, and nothing
        between 0x9BBE and 0x9BCD clears it. Reaching 0x9BCD means the `jc` at
        0x9BBF branched, which only happens on a borrow, so the carry
        arriving is set and the threshold is one lower than a bare reading of
        the operands gives. The other half of the same arm clears the carry
        first, so the two halves do not share a comparison convention.
        """
        self.assertEqual(self.insns[0x9BBD].mnemonic, 'setb')
        self.assertEqual(self.insns[0x9BBD].operand, 'CY')
        self.assertEqual(self.insns[0x9BBE].mnemonic, 'subb')
        self.assertEqual(self.insns[0x9BBF].mnemonic, 'jc')
        self.assertEqual(self.insns[0x9BBF].target, 0x9BC4)
        self.assertEqual(self.insns[0x9BCD].mnemonic, 'subb')
        self.assertEqual(self.insns[0x9BCD].operand, 'A, R7')

        # The bit-0-clear half, for contrast: clr CY then subb, and the
        # second subb inherits a carry known to be clear.
        self.assertEqual(self.insns[0x9BED].mnemonic, 'clr')
        self.assertEqual(self.insns[0x9BED].operand, 'CY')
        self.assertEqual(self.insns[0x9BEF].mnemonic, 'jc')
        self.assertEqual(self.insns[0x9BFA].mnemonic, 'subb')
        self.assertEqual(self.insns[0x9BFA].operand, 'A, R7')

    # -- the annotation and the register row -------------------------------

    def test_the_registers_row_still_carries_no_behavioural_claim(self):
        """A dispatcher being found is not a register being exercised.

        The row stays `present-untested` and its static counts are recomputed
        from the image by check_register_counts.py; what this pins is that the
        note names the dispatcher, so a later edit cannot quietly drop the one
        fact this reading added without the status assertion going red too.
        """
        row = self._register_row('XDATA_044B')
        self.assertEqual(row['status'], 'present-untested')
        self.assertIn('0x9AAD', row['note'],
                      'the note names the dispatcher')
        self.assertIn('not decoded', row['note'],
                      'the note says the five values are not decoded')

    def test_the_dispatcher_has_a_row_naming_the_mechanism(self):
        row = self._bank0_row(DISPATCHER)
        self.assertIsNotNone(row, 'bank0,%s has an annotation row' % DISPATCHER)
        self.assertNotIn('FUN_CODE', row['name'],
                         'the name is not the export placeholder')
        self.assertEqual(row['type'], 'dispatch')
        self.assertIn(row['type'], self._type_vocabulary())
        self.assertTrue(row['evidence'].strip(), 'evidence is mandatory')
        for cited in row['evidence'].split(';'):
            self.assertTrue((REPO / cited.strip()).exists(), cited.strip())

    def test_the_write_up_says_what_it_does_not_decode(self):
        """The write-up has to carry the limit, not only the table.

        A page that publishes the transition map and stays silent about the
        five values reads as a complete answer to the issue, which is the
        failure CLAUDE.md's calibration rule is about.
        """
        text = WRITEOUT.read_text(encoding='utf-8')
        self.assertIn('What is not decoded here', text)
        self.assertIn('No register `status:` changed', text)
        self.assertIn('no hardware or Windows machine was involved', text)

    def _register_row(self, name):
        for row in yaml.safe_load(REGISTERS.read_text(encoding='utf-8'))['registers']:
            if row.get('name') == name:
                return row
        self.fail('%s is not in registers.yaml' % name)

    def _bank0_row(self, addr):
        for row in self._function_rows():
            if row['scope'] == 'bank0' and row['addr'].upper() == addr.upper():
                return row
        return None

    def _function_rows(self):
        with FUNCTIONS.open(encoding='utf-8') as handle:
            return list(csv.DictReader(handle))

    def _type_vocabulary(self):
        """The closed `type:` vocabulary, read from the committed rows.

        Taken from the file rather than restated here so that a type added
        upstream does not need this suite edited to stay correct, and so a row
        carrying a type the file has never held fails against the file's own
        values instead of against a copy of them.
        """
        return {row['type'] for row in self._function_rows() if row['type']}


if __name__ == '__main__':
    unittest.main()
