#!/usr/bin/env python3
"""Give every BL51 bank-switch trampoline in the common-area block a decoded,
labelled target, read in the bank its own tail-jump stub selects.

`bank-call-audit.md` section 3 counts the block -- `0x1150` to `0x1ABC`, one
`MOV DPTR,#imm16` and a tail `ljmp`/`lcall` per entry -- and decodes none of
the immediates, because the immediate is not a branch operand and no census in
the tree matched one. Two have been read by hand, both off the reset vector
(`docs/findings/reset-vector-dptr-targets.md`, issue #559), and that write-up
says in as many words that one real routine and one bare `ret` license nothing
for the rest. This is the rest.

**The order is the method, and it is not a convenience.** Each row is read in
three steps in this order: the tail operand names the stub, the stub names the
bank, and only then is the target's first byte read *in that bank*. Read the
other way round there is no answer at all for this population -- every entry is
common-area code, below `0x8000`, where a bank program and the common program
are the same bytes, so "the bank the entry sits in" has no well-defined reading
(issue #465's write-up, `forwarder-target-bank-census.md`). What names the bank
is the stub, and it is in the same six bytes. `ghidra-functions.csv`'s
`bank1,19A8` row is why this is a refusal rather than a preference: a family
counted against bank-1 listings when the stub selects bank 0 had to be
withdrawn, and the replacement row says so in the same comment.

**Three classes and no fourth**, `bank-call-audit.md` section 4's own vocabulary
and no new one, measured in the selected bank:
`entry` if the byte is one of `find_banks.START_OPCODES`, `erased` if it sits
inside a run of at least `audit_call_targets.MIN_ERASED_RUN` `0xFF` bytes,
`other` otherwise. `entry` is a **scoring heuristic, not a decode** --
section 4 says so and this tool does not improve on it. A byte is not a body
either: a row whose `target_byte` is `0x22` says the first byte is `ret`, and
nothing more.

**And a fourth column that is a different question.** `listing` is whether a
committed export covers the target address *in the selected bank*, from
`ec/decompiled/listing-index.csv`. It is not a class and not a verdict; an
empty cell means **not covered by a committed listing**, which is the
`registers.yaml` caveat and section 4's: not found by this method, never
"absent". The column is here because it is the one that makes the table
actionable -- it is the join between an immediate nobody had decoded and the
export that already covers a part of the family, and the empty cells are the
seeds a pinned-toolchain run would land.

**What this is not.** Nothing here is a behavioural claim. No hardware, no
Windows, no live read, no Ghidra run: every input is a committed file and the
one image. Which bank an address resolves in says where the linker meant the
bytes to be read, not what the EC does there, and no `status:` in
`ec/annotations/registers.yaml` moves on any of it.

**How it sits beside `census_forwarder_targets.py`.** That tool closed #465 and
censuses the same 403 entries against the same stub map, so this is not a
second count of a new population: its table is `entry`/`operand`/`no-listing`
read off the committed `.asm` files, and this one is `entry`/`erased`/`other`
read off the image, with listing coverage carried beside it. The two overlap
exactly and the overlap is stated rather than implied -- see the write-up,
`docs/findings/trampoline-target-census.md`, and `census_forwarder_targets.py`
for its side.

This tool is **not** in `.github/scripts/agent-gates.sh` and cannot be from an
agent branch; `bash tools/run-tests.sh ec/tools` runs its suite.

Usage:
    python3 ec/tools/trampoline_target_census.py
    python3 ec/tools/trampoline_target_census.py --csv
    python3 ec/tools/trampoline_target_census.py --check
    python3 ec/tools/trampoline_target_census.py --write
    python3 ec/tools/trampoline_target_census.py --self-test
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from audit_call_targets import (MIN_ERASED_RUN, TRAMP_STRIDE, bank_switch_stubs,
                                byte_class, earlier_record, erased_runs,
                                region_bounds, trampolines)
from bucket_c_codemap import decode_bank
from disasm8051 import converges_from
from find_banks import find_stubs
from trace_xdata_refs import PD_MARKER, REGIONS, runtime_addr

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

DEFAULT_FIRMWARE = "ec/firmware/GMxMGxx_11.800"
DEFAULT_CSV = "ec/annotations/trampoline-target-census.csv"
DEFAULT_INDEX = "ec/decompiled/listing-index.csv"

# `0x22` is `ret`, and a lone one is a real one-instruction routine: the tree
# holds named precedents (`bank0,0xD9DB` `ret_stub`, `bank0,0xD2BE`
# `ret_only_d2be`) and issue #559's `0xD89F` is a third. So a byte test is no
# more decisive for `0x22` than `0xFF` is under section 4's rule, and for the
# same reason -- one `ret` is code, a run of them is not distinguishable from
# the bytes around it by anything in the image. What decides it is the run, and
# the run test that needs no threshold at all is the byte immediately below the
# target: a target whose predecessor is also `ret` is not the first byte of a
# run. Nothing here is a class and nothing here is a verdict -- `target_class`
# stays section 4's own three -- this is a reported shape, not a column.
RET = 0x22

# The block's extent, as the two addresses `audit_call_targets.py --self-test`
# already measures a stride over. Written here because this census is
# *range-restricted* to it -- `trampolines()` keys on the six-byte shape and
# would return an entry anywhere in the common area, and a table of "every
# trampoline" that silently meant "the ones inside these two addresses" is a
# scope claim its own column cannot check.
BLOCK_LO = 0x1150
BLOCK_HI = 0x1ABC

# Every entry's six bytes, spelled out so `--self-test` can assert the framing
# rather than assume it: a 3-byte `mov dptr,#imm16` and a 3-byte tail whose
# operand is one of the two stubs the image has callers for. The tail's *form*
# is left to the row's `opcode` cell -- `trampolines()` accepts `lcall` as well
# as `ljmp` and this tool reports whichever the byte is, so a block that ever
# grew an `lcall` entry would say so in the table rather than be refused here.
MOV_DPTR = 0x90
TAIL_OPCODES = (0x02, 0x12)

# Classes, as a closed set. `byte_class()` returns one of these three today; the
# tuple is what makes a fourth a change to this file rather than a silent new
# value in a committed CSV, which is the same reason `bucket_c_codemap.py`
# refuses a fourth `walk_verdict`.
CLASSES = ("entry", "erased", "other")

# `bank-call-targets.csv`'s thirteen columns in its own order, then this tool's
# five. The census shape is kept rather than abbreviated so the two tables read
# as one family and a reader can diff the headers; three of the thirteen have no
# answer for a trampoline row and say so in the write-up.
CSV_HEAD = ["file_offset", "region", "runtime", "opcode", "target", "bucket",
            "frame_onto", "frame_over", "earlier_record", "calls_stub",
            "calls_trampoline", "own_bank", "other_bank",
            "selects_bank", "stub", "target_class", "target_byte", "listing"]

# `bank-call-audit.md` section 4's rule, at the length that decides it, named so
# the boundary is one fixture on both sides rather than two literals written
# twice: a single 0xFF is `mov r7,a`, one of the commonest bytes in Keil C51
# output, so the test is on a run and not on a byte. `RUN_LENGTH_EDGE` bytes
# must read `other` and one more must read `erased`.
RUN_LENGTH_EDGE = 15

# The `REGIONS` names, held as a set so `bank_region()` can ask membership
# rather than build a dict per call. Computed once and never edited: a fourth
# mapped bank has to arrive through `trace_xdata_refs.REGIONS`, which is the
# statement of what is mapped.
MAPPED_REGIONS = frozenset(name for name, _, _, _, _ in REGIONS)

# How many instructions of an uncovered target the report decodes. A short
# prefix is a reading of the bytes and nothing more, which is what the report
# says beside it, and the number is a rendering choice: it changes no class and
# no cell of the committed table.
SEED_INSNS = 6

# The runtime window every bank maps to 0x8000-0xFFFF at, and the one address
# past its end. `trace_xdata_refs.REGIONS` is where both are *stated*; these are
# named so the refusals below read as claims about a window rather than as
# addresses typed three times.
BANK_WINDOW_LO = 0x8000
BANK_WINDOW_HI = 0x10000

# One of the two addresses `docs/findings/reset-vector-dptr-targets.md` read by
# hand, used here so `--self-test` asks the census's own byte-class function
# about an address another write-up already has an answer for. `0xD96C` opens
# `mov DPTR,#0x0100`, which is a `START_OPCODES` byte, so `entry` is the class
# and section 4's heuristic is what says so.
#
# Module-level for the same reason `COVERAGE_SPANS` is: `check_doc_figure_pins.py`
# reads every int constant inside an asserting call as a pin for a figure in
# some document.
RESET_VECTOR_TARGET = 0xD96C

# `covering_listings()`'s fixture, in the shape `listing_spans()` returns:
# (program, also_in, lo, hi, out_file). Two banks export the same span, a
# `common`-scoped row says which bank it is also in, and a fourth span sits
# clear of the first so a miss cannot be masked by a hit.
#
# Module-level rather than written into the `check()` calls that use it, for the
# reason `audit_call_targets.py` gives for its own fixtures:
# `check_doc_figure_pins.py` reads every int constant inside an asserting call
# across `ec/tools/*.py` as a pin for a figure in some document, so a bare
# address written into a `check()` here would make this module a second,
# uncited pin. A constant is invisible to that search.
COVERAGE_SPANS = [
    ("bank0", "", 0x8000, 0x8100, "bank0/8000.asm"),
    ("bank1", "", 0x8000, 0x8100, "bank1/8000.asm"),
    ("common", "bank1", 0x8000, 0x8100, "common/8000.asm"),
    ("bank0", "", 0x9000, 0x9010, "bank0/9000.asm"),
]


# --- the block --------------------------------------------------------------

def bank_region(bank: int) -> str:
    """`bank0`/`bank1` for the stub-selected bank number.

    Derived from `REGIONS`'s own names rather than written as a dict, so a
    fourth mapped bank has to appear here rather than fall off the end. The
    refusal is the point: `REGIONS` maps two banks in this image, `find_stubs()`
    finds four stubs, and a stub selecting bank 2 or 3 is a real finding that
    this census cannot resolve -- there is no window to read its target in.
    Saying so beats reading the neighbouring region's bytes.
    """
    name = "bank%d" % bank
    if name not in MAPPED_REGIONS:
        raise SystemExit(f"error: a stub selects bank {bank} and this image's "
                         f"region table maps no `{name}`, so there is no window "
                         "to read a target byte in")
    return name


def region_of(offset: int) -> str:
    """The `REGIONS` name whose span holds `offset`.

    Read rather than written as `"common"` so the `region` column is a fact
    about where the entry sits, which is the thing a reader checking the table
    against the region table would look up. An offset no span holds is refused
    rather than answered with the nearest one: an unowned entry is a framing
    question, and guessing would put the block's scope in a column nothing can
    check afterwards.
    """
    for name, lo, hi, _, _ in REGIONS:
        if lo <= offset < hi:
            return name
    raise SystemExit(f"error: file offset 0x{offset:05X} is in no mapped region, "
                     "so this census cannot say where the entry is read")


def block_entries(d: bytes, stubs=None):
    """[(entry, bank, target)] for every trampoline inside the block, in
    address order.

    `audit_call_targets.trampolines()` is *run*, not reimplemented: the block's
    framing and its 403-entry count are what `bank-call-audit.md` section 3 and
    `bank-call-audit.md --self-test` publish, and a second enumeration in this
    file would be a second answer to their question. The only thing added here
    is the range restriction, which is the census's own scope.
    """
    tramp = trampolines(d, bank_switch_stubs(d) if stubs is None else stubs)
    return [(entry, bank, target)
            for entry, (bank, target) in sorted(tramp.items())
            if BLOCK_LO <= entry <= BLOCK_HI]


def tail_stub(d: bytes, entry: int, stubs) -> int:
    """The stub address the entry's tail instruction names.

    Read back out of the six bytes rather than taken from the `trampolines()`
    row that already found the entry. It is the same two bytes, and reading
    them here is what makes `selects_bank` a fact about the image rather than a
    field copied from the scan that found the entry -- which is the whole claim
    this tool makes, so it is worth the two bytes.
    """
    op = d[entry + 3]
    if op not in TAIL_OPCODES:
        raise SystemExit(f"error: the entry at 0x{entry:04X} has "
                         f"0x{op:02X} where the tail instruction belongs, so it "
                         "is not a trampoline entry")
    return (d[entry + 4] << 8) | d[entry + 5]


def target_file_offset(bank: int, target: int):
    """File offset the target's first byte is read at in `bank`, or None.

    `region_bounds(bank_region(bank))[0]` is the bank's own file offset and
    every bank maps runtime `0x8000` there, so the two subtractions cancel to
    the shape the region table already asserts -- the same arithmetic
    `bucket_c_codemap.decode_bank()` writes out, and the same one
    `trace_xdata_refs.REGIONS` is the statement of.

    **None is a refusal and not an edge case to widen.** An address outside the
    selected bank's mapped window has no byte to read there, and the only other
    thing at that offset is the *other* bank's bytes or erased flash -- reading
    either and calling it the target's class is the `bank1,19A8` failure with
    the mechanism spelled out. Every target in this image is inside the window,
    so this never fires on a committed row, which is why `--self-test` and the
    suite both ask the function directly: a guard that only ever runs against
    conforming input is not a guard.
    """
    lo, hi = region_bounds(bank_region(bank))
    off = lo + (target - 0x8000)
    return off if lo <= off < hi else None


# --- listing coverage -------------------------------------------------------

def listing_spans(path: str = None):
    """[(program, also_in, lo, hi, out_file)] from `listing-index.csv`.

    `also_in` is honoured because it is how a *common*-scoped row says "the
    same bytes were exported in bank 1 as well" -- `build_ec_decompile.py`
    de-duplicates a function present in both banks into one `common` row and
    records the second program there. Asking for a common row without reading
    it would under-report coverage in exactly the family that is meant to be
    shared, and asking for one without the *bank* test would let a bank-0
    listing vouch for a bank-1 target, which is the mistake the whole method is
    built against. On this population the clause never decides: every `common`
    row is below `0x8000` and every target is at or above it. It is carried
    because it is what makes the lookup bank-specific rather than a grep.

    **A row whose span does not parse is refused, not skipped.** Skipping it
    would make an unreadable index read as a sparser one, and this column's
    whole job is to say what the export covers -- a row dropped here is a row
    that silently stops covering anything.
    """
    path = path or os.path.join(HERE, os.pardir, os.pardir,
                                *DEFAULT_INDEX.split("/"))
    out = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh, strict=True):
            try:
                addr = int(row["addr"], 16)
                size = int(row["size"])
            except (KeyError, TypeError, ValueError) as exc:
                raise SystemExit(
                    f"error: listing-index.csv row for {row.get('program')!r} "
                    f"{row.get('addr')!r} size {row.get('size')!r} does not "
                    f"parse as an address and a size ({exc}); a row dropped "
                    "here is a row that stops covering anything")
            out.append((row["program"].strip(), (row.get("also_in") or "").strip(),
                        addr, addr + size, row["out_file"].strip()))
    return out


def covering_listings(spans, bank: int, target: int):
    """[out_file] for every committed listing of `bank` whose span holds
    `target`, sorted and deduped."""
    program = bank_region(bank)
    return sorted({out for prog, also, lo, hi, out in spans
                   if lo <= target < hi
                   and (prog == program or (prog == "common"
                                            and program in also.split(";")))})


# --- the census -------------------------------------------------------------

def census(d: bytes, spans=None):
    """One dict per block entry, in address order.

    `spans` is taken rather than read so a caller can ask the coverage question
    against a fixture, and so the report and the CSV cannot disagree: there is
    one pass and every column is read off its row.

    The order of the three reads is the docstring's order and the row's own
    construction order: entry -> stub -> bank -> byte. `selects_bank` is settled
    from the stub before `target_class` is computed, and a target with no byte
    in the selected bank is refused by `target_file_offset()` rather than read
    somewhere else.
    """
    stubs = bank_switch_stubs(d)
    entries = block_entries(d, stubs)
    runs = {bank: erased_runs(d, *region_bounds(bank_region(bank)))
            for bank in sorted({bank for _, bank, _ in entries})}
    if spans is None:
        spans = listing_spans()
    rows = []
    for entry, bank, target in entries:
        stub = tail_stub(d, entry, stubs)
        off = target_file_offset(bank, target)
        if off is None:
            raise SystemExit(
                f"error: 0x{entry:04X} loads DPTR with 0x{target:04X}, which is "
                f"outside the window the bank-{bank} stub maps; there is no "
                "byte to read there in that bank, and reading one from the "
                "other bank would be the withdrawn bank1,19A8 count again")
        region = region_of(entry)
        onto, over = converges_from(d, entry)
        rows.append({
            "file_offset": entry,
            "region": region,
            "runtime": runtime_addr(entry, True),
            "opcode": "ljmp" if d[entry + 3] == 0x02 else "lcall",
            "target": target,
            "bucket": "",
            "frame_onto": onto,
            "frame_over": over,
            "earlier_record": earlier_record(d, entry, region_bounds(region)[0]),
            "calls_stub": bank,
            "calls_trampoline": "",
            "own_bank": "",
            "other_bank": "",
            "selects_bank": bank,
            "stub": stub,
            "target_class": byte_class(d, off, runs[bank]),
            "target_byte": d[off],
            "target_file_offset": off,
            "listing": covering_listings(spans, bank, target),
        })
    return rows


def csv_text(d: bytes, index_path: str = None) -> str:
    """The whole census as CSV text, from the image.

    Written to a string rather than to a file so `--check` can diff it against
    the committed copy and `--csv` can hand it to stdout: this tool writes
    exactly one committed file, under `--write`, and nothing else does.
    """
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEAD)
    for r in csv_rows(census(d, listing_spans(index_path))):
        w.writerow(r)
    return buf.getvalue()


def csv_rows(rows):
    """[list of str] -- the committed spelling of one census row each."""
    return [[f"0x{r['file_offset']:05X}", r["region"], f"0x{r['runtime']:04X}",
             r["opcode"], f"0x{r['target']:04X}", r["bucket"],
             r["frame_onto"], r["frame_over"], r["earlier_record"],
             r["calls_stub"], r["calls_trampoline"],
             r["own_bank"], r["other_bank"],
             r["selects_bank"], f"0x{r['stub']:04X}", r["target_class"],
             f"0x{r['target_byte']:02X}", "; ".join(r["listing"])]
            for r in rows]


def fill_runs(d: bytes, lo: int, hi: int, value: int):
    """[(start, stop)] **inclusive** runs of `value` in `[lo, hi)`, any length.

    Inclusive at both ends rather than the half-open `[start, stop)`
    `audit_call_targets.erased_runs()` returns, because a run of bytes is
    something a reader wants to name as an address range and `0xBF54`-`0xBFDD`
    says it better than `0xBF54`-`0xBFDE`. The one-byte floor is deliberate:
    a single `ret` is a routine, so a run this returns is not by itself a claim
    about any of its bytes.
    """
    out = []
    start = None
    for i in range(lo, hi + 1):
        if i < hi and d[i] == value:
            if start is None:
                start = i
        elif start is not None:
            out.append((start, i - 1))
            start = None
    return out


def ret_shape(d: bytes, rows):
    """(sel, inner, runs) for the `ret` shape.

    `sel` is every row whose target byte is `ret`; `inner` is the subset of it
    with a `ret` immediately below the target; `runs` is
    `[((bank, lo, hi), [rows in it])]` longest-first, the file-offset extent of
    each run and the targets that fall inside it.

    The second number is the one the write-up leads with and it needs no
    threshold: a target whose immediate predecessor in the selected bank is
    also `ret` is not the first byte of a run, so whatever routine it names
    begins one byte into a run of identical bytes. That is a statement about the
    bytes and nothing more -- a `lcall` into the middle of a run is possible,
    so this does not say the target is unreachable, and nothing here says a
    trampoline naming it is never called.
    """
    sel = [r for r in rows if r["target_byte"] == RET]
    inner = [r for r in sel
             if r["target_file_offset"] > region_bounds(
                 bank_region(r["selects_bank"]))[0]
             and d[r["target_file_offset"] - 1] == RET]
    every = {bank: fill_runs(d, *region_bounds(bank_region(bank)), RET)
             for bank in {r["selects_bank"] for r in sel}}
    runs = collections.defaultdict(list)
    for r in sel:
        a, z = next((a, z) for a, z in every[r["selects_bank"]]
                    if a <= r["target_file_offset"] <= z)
        runs[(r["selects_bank"], a, z)].append(r)
    return sel, inner, sorted(runs.items(), key=lambda kv: -(kv[0][2] - kv[0][1]))


# --- reporting --------------------------------------------------------------

def report(d: bytes, rows) -> None:
    """The plain run: the block, the classes, the coverage, and the one address
    the two banks answer differently about."""
    stubs = find_stubs(d)
    by_stub = collections.Counter(r["stub"] for r in rows)
    print("## 1. The block, and the stub each entry routes through")
    print()
    print(f"  0x{BLOCK_LO:04X}-0x{BLOCK_HI:04X}, {len(rows)} entries at stride "
          f"{TRAMP_STRIDE}, every tail operand one of the {len(by_stub)} stubs "
          "below.")
    for stub, bank in sorted(stubs):
        if by_stub[stub]:
            print(f"  stub 0x{stub:04X} selects bank {bank}: {by_stub[stub]} "
                  "entries route through it")
    print()
    print("`selects_bank` is read off the entry's own tail operand before the")
    print("target byte is read, and every entry is common-area code, so there is")
    print("no bank an entry could be read in instead.")
    print()

    print("## 2. What the target byte reads, in the selected bank")
    print()
    print("`entry` is `find_banks.START_OPCODES`, a scoring heuristic and not a")
    print(f"decode; `erased` is a run of at least {MIN_ERASED_RUN} 0xFF bytes;")
    print("`other` is neither. No class is a statement about a body: a row whose")
    print("byte is `22` says the first byte is `ret` and nothing more.")
    print()
    print("| stub | selects | entries | " + " | ".join(CLASSES) + " |")
    print("|---|---|---:|" + "---:|" * len(CLASSES))
    for stub, bank in sorted(stubs):
        sel = [r for r in rows if r["stub"] == stub]
        if not sel:
            continue
        cells = " | ".join(str(sum(1 for r in sel if r["target_class"] == c))
                           for c in CLASSES)
        print(f"| `0x{stub:04X}` | bank {bank} | {len(sel)} | {cells} |")
    print()

    lone_ff = sum(1 for r in rows if r["target_byte"] == 0xFF)
    print(f"  No row's target byte is `0xFF` ({lone_ff} of {len(rows)} rows have "
          "one), so section")
    print(f"  4's {MIN_ERASED_RUN}-byte run rule and a one-byte test would answer "
          "this table")
    print("  identically. The rule is carried because it is the right test, and "
          "this line")
    print("  says it is not what made the `erased` column.")
    print()

    print("## 3. Whether a committed listing covers the target, in that bank")
    print()
    print("An empty `listing` cell is **not covered by a committed listing** --")
    print("not found by this method, never absent. `census_forwarder_targets.py`")
    print("censused the same entries against the committed `.asm` files and")
    print("reached the same split; that is a second derivation, not a second")
    print("population.")
    print()
    print("| stub | selects | covered | not covered |")
    print("|---|---|---:|---:|")
    for stub, bank in sorted(stubs):
        sel = [r for r in rows if r["stub"] == stub]
        if not sel:
            continue
        print(f"| `0x{stub:04X}` | bank {bank} | {sum(1 for r in sel if r['listing'])} "
              f"| {sum(1 for r in sel if not r['listing'])} |")
    print()

    covered = [r for r in rows if r["listing"]]
    print("## 4. The address the two banks answer differently about")
    print()
    both = collections.defaultdict(dict)
    for r in rows:
        both[r["target"]][r["selects_bank"]] = r
    split = [t for t, sel in sorted(both.items()) if len(sel) == 2]
    if not split:
        print("  none in this image: no target is named by an entry in each bank")
    for t in split:
        print(f"  0x{t:04X} is named from both directions, and nothing in the")
        print("  bytes says which of the two runs:")
        for bank in sorted(both[t]):
            r = both[t][bank]
            print(f"    {r['opcode']} from `0x{r['file_offset']:04X}` through "
                  f"`0x{r['stub']:04X}`, bank {bank}: byte "
                  f"{r['target_byte']:02X}, `{r['target_class']}`"
                  + (f", covered by {', '.join(r['listing'])}" if r["listing"]
                     else ", no committed listing"))
        print("  The stub is what picks, and reading either bank for both rows is")
        print("  the withdrawn `bank1,19A8` count.")
    print()

    print("## 5. The seeds this names, and the targets nothing covers")
    print()
    uncovered = [r for r in rows if not r["listing"]]
    print(f"""  {len(covered)} of the {len(rows)} targets fall inside a committed listing
  of the bank their own stub selects; {len(uncovered)} fall inside none. Each of
  those is a seed a Ghidra run could land, and landing them is a `--report` run
  on the pinned assembler (`ec/ghidra/README.md`), not an inference from their
  absence. The rows carry their addresses.""")
    print()
    print("What a few of the uncovered bytes read as, in the bank their stub")
    print("selects -- the first of each class in address order, because a prefix")
    print("is a reading of the bytes and nothing more:")
    print()
    sample = []
    for cls in CLASSES:
        sample += [r for r in uncovered if r["target_class"] == cls][:3]
    for r in sample:
        base = region_bounds(bank_region(r["selects_bank"]))[0]
        print(f"  0x{r['file_offset']:04X} -> 0x{r['target']:04X} (bank "
              f"{r['selects_bank']}, `{r['target_class']}`): "
              + decode_bank(d, r["target"], base, SEED_INSNS))
    if len(uncovered) > len(sample):
        print(f"  ... and {len(uncovered) - len(sample)} more, every one of them "
              "a row in ec/annotations/trampoline-target-census.csv")
    print()

    rets, inner, runs = ret_shape(d, rows)
    print("## 6. The targets whose first byte is `ret`, and the runs they sit in")
    print()
    print(f"""  {len(rets)} of the {len(rows)} targets begin with `0x22`, and {len(inner)}
  of those have a `ret` immediately below them -- so they are not the first byte
  of a run, and whatever routine one names begins one byte into a run of
  identical bytes. That is a statement about the bytes and nothing more: an
  `lcall` into the middle of a run is possible, so this does not say the target
  is unreachable, and nothing here says a trampoline naming it is never called.
  `entry`/`erased`/`other` are section 4's three classes and none of them moved
  for any of this.

  Those {len(rets)} targets fall in {len(runs)} run(s) of `ret` bytes, in the
  bank their stub selects:""")
    print()
    print("| bank | run | bytes | targets |")
    print("|---|---|---:|---:|")
    for (bank, a, z), holders in runs:
        base = region_bounds(bank_region(bank))[0]
        print(f"| bank {bank} | `0x{0x8000 + a - base:04X}`-`0x{0x8000 + z - base:04X}` "
              f"| {z - a + 1} | {len(holders)} |")
    print()


# --- self-test --------------------------------------------------------------

def self_test(d: bytes) -> int:
    """The refusals and the re-derivations, on scratch bytes and on the image.

    Every figure here is recomputed from the image or built on the spot. None
    is a literal, so a firmware dump that moved one would redden this for a
    reason the message names rather than pass on a stale pair.
    """
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    print("trampoline_target_census.py --self-test")
    print()

    # 1. The block's framing, from the bytes rather than from the scan's own
    #    key. `trampolines()` returning an entry says there is a
    #    `90 hi lo 02/12 11 xx` shape there; it does not say the six bytes are
    #    contiguous, and the contiguity is what makes "stride 6 over this span"
    #    a statement about the block rather than about a set.
    entries = block_entries(d)
    check(all(d[e] == MOV_DPTR for e, _, _ in entries),
          f"every one of the {len(entries)} entries opens with `mov dptr,#imm16`")
    check(all(d[e + 3] in TAIL_OPCODES for e, _, _ in entries),
          "and every one carries a 3-byte tail instruction")
    strides = sorted({b - a for a, b in zip([e for e, _, _ in entries],
                                            [e for e, _, _ in entries][1:])})
    check(strides == [TRAMP_STRIDE],
          f"the entries are one unbroken {TRAMP_STRIDE}-byte stride over "
          f"0x{entries[0][0]:04X}-0x{entries[-1][0] + TRAMP_STRIDE:04X}"
          f"{'' if strides == [TRAMP_STRIDE] else ' -- strides ' + str(strides)}")
    covered_span = (entries[-1][0] + TRAMP_STRIDE - entries[0][0]) // TRAMP_STRIDE
    check(covered_span == len(entries),
          f"the span holds exactly as many stride-{TRAMP_STRIDE} slots "
          f"({covered_span}) as there are entries ({len(entries)}), so no entry "
          "is skipped inside it")
    check(all(BLOCK_LO <= e <= BLOCK_HI for e, _, _ in entries),
          f"and every one is inside the block this census is scoped to "
          f"(0x{BLOCK_LO:04X}-0x{BLOCK_HI:04X})")

    # 2. The stub split, re-derived from find_stubs() by hand rather than read
    #    off the scan's dict -- so a `trampolines()` that lost its bank would
    #    not be able to grade itself here.
    stubs = {addr: bank for addr, bank in find_stubs(d)}
    by_hand = collections.Counter()
    for e, _, _ in entries:
        by_hand[tail_stub(d, e, stubs)] += 1
    check(sum(by_hand.values()) == len(entries),
          f"every entry's tail operand names a stub `find_stubs()` found "
          f"({sum(by_hand.values())} of {len(entries)})")
    # The sweep is printed over every stub rather than over the routed ones, so
    # a zero is visible as a zero. That is what distinguishes "no entry routes
    # through this stub" from "the scan never looked at it", and
    # `bank-call-audit.md` 3 rests on the second reading being the first.
    print("        by stub: "
          + ", ".join(f"0x{a:04X}->bank{b}: {by_hand[a]}"
                      for a, b in sorted(stubs.items())))
    check(set(by_hand) <= set(stubs),
          "no entry names a stub outside the set `find_stubs()` found")
    # The refusal the block does not exercise, checked on a direct call.
    # `find_stubs()` finds four stubs and `REGIONS` maps two banks, so a stub
    # selecting bank 2 or 3 has no window to read a target in -- and no entry in
    # this image routes through one, which is exactly why it has to be asked
    # rather than found on a row.
    try:
        bank_region(max(stubs.values()))
        check(False, f"a bank `REGIONS` does not map is refused, and bank "
                     f"{max(stubs.values())} is one")
    except SystemExit as exc:
        check("maps no" in str(exc),
              f"a bank `REGIONS` does not map is refused rather than read from a "
              f"neighbouring region: {exc}")

    # 3. The read is in the selected bank. A target the two banks disagree
    #    about is the only shape where the ordering is observable, so the image
    #    is asked whether it holds one and the answer is used either way.
    stubs_map = bank_switch_stubs(d)
    rows = census(d)
    both = collections.defaultdict(dict)
    for r in rows:
        both[r["target"]][r["selects_bank"]] = r
    shared = {t: sel for t, sel in both.items() if len(sel) == 2}
    check(len(shared) <= 1,
          f"targets named from both directions in this image: {len(shared)} -- "
          "the census gives each its own bank's answer and never merges them")
    for t, sel in sorted(shared.items()):
        classes = {sel[b]["target_class"] for b in sel}
        check(len(classes) > 1,
              f"and 0x{t:04X} reads differently in the two banks -- "
              + "; ".join(f"bank{b}: byte {sel[b]['target_byte']:02X}, "
                          f"`{sel[b]['target_class']}`" for b in sorted(sel))
              + " -- so a run that read one bank for both is caught here")

    # 4. The refusal: a target outside the selected bank's window has no byte
    #    there, and the only other thing at that offset is another bank's.
    check(target_file_offset(0, BANK_WINDOW_LO) is not None
          and target_file_offset(0, 0xFFFF) is not None,
          "the first and last addresses of a bank's window both resolve")
    check(target_file_offset(0, BANK_WINDOW_LO - 1) is None,
          "an address below the banked window has no byte in that bank")
    check(target_file_offset(1, BANK_WINDOW_HI) is None,
          "and one above it, in either bank, is refused rather than read from "
          "the neighbouring region")
    check(all(r["target_file_offset"] == region_bounds(
                  bank_region(r["selects_bank"]))[0]
              + r["target"] - BANK_WINDOW_LO
              for r in rows),
          "every row's target was read at its own stub-selected bank's offset "
          "and no other")

    # 5. Section 4's 16-byte rule, on scratch bytes. The fixture is built here
    #    rather than found in the image: these are about the rule, and a fixture
    #    anchored at an address in the committed dump keeps testing only what it
    #    was written to test until those bytes change.
    lo, hi = region_bounds("bank0")
    for runlen, want in ((RUN_LENGTH_EDGE, "other"), (RUN_LENGTH_EDGE + 1, "erased")):
        buf = bytearray(d)
        buf[lo:lo + runlen] = b"\xFF" * runlen
        buf[lo + runlen] = 0x22   # ordinary code on the far side of the run
        runs = erased_runs(bytes(buf), lo, hi)
        check(byte_class(bytes(buf), lo, runs) == want,
              f"a run of {runlen} 0xFF bytes reads `{want}`, so the "
              f"{MIN_ERASED_RUN}-byte rule and not a one-byte test decides it")
    lone = bytearray(d)
    lone[lo] = 0xFF
    check(byte_class(bytes(lone), lo, erased_runs(bytes(lone), lo, hi)) != "erased",
          "and a lone 0xFF is not erased either, which is the case "
          "`0xFF` = `mov r7,a` makes")

    # 6. `entry` is the scoring heuristic section 4 names, used as one.
    check(byte_class(d, target_file_offset(0, RESET_VECTOR_TARGET),
                     erased_runs(d, *region_bounds("bank0"))) == "entry",
          "the byte-class the census reads is the one section 4's own vocabulary "
          "gives, from the imported function rather than a local copy")

    # 7. The census's own scope, re-derived: one row per entry, no row outside
    #    the block, and each row's bank equal to the stub's own.
    check(len(rows) == len(entries),
          f"one row per block entry ({len(rows)} rows, {len(entries)} entries)")
    check(all(r["selects_bank"] == stubs_map[r["stub"]] for r in rows),
          "and every row's `selects_bank` is the bank its own stub selects")
    check(all(r["stub"] == tail_stub(d, r["file_offset"], stubs_map) for r in rows),
          "with `stub` read back out of the entry's tail operand")
    check(all(r["target_class"] in CLASSES for r in rows),
          f"every row's class is one of the {len(CLASSES)} "
          f"({', '.join(CLASSES)})")
    check(all(r["bucket"] == "" and r["own_bank"] == ""
              and r["other_bank"] == "" and r["calls_trampoline"] == ""
              for r in rows),
          "the four census columns with no answer for a trampoline row are empty "
          "rather than reinterpreted")

    # 8. The `ret`-run shape, on scratch bytes for the rule and on the image
    #    for the claim. A one-byte `ret` is a real one-instruction routine, so
    #    the floor is 1 and the fixture says so: a rule with a floor of 2 would
    #    drop the shape `bank0,0xD9DB` `ret_stub` and issue #559's `0xD89F`
    #    both have.
    scratch = bytes([RET, RET, 0x23, RET])
    check(fill_runs(scratch, 0, 4, RET) == [(0, 1), (3, 3)],
          "fill_runs() is inclusive at both ends, keeps a one-byte run, and "
          "splits two runs a non-matching byte holds apart")
    check(fill_runs(bytes([RET] * 5), 0, 5, RET) == [(0, 4)],
          "and a run with nothing interrupting it is one run")
    rets, inner, runs = ret_shape(d, rows)
    check(all(r["target_byte"] == RET for r in rets),
          f"every target the ret shape reports ({len(rets)}) begins with `0x22`")
    check(all(d[r["target_file_offset"] - 1] == RET for r in inner),
          f"and every one of the {len(inner)} it calls interior really has a "
          "`ret` immediately below it")
    check(all(a <= r["target_file_offset"] <= z
              for (_, a, z), holders in runs for r in holders),
          "and every run's extent holds the targets attributed to it")
    check(all(all(d[i] == RET for i in range(a, z + 1))
              for (_, a, z), _ in runs),
          "with every byte of every reported run the same value, which is what "
          "makes the range a run rather than a span")
    accounted = [r for _, holders in runs for r in holders]
    check(len(accounted) == len(rets)
          and {r["file_offset"] for r in accounted} ==
              {r["file_offset"] for r in rets},
          "and the runs partition the targets the shape reported, in both "
          "directions")

    # 9. Coverage is bank-specific. A span that holds the address in the *other*
    #    bank must not vouch for it here; that is the whole of the
    #    `bank1,19A8` failure, expressed as a lookup.
    check(covering_listings(COVERAGE_SPANS, 0, 0x8050) == ["bank0/8000.asm"],
          "a bank-0 address is covered by the bank-0 listing and not by "
          "bank 1's")
    check(covering_listings(COVERAGE_SPANS, 1, 0x8050) == ["bank1/8000.asm",
                                                            "common/8000.asm"],
          "the same address in bank 1 is covered by bank 1's own listing and by "
          "the de-duplicated `common` row whose `also_in` names bank 1")
    check(covering_listings(COVERAGE_SPANS, 0, 0x9000) == ["bank0/9000.asm"],
          "and a bank-0 address outside every other span is covered by the one "
          "that holds it, and nothing else")
    check(covering_listings(COVERAGE_SPANS, 0, 0x9010) == [],
          "while an address one past a span's end is covered by nothing -- the "
          "off-by-one a half-open `[addr, addr+size)` gets wrong")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s)")
        return 1
    print("self-test passed: the refusals hold, the block's framing re-derives "
          "from the bytes, and the stub split is counted from `find_stubs()`")
    return 0


# --- committed table --------------------------------------------------------

def check_csv(d: bytes, path: str) -> int:
    """Diff the regenerated table against the committed one. Exit 1 on a diff.

    A *missing* file fails rather than being created. Writing it would make
    `--check` the thing that decides what the committed table is, which is the
    arrangement `bucket_c_codemap.py`'s own `check_csv()` refuses and this one
    is written beside rather than forked from.
    """
    if not os.path.exists(path):
        print(f"error: {path} does not exist. --check compares; it never "
              "creates. Generate the table with --csv and commit it.",
              file=sys.stderr)
        return 1
    want = open(path).read()
    got = csv_text(d)
    if got == want:
        print(f"{os.path.relpath(path, REPO)}: {got.count(chr(10)) - 1} row(s) "
              "match the committed file, byte for byte")
        return 0
    diff = list(difflib.unified_diff(want.splitlines(True), got.splitlines(True),
                                     fromfile=f"committed {path}",
                                     tofile="regenerated"))
    sys.stdout.writelines(diff)
    print("error: the committed table is not what this run derives from the "
          "image", file=sys.stderr)
    return 1


def write_csv(d: bytes, path: str) -> int:
    """The one file this tool writes, and only under `--write`."""
    with open(path, "w") as f:
        f.write(csv_text(d))
    print(f"wrote {os.path.relpath(path, REPO)}: "
          f"{csv_text(d).count(chr(10)) - 1} row(s)")
    return 0


def resolve(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(REPO, path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help=f"raw EC firmware image (default {DEFAULT_FIRMWARE})")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--csv", action="store_true",
                      help="write one row per block entry on stdout")
    mode.add_argument("--check", action="store_true",
                      help="regenerate the committed table in memory and diff it")
    mode.add_argument("--write", action="store_true",
                      help="write the committed table")
    mode.add_argument("--self-test", action="store_true",
                      help="re-derive the framing and check the refusals")
    ap.add_argument("--csv-path", default=DEFAULT_CSV,
                    help="the committed table (default %(default)s)")
    ap.add_argument("--index", default=None,
                    help=f"{DEFAULT_INDEX}, for the coverage column")
    args = ap.parse_args()

    path = resolve(args.firmware)
    if not os.path.isfile(path):
        ap.error(f"no firmware image at {args.firmware}")
    d = open(path, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)
    if args.check:
        return check_csv(d, resolve(args.csv_path))
    if args.write:
        return write_csv(d, resolve(args.csv_path))
    if args.csv:
        sys.stdout.write(csv_text(d, args.index))
        return 0
    report(d, census(d, listing_spans(args.index)))
    return 0


if __name__ == "__main__":
    sys.exit(main())