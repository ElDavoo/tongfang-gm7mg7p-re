#!/usr/bin/env python3
"""Check the interpreter evidence behind issue #1337's write-up, and refuse the
claims that evidence does not carry.

`docs/findings/mmrd-unaligned-escape.md` closed with two named blanks: what the
ACPI specification requires of an unaligned `SystemMemory` operand, and what
the interpreter does with one. Neither could be answered from the ASL and the
vendor driver, which is why they were left blank. `docs/findings/acpi-interpreter-region-access.md`
answers what two public interpreters do, from source fetched into
`evidence/acpi/` with its provenance.

This checker reads only committed files -- the write-up, the files under
`evidence/acpi/`, and the committed DSDT. It opens no image, no network and no
vendor binary, so a reviewer can run it offline. It is **not** wired into
`.github/scripts/agent-gates.sh`: that file is copied from the pipeline
template, and wiring a checker in is a `docs/ci/agent-gates-*.patch` whose
declared set `tools/test_agent_gates_patches.py` holds -- an edit to a shared
file for a gate this issue did not ask for. The `check_dmi_descriptor.py`
arrangement is the precedent: the suite runs via `bash tools/run-tests.sh`, the
checker is invoked by hand.

**Six rules, and the reason each is here.**

  1. **Provenance completeness, per file.** Every `.txt` under `evidence/acpi/`
     carries a non-empty `Project:`, `Revision:`, `Licence:` and `Retrieved:`.
     This is the mechanical half of what the issue asked of the commit, and it
     is a rule rather than a convention because an excerpt with no revision is a
     file nobody can re-derive -- which is what
     `evidence/acpi/fetch-acpi-sources.sh` exists to make impossible.

  2. **Citations resolve, and resolve to the line the write-up quotes.** A
     citation in the write-up is written as

         `evidence/acpi/<file>:NNN` — `<the text of that line>`

     and this requires the `<file>` to hold that text at that line. It is a
     containment test with a floor on the quoted length, not equality: quoting
     the source's own indentation inside a backtick span in the middle of a
     sentence would be a formatting rule wearing a check's clothes, and the
     floor is what stops the loosening from being "matches anything". The check
     is on the *quoted text*, not on the number, which is
     `ec/tools/check_citation_lines.py`'s principle applied to a new pair: a
     rank is not an identity, so an excerpt regenerated at a newer revision
     reddens every citation whose line moved rather than leaving a sentence
     that reads correctly and means the wrong line. Both directions are
     checked -- a citation that does not resolve is a failure, and so is an
     excerpt under `evidence/acpi/` that nothing in the write-up cites, which
     is how an evidence file that was fetched and then quietly stopped
     carrying anything gets noticed.

  3. **The identification is re-derived from the committed DSDT.** The write-up
     says `MMRW`/`MMRB`/`MMRD`/`MMWB`/`MMWD` are `Method (` declarations in the
     body of `Device (INOU)` with `_HID "INOU0000"`, and that `MMRD` is a call
     to `MMRW`. That is the load-bearing structural fact in the write-up -- it
     is what makes the specification an AMI extension document rather than the
     core one -- so it is measured against `evidence/acpi/dsdt.dsl` rather than
     asserted. The prose judgement that follows from it (that this is AMI's
     Aptio utility set) is not checked; that is a reading, and a reading is
     review's to accept or not.

  4. **The recorded null is present and shaped.** The write-up carries a
     `## What this does not establish` section, it names `ACPI.sys`, and that is
     the only section in which `ACPI.sys` appears. The two public interpreters
     are not the machine's interpreter, and a write-up that quietly drops the
     difference is the overclaim the whole issue is disciplined against -- so a
     dropped null fails, and so does an `ACPI.sys` claim smuggled into a
     section that reads as settled.

  5. **No live-run claim.** The write-up's opening records that no Windows
     machine was reached and that no `MMRD` was issued. Nothing here can run on
     the hardware, ever; a write-up whose opening implies otherwise is a failure
     this repository has had to retract from before.

  6. **Index and directory agree, both directions.** Every file under
     `evidence/acpi/` is named in `evidence/acpi/README.md`, and every name in
     that README is a file that exists. Mirrors `ec/tools/check_testdata_index.py`,
     which is the same invariant over the other self-indexed directory, and
     holds in both directions because each direction is a different failure.

**What this does not check, which is as much of the point.** Nothing here
establishes what this machine's Windows `ACPI.sys` does -- it is a closed-source
Microsoft driver, it is not in the tree, and no reading of a public interpreter
is a reading of it. Rule 4 exists to keep that gap *stated* rather than to
close it. Nor does anything here establish that the excerpts are what upstream
still says; `evidence/acpi/fetch-acpi-sources.sh` does that, and it needs the
network, so it is not a gate either.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

DEFAULT_WRITEUP = os.path.join(
    REPO, "docs", "findings", "acpi-interpreter-region-access.md")
DEFAULT_EVIDENCE = os.path.join(REPO, "evidence", "acpi")
DEFAULT_DSDT = os.path.join(DEFAULT_EVIDENCE, "dsdt.dsl")

# Rule 1. `Project:` is here beside the other three because a revision and a
# licence are both about *whose* text this is, and an excerpt that names a
# revision without naming the project is citable to nobody.
PROVENANCE_FIELDS = ("Project", "Revision", "Licence", "Retrieved")
# The fields are space-padded (`Licence      : ...`) to line their values up, so
# the colon is allowed either side of the padding. They are required to be
# indented, which is what keeps a prose sentence beginning with one of these
# words from being read as a field.
FIELD_RE = re.compile(r"^[ \t]+(%s)[ \t]*:[ \t]*(\S.*?)[ \t]*$"
                      % "|".join(PROVENANCE_FIELDS), re.MULTILINE)

# Rule 2. The citation form, and the excerpt line prefix
# `fetch-acpi-sources.sh` writes (`  NNNNN: text`). The prefix is stripped off
# before comparison, so what is checked is the quoted source line and not the
# line number the excerpt happens to be numbered with. The separator is a dash
# of either spelling because the write-up is prose and an em dash is what it
# reads with; requiring one kind would be a formatting rule wearing a check's
# clothes.
CITATION_RE = re.compile(
    r"`evidence/acpi/(?P<file>[\w.\-]+):(?P<line>\d+)`\s+(?:--|—|–)\s+"
    r"`(?P<text>[^`]+)`")
LINE_PREFIX_RE = re.compile(r"^\s*\d+:\s?")
# The quoted text is required to *appear in* the line rather than to equal it,
# with a floor on its length. Requiring equality would make the write-up quote
# the source's own indentation -- four spaces, or a tab in the kernel copy --
# inside a backtick span in the middle of a sentence, which is a formatting rule
# wearing a check's clothes: it gets edited to pass rather than read. The floor
# is what keeps the loosened comparison from being a comparison anything passes;
# `if` is not a citation.
MIN_QUOTED = 12

# Rule 3. `Device (INOU)` and the five methods, by name. The indentation is
# part of the rule rather than a formatting habit: `Device (INOU)` sits at eight
# spaces and its body at twelve, so "inside the body" is decidable from the
# committed text without a parser.
INOU_RE = re.compile(r"^(\s*)Device \(INOU\)\s*$")
HID_RE = re.compile(r'Name \(_HID, "INOU0000"\)')
METHOD_NAMES = ("MMRW", "MMRB", "MMRD", "MMWB", "MMWD")
METHOD_RE = re.compile(r"^(\s*)Method \((%s)," % "|".join(METHOD_NAMES))
MMRD_CALL = "Local1 = MMRW (Arg0, Zero, 0x02, Zero)"

# Rule 4.
NULL_HEADING = "What this does not establish"
HEADING_RE = re.compile(r"^##+ (.*?)\s*$", re.MULTILINE)
ACPI_SYS = "ACPI.sys"

# Rule 5. Phrases rather than a whole opening, so the sentence can be worded
# naturally; both must appear in the block above the first `##` heading.
NO_WINDOWS_RE = re.compile(r"No Windows[^\n]*\breached\b")
NO_MMRD_RE = re.compile(r"no `MMRD` was issued")

# Rule 6. A backticked token that looks like a file in this directory.
README_TOKEN_RE = re.compile(r"`([^`]+)`")


class Report:
    """The refusals, in the order they are checked.

    Every failure names the file and what was wrong with it, because a checker
    that says "failed" without saying what it wanted has cost more time than it
    has saved.
    """

    def __init__(self) -> None:
        self.failures: list[str] = []

    def fail(self, rule: str, message: str) -> None:
        self.failures.append("rule %s: %s" % (rule, message))

    def check(self, rule: str, ok: bool, message: str) -> bool:
        if not ok:
            self.fail(rule, message)
        return ok


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def evidence_files(evidence: str) -> list[str]:
    """The quoted-evidence files -- everything a citation can name."""
    return sorted(
        name for name in os.listdir(evidence)
        if name.endswith(".txt") and os.path.isfile(os.path.join(evidence, name))
    )


def rule_provenance(report: Report, evidence: str) -> None:
    names = evidence_files(evidence)
    if not report.check("1", names, "%s holds no .txt excerpt to check" % evidence):
        return
    for name in names:
        path = os.path.join(evidence, name)
        text = read(path)
        found = {key: value for key, value in FIELD_RE.findall(text)}
        for field in PROVENANCE_FIELDS:
            if field not in found:
                report.fail("1", "%s carries no `%s:` line, or it is empty" % (name, field))


def rule_citations(report: Report, writeup: str, evidence: str) -> None:
    cited: set[str] = set()
    for match in CITATION_RE.finditer(writeup):
        name, number, quoted = match.group("file"), int(match.group("line")), match.group("text")
        path = os.path.join(evidence, name)
        if not os.path.isfile(path):
            report.fail("2", "cites evidence/acpi/%s, which does not exist" % name)
            continue
        lines = read(path).split("\n")
        if not 1 <= number <= len(lines):
            report.fail("2", "cites evidence/acpi/%s:%d, which has %d lines"
                        % (name, number, len(lines)))
            continue
        actual = LINE_PREFIX_RE.sub("", lines[number - 1]).rstrip()
        if len(quoted) < MIN_QUOTED or quoted not in actual:
            report.fail(
                "2",
                "cites evidence/acpi/%s:%d as %r, which that line does not contain "
                "(it is %r)" % (name, number, quoted, actual),
            )
            continue
        cited.add(name)

    present = set(evidence_files(evidence))
    for name in sorted(present - cited):
        report.fail("2", "evidence/acpi/%s is cited by nothing in the write-up" % name)
    if report.check("2", cited, "the write-up cites no evidence/acpi line at all"):
        return


def rule_identification(report: Report, dsdt: str) -> None:
    lines = dsdt.split("\n")

    device = None
    for number, line in enumerate(lines, start=1):
        match = INOU_RE.match(line)
        if match:
            device = (number, len(match.group(1)))
            break
    if not report.check("3", device, "no `Device (INOU)` in the committed DSDT"):
        return

    device_line, device_indent = device
    # The opening `{` sits at the device's own indent, so the body is what
    # follows *that* line at a deeper indent, up to the first line back at the
    # device's own indent or shallower. Starting the scan at the declaration
    # would stop on the brace and find an empty device, which is why the brace
    # is stepped over rather than treated as the end of the body.
    opened = next((n for n, text in enumerate(lines[device_line:], start=device_line + 1)
                   if text.strip().startswith("{")), None)
    if not report.check("3", opened is not None,
                        "`Device (INOU)` is not followed by an opening brace"):
        return
    body: list[tuple[int, str]] = []
    for number, line in enumerate(lines[opened:], start=opened + 1):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= device_indent:
            break
        body.append((number, line))

    if not report.check("3", body, "`Device (INOU)` has an empty body"):
        return

    hid_lines = [n for n, text in body if HID_RE.search(text)]
    report.check("3", hid_lines,
                 "no `Name (_HID, \"INOU0000\")` in the body of `Device (INOU)`")

    declared = {m.group(2) for _, text in body
                for m in [METHOD_RE.match(text)] if m}
    for name in METHOD_NAMES:
        report.check("3", name in declared,
                     "%s is not declared `Method (` inside `Device (INOU)`" % name)

    mmrd = next((n for n, text in body if METHOD_RE.match(text)
                 and text.split("(")[1].startswith("MMRD,")), None)
    if report.check("3", mmrd is not None,
                    "no `Method (MMRD,` inside `Device (INOU)`"):
        assert mmrd is not None
        end = next((n for n, text in body if n > mmrd and text.strip() == "}"), None)
        block = lines[mmrd - 1:end] if end else lines[mmrd - 1:]
        report.check("3", any(MMRD_CALL in line for line in block),
                     "MMRD's body does not contain `%s`" % MMRD_CALL)


def sections(text: str) -> list[tuple[str, str]]:
    """`(heading, body)` for each `##` section, and the block above the first.

    The preamble is returned under an empty heading, because rule 5 is about it
    and rule 4 is not -- a mention of `ACPI.sys` while framing what the work is
    about is not a claim, and the preamble is where framing goes.
    """
    marks = [(m.start(), m.group(1)) for m in HEADING_RE.finditer(text)]
    if not marks:
        return [("", text)]
    out = [("", text[:marks[0][0]])]
    for index, (start, heading) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else len(text)
        out.append((heading, text[start:end]))
    return out


def rule_recorded_null(report: Report, writeup: str) -> None:
    parsed = sections(writeup)
    names = [heading for heading, _ in parsed if heading]
    if not report.check("4", NULL_HEADING in names,
                        "no `## %s` section" % NULL_HEADING):
        return
    for heading, body in parsed:
        if not heading:
            continue
        if heading == NULL_HEADING:
            report.check("4", ACPI_SYS in body,
                         "the `## %s` section does not name %s" % (NULL_HEADING, ACPI_SYS))
            continue
        if ACPI_SYS in body:
            report.fail("4", "%s appears in `%s`, outside the `## %s` section"
                        % (ACPI_SYS, heading, NULL_HEADING))


def rule_no_live_run(report: Report, writeup: str) -> None:
    preamble = sections(writeup)[0][1]
    report.check("5", bool(NO_WINDOWS_RE.search(preamble)),
                 "the opening does not record that no Windows machine was reached")
    report.check("5", bool(NO_MMRD_RE.search(preamble)),
                 "the opening does not record that no `MMRD` was issued")


def rule_index(report: Report, evidence: str) -> None:
    readme = os.path.join(evidence, "README.md")
    if not report.check("6", os.path.isfile(readme),
                        "%s does not exist" % readme):
        return
    # A backticked token naming a file in this directory: no path separator, a
    # known extension, and not a leading dot -- which is what keeps prose about
    # "the `.c.txt` excerpts" from being read as a claim that a file called
    # `.c.txt` is missing.
    tokens = {t for t in README_TOKEN_RE.findall(read(readme))
              if "/" not in t and not t.startswith(".")
              and t.endswith((".txt", ".dsl", ".sh", ".md"))
              and t != "README.md"}
    on_disk = {n for n in os.listdir(evidence) if n != "README.md"}
    for name in sorted(on_disk - tokens):
        report.fail("6", "%s is in evidence/acpi/ but named by no entry in its README" % name)
    for name in sorted(tokens - on_disk):
        report.fail("6", "evidence/acpi/README.md names %s, which is not in the directory" % name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--writeup", default=DEFAULT_WRITEUP,
                        help="the findings write-up to check")
    parser.add_argument("--evidence", default=DEFAULT_EVIDENCE,
                        help="evidence/acpi/ to check")
    parser.add_argument("--dsdt", default=None,
                        help="the committed DSDT (default: <evidence>/dsdt.dsl)")
    args = parser.parse_args(argv)

    dsdt = args.dsdt or os.path.join(args.evidence, "dsdt.dsl")
    report = Report()
    for path, what in ((args.writeup, "write-up"), (dsdt, "DSDT")):
        if not os.path.isfile(path):
            print("FATAL: %s not found: %s" % (what, path), file=sys.stderr)
            return 2

    rule_provenance(report, args.evidence)
    rule_citations(report, read(args.writeup), args.evidence)
    rule_identification(report, read(dsdt))
    rule_recorded_null(report, read(args.writeup))
    rule_no_live_run(report, read(args.writeup))
    rule_index(report, args.evidence)

    if report.failures:
        print("FAIL: %d problem(s)" % len(report.failures), file=sys.stderr)
        for failure in report.failures:
            print("  %s" % failure, file=sys.stderr)
        return 1

    print("OK: evidence/acpi/ is cited, dated, licensed, and the write-up's")
    print("    identification re-derives from the committed DSDT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())