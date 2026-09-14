#!/usr/bin/env python3
"""Locate and decode every direct XDATA reference site for a set of 16-bit
addresses, and say which firmware image inside the flash dump each site
belongs to.

scan_refs.py answers "how many `MOV DPTR,#addr` sites exist in this file".
This tool answers the two follow-up questions that count has to survive
before it means anything:

  1. *Which image is the site in?* The 256 KiB dump is not one program. It
     holds the main EC firmware (common area + CODE banks) and, at file
     offset 0x20000, a second, self-contained 8051 image that identifies
     itself as `ITE8850-PD` -- its own reset/interrupt vectors, its own
     64 KiB address space, therefore its own XDATA allocation. A `MOV
     DPTR,#0x07E2` in the PD image says nothing about what the main EC
     does with its 0x07E2, because they are not the same byte. A file-wide
     count silently adds the two together.
  2. *What does the site do?* Direction is taken from the opcodes that
     follow (0xE0 `movx a,@dptr` read, 0xF0 `movx @dptr,a` write, 0xA3
     `inc dptr` sequential walk into the following bytes). Where the site
     hands DPTR to a subroutine (`lcall`) instead, that is reported as
     exactly that -- unresolved -- not guessed at.

The decode is a linear best-effort walk, not a disassembler: it stops at
the first control-flow instruction and cannot follow branches (disasm8051.py
holds the opcode tables and says what else it cannot do). Treat the
mnemonics as a reading aid and confirm anything load-bearing with
`--r2-commands` output (or make_bank_image.py + r2 by hand). As with
scan_refs.py, indirect/pointer XDATA access is invisible here, so "0 sites
in image X" means "not found by this method", never "absent".

Usage:
    python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x07E2 0x07E3
    python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x07D0 --counts-only
    python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x07E2 --r2-commands
    python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x07D0 --csv > sites.csv
"""
import argparse
import collections
import csv
import sys

from disasm8051 import FLOW_OPCODES, OPCODE_LEN, converges_from, mnemonic

# Image map for ec/firmware/GMxMGxx_11.800. `runtime` is the address a site
# has once the image is loaded for disassembly; for the main EC that means
# a make_bank_image.py image (common area keeps its file offset, a bank
# window lands at 0x8000), for the PD image a flat 64 KiB dump of the
# region. Re-derive this with find_banks.py before trusting it against a
# different dump -- the bank->offset rows are that script's heuristic
# scoring, not a header field.
REGIONS = [
    ("common", 0x00000, 0x08000, 0x0000, "always mapped; same runtime address in every bank image"),
    ("bank0", 0x08000, 0x10000, 0x8000, "make_bank_image.py <fw> 0 0x08000"),
    ("bank1", 0x10000, 0x18000, 0x8000, "make_bank_image.py <fw> 1 0x10000"),
    ("erased", 0x18000, 0x20000, None, "all 0xFF"),
    ("pd-image", 0x20000, 0x30000, 0x0000, "separate ITE8850-PD 8051 image; dd bs=64k skip=2"),
    ("erased", 0x30000, 0x40000, None, "all 0xFF"),
]

# The PD image announces itself here. Checked rather than assumed, so a
# different dump whose 0x20000 region is something else gets labelled
# "unknown" instead of inheriting this image's conclusion.
PD_MARKER = (0x20040, b"ITE8850-PD")

# Flat image a human would load into r2 to see a site in each region.
R2_IMAGE = {"common": "bank0.bin", "bank0": "bank0.bin",
            "bank1": "bank1.bin", "pd-image": "pd.bin"}

MOV_DPTR = 0x90


def region_of(off: int, pd_verified: bool):
    for name, lo, hi, base, how in REGIONS:
        if lo <= off < hi:
            if name == "pd-image" and not pd_verified:
                return ("unknown", lo, base, "marker not found; region unidentified")
            return (name, lo, base, how)
    return ("unknown", 0, None, "outside the mapped regions")


def runtime_addr(off: int, pd_verified: bool):
    name, lo, base, _ = region_of(off, pd_verified)
    if base is None:
        return None
    return base + (off - lo)


def walk(d: bytes, start: int, max_insns: int = 8):
    """Decode forward from a site until the first control-flow instruction."""
    out = []
    i = start
    for _ in range(max_insns):
        n = OPCODE_LEN[d[i]]
        if i + n > len(d):
            break
        out.append((i, d[i:i + n], mnemonic(d, i)))
        if d[i] in FLOW_OPCODES:
            break
        i += n
        if i + 2 >= len(d) or d[i] == MOV_DPTR:
            break  # DPTR reloaded: whatever follows is a different access
    return out


def classify(insns):
    """Summarise a walk: access direction, and how far `inc dptr` walks on."""
    reads = writes = 0
    span = 1
    handoff = None
    for _, raw, text in insns[1:]:
        op = raw[0]
        if op == 0xE0:
            reads += 1
        elif op == 0xF0:
            writes += 1
        elif op == 0xA3:
            span += 1
        elif op in (0x02, 0x12) and not reads and not writes:
            handoff = text
            break
    if handoff:
        return f"DPTR handed to {handoff} -- direction unresolved here"
    if not reads and not writes:
        return "no movx found in the decoded window"
    parts = []
    if reads:
        parts.append(f"read x{reads}")
    if writes:
        parts.append(f"write x{writes}")
    if span > 1:
        parts.append(f"walks {span} consecutive bytes (inc dptr)")
    return ", ".join(parts)


def sites_for(d: bytes, addr: int):
    hi, lo = addr >> 8, addr & 0xFF
    return [i for i in range(len(d) - 2)
            if d[i] == MOV_DPTR and d[i + 1] == hi and d[i + 2] == lo]


def write_csv(d: bytes, addrs, pd_verified: bool) -> None:
    """One row per site, for a reader who wants to re-derive a table without
    re-running anything. `frame_onto`/`frame_over` are disasm8051's anchor
    sweep -- see converges_from() for why neither number settles framing on
    its own."""
    w = csv.writer(sys.stdout)
    w.writerow(["addr", "file_offset", "region", "runtime", "frame_onto",
                "frame_over", "access", "window"])
    for text in addrs:
        addr = int(text, 16)
        for o in sites_for(d, addr):
            name, _, _, _ = region_of(o, pd_verified)
            rt = runtime_addr(o, pd_verified)
            onto, over = converges_from(d, o)
            insns = walk(d, o)
            w.writerow([f"0x{addr:04X}", f"0x{o:05X}", name,
                        f"0x{rt:04X}" if rt is not None else "",
                        onto, over, classify(insns),
                        " ; ".join(" ".join(mn.split()) for _, _, mn in insns[1:])])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("addrs", nargs="+", help="hex addresses, e.g. 0x07E2")
    ap.add_argument("--counts-only", action="store_true",
                    help="per-image reference counts only, no site decode")
    ap.add_argument("--r2-commands", action="store_true",
                    help="also print ready-to-paste `r2 -a 8051` seek/pd commands per site")
    ap.add_argument("--csv", action="store_true",
                    help="write the site table as CSV on stdout instead of the decode")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so that --csv output stays a clean CSV when redirected.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF will be reported as region 'unknown'\n",
              file=sys.stderr)

    if args.csv:
        return write_csv(d, args.addrs, pd_verified)

    for text in args.addrs:
        addr = int(text, 16)
        found = sites_for(d, addr)
        tally = collections.Counter(region_of(o, pd_verified)[0] for o in found)
        print(f"0x{addr:04X}: {len(found)} direct MOV DPTR site(s)  "
              + ("  ".join(f"{k}={v}" for k, v in sorted(tally.items())) or "none"))
        if args.counts_only:
            print()
            continue
        for o in found:
            name, _, _, how = region_of(o, pd_verified)
            rt = runtime_addr(o, pd_verified)
            rt_text = f"runtime 0x{rt:04X}" if rt is not None else "runtime n/a"
            insns = walk(d, o)
            print(f"\n  file 0x{o:05X}  {name:<9} {rt_text}  [{how}]")
            print(f"    {classify(insns)}")
            for i, raw, mn in insns:
                shown = runtime_addr(i, pd_verified)
                label = f"0x{shown:04X}" if shown is not None else f"+0x{i - o:04X}"
                print(f"      {label}  {raw.hex():<8} {mn}")
            if args.r2_commands and rt is not None:
                img = R2_IMAGE.get(name, "image.bin")
                print(f"      $ r2 -a 8051 -e scr.color=0 -q -c 's 0x{rt:04x}; pd 10' {img}")
        print()


if __name__ == "__main__":
    sys.exit(main())
