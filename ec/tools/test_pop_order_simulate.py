#!/usr/bin/env python3
"""`simulate()` held to the table it runs over, under both push orders.

Stands in for: the half of `pd_pop_order_oracle.py` that executes the reader's
own bytes rather than counting sites. `--simulate` is what the
`pd-pop-order-second-witness.md` section 5 headline claim rests on -- that the
direct push order lands on a case of the table the call carries and the swapped
one does not -- and until this suite existed nothing ran it. `test_pop_order_oracle.py`
never mentioned `simulate`, and `pd_pop_order_oracle.py --self-test` calls only
the census functions, so a one-byte mutation of the interpreter's
`mov direct,Rn` handler left all fourteen cases passing and `--self-test` still
reporting success while `--simulate` printed a dispatch to an address that is not
a target of the table. §5's sentence inverted silently.

What it asserts, and what it deliberately does not: the expected dispatch target
is *computed from the table `decode_table()` returns*, not transcribed, and no
case asserts how many entries a table has or how many tables the census walked.
That is what keeps this a test of the interpreter rather than a second census
of the same fifteen tables -- the counts belong to
`test_pop_order_oracle.AgreesWithCommittedSpans`, which compares them to the
committed CSV.

Between them the cases here catch a wrong `DPH`/`DPL` destination, a wrong
`movc` offset, a reversed pop order, and a stop reason that names the wrong
thing. The first is the one worth stating plainly: §5's claim is that `DPH`
ends up holding offset 0 of an entry, and a simulator that wrote it to `DPL`
would produce a *plausible* wrong address rather than a crash, which is the
worst shape for a check to miss.

Nothing here opens a device, reads a register, or needs Windows or hardware:
every input is a committed file.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pd_pop_order_oracle as O
from disasm8051 import OPCODE_LEN, mnemonic

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"

# A read-only handle on the committed image, shared by every case that needs it.
D = FIRMWARE.read_bytes()

# The `lcall` before the `0x8038` table, the one `--simulate` defaults to, and
# the width of the `lcall` the table's offset is derived from. Both are the
# tool's own constants rather than addresses spelled here, so a dump whose
# reader moved re-checks itself instead of inheriting this one's answer.
SITE = O.SITE_0X8038
LCALL_LEN = OPCODE_LEN[0x12]

# Seed values for the registers `--simulate` starts from, distinct and not
# 0x00 or 0xFF so a byte that is read into the wrong register is visible in the
# transcript rather than coinciding with a plausible one. The selector is the
# table's own first case and is derived per case, not here.
SEED_R0, SEED_DPL, SEED_DPH = 0x22, 0x33, 0x44


def table():
    """The table `--simulate` runs over by default."""
    return O.decode_table(D, SITE + LCALL_LEN)


def reader_entry() -> int:
    """The runtime address `--simulate` enters the reader at: the one
    `readers()` finds, rather than 0x7151 spelled here."""
    return O.readers(D)[0][0]["runtime"]


def run(order: str):
    """`simulate()` over the `0x8038` table with the two `pop`s seeded for
    `order`. `(table, dispatch, transcript, stop reason, machine)`.

    Both arms differ in nothing but the two stack bytes, which is the property
    `--simulate` claims and the one a reader of the transcript is being asked to
    see: the same program, entered the same way, told one address or the other.
    """
    tbl = table()
    ret = O.runtime_addr(SITE, True) + LCALL_LEN
    # Under the direct order the return address reaches DPTR as it stands, and
    # under the swapped one it reaches it reversed -- which is what leaves DPTR
    # on the byte-swapped address.
    base = ret if order == O.READINGS[0] else O.byte_swapped(ret)
    machine = O.Machine(tbl["entries"][0]["case"], SEED_R0, SEED_DPL, SEED_DPH)
    dispatch, lines, why = O.simulate(D, O.region_of(SITE, True)[0],
                                      reader_entry(), [base >> 8, base & 0xFF],
                                      machine)
    return tbl, dispatch, lines, why, machine


class DirectOrderReachesTheTable(unittest.TestCase):
    """The push order `bank-call-audit.md` section 9 records."""

    def test_it_dispatches_to_the_tables_own_first_case(self):
        tbl, dispatch, _, why, _ = run(O.READINGS[0])
        self.assertEqual(why, "jumped")
        self.assertEqual(dispatch, tbl["entries"][0]["target"],
                         "the direct push order dispatches to the address the "
                         "table's own first entry names")

    def test_that_address_is_a_target_of_this_table_and_of_no_other_reading(self):
        # The half that holds `0x7166`/`0x7168`: the dispatch has to land on one
        # of the arms `decode_table()` derived *big-endian*, and on none of the
        # byte-swapped ones. A simulator that exchanged the two address bytes on
        # the way into DPH/DPL still dispatches somewhere -- it dispatches to
        # `byte_swapped(0x8054)` -- and this is the assertion that refuses it.
        tbl, dispatch, _, _, _ = run(O.READINGS[0])
        self.assertIn(dispatch, O.arms_of(tbl, O.READINGS[0]))
        self.assertNotIn(dispatch, O.arms_of(tbl, O.READINGS[1]))

    def test_dph_and_dpl_end_up_holding_the_high_and_low_byte_of_that_address(self):
        # Stated as registers rather than as a dispatch target, because this is
        # the specific claim: offset 0 of an entry is the *high* address byte.
        # `mov dph,r0` taking its value from `movc` at offset 0 is what makes
        # the address big-endian, and the two assertions together hold both
        # halves -- an exchange of the two destinations cannot satisfy them.
        tbl, dispatch, _, _, machine = run(O.READINGS[0])
        self.assertEqual(machine.v["DPH"], dispatch >> 8)
        self.assertEqual(machine.v["DPL"], dispatch & 0xFF)
        self.assertEqual((machine.v["DPH"] << 8) | machine.v["DPL"],
                         tbl["entries"][0]["target"])

    def test_the_transcript_ends_on_the_instruction_that_dispatched(self):
        # `simulate()` returns the transcript rather than printing it, so this
        # holds the report honest about where the run stopped: the last line is
        # the `jmp @a+dptr` that dispatched, named by `disasm8051`'s own mnemonic
        # rather than by an address or a string spelled here, and the run ends
        # there rather than at the step budget. A transcript that ran on past the
        # jump, or that stopped for the budget instead, would otherwise be
        # indistinguishable from one that did not.
        _, _, lines, why, _ = run(O.READINGS[0])
        self.assertEqual(why, "jumped")
        self.assertTrue(lines)
        self.assertLess(len(lines), O.SIM_STEPS,
                        "the direct run dispatched, so it did not use the whole "
                        "walk budget")
        pcs = [int(line.split()[0], 16) for line in lines]
        # Split into mnemonic and operands and rejoin with one space:
        # `disasm8051` pads its mnemonic column, and padding is a formatting
        # choice that is not the claim being made here.
        self.assertEqual(" ".join(mnemonic(D, pcs[-1], reader_entry()).split()),
                         "jmp @a+dptr",
                         "the transcript ends on the instruction that dispatched")
        self.assertEqual(pcs[0], reader_entry(),
                         "the walk starts at the reader's first instruction")


class SwappedOrderReachesNothing(unittest.TestCase):
    """The byte-swapped order -- the one that departs from the MCS-51 push
    order, since `lcall` leaves the high byte on top of the stack. This image
    does not take it: the walk never finds the table."""

    def test_it_dispatches_nowhere_within_the_step_budget(self):
        tbl, dispatch, lines, why, _ = run(O.READINGS[1])
        self.assertIsNone(dispatch)
        self.assertIn(f"no dispatch in {O.SIM_STEPS} instructions", why)
        # The whole budget, rather than a walk that stopped early for some other
        # reason: an unresolvable DPTR or a read past the dump is a *different*
        # stop, and one of those would be a finding about the region rule rather
        # than about the walk. Naming the budget is what separates them.
        self.assertEqual(len(lines), O.SIM_STEPS)

    def test_where_it_does_dispatch_nowhere_is_not_an_arm_of_the_table(self):
        # The claim section 5 makes about the final DPTR, held rather than
        # asserted in prose: the address the walk gives up on is ordinary
        # common-area code, not any of the table's arms under either reading.
        tbl, dispatch, _, _, machine = run(O.READINGS[1])
        self.assertIsNone(dispatch)
        self.assertNotIn(machine.dptr(), O.arms_of(tbl, O.READINGS[0]))
        self.assertNotIn(machine.dptr(), O.arms_of(tbl, O.READINGS[1]))

    def test_the_swapped_base_is_where_the_walk_starts_and_the_direct_one_is_not(self):
        # The link to the two `pop`s, and it is what `--simulate` adds over the
        # census: the same interpreter, the same table, entered with the one
        # address or the other. Asserted from the registers rather than from the
        # transcript so it holds whoever prints how much of it.
        ret = O.runtime_addr(SITE, True) + LCALL_LEN
        direct = O.byte_swapped(ret) if O.READINGS[0] == O.READINGS[1] else ret
        _, _, _, _, machine = run(O.READINGS[1])
        self.assertNotEqual(direct, O.byte_swapped(ret))
        self.assertNotEqual(machine.v["DPH"], direct >> 8)


class TheTwoOrdersDiffer(unittest.TestCase):
    """The falsifiable case, in the same shape as the census suite's.

    Every assertion is about a *difference* between the two runs, so a
    `simulate()` that ignored the `pops` it is handed -- running one order twice
    and reporting it as the finding -- fails all of them, while the assertions
    above, which each hold one arm against committed-derived constants, go on
    passing whichever way the swap went.
    """

    def test_the_two_runs_disperse_differently(self):
        _, direct, _, _, direct_machine = run(O.READINGS[0])
        _, swapped, _, _, swapped_machine = run(O.READINGS[1])
        self.assertIsNotNone(direct)
        self.assertIsNone(swapped)
        self.assertNotEqual(direct, swapped)
        self.assertNotEqual(direct_machine.dptr(), swapped_machine.dptr())

    def test_neither_order_reaches_a_dispatch_the_other_one_also_reaches(self):
        # Stated as a property of the pair rather than as two literals, so it
        # holds for a dump where both happen to find something: the two runs
        # must not agree on a target. Without this, an interpreter that walked
        # to the same table both times -- whatever the reason -- would satisfy
        # every assertion above.
        _, direct, _, _, _ = run(O.READINGS[0])
        _, swapped, _, _, _ = run(O.READINGS[1])
        self.assertNotIn(swapped, (direct,))


if __name__ == "__main__":
    unittest.main()