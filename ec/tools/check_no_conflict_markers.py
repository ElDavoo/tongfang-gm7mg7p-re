#!/usr/bin/env python3
"""No committed file carries a merge conflict's markers, and this is what stops it.

**Why it exists.** A merge conflict that is committed rather than resolved is
the worst outcome this repository can produce, and it is invisible by
construction: git is perfectly happy to store `<<<<<<< HEAD` in a blob, every
subsequent merge treats those three lines as ordinary content, and the file
reads as though it were written that way. `tools/README.md` carried exactly
that from `90287fec` (#36/#1089) until #1163 removed it, and nothing noticed
for the weeks in between -- not the review stage, not the gates, and not
`tools/test_readme_suite_table.py`, which asks whether every suite has a table
row and is therefore satisfied by a row sitting inside a conflict block.

It also nearly survived a second time. #1163's resolution is the correct one --
it keeps the corrected `test_walk_budget_census.py` row and re-adds the
`test_walk_flow_follow.py` row that the incoming side had dropped -- and the
mechanical resolution, `git checkout --theirs`, would have deleted a table row
and failed a suite that nothing was watching. A marker this cheap to detect
should not depend on somebody reading the diff carefully.

**What it checks.** A line beginning `<<<<<<< ` or `>>>>>>> ` in a committed
text file. Those two are unambiguous: no prose, no diff, no reStructuredText
produces them, and this tool's own docstring writes them in backticks, which is
why code spans are stripped before the match.

**The `=======` is not checked on its own, and that is deliberate.** Markdown
spells a setext heading as a line of `=` under its title, so a bare `=======`
rule would fire on a perfectly good document -- and a rule that fires on
correct text is a rule that gets deleted rather than fixed. Git only ever writes
a `=======` *between* a `<<<<<<<` and a `>>>>>>>`, so a file carrying one of
those is a file in a conflict, and the bare form is reported only in a file that
does. A genuinely half-resolved file that kept its two outer markers is still
caught, because those two are checked unconditionally.

Run with no arguments to check the committed tree; `--repo` points it elsewhere;
`--quiet` prints only the verdict.
"""

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

# The same three a checkout can put inside the repository without being
# committed. `.git` holds the conflict stages themselves, and a
# `git worktree add` under `.claude/` is a second copy of every file.
SKIP_DIRS = {".git", ".claude", "vendor"}

# Exactly seven is what git writes, but a repository can set
# `merge.conflictStyle` or a `conflict-marker-size`, and a marker that is
# longer is still a marker. Seven or more is the floor, and a setext underline
# under a short title is shorter than that far more often than not -- which is
# the second reason the bare form is not checked on its own.
START = re.compile(r"^<{7}(?:[ \t]|$)")
SEPARATOR = re.compile(r"^={7,}[ \t]*$")
END = re.compile(r"^>{7}(?:[ \t]|$)")

# Inline code spans, so a document or a tool that *names* the markers is not
# one carrying them. The rule is written in backticks in `CLAUDE.md` and in this
# file's own docstring, and matching the raw text would make the tool fail on
# the two places that state it.
CODE_SPAN = re.compile(r"`[^`]*`")

# Fenced code blocks, for the same reason one step further out: the write-up
# about this tool has to be able to quote a real conflict block to be worth
# reading, and a rule that fails on the document explaining the rule is a rule
# that gets deleted. A conflict inside a fence is not a thing git produces --
# it marks whole lines, and a fence would have to span them to hide them.
FENCE = re.compile(r"^\s*(?:```|~~~)")


def strip_fences(lines):
    """The lines outside every fenced code block, paired with their numbers."""
    inside = False
    for number, line in enumerate(lines, 1):
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            yield number, line


def tracked(repo):
    """Every committed file in the tree, as paths relative to `repo`.

    The working tree rather than `git ls-files`, so a scratch tree with no
    repository in it can be checked; `.git` and friends are pruned instead.
    """
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, repo).replace(os.sep, "/")


def read_lines(path):
    """The file's lines, or `None` if it is not text this tool can judge.

    A binary file is not a merge conflict, and a firmware image or a `.png` in
    `evidence/` must not be decoded with `errors="ignore"` and then searched for
    three ASCII sequences.
    """
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        return None


def check(repo, quiet=False):
    problems = []

    for rel in tracked(repo):
        lines = read_lines(os.path.join(repo, rel))
        if lines is None:
            continue
        numbered = list(strip_fences(lines))
        bare = [(n, CODE_SPAN.sub("", line)) for n, line in numbered]
        paired = any(START.match(t) or END.match(t) for _n, t in bare)

        for (number, line), (_n, text) in zip(numbered, bare):
            if START.match(text) or END.match(text):
                problems.append(
                    "%s:%d  %s\n"
                    "    This is a merge conflict that was committed rather than "
                    "resolved. Git stores the three marker lines as ordinary "
                    "content, so every merge after it treats them as text and "
                    "the file reads as though it were written that way. Nothing "
                    "else in the tree looks for them: `tools/README.md` carried "
                    "this from #1089 until #1163, and the suite-table check was "
                    "satisfied throughout by a row sitting inside the block."
                    % (rel, number, line.strip()[:60]))
            elif paired and SEPARATOR.match(text):
                problems.append(
                    "%s:%d  the `=======` between two conflict markers\n"
                    "    Reported only because this file also carries a `<<<<<<<` "
                    "or `>>>>>>>`: on its own a line of `=` is a markdown setext "
                    "heading, and a rule that fires on correct text is a rule "
                    "that gets deleted rather than fixed." % (rel, number))

    for problem in problems:
        print(problem)
    if problems:
        print("%d committed conflict marker(s) found." % len(problems))
        return 1
    if not quiet:
        print("no committed conflict marker: no file in the tree carries a "
              "merge's `<<<<<<<`, `=======` or `>>>>>>>`.")
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
