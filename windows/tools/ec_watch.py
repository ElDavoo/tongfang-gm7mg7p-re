#!/usr/bin/env python3
r"""Watch EC RAM for changes while something else -- the vendor's Control Center,
usually -- is driving it, and report which addresses moved.

`ecrw.py` can sweep 2 KiB of EC space in about 150 ms, which is fast enough to
catch a settings write as it lands. That turns "which register does the vendor
service actually use for X" from a static-analysis question into an observation:
start this, change X in the vendor UI, stop, and read off the addresses that
changed at that moment.

The output separates two kinds of address, because they need reading differently:

  * *busy* -- changed on many sweeps. Sensors: temperature, fan tacho, battery
    current. A setting is essentially never here.
  * *quiet* -- changed only once or twice in the whole run. This is what a
    settings write looks like, and it is the column to read first.

Neither label is a claim about meaning. An address appearing here means only
that its byte changed while the run was going on; whether the vendor service
wrote it, the EC wrote it itself, or it moved for an unrelated reason is exactly
what a single run cannot distinguish -- run it again with and without the action
before believing any of it.

With both --mark and --csv, each mark is written into the CSV as its own row
(`ts,MARK,,label`) as well as printed, so the capture alone says when the
operator acted -- see ec/tools/grade_0751_isolation.py, which grades a capture
by what moved between one mark and the next.

Usage:
  ec_watch.py                                  # 0x0000-0x07FF until Ctrl-C
  ec_watch.py --start 0x0700 --len 0x100
  ec_watch.py --seconds 60 --csv out.csv
  ec_watch.py --mark                           # press Enter to timestamp an action
"""
import argparse
import csv
import datetime
import sys
import threading
import time

from ecrw import Ec, EcError


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


class CsvSink:
    """The CSV, plus the lock that makes it safe to write from two threads.

    The sweep loop runs on the main thread and marks arrive on the stdin
    thread, so without this a mark can land in the middle of a change row.
    """

    def __init__(self, path):
        self._fh = open(path, "a", newline="")
        self._writer = csv.writer(self._fh)
        self._lock = threading.Lock()
        if self._fh.tell() == 0:
            self.row(["ts", "addr", "old", "new"])

    def row(self, values):
        with self._lock:
            # A mark typed as the run ends arrives after close(); dropping it
            # beats a traceback out of the stdin thread at the last moment.
            if self._fh.closed:
                return
            self._writer.writerow(values)
            self._fh.flush()

    def close(self):
        with self._lock:
            self._fh.close()


class Marker:
    """Lets the operator stamp 'I clicked the thing now' into the log."""

    def __init__(self, sink=None):
        self.marks = []
        self._n = 0
        self._sink = sink

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while True:
            try:
                label = sys.stdin.readline()
            except Exception:
                return
            if not label:
                return
            self._n += 1
            label = label.strip() or f"mark {self._n}"
            ts = now()
            self.marks.append((ts, label))
            if self._sink:
                self._sink.row([ts, "MARK", "", label])
            print(f"--- {ts}  MARK: {label} ---", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="0x0000")
    ap.add_argument("--len", dest="length", default="0x0800")
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after this long (default: until Ctrl-C)")
    ap.add_argument("--interval", type=float, default=0.25,
                    help="seconds between sweeps (default 0.25)")
    ap.add_argument("--csv", help="also write every change to this CSV")
    ap.add_argument("--mark", action="store_true",
                    help="read stdin; each line stamps a labelled mark, into "
                         "the CSV too if --csv is given")
    args = ap.parse_args(argv)

    start = int(args.start, 0)
    length = int(args.length, 0)
    addrs = list(range(start, start + length))

    sink = CsvSink(args.csv) if args.csv else None

    marker = Marker(sink)
    if args.mark:
        marker.start()

    changes = {}           # addr -> number of times it changed
    first_last = {}        # addr -> (first value seen, last value seen)
    t0 = time.time()
    sweeps = 0

    try:
        with Ec() as ec:
            prev = {a: ec.read(a) for a in addrs}
            for a, v in prev.items():
                first_last[a] = (v, v)
            print(f"{now()}  baseline: 0x{start:04X}-0x{start + length - 1:04X} "
                  f"({length} bytes), sweeping every {args.interval}s")
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
                        ts = now()
                        print(f"{ts}  0x{a:04X}: 0x{old:02X} -> 0x{v:02X}",
                              flush=True)
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
        print("nothing moved.")
        return 0

    quiet = sorted(a for a, n in changes.items() if n <= 2)
    busy = sorted(a for a, n in changes.items() if n > 2)

    print(f"\nquiet -- changed once or twice; a settings write looks like this "
          f"({len(quiet)}):")
    for a in quiet:
        f, l = first_last[a]
        print(f"  0x{a:04X}  0x{f:02X} -> 0x{l:02X}   ({changes[a]}x)")

    print(f"\nbusy -- changed on many sweeps, most likely a sensor ({len(busy)}):")
    for a in busy:
        f, l = first_last[a]
        print(f"  0x{a:04X}  0x{f:02X} -> 0x{l:02X}   ({changes[a]}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
