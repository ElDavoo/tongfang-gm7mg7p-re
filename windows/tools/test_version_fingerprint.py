#!/usr/bin/env python3
"""What `version_fingerprint.py` recovers, and what it refuses to conclude.

`version_fingerprint.py --self-check` holds the same assertions as a run of its
own; this suite exists because a `--self-check` is a thing a person runs and this
is a thing `tools/run-tests.sh` collects. The committed-vendor cases run the
tool's own entry point as a subprocess, so what is tested here is the code path
a user gets, including its exit status.

**Both halves, per this repository's standing argument.** The recoveries are
what the tool exists for and are the figures issue #83's write-up rests on. The
refusals are the half that matters more: a fingerprint tool that reports a
number where it has none is worse than one that reports nothing, because the
number is what a reader would act on. So a `wLength` that overruns its buffer, a
resource section that is not there, a file that is not a PE, and a zero
`TimeDateStamp` are each asserted to produce no version rather than a plausible
one.

**Nothing here is graded against the tool's own output.** The version figures
are the ones `windows/decompiled/v3.1.39.0/README.md` records as prose about
the shipped file, and the installer versions are the release numbers in the
vendor directory names. A tool that graded itself would pass whatever it
produced.
"""
import importlib.util
import io
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
TOOL = Path(__file__).with_name("version_fingerprint.py")

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("version_fingerprint", TOOL)
version_fingerprint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_fingerprint)

VENDOR = REPO / "vendor"
GCU = "control-center-3.1.39.0/MyControlCenter/GCUService.exe"
SETUP_316 = "control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe"
SETUP_3918 = "control-center-3.9.18.0/setup.exe"
ACPIDRV = "control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys"

# `dnfile` is the one optional dependency `version_fingerprint.py` has, and it
# is what reads a .NET `Assembly` table (see that module's docstring). The
# assertions that need it are skipped rather than failed when it is absent, so
# that a reader without it is told the check did not run instead of being shown
# a missing package as a wrong version. CI installs it, so there these run.
HAVE_DNFILE = importlib.util.find_spec("dnfile") is not None
needs_dnfile = unittest.skipUnless(HAVE_DNFILE, "dnfile not installed")


class TestCommittedVendorArtifacts(unittest.TestCase):
    """The figures issue #83's write-up cites, read back off the real files."""

    @classmethod
    def setUpClass(cls):
        cls.gcu = version_fingerprint.fingerprint(str(VENDOR / GCU))
        cls.old = version_fingerprint.fingerprint(str(VENDOR / SETUP_316))
        cls.new = version_fingerprint.fingerprint(str(VENDOR / SETUP_3918))
        cls.sys = version_fingerprint.fingerprint(str(VENDOR / ACPIDRV))

    def test_installed_service_reports_the_assembly_version_not_the_release(self):
        # `windows/decompiled/v3.1.39.0/README.md` records this as prose: "the
        # executable's own `FileVersion` is `1.0.2.70`", for a service whose
        # `DisplayVersion` is 3.1.39.0.
        self.assertEqual(self.gcu["fixed_file_version"], "1.0.2.70")

    @needs_dnfile
    def test_the_dotnet_assembly_table_agrees_with_the_version_resource(self):
        # The `Assembly` half of the case above, which is a different field
        # from the version resource and needs `dnfile` to read. Split from it so
        # that its absence skips one assertion rather than the FileVersion one.
        self.assertEqual(self.gcu["assembly_version"], "1.0.2.70")
        self.assertEqual(self.gcu["assembly_name"], "GCUService")

    def test_nothing_in_the_service_pe_names_the_control_center_release(self):
        # The finding the tool exists for. Asserted field by field rather than
        # by the absence of a substring, because "nothing anywhere in the file"
        # is not something a fingerprint of five fields can establish -- what
        # it establishes is that none of the fields a reader would consult for
        # a version carries the release.
        for key in version_fingerprint.CSV_FIELDS:
            if key == "path":
                continue  # the repository names the directory after the release
            self.assertNotIn("3.1.39.0", str(self.gcu[key]),
                             f"{key} carries the release number")

    def test_installers_do_carry_the_release(self):
        # The other half, and the actionable one: a recovered installer is
        # self-dating even though the tree it installs is not.
        self.assertEqual(self.old["fixed_file_version"], "3.1.6.0")
        self.assertEqual(self.new["fixed_file_version"], "3.9.18.0")

    def test_both_installers_share_one_link_stamp(self):
        # The limit on `TimeDateStamp`: two installers wrapping two different
        # releases carry the same one, so the stamp is not the release date of
        # either. What makes it so is measured; *why* they share it is not.
        self.assertEqual(self.old["timestamp"], self.new["timestamp"])
        self.assertNotEqual(self.old["timestamp"], "")
        self.assertNotEqual(self.old["sha256"], self.new["sha256"])

    def test_a_binary_with_no_version_resource_reports_none(self):
        # ACPIDriver.sys is byte-identical across 3.1.6.0 and 3.9.18.0 (see
        # `windows/decompiled/v3.1.6.0/README.md`), so "no version here" is the
        # correct answer for it and must not become an inferred one.
        self.assertEqual(self.sys["fixed_file_version"], "")
        self.assertEqual(self.sys["_version_resource"], "absent from the file")
        self.assertEqual(self.sys["assembly_version"], "")

    @needs_dnfile
    def test_a_native_driver_is_reported_as_not_a_dotnet_assembly(self):
        # Why `assembly_version` is empty above, which `dnfile` is what can
        # tell: "not a .NET assembly" and "not read" are different answers and
        # the field says which. Without `dnfile` it says only the second.
        self.assertIn("not a .NET assembly", self.sys["dotnet"])

    def test_every_row_reports_the_size_of_the_file_it_read(self):
        for row, rel in ((self.gcu, GCU), (self.old, SETUP_316),
                         (self.new, SETUP_3918), (self.sys, ACPIDRV)):
            with self.subTest(rel=rel):
                self.assertEqual(len(row["sha256"]), 64)
                self.assertEqual(row["size"], (VENDOR / rel).stat().st_size)

    def test_installer_string_padding_is_stripped(self):
        # Inno Setup right-pads its version fields; left in, two identical
        # versions would compare unequal on a string comparison.
        self.assertEqual(self.old["FileVersion"], "3.1.6.0")
        self.assertNotIn("  ", self.old["LegalCopyright"])


class TestVersionResourceParsing(unittest.TestCase):
    """The parser, on blobs built here, so a failure points at the parse."""

    def test_reads_both_fixed_versions_apart(self):
        fv, pv, _ = version_fingerprint.parse_version_info(
            version_fingerprint._synthetic_version_blob())
        self.assertEqual(fv, "3.4.5.6")
        self.assertEqual(pv, "3.4.5.7")

    def test_reads_strings_through_both_container_levels(self):
        _, _, strings = version_fingerprint.parse_version_info(
            version_fingerprint._synthetic_version_blob())
        self.assertEqual(strings.get("ProductName"), "Synthetic")
        self.assertEqual(strings.get("CompanyName"), "Nobody")

    def test_a_truncated_blob_reads_as_nothing(self):
        blob = version_fingerprint._synthetic_version_blob()
        for cut in (4, 8, len(blob) // 2, len(blob) - 1):
            with self.subTest(cut=cut):
                fv, pv, strings = version_fingerprint.parse_version_info(blob[:cut])
                self.assertEqual((fv, pv), ("", ""))
                self.assertEqual(strings, {})

    def test_a_length_field_that_overruns_the_buffer_is_not_trusted(self):
        # The failure this guards is reading past the end and getting a
        # plausible version out of whatever followed, which is what a
        # bounds-free version parser does on a truncated or hostile file.
        blob = bytearray(version_fingerprint._synthetic_version_blob())
        struct.pack_into("<H", blob, 0, 0xFFFF)
        fv, pv, _ = version_fingerprint.parse_version_info(bytes(blob))
        self.assertEqual((fv, pv), ("", ""))

    def test_a_fixed_file_info_with_the_wrong_signature_is_not_read(self):
        blob = bytearray(version_fingerprint._synthetic_version_blob())
        pos = version_fingerprint._pad4(
            6 + len("VS_VERSION_INFO") * 2 + 2)
        struct.pack_into("<I", blob, pos, 0xDEADBEEF)
        fv, _, _ = version_fingerprint.parse_version_info(bytes(blob))
        self.assertEqual(fv, "")

    def test_each_fixed_version_field_is_read_from_its_own_bytes(self):
        # Four different version numbers, one per field. A parser that read the
        # file version for both, or the product version for both, or the halves
        # in the wrong order, is caught by having no two of them equal.
        def quad(q):
            return struct.pack("<II", (q[0] << 16) | q[1], (q[2] << 16) | q[3])
        fixed = struct.pack("<II", 0xFEEF04BD, 0x00010000)
        fixed += quad((1, 2, 3, 4)) + quad((5, 6, 7, 8))
        fixed += b"\0" * (52 - len(fixed))
        fv, pv, _ = version_fingerprint.parse_version_info(_build(fixed))
        self.assertEqual((fv, pv), ("1.2.3.4", "5.6.7.8"))


def _build(fixed: bytes) -> bytes:
    """VS_VERSION_INFO around `fixed`, with two strings two records deep.

    Lets a test choose the two version numbers, which the tool's own synthetic
    blob fixes at one pair. A parser that read the file version where the
    product version belongs, or vice versa, passes on a blob where the two
    agree -- so the pair here has to differ.
    """
    strings = b"".join(
        version_fingerprint._version_record(k, v.encode("utf-16le") + b"\0\0")
        for k, v in (("ProductName", "Synthetic"), ("CompanyName", "Nobody")))
    strings = version_fingerprint._version_record("000004b0", children=strings)
    strings = version_fingerprint._version_record("StringFileInfo", children=strings)
    return version_fingerprint._version_record("VS_VERSION_INFO", fixed,
                                               children=strings, wtype=0)


class TestTimestamp(unittest.TestCase):
    def test_zero_is_not_1970(self):
        self.assertEqual(version_fingerprint.timestamp_utc(0), "not recorded (0)")

    def test_a_real_stamp_converts(self):
        self.assertEqual(version_fingerprint.timestamp_utc(0x61528305),
                         "2021-09-28 02:50:45+00:00")

    def test_a_stamp_from_the_other_side_of_the_epoch_reads_as_a_date(self):
        # Not a plausible year for a vendor build, and the tool says the year
        # rather than rejecting it: a wrong stamp is a fact about the file, and
        # a reader seeing it is better served than by a refusal that could be
        # mistaken for "this file carries no date".
        self.assertTrue(
            version_fingerprint.timestamp_utc(0xFFFFFFFF).startswith("2106-"))


class TestNonPeInputs(unittest.TestCase):
    def test_a_file_that_is_not_a_pe_is_reported_not_raised(self):
        with tempfile.NamedTemporaryFile(suffix=".bin") as fh:
            fh.write(b"this is not a portable executable\n" * 40)
            fh.flush()
            row = version_fingerprint.fingerprint(fh.name)
        self.assertEqual(row["machine"], "")
        self.assertIn("not a PE", row["pe"])
        self.assertEqual(len(row["sha256"]), 64)

    def test_a_truncated_pe_header_is_not_raised(self):
        with tempfile.NamedTemporaryFile(suffix=".exe") as fh:
            fh.write(b"MZ" + b"\0" * 30)
            fh.flush()
            row = version_fingerprint.fingerprint(fh.name)
        self.assertEqual(row["machine"], "")

    def test_a_pe_with_no_resource_directory_reports_no_version(self):
        # A minimal but well-formed PE32+ with an empty section table.
        pe = bytearray(b"\0" * 0x200)
        pe[0:2] = b"MZ"
        struct.pack_into("<I", pe, 0x3C, 0x80)
        pe[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HHIIIHH", pe, 0x84, 0x8664, 0, 0, 0, 0, 0xF0, 0x0022)
        struct.pack_into("<H", pe, 0x84 + 20, 0x020B)
        with tempfile.NamedTemporaryFile(suffix=".exe") as fh:
            fh.write(bytes(pe))
            fh.flush()
            row = version_fingerprint.fingerprint(fh.name)
        self.assertEqual(row["machine"], "x86-64")
        self.assertEqual(row["format"], "PE32+")
        self.assertEqual(row["_version_resource"], "absent from the file")
        self.assertEqual(row["fixed_file_version"], "")


class TestEntryPoint(unittest.TestCase):
    """The CLI, as a subprocess, including the exit status."""

    def _run(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args],
                              capture_output=True, text=True, cwd=str(REPO))

    def test_self_check_exits_zero(self):
        done = self._run("--self-check")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertNotIn("FAIL", done.stdout)

    @needs_dnfile
    def test_self_check_is_not_green_by_construction(self):
        # A check that has quietly stopped rejecting anything looks exactly
        # like a check that is working, so the mutation is put in and the run
        # is required to go red. The `dnfile` branch is the one that could
        # swallow this, so the run is also required not to have skipped
        # anything: with the dependency installed the assertion is hard again.
        with patch.object(version_fingerprint, "ORACLE_ASSEMBLY_VERSION", "9.9.9.9"):
            done = io.StringIO()
            with patch("sys.stdout", done):
                rc = version_fingerprint.self_check(str(REPO))
        self.assertEqual(rc, 1)
        self.assertIn("FAIL", done.getvalue())
        self.assertNotIn("skip", done.getvalue())

    def test_self_check_says_which_assertion_a_missing_dnfile_cost_it(self):
        # `dnfile` is optional, so the `Assembly` assertion cannot run without
        # it. Two things have to hold there, and they pull opposite ways: the
        # run must not report a *failure* (the table was not read, so no version
        # came back wrong), and it must not pass silently either (a reader who
        # sees green has to be able to find out that one check did not run).
        # `sys.modules[name] = None` is what makes the tool's local
        # `import dnfile` raise, which is the absence being simulated.
        done = io.StringIO()
        with patch.dict(sys.modules, {"dnfile": None}):
            with patch("sys.stdout", done):
                rc = version_fingerprint.self_check(str(REPO))
        out = done.getvalue()
        self.assertEqual(rc, 0, out)
        self.assertNotIn("FAIL", out)
        self.assertIn("dnfile not installed", out)
        # The assertions that do not need it still ran, rather than the whole
        # check having gone quiet with the dependency.
        self.assertIn("GCUService.exe FileVersion is the README's 1.0.2.70", out)

    def test_no_arguments_is_an_error(self):
        self.assertNotEqual(self._run().returncode, 0)

    def test_a_missing_file_is_an_error_not_a_traceback(self):
        done = self._run("no/such/file.exe")
        self.assertNotEqual(done.returncode, 0)
        self.assertNotIn("Traceback", done.stderr)

    def test_csv_output_carries_one_row_per_file(self):
        done = self._run("--csv", f"vendor/{GCU}", f"vendor/{ACPIDRV}")
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stdout.strip().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("fixed_file_version", lines[0])
        self.assertIn("1.0.2.70", lines[1])

    def test_csv_and_pretty_output_agree_on_the_same_file(self):
        pretty = self._run(f"vendor/{GCU}").stdout
        row = version_fingerprint.fingerprint(str(VENDOR / GCU))
        self.assertIn(row["sha256"], pretty)
        self.assertIn(row["assembly_version"], pretty)


if __name__ == "__main__":
    unittest.main()
