#!/usr/bin/env python3
"""Offline checks for callee_dptr_sites.py, the resolver that answers "is the
DPTR behind this `movx` named anywhere the other two methods can see?".

The tool exists because two committed methods were blind at the same two
sites and `check_site_census.py` read that as agreement, so what is pinned
here is the resolution itself: that `0xD319` really does leave DPTR at `0x0860`
for its two callers, that the walk refuses to answer where it cannot, and that
the committed table is what this run produces. The walk's own decision cases
live in the tool's `--self-test`, which the suite runs rather than repeating;
what is here is everything a reader of the table would otherwise have to take
on trust.

Committed files only, no firmware decode and no network.
"""
import builtins
import contextlib
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import callee_dptr_sites as cds  # noqa: E402

TREE = cds.Tree()
ROWS, UNPLACED = cds.rows(TREE)


def where(offset):
    """The one emitted row at a file offset, or None."""
    for row in ROWS:
        if row["file_offset"] == offset:
            return row
    return None


def emitted():
    """The `movx` rows, without the call-site rows whose `movx` cell is empty."""
    return [r for r in ROWS if r["movx"]]


class ResolvesThePage(unittest.TestCase):
    """The two stores the issue is about, and the four the page already had."""

    def test_both_stores_behind_lcall_0xd319_resolve_to_0x0860(self):
        # The load is inside the callee, so neither committed method's own
        # rule reaches it. If this stops holding the two rows are the whole
        # finding and it is gone.
        for offset in ("0x0D191", "0x0D249"):
            got = where(offset)
            self.assertIsNotNone(got, offset)
            self.assertEqual(got["dptr_source"], "callee", offset)
            self.assertEqual(got["xdata_addr"], "0x0860", offset)
            self.assertEqual(got["helper"], "0xD319", offset)
            self.assertEqual(got["movx"], "write", offset)

    def test_they_are_writes_and_not_reads(self):
        # `0xD319` returns a masked byte in A and the caller stores A on the
        # zero branch, so a `read` here would mean the walk found the wrong
        # instruction rather than the wrong address.
        for offset in ("0x0D191", "0x0D249"):
            self.assertTrue(where(offset)["movx"].startswith("w"), offset)

    def test_the_two_stores_the_sweep_already_found_are_still_literal(self):
        for offset in ("0x0D286", "0x0D28D"):
            got = where(offset)
            self.assertIsNotNone(got, offset)
            self.assertEqual(got["xdata_addr"], "0x0860", offset)
            self.assertEqual(got["movx"], "write", offset)
        self.assertEqual(where("0x0D286")["dptr_source"], "predecessor")
        self.assertEqual(where("0x0D28D")["dptr_source"], "literal")

    def test_every_address_the_table_puts_on_the_page_is_on_the_page(self):
        for row in emitted():
            if not row["xdata_addr"]:
                continue
            addr = int(row["xdata_addr"], 16)
            self.assertTrue(cds.PAGE_LO <= addr <= cds.PAGE_HI, row)

    def test_no_unresolved_row_carries_an_address(self):
        # The shape the whole tool exists to keep: "not established" and
        # "established" are different cells, and a row that has both would
        # read as a measured answer.
        for row in ROWS:
            if row["dptr_source"] == "unresolved":
                self.assertEqual(row["xdata_addr"], "", row)

    def test_the_directions_are_the_ones_the_listings_show(self):
        for row in emitted():
            self.assertIn(row["movx"], ("read", "write"), row)


class ThePageIsNotOnlyThisSite(unittest.TestCase):
    """Issue item 3: one site or the page. Both, and the two differ in address."""

    def test_the_same_shape_recurs_on_other_addresses_of_the_page(self):
        chased = {r["xdata_addr"] for r in emitted()
                  if r["dptr_source"] == "callee"}
        self.assertIn("0x0860", chased)
        self.assertTrue(chased - {"0x0860"},
                        "expected the callee-set shape to reach other page "
                        "addresses as well as 0x0860")

    def test_no_callee_set_row_on_the_page_is_left_unresolved(self):
        # Every callee-set `movx` this tool placed on the page is placed by
        # resolution rather than by leaving a hole, so the count of callee-set
        # rows and the count of callee-set rows carrying an address cannot
        # drift apart.
        for row in emitted():
            if row["dptr_source"] == "callee":
                self.assertNotEqual(row["xdata_addr"], "", row)

    def test_the_other_page_helpers_leave_a_different_dptr(self):
        # The reason 0x0860 is not simply "the page": 0xBD34, 0xBD3D and
        # 0xBC7E are chased too and none of them lands on 0x0860.
        helpers = {r["helper"] for r in emitted()
                   if r["dptr_source"] == "callee" and r["helper"]}
        self.assertIn("0xD319", helpers)
        for helper in helpers - {"0xD319"}:
            self.assertNotIn(
                "0x0860",
                {r["xdata_addr"] for r in emitted() if r["helper"] == helper},
                helper)


class TheCallSiteNoListingCovers(unittest.TestCase):
    """`0x0D1E3`: a committed `lcall 0xD319` in bytes no listing reaches."""

    def test_it_is_a_row_with_no_movx_and_no_listing(self):
        got = where("0x0D1E3")
        self.assertIsNotNone(got)
        self.assertEqual(got["listing"], "")
        self.assertEqual(got["movx"], "")
        self.assertEqual(got["dptr_source"], "unresolved")
        self.assertEqual(got["helper"], "0xD319")

    def test_it_is_not_counted_as_a_resolved_movx(self):
        # The distinction the table's two row kinds exist to keep: a booked
        # transfer is not a decoded access, and a row that made it into the
        # `movx` population would put a fifth store on a page whose stores are
        # counted elsewhere.
        self.assertNotIn("0x0D1E3", {r["file_offset"] for r in emitted()})

    def test_its_two_listed_siblings_are_covered_and_so_are_not_rows(self):
        # `bank-call-targets.csv` books three; a listing covers two of them.
        # Those two are absent from this table for the complementary reason:
        # a call site a listing covers is already a `callee` row.
        for offset in ("0x0D18C", "0x0D244"):
            self.assertTrue(TREE.covered_by("bank0", int(offset[2:], 16)),
                            offset)
            self.assertIsNone(where(offset), offset)
        self.assertFalse(TREE.covered_by("bank0", 0x0D1E3))

    def test_a_call_site_row_only_appears_for_a_helper_this_tool_chased(self):
        chased = {r["helper"] for r in emitted() if r["helper"]}
        for row in ROWS:
            if not row["movx"]:
                self.assertIn(row["helper"], chased, row)


class WhatIsNotACensus(unittest.TestCase):
    """The calibration the summary line and the docstring both promise."""

    def test_the_unplaced_count_is_reported_and_is_not_zero(self):
        self.assertGreater(UNPLACED, 0)

    def test_the_summary_carries_the_unplaced_count(self):
        line = cds.summary(TREE)
        self.assertIn(str(UNPLACED), line)

    def test_the_summary_names_the_chased_helpers(self):
        self.assertIn("0xD319", cds.summary(TREE))

    def test_an_empty_page_emits_no_rows_rather_than_a_guess(self):
        tree = cds._fixture({"T": [("8000", "mov", "DPTR, #0x9000"),
                                   ("8003", "movx", "A, @DPTR")]})
        self.assertEqual(cds.site_rows(tree), [])

    def test_a_page_address_reached_from_another_program_is_not_mixed_in(self):
        # `common` and `bank0` share runtime addresses; the row's `region` is
        # what says which image the byte is in, and it must never be blank.
        for row in emitted():
            self.assertIn(row["region"], cds.PROGRAMS, row)
            self.assertTrue(row["file_offset"], row)


class Refusals(unittest.TestCase):
    """The walk's own decision cases, over fixtures rather than the tree.

    Each fixture is the shape at 0x0D18C-0x0D191 with one thing changed, so a
    case that starts failing says which of the walk's rules moved.
    """

    # The shape itself: a call to a routine that loads DPTR, a `jnz` guarding
    # the fall-through, and the `movx` behind it.
    SHAPE = [("8000", "lcall", "0x8100"), ("8003", "jnz", "0x8006"),
             ("8005", "movx", "A, @DPTR")]
    LOADER = [("8100", "mov", "DPTR, #0x860"), ("8103", "ret", "")]

    def resolve(self, caller, callee=None):
        tree = cds._fixture({"F": list(caller),
                             "G": list(callee if callee is not None
                                       else self.LOADER)})
        return cds.resolve(tree, "bank0", "F",
                           next(i for i, row in enumerate(caller)
                                if row[1] == "movx"))

    def test_the_shape_resolves_through_the_callee(self):
        got = self.resolve(self.SHAPE)
        self.assertEqual((got["dptr_source"], got["xdata_addr"]),
                         ("callee", 0x0860))

    def test_a_ret_between_the_write_and_the_movx_stops_the_walk(self):
        got = self.resolve([("8000", "mov", "DPTR, #0x860"),
                            ("8003", "ret", ""),
                            ("8004", "movx", "A, @DPTR")])
        self.assertEqual(got["dptr_source"], "unresolved")
        self.assertIsNone(got["xdata_addr"])

    def test_a_callee_without_a_listing_is_named_rather_than_guessed(self):
        got = self.resolve(self.SHAPE, callee=[])
        self.assertEqual(got["dptr_source"], "callee")
        self.assertIsNone(got["xdata_addr"])
        self.assertIn("no committed listing", got["note"])

    def test_a_callee_that_returns_without_writing_dptr_resolves_to_nothing(self):
        got = self.resolve(self.SHAPE,
                           callee=[("8100", "mov", "A, #0x01"), ("8102", "ret", "")])
        self.assertEqual(got["dptr_source"], "callee")
        self.assertIsNone(got["xdata_addr"])

    def test_a_callee_that_writes_one_byte_of_dptr_resolves_to_nothing(self):
        # `mov DPH,A` moves DPTR and names no address, so the walk cannot
        # resolve through it even though it is not a `mov DPTR`.
        got = self.resolve(self.SHAPE,
                           callee=[("8100", "mov", "DPH, A"), ("8102", "ret", "")])
        self.assertIsNone(got["xdata_addr"])
        self.assertIn("moves DPTR without naming it", got["note"])

    def test_a_pop_of_dph_is_the_same_shape_and_also_refused(self):
        got = self.resolve(self.SHAPE,
                           callee=[("8100", "pop", "DPL"), ("8101", "ret", "")])
        self.assertIsNone(got["xdata_addr"])

    def test_an_ljmp_back_inside_the_listing_is_a_jump_not_a_tail_call(self):
        got = self.resolve([("8000", "ljmp", "0x8003"),
                            ("8003", "movx", "A, @DPTR")])
        self.assertEqual(got["dptr_source"], "unresolved")
        self.assertIsNone(got["helper"])

    def test_an_ljmp_out_of_the_listing_is_a_tail_call_and_is_chased(self):
        got = self.resolve([("8000", "ljmp", "0x8100"),
                            ("8003", "movx", "A, @DPTR")])
        self.assertEqual((got["dptr_source"], got["xdata_addr"]),
                         ("callee", 0x0860))

    def test_a_transfer_with_no_address_in_the_operand_is_not_resolved(self):
        got = self.resolve([("8000", "lcall", "@a+dptr"),
                            ("8003", "movx", "A, @DPTR")])
        self.assertEqual(got["dptr_source"], "unresolved")
        self.assertIsNone(got["helper"])

    def test_the_chase_bound_is_a_row_and_not_a_hang(self):
        got = self.resolve(self.SHAPE,
                           callee=[("8100", "lcall", "0x8100"),
                                   ("8103", "ret", "")])
        self.assertEqual(got["dptr_source"], "callee")
        self.assertIsNone(got["xdata_addr"])
        self.assertIn(str(cds.MAX_CHASE), got["note"])


class TheCommittedTable(unittest.TestCase):
    """`ec/annotations/xdata-0860-callee-dptr-sites.csv`, off the tool."""

    def test_this_run_reproduces_it_byte_for_byte(self):
        self.assertEqual(cds.check(), 0)

    def test_it_carries_every_column_the_tool_writes(self):
        with open(cds.CSV_PATH, newline="") as f:
            header = f.readline().rstrip("\r\n")
        self.assertEqual(header, ",".join(cds.COLUMNS))

    def test_every_row_of_it_names_a_region_the_tree_has(self):
        with open(cds.CSV_PATH, newline="") as f:
            body = f.read().splitlines()[1:]
        self.assertTrue(body)
        for line in body:
            self.assertIn(line.split(",")[1], cds.PROGRAMS, line)


class OpensNothingForWriting(unittest.TestCase):
    """The tool's promise in its own docstring: it writes stdout or nothing."""

    def test_the_csv_run_opens_no_file_for_writing(self):
        real = builtins.open
        opened = []

        def watched(path, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                opened.append((path, mode))
            return real(path, mode, *args, **kwargs)

        builtins.open = watched
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cds.csv_table(TREE)
        finally:
            builtins.open = real
        self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main()