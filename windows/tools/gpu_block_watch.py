#!/usr/bin/env python3
r"""Issue #184: watch both GPU blocks in one capture, and say which moved first.

`0x07C4`-`0x07D7` (the block the DSDT's ECMG field list names `DBEN`/`DBST`,
`DBD1`/`DBD2`, `GFID`, `CPUA`/`DBAP`/`DBSP`/`CGCT`, and which the ASL reads out
to `\_SB.NPCF` for the NVIDIA platform controller) and `0x0743`-`0x0746` (the
block the service's own `GpuFeatures` class writes: enable bits, cTGP target,
Dynamic Boost targets -- windows/vendor-ec-map.md:84-87) are swept here in a
single loop, in one CSV, on one clock. That is the whole point: docs/findings.md
§4o closes on a negative with a clobber hazard left in it, and the question it
could not answer from committed inputs is what moves *first* under a GPU-only
Control Center action. Two `ec_watch.py` instances would put the two halves in
two files with two start times, which is the cross-file correlation the
procedure at docs/hardware-tests/gpu-tgp-07c4-07d7-door.md is trying to avoid.

**This tool observes. It has no write path**, no `--i-mean-it` equivalent, and
no code path that calls `ecrw.Ec.write` at all. `0x07D0`/`0x07D1` are
`DO-NOT-WRITE-BLIND` in ec/annotations/registers.yaml and the established
writer for the `0x0743`-`0x0746` half is `ctgp_live_test.py` (issue #8), which
writes rather than observes. A byte appearing in this tool's output means its
value differed between two of its own sweeps; it does not say the vendor
service wrote it, the EC wrote it, or nothing did, and it is not evidence the
EC acts on it.

A row is also an *endpoint net*, not a trace: a byte that moves and comes back
between two sweeps reads as quiet here, so read a zero through issue #168
before believing it.

The `WATCH` table in this file is the citation list the procedure's §7 is
graded against, printed once at startup so a capture states on its face what it
watched. `--names-only` prints it and exits without opening \\.\ACPIDriver. Its
DSDT column is the ECMG field list's own bit allocation, which is not always the
vendor's bit semantics elsewhere -- `0x0743` is the one that differs, the field
list declaring two named bits and registers.yaml describing three. The
`registers.yaml` column is the current `status:` verbatim, and "no row in
ec/annotations/registers.yaml" is a statement about that file, never about the
address.

The CSV schema is `ts,addr,old,new` with a mark as `ts,MARK,,label` -- the
schema `ec_watch.py` and ec/tools/grade_0751_isolation.py already read, kept
byte-identical so issue #168's grading needs no parser for this file.

The `--interval` default is ec_watch.py's 0.25 s and is a starting point, not a
safe one: `ecrw.Ec.read` is one ECRR DeviceIoControl per byte with nothing
between calls, this is 24 of them per sweep, and issue #94 is the open work on
that pacing. If the fans audibly change, stop and raise it.

Usage:
  gpu_block_watch.py --csv out.csv --mark    # both blocks, until Ctrl-C
  gpu_block_watch.py --seconds 120 --csv out.csv
  gpu_block_watch.py --names-only            # the watch table, no EC opened
"""
import argparse
import sys
import time

from ecrw import Ec, EcError
from ec_watch import CsvSink, Marker, now

# The 12 addresses here have no row in registers.yaml. That is a claim about
# the file, not about the address: docs/findings.md §4c retracted a "does not
# exist" reading of a zero-reference scan, and a table that says "no row"
# twelve times is the sentence most likely to be misread back into one.
NO_ROW = "no row in ec/annotations/registers.yaml"

# (addr, DSDT field list name and bit, registers.yaml status, citation)
WATCH = [
    (0x0743, "GNEN b0, ECDC b1", "confirmed-working",
     "dsdt.dsl:52204, registers.yaml CTGP_DB_CTRL"),
    (0x0744, "CTVA", "confirmed-working",
     "dsdt.dsl:52207, registers.yaml CTGP_DB_CTRL"),
    (0x0745, "DBCT", "confirmed-working",
     "dsdt.dsl:52207, registers.yaml CTGP_DB_CTRL"),
    (0x0746, "MXDB", "confirmed-working",
     "dsdt.dsl:52207, registers.yaml CTGP_DB_CTRL"),
    (0x07C4, "DBEN b3, DBST b5", "present-untested",
     "dsdt.dsl:52238, registers.yaml GPU_DYNAMIC_BOOST_STATUS"),
    (0x07C5, "WHMS b5", NO_ROW, "dsdt.dsl:52243"),
    (0x07C6, "WMS0 b0-1", "present-untested",
     "dsdt.dsl:52246, registers.yaml AP_OEM_6"),
    (0x07C7, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07C8, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07C9, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07CA, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07CB, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07CC, "(no DSDT field)", "present-untested",
     "dsdt.dsl:52194, registers.yaml USB_C_POWER_PRIORITY"),
    (0x07CD, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07CE, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07CF, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07D0, "DBD1", "unknown-not-absent-DO-NOT-WRITE-BLIND",
     "dsdt.dsl:52248, registers.yaml DBD1"),
    (0x07D1, "DBD2", "unknown-not-absent-DO-NOT-WRITE-BLIND",
     "dsdt.dsl:52248, registers.yaml DBD2"),
    (0x07D2, "(no DSDT field)", NO_ROW, "dsdt.dsl:52194"),
    (0x07D3, "GFID b4-6", "present-untested",
     "dsdt.dsl:52251, registers.yaml GFID"),
    (0x07D4, "CPUA", "present-untested",
     "dsdt.dsl:52254, registers.yaml CPUA"),
    (0x07D5, "DBAP", "present-untested",
     "dsdt.dsl:52254, registers.yaml DBAP"),
    (0x07D6, "DBSP", NO_ROW, "dsdt.dsl:52254"),
    (0x07D7, "CGCT", NO_ROW, "dsdt.dsl:52254"),
]

# The two windows, in the order the procedure's result table reads them. A
# change line is tagged with the one it fell in, because "which of the two
# moved first" is the question and an untagged list of addresses leaves the
# reader to sort them by hand.
WINDOWS = (("0x07C4-0x07D7", 0x07C4, 0x07D7),
           ("0x0743-0x0746", 0x0743, 0x0746))


def window_of(addr):
    for label, start, end in WINDOWS:
        if start <= addr <= end:
            return label
    raise KeyError(f"0x{addr:04X} is not in a watched window")


def print_watch_table():
    """The citation list, once, before anything is opened.

    It is printed rather than left to a flag alone because a capture is
    evidence, and evidence that does not record what was watched is a capture
    of nothing in particular.
    """
    print(f"watch set -- {len(WATCH)} addresses in "
          f"{len(WINDOWS)} windows, one sweep, one clock")
    ad = max(len(n) for _, n, _, _ in WATCH)
    st = max(len(s) for _, _, s, _ in WATCH)
    for addr, name, status, cite in WATCH:
        print(f"  0x{addr:04X}  {name:<{ad}}  {status:<{st}}  {cite}")
    print("  a 'no row' cell is a statement about registers.yaml, not about "
          "the address.\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after this long (default: until Ctrl-C)")
    ap.add_argument("--interval", type=float, default=0.25,
                    help="seconds between sweeps (default 0.25; a starting "
                         "point, not a validated-safe one -- #94)")
    ap.add_argument("--csv", help="also write every change to this CSV")
    ap.add_argument("--mark", action="store_true",
                    help="read stdin; each line stamps a labelled mark, into "
                         "the CSV too if --csv is given")
    ap.add_argument("--names-only", action="store_true",
                    help="print the watch table and exit; no EC is opened")
    args = ap.parse_args(argv)

    print_watch_table()
    if args.names_only:
        return 0

    addrs = [a for a, *_ in WATCH]
    sink = CsvSink(args.csv) if args.csv else None

    marker = Marker(sink)
    if args.mark:
        marker.start()

    changes = {}           # addr -> number of times it changed
    first_last = {}        # addr -> (first value seen, last value seen)
    first_change = {}      # addr -> (its printed ts, time.time() at it)
    t0 = time.time()
    sweeps = 0

    try:
        with Ec() as ec:
            prev = {a: ec.read(a) for a in addrs}
            for a, v in prev.items():
                first_last[a] = (v, v)
            print(f"{now()}  baseline: {len(addrs)} addresses across "
                  f"{len(WINDOWS)} windows, sweeping every {args.interval}s")
            print("no interval here is validated (#94): one ECRR per byte "
                  "with nothing between them. If the fans audibly change, "
                  "stop and raise it.")
            if args.mark:
                print("type a label + Enter to stamp a mark; Ctrl-C to stop")
            else:
                print("Ctrl-C to stop")

            while True:
                time.sleep(args.interval)
                sweeps += 1
                for a in addrs:
                    v = ec.read(a)
                    old = prev[a]
                    if v != old:
                        prev[a] = v
                        changes[a] = changes.get(a, 0) + 1
                        first_last[a] = (first_last[a][0], v)
                        ts, t = now(), time.time()
                        first_change.setdefault(a, (ts, t))
                        print(f"{ts}  0x{a:04X}: 0x{old:02X} -> 0x{v:02X} "
                              f"  [{window_of(a)}]", flush=True)
                        if sink:
                            sink.row([ts, f"0x{a:04X}",
                                      f"0x{old:02X}", f"0x{v:02X}"])
                if args.seconds and time.time() - t0 >= args.seconds:
                    break
    except KeyboardInterrupt:
        print()
    except EcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        if sink:
            sink.close()

    elapsed = time.time() - t0
    print(f"\n=== {sweeps} sweeps over {elapsed:.0f}s, "
          f"{len(changes)} addresses changed ===")
    if marker.marks:
        print("\nmarks:")
        for ts, label in marker.marks:
            print(f"  {ts}  {label}")

    if not changes:
        print("\nnothing moved.")
        return 0

    earliest = {}
    for label, start, end in WINDOWS:
        in_window = sorted(a for a in changes if start <= a <= end)
        print(f"\nwindow {label} -- {len(in_window)} of "
              f"{sum(1 for a in addrs if start <= a <= end)} "
              f"addresses changed:")
        for a in in_window:
            f, l = first_last[a]
            print(f"  0x{a:04X}  0x{f:02X} -> 0x{l:02X}   "
                  f"({changes[a]}x, first {first_change[a][0]})")
        if in_window:
            first = min(in_window, key=lambda a: first_change[a][1])
            earliest[label] = (first_change[first][0], first_change[first][1])

    # Which window moved first, as a number. What the number means -- and
    # whether it settles anything -- is a human's reading, not this tool's: a
    # zero is "not moved by this method under this action", and #168 owns the
    # grading of a capture. Printed so the reading has both halves in one
    # place rather than two files.
    if len(earliest) == len(WINDOWS):
        first, second = sorted(earliest, key=lambda k: earliest[k][1])
        print(f"\nfirst change in {first} ({earliest[first][0]}) led "
              f"{second} by "
              f"{abs(earliest[first][1] - earliest[second][1]) * 1000:.0f} ms")
        print("a timing report, not a verdict: a byte that wanders back "
              "between two sweeps reads as quiet, and a mark is the only "
              "record of what the operator did when.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
