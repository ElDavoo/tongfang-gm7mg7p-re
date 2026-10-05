#!/usr/bin/env python3
"""Decode the inline `switch` tables the main EC image's one table-reading
subroutine consumes -- the bank-0 table at runtime 0x8038 in particular.

ec/annotations/bank-call-audit.md section 8 met that table as a side effect:
four PC-relative branch sites resolve outside their region, and one of them,
file 0x0803B, plainly sits in data. Section 8 read the bytes from 0x8038 as
`sjmp` + `index, address` triples. This tool reads them against the code that
consumes them instead, and the two readings disagree -- section 9 corrects
section 8 in place. (Section 8 also scored that site 24 of 24 on the anchor
walk; the walk now steps over the case table the site is inside, so it scores
5 of 24. Section 8's second correction says so, and §4's `0x00686` carries
the "a high frame score is not a branch" argument instead.)

**How the table is found, and why it is not a DPTR scan.** Nothing in this
image loads DPTR with #0x8038 or #0x803A: the reader takes its pointer off
the *stack*. The table sits inline immediately after an `lcall` to a
subroutine that begins `pop dph ; pop dpl ; mov r0,a`, so the return address
the call pushed is the table's own address and the accumulator carries the
selector. That is the shape Keil C51 emits for a `switch` on a byte (its
runtime calls the helper `?C?CCASE`); the name is a name for the idiom, not
a symbol read out of this image. So the search here is for the prologue
shape, then for `lcall` bytes naming it -- an immediate-DPTR scan finds this
table zero times, which is the blind spot that framing is meant to cover.

**Entry layout, taken from the reader rather than from the table.** This
module's own reader at `0x7151` reads the first two bytes of an entry as a
big-endian address and the *third* as the case value, and stops on an all-zero
address, after which two more bytes give the default. Address-then-case, not
case-then-address: section 8 read them the other way round, which shifts every
entry by one byte and puts a phantom `sjmp` at the table's head.

**That width is a parameter, not a constant, and `ENTRY_LEN` is this module's
default rather than the family's.** The PD image's three dispatchers walk 4- and
6-byte entries -- two target bytes at +0/+1 and then `stride - 2` key bytes --
so `decode_table()` takes the stride its caller derived with `entry_stride()`
from the reader in question, and `0x7151` is what `ENTRY_LEN` names. What does
*not* scale with the stride is the end of the table: the terminator is a zero
target pair and the default the two bytes after it at every stride, which is
`TERM_LEN`/`DEFAULT_LEN` below and `docs/findings/pd-reader-entry-layouts.md`
for the bytes it rests on.

**The reader search is an enumerated set of shapes, and it is tiered.** One
literal is a weak search: `d0 83 d0 82 f8` is the spelling this compiler
runtime emitted at `0x7151`, and nothing licenses reading a different reader
in the same image as the same five bytes. `PROLOGUE_SHAPES` below is the
enumerated set -- both pop orders, the selector save landing in a register or
a direct address, an intervening `push acc` -- and each entry says whether it
`from_return_address`, which is the family's invariant and the one thing that
separates this reader from a routine that pops a DPTR it pushed itself. A
direct-address reader (`mov dptr,#imm16` plus a table walk) is reported in its
own bucket by `direct_address_readers()` and never decoded as a table of this
family; the two buckets are separate results, not one widened one.

Widening trades a blind spot for false positives unless it is counted in two
tiers, so it is: **every** shape match is a tier-1 candidate, and a tier-2
candidate is one whose first `PROLOGUE_BODY_INSNS` instructions contain a
`movc a,@a+dptr`, i.e. the routine actually walks a table. On this image the
`d0 82 d0 83` pair alone is 36 sites in the main EC and 93 in the PD image,
against 2 for the whole five-byte literal, and the corroboration is what
separates them. A third filter settles the family question on its own terms: a
reader of *this* family is entered by a bare `lcall` and nothing else, so
`reader_call_sites()` on a candidate is what says whether its table can be
inline at all. `docs/findings/table-reader-spellings.md` is the reading, with
the counts, the `r2` listings and the two PD readers whose entry layout is not
this one.

**Regions, and what a PD verdict is worth.** `--region` runs the same search
over `common`/`bank0`/`bank1` (the regions a common-area subroutine is called
from), over the `ITE8850-PD` image at `0x20000`, or over both.
`pd_index_tables.py` is the PD half's own census and imports the shapes, the
decode and the checks from here rather than restating them, so the two readings
cannot drift. One check is weaker in the PD and reads the same: `malformed()`'s
"resolves inside the caller's own region" test is *banked* in the main EC --
below `0x8000` is common area, at or above it is the caller's own bank -- while
the PD image is flat, so the same test there only asks for a `0x0000`-`0xFFFF`
CODE address. That is a weaker check, not a stronger result.

**What a well-formed verdict is worth.** An `lcall` byte site is a byte scan
and over-counts (bank-call-audit.md section 1 says why), so each candidate's
table is checked rather than assumed: case values strictly ascending, every
target and the default resolving inside the caller's own region, and the byte
after the table being one of the table's own targets -- the fall-through a
compiler emits for the first case. All of that is corroboration, not
proof; nothing here is evidence that any handler executes, and no `status:`
in ../annotations/registers.yaml follows from a decode.

`--all-csv` and `--spans-csv` carry that caveat with them: the span list is
the census, one row per `lcall` *byte* site, so a phantom site that happens to
be followed by well-formed-looking bytes is in it. `frame_onto` rides along
per site rather than averaged, which is what keeps the weak ones visible.

Usage:
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --at 0x0D148
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --all-tables
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --region pd
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --csv \
        > ec/annotations/bank0-8038-dispatch-table.csv
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --all-csv \
        > ec/annotations/index-table-entries.csv
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --spans-csv \
        > ec/annotations/index-table-spans.csv
    python3 ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import sys

from disasm8051 import converges_from, decode
from trace_xdata_refs import (PD_MARKER, REGIONS, offset_for_runtime,
                              region_of, runtime_addr)

LCALL = 0x12

MOVC_A_DPTR = 0x93  # movc a,@a+dptr -- the table walk this family exists for
JMP_AT_A_DPTR = 0x73  # the dispatch; carries no address for a byte scan
MOV_DPTR = 0x90

# Instructions decoded past a shape match before the walk is called
# uncorroborated. The family's own reader reaches its first `movc` at +4, and
# a routine that walks a table does the same; the window is short on purpose,
# because a longer one lets a linear decode run past a call and into the bytes
# after it, which is how a `pop dpl ; pop dph` around a `movx` comes to look
# like a reader.
PROLOGUE_BODY_INSNS = 8

Prologue = collections.namedtuple(
    "Prologue", ["name", "pattern", "from_return_address", "what"])

# The enumerated prologue set, longest pattern first, so a candidate matches
# the most specific shape it can rather than the shortest. `from_return_address`
# is the family's invariant -- the pointer comes off the return address the
# `lcall` pushed -- and it is what `lcalled_readers()` gates on. Every entry
# here is `True` today, because a pop off the stack is the only spelling of
# that invariant; a shape that does not preserve it belongs in
# `direct_address_readers()`'s bucket instead, and adding one here with the
# flag `False` is the deliberate way to say it is not a table of this family.
#
# A shape match is not sufficient on its own, and the two filters that are
# named above: a shape match alone is tier 1, a `movc` in the window makes it
# tier 2, and a bare `lcall` naming it is what says the pointer came off the
# return address rather than off a `push dph`/`push dpl` the same routine did a
# few instructions earlier. The last two entries are the bare pop pairs, which
# are the other ten's prefixes: they are what a candidate matches when none of
# the more specific spellings does, and they are where the false positives
# come from.
PROLOGUE_SHAPES = (
    Prologue("pop-dph-dpl-selector-r0", bytes.fromhex("d083d082f8"), True,
             "`pop dph ; pop dpl ; mov r0,a` -- the spelling at 0x7151, and the "
             "one at the head of each PD dispatcher"),
    Prologue("pop-dpl-dph-selector-r0", bytes.fromhex("d082d083f8"), True,
             "pop dpl before dph, selector still r0"),
    Prologue("pop-dph-dpl-selector-rn", bytes.fromhex("d083d082f9"), True,
             "selector saved to r1 rather than r0"),
    Prologue("pop-dph-dpl-selector-r7", bytes.fromhex("d083d082ff"), True,
             "selector saved to r7 rather than r0"),
    Prologue("pop-dpl-dph-selector-rn", bytes.fromhex("d082d083f9"), True,
             "pop dpl first, selector saved to r1"),
    Prologue("pop-dpl-dph-selector-r7", bytes.fromhex("d082d083ff"), True,
             "pop dpl first, selector saved to r7"),
    Prologue("pop-dph-dpl-selector-direct", bytes.fromhex("d083d082f5"), True,
             "selector saved by `mov direct,a` rather than to a register"),
    Prologue("pop-dpl-dph-selector-direct", bytes.fromhex("d082d083f5"), True,
             "pop dpl first, selector saved to a direct address"),
    Prologue("pop-dph-dpl-push-acc", bytes.fromhex("d083d082e0"), True,
             "`push acc` between the pops and the selector save"),
    Prologue("pop-dpl-dph-push-acc", bytes.fromhex("d082d083e0"), True,
             "pop dpl first, `push acc` before the selector save"),
    Prologue("pop-dph-dpl", bytes.fromhex("d083d082"), True,
             "the bare pop pair, dph first -- no selector save named"),
    Prologue("pop-dpl-dph", bytes.fromhex("d082d083"), True,
             "the bare pop pair, dpl first -- no selector save named"),
)

SHORTEST_PROLOGUE = min(len(p.pattern) for p in PROLOGUE_SHAPES)

# The main EC image, i.e. the regions a common-area subroutine can be called
# from. The PD image at 0x20000 is a separate program with its own copy of
# the same compiler runtime, so its readers are not this one and its tables
# are not in this address space -- which is why it is a separate entry of
# REGION_SETS rather than a fourth region of the search. The runtime does
# carry over: the PD dispatchers are this family's shape, spelled the same way.
MAIN_EC = ("common", "bank0", "bank1")
PD_IMAGE = ("pd-image",)

REGION_SETS = {"main": MAIN_EC, "pd": PD_IMAGE, "both": MAIN_EC + PD_IMAGE}

# The common-area range BL51's bank-switch trampolines occupy, and the low and
# high of their DPTR immediates. Both are oracles for `--self-test` rather than
# inputs: every run re-derives them through `trampoline_targets()` and compares,
# so a different dump gets them checked and not inherited.
TRAMPOLINE_RANGE = (0x1150, 0x1ABC)
TRAMPOLINE_IMMEDIATE_RANGE = (0x8031, 0xFE00)

ENTRY_LEN = 3  # address_hi, address_lo, case value -- the stride at 0x07151

# The end of a table, which does not scale with the stride. A terminator is a
# zero target pair -- the same two bytes that carry every entry's target, read
# by the reader's own zero-tests -- and the default is the two bytes right after
# it, read by the same `jmp @a+dptr` the matched entries go out through. So the
# pair is two bytes at every stride and `end` is four bytes past the terminator
# at every stride. `DEFAULT_TAIL` is the 13 bytes of reader code that does it,
# byte-identical in all four readers, and it is what this is read from rather
# than scaled: `docs/findings/pd-reader-entry-layouts.md` has the listings.
TERM_LEN = 2
DEFAULT_LEN = 2

# `inc dptr ; inc dptr ; movc a,@a+dptr ; mov r0,a ; mov a,#1 ; movc a,@a+dptr ;
# mov dpl,a ; mov dph,r0 ; clr a ; jmp @a+dptr`, read: step DPTR two bytes past
# the zero target pair, load the two bytes there into DPTR, dispatch through
# them. The same 13 bytes at file 0x0715F (main EC), 0x211AA, 0x211D0 and
# 0x211FC, which is the per-stride re-derivation the terminator widths above
# are stated from -- not four constants that happen to agree.
DEFAULT_TAIL = bytes.fromhex("a3a393f8740193f5828883e473")

# The relative branches that close a reader's entry loop: `jnz` and `sjmp`.
# `jz` is excluded because these readers use it for the *dispatch* -- the
# branch taken on a key match, back into the routine's own head -- and reading
# that one's displacement would give the dispatch, not the stride.
LOOP_BRANCHES = (0x70, 0x80)
INC_DPTR = 0xA3

# Instructions decoded from a reader before giving up on its loop. A reader
# whose whole body is shorter than this has its stride found inside the bound
# anyway; the bound is here so a decode that finds no loop-back says so rather
# than running into the next routine.
READER_BODY_INSNS = 64

# Entries read before giving up on finding the terminator. No table in this
# image comes close (the largest has 49), and the cap is what stops a
# phantom `lcall` site inside data from walking the whole region.
MAX_ENTRIES = 64

# Instructions decoded into a handler window before giving up. Only the last
# window needs it: every other one is bounded by the next target.
MAX_BODY_INSNS = 64

RET_OPCODES = (0x22, 0x32)  # ret, reti

# The table ec/annotations/bank-call-audit.md section 9 is about, as the file
# offset of the `lcall` that precedes it.
SITE_0X8038 = 0x08035


def walks_a_table(d: bytes, off: int) -> bool:
    """Whether a `movc a,@a+dptr` falls in the first PROLOGUE_BODY_INSNS
    instructions at `off` -- tier 2 out of tier 1. A linear decode, so it can
    read a `movc` that does not execute; the short window is what bounds that."""
    return any(raw[0] == MOVC_A_DPTR
               for _, raw, _ in decode(d, off, PROLOGUE_BODY_INSNS))


def find_readers(d: bytes, regions=MAIN_EC):
    """Every prologue candidate in `regions`, one per matching offset.

    A candidate is tier 1 on its shape and tier 2 when `walks_a_table()` also
    holds; the shape name is the most specific one that matched, so `mov r0,a`
    is reported as itself rather than as the bare pop pair it starts with.

    A byte scan, like every other reader of this image: the same two or four
    bytes occur inside data and as operands of other instructions, and none of
    that is settled here. `reader_call_sites()` is what settles it."""
    out = []
    for name, lo, hi, base, _ in REGIONS:
        if name not in regions:
            continue
        for i in range(lo, hi - SHORTEST_PROLOGUE + 1):
            for p in PROLOGUE_SHAPES:
                if d[i:i + len(p.pattern)] == p.pattern:
                    out.append({"file_offset": i, "region": name,
                                "runtime": runtime_addr(i, True),
                                "shape": p.name,
                                "from_return_address": p.from_return_address,
                                "walks_table": walks_a_table(d, i)})
                    break
    return out


def direct_address_readers(d: bytes, regions=MAIN_EC):
    """Candidates for a reader that names its table with an immediate.

    The family this tool reads takes the table pointer off the *return
    address*, which is why an immediate-DPTR scan finds none of its 15 tables.
    A reader spelled the other way -- `mov dptr,#imm16` naming the table
    outright -- would not be one of this family, so it is counted and listed
    here and decoded nowhere: the two are separate results and folding the
    second into the first would widen the family to fit the search.

    The shape is deliberately tight, because `mov dptr,#imm16` is everywhere in
    this image -- 1632 byte sites in `common` alone -- and a looser shape would
    drown the search in pointer loads: a candidate must walk a table
    (`movc a,@a+dptr`) *and* dispatch through it (`jmp @a+dptr`) inside the
    same short window. That is a reader-shaped two-instruction pattern, not a
    pointer load."""
    out = []
    for name, lo, hi, base, _ in REGIONS:
        if name not in regions:
            continue
        for i in range(lo, hi - 2):
            if d[i] != MOV_DPTR:
                continue
            seen = {raw[0] for _, raw, _ in decode(d, i, PROLOGUE_BODY_INSNS)}
            if {MOVC_A_DPTR, JMP_AT_A_DPTR} <= seen:
                out.append({"file_offset": i, "region": name,
                            "runtime": runtime_addr(i, True),
                            "table_runtime": (d[i + 1] << 8) | d[i + 2]})
    return out


def reader_call_sites(d: bytes, reader_runtime: int, regions=MAIN_EC):
    """Every `lcall <reader>` *byte* in `regions`, with frame evidence. A byte
    scan, with the over-count bank-call-audit.md section 1 describes: the same
    three bytes occur inside data and as operand bytes of other instructions,
    so a site is a candidate until its table decodes.

    For a prologue candidate this is the decisive filter rather than a census
    step: a reader of this family is entered by a bare `lcall` and nothing
    else, so a candidate no `lcall` names cannot have an inline table at all.
    The gap that leaves is a caller reaching it another way -- a `jmp @a+dptr`
    dispatch, an `ljmp` thunk, a trampoline -- and those stay named as the
    blind spots they are."""
    want = bytes((LCALL, reader_runtime >> 8, reader_runtime & 0xFF))
    out = []
    for name, lo, hi, base, _ in REGIONS:
        if name not in regions:
            continue
        for i in range(lo, hi - len(want)):
            if d[i:i + len(want)] == want:
                onto, over = converges_from(d, i)
                out.append({"file_offset": i, "region": name,
                            "runtime": runtime_addr(i, True),
                            "frame_onto": onto, "frame_over": over})
    return out


def lcalled_readers(d: bytes, regions=MAIN_EC):
    """The subset of `find_readers()` that an `lcall` names, in the order
    `find_readers()` returns them. Two conditions, and both are needed: a shape
    that does not take the pointer off the return address has no inline table by
    construction, and a reader with no caller has none to decode. What is left
    is what the census is allowed to run under."""
    return [r for r in find_readers(d, regions)
            if r["from_return_address"]
            and reader_call_sites(d, r["runtime"], regions)]


def trampoline_targets(d: bytes):
    """{trampoline entry: DPTR target} over BL51's bank-switch block, from
    `audit_call_targets.trampolines()` -- the same function every figure in
    bank-call-audit.md derives from, imported rather than re-derived so this
    cross-check cannot disagree with the audit it is checking.

    Imported lazily: `audit_call_targets` is a whole census tool, and a module
    that only wants its trampoline reader should not pay for the rest."""
    from audit_call_targets import bank_switch_stubs, trampolines
    return trampolines(d, bank_switch_stubs(d))


def entry_stride(d: bytes, off: int, limit: int) -> int:
    """Bytes one entry advances DPTR, read off `off`'s own loop.

    The reader walks entries by running a few `inc dptr` and branching back to
    the zero-test at its head, so the stride is the length of the `inc dptr` run
    that feeds the last `LOOP_BRANCHES` branch in its body. `limit` bounds the
    decode to this reader's own bytes: the PD's three dispatchers are adjacent,
    and a window that ran past one would read the next one's stride back.

    The chosen branch has to land at or after `off` as well as backwards, or a
    backward branch belonging to a *different* routine that reaches back past
    this one's head could be adopted. The three PD loop-backs (`0x11A1`,
    `0x11C7`, `0x11F3`) all qualify, so this tightens the window rather than
    changing today's answer -- and it is what makes the "the window is not the
    routine" caveat checkable instead of merely true today.

    A linear decode, so a branch that does not execute counts the same as one
    that does; what is read is a shape of bytes, not a control-flow trace.

    None when the decode finds no such branch inside the bound -- "not found by
    this method", and a caller that needs a number says so rather than
    defaulting to the main EC's `ENTRY_LEN`."""
    insns = [x for x in decode(d, off, READER_BODY_INSNS) if x[0] < limit]
    back = None
    for n, (at, raw, _) in enumerate(insns):
        if raw[0] in LOOP_BRANCHES and raw[1] > 0x7F:
            target = at + len(raw) + (raw[1] - 256)
            if target >= off:
                back = n
    if back is None:
        return None
    run = 0
    for n in range(back - 1, -1, -1):
        if insns[n][1][0] != INC_DPTR:
            break
        run += 1
    return run


def decode_table(d: bytes, off: int, stride: int = ENTRY_LEN):
    """Decode the inline table at file offset `off`, one entry per `stride`
    bytes.

    `stride` defaults to `ENTRY_LEN`, this module's own reader's width. An
    entry is two target bytes at +0/+1 then `stride - 2` key bytes, compared
    most significant first by the reader's compare chain, and the key is the
    whole of them as an int, so a 4-byte or a 6-byte entry reads the same way
    as a 3-byte one. `case` is kept alongside `key` at `ENTRY_LEN` alone,
    because that is the width every committed CSV and every printed table in
    this file is written at, and a column named for it would otherwise read a
    4-byte entry's second key byte as a case value.

    The terminator and the default are `TERM_LEN`/`DEFAULT_LEN` at every stride
    -- see the constants for why they do not scale.

    Returns a dict with the entries, the terminator, the default address and
    the file offset one past the table, or None if the bytes do not reach a
    terminator inside MAX_ENTRIES."""
    region, lo, _, _ = region_of(off, True)
    entries = []
    i = off
    while len(entries) <= MAX_ENTRIES:
        if i + stride > len(d):
            return None
        target = (d[i] << 8) | d[i + 1]
        if target == 0:
            if i + TERM_LEN + DEFAULT_LEN > len(d):
                return None
            return {
                "file_offset": off,
                "region": region,
                "runtime": runtime_addr(off, True),
                "stride": stride,
                "entries": entries,
                "terminator_offset": i,
                "default": (d[i + TERM_LEN] << 8) | d[i + TERM_LEN + 1],
                "default_offset": i + TERM_LEN,
                "end": i + TERM_LEN + DEFAULT_LEN,
            }
        entry = {"file_offset": i, "runtime": runtime_addr(i, True),
                 "target": target,
                 "key": int.from_bytes(d[i + 2:i + stride], "big")}
        if stride == ENTRY_LEN:
            entry["case"] = d[i + 2]
        entries.append(entry)
        i += stride
    return None


def malformed(d: bytes, tbl) -> list:
    """The ways `tbl` fails to read as a table, as a list of reasons -- empty
    for a well-formed one. Each check is a property the compiler's own output
    has and a run of arbitrary data generally does not."""
    bad = []
    if not tbl["entries"]:
        bad.append("no entries")
        return bad
    # Over `key`, not over `case`: a 4- or a 6-byte entry has no single case
    # byte, and its key is the whole of the bytes the reader compares. At
    # `ENTRY_LEN` the two are the same expression over the same values, so the
    # main EC's verdicts do not move.
    keys = [e["key"] for e in tbl["entries"]]
    if keys != sorted(keys) or len(set(keys)) != len(keys):
        what = "case" if tbl["stride"] == ENTRY_LEN else "key"
        bad.append(f"{what} values not strictly ascending")
    region = tbl["region"]
    for target in [e["target"] for e in tbl["entries"]] + [tbl["default"]]:
        if offset_for_runtime(target, region) is None:
            bad.append(f"0x{target:04X} does not resolve from {region}")
    end_runtime = runtime_addr(tbl["end"], True)
    if end_runtime not in [e["target"] for e in tbl["entries"]]:
        bad.append(f"the byte after the table (0x{end_runtime:04X}) is not one "
                   "of its own targets")
    return bad


def body_bounds(tbl):
    """{target: end file offset} for each entry, bounding a handler at the
    next target *by address*. A reading window, not a decoded function
    boundary: a handler that falls through into the next one gets the same
    window as one that does not."""
    stops = sorted({e["target"] for e in tbl["entries"]} | {tbl["default"]})
    out = {}
    for target in stops:
        nxt = next((s for s in stops if s > target), None)
        here = offset_for_runtime(target, tbl["region"])
        end = offset_for_runtime(nxt, tbl["region"]) if nxt else None
        out[target] = (here, end)
    return out


def body_summary(d: bytes, tbl, target: int):
    """What the window at `target` names: its first instruction, the XDATA
    addresses its `mov dptr,#imm16` loads hold, and the subroutines it calls.

    The walk is disasm8051.py's linear one, so it reads a branch's
    displacement as an instruction and keeps going -- fine for listing the
    addresses a window names, useless as a control-flow trace. It stops at
    the next target or at the first `ret`, whichever comes first, so a body
    with an early return is under-read rather than run on into whatever
    follows it."""
    here, end = body_bounds(tbl)[target]
    xdata, calls = [], []
    first = None
    for i, raw, text in decode(d, here, MAX_BODY_INSNS, target):
        if first is None:
            first = text
        if end is not None and i >= end:
            break
        if raw[0] == MOV_DPTR:
            xdata.append((raw[1] << 8) | raw[2])
        elif raw[0] == LCALL:
            calls.append((raw[1] << 8) | raw[2])
        elif raw[0] in RET_OPCODES:
            break
    return {"first_insn": first, "xdata": sorted(set(xdata)),
            "calls": sorted(set(calls))}


def print_table(d: bytes, tbl) -> None:
    end_runtime = runtime_addr(tbl["end"], True)
    print(f"table at file 0x{tbl['file_offset']:05X} "
          f"({tbl['region']} runtime 0x{tbl['runtime']:04X})")
    print(f"  {len(tbl['entries'])} entries of {ENTRY_LEN} bytes, "
          f"file 0x{tbl['file_offset']:05X}-0x{tbl['terminator_offset'] - 1:05X}")
    print(f"  terminator 0x{d[tbl['terminator_offset']]:02X}"
          f"{d[tbl['terminator_offset'] + 1]:02X} at file "
          f"0x{tbl['terminator_offset']:05X} (an address field of 0x0000)")
    print(f"  default 0x{tbl['default']:04X} at file 0x{tbl['default_offset']:05X}")
    print(f"  table ends at file 0x{tbl['end']:05X} (runtime 0x{end_runtime:04X})")
    bad = malformed(d, tbl)
    print("  well-formed" if not bad else "  MALFORMED: " + "; ".join(bad))
    print()
    print("  case  entry     target  stride  first instruction")
    prev = None
    for e in tbl["entries"]:
        summary = body_summary(d, tbl, e["target"])
        stride = "" if prev is None else f"0x{e['target'] - prev:02X}"
        print(f"  0x{e['case']:02X}  0x{e['file_offset']:05X}  "
              f"0x{e['target']:04X}  {stride:>6}  {summary['first_insn']}")
        prev = e["target"]
    print()


def print_bodies(d: bytes, tbl) -> None:
    print("  what each window names (linear decode, not a control-flow trace):")
    for e in tbl["entries"]:
        s = body_summary(d, tbl, e["target"])
        print(f"    0x{e['target']:04X} case 0x{e['case']:02X}  "
              f"xdata {' '.join(f'0x{a:04X}' for a in s['xdata'])}")
        print(f"                     calls "
              f"{' '.join(f'0x{a:04X}' for a in s['calls']) or '-'}")
    s = body_summary(d, tbl, tbl["default"])
    print(f"    0x{tbl['default']:04X} default   "
          f"xdata {' '.join(f'0x{a:04X}' for a in s['xdata'])}")
    print()


def print_readers(d: bytes, readers, called, regions=MAIN_EC) -> None:
    """The search, its tiers, the direct-address bucket, and the reach of the
    readers the census below runs under. Tier 1 is every shape match and tier
    2 the corroborated subset of it, so the two counts are nested and the
    difference is the false-positive mass the tiers are there to show."""
    print(f"reader search over {'/'.join(regions)}: {len(PROLOGUE_SHAPES)} "
          f"prologue shape(s)")
    by_shape = collections.Counter(r["shape"] for r in readers)
    for p in PROLOGUE_SHAPES:
        if by_shape[p.name]:
            print(f"  {by_shape[p.name]:4}  {p.pattern.hex(' '):<14} "
                  f"{p.name}  -- {p.what}")
    tier2 = [r for r in readers if r["walks_table"]]
    n_sites = {r["runtime"]: len(reader_call_sites(d, r["runtime"], regions))
               for r in called}
    print(f"  {len(readers)} shape match(es) (tier 1), of which {len(tier2)} "
          f"reach a `movc a,@a+dptr` within {PROLOGUE_BODY_INSNS} "
          f"instructions (tier 2) and {len(called)} are named by an `lcall`")
    for r in tier2:
        print(f"    tier 2  file 0x{r['file_offset']:05X} runtime "
              f"0x{r['runtime']:04X} ({r['region']})  {r['shape']}  "
              f"{n_sites.get(r['runtime'], 0)} `lcall` byte site(s)")
    direct = direct_address_readers(d, regions)
    print(f"  {len(direct)} direct-address candidate(s) -- `mov dptr,#imm16` "
          "then a table walk and `jmp @a+dptr`. Not this family, and decoded "
          "nowhere:")
    for r in direct:
        print(f"    file 0x{r['file_offset']:05X} runtime 0x{r['runtime']:04X} "
              f"({r['region']}) names table 0x{r['table_runtime']:04X}")
    for immediate in (0x8038, 0x803A):
        want = bytes((MOV_DPTR, immediate >> 8, immediate & 0xFF))
        hits = [i for i in range(len(d) - 3) if d[i:i + 3] == want]
        print(f"  `mov dptr,#0x{immediate:04X}` byte sites file-wide: {len(hits)}")
    print(f"  {sum(n_sites.values())} `lcall` byte site(s) name the "
          f"{len(called)} reader(s) above")
    print()


def census(d: bytes, sites, stride: int = ENTRY_LEN):
    """Every candidate call site with its table, decoded and checked.

    `stride` is the entry width the *reading reader* walks, passed straight
    into `decode_table()`; a census over one reader's sites and another
    reader's width is the mistake this parameter exists to make impossible."""
    out = []
    for site in sites:
        tbl = decode_table(d, site["file_offset"] + 3, stride)
        out.append((site, tbl, [] if tbl is None else malformed(d, tbl)))
    return out


def print_census(d: bytes, rows) -> None:
    good = [r for r in rows if r[1] is not None and not r[2]]
    print(f"{len(good)} of {len(rows)} candidate site(s) are followed by a "
          "well-formed table")
    print()
    print("  site      region  frame   entries  span              cases")
    for site, tbl, bad in rows:
        if tbl is None:
            print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
                  f"{site['frame_onto']:2}/24   no terminator within "
                  f"{MAX_ENTRIES} entries")
            continue
        cases = [e["case"] for e in tbl["entries"]]
        span = f"0x{tbl['file_offset']:05X}-0x{tbl['end'] - 1:05X}"
        note = "" if not bad else "  MALFORMED: " + "; ".join(bad)
        print(f"  0x{site['file_offset']:05X}  {site['region']:<6}  "
              f"{site['frame_onto']:2}/24  {len(cases):7}  {span}  "
              f"0x{min(cases):02X}-0x{max(cases):02X}{note}")
    total = sum(t["end"] - t["file_offset"] for _, t, b in rows if t and not b)
    print()
    print(f"  {total} bytes of this image read as table data by this method")
    print()


ENTRY_COLUMNS = ["index", "entry_file_offset", "entry_runtime", "target_runtime",
                 "target_file_offset", "stride_from_prev", "target_first_insn",
                 "notes"]

SPAN_COLUMNS = ["site", "region", "site_runtime", "frame_onto", "frame_over",
                "entries", "table_file_offset", "table_end", "table_runtime",
                "first_case", "last_case", "default_runtime", "well_formed"]


def xdata_note(summary) -> str:
    """The `notes` cell for a window. Most of the 15 tables have windows only
    a few bytes long -- a thunk that branches away names no XDATA at all, and
    saying so beats a bare `xdata` with nothing after it."""
    if not summary["xdata"]:
        return "no xdata named in its window"
    return "xdata " + " ".join(f"0x{a:04X}" for a in summary["xdata"])


def entry_rows(d: bytes, tbl):
    """One row per entry, then the `default` row, in ENTRY_COLUMNS order.

    Shared by `--csv` and `--all-csv` so the single-table file and the
    combined one cannot drift into two different readings of the same table."""
    prev = None
    for e in tbl["entries"]:
        s = body_summary(d, tbl, e["target"])
        yield [
            f"0x{e['case']:02X}", f"0x{e['file_offset']:05X}",
            f"0x{e['runtime']:04X}", f"0x{e['target']:04X}",
            f"0x{offset_for_runtime(e['target'], tbl['region']):05X}",
            "" if prev is None else f"0x{e['target'] - prev:02X}",
            s["first_insn"], xdata_note(s),
        ]
        prev = e["target"]
    s = body_summary(d, tbl, tbl["default"])
    yield [
        "default", f"0x{tbl['default_offset']:05X}",
        f"0x{runtime_addr(tbl['default_offset'], True):04X}",
        f"0x{tbl['default']:04X}",
        f"0x{offset_for_runtime(tbl['default'], tbl['region']):05X}",
        "", s["first_insn"],
        "reached when no case matches; " + xdata_note(s),
    ]


def write_csv(d: bytes, tbl) -> None:
    """One table's entries on stdout.

    No comment header: the columns are named after the `bank-*-targets.csv`
    ones so that whatever region map issue #50 lands can read this with
    `csv.DictReader` and fold it in or supersede it, and a leading `#` line
    would be the one thing that stops it."""
    w = csv.writer(sys.stdout)
    w.writerow(ENTRY_COLUMNS)
    for row in entry_rows(d, tbl):
        w.writerow(row)


def write_all_csv(d: bytes, rows) -> None:
    """Every well-formed table's entries in one file, in ascending file order,
    each row naming the `lcall` site its table follows.

    The 0x8038 table is in here too, so a reader of the span list never has to
    special-case it -- bank0-8038-dispatch-table.csv stays the file section 9
    cites, and this one duplicates its eight entries on purpose."""
    w = csv.writer(sys.stdout)
    w.writerow(["site"] + ENTRY_COLUMNS)
    for site, tbl, bad in rows:
        if tbl is None or bad:
            continue
        for row in entry_rows(d, tbl):
            w.writerow([f"0x{site['file_offset']:05X}"] + row)


def write_spans_csv(d: bytes, rows) -> None:
    """One row per candidate call site: the census, not a filtered view of it.

    A site whose bytes do not decode into a table keeps its row with
    `well_formed=no` and empty span fields, because dropping it would turn
    the byte scan's over-count into an invisible one. `table_end` is one past
    the last table byte, so a span test is `table_file_offset <= off <
    table_end`."""
    w = csv.writer(sys.stdout)
    w.writerow(SPAN_COLUMNS)
    for site, tbl, bad in rows:
        row = [f"0x{site['file_offset']:05X}", site["region"],
               f"0x{site['runtime']:04X}", site["frame_onto"],
               site["frame_over"]]
        if tbl is None or bad:
            w.writerow(row + [""] * 7 + ["no"])
            continue
        cases = [e["case"] for e in tbl["entries"]]
        w.writerow(row + [
            len(tbl["entries"]), f"0x{tbl['file_offset']:05X}",
            f"0x{tbl['end']:05X}", f"0x{tbl['runtime']:04X}",
            f"0x{min(cases):02X}", f"0x{max(cases):02X}",
            f"0x{tbl['default']:04X}", "yes",
        ])


# The reader, hand-decoded with `r2 -a 8051` against a make_bank_image.py
# bank-0 image and transcribed in ../annotations/bank-call-audit.md section 9.
# The whole entry layout above is read off these 38 bytes, so they are the
# oracle for it: if they change, nothing else in this file means what it says.
READER_SITE = (0x07151, 0x7151, bytes.fromhex(
    "d083d082f8e4937012740193700da3a393f8740193f5828883e4737402"
    "936860efa3a3a380df"))

# The 0x8038 table as section 9 reports it: (case, entry file offset, target).
TABLE_0X8038 = (
    (0x00, 0x08038, 0x8054), (0x01, 0x0803B, 0x8094), (0x02, 0x0803E, 0x80D7),
    (0x03, 0x08041, 0x811A), (0x04, 0x08044, 0x815D), (0x05, 0x08047, 0x819D),
    (0x06, 0x0804A, 0x81DF), (0x07, 0x0804D, 0x8231),
)

# Target-to-target deltas, which is the reason section 9 exists at all rather
# than a sentence in section 8: that section read a 0x43 stride off the first
# three entries, and it does not survive entry 3.
STRIDES_0X8038 = (0x40, 0x43, 0x43, 0x43, 0x40, 0x42, 0x52)

# The three sites ec/annotations/bank-call-targets.csv offers as independent
# corroboration that this table is entered as code, hand-decoded against the
# bank image each one lives in: (file offset of the instruction the scan's
# bytes actually belong to, its bytes, the scanned site inside them). All
# three are phantoms, which is what makes them worth pinning here.
CORROBORATION_SITES = (
    (0x08040, bytes.fromhex("02811a"), "the case byte of the 0x02 entry plus "
     "the address field of the 0x03 one"),
    (0x0AA17, bytes.fromhex("30e102" "8038"), "displacement of `jnb acc.1` plus "
     "the `sjmp 0xAA54` after it"),
    (0x165D1, bytes.fromhex("4002" "80d7"), "displacement of `jc` plus the "
     "`sjmp 0xE5AC` after it"),
)

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"

# The whole census as section 10 commits it, one tuple per well-formed site:
# (`lcall` file offset, frame_onto, entries, table file offset, one past the
# table's last byte, lowest case, highest case). This is the oracle for
# index-table-spans.csv the way TABLE_0X8038 is for the 0x8038 decode -- a
# different dump gets the census re-derived rather than inheriting this one.
CENSUS_SITES = (
    (0x00DD3, 23, 9, 0x00DD6, 0x00DF5, 0x02, 0x12),
    (0x04064, 24, 15, 0x04067, 0x04098, 0xEC, 0xFF),
    (0x041EE, 24, 14, 0x041F1, 0x0421F, 0x60, 0xD4),
    (0x0424B, 24, 49, 0x0424E, 0x042E5, 0x20, 0xFF),
    (0x08035, 24, 8, 0x08038, 0x08054, 0x00, 0x07),
    (0x08662, 23, 8, 0x08665, 0x08681, 0x00, 0x09),
    (0x0918A, 24, 10, 0x0918D, 0x091AF, 0x00, 0x09),
    (0x09284, 24, 7, 0x09287, 0x092A0, 0x08, 0x38),
    (0x0A34A, 24, 7, 0x0A34D, 0x0A366, 0x00, 0x06),
    (0x0A682, 24, 7, 0x0A685, 0x0A69E, 0x01, 0xFE),
    (0x0D148, 24, 12, 0x0D14B, 0x0D173, 0x06, 0x39),
    (0x0D435, 24, 24, 0x0D438, 0x0D484, 0x90, 0xDD),
    (0x0DDBB, 24, 16, 0x0DDBE, 0x0DDF2, 0x80, 0xFE),
    (0x0EBDC, 24, 8, 0x0EBDF, 0x0EBFB, 0x00, 0x08),
    (0x0F254, 24, 7, 0x0F257, 0x0F270, 0x00, 0x08),
)

TABLE_DATA_BYTES = 663

# The three committed per-site censuses whose rows this family's spans account
# for.
TARGET_CSVS = ("bank-call-targets", "bank-paged-call-targets",
               "bank-relative-branch-targets")

# Rows of those three CSVs that fall inside each CENSUS_SITES span, in the same
# order: (bank-call, bank-paged-call, bank-relative-branch). They are all data
# read as code, so the column totals -- 9, 52, 72, i.e. the 133 section 9
# reports -- are what this family costs the three scans.
PHANTOM_ROWS = (
    (2, 1, 1), (0, 1, 18), (0, 3, 2), (1, 5, 3), (1, 6, 4), (0, 2, 1),
    (1, 12, 4), (0, 1, 4), (1, 1, 0), (1, 2, 1), (0, 10, 0), (0, 3, 9),
    (0, 2, 22), (2, 1, 1), (0, 2, 2),
)

# The two sites section 9 calls the weak ones at 23 of 24 anchors, as the bytes
# section 10 reads by hand: (site, file offset of the instruction before it,
# that instruction's bytes, the first table entry's bytes, its target, its case).
# The preceding instruction is what settles the frame -- it ends exactly on the
# site in both, so the one walk that steps over starts inside its operand.
WEAK_SITES = (
    (0x00DD3, 0x00DD1, bytes.fromhex("e545"), bytes.fromhex("0df502"),
     0x0DF5, 0x02),
    (0x08662, 0x0865F, bytes.fromhex("12ba36"), bytes.fromhex("868100"),
     0x8681, 0x00),
)

# The enumerated set as a value, so a shape cannot be added, dropped or
# respelled without the self-test going red. (name, pattern, from_return_address)
SHAPE_ENUMERATION = (
    ("pop-dph-dpl-selector-r0", "d083d082f8", True),
    ("pop-dpl-dph-selector-r0", "d082d083f8", True),
    ("pop-dph-dpl-selector-rn", "d083d082f9", True),
    ("pop-dph-dpl-selector-r7", "d083d082ff", True),
    ("pop-dpl-dph-selector-rn", "d082d083f9", True),
    ("pop-dpl-dph-selector-r7", "d082d083ff", True),
    ("pop-dph-dpl-selector-direct", "d083d082f5", True),
    ("pop-dpl-dph-selector-direct", "d082d083f5", True),
    ("pop-dph-dpl-push-acc", "d083d082e0", True),
    ("pop-dpl-dph-push-acc", "d082d083e0", True),
    ("pop-dph-dpl", "d083d082", True),
    ("pop-dpl-dph", "d082d083", True),
)

# The widened search's own result, as a whole census rather than a sample, so
# that a different dump gets these re-derived instead of inheriting them.
# SHAPE_HITS counts every tier-1 candidate by region; TIER2_SITES is the
# corroborated subset in file order.
SHAPE_HITS = {"common": 18, "bank0": 13, "bank1": 5}

TIER2_SITES = (0x07151, 0x086EA, 0x08716, 0x09410, 0x09439, 0x09484,
               0x0A22E, 0x0A25C, 0x0A282, 0x0A2A7)

# Why the nine bank0 candidates are not readers, and it is the same nine
# bytes each: every one is a `push dph ; push dpl ; mov dptr,#imm` , one read,
# `pop dpl ; pop dph` -- the compiler saving a DPTR it is about to clobber and
# restoring it after, so the pair restores a pointer the same routine pushed
# rather than taking a return address off the stack. Held as the candidate
# offsets and checked as a byte pattern, so the reading is a property of the
# image and not of this comment.
DPTR_RESTORE_SITES = (0x086EA, 0x08716, 0x09410, 0x09439, 0x09484,
                      0x0A22E, 0x0A25C, 0x0A282, 0x0A2A7)

PUSH_DPH_DPL = bytes.fromhex("c083c082")
POP_DPL_DPH = bytes.fromhex("d082d083")
READ_DPTR = (0xE0, 0xFD)  # `movx a,@dptr` and `mov r5,a`, the two spellings
# The low byte of every one of those nine `mov dptr,#imm16` immediates, so
# they all save and restore a pointer into the same 0x0a4x/0x0a50 page.
RESTORED_DPTR_LOW = (0x49, 0x50)

# The direct-address bucket's one site in the main EC, and the reason it is
# not a table: it reads a single byte at 0x1055 and dispatches through the
# bank-switch stub at 0x1100 indexed by it, so it names no table of this
# family's shape. The PD image has none of the shape at all.
DIRECT_ADDRESS_SITES = (0x0104D,)


def phantom_rows(spans):
    """Rows of the three committed censuses whose site falls inside one of
    `spans`, as one (call, paged, relative) tuple per span -- what reading a
    table's bytes as code costs those scans."""
    here = __file__.rsplit("/", 1)[0]
    sites = []
    for name in TARGET_CSVS:
        with open(f"{here}/../annotations/{name}.csv", newline="") as fh:
            sites.append([int(r["file_offset"], 16) for r in csv.DictReader(fh)])
    return tuple(tuple(sum(1 for o in per_csv if lo <= o < hi)
                       for per_csv in sites) for lo, hi in spans)


def self_test(d: bytes) -> int:
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    off, rt, raw = READER_SITE

    # The enumeration itself, held as a value: a shape added, dropped or
    # respelled changes the search, so it cannot change quietly. Longest first
    # is a precondition of the "most specific shape wins" rule, not a style.
    check(tuple((p.name, p.pattern.hex(), p.from_return_address)
                for p in PROLOGUE_SHAPES) == SHAPE_ENUMERATION
          and all(len(p.pattern) for p in PROLOGUE_SHAPES)
          and [len(p.pattern) for p in PROLOGUE_SHAPES]
          == sorted((len(p.pattern) for p in PROLOGUE_SHAPES), reverse=True),
          f"{len(PROLOGUE_SHAPES)} enumerated shape(s), longest pattern first, "
          "each naming itself and whether it takes the pointer off the return "
          f"address (got {[p.name for p in PROLOGUE_SHAPES]})")

    # The widening, and what it did not disturb. The counts are the whole
    # result of this issue: a wider net finds many more candidates and the
    # `lcall` filter still leaves one, so section 9's uniqueness assertion
    # holds against a search that no longer depends on the single literal it
    # was written against.
    readers = find_readers(d)
    per_region = collections.Counter(r["region"] for r in readers)
    check(per_region == SHAPE_HITS,
          f"{sum(SHAPE_HITS.values())} tier-1 candidates over "
          f"{len(PROLOGUE_SHAPES)} shapes -- "
          + ", ".join(f"{k} {v}" for k, v in sorted(SHAPE_HITS.items()))
          + f" (got {dict(sorted(per_region.items()))})")

    tier2 = [r for r in readers if r["walks_table"]]
    check(tuple(r["file_offset"] for r in tier2) == TIER2_SITES,
          f"{len(TIER2_SITES)} of them corroborated by a `movc a,@a+dptr` "
          "within the window, all but one of them in bank0 and none of them "
          f"named by an `lcall` but 0x{off:05X} (got "
          + ", ".join(f"0x{r['file_offset']:05X}" for r in tier2) + ")")

    called = lcalled_readers(d)
    check(tuple(r["file_offset"] for r in called) == (off,),
          "and the `lcall` filter leaves exactly the reader this file was "
          f"written about, at file 0x{off:05X} (got "
          + (", ".join(f"0x{r['file_offset']:05X}" for r in called) or "none")
          + ")")

    check(tuple(r["shape"] for r in called) == ("pop-dph-dpl-selector-r0",),
          "which the enumerated set names by its specific shape rather than "
          f"only as a member of the family (got "
          + ", ".join(r["shape"] for r in called) + ")")

    # Why the other nine are not readers, held as bytes rather than as the
    # verdict read off them: each is the `pop dpl ; pop dph` half of a
    # `push dph ; push dpl ; mov dptr,#0x0a4x ; movx a,@dptr` a few bytes
    # earlier. The push is 8 bytes back, or 9 where the byte read is also
    # kept in `r5`.
    for cand in DPTR_RESTORE_SITES:
        back = 9 if d[cand - 1] == 0xFD else 8
        head = d[cand - back:cand]
        check(head[:4] == PUSH_DPH_DPL
              and head[4] == MOV_DPTR and head[5] == 0x0A
              and head[6] in RESTORED_DPTR_LOW and head[7] == 0xE0
              and d[cand - 1] in READ_DPTR
              and d[cand:cand + 4] == POP_DPL_DPH,
              f"file 0x{cand:05X} is `{d[cand - back:cand + 4].hex(' ')}` -- a "
              f"DPTR pushed at 0x{cand - back:05X} and restored at "
              f"0x{cand:05X} around one read, not a return address off the "
              "stack")

    direct = direct_address_readers(d)
    check(tuple(r["file_offset"] for r in direct) == DIRECT_ADDRESS_SITES,
          f"the direct-address bucket -- `mov dptr,#imm16` then a table walk "
          f"and `jmp @a+dptr` -- is {len(DIRECT_ADDRESS_SITES)} site(s) and is "
          "not this family, so it is reported and not decoded (got "
          + (", ".join(f"0x{r['file_offset']:05X}" for r in direct) or "none")
          + ")")

    # The trampoline half of section 9's blind spots, decided on the
    # committed range rather than deferred to #48. #48's own work -- decoding
    # what the 402 other immediates point at -- is untouched and stays open.
    tramp = trampoline_targets(d)
    lo, hi = TRAMPOLINE_RANGE
    tlo, thi = TRAMPOLINE_IMMEDIATE_RANGE
    check(len(tramp) == 403
          and (min(tramp), max(tramp)) == (lo, hi),
          f"{len(tramp)} BL51 trampolines, entries 0x{lo:04X}-0x{hi:04X} "
          f"(got {len(tramp)}, 0x{min(tramp):04X}-0x{max(tramp):04X})")

    imms = [target for _, target in tramp.values()]
    check(min(imms) == tlo and max(imms) == thi
          and not [t for t in imms if t < 0x8000],
          f"every one of their {len(imms)} DPTR immediates is at or above "
          f"0x8000, spanning 0x{tlo:04X}-0x{thi:04X} (got 0x{min(imms):04X}-"
          f"0x{max(imms):04X}, {len([t for t in imms if t < 0x8000])} below)")

    check(rt not in imms,
          f"and none of them names the reader at 0x{rt:04X}, so no trampoline "
          "caller is a call site `reader_call_sites()` could have found -- the "
          "half of section 9's blind-spot sentence this issue asked about is "
          f"closed and the computed-caller half is not (got "
          f"{len([t for t in imms if t == rt])} naming it)")

    check(d[off:off + len(raw)] == raw,
          f"its {len(raw)} bytes are as hand-decoded -- the entry layout is read "
          "off these and off nothing else")

    # The default-dispatch tail, as the bytes rather than as the conclusion:
    # `inc dptr ; inc dptr` steps past a zero target pair of two bytes and the
    # two `movc`s read the two bytes after it, which is where `TERM_LEN` and
    # `DEFAULT_LEN` come from. Pinned at this reader and at the PD image's
    # three, so "the terminator is four bytes wide" is a reading of these
    # offsets and not a constant scaled by whatever stride it is handed.
    for tail_off in (0x0715F, 0x211AA, 0x211D0, 0x211FC):
        check(d[tail_off:tail_off + len(DEFAULT_TAIL)] == DEFAULT_TAIL,
              f"file 0x{tail_off:05X} is the same "
              f"{len(DEFAULT_TAIL)}-byte default-dispatch tail -- the zero "
              "target pair and the two-byte default after it are "
              f"{TERM_LEN}+{DEFAULT_LEN} bytes at this reader too, and `end` is "
              "four past the terminator whatever the entry stride is")

    # `decode_table()`'s stride is a parameter now, so this module's own width
    # is the default and the 3-byte decodes are unchanged. Asserted over every
    # entry of the census rather than at one table, because "the default is the
    # old constant" is a claim about all of them.
    check(all(decode_table(d, s["file_offset"] + 3)
              == decode_table(d, s["file_offset"] + 3, ENTRY_LEN)
              for s in reader_call_sites(d, rt)),
          "and `decode_table()`'s default stride is still this module's "
          f"{ENTRY_LEN}, so every one of this image's tables decodes as it did "
          "before the stride became a parameter")

    # The two widths the PD readers walk, pinned as bytes rather than as the
    # verdict read off them: a 4-byte record's key is entry bytes +2 and +3,
    # a 6-byte record's is +2 through +5, and `case` is not populated at either
    # because neither has a single case byte.
    for off_4, stride_4, raw_4 in (
            (0x213F9, 4, "14190206 144c0301 14520401 14a30504"),
            (0x22501, 6, "253200000005 251100000008")):
        want = tuple(bytes.fromhex(pair) for pair in raw_4.split())
        got = tuple(d[o:o + stride_4] for o in
                    range(off_4, off_4 + stride_4 * len(want), stride_4))
        wide = decode_table(d, off_4, stride_4)
        head = [] if wide is None else wide["entries"][:len(want)]
        check(got == want
              and len(head) == len(want)
              and all("case" not in e for e in wide["entries"])
              and tuple(e["key"] for e in head)
              == tuple(int.from_bytes(b[2:], "big") for b in want),
              f"file 0x{off_4:05X} reads as {stride_4}-byte records whose first "
              f"two bytes are the target and whose last {stride_4 - 2} are the "
              f"key -- `{raw_4}` (got "
              + " ".join(b.hex() for b in got) + ")")

    check(entry_stride(d, off, off + 0x100) == ENTRY_LEN,
          f"and the stride this reader's own `inc dptr` run gives is "
          f"{ENTRY_LEN} -- the same derivation the PD readers' widths come "
          f"through, checked here so it cannot quietly mean something else at "
          f"0x{off:05X} (got {entry_stride(d, off, off + 0x100)})")

    for immediate in (0x8038, 0x803A):
        want = bytes((MOV_DPTR, immediate >> 8, immediate & 0xFF))
        hits = [i for i in range(len(d) - 3) if d[i:i + 3] == want]
        check(not hits,
              f"no `mov dptr,#0x{immediate:04X}` anywhere in the file, so an "
              "immediate-DPTR scan finds this table zero times "
              f"(got {len(hits)})")

    tbl = decode_table(d, SITE_0X8038 + 3)
    check(tbl is not None and not malformed(d, tbl),
          "the table after the `lcall` at file 0x08035 decodes well-formed")
    if tbl is None:
        print("\nself-test FAILED")
        return 1

    got = tuple((e["case"], e["file_offset"], e["target"]) for e in tbl["entries"])
    check(got == TABLE_0X8038,
          f"{len(TABLE_0X8038)} entries, cases 0x00-0x07, targets "
          f"0x{TABLE_0X8038[0][2]:04X}-0x{TABLE_0X8038[-1][2]:04X} "
          f"(got {len(got)} entries)")

    check(tbl["terminator_offset"] == 0x08050 and tbl["default"] == 0x8274
          and tbl["end"] == 0x08054,
          "terminator at file 0x08050, default 0x8274, table ending at file "
          f"0x08054 (got 0x{tbl['terminator_offset']:05X}, "
          f"0x{tbl['default']:04X}, 0x{tbl['end']:05X})")

    strides = tuple(b[2] - a[2] for a, b in zip(TABLE_0X8038, TABLE_0X8038[1:]))
    check(strides == STRIDES_0X8038,
          "the target stride is 0x43 for the first three steps only and then "
          f"0x40/0x42/0x52 (got {', '.join(f'0x{s:02X}' for s in strides)})")

    # The correction section 9 makes, asserted as the two readings differing
    # on a specific byte rather than as prose: section 8 took file 0x08038 for
    # an `sjmp` whose displacement 0x54 targets 0x808E, and 0x808E is not an
    # entry of the table.
    sjmp_target = 0x803A + d[0x08039]
    check(d[0x08038] == 0x80 and sjmp_target == 0x808E
          and sjmp_target not in [e["target"] for e in tbl["entries"]],
          f"file 0x08038 reads as `sjmp 0x{sjmp_target:04X}` to a byte scan and "
          "0x808E is no entry of the decoded table -- the two readings disagree, "
          "which is what section 9 corrects")

    for site_off, site_raw, what in CORROBORATION_SITES:
        check(d[site_off:site_off + len(site_raw)] == site_raw,
              f"file 0x{site_off:05X} is `{site_raw.hex(' ')}` -- {what}")

    # And the census below, which the widening must not have disturbed. The
    # reader it runs under is the one the search found, not a hard-coded
    # address, so a second reader appearing shows up here as a changed count.
    sites = reader_call_sites(d, called[0]["runtime"])
    check(called[0]["runtime"] == rt and called[0]["file_offset"] == off,
          f"and the census runs under the found reader, file 0x{off:05X} / "
          f"runtime 0x{rt:04X}, rather than an address this file assumed")

    rows = census(d, sites)
    good = [r for r in rows if r[1] is not None and not r[2]]
    check(len(rows) == 15 and len(good) == 15,
          f"15 `lcall` byte sites name the reader and all 15 are followed by a "
          f"well-formed table (got {len(good)} of {len(rows)})")

    got = tuple((s["file_offset"], s["frame_onto"], len(t["entries"]),
                 t["file_offset"], t["end"],
                 min(e["case"] for e in t["entries"]),
                 max(e["case"] for e in t["entries"])) for s, t, _ in good)
    differs = next((g for g, want in zip(got, CENSUS_SITES) if g != want), None)
    check(got == CENSUS_SITES,
          f"the {len(CENSUS_SITES)} spans of index-table-spans.csv, each with "
          "its own frame_onto, entry count and case range"
          + ("" if differs is None else f" (first differing site: {differs})"))

    spans = [(t["file_offset"], t["end"]) for _, t, _ in good]
    total = sum(hi - lo for lo, hi in spans)
    check(total == TABLE_DATA_BYTES,
          f"{TABLE_DATA_BYTES} bytes of this image read as table data by this "
          f"method (got {total})")

    counts = phantom_rows(spans)
    check(counts == PHANTOM_ROWS,
          "the rows each span costs the three committed censuses, per table")

    per_csv = tuple(sum(c[i] for c in counts) for i in range(len(TARGET_CSVS)))
    check(per_csv == (9, 52, 72),
          "9 / 52 / 72 = 133 rows across bank-call-targets.csv, "
          "bank-paged-call-targets.csv and bank-relative-branch-targets.csv, "
          f"which is what section 9 reports (got {' / '.join(map(str, per_csv))} "
          f"= {sum(per_csv)})")

    # The two 23-of-24 sites, pinned as bytes rather than as the verdict read
    # off them: section 10's hand decode is a reading of these and stops being
    # worth anything if they are not what it read.
    for weak, prev_off, prev_raw, entry_raw, target, case in WEAK_SITES:
        tbl = decode_table(d, weak + 3)
        check(d[prev_off:prev_off + len(prev_raw)] == prev_raw
              and prev_off + len(prev_raw) == weak
              and d[weak:weak + 3] == bytes((LCALL, rt >> 8, rt & 0xFF))
              and d[weak + 3:weak + 3 + ENTRY_LEN] == entry_raw
              and tbl["entries"][0]["target"] == target
              and tbl["entries"][0]["case"] == case,
              f"file 0x{weak:05X} is `{prev_raw.hex(' ')}` ending on the "
              f"`lcall` and `{entry_raw.hex(' ')}` after it, i.e. "
              f"0x{target:04X} case 0x{case:02X}")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--at", help="file offset of the `lcall` preceding a table, "
                                 "e.g. 0x0D148 (default: the 0x8038 table)")
    ap.add_argument("--region", choices=sorted(REGION_SETS), default="main",
                    help="which regions to search for readers: the main EC "
                         "(common/bank0/bank1), the ITE8850-PD image at "
                         "0x20000, or both. The search is the same either way; "
                         "pd_index_tables.py is the PD census built on it")
    ap.add_argument("--all-tables", action="store_true",
                    help="decode the table after every call site naming the reader")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per entry on stdout instead of the tables")
    ap.add_argument("--all-csv", action="store_true",
                    help="write one row per entry for every well-formed table, "
                         "prefixed with the call site it follows")
    ap.add_argument("--spans-csv", action="store_true",
                    help="write one row per candidate call site with its "
                         "table's span, frame evidence and case range")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the widened reader search, the trampoline "
                         "immediates, the reader's bytes, the 0x8038 table, "
                         "every span of the call-site census and the rows each "
                         "one costs the three committed censuses")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded decodes were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)

    regions = REGION_SETS[args.region]
    readers = find_readers(d, regions)
    # The census is under every reader the search found that a caller
    # actually names. On this image that is one in the main EC and three in
    # the PD, so the count is asserted by --self-test rather than by a
    # hard-coded "expect exactly one" that a second reader would fail on.
    called = lcalled_readers(d, regions)
    if not called:
        print(f"no reader of the enumerated shapes is named by an `lcall` in "
              f"{'/'.join(regions)} -- rerun --self-test", file=sys.stderr)
        return 1
    sites = [s for r in called for s in reader_call_sites(d, r["runtime"], regions)]

    if args.all_csv or args.spans_csv:
        rows = census(d, sites)
        (write_all_csv if args.all_csv else write_spans_csv)(d, rows)
        return 0

    # `--at` names a main-EC file offset, so with no `--at` and a region set
    # that is not the main EC there is no single table to default to. The
    # census over the region's readers is the reading in that case, and it is
    # the one pd_index_tables.py writes up.
    if not args.at and regions != MAIN_EC:
        print_readers(d, readers, called, regions)
        print_census(d, census(d, sites))
        return 0

    site = int(args.at, 16) if args.at else SITE_0X8038
    tbl = decode_table(d, site + 3)

    if args.csv:
        if tbl is None:
            print(f"no table after file 0x{site:05X}", file=sys.stderr)
            return 1
        write_csv(d, tbl)
        return 0

    print_readers(d, readers, called, regions)
    if args.all_tables:
        print_census(d, census(d, sites))
        return 0
    if tbl is None:
        print(f"no table after file 0x{site:05X}")
        return 1
    print_table(d, tbl)
    print_bodies(d, tbl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
