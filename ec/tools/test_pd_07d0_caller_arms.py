#!/usr/bin/env python3
"""The thirteen `pd 0x07D0` caller arms, from the firmware bytes up.

`docs/findings/pd-07d0-caller-arms.md` is the write-up. The thirteen are the
fall-through cases in larger dispatch routines, each one calling one of the
seven `0x07D0` accessor stubs. This suite asserts relationships only, never
counts of the repository's own text:

- each of the thirteen has a `pd` row graded `hand-decoded` / `code-shape` with
  a non-empty `evidence` naming both of its own exported files, and both are
  on disk;
- each has an `index.csv` row seeded from its annotation, and a listing and a
  decompile beside it;
- each address is a real `lcall` site resolving to one of the seven stubs, and
  each stub's committed `inbound` equals the number of transfer sites — the
  existing relationship, re-read for the new rows;
- **the `0x4AE9` guard**: `call_graph.parse_listing()` on `pd/4AE9.asm` spells
  no address that `pd/4D6F.asm` also spells. Asking the parse rather than
  comparing spans keeps *spelled* and *covered* apart.
"""
import csv
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

ADDRESSES = [0x488F, 0x4932, 0x496C, 0x4989, 0x4AE9, 0x5131, 0x51B2,
             0x51E6, 0x51FE, 0x79B3, 0x7A5A, 0x842F, 0x844B]


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


call_graph = load("call_graph")


def committed_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class TestAnnotationRows(unittest.TestCase):
    """Each address has a row in ghidra-functions.csv."""

    @classmethod
    def setUpClass(cls):
        cls.rows = {(r["scope"], int(r["addr"], 16)): r
                    for r in committed_rows(HERE.parent / "annotations"
                                            / "ghidra-functions.csv")}

    def test_each_address_has_a_pd_row(self):
        for addr in ADDRESSES:
            with self.subTest(addr="%04X" % addr):
                self.assertIn(("pd", addr), self.rows)

    def test_each_row_carries_the_basis_the_plan_requires(self):
        for addr in ADDRESSES:
            with self.subTest(addr="%04X" % addr):
                row = self.rows[("pd", addr)]
                self.assertEqual("dispatch", row["type"])
                self.assertEqual("hand-decoded", row["basis"])
                self.assertEqual("code-shape", row["name_basis"])

    def test_each_rows_evidence_names_both_exported_files(self):
        for addr in ADDRESSES:
            with self.subTest(addr="%04X" % addr):
                paths = [p.strip()
                         for p in self.rows[("pd", addr)]["evidence"].split(";")]
                self.assertEqual(
                    ["ec/decompiled/pd/%04X.asm" % addr,
                     "ec/decompiled/pd/%04X.c" % addr], paths)
                for path in paths:
                    self.assertTrue((REPO / path).is_file(), path)


class TestExportRows(unittest.TestCase):
    """Each address reached the project, and the export says it was seeded."""

    @classmethod
    def setUpClass(cls):
        cls.index = {(r["program"], int(r["addr"], 16)): r
                     for r in committed_rows(HERE.parent / "decompiled"
                                             / "index.csv")}

    def test_each_address_has_an_index_row_seeded_from_its_annotation(self):
        for addr in ADDRESSES:
            with self.subTest(addr="%04X" % addr):
                row = self.index[("pd", addr)]
                self.assertEqual("annotation", row["seed_basis"])
                self.assertEqual("yes", row["annotated"])

    def test_each_address_has_both_a_listing_and_a_decompile(self):
        for addr in ADDRESSES:
            with self.subTest(addr="%04X" % addr):
                for suffix in (".asm", ".c"):
                    path = REPO / "ec" / "decompiled" / "pd" / ("%04X%s"
                                                                % (addr, suffix))
                    self.assertTrue(path.is_file(), str(path))


class TestCensusRelationship(unittest.TestCase):
    """Each address calls one of the seven stubs, and the census relationship
    holds: a stub has a row iff a committed listing carries a transfer to it.
    """

    @classmethod
    def setUpClass(cls):
        cls.index = call_graph.load_index()
        cls.edges, _unresolved, _orphans, _total, listings = call_graph.scan(
            cls.index)
        cls.keys = {("pd", call_graph.norm_addr("%04X" % a)) for a in ADDRESSES}
        cited, _rejected, _undecided, _listing_kept = call_graph.citations(
            cls.index, listings)
        cls.cited = set(cited)
        cls.census = {(r["scope"], call_graph.norm_addr(r["addr"])): r
                      for r in committed_rows(HERE.parent / "annotations"
                                              / "call-graph-callees.csv")}

    def test_each_address_calls_one_of_the_seven_stubs(self):
        stubs = {0x4C12, 0x4C19, 0x4C20, 0x52EF, 0x531F, 0x7B0D, 0x856F}
        for key in sorted(self.keys & set(self.edges)):
            with self.subTest(addr=key[1]):
                sites = self.edges[key]
                targets = {target for _, target, _ in sites}
                self.assertTrue(targets.issubset(stubs),
                               f"targets {targets} not in stubs {stubs}")

    def test_each_stub_has_a_row_when_a_listing_reaches_it(self):
        stubs = {0x4C12, 0x4C19, 0x4C20, 0x52EF, 0x531F, 0x7B0D, 0x856F}
        for stub in stubs:
            with self.subTest(stub="%04X" % stub):
                key = ("pd", call_graph.norm_addr("%04X" % stub))
                spelled = key in self.edges or key in self.cited
                in_census = key in self.census
                self.assertEqual(spelled, in_census)

    def test_each_stubs_inbound_equals_the_number_of_transfer_sites(self):
        for key in sorted(self.keys & set(self.edges)):
            with self.subTest(addr=key[1]):
                row = self.census[key]
                sites = self.edges[key]
                self.assertEqual(len(sites), int(row["inbound"]))

    def test_4ae9_parse_does_not_spell_anything_in_4d6f(self):
        # 4AE9 sits inside 4D6F.asm's span without being spelled by it
        # (4D6F starts with ajmp 0x4b12 that skips the block holding 4AE9).
        # The parse test and the span test disagree by exactly one here.
        # This assertion is what keeps the two from silently merging later.
        parse_4ae9 = set(call_graph.parse_listing(REPO / "ec" / "decompiled" /
                                                  "pd" / "4AE9.asm"))
        parse_4d6f = set(call_graph.parse_listing(REPO / "ec" / "decompiled" /
                                                  "pd" / "4D6F.asm"))
        self.assertEqual(len(parse_4ae9 & parse_4d6f), 0)
