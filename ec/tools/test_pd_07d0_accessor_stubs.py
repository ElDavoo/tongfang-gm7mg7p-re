#!/usr/bin/env python3
"""The seven `pd 0x07D0` accessor stubs, from the firmware bytes up.

`docs/findings/pd-07d0-accessor-stubs.md` is the write-up. What it rests on is
here, and it rests on nothing else: the seven unit entries are re-derived by a
byte scan of the committed firmware, the fourteen `lcall` sites are re-derived
the same way, and the annotation and export rows are read from the committed
CSVs. No Ghidra, no network, no hardware.

**The census case is the one that matters, and it asserts a relationship rather
than a count.** The seven stubs' inbound counts are the figure both write-ups
quote, and pinning them would be the CLAUDE.md hazard by name: a number every
tranche that seeds a caller function has to edit, held by a file that is not the
one being changed. So what is asserted is the rule `call_graph.py` implements --
a callee has a row exactly when some committed listing carries a transfer that
resolves to it, and that row's `inbound` is the number of transfer sites -- read
by running `call_graph.scan()` and comparing it against the committed
`call-graph-callees.csv` for these seven addresses. A run that seeds any of the
thirteen unspelled callers moves the relationship, not the literal, and this
suite follows it without a human editing anything here.

The last case reports, without failing, how many of the fourteen byte-scan sites
a committed listing spells. That is the number the write-up quotes, and it is
deliberately not an assertion: it is a measurement that the next tranche moves,
and a suite that failed on it would have to be edited by whoever seeds the next
caller.
"""
import collections
import csv
import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

from disasm8051 import mnemonic  # noqa: E402  (needs HERE on sys.path first)

FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"
PD_AT = 0x20000
# The whole unit, as bytes: `lcall 0xF739 ; mov dptr,#0x07D0 ; ret`. Matched as
# a byte string rather than decoded, because the point of the scan is that
# these seven are byte-identical -- asking the disassembler for a mnemonic
# would let it disagree with itself about an operand and quietly widen the set.
UNIT = bytes([0x12, 0xF7, 0x39, 0x90, 0x07, 0xD0, 0x22])
STUBS = (0x4C12, 0x4C19, 0x4C20, 0x52EF, 0x531F, 0x7B0D, 0x856F)
# The `lcall` encoding: 0x12 then a 16-bit big-endian target.
LCALL = 0x12


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


call_graph = load("call_graph")


def pd_image():
    return FIRMWARE.read_bytes()[PD_AT:]


def unit_entries(image):
    return [o for o in range(len(image) - len(UNIT) + 1)
            if image[o:o + len(UNIT)] == UNIT]


def lcall_sites(image, targets):
    """Every `lcall` site in the image resolving to one of `targets`."""
    wanted = set(targets)
    return [(o, (image[o + 1] << 8) | image[o + 2])
            for o in range(len(image) - 2)
            if image[o] == LCALL and ((image[o + 1] << 8) | image[o + 2]) in wanted]


def committed_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


class TestUnitBytes(unittest.TestCase):
    """The seven entries, derived from the firmware rather than transcribed."""

    @classmethod
    def setUpClass(cls):
        cls.image = pd_image()

    def test_the_seven_units_are_exactly_these_seven_addresses(self):
        self.assertEqual([0x4C12, 0x4C19, 0x4C20, 0x52EF, 0x531F, 0x7B0D, 0x856F],
                         unit_entries(self.image))

    def test_each_entry_disassembles_to_the_shape_the_name_states(self):
        # The byte scan above cannot see an operand, so this is the half that
        # holds the name to the code: `call_f739_then_return_dptr_07d0` claims
        # three instructions in that order and the disassembler has to agree.
        for entry in STUBS:
            with self.subTest(entry="%04X" % entry):
                got = [mnemonic(self.image, entry + off, entry)
                       for off in (0, 3, 6)]
                self.assertEqual(got, ["lcall 0xf739", "mov  dptr,#0x07d0",
                                       "ret"])

    def test_the_entry_is_three_bytes_before_the_dptr_load(self):
        # The retracted scan anchored on the `mov dptr` and found nothing; this
        # is the anchor the correction rests on, so it is a case and not a
        # sentence in the write-up.
        sites = [entry + 3 for entry in STUBS]
        self.assertEqual([], lcall_sites(self.image, sites))
        self.assertEqual(14, len(lcall_sites(self.image, list(sites) + list(STUBS))))


class TestCallerSites(unittest.TestCase):
    """The fourteen sites, and the per-stub distribution both write-ups quote."""

    @classmethod
    def setUpClass(cls):
        cls.image = pd_image()
        cls.sites = lcall_sites(cls.image, STUBS)

    def test_fourteen_sites_reach_the_family(self):
        self.assertEqual(14, len(self.sites))

    def test_two_sites_per_stub(self):
        # The byte scan is even where the census is not, and the write-up says
        # which is which rather than picking one phrasing. This is the even one.
        per_stub = collections.Counter(target for _, target in self.sites)
        self.assertEqual({stub: 2 for stub in STUBS},
                         {stub: per_stub[stub] for stub in STUBS})

    def test_every_site_continues_with_a_call(self):
        # The `ret` reasoning `walk-flow-follow.md` §2 rests on: thirteen of
        # the sites continue `lcall 0x347B ; lcall 0x104D` and the 14th, the
        # 0x4B1D one, continues `lcall 0x38CA ; lcall 0x3497`. Either way the
        # site is followed by calls, which is why the read of 0x07D0 happens
        # in the caller one call past it rather than in the stub.
        def following(offset):
            return [(self.image[offset + 4 + o] << 8) | self.image[offset + 5 + o]
                    for o in (0, 3)
                    if self.image[offset + 3 + o] == LCALL]

        for offset, _target in self.sites:
            with self.subTest(site="%05X" % offset):
                want = [0x38CA, 0x3497] if offset == 0x4B1D else [0x347B, 0x104D]
                self.assertEqual(want, following(offset))


class TestAnnotationRows(unittest.TestCase):
    """Every stub has a row, and the row states what basis it rests on."""

    @classmethod
    def setUpClass(cls):
        cls.rows = {(r["scope"], int(r["addr"], 16)): r
                    for r in committed_rows(HERE.parent / "annotations"
                                            / "ghidra-functions.csv")}

    def test_each_stub_has_a_pd_row(self):
        for stub in STUBS:
            with self.subTest(stub="%04X" % stub):
                self.assertIn(("pd", stub), self.rows)

    def test_each_row_carries_the_basis_the_write_up_claims(self):
        # `pd` rows may not be graded `ec-register` -- the PD image is a
        # separate program with its own XDATA map -- and `code-shape` is what
        # says "this name says what the code is, not what the register is".
        for stub in STUBS:
            with self.subTest(stub="%04X" % stub):
                row = self.rows[("pd", stub)]
                self.assertEqual("forwarder", row["type"])
                self.assertEqual("hand-decoded", row["basis"])
                self.assertEqual("code-shape", row["name_basis"])

    def test_each_rows_evidence_names_both_exported_files(self):
        for stub in STUBS:
            with self.subTest(stub="%04X" % stub):
                paths = [p.strip()
                         for p in self.rows[("pd", stub)]["evidence"].split(";")]
                self.assertEqual(
                    ["ec/decompiled/pd/%04X.asm" % stub,
                     "ec/decompiled/pd/%04X.c" % stub], paths)
                for path in paths:
                    self.assertTrue((REPO / path).is_file(), path)


class TestExportRows(unittest.TestCase):
    """Each stub reached the project, and the export says it was seeded."""

    @classmethod
    def setUpClass(cls):
        cls.index = {(r["program"], int(r["addr"], 16)): r
                     for r in committed_rows(HERE.parent / "decompiled"
                                             / "index.csv")}

    def test_each_stub_has_an_index_row_seeded_from_its_annotation(self):
        for stub in STUBS:
            with self.subTest(stub="%04X" % stub):
                row = self.index[("pd", stub)]
                self.assertEqual("annotation", row["seed_basis"])
                self.assertEqual("yes", row["annotated"])
                # 7 is the unit's own length. A larger size would mean the seed
                # swallowed a neighbour, which is the one way seeding at an
                # address that is not a clean entry shows up here.
                self.assertEqual(7, int(row["size"]))

    def test_each_stub_has_both_a_listing_and_a_decompile(self):
        for stub in STUBS:
            with self.subTest(stub="%04X" % stub):
                for suffix in (".asm", ".c"):
                    path = REPO / "ec" / "decompiled" / "pd" / ("%04X%s"
                                                                % (stub, suffix))
                    self.assertTrue(path.is_file(), str(path))


class TestCensusRelationship(unittest.TestCase):
    """A stub has a census row iff a committed listing transfers to it.

    The relationship, not a number. See the module docstring for why pinning
    the seven inbound counts would be the wrong shape for this file.
    """

    @classmethod
    def setUpClass(cls):
        cls.index = call_graph.load_index()
        cls.edges, _unresolved, _orphans, _total, _listings = call_graph.scan(
            cls.index)
        # `call_graph` keys everything on the normalised *string* address its
        # own `Index` builds, not on an int, so these keys have to match its.
        cls.keys = {("pd", call_graph.norm_addr("%04X" % s)) for s in STUBS}
        cls.census = {(r["scope"], call_graph.norm_addr(r["addr"])): r
                      for r in committed_rows(HERE.parent / "annotations"
                                              / "call-graph-callees.csv")}

    def test_a_row_exists_exactly_when_a_committed_listing_reaches_it(self):
        # Read off `call_graph.scan()`, the same walk the committed file was
        # built from. If the two ever disagree, one of them is wrong, and which
        # one is not something this case could report -- so it reports the
        # disagreement and stops.
        for key in sorted(self.keys):
            with self.subTest(stub=key[1]):
                self.assertEqual(key in self.census, key in self.edges)

    def test_each_rows_inbound_is_the_number_of_transfer_sites(self):
        for key in sorted(self.keys & set(self.edges)):
            with self.subTest(stub=key[1]):
                row = self.census[key]
                sites = self.edges[key]
                self.assertEqual(len(sites), int(row["inbound"]))
                forms = collections.Counter(form for _, _, form in sites)
                for form in ("lcall", "ljmp", "ajmp", "acall"):
                    self.assertEqual(forms[form], int(row[form]), form)

    def test_the_0x07d0_stubs_are_entered_only_from_a_listing_that_spells_one(self):
        # 0x4C20 is the one the census carries, and the site that gives it a
        # row is 0x4B1D, spelled at pd/4D6F.asm. The other six hold no row
        # because nothing committed spells a transfer to them -- which is a
        # fact about the export, not about the bytes, and the two write-ups
        # that quote the census have to say so.
        spelled = sorted(int(k[1], 16) for k in self.keys & set(self.edges))
        self.assertEqual([0x4C20], spelled)

    def test_report_without_failing(self):
        """How many of the fourteen sites a committed listing spells.

        Not an assertion. The number moves the moment a caller function is
        seeded, and a suite that failed on it would need editing by whoever
        does that -- which is the count-of-the-tree trap CLAUDE.md describes,
        reached from the other direction.
        """
        spelled = self.spelled_sites()
        print("\n  a committed listing spells %d of the 14 byte-scan sites%s"
              % (len(spelled),
                 (": " + ", ".join("%05X" % s for s in sorted(spelled)))
                 if spelled else ""))

    def spelled_sites(self):
        """The byte-scan `lcall` sites some committed listing actually spells.

        "Spells" means the listing's disassembly carries a transfer *at that
        address*, not that the address falls inside the function's span. The
        difference is the whole reason the census reads 1 of 14 while a
        `pd`-only span test says 2: `pd/4D6F.asm` runs 0x4A12-0x4E58, but its
        `ajmp 0x4b12` at 0x4A12 skips the block holding 0x4AE9, so nothing in
        that listing spells it -- one of the thirteen unspelled sites sits
        inside a span. The span has to be read in `pd`'s own address space; let
        it cross into `common` or the banks and seven more of the fourteen
        appear to fall in one, none of them at a `pd` instruction.
        Asking `parse_listing` is what keeps the two apart.
        """
        wanted = set(self.keys)
        out = set()
        for path in sorted((REPO / "ec" / "decompiled").glob("*/")):
            for listing in sorted(path.glob("*.asm")):
                scope = path.name
                for site, _form, target in call_graph.parse_listing(listing):
                    resolved = self.index.resolve(scope, target)
                    if resolved is not None and (resolved["program"],
                                                 resolved["_addr"]) in wanted:
                        out.add(int(site, 16))
        return out




if __name__ == "__main__":
    unittest.main()
