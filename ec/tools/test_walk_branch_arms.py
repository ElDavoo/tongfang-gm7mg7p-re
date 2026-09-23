#!/usr/bin/env python3
"""Offline checks for walk_branch_arms.py: no hardware, and for the parts that
would need a live read nothing but the committed firmware.

The tool's own --self-test holds the r2 hand transcriptions, which is the
oracle for the branch arithmetic. What is here is the rest: the direction
classification, the bounds, the things the tool deliberately refuses to guess,
and the wording of a negative result. A bug in any of those produces a
confident wrong CSV row rather than a crash, which is the failure mode worth
pinning.

The descent cases build their own byte fixtures rather than pointing at the
firmware, so a case keeps testing what it was written to test if the bytes
around some address in the image change. They are walked in the `common`
region, whose file offset equals its runtime address, so a 0x40-byte buffer is
its own address space and the addresses in a test are the offsets in the
fixture.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
# walk_branch_arms imports disasm8051 and trace_xdata_refs by bare module
# name, the way register_ref_table.py does, so the tool directory has to be on
# the path before it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'walk_branch_arms', HERE / 'walk_branch_arms.py')
wba = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wba)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# The descent cases' bounds, named so a case can change one without repeating
# the other's.
DEPTH = 8
INSNS = 64


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0."""
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def walk(img, start=0x00, dptr=None, depth=DEPTH, insns=INSNS):
    return wba.descend(img, "common", start, dptr, depth, insns, True)


# The three access shapes, as the tool decodes them.
READ = bytes([0x90, 0x07, 0x51, 0xE0, 0x22])                       # mov dptr,#0x0751 ; movx a,@dptr ; ret
WRITE = bytes([0x90, 0x07, 0x51, 0xF0, 0x22])                      # ... ; movx @dptr,a ; ret
BOTHE = bytes([0x90, 0x07, 0x51, 0xE0, 0xF0, 0x22])                 # ... ; movx a,@dptr ; movx @dptr,a ; ret
SPLIT = bytes([0x90, 0x07, 0x51, 0xE0, 0x30, 0xE7, 0x02, 0x22])     # ... ; jnb acc.7,+2 ; ret


class DirectionTests(unittest.TestCase):
    """`read` / `write` / `r+w` are three different claims. manual-fan-ctrl-
    0751.md 5 concluded only the third is absent, so a tool that collapsed
    them would quietly change the conclusion."""

    def test_a_read_is_not_a_write(self):
        arm = walk(fixture(READ))
        self.assertEqual(arm.writes(), set())
        self.assertEqual(arm.reads(), {0x0751})
        self.assertEqual(arm.accesses, "0x0751 read")

    def test_a_write_is_not_a_read(self):
        arm = walk(fixture(WRITE))
        self.assertEqual(arm.reads(), set())
        self.assertEqual(arm.writes(), {0x0751})
        self.assertEqual(arm.accesses, "0x0751 write")

    def test_reading_then_writing_the_same_byte_is_r_plus_w(self):
        arm = walk(fixture(BOTHE))
        self.assertEqual(arm.accesses, "0x0751 r+w")

    def test_reading_the_same_byte_twice_is_still_one_read(self):
        # The shape the firmware's own arms have: `jnb acc.7` with `movx a,@dptr`
        # on each side, so the byte is read on both the taken and the
        # fall-through side. Comparing the recorded directions against the
        # exact string "r" would render the doubled read as a write -- which is
        # what it did, and what made every PL in the 0x9Exx arms look written.
        img = fixture(bytes([0x90, 0x07, 0x51, 0xE0, 0x30, 0xE7, 0x00]),
                      bytes([0x90, 0x07, 0x51, 0xE0, 0x22]))
        arm = walk(img)
        self.assertEqual(arm.reads(), {0x0751})
        self.assertEqual(arm.writes(), set())
        self.assertEqual(arm.accesses, "0x0751 read")

    def test_inherited_dptr_is_carried_into_the_arm(self):
        # A site that branches without reloading DPTR leaves its value behind,
        # so the arm's own movx still names the mode byte rather than nothing.
        arm = walk(fixture(READ), dptr=0x0751)
        self.assertEqual(arm.reads(), {0x0751})


class DptrTests(unittest.TestCase):
    """A `movx` is charged to whatever `mov dptr,#imm16` last set, and to
    nothing before that. Charging it to a stale address is how a bounded scan
    reports a confident wrong one."""

    def test_a_dptr_built_from_a_register_is_unattributed(self):
        # The bank1 arms hand the CODE pointer to r2/r1 and rebuild DPTR from
        # them, so catching only `mov 0x82,a` would read 0x93E6 as a register.
        arm = walk(fixture(bytes([0x90, 0x93, 0xE6, 0x8A, 0x83, 0x89, 0x82, 0xE0, 0x22])))
        self.assertEqual(arm.xdata, {})
        self.assertEqual(arm.unattributed, 1)
        self.assertEqual(arm.code_pointers, [])
        self.assertEqual(arm.code_immediates, [0x93E6])

    def test_a_dptr_built_from_the_accumulator_is_unattributed(self):
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0xF5, 0x82, 0xF5, 0x83, 0xE0, 0x22])))
        self.assertEqual(arm.xdata, {})
        self.assertEqual(arm.unattributed, 1)
        self.assertTrue(any("run time" in e for e in arm.ends))

    def test_an_immediate_at_or_above_the_code_floor_cannot_be_xdata(self):
        arm = walk(fixture(bytes([0x90, 0x93, 0xE6, 0x93, 0x22])))
        self.assertEqual(arm.xdata, {})
        self.assertEqual(arm.code_immediates, [0x93E6])
        self.assertEqual(arm.code_pointers, [0x93E6])

    def test_a_movc_reads_code_even_through_a_low_address(self):
        # `movc a,@a+dptr` is a CODE access whatever DPTR holds, so recording
        # it only when the pointer is >= CODE_FLOOR would drop this case -- and
        # a dropped movc is the one that reads as an XDATA access on 0x0751.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0x93, 0x22])))
        self.assertEqual(arm.xdata, {})
        self.assertEqual(arm.reads(), set())
        self.assertEqual(arm.code_pointers, [0x0751])
        self.assertEqual(arm.code_immediates, [])

    def test_movx_through_a_register_is_counted_not_attributed(self):
        arm = walk(fixture(bytes([0xE2, 0x22])))
        self.assertEqual(arm.xdata, {})
        self.assertEqual(arm.movx_ri, 1)


class BoundTests(unittest.TestCase):
    """Every bound has to stop the walk and say so. A bound hit silently is
    the difference between "no arm reaches X" and "the walk stopped before it
    got to X", and only one of those is a finding."""

    def test_a_self_referential_branch_terminates(self):
        arm = walk(wba.LOOP_FIXTURE, start=wba.LOOP_SITE)
        self.assertTrue(any(e.startswith(wba.END_LOOP) for e in arm.ends))
        self.assertEqual(arm.insns, 2)

    def test_a_loop_is_not_reported_as_a_cut(self):
        # An arm that cycles has been fully explored; calling that `cut` would
        # understate what was read.
        self.assertEqual(wba.arm_status(walk(wba.LOOP_FIXTURE, start=wba.LOOP_SITE)),
                         "complete")

    def test_the_depth_limit_is_reported_as_a_cut(self):
        # A chain of sjmps, each one a transfer to the next. At depth 1 the
        # first is followed and the second is where the arm must say it stopped.
        img = fixture(*[bytes([0x80, 0x02, 0x00, 0x00]) for _ in range(4)])
        arm = walk(img, depth=1)
        self.assertTrue(any(e.startswith(wba.END_DEPTH) for e in arm.ends))
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))
        self.assertEqual(arm.insns, 2)

    def test_the_instruction_budget_is_reported_as_a_cut(self):
        arm = walk(fixture(bytes([0x00] * 0x20)), insns=4)
        self.assertTrue(any(e.startswith(wba.END_BUDGET) for e in arm.ends))
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))
        self.assertEqual(arm.insns, 4)

    def test_an_unresolvable_indirect_jump_is_reported_as_a_cut(self):
        arm = walk(fixture(bytes([0x73, 0x22])))
        self.assertTrue(any(e.startswith(wba.END_INDIRECT) for e in arm.ends))
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))

    def test_an_ljmp_ends_the_arm_and_becomes_a_callee(self):
        arm = walk(fixture(bytes([0x02, 0x81, 0x00])))
        self.assertEqual(arm.callees, [0x8100])
        self.assertIn(wba.END_TAIL, arm.ends)
        self.assertEqual(arm.insns, 1)

    def test_an_lcall_is_a_callee_and_the_spine_continues(self):
        # The code after a call is still the arm's own, so the write that
        # follows it has to be in the result.
        arm = walk(fixture(bytes([0x12, 0x81, 0x00]), bytes([0x90, 0x07, 0x51, 0xF0, 0x22])))
        self.assertEqual(arm.callees, [0x8100])
        self.assertEqual(arm.writes(), {0x0751})


class SiteTests(unittest.TestCase):
    """`test_site` has to find the mode-bit branch and refuse to borrow
    somebody else's. The `jnb acc.N` operand is `0xE0 + N`, not `0xE0`."""

    def find(self, img, target=0x0751):
        return wba.test_site(img, "common", 0, 0, target, True)

    def test_a_bit_test_names_the_mode_bit(self):
        found = self.find(fixture(SPLIT))
        self.assertIsNotNone(found)
        self.assertIn("USER (bit 7)", found["test"])
        # `jnb acc.7` is at 0x04 and is 3 bytes, so +2 lands on 0x09.
        self.assertEqual(found["branch"], 0x04)
        self.assertEqual(found["taken"], 0x09)
        self.assertEqual(found["fall"], 0x07)

    def test_a_bit_of_another_sfr_is_not_a_mode_bit(self):
        # `jnb 0x20.0` is a bit of an internal RAM byte, not of the mode byte,
        # and the arms either side of it are not this tool's arms.
        self.assertIsNone(self.find(fixture(bytes([0x90, 0x07, 0x51, 0xE0, 0x30, 0x20, 0x02, 0x22]))))

    def test_a_branch_on_a_byte_loaded_elsewhere_is_not_a_mode_branch(self):
        self.assertIsNone(self.find(fixture(bytes([0x90, 0x04, 0x9F, 0xE0, 0x30, 0xE7, 0x02, 0x22]))))

    def test_a_site_with_no_branch_yields_none(self):
        self.assertIsNone(self.find(fixture(bytes([0x90, 0x07, 0x51, 0x54, 0x7F, 0xF0, 0x22]))))

    def test_a_masked_accumulator_test_reports_the_mask(self):
        # The bank1 shape: `anl a,#0x80 ; jnz`, where the mode bit is in the
        # mask rather than in a bit operand.
        found = self.find(fixture(bytes([0x90, 0x07, 0x51, 0xE0, 0x54, 0x80, 0x70, 0x05])))
        self.assertIsNotNone(found)
        self.assertIn("anl a,#0x80", found["test"])
        self.assertIn("USER (bit 7)", found["test"])


class ClaimWordingTests(unittest.TestCase):
    """A negative result is the deliverable here, so its wording is load-
    bearing. "the EC does not" is the shape docs/findings.md 4d had to
    retract; every claim names the method and the blind spots that bit."""

    def test_a_writing_arm_claims_nothing(self):
        self.assertEqual(wba.no_claim(walk(fixture(WRITE))), "")

    def test_the_negative_is_scoped_to_the_method(self):
        claim = wba.no_claim(walk(fixture(READ)))
        self.assertIn("no arm found by this method", claim)
        self.assertNotIn("the EC does not", claim)
        self.assertNotIn("no arm writes", claim)

    def test_the_claim_lists_the_blind_spots_that_bite_on_this_arm(self):
        # A callee really does limit what a negative can claim, so its
        # presence has to change the sentence.
        plain = wba.no_claim(walk(fixture(READ)))
        called = wba.no_claim(walk(fixture(bytes([0x12, 0x81, 0x00]), bytes([0xE0, 0x22]))))
        self.assertNotIn("unresolved callee", plain)
        self.assertIn("unresolved callee", called)

    def test_a_cut_widens_the_claim_rather_than_narrowing_it(self):
        arm = walk(fixture(READ), depth=0)
        arm.end(f"{wba.END_DEPTH} at 0x0000")
        self.assertIn("a walk stopped at", wba.no_claim(arm))


class FirmwareTests(unittest.TestCase):
    """The counts the rest of the repo quotes, checked against the image, so
    the tool cannot quietly stop covering some of the 29 sites."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = wba.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        cls.rows = wba.arms_for(cls.d, 0x0751, cls.pd, 16, 500)

    def test_all_29_sites_are_accounted_for(self):
        self.assertEqual(len(self.rows), 29)

    def test_17_of_them_branch_on_a_mode_bit(self):
        branched = [r for r in self.rows if r[3] is not None]
        self.assertEqual(len(branched), 17)
        self.assertEqual(sum(1 for r in branched
                             if r[3]["mnemonic"].startswith("jnb")), 16)
        self.assertEqual(sum(1 for r in branched if r[1] == "bank1"), 1)

    def test_every_arm_of_every_branch_is_walked(self):
        for off, region, rt, test, arms in self.rows:
            if test is None:
                self.assertEqual(arms, [], f"0x{rt:04X} has no branch but has arms")
                continue
            self.assertEqual([a.kind for a in arms], ["taken", "fall-through"])
            self.assertEqual(arms[0].start, test["taken"])
            self.assertEqual(arms[1].start, test["fall"])

    def test_every_arm_of_0x0751_is_walked_to_its_bounds(self):
        # The fact the negative claims rest on: nothing was cut short at the
        # default bounds, so "no arm reaches X" is not "the walk gave up".
        for off, region, rt, test, arms in self.rows:
            for arm in arms:
                self.assertEqual(wba.arm_status(arm), "complete",
                                 f"0x{rt:04X} {arm.kind} was cut: {arm.ends}")

    def test_no_arm_of_0x0751_writes_a_power_limit_register(self):
        # manual-fan-ctrl-0751.md 5 concluded no path carries a default into a
        # PL register. The arms are the code that window could not see, so this
        # is where that conclusion either holds or has to be corrected. The
        # 0x9Exx arms *read* 0x0784/0x0785 and branch on them; read and write
        # are different claims and the test is deliberately about the write.
        pls = {0x0783, 0x0784, 0x0785}
        hits = {(f"0x{rt:04X}", arm.kind, f"0x{addr:04X}")
                for off, region, rt, test, arms in self.rows
                for arm in arms for addr in arm.writes() & pls}
        self.assertEqual(hits, set())

    def test_the_arms_writing_a_candidate_pwm_byte_are_the_ones_found(self):
        # 0x075B and 0x075C are in neither registers.yaml nor the EC's own
        # address map as a named register, and have never been confirmed; the
        # arms reach them. That is a prediction for the isolation run, not a
        # result from it, which is why the test only pins *which* arms and
        # leaves the significance to manual-fan-ctrl-0751.md 9.
        reach = {}
        for off, region, rt, test, arms in self.rows:
            for arm in arms:
                for pwm in {0x075B, 0x075C} & arm.writes():
                    reach.setdefault(pwm, set()).add(f"0x{rt:04X} {arm.kind}")
        self.assertIn("0x899D taken", reach[0x075B])
        self.assertIn("0x8942 fall-through", reach[0x075B])
        self.assertIn("0x8E8B taken", reach[0x075C])
        self.assertIn("0x8E8B fall-through", reach[0x075C])


if __name__ == '__main__':
    unittest.main()
