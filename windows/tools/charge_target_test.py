#!/usr/bin/env python3
r"""Test whether a host write to the EC's charge-voltage target 0x0522 sticks,
and whether the charger follows it. The live experiment for issue #91.

Background (docs/findings.md 4l, ec/annotations/charge-target-derating.md):
0x0522/0x0523 (little-endian mV) is the EC's constant-voltage charge target.
It reads 16400 mV on this pack while the pack itself requests 17400 (0x030E).
The EC derives 0x0522 from pack age and profile in a routine at bank0 0xB158,
and that routine is reached every scheduler pass from the task slot at 0x8539
(`lcall 0xe010` copies 0x030E into 0x0522, then `lcall 0xb12c` -> 0xB158
derates it). So the standing prediction is that the EC *rewrites* 0x0522
continuously and a host write will not stick. This tool measures that instead
of assuming it, and -- if the write does stick -- measures whether charge
current then falls, which is the only thing that shows the charger obeys the
byte.

Two questions, one loop:
  1. Does the write stick?  -> read 0x0522 back every interval; a value equal
     to what we wrote means it held, a value back at the original means the EC
     reverted it. This needs no particular battery state; run it at any charge.
  2. Does the charger follow it?  -> only meaningful while charging in the
     constant-voltage phase (voltage pinned ~16.4 V, current tapering, usually
     above ~65%). If the write sticks *and* is below the present pack voltage,
     charge current should fall toward zero. `ec_current_ma`/`wmi_rate_mw` are
     logged for exactly this, with the same two-source discipline as
     battery_trace.py (a stop is only a stop when both agree).

SAFETY -- this writes a live charge-voltage target:
  * Lower only. The tool refuses a target >= the current 0x0522 value; lowering
    a CV ceiling can only reduce charging, never overcharge. Raising it toward
    the pack's 17400 mV is a battery-longevity decision for the owner and is
    deliberately not offered here.
  * The original 0x0522/0x0523 is read first and restored on exit (including
    Ctrl-C / error). The EC is expected to restore it on its own within a pass
    regardless; the explicit restore is belt-and-suspenders.
  * One variable at a time, owner watching, per repo convention for live EC
    writes.

Usage (run elevated, with the vendor driver loaded):
  # question 1, safe at any charge incl. 100%: does the write stick?
  charge_target_test.py --target-mv 16300 --seconds 30 --interval 1 \
      --csv ../../evidence/battery-traces/2026-09-21-0522-stick.csv \
      --phase stick_100pct --i-mean-it

  # question 2, run while charging in CV (plug in around 75-85% first):
  charge_target_test.py --target-mv 16300 --seconds 60 --interval 2 \
      --csv ../../evidence/battery-traces/2026-09-21-0522-follow.csv \
      --phase follow_cv --i-mean-it

Addresses and values accept 0x-prefixed hex or decimal.
"""
import argparse
import csv
import datetime
import subprocess
import sys
import time

from ecrw import Ec, EcError

PS = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]

WMI_QUERY = (
    "$b = Get-CimInstance -Namespace 'root/wmi' -ClassName BatteryStatus | "
    "Select-Object -First 1; "
    "$w = Get-CimInstance -ClassName Win32_Battery | Select-Object -First 1; "
    "'{0} {1} {2} {3} {4} {5}' -f [int]$b.PowerOnline, [int]$b.Charging, "
    "[int]$b.Discharging, $b.RemainingCapacity, "
    "($b.ChargeRate - $b.DischargeRate), $w.EstimatedChargeRemaining"
)

ADDR_TARGET = 0x0522     # LE mV, the CV charge-voltage target under test
ADDR_REQUESTED = 0x030E  # LE mV, the pack's own requested ChargingVoltage
ADDR_CURRENT = 0x0434    # LE mA, battery current (validated in ec_validate.py)
ADDR_VOLTAGE = 0x0438    # LE mV, terminal voltage
ADDR_PROFILE = 0x07A6    # charge profile mask, bits 4-5
ADDR_GATE = 0x0490       # derating routine's gate byte (bits 0/1 govern 0xB158)


def u16(ec, addr):
    return ec.read(addr) | (ec.read(addr + 1) << 8)


def w16(ec, addr, val):
    ec.write(addr, val & 0xFF)
    ec.write(addr + 1, (val >> 8) & 0xFF)


def wmi():
    out = subprocess.run(PS + [WMI_QUERY], capture_output=True, text=True,
                         check=True).stdout.split()
    keys = ("ac", "charging", "discharging", "remaining_mwh", "rate_mw", "capacity")
    return dict(zip(keys, (int(x) for x in out)))


def _int(s):
    return int(s, 16) if str(s).lower().startswith("0x") else int(s, 0)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-mv", required=True, type=_int,
                    help="new charge-voltage target in mV; must be below the "
                         "current 0x0522 value")
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--phase", default="")
    ap.add_argument("--hold", action="store_true",
                    help="re-assert the write every loop (and every --hold-ms "
                         "within it), to try to pin 0x0522 against the EC's "
                         "own rewrite. Use --interval 0.2 or so. Without this "
                         "the target is written once and only observed.")
    ap.add_argument("--hold-ms", type=float, default=20.0,
                    help="with --hold, gap between re-writes inside one "
                         "interval (default 20 ms)")
    ap.add_argument("--i-mean-it", action="store_true",
                    help="required: this writes a live charge-voltage target")
    args = ap.parse_args(argv)

    cols = ["ts", "phase", "t_s", "target_written_mv", "target_readback_mv",
            "held", "requested_mv", "ec_current_ma", "ec_voltage_mv",
            "profile_07a6", "gate_0490", "ac", "charging", "capacity",
            "remaining_mwh", "wmi_rate_mw"]

    try:
        with Ec() as ec:
            original = u16(ec, ADDR_TARGET)
            requested = u16(ec, ADDR_REQUESTED)
            b0 = wmi()
            print(f"baseline: 0x0522 target = {original} mV, "
                  f"pack requested (0x030E) = {requested} mV")
            print(f"          current = {u16(ec, ADDR_CURRENT)} mA, "
                  f"voltage = {u16(ec, ADDR_VOLTAGE)} mV, "
                  f"0x07A6 = 0x{ec.read(ADDR_PROFILE):02X}, "
                  f"0x0490 = 0x{ec.read(ADDR_GATE):02X}")
            print(f"          AC={b0['ac']} charging={b0['charging']} "
                  f"capacity={b0['capacity']}% "
                  f"wmi_rate={b0['rate_mw']} mW")

            if args.target_mv >= original:
                print(f"refusing: target {args.target_mv} mV is not below the "
                      f"current {original} mV (lower only).", file=sys.stderr)
                return 2
            if args.target_mv < 12000:
                print(f"refusing: target {args.target_mv} mV is implausibly low "
                      "for a 4S pack; check units.", file=sys.stderr)
                return 2
            if not args.i_mean_it:
                print("refusing to write without --i-mean-it", file=sys.stderr)
                return 2

            fh = open(args.csv, "a", newline="")
            w = csv.writer(fh)
            if fh.tell() == 0:
                w.writerow(cols)

            t0 = time.time()
            try:
                w16(ec, ADDR_TARGET, args.target_mv)
                first = u16(ec, ADDR_TARGET)
                print(f"wrote 0x0522 = {args.target_mv} mV, immediate "
                      f"readback = {first} mV "
                      f"({'held' if first == args.target_mv else 'reverted'})"
                      f"{' [hold mode]' if args.hold else ''}")
                while True:
                    if args.hold:
                        # Re-assert repeatedly for the whole interval, so the
                        # byte spends as much time as possible at our value.
                        t_end = time.time() + args.interval
                        while time.time() < t_end:
                            w16(ec, ADDR_TARGET, args.target_mv)
                            time.sleep(args.hold_ms / 1000.0)
                    tb = u16(ec, ADDR_TARGET)
                    if args.hold:
                        # Sample the readback right after a fresh write, to see
                        # if it holds even momentarily.
                        w16(ec, ADDR_TARGET, args.target_mv)
                        tb = u16(ec, ADDR_TARGET)
                    b = wmi()
                    row = [
                        datetime.datetime.now().astimezone().isoformat(
                            timespec="seconds"),
                        args.phase, round(time.time() - t0, 1),
                        args.target_mv, tb,
                        int(tb == args.target_mv), requested,
                        u16(ec, ADDR_CURRENT), u16(ec, ADDR_VOLTAGE),
                        f"0x{ec.read(ADDR_PROFILE):02X}",
                        f"0x{ec.read(ADDR_GATE):02X}",
                        b["ac"], b["charging"], b["capacity"],
                        b["remaining_mwh"], b["rate_mw"],
                    ]
                    w.writerow(row)
                    fh.flush()
                    print("  ".join(str(x) for x in row), flush=True)
                    if time.time() - t0 >= args.seconds:
                        break
                    if not args.hold:  # hold mode already spent the interval
                        time.sleep(args.interval)
            finally:
                w16(ec, ADDR_TARGET, original)
                restored = u16(ec, ADDR_TARGET)
                print(f"restored 0x0522 -> {original} mV, readback = {restored} mV")
                fh.close()
    except EcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
