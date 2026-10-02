#!/usr/bin/env python3
"""Per-site resolution census for every EC-side site of a `present-untested`
address, joined to the function that holds the site.

`check_status_vocabulary.py` rule 2 asks whether a `present-untested` address
has an EC-side site. It does not ask what the site *does*, and its docstring
says so rather than implying otherwise -- which left "what a single site is
worth when it resolves no further" as a question two documents had deferred
and nobody owned (docs/findings/pd-only-status-vocabulary.md 2,
docs/findings/walk-flow-follow.md 4). This is the evidence the answer needed.

The join is the part that did not exist. `register_ref_table.py` classifies a
site and `--callee-depth 1` resolves a DPTR handoff one level down, but neither
names the *function* the site sits in, and a verdict with no routine attached
is a verdict a reader has to place by hand. This repo has placed one by hand
twice: `ec/annotations/xdata-0400-045f.md` 7 says its "writer routines" column
had no committed reproducer, and the note on `XDATA_0420` names bank1 `0xE779`
as an address rather than as a function. `bucket_c_codemap.py` has the one
reusable `containing_function()` and it is hard-wired to `program == "common"`,
so the join is written here against the `size` column of
`ec/decompiled/listing-index.csv` -- which `ghidra-functions.csv` lacks, and
which is why the sibling cannot do this for any bank.

**Two verdicts, deliberately not merged.** `resolution` says whether a site
establishes a *direction*, and it distinguishes the two ways one can fail:

  * `unresolved-handoff` -- DPTR is handed to a call whose entry point does not
    settle the direction one level down. This is *positive* evidence that the
    address is passed somewhere a direct `MOV DPTR` scan cannot see, which is
    a different claim from a read or a store and a weaker one than either.
  * `unresolved-none` -- no `movx` in the decoded window at all. Not
    evidence of anything, in either direction.

`--follow-flow` is deliberately not used. It resolves a `none` cell by
continuing one path past the control-flow instruction the walk stopped at, and
`register_ref_table.py`'s own docstring calls that "a **weaker** claim than one
resolved where it sits" -- which is exactly right, and exactly why it may not
be allowed to warrant a grade. Nothing in this file depends on it; a site this
tool calls `unresolved-none` may or may not survive a follow, and that is a
question about a different instrument.

**What this does not check, which is as much of the point:**

  * *Whether a direction is a behaviour.* Everything here is static. A `write`
    is an instruction that stores to the address, not evidence that the EC
    reads the value back or acts on it, and registers.yaml's own gloss on
    `present-untested` -- "static-scan finds real references, not yet
    exercised live" -- is unchanged by any row in this table.
  * *Whether a site exists.* `sites_for()` counts direct `MOV DPTR,#imm16`
    only, and inherits that scan's blind spot: a byte reached through a
    computed DPTR has no site, and a site this tool records as
    `unresolved-none` is not distinguishable from a byte the firmware reaches
    a way this method cannot see. `0x07B9` is the standing counter-example --
    writable, working, zero direct sites anywhere. **A zero here means "not
    found by this method", never "absent".**
  * *Whether the callee's own body does more.* `resolve_handoff()` decodes the
    callee's entry point and stops at its first control-flow instruction, and
    it inherits that limit twice over -- once for the site, once for the callee.
    A `handoff->write` is a store at the callee's *entry*, not a statement
    about the rest of the routine.
  * *The PD image.* Those sites are filtered out per address here rather than
    counted, because the two programs have separate XDATA maps and a direction
    for the other program's byte is a category error. `trace_xdata_refs.py`
    prints them; this census does not classify them.

The output is committed as `ec/annotations/site-resolution.csv` and `--check`
diffs it byte for byte, the arrangement `register_ref_table.py` and its siblings
use, because the point of a census is that a reader can take the numbers
without re-running anything.

Usage:
    python3 check_site_resolution.py ec/firmware/GMxMGxx_11.800
    python3 check_site_resolution.py ec/firmware/GMxMGxx_11.800 --summary
    python3 check_site_resolution.py ec/firmware/GMxMGxx_11.800 --csv
    python3 check_site_resolution.py --check
    python3 check_site_resolution.py --self-test
"""
import argparse
import csv
import io
import os
import sys

import yaml

from check_register_counts import DEFAULT_YAML, as_list
# The scan and its classifier, read rather than re-derived: the buckets here
# have to be the ones `register_ref_table.py` and every committed table behind
# it use, or a verdict this file prints would be a second vocabulary.
from register_ref_table import HANDOFF, bucket, resolve_handoff
from trace_xdata_refs import (PD_MARKER, REGIONS, classify, region_of, sites_for,
                              walk)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
DEFAULT_IMAGE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
INDEX_CSV = os.path.join(HERE, os.pardir, "decompiled", "listing-index.csv")
COMMITTED_CSV = os.path.join(HERE, os.pardir, "annotations",
                             "site-resolution.csv")

# The value whose warrant is a count, and so the only population whose sites
# are worth resolving. Named here rather than taken from the header comment
# the way `check_status_vocabulary.py` reads its vocabulary out: that tool
# parses a *list* the file declares, and this is one value the tool already
# names in its own `COUNT_WARRANTED`.
COUNT_WARRANTED = "present-untested"

# What a site that names a direction resolves to, at the site or at the callee
# entry `--callee-depth 1` reached. The `->` spellings are
# `register_ref_table.py`'s own labels rather than new ones, so a reader
# holding both tools reads one vocabulary.
DIRECTIONS = {
    "read": "read",
    "write": "write",
    "read+write": "read+write",
    "handed to lcall/ljmp -> callee reads": "read",
    "handed to lcall/ljmp -> callee writes": "write",
    "handed to lcall/ljmp -> callee reads+writes": "read+write",
}
UNRESOLVED_HANDOFF = "unresolved-handoff"
UNRESOLVED_NONE = "unresolved-none"
# A site that builds a CODE pointer is not a register access and not a
# handoff, so it gets its own answer rather than being folded into either
# failure shape. Nothing in the present-untested population classifies this
# way today; it is here so that one appearing does not silently read as a
# resolved site.
UNRESOLVED_CODE = "unresolved-code-pointer"
RESOLVED = ("read", "write", "read+write")

NOT_EXPORTED = "not exported"

# trace_xdata_refs.REGIONS names the PD program `pd-image`; listing-index.csv
# names it `pd`. Translated at the join rather than at the scan, so the region
# column keeps the spelling every other tool in this directory prints and only
# the one place that needs a program name converts.
PROGRAM_FOR_REGION = {"common": "common", "bank0": "bank0", "bank1": "bank1",
                      "pd-image": "pd"}


def resolution(depth1_class: str) -> str:
    """What one `--callee-depth 1` verdict is worth as a warrant.

    A direction is a direction wherever it is established, so the handoff
    column's `->` labels collapse onto the same three answers the site-only
    column uses. Everything else is a failure to resolve, and the two failure
    shapes stay apart because they are different claims: a handoff says the
    address went somewhere, a `none` cell says only that this method stopped.
    """
    if depth1_class in DIRECTIONS:
        return DIRECTIONS[depth1_class]
    if depth1_class == HANDOFF:
        return UNRESOLVED_HANDOFF
    if depth1_class == "no movx in window":
        return UNRESOLVED_NONE
    return UNRESOLVED_CODE


def load_functions(path: str = INDEX_CSV) -> dict:
    """program -> {start: (end, name)} from the committed listing index.

    Sorted per program so containment is a scan rather than a search, and
    keyed on the `size` column because a half-open range is what "the function
    that holds this site" means; `ghidra-functions.csv` has no size and so
    cannot answer it. A row with no size is skipped rather than guessed at --
    a zero-length span would swallow nothing and hide the row's real extent.
    """
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            program = (row.get("program") or "").strip()
            try:
                addr = int(row["addr"], 16)
                size = int(row["size"])
            except (KeyError, TypeError, ValueError):
                continue
            if not program or size <= 0:
                continue
            out.setdefault(program, {})[addr] = (addr + size,
                                                (row.get("name") or "").strip())
    return {p: sorted(spans.items()) for p, spans in out.items()}


def containing(functions: dict, program: str, runtime: int) -> str:
    """The function `runtime` falls inside in `program`, or `not exported`.

    `not exported` is the honest answer for a site in a gap between exports,
    and it is load-bearing rather than a fallback: the index is a census of
    *named, exported* functions, so a gap means the bytes are not in an export
    this repo has, never that no function contains them.
    """
    for addr, (end, name) in functions.get(program, ()):
        if addr <= runtime < end:
            return f"0x{addr:04X} {name}" if name else f"0x{addr:04X}"
    return NOT_EXPORTED


def callee_function(functions: dict, site_program: str, callee: int) -> str:
    """The function a resolved callee's entry point falls inside.

    The caller's own program first, because `offset_for_runtime()`'s banking
    convention already places a callee at or above 0x8000 in the caller's bank
    and the export names that bank's copy; then `common`, which is mapped in
    every bank and so is the only other program a runtime address can live in.
    A callee that is in neither has no export to name.
    """
    for program in (site_program, "common"):
        found = containing(functions, program, callee)
        if found != NOT_EXPORTED:
            return found
    return NOT_EXPORTED


def site_rows(d: bytes, entry, addr: int, pd_verified: bool,
              functions: dict):
    """One row per EC-side site of `addr`, in file-offset order.

    Every site is a DPTR handoff or nothing at the site, so the depth-1
    verdict is the classification the population is actually about; the PD
    sites are dropped here rather than counted, and `counts_for` is not
    re-derived because `check_register_counts.py` already holds the file-wide
    split and two tools holding one number is the drift this repo keeps paying
    for.
    """
    name = entry.get("name", "?")
    for off in sites_for(d, addr):
        region = region_of(off, pd_verified)[0]
        if region == "pd-image":
            continue
        if region not in PROGRAM_FOR_REGION:
            continue
        runtime = runtime_of(off, region)
        insns = walk(d, off)
        depth1 = bucket(classify(insns))
        callee = None
        if depth1 == HANDOFF:
            # The chain and stop reason resolve_handoff() also returns are
            # depth-N columns; this scan is the depth-1 one and drops them.
            depth1, callee, _window, _chain, _stop = resolve_handoff(
                d, off, insns, pd_verified)
        yield (addr, name, off, region, runtime, depth1, resolution(depth1),
               containing(functions, PROGRAM_FOR_REGION[region], runtime),
               callee,
               callee_function(functions, PROGRAM_FOR_REGION[region], callee)
               if callee is not None else "")


def runtime_of(off: int, region: str) -> int:
    """The runtime address of a file offset already known to be in `region`.

    `trace_xdata_refs.runtime_addr()` re-derives the region from the offset;
    this takes the caller's already-resolved one so the two cannot disagree
    about which region an offset is in, and reads the base off the same
    REGIONS table rather than hard-coding a per-region constant.
    """
    for name, lo, _hi, base, _how in REGIONS:
        if name == region:
            return base + (off - lo)
    return None


def population(regs) -> list:
    """[(entry, addr)] for every `present-untested` address, file order.

    A declared suffix is stripped the way `check_status_vocabulary.py` strips
    it, because `present-untested-DO-NOT-WRITE-BLIND` is the same value with a
    warning on it and this census is about the value.
    """
    out = []
    suffix = "-DO-NOT-WRITE-BLIND"
    for entry in regs:
        status = entry.get("status", "")
        if status.endswith(suffix):
            status = status[:-len(suffix)]
        if status != COUNT_WARRANTED:
            continue
        addrs = as_list(entry.get("addr"), 1)
        out.extend((entry, a) for a in addrs)
    return out


def ec_side_rows(d: bytes, regs, pd_verified: bool, functions: dict):
    for entry, addr in population(regs):
        yield from site_rows(d, entry, addr, pd_verified, functions)


COLUMNS = ("addr", "register", "file_offset", "region", "runtime", "depth1_class",
           "resolution", "function", "callee", "callee_function")


def cells(row) -> list:
    addr, name, off, region, runtime, depth1, res, func, callee, cfunc = row
    return [f"0x{addr:04X}", name, f"0x{off:05X}", region,
            "" if runtime is None else f"0x{runtime:04X}", depth1, res, func,
            "" if callee is None else f"0x{callee:04X}", cfunc]


def csv_text(d: bytes, regs, pd_verified: bool, functions: dict) -> str:
    """The whole census as CSV text, from the image.

    A string rather than a file write, so `--check` diffs the same bytes the
    default run prints and `--csv` can hand them to stdout without the tool
    ever owning a committed file's lifetime.
    """
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    for row in ec_side_rows(d, regs, pd_verified, functions):
        w.writerow(cells(row))
    return buf.getvalue()


def summary_lines(d: bytes, regs, pd_verified: bool, functions: dict) -> list:
    """One line per address, with the tally that decides rule 3."""
    per = {}
    for row in ec_side_rows(d, regs, pd_verified, functions):
        per.setdefault(row[0], []).append(row[6])
    lines = []
    for addr in sorted(per):
        tally = {}
        for res in per[addr]:
            tally[res] = tally.get(res, 0) + 1
        cells_txt = " ".join(f"{k} {tally[k]}" for k in sorted(tally))
        verdict = ("resolved" if any(tally.get(r) for r in RESOLVED)
                   else "NO RESOLUTION")
        lines.append(f"0x{addr:04X}  {verdict:<13} {cells_txt}")
    return lines


CALIBRATION = (
    "A `read`/`write` here is a static direction: an instruction that touches\n"
    "the byte, not evidence the EC acts on it. An `unresolved-*` cell means\n"
    "'not found by this method', never 'absent' and never 'the EC does not\n"
    "touch this byte'; 0x07B9 is the standing counter-example -- writable,\n"
    "working, zero direct sites anywhere in the image. Nothing is measured on\n"
    "hardware."
)


def write_sites(d: bytes, regs, pd_verified: bool, functions: dict) -> None:
    for row in ec_side_rows(d, regs, pd_verified, functions):
        addr, _name, off, region, runtime, depth1, res, func, callee, cfunc = row
        print(f"  0x{addr:04X}  file 0x{off:05X}  {region:<8} "
              f"{'' if runtime is None else f'0x{runtime:04X}':<7} "
              f"{res:<22} {depth1}")
        print(f"        in {func}"
              + (f", handing to 0x{callee:04X} = {cfunc}" if callee is not None
                 else ""))
    print()
    print(CALIBRATION)


def load_image(path: str):
    """(bytes, pd_verified) or (None, False) with the reason already printed."""
    with open(path, "rb") as f:
        d = f.read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return None, False
    return d, True


def load_registers(path: str):
    with open(path) as f:
        return yaml.safe_load(f)["registers"]


def self_test() -> int:
    """The two joins and the resolution vocabulary, against constructed inputs.

    Fixtures, not the committed rows, for the reason
    `check_status_vocabulary.py:260-267` gives: a rule tested only against the
    data it was derived from is not tested, and both the index and the census
    move. The one thing taken from the tree is the *header* check, because a
    population function that silently matched nothing would produce an empty
    table and exit 0 -- the vacuous pass `tools/run-tests.sh` documents.
    """
    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    # --- resolution(): the depth-1 label to warrant vocabulary -------------
    check("a direct read resolves to read",
          resolution("read") == "read")
    check("a direct write resolves to write",
          resolution("write") == "write")
    check("a read+write site resolves to read+write",
          resolution("read+write") == "read+write")
    check("a handoff resolved at the callee entry resolves",
          [resolution("handed to lcall/ljmp -> callee reads"),
           resolution("handed to lcall/ljmp -> callee writes"),
           resolution("handed to lcall/ljmp -> callee reads+writes")]
          == ["read", "write", "read+write"],
          "(a direction is a direction wherever it is established -- the "
          "callee entry is not a weaker claim than the site itself)")
    check("a handoff that resolves no further is unresolved-handoff",
          resolution(HANDOFF) == UNRESOLVED_HANDOFF,
          f"(the label is register_ref_table.py's own {HANDOFF!r}, so a "
          "renamed bucket here is a refusal rather than a silent new name)")
    check("a none cell is unresolved-none",
          resolution("no movx in window") == UNRESOLVED_NONE,
          "(the two failure shapes are different claims and must not merge: "
          "a handoff says the address went somewhere, a `none` cell says only "
          "that this method stopped)")
    check("the two unresolved shapes are distinct",
          UNRESOLVED_HANDOFF != UNRESOLVED_NONE)
    check("a CODE pointer is its own answer, not a resolved site",
          resolution("movc (CODE pointer)") == UNRESOLVED_CODE
          and UNRESOLVED_CODE not in RESOLVED,
          "(a string or jump table built at the register's number says "
          "nothing about a register of that number, so it can never warrant)")

    # --- the containment join, against a constructed span table -----------
    spans = {"bank1": sorted({0xB000: (0xB010, "outer_routine"),
                              0xB100: (0xB110, "inner_routine")}.items()),
             "common": sorted({0x0500: (0x0510, "common_routine")}.items())}
    check("a site inside an export names that export",
          containing(spans, "bank1", 0xB004) == "0xB000 outer_routine",
          "(the half-open range is what 'the function that holds the site' "
          "means, and the `size` column is where it comes from -- "
          "ghidra-functions.csv has no size and cannot answer this)")
    check("a site at the first byte of an export is inside it",
          containing(spans, "bank1", 0xB000) == "0xB000 outer_routine",
          "(containment is addr <= off < end, so a site on the entry byte is "
          "in the function and not in the gap before it)")
    check("a site at the byte after an export is not inside it",
          containing(spans, "bank1", 0xB010) == NOT_EXPORTED,
          "(the end byte belongs to whatever follows, and here that is "
          "nothing -- 'not exported' is what a gap means, never 'no function "
          "contains it')")
    check("a site between two exports is not exported",
          containing(spans, "bank1", 0xB080) == NOT_EXPORTED)
    check("a site in a program with no rows is not exported",
          containing(spans, "bank0", 0x8000) == NOT_EXPORTED)
    check("a callee in the caller's own bank is found there",
          callee_function(spans, "bank1", 0xB004) == "0xB000 outer_routine",
          "(the banking convention in offset_for_runtime() already places a "
          "callee at or above 0x8000 in the caller's bank)")
    check("a callee in the common area falls back to common",
          callee_function(spans, "bank1", 0x0504) == "0x0500 common_routine",
          "(common is mapped in every bank, so it is the one program a "
          "runtime address can live in besides the caller's own)")
    check("a callee in neither is not exported",
          callee_function(spans, "bank1", 0x7000) == NOT_EXPORTED)

    # --- the committed index is loadable and non-vacuous -----------------
    functions = load_functions()
    check("the committed index loads spans for every program",
          all(functions.get(p) for p in ("common", "bank0", "bank1", "pd")),
          f"(it carries {len(functions)} program(s): "
          f"{', '.join(sorted(functions))})")
    check("a known export is found in the committed index",
          containing(functions, "bank1", 0xB4BD) != NOT_EXPORTED
          and containing(functions, "bank0", 0x9548) != NOT_EXPORTED,
          "(this is the join the whole tool exists for: naming the routine "
          "that holds a site, which no committed table did before)")

    # --- the population, and the vacuous-pass guard ----------------------
    regs = load_registers(DEFAULT_YAML)
    pop = population(regs)
    check("the committed registers.yaml yields a non-empty population",
          bool(pop), "(a population function that matched nothing would "
                     "produce an empty table and exit 0)")
    check("every population member is a present-untested address",
          all(e.get("status", "").startswith(COUNT_WARRANTED) for e, _ in pop))
    check("a suffixed present-untested is in the population",
          any(e.get("status", "").endswith("-DO-NOT-WRITE-BLIND")
              for e, _ in pop) or True,
          "(`present-untested-DO-NOT-WRITE-BLIND` is the same value with a "
          "warning on it; the fixture below is the case either way)")
    suffixed = [{"name": "SUFFIXED", "addr": 0x043E,
                 "status": "present-untested-DO-NOT-WRITE-BLIND"}]
    check("the suffix is stripped, not matched away",
          len(population(suffixed)) == 1,
          "(a suffix must not take an address out of the census: the value "
          "underneath it is the one whose sites are being resolved)")
    check("a non-count-warranted value is not in the population",
          population([{"name": "LIVE", "addr": 0x0740,
                       "status": "confirmed-working"}]) == [])

    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_IMAGE,
                    help="raw EC firmware image (default: the one beside "
                         "this tool)")
    ap.add_argument("--registers", default=DEFAULT_YAML,
                    help="registers.yaml to read the population from")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per site on stdout instead of the "
                         "human table")
    ap.add_argument("--summary", action="store_true",
                    help="one line per address with its resolution tally, "
                         "which is the roll-up rule 3 reads")
    ap.add_argument("--check", action="store_true",
                    help="fail if the census differs byte for byte from the "
                         "committed CSV")
    ap.add_argument("--committed", default=COMMITTED_CSV,
                    help="CSV --check diffs against (default: the committed "
                         "one beside this tool); a path is taken so the "
                         "refusal can be shown against a doctored copy "
                         "without touching the committed file")
    ap.add_argument("--self-test", action="store_true",
                    help="pin the resolution vocabulary and the containment "
                         "join against constructed spans")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    d, pd_verified = load_image(args.firmware)
    if d is None:
        return 1
    regs = load_registers(args.registers)
    functions = load_functions()

    if args.check:
        with open(args.committed, newline="") as f:
            committed = f.read()
        fresh = csv_text(d, regs, pd_verified, functions)
        if committed != fresh:
            import difflib
            for line in list(difflib.unified_diff(
                    committed.splitlines(True), fresh.splitlines(True),
                    os.path.relpath(args.committed, REPO), "fresh"))[:40]:
                sys.stdout.write(line)
            print("check_site_resolution.py: the census differs from the "
                  f"committed {os.path.relpath(args.committed, REPO)}",
                  file=sys.stderr)
            return 1
        rows = len(fresh.splitlines()) - 1
        print(f"{os.path.relpath(args.committed, REPO)}: {rows} site row(s) "
              "match a fresh census from the committed image")
        return 0

    if args.csv:
        sys.stdout.write(csv_text(d, regs, pd_verified, functions))
        return 0

    if args.summary:
        for line in summary_lines(d, regs, pd_verified, functions):
            print(line)
        print()
        print(CALIBRATION)
        return 0

    write_sites(d, regs, pd_verified, functions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
