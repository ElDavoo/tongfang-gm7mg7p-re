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

The `in_data_region` column labels how many of an address's sites fall inside
a span `annotations/data-regions.yaml` lists as table entries (issue #50). It
is a LABEL, not a filter: the counts are unchanged and no site is dropped,
because dropping the phantoms would make a future scan's zero look like
absence -- the docs/findings.md 4c failure this header already cites.
`in_data_region=0` means "no site falls in a listed region", never "no site
is a phantom", and a region not being listed is not a claim about its bytes
either.

Usage:
    python3 scan_refs.py firmware.bin 0x07A6 0x07B9 0x0768
    python3 scan_refs.py firmware.bin --file registers.txt
    python3 scan_refs.py firmware.bin --all-0700   # histogram of 0x0700-0x07FF
"""
import argparse
import collections
import sys

from data_regions import load as load_data_regions, region_at
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
    """addr -> [file-wide, EC-image, PD-image] direct reference counts.

    The sites themselves are kept alongside, because the data-region label is
    a property of a *site* and not of an address: the same register can be
    referenced from code and from a table. A fourth slot carries the count of
    that address's sites landing inside a listed region.
    """
    hits = collections.defaultdict(lambda: [0, 0, 0, []])
    for i in range(len(data) - 2):
        if data[i] == 0x90:
            counts = hits[(data[i + 1] << 8) | data[i + 2]]
            counts[0] += 1
            counts[3].append(i)
            name = region_of(i, pd_verified)[0]
            if name in MAIN_EC_REGIONS:
                counts[1] += 1
            elif name == PD_REGION:
                counts[2] += 1
    return hits


def sites_in_data_regions(sites, regions) -> int:
    """How many of `sites` fall inside a listed data region.

    A label, deliberately: the caller still counts every site. Labelling is
    the whole point of `annotations/data-regions.yaml` -- a site that is
    inside a table read one byte out of frame is a phantom, and a phantom that
    has been named is not rediscovered by the next scan.
    """
    return sum(1 for s in sites if region_at(regions, s) is not None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("addrs", nargs="*", help="hex addresses, e.g. 0x07A6")
    ap.add_argument("--file", help="file with one hex address (and optional label) per line")
    ap.add_argument("--all-0700", action="store_true", help="dump full histogram for 0x0700-0x07FF")
    args = ap.parse_args()

    data = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = data[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so `--all-0700` redirected to a file stays a parseable table,
        # and a non-zero exit rather than a count. Without the marker
        # `region_of()` has relabelled the whole 0x20000 band `unknown`, so
        # every site in it lands in neither `ec=` nor `pd=` while the file-wide
        # `refs=` still stands -- and the verdict below then reaches `ABSENT`
        # on an address this scan *found* seven sites for. The count was right
        # and the sentence after it was not, which is the docs/findings.md 4
        # retraction reached by a different route. `check_pd_marker_contract.py`
        # is the census of which contract each tool here implements.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- the "
              "0x20000-0x2FFFF region is unidentified, so its sites are "
              "counted in neither ec= nor pd=\n", file=sys.stderr)
        return 1
    hits = scan(data, pd_verified)
    regions = load_data_regions()

    print(CAVEAT)

    if args.all_0700:
        for a in range(0x0700, 0x0800):
            if hits.get(a):
                total, ec, pd, sites = hits[a]
                labelled = sites_in_data_regions(sites, regions)
                print(f"0x{a:04X} : {total:>4} refs   ec={ec:<4} pd={pd}"
                      f"   in_data_region={labelled}")
        return 0

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
        total, ec, pd, sites = hits.get(a, [0, 0, 0, []])
        if ec:
            verdict = "referenced"
        elif pd:
            verdict = "referenced in the PD image ONLY, not by the EC"
        else:
            verdict = "ABSENT (see blind-spot caveat above)"
        # Trailing, so the columns the cheap gate's smoke test greps for
        # (`refs=15`, `referenced`) are untouched by adding it.
        labelled = sites_in_data_regions(sites, regions)
        print(f"0x{a:04X}  refs={total:<5} ec={ec:<5} pd={pd:<5} {verdict}"
              f"   in_data_region={labelled}   {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
