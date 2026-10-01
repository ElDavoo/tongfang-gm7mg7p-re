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

**A shared timestamp is refused, not fused.** There is no interval to judge
there, so the paragraph above's answer -- two windows, and let the reader
decide -- has nothing to decide with: `build_windows` gives the first of the
pair a span of `[t, t)`, it takes no change row, and every watched address
prints `????` for want of a level. The window count then reads one higher than
the number of actions in the capture, and `report_close_marks` hands the 0.0s
gap back as a question about pacing that this file cannot answer. `main` stops
before it builds any window.

**The grader owns that, not the writer**, for the reason the repeat refusal
below gives its own: a rule at the writer is a rule in `Marker`, whose contract
is to take whatever the operator types because `gpu_block_watch.py` hands it
free-form labels, and a capture assembled by hand from two files never passes a
writer at all. Refusing rather than fusing is the same answer the paragraph
above gives for a different reason -- fusing these two would assert they were
one action, and the 0751 grader fuses at `MARK_MERGE_SECONDS` because *that*
procedure runs one watcher per console and knows its three rows are one press.
The decision, and what a shared timestamp costs here, are in
docs/findings/door-grader-same-timestamp-marks.md.

**A capture is named once.** §3 runs one watcher on one console, so a file
listed twice is one console and not two, and `main` refuses it -- by resolved
path, so `x.csv`, `./x.csv` and a symlink to it are one repeat -- before it
reads anything. The rule is `grade_0751_isolation.distinct_captures`, the same
one the 0751 grader ships and tests, because the premise under it is the same
one: one file is one console however many times it is listed. What a repeat
costs is *not* the same, which is why this is not that grader's message copied.
There, a file agreeing with itself satisfies every cross-console check, so a
fat-fingered duplicate reads as a passing comparison. Here nothing is compared
between files at all: a repeat puts one console's marks in twice as many
windows, the duplicates landing on one timestamp, so half the windows are
zero-length, empty, and print `????` for every address; every change row prints
twice and is counted as `2 change rows`; and `report_close_marks` is handed two
marks 0.0s apart to hand back as a question about the operator's pacing. The
paragraph above is itself the argument for the rule: marks stay unfused
*because* there is one console, so one console's marks twice is not two sets of
action boundaries. Refusing a repeat rather than a second positional outright
is also what leaves `grade_timer_sweep.py`'s documented "one or more CSVs" alone.
Both decisions, and what a repeat costs each, are written up in
docs/findings/grader-repeated-capture.md.

**A capture is its own run.** A path may name more than one, and each file is
graded as a run of its own: windows are cut inside the file that headed them,
so a change row can only be filed under a mark from the capture that recorded
it, and each capture's §6 closing counts its own windows. The premise is the
one above -- one watcher on one console, one mark per action boundary -- read
one file at a time, and the alternative (one path, full stop) was declined in
`docs/findings/grader-repeated-capture.md` so that the three `nargs="+"`
capture graders keep one rule over one input shape. The whole of it is that a
capture's rows are graded against its own marks and nothing else, so a change
row of one file falling between two marks of another is a row of the first,
filed under a mark of the first, exactly as it would be if the other capture
had not been named. Nothing here depends on the two captures being far apart in
time, which is the shape `ec_watch.py` and `gpu_block_watch.py` produce when
both are run at once.

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


def collided_marks(marks):
    """The adjacent pairs of marks carrying one instant, over a sorted list.

    Equality and nothing else. `CLOSE_MARKS_SECONDS` owns how close is too
    close, and it stays a flag the reader judges over; this owns only the case
    where there is no interval at all, and widening it to a proximity test
    would quietly take over the 5s threshold's job and undo the deliberate
    no-merge decision above it.

    Sorted first, so two marks at one timestamp are neighbours and one linear
    pass finds every pair -- `main` sorts before calling.

    On the parsed datetime rather than on the string, because that is what the
    reader produced: `12:00:10.000+01:00` and `12:00:10+01:00` are one instant,
    and so is the same instant written at another UTC offset. A capture
    assembled by hand spells both, and a string compare would call them two
    marks.
    """
    return [(a, b) for a, b in zip(marks, marks[1:]) if a.ts == b.ts]


def capture_runs(paths, marks, changes):
    """[(source, marks, changes)] per capture, in the order they were read.

    The grouping, and it is the whole of what makes a capture its own run: a
    window may only be cut from marks and change rows that came out of the
    same file, so a row from one capture can never be filed under a mark from
    another. Keyed on `fan.capture_key` rather than on `source`, for the
    reason that function gives -- `read_capture` stores the path *as given*
    while `distinct_captures` keys the resolved one, so a run handed one file
    under two spellings would otherwise come back as two captures and each
    half would report itself as the whole of a run it is not.

    Seeded from `paths` rather than from the rows, so a capture carrying
    neither a mark nor a change row is still one run. A file the operator
    named is a run they expect §6 to say something about, and building the
    list from the rows alone would drop it from the report without saying so
    -- a §6 reading missing rather than a §6 reading of "nothing was
    recorded", which is the difference `docs/findings.md` §4c is about.

    Read order rather than sorted, so the report walks the captures the way
    the command line named them and the per-capture closings stay beside the
    windows they close. Marks and rows inside a capture are sorted by
    `main`, which is where the order of one capture is decided.
    """
    order, runs = [], {}
    for path in paths:
        key = fan.capture_key(path)
        if key not in runs:
            runs[key] = (path, [], [])
            order.append(key)
    for row, is_mark in [(m, True) for m in marks] + [(c, False)
                                                       for c in changes]:
        key = fan.capture_key(row.source)
        if key not in runs:
            # A row whose capture is not in `paths` cannot happen through
            # `main`, which reads the rows out of exactly those files. The
            # branch is here rather than an index error because a caller
            # passing one path list and rows from another should get a run
            # for the file the row names, not a KeyError three functions up.
            runs[key] = (row.source, [], [])
            order.append(key)
        runs[key][1 if is_mark else 2].append(row)
    return [runs[key] for key in order]


def build_windows(runs):
    """Assign every change to the last mark at or before it, per capture.

    `capture_runs`' triple in, `(source, marks)` out, one entry per capture.
    The same pass as `grade_0751_isolation.build_windows` and for the same
    reason it is repeated rather than that module edited: it starts by calling
    `coalesce_marks`, and the merge is the only thing wrong with it here,
    because its docstring says the fusing exists for a three-console run this
    procedure does not have. Issue #169 is open on that file, and a change to
    it made from here would collide with that work in review for no gain.

    The other difference from that pass is the grouping, and it is this
    module's own: it is handed one capture at a time rather than everything
    the command line named. Concatenating first is what filed `b.csv`'s rows
    21 hours after `a.csv`'s last mark and under it, with nothing in the
    report saying two captures had been handed in at all.

    Changes before the first mark belong to no window, exactly as they do
    there: §3 lets the sweep settle before the operator marks, so they are the
    settling noise rather than a reaction. They still set the level each window
    opened on, which is what lets a held byte print its level instead of
    `????`.
    """
    out = []
    for source, marks, changes in runs:
        ordered = sorted(changes, key=lambda c: c.ts)
        marks = sorted(marks, key=lambda w: w.ts)
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
        out.append((source, marks))
    return out


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
    # The file is named on the "runs to" line as well as on the heading
    # above it, and that is the repetition the per-capture cut needs rather
    # than a stylistic one: the line says where this window *ends*, and after
    # the cut that is a mark in `w.source` or the end of `w.source`, so a
    # reader who took "the next mark" to mean the next mark in the whole run
    # would be reading a mark a day away into a window that does not contain
    # it. The last window of a capture runs to that capture's end, not to a
    # mark another file recorded later.
    end = (f"the next mark in {w.source}" if n < total
           else f"the end of {w.source}")
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


def report_close_marks(runs):
    """Call out a file boundary, and adjacent marks within CLOSE_MARKS_SECONDS.

    Two checks over one flat sequence of marks, the sequence carrying each
    capture's own boundaries and the line between two captures. A boundary is
    a fact about the command line whatever the marks say, and the marks either
    side of it are not adjacent marks in one capture at all -- there is no
    interval between them to be close or far. The boundary note names both
    files and says they are two runs, which is what a reader of two day-apart
    captures needs and what nothing else in the report says.

    A pair spanning a boundary gets the boundary note and not the threshold
    one, and that is the whole of the ordering: `CLOSE_MARKS_SECONDS` asks
    whether two action boundaries were close, which is a question about one
    console's hands, and it has no answer to give about where one capture
    ended and the next began. Every pair inside a capture is still walked, the
    last capture's included -- one sequence rather than a loop per capture, so
    a run of one file walks its own pairs exactly as it did before.

    Captures are walked in the order the command line named them, not in
    chronological order, and the gap is taken as a distance for that reason.
    Naming them the other way round is a well-formed command line and prints
    the same note with the same two files in it; a boundary is a fact about
    the command line either way.

    The threshold check is unchanged and is not a merge, and not a warning
    about the capture: the two stay two windows, because §3 paces them ~30 s
    apart and a run where they are not is a run whose pacing is worth seeing.
    What it is for is the reader who expected one action boundary and got two
    -- the first window's figure is the one to distrust, and this is where that
    is said out loud rather than left to be worked out.
    """
    flat = [w for _, marks in runs for w in marks]
    for a, b in zip(flat, flat[1:]):
        # By absolute value, because this walk follows the order the captures
        # were named in rather than the order they happened: grading
        # `later.csv` then `earlier.csv` puts the later capture's last mark
        # first, and the difference comes out negative. A gap is a distance
        # between two instants and has no sign, and the note says "apart".
        # Sorting the flat sequence by timestamp instead would fix the figure
        # for captures that are far apart and make it worse for the ones that
        # overlap: their marks interleave, so the boundary is crossed more
        # than once and the crossings after the first are negative anyway.
        gap = abs((b.ts - a.ts).total_seconds())
        if fan.capture_key(a.source) != fan.capture_key(b.source):
            print(f"\n  note  {a.source} ends at {a.label!r} and {b.source} "
                  f"begins at {b.label!r}, {gap:.1f}s apart.")
            print("    They are two captures and two runs, graded one after "
                  "the other. No window")
            print("    crosses the line between them: each capture's windows "
                  "are cut from its own")
            print("    marks, so a change row is filed only under a mark from "
                  "the file that recorded it,")
            print("    and each closing below counts one capture's windows. A "
                  "figure over both would")
            print("    be a figure over a run that was not performed, which "
                  "is what the per-capture")
            print("    count is there to prevent.")
            continue
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
            print("    under the first. If they were one action after all, the "
                  "window headed")
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


def report_settle(runs, orders):
    """The closing section, in §6's own order of what it does and does not do.

    `orders` is one per-capture list of which blocks moved, so each shape is
    described from its own capture rather than from a template. The three
    branches are deliberately not collapsed: "one block moved" is neither of
    §6's other two readings, and a closing line that said §6's third bullet for
    a run in which the ACPI half moved twice would be the tool making the
    human's call.

    A closing per capture, and the counts in it are that capture's own
    windows. Summed over two day-apart files they read as one run's figures
    over a run nobody performed -- "3 of 3 moved one block only" across two
    days -- and every count in the section is a denominator over windows, so
    the closing is where the per-capture cut is most load-bearing.
    """
    print("\n=== what this does and does not settle ===")
    for (source, _), own in zip(runs, orders):
        print(f"  -- {source} --")
        ranked = [o for o in own if len(o) == len(WINDOWS)]
        if not own:
            # Stated rather than passed over. A capture with no mark row has
            # no window and so no §6 reading, and the "Neither block moved in
            # any window above" branch would say exactly that while implying
            # a result -- the shape docs/findings.md §4c is about, arrived at
            # through a window count of zero rather than a zero movement. The
            # capture holds no rows either, so there is nothing it could have
            # shown; that is what this says, and it is not a claim that the
            # bytes held still.
            print("  This capture carries no MARK row and no change row, so it "
                  "has no window and")
            print("  §6 has nothing to read here. That is a statement about "
                  "the file, not about the")
            print("  bytes: nothing was recorded, which is not the same as "
                  "nothing moved.")
            continue
        if ranked:
            print(f"  Both blocks moved in {len(ranked)} of the windows above,"
                  " so §5's ordering column has a")
            print("  number in them. That is the half of §6's first bullet "
                  "this capture can carry:")
            print("  the other half -- that `0x07D0` moved under a GPU-only "
                  "change with no host `ECRW` at")
            print("  the mark -- needs the PID and the IOCTL code, which are "
                  "§4a's and in no capture.")
        elif any(own):
            one = sum(1 for o in own if len(o) == 1)
            print(f"  No window had both blocks moving ({one} of {len(own)} "
                  "moved one block only), so §5's")
            print("  ordering column has no number in any of them, and that "
                  "matches none of §6's three")
            print("  readings as written: the first needs both halves of a "
                  "movement and the PID with it,")
            print("  the second is movement only when the Fn bundle runs, the "
                  "third is no movement at")
            print("  all. Which of them a one-block run is comes down to the "
                  "mark labels, and the verdict")
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

    if len(runs) > 1:
        print(f"  The {len(runs)} captures above are separate runs. Each "
              "closing above counts one file's")
        print("  windows and the caveats below hold for every one of them; a "
              "figure over the lot is")
        print("  not a figure over any run that was performed.")

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
                    help="gpu_block_watch.py --csv --mark capture(s), and "
                         "never the same file twice -- §3 runs one watcher on "
                         "one console, so a file listed twice is one console "
                         "and not two, and its marks would open windows that "
                         "are empty. By resolved path, so ./x.csv and x.csv "
                         "are the same repeat. Two or more files are two runs, "
                         "graded one after the other: each file's windows are "
                         "cut from its own marks and each file's closing "
                         "counts its own windows, so a change row is never "
                         "filed under a mark from another file. A file's rows "
                         "are graded the same way whether or not they fall "
                         "between another file's marks: one is filed under a "
                         "mark of the file that recorded it")
    args = ap.parse_args(argv)

    # Before the read loop rather than inside it: a report printed over four
    # windows and then refused is a half-right report, and the operator has to
    # be told which files they handed in before any of them is read rather than
    # left to infer it. The same input shape the 0751 grader refuses, for the
    # same reason and by the same one spelling of the test.
    paths, repeats = fan.distinct_captures(args.csv)
    if repeats:
        for given, first, resolved in repeats:
            if given == first:
                print(f"\n{given!r} is given twice, and both times it is "
                      f"{resolved}.", file=sys.stderr)
            else:
                print(f"\n{given!r} and {first!r} are both {resolved}.",
                      file=sys.stderr)
        # The consequences named are this grader's own, so the reader is not
        # sent looking for damage somewhere else -- and the one figure a repeat
        # does *not* move is named as firmly, because `first_change` takes the
        # earliest timestamp and rows duplicated at one timestamp collapse.
        print("A capture given twice is one console and not two, so nothing "
              "was read: its two marks would have opened four windows, two of "
              "them zero-length and empty, with all 24 addresses printing as "
              "`????` because a window that spans no sweep has no level to "
              "print; every change row would have been counted twice as `2 "
              "change rows`; and `report_close_marks` would have been handed "
              "two marks 0.0s apart to hand back as a question about the "
              "operator's pacing rather than as a duplicate. What a repeat does "
              "not change is §5's millisecond figure: the first change in a "
              "block is the earliest timestamp, so rows duplicated at one "
              "timestamp collapse and the ordering comes out the same. Name "
              "the capture once.", file=sys.stderr)
        return 1

    marks, changes = [], []
    for path in paths:
        m, c = fan.read_capture(path)
        marks += m
        changes += c
        print(f"{path}: {len(m)} mark(s), {len(c)} change row(s)")

    # One run per capture, and the per-file census above is what says so: the
    # counts are per file because `read_capture` is called per file, and the
    # two have to agree about what a run is or the reader has a per-file count
    # over a window count taken some other way.
    runs = capture_runs(paths, marks, changes)
    for _, own_marks, _ in runs:
        own_marks.sort(key=lambda w: w.ts)

    # The no-marks refusal, per capture rather than over the whole run. The
    # old check asked only whether *any* capture had a mark, which was the
    # question a single-capture invocation could ask and is the wrong one the
    # moment a second file is named: a capture carrying change rows and no
    # mark row has rows that belong to no window of its own, and under the
    # per-`source` cut below they cannot be filed under another capture's mark
    # either. §5 has no column for them, so the run is refused by name rather
    # than reported over silently.
    #
    # A capture with neither marks nor rows is not refused: it contributes no
    # windows and no movement, so there is nothing to misfile and nothing to
    # leave out of a table. It is said so on its census line above, which is
    # where a reader looks, rather than refused over a file that holds nothing.
    markless = [source for source, own_marks, own_changes in runs
                if own_changes and not own_marks]
    if markless:
        for source in markless:
            print(f"\n{source} has change rows and no MARK rows. "
                  "gpu_block_watch.py writes", file=sys.stderr)
            print("marks only with --mark.", file=sys.stderr)
        print("A window has no start without a mark, so which action those "
              "rows belong to is not knowable", file=sys.stderr)
        print("and §5 cannot be filled at all -- for that capture or, since "
              "its rows cannot be read as", file=sys.stderr)
        print("another capture's either, for the others. Nothing was graded.",
              file=sys.stderr)
        return 1

    # After the read, where the repeat refusal above cannot be: a shared
    # timestamp is a property of the marks, so there is nothing about the
    # command line to look at first. And before `build_windows`, so no
    # zero-length window reaches `report_window` -- a report over one is
    # half-right rather than wrong, which is the shape the no-marks refusal
    # above is written against too. Per capture, and per capture is the whole
    # of the change: a mark in one file and a mark in another are two
    # windows in two runs, and only two marks *in one capture* are the
    # ambiguity this refusal is about.
    collisions = [pair for source, own_marks, _ in runs
                  for pair in collided_marks(own_marks)]
    if collisions:
        watched = sum(hi - lo + 1 for _, lo, hi in WINDOWS)
        for a, b in collisions:
            print(f"\nmarks {a.label!r} and {b.label!r} are both "
                  f"{a.ts.isoformat()}, to the millisecond.", file=sys.stderr)
        # The consequences named are this grader's own and the figures that
        # move are named as firmly as those that do not: `first_change` takes
        # the earliest timestamp and the phantom window has no changes to take
        # it over, so §5's ms column comes out the same as the single-mark
        # control. And how the pair got there is left to the reader -- the
        # committed writers stamp at millisecond resolution and do not hold
        # marks apart, so naming a route here would name one of several and
        # read as a finding about which.
        print("§3 opens one window per mark so each action's movement can be "
              "told from the next one's, and two marks at one instant cannot "
              "be told apart: the capture does not say which action this was, "
              "so nothing was graded. The damage refusing avoids is this "
              "grader's own. The first of the pair would have been given a "
              "span of [t, t), taken no change row at all, and printed "
              f"`????` for all {watched} watched addresses, because a window "
              "that spans no sweep has no level to print. The window count "
              "would have read one per mark, none of which is a boundary any "
              "action took, and the closing line reads its 'Both blocks moved "
              "in N of the windows' over exactly that count. And "
              "`report_close_marks` would have been handed two marks 0.0s "
              "apart and offered that as a question about the operator's "
              "pacing rather than as a timestamp the grader could not use. "
              "What it does not change is §5's millisecond figure: the first "
              "change in a block is the earliest timestamp, so a window with "
              "no changes in it contributes no ordering to take the min over "
              "and the figure comes out the same as it does with the second "
              "mark deleted. Two marks a millisecond apart are two windows "
              "and are graded as two; nothing is fused here. Give the two "
              "actions two instants.", file=sys.stderr)
        return 1

    built = build_windows(runs)
    orders = []
    for source, windows in built:
        # The count is this capture's, and the capture is named on the same
        # line: with two files on the command line a bare "=== 3 window(s) ==="
        # is a total over two runs, which is the figure this change exists to
        # stop being printed. Parenthetical, the way `report_window` names a
        # window's own capture. Appended rather than worked into the sentence
        # so the line still reads the same for the one-capture case every
        # other assertion in the suite is written against.
        print(f"\n=== {len(windows)} window(s), one per mark, none merged ==="
              f" ({source})")
        orders.append([report_window(w, i, len(windows))
                       for i, w in enumerate(windows, 1)])
    report_close_marks(built)
    report_columns()
    report_settle(built, orders)
    return 0


if __name__ == "__main__":
    sys.exit(main())
