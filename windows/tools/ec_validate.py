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

Run elevated:  python windows\tools\ec_validate.py
"""
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

SAMPLES = 10
INTERVAL = 2.0


def wmi_battery():
    out = subprocess.run(PS + [WMI_QUERY], capture_output=True, text=True,
                         check=True).stdout.split()
    return dict(zip(FIELDS, (int(x) for x in out)))


def u16(ec, addr):
    """Little-endian 16-bit read, the width the battery fields use."""
    return ec.read(addr) | (ec.read(addr + 1) << 8)


def main():
    rows = []
    with Ec() as ec:
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
    if len(ec_seen) < 3:
        print("INCONCLUSIVE: the voltage barely moved, so a match proves little."
              " Re-run under load, or while charging.")
        return 2
    print(f"EC 0x04A6/7 (BAT_CYCLE_COUNT, registers.yaml confirmed-working) = "
          f"{rows[0]['cycles']}")
    print(f"EC 0x043E/0x044F (CPU/GPU temp, confirmed-working) = "
          f"{rows[-1]['cpu']} / {rows[-1]['gpu']} C")
    # One stray mismatch is expected whenever the driver's cache is refreshed
    # between our two reads; a read path that were not the EC would match ~never.
    return 0 if matched >= SAMPLES - 2 else 1


if __name__ == "__main__":
    sys.exit(main())
