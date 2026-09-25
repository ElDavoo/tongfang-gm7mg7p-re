#!/usr/bin/env python3
r"""Issue #174: sample 0x0456 and both arms of store_scaled_quotient_0449 in one
read-only loop, and say which arm produced each 0x0449.

Upstream calls 0x0456 `EC_ADDR_SYSTEM_ID` and reads bit 7 as `HAS_GPU`; bit 6
is load-bearing in the image, where 0xF3C9 picks a divisor from it before
scaling 0x060C/0x060D into 0x0449 (ec/decompiled/bank1/F3C9.asm, F3D7.asm).
Neither half has been exercised live, and there is no laptop here. This is the
instrument for that run: six reads per sweep, no writes, and per sweep a
report of which arm the arithmetic says produced the 0x0449 that was just
read.

**The selector is not known, so the branch is derived rather than observed.**
F3D7 branches on R7, and R7 is set nowhere in that listing or in the 0x198A
trampoline it calls (F3D7.c's plate comment says the same). This probe does
the reverse of what a trace would do: it computes what each arm would have
written from the other five bytes and checks that against the 0x0449 actually
read. A sample that one arm reproduces is a sample that arm is *consistent*
with. That is a weaker thing than knowing which arm ran, and §5 of
docs/hardware-tests/system-id-0456-bit6-divisor.md says so where a reader
needs it.

The arithmetic, read off the listings rather than the decompiled C:

  * 0x8886 -- `[DPTR]` goes to R1 and `[DPTR+1]` to R2, so a pair is
    little-endian with the lower address in the low byte.
  * 0xA5E6 -- sixteen rounds of shift-and-subtract; on exit R1 is the
    quotient's high byte, R2 its low byte, R3:R4 the remainder. R0 and R5
    accumulate the quotient bits and are fully shifted out over the sixteen
    rounds, so the result does not depend on their entry value.
  * 0xF3C9 -- R3 = 0x22 if 0x0456 bit 6 is set, else 0x44. Nine instructions,
    no ambiguity; F3C9.c drops both assignments and reads as returning one
    value, so the .asm is the one to cite.
  * 0xF3D7 -- R7 == 0: R3 = 100, R4 = 0, divide 0x0434/0x0435 by it, write
    the quotient's high byte to 0x0449. R7 != 0: call 0xF3C9, R4 = 0, read
    0x060C/0x060D, mask R2 (the high byte) with 0x03, multiply the 16-bit
    value by 10 in two `mul AB`s, divide, write the same byte. Both arms store
    R1, the *high* byte, on both paths.

`060c-branch`, `current-branch` and `unexplained` are the three outcomes a
sample can have, and a fourth is honest to name: `both-arms`, for a 0x0449
that both arms reproduce. At low magnitudes both predict 0 or 1, so this is
reachable in the field, and folding it into either arm would be picking the
one that reads better.

**The divisor a `060c-branch` sample implies is reported next to bit 6, not
folded into a pass/fail.** A sample on the 0x060C arm matched under one of the
two divisors; 0xF3C9 says which one bit 6 should have selected. A sample that
reproduces under 0x22 while 0x0456 bit 6 is clear is the contradiction, and a
single pass/fail would have swallowed it.

Samples the arithmetic cannot place -- and samples both arms place -- are
printed with their raw six bytes as they happen, so a disagreement is
diagnosable from the log without re-running anything. Every sample also goes
to the CSV with its branch and implied divisor, which is what §4 of the
procedure reads off.

**The annotated model and the one committed capture do not obviously agree,
and this tool is built to show that rather than to settle it.** The
`anl 0x02,#0x3` caps arm B's dividend at 0x03FF, so the byte arm B stores
never leaves {0, 1}; arm A needs 25600 mA to leave 0 and 51200 mA -- 51.2 A --
to reach 2. The one capture covering the byte,
evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv, has 0x0449 across
0x22-0x5A over 238 changes. Reading that capture against the model puts every
one of its 237 gradeable 0x0449 values in `unexplained`; it carries no 0x0456,
0x0434 or 0x0435 at all, so it cannot exercise the bit-6 half either. Which
of the two is wrong is not decided here, and the run decides it. Do not read
a low match count as the model failing.

**There is no write path.** Nothing is written to the EC: no `write`
subcommand, no `--i-mean-it` gate, because there is no write to gate. The
address guard below is the only thing that can refuse a run, and it refuses
before the EC is opened.

**No interval here is validated.** 0.5 s is the procedure's starting point and
nothing more -- issue #94 is the open work to make these tools safe by default,
and nothing in this repository measures an ECRR's cost. Six reads a sweep
against the 206 `manual_fan_ctrl_probe.py` already sweeps under load is much
less traffic, but "much less" is not a safety argument. If the fans audibly
change, stop and raise it.

Run elevated, next to ecrw.py. Needs the vendor's ACPI driver present.

Usage:
  system_id_probe.py --seconds 300 --mark --csv out.csv
  system_id_probe.py --start 0x0400 --len 0x60      # context range, still guarded
"""
import argparse
import csv
import datetime
import sys
import threading
import time

from ecrw import Ec, EcError

# Exclusive of 0x0460: the fan-tach bytes are the next page (issue #94), and
# the allow-list below is what keeps every flag out of them.
PAGE = range(0x0400, 0x0460)
OFF_PAGE = (0x060C, 0x060D)
ALLOWED = set(PAGE) | set(OFF_PAGE)
FAN_TACH = range(0x0460, 0x0470)
CONTEXT_LEN = 0x60

WATCH = [0x0456, 0x060C, 0x060D, 0x0449, 0x0434, 0x0435]

CURRENT_DIV = 0x64
DIV_BIT6_SET = 0x22
DIV_BIT6_CLEAR = 0x44

CSV_HEADER = ["ts", "sweep"] + [f"0x{a:04X}" for a in WATCH] + ["branch", "implied"]


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def divisor_from_bit6(system_id):
    """0xF3C9: R3 = 0x22 if 0x0456 bit 6 is set, else 0x44. R4 is 0 either way."""
    return DIV_BIT6_SET if system_id & 0x40 else DIV_BIT6_CLEAR


def arm_current(current_ma):
    """The R7 == 0 arm: 0x0434/0x0435 divided by 100, high byte stored."""
    return ((current_ma // CURRENT_DIV) >> 8) & 0xFF


def arm_060c(lo, hi, divisor):
    """The R7 != 0 arm: 0x060C/0x060D with the high byte masked, * 10, divided.

    The multiply is the listing's two `mul AB`s: the low byte's product
    supplies R1 and its carry R0, the high byte's product is added to that
    carry into R2, and the carry out of that `add` is discarded. With the high
    byte masked to 0-3 it cannot be reached, but masking it is the listing and
    masking it is what a reader of 0xF3D7 would have to check.
    """
    hi &= 0x03
    product = (((hi * 10) & 0xFF) + ((lo * 10) >> 8)) << 8 | ((lo * 10) & 0xFF)
    return ((product // divisor) >> 8) & 0xFF


def classify(snap):
    """Label one sample by which arm(s) reproduce its 0x0449.

    Returns (label, implied) with `implied` the arm-B divisors this sample is
    consistent with, in the order 0xF3C9 names them. It is empty for
    `current-branch` and `unexplained` -- a divisor listed there would mean
    the arm matched too, which is the `both-arms` case -- and can hold both
    divisors for one sample.
    """
    target = snap[0x0449]
    current_ma = snap[0x0434] | snap[0x0435] << 8
    current = arm_current(current_ma)
    implied = [d for d in (DIV_BIT6_SET, DIV_BIT6_CLEAR)
               if arm_060c(snap[0x060C], snap[0x060D], d) == target]
    if current == target:
        return ("both-arms" if implied else "current-branch"), implied
    if implied:
        return "060c-branch", implied
    return "unexplained", implied


def raw(snap):
    return "  ".join(f"0x{a:04X}=0x{snap[a]:02X}" for a in WATCH)


def refuse(addrs):
    """Refuse a watch set that leaves the allow-list, before the EC is opened.

    The exclusion is not a formality: reading 0x0460-0x046F through ECRR
    stalled the fans on a sibling board (#94, docs/related-projects.md). It
    lives in the tool rather than in the procedure because a --start that
    walks into the next page is a flag, and prose does not stop flags.
    """
    bad = sorted(a for a in addrs if a not in ALLOWED)
    if not bad:
        return
    where = ", ".join(f"0x{a:04X}" for a in bad)
    if any(a in FAN_TACH for a in bad):
        where += " -- 0x0460-0x046F are the fan-tach bytes (#94), never read"
    sys.exit(f"refusing to read outside 0x0400-0x045F and "
             f"{{0x060C,0x060D}}: {where}")


def watch_set(args):
    """The addresses one sweep reads, in order and without repeats.

    The six are always swept; --start adds a context range the arithmetic does
    not use, for an operator who wants the rest of the page in the same CSV.
    """
    addrs = list(WATCH)
    if args.start is not None:
        length = CONTEXT_LEN if args.length is None else args.length
        addrs += list(range(args.start, args.start + length))
    refuse(addrs)
    seen, ordered = set(), []
    for a in addrs:
        if a not in seen:
            seen.add(a)
            ordered.append(a)
    return ordered


class CsvSink:
    """The CSV, plus the lock that makes it safe to write from two threads.

    The sweep loop runs on the main thread and marks arrive on the stdin
    thread, so without this a mark can land in the middle of a sample row.

    A second class of this name rather than `ec_watch.py`'s, because this is
    deployed on its own; `utf-8` is declared for the same reason and with the
    same repeated literal, so a mark label of `§` is the same byte here as it
    is in a capture the grader reads.
    """

    def __init__(self, path):
        self._fh = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        self._lock = threading.Lock()
        if self._fh.tell() == 0:
            self.row(CSV_HEADER)

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
    """Lets the operator stamp 'I switched the GPU mode now' into the log."""

    def __init__(self, sink=None):
        self.marks = []
        self._n = 0
        self._sink = sink

    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()

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
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after this long (default: until Ctrl-C)")
    ap.add_argument("--interval", type=float, default=0.5,
                    help="seconds between sweeps; the procedure's starting "
                         "point, not a validated-safe value (default: 0.5)")
    ap.add_argument("--csv", help="write every sample, and every mark if "
                                  "--mark is given, to this CSV")
    ap.add_argument("--mark", action="store_true",
                    help="read stdin; each line stamps a labelled mark, into "
                         "the CSV too if --csv is given")
    ap.add_argument("--start", type=lambda s: int(s, 0),
                    help="also read a context range starting here; it is "
                         "guarded like everything else, so 0x0460 and up is "
                         "refused before the EC is opened")
    ap.add_argument("--len", dest="length", type=lambda s: int(s, 0),
                    help=f"length of the --start context range (default: "
                         f"0x{CONTEXT_LEN:02X})")
    args = ap.parse_args(argv)

    if args.length is not None and args.start is None:
        ap.error("--len needs --start")
    addrs = watch_set(args)

    sink = CsvSink(args.csv) if args.csv else None
    marker = Marker(sink)
    if args.mark:
        marker.start()

    counts = {}            # label -> samples
    implied = {}           # divisor -> [samples, of which bit 6 agreed]
    disagreeing = 0
    bit7 = None            # None until the first sample says
    bit7_set = 0
    bit7_changes = 0
    sweeps = 0
    t0 = time.time()

    try:
        with Ec() as ec:
            print(f"{now()}  {len(addrs)} address(es) per sweep, every "
                  f"{args.interval:g}s, no writes:")
            print("  " + " ".join(f"0x{a:04X}" for a in addrs))
            print("  no interval here is validated (#94 owns making these "
                  "tools safe by default): if the fans audibly change, stop "
                  "and raise it")
            print("  samples the arithmetic cannot place are printed as they "
                  "happen, one line each")
            if args.mark:
                print("type a label + Enter to stamp a mark; Ctrl-C to stop")
            else:
                print("Ctrl-C to stop")

            while True:
                time.sleep(args.interval)
                snap = {a: ec.read(a) for a in addrs}
                # Counted once the six are in hand, so a sweep the EC refused
                # mid-read is not in the denominator of the report below.
                sweeps += 1
                ts = now()
                label, divisors = classify(snap)
                counts[label] = counts.get(label, 0) + 1
                for d in divisors:
                    slot = implied.setdefault(d, [0, 0])
                    slot[0] += 1
                    if divisor_from_bit6(snap[0x0456]) == d:
                        slot[1] += 1

                set7 = 1 if snap[0x0456] & 0x80 else 0
                bit7_set += set7
                if set7 != bit7:
                    if bit7 is not None:
                        bit7_changes += 1
                        print(f"{ts}  0x0456 bit 7 {bit7} -> {set7}  "
                              f"(0x0456=0x{snap[0x0456]:02X})", flush=True)
                    bit7 = set7

                if label in ("unexplained", "both-arms"):
                    disagreeing += 1
                    print(f"{ts}  sweep {sweeps:>4}  {label:<14}  {raw(snap)}",
                          flush=True)

                if sink:
                    sink.row([ts, sweeps] + [f"0x{snap[a]:02X}" for a in WATCH]
                             + [label,
                                "|".join(f"0x{d:02X}" for d in divisors)])

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

    report(counts, implied, disagreeing, bit7, bit7_set, bit7_changes,
           sweeps, time.time() - t0, marker)
    return 0


def report(counts, implied, disagreeing, bit7, bit7_set, bit7_changes, sweeps,
           elapsed, marker):
    """Per-arm counts, the implied divisor against bit 6, and the bit-7 line.

    Every number here is arithmetic over the six bytes each sweep read. The
    labels say an arm is *consistent with* a sample, not that it ran, and
    nothing below is a status or a verdict -- §7 of the procedure is the call.
    """
    print(f"\n=== {sweeps} samples over {elapsed:.0f}s ===")
    print("\nper arm -- an arm matches a sample when its arithmetic "
          "reproduces that\nsample's 0x0449:")
    for label, what in (
            ("current-branch", "(0x0434|0x0435<<8) / 100"),
            ("060c-branch", "((0x060C|0x060D<<8) & high 0x03) * 10 / 0x22|0x44"),
            ("both-arms", "both arms reproduce 0x0449; R7 is not established"),
            ("unexplained", "neither arm reproduces 0x0449"),
    ):
        print(f"  {label:<16} {counts.get(label, 0):>5} of {sweeps}  {what}")

    print("\nbit 6, against the divisor each matching 0x060C sample implies:")
    if implied:
        for d in (DIV_BIT6_SET, DIV_BIT6_CLEAR):
            n, agree = implied.get(d, [0, 0])
            print(f"  implied 0x{d:02X}  {n:>5} sample(s)  bit 6 agreed on "
                  f"{agree}, disagreed on {n - agree}")
    else:
        print("  no sample landed on the 0x060C arm, so no divisor is "
              "implied and this says nothing about bit 6")

    print(f"\n0x0456 bit 7: set on {bit7_set} of {sweeps} samples, changed "
          f"{bit7_changes} times"
          + ("" if bit7 is None else f", last value {bit7}"))
    if disagreeing:
        print(f"\nsamples the arithmetic did not place: {disagreeing}. They "
              "are printed above with\ntheir raw bytes, and every sample is in "
              "the CSV's `branch` column.")
    if marker.marks:
        print("\nmarks:")
        for ts, label in marker.marks:
            print(f"  {ts}  {label}")
    print("\nNo status and no verdict: the branch is derived from the observed "
          "0x0449, not\nfrom R7, which no listing here sets. Section 7 of "
          "docs/hardware-tests/system-id-0456-bit6-divisor.md\nis the call, "
          "and a low match count is not by itself a refutation.")


if __name__ == "__main__":
    sys.exit(main())
