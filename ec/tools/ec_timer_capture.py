#!/usr/bin/env python3
"""Read-only Linux capture of a list of EC RAM bytes, in ec_watch.py's CSV format.

`windows/tools/ec_watch.py` is the Windows watcher and needs the vendor's
`ecrw`. This is the Linux counterpart for the case where the question is a
*rate*: it samples an explicit address list through the same physical ECMG
window `ecmem.py` maps (0xFE410000, the `MMRW` path the vendor's `ECRW`
takes), at an interval far shorter than a 2 KiB sweep allows, and writes one
`ts,addr,old,new` row per change -- the format
`ec/tools/grade_0751_isolation.py` and `check_capture_claims.py` already read.

It never opens `/dev/mem` for writing. Two guards run before the first read:

  * **The fan page, 0x0460-0x046F, is refused** (issue #94,
    `docs/related-projects.md`): reading those bytes stalled the fans on a
    sibling board. That was through `ECRR`, not this window, but the carve-out
    is kept rather than re-argued here.
  * **Addresses outside the host window are refused** unless
    `--outside-window` is given. On this machine the window maps
    0x0000-0x07FF and 0x0C00-0x0FFF; every other page reads 0xFF whatever the
    EC holds (`evidence/ec-watch/2026-09-24-host-window-page-census.txt`). A
    byte read there would sit at 0xFF for the whole run and look exactly like
    a countdown that never moved, which is the misreading this refuses.

The CSV opens with `#` comment lines (date, kernel, AC state, interval, the
address list, and whatever `--note` adds) before the header row, because a
capture that does not say what it watched and under what conditions is not
one a later reader can grade. Every consumer in this repository skips `#`.

The first sample is a baseline and goes in a `# baseline` comment line, so a
byte that never moved is still on record with the value it held, while the
data rows stay one per change exactly as `ec_watch.py` writes them (a row
count for an address is its change count, which is what
`check_capture_claims.py` holds prose to).

Usage (root, CONFIG_DEVMEM):
  ec_timer_capture.py --addrs 0x06d6 --interval 0.002 --seconds 60 --csv out.csv
  ec_timer_capture.py --addrs 0x06c2-0x06db,0x0440 --interval 0.01 --seconds 120 \\
      --csv out.csv --note "idle, AC"
  ec_timer_capture.py ... --mark     # each line on stdin stamps ts,MARK,,label
  ec_timer_capture.py ... --auto-mark --mark-input /dev/input/event7
                                     # MARK rows stamped from the machine itself
  ec_timer_capture.py --census       # which 256-byte pages hold anything but 0xFF

`--auto-mark` is for a run where the operator's hands are on the machine and
not on a keyboard feeding stdin: it polls every Mains supply's `online`, every
ACPI lid's `state`, and the gap between CLOCK_BOOTTIME and CLOCK_MONOTONIC
(which grows only while the system is suspended), and writes a
`ts,MARK,,auto: ...` row when one changes. `--mark-input DEV` reads an evdev
node passively -- no EVIOCGRAB, so every other reader still gets every event
-- and marks each key press and MSC_SCAN code, which is how a hotkey that no
sysfs file reflects gets a timestamp. A mark is when Linux saw the action, not
when the EC did.

`--census` is the measurement HOST_WINDOW below is taken from: one read-only
pass over the 64 KiB mapping, skipping the fan page, printing how many bytes
of each page are not 0xFF. A page that is all 0xFF is *consistent with* the
window not mapping it; it is not a statement about what the EC holds there.
"""
import argparse
import csv
import datetime
import os
import glob
import platform
import struct
import sys
import threading
import time

import ecmem

FAN_PAGE = range(0x0460, 0x0470)
HOST_WINDOW = ((0x0000, 0x07FF), (0x0C00, 0x0FFF))


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def parse_addrs(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = (int(x, 0) for x in part.split("-", 1))
            out.extend(range(lo, hi + 1))
        else:
            out.append(int(part, 0))
    seen = set()
    return [a for a in out if not (a in seen or seen.add(a))]


def in_window(a):
    return any(lo <= a <= hi for lo, hi in HOST_WINDOW)


def check_addrs(addrs, outside_window=False):
    """Return an error string, or None. Runs before /dev/mem is opened."""
    fan = [a for a in addrs if a in FAN_PAGE]
    if fan:
        return ("refusing the fan page 0x0460-0x046F (issue #94): "
                + " ".join(f"{a:#06x}" for a in fan))
    bad = [a for a in addrs if not 0 <= a < ecmem.SIZE]
    if bad:
        return "outside the 64 KiB ECMG mapping: " + " ".join(f"{a:#x}" for a in bad)
    if not outside_window:
        out = [a for a in addrs if not in_window(a)]
        if out:
            return ("outside the host window (reads 0xFF whatever the EC holds; "
                    "--outside-window to read anyway): "
                    + " ".join(f"{a:#06x}" for a in out))
    return None


def power_state():
    parts = []
    base = "/sys/class/power_supply"
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return "unknown"
    for n in names:
        for key in ("online", "status", "capacity"):
            p = os.path.join(base, n, key)
            try:
                with open(p) as f:
                    parts.append(f"{n}.{key}={f.read().strip()}")
            except OSError:
                pass
    return " ".join(parts) or "unknown"


class Sink:
    def __init__(self, path):
        self._fh = open(path, "w", newline="")
        self._w = csv.writer(self._fh, lineterminator="\n")
        self._lock = threading.Lock()

    def comment(self, text):
        with self._lock:
            self._fh.write(f"# {text}\n")
            self._fh.flush()

    def row(self, values):
        with self._lock:
            if not self._fh.closed:
                self._w.writerow(values)
                self._fh.flush()

    def close(self):
        with self._lock:
            self._fh.close()


def mark_loop(sink):
    n = 0
    for line in sys.stdin:
        n += 1
        label = line.strip() or f"mark {n}"
        ts = now()
        sink.row([ts, "MARK", "", label])
        print(f"--- {ts}  MARK: {label} ---", flush=True)


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def machine_state():
    st = {}
    for d in sorted(glob.glob("/sys/class/power_supply/*")):
        if _read(os.path.join(d, "type")) == "Mains":
            st[f"{os.path.basename(d)}.online"] = _read(os.path.join(d, "online"))
    for f in sorted(glob.glob("/proc/acpi/button/lid/*/state")):
        v = _read(f)
        st[f"lid {f.split('/')[-2]}"] = v.split()[-1] if v else None
    return st


def suspend_gap():
    return (time.clock_gettime(time.CLOCK_BOOTTIME)
            - time.clock_gettime(time.CLOCK_MONOTONIC))


def auto_mark_loop(sink, period=0.05):
    prev, gap = machine_state(), suspend_gap()
    while True:
        time.sleep(period)
        cur, g = machine_state(), suspend_gap()
        if g - gap > 0.5:
            label = f"auto: resumed, ~{g - gap:.1f} s suspended"
            sink.row([now(), "MARK", "", label])
            print(f"--- MARK: {label} ---", flush=True)
        gap = g
        for k in cur:
            if cur[k] != prev.get(k):
                label = f"auto: {k} {prev.get(k)} -> {cur[k]}"
                sink.row([now(), "MARK", "", label])
                print(f"--- MARK: {label} ---", flush=True)
        prev = cur


EVENT = struct.Struct("llHHi")      # struct input_event, 64-bit time
EV_KEY, EV_MSC, MSC_SCAN = 1, 4, 4


def input_mark_loop(sink, dev):
    with open(dev, "rb", buffering=0) as f:
        while True:
            buf = f.read(EVENT.size)
            if len(buf) < EVENT.size:
                return
            _, _, typ, code, value = EVENT.unpack(buf)
            if typ == EV_KEY and value == 1:
                label = f"auto: {os.path.basename(dev)} key {code} pressed"
            elif typ == EV_MSC and code == MSC_SCAN:
                label = f"auto: {os.path.basename(dev)} scan {value & 0xFFFFFFFF:#x}"
            else:
                continue
            sink.row([now(), "MARK", "", label])
            print(f"--- MARK: {label} ---", flush=True)


def census():
    m = ecmem._map()          # read-only mapping
    print(f"# host-window page census, ec/tools/ec_timer_capture.py --census, "
          f"ECMG {ecmem.BASE:#x} via /dev/mem, read-only")
    print(f"# {now()}  host {platform.node()}  kernel {platform.release()}")
    print("# page base: bytes != 0xFF / bytes read. The 0x0400 page reads 240: "
          "0x0460-0x046F skipped (issue #94)")
    runs = []
    for page in range(ecmem.SIZE >> 8):
        b = page << 8
        if b == 0x0400:
            data = bytes(m[b:FAN_PAGE.start]) + bytes(m[FAN_PAGE.stop:b + 0x100])
        else:
            data = bytes(m[b:b + 0x100])
        n = sum(x != 0xFF for x in data)
        print(f"{b:#06x} {n:3d}/{len(data)}")
        k = "all 0xFF" if n == 0 else "holds data"
        if runs and runs[-1][0] == k:
            runs[-1][2] = b
        else:
            runs.append([k, b, b])
    print("# runs:")
    for k, lo, hi in runs:
        print(f"#   {lo:#06x}-{hi + 0xFF:#06x}  {k}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--census", action="store_true",
                    help="print the per-page non-0xFF census and exit")
    ap.add_argument("--addrs",
                    help="comma list of addresses and lo-hi ranges")
    ap.add_argument("--interval", type=float, default=0.01,
                    help="seconds between passes over the list (default 0.01)")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--csv")
    ap.add_argument("--note", action="append", default=[],
                    help="free-text conditions line for the header; repeatable")
    ap.add_argument("--mark", action="store_true")
    ap.add_argument("--auto-mark", action="store_true",
                    help="mark AC, lid and suspend/resume changes from sysfs")
    ap.add_argument("--mark-input", action="append", default=[],
                    help="evdev node whose key presses become marks; repeatable")
    ap.add_argument("--outside-window", action="store_true")
    args = ap.parse_args(argv)
    if args.census:
        return census()
    if not (args.addrs and args.seconds and args.csv):
        ap.error("--addrs, --seconds and --csv are required unless --census")

    addrs = parse_addrs(args.addrs)
    err = check_addrs(addrs, args.outside_window)
    if err:
        print(f"error: {err}", file=sys.stderr)
        return 2

    m = ecmem._map()          # read-only mapping
    sink = Sink(args.csv)
    sink.comment(f"ec/tools/ec_timer_capture.py, read-only, ECMG window "
                 f"{ecmem.BASE:#x} via /dev/mem")
    sink.comment(f"started {now()}  host {platform.node()}  kernel {platform.release()}")
    sink.comment(f"power: {power_state()}")
    sink.comment(f"interval {args.interval}s  seconds {args.seconds}  "
                 f"{len(addrs)} addresses: " + " ".join(f"{a:#06x}" for a in addrs))
    for n in args.note:
        sink.comment(f"note: {n}")
    ts = now()
    prev = {a: m[a] for a in addrs}
    sink.comment(f"baseline {ts}: "
                 + " ".join(f"0x{a:04X}=0x{prev[a]:02X}" for a in addrs))
    sink.row(["ts", "addr", "old", "new"])
    if args.mark:
        threading.Thread(target=mark_loop, args=(sink,), daemon=True).start()
    if args.auto_mark:
        sink.comment("auto-mark state at start: " + " ".join(
            f"{k}={v}" for k, v in machine_state().items()))
        threading.Thread(target=auto_mark_loop, args=(sink,), daemon=True).start()
    for dev in args.mark_input:
        threading.Thread(target=input_mark_loop, args=(sink, dev),
                         daemon=True).start()

    passes = 0
    changes = {a: 0 for a in addrs}
    t0 = time.monotonic()
    deadline = t0 + args.seconds
    nxt = t0
    try:
        while True:
            nxt += args.interval
            delay = nxt - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            passes += 1
            for a in addrs:
                v = m[a]
                if v != prev[a]:
                    sink.row([now(), f"0x{a:04X}", f"0x{prev[a]:02X}", f"0x{v:02X}"])
                    prev[a] = v
                    changes[a] += 1
            if time.monotonic() >= deadline:
                break
    except KeyboardInterrupt:
        pass
    elapsed = time.monotonic() - t0
    sink.comment(f"ended {now()}  {passes} passes in {elapsed:.3f}s "
                 f"(mean pass period {elapsed / max(passes, 1) * 1000:.3f} ms)")
    sink.close()

    print(f"{passes} passes over {elapsed:.1f}s")
    for a in addrs:
        print(f"  0x{a:04X}  {changes[a]:6d} changes  last 0x{prev[a]:02X}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
