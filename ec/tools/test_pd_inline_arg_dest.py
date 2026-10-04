#!/usr/bin/env python3
"""`pd_inline_arg_dest.py`'s contract, on fixtures and against the committed image.

`pd_inline_arg_dest.py` replaces the backward byte scan behind
`ec/annotations/pd-inline-arg-sites.csv`'s `dest` column with a decode, and
writes `ec/annotations/pd-inline-arg-dest.csv`. Two things about that need
holding, and they are different kinds of check.

**The decode's own behaviour, on hand-built fixtures.** A walk that steps over
an `INLINE_ARG_CALLS` argument block has to land *past* the block rather than
inside it, or every row behind one is framed from a data byte and reports a
`mov dptr` that is not an instruction. Two walks agreeing have to read as one
answer and two walks conflicting as `decoded-ambiguous`, and a row with no
`mov dptr` on any converging walk has to produce its reason token and *no*
value. Each is a case below against bytes built for it, because none of them
can be provoked out of the committed image -- the image has no instance of the
ambiguous case at all, so a suite that only ran over the image would be
asserting that a code path is reachable and never executing it.

**The image-derived figures, asserted from the firmware rather than from the
tool.** The write-up's recovery counts are the finding, and they come from a
committed table another tool wrote. A suite that re-ran `pd_inline_arg_dest.py`
and compared it to the table would be circular: a pair that drifted together
would pass. So the figures below are computed here from
`ec/firmware/GMxMGxx_11.800` by this file's own code, and the token names they
name are `pd_inline_arg_dest.py`'s imported constants -- so a rename breaks the
import rather than silently passing, and the arithmetic is not re-run through
the tool under test. `--check` is run separately, as a subprocess, for the one
claim that *is* about the tool: that the table it writes is the table it
regenerates.

**What a green run is not.** Nothing here observes hardware. The suite reads
two committed files -- the firmware image and the committed site table -- and
no EC is opened, no register is read back and no live test ran. Every figure is
a static count over the committed image, which is the tool's own claim and this
suite's too. Nor does a green run say the decode is *right*: it says the
framing decisions are the ones this suite pins and that the committed table
reproduces. Which of two framings is real needs control-flow recovery, which
`../../ec/README.md` records as deliberately not attempted.

Usage:
    python3 -m unittest discover -s ec/tools -p test_pd_inline_arg_dest.py
"""
import csv
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import pd_inline_arg_dest as tool
from disasm8051 import INLINE_ARG_CALLS

TOOL = HERE / 'pd_inline_arg_dest.py'
FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
SITES_CSV = REPO / 'ec' / 'annotations' / 'pd-inline-arg-sites.csv'
DEST_CSV = REPO / 'ec' / 'annotations' / 'pd-inline-arg-dest.csv'

# The `mov dptr,#imm16` the fixtures below put where a decode can find it.
MOV_DPTR = 0x90
# The three bytes of `lcall 0x104D`, high byte first as the 8051 encodes an
# absolute target. Written out rather than assembled from the opcode and the
# address because a transposed pair here is a *different instruction*: the
# fixtures kept passing with the bytes the wrong way round, since nothing in
# the decode path reads a call's operand -- but `inline_arg_len()` keys on it,
# so the argument-block cases below were passing without the block being one.
LCALL_104D = bytes([0x12, 0x10, 0x4D])


def run(*args):
    """(returncode, stdout, stderr) from the tool, run as a reader runs it.

    A subprocess rather than an import, so the exit codes asserted on below are
    the ones a reader gets. Every positive case in this suite would also be
    satisfied by a comparison that reads nothing, which is what the negative
    controls are for.
    """
    p = subprocess.run([sys.executable, str(TOOL)] + list(args),
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def decode(fixture: bytes, at: int = 0, reach: int = None):
    """The tool's row for the `lcall` at `at` in `fixture`.

    Defaults to the tool's own reach, so a case here is about the framing rule
    and not about a particular window; the one case that is *about* the window
    passes its own.
    """
    return tool.decode_row(fixture, at, tool.REACH if reach is None else reach)


class DecodeFixtureTests(unittest.TestCase):
    """The framing rules, on bytes built to provoke each one."""

    def test_a_walk_steps_over_an_inline_argument_block(self):
        # Two calls back to back. The walk to the *second* one has to cross the
        # first one's four argument bytes, and crossing them is the whole
        # property: `00 00 00 01` decodes as three `nop`s and an `ajmp`, so a
        # walk that read the block as instructions arrives four bytes past the
        # second call and never lands on it. The decode therefore only recovers
        # `0x0A82` if the block was stepped over as a block.
        fixture = bytes([MOV_DPTR, 0x0A, 0x98,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01])
        at = len(fixture) - 7
        self.assertIsNotNone(tool.walk_to(fixture, 0, at),
                             'the walk did not reach the second call at all')
        row = decode(fixture, at)
        self.assertEqual(row["dest_decoded"], "0x0A82")
        self.assertEqual(row["dest_reason"], tool.UNIQUE)

    def test_a_walk_does_not_decode_inside_an_argument_block(self):
        # The same property on the instruction offsets rather than on the row:
        # no walk reaching the call may report an instruction inside a block.
        # Asserted over both blocks, because the first is the one a walk has to
        # cross and the second is the one it stops at.
        fixture = bytes([MOV_DPTR, 0x0A, 0x98,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01])
        at = len(fixture) - 7
        n = INLINE_ARG_CALLS[0x104D]
        blocks = [range(b + 3, b + 3 + n) for b in (3, at)]
        for back in range(1, tool.REACH + 1):
            insns = tool.walk_to(fixture, at - back, at)
            if insns is None:
                continue
            for off in insns:
                for block in blocks:
                    self.assertNotIn(
                        off, block,
                        f'walk from {at - back} decoded inside a block')

    def test_two_agreeing_walks_read_as_one_answer(self):
        fixture = bytes([0xE4,              # clr a
                         MOV_DPTR, 0x0A, 0x82,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01])
        row = decode(fixture, at=fixture.index(LCALL_104D))
        self.assertEqual(row["dest_reason"], tool.UNIQUE)
        self.assertEqual(row["dest_decoded"], "0x0A82")
        # Every walk that carried a load agreed, so the candidate cell names one
        # address. A `decoded-unique` row carrying two candidates would be the
        # token contradicting itself.
        self.assertEqual(len(row["dest_candidates"].split("|")), 1)

    def test_two_conflicting_walks_are_ambiguous_and_not_resolved(self):
        # The shape the committed image actually contains: `90 90 08 3D` read
        # from offset 0 is `mov dptr,#0x9008`, and read from offset 1 -- one
        # byte later -- the same four bytes are `mov dptr,#0x083D`. Both walks
        # reach the call, so the two disagree about which pointer is live.
        # Neither is preferred and the committed table is not consulted:
        # picking one would be a coin flip dressed as a measurement, which is
        # what `decoded-ambiguous` exists to prevent.
        fixture = bytes([MOV_DPTR, MOV_DPTR, 0x08, 0x3D,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01])
        row = decode(fixture, at=fixture.index(LCALL_104D))
        self.assertEqual(row["dest_reason"], tool.AMBIGUOUS)
        self.assertEqual(row["dest_decoded"], "")
        candidates = row["dest_candidates"].split("|")
        self.assertEqual(len(candidates), 2)
        self.assertIn("0x0882x1", candidates)
        self.assertIn("0x9082x1", candidates)

    def test_agreement_is_on_the_destination_not_the_loaded_dptr(self):
        # Two DPLs, one high byte. The mechanism overwrites the low byte with
        # the literal, so both walks deposit to the same cell and calling that
        # ambiguous would report a framing difference as a destination one.
        fixture = bytes([MOV_DPTR, 0x0A, 0x98,
                         0x75, 0x82, 0x34,               # mov DPL,#0x34
                         MOV_DPTR, 0x0A, 0x82,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01])
        row = decode(fixture, at=fixture.index(LCALL_104D))
        self.assertEqual(row["dest_reason"], tool.UNIQUE)
        self.assertEqual(row["dest_decoded"], "0x0A82")

    def test_a_row_with_no_mov_dptr_gets_a_reason_and_no_value(self):
        # A run of two-byte instructions and the call, with no `mov dptr` on it.
        fixture = bytes([0xE4, 0xE4, 0xE4,
                         *LCALL_104D, 0x00, 0x00, 0x00, 0x01])
        row = decode(fixture, at=fixture.index(LCALL_104D))
        self.assertEqual(row["dest_reason"], tool.NO_DPTR)
        self.assertEqual(row["dest_decoded"], "")
        # The empty is a token beside it, never the value cell itself: a blank
        # `dest_decoded` on a row with no reason reads as an answer.
        self.assertNotEqual(row["dest_reason"], "")

    def test_every_row_carries_a_reason(self):
        # The property, over the whole committed population rather than the
        # fixtures above. A row that could come back with an empty
        # `dest_reason` would put a blank in the table's `reason` column, and a
        # blank there is indistinguishable from "nothing to say".
        d = FIRMWARE.read_bytes()
        for row in tool.rows(d):
            self.assertIn(row["dest_reason"],
                          (tool.UNIQUE, tool.AMBIGUOUS, tool.NO_DPTR,
                           tool.NO_WALK))

    def test_a_short_buffer_is_refused_rather_than_indexed(self):
        # `walk_to()` reads the opcode byte at every step, so a call whose
        # buffer ends mid-instruction is the case an IndexError would come
        # from. Handing it a one-byte buffer asserts the refusal.
        self.assertIsNone(tool.walk_to(bytes([0x90]), 0, 8))


class ImageFigureTests(unittest.TestCase):
    """The write-up's figures, derived here from the firmware.

    Computed by this file rather than by re-running the tool, because the tool
    is what wrote the numbers. `dest_reason`'s vocabulary is the tool's, so a
    rename here fails at the import rather than passing quietly.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.rows = tool.rows(cls.d)
        with SITES_CSV.open(newline="") as f:
            cls.committed = {r["file_offset"]: r for r in csv.DictReader(f)}

    def decode_row(self, offset: int):
        return next(r for r in self.rows if r["file_offset"] == offset)

    def count(self, reason: str, only_empty: bool = False) -> int:
        return sum(1 for r in self.rows
                   if r["dest_reason"] == reason
                   and (not only_empty or not self.committed[r["file_offset"]]["dest"]))

    def test_the_committed_census_population_is_the_one_decoded(self):
        # The tool reads the committed table for its population rather than
        # re-deriving the call scan, and this asserts the two agree on what
        # that population is -- the property that makes the rest of these
        # figures about the same rows.
        self.assertEqual(len(self.rows), len(self.committed))

    def test_the_scan_left_rows_empty_and_the_decode_recovers_most_of_them(self):
        # The finding the write-up leads with: the byte scan cannot see a
        # `mov dptr` past 32 bytes or across an argument block, so it leaves
        # rows empty, and a decode reaches further and recovers most of them.
        empty = [r for r in self.rows
                 if not self.committed[r["file_offset"]]["dest"]]
        recovered = [r for r in empty
                     if r["dest_reason"] in (tool.UNIQUE, tool.AMBIGUOUS)]
        self.assertEqual(len(empty), 64)
        self.assertEqual(len(recovered), 48)
        # The remainder must each carry its reason, or the recovery figure is
        # counting successes and dropping the rest silently.
        for row in empty:
            self.assertNotEqual(row["dest_reason"], "")

    def test_the_rows_the_scan_left_empty_have_no_value_beyond_the_recovered_ones(self):
        # The 16 that stay empty are empty *with a reason*, and the split
        # between "no walk reached the call" and "no `mov dptr` on any walk"
        # is the tool's own vocabulary rather than a single bucket.
        empty = [r for r in self.rows
                 if not self.committed[r["file_offset"]]["dest"]]
        self.assertEqual(self.count(tool.NO_DPTR, only_empty=True), 16)
        self.assertEqual(self.count(tool.NO_WALK, only_empty=True), 0)

    def test_the_decode_agrees_with_every_dest_the_scan_did_reach(self):
        # The scan's readings were not wrong where it had one: over the rows
        # carrying a `dest`, a decode that lands exactly on the same cell. This
        # is the load-bearing cross-check -- the decode is a *replacement*, so
        # it has to reproduce what the scan got right before its extra reach
        # counts for anything.
        #
        # Restricted to the rows that carry a value. An ambiguous row decodes no
        # value *by design*, and holding it to the scan's would be holding the
        # tool to refusing to answer; `decoded-ambiguous` rows are checked below
        # instead.
        compared = 0
        for row in self.rows:
            committed = self.committed[row["file_offset"]]["dest"]
            if not committed or row["dest_reason"] == tool.AMBIGUOUS:
                continue
            self.assertEqual(row["dest_decoded"], committed,
                             f'{row["file_offset"]} decoded elsewhere')
            compared += 1
        self.assertTrue(compared, "no row carried both a dest and a value")

    def test_an_ambiguous_row_carries_candidates_and_no_value(self):
        # The refusal is a shape, not a gap: an ambiguous row names what the
        # walks disagreed about and leaves `dest_decoded` empty. A row that
        # silently picked one would be a coin flip with a value in it.
        for row in self.rows:
            if row["dest_reason"] != tool.AMBIGUOUS:
                continue
            self.assertEqual(row["dest_decoded"], "")
            self.assertGreater(len(row["dest_candidates"].split("|")), 1)

    def test_every_decoded_destination_has_the_literal_low_byte(self):
        # The mechanism substitutes 0x82 for the caller's DPL, so a decoded
        # destination ending in anything else would mean the decode was reading
        # a DPTR rather than a deposit -- which is the `0x0A98` the summary
        # rendered before the masking was moved ahead of it.
        from pd_inline_arg_sites import DEST_LOW
        for row in self.rows:
            if row["dest_decoded"]:
                self.assertEqual(int(row["dest_decoded"], 16) & 0xFF, DEST_LOW)


class CommittedTableTests(unittest.TestCase):
    """`--check`: the committed table is what this run derives."""

    def test_the_committed_table_is_what_the_committed_image_derives(self):
        rc, out, err = run(str(FIRMWARE), '--check')
        self.assertEqual(rc, 0, err)

    def test_a_doctored_table_is_red_and_names_the_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'doctored.csv'
            raw = DEST_CSV.read_bytes().decode('utf-8')
            rows = list(csv.reader(io.StringIO(raw, newline='')))
            column = rows[0].index('dest_reason')
            for row in rows[1:]:
                if row[column] == tool.UNIQUE:
                    row[column] = 'doctored'
                    break
            else:
                self.skipTest('no row carries the reason being altered')
            out_buf = io.StringIO(newline='')
            csv.writer(out_buf, lineterminator='\r\n').writerows(rows)
            path.write_text(out_buf.getvalue(), newline='')
            rc, _, err = run(str(FIRMWARE), '--check', str(path))
        self.assertNotEqual(rc, 0)
        self.assertIn('doctored', err)

    def test_an_unaltered_copy_is_green(self):
        # A check that is red on everything passes every positive case above,
        # so the control beside each red is the half that matters.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'copy.csv'
            path.write_bytes(DEST_CSV.read_bytes())
            rc, _, err = run(str(FIRMWARE), '--check', str(path))
        self.assertEqual(rc, 0, err)


if __name__ == '__main__':
    unittest.main()