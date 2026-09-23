#!/usr/bin/env python3
"""Apply §4 of docs/hardware-tests/manual-fan-ctrl-0751-isolation.md to a
capture, mechanically, so the sweep half of the procedure is read the same way
twice.

Input is what the procedure already produces: the `ec_watch.py --mark --csv`
captures for the `0x0700-0x07FF` sweep, the `0x0F00-0x0F5F` fan table and the
`0x0400-0x045F` temperature range, and, optionally, the `before-*`/`after-*`
`ecrw.py dump` files from its steps 0 and 6. Each mark in a CSV opens a window
that runs to the next mark, and for every window this reports whether the
bytes §4 names moved inside it:

  * `0x0783-0x0785` -- PL1/PL2/PL4 (§4.1)
  * `0x0F00-0x0F5F` -- the fan table (§4.2)
  * `0x07C6`        -- the byte the vendor brackets its fan-table write with (§4.3)

and, reported but not graded, the candidate fan-PWM bytes `0x075B`/`0x075C`
and `CPU_TEMP` `0x043E` / `GPU_TEMP` `0x044F` (§4.4/§4.5), plus whether
`0x0751` still holds the written value in the after-dump (§4.6).

Every context byte gets a `window delta` line in every window, whether or not
it moved: first value, last value, the endpoint net, the total movement (the
sum of the absolute steps it took inside the window), the max excursion (the
furthest it got from the value it opened the window at), and how many times it
moved. That is arithmetic on rows already in the capture, not a new judgement:
§4.4's comparison is how far the PWM bytes moved between one mark and the next,
and reading that off the change rows means doing the subtraction by eye across
two terminal windows -- or, for a byte that went somewhere and came back, the
counting and adding by eye that the figures do instead.

The three movement figures are all on the line because they are not
interchangeable. Net is an endpoint statistic, so it is the right summary of a
clean monotonic step and blind to movement that came back; §4.4 keys the
control-vs-write comparison on total, because a fan duty under a fixed load
wanders in both arms and the wander cannot separate them, while how far the
byte actually travelled can. Max excursion is the read for a write arm whose
response is a ramp to a new duty followed by wander.

A byte that held still is a line of zeros, not a missing line: absence would
read as missing data rather than as the strongest negative result the
procedure can produce.

**This is not the §7 call and cannot be.** §7 moves `MANUAL_FAN_CTRL` off
`present-untested` on fan PWM or package power moving under a fixed load.
Those bytes are captured and printed here, but printing them is not grading
them: the PWM address is unconfirmed (§4.4) and a fan's duty moves with the
die whether or not anything wrote `0x0751` -- separating those is what the
procedure's no-op control arm is for, not this script. Package power is read
by hand from HWiNFO (§4.5) and is in no capture. What this script says is
"of the bytes the sweep covers, these moved and these did not"; the call still
comes from a human holding the rest of the notes.

One action is marked in every watcher, so the same write appears as a MARK row
per capture; marks within `MARK_MERGE_SECONDS` are one window, not several.

Nothing here touches hardware; it reads files only.

Usage:
    python3 ec/tools/grade_0751_isolation.py capture-0700-07ff.csv \
        [capture-0f00-0f5f.csv] [capture-0400-045f.csv] \
        [--dump before-0700.txt] [--dump after-0700.txt]
    python3 ec/tools/grade_0751_isolation.py capture.csv --wrote 0xA0
"""
import argparse
import csv
import datetime
import sys

MANUAL_FAN_CTRL = 0x0751

# How close two marks have to be to count as one action. The procedure holds
# ~30 s between the control arm and the write and ~60 s before the restore, so
# this only has to be wide enough to cover pressing Enter in each of three
# consoles; a window that opened twice for one action would report "nothing
# moved" for half of it.
MARK_MERGE_SECONDS = 5

# The bytes §4 asks about, in its order. Everything else in the sweep is
# reported as context only: §4.4 says to read the whole 0x0700-0x07FF range
# rather than the two addresses issue #99 names, because neither is confirmed.
WATCHED = (
    ("PL1/PL2/PL4 (§4.1)", range(0x0783, 0x0786)),
    ("fan table (§4.2)", range(0x0F00, 0x0F60)),
    ("fan-table bracket byte 0x07C6 (§4.3)", range(0x07C6, 0x07C7)),
)

# The bytes §4.4/§4.5 name but this script does not grade. They get their own
# section because they are what §7's call is made on, and a reader should not
# have to find them in the generic "other addresses" list to notice them --
# and they get a line in every window, holding still or not, so that the no-op
# control arm and the write under test can be compared by eye: change row by
# change row, and then as the total movement the rows add up to, which is the
# figure §4.4 keys on. The PWM pair is where issue #99 says to look
# and is in no entry of registers.yaml; the two temperatures are
# confirmed-working, and are here as the record of whether the load was flat.
CONTEXT = (
    ("candidate fan PWM 0x075B/0x075C -- unconfirmed (§4.4)",
     range(0x075B, 0x075D)),
    ("CPU_TEMP 0x043E / GPU_TEMP 0x044F -- confirmed (§4.5)",
     (0x043E, 0x044F)),
)


class Change:
    def __init__(self, ts, addr, old, new, source):
        self.ts = ts
        self.addr = addr
        self.old = old
        self.new = new
        self.source = source


class Window:
    """One mark and everything that changed before the next mark."""

    def __init__(self, ts, label, source):
        self.ts = ts
        self.label = label
        self.source = source
        self.changes = []
        self.levels = {}


def parse_ts(s):
    return datetime.datetime.fromisoformat(s)


def read_capture(path):
    """(marks, changes) from one ec_watch.py CSV.

    Blank lines and `#` lines are skipped so an operator can annotate a
    capture by hand without breaking this.
    """
    marks, changes = [], []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "ts":
                continue
            if len(row) < 4:
                raise ValueError(f"{path}: short row {row!r}")
            ts, addr, old, new = row[0], row[1], row[2], row[3]
            if addr == "MARK":
                marks.append(Window(parse_ts(ts), new, path))
            else:
                changes.append(Change(parse_ts(ts), int(addr, 16),
                                      int(old, 16), int(new, 16), path))
    return marks, changes


def read_dump(path):
    """addr -> byte, from `ecrw.py dump` output (`0700: 12 34 ...`).

    `#` lines are skipped, as `read_capture` skips them. The two are written
    by the same operator out of the same run, and §6 tells them to annotate
    what they hand in; a comment carrying a colon is otherwise read as a row
    of bytes and raises out of `int()`.
    """
    values = {}
    with open(path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            base, _, rest = line.partition(":")
            if not rest.strip():
                continue
            addr = int(base.strip(), 16)
            for i, b in enumerate(rest.split()):
                values[addr + i] = int(b, 16)
    return values


def coalesce_marks(marks):
    """One window per action, however many consoles recorded it.

    The procedure runs one `--mark --csv` watcher per console, so a single
    action lands as several MARK rows seconds apart. Left alone, the changes
    that follow would be assigned to whichever of them happened to be last and
    the other two would report "nothing moved" for a write that did move
    things. A group starts at its *earliest* mark -- the window has to open
    before the first press, or the reaction is attributed to the wrong action
    -- and carries every label and source in it.
    """
    groups = []
    for m in sorted(marks, key=lambda w: w.ts):
        close = groups and (m.ts - groups[-1][-1].ts).total_seconds() \
            <= MARK_MERGE_SECONDS
        if close:
            groups[-1].append(m)
        else:
            groups.append([m])
    return [Window(g[0].ts,
                   " / ".join(dict.fromkeys(m.label for m in g)),
                   ", ".join(dict.fromkeys(m.source for m in g)))
            for g in groups]


def build_windows(marks, changes):
    """Assign every change to the last mark at or before it, and record the
    level each byte held where its window opened.

    Changes before the first mark belong to no window: the procedure has the
    operator let the sweep settle for ~10 s before marking, so they are the
    settling noise, not a reaction to anything. They still set the level the
    mark opened on, though, and that is worth more than their being dropped:
    without them a byte that moved while the sweep settled and then held still
    would print as level-unknown, when the captures in hand do say what it
    settled to. One time-ordered pass does both.
    """
    windows = coalesce_marks(marks)
    ordered = sorted(changes, key=lambda c: c.ts)
    last, i = {}, 0
    while i < len(ordered) and ordered[i].ts < windows[0].ts:
        last[ordered[i].addr] = ordered[i].new
        i += 1
    for n, w in enumerate(windows):
        w.levels = dict(last)
        end = windows[n + 1].ts if n + 1 < len(windows) else None
        while i < len(ordered) and (end is None or ordered[i].ts < end):
            w.changes.append(ordered[i])
            last[ordered[i].addr] = ordered[i].new
            i += 1
    return windows


def window_delta(w, addr):
    """One context byte's movement inside one window, as a printed line.

    `net` is the endpoint difference, `total` the sum of the absolute steps the
    byte took inside the window, `max` the furthest it got from the value it
    opened the window at. They are all here because §4.4's comparison is not
    answered by any one of them on its own: a byte that steps and settles says
    the same thing in all three, a byte that steps and wanders back does not.

    With no in-window change the byte did not move, so all three figures are
    zero and that is what the line says -- the line existing at all is the
    point, since no line reads as missing data rather than as a held byte. The
    level comes from `w.levels`: a change-row capture records transitions, not
    values, so a byte that has never appeared is known not to have moved while
    its level is not in evidence, and the line says that rather than filling
    something in.
    """
    seq = [c for c in w.changes if c.addr == addr]
    first = seq[0].old if seq else w.levels.get(addr)
    if first is None:
        level = "???? -> ????"
    else:
        level = f"0x{first:02X} -> 0x{seq[-1].new if seq else first:02X}"
    net = seq[-1].new - first if seq else 0
    total = sum(abs(c.new - c.old) for c in seq)
    peak = max((abs(c.new - first) for c in seq), default=0)
    if seq:
        count = f"({len(seq)} change{'' if len(seq) == 1 else 's'})"
    elif first is None:
        count = "(0 changes, level not in these captures)"
    else:
        count = "(0 changes)"
    return (f"window delta  0x{addr:04X}  {level}  net {net:+d}  "
            f"total {total}  max {peak}  {count}")


def report_window(w, n, total):
    end = "the next mark" if n < total else "the end of the capture"
    print(f"\n--- mark {n}/{total}: {w.ts.isoformat()}  {w.label!r} "
          f"({w.source})")
    print(f"    window runs to {end}")

    moved = False
    for name, addrs in WATCHED:
        hits = [c for c in w.changes if c.addr in addrs]
        if not hits:
            continue
        moved = True
        print(f"    {name}:")
        for c in hits:
            dt = (c.ts - w.ts).total_seconds()
            print(f"      0x{c.addr:04X}  0x{c.old:02X} -> 0x{c.new:02X}"
                  f"   (+{dt:.1f}s)")
    if not moved:
        print("    no watched byte moved in this window")

    print("    candidate PWM / temperature bytes (§4.4/§4.5) -- context, "
          "not graded here:")
    print("    net is the raw byte difference across the whole window, not a "
          "duty")
    print("    percentage; total is the sum of the absolute steps the byte "
          "took inside it,")
    print("    and max is the furthest it got from the value it opened the "
          "window at. §4.4")
    print("    keys the control-vs-write comparison on total. Every candidate "
          "byte gets a")
    print("    line in every window, so a byte that held still is a zero here "
          "and not a")
    print("    missing line.")
    for name, addrs in CONTEXT:
        print(f"      {name}:")
        for a in addrs:
            print(f"        {window_delta(w, a)}")
        for c in w.changes:
            if c.addr not in addrs:
                continue
            dt = (c.ts - w.ts).total_seconds()
            print(f"        0x{c.addr:04X}  0x{c.old:02X} -> 0x{c.new:02X}"
                  f"   (+{dt:.1f}s)")

    others = sorted({c.addr for c in w.changes
                     if not any(c.addr in a for _, a in WATCHED)
                     and not any(c.addr in a for _, a in CONTEXT)})
    if others:
        print(f"    other addresses that moved ({len(others)}), not graded "
              "here -- read them against §4.4 and §4.5 by hand:")
        print("      " + " ".join(f"0x{a:04X}" for a in others))
    return moved


def report_dumps(dumps, wrote):
    print("\n=== 0x0751 across the dumps (§4.6) ===")
    if not dumps:
        print("  no dump given (--dump); §4.6 not checked")
        return
    for path, values in dumps:
        v = values.get(MANUAL_FAN_CTRL)
        if v is None:
            print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} not covered by this dump")
        else:
            print(f"  {path}: 0x{MANUAL_FAN_CTRL:04X} = 0x{v:02X}")
    if wrote is None:
        return
    last = dumps[-1][1].get(MANUAL_FAN_CTRL)
    if last is None:
        return
    if last == wrote:
        print(f"  the last dump still holds the written 0x{wrote:02X}. Per "
              "CLAUDE.md that is a readback, not evidence the EC acted on it.")
    else:
        print(f"  the last dump holds 0x{last:02X}, not the written "
              f"0x{wrote:02X} -- something put it back; §3a's service-stopped "
              "run is what separates the vendor service from the EC.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="ec_watch.py --mark --csv capture(s)")
    ap.add_argument("--dump", action="append", default=[], metavar="FILE",
                    help="ecrw.py dump output; repeat for before- and after-")
    ap.add_argument("--wrote", help="the value written to 0x0751 (e.g. 0xA0)")
    args = ap.parse_args(argv)

    wrote = int(args.wrote, 0) if args.wrote else None

    marks, changes = [], []
    for path in args.csv:
        m, c = read_capture(path)
        marks += m
        changes += c
        print(f"{path}: {len(m)} mark(s), {len(c)} change row(s)")

    if not marks:
        print("\nno MARK rows in these captures. ec_watch.py writes them only "
              "when --mark and --csv are both given; without them a byte that "
              "moved 400 ms after the write and one that moved 40 s after it "
              "cannot be told apart, and §4 cannot be applied.", file=sys.stderr)
        return 1

    windows = build_windows(marks, changes)
    print(f"\n=== {len(windows)} window(s), one per mark ===")
    any_moved = False
    for i, w in enumerate(windows, 1):
        any_moved |= report_window(w, i, len(windows))

    dumps = [(p, read_dump(p)) for p in args.dump]
    report_dumps(dumps, wrote)

    print("\n=== what this does and does not settle ===")
    if any_moved:
        print("  At least one of the §4.1-§4.3 bytes moved after a mark. That "
              "contradicts the static prediction in "
              "ec/annotations/manual-fan-ctrl-0751.md §5 if it is the PLs, or "
              "§4.2 if it is the fan table -- capture it in full, it is the "
              "more interesting outcome.")
    else:
        print("  None of the §4.1-§4.3 bytes moved in any window: consistent "
              "with the static prediction, for this capture's window only "
              "(§5: a byte that does not move inside the window may still "
              "move at the next suspend, AC transition or EC reset).")
    print("  Any candidate PWM and temperature bytes printed above are "
          "context, not a result: 0x075B/0x075C are where issue #99 says "
          "to look, not a "
          "confirmed fan-PWM register, and a fan's duty moves with the die "
          "whether or not anything wrote 0x0751 -- which is what §3's no-op "
          "control arm measures, and what this script cannot. CPU package "
          "power (§4.5) is in no EC sweep and is still read by hand.")
    print("  §7 keys `confirmed-working` on fan PWM or package power moving "
          "under a fixed load, so this output is an input to that call and "
          "not the call itself. `confirmed-inert` as a standalone control "
          "additionally needs all three values, with and without the vendor "
          "service (§3a).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
