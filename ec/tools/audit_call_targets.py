#!/usr/bin/env python3
"""Enumerate every direct call in the main EC image and bucket its target, to
test the banking assumption trace_xdata_refs.offset_for_runtime() rests on.

Sections 1-4 cover the 3-byte absolute forms `lcall`/`ljmp`, which are the
ones that can name an address in another bank; section 5 covers the 2-byte
paged forms, which cannot.

offset_for_runtime() maps a call target back to a file offset by assuming the
ordinary Keil convention: a target below 0x8000 is in the common area, a
target at or above 0x8000 is in the *same* bank as the caller. Every EC-side
`--callee-depth 1` verdict register_ref_table.py will ever produce inherits
that assumption, so this tool counts the populations it applies to:

  bucket A  target < 0x8000                    -- common area, unambiguous
  bucket B  target >= 0x8000, caller in a bank -- the assumed same-bank case
  bucket C  target >= 0x8000, caller in common -- offset_for_runtime() None

**What this cannot do, and it is the first thing to say.** REGIONS gives
bank0 and bank1 the same base 0x8000, and nothing in an `lcall` names a bank:
a bank-to-same-bank call and a bank-to-other-bank call are the same three
bytes. So no count here can *prove* the assumption. What it can do is say how
large each population is, show where the linker's own cross-bank path goes
(the BL51 trampoline block, section 2 below), and for each bucket-B target
say whether the caller's own bank holds plausible code at that address while
the other bank holds erased flash, or the reverse -- the second being the
shape that would falsify the assumption.

Two framings are reported for every count, never one:

  * a *byte-scan upper bound* -- every 0x02/0x12 byte in the region, which
    over-counts because those values also occur as operand bytes inside other
    instructions and inside data tables; and
  * an *anchored-decode count* -- the subset that at least one of the 24
    preceding byte anchors decodes onto, via disasm8051.converges_from().

Neither settles framing (converges_from()'s own docstring says why), and the
anchored count is demonstrably not phantom-free: section 4 lists sites that
score 24 of 24 and are plainly inside an address table. Read the pair.

Section 5 adds the 2-byte paged family, `ajmp`/`acall`. Those are not a
banking question the way the absolute forms are -- a paged target is inside
the page the caller is already executing from, so it cannot leave the
caller's own region and needs no bank chosen for it -- so they are counted
separately rather than bucketed A/B/C. The point of counting them is that it
*shrinks* the population offset_for_runtime()'s same-bank assumption carries;
it settles nothing about bucket B. And the byte scan over-counts harder here
than above, not less: a 2-byte opcode matches 16 of the 256 byte values, so
any dense data table produces paged phantoms by the hundred.

Section 6 adds the third and last statically-resolvable family, the PC-relative
branches -- `sjmp`, `jc`/`jnc`/`jz`/`jnz`, `jb`/`jnb`/`jbc`, `cjne`, `djnz`.
Their targets are computable without a bank too, but for a different reason
than the paged forms: a rel8 displacement reaches [-128, +127] of the next PC,
so a relative branch can only leave the caller's region from within 128 bytes
of a region edge. Unlike a paged target, that is *possible*, so whether this
image has such a site is a checked property of this image rather than an
opcode fact -- --self-test walks every site and reports it. And the byte scan
over-counts harder again: 29 of the 256 byte values open a relative branch,
against 16 paged and 2 absolute.

Blind spots, none of which this tool closes: framing is unsettled in both
directions (section 2), computed targets via `jmp @a+dptr` or the
trampoline's DPTR-carried target are invisible to any byte scan, and banks 2
and 3 are taken as unused on the word of find_banks.py rather than
re-derived.

Usage:
    python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --csv > sites.csv
    python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --paged-csv > paged.csv
    python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --relative-csv > rel.csv
    python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import sys

from disasm8051 import (OPCODE_LEN, REL_OPCODES, REL_SITES, converges_from,
                        paged_target, relative_target)
from find_banks import START_OPCODES, STUB_PROLOGUE, find_stubs
from trace_xdata_refs import (PD_MARKER, REGIONS, offset_for_runtime,
                              runtime_addr)

CALL_OPCODES = (0x02, 0x12)  # ljmp, lcall -- the 3-byte absolute forms

# The 2-byte paged forms are a whole opcode family: the low 5 bits are fixed
# and the high 3 carry target bits, so `op & 0x1F` is the whole test.
PAGED_OPCODES = (0x01, 0x11)  # ajmp, acall

PAGE = 0x800  # what a paged target cannot leave

# How far a rel8 branch reaches either side of the next PC. A site further than
# this from both of its region's edges therefore cannot resolve outside it.
REL_REACH = 128

# Regions this audit covers, in REGIONS order. The PD image is flat, so its
# calls are not a banking question and are out of scope here.
AUDITED = ("common", "bank0", "bank1")

# The other bank a bucket-B target could have been meant for. Two banks are
# mapped in this image; find_banks.py reports no trampoline callers for banks
# 2 and 3, which this tool takes as given rather than re-deriving.
OTHER_BANK = {"bank0": "bank1", "bank1": "bank0"}

# Shortest run of 0xFF read as erased flash rather than as instructions.
# find_banks.py's scoring tests a single byte for 0xFF, which is fine for the
# question it asks and wrong for this one: 0xFF is `mov r7,a`, one of the
# commonest bytes in Keil C51 output. Four bucket-B targets in this image
# start with a lone 0xFF and continue into perfectly ordinary code, so a
# one-byte test would have reported them as calls into erased flash.
MIN_ERASED_RUN = 16


def erased_runs(d: bytes, lo: int, hi: int, minlen: int = MIN_ERASED_RUN):
    """[lo, hi) runs of at least `minlen` 0xFF bytes, as (start, end) pairs."""
    out = []
    start = None
    for i in range(lo, hi + 1):
        if i < hi and d[i] == 0xFF:
            if start is None:
                start = i
        elif start is not None:
            if i - start >= minlen:
                out.append((start, i))
            start = None
    return out


def byte_class(d: bytes, off: int, runs) -> str:
    """How the byte at `off` reads: a plausible Keil function entry, erased
    flash, or neither. `entry` is find_banks.py's START_OPCODES heuristic and
    is exactly as strong as that -- a scoring aid, not a decode."""
    if any(a <= off < b for a, b in runs):
        return "erased"
    return "entry" if d[off] in START_OPCODES else "other"


def call_sites(d: bytes, lo: int, hi: int):
    """(offset, opcode, target) for every 0x02/0x12 byte in [lo, hi)."""
    for i in range(lo, hi - 2):
        if d[i] in CALL_OPCODES:
            yield i, d[i], (d[i + 1] << 8) | d[i + 2]


def paged_sites(d: bytes, lo: int, hi: int):
    """(offset, opcode, target) for every ajmp/acall-shaped byte in [lo, hi).

    Stops at hi - 1 so both bytes of the instruction are inside the region:
    the alternative reads the first byte of the next region as an operand,
    which is the one shape whose target could land outside the caller's
    region."""
    for i in range(lo, hi - 1):
        if d[i] & 0x1F in PAGED_OPCODES:
            yield i, d[i], paged_target(d[i], d[i + 1], runtime_addr(i, True))


def relative_sites(d: bytes, lo: int, hi: int):
    """(offset, opcode, target) for every relative-branch-shaped byte in
    [lo, hi).

    Same region discipline paged_sites() has, but the instruction is 2 or 3
    bytes depending on the opcode, so the whole of it is required to fit: a
    3-byte form in a region's last two bytes would take its displacement from
    the next region. The displacement is the instruction's last byte, which is
    what relative_target()'s docstring is about."""
    for i in range(lo, hi):
        op = d[i]
        if op in REL_OPCODES and i + OPCODE_LEN[op] <= hi:
            yield i, op, relative_target(op, d[i + OPCODE_LEN[op] - 1],
                                         runtime_addr(i, True))


def edge_distance(off: int, lo: int, hi: int) -> int:
    """Bytes from `off` to the nearer edge of [lo, hi)."""
    return min(off - lo, hi - 1 - off)


def bucket_of(region: str, target: int) -> str:
    if target < 0x8000:
        return "A"
    return "C" if region == "common" else "B"


def bank_switch_stubs(d: bytes):
    """{stub address: bank it selects}, from find_banks.py's scan."""
    return dict(find_stubs(d))


def trampolines(d: bytes, stubs, limit: int = 0x8000):
    """{entry address: (bank, target)} for the BL51 bank-switch trampolines.

    Same `MOV DPTR,#target ; LJMP/LCALL stub` shape find_banks.py counts, but
    keyed by the address a caller would call rather than by the stub, because
    the question here is who calls them from where."""
    out = {}
    for i, op, target in call_sites(d, 0, limit):
        if i < 3 or d[i - 3] != 0x90:
            continue
        if target in stubs:
            out[i - 3] = (stubs[target], (d[i - 2] << 8) | d[i - 1])
    return out


def region_bounds(name: str):
    return next((lo, hi) for n, lo, hi, _, _ in REGIONS if n == name)


def survey(d: bytes):
    """Every audited call site, as a list of dicts -- the one pass both the
    tables and --csv are derived from, so they cannot disagree."""
    stubs = bank_switch_stubs(d)
    tramp = trampolines(d, stubs)
    runs = {name: erased_runs(d, *region_bounds(name)) for name in AUDITED}
    rows = []
    for name in AUDITED:
        lo, hi = region_bounds(name)
        for off, op, target in call_sites(d, lo, hi):
            onto, over = converges_from(d, off)
            row = {
                "region": name,
                "file_offset": off,
                "runtime": runtime_addr(off, True),
                "opcode": "ljmp" if op == 0x02 else "lcall",
                "target": target,
                "bucket": bucket_of(name, target),
                "anchored": onto > 0,
                "frame_onto": onto,
                "frame_over": over,
                "calls_stub": stubs.get(target),
                "calls_trampoline": tramp[target][0] if target in tramp else None,
                "own_bank": "",
                "other_bank": "",
            }
            if row["bucket"] == "B":
                other = OTHER_BANK[name]
                row["own_bank"] = byte_class(
                    d, offset_for_runtime(target, name), runs[name])
                row["other_bank"] = byte_class(
                    d, offset_for_runtime(target, other), runs[other])
            rows.append(row)
    return rows, stubs, tramp


def paged_survey(d: bytes):
    """Every audited paged site, in the same one-pass shape survey() has, so
    section 5 and --paged-csv cannot disagree either.

    There is no bucket column: a paged target is in the caller's own page and
    therefore its own region, so the A/B/C question the absolute forms raise
    does not arise. `in_region` is that claim re-derived per site rather than
    assumed -- --self-test fails on any row where it is false."""
    stubs = bank_switch_stubs(d)
    tramp = trampolines(d, stubs)
    runs = {name: erased_runs(d, *region_bounds(name)) for name in AUDITED}
    rows = []
    for name in AUDITED:
        lo, hi = region_bounds(name)
        for off, op, target in paged_sites(d, lo, hi):
            onto, over = converges_from(d, off)
            toff = offset_for_runtime(target, name)
            inside = toff is not None and lo <= toff < hi
            rows.append({
                "region": name,
                "file_offset": off,
                "runtime": runtime_addr(off, True),
                "opcode": "ajmp" if op & 0x1F == 0x01 else "acall",
                "target": target,
                "target_offset": toff,
                "in_region": inside,
                "target_class": byte_class(d, toff, runs[name]) if inside else "",
                "anchored": onto > 0,
                "frame_onto": onto,
                "frame_over": over,
                "calls_stub": stubs.get(target),
                "calls_trampoline": tramp[target][0] if target in tramp else None,
            })
    return rows, stubs, tramp


def relative_survey(d: bytes):
    """Every audited relative-branch site, in the same one-pass shape the other
    two surveys have, so section 6 and --relative-csv cannot disagree.

    `in_region` is not the settled claim it is for the paged family: a rel8
    target can leave the caller's region, from within REL_REACH bytes of an
    edge. It is recorded per site and counted, not asserted away. `length` and
    `disp` are carried because the 2-byte/3-byte framing is what decides where
    the displacement byte is, and a reader re-deriving a target from the CSV
    needs both."""
    stubs = bank_switch_stubs(d)
    tramp = trampolines(d, stubs)
    runs = {name: erased_runs(d, *region_bounds(name)) for name in AUDITED}
    rows = []
    for name in AUDITED:
        lo, hi = region_bounds(name)
        for off, op, target in relative_sites(d, lo, hi):
            onto, over = converges_from(d, off)
            toff = offset_for_runtime(target, name)
            inside = toff is not None and lo <= toff < hi
            rows.append({
                "region": name,
                "file_offset": off,
                "runtime": runtime_addr(off, True),
                "opcode": REL_OPCODES[op],
                "length": OPCODE_LEN[op],
                "disp": d[off + OPCODE_LEN[op] - 1],
                "target": target,
                "target_offset": toff,
                "in_region": inside,
                "target_class": byte_class(d, toff, runs[name]) if inside else "",
                "anchored": onto > 0,
                "frame_onto": onto,
                "frame_over": over,
                "calls_stub": stubs.get(target),
                "calls_trampoline": tramp[target][0] if target in tramp else None,
            })
    return rows, stubs, tramp


def counted(rows, **match):
    """`upper / anchored` for the subset of `rows` matching every keyword."""
    sel = [r for r in rows if all(r[k] == v for k, v in match.items())]
    return len(sel), sum(1 for r in sel if r["anchored"])


def print_buckets(rows) -> None:
    print("## 1. Call-target buckets, as `byte-scan upper bound / anchored-decode count`")
    print()
    print("| region | A: target < 0x8000 | B: >= 0x8000 from a bank | C: >= 0x8000 from common |")
    print("|---|---:|---:|---:|")
    for name in AUDITED:
        cells = []
        for b in "ABC":
            upper, anchored = counted(rows, region=name, bucket=b)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()


def print_trampolines(rows, stubs, tramp) -> None:
    print("## 2. Where the linker's own cross-bank calls go")
    print()
    for addr, bank in sorted(stubs.items()):
        callers = sum(1 for e, (b, _) in tramp.items() if b == bank)
        print(f"  stub 0x{addr:04X} selects bank {bank}: "
              f"{callers} trampoline(s) route through it")
    entries = sorted(tramp)
    if entries:
        print(f"  {len(tramp)} trampolines, common area 0x{entries[0]:04X}-0x{entries[-1]:04X}, "
              f"{sum(1 for _, t in tramp.values() if t >= 0x8000)} of them targeting >= 0x8000")
    print()
    print("Calls into that trampoline block, by the bank the trampoline selects:")
    print()
    print("| caller region | -> bank 0 | -> bank 1 |")
    print("|---|---:|---:|")
    for name in AUDITED:
        cells = []
        for bank in (0, 1):
            upper, anchored = counted(rows, region=name, calls_trampoline=bank)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()
    print("Calls to a stub address itself. Every one of these is a trampoline's")
    print("own tail instruction -- trampolines() found them by that shape -- so a")
    print("count here that exceeds the trampoline count would be a caller reaching")
    print("a stub without setting DPTR first:")
    for name in AUDITED:
        for bank in sorted(set(stubs.values())):
            upper, anchored = counted(rows, region=name, calls_stub=bank)
            if upper:
                print(f"  {name}: {upper} / {anchored} to the bank-{bank} stub")
    print()


def print_bucket_b(rows) -> None:
    print("## 3. Bucket B: what each target's own bank holds, against the other bank")
    print()
    print("`entry` is find_banks.py's START_OPCODES heuristic, `erased` a run of")
    print(f"at least {MIN_ERASED_RUN} 0xFF bytes, `other` neither. An `erased`/live pair with the")
    print("caller's own bank erased is the shape that would falsify the same-bank")
    print("assumption; a live/`erased` pair is consistent with it.")
    print()
    print("| caller | distinct targets | own / other bank | targets | sites |")
    print("|---|---:|---|---:|---:|")
    for name in ("bank0", "bank1"):
        sel = [r for r in rows if r["region"] == name and r["bucket"] == "B"]
        per_target = collections.defaultdict(list)
        for r in sel:
            per_target[r["target"]].append(r)
        hist = collections.Counter(
            (rs[0]["own_bank"], rs[0]["other_bank"]) for rs in per_target.values())
        first = True
        for (own, other), n in sorted(hist.items(), key=lambda kv: -kv[1]):
            sites = sum(len(rs) for t, rs in per_target.items()
                        if (rs[0]["own_bank"], rs[0]["other_bank"]) == (own, other))
            print(f"| {'`' + name + '`' if first else ''} "
                  f"| {len(per_target) if first else ''} "
                  f"| `{own}` / `{other}` | {n} | {sites} |")
            first = False
    print()


def print_bucket_c(d: bytes, rows, tramp) -> None:
    sel = [r for r in rows if r["bucket"] == "C"]
    anchored = [r for r in sel if r["anchored"]]
    targets = {r["target"] for r in sel}
    known = {t for _, t in tramp.values()}
    print("## 4. Bucket C: the sites offset_for_runtime() returns None for")
    print()
    print(f"  {len(sel)} site(s) upper bound, {len(anchored)} anchored, "
          f"{len(targets)} distinct target(s)")
    print(f"  {len(targets & known)} of those targets is/are also a banked entry point "
          "some trampoline names")
    print()
    print("The most strongly framed of them, by converges_from() score -- the ones")
    print("worth reading bytes for before treating any of this bucket as a call:")
    print()
    print("| file | ljmp/lcall | target | frame onto/over | preceding bytes |")
    print("|---|---|---|---:|---|")
    for r in sorted(anchored, key=lambda r: -r["frame_onto"])[:10]:
        off = r["file_offset"]
        prev = " ".join(f"{b:02x}" for b in d[max(0, off - 6):off])
        print(f"| `0x{off:05X}` | {r['opcode']} | `0x{r['target']:04X}` "
              f"| {r['frame_onto']}/{r['frame_onto'] + r['frame_over']} "
              f"| `{prev}` |")
    print()


def print_paged(rows) -> None:
    print("## 5. The 2-byte paged family: `ajmp`/`acall`")
    print()
    print("A paged target is the *next* instruction's 2 KiB page with 11 bits")
    print("substituted in, so it never leaves the page the caller is executing")
    print("from, and never leaves the caller's region -- every mapped region is a")
    print("whole number of aligned pages. That is opcode semantics plus a checked")
    print("property of REGIONS, not a result read out of this image, and it says")
    print("nothing about whether the bucket-B assumption above holds; it only")
    print("removes this family from the population that needs it.")
    print()
    print("The byte scan over-counts harder here than for the 3-byte forms: 16 of")
    print("the 256 byte values open a paged instruction, so read the pair.")
    print()
    print("| region | ajmp | acall | both |")
    print("|---|---:|---:|---:|")
    for name in AUDITED:
        cells = []
        for op in ("ajmp", "acall", None):
            match = {"region": name} if op is None else {"region": name, "opcode": op}
            upper, anchored = counted(rows, **match)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()
    print("What the target byte reads as -- `entry` is find_banks.py's START_OPCODES")
    print(f"heuristic, `erased` a run of at least {MIN_ERASED_RUN} 0xFF bytes, `other` neither.")
    print("Used as the scoring aid it is: `erased` marks a target worth reading bytes")
    print("for, `entry` is not a decode:")
    print()
    print("| region | entry | other | erased |")
    print("|---|---:|---:|---:|")
    for name in AUDITED:
        cells = []
        for cls in ("entry", "other", "erased"):
            upper, anchored = counted(rows, region=name, target_class=cls)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()
    print("Paged sites landing on the BL51 path. The trampoline block 0x1150-0x1ABC")
    print("spans pages a common-area paged call can reach from inside, so unlike the")
    print("banks this is a route a paged instruction could take:")
    for name in AUDITED:
        for bank in (0, 1):
            upper, anchored = counted(rows, region=name, calls_trampoline=bank)
            if upper:
                print(f"  {name}: {upper} / {anchored} onto a bank-{bank} trampoline entry")
        for bank in sorted({r["calls_stub"] for r in rows if r["calls_stub"] is not None}):
            upper, anchored = counted(rows, region=name, calls_stub=bank)
            if upper:
                print(f"  {name}: {upper} / {anchored} onto the bank-{bank} stub itself")
    if not any(r["calls_trampoline"] is not None or r["calls_stub"] is not None
               for r in rows):
        print("  none, by this scan")
    escaped = [r for r in rows if not r["in_region"]]
    print()
    print(f"  {len(escaped)} of {len(rows)} paged site(s) resolve outside the caller's "
          "own region")
    print()


REL_FAMILIES = ("sjmp", "jc", "jnc", "jz", "jnz", "jb", "jnb", "jbc",
                "cjne", "djnz")


def print_relative(rows) -> None:
    print("## 6. The PC-relative family: `sjmp`/`jc`/`jnc`/`jz`/`jnz`/"
          "`jb`/`jnb`/`jbc`/`cjne`/`djnz`")
    print()
    print("A rel8 displacement reaches [-128, +127] of the *next* PC, so a")
    print("relative branch can only leave the caller's region from within")
    print(f"{REL_REACH} bytes of a region edge. That is opcode arithmetic plus the")
    print("region table; unlike a paged target it does not forbid the escape, so")
    print("whether this image has one is counted below rather than assumed.")
    print()
    print("The byte scan over-counts harder here than anywhere above: 29 of the")
    print("256 byte values open a relative branch, against 16 paged and 2")
    print("absolute. Read the pair; the upper bound is not a site count.")
    print()
    header = " | ".join(REL_FAMILIES)
    print(f"| region | {header} | all |")
    print("|---" * (len(REL_FAMILIES) + 2) + "|")
    for name in AUDITED:
        cells = []
        for op in REL_FAMILIES + (None,):
            match = {"region": name} if op is None else {"region": name, "opcode": op}
            upper, anchored = counted(rows, **match)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()
    print("By instruction length, which is what decides where the displacement")
    print("byte is read from:")
    print()
    print("| region | 2-byte | 3-byte |")
    print("|---|---:|---:|")
    for name in AUDITED:
        cells = []
        for n in (2, 3):
            upper, anchored = counted(rows, region=name, length=n)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()
    print("What the target byte reads as -- the same START_OPCODES/erased-run")
    print("scoring aid section 5 uses, and no more of a decode here than there:")
    print()
    print("| region | entry | other | erased |")
    print("|---|---:|---:|---:|")
    for name in AUDITED:
        cells = []
        for cls in ("entry", "other", "erased"):
            upper, anchored = counted(rows, region=name, target_class=cls)
            cells.append("-" if not upper else f"{upper} / {anchored}")
        print(f"| `{name}` | " + " | ".join(cells) + " |")
    print()
    print("Relative sites landing on the BL51 path. A common-area branch can")
    print("reach the trampoline block 0x1150-0x1ABC if it starts near enough to")
    print("it; a bank never can:")
    for name in AUDITED:
        for bank in (0, 1):
            upper, anchored = counted(rows, region=name, calls_trampoline=bank)
            if upper:
                print(f"  {name}: {upper} / {anchored} onto a bank-{bank} trampoline entry")
        for bank in sorted({r["calls_stub"] for r in rows if r["calls_stub"] is not None}):
            upper, anchored = counted(rows, region=name, calls_stub=bank)
            if upper:
                print(f"  {name}: {upper} / {anchored} onto the bank-{bank} stub itself")
    if not any(r["calls_trampoline"] is not None or r["calls_stub"] is not None
               for r in rows):
        print("  none, by this scan")
    print()
    escaped = [r for r in rows if not r["in_region"]]
    print(f"  {len(escaped)} of {len(rows)} relative site(s) resolve outside the "
          "caller's own region")
    for r in sorted(escaped, key=lambda r: -r["frame_onto"])[:10]:
        lo, hi = region_bounds(r["region"])
        print(f"    0x{r['file_offset']:05X} {r['opcode']} -> 0x{r['target']:04X}, "
              f"{edge_distance(r['file_offset'], lo, hi)} byte(s) from a "
              f"{r['region']} edge, frame {r['frame_onto']}/"
              f"{r['frame_onto'] + r['frame_over']}")
    print()


def write_csv(rows) -> None:
    w = csv.writer(sys.stdout)
    w.writerow(["file_offset", "region", "runtime", "opcode", "target", "bucket",
                "frame_onto", "frame_over", "calls_stub", "calls_trampoline",
                "own_bank", "other_bank"])
    for r in rows:
        w.writerow([
            f"0x{r['file_offset']:05X}", r["region"],
            f"0x{r['runtime']:04X}" if r["runtime"] is not None else "",
            r["opcode"], f"0x{r['target']:04X}", r["bucket"],
            r["frame_onto"], r["frame_over"],
            "" if r["calls_stub"] is None else r["calls_stub"],
            "" if r["calls_trampoline"] is None else r["calls_trampoline"],
            r["own_bank"], r["other_bank"],
        ])


def write_paged_csv(rows) -> None:
    """A sibling of write_csv() rather than more columns on it: `bucket`,
    `own_bank` and `other_bank` are absolute-form questions that have no
    answer for a paged site, and bank-call-targets.csv stays as committed."""
    w = csv.writer(sys.stdout)
    w.writerow(["file_offset", "region", "runtime", "opcode", "target",
                "target_offset", "in_region", "target_class", "frame_onto",
                "frame_over", "calls_stub", "calls_trampoline"])
    for r in rows:
        w.writerow([
            f"0x{r['file_offset']:05X}", r["region"], f"0x{r['runtime']:04X}",
            r["opcode"], f"0x{r['target']:04X}",
            f"0x{r['target_offset']:05X}" if r["target_offset"] is not None else "",
            "yes" if r["in_region"] else "no", r["target_class"],
            r["frame_onto"], r["frame_over"],
            "" if r["calls_stub"] is None else r["calls_stub"],
            "" if r["calls_trampoline"] is None else r["calls_trampoline"],
        ])


def write_relative_csv(rows) -> None:
    """A third sibling: the paged table's columns minus the absolute-form ones,
    plus `length` and `disp`, which are what a reader needs to re-derive a
    target by hand. `calls_stub`/`calls_trampoline` stay, because a common-area
    relative branch can reach the BL51 block the way a paged one can."""
    w = csv.writer(sys.stdout)
    w.writerow(["file_offset", "region", "runtime", "opcode", "length", "disp",
                "target", "target_offset", "in_region", "target_class",
                "frame_onto", "frame_over", "calls_stub", "calls_trampoline"])
    for r in rows:
        w.writerow([
            f"0x{r['file_offset']:05X}", r["region"], f"0x{r['runtime']:04X}",
            r["opcode"], r["length"], f"0x{r['disp']:02X}",
            f"0x{r['target']:04X}",
            f"0x{r['target_offset']:05X}" if r["target_offset"] is not None else "",
            "yes" if r["in_region"] else "no", r["target_class"],
            r["frame_onto"], r["frame_over"],
            "" if r["calls_stub"] is None else r["calls_stub"],
            "" if r["calls_trampoline"] is None else r["calls_trampoline"],
        ])


# The four stub sites ec/annotations/lightbar-bat-flow.md 2 records, and the
# round-trip assertion its 3.5 prints. Both are load-bearing for this audit:
# section 2 is the stub evidence, and offset_for_runtime() is the function
# under test.
STUB_SITES = ((0x1100, 0), (0x1114, 1), (0x1128, 2), (0x113C, 3))

# Paged sites hand-decoded with `r2 -a 8051` against a make_bank_image.py
# image, as (file offset, runtime address, bytes, target). 0x02190 is the
# `ajmp 0x2009` ../annotations/bank-call-audit.md 5 already transcribed while
# reading bucket C. 0x167FF is this image's only paged site whose next PC
# crosses a page boundary, so its target is in the *following* page -- the
# off-by-one page arithmetic invites, and the reason paged_target() adds 2
# before masking. Commands in 7 of the same file.
PAGED_SITES = (
    (0x02190, 0x2190, b"\x01\x09", 0x2009),
    (0x167FF, 0xE7FF, b"\x01\x53", 0xE853),
)

# The relative-branch hand decodes live in disasm8051.REL_SITES, next to the
# function they pin; this tool re-checks them through its own site walk, which
# is what would catch relative_sites() reading the displacement from the wrong
# byte while relative_target() stayed correct. Transcripts in 8 of
# ../annotations/bank-call-audit.md.


def self_test(d: bytes) -> int:
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    stubs = tuple(sorted(bank_switch_stubs(d).items()))
    check(stubs == STUB_SITES,
          f"4 BL51 stub sites at {', '.join(f'0x{a:04X}' for a, _ in STUB_SITES)} "
          f"selecting banks 0-3 (got {', '.join(f'0x{a:04X}=bank{b}' for a, b in stubs)})")

    prologues = [i for i in range(0, 0x18000) if d[i:i + 3] == STUB_PROLOGUE]
    check(len(prologues) == 4,
          f"the `C0 08 74` prologue occurs 4 times in the main EC image "
          f"(got {len(prologues)})")
    pd = [i for i in range(0x20000, 0x30000) if d[i:i + 3] == STUB_PROLOGUE]
    check(not pd, f"and 0 times in the PD image (got {len(pd)})")

    broken = []
    for name, lo, hi, base, _ in REGIONS:
        if base is None:
            continue
        for off in (lo, lo + 0x137, hi - 1):
            if offset_for_runtime(runtime_addr(off, True), name) != off:
                broken.append(f"{name} 0x{off:05X}")
    check(not broken,
          "offset_for_runtime()/runtime_addr() round-trip for every mapped "
          f"region{'' if not broken else ' -- broken at ' + ', '.join(broken)}")

    check(offset_for_runtime(0x8000, "common") is None,
          "a common-area call to 0x8000 stays unresolvable (bucket C returns None)")

    for foff, rt, raw, want in PAGED_SITES:
        got = paged_target(raw[0], raw[1], rt)
        check(d[foff:foff + 2] == raw and got == want,
              f"file 0x{foff:05X} (runtime 0x{rt:04X}) is `{raw.hex(' ')}` targeting "
              f"0x{want:04X} (got `{d[foff:foff + 2].hex(' ')}` -> 0x{got:04X})")

    _, rt, _, want = PAGED_SITES[1]
    check(want & ~(PAGE - 1) == (rt + 2) & ~(PAGE - 1) != rt & ~(PAGE - 1),
          f"0x{rt:04X}'s target 0x{want:04X} is in the next instruction's page "
          f"0x{(rt + 2) & ~(PAGE - 1):04X}, not the opcode's own 0x{rt & ~(PAGE - 1):04X}")

    misaligned = [f"{name} 0x{lo:05X}" for name, lo, hi, base, _ in REGIONS
                  if base is not None and ((lo - base) % PAGE or (hi - lo) % PAGE)]
    check(not misaligned,
          "every mapped region is a whole number of 2 KiB pages aligned identically "
          "in file offset and runtime base -- the property the never-leaves-its-region "
          f"claim rests on{'' if not misaligned else ' -- broken at ' + ', '.join(misaligned)}")

    escaped, total = [], 0
    for name in AUDITED:
        lo, hi = region_bounds(name)
        for off, _, target in paged_sites(d, lo, hi):
            total += 1
            toff = offset_for_runtime(target, name)
            if toff is None or not lo <= toff < hi:
                escaped.append(f"0x{off:05X}")
    check(not escaped,
          f"all {total} paged site(s) in the audited regions resolve inside the "
          f"caller's own region{'' if not escaped else ' -- escaped at ' + ', '.join(escaped[:8])}")

    walked = {}
    for name in AUDITED:
        lo, hi = region_bounds(name)
        for off, op, target in relative_sites(d, lo, hi):
            walked[off] = (op, target)
    for foff, rt, raw, want in REL_SITES:
        got = walked.get(foff)
        check(d[foff:foff + len(raw)] == raw and got is not None and got[1] == want,
              f"file 0x{foff:05X} (runtime 0x{rt:04X}) is `{raw.hex(' ')}` targeting "
              f"0x{want:04X} in the site walk "
              f"(got `{d[foff:foff + len(raw)].hex(' ')}` -> "
              f"{'no site' if got is None else f'0x{got[1]:04X}'})")

    # The off-by-one pinned by a case that would fail, not only by ones that
    # pass: taking a 3-byte form's displacement from d[i + 1] reads its bit or
    # operand byte, and for these two that lands somewhere else entirely.
    wrong = [(foff, want, relative_target(raw[0], raw[1], rt))
             for foff, rt, raw, want in REL_SITES if len(raw) == 3]
    check(all(got != want for _, want, got in wrong),
          "reading a 3-byte form's displacement from the second byte instead of the "
          "last misses: " + ", ".join(f"0x{f:05X} -> 0x{got:04X}, not 0x{want:04X}"
                                      for f, want, got in wrong))

    rel_escaped, rel_total, far = [], 0, []
    for name in AUDITED:
        lo, hi = region_bounds(name)
        for off, _, target in relative_sites(d, lo, hi):
            rel_total += 1
            toff = offset_for_runtime(target, name)
            if toff is None or not lo <= toff < hi:
                rel_escaped.append(off)
                if edge_distance(off, lo, hi) > REL_REACH:
                    far.append(f"0x{off:05X}")
    check(not far,
          f"{len(rel_escaped)} of {rel_total} relative site(s) resolve outside the "
          f"caller's own region, every one of them within {REL_REACH} bytes of a "
          f"region edge as the rel8 range requires"
          f"{'' if not far else ' -- not at ' + ', '.join(far[:8])}")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per call site on stdout instead of the tables")
    ap.add_argument("--paged-csv", action="store_true",
                    help="write one row per ajmp/acall site on stdout instead of the tables")
    ap.add_argument("--relative-csv", action="store_true",
                    help="write one row per PC-relative branch site on stdout "
                         "instead of the tables")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the stub sites, the offset_for_runtime round-trip, "
                         "the paged page arithmetic and the rel8 displacement "
                         "arithmetic")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)

    if args.paged_csv:
        write_paged_csv(paged_survey(d)[0])
        return 0

    if args.relative_csv:
        write_relative_csv(relative_survey(d)[0])
        return 0

    rows, stubs, tramp = survey(d)
    if args.csv:
        write_csv(rows)
        return 0

    print_buckets(rows)
    print_trampolines(rows, stubs, tramp)
    print_bucket_b(rows)
    print_bucket_c(d, rows, tramp)
    print_paged(paged_survey(d)[0])
    print_relative(relative_survey(d)[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
