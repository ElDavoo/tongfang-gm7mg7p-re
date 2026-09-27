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

**Four classes per revision, each counted and printed, none of them a verdict:**

  * `edited` — a description cell (root) or a pointer cell (nested) differs
    from the first parent's. Printed with the sha, the subject, the row and
    table, the first-column token, and both cells, so the repair-or-routine
    reading can be made from this report rather than by re-running git.
  * `refused` — the two images have different row counts. `repair_rows()`
    already refuses rather than aligns and **that refusal is the separation
    between an edit and a row addition**: adding a row changes the count, so
    row additions land here automatically and are counted on neither side. A
    revision that both adds a row and edits a cell in the same table is
    **not separable by this method** and says so rather than guessing.
  * `unchanged` — the revision moved the file and the column read is
    byte-identical in both images. What moved is a first column, a `Feeds`
    cell, or prose below the table; saying so is the point, because "the file
    changed" and "the column changed" are different answers and a census that
    reported the second for a first would be overclaiming.
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
    HISTORY_REQUIREMENT, git_lines, parent, repair_rows, resolve_revision,
    subject)

# The index checker's table readers, the same import the sibling makes. Cells
# come from `table_cells()` and the whole-table shape from `markdown_tables()`,
# so a change to what a table is lands in one place.
from check_testdata_index import (  # noqa: F401
    HEADER, markdown_tables, table_cells)

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

# The five classes a revision can land in, plus the reader's own refusal. The
# order is the order a report prints them in.
EDITED = "edited"
REFUSED = "refused"
UNCHANGED = "unchanged"
UNBORN = "unborn"
NO_PARENT = "no-parent"
UNREADABLE = "not-read-by-this-method"
VERDICTS = (EDITED, REFUSED, UNCHANGED, UNBORN, NO_PARENT, UNREADABLE)

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
ROOT_COLUMN = "third column, the description"
NESTED_COLUMN = "first column, the path a row names"

# A cell in a report is prose, and prose pasted unwrapped into a terminal is
# unreadable. The cells themselves are never shortened: the whole of what one
# says is the evidence, and this is where a repair-or-routine judgement is
# made from.
WRAP = 76


# What one revision of one index produced. `rows` carries the cells for an
# `edited` record and is empty for every other class, because for those the
# class and `why` between them are the whole of the answer -- there is no cell
# to show and a synthetic one would be a number with nothing behind it.
Revision = collections.namedtuple(
    "Revision", "path kind sha headline verdict why rows")

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


def pointer_rows(text):
    """Column 1 of every data row of every table, one list per table.

    The nested reader, and the shape `nested_index()` reads off disk, done over
    a **text** so two revisions of the same file can be compared without
    extracting either. It is column 1 because that is the column a nested row's
    pointers are in; the second is prose about the case and a token lifted out
    of it is a pointer the index never made.
    """
    return [[row[0] for row in rows if row] for _header, rows in
            markdown_tables(text)]


def nested_edits(before_text, after_text):
    """-> (edited, refused) for two nested images.

    `edited` is a list of `(table number, row number, before, after)`;
    `refused` is a list of `(table number, why)`. Table by table rather than
    over the whole file, because two images with a different number of tables
    are not a comparison and a different number of rows **within one table**
    is, so a growth in table 1 does not make table 2 unmeasurable.

    The refusal carries the reason the census exists to keep: a table that grew
    may also have had a cell edited, and the two are not separable by a method
    that compares positions, so the line says that rather than reporting the
    rows it could line up.
    """
    before, after = pointer_rows(before_text), pointer_rows(after_text)
    if len(before) != len(after):
        return [], [(0, "the two images carry %d and %d table(s), so a table "
                       "number is not the same table on both sides; a table "
                       "was added or removed, which is not a pointer-column "
                       "edit, and a cell edit in the same file is not "
                       "separable from it by this method -- counted on neither "
                       "side. the pointer-column edits are not found by this "
                       "method" % (len(before), len(after)))]
    edited, refused = [], []
    for number, (old, new) in enumerate(zip(before, after), 1):
        if len(old) != len(new):
            grew = "grew" if len(new) > len(old) else "shrank"
            refused.append((number,
                            "table %d %s from %d to %d row(s), so a row number "
                            "names a different row in each; a row was added or "
                            "removed, which is not a pointer-column edit, and a "
                            "cell edit in the same table is not separable from "
                            "it by this method -- counted on neither side"
                            % (number, grew, len(old), len(new))))
            continue
        for row, (was, now) in enumerate(zip(old, new), 1):
            if was != now:
                edited.append((number, row, was, now))
    return edited, refused


def grew(before, after):
    """'grew' or 'shrank', named rather than left to the reader to derive from
    two counts.

    The direction is the half of a refusal that separates the two reasons a
    table can grow: a revision that adds a fixture row and one that drops a
    fixture both change the count, and only the direction says which happened.
    `repair_rows()`'s own reason carries both counts and is passed through
    beside this rather than reworded, so the two tools' reports keep meaning
    the same thing by the same class.
    """
    return "grew" if len(after) > len(before) else "shrank"


def classify(path, rev, repo=None):
    """-> (a `Revision`, None), or (None, why) if this clone cannot answer.

    The whole of one revision's measurement. The classes are decided in the
    order the questions are asked, because each is a reason the next one cannot
    be: a revision that does not resolve is a clone's problem before it is a
    revision's, a root commit has nothing to compare against before either
    image is read, and an image the reader cannot locate is not a comparison
    before its cells are counted.
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
                        []), None
    base, why = parent(sha, repo=repo)
    if base is None:
        return None, why
    after, why = read_at(sha, path, repo=repo)
    if after is None:
        return Revision(path, kind, sha, headline, UNBORN,
                        f"the file is not at this revision ({why})", []), None
    before, why = read_at(base, path, repo=repo)
    if before is None:
        return Revision(path, kind, sha, headline, UNBORN,
                        f"the file is not at the first parent {base[:8]} "
                        f"({why})", []), None
    if not located(after, kind) or not located(before, kind):
        return Revision(path, kind, sha, headline, UNREADABLE,
                        "the reader for this kind of index located no table "
                        "in an image that carries %d table(s); the edits are "
                        "not read by this method, which is a different answer "
                        "from there being none"
                        % len(markdown_tables(after)), []), None

    if kind == "root":
        before_cells = table_cells(before, column=3)
        after_cells = table_cells(after, column=3)
        rows, why = repair_rows(before, after)
        if why:
            return Revision(path, kind, sha, headline, REFUSED,
                            f"a row was added or removed and the table "
                            f"{grew(before_cells, after_cells)}; a cell edit "
                            f"in it is not separable from that by this method, "
                            f"and it is counted on neither side. {why}",
                            []), None
        first = table_cells(before, column=1)
        cells = [Cell("row %d" % row,
                      first[row - 1] if 1 <= row <= len(first) else "-",
                      before_cells[row - 1], after_cells[row - 1])
                 for row in rows]
    else:
        cells, refused = nested_edits(before, after)
        if refused:
            return Revision(path, kind, sha, headline, REFUSED,
                            "; ".join(why for _number, why in refused),
                            []), None
        cells = [Cell(f"table {number}, row {row}", was, was, now)
                 for number, row, was, now in cells]
    if not cells:
        return Revision(path, kind, sha, headline, UNCHANGED,
                        f"the file changed at this revision and the "
                        f"{column_of(kind)} is byte-identical in both images; "
                        f"whatever moved is not in it", []), None
    return Revision(path, kind, sha, headline, EDITED, "", cells), None


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
