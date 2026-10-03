#!/usr/bin/env python3
"""What `stride_index_table.py` claims about the `0x4900` block, held to the
committed image, and what it refuses.

`stride_index_table.py --self-test` holds the same refusals as a run of its
own. This suite exists because a `--self-test` is a thing a person runs and
this is a thing `tools/run-tests.sh` collects; both read the committed image
and the committed listings, so they cannot disagree about which refusals exist
or what the sites decode to.

**Every site's figures are asserted against the image, not against the scan
that produced them.** Each named site is re-decoded here from `FIRMWARE` at
its own offset -- stride, base offset, base high byte, the `mov DPH,A` that
follows -- and the scan is then asked whether it agrees. A tool that reported
its own scan's output as a census would pass a test that compared the two to
each other, which is the mistake this arrangement is written to catch.

**Deliberately absent: any assertion of a site count over the image.** The
number of stride constructions in a committed binary is a property of that
binary, and a suite that asserted it would be a value every re-export moves.
What is asserted is each *named* site, so a re-export that moved one is caught
by its own row rather than by a number. `--check` holds the write-up's
declared figures to the same image, which is where a census belongs.

**Also deliberately absent: any assertion that a region is "not a table".**
The byte-level argument is §1 of `docs/findings/4900-stride-table.md` and its
verdicts are a flow walk's, which cannot tell code from a table it wandered
into. What is asserted here is what the walk reported, at the addresses it
reported it for.

**Every mutation case is written against the error it is meant to catch**, and
each was run once with the mutation in place to confirm it goes red -- the
`test_data_regions.py` convention.

Nothing here opens a device, reads a register, or needs Windows or hardware:
every input is a committed file.
"""
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "stride_index_table.py"
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"
WRITEUP = REPO / "docs" / "findings" / "4900-stride-table.md"

sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("stride_index_table", TOOL)
sit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sit)


class SiteTests(unittest.TestCase):
    """The named sites, each re-decoded from the image at its own offset."""

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.off, magic = sit.PD_MARKER
        cls.pd = cls.d[cls.off:cls.off + len(magic)] == magic
        cls.rows = {r["offset"]: r
                    for r in sit.scan(cls.d, cls.pd, sit.BLOCK_BASE_HI)}
        cls.index_rows = sit.owning_rows()

    def test_each_named_site_decodes_to_its_stated_operands(self):
        # The one that matters most, because it is the whole of what the
        # write-up's census rests on. Read off the image rather than off
        # `scan()`, so a construction rewritten in the firmware fails here
        # instead of passing on a pair of stale numbers that agree with each
        # other. The four byte offsets are the tool's own named constants, so
        # a change to the shape has to be a change here too.
        for off, row in sorted(self.rows.items()):
            with self.subTest(site=f"0x{off:04X}"):
                self.assertEqual(self.d[off], 0x75, "not `mov B,#imm`")
                self.assertEqual(self.d[off + 1], 0xF0, "not B")
                self.assertEqual(self.d[off + 2], row["stride"])
                self.assertEqual(self.d[off + 3], 0xA4, "not `mul AB`")
                self.assertEqual(self.d[off + 4], 0x24, "not `add A,#imm`")
                self.assertEqual(self.d[off + 5], row["base_off"])
                self.assertEqual(self.d[off + 6], 0xF5, "not `mov direct,a`")
                self.assertEqual(self.d[off + 7], 0x82, "not DPL")
                self.assertEqual(self.d[off + 8], 0xE4, "not `clr A`")
                self.assertEqual(self.d[off + 9], 0x34, "not `addc A,#imm`")
                self.assertEqual(self.d[off + 10], row["base_hi"])
                self.assertEqual(row["base"],
                                 (row["base_hi"] << 8) | row["base_off"])
                self.assertEqual(row["base_hi"], sit.BLOCK_BASE_HI,
                                 "a site on another base page is not one of "
                                 "this block's, and is not counted as one")

    def test_the_dph_store_column_is_read_off_the_image_not_assumed(self):
        # Half the census `ret`s with the page still in the accumulator, so
        # this column decides how the census is read and it has to be the two
        # bytes at the site's own offset. Pinned by both outcomes rather than
        # by a count: a scan that required the store would report the majority
        # of these sites absent, and the case that catches it is one that
        # fails for a site without the store.
        for off, row in sorted(self.rows.items()):
            with self.subTest(site=f"0x{off:04X}"):
                after = off + sit.CONSTRUCTION_LEN
                has = (self.d[after] == 0xF5 and self.d[after + 1] == 0x83)
                self.assertEqual(row["dph_store"], has,
                                 "the dph_store column is not the two bytes "
                                 "at the site's own offset")
        self.assertTrue(any(r["dph_store"] for r in self.rows.values()),
                        "no site ends with `mov DPH,A`; the two outcome "
                        "directions above are then not both exercised")
        self.assertTrue(any(not r["dph_store"] for r in self.rows.values()),
                        "every site ends with `mov DPH,A`; a scan that "
                        "required it would then be indistinguishable here")

    def test_every_selected_site_is_on_an_instruction_line_of_a_listing(self):
        # The cross-check that separates a census from a byte scan: a linear
        # scan finds the eleven bytes inside somebody's immediate operand too,
        # and this is what says whether it did. Asserted over the sites rather
        # than as a count, so a site that loses its listing says which.
        for off, row in sorted(self.rows.items()):
            with self.subTest(site=f"0x{off:04X}"):
                self.assertEqual(sit.listing_covers(row, self.index_rows),
                                 sit.LISTED,
                                 "a site no committed listing carries as an "
                                 "instruction is a candidate, not a site")

    def test_a_site_no_listing_carries_reads_as_a_candidate_not_a_site(self):
        # The other direction, and the one that catches a cross-check that
        # answers `yes` unconditionally. `0x4A24` is inside the run and no
        # exported function covers it, so a listing that carries it does not
        # exist and the cell has to say so rather than reading as agreement.
        row = {"offset": sit.BLOCK_START + 0x4E}
        self.assertEqual(sit.owner_of(row["offset"], self.index_rows),
                         sit.NO_FUNCTION,
                         "the offset this case needs uncovered is now covered, "
                         "so the negative direction is not exercised")
        self.assertEqual(sit.listing_covers(row, self.index_rows),
                         sit.UNLISTED)

    def test_a_pd_row_never_owns_a_common_area_byte(self):
        # `index.csv`'s `addr` column is a file offset for every program but
        # the PD image, whose rows live at file `0x20000` with their own
        # address space. A lookup that took `pd 4402` for common-area 0x440B
        # would read a second program's listing over the first's -- so the
        # common row has to win, and this is the one address where the two
        # overlap on this image.
        self.assertEqual(sit.owner_of(0x440B, self.index_rows).split()[0],
                         "common",
                         "a PD-image row now owns a common-area byte")
        # The overlap is real rather than theoretical: `ec/decompiled/pd/
        # 4402.asm` exists, and its bytes are file 0x24402, not the common
        # area's 0x4402. That is why its `addr` is not a file offset and why
        # `owning_rows()` drops the scope.
        self.assertTrue(Path(sit.listing_path("pd", "4402")).exists(),
                        "the PD listing this case is about is gone, so the "
                        "overlap no longer exists")
        self.assertEqual(PD_LISTING_BYTES, self.d[0x24402:0x24402
                                                  + len(PD_LISTING_BYTES)],
                        "file 0x24402 is no longer the bytes `pd/4402.asm` "
                        "lists, so the PD row's addr is a file offset after "
                        "all and `owning_rows()`'s exclusion is wrong")
        self.assertNotEqual(PD_LISTING_BYTES,
                            self.d[0x4402:0x4402 + len(PD_LISTING_BYTES)],
                            "the PD listing now shows the common area's bytes "
                            "at the same address, so the overlap this case is "
                            "about no longer exists")

    def test_the_run_and_its_digest_are_the_bytes_the_write_up_declares(self):
        # The extent is declared, not discovered, so it is held here by its
        # own digest rather than by an address: a byte that moved inside the
        # run has to fail the digest, and a run whose ends moved has to fail
        # the length as well.
        block = self.d[sit.BLOCK_START:sit.BLOCK_END + 1]
        self.assertEqual(len(block), sit.BLOCK_END - sit.BLOCK_START + 1)
        self.assertEqual(hashlib.sha256(block).hexdigest(), BLOCK_SHA,
                         "the bytes at the declared extent are not the bytes "
                         "the write-up's table.sha256 was taken from")
        # The lower bound's own support: the byte above the run is a `ret` and
        # the byte below it is not, which is what `descend()` stops on.
        self.assertEqual(self.d[sit.BLOCK_START - 1], 0x22,
                         "the byte above the run is no longer the `ret` the "
                         "lower bound's walk stops at")
        # The upper bound's own support: the byte after the run is a call
        # target in a committed listing, which is the whole of that claim.
        self.assertIn(sit.BLOCK_END + 1, CALLED,
                      "the byte after the run is no longer called by any "
                      "committed listing, so the upper bound's support is "
                      "gone")

    def test_a_rewritten_pattern_byte_is_not_a_site_and_an_operand_is(self):
        # The two opposite mistakes, and both are easy: a pattern that carries
        # the stride byte misses a site whose stride is anything, and one that
        # omits it reports a stale stride for a site whose is not.
        #
        # The three pattern bytes checked here are the three the scan's own
        # predicate treats as half-matches -- an opcode with an operand byte
        # next to it. Checking the opcode alone would let a scan match a
        # `mov 0x??,a` that is not `mov DPL,A`, which is the mistake that
        # reading the operand off the site rather than off the bytes invites.
        off = min(self.rows)
        for at, what in ((1, "the `mov B,#imm` mode byte"),
                         (7, "the `mov DPL,A` operand byte")):
            with self.subTest(byte=f"+{at}", what=what):
                mutated = bytearray(self.d)
                mutated[off + at] ^= 0x01
                after = {r["offset"] for r in sit.scan(bytes(mutated), self.pd,
                                                      sit.BLOCK_BASE_HI)}
                self.assertNotIn(
                    off, after,
                    f"a construction whose {what} is rewritten is still "
                    "reported as a site")
        operand = bytearray(self.d)
        operand[off + sit.STRIDE_BYTE] ^= 0x01
        again = {r["offset"]: r for r in sit.scan(bytes(operand), self.pd,
                                                  sit.BLOCK_BASE_HI)}
        self.assertIn(off, again, "a stride operand is a reported figure, not "
                                  "a pattern byte; changing one must not lose "
                                  "the site")
        self.assertEqual(again[off]["stride"],
                         self.rows[off]["stride"] ^ 0x01)

    def test_a_truncated_buffer_is_a_verdict_and_not_an_index_error(self):
        # A scan over a buffer shorter than the pattern would otherwise raise
        # on the last few offsets, and a crash on a short fixture is the shape
        # of a latent hole -- `trace_xdata_refs.is_dptr_rebuild()`'s reason for
        # bounds-checking at the predicate rather than at the loop.
        for cut in (0, 1, sit.CONSTRUCTION_LEN - 1, sit.CONSTRUCTION_LEN):
            with self.subTest(cut=cut):
                self.assertEqual(sit.scan(self.d[:cut], self.pd), [])

    def test_the_callers_are_asked_for_the_register_they_actually_write(self):
        # The mistake a caller row makes when the entry's prologue hands the
        # index in from a register other than the one the site's own listing
        # reads: `common 0x43A5`'s three constructions all end in
        # `mov A, R6`, and six of its seven committed call sites write R7
        # instead, because the prologue at `0x43A5`-`0x43A8` is
        # `xch A, R6 / mov A, R7 / xch A, R6 / mov A, R6`. Searching the
        # callers for R6 found nothing and said so once per site, which reads
        # in prose as a statement about all seven of them and is a statement
        # about neither the register nor the callers.
        self.assertEqual(sit.prologue_index_source(self.d, "common", "43A5", "R6"),
                         "R7",
                         "common 0x43A5's entry no longer hands the index in "
                         "from the caller's R7")
        # An entry whose first two instructions are not that shape reports no
        # hand-off, rather than one inferred from the register it happens to
        # read.
        self.assertEqual(sit.prologue_index_source(self.d, "common", "4A42", "R1"),
                         "",
                         "an entry with no such prologue reports a hand-off it "
                         "does not have")
        # And the register the prologue names is the one the caller rows are
        # then answered against: a run-time write, a hand-off, and the one
        # call site where neither is in front of the `lcall`.
        for scope, addr, at, want in (
                ("common", "451A", 0x45A3, "`mov R7, A` at 0x45A2"),
                ("common", "4921", 0x492A, "`xch A, R7` at 0x4927 hands R1 to R7"),
        ):
            with self.subTest(caller=f"{scope} {addr} at 0x{at:04X}"):
                self.assertTrue(
                    sit.caller_index(self.d, scope, addr, at, "R7").startswith(want),
                    f"the index at {scope} {addr} 0x{at:04X} is no longer "
                    f"reached by {want!r}")
        self.assertEqual(sit.caller_index(self.d, "common", "4666", 0x4685, "R7"),
                         sit.NO_CONSTANT,
                         "the one committed call site that does not establish "
                         "the index register in its own listing is no longer "
                         "the bounded negative")

    def test_the_index_register_is_read_out_of_the_listing_not_guessed(self):
        # Three answers, kept apart because they are three different claims:
        # a register, a literal, or a read. The case pins the shape of each
        # rather than a register per site, so a site whose load moves does not
        # fail here -- the write-up's table is what a reader checks that
        # against, and `--check` holds it to the image.
        kinds = set()
        for off in sorted(self.rows):
            cell = sit.index_load(self.d, off, self.index_rows)
            kind = next((k for k in LOAD_KINDS if cell.startswith(k)), None)
            kinds.add(kind)
            with self.subTest(site=f"0x{off:04X}"):
                self.assertIsNotNone(
                    kind,
                    f"unrecognised index-load cell: {cell!r}")
        self.assertIn("R", kinds,
                      "no site's index load is a register, so the cell the "
                      "census mostly reports is not exercised here")
        self.assertIn("read", kinds,
                      "no site's index load is a read, so the cell that says "
                      "this tool does not follow the address is not "
                      "exercised here")
        # Three named sites pinned to the register the listing in front of
        # them loads, because the case above fixes the *shape* of every cell
        # and a tool that reported the same register for all of them would
        # pass it. Each is a claim about a site, not a census.
        for off, cell in ((0x43B1, "R6"), (0x4A77, "R1"), (0x4A5E, "read")):
            with self.subTest(site=f"0x{off:04X}"):
                self.assertTrue(
                    sit.index_load(self.d, off, self.index_rows).startswith(cell),
                    f"0x{off:04X} no longer indexes with {cell}")
        self.assertNotIn("literal", kinds,
                         "a site's index load is a literal now, so the cell "
                         "the case below is written for is not the only one")
        # The literal branch, on an offset in a committed listing where it is
        # the real answer: `0x4A52` is `mov A,#0x01` in
        # `ec/decompiled/common/4A4D.asm`, and 0x4A53 is the `movc` that uses
        # it. None of the nineteen sites has a literal index load, so without
        # this the branch would be dead code on this image and nothing here
        # would say so.
        self.assertTrue(
            sit.index_load(self.d, 0x4A53, self.index_rows).startswith("literal"),
            "the literal index-load branch is unreachable on the committed "
            "listings, or `mov A,#0x01` at 0x4A52 is no longer the nearest "
            "write to A")


class RecordFramingTests(unittest.TestCase):
    """The record framing, as a claim about named sites and named anchors."""

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.off, magic = sit.PD_MARKER
        cls.pd = cls.d[cls.off:cls.off + len(magic)] == magic
        cls.rows = sit.scan(cls.d, cls.pd, sit.BLOCK_BASE_HI)

    def frame(self, stride, base_off):
        return sit.record_frame(sit.BLOCK_BASE, sit.BLOCK_START, sit.BLOCK_END,
                                stride, base_off)

    def test_each_named_base_offset_lands_where_the_write_up_says(self):
        # The grid every site's `base_off` is framed on starts at the run's
        # first byte, `0x494E`, which is where `+0x4E` lands -- so `common
        # 0x43A5`'s `+0xCC` is record 8 field 6 at stride 15 and not record 0
        # of a grid counted from that base. Stated as (record, field) per site
        # rather than as a count, so a site that moves is named.
        want = {
            0x43B1: (8, 6), 0x43F6: (9, 1), 0x440B: (9, 3), 0x4A77: (8, 8),
            0x4B03: (8, 10), 0x4B2B: (8, 14), 0x4B38: (8, 12),
            0x4A28: (0, 2), 0x4A42: (0, 6), 0x4A5E: (0, 0), 0x4A84: (0, 0),
            0x4AA7: (0, 12), 0x4AB8: (0, 2), 0x4AC5: (0, 0), 0x4AD3: (0, 6),
            0x4AE0: (0, 8), 0x4AEF: (0, 4), 0x4B13: (0, 10),
            # The one site outside the run-start family: `+0x61` is the only
            # base offset here that is not even, and it is nineteen bytes
            # into the 21-byte record 0 rather than at its head.
            0x454F: (0, 19),
        }
        self.assertEqual(set(want), set(r["offset"] for r in self.rows),
                         "the set of named sites and the scanned set differ, "
                         "so the framing table is being held against a stale "
                         "census")
        for row in self.rows:
            off = row["offset"]
            with self.subTest(site=f"0x{off:04X}"):
                self.assertEqual(self.frame(row["stride"], row["base_off"]),
                                 want[off])

    def test_the_same_address_is_a_different_record_on_each_grid(self):
        # The whole of the "two geometries" question, pinned at the address the
        # two readings both name: `0x4900 + 0xCC` is `0x49CC`, and that is
        # record 6 field 0 of the 21-byte grid and record 8 field 6 of the
        # 15-byte one. Which of the two is the record grid is not settled here,
        # and this case is not what settles it.
        self.assertEqual(sit.BLOCK_BASE + 0xCC, 0x49CC,
                         "the +0xCC base is not the address this case frames")
        self.assertEqual(self.frame(21, 0xCC), (6, 0))
        self.assertEqual(self.frame(15, 0xCC), (8, 6))
        self.assertEqual(sit.record_frame(sit.BLOCK_BASE, sit.BLOCK_START,
                                          sit.BLOCK_END, 21, 0x4E),
                         (0, 0))

    def test_the_two_record_figures_are_separate_questions(self):
        # How many whole records fit in the run, and where the 256 index
        # values land relative to it, are different questions with different
        # answers. They are asserted apart because a tool that merged them
        # would pass a case that only checked one.
        self.assertEqual(sit.records_in_run(sit.BLOCK_START, sit.BLOCK_END, 15),
                         (14, 6))
        self.assertEqual(sit.records_in_run(sit.BLOCK_START, sit.BLOCK_END, 21),
                         (10, 6))
        reach = sit.walk_reaches(sit.BLOCK_BASE_HI, sit.LOWEST_BASE_OFF,
                                 sit.BLOCK_START, sit.BLOCK_END, 15,
                                 len(self.d))
        self.assertEqual(reach["indices"], 256)
        self.assertEqual(reach["in_run"], 178)
        self.assertEqual(reach["above_run"], 0)

    def test_the_walk_wraps_inside_the_page_rather_than_climbing(self):
        # The mistake this replaced: the address is eight bits wide, so the
        # walk leaves the run and comes back and a step count is not a stable
        # quantity. Asserted as the property of the address sequence itself --
        # no index reaches past the page, and the run's top is unreachable --
        # so a model that grew the address to 16 bits fails here.
        for stride in (15, 21):
            with self.subTest(stride=stride):
                addrs = sit.index_addresses(sit.BLOCK_BASE_HI, stride,
                                            sit.LOWEST_BASE_OFF)
                self.assertTrue(all(sit.PAGE_LO <= a <= sit.PAGE_HI
                                    for a in addrs),
                                "an index reached outside the page")
                self.assertFalse(any(a > sit.BLOCK_END for a in addrs),
                                 "an index reached above the declared run")
                # An odd stride is a bijection mod 256, so every page address
                # is named exactly once -- which is why the two strides and
                # every anchor agree on the tally.
                self.assertEqual(sorted(set(addrs)),
                                 list(range(sit.PAGE_LO, sit.PAGE_HI + 1)))

    def test_the_declared_run_is_not_the_set_of_bytes_the_constructions_name(self):
        # The run is declared wider than the arithmetic can address, and
        # narrower than the page the arithmetic reaches at its bottom. Both
        # halves are asserted as properties of the run and the page rather
        # than as counts, so what is held is the relationship and not a figure
        # -- `walk.*.indices_in_run` in the write-up's block is where the
        # count lives, and `--check` holds that to these bytes.
        self.assertGreater(sit.BLOCK_END, sit.PAGE_HI,
                           "the declared run no longer extends past the page "
                           "the arithmetic is confined to")
        for stride in (15, 21):
            with self.subTest(stride=stride):
                addrs = set(sit.index_addresses(sit.BLOCK_BASE_HI, stride,
                                                sit.LOWEST_BASE_OFF))
                self.assertTrue(addrs <= set(range(sit.PAGE_LO,
                                                   sit.PAGE_HI + 1)))
                self.assertFalse(addrs & set(range(sit.BLOCK_END + 1,
                                                   sit.PAGE_HI + 2)),
                                 "an index reached a byte above the page's "
                                 "ceiling")
                # Part of what the walk names is below the run, in the code
                # §1 says the export places above it.
                self.assertTrue(any(a < sit.BLOCK_START for a in addrs),
                                "no index fell below the run, so the lower "
                                "bound would be a floor after all")

    def test_a_base_offset_below_the_run_is_refused_not_framed(self):
        # A grid origin one base offset wrong produces an address in the code
        # above the run. It has to read as "outside the run", not as a
        # negative record index or as a record of the code.
        for off in (0x00, 0x20, 0x30, 0x4D):    # 0x4900 .. 0x494D
            with self.subTest(base_off=hex(off)):
                self.assertIsNone(self.frame(15, off))

    def test_no_base_offset_can_land_above_the_run(self):
        # `add A,#off` is eight bits, so the largest address the construction
        # can name is `0x4900 + 0xFF` = `0x49FF` -- inside the run. That is
        # why the run's upper bound is a walk's answer and not an arithmetic
        # one: no site can point past `0x49FF`, whatever the index is. Stated
        # here because it is the one bound of the two this tool cannot derive.
        self.assertIsNotNone(self.frame(15, 0xFF))
        self.assertLessEqual(sit.BLOCK_BASE + 0xFF, sit.BLOCK_END)


class BoundaryTests(unittest.TestCase):
    """The walk's verdicts at the two ends, held to the addresses asked for."""

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.index_rows = sit.owning_rows()

    def test_the_walk_verdicts_are_the_three_the_primitive_defines(self):
        self.assertEqual(set(sit.VERDICTS), {sit.REACHED, sit.NOT_REACHED,
                                             sit.UNKNOWN})
        for seed, target in ((0x4947, sit.BLOCK_START),
                             (0x4A26, sit.BLOCK_END + 1)):
            with self.subTest(seed=hex(seed), target=hex(target)):
                self.assertIn(sit.walk_verdict(self.d, "common", seed, target),
                              sit.VERDICTS)

    def test_the_walk_reports_the_bytes_it_decodes_and_only_those(self):
        # Both directions, because a predicate that answered `not-reached` for
        # everything would pass every negative above. The two positive
        # targets are the seed's own first instruction and the byte after it,
        # both of which `descend()` decodes as instructions on this image.
        for seed, target in ((0x4947, 0x4947), (0x4947, 0x4948),
                             (0x4A26, 0x4A28)):
            with self.subTest(seed=hex(seed), target=hex(target)):
                self.assertEqual(sit.walk_verdict(self.d, "common", seed,
                                                  target),
                                 sit.REACHED,
                                 "the walk no longer reports an instruction "
                                 "it decodes, so every negative below is "
                                 "vacuous")

    def test_the_function_above_the_run_does_not_walk_into_it(self):
        # The upper bound's negative half: the family that reads the block
        # reads it with `movc a,@a+dptr`, which is a CODE read and not a
        # decode, so no seed in the family decodes a byte of the run.
        arm_row = sit.owner_of(0x4A28, self.index_rows)
        self.assertNotEqual(arm_row, sit.NO_FUNCTION)
        seed = int(arm_row.split()[1], 16)
        self.assertEqual(sit.walk_verdict(self.d, "common", seed,
                                          sit.BLOCK_START),
                         sit.NOT_REACHED,
                         "the family that reads the block now decodes a byte "
                         "inside it, so the block's lower-bound argument has "
                         "to be restated")

    def test_the_run_length_tiles_at_the_two_byte_entry_width(self):
        tags = sit.entry_tags(self.d, sit.BLOCK_START, sit.BLOCK_END)
        span = sit.BLOCK_END - sit.BLOCK_START + 1
        self.assertEqual(tags["fields"] * sit.ENTRY_LEN, span,
                         "the run no longer tiles at the 2-byte entry width, "
                         "which is what its declared extent rests on")
        self.assertLess(tags["distinct_tags"], tags["fields"],
                        "the entry offsets hold nearly as many distinct bytes "
                        "as there are entries; that would not contradict the "
                        "tiling but it is worth a red run")

    def test_convergence_alone_decides_neither_end(self):
        # The reason `--boundary` prints it beside a walk rather than instead:
        # on this run every offset in the block is a fine instruction
        # boundary, so the framing evidence is uninformative in both
        # directions. A run that stopped here would have "established" that
        # the block is code.
        for at in (sit.BLOCK_START, sit.BLOCK_END + 1):
            with self.subTest(at=hex(at)):
                onto, over = sit.converges_from(self.d, at)
                self.assertEqual(onto + over, 24)
                self.assertGreater(onto, over,
                                   "the convergence count is no longer the "
                                   "uninformative one this page describes")


class RefusalTests(unittest.TestCase):
    """One case per refusal, each written against the error it catches.

    Every one of these was run once with the mutation in place to confirm the
    suite goes red without the guard. They exercise the *functions*, so they
    hold whichever entry point a caller reaches them through.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()

    def test_an_even_stride_is_refused_with_the_bijection_as_the_reason(self):
        # The mistake is a record width that happens to be even, read as
        # though the record count it prints means what the odd stride's does.
        # At even parity `A*stride mod 256` reaches half the offsets, so the
        # two figures are different quantities.
        for stride in (2, 14, 16):
            with self.subTest(stride=stride):
                with self.assertRaises(SystemExit) as caught:
                    sit.check_stride(stride)
                self.assertIn("bijection", str(caught.exception))
                self.assertIn(str(stride), str(caught.exception))

    def test_a_non_positive_stride_is_refused(self):
        # The zero case a division would otherwise raise on, and the negative
        # one a `range` would silently accept.
        for stride in (0, -15):
            with self.subTest(stride=stride):
                with self.assertRaises(SystemExit):
                    sit.check_stride(stride)

    def test_a_base_outside_the_common_area_is_refused_by_name(self):
        # The mistake is passing a bank runtime address, which is not a file
        # offset for the two windows `REGIONS` gives base 0x8000.
        for base in (0xC000, 0x8A26, 0x8000):
            with self.subTest(base=hex(base)):
                with self.assertRaises(SystemExit) as caught:
                    sit.check_block(base)
                self.assertIn("common area", str(caught.exception))
                self.assertIn(f"0x{base:04X}", str(caught.exception))

    def test_a_run_declared_past_the_end_of_the_image_is_refused(self):
        # A mistyped extent read as a short table: the tally simply comes out
        # empty and the answer is a zero that looks like a measurement.
        with self.assertRaises(SystemExit) as caught:
            sit.walk_reaches(sit.BLOCK_BASE_HI, sit.LOWEST_BASE_OFF,
                             sit.BLOCK_START, len(self.d) + 0x1000, 15,
                             len(self.d))
        self.assertIn("outside the image", str(caught.exception))

    def test_the_even_stride_refusal_is_also_reached_through_walk_reaches(self):
        # `walk_reaches()` is its own guard's only caller, so without this the
        # refusal above would be reachable from one entry point and not the
        # other.
        with self.assertRaises(SystemExit) as caught:
            sit.walk_reaches(sit.BLOCK_BASE_HI, sit.LOWEST_BASE_OFF,
                             sit.BLOCK_START, sit.BLOCK_END, 14)
        self.assertIn("bijection", str(caught.exception))


class WriteupTests(unittest.TestCase):
    """The write-up's declared figures, and the commands that re-derive them.

    The figures are the write-up's and the tool's `--check` holds them to the
    image. What is held here is that the check exists, that it is a real
    subprocess invocation of the committed tool, and that a block edited out
    of agreement goes red -- because a `--check` that has quietly stopped
    comparing looks exactly like one that is working.
    """

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), str(FIRMWARE),
                               *args], capture_output=True, text=True)

    def test_check_passes_on_the_committed_writeup(self):
        run = self.run_tool("--check")
        self.assertEqual(run.returncode, 0,
                         f"--check is red on the committed write-up:\n"
                         f"{run.stderr}")

    def test_a_figure_that_moved_goes_red(self):
        # The mutation case: one figure in the committed block changed, and
        # the check has to notice. Done on a copy so the write-up on disk is
        # not what is being tested.
        text = WRITEUP.read_text()
        start = text.index(f"```{sit.BLOCK_LANG}\n")
        end = text.index("```\n", start + 4)
        body = text[start + len(f"```{sit.BLOCK_LANG}\n"):end]
        moved = body.replace("table.bytes = ", "table.bytes = 999", 1)
        self.assertNotEqual(moved, body,
                            "the mutation did not apply; this case would pass "
                            "for the wrong reason")
        with tempfile.TemporaryDirectory() as scratch:
            copy = Path(scratch) / WRITEUP.name
            copy.write_text(text[:start] + f"```{sit.BLOCK_LANG}\n" + moved
                            + text[end:])
            run = self.run_tool("--check", str(copy))
        self.assertEqual(run.returncode, 1,
                         "a figure that no longer re-derives is not caught:\n"
                         f"{run.stdout}\n{run.stderr}")
        self.assertIn("table.bytes", run.stderr,
                      "the red run does not name the figure that moved")

    def test_a_writeup_with_no_block_is_refused_not_read_as_agreeing(self):
        with tempfile.TemporaryDirectory() as scratch:
            empty = Path(scratch) / "no-block.md"
            empty.write_text("# a page with no declared figures\n")
            run = self.run_tool("--check", str(empty))
        self.assertEqual(run.returncode, 1)
        self.assertIn("no fenced", run.stderr)

    def test_a_dump_without_the_pd_marker_is_reported_as_unidentified(self):
        # `region_of()` files the `0x20000-0x2FFFF` span under `unknown` when
        # the marker is absent, and a site there belongs to neither program's
        # count. That refusal is unreachable on the committed dump -- the
        # marker is in it -- so it is reached here on a copy with the marker
        # bytes removed rather than left as a branch nothing runs.
        raw = bytearray(FIRMWARE.read_bytes())
        off, magic = sit.PD_MARKER
        raw[off:off + len(magic)] = b"\x00" * len(magic)
        with tempfile.TemporaryDirectory() as scratch:
            copy = Path(scratch) / "no-marker.bin"
            copy.write_bytes(bytes(raw))
            run = subprocess.run([sys.executable, str(TOOL), str(copy),
                                  "--sites", "--base", "0x49"],
                                 capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("unknown", run.stdout,
                      "a dump whose PD marker is gone still reports its "
                      "sites as another program's")
        self.assertIn("ITE8850-PD", run.stderr,
                      "the note naming the missing marker is not printed")

    def test_a_missing_firmware_file_is_a_refusal_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as scratch:
            run = subprocess.run(
                [sys.executable, str(TOOL), str(Path(scratch) / "absent.bin")],
                capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertNotIn("Traceback", run.stderr)

    def test_emit_block_reproduces_the_committed_block(self):
        # `--check` says "regenerate rather than edit"; this is the half that
        # leaves a way to regenerate, so it is held to the same bytes the
        # write-up carries rather than only to itself.
        run = self.run_tool("--emit-block")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(run.stdout, WRITEUP.read_text(),
                      "the block the tool emits is not the block the write-up "
                      "carries, so `--check` would be red and nothing here "
                      "says which of the two moved")


# The byte column of the PD listing's first instruction line, read through
# the tool's own listing parser so the comparison below is against the bytes
# that listing actually carries rather than against a transcription of them.
PD_LISTING_BYTES = bytes.fromhex(
    next(sit.LISTING_LINE.match(line).group("bytes")
         for line in Path(sit.listing_path("pd", "4402")).read_text().splitlines()
         if sit.LISTING_LINE.match(line)))

# The four shapes an index-load cell can have, longest first so
# `no index load` is not read as a prefix of something shorter. Ordered rather
# than a set because the classification is a prefix match and `read` must not
# be tried after `R` on a cell that is neither.
LOAD_KINDS = ("no index load", "literal", "read", "R")

# The digest of the declared extent, taken from the committed image and copied
# from `--emit-block` so this file and the write-up hold the same bytes. It is
# a measurement over `ec/firmware/GMxMGxx_11.800`, not a count of this tree,
# and no change to this repository can move it.
BLOCK_SHA = "9ecf1319a6dcc9f3b4b044ae66f3c2726198dbb81f4b12d9eb9359d7bf8c1100"

# Every address a committed listing transfers control to, read once from the
# `.asm` tree the tool reads. Built at import so `test_the_run_and_its_digest_
# are_the_bytes_the_write_up_declares` can assert that the byte above the run
# is still a call target -- which is the whole of the upper bound's support.
def _called_addresses():
    out = set()
    for scope in sorted(os.listdir(sit.DECOMPILED)):
        sub = os.path.join(sit.DECOMPILED, scope)
        if not os.path.isdir(sub):
            continue
        for name in sorted(os.listdir(sub)):
            if not name.endswith(".asm"):
                continue
            text = (Path(sub) / name).read_text(errors="replace")
            for _at, rest in sit.listing_fields(text):
                m = sit.CALL_TARGET.match(rest)
                if m:
                    out.add(int(m.group("target"), 16))
    return out


CALLED = _called_addresses()


if __name__ == "__main__":
    unittest.main()
