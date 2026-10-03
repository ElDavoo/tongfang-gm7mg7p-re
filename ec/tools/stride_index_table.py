#!/usr/bin/env python3
"""Measure the CODE table the `0x4900` stride constructions index: how many
sites build an address into it, over what byte run it extends, what record
geometry the two strides imply, and what the committed listings pass as the
index.

**Why this is a new file and not another mode on `decode_index_table.py`.**
That tool censuses one *dispatch* table -- a run of 3-byte entries naming the
addresses a `switch` jumps to, read by a reader it recognises by shape. What
is at `0x4900` is not that: its readers are eleven bytes each and end in
`mov DPL,A / clr A / addc A,#0x49`, with no code window and no jump table, so
none of that tool's entry-layout machinery applies to it. It also has its own
`--check`/`--self-test` contract and its own committed table, and a new mode
on it would have to answer for both. CLAUDE.md's "a new tool is a new file"
is the same rule; this paragraph is why it is the right reading here.

**The construction, and the eleven bytes are load-bearing.** The shape is
`mov B,#stride / mul AB / add A,#off / mov DPL,A / clr A / addc A,#base_hi`,
and the last two instructions are what make `base_hi` a *page* rather than a
guess: `clr A` (0xE4) clears the carry on an 8051, so `addc A,#base_hi` is
`base_hi` whatever the low byte did, and the index is truncated to eight bits
by the `mul AB` before it. **The `mov DPH,A` that finishes the pointer is
*not* part of the shape.** Most of the sites this image's common area holds
`ret` with the page sitting in the accumulator and the `lcall` that follows
stores it; the rest store it themselves. A scan that *required* the store
would find only the sites that do, and would report the majority absent,
which is `docs/findings.md` §4d's shape. `--sites` therefore anchors on the
eleven bytes and *reports* the store as a column.

**A scan is an upper bound, and each match is cross-checked.** Every offset
this tool prints comes from a linear byte scan, which is the same caveat
`audit_call_targets.py` §1 and `bucket-c-codemap.md` §1 carry, and the same
remedy: `listing` names the committed `.asm` that carries the site's own
bytes as an instruction. A match in a table nobody has walked into is not yet
a site, and the column is what tells the two apart. Nothing here decides that
a byte is data; `--boundary` reports what a walk did with the boundaries and
nothing more.

**The record count is two measurements and never one.** 15 and 21 are both
odd, so `A*stride mod 256` is a bijection over all 256 index values and the
construction bounds nothing: any 8-bit index is admitted, and the number of
records a walk *can* reach is not a property of the table. So `--records`
prints two figures separately and labels each for what it is -- how many whole
records the declared byte run holds at that stride, and how far past the run
the eight-bit walk can be taken before it leaves it. A reader who wants one
"record count" is looking for something the arithmetic does not supply.

**An even stride is refused rather than measured.** `A*stride mod 256` is a
bijection only when the stride is odd. At an even stride the index maps onto
half the offsets, so the record count a stride implies is a different claim
with a different meaning, and a tool that printed it beside an odd one would
be comparing two different things. `--records` refuses with the reason.

**The index range is a property of the listings, not of the firmware.**
`--index-range` reports, per site, the register the preceding instruction
feeds `A` with and what the committed `.asm` shows at each `lcall` that
reaches it. Every one of those is a *run-time* value on this image -- a
register, or an XDATA byte -- and the output says "no constant in the listing"
where that is the answer rather than inferring a range. What the firmware can
actually pass is not in any of these files.

**Nothing here measures the byte.** Every input is a committed file, no
register is read, no `status:` in `../annotations/registers.yaml` moves, no
`0x4900` row is added to it (`0x4900` is a CODE address and that map is
XDATA-scoped), and no hardware or Windows is needed. A zero anywhere is "not
found by this method", never "absent".

Usage:
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --sites --base 0x49
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --at 0x4900 --len 0xD8
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --records --stride 15
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --index-range
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --boundary
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --check
    python3 stride_index_table.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import bisect
import collections
import csv
import difflib
import hashlib
import io
import os
import re
import sys

from disasm8051 import converges_from, mnemonic
from trace_xdata_refs import (PD_MARKER, REGIONS, region_of, repo_path,
                              runtime_addr)
from walk_branch_arms import CUTS, descend

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
DECOMPILED = os.path.join(HERE, os.pardir, "decompiled")
INDEX_CSV = os.path.join(HERE, os.pardir, "decompiled", "index.csv")
CALLEES_CSV = os.path.join(HERE, os.pardir, "annotations",
                           "call-graph-callees.csv")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
WRITEUP = os.path.join(REPO, "docs", "findings", "4900-stride-table.md")

# --- the construction ------------------------------------------------------
#
# Eleven bytes, as (offset, opcode) pairs rather than a packed pattern, so a
# reader can see which byte is which without counting hex digits and the
# table can name each one in the refusal messages. Every opcode here is one
# this image's own listings decode, so none of them is a spelling invented for
# the scan.
CONSTRUCTION = (
    (0, 0x75, "mov B,#stride"),       # 0x75 0xF0 nn -- opcode at 0
    (3, 0xA4, "mul AB"),
    (4, 0x24, "add A,#base_off"),     # 0x24 nn     -- opcode at 4
    (6, 0xF5, "mov DPL,A"),           # 0xF5 0x82   -- opcode at 6
    (8, 0xE4, "clr A"),
    (9, 0x34, "addc A,#base_hi"),     # 0x34 nn     -- opcode at 9
)
CONSTRUCTION_LEN = 11
# The two bytes a `mov DPH,A` adds, checked but not required -- see the module
# docstring. Reported as a column so a reader can see which sites complete the
# pointer and which leave the page in the accumulator.
DPH_STORE = (0xF5, 0x83)

# The three operand bytes, named once so the scan and the suite read the same
# offsets rather than each counting them.
STRIDE_BYTE = 2
BASE_OFF_BYTE = 5
BASE_HI_BYTE = 10

# --- the block this tool is about ------------------------------------------
#
# All four are the write-up's, and `--check` re-derives each of them from the
# image. The byte run is declared rather than discovered because the tool's
# own boundary argument is a walk's, and a walk's boundary is a claim with a
# reason beside it -- `docs/findings/4900-stride-table.md` §3 carries the
# reason and `--boundary` re-runs the walk. What the tool will not do is
# quietly re-measure the extent and report agreement with itself.
BLOCK_BASE = 0x4900
BLOCK_START = 0x494E
BLOCK_END = 0x4A25              # inclusive; 0x4A26 is the next call target
# The base high byte the common-area sites agree on, as `--sites --base`
# spells it. `addc A,#0x49` with the carry `clr A` cleared is `0x4900 + ...`,
# which is what makes one block rather than a family of lookups.
BLOCK_BASE_HI = 0x49
# The stride every one of those twenty uses for the first field, and the other
# stride the same twenty also use. Named because the record framing has to be
# computed at each, and a reader should not have to find them to do that.
STRIDES = (15, 21)
# The width the run tiles at, and the step every base offset in it advances
# by. This is a hypothesis about the *contents*, so it is a column and not a
# filter: `entry_tags()` measures whether the bytes at these offsets really
# are a small closed set and prints the answer rather than assuming it. Every
# base offset the constructions below `0x4B00` use advances by exactly this
# step, which is the observation the record framing rests on.
ENTRY_LEN = 2
FIELD_STEP = 2

# Where the walk figure is reported from, as (label, address). The first is
# the run's own first byte; the second is the `+0xCC` base that the `0x43A5`
# sequence walks from, which the grid `--records` prints at stride 15 places at
# record 8 field 6 rather than at record 0. They give different answers and
# both are printed, because a reader shown only one would take it for the
# record count -- and because a walk anchored at a grid's record 0 reads as
# that grid's count, which this one is not.
ANCHORS = (("run_start", BLOCK_START), ("base_cc", 0x49CC))
# The same two anchors, spelled for a reader. Kept beside ANCHORS rather than
# inside it because the figure keys are parsed as `key = value` and a key with
# a space in it is a line the parser refuses.
ANCHOR_LABELS = {"run_start": "the run's first byte",
                 "base_cc": "the +0xCC base"}

# The image-wide population, per region, is a count over committed bytes and
# is stated once in the write-up beside the command that prints it. Nothing
# else here restates it.
REGIONS_MAIN_EC = ("common", "bank0", "bank1")

# --- refusals --------------------------------------------------------------
#
# Each token is a distinct claim, so each is its own message and its own case
# in the suite. They are written against the mistake they catch rather than
# against the argument they are.
NOT_COMMON = ("base 0x%04X is not in the common area; the common area is "
              "0x0000-0x7FFF and a bank window's runtime address does not "
              "name a file offset")
EVEN_STRIDE = ("stride %d is even, so A*stride mod 256 is a bijection only "
               "for an odd stride; the record count an even stride implies is "
               "a different claim from the one an odd one makes, and this "
               "tool refuses to print the two beside each other")
OVERRUN = ("a run of %d record(s) at stride %d from 0x%04X ends at 0x%04X, "
           "which is outside the image's 0x%04X")
NO_BLOCK = ("no fenced stride-index-table block in %s; --check needs the "
            "figures the write-up declares, not this tool's own constants")
NO_FIRMWARE = "%s: no such file"

# The fence the write-up declares its figures in. A fenced block rather than a
# prose paragraph for `census_test_line_pins.py`'s reason: a number inside a
# fence is a transcript of a run, not a claim in prose, and the census is
# about prose.
BLOCK_LANG = "stride-index-table"
FIG_LINE = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+)\s*=\s*(?P<value>\S+)\s*$")

# --- listings --------------------------------------------------------------
#
# `ec/decompiled/index.csv`'s `addr` column is the *file offset* of the
# function's bytes, not a runtime address: `bank1/4A26.asm` and the common
# area's 0x4A26 are the same bytes, and the `program` column names which
# program's image seeded the export. That is why a coverage lookup below is a
# sort and a bisect on one number with no bank arithmetic in it, and why a
# site's owning function can be named from any program.
NO_FUNCTION = "no function covers this offset"
LISTED = "confirmed in a committed listing"
UNLISTED = "not covered by any committed listing"

# The one program in `index.csv` whose `addr` is not a file offset. Named
# because `owning_rows()`'s refusal to read it as one is the exception that
# makes the rest of that function's arithmetic true.
PD_SCOPE = "pd"

# A listing line: `<addr> <bytes> <mnemonic>`. The bytes are variable width
# (`mov r7,a` is one, `mov dptr,#0x0a17` is two), and the address is a bare
# four-digit hex field, so the mnemonic is the rest of the line.
# A listing line is `<addr>  <bytes>  [- -]  <mnemonic>`. The `- -` is
# Ghidra's empty-operand placeholder and appears only where an instruction is
# one byte long, so the byte column is "one or more two-hex-digit groups" and
# the placeholder is optional rather than counted: a parser that expects it
# skips every one-byte instruction, and those are most of a stride
# construction's own neighbours.
LISTING_LINE = re.compile(
    r"^(?P<addr>[0-9A-Fa-f]{4,6})\s+(?P<bytes>(?:[0-9a-f]{2}\s+)+)"
    r"(?:-\s+-\s+)?(?P<mn>\S.*?)\s*$")

# The instructions that end a linear block in a listing, and so bound the
# backward walk that finds a site's index load. Taken as text because the
# listings are the source here and the mnemonics are their own spelling.
TERMINATORS = ("ret", "reti", "ljmp", "ajmp", "jmp @a+dptr")

# `mov A,#imm`, the one encoding the index-load walk reads as a literal index.
# Spelled as its opcode because the walk tests the byte and not the listing's
# mnemonic, and the listing spells it `mov a,#0x01` with its own padding.
LITERAL_ACC = 0x74


def squash(text: str) -> str:
    """A listing's mnemonic column with its padding collapsed.

    The listings pad operands to a column, so `mov      A, R6` and `mov a,r6`
    are one instruction in two spellings. Nothing matches on the text, so this
    is only so a cell a reader compares against `disasm8051.py` output reads
    the same in both.
    """
    return " ".join(text.split())


def norm(d: bytes, at: int) -> str:
    """`mnemonic()`'s text, whitespace-normalised.

    `computed_dptr_sites.norm()`'s reason: the renderer pads operands to a
    column, so the same instruction reads `mov a,r6` in one cell and
    `mov  a,r6` in another and a cell compared against a listing does not
    match.
    """
    return " ".join(mnemonic(d, at).split())


# --- the census ------------------------------------------------------------

def site_at(d: bytes, off: int, pd_verified: bool):
    """The row for one construction at `off`, or None.

    One instruction in, one verdict out, so `--sites`, `--records`,
    `--index-range` and the summary are four views of one walk and cannot
    disagree about the population. Every byte is bounds-checked here rather
    than left to the caller's loop, for `trace_xdata_refs.is_dptr_rebuild()`'s
    reason: a truncated buffer has to get a verdict and not an `IndexError`.
    """
    if off < 0 or off + CONSTRUCTION_LEN > len(d):
        return None
    for at, op, _name in CONSTRUCTION:
        if d[off + at] != op:
            return None
    # `mov B,#stride` and `mov DPL,A` name their operand byte, so those two
    # opcodes appear twice in the pattern and each is only half a match. Both
    # are checked here rather than counted by the loop above, which is why the
    # operand bytes are absent from CONSTRUCTION rather than present and
    # unchecked.
    if d[off + 1] != 0xF0 or d[off + 7] != 0x82:
        return None
    stride = d[off + STRIDE_BYTE]
    base_off = d[off + BASE_OFF_BYTE]
    base_hi = d[off + BASE_HI_BYTE]
    end = off + CONSTRUCTION_LEN
    has_dph = (end + 1 < len(d) and d[end] == DPH_STORE[0]
               and d[end + 1] == DPH_STORE[1])
    name = region_of(off, pd_verified)[0]
    return {
        "offset": off,
        "runtime": runtime_addr(off, pd_verified),
        "region": name,
        "stride": stride,
        "base_off": base_off,
        "base_hi": base_hi,
        # The address the construction's *first* byte lands on with an index of
        # zero, which is the thing every base offset in a stride family has to
        # agree about before they are one table. Carried rather than computed
        # at print time so `--sites` and `--records` cannot compute it
        # differently.
        "base": (base_hi << 8) | base_off,
        "dph_store": has_dph,
        "form": " ; ".join(norm(d, off + at) for at, _op, _n in CONSTRUCTION),
    }


def scan(d: bytes, pd_verified: bool, base_hi=None) -> list:
    """Every construction a linear byte scan finds, in offset order.

    `base_hi` narrows to the sites that build an address into one page, which
    is the question `0x4900` is; with no value the whole image is scanned and
    the population is per region, so a reader can see what the narrowing hides.

    **This is an upper bound and the column beside it is the reason.** A byte
    scan finds the eleven bytes inside anybody's immediate operand as readily
    as in an instruction stream, which is the caveat `audit_call_targets.py`
    §1 carries. `listing` says whether a committed `.asm` carries this site's
    own bytes as an instruction, and a row whose cell reads `UNLISTED` is a
    candidate this tool has not corroborated.
    """
    out = []
    for off in range(len(d) - CONSTRUCTION_LEN):
        row = site_at(d, off, pd_verified)
        if row is None:
            continue
        if base_hi is not None and row["base_hi"] != base_hi:
            continue
        out.append(row)
    return out


def owning_rows(index_path: str = INDEX_CSV) -> list:
    """[(start, size, scope, addr, name)] sorted by start, from index.csv.

    For every program but the PD image, the `addr` column is the *file offset*
    of the function's bytes: `bank1/4A26.asm` and the common area's 0x4A26
    are the same bytes, and `program` names which image seeded the export. So
    a coverage question about the common area is `bisect` and no bank
    arithmetic at all.

    The `pd` rows are dropped, and this is the exception that makes the rest
    of the paragraph true rather than mostly true: the PD image is a separate
    program at file 0x20000 with its own address space, so `pd 4402` is file
    0x24402 and a lookup that treated its `addr` as a file offset finds a
    common-area function for it. Keeping them would put a second program's
    function over a first program's bytes, which is
    `trace_xdata_refs.py`'s first point about a file-wide count.

    Rows with no `size` are dropped too: an unmeasured extent cannot be said
    to cover a byte.
    """
    rows = []
    with open(index_path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["program"] == PD_SCOPE:
                continue
            try:
                start = int(r["addr"], 16)
                size = int(r["size"] or 0)
            except ValueError:
                continue
            if size <= 0:
                continue
            rows.append((start, size, r["program"], r["addr"], r["name"]))
    rows.sort(key=lambda t: (t[0], t[2]))
    return rows


def owner_of(off: int, rows: list) -> str:
    """`scope addr name` of the row whose extent covers `off`, or the refusal.

    The innermost row wins, so a one-byte placeholder row placed just below a
    real function does not swallow it. Ties at one address are broken by
    `common` first: the same bytes are exported once per program whose image
    seeded them, and the common-area spelling is the one a reader of the
    common area wants.
    """
    starts = [r[0] for r in rows]
    i = bisect.bisect_right(starts, off)
    best = None
    for start, size, scope, addr, name in reversed(rows[:i]):
        if start + size <= off:
            continue
        if best is None or start > best[0]:
            best = (start, scope, addr, name)
        elif start == best[0] and best[1] != "common" and scope == "common":
            best = (start, scope, addr, name)
    if best is None:
        return NO_FUNCTION
    return f"{best[1]} {best[2]} {best[3]}"


def listing_stream(off: int, rows: list) -> list:
    """[(addr, mnemonic text)] for the contiguous listings ending at `off`.

    The function a site sits in is often exported one byte at a time, because
    that is how the call-target census that cut it saw it: `common 0x4A42` is
    eleven bytes and the `mov A,R1` that feeds it is its own one-byte row at
    `0x4A41`. A lookup that read only the site's own listing would find
    nothing in front of it and report "no index load" for a site whose index
    load is a committed line one file away. So this walks back over every row
    that begins exactly where the previous one ended, and stops at the first
    gap -- a gap is a boundary the export has said something about, and
    reading past one would be reading a different function.
    """
    starts = [r[0] for r in rows]
    i = bisect.bisect_right(starts, off)
    stream, at = [], None
    j = i - 1
    while j >= 0:
        start, size, scope, addr, _name = rows[j]
        if at is not None and start + size != at:
            break
        if start + size <= off and at is None:
            # The site's own row does not cover it: the site is in a gap the
            # export says nothing about, so nothing here is its listing.
            j -= 1
            if j >= 0 and rows[j][0] + rows[j][1] != start:
                break
            continue
        lines = read_listing(scope, addr)
        if not lines:
            break
        stream = lines + stream
        at = start
        j -= 1
    return stream


def listing_path(scope: str, addr: str) -> str:
    return os.path.join(DECOMPILED, scope, addr + ".asm")


def read_listing(scope: str, addr: str) -> list:
    """[(addr, mnemonic text)] for one committed listing, or [].

    Parsed from the listing rather than re-decoded from the image on purpose:
    the question `--sites` asks of this file is whether *a committed listing*
    carries the site's bytes as an instruction, and re-decoding would answer
    a different one -- what this tool's own decoder makes of them.
    """
    path = listing_path(scope, addr)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return []
    return listing_fields(text)


def listing_covers(row: dict, index_rows: list) -> str:
    """LISTED or UNLISTED -- for one construction site.

    A site is LISTED when a committed `.asm` carries an instruction line at the
    site's own offset. That is the cross-check that turns a byte scan into a
    census, and it is deliberately about the *instruction* at the offset and
    not about a listing that merely spans it: a site inside a function the
    export cut wide is not thereby corroborated, and the site count beside it
    says how many were.
    """
    stream = listing_stream(row["offset"], index_rows)
    if not stream:
        return UNLISTED
    return LISTED if any(at == row["offset"] for at, _mn in stream) else UNLISTED


# --- the record framing ----------------------------------------------------

def check_stride(stride: int) -> None:
    """Refuse an even stride, with the bijection as the reason.

    `A*stride mod 256` maps the 256 index values onto all 256 offsets only
    when the stride is odd. At an even stride the index reaches half of them,
    so "how many records does the walk hold" is a different question at each
    parity and a table that printed both beside each other would be comparing
    two different quantities. The suite carries this refusal as a case.
    """
    if stride <= 0:
        raise SystemExit(f"error: stride {stride} is not a positive length")
    if stride % 2 == 0:
        raise SystemExit("error: " + EVEN_STRIDE % stride)


def check_block(base: int) -> None:
    """Refuse a base outside the common area, with the map as the reason.

    `REGIONS` gives the common area base 0 and the two bank windows base
    0x8000, so a bank runtime address is not a file offset and every offset
    below is computed from one. Taking a `--base` outside the common area
    would silently compute record arithmetic in a bank window against bytes
    this tool never read.
    """
    lo, hi = region_bounds()
    if not lo <= base <= hi:
        raise SystemExit("error: " + NOT_COMMON % base)


def region_bounds() -> tuple:
    """(first, last) file offset of the common area, off REGIONS itself.

    Read from `REGIONS` rather than written here so a fourth mapped region
    cannot make this table disagree with the one the rest of the repository
    uses, and so the refusal above names the same bounds the walk assumes.
    """
    name, lo, hi, base, _how = next(r for r in REGIONS if r[0] == "common")
    if base != 0:
        raise SystemExit("error: the common area is not at runtime base 0 in "
                         "REGIONS, so a file offset is not its address")
    return lo, hi - 1


def record_frame(base: int, start: int, end: int, stride: int, off: int):
    """(record index, field offset) for the address `base + off` lands on.

    `base` is the *page* base the construction's `add A,#off` is added to --
    `0x4900` for every site on this block -- and `off` is that
    construction's own `base_off`, so `base + off` is the address the site
    points at and the record it falls in is a fact about that address.

    The grid is counted from `start`, the run's first byte, and not from
    `base`. That is a choice with a visible consequence and it is named here
    because the two anchors disagree by 126 bytes: `start` is where `+0x4E`
    lands, so record 0 field 0 is the `+0x4E` address and `+0xCC` is record 8
    field 6 at stride 15 -- not record 0. `start` rather than `base` because a
    grid counted from `base` would put record 0 below the run, in the code
    above it, and the lowest offset any site here uses is `+0x4E`.

    None when `base + off` is outside the declared run, which is the honest
    answer for a base offset that lands in the code rather than in the table.
    The two numbers are the whole of the "record heads, mid-record offsets, or
    two separate sub-tables" question: a field offset that is neither 0 nor a
    small constant is a mid-record offset, and the record index says which
    record.
    """
    rel = base + off - start
    if rel < 0 or rel > end - start:
        return None
    return divmod(rel, stride)


def records_in_run(start: int, end: int, stride: int) -> tuple:
    """(whole records, bytes left over) for the byte run, at `stride`.

    The first of the two record figures, and it is a statement about the run
    and not about the walk: how many whole records of that stride fit inside
    the bytes the block is declared to be. `walk_reaches()` is the second,
    and the module docstring is why they are not merged.
    """
    span = end - start + 1
    return divmod(span, stride)


def walk_reaches(base: int, start: int, end: int, stride: int,
                 image_len: int = None) -> int:
    """How many steps the walk takes before it leaves the declared run.

    The second of the two record figures, and the one the arithmetic is
    actually about: the largest `k` with `base + k*stride` still inside the
    run. Because an odd stride is a bijection, this is a statement about where
    *this* grid runs out, not about how many indices the construction admits
    -- which is all 256 of them, whatever this returns.

    A run declared past the end of the image is refused rather than counted.
    The mistake is a mistyped extent, and without the check it reads as a
    short table: the loop simply never enters, and the answer is a zero that
    looks like a measurement. `image_len` is what makes the two distinguishable.
    """
    check_stride(stride)
    if image_len is not None and end >= image_len:
        raise SystemExit("error: " + OVERRUN % (0, stride, start,
                                                end, image_len))
    k, off = 0, base
    while start <= off <= end:
        k += 1
        off = (off + stride) & 0xFFFF
        if k > 0x10000:            # unreachable for an odd stride; a guard
            break
    return k - 1 if k else 0


def entry_tags(d: bytes, start: int, end: int) -> dict:
    """The bytes at each field offset of the run, and how many there are.

    The measurement behind the two-byte-entry claim: `fields` is the count of
    the run's even offsets and `tag_bytes` is the number of distinct values at
    them. A run of 2-byte entries with a small closed tag vocabulary gives a
    `tag_bytes` far below `fields`; a run that is really code gives something
    near 256. It is printed, never asserted, because what a tag *means* is
    `docs/findings/4900-stride-table.md` §6's open question and this tool
    declines to answer it.
    """
    fields = [start + k for k in range(0, end - start + 1, FIELD_STEP)]
    tags = collections.Counter(d[a] for a in fields if a < len(d))
    return {"fields": len(fields), "distinct_tags": len(tags),
            "tags": tags}


# --- the boundaries --------------------------------------------------------

BOUNDARY_BUDGET = 2000
BOUNDARY_DEPTH = 12

# What a walk verdict is, and what it is not. Three values, borrowed from
# `bucket_c_codemap.py`'s own: a byte the walk decoded as an instruction, a
# byte it did not reach for a reason it can name, and a walk that could not
# decide. A fourth is refused rather than rendered.
REACHED = "reached-by-walk"
NOT_REACHED = "not-reached"
UNKNOWN = "unknown"
VERDICTS = (REACHED, NOT_REACHED, UNKNOWN)

# `descend()`'s ends that mean it stopped, as opposed to finished. Its own
# `CUTS`, imported rather than re-spelled: an end this file wrote out in its
# own words would match nothing and every walk that gave up would report as
# `not-reached` -- a silent misclassification in the safe-looking direction,
# which is the direction `bucket_c_codemap.py`'s `UNKNOWN_REASONS` exists to
# stop.
GAVE_UP = CUTS


def walk_verdict(d: bytes, region: str, seed: int, target: int) -> str:
    """One of `VERDICTS` for `target`, given a forward walk from `seed`.

    A flow walk cannot tell code from a table it wandered into, so this never
    returns "is a table": it reports whether the walk decoded `target` as an
    instruction, whether it stopped at a `target` it cannot reach for a named
    reason, or whether it could not decide. That is `bucket_c_codemap.py`'s
    three verdicts on the same primitive, and the third exists so that "this
    method gave up here" is a reported outcome rather than a silent negative.
    """
    arm = descend(d, region, seed, None, BOUNDARY_DEPTH, BOUNDARY_BUDGET, True)
    for _start, insns in arm.blocks:
        for pc, _text in insns:
            if pc == target:
                return REACHED
    for why in arm.ends:
        if why in GAVE_UP:
            return UNKNOWN
    # No cut fired and the target was never decoded: the walk finished and
    # this byte is not in it. That is a negative the walk decided, which is
    # what separates it from the cell above.
    return NOT_REACHED


def boundary_report(d: bytes, index_rows: list) -> list:
    """[(what, at, cell)] -- the evidence at each end of the declared run.

    Two functions bracket the run -- the one whose extent ends below it and
    the one whose entry is the next byte above it -- and each is walked
    *forward* against both ends. That is the question the boundary actually
    turns on: whether the code on either side of the run reaches into it.
    Asking only the nearer function would be the tautology a walk from a
    function's own entry always answers, so it is not asked.

    `converges_from()` is reported beside each walk because it is framing
    evidence and cannot decide this on its own: a run of two-byte entries
    syncs onto every one of its own offsets, and on this run it does. The
    two-byte tiling is printed as a byte count and never as a verdict,
    because what an entry *means* is not this tool's question.
    """
    out = []
    below = owner_of(BLOCK_START - 1, index_rows)
    above = owner_of(BLOCK_END + 1, index_rows)
    ends = (("run start", BLOCK_START), ("byte after the run", BLOCK_END + 1))
    for label, at in ends:
        onto, over = converges_from(d, at)
        out.append((f"0x{at:04X} ({label})", at,
                    f"converges: {onto} of {onto + over} nearby anchors"))
    for side, text in (("bracketing function below the run", below),
                       ("bracketing function above the run", above)):
        if text == NO_FUNCTION:
            out.append((side, 0, NO_FUNCTION))
            continue
        seed = int(text.split()[1], 16)
        arm = descend(d, "common", seed, None, BOUNDARY_DEPTH,
                      BOUNDARY_BUDGET, True)
        stop = "; ".join(arm.ends) or "no terminator recorded"
        verdicts = ", ".join(f"{label} {walk_verdict(d, 'common', seed, at)}"
                             for label, at in ends)
        out.append((f"walk from {side}", BLOCK_START,
                    f"{text}, seed 0x{seed:04X}: {verdicts}; the walk ended "
                    f"at {stop}"))
    tags = entry_tags(d, BLOCK_START, BLOCK_END)
    span = BLOCK_END - BLOCK_START + 1
    out.append(("run length at the 2-byte entry width", BLOCK_END,
                f"{tags['fields']} entries cover it exactly "
                f"({tags['fields'] * ENTRY_LEN} of {span} bytes), with "
                f"{tags['distinct_tags']} distinct bytes at the entry offsets"))
    return out


# --- the index -------------------------------------------------------------

def index_load(d: bytes, off: int, index_rows: list) -> str:
    """What the committed listings put in A in front of the site at `off`.

    Read backwards through the stitched listing, stopping at the block's end,
    and reporting the last line that writes A. Three answers, kept apart
    because they are three different claims: a register name, a literal, or a
    read whose address this tool does not follow. A site whose predecessors
    no listing carries is `NO_INDEX_LOAD` rather than a guess -- the eleven
    construction bytes say nothing about what fed A.
    """
    lines = listing_stream(off, index_rows)
    if not lines:
        return NO_INDEX_LOAD
    starts = [at for at, _mn in lines]
    i = bisect.bisect_right(starts, off) - 1
    seen = 0
    while i >= 0 and seen < WINDOW:
        at, textline = lines[i]
        seen += 1
        head = textline.split(" ", 1)[0].lower()
        if head in TERMINATORS:
            break
        op = d[at] if at < len(d) else None
        if op in (0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF):
            return f"R{op - 0xE8} (from `{squash(textline)}` at 0x{at:04X})"
        if op == LITERAL_ACC:
            return f"literal {norm(d, at)} at 0x{at:04X}"
        if op in (0xE0, 0xE2, 0xE3, 0xF2, 0xF3, 0x93):
            return f"read, not a register (`{squash(textline)}` at 0x{at:04X})"
        i -= 1
    return NO_INDEX_LOAD


# How far back the index-load walk looks, in listing lines. Four is the width
# of the idiom `computed_dptr_sites.py` names for the same question -- a load,
# a hand-off, and the store beside it -- and a site whose load is further back
# than that is a `NO_INDEX_LOAD` rather than a widened window, because the
# number would then be this file's rather than the image's.
WINDOW = 4
NO_INDEX_LOAD = ("no index load in the committed listing's window; the "
                 "construction bytes say nothing about what fed A")


def call_sites(targets: set) -> dict:
    """{entry offset: [(caller listing, call offset)]} for `targets`.

    One pass over the committed `.asm` tree, because the question is "what do
    the listings pass", and the listings are the only committed record of
    that. A `lcall`/`acall` whose operand names a target is kept with the
    listing it sits in, so the reader can go and look at the instruction in
    front of it.

    The line is parsed by `listing_fields()` rather than by a regex of its
    own, because the byte column is one to three space-separated groups: a
    pattern that matches a single group finds a `lcall` in a two-byte line
    and misses it in a three-byte one, which is every `lcall` there is. That
    is not a hypothetical -- it is what this function did first, and it
    reported no callers at all for a site seven listings call.
    """
    found = {t: [] for t in targets}
    if not targets:
        return found
    for scope in sorted(os.listdir(DECOMPILED)):
        sub = os.path.join(DECOMPILED, scope)
        if not os.path.isdir(sub):
            continue
        for name in sorted(os.listdir(sub)):
            if not name.endswith(".asm"):
                continue
            path = os.path.join(sub, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for at, rest in listing_fields(text):
                m = CALL_TARGET.match(rest)
                if m is None:
                    continue
                target = int(m.group("target"), 16)
                if target in found:
                    found[target].append((f"{scope} {name[:-4]}", at))
    return found


# `lcall`/`acall`/`ljmp`/`ajmp` with an absolute operand, off the listing's
# own mnemonic column. `acall` and `ajmp` carry a *paged* operand, so the
# value is the byte rather than a runtime address and a match on one is a
# target this tool cannot resolve -- reported, not silently dropped.
CALL_TARGET = re.compile(
    r"^(?:lcall|acall|ljmp|ajmp)\s+0x(?P<target>[0-9A-Fa-f]{4})\b", re.I)


def listing_fields(text: str) -> list:
    """[(addr, mnemonic text)] for every instruction line in a listing.

    One parser for both callers above, so a change to the listing format is a
    change in one place. The `;` header lines do not match and are not
    special-cased: they begin with `;`, which is not the start of a hex
    address, and the regex is what says so.
    """
    out = []
    for line in text.splitlines():
        m = LISTING_LINE.match(line)
        if m:
            out.append((int(m.group("addr"), 16), m.group("mn")))
    return out


def register_name(cell: str) -> str:
    """`R6` for an index-load cell that names a register, else "".

    The callers' report needs the register to look for, and the load cell is
    the only place it is named. A cell that names a read or a literal has no
    register to follow, and the callers row then says so rather than
    searching for one.
    """
    m = re.match(r"^R([0-7])\b", cell)
    return f"R{m.group(1)}" if m else ""


def caller_index(d: bytes, scope: str, addr: str, call_at: int,
                 reg: str) -> str:
    """What the caller's own listing puts in `reg` in front of the call.

    The plan's "the constant each committed listing passes in the index
    register", measured rather than assumed: the last write to `reg` inside
    the caller's own listing and inside `WINDOW` of the call. A literal is
    reported as one; anything else is `NO_CONSTANT`, which on this image is
    what every caller of every one of these sites is.
    """
    if not reg:
        return "index register not named at the site"
    lines = read_listing(scope, addr)
    starts = [at for at, _mn in lines]
    i = bisect.bisect_right(starts, call_at) - 1
    seen = 0
    # `mov Rn,#imm` is 0x78-0x7F; `mov direct,#imm` is 0x75 and does not name
    # a register, so it cannot be this one.
    while i >= 0 and seen < WINDOW:
        at, textline = lines[i]
        seen += 1
        if textline.split(" ", 1)[0].lower() in TERMINATORS:
            break
        op = d[at] if at < len(d) else None
        if op is not None and 0x78 <= op <= 0x7F and f"R{op - 0x78}" == reg:
            return f"{norm(d, at)} at 0x{at:04X}"
        if op is not None and 0xF8 <= op <= 0xFF and f"R{op - 0xF8}" == reg:
            return f"`{squash(textline)}` at 0x{at:04X} (run time)"
        i -= 1
    return NO_CONSTANT


NO_CONSTANT = ("no constant within this window of the call in the caller's "
               "own listing")


# --- figures the write-up declares ------------------------------------------

def figures(d: bytes, pd_verified: bool, index_rows: list) -> list:
    """The `key = value` lines `--check` holds the write-up to.

    Every key is re-derived from the image on every run, and the write-up
    quotes the block rather than these lines. A key here with no reader in
    this file is a promise wearing the costume of a pin, which is the
    `check_doc_figure_pins.py` defect this ordering is meant to avoid: the
    list is built by the functions whose output each key *is*.
    """
    sites = scan(d, pd_verified, BLOCK_BASE_HI)
    allsites = scan(d, pd_verified)
    per_region = collections.Counter(r["region"] for r in allsites)
    block = d[BLOCK_START:BLOCK_END + 1]
    tags = entry_tags(d, BLOCK_START, BLOCK_END)
    out = [
        ("table.start", f"0x{BLOCK_START:04X}"),
        ("table.end", f"0x{BLOCK_END:04X}"),
        ("table.bytes", str(len(block))),
        ("table.sha256", hashlib.sha256(block).hexdigest()),
        ("table.entries_at_2", str(tags["fields"])),
        ("table.distinct_entry_bytes", str(tags["distinct_tags"])),
        ("sites.total", str(len(allsites))),
    ]
    for region in REGIONS_MAIN_EC + ("pd-image", "unknown"):
        out.append((f"sites.{region}", str(per_region.get(region, 0))))
    out.append((f"sites.base_0x{BLOCK_BASE_HI:02X}", str(len(sites))))
    out.append((f"sites.base_0x{BLOCK_BASE_HI:02X}.with_dph_store",
                str(sum(1 for r in sites if r["dph_store"]))))
    out.append(("sites.common_listed",
                str(sum(1 for r in sites
                        if listing_covers(r, index_rows) == LISTED))))
    for row in sites:
        # Comma-separated and space-free so one figure is one `key = value`
        # line: the block is diffed line by line, and a value carrying spaces
        # is a line a reader has to re-read to see what changed.
        covers = listing_covers(row, index_rows)
        out.append((f"site.0x{row['offset']:04X}",
                    f"stride={row['stride']},"
                    f"base_off=0x{row['base_off']:02X},"
                    f"base_hi=0x{row['base_hi']:02X},"
                    f"dph_store={'yes' if row['dph_store'] else 'no'},"
                    f"listing="
                    f"{'confirmed' if covers == LISTED else 'unconfirmed'}"))
    for stride in STRIDES:
        whole, left = records_in_run(BLOCK_START, BLOCK_END, stride)
        out.append((f"records.{stride}.whole", str(whole)))
        out.append((f"records.{stride}.leftover_bytes", str(left)))
        for label, anchor in ANCHORS:
            out.append((f"walk.{stride}.steps_from_{label}",
                        str(walk_reaches(anchor, BLOCK_START, BLOCK_END,
                                         stride, len(d)))))
    return out


def block_from_text(text: str, path: str) -> dict:
    """The fenced block's `key = value` pairs, or a refusal.

    Reads the fence's body rather than the whole file, so a figure quoted in
    the prose beside the block is not held by `--check` and one inside the
    fence is. The fence is matched on its language tag, so the dump the
    write-up prints with it does not parse as a declaration.
    """
    # A refusal is printed and returned rather than raised, so a caller that
    # is *testing* the refusal -- `--self-test`, and the suite's case for it --
    # gets a return code instead of an interpreter traceback on its way out.
    m = re.search(r"^```" + BLOCK_LANG + r"\s*$(?P<body>.*?)^```\s*$",
                  text, re.M | re.S)
    if m is None:
        print("error: " + NO_BLOCK % repo_path(path), file=sys.stderr)
        return None
    out = {}
    for line in m.group("body").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k = FIG_LINE.match(line)
        if k is None:
            print(f"error: {repo_path(path)}: {line!r} in the "
                  f"```{BLOCK_LANG} block is not `key = value`", file=sys.stderr)
            return None
        if k.group("key") in out:
            print(f"error: {repo_path(path)}: key {k.group('key')!r} is "
                  f"declared twice in the ```{BLOCK_LANG} block", file=sys.stderr)
            return None
        out[k.group("key")] = k.group("value")
    if not out:
        print("error: " + NO_BLOCK % repo_path(path), file=sys.stderr)
        return None
    return out


def run_check(d: bytes, pd_verified: bool, index_rows: list, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces the write-up's block.

    Diffed rather than compared cell by cell so a red run says which figure
    moved and which way, which is the whole of what a reader needs from it.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    declared = block_from_text(text, path)
    if declared is None:
        return 1
    got = figures(d, pd_verified, index_rows)
    generated = "".join(f"{k} = {v}\n" for k, v in sorted(got))
    want = "".join(f"{k} = {v}\n" for k, v in sorted(declared.items()))
    if generated == want:
        print(f"{repo_path(path)}: its ```{BLOCK_LANG} block reproduces from "
              f"{repo_path(DEFAULT_FIRMWARE)} ({len(got)} figures)")
        return 0
    print(f"note: {repo_path(path)}'s ```{BLOCK_LANG} block differs from what "
          "this run re-derived; the block is the product of the commands the "
          "page names, so regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(want.splitlines(), generated.splitlines(),
                                     "declared", "re-derived", lineterm="", n=0):
        print(line, file=sys.stderr)
    extra = sorted(set(declared) - {k for k, _v in got})
    for key in extra:
        print(f"note: {key!r} is declared in the block and no figure here "
              "derives it", file=sys.stderr)
    return 1


# --- output ----------------------------------------------------------------

def hex_dump(d: bytes, at: int, length: int, width: int = 16) -> str:
    """Aligned hex plus ASCII over `length` bytes from `at`.

    `disasm8051.py` cannot produce this: it has no hex mode, and its `-n`
    counts *instructions* rather than bytes, so `--at 0x4900 -n 200` frames a
    table as garbage instructions and reports the framing as the finding. A
    dump of a byte run is not a decode, and it is printed as one.
    """
    out = io.StringIO()
    for start in range(at, at + length, width):
        chunk = d[start:start + width]
        if not chunk:
            break
        hexed = " ".join(f"{b:02X}" for b in chunk)
        text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        out.write(f"{start:05X}  {hexed:<{width * 3 - 1}}  |{text}|\n")
    return out.getvalue()


def sites_table(d: bytes, rows: list, index_rows: list) -> str:
    """The `--sites` table as a string rather than a write.

    Columns are the site's identity, the three arithmetic operands, whether
    the store that finishes the pointer is there, the register the listing
    puts in A, which exported function covers it, and the listing cross-check
    that turns the scan into a census.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file_offset", "runtime", "region", "stride", "base_off",
                "base_hi", "base", "dph_store", "index_load", "function",
                "listing"])
    for r in rows:
        w.writerow([
            f"0x{r['offset']:05X}",
            f"0x{r['runtime']:04X}" if r["runtime"] is not None else "",
            r["region"], r["stride"], f"0x{r['base_off']:02X}",
            f"0x{r['base_hi']:02X}", f"0x{r['base']:04X}",
            "yes" if r["dph_store"] else "no",
            index_load(d, r["offset"], index_rows),
            owner_of(r["offset"], index_rows),
            listing_covers(r, index_rows)])
    return buf.getvalue()


def sites_report(d: bytes, pd_verified: bool, index_rows: list,
                 base_hi=None) -> str:
    """The census, with the population split by region and by narrowing.

    The split is printed rather than filtered silently because a count that a
    `--base` can manufacture is not a finding: both the narrowed and the
    whole-image populations are here on every run, so the reader never has to
    re-run to find out what the narrowing hid.
    """
    rows = scan(d, pd_verified, base_hi)
    allrows = scan(d, pd_verified)
    per_region = collections.Counter(r["region"] for r in allrows)
    listed = sum(1 for r in rows if listing_covers(r, index_rows) == LISTED)
    # Without a `--base` the two columns are the same census twice, which
    # would read as a narrowing that happened. So the second column is dropped
    # rather than filled, and the header says which of the two cases this is.
    narrowed = base_hi is not None
    out = [f"{len(allrows)} stride construction(s) in {len(d)} bytes of "
           "image, by region"
           + (f", and the subset on base page 0x{base_hi:02X}\n"
              if narrowed else " (no `--base`, so nothing is filtered)\n"),
           "A byte scan is an upper bound: these are the offsets whose eleven "
           "bytes read\nas the construction, wherever they sit.\n",
           "  region       all" + ("  selected\n" if narrowed else "\n")]
    for region in REGIONS_MAIN_EC + ("pd-image", "unknown"):
        line = f"  {region:<9} {per_region.get(region, 0):>6}"
        if narrowed:
            line += f"  {sum(1 for r in rows if r['region'] == region):>8}"
        out.append(line + "\n")
    out.append(f"\n{listed} of {len(rows)} "
               + ("selected " if narrowed else "")
               + "site(s) sit on an instruction line of a committed .asm "
               "listing;\nthe `listing` column is the cross-check that "
               "separates the two.\n\n")
    out.append(sites_table(d, rows, index_rows))
    return "".join(out)


def records_report(d: bytes, rows: list, stride: int, base: int) -> str:
    """The record framing for one stride, and the two figures kept apart.

    `--stride` picks the geometry and `--base` the page the constructions'
    `base_off` are added to; both are printed on every run because a record
    index printed without the grid it was computed on is a number with
    nothing to check it against.

    The walk figure is reported from two anchors rather than one -- the run's
    own first byte, and the `+0xCC` base the `0x43A5` sequence walks from --
    because they give different answers and a reader who only saw one would
    take it for the record count. Neither is what the firmware can pass; an
    odd stride is a bijection mod 256 and admits all 256 index values.
    """
    whole, left = records_in_run(BLOCK_START, BLOCK_END, stride)
    out = [f"page base 0x{base:04X}, stride {stride}, run "
           f"0x{BLOCK_START:04X}-0x{BLOCK_END:04X}\n"]
    out.append(f"  the run is {BLOCK_END - BLOCK_START + 1} bytes: "
               f"{whole} whole record(s) of {stride} and {left} byte(s) "
               "left over\n")
    for label, anchor in ANCHORS:
        out.append(f"  the 8-bit walk from 0x{anchor:04X} "
                   f"({ANCHOR_LABELS[label]}) reaches "
                   f"{walk_reaches(anchor, BLOCK_START, BLOCK_END, stride, len(d))}"
                   " further record(s) before it leaves the run.\n")
    out.append("  These are three different questions and the tool will not "
               "merge them. An odd stride\n  is a bijection mod 256, so the "
               "construction admits every 8-bit index and none of these is a "
               "record\n  count the firmware can reach; the last is where "
               "*this* grid runs out.\n")
    out.append("  site        base_off  record  field\n")
    for r in rows:
        frame = record_frame(base, BLOCK_START, BLOCK_END, stride, r["base_off"])
        if frame is None:
            out.append(f"  0x{r['offset']:04X}    0x{r['base_off']:02X}"
                       f"      --    outside the run\n")
        else:
            out.append(f"  0x{r['offset']:04X}    0x{r['base_off']:02X}"
                       f"      {frame[0]:>4}   {frame[1]:>5}\n")
    return "".join(out)


def callee_rows(path: str = CALLEES_CSV) -> dict:
    """{(scope, addr): row} from `call-graph-callees.csv`.

    Read for one number only: the `inbound` count each entry is credited
    with. `--index-range`'s own caller list is read out of the `.asm`
    listings, and this is the committed census those should agree with --
    `call_graph.py --check` holds that file against the listings it was
    derived from, and this print is what a reader sees when they do not. The
    two are different derivations on purpose; a table that agreed with
    itself would check nothing.
    """
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r["scope"], r["addr"].upper())] = r
    return out


def index_report(d: bytes, rows: list, index_rows: list) -> str:
    """What each site indexes with, and what the listings pass to reach it.

    Every row is a *committed* observation. Where no listing passes a
    constant, the cell says so, and the write-up reports that as the answer
    to the index question rather than inferring a range from the arithmetic:
    15 and 21 are odd, so `A*stride mod 256` is a bijection and the
    construction bounds nothing on its own.

    Three sites share an entry, so their caller rows repeat. That is
    deliberate: each construction is asked the same question in its own right
    and a site whose function is reached by a different set of callers than
    its neighbour would otherwise be invisible.
    """
    entries = {}
    for r in rows:
        text = owner_of(r["offset"], index_rows)
        if text != NO_FUNCTION:
            entries.setdefault(int(text.split()[1], 16), text)
    calls = call_sites(set(entries))
    census = callee_rows()
    out = []
    for r in rows:
        text = owner_of(r["offset"], index_rows)
        load = index_load(d, r["offset"], index_rows)
        if text == NO_FUNCTION:
            out.append(f"  0x{r['offset']:04X}  {NO_FUNCTION}\n")
            continue
        scope, addr, _name = text.split(" ", 2)
        entry = int(addr, 16)
        reg = register_name(load)
        who = calls.get(entry, [])
        crow = census.get((scope, addr.upper()))
        counted = crow["inbound"] if crow else "no row"
        out.append(f"  0x{r['offset']:04X}  entry {scope} {addr}  {load}\n")
        for listing, call_at in who:
            cscope, caddr = listing.split(" ", 1)
            out.append(f"      {listing} at 0x{call_at:04X}: "
                       f"{caller_index(d, cscope, caddr, call_at, reg)}\n")
        out.append(f"      {len(who)} caller(s) found in the listings; "
                   f"call-graph-callees.csv credits this entry {counted}\n")
    out.append("\n  The index load is read out of the committed .asm the site "
               "sits in, backwards to\n  the end of its block. `read, not a "
               "register` names a read whose address this tool\n  does not "
               "follow. A caller row is what the caller's own listing puts in "
               "the index\n  register inside the same window; what the "
               "firmware can pass is not in these files, and\n  an odd stride "
               "is a bijection mod 256, so no range follows from the "
               "arithmetic.\n")
    return "".join(out)


# --- self-test -------------------------------------------------------------

def self_test(d: bytes, pd_verified: bool, index_rows: list) -> int:
    """The refusals, each written against the error it is meant to catch.

    A `--self-test` is a thing a person runs; `test_stride_index_table.py`
    is a thing `tools/run-tests.sh` collects, and it carries the same cases
    plus the mutation runs that show each one goes red. Both read the
    committed image, so they cannot disagree about which refusals exist.
    """
    fails = []

    def check(ok, text):
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")
        if not ok:
            fails.append(text)

    print("stride_index_table.py --self-test")

    # 1. An even stride is refused. The mistake is the one a reader makes when
    #    they type a record width that happens to be even, believing the
    #    record count it prints means what the odd stride's does.
    try:
        check_stride(14)
        check(False, "an even stride is refused with the bijection as the reason")
    except SystemExit as e:
        check("bijection" in str(e) and "14" in str(e),
              "an even stride is refused with the bijection as the reason")

    # 2. A base outside the common area is refused. The mistake is passing a
    #    bank runtime address, which is not a file offset for the two windows
    #    `REGIONS` gives base 0x8000.
    try:
        check_block(0xC000)
        check(False, "a base outside the common area is refused")
    except SystemExit as e:
        check("common area" in str(e) and "0xC000" in str(e),
              "a base outside the common area is refused, naming the bound")

    # 3. The construction's eleven bytes, read as a byte pattern, hold every
    #    figure the census prints for a site. Written against the mistake the
    #    suite's own provenance is full of -- reading the operands off a scan
    #    site rather than off the bytes -- so the check is against the image.
    rows = scan(d, pd_verified, BLOCK_BASE_HI)
    shapes = all(
        r["stride"] == d[r["offset"] + STRIDE_BYTE]
        and r["base_off"] == d[r["offset"] + BASE_OFF_BYTE]
        and r["base_hi"] == d[r["offset"] + BASE_HI_BYTE]
        and d[r["offset"] + 1] == 0xF0 and d[r["offset"] + 7] == 0x82
        and r["base"] == ((d[r["offset"] + BASE_HI_BYTE] << 8)
                          | d[r["offset"] + BASE_OFF_BYTE])
        for r in rows)
    check(shapes, "every site's three operands re-read off the image")

    # 4. A rewritten construction is a different site, not the same one, and a
    #    rewritten *operand* is the same site with a different number. Both
    #    halves are here because the two mistakes are opposite and both are
    #    easy: a pattern that includes the stride byte misses a site whose
    #    stride is anything, and a pattern that excludes it reports a stale
    #    stride for one whose is not.
    site = rows[0]["offset"]
    pattern = bytearray(d)
    pattern[site + 1] ^= 0x01          # the 0xF0 of `mov B,#imm`
    after = scan(bytes(pattern), pd_verified, BLOCK_BASE_HI)
    check(site not in {r["offset"] for r in after},
          "a construction whose mode byte is rewritten stops being a site")
    operand = bytearray(d)
    operand[site + STRIDE_BYTE] ^= 0x01
    again = {r["offset"]: r for r in scan(bytes(operand), pd_verified,
                                         BLOCK_BASE_HI)}
    check(site in again and again[site]["stride"] == rows[0]["stride"] ^ 0x01,
          "a site whose stride operand changes is still a site, with the "
          "stride the byte now holds")

    # 5. A record count that overruns the image is refused, rather than
    #    printed as a count of bytes past the end of the buffer. The mistake
    #    is a typo in a declared extent that reads as a short table instead of
    #    as a run past the end of what was read.
    try:
        walk_reaches(0x4900, BLOCK_START, len(d) + 0x1000, 15, len(d))
        check(False, "a run declared past the end of the image is refused")
    except SystemExit as e:
        check("outside the image" in str(e),
              "a run declared past the end of the image is refused, "
              "naming the bound")
    check(walk_reaches(0x4A25, BLOCK_START, BLOCK_END, 15) == 0,
          "a grid anchored at the run's last byte reaches no further record")

    # 6. A `--check` against a write-up whose figures no longer re-derive is
    #    red. Built here rather than asserted about, because the mistake it
    #    catches is a check that has quietly stopped comparing anything.
    scratch = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                           "stride-index-table-self-test.md")
    keys = figures(d, pd_verified, index_rows)
    body = "".join(f"{k} = {v}\n" for k, v in keys)
    with open(scratch, "w", encoding="utf-8") as fh:
        fh.write(f"# scratch\n\n```{BLOCK_LANG}\n{body}```\n")
    check(run_check(d, pd_verified, index_rows, scratch) == 0,
          "a block this run produced re-derives")
    body_bad = body.replace("table.bytes = %d" % (BLOCK_END - BLOCK_START + 1),
                            "table.bytes = %d" % (BLOCK_END - BLOCK_START))
    with open(scratch, "w", encoding="utf-8") as fh:
        fh.write(f"# scratch\n\n```{BLOCK_LANG}\n{body_bad}```\n")
    ok = run_check(d, pd_verified, index_rows, scratch) == 1
    check(ok, "a block whose extent figure is off by one goes red")
    os.unlink(scratch)

    # 7. A write-up with no fenced block is refused, rather than read as a
    #    block of nothing and reported as agreement.
    scratch = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                           "stride-index-table-empty.md")
    with open(scratch, "w", encoding="utf-8") as fh:
        fh.write("# scratch\n\nno block here\n")
    check(run_check(d, pd_verified, index_rows, scratch) == 1,
          "a write-up with no fenced block is refused, not read as agreeing")

    print(f"\n{len(fails)} failure(s)" if fails else "\nall assertions passed")
    return 1 if fails else 0


# --- main ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--sites", action="store_true",
                    help="the stride-construction census, over every region")
    ap.add_argument("--base", metavar="0xNN",
                    help="with --sites, keep only the sites whose construction "
                         "builds an address on this base page; with "
                         "--records, the page the constructions' base_off is "
                         "added to (default: 0x4900)")
    ap.add_argument("--at", metavar="0xNNNN", default="0x4900",
                    help="start of the hex dump (default: 0x4900)")
    ap.add_argument("--len", metavar="N", default=0xD8, type=lambda v: int(v, 0),
                    help="bytes of hex dump (default: 0xD8)")
    ap.add_argument("--records", action="store_true",
                    help="the record framing, per site, at one stride")
    ap.add_argument("--stride", type=int, default=STRIDES[0], metavar="N",
                    help=f"stride for --records (default: {STRIDES[0]})")
    ap.add_argument("--index-range", action="store_true",
                    help="what each site indexes with, and the callers the "
                         "committed listings show")
    ap.add_argument("--boundary", action="store_true",
                    help="the code/data evidence at each end of the block")
    ap.add_argument("--emit-block", action="store_true",
                    help="print the ```{lang} block the write-up declares, "
                         "ready to paste; --check compares against it")
    ap.add_argument("--check", nargs="?", const=WRITEUP, metavar="PATH",
                    help="re-derive the figures the write-up declares and fail "
                         f"on any difference (default: {repo_path(WRITEUP)})")
    ap.add_argument("--self-test", action="store_true",
                    help="run this tool's own refusals")
    args = ap.parse_args()

    try:
        with open(args.firmware, "rb") as fh:
            d = fh.read()
    except OSError:
        print("error: " + NO_FIRMWARE % repo_path(args.firmware), file=sys.stderr)
        return 1
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF are reported as region 'unknown', "
              "not as another image's\n", file=sys.stderr)
    index_rows = owning_rows()

    if args.self_test:
        return self_test(d, pd_verified, index_rows)
    if args.emit_block:
        # The other half of `--check`. A check that says "regenerate rather
        # than edit" has to leave a way to regenerate, or the sentence is a
        # way of saying "hand-edit this carefully".
        sys.stdout.write(f"```{BLOCK_LANG}\n")
        sys.stdout.write("".join(f"{k} = {v}\n"
                                 for k, v in sorted(figures(d, pd_verified,
                                                            index_rows))))
        sys.stdout.write("```\n")
        return 0
    if args.check is not None:
        return run_check(d, pd_verified, index_rows, args.check)

    if args.records:
        base = int(args.base, 16) if args.base else BLOCK_BASE
        check_stride(args.stride)
        check_block(base)
        rows = scan(d, pd_verified, BLOCK_BASE_HI)
        sys.stdout.write(records_report(d, rows, args.stride, base))
        return 0
    if args.index_range:
        rows = scan(d, pd_verified, BLOCK_BASE_HI)
        sys.stdout.write(index_report(d, rows, index_rows))
        return 0
    if args.boundary:
        sys.stdout.write("the two ends of the declared run, and the two "
                         "functions they are bracketed by\n\n")
        for label, at, cell in boundary_report(d, index_rows):
            sys.stdout.write(f"  0x{at:04X}  {label}\n         {cell}\n")
        sys.stdout.write("\n  A convergence count is framing evidence and "
                         "cannot decide code from data on its own -- a run\n"
                         "  of two-byte entries syncs onto every one of its own "
                         "offsets. The walk verdict beside it is a flow\n"
                         "  walk, and a flow walk cannot tell code from a table "
                         "it wandered into either.\n")
        return 0

    at = int(args.at, 16)
    out = [f"0x{at:04X}, {args.len} byte(s). The record-like run the "
           f"constructions address is 0x{BLOCK_START:04X}-0x{BLOCK_END:04X} "
           f"({BLOCK_END - BLOCK_START + 1} bytes).\n\n",
           hex_dump(d, at, args.len), "\n"]
    sys.stdout.write("".join(out))
    if args.sites:
        base_hi = int(args.base, 16) if args.base else None
        sys.stdout.write(sites_report(d, pd_verified, index_rows, base_hi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
