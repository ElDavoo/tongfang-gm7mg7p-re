#!/usr/bin/env python3
"""Offline checks for pd_dispatch_key.py: no hardware, and nothing but the
committed firmware.

**The measurement is held by value, not stubbed.** The record bytes, the key
addresses and the dispatch targets are asserted against the committed image,
so a byte that moved takes this suite red rather than letting a report go
quietly wrong. The oracle is split in two on purpose: `FIRST_EIGHT` is
transcribed by hand from the arithmetic a reader would do on paper -- it is the
check that the tool is describing the chain at all -- and everything above it
is re-derived from the image.

**And the hand check is not enough, which is the suite's other half.**
`FIRST_EIGHT` covers `R7` 0..7. A model that added the carry flag to `add A,A`
as well as to `addc A,DPH` agrees with every one of those eight and disagrees
with the machine for the 128 bytes from `0x80` up, where the selector byte is
large enough for `2*R7` to leave eight bits. That is not a hypothetical: it is
the defect this tool was written to catch, and `TestCarryHandling` pins it, so
the eight-value oracle cannot quietly become the whole of the coverage.

**The mutations are what make the rest mean anything.** Without them, a
`Machine` that ignored the image and computed the closed form internally would
pass every assertion above, because the closed form is what it computes. Each
mutation changes one byte of a scratch copy of the image and asserts the run
goes red *and names the thing* -- a stride byte that makes the two disagree, an
opcode and a direct address the model refuses rather than skips. A mutation
case that only asserted a red run would pass on a checker that had stopped
looking.

**The refusals are the calibration.** A dump whose 0x20000 region is not the
ITE8850-PD image is refused with the offset in the message rather than decoded
into a page of arithmetic about the wrong program; an opcode or a direct
address outside the modelled set raises rather than being skipped, because a
silent skip is exactly what would let the closed form and the machine agree
while both ignored the byte in question.

Read-only: every fixture is a `tempfile` or the committed image opened for
reading, and `TestWritesNothing` holds `git status --porcelain` byte-identical
across a real run.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# pd_dispatch_key imports its siblings by bare module name, the way the rest of
# this directory does, so the tool directory goes on the path before the load
# rather than after.
sys.path.insert(0, str(HERE))

import pd_dispatch_key as pdk  # noqa: E402

FIRMWARE = str(HERE.parent / "firmware" / "GMxMGxx_11.800")

# The eight addresses issue #647 checks by hand, transcribed rather than
# computed, so the suite contains at least one expectation the tool under test
# did not produce. It is the low end of the byte on purpose: these eight are
# what a reader would do on paper, and `TestCarryHandling` is what says that
# doing eight is not the same as doing 256.
FIRST_EIGHT = (0x0424, 0x0684, 0x08E4, 0x0B44,
               0x0DA4, 0x1004, 0x1264, 0x14C4)

# The four records at file 0x2CB4D, transcribed from
# `ec/decompiled/pd/CB2A.asm`'s last three bytes and the image's next thirteen.
# Only 0xCB4D..0xCB4F appear in any committed listing, so this half of the
# table has no listing to be checked against and is the image's to say.
RECORDS = ((0xCB, 0x5D, 0x01, 0x08),
           (0xCB, 0x66, 0x02, 0x06),
           (0xCB, 0x6F, 0x02, 0x07),
           (0x00, 0x00, 0xCB, 0x76))


def load():
    return pdk.read_image(FIRMWARE)


def patched(offset: int, value: int):
    """A scratch copy of the committed image with one byte replaced."""
    data = bytearray(load())
    data[offset] = value
    return bytes(data)


def file_offset(runtime: int) -> int:
    return pdk.to_file(runtime)


def code(data, addr):
    return pdk.code(data, addr)


class RecordTable(unittest.TestCase):
    """The sixteen bytes at `pd` 0xCB4D, read from the image."""

    def setUp(self):
        self.data = load()

    def test_records_are_the_committed_bytes(self):
        self.assertEqual(tuple(pdk.records(self.data)), RECORDS)

    def test_table_starts_at_the_lcall_return_address(self):
        # `pd 0x11C2` enters with DPTR here because the `lcall 0x11C2` at
        # 0xCB4A pushed a return address of 0xCB4D and the routine pops it
        # straight back into DPTR. If either moved, the table the scan reads
        # would be a different table and every key pair would mean something
        # else.
        self.assertEqual(pdk.TABLE_RUNTIME, 0xCB4A + 3)
        self.assertEqual(pdk.DISPATCH_CALL, 0xCB4A)

    def test_code_resumes_after_the_last_record(self):
        after = pdk.TABLE_RUNTIME + pdk.RECORD * len(RECORDS)
        self.assertEqual(after, 0xCB5D)
        # `eb 64 02` is `mov a,r3 / mov a,@r4 / inc r0`, which is what
        # `store_0803_0805_then_jump_c808`'s decompile reads past its own
        # table. A table that ran further would be claiming these bytes are
        # records.
        self.assertEqual(bytes(code(self.data, after + i) for i in range(3)),
                         b"\xeb\x64\x02")


class KeyAddress(unittest.TestCase):
    """The closed form against the machine, over the whole byte."""

    def setUp(self):
        self.data = load()

    def test_first_eight_match_the_hand_check(self):
        self.assertEqual(tuple(pdk.closed_form(n) for n in range(8)),
                         FIRST_EIGHT)

    def test_closed_form_and_machine_agree_for_every_byte(self):
        self.assertEqual(pdk.agree(self.data), [])

    def test_machine_reports_its_own_address_not_the_closed_form(self):
        # The comparison is only worth anything if the machine arrives at the
        # address on its own. Handing it the closed form as the seed and then
        # reading that seed back would agree for every byte including a
        # completely wrong stride, which is what `Mutations` is for.
        result = pdk.run(self.data, 0x03)
        self.assertEqual(result["machine"], result["closed"])
        self.assertEqual(result["machine"], 0x0B44)

    def test_addresses_are_distinct_across_the_byte(self):
        # Two selector bytes landing on one address would make "which record"
        # ambiguous from the address alone. The stride is 608 and the space is
        # 65536, so 256 of them cannot collide.
        seen = {pdk.closed_form(n) for n in range(0x100)}
        self.assertEqual(len(seen), 0x100)

    def test_carry_handling_is_what_the_upper_half_gets_right(self):
        # `pd 0x349B` is `add A,A` / `add A,DPH` -- two plain adds, so the
        # carry out of the first is discarded and DPH takes 2*R7 modulo 256.
        # `pd 0x10BC` is `add A,DPL` / `addc A,DPH`, and the carry there is
        # folded in. A model that added the carry to both agrees with the
        # closed form for R7 below 0x80 and is one byte out for every byte
        # above it, which is the half the hand check never reaches.
        self.assertEqual(pdk.closed_form(0x80), 0x3424)
        self.assertEqual(pdk.run(self.data, 0x80)["machine"], 0x3424)
        self.assertEqual(pdk.run(self.data, 0xFF)["machine"], 0x61C4)

    def test_key_addresses_share_one_residue(self):
        # The stride is 0x260 = 32 * 19, so every address the chain can reach
        # is congruent to the base modulo 32. This is arithmetic about this
        # call site only: the other fifteen `lcall 0x11C2` sites build their
        # own DPTR.
        residues = {pdk.closed_form(n) % pdk.KEY_ADDR_MODULUS
                    for n in range(0x100)}
        self.assertEqual(residues, {pdk.BASE % pdk.KEY_ADDR_MODULUS})


class Selection(unittest.TestCase):
    """The record table as a function of the key pair."""

    def setUp(self):
        self.data = load()
        self.recs = pdk.records(self.data)

    def test_keyed_records_key_on_the_bytes_the_scan_compares(self):
        self.assertEqual(pdk.select_record(self.recs, 0x01, 0x08),
                         (0, 0xCB5D))
        self.assertEqual(pdk.select_record(self.recs, 0x02, 0x06),
                         (1, 0xCB66))
        self.assertEqual(pdk.select_record(self.recs, 0x02, 0x07),
                         (2, 0xCB6F))

    def test_every_other_pair_takes_the_default(self):
        # The `00 00` record is what stops the scan, so this table cannot be
        # walked off its end whatever the pair is. That is a property of these
        # sixteen bytes, not of the caller.
        for low, high in ((0x00, 0x00), (0xFF, 0xFF), (0x01, 0x07), (0x7F, 0x7F)):
            self.assertEqual(pdk.select_record(self.recs, low, high),
                             (3, 0xCB76))

    def test_default_wins_over_a_key_that_would_also_match_it(self):
        # The `+0`/`+1` test comes first in the scan, so a record whose target
        # pair is zero never reaches the comparison. The census has to make the
        # same decision the machine does or the two are not describing one
        # routine.
        recs = ((0x00, 0x00, 0x12, 0x34),)
        self.assertEqual(pdk.select_record(recs, 0x12, 0x34), (0, 0x1234))

    def test_machine_agrees_with_the_census_on_the_named_set(self):
        self.assertEqual(pdk.machine_agrees(self.data, self.recs,
                                             pdk.probe_pairs(self.recs)), [])

    def test_named_probes_cover_the_table(self):
        pairs = set(pdk.probe_pairs(self.recs))
        for rec in self.recs:
            if not pdk.is_default(rec):
                self.assertIn((rec[2], rec[3]), pairs)
        self.assertIn((0x00, 0x00), pairs)
        self.assertIn((0xFF, 0xFF), pairs)

    def test_key_pair_order_is_low_byte_first(self):
        # `pd 0x38D3` leaves B holding `XDATA[addr]` and A holding
        # `XDATA[addr+1]`, and the scan compares `CODE[+2]` against B. Printing
        # the pair the other way round would still be self-consistent and would
        # name the wrong records, so the order is pinned against the census.
        result = pdk.run(self.data, 0x00, pair=(0x01, 0x08))
        self.assertEqual((result["low"], result["high"]), (0x01, 0x08))
        self.assertEqual(result["target"], 0xCB5D)


class Chain(unittest.TestCase):
    """The chain's shape, as the listings state it."""

    def setUp(self):
        self.data = load()

    def test_every_chain_entry_has_a_listing(self):
        for addr, _ in pdk.CHAIN:
            listing = HERE.parent / "decompiled" / "pd" / f"{addr:04X}.asm"
            self.assertTrue(listing.exists(), f"no listing at {listing}")

    def test_34ef_has_no_return(self):
        # `pd 0x34EF` is one instruction and falls through into `pd 0x34F2`,
        # so the stride is supplied by a fall-through rather than by a second
        # call. A `ret` here would make the chain two calls and the
        # derivation's shape wrong while every address in it stayed right.
        text = (HERE.parent / "decompiled" / "pd" / "34EF.asm").read_text()
        self.assertNotIn("ret", text)
        machine = pdk.Machine(self.data)
        machine.run(0x34EF)
        entered = [addr for addr, _, _, _ in machine.steps]
        # The step after `pd 0x34EF` is the next address, which is what
        # "falls through" means: no branch and no call gets there.
        self.assertEqual(entered[:4], [0x34EF, 0x34F2, 0x34F5, 0x10BC])
        self.assertEqual(entered[1], entered[0] + pdk.OPCODE_LEN[
            pdk.code(self.data, entered[0])])

    def test_chain_runs_through_the_no_return_helpers(self):
        machine = pdk.Machine(self.data)
        machine.r[pdk.SELECTOR_REG] = 0x00
        machine.r[3] = pdk.R3_SUBSTITUTE
        machine.run(0xCB2A)
        entered = [addr for addr, _, _, _ in machine.steps]
        for addr, _ in pdk.CHAIN[1:]:
            self.assertIn(addr, entered,
                          f"0x{addr:04X} was never entered by the chain")

    def test_r3_guard_precondition(self):
        # `pd 0xCB2A` returns at 0xCB3A when R3 == 0x0D, before any of the key
        # arithmetic. The selector therefore only runs for a caller that does
        # not take that branch, and the simulation says which value it used
        # rather than picking one silently.
        machine = pdk.Machine(self.data)
        machine.r[pdk.SELECTOR_REG] = 0x05
        machine.r[3] = pdk.R3_GUARD_VALUE
        machine.run(0xCB2A)
        self.assertEqual(machine.stop, "top-ret")
        self.assertIsNone(machine.target)
        self.assertNotIn(0x34EF, [addr for addr, _, _, _ in machine.steps])

    def test_key_address_is_read_before_dptr_is_rebuilt(self):
        # DPTR at the dispatch call is one past the key address, because
        # `pd 0x38D3` runs `inc DPTR` between the two byte reads. Reading the
        # wrong side of that increment is a one-byte disagreement that looks
        # like a broken derivation.
        machine = pdk.Machine(self.data)
        machine.r[pdk.SELECTOR_REG] = 0x02
        machine.r[3] = pdk.R3_SUBSTITUTE
        machine.run(0xCB2A)
        self.assertEqual(machine.state_at(pdk.KEY_ADDRESSED)[0], 0x08E4)
        self.assertEqual(machine.state_at(pdk.DISPATCH_CALL)[0], 0x08E5)


class Refusals(unittest.TestCase):
    """What this tool will not describe, and why."""

    def test_dump_without_the_pd_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nomarker.bin"
            data = bytearray(load())
            off, _ = pdk.PD_MARKER
            data[off:off + 8] = b"NOTAPD!!"
            path.write_bytes(bytes(data))
            with self.assertRaises(pdk.Refusal) as caught:
                pdk.read_image(str(path))
        self.assertIn(f"0x{off:05X}", str(caught.exception))

    def test_missing_file_is_a_missing_file(self):
        # Not a Refusal: `open` raising is already the loud, honest failure,
        # and wrapping it would name a problem that is not this tool's to
        # diagnose.
        with self.assertRaises(OSError):
            pdk.read_image(str(HERE / "no-such-image.bin"))

    def test_code_address_outside_the_pd_region(self):
        data = load()
        lo, hi, _ = pdk.pd_region()
        with self.assertRaises(pdk.Refusal) as caught:
            pdk.code(data, 0x10000)
        self.assertIn("16-bit", str(caught.exception))
        # A `movc` that walked off the end of the program must not read a byte
        # from the erased band above it, where everything is 0xFF and a wrong
        # answer would look like a match.
        self.assertTrue(pdk.in_region(lo))
        self.assertFalse(pdk.in_region(hi))

    def test_state_at_an_address_the_chain_never_reached(self):
        data = load()
        machine = pdk.Machine(data)
        machine.r[pdk.SELECTOR_REG] = 0x00
        machine.r[3] = pdk.R3_GUARD_VALUE
        machine.run(0xCB2A)
        with self.assertRaises(pdk.Refusal) as caught:
            machine.state_at(0x10BC)
        self.assertIn("not executed", str(caught.exception))


class Mutations(unittest.TestCase):
    """One byte of a scratch image changed; the run must notice.

    Without these, a `Machine` that computed the closed form internally and
    never read the firmware would pass every assertion above -- the closed form
    is what it computes, so agreeing with it proves nothing about whether the
    image was consulted. Each case therefore asserts the failure *names* the
    thing, not merely that something went red.
    """

    def test_stride_byte_change_breaks_the_agreement(self):
        # `pd 0x34F2`'s `mov B,#0x60`: the multiplier the whole stride is
        # built on. Patched at the immediate, not the direct byte, because the
        # direct byte is 0xF0 -- B -- and moving that is a different opcode's
        # operand rather than the same instruction.
        mutated = patched(file_offset(0x34F4), 0x61)
        mismatches = pdk.agree(mutated)
        self.assertTrue(mismatches)
        self.assertEqual([n for n, _, _ in mismatches if n == 0x01], [0x01])
        # R7 = 0 multiplies out to nothing, so the one byte that cannot notice
        # is the one the chain starts from.
        self.assertNotIn(0x00, [n for n, _, _ in mismatches])

    def test_base_change_breaks_the_agreement(self):
        # `pd 0x34EF`'s `mov DPTR,#0x0424` -- the high byte of the immediate,
        # so the base moves to 0x2524. Every selector byte notices this one,
        # including R7 = 0, which is what distinguishes it from the stride:
        # the stride multiplies out to nothing at zero and the base does not.
        mutated = patched(file_offset(0x34F0), 0x25)
        self.assertEqual(len(pdk.agree(mutated)), 0x100)
        self.assertEqual(pdk.run(mutated, 0x00)["machine"], 0x2524)

    def test_carry_flag_is_read_from_the_image_not_assumed(self):
        # `pd 0x349B`'s `add A,DPH` at 0x349D made an `addc`. The difference
        # is visible only where the `add A,A` above it carried -- R7 = 0x80 is
        # the smallest byte that does -- so the case asserts both directions:
        # a selector byte with no carry is unmoved, and one with a carry is a
        # whole DPH out. A model that hard-coded either behaviour passes half
        # of this and fails the other half.
        mutated = patched(file_offset(0x349D), 0x35)
        self.assertEqual(pdk.run(mutated, 0x03)["machine"],
                         pdk.run(load(), 0x03)["machine"])
        self.assertEqual(pdk.run(mutated, 0x80)["machine"],
                         pdk.run(load(), 0x80)["machine"] + 0x100)

    def test_unmodelled_opcode_is_refused_not_skipped(self):
        # `pd 0x10BC`'s `mul ab` replaced with `djnz r2,rel`, which this model
        # does not implement. A silent skip here is what would let the closed
        # form and the machine agree while both ignored the multiplication.
        mutated = patched(file_offset(0x10BC), 0xD8)
        with self.assertRaises(pdk.Refusal) as caught:
            pdk.run(mutated, 0x03)
        self.assertIn("0x10BC", str(caught.exception))
        self.assertIn("0xd8", str(caught.exception).lower())

    def test_unmodelled_direct_address_is_refused_not_read_as_zero(self):
        # `pd 0x349B`'s `add A,0xE0` retargeted at a direct byte this model
        # does not carry. Reading it as zero would compute a plausible address
        # from a byte nobody looked at.
        mutated = patched(file_offset(0x349C), 0x30)
        with self.assertRaises(pdk.Refusal) as caught:
            pdk.run(mutated, 0x03)
        self.assertIn("0x30", str(caught.exception))

    def test_record_byte_change_moves_the_census_not_just_the_print(self):
        # The high key byte of the first record, `CODE[+3]` at 0xCB50. The
        # pair that selects the record moves with it; the target does not,
        # because the target is `CODE[+0]`/`CODE[+1]` and neither was touched.
        mutated = patched(file_offset(0xCB50), 0x09)
        recs = pdk.records(mutated)
        self.assertNotEqual(tuple(recs), RECORDS)
        self.assertEqual(pdk.select_record(recs, 0x01, 0x09), (0, 0xCB5D))
        self.assertEqual(pdk.select_record(recs, 0x01, 0x08), (3, 0xCB76))

    def test_table_without_a_default_leaves_pairs_unclaimed(self):
        # With the `00 00` record's first two bytes made nonzero it becomes an
        # ordinary keyed record, and the table has no terminator at all: four
        # keyed records, four pairs claimed, and the census says the other
        # 65532 are claimed by nothing. That is the shape of a scan running off
        # the end of its table, and it is why the committed table's fourth
        # record being `00 00` is a measurement rather than a detail.
        mutated = patched(file_offset(0xCB59), 0x01)
        recs = pdk.records(mutated)
        self.assertFalse(any(pdk.is_default(rec) for rec in recs))
        claimed = {(rec[2], rec[3]) for rec in recs}
        self.assertEqual(len(claimed), len(recs))
        unclaimed = sum(1 for low in range(0x100) for high in range(0x100)
                        if pdk.select_record(recs, low, high) is None)
        self.assertEqual(unclaimed, 65536 - len(recs))


class ListingParse(unittest.TestCase):
    """`listing_mnemonic`, which the self-test's verdict rests on entirely."""

    def test_two_and_three_byte_forms(self):
        self.assertEqual(pdk.listing_mnemonic("11D2     93 - -   movc  A,@A+DPTR"),
                         (0x11D2, "movc"))
        self.assertEqual(pdk.listing_mnemonic("34F2     75 f0 60 mov  B, #0x60"),
                         (0x34F2, "mov"))

    def test_headers_and_blank_lines_are_not_instructions(self):
        self.assertIsNone(pdk.listing_mnemonic("; pd @ 11C2   dispatch_2byte"))
        self.assertIsNone(pdk.listing_mnemonic(""))

    def test_a_hex_pair_is_a_byte_not_a_mnemonic(self):
        # `mov` and `mul` are not two hex digits and `jz` is not either, which
        # is what makes "first non-byte token" unambiguous on these listings.
        self.assertEqual(pdk.listing_mnemonic("10BC     a4 - -   mul   ab"),
                         (0x10BC, "mul"))


class SelfTest(unittest.TestCase):
    """The tool's own `--self-test`, run the way a reader would run it."""

    def test_self_test_is_green_on_the_committed_tree(self):
        out = subprocess.run(
            [sys.executable, str(HERE / "pd_dispatch_key.py"), FIRMWARE,
             "--self-test"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("re-derive", out.stdout)

    def test_self_test_reports_a_stale_listing(self):
        # A listing whose bytes no longer match the image is the case the
        # self-test exists for. Held by driving `listing_mnemonic` over a
        # hand-made line rather than by editing a committed file, because the
        # committed listings are shared and several agent PRs are open against
        # them.
        stale = "11D2     93 - -   ljmp  0x0000"
        at, printed = pdk.listing_mnemonic(stale)
        decoded = pdk.mnemonic(load(), file_offset(at), at).split()[0]
        self.assertEqual(printed, "ljmp")
        self.assertNotEqual(decoded, printed)


class CommandLine(unittest.TestCase):
    """The exits, because a tool that reports a disagreement as 0 is worse
    than one that crashes."""

    def tool(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / "pd_dispatch_key.py"), FIRMWARE, *args],
            capture_output=True, text=True)

    def test_default_run_is_green_and_prints_the_table(self):
        out = self.tool()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("cb 5d 01 08", out.stdout)
        self.assertIn("256 agree, 0 disagree", out.stdout)

    def test_select_is_green(self):
        out = self.tool("--select")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("65533 of 65536 pairs", out.stdout)

    def test_verify_all_without_select_is_a_usage_error(self):
        out = self.tool("--verify-all")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("--select", out.stderr)

    def test_chain_trace_names_the_addresses(self):
        out = self.tool("--chain", "0x03")
        self.assertEqual(out.returncode, 0, out.stderr)
        for addr in (0xCB2A, 0x34EF, 0x10BC, 0x349B, 0x38D3, 0x11C2):
            self.assertIn(f"0x{addr:04X}", out.stdout)

    def test_refused_image_exits_two_with_the_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nomarker.bin"
            data = bytearray(load())
            off, _ = pdk.PD_MARKER
            data[off:off + 8] = b"NOTAPD!!"
            path.write_bytes(bytes(data))
            out = subprocess.run(
                [sys.executable, str(HERE / "pd_dispatch_key.py"), str(path)],
                capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertIn(f"0x{off:05X}", out.stderr)
        self.assertEqual(out.stdout, "")


class TestWritesNothing(unittest.TestCase):
    """The tool is read-only, and a run that left a file behind would be a
    finding about the tree rather than about the machine."""

    def test_working_tree_is_byte_identical_across_a_run(self):
        before = subprocess.run(["git", "status", "--porcelain"],
                                cwd=str(HERE.parent.parent),
                                capture_output=True, text=True).stdout
        subprocess.run(
            [sys.executable, str(HERE / "pd_dispatch_key.py"), FIRMWARE,
             "--select"], capture_output=True, text=True)
        after = subprocess.run(["git", "status", "--porcelain"],
                               cwd=str(HERE.parent.parent),
                               capture_output=True, text=True).stdout
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
