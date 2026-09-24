#!/usr/bin/env python3
r"""Cross-check `ecrw.py`'s EC reads against values Windows reports independently.

The point is not to discover anything: it is to establish that the bytes
`ecrw.py` returns really are this EC's live state, before any of them is used as
evidence or written to.

The check is on battery terminal voltage, which under load swings by hundreds of
mV from second to second, so a match is not something a broken read path could
produce by luck. It is sampled two ways at once:

  * `ecrw.py` reading EC `0x0438/0x0439` as a little-endian 16-bit value,
  * the ACPI battery driver's `root\wmi` `BatteryStatus.Voltage`.

They do not match instant-for-instant, because `BatteryStatus` serves a cached
value that the battery driver refreshes on its own schedule. What it does do is
*repeat*, exactly, a value the EC held a moment earlier. So the test is not
"are they equal now" but "is every WMI reading an exact copy of some EC reading
from this run" -- which is both strictly harder to pass by accident and the
correct model of how the two sources relate.

A second arm samples `0x0436`/`0x0437` beside the same WMI
`RemainingCapacity`. That pair is `XDATA_0436_PAIR` in
`ec/annotations/registers.yaml`: upstream calls it
`EC_ADDR_BAT_REMAIN_CAPACITY` (`uniwill-acpi.c:79,81`), and the one committed
capture of it steps `+0x14` every ~35 s with `0x0437` never moving
(`docs/findings.md` 4g), which does not read like a charge figure. Calling it a
capacity *or* a counter on that evidence is the "reads as" overclaim
`CLAUDE.md` warns about, so the name is a placeholder until someone takes a
live read beside a second source.
`docs/hardware-tests/remain-capacity-0436.md` is that procedure, written for a
human at the machine. **Nothing in this file has been run on one.**

**The second arm reports; it does not conclude.** A run in which WMI's
RemainingCapacity is never an exact copy of the EC pair is an observation and
not a refutation: a counter fails the same test, and the equality quietly
assumes the EC's unit is mWh, which nothing here establishes. The arm cannot
tell the other way either -- nothing in it says the pair *is* a capacity. So it
does not change the exit code, and the voltage arm's committed 10/10 stays the
only verdict this script returns.

The two arms keep separate cadences on purpose. The voltage arm's 10 samples
at 2.0 s are `docs/findings.md` 4g exactly as committed, and a bare invocation
still reproduces it; the capacity arm defaults to 1 s because its discriminator
is a fall of several hundred mWh across a discharge rather than a
second-to-second swing.

Run elevated:
  python windows\tools\ec_validate.py
  python windows\tools\ec_validate.py --samples 900 --interval 1 ^
      --csv 2026-09-23-0436-capacity.csv
"""
import argparse
import csv
import datetime
import subprocess
import sys
import time

from ecrw import Ec

PS = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]

WMI_QUERY = (
    "$b = Get-CimInstance -Namespace 'root/wmi' -ClassName BatteryStatus | "
    "Select-Object -First 1; "
    "'{0} {1} {2} {3} {4}' -f $b.Voltage, $b.RemainingCapacity, "
    "$b.ChargeRate, $b.DischargeRate, [int]$b.PowerOnline"
)

FIELDS = ("voltage_mv", "remaining_mwh", "charge_mw", "discharge_mw", "ac_online")

# Addresses under test. 0x043E/0x044F are registers.yaml's confirmed-working
# CPU_TEMP/GPU_TEMP; 0x04A6/7 is BAT_CYCLE_COUNT. 0x0438 is the candidate this
# script exists to pin down.
ADDR_VOLTAGE = 0x0438
ADDR_CPU_TEMP = 0x043E
ADDR_GPU_TEMP = 0x044F
ADDR_CYCLES = 0x04A6

# The 0x0436 capacity arm. Every byte it touches, and nothing else: 0x0402/3
# design capacity for the scale, 0x0404/5 full capacity for the bound, 0x0434/5
# current and 0x0438/9 voltage so a human can reconstruct mW from the pack's own
# numbers and confirm the pack really was discharging under the load.
ADDR_REMAIN = 0x0436
ADDR_DESIGN_CAPACITY = 0x0402
ADDR_FULL_CAPACITY = 0x0404
ADDR_CURRENT = 0x0434
CAP_ADDRS = (ADDR_REMAIN, ADDR_DESIGN_CAPACITY, ADDR_FULL_CAPACITY,
             ADDR_CURRENT, ADDR_VOLTAGE)

# The page the capacity arm is allowed to read, and the reason the check below
# is in code rather than in the procedure prose: 0x0460-0x046F is the
# fan-tachometer block, and reading those through ECRR stalled the fans on a
# sibling board (issue #94, docs/related-projects.md). A typo in CAP_ADDRS is
# the only way this arm gets there.
PAGE_FIRST, PAGE_LAST = 0x0400, 0x045F

# The voltage arm's numbers, unchanged: docs/findings.md 4g's 10/10 is a
# committed finding and a bare invocation still has to reproduce it.
SAMPLES = 10
INTERVAL = 2.0

# The capacity arm's, from the issue: 1 s, because the thing it is looking for
# is a fall over a discharge rather than a second-to-second swing.
CAP_SAMPLES = 10
CAP_INTERVAL = 1.0

CAP_COLUMNS = ["ts", "ec_0436", "wmi_remaining_mwh", "ec_0404_full",
               "ec_0402_design", "ec_0434_ma", "ec_0438_mv", "ac",
               "charge_mw", "discharge_mw"]


def wmi_battery():
    out = subprocess.run(PS + [WMI_QUERY], capture_output=True, text=True,
                         check=True).stdout.split()
    return dict(zip(FIELDS, (int(x) for x in out)))


def u16(ec, addr):
    """Little-endian 16-bit read, the width the battery fields use."""
    return ec.read(addr) | (ec.read(addr + 1) << 8)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


def check_page(addrs):
    """Every address of a 16-bit read has to stay on the page; return the list.

    The bound is on `addr` *and* `addr+1`, because a read of 0x045F reaches
    0x0460 and that is the first fan-tach byte. Raises ValueError naming what
    is wrong rather than asserting, so it survives `python -O`.
    """
    off = [a for a in addrs
           if not (PAGE_FIRST <= a <= PAGE_LAST
                   and PAGE_FIRST <= a + 1 <= PAGE_LAST)]
    if off:
        raise ValueError(
            f"address(es) {', '.join(f'0x{a:04X}' for a in off)} read outside "
            f"0x{PAGE_FIRST:04X}-0x{PAGE_LAST:04X}; 0x0460-0x046F is the "
            "fan-tach block (issue #94) and the capacity arm must not reach it")
    return list(addrs)


class SampleCsv:
    """Append-only CSV, one row per sample, header written only to a new file.

    The same shape as `ec_watch.py`'s CsvSink, minus the lock: this arm is one
    thread, and there is nothing here to interleave with. Append mode is the
    part that matters -- a run stopped and resumed has to extend the capture
    rather than replace it, so a finished run can be committed under
    `evidence/ec-watch/` as the file it was captured to.
    """

    def __init__(self, path, columns=CAP_COLUMNS):
        self._fh = open(path, "a", newline="")
        self._writer = csv.writer(self._fh)
        if self._fh.tell() == 0:
            self.row(columns)

    def row(self, values):
        if self._fh.closed:
            return
        self._writer.writerow(values)
        self._fh.flush()

    def close(self):
        self._fh.close()


def voltage_arm(ec):
    """docs/findings.md 4g's test, exactly as committed. Returns (rows, matched).

    Left alone deliberately: the 10/10 is a cited finding and the function that
    produced it is what a reader checks the citation against.
    """
    rows = []
    for i in range(SAMPLES):
        w = wmi_battery()
        rows.append({
            "ec_mv": u16(ec, ADDR_VOLTAGE),
            "wmi_mv": w["voltage_mv"],
            "ac": w["ac_online"],
            "cpu": ec.read(ADDR_CPU_TEMP),
            "gpu": ec.read(ADDR_GPU_TEMP),
            "cycles": u16(ec, ADDR_CYCLES),
        })
        if i < SAMPLES - 1:
            time.sleep(INTERVAL)

    ec_seen = {r["ec_mv"] for r in rows}

    print(f"{'#':>2}  {'EC 0x0438':>9}  {'WMI mV':>7}  {'WMI is an EC value':>18}"
          f"  {'cpu':>4}  {'gpu':>4}")
    matched = 0
    for i, r in enumerate(rows):
        # Only credit a WMI reading that the EC had already shown by this point:
        # letting it match a *later* EC value would be matching on noise.
        earlier = {x["ec_mv"] for x in rows[:i + 1]}
        ok = r["wmi_mv"] in earlier
        matched += ok
        print(f"{i:>2}  {r['ec_mv']:>9}  {r['wmi_mv']:>7}  "
              f"{('yes' if ok else 'NO'):>18}  {r['cpu']:>4}  {r['gpu']:>4}")

    print()
    print(f"EC 0x0438 took {len(ec_seen)} distinct values across {SAMPLES} "
          f"samples: {sorted(ec_seen)}")
    print(f"exact-copy matches: {matched}/{SAMPLES} WMI readings equal an EC "
          "reading already seen this run")
    return rows, matched


def capacity_arm(ec, samples, interval, sink=None):
    """Sample 0x0436/7 beside WMI RemainingCapacity. Reports; grades nothing.

    Two observations come out, and the caller is expected to read them as
    observations:

    * the docs/findings.md 4g exact-copy test, with the same one-directional
      guard the voltage arm uses -- a WMI reading counts only if the EC had
      already held that value earlier in this run;
    * whether the pair ever exceeded 0x0404/5, which a remaining capacity could
      not and a small periodic counter also could not.

    Returns (rows, matched, over_bound), the last being the first sample whose
    pair came in above the full-capacity reading.
    """
    rows = []
    for i in range(samples):
        w = wmi_battery()
        row = {
            "ts": now(),
            "ec_0436": u16(ec, ADDR_REMAIN),
            "wmi_remaining_mwh": w["remaining_mwh"],
            "ec_0404_full": u16(ec, ADDR_FULL_CAPACITY),
            "ec_0402_design": u16(ec, ADDR_DESIGN_CAPACITY),
            "ec_0434_ma": u16(ec, ADDR_CURRENT),
            "ec_0438_mv": u16(ec, ADDR_VOLTAGE),
            "ac": w["ac_online"],
            "charge_mw": w["charge_mw"],
            "discharge_mw": w["discharge_mw"],
        }
        rows.append(row)
        if sink:
            sink.row([row[c] for c in CAP_COLUMNS])
        if i < samples - 1:
            time.sleep(interval)

    matched = 0
    over_bound = None
    for i, r in enumerate(rows):
        earlier = {x["ec_0436"] for x in rows[:i + 1]}
        r["exact_copy"] = r["wmi_remaining_mwh"] in earlier
        matched += r["exact_copy"]
        r["within_bound"] = r["ec_0436"] <= r["ec_0404_full"]
        if not r["within_bound"] and over_bound is None:
            over_bound = r

    ec_seen = {r["ec_0436"] for r in rows}
    print(f"{'#':>2}  {'EC 0x0436':>9}  {'WMI mWh':>7}  {'WMI is an EC value':>18}"
          f"  {'0x0404 full':>10}  {'<= full':>7}")
    for i, r in enumerate(rows):
        print(f"{i:>2}  {r['ec_0436']:>9}  {r['wmi_remaining_mwh']:>7}  "
              f"{('yes' if r['exact_copy'] else 'NO'):>18}  "
              f"{r['ec_0404_full']:>10}  "
              f"{('yes' if r['within_bound'] else 'NO'):>7}")

    print()
    print(f"EC 0x0436/7 took {len(ec_seen)} distinct values across {samples} "
          f"samples: {sorted(ec_seen)}")
    print(f"EC 0x0402/3 (design capacity) first read: {rows[0]['ec_0402_design']}")
    print(f"EC 0x0436/7 <= EC 0x0404/5 (full capacity) on every sample: "
          f"{'no' if over_bound else 'yes'}")
    print(f"exact-copy matches: {matched}/{samples} WMI RemainingCapacity "
          "readings equal an EC 0x0436/7 reading already seen this run")
    if len(ec_seen) < 3:
        print("INCONCLUSIVE: 0x0436 barely moved, so this says little either "
              "way. Re-run across a real discharge.")
    print("Both numbers above are observations. A counter fails the exact-copy "
          "test the same way, and the equality assumes the EC's unit is mWh; "
          "grading this is a human's, per "
          "docs/hardware-tests/remain-capacity-0436.md.")
    return rows, matched, over_bound


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=CAP_SAMPLES,
                    help=f"capacity-arm samples (default: {CAP_SAMPLES})")
    ap.add_argument("--interval", type=float, default=CAP_INTERVAL,
                    help=f"seconds between capacity-arm samples (default: "
                         f"{CAP_INTERVAL:g}; the voltage arm keeps its own "
                         f"{INTERVAL:g}, which is 4g's as committed)")
    ap.add_argument("--csv", metavar="PATH",
                    help="append one row per capacity-arm sample to this CSV, "
                         "header written only if the file is new")
    args = ap.parse_args(argv)

    try:
        check_page(CAP_ADDRS)
    except ValueError as e:
        print(f"refusing to run: {e}", file=sys.stderr)
        return 2

    sink = SampleCsv(args.csv) if args.csv else None
    try:
        with Ec() as ec:
            print(f"--- 0x0438/9 voltage arm, {SAMPLES} samples at "
                  f"{INTERVAL:g}s (docs/findings.md 4g, unchanged) ---")
            rows, matched = voltage_arm(ec)
            if len({r["ec_mv"] for r in rows}) < 3:
                print("INCONCLUSIVE: the voltage barely moved, so a match "
                      "proves little. Re-run under load, or while charging.")
                return 2
            print(f"EC 0x04A6/7 (BAT_CYCLE_COUNT, registers.yaml "
                  f"confirmed-working) = {rows[0]['cycles']}")
            print(f"EC 0x043E/0x044F (CPU/GPU temp, confirmed-working) = "
                  f"{rows[-1]['cpu']} / {rows[-1]['gpu']} C")

            print(f"\n--- 0x0436/7 capacity arm, {args.samples} samples at "
                  f"{args.interval:g}s ---")
            capacity_arm(ec, args.samples, args.interval, sink)
    finally:
        if sink:
            sink.close()

    # The voltage arm's 10/10 is the only verdict this script returns. One
    # stray mismatch is expected whenever the driver's cache is refreshed
    # between our two reads; a read path that were not the EC would match
    # ~never. The capacity arm cannot move this either way -- see its docstring.
    return 0 if matched >= SAMPLES - 2 else 1


if __name__ == "__main__":
    sys.exit(main())
