#!/usr/bin/env python3
"""The eight `0x0F` sites, the carry rule, and the refusals of
`computed_dptr_sites.py`, on its own.

**The claim, and what it is not a census of.** The load-bearing case asserts
*which addresses reach page `0x0F`* -- the eight `manual-fan-ctrl-0751.md` §6
hand-decoded -- and asserts that the answer does not move with `--window`. It
deliberately does **not** assert how many computed-DPTR sites the tool finds in
the image: that is a count of the tree, every merge that changes a byte would
have to edit it, and `CLAUDE.md` records four times over that such a line is
where merge conflicts start. "These eight addresses reach this page" is a
finding; "the tool finds N sites" would be a maintenance tax wearing a
finding's clothes.

Every other case builds its own buffer through the local `fixture()` helper
rather than pointing at the firmware, for the reason
`test_find_indirect_xdata.py` gives: this tool's whole population is "an
opcode byte somewhere", so a fixture that *is* the image would be testing the
image, and would keep doing so only until the bytes around some address in it
changed.

The one class that does read the committed image is `CommittedTableTests`, and
it is the one that has to: `--check` reproducing
`../annotations/computed-dptr-sites.csv` byte for byte is what makes the
annotation's page census an assertion rather than a paragraph, and a suite that
only ever fed the tool a fixture could not tell whether that table still
describes the image.
"""
import contextlib
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# computed_dptr_sites imports disasm8051 and trace_xdata_refs by bare module
# name, the way find_indirect_xdata does, so the tool directory has to be on
# the path before it is loaded rather than after.
sys.path.insert(0, str(HERE))
import computed_dptr_sites as C       # noqa: E402
import trace_xdata_refs as T           # noqa: E402

FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"
COMMITTED_CSV = REPO / "ec" / "annotations" / "computed-dptr-sites.csv"

# The eight `DPH` builds issue #110 names, as file offsets in `bank0`, which
# is where a bank0 runtime address below 0x10000 lands. Spelled out here rather
# than derived from the tool, because a list generated from the scan would agree
# with the scan by construction and the class's whole claim would be that it
# agrees with the write-up instead.
EIGHT = [0x08AC6, 0x08AD8, 0x08AF3, 0x08B0C, 0x0BCE3, 0x0BDEC, 0x0E86B, 0x0F312]
# The two of the eight that hand DPTR to a subroutine rather than riding a
# `movx` themselves, and the routine both hand it to. The rest are followed by
# `movx @dptr`; these two would be dropped by a population filtered on `movx`,
# and that filter is the specific mistake `TheEightSitesTests` holds.
HANDOFF = [0x08AD8, 0x08AF3]
HANDOFF_TARGET = 0xBDF2
# The window widths the case below sweeps. It is the whole range the summary
# prints -- which skips one width in the middle, so the sweep is a range and not
# the printed list -- and the sweep then runs one past the widest, so a width at
# which the count would change if it were going to is inside it.
WIDTHS = tuple(range(min(C.SENSITIVITY_WIDTHS), max(C.SENSITIVITY_WIDTHS) + 1))


def clr_a() -> bytes:
    return bytes([0xE4])              # clr a -- clears A *and* the carry


def addc(v: int) -> bytes:
    return bytes([0x34, v])            # addc a,#v -- carry-dependent


def add(v: int) -> bytes:
    return bytes([0x24, v])            # add a,#v -- never carry-dependent


def mov_dph() -> bytes:
    return bytes([0xF5, 0x83])        # mov 0x83,a -- the anchor


def mov_dpl() -> bytes:
    return bytes([0xF5, 0x82])        # mov 0x82,a


def mov_a(v: int) -> bytes:
    return bytes([0x74, v])            # mov a,#v


def clr_c() -> bytes:
    return bytes([0xC3])              # clr c -- carry only, A untouched


def lcall(target: int) -> bytes:
    return bytes([0x12, target >> 8, target & 0xFF])


def setb_c() -> bytes:
    return bytes([0xD3])              # setb c


def fixture(*insns: bytes, size: int = 0x80) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_find_indirect_xdata.py` and
    `test_trace_xdata_refs.py` each carry a copy of, and for the same reason.
    The tail past the last instruction is filled with `0x00`, which the opcode
    table's 1-byte `nop` absorbs, so a walk over it is a run of nops rather
    than a decode of whatever byte happened to be there -- which is what lets a
    case's site offset be the offset the fixture laid the site down at.
    """
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def one_site(img: bytes, pd_verified: bool = False,
             back: int = C.WINDOW) -> dict:
    """The single site `sites()` finds, or a failure naming what it found.

    Every resolution case wants exactly one site, and a case that quietly got
    two would go on to assert about the first of them -- which is the way a
    fixture stops being evidence for what its name claims.
    """
    rows = C.sites(img, pd_verified, back)
    if len(rows) != 1:
        raise AssertionError(f"fixture holds {len(rows)} site(s) at "
                             f"{[r['offset'] for r in rows]}, not 1")
    return rows[0]


def capture(fn, *args) -> (str, int):
    """(what `fn` printed, what it returned), for the report modes.

    `page_report()` writes its answer and returns an exit code, and the exit
    code is half of what the issue asked for: a page the main EC does not
    reach has to be a non-zero run and not a sentence nobody reads.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*args)
    return buf.getvalue(), rc


def page0f(d: bytes, pd_verified: bool, back: int = C.WINDOW) -> list:
    """The file offsets of the main-EC sites whose page this tool establishes
    as `0x0F`, for the cases that are about *which addresses* reach a page."""
    return sorted(r["offset"] for r in C.sites(d, pd_verified, back)
                  if r["region"] in C.MAIN_EC_REGIONS
                  and r["page_value"] == 0x0F)


class TheEightSitesTests(unittest.TestCase):
    """Issue #110's acceptance criterion, asserted as a claim and not a census.

    Eight bank0 `DPH` builds reach page `0x0F`, they are the eight §6 names, and
    the answer is the same at every window width the tool offers. The third half
    is the one that makes the first two a finding rather than a coincidence: a
    count a `--window` knob can manufacture is a property of the knob.
    """

    @classmethod
    def setUpClass(cls):
        cls.img = FIRMWARE.read_bytes()

    def test_the_eight_are_found_unseeded_and_are_the_ones_the_writeup_names(self):
        # The whole of the issue's "Done": the tool finds the eight known `0x0F`
        # sites without hand-seeding. Nothing in the tool is given these
        # addresses -- they are transcribed from the issue and from §6, and the
        # comparison is against a run that was never told them.
        self.assertEqual(page0f(self.img, True), EIGHT)
        # And every one of them is in bank0, which is where §6 put them. A
        # `mov 0x83,a` in the PD image is another program's byte, so a page-0x0F
        # hit over there would be a different program's page of the same number.
        regions = {r["region"] for r in C.sites(self.img, True)
                   if r["page_value"] == 0x0F}
        self.assertEqual(regions, {"bank0"})
        # The named runtime address is the `addc` itself, two bytes short of
        # the `mov 0x83,a` that completes the pointer -- so a reader can put
        # §6's listing and this row side by side and see the same instruction.
        for row in C.sites(self.img, True):
            if row["page_value"] != 0x0F:
                continue
            # A bank0 file offset and its runtime address are the same number
            # (`REGIONS` gives bank0 lo=0x08000, base=0x8000), which is what
            # lets §6's `0x8ac6` listing and this row be read against each
            # other without translating between them.
            self.assertEqual(row["runtime"], row["offset"])
            self.assertEqual(row["dph_store"] - row["offset"], 2)
            self.assertEqual(row["form"], "addc a,#0x0f")

    def test_the_count_does_not_depend_on_the_window(self):
        # The sweep, including a width one past the widest the summary prints.
        # "Eight at the default" is a claim about an image; "eight at every
        # width" is a claim about the scan, and it is the one that would catch a
        # window default chosen to produce the answer.
        for width in sorted(set(WIDTHS) | {max(WIDTHS) + 1}):
            with self.subTest(window=width):
                self.assertEqual(page0f(self.img, True, width), EIGHT)

    def test_all_eight_are_found_though_only_six_have_a_following_movx(self):
        # The regression for the filter the tool's docstring declines to apply.
        # `0x8AD8` and `0x8AF3` do `setb c ; lcall 0xBDF2` and
        # `clr c ; lcall 0xBDF2`, so a population that kept only sites followed
        # by a `movx` would find six -- and would have failed the issue's own
        # test while looking like a clean run.
        rows = {r["offset"]: r for r in C.sites(self.img, True)
                if r["page_value"] == 0x0F}
        with_movx = sorted(at for at, r in rows.items()
                           if C.access_of(r["access"]) != "hands DPTR to a "
                                                         "subroutine")
        self.assertEqual(len(with_movx), 6)
        for at in HANDOFF:
            with self.subTest(site=f"0x{at:05X}"):
                self.assertIn(at, rows)
                self.assertEqual(C.access_of(rows[at]["access"]),
                                 "hands DPTR to a subroutine")
                self.assertIn(f"lcall 0x{HANDOFF_TARGET:04x}", rows[at]["access"])
        # The handoff is a *reported column*, so the two are still in the same
        # population and the same table as the six.
        self.assertEqual(sorted(rows), EIGHT)
        table = C.csv_table(list(rows.values()))
        self.assertEqual(len(table.strip().splitlines()), len(EIGHT) + 1)

    def test_a_handed_over_pointer_still_counts_as_reaching_the_page(self):
        # `--page`'s half of the same decision: the handoff is not a reason to
        # drop a row, so a page reached only by handoffs is still reached.
        hits, undecided = C.page_of_sites(self.img, True, 0x0F)
        self.assertEqual(sorted(r["offset"] for r in hits["bank0"]), EIGHT)
        # The eight are hits and not maybes, which is the claim; the rest of the
        # undecided list is this image's refusals, which a refusal's page being
        # undetermined puts under every page, and a count of those would be a
        # figure every merge that changes a byte has to edit.
        self.assertEqual(set(EIGHT) & {r["offset"] for r in undecided}, set())
        out, rc = capture(C.page_report, self.img, True, 0x0F)
        self.assertEqual(rc, 0)
        self.assertIn("hands DPTR to a subroutine", out)


class CarryTests(unittest.TestCase):
    """`addc` is carry-dependent, and the accumulator decides everything else.

    Both directions, because a rule that only refuses would also pass a suite
    that never resolved anything, and a rule that only resolves would pass on an
    image where the `clr a` happened to be there by luck.
    """

    def test_clr_a_makes_the_addc_determinate(self):
        # The idiom every one of the eight uses. `clr a` clears the accumulator
        # *and* the carry on an 8051, so this is provably 0x0F and not
        # 0x0F-or-0x10 -- the tool derives the carry, it does not assume it.
        site = one_site(fixture(clr_a(), addc(0x0F), mov_dph()))
        self.assertEqual(site["page"], "0x0F")
        self.assertEqual(site["page_value"], 0x0F)
        self.assertEqual(site["page_state"], C.DETERMINATE)

    def test_the_same_addc_without_the_clr_stops_resolving(self):
        # Take away the one instruction that decided it and the answer has to
        # stop being an answer. The predecessor here is a `nop`, which writes
        # neither A nor the carry -- so this is a **refusal**, not the two-value
        # candidate set: both quantities are unestablished, and a set of two
        # would be a claim about the accumulator this tool did not make. The
        # candidate-set case is the `mov a,#NN` one below, where the
        # accumulator really is known and only the carry is not.
        site = one_site(fixture(bytes([0x00]), addc(0x0F), mov_dph()))
        self.assertIsNone(site["page_value"])
        self.assertNotEqual(site["page"], "0x0F")
        self.assertIn("nop", site["page"])
        self.assertNotIn("{", site["page"])

    def test_a_candidate_set_is_never_collapsed_to_its_low_member(self):
        # The §4d shape, named and held. `mov a,#0x0f ; addc a,#0x00` fixes the
        # accumulator and leaves the carry, so the high byte is one of two
        # values -- and a tool that printed `0x0F` would be claiming the method
        # established something it did not.
        img = fixture(mov_a(0x0F), addc(0x00), mov_dph())
        site = one_site(img)
        self.assertIsNone(site["page_value"])
        self.assertIn("{0x0F, 0x10}", site["page"])
        self.assertNotEqual(site["page"], "0x0F")
        # And the row is not in `--page`'s hit tally either, because a set is
        # not a hit -- it is listed as undecided for the two pages in the set,
        # which is the difference between "measured and not this" and "not
        # looked at".
        for page in (0x0F, 0x10):
            with self.subTest(page=f"0x{page:02x}"):
                hits, undecided = C.page_of_sites(img, False, page)
                self.assertEqual(hits, {})
                self.assertEqual([r["offset"] for r in undecided],
                                 [site["offset"]])

    def test_add_a_resolves_on_the_accumulator_alone(self):
        # `add a,#imm` never reads the carry, so it resolves on the accumulator
        # alone -- which is the one case where the immediate is not even the
        # whole of the answer and the tool still gets it right. `add a,#0x7d`
        # on a `clr a` is 0x7D and not 0x7D-or-0x7E.
        site = one_site(fixture(clr_a(), add(0x7D), mov_dph()))
        self.assertEqual(site["page"], "0x7D")
        self.assertEqual(site["page_state"], C.DETERMINATE)

    def test_add_a_ignores_a_carry_that_addc_would_consume(self):
        # The two opcodes are different instructions and conflating them is an
        # off-by-one page. `add a,#imm` is `A + imm` and never reads the carry;
        # `addc a,#imm` is `A + imm + C`. With A = 0x2A and C = 1 the same
        # immediate is 0x3A for the first and 0x3B for the second.
        #
        # Asserted on `page_of()` rather than on a fixture because the
        # one-instruction rule cannot reach a state where a *set* carry meets a
        # known accumulator -- it would take two instructions -- and a case
        # that built one anyway would be testing a reach the tool does not have.
        # The fixture cases above are what show the rule on real bytes; this one
        # is what holds the arithmetic, and the same way `P2WriterTests` holds
        # its table's encodings.
        for opcode, expected in ((0x24, "0x3A"), (0x34, "0x3B")):
            with self.subTest(opcode=f"0x{opcode:02x}"):
                page, value, state, pages = C.page_of(bytes([opcode, 0x10]), 0,
                                                      (0x2A, 1, "setb c"))
                self.assertEqual(page, expected)
                self.assertEqual(value, 0x3A + (opcode == 0x34))
                self.assertEqual(state, C.DETERMINATE)
                self.assertEqual(pages, frozenset({0x3A + (opcode == 0x34)}))

    def test_a_carry_setter_on_its_own_is_still_not_a_page_source(self):
        # `setb c` (0xD3) is the mirror of the `clr c` case below and is pinned
        # with it, because the two are the same shape: the carry is known and
        # the accumulator is not, so `A + 0x2a + 1` is not `0x2b`.
        site = one_site(fixture(setb_c(), addc(0x2A), mov_dph()))
        self.assertIsNone(site["page_value"])
        self.assertIn("setb c", site["page"])

    def test_a_site_that_sets_the_carry_in_a_separate_instruction_is_refused(self):
        # The rule's one documented limit, named here so a reader who finds
        # `mov a,#0x0f ; clr c ; addc a,#0x00` somewhere expects the refusal
        # rather than the answer. A and the carry are read from the *same* one
        # instruction, and only `clr a` establishes both at once -- so a site
        # that sets them in two instructions is refused. That is conservative in
        # the direction that matters: it under-counts pages and never invents
        # one, which is the §4c/§4d direction, and the cost is that `--page`
        # reports fewer pages than the firmware reaches rather than more.
        site = one_site(fixture(mov_a(0x0F), clr_c(), addc(0x00), mov_dph()))
        self.assertIsNone(site["page_value"])
        self.assertNotEqual(site["page"], "0x0F")
        # The two-instruction form is not in this image at all, which is what
        # makes the limit free here; the refusal above is what it would get.
        self.assertEqual(site["page_state"], "refused")

    def test_clr_c_alone_is_not_a_page_source(self):
        # The case this rule exists for, and it is a real 8051 spelling: `clr c`
        # is the ordinary way to write "no carry", and it establishes the carry
        # *and not the accumulator*. `clr c ; addc a,#0x0f` computes `A + 0x0f`,
        # not `0x0f`, so reading the immediate off it would be the same
        # over-claim as reading an unresolved `P2` as a page.
        site = one_site(fixture(clr_c(), addc(0x0F), mov_dph()))
        self.assertIsNone(site["page_value"])
        self.assertNotEqual(site["page"], "0x0F")
        self.assertIn("clr c", site["page"])

    def test_a_refusal_names_the_encoding_that_defeated_it(self):
        # A cell that said only "not established" would read as a verdict about
        # the byte rather than as a limit on the method, and the three reasons
        # here are three different limits.
        lcallee = one_site(fixture(lcall(0x2A7B), addc(0x0F), mov_dph()))
        self.assertIn("lcall 0x2a7b", lcallee["page"])
        in_reg = one_site(fixture(bytes([0xEE]), addc(0x0F), mov_dph()))
        self.assertIn("mov a,r6", in_reg["page"])
        bare = one_site(fixture(addc(0x0F), mov_dph()))
        self.assertEqual(bare["page"], C.NO_BEFORE)

    def test_the_nearest_add_is_the_one_in_force(self):
        # The window holds two immediate adds and the store is written with the
        # accumulator the *nearer* one left. Taking the further one would report
        # a page the immediately preceding instruction had already replaced --
        # the same reason `find_indirect_xdata.py` records the last `P2` write
        # rather than searching for the literal.
        site = one_site(fixture(clr_a(), addc(0x0F), clr_a(), addc(0x33),
                                mov_dph()), back=8)
        self.assertEqual(site["page"], "0x33")


class LowByteTests(unittest.TestCase):
    """The half the issue also asked for, and the evidenced negative it is.

    "Plus, where the low byte is also an immediate or a known-value read, the
    concrete address" -- so the cell has to be able to hold a concrete address,
    and it has to decline to when the low byte is a run-time value rather than
    composing an address nobody read.
    """

    def test_a_literal_low_byte_gives_the_concrete_address(self):
        # The positive case, so the refusals below are refusals rather than a
        # tool that can only say no. `mov a,#0xb9 ; mov 0x82,a ; clr a ;
        # addc a,#0x07 ; mov 0x83,a` is 0x07B9 built in five instructions.
        site = one_site(fixture(mov_a(0xB9), mov_dpl(), clr_a(), addc(0x07),
                                mov_dph()))
        self.assertEqual(site["low"], "literal 0xB9")
        self.assertEqual(site["low_value"], 0xB9)
        self.assertEqual(site["xaddr"], "0x07B9")

    def test_a_run_time_low_byte_reports_the_page_and_names_the_supply(self):
        # The shape all eight `0x0F` sites have: the instruction before the
        # `mov 0x82,a` is an `add`, so the stored value is a run-time
        # computation and the address is not derivable from the window.
        site = one_site(fixture(add(0x20), mov_dpl(), clr_a(), addc(0x0F),
                                mov_dph()))
        self.assertIsNone(site["low_value"])
        self.assertTrue(site["low"].startswith("at run time"))
        self.assertIn("add a,#0x20", site["low"])
        # The cell must not spell an address: `page 0x0F` and the supply, never
        # `0x0F20`, which would be a claim about a byte no instruction read.
        self.assertTrue(site["xaddr"].startswith("page 0x0F"))
        self.assertNotIn("0x0F20", site["xaddr"])

    def test_no_dpl_store_in_the_window_is_its_own_token(self):
        # Different from a run-time low byte: there is no `mov DPL,a` behind the
        # add at all, so the low half was not set here and this tool cannot say
        # anything about it. Merging the two would read as "the low byte is a
        # value we could not follow" for a row where there is no low byte.
        site = one_site(fixture(clr_a(), addc(0x0F), mov_dph()))
        self.assertEqual(site["low"], C.NO_DPL)
        self.assertIsNone(site["low_value"])

    def test_the_eight_never_resolve_their_low_byte(self):
        # The issue's own second half, answered against the image: at the eight
        # the low byte is a `movx a,@dptr` result or `mov a,#0x80 ; add a,r7`,
        # so the concrete address is not resolvable at any of them. The claim
        # is about those eight addresses reaching a page, not about a count.
        d = FIRMWARE.read_bytes()
        rows = {r["offset"]: r for r in C.sites(d, True)
                if r["page_value"] == 0x0F}
        self.assertEqual(sorted(rows), EIGHT)
        for at in EIGHT:
            with self.subTest(site=f"0x{at:05X}"):
                self.assertIsNone(rows[at]["low_value"])
                self.assertTrue(rows[at]["low"].startswith("at run time"))
                self.assertTrue(rows[at]["xaddr"].startswith("page 0x0F"))


class AnchoredTests(unittest.TestCase):
    """The anchor is a `mov 0x83,a` the decode reaches, not two bytes.

    Both directions, for the reason `test_find_indirect_xdata.P2WriterTests`
    pins them in both directions: a table too wide invents sites, and a table
    too narrow loses them, and one direction alone cannot tell the two apart.
    """

    # `mov dptr,#0xF583` is three bytes whose second and third are 0xF5 and
    # 0x83 -- an immediate that happens to spell a `mov DPH,a`. No `nop` between
    # it and a real site, so hiding the collision is not available.
    IMG = fixture(bytes([0x90, 0xF5, 0x83]), clr_a(), addc(0x0F), mov_dph())

    def test_an_immediate_that_spells_a_dph_store_is_not_a_site(self):
        # The two bytes are real, the instruction they spell is not, and the
        # byte scan finds all of them.
        rows = C.sites(self.IMG, False)
        self.assertEqual([r["offset"] for r in rows], [4])
        self.assertEqual([r["dph_store"] for r in rows], [6])
        # And the raw pass is the over-count, which the summary prints beside
        # the anchored one so a reader can see the gap rather than infer it:
        # the pair at offset 1 is the `mov dptr,#0xF583` immediate.
        self.assertEqual(C.raw_sites(self.IMG), [1, 6])

    def test_the_anchor_is_the_high_half_and_not_the_low(self):
    # `mov 0x82,a` is one byte away from `mov 0x83,a` and is the *other* half
    # of the pointer. A tool that read the operand loosely would anchor on
    # `mov DPL,a` and report the low byte's construction as the site's.
        site = one_site(fixture(clr_a(), addc(0x0F), mov_dph()))
        self.assertEqual(site["dph_store"], 3)
        # A `mov DPL,a` with no `mov DPH,a` after it is not a site, and its
        # two bytes are not in the anchored population either.
        self.assertEqual(C.sites(fixture(clr_a(), addc(0x0F), mov_dpl()), False), [])

    def test_a_store_nobody_built_is_declined_with_its_own_token(self):
        # A `mov 0x83,a` with no `add` in the window is not a computed-DPTR
        # site, and the tool says which of the two reasons applies rather than
        # dropping it silently -- "the window found nothing" and "the window ran
        # out" are different claims about different bytes.
        lone = C.declined(fixture(clr_a(), mov_dph()), False)
        self.assertEqual([why for _at, why in lone], [C.NO_ADD])
        # With four instruction starts behind the store and no `add` among
        # them, the token carries the budget that ran out instead. Two distinct
        # claims about two distinct bytes, which is why they are two strings
        # and a summary that merged them would read as one.
        img = fixture(bytes([0x90, 0x04, 0x60]), clr_a(), clr_c(), clr_a(),
                      clr_a(), mov_dph())
        self.assertEqual([why for _at, why in C.declined(img, False)],
                         [f"{C.NO_ADD} ({C.window_end(C.WINDOW)})"])
        self.assertNotEqual(C.NO_ADD, C.window_end(C.WINDOW))

    def test_a_high_byte_build_is_counted_once_however_many_stores_follow_it(self):
        # The linear walk does not stop at control flow, so a `ret` in the
        # middle of a routine leaves the next byte to be decoded -- and where
        # that byte is `F5 83` a second store opens on the *same* `addc`. The
        # nearest store is the one the build feeds, and reporting the build
        # twice would make the population a function of what follows a `ret`.
        img = fixture(clr_a(), addc(0x0F), mov_dph(), bytes([0x22]),
                      mov_dph())
        rows = C.sites(img, False)
        self.assertEqual([r["offset"] for r in rows], [1])
        self.assertEqual(rows[0]["dph_store"], 3)
        # The real store is at offset 3 and the phantom at 6, with the `ret`'s
        # own byte at 5 -- which is the byte the linear walk decodes as the
        # second `mov 0x83,a` and which no 8051 would ever execute.
        self.assertEqual(img[3:5], bytes([0xF5, 0x83]))
        self.assertEqual(img[5], 0x22)
        self.assertEqual(img[6:8], bytes([0xF5, 0x83]))

    def test_the_declined_census_and_the_sites_partition_the_anchored_stores(self):
        # `sites()` suppresses the row for a build a nearer store already
        # claimed, and `declined()` used to collect only `store_verdict()`'s
        # refusals -- so a duplicate fell out of both lists and the arithmetic
        # the summary prints on every run (`anchored = sites + declined`) came
        # out short by one per duplicate. The property is the partition, not a
        # count of the tree: every anchored store is named exactly once across
        # the two, whichever side it lands on.
        img = fixture(clr_a(), addc(0x0F), mov_dph(), bytes([0x22]),
                      mov_dph(), mov_dph())
        rows = C.sites(img, False)
        declined = C.declined(img, False)
        anchored = [s for _starts, found in C.stores(img) for s in found]
        named = [r["dph_store"] for r in rows] + [at for at, _why in declined]
        self.assertEqual(sorted(named), sorted(anchored))
        self.assertEqual(len(named), len(set(named)))
        # And the duplicate is declined under its own reason rather than under
        # `NO_ADD`: its `addc` is sitting in its window, so "no immediate
        # add/addc in the window" would be false of it.
        self.assertIn((6, C.DUP_BUILD), declined)
        self.assertNotIn(C.NO_ADD, [why for _at, why in declined])


class TruncationTests(unittest.TestCase):
    """Short buffers get a verdict, and a refusal names what it ran out of."""

    def test_a_truncated_store_is_a_verdict_and_not_an_index_error(self):
        # `store_verdict()` bounds-checks the store itself, for the reason
        # `trace_xdata_refs.is_dptr_rebuild()` documents: a caller holding a
        # short buffer has to get a refusal, and a crash on a fixture is a
        # latent hole rather than a passing test.
        # Offsets 0 and 2 are the `addc` and the store, and 3 is past the end:
        # none of the three is a `mov 0x83,a` this function can take a window
        # behind, and all three have to come back with a reason rather than an
        # exception. The store at offset 2 *is* one, and is the control -- a
        # refusal there would mean the bounds check had swallowed the answer.
        for at in (-1, 0, 1, 3, 99):
            with self.subTest(store=at):
                row, why = C.store_verdict(fixture(addc(0x0F), mov_dph()),
                                           [0, 2, 4], at, False)
                self.assertIsNone(row)
                self.assertIsInstance(why, str)
                self.assertTrue(why)
        live, why = C.store_verdict(fixture(addc(0x0F), mov_dph()),
                                    [0, 2, 4], 2, False)
        self.assertIsNone(why)
        self.assertIsNotNone(live)

    def test_a_buffer_that_stops_inside_an_add_is_still_a_row(self):
        # The `addc` is the last thing in the buffer, so its immediate byte is
        # the one the tool must not reach past the end for.
        img = fixture(clr_a(), addc(0x0F), mov_dph())[:6]
        site = one_site(img)
        self.assertEqual(site["page"], "0x0F")
        # And the window column is the decode it was resolved against, so a
        # reader is not asked to take the cell on trust.
        starts = C.anchored_starts(img, 0, len(img))
        behind, _why = C.window_before(starts, site["dph_store"], C.WINDOW)
        self.assertEqual(site["window"],
                         " ; ".join(C.norm(img, at) for at in behind
                                    + [site["dph_store"]]))


class RegionSplitTests(unittest.TestCase):
    """The main EC and the PD image, never added together.

    `lightbar-bat-flow.md` §2's mistake, and the invariant the summary's
    two-total printout exists to hold.
    """

    @staticmethod
    def image_with(*offsets, page: int = 0x0F) -> bytes:
        """A buffer holding one `page`-building site at each offset.

        Zero-filled elsewhere, which the opcode table reads as a run of 1-byte
        `nop`s, so each site is an anchored start and nothing else in a 192 KiB
        buffer is one. The buffer stops at 0x30000, the end of the PD region,
        rather than being padded further: a size the walk cannot reach would
        hide a bounds defect instead of being irrelevant to it.
        """
        img = bytearray(b"\x00" * 0x30000)
        for at in offsets:
            img[at:at + 5] = clr_a() + addc(page) + mov_dph()
        return bytes(img)

    def test_the_two_images_are_counted_apart(self):
        rows = C.sites(self.image_with(0x0100, 0x20020), pd_verified=True)
        self.assertEqual([r["region"] for r in rows], ["common", "pd-image"])
        # The runtime address is the region's own base plus the offset into it,
        # and the offset is that of the `addc` -- the first byte of the
        # five-byte sequence -- so the PD image's site is not the main EC's
        # 0x20020 and the table cannot be read as though it were.
        self.assertEqual([r["offset"] for r in rows], [0x0101, 0x20021])
        self.assertEqual([r["runtime"] for r in rows], [0x0101, 0x0021])
        self.assertNotIn(C.PD_REGION, C.MAIN_EC_REGIONS)
        self.assertEqual(sum(1 for r in rows
                             if r["region"] in C.MAIN_EC_REGIONS), 1)

    def test_a_buffer_without_the_marker_reports_unknown_not_pd_image(self):
        # `region_of()`'s refusal, reached through this tool's own output. A
        # dump that is not this one has to get `unknown` rather than inherit
        # the PD image's conclusion from the offset alone.
        rows = C.sites(self.image_with(0x0100, 0x20020), pd_verified=False)
        self.assertEqual([r["region"] for r in rows], ["common", "unknown"])
        self.assertEqual(len(rows), 2)

    def test_the_page_report_prints_the_unidentified_region_rather_than_dropping_it(self):
        # The same refusal through `page_report()`, which is where it was lost.
        # A row in the unidentified span is not a refusal -- it has a page, so it
        # is in no "could not place" list -- and `pd-image` is a different
        # image's region, so the loop over the named regions skipped it too. It
        # was in neither printed list while the report exited 1 beside it, and
        # `page_report()`'s docstring promises the rows that could not be placed
        # are printed rather than dropped.
        out, rc = capture(C.page_report, self.image_with(0x20020), False, 0x0F)
        self.assertEqual(rc, 1)
        self.assertIn("unknown", out)
        self.assertIn("0x20021", out)
        # And it is added to nothing: not the main EC's half, whose exit code is
        # the question, and not the PD image's line, which is another program.
        self.assertEqual(sum(1 for r in C.sites(self.image_with(0x20020), False)
                             if r["region"] in C.MAIN_EC_REGIONS), 0)
        self.assertNotIn(C.UNKNOWN_REGION, C.MAIN_EC_REGIONS)

    def test_the_page_report_names_the_image_each_hit_is_in(self):
        # The issue asks whether the **main EC image** reaches the page, so the
        # answer is per image and the exit code is about the main EC alone.
        out, rc = capture(C.page_report,
                          self.image_with(0x0100, 0x20020), True, 0x0F)
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("building 0x0F"), 2)
        self.assertIn("common", out)
        self.assertIn("pd-image", out)

    def test_a_page_only_the_pd_image_reaches_exits_non_zero(self):
        # And the refusal: a PD hit is not an EC-side reference to a 0x0Fxx
        # byte, so the main EC's half of the answer has to be a non-zero run
        # even though the page is not empty.
        out, rc = capture(C.page_report, self.image_with(0x20020), True, 0x0F)
        self.assertEqual(rc, 1)
        self.assertIn("reaches page 0x0F at no computed-`DPH`", out)
        self.assertIn("building 0x0F", out)

    def test_a_page_nothing_reaches_exits_non_zero_with_no_hits(self):
        # The main EC's only site resolves onto another page, so "page 0x0F" is
        # empty and the count is the whole of the answer.
        out, rc = capture(C.page_report,
                          self.image_with(0x0100, page=0x04), True, 0x0F)
        self.assertEqual(rc, 1)
        self.assertIn("not reached by any site with an established page", out)
        self.assertNotIn("building 0x0F", out)

    def test_a_refused_row_is_neither_a_hit_nor_a_miss(self):
        # The distinction `--page` has to keep: a site whose accumulator this
        # tool could not read is neither a hit on the queried page nor a miss
        # for it. It is printed, so the zero beside it is a measurement and not
        # a silence.
        #
        # **The queried page is deliberately not the one the immediate names.**
        # A refusal leaves A whatever a callee returned, so the site can reach
        # any page at all; keying the test on the immediate made this pass
        # only because `0x0F` here happened to be both the immediate and the
        # query, and would have printed a bare `common 0` with nothing listed
        # beside it for a refusal that could have been 0x07.
        img = bytearray(b"\x00" * 0x80)
        img[0:5] = bytes([0xEE]) + addc(0x0F) + mov_dph()   # `mov a,r6` first
        self.assertNotEqual(0x07, 0x0F)   # the query below is not the immediate
        hits, undecided = C.page_of_sites(bytes(img), False, 0x07)
        self.assertEqual(hits, {})
        self.assertEqual([r["offset"] for r in undecided], [1])
        out, rc = capture(C.page_report, bytes(img), False, 0x07)
        self.assertEqual(rc, 1)
        self.assertIn("could not place", out)
        self.assertIn("0x00001", out.replace("0x0001", "0x00001"))

    def test_a_candidate_set_names_the_page_and_not_only_the_immediate(self):
        # The other direction, and the one the immediate got wrong in *both*
        # ways: here A is known and non-zero, so the high byte is `0x0B + 0x0F`
        # and the immediate `0x0F` is not the page at all. The row's own cell
        # spells the candidate set, and that set -- not the immediate -- is what
        # decides whether the row is listed under the queried page.
        img = fixture(mov_a(0x0B), addc(0x0F), mov_dph())
        site = one_site(img)
        self.assertEqual(site["page"], "{0x1A, 0x1B} -- " + C.CARRY_UNKNOWN)
        self.assertEqual(site["page_candidates"], frozenset({0x1A, 0x1B}))
        for page in (0x1A, 0x1B):
            with self.subTest(page=f"0x{page:02x}"):
                hits, undecided = C.page_of_sites(img, False, page)
                self.assertEqual(hits, {})
                self.assertEqual([r["offset"] for r in undecided],
                                 [site["offset"]])
        # And the page the immediate names is one the row's own set rules out,
        # so it must not be listed there. This is the half that put a row under
        # a page it cannot be.
        hits, undecided = C.page_of_sites(img, False, 0x0F)
        self.assertEqual(hits, {})
        self.assertEqual(undecided, [])

    def test_a_determinate_page_is_listed_as_a_hit_and_not_as_undecided(self):
        # The two lists are disjoint by construction, so a resolved row is
        # counted once rather than appearing under both. The fixture resolves
        # on the accumulator alone, and the queried page is its own.
        img = fixture(clr_a(), addc(0x0F), mov_dph())
        hits, undecided = C.page_of_sites(img, False, 0x0F)
        self.assertEqual([r["offset"] for r in hits["common"]], [1])
        self.assertEqual(undecided, [])


class CsvTests(unittest.TestCase):
    """The table's cells, through the csv module rather than by eye."""

    def test_the_row_carries_the_evidence_the_cells_are_built_from(self):
        img = fixture(mov_a(0xB9), mov_dpl(), clr_a(), addc(0x07), mov_dph())
        table = C.csv_table(C.sites(img, False))
        row = next(csv.DictReader(io.StringIO(table)))
        self.assertEqual(row["file_offset"], "0x00005")
        self.assertEqual(row["dph_store"], "0x00007")
        self.assertEqual(row["region"], "common")
        self.assertEqual(row["runtime"], "0x0005")
        self.assertEqual(row["form"], "addc a,#0x07")
        self.assertEqual(row["page"], "0x07")
        self.assertEqual(row["low"], "literal 0xB9")
        self.assertEqual(row["xaddr"], "0x07B9")
        # The framing evidence is disasm8051's, and both halves of it are here
        # because either alone settles nothing -- the pair is the claim.
        onto, over = T.converges_from(img, 5)
        self.assertEqual((int(row["frame_onto"]), int(row["frame_over"])),
                         (onto, over))

    def test_a_refused_row_says_which_half_defeated_it(self):
        # The page cell and the low cell are separate columns for the reason the
        # tool's docstring gives: one names the encoding that beat the page
        # half, the other the one that beat the low half, and a reader told only
        # "unresolved" would have to work out which.
        img = fixture(lcall(0x2A7B), addc(0x0F), mov_dph())
        row = next(csv.DictReader(io.StringIO(C.csv_table(C.sites(img, False)))))
        self.assertIn("lcall 0x2a7b", row["page"])
        self.assertNotEqual(row["page"], "0x0F")
        self.assertEqual(row["low"], C.NO_DPL)
        self.assertTrue(row["xaddr"].startswith("no page;"))


class CommittedTableTests(unittest.TestCase):
    """`--check` against the committed image and the committed CSV.

    The one class that reads the firmware, because the claim it holds is the
    one nothing else here can: that `../annotations/computed-dptr-sites.csv` is
    what this tool prints for `../firmware/GMxMGxx_11.800` today, so the
    annotation's page census is an assertion with a re-run behind it and not a
    paragraph.
    """

    def test_the_committed_table_is_what_this_run_produces(self):
        out = subprocess.run(
            [sys.executable, str(HERE / "computed_dptr_sites.py"),
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
                f.write(text.replace("common", "comm0n", 1))
            out = subprocess.run(
                [sys.executable, str(HERE / "computed_dptr_sites.py"),
                 str(FIRMWARE), "--check", edited],
                capture_output=True, text=True, cwd=REPO)
        self.assertEqual(out.returncode, 1)
        self.assertIn("differs from what this run produced", out.stderr)

    def test_the_page_0x07_answer_is_a_non_zero_run_on_the_committed_image(self):
        # The other end of the issue's two addresses, and it is a negative:
        # **no** computed-`DPH` site reaches page `0x07` in any image, which is
        # what narrows what the zero in `registers.yaml`'s `0x07B9` and `0x07D0`
        # rows licenses. The exit code is the claim; the wording is the shape.
        #
        # The `no` in the closing sentence is pinned rather than left to the
        # sentence after it: this branch only runs when the main EC established
        # no site on the page, so an un-negated "reaches" would state the
        # opposite of the measurement at the point a reader stops reading.
        #
        # The spelling in that sentence is the claim, not decoration: the
        # negative is about computed `DPH` sites -- the ones *this* scan can
        # establish -- and not about the other spellings of the same page.
        # `scan_refs.py` and `trace_xdata_refs.py` both find direct
        # `MOV DPTR,#imm16` sites on page `0x07` in the main EC, so a closing
        # sentence reaching past this scan to the others would be false against
        # the committed image, and this assertion is what holds it scoped.
        out = subprocess.run(
            [sys.executable, str(HERE / "computed_dptr_sites.py"),
             str(FIRMWARE), "--page", "0x07"],
            capture_output=True, text=True, cwd=REPO)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        self.assertIn("not reached by any site with an established page", out.stdout)
        self.assertIn("reaches page 0x07 at no computed-`DPH`", out.stdout)
        self.assertIn('"not found by this method"', out.stdout)


if __name__ == "__main__":
    unittest.main()
