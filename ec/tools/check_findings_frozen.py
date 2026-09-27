#!/usr/bin/env python3
"""`docs/findings.md` is closed to new sections, and this is what holds it.

**Why the file is frozen.** `docs/findings.md` is the one file every change in
this repository is required to touch: `CLAUDE.md`'s convention is that a finding
is written up in its own file under `docs/findings/` and *summarised* in
`docs/findings.md`. For a long time that made it append-only, and an append-only
file that seven branches append to at once is not a convention, it is a lock that
nobody holds. Every simultaneous pair of changes collided at the same hunk, and
the resolution was never "merge the two findings" -- it was a page of prose
arguing about which section number was "the last section in the file", which is a
claim every subsequent append falsifies and which the file carried 51 times
against a rule it had itself written down twice.

So the numbering stops. A new finding is a new file under `docs/findings/` and
nothing else. This tool is the enforcement, because the rule is prose and prose
loses: it was written twice and violated 51 times.

**What it checks, and what it deliberately does not.**

1. **The section count.** `FROZEN_SECTIONS` is the number of `## N.` sections
   the file had when it was frozen. One more is a failure, and the new section
   is named. This is the check that would have prevented every one of the
   conflicts this file exists to describe.
2. **That the file is still append-only.** Section numbers must be strictly
   increasing, with no gaps and no repeats. A gap means a section was deleted or
   a number was reused, and a *decrease* means one was renumbered -- both of
   which invalidate the `§N` references the rest of the tree cites.

It does **not** check that the prose inside an existing section is still true.
That is a reading, and this is a count; `docs/findings.md` §4a-4d is the rule
for a claim that has stopped being true, and it is unchanged by any of this.

**Why the ceiling is a constant and not a hash of the file.** A hash would also
have to be updated by every edit to any section, which is the churn this is
removing. The section count moves only when a section is added or removed, and
that is exactly the event worth failing on.

Run with no arguments to check the committed tree; `--repo` points it elsewhere.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
FINDINGS = os.path.join("docs", "findings.md")

# The number of `## N.` sections `docs/findings.md` held when it was frozen.
#
# **This is a ceiling and a floor at once, and that is deliberate.** A ceiling
# alone catches an addition, which is the conflict; it cannot catch a deletion,
# because a file one section short is indistinguishable from one that was always
# that short -- deleting the *last* section leaves a contiguous `1..N-1` and no
# gap for the ordering check to find. Requiring the count to be *exactly* this
# catches both, and makes every edit to the file a change to this line, which is
# where a silent deletion should show up.
#
# **Raise it only to admit a summary that was already in flight when the file
# was frozen, and only with a line saying which.** A raise that admits a new
# finding is the thing this file exists to prevent, and it is otherwise
# invisible in a diff.
FROZEN_SECTIONS = 97

SECTION = re.compile(r"^## (\d+)\.\s")


def sections(text):
    """-> [(number, title)] for every `## N. title` heading, in file order."""
    out = []
    for line in text.splitlines():
        m = SECTION.match(line)
        if m:
            out.append((int(m.group(1)), line[3:].strip()))
    return out


def check(repo):
    path = os.path.join(repo, FINDINGS)
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print("cannot read %s: %s" % (FINDINGS, exc), file=sys.stderr)
        return 1

    found = sections(text)
    problems = []

    if len(found) > FROZEN_SECTIONS:
        added = found[FROZEN_SECTIONS:]
        problems.append(
            "%s carries %d sections and the frozen count is %d. The file is "
            "closed: a new finding is a new file under `docs/findings/`, and a "
            "change that needs a summary here is carrying a finding it has not "
            "written up. These are the sections past the frozen count:"
            % (FINDINGS, len(found), FROZEN_SECTIONS))
        for number, title in added:
            problems.append("    %3d. %s" % (number, title[:90]))
    elif len(found) < FROZEN_SECTIONS:
        problems.append(
            "%s carries %d sections and the frozen count is %d: %d section(s) "
            "have been removed. The sections below are the history and several "
            "are cited by number from files that predate the freeze, so a "
            "deletion breaks those citations silently. §4a-4d is for a claim "
            "that stopped being true; a section that is gone is not corrected "
            "beside itself, it is missing."
            % (FINDINGS, len(found), FROZEN_SECTIONS,
               FROZEN_SECTIONS - len(found)))

    numbers = [n for n, _ in found]
    if numbers != sorted(numbers):
        problems.append(
            "section numbers are not in increasing order, so the file is no "
            "longer append-only: %s"
            % ", ".join(str(n) for n in numbers[:20]))
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        problems.append("section number(s) used more than once: %s"
                        % ", ".join(str(n) for n in duplicates))
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        missing = sorted(set(expected) - set(numbers))
        extra = sorted(set(numbers) - set(expected))
        if missing:
            problems.append("section number(s) absent: %s"
                            % ", ".join(str(n) for n in missing))
        if extra:
            problems.append("section number(s) beyond 1..%d: %s"
                            % (len(numbers), ", ".join(str(n) for n in extra)))

    for problem in problems:
        print(problem)
    if problems:
        return 1
    print("docs/findings.md: %d section(s), append-only, and exactly the "
          "frozen count." % len(found))
    print("  the file is closed. The count is not to be raised again: the "
          "remaining summaries are in flight, and the one after them belongs in "
          "docs/findings/.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", default=REPO,
                        help="repository root (default: this one)")
    args = parser.parse_args(argv)
    return check(args.repo)


if __name__ == "__main__":
    sys.exit(main())
