#!/usr/bin/env python3
r"""Refuse a capture under `evidence/ec-watch/` that no `<date>-*` glob reaches.

`check_testdata_row_claims.py`'s `captures_for()` resolves a bare date in the
testdata index's third column against `evidence/ec-watch/<date>-*`. That glob is
a glob rather than a guess for two reasons, and **both are properties of the
capture root that nothing on the tree read**: every file in the root is dated in
its own filename, and the root is flat. `captures_for()`'s own docstring states
them as reasons and `docs/findings/testdata-row-claims-dated-capture.md` states
them as premises. Both are true on this tree today -- measured, with the
commands and their output, in
`docs/findings/capture-filename-date-prefix.md`. This is what holds them, and
this is a **new file rather than a mode on `check_capture_claims.py`**, per
`CLAUDE.md`'s rule: the question is about a name, not about an address in a
capture, and a second mode on that tool would put a naming refusal in the same
`--check` as prose claims.

**Two refusals, two vocabularies, one directory listing.** They are reported
separately because they are different mistakes with different fixes, and a
report that folded them into one count would say "1 problem" and leave a reader
to work out which of the two premises had stopped holding:

  * **a name carrying no `<YYYY-MM-DD>-` prefix.** The file is unreachable by
    *every* `<date>-*` glob, not merely by the dates the index happens to name.
    Nothing in the index can be a claim about it, so no claim about it is ever
    checked and no verdict is ever about it.
  * **a subdirectory in the root.** This is the second premise, and until now
    it was unchecked anywhere at all. It is a real blind spot rather than a
    hypothetical one: `glob.glob()` returns directories, so `<date>-*` would
    match one, and `carried_by()` skips anything that is not
    `os.path.isfile`. The date would resolve to a file set the tool then reads
    nothing from, and the sentence's literals would come back `missing` -- a
    red verdict caused by a directory, reported as a disagreement in the index,
    which is a defect in the prose and not a reason to change a fixture.

**The distinction this must not blur, because the two numbers look alike.** How
many files in the root *this run* reached, and how many files in the root are
*reachable at all*, are different questions with different answers. The run
reaches **6 of the 15** files here, because it globs the dates the index names
and the index is not a manifest of the capture root; the other **9** are
conforming captures no dated sentence mentions, which is normal and not a
finding. **0 of 15** is the other question -- the files no glob of this shape
can reach -- and only that one is a property of the naming convention. A line
reporting the first would read as an alarm about nine files for as long as the
corpus is heterogeneously dated, so the printed census reports the second and
this refusal is about the second too. The same line, over the same listing, is
what `check_testdata_row_claims.py` prints as its denominator, and both are
read out of `census()` here so the two cannot disagree about one directory.

**What this does not check, which is as much of the point:**

  * *Whether a capture is a capture.* This reads a directory listing. It never
    opens a file, never reads a byte, never runs a capture-producing tool, and
    never reaches the EC, a laptop or Windows. A file that satisfies the prefix
    rule and is not a capture passes here, and the question of what one of
    these files contains is `check_capture_claims.py`'s and `check_capture_encoding.py`'s.
  * *That the date is a real day.* `20\d\d-\d\d-\d\d-` is the shape, not a
    calendar; `2026-99-99-` passes. Deciding that a named day exists is not a
    naming rule, and a checker that guessed at it would be reporting a
    different question than the one that keeps the glob honest.
  * *That every capture in the root is named by the index.* It is not, and
    requiring it would be wrong: the index is a description of the testdata
    fixtures, not a manifest of the capture corpus. See the distinction above.
  * *Which date a sentence resolves to.* That is `captures_for()`'s, and it is
    unchanged. This holds the premise that function rests on; it does not
    change what a match does.

**A refusal nothing checks is a refusal with no teeth**, and the cost of this
one is written down rather than designed away: the suite asserts the committed
root has **no** non-conforming name and **no** subdirectory, which is a tripwire
rather than a floor. A future capture that arrives unprefixed turns that case
red, which is exactly what a refusal is for, and a future one that arrives
prefixed and conformant does not. Nothing about the count of files is
asserted, so the corpus is free to grow.

Usage:
    python3 ec/tools/check_capture_names.py [--check]
"""
import argparse
import collections
import os
import re
import sys

# Where a capture lives, imported rather than written out: the sibling's
# `CAPTURES` is built from the same constant, so one place decides and a second
# copy of the path is a second thing to fall out of date. See `CLAUDE.md`'s rule
# about shared sources of truth, and `check_testdata_row_claims.py`'s import of
# the same name for the same reason.
from check_capture_claims import WATCH

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ROOT = os.path.join(REPO, WATCH)

# The rule, in the one place it is written. `captures_for()` builds
# `f"{date}-*"` and globs it, so this is the exact shape that glob reaches for:
# a four-digit year, two-digit month, two-digit day, and a hyphen after it. It
# is imported by `check_testdata_row_claims.py` for its denominator line, so the
# two tools cannot come to answer differently about one directory.
PREFIX = re.compile(r"^20\d\d-\d\d-\d\d-")

# One listing, three lists. `files` is every file in the root, `undated` the
# ones `PREFIX` does not match, and `directories` the rest of the entries --
# the three the printout quotes, and the two the refusals are taken from.
#
# The split is `os.path.isfile` and not `os.path.isdir` on purpose: that is the
# predicate `carried_by()` itself uses, so `directories` is exactly the set of
# entries the reader would skip, which is what the refusal is about. A symlink
# to a file is a file to both, and a directory is the case that exists in a
# capture root; anything else lands here too, and being refused for it is the
# right side to err on.
Census = collections.namedtuple("Census", "files undated directories")


def census(root: str):
    """(files, undated, directories) from one listing of the capture root.

    `None` when the root cannot be listed at all, which is kept apart from an
    empty root on purpose: `findings.md` §14b's defect and `run-tests.sh`'s
    guard are the same mistake one level apart, and a checker that reports
    "0 of 0, every name conforms" about a directory it never read has found
    nothing rather than checked nothing.
    """
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    files = [n for n in names if os.path.isfile(os.path.join(root, n))]
    return Census(files,
                  [n for n in files if not PREFIX.match(n)],
                  [n for n in names if not os.path.isfile(os.path.join(root, n))])


def report(found: Census, where: str):
    """Print each refusal with the premise it breaks, and return which.

    Two loops rather than one over a merged list, so the two vocabularies stay
    apart in the output as well as in the code: a reader who is told one
    problem has been renamed is not left wondering which of the two premises
    stopped holding. The messages name the mechanism rather than the rule,
    because the useful half of "this is non-conforming" is *what that costs* --
    a glob that cannot reach it, or a glob that reaches a file set the reader
    then cannot read.

    `where` is the root as the caller wants it named, so the refusal can point
    at a scratch tree in a case rather than at the committed one.
    """
    problems = []
    for name in found.undated:
        print(f"{where}/{name}: carries no `{PREFIX.pattern}` prefix, so no "
              f"`<date>-*` glob reaches it and a bare date in the testdata index "
              f"cannot resolve to it. Rename it to the day it was captured.",
              file=sys.stderr)
        problems.append(name)
    for name in found.directories:
        print(f"{where}/{name}: is not a file, so `<date>-*` may match it and "
              f"`carried_by()` skips it -- the date resolves to a file set "
              f"nothing is read from, and the literals of that sentence come "
              f"back `missing` as if the index were wrong. A subdirectory is "
              f"the case that exists here; the capture root is flat, and a "
              f"capture belongs beside its siblings.",
              file=sys.stderr)
        problems.append(name)
    if problems:
        print(f"{len(problems)} capture-name refusal(s) under {where}/: the "
              f"dated-capture glob is a glob only while the root is flat and "
              f"every file in it is dated in its own filename.", file=sys.stderr)
        print("A refusal here is not a reason to widen `captures_for()`. It is "
              "a reason to fix the name.", file=sys.stderr)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Branched on, unlike the sibling's --check, because this tool is both a
    # census and a refusal and the two have different standing: read by hand it
    # is the measurement the write-up quotes, and the exit code is the one
    # thing about it that should not be a claim until asked for.
    ap.add_argument("--check", action="store_true",
                    help="fail when a capture in the root carries no date "
                         "prefix or when the root is not flat (the gate's "
                         "entry point; the default run prints the same census "
                         "and exits 0 over a readable root -- a root that "
                         "cannot be listed is a broken census, and is refused "
                         "with or without --check)")
    args = ap.parse_args()

    found = census(ROOT)
    if found is None:
        print(f"check_capture_names.py: {WATCH}/ could not be listed, so no "
              f"name was checked -- that is a broken census, not an empty one",
              file=sys.stderr)
        return 1
    problems = report(found, WATCH)

    print(f"{len(found.files)} capture(s) under {WATCH}/, "
          f"{len(found.undated)} without a date prefix, "
          f"{len(found.directories)} subdirector(ies)")
    if not problems:
        print("every capture in the root is dated in its own filename and the "
              "root is flat, so `captures_for()`'s `<date>-*` is a glob rather "
              "than a guess")
    if args.check and problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
