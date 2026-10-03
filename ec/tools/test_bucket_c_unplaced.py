#!/usr/bin/env python3
"""Offline checks for `bucket_c_unplaced.py`: no hardware, no capture, no
Ghidra, and for the parts that would need a live read nothing but the committed
firmware.

The tool's own `--self-test` holds the refusals that need the image.
`--check` is the reproducibility half and is driven from here too, in both
directions, because a `--check` that has quietly stopped failing looks exactly
like a `--check` that is working. What is here and not there is everything a
fixture can answer: the closed vocabularies from the other side of
`SystemExit`, the geometry of the two distance columns against hand-built
regions, and the figure pin that holds the prose's copy of the derived count.

**The oracle is transcribed into this docstring, not read from the tool.** From
`ec/annotations/bank-call-audit.md` §5 and
[`docs/findings/ec-data-regions.md`](../docs/findings/ec-data-regions.md) §4, as
those files state them:

    * 140 bucket-C sites, upper bound, 83 of them anchored;
    * 102 distinct targets across those sites;
    * exactly 1 of those 102 is also an address some BL51 trampoline names, and
      it is `0xE000`;
    * `0x021C6` is that site's own site: 24 of 24, `lcall 0xE000`;
    * `0x021C6` is **0x12 past** `common-219c-ff-triples`'s `file_hi` of
      `0x21B4`, with `d[0x21C5] = 0xE0` in between, and the `ff-triples` shape
      does **not** decode at it;
    * it is 921 bytes below the nearest instruction start `bucket_c_codemap.md`
      decoded;
    * `0x055DC`, `0x00381` and `0x06952` are **labelled**, so they are absent
      from this population by construction;
    * the 35 labelled sites include 33 anchored, leaving 50 anchored unplaced.

Those figures were written down by enumerations this tool does not perform and
must not be able to grade itself against. A tool that computed its own
expectation would pass whenever its arithmetic drifted with the thing it
measures; these are literals, and a change to the census that moved any of them
is a change `audit_call_targets.py` has to explain in its own write-up first.
The same arrangement `test_bucket_c_codemap.py` and `test_data_regions.py`
describe.

**The figure pin, and why it is a check rather than an edit.** The unplaced count
is stated in prose in `data-regions.yaml`'s header, in `bank-call-audit.md`, and
in `data_regions.py`'s module docstring. None is edited here: no region is added
by this change, so the number is not moving, and editing shared files to restate
a figure that is already right is the churn CLAUDE.md's totals rule was written
about. Instead the derived count is held against each of them, so the next
region to be listed turns the run red *by name* rather than leaving a stale
sentence for a reader to catch. That is `check_citation_lines.py`'s model -- hold
the claim against one derivation -- and it is the direct opposite of the failure
CLAUDE.md records at bit #1169, where four concurrent branches each bumped a
hard-coded count from a different base.

**What is deliberately not here.** No case asserts that a site *means*
anything. `code` is a statement about where a byte falls relative to something
this repository's walk decoded, and nothing in this suite says any byte is or is
not a call -- the module docstring's §4c sentence is the statement of that.
`bucket-call-targets.csv` and `registers.yaml` are asserted to be *untouched*,
which is a fact about two files rather than a reading of the firmware.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# bucket_c_unplaced imports bucket_c_codemap by bare module name, the way
# register_ref_table.py does, so the tool directory has to be on the path before
# it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'bucket_c_unplaced', HERE / 'bucket_c_unplaced.py')
bcu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bcu)
import bucket_c_codemap as bcc        # noqa: E402  (needs the path above)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')
COMMITTED_CSV = HERE.parent / 'annotations' / 'bucket-c-unplaced.csv'
ANNOTATIONS = HERE.parent / 'annotations' / 'ghidra-functions.csv'
INDEX = HERE.parent / 'decompiled' / 'index.csv'
TOOL = str(HERE / 'bucket_c_unplaced.py')

# The oracle. See the module docstring for why these are literals and not
# something read back from the tool's own output.
ORACLE_SITES = 140
ORACLE_ANCHORED = 83
ORACLE_TARGETS = 102
ORACLE_TRAMPOLINE_NAMED = 1
ORACLE_TRAMPOLINE_TARGET = 0xE000
ORACLE_LABELED = 35
ORACLE_LABELED_ANCHORED = 33
ORACLE_UNPLACED_ANCHORED = 50
ORACLE_SITE = 0x021C6
ORACLE_REGIONS_GAP = 0x12
ORACLE_BYTE_BEFORE = 0xE0
ORACLE_FRONTIER = 921
ORACLE_LABELLED_ABSENT = (0x055DC, 0x00381, 0x06952)

# The prose files that state the derived unplaced count, and the shape of the
# sentence each states it in. Held, not edited -- see the module docstring.
#
# The regexes are deliberately narrow: each has to match the sentence that
# actually carries the figure, so a file that dropped its mention fails here
# instead of quietly passing a check with nothing to compare against. That is
# the vacuous-pass direction `test_readme_suite_table.py` documents, and it is
# why these cases assert a *non-empty* match list before comparing any of it.
#
# Each is anchored on the words *around* the figure rather than on the figure's
# own sentence, because the YAML header states it inside a run of `#` comment
# lines and the wrap puts a `#` between "the other 105" and "bucket-C sites".
# The words are what identify the claim; the number is what the run compares.
FIGURE_PINS = (
    ("ec/annotations/data-regions.yaml",
     re.compile(r"the other (\d+) # bucket-C sites")),
    ("ec/annotations/bank-call-audit.md",
     re.compile(r"the other (\d+) are not thereby calls")),
    ("ec/tools/data_regions.py",
     re.compile(r"the (\d+) bucket-C sites that fall")),
)


REPO = HERE.parent.parent


def _pinned(repo_relative: str) -> str:
    """The text of a repo-relative file named in `FIGURE_PINS`.

    Line breaks collapsed to single spaces. `data-regions.yaml` states its
    figure inside `#` comment lines, so the collapse has to keep the `#` as a
    token rather than strip it -- the wrap carries one into the middle of the
    sentence the regex has to match.
    """
    return " ".join((REPO / repo_relative).read_text().split())


_CENSUS = None


def census(d=None):
    """The census over the committed image, built once and shared.

    Memoised because `Census.__init__` runs the whole recursive descent, and
    every class that asks for the census wants the same object over a file that
    cannot change while the suite runs. The image is read once for the same
    reason: a case that mutated it would not be testing what its name says.
    """
    global _CENSUS
    if d is not None:
        return bcu.Census(d, str(ANNOTATIONS), str(INDEX))
    if _CENSUS is None:
        _CENSUS = bcu.Census(image(), str(ANNOTATIONS), str(INDEX))
    return _CENSUS


def image() -> bytes:
    """The committed firmware, read once and shared."""
    global _IMAGE
    if _IMAGE is None:
        _IMAGE = Path(FIRMWARE).read_bytes()
    return _IMAGE


def table():
    """The census as `CSV_HEAD`/cell dicts, over the committed image."""
    global _TABLE
    if _TABLE is None:
        _TABLE = bcu.table_dicts(image(), str(ANNOTATIONS), str(INDEX))
    return _TABLE


def generated() -> str:
    """What the tool generates for the committed image, once and shared.

    `csv_text()` re-runs the whole recursive descent on every call, so a suite
    that compared it a dozen times paid for the walk a dozen times.
    """
    global _GENERATED
    if _GENERATED is None:
        _GENERATED = bcu.csv_text(image(), str(ANNOTATIONS), str(INDEX))
    return _GENERATED


_IMAGE = None
_TABLE = None
_GENERATED = None


class ParseTests(unittest.TestCase):
    """The committed table parses, and parses into what the tool produces.

    First, and on its own, because every set comparison below would pass
    vacuously against an empty parse: a header that fails to split, or a row
    count of zero, satisfies `set(...) == set(...)` just as well as a correct
    table does. That is the `test_readme_suite_table.py` failure wearing a
    pass's clothes.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = image()
        cls.text = COMMITTED_CSV.read_text()
        with COMMITTED_CSV.open(newline="") as fh:
            cls.rows = list(csv.DictReader(fh))

    def test_the_header_is_exactly_the_declared_columns(self):
        header = self.text.split("\n", 1)[0]
        self.assertEqual(header, ",".join(bcu.CSV_HEAD))

    def test_every_row_has_a_cell_for_every_column(self):
        # `csv.DictReader` puts a short row's missing cells in `None` and a
        # long row's surplus under `None` as the key, so a ragged table reads
        # back without raising. Checking the keys catches both.
        self.assertTrue(self.rows)
        for row in self.rows:
            self.assertEqual(set(row), set(bcu.CSV_HEAD),
                             f"ragged row at {row.get('file_offset')}")
            for col, cell in row.items():
                self.assertIsNotNone(cell, f"{col} is missing")

    def test_every_verdict_and_reason_is_in_the_closed_vocabulary(self):
        for row in self.rows:
            self.assertIn(row["verdict"], bcu.VERDICTS, row["file_offset"])
            self.assertIn(row["verdict_reason"],
                          bcu.VERDICT_REASONS[row["verdict"]],
                          f"{row['file_offset']} -> {row['verdict_reason']!r}")
            self.assertIn(row["grid_state"], bcu.GRID_STATES,
                          row["file_offset"])

    def test_the_rows_are_sorted_by_offset_so_two_runs_cannot_disagree(self):
        offsets = [int(r["file_offset"], 16) for r in self.rows]
        self.assertEqual(offsets, sorted(offsets))

    def test_the_census_reads_back_what_the_tool_wrote(self):
        # The direction that makes the rest meaningful: the parsed rows are the
        # tool's own output, not a table assembled by hand and compared against
        # something else. So the committed CSV has to parse into exactly what a
        # fresh run derives -- a round trip, not a spot check.
        text = generated()
        with io.StringIO(text) as fh:
            self.assertEqual(list(csv.DictReader(fh)), self.rows)


class VocabularyTests(unittest.TestCase):
    """The vocabularies are closed, from the other side of `SystemExit`.

    The tool's `--self-test` runs these against the image; these run them
    without one, so a refusal that only fires once the image loads is not the
    only thing covering it.
    """

    def test_a_verdict_outside_the_vocabulary_is_refused(self):
        for outside in ("probably-code", "", "Code", "CODE", "resolved",
                        "trampolines", None, 0, 1):
            with self.assertRaises(SystemExit) as caught:
                bcu.check_verdict(outside, "ret")
            self.assertIn("is not one of", str(caught.exception))

    def test_an_empty_reason_is_refused_rather_than_rendered(self):
        # The case a hand-edited table gets wrong: a blank `verdict_reason` cell
        # still looks like a row, and nothing downstream can tell it from a site
        # this method declined for no stated reason at all.
        for blank in ("", "   ", "\t", "\n"):
            with self.assertRaises(SystemExit) as caught:
                bcu.check_verdict(bcu.UNRESOLVED, blank)
            self.assertIn("empty reason", str(caught.exception))

    def test_a_reason_outside_its_verdicts_set_is_refused(self):
        for verdict in bcu.VERDICTS:
            for other in bcu.VERDICTS:
                if other == verdict:
                    continue
                borrowed = sorted(bcu.VERDICT_REASONS[other])[0]
                with self.assertRaises(SystemExit) as caught:
                    bcu.check_verdict(verdict, borrowed)
                self.assertIn("is not a", str(caught.exception))

    def test_every_verdict_has_at_least_one_reason(self):
        # The other direction: a verdict nothing can be emitted for is a member
        # of a closed vocabulary that no row will ever carry, which is how a
        # column quietly stops meaning anything.
        for verdict in bcu.VERDICTS:
            self.assertTrue(bcu.VERDICT_REASONS[verdict],
                            f"{verdict} has no reason in its vocabulary")

    def test_no_two_verdicts_share_a_reason(self):
        # Keeps `verdict_for()`'s ordered first-match rule unambiguous: if a
        # reason belonged to two verdicts, which one a row carried would depend
        # on evaluation order rather than on the bytes.
        seen = set()
        for reasons in bcu.VERDICT_REASONS.values():
            self.assertFalse(seen & reasons,
                             f"{sorted(seen & reasons)} belongs to two verdicts")
            seen |= set(reasons)

    def test_the_unresolved_reasons_are_the_walks_own_vocabulary(self):
        # Borrowed rather than restated, so this file and bucket_c_codemap.py
        # cannot disagree about why a site came out unresolved. A copy would
        # drift the first time the walk gained a reason.
        self.assertIs(bcu.VERDICT_REASONS[bcu.UNRESOLVED], bcc.WALK_REASONS)

    def test_a_fifth_verdict_is_refused_rather_than_rendered(self):
        # Named explicitly rather than left to the loop above: the closedness
        # claim is about the *size* of the vocabulary too, and a future edit
        # that appended a member should have to delete this.
        self.assertEqual(len(bcu.VERDICTS), 4)
        with self.assertRaises(SystemExit):
            bcu.check_verdict("resolved", "ret")


class NearestRegionTests(unittest.TestCase):
    """`nearest_region()` against hand-built regions, including the tie.

    The distance definition is the load-bearing thing here: §4 of
    `ec-data-regions.md` states `0x021C6` as 0x12 past `common-219c-ff-triples`'s
    `file_hi`, and a definition measured from the last entry byte instead puts
    this column one away from the committed sentence it exists to support --
    which is a disagreement a reader cannot resolve without re-deriving both.
    """

    REGIONS = [
        {"name": "aaa-first", "file_lo": 0x10, "file_hi": 0x20, "stride": 2},
        {"name": "bbb-second", "file_lo": 0x40, "file_hi": 0x50, "stride": 3},
    ]

    def test_a_site_inside_a_region_is_zero_away(self):
        region, dist = bcu.nearest_region(self.REGIONS, 0x15)
        self.assertEqual((region["name"], dist), ("aaa-first", 0))

    def test_a_site_before_a_region_measures_to_its_first_byte(self):
        region, dist = bcu.nearest_region(self.REGIONS, 0x0D)
        self.assertEqual((region["name"], dist), ("aaa-first", 3))

    def test_a_site_past_a_region_measures_from_file_hi_and_not_from_its_last_byte(self):
        # 0x20 is `file_hi`, the byte *after* the last entry at 0x1F, so the
        # distance is 0 and not 1. This is the convention §4's 0x12 depends on:
        # 0x21C6 - 0x21B4 is 0x12, while 0x21C6 - 0x21B3 is the 0x13 §4 gives for
        # the same site measured from the last entry.
        region, dist = bcu.nearest_region(self.REGIONS, 0x20)
        self.assertEqual((region["name"], dist), ("aaa-first", 0))
        _, after = bcu.nearest_region(self.REGIONS, 0x21)
        self.assertEqual(after, 1)

    def test_the_closest_region_wins_and_ties_break_on_the_name(self):
        # Deterministic without relying on the region order in the YAML, which
        # is stable today and would make the table stable for a reason nobody
        # wrote down.
        _, dist = bcu.nearest_region(self.REGIONS, 0x21)
        self.assertEqual(dist, 1)
        tied = [{"name": "zzz", "file_lo": 0x00, "file_hi": 0x08, "stride": 2},
                {"name": "aaa", "file_lo": 0x20, "file_hi": 0x28, "stride": 2}]
        region, _ = bcu.nearest_region(tied, 0x14)
        self.assertEqual(region["name"], "aaa")

    def test_no_regions_at_all_yields_no_region_and_no_distance(self):
        self.assertEqual(bcu.nearest_region([], 0x15), (None, None))


class GridStateTests(unittest.TestCase):
    """`grid_state()` against hand-built regions and bytes.

    The three answers are the same measurement the verdict gates on, so a
    swapped guard would report a table entry for a byte that is off the grid --
    which is the one mistake this column exists to prevent.

    The fixture lays its entries down *at* 0x100 rather than at the start of
    the buffer: `grid_state()` indexes the image by file offset, and a fixture
    whose bytes sit at 0 would answer about a region at 0x100 whose extent it
    cannot see. `test_walk_branch_arms.py` states the same arrangement from the
    other side, and here it is what makes the addresses in a case the offsets in
    the fixture.
    """

    LEN = 0x120
    LO = 0x100

    @classmethod
    def setUpClass(cls):
        img = bytearray(b"\x00" * cls.LEN)
        # The third entry's leading byte is 0x00 rather than the 0x02 an `ljmp`
        # entry needs, so the grid has a cell in it that does not decode. That
        # is the whole point of the `shape-fails` cell, and `0x021C6` is the
        # real-image case of it: on the stride grid of the `ff-triples` region
        # beside it, and holding 0x12 where an entry would need 0xFF.
        for i, entry in enumerate((b"\x02\x01\x02", b"\x02\x02\x02",
                                   b"\x00\x03\x02")):
            at = cls.LO + i * 3
            img[at:at + 3] = entry
        cls.BYTES = bytes(img)

    @staticmethod
    def region(stride=3, hi=0x109, shape="ljmp-table"):
        return {"name": "t", "file_lo": GridStateTests.LO, "file_hi": hi,
                "stride": stride, "shape": shape}

    def grid(self, off):
        return bcu.grid_state(self.BYTES, self.region(), off)

    def test_an_entry_offset_decodes_and_is_on_grid(self):
        self.assertEqual(self.grid(0x103), bcu.GRID_HOLDS)

    def test_an_offset_on_the_grid_whose_shape_does_not_decode_says_so(self):
        # 0x106 is on the stride grid -- the third entry starts there -- but its
        # leading byte is 0x00 rather than the 0x02 an `ljmp` entry needs.
        # Reported as its own cell rather than as `off-grid`, because "this byte
        # is where an entry would be and it is not one" is a different reading
        # from "this byte is not where an entry would be", and `0x021C6` is the
        # case that distinction is for.
        self.assertEqual(self.grid(0x106), bcu.GRID_FAILS)

    def test_an_offset_off_the_grid_is_off_grid(self):
        self.assertEqual(self.grid(0x101), bcu.GRID_OFF)
        self.assertEqual(self.grid(0x104), bcu.GRID_OFF)

    def test_the_grid_extends_past_the_declared_end_and_says_so(self):
        # The grid is a property of the stride, not of the span: a byte past
        # `file_hi` can still be on it, and 0x109 is the offset where a table
        # that ran on would place its next entry. Whether that makes a site a
        # *table entry* is the adjacency gate's question in `verdict_for()`,
        # not this function's -- and here it is a byte of zeros, so it does not.
        self.assertEqual(self.grid(0x109), bcu.GRID_FAILS)
        self.assertEqual(self.grid(0x10C), bcu.GRID_FAILS)

    def test_the_shape_actually_decoded_is_what_makes_it_hold(self):
        # The held/fails distinction is the shape decoder's, not a stride test:
        # the same region and the same grid, differing only in what the entry
        # holds.
        self.assertEqual(
            bcu.grid_state(self.BYTES, self.region(), 0x103), bcu.GRID_HOLDS)
        self.assertEqual(
            bcu.grid_state(b"\x00" * self.LEN, self.region(), 0x103),
            bcu.GRID_FAILS)

    def test_a_region_with_no_stride_is_annotated_rather_than_fatal(self):
        # `data_regions.check()` reports a null stride as a span it cannot
        # re-derive. This census is not the place to refuse a region list that
        # tool will read, so the row says why rather than the run dying.
        self.assertEqual(bcu.grid_state(self.BYTES, self.region(stride=None),
                                        0x103), bcu.GRID_NO_STRIDE)
        self.assertEqual(bcu.grid_state(self.BYTES, self.region(stride=0),
                                        0x103), bcu.GRID_NO_STRIDE)

    def test_no_region_at_all_is_the_same_cell_rather_than_a_crash(self):
        self.assertEqual(bcu.grid_state(self.BYTES, None, 0x103),
                         bcu.GRID_NO_STRIDE)


class FrontierTests(unittest.TestCase):
    """`bytes_below_frontier()` on a hand-built instruction-start set.

    The definition is to the nearest instruction *start*, not the nearest
    decoded byte, and the reason is that `bucket-c-codemap.md`'s own figure for
    `0x021C6` was taken under this one. A column that disagreed with a
    committed sentence by two would be a column a reader has to re-derive.
    """

    STARTS = [0x10, 0x20, 0x40]

    def test_a_site_on_an_instruction_start_is_zero_below_the_frontier(self):
        self.assertEqual(bcu.bytes_below_frontier(self.STARTS, 0x20), 0)

    def test_a_site_past_an_instruction_measures_to_that_start(self):
        self.assertEqual(bcu.bytes_below_frontier(self.STARTS, 0x25), 5)
        self.assertEqual(bcu.bytes_below_frontier(self.STARTS, 0x30), 0x10)

    def test_a_site_below_every_start_has_no_frontier_rather_than_a_number(self):
        # `None` is a fact about the seed set -- the walk decoded nothing down
        # there -- and rendering it as 0 would put it in the same column as a
        # site that sits exactly on an instruction.
        self.assertIsNone(bcu.bytes_below_frontier(self.STARTS, 0x05))

    def test_the_frontier_is_the_nearest_start_not_the_lowest(self):
        self.assertEqual(bcu.bytes_below_frontier(self.STARTS, 0x42), 2)
        self.assertEqual(bcu.bytes_below_frontier(self.STARTS, 0x22), 2)


class PopulationTests(unittest.TestCase):
    """The population partitions bucket C, in both directions.

    One direction passes for a census that dropped every row, and the other for
    one that counted each site twice, so both are asserted.
    """

    @classmethod
    def setUpClass(cls):
        cls.census = census()

    def test_unplaced_plus_labelled_is_the_bucket_c_population(self):
        unplaced = self.census.unplaced()
        labelled = self.census.labelled()
        self.assertEqual(len(unplaced) + len(labelled), ORACLE_SITES)
        self.assertEqual(len(self.census.rows), ORACLE_SITES)

    def test_the_two_halves_are_disjoint_and_cover_every_bucket_c_row(self):
        unplaced = {r["file_offset"] for r in self.census.unplaced()}
        labelled = {r["file_offset"] for r in self.census.labelled()}
        bucket_c = {r["file_offset"] for r in self.census.rows
                    if r["bucket"] == "C"}
        self.assertEqual(unplaced & labelled, set())
        self.assertEqual(unplaced | labelled, bucket_c)

    def test_the_population_is_exactly_what_region_at_declines(self):
        from data_regions import region_at
        for r in self.census.unplaced():
            self.assertIsNone(region_at(self.census.regions, r["file_offset"]),
                              f"0x{r['file_offset']:05X}")

    def test_the_anchored_split_matches_the_audit(self):
        unplaced = self.census.unplaced()
        labelled = self.census.labelled()
        self.assertEqual(sum(1 for r in unplaced if r["anchored"]),
                         ORACLE_UNPLACED_ANCHORED)
        self.assertEqual(sum(1 for r in labelled if r["anchored"]),
                         ORACLE_LABELED_ANCHORED)
        self.assertEqual(sum(1 for r in self.census.rows if r["anchored"]),
                         ORACLE_ANCHORED)

    def test_no_mode_drops_a_row(self):
        # `data_regions.py` refuses filtering rather than suppressing a labelled
        # site, and the rule this census inherits is the mirror: the unplaced
        # half is *every* row `region_at()` declines, and the labelled half is
        # still counted beside it. A row the walk never reached is in the table
        # with a verdict, not absent from it.
        rows = table()
        self.assertEqual(len(rows), len(self.census.unplaced()))
        self.assertEqual({t["file_offset"] for t in rows},
                         {f"0x{r['file_offset']:05X}"
                          for r in self.census.unplaced()})


class OracleTests(unittest.TestCase):
    """The figures `bank-call-audit.md` §5 and `ec-data-regions.md` §4 state.

    The literals are in the module docstring. These read the image, so a change
    to `audit_call_targets.py` or to `data-regions.yaml` that moved a count is a
    red run here rather than a new number in this tool's own report.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = image()
        cls.census = census()
        cls.table = {t["file_offset"]: t for t in table()}

    def test_the_census_has_not_moved(self):
        self.assertEqual(len(self.census.rows), ORACLE_SITES)
        self.assertEqual(sum(1 for r in self.census.rows if r["anchored"]),
                         ORACLE_ANCHORED)
        self.assertEqual(len({r["target"] for r in self.census.rows}),
                         ORACLE_TARGETS)
        shared = ({r["target"] for r in self.census.rows}
                  & self.census.trampoline_targets)
        self.assertEqual(len(shared), ORACLE_TRAMPOLINE_NAMED)
        self.assertEqual(shared, {ORACLE_TRAMPOLINE_TARGET})

    def test_the_site_the_write_up_is_about_is_in_the_population(self):
        self.assertIn(f"0x{ORACLE_SITE:05X}", self.table)

    def test_the_three_labelled_sites_are_absent_from_it(self):
        # These are the two phantoms the audit read byte by byte and the
        # entry-aligned site §4 contrasts `0x021C6` with. All three are inside a
        # listed region, so their absence here is the population definition
        # working, not a lookup that failed.
        for off in ORACLE_LABELLED_ABSENT:
            self.assertNotIn(f"0x{off:05X}", self.table, f"0x{off:05X}")

    def test_the_byte_between_the_site_and_the_triples_is_what_they_state(self):
        self.assertEqual(self.d[ORACLE_SITE - 1], ORACLE_BYTE_BEFORE)

    def test_the_gap_to_the_nearest_region_is_what_section_four_pins(self):
        site = self.table[f"0x{ORACLE_SITE:05X}"]
        self.assertEqual(site["nearest_region"], "common-219c-ff-triples")
        self.assertEqual(site["bytes_to_nearest_region"], ORACLE_REGIONS_GAP)

    def test_the_shape_does_not_decode_at_the_site(self):
        # The `ff-triples` shape needs a leading 0xFF; the site's byte is 0x12.
        # Recorded beside the verdict rather than folded into it, because
        # `trampoline` is decided on the *target* and says nothing about the
        # bytes here.
        site = self.table[f"0x{ORACLE_SITE:05X}"]
        self.assertEqual(site["grid_state"], bcu.GRID_FAILS)
        self.assertEqual(self.d[ORACLE_SITE], 0x12)

    def test_the_site_is_the_trampoline_named_target_its_own_site(self):
        site = self.table[f"0x{ORACLE_SITE:05X}"]
        self.assertEqual(site["target"], f"0x{ORACLE_TRAMPOLINE_TARGET:04X}")
        self.assertEqual(site["opcode"], "lcall")
        self.assertEqual(site["target_is_trampoline_entry"], bcu.YES)
        self.assertEqual(site["verdict"], bcu.TRAMPOLINE)

    def test_the_gap_below_the_walk_is_the_one_the_codemap_states(self):
        site = self.table[f"0x{ORACLE_SITE:05X}"]
        self.assertEqual(site["bytes_below_frontier"], ORACLE_FRONTIER)

    def test_the_best_framed_target_is_named_nowhere(self):
        # The one address of the 102 that a trampoline names is also the one no
        # hand annotation names, in either bank. Recorded as `no`, which is
        # "not found by this method" and not a claim that the routine does not
        # exist.
        site = self.table[f"0x{ORACLE_SITE:05X}"]
        self.assertEqual(site["target_named_in"], bcu.NOT_NAMED)
        self.assertNotIn(ORACLE_TRAMPOLINE_TARGET, self.census.annotations)
        self.assertNotIn(ORACLE_TRAMPOLINE_TARGET, self.census.index)


class VerdictRuleTests(unittest.TestCase):
    """The ordered rule, on sites the real census produced.

    Each case names the verdict a swapped guard would give instead, because a
    rule that answers `code` for everything passes any positive-only assertion
    on `code`.
    """

    @classmethod
    def setUpClass(cls):
        cls.table = table()

    def test_a_table_entry_always_has_the_grid_measurement_behind_it(self):
        entries = [t for t in self.table if t["verdict"] == bcu.TABLE_ENTRY]
        for t in entries:
            self.assertEqual(t["grid_state"], bcu.GRID_HOLDS, t["file_offset"])
            self.assertLessEqual(t["bytes_to_nearest_region"],
                                 int(self._stride(t)), t["file_offset"])

    @staticmethod
    def _stride(t):
        """The nearest region's stride, for the adjacency a `table-entry` claims."""
        import yaml
        doc = yaml.safe_load((HERE.parent / 'annotations'
                              / 'data-regions.yaml').read_text())
        for reg in doc["regions"]:
            if reg["name"] == t["nearest_region"]:
                return reg["stride"]
        raise AssertionError(f"{t['nearest_region']} is not a listed region")

    def test_no_table_entry_is_far_from_the_region_it_is_attributed_to(self):
        # The adjacency gate, stated as a property rather than as a fixture:
        # every `table-entry` sits within one stride of its region, so no row is
        # a table entry on the strength of one byte matching a shape at some
        # distance.
        for t in self.table:
            if t["verdict"] == bcu.TABLE_ENTRY:
                self.assertLessEqual(t["bytes_to_nearest_region"],
                                     self._stride(t))

    def test_the_ungated_grid_answer_can_disagree_with_the_verdict(self):
        # If every on-grid row were also a table entry, `grid_state` and
        # `verdict` would be one column wearing two names and the adjacency gate
        # would be untested by the image.
        on_grid_not_entry = [t for t in self.table
                             if t["grid_state"] == bcu.GRID_HOLDS
                             and t["verdict"] != bcu.TABLE_ENTRY]
        self.assertTrue(on_grid_not_entry,
                        "no row on a region's grid is anything but a table "
                        "entry, so the gate is doing nothing on this image")

    def test_code_is_not_the_same_question_as_on_an_instruction_boundary(self):
        code = [t for t in self.table if t["verdict"] == bcu.CODE]
        self.assertTrue(code)
        not_boundary = [t for t in code
                        if t["on_instruction_boundary"] == bcu.NO]
        self.assertTrue(not_boundary,
                        "every `code` row also starts an instruction, so the "
                        "boolean is not carrying a second question")

    def test_the_reason_says_which_method_read_the_byte_as_code(self):
        for t in self.table:
            if t["verdict"] == bcu.CODE:
                self.assertIn(t["verdict_reason"], (
                    "on-an-instruction-boundary-this-walk-decoded",
                    "mid-instruction-in-a-span-this-walk-decoded",
                    "inside-a-ghidra-common-function"), t["file_offset"])

    def test_a_ghidra_common_row_is_never_credited_to_the_walk(self):
        # `inside-a-ghidra-common-function` is a *second* method's coverage: the
        # `common` function set `ec/decompiled/index.csv` records, not the #49
        # descent. The write-up and `bank-call-audit.md` §5 both once counted
        # these rows as walk-decoded, which made the two clauses overlap and
        # summed past the `code` total. A row that no walk span covers cannot be
        # described as inside one, whatever the prose says about it — so the
        # property is asserted here instead of a count, which a different seed
        # set would have every merge re-argue.
        by_off = {s.off: s for s in census().sites()}
        ghidra_common = [t for t in self.table
                         if t["verdict_reason"]
                         == "inside-a-ghidra-common-function"]
        self.assertTrue(ghidra_common,
                        "no row is covered by the Ghidra `common` function set, "
                        "so the second method is untested on this image")
        for t in ghidra_common:
            site = by_off[int(t["file_offset"], 16)]
            self.assertFalse(site.in_walk_span,
                             f"{t['file_offset']} is inside a walk span, so "
                             f"the walk -- not the `common` function set -- is "
                             f"the method that read it")
            self.assertTrue(site.in_ghidra, t["file_offset"])
            self.assertEqual(t["on_instruction_boundary"], bcu.NO,
                             t["file_offset"])

    def test_a_walk_spanned_row_is_covered_by_the_walk(self):
        # The converse, so the split above cannot be satisfied by emptying the
        # walk-spanned family and leaving only the `common` one.
        by_off = {s.off: s for s in census().sites()}
        spanned = [t for t in self.table
                   if t["verdict_reason"] in (
                       "mid-instruction-in-a-span-this-walk-decoded",
                       "on-an-instruction-boundary-this-walk-decoded")]
        self.assertTrue(spanned,
                        "no row is covered by a span the walk decoded, so the "
                        "distinction between the two methods is untested")
        for t in spanned:
            self.assertTrue(by_off[int(t["file_offset"], 16)].in_walk_span,
                            t["file_offset"])

    def test_the_reason_a_code_row_carries_follows_from_the_span_that_covers_it(self):
        # The mapping is a function, not a partition that happens to hold: a
        # `code` row is credited to the walk exactly when a walk span covers
        # it. This is the invariant the write-up's prose violated when it called
        # all the non-boundary `code` rows walk-decoded -- the two figures the
        # page quotes (the walk's share and the `common` set's) can only be
        # counted apart if this holds for every row.
        by_off = {s.off: s for s in census().sites()}
        walk_reasons = ("on-an-instruction-boundary-this-walk-decoded",
                        "mid-instruction-in-a-span-this-walk-decoded")
        for t in self.table:
            if t["verdict"] != bcu.CODE:
                continue
            site = by_off[int(t["file_offset"], 16)]
            if site.in_walk_span:
                self.assertIn(t["verdict_reason"], walk_reasons,
                              f"{t['file_offset']}: a walk span covers this "
                              f"byte, so the reason must name the walk")
            else:
                self.assertEqual(t["verdict_reason"],
                                 "inside-a-ghidra-common-function",
                                 f"{t['file_offset']}: no walk span covers "
                                 f"this byte, so it is the `common` function "
                                 f"set's coverage and not the walk's")

    def test_a_mid_instruction_row_and_a_boundary_row_are_told_apart(self):
        # The distinction `0x055DC` is the precedent for: covered by something
        # read as code, and starting an instruction, are two answers.
        on_boundary = [t for t in self.table
                       if t["on_instruction_boundary"] == bcu.YES]
        for t in on_boundary:
            self.assertEqual(t["verdict_reason"],
                             "on-an-instruction-boundary-this-walk-decoded",
                             t["file_offset"])
        for t in self.table:
            if t["verdict_reason"] == "mid-instruction-in-a-span-this-walk-decoded":
                self.assertEqual(t["on_instruction_boundary"], bcu.NO,
                                 t["file_offset"])

    def test_an_unresolved_row_carries_the_walks_own_reason(self):
        for t in self.table:
            if t["verdict"] == bcu.UNRESOLVED:
                self.assertIn(t["verdict_reason"], bcc.WALK_REASONS,
                              t["file_offset"])
                self.assertEqual(t["verdict_reason"], t["walk_reason"],
                                 t["file_offset"])


class CommittedTableTests(unittest.TestCase):
    """`--check` in both directions, and the two invariants about scope."""

    @classmethod
    def setUpClass(cls):
        cls.d = image()
        cls.text = COMMITTED_CSV.read_text()

    def test_the_committed_table_is_what_this_run_derives(self):
        self.assertEqual(generated(),
                         self.text)

    def assert_check_fails(self, doctored_text, what):
        """`check_csv` against a doctored copy, diff kept out of the suite's own
        output. The diff is the tool working; printing it on every run of this
        suite would put a page of expected noise in front of the one real
        failure, which is how a red run stops being read."""
        with tempfile.TemporaryDirectory() as tmp:
            doctored = Path(tmp) / 'bucket-c-unplaced.csv'
            doctored.write_text(doctored_text)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), \
                    contextlib.redirect_stderr(buf):
                rc = bcu.check_csv(self.d, str(doctored), str(ANNOTATIONS),
                                   str(INDEX))
            self.assertEqual(rc, 1, f"a {what} committed table passed --check")
            self.assertIn("not what this run derives", buf.getvalue())

    def test_a_doctored_verdict_cell_fails(self):
        self.assert_check_fails(
            self.text.replace(",code,mid-instruction-in-a-span-this-walk-decoded",
                              ",unresolved,mid-instruction-in-a-span-this-walk-decoded", 1),
            "verdict-doctored")

    def test_a_doctored_reason_cell_fails(self):
        self.assert_check_fails(
            self.text.replace(",code,inside-a-ghidra-common-function",
                              ",code,on-an-instruction-boundary-this-walk-decoded", 1),
            "reason-doctored")

    def test_a_doctored_frontier_cell_fails(self):
        # The gap is the column this census adds over the code map, so a doctored
        # one is the drift `--check` most needs to catch: nothing else in the
        # tree would notice a moved frontier distance.
        self.assert_check_fails(
            self.text.replace(",921,", ",920,", 1),
            "frontier-doctored")

    def test_a_doctored_grid_cell_fails(self):
        self.assert_check_fails(
            self.text.replace(",on-grid shape-fails,",
                              ",on-grid shape-holds,", 1),
            "grid-doctored")

    def test_a_doctored_name_cell_fails(self):
        self.assert_check_fails(
            self.text.replace(",no,code,", ",common:invented,code,", 1),
            "name-doctored")

    def test_a_truncated_csv_fails(self):
        # The other direction: a table that lost rows is a red run too, and a
        # check that only noticed *changed* cells would not notice this.
        self.assert_check_fails("\n".join(self.text.splitlines()[:-1]) + "\n",
                                "truncated")

    def test_a_missing_csv_fails_rather_than_being_created(self):
        # A `--check` that wrote the file it was asked to check is not a check,
        # it is the thing that decides what the committed table says.
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / 'bucket-c-unplaced.csv'
            buf = io.StringIO()
            with contextlib.redirect_stderr(buf):
                rc = bcu.check_csv(self.d, str(absent), str(ANNOTATIONS),
                                   str(INDEX))
            self.assertEqual(rc, 1)
            self.assertIn("never", buf.getvalue())
            self.assertFalse(absent.exists(),
                             "--check created the file it was asked to check")

    def test_the_header_and_the_row_count_agree_with_the_derived_population(self):
        text = generated()
        lines = text.rstrip("\n").split("\n")
        self.assertEqual(lines[0], ",".join(bcu.CSV_HEAD))
        self.assertEqual(len(lines) - 1, len(census().unplaced()))

    def test_the_shared_columns_join_on_the_census(self):
        # Columns 1-6 are `bank-call-targets.csv`'s own, in its own spelling, so
        # a row keyed on `file_offset` from either file carries the same bytes
        # there and a drift between the two is a red run rather than a stale
        # row. `bucket` is not compared: every row here is bucket C by
        # construction, which is the reason it is not carried at all.
        shared = ("runtime", "opcode", "target", "frame_onto", "frame_over")
        census_path = HERE.parent / 'annotations' / 'bank-call-targets.csv'
        with census_path.open() as fh:
            header = fh.readline().rstrip("\n").split(",")
            theirs = {}
            for line in fh:
                cells = line.rstrip("\n").split(",")
                theirs[cells[0]] = dict(zip(header, cells))
        for t in table():
            row = theirs.get(t["file_offset"])
            self.assertIsNotNone(row, f"{t['file_offset']} is not in the census")
            self.assertEqual(row["region"], "common",
                             f"{t['file_offset']} is not a common-area site")
            self.assertEqual(row["bucket"], "C")
            for col in shared:
                # The two counts are integers here and text in the census file,
                # so they are compared as the bytes a reader would see in each --
                # which is what "the same value in both files" actually means.
                self.assertEqual(str(t[col]), row[col],
                                 f"{t['file_offset']} column {col}")


class FigurePinTests(unittest.TestCase):
    """The derived count, held against every file that states it in prose.

    Not an edit -- see the module docstring. The claim is that the figure
    `data-regions.yaml`, `bank-call-audit.md` and `data_regions.py` carry is the
    one this run derives, so the next region to be listed turns the run red and
    names the files rather than leaving four sentences to go quietly stale.
    """

    def test_every_prose_mention_is_found_before_any_of_them_is_compared(self):
        # The vacuous-pass direction, stated as its own case: a regex that stops
        # matching its sentence would make every comparison below an assertion
        # that zero figures agree.
        for path, pattern in FIGURE_PINS:
            with self.subTest(path=path):
                self.assertTrue(pattern.search(_pinned(path)),
                                f"{path} states the count in a shape this "
                                "check no longer recognises")

    def test_the_prose_and_the_census_state_the_same_count(self):
        derived = len(census().unplaced())
        for path, pattern in FIGURE_PINS:
            found = pattern.findall(_pinned(path))
            with self.subTest(path=path):
                self.assertTrue(found, f"{path} mentions no count")
                for stated in found:
                    self.assertEqual(int(stated), derived,
                                     f"{path} says {stated}, this run derives "
                                     f"{derived}")

    def test_the_split_the_files_state_adds_up_to_the_census(self):
        # The same arithmetic each of those sentences performs, held here so a
        # region added to `data-regions.yaml` without the prose moving fails on
        # the sum as well as on each figure.
        c = census()
        unplaced, labelled = len(c.unplaced()), len(c.labelled())
        self.assertEqual(unplaced + labelled, ORACLE_SITES)
        self.assertEqual(labelled, ORACLE_LABELED)
        self.assertEqual(sum(1 for r in c.unplaced() if r["anchored"]),
                         ORACLE_UNPLACED_ANCHORED)


class ScopeTests(unittest.TestCase):
    """The files this change must not have moved, and the flags it must not have.

    `bank-call-targets.csv` is another issue's output and `registers.yaml` is
    the source of truth for register status. Neither is touched here, and these
    are the cases that say so in a way a later branch cannot undo by accident.
    """

    def test_the_census_carries_no_verdict_column(self):
        # The classification lives in its own file, not as a column on a census
        # someone else owns. A `verdict` header cell would be the shape of that
        # mistake even if every row were right. Compared cell-wise, since
        # `verdict` is a substring of the code map's `walk_verdict`.
        with (HERE.parent / 'annotations' / 'bank-call-targets.csv').open() as fh:
            columns = set(fh.readline().strip().split(","))
        for column in ("verdict", "verdict_reason", "grid_state",
                       "walk_verdict", "walk_reason", "containing_function",
                       "on_instruction_boundary", "bytes_below_frontier"):
            self.assertNotIn(column, columns)

    def test_the_code_map_table_gained_no_column_from_this_census(self):
        # The mirror: the sibling census's columns are its own, and this change
        # is a sibling file rather than an extension of it. Compared as a set of
        # header cells rather than as a substring, because `verdict` is a
        # substring of that table's own `walk_verdict` and a substring test would
        # redden on a column this change never touched.
        with (HERE.parent / 'annotations' / 'bucket-c-codemap.csv').open() as fh:
            columns = set(fh.readline().strip().split(","))
        self.assertEqual(columns, set(bcc.CSV_HEAD))
        for column in ("verdict", "verdict_reason", "grid_state",
                       "on_instruction_boundary", "target_named_in",
                       "bytes_below_frontier", "prev_bytes"):
            self.assertNotIn(column, columns)

    def test_no_region_was_added_or_edited(self):
        # This census adds no claim about the image. A region entry appearing or
        # moving would be one, and `data_regions.py --check` is run below to hold
        # the spans themselves.
        import yaml
        doc = yaml.safe_load((HERE.parent / 'annotations'
                              / 'data-regions.yaml').read_text())
        names = [r["name"] for r in doc["regions"]]
        self.assertEqual(len(names), len(set(names)), "duplicate region name")
        self.assertIn("common-219c-ff-triples", names)
        triples = next(r for r in doc["regions"]
                       if r["name"] == "common-219c-ff-triples")
        self.assertEqual((triples["file_lo"], triples["file_hi"]),
                         (0x219C, 0x21B4))

    def test_no_register_status_names_this_tool(self):
        # Nothing here is about a register, so no `status:` can have moved on the
        # strength of a Python walk over a `bytes` object.
        registers = (HERE.parent / 'annotations' / 'registers.yaml').read_text()
        for token in ("bucket_c_unplaced", "bucket-c-unplaced", "unplaced"):
            self.assertNotIn(token, registers)

    def test_the_data_regions_yaml_is_read_and_not_rewritten(self):
        # `data_regions.py --check` re-derives every span from the image, so it
        # is the mode that would go red if this tool had written the file. Run
        # rather than asserted here: the assertion is that the mode still exits
        # 0, which is a fact about a command and not about this tool.
        result = subprocess.run(
            [sys.executable, str(HERE / 'data_regions.py'), "--check"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_code_map_table_still_matches_its_own_check(self):
        # The census this one is built on. If it moved, every column carried
        # forward here moved with it, and the drift belongs in its own tool's
        # failure rather than surfacing as a mystery in this one.
        result = subprocess.run(
            [sys.executable, str(HERE / 'bucket_c_codemap.py'), FIRMWARE,
             "--check"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RefusalTests(unittest.TestCase):
    """The refusals from the other side of `SystemExit`, and the CLI's own."""

    def setUp(self):
        self.d = image()

    def test_check_and_self_test_are_refused_together(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--check", "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--check and --self-test", result.stderr)

    def test_csv_and_for_offset_are_refused_together(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--csv", "--for-offset", "0x021C6"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--csv and --for-offset", result.stderr)

    def test_an_image_without_the_pd_marker_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "not-the-ec.bin"
            other.write_bytes(b"\x00" * 0x20040)
            result = subprocess.run(
                [sys.executable, TOOL, str(other), "--csv"],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("ITE8850-PD", result.stderr)

    def test_for_offset_reports_a_site_outside_the_population(self):
        # The labelled sites are the ones a reader is most likely to try, and
        # the message has to say *why* the row is absent rather than printing
        # an empty one.
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--for-offset", "0x055DC"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("common-055a8-be-words", result.stdout)

    def test_the_self_test_exits_zero_on_the_committed_image(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("self-test passed", result.stdout)

    def test_check_exits_zero_on_the_committed_image(self):
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE, "--check"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_plain_run_prints_the_base_rate_the_write_up_relies_on(self):
        # The report is what the write-up quotes, so the two figures it has to
        # carry -- the population and the grid share -- are printed by the tool
        # rather than recomputed by a reader.
        result = subprocess.run(
            [sys.executable, TOOL, FIRMWARE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f"## 1. The population: {len(census().unplaced())} site",
                      result.stdout)
        # The base rate the write-up quotes, so a reader who runs the tool gets
        # the figure beside the site it qualifies rather than only in prose.
        self.assertIn("sit on their nearest", result.stdout)
        # And the sentence that stops the table being read as a clearance.
        self.assertIn("Nothing here is a behavioural claim", result.stdout)


if __name__ == "__main__":
    unittest.main()