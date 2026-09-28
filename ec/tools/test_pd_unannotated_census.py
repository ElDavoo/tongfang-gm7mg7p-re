#!/usr/bin/env python3
"""Offline checks for pd_unannotated_census.py: the tool's derivations, and the
claim the population exists to be closed against.

Two classes, and the split between them is the point.

**The first asserts the claim, not the census.** "Every `pd` listing under
`ec/decompiled/` has a `pd` row in `ghidra-functions.csv` whose `evidence` names
that listing first, and that row's address resolves to an exported function" is
a statement about the tree that stays true as the tree grows: a new listing
arrives already annotated, or not at all, and either way the sentence is either
true or the failure is a real one. "There are 535 listings and 498 rows" is not
that. It is a value every merge that annotates one row has to edit, and
`ec/tools/test_check_pin_table_by_cited_file.py` has been that bug four times --
four concurrent branches each bumping one held count from a different base. The
suite asserts the former, so the population figure can move without the test
moving with it.

**The second asserts the tool's own derivations**, which is what
`--self-test` cannot do alone: that `census()` on a fixture tree produces the
population, the shared-address flag, the edges and the orphan list the module
docstring says it does. The failure that made this split necessary is recorded
in the fixture: the first version of the self-test asserted a set of
expressions re-derived beside the real ones and passed while `census()`
compared an `int` against a set of address strings, so every shared
`common`/`pd` address read as unshared and the report said 0 where the tree has
2. A self-test that re-derives the answer beside the code certifies the
derivation, not the tool, so these cases call `census()` itself.
"""
import csv
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

spec = importlib.util.spec_from_file_location(
    "pd_unannotated_census", HERE / "pd_unannotated_census.py")
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


class TestTheClaim(unittest.TestCase):
    """The committed tree, read through the claim rather than a count."""

    def test_every_pd_listing_has_a_row(self):
        """The bar this issue sets: a row per listing.

        One row per listing, one listing per row, and no address carrying two
        rows. Those three are the whole of the claim, and they are the shape
        that stays true as the tree grows: a new listing arrives already
        annotated or not at all, and either way the sentence is true or the
        failure is a real one. "There are 535 listings and 498 rows" is not
        that -- it is a value every merge that annotates a row has to edit.
        """
        listings = census.listing_addresses()
        self.assertTrue(listings, "no pd listings found at all")

        rows = {}
        for row in read_csv(census.EC_CSV):
            if row["scope"] == census.PROGRAM:
                key = census.norm_addr(row["addr"])
                self.assertNotIn(
                    key, rows, "two pd rows at one address: %s" % key)
                rows[key] = row

        self.assertEqual([a for a in listings if a not in rows], [],
                         "pd listings with no row")

    def test_no_pd_row_cites_another_functions_listing(self):
        """Where a row cites a listing, it cites its own.

        **This is a weaker claim than "every row cites its own listing", and
        the weakening is measured, not convenient.** 34 committed `pd` rows
        cite no listing at all -- `pd 0x10BC` names only
        `ec/annotations/ec-0x07d0-sites.md`, because for those rows the
        write-up *is* the reading and there is no listing citation to check.
        They are the same 34 `asm_path()` cannot resolve, which
        `pd_unannotated_census.py` reports on every run, and repairing them is
        a separate change to a shared file. So the assertion here is the one
        that is true of the whole population and is the failure worth catching:
        a row that *does* name a listing must not name a different function's.
        That is a mis-citation, and `build_ec_decompile.py --check` cannot see
        it, because all it asks is that the cell be non-empty.
        """
        stray = []
        for row in read_csv(census.EC_CSV):
            if row["scope"] != census.PROGRAM:
                continue
            addr = census.norm_addr(row["addr"])
            cited = [p.strip() for p in row["evidence"].split(";")]
            listings = [p for p in cited
                        if p.startswith("ec/decompiled/%s/" % census.PROGRAM)
                        and p.endswith(".asm")]
            for path in listings:
                if os.path.basename(path)[:-4].upper() != addr:
                    stray.append((addr, path))

        self.assertEqual(stray, [],
                         "pd rows citing another function's listing: %s"
                         % stray)

    def test_every_pd_row_resolves_to_an_exported_function(self):
        """The other half of a row being a finding rather than a claim.

        A row naming an address with no listing behind it is a stale claim, and
        `build_ec_decompile.py --check` refuses one -- so this asserts the CSV
        and the committed export agree, which is what makes the row above a
        closed loop rather than 535 rows in a file.
        """
        exported = {census.norm_addr(r["addr"])
                    for r in read_csv(REPO / "ec" / "decompiled"
                                       / "index.csv")
                    if r["program"] == census.PROGRAM}
        orphans = sorted(
            census.norm_addr(r["addr"])
            for r in read_csv(census.EC_CSV)
            if r["scope"] == census.PROGRAM
            and census.norm_addr(r["addr"]) not in exported)
        self.assertEqual(orphans, [],
                         "pd rows naming no exported function: %s"
                         % ", ".join(orphans))

    def test_the_census_reports_an_empty_population(self):
        """The suite passes for the right reason, and not because it is
        vacuous.

        A test of the claim that also passes on a tree where the census is
        broken -- because the census found nothing, so nothing was unannotated,
        so the claim held -- is a test that cannot fail. Asserting that the
        tool's own run comes back empty *and* that it read the tree first
        closes that: a census that located nothing has to say so rather than
        report a clean bill of health.
        """
        rows, orphans, unreadable = census.census()
        listing_count = len(census.listing_addresses())
        self.assertGreater(listing_count, 0)
        self.assertEqual(rows, [], "pd listings still without a row: %s"
                         % ", ".join(r["addr"] for r in rows))
        self.assertEqual(orphans, [],
                         "pd rows with no listing: %s" % ", ".join(orphans))
        # The evidence-column gap is pre-existing and reported rather than
        # repaired here (see the tool's module docstring), so the test pins
        # that the tool still *reports* it -- not any value for it.
        self.assertIsInstance(unreadable, int)

    def test_report_runs_and_prints_the_claim(self):
        """`report()` is exercised on the committed tree, not only on fixtures.

        The prose it prints is the part a write-up quotes, and a format string
        that raised on a row would take the tool down at exactly the moment
        somebody runs it for a number. The assertion is that it runs and says
        the population is empty -- which is the state this change leaves it in.
        """
        rows, orphans, unreadable = census.census()
        buf = io.StringIO()
        old = sys.stdout
        try:
            sys.stdout = buf
            self.assertTrue(census.report(rows, orphans, unreadable))
        finally:
            sys.stdout = old
        text = buf.getvalue()
        self.assertIn("listings with no ghidra-functions.csv row: 0",
                      text)
        self.assertIn("also carrying a `common` row", text)


class TestDerivations(unittest.TestCase):
    """`census()` on a fixture tree, through the function the tool runs."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        self.pd = os.path.join(self.root, "ec", "decompiled", "pd")
        census.write_listing(self.pd, "0012", "FUN_CODE_0012",
                             [("0012", "ff - -", "mov", "R7, A")])
        census.write_listing(self.pd, "06EA", "FUN_CODE_06ea",
                             [("06ea", "12 10 00", "lcall", "0x1000"),
                              ("06ec", "22 - -", "ret", "")])
        census.write_listing(self.pd, "1000", "FUN_CODE_1000",
                             [("1000", "22 - -", "ret", "")])
        census.write_listing(self.pd, "2000", "FUN_CODE_2000",
                             [("2000", "22 - -", "ret", "")])
        self.rows = [
            {"scope": "pd", "addr": "0x06ea", "evidence": self.ev("06EA")},
            {"scope": "common", "addr": "0x0012", "evidence": self.ev("0012")},
            {"scope": "pd", "addr": "0x3000", "evidence": self.ev("3000")},
        ]
        self.addCleanup(self._tmp.cleanup)

    @staticmethod
    def ev(addr):
        return "ec/decompiled/pd/%s.asm; ec/decompiled/pd/%s.c" % (addr, addr)

    def run_census(self, rows=None):
        rows = self.rows if rows is None else rows
        got, orphans, unreadable = census.census(rows=rows,
                                                 directory=self.pd,
                                                 repo=self.root)
        return {r["addr"]: r for r in got}, orphans, unreadable

    def test_population_is_a_two_way_difference(self):
        """A listing with no row, and a row with no listing, are both reported.

        Netting them is the failure this exists to prevent: it returns zero for
        a tree where one listing was annotated and one row was dropped in the
        same commit, and zero reads as a finished population.
        """
        got, orphans, _ = self.run_census()
        self.assertEqual(sorted(got), ["0012", "1000", "2000"])
        self.assertEqual(orphans, ["3000"])

    def test_a_common_row_does_not_annotate_the_pd_side(self):
        """Same address, separate program.

        This is the conflation the whole census is scoped around, and the case
        the re-derived self-test got wrong: read as strings rather than
        numerically, `shared_with_common` is False for every address and the
        report's overlap line reads 0 on a tree that has 2.
        """
        got, _, _ = self.run_census()
        self.assertTrue(got["0012"]["shared_with_common"])
        self.assertFalse(got["1000"]["shared_with_common"])
        self.assertFalse(got["2000"]["shared_with_common"])

    def test_edges_carry_the_callers_own_scope(self):
        """Which region an edge starts in is what decides whether seeding the
        target can move a figure, so the scope is recorded and not summed."""
        got, _, _ = self.run_census()
        self.assertEqual([s for s, _, _ in got["1000"]["inbound"]], ["pd"])
        self.assertEqual(got["1000"]["callers"], ["pd"])
        self.assertEqual(got["2000"]["inbound"], [])

    def test_a_row_whose_evidence_resolves_to_nothing_is_counted(self):
        """`asm_path()` returns None rather than raising, so a stale citation
        drops that row's edges silently. The tool counts them instead, because
        a figure that is low for a reason nobody printed reads as a finding."""
        _, _, unreadable = self.run_census()
        self.assertEqual(unreadable, 1)

    def test_an_empty_population_is_reported_as_empty(self):
        """Annotating every fixture listing empties the census, and the report
        says so rather than printing nothing at all."""
        rows = self.rows + [{"scope": "pd", "addr": "0x0012",
                             "evidence": self.ev("0012")},
                            {"scope": "pd", "addr": "0x1000",
                             "evidence": self.ev("1000")},
                            {"scope": "pd", "addr": "0x2000",
                             "evidence": self.ev("2000")}]
        got, _, _ = self.run_census(rows)
        buf = io.StringIO()
        old = sys.stdout
        try:
            sys.stdout = buf
            census.report(got, [], 0)
        finally:
            sys.stdout = old
        self.assertIn("listings with no ghidra-functions.csv row: 0",
                      buf.getvalue())


if __name__ == "__main__":
    unittest.main()
