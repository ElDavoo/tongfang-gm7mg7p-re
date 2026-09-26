#!/usr/bin/env python3
"""Reconcile the per-pin table in docs/findings/test-line-pin-census.md against the census's own run.

Issue #942. `census_test_line_pins.py` is a census, not a check: it finds every
`test_*.py:NNN` the committed markdown carries, resolves each one, and renders
no verdict on any of them. `docs/findings/test-line-pin-census.md` holds the
verdicts, one per occurrence, in a five-column table. **Four of those five
columns are not a reading at all** -- they are the citing file, the citing
line, the cited target, the read kind and the shape, all of which the census
already computes and prints under `--verbose`. Only the verdict column is the
judgement, and nothing joined the other four to the run.

That gap has a price, and this repository has paid it by hand: #930
re-registered a row because its own citing line moved, #891 re-registered two
more, #889's note moved two, and a merge that only *adds a paragraph*
invalidates a row. The only signal was a human re-reading `--verbose` against
105 rows. So this is the gate that makes the next drift loud rather than the
last one silent.

**It never reads the verdict cell.** The cell is split out with the rest and
discarded: never compared, never printed in a problem message, never counted.
The reason is the write-up's own `*Why no checker*` (`:946`), and it is worth
restating in its own terms: the citation means *the line where this claim is
decided*, 5 of the 73 that resolve land on a `def test_` header and 6 land on
a blank line, so no single anchor covers them and a rule that rendered a
verdict would redden on sentences that are true. What this checks is that the
table still **describes** the run. Whether a pin carries its claim stays a
reading a human looked at, and `docs/findings/test-line-pin-repoint-563.md`'s
:33 — **"Both carry" is a reading, and it is a reading somebody looked at.** —
stays true.

**And it exits 0 on a tree where every verdict is wrong.** That standing is the
whole reason this is not the checker the write-up declines to ship, and the
suite asserts it against a table whose verdicts are all nonsense. It exits
non-zero only on a row the run does not describe, or on a run that placed
nothing -- a check that located nothing reports that rather than returning
clean, which is `census_test_line_pins.py`'s own exit-code rule and
`check_citation_lines.py`'s vacuous-pass guard.

**The table is found structurally, never by line number.** A checker that
pinned its own table's line numbers would be invalidated by exactly the class
of edit it exists to catch -- a paragraph inserted above the table moves every
row -- which is the whole lesson of the issue applied to the checker for it.

**What is compared.** Rows are matched to records on
`(resolved citing path, citing line, target spelling)`, a key that is unique
across all 105 records today, and a duplicate is reported rather than resolved
to the first. Three of the four mechanical columns are then held to the run:
the read kind and the shape, read out of the record rather than re-derived,
and the resolved path, re-derived from the row's own cells and required to
equal the record's.

**The resolved-path class is an identity on a placed row, and the suite says
so.** The plan it came from argued that re-deriving the path catches a citing
file moving to a different directory, where the read cell can still read
`beside` and still be right about nothing. Measured, that does not survive the
key: a record's `path` has exactly one source, `census.resolve()` called on
`(spelling, dirname(citing))`, and the key pins both of those inputs. So on a
placed row the comparison cannot differ, and this file keeps it for the one
thing it is still good for -- it is the assertion that fires if
`census.resolve()` ever stops being a pure function of its inputs, which is a
regression nothing else here would notice -- rather than dropping a class the
plan named and leaving it silently absent. `derived_path()` carries the full
reasoning and `test_path_differs_fires_when_the_record_and_the_row_disagree`
demonstrates the class is not dead.

**The census is loaded, not restated.** `census()`, `resolve()`, `shape_of()`,
the `BY_*` read-kind vocabulary, `SELF_DOC`, `PRUNED` and `walk()` all come
from `census_test_line_pins.py` by file location, so a change to the record
shape or to the resolver cannot leave this tool measuring a different thing
than the census it reconciles. The one thing it builds for itself is a file
index over every file in the tree rather than over `test_*.py` alone, because
a citing path names a `.md` file and the census's own `suites()` index would
not answer for one.

**What this does not check** is in `docs/findings/pin-table-row-reconciliation.md`,
and it is a longer list than the classes below: a verdict that has quietly
stopped being true, a row that is *right* about a stale line, a spelling the
census never emitted, and the table's row **order**. Every negative here is
"not read by this method", never "absent" -- the caveat
`ec/annotations/registers.yaml` carries for a static scan.

Usage:
    python3 ec/tools/check_pin_table_rows.py
    python3 ec/tools/check_pin_table_rows.py --verbose
    python3 ec/tools/check_pin_table_rows.py --root /path/to/a/scratch/tree
"""
import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)

# The census is a sibling module rather than an import, for the reason
# `test_census_test_line_pins.py` already uses the arrangement for: loading it
# by file location keeps `sys.path` untouched and keeps the record shape, the
# resolver and the read-kind vocabulary in one file instead of two. A copy of
# the reader here would be a second thing to re-derive when the first moves.
_spec = importlib.util.spec_from_file_location(
    "census_test_line_pins", os.path.join(HERE, "census_test_line_pins.py"))
census = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(census)

# The table's own header, and how many columns a row has to have for its
# verdict cell to be *the* verdict cell rather than a column that shifted.
# The arity is checked; the fifth cell's contents are not read, which is the
# standing this tool exists to hold and is why no comparison below mentions it.
TABLE_HEADER = "| citing | cited target | read | shape | verdict |"
TABLE_COLUMNS = 5

# The two spellings the table's citing column is written in. 104 rows write
# [`path](path) with the line number outside the link, and one writes the line
# number inside the code span; a reader that handled only the first would
# report the whole table unparsed, and one that skipped what it could not parse
# would place nothing and pass. The trailing `+` is the dagger one row carries,
# stripped here and kept on the message, because a row that carries the mark is
# the row the write-up is superseding and a message that dropped it would name
# a different row than the one it is about.
CITING_LINKED = re.compile(r"\[`(?P<path>[^`]+)`\]\([^)]+\):(?P<lineno>\d+)"
                           r"(?P<marker>\s*†)?")
CITING_SPAN = re.compile(r"`(?P<path>[^`]+):(?P<lineno>\d+)`(?P<marker>\s*†)?")
CITING_SPELLINGS = (CITING_LINKED, CITING_SPAN)

# The table's read column against the census's `BY_*`. One entry is an
# abbreviation rather than a mismatch: `xdata-register-map.md`'s two rows write
# `beside` where the census writes `beside-the-citing-file`, and normalising
# the two cells in the table instead would edit a shared, actively churning
# file for a cosmetic reason. A cell in neither map is a reported problem and
# not a pass, so a fourth spelling fails rather than slipping through.
READ_CELLS = {
    census.BY_PATH: census.BY_PATH,
    census.BY_NAME: census.BY_NAME,
    census.BY_BESIDE: census.BY_BESIDE,
    "beside": census.BY_BESIDE,
}
SHAPE_CELLS = {shape: shape for shape in census.SHAPES}

# The two spellings of "the run recorded no answer here": the census writes a
# bare hyphen in a declined record's `how` and `shape`, and the table writes
# an em dash in the same two columns. Shared by the read and shape lookups
# rather than written into each map, so the dash cannot be given a different
# meaning in one of them.
NONE_CELL = {"-": "-", "—": "-"}

# The seven classes this reports, in the order the summary prints them. Named
# rather than numbered so a message and a run agree on what a difference is
# called, and so a new one is a deliberate addition to a list a reader can see
# rather than a branch that appears in output nobody has read before.
UNPARSED = "unparsed-row"
UNPLACED = "unplaced-row"
NO_ROW = "row-without-record"
DUPLICATE = "duplicate-key"
READ_DIFFERS = "read-differs"
SHAPE_DIFFERS = "shape-differs"
PATH_DIFFERS = "path-differs"
CLASSES = (UNPARSED, UNPLACED, NO_ROW, DUPLICATE,
           READ_DIFFERS, SHAPE_DIFFERS, PATH_DIFFERS)


def read_lines(path):
    """`path` as a list of lines, one entry per line the file really has.

    The census's own `lines_of()` would do this, and is not used for it: that
    one reads a *test* file to answer how long it is, and this one reads a
    markdown file to find a table. A file that cannot be read is `None` here,
    and the caller reports that -- a missing write-up is not a table with no
    rows.
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    lines = text.split("\n")
    return lines[:-1] if lines and lines[-1] == "" else lines


def find_table(lines):
    """(at, [(at, cells)]) for the per-pin table in `lines`, or None.

    Located by its header rather than by a line number, and the header has to
    be **unique**: two of them mean the write-up grew a second table and this
    one does not know which is the per-pin one, which is a problem to report
    rather than a first-match to take. Rows are the `|`-prefixed lines that
    follow, up to the first line that is not one -- a table ends where its
    block does, and the write-up's next heading is one blank line away.
    """
    starts = [at for at, line in enumerate(lines, 1)
              if line.strip() == TABLE_HEADER]
    if len(starts) != 1:
        return None
    rows = []
    for at, line in enumerate(lines[starts[0]:], starts[0] + 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the `|---|---|` separator, which is not a row
        rows.append((at, cells))
    return rows


def read_citing(cell):
    """(path, lineno, marker) for one citing cell, or None if it is neither form."""
    for pattern in CITING_SPELLINGS:
        hit = pattern.fullmatch(cell.strip())
        if hit:
            return (hit.group("path"), int(hit.group("lineno")),
                    (hit.group("marker") or "").strip())
    return None


def read_target(cell):
    """(spelling, lines) for one cited-target cell, or None.

    The line half is split off with `rsplit(":", 1)` -- the same split
    `census.report()` uses on a record's own spelling -- because the target
    column carries a full `path:NNN` or `path:NNN-MMM` pin, and the path half
    is what `census.resolve()` takes.
    """
    text = cell.strip().strip("`").strip()
    if ":" not in text:
        return None
    spelling, _, lines = text.rpartition(":")
    if not spelling or not lines[0].isdigit():
        return None
    return spelling, lines


def canonical(cell, vocabulary):
    """The census's own constant for one table cell, or None if it is not one.

    A `None` is the caller's problem to report rather than skip: a cell this
    cannot read is a cell it cannot check, and a row that is quietly left
    unchecked is the silence every pointer-checker in this tree fails in.
    """
    cell = cell.strip()
    if cell in vocabulary:
        return vocabulary[cell]
    return NONE_CELL.get(cell)


def resolve_citing(spelling, beside_dir, present):
    """(relpath, detail) for a row's citing path, or (None, why).

    The census's own two-step rule -- against the tree first, then beside the
    file that wrote it -- and it is two steps for the same reason it is two
    steps in `census.resolve()`: the table writes `../findings.md` and
    `../../tools/README.md` for its own neighbours and a bare
    `0751-grader-block-scoping.md` for a sibling, and a tree-only reading
    reports all three as missing files. A path that resolves by neither names
    both attempts and any file of that name in the tree, because a wrong
    directory prefix and a deleted file look identical from here and have
    opposite fixes.
    """
    if spelling in present:
        return spelling, "in the tree"
    beside = os.path.normpath(os.path.join(beside_dir, spelling))
    if beside != spelling and beside in present:
        return beside, (f"not in the tree, and {beside} beside "
                        f"{census.SELF_DOC} is")
    same = sorted(rel for rel in present
                  if os.path.basename(rel) == os.path.basename(spelling))
    hint = (f"; the only file of that name in the tree is {same[0]}"
            if len(same) == 1 else
            "; no file of that name is in the tree" if not same else
            "; the files of that name are " + ", ".join(same))
    return None, (f"the row names {spelling!r}, which is not in the tree, and "
                  f"{beside!r} beside {census.SELF_DOC} is not either" + hint)


def census_view(root):
    """(records, files, index) for `root`: the census's run and `resolve()`'s inputs.

    `census()` returns the files it read but not the module-name index, and
    `suites()` re-reads the same tree to build it, so this walks twice. That
    is cheaper than a second way of building the index here, and a second way
    is what would let the record shape and the resolution shape drift apart.
    """
    records, files = census.census(root)
    _files, index = census.suites(root)
    return records, files, index


def read_kind(record):
    """The read kind the census recorded for `record`, or None if it recorded none.

    Read out of the record's own `how` rather than re-derived, because `how` is
    where the census says *which rule answered*, and a re-derivation here would
    be a second implementation of the thing being measured.
    """
    for kind in (census.BY_PATH, census.BY_NAME, census.BY_BESIDE):
        if kind in record[5]:
            return kind
    return None


def recorded(record):
    """(read kind, shape) the census recorded for `record`, or (None, None).

    A resolving record has both. A declined one has the census's own `-` for
    both, which is what the table writes as an em dash. The other three
    verdicts replace `how` with a reason and never reach the shape rule at all,
    so there is nothing here to compare a row against -- and a row is not held
    to a value the run does not record. `uncompared()` counts those rows and
    the run prints the count, so a class that stopped firing reads as a
    number rather than as a clean run.
    """
    if record[3] == census.RESOLVES:
        return read_kind(record), record[6]
    if record[3] == census.DECLINED:
        return "-", "-"
    return None, None


def derived_path(spelling, citing_dir, index, files):
    """The `path` a record carries, re-derived from one row's own three cells.

    `census.resolve()` is asked rather than re-implemented, so this is the same
    two-step rule reached from the row rather than from the run.

    **What this class is, stated from the measurement rather than the plan.**
    The issue's argument for a separate `path-differs` class was that a citing
    file moving to a different directory would leave the read cell reading
    `beside` and right about nothing. Measured on this tree, that argument
    does not survive the key: a row is matched on
    `(resolved citing path, citing line, target spelling)`, and a record's
    `path` has exactly one source -- `census.resolve()`, called on
    `(spelling, dirname(citing))`. **The key pins both of those inputs
    exactly**, so on a placed row this comparison is an identity by
    construction and cannot differ. It is kept because it is the one assertion
    that would fire if `census.resolve()` ever stopped being a pure function of
    its inputs -- which is a real regression, and one nothing else here would
    notice -- and because dropping it would have left a plan-named class
    silently absent. It is *not* a fifth independent column check, and the
    suite says so rather than letting a green run imply otherwise.
    """
    _verdict, path, _how = census.resolve(spelling, os.path.basename(spelling),
                                         citing_dir, index, files)
    return path


def compare_row(record, cells, where, label, target, resolved, index, files):
    """The problems one *placed* row has against the record it was matched to.

    Everything on the row's side of the comparison is passed in -- the four
    cells it was read from, the target spelling it spells, and the citing path
    it resolved to -- so this reads the row and never goes back to the table.
    Split out of `reconcile()` so a case can hand it a record the run could not
    have produced and watch `path-differs` fire: on a real matched row the
    class is an identity (see `derived_path`), and a check only ever
    exercised by a tree that cannot occur is a check nothing has tested.
    """
    want_read, want_shape = recorded(record)
    problems = []
    if want_read is None:
        return problems
    got = canonical(cells[2], READ_CELLS)
    if got != want_read:
        problems.append((
            READ_DIFFERS, f"{where} {label}",
            f"the row reads {cells[2]!r}"
            + ("" if got else ", which is not a read kind the census emits at "
                              "all")
            + f" and the run read {want_read!r}"))
    got = canonical(cells[3], SHAPE_CELLS)
    if got != want_shape:
        problems.append((
            SHAPE_DIFFERS, f"{where} {label}",
            f"the row says {cells[3]!r}"
            + ("" if got else ", which is not a shape the census emits at all")
            + f" and the run read {want_shape!r}"))
    if record[4] is not None:
        want_path = derived_path(target, os.path.dirname(resolved), index, files)
        if want_path != record[4]:
            problems.append((
                PATH_DIFFERS, f"{where} {label}",
                f"this row's own cells resolve {target!r} to {want_path!r} "
                f"from the citing file {resolved!r}, and the record carries "
                f"{record[4]!r}"))
    return problems


def reconcile(root):
    """(rows, records, placed, problems, uncompared) for the table under `root`.

    `problems` is a list of `(class, where, detail)`, in the order the rows are
    read, so two runs on two trees print the same report. `placed` is the
    number of rows that matched a record, and it is the number a run that
    placed nothing is judged on.
    """
    path = os.path.join(root, census.SELF_DOC)
    lines = read_lines(path)
    if lines is None:
        return None, None, 0, [(UNPARSED, census.SELF_DOC,
                                f"{census.SELF_DOC} could not be read")], 0
    table = find_table(lines)
    if table is None:
        found = sum(1 for line in lines if line.strip() == TABLE_HEADER)
        return None, None, 0, [(UNPARSED, census.SELF_DOC,
                                f"{found} line(s) of {census.SELF_DOC} read as "
                                f"the per-pin table header {TABLE_HEADER!r}, and "
                                f"the table is located by that header rather "
                                f"than by a line number, so there is no telling "
                                f"which one is the per-pin table")], 0

    records, files, index = census_view(root)
    by_key = {}
    for record in records:
        by_key.setdefault((record[0], record[1], record[2]), []).append(record)

    table_dir = os.path.dirname(census.SELF_DOC)
    present = set(census.walk(root, ""))
    problems, claimed, placed, uncompared = [], set(), 0, 0

    for at, cells in table:
        where = f"{census.SELF_DOC}:{at}"
        if len(cells) != TABLE_COLUMNS:
            problems.append((UNPARSED, where,
                             f"the row has {len(cells)} cell(s), not "
                             f"{TABLE_COLUMNS}, so which one is the verdict is "
                             f"not a thing this tool can say"))
            continue
        citing = read_citing(cells[0])
        target = read_target(cells[1])
        if citing is None or target is None:
            which = ("citing" if citing is None else "cited-target")
            cell = cells[0] if citing is None else cells[1]
            problems.append((UNPARSED, where,
                             f"the {which} cell {cell!r} is in neither of the "
                             f"spellings this tool reads, and a row it cannot "
                             f"parse is a row it cannot check"))
            continue
        path_text, lineno, marker = citing
        label = f"{path_text}:{lineno}" + (f" {marker}" if marker else "")
        resolved, why = resolve_citing(path_text, table_dir, present)
        if resolved is None:
            problems.append((UNPARSED, f"{where} {label}", why))
            continue

        key = (resolved, lineno, target[0] + ":" + target[1])
        if key in claimed:
            problems.append((DUPLICATE, f"{where} {label}",
                             "another row already carries this citing file, "
                             "citing line and target, and which of the two is "
                             "the record is not guessed"))
            continue
        claimed.add(key)
        found = by_key.get(key, [])
        if len(found) > 1:
            problems.append((DUPLICATE, f"{where} {label}",
                             f"{len(found)} census records carry this citing "
                             f"file, citing line and target, and which of them "
                             f"this row is about is not guessed"))
            continue
        if not found:
            problems.append((UNPLACED, f"{where} {label}",
                             f"no record for {resolved}:{lineno} naming "
                             f"{key[2]!r}; the run read that citing line as "
                             f"something else, or as nothing"))
            continue

        record = found[0]
        placed += 1
        if recorded(record)[0] is None:
            uncompared += 1
            continue
        problems.extend(compare_row(record, cells, where, label, target[0],
                                    resolved, index, files))

    for key in sorted(by_key):
        if key not in claimed:
            problems.append((NO_ROW, f"{key[0]}:{key[1]}",
                             f"the run reads a pin at this line naming "
                             f"{key[2]!r} and the table has no row for it"))
    return table, records, placed, problems, uncompared


def report(root, outcome, verbose):
    """The whole output: every row under `--verbose`, then the counts.

    Every class is printed on every run with its count, the way
    `census.report()` prints every verdict and every shape including the ones
    that are zero -- a class that stopped firing has to read as a number rather
    than as a line that is no longer there.
    """
    table, records, placed, problems, uncompared = outcome
    # Before anything else, including before the "the table was not found"
    # return below: the one problem that stops the run is the one a reader most
    # needs named, and `main()`'s message only says that it exits non-zero.
    for kind, where, detail in problems:
        print(f"{kind}  {where}\n    {detail}", file=sys.stderr)
    if records is None:
        # A summary line of zeroes here would read as a run that checked
        # nothing and found nothing wrong, which is the one outcome this must
        # not look like.
        return
    for at, cells in table:
        if verbose and len(cells) == TABLE_COLUMNS:
            citing, target = read_citing(cells[0]), read_target(cells[1])
            print(f"  {census.SELF_DOC}:{at}  "
                  f"{f'{citing[0]}:{citing[1]}' if citing else cells[0]}  "
                  f"{target[0] if target else cells[1]}  "
                  f"{cells[2]}  {cells[3]}")

    counts = {kind: sum(1 for problem in problems if problem[0] == kind)
              for kind in CLASSES}
    print(f"{len(table)} table row(s) against {len(records)} census record(s) "
          f"under {root}: {placed} placed")
    print("  " + ", ".join(f"{counts[kind]} {kind}" for kind in CLASSES))
    if uncompared:
        print(f"  {uncompared} row(s) not compared: their record is neither a "
              f"resolving nor a declined one, so the run recorded no read kind "
              f"and no shape to hold them to")
    print("  no verdict cell was read: whether a cited line still carries the "
          "claim it is cited for is a reading, and it is "
          f"{census.SELF_DOC}'s table")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=REPO,
                    help="the tree to reconcile (default: this repository)")
    ap.add_argument("--verbose", action="store_true",
                    help="name every row: the table line, the citing file and "
                         "line, the cited target, the read cell and the shape")
    args = ap.parse_args()

    # Normalised because the default is derived from `__file__` and prints as
    # `.../ec/tools/../..`, which is a path a reader has to resolve before they
    # can tell whether it is the tree they meant.
    root = os.path.normpath(args.root)
    outcome = reconcile(root)
    report(root, outcome, args.verbose)
    if outcome[0] is None:
        print("check_pin_table_rows.py: the per-pin table is not in "
              f"{census.SELF_DOC}, so no row could be checked -- that is a "
              "broken reconciliation, not a clean one", file=sys.stderr)
        return 1
    table, records, placed, problems, _uncompared = outcome
    if problems:
        return 1
    if not records or not table or not placed:
        print("check_pin_table_rows.py: no row was placed against a record, so "
              "nothing was checked -- that is a broken reconciliation, not a "
              "clean one", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
