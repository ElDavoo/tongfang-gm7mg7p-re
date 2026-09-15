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

`--callee-depth 1` resolves the handoff bucket one level down, by decoding
the called routine's own entry point the way ec-0x07d0-sites.md 3 and
pd-xdata-overlap.md 3 did by hand for 0x07D0 and 0x04A6. It inherits every
limit above *twice over*, once for the site's walk and once for the callee's:
a callee that hands DPTR on again, ends its window at a branch, or is not
reachable from the calling site's region stays `handoff->unresolved`, which
is a verdict of this method and not a statement that the callee does nothing.

Usage:
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --csv > sites.csv
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1
"""
import argparse
import collections
import csv
import sys

import yaml

from check_register_counts import DEFAULT_YAML, counts_for
from trace_xdata_refs import (PD_MARKER, call_target, classify, mnemonic,
                              offset_for_runtime, region_of, runtime_addr,
                              sites_for, walk)

HANDOFF = "handed to lcall/ljmp (unresolved)"

# Bucket label -> markdown column header. Order is the table's column order,
# and the labels are what --csv writes, so the two stay the same vocabulary.
CLASSES = (
    ("read", "read"),
    ("write", "write"),
    ("read+write", "r+w"),
    ("movc (CODE pointer)", "movc"),
    ("jmp @a+dptr", "jmp"),
    (HANDOFF, "handoff"),
    ("no movx in window", "none"),
)

# What the handoff column becomes at --callee-depth 1. The unresolved bucket
# keeps the depth-0 label: it is the same verdict, reached one level further
# in, so nothing has to special-case it.
HANDOFF_CLASSES = (
    ("handed to lcall/ljmp -> callee reads", "handoff->read"),
    ("handed to lcall/ljmp -> callee writes", "handoff->write"),
    ("handed to lcall/ljmp -> callee reads+writes", "handoff->r+w"),
    (HANDOFF, "handoff->unresolved"),
)


def classes_for(callee_depth: int):
    """Column order for a depth. At depth 1 the single handoff column is
    replaced in place by the four it resolves into, so the two modes never
    both describe the same site and depth 0 stays byte-identical to before."""
    if not callee_depth:
        return CLASSES
    out = []
    for label, short in CLASSES:
        out.extend(HANDOFF_CLASSES if label == HANDOFF else [(label, short)])
    return tuple(out)


def bucket(access: str) -> str:
    """Map one classify() string onto one of CLASSES."""
    if access.startswith("DPTR handed"):
        return HANDOFF
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


def resolve_handoff(d: bytes, off: int, insns, pd_verified: bool):
    """(bucket, callee runtime, callee window) for one handoff site.

    The callee's entry point is decoded with the same walk, classified with
    skip=0 because the instruction at the entry point is itself the access.
    Anything that is not a plain movx direction -- another handoff, a movc, a
    walk that ends at a branch -- stays in the unresolved bucket with the
    callee's own verdict as the window, so the reason is on the row."""
    # walk() stops at the first control-flow instruction, so the lcall/ljmp
    # classify() saw is the last one it decoded.
    target = call_target(insns[-1][1])
    if target is None:
        return HANDOFF, None, "handoff is not an lcall/ljmp"
    region = region_of(off, pd_verified)[0]
    coff = offset_for_runtime(target, region)
    if coff is None:
        return HANDOFF, target, f"callee not reachable from region {region}"
    cinsns = walk(d, coff)
    access = classify(cinsns, skip=0)
    window = " ; ".join(" ".join(mn.split()) for _, _, mn in cinsns)
    read, write = "read" in access, "write" in access
    if read and write:
        return "handed to lcall/ljmp -> callee reads+writes", target, window
    if read:
        return "handed to lcall/ljmp -> callee reads", target, window
    if write:
        return "handed to lcall/ljmp -> callee writes", target, window
    return HANDOFF, target, f"{access} | {window}"


def site_rows(d: bytes, addr: int, pd_verified: bool, callee_depth: int):
    """One (offset, region, runtime, bucket, callee, callee_window) per site.
    The markdown table is a group-by over these, so both outputs classify the
    same sites the same way."""
    for o in sites_for(d, addr):
        insns = walk(d, o)
        label = bucket(classify(insns))
        callee = window = None
        if callee_depth and label == HANDOFF:
            label, callee, window = resolve_handoff(d, o, insns, pd_verified)
        yield (o, region_of(o, pd_verified)[0], runtime_addr(o, pd_verified),
               label, callee, window,
               " ; ".join(" ".join(mn.split()) for _, _, mn in insns[1:]))


def addresses(regs):
    """(name, addr) for every address in registers.yaml, file order."""
    for r in regs:
        name = r.get("name", "?")
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        for addr in addrs:
            yield name, addr


def row_for(d: bytes, addr: int, pd_verified: bool, rows):
    """(total, main, pd, {bucket: count}) for one address."""
    total, main, pd = counts_for(d, addr, pd_verified)
    hist = collections.Counter(r[3] for r in rows)
    return total, main, pd, hist


def reconcile(name: str, addr: int, total: int, main: int, pd: int, hist,
              classes) -> int:
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
    unknown = set(hist) - {label for label, _ in classes}
    if unknown:
        print(f"{name} 0x{addr:04X}: unbucketed class(es) {sorted(unknown)} -- "
              "classify() gained a verdict bucket() does not know",
              file=sys.stderr)
        problems += 1
    return problems


def write_markdown(d: bytes, regs, pd_verified: bool, callee_depth: int) -> int:
    problems = 0
    classes = classes_for(callee_depth)
    header = ["addr", "register", "total", "main EC", "PD"]
    header += [short for _, short in classes]
    align = ["---", "---"] + ["---:"] * (len(header) - 2)
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(align) + "|")
    for name, addr in addresses(regs):
        rows = list(site_rows(d, addr, pd_verified, callee_depth))
        total, main, pd, hist = row_for(d, addr, pd_verified, rows)
        problems += reconcile(name, addr, total, main, pd, hist, classes)
        # The parenthetical half of a name is commentary ("(Windows-only
        # address, ...)"), and one of them is longer than the rest of the
        # row put together; --csv keeps the name verbatim for grepping.
        short_name = name.split(" (")[0]
        cells = [f"`0x{addr:04X}`", f"`{short_name}`", str(total), str(main), str(pd)]
        cells += [str(hist.get(label, 0)) for label, _ in classes]
        print("| " + " | ".join(cells) + " |")
    return problems


def write_csv(d: bytes, regs, pd_verified: bool, callee_depth: int) -> int:
    """One row per site. The markdown table is a group-by over this, so a
    reader can re-derive it without re-running anything. At depth 1 the two
    extra columns carry the callee the class came from, so a row's verdict
    can be checked against an independent disassembler."""
    problems = 0
    classes = classes_for(callee_depth)
    w = csv.writer(sys.stdout)
    head = ["addr", "register", "file_offset", "region", "runtime", "class",
            "window"]
    if callee_depth:
        head += ["callee", "callee_window"]
    w.writerow(head)
    for name, addr in addresses(regs):
        rows = list(site_rows(d, addr, pd_verified, callee_depth))
        total, main, pd, hist = row_for(d, addr, pd_verified, rows)
        problems += reconcile(name, addr, total, main, pd, hist, classes)
        for o, region, rt, label, callee, callee_window, window in rows:
            cells = [f"0x{addr:04X}", name, f"0x{o:05X}", region,
                     f"0x{rt:04X}" if rt is not None else "", label, window]
            if callee_depth:
                cells += [f"0x{callee:04X}" if callee is not None else "",
                          callee_window or ""]
            w.writerow(cells)
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
    ap.add_argument("--callee-depth", type=int, choices=(0, 1), default=0,
                    help="1: split the handoff bucket by what the called routine's "
                         "own entry point does with DPTR (default 0, site only)")
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

    problems = (write_csv if args.csv else write_markdown)(
        d, regs, pd_verified, args.callee_depth)
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
