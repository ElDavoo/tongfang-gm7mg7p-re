#!/usr/bin/env python3
"""Offline checks for access_cell_corrections.py, the one place a committed
`access` cell may differ from `classify(walk(d, file_offset))` at `walk()`'s
own budget of 8.

**What is pinned here is the property that makes the module a measurement
rather than a list of assertions somebody typed.** Every entry names the
instruction budget at which the tool itself produces the string it claims,
and each of those three claims is re-derived from `ec/firmware/GMxMGxx_11.800`
on every run. An entry whose string cannot be reproduced is a claim about
bytes the bytes do not carry, and `verify()` refuses the module rather than
exporting one -- so the refusal is exercised here on a hand-built entry that
is deliberately not derivable.

The rest is the weaker half, and it is here because a table with no shape is
a table nothing can read: every entry has a reason and an evidence path that
resolves, the key set is the three rows
`walk_budget_census.py` classified B, and `corrected()` leaves every other
offset's cell exactly as `classify()` gave it.

Nothing here needs hardware, Windows or a capture. The firmware read is a
committed file, and the write-up carrying the bytes is
`../../docs/findings/class-b-access-cell-corrections.md`.
"""
import csv
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# access_cell_corrections imports nothing from trace_xdata_refs at module
# scope -- its decoder import is inside verify(), so that this module and
# trace_xdata_refs can each import the other -- but the derivation check needs
# the decoder, and the tool directory has to be on the path before either is
# loaded rather than after.
sys.path.insert(0, str(HERE))
import access_cell_corrections as ACC   # noqa: E402
import trace_xdata_refs as T            # noqa: E402
import walk_budget_census as W          # noqa: E402

FIRMWARE = HERE.parent / 'firmware' / 'GMxMGxx_11.800'
ANNOT = HERE.parent / 'annotations'

# The rows `../../docs/findings/walk-window-terminators.md` §B
# classified B, and the only rows any committed table may differ from
# `classify(walk(d, off))` on. Held as the census's own classification rather
# than as a second copy of it: the test below re-derives this set from
# `walk_budget_census.py` and asserts it, so a further class-B row appearing
# fails here rather than passing unnoticed. Which is what happened when
# `0x07D2`'s table joined `walk_budget_census.py`'s `TABLES` and its one
# class-B row (`0x2F628`) was corrected.
CLASS_B = {"ec-07d6-07d7-sites.csv": "0x2BECB",
           "ec-0x07d0-sites.csv": "0x2E8D4",
           "ec-0x07d2-sites.csv": "0x2F628",
           "xdata-0400-045f-sites.csv": "0x0DD4A"}


def firmware():
    """The image, read once and kept, for the reason
    `test_walk_budget_census.py`'s helper of the same name gives."""
    if not firmware._cached:
        firmware._cached = FIRMWARE.read_bytes()
    return firmware._cached


firmware._cached = None


def rows_of(name):
    with open(ANNOT / name, newline="") as f:
        return list(csv.DictReader(f))


def cell_of(name, offset):
    for row in rows_of(name):
        if row["file_offset"] == offset:
            return row["access"]
    return None


class DerivationTests(unittest.TestCase):
    """The load-bearing half: every recorded string comes out of the image at
    the budget recorded beside it."""

    def test_verify_passes_against_the_committed_image(self):
        # Raises rather than returning a verdict, so this is the module's own
        # refusal being exercised rather than a re-implementation of it.
        ACC.verify(firmware())

    def test_every_entry_is_what_the_image_gives_at_its_recorded_budget(self):
        d = firmware()
        for c in ACC.CORRECTIONS:
            with self.subTest(table=c.table, offset=f"0x{c.offset:05X}"):
                self.assertEqual(T.classify(T.walk(d, c.offset, c.budget)),
                                 c.access)

    def test_every_entry_is_recorded_short_at_walk_own_budget(self):
        """A correction that already holds at budget 8 is not a correction.

        Without this, an entry could be added that silently agreed with
        `classify()` and the module would look like it was doing work.
        """
        d = firmware()
        for c in ACC.CORRECTIONS:
            with self.subTest(table=c.table, offset=f"0x{c.offset:05X}"):
                self.assertNotEqual(
                    T.classify(T.walk(d, c.offset)), c.access,
                    f"0x{c.offset:05X} is committed as {c.access!r}, which is "
                    "what walk()'s own budget already gives -- so this entry "
                    "corrects nothing and hides whether the budget beside it "
                    "is doing any work")

    def test_every_recorded_budget_is_larger_than_walk_own(self):
        for c in ACC.CORRECTIONS:
            self.assertGreater(c.budget, T.walk.__defaults__[0], c.table)

    def test_the_recorded_budget_is_the_censuses_own_extend_figure(self):
        """The budget is a measurement point both tools agree on, not a number
        either of them chose alone. A correction derived at a budget nothing
        else in the tree uses would be re-derivable and unreviewable."""
        for c in ACC.CORRECTIONS:
            self.assertEqual(c.budget, W.EXTEND, c.table)

    def test_a_string_the_image_does_not_produce_is_refused(self):
        """The refusal, on an entry built to fail it.

        Built rather than reached: no committed image produces a wrong
        string, so a case that waited for one would never run. `CORRECTIONS`
        is swapped rather than `BY_OFFSET` because `verify()` reads the former
        -- the tuple is the source of truth and the dict is built from it, so
        patching the dict alone would leave the check running over entries the
        case did not touch.
        """
        good = ACC.CORRECTIONS[0]
        bad = good._replace(access="write x99, walks 99 consecutive bytes "
                                  "(inc dptr)")
        d = firmware()
        self.assertNotEqual(
            T.classify(T.walk(d, bad.offset, bad.budget)), bad.access)
        saved = ACC.CORRECTIONS
        ACC.CORRECTIONS = (bad,)
        try:
            with self.assertRaises(ValueError) as cm:
                ACC.verify(d)
        finally:
            ACC.CORRECTIONS = saved
        self.assertIn("a claim", str(cm.exception))

    def test_verify_reports_the_offset_and_the_budget_that_disagree(self):
        """The message names enough to re-run the one thing that failed.

        Asserted separately from the refusal above because a `verify()` that
        raised the right exception for the wrong row would satisfy that one.
        """
        good = ACC.CORRECTIONS[0]
        bad = good._replace(access="write x99")
        saved = ACC.CORRECTIONS
        ACC.CORRECTIONS = (good, bad)
        try:
            with self.assertRaises(ValueError) as cm:
                ACC.verify(firmware())
        finally:
            ACC.CORRECTIONS = saved
        message = str(cm.exception)
        self.assertIn(bad.table, message)
        self.assertIn(f"0x{bad.offset:05X}", message)
        self.assertIn(str(bad.budget), message)

    def test_corrected_passes_through_an_offset_it_does_not_hold(self):
        d = firmware()
        off = 0x2E8D4 + 1
        self.assertNotIn(off, ACC.BY_OFFSET)
        derived = T.classify(T.walk(d, off))
        self.assertEqual(ACC.corrected(off, derived), derived)

    def test_corrected_gives_the_entry_for_an_offset_it_does_hold(self):
        for c in ACC.CORRECTIONS:
            derived = T.classify(T.walk(firmware(), c.offset))
            self.assertEqual(ACC.corrected(c.offset, derived), c.access, c.table)


class PopulationTests(unittest.TestCase):
    """Which rows this module is allowed to speak about."""

    def test_the_key_set_is_the_three_class_b_rows(self):
        self.assertEqual({c.table: f"0x{c.offset:05X}" for c in
                          ACC.CORRECTIONS}, CLASS_B)

    def test_the_lookup_dict_is_the_tuple_with_no_offset_lost_to_it(self):
        """`corrected()` reads `BY_OFFSET` and `verify()` reads
        `CORRECTIONS`, so the two have to be the same rows. A duplicate offset
        would silently drop one of them from the lookup -- the entry would
        still be verified and never applied."""
        self.assertEqual(len(ACC.BY_OFFSET), len(ACC.CORRECTIONS),
                         "two entries share an offset, so one of them is "
                         "verified but never returned by corrected()")
        for c in ACC.CORRECTIONS:
            self.assertIs(ACC.BY_OFFSET[c.offset], c)

    def test_the_set_is_the_censuses_own_class_b_reading(self):
        """Derived from `walk_budget_census.py`, not asserted beside it.

        The census classifies the rows that move; the module is what the
        corrected cells turn those rows into. If the module named a row the
        census does not class B, one of the two is measuring something else.
        """
        d = firmware()
        classified = {}
        for name in W.TABLES:
            for row in rows_of(name):
                off = int(row["file_offset"], 16)
                insns, why_at = T.walk_why(d, off, W.BUDGET)
                if why_at != T.budget_end(W.BUDGET):
                    continue
                at_extend, _ = T.walk_why(d, off, W.EXTEND)
                verdict = W.verdict_for(at_extend[len(insns):], T.walk_why(
                    d, off, W.EXTEND)[1], W.BUDGET, W.EXTEND,
                    T.classify(at_extend) != T.classify(insns))
                if verdict.startswith("B: "):
                    classified[name] = row["file_offset"]
        self.assertEqual(classified, CLASS_B)

    def test_no_corrected_offset_is_missing_from_its_named_table(self):
        """Each entry names the table its cell lives in, and that cell has to
        be there. An entry pointing at a table the row is not in would be a
        correction nothing reads."""
        for c in ACC.CORRECTIONS:
            with self.subTest(table=c.table):
                self.assertEqual(cell_of(c.table, f"0x{c.offset:05X}"),
                                 c.access)

    def test_the_three_tables_and_the_census_are_the_only_ones_moved(self):
        """Every committed row that is not a *callee-set* site still
        satisfies `classify(walk(d, off)) == access`, so the corrections are
        three cells and not a loosened invariant.

        The exclusion is the one `trace_xdata_refs.py --callee-column` makes,
        and it is derived from that tool's committed input rather than typed
        as a list of offsets: a row is exempt only when its cell carries the
        `DPTR from` spelling **and** equals the cell
        `trace_xdata_refs.load_callee_map()` produces for its
        `(addr, file_offset)`. Those rows are held to the resolver's table by
        the next case, which is a stronger check than this one, not a gap in
        it.

        Held as the per-row property rather than as a count of the
        population: a merge that adds a table or a row moves no total here.
        """
        d = firmware()
        callee = T.load_callee_map()
        for name in W.TABLES:
            for row in rows_of(name):
                off = int(row["file_offset"], 16)
                key = (row["addr"], row["file_offset"])
                if callee.get(key) == row["access"]:
                    continue
                derived = T.classify(T.walk(d, off))
                want = ACC.corrected(off, derived)
                with self.subTest(table=name, offset=row["file_offset"]):
                    self.assertEqual(row["access"], want)

    def test_a_callee_set_cell_is_the_resolver_table_s_own(self):
        """The rows this case exempts are checked against a committed table
        instead of against the image, because `classify()` cannot derive them:
        the DPTR behind such a `movx` was loaded in another function. What
        they are held to is `callee_dptr_sites.py`'s own `--csv` output, so a
        cell typed into the sweep table by hand fails here.
        """
        callee = T.load_callee_map()
        self.assertTrue(callee)
        for name in W.TABLES:
            for row in rows_of(name):
                key = (row["addr"], row["file_offset"])
                if T.DPTR_FROM in row["access"]:
                    with self.subTest(table=name, offset=row["file_offset"]):
                        self.assertEqual(row["access"], callee.get(key))


class SelfTestTests(unittest.TestCase):
    """The `--self-test` a reader runs, so the CLI path is not untested
    merely because every other case here calls `verify()` in-process."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / 'access_cell_corrections.py'),
             str(FIRMWARE), *args], capture_output=True, text=True)

    def test_the_self_test_passes_against_the_committed_firmware(self):
        out = self._run('--self-test')
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("self-test passed", out.stdout)

    def test_a_missing_image_is_a_failure_not_a_pass(self):
        out = subprocess.run(
            [sys.executable, str(HERE / 'access_cell_corrections.py'),
             str(HERE / 'no-such-image.bin'), '--self-test'],
            capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("is not a file", out.stderr)


class EntryShapeTests(unittest.TestCase):
    """Every entry says why and points at something that exists."""

    def test_every_reason_is_non_empty_and_quotes_an_address(self):
        for c in ACC.CORRECTIONS:
            with self.subTest(table=c.table):
                self.assertTrue(c.reason.strip(),
                                f"0x{c.offset:05X} has no reason recorded")
                # A reason that quotes no address is a restatement of the
                # verdict rather than a reason for it. The addresses in these
                # reasons are the listing's *runtime* ones (`0xBED5`, not the
                # file offset `0x2BECB`), because that is how
                # `../decompiled/*/**.asm` spells them -- so the check is that
                # the reason is anchored in bytes, not that it names the
                # offset it is filed under.
                self.assertRegex(
                    c.reason, r"0x[0-9A-Fa-f]{4}",
                    f"0x{c.offset:05X}'s reason quotes no address, so it "
                    "restates the verdict instead of grounding it")

    def test_every_evidence_path_resolves(self):
        for c in ACC.CORRECTIONS:
            self.assertTrue(c.evidence, f"0x{c.offset:05X} has no evidence")
            for rel in c.evidence:
                with self.subTest(table=c.table, path=rel):
                    self.assertTrue((REPO / rel).is_file(),
                                    f"{rel} does not resolve")

    def test_every_entry_names_the_asm_listing_it_was_read_from(self):
        """The `.asm` is the machine code; the `.c` is a reading of it, and
        the file header says so. A correction resting only on a decompile
        would be resting on the weaker half of the pair."""
        for c in ACC.CORRECTIONS:
            self.assertTrue(any(rel.endswith(".asm") for rel in c.evidence),
                            f"0x{c.offset:05X} cites no .asm listing")

    def test_no_entry_corrects_a_row_the_census_does_not_measure(self):
        """The census measures `access` cells; a corrected row that no census
        table carried would be corrected in a table nothing checks."""
        tables = {c.table for c in ACC.CORRECTIONS}
        self.assertLessEqual(tables, set(W.TABLES))


if __name__ == '__main__':
    unittest.main()
