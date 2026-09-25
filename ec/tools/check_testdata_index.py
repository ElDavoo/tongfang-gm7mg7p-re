#!/usr/bin/env python3
"""Hold `ec/tools/testdata/README.md` and the tree under it to each other.

The index is what a change greps to learn which fixture holds which grader case,
and it is written by hand. Nothing reads it -- `grep -rn 'testdata/README'` over
the suite and the gate returns two prose mentions and not one read -- so a
fixture directory with no row in it, a row naming a path that is not on disk, a
`Feeds` cell naming a tool that has been renamed, and a self-indexed directory's
own table naming a listing or a CSV row that is not there would all land
unremarked. Those are the four places an index and a tree can disagree, which
this walks in one pass and prints each one's tally for.

The index has needed a hand-repair twice, in #502 and #720, and that is not
what these directions are for. Both were edits to a row's third column -- the
description of a case the row already named -- and this reads the first column,
the second and the nested tables, so it would have been green through both. It
is here for the gaps, which nothing else would have caught.

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

**What this does not check, which is as much of the point:**

  * *Whether a fixture is what its row says it is.* This is index/tree
    agreement and nothing else. A green run means the two files point at each
    other consistently; it says nothing about whether a CSV constructs the shape
    the third column describes, which is what a reader opens the file for.
  * *A token whose shape matches no rule below.* `unresolved` is counted and
    printed and is not a failure: a shape this tool cannot read is "not
    resolved by this method", never "absent", the same caveat
    `ec/annotations/registers.yaml` carries for a static scan. The rules are in
    `resolve()`, and falling off the end of them is the calibration line made
    mechanical rather than a sixth verdict that guesses.
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
  * *The reverse direction for either new source.* A `.py` under `ec/tools/`
    carrying no `Feeds` row, and a committed `.asm` or CSV row carrying no
    table row in its directory's `README.md`. Both are the "top-level files
    with no row" gap above, in the two directions added later, and both are
    declined for the same reason.
  * *Program/scope identity in the nested CSV lookup.* A row that exists at the
    address resolves even when it says something other than the cell claims.
    The invariant is "the row the index names is in the file it names", and
    "and it says the right thing" is a question about the fixture with a
    different owner. The cost is worth stating: a typo to an address that
    happens to exist in that CSV passes.
  * *A row whose cell holds no backticked token.* It yields no reference at
    all, which is the shipped first-column behaviour. A rule invented here
    would be a parser guessing, so the limit is stated rather than met.
  * *Prose below the table, in the index -> tree direction.* The whole file is
    searched for a directory name; only the table's two path columns are
    resolved against the disk. A path mentioned in prose is neither held to the
    disk nor reported as unchecked, which is the one place a reader could take
    silence for agreement.

All four tallies print whether or not they found anything, because a run that
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


def repo_path(path: str) -> str:
    """Repository-relative, so a report can be pasted into an editor.

    A `relpath` over a path the caller already made relative resolves against
    the working directory instead, which turns `ec/tools/testdata/README.md`
    into a chain of `..` on any run from outside the repository root.
    """
    return os.path.relpath(path, os.path.join(HERE, os.pardir, os.pardir))


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
    "nested_unresolved directories named self_indexed rows tokens feeds_cells "
    "feeds_tokens nested_indexes nested_tables nested_rows nested_checks")

# What one self-indexed directory's own README named, over the same three
# verdicts and carrying the same `where`/`token`/`note` triple as every other
# list here, so `check()` can add them up without a second shape of answer.
Nested = collections.namedtuple("Nested", "tables rows checks missing unresolved")


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


def nested_pointers(cell, directory):
    """Every reference a self-indexed directory's row makes, in reading order.

    A cell is a relative path, a `X.csv` plus one or more addresses, or both of
    those joined by ` + `; the third is one row and two references, and the
    second of the committed pair names two rows. A part that is none of the
    three is `unresolved` and says so, for the same reason a token the
    first-column rules fall off the end of does.
    """
    out = []
    for part in cell.split(" + "):
        tokens = TOKEN.findall(part)
        stem, extension = os.path.splitext(tokens[0]) if tokens else ("", "")
        if extension == ".csv":
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


def nested_index(path):
    """What one self-indexed directory's own README named, and what is not there.

    Column 1 of every data row of every table in the file, and nothing else: the
    second column is prose about the case and the third is a long explanation of
    it, and a token lifted out of either would be a pointer the index never
    made. The `where` on every finding is this README rather than the top-level
    one, so a reader is told which of the two files to open.
    """
    where = repo_path(path)
    with open(path, encoding="utf-8") as f:
        tables = markdown_tables(f.read())
    rows, checks = 0, 0
    missing, unresolved = [], []
    for _, table in tables:
        for row in table:
            rows += 1
            for verdict, token, note in nested_pointers(row[0], os.path.dirname(path)):
                checks += 1
                if verdict == MISSING:
                    missing.append((where, token, note))
                elif verdict == UNRESOLVED:
                    unresolved.append((where, token, note))
    return Nested(len(tables), rows, checks, missing, unresolved)


def check(root):
    """A `Result` for one testdata tree.

    The index is read from `root/README.md`, which is where it is by definition,
    so a caller cannot point the check at one file's table and another file's
    tree. Each problem carries the repository-relative path it was found under,
    made relative here rather than in `main` for the reason `report()` gives.

    `gaps` are (testdata path, directory name); the other six are (index path,
    token, what the token was read as), the `nested_` pair naming the
    self-indexed README rather than this one. The row number is not carried: a
    token is a unique string in a 27-row table a reader has open, and a wrong
    line number is worse than none.
    """
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
    indexes, tables, rows, checks = 0, 0, 0, 0
    for name, verdict in zip(names, how):
        if verdict != "self":
            continue
        indexes += 1
        found = nested_index(os.path.join(root, name, "README.md"))
        tables += found.tables
        rows += found.rows
        checks += found.checks
        nested_missing += found.missing
        nested_unresolved += found.unresolved

    return Result(gaps, missing, unresolved, feeds_missing, feeds_unresolved,
                  nested_missing, nested_unresolved, len(how), how.count("index"),
                  how.count("self"), len(cells), tokens, len(feeds), feeds_tokens,
                  indexes, tables, rows, checks)


def report(gaps, missing, unresolved, feeds, nested):
    """Print each disagreement, and return how many there were.

    A disagreement here is a defect in one of the two files, and it is not a
    reason to delete a fixture or a row: the fix is whichever of the two the
    edit was supposed to make. Only `missing` counts -- an `unresolved` token is
    printed so a reader can decide whether this tool's vocabulary needs a rule,
    and a check that failed on its own parser would be pushed to grow one.

    `feeds` and `nested` are the (missing, unresolved) pair for the two sources
    added later, and every line names the file it was found under: a `Feeds`
    miss is this index and a nested miss is the self-indexed README beside it,
    which is what the `where` a caller hands in already carries.
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
    total = len(gaps) + len(missing) + len(feeds[0]) + len(nested[0])
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
              (result.nested_missing, result.nested_unresolved)):
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
