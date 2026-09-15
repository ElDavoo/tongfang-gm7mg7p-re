#!/usr/bin/env python3
"""Count direct XDATA reference sites per image for *every* address in a
span, in one pass over the dump.

trace_xdata_refs.py answers "where are the sites for this address, and what
do they do". It rescans all 256 KiB per address, so asking it about a
1024-address span is impractically slow. This tool answers the coarser
question that a span needs -- how many sites each address has in each image
-- and answers it for the whole span at once, so the shape of one image's
usage across a range can be compared against the other's.

That comparison is what it exists for: ec/annotations/pd-xdata-overlap.md
uses it to ask whether the ITE8850-PD image's XDATA usage over 0x0400-0x07FF
looks like a map it allocated for itself, or like it clusters where the EC's
registers happen to sit.

The region map, the PD image's identifying marker and the "which image is
this offset in" rule all come from trace_xdata_refs.py; nothing about the
dump's layout is re-derived here. The counting is the same `90 hi lo` byte
pattern scan_refs.py uses, with the same limits: it is not instruction
aligned, so a hit can be an operand byte or table data rather than a real
`MOV DPTR,#imm16`, and indirect/pointer XDATA access is invisible to it. A
zero therefore means "not found by this method", never "absent" -- see the
0x07B9 blind spot in docs/findings.md 4c. Counts here are expected to equal
`trace_xdata_refs.py --counts-only` for any address; they are a faster way
to get the same number, not a second opinion.

Read-only: it opens the firmware image for reading and writes nothing.

Usage:
    python3 xdata_span_survey.py ../firmware/GMxMGxx_11.800 0x0400 0x07FF
    python3 xdata_span_survey.py ../firmware/GMxMGxx_11.800 0x0400 0x07FF --csv
    python3 xdata_span_survey.py ../firmware/GMxMGxx_11.800 0x0400 0x07FF --page 0x40
"""
import argparse
import collections
import csv
import sys

from trace_xdata_refs import PD_MARKER, REGIONS, region_of

# Region names in the order the tables print them, main EC first. Taken from
# REGIONS rather than spelled out, so a re-derived image map carries through.
IMAGES = [name for name, *_ in REGIONS if name not in ("erased",)]
MAIN_EC_IMAGES = ("common", "bank0", "bank1")
PD_IMAGE = "pd-image"

MOV_DPTR = 0x90


def survey(d: bytes, lo: int, hi: int, pd_verified: bool):
    """addr -> Counter of region name -> site count, for lo <= addr <= hi."""
    counts = collections.defaultdict(collections.Counter)
    for i in range(len(d) - 2):
        if d[i] != MOV_DPTR:
            continue
        addr = (d[i + 1] << 8) | d[i + 2]
        if lo <= addr <= hi:
            counts[addr][region_of(i, pd_verified)[0]] += 1
    return counts


def totals(counts, names):
    return sum(counts[n] for n in names)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("lo", help="first address of the span, e.g. 0x0400")
    ap.add_argument("hi", help="last address of the span, inclusive, e.g. 0x07FF")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per address on stdout instead of the table")
    ap.add_argument("--page", type=lambda s: int(s, 0), metavar="N",
                    help="also bucket the span into blocks of N addresses")
    args = ap.parse_args()

    lo, hi = int(args.lo, 16), int(args.hi, 16)
    if lo > hi:
        ap.error("lo must not be above hi")

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so that --csv output stays a clean CSV when redirected.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF will be reported as region 'unknown'\n",
              file=sys.stderr)

    counts = survey(d, lo, hi, pd_verified)

    if args.csv:
        w = csv.writer(sys.stdout)
        w.writerow(["addr", "total", "main_ec", "pd_image"] + IMAGES)
        for addr in range(lo, hi + 1):
            c = counts[addr]
            w.writerow([f"0x{addr:04X}", sum(c.values()),
                        totals(c, MAIN_EC_IMAGES), c[PD_IMAGE]]
                       + [c[n] for n in IMAGES])
        return

    span_ec = sum(totals(counts[a], MAIN_EC_IMAGES) for a in range(lo, hi + 1))
    span_pd = sum(counts[a][PD_IMAGE] for a in range(lo, hi + 1))
    touched_ec = sum(1 for a in range(lo, hi + 1) if totals(counts[a], MAIN_EC_IMAGES))
    touched_pd = sum(1 for a in range(lo, hi + 1) if counts[a][PD_IMAGE])
    both = sum(1 for a in range(lo, hi + 1)
               if totals(counts[a], MAIN_EC_IMAGES) and counts[a][PD_IMAGE])
    print(f"0x{lo:04X}-0x{hi:04X}: {hi - lo + 1} addresses")
    print(f"  main EC : {span_ec:>6} sites over {touched_ec} addresses")
    print(f"  PD image: {span_pd:>6} sites over {touched_pd} addresses")
    print(f"  both    : {both} address(es) with sites in each image")

    if args.page:
        print()
        print(f"  {'block':<17} {'main EC':>8} {'PD':>8}")
        for base in range(lo, hi + 1, args.page):
            top = min(base + args.page - 1, hi)
            ec = sum(totals(counts[a], MAIN_EC_IMAGES) for a in range(base, top + 1))
            pd = sum(counts[a][PD_IMAGE] for a in range(base, top + 1))
            print(f"  0x{base:04X}-0x{top:04X}   {ec:>8} {pd:>8}")


if __name__ == "__main__":
    sys.exit(main())
