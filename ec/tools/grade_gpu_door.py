#!/usr/bin/env python3
r"""Apply §5 of docs/hardware-tests/gpu-tgp-07c4-07d7-door.md to a capture,
mechanically, so the ordering half of the door question is read off the CSV
rather than off a terminal scrollback.

Input is exactly what §3 already produces: the `gpu_block_watch.py --csv
--mark` capture, `ts,addr,old,new` change rows and `ts,MARK,,label` marks, in
the schema `ec_watch.py` writes and the watcher emits byte for byte. Each mark
opens a window that runs to the next mark, and for every window this reports

  * what moved in `0x07C4`-`0x07D7` (§5 column 3, the ACPI half), each hit
    with its ECMG field-list name, which is the column's parenthetical
  * what moved in `0x0743`-`0x0746` (§5 column 4, the half the service's own
    `GpuFeatures` class writes -- windows/vendor-ec-map.md:84-87)
  * which of the two moved first and by how many milliseconds (§5 column 5),
    or that there is no ordering to report because only one block moved, or
    neither did
  * a `net` / `total` / `max` line for all 24 watched addresses whether or not
    they moved

That last list is the point. A change row is an endpoint difference between
two of the watcher's own sweeps, so a byte that went somewhere and came back
between them reads as quiet -- and `net`, the endpoint figure, is blind to
exactly that while `total`, the movement the byte actually took, is not. The
other reason every address gets a line is the one §4c's retraction is about: a
byte that held still is a line of zeros, not a missing line, because absence
reads as missing data rather than as the strongest negative this procedure can
produce.

**Marks are not merged, on purpose.** `grade_0751_isolation.py` fuses marks
within `MARK_MERGE_SECONDS` because §3 of *that* procedure runs one watcher per
console, so a single action lands as several MARK rows seconds apart and a
window that opened twice would report "nothing moved" for half of it. This
procedure runs **one** watcher on one console, and §3 says "mark, act, hold,
mark" -- one mark per action boundary. Fusing two here would attribute the
second action's movement to the first, which is the mis-attribution the merge's
own docstring warns against. Two marks close together are reported as two
windows, and their distance is printed so a reader can see that they were close
and judge for itself whether they were one action.

**The ms figure is a sweep, not a clock.** Both timestamps are the sweeps that
saw the change, so the delta between them is good to about one `--interval`
(0.25 s by default) and no better. It is printed in milliseconds because §5's
column is in milliseconds, not because a millisecond was measured.

**This fills five of §5's ten columns and says so.** Columns 1-5 come out of
this capture. Columns 6-9 -- the ProcMon PID, the process image, the IOCTL code
on the `\.\ACPIDriver` handle and the loaded-module list -- are §4a's, read off
a Windows `.PML` that no tool in this repository can open, and column 10 is the
human's call against §6. A table with only the five this fills is half a table,
and must not read as a complete one.

**Nothing here is a verdict.** §6's three-way reading needs the PID and the
IOCTL code, which are not in a capture; what the windows settle is the
ordering. And two caveats travel with every figure: a zero is "not moved by
this method under this action", never "absent"; and a readback is not an
effect -- which for this procedure is stronger than usual, because nothing in
it writes anything. `0x07D0`/`0x07D1` are `DO-NOT-WRITE-BLIND` in
ec/annotations/registers.yaml, and this tool has no write path, like the
watcher whose output it reads.

Nothing here touches hardware; it reads files only.

Usage:
    python3 ec/tools/grade_gpu_door.py <date>-gpu-door-07c4-07d7.csv
"""
import argparse
import sys

# The CSV vocabulary, not the 0751 procedure's watched sets: `read_capture`,
# `Window` and `window_delta` are the schema and the three movement figures
# both graders print, and re-deriving them here would be a second copy to
# drift. `grade_0751_isolation` imports nothing but stdlib, so importing it
# costs an offline grader nothing -- the reason
# `windows/tools/gpu_block_watch.py` cannot be imported for the same job is
# written where it matters, over DS_NAMES below.
import grade_0751_isolation as fan

# The two blocks, in the order §5's result table reads them. Held against
# `gpu_block_watch.WINDOWS` by windows/tools/test_gpu_block_watch.py, because
# an ordering read off one set of bounds and captured against another is the
# drift #266 found in the procedure's own copy of the watch table.
WINDOWS = (("0x07C4-0x07D7", 0x07C4, 0x07D7),
           ("0x0743-0x0746", 0x0743, 0x0746))

# §5's column 3 ends in "(DSDT name)", so a movement without its ECMG
# field-list name is not the cell. Transcribed here rather than imported:
# `gpu_block_watch` does `from ecrw import Ec, EcError`, and `ecrw` binds
# kernel32 at import time, so it loads only on Windows -- importing it would
# make an offline grader Windows-only, which is the one thing a grader that
# has to be runnable before a human owns a laptop cannot be. The same test
# holds these 24 pairs against the watcher's own `WATCH` table, which
# CitationTableTests holds against evidence/acpi/dsdt.dsl, so the chain from
# the DSDT to this file is checked rather than assumed.
DS_NAMES = (
    (0x0743, "GNEN b0, ECDC b1"),
    (0x0744, "CTVA"),
    (0x0745, "DBCT"),
    (0x0746, "MXDB"),
    (0x07C4, "DBEN b3, DBST b5"),
    (0x07C5, "WHMS b5"),
    (0x07C6, "WMS0 b0-1"),
    (0x07C7, "(no DSDT field)"),
    (0x07C8, "(no DSDT field)"),
    (0x07C9, "(no DSDT field)"),
    (0x07CA, "(no DSDT field)"),
    (0x07CB, "(no DSDT field)"),
    (0x07CC, "(no DSDT field)"),
    (0x07CD, "(no DSDT field)"),
    (0x07CE, "(no DSDT field)"),
    (0x07CF, "(no DSDT field)"),
    (0x07D0, "DBD1"),
    (0x07D1, "DBD2"),
    (0x07D2, "(no DSDT field)"),
    (0x07D3, "GFID b4-6"),
    (0x07D4, "CPUA"),
    (0x07D5, "DBAP"),
    (0x07D6, "DBSP"),
    (0x07D7, "CGCT"),
)

# How close two marks have to be to be worth flagging, in seconds. A warning
# and nothing else: the marks stay separate windows whatever this says, and the
# threshold only decides whether the distance is called out. It is the 0751
# grader's `MARK_MERGE_SECONDS` on the same 5 s scale because the scale is
# about human hands, not about either procedure -- §3's "hold ~30 s after
# each action" is the thing that keeps a real action boundary far from this.
CLOSE_MARKS_SECONDS = 5


def window_of(addr):
    for label, start, end in WINDOWS:
        if start <= addr <= end:
            return label
    raise KeyError(f"0x{addr:04X} is not in a watched window")


def name_of(addr):
    for a, name in DS_NAMES:
        if a == addr:
            return name
    raise KeyError(f"0x{addr:04X} has no ECMG field-list name in DS_NAMES")


def build_windows(marks, changes):
    """Assign every change to the last mark at or before it, marks unmerged.

    `grade_0751_isolation.build_windows` is this pass and starts by calling
    `coalesce_marks`; the merge is the only thing wrong with it here, and its
    docstring says the fusing exists for a three-console run this procedure
    does not have. So the pass is repeated rather than the module edited --
    issue #169 is open on that file, and a change to it made from here would
    collide with that work in review for no gain.

    Changes before the first mark belong to no window, exactly as they do
    there: §3 lets the sweep settle before the operator marks, so they are the
    settling noise rather than a reaction. They still set the level each window
    opened on, which is what lets a held byte print its level instead of
    `????`.
    """
    ordered = sorted(changes, key=lambda c: c.ts)
    last, i = {}, 0
    while i < len(ordered) and ordered[i].ts < marks[0].ts:
        last[ordered[i].addr] = ordered[i].new
        i += 1
    for n, w in enumerate(marks):
        w.levels = dict(last)
        end = marks[n + 1].ts if n + 1 < len(marks) else None
        while i < len(ordered) and (end is None or ordered[i].ts < end):
            w.changes.append(ordered[i])
            last[ordered[i].addr] = ordered[i].new
            i += 1
    return marks


def first_change(w, addrs):
    """(timestamp, address) of the earliest change in one block, or None.

    `min` on the timestamp rather than `hits[0]`, so the answer does not
    depend on the caller having kept the change rows in time order.
    """
    hits = [c for c in w.changes if c.addr in addrs]
    if not hits:
        return None
    first = min(hits, key=lambda c: c.ts)
    return first.ts, first.addr


def report_window(w, n, total):
    end = "the next mark" if n < total else "the end of the capture"
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
    print(f"    window runs to {end}")

    firsts = {}
    for label, lo, hi in WINDOWS:
        addrs = range(lo, hi + 1)
        hits = [c for c in w.changes if c.addr in addrs]
        firsts[label] = first_change(w, addrs)
        # Distinct addresses, not change rows: a byte that steps twice inside
        # one window is one address that moved, and counting its rows here
        # would put "3 of 20 addresses moved" over a window where exactly one
        # did. The row count is printed alongside when the two differ, because
        # a byte that went somewhere and came back is the case where it does.
        moved_addrs = {c.addr for c in hits}
        rows = (f", {len(hits)} change rows" if len(hits) > len(moved_addrs)
                else "")
        print(f"    {label}: {len(moved_addrs)} of {len(addrs)} addresses "
              f"moved{rows}")
        if not hits:
            # Stated, not omitted. §5's column is a cell whether the cell is
            # empty of movement or empty of data, and only one of those is a
            # result -- so the line is the difference.
            print("      nothing in this block moved by this method under "
                  "this action")
            continue
        for c in hits:
            dt = (c.ts - w.ts).total_seconds()
            print(f"      0x{c.addr:04X}  0x{c.old:02X} -> 0x{c.new:02X}"
                  f"   (+{dt:.1f}s)   {name_of(c.addr)}")

    # The ordering, which is the question the procedure is named for and the
    # one figure the watcher's console summary prints once over the whole run
    # and nowhere per action. A block that did not move has no first change,
    # so this is where "only one block moved" has to be said rather than left
    # as a missing half of a comparison.
    moved = [label for label in firsts if firsts[label]]
    if len(moved) == len(WINDOWS):
        # Keyed on the timestamp, not on the tuple's own order: the labels sort
        # as strings and `0x0743-0x0746` < `0x07C4-0x07D7`, so an unkeyed sort
        # names the host half as leading every time the ACPI half did.
        (a_label, a_first), (b_label, b_first) = sorted(
            ((label, firsts[label]) for label in moved),
            key=lambda pair: pair[1][0])
        lead_ms = abs((a_first[0] - b_first[0]).total_seconds()) * 1000
        # Offsets from the mark rather than wall-clock timestamps, because
        # that is the form the change rows above are printed in and the form
        # §5's cell is read in.
        print(f"    which block moved first: {a_label} "
              f"(0x{a_first[1]:04X}, +{(a_first[0] - w.ts).total_seconds():.1f}s"
              " after the mark)")
        print(f"      led {b_label} "
              f"(0x{b_first[1]:04X}, +{(b_first[0] - w.ts).total_seconds():.1f}s"
              f" after the mark) by {lead_ms:.0f} ms")
    elif moved:
        only = moved[0]
        print(f"    no ordering to report: only {only} moved, and one block "
              "cannot lead")
    else:
        print("    no ordering to report: neither block moved in this window")

    # Every watched address, in WINDOWS order, moved or not. The three figures
    # are not interchangeable and the reason is the byte that went somewhere
    # and came back: `net` is the endpoint difference and is blind to that,
    # `total` is the movement the byte took and is not, and `max` is how far it
    # got from the value the window opened on. A byte that never appears in the
    # change rows has a level that is not in evidence rather than a known one,
    # and says so -- a change-row capture records transitions, not values.
    print("    every watched address, moved or not -- a zero is 'not moved by "
          "this method under")
    print("    this action', and it is a stated line rather than a missing one:")
    for label, lo, hi in WINDOWS:
        print(f"      {label}:")
        for a in range(lo, hi + 1):
            print(f"        {fan.window_delta(w, a)}")
    return moved


def report_close_marks(windows):
    """Call out adjacent marks that landed within CLOSE_MARKS_SECONDS.

    Not a merge, and not a warning about the capture: the two stay two
    windows, because §3 paces them ~30 s apart and a run where they are not
    is a run whose pacing is worth seeing. What it is for is the reader who
    expected one action boundary and got two -- the first window's figure is
    the one to distrust, and this is where that is said out loud rather than
    left to be worked out.
    """
    for a, b in zip(windows, windows[1:]):
        gap = (b.ts - a.ts).total_seconds()
        if gap <= CLOSE_MARKS_SECONDS:
            print(f"\n  note  marks {a.label!r} and {b.label!r} are {gap:.1f}s "
                  f"apart, inside the {CLOSE_MARKS_SECONDS}s flag threshold.")
            print("    They stay two windows. The 0751 grader fuses marks this "
                  "close because")
            print("    that procedure runs one watcher per console and one "
                  "action lands in all")
            print("    three; this one runs a single watcher on a single "
                  "console with one mark per")
            print("    action boundary, so fusing them here would file the "
                  "second action's movement")
            print(f"    under the first. If they were one action after all, "
                  f"the window headed")
            print(f"    by {a.label!r} is the one to distrust.")


def report_columns():
    """Which of §5's ten columns this tool fills, and which it does not.

    Named rather than implied, because the failure this guards is a reader
    filling five cells and handing on a table that looks finished. The five it
    does not fill are not deferred work either: four are §4a's Windows `.PML`,
    which nothing in this repository can open, and the fifth is a judgement.
    """
    print("\n=== §5's ten columns ===")
    print("  Filled from the capture above:")
    print("    mark label                     col 1  -- each window's heading")
    print("    mark ts                        col 2  -- ditto")
    print("    0x07C4-0x07D7 addresses moved  col 3  -- the ACPI half, DSDT "
          "names")
    print("    0x0743-0x0746 addresses moved  col 4  -- the host half")
    print("    which block first, and by how many ms  col 5  -- the ordering "
          "lines")
    print("  NOT filled here, so a table carrying only the five above is half a "
          "table.")
    print("  Columns 6-9 are §4a's ProcMon half, read off a Windows `.PML` that")
    print("  no tool in this repository opens:")
    print("    ProcMon PID                    col 6")
    print("    process image                  col 7")
    print("    IOCTL code on the \\.\\ACPIDriver  col 8")
    print("    modules loaded at that instant col 9")
    print("  And column 10 is the human's call against §6 in every case:")
    print("    verdict                        col 10")


def report_settle(orders):
    """The closing section, in §6's own order of what it does and does not do.

    `orders` is the per-window list of which blocks moved, so each shape is
    described from the capture rather than from a template. The three branches
    are deliberately not collapsed: "one block moved" is neither of §6's other
    two readings, and a closing line that said §6's third bullet for a run in
    which the ACPI half moved twice would be the tool making the human's call.
    """
    print("\n=== what this does and does not settle ===")
    ranked = [o for o in orders if len(o) == len(WINDOWS)]
    if ranked:
        print(f"  Both blocks moved in {len(ranked)} of the windows above, so "
              "§5's ordering column has a")
        print("  number in them. That is the half of §6's first bullet this "
              "capture can carry:")
        print("  the other half -- that `0x07D0` moved under a GPU-only change "
              "with no host `ECRW` at")
        print("  the mark -- needs the PID and the IOCTL code, which are §4a's "
              "and in no capture.")
    elif any(orders):
        one = sum(1 for o in orders if len(o) == 1)
        print(f"  No window had both blocks moving ({one} of {len(orders)} "
              "moved one block only), so §5's")
        print("  ordering column has no number in any of them, and that "
              "matches none of §6's three")
        print("  readings as written: the first needs both halves of a "
              "movement and the PID with it,")
        print("  the second is movement only when the Fn bundle runs, the third "
              "is no movement at")
        print("  all. Which of them a one-block run is comes down to the mark "
              "labels, and the verdict")
        print("  column is the human's call against §6.")
    else:
        print("  Neither block moved in any window above, so §6's third "
              "bullet -- no movement at")
        print("  all under all three actions -- applies, and the clobber "
              "hazard stands where §4o")
        print("  records it. Whether the actions were in fact taken is the "
              "operator's record, not")
        print("  this file's: a mark is the only evidence that anything "
              "happened, and this tool")
        print("  reads marks.")

    for line in (
        "  Two caveats belong next to the table rather than in a footnote.",
        "      * A zero is 'not moved by this method under this action', "
        "never 'absent',",
        "        'unused' or 'unreferenced'. A change row is an endpoint "
        "difference between",
        "        two of the watcher's own sweeps, so a byte that moved and "
        "came back between",
        "        them reads as quiet -- which is why every address has a "
        "`net`/`total`/`max` line",
        "        above, and why `total` is the figure to read a move-and-"
        "return from.",
        "        docs/findings.md §4c retracted a 'does not exist' claim built "
        "on a zero-",
        "        reference scan; a zero here is the same shape of claim.",
        "      * A readback is not an effect. Nothing in this procedure checks "
        "whether the EC",
        "        acted on a byte, and it is stronger than usual here: nothing "
        "in it writes at",
        "        all. `0x07D0`/`0x07D1` are DO-NOT-WRITE-BLIND in",
        "        ec/annotations/registers.yaml, and neither this tool nor the "
        "watcher it grades",
        "        has a write path.",
        "      * The ms figure is good to about one `--interval` (0.25 s by "
        "default), not to",
        "        the millisecond it is printed in: both timestamps are the "
        "sweeps that saw the",
        "        change, not the instant the byte moved.",
    ):
        print(line)

    print("  What a passive capture cannot do, said here so §6 is not read as "
          "if it could:")
    print("  it cannot decide the `DBEN` identification "
          "(ec/annotations/ec-07c4-07d5-sites.md §9),")
    print("  and it does not attribute the 2026-09-23 `0x07C4` "
          "`0x08`->`0x28`->`0x38` writes that file's §8")
    print("  records as unattributed. A procedure that settles nothing is still "
          "a result; one")
    print("  that is read as settling that is not.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="gpu_block_watch.py --csv --mark capture(s)")
    args = ap.parse_args(argv)

    marks, changes = [], []
    for path in args.csv:
        m, c = fan.read_capture(path)
        marks += m
        changes += c
        print(f"{path}: {len(m)} mark(s), {len(c)} change row(s)")

    if not marks:
        print("\nno MARK rows in these captures. gpu_block_watch.py writes "
              "them only with --mark,", file=sys.stderr)
        print("and without them a window has no start, so which action a "
              "movement belongs to is", file=sys.stderr)
        print("not knowable and §5 cannot be filled at all.", file=sys.stderr)
        return 1

    marks = sorted(marks, key=lambda w: w.ts)
    build_windows(marks, changes)
    print(f"\n=== {len(marks)} window(s), one per mark, none merged ===")
    orders = []
    for i, w in enumerate(marks, 1):
        orders.append(report_window(w, i, len(marks)))
    report_close_marks(marks)
    report_columns()
    report_settle(orders)
    return 0


if __name__ == "__main__":
    sys.exit(main())
