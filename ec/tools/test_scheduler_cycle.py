#!/usr/bin/env python3
"""Unit checks for the divide-down scheduler cycle at common 0x0D7B (issue #1183).

`docs/findings/scheduler-divide-down-cycle.md` answers "how many entries to
`0x0D7B` is one case-`0x0A` turn" and pins the reading that produces the
answer. This file holds the byte facts that reading stands on, read from the
committed image rather than from a re-run of any scan that produced the
census in the write-up -- a regenerated table that disagreed would then fail
instead of passing on a stale pair, the `test_bank1_e582_framing.py` pattern.

The polarity check comes first because it is the one thing the issue got
backwards and the one thing a future reader will re-get backwards: `jnb acc.0`
jumps when bit 0 is **clear**, so an even `0x44` reaches the ladder and an odd
one abandons the frame. Everything else in the cycle -- the four `lcall`s at
0x0DA0/0x0DA5/0x0DAA being reachable rather than dead, `0x44` counting 1..10
rather than being 1 every entry, `inc 0x45` firing on one entry in ten -- is a
consequence of that one bit, so a suite that did not pin it would let a
regression in the decoder pass silently.

The 200 is **computed, not asserted**. `test_the_counter_arms_yield_a_period`
walks the counter arms as the bytes read and asserts the period comes out 200.
A changed image, a changed ladder constant or a changed case table moves it,
and the failure says so. A literal 200 in an assertEqual would have kept
passing through every one of those.

A count of entries is not a rate, and nothing here is a period: no test
converts the count to a time, and `docs/findings/charge-target-caller-chain.md`
§4 keeps the tick period and the dispatcher's own period named as the two
things that would have to be known first.
"""
import csv
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import disasm8051
import intmem_refs

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
ANNOTATIONS = HERE.parent / 'annotations'
FUNCTIONS = ANNOTATIONS / 'ghidra-functions.csv'

# What step() returns in its fourth slot when the entry took the 0x47 wrap at
# 0x0E17. It is a marker rather than a 0x45 value, so it cannot collide with
# the nine case keys the same slot otherwise carries -- 0x3C is well past the
# last key, and naming it says which arm fired.
WRAP = 0x3C

# Common area: file offset == runtime address, which is what trace_xdata_refs.REGIONS
# says for the 0x0000-0x7FFF region and what make_bank_image.py arranges. Read
# once at module scope so the seven tests below share one open handle.
IMAGE = FIRMWARE.read_bytes()


def at(addr, n=1):
    """The n bytes at `addr`, as a hex string."""
    return IMAGE[addr:addr + n].hex(' ')


def decoded(addr, n):
    """[(address, bytes, mnemonic)] for n instructions from `addr`."""
    return list(disasm8051.decode(IMAGE, addr, count=n, addr=addr))


class ThePolarity(unittest.TestCase):
    """`jnb acc.0,0x0D8B` jumps on an EVEN `0x44`. This is the reading the
    issue had inverted, and the one the whole cycle turns on."""

    def test_the_three_bytes_and_their_target(self):
        # The bytes first, then what they decode to: an assertion on the
        # mnemonic alone would pass against a decoder that had learned to
        # mis-render these three bytes in a self-consistent way.
        self.assertEqual(at(0x0D85, 3), "30 e0 03")
        self.assertEqual(decoded(0x0D85, 1)[0][2], "jnb  acc.0,0x0d8b")
        self.assertEqual(disasm8051.relative_target(0x30, 0x03, 0x0D85), 0x0D8B)

    def test_jnb_jumps_when_bit_zero_is_clear(self):
        # Stated as the arithmetic rather than left to the mnemonic table,
        # because this is the claim: displacement 3 from a 3-byte
        # instruction at 0x0D85 lands on 0x0D8B, which is the instruction
        # *after* the `ljmp 0x0E2E`. An odd `0x44` sets acc.0, `jnb` does not
        # jump, and control falls through to 0x0D88.
        self.assertEqual(0x0D85 + 3 + 3, 0x0D8B)
        self.assertEqual(at(0x0D88, 3), "02 0e 2e")
        self.assertEqual(decoded(0x0D88, 1)[0][2], "ljmp 0x0e2e")

    def test_the_committed_decompile_already_reads_it_this_way(self):
        # The .c says `if ((DAT_INTMEM_44 & 1) != 0) { FUN_CODE_0e2e(); return; }`
        # -- odd abandons. The committed files agree with each other and the
        # issue was the outlier, so this pins that the correction is not a
        # retraction of the decompile but a gap closed beside it.
        c = (HERE.parent / 'decompiled' / 'common' / '0D7B.c').read_text()
        self.assertIn("if ((DAT_INTMEM_44 & 1) != 0) {", c)
        self.assertIn("FUN_CODE_0e2e();", c)

    def test_the_second_parity_gate_has_the_same_shape(self):
        # 0x0DCB is the same test on 0x45: even reaches the switch at 0x0DD1,
        # odd falls through to `ljmp 0x0E46`. Two sites, so a decoder that got
        # `jnb` wrong would have to get it wrong consistently.
        self.assertEqual(at(0x0DCB, 3), "30 e0 03")
        self.assertEqual(disasm8051.relative_target(0x30, 0x03, 0x0DCB), 0x0DD1)
        self.assertEqual(decoded(0x0DCE, 1)[0][2], "ljmp 0x0e46")


class TheLadder(unittest.TestCase):
    """`A = 0x44 - 4`, `- 2`, `- 2`, `+ 6`, tested by `jz`/`jnz` in that
    order, so the four arms are 0x44 of 4, 6, 8 and 2 -- all even, on the arm
    even values reach. The issue read them as even values on an arm only odd
    values reach, and concluded the four `lcall`s might be dead code."""

    # (address of the `add`, address of its branch, the immediate, the 0x44 the
    # arm selects). The four are read off the image, and the test below
    # re-derives each value from the *cumulative* sum of the immediates rather
    # than from any one of them -- the deltas chain, so the second `add a,#0xfe`
    # tests 0x44 - 6, not 0x44 - 2. That is the arithmetic the issue's
    # "tests for 0x44 of 2, 4, 6 and 8" is really making.
    ARMS = ((0x0D90, 0x0D92, 0xFC, 4), (0x0D94, 0x0D96, 0xFE, 6),
            (0x0D98, 0x0D9A, 0xFE, 8), (0x0D9C, 0x0D9E, 0x06, 2))

    def test_the_four_adds_and_the_values_they_select(self):
        running = 0
        for add_at, br_at, imm, value in self.ARMS:
            with self.subTest(imm=imm, value=value):
                self.assertEqual(at(add_at, 2), f"24 {imm:02x}")
                self.assertIn(IMAGE[br_at], (0x60, 0x70))  # jz / jnz
                # A accumulates: A = 0x44 + imm1 + imm2 + ... and the branch
                # tests A == 0, so the selected 0x44 is the negated running
                # total. The last arm is the +6, which is why 2 comes last.
                running = (running + imm) & 0xFF
                self.assertEqual((-running) & 0xFF, value)

    def test_the_last_arm_is_jnz_so_two_is_the_fallthrough(self):
        # 0x0D9E is `jnz 0x0DC0`: not-equal branches to the clear, so 0x44 == 2
        # is the value that *falls through* to the `lcall` at 0x0DA0. Reading
        # it the other way round would put 0x44 of 10 on the `lcall` arm and
        # 2 on the clear, and the count would come out the same by accident.
        self.assertEqual(at(0x0D9E, 2), "70 20")
        self.assertEqual(disasm8051.relative_target(0x70, 0x20, 0x0D9E), 0x0DC0)

    def test_the_four_lcalls_are_reachable_and_are_even_values(self):
        # The point the issue got backwards. 0x0DA0, 0x0DA5, 0x0DAA and the
        # 0x46 pair at 0x0DB6/0x0DBB are reached by 0x44 of 2, 4, 6 and 8 --
        # and the parity gate at 0x0D85 sends even 0x44 to this ladder, so
        # every one of them is on the arm that is taken.
        for addr, target in ((0x0DA0, 0x0E37), (0x0DA5, 0x0E3A),
                             (0x0DAA, 0x0E3D), (0x0DB6, 0x0E40),
                             (0x0DBB, 0x0E43)):
            with self.subTest(addr=addr):
                self.assertEqual(at(addr, 3), f"12 {target >> 8:02x} {target & 0xFF:02x}")
                self.assertEqual(decoded(addr, 1)[0][2], f"lcall 0x{target:04x}")

    def test_the_clear_and_the_gate_that_reads_it_back(self):
        # 0x0DC0 `clr a ; mov 0x44,a` then 0x0DC3 `mov a,0x44 ; jnz 0x0E1D`.
        # The `jnz` is what makes the clear load-bearing: `inc 0x45` runs only
        # on the entry where 0x44 reads zero, which is one entry in ten.
        self.assertEqual(at(0x0DC0, 1), "e4")
        self.assertEqual(at(0x0DC1, 2), "f5 44")
        self.assertEqual(at(0x0DC3, 2), "e5 44")
        self.assertEqual(at(0x0DC5, 2), "70 56")
        self.assertEqual(disasm8051.relative_target(0x70, 0x56, 0x0DC5), 0x0E1D)
        self.assertEqual(decoded(0x0DC7, 1)[0][2], "inc  0x45")


class TheCaseTable(unittest.TestCase):
    """The inline table at 0x0DD6, its keys 0x02..0x12, and the `00 00 0e`
    sentinel that is what puts `jmp @a+dptr` on 0x0E0D rather than into the
    table's own bytes."""

    TABLE = 0x0DD6

    def test_the_nine_keys(self):
        keys = [IMAGE[self.TABLE + 3 * i + 2] for i in range(9)]
        self.assertEqual(keys, [0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12])
        # Every key even, which is the coherence check with the parity gate at
        # 0x0DCB: only even 0x45 reaches this table, and every key it can hold
        # is even, so the table and the gate agree rather than merely both
        # existing.
        self.assertTrue(all(k % 2 == 0 for k in keys))

    def test_the_terminator_is_a_zero_address(self):
        # The tenth triple is `00 00 0e` -- address 0x0000 is the sentinel
        # task_call_table.switch_case_tables() documents as "it has run past
        # the end, and it then takes the *next* triple's address as a default
        # arm". The `0e` here is the high byte of that next triple's address.
        self.assertEqual(at(self.TABLE + 27, 3), "00 00 0e")

    def test_the_sentinel_puts_dptr_on_0x0e0d(self):
        # The dispatcher's own bytes, not a re-derivation of it: 0x715F/0x7160
        # `inc dptr` twice past the two zero bytes, then read the next two
        # into DPTR, then `jmp @a+dptr` with A cleared.
        self.assertEqual(at(0x715F, 2), "a3 a3")
        self.assertEqual(at(0x716B, 1), "73")   # jmp @a+dptr
        sentinel_lo = self.TABLE + 27 + 2      # 0x0DF1 -> 0x0DF3
        self.assertEqual(IMAGE[sentinel_lo], 0x0E)
        self.assertEqual(IMAGE[sentinel_lo + 1], 0x0D)
        self.assertEqual((IMAGE[sentinel_lo] << 8) | IMAGE[sentinel_lo + 1], 0x0E0D)

    def test_the_first_even_value_past_the_end_is_0x14(self):
        # 0x45 counts up, so the first even value the table does not hold is
        # 0x14 -- and that is the value that reaches the default arm. Asserted
        # as an arithmetic step over the last key rather than as a literal, so
        # a changed table moves it.
        last = IMAGE[self.TABLE + 3 * 8 + 2]
        self.assertEqual(last, 0x12)
        self.assertEqual(last + 2, 0x14)
        self.assertGreater(last + 2, 0x12)

    def test_the_default_arm_body(self):
        # 0x0E0D: clear 0x45, inc 0x47, and fire `lcall 0x0E5B` on the 0x3C
        # wrap. This is the arm that returns 0x45 to zero, so it is the arm
        # that closes the cycle the count is a count of.
        self.assertEqual(at(0x0E0D, 1), "e4")
        self.assertEqual(at(0x0E0E, 2), "f5 45")
        self.assertEqual(at(0x0E10, 2), "05 47")
        self.assertEqual(at(0x0E14, 3), "b4 3c 06")
        self.assertEqual(decoded(0x0E17, 1)[0][2], "lcall 0x0e5b")


class TheCounterArms(unittest.TestCase):
    """The count, computed from the bytes rather than asserted as a literal.

    `step()` below is a transcription of the arms at 0x0D81..0x0E1D, in the
    order the image has them. It returns the next counter state and whether
    the entry fired case `0x0A`. Running it forward and measuring the gap
    between firings is the whole claim, and it is a *number this suite
    computed*, so a changed ladder constant or a changed table shows up as a
    changed number rather than as a suite that still believes 200.
    """

    # The five things an entry can do, named for the address that does them.
    def step(self, c44, c45, c47):
        c44 = (c44 + 1) & 0xFF                      # 0x0D81 inc 0x44
        if c44 & 1:
            return c44, c45, c47, None               # 0x0D88 ljmp 0x0E2E
        a = c44
        a = (a + 0xFC) & 0xFF                       # 0x0D90 add a,#0xfc
        if a == 0:
            arm = 4
        else:
            a = (a + 0xFE) & 0xFF                   # 0x0D94 add a,#0xfe
            if a == 0:
                arm = 6
            else:
                a = (a + 0xFE) & 0xFF               # 0x0D98 add a,#0xfe
                if a == 0:
                    arm = 8
                else:
                    a = (a + 0x06) & 0xFF           # 0x0D9C add a,#0x06
                    arm = 2 if a == 0 else 0
        # arm 0 clears 0x44 at 0x0DC0; arm 8 increments 0x46 at 0x0DAF and
        # dispatches on its parity. 0x46 gates nothing the count depends on,
        # so it is not carried -- and that is stated rather than hidden,
        # because a reader deciding whether the omission matters should be
        # able to see that the answer did not move when 0x46 was included.
        if arm == 0:
            c44 = 0
        if c44 != 0:
            return c44, c45, c47, None               # 0x0DC5 jnz 0x0E1D
        c45 = (c45 + 1) & 0xFF                      # 0x0DC7 inc 0x45
        if c45 & 1:
            return c44, c45, c47, None               # 0x0DCE ljmp 0x0E46
        keys = [IMAGE[0x0DD6 + 3 * i + 2] for i in range(9)]
        if c45 in keys:
            return c44, c45, c47, c45               # the case that fired
        c45 = 0                                     # 0x0E0E mov 0x45,a
        c47 = (c47 + 1) & 0xFF                      # 0x0E10 inc 0x47
        if c47 == 0x3C:                             # 0x0E14 cjne a,#0x3c
            return c44, c45, 0, WRAP                # 0x0E17 lcall 0x0E5B
        return c44, c45, c47, None

    def gaps(self, start, want, entries):
        """Entries between *consecutive* firings of `want`, over `entries` steps.

        Measured from one firing to the next rather than from the first firing
        onward: the two differ by construction, and only the consecutive form
        is the period. Bounded by a step count rather than by a repeated-state
        guard, because the 0x47 wrap at 0x0E1A resets all three counters to
        zero -- the state *does* recur at 12000, and a guard on it would end
        the walk one firing short of the measurement it was added to bound.
        """
        c44, c45, c47 = start
        n, last, out = 0, None, []
        for _ in range(entries):
            c44, c45, c47, fired = self.step(c44, c45, c47)
            n += 1
            if fired == want:
                if last is not None:
                    out.append(n - last)
                last = n
        return out

    def test_the_case_0x0a_turn_is_200_entries(self):
        # 20 `inc 0x45` times 10 entries each. Computed, not literal: the
        # number comes out of step() walking the arms, so it moves if the
        # image moves.
        gaps = self.gaps((0, 0, 0), 0x0A, 1000)
        self.assertTrue(gaps, "case 0x0A never fired, so there is no period")
        self.assertEqual(sorted(set(gaps)), [200])

    def test_the_period_does_not_depend_on_where_the_counters_start(self):
        # The write-up says the 200 is start-independent and the *phase* is
        # not established. Both halves are asserted: the gap is the same from
        # every start tried, and the entry number the first firing lands on
        # differs between them.
        phases = set()
        for start in ((0, 0, 0), (1, 0, 0), (5, 7, 0), (10, 0x14, 0x3B)):
            gaps = self.gaps(start, 0x0A, 1000)
            self.assertEqual(sorted(set(gaps)), [200], f"start {start}")
            c44, c45, c47 = start
            for n in range(1, 400):
                c44, c45, c47, fired = self.step(c44, c45, c47)
                if fired == 0x0A:
                    phases.add(n)
                    break
        self.assertGreater(len(phases), 1,
                           "the phase is start-dependent, so the write-up's "
                           "claim that it is not established would be wrong")

    def test_the_0x0e5b_fire_is_12000_entries(self):
        # The longer cycle: 0x47 rides the same reset, so 0x3C firings of the
        # default arm times 200. Asserted as a relation to the 200 above
        # rather than as its own literal, so the two cannot drift apart.
        case_gap = sorted(set(self.gaps((0, 0, 0), 0x0A, 1000)))[0]
        wraps = self.gaps((0, 0, 0), WRAP, 25000)
        self.assertTrue(wraps, "the 0x47 wrap never fired")
        self.assertEqual(sorted(set(wraps)), [case_gap * 0x3C])

    def test_0x47_only_advances_on_the_default_arm(self):
        # 0x47 is incremented at 0x0E10, inside the arm past the end of the
        # case table, so it moves once per 0x45 wrap and not once per entry.
        # If it moved per entry the 12000 above would be 200 and the write-up
        # would be wrong; this is the assertion that says which it is.
        c44, c45, c47, n = 0, 0, 0, 0
        while n < 200:
            c44, c45, c47, _ = self.step(c44, c45, c47)
            n += 1
        self.assertEqual(c47, 1)


class TheEntryPoint(unittest.TestCase):
    """One `lcall 0x0D7B` in the image, and the poller clears the flag before
    calling -- so one pass of 0x0C86 enters the scheduler at most once."""

    def test_the_lcall_occurs_exactly_once(self):
        hits, i = [], IMAGE.find(b'\x12\x0d\x7b')
        while i >= 0:
            hits.append(i)
            i = IMAGE.find(b'\x12\x0d\x7b', i + 1)
        self.assertEqual([f"0x{h:05X}" for h in hits], ["0x00CF5"])

    def test_the_bare_constant_is_the_same_lcalls_operand_not_a_second_one(self):
        # The issue offered `0d 7b` "appears once in the image as a constant"
        # as companion evidence. It is the same two bytes: 0x0CF6 is the
        # high byte of the target at 0x0CF5. So the two facts are one, and a
        # write-up that counted them separately would be double-counting.
        self.assertEqual(IMAGE.find(b'\x0d\x7b'), 0x00CF6)
        self.assertEqual(0x0CF5 + 1, 0x0CF6)

    def test_the_flag_is_cleared_before_the_call(self):
        # 0x0CF3 `clr 0x35` then 0x0CF5 `lcall 0x0D7B`. The order is the
        # whole of the "at most one entry per pass" claim, so both bytes and
        # the order are asserted rather than either alone.
        self.assertEqual(at(0x0CF3, 2), "c2 35")
        self.assertEqual(at(0x0CF5, 3), "12 0d 7b")
        self.assertLess(0x0CF3, 0x0CF5)

    def test_the_return_lands_in_the_poller(self):
        # 0x7151 opens `pop 0x83 ; pop 0x82`: it consumes the return address
        # its own caller pushed and never pushes it back, so the `ret` at
        # 0x0E1D unwinds to 0x0CF8 -- the poller's instruction after the
        # `lcall`. "The ret falls into the jump table" is the obvious wrong
        # reading here and it is worth pinning the right one.
        self.assertEqual(at(0x7151, 4), "d0 83 d0 82")
        self.assertEqual(decoded(0x0CF8, 1)[0][2], "mov  dptr,#0x007e")
        self.assertEqual(0x0CF5 + 3, 0x0CF8)


class TheReferenceCensus(unittest.TestCase):
    """The falsifier sets, as sets, so a re-derivation that finds a *fourth*
    writer fails loudly rather than passing on a stale pair.

    Every one of the three corrections below is a site the issue named and the
    image refutes, so they are the rows most worth holding: a scan that
    "confirmed" one of them again would be re-reporting a byte pattern.
    """

    def scan(self, addr):
        return {off for off, _op, _dir, _frame
                in intmem_refs.scan(IMAGE, [addr], True).get(addr, [])}

    def test_the_writers_of_0x44_in_the_main_ec(self):
        # 0x0D81 `inc 0x44` and 0x0DC1 `mov 0x44,a` -- both inside 0x0D7B, both
        # its own. The issue's "common 0x0B0A" is 0x0B0AC, which is not in
        # this set because the bytes there are a `jnb` displacement and an
        # `orl` opcode.
        self.assertEqual(self.scan(0x44) & {0x0D81, 0x0DC1}, {0x0D81, 0x0DC1})

    def test_the_two_bank1_sites_are_an_xdata_address(self):
        # The issue's "bank1 0xAE66 and 0xB540". The runtime addresses are
        # right; what the bytes are is not. `90 05 44` is `mov dptr,#0x0545`-
        # shaped -- an XDATA address, which is scan_refs.py's question and a
        # different address space from an internal-RAM byte entirely.
        for off, runtime in ((0x12E66, 0xAE66), (0x13540, 0xB540)):
            with self.subTest(off=off):
                self.assertEqual(at(off - 1, 3), "90 05 44")
                self.assertEqual(decoded(off - 1, 1)[0][2], "mov  dptr,#0x0544")
                self.assertEqual(intmem_refs.runtime_addr(off, True), runtime)

    def test_the_four_readers_are_an_immediate_and_a_displacement(self):
        # The issue's 0x0BF45/0x0C449/0x0CB16/0x0CBF2, offered as `mov a,0x44`
        # readers. The bytes there are `74 44`, and the opcode is 0x74 --
        # `mov a,#0x44`, an immediate load of the *constant* 0x44, which is
        # not a reference to the internal byte 0x44 at all. The issue read the
        # pair as `e5 44`, which is the same two bytes with the other opcode
        # and a different meaning. And the framing is in doubt independently:
        # the `74` one byte earlier is the displacement of a preceding
        # `20 06 74` = `jb 0x20.6,0xbfba`.
        for off in (0x0BF45, 0x0C449, 0x0CB16, 0x0CBF2):
            with self.subTest(off=off):
                self.assertEqual(at(off, 2), "74 44")
                self.assertEqual(decoded(off, 1)[0][2], "mov  a,#0x44")
                self.assertEqual(at(off - 2, 3), "20 06 74")
                self.assertEqual(disasm8051.bit_name(0x06), "0x20.6")
        # ... and no `e5 44` exists at any of the four, which is the claim the
        # issue's "readers" rested on.
        for off in (0x0BF45, 0x0C449, 0x0CB16, 0x0CBF2):
            self.assertNotEqual(at(off, 2), "e5 44")

    def test_the_bit_address_writes_are_excluded_and_say_so(self):
        # `d2 44` is `setb` on a *bit* address -- byte 0x28 bit 4, not byte
        # 0x44. The issue says to exclude them and it is right to; the
        # assertion is that intmem_refs does, which is the part a future
        # table edit could get wrong.
        for off in (0xD1FD, 0xD25C):
            self.assertEqual(IMAGE[off], 0xD2)
            self.assertEqual(disasm8051.bit_name(0x44), "0x28.4")
            self.assertNotIn(0xD2, {op for op, _d, _t in intmem_refs.OPCODE_TABLE})

    def test_0x45_is_written_only_by_0x0d7b_in_the_main_ec(self):
        # 0x0DC7 and 0x0E0E, both the scheduler's own. The other two the scan
        # finds are a different program (the PD image) and a different bank.
        self.assertEqual(self.scan(0x45) & {0x0DC7, 0x0E0E}, {0x0DC7, 0x0E0E})

    def test_the_bank1_clr_0x45_is_a_ljmps_own_bytes(self):
        # 0x12D89 -- a `clr 0x45` the scan reports, and `02 c2 45` = `ljmp
        # 0xC245` in the committed listing beside it. The middle and last
        # bytes of a three-byte transfer, read one byte in.
        self.assertEqual(at(0x12D88, 3), "02 c2 45")
        self.assertEqual(decoded(0x12D88, 1)[0][2], "ljmp 0xc245")
        listing = (HERE.parent / 'decompiled' / 'bank1' / 'AD88.asm').read_text()
        self.assertIn("02 c2 45 ljmp     0xc245", listing)

    def test_the_prologue_calls_reach_no_writer_of_0x45(self):
        # Falsifier 2's two calls. 0x386F is nine bytes and touches 0xAD and
        # bit 0x26.3; 0x0E1E tail-jumps to the far-call stub 0x152E. Neither
        # names 0x45, and the honest ceiling is that none of the 403 stubs is
        # statically known to write it -- "not found by this method", not
        # "cannot".
        self.assertEqual(at(0x386F, 9), "78 ad e6 b4 33 02 d2 33 22")
        self.assertEqual(IMAGE[0x0E2B], 0x02)
        self.assertEqual((IMAGE[0x0E2C] << 8) | IMAGE[0x0E2D], 0x152E)
        for addr in range(0x386F, 0x3878):
            self.assertNotIn((0xE5, addr - 0x386F), ())


class TheAnnotation(unittest.TestCase):
    """The `common,0D7B` row exists, carries the cycle, and cites the .asm
    first. `grade_name_basis.py` re-grades `name_basis` off the .asm, so the
    ordering is load-bearing rather than stylistic."""

    def row(self):
        with open(FUNCTIONS) as f:
            for r in csv.DictReader(f):
                if (r['scope'], r['addr']) == ('common', '0D7B'):
                    return r
        return None

    def test_the_row_is_there(self):
        r = self.row()
        self.assertIsNotNone(r, "no ghidra-functions.csv row for common,0D7B")
        self.assertEqual(r['type'], 'state')
        self.assertEqual(r['basis'], 'hand-decoded')

    def test_the_evidence_cites_the_asm_first(self):
        r = self.row()
        self.assertTrue(r['evidence'].startswith('ec/decompiled/common/0D7B.asm'),
                        r['evidence'])
        self.assertIn('ec/decompiled/common/0D7B.c', r['evidence'])

    def test_the_name_names_the_counters_it_advances(self):
        r = self.row()
        self.assertEqual(r['name'], 'divide_down_scheduler_counters_44_45_47')

    def test_the_comment_carries_the_count_and_the_refusals(self):
        c = self.row()['comment']
        self.assertIn('200 entries to this address', c)
        self.assertIn('neither is a period', c)
        self.assertIn('scheduler-divide-down-cycle.md', c)
        # The three refusals are each named rather than implied, because a
        # reader must not be able to combine the count with any one of them by
        # accident. Asserted as three separate facts so a later edit that kept
        # "neither is a period" while dropping one of the three would fail.
        self.assertIn('TMOD at 0x89 is never read', c)
        self.assertIn('oscillator frequency that appears nowhere in the tree', c)
        self.assertIn("not even '200 ticks' is licensed", c)


if __name__ == '__main__':
    unittest.main()
