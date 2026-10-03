#!/usr/bin/env python3
"""Census every edit the testdata index's history holds, and report none as a verdict.

The corpus says the index "has needed a hand-repair twice, in #502 and #720",
and no measurement stood behind either the word *hand-repair* or the word
*twice*: `measure_index_repair_visibility.py` takes a **pair** of named
revisions on the command line, so what it counted was the two shas
`git log --format=%s` produced and the detector then confirmed. That is a
measurement of a named pair, and the number it published became a sentence
about the whole population. This walks the population instead. That claim was
carried at twenty sites in fifteen files, enumerated in
`docs/findings/testdata-index-repair-census.md`; this tool counts the *edits*,
and that write-up counts the *sentences*, so the two figures are not the same
measurement and are not to be added or reconciled against each other.

**What is counted, and the two populations it is counted over.** The root
index's **third** column is what a reader opens the table to read, and the
nested indexes' tables are two columns wide, so their first column holds a
**path** rather than prose and the second is prose a pointer was never lifted
from (`check_testdata_index.nested_index()`'s own docstring). A third-column
census is therefore the wrong instrument for a nested index *by construction*:
`table_cells(text, column=3)` returns `[]` for a file whose tables are headed
`file / row`, and comparing two empty lists finds the lengths equal and reports
no difference. **So there are two differently-shaped measurements here, and a
count is never mixed across them.** The reconciliation that quote needs is
stated per population or not at all.

**The unreadable guard is the reason this is not a smaller tool.** Any index
whose reader locates no table in an image that plainly carries tables is
reported as *not read by this method*, never as "no edits" — the exact failure
`measure_index_repair_visibility.repair_rows()`'s own docstring names
("a comparison that compared nothing looks exactly like one that found no
difference"). The committed nested index is that case for the column-3 reader,
which is why a census built only on `repair_rows()` would print a clean, wrong
zero over it.

**The classes a revision lands in, each counted and printed, none of them a
verdict:**

  * `edited` — a description cell (root) or a pointer cell (nested) differs
    from the first parent's. Printed with the sha, the subject, the row and
    table, the first-column token, and both cells, so the repair-or-routine
    reading can be made from this report rather than by re-running git.
  * `one-sided` — the two images do not carry the same rows: a key is present
    in one and absent from the other. Each is printed with the direction and
    the cell that exists, and it is counted on neither side **as an edit**.
    A revision that both adds a row and edits a shared row lands in `edited`
    with its additions printed beside the edit, which is the case the older
    positional comparison could only refuse as *not separable by this method*.
  * `refused` — the two images cannot be keyed against each other at all: a
    key is empty, a key is repeated inside one image, or a row has no cell in
    the column being read. That is a refusal of the **method**, not a class of
    revision, and it is not where a row addition goes.
  * `unchanged` — the revision moved the file and every row it shares with its
    first parent reads the same in both images. What moved is a first column, a
    `Feeds` cell, or prose below the table; saying so is the point, because "the
    file changed" and "the column changed" are different answers and a census
    that reported the second for a first would be overclaiming.
  * `unborn` — the file is not at the revision, or not at its first parent.
    A fact about the revision, printed with the path.
  * `no-parent` — a root commit has nothing to compare against. Not a zero.

**This tool's own wording never calls an edit a repair.** An edit is an edit;
whether one was wrong, and wrong enough to be fixed by hand, is a judgement
about the sentence, and the write-up
`docs/findings/testdata-index-repair-census.md` makes it per revision from the
cells printed here. The corpus's own number made the two the same thing, and
that is the conflation this separates.

**The one place the word can appear in the output is a commit subject, quoted
verbatim**, and it does: `99c01938`'s is *"the two index hand-repairs are
measured, and …"*. That is git's sentence about itself, not this tool's, and a
redaction would make a report unable to say what a revision was about — which is
the reason the subject is printed at all. The invariant is over the class
labels, the column names, the reasons and the closing lines, and it is asserted
as such, with the quoting pinned beside it so the exemption cannot widen
silently.

**Every negative here is "not found by this method", never a count of zero** —
the caveat `ec/annotations/registers.yaml` carries for a static scan. A
revision that does not resolve is *not measurable in this clone*, at exit 2
and with the command that failed; a path whose reader found no table is
*not read by this method*; a run that located no index at all is a broken
census and says so, because "looked at nothing" and "found nothing" are the
same output from a clean exit code.

**A full clone is required**, for `measure_index_repair_visibility.py`'s own
reason, and its `HISTORY_REQUIREMENT` is printed here unchanged rather than
restated in words that could drift from it.

**The direction is unchanged from the sibling, and does not inherit its limit.**
Both tools compare *texts*. Neither runs a checker over an old tree, so
neither depends on what today's rules say about yesterday's prose.

Usage:
    python3 ec/tools/census_index_third_column_edits.py --census
"""
import argparse
import collections
import os
import shutil
import subprocess
import sys
import textwrap

# The sibling's readers and resolvers, imported rather than copied, for the
# reason its own import comment gives: a second reader of the same table could
# come to disagree with the tool it is measuring, and `git_lines()`'s docstring
# is the repository's own statement of why a git that failed must be able to
# say so. `HISTORY_REQUIREMENT` is reused verbatim so the two tools cannot
# disagree about what a clone has to be to answer.
from measure_index_repair_visibility import (  # noqa: F401
    HISTORY_REQUIREMENT, git_lines, parent, resolve_revision, subject)

# The keyed comparison, in its own file. It is a census concept and not a mode
# on this tool: a third function bolted onto a file this size is one more thing
# a reader of the census has to hold, and the alignment is a thing the census
# reports rather than something it does to an image.
from index_keyed_rows import compare

# The index checker's own vocabulary for what a table is, the same import the
# sibling makes: `HEADER` is how the root index is located and `markdown_tables()`
# is the shape every reader here agrees on, so a change to either lands in one
# place rather than in two.
#
# `table_cells()` and `measure_index_repair_visibility.repair_rows()` are
# deliberately **not** imported here. This census no longer calls either -- the
# first because the keyed comparison reads its rows, the second because that is
# the *pair* tool's refusal and a population is not a pair -- and an import kept
# alive only for a test to reach through this namespace would be a name in this
# file that nothing here uses.
from check_testdata_index import HEADER, markdown_tables

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# The directory a self-indexed index sits under, and the pathspec that finds
# every index ever added beneath it.
#
# `:(glob)` is load-bearing and the plain spelling is not: a bare
# `ec/tools/testdata/**/README.md` matches `call-graph/README.md` and **not**
# the root index itself, so a census built on it would silently measure only
# the nested population and publish the result as a count over the root. A
# missing root index is not a zero, it is a census that looked at half a tree.
TESTDATA = "ec/tools/testdata"
POPULATION = ":(glob)%s/**/README.md" % TESTDATA

# The classes a revision can land in. The order is the order a report prints
# them in, and it is the order the questions are asked in: an edit is the answer,
# a one-sided row is a fact beside it, and a refusal is the method declining.
EDITED = "edited"
ONE_SIDED = "one-sided"
REFUSED = "refused"
UNCHANGED = "unchanged"
UNBORN = "unborn"
NO_PARENT = "no-parent"
UNREADABLE = "not-read-by-this-method"
VERDICTS = (EDITED, ONE_SIDED, REFUSED, UNCHANGED, UNBORN, NO_PARENT, UNREADABLE)

# The two classes whose token is their whole reason. Every other one carries a
# sentence beside it, because the token alone would not say it: a refusal has a
# direction and two row counts, an `unborn` has the path git could not find it
# at, and an unreadable image has the number of tables it plainly carries.
# Printing these two as well would be twelve identical sentences in a transcript
# whose whole job is that a line in it means something.
SILENT = (UNCHANGED, NO_PARENT)

# The column each population is read in, and the wording a report prints it
# with. Named rather than derived from a length so a reader of the transcript
# can see which instrument produced which number without counting columns.
#
# The numbers are the ones `index_keyed_rows.keyed_rows()` reads into each row,
# and for the nested population the measured column **is** the key column --
# which is why a nested pointer change is reported as a key removed and a key
# added rather than as an edit, and why `one-sided` prints both of them. That is
# the key's own consequence and not a special case put in here to keep a number.
ROOT_COLUMN = 3
ROOT_WORDING = "third column, the description"
NESTED_COLUMN = 1
NESTED_WORDING = "first column, the path a row names"

# A cell in a report is prose, and prose pasted unwrapped into a terminal is
# unreadable. The cells themselves are never shortened: the whole of what one
# says is the evidence, and this is where a repair-or-routine judgement is
# made from.
WRAP = 76


# What one revision of one index produced. `rows` carries the cells for an
# `edited` record and is empty for every other class, because for those the
# class and `why` between them are the whole of the answer -- there is no cell
# to show and a synthetic one would be a number with nothing behind it.
# `sides` carries the rows present on one image only, which is the whole content
# of a `one-sided` record and is printed beside an `edited` one that also moved a
# row; it is its own field rather than a row in `rows` so that the invariant
# above stays true whatever a revision did.
Revision = collections.namedtuple(
    "Revision", "path kind sha headline verdict why rows sides")

# One differing cell: where it is, what the row names, and the two texts.
Cell = collections.namedtuple("Cell", "position first before after")


def _git(*args, repo=None):
    """git, run against the repository whatever the cwd is."""
    return subprocess.run(["git", "-C", repo or REPO] + list(args),
                          capture_output=True, text=True)


def read_at(rev, path, repo=None):
    """-> (text, None) for `path` at `rev`, or (None, why) if it is not there.

    `git_lines()` for the failure half and `subprocess.run` for the bytes, and
    the split is deliberate: `git_lines()` drops empty lines so it can return
    `None` rather than `[]` for a command that did not answer, and an empty
    line is exactly what **ends** a markdown table. Reading cells out of a text
    with its blank lines removed can weld the foot of one table to the head of
    the next, and a census counting the welded rows is measuring a file this
    repository does not have.
    """
    try:
        r = _git("show", "%s:%s" % (rev, path), repo=repo)
    except OSError as exc:
        return None, "git could not be run: %s" % exc
    if r.returncode != 0:
        return None, (r.stderr.strip()
                      or ("git show %s:%s exited %d" % (rev, path, r.returncode)))
    return r.stdout, None


def has_parent(rev, repo=None):
    """-> (whether, None) for `rev` having a first parent, else (None, why).

    `parent()` cannot answer this on its own: a root commit's `rev^` and a
    clone that cannot resolve it are the same `None` carrying the same
    "no commit" reason, and this census's answers for the two are different —
    one is a fact about the revision and one is the run's own failure at exit
    2. `rev-list --parents` prints the parents a commit has and prints none
    for a root commit, so the two separate mechanically.
    """
    lines, why = git_lines("rev-list", "--parents", "-1", rev, repo=repo)
    if lines is None:
        return None, why
    if not lines:
        return None, ("git rev-list --parents -1 %s printed nothing" % rev)
    return len(lines[0].split()) > 1, None


def reader_for(path):
    """'root' or 'nested': which population a path belongs to, by its place.

    The root index is `testdata/README.md` because that is where the root is,
    not because a constant says so; anything a level below it is a
    self-indexed directory's own `README.md`. Deriving it from the path is what
    lets the next self-indexed directory pass with no edit here, the same
    argument `check_testdata_index.py`'s self-indexed clause makes.
    """
    return "root" if os.path.dirname(path) == TESTDATA else "nested"


def column_of(kind):
    """The wording a report prints this population's measured column with.

    Named per kind rather than derived from a length, for the reason
    `ROOT_COLUMN` carries: a reader of a transcript has to be able to see which
    instrument produced which number without counting columns off a table.
    """
    return ROOT_WORDING if kind == "root" else NESTED_WORDING


def measured_column(kind):
    """The cell `index_keyed_rows` reads into each row for this population."""
    return ROOT_COLUMN if kind == "root" else NESTED_COLUMN


def located(text, kind):
    """Whether the reader for this kind found the table it is there to read.

    `table_cells()` returns `[]` both for a file with no table of the shape it
    looks for and for one whose table has no data rows, and this census has to
    tell those apart. The first is a file this reader cannot read at all; a
    report that called it "no difference" would be reporting a comparison it
    did not make. The second is a real, empty answer and is not this.
    """
    tables = markdown_tables(text)
    if not tables:
        return False
    if kind == "nested":
        return True
    return any(header and header[0] == HEADER for header, _rows in tables)


def grew(before, after):
    """'grew' or 'shrank', named rather than left to the reader to derive from
    two counts.

    The direction is the half of an answer that separates the two reasons a row
    count can move: a revision that adds a fixture row and one that drops a
    fixture both change the count, and only the direction says which happened.
    `repair_rows()`'s own reason carries both counts too, so the two tools'
    reports keep meaning the same thing by the same words.

    It takes counts rather than the things counted, so the caller reads them off
    the comparison rather than re-reading the images to learn how many rows each
    had.
    """
    return "grew" if after > before else "shrank"


def classify(path, rev, repo=None):
    """-> (a `Revision`, None), or (None, why) if this clone cannot answer.

    The whole of one revision's measurement. The classes are decided in the
    order the questions are asked, because each is a reason the next one cannot
    be: a revision that does not resolve is a clone's problem before it is a
    revision's, a root commit has nothing to compare against before either
    image is read, and an image the reader cannot locate is not a comparison
    before its cells are counted.

    The last three classes are one measurement read three ways. The two images
    are keyed against each other once, and what comes back is an edit, a row
    present on one side only, or a refusal -- so a revision that did both of the
    first two is `edited` **with** its one-sided rows printed beside the edit,
    rather than the *not separable by this method* the positional comparison had
    to say about it.
    """
    kind = reader_for(path)
    sha, why = resolve_revision(rev, repo=repo)
    if sha is None:
        return None, why
    head = subject(sha, repo=repo)
    headline = f"{sha}" + (f" -- {head}" if head else "")
    apart, why = has_parent(sha, repo=repo)
    if apart is None:
        return None, why
    if not apart:
        return Revision(path, kind, sha, headline, NO_PARENT,
                        "a root commit has no parent to compare against, which "
                        "is a fact about the revision and not a count of zero",
                        [], []), None
    base, why = parent(sha, repo=repo)
    if base is None:
        return None, why
    after, why = read_at(sha, path, repo=repo)
    if after is None:
        return Revision(path, kind, sha, headline, UNBORN,
                        f"the file is not at this revision ({why})", [], []), None
    before, why = read_at(base, path, repo=repo)
    if before is None:
        return Revision(path, kind, sha, headline, UNBORN,
                        f"the file is not at the first parent {base[:8]} "
                        f"({why})", [], []), None
    if not located(after, kind) or not located(before, kind):
        return Revision(path, kind, sha, headline, UNREADABLE,
                        "the reader for this kind of index located no table "
                        "in an image that carries %d table(s); the edits are "
                        "not read by this method, which is a different answer "
                        "from there being none"
                        % len(markdown_tables(after)), [], []), None

    answer = compare(before, after, column=measured_column(kind),
                     root=(kind == "root"))
    if answer.refusal is not None:
        return Revision(path, kind, sha, headline, REFUSED, answer.refusal,
                        [], []), None
    cells = [Cell(found.where, found.key, found.before, found.after)
             for found in answer.edits]
    sides = list(answer.one_sided)
    if cells:
        return Revision(path, kind, sha, headline, EDITED, "", cells,
                        sides), None
    if not sides:
        # Every key in both images reads the same in both, and the two key sets
        # are equal -- a stronger claim than "the column is byte-identical in
        # both images", and deliberately stated as it is measured. A reorder
        # moves the column without moving any cell, and it is not an edit: the
        # reader asks what each row says, not where it sits.
        return Revision(path, kind, sha, headline, UNCHANGED,
                        f"the file changed at this revision and every row it "
                        f"shares with its first parent reads the same in the "
                        f"{column_of(kind)}; whatever moved is not in it",
                        [], []), None
    return Revision(path, kind, sha, headline, ONE_SIDED,
                    _one_sided_why(answer, kind), [], sides), None


def _one_sided_why(answer, kind):
    """The reason a revision's `one-sided` line carries, above its key list.

    Two things a reader needs before the list below it means anything: **which
    way the move went**, and **what the line is not**. The direction separates a
    revision that added rows from one that dropped them, which are the two
    reasons a key set can differ and only one of which is usually the one a
    reader is looking for. The second sentence says the class is not `edited` and
    not `refused`: an edit is over a key both images carry, so a row on one side
    only cannot be one, and the method answered rather than declined.
    """
    return (f"the two images do not carry the same rows: the key set "
            f"{grew(answer.before_rows, answer.after_rows)} from "
            f"{answer.before_rows} to {answer.after_rows} key(s), and each one "
            f"listed below is in one image and absent from the other. that is a "
            f"row added or removed rather than a {column_of(kind)} edit, and it "
            f"is counted on neither side as one")


def population(repo=None):
    """-> ([paths], None), every index ever added under `testdata/`, or
    ([], why).

    From `git log --diff-filter=A --name-only`, so the population is every
    `README.md` this repository has ever committed under the testdata root --
    **including one that has since been deleted**, which a walk of the working
    tree would have missed and a walk of `HEAD` would miss for the same reason.
    That is the issue's own question asked over the history rather than over
    the tree, and it is why this is a `git log` and not a `find`.

    Sorted, with the root first, so a report is reproducible and a reader can
    find the population's own line in it.
    """
    lines, why = git_lines("log", "--diff-filter=A", "--name-only",
                           "--format=", POPULATION, repo=repo)
    if lines is None:
        return [], why
    found = sorted({line for line in lines if line.endswith("/README.md")})
    root, nested = [p for p in found if reader_for(p) == "root"], [
        p for p in found if reader_for(p) == "nested"]
    return root + nested, None


def revisions(path, repo=None):
    """-> ([shas], None) for every commit that touched `path`.

    The whole history of one path, oldest last, so a report reads the way the
    file grew. `None` on failure for the reason `git_lines()` gives: a log that
    did not run and a log over a path this clone has never heard of are the two
    things a census most needs to tell apart, and an empty list here would make
    a file that never existed look like a file that was never edited.
    """
    return git_lines("log", "--format=%H", "--", path, repo=repo)


def census(repo=None):
    """(records, paths) over the whole population, or (None, why).

    A census that reached nothing is not a census, and the two reasons it can
    reach nothing are kept apart: no population, and a population whose history
    this clone will not answer. Both come back the same way as every other
    answer here, so `main()` has one failure branch rather than two.
    """
    paths, why = population(repo=repo)
    if why is not None:
        return None, why
    records = []
    for path in paths:
        shas, why = revisions(path, repo=repo)
        if why is not None:
            return None, why
        for rev in shas:
            found, why = classify(path, rev, repo=repo)
            if found is None:
                return None, why
            records.append(found)
    return records, paths


def wrapped(label, text, indent):
    """One cell in a report, indented and wrapped and otherwise whole.

    `textwrap` on the cell rather than on the line, so a table row's own
    leading space is not mistaken for indentation and a backticked token is
    never split across a line boundary in a way that hides it.
    """
    body = textwrap.fill(" ".join(text.split()), width=WRAP,
                         initial_indent=label, subsequent_indent=" " * len(label))
    return [indent + line for line in body.splitlines()]


def sides_lines(record):
    """The one-sided rows of `record`, one per key, in the tool's own words.

    The direction first and the **cell that exists** beside the key, because the
    cell is the evidence and the direction is what says what the key's absence
    means. A nested index's measured cell **is** its key -- its tables are two
    columns wide and the first holds the path -- so there the pair is the same
    string and printing it twice would be two copies of one fact. That is the
    population's shape rather than a formatting accident, and it is why a nested
    pointer change lands here rather than in `edited`.

    Printed under an `edited` record as well as under a `one-sided` one, because
    a revision that both edited a shared row and moved a key is measured as
    both, and the additions are half of what that revision did.
    """
    lines = []
    for side in record.sides:
        label = "%s: " % side.direction
        body = side.where + " -- " + side.key
        if record.kind != "nested":
            body += " -- " + side.cell
        lines += wrapped(label, body, "      ")
    return lines


def report(records, paths):
    """The census's whole output, and the counts a run has to be readable by.

    The `edited` block is printed in full on every run and each other revision
    on a line of its own, because the cells are what the report is for: the
    question this answers is a judgement about a sentence, and a reader who has
    to re-run git to see the sentence has not been given an answer. The other
    classes carry their reason beside them rather than in a legend, so a line
    in a pasted transcript is not a verdict that has to be looked up.
    """
    print(f"population, from `git log --diff-filter=A --name-only -- "
          f"'{POPULATION}'`: {len(paths)} index(es) ever added under "
          f"{TESTDATA}/")
    for path in paths:
        print(f"  {path} -- read in its {column_of(reader_for(path))}")
    print()

    for record in records:
        if record.verdict != EDITED:
            continue
        print(f"{EDITED}, {column_of(record.kind)} -- {record.path}")
        print(f"  {record.headline}")
        for cell in record.rows:
            print(f"    {cell.position} -- {cell.first}")
            for line in wrapped("before: ", cell.before, "      "):
                print(line)
            for line in wrapped("after:  ", cell.after, "      "):
                print(line)
        for line in sides_lines(record):
            print(line)
        print()

    counts = {verdict: 0 for verdict in VERDICTS}
    for record in records:
        counts[record.verdict] += 1
    print(f"{len(records)} revision(s) of {len(paths)} index(es): "
          + ", ".join("%d %s" % (counts[v], v) for v in VERDICTS))
    for record in records:
        if record.verdict == EDITED:
            continue
        print(f"  {record.verdict}, {column_of(record.kind)} -- {record.path}")
        if record.verdict not in SILENT:
            for line in wrapped("", record.why, "      "):
                print(line)
        for line in sides_lines(record):
            print(line)
        print(f"    {record.headline}")
    print("  an edit is not a repair: whether one was wrong is a reading of the "
          "cells above, and it is "
          "docs/findings/testdata-index-repair-census.md's, not this run's")
    print("  every negative above is 'not found by this method'. A revision "
          "that does not resolve is not measurable in this clone, at exit 2.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Accepted and not branched on, the way `check_testdata_index.py --check`
    # is: the census is the whole of what this tool does, and the flag is how a
    # reader says which mode was meant. There is deliberately no `--check`:
    # this renders no verdict, so there is nothing for a gate to call.
    ap.add_argument("--census", action="store_true",
                    help="census the whole population (the default, and the "
                         "only mode)")
    ap.add_argument("--repo", help="repository to read (default: this one)")
    args = ap.parse_args()

    if shutil.which("git") is None:
        print("  git is not on PATH, so no revision can be resolved and "
              "nothing here is measurable.", file=sys.stderr)
        print(HISTORY_REQUIREMENT, file=sys.stderr)
        return 2

    # Two shapes out of one function, so there is one failure branch. Every
    # measurement this tool makes is "git said nothing", and a git that failed
    # has to be distinguishable from a tree with nothing in it -- exit 2 with
    # the command that failed, never a count of zero.
    answer = census(repo=args.repo)
    if answer[0] is None:
        print(f"census_index_third_column_edits.py: {answer[1]}", file=sys.stderr)
        print(HISTORY_REQUIREMENT, file=sys.stderr)
        return 2
    records, paths = answer
    report(records, paths)
    if not paths:
        print("census_index_third_column_edits.py: no index was found at all, "
              "so nothing was censused -- that is a broken census, not an "
              "empty one", file=sys.stderr)
        return 1
    if not records:
        print("census_index_third_column_edits.py: the population was found "
              "and no revision of any of it is in this clone, so nothing was "
              "censused -- that is a broken census, not an empty one",
              file=sys.stderr)
        print(HISTORY_REQUIREMENT, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
