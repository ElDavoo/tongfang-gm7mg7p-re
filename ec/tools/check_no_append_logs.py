#!/usr/bin/env python3
"""No document grows a per-merge append log, and this is what stops it.

**The shape.** A document that every merge must edit is a lock nobody holds. It
does not fail loudly on the first merge; it fails on the *second* one, in the
same hunk, and the resolution is prose about what changed rather than the two
changes themselves. This repository has now hit that three times, in three
files, and each time the same two moves produced the next occasion:

  1. `docs/findings.md` — every change had to append a summary section, so
     twenty-nine merges collided in one hunk and the file carried 51 clauses
     about which section number was "the last section in the file". Now frozen
     by `check_findings_frozen.py`.
  2. `tools/README.md` — a hand-kept total ("There are forty-nine today, 1561
     tests in all") that every merge adding a suite had to correct, in place.
     It collected **22 supersession notes over 3,522 lines and 40,240 words**,
     and the note ordinals disagreed with one another because branches numbered
     their own without seeing the others'. Now held by
     `tools/test_readme_suite_table.py`.
  3. `docs/findings/test-line-pin-census.md` — sixteen
     `## The #NNN merge, <date>` sections, one per merge that touched the
     per-pin table, 1,924 lines. Removed 2026-09-27.

**What it checks.** Two shapes, both of which are the *form* of an append log
rather than any judgement about content:

1. **A heading that is a merge.** A `##` heading naming a merge — an issue or PR
   number, or a date, in a heading whose subject is the merge rather than the
   finding. Those are per-merge sections, and they are what a document grows one
   of per merge. A heading that *cites* a merge while being about something else
   (`## Why no checker`, `## The #887 merge as a question of scope`) is a
   section of the document, not a section per merge, and is not this.
2. **A supersession note outside `docs/findings/`.** `*(Superseded …)*` is the
   marker this repository uses for "the wrong version stays visible beside the
   correction", and §4a-4d is a real rule worth keeping. It belongs in a
   findings file, where a reader expects history. In a shared document it is the
   same append log by another spelling — the second of the three cases above is
   22 of them.

**What it deliberately does not check.** It reads no figure and rules no claim
true. A document may state a count, a date or a commit hash as often as it
likes; this is about where corrections *accumulate*, not about what they say.
`docs/findings.md` states a repository-counting figure 263 times and is not this tool's
business, because it is frozen and nobody can add to it.

Run with no arguments to check the committed tree; `--repo` points it elsewhere;
`--quiet` prints only the verdict.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

# Trees with no documents in them, and the two a checkout can put inside the
# repository without being committed. The second is not tidiness: a
# `git worktree add` under `.claude/` is a second copy of every document, and
# counting it is how a figure stops being a measurement of this tree.
SKIP_DIRS = {".git", ".claude", "vendor"}

HEADING = re.compile(r"^##\s+(\S.*?)\s*$")
SUPERSESSION = re.compile(r"\*\(Superseded\b")
# Inline code spans, so a document that *names* the pattern is not one. The
# rule for the supersession note is written in `CLAUDE.md` and in this file's
# own docstring, both of which write `*(Superseded ...)*` in backticks; matching
# the raw text would make the rule fail on the two places that state it, which
# is the fastest way to a check everybody disables.
CODE_SPAN = re.compile(r"`[^`]*`")

# A heading whose subject *is* a merge. Both halves are needed: a bare `merge`
# would catch "## Why no checker mentions a merge somewhere", and a bare `#\d+`
# would catch every section that cites an issue, which is most of them.
MERGE_REF = re.compile(r"#\d+|(?:19|20)\d\d-\d\d-\d\d")
MERGE_WORD = re.compile(r"\bmerge[sd]?\b|\bmerged\b", re.I)

# A heading that is about the merge only if the merge is the whole subject.
# These are the shapes that stayed when the ones below were removed, and they
# are kept here so the tool's own boundary is visible in one place.
NOT_A_MERGE_SECTION = re.compile(
    r"^\s*(why|what|how|when|where|is|are|does|do|can|should|the measurement|"
    r"verified|left out|left open|nothing|nothing else|out of scope)\b", re.I)


def documents(repo):
    """Every markdown file in the tree, as paths relative to `repo`."""
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(".md"):
                full = os.path.join(dirpath, name)
                yield os.path.relpath(full, repo).replace(os.sep, "/")


def is_findings(rel):
    return rel.startswith("docs/findings/")


def check(repo, quiet=False):
    problems = []

    for rel in documents(repo):
        with open(os.path.join(repo, rel), encoding="utf-8") as handle:
            lines = handle.read().split("\n")

        for number, line in enumerate(lines, 1):
            heading = HEADING.match(line)
            if heading:
                title = heading.group(1)
                bare = CODE_SPAN.sub("", title)
                if (MERGE_REF.search(bare) and MERGE_WORD.search(bare)
                        and not NOT_A_MERGE_SECTION.match(title)):
                    problems.append(
                        "%s:%d  `## %s`\n"
                        "    A heading that is a merge is a section per merge, and a "
                        "document grows one of those every time it is touched — which "
                        "is what made `docs/findings.md`, `tools/README.md` and "
                        "`docs/findings/test-line-pin-census.md` the three most "
                        "conflict-prone files in the tree in turn. A section about "
                        "the merge's *effect* on a finding belongs under a heading "
                        "named for the finding." % (rel, number, title[:80]))
            if not is_findings(rel) and SUPERSESSION.search(CODE_SPAN.sub("", line)):
                problems.append(
                    "%s:%d  a supersession note outside `docs/findings/`\n"
                    "    `*(Superseded ...)*` is §4a-4d doing its job, and it belongs in "
                    "a findings file where a reader expects history. In a shared "
                    "document it is an append log by another spelling — "
                    "`tools/README.md` collected 22 of them under one sentence, over "
                    "3,522 lines." % (rel, number))

    for problem in problems:
        print(problem)
    if problems:
        print("%d append-log shape(s) found." % len(problems))
        return 1
    if not quiet:
        print("no per-merge append log: no heading is a merge, and no "
              "supersession note sits outside `docs/findings/`.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", default=REPO,
                        help="repository root (default: this one)")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the verdict line")
    args = parser.parse_args(argv)
    return check(args.repo, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
