#!/usr/bin/env python3
"""Find the XDATA sites the other two scanners cannot see: `movx @Ri`, whose
address is `P2` in the high byte and `R0`/`R1` in the low one, and therefore
is not in the instruction at all.

`scan_refs.py` counts `MOV DPTR,#imm16` and `trace_xdata_refs.py` takes the
same sites down to the individual one. Both therefore see one XDATA
addressing mode of the 8051 out of the two, and `docs/findings.md` §5's "the
static route to `0x07D0` is now exhausted on the firmware side" is exhausted
*by that mode*: `0x07B9` is a byte Windows writes and the EC honours, with
zero direct references anywhere in the image, which is the §4c retraction's
standing counter-example. On an 8051 the other mode is `movx a,@r0` (0xE2),
`movx a,@r1` (0xE3), `movx @r0,a` (0xF2) and `movx @r1,a` (0xF3), one byte
each, with the page in the `P2` SFR (0xA0) and the low byte in the register.
Nobody had looked for them; this is that look.

**Two passes, and both counts are printed.** A raw byte scan finds every
offset whose byte is one of those four, and it over-counts by about 8x: 0xE2,
0xE3, 0xF2 and 0xF3 are common *operand* bytes inside `mov dptr,#imm16`,
`jnb bit,rel` and `cjne a,#data,rel`, so most of what a byte scan finds is
somebody's immediate. The anchored pass walks each region from its base with
`OPCODE_LEN` and `inline_arg_len` and keeps only the offsets that walk reaches
as an instruction start. The anchored set is the population every other number
here is about; the raw count is printed beside it so the gap is visible rather
than silently filtered.

**The window resolves an address, or it says which half it could not.** For
each site this walks back a bounded window of the *anchored* decode -- the
instruction starts that precede the site in the same walk, so the window is
framed by the same decision the site itself was found under -- and records
the last write to the `P2` byte and the last `mov rN,#imm` for the site's own
register. Both literal means a full address. Anything else is `unresolved`,
and the cell names the half and the encoding that defeated it, because
`P2`_SUPPLIED-BY-A-REGISTER and `Rn`-NEVER-LOADED-ARE-DIFFERENT-REASONS and a
single word would merge them. Nothing is inferred: a page is never read out of
a register, a table, or across a call, which is the issue's own instruction and
this repository's calibration rule, and it is also what makes a negative
result citable.

**A zero is "not found by this method", and the control is on every run.** The
summary prints the same `mov <direct>,#imm` query for six other byte-addressed
SFRs beside the `P2` one, because a scan that finds nothing is only
meaningful next to a scan that finds plenty: the count for `0xF0` (B) is three
orders of magnitude away from the count for `0xA0`, and that difference is
what turns "not found by this method" into a statement about the form rather
than about the tool.

**The two images are never added together.** `region_of()` is the only source
of the split and every count is printed per image; the PD image's 0x07B9 is a
different program's byte. This is `docs/findings/lightbar-bat-flow.md` §2's
mistake and `trace_xdata_refs.py`'s docstring's first point.

**What this does not establish.** A `P2` set by a call, restored after one, or
seeded from a table; a `P2` written before the window opens (the window is 24
bytes and the walk behind the site is only a walk); the low-byte register's
value after an instruction this tool does not model -- it records the last
literal load it can see, not the register's value, and the `window` column
carries the instructions between the two so a reader can judge that itself;
`mov @Ri,#data` (0x76/0x77), which writes the same XDATA byte through the same
`P2` half and is not in this population because the issue asked for `movx`;
`@dptr` walks, which are a different population and a different issue; and
the anchored pass's own framing, which is one linear decode per region and
re-syncs a byte at a time at the region's tail, so one mis-framing shifts
every site behind it -- `frame_onto`/`frame_over` are `disasm8051`'s evidence
about that, and as its own docstring says, read the pair and not either half.

Reads the committed image and writes nothing but stdout.
`ec/annotations/indirect-xdata-sites.md` is the write-up and
`ec/annotations/indirect-xdata-sites.csv` is the table this reproduces.

Usage:
    python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800
    python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/indirect-xdata-sites.csv
    python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --check
    python3 find_indirect_xdata.py ../firmware/GMxMGxx_11.800 --page 0x07
"""
import argparse
import bisect
import collections
import csv
import io
import os
import sys

from disasm8051 import OPCODE_LEN, converges_from, inline_arg_len, mnemonic
from trace_xdata_refs import (PD_MARKER, REGIONS, check_table, region_of,
                              repo_path, runtime_addr)

SITES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        os.pardir, "annotations", "indirect-xdata-sites.csv")

# The indirect XDATA forms, as {opcode: (form, which register supplies the low
# byte)}. Four one-byte opcodes, and the register is part of the site's own
# identity rather than something a later pass looks up: `movx a,@r0` and
# `movx a,@r1` reach different bytes off the same `P2`, so a table that
# resolved a page without naming the register would resolve the wrong address.
MOVX_RI = {0xE2: ("movx a,@r0", 0), 0xE3: ("movx a,@r1", 1),
           0xF2: ("movx @r0,a", 0), 0xF3: ("movx @r1,a", 1)}

# Every 8051 encoding that writes the `P2` byte (direct 0xA0) or one of its
# eight bits (0xA0-0xA7), as (first opcode, last opcode, which byte carries
# the address, name, the immediate is the page).
#
# The table is complete rather than literal-only, and that completeness is
# the point: a window whose *last* `P2` write is one of the other eighteen
# has a page this tool cannot name, and a table listing only `mov p2,#imm`
# and the four bit forms would step over `orl p2,#0x0f` silently and resolve
# a page from a `P2` that had just been overwritten.
#
# `pd_index_geometry.DIRECT_DST_OPS` is the in-repository oracle for the
# direct-byte-destination rows, and it is what caught `xch a,direct` (0xC5)
# missing here when #1169 was reviewed: this table was built from sdas8051
# alone and that encoding is the one an assembling-first pass does not reach.
#
# Every row here was assembled with sdas8051 -- the assembler
# `verify_reassembly.py` re-encodes every committed listing with -- rather
# than recalled, and the encodings are transcribed into
# `../tools/test_find_indirect_xdata.py` beside their expected names so the
# table is held against that transcript and not against itself. Re-derive
# them with:
#
#     printf '\t.area CODE (ABS)\n\tmov p2,#0x07\n\torl p2,#0x0f\n\t...\n' > p.s
#     sdas8051 -plosgff p.rel p.s
#
# Three rows are not in sdas8051's accepted set and are there from the 8051
# manual and `verify_reassembly.BIT_UNSUPPORTED` instead: `clr bit` (0xC1),
# which sdas8051 assembles as `clr direct` (0xC2) without complaining.
# `mov direct,direct` (0x85) is the row that carries the address in the
# *third* byte: the destination is the second operand and the source the
# first, which is the same trap `verify_reassembly.DIRECT_OPERANDS`'s comment
# works through.
#
# The three logic rows start at 0x02 into their decade, not at 0x00, and that
# is not a detail. 0x40 is `jc rel`, 0x50 `jnc rel`, 0x60 `jz rel` and 0x70
# `jnz rel`, and in each of those the second byte is a *displacement* -- so a
# table spanning 0x40-0x43 would read every `jc` whose target byte happened
# to fall in 0xA0-0xA7 as a write to `P2`, and would resolve a page from a
# branch target. It is not a theoretical over-count: the first run of this
# tool's own `--csv` reported two `movx @Ri` sites whose last `P2` write was
# `orl p2,#imm-or-a`, and the `window` cell on the same two rows rendered
# those bytes as `jc +0xa2` and `jc +0x98`. `../tools/
# test_find_indirect_xdata.py` pins the collision in both directions.
P2_WRITERS = [
    (0x75, 0x75, 1, "mov p2,#imm", True),
    (0x85, 0x85, 2, "mov p2,direct", False),
    (0xC5, 0xC5, 1, "xch a,p2", False),           # the direct byte is at raw[1]
    (0x86, 0x87, 1, "mov p2,@ri", False),        # r0, r1
    (0x88, 0x8F, 1, "mov p2,register", False),   # Rn in the opcode's low 3 bits
    (0xF5, 0xF5, 1, "mov p2,acc", False),
    (0x05, 0x05, 1, "inc p2", False),            # also `inc p2.x`
    (0x15, 0x15, 1, "dec p2", False),
    (0xD0, 0xD0, 1, "pop p2", False),
    (0xD5, 0xD5, 1, "djnz p2", False),
    (0x42, 0x43, 1, "orl p2,#imm-or-a", False),  # 0x43 carries the immediate
    (0x52, 0x53, 1, "anl p2,#imm-or-a", False),  # 0x53 carries the immediate
    (0x62, 0x63, 1, "xrl p2,#imm-or-a", False),  # 0x63 carries the immediate
    (0x10, 0x10, 1, "jbc p2.x", False),          # clears the bit it tests
    (0x92, 0x92, 1, "mov p2.x,carry", False),
    (0xB2, 0xB2, 1, "cpl p2.x", False),
    (0xC1, 0xC1, 1, "clr p2.x", False),          # sdas8051 spells this 0xC2
    (0xC2, 0xC2, 1, "clr p2", False),            # the whole byte
    (0xD2, 0xD2, 1, "setb p2.x", False),
]
# The one row whose immediate is the page half, by name, so the summary can
# pin it first and the test can ask for it without re-deriving the index.
P2_LITERAL = "mov p2,#imm"

# The SFRs the summary's control query runs over, as {direct address: name}.
# The control exists so a zero for 0xA0 is a fact about the form rather than
# about the query: each of these is the same two-byte-plus-immediate encoding
# the `P2` half would have, so a scan that finds hundreds of one and none of
# another is measuring the image. SP (0x81) is here because it is the
# byte-addressed register every C compiler seeds first.
CONTROL_SFRS = [(0xF0, "B"), (0xE0, "ACC"), (0xD0, "PSW"), (0x81, "SP"),
                (0x90, "P1"), (0x80, "P0"), (0xA0, "P2")]

# The backward window, in bytes. `disasm8051.converges_from()`'s own default,
# so the two tools that frame a site frame it over the same distance; the
# reason a number and not a rule is that a reader looking at a cell carrying
# it has to be able to see which 24 produced it.
WINDOW = 24

# The main EC, as `region_of()` spells its three regions, and the PD image
# beside it. Named rather than computed so a reader can see that the split is
# a split and not a total: a `P2` in the PD image is another program's byte.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")
PD_REGION = "pd-image"

# The cells `xaddr` is built from, and the two reasons a window can run out
# before it has seen both halves. Named because a cell that said "unresolved"
# with no reason would read as a verdict on the byte rather than as a limit on
# the method, which is the one thing the §4c retraction is about.
NO_P2_WRITER = "no P2 write in the window"
NO_RN_LOAD = "no `mov r{reg},#imm` in the window"


def window_end(back: int) -> str:
    """The token for a window that used every byte it was given.

    A function for the reason `trace_xdata_refs.budget_end()` gives: the
    number is the loop's own argument, and a reader looking at a
    `window exhausted (24 bytes)` cell has to be able to see which 24."""
    return f"window exhausted ({back} bytes)"


REGION_START = "start of region"


def p2_write(d: bytes, i: int):
    """(name, literal) if the instruction at offset `i` writes 0xA0-0xA7.

    None for anything else, including an instruction whose *second* byte
    happens to fall in 0xA0-0xA7 without its opcode being one of the
    writers -- which is most of the image, and is the same over-count the raw
    pass reports for the `movx` opcodes themselves. The address-byte test is
    what separates `P2` from the other byte-addressed SFRs, so the table does
    not have to be spelled per-SFR.

    `literal` is the immediate for `mov p2,#imm` and None for everything
    else, which is what separates the one encoding that can resolve a page
    from the seventeen that cannot."""
    if i >= len(d):
        return None
    op = d[i]
    row = next((r for r in P2_WRITERS if r[0] <= op <= r[1]), None)
    if row is None:
        return None
    _lo, _hi, at, name, literal = row
    if i + at >= len(d) or not 0xA0 <= d[i + at] <= 0xA7:
        return None
    return name, d[i + 2] if literal and i + 2 < len(d) else None


def rn_load(d: bytes, i: int, reg: int):
    """The immediate `mov r{reg},#imm` at `i` loads, else None.

    Only the site's own register, and only the immediate form: the issue
    asked for the last `mov r0,#imm`/`mov r1,#imm` and nothing else, and a
    wider rule would have to model every instruction that modifies the
    register to mean anything. That limit is named in the module docstring
    and the `window` column carries the instructions between the load and
    the site so a reader can see what this tool did not model."""
    if 0x78 + reg != d[i] or i + 1 >= len(d):
        return None
    return d[i + 1]


def anchored_starts(d: bytes, lo: int, hi: int) -> list:
    """Every offset the linear decode of `d[lo:hi]` reaches as an
    instruction start, in order.

    The one framing decision this tool makes, and `disasm8051.py` holds the
    tables: `OPCODE_LEN` for the length, `inline_arg_len()` for the PD
    image's inline-argument block, and a one-byte re-sync where an
    instruction would run past the region's end. Nothing else re-frames
    anything, so a site's framing evidence (`converges_from()`) and the
    window behind it come from the same walk."""
    starts, i = [], lo
    while i < hi and i < len(d):
        n = OPCODE_LEN[d[i]]
        if i + n > hi or i + n > len(d):
            i += 1
            continue
        starts.append(i)
        i += n + inline_arg_len(d, i)
    return starts


def window_before(d: bytes, starts: list, site: int, back: int = WINDOW):
    """(the instructions behind `site` inside the window, why it ended).

    The instruction starts are the same list the site was found in, so the
    window is contiguous with the site's own framing: a `mov p2,#imm` this
    finds is one the anchored decode actually reaches, not one a fresh walk
    from some other byte happens to step onto.

    `why` is which of the two guards ended it -- the byte budget or the
    start of the region -- because a window that ran out and one that found
    everything and stopped at the region edge are otherwise the same list of
    offsets, and the difference decides whether an unresolved row means
    "nothing was there" or "the look stopped"."""
    k = bisect.bisect_left(starts, site)
    out, why = [], None
    while k > 0:
        at = starts[k - 1]
        if site - at > back:
            why = window_end(back)
            break
        out.append(at)
        k -= 1
    return out[::-1], why or REGION_START


def resolve(p2, rn, reg: int, why: str) -> str:
    """The `xaddr` cell: the full address, or which half is missing and why.

    `p2` is a p2_write() pair and `rn` the rn_load() immediate, either None
    when the window held no such instruction. A cell that said only
    "unresolved" would read as a verdict about the byte; this one names each
    half separately -- "P2: last write is `mov p2,acc`" beside "Rn: no
    `mov r0,#imm` in the window" -- which is the evidence the issue asked to
    be reported and the reason a clean result is citable."""
    if p2 is not None and p2[1] is not None and rn is not None:
        return f"0x{(p2[1] << 8) | rn:04X}"
    halves = []
    if p2 is None:
        halves.append(f"P2: {NO_P2_WRITER}")
    elif p2[1] is None:
        halves.append(f"P2: last write is `{p2[0]}`")
    else:
        halves.append(f"P2: literal 0x{p2[1]:02X}")
    if rn is None:
        halves.append("Rn: " + NO_RN_LOAD.format(reg=reg))
    else:
        halves.append(f"Rn: literal 0x{rn:02X}")
    return "unresolved; " + "; ".join(halves) + f" ({why})"


def unresolved_by(site: dict) -> str:
    """Which half left a site unresolved, from the structured row.

    Read off the row rather than back out of the `xaddr` cell, because that
    cell is prose this module formats and re-parsing a cell in order to count
    the thing it says is how a summary and a table come to disagree.

    Three buckets, cut on the page half, because that is the half the issue
    is about: the literal `mov p2,#imm` is the only write that can supply a
    page, so "the window held a write and it was one of the other seventeen"
    and "the window held no write at all" are different findings and a table
    that merged them would read as one. The low half is not a bucket of its
    own -- a site that has a literal `Rn` and no `P2` is in the first, and
    the per-row `xaddr` cell says which half it was. The third bucket is
    reachable only for a site whose page is literal and whose low byte is
    not, which is why a resolved site never lands in it; the caller filters
    on the cell and this does not need to."""
    p2 = site["p2"]
    if p2 is None:
        return NO_P2_WRITER
    if p2[1] is None:
        return f"P2 window's last write is `{p2[0]}`"
    return "P2 half literal, Rn half not found"


def sites(d: bytes, pd_verified: bool, back: int = WINDOW) -> list:
    """Every anchored `movx @Ri` site, with the row this tool prints for it.

    One function so the `--csv` table, the summary and the `--page` answer
    are three views of the same walk and cannot disagree about the
    population or about a site's region. `region_of()` decides the region and
    returns `unknown` rather than `pd-image` when the marker is absent, so a
    dump that is not this one gets the refusal instead of a borrowed
    conclusion."""
    out = []
    for name, lo, hi, base, _how in REGIONS:
        if base is None:
            # No runtime base: the two `erased` rows of REGIONS, and the one
            # definition of what they are stays REGIONS'. 0xFF is `mov r7,
            # direct` on a 8051, so a walk through them would decode filler
            # as instructions and report it as sites.
            continue
        starts = anchored_starts(d, lo, hi)
        for site in starts:
            op = d[site]
            if op not in MOVX_RI:
                continue
            form, reg = MOVX_RI[op]
            behind, why = window_before(d, starts, site, back)
            # Nearest first, because the *last* write before the site is the
            # one in force at it -- a `mov p2,#imm` four instructions back
            # behind a `mov p2,acc` supplies nothing.
            p2 = rn = None
            for at in reversed(behind):
                if p2 is None:
                    p2 = p2_write(d, at)
                if rn is None:
                    rn = rn_load(d, at, reg)
                if p2 is not None and rn is not None:
                    break
            onto, over = converges_from(d, site)
            out.append({
                "offset": site,
                "region": region_of(site, pd_verified)[0],
                "runtime": runtime_addr(site, pd_verified),
                "form": form,
                "register": reg,
                "frame_onto": onto,
                "frame_over": over,
                "p2": p2,
                "rn": rn,
                "xaddr": resolve(p2, rn, reg, why),
                "window": " ; ".join(
                    " ".join(mnemonic(d, at).split()) for at in behind),
            })
    return out


def raw_sites(d: bytes) -> list:
    """Every offset whose byte is one of the four, framed or not.

    Reported, never tabulated. It exists so the summary can print the
    anchored count beside the count a two-byte byte scan would have found,
    which is the only way a reader can see that the 0xE2 inside somebody's
    `mov dptr,#imm16` is not a site."""
    return [i for i, b in enumerate(d) if b in MOVX_RI]


def sfr_literal_counts(d: bytes) -> collections.Counter:
    """`mov <direct>,#imm` byte-pair counts for CONTROL_SFRS, over the file.

    The control the `P2` zero needs beside it. The query is the same
    two-byte-plus-immediate for every entry, so the count for 0xF0 is what
    says the query works, and the count for 0xA0 is what says the form is not
    found by it in this image."""
    out = collections.Counter()
    for direct, _name in CONTROL_SFRS:
        out[direct] = sum(1 for i in range(len(d) - 2)
                          if d[i] == 0x75 and d[i + 1] == direct)
    return out


def p2_writer_counts(d: bytes) -> collections.Counter:
    """Which P2-writing encodings the anchored decode reaches, and how
    often -- over the whole image, both programs, deliberately not split by
    region because this is a census of the *form* and not of a byte."""
    out = collections.Counter()
    for _name, lo, hi, base, _how in REGIONS:
        if base is None:
            continue
        for at in anchored_starts(d, lo, hi):
            found = p2_write(d, at)
            if found is not None:
                out[found[0]] += 1
    return out


def writer_census(counts: collections.Counter) -> list:
    """[(name, count)] for the P2 encodings, the literal one first.

    Eighteen rows of mostly zeroes is a wall, and a wall is how a reader
    stops looking half way down it -- so the literal row is pinned to the
    top (it is the one the issue asked about) and the rest are printed only
    where they occur, tallest first. The summary prints the count of the
    zeros beside them, so a row that is missing is a stated zero rather than
    an omission."""
    names = [r[3] for r in P2_WRITERS]
    rest = sorted(((n, counts.get(n, 0)) for n in names
                   if n != P2_LITERAL and counts.get(n, 0)),
                  key=lambda pair: (-pair[1], pair[0]))
    return [(P2_LITERAL, counts.get(P2_LITERAL, 0))] + rest


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write.

    `--check` diffs the same bytes this prints, and the tool's contract is
    that it writes nothing but stdout. The columns are the site's identity,
    the framing evidence, the two halves' evidence, the resolution and the
    window's own decode -- in that order, so the last three together let a
    reader re-derive the cell before it from the row rather than taking it
    on trust."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file_offset", "runtime", "region", "form", "frame_onto",
                "frame_over", "p2", "rn", "xaddr", "window"])
    for r in rows:
        p2 = r["p2"]
        w.writerow([
            f"0x{r['offset']:05X}",
            f"0x{r['runtime']:04X}" if r["runtime"] is not None else "",
            r["region"], r["form"],
            r["frame_onto"], r["frame_over"],
            "none in window" if p2 is None else
            (f"{p2[0]} = 0x{p2[1]:02X}" if p2[1] is not None else p2[0]),
            "none in window" if r["rn"] is None else f"literal 0x{r['rn']:02X}",
            r["xaddr"], r["window"]])
    return buf.getvalue()


def page_report(rows: list, page: int) -> int:
    """The `--page` answer: who resolves onto `page`, per image.

    Returns non-zero when the page is reached by nothing at all, so a
    scripted caller can use it. The tally is of *resolved* addresses, and a
    site this tool could not resolve is not in it and is not counted as
    evidence against the page -- the two are counted separately in the
    printed lines above this, which is what stops a `movx @Ri` in the PD
    image reading as an EC-side reference to a 0x07xx byte."""
    per_image = collections.defaultdict(list)
    for r in rows:
        if r["xaddr"].startswith("unresolved"):
            continue
        addr = int(r["xaddr"][2:], 16)
        if addr >> 8 == page:
            per_image[r["region"]].append((addr, r["offset"]))
    print(f"page 0x{page:02X}, by the sites this tool can resolve:\n")
    for region in MAIN_EC_REGIONS + (PD_REGION,):
        hits = sorted(per_image.get(region, []))
        if not hits:
            print(f"  {region:<9} 0  -- not reached by any resolvable site")
            continue
        tally = collections.Counter(addr for addr, _ in hits)
        for addr, count in sorted(tally.items()):
            where = ", ".join(f"0x{off:05X}" for a, off in hits if a == addr)
            print(f"  {region:<9} {count:>2} site(s) on 0x{addr:04X}  ({where})")
    main_ec = sum(len(per_image.get(r, [])) for r in MAIN_EC_REGIONS)
    if not main_ec:
        print(f"\nSo the main EC reaches page 0x{page:02X} by this method "
              "nowhere, and the PD\nimage's indirect XDATA is a different "
              "program's byte either way.")
    return 0 if main_ec else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout instead "
                         "of the summary")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against a committed table and exit "
                         "non-zero on any difference (default: "
                         f"{repo_path(SITES_CSV)})")
    ap.add_argument("--page", metavar="0xNN",
                    help="answer the issue's page question: which sites "
                         "resolve onto this XDATA page, per image. Exits "
                         "non-zero when the main EC reaches it nowhere")
    ap.add_argument("--window", type=int, default=WINDOW, metavar="N",
                    help=f"backward window in bytes (default: {WINDOW}, the "
                         "same default disasm8051.converges_from() uses)")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF are reported as region 'unknown', "
              "not as another image's\n", file=sys.stderr)

    rows = sites(d, pd_verified, args.window)
    table = csv_table(rows)
    if args.check is not None:
        return check_table(table, args.check)
    if args.csv:
        sys.stdout.write(table)
        return 0

    raw = raw_sites(d)
    by_region = collections.Counter(r["region"] for r in rows)
    raw_by_region = collections.Counter(region_of(i, pd_verified)[0] for i in raw)
    resolved = [r for r in rows if not r["xaddr"].startswith("unresolved")]

    print(f"{len(raw)} raw `movx @Ri` opcode bytes in {len(d)} bytes of image, "
          f"of which the anchored\ndecode reaches {len(rows)} as an "
          f"instruction start ({len(raw) / max(len(rows), 1):.1f}x). The raw "
          "count is a byte scan:\n0xE2, 0xE3, 0xF2 and 0xF3 are common "
          "operands, not just opcodes.\n")
    for region in MAIN_EC_REGIONS:
        print(f"  {region:<9} {by_region.get(region, 0):>4} anchored site(s)   "
              f"{raw_by_region.get(region, 0):>4} raw byte(s)")
    # The two totals, on their own lines and never as one number: a `movx @Ri`
    # in the PD image is another program's byte, and this is the printout that
    # says so every run rather than the docstring.
    for label, regions in (("main EC", MAIN_EC_REGIONS),
                           ("PD image", (PD_REGION,))):
        print(f"  {label:<9} {sum(by_region.get(r, 0) for r in regions):>4} "
              f"anchored site(s)   "
              f"{sum(raw_by_region.get(r, 0) for r in regions):>4} raw byte(s)")
    print("  main EC = common area + CODE banks 0 and 1. PD image is a "
          "separate ITE8850-PD\n  program with its own XDATA map, and is "
          "never added to the line above.\n")

    print(f"Of the {len(rows)} anchored sites, {len(resolved)} resolve to a "
          f"full XDATA address and\n{len(rows) - len(resolved)} are "
          "unresolved, by what their backward window held:\n")
    reasons = collections.Counter(unresolved_by(r) for r in rows
                                  if r["xaddr"].startswith("unresolved"))
    for reason, count in sorted(reasons.items()):
        print(f"  {count:>4}  {reason}")

    p2_forms = p2_writer_counts(d)
    print("\nThe `P2` byte, over the whole image, by anchored encoding -- the "
          "evidence a site is\nresolved against. The literal row first; the "
          "rest only where they occur:\n")
    census = writer_census(p2_forms)
    for name, count in census:
        print(f"  {count:>5}  {name}")
    print(f"  {len(P2_WRITERS)} encodings write 0xA0-0xA7 on an 8051; "
          f"{len(p2_forms)} of them occur in this\n  image and the other "
          f"{len(P2_WRITERS) - len(p2_forms)} are not found by this method.")

    control = sfr_literal_counts(d)
    print("\nThe control for the `P2` zero, the same two-byte-plus-immediate "
          "query over the same file:\n")
    for direct, name in CONTROL_SFRS:
        mark = "   <- the page half" if direct == 0xA0 else ""
        print(f"  {control[direct]:>5}  mov {name},#imm{mark}")
    if control[0xA0] == 0:
        print(f"\n`mov p2,#imm` occurs {control[0xA0]} times in this image "
              f"against {control[0xF0]} for `mov b,#imm`\nthrough the same "
              "query. That is a property of the image and not of this scan, "
              "and it is a\nstatement about the *form*: it is not a statement "
              "that the EC never sets P2.")

    if args.page is not None:
        print()
        return page_report(rows, int(args.page, 16))
    print(f"\n{repo_path(SITES_CSV)} is the per-site table; `--csv` prints it "
          "and `--check` diffs this\nrun against it. "
          "ec/annotations/indirect-xdata-sites.md is the write-up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
