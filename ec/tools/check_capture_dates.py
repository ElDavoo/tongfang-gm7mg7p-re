#!/usr/bin/env python3
r"""Hold every capture's date prefix to the dates the capture itself carries.

`check_capture_names.py`'s `PREFIX` is `^20\d\d-\d\d-\d\d-`, and that tool is
explicit that this is the right scope: "the shape, not a calendar", and "This
reads a directory listing. It never opens a file, never reads a byte." Both
hold, and both are why this is a **new file** rather than a second mode on it:
a naming guard that opens a file stops being a naming guard, and the question
here is a different one. What the naming guard leaves open is that **the
prefix is a claim about a day, and the file knows what day it is.** Not a
calendar question -- a cross-check between two committed facts, which is
decidable the way `check_capture_claims.py` finds a prose claim decidable
against a capture that does not move under a re-run.

**Three populations, and the third is the reason this is not two.** A run that
reported a verdict per capture would have to fold one of these into another,
and the fold is the defect:

  * **agrees** -- the prefix is among the dates the file carries.
  * **disagrees** -- it is not. **The only refusal here.** `--check` fails on
    this and on nothing else.
  * **cannot be checked** -- the file states no date at all, or no reader takes
    it, or it carries no prefix to check against. This is a **counted, named
    line, not a pass and not a failure**, and a merged count is what hides it:
    "15 captures, 0 problems" over a corpus in which one capture's day is
    asserted by nothing but its own filename is a green run that has said
    nothing about that capture. Every member is named on its own line, every
    run, so a human closing the gap watches the bucket shrink rather than
    having to diff an exit code.

The census on the committed root is in
`docs/findings/capture-prefix-vs-contents.md`, beside the write-up for
`docs/findings/capture-filename-date-prefix.md`'s half of this (the name).

**Set membership, not every-must-match.** The rule is that the prefix must be
*among* the dates the file carries. The stricter reading -- every date the file
carries must equal the prefix -- is declined, and the corpus is why: a capture
names its siblings. `2026-09-23-power-mode-snapshot-dc.txt:2` reads "just
before the power-mode capture in `2026-09-23-power-mode-cycle-*`", so a date
that is not the file's own day is already a shape this corpus has, and
requiring every one of them to equal the prefix would refuse a file for naming
its neighbour correctly. **The two readings give identical answers on this
tree**, where every checkable capture carries exactly one date; this is a
decision about the rule, not a measurement of a difference.

**One rule for how a date is found, not one per file type.** Dates are read out
of the whole file as text, not from the `ts` column for a `.csv` and a `#`
header for a `.txt`. Both are the same thing -- a date in the text -- and a
per-type reader is a second rule to keep in step with the corpus's file types,
which is a maintenance cost bought for nothing. Declined, and the case is
pinned rather than left here.

**What this does not check, which is as much of the point:**

  * *That a date in a filename is a real day.* `20\d\d-\d\d-\d\d` is the shape,
    not the calendar, and `2026-99-99-` conforms -- this is a cross-check, not
    a date parser, and `check_capture_names.py` already pins that half.
  * *That a capture is a capture, or that its contents are right.* It reads
    bytes and looks for a shape in them. What a capture contains is
    `check_capture_claims.py`'s; what a capture is written in is
    `check_capture_encoding.py`'s; whether it is one of these files is
    `check_capture_names.py`'s.
  * *A name carrying no prefix.* That is `check_capture_names.py`'s refusal and
    it stays that tool's. A file with no prefix is counted here too, with the
    reason named, so the run does not read as having skipped it silently --
    but it is one sentence about one file, not a second refusal with a second
    vocabulary, which is what blurring the two tools' answers would look like.
  * *A subdirectory in the root.* Never seen: the listing this walks is that
    tool's `census()`, so a directory is not in `files` and no read is
    attempted on it. It is refused there, once, in the vocabulary that owns it.
  * *Which of the two committed facts is wrong* when they disagree. A name and
    a header are both claims about a run, and a reader with the run is who can
    say which one to correct. The message says so rather than guessing.
  * *Live hardware, Windows, or the EC.* Nothing here opens a device. This is a
    read of committed bytes, one level from the data.

**A refusal nothing checks is a refusal with no teeth**, and the committed root
cannot show a disagreement -- every capture that states a day agrees with its
own prefix -- so both refusals are fired on a scratch root instead, the reason
`test_check_capture_names.py`'s docstring gives for its own two. What the
committed root carries is a tripwire: **0 disagreeing, and a denominator that is
not a figure.** Pinning `15` would turn every capture a human commits into a
failure, which is the same trade `docs/agent-pipeline.md` records against a
floor. The tripwire is the disagreement set being *empty*, and the
`captures_for()`-shaped guarantee that a future uncheckable capture shrinks the
third population without turning anything red.

**Not in any gate.** `.github/` is copied from `ElDavoo/agent-pipeline` and this
branch's token has no `workflow` scope, so no `docs/ci/agent-gates-*.patch` is
written and no workflow is touched. Both closest siblings -- `check_capture_names.py`
and `check_capture_encoding.py` -- are ungated on exactly this reasoning, and
their `tools/README.md` rows say so. `tools/run-tests.sh` is the only thing that
runs this.

Usage:
    python3 ec/tools/check_capture_dates.py [--check]
"""
import argparse
import collections
import os
import re
import sys

# Both imports are the same argument: one place decides where a capture lives
# and one place decides what its name has to look like, so this tool cannot
# come to answer differently about one directory than the two that own those
# questions. `root_listing` is the third -- it is the function that decides
# what a file in the root *is*, and a second copy of it here would be a second
# answer to that, one directory listing apart. See `check_capture_names.py`'s
# import of the same name for the same reason.
from check_capture_claims import WATCH
from check_capture_names import PREFIX, census as root_listing

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ROOT = os.path.join(REPO, WATCH)

# A date anywhere in the text. Unanchored, because the rule is "the file
# carries a day" and a capture states that day in a `ts` column, in a `#`
# header, or in a sentence about a sibling, and all three are the same claim
# about the same thing. The shape is `PREFIX`'s own without the `^` and the
# trailing `-`; the two are not written out as one from the other because
# `PREFIX` is imported and a re-derived copy is a second rule to keep in step.
DATE = re.compile(r"20\d\d-\d\d-\d\d")

# The three populations and the line each is reported on, in the order they
# are reported: from the most the run knows about a capture to the least. The
# wording is here rather than formatted around the names, because a census
# line a reader has to assemble in their head reads as one number, and this
# line's whole job is to be three.
CENSUS_LINES = (
    ("agrees", "prefix agrees with a date the file carries"),
    ("disagrees", "prefix disagrees"),
    ("unchecked", "prefix cannot be checked"),
)

# The same three as names, for `partition()`. One list rather than two, so a
# population cannot be counted without a line saying what it is.
POPULATIONS = tuple(population for population, _ in CENSUS_LINES)

# One capture's whole verdict, in one record. `prefix` is the ten characters
# `PREFIX` matched and `dates` is every `20\d\d-\d\d` the file carries; both
# are None or empty unless the capture is a disagreement, and `reason` is the
# other half of the same: it is populated exactly when `population` is
# `unchecked`, and says why rather than leaving a reader to infer it from an
# absent count.
Checked = collections.namedtuple(
    "Checked", "name prefix dates population reason")


def prefix_of(name: str):
    """The ten characters `PREFIX` matches at the front of `name`, or None.

    `PREFIX` ends in the hyphen that makes `<date>-*` a glob, so the date is
    that match with its trailing hyphen dropped -- which follows the pattern's
    own structure rather than asserting a length, so a pattern that grew a
    second separator loses it too. The case below holds this against a
    different spelling of the same ten characters, so the two readers of the
    rule cannot drift.
    """
    matched = PREFIX.match(name)
    return matched.group(0)[:-1] if matched else None


def inspect(name: str, path: str) -> Checked:
    """One capture's population, from its name and the file behind it.

    Every way this can fail to cross-check a capture lands in `unchecked` with
    a reason, never as an agreement and never as a crash: a file no reader
    takes, a file with no day in it, a name with no prefix, a file that cannot
    be opened. Each is a different fact and they have different fixes, so they
    are four reasons in one population rather than four populations -- the
    population is what the run *cannot say*, and a report that grew a bucket
    per reason would be reporting the corpus's file types as its verdicts.

    The order is the order the cheap answers are in: the prefix before the
    bytes, because a name with no prefix has nothing to hold the contents to
    and reading it would answer a question nobody asked.
    """
    prefix = prefix_of(name)
    if prefix is None:
        return Checked(name, None, [], "unchecked",
                       f"carries no `{PREFIX.pattern}` prefix, so the "
                       f"cross-check has no claim to run it against")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        # Named, not crashed, and not a fourth population. This is the shape
        # `check_capture_encoding.py` exists to refuse -- a capture is defined
        # to be utf-8 -- so the reason points at the tool that owns it rather
        # than inventing a fourth way for a run to come back not-a-pass.
        return Checked(name, prefix, [], "unchecked",
                       "is not utf-8-decodable, so no date can be read out "
                       "of it; a capture is defined to be utf-8, and this "
                       "is the shape `check_capture_encoding.py` refuses")
    except OSError as e:
        # A file that went between the listing and the read, or one this
        # process cannot open. The census is a walk of a live directory, so
        # this is reachable in principle and a traceback is the one answer
        # that helps nobody.
        return Checked(name, prefix, [], "unchecked",
                       f"could not be read ({e.strerror or e}), so no date "
                       "can be read out of it")
    dates = sorted(set(DATE.findall(text)))
    if not dates:
        return Checked(name, prefix, dates, "unchecked",
                       "carries no date to check, so the day in its name is "
                       "asserted by nothing but the name")
    if prefix in dates:
        return Checked(name, prefix, dates, "agrees", None)
    return Checked(name, prefix, dates, "disagrees", None)


def census(root: str):
    """Every capture under `root` as one `Checked` each, or None.

    `None` when the root cannot be listed, kept apart from an empty root on
    purpose and for the reason `check_capture_names.census()` gives: "0
    disagreeing, 0 unchecked" over a directory nobody read is a checker that
    passed by checking nothing, which is the `docs/findings.md` §14b defect one
    level up from the runner's own empty-discovery guard.

    The listing is `root_listing().files`, so this tool never sees a
    subdirectory and never attempts a read on one. That refusal is
    `check_capture_names.py`'s and stays there; two tools reporting the same
    entry in two vocabularies is the blurring the sibling's own docstring
    refuses at length, in a section headed "two refusals, two vocabularies".
    """
    listed = root_listing(root)
    if listed is None:
        return None
    return [inspect(name, os.path.join(root, name)) for name in listed.files]


def partition(found):
    """{population: [Checked]} -- the three buckets, from one walk.

    One walk rather than three, and one field rather than three lists, so the
    buckets cannot disagree about which capture they hold. A capture appears
    in exactly one, and the sum of the three is every file the listing gave:
    which is what stops an implementation that reports everything agreeing
    from satisfying every case with a positive one.
    """
    return {population: [c for c in found if c.population == population]
            for population in POPULATIONS}


def shown(root: str) -> str:
    """The root as a report should name it: repo-relative when it is in the repo.

    `os.path.relpath` unconditionally would hand a scratch root a
    `../../../../../tmp/...` chain, which is the shape
    `check_capture_claims.py`'s `report()` refuses to print and
    `check_capture_encoding.py`'s `_shown()` already answers. Over the
    committed root this is `WATCH` and the two spellings are one string, so
    nothing the write-up quotes moves.
    """
    repo = os.path.abspath(REPO)
    full = os.path.abspath(root)
    if full == repo or full.startswith(repo + os.sep):
        return os.path.relpath(full, repo)
    return full


def report(buckets, where: str):
    """Print the three populations, and return the disagreements.

    The refusals go to stderr and the census to stdout, as in the siblings,
    and each is a different kind of statement: a disagreement is a claim that
    something is wrong, and a population is a measurement. **`--check` reads
    only the return value**, so the third population can be printed as loudly
    as it likes and still never be the verdict -- that is the standing the
    whole third bucket exists to keep, and it is why the bucket is counted and
    named rather than left out.

    `where` is the root as the caller wants it named -- `main()` asks
    `shown()`, a case passes its own -- so a scratch tree is named as itself
    rather than as the committed one.
    """
    unchecked = buckets["unchecked"]
    disagreements = buckets["disagrees"]

    for c in disagreements:
        print(f"{where}/{c.name}: the name says `{c.prefix}` and the file "
              f"itself carries {', '.join(c.dates)}; the prefix is a claim "
              f"about a day and this file does not make it", file=sys.stderr)
    if disagreements:
        print(f"{len(disagreements)} capture(s) under {where}/ whose date "
              f"prefix disagrees with a date the file itself carries",
              file=sys.stderr)
        print("A disagreement is a defect in one of two committed facts, and "
              "which one is a fact about the run rather than about the "
              "corpus: the header and the filename are both claims about the "
              "same day.", file=sys.stderr)

    total = sum(len(buckets[p]) for p in POPULATIONS)
    print(f"{total} capture(s) under {where}/:")
    for population, said in CENSUS_LINES:
        print(f"  {len(buckets[population]):>3}  {said}")
    for c in unchecked:
        print(f"       {where}/{c.name}: {c.reason}")
    if unchecked:
        print(f"{len(unchecked)} of those cannot be cross-checked, so the day "
              f"in the name is asserted by nothing this run read; each one is "
              f"named above, and `--check` does not fail on it")
    if not disagreements:
        print(f"no capture under {where}/ has a date prefix its own contents "
              f"contradict")
    return disagreements


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Branched on for the same reason `check_capture_names.py` branches: this
    # tool is both a census and a refusal, and read by hand the exit code
    # should not be a claim until asked for. `--check` adds exactly one thing,
    # and the suite holds it: an uncheckable capture is a line either way.
    ap.add_argument("--check", action="store_true",
                    help="fail when a capture's date prefix disagrees with a "
                         "date the file itself carries (the gate's entry "
                         "point; the default run prints the same three "
                         "populations and exits 0 over a readable root -- a "
                         "capture whose date cannot be checked is a counted, "
                         "named line rather than a verdict, and a root that "
                         "cannot be listed is a broken census and is refused "
                         "with or without --check)")
    args = ap.parse_args()

    found = census(ROOT)
    if found is None:
        print(f"check_capture_dates.py: {shown(ROOT)}/ could not be listed, "
              f"so no prefix was cross-checked -- that is a broken census, not "
              f"an empty one", file=sys.stderr)
        return 1
    disagreements = report(partition(found), shown(ROOT))

    if args.check and disagreements:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
