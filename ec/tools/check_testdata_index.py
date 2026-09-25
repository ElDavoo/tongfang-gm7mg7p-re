#!/usr/bin/env python3
"""Hold `ec/tools/testdata/README.md` and the tree under it to each other.

The index is what a change greps to learn which fixture holds which grader case,
and it is written by hand. Nothing reads it -- `grep -rn 'testdata/README'` over
the suite and the gate returns two prose mentions and not one read -- so a
fixture directory with no row in it, and a row naming a path that is not on
disk, would both land unremarked. Those are the two directions an index and a
tree can disagree in, which this walks in one pass and prints each one's tally
for.

The index has needed a hand-repair twice, in #502 and #720, and that is not
what these directions are for. Both were edits to a row's third column -- the
description of a case the row already named -- and this reads the first column
and the tree, so it would have been green through both. It is here for the
gaps, which nothing else would have caught.

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
than one that was never made. It reads the first column only, because the `Feeds`
column is a tool reference and not a fixture path -- a different invariant.

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
  * *`call-graph/README.md`'s own table.* That is a nested index of a different
    and harder shape -- its rows name a `ghidra-functions.csv` row, not a path
    on disk -- so reading it is a separate piece of work. Its *existence* is
    what the self-indexed clause above reads.
  * *Prose below the table, in the index -> tree direction.* The whole file is
    searched for a directory name; only the table's first column is resolved
    against the disk. A path mentioned in prose is neither held to the disk nor
    reported as unchecked, which is the one place a reader could take silence
    for agreement.

Both tallies print whether or not they found anything, because a run that
checked nothing and a run that found nothing look the same from the exit code
alone. There is no floor on either number, for the reason
`docs/agent-pipeline.md` records about gates: an expected count turns every
added fixture into a failure. The suite asserts non-emptiness instead, which is
the assertion that is true of the tree rather than of the tool.

Usage:
    python3 ec/tools/check_testdata_index.py [--check]
"""
import argparse
import collections
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
# three problem lists, and the tallies a caller prints so that a run which
# reached nothing does not look like a run that found nothing. The three
# directory counts are separate fields rather than a length, because the second
# line of the output is about how the directories are indexed rather than about
# how many there are.
Result = collections.namedtuple(
    "Result",
    "gaps missing unresolved directories named self_indexed rows tokens")


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


def table_cells(index):
    """The first cell of every row of the index's table, in reading order.

    Ends at the first line that does not open a cell, which is what keeps the
    paragraphs below the table out of it -- they are prose about directories,
    and reading them as rows would resolve the same paths a second time.
    """
    cells, in_table = [], False
    for line in index.splitlines():
        if not line.startswith("|"):
            if in_table:
                break
            continue
        cell = line.split("|")[1].strip()
        if not in_table:
            in_table = cell == HEADER
            continue
        if set(cell) <= {"-", ":"}:
            continue
        cells.append(cell)
    return cells


def below(root, pattern):
    """Every path under `root` matching `pattern`, at any depth.

    Recursive because the `...` and bare-`*` rules do not know which directory
    the index meant -- `...-0400-045f.csv` is written in a cell whose other
    token is a different directory's row, and the abbreviation is what the
    index committed to, not a guess about where the file went.
    """
    return glob.glob(os.path.join(root, "**", pattern), recursive=True)


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
    # the top of the directory and the table spells them without a path. The
    # extension is what makes it a filename rather than prose, and it is also
    # what keeps a token like `0x0700-0x07FF` out of this branch and in
    # `unresolved` below, where the honest answer is that this tool cannot read
    # it -- not that the file is absent.
    stem, extension = os.path.splitext(token)
    if extension and not stem.startswith("."):
        path = os.path.join(root, token)
        return (RESOLVED if os.path.exists(path) else MISSING), token

    return UNRESOLVED, token


def check(root):
    """A `Result` for one testdata tree.

    The index is read from `root/README.md`, which is where it is by definition,
    so a caller cannot point the check at one file's table and another file's
    tree. Each problem carries the repository-relative path it was found under,
    made relative here rather than in `main` for the reason `report()` gives.

    `gaps` are (testdata path, directory name); `missing` and `unresolved` are
    (index path, token, what the token was read as). The row number is not
    carried: a token is a unique string in a 27-row table a reader has open,
    and a wrong line number is worse than none.
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
    return Result(gaps, missing, unresolved, len(how), how.count("index"),
                  how.count("self"), len(cells), tokens)


def report(gaps, missing, unresolved):
    """Print each disagreement, and return how many there were.

    A disagreement here is a defect in one of the two files, and it is not a
    reason to delete a fixture or a row: the fix is whichever of the two the
    edit was supposed to make. Only `missing` counts -- an `unresolved` token is
    printed so a reader can decide whether this tool's vocabulary needs a rule,
    and a check that failed on its own parser would be pushed to grow one.
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
    total = len(gaps) + len(missing)
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
    if report(result.gaps, result.missing, result.unresolved):
        return 1
    print(f"{result.directories} testdata/ director"
          f"{'y' if result.directories == 1 else 'ies'}: {result.named} named in "
          f"the index, {result.self_indexed} self-indexed, {len(result.gaps)} gap(s)")
    print(f"{result.rows} table row(s), {result.tokens} path token(s): "
          f"{result.tokens - len(result.missing) - len(result.unresolved)} resolved, "
          f"{len(result.missing)} missing, {len(result.unresolved)} unresolved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
