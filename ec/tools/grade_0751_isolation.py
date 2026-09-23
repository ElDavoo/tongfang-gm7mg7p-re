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

Each context byte that moved in a window is also summarised as a
`window delta` -- first value, last value, net, and how many times it moved
inside the window. That is arithmetic on rows already in the capture, not a
new judgement: §4.4's deciding comparison is how far the PWM bytes drifted
between one mark and the next, and reading that off the change rows means
doing the subtraction by eye across two terminal windows.

`--dump-pair` reads the same §4.1-§4.3 bytes a second, wider way, from a
before/after dump pair per range -- the two range dumps §3's steps 0 and 6
take, which bracket the whole block where each CSV window brackets one arm
of it. That bracket is complementary to the windowed one, not a stronger
form of it: a byte that moved at any point in the block and is back where it
started by the after-dump reads unchanged here, and a byte that moves
entirely between two of `ec_watch.py`'s sweeps is in no change row at all.
Each read has a gap the other does not close. An address one dump covers and
the other does not is a coverage gap, never a change.

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
    python3 ec/tools/grade_0751_isolation.py capture.csv \
        --dump-pair before-0700.txt after-0700.txt \
        --dump-pair before-0f00.txt after-0f00.txt
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
# but they are printed per window precisely so the no-op control arm and the
# write under test can be compared by eye, change row by change row and then
# as the net the rows add up to. The PWM pair is where issue #99 says to look
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
    """Assign every change to the last mark at or before it.

    Changes before the first mark belong to no window: the procedure has the
    operator let the sweep settle for ~10 s before marking, so they are the
    settling noise, not a reaction to anything.
    """
    windows = coalesce_marks(marks)
    for c in sorted(changes, key=lambda c: c.ts):
        prior = [w for w in windows if w.ts <= c.ts]
        if prior:
            prior[-1].changes.append(c)
    return windows


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

    groups = [(name, [c for c in w.changes if c.addr in addrs])
              for name, addrs in CONTEXT]
    groups = [(name, hits) for name, hits in groups if hits]
    if groups:
        print("    candidate PWM / temperature bytes (§4.4/§4.5) -- context, "
              "not graded here:")
        print("    net is the raw byte difference across the whole window, "
              "not a duty percentage:")
        for name, hits in groups:
            print(f"      {name}:")
            for a in sorted({c.addr for c in hits}):
                seq = [c for c in hits if c.addr == a]
                print(f"        window delta  0x{a:04X}  "
                      f"0x{seq[0].old:02X} -> 0x{seq[-1].new:02X}  "
                      f"net {seq[-1].new - seq[0].old:+d}  "
                      f"({len(seq)} change{'' if len(seq) == 1 else 's'})")
            for c in hits:
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


def report_dump_pairs(pairs):
    """The same watched bytes, read across a whole block instead of a window.

    A pair is §3's own bracket for one range -- step 0 and step 6, ~100 s
    apart -- and a CSV window is one arm of that block. So this is a wider
    bracket on the same question, not a better answer: a byte that moved
    anywhere in the block and is back at its starting value by the
    after-dump reads unchanged here, and a byte that moves entirely between
    two of `ec_watch.py`'s sweeps is in no change row at all. Each read has
    a gap the other does not close, and neither emits a status.

    Only the intersection of the two address sets is compared. `read_dump`
    returns what it saw, so an address past the end of the shorter dump is
    simply missing from it, and a plain `!=` over the union would call every
    one of them a difference. A gap like that is coverage, printed as such.

    The bucketing is `report_window`'s, unchanged: the §4.1-§4.3 bytes, then
    the §4.4/§4.5 context bytes printed and not graded, then everything else
    named for the human. No third category -- a byte's membership in one
    bucket is the same question here as it is per window.
    """
    print("\n=== whole-block dump pairs (§4.1-§4.3) ===")
    if not pairs:
        print("  no dump pair given (--dump-pair); the whole-block read is not "
              "checked")
        return
    for before_path, after_path, before, after in pairs:
        common = sorted(set(before) & set(after))
        moved = [a for a in common if before[a] != after[a]]
        print(f"\n  {before_path} -> {after_path}, {len(common)} address(es) "
              "compared")

        only_before = sorted(set(before) - set(after))
        only_after = sorted(set(after) - set(before))
        if only_before or only_after:
            print("    coverage gap, not a change: whatever moved in the part "
                  "one of these does not cover is outside this read.")
            print("      before dump only: "
                  + (" ".join(f"0x{a:04X}" for a in only_before) or "none"))
            print("      after dump only:  "
                  + (" ".join(f"0x{a:04X}" for a in only_after) or "none"))

        for name, addrs in WATCHED:
            hits = [a for a in moved if a in addrs]
            if not any(a in addrs for a in common):
                # The fan table is not in a 0x0700 dump and the PLs are not
                # in a 0x0F00 one, so §6's pairs each cover some of §4.1-§4.3
                # and not all. Silence there would read as "nothing moved".
                print(f"    {name}: not covered by this pair")
            elif not hits:
                print(f"    {name}: unchanged across the block")
            else:
                print(f"    {name}:")
                for a in hits:
                    print(f"      0x{a:04X}  0x{before[a]:02X} -> "
                          f"0x{after[a]:02X}")

        groups = [(name, [a for a in moved if a in addrs])
                  for name, addrs in CONTEXT]
        groups = [(name, hits) for name, hits in groups if hits]
        if groups:
            print("    candidate PWM / temperature bytes (§4.4/§4.5) -- "
                  "context, not graded here:")
            for name, hits in groups:
                print(f"      {name}:")
                for a in hits:
                    print(f"        0x{a:04X}  0x{before[a]:02X} -> "
                          f"0x{after[a]:02X}")

        others = [a for a in moved
                  if not any(a in addrs for _, addrs in WATCHED)
                  and not any(a in addrs for _, addrs in CONTEXT)]
        if others:
            print(f"    other addresses that differ ({len(others)}), not "
                  "graded here -- read them against §4.4 and §4.5 by hand:")
            print("      " + " ".join(f"0x{a:04X}" for a in others))

    print("\n  Every `unchanged` above says the byte did not differ between "
          "these two reads, which is not a claim that it did not move inside "
          "the block: §5, a byte that does not move inside a window may "
          "still move at the next suspend, AC transition or EC reset. This "
          "bracket is complementary to the windowed CSV read above, not a "
          "stronger one -- a byte that moved and was back where it started "
          "by the after-dump reads unchanged here whether or not the "
          "captures recorded the move, and a byte that moves entirely "
          "between two of ec_watch.py's sweeps is in no change row at all. "
          "Neither gap is closed by the other read.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="ec_watch.py --mark --csv capture(s)")
    ap.add_argument("--dump", action="append", default=[], metavar="FILE",
                    help="ecrw.py dump output; repeat for before- and after-")
    ap.add_argument("--dump-pair", action="append", nargs=2, default=[],
                    metavar=("BEFORE", "AFTER"),
                    help="one range's ecrw.py dump before/after pair, as §3's "
                         "steps 0 and 6 take it; repeat per range. Read for "
                         "the whole-block report and independent of --dump, "
                         "whose §4.6 readback still comes from the last one")
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

    # After the §4.6 readback, so the section order stays the one §6
    # documents: the per-window read, then 0x0751 across the dumps, then the
    # whole-block bracket on the same §4.1-§4.3 bytes.
    pairs = [(b, a, read_dump(b), read_dump(a))
             for b, a in args.dump_pair]
    report_dump_pairs(pairs)

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
    if pairs:
        print("  The whole-block dump pairs above were read as a second, "
              "wider bracket on the same §4.1-§4.3 bytes. That is two "
              "brackets, not two results: each has a gap the other does not "
              "close, and neither grades the PWM or temperature bytes the "
              "pairs happen to print.")
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
