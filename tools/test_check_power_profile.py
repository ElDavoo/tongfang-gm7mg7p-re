#!/usr/bin/env python3
r"""The refusals of `tools/check_power_profile.py`, not its happy path.

A rule that cannot fail is the failure mode worth a suite, and this checker's
whole job is refusing. The previous attempt at issue #10 shipped a checker that
accepted any plausible `UNIWILL_FEATURE_*` constant, so a name invented into
both a map and a patch passed every check in the tree; each case here mutates
one committed input, runs `--check` **as a subprocess** — for a checker the
exit code is the product, and only a process can show what a consumer sees —
and asserts it goes red *and names the problem*.

**The negative controls are what make the greens mean anything.** A rule that
fires on everything passes every positive in this file. Each one therefore
carries a companion that must stay green: the same row as the misspelling but
spelled correctly, a comment naming the wrong Turbo gate, a bulk write that
*does* cover the run a single-address write would not. The two that decide
whether the tool survives a week are the comment case and the vocabulary case
— a check that fires on the text stating it is a check everybody turns off,
and this patch names `FAN_TURBO_SUPPORTED` in a comment precisely to record
that it is refusing it.

Every mutation is a `tempfile` copy, so nothing here writes the artifact a
human submits. **Not in any gate:** `run-tests.sh` finds the suite by itself,
and the checker is not wired into `agent-gates.sh` because that file is copied
from `agent-pipeline` and the change is upstream's to make.
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

import check_power_profile as c  # noqa: E402


def read_map(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_map(path, rows, columns=None):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns or c.COLUMNS)
        w.writeheader()
        w.writerows(rows)


def find(rows, **kw):
    """The one row matching every key=value, or a failure that says so."""
    for row in rows:
        if all(row.get(k, "").strip() == v for k, v in kw.items()):
            return row
    raise AssertionError(f"no row matching {kw} in {len(rows)} rows")


class CheckPowerProfile(unittest.TestCase):
    """Every case runs the real checker over a copy of one committed input."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="check-profile-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.map = os.path.join(self.tmp, "profile-map.csv")
        self.patch = os.path.join(self.tmp, "patch.diff")
        self.excerpt = os.path.join(self.tmp, "excerpt.txt")
        self.pr = os.path.join(self.tmp, "PR.md")
        shutil.copy(c.DEFAULT_MAP, self.map)
        shutil.copy(c.DEFAULT_PATCH, self.patch)
        shutil.copy(c.DEFAULT_EXCERPT, self.excerpt)
        shutil.copy(c.DEFAULT_PR, self.pr)

    def run_check(self, *extra):
        """`--check` over the copies, as a subprocess. Returns (rc, out, err)."""
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "tools", "check_power_profile.py"),
             "--check", "--map", self.map, "--patch", self.patch,
             "--excerpt", self.excerpt, "--pr", self.pr, *extra],
            capture_output=True, text=True, cwd=self.tmp)
        return proc.returncode, proc.stdout, proc.stderr

    def assertRed(self, needle, *extra):
        rc, _out, err = self.run_check(*extra)
        self.assertEqual(rc, 1, f"expected a refusal, got a clean run:\n{err}")
        self.assertIn(needle, err,
                      f"the run went red but never named {needle!r}:\n{err}")

    def assertGreen(self, *extra):
        rc, _out, err = self.run_check(*extra)
        self.assertEqual(rc, 0, f"expected a clean run, got:\n{err}")

    # --- the committed artifact, which is the point of running this ------

    def test_committed_artifact_is_clean(self):
        self.assertGreen()

    def test_self_test_passes(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "tools", "check_power_profile.py"),
             "--self-test"],
            capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0,
                         f"--self-test refused:\n{proc.stdout}{proc.stderr}")

    def test_a_check_that_locates_nothing_is_not_a_clean_run(self):
        """A checker handed a tree it cannot read must fail, not pass quietly.

        The vacuous-check defect at the level of the exit code: a run that read
        no rows and no excerpt has checked nothing, and reporting that as green
        is how a gate stops gating.
        """
        rc, _out, err = self.run_check("--map", os.path.join(self.tmp, "absent.csv"))
        self.assertEqual(rc, 1, f"a missing map was a clean run:\n{err}")

    # --- rule 3: the value is derived, never typed -----------------------

    def test_a_bare_literal_value_source_is_refused(self):
        for literal in ("0xA0", "35", "0x23 0x23 0xA5"):
            with self.subTest(literal=literal):
                rows = read_map(self.map)
                find(rows, mode="low-power", register="0x0751")["value_source"] = literal
                write_map(self.map, rows)
                self.assertRed("names neither a bit spelling")
                shutil.copy(c.DEFAULT_MAP, self.map)

    def test_a_blank_value_source_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="balanced", register="0x0751")["value_source"] = ""
        write_map(self.map, rows)
        self.assertRed("value_source is empty")

    def test_the_same_cell_spelled_as_bits_is_not_refused(self):
        """The negative control for the case above, in the same column."""
        rows = read_map(self.map)
        find(rows, mode="performance", register="0x0751")["value_source"] = \
            "ec-mode-byte:FAN_MODE_TURBO (0x10)"
        write_map(self.map, rows)
        self.assertGreen()

    # --- rule 1, in both directions --------------------------------------

    def test_a_status_registers_yaml_does_not_record_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="low-power", register="0x0751")["registers_status"] = \
            "confirmed-working"
        write_map(self.map, rows)
        self.assertRed("is not what registers.yaml records")

    def test_a_blank_status_on_an_address_the_file_records_is_refused(self):
        """The fan table's shape applied where it is not right.

        `0x0F00` has no entry, which is why its row leaves the cell empty; the
        mode byte has one, and an empty cell there would be an ungraded
        register slipping through as nobody's business.
        """
        rows = read_map(self.map)
        find(rows, mode="low-power", register="0x0751")["registers_status"] = ""
        write_map(self.map, rows)
        self.assertRed("registers_status is empty but registers.yaml records")

    def test_the_fan_tables_empty_status_is_not_refused(self):
        rows = read_map(self.map)
        row = find(rows, register="0x0F00-0x0F5F")
        self.assertEqual(row["registers_status"], "",
                         "the fan table's status should be empty, and this "
                         "case is what holds it")
        self.assertGreen()

    def test_an_undeclared_status_vocabulary_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="balanced", register="0x0751")["registers_status"] = \
            "confirmed-maybe"
        write_map(self.map, rows)
        self.assertRed("is not a value registers.yaml's header declares")

    # --- rule 4: the spellings, and who owes an unsourced one ------------

    def test_a_misspelled_upstream_name_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="low-power", register="0x0751")["upstream_name"] = \
            "EC_ADDR_MANUAL_FAN_CTRL_2"
        write_map(self.map, rows)
        self.assertRed("does not appear in upstream-excerpt-profile.txt")

    def test_an_address_source_pointing_at_the_wrong_line_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="low-power", register="0x0751")["upstream_addr_source"] = \
            "uniwill-acpi.c:240"  # carries 0x0782
        write_map(self.map, rows)
        self.assertRed("does not carry")

    def test_an_address_source_naming_an_unquoted_line_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="low-power", register="0x0751")["upstream_addr_source"] = \
            "uniwill-acpi.c:9999"
        write_map(self.map, rows)
        self.assertRed("is not a line upstream-excerpt-profile.txt quotes")

    def test_a_row_claiming_an_address_the_patch_never_defines_is_refused(self):
        """The unsourced case, in the direction that is a claim rather than a gap."""
        rows = read_map(self.map)
        row = find(rows, register="0x049F")
        row["register"] = "0x0999"
        row["registers_status"] = ""
        write_map(self.map, rows)
        self.assertRed("is not an address registers.yaml records")

    # --- rule 5: additive only -------------------------------------------

    def test_a_removed_line_is_refused(self):
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "+\t.probe = gm7mg7p_probe,",
                "-\t.probe = gm7mg7p_probe,\n+\t.probe = gm7mg7p_probe,"))
        self.assertRed("the patch removes a line")

    def test_prose_in_the_patch_header_is_not_a_removal(self):
        """The negative control for the case above.

        The header is documentation and may say anything, including what a
        rule forbids; a scanner that started at the top of the file would fire
        on this patch's own explanation of itself.
        """
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace("Subject: [PATCH]",
                                 "Subject: [PATCH]\n- this line of prose starts with a dash"))
        self.assertGreen()

    # --- rules 6, 7, 8: the absences, and their negative controls --------

    def test_a_mode_byte_the_captures_never_recorded_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="performance", register="0x0751")["value_source"] = \
            "ec-mode-byte:FAN_MODE_TURBO (0x99)"
        write_map(self.map, rows)
        self.assertRed("The run is the live half of the answer")

    def test_a_mode_byte_vendor_ec_map_does_not_list_is_refused(self):
        rows = read_map(self.map)
        find(rows, mode="balanced", register="0x0751")["value_source"] = \
            "ec-mode-byte:no bits set (0x77)"
        write_map(self.map, rows)
        self.assertRed("does not list it")

    def test_a_patch_gating_on_fan_turbo_supported_is_refused(self):
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "\tdata->turbo_supported = !!(value & TURBO_MODE_SUPPORTED);",
                "\tdata->turbo_supported = !!(value & FAN_TURBO_SUPPORTED);"))
        self.assertRed("FAN_TURBO_SUPPORTED")

    def test_a_patch_naming_the_wrong_gate_in_a_comment_is_not_refused(self):
        """The case that decides whether rule 7 survives a week.

        This patch names `FAN_TURBO_SUPPORTED` in a comment precisely to record
        that it is refusing it. A rule that scanned comments would fire on the
        explanation of the rule.
        """
        rc, _out, err = self.run_check()
        self.assertEqual(rc, 0, f"the comment naming the wrong gate was refused:\n{err}")
        with open(self.patch) as f:
            self.assertIn("FAN_TURBO_SUPPORTED", f.read(),
                          "the fixture no longer explains the gate it refuses, "
                          "so this case has stopped testing anything")

    def test_a_hard_coded_wattage_is_refused(self):
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "\tu8 limits[ARRAY_SIZE(uniwill_pl_settings)];",
                "\tu8 limits[ARRAY_SIZE(uniwill_pl_settings)];\n+\tlimits[0] = 35;"))
        self.assertRed("a wattage here is the one thing")

    def test_a_limit_read_out_of_a_default_block_is_not_a_wattage(self):
        """The negative control for the case above.

        `.pl_defaults = 0x0734,` names the address the driver reads the limit
        out of. Scoping the rule to bare decimals assigned to limit-shaped
        names is what keeps it from firing on that.
        """
        rc, _out, err = self.run_check()
        self.assertEqual(rc, 0, f"a default block address was read as a wattage:\n{err}")

    def test_a_patch_writing_ap_oem_is_refused(self):
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "\tret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,",
                "\tregmap_write(data->regmap, EC_ADDR_AP_OEM, 0);\n+\t"
                "ret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,"))
        self.assertRed("EC_ADDR_AP_OEM")

    def test_a_patch_reading_ap_oem_is_not_refused(self):
        """The negative control: the driver already reads that byte, and the
        rule is about writes."""
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "\tret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,",
                "\tregmap_read(data->regmap, EC_ADDR_AP_OEM, &value);\n+\t"
                "ret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,"))
        self.assertGreen()

    # --- rule 9: nothing the patch touches is unaccounted for ------------

    def test_a_write_the_map_does_not_claim_is_refused(self):
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "\tret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,",
                "\tregmap_write(data->regmap, EC_ADDR_CTGP_DB_TPP_OFFSET, 1);\n+\t"
                "ret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,"))
        self.assertRed("no profile-map.csv row accounts for it")

    def test_a_write_the_checker_cannot_resolve_is_refused_not_skipped(self):
        """The class of write that is hardest to notice, held the other way.

        `EC_ADDR_BIOS_OEM` is a real upstream constant, but the excerpt this
        checker resolves names against does not quote its `#define`, so the
        write cannot be tied to an address. Declining it would leave the
        quietest hole in the rule sitting exactly where a reader would not
        look.
        """
        with open(self.patch) as f:
            text = f.read()
        with open(self.patch, "w") as f:
            f.write(text.replace(
                "\tret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,",
                "\tregmap_write(data->regmap, EC_ADDR_BIOS_OEM, 1);\n+\t"
                "ret = regmap_update_bits(data->regmap, EC_ADDR_MANUAL_FAN_CTRL,"))
        self.assertRed("does not give it an address this checker can read")

    def test_a_row_claiming_a_write_the_patch_never_makes_is_refused(self):
        """Rule 9's other direction: a map promising what the patch does not do.

        The row is repointed at a register the patch genuinely never touches,
        rather than at one it does -- so the refusal is about the map and not
        about the diff.
        """
        rows = read_map(self.map)
        row = find(rows, mode="performance", register="0x0785")
        row["register"] = "0x0744"
        row["upstream_name"] = "EC_ADDR_CTGP_DB_CTGP_OFFSET"
        row["upstream_addr_source"] = "uniwill-acpi.c:157"
        row["registers_status"] = "confirmed-working"
        write_map(self.map, rows)
        self.assertRed("never writes that address")

    def test_a_bulk_write_covers_its_whole_run(self):
        """The negative control for the resolution behind that case.

        `regmap_bulk_write(..., EC_ADDR_PL1_SETTING, limits, sizeof(limits))`
        writes 0x0783, 0x0784 and 0x0785. A checker that read only the first
        argument would report two rows the patch very much does honour.
        """
        rc, _out, err = self.run_check()
        self.assertEqual(rc, 0,
                         f"the committed patch was refused for its own bulk write:\n{err}")
        with open(self.patch) as f:
            self.assertIn("regmap_bulk_write", f.read(),
                          "the fixture no longer contains the bulk write this "
                          "case is about")

    # --- the PR body ------------------------------------------------------

    def test_a_pr_body_that_omits_a_written_register_is_refused(self):
        with open(self.pr) as f:
            text = f.read()
        with open(self.pr, "w") as f:
            f.write(text.replace("EC_ADDR_MANUAL_FAN_CTRL", "that register"))
        self.assertRed("which the map claims the patch")

    def test_a_pr_body_naming_a_pl_register_by_name_only_is_enough(self):
        """The negative control for the case above, and for the rule's shape.

        The body a human pastes is written in the names a kernel reader knows,
        so a rule demanding the hex address would fail a well-written one. The
        hex `0x0783` is stripped here and the run has to stay green on the
        symbolic name alone.
        """
        with open(self.pr) as f:
            text = f.read()
        with open(self.pr, "w") as f:
            f.write(text.replace("0x0783", "the first limit register"))
        rc, _out, err = self.run_check()
        self.assertEqual(rc, 0,
                         f"a PR body naming a register by symbol was refused:\n{err}")


if __name__ == "__main__":
    unittest.main()
