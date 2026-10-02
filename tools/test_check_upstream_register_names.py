#!/usr/bin/env python3
r"""The refusals of `tools/check_upstream_register_names.py`, not its happy path.

A rule that cannot fail is the failure mode worth a suite, and this checker's
whole job is refusing. Every case here mutates one committed input, runs
`--check` **as a subprocess** — for a checker the exit code is the product, and
only a process can show what a consumer sees — and asserts it goes red *and
names the problem*.

**The negative controls are what make the greens mean anything.** A rule that
fires on everything passes every positive in this file. Each one therefore
carries a companion that must stay green: the same citation correctly spelled,
a hex address beside a decimal, a claim that names the wrong gate *in prose*
in order to record that the note is declining to claim it. That last one
decides whether rule 6 survives a week — a check that fires on the text stating
it is a check everybody turns off, and this note names `FAN_TURBO_SUPPORTED`
in three places precisely to say it is not claiming the thing.

Two cases drive the tree rather than the note, because two of the checker's
rules are about a *gap* and a *decline* rather than about a citation: adding a
`0x0742` row to `registers.yaml` has to make the note's "no entry" claim go
stale, and a fragment showing a read of the Turbo gate has to make the
declining stale. Both are driven over a scratch copy, never over the committed
file.

Every mutation is a `tempfile` copy, so nothing here writes the note a human
sends upstream. **Not in any gate:** `run-tests.sh` finds the suite by itself,
and the checker is not wired into `agent-gates.sh` because that file is copied
from `agent-pipeline` and the change is upstream's to make.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "tools", "check_upstream_register_names.py")

# The committed inputs, and where they live, so a case can copy one and hand
# the rest over untouched. Read off the module rather than repeated here, so
# this suite cannot end up checking a different file from the one the checker
# defaults to.
sys.path.insert(0, os.path.join(REPO, "tools"))
import check_upstream_register_names as c  # noqa: E402


def read(path):
    with open(path) as f:
        return f.read()


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


class CheckUpstreamRegisterNames(unittest.TestCase):
    """Every case runs the real checker over a copy of one committed input."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="check-upstream-names-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.note = os.path.join(self.tmp, "note.md")
        shutil.copy(c.DEFAULT_NOTE, self.note)
        self.text = read(self.note)

    def edit(self, old, new, count=1):
        """Replace in the scratch note and write it back, or fail loudly.

        The assertion matters: a case whose anchor text has drifted would
        otherwise write a note identical to the committed one, go green, and
        pass for the wrong reason -- which is the defect this suite exists to
        catch, wearing its own clothes.
        """
        self.assertIn(old, self.text,
                      f"the committed note no longer contains {old!r}, so this "
                      f"case is not testing what it was written for")
        self.text = self.text.replace(old, new, count)
        write(self.note, self.text)

    def scratch_patches(self, extra=None):
        """A copy of the committed excerpt directories, under `--patches`.

        The excerpt tree is what rule 6's read-decline is decided against, so
        a case that has to make the decline stale has to add a fragment
        somewhere -- and it has to add it to a copy, because the committed
        excerpts are inputs to every other case and to the checker itself.
        `extra` names a file to create inside a directory the note cites
        nowhere, which is the only place a read would realistically land.
        """
        patches = os.path.join(self.tmp, "patches")
        for name in ("gm7mg7p-dmi-entry", "gm7mg7p-power-profile"):
            os.makedirs(os.path.join(patches, name))
            for excerpt in os.listdir(os.path.join(c.PATCHES, name)):
                if excerpt.startswith("upstream-excerpt"):
                    shutil.copy(os.path.join(c.PATCHES, name, excerpt),
                                os.path.join(patches, name, excerpt))
        for directory, filename, text in (extra or []):
            os.makedirs(os.path.join(patches, directory), exist_ok=True)
            write(os.path.join(patches, directory, filename), text)
        return patches

    def run_check(self, *extra):
        """`--check` over the copies, as a subprocess. Returns (rc, out, err)."""
        proc = subprocess.run(
            [sys.executable, CHECKER, "--check", "--note", self.note, *extra],
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

    # --- the committed note, which is the point of running this ----------

    def test_committed_note_is_clean(self):
        self.assertGreen()

    def test_self_test_passes(self):
        proc = subprocess.run([sys.executable, CHECKER, "--self-test"],
                              capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0,
                         f"--self-test refused:\n{proc.stdout}{proc.stderr}")

    def test_a_note_that_does_not_exist_is_not_a_clean_run(self):
        """The vacuous-check defect at the level of the exit code.

        A run that read no note has checked nothing, and reporting that as
        green is how a gate stops gating.
        """
        rc, _out, err = self.run_check("--note", os.path.join(self.tmp, "gone.md"))
        self.assertEqual(rc, 1, f"a missing note was a clean run:\n{err}")

    def test_a_note_with_no_table_is_not_a_clean_run(self):
        """Same defect one level in: the tables are what the rules read.

        A note whose calibration table has been cut down to prose leaves every
        rule below it with nothing to decide, and five green rules would look
        exactly like five passing checks.
        """
        self.edit("| claim | kind | standing |", "Claims, unranked:")
        self.assertRed("no table headed 'claim'")

    # --- rule 1: the upstream spellings ---------------------------------

    def test_a_misspelled_upstream_symbol_is_refused(self):
        self.edit("| `EC_ADDR_FAN_DEFAULT` | `0x0786` |",
                  "| `EC_ADDR_FAN_DEFAUL` | `0x0786` |")
        self.assertRed("A definition is the only shape this rule accepts")

    def test_a_citation_to_a_line_the_excerpt_does_not_carry_is_refused(self):
        self.edit("upstream-excerpt.txt:174", "upstream-excerpt.txt:9999")
        self.assertRed("there is no line 9999")

    def test_a_value_upstream_does_not_define_is_refused(self):
        self.edit("| `EC_ADDR_FAN_DEFAULT` | `0x0786` |",
                  "| `EC_ADDR_FAN_DEFAULT` | `0x0799` |")
        self.assertRed("the note gives EC_ADDR_FAN_DEFAULT the value")

    def test_an_excerpts_bracket_annotation_is_not_a_definition(self):
        """The negative case, and the reason the rule wants a `#define`.

        The profile excerpt carries a `[bracket]` line naming
        `FAN_TURBO_SUPPORTED` in prose, right above the fragment that defines
        it. A rule that read "the symbol appears on that line" would accept
        the annotation as the definition.
        """
        self.edit("upstream-excerpt-profile.txt:133",
                  "upstream-excerpt-profile.txt:123")
        self.assertRed("not a quoted fragment")

    def test_a_name_used_in_prose_but_not_in_the_table_is_refused(self):
        with open(self.note, "a") as f:
            f.write("\nA passing mention of `FAN_CURVE_ROWS`.\n")
        self.assertRed("the note uses the upstream name FAN_CURVE_ROWS")

    def test_a_name_the_table_carries_is_not_refused_for_appearing_in_prose(self):
        """The negative control for the closure above.

        Repeating a graded name in prose is what the note is for; only a name
        the table has never read off a pinned rev is the defect.
        """
        with open(self.note, "a") as f:
            f.write("\n`EC_ADDR_FAN_DEFAULT` again, in prose.\n")
        self.assertGreen()

    # --- rule 2: the registers.yaml rows, and 0x0742's absence -----------

    def test_an_entry_name_registers_yaml_does_not_use_is_refused(self):
        self.edit("| `0x0786` | `CPU_TCC_OFFSET (APTC/APTN)` |",
                  "| `0x0786` | `CPU_TCC_OFFSET` |")
        self.assertRed("registers.yaml calls it")

    def test_a_status_registers_yaml_does_not_record_is_refused(self):
        self.edit("| `0x049F` | `BIOS_INFO_3 (Turbo mode supported)` | "
                  "`present-untested` |",
                  "| `0x049F` | `BIOS_INFO_3 (Turbo mode supported)` | "
                  "`confirmed-working` |")
        self.assertRed("registers.yaml records")

    def test_0x0742_cited_as_a_registers_yaml_row_is_refused(self):
        """The guard the issue's own gap needs.

        `0x0742` has no entry, so a row naming one resolves to nothing. A
        later reader tidying that into a citation is the failure, and this is
        the case that stops it.
        """
        self.edit("| `0x0742` | *(no entry)* | *(no entry)* |",
                  "| `0x0742` | `USB_C_POWER_PRIORITY` | "
                  "`unknown-not-absent` |")
        self.assertRed("registers.yaml records no entry for 0x0742")

    def test_the_no_row_claim_goes_stale_once_the_file_grows_one(self):
        """The other direction of the same gap, driven over a scratch copy.

        If this only fired one way the rule would be a lock on today's tree
        rather than a claim about it, and closing the gap would turn a correct
        note red for the wrong reason.
        """
        scratch = os.path.join(self.tmp, "registers.yaml")
        shutil.copy(c.DEFAULT_REGISTERS, scratch)
        # The copy first, and the append only to the copy. The other order
        # writes the row onto the committed file, which is the one thing a
        # suite whose subject is "nothing here writes the artifact" must not
        # do.
        with open(scratch, "a") as f:
            f.write("  - name: SUPPORT_BYTE_5 (added by a later change)\n"
                    "    addr: 0x0742\n"
                    "    sources: [uniwill-laptop]\n"
                    "    status: present-untested\n")
        self.assertRed("it now has one", "--registers", scratch)

    def test_a_live_address_with_no_registers_row_is_refused(self):
        """The closure: an address the note reports a value for is a claim."""
        self.edit("| `0x049F` | `BIOS_INFO_3 (Turbo mode supported)` | "
                  "`present-untested` |",
                  "| `0x0499` | `BIOS_INFO_3 (Turbo mode supported)` | "
                  "`present-untested` |")
        self.assertRed("has no row for it")

    # --- rule 3: the decompiled citations -------------------------------

    def test_a_citation_past_the_end_of_its_file_is_refused(self):
        self.edit("ECSpec.cs:307`", "ECSpec.cs:30000`")
        self.assertRed("is not inside it")

    def test_a_citation_in_the_second_table_is_not_invisible(self):
        """The note carries two `what | citation` tables, one per
        discrepancy, and a reader that stopped at the first would hold half the
        note's citations and report nothing about the other half."""
        self.edit("`GetTurboModeSupport` reads `1183`",
                  "`GetTurboModeModeSupport` reads `1183`")
        self.assertRed("no line of")

    def test_a_value_the_cited_span_does_not_carry_is_refused(self):
        self.edit("`ADDR_L1_PWM_DEFAULT_MYFAN3` is `1926`",
                  "`ADDR_L1_PWM_DEFAULT_MYFAN3` is `1927`")
        self.assertRed("no line of")

    def test_a_hex_address_beside_a_decimal_is_not_refused(self):
        """The negative control for the two cases above.

        This note's whole job is translating between a vendor that writes
        `1926` and an upstream that writes `0x0786`, and the hex is a
        translation for the reader rather than something the vendor's source
        carries. Rule 1 anchors the upstream half of that join.
        """
        self.edit("`ADDR_L1_PWM_DEFAULT_MYFAN3` is `1926`",
                  "`ADDR_L1_PWM_DEFAULT_MYFAN3` is `1926`, which is `0x786`")
        self.assertGreen()

    # --- rule 4: the live values, and what "held" means ------------------

    def test_a_value_the_snapshot_does_not_carry_is_refused(self):
        self.edit("| `0x0786` | `0x00` |", "| `0x0786` | `0x77` |")
        self.assertRed("and 2026-09-23-power-mode-snapshot-dc.txt records")

    def test_a_value_cited_to_the_transition_log_is_refused(self):
        """The overclaim the issue this note answers would otherwise carry.

        The `*-cycle-*.csv` files have the header `ts,addr,old,new` and record
        transitions, so they never read anything. Citing one for a value is an
        overclaim in the shape of a citation, and this is the only rule here
        that can tell the two files apart by what they are rather than by what
        a reader remembers about them.
        """
        self.edit("`0x00` | `2026-09-23-power-mode-snapshot-dc.txt`",
                  "`0x00` | `2026-09-23-power-mode-cycle-0700-07ff.csv`")
        self.assertRed("transition log")

    def test_an_address_the_cycle_capture_never_moved_cannot_be_called_changed(self):
        self.edit("| `0x049F` | `0x0A` | "
                  "`2026-09-23-power-mode-snapshot-dc.txt` | `no` |",
                  "| `0x049F` | `0x0A` | "
                  "`2026-09-23-power-mode-snapshot-dc.txt` | `yes` |")
        self.assertRed("has no row for it")

    def test_an_address_the_capture_did_move_can_be_called_changed(self):
        """The negative control for the case above, the other way round.

        `0x0751` is the mode byte, and the cycle capture moves it six times, so
        saying so has to stay green on the same tree that refuses the case
        above. Without it the rule could be refusing every value of that
        column.
        """
        self.edit("| `0x049F` | `0x0A` | "
                  "`2026-09-23-power-mode-snapshot-dc.txt` | `no` |",
                  "| `0x0751` | `0x10` | "
                  "`2026-09-23-power-mode-snapshot-dc.txt` | `yes` |")
        self.edit("| `0x049F` | `BIOS_INFO_3 (Turbo mode supported)` | "
                  "`present-untested` |",
                  "| `0x0751` | `MANUAL_FAN_CTRL (power mode / fan mode)` | "
                  "`present-untested` |\n| `0x049F` | "
                  "`BIOS_INFO_3 (Turbo mode supported)` | `present-untested` |")
        self.assertGreen()

    # --- rule 5: the DSDT field list ------------------------------------

    def test_a_width_the_asl_does_not_give_is_refused(self):
        self.edit("| `APTC` | `EC0` | `0x786` | `7` | `0-6` |",
                  "| `APTC` | `EC0` | `0x786` | `8` | `0-7` |")
        self.assertRed("the field list gives")

    def test_a_field_name_the_asl_does_not_give_is_refused(self):
        self.edit("| `APTC` | `EC0` | `0x786` | `7` | `0-6` |",
                  "| `APTZ` | `EC0` | `0x786` | `7` | `0-6` |")
        self.assertRed("the ASL names")

    def test_another_devices_field_at_the_same_offset_is_not_substituted(self):
        """The derivation is bounded to the device the row names.

        `UCSI` covers `0x786` in a USB controller's field list, earlier in the
        same file. A walk that did not stop at `Device (EC0)` would answer
        with it, and the note would be describing the wrong table.
        """
        self.edit("| `APTC` | `EC0` | `0x786` | `7` | `0-6` |",
                  "| `UCSI` | `XUSB` | `0x786` | `8` | `0-7` |")
        self.edit("| `APTN` | `EC0` | `0x786` | `1` | `7-7` |\n", "")
        self.assertRed("no field list of XUSB covers offset 0x786")

    # --- rule 6: the two declines, and the one that can go stale ---------

    def test_a_cross_board_claim_carried_as_established_is_refused(self):
        self.edit("`EC_ADDR_FAN_DEFAULT` is wrong for every Uniwill board | "
                  "cross-board | not-established |",
                  "`EC_ADDR_FAN_DEFAULT` is wrong for every Uniwill board | "
                  "cross-board | confirmed-static |")
        self.assertRed("cross-board claim is carried as")

    def test_an_upstream_use_claim_carried_as_established_is_refused(self):
        self.edit("| upstream reads `FAN_TURBO_SUPPORTED` | upstream-use | "
                  "not-established |",
                  "| upstream reads `FAN_TURBO_SUPPORTED` | upstream-use | "
                  "confirmed-static |")
        self.assertRed("upstream-use claim is carried as")

    def test_a_standing_outside_the_closed_set_is_refused(self):
        self.edit("| not-established |", "| probably-fine |")
        self.assertRed("is not one of")

    def test_the_note_naming_the_declined_gate_is_not_refused_for_it(self):
        """The case that decides whether rule 6 survives a week.

        The committed note names `FAN_TURBO_SUPPORTED` in its upstream table,
        in §4 and in §7, and rule 1 and rule 6 both key on that symbol. What
        must not happen is either of them firing on the sentence that records
        the note declining to claim the thing.
        """
        self.assertGreen()
        with open(self.note) as f:
            text = f.read()
        self.assertIn("not found being read", text,
                      "the note no longer declines the claim this case exists "
                      "to protect, so the case has stopped testing anything")

    def test_the_decline_goes_stale_when_an_excerpt_shows_a_read(self):
        """The one rule a new fragment can falsify rather than an edit.

        Driven over a scratch copy of the excerpt directory, so the committed
        excerpts are never the thing being edited to demonstrate the refusal.
        """
        patches = self.scratch_patches()
        with open(os.path.join(patches, "gm7mg7p-power-profile",
                               "upstream-excerpt-profile.txt"), "a") as f:
            f.write("    260: if (value & FAN_TURBO_SUPPORTED)\n")
        self.assertRed("gone stale", "--patches", patches)

    def test_a_read_in_an_excerpt_the_note_never_cites_still_counts(self):
        """The fragment that would make the decline stale is the one no row of
        the note points at, so a rule scanning only the cited excerpts would
        miss it. The scratch tree here carries a second excerpt directory the
        note names nowhere."""
        patches = self.scratch_patches([(
            "gm7mg7p-something-else", "upstream-excerpt-extra.txt",
            "    11: if (raw & FAN_TURBO_SUPPORTED)\n")])
        self.assertRed("gone stale", "--patches", patches)


if __name__ == "__main__":
    unittest.main()
