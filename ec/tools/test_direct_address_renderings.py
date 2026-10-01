#!/usr/bin/env python3
"""The six `direct`-destination renderings, and the negatives that hold them in place.

`disasm8051.py --self-test` holds the opcode and mnemonic tables against hand
transcriptions, and it had no case for `0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63`
-- so all six fell through to `db`, and four committed annotation tables inherited
that. `--self-test` is the wrong home for the follow-up: it reads the firmware
image and two transcribed `.md` windows, and these six are settled by the
committed Ghidra listings, so they get a file of their own with the oracle beside
them. The write-up is
`../../docs/findings/direct-address-opcode-rendering.md`; its first table is the
six.

Four questions, kept apart because they fail for different reasons. **What the
renderings are**, taken from the committed Ghidra listings rather than from the
decoder: `42 f0` is `orl 0xf0,a` because `ec/decompiled/common/70FA.asm` spells it
`orl B, A`, and an expectation derived from the code under test would agree with it
whatever it were. **What the lengths are**, held at 2/3/2/3/2/3 so a later branch
cannot quietly take the three-byte reading of the accumulator rows and re-frame
every window containing one -- a real disagreement, recorded rather than settled,
and one `opcode_coverage.py --divergence` cannot see, because its `MCS51_LEN`
carries the same reading on all twelve. **What must not move**: the accumulator
rows either side of the group, the four branch opcodes the six sit one byte above,
and the map-unassigned bytes `citation_gap_scan.UNASSIGNED` grades a window's
`not-code` verdict on. And **what the four committed tables say**, which is where
the defect actually showed up, since `db` is the token this repository reads as
*data, not code*.

That last class is a check on the claim, not a census. Nothing here counts rows or
cells: a number every landing suite has to edit is the mistake this repository has
already made four times over, and the write-up carries the figures as prose with
the command that re-derives them.
"""
import csv
import importlib.util
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "ec" / "tools"))


def _load(name):
    """Load a sibling tool by file location, as the other suites in ec/tools do."""
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("disasm8051")

# (path, line, runtime address, bytes, this module's rendering, the listing's own).
# Every row is transcribed from the committed listing named beside it, which is
# the discipline `disasm8051.BIT_SITES` and `TEXTBOOK_BIT_SITES` record: an
# encoding derived from the tool under test asserts nothing. The listing's text is
# carried as well so a row that rots in the `.asm` is caught rather than quietly
# becoming an expectation the decoder merely agrees with.
LISTING_ORACLE = (
    ("ec/decompiled/common/70FA.asm", 12, "7100", b"\x42\xf0",
     "orl  0xf0,a", "orl      B, A"),
    ("ec/decompiled/common/22EF.asm", 65, "2357", b"\x62\x66",
     "xrl  0x66,a", "xrl      0x66, A"),
    ("ec/decompiled/common/2632.asm", 43, "2667", b"\x52\x66",
     "anl  0x66,a", "anl      0x66, A"),
    ("ec/decompiled/common/2632.asm", 54, "2680", b"\x63\x65\xff",
     "xrl  0x65,#0xff", "xrl      0x65, #0xff"),
    ("ec/decompiled/common/5802.asm", 56, "5857", b"\x43\x45\x47",
     "orl  0x45,#0x47", "orl      0x45, #0x47"),
    ("ec/decompiled/bank1/897B.asm", 21, "8995", b"\x53\x00\x07",
     "anl  0x00,#0x07", "anl      0x00, #0x7"),
)

# The four committed tables the renderer feeds, and the one column in each that
# holds a decode. `bank-call-targets.csv`, `bank-relative-branch-targets.csv` and
# `bank-paged-call-targets.csv` put a single earlier instruction in
# `earlier_record`; `indirect-xdata-sites.csv` puts up to 24 in `window`, which is
# why a token count and a cell count over the four are not the same number.
CORPUS_TABLES = (
    ("bank-call-targets.csv", "earlier_record"),
    ("bank-relative-branch-targets.csv", "earlier_record"),
    ("bank-paged-call-targets.csv", "earlier_record"),
    ("indirect-xdata-sites.csv", "window"),
)

# The text the four tables used to carry, and which this decoder can no longer
# produce for these six opcodes at all. `\s+` rather than one literal space,
# because the four do not agree on spacing: the three site tables carry
# `mnemonic()`'s own column-padded `db   0x42`, while `find_indirect_xdata.py`
# re-spaces its `window` cells with `" ".join(mnemonic(...).split())`, which
# arrives as `db 0x42`. A single-space pattern matches one of the two and so
# passes vacuously over the other three.
SIX_AS_DATA = re.compile(r"\bdb\s+0x(?:42|43|52|53|62|63)\b")

# `<runtime>  <bytes...>  <mnemonic>` in the three site tables. Asserted on a
# sample because its whole job is to catch a column that has stopped being a
# decode, and a shape check over a whole table would only be slower.
DECODE_SHAPE = re.compile(r"^0x[0-9A-Fa-f]+ ((?:[0-9a-f]{2} )+[0-9a-f]{2}) \S")


class DirectDestinationRenderings(unittest.TestCase):
    """The six, as the committed listings transcribe them."""

    def test_each_rendering_against_its_transcribed_listing(self):
        for path, line, addr, raw, want, listing_text in LISTING_ORACLE:
            with self.subTest(f"{path}:{line} 0x{addr}"):
                source = (REPO / path).read_text(encoding="utf-8").splitlines()
                # Both halves asserted against the committed file: the bytes the
                # expectation was transcribed from, and the listing text it was
                # transcribed out of. A row that rots in the `.asm` then fails
                # here rather than becoming an expectation the decoder happens to
                # satisfy.
                self.assertTrue(
                    source[line - 1].startswith(f"{addr}     {raw.hex(' ')}"),
                    f"{path}:{line} reads {source[line - 1]!r}, not the "
                    f"transcribed `{addr}     {raw.hex(' ')}`")
                self.assertIn(listing_text, source[line - 1])
                self.assertEqual(D.mnemonic(raw, 0), want)

    def test_the_listings_sfr_naming_and_the_rendered_address_are_one_operand(self):
        # `orl B, A` and `orl 0xf0,a` are one instruction, and the only thing
        # between them is whether the renderer names the SFR. Asserted as an
        # equality of the *byte*, which is the claim, rather than of the literal
        # `B` -- a suite expecting the letter would be asserting Ghidra's naming
        # convention rather than the encoding, and this decoder names SFRs as
        # addresses elsewhere too (`clr 0xd0`, `mov c,acc.0`, `anl 0x82,a`), so a
        # literal expectation would be asserting an inconsistency with itself.
        # `BIT_SFR` is the module's own table, so the two names are reconciled by
        # the thing that has to agree with itself either way.
        _path, _line, _addr, raw, want, listing_text = LISTING_ORACLE[0]
        listed = listing_text.split()[1].split(",")[0]     # `B` in `orl      B, A`
        operand = want.split()[1].split(",")[0]            # the renderer's `0xf0`
        self.assertEqual(D.BIT_SFR[int(operand[2:], 16)], listed.lower())
        self.assertEqual(D.mnemonic(raw, 0), want)

    def test_a_direct_operand_is_written_the_way_clr_direct_writes_its(self):
        # The house style for a byte-addressed destination, `clr 0x7f` at `0xC2`
        # being the precedent these follow. The claim is that the two write their
        # operand the same *way* -- a bare `0x%02x` address, no SFR name -- so
        # both operands are checked against one shape rather than against a second
        # copy of the same literal: the byte differs case to case, and only the
        # spelling is the point.
        shape = r"0x[0-9a-f]{2}"
        self.assertRegex(D.mnemonic(b"\xc2\x7f", 0), rf"^clr {{2}}{shape}$")
        for op, operand, name in ((0x42, 0xF0, "orl"), (0x52, 0x82, "anl"),
                                  (0x62, 0x00, "xrl")):
            with self.subTest(op=f"0x{op:02x}"):
                got = D.mnemonic(bytes([op, operand]), 0)
                self.assertRegex(got, rf"^{name} {{2}}{shape},a$")
                self.assertEqual(got, f"{name}  0x{operand:02x},a")


class Lengths(unittest.TestCase):
    """`OPCODE_LEN` is not widened here, and the reason is on the page.

    The Intel manual's opcode table admits a three-byte `direct,#data` reading of
    `0x25`/`0x35`/`0x45`/`0x55`/`0x65`/`0x95` that every assembler and compiler
    emits as the two-byte `a,direct` form. That disagreement is recorded in
    `disasm8051.py` beside the 0xA0/0xB0 comment and is not settled here. What is
    held is that this change did not quietly take a side on it, on either half.
    """

    def test_the_six_keep_their_mapped_lengths(self):
        for op, want in ((0x42, 2), (0x43, 3), (0x52, 2),
                          (0x53, 3), (0x62, 2), (0x63, 3)):
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(D.OPCODE_LEN[op], want)

    def test_the_accumulator_half_stays_two_bytes_too(self):
        # The same disagreement on the other side of the group. A later branch
        # taking the three-byte reading here would re-frame every window holding
        # one, and `--divergence` would not see it -- `MCS51_LEN` carries the same
        # two-byte reading, so the two oracles agree with each other for the same
        # reason and the comparison is blind to the row. That is the boundary with
        # #1155, and it is why this is an assertion rather than a comment.
        for op in (0x25, 0x35, 0x45, 0x55, 0x65, 0x95):
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(D.OPCODE_LEN[op], 2)

    def test_a_walk_survives_a_window_of_all_six(self):
        # The lengths are what keep a walk in place, so drive the walk rather than
        # only reading the table: each instruction starts where the previous one
        # ended, which is the property a wrong length would break first.
        window = (b"\x42\xf0" + b"\x52\x82" + b"\x62\x00"
                  + b"\x43\x45\x47" + b"\x53\x82\x7f" + b"\x63\x82\x2b")
        got = list(D.decode(window, 0, 6, 0))
        self.assertEqual([i for i, _r, _t in got], [0, 2, 4, 6, 9, 12])
        self.assertEqual([t for _i, _r, t in got],
                         ["orl  0xf0,a", "anl  0x82,a", "xrl  0x00,a",
                          "orl  0x45,#0x47", "anl  0x82,#0x7f", "xrl  0x82,#0x2b"])


class NegativesHeld(unittest.TestCase):
    """What the growth must not have swallowed.

    The six sit one byte above the branch opcodes, so a decoder that widened a row
    the wrong way would read `jc`/`jnc`/`jz`/`jnz` as data -- a worse failure than
    the one this change fixes, and one no committed listing would catch if it
    landed in a window nobody has quoted.
    """

    def test_the_four_branches_below_the_six_still_branch(self):
        for op, name in ((0x40, "jc"), (0x50, "jnc"), (0x60, "jz"), (0x70, "jnz")):
            with self.subTest(op=f"0x{op:02x}"):
                got = D.mnemonic(bytes([op, 0x10]), 0)
                self.assertTrue(got.startswith(name), got)
                self.assertEqual(D.OPCODE_LEN[op], 2)

    def test_the_accumulator_rows_still_name_the_accumulator(self):
        # The four-way group `0x52`/`0x53`/`0x54`/`0x55` is the one §1 of
        # `dptr-rebuild-walk-guard.md` first described wrongly, and its correction
        # is only worth anything while these stay as they are: `0x54` is
        # `anl a,#data`, two bytes, masking A rather than writing DPL. The wrong
        # account is left visible there; this is what makes it visibly wrong
        # rather than merely retracted.
        for op, want in ((0x54, "anl  a,#0x82"), (0x44, "orl  a,#0x82"),
                         (0x64, "xrl  a,#0x82"), (0x74, "mov  a,#0x82")):
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(D.mnemonic(bytes([op, 0x82]), 0), want)
                self.assertEqual(D.OPCODE_LEN[op], 2)
        for op, want in ((0x55, "anl  a,0x82"), (0x45, "orl  a,0x82"),
                         (0x65, "xrl  a,0x82")):
            with self.subTest(op=f"0x{op:02x}"):
                self.assertEqual(D.mnemonic(bytes([op, 0x82]), 0), want)
                self.assertEqual(D.OPCODE_LEN[op], 2)

    def test_the_four_map_unassigned_bytes_still_print_db(self):
        # `citation_gap_scan.UNASSIGNED` is the `not-code` criterion a window is
        # graded against, and a decoder that named these four would quietly change
        # what that verdict means. Read from the scanner rather than written here
        # so the two cannot drift into each other being right.
        C = _load("citation_gap_scan")
        self.assertEqual(set(C.UNASSIGNED), {0x06, 0x07, 0x16, 0x17})
        for b in sorted(C.UNASSIGNED):
            with self.subTest(op=f"0x{b:02x}"):
                self.assertEqual(D.mnemonic(bytes([b, 0x00]), 0), f"db   0x{b:02x}")

    def test_db_is_still_reachable_at_all(self):
        # The negative of the negative: a decoder that stopped printing `db`
        # anywhere would satisfy the case above vacuously, and `db` is what
        # several committed tables' framing rests on.
        self.assertTrue(D.mnemonic(b"\xa5\x00", 0).startswith("db"))


class CommittedTables(unittest.TestCase):
    """The four tables, which is where the defect actually showed up.

    `db` was the token this repository reads as *data, not code*, so a code byte
    printed as one made a code island read as a data island. These assert the text
    is gone from all four, that the tables are still tables, and that the column
    the renderer feeds still reads as a decode -- the last one against the
    opposite mistake, since a table emptied of cells would pass the first case.
    """

    def rows(self, name):
        with (REPO / "ec/annotations" / name).open(newline="") as fh:
            return list(csv.reader(fh))

    def test_no_committed_cell_carries_the_six_as_data(self):
        for name, column in CORPUS_TABLES:
            with self.subTest(table=name):
                table = self.rows(name)
                col = table[0].index(column)
                hits = [r[col] for r in table[1:] if SIX_AS_DATA.search(r[col])]
                self.assertEqual(hits, [], f"{name}: {len(hits)} cell(s) left")

    def test_the_four_tables_are_still_tables(self):
        for name, column in CORPUS_TABLES:
            with self.subTest(table=name):
                table = self.rows(name)
                self.assertIn(column, table[0])
                self.assertGreater(len(table), 1, f"{name} has no rows")
                # Every row the same width as the header. A regenerated table that
                # lost or gained a column would otherwise be caught only by
                # whichever reader happens to look at it first.
                for row in table[1:]:
                    self.assertEqual(len(row), len(table[0]), f"{name}: {row[:2]}")

    def test_the_rendered_column_still_reads_as_a_decode(self):
        for name, column in CORPUS_TABLES[:3]:
            with self.subTest(table=name):
                table = self.rows(name)
                col = table[0].index(column)
                filled = [r[col] for r in table[1:] if r[col]]
                self.assertTrue(filled, f"{name}: no filled {column} cells")
                for cell in filled[:100]:
                    self.assertRegex(cell, DECODE_SHAPE, cell)

    def test_the_window_column_still_reads_as_separated_instructions(self):
        # The fourth table's shape is different -- no address column, up to 24
        # instructions joined by ` ; ` and re-spaced by the generator's
        # `" ".join(mnemonic(...).split())` -- so it gets its own case rather than
        # being bent into the other one. The re-spacing is worth naming: a
        # `db` that `mnemonic()` pads to four columns arrives here as `db 0x66`,
        # so an assertion written against the module's own spacing would match
        # nothing in this file and pass vacuously. What is asserted is the shape
        # only -- one instruction per element, none empty, and none of them one
        # of the six (the other 29 opcodes still render `db`, and this column
        # carries plenty of them).
        table = self.rows("indirect-xdata-sites.csv")
        col = table[0].index("window")
        seen = 0
        for row in table[1:]:
            cell = row[col]
            if not cell:
                continue
            seen += 1
            for piece in cell.split(" ; "):
                self.assertTrue(piece.strip(), f"empty instruction in {cell!r}")
                self.assertNotRegex(piece, SIX_AS_DATA, cell)
        self.assertTrue(seen, "no window cells to check")


if __name__ == "__main__":
    unittest.main()
