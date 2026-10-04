#!/usr/bin/env python3
"""Measure bank_attribution.py's closure against the function inventory the tree
already has, and name the two addresses where the walk's framing is visible.

`bank-attribution.md` 4 pins one instance of the walk's framing risk: the
closure reaches the first byte of the `bank0` `0x8038` dispatch table, decodes
`80 54` as `sjmp 0x808E`, and follows it -- "a silent gain rather than as a
stop: the closure acquires an address on the strength of a frame the data handed
it, and nothing in the tables distinguishes that from a real one." That last
clause is the question here. `ec/decompiled/index.csv` is a function inventory
for this same image, cut by Ghidra rather than by this walk, and nothing
compared the two.

**Three predicates, and they do not agree, so all three are printed.**

  inside-a-row        the address falls inside some row's `[addr, addr+size)`
                      span. The population the issue asked for, and the one
                      `nested_frame_census.py` reports as its primary reading.
  at-a-row-entry      the address *is* some row's `addr`. A subset of the above
                      on this tree, and reported apart because a reader asking
                      "is this where a function begins" is asking this and not
                      the other.
  at-an-insn-boundary the address is where some committed `.asm` listing starts
                      an instruction, in the same program. **This is the
                      predicate that answers 4's open question, and it is not
                      the one the issue proposed.** `0x808E` is inside a row's
                      span -- `bank0 0x806C` covers it -- so "no row names it"
                      is false on this tree. But no committed listing starts an
                      instruction at `0x808E`: the listing that holds those
                      bytes draws `0x808C` `lcall 0xbe7e`, three bytes long, and
                      `0x808E` is its last. The inventory distinguishes the two
                      cases, and it does so on boundaries rather than on spans.

**The boundary is printed; the bytes under it are pinned.** Which addresses
the listings start instructions at is a property of `ec/decompiled/*.asm`, a
regenerable export, so `--self-test` asserts nothing about it and a later
annotation redrawing those bytes is not a regression. What it pins instead is
the *reason*: bank0 `0x808C` reads `12 be 7e` in the committed firmware, a
three-byte `lcall 0xbe7e` over `0x808C`-`0x808E`, which no merge can move.

**The two span readings, printed together and neither presented as the
population.** `index.csv`'s `size` column and the committed listing's own span
disagree on this image -- `bank0 0x8054` records 21 and its listing runs
`0x8054`-`0x806B` -- and only the listing is the byte range a reader can check
an address against, which is `second_copy_census.row_span()`'s reason for
reading the `.asm`. Every inside/outside figure below is therefore printed
twice, once per reading, and where they differ the tool says so rather than
picking one.

**A row is not a boundary, and this says so by splitting on `seed_basis`.**
A `call-target` row was put there by a byte scan finding a `74 01` pair, which
is a weaker footing than a hand annotation in exactly the way a byte-derived
walk is a weaker footing than a hand decode. So every figure is printed over
all rows and again over rows excluding `call-target`, and the answer moves.

**What this is not.** Nothing here is a behavioural claim. No image was opened
beyond reading the committed firmware, no register was read back, no capture
was taken, no Ghidra export ran, and no laptop, EC or Windows machine is
involved: every input is a committed file. "No row covers this address" is
**not found by this method**, never "there is no function here" and never
"absent" -- the same calibration rule `registers.yaml` states for a static scan.
The `ret` runs below are statements about bytes and about the linker's stub
table; nothing here is evidence about what the EC executes. The tool **writes
nothing**: there is no CSV mode and no `--apply`, and the self-test asserts
that the module defines no write path.

Usage:
    python3 ec/tools/census_closure_functions.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/census_closure_functions.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import os
import sys

# The closure is bank_attribution.py's, imported rather than reimplemented: a
# second walk of the same bytes is a second set of numbers, and this tool's
# whole claim is about *that* walk's output. Same arrangement
# check_pin_table_by_cited_file.py uses for census_test_line_pins.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bank_attribution as ba
from audit_call_targets import survey
from citation_callers import iter_instructions
from second_copy_census import row_span
from trace_xdata_refs import offset_for_runtime

EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
STUB_TABLE = os.path.join(EC, "annotations", "task-call-table.csv")

# The two maximal `0x22` runs in bank0's window, and the threshold that makes
# them a population. Re-derived in --self-test from the firmware rather than
# carried, because a run is a fact about this image's bytes and a pin here that
# merely re-states this list would hold nothing.
#
# The large one is what the issue filed as "134 consecutive `0x22` bytes" at
# `0xBF55`-`0xBFDA`. The bytes are indeed all `0x22`, but the run is
# `0xBF54`-`0xBFDD`: `0xBFDB` and `0xBFDD` are `0x22` too, and `0xBF54` is the
# `ret` that ends the block before it. The issue's endpoints are three bytes
# early at the top and one byte late at the bottom.
RET_RUNS = ((0xBF1B, 0xBF2B), (0xBF54, 0xBFDD))
RET_BYTE = 0x22
RUN_MIN = 8

# The `0x8038` instance, addressed by what the tool has to reproduce rather than
# by the conclusion. NEGATIVE in bank_attribution.py owns the walk's side of
# this; what is here is the inventory's answer to it.
TABLE_BASE = 0x8038
SJMP_TARGET = 0x808E
HANDLERS = (0x8094, 0x80D7)

# Where the listing holding SJMP_TARGET draws an instruction instead, and the
# three bytes that instruction occupies. Named because it is the *reason*
# SJMP_TARGET is not an instruction start, and it is a fact about the committed
# image rather than about the export: `12` is `lcall` in the 8051 map, so
# `12 be 7e` at 0x808C is `lcall 0xbe7e` spanning 0x808C-0x808E. No merge can
# move it, which is what makes it pinnable where the listing's own instruction
# starts are not -- see the self-test.
LCALL_SITE = 0x808C


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ret_runs(d, bank=0):
    """The maximal runs of RET_BYTE in `bank`'s window of at least RUN_MIN
    bytes, as [(first, last)] ascending.

    Read out of the firmware through `offset_for_runtime()` rather than by
    adding `0x8000`, because a hand-rolled offset is bank 0's mapping and would
    read bank 1 at the wrong place.
    """
    region = f"bank{bank}"
    runs, start = [], None
    for addr in range(ba.BANK_FLOOR, 0x10000):
        if d[offset_for_runtime(addr, region)] == RET_BYTE:
            if start is None:
                start = addr
        elif start is not None:
            runs.append((start, addr - 1))
            start = None
    if start is not None:
        runs.append((start, 0xFFFF))
    return [r for r in runs if r[1] - r[0] + 1 >= RUN_MIN]


def spans_by_program(index_rows):
    """{program: [(first, last, addr, seed_basis)]} over both span readings.

    Two lists per program and both are kept, because they disagree and the
    disagreement is the measurement: `size` is what the exporter recorded and
    the listing span is what a reader can check a byte against.
    """
    by_size, by_listing = collections.defaultdict(list), collections.defaultdict(list)
    for row in index_rows:
        addr = int(row["addr"], 16)
        size = int(row["size"])
        by_size[row["program"]].append((addr, addr + size - 1, addr,
                                        row.get("seed_basis", "?")))
        span = row_span(DECOMPILED, row["program"], addr)
        if span:
            by_listing[row["program"]].append((span[0], span[1], addr,
                                               row.get("seed_basis", "?")))
    for program in by_size:
        by_size[program].sort()
        by_listing[program].sort()
    return {"size": by_size, "listing": by_listing}


def starts_by_program():
    """{program: {addr, ...}} -- where a committed listing starts an
    instruction.

    Read from the `.asm` files with `iter_instructions()`, the tree's one
    listing reader. This is the predicate 4's open question turns on: an address
    can sit well inside a named function's span and still be a byte no listing
    ever decoded an instruction at, which is what the `0x808E` case is.
    """
    out = {}
    for program in sorted(os.listdir(DECOMPILED)):
        here = os.path.join(DECOMPILED, program)
        if not os.path.isdir(here):
            continue
        starts = set()
        for name in sorted(os.listdir(here)):
            if name.endswith(".asm"):
                for parts in iter_instructions(os.path.join(here, name)):
                    starts.add(int(parts[0], 16))
        out[program] = starts
    return out


def covering(spans, addr):
    """The row whose span holds `addr`, or None."""
    for first, last, row_addr, basis in spans:
        if first <= addr <= last:
            return (row_addr, basis, first, last)
    return None


def bank_rows(spans, drop_call_target=False):
    if not drop_call_target:
        return spans
    return [s for s in spans if s[3] != "call-target"]


def partition(reached, spans):
    """(inside, at_entry, outside) over one bank's reached addresses.

    `at_entry` is the addresses that are a row's own `addr`, and `inside`
    counts every address a row's span holds -- so the two overlap by
    construction and the report says so rather than printing a Venn it does not
    mean. `outside` is what is left, which is the population the runs below are
    built from.
    """
    row_addrs = {s[2] for s in spans}
    inside = {a for a in reached if covering(spans, a)}
    at_entry = {a for a in reached if a in row_addrs}
    return inside, at_entry, set(reached) - inside


def runs_of(addrs):
    out = []
    for addr in sorted(addrs):
        if out and addr == out[-1][1]:
            out[-1][1] = addr + 1
        else:
            out.append([addr, addr + 1])
    return out


def single_path(reached):
    """The addresses exactly one path reaches, out of `closure()`'s `reached`.

    `reached[a]` is the **path count**, incremented once per block the address
    appears in per entry point; `who[a]` is the **set** of entry points that
    decode it. They are not the same population and the difference is load
    bearing: an address sitting in two blocks of one entry point carries two
    paths and one entry point, so `len(who[a]) == 1` is the larger set and is
    *not* the `1 path` column `bank-attribution.md` section 2 tabulates. The
    path count is what is used here, and the report says which is which.
    """
    return {a for a, n in reached.items() if n == 1}


def path_census(reached, d, bank):
    """{single, single_ret, single_in_run} for one bank's single-path addresses.

    The composition of the `1 path` column: how much of it is `ret` filler,
    which is what stops section 2's histogram being read as that many separate
    weak claims. `single_in_run` is the part inside the maximal `0x22` runs, and
    the rest is the `ret` byte that ends some other block -- a byte with no run
    around it, which reads as one path for the same reason a run does.
    """
    runs = ret_runs(d, bank)
    one = single_path(reached)
    return {
        "single": len(one),
        "single_ret": sum(1 for a in one
                          if d[offset_for_runtime(a, f"bank{bank}")] == RET_BYTE),
        "single_in_run": sum(1 for a in one
                             if any(f <= a <= l for f, l in runs)),
    }


def census(closures, pairs, spans, starts, stub_targets, d):
    """Every figure this tool reports, as one dict.

    Takes `bank_attribution.closure()`'s own tuples rather than the reached
    counter alone, so the entry-point kinds are read from the walk that produced
    the addresses and not re-derived here. Built in one pass so the report cannot
    print an inside-count from one walk and a runs-count from another.
    """
    reached = {b: closures[b][0] for b in closures}
    out = {}
    for reading in ("size", "listing"):
        per_bank = {}
        for bank in (0, 1):
            program = f"bank{bank}"
            rows = bank_rows(spans[reading].get(program, []))
            rows_no_ct = bank_rows(spans[reading].get(program, []), True)
            inside, at_entry, outside = partition(reached[bank], rows)
            inside_x, _at_entry_x, outside_x = partition(reached[bank], rows_no_ct)
            per_bank[bank] = {
                "reached": len(reached[bank]),
                "inside": len(inside),
                "at_entry": len(at_entry),
                "outside": len(outside),
                "outside_runs": len(runs_of(outside)),
                "inside_x": len(inside_x),
                "outside_x": len(outside_x),
                "outside_runs_x": len(runs_of(outside_x)),
                "boundary": len({a for a in reached[bank] if a in starts[program]}),
            }
        # The `1 path` column of bank-attribution.md section 2, composed. It is
        # printed for both banks even though only bank0 has the `ret` runs, so
        # the zeros beside it are on the page rather than absent from it.
        for bank in (0, 1):
            per_bank[bank].update(path_census(reached[bank], d, bank))
        # Pair targets: the same predicate over the four verdicts, which is the
        # population the issue called "in far better shape than the address
        # count suggests" -- and the one its two exceptions came from.
        per_verdict, exceptions = {}, []
        for verdict in ba.VERDICTS:
            mine = [p for p in pairs if p["verdict"] == verdict]
            rows = {r["region"]: bank_rows(spans[reading].get(r["region"], []))
                    for r in mine}
            named = [p for p in mine
                     if covering(rows[p["region"]], p["target"])]
            per_verdict[verdict] = (len(named), len(mine))
            exceptions += [p for p in mine
                           if covering(rows[p["region"]], p["target"]) is None]
        out[reading] = {"banks": per_bank, "verdicts": per_verdict,
                        "exceptions": exceptions}
    out["stub_targets"] = stub_targets
    return out


def stub_census(d):
    """{run_key: [target, ...]} for the far-call stubs whose target is a byte
    of one of the runs, plus how many stubs there are in all.

    `task-call-table.csv` is the committed record of the 403 stubs
    (`table=far-call-stub`), and it is a *different* derivation from the
    closure's: the linker wrote the table, this walk did not. That is why a
    count resting on it is worth more than a fraction of the walk's output.
    """
    runs = ret_runs(d)
    every, in_a_run = 0, collections.defaultdict(list)
    for row in read_csv(STUB_TABLE):
        if row["table"] != "far-call-stub":
            continue
        every += 1
        target = int(row["target"], 16)
        if row["bank"] != "bank0":
            continue
        if d[offset_for_runtime(target, "bank0")] != RET_BYTE:
            continue
        for key in runs:
            if key[0] <= target <= key[1]:
                in_a_run[key].append(target)
                break
    return every, {k: sorted(v) for k, v in in_a_run.items()}


def print_inventory(got):
    say = print
    say("## the population, under both readings of a row's span")
    say("")
    say("| reading | bank | reached | inside a row | at a row's entry | "
        "outside a row | outside runs |")
    say("|---|---|---:|---:|---:|---:|---:|")
    for reading in ("size", "listing"):
        for bank in (0, 1):
            b = got[reading]["banks"][bank]
            say(f"| `{reading}` | `bank{bank}` | {b['reached']} | {b['inside']} "
                f"| {b['at_entry']} | {b['outside']} | {b['outside_runs']} |")
    say("")
    say("`inside a row` counts every address some row's span holds, and `at a")
    say("row's entry` counts the addresses that *are* a row's own `addr` -- a")
    say("subset of the column beside it, printed apart because it is the one a")
    say("reader asking \"where does a function begin\" wants. `outside a row` is")
    say("the rest, and the runs column groups those into contiguous spans.")
    say("")
    say("**Two readings, because a row's span is two things.** `size` is")
    say("`index.csv`'s own `size` column. `listing` is the committed `.asm` span,")
    say("which is the byte range a reader can check an address against --")
    say("`bank0 0x8054` records 21 and its listing runs 0x8054-0x806B, so the two")
    say("disagree on this image and only one of them is checkable. Both are")
    say("printed and neither is presented as the population.")
    say("")
    moved = [b for b in (0, 1)
             if got["size"]["banks"][b]["inside"] != got["listing"]["banks"][b]["inside"]]
    if moved:
        for b in moved:
            say(f"  `bank{b}`: {got['size']['banks'][b]['inside']} by `size`, "
                f"{got['listing']['banks'][b]['inside']} by listing -- so which "
                f"reading is meant decides the figure.")
        say("")
    say("Every figure above is a count over committed files, and none of them is a")
    say("claim about what the EC executes.")
    say("")


def print_seed_basis(got):
    say = print
    say("## the same figures over rows that are not byte-scan-seeded")
    say("")
    say("| bank | reached | inside (all rows) | inside (no `call-target`) | "
        "outside (all rows) | outside (no `call-target`) |")
    say("|---|---:|---:|---:|---:|---:|")
    for reading in ("size", "listing"):
        for bank in (0, 1):
            b = got[reading]["banks"][bank]
            say(f"| `bank{bank}` (`{reading}`) | {b['reached']} | {b['inside']} "
                f"| {b['inside_x']} | {b['outside']} | {b['outside_x']} |")
    say("")
    say("A `call-target` row was put in the inventory by a byte scan finding a")
    say("`74 01` pair, which is a weaker footing than a hand annotation in exactly")
    say("the way a byte-derived walk is a weaker footing than a hand decode. So")
    say("every figure is printed twice, and a reader who wants the strict reading")
    say("takes the second column rather than assuming it. Neither is the")
    say("population: both are over the same reached addresses.")
    say("")


def print_boundary(got):
    say = print
    say("## at an instruction boundary, which is what section 4's question is")
    say("")
    say("An address can sit well inside a named function's span and still be a byte")
    say("no committed listing ever started an instruction at. That is the third")
    say("predicate, and it is the one that answers the open question section 4 left.")
    say("")
    say("| bank | reached | at an instruction boundary | not at one |")
    say("|---|---:|---:|---:|")
    for bank in (0, 1):
        b = got["size"]["banks"][bank]
        say(f"| `bank{bank}` | {b['reached']} | {b['boundary']} "
            f"| {b['reached'] - b['boundary']} |")
    say("")
    say("`at an instruction boundary` means some committed `.asm` in the same")
    say("program starts an instruction at that address. It is *not* a statement")
    say("that the address is code, and an address outside every listing is")
    say("**not found by this method** rather than absent.")
    say("")


def print_pairs(got):
    say = print
    for reading in ("size", "listing"):
        say(f"## the bucket-B pair targets, by verdict ({reading} reading)")
        say("")
        say("| verdict | inside a row | of |")
        say("|---|---:|---:|")
        for verdict in ba.VERDICTS:
            named, total = got[reading]["verdicts"][verdict]
            say(f"| `{verdict}` | {named} | {total} |")
        say("")
    size_x = sorted((p["region"], p["target"]) for p in got["size"]["exceptions"])
    list_x = sorted((p["region"], p["target"]) for p in got["listing"]["exceptions"])
    say("**The exceptions are named, because the issue asked for that by name.**")
    say("")
    say(f"- under `size`: {len(size_x)} of "
        f"{sum(got['size']['verdicts'][v][1] for v in ba.VERDICTS)} pair targets "
        f"fall outside every row -- "
        + ", ".join(f"`{r}` `0x{t:04X}`" for r, t in size_x))
    say(f"- under `listing`: {len(list_x)} fall outside every listing -- "
        + ", ".join(f"`{r}` `0x{t:04X}`" for r, t in list_x))
    say("")
    say("The two readings do not name the same addresses, which is the reason both")
    say("are printed. Each is **not found by this method**: no row of that")
    say("program's inventory carries a span reaching it. That is a statement about")
    say("`index.csv`, not about the bytes, and it is not \"there is no function")
    say("here\". The nearest rows above and below each are printed in the section")
    say("below so a reader can see what does surround it.")
    say("")


def print_exceptions(got, spans, index_rows):
    say = print
    say("## what surrounds each target that falls outside every row")
    say("")
    rows_by = collections.defaultdict(list)
    for row in index_rows:
        rows_by[row["program"]].append((int(row["addr"], 16), row["name"],
                                        int(row["size"]), row.get("seed_basis", "?")))
    for program in rows_by:
        rows_by[program].sort()
    for reading in ("size", "listing"):
        say(f"### {reading} reading")
        say("")
        say("| pair | target | nearest row below | nearest row above |")
        say("|---|---|---|---|")
        for p in sorted(got[reading]["exceptions"],
                        key=lambda p: (p["region"], p["target"])):
            rows = rows_by[p["region"]]
            below = [r for r in rows if r[0] <= p["target"]]
            above = [r for r in rows if r[0] > p["target"]]
            lo = (f"`0x{below[-1][0]:04X}` `{below[-1][1]}` "
                  f"({below[-1][2]}b, `{below[-1][3]}`)") if below else "none"
            hi = (f"`0x{above[0][0]:04X}` `{above[0][1]}` "
                  f"({above[0][2]}b, `{above[0][3]}`)") if above else "none"
            say(f"| `{p['region']}` `{ba.SHORT[p['verdict']]}` "
                f"| `0x{p['target']:04X}` | {lo} | {hi} |")
        say("")
    say("A gap between two rows is a gap in the *inventory*. The export seeds a")
    say("function at a call target, a hand annotation, or Ghidra's own analysis,")
    say("and a byte in between two of them is a byte nothing seeded. Whether the")
    say("walk is right to reach it is a separate question, and the `ret` runs")
    say("below are the largest such case.")
    say("")


def print_ret_runs(d, reached, entries, who, stub_targets):
    say = print
    runs = ret_runs(d)
    every, in_a_run = stub_targets
    say("## the `0x22` runs, and why the closure is in them at all")
    say("")
    say(f"`0x22` is `ret` in the 8051 map, and a run of them is a block the linker")
    say(f"left as fill. These are the {len(runs)} maximal runs of at least {RUN_MIN}")
    say(f"bytes in bank0's window, measured out of the firmware rather than taken")
    say("from any report:")
    say("")
    say("| run | bytes | reached | unreached | far-call stubs targeting it |")
    say("|---|---:|---:|---:|---:|")
    for first, last in runs:
        reached_here = [a for a in range(first, last + 1) if a in reached]
        missing = [a for a in range(first, last + 1) if a not in reached]
        say(f"| `0x{first:04X}`-`0x{last:04X}` | {last - first + 1} "
            f"| {len(reached_here)} | {len(missing)} "
            f"| {len(in_a_run.get((first, last), ()))} |")
    say("")
    say("**The attribution here is the linker's, not the walk's, and that is the")
    say("substantive correction.** The issue read the large run as a linear block")
    say("walking forward through a linker-reserved gap and credited its bytes to")
    say("the closure. They are not walk-derived frames: every entry point inside")
    say("a run is a *trampoline seed*, which is the linker's own far-call stub and")
    say("the tool's strongest footing. In each run the one byte that is not a seed")
    say("is the run's own first byte, reached from the block before it because")
    say("that block ends in a `ret` there:")
    say("")
    for first, last in runs:
        here = [a for a in range(first, last + 1) if a in reached]
        seeds = sum(1 for a in here if entries.get(a, (None,))[0] == "trampoline")
        rest = [a for a in here if a not in entries]
        say(f"- `0x{first:04X}`-`0x{last:04X}`: {len(here)} reached, {seeds} of "
            f"them trampoline seeds"
            + (", and " + ", ".join(
                f"`0x{a:04X}` is reached from `0x{sorted(who[a])[0]:04X}`"
                for a in rest)
               + " instead, so the walk adds nothing here" if rest else ""))
    say("")
    say(f"Across both runs, {sum(len(v) for v in in_a_run.values())} of the {every}")
    say("far-call stubs in `task-call-table.csv` target a byte of one of them, at a")
    say("stride of 1 in target space -- the linker wrote one stub per byte of fill.")
    say("That is a count of the linker's own table, cross-checkable against a")
    say("committed CSV, and it is worth more than a fraction of the walk's output.")
    say("")
    say("What it does **not** say is why BL51 emits a far-call stub per byte of a")
    say("`ret` run. That is a linker/relocation question, it is open, and this")
    say("tool does not have the vocabulary to answer it.")
    say("")


def print_path_counts(got):
    say = print
    say("## the `1 path` column of section 2, and how much of it is filler")
    say("")
    say("`bank-attribution.md` section 2 tabulates how many independent paths "
        "reach each")
    say("attributed address, and its `1` column is by far the largest. It is "
        "not that many")
    say("separate weak claims, and this is the measurement that says so:")
    say("")
    say("| bank | reached | 1 path | of those, `0x22` bytes | of those, inside a "
        "`0x22` run |")
    say("|---|---:|---:|---:|---:|")
    for bank in (0, 1):
        b = got["size"]["banks"][bank]
        say(f"| `bank{bank}` | {b['reached']} | {b['single']} | {b['single_ret']} "
            f"| {b['single_in_run']} |")
    say("")
    say("A byte inside a run of `ret` reads as one path **by construction**: "
        "there is")
    say("nothing in it for a second path to disagree about, because a `ret` "
        "ends a flow")
    say("cleanly. So the `1` column carries a block of linker fill that is not "
        "a weak")
    say("claim in either direction -- it is neither corroborated nor "
        "contradicted, it is")
    say("filler. The `inside a run` column is the part where that is visible as "
        "a run;")
    say("the rest of the `0x22` column is the single `ret` byte that ends "
        "whichever")
    say("block it terminates, which reads as one path for the same reason.")
    say("")
    say("**`1 path` means the path count, not the entry-point count.** "
        "`closure()`'s")
    say("`reached[addr]` is incremented once per block an address appears in, "
        "while")
    say("`who[addr]` is the *set* of entry points that decode it, so "
        "`len(who[addr]) == 1`")
    say("is a larger population over the same addresses. The column above is "
        "the path")
    say("count, because that is the one section 2's histogram tabulates; a "
        "reader who")
    say("wants the entry-point reading has to say so.")
    say("")
    say("Every figure here is a count over the walk's own output and the "
        "committed image,")
    say("and none of it is a claim about what the EC executes.")
    say("")


def print_index_table(got, index_rows, starts):
    say = print
    rows = {(r["program"], int(r["addr"], 16)): r for r in index_rows}
    say("## section 4's `0x8038` instance, answered from the inventory")
    say("")
    say(f"`0x{TABLE_BASE:04X}` is named `{rows[('bank0', TABLE_BASE)]['name']}`, "
        f"size {rows[('bank0', TABLE_BASE)]['size']}, "
        f"`seed_basis={rows[('bank0', TABLE_BASE)]['seed_basis']}`. The two "
        f"handlers the table's own entry fields point at are "
        + ", ".join(f"`0x{a:04X}` `{rows[('bank0', a)]['name']}`" for a in HANDLERS)
        + ".")
    say("")
    base = starts["bank0"]
    say("| address | inside a row's span | starts an instruction in a listing |")
    say("|---|---|---|")
    for addr in (TABLE_BASE, SJMP_TARGET) + HANDLERS:
        covered = covering(spans_by_program(index_rows)["size"]["bank0"], addr)
        say(f"| `0x{addr:04X}` | "
            + (f"yes, `{rows[('bank0', covered[0])]['name']}`"
               if covered else "no")
            + f" | {'yes' if addr in base else '**no**'} |")
    say("")
    say(f"So the answer to section 4's open question -- \"nothing in the tables")
    say(f"distinguishes that from a real one\" -- is that the tables **do**")
    say(f"distinguish it, and they do so on instruction boundaries rather than on")
    say(f"spans. `0x{SJMP_TARGET:04X}` *is* inside a named row, so \"no row names")
    say(f"it\" would be false on this tree. But no committed listing starts an")
    say(f"instruction there: the listing holding those bytes draws `0x808C`")
    say(f"`lcall 0xbe7e`, three bytes long, and `0x{SJMP_TARGET:04X}` is its last")
    say(f"one. The walk decoded table data as `sjmp 0x{SJMP_TARGET:04X}` and landed")
    say(f"on a byte no listing ever decoded an instruction at.")
    say("")
    say("**`no listing starts an instruction at this address` is not found by this")
    say("method, never \"this is not code\".** It is what the committed export")
    say("decoded, on one decompilation, for this image. **This row is printed and")
    say("not pinned** -- it reads `ec/decompiled/*.asm`, which a later annotation")
    say("regenerates, so a redraw of these bytes is a legitimate change rather")
    say(f"than a regression. What `--self-test` pins is the reason underneath it: bank0")
    say(f"0x{LCALL_SITE:04X} reads `{LCALL_BYTES.hex(' ')}` in the committed firmware,")
    say(f"a three-byte `lcall 0xbe7e` over 0x{LCALL_SITE:04X}-0x{SJMP_TARGET:04X}.")
    say("")


def print_repro():
    say = print
    say("## reproducing every figure above")
    say("")
    say("No Ghidra, no network, no scratch directory, no hardware. Every input is a")
    say("committed file: `ec/decompiled/index.csv`, the `.asm` listings,")
    say("`ec/annotations/task-call-table.csv`, `ec/annotations/ghidra-functions.csv`")
    say("and `ec/firmware/GMxMGxx_11.800`. **No figure here is a total this file")
    say("carries** -- they are whatever this prints on the tree you run it on,")
    say("which is why the write-up quotes them rather than holding them.")
    say("")
    say("```")
    say("python3 ec/tools/census_closure_functions.py "
        "ec/firmware/GMxMGxx_11.800              # this report")
    say("python3 ec/tools/census_closure_functions.py "
        "ec/firmware/GMxMGxx_11.800 --self-test  # the claims and the refusals")
    say("```")
    say("")


def write_runs_csv(reached, spans):  # pragma: no cover - never called
    raise NotImplementedError(
        "census_closure_functions.py writes nothing: there is no CSV mode and "
        "no --apply")


# --- self-test ---------------------------------------------------------------
#
# CLAUDE.md's rule is "assert the claim, not the census", and it is the whole
# constraint here: the inside/at-entry/outside fractions move with both the
# walk's bounds and with inventory growth, and a pin on any of them would fail a
# correct tool over an unrelated merge. What is pinned instead is the claim, and
# the tool's own logic on a fixture inventory.

# The byte pins for the runs, re-derived rather than carried.
RUN_BYTES = {
    0xBF4E: b"\x90\x09\xe3\x74\x1e\xf0",
    0xBFDE: b"\x90\x16\x74\x74\x18\xf0",
}

# The `0x8038` instance, as bytes rather than as a conclusion.
SJMP_BYTES = b"\x80\x54"

# The instruction the listing draws across SJMP_TARGET instead, as bytes read
# out of the firmware. This is the claim behind "0x808E is no instruction
# start", stated over the one input that cannot move: the committed image. The
# boundary itself is a fact about `ec/decompiled/*.asm`, which is a
# regenerable export -- --self-test prints it and deliberately does not assert
# it, because a later annotation redrawing those bytes would legitimately change
# the answer and a red run there would grade a correct tool as broken.
LCALL_BYTES = b"\x12\xbe\x7e"


def self_test(d) -> int:
    bad = 0

    def check(ok, text, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}"
              + ("" if ok or not detail else f"  {detail}"))

    print("census_closure_functions.py --self-test")

    rows, _stubs, tramp = survey(d)
    seeds = ba.seeds_for(tramp)
    reached = {b: ba.closure(d, b, seeds[b]) for b in (0, 1)}
    pairs = ba.pair_rows(rows, reached)
    index_rows = read_csv(INDEX_CSV)
    spans = spans_by_program(index_rows)
    starts = starts_by_program()
    every, stub_targets = stub_census(d)

    # --- the runs, as bytes ---------------------------------------------
    for addr, want in RUN_BYTES.items():
        got = d[offset_for_runtime(addr, "bank0"):offset_for_runtime(addr, "bank0")
                + len(want)]
        check(got == want,
              f"bank0 0x{addr:04X} is `{got.hex(' ')}`"
              + ("" if got == want else f" -- expected `{want.hex(' ')}`"))

    runs = ret_runs(d)
    check(runs == [tuple(r) for r in RET_RUNS],
          f"the maximal `0x{RET_BYTE:02X}` runs of at least {RUN_MIN} bytes in "
          f"bank0's window are "
          + ", ".join(f"0x{a:04X}-0x{b:04X}" for a, b in runs)
          + ("" if runs == [tuple(r) for r in RET_RUNS]
             else f" -- expected {RET_RUNS}"))

    # The claim the issue's endpoints got wrong, asserted on the tree: the run
    # the issue named is inside this one.
    check(d[offset_for_runtime(0xBFDB, "bank0")] == RET_BYTE,
          "bank0 0xBFDB is a `0x22` byte, so the issue's `0xBF55`-`0xBFDA` "
          "endpoints are three bytes early at the top")
    check(d[offset_for_runtime(0xBFDD, "bank0")] == RET_BYTE,
          "and 0xBFDD is one too, so they are a byte late at the bottom")

    # --- the far-call stubs ---------------------------------------------
    check(every == len([r for r in read_csv(STUB_TABLE)
                        if r["table"] == "far-call-stub"]),
          f"the stub table records {every} far-call stubs, and every one is a "
          f"row this census read")
    check(all(d[offset_for_runtime(t, "bank0")] == RET_BYTE
              for targets in stub_targets.values() for t in targets),
          f"every far-call stub targeting a byte of the runs targets a `0x22` "
          f"byte ({sum(len(v) for v in stub_targets.values())} of them) -- "
          f"asserted per row, which is what the count rides on")

    # --- what the closure does inside the runs, which is the reframe -----
    # `closure()` returns a tuple; unpack it once rather than indexing it at
    # every use, so a mis-index reads as itself.
    r0, who0, entries0 = reached[0][:3]
    for first, last in runs:
        here = [a for a in range(first, last + 1) if a in r0]
        seeds_here = [a for a in here if entries0.get(a, (None,))[0] == "trampoline"]
        check(bool(here) and all(r0[a] == 1 for a in here),
              f"every one of the {len(here)} reached bytes of "
              f"0x{first:04X}-0x{last:04X} carries exactly one path")
        check(bool(seeds_here) and all(who0[a] == {a} for a in seeds_here),
              f"and each of the {len(seeds_here)} trampoline seeds in it is its "
              f"own entry point with nothing else reaching it -- the walk adds "
              f"nothing here, which is the correction to the issue's reading")
        rest = [a for a in here if a not in seeds_here]
        check(all(a not in entries0 and who0[a] for a in rest),
              f"the {len(rest)} reached byte(s) that are not seeds ("
              + ", ".join(f"0x{a:04X}" for a in rest)
              + ") are reached from another entry point instead, not entered "
                "as one -- the `ret` that ends the block before the run")

    # --- the `0x8038` instance ------------------------------------------
    base = starts["bank0"]
    off = offset_for_runtime(TABLE_BASE, "bank0")
    check(d[off:off + 2] == SJMP_BYTES,
          f"bank0 0x{TABLE_BASE:04X} is `{d[off:off + 2].hex(' ')}`, the "
          f"address field the section 4 instance is about")
    check(SJMP_TARGET in reached[0][0],
          f"the closure reaches 0x{SJMP_TARGET:04X} on the frame the data gave "
          f"it -- the failure mode is pinned, not dropped")
    # The reason, asserted over the firmware rather than over the export. The
    # listing's own instruction starts are *printed* and not asserted: they are
    # a property of ec/decompiled/*.asm, which a later annotation regenerates,
    # so pinning them would turn a legitimate redraw into a red run. The three
    # bytes below are the same claim stated over the committed image, which no
    # merge can move.
    lcall_off = offset_for_runtime(LCALL_SITE, "bank0")
    check(d[lcall_off:lcall_off + len(LCALL_BYTES)] == LCALL_BYTES,
          f"bank0 0x{LCALL_SITE:04X} is "
          f"`{d[lcall_off:lcall_off + len(LCALL_BYTES)].hex(' ')}` = "
          f"`lcall 0xbe7e`, three bytes over "
          f"0x{LCALL_SITE:04X}-0x{SJMP_TARGET:04X} -- a firmware fact, and the "
          f"reason no listing can start an instruction at "
          f"0x{SJMP_TARGET:04X}")
    # Deliberately NOT asserted: whether a committed listing starts an
    # instruction at 0x{SJMP_TARGET} or at 0x{LCALL_SITE}. Both read
    # ec/decompiled/*.asm, which is a regenerable export, so a later
    # annotation redrawing those bytes would legitimately change the answer --
    # and a red run there would grade a correct tool as broken, which is the
    # failure mode this tool is built to avoid. The report prints both; the
    # firmware bytes above carry the claim instead.
    print(f"       boundary, printed and not pinned: 0x{SJMP_TARGET:04X} "
          f"{'is' if SJMP_TARGET in base else 'is not'} an instruction start in "
          f"a committed listing, 0x{LCALL_SITE:04X} "
          f"{'is' if LCALL_SITE in base else 'is not'} (both read the "
          f"regenerable export)")
    by_addr = {(r["program"], int(r["addr"], 16)): r for r in index_rows}
    row = by_addr[("bank0", TABLE_BASE)]
    check(row["name"] == "index_table_base" and row["seed_basis"] == "annotation"
          and row["annotated"] == "yes",
          f"`index.csv` still names bank0 0x{TABLE_BASE:04X} "
          f"`{row['name']}` with `seed_basis={row['seed_basis']}` and "
          f"`annotated={row['annotated']}` -- a named row, not a census")
    for addr in HANDLERS:
        got = by_addr.get(("bank0", addr))
        check(got is not None and got["name"].startswith("index_case_"),
              f"and the handler 0x{addr:04X} is named too "
              f"({got['name'] if got else 'absent from index.csv'})")

    # The pair verdicts, imported rather than restated: bank_attribution.py's
    # own self-test owns those numbers and this tool adds no opinion about
    # them.
    got = tuple(ba.tally(pairs)[v] for v in ba.VERDICTS)
    check(got == ba.PAIR_PINS["all"],
          f"the {len(pairs)} bucket-B pairs split {got[0]} / {got[1]} / "
          f"{got[2]} / {got[3]}, which is bank_attribution.py's own pin"
          + ("" if got == ba.PAIR_PINS["all"]
             else f" -- expected {ba.PAIR_PINS['all']}"))

    # --- the tool's own logic, on a fixture inventory --------------------
    # A synthetic row set, for the reason nested_frame_census.py gives: every
    # shape below is one the committed tree happens not to have in the
    # arrangement that makes it a test, and a refusal tested against the tree
    # stops being a refusal the day the tree grows a row that needs it.
    fixture = [
        {"program": "bank0", "addr": "1000", "name": "outer", "size": "8",
         "seed_basis": "annotation"},
        {"program": "bank0", "addr": "1008", "name": "start_only", "size": "1",
         "seed_basis": "annotation"},
        # Outside `outer`'s span on purpose: nesting the `call-target` row
        # inside it would leave the strict reading's removal of that row
        # invisible, since the outer row would still cover its bytes.
        {"program": "bank0", "addr": "100C", "name": "inner", "size": "2",
         "seed_basis": "call-target"},
        {"program": "bank0", "addr": "1010", "name": "zero", "size": "0",
         "seed_basis": "annotation"},
    ]
    fspans = spans_by_program(fixture)["size"]["bank0"]
    # A row of size 0 has an empty span, so it covers nothing at all -- not even
    # its own address. The `[addr, addr+size)` half-open form does this for
    # free, and the case is here because it is the one shape that would
    # otherwise read as a row holding one byte.
    check(covering(fspans, 0x1010) is None and covering(fspans, 0x1011) is None,
          "a zero-size row covers nothing, not even its own address")
    # Adjacent rows meet without overlapping: the byte at addr+size is the next
    # row's first byte, and no two rows both hold it.
    check(covering(fspans, 0x1007) is not None
          and covering(fspans, 0x1008) is not None
          and covering(fspans, 0x1009) is None,
          "rows are half-open: 0x1007 is the last byte of the first, 0x1008 "
          "opens the second, and 0x1009 is in neither")
    probe = list(range(0x1000, 0x1013))
    inside, at_entry, outside = partition(probe, fspans)
    check(len(inside) == 11 and at_entry == {0x1000, 0x1008, 0x100C, 0x1010}
          and 0x1010 in outside,
          f"inside/at-entry/outside over the probe set: {len(inside)} inside, "
          f"at-entry {sorted(f'0x{a:04X}' for a in at_entry)}, and the "
          f"zero-size row's address is in at-entry while `outside` still holds "
          f"it -- which is the case that makes the two columns overlap rather "
          f"than sum ({len(outside)} outside)")
    check(at_entry <= inside | {0x1010} and len(at_entry & inside) == 3,
          "so at-entry is inside except for the zero-size row, and the report's "
          "'subset' wording is a property of the committed tree rather than of "
          "the partition")
    no_ct = bank_rows(fspans, True)
    check(covering(no_ct, 0x100C) is None and covering(no_ct, 0x100D) is None
          and covering(fspans, 0x100C) is not None,
          "dropping `call-target` rows removes their span too, so the strict "
          "reading is a genuinely smaller population rather than a relabelling")

    # --- the refusals ---------------------------------------------------
    # Read the parser's own flag list rather than grepping the source for a
    # string: the docstring says "there is no `--apply`", so a text search
    # would fail on the sentence that documents the absence.
    flags = {opt for action in _parser()._actions for opt in action.option_strings}
    check(not any(f in flags for f in ("--apply", "--write", "--csv", "-o",
                                       "--out", "--update")),
          f"the tool's flags are {sorted(flags)} -- no write mode, and no "
          f"third flag that reads like a gate")
    try:
        write_runs_csv(reached[0][0], spans)
        check(False, "the write path refuses rather than writing")
    except NotImplementedError:
        check(True, "the write path refuses rather than writing")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the readings above")
        return 1
    print("self-test passed: the runs re-derived from the firmware, the stub "
          "table's own count, the seeds inside the runs, section 4's instance "
          "pinned as the firmware bytes that explain it (its instruction "
          "boundaries printed, not pinned), and the fixture partition")
    return 0


def _parser():
    """The argument parser, built by a function so the self-test can read its
    own flag list -- which is how "this tool writes nothing" is checked, rather
    than by searching the source for a flag name the docstring also mentions.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image "
                                     "(e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--self-test", action="store_true",
                    help="re-derive the runs from the firmware and assert the "
                         "claims, not the census")
    return ap


def main() -> int:
    args = _parser().parse_args()

    d = open(args.firmware, "rb").read()
    rows, _stubs, tramp = survey(d)
    seeds = ba.seeds_for(tramp)
    reached = {b: ba.closure(d, b, seeds[b]) for b in (0, 1)}
    pairs = ba.pair_rows(rows, reached)
    index_rows = read_csv(INDEX_CSV)
    spans = spans_by_program(index_rows)
    starts = starts_by_program()
    stub_targets = stub_census(d)
    got = census(reached, pairs, spans, starts, stub_targets, d)

    if args.self_test:
        return self_test(d)

    basis = collections.Counter(r.get("seed_basis", "?") for r in index_rows)
    print("census_closure_functions.py -- bank_attribution.py's closure measured "
          "against ec/decompiled/index.csv")
    print()
    print(f"  {len(index_rows)} inventory rows: "
          + ", ".join(f"{n} `{k}`" for k, n in sorted(basis.items())))
    print("  Nothing here is a behavioural claim. No register was read back, no")
    print("  capture was taken, no Ghidra export ran, and no `status:` in")
    print("  ../annotations/registers.yaml moves.")
    print()

    print_inventory(got)
    print_seed_basis(got)
    print_boundary(got)
    print_pairs(got)
    print_exceptions(got, spans, index_rows)
    print_ret_runs(d, reached[0][0], reached[0][2], reached[0][1], stub_targets)
    print_path_counts(got)
    print_index_table(got, index_rows, starts)
    print_repro()
    return 0


if __name__ == "__main__":
    sys.exit(main())