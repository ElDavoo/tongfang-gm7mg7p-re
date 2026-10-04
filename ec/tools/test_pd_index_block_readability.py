#!/usr/bin/env python3
"""Offline checks for pd_index_block_readability.py. No EC is opened and no
capture is read: the tool's whole subject is two committed files, and these
tests hold its derivation to them and to the document that quotes it.

What this stands in for is the question a human at the machine cannot be asked
twice: **which of the PD image's record bases this host can read at all.** That
question has a per-stride answer the procedure document prints as a table, and
a table in a document is exactly the shape CLAUDE.md says goes stale silently
-- the next merge that moves a base leaves it reading as a complete result. So
the relations here are the ones that break loudly when the inputs move:

  * the split agrees with the window, in both directions, for every base -- so a
    base the tool calls unreadable really is outside the window and one it calls
    readable really is inside, rather than the two being independently wrong;
  * the procedure document's two tables are what this run derives from the
    committed CSV and the window constant, so a re-run of
    `pd_index_geometry.py --bases` that moves a base fails here instead of
    leaving a stale table behind -- and a stale *slot* table, which is the one
    carrying the reachable-length figures, is refused as loudly as a stale
    split table, because a document quoting a length no `--addrs` reproduces
    is the same defect as one quoting a base count that has moved;
  * what the tool counts reachable is exactly what `ec_timer_capture`'s own
    guard accepts, address by address and in both directions, and the fan page
    is never counted -- "inside the window" and "readable by a capture" are
    different questions, and only the second one is one an operator can act on;
  * the fan-page split the procedure specifies is what the capture tool's own
    guard accepts, which is the property that makes the requested block
    sampleable at all;
  * the record stride is claimed only for the families the committed census
    counts a `0x200x` page term for, which is what stops `base + 0x260` from
    being printed beside a `0x5E` base as though it were that family's layout.

Nothing here asserts a count of the repository. The figures asserted are
over committed firmware -- bases, addresses, window edges -- which is the case
CLAUDE.md allows, and each is stated as a relation between two derived values
rather than as a census of the tree.
"""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

spec = importlib.util.spec_from_file_location(
    'pd_index_block_readability', HERE / 'pd_index_block_readability.py')
pib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pib)

# The capture tool this one shares its window with, imported rather than
# restated: the whole claim is that `HOST_WINDOW` is the same constant the
# capture tool's guard refuses on, and a copy here would be a second one to
# drift. Imported by name rather than through `spec_from_file_location` so that
# it is the *same module object* `pd_index_block_readability` imported -- a
# second load under another name would be a second module with its own copy of
# the constant, and `assertIs` below would fail for that reason alone.
import ec_timer_capture as capture

REPO = HERE.parent.parent
PROCEDURE = REPO / 'docs' / 'hardware-tests' / 'pd-index-geometry-live.md'

# The block the procedure samples. `pd-index-geometry.md` section 3.3's
# contiguous-field-offset bases plus the rest of the low run: written out here
# rather than derived, because what is under test is that this range is the one
# the capture tool accepts -- a test that computed the range would agree with
# whatever the tool did.
BLOCK = (0x0400, 0x04A8)
# `ec_timer_capture.FAN_PAGE` sits inside BLOCK, so the range as the issue
# writes it is refused by the tool's own guard. The split below is what the
# procedure has to specify instead, and this test is what holds it to that.
SPLIT = '0x0400-0x045f,0x0470-0x04a8'


class WindowAgreementTests(unittest.TestCase):
    """The split is a function of the window, in both directions.

    The tool could label every base readable and still be a pure function of
    its two inputs; these are the checks that make the *labels* mean what the
    procedure says they mean.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = pib.split(pib.load_strides())

    def test_the_window_is_the_capture_tools_own_constant(self):
        # The claim the whole tool rests on: these are the same pages
        # `ec_timer_capture.py` refuses an out-of-window address against, not
        # a second reading of the census. If the capture tool's guard ever
        # moves, this is the red that stops the two from disagreeing about
        # which addresses are sampleable.
        self.assertIs(pib.HOST_WINDOW, capture.HOST_WINDOW)
        self.assertIs(pib.in_window, capture.in_window)

    def test_an_unreadable_base_is_really_outside_the_window(self):
        for stride, row in self.rows.items():
            for base in row['bases']:
                if not pib.readable_at(base, 0):
                    self.assertFalse(pib.in_window(base),
                                     f"{stride} base 0x{base:04X}")

    def test_a_readable_base_is_really_inside_the_window(self):
        for stride, row in self.rows.items():
            for base in row['bases']:
                if pib.readable_at(base, 0):
                    self.assertTrue(pib.in_window(base),
                                    f"{stride} base 0x{base:04X}")

    def test_the_split_partitions_every_base_exactly_once(self):
        # The relation, not the census: read plus not-read is the base list,
        # for every family. A base counted twice would print as both.
        for stride, row in self.rows.items():
            readable = set(row['readable'][0])
            unreadable = {b for b in row['bases'] if not pib.readable_at(b, 0)}
            self.assertEqual(readable & unreadable, set(), stride)
            self.assertEqual(readable | unreadable, set(row['bases']), stride)

    def test_what_is_counted_reachable_is_what_the_capture_guard_accepts(self):
        # The property the whole tool rests on, in both directions and address
        # by address: `reachable_addrs` names exactly the bytes of a record
        # that `ec_timer_capture.check_addrs` will not refuse. Held over the
        # walk rather than a length's worth, because a count is the claim that
        # goes stale -- a record cut by the window edge and a record cut by the
        # fan page are both "short of 608", and only the address list says
        # which bytes each one lost.
        #
        # The walk stops at the first byte outside the window, so a record
        # beginning outside it contributes nothing even where its later bytes
        # re-enter the mapping at `0x0C00`: those are not bytes a sequential
        # sweep over this record walks through. That is why the expected set
        # runs to the window edge rather than over the whole record.
        for stride, bases in pib.load_strides():
            for base in bases:
                for slot in range(pib.SLOTS):
                    start = pib.slot_start(base, slot)
                    walked = 0
                    while (walked < pib.RECORD_STRIDE
                           and pib.in_window(start + walked)):
                        walked += 1
                    want = {a for a in range(start, start + walked)
                            if capture.check_addrs([a]) is None}
                    got = set(pib.reachable_addrs(base, slot))
                    self.assertEqual(got, want,
                                     f"{stride} 0x{base:04X} slot {slot}")
                    self.assertEqual(pib.reachable_bytes(base, slot), len(got),
                                     f"{stride} 0x{base:04X} slot {slot}")

    def test_the_fan_page_is_never_counted_reachable(self):
        # The negative that gives the check above teeth. A `reachable_bytes`
        # that walked straight through `0x0460`-`0x046F` would agree with
        # `in_window` on every byte and still report a record as covered that
        # the capture tool refuses to read, which is the overclaim this suite
        # exists to catch.
        for stride, bases in pib.load_strides():
            for base in bases:
                for slot in range(pib.SLOTS):
                    for addr in pib.reachable_addrs(base, slot):
                        self.assertNotIn(addr, capture.FAN_PAGE,
                                         f"0x{addr:04X} counted reachable")

    def test_a_record_spanning_the_fan_page_is_not_reported_as_whole(self):
        # The specific figure the reviewer's finding is about, on the committed
        # data: a slot-0 record covering `0x0460`-`0x046F` loses exactly those
        # sixteen bytes, so it is short of the stride however far into the
        # record they sit. Written as the relation (whole iff every byte of the
        # record is sampleable) rather than as the number, which the derivation
        # owns, so it holds on any host whose window differs from this one.
        for stride, bases in pib.load_strides():
            for base in bases:
                for slot in range(pib.SLOTS):
                    start = pib.slot_start(base, slot)
                    whole = pib.reachable_bytes(base, slot) == pib.RECORD_STRIDE
                    every = all(pib.sampleable(a) for a in
                                range(start, start + pib.RECORD_STRIDE))
                    self.assertEqual(whole, every,
                                     f"{stride} 0x{base:04X} slot {slot}")


class RecordStrideScopeTests(unittest.TestCase):
    """`0x260` is the record stride of the paged families and of no other.

    `pd-index-geometry.md` 7.4 says it outright, and the census's own
    `sites_with_page_term` column is the data behind it. Printing `base +
    0x260` beside a `0x5E` base would be arithmetic dressed as that family's
    layout, which is the overclaim this suite exists to prevent.
    """

    def test_the_paged_families_are_the_ones_the_census_counts(self):
        from_csv = {stride for stride, bases in pib.load_strides()
                    if stride != pib.UNRESOLVED and pib.paged_sites(stride)
                    and bases}
        self.assertEqual(set(pib.PAGED_STRIDES), from_csv)

    def test_a_family_without_a_page_term_is_not_placed_at_a_higher_slot(self):
        # The negative, on the tool's own output: the slot table names only the
        # paged families. A `0x5E` row in it would be a layout claim 7.4
        # excludes.
        out = io.StringIO()
        pib.print_slots(out)
        named = {line.split("|")[1].strip().strip("`")
                 for line in out.getvalue().splitlines()
                 if line.startswith("| `")}
        self.assertEqual(named, set(pib.PAGED_STRIDES))

    def test_slot_zero_needs_no_stride_and_so_covers_every_family(self):
        # The other half: the slot-0 readability of a base is a statement about
        # the address alone, so it is a claim for the `0x08xx` families too.
        # Restricting the split table to the paged families would drop the very
        # rows the procedure needs to say what it cannot sample.
        out = io.StringIO()
        pib.print_table(out)
        for stride, bases in pib.load_strides():
            if stride == pib.UNRESOLVED:
                continue
            self.assertIn(f"`{stride}`", out.getvalue())


class FanPageTests(unittest.TestCase):
    """The block the procedure samples, as the capture tool's guard sees it.

    The issue's block spec spans the fan page `0x0460`-`0x046F` (issue #94),
    which `ec_timer_capture.py` refuses. These hold the split the procedure
    specifies, because a procedure that printed the range as filed would send
    an operator to a command that refuses before it reads anything.
    """

    def test_the_range_as_written_is_refused_by_the_capture_tools_guard(self):
        addrs = capture.parse_addrs(f"{BLOCK[0]:#06x}-{BLOCK[1]:#06x}")
        self.assertIsNotNone(capture.check_addrs(addrs))

    def test_the_split_is_accepted_by_the_capture_tools_guard(self):
        addrs = capture.parse_addrs(SPLIT)
        self.assertIsNone(capture.check_addrs(addrs))

    def test_the_split_is_the_range_less_exactly_the_fan_page(self):
        # The relation, and the reason the procedure can say the split differs
        # from the requested range by the fan page and nothing else: dropping
        # those addresses is the whole of the difference.
        block = set(capture.parse_addrs(f"{BLOCK[0]:#06x}-{BLOCK[1]:#06x}"))
        split = set(capture.parse_addrs(SPLIT))
        self.assertEqual(block - split, set(capture.FAN_PAGE))

    def test_every_base_of_the_block_is_in_the_split(self):
        # The half that makes the split usable: the bases the procedure's
        # prediction rests on all survive the carve-out, so nothing in the
        # record geometry is lost to it.
        split = set(capture.parse_addrs(SPLIT))
        for stride, bases in pib.load_strides():
            if stride != '0x60':
                continue
            for base in bases:
                if BLOCK[0] <= base <= BLOCK[1]:
                    self.assertIn(base, split, f"0x{base:04X}")


class DocumentTableTests(unittest.TestCase):
    """The procedure document's table against what this run derives.

    A table in a document is a figure of a derived thing, and CLAUDE.md's rule
    about figures is that they go stale silently. `--check` is the tool for
    it; these hold that the document's copy is the one `--check` would accept,
    so the check has a real document to run against and not only a fixture.
    """

    def test_the_procedure_document_exists_and_is_checkable(self):
        self.assertTrue(PROCEDURE.is_file(), PROCEDURE)
        self.assertEqual(pib.check_document(str(PROCEDURE)), 0)

    def test_a_table_that_disagrees_with_the_derivation_is_refused(self):
        # The negative that gives `--check` teeth. Without it, a check that
        # always returned 0 would pass this document too. Exit 1 rather than a
        # raise: the refusal is a gate's verdict, and the one case that raises
        # is the unparseable table below.
        with open(PROCEDURE, encoding='utf-8') as f:
            text = f.read()
        line = next(l for l in text.splitlines()
                    if l.startswith("| `0x04`"))
        # A *well-formed* row carrying the wrong figure. A malformed one would
        # be refused too -- `_document_table` drops a row that is not four
        # cells, so it would go missing from the comparison -- but it would be
        # reported as a row the derivation has and the document does not,
        # which is a different complaint than the one a wrong figure deserves.
        broken = text.replace(line, line.replace("| 2 | 2 | 0 |", "| 9 | 2 | 0 |"))
        self.assertNotEqual(broken, text, "the fixture edit changed nothing")
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False,
                                         encoding='utf-8') as f:
            f.write(broken)
            name = f.name
        try:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(pib.check_document(name), 1)
            # The refusal names both sides, or an operator cannot tell which
            # number to go and look at.
            self.assertIn("document:", err.getvalue())
            self.assertIn("derived:", err.getvalue())
        finally:
            os.unlink(name)

    def test_a_stale_slot_table_is_refused(self):
        # The failure this check exists for, on the row it is most able to get
        # wrong. The split table says how many *bases* are readable and moves
        # only when a base moves; the slot table carries the reachable-length
        # figure, and a document quoting `608-608` where the derivation says
        # `592-608` is quoting a length no `--addrs` argument reproduces. A
        # `--check` that read only the split table would let exactly that
        # through, so the edit below leaves the split table untouched and only
        # the slot one stale.
        with open(PROCEDURE, encoding='utf-8') as f:
            text = f.read()
        want = pib.slot_table_lines()
        self.assertTrue([w for w in want if w[3] != "--"],
                        "the derivation printed no slot ranges at all")
        line = next(l for l in text.splitlines()
                    if l.startswith("| `0x60` | 0 |"))
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        stale = cells[3]
        self.assertIn("-", stale, f"no range in the document's row: {line}")
        broken = text.replace(line, line.replace(stale, "608-608"))
        self.assertNotEqual(broken, text, "the fixture edit changed nothing")
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False,
                                         encoding='utf-8') as f:
            f.write(broken)
            name = f.name
        try:
            with contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(pib.check_document(name), 1)
            # And it names the row, not just the table, so the operator knows
            # which figure to go and re-derive.
            self.assertIn("608-608", err.getvalue())
            self.assertIn("slot table", err.getvalue())
        finally:
            os.unlink(name)

    def test_a_document_with_no_table_raises_rather_than_passing(self):
        # The vacuity guard: a document whose table could not be parsed must be
        # a red run and not an empty list the check agrees with.
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False,
                                         encoding='utf-8') as f:
            f.write("# no table here\n\nProse instead.\n")
            name = f.name
        try:
            with self.assertRaises(SystemExit):
                pib.check_document(name)
        finally:
            os.unlink(name)

    def test_the_parsed_table_is_every_resolved_stride_and_nothing_else(self):
        with open(PROCEDURE, encoding='utf-8') as f:
            found = pib._document_table(f.read())
        derived = [s for s, _ in pib.load_strides() if s != pib.UNRESOLVED]
        self.assertEqual([s for s, _ in found], derived)

    def test_the_two_document_tables_are_read_apart(self):
        # `--check` reads two tables out of one document by row shape, so the
        # shapes have to be disjoint or one check silently reads the other's
        # rows and compares a range against a count. Both directions: a slot
        # row is not a split row, and a split row is not a slot row, including
        # the `--` row a slot with no readable base produces.
        rows = [
            ("| `0x60` | 0 | 37 | 592-608 |", True),
            ("| `0x60` | 2 | 0 | -- |", True),
            ("| `0x04` | 2 | 2 | 0 |", False),
            ("| `0x5E` | 9 | 0 | 9 |", False),
        ]
        for line, is_slot in rows:
            self.assertEqual(bool(pib._document_slot_table(line)), is_slot,
                             f"slot parse of {line}")
            self.assertEqual(bool(pib._document_table(line)), not is_slot,
                             f"split parse of {line}")

    def test_the_document_slot_table_is_what_the_tool_would_print(self):
        # Held by row rather than by the surrounding prose, so a caption edit
        # that leaves the table correct is not a failure and a table edit that
        # leaves the caption correct is.
        with open(PROCEDURE, encoding='utf-8') as f:
            found = pib._document_slot_table(f.read())
        self.assertEqual(found, list(pib.slot_table_lines()))


class KnownAnswerTests(unittest.TestCase):
    """The committed facts the write-up and the procedure both rest a sentence
    on, run through the tool's own `--self-test` so that entry point is covered
    rather than only the functions behind it."""

    def test_the_self_test_passes(self):
        self.assertEqual(pib.self_test(), 0)

    def test_the_self_test_is_not_vacuous(self):
        # A list of lambdas that all return a truthy constant would pass every
        # time and say nothing. Inverting each one has to make it fail.
        rows = pib.split(pib.load_strides())
        for what, holds in pib.SELF_TEST:
            self.assertTrue(holds(rows), what)

    def test_the_paged_block_bases_are_all_readable_and_their_slot_two_is_not(self):
        # The two facts the procedure's two-index arm and its fan-page split
        # both rest on, read straight off the committed CSV.
        row = pib.split(pib.load_strides())['0x60']
        self.assertTrue(row['readable'][0])
        self.assertEqual(row['readable'][2], [])


if __name__ == '__main__':
    unittest.main()