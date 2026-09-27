#!/usr/bin/env python3
"""Checks on the checker for issue #10's prepared DMI entry.

`tools/check_dmi_descriptor.py` is the thing that decides whether
`linux/patches/gm7mg7p-dmi-entry/` may claim eight feature bits for this board
rather than one. Its previous attempt at this work shipped a rule that accepted
any plausible `UNIWILL_FEATURE_*` constant, so an invented name written into
both the map and a patch passed every check in the repository -- and a
reviewer called that unfalsifiable, correctly, and closed the PR.

A rule that cannot fail is the failure mode worth a suite, so this one pins the
refusals rather than the happy path. Each case mutates one committed input and
asserts that `--check` goes red and says something specific. Every mutation
happens in a `tempfile` copy; nothing here writes to the repository, because
the map and the patch are the artifacts a human submits.

Three things this deliberately does not do. It does not compile the patched
driver -- there is no kernel headers tree on the runner, and
`linux/nix/uniwill-laptop.nix` is the human's build path. It does not fetch
anything: the committed `upstream-excerpt.txt` is the evidence, and
`linux/patches/gm7mg7p-dmi-entry/fetch-upstream.sh` is what re-derives it, on a
machine with egress. And it does not assert that the eight bits are right on
hardware, because nothing in this repository can know that.
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import check_dmi_descriptor as checker  # noqa: E402

ENTRY = REPO / "linux" / "patches" / "gm7mg7p-dmi-entry"
MAP = ENTRY / "feature-map.csv"
EXCERPT = ENTRY / "upstream-excerpt.txt"
PATCH = ENTRY / "uniwill-acpi-dm-gm7mg7p.patch"
PR = ENTRY / "PR_DESCRIPTION.md"
REGISTERS = REPO / "ec" / "annotations" / "registers.yaml"
BASE_COMMIT = REPO / "linux" / "patches" / "BASE_COMMIT"
NIX = REPO / "linux" / "nix" / "uniwill-laptop.nix"


@contextmanager
def patched_map(mutate):
    """A copy of the map with `mutate` applied, so a refusal can be provoked.

    The point of going through the real file rather than calling the rules with
    a dict is that the CSV round-trip is part of what is being checked: a row
    whose quoting is wrong parses into a different map, and a suite that fed
    the checker a hand-built dict would never see it.
    """
    tmp = Path(tempfile.mkdtemp()) / "feature-map.csv"
    try:
        tmp.write_text(mutate(MAP.read_text()))
        yield tmp
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def run_check(map_path=MAP):
    """`--check` as a subprocess, so the exit status under test is the real one."""
    return subprocess.run(
        [sys.executable, str(HERE / "check_dmi_descriptor.py"),
         "--check", "--map", str(map_path)],
        capture_output=True, text=True)


def map_rows():
    """The committed map's rows, with the file closed.

    Every read goes through here rather than a bare `MAP.open()`: a leaked
    handle raises a ResourceWarning from wherever the GC happens to run, which
    lands in the middle of `tools/run-tests.sh`'s output and reads like a
    failure that is not one.
    """
    with MAP.open(newline="") as f:
        return list(csv.DictReader(f))


def replace_in_map(old, new):
    """A mutator swapping one exact substring of the map.

    It raises if the substring is gone rather than mutating nothing: a rename
    in `feature-map.csv` has to come with an update here, and a case that
    silently stopped mutating is a case that has stopped testing.
    """
    def mutate(text):
        if old not in text:
            raise AssertionError(
                f"the map no longer contains {old!r}, so this case is testing "
                f"nothing. A rename in feature-map.csv has to come with an "
                f"update here or the suite is quietly vacuous.")
        return text.replace(old, new, 1)
    return mutate


def blank_reason(feature):
    """A mutator emptying one row's quoted `reason` field."""
    def mutate(text):
        lines = text.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith(feature + ","):
                head, sep, _tail = line.partition('"')
                if not sep:
                    raise AssertionError(
                        f"the {feature} row's reason is not a quoted field, "
                        f"so blanking it would not blank the reason cell")
                lines[i] = head + "\n"
                return "".join(lines)
        raise AssertionError(f"the {feature} row is gone from the map")
    return mutate


class CommittedArtifactTests(unittest.TestCase):
    """The shipped artifact, checked as it stands."""

    def test_check_is_green(self):
        r = run_check()
        self.assertEqual(
            r.returncode, 0,
            f"the committed artifact is refused:\n{r.stderr}")

    def test_self_test_is_green(self):
        r = subprocess.run(
            [sys.executable, str(HERE / "check_dmi_descriptor.py"),
             "--self-test"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_map_has_the_fifteen_rows_the_issue_lists(self):
        rows = map_rows()
        self.assertEqual(len(rows), 15, f"got {len(rows)} rows")
        self.assertEqual(
            sum(1 for r in rows if r["in_descriptor"].strip() == "yes"), 8)
        self.assertEqual(
            sum(1 for r in rows if r["in_descriptor"].strip() == "no"), 7)

    def test_every_row_carries_a_reason(self):
        for row in map_rows():
            self.assertTrue(
                row["reason"].strip(),
                f"{row['repo_feature']} has no reason, and an exclusion with "
                f"no written reason is the one thing this file exists for")

    def test_patch_is_additive_only(self):
        body, _added, _bits = checker.patch_added_bits(PATCH)
        self.assertEqual(
            checker.removed_lines(body), [],
            "the patch removes a line. This entry must not touch an existing "
            "row, field or bit, or every other board in the table is at risk")

    def test_patch_bits_and_map_rows_agree_both_ways(self):
        _body, _added, bits = checker.patch_added_bits(PATCH)
        claimed = {r["upstream_bit"].strip()
                   for r in map_rows()
                   if r["in_descriptor"].strip() == "yes"}
        self.assertEqual(bits - claimed, set(),
                         "a bit the patch sets that no row names")
        self.assertEqual(claimed - bits, set(),
                         "a row claiming a bit the patch does not set")

    def test_base_commit_agrees_with_the_nix_pin(self):
        b, n = checker.base_rev(BASE_COMMIT), checker.nix_rev(NIX)
        self.assertTrue(
            checker.revs_agree(b, n),
            f"linux/patches/BASE_COMMIT says {b!r} but {NIX.name} pins {n!r}. "
            f"The patch is diffed against one and the build fetches the "
            f"other, and the excerpt has to quote the one the build fetches")

    def test_excerpt_quotes_the_lines_the_map_cites(self):
        lines = checker.excerpt_lines(EXCERPT)
        for row in map_rows():
            src = row["upstream_addr_source"].strip()
            if not src:
                continue
            n = int(src.rsplit(":", 1)[1])
            self.assertIn(n, lines,
                          f"{row['repo_feature']} cites {src}, which the "
                          f"excerpt does not quote")
            self.assertIn(
                row["upstream_ec_addr"].strip(), lines[n],
                f"{row['repo_feature']} cites {src} for "
                f"{row['upstream_ec_addr']}, which that line does not carry")

    def test_no_bit_source_is_unsourced(self):
        # The review's central objection to the previous attempt: `unsourced`
        # encoded "not sourceable" as a permanent property of a row, when the
        # enum was one fetch away. With the excerpt committed, no row may say
        # it cannot name a bit.
        for row in map_rows():
            self.assertEqual(
                row["bit_source"].strip(), "upstream@5a24248",
                f"{row['repo_feature']} has bit_source "
                f"{row['bit_source']!r}. The enum is in upstream-excerpt.txt, "
                f"so every row's spelling is readable at the pinned rev")
            self.assertTrue(
                row["upstream_bit"].strip(),
                f"{row['repo_feature']} names no upstream bit")


class RefusalTests(unittest.TestCase):
    """One mutation per rule, each asserting the refusal names the problem."""

    def assert_refused(self, mutate, *must_mention):
        with patched_map(mutate) as tmp:
            r = run_check(tmp)
        self.assertEqual(
            r.returncode, 1,
            f"the mutation was accepted; --check should have refused it.\n"
            f"stdout: {r.stdout}\nstderr: {r.stderr}")
        for phrase in must_mention:
            self.assertIn(
                phrase, r.stderr,
                f"the refusal does not mention {phrase!r}, so it is not "
                f"explaining the problem it found.\nstderr: {r.stderr}")

    def test_a_misspelled_constant_is_refused(self):
        # The case the previous checker could not make. UNIWILL_FEATURE_CPU_TMP
        # is a plausible invention that reads correctly and does not exist.
        self.assert_refused(
            replace_in_map("UNIWILL_FEATURE_CPU_TEMP", "UNIWILL_FEATURE_CPU_TMP"),
            "does not appear in upstream-excerpt.txt")

    def test_an_invented_address_is_refused(self):
        self.assert_refused(
            replace_in_map("0x043E,uniwill-acpi.c:87", "0x0999,uniwill-acpi.c:87"),
            "0x0999 does not appear in upstream-excerpt.txt")

    def test_an_address_source_pointing_elsewhere_is_refused(self):
        self.assert_refused(
            replace_in_map("0x043E,uniwill-acpi.c:87", "0x043E,uniwill-acpi.c:89"),
            "does not carry 0x043E")

    def test_a_status_registers_yaml_does_not_record_is_refused(self):
        # The hand-copied status: registers.yaml grades 0x043E confirmed-working.
        self.assert_refused(
            replace_in_map("0x043E,confirmed-working", "0x043E,present-untested"),
            "is not what registers.yaml records for 0x043E")

    def test_an_address_with_no_register_entry_is_refused(self):
        self.assert_refused(
            replace_in_map("0x043E,confirmed-working,0x043E",
                           "0x0998,confirmed-working,0x043E"),
            "not an address registers.yaml records")

    def test_an_undeclared_status_is_refused(self):
        self.assert_refused(
            replace_in_map("0x043E,confirmed-working", "0x043E,confirmed-maybe"),
            "is not a value registers.yaml's header declares")

    def test_claiming_a_present_untested_feature_is_refused(self):
        # The KEYBOARD_BACKLIGHT trap: its Fn+F6/F7 hotkey is confirmed, its
        # software LED-class path is not. The map keeps it out; putting it in
        # has to fail.
        self.assert_refused(
            replace_in_map("0x078C,present-untested,0x078C,uniwill-acpi.c:257,,no,",
                           "0x078C,present-untested,0x078C,uniwill-acpi.c:257,,yes,"),
            "not a grade asserting the feature works")

    def test_claiming_a_refuted_mechanism_is_refused(self):
        # confirmed-not-this-mechanism is `confirmed-` prefixed and means the
        # opposite of "works". A prefix test would have demanded this claim.
        self.assert_refused(
            replace_in_map(
                "0x0748,confirmed-not-this-mechanism,0x0748,uniwill-acpi.c:165,,no,",
                "0x0748,confirmed-not-this-mechanism,0x0748,uniwill-acpi.c:165,,yes,"),
            "not a grade asserting the feature works")

    def test_a_fan_claim_without_the_interface_judgement_is_refused(self):
        # Rule 6(b)'s second half, and the one 6(a) can never reach because the
        # fans have no address in registers.yaml.
        self.assert_refused(
            replace_in_map("live-confirmed;driver-interface-drives",
                           "live-confirmed"),
            "must also record that the driver's interface genuinely drives")

    def test_a_claim_with_no_verdict_is_refused(self):
        self.assert_refused(
            replace_in_map("live-confirmed;driver-interface-drives,yes,",
                           ",yes,"),
            "the verdict must carry the live observation")

    def test_a_verdict_borrowing_another_grade_is_refused(self):
        self.assert_refused(
            replace_in_map("live-confirmed;driver-interface-drives",
                           "unknown-not-absent;driver-interface-drives"),
            "the verdict must carry the live observation")

    def test_a_claim_citing_no_file_is_refused(self):
        self.assert_refused(
            replace_in_map("docs/findings.md \"\"Feature-by-feature driver "
                           "verification\"\"). Upstream's fan hwmon",
                           "it seemed right. Upstream's fan hwmon"),
            "needs a reason citing the file")

    def test_an_exclusion_with_no_reason_is_refused(self):
        # Blanked rather than swapped, because the reason is a quoted CSV
        # field: emptying it means removing the quotes too, and a swap that
        # left them behind would test a different row.
        self.assert_refused(
            blank_reason("TOUCHPAD_TOGGLE"),
            "an exclusion with no written reason")

    def test_a_claim_with_no_reason_is_refused(self):
        self.assert_refused(
            blank_reason("PRIMARY_FAN"),
            "an exclusion with no written reason")


class RuleAgreementTests(unittest.TestCase):
    """The properties that make the rules worth having, stated as invariants."""

    def test_working_statuses_exclude_the_two_inert_grades(self):
        # If this ever holds only two values by accident again, the include
        # rule has stopped being about behaviour and started being a prefix.
        self.assertNotIn("confirmed-inert", checker.WORKING_STATUSES)
        self.assertNotIn("confirmed-not-this-mechanism",
                         checker.WORKING_STATUSES)
        self.assertIn("confirmed-working", checker.WORKING_STATUSES)
        self.assertIn("confirmed-working-partially", checker.WORKING_STATUSES)

    def test_declared_statuses_are_the_real_ones(self):
        from check_status_vocabulary import declared_statuses
        values, _suffixes = declared_statuses(REGISTERS)
        for status in checker.WORKING_STATUSES:
            self.assertIn(status, values,
                          f"{status} is claimable but registers.yaml does not "
                          f"declare it, so rule 6(a) is checking against a "
                          f"grade that does not exist")

    def test_every_upstream_bit_exists_in_the_excerpt(self):
        # The claim that makes rule 7 meaningful: every spelling the map uses
        # is one the pinned source defines.
        text = EXCERPT.read_text()
        for row in map_rows():
            self.assertIn(row["upstream_bit"].strip(), text,
                          f"{row['repo_feature']} names a constant the "
                          f"excerpt does not contain")


if __name__ == '__main__':
    unittest.main()
