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
fixture -- except the two cases that name the `pd-image` region and the
firmware, where a runtime address and its file offset are two different
numbers or the claim is about this image specifically.

`IncDptrTests` and `UnknownDptrCauseTests` cover what `descend()` does with a
DPTR it cannot name. The second one's check over the two committed tables is a
partition rather than a census: it asserts that a store with no address says
which of the declared causes took the pointer away, and not how many there
are. The numbers move with the walk, and a total in an assertion is a value
every merge that touches the walk has to go and edit.
"""
import csv
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

# The two-byte store: `mov dptr,#hi ; movx @dptr,a ; inc dptr ;
# movx @dptr,a`. This is the shape 0xB730 and the eight 0x8038 handlers do,
# and the one the walk used to truncate at the increment.
PAIR = bytes([0x90, 0x07, 0x51, 0xF0, 0xA3, 0xF0, 0x22])             # mov dptr,#0x0751 ; movx @dptr,a ; inc dptr ; movx @dptr,a ; ret


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


class IncDptrTests(unittest.TestCase):
    """`inc dptr` is a `mov dptr` of the successor, and the walk has to treat
    it as one. It used to credit the byte walked over and then set the pointer
    to unknown, which cost every store after an increment its address -- the
    `movx @dptr,a` reaching `0x089F` at 0xB735, and the low byte of the
    16-bit store every 0x8038 handler does.

    Fixtures, not image addresses, for the reason this file's docstring gives:
    a case anchored at an address keeps testing what it was written to test
    only until the bytes there change. The one case that *is* on the image is
    `UserClearCalleeTests::test_the_inc_dptr_store_lands_on_089f`, which
    exists to pin the acceptance criterion against the firmware itself."""

    def test_the_store_after_an_increment_lands_on_the_successor(self):
        arm = walk(fixture(PAIR))
        self.assertEqual(arm.writes(), {0x0751, 0x0752})
        self.assertEqual(arm.unattributed, 0)
        # The byte walked over is read on the way past and written by the
        # store before the increment, which is why 0x0751 is `r+w` and not
        # `write`. This is a modelling choice, kept: the pointer does cross
        # that byte, and `0x089E` reading as `r+w` where the machine code only
        # writes it is the visible consequence on the real table.
        self.assertEqual(arm.accesses, "0x0751 r+w ; 0x0752 write")

    def test_an_increment_with_no_pointer_beneath_it_stays_unknown(self):
        # `inc dptr` on a pointer nothing set is not `dp + 1` for any `dp` the
        # walk can name, so the store after it is unattributed rather than
        # credited to 0x0001.
        arm = walk(fixture(bytes([0xA3, 0xF0, 0x22])))
        self.assertEqual(arm.xdata, {})
        self.assertEqual(arm.unattributed, 1)

    def test_an_increment_that_carries_bumps_the_high_byte(self):
        # DPL is the low byte, so 0x08FF increments to 0x0900 and the carry
        # lands in DPH. The case the issue asks the tool to state rather than
        # assume, and the one an implementation which added 1 to a masked
        # value would get wrong.
        arm = walk(fixture(bytes([0x90, 0x08, 0xFF, 0xF0, 0xA3, 0xF0, 0x22])))
        self.assertEqual(arm.writes(), {0x08FF, 0x0900})
        self.assertEqual(arm.unattributed, 0)

    def test_the_pointer_wraps_at_the_top_of_the_map(self):
        # DPTR is 16 bits, so the increment from 0xFFFF is 0x0000. A result
        # outside the register would be an address the machine cannot hold.
        arm = walk(fixture(bytes([0x90, 0xFF, 0xFF, 0xF0, 0xA3, 0xF0, 0x22])))
        self.assertEqual(arm.writes(), {0xFFFF, 0x0000})
        self.assertEqual(arm.unattributed, 0)

    def test_a_second_increment_carries_from_the_first(self):
        # Three bytes as one pointer: each increment steps the previous one,
        # so the middle store is neither lost nor charged to the first address.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0xF0, 0xA3, 0xF0, 0xA3, 0xF0, 0x22])))
        self.assertEqual(arm.writes(), {0x0751, 0x0752, 0x0753})
        self.assertEqual(arm.unattributed, 0)

    def test_an_increment_onto_a_code_pointer_is_not_an_xdata_address(self):
        # `mov dptr,#0x93E6` is a CODE pointer and `descend()` records it as
        # one. An increment that reaches one refuses it: the value goes to
        # `code_immediates` and the store after it is unattributed rather than
        # charged to an address the map says is not XDATA. Losing a possible
        # store is the direction this tool takes everywhere else -- see
        # `_dptr_write()` -- and the module docstring's `CODE_FLOOR` argument.
        #
        # `mov dptr` itself does *not* refuse: it records the immediate and
        # leaves the pointer set, so a `movx` behind one is charged to
        # `xdata`. The increment is deliberately the stricter of the two, and
        # `test_the_increment_and_a_mov_dptr_of_the_same_value_disagree` is
        # what keeps that divergence visible rather than accidental.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0xF0, 0xA3, 0xF0, 0x22])))
        # 0x0751 + 1 is not a CODE pointer; the crossing is the separate case
        # below, where the increment itself steps over the floor.
        self.assertEqual(arm.writes(), {0x0751, 0x0752})

        crossed = walk(fixture(bytes([0x90, 0x7F, 0xFF, 0xF0, 0xA3, 0xF0, 0x22])))
        self.assertEqual(crossed.xdata, {0x7FFF: {"r", "w"}})
        self.assertNotIn(0x8000, crossed.xdata)
        self.assertIn(0x8000, crossed.code_immediates)
        self.assertEqual(crossed.unattributed, 1)
        self.assertEqual(crossed.unknown_causes, [wba.DPTR_CODE])

    def test_the_increment_and_a_mov_dptr_of_the_same_value_disagree(self):
        # Pinned so the disagreement above is a fact about this file rather
        # than an accident waiting to be "fixed" in one place and not the
        # other. Making the two agree means deciding what a `movx` behind a
        # CODE immediate is, which is a question about the map rather than
        # about `inc dptr`, and it is not this change's to answer.
        stepped = walk(fixture(bytes([0x90, 0x7F, 0xFF, 0xF0, 0xA3, 0xF0, 0x22])))
        loaded = walk(fixture(bytes([0x90, 0x80, 0x00, 0xF0, 0x22])))
        self.assertIn(0x8000, loaded.xdata)
        self.assertNotIn(0x8000, stepped.xdata)
        self.assertIn(0x8000, loaded.code_immediates)
        self.assertIn(0x8000, stepped.code_immediates)

    def test_a_decrement_between_two_increments_refuses_rather_than_guesses(self):
        # Required by the increment, not by the issue: with the pointer live
        # across more instructions, a stale `dp` here would produce 0x0753 --
        # an address the machine never touches. `_dptr_write()`'s rule is that
        # unattributed is the safe direction and a wrong address is not, and
        # the in-place mutations reach that by the other direction.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0xF0, 0xA5, 0xF0, 0x22])))
        self.assertEqual(arm.xdata, {0x0751: {"w"}})
        self.assertEqual(arm.unattributed, 1)
        self.assertEqual(arm.unknown_causes, [wba.DPTR_MUTATED])

    def test_a_mutation_records_against_the_store_behind_it_not_a_whole_row(self):
        # The reason the causes are a list and not a set. A callee that opens
        # on a `movx` and then decrements DPTR has two stores with no address
        # and two different reasons: the first rode a pointer inherited from the
        # caller, and the second rode one this walk has just seen stepped down.
        # A single set for the row would say one or the other and be wrong
        # about whichever it did not pick.
        #
        # The second cause is also the stronger claim, and the one a reader
        # wants: an inherited pointer would be resolved by carrying the
        # caller's value, while a mutated one would not, because the callee has
        # moved it since.
        arm = wba.descend(fixture(bytes([0xE0, 0xA5, 0xF0, 0x22])), "common", 0,
                          None, DEPTH, INSNS, True, wba.DPTR_INHERITED)
        self.assertEqual(arm.unknown_causes,
                         [wba.DPTR_INHERITED, wba.DPTR_MUTATED])
        self.assertEqual(wba.dp_causes(arm),
                         f"{wba.DPTR_INHERITED} ; {wba.DPTR_MUTATED}")

    def test_the_in_place_dptr_forms_are_the_ones_is_dptr_rebuild_names(self):
        # The write-only half of the table. `inc dpl`/`dec dph`/`xch a,dpl` and
        # the `anl`/`orl`/`xrl` on DPL move the pointer; the `anl a,0x82` forms
        # only read the byte and must leave the pointer alone, or a
        # read-modify-write of a pointer the walk could have followed would be
        # dropped for no reason.
        for op in (0x05, 0x15, 0xC5, 0x42, 0x43, 0x52, 0x53, 0x62, 0x63):
            with self.subTest(op="0x%02X" % op):
                img = fixture(bytes([0x90, 0x07, 0x51]), bytes([op, 0x82, 0x00]),
                              bytes([0xF0, 0x22]))
                arm = walk(img)
                self.assertEqual(arm.unattributed, 1)
                self.assertEqual(arm.unknown_causes, [wba.DPTR_MUTATED])
        for op in (0x55, 0x45, 0x65):
            with self.subTest(op="0x%02X" % op, reads_only=True):
                img = fixture(bytes([0x90, 0x07, 0x51]), bytes([op, 0x82]),
                              bytes([0xF0, 0x22]))
                self.assertEqual(walk(img).writes(), {0x0751})

    def test_a_store_is_charged_across_a_call_and_says_so(self):
        # Issue #197: the callee may have rebuilt DPTR, so the address may be
        # wrong. This does not close that -- the store is charged -- but the row
        # has to say the credit is not one of the unquestioned ones, which is
        # what the `dp_causes` cell and `no_claim()` carry.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0x12, 0x81, 0x00, 0xF0, 0x22])))
        self.assertEqual(arm.writes(), {0x0751})
        self.assertTrue(arm.crossed_call)
        self.assertIn(wba.DPTR_CARRIED, wba.dp_causes(arm))

    def test_a_mov_dptr_after_the_call_clears_the_caveat(self):
        # The mark is about the pointer's history, not a property of the row:
        # once the walk sees a new `mov dptr` the value is the arm's own again
        # and saying otherwise would make the column noise rather than a claim.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0x12, 0x81, 0x00,
                                  0x90, 0x09, 0xE6, 0xF0, 0x22])))
        self.assertEqual(arm.writes(), {0x09E6})
        self.assertFalse(arm.crossed_call)
        self.assertNotIn(wba.DPTR_CARRIED, wba.dp_causes(arm))


class UnknownDptrCauseTests(unittest.TestCase):
    """An `unattributed` count with no cause is a number a reader has to take
    on trust, and the causes are not interchangeable: an inherited pointer is
    unknowable from the row while a rebuilt one is knowable in principle from
    the same bytes. Each unattributed `movx` therefore records which, and the
    cell names them per row."""

    def test_every_unattributed_store_records_exactly_one_cause(self):
        # The partition property, over the two tables this tool produces. Not
        # a count of them: the numbers move with the walk, and a total in an
        # assertion is a value every merge has to edit.
        for addr in (0x0751, 0x1904, 0x1906, 0x1909, 0x190C):
            for label, arm in _all_rows(FIRMWARE, addr):
                with self.subTest(addr="0x%04X" % addr, row=label):
                    self.assertEqual(len(arm.unknown_causes), arm.unattributed)
                    self.assertTrue(set(arm.unknown_causes)
                                    <= set(wba.UNKNOWN_CAUSES),
                                    arm.unknown_causes)

    def test_the_two_committed_tables_leave_nothing_without_a_cause(self):
        # The claim the issue asks for, on the committed CSVs rather than on a
        # re-walk: a reader of either table can tell what every unattributed
        # store in it is a store *through*. `DPTR_CARRIED` is the one cause
        # that can appear without an unattributed store, because it qualifies a
        # store that *was* charged, so the check is on the others.
        for name in ("manual-fan-ctrl-0751-arms.csv", "bank0-8038-handler-arms.csv"):
            path = Path(HERE.parent / 'annotations' / name)
            with self.subTest(csv=name):
                with open(path, newline="") as f:
                    for row in csv.DictReader(f):
                        stores = int(row["unattributed"] or 0)
                        causes = {c for c in row["dp_causes"].split(" ; ") if c}
                        losses = causes - {wba.DPTR_CARRIED}
                        where = "0x%s %s" % (row["addr"],
                                              row["arm_start"] or row["callee"])
                        self.assertEqual(bool(stores), bool(losses),
                                         "%s: %d store(s), %r" % (where, stores,
                                                                  sorted(losses)))
                        self.assertTrue(causes <= _DECLARED, row["dp_causes"])

    def test_a_callee_row_names_the_inherited_pointer_not_a_run_time_build(self):
        # The larger half of what is left. `callee_row()` used to say
        # "partial: DPTR built at run time" for every partial row, which for a
        # callee that never builds one is a claim about the row that is not
        # true -- and it is the cause a reader cannot get anywhere else, since
        # the caller's pointer is precisely what this row does not carry.
        row = wba.callee_row(_fixture_bytes([0xE0, 0x22]), "common", 0, 8, 64)
        self.assertEqual(row[CSV_CAUSES], wba.DPTR_INHERITED)
        self.assertIn(wba.DPTR_INHERITED, row[CSV_STATUS])
        self.assertNotIn("run time", row[CSV_STATUS])

    def test_a_callee_that_rebuilds_the_pointer_names_that_instead(self):
        row = wba.callee_row(
            _fixture_bytes([0x90, 0x07, 0x51, 0xE0, 0xF5, 0x82, 0xE0, 0x22]),
            "common", 0, 8, 64)
        self.assertEqual(row[CSV_CAUSES], wba.DPTR_BUILT)

    def test_a_callee_that_does_both_names_both(self):
        # The case a single-cause `partial:` reason cannot express, and the
        # reason the status cell carries the whole list rather than one of it.
        row = wba.callee_row(
            _fixture_bytes([0xE0, 0x90, 0x07, 0x51, 0xF5, 0x82, 0xE0, 0x22]),
            "common", 0, 8, 64)
        self.assertIn(wba.DPTR_INHERITED, row[CSV_STATUS])
        self.assertIn(wba.DPTR_BUILT, row[CSV_STATUS])


# The cause vocabulary the partition and CSV checks hold the rows to, taken
# from the tool rather than written out here so a new cause is a deliberate
# edit in one place and not something a row can quietly acquire.
_DECLARED = frozenset(wba.UNKNOWN_CAUSES) | {wba.DPTR_CARRIED}

# Cell positions in a `callee_row()` result, named rather than indexed so a
# column added to CSV_HEAD shows up as a wrong constant here and not as a row
# that reads a different cell. Counted from the end, since the cells after the
# address are what `callee_row()` fills in for the callee row shape.
CSV_CAUSES = -4
CSV_STATUS = -2
CSV_UNATTRIBUTED = -5


def _fixture_bytes(insns):
    """The same flat `common`-region buffer `fixture()` builds, as the
    `callee_row()` tests need it -- they call the row builder rather than the
    descent, so they do not have a `walk()` to go through."""
    return fixture(insns)


def _all_rows(firmware, addr):
    """[(label, arm)] for every arm and every callee row one address reaches,
    at the same bounds the committed CSVs are written at. The label is the
    address a reader would look the row up by, so a failure names the row."""
    d = Path(firmware).read_bytes()
    off, magic = wba.PD_MARKER
    pd = d[off:off + len(magic)] == magic
    for _foff, region, rt, test, arms in wba.arms_for(d, addr, pd, 16, 500):
        if test is None:
            continue
        for arm in arms:
            yield f"0x{rt:04X} {arm.kind}", arm
        for callee in dict.fromkeys(c for a in arms for c in a.callees):
            if wba.offset_for_runtime(callee, region) is None:
                continue
            yield f"0x{rt:04X} callee 0x{callee:04X}", wba.descend(
                d, region, callee, None, 16, 500, True, wba.DPTR_INHERITED)


class BoundTests(unittest.TestCase):
    """Every bound has to stop the walk and say so. A bound hit silently is
    the difference between "no arm reaches X" and "the walk stopped before it
    got to X", and only one of those is a finding.

    The cases below the walk bounds pin the classification each stop reason
    carries -- cut or not, decided by what stopped the walk rather than by how
    its message begins. `Arm.end()` takes that verdict as a required argument
    and `arm.cut_ends` reads it back, so these assert the answer rather than a
    match against a string.

    The cases at the end bound `test_site()` rather than the walk, and call it
    directly for the reason the `pd-image` case above does: `walk()` pins the
    region to `common` *and* descends, and these are about the scan."""

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

    def test_an_index_past_the_end_of_the_buffer_is_reported_as_a_cut(self):
        # Ten one-byte opcodes, so the walk decodes all ten and then steps to
        # off == len(d) and reads one past it. `off + n > len(d)` is false on
        # the last byte -- 9 + 1 > 10 is not -- so that test never fires: it
        # asks whether the *instruction* fits, not whether the index is
        # readable. Before the pre-read guard this is an IndexError out of
        # `op = d[off]`, which is a traceback rather than a result.
        arm = walk(bytes(10))
        self.assertTrue(any(e.startswith(wba.END_IMAGE) for e in arm.ends))
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))
        self.assertEqual(arm.insns, 10)

    def test_the_pds_highest_offset_is_above_the_length_main_certifies(self):
        # The region that puts the two numbers furthest apart, named so the
        # case above is not read as an artefact of a short fixture. For
        # `pd-image` the highest offset `offset_for_runtime()` will return is
        # the last address of the region, 0x2FFFF, while main()'s PD-marker
        # check -- a slice comparison, which cannot raise -- certifies a buffer
        # of 0x2004A. This buffer is the one main() accepts, and an arm one
        # byte past the floor has to say so rather than read out of range.
        d = Path(FIRMWARE).read_bytes()
        off, magic = wba.PD_MARKER
        cut = d[:off + len(magic)]
        self.assertEqual(cut[off:off + len(magic)], magic)
        self.assertEqual(wba.offset_for_runtime(0xFFFF, "pd-image"), 0x2FFFF)
        arm = wba.descend(cut, "pd-image", 0x004A, None, DEPTH, INSNS, True)
        self.assertTrue(any(e.startswith(wba.END_IMAGE) for e in arm.ends))
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))

    def test_an_instruction_that_does_not_fit_is_a_cut(self):
        # Nine one-byte opcodes and then the opcode of a three-byte `mov dptr`
        # on the last byte, so `off + n > len(d)` with `off` itself in range.
        # The instruction was never decoded, which is the same condition
        # `END_IMAGE` reports one step earlier for the index; before each
        # reason carried its own verdict this one was emitted address-first,
        # matched no `CUTS` prefix, and the arm read `complete`.
        arm = walk(bytes([0x00] * 9) + bytes([0x90]))
        self.assertEqual(len(arm.cut_ends), 1)
        self.assertIn("runs past the end of the image", arm.cut_ends[0])
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))
        self.assertEqual(arm.insns, 9)

    def test_an_address_outside_the_region_is_a_cut_at_the_entry_point(self):
        # `common` is 0x0000-0x7FFF, so 0x9000 is not in it and the bytes
        # there were never read. Same condition `callee_row()` states as
        # `unresolved: not reachable from region ...` when it fires there.
        self.assertIsNone(wba.offset_for_runtime(0x9000, "common"))
        arm = walk(bytes(0x40), start=0x9000)
        self.assertEqual(arm.insns, 0)
        self.assertEqual(arm.cut_ends,
                         ["0x9000 is not reachable from region common"])
        self.assertTrue(wba.arm_status(arm).startswith("cut:"))

    def test_an_address_outside_the_region_is_a_cut_after_decoding(self):
        # The same case again, reached the way the firmware reaches it: the
        # walk decodes inside the region first and a branch then carries it
        # over the edge, which is the `BANK_EDGE` shape `bucket_c_codemap.py`
        # documents. Without this the case above could be read as an artefact
        # of an entry point that is never in range.
        img = bytearray(0x8000)
        img[0x7FF0:0x7FF3] = bytes([0x40, 0x0D, 0x22])   # jc +13 -> 0x8000 ; ret
        arm = wba.descend(bytes(img), "common", 0x7FF0, None, DEPTH, INSNS, True)
        self.assertGreater(arm.insns, 0)
        self.assertEqual(arm.cut_ends,
                         ["0x8000 is not reachable from region common"])

    def test_the_dptr_note_is_not_a_cut(self):
        # The one reason that is neither: the walk records it and carries on,
        # so an arm whose only end is the DPTR note is complete. `DptrTests`
        # pins that the message is recorded; nothing pinned what it was
        # classified as, which is the half a reader of `arm_status()` sees.
        arm = walk(fixture(bytes([0x90, 0x07, 0x51, 0xF5, 0x82, 0xE0, 0x22])))
        self.assertEqual(arm.ends, [wba.END_DPTR, wba.END_RET])
        self.assertEqual(arm.cut_ends, [])
        self.assertEqual(wba.arm_status(arm), "complete")

    def test_the_four_existing_cuts_stay_cuts(self):
        # One assertion each, so reclassifying any of them has to be
        # deliberate rather than a side effect of a later edit.
        budget = walk(fixture(bytes([0x00] * 0x20)), insns=4)
        self.assertEqual(budget.cut_ends, [f"{wba.END_BUDGET} at 0x0004"])

        depth = walk(fixture(*[bytes([0x80, 0x02, 0x00, 0x00])
                               for _ in range(4)]), depth=1)
        self.assertEqual(len(depth.cut_ends), 1)
        self.assertTrue(depth.cut_ends[0].startswith(wba.END_DEPTH))

        indirect = walk(fixture(bytes([0x73, 0x22])))
        self.assertEqual(indirect.cut_ends, [wba.END_INDIRECT])

        image = walk(bytes(10))
        self.assertEqual(image.cut_ends, [f"{wba.END_IMAGE} at 0x000A"])

    def test_the_non_cuts_stay_non_cuts(self):
        # `ret`/`reti` and a tail jump are the arm finishing or handing over,
        # not the walk giving up, and a loop is an arm that has been fully
        # explored. Same reason as the case above, from the other side.
        for opcode, expected in ((0x22, wba.END_RET), (0x32, wba.END_RETI)):
            arm = walk(fixture(bytes([opcode])))
            self.assertEqual(arm.cut_ends, [], f"{expected} is not a cut")
            self.assertEqual(wba.arm_status(arm), "complete")

        tail = walk(fixture(bytes([0x02, 0x81, 0x00])))
        self.assertEqual(tail.cut_ends, [])
        self.assertIn(wba.END_TAIL, tail.ends)

        looped = walk(wba.LOOP_FIXTURE, start=wba.LOOP_SITE)
        self.assertEqual(looped.cut_ends, [])

    def test_every_stop_reason_descend_can_record_is_accounted_for(self):
        # The issue's done-condition as one executable statement: every
        # reason `descend()` can record is classified here, and the ones that
        # mean the walk gave up are exactly the ones reported. The required
        # `cut` argument is what makes this exhaustive rather than
        # representative -- a new reason cannot be added at a call site
        # without stating a verdict there, and this pins each verdict to the
        # mechanism rather than to a string's first characters.
        cases = {
            # reason: (end, is a cut)
            wba.END_RET: (walk(fixture(bytes([0x22]))), False),
            wba.END_RETI: (walk(fixture(bytes([0x32]))), False),
            wba.END_TAIL: (walk(fixture(bytes([0x02, 0x81, 0x00]))), False),
            wba.END_DPTR: (walk(fixture(bytes([0x90, 0x07, 0x51,
                                               0xF5, 0x82, 0xE0, 0x22]))), False),
            wba.END_INDIRECT: (walk(fixture(bytes([0x73, 0x22]))), True),
        }
        seen = {e for arm, _ in cases.values() for e in arm.ends}
        self.assertEqual(seen, set(cases))
        for reason, (arm, is_cut) in cases.items():
            self.assertIn(reason, arm.ends)
            self.assertEqual(arm.cut_ends == [reason], is_cut, reason)

        # The reasons that carry an address, so they cannot be matched by
        # equality. Four lead with the reason and two lead with the address;
        # both shapes are here because which end a message *begins* with is
        # exactly what the classification no longer depends on.
        for arm, prefix, is_cut in (
            (walk(wba.LOOP_FIXTURE, start=wba.LOOP_SITE), wba.END_LOOP, False),
            (walk(fixture(bytes([0x00] * 0x20)), insns=4), wba.END_BUDGET, True),
            (walk(fixture(*[bytes([0x80, 0x02, 0x00, 0x00])
                           for _ in range(4)]), depth=1), wba.END_DEPTH, True),
            (walk(bytes(10)), wba.END_IMAGE, True),
        ):
            self.assertTrue(any(e.startswith(prefix) for e in arm.ends), prefix)
            self.assertEqual(bool(arm.cut_ends), is_cut, prefix)

        for arm, tail, is_cut in (
            (walk(bytes([0x00] * 9) + bytes([0x90])),
             " runs past the end of the image", True),
            (walk(bytes(0x40), start=0x9000),
             " is not reachable from region common", True),
        ):
            self.assertTrue(any(e.endswith(tail) for e in arm.ends), tail)
            self.assertEqual(bool(arm.cut_ends), is_cut, tail)

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

    def test_a_site_scan_stops_at_an_instruction_the_buffer_does_not_hold_whole(self):
        # `test_site()`'s index guard covers `d[off]`, and a `mov dptr` is
        # three bytes: on the last two of a buffer the guard is satisfied and
        # `d[off + 2]` is not there. Ten one-byte opcodes then a `90 07`, which
        # is the opcode with one of its two operand bytes, walked at the
        # opcode -- the same fixture shape the other cases here build.
        cut = b"\x00" * 10 + bytes([0x90, 0x07])
        self.assertIsNone(wba.test_site(cut, "common", 10, 10, 0x0751, True))

        # The other half, and the reason the guard is `>` and not `>=`: the
        # `jnb` ends on the last byte of the buffer, which is a whole
        # instruction, so it has to decode. An over-bounding guard would
        # refuse it and lose a real site, which is the quiet way to be wrong
        # in the other direction.
        whole = b"\x00" * 10 + bytes([0x90, 0x07, 0x51, 0xE0, 0x30, 0xE7, 0x02])
        found = wba.test_site(whole, "common", 10, 10, 0x0751, True)
        self.assertIsNotNone(found)
        self.assertEqual(len(found["raw"]), wba.OPCODE_LEN[found["raw"][0]])
        self.assertIn("USER (bit 7)", found["test"])

    def test_a_site_scan_does_not_read_a_mask_past_its_own_operand(self):
        # The other end of the scan, and the same bound from the other
        # direction: `anl a,#imm` is the previous instruction of the bank1
        # `anl ; jnz` shape and its immediate is `d[off + 1]`, so a buffer
        # ending on the `54` has an index the guard accepts and an operand it
        # does not hold.
        cut = bytes([0x90, 0x07, 0x51, 0xE0, 0x54])
        self.assertIsNone(wba.test_site(cut, "common", 0, 0, 0x0751, True))

        whole = bytes([0x90, 0x07, 0x51, 0xE0, 0x54, 0x80, 0x70, 0x05])
        found = wba.test_site(whole, "common", 0, 0, 0x0751, True)
        self.assertIsNotNone(found)
        self.assertEqual(len(found["raw"]), wba.OPCODE_LEN[found["raw"][0]])
        self.assertIn("anl a,#0x80", found["test"])


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
        arm.end(f"{wba.END_DEPTH} at 0x0000", cut=True)
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


class UserClearCalleeTests(unittest.TestCase):
    """What manual-fan-ctrl-0751.md 8a says about the two routines the USER
    branches tail-jump to. Section 8 had them "themselves long" and was wrong
    against its own arms CSV; 8a quotes 20 and 8 and then rests its sharpest
    claim -- that both entries into the 0x089E/0x089F pair store arrive with
    the accumulator already zeroed -- on the bytes at three addresses.

    None of that is checked by a gate: no gate compares a document to the arms
    CSV, and the walk tracks DPTR rather than A, so the accumulator claim is
    invisible to everything else in this file. The cases are here because the
    claim is the strongest thing 8a says and the cheapest thing to get wrong.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = wba.PD_MARKER
        cls.rows = wba.arms_for(cls.d, 0x0751, cls.d[off:off + len(magic)] == magic, 16, 500)

    def at(self, runtime, n):
        """`n` bytes of bank0 at a runtime address, as the image holds them."""
        return self.d[wba.offset_for_runtime(runtime, "bank0"):][:n]

    def test_the_two_callees_are_as_short_as_8a_says(self):
        # 20 and 8, both ending in `ret`. The doc quotes them because the
        # arms CSV's `insns` column says so, and this is the same number read
        # off the image rather than off the document.
        self.assertEqual(wba.callee_row(self.d, "bank0", 0xB716, 16, 500)[0], 20)
        self.assertEqual(wba.callee_row(self.d, "bank0", 0xB82E, 16, 500)[0], 8)

    def test_the_user_set_arm_reaches_the_pair_store_too(self):
        # 8a says both entries into 0xB730 carry A = 0, which is only a
        # statement about two paths if the USER-*set* path is one of them.
        #
        # Anchored on the callee, not on 0x089E turning up in the arm's
        # writes: the `jnc 0xb736` at 0xB714 falls through into the
        # 0xB716-0xB736 body, so the arm's own linear block already decodes
        # 0xB730 and 0x089E is in `writes` whether or not the USER-set path
        # is reachable. 0xB730 in `callees` is the tool recording the
        # `ljmp 0xb730` at 0xB6A5, and it does flip when those bytes go.
        # (A tail jump is not followed inline -- it ends the arm and appends
        # the target to `callees`; see `descend()`.)
        arm = next(a for off, region, rt, test, arms in self.rows
                   for a in arms if a.start == 0xB5F1)
        self.assertIn(0xB730, arm.callees)

    def test_the_accumulator_is_cleared_immediately_before_both_entries(self):
        # The claim itself, on the bytes. `clr a` at 0xB72B is one instruction
        # ahead of the store inside 0xB716, and `clr a` at 0xB6A4 is one ahead
        # of the ljmp that reaches the same store from the USER-set arm -- so
        # the stored value is zero on both and neither depends on what the
        # caller happened to leave in A.
        self.assertEqual(self.at(0xB72B, 1), b"\xe4")            # clr a, inside 0xB716
        self.assertEqual(self.at(0xB6A4, 4), b"\xe4\x02\xb7\x30")  # clr a ; ljmp 0xb730
        self.assertEqual(self.at(0xB730, 3), b"\x90\x08\x9e")      # mov dptr,#0x089e

    def test_those_are_the_only_two_entries_into_0xb730(self):
        # 8a says a byte scan finds one `ljmp 0xb730` and no other, and that
        # is what lets it say "both" rather than "the two this method finds".
        # If a second caller ever appears the accumulator claim stops covering
        # the routine, and the test that should notice is this one.
        self.assertEqual([f"0x{i:04X}" for i in range(len(self.d) - 2)
                          if self.d[i:i + 3] == b"\x02\xb7\x30"], ["0xB6A5"])

    def test_the_inc_dptr_store_lands_on_089f(self):
        # The `inc dptr` half of issue #242, on the bytes and then on the walk.
        # 8a attributed the store at 0xB735 to nothing and explained it as a
        # tool limitation -- `descend()` set the pointer to unknown at the
        # increment -- so `0x089E` and `0x089F` were written as one 16-bit
        # store in the firmware and the CSV named only the first byte of it.
        #
        # Both halves are pinned. The bytes first, so the case says what it
        # says about the firmware and not about a walk that would produce the
        # same answer from a different instruction; then the walk, because the
        # credit is the thing the issue is about and no other test in this
        # file covers it against the image.
        self.assertEqual(self.at(0xB730, 7),
                         bytes([0x90, 0x08, 0x9E, 0xF0, 0xA3, 0xF0, 0x22]))
        row = wba.callee_row(self.d, "bank0", 0xB716, 16, 500)
        self.assertIn(0x089F, _xdata_addresses(row))
        # 0x089E is credited a read as well as a write, because the pointer
        # walks over the byte on its way to 0x089F. That is a modelling
        # choice, not what the machine code does, and it is the reason the
        # `XDATA_089E` cell reads `r+w` -- so it is asserted here rather than
        # left to be discovered as an apparent contradiction.
        self.assertIn(0x089E, _xdata_addresses(row))
        self.assertEqual(row[CSV_UNATTRIBUTED], 0)
        # The point the issue names: the store is no longer counted, and the
        # row no longer explains itself by a run-time DPTR build.
        self.assertNotIn("run time", row[CSV_STATUS])
        self.assertEqual(row[CSV_STATUS], "resolved")


def _xdata_addresses(callee_row_result):
    """The addresses a `callee_row()` result's `xdata` cell names."""
    return {int(cell.split(" ", 1)[0], 16)
            for cell in callee_row_result[1].split(" ; ") if cell}


class CheckTableTests(unittest.TestCase):
    """The --check mode validates the committed CSV stays in sync with the
    tool's implementation."""

    def test_walk_branch_arms_check_reproduces_the_committed_csv(self):
        """--check exits 0 when this run reproduces the committed CSV byte for
        byte. This is the gate that keeps the table from silently diverging when
        the walk's DPTR handling or other parts change."""
        d = Path(FIRMWARE).read_bytes()
        off, magic = wba.PD_MARKER
        pd = d[off:off + len(magic)] == magic
        # The committed CSV was cut with --callee-depth 1 and the default
        # --max-insns (500) and --max-depth (16).
        generated = wba.write_csv(d, ["0x0751"], pd, 1, 16, 500)
        committed_path = Path(HERE.parent / 'annotations' / 'manual-fan-ctrl-0751-arms.csv')
        with open(committed_path, newline="") as f:
            committed = f.read()
        self.assertEqual(generated, committed,
                         "run `python3 ec/tools/walk_branch_arms.py "
                         "ec/firmware/GMxMGxx_11.800 0x0751 --callee-depth 1 "
                         "--csv > ec/annotations/manual-fan-ctrl-0751-arms.csv` "
                         "to regenerate the committed table")

    def test_check_refuses_max_insns_the_committed_csv_does_not_record(self):
        """--check refuses when run with a --max-insns that differs from what
        the committed CSV was cut with, preventing false-green comparisons."""
        import sys
        # Test that --check refuses conflicting --max-insns.
        old_argv = sys.argv
        try:
            sys.argv = ["walk_branch_arms.py", "firmware", "--check", "--max-insns", "300"]
            self.assertNotEqual(wba._check_committed_csv_params(), 0,
                               "--check should refuse when --max-insns differs")
            # Test that --check refuses conflicting --max-depth.
            sys.argv = ["walk_branch_arms.py", "firmware", "--check", "--max-depth", "8"]
            self.assertNotEqual(wba._check_committed_csv_params(), 0,
                               "--check should refuse when --max-depth differs")
            # Test that --check refuses conflicting --callee-depth.
            sys.argv = ["walk_branch_arms.py", "firmware", "--check", "--callee-depth", "0"]
            self.assertNotEqual(wba._check_committed_csv_params(), 0,
                               "--check should refuse when --callee-depth differs")
            # Test that --check accepts correct parameters.
            sys.argv = ["walk_branch_arms.py", "firmware", "--check"]
            self.assertEqual(wba._check_committed_csv_params(), 0,
                            "--check should accept defaults")
        finally:
            sys.argv = old_argv


class CommittedArmsTableTests(unittest.TestCase):
    """Properties that the committed arms table must satisfy. These tests
    cannot silently pass if the table is stale -- they verify the table's
    content against the rules the tool enforces."""

    def test_no_committed_arm_ends_on_invalid_cut(self):
        """Every row in the committed CSV represents an arm that either
        completed its walk or stopped at one of the named termination
        reasons. An invalid terminator is a sign the table was generated by a
        different version of the tool."""
        path = Path(HERE.parent / 'annotations' / 'manual-fan-ctrl-0751-arms.csv')
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ends = row.get("ends", "").split("; ")
                for end in ends:
                    if not end:
                        continue
                    # The end must be one of the named ends the tool defines.
                    # It can be simple or with an address. END_LOOP is formatted
                    # as "loop back to 0xXXXX", END_RUNS_PAST and END_UNREACHABLE
                    # include their addresses in the message itself.
                    is_simple = end in (wba.END_RET, wba.END_RETI, wba.END_TAIL,
                                       wba.END_DPTR, wba.END_INDIRECT)
                    is_loop = end.startswith(wba.END_LOOP + " back to 0x")
                    is_with_address = (
                        end.startswith(wba.END_BUDGET + " at 0x") or
                        end.startswith(wba.END_DEPTH + " at 0x") or
                        end.startswith(wba.END_IMAGE + " at 0x") or
                        " runs past the end of the image" in end or
                        " is not reachable from region " in end
                    )
                    self.assertTrue(is_simple or is_loop or is_with_address,
                                   f"0x{row['addr']} {row['arm_start'] or row['callee']}: "
                                   f"unknown terminator: {end!r}")


if __name__ == '__main__':
    unittest.main()
