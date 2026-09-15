#!/usr/bin/env python3
"""Re-derive the whole reference table for registers.yaml in one pass: the
per-image count split *and* the access direction of every site behind it.

check_register_counts.py answers "are the three recorded counts still the
counts in the image". This answers the question one level down, which a
count cannot: *what do those sites do*. Two different things inflate a
`MOV DPTR,#imm16` total and neither is a register access --

  * the site builds a **CODE** pointer (`movc a,@a+dptr`, `jmp @a+dptr`)
    into a string or jump table, which says nothing about a register of
    that number (ec/annotations/ec-0x07d0-sites.md 5), and
  * the site hands DPTR to a subroutine, where the direction is not
    resolvable at the site at all.

Both are reported as themselves here rather than as "no movx", so that an
address whose population is dominated by them is visible instead of
looking like an ordinary referenced register.

The classification is trace_xdata_refs.classify() over trace_xdata_refs.walk(),
so it inherits every limit of that walk: a linear best-effort decode, not a
disassembler, over a window of 8 instructions that stops at the first
control-flow instruction. Indirect/pointer XDATA access is invisible to the
site scan underneath it, so a `0` anywhere in this table means "not found by
this method", never "absent" -- 0x07B9 is the standing counter-example.
Nothing here is measured on hardware: a `write` class is not evidence that
the EC acts on the value, only that an instruction stores to the address.

The table reconciles itself twice per address -- the class buckets have to
sum to the site count, and main + PD to the file-wide total -- and exits
non-zero if either fails, so a silently dropped site is a failure rather
than a quieter table.

Usage:
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --csv > sites.csv
"""
import argparse
import collections
import csv
import sys

import yaml

from check_register_counts import DEFAULT_YAML, counts_for
from trace_xdata_refs import (PD_MARKER, classify, mnemonic, region_of,
                              runtime_addr, sites_for, walk)

# Bucket label -> markdown column header. Order is the table's column order,
# and the labels are what --csv writes, so the two stay the same vocabulary.
CLASSES = (
    ("read", "read"),
    ("write", "write"),
    ("read+write", "r+w"),
    ("movc (CODE pointer)", "movc"),
    ("jmp @a+dptr", "jmp"),
    ("handed to lcall/ljmp (unresolved)", "handoff"),
    ("no movx in window", "none"),
)


def bucket(access: str) -> str:
    """Map one classify() string onto one of CLASSES."""
    if access.startswith("DPTR handed"):
        return "handed to lcall/ljmp (unresolved)"
    if access.startswith("movc"):
        return "movc (CODE pointer)"
    if access.startswith("jmp"):
        return "jmp @a+dptr"
    read, write = "read" in access, "write" in access
    if read and write:
        return "read+write"
    if read:
        return "read"
    if write:
        return "write"
    return "no movx in window"


def addresses(regs):
    """(name, addr) for every address in registers.yaml, file order."""
    for r in regs:
        name = r.get("name", "?")
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        for addr in addrs:
            yield name, addr


def row_for(d: bytes, addr: int, pd_verified: bool):
    """(total, main, pd, {bucket: count}) for one address."""
    total, main, pd = counts_for(d, addr, pd_verified)
    hist = collections.Counter()
    for o in sites_for(d, addr):
        hist[bucket(classify(walk(d, o)))] += 1
    return total, main, pd, hist


def reconcile(name: str, addr: int, total: int, main: int, pd: int, hist) -> int:
    problems = 0
    classified = sum(hist.values())
    if classified != total:
        print(f"{name} 0x{addr:04X}: {classified} site(s) classified, "
              f"{total} found -- a site was dropped between sites_for() and "
              "classify()", file=sys.stderr)
        problems += 1
    if main + pd != total:
        # Same failure check_register_counts.py makes, for the same reason:
        # a site outside the mapped regions means the image map is wrong.
        print(f"{name} 0x{addr:04X}: {main} + {pd} sites do not add up to "
              f"{total} -- some site is outside the mapped regions, "
              "re-derive them with find_banks.py", file=sys.stderr)
        problems += 1
    unknown = set(hist) - {label for label, _ in CLASSES}
    if unknown:
        print(f"{name} 0x{addr:04X}: unbucketed class(es) {sorted(unknown)} -- "
              "classify() gained a verdict bucket() does not know",
              file=sys.stderr)
        problems += 1
    return problems


def write_markdown(d: bytes, regs, pd_verified: bool) -> int:
    problems = 0
    header = ["addr", "register", "total", "main EC", "PD"]
    header += [short for _, short in CLASSES]
    align = ["---", "---"] + ["---:"] * (len(header) - 2)
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(align) + "|")
    for name, addr in addresses(regs):
        total, main, pd, hist = row_for(d, addr, pd_verified)
        problems += reconcile(name, addr, total, main, pd, hist)
        # The parenthetical half of a name is commentary ("(Windows-only
        # address, ...)"), and one of them is longer than the rest of the
        # row put together; --csv keeps the name verbatim for grepping.
        short_name = name.split(" (")[0]
        cells = [f"`0x{addr:04X}`", f"`{short_name}`", str(total), str(main), str(pd)]
        cells += [str(hist.get(label, 0)) for label, _ in CLASSES]
        print("| " + " | ".join(cells) + " |")
    return problems


def write_csv(d: bytes, regs, pd_verified: bool) -> int:
    """One row per site. The markdown table is a group-by over this, so a
    reader can re-derive it without re-running anything."""
    problems = 0
    w = csv.writer(sys.stdout)
    w.writerow(["addr", "register", "file_offset", "region", "runtime",
                "class", "window"])
    for name, addr in addresses(regs):
        total, main, pd, hist = row_for(d, addr, pd_verified)
        problems += reconcile(name, addr, total, main, pd, hist)
        for o in sites_for(d, addr):
            region = region_of(o, pd_verified)[0]
            rt = runtime_addr(o, pd_verified)
            insns = walk(d, o)
            w.writerow([f"0x{addr:04X}", name, f"0x{o:05X}", region,
                        f"0x{rt:04X}" if rt is not None else "",
                        bucket(classify(insns)),
                        " ; ".join(" ".join(mn.split()) for _, _, mn in insns[1:])])
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--registers", default=DEFAULT_YAML,
                    help="registers.yaml to tabulate (default: the one beside this tool)")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per site on stdout instead of the markdown table")
    ap.add_argument("--markdown", action="store_true",
                    help="markdown table (the default; accepted so a pasted command can be explicit)")
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

    problems = (write_csv if args.csv else write_markdown)(d, regs, pd_verified)
    addrs = sum(1 for _ in addresses(regs))
    if problems:
        print(f"{problems} reconciliation problem(s) across {len(regs)} entries "
              f"/ {addrs} addresses", file=sys.stderr)
        return 1
    # stderr, so --csv output stays a clean CSV when redirected; flushed
    # first so a console transcript keeps the summary under the table.
    sys.stdout.flush()
    print(f"{len(regs)} entries / {addrs} addresses: class buckets sum to the "
          "site count and main + PD to the file-wide total for every address",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
