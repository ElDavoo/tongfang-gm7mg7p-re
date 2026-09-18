#!/usr/bin/env python3
r"""Coulomb-count a charge on Windows, alongside the EC bytes that might govern it.

The Windows counterpart of `linux/battery-trace/limit-pair-test`. Same discipline
as `docs/findings.md` 4a demands: the question "did charging stop" is answered
with *current*, not with `capacity` (which is quantised and lags) and not with a
resting `voltage` (which is what 4a got wrong). Current reaching and staying at
zero while AC is still present is the only thing that counts as a stop.

Two independent current sources are logged side by side on purpose:

  * `ec_current_ma`  -- EC 0x0434/0x0435, little-endian mA
  * `wmi_rate_mw`    -- the ACPI battery driver's ChargeRate/DischargeRate

The ACPI one is cached and periodically reads 0, so it cannot carry the argument
by itself; the EC one is live but is this repo's own inference. Requiring both
to agree before calling a stop is what keeps a cache artefact from being written
up as an enforced charge limit.

Usage:
  battery_trace.py --csv evidence/battery-traces/2026-09-18-stationary.csv
  battery_trace.py --interval 15 --seconds 3600
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

# EC addresses logged every sample.
#   0x07A6  CHARGING_PROFILE_MASK  (registers.yaml, confirmed-working-partially)
#   0x07B9  CHARGE_CTRL / BATTERY_CHARGE_LIMIT_UP   (ECSpec.cs)
#   0x07D0  BATTERY_CHARGE_LIMIT_DOWN               (ECSpec.cs)
#   0x07D1  the byte the DSDT's T1WR pairs with 0x07D0
WATCH = [0x07A6, 0x07B9, 0x07D0, 0x07D1, 0x07CC]

ADDR_CURRENT = 0x0434   # little-endian mA, cross-checked against WMI's rate
ADDR_VOLTAGE = 0x0438   # little-endian mV, validated in ec_validate.py


def u16(ec, addr):
    return ec.read(addr) | (ec.read(addr + 1) << 8)


def wmi():
    out = subprocess.run(PS + [WMI_QUERY], capture_output=True, text=True,
                         check=True).stdout.split()
    keys = ("ac", "charging", "discharging", "remaining_mwh", "rate_mw", "capacity")
    return dict(zip(keys, (int(x) for x in out)))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--interval", type=float, default=15.0)
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after this long (default: until Ctrl-C)")
    ap.add_argument("--phase", default="",
                    help="label written into every row of this run")
    args = ap.parse_args(argv)

    cols = (["ts", "phase", "ac", "charging", "capacity", "remaining_mwh",
             "wmi_rate_mw", "ec_current_ma", "ec_voltage_mv"]
            + [f"ec_{a:04x}" for a in WATCH])

    fh = open(args.csv, "a", newline="")
    w = csv.writer(fh)
    if fh.tell() == 0:
        w.writerow(cols)

    t0 = time.time()
    try:
        with Ec() as ec:
            while True:
                b = wmi()
                row = [
                    datetime.datetime.now().astimezone().isoformat(
                        timespec="seconds"),
                    args.phase, b["ac"], b["charging"], b["capacity"],
                    b["remaining_mwh"], b["rate_mw"],
                    u16(ec, ADDR_CURRENT), u16(ec, ADDR_VOLTAGE),
                ] + [f"0x{ec.read(a):02X}" for a in WATCH]
                w.writerow(row)
                fh.flush()
                print("  ".join(str(x) for x in row), flush=True)
                if args.seconds and time.time() - t0 >= args.seconds:
                    break
                time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    except EcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
