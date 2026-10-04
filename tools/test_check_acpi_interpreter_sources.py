#!/usr/bin/env python3
"""The refusals of `tools/check_acpi_interpreter_sources.py`, one per rule.

The checker is what decides whether
`docs/findings/acpi-interpreter-region-access.md` may say that two public
interpreters split an unaligned `MMRD` into four byte-wide accesses and test no
alignment. Its six rules are each a claim about evidence that could stop being
true without anybody noticing: an excerpt that lost its revision, a citation that
now points at the wrong line, a DSDT fact that was never re-measured, a recorded
null quietly dropped, an opening that starts implying a live run, an index entry
that stopped matching the directory.

A rule that cannot fail is the failure mode worth a suite, so this one pins the
refusals rather than the happy path. Each case mutates one committed input and
asserts that the checker goes red *and names the problem* — a bare non-zero exit
would pass just as well if the checker had started refusing everything, which is
the other way a check quietly dies.

Rule 2 is the one that had a gap worth a note here. It originally matched only
the fully quoted citation form, so a bare `` `:NNN` `` — which is how the
write-up names a line when it has just named the file — resolved to nothing at
all and was checked against nothing. Two such pointers were wrong: each named a
line that existed and said the opposite of its sentence, and one named a
`byte_alignment = 2;` in the very paragraph arguing that the access granularity
is 8. The rule now covers both forms and requires an excerpt pointer to quote
the line it names, which is what stops the next one; the three cases under rule 2
below are that, pinned.

Every mutation happens in a `tempfile` copy, and the checker runs as a
subprocess so the exit status under test is the real one. Nothing here writes to
the repository: the excerpts and the write-up are committed evidence and an
artificial edit to either would be a fabricated finding.

One thing this deliberately does not do: it does not fetch anything, and it does
not assert that the excerpts are what upstream still says.
`evidence/acpi/fetch-acpi-sources.sh` re-derives them from a fresh fetch and
needs the network, so it is not a gate. What is pinned here is the weaker and
still load-bearing claim — that the write-up's citations resolve against the
committed excerpts — which is the half a reviewer can check without egress.
"""
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
CHECKER = HERE / "check_acpi_interpreter_sources.py"

WRITEUP_NAME = "acpi-interpreter-region-access.md"
ACPICA = "acpica-region-access-excerpt.c.txt"
LINUX = "linux-acpi-region-access-excerpt.c.txt"
NULL_HEADING = "## What this does not establish"


@contextmanager
def sandbox():
    """A throwaway copy of everything the checker reads.

    The evidence directory, the write-up and the DSDT go in together because a
    mutation to any one of them is a case, and the checker's `--evidence`,
    `--writeup` and `--dsdt` options exist so a case can point at the copy. What
    is deliberately *not* copied is the rest of the tree: a suite that could
    reach `registers.yaml` would eventually come to depend on it.
    """
    root = Path(tempfile.mkdtemp())
    try:
        evidence = root / "acpi"
        shutil.copytree(REPO / "evidence" / "acpi", evidence)
        writeup = root / WRITEUP_NAME
        shutil.copy(REPO / "docs" / "findings" / WRITEUP_NAME, writeup)
        yield root, evidence, writeup
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run(evidence, writeup, dsdt=None):
    argv = [sys.executable, str(CHECKER),
            "--evidence", str(evidence),
            "--writeup", str(writeup),
            "--dsdt", str(dsdt or (evidence / "dsdt.dsl"))]
    return subprocess.run(argv, capture_output=True, text=True)


def edit(path, old, new, count=1):
    """Replace `old` in `path`, refusing to do it silently if it is not there.

    A mutation helper that no-ops when its anchor has drifted leaves the suite
    green and testing nothing, which is the same failure as a rule that cannot
    fail. `count=-1` replaces every occurrence, which is how the
    cites-by-nothing case removes one excerpt's worth of references.
    """
    text = path.read_text(encoding="utf-8")
    occurrences = text.count(old)
    if occurrences == 0:
        raise AssertionError("mutation anchor not present in %s: %r" % (path, old[:60]))
    if count != -1 and occurrences < count:
        raise AssertionError("mutation anchor appears %d times in %s, wanted %d"
                             % (occurrences, path, count))
    path.write_text(text.replace(old, new, count), encoding="utf-8")


class Refusals(unittest.TestCase):
    """One mutation per rule, and the negative control that says they can pass."""

    def assertRefused(self, result, needle):
        self.assertNotEqual(result.returncode, 0,
                            "checker accepted a mutation it should have refused:\n%s"
                            % result.stdout)
        self.assertIn(needle, result.stderr,
                      "refusal did not name %r; stderr was:\n%s" % (needle, result.stderr))

    def test_the_committed_tree_passes(self):
        """The negative control.

        Without this, every other case in this file passes if the checker
        refuses everything, which is the other way a rule set dies quietly.
        """
        with sandbox() as (_, evidence, writeup):
            result = run(evidence, writeup)
            self.assertEqual(result.returncode, 0,
                             "checker refused the committed tree:\n%s" % result.stderr)

    # --- rule 1: provenance -------------------------------------------------

    def test_an_excerpt_without_a_licence_line_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            path = evidence / ACPICA
            edit(path, "  Licence      : ", "  Note         : ")
            self.assertRefused(run(evidence, writeup), "carries no `Licence:` line")

    def test_an_excerpt_with_an_empty_revision_is_refused(self):
        """A field present but blank is as uncitable as a field absent.

        The whole line goes, not just the rev: leaving `(tag v6.6, released
        2023-10-30)` behind would still be a non-empty revision and the case
        would quietly stop testing anything.
        """
        with sandbox() as (_, evidence, writeup):
            edit(evidence / LINUX,
                 "  Revision     : ffc253263a1375a65fa6c9f62a893e9767fbebfa "
                 "(tag v6.6, released 2023-10-30)",
                 "  Revision     :")
            self.assertRefused(run(evidence, writeup), "carries no `Revision:` line")

    # --- rule 2: citations --------------------------------------------------

    def test_a_citation_whose_quoted_text_is_not_on_that_line_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(writeup, "`DatumCount = ACPI_ROUND_UP_TO (`",
                 "`DatumCount = ACPI_ROUND_UP_BY (`")
            self.assertRefused(run(evidence, writeup),
                               "which that line does not contain")

    def test_a_citation_pointing_at_a_line_that_moved_is_refused(self):
        """The case `ec/tools/check_citation_lines.py` exists for.

        The number is a rank into a file that gets regenerated, so a citation
        whose line moved lands somewhere real and reads plausibly. Here the
        excerpt is renumbered by one and the write-up is not, which is what a
        re-derivation at a newer revision looks like from the write-up's side.
        """
        with sandbox() as (_, evidence, writeup):
            excerpt = evidence / ACPICA
            lines = excerpt.read_text(encoding="utf-8").split("\n")
            quoted = "#define ACPI_MISALIGNMENT_NOT_SUPPORTED"
            index = next(i for i, line in enumerate(lines) if quoted in line)
            lines[index - 1], lines[index] = lines[index], lines[index - 1]
            excerpt.write_text("\n".join(lines), encoding="utf-8")
            self.assertRefused(run(evidence, writeup),
                               "which that line does not contain")

    def test_a_too_short_quotation_is_refused(self):
        """`if` is not a citation.

        The check is a containment test rather than an equality test, so that
        the write-up can quote a fragment instead of the source's own
        indentation. This is the case that keeps the loosening from becoming
        "matches anything".
        """
        with sandbox() as (_, evidence, writeup):
            edit(writeup, "`/* Validate and translate the bit width */`", "`if`")
            self.assertRefused(run(evidence, writeup), "which that line does not contain")

    def test_a_shorthand_citation_pointing_at_the_wrong_line_is_refused(self):
        """The case this rule was widened for.

        A bare `:NNN` inherits its file from the fully qualified pointer before
        it, so it resolves against the same excerpt -- and against the wrong
        line just as silently. This is the shape of the two pointers the first
        draft of the checker was green over: `:196` and `:151` each named a line
        that existed and said the opposite of the sentence, one of them a
        `byte_alignment = 2;` in the paragraph arguing that `ByteAcc` yields an
        8-bit granularity. Redirecting the shorthand is the same edit the fix
        made to the write-up, and it has to go red.
        """
        with sandbox() as (_, evidence, writeup):
            # Redirect the pointer, keeping the quotation: the mutation the fix
            # to the write-up was, which is what the rule has to catch. The
            # `edit` helper is not used because the pointer and its quotation
            # straddle a line wrap in the write-up.
            text = writeup.read_text(encoding="utf-8")
            assert ":229" in text, "the pointer this case redirects is gone"
            writeup.write_text(text.replace(":229", ":196", 1), encoding="utf-8")
            self.assertRefused(run(evidence, writeup),
                               "which that line does not contain")

    def test_a_pointer_into_an_excerpt_with_no_quoted_text_is_refused(self):
        """The other half of the same gap.

        Widening the pattern to find bare `:NNN` is only half the fix: without
        this, a pointer that quotes nothing resolves to a line number and is
        then checked against nothing, which is how both pointers above passed
        in the first place. Stripping the quotation from a pointer that the
        committed write-up carries is the mutation.
        """
        with sandbox() as (_, evidence, writeup):
            edit(writeup, "`:150` — `*value = (u64)ACPI_GET32(logical_addr_ptr);`",
                 "`:150`")
            self.assertRefused(run(evidence, writeup), "with no quoted text")

    def test_a_shorthand_that_inherits_no_file_is_refused(self):
        """Inheritance has to fail loudly rather than default to something.

        The first fully qualified pointer in the write-up is what a shorthand
        before it would inherit; removing it leaves a `:NNN` naming no file at
        all, and the alternative to refusing is to guess one.
        """
        with sandbox() as (_, evidence, writeup):
            # Remove the first fully qualified pointer in the write-up, so the
            # bare pointers after it have nothing to inherit. The anchor spans
            # a line wrap, so this is a direct replace rather than `edit`.
            text = writeup.read_text(encoding="utf-8")
            old = "`evidence/acpi/dsdt.dsl:50420`,\n`:50475`"
            assert old in text, "the first qualified pointer moved"
            writeup.write_text(text.replace(old, "`:50475`", 1), encoding="utf-8")
            self.assertRefused(run(evidence, writeup),
                               "which names no file: there is no evidence/acpi/<file>")

    def test_a_new_excerpt_is_held_to_the_quotation_rule(self):
        """The exemption is keyed on the file's shape, so it cannot widen.

        The DSDT is this repository's own committed disassembly rather than a
        fragment of upstream source at a pinned revision, and rule 3 re-derives
        the structure its pointers are used for from the file itself -- so a
        bare `:50422` into it is a locator rather than a citation, and requiring
        a quotation would be a rule about a file in this tree.

        The committed tree already relies on that (its DSDT pointers are bare),
        so the negative control is what holds the exemption open. This case
        holds the other edge: add a second `.txt` to the directory and point a
        bare pointer at it, and it is an excerpt like any other -- it has to be
        quoted, and a pointer that is not has to be refused. `is_excerpt` is
        written against the shape rather than a filename precisely so that a new
        excerpt cannot acquire the exemption by being added.
        """
        with sandbox() as (_, evidence, writeup):
            shutil.copy(evidence / ACPICA, evidence / "second-excerpt.txt")
            edit(evidence / "README.md", "- **`%s`**" % ACPICA,
                 "- **`%s`**\n- **`second-excerpt.txt`**" % ACPICA)
            # A pointer at a line of the new excerpt, with nothing quoted. The
            # line exists and is in range, so only the quotation rule can
            # redden it -- which is the point.
            edit(writeup, "`evidence/acpi/dsdt.dsl:50420`",
                 "`evidence/acpi/second-excerpt.txt:84`")
            self.assertRefused(run(evidence, writeup), "with no quoted text")

    def test_an_excerpt_nobody_cites_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            extra = evidence / "acpi-spec-field-access.txt"
            shutil.copy(evidence / ACPICA, extra)
            edit(writeup, ACPICA, "acpica-region-access-copied.c.txt", count=-1)
            # The copy has to be indexed and dated, or rules 6 and 1 fire first
            # and this case stops being about rule 2.
            edit(evidence / "README.md", "- **`%s`**" % ACPICA,
                 "- **`%s`**\n- **`acpi-spec-field-access.txt`**" % ACPICA)
            self.assertRefused(run(evidence, writeup), "is cited by nothing in the write-up")

    def test_a_citation_to_a_file_that_does_not_exist_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            # A line the write-up really cites, so the case is about the file
            # name and not about a stale anchor: `edit` refuses to no-op.
            edit(writeup, "evidence/acpi/%s:84" % ACPICA,
                 "evidence/acpi/acpi-spec-field-access.txt:84")
            self.assertRefused(run(evidence, writeup), "which does not exist")

    # --- rule 3: the identification, re-derived from the DSDT ---------------

    def test_a_hardware_id_that_is_not_INOU_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(evidence / "dsdt.dsl", '"INOU0000"', '"INOU9999"')
            self.assertRefused(run(evidence, writeup), 'Name (_HID, "INOU0000")')

    def test_a_method_that_is_not_declared_inside_INOU_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(evidence / "dsdt.dsl", "Method (MMWB, 2, NotSerialized)",
                 "Method (MMZZ, 2, NotSerialized)")
            self.assertRefused(run(evidence, writeup),
                               "MMWB is not declared `Method (` inside `Device (INOU)`")

    def test_an_MMRD_that_does_not_call_MMRW_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(evidence / "dsdt.dsl",
                 "Local1 = MMRW (Arg0, Zero, 0x02, Zero)",
                 "Local1 = MMRW (Arg0, Zero, 0x02, Arg1)")
            self.assertRefused(run(evidence, writeup),
                               "MMRD's body does not contain")

    def test_a_device_that_is_not_there_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(evidence / "dsdt.dsl", "Device (INOU)", "Device (IOUX)")
            self.assertRefused(run(evidence, writeup),
                               "no `Device (INOU)` in the committed DSDT")

    # --- rule 4: the recorded null ------------------------------------------

    def test_a_write_up_that_drops_the_null_section_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(writeup, NULL_HEADING, "## Something else entirely")
            self.assertRefused(run(evidence, writeup),
                               "no `## What this does not establish` section")

    def test_a_null_section_that_stops_naming_the_driver_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            # Every mention, not the first: the null section names the driver
            # in three separate sentences, and a rule that only checked the
            # opening one would pass on a write-up that had quietly rewritten
            # the other two into something settled.
            head, _, tail = writeup.read_text(encoding="utf-8").partition(NULL_HEADING)
            writeup.write_text(head + NULL_HEADING + tail.replace("ACPI.sys", "the driver"),
                               encoding="utf-8")
            self.assertRefused(run(evidence, writeup),
                               "does not name ACPI.sys")

    def test_a_driver_claim_outside_the_null_section_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(writeup,
                 "## The specification",
                 "## The specification\n\nIt matters that ACPI.sys agrees.\n")
            self.assertRefused(run(evidence, writeup),
                               "appears in `The specification`, outside")

    # --- rule 5: no live-run claim -----------------------------------------

    def test_an_opening_that_drops_the_no_windows_statement_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(writeup, "No Windows machine was reached,", "A Windows machine answered,")
            self.assertRefused(run(evidence, writeup),
                               "does not record that no Windows machine was reached")

    def test_an_opening_that_drops_the_no_MMRD_statement_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(writeup, "no `MMRD` was issued", "one `MMRD` was issued")
            self.assertRefused(run(evidence, writeup),
                               "does not record that no `MMRD` was issued")

    # --- rule 6: index and directory, both directions -----------------------

    def test_a_file_the_index_does_not_name_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            readme = evidence / "README.md"
            # Drop only the entry, not the prose elsewhere in the file that
            # mentions the file -- this case is about the index entry.
            for line in readme.read_text(encoding="utf-8").split("\n"):
                if line.startswith("- **`%s`**" % LINUX):
                    edit(readme, line + "\n", "")
                    break
            else:
                self.fail("no index entry for %s to remove" % LINUX)
            self.assertRefused(run(evidence, writeup),
                               "is in evidence/acpi/ but named by no entry in its README")

    def test_an_index_entry_for_a_missing_file_is_refused(self):
        with sandbox() as (_, evidence, writeup):
            edit(evidence / "README.md", "## Files",
                 "## Files\n\n- **`acpi-spec-field-access.txt`** — not committed yet\n")
            self.assertRefused(run(evidence, writeup),
                               "names acpi-spec-field-access.txt, which is not in the directory")

    # --- the shape of the refusal itself ------------------------------------

    def test_a_missing_write_up_is_a_hard_error_not_a_pass(self):
        """A checker handed nothing must not report success.

        `bash tools/run-tests.sh` documents the same failure mode one level up:
        a check that stops finding its inputs has to stop passing, or it stops
        being a check.
        """
        with sandbox() as (_, evidence, _):
            result = run(evidence, evidence / "no-such-write-up.md")
            self.assertEqual(result.returncode, 2)
            self.assertIn("write-up not found", result.stderr)


if __name__ == "__main__":
    unittest.main()