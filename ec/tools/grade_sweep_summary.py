#!/usr/bin/env python3
"""Read a per-address EC sweep summary in the committed four-column shape.

`evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv` is the one capture
in `evidence/ec-watch/` that is a projection rather than a log: four columns,
one row per address, `addr,change_count,first_old,last_new`. It was
transcribed by hand from a 32,499-row change log that was never committed,
and nothing regenerated or checked it. Issue #276 is what a lossy projection
costs when a reader takes it at face value -- a claim that `0x07C6` "held
`0x04`", over a row that reads `0x07C6,2,0x04,0x04` and is a byte that moved
twice and came back. This tool is that file's reader, and the thing it exists
to refuse is the `held` reading of a row with a non-zero `change_count`.

**Three classes, and the third is the whole point.**

| condition | what this prints |
|---|---|
| `change_count == 0`, endpoints equal | `held` |
| endpoints differ | `moved, net ±N` |
| endpoints equal, `change_count > 0` | `moved N times, returned to its first recorded value` |

There is no fourth. There is in particular **no path by which a byte with a
non-zero change count is described as held, unchanged or quiet**, whatever its
endpoints say -- and that is a property of the classifier, not a string
searched for in the output. The net figure is an endpoint statistic, so it is
blind to exactly the movement a returned byte made; printing it alone is what
the false sentence walked into.

**What `first_old` is measured against, and what it is not.** It is the value
an address held at a sweep *inside* the window: the pre-image of that
address's first recorded change. The four columns cannot distinguish that from
"the value at the window's first sweep", because the difference between the two
is a whole missing transition, and a transition is what this format does not
carry. The closing section says so, and works it on a row read out of the file
rather than named here: the first row in file order with exactly one recorded
change and two endpoints that differ, because that is the shape where the
missing step is a single row wide and easiest to read past. What the format
carries no word for at all is the intermediate values, the timestamps, the
order, and whether an address with no row in the file moved at all -- which is
"not found to move in this file", never "never written".

**The header reconciliation is reported, not adjudicated.** The `#` block at
the head of a summary states how many rows the log it was derived from had,
and the `change_count` column sums to a figure that is a function of what the
transcriber kept. Both are computed on every run and printed with their
difference; neither is written into this file. Which of them is right cannot be
settled from anything committed, because the source log is not in the tree, so
the report says that rather than picking one. `--strict` turns a
non-reconciling pair into a non-zero exit, for a human who still holds the
log; the default exit is 0, because a difference this tool cannot resolve is
not a defect it has found.

**A change log is refused, not graded.** Handed a `ts,addr,old,new` capture
this tool prints one line naming the readers that own that shape --
`grade_gpu_door.py` for the `0x07C4`-`0x07D7` GPU block, and
`grade_0751_isolation.py` for a marked run -- plus `check_capture_claims.py`
for the prose-claim oracle, which is the tool that holds prose about a capture
to the capture. A fourth reader of a format two graders already hold would be
a fourth thing to keep in step with the shape rather than a fourth answer.

**What it reads, and what it does not check.** It reads the file it is handed
and no other: no EC, no firmware image, no Ghidra, no network, no scratch
directory. The `#` lines are dropped before the header is read, by importing
`check_capture_claims.capture_lines` rather than repeating its filter -- the
committed summary opens with a `#` block, and a reader that takes a comment
as the fieldnames finds no `addr` column at all, which reads as "this file
carries no addresses" rather than as a parser that skipped what it should not
have. `normalise()` comes from the same module so `0x0449` and `0X0449` are
one address here as they are there, and the `change_count` total is
`read_capture()`'s own figure rather than a second tally of the same column:
that figure is what `check_capture_claims.py` compares a prose claim against,
and this tool printing its own number would leave two readers of one column
free to disagree.

**Value columns are parsed tolerantly.** `0x04`, `04` and `4` are one value.
The committed file's rows are all two-digit padded, and requiring that of a
future summary would be a rule about spelling rather than about meaning.

**It grades no register.** Nothing here changes a `status:` in
`ec/annotations/registers.yaml`, and a row here is a passive record of what a
watcher saw -- not a readback of anything, and not evidence that the EC acts
on a byte.

`--self-test` runs this tool's own committed suite,
`test_grade_sweep_summary.py`, and hands back its exit code. It is dispatched
before the parser rather than after, because `summary` is a required
positional and relaxing it would make a command line with no file in it a
passing run -- which is one of the refusals this tool is for. The suite runs
in a subprocess rather than being imported, so the tool is not loaded a second
time under another name in one interpreter.

Usage:
    python3 ec/tools/grade_sweep_summary.py sweep-summary.csv [--strict]
    python3 ec/tools/grade_sweep_summary.py --self-test
"""
import argparse
import csv
import os
import re
import subprocess
import sys

# The `#` filter, the address spelling and the `change_count` total, all from
# the tool that already reads every capture under evidence/ec-watch/. One
# reader of each, so a fix to any of them lands once and this tool gets it.
from check_capture_claims import capture_lines, normalise, read_capture

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
SUMMARY = os.path.join("evidence", "ec-watch",
                       "2026-09-18-ac-plugin-sweep-summary.csv")

# The suite `--self-test` runs, and the directory it is discovered in.
# Absolute so the mode works from any cwd, and named by file rather than by
# `test_*.py` so the gate's cost is this suite's and not the whole directory's.
SUITE_FILE = "test_grade_sweep_summary.py"
TOOL_DIR = HERE

# The two shapes this tool tells apart. The summary is matched as a superset,
# so a future summary carrying one more column is still a summary; a capture
# log is matched on its four own columns for the same reason. Neither is a
# requirement on the *order*, which is the reader's business and not the
# format's.
SUMMARY_COLUMNS = ("addr", "change_count", "first_old", "last_new")
CHANGE_LOG_COLUMNS = ("ts", "addr", "old", "new")

# The figure a summary's `#` block states about the log it was derived from,
# as `32,499-row`. It is a claim about a file that is not committed, which is
# why it is printed beside the column's own sum and neither is believed. The
# thousands separator is optional so both spellings parse.
HEADER_ROWS = re.compile(r"\b(\d[\d,]*)-row\b")

# The readers a refused change log is sent to rather than read here. Named in
# the refusal itself, so a person handed the wrong file is told where to go in
# the same line that refuses it. `fan_pair_correlation.py` is here for the same
# reason as the two graders: it has its own reader for `ts,addr,old,new` and
# this tool is not the place a change log gets a third.
OWNERS = (
    ("grade_gpu_door.py", "the `0x07C4`-`0x07D7` GPU block"),
    ("grade_0751_isolation.py", "a marked run, windows cut at its `MARK` rows"),
    ("fan_pair_correlation.py", "tachometer pairs correlated across captures"),
)

# A value column: `0x04`, `04` and `4` are one byte, and anything outside
# `0x00`-`0xFF` is not a byte at all.
VALUE = re.compile(r"\A(?:0[xX])?([0-9A-Fa-f]{1,2})\Z")


class Refused(Exception):
    """A file this tool will not grade, with the sentence saying why.

    Raised rather than returned, because every way of failing here has the
    same consequence: a reader that could not classify a file must not report
    an empty classification of it, which would print as a clean run over rows
    nobody read.
    """


def value_of(text, where, column):
    """One byte from a value column, or the refusal naming what is wrong."""
    if text is None:
        raise Refused(f"{where}: no {column} column")
    m = VALUE.match(text.strip())
    if not m:
        # The pattern caps a value at two hex digits, so a three-digit one
        # fails here rather than arriving as a number out of range.
        raise Refused(f"{where}: {column} reads {text!r}, which is not a byte "
                      "written as 0x00-0xFF (a bare 04 and a 0x04 are both "
                      "accepted; anything wider is not one)")
    return int(m.group(1), 16)


def count_of(text, where):
    """The `change_count` column as a non-negative integer."""
    if text is None or not text.strip().isdigit():
        raise Refused(f"{where}: change_count reads {text!r}, which is not a "
                      "count of changes")
    return int(text.strip())


def comment_lines(path):
    """The `#` block at the head of a file, in order and without the marker."""
    out = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped.startswith("#"):
                if stripped:
                    break
                continue
            out.append(stripped.lstrip("#").strip())
    return out


def fieldnames_of(path):
    """The header of a capture with its `#` block already dropped.

    `csv.DictReader` rather than a hand split, because the fieldnames are what
    both shape tests read and this is the one reader of them in the tree.
    """
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(capture_lines(path))
        return reader.fieldnames or []


def classify(count, first, last, where):
    """`(class, phrase)` for one row, or the refusal naming what is wrong.

    The order of the arms is the order of the table in the docstring, and the
    first one is a refusal rather than a branch: `change_count == 0` with two
    endpoints that differ is a file that contradicts itself, and grading it
    either way would pick a side. The `held` arm is unreachable for a byte that
    moved, which is the property the suite pins over the committed file, and it
    is reached by the count rather than by the endpoints because the count is
    the only column that says the byte moved at all.
    """
    if first != last:
        if count == 0:
            raise Refused(
                f"{where}: change_count is 0 but the endpoints differ, so the "
                f"row says the byte never moved and that it did; the file "
                f"contradicts itself and no reading of it can be graded")
        return "moved", (f"moved, net "
                         f"{'+' if last > first else '-'}{abs(last - first):#04x}")
    if count == 0:
        return "held", "held"
    return "returned", (f"moved {count} time{'s' if count != 1 else ''}, "
                        "returned to its first recorded value")


def summary_rows(path):
    """[(address, count, first, last)] for a summary in this shape.

    Every row is checked before the first is returned, so a file with a bad row
    at the end grades none of them: a report printed over the rows before a
    refusal is a half-right report.
    """
    out = []
    seen = set()
    for number, row in enumerate(csv.DictReader(capture_lines(path)), start=1):
        where = f"row {number}"
        address = normalise(row["addr"].strip()) if row.get("addr") else ""
        if not re.fullmatch(r"0x[0-9A-F]{4}", address):
            raise Refused(f"{where}: addr reads {row.get('addr')!r}, which is "
                          "not a four-digit EC address")
        if address in seen:
            raise Refused(f"{where}: {address} has a second row; a summary is "
                          "one row per address, and two of them make the "
                          "change_count column ambiguous")
        seen.add(address)
        count = count_of(row.get("change_count"), where)
        first = value_of(row.get("first_old"), where, "first_old")
        last = value_of(row.get("last_new"), where, "last_new")
        # Classified here rather than at the print, so a self-contradicting
        # row is refused before any row of the file is reported.
        classify(count, first, last, where)
        out.append((address, count, first, last))
    return out


def refuse_other_shape(path, columns):
    """Why this file is not a summary, or None when it is one."""
    fields = {name.strip() for name in columns if name}
    if fields.issuperset(SUMMARY_COLUMNS):
        return None
    if fields.issuperset(CHANGE_LOG_COLUMNS):
        raise Refused(
            f"that is a change log ({','.join(columns[:4])}), one row per "
            "change rather than one row per address, so there is no "
            "`change_count` to read a total out of and nothing here is said "
            "about it. " + " and ".join(
                f"`{tool}` owns {what}" for tool, what in OWNERS) +
            "; `check_capture_claims.py` is the reader for a claim written in "
            "prose about one")
    raise Refused(
        f"the header names {','.join(columns) if columns else 'no columns'}, "
        f"which is neither this format (`{','.join(SUMMARY_COLUMNS)}`) nor "
        "the change log the other readers hold. Refused rather than guessed "
        "at, because the columns this tool reads are the ones whose absence "
        "makes every row below it unreadable")


def report(path, strict=False):
    """Print the classification of one summary; return the exit code."""
    # Read and check the whole file before printing any of it, so a row that
    # refuses at the end never leaves the rows before it already on the
    # terminal: a report the reader has to decide how much to believe is worse
    # than no report and a reason.
    comments = comment_lines(path)
    rows = summary_rows(path)

    print(f"{path}: a per-address sweep summary "
          f"({','.join(SUMMARY_COLUMNS)})")
    if comments:
        print("\n  what the file's own header says")
        for line in comments:
            print(f"    # {line}")

    counts = {"held": 0, "moved": 0, "returned": 0}
    for address, count, first, last in rows:
        kind, phrase = classify(count, first, last, address)
        counts[kind] += 1
        print(f"  {address}  0x{first:02X} -> 0x{last:02X}  {count} change(s)"
              f"  {phrase}")

    print(f"\n  {len(rows)} row(s): {counts['moved']} moved, "
          f"{counts['returned']} moved and returned, {counts['held']} held")
    if not rows:
        print("  nothing to classify, so nothing above is a reading of the "
              "file's behaviour")

    reconciled = reconcile(path, comments, rows)
    reference_point(rows)
    what_is_absent()

    print("\nnote  this is a read of a committed CSV: no EC was opened, no "
          "register read\n      back, and nothing here is evidence that the EC "
          "acts on a byte.")
    return 1 if (strict and not reconciled) else 0


def reconcile(path, comments, rows):
    """Print the header's figure against the column's; return whether they agree.

    Both figures are computed on this run. The header's is read out of the
    `#` block as a claim about a log that is not committed, and the column's is
    `read_capture()`'s own total, so this is the number a prose claim about
    this file is compared against rather than a second tally that could drift
    from it. The difference is printed and not adjudicated: the 32,499-row log
    is not in the tree, so no run of this tool can say which figure is right,
    and a tool that picked one would be reporting a fact about a file nobody
    has.
    """
    total = sum(read_capture(path)[0].values())
    stated = [int(m.group(1).replace(",", "")) for comment in comments
              for m in [HEADER_ROWS.search(comment)] if m]

    print("\n  header reconciliation")
    if not stated:
        print("    the `#` block states no source-log row count, so there is "
              "nothing\n    here for the change_count column to disagree "
              "with")
        return True
    claim = stated[0]
    print(f"    the header states the source log had {claim} row(s)")
    print(f"    the change_count column sums to {total}")
    if claim == total:
        print("    they agree")
        return True
    over = "more" if total > claim else "fewer"
    print(f"    they do not reconcile: the column is {abs(total - claim)} "
          f"{over} than the\n    header's figure")
    print("    not settled here. The source log is not committed, so nothing "
          "in this tree can\n    say which figure is right. The two describe "
          "different things -- one is every\n    change the whole log held, "
          "the other what this file's own rows account for --\n    and a "
          "header naming rows this file does not carry would raise the column\n"
          "    above the log, which is one way to read this and not a "
          "conclusion.")
    return False


def reference_point(rows):
    """Say what `first_old` is measured against, worked on a row from the file."""
    print("\n  what first_old is measured against")
    print("    the value an address held at a sweep inside the window -- the\n"
          "    pre-image of that address's first recorded change. The four "
          "columns\n    cannot tell that apart from \"the value at the "
          "window's first sweep\", and the\n    difference between the two is "
          "a whole missing transition.")
    example = next((row for row in rows
                    if row[1] == 1 and row[2] != row[3]), None)
    if example is not None:
        address, _, first, last = example
        print(f"    {address} records one change, 0x{first:02X} -> "
              f"0x{last:02X}, and nothing in\n    this file says how it came "
              f"to be at 0x{first:02X}. So the row does not say\n    whether "
              "the byte was already there when the window opened or\n"
              "    arrived at it inside the window, and no reading of "
              "`first_old`\n    as \"where it started\" can be had from these "
              "four columns.")
    else:
        print("    this file records no single-change row with two endpoints "
              "that differ,\n    so it offers no worked example of the gap "
              "and the bound above stands\n    unillustrated.")


def what_is_absent():
    """The four things the format carries no word for, and what absence means."""
    print("\n  what these columns do not carry")
    print("    the intermediate values a byte took between the two endpoints,\n"
          "    the timestamps, the order the changes happened in, and whether\n"
          "    an address with no row here moved at all. A missing row means\n"
          "    \"not found to move in this file\"; it does not mean the byte "
          "was\n    never written.")


def self_test(run=None):
    """Run the committed suite in a subprocess and return its exit code.

    `run` is `subprocess.run` unless a caller passes its own, which is what the
    suite's own case for this mode drives: a `--self-test` case that ran the
    mode for real would have the mode run the suite containing it, which runs
    the case again, and so on.
    """
    cmd = [sys.executable, "-m", "unittest", "discover",
           "-s", TOOL_DIR, "-p", SUITE_FILE]
    proc = (subprocess.run if run is None else run)(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # unittest's summary on one stream, so there is one thing to parse and one
    # thing to print: it writes to stderr, and its verdict is the exit code.
    out = proc.stdout or ""
    if out and not out.endswith("\n"):
        out += "\n"
    # The count decorates and never decides. An expected count in a runner
    # turns every added test into a failure, which is the wrong trade --
    # tools/run-tests.sh gives the same reason for printing its own counts.
    m = re.search(r"^Ran (\d+) tests? ", out, re.M)
    n = int(m.group(1)) if m else 0
    if proc.returncode:
        print(out, end="")
        print(f"{SUITE_FILE}: FAILED")
        return 1
    if not n:
        # A discovery that matched nothing exits 0 and prints OK, which from
        # the outside is indistinguishable from a suite that passed. A renamed
        # file, a moved -s, a pattern that no longer matches: each turns a gate
        # green without running anything, and the moment to notice is before it
        # has stopped failing.
        print(out, end="")
        print(f"{SUITE_FILE}: FAILED -- no test ran, which is not a pass. It "
              f"is discovered at {os.path.relpath(TOOL_DIR)}; if that is not "
              "where the suite is, this mode is looking in the wrong place.")
        return 1
    print(f"{SUITE_FILE}: {n} test{'s' if n != 1 else ''}, passed")
    # The gate's own deferral, in the same place and for the same reason: a run
    # that exercises nothing a reader can see is a check that gets dropped.
    print("\nnote  these are the tool's own refusals over the committed "
          "fixtures in\n      ec/tools/testdata/ and over one committed CSV: "
          "no EC is opened, no register is\n      read back, and no capture "
          "was taken on the machine.")
    return 0


def main(argv=None):
    # `sys.argv[1:]` spelled out because argparse does that itself for a None,
    # and the flag has to be readable before the parser ever sees the list.
    argv = sys.argv[1:] if argv is None else list(argv)
    if "--self-test" in argv:
        return self_test()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary", nargs="+",
                    help="a per-address sweep summary in the "
                         "`addr,change_count,first_old,last_new` shape, with "
                         "its `#` header block dropped before the header is "
                         "read. A change log is refused rather than graded")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero when the `#` block's source-log row "
                         "count and the change_count column do not reconcile. "
                         "Off by default: the source log is not committed, so "
                         "this tool cannot say which figure is wrong, only "
                         "that they differ")
    args = ap.parse_args(argv)

    failed = 0
    for path in args.summary:
        if not os.path.isfile(path):
            print(f"\n{path}: no such file", file=sys.stderr)
            failed = 1
            continue
        try:
            refuse_other_shape(path, fieldnames_of(path))
            if report(path, args.strict):
                failed = 1
        except Refused as exc:
            # Every refusal is a sentence, not an exit code on its own, so the
            # reason a file was not graded travels with the refusal. A refusal
            # that printed nothing but a status would leave the operator
            # looking for a tool to run instead of a shape to fix.
            print(f"\n{path}: not a sweep summary -- {exc}.", file=sys.stderr)
            failed = 1
    return failed


if __name__ == "__main__":
    sys.exit(main())