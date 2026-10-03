#!/usr/bin/env python3
"""That `fw_image_diff.py` attributes a difference to the right image.

`fw_image_diff.py --self-test` holds the same assertions as a run of its own;
this suite exists because a `--self-test` is a thing a person runs and this is
a thing `tools/run-tests.sh` collects. The committed image is read here rather
than a fixture, so these cases cannot pass against a stale copy of a file the
firmware work has since moved on from.

**The attribution is the whole point.** `docs/findings.md` §3a records a
register coming to be recorded as present in EC firmware that references it
zero times, because a file-wide count had added the main EC to the ITE8850-PD
image sharing the dump. So every case here is written as "this byte is counted
here and *not* there": a mutation in each region in turn, and then the pd-image
case again on its own, because a byte inside the second program being counted
toward the first is the exact mistake being guarded against.

**The refusals are tested as hard as the attribution**, for the reason this
repository keeps restating: a check that has quietly stopped rejecting anything
looks exactly like a check that is working. A short image is refused rather
than compared over the overlap, and the refusal names both sizes.

**What is deliberately not asserted.** No case says a difference in the charge
code would mean anything, and none is written against a recovered 2021 image,
because there is not one committed and obtaining it is a human step
(`docs/findings.md` §6). `registers.yaml` does not move on the strength of this
tool: nothing here observes a register's behaviour.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
TOOL = Path(__file__).with_name("fw_image_diff.py")
FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("fw_image_diff", TOOL)
fw_image_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fw_image_diff)

with open(FIRMWARE, "rb") as _fh:
    IMAGE = _fh.read()


def mutated_at(*offsets):
    data = bytearray(IMAGE)
    for off in offsets:
        data[off] ^= 0xFF
    return bytes(data)


def region_count(a, b, region):
    return next(r["differing"] for r in fw_image_diff.region_rows(a, b)
                if r["region"] == region)


class TestRegionAttribution(unittest.TestCase):
    """One flipped byte in each mapped region, counted in that region only."""

    def test_the_mutation_offsets_fall_in_the_regions_they_are_named_for(self):
        # The pairing is written out in the tool's own table; asserting it here
        # means a region boundary moving shows up as a failure here rather than
        # as a silently re-pointed mutation.
        for region, offset in fw_image_diff.SELF_TEST_MUTATIONS.items():
            with self.subTest(region=region):
                self.assertEqual(
                    fw_image_diff.region_of(offset, True)[0], region)

    def test_each_mutation_is_counted_in_its_own_region_and_no_other(self):
        for region, offset in fw_image_diff.SELF_TEST_MUTATIONS.items():
            with self.subTest(region=region):
                rows = fw_image_diff.region_rows(IMAGE, mutated_at(offset))
                touched = [r["region"] for r in rows if r["differing"]]
                self.assertEqual(touched, [region])

    def test_a_pd_image_byte_is_never_counted_in_the_main_ec(self):
        offset = fw_image_diff.SELF_TEST_MUTATIONS["pd-image"]
        other = mutated_at(offset)
        for region in fw_image_diff.FIRMWARE_REGIONS:
            if region == "pd-image":
                continue
            with self.subTest(region=region):
                self.assertEqual(region_count(IMAGE, other, region), 0)
        self.assertEqual(region_count(IMAGE, other, "pd-image"), 1)

    def test_the_first_and_last_differing_offsets_are_reported_in_file_space(self):
        offset = fw_image_diff.SELF_TEST_MUTATIONS["bank1"]
        row = next(r for r in fw_image_diff.region_rows(IMAGE, mutated_at(offset))
                   if r["region"] == "bank1")
        self.assertEqual((row["first"], row["last"]), (offset, offset))

    def test_an_identical_image_reports_nothing_anywhere(self):
        for row in fw_image_diff.region_rows(IMAGE, IMAGE):
            with self.subTest(region=row["region"], span=row["lo"]):
                self.assertEqual(row["differing"], 0)
                self.assertIsNone(row["first"])
                self.assertIsNone(row["last"])

    def test_the_regions_are_the_shared_table_not_a_local_copy(self):
        # A second, privately-edited region map would be a second answer to the
        # §3a question, which is what importing `REGIONS` exists to prevent.
        from trace_xdata_refs import REGIONS
        self.assertEqual([r["region"] for r in fw_image_diff.region_rows(IMAGE, IMAGE)],
                         [name for name, *_ in REGIONS])


class TestRefusals(unittest.TestCase):
    def _refusal(self, len_b):
        with self.assertRaises(SystemExit) as caught:
            fw_image_diff.check_sizes("old.bin", len(IMAGE), "new.bin", len_b)
        return str(caught.exception)

    def test_a_short_image_is_refused(self):
        self.assertIn("different sizes", self._refusal(len(IMAGE) - 1))

    def test_a_long_image_is_refused(self):
        self.assertIn("different sizes", self._refusal(len(IMAGE) + 1))

    def test_the_refusal_names_both_sizes(self):
        text = self._refusal(len(IMAGE) - 1)
        self.assertIn(str(len(IMAGE)), text)
        self.assertIn(str(len(IMAGE) - 1), text)

    def test_equal_sizes_are_not_refused(self):
        fw_image_diff.check_sizes("a", 100, "b", 100)  # returns, does not raise

    def test_a_missing_marker_labels_the_pd_region_unknown(self):
        off, _magic = fw_image_diff.PD_MARKER
        unmarked = bytearray(IMAGE)
        unmarked[off] ^= 0xFF
        self.assertFalse(fw_image_diff.pd_verified(bytes(unmarked)))
        self.assertEqual(fw_image_diff.region_of(0x20050, False)[0], "unknown")

    def test_region_rows_renames_the_row_when_told_the_marker_is_gone(self):
        # `verified=None` keeps the table's own name, which is what the
        # byte-attribution cases want; a boolean replaces it with
        # `region_of()`'s verdict.
        off, _magic = fw_image_diff.PD_MARKER
        unmarked = bytearray(IMAGE)
        unmarked[off] ^= 0xFF
        names = [r["region"] for r in
                 fw_image_diff.region_rows(IMAGE, bytes(unmarked), verified=False)]
        self.assertIn("unknown", names)
        self.assertNotIn("pd-image", names)
        kept = [r["region"] for r in
                fw_image_diff.region_rows(IMAGE, bytes(unmarked))]
        self.assertIn("pd-image", kept)

    def test_the_committed_image_carries_its_marker(self):
        self.assertTrue(fw_image_diff.pd_verified(IMAGE))


class TestReferenceCounts(unittest.TestCase):
    """The counts the tool re-runs on both images come from `scan_refs.py`."""

    def test_a_known_register_reads_the_same_way_through_both_tools(self):
        # 0x07A6 is the mode register §4h names. The number is `scan_refs.py`'s,
        # read through the same function, so this is one answer to one question
        # rather than a fixture copied into two places.
        import scan_refs
        counts = fw_image_diff.reference_counts([0x07A6], IMAGE)[0x07A6]
        self.assertEqual(counts, tuple(scan_refs.scan(IMAGE, True)[0x07A6][:3]))
        self.assertGreater(counts[1], 0)

    def test_the_ec_and_pd_columns_are_not_the_same_number(self):
        # If they were, the split this tool exists to preserve is not being
        # computed. 0x07D0's sites are PD-side in the committed image, which is
        # what §5's 2026-09-23 note about 0x07D0 records.
        total, ec, pd = fw_image_diff.reference_counts([0x07D0], IMAGE)[0x07D0]
        self.assertGreater(pd, 0)
        self.assertEqual(ec, 0)
        self.assertEqual(total, ec + pd)

    def test_an_unreferenced_address_is_zero_not_an_error(self):
        self.assertEqual(fw_image_diff.reference_counts([0x07B9], IMAGE)[0x07B9],
                         (0, 0, 0))


class TestFullRun(unittest.TestCase):
    """The CLI's own path, over files written for the run."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="fw_image_diff_suite_")
        cls.old = os.path.join(cls.scratch.name, "committed.bin")
        cls.new = os.path.join(cls.scratch.name, "mutated.bin")
        with open(cls.old, "wb") as fh:
            fh.write(IMAGE)
        with open(cls.new, "wb") as fh:
            fh.write(mutated_at(*fw_image_diff.SELF_TEST_MUTATIONS.values()))

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_the_report_carries_the_calibration_caveat(self):
        text = fw_image_diff.compare(self.old, self.old, [0x07A6])
        self.assertIn("'absent'", text)
        self.assertIn("not\nthat the two are equivalent", text)

    def test_identical_images_report_no_differing_bytes(self):
        self.assertIn("0 differing byte(s)",
                      fw_image_diff.compare(self.old, self.old, []))

    def test_a_mutation_in_each_region_shows_a_row_for_each_region(self):
        text = fw_image_diff.compare(self.old, self.new, [])
        for region in fw_image_diff.SELF_TEST_MUTATIONS:
            with self.subTest(region=region):
                self.assertIn(region, text)

    def test_the_addrs_table_names_both_sides(self):
        text = fw_image_diff.compare(self.old, self.new, [0x07A6])
        self.assertIn("old total/ec/pd", text)
        self.assertIn("0x07A6", text)

    def test_a_marker_less_image_is_labelled_unknown_in_the_printed_table(self):
        # Asserted on `compare()`'s text, not on `region_of()`. The dependency
        # already does this labelling, so an assertion on the dependency passes
        # even if `compare()` stopped consulting it -- which is what removing
        # the marker branch did: the tool stayed green while printing a row
        # labelled `pd-image` directly under a note saying `unknown`.
        stripped = os.path.join(self.scratch.name, "no-marker.bin")
        off, _magic = fw_image_diff.PD_MARKER
        unmarked = bytearray(IMAGE)
        unmarked[off] ^= 0xFF
        with open(stripped, "wb") as fh:
            fh.write(bytes(unmarked))
        text = fw_image_diff.compare(self.old, stripped, [])
        table = text.split("Regions", 1)[-1]
        self.assertIn("unknown", table)
        self.assertNotIn("pd-image", table)
        self.assertIn("no 'ITE8850-PD' marker", text)

    def test_an_intact_pair_still_calls_the_region_pd_image(self):
        text = fw_image_diff.compare(self.old, self.old, [])
        self.assertIn("pd-image", text.split("Regions", 1)[-1])

    def test_a_region_filter_narrows_the_rows(self):
        text = fw_image_diff.compare(self.old, self.new, [], only=["common"])
        self.assertIn("common", text)
        self.assertNotIn("bank1", text)

    def test_a_short_file_through_the_cli_is_an_error_not_a_report(self):
        short = os.path.join(self.scratch.name, "short.bin")
        with open(short, "wb") as fh:
            fh.write(IMAGE[:-1])
        done = subprocess.run(
            [sys.executable, str(TOOL), self.old, short],
            capture_output=True, text=True, cwd=str(REPO))
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("different sizes", done.stdout + done.stderr)
        self.assertNotIn("differing byte(s)", done.stdout)


class TestSelfTestEntryPoint(unittest.TestCase):
    def test_self_test_exits_zero(self):
        done = subprocess.run([sys.executable, str(TOOL), "--self-test"],
                              capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("FAIL", done.stdout)

    def test_one_argument_is_an_error(self):
        done = subprocess.run([sys.executable, str(TOOL), str(FIRMWARE)],
                              capture_output=True, text=True, cwd=str(REPO))
        self.assertNotEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
