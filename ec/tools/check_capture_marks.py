#!/usr/bin/env python3
r"""Refuse a committed `evidence/ec-watch/*.csv` whose mark situation the index does not record.

Every timing claim in this repository over a passive capture rests on being
able to place a byte's move against an event. Where the capture carries
`ts,MARK,,label` rows that placement is mechanical; where it carries none, the
placement is an inference, and the door procedure has already had to retract
one such inference in place
(`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`, "at the plug-in" does not
survive). The defect this closes is not that nobody wrote the fact down -- it
is that **a reader cannot tell which captures support a timing claim and which
do not.** The index names the tool and the intervals and never says.

So the index carries one row per committed capture: how many `MARK` rows the
file holds, and, where it holds none, why not. Four refusals, and they are
four different mistakes with four different fixes:

  * **a capture with no row.** Not described by the index at all, so nothing
    says whether a timing claim over it is mechanical or inferred.
  * **a count that disagrees with the file.** The row says `N` and the file
    holds `M`, so the index is stale in whichever direction -- a file that
    gained a mark, or a number typed by hand. Both numbers are named.
  * **a `0` row with an empty reason cell.** The count is right and the
    reader still cannot tell whether the absence is deliberate. This is the
    refusal that makes the others mean something: a checker that only held
    counts would pass a corpus that says nothing.
  * **a row for a file that is not on disk.** A capture that was renamed,
    merged or dropped leaves its row behind, and a stale row is a claim about
    a file no reader can open.

**What this checks is a recorded reason, not marks.** A capture legitimately
has none: `ec_watch.py` writes a `MARK` row only when its `Marker` thread was
started, so a capture taken without `--mark` cannot hold one however many
times a byte moved. This tool never says a capture should have marks, never
opens the EC, never runs a capture, and never touches
`ec/annotations/registers.yaml`. **The reason cells are text a human writes and
this check holds only their presence**, so what a cell says is the author's
claim rather than something verified here -- which is why the committed ones
describe each file's shape instead of naming the command that produced it: no
mark-free capture under `evidence/ec-watch/` records its flags, and
`ec_watch.py`'s `Marker._loop` returns on EOF, so a run with `--mark` and
nothing typed leaves a file indistinguishable from one taken without it.

**`.txt` files in the capture root are outside this by construction, and are
reported rather than passed over in silence.** The scope is `*.csv`, so a
`.txt` capture gets no row and raises no refusal -- but "outside the rule" and
"checked and found conformant" must not read the same, which is why the
census line counts them. `check_capture_claims.py` reports a skipped `.txt`
capture for the same reason and says which it skipped.

**A new file rather than a mode on `check_capture_claims.py`**, per
`CLAUDE.md`'s rule: that tool's subject is address-presence and row-count
claims in prose, and a naming or index-completeness refusal belongs in its own
`--check` with its own vocabulary. `check_capture_names.py` is the precedent
for exactly this split. `WATCH` is imported from that tool rather than
re-spelled, so one place decides the path and a second copy of it is a second
thing to fall out of date.

**A refusal nothing checks is a refusal with no teeth**, and the cost of this
one is written down rather than designed away: the suite fires every refusal
on a scratch index, and the committed tree is asserted as **emptiness** --
no capture without a row, no disagreement, no stale row -- rather than as a
count of rows, so the corpus is free to grow while a capture that loses its
row turns it red.

Usage:
    python3 ec/tools/check_capture_marks.py [--check]
"""
import argparse
import csv
import collections
import os
import re
import sys

# Where a capture lives, imported rather than written out: `check_capture_names.py`
# and `check_testdata_row_claims.py` import the same name for the same reason,
# and `CLAUDE.md` asks for one place to decide a shared path.
from check_capture_claims import WATCH

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ROOT = os.path.join(REPO, WATCH)
INDEX = os.path.join(REPO, "evidence", "README.md")

# The table's own header row, matched rather than looked up by line number.
# A markdown table is found by its header, so this is what keeps the check
# working when a bullet above the table grows: `resolve()` in
# `measure_mark_provenance.py` is the same discipline for the same reason, and
# a `file:NNN` held to a prose file is a line every merge has to edit.
#
# Matched on the first two columns' names and the third's opening word. Not on
# all three in full: the header's own wording is prose a later commit may
# reword, and a check that reddened on a reworded column heading would be
# checking the heading rather than the corpus. The count of columns is part of
# the match, so a three-column table elsewhere in the index that happens to
# open with `capture` is not read as this one.
HEADER = ("capture", "mark", "why none")


def is_header(cells) -> bool:
    """Whether one table row is this table's header."""
    if not cells or len(cells) != 3:
        return False
    plain = [c.strip("`").strip().lower() for c in cells]
    return (plain[0] == HEADER[0]
            and plain[1].startswith(HEADER[1])
            and plain[2].startswith(HEADER[2]))


# One table row as `(capture filename, MARK count, reason)`. A namedtuple
# because the three are unpacked together at every refusal and a bare tuple
# would let a reordering pass silently -- the width is the whole contract.
# `marks` is an `int` when the cell held a count and the raw string when it
# did not, so a row this tool cannot read is refused by name rather than
# skipped into a green run.
Row = collections.namedtuple("Row", "capture marks reason")


def captures(root: str):
    """(csvs, txts) in the capture root, or None when it cannot be listed.

    `None` rather than two empty lists, for the reason
    `check_capture_names.census()` gives its own: "0 problems" over a root
    nobody read is a checker that passed by checking nothing, which is the
    §14b defect `run-tests.sh` guards at the suite level."""
    try:
        names = sorted(os.listdir(root))
    except OSError:
        return None
    files = [n for n in names if os.path.isfile(os.path.join(root, n))]
    return ([n for n in files if n.endswith(".csv")],
            [n for n in files if n.endswith(".txt")])


def mark_count(path: str) -> int:
    """How many `MARK` rows a capture holds.

    The same rule the writers' readers use -- `row[0] == "ts"` is the header,
    `row[0].startswith("#")` is the `#` block, and a mark is `row[1]` equal to
    the literal -- so a file this counts zero for is a file
    `grade_0751_isolation.read_capture` finds no mark in either. It reads with
    `errors="replace"` for the reason `measure_mark_provenance.fixture_census`
    gives: a writer appends without decoding, so an undecodable byte is a file
    that exists rather than an exception here."""
    n = 0
    with open(path, newline="", errors="replace") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "ts":
                continue
            if len(row) > 1 and row[1] == "MARK":
                n += 1
    return n


def _cells(line: str):
    """A table row's cells, or None for a line that is not one."""
    if not line.startswith("|"):
        return None
    cells = [c.strip() for c in line.rstrip().split("|")]
    # Leading and trailing pipes give an empty first and last cell; drop them
    # so a row's cells are its columns rather than its punctuation.
    if cells and not cells[0]:
        cells = cells[1:]
    if cells and not cells[-1]:
        cells = cells[:-1]
    return cells


def index_rows(text: str):
    """The rows of the mark table in `evidence/README.md`.

    Found by its header rather than by position, and every row after it is
    taken until the table ends -- a markdown table is its header, its
    separator, and the lines that follow, and a line that is not a table row
    closes it.

    A header that is not found is an empty list rather than an error here:
    `main()` reports that separately, because "the table is gone" and "the
    table is empty" are different failures and reporting both as "no rows"
    would let a renamed column pass as an empty corpus."""
    rows, in_table = [], False
    for line in text.splitlines():
        cells = _cells(line)
        if cells is None:
            in_table = False
            continue
        if is_header(cells):
            in_table = True
            continue
        if not in_table:
            continue
        # The separator under a markdown header is dashes, not a row.
        if all(c and set(c) <= set("-:") for c in cells):
            continue
        # A row that is not three cells wide is a row this tool cannot read, and
        # `check()` refuses it by name rather than the run skipping it or
        # dying on it: indexing `cells[2]` unconditionally would end the run
        # in an IndexError naming a list rather than the line that caused it,
        # and truncating a wider row would drop cells silently. So the width
        # is carried into the row as its own unreadable marks cell.
        if len(cells) != 3:
            rows.append(Row(cells[0].strip("`").strip() if cells else "",
                            f"{len(cells)} cells, not 3", ""))
            continue
        # The filename is written as a code span and the count as a bare
        # integer. Anything else in either cell is a row this tool cannot
        # read, and `check()` refuses it by name too: a row it cannot parse
        # is a row that records nothing.
        name = cells[0].strip("`").strip()
        count = cells[1].strip().strip("`")
        rows.append(Row(name, int(count) if count.isdigit() else count,
                        cells[2].strip()))
    return rows


def table_header_found(text: str) -> bool:
    """Whether the index carries the table at all."""
    return any(is_header(_cells(line)) for line in text.splitlines())


def check(root: str, rows, csvs):
    """Every disagreement between the index's rows and the files on disk.

    Returns the refusal messages. Both directions are walked as set
    differences, the way `measure_mark_provenance.check_citations` walks its
    join, because a one-sided check is a check that cannot notice a capture
    leaving."""
    problems = []
    seen = collections.Counter(r.capture for r in rows)
    for row in rows:
        if not isinstance(row.marks, int):
            problems.append(
                f"{WATCH}/{row.capture}: the marks cell is {row.marks!r}, "
                "which is not a count, so the row records nothing this check "
                "can hold it to")
            continue
        if row.marks == 0 and not row.reason:
            problems.append(
                f"{WATCH}/{row.capture}: no MARK row and an empty reason "
                "cell, so a reader cannot tell whether the absence is "
                "deliberate. The reason is the finding; the count is the "
                "arithmetic.")
            continue
        path = os.path.join(root, row.capture)
        if not os.path.isfile(path):
            problems.append(
                f"{WATCH}/{row.capture}: the index has a row for it and no "
                "such file is on disk, so the row is a claim about a capture "
                "nobody can open. Rename the capture or drop the row.")
            continue
        actual = mark_count(path)
        if row.marks != actual:
            problems.append(
                f"{WATCH}/{row.capture}: the index says {row.marks} MARK "
                f"row(s) and the file holds {actual}")
    for name in csvs:
        if seen[name] == 0:
            problems.append(
                f"{WATCH}/{name}: a committed capture with no row in the "
                "index's mark table, so nothing records whether a timing "
                "claim over it is mechanical or inferred")
        elif seen[name] > 1:
            problems.append(
                f"{WATCH}/{name}: {seen[name]} rows in the index's mark table, "
                "so which one a reader is to believe is not stated")
    return problems


def report(problems, where: str):
    """Print each refusal with the mistake it is, and return them.

    The message names the fix rather than the rule, for the reason
    `check_capture_names.report()` gives: the useful half of "this does not
    conform" is what the reader has to go and do. `where` is the root as the
    caller wants it named, so a refusal can point at a scratch tree in a case
    rather than at the committed one."""
    for problem in problems:
        print(f"{where}: {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} capture-mark refusal(s) under {where}/: every "
              "committed capture is to say whether a timing claim over it is "
              "mechanical or inferred, and these do not.", file=sys.stderr)
        print("A refusal here is not a reason to take a mark retroactively. It "
              "is a reason to say what the file is.", file=sys.stderr)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # Branched on, for the reason `check_capture_names.py` branches on it: this
    # tool is both a census and a refusal and read by hand it is the record a
    # writer consults, so the exit code should not be a claim until asked for.
    ap.add_argument("--check", action="store_true",
                    help="fail when a committed capture's mark situation is "
                         "not recorded in the index (the gate's entry point; "
                         "the default run prints the same census and exits 0)")
    args = ap.parse_args()

    found = captures(ROOT)
    if found is None:
        print(f"check_capture_marks.py: {WATCH}/ could not be listed, so no "
              "capture was checked -- that is a broken census, not an empty "
              "one", file=sys.stderr)
        return 1
    csvs, txts = found

    try:
        with open(INDEX, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"check_capture_marks.py: evidence/README.md could not be read "
              f"({e}), so no row could be held to a file -- that is a broken "
              "read, not an index with nothing to say", file=sys.stderr)
        return 1
    if not table_header_found(text):
        print("check_capture_marks.py: evidence/README.md carries no mark "
              "table, so every capture below is unrecorded rather than "
              "conformant", file=sys.stderr)
        return 1

    rows = index_rows(text)
    problems = check(ROOT, rows, csvs)
    report(problems, WATCH)

    print(f"{len(csvs)} capture(s) under {WATCH}/, "
          f"{len(rows)} row(s) in the index's mark table, "
          f"{len(txts)} `.txt` file(s) outside this rule's scope by "
          "construction (the rule is over `*.csv`)")
    if not problems:
        print("every committed capture's MARK row count agrees with the index, "
              "and each one holding none says why")
    if args.check and problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())