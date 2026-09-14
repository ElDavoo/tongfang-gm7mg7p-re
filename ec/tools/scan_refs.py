#!/usr/bin/env python3
"""Scan the ITE EC firmware image for direct XDATA references to a set of
16-bit addresses.

Method: on 8051, a direct XDATA access is preceded by `MOV DPTR,#imm16`
(opcode 0x90 hi lo). Counting occurrences of `90 <hi> <lo>` for a given
address is a cheap, high-precision (but not complete-recall) way to find
which EC registers a given firmware image actually implements.

Validated methodology (see docs/findings.md "Static-scan validation"):
against 20 registers whose behaviour was independently confirmed on live
hardware (15 working, 5 confirmed non-functional), this scan predicted
all 20 correctly. It is NOT proof of absence: indirect addressing (a
pointer built in Rn/Rm, common in Keil-generated code for tight loops
and switch-derived tables) is invisible to this scan. The 0x07B0-0x07BE
block is a documented blind spot -- see docs/findings.md "Retraction".

Usage:
    python3 scan_refs.py firmware.bin 0x07A6 0x07B9 0x0768
    python3 scan_refs.py firmware.bin --file registers.txt
    python3 scan_refs.py firmware.bin --all-0700   # histogram of 0x0700-0x07FF
"""
import argparse
import collections
import sys


def scan(data: bytes) -> collections.Counter:
    hits = collections.Counter()
    for i in range(len(data) - 2):
        if data[i] == 0x90:
            hits[(data[i + 1] << 8) | data[i + 2]] += 1
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("addrs", nargs="*", help="hex addresses, e.g. 0x07A6")
    ap.add_argument("--file", help="file with one hex address (and optional label) per line")
    ap.add_argument("--all-0700", action="store_true", help="dump full histogram for 0x0700-0x07FF")
    args = ap.parse_args()

    data = open(args.firmware, "rb").read()
    hits = scan(data)

    if args.all_0700:
        for a in range(0x0700, 0x0800):
            if hits.get(a):
                print(f"0x{a:04X} : {hits[a]:>4} refs")
        return

    targets = []
    for a in args.addrs:
        targets.append((a, int(a, 16)))
    if args.file:
        for line in open(args.file):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            targets.append((parts[-1], int(parts[0], 16)))

    if not targets:
        ap.error("give addresses as args, --file, or --all-0700")

    for label, a in targets:
        c = hits.get(a, 0)
        verdict = "referenced" if c else "ABSENT (see blind-spot caveat above)"
        print(f"0x{a:04X}  refs={c:<5} {verdict}   {label}")


if __name__ == "__main__":
    sys.exit(main())
