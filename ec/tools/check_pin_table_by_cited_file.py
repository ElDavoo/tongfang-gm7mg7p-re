#!/usr/bin/env python3
"""Which test file the corpus's `test_*.py:NNN` pins name, and which indexed suite none does.

**Nothing here is a hardware claim.** No image is opened, no register is read
back, no capture is taken, and no laptop, EC or Windows machine is involved:
every figure below is a count of occurrences in the committed markdown, and the
one command that produces them is in this tree. Same framing as
`docs/findings/test-line-pin-census.md`, for the same reason -- this is a census
of text about text.

**The axis, and why it is a fifth one.** Issue #887's census breaks its class
down on four axes and every one of them is a property of *where a pin is
written*: 105 occurrences, 78 distinct spellings, 57 distinct resolved targets,
27 citing files. The axis that decides how much damage an edit does is **which
test file the pin names**, and nothing on that page breaks the class down on it.
The two tables below are that breakdown and the population it is a breakdown
*of* -- the indexed suites no pin names at all, which is the other direction the
same question asks.

**Why the name says `check_` and this tool cannot redden.** Issue #941 asked for
this file and for `test_<tool>.py` beside it, and taking both is the deliverable
that matches the ask. But in this tree `census_*` means "renders no verdict" and
`check_*` means "it can redden", and a `check_`-named tool that never fails on
drift is the shape `docs/findings.md` §14b records: a check reporting a pass
over work it could not have failed. The standing is stated here rather than left
for a reader to assume a gate exists, and
`test_check_pin_table_by_cited_file.py` holds it from the output side -- the
report contains neither `carries` nor `does not carry`, and a run whose every
pin is wrong exits 0. The alternative name is
`ec/tools/census_pin_table_by_cited_file.py`; it breaks the `test_<tool>.py`
pairing the issue asked for, and a rename is cheaper later than one now.

**What it consumes.** `census_test_line_pins.census()` -- one extractor, one
population, one verdict vocabulary. A second walk of the markdown here would be
a second set of numbers, and a headcount that cannot be reconciled against
itself is the failure `docs/findings/test-line-pin-census.md`'s whole argument
is about. That tool renders no verdict on any claim; neither does this one; the
`carries` / `does not carry` table is untouched by both.

**The one place this file reads a spelling for a target.** `census()` returns a
path for every record that resolves and `None` for every record it declines --
the fence rule declines before resolution runs, so a declined record has no
target to charge. This file normalises the *spelling* of a declined record with
`os.path.normpath()` and looks the result up:

  * a **path** spelling is placed by-path and by nothing else. `./ec/tools/x.py`
    and `ec/tools/x.py` are one path written two ways, and `normpath` erases the
    difference -- sixteen `grep -rn` transcript pins are spelled the first way and
    are the same pins as sixteen live ones. It is a **spelling** normalisation
    and not a path repair: a spelling naming a file that is somewhere else is
    *not* repaired into the file that is here, which is the guess
    `census.resolve()` refuses and which `test-line-pin-census.md` records as
    having cost four sound citations.
  * a **bare module name** goes to the census's own index, through
    `census.resolve()` rather than a second reader written here, so a declined
    pin spelled `test_x.py:4` is charged to the one file of that name -- or to
    `ambiguous-path`, when two could answer to it.
  * anything else lands in a **named** `unresolved-path` or `ambiguous-path`
    bucket, counted and printed with the spelling that landed there. There is
    **no basename fallback**: falling back to a base name is the guess
    `ambiguous-path` exists to refuse, and a second reader that made it here
    would put the guess back through the front door.

**What the negatives are.** `unresolved-path` says *no file of that path is in
this tree*, which is a statement about a directory walk, and a suite in the tail
says *no pin in the population names it*, which is a statement about the
population. Neither is a statement that a citation is missing, and neither is
ever "absent": `ec/annotations/registers.yaml` carries the same caveat for a
static scan, and it is load-bearing here rather than decorative. **The
concentration below is the cost of an edit, not an accusation** -- a heavily
cited suite is not thereby wrong, and this tool says nothing whatever about the
pins it counts.

**And what this tool is not.** It is not in `.github/scripts/agent-gates.sh`, and
cannot be from an agent branch: the plan stage's push token has no `workflow`
scope, so a branch touching `.github/` fails at the very end of the run. It runs
by hand, where `census_test_line_pins.py` stands today. A census nobody runs is
the shape of defect issue #819 was, so that standing is a case rather than a
sentence here.

Usage:
    python3 ec/tools/check_pin_table_by_cited_file.py
"""
import argparse
import os
import sys

# The census, not a copy of it. Tools run with their own directory on
# `sys.path`, the way `check_capture_claims.py` imports
# `check_cluster_citations`, so the import is by bare module name.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census_test_line_pins as census

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)

# The three verdicts a record can arrive in still carrying a file, and the
# table's three middle columns in that order. The census's own words rather than
# this file's, so a reader who knows the first tool's vocabulary does not have to
# learn a second one.
PLACED = (census.RESOLVES, census.OUT_OF_RANGE, census.DECLINED)

# The buckets a record lands in when no file is answerable for it. Also the
# census's own, and for the same reason: a record it read and refused to guess
# is not re-guessed here.
BUCKETS = (census.UNRESOLVED, census.AMBIGUOUS)


def place(record, files, index):
    """(bucket, path, how) for one census record.

    The bucket is the record's own census verdict, and the path is the file the
    record is charged to. A `None` path is not an error: it is the record going
    to a named bucket, and `how` is what the report prints beside it.
    """
    citing, _at, spelling, verdict, path, how, _shape, _text = record
    if verdict in (census.RESOLVES, census.OUT_OF_RANGE):
        # The census placed it, and an `out-of-range` record keeps the path it
        # was placed on: the file is named even when the line is not one the
        # file has. That is why the column is its own rather than folded into
        # `resolves`, and why the census's own `out-of-range` count reconciles
        # against a column of its own rather than against nothing.
        return verdict, path, how
    if verdict in BUCKETS:
        # The census read this one and declined to guess. A second reader that
        # guessed here would undo that refusal in the one place whose output a
        # reader is least able to audit.
        return verdict, None, f"the census read it as {verdict}: {how}"

    spelling = spelling.rsplit(":", 1)[0]
    normalised = os.path.normpath(spelling)
    if "/" in spelling:
        if normalised in files:
            return (census.DECLINED, normalised,
                    f"the spelling is written {spelling!r} and normalises to it "
                    f"({census.BY_PATH})")
        elsewhere = index.get(os.path.basename(spelling), [])
        hint = (f"; the only file of that name in the tree is {elsewhere[0]}"
                if len(elsewhere) == 1 else
                "; no file of that name is in the tree" if not elsewhere else
                "; the files of that name are " + ", ".join(elsewhere))
        return (census.UNRESOLVED, None,
                f"the pin names the path {spelling!r}, which normalises to "
                f"{normalised!r} and is not in the tree, and the path is not "
                f"repaired" + hint)
    # A bare module name is what `by-name` reads, and the census's index is
    # where that reading lives. The bucket stays `declined` even where the
    # placement succeeds: the census declined this record before resolution
    # ran, and which file it *would* have resolved to is a different fact from
    # what it did with it.
    placed, path, how = census.resolve(normalised, os.path.basename(normalised),
                                       os.path.dirname(citing), index, files)
    return (census.DECLINED if placed == census.RESOLVES else placed), path, how


def charged(records, files, index):
    """({path: [bucket, ...]}, [(bucket, spelling, where, how), ...]).

    The two halves are the table and the named buckets, kept apart so a record
    that is not a row cannot be read as one.
    """
    table, buckets = {}, []
    for record in records:
        bucket, path, how = place(record, files, index)
        if path is None:
            buckets.append((bucket, record[2], f"{record[0]}:{record[1]}", how))
        else:
            table.setdefault(path, []).append(bucket)
    return table, buckets


def rows(table):
    """[(path, resolves, out-of-range, declined, occurrences)], biggest first.

    Sorted by occurrences, then by resolves, then by path, so two runs print the
    same report and a case can compare two of them without ordering them first.
    A file with no `out-of-range` record still gets the column, on every run, for
    the reason the census's report prints its zero verdicts: a column that appears
    only when it is non-zero is a column a reader cannot tell from one that
    stopped being measured.
    """
    ordered = sorted(table.items(),
                     key=lambda item: (-len(item[1]),
                                       -item[1].count(census.RESOLVES), item[0]))
    return [(path, buckets.count(census.RESOLVES),
             buckets.count(census.OUT_OF_RANGE), buckets.count(census.DECLINED),
             len(buckets)) for path, buckets in ordered]


def unpinned(records, files):
    """The indexed test files no pin in the population names, sorted.

    `files` is `census.suites()`'s own index of every `test_*.py` under the tree,
    so the population is the one the census resolves against and a suite absent
    from this list is one some pin named.

    A **declined** record does not take a suite out of this tail. The fence rule
    declines it before resolution runs, and a transcript of a tool's output is
    not a citation -- the same reason the census will not resolve it. On the
    committed tree the six suites the declined records name are six of the same
    eleven the resolving ones name, so the figure is the same under either
    reading; the definition is stated because the two agree here and would not
    have to agree on a tree where a suite was named only inside a fence.
    """
    named = {record[4] for record in records if record[4] is not None}
    return sorted(set(files) - named)


def report(root, records, files, index):
    """This tool's whole output, and the counts a run has to be readable by."""
    table, buckets = charged(records, files, index)
    cited, tail = rows(table), unpinned(records, files)
    total = len(records)

    print("which test file the census's pins name, and the indexed suites "
          "none of them does")
    print(f"  {total} pin(s) over {len(files)} indexed test file(s): "
          f"{len(cited)} named by a pin, {len(tail)} named by none")

    width = max([len(path) for path, *_ in cited] + [len("cited test file")]) + 2
    print("\n  " + "cited test file".ljust(width)
          + "".join(verdict.rjust(13) for verdict in PLACED)
          + "occurrences".rjust(13))
    for path, resolves, out_of_range, declined, occurrences in cited:
        print("  " + path.ljust(width) + "".join(
            str(n).rjust(13)
            for n in (resolves, out_of_range, declined, occurrences)))

    if cited:
        head, rest = cited[0][4], cited[0][4] + cited[1][4] if len(cited) > 1 else 0
        print(f"  {head} of {total} occurrence(s) name one suite"
              + (f", and {rest} of {total} name the two above" if rest else "")
              + " -- the cost of an edit to that file, not an accusation")

    # The zeros are printed rather than dropped, so a bucket that has gone empty
    # reads differently from a bucket that is not measured.
    print("\n  " + ", ".join(
        f"{sum(1 for b in buckets if b[0] == bucket)} {bucket}"
        for bucket in BUCKETS) + " (records this file could place nowhere; "
        "counted, named, and never guessed)")
    for bucket, spelling, where, how in buckets:
        print(f"    {bucket:<15} {spelling:<40} {where}  {how}")

    print(f"\n  indexed but named by no pin ({len(tail)} of {len(files)}):")
    for path in tail:
        print(f"    {path}")

    print(f"  read {len(census.markdown(root))} markdown file(s) and "
          f"{len(files)} test file(s) under the tree, on "
          f"census_test_line_pins.py's population: "
          f"{'/'.join(census.PRUNED)}/ and {census.SELF_DOC} excluded there")
    print("  no verdict is rendered here and none fails: whether a cited line "
          "still bears the claim it is cited for is a reading, and it is "
          "docs/findings/test-line-pin-census.md's table")
    print("  every negative above is 'not read by this method', never 'absent'")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()

    if not census.markdown(REPO):
        print("check_pin_table_by_cited_file.py: no markdown file was read at "
              "all, so no pin could be charged to a file -- that is a broken "
              "census, not an empty one", file=sys.stderr)
        return 1
    records, _files = census.census(REPO)
    # `suites()` rather than the `files` `census()` hands back, because a bare
    # module name is answered by the index and by nothing else. Both walks read
    # the same tree and neither of them re-walks the markdown.
    files, index = census.suites(REPO)
    report(REPO, records, files, index)
    if not records:
        print("check_pin_table_by_cited_file.py: no `test_*.py:NNN` was found "
              "in the markdown read, so nothing was charged to a file -- that "
              "is a broken census, not an empty one", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
