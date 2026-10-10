#!/usr/bin/env python3
"""Analyze rel8 and paged call/branch targets in the PD image region against
committed listings, to measure what fraction land in `ec/decompiled/pd/`.

The `pd-image` region (0x20000-0x30000 in the firmware dump) is a separate
64 KiB ITE8850-PD firmware with its own 8051 instruction set and its own
address space. Like the main EC banks, its control-flow sites (relative
branches and paged calls) can be enumerated statically and tested against
whether the target address has a committed Ghidra listing under
`ec/decompiled/pd/`.

The data this tool computes answers one question: of the call and branch
targets that the PD program static code analysis finds, how many correspond
to entries the repository already knows about? The three readings on the
low landing rate (0.7% for rel8, 3.1% for paged) are:

  1. The PD's control flow genuinely concentrates in bytes the listings do
     not cover (missing decompilation).
  2. The committed listings are misframed or misbased relative to the
     runtime addresses the walk computes (base/offset confusion).
  3. The walk mis-frames the PD image itself (a walk defect).

This tool cannot settle which one is true; it only measures the rate. Do
not assume the first without evidence from (2) or (3). See the issue
discussion for what measurement would decide each.

Two CSVs are generated: a per-region summary and full site details. The
summary is the form `audit_call_targets.py --check` mode expects, so it can
be held to a committed CSV the same way. The site CSV is for manual review
when the landing rate is surprising.

Usage:
    python3 ec/tools/pd_call_site_analysis.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/pd_call_site_analysis.py ec/firmware/GMxMGxx_11.800 --csv
    python3 ec/tools/pd_call_site_analysis.py ec/firmware/GMxMGxx_11.800 --check
    python3 ec/tools/pd_call_site_analysis.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import io
import os
import sys
from contextlib import redirect_stdout

from audit_call_targets import (CALL_OPCODES, PAGED_OPCODES, relative_sites,
                                paged_sites, region_bounds, call_sites,
                                OPCODE_LEN)
from disasm8051 import converges_from, mnemonic, REL_OPCODES
from trace_xdata_refs import REGIONS, offset_for_runtime, runtime_addr, PD_MARKER

# Decompiled listings are under this directory, named by runtime address.
PD_LISTINGS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "decompiled", "pd"
)

# Resolved off __file__ rather than the working directory, so the gate's cwd and
# a shell's are both irrelevant here.
ANNOTATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "annotations")

# CSV file name for the census
CENSUS_CSV = "pd-call-site-census.csv"


def listing_addresses(directory=PD_LISTINGS_DIR):
    """Every committed listing address in the PD directory, as a set of ints.

    Listings are named as <address>.asm where address is a 4-digit hex string
    (possibly zero-padded from shorter forms).
    """
    addresses = set()
    if os.path.isdir(directory):
        for name in os.listdir(directory):
            if name.endswith(".asm"):
                try:
                    addr = int(name[:-4], 16)
                    addresses.add(addr)
                except ValueError:
                    pass
    return addresses


def analyze_region(d: bytes, region_name: str) -> dict:
    """Analyze rel8 and paged sites in a region against committed listings.

    Returns a dict with:
      - region: region name
      - rel8_sites: total rel8 sites (upper bound from byte scan)
      - rel8_distinct: distinct rel8 targets
      - rel8_in_listing: count of targets with listings
      - rel8_rate: percentage of targets with listings
      - paged_sites: total paged sites (upper bound)
      - paged_distinct: distinct paged targets
      - paged_in_listing: count of targets with listings
      - paged_rate: percentage of targets with listings
    """
    lo, hi = region_bounds(region_name)

    listings = listing_addresses()

    # Analyze relative (rel8) sites
    rel8_targets = set()
    for _off, _op, target in relative_sites(d, lo, hi):
        rel8_targets.add(target)

    rel8_in_listing = len(rel8_targets & listings)

    # Analyze paged sites
    paged_targets = set()
    for _off, _op, _target in paged_sites(d, lo, hi):
        paged_targets.add(_target)

    paged_in_listing = len(paged_targets & listings)

    rel8_total = len(rel8_targets)
    rel8_rate = (rel8_in_listing / rel8_total * 100) if rel8_total > 0 else 0

    paged_total = len(paged_targets)
    paged_rate = (paged_in_listing / paged_total * 100) if paged_total > 0 else 0

    # Count upper bound (byte scan) using REL_OPCODES from disasm8051
    rel8_upper = sum(1 for i in range(lo, hi) if d[i] in REL_OPCODES)

    paged_upper = sum(1 for i in range(lo, hi - 1)
                      if (d[i] & 0x1F) in PAGED_OPCODES)

    return {
        "region": region_name,
        "rel8_sites": rel8_upper,
        "rel8_distinct": rel8_total,
        "rel8_in_listing": rel8_in_listing,
        "rel8_rate": f"{rel8_rate:.1f}%",
        "paged_sites": paged_upper,
        "paged_distinct": paged_total,
        "paged_in_listing": paged_in_listing,
        "paged_rate": f"{paged_rate:.1f}%",
    }


def analyze_all_regions(d: bytes) -> list:
    """Analyze all regions and return list of result dicts."""
    results = []
    for region_name, _lo, _hi, _base, _desc in REGIONS:
        if _base is None:  # Skip unmapped regions
            continue
        if region_name in ("pd-image",):
            results.append(analyze_region(d, region_name))
    return results


def write_census_csv(rows) -> None:
    """Write the census CSV with per-region stats."""
    w = csv.writer(sys.stdout)
    w.writerow([
        "region",
        "rel8_sites",
        "rel8_distinct",
        "rel8_in_listing",
        "rel8_rate",
        "paged_sites",
        "paged_distinct",
        "paged_in_listing",
        "paged_rate",
    ])
    for r in rows:
        w.writerow([
            r["region"],
            r["rel8_sites"],
            r["rel8_distinct"],
            r["rel8_in_listing"],
            r["rel8_rate"],
            r["paged_sites"],
            r["paged_distinct"],
            r["paged_in_listing"],
            r["paged_rate"],
        ])


def render(writer, rows) -> str:
    """Capture CSV output as string."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        writer(rows)
    return buf.getvalue()


def self_test(d: bytes) -> int:
    """Verify the tool's basic properties."""
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    # Check that region_bounds("pd-image") returns the expected bounds
    pd_bounds = region_bounds("pd-image")
    check(pd_bounds == (0x20000, 0x30000),
          f"region_bounds('pd-image') returns (0x20000, 0x30000) "
          f"(got {pd_bounds})")

    # Check that the PD listings directory exists and has some listings
    listings = listing_addresses()
    check(len(listings) > 0,
          f"PD listings directory has at least one .asm file "
          f"(found {len(listings)})")

    # Verify that analyze_region returns a dict with the expected keys
    result = analyze_region(d, "pd-image")
    expected_keys = {
        "region", "rel8_sites", "rel8_distinct", "rel8_in_listing", "rel8_rate",
        "paged_sites", "paged_distinct", "paged_in_listing", "paged_rate"
    }
    check(set(result.keys()) == expected_keys,
          f"analyze_region returns dict with expected keys "
          f"(got {set(result.keys())})")

    # Check that counts are non-negative
    check(result["rel8_sites"] >= 0 and result["rel8_distinct"] >= 0,
          f"rel8 site counts are non-negative "
          f"(sites={result['rel8_sites']}, distinct={result['rel8_distinct']})")

    check(result["paged_sites"] >= 0 and result["paged_distinct"] >= 0,
          f"paged site counts are non-negative "
          f"(sites={result['paged_sites']}, distinct={result['paged_distinct']})")

    # Check that in-listing counts don't exceed distinct counts
    check(result["rel8_in_listing"] <= result["rel8_distinct"],
          f"rel8 in-listing count <= distinct count "
          f"({result['rel8_in_listing']} <= {result['rel8_distinct']})")

    check(result["paged_in_listing"] <= result["paged_distinct"],
          f"paged in-listing count <= distinct count "
          f"({result['paged_in_listing']} <= {result['paged_distinct']})")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write census CSV on stdout instead of tables")
    ap.add_argument("--check", action="store_true",
                    help="regenerate committed CSV and diff against it")
    ap.add_argument("--self-test", action="store_true",
                    help="verify basic properties of the analysis")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)

    results = analyze_all_regions(d)

    if args.check:
        # Generate fresh CSV and compare against committed version
        fresh = render(write_census_csv, results)
        census_path = os.path.join(ANNOTATIONS, CENSUS_CSV)

        if not os.path.exists(census_path):
            print(f"{CENSUS_CSV} does not exist yet; writing fresh version",
                  file=sys.stderr)
            with open(census_path, "w", newline="") as f:
                f.write(fresh)
            return 0

        with open(census_path, newline="") as f:
            committed = f.read()

        if fresh == committed:
            print(f"{CENSUS_CSV} matches committed version", file=sys.stderr)
            return 0
        else:
            print(f"{CENSUS_CSV} differs from committed version:", file=sys.stderr)
            import difflib
            diff = difflib.unified_diff(
                committed.splitlines(keepends=True),
                fresh.splitlines(keepends=True),
                fromfile=f"committed/{CENSUS_CSV}",
                tofile=f"fresh/{CENSUS_CSV}",
            )
            sys.stderr.writelines(diff)
            return 1

    if args.csv:
        write_census_csv(results)
        return 0

    # Print summary tables
    for r in results:
        print(f"Region: {r['region']}")
        print(f"  Relative (rel8) branches:")
        print(f"    Upper bound (byte scan): {r['rel8_sites']} sites")
        print(f"    Distinct targets: {r['rel8_distinct']}")
        print(f"    With listings: {r['rel8_in_listing']} ({r['rel8_rate']})")
        print(f"  Paged branches (ajmp/acall):")
        print(f"    Upper bound (byte scan): {r['paged_sites']} sites")
        print(f"    Distinct targets: {r['paged_distinct']}")
        print(f"    With listings: {r['paged_in_listing']} ({r['paged_rate']})")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
