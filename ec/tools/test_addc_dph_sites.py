#!/usr/bin/env python3
"""The six `addc A,#imm ; mov DPH,A` sites, their predecessors, and the two
pages the residual is about, on `addc_dph_sites.py`'s own.

**The claim, and what it is not a census of.** The load-bearing cases assert
*which addresses reach page `0x08` or page `0x1C`* and *what each site's
accumulator is carrying* -- the six addresses `xdata-1c3x-consumers.md` §6.2
names as its residual, transcribed from the write-up and the exported listings
rather than generated from the scan. It deliberately does **not** assert how
many `34 xx f5 83` sites the tool finds in the image: that is a count of the
tree, every merge that changes a byte would have to edit it, and `CLAUDE.md`
records four times over that such a line is where merge conflicts start. "None
of these six addresses builds page `0x08` or page `0x1C` by this construction"
is a finding; "the tool finds N sites" would be a maintenance tax wearing a
finding's clothes.

Every other case builds its own buffer through the local `fixture()` helper
rather than pointing at the firmware, for the reason
`test_check_site_resolution.py` gives: this tool's whole population is "an
opcode byte somewhere", so a fixture that *is* the image would be testing the
image, and would keep doing so only until the bytes around some address in it
changed.

The one class that does read the committed image is `CommittedTableTests`, and
it is the one that has to: `--check` reproducing
`../annotations/xdata-addc-dph-residual-sites.csv` byte for byte is what makes
the write-up's per-site table an assertion rather than a paragraph, and a suite
that only ever fed the tool a fixture could not tell whether that table still
describes the image.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# addc_dph_sites imports disasm8051 and trace_xdata_refs by bare module name,
# the way computed_dptr_sites does, so the tool directory has to be on the path
# before it is loaded rather than after.
sys.path.insert(0, str(HERE))
import addc_dph_sites as A       # noqa: E402
import disasm8051 as D           # noqa: E402
import trace_xdata_refs as T     # noqa: E402

FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"
COMMITTED_CSV = REPO / "ec" / "annotations" / "xdata-addc-dph-residual-sites.csv"

# The six sites `xdata-1c3x-consumers.md` §6.2 names as its residual, with the
# immediate each one's `addc` carries. Spelled out here rather than derived
# from the scan, because a list generated from the tool would agree with the
# tool by construction and this class's whole claim would be that it agrees with
# the write-up instead.
RESIDUAL = [(0x2266, 0x0D), (0x2270, 0x0D), (0x2278, 0x0D),
            (0x22DF, 0x0D), (0x28EF, 0x2A), (0x2912, 0x2A)]
# The three call targets the four `xx`=`0x0D` sites call, and which sites call
# which. Three distinct callees rather than one: the document this pass corrects
# named `0x2A7B` for all four, which would leave a reader checking one routine
# and assuming it covered the other three.
CALLS = {0x2266: 0x2A7B, 0x2270: 0x2A7B, 0x2278: 0x2A8F, 0x22DF: 0x2A7D}
# The two `xx`=`0x2A` sites and the instruction each one's `mov a,r6` is at.
# The register is named here because that is what the tool's cell carries: the
# tool reports the register and refuses to read it, so the value comes from the
# write-up's argument against the `mov r6,#0x00` three instructions earlier.
REG_SITES = {0x28EF: (0x28EE, "r6"), 0x2912: (0x2911, "r6")}


def clr_a() -> bytes:
    # clr a -- clears the accumulator and leaves the carry alone, which is
    # why every `dph_set` in this suite is a two-element set.
    return bytes([0xE4])


def addc(v: int) -> bytes:
    return bytes([0x34, v])            # addc a,#v -- carry-dependent


def mov_dph() -> bytes:
    return bytes([0xF5, 0x83])        # mov 0x83,a


def lcall(target: int) -> bytes:
    return bytes([0x12, target >> 8, target & 0xFF])


def mov_a_r6() -> bytes:
    return bytes([0xEE])              # mov a,r6


def mov_a(v: int) -> bytes:
    return bytes([0x74, v])


def clr_c() -> bytes:
    return bytes([0xC3])              # clr c -- the carry, and not the accumulator


def mov_dptr(v: int) -> bytes:
    return bytes([0x90, v >> 8, v & 0xFF])   # mov dptr,#v -- operand bytes


def movx_store() -> bytes:
    return bytes([0xF0])              # movx @dptr,a


def movx_load() -> bytes:
    return bytes([0xE0])              # movx a,@dptr


def movc() -> bytes:
    return bytes([0x93])              # movc a,@a+dptr -- a CODE read


def fixture(*insns: bytes, size: int = 0x80) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_computed_dptr_sites.py` and
    `test_find_indirect_xdata.py` each carry a copy of, and for the same
    reason. The tail past the last instruction is filled with `0x00`, which the
    opcode table's 1-byte `nop` absorbs, so a walk over it is a run of nops
    rather than a decode of whatever byte happened to be there -- which is what
    lets a case's site offset be the offset the fixture laid the site down at.
    """
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def rows_for(img: bytes):
    """The residual rows for a fixture image, as offset -> row."""
    return {r["offset"]: r for r in A.residual(img, pd_verified=False)}


def only_row(img: bytes) -> dict:
    """The fixture's single residual row.

    A fixture's site offset is whatever its instruction lengths make it, which
    is a thing to read off the row rather than to hardcode in each case -- a
    case that asserted `rows[0]` was asserting an offset, and the offsets move
    whenever an instruction in the fixture does.
    """
    rows = rows_for(img)
    assert len(rows) == 1, f"expected one residual site, got {sorted(rows)}"
    return next(iter(rows.values()))


class TheResidualTests(unittest.TestCase):
    """The six addresses, their immediates, and the two pages, read off the
    committed image — plus the one `clr a` site the corrected page rule puts on
    page `0x08`.

    Each expected value here is transcribed by hand from the exported listings
    and `disasm8051.py`, so the class asserts agreement between the write-up
    and the tool rather than the tool with itself.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.rows = {r["offset"]: r for r in A.residual(cls.d, pd_verified=False)}

    def test_the_six_residual_addresses_are_the_six_named(self):
        # A **claim**, not a census: these six reach neither page, which is the
        # issue's whole question. The census that produced them is the tool's,
        # and `CensusSplitTests` below is what pins the 58/6 split.
        self.assertEqual(sorted(self.rows), [a for a, _ in RESIDUAL])

    def test_each_site_carries_the_immediate_the_listings_show(self):
        for addr, imm in RESIDUAL:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(self.rows[addr]["imm"], imm)

    def test_none_of_the_six_builds_page_0x08(self):
        for addr, _imm in RESIDUAL:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(self.rows[addr]["reaches_0x08"], "no")
                self.assertNotIn(0x08, self.rows[addr]["pages"])

    def test_none_of_the_six_builds_page_0x1c(self):
        for addr, _imm in RESIDUAL:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(self.rows[addr]["reaches_0x1c"], "no")
                self.assertNotIn(0x1C, self.rows[addr]["pages"])

    def test_the_four_low_byte_sites_name_their_own_call_target(self):
        # Three distinct callees, not one. A single-cell implementation would
        # pass "the four are named" while leaving the reader to assume the one
        # routine it printed covers the other three.
        for addr, target in CALLS.items():
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(self.rows[addr]["preceded_by"],
                                 f"`lcall 0x{target:04x}`")

    def test_the_four_low_byte_sites_are_followed_by_three_distinct_callees(self):
        self.assertEqual(len(set(CALLS.values())), 3)

    def test_the_two_high_byte_sites_name_the_register_they_read(self):
        for addr, (prev, reg) in REG_SITES.items():
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(self.rows[addr]["preceded_by"],
                                 f"`mov a,{reg}` at 0x{prev:05X} "
                                 f"-- `A` carries {reg}, {A.REG_CARRIES}")

    def test_only_one_of_the_six_stores_through_the_computed_pointer(self):
        # `0x2266` is the one writer. The other three `0x0D` sites read, and the
        # two `0x2A` sites feed a `movc` -- a CODE read -- so a population
        # filtered on `movx @dptr,a` would have found one site and called it a
        # census.
        stores = [a for a, r in self.rows.items() if r["access"].startswith("store")]
        self.assertEqual(stores, [0x2266])

    def test_the_two_high_byte_sites_feed_a_movc_and_not_a_movx(self):
        # The page-independent half of the closure: whatever `DPH` held, the
        # pointer is consumed by a `movc`, and the `movx` after it is aimed at a
        # hard literal. So neither site can be an XDATA writer at all.
        for addr in REG_SITES:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(
                    self.rows[addr]["access"],
                    "CODE read via `movc a,@a+dptr`, not an XDATA access")

    def test_the_page_set_is_two_elements_for_every_residual_site(self):
        # The set is never collapsed to its low member. `addc` reads the carry
        # and nothing here establishes it, so a single-value cell would be a
        # claim the method did not support -- the retraction shape.
        for addr, _imm in RESIDUAL:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(len(self.rows[addr]["pages"]), 2)

    def test_the_clr_a_site_that_builds_page_0x08_is_the_one_the_merge_found(self):
        # The corrected rule is only worth anything if it agrees with the
        # image, so here it does: read off the committed firmware, the one
        # `clr a` site whose set holds `0x08` is `0x8360`, the page-`0x08`
        # store this pass is built around. A claim about *which* site, not a
        # count of the tree -- what is load-bearing is that it is the known
        # one and that it is alone, and both are what makes the `clr a` half
        # resolve to this site rather than to nothing.
        rows = [r for r in (A.site_row(self.d, at, False)
                            for at in A.census(self.d))
                if r["preceded_by"] == A.CLR_A_SHAPE and 0x08 in r["pages"]]
        self.assertEqual([r["offset"] for r in rows], [0x8360])
        self.assertEqual(rows[0]["dph_set"], "{0x08, 0x09}")
        self.assertEqual(rows[0]["access"], "store via `movx @dptr,a`")

    def test_no_census_site_is_in_the_pd_image(self):
        # A scope claim, not a count. The PD image is a **separate 8051
        # program** with its own XDATA map (`trace_xdata_refs.REGIONS`), so a
        # `DPH` built there is not a byte of the EC's XDATA and a page it
        # reaches says nothing about the page of that number here.
        #
        # This is worth a test of its own because the exclusion is invisible in
        # the residual: every one of the PD image's own `34 xx f5 83` sites is
        # preceded by `clr a`, so folding the region in would change the
        # census without changing this document's six rows, and nothing else
        # would notice.
        pd_span = next((lo, hi) for name, lo, hi, _b, _h
                       in T.REGIONS if name == "pd-image")
        in_pd = [a for a in A.census(self.d) if pd_span[0] <= a < pd_span[1]]
        self.assertEqual(in_pd, [])


class CalleeShapeTests(unittest.TestCase):
    """The three call targets, read with the repository's own disassembler.

    The closure rests on each of them ending `clr a ; ret`, so A is `0` on
    return whatever the caller held. That is a claim about the bytes and not
    about the export boundary, so it is checked here against `disasm8051.py` --
    the oracle `ec/annotations/computed-dptr-sites.md` names -- rather than
    against the tool under test.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()

    def mnemonic(self, at: int) -> str:
        return " ".join(D.mnemonic(self.d, at).split())

    def body(self, at: int, cap: int = 12) -> list:
        """Mnemonics decoded forward from `at` up to and including its `ret`.

        Stepped by `OPCODE_LEN` rather than by one byte, which is the whole
        point: the three callees share a tail, and a walk that advanced a byte
        at a time would decode the operand of `mov a,#0x90` as an instruction
        and report a body none of them has.

        Walked to the `ret` rather than to a fixed instruction count because
        the three differ in length -- `0x2A8F` is one instruction longer than
        `0x2A7D` before the shared tail -- and a fixed count is a place for
        the count to be quietly wrong about one of them.
        """
        out, at = [], at
        for _ in range(cap):
            if at >= len(self.d):
                break
            out.append(self.mnemonic(at))
            if self.d[at] == 0x22:       # ret -- the routine's own end
                break
            at += D.OPCODE_LEN[self.d[at]]
        return out

    def test_each_callee_returns_with_the_accumulator_cleared(self):
        for target in set(CALLS.values()):
            with self.subTest(target=f"0x{target:04X}"):
                # `clr a` then `ret` is what makes A `0` on entry to the addc,
                # whatever the caller held -- the closure's whole premise, and
                # one the raw bytes settle rather than the export boundary.
                body = self.body(target)
                self.assertIn("clr a", body)
                self.assertEqual(body[body.index("clr a") + 1], "ret")
                self.assertEqual(body[-1], "ret")

    def test_the_three_callees_are_three_distinct_addresses(self):
        self.assertEqual(len({t for t in CALLS.values()}), 3)


class CensusSplitTests(unittest.TestCase):
    """The `clr a` / not-`clr a` split, on fixtures.

    On the committed image this is 58 and 6; here it is built so the split is
    tested as the *rule* rather than as the number, which is the shape that
    does not need editing when the firmware changes.
    """

    def test_a_clr_a_site_is_not_in_the_residual(self):
        # `clr a` is what splits the population, so a site behind one is the
        # half the residual leaves out -- whatever its page set is. The set
        # itself is checked in the case below, on `site_row` directly, because
        # `residual()` filters these rows out and so cannot show it.
        img = fixture(clr_a(), addc(0x0F), mov_dph())
        self.assertEqual(rows_for(img), {},
                         "a `clr a` site must not be in the residual")

    def test_a_clr_a_site_still_builds_two_pages_and_not_one(self):
        # `clr a` pins A to 0 and does **not** touch the carry, so the site
        # builds `imm` or `imm+1` -- not the immediate alone. Both members
        # count: a set of that shape holds page `P` when the immediate is `P`
        # **or** `P-1`, so a site carrying the page itself reaches it. That is
        # not a corner case here -- immediate `0x08` is in the image and is
        # `0x8360`, the page-`0x08` store this pass is built around. A rule
        # that read `P-1` alone would report that site as ruled out.
        #
        # So the `clr a` population's two pages do not share one reading: the
        # page-`0x1C` negative rests on neither `0x1C` nor `0x1B` being an
        # immediate, while the page-`0x08` half resolves to `0x8360` alone.
        # `TheResidualTests` pins the first against the image; this table pins
        # the rule both readings are read off.
        #
        # On `site_row` rather than through `residual()`, because the residual
        # is by definition the rows `clr a` leaves out.
        def clr_row(imm: int) -> dict:
            img = fixture(clr_a(), addc(imm), mov_dph())
            at = A.census(img)[0]
            return A.site_row(img, at, pd_verified=False)

        self.assertEqual(clr_row(0x0F)["dph_set"], "{0x0F, 0x10}")
        # Each case is (immediate, the page its set must hold). `0x07`/`0x08`
        # and `0x08`/`0x08` are the two ways a set can hold `0x08`, and
        # `0x1B`/`0x1C` and `0x1C`/`0x1C` the two ways it can hold `0x1C`;
        # a table carrying only one of each would leave the rule half-pinned
        # in the exact way it was wrong.
        for imm, page in ((0x07, 0x08), (0x08, 0x08), (0x1B, 0x1C),
                           (0x1C, 0x1C), (0x06, None), (0x1D, None)):
            with self.subTest(imm=f"0x{imm:02X}"):
                row = clr_row(imm)
                self.assertEqual(len(row["pages"]), 2)
                if page is None:
                    self.assertEqual(row["reaches_0x08"], "no")
                    self.assertEqual(row["reaches_0x1c"], "no")
                else:
                    self.assertIn(page, row["pages"])
                    self.assertEqual(
                        row["reaches_0x08" if page == 0x08 else "reaches_0x1c"],
                        "yes")

    def test_the_same_immediate_without_the_clr_a_is_a_residual_site(self):
        row = only_row(fixture(mov_a(0x0F), addc(0x0F), mov_dph()))
        self.assertEqual(row["imm"], 0x0F)
        self.assertEqual(row["dph_set"], "{0x0F, 0x10}")

    def test_a_lcall_predecessor_is_named_and_not_read(self):
        row = only_row(fixture(lcall(0x2A7B), addc(0x0D), mov_dph()))
        self.assertEqual(row["preceded_by"], "`lcall 0x2a7b`")
        # The accumulator is *not* established from a call: the tool has no
        # register model and no export-boundary model, so it says so.
        self.assertEqual(row["a_on_entry"], "not established by this tool")

    def test_a_register_predecessor_is_named_and_not_read(self):
        row = only_row(fixture(mov_a_r6(), addc(0x2A), mov_dph()))
        self.assertEqual(row["preceded_by"],
                         f"`mov a,r6` at 0x00000 -- `A` carries r6, "
                         f"{A.REG_CARRIES}")

    def test_a_register_predecessor_reads_differently_from_a_bare_refusal(self):
        # The two refusals are different claims and have to render differently:
        # `mov a,r6` says a *register* carries the accumulator, which is what
        # points a reader at the instruction that last wrote it, while any
        # other encoding says the tool does not know what carries `A`. Folding
        # them into one cell loses the distinction the two `0x2A` sites rest
        # on, and it is a distinction the table is the only place recorded.
        reg = only_row(fixture(mov_a_r6(), addc(0x2A), mov_dph()))
        other = only_row(fixture(clr_c(), addc(0x2A), mov_dph()))
        self.assertIn(A.REG_CARRIES, reg["preceded_by"])
        self.assertIn(A.NOT_MODELLED, other["preceded_by"])
        self.assertNotEqual(reg["preceded_by"], other["preceded_by"])

    def test_a_site_the_anchored_walk_cannot_reach_says_so(self):
        # The population is a byte scan, so it can find a `34 xx f5 83` the
        # linear walk never lands on as an instruction start -- here a `mov dptr`
        # whose operand bytes happen to spell the triple. The row is still in
        # the table; its `window` says the walk did not reach it rather than
        # carrying a decode of whatever instructions precede it.
        img = fixture(mov_dptr(0x340D), mov_dph())
        rows = rows_for(img)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[next(iter(rows))]["window"], A.UNFRAMED)

    def test_the_scan_finds_every_triple_and_the_split_sums_to_it(self):
        img = fixture(clr_a(), addc(0x01), mov_dph(),
                      mov_a(0x02), addc(0x02), mov_dph(),
                      lcall(0x2A7B), addc(0x03), mov_dph())
        every = A.census(img)
        residual = {r["offset"] for r in A.residual(img, pd_verified=False)}
        # Three triples laid down, three found, and the `clr a` one is the only
        # site the residual leaves out. Asserting the *rule* (the split covers
        # the census exactly) rather than the offsets is what keeps this case
        # from being a second copy of the image's own byte layout.
        self.assertEqual(len(every), 3)
        self.assertEqual(len(residual), 2)
        self.assertTrue(residual < set(every))


class AccessTests(unittest.TestCase):
    """What DPTR is used for, on fixtures.

    Each of these is a site a filter would have dropped or misread, which is
    the reason the column is reported rather than used as one.
    """

    def test_a_store_two_instructions_past_the_pointer_is_still_a_store(self):
        # `mov a,0x66 ; movx @dptr,a` -- the value being stored is loaded from
        # a direct address between the pointer build and the store. Reading the
        # one opcode after `mov DPH,A` would call this a non-access.
        row = only_row(fixture(lcall(0x2A7B), addc(0x0D), mov_dph(),
                               mov_a(0x66), movx_store()))
        self.assertEqual(row["access"], "store via `movx @dptr,a`")

    def test_a_movc_is_a_code_read_and_not_an_xdata_access(self):
        row = only_row(fixture(lcall(0x2A7B), addc(0x0D), mov_dph(), movc()))
        self.assertEqual(row["access"],
                         "CODE read via `movc a,@a+dptr`, not an XDATA access")

    def test_a_read_is_a_read(self):
        row = only_row(fixture(lcall(0x2A7B), addc(0x0D), mov_dph(), movx_load()))
        self.assertEqual(row["access"], "read via `movx a,@dptr`")

    def test_a_site_with_no_access_is_reported_rather_than_dropped(self):
        # The population is every `34 xx f5 83` whose predecessor is not
        # `clr a`. A site whose pointer is used later is in the table with the
        # limit stated, not absent from it.
        row = only_row(fixture(lcall(0x2A7B), addc(0x0D), mov_dph(),
                               *([mov_a(0x00)] * 5)))
        self.assertIn("no `movx`/`movc`", row["access"])


class CsvTests(unittest.TestCase):
    """The CSV round-trip, on a fixture."""

    def test_the_table_round_trips_through_the_csv_writer(self):
        img = fixture(lcall(0x2A7B), addc(0x0D), mov_dph(), movx_load())
        text = A.csv_table(A.residual(img, pd_verified=False))
        self.assertIn("addr,region,imm,preceded_by", text.splitlines()[0])
        self.assertIn("`lcall 0x2a7b`", text)

    def test_the_table_carries_a_claim_per_site_and_no_counts(self):
        # Every row is a per-site claim, and the header names no column that
        # counts the tree -- a total in a committed table is a line every merge
        # that finds a site has to edit.
        img = fixture(lcall(0x2A7B), addc(0x0D), mov_dph(), movx_load())
        header = A.csv_table(A.residual(img, pd_verified=False)).splitlines()[0]
        for column in header.split(","):
            self.assertNotIn("count", column)


class CommittedTableTests(unittest.TestCase):
    """`--check` against the committed image and the committed CSV.

    The one class that reads the firmware, because the claim it holds is the
    one nothing else here can: that
    `../annotations/xdata-addc-dph-residual-sites.csv` is what this tool prints
    for `../firmware/GMxMGxx_11.800` today, so the write-up's per-site table is
    an assertion with a re-run behind it and not a paragraph.
    """

    def test_the_committed_table_is_what_this_run_produces(self):
        out = subprocess.run(
            [sys.executable, str(HERE / "addc_dph_sites.py"),
             str(FIRMWARE), "--check", str(COMMITTED_CSV)],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("reproduces it byte for byte", out.stdout)

    def test_the_check_is_red_against_a_table_that_is_not_this_runs(self):
        # A `--check` that is green because it never compares anything is worse
        # than no check, so the refusal is pinned: one byte of filler the tool
        # could not have produced has to turn it red.
        with tempfile.TemporaryDirectory() as tmp:
            edited = os.path.join(tmp, "edited.csv")
            with open(COMMITTED_CSV, newline="") as f:
                text = f.read()
            with open(edited, "w", newline="") as f:
                f.write(text.replace("`lcall 0x2a8f`", "`lcall 0x2a7f`", 1))
            out = subprocess.run(
                [sys.executable, str(HERE / "addc_dph_sites.py"),
                 str(FIRMWARE), "--check", edited],
                capture_output=True, text=True, cwd=REPO)
        self.assertEqual(out.returncode, 1)
        self.assertIn("differs from what this run produced", out.stderr)


if __name__ == "__main__":
    unittest.main()