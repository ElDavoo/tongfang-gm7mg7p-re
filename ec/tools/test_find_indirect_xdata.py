#!/usr/bin/env python3
"""The refusals and the resolution contract of `find_indirect_xdata.py`, on
its own.

Every case builds its own buffer through the local `fixture()` helper rather
than pointing at the firmware, for the reason
`test_trace_xdata_refs.py` gives: a case that pointed at the image would keep
testing the same bytes only until the bytes around some address in it
changed, and this tool's whole population is "an opcode byte somewhere", so
a fixture that *is* the image would be testing the image.

The one class that does read the committed image is
`CommittedTableTests`, and it is the one that has to: `--check` reproducing
`../annotations/indirect-xdata-sites.csv` byte for byte is what makes the
annotation's counts an assertion rather than a claim, and a test that only
ever fed the tool a fixture could not tell whether that table is still
current.

The encoding list in `P2WriterTests` is transcribed from sdas8051's own
listing rather than generated from the tool's table, which is the point of
the class: a mistyped opcode range in `P2_WRITERS` would make a generated
list agree with it, and the table's own names would be the only evidence for
the table.
"""
import contextlib
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# find_indirect_xdata imports disasm8051 and trace_xdata_refs by bare module
# name, the way register_ref_table.py does, so the tool directory has to be
# on the path before it is loaded rather than after.
sys.path.insert(0, str(HERE))
import find_indirect_xdata as F        # noqa: E402
import trace_xdata_refs as T           # noqa: E402

FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"
COMMITTED_CSV = REPO / "ec" / "annotations" / "indirect-xdata-sites.csv"

# The four indirect forms, by the register whose low byte they take.
MOVX_R0 = bytes([0xE2])                # movx a,@r0
MOVX_R1 = bytes([0xE3])                # movx a,@r1
MOVX_W0 = bytes([0xF2])                # movx @r0,a
MOVX_W1 = bytes([0xF3])                # movx @r1,a


def p2(v: int) -> bytes:
    return bytes([0x75, 0xA0, v])      # mov p2,#v -- the only literal P2 write


def r0(v: int) -> bytes:
    return bytes([0x78, v])            # mov r0,#v


def r1(v: int) -> bytes:
    return bytes([0x79, v])            # mov r1,#v


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_trace_xdata_refs.py` and `test_walk_budget_census.py`
    each carry a copy of, and for the same reason. The tail past the last
    instruction is filled with `0x00`, which is the opcode table's 1-byte
    `nop`, so a walk over it is a run of nops rather than a decode of
    whatever byte happened to be there -- which is what lets a case's site
    offset be the offset the fixture laid the site down at."""
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def one_site(img: bytes, pd_verified: bool = False, back: int = F.WINDOW) -> dict:
    """The single site `sites()` finds, or a failure naming what it found.

    Every resolution case wants exactly one site, and a case that quietly got
    two would go on to assert about the first of them -- which is the way a
    fixture stops being evidence for what its name claims."""
    rows = F.sites(img, pd_verified, back)
    if len(rows) != 1:
        raise AssertionError(f"fixture holds {len(rows)} site(s) at "
                             f"{[r['offset'] for r in rows]}, not 1")
    return rows[0]


def capture(fn, *args) -> (str, int):
    """(what `fn` printed, what it returned), for the report modes.

    `page_report()` writes its answer and returns an exit code, and the exit
    code is half of what the issue asked for: a page the main EC does not
    reach has to be a non-zero run, not a sentence nobody reads."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*args)
    return buf.getvalue(), rc


class AnchoredTests(unittest.TestCase):
    """The distinction the tool's first paragraph is about: a `0xE2` that is
    somebody's immediate is not a site, and a raw byte scan cannot tell."""

    # `mov dptr,#0x07E2` is three bytes whose third is 0xE2 -- an immediate
    # that happens to be an indirect-XDATA opcode. A `nop` between it and the
    # real site would hide the collision, so there is none.
    IMG = fixture(bytes([0x90, 0x07, 0xE2]), MOVX_R0)

    def test_the_operand_byte_is_not_a_site(self):
        self.assertEqual([r["offset"] for r in F.sites(self.IMG, False)], [3])
        # And the raw pass finds both, which is the 8x the summary prints.
        self.assertEqual(F.raw_sites(self.IMG), [2, 3])

    def test_both_passes_report_their_own_count(self):
        # The raw count is what a byte scan would have found and the anchored
        # count is the population; a tool that filtered silently would leave
        # only one visible and the gap would read as agreement rather than as
        # an 8x over-count.
        self.assertEqual(len(F.raw_sites(self.IMG)), 2)
        self.assertEqual(len(F.sites(self.IMG, False)), 1)

    def test_all_four_forms_are_sites_and_each_names_its_register(self):
        # One at a time, because a case that laid all four down would not say
        # which of them was mis-decoded. `movx a,@r1` and `movx @r0,a` take
        # different low bytes off the same page, so a tool that lost the
        # register would resolve the wrong address.
        for form, reg, op in ((MOVX_R0, 0, "movx a,@r0"),
                              (MOVX_R1, 1, "movx a,@r1"),
                              (MOVX_W0, 0, "movx @r0,a"),
                              (MOVX_W1, 1, "movx @r1,a")):
            with self.subTest(form=form.hex()):
                site = one_site(fixture(form))
                self.assertEqual(site["form"], op)
                self.assertEqual(site["register"], reg)


class P2WriterTests(unittest.TestCase):
    """Every encoding that writes 0xA0-0xA7, and nothing that does not.

    The left column is transcribed from `sdas8051 -plosgff`, the assembler
    `verify_reassembly.py` re-encodes every committed listing with and the one
    this repository already treats as an independent oracle:

        printf '\\t.area CODE (ABS)\\n\\tmov p2,#0x07\\n\\torl p2,#0x0f\\n...\\n' > p.s
        sdas8051 -plosgff p.rel p.s

    `clr p2.x` (0xC1) is the one row sdas8051 will not produce: it assembles
    the bit form as `clr direct` (0xC2) without failing, which is the defect
    `verify_reassembly.BIT_UNSUPPORTED` exists to name, so that row comes from
    the manual and that table instead.
    """

    # (encoding, the name this file gives it, the literal it supplies or None)
    WRITERS = [
        (b"\x75\xa0\x07", "mov p2,#imm", 0x07),
        (b"\x85\x90\xa0", "mov p2,direct", None),
        (b"\xc5\xa0", "xch a,p2", None),
        (b"\x86\xa0", "mov p2,@ri", None),
        (b"\x87\xa0", "mov p2,@ri", None),
        (b"\x88\xa0", "mov p2,register", None),
        (b"\x8a\xa0", "mov p2,register", None),
        (b"\x8f\xa0", "mov p2,register", None),
        (b"\xf5\xa0", "mov p2,acc", None),
        (b"\x05\xa0", "inc p2", None),
        (b"\x15\xa0", "dec p2", None),
        (b"\xd0\xa0", "pop p2", None),
        (b"\xd5\xa0\x00", "djnz p2", None),
        (b"\x42\xa0", "orl p2,#imm-or-a", None),
        (b"\x43\xa0\x0f", "orl p2,#imm-or-a", None),
        (b"\x52\xa0", "anl p2,#imm-or-a", None),
        (b"\x53\xa0\x0f", "anl p2,#imm-or-a", None),
        (b"\x62\xa0", "xrl p2,#imm-or-a", None),
        (b"\x63\xa0\x0f", "xrl p2,#imm-or-a", None),
        (b"\x10\xa0\x00", "jbc p2.x", None),
        (b"\x92\xa0", "mov p2.x,carry", None),
        (b"\xb2\xa1", "cpl p2.x", None),
        (b"\xc1\xa0", "clr p2.x", None),
        (b"\xc2\xa0", "clr p2", None),
        (b"\xd2\xa3", "setb p2.x", None),
    ]

    def test_every_transcribed_encoding_is_named(self):
        for raw, name, literal in self.WRITERS:
            with self.subTest(encoding=raw.hex()):
                got = F.p2_write(raw + b"\x00" * 4, 0)
                self.assertIsNotNone(got, f"{raw.hex()} is not recognised")
                self.assertEqual(got, (name, literal))

    def test_the_table_holds_no_row_the_transcript_does_not(self):
        # The other direction, and the half that matters: a row in
        # P2_WRITERS no transcribed encoding reaches is a claim no case is
        # holding, and it is exactly what over-eager widening of the table
        # would add.
        covered = {raw[0] for raw, _n, _l in self.WRITERS}
        for lo, hi, _at, name, _lit in F.P2_WRITERS:
            with self.subTest(row=name):
                self.assertTrue(covered & set(range(lo, hi + 1)),
                                f"{name} ({lo:#04x}-{hi:#04x}) has no "
                                "transcribed encoding in this suite")

    def test_a_byte_in_range_that_is_not_an_address_is_not_a_write(self):
        # The over-count the table has to refuse. `mov dptr,#0xA007` holds
        # 0xA0 as an immediate, `mov 0x07,#0xA0` holds it as the immediate of
        # a write to a *different* direct, and `mov 0x07,0xA0` holds it as
        # the source of a write to a different direct. A table keyed on the
        # byte's value rather than on the operand's position would take all
        # three for a P2 write and resolve a page from a `P2` nobody touched.
        for raw in (b"\x90\xa0\x07", b"\x75\x07\xa0", b"\x85\xa0\x07",
                    b"\x92\x07", b"\x88\x90", b"\x05\x90", b"\xc2\x90"):
            with self.subTest(encoding=raw.hex()):
                self.assertIsNone(F.p2_write(raw + b"\x00" * 4, 0))

    def test_a_branch_displacement_in_range_is_not_an_address(self):
        # The collision that cost this table a revision. 0x40 is `jc rel`
        # and 0x42 is `orl direct,A`, so a range spanning 0x40-0x43 reads
        # every `jc` whose target byte lands in 0xA0-0xA7 as a write to P2 --
        # and P2 is exactly the page an indirect `movx @Ri` reads, so the
        # false positive lands on the very sites the tool exists to explain.
        # The four branch opcodes are the ones that own the low byte of their
        # decade; 0x70 is `jnz` and 0x72 is the short `jbc`, neither of which
        # is a P2 writer, so neither may be caught by a wide range either.
        for op, name in ((0x40, "jc"), (0x50, "jnc"), (0x60, "jz"), (0x70, "jnz")):
            with self.subTest(opcode=op):
                self.assertIsNone(F.p2_write(bytes([op, 0xA2, 0x00]), 0))
                # And the mnemonic on the same bytes says branch, so a table
                # and the decoder cannot both be right if one of them is.
                self.assertTrue(F.mnemonic(bytes([op, 0xA2, 0x00]), 0)
                                .startswith(name))
        # The three logic forms that *are* P2 writers still work, one byte
        # up from the branch -- which is the whole of the distinction.
        for op in (0x42, 0x52, 0x62):
            with self.subTest(opcode=op):
                self.assertIsNotNone(
                    F.p2_write(bytes([op, 0xA0]) + b"\x00" * 4, 0))

    def test_mov_direct_direct_takes_the_destination_from_the_third_byte(self):
        # The row `verify_reassembly.DIRECT_OPERANDS`'s comment works through:
        # `85 F0 00` is `mov 0x00,0xF0` and not `mov 0xF0,0x00`, so a table
        # reading the address from byte 1 would call the second of these a
        # write to P1 and miss the first.
        self.assertEqual(F.p2_write(b"\x85\x90\xa0" + b"\x00" * 4, 0),
                         ("mov p2,direct", None))
        self.assertIsNone(F.p2_write(b"\x85\xa0\x90" + b"\x00" * 4, 0))


class ResolutionTests(unittest.TestCase):
    """Both halves literal, one of them, neither, and the cell each gives.

    The `unresolved` cell is the tool's refusal, and these are the cases that
    hold it to naming the half rather than saying "unresolved" and leaving a
    reader to work out which."""

    def test_both_halves_literal_resolves_to_the_full_address(self):
        site = one_site(fixture(p2(0x07), r0(0xB9), MOVX_R0))
        self.assertEqual(site["xaddr"], "0x07B9")
        self.assertEqual(site["p2"], ("mov p2,#imm", 0x07))
        self.assertEqual(site["rn"], 0xB9)

    def test_the_register_belongs_to_the_site_not_to_the_window(self):
        # `movx a,@r1` with only r0 loaded resolves to nothing: the literal
        # load is for the other register, and a tool that took any Rn literal
        # out of the window would compose a page and a low byte that never
        # met. This is the case the issue's "`mov r0,#imm` / `mov r1,#imm`"
        # wording is about, and r1 is spelled out because the window holds a
        # load that would satisfy a looser rule.
        site = one_site(fixture(p2(0x07), r0(0xB9), MOVX_R1))
        self.assertIn("Rn: no `mov r1,#imm` in the window", site["xaddr"])
        self.assertIsNone(site["rn"])
        # And the mirror: r1 loaded for an r0 site does not rescue it either.
        self.assertIn("Rn: no `mov r0,#imm` in the window",
                      one_site(fixture(p2(0x07), r1(0xB9), MOVX_R0))["xaddr"])
        # The positive case for r1, so the two are a pair rather than a
        # refusal that would also be the answer for a site it should resolve.
        self.assertEqual(one_site(fixture(p2(0x07), r1(0xB9), MOVX_R1))["xaddr"],
                         "0x07B9")

    def test_one_literal_half_and_the_token_says_which_is_missing(self):
        page_only = one_site(fixture(p2(0x07), MOVX_R0))
        self.assertIn("P2: literal 0x07", page_only["xaddr"])
        self.assertIn("Rn: no `mov r0,#imm` in the window", page_only["xaddr"])
        low_only = one_site(fixture(r0(0xB9), MOVX_R0))
        self.assertIn(F.NO_P2_WRITER, low_only["xaddr"])
        self.assertIn("Rn: literal 0xB9", low_only["xaddr"])
        # The three buckets, cut on the page half. The third is unreachable
        # from a resolved site and is named anyway so a bucket that reads 0
        # is a measurement rather than a gap in the vocabulary.
        self.assertEqual(F.unresolved_by(low_only), F.NO_P2_WRITER)
        self.assertEqual(F.unresolved_by(page_only),
                         "P2 half literal, Rn half not found")
        self.assertEqual(F.unresolved_by(one_site(fixture(MOVX_R0))),
                         F.NO_P2_WRITER)
        self.assertEqual(F.unresolved_by(
            one_site(fixture(b"\xf5\xa0", MOVX_R0))),
            "P2 window's last write is `mov p2,acc`")

    def test_a_non_literal_p2_write_names_the_encoding_that_defeated_it(self):
        # `mov p2,a` overwrites the page with the accumulator, so a window
        # ending in it holds no page this tool can name. The cell says which
        # encoding it was, because an "unresolved" with no reason is a verdict
        # on the byte rather than a limit on the method.
        site = one_site(fixture(p2(0x07), r0(0xB9), b"\xf5\xa0", MOVX_R0))
        self.assertIn("P2: last write is `mov p2,acc`", site["xaddr"])
        self.assertNotIn("0x07B9", site["xaddr"])

    def test_the_last_p2_write_wins(self):
        # Two writes in the window: the later one is the one in force at the
        # site. Taking the earlier one would resolve a page the instruction
        # immediately before the site had already replaced -- which is the
        # whole reason the window records writers rather than searching for
        # the literal.
        overwritten = one_site(fixture(p2(0x07), r0(0xB9), p2(0x04), MOVX_R0))
        self.assertEqual(overwritten["xaddr"], "0x04B9")
        self.assertEqual(
            one_site(fixture(p2(0x04), p2(0x07), r0(0xB9), MOVX_R0))["xaddr"],
            "0x07B9")


class WindowTests(unittest.TestCase):
    """Why a window stopped, and that a wider one finds more.

    The two guards are different claims -- "the look stopped at 24 bytes" and
    "the look stopped because the region ran out" -- and a cell that reported
    one for the other would misstate every site in the first 24 bytes of
    `common`."""

    @staticmethod
    def far_apart() -> bytes:
        """Both loads at offset 0, the site 48 bytes later. `0x00` between
        them is a `nop`, so the decode behind the site is contiguous and the
        only thing the distance changes is how much of it the window reaches."""
        img = bytearray(b"\x00" * 0x40)
        img[0:5] = p2(0x07) + r0(0xB9)
        img[0x30:0x31] = MOVX_R0
        return bytes(img)

    def test_a_window_that_ran_out_says_so_rather_than_guessing(self):
        site = one_site(self.far_apart())
        self.assertEqual(site["offset"], 0x30)
        self.assertTrue(site["xaddr"].startswith("unresolved"))
        self.assertIn(F.NO_P2_WRITER, site["xaddr"])
        self.assertIn(F.window_end(F.WINDOW), site["xaddr"])
        self.assertNotIn(F.REGION_START, site["xaddr"])

    def test_a_wider_window_finds_what_the_narrow_one_could_not(self):
        # The same bytes and the same site, so the difference is the budget
        # and nothing else. Without this, the case above would pass on a tool
        # that never looked back at all.
        wider = one_site(self.far_apart(), back=48)
        self.assertEqual(wider["xaddr"], "0x07B9")

    def test_a_window_that_reached_the_region_start_says_that_instead(self):
        # A site with nothing behind it at all: the walk stopped because the
        # region did, which is a different claim from "the look stopped at 24
        # bytes", and a cell that reported one for the other would misstate
        # every site in the first 24 bytes of `common`.
        site = one_site(fixture(MOVX_R0))
        self.assertIn(F.REGION_START, site["xaddr"])
        self.assertNotIn(F.window_end(F.WINDOW), site["xaddr"])
        # A resolved cell carries no reason at all, because nothing stopped
        # the look short of finding both halves.
        self.assertNotIn(F.REGION_START,
                         one_site(fixture(p2(0x07), r0(0xB9), MOVX_R0))["xaddr"])

    def test_the_window_token_carries_the_budget_that_ran_out(self):
        # `trace_xdata_refs.budget_end()`'s reason for making the budget part
        # of the token: a reader looking at "window exhausted (24 bytes)" has
        # to be able to see which 24 produced it.
        self.assertEqual(F.window_end(24), "window exhausted (24 bytes)")
        self.assertNotEqual(F.window_end(24), F.window_end(48))

    def test_the_window_column_is_the_decode_it_resolved_against(self):
        # The evidence has to be on the row, or a reader takes the `xaddr`
        # cell on trust. Asserted against `window_before()` rather than
        # against a spelling: the mnemonic text is disasm8051.py's subject
        # and a case coupled to its wording would go red for a change that is
        # not a resolution defect.
        img = fixture(p2(0x07), r0(0xB9), MOVX_R0)
        site = one_site(img)
        behind, _why = F.window_before(img, F.anchored_starts(img, 0, len(img)), 5)
        self.assertEqual(
            site["window"],
            " ; ".join(" ".join(F.mnemonic(img, at).split()) for at in behind))


class RegionSplitTests(unittest.TestCase):
    """The main EC and the PD image, never added together.

    `lightbar-bat-flow.md` §2's mistake, and the invariant the summary's
    two-total printout exists to hold."""

    @staticmethod
    def image_with(*offsets, page: int = 0x07, low: int = 0xB9) -> bytes:
        """A buffer holding one resolvable `page:low` site at each offset.

        Zero-filled elsewhere, which the opcode table reads as a run of
        1-byte `nop`s, so each site is an anchored start and nothing else in
        a 192 KiB buffer is one. The buffer stops at 0x30000, the end of the
        PD region, rather than being padded further: a size the walk cannot
        reach would hide a bounds defect instead of being irrelevant to it.
        `page`/`low` are arguments so a case can ask about a page no site in
        the buffer is on.
        """
        img = bytearray(b"\x00" * 0x30000)
        for at in offsets:
            img[at:at + 6] = p2(page) + r0(low) + MOVX_R0
        return bytes(img)

    def test_the_two_images_are_counted_apart(self):
        rows = F.sites(self.image_with(0x0100, 0x20020), pd_verified=True)
        self.assertEqual([r["region"] for r in rows], ["common", "pd-image"])
        # The runtime address is the region's own base plus the offset into
        # it, and the offset is that of the `movx` itself -- the fifth byte of
        # the six-byte sequence -- so the PD image's site is not the main EC's
        # 0x20020 and the table cannot be read as though it were.
        self.assertEqual([r["offset"] for r in rows], [0x0105, 0x20025])
        self.assertEqual([r["runtime"] for r in rows], [0x0105, 0x0025])
        self.assertNotIn(F.PD_REGION, F.MAIN_EC_REGIONS)
        self.assertEqual(sum(1 for r in rows
                             if r["region"] in F.MAIN_EC_REGIONS), 1)

    def test_a_buffer_without_the_marker_reports_unknown_not_pd_image(self):
        # `region_of()`'s refusal, reached through this tool's own output. A
        # dump that is not this one has to get `unknown` rather than inherit
        # the PD image's conclusion from the offset alone.
        rows = F.sites(self.image_with(0x0100, 0x20020), pd_verified=False)
        self.assertEqual([r["region"] for r in rows], ["common", "unknown"])
        self.assertEqual(len(rows), 2)

    def test_the_page_report_names_the_image_each_hit_is_in(self):
        # The issue asks whether the **main EC image** reaches page 0x07, so
        # the answer is per image and the exit code is about the main EC
        # alone.
        out, rc = capture(F.page_report,
                          F.sites(self.image_with(0x0100, 0x20020), True), 0x07)
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("0x07B9"), 2)
        self.assertIn("common", out)
        self.assertIn("pd-image", out)

    def test_a_page_only_the_pd_image_reaches_exits_non_zero(self):
        # And the refusal: a PD hit is not an EC-side reference to a 0x07xx
        # byte, so the main EC's half of the answer has to be a non-zero run
        # even though the page is not empty.
        out, rc = capture(F.page_report,
                          F.sites(self.image_with(0x20020), True), 0x07)
        self.assertEqual(rc, 1)
        self.assertIn("the main EC reaches page 0x07 by this method nowhere",
                      out)
        self.assertIn("0x07B9", out)

    def test_a_page_nothing_reaches_exits_non_zero_with_no_hits(self):
        # The main EC's only site is resolvable and is on another page, so
        # "page 0x07" is empty and the count is the whole of the answer.
        out, rc = capture(F.page_report,
                          F.sites(self.image_with(0x0100, page=0x04), True), 0x07)
        self.assertEqual(rc, 1)
        self.assertIn("not reached by any resolvable site", out)
        self.assertNotIn("0x07B9", out)


class CsvTests(unittest.TestCase):
    """The table's cells, through the csv module rather than by eye."""

    def test_the_row_carries_the_evidence_the_cell_is_built_from(self):
        img = fixture(p2(0x07), r0(0xB9), MOVX_R0)
        table = F.csv_table(F.sites(img, False))
        row = next(csv.DictReader(io.StringIO(table)))
        self.assertEqual(row["file_offset"], "0x00005")
        self.assertEqual(row["region"], "common")
        self.assertEqual(row["runtime"], "0x0005")
        self.assertEqual(row["form"], "movx a,@r0")
        self.assertEqual(row["p2"], "mov p2,#imm = 0x07")
        self.assertEqual(row["rn"], "literal 0xB9")
        self.assertEqual(row["xaddr"], "0x07B9")
        # The framing evidence is disasm8051's, and both halves of it are
        # here because either alone settles nothing -- the pair is the claim.
        onto, over = T.converges_from(img, 5)
        self.assertEqual((int(row["frame_onto"]), int(row["frame_over"])),
                         (onto, over))

    def test_an_unresolved_row_says_which_half_in_the_p2_and_rn_cells(self):
        table = F.csv_table(F.sites(fixture(b"\xf5\xa0", r0(0xB9), MOVX_R0), False))
        row = next(csv.DictReader(io.StringIO(table)))
        self.assertEqual(row["p2"], "mov p2,acc")
        self.assertEqual(row["rn"], "literal 0xB9")
        self.assertIn("unresolved", row["xaddr"])


class CommittedTableTests(unittest.TestCase):
    """`--check` against the committed image and the committed CSV.

    The one class that reads the firmware, because the claim it holds is the
    one nothing else here can: that
    `../annotations/indirect-xdata-sites.csv` is what this tool prints for
    `../firmware/GMxMGxx_11.800` today, so the annotation's counts are an
    assertion with a re-run behind it and not a paragraph."""

    def test_the_committed_table_is_what_this_run_produces(self):
        out = subprocess.run(
            [sys.executable, str(HERE / "find_indirect_xdata.py"),
             str(FIRMWARE), "--check", str(COMMITTED_CSV)],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)

    def test_the_check_is_red_against_a_table_that_is_not_this_runs(self):
        # A `--check` that is green because it never compares anything is
        # worse than no check, so the refusal is pinned: one byte of filler
        # the tool could not have produced has to turn it red.
        with tempfile.TemporaryDirectory() as tmp:
            edited = os.path.join(tmp, "edited.csv")
            with open(COMMITTED_CSV, newline="") as f:
                text = f.read()
            with open(edited, "w", newline="") as f:
                f.write(text.replace("common", "comm0n", 1))
            out = subprocess.run(
                [sys.executable, str(HERE / "find_indirect_xdata.py"),
                 str(FIRMWARE), "--check", edited],
                capture_output=True, text=True, cwd=REPO)
        self.assertEqual(out.returncode, 1)
        self.assertIn("differs from what this run produced", out.stderr)


if __name__ == "__main__":
    unittest.main()
