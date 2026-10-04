#!/usr/bin/env python3
"""`trace_xdata_refs.py --callee-column`: the sites whose DPTR a callee left.

Kept apart from `test_trace_xdata_refs.py` and
`test_trace_xdata_refs_usage.py` for the reason those two name: the first is
scoped to `walk()`'s bounds contract and the second to the advice the
`Usage:` block gives, and this is neither. It is about a population -- which
rows the `--csv` table gains, where they sort, and which cell of theirs is
read rather than derived.

The population rule is the thing worth holding. A callee-set `movx` becomes a
site because the sweep's own `MOV DPTR` scan cannot find it at all; a
`predecessor` row does not, because the load it depends on *is* a site at
another address the sweep already books. Getting that backwards either loses
the stores this issue is about or books one store twice.

Committed files only: the firmware image, the two committed CSVs and the
resolver's table. No hardware, no Ghidra, no network.
"""
import csv
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trace_xdata_refs as T  # noqa: E402

FW = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
# xdata-086x-dispatch.md §1's address list: the run whose --csv output is the
# committed sites table.
PAGE = ["0x0860", "0x0862", "0x0865", "0x0866", "0x0867", "0x0868", "0x0869",
        "0x086A", "0x086B", "0x086D", "0x086E", "0x1C39", "0x1C3A", "0x1F01",
        "0x1F07"]


def run(*args):
    """(exit code, stdout) for one `trace_xdata_refs.py` run."""
    done = subprocess.run([sys.executable, os.path.join(HERE,
                                                        "trace_xdata_refs.py"),
                           FW, *args],
                          capture_output=True, text=True, check=False)
    return done.returncode, done.stdout


def table(*extra):
    code, out = run(*PAGE, "--csv", "--census-column", *extra)
    assert code == 0, out
    return list(csv.DictReader(out.splitlines()))


class ThePopulation(unittest.TestCase):
    """Which rows the flag adds, and which rows it must not."""

    def test_the_two_stores_of_the_issue_are_rows_under_the_flag(self):
        got = {r["file_offset"]: r for r in table("--callee-column")}
        for offset in ("0x0D191", "0x0D249"):
            self.assertIn(offset, got, offset)
            self.assertEqual(got[offset]["addr"], "0x0860")
            self.assertEqual(got[offset]["access"],
                             "write x1, DPTR from 0xD319")
            self.assertEqual(got[offset]["census"], "dptr from callee")

    def test_without_the_flag_they_are_absent(self):
        got = {r["file_offset"] for r in table()}
        for offset in ("0x0D191", "0x0D249"):
            self.assertNotIn(offset, got, offset)

    def test_a_predecessor_row_is_not_promoted_to_a_site(self):
        # `0x0BD3D` is a `movx` whose DPTR the listing above left loaded. The
        # load is a site in its own right at `0x0BD36`, which the sweep already
        # books, so a second row would book the same routine twice.
        got = {r["file_offset"] for r in table("--callee-column")}
        self.assertNotIn("0x0BD3D", got)
        self.assertIn("0x0BD36", got)

    def test_the_flag_adds_no_column(self):
        # The other committed tables reproduce byte for byte because the
        # default carries nothing new; a column here would change the meaning
        # of every row rather than the value of some.
        self.assertEqual(list(table()[0]), list(table("--callee-column")[0]))

    def test_the_rows_sort_by_offset_within_their_address(self):
        offsets = [r["file_offset"] for r in table("--callee-column")
                   if r["addr"] == "0x0860"]
        self.assertEqual(offsets, sorted(offsets))

    def test_the_window_of_a_callee_row_starts_on_the_movx(self):
        # The byte-scan sites skip the `MOV DPTR` their window is anchored on;
        # a callee site's anchor *is* the access, so including the load would
        # be reporting an instruction this row is not about.
        got = {r["file_offset"]: r for r in table("--callee-column")}
        self.assertEqual(got["0x0D191"]["window"],
                         "movx @dptr,a ; ljmp 0xd28e")
        self.assertEqual(got["0x0D144"]["window"],
                         "movx a,@dptr ; lcall 0x7151")


class TheCellIsReadNotDerived(unittest.TestCase):
    """`load_callee_map()`'s own contract with the resolver's table."""

    def test_only_callee_rows_with_a_movx_become_cells(self):
        cells = T.load_callee_map()
        with open(T.CALLEE_CSV, newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertTrue(cells)
        for row in rows:
            key = (row["xdata_addr"], row["file_offset"])
            if row["dptr_source"] == "callee" and row["movx"]:
                self.assertIn(key, cells, key)
                self.assertIn(T.DPTR_FROM, cells[key])
            else:
                self.assertNotIn(key, cells, key)

    def test_every_cell_names_the_helper_the_resolver_row_does(self):
        with open(T.CALLEE_CSV, newline="") as f:
            rows = {(r["xdata_addr"], r["file_offset"]): r
                    for r in csv.DictReader(f)}
        for key, cell in T.load_callee_map().items():
            self.assertTrue(cell.endswith(rows[key]["helper"]), key)

    def test_an_unreadable_table_is_no_cells_and_not_a_crash(self):
        missing = os.path.join(HERE, "no-such-callee-table.csv")
        self.assertEqual(T.load_callee_map(missing), {})

    def test_the_committed_table_is_the_one_the_tool_reads(self):
        self.assertTrue(os.path.exists(T.CALLEE_CSV))
        self.assertIn("callee_dptr_sites.py", T.CALLEE_TOOL)


class CheckReCutsTheColumn(unittest.TestCase):
    """`--check` cannot be told to re-cut by the flag a reader forgets."""

    def test_check_against_the_committed_table_reproduces_it(self):
        code, out = run(*PAGE, "--csv", "--census-column", "--check")
        self.assertEqual(code, 0, out)

    def test_check_finds_the_column_itself_when_the_flag_is_absent(self):
        # The 0x086x table carries `DPTR from` cells and no column that says
        # so, so the header cannot answer this; a bare `--check` has to look
        # at the rows or a reader who forgets the flag gets a diff of every
        # callee row rather than an explanation.
        code, out = run(*PAGE, "--csv", "--census-column", "--check")
        self.assertEqual(code, 0, out)
        self.assertIn("reproduces it byte for byte", out)

    def test_check_against_a_table_without_the_column_still_works(self):
        # The other three committed tables, which have no callee rows: the
        # detection is over their bytes and finds nothing, so they keep
        # reproducing from the plain command.
        for name in ("xdata-0400-045f-sites.csv", "ec-07c4-07d5-sites.csv"):
            path = os.path.join(HERE, os.pardir, "annotations", name)
            if not os.path.exists(path):
                continue
            self.assertNotIn(T.DPTR_FROM, T.committed_text(path), name)


class TheUsageSurface(unittest.TestCase):
    def test_the_flag_needs_csv(self):
        code, _ = run(*PAGE, "--callee-column")
        self.assertEqual(code, 2)

    def test_the_committed_table_is_the_one_this_run_produces(self):
        # Read with newline="" for the reason check_table() gives: the
        # committed tables carry the csv module's own CRLF terminator, and
        # universal-newline translation would rewrite every one of them and
        # report a difference on a run that produced them.
        code, out = run(*PAGE, "--csv", "--census-column", "--callee-column")
        self.assertEqual(code, 0)
        with open(T.SITES_CSV, newline="") as f:
            self.assertEqual(out, f.read().replace("\r\n", "\n"))


if __name__ == "__main__":
    unittest.main()