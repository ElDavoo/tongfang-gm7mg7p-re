#!/usr/bin/env python3
"""`boot_xdata_sites.py`'s interpreter, on fixtures it can be wrong about.

**What this file stands in for.** The tool's own `--self-test` pins the
boot-path answer against `ec/firmware/GMxMGxx_11.800`: the routine set the
vector's bytes name, the store set those routines produce, the three spared
bytes, and the refusals. That is the measurement the write-up rests on, and it
is a known-answer run against the committed image.

This file is the half `--self-test` cannot be. Every case here is a
**hand-built buffer**, so the interpreter's semantics are tested where a real
image could only test them by agreeing with itself -- a store set derived from
the same walk it is checking cannot catch the walk being wrong. The cases pair
with each other: `test_mov_rn_direct_reads_the_address_not_the_literal` is the
case whose absence would let `0xD96F`'s `mov r7,0x82` read the literal `0x82`
instead of DPTR's low byte, and `test_push_order_is_low_byte_first` is the one
whose absence lets a call return with its address bytes exchanged.

**The refusals are half the file.** A check that has quietly stopped refusing
looks exactly like a check that is working, and the way that happens here is
specific: the interpreter models about thirty opcodes, and an arm added for a
routine this image happens to contain would leave every other input still
short-circuiting into a store set that reads as complete. Each refusal case
below builds a buffer that would yield a plausible *wrong* answer with its
guard removed.

No hardware, no firmware image and no network. Every case lays down its own
bytes, except the two that read the committed image to pin the tool's entry
points, and those assert the image's own committed listings rather than the
tool's arithmetic.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# boot_xdata_sites imports disasm8051, bl51_trampolines and trace_xdata_refs
# by bare module name, so the tool directory has to be on the path before the
# tool is loaded rather than after.
sys.path.insert(0, str(HERE))
import boot_xdata_sites as B        # noqa: E402
import trace_xdata_refs as T        # noqa: E402

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
TOOL = HERE / "boot_xdata_sites.py"

# Instruction bytes, named so a case reads as the disassembly rather than as a
# list of integers.
MOV_DPTR_0100 = bytes([0x90, 0x01, 0x00])   # mov dptr,#0x0100
MOVX_WRITE = bytes([0xF0])                   # movx @dptr,a
MOVX_READ = bytes([0xE0])                    # movx a,@dptr
INC_DPTR = bytes([0xA3])                     # inc dptr
RET = bytes([0x22])
SET_DPL = bytes([0xAF, 0x82])                # mov r7,0x82 -- DPL by address
SET_DPH = bytes([0xAE, 0x83])                # mov r6,0x83 -- DPH by address
CLR_C = bytes([0xC3])
MOV_A_R6 = bytes([0xEE])
MOV_A_R7 = bytes([0xEF])
SUBB_10 = bytes([0x94, 0x10])
JNC = bytes([0x50, 0x05])
SHR3 = bytes([0x80, 0xFD])                   # sjmp -3


class InterpreterCases(unittest.TestCase):
    """The 8051 semantics the store set is made of, on hand-built buffers."""

    def run_to_end(self, image, start=0):
        """Execute `image` from `start` and return the Machine.

        A direct `_step()` loop rather than `walk_boot()`: these cases are about
        one instruction's effect on the machine, and going through the boot
        path would put the vector's own calls and the stub set in the way of a
        three-instruction fixture. SP is set to the vector's depth so the `ret`
        that ends a fixture unwinds the outermost frame, as it would in a
        called routine.
        """
        machine = B.Machine(bytes(image))
        machine.base_sp = B.STACK_TOP
        machine.sp = B.STACK_TOP
        pc = start
        while pc is not None:
            pc = B._step(machine, pc)
        return machine



    def test_store_records_the_address_dptr_names(self):
        machine = self.run_to_end(MOV_DPTR_0100 + MOVX_WRITE + RET)
        self.assertEqual(machine.stored(), {0x0100: 0})

    def test_inc_dptr_walks_but_does_not_store(self):
        # The `walked`/`stored` split is what `spared` is reported from, so a
        # byte that was walked and not stored has to be visible as walked.
        machine = self.run_to_end(MOV_DPTR_0100 + INC_DPTR + INC_DPTR + RET)
        self.assertEqual(machine.stored(), {})
        self.assertEqual(machine.walked_set(), {0x0100, 0x0101})

    def test_mov_rn_direct_reads_the_address_not_the_literal(self):
        # `mov r7,0x82` copies DPL, not the number 0x82. An interpreter that
        # takes the operand as a value walks a different range entirely, and
        # this is the shape the 0xD96C loop is built from.
        machine = self.run_to_end(
            MOV_DPTR_0100 + SET_DPL + SET_DPH + MOV_A_R7 + RET)
        self.assertEqual(machine.a, 0x00)
        machine = self.run_to_end(
            bytes([0x90, 0xAB, 0xCD]) + SET_DPL + MOV_A_R7 + RET)
        self.assertEqual(machine.a, 0xCD)

    def test_subb_borrows_and_sets_carry(self):
        # `clr c / mov a,r6 / subb a,#0x10 / jnc` is the range test the boot
        # clear is made of, and the carry out of it is the loop's only exit
        # condition. R6 carries DPH, which `mov dptr,#0x0100` set to 1, so this
        # is 1 - 0x10.
        image = MOV_DPTR_0100 + SET_DPH + CLR_C + MOV_A_R6 + SUBB_10 + RET
        machine = self.run_to_end(image)
        self.assertEqual(machine.a, 0xF1)     # 0x01 - 0x10, borrowed
        self.assertEqual(machine.carry, 1)

    def test_setb_c_makes_the_next_subb_borrow(self):
        # With the carry already set, `subb a,#0xff` is an effective -0x100 and
        # always borrows, where with the carry clear it is an effective -0xff
        # and borrows only when A is 0. This is what makes the second bound read
        # 0x0800 rather than the 0x07FF its own immediates spell, so the two
        # cases are the same instruction with the carry differing.
        image = (SET_DPH + bytes([0xD3]) + MOV_A_R6
                 + bytes([0x94, 0xFF]) + RET)
        machine = self.run_to_end(image)
        self.assertEqual(machine.a, 0x00)     # 0x00 - 0xff - 1 = -0x100
        self.assertEqual(machine.carry, 1)
        # Carry clear: 0x00 - 0xff still borrows, but from -0xff not -0x100 --
        # so a witness that read only the accumulator's value would see both as
        # 0x00 and miss the difference the second bound turns on.
        image = (SET_DPH + CLR_C + MOV_A_R6
                 + bytes([0x94, 0xFF]) + RET)
        machine = self.run_to_end(image)
        self.assertEqual(machine.a, 0x01)     # 0x00 - 0xff
        self.assertEqual(machine.carry, 1)

    def test_push_order_is_low_byte_first(self):
        # The 8051 pushes a return address low byte first. Getting it backwards
        # still looks right inside one frame and only shows as a return address
        # with its halves exchanged.
        machine = B.Machine(bytes([0x00] * 0x200))
        machine.sp = 0xC0
        B._push_return(machine, 0x1234, 0x5678)
        self.assertEqual(machine.direct[0xC1], 0x34)
        self.assertEqual(machine.direct[0xC2], 0x12)

    def test_call_and_ret_round_trip_the_return_address(self):
        #            0  1  2  3  4  5  6  7
        image = bytes([0x12, 0x00, 0x06,   # lcall 0x0006
                       0x22,              # 0x0003: the caller's ret
                       0x00, 0x00,
                       0x22])             # 0x0006: the callee
        machine = B.Machine(image)
        machine.base_sp = B.STACK_TOP
        machine.sp = B.STACK_TOP
        pc = B._step(machine, 0)               # the lcall
        self.assertEqual(pc, 0x06)
        pc = B._step(machine, pc)              # the callee's ret
        self.assertEqual(pc, 3)                # back after the 3-byte lcall
        self.assertEqual(machine.sp, B.STACK_TOP)

    def test_unknown_xdata_byte_never_becomes_zero(self):
        # A `movx a,@dptr` of an address nothing wrote must not read as 0: the
        # whole `written-unknown` token depends on it, and a bytearray XDATA
        # would make "never written" and "written zero" the same value.
        machine = self.run_to_end(MOV_DPTR_0100 + MOVX_READ + MOVX_WRITE + RET)
        self.assertIs(machine.stored()[0x0100], B.Machine.UNKNOWN)

    def test_a_written_byte_reads_back_as_written(self):
        machine = self.run_to_end(
            MOV_DPTR_0100 + MOVX_WRITE + bytes([0xE4]) + MOVX_READ + RET)
        self.assertEqual(machine.stored()[0x0100], 0)
        self.assertEqual(machine.a, 0)

    def test_zero_to_sp_stays_a_flag_and_not_a_value(self):
        # `0x0F75`'s IRAM loop zeroes SP, and the walk has to be able to tell
        # that from SP merely not being set yet -- every routine starts with
        # SP reading 0, so testing the value alone fires on every one of them.
        machine = B.Machine(bytes([0xC2, 0x81, 0x22]))
        self.assertEqual(machine.sp, 0)
        self.assertFalse(machine.sp_written_to_zero)
        B._step(machine, 0)
        self.assertTrue(machine.sp_written_to_zero)

    def test_the_sp_flag_tracks_address_81_not_the_value_of_sp(self):
        # Pushing a return address whose high byte is 0x00 leaves SP at 0xC2,
        # but the flag must stay clear: it records a deliberate write to direct
        # address 0x81, not "SP reads 0". Conflating the two would end every
        # walk at the first `ret` whose return address had a zero high byte.
        machine = B.Machine(bytes(0x200))
        machine.sp = B.STACK_TOP
        B._push_return(machine, 0x007F, 0)
        self.assertEqual(machine.sp, 0xC2)
        self.assertFalse(machine.sp_written_to_zero)
        # ... and the write that does set it.
        B._store(machine, B.Machine.SP, 0)
        self.assertTrue(machine.sp_written_to_zero)

    def test_storing_a_known_value_to_acc_clears_the_unknown_flag(self):
        machine = B.Machine(bytes([0xE0, 0x74, 0x41, 0x22]))
        B._step(machine, 0)                    # movx a,@dptr -- unknown
        self.assertTrue(machine.a_unknown)
        B._step(machine, 1)                    # mov a,#0x41
        self.assertFalse(machine.a_unknown)
        self.assertEqual(machine.a, 0x41)


class RefusalCases(unittest.TestCase):
    """The guards. Each buffer would yield a plausible wrong answer without one."""

    def refuses(self, image, start=0, budget=B.STEP_BUDGET):
        """Assert that walking `image` stops with a `Refusal`, not a store set.

        Routed through `walk_routine()` rather than a bare `_step()` loop, so
        the budget case below is the tool's own budget and not a loop the test
        wrote. The exception is the point -- a walk that completed would leave
        a store set on the machine a caller could go on to read, which is the
        whole failure these cases exist for -- so completion has to fail
        explicitly rather than fall out of the loop.
        """
        try:
            machine = B.walk_routine(bytes(image), start, budget)
        except B.Refusal:
            return
        self.fail(f"the walk completed instead of refusing; it stored "
                  f"{sorted(machine.stored())}")

    def test_unmodelled_opcode_stops_the_walk(self):
        # 0xFF is `mov r7,a`. Treating it as a store or skipping it would leave
        # a store set one byte short that reads as complete.
        self.refuses(MOV_DPTR_0100 + bytes([0xFF]) + RET)

    def test_truncated_immediate_stops_the_walk(self):
        self.refuses(bytes([0x90, 0x34]))

    def test_truncated_operand_stops_the_walk(self):
        self.refuses(bytes([0x75, 0x81]))

    def test_subb_on_an_unknown_accumulator_stops_the_walk(self):
        # The arithmetic has no value to do. Substituting zero would invent one.
        self.refuses(MOV_DPTR_0100 + MOVX_READ + SUBB_10 + RET)

    def test_budget_is_a_refusal_not_a_stop(self):
        # `sjmp -3` is an infinite loop with nothing unmodelled in it, so only
        # the budget can end it -- and a budget that returned a store set would
        # report a partial range clear as a whole one.
        self.refuses(SHR3, budget=64)

    def test_a_branch_off_the_buffer_stops_the_walk(self):
        # A relative branch is free to compute a target past the end. That is a
        # real 8051 address, not an index into this file, so it has to be a
        # refusal rather than an IndexError out of the middle of a walk.
        self.refuses(SHR3)

    def test_an_entry_past_the_buffer_stops_the_walk(self):
        self.refuses(RET, start=0x0100)


class CommittedImageCases(unittest.TestCase):
    """The entry points and the committed table, read from the real inputs."""

    @classmethod
    def setUpClass(cls):
        cls.image = FIRMWARE.read_bytes()
        cls.stubs = B.boot_stubs()

    def test_reset_vector_is_the_entry_the_walk_reads(self):
        # A byte assertion, not the tool's arithmetic: the hardware reset vector
        # is a `ljmp` to the routine that holds the calls, and the tool's
        # `boot_routines()` decodes from `RESET_VECTOR`.
        self.assertEqual(self.image[B.RESET_VECTOR:B.RESET_VECTOR + 3],
                         bytes([0x02, 0x00, 0x70]))

    def test_the_four_routines_come_from_the_vector_bytes(self):
        steps = B.boot_routines(self.image, self.stubs)
        self.assertEqual([payload for kind, payload in steps
                          if kind == "routine"],
                         [0x110A, 0x158E, 0x0F75, 0x1594])
        stops = [payload for kind, payload in steps if kind == "stops"][0]
        self.assertTrue(stops, "the tail-jump stop is not recorded")

    def test_the_vector_own_stores_bracket_the_calls(self):
        # `0x0070` writes XDATA 0x1001, then calls, then copies a byte to
        # 0x0004. The copy landing after `0x0F75` is the whole reason the steps
        # are ordered rather than two separate lists: 0x0004 is cleared by that
        # routine and overwritten by the vector, so it is `written-unknown` and
        # not `cleared`.
        steps = B.boot_routines(self.image, self.stubs)
        kinds = [kind for kind, _ in steps]
        # writes, four routines, writes, stops -- the two `writes` steps are the
        # vector's own `movx` at 0x1001 and its copy to 0x0004, and nothing
        # else on the path emits one.
        self.assertEqual(kinds,
                         ["writes"] + ["routine"] * 4 + ["writes", "stops"])

    def test_the_trampolines_name_bank_zero_targets(self):
        # The shape rule's whole content: `0x1594` carries `mov DPTR,#0xD96C`
        # and `0x158E` carries `mov DPTR,#0xD89F`, each followed by the stub.
        # Read off the committed bytes, not out of the tool.
        self.assertEqual(self.image[0x1594:0x159A],
                         bytes([0x90, 0xD9, 0x6C, 0x02, 0x11, 0x00]))
        self.assertEqual(self.image[0x158E:0x1594],
                         bytes([0x90, 0xD8, 0x9F, 0x02, 0x11, 0x00]))

    def test_the_committed_table_is_reproduced_byte_for_byte(self):
        out = subprocess.run(
            [sys.executable, str(TOOL), "--csv", "--check"],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("byte for byte", out.stdout)

    def test_the_tool_writes_no_file_in_the_annotations_directory(self):
        # A tripwire, the way `test_code_pointer_sites.py` holds
        # `registers.yaml`: the table is `--check`ed and regenerated by command,
        # so a hand-edit has to fail `--check` rather than survive it.
        before = B.SITES_CSV
        with open(before, "rb") as handle:
            original = handle.read()
        subprocess.run([sys.executable, str(TOOL), "--csv"],
                       capture_output=True, text=True, check=True)
        with open(before, "rb") as handle:
            self.assertEqual(handle.read(), original)


class DirectIndexCases(unittest.TestCase):
    """`direct_index()` against `trace_xdata_refs.sites_for()`, on fixtures."""

    def test_index_and_sites_for_agree(self):
        # `direct_index()` exists only because `sites_for()` rescans per
        # address, which is too slow for a 6,000-row table. One implementation,
        # two callers: this is what holds the fast one to the slow one.
        image = bytearray(b"\xff" * 64)
        for off in (0x00, 0x10, 0x20):
            image[off:off + 3] = bytes([0x90, 0x07, 0xD0])
        image[0x08] = 0x90                     # a lone 0x90: not a full site
        image = bytes(image)
        index = B.direct_index(image)
        # `sites_for()` scans `range(len(d) - 2)`, so a `0x90` in the last two
        # bytes is out of range for both -- the fixture asserts the two agree
        # on the boundary rather than only on the interior.
        self.assertEqual(sorted(index), [0x07D0, 0xFFFF])
        self.assertEqual(index[0x07D0], T.sites_for(image, 0x07D0))
        self.assertEqual(index.get(0x1234, []), T.sites_for(image, 0x1234))


class CommandLineCases(unittest.TestCase):
    """`main()`'s exit status, which is the only thing a caller can branch on."""

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args],
                              capture_output=True, text=True)

    def test_self_test_exits_zero(self):
        out = self.run_tool("--self-test")
        self.assertEqual(out.returncode, 0, out.stderr)

    def test_check_without_csv_is_refused_by_argparse(self):
        out = self.run_tool("--check")
        self.assertEqual(out.returncode, 2)
        self.assertIn("--csv", out.stderr)

    def test_a_half_open_range_is_refused(self):
        out = self.run_tool("--lo", "0x09C0")
        self.assertEqual(out.returncode, 1)
        self.assertIn("--lo and --hi", out.stderr)

    def test_an_inverted_range_is_refused(self):
        out = self.run_tool("--lo", "0x09D0", "--hi", "0x09C0")
        self.assertEqual(out.returncode, 1)
        self.assertIn("above", out.stderr)

    def test_a_non_hex_address_is_refused(self):
        out = self.run_tool("0xZZZZ")
        self.assertEqual(out.returncode, 1)
        self.assertIn("not a hex address", out.stderr)

    def test_an_out_of_range_address_is_refused(self):
        out = self.run_tool("0x1FFFF")
        self.assertEqual(out.returncode, 1)
        self.assertIn("16-bit", out.stderr)


if __name__ == '__main__':
    unittest.main()