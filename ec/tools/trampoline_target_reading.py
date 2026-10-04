#!/usr/bin/env python3
"""Say what a trampoline target *is*: whether it sits in a fill run, and who
calls the entry that names it.

`trampoline_target_census.py` (issue #574) gave every entry in the BL51 block a
row: the `imm16`, the bank its own tail-jump stub selects, the byte read **in
that bank**, and whether a committed listing covers it. That answers *what is
at the target*. This answers the two questions its columns cannot carry, both
of which `bank-call-audit.md` section 3 leaves open:

  * **is the target inside a run of identical bytes** -- the census has
    `target_byte` and `target_class`, and `0x22` is neither `entry` nor
    `erased`, so a row whose target begins with `ret` reads `other` whether it
    is a lone one-instruction routine or the 300th byte of a fill; and
  * **how many call sites reach the entry** -- a target nothing calls and a
    target one caller reaches are different claims, and `bank-call-targets.csv`
    carries the sites without joining them to the entry.

Both are joins rather than new scans: the entries, the banks and the target
bytes are **imported** from `trampoline_target_census`, and the call sites are
read out of the committed `bank-call-targets.csv`. Neither is re-derived, so
this table cannot disagree with the census about which entries exist or what is
at a target -- a drift in either is a red run in `test_trampoline_target_reading.py`,
which holds the two committed tables against each other.

**What a target inside a `ret` run is, and what this does not decide.** The
stub at `0x1100` pushes `0x08`, pushes the accumulator, pushes DPL and DPH,
selects the bank, clears DPTR, and `ret`s -- and that `ret` consumes the two
DPTR bytes it pushed, so **control reaches the target**; what the target's own
`ret` then pops is the marker, not the caller's return address
(`docs/findings/scheduler-run-8518-entries.md` section 2 derives this from the
stub's bytes, and `run_entry_map.py --self-test` re-derives it). A target that
begins with `0x22` is therefore a far routine one instruction long.

That is the *mechanism*, and it is settled from bytes. Whether the 138-byte
run at `0xBF54`-`0xBFDD` is linker padding, a shared return, or dead code is
**not** decided here: that is issue #1080's question, this reports the run's
extent and the callers, and no `status:` in `ec/annotations/registers.yaml`
moves on any of it.

**The threshold, and why the count is not doing the work.** `ret` is a one-byte
opcode that ends a routine, and the tree holds named one-instruction `ret`
routines (`bank0,0xD9DB` `ret_stub`, `bank0,0xD2BE` `ret_only_d2be`, and issue
#559's `0xD89F`), so a single byte decides nothing -- the same argument
`audit_call_targets.MIN_ERASED_RUN` makes for a lone `0xFF`. What decides it is
the **run**, and the threshold is picked inside a range where the population
does not move: `--self-test` sweeps it and the count is flat from
`MIN_RET_RUN` up to the longest run carrying the population, falling on either
side of that. The sweep reaches past both bounds deliberately, so the flatness
is bounded by a measured fall rather than by where the list stops.

**Nothing here was observed on hardware.** No register was read back, no
capture opened, no Windows machine and no Ghidra run. Every figure is a static
read of `ec/firmware/GMxMGxx_11.800` and of files already committed.

Usage:
    python3 ec/tools/trampoline_target_reading.py
    python3 ec/tools/trampoline_target_reading.py --csv > targets.csv
    python3 ec/tools/trampoline_target_reading.py --check
    python3 ec/tools/trampoline_target_reading.py --write
    python3 ec/tools/trampoline_target_reading.py --self-test
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from audit_call_targets import MIN_ERASED_RUN, erased_runs
from trampoline_target_census import (BLOCK_HI, BLOCK_LO, RET, bank_region,
                                      block_entries, census, fill_runs,
                                      region_bounds)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))

DEFAULT_FIRMWARE = "ec/firmware/GMxMGxx_11.800"
DEFAULT_CSV = "ec/annotations/trampoline-target-reading.csv"
DEFAULT_CALLS = "ec/annotations/bank-call-targets.csv"

# Shortest run of `ret` read as a fill rather than as one-instruction routines.
#
# Picked in the **middle** of the range where the population does not move,
# not at its edge and not where the count first looks meaningful.
# `--self-test` sweeps it and derives both bounds: the count falls from the
# two-byte runs, is flat across a middle band, and falls again past the
# shorter of the two runs carrying the population. This value is inside that
# band with room on both sides, which is what makes `in_ret_run` a reading of
# the run rather than of the cutoff -- at an edge it would be one measurement
# away from a different population, and a reader would have to re-derive the
# sweep to find out which side it was on.
#
# `SWEEP` deliberately reaches past the upper bound so the second fall is
# visible on every run: a sweep that stopped at the chosen value would read as
# flat and would be reporting only where it stopped looking.
#
# Module-level rather than written into the `check()` calls that use it, for
# the reason `audit_call_targets.py` gives for `TRAMP_STRIDE` and
# `STUB_SITES`: `check_doc_figure_pins.py` reads every int constant inside an
# asserting call across `ec/tools/*.py` as a pin for a figure in some document,
# so a bare literal here would make this module an uncited second source for
# one. A named constant is what the search resolves.
MIN_RET_RUN = 12

# The sweep `--self-test` prints, low to high, spanning below the flat band,
# across it, and past its upper bound -- so both falls are measured rather than
# implied by where the list ends.
SWEEP = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 20, 24, 32)

# One planted BL51 entry, as (offset, six bytes, what the guard below is for).
# The shape is `trampoline_target_census.MOV_DPTR` plus a 3-byte tail naming a
# stub the image really has, so `audit_call_targets.trampolines()` accepts it
# and only the *census's own* range restriction stands between it and the 403.
#
# Two cases, because a range check has two ways to be wrong and only one of
# them shows up on a buffer nobody plants anything in:
#
#   INSIDE   planted at 0x1153, between two real entries. It is well-formed
#            and in range, so it must be absorbed by the scan -- and then the
#            stride is no longer one run, which is the property
#            `trampoline_target_census` asserts the block's framing by. A
#            census that reported 404 entries here would be reporting a stride
#            of 6 and 9, not 6, so the framing check is what catches it.
#   OUTSIDE  planted at 0x1AC2, six bytes past the block's last entry and
#            still inside the common area, so `trampolines()` finds it and
#            `block_entries()`'s range test is the only thing that keeps it out
#            of the table. This is the case that would silently become 404.
#
# Module-level for the reason `MIN_RET_RUN` gives.
PLANTED = (
    ("INSIDE", 0x1153, b"\x90\x12\x34\x02\x11\x00"),
    ("OUTSIDE", 0x1AC2, b"\x90\x12\x34\x02\x11\x00"),
)

# `bank-call-audit.md` section 4's 16-byte rule, imported rather than restated:
# this table's `in_erased_run` column is that rule applied to the target byte,
# and a second literal would be a second thing to keep in step.
ERASED_RUN = MIN_ERASED_RUN

# The two cells the census's own columns cannot express, plus what this table
# adds to them. `call_sites` is the number of committed `calls_trampoline`
# rows naming the entry -- an **upper bound**, because that column comes from a
# byte scan whose framing section 2 of the audit calls unsettled; `caller_ops`
# is the opcode mix over those same rows, kept beside the count because
# `ljmp` and `lcall` reach an entry by different routes and the difference is
# the reading.
CSV_HEAD = ["file_offset", "runtime", "stub", "selects_bank", "dptr_target",
            "target_byte", "target_class", "ret_run", "in_ret_run",
            "in_erased_run", "call_sites", "caller_ops"]


def call_sites_by_entry(path: str = None):
    """{entry address: [(opcode, region, file_offset)]} from the committed CSV.

    Read from `bank-call-targets.csv` rather than re-scanned, because that
    table is where the tree already publishes its call sites and a second scan
    would be a second answer to its question. Only rows whose
    `calls_trampoline` cell is non-empty are call sites *of a trampoline
    entry*; the rest name something else and joining them would attribute
    calls to entries that were never called.

    **The count this returns is an upper bound.** That column comes from the
    byte scan `bank-call-audit.md` section 2 reports as unsettled in both
    directions: it over-counts, because `0x02`/`0x12` also occur as operand
    bytes, and it is not anchored to an instruction boundary. So "one call
    site" means *the scan finds one*, which is the sentence the write-up uses.
    """
    path = path or os.path.join(REPO, *DEFAULT_CALLS.split("/"))
    out = collections.defaultdict(list)
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh, strict=True):
            if not row.get("calls_trampoline"):
                continue
            try:
                target = int(row["target"], 16)
                off = int(row["file_offset"], 16)
            except (KeyError, TypeError, ValueError) as exc:
                raise SystemExit(
                    f"error: {path} row for {row.get('region')!r} "
                    f"{row.get('file_offset')!r} does not parse as an address "
                    f"({exc}); a row dropped here is a caller that silently "
                    "stops being counted")
            out[target].append((row["opcode"], row["region"], off))
    return out


def ret_runs(d: bytes, banks):
    """{bank: [(lo, hi)]} inclusive file-offset extents of `ret` runs.

    `fill_runs()` from the census is the only implementation; it is imported
    rather than rewritten so the two tables agree on what a run is by
    construction. Inclusive at both ends because `0xBF54`-`0xBFDD` names a
    range and `0xBF54`-`0xBFDE` does not.
    """
    return {b: fill_runs(d, *region_bounds(bank_region(b)), RET) for b in banks}


def run_at(runs, bank: int, off: int):
    """`(lo, hi)` for the run holding file offset `off`, or None.

    The lookup a caller does per row. A run too short to count is still
    *returned*: the decision belongs to `in_ret_run`'s threshold, so this
    function reports the shape and the caller applies the cutoff. That split is
    what lets `--self-test` sweep the threshold without re-deriving the runs.
    """
    for lo, hi in runs.get(bank, ()):
        if lo <= off <= hi:
            return (lo, hi)
    return None


def runtime_of(bank: int, off: int) -> int:
    """The runtime address a bank's file offset answers to."""
    return 0x8000 + off - region_bounds(bank_region(bank))[0]


def reading(d: bytes, calls=None):
    """One dict per block entry, in address order.

    The census's own `census()` supplies every row's entry, stub, bank, target
    and target byte, so this cannot disagree with it about any of them; what is
    added here is the run the target sits in and the call sites that reach the
    entry. Both are per-row joins, so the report, the table and `--self-test`
    are all reading one pass.
    """
    rows = census(d)
    banks = sorted({r["selects_bank"] for r in rows})
    runs = ret_runs(d, banks)
    erased = {b: erased_runs(d, *region_bounds(bank_region(b))) for b in banks}
    if calls is None:
        calls = call_sites_by_entry()
    out = []
    for r in rows:
        bank = r["selects_bank"]
        off = r["target_file_offset"]
        run = run_at(runs, bank, off)
        sites = calls.get(r["file_offset"], [])
        out.append({
            "file_offset": r["file_offset"],
            "runtime": r["runtime"],
            "stub": r["stub"],
            "selects_bank": bank,
            "dptr_target": r["target"],
            "target_byte": r["target_byte"],
            "target_class": r["target_class"],
            "ret_run": run,
            "in_ret_run": run is not None and run[1] - run[0] + 1 >= MIN_RET_RUN,
            "in_erased_run": any(a <= off < b for a, b in erased[bank]),
            "call_sites": len(sites),
            "caller_ops": collections.Counter(op for op, _, _ in sites),
        })
    return out


def csv_rows(rows):
    """[list of str] -- the committed spelling of one row each."""
    out = []
    for r in rows:
        run = r["ret_run"]
        out.append([
            f"0x{r['file_offset']:05X}", f"0x{r['runtime']:04X}",
            f"0x{r['stub']:04X}", r["selects_bank"],
            f"0x{r['dptr_target']:04X}", f"0x{r['target_byte']:02X}",
            r["target_class"],
            "-" if run is None else
            "0x%04X-0x%04X" % (runtime_of(r["selects_bank"], run[0]),
                               runtime_of(r["selects_bank"], run[1])),
            "yes" if r["in_ret_run"] else "no",
            "yes" if r["in_erased_run"] else "no",
            r["call_sites"],
            ";".join("%s=%d" % (op, n)
                     for op, n in sorted(r["caller_ops"].items())) or "-",
        ])
    return out


def csv_text(d: bytes) -> str:
    """The whole table as CSV text, from the image."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEAD)
    w.writerows(csv_rows(reading(d)))
    return buf.getvalue()


# --- reporting --------------------------------------------------------------

def print_runs(rows) -> None:
    """The run each target sits in, longest first, and the threshold sweep."""
    banks = sorted({r["selects_bank"] for r in rows})
    sel = [r for r in rows if r["ret_run"] is not None
           and r["ret_run"][1] - r["ret_run"][0] + 1 >= MIN_RET_RUN]
    print("## 1. Targets inside a `ret` run, and the runs themselves")
    print()
    print("`ret` is one byte and ends a routine, and the tree holds named")
    print("one-instruction `ret` routines, so a byte test decides nothing -- the")
    print("run does. The threshold is where the count stops moving:")
    print()
    by_run = collections.defaultdict(list)
    for r in sel:
        by_run[(r["selects_bank"], r["ret_run"])].append(r)
    print("| bank | run | bytes | targets | call sites |")
    print("|---|---|---:|---:|---:|")
    for (bank, run), holders in sorted(by_run.items(),
                                       key=lambda kv: -(kv[0][1][1] - kv[0][1][0])):
        lo = "0x%04X" % runtime_of(bank, run[0])
        hi = "0x%04X" % runtime_of(bank, run[1])
        print(f"| bank {bank} | `{lo}`-`{hi}` | {run[1] - run[0] + 1} "
              f"| {len(holders)} | {sum(h['call_sites'] for h in holders)} |")
    print()
    print(f"  {len(sel)} of {len(rows)} targets sit inside a run of at least "
          f"{MIN_RET_RUN} `ret`")
    print("  bytes. Every one is read in the bank its own stub selects, and "
          "`ret_run` is `-`")
    print("  for the rest, which is a statement about the run and not about "
          "the byte.")
    print()
    longer = [r for r in rows if r["ret_run"] is not None and not r["in_ret_run"]]
    if longer:
        print("  In a run too short to count, which the threshold decides and the")
        print("  run does not:")
        print()
        for r in sorted(longer, key=lambda r: -(r["ret_run"][1] - r["ret_run"][0])):
            run = r["ret_run"]
            print("    0x%04X -> 0x%04X, a %d-byte run at `0x%04X`-`0x%04X`"
                  % (r["file_offset"], r["dptr_target"], run[1] - run[0] + 1,
                     runtime_of(r["selects_bank"], run[0]),
                     runtime_of(r["selects_bank"], run[1])))
        print()


def print_callers(rows) -> None:
    """Who reaches each entry, for the affected population and the rest."""
    print("## 2. How many call sites reach each entry")
    print()
    print("`call_sites` counts rows of the committed `bank-call-targets.csv`")
    print("whose `calls_trampoline` cell is non-empty. **That is a byte-scan")
    print("upper bound** -- `bank-call-audit.md` section 2 calls the framing")
    print("unsettled in both directions -- so the sentence is *the scan finds*")
    print("one call site, not *there is* one.")
    print()
    for label, sel in (("inside a counted `ret` run",
                        [r for r in rows if r["in_ret_run"]]),
                       ("every other target",
                        [r for r in rows if not r["in_ret_run"]])):
        hist = collections.Counter(r["call_sites"] for r in sel)
        spread = ", ".join(f"{n} with {c}" for c, n in sorted(hist.items()))
        print(f"  {label} -- {len(sel)} entries: {spread}.")
        print()
    ops = collections.Counter()
    for r in rows:
        if r["in_ret_run"]:
            ops.update(r["caller_ops"])
    if ops:
        print("  Opcode mix over those sites: "
              + ", ".join(f"{op} {n}" for op, n in sorted(ops.items()))
              + ".")
        print("  The write-up reads the `ljmp`/`lcall` split; it is a property "
              "of the call")
        print("  sites, not of the targets.")
        print()


def print_erased(rows) -> None:
    """The erased-run column, reported as the result it is."""
    hits = [r for r in rows if r["in_erased_run"]]
    print("## 3. Erased flash at a target")
    print()
    print(f"  {len(hits)} of {len(rows)} targets sit in a run of at least "
          f"{ERASED_RUN}")
    print("  `0xFF` bytes in the bank their own stub selects.")
    print()
    print("  **Not found by this method**, and worth saying in both directions:")
    print("  the rule is `bank-call-audit.md` section 4's own, run at the")
    print("  target byte rather than at a call target. It is a property of")
    print("  these bytes, not a statement that either bank has no erased flash")
    print("  -- both do, at addresses this table does not name.")
    print()


def report(d: bytes) -> None:
    print("## 0. The block")
    print()
    rows = reading(d)
    print(f"  0x{BLOCK_LO:04X}-0x{BLOCK_HI:04X}, {len(rows)} entries, one row")
    print("  each. Entries, banks and target bytes are imported from")
    print("  `trampoline_target_census`; call sites are read from the committed")
    print("  `bank-call-targets.csv`. Nothing is re-scanned.")
    print()
    print_runs(rows)
    print_callers(rows)
    print_erased(rows)


# --- self-test --------------------------------------------------------------

def self_test(d: bytes) -> int:
    """The refusals, the flatness, and the join's two ends.

    Every figure is recomputed from the image or read off a committed file.
    None is a literal except through a named constant, so a dump that moved one
    would redden this for a reason the message names.
    """
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    print("trampoline_target_reading.py --self-test")
    print()

    # 1. The block's framing, re-derived from the bytes rather than read off the
    #    scan's own dict. This table's population is the census's, so it
    #    inherits the framing instead of checking it -- and every figure below
    #    is a statement about *these* entries.
    entries = block_entries(d)
    strides = sorted({b - a for a, b in zip([e for e, _, _ in entries],
                                            [e for e, _, _ in entries][1:])})
    check(len(entries) == len({e for e, _, _ in entries})
          and all(BLOCK_LO <= e <= BLOCK_HI for e, _, _ in entries),
          f"the {len(entries)} entries are distinct and every one is inside "
          f"0x{BLOCK_LO:04X}-0x{BLOCK_HI:04X}")
    check(strides == [6],
          "and they are one unbroken six-byte stride over the block -- the "
          "framing every count below is a statement about"
          f"{'' if strides == [6] else ' -- strides ' + str(strides)}")

    # 2. The stub split, so a `census()` that lost its bank cannot pass here by
    #    grading itself against its own output.
    rows = reading(d)
    split = collections.Counter(r["stub"] for r in rows)
    check(len(split) == 2,
          f"the entries route through {len(split)} stubs "
          f"({', '.join('0x%04X' % s for s in sorted(split))})")
    per_entry = collections.Counter(r["selects_bank"] for r in rows)
    census_rows_ = census(d)
    check(all(r["selects_bank"] == c["selects_bank"]
              and r["dptr_target"] == c["target"]
              and r["target_byte"] == c["target_byte"]
              for r, c in zip(rows, census_rows_)),
          "and every row's bank, immediate and target byte is the census's "
          "own, read across rather than re-derived")

    # 3. The refusal fixtures. A well-formed entry planted in a buffer must be
    #    refused or made visible, never absorbed silently -- and which of the
    #    two it is depends on where it lands.
    for name, off, raw in PLANTED:
        buf = bytearray(d)
        buf[off:off + len(raw)] = raw
        after = block_entries(bytes(buf))
        added = [e for e, _, _ in after if e not in {x for x, _, _ in entries}]
        if name == "OUTSIDE":
            check(not added and len(after) == len(entries),
                  f"a well-formed entry planted {off:#06x}, outside the block, "
                  f"is not absorbed into the {len(entries)} (got {len(after)}) "
                  "-- the range restriction, not the scan, is what excludes it")
        else:
            after_e = [e for e, _, _ in after]
            st = sorted({b - a for a, b in zip(after_e, after_e[1:])})
            check(bool(added) and st != [6],
                  f"and one planted {off:#06x}, inside the block, IS taken by "
                  f"the scan (it appears at {[hex(a) for a in added]}) and the "
                  f"stride is then {st} rather than one run -- so a planted "
                  "entry cannot be absorbed without the framing check seeing it")

    # 4. The threshold's flatness. This is the load-bearing property of
    #    `in_ret_run`: the number must not depend on where in the flat range the
    #    cutoff sits, or the column is a reading of the cutoff rather than of
    #    the run. Printed as the whole sweep, not the chosen figure alone.
    runs = ret_runs(d, sorted({r["selects_bank"] for r in rows}))

    def counted(n):
        return sum(1 for r in rows
                   if r["ret_run"] is not None
                   and r["ret_run"][1] - r["ret_run"][0] + 1 >= n)

    # The band is derived over **every** threshold, not over `SWEEP`'s
    # sampled values: a walk that stopped at the first gap in the sample would
    # report a band narrower than the real one, which is the same defect as
    # reading flatness off a list that ends where the author stopped looking.
    # `counted()` is cheap (a length comparison per row), so the whole range
    # from the smallest run to the largest is swept and `SWEEP` is only what
    # gets *printed*.
    lengths = [r["ret_run"][1] - r["ret_run"][0] + 1
               for r in rows if r["ret_run"] is not None]
    every = {n: counted(n) for n in range(min(lengths), max(lengths) + 1)}
    sweep = {n: every[n] for n in SWEEP if n in every}
    chosen = counted(MIN_RET_RUN)
    lo = MIN_RET_RUN
    while lo - 1 in every and every[lo - 1] == chosen:
        lo -= 1
    hi = MIN_RET_RUN
    while hi + 1 in every and every[hi + 1] == chosen:
        hi += 1
    check(lo < MIN_RET_RUN <= hi,
          f"the count is {chosen} at every threshold from {lo} to {hi}, and "
          f"{MIN_RET_RUN} is strictly inside that band rather than at either "
          "edge -- so the threshold is not selecting the population")
    check(lo - 1 in every and every[lo - 1] != chosen,
          f"and the band is bounded below by a measured fall: at {lo - 1} the "
          f"count is {every.get(lo - 1)}")
    check(hi + 1 in every and every[hi + 1] != chosen,
          f"and above by one too: at {hi + 1} it is {every.get(hi + 1)}, "
          "because the shorter of the two runs carrying the population stops "
          "qualifying while the longer one has not")
    print("        sweep (the count moves below the band and again past its "
          "upper bound,")
    print("        which is what makes the band a measurement; every "
          "threshold from the")
    print("        shortest run to the longest is walked, this is a sample of "
          "it):")
    print("        " + ", ".join(f"{n}: {sweep[n]}" for n in SWEEP))
    check(chosen == sum(1 for r in rows if r["in_ret_run"]),
          f"and `in_ret_run` agrees with the sweep at {MIN_RET_RUN} ({chosen})")

    # 5. A run's extent is a range, and every byte of a reported run is the
    #    value it claims. Inclusive at both ends, or `0xBF54`-`0xBFDD` would
    #    name one byte fewer than it holds.
    sel = [r for r in rows if r["in_ret_run"]]
    check(all(all(d[i] == RET for i in range(lo, hi + 1))
              for r in sel for lo, hi in [r["ret_run"]]),
          f"every byte of every run reported for the {len(sel)} selected "
          "entries really is `0x22`, which is what makes the extent a run "
          "rather than a span")
    check(all(r["ret_run"] is None or r["target_byte"] == RET for r in rows),
          "and a row carries a run only when its own target byte is `0x22`")
    check(all(r["ret_run"] is None
              or r["ret_run"][1] - r["ret_run"][0] + 1 >= MIN_RET_RUN
              for r in rows if r["in_ret_run"]),
          "and `in_ret_run` is never set on a run shorter than the threshold")
    longer = [r for r in rows if r["ret_run"] is not None and not r["in_ret_run"]]
    check(all(r["ret_run"][1] - r["ret_run"][0] + 1 < MIN_RET_RUN
              for r in longer),
          f"while the {len(longer)} row(s) carrying a run too short to count "
          "keep the run and drop only the verdict -- the shape is reported and "
          "the cutoff is applied to it, not the other way round")

    # 6. The run partition: no entry is in two runs, and the runs reported
    #    cover exactly the entries that claim one.
    seen = collections.Counter()
    for r in rows:
        if r["ret_run"] is not None:
            seen[(r["selects_bank"], r["ret_run"])] += 1
    check(sum(seen.values()) == sum(1 for r in rows if r["ret_run"] is not None),
          "every row carrying a run is counted under exactly one run, so the "
          "runs partition them rather than overlapping")

    # 7. The join's two ends. Every site names an entry this table has, and
    #    every entry's count is the number of sites naming it. A site resolving
    #    to nothing would be a caller attributed to no thunk, and an entry
    #    counted twice would inflate the shape the write-up reads.
    calls = call_sites_by_entry()
    known = {r["file_offset"] for r in rows}
    unresolved = sorted(t for t in calls if t not in known)
    check(not unresolved,
          f"every one of the {sum(len(v) for v in calls.values())} committed "
          "call sites naming a trampoline resolves to an entry in this table"
          f"{'' if not unresolved else ' -- unresolved at ' + ', '.join(hex(t) for t in unresolved[:8])}")
    check(all(r["call_sites"] == len(calls.get(r["file_offset"], []))
              for r in rows),
          "and every entry's `call_sites` is the number of sites naming it, "
          "read from the same committed file")
    check(all(sum(r["caller_ops"].values()) == r["call_sites"] for r in rows),
          "with `caller_ops` summing to `call_sites` on every row -- the opcode "
          "mix is a split of the count, not a second count")

    # 8. The census's own columns are carried, not recomputed: this table must
    #    not be able to disagree with it about a byte. Held as a relationship
    #    rather than against the committed CSV, so a re-export of either moves
    #    both without either moving here.
    check(all(c["target_class"] == r["target_class"]
              and c["stub"] == r["stub"]
              and c["file_offset"] == r["file_offset"]
              for r, c in zip(rows, census_rows_)),
          "every row's class, stub and entry address is the census row's, so "
          "the two tables cannot drift apart on a byte")

    # 9. The committed table, regenerated in memory and diffed.
    committed = os.path.join(REPO, *DEFAULT_CSV.split("/"))
    if os.path.exists(committed):
        want = open(committed).read()
        got = csv_text(d)
        check(want == got,
              f"{DEFAULT_CSV} is reproduced byte for byte by --write, so the "
              "committed table and every count above it are unchanged"
              f"{'' if want == got else ' -- differs; regenerate it with --write'}")
    else:
        check(False, f"{DEFAULT_CSV} does not exist; generate it with --write")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s)")
        return 1
    print("self-test passed: the planted entries are refused, the threshold "
          "sits inside a measured flat band, and the join resolves at both "
          "ends")
    return 0


# --- committed table --------------------------------------------------------

def check_csv(d: bytes, path: str) -> int:
    """Diff the regenerated table against the committed one. Exit 1 on a diff."""
    if not os.path.exists(path):
        print(f"error: {path} does not exist. --check compares; it never "
              "creates. Generate the table with --write and commit it.",
              file=sys.stderr)
        return 1
    want = open(path).read()
    got = csv_text(d)
    if got == want:
        print(f"{os.path.relpath(path, REPO)}: matches the committed file, "
              "byte for byte")
        return 0
    sys.stdout.writelines(difflib.unified_diff(
        want.splitlines(True), got.splitlines(True),
        fromfile=f"committed {path}", tofile="regenerated"))
    print("error: the committed table is not what this run derives from the "
          "image", file=sys.stderr)
    return 1


def write_csv(d: bytes, path: str) -> int:
    """The one file this tool writes, and only under `--write`."""
    with open(path, "w") as f:
        f.write(csv_text(d))
    print(f"wrote {os.path.relpath(path, REPO)}")
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
                      help="re-derive the framing, check the refusals and the "
                           "threshold's flatness")
    ap.add_argument("--csv-path", default=DEFAULT_CSV,
                    help="the committed table (default %(default)s)")
    args = ap.parse_args()

    path = resolve(args.firmware)
    if not os.path.isfile(path):
        ap.error(f"no firmware image at {args.firmware}")
    d = open(path, "rb").read()
    from trace_xdata_refs import PD_MARKER
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
        sys.stdout.write(csv_text(d))
        return 0
    report(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
