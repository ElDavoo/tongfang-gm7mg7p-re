#!/usr/bin/env python3
"""Hold the corrected checkout-depth sites by value, in the table the suite reads.

Four sites in two tools were corrected in #1009, and `check_history_checkouts.py`
finds the five sentences they now occupy. What held them was a **count** and a
**set**: `len(sites) >= 4`, and `{rel for rel, ... in sites} == set(PROSE_FILES)`.
Both survive a site going missing. The tree holds five, so five-to-four is green,
and `prose_sites()` iterates `PROSE_FILES` itself, so the set of files it found
is a *subset* of the one it is compared against by construction and the assert
can only fire on a file that is not in `PROSE_FILES` -- which is the one edit
that takes a corrected site out of the checker's reach. This is the shape
`docs/findings/history-checkout-claims.md` says the suite exists to close, *"a
checker that has quietly stopped finding anything is indistinguishable from one
that is working"*, and it was open in it.

**The identity is a file and a fragment of the sentence, not a line.** A line
needs a stated rule for the drift, and the comment above `HISTORY_REQUIREMENT`
is the case in point: it has been repointed repeatedly this month, which the
#1030 filing records. A fragment does not, which is the argument
`ec/tools/check_citation_lines.py:18-22` makes at greater length for a rank into
a generated CSV: hold the address, not the number. A fragment is also what
survives a rewrap, and two of the five sites are Python string constants whose
raw text carries `\\n` escapes and a `" "` seam that leaves three spaces where
two source lines meet. Every match is therefore made against
`" ".join(readable(sentence).split())` -- the text the report prints, run
together -- so rewrapping the comment around a claim is not a change to its row.
`squash()` is that one line and nothing else, and the suite's rewrap control is
the executable form of the claim.

**Every row is file-scoped, and that is load-bearing.** The two tools' two
`HISTORY_REQUIREMENT` sentences both carry the phrase *"which is what ci.yml's
`workflows` job uses"* -- one in each file -- so a fragment taken from that
shared wording would match a sentence in both, and a matcher that ignored the
file would hold two sites with one row. Rows 3 and 4b are each written to start
*after* the shared phrase, so the file scope is what makes that necessary rather
than lucky, and it is also what lets the two tools keep their own wording of one
fact, which `history-checkout-claims.md` declines to unify with a reason. Each
row matches exactly one site on the committed tree, which is what `main()` prints
and what the suite's committed-tree case asserts.

**Four sites, five sentences, and the two are named separately here** so they
cannot be conflated again. #1009 fixed four *sites*; the corrected sites occupy
five *sentences*, because the sibling's replacement comment is a depth claim
about `ci.yml` in its own right. `SITES` below is five rows long for four sites.

**Two directions are checked, and the count checked neither.** A row no site
matched is a corrected site this reader is no longer finding -- the hole the
`>= 4` floor and the file-set comparison both left open. A site no row matched
is a sixth depth claim nothing holds, and without the second direction the table
is a floor the other way and a tool that grows a claim gets no sentence about
it. The cost is one row when a claim legitimately grows, and the message says
exactly that. A third and a fourth are the two "more than one" cases, and they
are transposes: a row matching more than one site is a row carrying more than
one sentence of its file, a site matched by more than one row is two of the
file's rows landing on one sentence, and #1030 asked for the second of those
("a site matching two rows -- reported as a bug in the table, not as a drift").
Both are a fault in this table rather than a corrected site going missing, and
each message names only what it detected: naming the other transpose in a
message that cannot see it is how the second of the two was documented for a
while without being implemented.

**"Not found by this method", never "removed" or "absent."** The matcher cannot
tell a deleted sentence from a reader that stopped finding one, which is the same
blind spot the tool's own docstring and `ec/annotations/registers.yaml`'s caveat
both name, so every message here is worded as what the method found.

**Regenerating a row.** Run this file after editing either tool's prose: it
prints every row beside the line it matched, and every site no row matched with
its sentence, so a fragment is copied out of the output rather than typed off a
line number a rewrap has since moved. That is also the only safe way to write
one: `readable()` strips its own `TRIM` -- the source quoting, the comment
marker and the whitespace -- off both ends of a sentence, so a fragment taken
from a source sentence's opening words need not match the text the matcher sees
(`NEW_CLAIM` in the suite is a case of exactly that, and its assertion is
written the way the report prints it). The table cannot go stale for want of a
way to update it.

Usage:
    python3 ec/tools/history_checkout_sites.py
"""
import collections
import os
import sys

# The tool, imported rather than reimplemented: `readable()` decides what a reader
# of the report sees, and a second copy of it here would be a second answer to
# "which text is the sentence", which is the whole question the fragments below
# are asked about. Plain sibling import for the reason
# `check_testdata_row_claims.py` imports three of its siblings -- these tools are
# not a package, and a case that monkeypatched the reader instead would be
# testing the monkeypatch.
from check_history_checkouts import load_workflows, prose_sites, readable

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# (relpath, fragment, what it is). The `what` is not decoration: a failure that
# names only a file and a fragment of English is a message a reader has to go and
# decode, and "which of the four sites is this" is the first question of the day.
Site = collections.namedtuple("Site", "rel fragment what")

# Four corrected sites in five sentences, one row each. The fragments are
# verbatim substrings of the squashed text the report prints, and each is
# distinct *within its own file* -- the three `verify_reassembly.py` rows share
# the file and nothing else, and rows 3 and 4b are the pair the file scope exists
# for. `run this file` is how a row is checked against the tree and how a new one
# is written.
SITES = (
    Site("ec/tools/verify_reassembly.py",
         "ci.yml's `gates` job has one (`fetch-depth: 0`) and is the job that runs the gate",
         "site 1 -- the docstring's usage block, printed at the depth word's line"),
    Site("ec/tools/verify_reassembly.py",
         "the agent stages' `implement`, `fix` and `resolve` -- checks out with `fetch-depth: 0`",
         "site 2 -- the comment above `HISTORY_REQUIREMENT`"),
    Site("ec/tools/verify_reassembly.py",
         "which is what ci.yml's `workflows` job uses, though that job runs no history reader",
         "site 3 -- `HISTORY_REQUIREMENT` itself"),
    Site("ec/tools/measure_index_repair_visibility.py",
         "has been `fetch-depth: 0` since #407 (`cc2ab10d`) while its `workflows` job is default-depth",
         "site 4 -- the sibling's comment, the fourth corrected site"),
    Site("ec/tools/measure_index_repair_visibility.py",
         "has neither of them, and this tool would go on to report a count of zero over a tree it never read",
         "site 4 -- the sibling's `HISTORY_REQUIREMENT`"),
)


def squash(sentence):
    """A site's sentence as the report prints it, with its whitespace run together.

    `readable()` does the source-quoting half -- the `\\n` a string constant
    carries, a wrapped comment's own `#`, the `" "` seam between two lines of one
    string -- and leaves runs of spaces wherever two of those met. The report
    prints what is left of them and the table is held against what the report
    prints, so the squash belongs here rather than in either.
    """
    return " ".join(readable(sentence).split())


def match(sites, expected=SITES):
    """-> [[row index, ...]] per site, in `sites` order.

    A site is a five-tuple from `check_history_checkouts.prose_sites()`, read
    positionally because the tool's own tuple is named for its report and
    unpacking four of its five fields to reach the third would be noise.
    """
    hits = []
    for site in sites:
        text = squash(site[2])
        hits.append([index for index, row in enumerate(expected)
                     if row.rel == site[0] and row.fragment in text])
    return hits


def problems(sites, expected=SITES):
    """-> [str], one message per disagreement between `sites` and `expected`.

    The single thing the suite asserts on, so the committed-tree cases and the
    scratch-tree controls go through identical code and a control cannot
    demonstrate a path the suite's own assertion does not use.

    **Both directions of each disagreement, and the two "more than one" cases
    are transposes rather than halves of one.** A row no site matched and a site
    no row matched are the two drifts. A row matching two sites and a site
    matched by two rows are the same shape read the other way round, and each
    is judged on its own: the first is this row carrying more than one sentence
    of its file, the second is two of this file's rows landing on one sentence.
    Judging only the first and describing the second in its message is how #1030's
    third direction came to be *named* without being implemented -- a reader
    could not tell a table that had grown two rows for one sentence from a table
    that was correct, because nothing said so. Each message below therefore
    names what it detected and stops there.
    """
    hits = match(sites, expected)
    found = []
    for index, row in enumerate(expected):
        at = [i for i, got in enumerate(hits) if index in got]
        if not at:
            seen = sum(1 for site in sites if site[0] == row.rel)
            found.append(
                f"{row.rel}: no site carries the fragment {row.fragment!r} -- "
                f"{row.what}. {seen} site(s) were found in that file. Not found "
                f"by this method: a reader that stopped finding this site and a "
                f"sentence taken out of the file are the same thing here, and "
                f"neither is reported as absent")
        elif len(at) > 1:
            found.append(
                f"{row.rel}: the fragment {row.fragment!r} -- {row.what} -- "
                f"matches {len(at)} sites "
                f"({', '.join('%s:%d' % (sites[i][0], sites[i][1]) for i in at)}). "
                f"One row is carrying more than one sentence of its file, which "
                f"is not a corrected site going missing: either this row's "
                f"fragment is not distinct within its file and belongs to one of "
                f"the sentences it names, or that file now carries these words "
                f"twice")
    for site, got in zip(sites, hits):
        if not got:
            found.append(
                f"{site[0]}:{site[1]}: {squash(site[2])!r} matches no row in "
                f"this table -- a depth claim nothing is holding. Add a row "
                f"carrying a fragment of it")
        elif len(got) > 1:
            found.append(
                f"{site[0]}:{site[1]}: {squash(site[2])!r} is carried by "
                f"{len(got)} rows "
                f"({', '.join('%d: %s' % (i, expected[i].what) for i in got)}). "
                f"Two rows matching one sentence is a bug in this table and not "
                f"a drift in the tree: the site is still found, so nothing has "
                f"gone missing, but the rows are no longer one apiece -- their "
                f"fragments overlap here, so one of them is not naming a site "
                f"of its own. Split them, or drop the row this site is not")
    return found


def main() -> int:
    """Print the table beside what the committed tree holds, and the verdict.

    The `what` is on every line because this is the regeneration path: a reader
    who has just edited one of the two tools' comments needs to see which row
    stopped matching before they need to see the prose explaining why.
    """
    workflows, unreadable = load_workflows(REPO)
    sites = prose_sites(REPO, workflows, unreadable)
    hits = match(sites)
    print(f"history_checkout_sites.py: {len(SITES)} row(s) in the expected-site "
          f"table, {len(sites)} sentence(s) found in the two tools.")
    for index, row in enumerate(SITES):
        at = [i for i, got in enumerate(hits) if index in got]
        if not at:
            where = "NO SITE"
        elif len(at) == 1:
            where = "%s:%d" % (sites[at[0]][0], sites[at[0]][1])
        else:
            where = "%d SITES: %s" % (
                len(at), ", ".join("%s:%d" % (sites[i][0], sites[i][1]) for i in at))
        print(f"  {row.what}\n      {row.rel} -> {where}")
    for why in unreadable:
        print(f"  {why}", file=sys.stderr)
    found = problems(sites)
    for message in found:
        print(f"  FAIL {message}", file=sys.stderr)
    if found:
        print(f"history_checkout_sites.py: {len(found)} problem(s). A corrected "
              f"site is held by its file and a fragment of its sentence, so "
              f"rewrapping the comment around one is not a change to its row.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
