#!/usr/bin/env python3
"""Every `lcall 0x104D` in the PD image, the four bytes it carries inline, and
where `0x104D` deposits them.

`ec/annotations/ec-0x07d0-sites.md` §5 found 68 of the 254 `0x07D0` sites
sitting immediately after this call, could not say what the four bytes were,
and recorded that a linear walk through them comes out misframed.
`../../docs/findings/pd-inline-arg-trampoline.md` is the write-up that settles
the mechanism; this is the measurement it rests on. The short version:
`0x104D` takes the caller's return address off the stack into DPTR, copies the
four code bytes at that address into XDATA through `0x1064`, and tail-jumps back
to return address + 4, so the bytes a linear decoder reads as instructions are
arguments to a call that has already returned.

Three things this tool does that a hand-picked transcript cannot.

**The population.** Every site, not the ones that happen to precede a `0x07D0`
reference. That is what turns "are the four bytes constant, an enumerated set,
or per-site?" into a distribution with a denominator: 40 distinct quadruples
over 458 sites, and 8 over the 68 the issue listed. A sample of three sites
could not distinguish those.

**The argument bytes are read, not inferred.** `--simulate` establishes *where*
the helper puts them and where it resumes; the per-site quadruple is then read
straight out of the image at the address the simulation says to read. A value
carried through the simulator instead would be one more chance to be wrong
about the same thing twice.

**The order of the two `pop`s is a choice, and both choices are computed over
every site.** `--simulate` runs one site under each order; `--pop-order` runs
the whole census under each, which is what the write-up's 40-against-427
comparison rests on. The two differ in nothing but the address the helper reads
the four code bytes from -- the destination comes from `B` and the literal
`0x82`, and no `pop` touches either -- so whatever moves between the columns is
the order and nothing else. **Which order this firmware uses is the write-up's
inference from that comparison, not this tool's finding**: the mode reports both
columns and the comparison a reader draws from them, the same way the census
puts a derived `dest` beside a scanned-for `dptr_load` rather than folding the
weaker one into the stronger.

**The `mov dptr` before the call is a scan, and the table says so.** `dptr_load`
is the nearest preceding `90 xx xx` *byte pattern* within `DPTR_SCAN` bytes,
and `dptr_gap` is how far back it was found, so a row with a gap of 0 can be
told from one with a gap of 20. This is not a decoded backward walk and not
control-flow recovery; the repository has deliberately not attempted the latter
(`../README.md`, "toolchain proven, not attempted"). A gap-0 row is a strong
reading and a gap-20 row is a weak one, and the column is what tells them
apart. Rows with no such load in range get an empty cell, which is "not found
by this scan" and never "there is none".

**A zero is "not found by this method".** The EC-image count is the safety
argument for `disasm8051.INLINE_ARG_CALLS` being keyed on the call rather than
on an address range: 458 in the PD image and 0 in the EC image, so no committed
main-EC listing can be re-framed by the special case.
`../tools/test_disasm8051_inline_args.py` pins the zero so a different dump
turns that argument red rather than silently re-framing the other program.

Usage:
    python3 pd_inline_arg_sites.py ../firmware/GMxMGxx_11.800
    python3 pd_inline_arg_sites.py ../firmware/GMxMGxx_11.800 --simulate
    python3 pd_inline_arg_sites.py ../firmware/GMxMGxx_11.800 --pop-order
    python3 pd_inline_arg_sites.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/pd-inline-arg-sites.csv
    python3 pd_inline_arg_sites.py ../firmware/GMxMGxx_11.800 --check
"""
import argparse
import collections
import csv
import io
import os
import sys

from disasm8051 import INLINE_ARG_CALLS, OPCODE_LEN, mnemonic
from trace_xdata_refs import (PD_MARKER, REGIONS, check_table, region_of,
                              repo_path)

HERE = os.path.dirname(os.path.abspath(__file__))
SITES_CSV = os.path.join(HERE, os.pardir, "annotations",
                         "pd-inline-arg-sites.csv")
# The committed site tables the summary reports overlap against, and the address
# each is a census of. Read-only, and only for the overlap figures: the census
# itself is derived from the image, so a stale row in one of these would move a
# number in the summary and nothing else.
OVERLAP_TABLES = (
    ("ec-0x07d0-sites.csv", "0x07D0"),
    ("ec-0x07d1-sites.csv", "0x07D1"),
    ("ec-07d6-07d7-sites.csv", "0x07D6/0x07D7"),
)

# The one call this tool knows how to describe. The target is read from
# `disasm8051.INLINE_ARG_CALLS` rather than spelled here, so a second entry in
# that table cannot leave this tool behind: it names the entry it is reporting
# on and refuses if there is not exactly one.
TRAMPOLINE = 0x104D
# The two `pop`s inside the helper that make the order a question at all. Spelled
# as addresses in the routine rather than derived from `TRAMPOLINE`, because they
# are a property of this routine's bytes: a derived pair would print a confident
# wrong one if the entry point ever moved, which is the one thing a report about
# the mechanism must not do.
POP_DPH, POP_DPL = 0x1052, 0x1054
# The two readings of that order, as `--pop-order` names its columns. The first
# is the one `census()` and the committed table follow; the second is the one the
# MCS-51 manual's push order would give.
READINGS = ("return address", "byte-swapped")
# The XDATA low byte the helper's `mov r0,#0x82` substitutes for the caller's
# DPL. A constant in the instruction, and the reason the destination below is
# not simply the DPTR the caller loaded.
DEST_LOW = 0x82
# How far back `dptr_load` looks for a `mov dptr,#imm16`. 32 is wide enough to
# reach the load at all 458 sites and short enough that a `90 xx xx` inside
# unrelated code is unlikely to be taken for one; `dptr_gap` is what a reader
# judges that likelihood by.
DPTR_SCAN = 32
# The site the write-up's simulation transcript is taken from, and the
# arguments it enters the helper with. Chosen because it is the site
# ec-0x07d0-sites.md §5 quotes, so the two can be read side by side.
EXAMPLE_RUNTIME = 0x3AA8
EXAMPLE_DPL, EXAMPLE_DPH = 0x98, 0x0A
# Garbage in the caller's A, R0 and B, so the transcript shows they do not
# survive. The helper overwrites R0 before reading it, and A is clobbered by
# the first `clr a`, so these values must not appear in the stores below.
EXAMPLE_A, EXAMPLE_R0, EXAMPLE_B = 0x11, 0x22, 0x33

COLUMNS = ["file_offset", "runtime", "resume", "resume_opcode", "inline",
           "value", "dptr_load", "dptr_gap", "dest"]

# The opcodes `simulate()` executes. Confined to the two routines' own bytes and
# deliberately short: an opcode missing here raises rather than being skipped,
# so the simulator cannot quietly execute a partial program and report a store
# that never happened.
SIM_LEN = {0xA8: 2, 0x85: 3, 0xD0: 2, 0x12: 3, 0xE4: 1, 0x93: 1, 0xA3: 1,
           0xC5: 2, 0xC8: 1, 0xF0: 1, 0x22: 1, 0x73: 1}
# The same instruction written the way `disasm8051` writes it, as a function of
# the operand byte(s) rather than a format string -- the three-byte forms take
# two of them and the two-byte forms one, and a single `%`-format cannot say
# which is which.
SIM_TEXT = {
    0xA8: lambda b1, b2: f"mov  r0,#0x{b1:02x}",
    0x85: lambda b1, b2: f"mov  0x{b2:02x},0x{b1:02x}",
    0xD0: lambda b1, b2: f"pop  0x{b1:02x}",
    0x12: lambda b1, b2: f"lcall 0x{(b1 << 8) | b2:04x}",
    0xE4: lambda b1, b2: "clr  a",
    0x93: lambda b1, b2: "movc a,@a+dptr",
    0xA3: lambda b1, b2: "inc  dptr",
    0xC5: lambda b1, b2: f"xch  a,0x{b1:02x}",
    0xC8: lambda b1, b2: "xch  a,r0",
    0xF0: lambda b1, b2: "movx @dptr,a",
    0x22: lambda b1, b2: "ret",
    0x73: lambda b1, b2: "jmp  @a+dptr",
}
# The registers a value can be in, in the order the transcript prints them. The
# five are the ones the two routines touch; anything else raises.
SIM_REGS = ("A", "R0", "B", "DPL", "DPH")
SIM_SFR = {"A": 0xE0, "B": 0xF0, "DPL": 0x82, "DPH": 0x83, "R0": 0xF8}


def pd_base(pd_verified: bool) -> int:
    """File offset the PD image's runtime 0x0000 sits at.

    Read off `trace_xdata_refs.REGIONS` rather than written as 0x20000, so the
    two tools cannot disagree about where the second program starts. Raises on
    an unverified marker instead of returning a guess: without the marker the
    region is unidentified and every offset below would be somebody else's."""
    if not pd_verified:
        raise SystemExit("pd region unidentified; see main()")
    lo, base = next((lo, base) for name, lo, _, base, _ in REGIONS
                    if name == "pd-image")
    return lo - base


def pattern_for(target: int) -> bytes:
    """The bytes of a 3-byte absolute call to `target`.

    Derived from `OPCODE_LEN` rather than assumed, so a caller table that grew
    a 2-byte entry would make this raise instead of scanning for a 3-byte
    pattern that no longer describes the call."""
    n = OPCODE_LEN[0x12]
    if n != 3:
        raise SystemExit(f"lcall is {n} bytes in OPCODE_LEN, not 3; this tool's "
                         "scan pattern would not describe the call it names")
    return bytes([0x12, target >> 8, target & 0xFF])


class Machine:
    """The five registers the two routines touch, as bytes.

    A dict and named accessors rather than a byte array indexed by SFR number,
    because the point of the transcript is that a reader can see which register
    each value is in; an `xch` chain is exactly where a hand-trace goes wrong,
    and this is the executable version of the check.
    """

    def __init__(self, a, r0, b, dpl, dph):
        self.v = {"A": a, "R0": r0, "B": b, "DPL": dpl, "DPH": dph}

    def rd(self, direct: int) -> int:
        if direct not in SIM_SFR.values():
            raise SystemExit(f"simulate(): read of unmodelled direct "
                             f"0x{direct:02x}; the two routines are supposed "
                             "to touch only A, R0, B, DPL and DPH")
        return self.v[[k for k, a in SIM_SFR.items() if a == direct][0]]

    def wr(self, direct: int, val: int) -> None:
        if direct not in SIM_SFR.values():
            raise SystemExit(f"simulate(): write of unmodelled direct "
                             f"0x{direct:02x}")
        self.v[[k for k, a in SIM_SFR.items() if a == direct][0]] = val & 0xFF

    def dptr(self) -> int:
        return (self.v["DPH"] << 8) | self.v["DPL"]

    def row(self) -> str:
        return " ".join(f"{k}=0x{self.v[k]:02X}" for k in SIM_REGS)


def simulate(d: bytes, base: int, entry: int, pops: list, machine: Machine,
             trace: bool = True) -> tuple:
    """(the XDATA stores, the tail-jump target) for `0x104D` entered at `entry`.

    `pops` is what the two `pop`s at `0x1052`/`0x1054` take off the stack, in
    order. It is a parameter rather than a derivation because the MCS-51
    `lcall` pushes the high byte first, so the first `pop` would take the *low*
    byte and leave DPTR holding the byte-swapped return address; what this image
    actually does contradicts that, and the write-up carries the measurement
    that settles it. Passing it in is what lets `--simulate` be run either way
    and produce a difference instead of an assertion.

    A `jmp @a+dptr` ends the run and its target is returned, because a
    `jmp` transfers control: continuing to step from the following address
    would execute bytes the program never reaches, and on this image that
    already produces a fifth store that does not happen."""
    stores = []
    pc = entry
    while True:
        op = d[base + pc]
        if op not in SIM_LEN:
            raise SystemExit(f"simulate(): unmodelled opcode 0x{op:02X} at "
                             f"0x{pc:04X}; add it to SIM_LEN or the transcript "
                             "stops being a claim about the whole routine")
        n = SIM_LEN[op]
        b1 = d[base + pc + 1]
        b2 = d[base + pc + 2] if n == 3 else None
        if op == 0xA8:
            machine.v["R0"] = b1
        elif op == 0x85:
            machine.wr(b2, machine.rd(b1))
        elif op == 0xD0:
            machine.wr(b1, pops.pop(0))
        elif op == 0xE4:
            machine.v["A"] = 0
        elif op == 0x93:
            machine.v["A"] = d[base + machine.dptr()]
        elif op == 0xA3:
            machine.v["DPL"] = (machine.v["DPL"] + 1) & 0xFF
        elif op == 0xC5:
            tmp = machine.rd(b1)
            machine.wr(b1, machine.v["A"])
            machine.v["A"] = tmp
        elif op == 0xC8:
            tmp = machine.v["R0"]
            machine.v["R0"] = machine.v["A"]
            machine.v["A"] = tmp
        elif op == 0xF0:
            stores.append((machine.dptr(), machine.v["A"]))
        if trace:
            note = SIM_TEXT[op](b1, b2)
            mark = "   <-- store" if op == 0xF0 else ""
            print(f"  0x{pc:04X}  {note:<18}"
                  f"  {machine.row()}  DPTR=0x{machine.dptr():04X}{mark}")
        if op == 0x22:
            return stores, None
        if op == 0x73:
            return stores, machine.dptr()
        if op == 0x12:
            # Folded up rather than returned alone, because the four `movx`
            # stores all happen inside the `0x1064` calls and a caller reading
            # only the outermost frame's list would see none of them.
            inner, _ = simulate(d, base, (b1 << 8) | b2, pops, machine, trace)
            stores.extend(inner)
        pc += n


def dptr_before(d: bytes, site: int) -> tuple:
    """(the DPTR a caller loaded, how far back) from the nearest `90 xx xx`.

    A backward byte scan, which is the honest description and not a euphemism:
    it cannot tell a `mov dptr,#imm16` from the same three bytes inside another
    instruction. `dptr_gap` is the reader's evidence -- a gap of 0 means the
    load is the instruction immediately before the call, which is as strong as
    a byte pattern gets."""
    for back in range(3, DPTR_SCAN + 1):
        o = site - back
        if o < 0:
            break
        if d[o] == 0x90:
            return (d[o + 1] << 8) | d[o + 2], back
    return None, None


def sites(d: bytes, pd_verified: bool) -> list:
    """Every `lcall 0x104D` in the dump, in file-offset order.

    The whole dump is scanned and the region split afterwards, rather than only
    the PD window, so the count this returns and `ec_image_count()`'s are two
    halves of one scan and cannot come from two methods."""
    pat = pattern_for(TRAMPOLINE)
    return [off for off in range(0, len(d) - len(pat) + 1)
            if d[off:off + len(pat)] == pat
            and region_of(off, pd_verified)[0] == "pd-image"]


def census(d: bytes, base: int) -> list:
    """One row per site, as a dict keyed by `COLUMNS`."""
    n = INLINE_ARG_CALLS[TRAMPOLINE]
    rows = []
    for off in sites(d, True):
        runtime = off - base
        arg = d[off + 3:off + 3 + n]
        resume = runtime + 3 + n
        dptr, gap = dptr_before(d, off)
        rows.append({
            "file_offset": f"0x{off:05X}",
            "runtime": f"0x{runtime:04X}",
            "resume": f"0x{resume:04X}",
            # The byte where the tail call lands, so a reader can see the resume
            # point is an instruction and not padding. That it is a plausible
            # opcode is what distinguishes the +4 reading from any other.
            "resume_opcode": f"0x{d[base + resume]:02X}",
            "inline": arg.hex(" "),
            "value": f"0x{int.from_bytes(arg, 'big'):08X}"
                     f"={int.from_bytes(arg, 'big')}",
            "dptr_load": f"0x{dptr:04X}" if dptr is not None else "",
            "dptr_gap": gap if gap is not None else "",
            "dest": f"0x{(dptr & 0xFF00) | DEST_LOW:04X}" if dptr is not None
                    else "",
        })
    return rows


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write, because `--check`
    diffs the same bytes this prints and the tool's contract is that it writes
    nothing but stdout."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in rows:
        w.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


def ec_image_count(d: bytes) -> int:
    """`lcall 0x104D` occurrences in the main EC image, by the same scan.

    Split by `region_of` rather than by an offset range spelled here, so the
    number is "the EC's own count" and not "whatever lies below 0x20000"."""
    pat = pattern_for(TRAMPOLINE)
    return sum(1 for off in range(0, len(d) - len(pat) + 1)
               if d[off:off + len(pat)] == pat
               and region_of(off, True)[0] in ("common", "bank0", "bank1"))


def read_table(name: str) -> list:
    """The rows of a committed site table, named as in `OVERLAP_TABLES`.

    Shared with `pop_order_mode()` so the `0x07D0` row count the summary reports
    and the one the pop-order figures are counted against come from one file and
    one parse. Read-only, like the census it feeds: a stale row moves a number
    in the summary and nothing else."""
    with open(os.path.join(HERE, os.pardir, "annotations", name),
              newline="") as f:
        return list(csv.DictReader(f))


def overlap(rows: list) -> list:
    """(table label, its row count, how many are preceded by the idiom)."""
    by_offset = {r["file_offset"] for r in rows}
    out = []
    for name, label in OVERLAP_TABLES:
        try:
            table = read_table(name)
        except OSError as e:
            out.append((label, f"unreadable: {e}", ""))
            continue
        hit = sum(1 for r in table
                  if f"0x{int(r['file_offset'], 16) - 7:05X}" in by_offset)
        out.append((label, len(table), hit))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout instead of "
                         "the summary")
    ap.add_argument("--simulate", action="store_true",
                    help="execute 0x104D and 0x1064 over the committed image "
                         "and print the register trace, instead of the census")
    ap.add_argument("--pop-order", dest="pop_order", action="store_true",
                    help="count every site under both readings of the two pops "
                         "at 0x1052/0x1054, instead of the census")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: {repo_path(SITES_CSV)})")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so `--csv` redirected to a file stays a clean CSV, and
        # non-zero: without the marker the region is unidentified, so every
        # runtime address below would be somebody else's.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- the "
              "pd region is unidentified, so this tool has no population to "
              "census\n", file=sys.stderr)
        return 1

    if len(INLINE_ARG_CALLS) != 1 or TRAMPOLINE not in INLINE_ARG_CALLS:
        print(f"note: disasm8051.INLINE_ARG_CALLS holds "
              f"{sorted(INLINE_ARG_CALLS)}, and this tool describes one call -- "
              "extend it rather than let it report the wrong population\n",
              file=sys.stderr)
        return 1

    base = pd_base(pd_verified)

    if args.simulate:
        return simulate_mode(d, base)
    if args.pop_order:
        return pop_order_mode(d, base)

    rows = census(d, base)
    generated = csv_table(rows)
    if args.check is not None:
        return check_table(generated, args.check)
    if args.csv:
        sys.stdout.write(generated)
        return 0

    ec = ec_image_count(d)
    tuples = collections.Counter(r["inline"] for r in rows)
    resume_ops = collections.Counter(r["resume_opcode"] for r in rows)
    dests = collections.Counter(r["dest"] for r in rows if r["dest"])
    gaps = collections.Counter(r["dptr_gap"] for r in rows if r["dptr_gap"] != "")
    # Read most-significant byte first, because that is the order the helper
    # copies them in: the first byte deposited is the first byte of the number.
    high_zero = sum(1 for t in tuples
                    if bytes(int(b, 16) for b in t.split())[:2] == b"\x00\x00")
    print(f"0x{TRAMPOLINE:04X} is called {len(rows)} time(s) in the pd image and "
          f"{ec} time(s) in the main EC,\nby a byte scan for "
          f"`{pattern_for(TRAMPOLINE).hex(' ')}` over the whole dump.\n")
    print(f"The {len(tuples)} distinct four-byte arguments, most common first; "
          f"the value is\nread big-endian, in the order the helper copies them: "
          f"\n{high_zero} of the {len(tuples)} are zero in both high "
          "bytes.\n")
    for text, n in tuples.most_common():
        raw = bytes(int(b, 16) for b in text.split())
        print(f"  {n:>4}  {text}   0x{int.from_bytes(raw, 'big'):08X} "
              f"= {int.from_bytes(raw, 'big')}")
    top_op, top_n = resume_ops.most_common(1)[0]
    # Only rendered for a one-byte opcode. The operand bytes of a three-byte
    # form are not part of this claim, and printing them as zero would put a
    # fabricated `mov dptr,#0x0000` in a summary a reader might quote.
    top_raw = int(top_op, 16)
    one_byte = OPCODE_LEN[top_raw] == 1
    top_text = f" (`{mnemonic(bytes([top_raw]), 0, 0)}`)" if one_byte else ""
    print(f"\nThe tail call resumes {INLINE_ARG_CALLS[TRAMPOLINE]} bytes past the "
          f"call, over {len(resume_ops)} distinct\nopcode(s) at the resume "
          f"point; {top_op}{top_text} at {top_n} of {len(rows)}.\n")
    print("Where the helper deposits them, from `dptr_load` "
          "(a backward scan, most\ncommon gap "
          f"{gaps.most_common(1)[0][0]}, which is the instruction immediately "
          f"before the call):\n")
    for dest, n in dests.most_common(6):
        print(f"  {n:>4}  {dest}")
    print(f"\n{sum(1 for r in rows if not r['dptr_load'])} of {len(rows)} have "
          f"no `90 xx xx` within {DPTR_SCAN} bytes and read empty, which is "
          "'not found by\nthis scan' and not 'there is none'.\n")
    print("Overlap with the committed site tables "
          "(the idiom at file_offset - 7):\n")
    for label, total, hit in overlap(rows):
        print(f"  {str(total):>6}  {label:<12} {hit} preceded by the idiom")
    print(f"\n{repo_path(SITES_CSV)} is the table, one row per site; "
          "`--simulate` is the mechanism\nbehind the `inline` and `dest` "
          "columns, and the write-up is\n"
          "../../docs/findings/pd-inline-arg-trampoline.md.")
    return 0


def simulate_mode(d: bytes, base: int) -> int:
    """The transcript `--simulate` prints, for the example site.

    Two runs, differing only in what the two `pop`s take off the stack, because
    that is the one thing about the mechanism this image's evidence contradicts
    the MCS-51 manual on and a reader is entitled to see both of. The stores are
    at the same XDATA addresses either way -- the destination comes from `B` and
    the literal `0x82`, neither of which a pop touches -- so what the order
    changes is only *which* code bytes are copied."""
    ret = EXAMPLE_RUNTIME + 3
    print(f"0x{TRAMPOLINE:04X} entered with the caller's DPTR = 0x"
          f"{EXAMPLE_DPH:02X}{EXAMPLE_DPL:02X} (its `mov dptr,#0x"
          f"{EXAMPLE_DPH:02X}{EXAMPLE_DPL:02X}` at 0x{EXAMPLE_RUNTIME - 3:04X}) "
          f"and a return address of 0x{ret:04X}.\n")
    for label, pops in ((f"the two pops take 0x{ret >> 8:02X} then "
                         f"0x{ret & 0xFF:02X}, so DPTR = the return address",
                         [ret >> 8, ret & 0xFF]),
                        (f"the two pops take 0x{ret & 0xFF:02X} then "
                         f"0x{ret >> 8:02X}, so DPTR = the byte-swapped 0x"
                         f"{(ret & 0xFF) << 8 | ret >> 8:04X} that the manual's "
                         "push order would give",
                         [ret & 0xFF, ret >> 8])):
        print("=" * 78)
        print(label)
        print("=" * 78)
        m = Machine(EXAMPLE_A, EXAMPLE_R0, EXAMPLE_B, EXAMPLE_DPL, EXAMPLE_DPH)
        stores, jump = simulate(d, base, TRAMPOLINE, list(pops), m)
        print("\n  XDATA written:")
        for addr, val in stores:
            print(f"    0x{addr:04X} <- 0x{val:02X}")
        if jump is not None:
            print(f"  `clr a ; jmp @a+dptr` then transfers to 0x{jump:04X}, "
                  f"where the byte is 0x{d[base + jump]:02X}")
        print()
    return 0


def reading_at(runtime: int, n: int) -> list:
    """[(label, read address, resume address)] for the two `pop` orderings.

    A site's return address is its runtime address + 3; the byte-swapped
    reading is the one the MCS-51 manual's push order implies, computed here
    rather than argued against. The resume is the read address `n` on in either
    column, because `0x104D` calls `0x1064` once per argument byte and each call
    leaves DPTR one further on -- the same arithmetic both ways, which is what
    keeps the comparison about the order and nothing else."""
    ret = runtime + OPCODE_LEN[0x12]
    swapped = ((ret & 0xFF) << 8) | (ret >> 8)
    return [(READINGS[0], ret, ret + n), (READINGS[1], swapped, swapped + n)]


def pop_order_mode(d: bytes, base: int) -> int:
    """Every site counted under both readings of the two `pop`s, side by side.

    `--simulate` is this for one site. What a whole-population comparison adds is
    that the byte-swapped reading is not merely different, it is *worse*: a
    firmware that put a four-byte constant in a second program would not be
    under any obligation to make the byte-scrambled addresses it would have to
    copy from hold an enumerated set, and this one does not. That is the
    comparison the write-up's claim to have settled the order rests on, so it is
    a mode here rather than a table in prose.

    Both denominators are printed for the `0x07D0` figure, and they are
    different populations -- rows of a committed table against rows of this
    census. Both are printed because printing one would let a reader take the
    numerator of 4 for 4 of the 254."""
    n = INLINE_ARG_CALLS[TRAMPOLINE]
    offs = sites(d, True)
    try:
        d07_offs = {int(r["file_offset"], 16)
                    for r in read_table("ec-0x07d0-sites.csv")}
    except OSError as e:
        # stderr and non-zero, as in `main()`: without the table there is no
        # denominator to report the hit count against, and a figure with one
        # missing would read as a finding.
        print("note: cannot read the committed 0x07D0 table, so there is no "
              f"denominator for the resume count: {e}\n", file=sys.stderr)
        return 1

    quads = {label: collections.Counter() for label in READINGS}
    rows_hit = {label: set() for label in READINGS}
    calls_hit = collections.Counter()
    unreadable = 0
    for off in offs:
        for label, at, resume in reading_at(off - base, n):
            # The read address is a permutation of a site's own, not an offset
            # into the census, so unlike `census()`'s it is bounded against the
            # dump rather than assumed to be in it.
            if base + at + n > len(d):
                unreadable += 1
                continue
            quads[label][d[base + at:base + at + n]] += 1
            if base + resume in d07_offs:
                rows_hit[label].add(base + resume)
                calls_hit[label] += 1

    width = max(len(s) for s in READINGS)
    lines = [(f"distinct four-byte values over {len(offs)}",
              [str(len(quads[r])) for r in READINGS]),
             ("most common value",
              [quads[r].most_common(1)[0][0].hex(" ") for r in READINGS]),
             ("its multiplicity",
              [str(quads[r].most_common(1)[0][1]) for r in READINGS]),
             (f"0x07D0 rows a resume lands on, of {len(d07_offs)}",
              [str(len(rows_hit[r])) for r in READINGS]),
             (f"call sites whose resume lands on one, of {len(offs)}",
              [str(calls_hit[r]) for r in READINGS])]
    label_w = max(len(s) for s, _ in lines)
    print(f"Both readings of the two `pop`s at 0x{POP_DPH:04X}/0x{POP_DPL:04X}, "
          f"over the {len(offs)} sites,\nwith nothing else changed.  The "
          f"left-hand column is the one `census()`\nand the committed `inline` "
          f"column follow; adopting it over the other is\nthe write-up's "
          f"inference from this table, not this tool's finding.\n")
    print(f"{'':<{label_w}}  " + "  ".join(f"{r:>{width}}" for r in READINGS))
    for label, cells in lines:
        print(f"{label:<{label_w}}  "
              + "  ".join(f"{c:>{width}}" for c in cells))
    print("\nThe last two rows are one figure counted twice, over two "
          "populations that are\nnot the same size: no two calls resume at the "
          "same address under either\nreading, so `68 of 254` and `68 of 458` "
          "agree, and the `4` is four of the 458\ncalls.  Reading it as four of "
          "the 254 `0x07D0` rows would be borrowing a\ndenominator that is not "
          "its own, which is why both are printed.")
    print(f"\n{unreadable} of {len(offs)} read outside the dump "
          "under one of the two readings, so\nevery figure above is over the "
          "whole population.  A non-zero count would\nleave those sites out, "
          "which is 'not found by this method' and not 'there\nis none'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
