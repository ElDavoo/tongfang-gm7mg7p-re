#!/usr/bin/env python3
"""Establish the entry/boundary set of the counter sweep at bank1:0x8001-0x8189.

`ec/decompiled/index.csv` cuts those 393 bytes into 42 exports, and the 42
`ghidra-functions.csv` rows describe them as slices whose boundaries are "the
call-target byte scan's hypothesis". This tool settles that hypothesis by
measurement: it takes the census rows that target into the run, scores each
caller with `disasm8051.converges_from()` -- the repository's own anchoring
method, the one `audit_call_targets.py` already reports the anchored half of
every count from -- and cross-checks each one against the instruction starts
parsed out of the committed `.asm` listings. It introduces no new theory of
framing; the frame score is read next to the listing evidence, because the
score alone proves nothing (`../annotations/bank-call-audit.md` 1, and this
tool's own `--self-test`).

The result on the committed tree: 180 `bank1` census rows target into the run,
70 distinct targets, and **exactly one** site is at an instruction start in a
committed listing -- `bank1:0xABB8` `lcall 0x8001`, 24 of 24, corroborated by
the annotated forwarder at that address. **135 of the other 179 are the rel8
displacement byte of a `cjne`**, which the census's `0x02`/`0x12` byte scan
cannot tell from an `ljmp` opcode; 39 more are the displacement byte of another
PC-relative branch, one is the low target byte of an `ljmp`/`lcall` the listing
already carries, two are an immediate operand of a non-branch, and two sit in a
committed gap between two listings. That is
`../annotations/bank-call-audit.md` 1's "upper bound, not a partition" biting
in one measurable place, and it is why "one confirmed caller" is the whole of
the finding: **the 179 others are not 179 absent calls**, they are 179
byte-scan sites this method did not confirm, in a scan with a named blind spot.

Two things this deliberately does not do. It does not delete the slice rows --
every one of the 42 annotation addresses is also a census seed, so deleting
them removes no seeds at all, and `--mode export-only` cannot un-carve the
functions already in the committed `.rep` (nothing under `ghidra/scripts/`
calls `removeFunction`, `clearListing` or `deleteFunction`). And it does not
claim the rebuild's outcome: the prediction is in
`docs/findings/counter-sweep-entry-set.md`, to be confirmed from `index.csv`
and `manifest.csv` when a machine with the pinned assembler runs one.

**Two ways to read this wrong, both silent.** A `bank1` site's *file offset* is
not its runtime address -- `0x12BB8` is runtime `0xABB8` and the listing is
`ec/decompiled/bank1/ABB8.asm` -- so keying listings by the census's
`file_offset` column finds no file for any of the 180 and reports every one of
them a phantom in a gap. And a listing line's operand text carries its own
four-hex-digit tokens (`jz 0x8009`), so an unanchored regex for an address
matches the branch target as readily as the address column. Both are asserted
in `--self-test` rather than left to the next reader.

Usage:
    python3 counter_sweep_entry.py
    python3 counter_sweep_entry.py --self-test
    python3 counter_sweep_entry.py --csv > counter-sweep-entry.csv
"""
import argparse
import bisect
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC_DIR = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from disasm8051 import (OPCODE_LEN, REL_OPCODES, converges_from)   # noqa: E402
from trace_xdata_refs import (PD_MARKER, offset_for_runtime,       # noqa: E402
                              runtime_addr)

FIRMWARE = os.path.join(EC_DIR, "firmware", "GMxMGxx_11.800")
CENSUS_CSV = os.path.join(EC_DIR, "annotations", "bank-call-targets.csv")
INDEX_CSV = os.path.join(EC_DIR, "decompiled", "index.csv")
ANNOTATIONS_CSV = os.path.join(EC_DIR, "annotations", "ghidra-functions.csv")

# The run, half-open: 0x8001 through the `ret` at 0x8189 inclusive. Written
# with the 0x22 at each end named in the assertion below rather than inferred
# from the number, because "393 bytes ending in a ret" is a claim the tool
# checks, not an assumption it makes.
PROGRAM = "bank1"
RUN = (0x8001, 0x818A)
RET = 0x22

# The one caller the committed listings put at an instruction start. Pinned in
# --self-test together with its frame score; a census or a listing change that
# moves it should fail here rather than quietly change the headline.
ENTRY_SITE_FILE_OFFSET = 0x12BB8
ENTRY_SITE_RUNTIME = 0xABB8
ENTRY_TARGET = 0x8001

# The runner-up, which is here because its target is not an instruction
# boundary -- the check that stops "5 of 24 anchors" from being read as a call.
RUNNER_UP_RUNTIME = 0x9C34
RUNNER_UP_TARGET = 0x801A

# The rows the annotations argue about: three seeds a prior change added, and
# two whose comments make a positive claim about where the body starts. Their
# scores are the answer to that argument.
SLICE_TARGETS = (0x8008, 0x8010, 0x8017, 0x8018, 0x80EF)
SLICE_MAX_FRAME = 1

# An instruction line is `<4 hex addr> <up to 3 byte columns, '-' padded>
# <mnemonic> <operands>`, and only the first column is the address. Anchored at
# the start of the line for the reason in the docstring: the operand text
# carries four-hex-digit branch targets of its own.
LINE_RE = re.compile(
    r"^([0-9A-Fa-f]{4})\s+((?:[0-9a-f]{2}|-)\s+(?:[0-9a-f]{2}|-)\s+"
    r"(?:[0-9a-f]{2}|-))\s+(\S.*)$")
# The same shape, deliberately unanchored, for the self-test that says why the
# anchor is there.
LOOSE_ADDR_RE = re.compile(r"[0-9A-Fa-f]{4}")


def read_listings(program):
    """(starts, {runtime address: (bytes, text)}) for `program`'s committed
    `.asm` files.

    The address in a listing is the *runtime* address, and the file is named for
    it, so the dict is keyed the way the listings are written and a caller with
    a census `file_offset` has to map it in with `runtime_addr()` first. That is
    the trap `--self-test` asserts rather than leaves to a reader."""
    out = {}
    d = os.path.join(EC_DIR, "decompiled", program)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".asm"):
            continue
        with open(os.path.join(d, name)) as f:
            for line in f:
                m = LINE_RE.match(line)
                if not m:
                    continue
                addr = int(m.group(1), 16)
                out[addr] = (tuple(int(b, 16) for b in m.group(2).split()
                                   if b != "-"), m.group(3).rstrip())
    return sorted(out), out


def owner_of(addr, starts, listings):
    """(owner address, byte index) for the instruction covering `addr`, or
    (None, None) when `addr` is in a committed gap between two listings.

    Listings are contiguous-or-nothing: Ghidra exported one function per file
    and a byte no listing covers is a gap, not a misframed instruction. The
    distinction is load-bearing, because a gap is a different kind of "not
    found by this method" from an operand byte -- and both are reported as
    such, never as an absence."""
    lo = bisect.bisect_left(starts, addr)
    if lo < len(starts) and starts[lo] == addr:
        return addr, 0
    if lo == 0:
        return None, None
    owner = starts[lo - 1]
    if lo == len(starts) or owner + len(listings[owner][0]) <= addr:
        return None, None
    return owner, addr - owner


def site_shape(addr, starts, listings):
    """How `addr` reads against the committed listings, as
    (kind, owner, opcode, text, index). `kind` is one of

      start  -- the address is an instruction start in a committed listing
      gap    -- no listing covers it
      operand -- it is the Nth byte of the instruction at `owner`

    The `operand` branch is the whole point of the exercise: a `0x02` byte that
    is a `cjne`'s displacement is not an `ljmp`. `index` is which byte, because
    whether the `0x02` is the instruction's last byte (a displacement) or its
    second (an immediate) is the difference between a branch and a load."""
    owner, idx = owner_of(addr, starts, listings)
    if owner is None:
        return "gap", None, None, None, None
    raw, text = listings[owner]
    if idx == 0:
        return "start", owner, raw[0], text, 0
    return "operand", owner, raw[0], text, idx


def load_census():
    with open(CENSUS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_index():
    with open(INDEX_CSV, newline="") as f:
        return list(csv.DictReader(f))


def load_annotations():
    with open(ANNOTATIONS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def run_rows(index):
    return [r for r in index
            if r["program"] == PROGRAM
            and RUN[0] <= int(r["addr"], 16) < RUN[1]]


def target_rows(census):
    """Census rows whose target lands in the run, from `bank1` only.

    The region filter is not a shortcut. A `bank0` site and a `common` site
    target the same 16-bit address space, and `offset_for_runtime()` resolves a
    target above 0x8000 against the *caller's own* bank -- so a `bank0` row
    naming 0x8001 is about bank 0's 0x8001, which is a different byte. Counting
    them would overstate the caller population for this run by 47 rows without
    saying whose bank they were in."""
    return [r for r in census
            if r["region"] == PROGRAM
            and RUN[0] <= int(r["target"], 16) < RUN[1]]


def survey(d, census, starts, listings):
    """One pass over the census rows, so the tables and --csv cannot disagree."""
    rows = []
    for r in target_rows(census):
        foff = int(r["file_offset"], 16)
        runtime = runtime_addr(foff, True)
        onto, over = converges_from(d, foff)
        kind, owner, op, text, idx = site_shape(runtime, starts, listings)
        rows.append({
            "file_offset": foff,
            "runtime": runtime,
            "opcode": r["opcode"],
            "target": int(r["target"], 16),
            "frame_onto": onto,
            "frame_over": over,
            "shape": kind,
            "owner": owner,
            "owner_opcode": op,
            "owner_text": text,
            "owner_index": idx,
            "census_onto": int(r["frame_onto"]),
            "census_over": int(r["frame_over"]),
            "image_byte": d[foff],
        })
    return rows


def per_target(rows, starts, listings):
    """One row per distinct target, best-framed caller first.

    `best` is the site's own `converges_from()` score, and it is carried
    *beside* `target_shape` rather than instead of it: a target no listing names
    as an instruction start is a byte scan pointing inside an instruction
    whatever its caller's score, which is the check that catches the
    runner-up."""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["target"]].append(r)
    out = []
    for target, rs in sorted(by.items()):
        best = max(rs, key=lambda r: (r["frame_onto"], -r["file_offset"]))
        owner, idx = owner_of(target, starts, listings)
        out.append({
            "target": target,
            "sites": len(rs),
            "anchored": sum(1 for r in rs if r["frame_onto"] > 0),
            "best_file_offset": best["file_offset"],
            "best_runtime": best["runtime"],
            "best_opcode": best["opcode"],
            "frame_onto": best["frame_onto"],
            "frame_total": best["frame_onto"] + best["frame_over"],
            "site_shape": best["shape"],
            "target_shape": "instruction-start" if idx == 0 else (
                "no-listing" if owner is None else "mid-instruction"),
        })
    return out


def annotated_in_run(annotations):
    return {int(r["addr"], 16) for r in annotations
            if r["scope"] == PROGRAM and RUN[0] <= int(r["addr"], 16) < RUN[1]}


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def print_run(index, d):
    rows = run_rows(index)
    addrs = [int(r["addr"], 16) for r in rows]
    sizes = [int(r["size"]) for r in rows]
    gaps, cur = [], RUN[0]
    for a, n in sorted(zip(addrs, sizes)):
        if a != cur:
            gaps.append((a, cur))
        cur = a + n
    if cur != RUN[1]:
        gaps.append((RUN[1], cur))
    print("## 1. The run, as `index.csv` records it")
    print()
    print(f"  {len(rows)} export(s) over 0x{RUN[0]:04X}-0x{RUN[1] - 1:04X}, "
          f"sizes summing to {sum(sizes)} against a run of {RUN[1] - RUN[0]}")
    print(f"  {len(gaps)} gap/overlap in the tiling"
          + (f" -- {gaps[:3]}" if gaps else ""))
    print(f"  {sum(1 for n in sizes if n == 1)} of them one instruction")
    print(f"  seed_basis: "
          f"{', '.join(sorted({r['seed_basis'] for r in rows}))}")
    before = d[offset_for_runtime(RUN[0] - 1, PROGRAM)]
    last = d[offset_for_runtime(RUN[1] - 1, PROGRAM)]
    print(f"  the byte before the run (0x{RUN[0] - 1:04X}) is 0x{before:02X}"
          f" and the run's last (0x{RUN[1] - 1:04X}) is 0x{last:02X}"
          f" -- both `ret`, asserted in --self-test")
    print()


def bucket_of_site(r):
    """What the byte at a census site is, given the instruction the committed
    listings say owns it. The four operand buckets are the whole finding, and
    they are distinguished by the owner's opcode and by *which* byte the site is
    -- a `0x02` in the last byte of a 3-byte `cjne` is a displacement, and the
    same byte in the second position of a `mov R1,#imm` is an immediate."""
    if r["shape"] == "start":
        return "start"
    if r["shape"] == "gap":
        return "gap"
    op, idx = r["owner_opcode"], r["owner_index"]
    last = idx == OPCODE_LEN[op] - 1
    if op in CJNE_OPCODES and last:
        return "cjne"
    if op in REL_OPCODES and last:
        return "relative"
    if op in (0x02, 0x12):
        return "absolute"
    return "other"


SITE_BUCKETS = [
    ("start", "an instruction start"),
    ("cjne", "the rel8 displacement byte of a `cjne` -- opcode 0xb4, 0xb5, "
             "0xba or 0xbf, each of which ends in 0x02 or 0x12"),
    ("relative", "the rel8 displacement byte of another PC-relative branch"),
    ("absolute", "the low target byte of an `ljmp`/`lcall` the listing already "
                 "carries"),
    ("other", "an immediate operand of an instruction that is not a branch"),
    ("gap", "in a committed gap, covered by no listing"),
]


def print_sites(rows):
    hist = collections.Counter(bucket_of_site(r) for r in rows)
    anchors = rows[0]["frame_onto"] + rows[0]["frame_over"] if rows else 0
    print("## 2. What those sites are, against the committed listings")
    print()
    print(f"  {len(rows)} site(s), {len({r['target'] for r in rows})} distinct "
          f"target(s), {sum(1 for r in rows if r['frame_onto'] == 0)} scoring "
          f"0/{anchors}")
    print()
    print("| what the site is, in a committed listing | count |")
    print("|---|---:|")
    for key, label in SITE_BUCKETS:
        print(f"| {label} | {hist.get(key, 0)} |")
    print()
    print("A `cjne` is 3 bytes with its displacement last, so the opcode is"
          " 0xb4/0xb5 (`cjne A,#imm,rel` / `cjne A,direct,rel`) or 0xb8-0xbf"
          " (`cjne Rn,#imm,rel`) and the byte a census row reads as an `ljmp`"
          " opcode is that displacement. This is"
          " `../annotations/bank-call-audit.md` 1's \"upper bound, not a"
          " partition\" in one measurable place.")
    print()
    anchored = [r for r in rows if r["frame_onto"] > 0]
    print("The anchored sites, most-framed first. The frame score is"
          " `converges_from()` and settles nothing by itself -- the listing"
          " column beside it is the half that does:")
    print()
    print("| runtime | file | census says | frame | in a committed listing it is |")
    print("|---|---|---|---:|---|")
    for r in sorted(anchored, key=lambda r: (-r["frame_onto"],
                                             r["file_offset"]))[:10]:
        if r["shape"] == "start":
            what = "an instruction start"
        elif r["shape"] == "gap":
            what = "in a committed gap"
        else:
            n = OPCODE_LEN[r["owner_opcode"]]
            what = (f"byte {r['owner_index'] + 1} of {n} -- "
                    f"`{r['owner_text']}`")
        print(f"| `0x{r['runtime']:04X}` | `0x{r['file_offset']:05X}` "
              f"| {r['opcode']} 0x{r['target']:04X} "
              f"| {r['frame_onto']}/{r['frame_onto'] + r['frame_over']} "
              f"| {what} |")
    print()


# The three `target_shape` values, as a table and a CSV cell read the same way.
TARGET_SHAPE = {
    "instruction-start": "yes",
    "mid-instruction": "no (mid-instruction)",
    "no-listing": "no (in a gap)",
}


def print_targets(targets, annotated):
    print("## 3. The per-target table")
    print()
    print("`frame` is the best-scoring caller of that target out of the 24"
          " preceding byte anchors. `target in a listing` is whether a committed"
          " `.asm` names the target as an instruction start; a `no` there is"
          " what disqualifies a framed call whose bytes point inside an"
          " instruction.")
    print()
    print("| target | callers | frame | best caller | target in a listing | annotation row |")
    print("|---|---:|---:|---|---|---|")
    for t in targets:
        print(f"| `0x{t['target']:04X}` | {t['sites']} "
              f"| {t['frame_onto']}/{t['frame_total']} "
              f"| `0x{t['best_runtime']:04X}` | {TARGET_SHAPE[t['target_shape']]} "
              f"| {'yes' if t['target'] in annotated else 'no'} |")
    print()


def print_verdicts(targets, annotated, sites, at_start):
    by = {t["target"]: t for t in targets}
    print("## 4. The addresses the annotations argue about")
    print()
    print("| address | census callers | best frame | target in a listing | annotation row |")
    print("|---|---:|---:|---|---|")
    for addr in (ENTRY_TARGET,) + SLICE_TARGETS:
        t = by[addr]
        print(f"| `0x{addr:04X}` | {t['sites']} "
              f"| {t['frame_onto']}/{t['frame_total']} "
              f"| {TARGET_SHAPE[t['target_shape']]} "
              f"| {'yes' if addr in annotated else 'no'} |")
    print()
    best_slice = max(by[a]["frame_onto"] for a in SLICE_TARGETS)
    total = by[ENTRY_TARGET]["frame_total"]
    print(f"  The entry is `0x{ENTRY_TARGET:04X}` at "
          f"{by[ENTRY_TARGET]['frame_onto']}/{total}; the best any of the five "
          f"slice addresses reaches is {best_slice}/{total}.")
    print()
    print("  **One confirmed caller found by this method is the whole of the"
          " finding.** It is not \"the only caller in the firmware\": the "
          f"{sites - at_start} other sites are gaps in a byte scan with a"
          " named blind spot, and `converges_from()`'s own docstring says a"
          " site nobody syncs onto is not thereby misframed -- it may simply"
          " be preceded by data no linear walk can decode into alignment."
          " `../annotations/bank-call-audit.md` 1 makes the same point from"
          " the other side, listing sites that score 24 of 24 and are plainly"
          " inside an address table.")
    print()


def write_csv(targets, annotated):
    w = csv.writer(sys.stdout)
    w.writerow(["target", "callers", "anchored_callers", "frame_onto",
                "frame_total", "best_caller_file_offset", "best_caller_runtime",
                "best_caller_opcode", "site_shape", "target_shape",
                "annotation_row"])
    for t in targets:
        w.writerow([
            f"0x{t['target']:04X}", t["sites"], t["anchored"],
            t["frame_onto"], t["frame_total"],
            f"0x{t['best_file_offset']:05X}", f"0x{t['best_runtime']:04X}",
            t["best_opcode"], t["site_shape"], t["target_shape"],
            "yes" if t["target"] in annotated else "no",
        ])


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

# The run's shape, as --self-test asserts it. A figure a reader can check
# against `index.csv` without running anything.
ORACLE = {
    "exports": 42,
    "bytes": 393,
    "one_instruction": 16,
    "sites": 180,
    "targets": 70,
    "at_instruction_start": 1,
    "cjne_displacement": 135,
    "annotated": 42,
    "entry_frame": (24, 24),
    "runner_up_frame": (5, 24),
}

CJNE_OPCODES = (0xB4, 0xB5, 0xBA, 0xBF)


def self_test(d, index, annotations, rows, targets) -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("counter_sweep_entry.py --self-test")

    idx = run_rows(index)
    by = {t["target"]: t for t in targets}
    annotated = annotated_in_run(annotations)

    check(len(idx) == ORACLE["exports"]
          and sum(int(r["size"]) for r in idx) == ORACLE["bytes"]
          and RUN[1] - RUN[0] == ORACLE["bytes"]
          and sum(1 for r in idx if int(r["size"]) == 1) == ORACLE["one_instruction"],
          f"index.csv splits the run into {ORACLE['exports']} exports whose "
          f"sizes sum to {ORACLE['bytes']}, {ORACLE['one_instruction']} of them "
          "one instruction")

    cur, tiled = RUN[0], True
    for r in sorted(idx, key=lambda r: int(r["addr"], 16)):
        if int(r["addr"], 16) != cur:
            tiled = False
        cur = int(r["addr"], 16) + int(r["size"])
    check(tiled and cur == RUN[1],
          f"and those {ORACLE['exports']} boundaries tile "
          f"0x{RUN[0]:04X}-0x{RUN[1] - 1:04X} with no gap and no overlap")

    check(len(rows) == ORACLE["sites"] and len(by) == ORACLE["targets"],
          f"{ORACLE['sites']} census site(s) from {PROGRAM} target into the "
          f"run, covering {ORACLE['targets']} distinct target(s)")

    check(all(r["image_byte"] in (0x02, 0x12) for r in rows),
          "every one of them is a 0x02 or 0x12 byte in the image, which is the "
          "census's own rule for a site")

    check(all(r["frame_onto"] == r["census_onto"]
              and r["frame_over"] == r["census_over"] for r in rows),
          "and the frame scores recomputed here with converges_from() are the "
          "ones bank-call-targets.csv already carries, on all "
          f"{len(rows)} rows")

    at_start = [r for r in rows if r["shape"] == "start"]
    check(len(at_start) == ORACLE["at_instruction_start"]
          and at_start[0]["runtime"] == ENTRY_SITE_RUNTIME
          and at_start[0]["target"] == ENTRY_TARGET,
          f"exactly {ORACLE['at_instruction_start']} of the {len(rows)} sites "
          f"is an instruction start in a committed listing, and it is "
          f"0x{ENTRY_SITE_RUNTIME:04X} -> 0x{ENTRY_TARGET:04X}")

    cjne = sum(1 for r in rows if bucket_of_site(r) == "cjne")
    check(cjne == ORACLE["cjne_displacement"],
          f"{ORACLE['cjne_displacement']} of the {len(rows) - len(at_start)} "
          "others are the rel8 displacement byte of a `cjne` (0xb4/0xb5/"
          "0xba/0xbf), which a 0x02/0x12 byte scan cannot tell from an `ljmp`")

    check(all(r["owner_index"] == OPCODE_LEN[r["owner_opcode"]] - 1
              for r in rows if bucket_of_site(r) == "cjne"),
          "and every one of them is the instruction's *last* byte, which is"
          " what makes it a displacement rather than the `cjne`'s immediate")

    entry = by[ENTRY_TARGET]
    check((entry["frame_onto"], entry["frame_total"]) == ORACLE["entry_frame"]
          and entry["best_runtime"] == ENTRY_SITE_RUNTIME,
          f"0x{ENTRY_TARGET:04X} is reached at "
          f"{ORACLE['entry_frame'][0]}/{ORACLE['entry_frame'][1]} from "
          f"0x{ENTRY_SITE_RUNTIME:04X}")

    worst = max(by[a]["frame_onto"] for a in SLICE_TARGETS)
    check(all(by[a]["frame_onto"] <= SLICE_MAX_FRAME for a in SLICE_TARGETS),
          f"each of {', '.join('0x%04X' % a for a in SLICE_TARGETS)} is reached "
          f"at no better than {SLICE_MAX_FRAME}/"
          f"{by[ENTRY_TARGET]['frame_total']} (the best of the five is {worst})")

    runner = by[RUNNER_UP_TARGET]
    check((runner["frame_onto"], runner["frame_total"]) == ORACLE["runner_up_frame"]
          and runner["best_runtime"] == RUNNER_UP_RUNTIME
          and runner["target_shape"] != "instruction-start",
          f"the runner-up site 0x{RUNNER_UP_RUNTIME:04X} frames at "
          f"{ORACLE['runner_up_frame'][0]}/{ORACLE['runner_up_frame'][1]} and its "
          f"target 0x{RUNNER_UP_TARGET:04X} is "
          f"{TARGET_SHAPE[runner['target_shape']]} in any committed listing"
          " -- which is why the frame score alone settles nothing")

    onto, over = converges_from(d, offset_for_runtime(RUN[0], PROGRAM))
    check((onto, onto + over) == ORACLE["entry_frame"],
          f"0x{RUN[0]:04X} is itself a frame boundary in the image, {onto} of "
          f"{onto + over} preceding anchors decoding onto it")

    check(d[offset_for_runtime(RUN[0] - 1, PROGRAM)] == RET
          and d[offset_for_runtime(RUN[1] - 1, PROGRAM)] == RET,
          f"the byte before the run and the run's last byte are both 0x{RET:02X}"
          " (`ret`): the one ending the preceding routine, and the one ending "
          "this one")

    check(len(annotated) == ORACLE["annotated"] and annotated <= set(by),
          f"{ORACLE['annotated']} annotation row(s) sit in the run and every one "
          f"of them is a census target, so deleting them removes "
          f"{len(annotated & set(by))} of the {len(by)} seeds rather than all "
          f"of them -- {len(set(by) - annotated)} census seed(s) would remain, "
          "and seed_rows() takes the union of the two")

    # The two silent misreadings, asserted rather than described.
    runtime = runtime_addr(ENTRY_SITE_FILE_OFFSET, True)
    listing = os.path.join(EC_DIR, "decompiled", PROGRAM, f"{runtime:04X}.asm")
    wrong = os.path.join(EC_DIR, "decompiled", PROGRAM,
                         f"{ENTRY_SITE_FILE_OFFSET:04X}.asm")
    check(runtime == ENTRY_SITE_RUNTIME and os.path.isfile(listing)
          and not os.path.isfile(wrong),
          f"the path index: file offset 0x{ENTRY_SITE_FILE_OFFSET:05X} is "
          f"runtime 0x{runtime:04X}, so the listing is "
          f"{PROGRAM}/{runtime:04X}.asm and "
          f"{PROGRAM}/{ENTRY_SITE_FILE_OFFSET:04X}.asm does not exist -- keying "
          f"listings by file_offset reports all {len(rows)} sites unframed")

    sample = f"{ENTRY_SITE_RUNTIME:04X}     12 01 02 lcall     0x0102"
    loose = LOOSE_ADDR_RE.findall(sample)
    anchored = LINE_RE.match(sample)
    check(len(loose) == 2 and loose[0] == f"{ENTRY_SITE_RUNTIME:04X}"
          and loose[1] == "0102" and anchored is not None
          and anchored.group(1) == f"{ENTRY_SITE_RUNTIME:04X}",
          f"the listing regex: an unanchored four-hex-digit search on one "
          f"instruction line returns the branch target as well as the address "
          f"({loose}, and {loose[1]} is an operand, not a second instruction), "
          "so the parse is anchored at the line start")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=FIRMWARE,
                    help="raw EC firmware image (default: the committed one)")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per distinct target on stdout instead "
                         "of the tables")
    ap.add_argument("--self-test", action="store_true",
                    help="assert the entry, the slice scores, the cjne count "
                         "and the two path/regex misreadings against the "
                         "committed tree")
    args = ap.parse_args(argv)

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is "
              "not the image the recorded counts were taken from",
              file=sys.stderr)
        return 1

    census, index = load_census(), load_index()
    annotations = load_annotations()
    annotated = annotated_in_run(annotations)
    starts, listings = read_listings(PROGRAM)
    rows = survey(d, census, starts, listings)
    targets = per_target(rows, starts, listings)

    if args.self_test:
        return self_test(d, index, annotations, rows, targets)

    if args.csv:
        write_csv(targets, annotated)
        return 0

    print_run(index, d)
    print_sites(rows)
    print_targets(targets, annotated)
    print_verdicts(targets, annotated, len(rows),
                   sum(1 for r in rows if r["shape"] == "start"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
