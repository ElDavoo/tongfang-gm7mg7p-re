#!/usr/bin/env python3
r"""Issue #99: write only the power-mode byte 0x0751 and watch whether the EC
moves anything else on its own.

The vendor service writes a whole bundle per power mode (0x0751, PL1/PL2/PL4,
the fan table, GPU bytes; see windows/vendor-ec-map.md "Power modes"). This
isolates the mode byte: it reads a fixed watch-set plus the fan table
(0x0F00-0x0F5F) every 0.3 s, writes 0x0751 to one target value, holds, then
restores the original. If the EC derived the PLs or the fan table from the
mode byte, they would move here with nothing else writing them.

Never touches the fan-tach bytes (0x0460-0x046F; see #94). Values are limited
to the three the vendor itself writes: 0xA0 Office, 0x00 Gaming, 0x10 Turbo
(a no-op if that is already the mode). Restores 0x0751 in a finally block.

Run elevated, next to ecrw.py. Needs the vendor's ACPI driver present.

Usage:
  manual_fan_ctrl_probe.py 0xA0 [hold_seconds]
"""
import sys
import time

from ecrw import Ec

WATCH = [0x0751, 0x0783, 0x0784, 0x0785, 0x0786, 0x0787,
         0x07C5, 0x07C6, 0x075B, 0x075C, 0x0743, 0x0744, 0x0745, 0x0746]
FANTBL = list(range(0x0F00, 0x0F60))
ALL = WATCH + FANTBL
ALLOWED = {0x00, 0x10, 0xA0}


def snap(ec):
    return {a: ec.read(a) for a in ALL}


def diff(base, cur):
    return [(a, base[a], cur[a]) for a in ALL if base[a] != cur[a]]


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: manual_fan_ctrl_probe.py 0xA0|0x00|0x10 [hold_seconds]")
    target = int(sys.argv[1], 16)
    if target not in ALLOWED:
        sys.exit(f"value 0x{target:02X} not in the vendor set {{0x00,0x10,0xA0}}")
    hold = float(sys.argv[2]) if len(sys.argv) > 2 else 20.0
    ec = Ec()
    orig = ec.read(0x0751)
    print(f"0x0751 currently 0x{orig:02X}; writing 0x{target:02X}, holding {hold:.0f}s")
    base = snap(ec)
    moved = {}
    try:
        ec.write(0x0751, target)
        t0 = time.time()
        while time.time() - t0 < hold:
            cur = snap(ec)
            for a, o, n in diff(base, cur):
                print(f"    +{time.time()-t0:4.1f}s  0x{a:04X}: 0x{o:02X} -> 0x{n:02X}")
                moved[a] = (base[a], n)
            base = cur
            time.sleep(0.3)
    finally:
        ec.write(0x0751, orig)
        time.sleep(0.4)
        print(f"restored 0x0751 -> 0x{ec.read(0x0751):02X}")
    print("SUMMARY: addresses that moved while only 0x0751 was written:")
    if not moved:
        print("  none (0x0751 changed nothing else on its own)")
    for a, (o, n) in sorted(moved.items()):
        tag = " (fan PWM; thermal, cf. a no-op control write)" if a in (0x075B, 0x075C) else ""
        print(f"  0x{a:04X}: 0x{o:02X} -> ... (last 0x{n:02X}){tag}")


if __name__ == "__main__":
    main()
