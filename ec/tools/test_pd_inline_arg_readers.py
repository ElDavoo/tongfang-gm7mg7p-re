#!/usr/bin/env python3
"""`pd_inline_arg_readers.py`'s per-program, per-direction census, on fixtures and
against the committed image.

The tool answers issue #1142's question -- who reads the `??82` cells
`lcall 0x104D` fills in -- and the answer is negative, so what needs holding is
the *shape* of the negative rather than its size. A reader-count tool that
reported zero because it swept nothing would produce the same table, which is why
the fixture cases below exist: each one builds bytes that a method must find, so
a method that silently stopped matching anything is red rather than quietly
agreeing with the firmware.

**The fixtures cover the three things that went wrong while writing it.**
`accumulator_index()` seeded its accumulator walk from nothing and reported zero
everywhere; it then masked the high byte against itself and decoded a fixture as
`0x0008`; and it broke on the first DPTR store, so a `mov DPH` before `mov DPL`
found half the addresses there are. Each has a case below, because each was
invisible against the image -- this firmware has no accumulator-built `??82`
cell, so a suite reading only the image would have passed all three.

**The per-program and per-direction split is asserted as a property, not read
off a figure.** A blended `reads` total is the defect the tool exists to correct,
so the cases here are about *which* program's site a row counts and whether a
`movx @dptr,a` is a write, not about how many there are.

**The image-derived figures are computed here from the firmware, not by re-running
the tool.** The tool wrote `ec/annotations/pd-inline-arg-readers.csv`; a suite
that compared the tool to its own table would pass on a pair that drifted
together. `--check` is run as a subprocess for the one claim that *is* about the
tool.

**What a green run is not.** Nothing here observes hardware: the suite reads two
committed files and opens no EC, reads no register back and runs no live test.
Every figure is a static count over the committed image. Nor does it say a
consumer does not exist -- it says these sweeps found none, and
`--blind-spots` is where each method's own miss conditions are stated.

Usage:
    python3 -m unittest discover -s ec/tools -p test_pd_inline_arg_readers.py
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

import pd_inline_arg_readers as tool

TOOL = HERE / 'pd_inline_arg_readers.py'
FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
READERS_CSV = REPO / 'ec' / 'annotations' / 'pd-inline-arg-readers.csv'

# The opcodes the fixtures below build out of, spelled here rather than reached
# for through the tool so that a rename in either direction breaks a case
# instead of quietly agreeing with itself.
MOV_DPTR, MOV_A_IMM, MOV_DIRECT_A, MOV_DIRECT_IMM = 0x90, 0x74, 0xF5, 0x75
MOVX_RD, MOVX_WR, LCALL = 0xE0, 0xF0, 0x12
# The three bytes of `lcall 0x104D`, high byte first as the 8051
# encodes an absolute target. Written out rather than assembled from
# `LCALL` and 0x104D so that a wrong operand order here shows up as a
# fixture that stops resembling the instruction it names.
LCALL_104D = bytes([0x12, 0x10, 0x4D])


def run(*args):
    """(returncode, stdout, stderr) from the tool, run as a reader runs it."""
    p = subprocess.run([sys.executable, str(TOOL)] + list(args),
                       cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class DirectionTests(unittest.TestCase):
    """A site is a read or a write, and which one is the finding.

    The issue read `--counts-only`'s output as a reader count; these cases are
    the assertion that a site which stores is reported as a store.
    """

    def test_a_movx_write_is_a_write_and_not_a_read(self):
        # Two trailing bytes: `walk_why()` stops at `end of buffer` rather
        # than decode an instruction that has only its own byte in the buffer,
        # so a bare `movx` after the `mov dptr` is never reached.
        fixture = bytes([MOV_DPTR, 0x0A, 0x82, MOVX_WR, 0x00, 0x00])
        got = tool.directions(fixture, 0)
        self.assertEqual(got["writes"], 1)
        self.assertEqual(got["reads"], 0)

    def test_a_movx_read_is_a_read(self):
        fixture = bytes([MOV_DPTR, 0x0A, 0x82, MOVX_RD, 0x00, 0x00])
        got = tool.directions(fixture, 0)
        self.assertEqual(got["reads"], 1)
        self.assertEqual(got["writes"], 0)

    def test_a_window_with_no_movx_is_neither(self):
        # `classify()`'s own "no movx found" wording. Counting it as a read
        # would be the overclaim the whole tool is built to avoid, so the case
        # asserts it contributes to neither column rather than asserting a
        # fourth value this file invented.
        fixture = bytes([MOV_DPTR, 0x0A, 0x82, 0xE4, 0x00, 0x00])
        got = tool.directions(fixture, 0)
        self.assertEqual((got["reads"], got["writes"], got["unresolved"]),
                         (0, 0, 0))

    def test_a_window_handed_to_a_subroutine_is_unresolved_not_a_direction(self):
        fixture = bytes([MOV_DPTR, 0x0A, 0x82, LCALL, 0x10, 0x4D])
        got = tool.directions(fixture, 0)
        self.assertEqual(got["unresolved"], 1)
        self.assertEqual((got["reads"], got["writes"]), (0, 0))


class SweepFixtureTests(unittest.TestCase):
    """Each register-fed sweep finds the idiom it was written for."""

    def test_an_adjacent_immediate_pair_names_the_address(self):
        fixture = bytes([MOV_DIRECT_IMM, tool.DPL, 0x82,
                         MOV_DIRECT_IMM, tool.DPH, 0x0A])
        self.assertEqual(sorted(tool.half_index(fixture)), [0x0A82])

    def test_an_immediate_pair_names_the_address_in_either_order(self):
        # The `mov DPH`/`mov DPL` order. A pairing that only looked for the low
        # byte first would find half the addresses there are, and the half it
        # missed would read as a property of the firmware.
        fixture = bytes([MOV_DIRECT_IMM, tool.DPH, 0x0A,
                         MOV_DIRECT_IMM, tool.DPL, 0x82])
        self.assertEqual(sorted(tool.half_index(fixture)), [0x0A82])

    def test_an_accumulator_built_dptr_names_the_address_in_either_order(self):
        # Both orders, and both must reach `0x0A82`. The second of these two is
        # the case that was broken: a walk that stopped at the first DPTR store
        # found nothing here.
        for fixture in (
                bytes([MOV_A_IMM, 0x82, MOV_DIRECT_A, tool.DPL,
                       MOV_A_IMM, 0x0A, MOV_DIRECT_A, tool.DPH]),
                bytes([MOV_A_IMM, 0x0A, MOV_DIRECT_A, tool.DPH,
                       MOV_A_IMM, 0x82, MOV_DIRECT_A, tool.DPL])):
            self.assertEqual(sorted(tool.accumulator_index(fixture)), [0x0A82],
                             f'{fixture.hex(" ")} decoded elsewhere')

    def test_an_accumulator_walk_with_no_established_a_is_refused(self):
        # The two store forms with nothing loading A. This is the method's miss
        # condition as behaviour: an A carried in from a register is *not*
        # assumed to be 0x00, which is the guess that would have manufactured
        # addresses rather than declining to.
        fixture = bytes([MOV_DIRECT_A, tool.DPL, MOV_DIRECT_A, tool.DPH])
        self.assertEqual(dict(tool.accumulator_index(fixture)), {})

    def test_an_accumulator_walk_missing_one_half_yields_no_address(self):
        fixture = bytes([MOV_A_IMM, 0x82, MOV_DIRECT_A, tool.DPL])
        self.assertEqual(dict(tool.accumulator_index(fixture)), {})

    def test_half_a_pair_is_not_an_address(self):
        fixture = bytes([MOV_DIRECT_IMM, tool.DPL, 0x82])
        self.assertEqual(dict(tool.half_index(fixture)), {})

    def test_the_helper_entry_sweep_finds_both_absolute_forms(self):
        fixture = LCALL_104D + bytes([0x02, 0x10, 0x4D])
        self.assertEqual(tool.helper_entries(fixture, 0x104D), [0, 3])


class PerProgramTests(unittest.TestCase):
    """The split, which is the whole finding, on bytes rather than on the image."""

    def pd_image_with(self, payload: bytes, at: int = None) -> bytes:
        """A buffer shaped so `region_of()` reads the payload as PD-image code.

        Long enough for the PD region to be inside it and erased elsewhere, so
        `region_of()` returns `pd-image` for the offset `payload` is placed at
        and nothing else. Built rather than borrowed from the committed image so
        that a case can put a *read* where the firmware has none.
        """
        pd_lo = next(lo for name, lo, _, _, _ in tool.REGIONS
                     if name == "pd-image")
        buf = bytearray(b"\xFF" * (pd_lo + len(payload) + 8))
        at = pd_lo if at is None else at
        buf[at:at + len(payload)] = payload
        return bytes(buf)

    def test_a_pd_image_read_is_counted_as_one(self):
        # **The negative result's own falsifier.** Every other case in this
        # class asserts that `pd_side_reads` is zero, which a column hard-wired
        # to zero would also satisfy. This builds a PD-image site that does
        # read the cell and requires the column to say so -- so the zeros in
        # `ImageFigureTests` are a measurement of the firmware rather than a
        # property of the code.
        payload = bytes([MOV_DPTR, 0x0A, 0x82, MOVX_RD, 0x00, 0x00])
        row = tool.row_for(self.pd_image_with(payload), 0x0A82, 1, {}, {})
        self.assertEqual(row["pd_side_reads"], 1)
        self.assertEqual(row["mov_dptr_by_region"], "pd-image=1")
        self.assertIn("pd-side reads found", row["reason"])

    def test_a_pd_image_write_is_not_counted_as_a_read(self):
        # The correction this issue turns on, on bytes rather than on the
        # image: a site in the PD image that *stores* is a writer, and a column
        # that counted sites rather than directions would report a reader here.
        payload = bytes([MOV_DPTR, 0x0A, 0x82, MOVX_WR, 0x00, 0x00])
        row = tool.row_for(self.pd_image_with(payload), 0x0A82, 1, {}, {})
        self.assertEqual(row["pd_side_reads"], 0)
        self.assertEqual(row["mov_dptr_writes"], 1)

    def test_a_site_is_attributed_to_the_program_it_is_in(self):
        # A row's `mov_dptr_by_region` names the program rather than a blended
        # total, and the per-region counts add up to the whole-image site count.
        # `region_of()` itself is `trace_xdata_refs`'s, so this asserts the tool
        # uses it per site rather than re-deciding what a region is.
        rows = tool.census(FIRMWARE.read_bytes())
        self.assertTrue(rows)
        for row in rows:
            regions = dict(part.split("=") for part in
                           row["mov_dptr_by_region"].split(";") if part)
            self.assertEqual(sum(int(v) for v in regions.values()),
                             row["mov_dptr_sites"])

    def test_no_row_carries_a_blended_reader_total(self):
        # The defect would be a single `reads` column with another program's
        # sites folded into it. `pd_side_reads` is the column that must never
        # exceed the whole-image read count, and must not be the sum of it.
        for row in tool.census(FIRMWARE.read_bytes()):
            self.assertLessEqual(row["pd_side_reads"], row["mov_dptr_reads"])


class ImageFigureTests(unittest.TestCase):
    """The write-up's figures, derived here from the firmware."""

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.rows = {r["dest"]: r for r in tool.census(cls.d)}

    def test_the_deposit_counts_come_from_the_committed_census(self):
        # The population is read out of `pd-inline-arg-sites.csv`, so the totals
        # here are the committed tool's and are re-derivable by anyone with the
        # file. Asserting the property -- that the column is the committed
        # census's -- rather than re-deriving the scan keeps this suite out of
        # the business of the tool whose table it is not testing.
        with (REPO / 'ec' / 'annotations' / 'pd-inline-arg-sites.csv').open(
                newline='') as f:
            committed = [r for r in csv.DictReader(f) if r["dest"]]
        self.assertEqual(sum(int(r["deposits"]) for r in self.rows.values()),
                         len(committed))

    def test_the_0x0a82_site_is_a_writer(self):
        # The correction at the centre of this issue. `--counts-only` reported
        # one site for `0x0A82` in the PD image and the issue read it as a
        # reader; decoded, it stores two bytes and walks one, and this is the
        # cell that makes "174 writers against one reader" wrong.
        row = self.rows['0x0A82']
        self.assertEqual(row["mov_dptr_by_region"], "pd-image=1")
        self.assertEqual(row["mov_dptr_reads"], 0)
        self.assertGreater(row["mov_dptr_writes"], 0)

    def test_every_0x0782_site_is_in_another_program(self):
        # The other half of the correction: all eleven are `bank0`, the main EC.
        # Summing them into a reader count for the PD image's 107 deposits is the
        # cross-program artifact, and `pd-xdata-span-sites.csv` already carries
        # the same split for this address.
        row = self.rows['0x0782']
        self.assertEqual(row["mov_dptr_by_region"], "bank0=11")
        self.assertNotIn("pd-image", row["mov_dptr_by_region"])
        self.assertEqual(row["pd_side_reads"], 0)
        # And the main EC's own reads are real, they are just not this
        # program's -- a row holding zero here would hide the split rather than
        # report it.
        self.assertGreater(row["mov_dptr_reads"], 0)

    def test_0x0882_is_settled_as_a_zero_by_two_methods(self):
        # No `MOV DPTR` site anywhere in the dump, and no row in the
        # decompile-derived census either. The two have different blind spots,
        # so their agreement is what makes the zero a result rather than a
        # shrug.
        row = self.rows['0x0882']
        self.assertEqual(row["mov_dptr_sites"], 0)
        self.assertEqual(row["mov_dptr_by_region"], "")
        with (REPO / 'ec' / 'annotations' / 'xdata-registers.csv').open(
                newline='') as f:
            census = {r["addr"].upper(): r for r in csv.DictReader(f)}
        self.assertNotIn("0X0882", census)

    def test_no_cell_has_a_pd_side_read(self):
        # The negative result, in the form the write-up states it: not "there is
        # no reader" but "these sweeps found none". Asserted per cell so a
        # single row gaining one is the visible failure.
        for dest, row in self.rows.items():
            self.assertEqual(row["pd_side_reads"], 0, f'{dest} gained a read')

    def test_every_row_carries_a_reason(self):
        # The empty-is-a-token rule, on the column a reader of the CSV sees
        # first. A blank `reason` is indistinguishable from "nothing to say".
        for dest, row in self.rows.items():
            self.assertNotEqual(row["reason"], "", f'{dest} has no reason')

    def test_the_entry_sweep_finds_the_register_fed_entries_the_scan_misses(self):
        # The population fact: `lcall 0x104D` is one spelling, and `ljmp 0x104D`
        # plus the two forwarders are three more the committed census does not
        # count. Reported here as entries, because an entry takes its
        # destination in a register and so names no cell.
        found = {(t, label): n for t, label, n, _ in tool.entries(self.d)}
        self.assertEqual(found[(0x104D, "lcall")], 458)
        self.assertEqual(found[(0x104D, "ljmp")], 2)
        self.assertEqual(found[(0x107E, "lcall")], 2)
        self.assertEqual(found[(0x1098, "lcall")], 2)


class CommittedTableTests(unittest.TestCase):
    """`--check`: the committed table is what this run derives."""

    def test_the_committed_table_is_what_the_committed_image_derives(self):
        rc, out, err = run(str(FIRMWARE), '--check')
        self.assertEqual(rc, 0, err)

    def test_a_doctored_region_is_red_and_names_the_row(self):
        # The cell that carries the finding, because a doctored read count would
        # be swallowed by a table whose whole point is the per-program split.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'doctored.csv'
            with READERS_CSV.open(newline='') as f:
                rows = list(csv.reader(f))
            header = rows[0]
            column = header.index('mov_dptr_by_region')
            for row in rows[1:]:
                if row[header.index('dest')] == '0x0782':
                    row[column] = 'pd-image=11'
                    break
            else:
                self.skipTest('the 0x0782 row is gone from the committed table')
            buf = io.StringIO(newline='')
            csv.writer(buf, lineterminator='\r\n').writerows(rows)
            path.write_text(buf.getvalue(), newline='')
            rc, _, err = run(str(FIRMWARE), '--check', str(path))
        self.assertNotEqual(rc, 0)
        self.assertIn('pd-image=11', err)

    def test_an_unaltered_copy_is_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'copy.csv'
            path.write_bytes(READERS_CSV.read_bytes())
            rc, _, err = run(str(FIRMWARE), '--check', str(path))
        self.assertEqual(rc, 0, err)

    def test_an_unidentified_pd_region_is_refused_rather_than_counted(self):
        # Without the marker the two programs cannot be told apart and every
        # count would be the blend this tool exists to prevent, so the run
        # exits non-zero rather than reporting one.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'nomarker.bin'
            d = bytearray(FIRMWARE.read_bytes())
            d[0x20040:0x20049] = b'\x00' * len(tool.PD_MARKER[1])
            path.write_bytes(bytes(d))
            rc, _, err = run(str(path), '--check')
        self.assertNotEqual(rc, 0)
        self.assertIn('unidentified', err)


if __name__ == '__main__':
    unittest.main()