#!/usr/bin/env python3
"""That `cc_version_diff.py` refuses the encrypted trees, and diffs a clean pair.

`cc_version_diff.py --self-test` holds the same assertions as a run of its own;
this suite exists because a `--self-check` is a thing a person runs and this is
a thing `tools/run-tests.sh` collects. The refusal cases are run against the
committed trees, so this suite fails if the trees stop carrying markers -- which
would mean the decompiles had been regenerated decrypted, and the refusal's
reason would have changed underneath it.

**What the refusal is for, and why it is tested hardest here.** The two older
committed trees yield no EC call sites at all, because their method bodies are
ciphertext. A diff that reported that as "the older version wrote no register"
would be the `docs/findings.md` §4c failure wearing a diff's clothes. So the
suite asserts three separate things a reader would act on: that the run exits
non-zero, that it prints no per-address table at all, and that its message says
why in terms that name the markers rather than the versions.

**The marker count is cross-checked against the other tool**, `t1wr_callers.py`,
over the same tree. Both read the same vocabulary (`DECOMPILER_MARKERS` is
imported, not restated) but they walk independently, so agreement is a
property of the data rather than of one shared loop -- and a disagreement would
mean one of the two is reading a different tree than it thinks.

**No case here asserts what a version does.** The decrypted 3.1.39.0 tree's
register table is asserted to be *readable*, not to have any particular content;
`docs/findings.md` §4k is where the 3.1.39.0 behaviour is written down.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
TOOL = Path(__file__).with_name("cc_version_diff.py")
DECOMPILED = REPO / "windows" / "decompiled"

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("cc_version_diff", TOOL)
cc_version_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc_version_diff)

TREE_316 = str(DECOMPILED / "v3.1.6.0")
TREE_3918 = str(DECOMPILED / "v3.9.18.0")
TREE_3139 = str(DECOMPILED / "v3.1.39.0" / "GCUService")
VENDOR_ACPIDRV = str(REPO / "vendor" / "control-center-3.9.18.0" / "ACPIDriver")


class TestRefusalOnEncryptedTrees(unittest.TestCase):
    """The committed older trees are what the refusal exists for."""

    @classmethod
    def setUpClass(cls):
        cls.text, cls.status = cc_version_diff.diff(TREE_316, TREE_3918)

    def test_a_run_over_two_encrypted_trees_exits_non_zero(self):
        self.assertNotEqual(self.status, 0)

    def test_a_refused_run_prints_no_diff(self):
        # The whole point: not a diff with a caveat at the bottom, no diff.
        for heading in ("EC register accesses", "BatteryProtection2 methods"):
            self.assertNotIn(heading, self.text)

    def test_the_refusal_names_the_markers_not_the_versions(self):
        self.assertIn("decompiler markers", self.text)
        self.assertIn("BatteryProtection2.cs", self.text)
        self.assertIn("marker(s)", self.text)

    def test_the_refusal_says_a_zero_is_not_an_answer(self):
        self.assertIn("is not an answer", self.text)

    def test_the_refusal_does_not_claim_a_version_wrote_nothing(self):
        # The refusal has to *name* the sentence it exists to prevent, so a
        # bare substring check would fail on a correct message. What must not
        # happen is that phrase appearing unquoted as the tool's own finding.
        self.assertIn('"this version wrote no register"', self.text)
        for line in self.text.splitlines():
            if "wrote no register" in line:
                self.assertIn('"', line, f"unquoted: {line!r}")

    def test_the_refusal_is_symmetric_in_its_two_arguments(self):
        _text, status = cc_version_diff.diff(TREE_3918, TREE_316)
        self.assertNotEqual(status, 0)

    def test_a_clean_tree_against_an_encrypted_one_is_also_refused(self):
        # The obvious half-use: diffing the readable tree against the
        # unreadable one is the exact comparison issue #83 wants, and it is
        # the one that would produce a plausible-looking one-sided answer.
        _text, status = cc_version_diff.diff(TREE_316, TREE_3139)
        self.assertNotEqual(status, 0)


class TestMarkerCensus(unittest.TestCase):
    """The counts the refusal prints, against two independent walks."""

    def test_316_carries_markers_in_exactly_one_file(self):
        total, files = cc_version_diff.marker_census(TREE_316)
        self.assertEqual(list(files), ["BatteryProtection2.cs"])
        self.assertEqual(total, files["BatteryProtection2.cs"])

    def test_the_count_agrees_with_t1wr_callers_own_walk(self):
        import t1wr_callers
        marker = t1wr_callers.DECOMPILER_MARKERS[0]
        for tree in (TREE_316, TREE_3918):
            with self.subTest(tree=os.path.basename(tree)):
                with open(os.path.join(tree, "BatteryProtection2.cs"),
                          encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                mine, _files = cc_version_diff.marker_census(tree)
                theirs = t1wr_callers.decompiler_census(tree)
                self.assertEqual(mine, sum(theirs.values()))
                self.assertEqual(theirs["BatteryProtection2.cs"],
                                 text.count(marker))

    def test_the_decrypted_tree_carries_none(self):
        # If this ever fails, the reason the refusal prints has changed and the
        # assertions above are asserting the wrong thing.
        total, files = cc_version_diff.marker_census(TREE_3139)
        self.assertEqual((total, files), (0, {}))

    def test_the_census_of_a_missing_tree_is_empty(self):
        # The census alone cannot tell a missing tree from a clean one, which is
        # exactly why `check_tree()` runs first. Asserted so the interaction
        # stays a decision rather than becoming an accident.
        total, files = cc_version_diff.marker_census("/no/such/tree")
        self.assertEqual((total, files), (0, {}))


class TestMissingTrees(unittest.TestCase):
    """A path that is not a tree must not produce a clean-looking diff.

    Issue #83's own next step is to *create* `windows/decompiled/v<version>/`,
    so a not-yet-existing path is the expected state before the first recovery
    rather than a typo. Left unhandled it produces the exact answer this tool
    exists to withhold: every address and every method one-sided, exit 0.
    """

    def _refuses(self, *args):
        with self.assertRaises(SystemExit) as caught:
            cc_version_diff.diff(*args)
        return str(caught.exception)

    def test_a_missing_tree_is_refused_by_the_run(self):
        text = self._refuses("/no/such/tree", TREE_3139)
        self.assertIn("is not a directory", text)

    def test_a_file_given_where_a_tree_belongs_is_refused(self):
        path = os.path.join(TREE_316, "BatteryProtection2.cs")
        self.assertIn("is not a directory", self._refuses(path, TREE_3139))

    def test_a_directory_of_binaries_is_refused(self):
        text = self._refuses(str(VENDOR_ACPIDRV), TREE_3139)
        self.assertIn("holds no .cs files", text)

    def test_the_refusal_explains_what_to_do_instead(self):
        text = self._refuses("/no/such/tree", TREE_3139)
        self.assertIn("dotnet_dump.py", text)

    def test_the_missing_tree_is_checked_on_either_side(self):
        self.assertIn("is not a directory",
                      self._refuses(TREE_3139, "/no/such/tree"))

    def test_a_real_tree_is_not_refused_by_check_tree(self):
        cc_version_diff.check_tree(TREE_316)  # returns, does not raise

    def test_the_cli_reports_it_without_a_traceback(self):
        done = subprocess.run(
            [sys.executable, str(TOOL), "/no/such/tree", TREE_3139],
            capture_output=True, text=True, cwd=str(REPO))
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("Traceback", done.stderr)
        self.assertNotIn("EC register accesses", done.stdout)


class TestCleanDiff(unittest.TestCase):
    """A pair with no markers in it must actually diff, or the refusal is
    a tool that only ever refuses."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix="cc_version_diff_suite_")
        cls.a = cc_version_diff._clean_tree(cls.scratch.name, "A")
        cls.b = cc_version_diff._clean_tree(cls.scratch.name, "B")
        cls.text, cls.status = cc_version_diff.diff(cls.a, cls.b)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    def test_a_clean_pair_is_not_refused(self):
        self.assertEqual(self.status, 0)
        self.assertIn("EC register accesses", self.text)

    def test_an_address_one_side_only_appears_as_a_difference(self):
        self.assertIn("0x07B9", self.text)

    def test_an_address_both_sides_touch_identically_is_omitted(self):
        self.assertNotIn("0x07A6", self.text)

    def test_a_one_sided_method_is_marked_on_its_own_line(self):
        line = cc_version_diff._line_for(self.text, "SetBatteryChargingLimit_Up")
        self.assertIsNotNone(line)
        self.assertIn("*", line)

    def test_a_shared_method_is_not_marked(self):
        line = cc_version_diff._line_for(self.text, "SetHealthProtectionHigh")
        self.assertIsNotNone(line)
        self.assertNotIn("*", line)

    def test_a_tree_diffed_against_itself_reports_nothing_differing(self):
        text, status = cc_version_diff.diff(self.a, self.a)
        self.assertEqual(status, 0)
        self.assertIn("0 differing", text)

    def test_an_addr_filter_narrows_the_table(self):
        text, _status = cc_version_diff.diff(self.a, self.b, want_addr="0x07b9")
        self.assertIn("0x07B9", text)
        self.assertNotIn("0x07A6", text)


class TestSummaryAdapter(unittest.TestCase):
    """`summary()` reads `ec_callsites.py`'s own output, so check it does."""

    def test_the_decrypted_tree_reads_through_to_the_real_scan(self):
        rows = cc_version_diff.summary(TREE_3139)
        self.assertTrue(rows, "the committed decrypted tree produced no rows")
        self.assertIn("0x07A6", rows)
        self.assertGreater(rows["0x07A6"]["writes"], 0)

    def test_the_charge_methods_are_found_by_class_name_not_by_path(self):
        # The tree nests the class under a per-namespace directory; finding it
        # there is what stops the method-set half from being empty on every
        # version whose layout differs from the last one.
        methods = cc_version_diff.charge_methods(TREE_3139)
        self.assertIn("SetHealthProtectionHigh", methods)
        self.assertIn("SetBatteryChargingLimit_Up", methods)

    def test_the_encrypted_tree_yields_no_addresses(self):
        # The fact the refusal rests on, asserted directly rather than only
        # through the refusal's exit status.
        self.assertEqual(cc_version_diff.summary(TREE_316), {})
        self.assertEqual(cc_version_diff.summary(TREE_3918), {})


class TestEntryPoint(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args],
                              capture_output=True, text=True, cwd=str(REPO))

    def test_self_test_exits_zero(self):
        done = self._run("--self-test")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("FAIL", done.stdout)

    def test_the_refusal_reaches_the_shell_as_a_non_zero_status(self):
        done = self._run("windows/decompiled/v3.1.6.0",
                         "windows/decompiled/v3.9.18.0")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("decompiler markers", done.stdout)
        self.assertNotIn("EC register accesses", done.stdout)

    def test_one_argument_is_an_error(self):
        self.assertNotEqual(self._run("windows/decompiled/v3.1.6.0").returncode, 0)

    def test_the_decimal_addr_form_is_accepted(self):
        # The scan's rows are `0xNNNN`; a caller reading an address off a
        # capture as a decimal gets the same row rather than an empty table.
        done = self._run("windows/decompiled/v3.1.39.0/GCUService",
                         "windows/decompiled/v3.1.39.0/GCUService", "--addr", "1958")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("0x07A6", done.stdout)


if __name__ == "__main__":
    unittest.main()
