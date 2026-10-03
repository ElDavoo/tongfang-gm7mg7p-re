#!/usr/bin/env python3
r"""Find the captures in the committed tree whose marks share an instant, and
re-derive what one action's "nothing moved" was read over.

`docs/findings/door-grader-same-timestamp-marks.md` justified the door
grader's refusal from what the committed writers *can* do, and said so in as
many words: "no run has been taken and no operator has been observed". One has
been taken, and it is committed --
`evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv` carries two MARK
rows at `21:21:11.447`, which is the shape that file said was constructible and
had not been observed. This is the tool that says so by counting, rather than
by reading one file, and the one that re-derives the sentence the two documents
holding that capture draw from it.

**It measures and writes nothing.** No EC is opened, no register is read back,
no capture is modified, and every figure in
`docs/findings/perturb-arm-colliding-marks.md` is quoted from this tool's
output with the command beside it, because a figure in that page this tool did
not print is a figure nobody can re-derive.

**Two forms, because the two questions are different.**

*corpus* (no arguments) walks the tree for `*.csv` carrying a MARK row, and for
each one runs the **grader's own** reader (`grade_0751_isolation.read_capture`)
and the **grader's own** comparison (`grade_gpu_door.collided_marks`) rather
than a second copy that could drift. A collision is a property of the door
grader's reading of a file, so it is asked of the door grader.

*one capture* prints what that capture says about itself: the watched set and
the baseline, every mark, every colliding pair, and then -- the part the Fn arm
of §4a needs -- for each pair the interval to the next mark, its elapsed time,
its change-row count and its per-address census; plus, for every watched
address, whether it has **any** change row in the whole capture and what the
baseline value is. That last pair of figures is what makes "held `0x10`"
independent of any window, and it is the reason this form exists rather than a
`grade_gpu_door.py` mode.

**The population is a measurement, never a constant.** The corpus form's totals
belong to the run that printed them, so no count is written into this file, no
date is printed, and the write-up dates the run in prose. A total in a tool
would be a value every added capture has to edit, which is
`ec/tools/check_pin_table_by_cited_file.py`'s lesson at one level up.

**A "no change row" is not "inert".** Nothing here reads the EC, and a byte
absent from a capture's change rows has a level that is not in evidence rather
than a known one: a change-row capture records transitions, not values. That is
why the baseline is printed beside every count, and why `registers.yaml`'s own
caveat -- a byte that held still is not evidence about what the EC does with it
-- travels with these figures rather than being restated by them.

Usage:
    python3 ec/tools/scan_mark_collisions.py                      # the corpus
    python3 ec/tools/scan_mark_collisions.py capture.csv          # one file
"""
import argparse
import os
import sys
from collections import Counter

# Both graders, imported rather than re-implemented. `grade_gpu_door.collided_marks`
# is the *definition* of a collision for this repository -- it is the one that
# refuses, and a second spelling of equality here could disagree with the refusal
# it is describing. `grade_0751_isolation.read_capture` is the strict CSV
# reader the refusal is applied to, so a mark's `ts` here is the same parsed
# datetime the grader compares and not a string read a second way. Both are
# stdlib-only, so importing them costs an offline tool nothing -- and this tool
# takes the watch table from `windows/tools/gpu_block_watch.py` by reference
# rather than re-reading a capture's worth of it here.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grade_0751_isolation as fan
import grade_gpu_door as door
import grade_timer_sweep as sweep

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

# The three directories a `find` from the repository root walks into but the
# committed tree does not hold. `.claude/` is the one that bites and the reason
# is not tidiness: `git worktree add` under `.claude/worktrees/` puts a whole
# second checkout inside this one, so a developer with any worktree open scans
# a population nobody else's run can reproduce. This is the same pruning, for
# the same reason, as `tools/test_readme_suite_table.py`'s `PRUNED` and
# `census_test_line_pins.py`'s; the three should be read together, because one
# suite set defined three ways is three answers.
PRUNED = (".git", ".claude", "vendor", "__pycache__")

# The marker a capture row carries, as a substring of the raw line. A prefilter
# and not the reader: the tree holds many more `*.csv` files than the corpus
# form reports, and the ones this skips are two populations rather than one --
# tables that are not captures at all (an annotations table, a decompile index),
# which `read_capture` refuses, and captures that simply carry no mark row,
# which the same reader accepts and which hold no mark to collide. A file with
# no `,MARK,` in it cannot hold a mark, so asking the text first is what lets
# the population be "files carrying a MARK row" and not "files the strict
# reader happened to accept". It is a *narrowing*,
# never a decision: a file that carries the marker is still read by
# `read_capture`, and a file it refuses is named rather than dropped, so a
# capture the reader cannot open shows up in the population as an unreadable
# one rather than as a file that does not exist.
MARK_SUBSTR = ",MARK,"


def repo_path(path):
    """`path` relative to the repository root, in posix spelling.

    `REPO` is built with `os.pardir` and `os.walk` does not normalise what it
    yields, so the two spellings of one file differ as strings -- the reason
    `measure_mark_provenance.repo_path` exists, and the reason the output here
    is sorted and comparable across runs rather than matching a hand-typed path.
    """
    return os.path.relpath(path, REPO).replace(os.sep, "/")


def marked_captures():
    """Every `*.csv` in the working tree that carries a MARK row, sorted by
    repo-relative path.

    In a clean checkout that is the committed set, and it is the sense in which
    the corpus form's figures are "the committed corpus" -- but the walk reads
    the filesystem, not the index, so an untracked `*.csv` here would be counted
    too. That is the same class of drift `PRUNED` exists for, one level down:
    a population that depends on what is sitting uncommitted in the working tree
    is not a measurement of this tree either. `PRUNED` is walked out of the top
    of the relative path, so a checkout nested at any depth is skipped and not
    only one at the root. The `,MARK,` test is the prefilter above's; nothing
    here decides what a mark *is*, it only decides which files are worth
    handing to the reader that does.
    """
    out = []
    for dirpath, dirs, names in os.walk(REPO):
        dirs[:] = sorted(d for d in dirs if d not in PRUNED)
        for name in names:
            if not name.endswith(".csv"):
                continue
            path = os.path.join(dirpath, name)
            rel = repo_path(path)
            if rel.split("/")[0] in PRUNED:
                continue
            with open(path, encoding="utf-8", errors="replace") as f:
                if any(MARK_SUBSTR in line for line in f):
                    out.append(path)
    return sorted(out, key=repo_path)


def load_capture(path):
    """(marks sorted, changes) for one capture, through the grader's reader.

    Sorted here rather than by each caller, because `collided_marks`'s own
    docstring says it assumes a sorted list -- "Sorted first, so two marks at
    one timestamp are neighbours and one linear pass finds every pair" -- and a
    caller that forgot would be reading a subset of the collisions rather than
    all of them.

    Returns the `ValueError` rather than raising it, so the corpus form can
    name a file the strict reader refuses and carry on to the next one. A
    refusal is a fact about a file, not a reason to stop a scan: dropping it
    silently would make the population smaller than the tree without saying so.
    """
    try:
        marks, changes = fan.read_capture(path)
    except (ValueError, OSError) as exc:
        return None, str(exc)
    return sorted(marks, key=lambda w: w.ts), changes


def report_capture(path):
    """Everything one capture says about itself, read through the graders.

    Two readings of "the Fn arm moved nothing", and the point of the tool is
    that a reader should not have to guess which one a document used:

      * **whole capture** -- a byte with no change row anywhere in the file and
        one value carried, the `0x0751=0x10` on the `# baseline` line. This
        holds over every interval the capture has, so it does not depend on
        where an action boundary was drawn.
      * **pair to the next mark** -- what the door grader's own windowing would
        have graded had it not refused. Printed with its elapsed time, its row
        count and its per-address census, so "nothing but the sweep moved" is a
        measured sentence rather than an absence.

    `load` is the timer grader's, so the watched set and the baseline are that
    procedure's parse of the header rather than a hand-read comment -- which is
    the whole difference between `0x0751` being in the capture and it being
    claimed to be.
    """
    rel = repo_path(path)
    print(f"\n=== {rel} ===")
    marks, changes = load_capture(path)
    if marks is None:
        print(f"  read_capture refused this file: {changes}")
        return None
    print(f"  {len(marks)} mark(s), {len(changes)} change row(s)")

    watched, baseline, rows, span, interval = sweep.load([path])
    if watched is None:
        print("  no `# interval ... addresses:` header line, so there is no "
              "watched set and")
        print("  nothing below can name a baseline. The whole-capture reading "
              "needs one.")
    else:
        print(f"  watched set: {len(watched)} addresses, interval "
              f"{interval}s, span {span:.3f}s")
        print(f"    {' '.join(f'0x{a:04X}' for a in watched)}")

    print("\n  every mark, parsed:")
    for i, w in enumerate(marks):
        print(f"    {i}: {w.ts.isoformat()}  {w.label!r}")

    pairs = door.collided_marks(marks)
    if not pairs:
        print("\n  no adjacent pair shares an instant: `collided_marks` "
              "returns nothing, and")
        print("  grade_gpu_door.py would not refuse this capture.")
    for a, b in pairs:
        print(f"\n  collision: {a.label!r} and {b.label!r} are both "
              f"{a.ts.isoformat()}")
        # The window the door grader would have graded, and the one it refuses
        # to. Printed as an interval rather than as a phrase, because the pair
        # is precisely the case where there is no interval between the two
        # marks themselves.
        #
        # The mark after the *second* of the pair, found by position rather
        # than by `list.index`: `Window` carries no `__eq__`, so an index
        # lookup happens to work by identity today, and a dataclass-shaped
        # `Window` would make it find the wrong mark in a capture that opens two
        # windows with equal fields.
        after = next((n for n, m in enumerate(marks) if m is b), None)
        end = marks[after + 1] if after is not None and after + 1 < len(marks) else None
        if end is None:
            print("    to the end of the capture")
            continue
        elapsed = (end.ts - b.ts).total_seconds()
        inside = sorted((c for c in changes if b.ts < c.ts < end.ts),
                        key=lambda c: c.ts)
        print(f"    the second of the pair to the next mark {end.label!r} at "
              f"{end.ts.isoformat()}:")
        print(f"      {elapsed:.3f}s, and {len(inside)} of the capture's change "
              f"rows fall in it")
        census = Counter(c.addr for c in inside)
        for addr, n in sorted(census.items()):
            # The interval's own count, and named as such rather than printed
            # bare beside the address. `check_capture_claims.py` holds a count
            # in committed prose to the *file's* count for the address nearest
            # it, and this is a count over an interval inside the file: a
            # reader -- and that tool -- cannot tell the two apart from a bare
            # number. Saying which is which is the difference between a figure
            # that is re-derivable and one that reads as a contradiction of the
            # capture.
            print(f"        0x{addr:04X}  {n} of this interval's change rows")
        if not inside:
            print("        no address moved in this interval. That is a "
                  "window of no time,")
            print("        which is what the refusal is about; it is not a "
                  "statement that")
            print("        the byte is inert.")
        else:
            print(f"        {len(census)} distinct address(es) in that "
                  "interval, which is the whole of what moved in it")

    if watched is not None:
        print("\n  every watched address, over the whole capture -- a count of "
              "0 is")
        print("  'no change row in this file', never 'absent' and never "
              "'inert'; a change-row")
        print("  capture records transitions, not values, so the baseline "
              "beside it is the")
        print("  only value the file carries:")
        moved = Counter(r[1] for r in rows)
        for addr in watched:
            n = moved.get(addr, 0)
            base = baseline.get(addr)
            base_s = "no baseline line" if base is None else f"0x{base:02X}"
            verdict = "moved" if n else "no change row in the whole capture"
            print(f"    0x{addr:04X}  baseline {base_s}  {n} change row(s)  "
                  f"{verdict}")
    return pairs


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="*",
                    help="report one capture in full. With none, walk the "
                         "committed tree and report the population instead")
    args = ap.parse_args(argv)

    if args.csv:
        for path in args.csv:
            report_capture(path)
        return 0

    paths = marked_captures()
    unreadable, carried, pairs, total_pairs = [], 0, 0, 0
    print("=== corpus scan: every committed *.csv carrying a MARK row ===")
    # The root is not printed. An absolute path differs per checkout, and the
    # point of this output being date-free is that two runs diff cleanly --
    # which a `/home/runner/...` line under an otherwise stable report would
    # break on the first machine that was not the machine that wrote it.
    print("\nper file:")
    for path in paths:
        marks, changes = load_capture(path)
        if marks is None:
            unreadable.append((repo_path(path), changes))
            print(f"  {repo_path(path)}  UNREADABLE -- {changes}")
            continue
        if not marks:
            # Carries the marker as text and parses to no mark. Worth its own
            # line: it is the case where the prefilter and the reader disagree,
            # and a reader must be able to see that the two did.
            print(f"  {repo_path(path)}  0 mark(s) (the text carries "
                  f"{MARK_SUBSTR!r} but no row parses as one)")
            continue
        carried += 1
        found = door.collided_marks(marks)
        note = f"{len(found)} colliding pair(s)" if found else "no collision"
        print(f"  {repo_path(path)}  {len(marks)} mark(s)  {note}")
        for a, b in found:
            pairs += 1
            total_pairs += 1
            print(f"    {a.label!r} and {b.label!r} are both "
                  f"{a.ts.isoformat()}")

    walked = len(paths)
    print("\n=== this run's population ===")
    print(f"  files walked carrying a MARK row      {walked}")
    print(f"  of those, refused by read_capture     {len(unreadable)}")
    print(f"  files carrying at least one mark      {carried}")
    print(f"  files carrying a colliding pair       {pairs}")
    print(f"  colliding pairs in the whole tree     {total_pairs}")
    for rel, why in unreadable:
        print(f"    unreadable: {rel} -- {why}")
    print("\n  These are this run's figures over this tree, not a census. The")
    print("  population grows with every capture a human takes and commits, so")
    print("  it is quoted from this output with the date and never asserted.")
    print("\n  Reproduce with:")
    print("    python3 ec/tools/scan_mark_collisions.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
