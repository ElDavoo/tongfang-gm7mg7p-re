#!/usr/bin/env python3
"""The caller chain into `0xA7C8`, and the two `0x0741` facts the PL race turns
on (issue #109).

`docs/findings/a7c8-dispatch-slot-and-pl-race.md` answers "what calls the
routine whose tail holds the only main-EC writer of PL1/PL2/PL4" and decides
the host-writes-PLs / EC-zeroes-PLs race. This file holds the byte facts that
answer stands on, read from `ec/firmware/GMxMGxx_11.800` rather than from a
re-run of any scan that produced a table the write-up quotes -- so a
regenerated table that disagreed fails instead of passing on a stale pair, the
`test_scheduler_cycle.py` pattern.

Two of the pins are negatives and both are written as scans that can fail.
`TheOemBitZeroRevocation.test_no_instruction_sets_0741_bit0` is a direct-`MOV
DPTR` census with the same eight-instruction window `trace_xdata_refs.py`
classifies with, and it names its regions on the failure. It is blind to a
blind whole-byte store beyond its window and to any store through a DPTR built
at run time; `common 0x7151` in this same image is a dispatch mechanism a
two-opcode scan cannot see, and `manual-fan-ctrl-0751.md` section 6 is the
worked counter-example on a second address. Nothing here says a register is
absent, and nothing here is a behavioural observation: no byte was read back
and no hardware was reached.

The polarity check comes first because it is the one thing a reader will
re-derive backwards and because everything downstream depends on it: `jnb
acc.0` jumps when bit 0 is **clear**, so an odd `0x45` abandons the frame at
`0x0DCE` and only an even one reaches the case table -- whose nine keys are
all even. A decoder that got that bit wrong would still resolve every address
in this file correctly and would put `0xA7C8` on the wrong turn of the
scheduler.
"""
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import disasm8051

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'

IMAGE = FIRMWARE.read_bytes()

# The three main-EC regions as (name, file lo, file hi, runtime base), after
# trace_xdata_refs.REGIONS: the common area is file offset == runtime address,
# and both bank windows are make_bank_image.py's arrangement, where runtime
# 0x8000 sits at the bank's own file offset. The PD image is the fourth region
# and the one scan below names separately.
REGIONS = (('common', 0x00000, 0x08000, 0x0000),
           ('bank0', 0x08000, 0x10000, 0x8000),
           ('bank1', 0x10000, 0x18000, 0x8000))

PD_IMAGE = 0x20000

COMMON = IMAGE[:0x8000]
BANK0 = IMAGE[0x8000:0x10000]

# trace_xdata_refs.py's classification window. Matched rather than chosen, so
# "the same method" in the write-up means the same eight instructions.
WINDOW = 8


def at(addr, n=1):
    """The n bytes at `addr` in the common image, as a hex string."""
    return COMMON[addr:addr + n].hex(' ')


def common(addr, n=1):
    """The n bytes at `addr` in the common image."""
    return COMMON[addr:addr + n]


def bank0(runtime, n=1):
    """The n bytes at `runtime` in bank0."""
    off = runtime - 0x8000
    return BANK0[off:off + n]


def bank0_at(runtime, n=1):
    """The n bytes at `runtime` in bank0, as a hex string."""
    return bank0(runtime, n).hex(' ')


def mnemonic(data, addr, runtime):
    """disasm8051.mnemonic, named so the assertions read as decodes."""
    return disasm8051.mnemonic(data, addr, runtime)


def target(runtime, opcode, disp):
    """disasm8051.relative_target, named so the assertions below read as
    arithmetic rather than as table lookups. PC-relative branches only -- an
    `ljmp` carries an absolute address, which is what `branch` is for."""
    return disasm8051.relative_target(opcode, disp, runtime)


def branch(runtime, raw):
    """The destination of a `sjmp`/`ljmp`, from the bytes at `runtime`.

    `sjmp` is two bytes and its operand is a signed displacement from the next
    instruction; `ljmp` is three and its operand is the absolute address.
    Reading either with the other's rule lands in the middle of a neighbouring
    instruction, which is the shape of mistake `manual-fan-ctrl-0751.md`
    section 9 spends a paragraph on. `raw` may carry more bytes than the
    instruction does -- these windows come out of a byte slice, not a
    decoder -- so the length is bounded by OPCODE_LEN before the operand is
    read."""
    opcode = raw[0]
    if opcode == 0x80:
        return target(runtime, opcode, raw[1])
    if opcode == 0x02:
        return (raw[1] << 8) | raw[2]
    raise AssertionError(f"{runtime:#06x} is {raw.hex(' ')}, not a sjmp or ljmp")


def transfers_naming(addr):
    """[(region, runtime, opcode)] for every `lcall`/`ljmp` in the main EC
    naming `addr`. Unaligned on purpose: a scan restricted to instruction
    boundaries would be a weaker claim than the one the write-up makes."""
    hi, lo = addr >> 8, addr & 0xFF
    out = []
    for name, lo_off, hi_off, base in REGIONS:
        data = IMAGE[lo_off:hi_off]
        for i in range(len(data) - 2):
            if data[i] in (0x12, 0x02) and data[i + 1] == hi and data[i + 2] == lo:
                out.append((name, i + base, data[i]))
    return out


def xdata_sites(addr):
    """[(region, runtime, [mnemonics])] for every direct `MOV DPTR,#addr` in
    the regions, with the window decoded. This is `trace_xdata_refs.py`'s
    method -- a byte census plus a linear window -- done here so the negatives
    below are the tool's own rather than a summary's.

    The window stops at the first control-flow instruction, which is what the
    tool's `terminator` column records and not an extra restriction added here.
    Without it a read-only site runs on into the next routine and charges that
    routine's read-modify-write to this register: `0x0741`'s site at `0xA9A5` is
    `movx a,@dptr ; jnb acc.2`, and eight instructions past the branch there is
    an `anl a,#0xfb` / `movx @dptr,a` pair belonging to somebody else."""
    hi, lo = addr >> 8, addr & 0xFF
    needle = bytes((0x90, hi, lo))
    out = []
    for name, lo_off, hi_off, base in REGIONS:
        data = IMAGE[lo_off:hi_off]
        for m in re.finditer(re.escape(needle), data):
            i = m.start()
            out.append((name, i + base,
                        [t[2] for t in
                         disasm8051.decode(data, i, count=WINDOW, stop_at_flow=True)]))
    return out


MOVX_READ = "movx a,@dptr"
MOVX_WRITE = "movx @dptr,a"
MASK = re.compile(r"^(orl|anl|xrl)  a,#0x([0-9a-f]{2})$")


def rmw_writers(addr):
    """[(region, runtime, mnemonic)] for every read-modify-write of `addr`
    this method finds, and nothing else.

    The shape is `movx a,@dptr` / a mask / `movx @dptr,a` -- the same three
    instructions `manual-fan-ctrl-0751-writers.csv` records -- and only the
    **first** one in the window counts. A `mov dptr` reloads DPTR, so the
    read-modify-write that follows it belongs to a different register:
    `0xAD17` writes `0x0741` with `anl a,#0xfb` and then, four instructions
    later, `0x073C` with `anl a,#0xf9`, and only the first is a `0x0741`
    writer. Reading the whole window is how a neighbouring register's mask ends
    up charged here.
    """
    writers = []
    for region, runtime, window in xdata_sites(addr):
        for i, m in enumerate(window[:-2]):
            if m == MOVX_READ and MASK.match(window[i + 1]) \
                    and window[i + 2] == MOVX_WRITE:
                writers.append((region, runtime, window[i + 1]))
                break
    return writers


class ThePolarity(unittest.TestCase):
    """`jnb acc.0,0x0DD1` jumps on an EVEN `0x45`. Everything downstream
    assumes the case table is only reachable on an even value, so this is
    first."""

    def test_the_three_bytes_and_their_target(self):
        # Bytes first, then the mnemonic: an assertion on the mnemonic alone
        # would pass against a decoder that had learned to mis-render these
        # three bytes in a self-consistent way.
        self.assertEqual(at(0x0DCB, 3), "30 e0 03")
        self.assertEqual(mnemonic(COMMON, 0x0DCB, 0x0DCB), "jnb  acc.0,0x0dd1")
        self.assertEqual(target(0x0DCB, 0x30, 0x03), 0x0DD1)

    def test_odd_045_abandons_the_frame_and_even_reaches_the_table(self):
        # The claim as arithmetic rather than as a mnemonic: displacement 3
        # from a 3-byte instruction at 0x0DCB lands on 0x0DD1, so an odd 0x45
        # does not jump and falls through to the `ljmp 0x0E46` at 0x0DCE --
        # which names the OTHER stub, `0x155E` -> bank0 `0x8518`.
        self.assertEqual(0x0DCB + 3 + 3, 0x0DD1)
        self.assertEqual(at(0x0DCE, 3), "02 0e 46")
        self.assertEqual(mnemonic(COMMON, 0x0DCE, 0x0DCE), "ljmp 0x0e46")
        self.assertEqual(at(0x0DD1, 2), "e5 45")
        self.assertEqual(at(0x0DD3, 3), "12 71 51")

    def test_every_key_the_table_holds_is_even(self):
        # The coherence check with the gate above. Only even 0x45 reaches the
        # switch at all, so an odd key would be a key the dispatcher can never
        # be asked for.
        keys = [COMMON[0x0DD6 + 3 * i + 2] for i in range(9)]
        self.assertEqual(keys, [0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12])
        self.assertTrue(all(k % 2 == 0 for k in keys))


class TheCaseTable(unittest.TestCase):
    """The nine triples inline at 0x0DD6 and the terminator after them. Which
    two keys reach `0xA7C8` is the whole finding, so the table is walked with
    the dispatcher's grammar rather than compared against a transcription."""

    TABLE = 0x0DD6

    def triples(self):
        """[(address, case, bytes at that address)] for the nine entries.

        The decode is anchored at the address the triple *names*, not at the
        triple itself -- the triples are data, and decoding them as
        instructions is how a table turns into a plausible-looking wrong
        answer."""
        out = []
        for i in range(9):
            addr = ((COMMON[self.TABLE + 3 * i] << 8)
                    | COMMON[self.TABLE + 3 * i + 1])
            out.append((addr, COMMON[self.TABLE + 3 * i + 2], common(addr, 3)))
        return out

    def test_the_nine_addresses_and_keys(self):
        self.assertEqual([(a, c) for a, c, _ in self.triples()],
                         [(0x0DF5, 0x02), (0x0DF7, 0x04), (0x0DF9, 0x06),
                          (0x0DFB, 0x08), (0x0DFE, 0x0A), (0x0E01, 0x0C),
                          (0x0E04, 0x0E), (0x0DF9, 0x10), (0x0E0A, 0x12)])

    def test_the_terminator_carries_the_default_arm(self):
        # `00 00` at 0x0DF1 is the "past the end" address, and the two bytes
        # the dispatcher reads after it -- 0x0DF3/0x0DF4 -- are `0e 0d`, which
        # is 0x0E0D. The terminator carries the escape, and 0x0E0D is the arm
        # that clears 0x45.
        self.assertEqual(at(self.TABLE + 27, 2), "00 00")
        self.assertEqual(at(self.TABLE + 29, 2), "0e 0d")
        self.assertEqual((COMMON[self.TABLE + 29] << 8) | COMMON[self.TABLE + 30],
                         0x0E0D)
        self.assertEqual(at(0x0E0D, 2), "e4 f5")   # clr a ; mov 0x45,a
        self.assertEqual(target(0x0E14, 0xB4, 0x06), 0x0E1D)

    def test_the_two_keys_that_reach_0xa7c8_are_0x02_and_0x0c(self):
        # Walk each key the way the dispatcher does: land on the address the
        # triple names, then take at most one `sjmp`/`ljmp` hop, and collect
        # the keys that arrive at 0x0E01. Case 0x02 needs the hop -- its
        # landing at 0x0DF5 is a `sjmp` -- and case 0x0C's landing *is*
        # 0x0E01, which is why "within one hop" and not "after one hop" is the
        # rule. A landing that is neither stops the walk and says so.
        reached = []
        for addr, case, raw in self.triples():
            with self.subTest(case=case):
                self.assertIn(raw[0], (0x80, 0x02),
                              f"case 0x{case:02x} lands on {raw.hex(' ')}, "
                              "which is not a jump")
            hop = addr if addr == 0x0E01 else branch(addr, raw)
            if hop == 0x0E01:
                reached.append(case)
        self.assertEqual(reached, [0x02, 0x0C])

    def test_0x0e01_is_the_ljmp_that_names_the_dispatch_slot(self):
        # The second hop, for both keys at once: 0x0E01 is `ljmp 0x0E49`.
        self.assertEqual(at(0x0E01, 3), "02 0e 49")
        self.assertEqual(branch(0x0E01, common(0x0E01, 3)), 0x0E49)


class TheDispatchSlot(unittest.TestCase):
    """`0x0E49` is slot 11 of the seventeen-entry block at 0x0E2B-0x0E5D and
    names stub `0x1564`. Which slot is the point: the block's entries are not
    interchangeable, so reaching one of them says nothing about the others."""

    BLOCK = 0x0E2B
    SLOTS = 17

    def slots(self):
        """[(address, opcode, operand)] for the block, at its own stride of 3,
        in file order. The operand is left as the two bytes the instruction
        carries; only the two entries this file cares about are `ljmp`, so the
        block's one `lcall` does not have to resolve."""
        return [(self.BLOCK + 3 * i, common(self.BLOCK + 3 * i)[0],
                 common(self.BLOCK + 3 * i, 3))
                for i in range(self.SLOTS)]

    def test_the_block_is_seventeen_entries_and_then_not_a_jump(self):
        # 0x0E5E is the eighteenth entry's address and is `mov 0x8a,#0x06` --
        # the counter reset's own code, not another slot. Without this the
        # block's extent is a guess and "seventeen" is a claim about nothing.
        slots = self.slots()
        self.assertEqual(len(slots), self.SLOTS)
        self.assertEqual(slots[-1][0] + 3, 0x0E5E)
        self.assertEqual(at(0x0E5E, 3), "75 8a 06")

    def test_sixteen_ljmps_and_one_lcall(self):
        # charge-target-caller-chain.md section 1's shape claim, held here so
        # a change to the block's opcodes fails instead of passing silently.
        ops = [op for _, op, _ in self.slots()]
        self.assertEqual(ops.count(0x02), 16)
        self.assertEqual(ops.count(0x12), 1)
        self.assertEqual([a for a, op, _ in self.slots() if op == 0x12], [0x0E2E])

    def test_0x0e49_is_the_eleventh_entry_and_names_stub_0x1564(self):
        # The eleventh of seventeen, which is the fact that matters: the block
        # is a set of independent cases and reaching one is not reaching any
        # other.
        addr, opcode, raw = self.slots()[10]
        self.assertEqual(addr, 0x0E49)
        self.assertEqual(branch(addr, raw), 0x1564)

    def test_the_entry_before_it_names_the_other_stub(self):
        # The tenth is the odd-`0x45` arm's destination. If it ever equalled
        # the eleventh's, the parity would stop being load-bearing.
        addr, opcode, raw = self.slots()[9]
        self.assertEqual(addr, 0x0E46)
        self.assertEqual(branch(addr, raw), 0x155E)

    def test_the_two_slots_decoded_are_the_three_bytes_named(self):
        self.assertEqual(at(0x0E46, 3), "02 15 5e")
        self.assertEqual(at(0x0E49, 3), "02 15 64")


class TheStub(unittest.TestCase):
    """`0x1564` is a BL51 far-call stub for bank0 `0x851B`, and `0x851B` is
    `lcall 0xA7C8`. The stub's six bytes are what turn a common-area dispatch
    slot into a banked call."""

    def test_0x1564_is_the_stub_for_0x851b(self):
        self.assertEqual(at(0x1564, 6), "90 85 1b 02 11 00")
        self.assertEqual(mnemonic(COMMON, 0x1564, 0x1564), "mov  dptr,#0x851b")
        self.assertEqual(mnemonic(COMMON, 0x1567, 0x1567), "ljmp 0x1100")

    def test_0x155e_is_the_stub_for_the_runs_base(self):
        # The odd-`0x45` arm. Naming it is what makes the polarity a claim
        # about two different routines rather than one.
        self.assertEqual(at(0x155E, 6), "90 85 18 02 11 00")
        self.assertEqual(mnemonic(COMMON, 0x155E, 0x155E), "mov  dptr,#0x8518")

    def test_the_bank_select_stub_both_of_them_tail_jump_to(self):
        # 0x1100's `ret` pops DPTR rather than a return address. That is the
        # property scheduler-run-8518-entries.md section 2 rests on: a banked
        # routine's `ret` lands in 0x1100-0x11FF and not back in the run.
        self.assertEqual(at(0x1100, 20),
                         "c0 08 74 11 c0 e0 c0 82 c0 83 75 08 0a c2 90 c2 91 c2 92 22")
        self.assertEqual(mnemonic(COMMON, 0x1113, 0x1113), "ret")

    def test_no_address_of_the_run_lands_inside_that_window(self):
        # The window claim, computed rather than asserted: the 22 entries of
        # the run at 0x8518 are all far outside 0x1100-0x11FF.
        run = [0x8518 + 3 * i for i in range(22)]
        self.assertEqual([a for a in run if 0x1100 <= a <= 0x11FF], [])


class TheRunEntry(unittest.TestCase):
    """Entering the run at `0x8518` does not reach `0xA7C8`; entering at
    `0x851B` does. Those four bytes are the whole of the structural difference
    and they are what made the framing question worth asking."""

    def test_0x8518_is_a_tail_jump_and_0x851b_is_the_lcall(self):
        self.assertEqual(bank0_at(0x8518, 3), "02 b0 65")
        self.assertEqual(bank0_at(0x851B, 3), "12 a7 c8")

    def test_entering_at_851b_runs_a7c8_then_a844_then_leaves(self):
        # 0x851B and 0x851E are `lcall`s, so entering at 0x851B falls through
        # into 0x851E; 0x8521 is `ljmp`, so the segment ends there.
        self.assertEqual(bank0_at(0x851E, 3), "12 a8 44")
        self.assertEqual(bank0_at(0x8521, 3), "02 cf c6")

    def test_0xa7c8_has_exactly_one_transfer_naming_it(self):
        # The negative the whole chain rests on, and a scan that can fail: an
        # unaligned two-opcode scan of the common area and both banks. It finds
        # the one `lcall` and nothing else. It does NOT rule out a transfer
        # built at run time or routed through a function-pointer table, which
        # is what `common 0x7151` is in this same image.
        self.assertEqual(transfers_naming(0xA7C8), [('bank0', 0x851B, 0x12)])

    def test_the_same_scan_over_the_pd_image_finds_nothing(self):
        # Scoped to its own region and said so, so the failure names what was
        # searched rather than implying the whole dump.
        pd = IMAGE[PD_IMAGE:0x30000]
        hits = [PD_IMAGE + i for i in range(len(pd) - 2)
                if pd[i] in (0x12, 0x02)
                and pd[i + 1] == 0xA7 and pd[i + 2] == 0xC8]
        self.assertEqual(hits, [], f"pd-image 0x{PD_IMAGE:X}-0x2FFFF has {hits}")


class ThePlClear(unittest.TestCase):
    """The one-shot at `0xA80A` guards the mode write and NOT the PL clear.
    This is the issue's "boot-shaped, not proof" question answered against the
    boot reading, and it is why the routine is a recurring init pass rather
    than a boot event."""

    def test_both_jnbs_target_the_pl_clear(self):
        # The bits differ -- 0xA802 tests bit 0, 0xA806 tests bit 5 -- and the
        # target does not, which is the whole claim: the PL clear is the branch
        # target of both, so it is the fall-through and not the body of the
        # one-shot.
        self.assertEqual((bank0_at(0xA802, 3), bank0_at(0xA806, 3)),
                         ("30 e0 26", "30 e5 22"))
        for addr in (0xA802, 0xA806):
            with self.subTest(addr=addr):
                opcode, _, disp = bank0(addr, 3)
                self.assertEqual(target(addr, opcode, disp), 0xA82B)

    def test_the_one_shot_is_the_mask_at_0xa80a_and_nothing_else(self):
        self.assertEqual(bank0_at(0xA80A, 2), "54 df")
        self.assertEqual(mnemonic(BANK0, 0x280A, 0xA80A), "anl  a,#0xdf")

    def test_the_mode_block_falls_through_into_the_pl_clear(self):
        # 0xA823 clr a / mov r7,a / lcall 0x94D0 / lcall 0x8653, then 0xA82B --
        # so the both-bits-set path arrives without taking either branch, and
        # `jb acc.0` at 0xA82F is the gate the PL clear sits behind.
        self.assertEqual(bank0_at(0xA823, 2), "e4 ff")
        self.assertEqual(bank0_at(0xA825, 3), "12 94 d0")
        self.assertEqual(bank0_at(0xA828, 3), "12 86 53")
        self.assertEqual(bank0_at(0xA82B, 3), "90 07 41")
        self.assertEqual(target(0xA82F, 0x20, 0x11), 0xA843)

    def test_the_four_whole_byte_stores_are_a_cleared_accumulator(self):
        # 0x0783/0x0784/0x0785 and 0x078B, each `movx @dptr,a` after the
        # `clr a` at 0xA832 -- so what is written is zero and not a per-mode
        # default. DPTR is charged from the `mov dptr` three bytes back, which
        # is the one shape this block uses and is checked here rather than
        # assumed.
        self.assertEqual(bank0_at(0xA832, 1), "e4")
        stores = []
        for runtime in range(0xA832, 0xA843):
            if bank0(runtime, 1) == b"\xf0":
                pointer = bank0(runtime - 3, 3)
                self.assertEqual(pointer[0], 0x90)
                stores.append((pointer[1] << 8) | pointer[2])
        self.assertEqual(stores, [0x0783, 0x0784, 0x0785, 0x078B])

    def test_the_entry_gates_are_the_two_xor_routines_named_in_the_csv(self):
        # `0xBE9C` is read_x0780_xor_a2 and `0xB9D8` is read_06e6_xor_01 in
        # ec/annotations/ghidra-functions.csv. The write-up states the gates as
        # `[0x0780] != 0xA2` and `[0x06E6] == 0x01`, so both the `jz` polarity
        # and the XOR constant are pinned here rather than left to the
        # mnemonic table alone.
        self.assertEqual(bank0_at(0xA7C8, 3), "12 be 9c")
        self.assertEqual(bank0_at(0xA7CB, 2), "60 76")
        self.assertEqual(target(0xA7CB, 0x60, 0x76), 0xA843)
        self.assertEqual(bank0_at(0xBE9C, 6), "90 07 80 e0 64 a2")

        self.assertEqual(bank0_at(0xA7EA, 3), "12 b9 d8")
        self.assertEqual(bank0_at(0xA7ED, 2), "60 04")
        self.assertEqual(target(0xA7ED, 0x60, 0x04), 0xA7F3)
        self.assertEqual(bank0_at(0xB9D8, 6), "90 06 e6 e0 64 01")


class TheOemBitZeroRevocation(unittest.TestCase):
    """`0xBD03` clears `0x0741` bit 0, and nothing this method finds sets it.
    The second half is a negative and is written as one.

    The bit-addressable forms cannot help or hinder here and the reason is
    worth naming: bit 0 of XDATA `0x0741` would be bit address `0x41`, which
    is a bit of *internal* RAM byte `0x08`, so `setb`/`clr` cannot express it
    at all. Only an accumulator mask or a direct byte store can touch this
    bit, and both are what the window below decodes."""

    def test_0xbd03_is_the_clear(self):
        self.assertEqual(bank0_at(0xBD03, 6), "90 07 41 e0 54 fe")
        self.assertEqual(mnemonic(BANK0, 0x3D03, 0xBD03), "mov  dptr,#0x0741")
        self.assertEqual(mnemonic(BANK0, 0x3D07, 0xBD07), "anl  a,#0xfe")

    def test_exactly_two_callers(self):
        self.assertEqual(transfers_naming(0xBD03),
                         [('bank0', 0xAB75, 0x12), ('bank0', 0xACFC, 0x12)])

    def test_the_06e6_caller_is_gated_on_06e6_being_05(self):
        # 0xAB75 sits in `set_06e2_bit0_from_c412`, whose committed row says
        # the same thing; these are the two bytes that make it true, and the
        # other caller is inside `reset_xdata_flags_and_07d5_to_ff` at 0xACB4.
        self.assertEqual(bank0_at(0xAB6E, 3), "90 06 e6")
        self.assertEqual(bank0_at(0xAB72, 3), "b4 05 04")
        self.assertEqual(target(0xAB72, 0xB4, 0x04), 0xAB79)

    def test_no_instruction_sets_0741_bit0(self):
        # The negative, as a scan that can fail. For every direct
        # `MOV DPTR,#0x0741` in the three main-EC regions the eight-instruction
        # window is decoded, and any read-modify-write whose mask sets bit 0 --
        # or any `movx @dptr,a` with no `movx a,@dptr` in the window, which
        # would be a blind whole-byte store this window cannot attribute --
        # fails. A store through a DPTR built at run time is invisible to a
        # `mov dptr` census at all, and the failure message says so rather
        # than reporting the bit absent.
        blind = [(region, runtime, window)
                 for region, runtime, window in xdata_sites(0x0741)
                 if MOVX_WRITE in window and MOVX_READ not in window]
        setters = [(region, runtime, m)
                   for region, runtime, m in rmw_writers(0x0741)
                   if m.startswith("orl") and int(MASK.match(m).group(2), 16) & 1]
        self.assertEqual(
            (setters, blind), ([], []),
            "a bit-0 setter or a blind store on 0x0741 is found by this method "
            f"over {'+'.join(name for name, *_ in REGIONS)}: "
            f"setters={setters} blind={blind}. A store through a DPTR built at "
            "run time is not in its reach, so this is not a statement that the "
            "bit is never set.")

    def test_the_writers_are_all_other_bits(self):
        # The complement of the scan above, as a positive list: every
        # read-modify-write this method finds on 0x0741 and the immediate it
        # applies. Bit 0 is cleared at 0xBD03 and untouched everywhere else.
        self.assertEqual(rmw_writers(0x0741), [
            ('bank0', 0x8782, "orl  a,#0x20"),
            ('bank0', 0x879D, "orl  a,#0x20"),
            ('bank0', 0x87AC, "anl  a,#0xdf"),
            ('bank0', 0xA990, "anl  a,#0xfb"),
            ('bank0', 0xA9E1, "orl  a,#0x04"),
            ('bank0', 0xAD17, "anl  a,#0xfb"),
            ('bank0', 0xAD46, "anl  a,#0x7f"),
            ('bank0', 0xBD03, "anl  a,#0xfe"),
            ('bank0', 0xCF78, "anl  a,#0x7f"),
            ('bank0', 0xCFEE, "orl  a,#0x80"),
        ])


if __name__ == '__main__':
    unittest.main()
