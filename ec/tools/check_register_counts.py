#!/usr/bin/env python3
"""Recompute every reference count in ec/annotations/registers.yaml from the
firmware image and fail on anything that doesn't match.

The point is that a reader does not have to trust the numbers in the YAML,
or the audit table beside it (ec/annotations/static-refs-audit.md). Three
things are checked per address:

  * `static_refs` still equals the file-wide `MOV DPTR,#addr` site count
    (what scan_refs.py reports),
  * `static_refs_main_ec` equals the sites inside the EC firmware itself
    (common area + CODE banks), and `static_refs_pd_image` the sites inside
    the ITE8850-PD image at file 0x20000 -- the split that #21 showed a
    file-wide total silently hides,
  * both split keys are *present*. A missing key is an error, not a zero:
    "audited, no PD contamination" and "never audited" have to stay
    distinguishable from the file, which is why entries record explicit
    zeroes.

This says nothing about whether a status is right. It says the numbers a
status was argued from are the numbers the image actually contains. The
indirect-addressing blind spot (docs/findings.md 4c) applies here exactly
as it does to the tools this builds on: a verified 0 means "not found by
this method", never "absent".

Usage:
    python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
"""
import argparse
import os
import sys

import yaml

from trace_xdata_refs import PD_MARKER, region_of, sites_for

# The EC firmware proper, as opposed to the PD image sharing the dump.
# Names come from trace_xdata_refs.REGIONS, so re-deriving that map with
# find_banks.py against a different dump carries through to here.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")
PD_REGION = "pd-image"

DEFAULT_YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            os.pardir, "annotations", "registers.yaml")

SPLIT_KEYS = ("static_refs_main_ec", "static_refs_pd_image")


def counts_for(d: bytes, addr: int, pd_verified: bool):
    """(file-wide, main-EC, PD-image) site counts for one address."""
    total = main = pd = 0
    for o in sites_for(d, addr):
        total += 1
        name = region_of(o, pd_verified)[0]
        if name in MAIN_EC_REGIONS:
            main += 1
        elif name == PD_REGION:
            pd += 1
    return total, main, pd


def as_list(value, n: int):
    """Normalise a scalar-or-list YAML value to one element per address."""
    if isinstance(value, list):
        return value
    return [value] * n


def check(d: bytes, regs, pd_verified: bool) -> int:
    problems = 0
    for r in regs:
        name = r.get("name", "?")
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        missing = [k for k in SPLIT_KEYS if k not in r]
        if missing:
            print(f"{name}: not audited -- missing {', '.join(missing)}",
                  file=sys.stderr)
            problems += 1
            continue
        recorded = {k: as_list(r[k], len(addrs)) for k in SPLIT_KEYS}
        recorded["static_refs"] = as_list(r.get("static_refs"), len(addrs))
        ragged = [k for k, v in recorded.items() if len(v) != len(addrs)]
        if ragged:
            for k in ragged:
                print(f"{name}: {k} has {len(recorded[k])} value(s) for "
                      f"{len(addrs)} address(es)", file=sys.stderr)
            problems += len(ragged)
            continue
        for i, addr in enumerate(addrs):
            total, main, pd = counts_for(d, addr, pd_verified)
            for key, measured in (("static_refs", total),
                                  ("static_refs_main_ec", main),
                                  ("static_refs_pd_image", pd)):
                if recorded[key][i] != measured:
                    print(f"{name} 0x{addr:04X}: {key} says "
                          f"{recorded[key][i]}, image has {measured}",
                          file=sys.stderr)
                    problems += 1
            if main + pd != total:
                # Sites in the erased regions would land here; the image map
                # would be wrong, not the YAML.
                print(f"{name} 0x{addr:04X}: {main} + {pd} sites do not add "
                      f"up to {total} -- some site is outside the mapped "
                      "regions, re-derive them with find_banks.py",
                      file=sys.stderr)
                problems += 1
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--registers", default=DEFAULT_YAML,
                    help="registers.yaml to check (default: the one beside this tool)")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    with open(args.registers) as f:
        regs = yaml.safe_load(f)["registers"]

    problems = check(d, regs, pd_verified)
    addrs = sum(len(r["addr"]) if isinstance(r["addr"], list) else 1 for r in regs)
    if problems:
        print(f"{problems} problem(s) across {len(regs)} entries / {addrs} addresses",
              file=sys.stderr)
        return 1
    print(f"{len(regs)} entries / {addrs} addresses: every static_refs, "
          "static_refs_main_ec and static_refs_pd_image reproduced from "
          f"{args.firmware}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
