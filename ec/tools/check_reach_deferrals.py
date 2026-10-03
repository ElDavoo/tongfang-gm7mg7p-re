#!/usr/bin/env python3
"""Every sentence crediting the cluster-citation check with holding the tree
deferring to that check's own docstring for what it does not reach.

**Why it exists.** `check_cluster_citations.py` is described in the prose
around it, and one of those descriptions drifted without anybody noticing. The
merge that taught the tool a fourth citation form also reworded a limit in its
docstring, and the sentences beside it kept asserting a reach the tool no
longer had -- so the tree carried a claim about the checker that only the
checker's own docstring could contradict, and nothing read the two together.
That is the prose-restatement failure issue #253 was about, one level up: a
fact stated in two places and held by neither.

A limit list is not decidable, so it drifts when it is copied and does not
drift when it is pointed at. This is what makes the pointed-at form the only
one the tree carries: a unit that credits the tool with holding the tree has to
say where the reach stops, and the one place that is written down is the
tool's docstring.

**What it checks.** One shape. A unit that names `check_cluster_citations.py`
*and* asserts that reach in its own running words, without pointing at the
docstring, is reported. The claim is read from running prose only: a document
quoting the sentence rather than making it -- this file's own suite has to be
able to show the wording it replaced, and the write-up about this rule has to
quote what it is a rule about -- carries it in a code span, and a rule that
fires on the text stating it is a rule everybody turns off.

**A fenced block is not exempt, and the asymmetry with the paragraph above is
deliberate.** A sentence inside a fence is still a sentence a document makes:
`check_cluster_citations.py` cuts its units inside fences for exactly that
reason, and a rule that let a claim escape by being written in a block would be
a hole in the one thing this exists to enforce. So the exemption is the inline
code span and nothing wider, and the write-up about this rule quotes in
backticks rather than in a fence. Read the other way, a fence does not make a
claim exempt either -- the pairing a reader takes from a quoted block is the
pairing the sentence makes.

A tree where no unit makes the claim at all is **failed**, not passed. A
checker whose subject has been renamed or reworded out from under it has
stopped seeing anything, and an empty set of matches is what that looks like;
the sibling checkers here guard the same hole by asserting their own suite
finds something.

**What this does not check, which is as much of the point:**

  * *What the limits are.* This reads no limit, holds no claim about the
    cluster check's reach true, and says nothing about whether a sentence that
    defers is *right* to defer. The limits are enumerated in
    `check_cluster_citations.py`'s docstring and are that tool's to keep; a
    restatement of them here would be the very thing this exists to stop, and
    a second copy is the second place to go stale.
  * *Whether the pointer is a pointer.* `DEFERS` is a word, not a parse, so it
    cuts both ways and neither cut is left unsaid. A sentence that names the
    docstring in passing -- "its docstring is out of date" -- has satisfied the
    rule without deferring, and one that says "subject to the exceptions noted
    below", or links a write-up paraphrasing the limits, defers to a reader and
    not to this. Only the tool's own docstring carries the list, which is why
    that is the one thing worth pointing at; whether a looser pointer is worth
    accepting is a judgement about how much prose the tree wants to write, not
    something a word-level rule can decide.
  * *How many places make the claim.* The property is that every one of them
    defers, and a count of them is a figure the next document invalidates.
  * *Whether the tool walks the same prose this does.* The roots and the
    sentence splitter are imported rather than copied, so the two cannot drift
    into checking different corpora, but a root the cluster check drops is a
    root this stops reading with it.

Run with no arguments to check the committed tree; `--repo` points it elsewhere;
`--quiet` prints only the verdict.
"""

import argparse
import os
import re
import sys

# The walker and the splitter, not copies of them. A claim is a sentence, and
# this corpus wraps sentences across lines, so a line-based scan misses an
# attribution that straddles a wrap -- the same reason check_capture_claims.py
# imports `units()` rather than writing a second one.
from check_cluster_citations import ROOTS, units

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

# The tool whose reach is in question, by file name. A unit has to be about
# this one: the tree describes a great many checks, and a sentence saying that
# some other tool holds the tree is not this rule's business.
TOOL = "check_cluster_citations.py"

# The claim itself, in the words the sites use. Matched against the unit with
# its code spans stripped, so a document that *quotes* the sentence is not one
# making it. The whitespace is open because `units()` joins a wrapped sentence
# with a single space and a rewrap must not turn a claim into nothing.
CLAIM = re.compile(r"holds\s+the\s+rest\s+of\s+the\s+tree", re.IGNORECASE)

# A deferral is a pointer at the tool's own docstring, and that is the only
# pointer that counts. A word is enough rather than a phrase: the claim is
# about where the reach stops, and any sentence naming that docstring is
# sending the reader to the list, whether it says "within the limits its
# docstring states" or "and see the docstring for the rest".
DEFERS = re.compile(r"\bdocstrings?\b", re.IGNORECASE)

# Inline code spans, for the reason CLAIM is matched against the stripped unit.
# The write-up about this rule has to show the sentence this one replaced, and
# a document shows a sentence it is quoting in a code span; matching the raw
# text would make the explanation of the rule fail on the rule. This file's own
# docstring does not need the exemption -- it describes the claim without making
# it -- and `test_check_reach_deferrals.py` holds that, because "the docstring
# quotes the rule" is an easy thing to believe and an easy thing to stop doing.
CODE_SPAN = re.compile(r"`[^`]*`")


def prose(repo):
    """Every markdown file under the roots the cluster check walks.

    The working tree rather than `git ls-files`, the way
    `check_no_conflict_markers.py` walks, so a scratch tree with no repository
    in it can be checked at all; dot-directories are pruned instead, which is
    what keeps a `git worktree add` under `.claude/` from being read as a second
    copy of every sentence.
    """
    paths = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(repo, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                      if f.endswith(".md")]
    paths.sort()
    return paths


def check(repo, quiet=False):
    problems = []
    claimed = []

    for path in prose(repo):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        # The cheap pre-filter, for the reason the cluster check carries one:
        # most of the corpus names no cluster check at all, and reading every
        # file twice is the difference between a check a human runs and one
        # they do not.
        if TOOL not in text:
            continue
        rel = os.path.relpath(path, repo).replace(os.sep, "/")
        for lineno, unit in units(text):
            if TOOL not in unit:
                continue
            bare = CODE_SPAN.sub("", unit)
            if not CLAIM.search(bare):
                continue
            claimed.append(rel)
            if not DEFERS.search(bare):
                problems.append(
                    "%s:%d  %s\n"
                    "    This credits the cluster-citation check with holding the "
                    "whole tree without saying where its reach stops. The limits are "
                    "enumerated in the tool's own docstring and nowhere else, so a "
                    "reader who follows this sentence is told the tree is held flatly "
                    "and cannot see the exception. A limit list copied here is a "
                    "second copy to go stale; point at the docstring instead." %
                    (rel, lineno, unit.strip()[:60]))

    if not claimed:
        problems.append(
            "no unit in the tree credits %s with holding the rest of the tree\n"
            "    A rule that matches nothing has usually stopped matching: the "
            "wording it reads has been reworded, renamed or moved, and this run "
            "passes because it found no subject rather than because the subject is "
            "sound. That is \"not found by this method\" reported as a failure on "
            "purpose -- a silent pass here would be indistinguishable from the "
            "check being satisfied." % TOOL)

    for problem in problems:
        print(problem)
    if problems:
        print("%d unit(s) state the reach without deferring for it." % len(problems))
        return 1
    if not quiet:
        print("every unit crediting %s with holding the rest of the tree defers to "
              "its docstring for what it does not check; %d such unit(s) read, each "
              "of them: a pointer, not a copy of the list" % (TOOL, len(claimed)))
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
