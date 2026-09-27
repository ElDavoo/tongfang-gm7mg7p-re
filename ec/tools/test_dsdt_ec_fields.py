#!/usr/bin/env python3
"""The bit arithmetic and the refusals of `dsdt_ec_fields`, on their own.

`dsdt_ec_fields.py --self-test` holds the tool's *answers*: the three bit
oracles the tree already reads the same way from two different directions, the
nine addresses ECMG and `registers.yaml` agree on, and the shape of the ECMG
and GNVS lists. This file holds the other half -- the cases that decide whether
those answers could have come out wrong in a way the self-test would read as
right.

The split is the one `test_walk_budget_census.py` and
`test_trace_xdata_refs.py` use, for the same reason: a self-test that walks
the committed .dsl passes just as happily on a parser that rounds sub-byte
widths to whole bytes, because a field at bit 3 of a byte is still *at* that
byte. The bit index is the whole claim, so the oracles pin it in one place and
the fixtures below pin what produces it everywhere else.

Three things this holds that nothing else here does:

  * **Multi-byte elements.** `PMAX, 16` at `Offset (0x7B3)` covers 0x07B3 and
    0x07B4, and the following element starts at 0x07B5 -- the 0x07B3 CPU
    PL2 default in `registers.yaml` is a byte-addressed register, so an
    off-by-one in the cursor would silently renumber the whole tail of the
    list. Nothing in the oracles would notice.
  * **Unnamed bit runs.** `Offset (0x7C4)` declares three unnamed bits before
    `DBEN`, and `Offset (0x7A4)` two before `GC6S`. A parser that ignored them
    would place `DBEN` and `DBST` at bits 0 and 2, which is the reading
    `registers.yaml` records having had to correct in place.
  * **The refusals, once each.** The `--self-test` output prints the message
    each refusal produces; a case that only asserted "it raised" would not tell
    a reader which message is the one that matters, and one that only asserted
    the message would pass if the wrong input were refused for the wrong
    reason. Each case below asserts both, on a fixture with exactly one thing
    wrong with it.

No hardware, no firmware image, no Ghidra and no network: the committed
`evidence/acpi/dsdt.dsl` and fixtures built here are the whole corpus. Run it
with `python3 ec/tools/test_dsdt_ec_fields.py` from the repository root, or
under any unittest runner.
"""
import contextlib
import csv
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).parent
# dsdt_ec_fields imports trace_xdata_refs, which imports disasm8051 by bare
# module name, so the tool directory has to be on the path before the tool is
# loaded rather than after.
sys.path.insert(0, str(HERE))
import dsdt_ec_fields as D           # noqa: E402

REPO = HERE.parent.parent


# A whole operation region plus field list, so a fixture's only wrong thing is
# what the case is about. The list opens on the next line, as iasl emits it.
def fixture(*body: str) -> list:
    return ["OperationRegion (TST, SystemMemory, 0x10000000, 0x10000)",
            "Field (TST, AnyAcc, NoLock, Preserve)", "{", *body, "}"]


def elements(*body: str) -> list:
    """The parsed elements of a fixture, as the tool returns them."""
    return D.extract(fixture(*body), "<test fixture>", "TST")["elements"]


class BitCursorTests(unittest.TestCase):
    """Where each element lands, which is the whole of the extraction."""

    def test_the_list_opens_at_byte_zero(self):
        # ASL's implicit start, and the reason GNVS's 1,038 names come out one
        # per byte across 0x0000-0x07F9 rather than from its first `Offset`.
        self.assertEqual(elements("    FIRST,  8")[0][:4], ("FIRST", 0, 0, 8))

    def test_an_offset_moves_the_cursor_to_that_byte(self):
        self.assertEqual(elements("    Offset (0x07A4),", "    GC6S,  1")[0][:4],
                         ("GC6S", 0x07A4, 0, 1))

    def test_unnamed_bits_are_counted_not_skipped(self):
        # The shape of `Offset (0x7C4)`, three unnamed bits, DBEN, one more,
        # DBST. Whole-byte rounding puts DBEN at bit 0 -- the reading
        # registers.yaml's note records correcting.
        got = elements("    Offset (0x07C4),", "        ,  3,",
                       "    DBEN,  1,", "        ,  1,", "    DBST,  1")
        self.assertEqual([e[:4] for e in got],
                         [("DBEN", 0x07C4, 3, 1), ("DBST", 0x07C4, 5, 1)])

    def test_a_named_element_crossing_a_byte_boundary_advances_the_cursor(self):
        # `Offset (0x7E8), , 5, APCN, 4` puts APCN's four bits at 0x07E8 bit 5
        # through 0x07E9 bit 0, so the next element opens at 0x07E9 bit 1. A
        # cursor that clamped a crossing element to its first byte would put
        # NEXT a bit low and every element after it along with it.
        got = elements("    Offset (0x07E8),", "        ,  5,",
                       "    APCN,  4,", "    NEXT,  8")
        self.assertEqual([e[:4] for e in got],
                         [("APCN", 0x07E8, 5, 4), ("NEXT", 0x07E9, 1, 8)])

    def test_a_multi_byte_element_advances_by_its_width(self):
        # `PMAX, 16` at 0x07B3 is 0x07B3-0x07B4, so `PBSS, 16` opens at
        # 0x07B5. Rounding a 16-bit element up to "the byte it ended in" is
        # how the tail of this list would renumber by one.
        got = elements("    Offset (0x07B3),", "    PMAX,  16,",
                       "    PBSS, 16")
        self.assertEqual([e[:4] for e in got],
                         [("PMAX", 0x07B3, 0, 16), ("PBSS", 0x07B5, 0, 16)])

    def test_an_offset_resets_the_cursor_whatever_came_before(self):
        # The committed ECMG list jumps 0x07BA -> 0x07C0 mid-byte-group, so a
        # cursor that only ever advanced would not reach the second offset.
        got = elements("    Offset (0x07BA),", "    VBNL, 16,",
                       "    Offset (0x07C0),", "    AP01, 8")
        self.assertEqual([e[:4] for e in got],
                         [("VBNL", 0x07BA, 0, 16), ("AP01", 0x07C0, 0, 8)])

    def test_each_element_carries_the_line_it_was_declared_on(self):
        # Every row in the committed CSV is cited by dsdt.dsl line, so the
        # line number is part of the extraction and not decoration. Line 5 of
        # the fixture: the region, the Field, the brace, the Offset, the name.
        got = D.extract(fixture("    Offset (0x0040),", "    NNAM, 8"),
                        "<test fixture>", "TST")
        self.assertEqual(got["elements"][0][4], 5)

    def test_blank_and_commented_lines_do_not_move_the_cursor(self):
        got = elements("    Offset (0x0040),", "",
                       "    ; a comment inside the list", "    NNAM, 8")
        self.assertEqual(got[0][:4], ("NNAM", 0x0040, 0, 8))


class RefusalTests(unittest.TestCase):
    """One wrong thing per fixture, and the message it has to produce.

    A refusal that raised for the wrong reason is a refusal that will keep
    raising after the reason is fixed, so each case pins a distinctive phrase
    rather than `assertRaises(FieldError)` alone.
    """

    def assertRefused(self, lines, phrase):
        with self.assertRaises(D.FieldError) as cm:
            D.extract(lines, "<test fixture>", "TST")
        self.assertIn(phrase, str(cm.exception))

    def test_an_offset_that_is_not_a_literal_is_refused(self):
        # An `Offset (CurrentTbStatus)` or `Offset (SBRG + 0x100)` resolves at
        # ACPI-load time. Placing the fields after it from a guess is how a
        # name ends up on an address the firmware never wrote.
        self.assertRefused(
            fixture("    Offset (Base + 0x100),", "    NNAM, 8"),
            "not a literal byte offset")

    def test_an_access_keyword_is_refused(self):
        # `Access (ProcessLock)` makes an element's width bits where the
        # default makes it bytes, so every bit index after it would be wrong
        # and none of them would look wrong.
        self.assertRefused(
            fixture("    Offset (0x0040),", "    Access (ProcessLock),",
                    "    NNAM, 8"),
            "Access (ProcessLock)")

    def test_one_name_at_two_addresses_is_refused(self):
        self.assertRefused(
            fixture("    Offset (0x0040),", "    DUP, 8,",
                    "    Offset (0x0050),", "    DUP, 8"),
            "declared twice")

    def test_a_list_naming_an_undeclared_region_is_refused(self):
        # The offsets in such a list address nothing the file declares, which
        # is exactly what a Field list over a region someone renamed looks
        # like, and what a GNVS-versus-ECMG confusion would look like.
        self.assertRefused(
            ["Field (TST, AnyAcc, NoLock, Preserve)", "{",
             "    Offset (0x0040),", "    NNAM, 8", "}"],
            "no OperationRegion of that name")

    def test_a_list_that_never_opens_is_refused(self):
        self.assertRefused(
            ["OperationRegion (TST, SystemMemory, 0x10000000, 0x10000)",
             "Field (TST, AnyAcc, NoLock, Preserve)"],
            "unterminated")

    def test_a_line_the_grammar_does_not_name_is_refused(self):
        # IndexField and Connection are real ASL and would change where a
        # field lands. Skipping them is how a list would be parsed with a hole
        # in it and the hole would read as "the DSDT does not name this".
        self.assertRefused(
            fixture("    Offset (0x0040),", "    IndexField (IDX, 0)"),
            "unrecognised line")

    def test_a_region_with_no_field_list_at_all_is_refused(self):
        self.assertRefused(
            ["OperationRegion (TST, SystemMemory, 0x10000000, 0x10000)"],
            "no Field (TST, ...) list")


class CommittedFileTests(unittest.TestCase):
    """The committed .dsl and the committed table, as the tool reads them."""

    @classmethod
    def setUpClass(cls):
        with open(D.DEFAULT_DSDT, errors="replace") as f:
            cls.lines = f.read().split("\n")
        cls.ecmg = D.extract(cls.lines, D.DEFAULT_DSDT, "ECMG")

    def test_the_committed_table_is_what_the_tool_regenerates(self):
        # `--check` in one command, from the suite, so a hand-edited cell in
        # dsdt-ecmg-fields.csv is caught here and not only by a human who
        # remembers the flag.
        rc = subprocess.run(
            [sys.executable, str(HERE / "dsdt_ec_fields.py"),
             str(REPO / "ec" / "firmware" / "GMxMGxx_11.800"),
             "--csv", "--check"],
            cwd=REPO, capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, rc.stdout + rc.stderr)

    def test_check_reports_a_difference_rather_than_crashing_on_one(self):
        # The half of `--check` that never runs when the committed table is
        # correct, which is why it needs its own case: `check_table()` builds a
        # unified diff on the failing path only, so a typo in that one call --
        # `lineterminator` for `lineterm`, which is what this file's tool first
        # had -- leaves every other case here green while the check raises a
        # TypeError exactly when it is needed. A check that crashes when it
        # finds a difference is a check that reports "no difference".
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "fields.csv")
            with open(path, "w", newline="") as f:
                f.write("region,addr\nECMG,0x0000\n")
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc = D.check_table("region,addr\nECMG,0x0001\n", path)
        self.assertEqual(rc, 1)
        self.assertIn("-ECMG,0x0000", err.getvalue())
        self.assertIn("+ECMG,0x0001", err.getvalue())

    def test_check_reports_an_unreadable_path_once(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with contextlib.redirect_stderr(io.StringIO()):
                rc = D.check_table("x\n", os.path.join(d, "absent.csv"))
        self.assertEqual(rc, 1)

    def test_no_row_in_the_committed_table_claims_an_ec_site_without_one(self):
        # The grade column is the file's only proposed status, and a
        # `present-untested` on a zero would be the claim docs/findings.md 4c
        # retracted. Read back off disk rather than off build_rows(), so it
        # tests the committed bytes.
        with open(D.FIELDS_CSV, newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), len(self.ecmg["elements"]))
        for r in rows:
            if r["grade"] == "present-untested":
                self.assertGreater(int(r["static_refs_main_ec"]), 0,
                                   f"{r['addr']} {r['name']}")
            if r["grade"] == "unknown-not-absent":
                self.assertEqual(int(r["static_refs_main_ec"]), 0, f"{r['addr']}")
                self.assertGreater(int(r["static_refs"]), 0, f"{r['addr']}")
            if r["grade"] == D.NO_SITE:
                self.assertEqual(int(r["static_refs"]), 0, f"{r['addr']}")

    def test_the_committed_table_proposes_no_status_outside_the_vocabulary(self):
        # registers.yaml's `status:` list is the set a `grade` cell can be
        # promoted into, so a proposal outside it is a status this sweep
        # invented. `not-found-by-this-method` is not a proposal at all -- it
        # is what a row says when nothing is proposed -- and it is asserted
        # absent from the vocabulary so it cannot be lifted into an entry by
        # someone reading the CSV for candidates.
        with open(D.DEFAULT_REGISTERS) as f:
            statuses = {r["status"] for r in yaml.safe_load(f)["registers"]}
        with open(D.FIELDS_CSV, newline="") as f:
            grades = {r["grade"] for r in csv.DictReader(f)}
        self.assertNotIn(D.NO_SITE, statuses)
        proposals = grades - {D.NO_SITE}
        self.assertTrue(proposals <= statuses | {"present-untested",
                                                 "unknown-not-absent"},
                        proposals - statuses)
        self.assertIn(D.NO_SITE, grades,
                      "the zero rows are the point of the token existing")


if __name__ == "__main__":
    unittest.main()
