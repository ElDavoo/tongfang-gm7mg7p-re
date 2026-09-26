#!/usr/bin/env python3
"""Hold `ec/tools/testdata/README.md` and the tree under it to each other.

The index is what a change greps to learn which fixture holds which grader case,
and it is written by hand. Nothing reads it -- `grep -rn 'testdata/README'` over
the suite and the gate returns two prose mentions and not one read -- so a
fixture directory with no row in it, a row naming a path that is not on disk, a
`Feeds` cell naming a tool that has been renamed, a self-indexed directory's
own table naming a listing or a CSV row that is not there, and a fixture CSV's
`evidence` cell naming a listing the real tree does not have would all land
unremarked. Those are the five places an index and a tree can disagree, which
this walks in one pass and prints each one's tally for.

The index has needed a hand-repair twice, in #502 and #720, and that is not
what these directions are for. Both were edits to a row's third column -- the
description of a case the row already named -- and this reads the first column,
the second and the nested tables, not the third. Run over both pre-repair
trees it reported 0 gaps, 0 path misses and 0 `Feeds` misses, so the "green
through both" this used to assert is now a measurement; the one nested miss it
does report names an untracked `.asm` that no revision carries, and is an
artefact of extracting history rather than a fact about either repair (issue
#978, `docs/findings/testdata-row-claims-repair-measurement.md`). It is here
for the gaps, which nothing else would have caught.

**Directory -> index.** Every immediate subdirectory of `testdata/` has to be
reachable: either the top-level index carries its name followed by a slash, or
the directory indexes itself with its own `README.md`. The second clause is not
hypothetical -- `call-graph/` is a directory the top-level table does not name,
and self-indexing it is the right call. The clause is therefore structural and
not an exemption list: the next self-indexed directory passes with no edit here,
which is what `test_check_testdata_index.py` pins with a directory name this
file has never seen.

The trailing slash is load-bearing. `0751-isolation-run/` is a prefix of
`0751-isolation-run-3blocks/`, so a bare substring test would pass the former on
the strength of the latter's row and the directory that matters most -- the one
§6 of the isolation procedure names, and the one the grader's own equality holds
`test_grade_0751_isolation.py` to -- on the strength of a row about a different
fixture. The search is over the whole index rather than the table, because that
directory is named in prose at the bottom of the file and a table-only scan
would report a gap on it.

**Index -> tree.** The first column of the `File` table, every backticked token
in it, each resolved against the disk. A row naming a path that is not there is
the same class of mistake as a fixture with no row: the index is a promise about
which files exist, and a promise that has quietly stopped being true is worse
than one that was never made.

**`Feeds`.** The second column is a tool reference and not a fixture path, so
it is a different invariant *and* a different resolution: each backticked token
is cut at its first whitespace and the name resolved against the **parent** of
`testdata/`, which is `ec/tools/` where the tools are. The cut is the whole of
the flag-suffix rule, and the `via` clause needs none of its own because its
two halves are both backticked -- reading every backticked token reads both.

**A self-indexed directory's own index.** The clause above reads a directory's
`README.md` for its *existence*; this reads what is inside it, which is the same
rule one level down in a harder shape. Those rows name a `.asm` and a
`ghidra-functions.csv` row rather than a path and nothing else, so a cell is
read as a relative path, as a `X.csv` plus one or more addresses, or as both
joined by ` + `. **Every** table in the file is walked, not the first: a table
is located by its own shape -- a `|` line immediately over a separator -- so the
next self-indexed directory needs no edit here either, the same argument the
self-indexed clause itself makes.

**The `evidence` column of a named CSV.** The one column those CSVs carry that
points at the **real** tree rather than at the fixture, so it is a third base:
the repository root, beside `ec/tools/` for `Feeds` and the self-indexed
directory for a nested `.asm`. Which CSVs are read is structural rather than an
exemption list -- they are the ones a self-indexed directory's own tables
already name, so the next self-indexed directory carrying one is covered with
no edit here, the same argument the clause above makes. The column is read **by
name** and not by position, because `evidence` is column 7 of 8 in one of the
two committed CSVs and column 10 of 12 in the other, and a position would be
right on the day it landed and wrong after the next edit. A cell is
`;`-separated, because one committed row names a listing and its `.c` side by
side. Two shapes are `unresolved` and neither is a failure: a named CSV with no
`evidence` column at all, and a token whose shape no path rule reads. The first
is a fact about the *CSV* rather than about a cell, so it is counted against
`evidence_csvs` and printed on a line of its own rather than against the token
tally: the two have to subtract from the same population, or a CSV with no
column to read would take one more off the resolved count than it ever added
to it. An **empty** value is neither -- it yields no pointer at all, the same
limit the first-column rules carry, because a rule invented here would be a
parser guessing.

**What this does not check, which is as much of the point:**

  * *Whether a fixture is what its row says it is.* This is index/tree
    agreement and nothing else. A green run means the two files point at each
    other consistently; it says nothing about whether a CSV constructs the shape
    the third column describes, which is what a reader opens the file for.
  * *A token whose shape matches no rule below.* `unresolved` is counted and
    printed and is not a failure: a shape this tool cannot read is "not
    resolved by this method", never "absent", the same caveat
    `ec/annotations/registers.yaml` carries for a static scan. The rules are in
    `resolve()`, `resolve_tool()` and `evidence_pointers()`, and falling off the
    end of them is the calibration line made mechanical rather than a sixth
    verdict that guesses.
  * *The `...` abbreviation, beyond the glob.* The table writes
    `` `0751-isolation-example-fixed-load-0700-07ff.csv` + `...-0400-045f.csv` ``,
    and resolving the second token by splicing the first one's stem would
    produce a double-dash name that is not on disk. It is resolved by glob
    instead -- `...-0400-045f.csv` becomes `*-0400-045f.csv` -- so an
    abbreviation that names nothing real is a `missing`, which is the honest
    answer, and one that names something real is a `resolved` whichever
    directory it turns out to be in.
  * *Top-level files with no row.* Direction 1 is about directories, which is
    what the issue asks for. The twenty loose `*.csv`/`*.txt` files beside the
    table are covered in the other direction, as rows, and a *new* one added
    beside them is not caught until a row names it.
  * *The reverse direction for any of the three sources added later.* A `.py`
    under `ec/tools/` carrying no `Feeds` row; a committed `.asm` or CSV row
    carrying no table row in its directory's `README.md`; and a real
    `ec/decompiled/**` listing that no `evidence` cell names. All three are the
    "top-level files with no row" gap above, in the directions added later, and
    all three are declined for the same reason.
  * *Program/scope identity in the nested CSV lookup.* A row that exists at the
    address resolves even when it says something other than the cell claims.
    The invariant is "the row the index names is in the file it names", and
    "and it says the right thing" is a question about the fixture with a
    different owner. The cost is worth stating: a typo to an address that
    happens to exist in that CSV passes.
  * *A row whose cell holds no backticked token, and an `evidence` cell holding
    no value.* Both yield no reference at all, which is the shipped
    first-column behaviour. A rule invented here would be a parser guessing, so
    the limit is stated rather than met.
  * *Prose below the table, in the index -> tree direction.* The whole file is
    searched for a directory name; only the table's two path columns are
    resolved against the disk. A path mentioned in prose is neither held to the
    disk nor reported as unchecked, which is the one place a reader could take
    silence for agreement.

All five tallies print whether or not they found anything, because a run that
checked nothing and a run that found nothing look the same from the exit code
alone. There is no floor on any of them, for the reason
`docs/agent-pipeline.md` records about gates: an expected count turns every
added fixture into a failure. The suite asserts non-emptiness instead, which is
the assertion that is true of the tree rather than of the tool.

Usage:
    python3 ec/tools/check_testdata_index.py [--check]
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTDATA = os.path.join(HERE, "testdata")
INDEX = os.path.join(TESTDATA, "README.md")
# The third base, and a global read at call time rather than a `repo=REPO`
# default: the suite's `run_tool()` patches it the way it patches `TESTDATA`,
# and a default would bind at def-time and make that patch inert.
REPO = os.path.join(HERE, os.pardir, os.pardir)


def repo_path(path: str) -> str:
    """Repository-relative, so a report can be pasted into an editor.

    A `relpath` over a path the caller already made relative resolves against
    the working directory instead, which turns `ec/tools/testdata/README.md`
    into a chain of `..` on any run from outside the repository root. The base
    is the `REPO` global rather than a fresh `HERE/../..`, so a run pointed at a
    scratch tree reports scratch-relative paths and not a chain of `..` out of
    an unrelated root.
    """
    return os.path.relpath(path, REPO)


# The table is located by its own first header cell rather than by a line
# number, so an edit above it cannot quietly move the scan off it and leave a
# green run that read no rows at all.
HEADER = "File"

# Every backticked token in the cell, not one. `tools/test_readme_suite_table.py`
# fullmatches a single path per cell, which is right for a one-path-per-row
# table and wrong for this one: these cells hold several paths joined by ` + `
# or `, `, and a fullmatch would read the two-token rows as no row at all.
TOKEN = re.compile(r"`([^`]+)`")

# Directories Python leaves behind, and dot-names, which are not part of the
# index's subject matter. The rule is about what a reader of the index sees, so
# what a build left behind is not in it.
SKIP = ("__pycache__",)

# The three verdicts, kept as strings because they are what a report prints and
# a test asserts against. Only `missing` fails.
RESOLVED, MISSING, UNRESOLVED = "resolved", "missing", "unresolved"

# What one run found, in the shape the closing line of the docstring wants: the
# problem lists, one per source, and the tallies a caller prints so that a run
# which reached nothing does not look like a run that found nothing. The three
# directory counts are separate fields rather than a length, because the second
# line of the output is about how the directories are indexed rather than about
# how many there are. The list fields are flat rather than grouped by source
# because the suite asserts this namedtuple positionally, and a grouping would
# rewrite that for no reader's benefit.
Result = collections.namedtuple(
    "Result",
    "gaps missing unresolved feeds_missing feeds_unresolved nested_missing "
    "nested_unresolved evidence_missing evidence_unresolved "
    "evidence_columnless directories named "
    "self_indexed rows tokens feeds_cells feeds_tokens nested_indexes "
    "nested_tables nested_rows nested_checks evidence_csvs evidence_cells "
    "evidence_tokens")

# What one self-indexed directory's own README named, over the same three
# verdicts and carrying the same `where`/`token`/`note` triple as every other
# list here, so `check()` can add them up without a second shape of answer. The
# `evidence_` fields are the totals over the CSVs that directory's tables name.
Nested = collections.namedtuple(
    "Nested", "tables rows checks missing unresolved evidence_csvs "
    "evidence_cells evidence_tokens evidence_missing evidence_unresolved "
    "evidence_columnless")

# What one named CSV's `evidence` column named, in that same shape. A cell and a
# token are counted apart because a cell is `;`-separated and the one
# multi-pointer cell in the committed tree is the reason: a tally taken per cell
# would read 10 there and 11. `columnless` is kept out of `unresolved` for the
# reason the module docstring gives: it is a fact about the CSV, so it counts
# against `tokens` nowhere and `tokens - missing - unresolved` cannot go below
# zero because of a file this tool could not read a column out of.
Evidence = collections.namedtuple(
    "Evidence", "cells tokens missing unresolved columnless")


def fixture_dirs(root):
    """The immediate subdirectories of `root` the index is about."""
    for name in sorted(os.listdir(root)):
        if name.startswith(".") or name in SKIP:
            continue
        if os.path.isdir(os.path.join(root, name)):
            yield name


def reachable(name, root, index):
    """`self`, `index` or None: how `name` is indexed, if it is at all.

    The clause order is the issue's, not this tool's taste: an index that names
    the directory and a directory that indexes itself are both answers, and a
    directory carrying both is not a gap either way.
    """
    if os.path.isfile(os.path.join(root, name, "README.md")):
        return "self"
    if name + "/" in index:
        return "index"
    return None


def row_cells(line):
    """The cells of a `|` line, or nothing at all for any other line.

    Trailing empties are dropped so that a well-formed `| a | b |` and a
    truncated `| a | b` are the same two cells, which is what lets the separator
    test below be a statement about every cell rather than about the first.
    """
    if not line.startswith("|"):
        return []
    cells = [cell.strip() for cell in line.split("|")[1:]]
    while cells and not cells[-1]:
        cells.pop()
    return cells


def markdown_tables(text):
    """Every markdown table in `text`, as (header cells, data rows) pairs.

    A table starts at a `|` line immediately above a separator line -- every
    cell of it drawn from `{-, :}` -- and ends at the first line that does not
    open a cell, which is what keeps the paragraphs under a table out of it.
    They are prose about directories, and reading them as rows would resolve
    the same paths a second time.

    Located by shape rather than by a header name, so that a file with three
    tables in it yields three and the next self-indexed directory needs no edit
    here: the self-indexed clause above is structural for the same reason, and a
    rule keyed on a header string would be the exemption list it is not.
    """
    lines, tables, rows = text.splitlines(), [], None
    for number, line in enumerate(lines):
        cells = row_cells(line)
        if not cells:
            rows = None
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            # A separator. It opens a table when the line above it opened a
            # cell too; one inside a table body is skipped rather than read as
            # the head of a new one.
            if rows is None and number and row_cells(lines[number - 1]):
                rows = []
                tables.append((row_cells(lines[number - 1]), rows))
            continue
        if rows is not None:
            rows.append(cells)
    return tables


def table_cells(index, column=1):
    """The `column`th cell of every row of the index's own table, in order.

    Columns are counted from 1, the way a reader counts them, so the default is
    the first column and `column=2` is `Feeds`. The table is the one whose first
    header cell is `HEADER`, so an edit above it cannot quietly move the scan
    off it and leave a green run that read no rows at all. A thin wrapper over
    `markdown_tables` so the nested reader and this one cannot drift apart in
    what a table is.
    """
    for header, rows in markdown_tables(index):
        if header and header[0] == HEADER:
            return [row[column - 1] for row in rows if column <= len(row)]
    return []


def feeds_pointers(cell):
    """Every tool a `Feeds` cell names, each cut at its first whitespace.

    The cut is the whole of the flag-suffix rule -- `` `../tool.py --dump-pair` ``
    names `../tool.py` -- and the `via` clause needs no rule of its own, because
    both of its halves are backticked and reading every backticked token reads
    both. Without it the committed tree reports three false misses on the day
    this lands, which is the issue's own condition on the whole direction: a
    check that false-positives is worse than no check.
    """
    return [token.split()[0] for token in TOKEN.findall(cell) if token.split()]


def below(root, pattern):
    """Every path under `root` matching `pattern`, at any depth.

    Recursive because the `...` and bare-`*` rules do not know which directory
    the index meant -- `...-0400-045f.csv` is written in a cell whose other
    token is a different directory's row, and the abbreviation is what the
    index committed to, not a guess about where the file went.
    """
    return glob.glob(os.path.join(root, "**", pattern), recursive=True)


def names_a_file(token):
    """Whether the token is spelled like a path rather than like prose.

    The extension is the test, and it is what keeps a token like
    `0x0700-0x07FF` out of every branch that joins it onto a directory and
    answers against the disk -- where the honest answer is that this tool
    cannot read it, not that the file is absent. The dot-name test is on the
    last component, because `../grade.py` is a tool and `.gitignore` is not.
    """
    stem, extension = os.path.splitext(os.path.basename(token))
    return bool(extension) and not stem.startswith(".")


def resolve(token, root):
    """(verdict, note) for one token from a table cell.

    The note is what the token was read as, and is carried into a report so a
    `missing` says which rule it failed rather than only that a rule did.
    """
    # `...-suffix.csv` is the table's own abbreviation for "a file in the
    # family the previous token named". It is resolved as `*suffix.csv` over
    # the whole of testdata/, which is the only reading of it that cannot
    # invent a name: the stem it would have to be spliced onto is not in the
    # token, and a guess at it is how a checker grows a false failure.
    if token.startswith("..."):
        pattern = "*" + token[3:]
        return (RESOLVED if below(root, pattern) else MISSING), pattern

    if "/" in token:
        directory, _, pattern = token.rpartition("/")
        path = os.path.join(root, directory)
        if not os.path.isdir(path):
            return MISSING, token
        if not pattern:
            return RESOLVED, token
        return (RESOLVED if glob.glob(os.path.join(path, pattern)) else MISSING), token

    if any(c in token for c in "*?["):
        return (RESOLVED if below(root, token) else MISSING), token

    # A bare filename is `testdata/<name>`: the twenty loose fixtures sit at
    # the top of the directory and the table spells them without a path.
    if names_a_file(token):
        path = os.path.join(root, token)
        return (RESOLVED if os.path.exists(path) else MISSING), token

    return UNRESOLVED, token


def resolve_tool(token, tools_root):
    """(verdict, note) for one tool a `Feeds` cell names.

    `tools_root` is the **parent** of the testdata root -- `ec/tools/` for the
    committed tree, and the temporary root for a scratch one, which is what
    keeps the rule testable without hardcoding a directory the scratch cases do
    not have. The leading `../` is consumed rather than followed, because the
    cell writes the path from the *fixture's* point of view: the tool is the
    fixture's sibling, and resolving the cell against `testdata/` would be the
    first-column rule applied to a column that names a different kind of thing.
    Join-then-normalise, never string-concatenate a `..` that escapes against
    the working directory.
    """
    if not names_a_file(token):
        return UNRESOLVED, token
    relative = token
    while relative.startswith("../"):
        relative = relative[3:]
    path = os.path.normpath(os.path.join(tools_root, relative))
    return (RESOLVED if os.path.exists(path) else MISSING), repo_path(path)


def as_address(text):
    """The address as an integer, or None when it is not one this tool reads.

    The `0x` prefix, the case of the digits and how many they are padded to are
    the three ways the two sides of a nested reference spell one address, and
    every one of them is live in the committed file: `0x0EA2` against `0EA2`,
    `0xDEAD` against `DEAD`, `0x0070` against `0070`. A string compare reports
    a miss on all of them, and the check would be wrong on the day it landed.
    """
    text = text.strip()
    if text[:2].lower() == "0x":
        text = text[2:]
    try:
        return int(text, 16)
    except ValueError:
        return None


def csv_pointers(csvname, addresses, directory):
    """Every address a `X.csv` reference names, looked up in that CSV.

    Existence, not identity: the invariant is that the row the index names is
    in the file it names, and whether that row says what the cell claims is a
    question about the fixture with a different owner. A CSV with no `addr`
    column is `unresolved` rather than `missing` -- this tool cannot read that
    shape, which is not the same as the row being absent.
    """
    path = os.path.join(directory, csvname)
    if not os.path.isfile(path):
        return [(MISSING, csvname, csvname)]
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0] if rows else []
    if "addr" not in header:
        return [(UNRESOLVED, csvname, f"{csvname} has no `addr` column")]
    column = header.index("addr")
    held = set()
    for row in rows[1:]:
        if column < len(row) and as_address(row[column]) is not None:
            held.add(as_address(row[column]))
    if not addresses:
        return [(UNRESOLVED, csvname, f"{csvname} is named with no address")]
    out = []
    for token in addresses:
        # `index.csv` rows `0x1400`/`0x1410` is one backticked token naming
        # two rows, so the count this prints is per reference and not per cell.
        for piece in token.split("/"):
            value = as_address(piece)
            if value is None:
                out.append((UNRESOLVED, piece, f"{csvname} `{piece}` is not hex"))
            else:
                verdict = RESOLVED if value in held else MISSING
                out.append((verdict, piece, f"{csvname} {piece}"))
    return out


def nested_pointers(cell, directory, csvs=None):
    """Every reference a self-indexed directory's row makes, in reading order.

    A cell is a relative path, a `X.csv` plus one or more addresses, or both of
    those joined by ` + `; the third is one row and two references, and the
    second of the committed pair names two rows. A part that is none of the
    three is `unresolved` and says so, for the same reason a token the
    first-column rules fall off the end of does.

    `csvs` is the set of `X.csv` names this cell already recognised, collected on
    the way through rather than by a second pass: a second `.csv` shape test
    would be a second thing to keep in step, and the names are the input to the
    `evidence` rule below.
    """
    out = []
    for part in cell.split(" + "):
        tokens = TOKEN.findall(part)
        stem, extension = os.path.splitext(tokens[0]) if tokens else ("", "")
        if extension == ".csv":
            if csvs is not None:
                csvs.add(tokens[0])
            out.extend(csv_pointers(tokens[0], tokens[1:], directory))
        elif names_a_file(tokens[0]):
            # Resolved against the directory itself, not `testdata/`: the
            # README is written from there and writes its paths from there, and
            # a `..` that escaped to the parent would answer about a tree this
            # check never looked at.
            path = os.path.normpath(os.path.join(directory, tokens[0]))
            out.append(((RESOLVED if os.path.exists(path) else MISSING),
                        tokens[0], repo_path(path)))
        else:
            # A part neither rule reads. The token is its first backticked word,
            # so an `unresolved` line here names the same kind of thing the
            # first-column one does, and the note is the whole part, so a reader
            # can see what was passed over rather than only that something was.
            note = part.strip()
            out.append((UNRESOLVED, tokens[0] if tokens else note, note))
    return out


def evidence_pointers(csvname, directory, repo):
    """What one named CSV's `evidence` column names, and what is not there.

    A third base, and the only source here that reads a file's *contents* for a
    named column rather than a cell's backticked tokens: the column is the one
    the two committed fixture CSVs point at the **real** tree with, and the
    question it answers is "does `ec/decompiled/` hold that listing", which is a
    fact about committed files and not about what the fixture exercises.

    The column is read **by name** rather than by position, because it is
    column 7 of 8 in one of the two committed CSVs and column 10 of 12 in the
    other, and a position is right until the next column is added. A cell is
    `;`-separated: one committed row names `0EA2.asm` and `0EA2.c` side by side,
    and a cell read whole is a token no path rule can match. An **empty** value
    is not a pointer at all -- the shipped first-column limit that a cell with
    no backticked token yields no reference -- and a rule invented to read one
    would be a parser guessing. A CSV with no `evidence` column is `unresolved`
    rather than `missing`, for the reason `csv_pointers` gives for `addr`: "this
    tool cannot read that shape" is not "the cell is absent". It is reported on
    its own list rather than among the token findings, because a column that is
    not in the file has not named anything and there is no token behind it to
    count: leaving it in `unresolved` would subtract it from a tally of tokens
    this CSV contributed none of, and the fifth line would read a negative count
    of resolved paths.
    """
    path = os.path.join(directory, csvname)
    where = repo_path(path)
    if not os.path.isfile(path):
        # Already a `missing` on the nested side, which is the finding a reader
        # wants; opening it here would be a second report of the same edit.
        return Evidence(0, 0, [], [], [])
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0] if rows else []
    if "evidence" not in header:
        return Evidence(0, 0, [], [],
                        [(where, csvname,
                          f"{csvname} has no `evidence` column")])
    column = header.index("evidence")
    cells, tokens, missing, unresolved = 0, 0, [], []
    for row in rows[1:]:
        if column >= len(row) or not row[column].strip():
            continue
        cells += 1
        for token in (piece.strip() for piece in row[column].split(";")):
            if not token:
                continue
            tokens += 1
            if not names_a_file(token):
                # A URL, an address range, a bare word: "not resolved by this
                # method", never "absent". The note is the token, which is what
                # a reader needs to see rather than only that something was
                # passed over.
                unresolved.append((where, token, token))
                continue
            target = os.path.normpath(os.path.join(repo, token))
            if not os.path.exists(target):
                missing.append((where, token, repo_path(target)))
    return Evidence(cells, tokens, missing, unresolved, [])


def nested_index(path, repo):
    """What one self-indexed directory's own README named, and what is not there.

    Column 1 of every data row of every table in the file, and nothing else: the
    second column is prose about the case and the third is a long explanation of
    it, and a token lifted out of either would be a pointer the index never
    made. The `where` on every finding is this README rather than the top-level
    one, so a reader is told which of the two files to open.

    The `evidence_` totals are over the CSVs those cells named, and each
    distinct name is read once however many rows name it. Sorted, so the
    findings a run prints are in a fixed order rather than in the set's.
    """
    where = repo_path(path)
    directory = os.path.dirname(path)
    with open(path, encoding="utf-8") as f:
        tables = markdown_tables(f.read())
    rows, checks = 0, 0
    missing, unresolved = [], []
    named = set()
    for _, table in tables:
        for row in table:
            rows += 1
            for verdict, token, note in nested_pointers(row[0], directory, named):
                checks += 1
                if verdict == MISSING:
                    missing.append((where, token, note))
                elif verdict == UNRESOLVED:
                    unresolved.append((where, token, note))
    cells, tokens = 0, 0
    evidence_missing, evidence_unresolved, evidence_columnless = [], [], []
    for csvname in sorted(named):
        found = evidence_pointers(csvname, directory, repo)
        cells += found.cells
        tokens += found.tokens
        evidence_missing += found.missing
        evidence_unresolved += found.unresolved
        evidence_columnless += found.columnless
    return Nested(len(tables), rows, checks, missing, unresolved, len(named),
                  cells, tokens, evidence_missing, evidence_unresolved,
                  evidence_columnless)


def check(root, repo=None):
    """A `Result` for one testdata tree.

    The index is read from `root/README.md`, which is where it is by definition,
    so a caller cannot point the check at one file's table and another file's
    tree. Each problem carries the repository-relative path it was found under,
    made relative here rather than in `main` for the reason `report()` gives.

    `gaps` are (testdata path, directory name); the other eight are (index path,
    token, what the token was read as), the `nested_` pair naming the
    self-indexed README rather than this one and the `evidence_` pair naming the
    fixture CSV whose cell disagrees, which is a third file again and the reason
    reusing either of the other two would send a reader to a file that does not
    contain the cell. The row number is not carried: a token is a unique string
    in a 27-row table a reader has open, and a wrong line number is worse than
    none.

    `repo` is the base the `evidence` column resolves against, defaulted to the
    module global **at call time** so a caller that patches `REPO` and a caller
    that passes the argument are the same thing. A `repo=REPO` default would
    bind at def-time and silently defeat the patch.
    """
    if repo is None:
        repo = REPO
    with open(os.path.join(root, "README.md"), encoding="utf-8") as f:
        index = f.read()
    where, under = repo_path(os.path.join(root, "README.md")), repo_path(root)

    gaps, missing, unresolved = [], [], []
    names = list(fixture_dirs(root))
    how = [reachable(name, root, index) for name in names]
    for name, verdict in zip(names, how):
        if verdict is None:
            gaps.append((under, name))

    cells = table_cells(index)
    tokens = 0
    for cell in cells:
        for token in TOKEN.findall(cell):
            tokens += 1
            verdict, note = resolve(token, root)
            if verdict == MISSING:
                missing.append((where, token, note))
            elif verdict == UNRESOLVED:
                unresolved.append((where, token, note))

    feeds_missing, feeds_unresolved = [], []
    tools_root = os.path.dirname(root)
    feeds = table_cells(index, column=2)
    feeds_tokens = 0
    for cell in feeds:
        for token in feeds_pointers(cell):
            feeds_tokens += 1
            verdict, note = resolve_tool(token, tools_root)
            if verdict == MISSING:
                feeds_missing.append((where, token, note))
            elif verdict == UNRESOLVED:
                feeds_unresolved.append((where, token, note))

    # Only a directory that indexes *itself* carries a nested index. A directory
    # the top-level table merely names has no README to read, and the two
    # reachability clauses stay the two things they were.
    nested_missing, nested_unresolved = [], []
    evidence_missing, evidence_unresolved, evidence_columnless = [], [], []
    indexes, tables, rows, checks = 0, 0, 0, 0
    csv_read, cells_read, tokens_read = 0, 0, 0
    for name, verdict in zip(names, how):
        if verdict != "self":
            continue
        indexes += 1
        found = nested_index(os.path.join(root, name, "README.md"), repo)
        tables += found.tables
        rows += found.rows
        checks += found.checks
        csv_read += found.evidence_csvs
        cells_read += found.evidence_cells
        tokens_read += found.evidence_tokens
        nested_missing += found.missing
        nested_unresolved += found.unresolved
        evidence_missing += found.evidence_missing
        evidence_unresolved += found.evidence_unresolved
        evidence_columnless += found.evidence_columnless

    return Result(gaps, missing, unresolved, feeds_missing, feeds_unresolved,
                  nested_missing, nested_unresolved, evidence_missing,
                  evidence_unresolved, evidence_columnless, len(how),
                  how.count("index"),
                  how.count("self"), len(cells), tokens, len(feeds), feeds_tokens,
                  indexes, tables, rows, checks, csv_read, cells_read,
                  tokens_read)


def report(gaps, missing, unresolved, feeds, nested, evidence, columnless):
    """Print each disagreement, and return how many there were.

    A disagreement here is a defect in one of the two files, and it is not a
    reason to delete a fixture or a row: the fix is whichever of the two the
    edit was supposed to make. Only `missing` counts -- an `unresolved` token is
    printed so a reader can decide whether this tool's vocabulary needs a rule,
    and a check that failed on its own parser would be pushed to grow one.

    `feeds`, `nested` and `evidence` are the (missing, unresolved) pair for the
    three sources added later, and every line names the file it was found under:
    a `Feeds` miss is this index, a nested miss is the self-indexed README
    beside it, and an `evidence` miss is the fixture CSV holding the cell, which
    is what the `where` a caller hands in already carries.

    `columnless` is the `evidence` source's third list, and the only one of the
    three with wording of its own: a CSV whose header has no `evidence` column
    in it has not named anything, so the line says the column was not found
    rather than reusing the token wording, whose leading clause is the part a
    reader skims.
    """
    for under, name in gaps:
        print(f"{under}/{name}/: no index names it, and it has no README.md of "
              f"its own", file=sys.stderr)
    for where, token, note in missing:
        print(f"{where}: the table names `{token}` (read as `{note}`), which is "
              f"not on disk", file=sys.stderr)
    for where, token, note in unresolved:
        print(f"{where}: the table names `{token}`, which this tool cannot "
              f"resolve to a path ({note}) -- not checked, not absent",
              file=sys.stderr)
    for where, token, note in feeds[0]:
        print(f"{where}: the `Feeds` column names `{token}` (read as `{note}`), "
              f"which is not a tool on disk", file=sys.stderr)
    for where, token, note in feeds[1]:
        print(f"{where}: the `Feeds` column names `{token}`, which this tool "
              f"cannot resolve to a tool path ({note}) -- not checked, not "
              f"absent", file=sys.stderr)
    for where, token, note in nested[0]:
        print(f"{where}: the table names `{token}` (read as `{note}`), which is "
              f"not there", file=sys.stderr)
    for where, token, note in nested[1]:
        print(f"{where}: the table names `{token}`, which this tool cannot "
              f"resolve ({note}) -- not checked, not absent", file=sys.stderr)
    for where, token, note in evidence[0]:
        print(f"{where}: the `evidence` column names `{token}` (read as "
              f"`{note}`), which is not on disk", file=sys.stderr)
    for where, token, note in evidence[1]:
        print(f"{where}: the `evidence` column names `{token}`, which this tool "
              f"cannot resolve to a path ({note}) -- not checked, not absent",
              file=sys.stderr)
    for where, token, note in columnless:
        print(f"{where}: {note} -- not checked, not absent", file=sys.stderr)
    total = (len(gaps) + len(missing) + len(feeds[0]) + len(nested[0])
             + len(evidence[0]))
    if total:
        print(f"{total} disagreement(s) between {repo_path(INDEX)} and the tree "
              f"under it", file=sys.stderr)
    return total


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Accepted and not branched on: the check is the whole of what this tool
    # does, so --check is the default and the flag is the gate's spelling of it,
    # the way `check_register_counts.py` takes its image positionally.
    ap.add_argument("--check", action="store_true",
                    help="check the committed index against the committed tree "
                         "(the default, and the gate's entry point)")
    ap.parse_args()

    result = check(TESTDATA)
    if report(result.gaps, result.missing, result.unresolved,
              (result.feeds_missing, result.feeds_unresolved),
              (result.nested_missing, result.nested_unresolved),
              (result.evidence_missing, result.evidence_unresolved),
              result.evidence_columnless):
        return 1
    print(f"{result.directories} testdata/ director"
          f"{'y' if result.directories == 1 else 'ies'}: {result.named} named in "
          f"the index, {result.self_indexed} self-indexed, {len(result.gaps)} gap(s)")
    print(f"{result.rows} table row(s), {result.tokens} path token(s): "
          f"{result.tokens - len(result.missing) - len(result.unresolved)} resolved, "
          f"{len(result.missing)} missing, {len(result.unresolved)} unresolved")
    print(f"{result.feeds_cells} Feeds cell(s), {result.feeds_tokens} tool "
          f"pointer(s): {result.feeds_tokens - len(result.feeds_missing) - len(result.feeds_unresolved)} "
          f"resolved, {len(result.feeds_missing)} missing, "
          f"{len(result.feeds_unresolved)} unresolved")
    print(f"{result.nested_indexes} self-indexed README(s), {result.nested_tables} "
          f"table(s), {result.nested_rows} row(s), {result.nested_checks} "
          f"check(s): {result.nested_checks - len(result.nested_missing) - len(result.nested_unresolved)} "
          f"resolved, {len(result.nested_missing)} missing, "
          f"{len(result.nested_unresolved)} unresolved")
    # The column-less count sits with the CSVs rather than in the tally triple,
    # because it is a fact about a file rather than about a cell: a CSV with no
    # `evidence` column in it contributed no token, so counting it as an
    # `unresolved` token would take one more off the resolved count than the
    # count ever had, and the line would read a negative number of resolved
    # paths. Every quantity here now subtracts from `evidence_tokens` and
    # nothing else.
    print(f"{result.evidence_csvs} fixture CSV(s), "
          f"{len(result.evidence_columnless)} with no `evidence` column, "
          f"{result.evidence_cells} evidence cell(s), "
          f"{result.evidence_tokens} evidence path token(s): "
          f"{result.evidence_tokens - len(result.evidence_missing) - len(result.evidence_unresolved)} "
          f"resolved, {len(result.evidence_missing)} missing, "
          f"{len(result.evidence_unresolved)} unresolved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
