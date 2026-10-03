#!/usr/bin/env python3
"""`pd-direct-offset-sites.csv` is derived, and this runs the derivation that holds it.

`ec/annotations/pd-direct-offset-sites.csv` is the committed table of every
candidate site in the PD image that writes the direct `0x0D`/`0x0E` pair, or
that reaches the `0x1253` pointer add through an `lcall`/`ljmp`.
`ec/tools/pd_direct_offset_sites.py` re-derives it from the committed firmware
image and `--check` diffs the two, byte for byte.

**The gap this fills.** That `--check` existed and nothing ran it. It was not
in `.github/scripts/agent-gates.sh`, no `.github/workflows/` file called it, no
`test_*.py` invoked it, and no other tool runs the mode or reads the table --
so the mode that would catch a drifted row was itself the thing nothing
called, which is the shape `docs/agent-pipeline.md` item 4 records for the arms
it has prepared and not landed. The one other file naming
`pd_direct_offset_sites.py` is `pd_dispatch_key.py`, and it names it in
`pd_region()`'s docstring to say why the two keep the same PD region lookup
separately: a cross-reference about a shared convention, not a hold on the
table. A hand edit of a row, a re-cut of the scan after a rename, a
regenerated firmware image: each would have merged green with the table
describing the PD image no longer.

The sibling holds are wired and this one was not, which is what makes it the
instance rather than a shape. `call_graph.py --check` is a cheap-tier gate arm
holding `call-graph-callees.csv`; `verify_gap_text.py --check` and
`dsdt_ec_fields.py --csv --check` are each run by the tool's own suite as a
subprocess. This one had neither.

**What is checked.** Both of the tool's modes are run as subprocesses over the
committed tree, so what a case sees is the exit code a reader gets rather than a
value this file computed:

1. `--csv --check` against the committed table exits 0 -- the table is what the
   committed image derives, so a row that stopped being true is a red run.
2. `--self-test` exits 0 -- the decodes, the three populations and the bank
   selection are what the tool's own oracles hold them to.
3. **The negative controls, which are the substance.** A `--check` that cannot
   fail is not a check, and every positive case above is also satisfied by a
   comparison that reads nothing. So a doctored cell is red and its diff names
   the row; a missing table is red rather than silently created; the unaltered
   copy of the same table beside each red is green, because a check that is red
   on everything passes all of them. These run as subprocesses over `tempfile`
   copies through `--check PATH`, so the tool reads a file this suite made and
   the committed table is never written.

**What a green run is not.** It says the committed table is what this run
derives from the committed image, and that the tool's own self-test holds. It
does not say the scan is complete: the tool's docstring is explicit that a byte
scan over the region both over-counts (a `75 0D` inside a data table reads as
`mov 0x0d,#imm`) and under-counts (a call reached through a dispatch table
carries no target bytes), so an empty caller list is "not found by this method"
and never "nothing calls it". A row that this suite would not notice changing
is a row the tool declined to label; the four `form` values and the three
`note` values are what it says about itself.

Nothing here observes hardware. The suite reads two committed files -- the
firmware image and the table -- and no EC is opened, no register is read back
and no live test ran. Every figure in the committed table is a static count over
the committed image, which is the tool's own claim and this suite's too.
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
TOOL = HERE / 'pd_direct_offset_sites.py'
FIRMWARE = REPO / 'ec' / 'firmware' / 'GMxMGxx_11.800'
SITES_CSV = REPO / 'ec' / 'annotations' / 'pd-direct-offset-sites.csv'


def run(*args):
    """Run the tool and return (returncode, stdout, stderr).

    A subprocess rather than an import, so what the cases below assert on is the
    exit code a reader gets rather than a value this file produced itself. Every
    positive case in this suite is also satisfied by a comparison that reads
    nothing, which is the failure the negative controls exist for.
    """
    cmd = [sys.executable, str(TOOL)] + list(args)
    p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def committed_copy(tmpdir, mutate=None):
    """A byte-identical copy of the committed table, with `mutate` applied.

    Copied as bytes rather than re-rendered: the committed table carries the csv
    module's own CRLF terminator, and `trace_xdata_refs.check_table` reads with
    `newline=""` precisely so a checkout that rewrote the terminators is
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


def doctor_one_immediate(raw):
    """Change one cell of one row; every other cell is untouched.

    One cell rather than a whole row, so the diff `--check` prints names the
    field that moved instead of a row that vanished. This is the shape a hand
    edit takes, and it is the case a suite holding only the row *count* passes.

    Parsed and re-rendered with the csv module rather than split on `,`,
    because a row's `text` cell is quoted and contains a comma of its own
    (`"mov  0x0d,#0x27"`); a naive split would count that comma as a column and
    edit the wrong field while still producing a difference. Re-rendering is
    safe for the control to stay meaningful because the whole table is rewritten
    in the writer's own dialect, so an unaltered table re-renders to the bytes
    already committed -- which `test_an_unaltered_copy_is_green` asserts.
    """
    text = raw.decode('utf-8')
    rows = list(csv.reader(io.StringIO(text, newline='')))
    header, column = rows[0], rows[0].index('immediate')
    for row in rows[1:]:
        if len(row) == len(header) and row[column]:
            row[column] = '0xDE' if row[column] != '0xDE' else '0x27'
            break
    else:
        raise AssertionError('no row carries an `immediate` to alter')
    out = io.StringIO(newline='')
    csv.writer(out, lineterminator='\r\n').writerows(rows)
    return out.getvalue().encode('utf-8')


class DerivedTableTests(unittest.TestCase):
    """The two modes, run the way a reader runs them."""

    def test_the_committed_table_is_what_the_committed_image_derives(self):
        # The whole of the hold. `--csv --check` re-derives the table from
        # `ec/firmware/GMxMGxx_11.800` and diffs it against the committed file
        # byte for byte, so a row that no longer describes the PD image fails
        # here rather than in prose.
        rc, out, err = run(str(FIRMWARE), '--csv', '--check')
        self.assertEqual(rc, 0, out + err)

    def test_the_tools_own_self_test_holds(self):
        # `--self-test` is the other half, and it needs no image: it checks the
        # decodes and the three populations against the committed transcripts.
        rc, out, err = run('--self-test')
        self.assertEqual(rc, 0, out + err)


class NegativeControlTests(unittest.TestCase):
    """The check failing when it should, and passing when it should.

    Every case here is a mutation of the *input to the check* rather than of the
    tool, because a mutation of the tool would be testing the mutation. The
    unaltered copy runs beside each red for the reason in `run()`: a check that
    reports a difference for everything passes all of the reds below.
    """

    def test_a_doctored_cell_is_red_and_the_diff_names_the_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = committed_copy(tmp, doctor_one_immediate)
            rc, out, err = run(str(FIRMWARE), '--csv', '--check', str(path))
            self.assertEqual(rc, 1, out + err)
            # The failure has to say which row moved, or it is a red run that
            # tells a reader nothing about what to regenerate.
            self.assertIn('-direct,pd,0x20514', err)

    def test_an_unaltered_copy_is_green_beside_the_doctored_one(self):
        # The control. Without it, `test_a_doctored_cell_is_red...` is also
        # satisfied by a `--check` that always exits 1.
        with tempfile.TemporaryDirectory() as tmp:
            path = committed_copy(tmp)
            rc, out, err = run(str(FIRMWARE), '--csv', '--check', str(path))
            self.assertEqual(rc, 0, out + err)

    def test_a_missing_table_is_red_and_is_not_created(self):
        # The failure the tool's own docstring calls out: a `--check` that
        # creates what it is checking turns a missing artifact into a green
        # run and then leaves a file behind for the next commit to trust.
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / 'absent.csv'
            rc, out, err = run(str(FIRMWARE), '--csv', '--check', str(absent))
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
            rc, out, err = run(str(FIRMWARE), '--csv', '--check', str(path))
            self.assertEqual(rc, 1, out + err)

    def test_nothing_here_wrote_the_committed_table(self):
        # The hold is only worth having if the case that runs it leaves the
        # artifact alone. Compared by bytes, because a rewrite that preserved
        # the parsed rows would still be a tool writing to a committed input.
        before = SITES_CSV.read_bytes()
        run(str(FIRMWARE), '--csv', '--check')
        run('--self-test')
        self.assertEqual(SITES_CSV.read_bytes(), before)


class CommittedShapeTests(unittest.TestCase):
    """What the committed table says about itself, held as a property.

    These assert that the table's *vocabulary* is intact -- the columns are the
    tool's, the row forms are the four it distinguishes, and every row names the
    region it was scanned in. They are deliberately not assertions about how
    many rows there are: a count is a figure every PD change moves, and this
    suite would then be a value the next commit has to edit.
    """

    def test_the_header_is_the_tools_own_column_list(self):
        with SITES_CSV.open(newline='') as f:
            header = next(csv.reader(f))
        sys.path.insert(0, str(HERE))
        import pd_direct_offset_sites as tool
        self.assertEqual(header, tool.COLUMNS)

    def test_every_row_names_the_region_it_was_scanned_in(self):
        # The calibration the tool's docstring states: a row that read as an EC
        # claim rather than a PD one would be a row about the wrong image.
        with SITES_CSV.open(newline='') as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(rows, 'the committed table parsed as empty')
        for row in rows:
            self.assertEqual(row['image'], 'pd')

    def test_every_row_carries_one_of_the_four_forms_the_tool_distinguishes(self):
        # Direct-form and register-form mean the same bytes and are kept apart
        # because PSW.RS decides; the two transfer forms are the `0x1253`
        # callers. A fifth value would be a claim this suite cannot check, so
        # the vocabulary is held closed here rather than left to the reader.
        with SITES_CSV.open(newline='') as f:
            rows = list(csv.DictReader(f))
        self.assertLessEqual({r['form'] for r in rows},
                             {'direct', 'register', 'lcall', 'ljmp'})

    def test_a_direct_form_row_writes_the_pair_its_opcode_names(self):
        # The distinction that keeps the table readable: a direct-form row is
        # `0x0D`/`0x0E` whatever PSW says, so the byte its opcode writes has to
        # be one of the pair. The offset into the opcode bytes is the tool's own
        # `DIRECT_DST`, read rather than re-spelled -- `75 0d 27` carries its
        # destination in the middle byte and `f5 0d` in the last, so a suite
        # guessing the position would be asserting the wrong field on one of the
        # two shapes and passing on the other by luck.
        sys.path.insert(0, str(HERE))
        import pd_direct_offset_sites as tool

        with SITES_CSV.open(newline='') as f:
            rows = [r for r in csv.DictReader(f) if r['form'] == 'direct']
        self.assertTrue(rows, 'no direct-form row to check')
        for row in rows:
            opcodes = [int(b, 16) for b in row['opcodes'].split()]
            offset = tool.DIRECT_DST.get(opcodes[0])
            self.assertIsNotNone(
                offset, 'a direct-form row whose opcode carries no direct '
                       'destination: %r' % (row,))
            self.assertIn(opcodes[offset], (0x0D, 0x0E),
                          'a direct-form row whose opcodes do not write '
                          '0x0D/0x0E: %r' % (row,))


if __name__ == '__main__':
    unittest.main()