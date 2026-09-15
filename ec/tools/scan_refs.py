#!/usr/bin/env python3
"""Scan the ITE EC firmware image for direct XDATA references to a set of
16-bit addresses.

Method: on 8051, a direct XDATA access is preceded by `MOV DPTR,#imm16`
(opcode 0x90 hi lo). Counting occurrences of `90 <hi> <lo>` for a given
address is a cheap, high-precision (but not complete-recall) way to find
which EC registers a given firmware image actually implements.

Every count is reported per image, never as a bare file-wide total: the
256 KiB dump holds two unrelated 8051 programs (the EC firmware and the
ITE8850-PD image at file 0x20000), and a `MOV DPTR,#0x07E2` in the PD
image is not a reference to the EC register of that number. A file-wide
total adds the two together, which is how `LIGHTBAR_BAT_*` came to be
recorded as present in EC firmware that references it zero times -- see
docs/findings.md 3a. The regions come from trace_xdata_refs.py, which is
still the tool to reach for when the sites themselves matter.

Validated methodology (see docs/findings.md "Static-scan validation"):
against 20 registers whose behaviour was independently confirmed on live
hardware (15 working, 5 confirmed non-functional), this scan predicted
all 20 correctly. It is NOT proof of absence: indirect addressing (a
pointer built in Rn/Rm, common in Keil-generated code for tight loops
and switch-derived tables) is invisible to this scan. The 0x07B0-0x07BE
block is a documented blind spot -- see docs/findings.md "Retraction".
That applies to the split too: `ec=0` means "not found in the EC image by
this method", never "absent".

Usage:
    python3 scan_refs.py firmware.bin 0x07A6 0x07B9 0x0768
    python3 scan_refs.py firmware.bin --file registers.txt
    python3 scan_refs.py firmware.bin --all-0700   # histogram of 0x0700-0x07FF
"""
import argparse
import collections
import sys

from trace_xdata_refs import PD_MARKER, region_of

# Which trace_xdata_refs.py regions are the EC firmware itself, as opposed
# to the PD image sharing the dump. Re-deriving that map (find_banks.py)
# carries through to here.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")
PD_REGION = "pd-image"

CAVEAT = (
    "This dump holds two 8051 programs; ec= counts sites in the EC firmware\n"
    "(common area + CODE banks), pd= sites in the separate ITE8850-PD image,\n"
    "whose XDATA map is unrelated. A pd-only count is not EC-side evidence.\n"
    "A zero means 'not found by this scan', never 'absent' -- see the\n"
    "indirect-addressing blind spot in docs/findings.md.\n"
)


def scan(data: bytes, pd_verified: bool = True):
    """addr -> [file-wide, EC-image, PD-image] direct reference counts."""
    hits = collections.defaultdict(lambda: [0, 0, 0])
    for i in range(len(data) - 2):
        if data[i] == 0x90:
            counts = hits[(data[i + 1] << 8) | data[i + 2]]
            counts[0] += 1
            name = region_of(i, pd_verified)[0]
            if name in MAIN_EC_REGIONS:
                counts[1] += 1
            elif name == PD_REGION:
                counts[2] += 1
    return hits


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("addrs", nargs="*", help="hex addresses, e.g. 0x07A6")
    ap.add_argument("--file", help="file with one hex address (and optional label) per line")
    ap.add_argument("--all-0700", action="store_true", help="dump full histogram for 0x0700-0x07FF")
    args = ap.parse_args()

    data = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = data[off:off + len(magic)] == magic
    hits = scan(data, pd_verified)

    print(CAVEAT)
    if not pd_verified:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- sites in "
              "0x20000-0x2FFFF belong to an unidentified region and are counted\n"
              "in neither ec= nor pd=\n")

    if args.all_0700:
        for a in range(0x0700, 0x0800):
            if hits.get(a):
                total, ec, pd = hits[a]
                print(f"0x{a:04X} : {total:>4} refs   ec={ec:<4} pd={pd}")
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
        total, ec, pd = hits.get(a, [0, 0, 0])
        if ec:
            verdict = "referenced"
        elif pd:
            verdict = "referenced in the PD image ONLY, not by the EC"
        else:
            verdict = "ABSENT (see blind-spot caveat above)"
        print(f"0x{a:04X}  refs={total:<5} ec={ec:<5} pd={pd:<5} {verdict}   {label}")


if __name__ == "__main__":
    sys.exit(main())
