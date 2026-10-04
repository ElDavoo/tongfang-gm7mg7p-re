#!/usr/bin/env python3
"""Offline checks for pd_stride_families.py: committed files only.

The tool's own `--self-test` pins its decode against bytes and against the two
committed CSVs it reads. What stands in for the tool here is everything that
decision does not cover: that the committed output is regenerable rather than
merely present, that the CSV's shape is the one the annotation quotes, that the
vocabularies are the ones the annotation quotes them by, and that a run leaves
the three baseline CSVs this work reads byte-identical.

Those are properties, not figures. Nothing here counts a suite, a test, a row
of the repository's own text or an entry of the committed CSV -- those move on
every landing merge, which is the failure CLAUDE.md's "no totals" rule exists
to prevent, and a count in a test assertion is the same line every other open
branch has to edit. Where a number is genuinely load-bearing it is the address
of a byte or the value of a firmware-derived constant, both of which no change
to this repository can move.

Three failure shapes are covered, each asserted as itself rather than as a
non-failure, because a check that only asserted "no exception" would go green
on a tool that had started raising nothing at all:

  * the committed CSV drifting from what the firmware produces (drift, not
    absence -- the file exists and is wrong);
  * a column being renamed, dropped or reordered, which is what makes the
    annotation's tables and the docstring's vocabulary stop matching the file;
  * a null cell becoming an empty one, which is the shape that reads as "there
    is no consumer here" instead of "not found by this method".

Refusals are covered too, on the one argument `--sites` takes: an address that
is not in the PD runtime range is refused by name rather than raising an
IndexError from whichever line read first.
"""
import csv
import io
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
# pd_stride_families inserts the tool directory on sys.path itself, but the
# import has to be given a spec from the file's own path so this suite does not
# depend on the runner's working directory. The pattern
# test_check_site_census.py uses.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    "pd_stride_families", HERE / "pd_stride_families.py")
psf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(psf)

FIRMWARE = str(HERE.parent / "firmware" / "GMxMGxx_11.800")
SITES_CSV = HERE.parent / "annotations" / "pd-stride-family-sites.csv"

# The baselines this change reads and must not write. Each is named with the
# mode that regenerates it, so a failure says which one moved.
BASELINES = (
    ("pd-base-strides.csv", ["--strides-csv", "all"]),
    ("pd-index-accesses.csv", ["--accesses-csv", "all"]),
    ("pd-access-strides.csv", ["--access-strides-csv", "all"]),
)

_IMAGE = None


def image():
    global _IMAGE
    if _IMAGE is None:
        with open(FIRMWARE, "rb") as f:
            _IMAGE = f.read()
    return _IMAGE


def run(*args):
    return subprocess.run(
        [sys.executable, str(HERE / "pd_stride_families.py"), FIRMWARE, *args],
        capture_output=True, text=True, check=False)


class ToolOutput(unittest.TestCase):
    """What the tool produces on the committed image, once for the class."""

    @classmethod
    def setUpClass(cls):
        cls.rows = psf.family_rows(image())
        cls.text = psf.csv_text(cls.rows)

    def test_every_mode_exits_zero(self):
        for args in ([], ["--families"], ["--csv"],
                     ["--sites", "0x8077", "0xCC5B", "0x2F0B"]):
            with self.subTest(mode=args or "default"):
                self.assertEqual(run(*args).returncode, 0)

    def test_no_mode_is_an_error(self):
        # The tool prints the per-site table when no mode is named, so an
        # invocation with nothing to do is a report and not a usage error.
        self.assertEqual(run().returncode, 0)


class CommittedCsv(unittest.TestCase):
    """The committed file is regenerable, not merely present."""

    @classmethod
    def setUpClass(cls):
        cls.committed = SITES_CSV.read_text(encoding="utf-8")
        cls.fresh = run("--csv").stdout

    def test_regenerates_byte_for_byte(self):
        self.assertEqual(self.committed, self.fresh,
                         "ec/annotations/pd-stride-family-sites.csv does not "
                         "match what the committed firmware produces")

    def test_header_is_this_tool_header_in_order(self):
        header = self.committed.splitlines()[0]
        self.assertEqual(header, ",".join(psf.FIELDS))

    def test_sorted_lexicographically_in_header_order(self):
        rows = list(csv.DictReader(io.StringIO(self.committed)))
        keys = [tuple(r[f] for f in psf.FIELDS) for r in rows]
        self.assertEqual(keys, sorted(keys),
                         "rows are not in the sort order §8.3 of "
                         "pd-index-geometry.md requires")

    def test_round_trips_through_dictreader_and_dictwriter(self):
        # Read the committed file, write it back, and require the same bytes.
        # A truncated or re-quoted table would survive a naive row-by-row zip
        # against itself, so the round trip is over the text.
        parsed = list(csv.DictReader(io.StringIO(self.committed)))
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=psf.FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(parsed)
        self.assertEqual(buf.getvalue(), self.committed)
        self.assertEqual(len(parsed), len(psf.family_rows(image())))

    def test_one_row_per_contributing_site(self):
        # A property of the decode, not a count of the table: every row names a
        # site the whole-image `MOV DPTR` scan found, and every such site for
        # the three families appears exactly once.
        keys = [r["site_runtime"] for r in rows_of(self.committed)]
        self.assertEqual(len(keys), len(set(keys)))
        expected = {f"0x{s['runtime']:04X}" for s in psf.base_sites(
            image(), psf.WHOLE_IMAGE)
            if set(psf.STRIDE_RE.findall(" ".join(
                psf.effective_terms(s["terms"])))) & family_bare()}
        self.assertEqual(set(keys), expected)


def rows_of(text):
    return list(csv.DictReader(io.StringIO(text)))


def family_bare():
    """The families as the bare hex `STRIDE_RE` matches, which drops the `0x`.

    The tool holds them with the prefix because that is the form the committed
    CSVs print; the regex that finds a stride in a term yields the other one.
    Keeping the conversion here rather than in the tool is what lets both hold.
    """
    return {f[2:] for f in psf.FAMILIES}


class Vocabulary(unittest.TestCase):
    """The cell values are the ones the annotation and docstring quote.

    A vocabulary that drifts from the document is how a document ends up
    quoting a label no row carries, which is a claim no check would otherwise
    notice.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = rows_of(SITES_CSV.read_text(encoding="utf-8"))

    def test_only_declared_arithmetic_classes(self):
        self.assertLessEqual({r["arithmetic"] for r in self.rows},
                             {psf.LOW8_TRUNCATED, psf.FULL_PRODUCT})

    def test_only_declared_base_sources(self):
        self.assertLessEqual({r["base_source"] for r in self.rows},
                             {psf.REBASED, psf.SITE_IMMEDIATE})

    def test_only_declared_site_classes(self):
        self.assertLessEqual({r["site_class"] for r in self.rows},
                             {psf.CODE_SITE, psf.FRAMING_CANDIDATE})

    def test_only_declared_index_sources(self):
        self.assertLessEqual(
            {r["index_source"] for r in self.rows},
            {psf.INDEX_FROM_FRAME, psf.INDEX_FROM_REGISTER, psf.INDEX_FROM_MOVX,
             psf.INDEX_CLOBBERED, psf.INDEX_NOT_NAMED, psf.INDEX_NOT_REACHED})

    def test_only_declared_strides(self):
        self.assertLessEqual({r["stride"] for r in self.rows}, set(psf.FAMILIES))

    def test_arithmetic_agrees_with_the_term_it_was_read_from(self):
        for r in self.rows:
            with self.subTest(site=r["site_runtime"]):
                want = (psf.LOW8_TRUNCATED if "low8(" in r["index_terms"]
                        else psf.FULL_PRODUCT)
                self.assertEqual(r["arithmetic"], want)

    def test_base_source_agrees_with_the_base_it_names(self):
        for r in self.rows:
            with self.subTest(site=r["site_runtime"]):
                rebased = r["base_source"] == psf.REBASED
                self.assertEqual(rebased,
                                 r["effective_base"] != r["mov_dptr_immediate"])

    def test_framing_candidates_reach_no_helper(self):
        # The generalisation the docstring makes about the framing candidates
        # -- that they are the sites whose chain reaches nothing -- is only true
        # if the label and the helpers cell are held to each other, which is
        # what this is. It is a property, so it holds whichever sites carry the
        # label rather than naming two addresses as the answer.
        for r in self.rows:
            if r["site_class"] == psf.FRAMING_CANDIDATE:
                self.assertEqual(r["helpers"], psf.NOT_FOUND)
            else:
                self.assertNotEqual(r["helpers"], psf.NOT_FOUND)

    def test_every_stop_names_an_address(self):
        for r in self.rows:
            with self.subTest(site=r["site_runtime"]):
                self.assertTrue(r["chain_stop"])
                self.assertRegex(r["stop_runtime"], r"^0x[0-9A-F]{4}$")
                self.assertRegex(r["stop_file"], r"^0x[0-9A-F]{5}$")


class CalibratedNulls(unittest.TestCase):
    """Every unresolved cell is a token, and an empty cell is the failure.

    CLAUDE.md's calibration rule reads a static scan's zero as "not found by
    this method" and never as "absent", and an empty CSV cell is how a reader
    takes it as absent instead.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = rows_of(SITES_CSV.read_text(encoding="utf-8"))

    def test_no_cell_is_empty(self):
        for r in self.rows:
            empty = sorted(k for k, v in r.items() if v == "")
            self.assertEqual(empty, [], f"{r['site_runtime']} leaves "
                                        f"{', '.join(empty)} empty")

    def test_columns_that_can_be_unresolved_carry_a_token(self):
        token_columns = ("helpers", "owning_function", "access_row_kind",
                         "access_status", "consumer_runtime", "consumer_file",
                         "direction", "access_id", "index_source")
        for r in self.rows:
            for column in token_columns:
                with self.subTest(site=r["site_runtime"], column=column):
                    self.assertTrue(r[column])

    def test_unjoined_access_cells_all_read_the_same_way(self):
        # A row with no access join must not read as though a direction were
        # established, which is what leaving `direction` empty would say.
        for r in self.rows:
            if r["access_id"] == psf.NOT_FOUND:
                self.assertEqual(r["access_status"], psf.NOT_FOUND)
                self.assertEqual(r["consumer_runtime"], psf.NOT_FOUND)
                self.assertEqual(r["direction"], psf.UNRESOLVED_DIRECTION)

    def test_a_joined_row_carries_the_committed_census_own_vocabulary(self):
        with open(HERE.parent / "annotations" / "pd-index-accesses.csv",
                  encoding="utf-8") as f:
            access = {r["access_id"]: r for r in csv.DictReader(f)}
        for r in self.rows:
            if r["access_id"] == psf.NOT_FOUND:
                continue
            with self.subTest(site=r["site_runtime"]):
                source = access[r["access_id"]]
                self.assertEqual(r["access_row_kind"], source["row_kind"])
                self.assertEqual(r["access_status"], source["status"])
                self.assertEqual(r["access_id"], source["access_id"])

    def test_the_census_joins_nothing_for_the_two_families_it_never_covered(self):
        # Every `0x67` and `0x04` site is a `mov dptr,#imm` followed by
        # `lcall 0x10BC`, so the shape is §8's `direct-handoff`; the gap is the
        # helper. `immediate_templates()` keeps only `=`-prefixed rebasing
        # terms and `0x10BC`'s own term is `{a}×{b}`, and `access_entries()`'s
        # `reaches_template()` bails on its second instruction `add a,0x82`
        # (`0x25`), which `access_load()` does not model — so `0x10BC` is not
        # in §8's `entries`. That gap is the reason this work exists, so it is
        # asserted as a property of the join rather than left as prose: a future
        # census that does cover them is an improvement this assertion should be
        # updated to allow, not a regression.
        for r in self.rows:
            if r["stride"] in (psf.FAMILIES[1], psf.FAMILIES[2]):
                self.assertEqual(r["access_id"], psf.NOT_FOUND)


class BaselinesUntouched(unittest.TestCase):
    """A run of this tool writes nothing the three baselines own."""

    def test_baselines_are_byte_identical_after_a_run(self):
        before = {name: (HERE.parent / "annotations" / name).read_bytes()
                  for name, _ in BASELINES}
        self.assertEqual(run("--csv").returncode, 0)
        self.assertEqual(run("--families").returncode, 0)
        for name, _ in BASELINES:
            with self.subTest(csv=name):
                self.assertEqual(
                    (HERE.parent / "annotations" / name).read_bytes(),
                    before[name],
                    f"ec/annotations/{name} moved during a run of this tool")

    def test_the_tool_regenerates_the_baselines_it_reads(self):
        # Cross-check, not a rewrite: the tool must agree with the committed
        # stride census on every family, or --self-test's first assertion is
        # checking something the committed file already contradicts.
        self.assertEqual(psf._cross_check(psf.family_rows(image())), [])

    def test_self_test_exits_zero(self):
        self.assertEqual(run("--self-test").returncode, 0)


class Refusals(unittest.TestCase):
    """The one argument `--sites` takes, and what it does with a bad one."""

    def test_an_address_outside_the_pd_range_is_refused_not_raised(self):
        proc = run("--sites", "0x10000")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("pd-image", (proc.stdout + proc.stderr).lower())

    def test_a_site_that_resolves_nothing_is_named_not_guessed(self):
        proc = run("--sites", "0x0000")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("by this method", proc.stdout)


if __name__ == "__main__":
    unittest.main()
