#!/usr/bin/env python3
"""Offline checks for census_xdata_writers.py.

`--self-test` holds the r2 hand transcriptions, which is the oracle for the
store scan. What is here is the rest: the partition the tool's headline number
rests on, the two vocabularies, the join to the site table in both directions,
and `--check` driven in both directions -- a doctored cell fails and a **missing**
file fails rather than being created.

The store-scan cases build their own byte fixtures rather than pointing at the
firmware, so a case keeps testing what it was written to test if the bytes
around some address in the image change. That is `test_walk_branch_arms.py`'s
stated reason and the split `test_walk_budget_census.py` and
`test_trace_xdata_refs.py` use: which instructions come back is this file's
question, which guard fired is theirs.

**Nothing here asserts a count of the tree.** The one figure the tool reports
that a re-cut could move -- the arm walk's unattributed stores, which is the
reason the writer count is not closed -- is read out of the committed arms
table and compared against the tool's own reading of the same table, so the
two cannot disagree. The writer and store counts are held as *relationships*
(the partition sums; `store_count` equals the number of renders in
`store_runtime`), which is the `CLAUDE.md` rule that a test asserting a census
is a value every merge has to edit.
"""
import csv
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

HERE = Path(__file__).parent
# census_xdata_writers imports check_register_counts, disasm8051,
# trace_xdata_refs and walk_flow_follow by bare module name, the way
# register_ref_table.py does, so the tool directory has to be on the path before
# it is loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'census_xdata_writers', HERE / 'census_xdata_writers.py')
cxw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cxw)

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')
WRITERS = cxw.WRITERS_CSV
ADDRESS = 0x0751
# The one address both committed tables are about, spelled the way the tables
# spell it. Passed as a string because that is the form the join compares, and
# a case that handed the int would exercise a comparison no caller makes.
WANT = f"0x{ADDRESS:04X}"

_IMAGE = None


def image() -> bytes:
    global _IMAGE
    if _IMAGE is None:
        with open(FIRMWARE, "rb") as f:
            _IMAGE = f.read()
    return _IMAGE


def summary():
    """The census over the committed image, memoised.

    The reconciliation problems are asserted in their own case rather than
    swallowed here, so this one cannot be the reason they go unnoticed -- but
    they are not raised either, because `writer_rows` reports them as data and
    a case that wants them asks for them.
    """
    return cxw.census(image(), ADDRESS, True)[0]


def rows_of(text: str):
    return list(csv.DictReader(io.StringIO(text)))


def scan(*raw: bytes):
    """`stores_in()` over hand-laid bytes, decoded by the tool's own decoder."""
    return cxw.stores_in(cxw.decode_fixture(b"".join(raw)))


class StoreScanTests(unittest.TestCase):
    """The blind-store / read-modify-write rule, on bytes rather than addresses.

    Each case is arranged so a scan that answered one shape to everything would
    fail it: the fixtures are not all modifies, and the two that are not
    differ from each other.
    """

    def test_read_modify_write_carries_the_mask(self):
        self.assertEqual(scan(b"\xe0\x54\xbf\xf0"),
                         [(0x03, cxw.RMW, "anl a,#0xbf")])

    def test_store_with_no_load_is_blind(self):
        got = scan(b"\xf0")
        self.assertEqual(got, [(0x00, cxw.BLIND, cxw.NO_SOURCE)])

    def test_load_then_store_is_unmodified_not_blind(self):
        # The distinction the two cells above exist for: a load with nothing
        # between it and the store is a modify of what was read, not a blind
        # overwrite, and a scan that answered "blind" to both would pass the
        # first of them.
        self.assertEqual(scan(b"\xe0\xf0"), [(0x01, cxw.RMW, cxw.UNMODIFIED)])

    def test_a_store_does_not_count_as_a_load_for_the_next_one(self):
        got = scan(b"\xe0\xf0\x44\x80\xf0")
        self.assertEqual([(s, c) for _, s, c in got],
                         [(cxw.RMW, cxw.UNMODIFIED), (cxw.BLIND, cxw.NO_SOURCE)])

    def test_one_load_two_stores_masks_each_against_its_own_store(self):
        got = scan(b"\xe0\x44\x80\xf0\x44\x10\xf0")
        self.assertEqual([c for _, _, c in got], ["orl a,#0x80", cxw.NO_SOURCE])

    def test_a_movx_between_two_stores_clears_the_pending_load(self):
        # A read of the byte, a store, then a read, then a store: the second
        # store's mask is the instruction between *it* and its own read.
        got = scan(b"\xe0\xf0\xe0\x54\x10\xf0")
        self.assertEqual([c for _, _, c in got], [cxw.UNMODIFIED, "anl a,#0x10"])

    def test_a_dptr_rebuild_is_rendered_rather_than_folded_away(self):
        # `walk_why()` ends a window at a reload, so this shape does not arise
        # in the image -- and that is the point. The store is of a byte the load
        # never touched, and a scan that dropped the rebuild out of the mask
        # would report a modify of the wrong byte.
        got = scan(b"\xe0\x90\x07\x51\xf0")
        self.assertEqual(got, [(0x04, cxw.RMW, "mov dptr,#0x0751")])

    def test_no_store_is_no_store(self):
        self.assertEqual(scan(b"\x90\x07\x51\xe0\x30\xe1\x15"), [])

    def test_store_offsets_are_the_instruction_offsets(self):
        got = scan(b"\x90\x07\x51\xe0\x54\xef\xf0\xe0\x44\x80\xf0")
        self.assertEqual([i for i, _, _ in got], [0x06, 0x0A])

    def test_the_shipped_fixtures_agree_with_the_tool(self):
        # The self-test's own table, run through the same path, so a fixture
        # edited to match a broken scan fails here too. This is the case that
        # keeps --self-test from being the only thing holding the scan.
        for label, raw, expected in cxw.SELF_TEST_STORES:
            with self.subTest(label):
                got = cxw.stores_in(
                    cxw.decode_fixture(bytes(int(t, 16) for t in raw.split())))
                self.assertEqual(got, expected)


class VocabularyTests(unittest.TestCase):
    """Both vocabularies are closed, and asserted by name.

    A count would not do it: a fourth status that is a synonym for one of the
    three keeps the count right and lets `--check` go green on it.
    """

    def test_status_vocabulary_is_exactly_three_named_values(self):
        self.assertEqual(set(cxw.STATUSES),
                         {cxw.FOUND, cxw.TRUNCATED, cxw.UNRESOLVED})

    def test_condition_vocabulary_is_exactly_the_four_the_issue_named(self):
        self.assertEqual(set(cxw.CONDITIONS),
                         {cxw.BOOT_DEFAULT, cxw.TEMPERATURE_GATE,
                          cxw.MODE_DECODE, cxw.HOST_WRITE_THROUGH})

    def test_every_empty_bucket_that_can_be_empty_carries_a_reason(self):
        # `host-write-through` is expected to come back with no row, and a
        # bucket reported empty with no reason is indistinguishable from a
        # bucket nobody looked for.
        self.assertIn(cxw.HOST_WRITE_THROUGH, cxw.BUCKET_REASONS)
        for condition in cxw.CONDITIONS:
            reason = cxw.BUCKET_REASONS.get(condition, "")
            self.assertTrue(reason == "" or "found by this method" in reason
                            or "no site" in reason,
                            f"{condition}: {reason!r} states neither a reason "
                            "nor the calibration the empty bucket needs")

    def test_no_source_and_unmodified_are_different_cells(self):
        # "the accumulator held an unrelated value" and "the accumulator held
        # the byte unmodified" are different statements about what a store can
        # destroy, so they cannot share a spelling.
        self.assertNotEqual(cxw.NO_SOURCE, cxw.UNMODIFIED)

    def test_the_sequence_separator_is_not_the_site_table_instruction_one(self):
        # ` ; ` means "next instruction" in a `window` cell; reusing it inside
        # a `mask` cell would read as a disassembly.
        self.assertNotIn(";", cxw.SEQUENCE)
        self.assertIn("then", cxw.SEQUENCE)

    def test_a_mask_for_a_blind_store_is_the_no_source_cell(self):
        for row in rows_of(_table()):
            if row["access_shape"] == cxw.BLIND:
                self.assertEqual(row["mask"], cxw.NO_SOURCE)


class CsvShapeTests(unittest.TestCase):
    """The committed table's own cells, read back off disk."""

    def setUp(self):
        with open(WRITERS, newline="") as f:
            self.text = f.read()
        self.rows = rows_of(self.text)

    def test_the_header_is_the_tools_own(self):
        self.assertEqual(self.text.split("\r\n")[0].split(","),
                         cxw.CSV_COLUMNS)

    def test_every_row_is_about_the_address_the_table_names(self):
        for row in self.rows:
            self.assertEqual(row["addr"], WANT)

    def test_every_row_carries_a_condition_with_evidence(self):
        for row in self.rows:
            with self.subTest(row["site_file_offset"]):
                self.assertIn(row["condition"], cxw.CONDITIONS)
                self.assertTrue(row["condition_evidence"].strip(),
                                "a hand-filled condition with nothing behind it")

    def test_no_row_claims_the_empty_bucket(self):
        # `host-write-through` is in the vocabulary and deliberately has no
        # row; a row appearing under it is a claim with no instruction in the
        # image behind it, and the tool's own run says so.
        self.assertNotIn(cxw.HOST_WRITE_THROUGH,
                         {r["condition"] for r in self.rows})

    def test_every_derived_cell_is_in_the_vocabulary(self):
        for row in self.rows:
            self.assertIn(row["access_shape"], (cxw.BLIND, cxw.RMW))
            self.assertIn(row["status"], cxw.STATUSES)

    def test_store_count_equals_the_number_of_renders_in_store_runtime(self):
        # A self-consistency invariant rather than a count of the tree: it
        # holds whatever the census finds and catches a row whose two store
        # columns have drifted apart.
        for row in self.rows:
            with self.subTest(row["site_file_offset"]):
                self.assertEqual(int(row["store_count"]),
                                 len(row["store_runtime"].split(cxw.SEQUENCE)))

    def test_mask_has_one_cell_per_store(self):
        for row in self.rows:
            with self.subTest(row["site_file_offset"]):
                self.assertEqual(int(row["store_count"]),
                                 len(row["mask"].split(cxw.SEQUENCE)))

    def test_every_evidence_cell_names_an_address(self):
        # The evidence column's job is to point at the branch the condition was
        # read from. One that does not is a condition with a category name and
        # nothing a reader can go and check.
        for row in self.rows:
            self.assertRegex(row["condition_evidence"], r"0x[0-9A-Fa-f]{4}")


class DerivationTests(unittest.TestCase):
    """The committed table against a fresh derivation, and the partition.

    Nothing here asserts how many writers there are. A census that moved -- a
    re-cut of `trace_xdata_refs`, a firmware change -- must be a red run, and
    the way to get that without a hand-kept number is to re-derive and diff.
    """

    def setUp(self):
        self.summary = summary()
        self.committed = cxw.read_committed(WRITERS)
        self.generated, problems = cxw.csv_table(self.summary["rows"],
                                                 self.committed, notes=False)
        self.problems = problems

    def test_the_committed_table_is_what_this_run_derives(self):
        self.assertEqual(self.problems, [])
        with open(WRITERS, newline="") as f:
            self.assertEqual(f.read(), self.generated)

    def test_the_census_is_not_vacuously_empty(self):
        # The diff above passes on a tool that returned nothing and wrote a
        # header. §14b's shape: a discovery of zero is itself a failure.
        self.assertTrue(self.summary["rows"])
        self.assertTrue(self.summary["stores"])
        self.assertTrue(self.committed)

    def test_writers_and_read_only_sites_partition_the_site_population(self):
        writers = {s["offset"] for s in self.summary["writers"]}
        read_only = {s["offset"] for s in self.summary["read_only"]}
        self.assertEqual(writers & read_only, set())
        self.assertEqual(len(writers) + len(read_only),
                         len(self.summary["all_sites"]))

    def test_the_partition_covers_every_site_the_sites_table_commits(self):
        # The two populations have to be the same set of sites, not merely the
        # same size: a method that silently stopped resolving a site would
        # keep both numbers and change what they mean.
        committed = {f"0x{s['offset']:05X}" for s in self.summary["all_sites"]}
        with open(cxw.SITES_CSV, newline="") as f:
            on_disk = {r["file_offset"] for r in csv.DictReader(f)
                       if r["addr"] == WANT}
        self.assertEqual(committed, on_disk)

    def test_the_shapes_partition_the_store_instructions(self):
        # `access_shape` is a two-value vocabulary over the stores, so the
        # store total has to equal the two buckets summed -- and a site may not
        # carry both, which is what "disjoint" is here for.
        tally = {}
        for site in self.summary["writers"]:
            shapes = {s for _, s, _ in site["stores"]}
            self.assertLessEqual(len(shapes), 1,
                                 f"{site['runtime']:#06x}: a site with both "
                                 "shapes has no single access_shape")
            if not shapes:
                continue
            shape = shapes.pop()
            tally[shape] = tally.get(shape, 0) + len(site["stores"])
        self.assertEqual(sum(tally.values()), self.summary["stores"])
        self.assertEqual(set(tally), {cxw.BLIND, cxw.RMW})

    def test_no_reconciliation_problem(self):
        _, problems = cxw.census(image(), ADDRESS, True)
        self.assertEqual(problems, [])

    def test_a_site_the_classification_calls_a_writer_always_has_a_status(self):
        for site in self.summary["all_sites"]:
            if site["writer"]:
                self.assertIn(site["status"], cxw.STATUSES)
            else:
                self.assertIsNone(site["status"])

    def test_a_truncated_row_is_exactly_a_budget_terminator(self):
        # `window-truncated` has to mean what its name says, or it is a
        # qualifier on a finding rather than a fact about one.
        for site in self.summary["writers"]:
            if site["status"] == cxw.TRUNCATED:
                self.assertEqual(site["terminator"],
                                 cxw.budget_end(cxw.WINDOW))

    def test_the_followed_sites_keep_their_weaker_claim_visible(self):
        # Two of the ten are resolved only by following a branch past the site.
        # That is a weaker claim than a window that settles where it sits, and
        # the two must never be silently equal.
        followed = {s["offset"] for s in self.summary["followed"]}
        self.assertTrue(followed)
        for site in self.summary["all_sites"]:
            if site["offset"] in followed:
                self.assertEqual(site["linear"], cxw.NO_MOVX)
                self.assertNotEqual(site["direction"], cxw.NO_MOVX)
            elif site["followed"]:
                self.fail("a followed site with no linear gap")

    def test_the_arms_figure_is_read_from_the_committed_table(self):
        gap, err = cxw.arms_gap(WANT)
        self.assertIsNone(err)
        self.assertEqual(gap, cxw.SELF_TEST_ARMS)

    def test_the_gap_is_reported_and_not_derived_from_nothing(self):
        # The figure is the reason the count is not closed, so it has to be a
        # number read off a committed table and not a constant in a docstring
        # that nothing would notice moving.
        self.assertTrue(cxw.ARMS_CSV.endswith("manual-fan-ctrl-0751-arms.csv"))
        buf = io.StringIO()
        with redirect_stderr(buf):
            cxw.report(ADDRESS, self.summary)
        out = buf.getvalue()
        self.assertIn(str(cxw.SELF_TEST_ARMS[1]), out)
        self.assertIn("#34", out)


def _table() -> str:
    """The committed table, as text, for the cases that want the cells."""
    with open(WRITERS, newline="") as f:
        return f.read()


class FollowedSiteTests(unittest.TestCase):
    """The branch-followed sites, and the invariant the re-walk rests on.

    Two of the ten `0x0751` writers are resolved only by following a branch
    past the site, so the weaker claim has to be visible rather than folded in
    -- and the re-walk of each followed segment depends on `follow_site()`
    having resolved the very start it reports, which is a property of that
    function and not of this one.
    """

    def test_a_block_start_the_region_cannot_reach_is_refused_not_defaulted(self):
        # A silent `or off` would re-scan the anchor, which holds no `movx` for
        # exactly the sites this path exists for, and report a site that has
        # stores as one that has none. So the disagreement is raised, and the
        # message names both functions.
        original = cxw.offset_for_runtime

        def refuse(runtime, region):
            if runtime >= 0xA000:
                return None
            return original(runtime, region)

        cxw.offset_for_runtime = refuse
        self.addCleanup(setattr, cxw, "offset_for_runtime", original)
        with self.assertRaises(ValueError) as caught:
            cxw.site_record(image(), ADDRESS, 0x0ABE8, True)
        self.assertIn("follow_site()", str(caught.exception))
        self.assertIn("no longer agree", str(caught.exception))

    def test_a_refused_segment_does_not_silently_become_a_read_only_site(self):
        # The same refusal seen from the census rather than from one record: a
        # dropped writer is a smaller table, which is the failure the
        # reconciliations exist to turn into a red run.
        original = cxw.offset_for_runtime
        cxw.offset_for_runtime = lambda runtime, region: (
            None if runtime >= 0xA000 else original(runtime, region))
        self.addCleanup(setattr, cxw, "offset_for_runtime", original)
        with self.assertRaises(ValueError):
            cxw.census(image(), ADDRESS, True)

    def test_the_two_followed_sites_are_the_ones_whose_window_holds_no_movx(self):
        # A site the follow did not have to touch is not `followed`, or the
        # flag stops saying which sites rest on a weaker claim.
        for site in summary()["all_sites"]:
            if site["followed"]:
                self.assertEqual(site["linear"], cxw.NO_MOVX)
                self.assertTrue(site["stores"])
            else:
                self.assertNotEqual(site["linear"], cxw.NO_MOVX)


class SiteJoinTests(unittest.TestCase):
    """`check_sites()` in both directions, against scratch copies.

    The direction cell the committed site table carries is `classify()` over the
    bytes the table was cut with, so re-deriving it has to give the same
    string. A tool measuring a different walk would pass every assertion about
    its own table and be describing another population.
    """

    def setUp(self):
        self.all_sites = summary()["all_sites"]
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _sites_copy(self, mutate=None) -> str:
        """A copy of the committed site table, optionally doctored.

        Written with `csv.DictWriter` rather than by editing text, so the copy
        parses back through the same reader the check uses and a case cannot
        pass on a quoting accident.
        """
        with open(cxw.SITES_CSV, newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = reader.fieldnames, [r for r in reader
                                               if r["addr"] == WANT]
        if mutate:
            rows = mutate(rows)
        path = os.path.join(self.tmp, "sites.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        return path

    def test_the_committed_table_needs_no_correction(self):
        problems, _ = cxw.check_sites(self.all_sites, ADDRESS)
        self.assertEqual(problems, [])

    def test_a_doctored_access_cell_is_reported(self):
        def doctor(rows):
            rows[0]["access"] = "write x1"
            return rows
        problems, _ = cxw.check_sites(self.all_sites, ADDRESS,
                                      self._sites_copy(doctor))
        self.assertTrue(any("commits" in p for p in problems), problems)

    def test_a_site_the_table_records_and_sites_for_does_not_find(self):
        # A *derived* site is missing, not a table row: the two directions are
        # different failures and only one of them is a row count, so the derived
        # side is what gets shortened here.
        problems, _ = cxw.check_sites(self.all_sites[:-1], ADDRESS)
        self.assertTrue(any("no longer finds" in p for p in problems), problems)

    def test_a_site_this_run_finds_and_the_table_does_not_record(self):
        problems, _ = cxw.check_sites(self.all_sites, ADDRESS,
                                      self._sites_copy(lambda rows: rows[:-1]))
        self.assertTrue(any("does not record" in p for p in problems), problems)

    def test_a_table_row_for_an_address_the_run_never_reached(self):
        def doctor(rows):
            return rows + [dict(rows[0], file_offset="0x0DEAD")]
        problems, _ = cxw.check_sites(self.all_sites, ADDRESS,
                                      self._sites_copy(doctor))
        self.assertTrue(any("no longer finds" in p for p in problems), problems)

    def test_a_missing_site_table_is_reported_not_silently_empty(self):
        # A silently empty read is a check that reports nothing and exits 0.
        problems, _ = cxw.check_sites(self.all_sites, ADDRESS,
                                      os.path.join(self.tmp, "absent.csv"))
        self.assertEqual(len(problems), 1)
        self.assertIn("absent.csv", problems[0])


class CheckBothDirectionsTests(unittest.TestCase):
    """`--check` driven as a subprocess, both ways it can fail.

    The direction that matters most is the missing file: a `--check` that
    writes the table it is checking has stopped checking it, and a green run
    would then be a statement about the tool's own output.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / "census_xdata_writers.py"), *args],
            capture_output=True, text=True, cwd=str(HERE))

    def _copy(self, name="writers.csv") -> str:
        path = os.path.join(self.tmp, name)
        shutil.copyfile(WRITERS, path)
        return path

    def _rewrite(self, path: str, mutate) -> None:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = reader.fieldnames, list(reader)
        rows = mutate(rows)
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    def test_check_on_the_committed_table_exits_zero(self):
        got = self.run_tool("--check", WRITERS)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn("byte for byte", got.stdout)

    def test_check_with_no_path_uses_the_committed_table(self):
        got = self.run_tool("--check")
        self.assertEqual(got.returncode, 0, got.stderr)

    def test_a_doctored_mechanical_cell_fails(self):
        path = self._copy()
        # Two different columns at once, so a check that only watched one of
        # them could not pass.
        def doctor(rows):
            rows[0]["access_shape"] = cxw.BLIND
            rows[1]["site_runtime"] = "0x0000"
            return rows
        self._rewrite(path, doctor)
        got = self.run_tool("--check", path)
        self.assertEqual(got.returncode, 1)
        self.assertIn("differs", got.stderr)

    def test_a_legal_hand_filled_edit_is_carried_through_and_the_check_passes(self):
        # The arrangement, stated as a case because it is the surprising half:
        # `condition` and `condition_evidence` are prose read off a listing, so
        # `--check` carries them rather than regenerating them, and a corrected
        # condition on a row whose bytes did not move is *not* drift. What holds
        # them is the closed vocabulary, in the two cases below -- so this is
        # the reason those two exist and not belt and braces.
        path = self._copy()
        self._rewrite(path, lambda rows: [dict(
            rows[0], condition=cxw.BOOT_DEFAULT,
            condition_evidence="0x897D subb a,#0x46 / jnc 0x899D on 0x043E")]
            + rows[1:])
        got = self.run_tool("--check", path)
        self.assertEqual(got.returncode, 0, got.stderr)
        self.assertIn("byte for byte", got.stdout)

    def test_a_hand_filled_cell_outside_the_vocabulary_fails_the_check(self):
        # So the arrangement is not a hole: a value nothing can classify is a
        # red run, which is what stops "hand-filled" from becoming "unheld".
        path = self._copy()
        self._rewrite(path, lambda rows: [dict(
            rows[0], condition="thermal-drop")] + rows[1:])
        got = self.run_tool("--check", path)
        self.assertEqual(got.returncode, 1)
        self.assertIn("thermal-drop", got.stderr)

    def test_a_hand_filled_cell_with_no_evidence_fails_the_check(self):
        path = self._copy()
        self._rewrite(path, lambda rows: [dict(
            rows[0], condition=cxw.MODE_DECODE, condition_evidence="")]
            + rows[1:])
        got = self.run_tool("--check", path)
        self.assertEqual(got.returncode, 1)
        self.assertIn("condition_evidence", got.stderr)

    def test_a_condition_outside_the_vocabulary_is_refused(self):
        problems, _ = cxw.validate_rows(
            [{"site_file_offset": "0x0898A", "status": cxw.FOUND,
              "access_shape": cxw.RMW}],
            [{"site_file_offset": "0x0898A", "condition": "because-i-said-so",
              "condition_evidence": "0x897D subb a,#0x46"}])
        self.assertTrue(any("is not one of" in p for p in problems), problems)

    def test_a_condition_with_no_evidence_is_refused(self):
        problems, _ = cxw.validate_rows(
            [{"site_file_offset": "0x0898A", "status": cxw.FOUND,
              "access_shape": cxw.RMW}],
            [{"site_file_offset": "0x0898A", "condition": cxw.MODE_DECODE,
              "condition_evidence": ""}])
        self.assertTrue(any("no condition_evidence" in p for p in problems),
                        problems)

    def test_evidence_with_no_condition_is_refused(self):
        problems, _ = cxw.validate_rows(
            [{"site_file_offset": "0x0898A", "status": cxw.FOUND,
              "access_shape": cxw.RMW}],
            [{"site_file_offset": "0x0898A", "condition": "",
              "condition_evidence": "0x897D subb a,#0x46"}])
        self.assertTrue(any("with no condition" in p for p in problems), problems)

    def test_a_committed_row_this_run_derives_no_site_for_is_reported(self):
        # The direction a plain diff would miss: the table and the image no
        # longer describe the same set of sites, which a byte-for-byte diff
        # reports as one changed line among others.
        with open(WRITERS, newline="") as f:
            rows = list(csv.DictReader(f))
        extra = dict(rows[0], site_file_offset="0x0DEAD")
        problems, _ = cxw.validate_rows(
            [{"site_file_offset": r["site_file_offset"], "status": cxw.FOUND,
              "access_shape": cxw.RMW} for r in rows], rows + [extra])
        self.assertTrue(any("no writer site" in p for p in problems), problems)

    def test_a_missing_table_fails_and_is_not_created(self):
        path = os.path.join(self.tmp, "absent.csv")
        got = self.run_tool("--check", path)
        self.assertEqual(got.returncode, 1)
        self.assertFalse(os.path.exists(path),
                         "--check wrote the file it was checking")

    def test_a_table_with_the_wrong_header_is_refused(self):
        path = os.path.join(self.tmp, "wrong.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["addr", "site_runtime"])
            w.writerow(["0x0751", "0x898A"])
        got = self.run_tool("--check", path)
        self.assertEqual(got.returncode, 1)
        self.assertIn("not a census_xdata_writers table", got.stderr)

    def test_an_address_given_to_check_is_refused(self):
        got = self.run_tool(FIRMWARE, ADDRESS_HEX, "--check", WRITERS)
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("takes the address from the committed table", got.stderr)

    def test_no_address_and_no_check_is_refused(self):
        got = self.run_tool()
        self.assertNotEqual(got.returncode, 0)
        self.assertIn("an address", got.stderr)

    def test_an_image_without_the_pd_marker_is_refused(self):
        path = os.path.join(self.tmp, "not-ec.bin")
        with open(path, "wb") as f:
            f.write(b"\x00" * 0x21000)
        got = self.run_tool(path, ADDRESS_HEX)
        self.assertEqual(got.returncode, 1)
        self.assertIn("ITE8850-PD", got.stderr)


ADDRESS_HEX = f"0x{ADDRESS:04X}"


class UnresolvedStatusTests(unittest.TestCase):
    """`unresolved` is reachable, not a decorative state.

    No `0x0751` site in the image is one -- every window the classification
    calls a writer holds a `movx @dptr,a` the scan can place -- so a case has to
    build the record by hand. `row_for()` is pure for exactly that reason: a
    status nothing can construct is a status nothing can check, and this is the
    case that constructs one.
    """

    def _unresolved_site(self) -> dict:
        return {"offset": 0x0DEAD, "region": "bank0", "runtime": 0x9EAD,
                "linear": "write x1", "direction": "write x1",
                "followed": False, "writer": True, "stores": [],
                "status": cxw.UNRESOLVED, "terminator": "flow opcode"}

    def test_an_unresolved_row_names_the_reason_in_the_mask_cell(self):
        row = cxw.row_for(ADDRESS, self._unresolved_site(), True)
        self.assertEqual(row["status"], cxw.UNRESOLVED)
        self.assertIn("no movx @dptr,a", row["mask"])
        self.assertIn("write x1", row["mask"])

    def test_an_unresolved_row_reports_zero_stores_rather_than_hiding_it(self):
        # A `store_count` of 0 beside a direction that says "write" is the
        # contradiction the status exists to name, so it stays in the row
        # instead of being dropped.
        row = cxw.row_for(ADDRESS, self._unresolved_site(), True)
        self.assertEqual(row["store_count"], "0")
        self.assertEqual(row["store_runtime"], "")

    def test_an_unresolved_row_survives_the_vocabulary_check(self):
        # The status is in the closed set, so the row is a legal one -- the
        # check has to accept it, or a real unresolved site could never be
        # committed.
        text, problems = cxw.csv_table(
            [cxw.row_for(ADDRESS, self._unresolved_site(), True)], [],
            notes=False)
        self.assertEqual(problems, [])
        self.assertIn(cxw.UNRESOLVED, text)

    def test_a_found_row_keeps_its_mask_and_leaves_the_reason_out(self):
        site = dict(self._unresolved_site(),
                    stores=[(0x0DEB0, cxw.RMW, "anl a,#0xbf")],
                    status=cxw.FOUND)
        row = cxw.row_for(ADDRESS, site, True)
        self.assertEqual(row["mask"], "anl a,#0xbf")
        self.assertEqual(row["access_shape"], cxw.RMW)
        self.assertEqual(row["store_count"], "1")


class SelfTestTests(unittest.TestCase):
    """`--self-test` is a real gate, not a decoration.

    It is what the prepared `docs/ci/agent-gates-0751-writer-census.patch` runs,
    so a change that breaks it has to be visible here as well -- and it is the
    only thing in the file that grades the store scan against a second
    disassembler.
    """

    def test_self_test_exits_zero_on_the_committed_image(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = cxw.self_test(FIRMWARE)
        self.assertEqual(rc, 0, buf.getvalue())

    def test_every_fixture_is_transcribed_bytes_not_an_address(self):
        for label, raw, _ in cxw.SELF_TEST_STORES:
            with self.subTest(label):
                self.assertRegex(raw, r"^([0-9a-f]{2} )+[0-9a-f]{2}$")

    def test_the_arms_figure_is_a_pair_and_not_a_bare_number(self):
        # The write-up quotes both halves, and half of a gap is not a gap.
        self.assertEqual(len(cxw.SELF_TEST_ARMS), 2)
        self.assertGreater(cxw.SELF_TEST_ARMS[1], 0)


if __name__ == "__main__":
    unittest.main()
