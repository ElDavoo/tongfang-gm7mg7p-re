#!/usr/bin/env python3
"""`pd-store-back-dptr-sites.csv` is derived, and the properties behind the write-up hold.

`ec/annotations/pd-store-back-dptr-sites.csv` is the committed table of the DPTR
each caller of the PD image's `0x122F` store-back entry loaded before it
transferred, over the byte-scan population `../../docs/findings/pd-direct-offset-pointer-add.md`
§3 counts. `ec/tools/pd_store_back_dptr.py` re-derives it from the committed
firmware image and `--check` diffs the two, byte for byte.

**What is checked, and why each part is here.**

1. `--check` against the committed table exits 0. The table is what the
   committed image derives, so a row that stopped being true is a red run.
2. `--self-test` exits 0 — the `r2 -a 8051` transcriptions, the derived entry,
   and the relations the write-up reads.
3. **The negative controls, which are the substance.** Every positive case above
   is also satisfied by a comparison that reads nothing. So a doctored cell is
   red and its diff names the row; a missing table is red rather than silently
   created; a dropped row is red; the unaltered copy of the same table beside
   each red is green, because a check that is red on everything passes all of
   them. These run as subprocesses over `tempfile` copies through
   `--check PATH`, so the tool reads a file this suite made and the committed
   table is never written.
4. **The tool's own refusals**, which are the half that matters: no marker means
   no population to read rather than a confident answer about unidentified
   bytes.
5. **Property cases over fixtures**, built by the local `fixture()` helper
   rather than by pointing at the firmware. The reason
   `test_check_site_resolution.py` gives is the one that applies here: the
   population is "an opcode byte somewhere", so a fixture that *is* the image
   would be testing the image. These cover the band test at its own edges and
   the listing grade that keeps a disagreement visible.
6. **The baseline comparison is a relation, not a figure.** The store-back
   sites' share of the displacement band must exceed the whole region's. The
   two percentages are read out of the tool's own output rather than pinned,
   because the comparison is the finding and each percentage is a number a
   change to the image would move.

**What a green run is not.** It says the committed table is what this run
derives from the committed image, and that the properties the write-up rests on
hold over the committed tree. It does not say the scan is complete: a byte scan
over the region both over-counts (a `12 12 2f` inside a data table reads as
`lcall 0x122F`) and under-counts (a call reached through a dispatch table
carries no target bytes), so the table is a candidate population and the
`in_committed_listing` column is what separates the corroborated rows from the
rest. This suite deliberately asserts no row count: a count is a figure every
PD change moves.

Nothing here observes hardware. The suite reads committed files -- the firmware
image, the table and the exported listings -- and no EC is opened, no register
is read back and no live test ran.
"""
import csv
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOOL = HERE / 'pd_store_back_dptr.py'
FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
SITES_CSV = REPO / 'ec' / 'annotations' / 'pd-store-back-dptr-sites.csv'
LISTINGS = REPO / 'ec' / 'decompiled' / 'pd'

# pd_store_back_dptr imports its siblings by bare module name, the way
# addc_dph_sites.py and computed_dptr_sites.py do, so the tool directory has
# to be on the path before they are loaded rather than after.
sys.path.insert(0, str(HERE))
import pd_store_back_dptr as tool


def run(*args):
    """Run the tool and return (returncode, stdout, stderr).

    A subprocess rather than an import, so what the cases below assert on is
    the exit code a reader gets rather than a value this file produced itself.
    Every positive case in this suite is also satisfied by a comparison that
    reads nothing, which is the failure the negative controls exist for.
    """
    cmd = [sys.executable, str(TOOL)] + list(args)
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def committed_copy(tmpdir, mutate=None):
    """A byte-identical copy of the committed table, with `mutate` applied.

    Copied as bytes rather than re-rendered: the committed table carries the
    csv module's own CRLF terminator, and `trace_xdata_refs.check_table` reads
    with `newline=""` precisely so a checkout that rewrote the terminators is
    reported as a difference rather than compared against a translation this
    suite made up. Writing the copy back the same way keeps the control green
    for that reason instead of for luck.
    """
    raw = SITES_CSV.read_bytes()
    if mutate is not None:
        raw = mutate(raw)
    path = Path(tmpdir) / 'copy.csv'
    path.write_bytes(raw)
    return path


def doctor_one_displacement(raw):
    """Change one cell of one row; every other cell is untouched.

    One cell rather than a whole row, so the diff `--check` prints names the
    field that moved instead of a row that vanished. This is the shape a hand
    edit takes, and it is the case a suite holding only the row *count* passes.

    Parsed and re-rendered with the csv module rather than split on `,`, so a
    quoted cell containing a comma cannot shift the column being edited.
    Re-rendering is safe for the control to stay meaningful because the whole
    table is rewritten in the writer's own dialect, so an unaltered table
    re-renders to the bytes already committed -- which
    `test_an_unaltered_copy_is_green` asserts.
    """
    text = raw.decode('utf-8')
    rows = list(csv.reader(io.StringIO(text, newline='')))
    header, column = rows[0], rows[0].index('dptr_loaded')
    for row in rows[1:]:
        if len(row) == len(header) and row[column]:
            row[column] = '0xDEAD'
            break
    else:
        raise AssertionError('no row carries a `dptr_loaded` to alter')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n').writerows(rows)
    return out.getvalue().encode('utf-8')


def demote_a_listing_grade(raw):
    """Turn one `both` grade into `no`, leaving the row otherwise intact.

    The other shape a hand edit takes here, and the one this tool's vocabulary
    is most able to get wrong: a row whose load and transfer a decoded listing
    carries being filed as resting on the byte scan alone. Nothing else in the
    row moves, so a check that only counted rows would not see it.
    """
    text = raw.decode('utf-8')
    rows = list(csv.reader(io.StringIO(text, newline='')))
    header, column = rows[0], rows[0].index('in_committed_listing')
    for row in rows[1:]:
        if len(row) == len(header) and row[column] == 'both':
            row[column] = 'no'
            break
    else:
        raise AssertionError('no row carries a `both` grade to demote')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n').writerows(rows)
    return out.getvalue().encode('utf-8')


def fixture(*chunks):
    """A synthetic PD region, as a bytes object.

    The population this tool reads is "an opcode byte somewhere", so a fixture
    that were the firmware image would be testing the image. What the cases
    below need is control over *where* a `mov dptr,#imm16` sits relative to a
    transfer, which the committed image does not let them choose.
    """
    return b''.join(chunks)


def dptr(imm):
    """The three bytes of `mov dptr,#imm16`."""
    return bytes([0x90, (imm >> 8) & 0xFF, imm & 0xFF])


def store_back_entry_bytes():
    """The store-back entry as `fold_back()` finds it, for a fixture to call.

    `fold_back()` locates the block by looking for the direct-form writer that
    stores a *computed* value into the pair, so a fixture has to carry that
    shape before any transfer to it will be measured. Transcribed from the
    committed listing `ec/decompiled/pd/122F.asm` and re-exported as bytes here
    rather than as an address, because these cases are about the scan around a
    site rather than about the entry.
    """
    return bytes([
        0xE5, 0x0E,                    # mov a,0x0e
        0x25, 0x82,                    # add a,0x82
        0xF5, 0x82,                    # mov 0x82,a
        0xE5, 0x0D,                    # mov a,0x0d
        0x35, 0x83,                    # addc a,0x83
        0xF5, 0x83,                    # mov 0x83,a
        0xB5, 0x0D, 0x04,              # cjne a,0x0d,+4
        0x85, 0x82, 0x0E,              # mov 0x0e,0x82
        0x22,                          # ret
        0x85, 0x82, 0x0E,              # mov 0x0e,0x82
        0xF5, 0x0D,                    # mov 0x0d,a
        0x22,                          # ret
    ])


ENTRY_OFFSET = 0x100


class DerivedTableTests(unittest.TestCase):
    """The two modes, run the way a reader runs them."""

    def test_the_committed_table_is_what_the_committed_image_derives(self):
        # The whole of the hold. `--check` re-derives the table from
        # `ec/firmware/GMxMGxx_11.800` and diffs it against the committed file
        # byte for byte, so a row that no longer describes the PD image fails
        # here rather than in prose.
        rc, out, err = run(str(FIRMWARE), '--check')
        self.assertEqual(rc, 0, out + err)

    def test_the_tools_own_self_test_holds(self):
        # `--self-test` is the other half, and it needs no argument: it checks
        # the decodes, the derived entry and the relations against the
        # committed image and the committed listings.
        rc, out, err = run('--self-test')
        self.assertEqual(rc, 0, out + err)

    def test_check_and_csv_agree_with_each_other(self):
        # The two are the same derivation reached two ways, and `--check`
        # compares against the *file* rather than against stdout. A `--csv` that
        # printed something `--check` would not accept would make the mode a
        # reader regenerates the table with differ from the one that holds it.
        #
        # In binary rather than through `run()`, because that helper reads the
        # pipe in text mode and universal-newline translation would rewrite the
        # csv module's CRLF terminator to LF on the way through -- which is the
        # exact difference `trace_xdata_refs.check_table` exists to preserve, and
        # this case is about the bytes. Reading the file the same way it is
        # written is what keeps the comparison about the bytes too.
        p = subprocess.run([sys.executable, str(TOOL), str(FIRMWARE), '--csv'],
                           cwd=REPO, capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        self.assertEqual(p.stdout, SITES_CSV.read_bytes())


class NegativeControlTests(unittest.TestCase):
    """The check failing when it should, and passing when it should.

    Every case here is a mutation of the *input to the check* rather than of
    the tool, because a mutation of the tool would be testing the mutation. The
    unaltered copy runs beside each red for the reason in `run()`: a check that
    reports a difference for everything passes all of the reds below.
    """

    def test_a_doctored_cell_is_red_and_the_diff_names_the_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = committed_copy(tmp, doctor_one_displacement)
            rc, out, err = run(str(FIRMWARE), '--check', str(path))
            self.assertEqual(rc, 1, out + err)
            # The failure has to say which row moved, or it is a red run that
            # tells a reader nothing about what to regenerate.
            self.assertIn('lcall,pd,', err)

    def test_a_demoted_listing_grade_is_red(self):
        # The other shape a hand edit takes in this table, and the one the
        # three-grade vocabulary exists to make visible: a site a decoded
        # listing carries filed as one resting on the byte scan alone.
        with tempfile.TemporaryDirectory() as tmp:
            path = committed_copy(tmp, demote_a_listing_grade)
            rc, out, err = run(str(FIRMWARE), '--check', str(path))
            self.assertEqual(rc, 1, out + err)

    def test_an_unaltered_copy_is_green_beside_the_doctored_one(self):
        # The control. Without it, `test_a_doctored_cell_is_red...` is also
        # satisfied by a `--check` that always exits 1.
        with tempfile.TemporaryDirectory() as tmp:
            path = committed_copy(tmp)
            rc, out, err = run(str(FIRMWARE), '--check', str(path))
            self.assertEqual(rc, 0, out + err)

    def test_a_missing_table_is_red_and_is_not_created(self):
        # The failure the tool's own docstring calls out: a `--check` that
        # creates what it is checking turns a missing artifact into a green run
        # and then leaves a file behind for the next commit to trust.
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / 'absent.csv'
            rc, out, err = run(str(FIRMWARE), '--check', str(absent))
            self.assertEqual(rc, 1, out + err)
            self.assertFalse(absent.exists(), 'the missing table was created')

    def test_a_dropped_row_is_red(self):
        # A table that lost a row parses cleanly and reads as a census, which
        # is the shape a partial regeneration leaves behind.
        def drop_a_row(raw):
            lines = raw.decode('utf-8').split('\r\n')
            return '\r\n'.join(lines[:1] + lines[2:]).encode('utf-8')

        with tempfile.TemporaryDirectory() as tmp:
            path = committed_copy(tmp, drop_a_row)
            rc, out, err = run(str(FIRMWARE), '--check', str(path))
            self.assertEqual(rc, 1, out + err)

    def test_nothing_here_wrote_the_committed_table(self):
        # The hold is only worth having if the case that runs it leaves the
        # artifact alone. Compared by bytes, because a rewrite that preserved
        # the parsed rows would still be a tool writing to a committed input.
        before = SITES_CSV.read_bytes()
        run(str(FIRMWARE), '--check')
        run('--self-test')
        self.assertEqual(SITES_CSV.read_bytes(), before)

    def test_an_image_without_the_marker_is_refused(self):
        # The refusal that matters: without the marker the region is
        # unidentified, so every runtime address would be somebody else's. A
        # tool that answered anyway would produce a confident table about
        # bytes it has not identified.
        with tempfile.TemporaryDirectory() as tmp:
            blank = Path(tmp) / 'not-the-pd-image.bin'
            blank.write_bytes(b'\x00' * (128 * 1024))
            rc, out, err = run(str(blank), '--check')
            self.assertEqual(rc, 1, out + err)
            self.assertIn('marker', err)


class FixturePropertyTests(unittest.TestCase):
    """The properties, over fixtures the cases choose themselves.

    These exist because the committed image fixes where the loads are, so it
    cannot exercise the edges of the band test or the listing grade. Each case
    builds a region with the entry at a known offset and a transfer at a known
    place relative to its load.
    """

    def region_with(self, *sites):
        """A region carrying the store-back entry and `sites` at 0x0000+.

        `sites` are byte chunks placed before the entry, so a case can put a
        `mov dptr,#imm16` and a transfer three bytes apart -- or not -- without
        depending on where anything sits in the real image."""
        prefix = b''.join(sites)
        return prefix + bytes([0x00] * (ENTRY_OFFSET - len(prefix))) \
            + store_back_entry_bytes()

    def test_a_load_three_bytes_back_is_the_adjacent_one(self):
        # The property the whole reading rests on: `mov dptr,#imm16` is three
        # bytes, so a load at gap 3 is the instruction immediately before the
        # transfer. The fixture puts a decoy `mov dptr` further back and checks
        # the near one is the one reported.
        region = self.region_with(
            dptr(0x1234), b'\x00' * 4, dptr(0xFFFC),
            bytes([0x12, ENTRY_OFFSET >> 8, ENTRY_OFFSET & 0xFF]))
        rows = tool.census(region, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['dptr_loaded'], '0xFFFC')
        self.assertEqual(rows[0]['dptr_gap'], 3)
        self.assertEqual(rows[0]['dptr_signed'], '-4')

    def test_a_load_beyond_the_window_is_not_found_rather_than_guessed(self):
        # A load 40 bytes back is outside DPTR_SCAN, so the row says so in its
        # note rather than reporting the nearest load it could reach. This is
        # "not found by this method" and never a value.
        region = self.region_with(
            dptr(0x1234), b'\x00' * 37,
            bytes([0x12, ENTRY_OFFSET >> 8, ENTRY_OFFSET & 0xFF]))
        rows = tool.census(region, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['dptr_loaded'], '')
        self.assertEqual(rows[0]['dptr_gap'], '')
        self.assertEqual(rows[0]['dptr_signed'], '')
        self.assertIn('not found by this scan', rows[0]['note'])

    def test_the_signed_column_is_the_two_complement_reading_of_the_immediate(self):
        # Both edges of the sign boundary, because that is where a two's
        # complement reading and a plain hex rendering disagree -- and where a
        # row that quietly mixed the two would sort the table wrongly.
        for imm, want in ((0xFFFC, '-4'), (0xFFFF, '-1'), (0x0000, '+0'),
                          (0x0002, '+2'), (0x8000, '-32768'), (0x7FFF, '+32767')):
            with self.subTest(imm=imm):
                self.assertEqual(tool.signed_of(imm), int(want))

    def test_a_row_whose_load_is_outside_every_listing_is_graded_transfer_only(self):
        # The grade that keeps a disagreement visible. Each span below is a
        # listing's covered bytes, and the offsets are a transfer at 3 whose
        # load is at 0 -- so the first span covers the transfer and not the
        # load, which is the shape `0x7059` has in the committed tree. Grading
        # that a `both` would round a disagreement up to agreement.
        self.assertEqual(tool.listing_evidence([(3, 6)], 3, 3), 'transfer only')
        self.assertEqual(tool.listing_evidence([(0, 6)], 3, 3), 'both')
        self.assertEqual(tool.listing_evidence([(3, 6)], 9, 3), 'no')

    def test_a_site_with_no_load_is_still_a_row(self):
        # The population is the transfer, not the load. A caller that inherits
        # DPTR from its own caller is one of the 81, and dropping it would make
        # the table a census of loads rather than of callers.
        region = self.region_with(
            bytes([0x12, ENTRY_OFFSET >> 8, ENTRY_OFFSET & 0xFF]))
        rows = tool.census(region, 0)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['form'], 'lcall')
        self.assertEqual(rows[0]['dptr_loaded'], '')

    def test_band_share_is_a_share_of_the_values_given_and_of_nothing_else(self):
        # The baseline the finding rests on is a fraction of its own
        # population, so the two properties that could be got wrong are tested
        # directly: an empty population divides rather than crashing, and a
        # value outside the band is not counted as inside it.
        self.assertEqual(tool.band_share([]), 0.0)
        self.assertEqual(tool.band_share([1, -1, 1, -1]), 100.0)
        self.assertEqual(tool.band_share([0, 0]), 100.0)
        self.assertEqual(tool.band_share([tool.BAND + 1, -tool.BAND - 1]), 0.0)
        # The band's own edges are inside it, which is what makes the
        # comparison against the whole region meaningful at all.
        self.assertEqual(tool.band_share([tool.BAND, -tool.BAND]), 100.0)


class CommittedShapeTests(unittest.TestCase):
    """What the committed table and the committed tree say about themselves.

    These assert *properties* -- the columns are the tool's, the grades are
    values it defines, and every row names the region it was scanned in. They
    are deliberately not assertions about how many rows there are: a count is a
    figure every PD change moves, and this suite would then be a value the next
    commit has to edit.
    """

    def rows(self):
        with SITES_CSV.open(newline='') as f:
            return list(csv.DictReader(f))

    def test_the_header_is_the_tools_own_column_list(self):
        with SITES_CSV.open(newline='') as f:
            header = next(csv.reader(f))
        self.assertEqual(header, tool.COLUMNS)

    def test_every_row_names_the_region_it_was_scanned_in(self):
        # The calibration the tool's docstring states: a row that read as an EC
        # claim rather than a PD one would be a row about the wrong image.
        rows = self.rows()
        self.assertTrue(rows, 'the committed table parsed as empty')
        for row in rows:
            self.assertEqual(row['image'], 'pd')

    def test_every_row_carries_one_of_the_two_transfer_forms(self):
        # The population is the store-back entry's callers, and the two forms
        # are counted apart because a tail call is a different idiom from one
        # that returns. A third value would be a claim this suite cannot check,
        # so the vocabulary is held closed here rather than left to the reader.
        self.assertLessEqual({r['form'] for r in self.rows()}, {'lcall', 'ljmp'})

    def test_every_row_carries_one_of_the_three_listing_grades(self):
        # The grades are the tool's own, and the point of having three rather
        # than two is that a disagreement between what a listing covers and what
        # the byte scan found stays visible instead of being rounded up.
        self.assertLessEqual({r['in_committed_listing'] for r in self.rows()},
                             {'both', 'transfer only', 'no'})

    def test_the_signed_column_matches_the_loaded_immediate_in_every_row(self):
        # The relation between the two DPTR columns, held rather than both
        # pinned: a row whose `dptr_signed` is not the two's-complement reading
        # of its own `dptr_loaded` would make the whole comparison in the
        # write-up meaningless, and it would do so silently.
        for row in self.rows():
            if not row['dptr_loaded']:
                self.assertEqual(row['dptr_signed'], '', row)
                continue
            imm = int(row['dptr_loaded'], 16)
            self.assertEqual(int(row['dptr_signed']), tool.signed_of(imm), row)

    def test_a_row_with_a_load_also_carries_its_gap(self):
        # The adjacency claim and the gap that carries it are two cells of one
        # statement. A row that has one without the other would read as either
        # "the load is adjacent" with nothing saying how far, or the reverse.
        for row in self.rows():
            if row['dptr_loaded']:
                self.assertEqual(row['dptr_gap'], str(tool.LOAD_GAP), row)
            else:
                self.assertEqual(row['dptr_gap'], '', row)

    def test_every_row_carries_a_framing_verdict_in_the_note_vocabulary(self):
        # The notes are the tool's closed vocabulary, and a phantom is labelled
        # rather than filtered -- so an unknown value here would mean a row had
        # been dropped rather than reported.
        self.assertLessEqual({r['note'] for r in self.rows()},
                             {tool.FRAMED, tool.PARTIAL, tool.UNSYNCABLE,
                              tool.NO_LOAD.format(n=tool.DPTR_SCAN)})


class BaselineRelationTests(unittest.TestCase):
    """The comparison the finding is, held as a relation.

    The write-up's claim is that the store-back sites' immediates cluster near
    zero *against the region's own rate*, so that is what is asserted. Neither
    percentage is pinned: each is a number over the committed image that a
    change to the image would move, and pinning either would make this suite a
    value the next commit has to edit.
    """

    def shares(self):
        """(store-back share, whole-region share) as the tool's summary prints.

        Read out of the summary rather than re-derived, so what these cases
        check is the figure a reader reads. The summary wraps the sentence
        across lines to a fixed width, so the output is collapsed to one line
        before the two percentages are pulled off it; matching on the `against`
        that separates them is what keeps the two from being swapped.
        """
        rc, out, err = run(str(FIRMWARE))
        self.assertEqual(rc, 0, out + err)
        flat = ' '.join(out.split())
        site = re.search(r'inside -\S+\s+([\d.]+)% of these', flat)
        region = re.search(r'against ([\d.]+)% of', flat)
        self.assertIsNotNone(site, flat)
        self.assertIsNotNone(region, flat)
        return float(site.group(1)), float(region.group(1))

    def test_the_sites_concentrate_far_more_than_the_region_does(self):
        site_share, region_share = self.shares()
        self.assertGreater(site_share, region_share)
        self.assertEqual(site_share, 100.0)

    def test_the_region_baseline_is_far_below_the_sites(self):
        # Stated as its own case so a change that made the *region's* rate the
        # thing that moved is a separate red run from one that made the sites'
        # rate move. Both halves of the comparison are load-bearing: a claim
        # that only said "all 81 fall in the band" would be satisfied by a
        # region in which everything does.
        _site_share, region_share = self.shares()
        self.assertLess(region_share, 50.0)


if __name__ == '__main__':
    unittest.main()