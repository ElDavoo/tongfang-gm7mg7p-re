#!/usr/bin/env python3
"""Offline checks on `--spans`, the export issue #20's code/data separation is
built on: that it carries every descent the walk made, that it says so in the
file rather than only in the write-up, and that a consumer can still recover the
seed-only view it replaces.

**Why this is a separate suite from `test_bucket_c_codemap.py`.** That one holds
the terminator fixtures and the census oracle, and it is a long shared file
several branches append to; a case about the export does not belong at its end.
What is here is the property the export carries and nothing else asserts:
`write_spans()` used to iterate `seeds`, so every descent the walk reached
through a callee was in the coverage count and absent from the file, with
nothing on either side saying so.

**Every case below asserts the claim, never a census.** "Every descent the walk
made is in the export" holds whatever the seed set is; a row count holds only
until the next branch lands a seed, and CLAUDE.md's rule against counts of the
tree is the same rule. So the figures in the header are parsed back out and
compared against the walk that produced the file, never against a literal. What
*is* read from a committed artifact is the oracle below -- the
`containing_function` cells of `bucket-c-codemap.csv`, which were written down
by a census this tool does not perform and must not grade itself against.

**The negative halves are the point of half of this.** An export that emitted
*only* the callee-discovered rows would satisfy "every descent the walk reached
through a callee is here" perfectly, so each such claim is stated beside the one
that rules it out: the seed-derived rows are still there, and filtering on
`basis` gives back exactly the view the export replaced.

Nothing here needs hardware, Windows or a capture: every case is a read of the
committed image over bytes already in the tree.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).parent
# bucket_c_codemap imports disasm8051 and trace_xdata_refs by bare module name,
# so the tool directory has to be on the path before it is loaded. Same
# arrangement, and same reason, as test_bucket_c_codemap.py.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'bucket_c_codemap', HERE / 'bucket_c_codemap.py')
bcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcc)

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
COMMITTED_CSV = HERE.parent / 'annotations' / 'bucket-c-codemap.csv'

SPAN_HEAD = ["entry", "basis", "block_lo", "block_hi", "insns", "end"]

_WALK = {}


def walk():
    """`(seeds, descents)` for the committed image, walked once per process.

    `build()` descends the whole common area and takes a couple of seconds; the
    cases below all want the same walk, and re-running it per case would make
    the suite's cost a function of how many assertions it has.
    """
    if "walk" not in _WALK:
        # `build()` returns (rows, seeds, reached, descents, ...); the export
        # needs the two the walk kept apart, so they are indexed rather than
        # unpacked -- a later return value should not edit this line.
        built = bcc.build(FIRMWARE.read_bytes())
        _WALK["walk"] = (built[1], built[3])
    return _WALK["walk"]


def spans() -> str:
    """`write_spans()`'s stdout for the committed image, captured not printed."""
    seeds, descents = walk()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        bcc.write_spans(seeds, descents)
    return buf.getvalue()


def note_and_rows(text):
    """(the `#` block, the rows past it) for a captured export.

    Split the way `bank_call_regions.parse()` and `call_graph_gaps.read_rows()`
    split one, which is the whole obligation the header states: a consumer that
    does not drop the `#` lines gets the first one as its fieldnames.
    """
    lines = text.splitlines()
    note = [ln for ln in lines if ln.startswith("#")]
    body = [ln for ln in lines if not ln.startswith("#")]
    return "\n".join(note), list(csv.DictReader(body))


def header_figures(note):
    """`{label: count}` for the coverage block the header carries.

    The header lays the counts out as a right-aligned column, so the label and
    the number are read off one line together rather than matched separately --
    a consumer told to check the file against it is doing exactly this.
    """
    return {label.strip(): int(n)
            for label, n in re.findall(r"#\s{2,}([\w ]+?)\s+(\d+)\s", note)}


def is_callee(basis):
    return basis.startswith("call-from-")


class EveryDescentIsExportedTests(unittest.TestCase):
    """The general claim: nothing the walk descended is missing from the file."""

    @classmethod
    def setUpClass(cls):
        cls.seeds, cls.descents = walk()
        _, cls.rows = note_and_rows(spans())
        cls.exported = {int(r["entry"], 16) for r in cls.rows}

    def assert_all_exported(self, entries, what):
        # Names the first missing address rather than only how many: a walk
        # that lost a population loses a whole class of them, and the first one
        # is what tells a reader which class.
        missing = sorted(entries - self.exported)
        if missing:
            self.fail(f"{len(missing)} {what} absent from the export, first at "
                      f"0x{missing[0]:04X}")

    def test_every_descent_the_walk_made_is_in_the_export(self):
        # The claim, not a count: whatever `walk()` returned, `write_spans()`
        # emitted. A `write_spans()` that goes back to iterating the seeds
        # fails here, and so does one that drops a descent with no blocks.
        self.assert_all_exported(set(self.descents), "descent(s) the walk made")

    def test_every_callee_discovered_descent_is_in_the_export(self):
        # The population the old export dropped entirely, named by its basis.
        # Alone this would also pass for an export carrying *only* callee rows,
        # which is what the next case is for.
        callee = {e for e, rec in self.descents.items() if is_callee(rec.basis)}
        self.assertTrue(callee, "this image has no callee-discovered descents, "
                                "so the case after this one would pass "
                                "vacuously")
        self.assert_all_exported(callee, "callee-discovered descent(s)")

    def test_every_seed_descent_is_still_in_the_export(self):
        # The negative half of the one above: the fix added a population, it
        # did not substitute one for the other.
        self.assert_all_exported({a for a, _ in self.seeds if a in self.descents},
                                 "seed descent(s)")

    def test_every_row_carries_the_basis_of_the_descent_that_decoded_it(self):
        # That column is the only thing telling a consumer which of the two
        # populations a row came from, so it has to agree with `descents` row
        # for row rather than be re-derived from the seed set.
        for row in self.rows:
            entry = int(row["entry"], 16)
            self.assertEqual(row["basis"], self.descents[entry].basis,
                             f"0x{entry:04X}")

    def test_a_callee_row_names_a_caller_the_walk_descended_from(self):
        # `call-from-0xNNNN` is a claim about another descent and it has to be
        # one the walk made, or the column is decoration. Parsed back out of the
        # string rather than pattern-matched loosely, so a basis formatted some
        # other way fails here instead of passing as a caller.
        callers = set()
        for row in self.rows:
            if not is_callee(row["basis"]):
                continue
            head, sep, tail = row["basis"].rpartition("-0x")
            self.assertEqual((head, sep, len(tail)), ("call-from", "-0x", 4),
                             f"malformed callee basis {row['basis']!r}")
            callers.add(int(tail, 16))
        self.assertTrue(callers, "no callee-discovered row in the export")
        self.assertEqual(sorted(callers - set(self.descents)), [])


class OracleFromTheCommittedTableTests(unittest.TestCase):
    """The issue's own oracle: every descent the committed table names is here.

    `bucket-c-codemap.csv` is another artifact of the same walk and it was never
    short -- `containing_function` reads `reached`/`descents`, so it already
    carried the callee-discovered entries. That is what makes it the witness
    that the *export* was the incomplete one: cells naming a `call-from-` basis
    had no row to land in before this change. The two files are read across on
    the entry address, which is what `containing_function` holds.
    """

    @classmethod
    def setUpClass(cls):
        _, cls.span_rows = note_and_rows(spans())
        cls.basis = {int(r["entry"], 16): r["basis"] for r in cls.span_rows}
        cls.named = set()
        with open(COMMITTED_CSV, newline="") as fh:
            for row in csv.DictReader(fh):
                cell = row["containing_function"]
                if "call-from-" in cell:
                    cls.named.add(cell.split()[0])

    def test_the_committed_table_does_name_callee_discovered_descents(self):
        # The oracle has to be non-empty or every case below passes vacuously,
        # and the entries have to be callee-discovered ones specifically: a
        # seed entry was in the export all along.
        self.assertTrue(
            self.named, "no containing_function cell in the committed table "
                        "names a callee-discovered descent, so this suite is "
                        "testing nothing on this image")
        for cell in sorted(self.named):
            self.assertTrue(is_callee(self.basis[int(cell, 16)]),
                            f"{cell} is exported with a non-callee basis")

    def test_every_callee_discovered_descent_the_table_names_is_exported(self):
        missing = sorted(c for c in self.named if int(c, 16) not in self.basis)
        self.assertEqual(
            missing, [],
            f"{len(missing)} descent(s) the committed table names are absent "
            f"from the export, first at {missing[0]}" if missing else "")


class CoverageHeaderTests(unittest.TestCase):
    """The coverage statement is in the file, and it is a claim not a number.

    An export that has lost descents has to be *visibly* short, and the way to
    do that without pinning a figure the next landing seed moves is for the file
    to state the population it covers and for a case to hold that statement to
    the walk that produced it. So these assert the header's own figures are this
    run's -- the relation, not the numerals.
    """

    @classmethod
    def setUpClass(cls):
        cls.seeds, cls.descents = walk()
        cls.note, cls.rows = note_and_rows(spans())

    def test_the_export_opens_with_a_comment_block(self):
        text = spans().splitlines()
        self.assertTrue(text[0].startswith("#"),
                        "the export does not open with a `#` line, so a "
                        "consumer has no way to tell prose from data")
        first_data = next(ln for ln in text if not ln.startswith("#"))
        self.assertEqual(first_data.split(","), SPAN_HEAD)

    def test_the_headline_figures_are_this_run_s_own(self):
        figures = header_figures(self.note)
        for label in ("descents", "blocks"):
            self.assertIn(label, figures,
                          f"the header states no {label} figure: {figures}")
        self.assertEqual(figures["descents"], len(self.descents))
        self.assertEqual(figures["blocks"],
                         sum(len(rec.blocks) for rec in self.descents.values()))
        # The row count *is* the block figure, which is what makes it a coverage
        # statement about this file rather than about the walk alone: a
        # `write_spans()` emitting fewer rows than it claims fails here.
        self.assertEqual(len(self.rows), figures["blocks"])

    def test_the_header_splits_the_population_it_covers(self):
        walked = sum(1 for a, _ in self.seeds if a in self.descents)
        figures = header_figures(self.note)
        self.assertEqual(figures.get("from the seed set"), walked)
        self.assertEqual(figures.get("discovered"), len(self.descents) - walked)
        # Counted in descents, not rows: the split is a claim about entries,
        # and the two halves sum to the descent total rather than to the block
        # total the header states separately.
        self.assertEqual(figures["from the seed set"] + figures["discovered"],
                         figures["descents"])
        self.assertEqual(
            len({r["entry"] for r in self.rows if is_callee(r["basis"])}),
            figures["discovered"],
            "the export's callee-discovered entries are not the descents the "
            "walk found outside the seed set")

    def test_the_header_states_the_obligation_to_skip_it(self):
        # `csv.DictReader` does not skip a comment, so a consumer that misses
        # this gets a parse that succeeds and answers nothing. The header says
        # so rather than leaving the next consumer to find out.
        self.assertIn("csv.DictReader", self.note)
        self.assertIn("read_rows", self.note)

    def test_the_rows_are_sorted_by_entry_address(self):
        # The property that makes the file the same on every run and from every
        # branch: entries ascend. Walk order is a BFS pop order and so a
        # function of which seed was reached first, which is not a stable answer
        # to "what order are these in" once the seed set moves.
        entries = [int(r["entry"], 16) for r in self.rows]
        self.assertEqual(entries, sorted(entries))

    def test_the_export_is_the_same_on_two_runs(self):
        self.assertEqual(spans(), spans())


class FilteringRecoversTheSeedOnlyViewTests(unittest.TestCase):
    """What the export replaced is still derivable from it, with no loss.

    One output rather than two modes is the arrangement this suite keeps
    honest: a consumer that wants the seed-derived view -- which is all the
    export carried before -- filters on `basis` and gets exactly it back.
    """

    @classmethod
    def setUpClass(cls):
        cls.seeds, cls.descents = walk()
        _, cls.rows = note_and_rows(spans())
        cls.callee = [r for r in cls.rows if is_callee(r["basis"])]
        cls.seed_only = [r for r in cls.rows if not is_callee(r["basis"])]

    def test_filtering_on_basis_reproduces_the_block_set_per_seed(self):
        # Compared as whole rows built from `descents` rather than as a count,
        # so this asserts the rows agree and not that there happen to be the
        # same number of them. `insns` is formatted rather than passed through
        # because the row comes back out of a `csv.DictReader`, where every
        # cell is text -- a bare int here would compare unequal to a row that is
        # in fact right.
        want = []
        for entry, basis in self.seeds:
            rec = self.descents.get(entry)
            if rec is None:
                continue
            for lo, pcs, _ in rec.blocks:
                want.append((f"0x{entry:04X}", basis, f"0x{lo:04X}",
                             f"0x{pcs[-1]:04X}", str(len(pcs)), rec.terminal))
        got = [tuple(r[col] for col in SPAN_HEAD) for r in self.seed_only]
        self.assertEqual(got, want)

    def test_the_two_populations_partition_the_rows(self):
        # Disjoint by basis, so the filter cannot both keep and drop a row --
        # and a non-empty callee half is what stops the case above proving
        # anything with a filter that removed nothing.
        self.assertTrue(self.callee,
                        "no callee-discovered rows, so the filter above was a "
                        "no-op and proved nothing")
        self.assertEqual(len(self.seed_only) + len(self.callee), len(self.rows))


class CommittedTableTests(unittest.TestCase):
    """The fix is in the export, so the committed table does not move.

    `csv_text()` reads `codemap.reason_for()`, which reads `reached`/`descents`
    -- already the whole walk, before and after. Asserted here because a later
    change that quietly re-derived verdicts from the seed set would move the
    table, and a consumer of the table would see that before anyone ran
    `--check`.
    """

    def test_the_committed_table_is_still_what_this_run_derives(self):
        self.assertEqual(bcc.csv_text(FIRMWARE.read_bytes()),
                         COMMITTED_CSV.read_text())


if __name__ == "__main__":
    unittest.main()