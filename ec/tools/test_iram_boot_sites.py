#!/usr/bin/env python3
"""`iram_boot_sites.py`'s `@Ri` pairing, on buffers it can be wrong about.

**What this file stands in for.** The tool's own `--self-test` pins the pairing
against the committed image: the `0x0162`/`0x0164` and `0x017E` pairs in
`../decompiled/common/012F.asm` resolve to `0x84` and `0xAA`, the direct scan
finds no write to `0x84` at all, and `0x0F91` in `../decompiled/common/0F75.asm`
is left unresolved. That is a known-answer run against committed listings.

This file is the half `--self-test` cannot be. Every pairing case here is a
**hand-built buffer**, so the method is tested where the committed image could
only test it by agreeing with itself: a scan that paired a `mov Rn,#imm` with
the *next* `@Ri` instruction regardless of which register that instruction names
would still produce the three `012F.asm` rows and a great deal else, and nothing
on the committed image distinguishes the two rules. `PairingCases` lays down
`mov R0,#0x84` followed by `mov @R1,A` and reads what comes out.

**The refusals are half the file.** A scan window that runs off the end of the
buffer drops its last candidate silently, and a table one row short reads as a
complete census of a shorter image -- which is exactly what a check that has
quietly stopped refusing looks like.

No hardware, no network, no Ghidra. The cases that read the committed image
assert the image's own bytes against the tool, not the tool against itself.
"""
import csv
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# iram_boot_sites imports data_regions, disasm8051, intmem_refs and
# trace_xdata_refs by bare module name, so the tool directory has to be on the
# path before the tool is loaded rather than after.
sys.path.insert(0, str(HERE))
import intmem_refs as I                 # noqa: E402
import iram_boot_sites as S             # noqa: E402

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
TOOL = HERE / "iram_boot_sites.py"
SITES_CSV = HERE.parent / "annotations" / "iram-boot-sites.csv"

# Instruction bytes, named so a case reads as the disassembly rather than as a
# list of integers.
LOAD_R0 = bytes([0x78])                 # mov r0,#imm -- the pointer load
LOAD_R1 = bytes([0x79])                 # mov r1,#imm
STORE_IMM_R0 = bytes([0x76])            # mov @r0,#data -- a write through R0
STORE_IMM_R1 = bytes([0x77])            # mov @r1,#data
READ_A_R0 = bytes([0xE6])               # mov a,@r0
STORE_A_R0 = bytes([0xF6])              # mov @r0,a
STORE_A_R1 = bytes([0xF7])              # mov @r1,a


def pairs(data):
    """`pair_sites()` for `data`, as {site offset: (load offset, address)}."""
    return S.pair_sites(S.ri_sites(data), S.load_sites(data))


class PairingCases(unittest.TestCase):
    """The pairing on buffers built to have exactly one reading."""

    def test_a_load_followed_by_its_own_register_resolves(self):
        data = LOAD_R0 + bytes([0x84]) + STORE_IMM_R0 + bytes([0x02])
        self.assertEqual(pairs(data), {2: (0, 0x84)})

    def test_the_address_is_the_immediate_not_the_opcode(self):
        # The whole point of following the register: the operand byte of
        # `mov @r0,#data` is the *value*, and reading it as the address would
        # put every paired row on byte 0x02.
        data = LOAD_R0 + bytes([0xAA]) + STORE_IMM_R0 + bytes([0x02])
        self.assertEqual(pairs(data)[2], (0, 0xAA))

    def test_a_store_of_the_accumulator_resolves_to_the_same_address(self):
        # `mov @r0,A` carries no immediate of its own, so the only thing that
        # can name the byte is the load -- and the value written is whatever
        # the accumulator held, which this method does not claim to know.
        data = LOAD_R0 + bytes([0x99]) + STORE_A_R0
        self.assertEqual(pairs(data), {2: (0, 0x99)})

    def test_a_read_through_the_register_resolves_too(self):
        data = LOAD_R0 + bytes([0x84]) + READ_A_R0
        self.assertEqual(pairs(data), {2: (0, 0x84)})

    def test_a_load_for_the_other_register_does_not_resolve(self):
        # `mov r0,#0x84` then `mov @r1,A`: R1 holds something else, and pairing
        # them would name a byte neither instruction names.
        data = LOAD_R0 + bytes([0x84]) + STORE_A_R1
        self.assertEqual(pairs(data), {})

    def test_a_load_and_a_store_for_different_registers_do_not_pair(self):
        data = LOAD_R0 + bytes([0x84]) + LOAD_R1 + bytes([0xAA]) + STORE_IMM_R1 \
            + bytes([0x02])
        # The R1 pair resolves; the R0 load three bytes back does not, because
        # the `@r1` site names R1 and only R1.
        self.assertEqual(pairs(data), {4: (2, 0xAA)})

    def test_a_load_several_instructions_back_does_not_resolve(self):
        # The stated blind spot, pinned: widening the window to "the last
        # `mov Rn,#imm`" would resolve this and would be wrong, because a
        # register reloaded in between carries a different address.
        data = LOAD_R0 + bytes([0x84]) + bytes([0xE4]) + bytes([0x90]) \
            + bytes([0x00, 0x40]) + STORE_A_R0
        self.assertEqual(pairs(data), {})

    def test_a_site_with_no_load_at_all_does_not_resolve(self):
        self.assertEqual(pairs(STORE_A_R0), {})

    def test_the_site_at_offset_zero_has_no_room_for_a_load(self):
        # Not a refusal: the site is real and it is reported as unresolved. The
        # row exists; only its address is unestablished.
        self.assertEqual(pairs(LOAD_R0 + bytes([0x84]) + STORE_A_R0),
                         {2: (0, 0x84)})
        self.assertEqual(S.ri_sites(bytes([0xF6]))[0][0], 0)

    def test_every_ri_site_is_either_paired_or_left_unresolved(self):
        # The partition, on a buffer with both kinds in it. A site dropped from
        # one side and not the other would make the pairing's yield read higher
        # than it is.
        data = (LOAD_R0 + bytes([0x84]) + STORE_A_R0
                + bytes([0x00]) + STORE_A_R1
                + bytes([0x00]) + READ_A_R0)
        sites = {site[0] for site in S.ri_sites(data)}
        self.assertEqual(sites, {2, 4, 6})
        self.assertEqual(set(pairs(data)), {2})


class OpcodeTableCases(unittest.TestCase):
    """`RI_TABLE` against `intmem_refs.OPCODE_TABLE` and the 8051 encoding."""

    def test_the_two_tables_name_different_instructions(self):
        # The same two bytes read as a direct operand and as an `@Ri` opcode
        # name different bytes. A scan holding both would count one instruction
        # twice under two answers, so the overlap is checked rather than assumed
        # away in review.
        direct = {op for op, _direction, _text in I.OPCODE_TABLE}
        self.assertEqual(direct & set(S.RI_BY_OPCODE), set())

    def test_the_movx_forms_are_absent(self):
        # `movx a,@Ri` and `movx @Ri,A` reach XDATA, which is a different
        # address space. In this dump they are how the ITE8850-PD image reads
        # its own external RAM, and counting them as internal-RAM byte
        # references is the mistake `intmem_refs.py` records for `0x90`.
        for op in (0xE2, 0xE3, 0xF2, 0xF3):
            self.assertNotIn(op, S.RI_BY_OPCODE)

    def test_the_mov_dptr_form_is_absent(self):
        self.assertNotIn(0x90, S.RI_BY_OPCODE)

    def test_each_rows_register_is_the_opcodes_low_bit(self):
        # `@Ri` is R0 for the even opcode and R1 for the odd one, in every one
        # of the five encodings. A row that disagreed would pair a load into
        # R0 with a store through R1.
        for op, reg, _direction, _text, _operands in S.RI_TABLE:
            self.assertEqual(reg, op & 1, f"opcode 0x{op:02X}")

    def test_every_row_carries_a_direction_and_an_operand_count(self):
        for op, _reg, direction, text, operands in S.RI_TABLE:
            self.assertIn(direction, ("read", "write", "rmw"), f"0x{op:02X}")
            self.assertIn(operands, (0, 1), f"0x{op:02X}")
            self.assertTrue(text.strip(), f"0x{op:02X}")

    def test_the_reserved_opcode_renders_without_a_substitution(self):
        # `0xA5`'s mnemonic in `intmem_refs.OPCODE_TABLE` names no address, so
        # it carries no `%02x` to fill. Dropping the row instead would drop a
        # pair the census is supposed to keep.
        self.assertEqual(S.direct_text(0xA5, 0x2F),
                         "reserved -- never an instruction")

    def test_a_direct_template_renders_with_the_address(self):
        self.assertEqual(S.direct_text(0xF5, 0x84), "mov  0x84,a")


class RefusalCases(unittest.TestCase):
    """The scans this tool declines, each with the reason it names.

    Every buffer below would yield a short, plausible table if its guard were
    removed -- which is the same thing as a table with one row missing and no
    sentence saying so.
    """

    def refuses(self, buffer, needle):
        with self.assertRaises(S.Refusal) as caught:
            S.load_sites(buffer)
            sites = S.ri_sites(buffer)
            S.pair_sites(sites, S.load_sites(buffer))
            for off, _op, _reg, _direction, _text, operands in sites:
                for n in range(operands):
                    S._operand(buffer, off, n + 1)
        self.assertIn(needle, str(caught.exception))

    def test_a_pointer_load_with_no_immediate_byte_is_refused(self):
        # `mov r0,#` at the end of the buffer. Whether it names a byte at all
        # cannot be read, so the load index stops rather than skipping it.
        self.refuses(LOAD_R0, "runs off the end")

    def test_a_site_whose_immediate_is_missing_is_refused(self):
        self.refuses(LOAD_R0 + bytes([0x84]) + STORE_IMM_R0,
                     "runs off the end")

    def test_a_site_whose_direct_operand_is_missing_is_refused(self):
        self.refuses(bytes([0xA6]), "runs off the end")

    def test_the_refusal_names_the_offset_it_stopped_at(self):
        with self.assertRaises(S.Refusal) as caught:
            S.load_sites(bytes([0x00, 0x00, 0x78]))
        self.assertIn("0x00002", str(caught.exception))


class CommittedImageCases(unittest.TestCase):
    """The pairing against the committed listings and image."""

    @classmethod
    def setUpClass(cls):
        cls.image = FIRMWARE.read_bytes()
        cls.sites = S.ri_sites(cls.image)
        cls.paired = S.pair_sites(cls.sites, S.load_sites(cls.image))

    def test_the_012F_listing_shows_the_pair_the_scan_finds(self):
        # A byte assertion, not the tool's arithmetic: `012F.asm` spells the
        # pair `mov R0,#0x84` / `mov @R0,#0x2`, and the scan's answer has to be
        # that pair rather than a rendering of its own.
        self.assertEqual(self.image[0x0162:0x0166],
                         bytes([0x78, 0x84, 0x76, 0x02]))
        self.assertEqual(self.paired[0x0164], (0x0162, 0x84))

    def test_the_0F75_listing_shows_the_site_the_scan_leaves_unresolved(self):
        # `0x0F75.asm` line `0x0F91  f6  mov @R0,A`, with `clr A` before it.
        # The clear is the reason the pairing cannot name the byte: R0 came from
        # the `xch a,R0` pair above, not from a load.
        self.assertEqual(self.image[0x0F90:0x0F92], bytes([0xE4, 0xF6]))
        self.assertNotIn(0x0F91, self.paired)
        self.assertIn(0x0F91, {site[0] for site in self.sites})

    def test_the_direct_table_still_finds_no_write_to_0x84(self):
        # The premise correction the tool rests on, in this scan's own negative
        # vocabulary: `intmem_refs` finds no write to 0x84 anywhere, and the
        # pairing is what recovers the ones `012F.asm` shows.
        direct = I.scan(self.image, [0x84], True).get(0x84, [])
        self.assertEqual([d for _o, _op, d, _f in direct
                          if d in ("write", "rmw")], [])
        self.assertIn(0x84, [addr for _load, addr in self.paired.values()])

    def test_the_committed_table_is_reproduced_byte_for_byte(self):
        out = subprocess.run([sys.executable, str(TOOL), "--csv", "--check"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("byte for byte", out.stdout)


class CommittedTableCases(unittest.TestCase):
    """`iram-boot-sites.csv`, read against the tree that produced it."""

    @classmethod
    def setUpClass(cls):
        with open(SITES_CSV, newline="") as handle:
            cls.rows = list(csv.DictReader(handle))

    def test_the_header_is_the_columns_the_tool_declares(self):
        with open(SITES_CSV, newline="") as handle:
            header = next(csv.reader(handle))
        self.assertEqual(header, S.CSV_COLUMNS)

    def test_every_row_carries_one_of_the_three_forms(self):
        self.assertEqual(sorted({r["form"] for r in self.rows}),
                         ["direct", "ri", "ri-unresolved"])

    def test_every_addressable_row_names_a_byte_in_the_boot_range(self):
        lo, hi = S.BOOT_IRAM
        for row in self.rows:
            if row["addr"] == S.UNRESOLVED:
                continue
            self.assertTrue(lo <= int(row["addr"], 16) <= hi, row["addr"])

    def test_an_unresolved_row_carries_no_address(self):
        for row in self.rows:
            if row["form"] == "ri-unresolved":
                self.assertEqual(row["addr"], S.UNRESOLVED)

    def test_the_frame_pair_accounts_for_every_anchor_the_scan_considered(self):
        # `converges_from` starts one walk per preceding byte and skips the ones
        # before the buffer, so the pair sums to the number of anchors that
        # existed -- 24 for a site that far in, fewer only near offset 0. A row
        # where it does not is a row whose framing was filled in by something
        # other than the scan.
        for row in self.rows:
            off = int(row["file_offset"], 16)
            self.assertEqual(int(row["frame_onto"]) + int(row["frame_over"]),
                             min(24, off), row["file_offset"])

    def test_the_chan_init_writes_the_issue_names_are_rows(self):
        # `012F.asm`'s three `chan_init` writes, read out of the committed
        # table: the two the direct form misses entirely (`0x84`, and `0xAA`'s
        # pair behind the `clr 0xaa` sites) and the `0x99` one beside them.
        by_addr = {}
        for row in self.rows:
            if row["form"] == "ri":
                by_addr.setdefault(row["addr"], []).append(row)
        self.assertIn("0x84", by_addr)
        self.assertIn("0xaa", by_addr)
        self.assertIn("0x00164", [r["file_offset"] for r in by_addr["0x84"]])
        self.assertIn("0x00180", [r["file_offset"] for r in by_addr["0xaa"]])


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

    def test_a_non_hex_address_is_refused(self):
        # The image comes first, as `intmem_refs.py`'s own command line takes
        # it, so the address is the second positional.
        out = self.run_tool(str(FIRMWARE), "0xZZ")
        self.assertEqual(out.returncode, 1)
        self.assertIn("not a hex address", out.stderr)

    def test_an_out_of_range_address_is_refused(self):
        out = self.run_tool(str(FIRMWARE), "0x1FF")
        self.assertEqual(out.returncode, 1)
        self.assertIn("not a direct byte address", out.stderr)

    def test_a_missing_image_is_a_named_failure_not_a_traceback(self):
        out = self.run_tool("/nonexistent/image.bin")
        self.assertEqual(out.returncode, 1)
        self.assertIn("note:", out.stderr)
        self.assertNotIn("Traceback", out.stderr)

    def test_the_per_address_report_prints_the_sites_it_found(self):
        out = self.run_tool(str(FIRMWARE), "0x84")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("refs=", out.stdout)
        self.assertIn("NOT FOUND BY THIS METHOD", out.stdout)


if __name__ == '__main__':
    unittest.main()