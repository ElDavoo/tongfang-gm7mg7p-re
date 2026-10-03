#!/usr/bin/env python3
"""Offline checks for `check_pd_site_bases.py`: the PD-image sites of the
`0x0436`/`0x0437` pair, the classifier's discrimination, and the writer-set
relationship the corrected `registers.yaml` note asserts.

**What is asserted is a claim, not a census.** Nothing here holds a count of
the tree. `0x0436`'s writers are asserted as a *relationship* between the note
in `registers.yaml` and the census in `site-resolution.csv` -- the two must
name the same set of sites and the same callees behind them -- so a ninth
writer fails by disagreeing with the other file rather than by needing a number
bumped. `0x0437`'s five PD sites are asserted *individually*, one case each,
so a regression names the site rather than reporting a tally that moved.
`TestTheWriterColumn` asserts the same relationship a third time, between
`xdata-0400-045f.md` §7's writer column and the census it is derived from:
an address with a handoff-resolved writer and a `—` cell is a cell saying an
address has no writers when the census says it has some, which is the defect
this change fixes one column to the left of where it was first caught. That
split is `CLAUDE.md`'s "no totals of the repository's own text" applied to
tests: a figure every landing change has to edit is a value every merge has to
resolve.

**The negative control is the part that makes the rest mean anything.** A
classifier that answered `stride-base` for every input would pass every
assertion about the real callee, since all five sites do hand DPTR to
`add_full_product_to_dptr`. So `TestTheClassifier` feeds the tool bodies built
from the committed listings' own bytes -- one with `movx a,@dptr`, one with
`movx @dptr,a`, one with both -- and requires `read`, `write` and `read+write`
back. The expected values are transcribed from `ec/decompiled/`, not read out
of the code under test; the derivation cases call the tool's own functions
rather than re-deriving them beside them, which is the failure
`test_pd_unannotated_census.py`'s module docstring records (a self-test that
re-derives the answer certifies the derivation, not the tool).

**Every negative in this file is "not found by this method".** `0x0436` having
no PD site is a statement about a `MOV DPTR,#imm16` byte scan, which cannot see
a computed DPTR or the unscanned `movx @Ri` + P2 paging form (issue #34). The
docstring of the case that says so carries the hedge, so dropping it from the
code changes what the test means rather than only what it prints. Nothing here
was measured on hardware: a `write` class is an instruction that stores, not
evidence that the PD or the EC acts on the value.
"""
import csv
import importlib.util
import os
from pathlib import Path
import re
import sys
import unittest

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import check_pd_site_bases as pdb  # noqa: E402
import check_site_resolution as csr  # noqa: E402
from disasm8051 import decode  # noqa: E402
from trace_xdata_refs import (classify, region_of, sites_for,  # noqa: E402
                              walk, walk_why)

REGISTERS_YAML = HERE.parent / "annotations" / "registers.yaml"
SITE_RESOLUTION = HERE.parent / "annotations" / "site-resolution.csv"
PD_BASES_CSV = HERE.parent / "annotations" / "pd-0436-0437-bases.csv"
PAGE_MD = HERE.parent / "annotations" / "xdata-0400-045f.md"
IMAGE = HERE.parent / "firmware" / "GMxMGxx_11.800"

# The five `0x0437` PD sites, transcribed from the image by
# `check_pd_site_bases.py ec/firmware/GMxMGxx_11.800` and readable off
# `ec/annotations/pd-0436-0437-bases.csv`. Listed individually rather than as a
# length so a regression names the site; this is a property of the committed
# firmware, which no change to this repository can move.
PD_0437_SITES = ("0x2358F", "0x239BC", "0x26FF1", "0x28724", "0x28802")

# `add_full_product_to_dptr`, byte for byte, from `ec/decompiled/pd/10BC.asm`.
# Transcribed from the listing rather than read out of the tool, so the case
# below fails if the classifier stops agreeing with the committed bytes.
ADD_FULL_PRODUCT = bytes.fromhex("a4 25 82 f5 82 e5 f0 35 83 f5 83 22")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def image():
    with open(IMAGE, "rb") as f:
        return f.read()


def note_for(regs, name):
    for entry in regs:
        if entry.get("name") == name:
            return " ".join(str(entry.get("note", "")).split())
    raise AssertionError("no register entry named %s" % name)


def read_registers():
    """`registers.yaml` as a list of entries, loaded here rather than at import.

    The note a case reads changes with every correction, so it is read per
    case rather than cached at module scope; a suite that read it once at
    import would pass against a stale tree.
    """
    import yaml
    with open(REGISTERS_YAML) as f:
        return yaml.safe_load(f)["registers"]


def pd_sites(d, addr):
    """The PD-image sites of `addr`, as file offsets, in file order.

    `region_of` does the image split rather than a hand-written offset range,
    which is what keeps the PD window at file `0x20000` and not `0x08000` --
    `ec/annotations/xdata-0400-045f.md` §6 warns that reading the boundary at
    `0x08000` misses sites, and a test that spelled the range out itself would
    be one edit away from repeating the mistake.
    """
    return [off for off in sites_for(d, addr)
            if region_of(off, True)[0] == "pd-image"]


class TestTheWriterSet(unittest.TestCase):
    """The corrected `registers.yaml` note against the committed census.

    The note said "the only writer is the zero-clear". `site-resolution.csv`,
    committed and never cross-read against it, carries the other seven. This
    asserts the two agree, as a relationship: every site the census resolves to
    `write` has to be a site the note names, and vice versa.
    """

    def setUp(self):
        self.census = [r for r in read_csv(SITE_RESOLUTION)
                       if r["addr"] == "0x0436"]
        self.writers = {r["runtime"]: r for r in self.census
                        if r["resolution"] == "write"}

    def _note(self, name):
        return note_for(read_registers(), name)

    def test_the_census_has_writers_to_relate_to(self):
        """A vacuous pass guard, in the shape `run-tests.sh` documents.

        If the address were renamed or its `resolution` column changed, every
        comparison below would hold trivially against an empty set, and the
        suite would exit 0 having checked nothing.
        """
        self.assertTrue(self.census,
                        "no site-resolution.csv rows for 0x0436")
        self.assertTrue(self.writers,
                        "no write-resolved 0x0436 sites to compare a note "
                        "against; the relationship below would hold vacuously")

    def test_every_write_site_is_a_distinct_function(self):
        """Each writing site is in its own routine.

        The note's defect was one routine named against many sites, so this is
        the property that makes "one writer" wrong rather than merely
        under-detailed: two sites sharing a routine would be one writer with
        two arms, and the note's wording would need a different correction.
        """
        functions = {r["function"] for r in self.writers.values()}
        self.assertEqual(len(functions), len(self.writers),
                         "a 0x0436 writing routine holds two of the writing "
                         "sites: %s" % sorted(functions))

    def test_the_direct_store_is_the_zero_clear_and_the_rest_are_handoffs(self):
        """One site stores at the site; the others hand DPTR to a pair writer.

        This is the distinction the corrected note draws, and it is drawn from
        the census's own two columns rather than from a number. A handoff
        resolved as a write is a store at the *callee's* entry, so the set of
        callees is what a reader has to check, not the eight sites.
        """
        direct = [r for r in self.writers.values() if r["depth1_class"] == "write"]
        self.assertTrue(direct, "no direct 0x0436 store in the census")
        for row in direct:
            self.assertEqual(row["callee"], "",
                             "a site classified as a direct store names a "
                             "callee: %s" % row["runtime"])
        for row in self.writers.values():
            if row["callee"]:
                self.assertIn(row["callee_function"], (
                    "0x888C write_r1r2_to_xdata_pair",
                    "0x889E write_r3r4_to_xdata_pair"),
                    "%s hands DPTR to %s, which this suite does not know to be "
                    "a pair writer" % (row["runtime"], row["callee_function"]))

    def test_the_note_carries_the_correction_beside_the_original(self):
        """The retraction is marked, not made by silent edit.

        `registers.yaml`'s wrong sentence is left where it was and the
        correction is added beside it in the file's own dated form, which is
        what `docs/findings.md` §4a-4d asks for and what the rest of the file
        already does. So the assertion is that the correction is *present* and
        *dated* -- not that the old wording is gone, since leaving the wrong
        version visible is the point.
        """
        note = self._note("XDATA_0436_PAIR")
        self.assertIn("*** 2026-10-03 (issue #213) ***", note,
                      "registers.yaml carries no dated correction for "
                      "XDATA_0436_PAIR")
        self.assertIn("The only writer is in the zero-clear", note,
                      "the original claim was edited away rather than left "
                      "visible with the correction beside it")
        self.assertIn("is wrong", note,
                      "the correction does not say the claim above it is "
                      "wrong")

    def test_the_correction_distinguishes_the_direct_store(self):
        """The corrected claim is the smallest true one.

        "The only *direct* store" is what the evidence supports: one site
        stores at the site and the others store at a callee. Asserted as the
        word being present rather than as a sentence, so a reworded correction
        does not fail and a reverted one does.
        """
        self.assertIn('"only writer" half above is wrong',
                      self._note("XDATA_0436_PAIR"))
        self.assertIn("AT the site", self._note("XDATA_0436_PAIR"),
                      "the correction does not say what makes the remaining "
                      "store the only one")

    def test_the_neighbouring_note_is_corrected_the_same_way(self):
        """`BAT_VOLTAGE_MV` repeats the identical false sentence.

        It is a separate entry one below and was corrected in the same change:
        the defect is the file's, not this address's, and leaving one instance
        standing would leave the note wrong about `0x0438` in the same way.
        The census decides whether a correction is needed, so the case fails
        if the claim is ever true -- and passes only if the correction is
        actually there.
        """
        writers = [r for r in read_csv(SITE_RESOLUTION)
                   if r["addr"] == "0x0438" and r["resolution"] == "write"]
        self.assertTrue(writers,
                        "no write-resolved 0x0438 sites, so the note's claim "
                        "is not contradicted by anything")
        note = self._note("BAT_VOLTAGE_MV")
        self.assertIn("The only writer is the shared zero-clear", note,
                      "the original claim was edited away rather than left "
                      "visible")
        self.assertIn("*** 2026-10-03 (issue #213) ***", note,
                      "registers.yaml carries no dated correction for "
                      "BAT_VOLTAGE_MV")


class TestThePdSites(unittest.TestCase):
    """Each `0x0437` PD site, on its own.

    One case per site rather than one over a list, so a regression names the
    site: an assertion over five rows that fails says only that the count moved,
    and the count is the thing this file deliberately does not hold.
    """

    def setUp(self):
        self.d = image()
        self.rows = {r["file_offset"]: r
                     for r in read_csv(PD_BASES_CSV)}
        self.functions = csr.load_functions()

    def _classify(self, file_offset):
        off = int(file_offset, 16)
        return pdb.classify_site(self.d, off, "pd-image", self.functions)

    def _case(self, file_offset):
        with self.subTest(site=file_offset):
            row = self.rows.get(file_offset)
            self.assertIsNotNone(
                row, "no committed row for the PD site at %s" % file_offset)
            verdict = self._classify(file_offset)
            self.assertEqual(verdict["class"], pdb.STRIDE_BASE,
                             "%s classified %s from a fresh decode"
                             % (file_offset, verdict["class"]))
            self.assertEqual(row["class"], pdb.STRIDE_BASE,
                             "the committed row for %s says %s"
                             % (file_offset, row["class"]))
            return verdict

    def test_the_five_sites_are_all_stride_base(self):
        """Every `0x0437` PD site names a base, and the reason names why.

        The reason is the load-bearing half: a row that said `stride-base` with
        no callee would be an assertion, and this is a decode of
        `add_full_product_to_dptr`'s own committed bytes. Its `size` is checked
        too, because that is the span the decode was bounded by.
        """
        self.assertEqual(
            {f"0x{off:05X}" for off in pd_sites(self.d, 0x0437)},
            set(PD_0437_SITES),
            "the PD sites of 0x0437 in the image are not the ones this suite "
            "asserts about")
        for file_offset in PD_0437_SITES:
            with self.subTest(site=file_offset):
                verdict = self._case(file_offset)
                self.assertEqual(verdict["callee"], "0x10BC",
                                 "%s hands DPTR somewhere else" % file_offset)
                self.assertEqual(verdict["callee_name"],
                                 "add_full_product_to_dptr")
                self.assertEqual(verdict["callee_size"], 12,
                                 "the committed export's size moved")
                self.assertEqual(verdict["movx"], "none")
                self.assertIn("base", verdict["why"])

    def test_the_callee_carries_no_movx_in_its_own_bytes(self):
        """`add_full_product_to_dptr` is pointer arithmetic, checked on bytes.

        The whole finding rests on this routine not dereferencing, so it is
        read out of the committed listing's bytes and asserted directly rather
        than through the tool's own verdict -- and against `decode_export`'s
        bounds, since a decode that ran past the `ret` would find a `movx`
        belonging to the next export.
        """
        body = pdb.decode_export(self.d, 0x210BC, 0x10BC, 12)
        self.assertEqual(len(body), 7,
                         "the committed listing is 7 instructions; a decode "
                         "of a different length is decoding other bytes")
        self.assertEqual(pdb.movx_class(body), "",
                         "add_full_product_to_dptr contains a movx, so the "
                         "five sites are dereferences and not bases")
        self.assertEqual(body[-1][2].split()[0], "ret")

    def test_0436_has_no_pd_site(self):
        """No PD-image site at all -- "not found by this method", not "absent".

        This is half of the asymmetry the issue asked about, and the hedge is
        the case's own subject. `sites_for` is a `MOV DPTR,#imm16` byte scan: a
        DPTR the PD builds arithmetically has no site, and the indirect
        `movx @Ri` + P2 paging form of issue #34 is not scanned at all. So the
        assertion is that this method finds none, which is what a recorded zero
        in `static_refs_pd_image` means, and not that the PD never touches the
        byte.
        """
        self.assertEqual(pd_sites(self.d, 0x0436), [],
                         "a PD-image site of 0x0436 exists in the image")

    def test_0434_appears_beside_the_pair(self):
        """The neighbouring stride base is in the artifact too.

        `0x0434` is censused alongside the pair so the resemblance is visible
        in the committed file rather than asserted in prose: it is a stride
        base too, and `ec/annotations/pd-base-strides.csv` already lists it
        beside `0x0437` on its `0x60` row. A reader should not have to take
        that from a write-up.
        """
        addrs = {r["addr"] for r in read_csv(PD_BASES_CSV)}
        self.assertIn("0x0434", addrs,
                      "the artifact does not carry 0x0434, so the stride-base "
                      "shape beside the pair is prose rather than data")
        self.assertNotIn("0x0436", addrs,
                         "0x0436 has no PD site and so no row; a row for it "
                         "would be a fabricated finding")


class TestTheClassifier(unittest.TestCase):
    """The discrimination, against bodies built from committed bytes.

    Without these, every assertion above would hold of a classifier that
    returned `stride-base` for anything -- which is what the tool did for one
    run, when `decode()` was handed a fixed instruction count instead of the
    export's own `size` and ran past `add_full_product_to_dptr`'s `ret` into
    the next routine's `movx`.
    """

    def test_a_body_that_reads_is_a_read(self):
        """`read_xdata_pair_to_r1r2`, byte for byte from bank1/8886.asm."""
        body = bytes.fromhex("e0 f9 a3 e0 fa 22")
        self.assertEqual(pdb.movx_class(decode(body, 0, 32)), pdb.READ)

    def test_a_body_that_stores_is_a_write(self):
        """`write_r1r2_to_xdata_pair`, byte for byte from bank1/888C.asm."""
        body = bytes.fromhex("e9 f0 a3 ea f0 22")
        self.assertEqual(pdb.movx_class(decode(body, 0, 32)), pdb.WRITE)

    def test_a_body_that_does_both_is_read_write(self):
        """Both directions in one body are reported as both, not one of them.

        A classifier that reported the first `movx` it saw would call this a
        read and silently lose the store; the census would then under-report
        writers rather than fail.
        """
        body = bytes.fromhex("e0 f0 22")
        self.assertEqual(pdb.movx_class(decode(body, 0, 32)), pdb.READ_WRITE)

    def test_a_body_with_no_movx_is_no_access(self):
        """The answer `stride-base` rests on, asserted on its own.

        `""` is a result here and not a failure: it is what distinguishes a
        pointer routine from an accessor, and it is the whole reason the five
        sites are bases.
        """
        self.assertEqual(pdb.movx_class(decode(ADD_FULL_PRODUCT, 0, 32)), "")
        self.assertEqual(pdb.movx_class(decode(bytes.fromhex("22"), 0, 32)), "")

    def test_an_empty_body_is_no_access(self):
        """Zero instructions is not a read, and must not read as one."""
        self.assertEqual(pdb.movx_class(decode(b"", 0, 32)), "")

    def test_a_data_block_is_not_counted_as_a_movx(self):
        """`disasm8051.decode` yields inline-arg and case-table items too.

        A data byte can be `0xE0` without being a `movx`, so counting
        `raw[0]` blindly would let a block read as an access. The tool refuses
        the body instead, which is the honest answer: this classifier cannot
        decide it.
        """
        seq = [(0, b"\xe0", "inline args: e0")]
        self.assertEqual(pdb.movx_class(seq), pdb.UNRESOLVED)

    def test_the_decode_stops_at_the_first_control_flow_instruction(self):
        """The bound that keeps a tail jump from reading the next routine.

        `dptr_0428_plus_60a` ends in `ljmp 0x10bc` and the bytes after the jump
        belong to the next routine even though the export's `size` span
        includes them. One of `0x0434`'s sites enters that export mid-routine,
        which is where a size bound alone would have run on.
        """
        body = pdb.decode_export(image(), 0x235AC, 0x35AC, 11)
        self.assertEqual(pdb.movx_class(body), pdb.READ,
                         "dptr_0428_plus_60a's own first instruction is a "
                         "movx; a decode that stopped short would read as "
                         "stride-base")
        self.assertEqual(body[-1][2].split()[0], "ljmp",
                         "the decode ran past the routine's own jump")
        # Entered four bytes in, as a PD site does.
        mid = pdb.decode_export(image(), 0x235B0, 0x35B0, 7)
        self.assertEqual(pdb.movx_class(mid), "",
                         "from 0x35B0 the routine is pointer arithmetic, and "
                         "it is the same routine")

    def test_every_class_the_tool_can_emit_is_named(self):
        """A class nothing in `CLASSES` names would print in a committed cell.

        The CSV is the artifact a reader takes without re-running anything, so
        its vocabulary has to be the module's, and this is where a new class
        gets added to both at once.
        """
        for verdict in ({"class": pdb.STRIDE_BASE}, {"class": pdb.READ},
                        {"class": pdb.WRITE}, {"class": pdb.READ_WRITE},
                        {"class": pdb.UNRESOLVED}):
            self.assertIn(verdict["class"], pdb.CLASSES)


class TestTheSiteScanner(unittest.TestCase):
    """The site's own decode, so a `stride-base` is not the walk's failure."""

    def test_the_site_window_is_a_handoff_not_an_access(self):
        """Each site hands DPTR on; none dereferences where it sits.

        This is the boundary of the claim. The tool reads the *callee's* body,
        so if a site dereferenced DPTR itself the class would be about the site
        and the reasoning would be a different one. `classify()` over the real
        walk is what settles that, rather than the tool's verdict restated.
        """
        d = image()
        for off in pd_sites(d, 0x0437):
            access = classify(walk(d, off))
            self.assertTrue(access.startswith("DPTR handed"),
                            "PD site at file 0x%05X resolves to %r, which "
                            "this suite's reasoning does not cover"
                            % (off, access))

    def test_a_site_that_dereferences_is_not_a_base(self):
        """The bank1 zero-clear, read through the same classifier.

        `FUN_CODE_b88c`'s `movx @DPTR,A` at the site is a store, and running
        the PD classifier over it has to say so. It is the negative control for
        the whole tool from the other side: the five PD sites and this one are
        the same code shape, and only one of them dereferences.
        """
        d = image()
        off = 0x138BF          # bank1 0xB8BF, the `movx @dptr,a` in b88c
        self.assertEqual(region_of(off, True)[0], "bank1")
        verdict = pdb.classify_site(d, off, "bank1", csr.load_functions())
        self.assertEqual(verdict["class"], pdb.WRITE,
                         "a site whose own window stores was classified %s"
                         % verdict["class"])
        self.assertEqual(verdict["callee"], "",
                         "a store at the site names no callee")


class TestTheCommittedArtifact(unittest.TestCase):
    """The CSV a reader takes without re-running anything."""

    def test_the_check_reproduces_the_committed_csv(self):
        """`--check` is the gate; this is the same comparison as a test.

        Run through `csv_text` rather than by shelling out, so a failure names
        the differing bytes instead of an exit status.
        """
        d = image()
        with open(PD_BASES_CSV, newline="") as f:
            committed = f.read()
        fresh = pdb.csv_text(d, list(pdb.DEFAULT_ADDRS), True,
                             csr.load_functions())
        self.assertEqual(committed, fresh,
                         "the committed census differs from a fresh one")

    def test_every_row_names_a_class_and_no_row_is_blank(self):
        """A row with an empty `class` is a row that says nothing."""
        for row in read_csv(PD_BASES_CSV):
            with self.subTest(site=row["file_offset"]):
                self.assertIn(row["class"], pdb.CLASSES)
                self.assertTrue(row["runtime"].startswith("0x"))

    def test_an_unresolved_row_carries_its_reason(self):
        """`unresolved` is "not found by this method", so it has to say by what.

        A bare `unresolved` would read as a verdict on the site rather than as
        the limit of a method, which is the difference `registers.yaml`'s own
        preamble and `docs/findings.md` §4c turn on.
        """
        for row in read_csv(PD_BASES_CSV):
            if row["class"] == pdb.UNRESOLVED:
                with self.subTest(site=row["file_offset"]):
                    self.assertTrue(row["why"],
                                    "an unresolved row with no reason")


class TestTheWriterColumn(unittest.TestCase):
    """§7's writer column against the census that column is derived from.

    The column's definition says a handoff-resolved store is one the site does
    not perform at its own instruction, and §1's argument is that a cell
    reading as "no writers" when the census carries some is the same defect
    one column to the left of where it was first caught. That is a claim about
    the table, and it is checkable against `site-resolution.csv` rather than
    against a number written down anywhere.

    Scoped to addresses with at least one **handoff-resolved** writer, which is
    the form this change added and the one whose absence is the defect: an
    address whose only writers are direct ones is already named in the cell,
    and asserting over those would hold this suite to a convention on rows
    this change did not touch.

    Asserted as that relationship and not as a tally. The cases below hold
    "every handoff-resolved writer is annotated" and "the annotated count
    agrees with the census"; none holds a figure for how many such addresses
    exist, so a landing change that resolves one more site to a handoff write
    fails by disagreeing with the census rather than by needing a count edited
    here.
    """

    def setUp(self):
        self.table = read_table_rows(PAGE_MD)
        self.handoff = {}
        for row in read_csv(SITE_RESOLUTION):
            addr = int(row["addr"], 16)
            if not 0x400 <= addr <= 0x45F:
                continue
            if row["resolution"] == "write" and row["callee"]:
                self.handoff.setdefault(addr, []).append(row)

    def test_the_table_has_the_rows_to_check(self):
        """A vacuous pass guard, for the same reason as the writer-set one.

        If §7's table stopped parsing, or the census stopped carrying
        `0x0400`-`0x045F` rows, every comparison below would hold against
        nothing and the suite would exit 0 having checked nothing.
        """
        self.assertTrue(self.table, "no §7 rows parsed out of %s" % PAGE_MD)
        self.assertTrue(self.handoff,
                        "no handoff-resolved writers in the page's range; the "
                        "relationship below would hold vacuously")

    def test_no_handoff_resolved_address_is_left_unannotated(self):
        """The `—` in a writer cell means "no writers", so it has to be true.

        A handoff-resolved `write` row with a `—` cell is the cell and the
        census disagreeing, and the table is what a reader takes without
        re-running `check_site_resolution.py`. This is the property `0x0434`
        failed before: three handoff-resolved writers, cell `—`. Asserted per
        address so the failure names which row is wrong.
        """
        for addr in sorted(self.handoff):
            with self.subTest(addr="0x%04X" % addr):
                row = self.table.get(addr)
                self.assertIsNotNone(row, "no §7 row for 0x%04X" % addr)
                self.assertNotEqual(row[1].strip(), "—",
                                    "0x%04X has %d handoff-resolved writer(s) "
                                    "in site-resolution.csv and a `—` writer "
                                    "cell" % (addr, len(self.handoff[addr])))

    def test_an_annotated_cell_names_every_handoff_routine(self):
        """Naming the routine is the column's job; the count alone is not enough.

        A cell that gave the count without the routines would satisfy the case
        above and tell a reader nothing they could act on, so this one holds
        the stronger property: each function holding a handoff-resolved write
        for the address is named in that address's cell.
        """
        for addr, rows in sorted(self.handoff.items()):
            cell = self.table.get(addr, ("", ""))[1]
            with self.subTest(addr="0x%04X" % addr):
                for row in rows:
                    name = row["function"].split(None, 1)[-1]
                    self.assertIn(name, cell,
                                  "0x%04X's writer cell names no routine for "
                                  "the site at %s in %s"
                                  % (addr, row["runtime"], name))

    def test_the_cell_counts_the_handoff_writers_the_census_finds(self):
        """The count in the cell is the census's, in the form the definition names.

        `depth1_class == "write"` is a store at the site's own instruction and
        the cell names that routine; a store resolved through a callee is not
        visible as an instruction at the site, which is what the
        `N handoff-resolved` marker is for. A row with both appends the count,
        a row with only handoff-resolved writers leads with it. Asserted
        against the census's own columns, so a site that moves between the two
        forms fails here rather than sitting in a cell that no longer describes
        it.
        """
        for addr, rows in sorted(self.handoff.items()):
            cell = self.table.get(addr, ("", ""))[1]
            direct = any(r["depth1_class"] == "write" for r in
                         read_csv(SITE_RESOLUTION)
                         if int(r["addr"], 16) == addr
                         and r["resolution"] == "write")
            with self.subTest(addr="0x%04X" % addr):
                if direct:
                    self.assertIn("+ %d handoff-resolved" % len(rows), cell,
                                  "0x%04X has a direct store and %d "
                                  "handoff-resolved one(s); its cell does not "
                                  "append the count" % (addr, len(rows)))
                else:
                    self.assertIn("%d handoff-resolved:" % len(rows), cell,
                                  "0x%04X has no direct store and %d "
                                  "handoff-resolved one(s); its cell does not "
                                  "lead with the count" % (addr, len(rows)))

    def test_a_handoff_count_never_exceeds_the_sites_the_row_carries(self):
        """The count is of sites, so it cannot exceed the row's own site total.

        Cheap, and it catches the failure a hand-typed count invites: a count
        larger than the number of EC-side sites the row carries is arithmetic
        that has drifted from the image, whatever the prose beside it says.
        """
        for addr, rows in sorted(self.handoff.items()):
            ec = self.table.get(addr, ("", ""))[0]
            with self.subTest(addr="0x%04X" % addr):
                self.assertLessEqual(len(rows), int(ec),
                                     "0x%04X: %d handoff-resolved writers but "
                                     "the row counts %s EC-side sites"
                                     % (addr, len(rows), ec))


def read_table_rows(path):
    """§7's per-address rows, as `{addr: (ec_count, writer_cell)}`.

    Scoped to the one table between its header row and the next `##` heading,
    because the file carries several address tables and a document-wide match
    picks up rows from the others -- including a two-cell table that would
    otherwise be read as a row whose writer column is a prose sentence. The
    writer cell is the one after `unr`, with the optional trailing
    `record seeds` column dropped.
    """
    lines = Path(path).read_text().splitlines()
    start = next(i for i, ln in enumerate(lines)
                 if ln.startswith("| addr | EC | PD |"))
    rows = {}
    for line in lines[start + 2:]:
        if line.startswith("## "):
            break
        m = re.match(r"\| `0x([0-9A-Fa-f]{4})`(?: \*\(not entered\)\*)?"
                     r" \|(.*)\|\s*$", line)
        if m:
            cells = [c.strip() for c in m.group(2).split("|")]
            rows[int(m.group(1), 16)] = (cells[0], cells[10])
    return rows


if __name__ == "__main__":
    unittest.main()