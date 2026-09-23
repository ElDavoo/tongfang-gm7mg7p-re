#!/usr/bin/env python3
"""Apply §4 of docs/hardware-tests/manual-fan-ctrl-0751-isolation.md to a
capture, mechanically, so the sweep half of the procedure is read the same way
twice.

Input is what the procedure already produces: one or two `ec_watch.py --mark
--csv` captures (the `0x0700-0x07FF` sweep and the `0x0F00-0x0F5F` one) and,
optionally, the `before-*`/`after-*` `ecrw.py dump` files from its steps 0 and
5. Each mark in a CSV opens a window that runs to the next mark, and for every
window this reports whether the bytes §4 names moved inside it:

  * `0x0783-0x0785` -- PL1/PL2/PL4 (§4.1)
  * `0x0F00-0x0F5F` -- the fan table (§4.2)
  * `0x07C6`        -- the byte the vendor brackets its fan-table write with (§4.3)

and whether `0x0751` still holds the written value in the after-dump (§4.6).

**This is not the §7 call and cannot be.** §7 moves `MANUAL_FAN_CTRL` off
`present-untested` on fan PWM or package power moving under a fixed load, and
neither of those is in an EC sweep -- the PWM address is unconfirmed (§4.4)
and package power is read by hand from HWiNFO (§4.5). What this script says is
"of the bytes the sweep covers, these moved and these did not"; the call still
comes from a human holding the rest of the notes.

Nothing here touches hardware; it reads files only.

Usage:
    python3 ec/tools/grade_0751_isolation.py capture-0700-07ff.csv \
        [capture-0f00-0f5f.csv] [--dump before-0700.txt] [--dump after-0700.txt]
    python3 ec/tools/grade_0751_isolation.py capture.csv --wrote 0xA0
"""
import argparse
import csv
import datetime
import sys

MANUAL_FAN_CTRL = 0x0751

# The bytes §4 asks about, in its order. Everything else in the sweep is
# reported as context only: §4.4 says to read the whole 0x0700-0x07FF range
# rather than the two addresses issue #99 names, because neither is confirmed.
WATCHED = (
    ("PL1/PL2/PL4 (§4.1)", range(0x0783, 0x0786)),
    ("fan table (§4.2)", range(0x0F00, 0x0F60)),
    ("fan-table bracket byte 0x07C6 (§4.3)", range(0x07C6, 0x07C7)),
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
    """addr -> byte, from `ecrw.py dump` output (`0700: 12 34 ...`)."""
    values = {}
    with open(path) as f:
        for line in f:
            base, _, rest = line.partition(":")
            if not rest.strip():
                continue
            addr = int(base.strip(), 16)
            for i, b in enumerate(rest.split()):
                values[addr + i] = int(b, 16)
    return values


def build_windows(marks, changes):
    """Assign every change to the last mark at or before it.

    Changes before the first mark belong to no window: the procedure has the
    operator let the sweep settle for ~10 s before marking, so they are the
    settling noise, not a reaction to anything.
    """
    windows = sorted(marks, key=lambda w: w.ts)
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

    others = sorted({c.addr for c in w.changes
                     if not any(c.addr in a for _, a in WATCHED)})
    if others:
        print(f"    other addresses that moved ({len(others)}), not graded "
              "here -- read them against §4.4 by hand:")
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
    print("  Fan PWM (§4.4) and CPU package power (§4.5) are NOT in this data. "
          "§7 keys `confirmed-working` on one of those moving under a fixed "
          "load, so this output is an input to that call and not the call "
          "itself. `confirmed-inert` as a standalone control additionally "
          "needs all three values, with and without the vendor service (§3a).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
