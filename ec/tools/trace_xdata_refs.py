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
     hands DPTR to a subroutine (`lcall`/`acall`, or the `ljmp`/`ajmp`
     tail-call forms) instead, that is reported as exactly that --
     unresolved -- not guessed at.
  3. *What does the C-level census say about the same site?* `--census-column`
     appends a `census` column to the `--csv` table carrying
     `../annotations/xdata-0860-census-sites.csv`'s per-site correspondence:
     the bucket and occurrence count of the decompiled C's references at that
     site, or the token saying the correspondence was not recorded. **That
     column is not derived from the image, and this tool never derives it.**
     It is a hand-typed reading of the decompile, kept as data beside the
     sweep that has to agree with it, and `../tools/check_site_census.py` is
     what holds the two to each other -- the two methods' vocabularies and
     every way they differ are that tool's docstring. A blank cell would read
     as "the two agree", so there are none: `not recorded` is the explicit
     "not done by this method" token, and the 14 addresses of the 0x086x page
     other than `0x0860` carry it.

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
    python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x0860 --csv --census-column
    python3 trace_xdata_refs.py ../firmware/GMxMGxx_11.800 0x0860 --csv --census-column --check
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from disasm8051 import (FLOW_OPCODES, OPCODE_LEN, converges_from, mnemonic,
                        paged_target)

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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ANNOT = os.path.join(HERE, os.pardir, "annotations")
# The hand-typed cross-method correspondence --see the module docstring's
# third point. Read only by --census-column.
CENSUS_MAP = os.path.join(ANNOT, "xdata-0860-census-sites.csv")
# What --check compares against when it is given no path: the 0x086x page's
# own table, the one ../annotations/xdata-086x-dispatch.md §1 names. The other
# three committed tables this tool emits are named on their own pages, so
# those callers pass the path.
SITES_CSV = os.path.join(ANNOT, "xdata-086x-dispatch-sites.csv")

# The value each of the two non-mapped states renders as, in the vocabulary
# check_site_census.py's docstring states. A third cell value, "not recorded",
# belongs to the renderer rather than to this file: a site the map has no row
# for is not the same claim as a row that says the census is blind there.
CENSUS_TOKENS = {"no-occurrence": "no census occurrence",
                 "other-program": "other program"}


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


def load_census_map(path: str = CENSUS_MAP) -> dict:
    """file_offset (spelled as the map's CSV spells it) -> the cell to print.

    One `census` cell per site, rendered from the map's `census_state` and
    `census_count`, and nothing else: the token for "the decompile names no
    address here" and the token for "a different program, with its own XDATA
    map" are the map's to say, and this function only says which one. A state
    the map does not define is a ValueError rather than a default cell,
    because a default here is a cell that reads as agreement.
    """
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for row in rows:
        offset, state = row["file_offset"], row["census_state"]
        if state == "mapped":
            out[offset] = f"{row['census_bucket']} x{row['census_count']}"
        elif state in CENSUS_TOKENS:
            out[offset] = CENSUS_TOKENS[state]
        else:
            raise ValueError(f"{repo_path(path)}: {offset} has census_state "
                             f"{state!r}, which is not one of 'mapped', "
                             f"{', '.join(repr(s) for s in CENSUS_TOKENS)}")
    return out


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


def offset_for_runtime(runtime: int, region: str):
    """File offset of runtime address `runtime` as seen from code in `region`
    -- the inverse of runtime_addr(), off the same REGIONS table so the two
    cannot drift. None when the bytes are not reachable from that region.

    For the banked main EC this assumes the ordinary Keil banking convention:
    a target below 0x8000 is in the common area (mapped in every bank), and a
    target at or above 0x8000 is in the *same* bank as the caller. A cross-bank
    call would be decoded against the wrong bank's bytes, so audit_call_targets.py
    enumerates every lcall/ljmp in this image looking for one: none was found
    by that method, and the linker's own cross-bank path turns out to be the
    BL51 trampoline block, which is indirect and never reaches bucket B at all.
    That is "not found", not "absent" -- a same-bank and a cross-bank direct
    call are byte-identical, so 3220 of the 3261 such sites are decided by this
    assumption rather than by evidence. ../annotations/bank-call-audit.md has
    the counts and the blind spots.

    The 2-byte paged forms carry none of that assumption. An `ajmp`/`acall`
    target is the next instruction's own 2 KiB page with 11 bits substituted
    in, so it lands in the page the caller is already executing from; every
    mapped main-EC region in REGIONS is a whole number of 2 KiB pages aligned
    identically in file offset and runtime base (audit_call_targets.py
    --self-test checks that), so such a target cannot leave the caller's own
    region and needs no bank chosen for it. The one shape that would escape
    -- an instruction in a region's last two bytes, whose next PC is already
    past the end -- occurs nowhere in this image, which the same self-test
    checks site by site.

    A target at or above 0x8000 seen from the common area is unresolvable --
    nothing in the byte says which bank is mapped -- and returns None. That
    case does occur: 140 sites by byte scan, 83 of them anchored, per 5 of
    the same file. The PD image is flat, so nothing in it is affected by any
    of this.
    """
    home = next(((lo, hi, base) for name, lo, hi, base, _ in REGIONS
                 if name == region and base is not None), None)
    if home is None:
        return None
    lo, hi, base = home
    if base == 0x8000 and runtime < 0x8000:
        common_lo, common_base = next((lo2, base2) for name, lo2, _, base2, _
                                      in REGIONS if name == "common")
        return common_lo + (runtime - common_base)
    if not base <= runtime < base + (hi - lo):
        return None
    return lo + (runtime - base)


def call_target(raw: bytes, addr: int = None):
    """Absolute target of a handoff instruction classify() reports.

    The 3-byte absolute forms `ljmp`/`lcall` carry their whole target in the
    instruction, so they resolve with or without `addr`. The 2-byte paged
    forms `ajmp`/`acall` take their page from the address of the instruction
    *after* them, so they resolve only when the caller supplies `addr` -- a
    caller that cannot say where the instruction runs still gets None rather
    than a target picked from some assumed page. None for anything else, so a
    caller can hand it any instruction from a walk()."""
    if raw[0] in (0x02, 0x12) and len(raw) >= 3:
        return (raw[1] << 8) | raw[2]
    if raw[0] & 0x1F in (0x01, 0x11) and len(raw) >= 2 and addr is not None:
        return paged_target(raw[0], raw[1], addr)
    return None


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


def classify(insns, skip: int = 1):
    """Summarise a walk: access direction, and how far `inc dptr` walks on.

    `MOV DPTR,#imm16` builds CODE pointers as well as XDATA ones, so a site
    followed by `movc a,@a+dptr` or `jmp @a+dptr` is a table lookup in CODE
    and says nothing about a register of that number -- the blind spot
    ../annotations/ec-0x07d0-sites.md 5 warns about. Those two are named
    rather than folded into the "no movx" catch-all, which would read as
    "the walk found nothing" when the walk in fact found the answer.

    `skip` is how many leading instructions carry no direction: 1 for a
    reference site, whose first instruction is the `MOV DPTR` itself, and 0
    for a walk that starts at a subroutine entry point, where the first
    instruction is already an access on the DPTR the caller handed over."""
    reads = writes = movc = 0
    span = 1
    handoff = jmp_dptr = None
    for _, raw, text in insns[skip:]:
        op = raw[0]
        if op == 0xE0:
            reads += 1
        elif op == 0xF0:
            writes += 1
        elif op == 0xA3:
            span += 1
        elif op == 0x93:
            movc += 1
        elif op == 0x73:
            jmp_dptr = text
            break
        elif (op in (0x02, 0x12) or op & 0x1F in (0x01, 0x11)) \
                and not reads and not writes and not movc:
            handoff = text
            break
    if handoff:
        return f"DPTR handed to {handoff} -- direction unresolved here"
    if not reads and not writes:
        if movc:
            return f"movc a,@a+dptr x{movc} -- CODE pointer, not an XDATA access"
        if jmp_dptr:
            return f"{jmp_dptr.strip()} -- CODE pointer into a jump table"
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


def csv_table(d: bytes, addrs, pd_verified: bool, census=None):
    """(the `--csv` table, per-address counts of the sites the map does not
    cover), for a reader who wants to re-derive a table without re-running
    anything. `frame_onto`/`frame_over` are disasm8051's anchor sweep -- see
    converges_from() for why neither number settles framing on its own.

    A string rather than a write to stdout, because `--check` diffs the same
    bytes this prints. `census` is load_census_map()'s dict, appended as a
    ninth column; None leaves it out, and that is what keeps the other three
    committed tables this tool emits (`xdata-0400-045f-sites.csv`,
    `ec-07c4-07d5-sites.csv` and the `0x07D0` one) reproducing byte for byte
    from the plain command."""
    buf = io.StringIO()
    w = csv.writer(buf)
    columns = ["addr", "file_offset", "region", "runtime", "frame_onto",
               "frame_over", "access", "window"]
    if census is not None:
        columns.append("census")
    w.writerow(columns)
    unmapped = collections.Counter()
    for text in addrs:
        addr = int(text, 16)
        for o in sites_for(d, addr):
            name, _, _, _ = region_of(o, pd_verified)
            rt = runtime_addr(o, pd_verified)
            onto, over = converges_from(d, o)
            insns = walk(d, o)
            row = [f"0x{addr:04X}", f"0x{o:05X}", name,
                   f"0x{rt:04X}" if rt is not None else "",
                   onto, over, classify(insns),
                   " ; ".join(" ".join(mn.split()) for _, _, mn in insns[1:])]
            if census is not None:
                cell = census.get(row[1])
                if cell is None:
                    cell = "not recorded"
                    unmapped[f"0x{addr:04X}"] += 1
                row.append(cell)
            w.writerow(row)
    return buf.getvalue(), unmapped


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly.

    Read with `newline=""` so the comparison is the bytes on disk. The
    committed tables carry the csv module's own CRLF terminator, and
    universal-newline translation would rewrite every one of them to LF and
    report a difference on every run -- a check that is red on the committed
    data is a check nobody trusts, which is worse than no check."""
    try:
        with open(path, newline="") as f:
            on_disk = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{repo_path(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced; "
          "the file is the product of the command on the page that names it, "
          "so regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(), generated.splitlines(),
                                     "committed", "generated", lineterm="", n=0):
        print(line, file=sys.stderr)
    return 1


def main() -> int:
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
    ap.add_argument("--census-column", action="store_true",
                    help="with --csv, append the `census` column rendered from "
                         f"{repo_path(CENSUS_MAP)} -- read from that file, not "
                         "derived from the image")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="with --csv, diff this run against a committed table and "
                         "exit non-zero on any difference (default: the 0x086x page's)")
    args = ap.parse_args()

    if (args.census_column or args.check is not None) and not args.csv:
        ap.error("--census-column and --check are about the --csv table; they need --csv")

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so that --csv output stays a clean CSV when redirected.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF will be reported as region 'unknown'\n",
              file=sys.stderr)

    if args.csv:
        census = None
        if args.census_column or args.check is not None:
            try:
                census = load_census_map()
            except (OSError, ValueError) as e:
                print(f"note: {e}", file=sys.stderr)
                return 1
        table, unmapped = csv_table(d, args.addrs, pd_verified, census)
        if unmapped:
            by_addr = ", ".join(f"{a} x{n}" for a, n in sorted(unmapped.items()))
            print(f"note: {sum(unmapped.values())} site(s) have no row in "
                  f"{repo_path(CENSUS_MAP)} and read 'not recorded': {by_addr}\n",
                  file=sys.stderr)
        if args.check is not None:
            return check_table(table, args.check)
        sys.stdout.write(table)
        return 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
