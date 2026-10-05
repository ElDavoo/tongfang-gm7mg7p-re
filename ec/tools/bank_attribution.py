#!/usr/bin/env python3
"""Seed a per-bank reachability closure from the 403 BL51 trampolines, and say
what it does to the 1288 bucket-B pairs the same-bank assumption is carrying.

../annotations/bank-call-audit.md 4 is honest about where its census lands: of
1305 distinct (caller bank, target) pairs, 1288 are "both banks live" -- the
target decodes as plausible code in bank 0 and bank 1 alike, nothing in the
instruction distinguishes them, and "the assumption is what decides these, not
the evidence." The byte-level heuristic (`entry`/`erased`/`other` over
find_banks.py's START_OPCODES) has gone as far as it can go.

There is a second, independent source of bank information in the image that
the audit surfaced and did not exploit: the trampoline block. Each of the 403
entries in common-area 0x1150-0x1ABC is `mov dptr,#target ; ljmp/lcall <stub>`,
and the stub's identity fixes the bank it selects (0x1100 -> bank 0, 0x1114 ->
bank 1), so the *target* of such a trampoline is a banked entry point the
linker itself named. That is the seed set this tool grows a closure from: from
each seed, follow intra-bank control flow inside that bank's own 0x8000-0xFFFF
window, and every address reached is attributed to that bank.

**What is followed, and what stops a flow, stated before any number.**
Followed: fall-through, the PC-relative family, `ajmp`/`acall`, and
`lcall`/`ljmp` whose target stays in the walked bank's own window -- the last of
which becomes a new entry point, which is the whole mechanism and is what lets
the closure reach 0x888C from 0x92F7. Stopped: `ret`/`reti` end a flow; an
`lcall`/`ljmp` onto a trampoline entry or a stub is a bank switch and not an
intra-bank edge (the other bank already has that target as a seed, so following
it would let a closure claim code the linker says is in the other bank).

**Three edge kinds reach past what the bytes alone give, and all three are
`dispatch_edges.py`'s work rather than this file's.** A `jmp @a+dptr` is a
computed target no byte-derived walk can resolve, so `descend()` stops there --
but the walk's arrival at the dispatch is the evidence, and the table the site
reads is what resolves it, so the table's rows are seeded once the site is
inside the closure. An `index-table` edge is the same move for the common-area
`?C?CCASE` reader at 0x7151, which dispatches into banked code this closure
could not otherwise reach. Both seed a *row or target address* and let
`descend()` derive where it goes, so they are control-flow edges the walk
follows rather than targets this file asserts. **A table edge is a table
edge**: the reader pops the return address into DPTR, so the table's address is
never an immediate and the edge is read out of data, never proved by control
flow. This file's standing caveat carries the same warning beside the
numbers.

**The reset vector and the interrupt vectors are seeds now, and what they were
worth is a measured negative.** They are common-area entry points no trampoline
names, so they were the single change most likely to move the residue below.
They are seeded (`vector_handlers()`), and a `callee` below `BANK_FLOOR` is
followed as a same-bank continuation rather than only recorded. Together those
add entry points and **zero banked addresses**, and leave all four verdicts
where they were: the last section measures it against the closure without
them, and
../../docs/findings/common-area-continuation-zero-delta.md is the write-up.

**The edge that would have moved it is one this worklist does not have.** A
common-area routine routes into banked code the way the linker writes a
cross-bank route -- `mov dptr,#target ; ljmp <stub>`, as at common `0x1150`.
`descend()` records the immediate in `arm.code_immediates` and never in
`arm.callees`, so a worklist keyed on callees cannot see that edge, and the stub
it lands on ends in `ret` at `0x1113`, so nothing branches onward to the
DPTR's value either. **The route the linker writes at a trampoline site is
covered by a different edge**, because `seeds_for()` reads the same bytes as a
seed and the closure reaches the target; the last section measures how much of
the census that accounts for, so its DPTR-immediate count is not read as a count
of routes nothing follows. What the worklist lacks is the immediate written
where no trampoline names it. A DPTR immediate at or above `CODE_FLOOR` is a
code-pointer *candidate* rather than a proved entry, so enabling it is a
separate decision with its own calibration and is deliberately not enabled
here.

**The counting, stated precisely because the three headline numbers
double-count.** A bucket-B pair is `(caller bank b, target T)` and the closure
is computed separately per bank, so `T` can be in closure(b), in closure(1-b),
both, or neither. Four verdicts, and the issue's three numbers are drawn from
them without overlap:

  attributed-same-bank    T in closure(b), not in closure(1-b)  -- agreeing
  attributed-cross-bank   T in closure(1-b), not in closure(b)  -- contradicting
  still-ambiguous         in both
  unreached               in neither                           -- the residue

so evidence-decided = agreeing + contradicting, contradictions is the
contradicting part of that, and the residue is `unreached`. All four are
printed, because reporting only the sum would hide the contradictions inside
it.

**Every attribution here is "attributed by this closure", never "proved to be in
bank N",** and the reason is in bank-call-audit.md 2: a flow walk has no
function-boundary recovery, and a 23-of-24 anchored site there sits inside a
data table. This tool's own answer to that is in section 5 and in --self-test --
it reaches one byte of the `bank0` `0x8038` dispatch table, and the mis-decode
it makes of that byte is *followed* into a real routine rather than refused, so
the failure shows up as a false entry in the closure instead of a stop. All
three halves are asserted rather than dropped. Two further limits are inherited
rather than chosen: a seed's bank is a fact about the *stub*, not about the
target's bank at run time, because the closure propagates the trampoline's bank
through edges and never observes which bank is selected; and a walk that runs
out of budget stops, which is a statement about the walk and not about the
code. Banks 2 and 3 are taken as unused on find_banks.py's word and were not
re-derived. Nothing here measures the byte, so no `status:` in
../annotations/registers.yaml moves and nothing here is evidence that the EC
executes any of it. `census_closure_functions.py`, beside this file, measures
the closure against ec/decompiled/index.csv and answers the one-byte failure's
open question; its write-up is
../../docs/findings/closure-vs-function-inventory.md.

Usage:
    python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --pairs-csv > pairs.csv
    python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --regions-csv > regions.csv
    python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import sys

import build_ec_decompile
import dispatch_edges
from audit_call_targets import AUDITED, bucket_of, survey
from disasm8051 import mnemonic
from find_banks import find_stubs
from trace_xdata_refs import PD_MARKER, offset_for_runtime
from walk_branch_arms import CUTS, descend

# Both bank windows are 0x8000-0xFFFF, so a target below this is the common
# area and no closure can attribute it to a bank. It is also the floor
# audit_call_targets.bucket_of() splits on, so the two are the same number for
# the same reason and are named once here.
BANK_FLOOR = 0x8000

# Bounds, per entry point, and both recorded constants rather than flags: a
# count is a budget on work, not a bound on the buffer
# (../../docs/findings/count-bounded-walk-invariant.md), and a bound that only
# exists as a command-line knob is a bound nobody re-derives. They are
# walk_branch_arms.py's own defaults for the 0x0751 arms, chosen so this
# closure's numbers are comparable with that tool's rather than tuned until
# they looked better. Section 7 reports which of them fired and where.
MAX_DEPTH = 16
MAX_INSNS = 500

# The four stub sites ec/annotations/bank-call-audit.md 3 records, re-derived
# through find_stubs() rather than quoted, because the whole chain rests on it.
STUB_SITES = ((0x1100, 0), (0x1114, 1), (0x1128, 2), (0x113C, 3))

# Seed census, as audit_call_targets.py's section 2 records it: 403
# trampolines in all, 350 through the bank-0 stub and 53 through the bank-1
# one, every target at or above 0x8000.
SEEDS = (403, 350, 53)

VERDICT_AGREE = "attributed-same-bank"
VERDICT_CONTRA = "attributed-cross-bank"
VERDICT_AMBIG = "still-ambiguous"
VERDICT_NONE = "unreached"
VERDICTS = (VERDICT_AGREE, VERDICT_CONTRA, VERDICT_AMBIG, VERDICT_NONE)

# How a verdict reads in a table cell, which is not its column value.
SHORT = {VERDICT_AGREE: "agreeing", VERDICT_CONTRA: "contradicting",
         VERDICT_AMBIG: "still ambiguous", VERDICT_NONE: "unreached"}


def seeds_for(tramp):
    """{bank: {target, ...}} from audit_call_targets.trampolines()'s
    `{entry: (bank, target)}`. The seed set is the banked entry points the
    linker itself named, so it is imported rather than re-scanned: a second
    scan of the same shape could only drift from the census it is seeded
    from."""
    out = {}
    for _entry, (bank, target) in tramp.items():
        if target >= BANK_FLOOR:
            out.setdefault(bank, set()).add(target)
    return out


def vector_handlers(d: bytes, tramp):
    """The vector table's common-area code handlers, as `{bank: {addr, ...}}`.

    The other seed source the firmware writes down itself: the reset vector and
    the interrupt vectors, whose targets are entry points no trampoline names.
    Read from `build_ec_decompile.vector_seeds()` rather than by walking the
    table here, for the reason `seeds_for()` gives for the trampolines -- the
    vector layout is walked, not assumed (`discover_vector_table()`, because
    both images in this dump defeat the textbook one), and a second walk of it
    in this file could only drift from the census the decompile was built on.

    Every vector target on this image is common area, so the same set seeds both
    banks and `bank` is the caller spreading one set over two closures. Five of
    the twelve targets are themselves trampoline entries, whose targets are
    already seeds through a different route, so they are left out here; the
    split is asserted in --self-test rather than restated as a list, because the
    assertion is what would catch a change to either half.
    """
    out = {0: set(), 1: set()}
    for addr, basis in build_ec_decompile.vector_seeds(d):
        if basis != "vector-target" or addr >= BANK_FLOOR:
            continue
        if addr in tramp:
            continue
        for bank in out:
            out[bank].add(addr)
    return out


def closure(d: bytes, bank: int, seeds, max_depth: int = MAX_DEPTH,
            max_insns: int = MAX_INSNS, follow_common: bool = True):
    """Everything reachable from `seeds` inside bank `bank`'s own window.

    `walk_branch_arms.descend()` does the block-level work unchanged and is
    used as it stands, with its own `END_*` reason tokens: it is a bounded,
    iterative, no-recursion linear-block descender whose `walked` set covers
    every decoded address rather than every block start, and a closure has no
    reason to keep a second vocabulary. The one difference is above it rather
    than inside it. descend() records an `lcall` as a callee and walks past it,
    and ends the arm at an `ljmp`; a closure has to descend into same-bank call
    targets, because that is the mechanism. So the entry-point worklist lives
    here, above descend(): a same-bank `lcall`/`ljmp` target becomes a new seed
    and gets its own descend(), and an entry point is descended once however
    many paths reach it.

    Returns (reached, who, entries, cuts, common):
      reached  address -> how many distinct entry points decode it
      who      address -> the entry points that decode it
      entries  address -> (kind, the entry point that first reached it)
      cuts     the bound that fired -> the entry points it fired on
      common   common-area call target -> the entry points that call it

    The path count is the cheap robustness signal the write-up reads: a byte one
    accidental path wandered into carries 1, a routine five independent calls
    land in carries 5, and a walk with no function-boundary recovery cannot
    tell the two apart on its own.

    **A `callee < BANK_FLOOR` is followed as a same-bank continuation, and
    nothing at or above BANK_FLOOR is attributed to a bank because of one.**
    `common` keeps recording the call for section 7 either way; what
    `follow_common` decides is whether the callee also becomes an entry point of
    its own, descended in the *calling* bank's window. The `pc >= BANK_FLOOR`
    gate above is what holds the attribution still: a common-area arm can only
    add banked bytes by decoding a banked address, and on this image none of
    them does -- which is why following them moves no verdict in section 4. The
    continuation applies the same convention `offset_for_runtime()` already
    applies to bucket B, so it *extends* that assumption rather than testing
    it, and this file's standing caveat is unchanged.

    Where two banks reach the same common callee the continuation is ambiguous
    by construction -- a common-area routine is shared, so the bytes below
    0x8000 name no bank. `entries` records it as the `kind` `"common"` with
    `frm` the entry point that reached it, which is the bank that would have
    continued, and picks no winner.

    **The worklist is a fixpoint, and it has to be.** A dispatch-table edge is
    only added once its `jmp @a+dptr` is inside the walk, because a table
    nothing reached must not put bytes in the closure. That makes the edge set
    depend on the walk and the walk on the edge set, and on this image the
    dependency is real rather than theoretical: the 0xEFE8 table's first row
    lands on a wrapper that loads DPTR for a *second* table, so seeding the
    first is what makes the second's dispatch site reachable at all. So the
    loop re-asks for edges whenever the worklist drains, and stops when a pass
    adds none.
    """
    region = f"bank{bank}"
    reached = collections.Counter()
    who = collections.defaultdict(set)
    entries = {}
    cuts = collections.defaultdict(set)
    common = collections.defaultdict(set)
    # Explicit list rather than recursion, for descend()'s reason: an arm that
    # re-enters itself through a routine would be a RecursionError here rather
    # than a reported result.
    pending = collections.deque((t, "trampoline", None) for t in sorted(seeds))
    done = set()
    while True:
        while pending:
            start, kind, frm = pending.popleft()
            if start in done:
                continue
            done.add(start)
            entries[start] = (kind, frm)
            arm = descend(d, region, start, None, max_depth, max_insns, True)
            for _start, insns in arm.blocks:
                for pc, _text in insns:
                    # A block can leave the bank window -- a rel8 branch from
                    # within 128 bytes of 0x8000 reaches the common area, and
                    # offset_for_runtime() resolves it there rather than
                    # refusing. The common area is mapped in every bank, so
                    # attributing those bytes to one of them would be a claim
                    # about a region no bank owns.
                    if pc >= BANK_FLOOR:
                        reached[pc] += 1
                        who[pc].add(start)
            for why in arm.ends:
                if why.startswith(CUTS):
                    cuts[why.split(" at ")[0]].add(start)
            for callee in dict.fromkeys(arm.callees):
                if callee < BANK_FLOOR:
                    common[callee].add(start)
                    if follow_common:
                        pending.append((callee, "common", start))
                elif offset_for_runtime(callee, region) is not None:
                    pending.append((callee, "call", start))
        # The worklist has drained, so every dispatch site this walk can reach
        # is now decided and the edges are known. `frm` is the site rather than
        # None: entry_chain() reads a None as a seed the linker wrote down, and
        # a table handler counted among those would be a false claim about the
        # linker in the one section that separates the two.
        fresh = [(e["addr"], e["kind"], e["site"])
                 for e in dispatch_edges.edges(d, region, reached)
                 if e["addr"] not in done]
        if not fresh:
            break
        pending.extend(fresh)
    return reached, who, entries, cuts, common


def entry_chain(entries, addr):
    """The entry-point chain that reaches `addr`, seeds first. Stops at the
    seed, whose `frm` is None.

    A table edge's `frm` is the site that dispatched it, not a seed, so the
    chain for one of those addresses ends at the dispatch: it is a hop from a
    `jmp @a+dptr` or an `lcall 0x7151`, not from a name the linker wrote down.
    That is the whole reason the `frm` is set rather than left None -- a table
    handler must not read as depth-0 in the histogram -- and it is also why the
    histogram reports those two populations apart rather than as one depth
    figure. Splicing the site's own chain back in would make the number larger
    without making it more meaningful: `who` maps an address to *every* entry
    point that decoded it, so there is no one chain to splice, and picking
    among them would report an arbitrary walk's depth as the row's.

    A `common` hop is spliced the same way a table edge is, and for the same
    reason: its `frm` is the entry point that called it, so the chain ends at a
    banked entry point rather than at a seed. It is also the honest place to
    stop, because a common-area address below the bank floor is one every bank
    maps -- continuing past it would attribute shared code to whichever bank
    happened to be walked first.
    """
    out = [addr]
    while out[-1] in entries:
        _kind, frm = entries[out[-1]]
        if frm is None:
            break
        out.append(frm)
    return list(reversed(out))


def runs_of(reached):
    """`reached`'s addresses as [start, end) contiguous runs, in address
    order. The regions table is per run rather than per address because an
    address list of 12,694 items is not a table a reader can hold, and because
    a run is the unit a region map (#50) would consume anyway."""
    out = []
    for addr in sorted(reached):
        if out and addr == out[-1][1]:
            out[-1][1] = addr + 1
        else:
            out.append([addr, addr + 1])
    return out


def pair_rows(rows, closures):
    """One row per distinct bucket-B (caller region, target) pair, with the
    byte classes audit_call_targets.survey() already computed and the closure's
    verdict beside them. Both tables and --pairs-csv come from this one pass, so
    they cannot disagree.

    The byte classes ride along unchanged rather than being re-derived: they are
    the committed buckets, and the question this tool adds is a different one
    about the same population, not a better version of it.
    """
    per = {}
    for r in rows:
        if bucket_of(r["region"], r["target"]) != "B":
            continue
        cell = per.setdefault((r["region"], r["target"]),
                              {"own_bank": r["own_bank"],
                               "other_bank": r["other_bank"], "sites": 0})
        cell["sites"] += 1
    out = []
    for (region, target), cell in sorted(per.items()):
        bank = int(region[-1])
        mine = target in closures[bank][0]
        theirs = target in closures[1 - bank][0]
        verdict = (VERDICT_AGREE if mine and not theirs else
                   VERDICT_CONTRA if theirs and not mine else
                   VERDICT_AMBIG if mine else VERDICT_NONE)
        out.append({"region": region, "target": target, "verdict": verdict,
                    "paths_own": closures[bank][0].get(target, 0),
                    "paths_other": closures[1 - bank][0].get(target, 0), **cell})
    return out


def both_live(pairs):
    """The subset that is the whole point: neither bank holds erased flash at
    the target, so bank-call-audit.md 4's byte classes have nothing to say
    about which bank it is in. The 17 pairs that leaves out are the closure's
    own check and are reported separately rather than folded in."""
    return [p for p in pairs
            if p["own_bank"] != "erased" and p["other_bank"] != "erased"]


def tally(pairs):
    return collections.Counter(p["verdict"] for p in pairs)


def print_seeds(stubs, seeds, handlers) -> None:
    print("## 1. The seeds: what the linker's own trampolines name")
    print()
    for addr, bank in sorted(stubs.items()):
        print(f"  stub 0x{addr:04X} selects bank {bank}: "
              f"{len(seeds.get(bank, ())) - len(handlers.get(bank, ()))} "
              f"seed(s) route through it")
    banked = sum(len(v) - len(handlers.get(b, ()))
                 for b, v in seeds.items())
    print(f"  {banked} seeds in all, every target >= 0x{BANK_FLOOR:04X}, plus "
          f"{len(handlers[0])} common-area handler(s) per bank from the vector "
          f"table")
    print()
    print("A seed is a (target, bank) pair the linker itself wrote down: the")
    print("trampoline's DPTR immediate, and the bank its stub selects. That bank")
    print("is `find_stubs()` decoding the stub body's `setb`/`clr` on")
    print("P1.0-P1.2, not a header field -- the same reading bank-call-audit.md 3")
    print("records, corroborated by make_bank_image.py --self-test. It is the one")
    print("link in the chain here that is not new evidence, and it is not new.")
    print()
    print("The vector table's common-area handlers are seeds too and are counted")
    print("apart, because they are a different kind of claim: a trampoline names")
    print("a target *and* the bank that reaches it, where a vector names a")
    print("target and every bank gets it. The last section measures what they")
    print("are worth.")
    print()


def print_closure(closures, seeds) -> None:
    print("## 2. The closure, per bank")
    print()
    print("An address is attributed to a bank when a walk seeded from that")
    print("bank's own seeds decodes it. `entry points` counts the trampoline")
    print("seeds plus everything the walk derived from them, each descended once;")
    print("`runs` is how many contiguous spans those addresses fall into.")
    print()
    print("| bank | seeds | entry points | call-derived | common-derived | "
          "table-derived | addresses | runs |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for bank in sorted(closures):
        reached, _who, entries, _cuts, _common = closures[bank]
        kinds = collections.Counter(kind for kind, _frm in entries.values())
        print(f"| `bank{bank}` | {len(seeds[bank])} | {len(entries)} "
              f"| {kinds['call']} | {kinds['common']} "
              f"| {sum(n for k, n in kinds.items() if k != 'call' and k != 'common' and k != 'trampoline')} "
              f"| {len(reached)} | {len(runs_of(reached))} |")
    print()
    print("`common-derived` is the entry points reached by following a call")
    print("below 0x8000 as a same-bank continuation. They are counted apart")
    print("because none of them attributes a byte to a bank: the `pc >=")
    print("0x8000` gate in `closure()` holds, so a common-area arm can only add")
    print("addresses above the floor, and on this image none of them decodes one.")
    print("That is the measurement the last section prints, and it is why this")
    print("column and `addresses` move independently.")
    print()
    print("`table-derived` is the split the two dispatch mechanisms need: an")
    print("entry point a `?C?CCASE` table named, and one a `jmp @a+dptr` table")
    print("named. Both are read out of data rather than walked to, so they carry")
    print("this file's standing caveat and an ordinary same-bank call target")
    print("does not -- the regions CSV's `sources` column keeps them apart per")
    print("run.")
    print()
    print("How many distinct entry points decode each attributed address. One")
    print("path is the common case and is not evidence of anything on its own;")
    print("the point of the column is that a byte one accidental path wandered")
    print("into is visibly different from a routine several independent calls")
    print("land in. It is corroboration and not proof, and a high count is not a")
    print("framing check either -- a walk that walked into a table five times")
    print("would score well.")
    print()
    for bank in sorted(closures):
        hist = collections.Counter(closures[bank][0].values())
        line = " / ".join(f"{hist[n]} address(es) on {n} path"
                          f"{'' if n == 1 else 's'}" for n in sorted(hist)[:5])
        rest = sum(v for k, v in hist.items() if k > 5)
        if rest:
            line += f" / {rest} address(es) on 6 or more"
        print(f"  bank{bank}: {line}")
    print()


def print_pairs(pairs) -> None:
    print("## 3. The 1305 bucket-B pairs, by closure verdict")
    print()
    print("First the population as bank-call-audit.md 4 buckets it, so the two")
    print("tables below are over the same 1305 pairs: `own`/`other` are that")
    print("file's byte classes -- `entry`/`erased`/`other` -- carried through")
    print("unchanged, not re-derived.")
    print()
    print("| caller | own / other byte class | pairs |")
    print("|---|---|---:|")
    for region in AUDITED:
        sel = [p for p in pairs if p["region"] == region]
        if not sel:
            continue
        classes = collections.Counter((p["own_bank"], p["other_bank"]) for p in sel)
        first = True
        for (own, other), n in sorted(classes.items(), key=lambda kv: -kv[1]):
            print(f"| {'`' + region + '`' if first else ''} "
                  f"| `{own}` / `{other}` | {n} |")
            first = False
        print(f"| | **{region} total** | **{len(sel)}** |")
    print()
    print("The same 1305 pairs against the closure, which is the part this tool")
    print("adds. `agreeing` means the closure reaches the target in the caller's")
    print("own bank and not in the other; `contradicting` the reverse; `still")
    print("ambiguous` in both, so the closure does not separate them; `unreached`")
    print("in neither. Read `agreeing` and `contradicting` together, as every")
    print("count in bank-call-audit.md is read:")
    print()
    print("| caller | pairs | agreeing | contradicting | still ambiguous | unreached |")
    print("|---|---:|---:|---:|---:|---:|")
    for region in AUDITED:
        sel = [p for p in pairs if p["region"] == region]
        if not sel:
            continue
        t = tally(sel)
        cells = " | ".join(str(t[v]) for v in VERDICTS)
        print(f"| `{region}` | {len(sel)} | {cells} |")
    total = tally(pairs)
    print(f"| **all** | **{len(pairs)}** | **{total[VERDICT_AGREE]}** "
          f"| **{total[VERDICT_CONTRA]}** | **{total[VERDICT_AMBIG]}** "
          f"| **{total[VERDICT_NONE]}** |")
    print()


def print_headline(pairs, closures) -> None:
    amb = both_live(pairs)
    t = tally(amb)
    print("## 4. The three counts, over the 1288 both-banks-live pairs")
    print()
    print("This is the population the same-bank assumption is carrying: the")
    print("target is not erased in either bank, so the byte classes of")
    print("bank-call-audit.md 4 cannot separate the two readings of it. The")
    print("closure is asked the same question about each one.")
    print()
    print(f"  {len(amb)} both-banks-live pairs of the {len(pairs)} bucket-B pairs")
    print(f"    attributed to the caller's own bank only   {t[VERDICT_AGREE]}")
    print(f"    attributed to the other bank only          {t[VERDICT_CONTRA]}")
    print(f"    attributed to both, so not separated       {t[VERDICT_AMBIG]}")
    print(f"    reached by neither: the residue            {t[VERDICT_NONE]}")
    print()
    print(f"  evidence-decided = {t[VERDICT_AGREE]} agreeing + "
          f"{t[VERDICT_CONTRA]} contradicting = "
          f"{t[VERDICT_AGREE] + t[VERDICT_CONTRA]}")
    print(f"  of which contradictions: {t[VERDICT_CONTRA]}")
    print(f"  residue, the closure never reaches them: {t[VERDICT_NONE]}")
    print()
    print("The residue is the honest bottom of all of it. A closure seeded from")
    print("403 entry points does not cover a bank, and the number that says so")
    print("is printed rather than rounded away.")
    print()
    print("**A contradiction is a statement about the closure at least as much as")
    print("about the call.** `T in closure(1-b) and not in closure(b)` says the")
    print("target is reachable from the other bank's seeds and was not reached")
    print("from this bank's -- which is a coverage statement about the second")
    print("half as much as an attribution in the first. Two readings stay open")
    print("for each of them and neither is settled here: the call really is")
    print("cross-bank, or the own-bank walk did not reach T. Nothing here rules")
    print("out a second bank-switch idiom spelled differently, and")
    print("bank-call-audit.md 3's point stands -- BL51's path is indirect, so a")
    print("direct `lcall` between banks would not be one of these.")
    print()
    # Depth from the seed is measured, not characterised: an earlier revision
    # of this section read the sub-class as "a name the linker wrote down, or
    # one hop from one", which holds for 238 of these 632 and mis-describes the
    # 394 further out. bank-attribution.md 7 records call-derived entry points
    # three hops from a linker-written seed (0xF495, 0xF4A4) -- in the 17 pairs
    # outside the 1288, so they show the shape rather than join this set -- and
    # the depth is a real spread. Printed as a histogram, not a two-value gloss,
    # with every number in it derived here.
    own = [p for p in amb
           if p["target"] in closures[int(p["region"][-1])][2]]
    # Split before the histogram, not after it. A table-derived entry point's
    # chain ends at the dispatch that named it rather than at a seed, so
    # counting it in the same depth figure would report "one hop from a name the
    # linker wrote down" for an address whose `frm` is a `jmp @a+dptr`. The two
    # are printed as the two populations they are, which is also what keeps the
    # seed count below a count of linker-written seeds.
    tabled = [p for p in own
              if closures[int(p["region"][-1])][2][p["target"]][0] != "call"
              and closures[int(p["region"][-1])][2][p["target"]][0] != "trampoline"]
    depth = collections.Counter()
    for p in own:
        if p in tabled:
            continue
        bank = int(p["region"][-1])
        depth[len(entry_chain(closures[bank][2], p["target"])) - 1] += 1
    walked = len(own) - len(tabled)
    shallow = depth[0] + depth[1]
    deepest = max(depth, default=0)
    print(f"  {len(own)} of the {len(amb)} have the target as an entry point of the")
    print("  caller's own closure, which is the strongest sub-class. Split by how")
    print("  the entry point was reached, because the two are not the same claim:")
    print()
    print(f"    {walked} reached by control flow -- a seed the linker wrote down")
    print(f"      ({depth[0]}), or a same-bank call target one to {deepest} hops")
    print("      from one. Those hops are measured, each chain walked back to the")
    print("      seed that reaches it:")
    print()
    print("      " + "  ".join(f"{k}: {depth[k]}" for k in sorted(depth)))
    print()
    print(f"      {shallow} at one hop or fewer, {walked - shallow} at two or more")
    if tabled:
        print()
        print(f"    {len(tabled)} reached through a dispatch table, which is a")
        print("      different claim: the target is an entry point because a table")
        print("      named it, read out of data rather than followed as control")
        print("      flow. Each is one hop from the site that named it, and the")
        print("      sites are the `jmp @a+dptr` and `lcall 0x7151` addresses of")
        print("      section 7. They are not counted as seeds and not counted in")
        print("      the depth histogram above.")
    print()


def print_check(pairs) -> None:
    print("## 5. The 17 pairs outside the 1288, as the closure's own check")
    print()
    print("They are not part of the headline, and they are the two populations")
    print("that can catch a broken walk rather than a real cross-bank call. The")
    print("11 own-live/other-erased pairs are the shape that would *falsify* the")
    print("same-bank assumption, so a contradiction among them is evidence the")
    print("walk is wrong and not that a cross-bank call exists. The 6")
    print("both-erased pairs should be attributed to neither bank, since both")
    print("hold erased flash at the target.")
    print()
    print("| caller | target | own / other | sites | closure verdict |")
    print("|---|---|---|---:|---|")
    for p in pairs:
        if p["own_bank"] != "erased" and p["other_bank"] != "erased":
            continue
        print(f"| `{p['region']}` | `0x{p['target']:04X}` | `{p['own_bank']}` / "
              f"`{p['other_bank']}` | {p['sites']} | {SHORT[p['verdict']]} |")
    print()
    live_own = [p for p in pairs
                if p["own_bank"] != "erased" and p["other_bank"] == "erased"]
    both_erased = [p for p in pairs
                   if p["own_bank"] == "erased" and p["other_bank"] == "erased"]
    contra = [p for p in live_own if p["verdict"] == VERDICT_CONTRA]
    reached = [p for p in both_erased if p["verdict"] != VERDICT_NONE]
    print(f"  {len(live_own)} own-live/other-erased pairs, {len(contra)} contradicting")
    print(f"  {len(both_erased)} both-erased pairs, {len(reached)} attributed to a bank at all")
    print()


def print_handoff(d, closures, seeds, tramp, handlers) -> None:
    """The site issue #48 was opened for: bank-1 runtime 0xDFD0's
    `lcall 0x888C`, whose `handoff->write` verdict rests on the same-bank
    assumption plus one hand decode (pd-xdata-overlap.md 2).

    **Correction, 2026-10-04 (issue #1079): the call site is now reached, so
    this section's original "the two halves answer differently" no longer
    holds, and the difference it pointed at is gone.** Seeding the dispatch
    tables brought `0xDEE8` into the closure and the walk ran from there
    through `0xDFD0`, where it had stopped before. Both halves now answer the
    same way, which is a real change to what this file can say about the
    *caller* side -- and it still proves nothing, for the reason the last
    paragraph gives. The wrong reading is left visible in the prose below
    rather than edited away, per CLAUDE.md's calibration rule.
    """
    site, target, bank = 0xDFD0, 0x888C, 1
    print("## 6. The `0x04A6` handoff at bank-1 `0xDFD0`")
    print()
    reached, who, entries, _cuts, _common = closures[bank]
    print(f"  the call site 0x{site:04X} (`lcall 0x{target:04X}`) is "
          f"{'inside' if site in reached else 'OUTSIDE'} bank 1's closure")
    print(f"  the target 0x{target:04X} is {'inside' if target in reached else 'OUTSIDE'} "
          f"bank 1's closure and "
          f"{'inside' if target in closures[0][0] else 'outside'} bank 0's")
    if site in reached:
        callers = sorted(who.get(site, ()))
        print(f"  the call site is reached by entry point(s) "
              f"{', '.join(f'0x{a:04X}' for a in callers)} -- it was not reached "
              f"before the dispatch tables were seeded")
        for a in callers:
            print(f"    0x{a:04X} itself along "
                  f"{' -> '.join(f'0x{x:04X}' for x in entry_chain(entries, a))}")
    if target in reached:
        chain = entry_chain(entries, target)
        print(f"  the target is reached from entry point(s) "
              f"{' -> '.join(f'0x{a:04X}' for a in chain)}")
        for a in chain:
            if a in handlers[bank]:
                print(f"  0x{a:04X} is a vector-table handler, which names a "
                      f"target for every bank rather than naming this one")
                continue
            if a not in seeds[bank]:
                continue
            names = [e for e, (b, t) in sorted(tramp.items()) if t == a and b == bank]
            print(f"  0x{a:04X} is a seed: trampoline(s) "
                  f"{', '.join(f'0x{e:04X}' for e in names)} name it")
    print()
    print("Both halves now answer the same way, and that is what this section")
    print("records. The closure reaches the *target* from a bank-1 seed, so the")
    print("16-bit store pd-xdata-overlap.md 2 decoded by hand is attributed to")
    print("bank 1 by this closure as well as by that hand decode -- a second")
    print("line of evidence, and it agrees. It now also reaches the *call site*,")
    print("which it did not before, so on this file's evidence 0xDFD0 is no")
    print("longer only \"the assumption plus the hand decode\": a walk from a")
    print("bank-1 entry point decodes those bytes.")
    print()
    print("What that does not do is settle which bank is mapped when the CPU")
    print("arrives there. A same-bank and a cross-bank reading of the same three")
    print("call bytes are the same three bytes in the window they are read from,")
    print("so reaching the site says those bytes are reachable from bank 1's")
    print("seeds -- not that bank 1 is selected at run time. That gap is")
    print("unchanged by this section's result, and it is the whole of the")
    print("reason the closure had to be built.")
    print()
    print("Neither half turns \"assumed\" into \"proved\". The walk has no")
    print("function-boundary recovery, so every attribution here is")
    print("\"attributed by this closure\"; and where a half is still negative it")
    print("is a statement about this closure's coverage, never about 0x888C or")
    print("0xDFD0 themselves.")
    print()
    for region in ("bank1", "bank0"):
        off = offset_for_runtime(site, region)
        print(f"  {region} file 0x{off:05X} at runtime 0x{site:04X}: "
              f"`{d[off:off + 3].hex(' ')}` = `{mnemonic(d, off, site)}`")
    # The instruction, not the routine: the `lcall` is three bytes past the
    # `mov dptr,#0x04A6` the site opens with, and it is the `lcall` that names
    # a target. Note what the two listings are and are not -- the same runtime
    # address holds different code in each bank's window, which is ordinary,
    # and it is *why* nothing in the instruction settles the question rather
    # than evidence that it does. Once the caller's bank is fixed the three
    # bytes are fixed too; what they do not name is which window the CPU is in
    # when it arrives, and a same-bank and a cross-bank `lcall` are the same
    # three bytes in the window they are read from.
    call = offset_for_runtime(site + 3, "bank1")
    call0 = offset_for_runtime(site + 3, "bank0")
    print(f"  the `lcall` at 0x{site + 3:04X} reads `{d[call:call + 3].hex(' ')}` in "
          f"bank1's window and `{d[call0:call0 + 3].hex(' ')}` in bank0's --")
    print("  the same runtime address is different code in each bank, which is")
    print("  ordinary and is exactly the ambiguity: the three bytes fix the")
    print("  target only for a caller whose own bank is already known, and they")
    print("  do not say which bank is mapped at run time. That is the whole of")
    print("  the reason the closure had to be built.")
    print()


def print_cuts(d: bytes, closures, seeds) -> None:
    print("## 7. The bounds that fired, and the blind spots that remain")
    print()
    print("A walk that stops is a statement about the walk, so every bound is")
    print("recorded where it fired rather than summarised as a rate, together")
    print("with how much of the closure rests on the walks that stopped.")
    print()
    for bank in sorted(closures):
        reached, who, _entries, cuts, _common = closures[bank]
        if not cuts:
            print(f"  bank{bank}: no bound fired")
            continue
        cut_eps = {e for eps in cuts.values() for e in eps}
        for why, eps in sorted(cuts.items()):
            print(f"  bank{bank}: {len(eps)} entry point(s) stopped at {why}, "
                  f"first at 0x{min(eps):04X}")
        print(f"  bank{bank}: {sum(1 for a in reached if who[a] & cut_eps)} of its "
              f"{len(reached)} addresses are reached by a walk that stopped, "
              f"{sum(1 for a in reached if who[a] and who[a] <= cut_eps)} of them "
              f"by no other")
    print()
    print("The other half of the accounting: calls that leave the bank window. A")
    print("target below 0x8000 is common area, mapped in every bank, so this")
    print("closure records it and follows nothing. The `?C?CCASE` reader at")
    print("0x7151 dispatches all 15 of this image's inline index tables")
    print("(bank-call-audit.md 9, 10; every one of the 15 sites in")
    print("index-table-entries.csv is an `lcall 0x7151`) and is itself common")
    print("area, so the tables are read out of the CSV and seeded as edges")
    print("rather than walked to -- dispatch_edges.py's first job. Eleven of the")
    print("15 sites sit inside bank0's window and four in the common area; only")
    print("the eleven can name a banked target, and the four common-area tables")
    print("are unattributable by construction because they dispatch within the")
    print("region every bank maps and no bank owns.")
    print()
    for bank in sorted(closures):
        common = closures[bank][4]
        callers = {e for eps in common.values() for e in eps}
        top = sorted(common.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:4]
        print(f"  bank{bank}: {len(common)} distinct common-area call targets from "
              f"{len(callers)} entry point(s)"
              + (", most-called "
                 + ", ".join(f"0x{a:04X} x{len(eps)}" for a, eps in top) if top else ""))
    print()
    print("The `jmp @a+dptr` tables are the same move read from the bytes rather")
    print("than from a CSV. `descend()` still stops at the dispatch -- it is a")
    print("computed target and this walk does not resolve one -- but the walk's")
    print("arrival at the site is the evidence, and dispatch_edges.py seeds the")
    print("table's row addresses so descend() derives the targets itself.")
    print()
    for bank in sorted(closures):
        tables = dispatch_edges.dispatch_tables(d, f"bank{bank}")
        idle = dispatch_edges.unreachable(d, f"bank{bank}", closures[bank][0])
        short = dispatch_edges.truncated_tables(d, f"bank{bank}")
        if not tables:
            print(f"  bank{bank}: no `mov dptr`-based dispatch table in this window")
            continue
        print(f"  bank{bank}: {len(tables) - len(idle)} of {len(tables)} "
              f"dispatch table(s) are reached and fire; {len(idle)} are not"
              + (f", first at 0x{min(t['site'] for t in idle):04X}" if idle else ""))
        for t in short:
            print(f"    0x{t['site']:04X}: the `anl` mask admits {t['masked']} "
                  f"indices but the table has {t['rows']} `ljmp` row(s) from "
                  f"0x{t['base']:04X}; the rest are not seeded")
    print()
    print("The tables that do not fire are a coverage statement and not a claim")
    print("that the table is absent -- the enumeration is a shape scan, and")
    print("section 7's last bullet says what that costs.")
    print()
    print("Named blind spots, none of which this tool closes:")
    print()
    print("  * A table edge is a table edge, not control flow the firmware")
    print("    proved. The `?C?CCASE` reader pops the return address into DPTR,")
    print("    so the table's address is never an immediate and every index")
    print("    target here is read out of data. What it adds is reachability")
    print("    under the table's own framing and nothing stronger.")
    print("  * The four common-area index tables dispatch below 0x8000, so no")
    print("    bank owns their handlers and no closure can attribute them.")
    print("  * The reset vector and the interrupt vectors are seeds now, and a")
    print("    call into the common area is followed as a same-bank")
    print("    continuation, so neither is a blind spot by omission any more --")
    print("    but the route out of the common area still is. The last section")
    print("    measures it: a common-area arm names banked code in a DPTR")
    print("    immediate, which is not an edge this walk follows.")
    print("  * A second bank-switch idiom spelled differently would be invisible:")
    print("    this walk treats every same-bank call as intra-bank.")
    print("  * Banks 2 and 3 are taken as unused on find_banks.py's word and were")
    print("    not re-derived.")
    print("  * A call into the common area is not a failure of the walk and is")
    print("    not an attribution: the common area is mapped in every bank, so")
    print("    no bank owns those bytes.")
    print("  * The seeds are byte-derived too, and so are the dispatch shapes:")
    print("    audit_call_targets.trampolines() finds the seeds by shape and")
    print("    dispatch_edges.py finds the tables by shape, so a shape match")
    print("    inside a data table would be indistinguishable here from a real")
    print("    one. That is why a table whose mask admits more indices than it")
    print("    has `ljmp` rows is reported above rather than padded to the mask.")
    print()
    print("Nothing in this file was measured on hardware. No register was read")
    print("back, no capture was taken, and no `status:` in")
    print("../annotations/registers.yaml moves.")
    print()


def print_common(d: bytes, closures, without, handlers, seeds,
                 tramp) -> None:
    """The common area, followed and measured: the answer to whether the
    residue in section 4 is seeds or bounds.

    `without` is the same closure with `follow_common` off and the vector
    handlers not seeded, so every figure here is a difference between two
    populations this file computed rather than a remembered one.

    The three edge kinds stay separable in that comparison without being
    measured against each other here: `without` differs from `closures` in
    both the seeds and the continuation, while the `0x7151` and
    `jmp @a+dptr` edges are present in *both* populations and so cancel out.
    That is what keeps this section from being read as crediting issue #1079's
    tables with work they did not do -- sections 3 and 4 report those edges on
    their own.
    """
    print("## 8. The common area, followed: seeds, bounds, and neither")
    print()
    print("Two changes reach past the bank window, and this section measures")
    print("both against the closure without them. A `callee < BANK_FLOOR` is")
    print("followed as a same-bank continuation, and the vector table's")
    print(f"common-area handlers ({len(handlers[0])} of them) seed each bank.")
    print()
    print("| bank | entry points without | with | addresses without | with |")
    print("|---|---:|---:|---:|---:|")
    for bank in sorted(closures):
        print(f"| `bank{bank}` | {len(without[bank][2])} | {len(closures[bank][2])} "
              f"| {len(without[bank][0])} | {len(closures[bank][0])} |")
    print()
    same = [b for b in sorted(closures)
            if closures[b][0] == without[b][0]]
    if len(same) == len(closures):
        print("The attributed address set is identical in both banks. The walk")
        print("does real work and gains no banked byte: that is the measured")
        print("answer, and it is a negative one.")
    else:
        print("The attributed address set is NOT identical -- this is a real")
        print("change, not the zero delta the write-up reports:")
        for b in sorted(closures):
            if b not in same:
                print(f"  bank{b} gained "
                      f"{len(closures[b][0]) - len(without[b][0])} address(es)")
    print()

    # One survey for both populations: it is the expensive pass over every
    # call site in the image, and the two closures differ only in what they
    # reached, not in what was called.
    rows = survey(d)[0]
    pairs_with = pair_rows(rows, closures)
    pairs_without = pair_rows(rows, without)
    for label, sel in (("all bucket-B pairs", None),
                       ("both-banks-live pairs", both_live)):
        a = tally(sel(pairs_without) if sel else pairs_without)
        b = tally(sel(pairs_with) if sel else pairs_with)
        cells = " / ".join(f"{b[v] - a[v]:+d}" for v in VERDICTS)
        print(f"  {label}: {cells} (agreeing / contradicting / still ambiguous /")
        print("    unreached), as the delta of the four verdicts.")
    print()
    # Each contribution on its own, so the zero is three measured zeros rather
    # than one number a reader has to take on trust. Each row varies exactly one
    # thing against the same `without` baseline: the seeds row turns the
    # continuation off, the continuation row leaves the vector handlers out. The
    # third row is what ships. `follow_common` defaults to True, so a row that
    # did not pass it would silently measure the same closure as the one above
    # and print identical figures under a second label -- which is the failure
    # this argument exists to make impossible rather than to argue about.
    baseline = tally(pair_rows(rows, without))
    seeds_only = {b: closure(d, b, seeds[b] | handlers[b],
                             follow_common=False) for b in (0, 1)}
    cont_only = {b: closure(d, b, seeds[b]) for b in (0, 1)}
    print("Each contribution on its own, against the same \"without\" baseline.")
    print("The entry points each row adds are what tell the rows apart: the banked")
    print("figures are all `+0`, which is the finding, so a row that had quietly")
    print("reused the closure above it would print the same zeros under a second")
    print("label and nothing here would notice.")
    print()
    for label, cl in (("vector-table seeds alone", seeds_only),
                      ("common-area continuation alone", cont_only),
                      ("both (as shipped)", closures)):
        b = tally(pair_rows(rows, cl))
        cells = " / ".join(f"{b[v] - baseline[v]:+d}" for v in VERDICTS)
        print(f"  {label}: {cells} -- adds "
              f"{len(cl[0][2]) - len(without[0][2])} entry point(s) and "
              f"{len(cl[0][0]) - len(without[0][0])} banked address(es) in bank0, "
              f"{len(cl[1][2]) - len(without[1][2])} and "
              f"{len(cl[1][0]) - len(without[1][0])} in bank1")
    print("  The three agree, so the zero is not a sum of two cancellations that")
    print("  would partly survive either change on its own. Two rows printing the")
    print("  same figures would instead mean the two changes are indistinguishable")
    print("  on this image, which is worth seeing rather than hiding behind a")
    print("  label -- so nothing here collapses a row that matches another.")
    print("  `0x7151` and `jmp @a+dptr` edges: present in every population above,")
    print("  so they cancel; sections 3 and 4 report them (issue #1079 took the")
    print("  residue from 398 to 89).")
    print()

    # The reason, which is the useful part: what a common-area arm actually
    # carries. A DPTR immediate at or above the floor is the linker's route out
    # of the common area, and descend() records it as a code immediate rather
    # than a callee, so a worklist keyed on callees cannot see the edge.
    #
    # The count is reported *against the trampoline census*, not on its own,
    # because on this image the census already names almost all of them: the
    # linker writes the route at the trampoline site, so `seeds_for()` has the
    # target as a seed and the closure reaches it. Reading the bare total as
    # "103 unfollowed routes" would be the opposite of what it measures -- it is
    # how often the idiom appears in the arms this walk descended, most of which
    # are covered by a different edge. What is left over is printed beside it.
    named = {target for _bank, target in tramp.values()}
    # Decoded once per bank and reused by the cross-bank paragraph below:
    # `imms_for()` descends every `common`-kind entry point, which is the
    # expensive half of this section, and the two paragraphs ask different
    # questions of one set rather than two.
    banked_imms = {bank: {i for i in imms_for(d, f"bank{bank}", closures[bank])
                          if offset_for_runtime(i, f"bank{bank}") is not None}
                   for bank in sorted(closures)}
    for bank in sorted(closures):
        beyond = banked_imms[bank]
        common_eps = sum(1 for a, (k, _f) in closures[bank][2].items()
                         if a < BANK_FLOOR and k == "common")
        covered = beyond & named
        print(f"  bank{bank}: {common_eps} entry points of kind `common` "
              f"name {len(beyond)} distinct DPTR immediates at or above "
              f"0x{BANK_FLOOR:04X}, of which {len(covered)} are already named "
              f"by a trampoline entry somewhere in the image and "
              f"{len(beyond) - len(covered)} are not")
        for i in sorted(beyond - named):
            print(f"    0x{i:04X} is named by no trampoline entry")
    print()
    print("So the arms carry the idiom in bulk, and the trampoline census already")
    print("reads it at the linker sites -- which is why following the common area")
    print("reaches those targets by a different route rather than not at all. The")
    print("total above is how often the idiom appears in the arms this walk")
    print("descended, **not a count of routes nothing follows**. The edge this")
    print("worklist lacks is the *non*-linker one: an immediate written where no")
    print("trampoline names it.")
    print()
    print("And on this image there is no such code route to miss. The immediate")
    print("above that no trampoline names is an **XDATA** pointer, not a code")
    print("address: common 0x0F75's `mov dptr,#0x9000` at "
          f"0x{XDATA_CLEAR_SITE:04X} bounds")
    print("the `movx @dptr,a` loop that clears XDATA 0x9000-0x97FF, and nothing")
    print("branches to it. So the closure misses no banked route through the")
    print("common area -- not because it sees every edge, but because the routes")
    print("it does not see are already seeds. That is what makes the zero a")
    print("measurement rather than a lucky one, and it is also why the follow-up")
    print("below is sized on the closure as a whole rather than on an example.")
    print()
    # The half of the overlap that is not "the same bank's own trampolines",
    # because it is the reason following the common area could not have moved a
    # byte even if the edge were added. These are cross-bank routes: the
    # immediate names a target the *other* bank seeds. Attributing them to the
    # bank whose common-area code carried the immediate is precisely the
    # same-bank assumption this file already applies, extended one step further
    # than the standing caveat covers -- so it is named here rather than counted
    # as coverage.
    for bank in sorted(closures):
        other = 1 - bank
        cross = (banked_imms[bank] - seeds[bank]) & seeds[other]
        print(f"  bank{bank}: of the immediates above that are not seeds of "
              f"bank{bank}, {len(cross)} name a target `seeds_for()` seeds for "
              f"bank{other} -- a cross-bank route, which following the common "
              f"area could only have attributed to bank{bank} by extending the "
              f"same-bank assumption past what the standing caveat covers")
    print()
    print("`descend()` records a `mov dptr,#imm` in `arm.code_immediates` and")
    print("never in `arm.callees`, so a worklist keyed on callees cannot see")
    print("the edge -- and the stub the route lands on ends in `ret` at")
    print("0x1113, so nothing branches onward to the DPTR's value either. That is")
    print("the shape the linker writes a cross-bank route in:")
    print()
    off = offset_for_runtime(0x1150, "common")
    print(f"  common 0x1150 is `{d[off:off + 6].hex(' ')}`")
    print(f"    = `{mnemonic(d, off, 0x1150)}` ; `{mnemonic(d, off + 3, 0x1150)}`")
    print()
    print("**So the answer to \"seeds or bounds\" is neither.** The residue is")
    print("not waiting on more entry points and not waiting on more budget: the")
    print("worklist has an edge vocabulary, and this edge is not in it. The")
    print("`bounds` figures section 7 prints are the walks that stopped, and the")
    print("four verdicts above do not move when those walks are given more room")
    print("to stop -- so neither the seeds nor the bounds is what is left.")
    print()
    print("Adding the DPTR immediate as an edge is a separate decision with its")
    print("own calibration -- an immediate at or above CODE_FLOOR is a code")
    print("pointer *candidate*, not a proved entry -- so it is not enabled")
    print("here. What it would move is measured in")
    print("../../docs/findings/common-area-continuation-zero-delta.md.")
    print()
    print("**Nothing above is a verdict on the same-bank assumption.** Following")
    print("a common call applies the same convention `offset_for_runtime()`")
    print("already applies to bucket B, so it extends that assumption rather")
    print("than testing it. The standing caveat is unchanged.")
    print()


def bounds_for(eps, cuts):
    """The bounds that fired for the walks whose entry points are `eps`.

    Filtered by the entry points that cover the run, not the union over
    `cuts`. `cuts` is every bound that fired *anywhere* in the bank -- three
    entry points stopped in bank 0, seven in bank 1 -- so a union over its keys
    labels all 7006 bank-0 runs as bound-limited when only 535 are reached by a
    walk that stopped. An empty list is a fact about those walks and not about
    the bank's: it means no walk reaching this run stopped.
    """
    return sorted(why for why, cut_eps in cuts.items() if eps & cut_eps)


def regions_rows(closures):
    """The regions table as dicts, one per attributed contiguous run per bank.

    The entry-point columns are what a later region map (#50) needs and a
    per-address list cannot give it: how many independent paths reach the run,
    how many of those start at a name the linker wrote down, which kinds of
    edge seeded them, and which bounds fired for the walks that covered it.
    `bounds` is bounds_for() over those walks, so a run whose entry points hit
    a bound is a run whose right-hand edge is the walk's decision and not the
    image's, and a run with none is not labelled by a bound that fired
    somewhere else in the bank.

    `sources` is the sorted set of edge kinds among the entry points covering
    the run, and it is the column that keeps the two dispatch mechanisms
    separable downstream. Without it a run reached from a `?C?CCASE` table and
    a run reached only from ordinary calls are the same row, and the first is
    a reachability under a table's own framing while the second is not --
    §8's standing caveat applies to one and not the other. The column was
    added when the tables became edges; the file has no Python consumer (the
    census beside this tool reads `index.csv` and `task-call-table.csv`), so
    a consumer that grew one should read `sources` rather than infer the
    mechanism from `seed_entries`.

    `tramp_seeds` is not a field: --self-test checks `seed_entries` against
    the runs whose `sources` has no `trampoline` in it, which is the pair that
    would break if a future edit let a table edge count as a seed.
    """
    out = []
    for bank in sorted(closures):
        reached, who, entries, cuts, _common = closures[bank]
        for start, end in runs_of(reached):
            addrs = [a for a in range(start, end) if a in reached]
            paths = [reached[a] for a in addrs]
            eps = {e for a in addrs for e in who[a]}
            kinds = {entries[e][0] for e in eps}
            out.append({"bank": f"bank{bank}", "start": f"0x{start:04X}",
                        "end": f"0x{end:04X}", "bytes": len(addrs),
                        "entry_points": len(eps),
                        "seed_entries": sum(1 for e in eps
                                            if entries[e][0] == "trampoline"),
                        "min_paths": min(paths), "max_paths": max(paths),
                        "bounds": " ; ".join(bounds_for(eps, cuts)),
                        "sources": sorted(kinds)})
    return out


REGION_COLUMNS = ("bank", "start", "end", "bytes", "entry_points",
                  "seed_entries", "min_paths", "max_paths", "bounds", "sources")


def write_regions_csv(closures, seeds) -> int:
    """The regions table on stdout, in REGION_COLUMNS' order. The rows come
    from regions_rows() so the file and --self-test cannot disagree."""
    w = csv.writer(sys.stdout)
    w.writerow(REGION_COLUMNS)
    for row in regions_rows(closures):
        w.writerow([(" ".join(row[c]) if c == "sources" else row[c])
                    for c in REGION_COLUMNS])
    return 0


def write_pairs_csv(pairs) -> int:
    w = csv.writer(sys.stdout)
    w.writerow(["caller_bank", "target", "own_bank", "other_bank", "sites",
                "verdict", "paths_own", "paths_other"])
    for p in pairs:
        w.writerow([p["region"], f"0x{p['target']:04X}", p["own_bank"],
                    p["other_bank"], p["sites"], p["verdict"],
                    p["paths_own"], p["paths_other"]])
    return 0


# --- self-test ---------------------------------------------------------------
#
# Every number below is re-derived from ec/firmware/GMxMGxx_11.800 rather than
# carried, and the two hand-decoded pins are the ones a count cannot supply: an
# address the closure must reach and the path that reaches it, and a region it
# must not. Both were read in `r2 -a 8051` against a make_bank_image.py image;
# the transcripts are in ../annotations/bank-attribution.md.

# The hand-decoded positive. bank1 0x888C is the 16-bit store of R1/R2 that
# pd-xdata-overlap.md 2 reads; this closure reaches it from bank1 0x92F7, itself
# named by the trampoline at common 0x1954 (`mov dptr,#0x92f7 ; ljmp 0x1114`),
# by the `lcall 0x888c` at 0x9343. Bank 0's 0x888C is `addc a,r6 ; mov
# dptr,#0x0f5d` and no bank-0 path reaches it, so the same three call bytes
# resolve to two different routines depending on which closure is asked.
POSITIVE = {
    "bank": 1,
    "other_bank": 0,
    "target": 0x888C,
    "chain": (0x92F7, 0x888C),
    "trampoline": 0x1954,
    "trampoline_bytes": b"\x90\x92\xf7\x02\x11\x14",
    "call_site": 0x9343,
    "call_bytes": b"\x12\x88\x8c",
    # disasm8051 pads the mnemonic to four columns, which is why one of these
    # has two spaces after `mov` and the other one.
    "own_mnemonic": "mov  a,r1",
    "other_mnemonic": "addc a,r6",
}

# The hand-decoded negative, at the boundary it actually fell at. bank0 0x8031
# is a real routine (`mov dptr,#0x08e0 ; movx a,@dptr ; lcall 0x7151`, the
# bank-call-audit.md 9 transcript) named by the trampoline at common 0x1A98.
# The `lcall` is followed by the index table inline -- that is the shape 9
# describes, where the callee pops the return address into DPTR -- so a walk
# that continues past a call lands on table data, and 0x8038 is that table's
# first byte (9's layout: 8 entries of three at 0x08038, `0000` at 0x08050, the
# default at 0x08052, the span ending at its own first target 0x08054).
#
# What happens there is NOT a refusal. 0x8038 is the entry-0 address field
# `80 54`, and `80 54` is also a well-formed instruction: descend() decodes it
# as `sjmp 0x808E` and *follows* it, because an unconditional jump is a
# transfer, not a split. 0x808E is a real routine, and this closure credits it
# to the 0x8031 arm alone. So the walk does not stop at the table -- it sails
# through it on a frame the data gave it and acquires a false entry. That is
# the same failure mode 2 records (a walk whose frame came from inside a data
# table), and here it reads as a silent gain rather than as a stop, which is
# the less visible of the two.
#
# 0x8039-0x8053 are unreached for an unrelated reason, and an earlier draft of
# this comment got it wrong: descend() has no fall-through past an
# unconditional jump. `sjmp` ends the linear block and opens a fresh one at the
# target, so the bytes after 0x8038 are never decoded -- not because the
# transfer was declined.
#
# The pin is the boundary as it fell rather than the one the issue expected,
# and it is asserted in all three directions: the one byte reached, the 27 that
# are not, and the target the mis-decode *did* reach. Dropping the check
# because it failed would have been the quiet way to lose all three.
NEGATIVE = {
    "bank": 0,
    "seed": 0x8031,
    "trampoline": 0x1A98,
    "trampoline_bytes": b"\x90\x80\x31\x02\x11\x00",
    "call_site": 0x8035,
    "call_bytes": b"\x12\x71\x51",
    "reached": 0x8038,
    "reached_bytes": b"\x80\x54",
    # The target the mis-decode reaches, asserted because it is the half of
    # the failure mode that looks like a stop and is not one.
    "followed": 0x808E,
    "table": (0x8039, 0x8054),   # half-open: the rest of the 28-byte table
}

# Two of bank1's `jmp @a+dptr` sites, as (the `mov dptr,#table` six bytes above
# the dispatch, the `mov dptr` three bytes). Both were read in `r2 -a 8051`
# against a make_bank_image.py bank-1 image. These two are the ones this file
# pins by hand; the rest are enumerated by dispatch_edges.py from the same
# bytes, and enumerating them is what put them in the closure at all.
DISPATCH = ((0x8A65, b"\x90\x8a\x45"), (0x98DE, b"\x90\x98\xb4"))

# The `0xEFE7` determination, pinned here as well as in dispatch_edges.py
# because the claim this file used to make about it -- that it was one of seven
# blind spots -- is the claim that changed. It is not a byte-scan artefact: the
# `73` at 0xEFE7 is the last byte of the 14-byte routine at 0xEFDA that
# ec/decompiled/index.csv already names `dispatch_index_3x_from_byte_00`, the
# table it dispatches is loaded by `mov dptr,#0xefe8` at 0xEF9A two instructions
# before the `lcall 0xEFDA` at 0xEF9D, and row 14 of that table is the
# `ljmp 0xF040` at 0xF012 that the same inventory independently names
# `table_efe8_row14_ljmp_f040`. The bytes are the pin and the listing is not,
# for the reason the negative below gives: ec/decompiled/*.asm is a regenerable
# export, so a later annotation redrawing these bytes is not a regression.
# dispatch_edges.py --self-test asserts all four halves; what is asserted here
# is that the closure now *reaches through* the table, which is the behaviour
# that changed and the only part a reader of this file cannot re-derive from
# the sibling's output.
EFE7 = {
    "bank": 1,
    "jmp": 0xEFE7,
    "jmp_bytes": b"\x73",
    "routine": (0xEFDA, 14),        # half-open span of the dispatcher itself
    "load": 0xEF9A,
    "load_bytes": b"\x90\xef\xe8",
    "base": 0xEFE8,
    "rows": 16,                     # the dispatcher's own `anl 0x00,#0x0f`
    "row14": 0xF012,
    "row14_bytes": b"\x02\xf0\x40",
}

# The four verdicts over all the bucket-B pairs and over the both-banks-live
# ones. A different dump re-derives them rather than inheriting this image's
# answer, which is the whole point of pinning them.
#
# **The direction of the move is not all one way, and the pins are the only
# place that shows it.** Seeding the dispatch tables took the residue from 398
# to 89 and the agreeing class from 568 to 614, which is the coverage the
# tables were added for. It also took `still ambiguous` from 115 to 510, and
# that is the number to read next to the others: a pair the closure could not
# separate before and cannot separate now is not a pair it has decided, and a
# target that this change newly reaches in *both* banks is exactly what an
# ambiguous verdict means. `contradicting` fell from 207 to 75 for the same
# reason -- some of those targets are now reached on the calling bank's side
# too. So this is more coverage and a weaker separation on the pairs that were
# already ambiguous, not a verdict on the same-bank assumption, and the
# standing-caveat section says so
# beside the numbers rather than in a footnote.
PAIR_PINS = {
    "all": (625, 75, 510, 95),
    "both_live": (614, 75, 510, 89),
    "populations": (1305, 1288),
}

# The 17 pairs outside the 1288: zero contradictions among the 11
# own-live/other-erased pairs, and zero attributions among the 6 both-erased.
# Unchanged by the table edges, and that is the load-bearing part: these are
# the populations that would catch a broken walk rather than a real cross-bank
# call, so their holding is evidence the new edges did not corrupt anything.
CHECK_PINS = (11, 0, 6, 0)

# The regions CSV's `bounds` column, per bank: the runs a stopped walk reaches,
# and the runs in all. `cuts` is every reason that fired *anywhere* in the bank,
# so a consumer -- or a future edit to bounds_for() -- that unions it over a run
# reports every row as bound-limited when far fewer are. Pinned per run because
# the per-address figures §5 prints do not constrain it: a run of 1 byte and a
# run of 40 both count once.
CUT_RUNS = ((535, 8244), (135, 7889))

# The closures' own sizes, reported rather than pinned. They are a property of
# this image's bounds, and a pin here would fail a correct tool over a
# different dump -- the seed census and the four verdicts above are the pins
# that mean something independent of how much a walk happened to cover. The
# figure this file's own docstring and §2 print is derived here, not stored.
CLOSURE_SIZE = (14830, 12258)
ENTRY_POINTS = (1010, 669)

# The reset vector's five `lcall`s, and the shape of the linker's route out of
# the common area that the last section's answer rests on. The reset vector is
# the clearest common-area entry point there is -- it is the one the CPU reaches
# at power-on -- so it is the one the "seeds or bounds" question is asked of.
#
# Both routes are pinned as bytes because the claim is about the worklist's
# *vocabulary*: `0x158E` is `mov dptr,#0xD89F ; ljmp 0x1100`, so the target is a
# DPTR immediate and the only thing branched to is the stub. No callee in the
# walk ever names `0xD89F`.
#
# **What these two are NOT is an example of a target the closure fails to
# reach, and the distinction is asserted rather than left to the reader.**
# `0x158E` and `0x1594` are themselves entries in `trampolines()`, so
# `seeds_for()` already seeds their targets and bank0's closure reaches both
# `0xD89F` and `0xD96C` -- before this change as well as after. The pair is
# pinned to show that the *edge* is missing from the vocabulary, not that the
# *address* is out of reach: the census covers the route at the linker site by a
# different edge, and what a callee-keyed worklist cannot see is an immediate
# written where no trampoline names it. The last section measures that overlap
# rather than leaving a reader to infer it from the byte count.
# docs/findings/reset-vector-dptr-targets.md is about the two targets; what is
# asserted here is the vocabulary claim, which is why following the common area
# moves nothing.
RESET_VECTOR = 0x0070
DPTR_ROUTES = ((0x158E, b"\x90\xd8\x9f\x02\x11\x00", 0xD89F, 0x1100),
               (0x1594, b"\x90\xd9\x6c\x02\x11\x00", 0xD96C, 0x1100))

# The one DPTR immediate at or above `CODE_FLOOR` that a `common`-kind arm
# carries and no trampoline entry names: `0x9000` at `0x0F95`, where it bounds
# the `movx @dptr,a` loop that clears XDATA `0x9000`-`0x97FF`. It is an XDATA
# pointer, not a code route, and it is named here so the leftover it accounts
# for is not read as a missed bank of code -- which is the claim
# `reset-vector-dptr-targets.md` would otherwise be cited for. Pinned as bytes
# for the same reason `DPTR_ROUTES` is: the `mov dptr` is real, and what it
# points at is the part that decides what it means.
XDATA_CLEAR_SITE = 0x0F95
XDATA_CLEAR_IMMEDIATE = 0x9000
XDATA_CLEAR_IMMEDIATES = frozenset({XDATA_CLEAR_IMMEDIATE})


def imms_for(d: bytes, region: str, closure_result):
    """Every DPTR immediate the `common`-kind entry points of one bank's
    closure carry, decoded afresh rather than read out of a cached arm.

    `common-kind entry points`, not "common-area entry points": the set is the
    entry points whose recorded `kind` is `"common"`, which is a smaller set
    than every entry point below `BANK_FLOOR` (a seed or a trampoline entry in
    the common area is one too) and a different set again from the `common`
    call-target map section 7 prints. Naming it precisely is the point: the
    three are adjacent and a bare count reads as interchangeable.
    """
    eps = [a for a, (kind, _frm) in closure_result[2].items()
           if a < BANK_FLOOR and kind == "common"]
    out = set()
    for a in sorted(eps):
        for dp in descend(d, region, a, None, MAX_DEPTH, MAX_INSNS,
                          True).code_immediates:
            out.add(dp)
    return out


def self_test(d: bytes) -> int:
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("bank_attribution.py --self-test")

    stubs = tuple(sorted(find_stubs(d)))
    check(stubs == STUB_SITES,
          "find_stubs() decodes the four BL51 stubs as "
          + ", ".join(f"0x{a:04X}=bank{b}" for a, b in STUB_SITES)
          + ("" if stubs == STUB_SITES else f" -- got {stubs}"))

    rows, _stubs, tramp = survey(d)
    seeds = seeds_for(tramp)
    handlers = vector_handlers(d, tramp)
    census = (len(tramp), len(seeds[0]), len(seeds[1]))
    check(census == SEEDS and all(t >= BANK_FLOOR for _e, (_b, t) in tramp.items()),
          f"{census[0]} trampolines, {census[1]} through the bank-0 stub and "
          f"{census[2]} through the bank-1 one, every target >= "
          f"0x{BANK_FLOOR:04X}"
          + ("" if census == SEEDS else f" -- expected {SEEDS}"))

    # The vector table's split, asserted as the relation between the two rather
    # than as a list of addresses: what it adds is the common-area code
    # handlers, and what it does not add is the targets that are themselves
    # trampoline entries, because their own targets are already seeds through
    # the stub. Both halves are the claim -- "twelve targets, seven seeds" read
    # as a number would not catch a vector table that grew a thirteenth entry.
    vtargets = {addr for addr, basis in build_ec_decompile.vector_seeds(d)
                if basis == "vector-target"}
    common_targets = {a for a in vtargets if a < BANK_FLOOR}
    already = common_targets & set(tramp)
    got_handlers = handlers[0]
    check(handlers[0] == handlers[1] and got_handlers == common_targets - already,
          f"the vector table's {len(vtargets)} targets are all common area, and "
          f"{len(already)} of them are themselves trampoline entries whose "
          f"targets are already seeds, so {len(got_handlers)} common-area "
          f"handler(s) seed each bank"
          + ("" if handlers[0] == handlers[1]
             and got_handlers == common_targets - already
             else f" -- got {sorted(got_handlers)}"))
    check(bool(already) and all(tramp[a][1] >= BANK_FLOOR
                                and tramp[a][1] in seeds[tramp[a][0]]
                                for a in already),
          f"and the {len(already)} targets that are trampoline entries "
          f"({', '.join(f'0x{a:04X}' for a in sorted(already))}) are left out "
          f"because each one's own target is already a banked seed -- "
          f"{', '.join(f'0x{tramp[a][1]:04X}' for a in sorted(already))}"
          if already else "no vector target is a trampoline entry, which is not "
          "the shape this image has")

    closures = {b: closure(d, b, seeds[b] | handlers[b]) for b in (0, 1)}
    # Without either change, so every claim below is a difference between two
    # populations this function computed rather than a remembered one.
    without = {b: closure(d, b, seeds[b], follow_common=False) for b in (0, 1)}

    # The hand-decoded positive, end to end: the trampoline's bytes, the call
    # site's bytes, the path the closure takes, and the other bank's answer.
    bank, other = POSITIVE["bank"], POSITIVE["other_bank"]
    target = POSITIVE["target"]
    tramp_off = offset_for_runtime(POSITIVE["trampoline"], "common")
    tramp_raw = d[tramp_off:tramp_off + len(POSITIVE["trampoline_bytes"])]
    check(tramp_raw == POSITIVE["trampoline_bytes"],
          f"common 0x{POSITIVE['trampoline']:04X} is `{tramp_raw.hex(' ')}` = "
          f"`{mnemonic(d, tramp_off, POSITIVE['trampoline'])}` "
          f"`{mnemonic(d, tramp_off + 3, POSITIVE['trampoline'])}` (expected "
          f"`{POSITIVE['trampoline_bytes'].hex(' ')}`)")
    call_off = offset_for_runtime(POSITIVE["call_site"], f"bank{bank}")
    call_raw = d[call_off:call_off + 3]
    check(call_raw == POSITIVE["call_bytes"],
          f"bank{bank} 0x{POSITIVE['call_site']:04X} is `{call_raw.hex(' ')}` = "
          f"`{mnemonic(d, call_off, POSITIVE['call_site'])}` (expected "
          f"`{POSITIVE['call_bytes'].hex(' ')}`)")
    chain = tuple(entry_chain(closures[bank][2], target))
    check(target in closures[bank][0] and chain == POSITIVE["chain"],
          f"bank{bank}'s closure reaches 0x{target:04X} along "
          f"{' -> '.join(f'0x{a:04X}' for a in chain) or '(it is not an entry point)'}"
          f" (expected {' -> '.join(f'0x{a:04X}' for a in POSITIVE['chain'])})")
    check(target not in closures[other][0],
          f"bank{other}'s closure does not reach 0x{target:04X}, so the same three "
          f"call bytes resolve to two different routines")
    off_own = offset_for_runtime(target, f"bank{bank}")
    off_other = offset_for_runtime(target, f"bank{other}")
    own_text = mnemonic(d, off_own, target)
    other_text = mnemonic(d, off_other, target)
    check(own_text == POSITIVE["own_mnemonic"] and other_text == POSITIVE["other_mnemonic"],
          f"0x{target:04X} is `{own_text}` in bank{bank} and `{other_text}` in "
          f"bank{other} -- the hand decode pd-xdata-overlap.md 2 makes, and the "
          f"one this attribution is corroborating")

    # The hand-decoded negative, at the boundary it actually fell at.
    bank = NEGATIVE["bank"]
    tramp_off = offset_for_runtime(NEGATIVE["trampoline"], "common")
    tramp_raw = d[tramp_off:tramp_off + len(NEGATIVE["trampoline_bytes"])]
    check(tramp_raw == NEGATIVE["trampoline_bytes"] and NEGATIVE["seed"] in seeds[bank],
          f"common 0x{NEGATIVE['trampoline']:04X} is `{tramp_raw.hex(' ')}`, so "
          f"bank{bank} 0x{NEGATIVE['seed']:04X} is a seed"
          + ("" if tramp_raw == NEGATIVE["trampoline_bytes"] and
             NEGATIVE["seed"] in seeds[bank] else " -- expected "
             f"`{NEGATIVE['trampoline_bytes'].hex(' ')}`"))
    call_off = offset_for_runtime(NEGATIVE["call_site"], f"bank{bank}")
    call_raw = d[call_off:call_off + 3]
    reach_off = offset_for_runtime(NEGATIVE["reached"], f"bank{bank}")
    reach_raw = d[reach_off:reach_off + 2]
    check(call_raw == NEGATIVE["call_bytes"] and reach_raw == NEGATIVE["reached_bytes"],
          f"bank{bank} 0x{NEGATIVE['call_site']:04X} is `{call_raw.hex(' ')}` and "
          f"0x{NEGATIVE['reached']:04X} is `{reach_raw.hex(' ')}` -- the `lcall` "
          f"falls into the index table stored inline after it"
          + ("" if call_raw == NEGATIVE["call_bytes"] and
             reach_raw == NEGATIVE["reached_bytes"] else
             f" -- expected `{NEGATIVE['call_bytes'].hex(' ')}` and "
             f"`{NEGATIVE['reached_bytes'].hex(' ')}`"))
    check(NEGATIVE["reached"] in closures[bank][0],
          f"bank{bank}'s closure reaches 0x{NEGATIVE['reached']:04X}: the walk "
          f"continues past the `lcall` and lands on the table, which is the known "
          f"failure mode and is pinned here rather than dropped")
    # The half of the failure mode that reads as a stop and is not one. `80 54`
    # is a well-formed `sjmp`, so the walk follows it out of the table and into
    # a real routine. Asserting the *arrival* is what keeps the corrected
    # mechanism from decaying back into "the transfer was declined": the 27
    # bytes below are unreached because descend() has no fall-through past an
    # unconditional jump, which is a different fact from not following one.
    check(NEGATIVE["followed"] in closures[bank][0],
          f"and follows the `sjmp` off it to 0x{NEGATIVE['followed']:04X}, which "
          f"is a real routine -- the walk does not stop at the table, it leaves "
          f"it on a frame the data gave it"
          + ("" if NEGATIVE["followed"] in closures[bank][0] else " -- not reached"))
    inside = [a for a in range(*NEGATIVE["table"]) if a in closures[bank][0]]
    check(not inside,
          f"while not one of the {NEGATIVE['table'][1] - NEGATIVE['table'][0]} "
          f"table bytes after it, 0x{NEGATIVE['table'][0]:04X}-"
          f"0x{NEGATIVE['table'][1] - 1:04X} -- descend() has no fall-through "
          f"past an unconditional jump, so they are never decoded"
          + ("" if not inside else " -- reached "
             + ", ".join(f"0x{a:04X}" for a in inside[:8])))

    # The dispatch shape section 7 characterises rather than merely lists.
    for addr, raw in DISPATCH:
        off = offset_for_runtime(addr, "bank1")
        got_raw = d[off:off + 3]
        jmp_off = offset_for_runtime(addr + 6, "bank1")
        ok = got_raw == raw and d[jmp_off] == 0x73
        check(ok,
              f"bank1 0x{addr:04X} is `{got_raw.hex(' ')}` "
              f"(`{mnemonic(d, off, addr)}`) and 0x{addr + 6:04X} is "
              f"`{d[jmp_off]:02x}` = `{mnemonic(d, jmp_off, addr + 6)}`"
              + ("" if ok else f" -- expected `{raw.hex(' ')}` and 0x73"))

    # The 0xEFE7 determination, at the point the change is actually about: this
    # closure used to stop there and now walks through the table. dispatch_edges
    # .py --self-test pins the bytes that make 0xEFE7 a dispatch; what is
    # asserted here is the consequence -- the table's rows are entry points and
    # the `ljmp` behind them is followed -- so a future edit that drops the
    # table edges fails here rather than silently reverting the finding.
    reached1, entries1 = closures[EFE7["bank"]][0], closures[EFE7["bank"]][2]
    table_rows = [EFE7["base"] + 3 * i for i in range(EFE7["rows"])]
    seeded = [a for a in table_rows if entries1.get(a, ("",))[0].startswith("dispatch")]
    check(len(seeded) == len(table_rows) and all(a in reached1 for a in table_rows),
          f"bank1 reaches all {len(table_rows)} rows of the 0x{EFE7['base']:04X} "
          f"table, each seeded as a `dispatch-*` entry point with `frm` the "
          f"0xEFE7 site that named it -- so the site is dispatched through "
          f"rather than a blind spot"
          + ("" if len(seeded) == len(table_rows) else
             f" -- only {len(seeded)} seeded"))
    check(entries1.get(EFE7["row14"]) == ("dispatch-shared", EFE7["load"] + 3),
          f"and row 14 is the `ljmp 0xF040` the committed inventory already "
          f"names `table_efe8_row14_ljmp_f040`, reached by descend() following "
          f"the row rather than by this file asserting a target"
          + ("" if entries1.get(EFE7["row14"]) == ("dispatch-shared", EFE7["load"] + 3)
             else f" -- got {entries1.get(EFE7['row14'])}"))
    # And the handler the walk derives from it, which is the part no table
    # lookup in this file could have asserted.
    check(0xF040 in reached1,
          f"so 0xF040 -- the ljmp target behind row 14 -- is inside bank1's "
          f"closure, reached by the walk following the row's `ljmp`"
          + ("" if 0xF040 in reached1 else " -- not reached"))

    pairs = pair_rows(rows, closures)
    got = tuple(tally(pairs)[v] for v in VERDICTS)
    check(got == PAIR_PINS["all"],
          f"the {len(pairs)} bucket-B pairs split {got[0]} / {got[1]} / {got[2]} /"
          f" {got[3]} (agreeing / contradicting / still ambiguous / unreached)"
          + ("" if got == PAIR_PINS["all"] else f" -- expected {PAIR_PINS['all']}"))
    amb = both_live(pairs)
    got = tuple(tally(amb)[v] for v in VERDICTS)
    check(got == PAIR_PINS["both_live"],
          f"the {len(amb)} both-banks-live pairs split {got[0]} / {got[1]} / "
          f"{got[2]} / {got[3]} -- so evidence-decided {got[0] + got[1]}, "
          f"contradictions {got[1]}, residue {got[3]}"
          + ("" if got == PAIR_PINS["both_live"]
             else f" -- expected {PAIR_PINS['both_live']}"))
    check((len(pairs), len(amb)) == PAIR_PINS["populations"],
          f"and the two populations are the {PAIR_PINS['populations'][0]} and "
          f"{PAIR_PINS['populations'][1]} bank-call-audit.md 4 records")

    # --- the common area: a measured negative, and the edges behind it -----
    #
    # The four verdicts above are unchanged by following the common area and
    # seeding the vector handlers, and that is the finding rather than a
    # disappointment: it is what moves "the residue is seeds or bounds" off
    # both horns. So the identity is asserted directly, against the closure
    # computed without either change, and asserted as the *address set* rather
    # than as the four tallies -- the tallies would also agree if a byte had
    # moved between two verdicts.
    for b in (0, 1):
        grew = len(closures[b][2]) - len(without[b][2])
        check(closures[b][0] == without[b][0],
              f"bank{b}: seeding the {len(handlers[b])} vector handler(s) and "
              f"following the common area adds {grew} entry point(s) and "
              f"{len(closures[b][0]) - len(without[b][0])} banked address(es) -- "
              f"the attributed set is identical, which is the measured negative"
              + ("" if closures[b][0] == without[b][0] else " -- IT MOVED"))
    check(all(tally(pair_rows(rows, closures))[v]
              == tally(pair_rows(rows, without))[v] for v in VERDICTS),
          "and the four verdicts are identical over both populations, so none of "
          "the residue moved either")
    check(all(closures[b][0][a] == without[b][0][a]
              for b in (0, 1) for a in closures[b][0]),
          "including the per-address path counts, so no byte was reached more "
          "often than before -- following the common area added entry points "
          "and no path")

    # The worklist followed them, which is what makes the zero above a
    # measurement rather than a no-op: a change that silently did nothing would
    # produce the same identity.
    followed = {a for b in (0, 1) for a, (k, _f) in closures[b][2].items()
                if k == "common"}
    check(followed and all(a < BANK_FLOOR for a in followed),
          f"the walk does descend common-area callees: {len(followed)} distinct "
          f"address(es) are `common`-kind entry points, every one of them below "
          f"0x{BANK_FLOOR:04X}"
          + ("" if followed else " -- it followed none, so the identity above "
             "proves nothing"))
    # Each records the entry point that reached it, so the shared-routine
    # ambiguity is written down rather than resolved by picking a bank.
    check(all(closures[b][2][a][1] is not None
              for b in (0, 1) for a, (k, _f) in closures[b][2].items()
              if k == "common"),
          "and each one's `frm` is the entry point that reached it rather than "
          "None, so a common callee two banks reach is recorded as ambiguous by "
          "construction instead of attributed to whichever bank was walked "
          "first -- entry_chain() stops there rather than splicing past a "
          "region no bank owns")

    # The edge that is missing, pinned as bytes and as an absence. This is the
    # whole of the last section's answer, so it is asserted rather than
    # described:
    # the target is a DPTR immediate and never a callee, which is precisely why
    # a callee-keyed worklist cannot reach it.
    for site, raw, target, stub in DPTR_ROUTES:
        site_off = offset_for_runtime(site, "common")
        got_raw = d[site_off:site_off + len(raw)]
        arm = descend(d, "bank0", site, None, MAX_DEPTH, MAX_INSNS, True)
        check(got_raw == raw and target in arm.code_immediates
              and target not in arm.callees and stub in arm.callees,
              f"common 0x{site:04X} is `{got_raw.hex(' ')}`, so 0x{target:04X} "
              f"is in its `code_immediates` and not in its `callees` -- the "
              f"linker's route out of the common area is an edge this "
              f"worklist's vocabulary does not have"
              + ("" if got_raw == raw and target in arm.code_immediates
                 and target not in arm.callees and stub in arm.callees
                 else f" -- immediates {sorted(set(arm.code_immediates))}, "
                      f"callees {[hex(c) for c in dict.fromkeys(arm.callees)]}"))
    reset = descend(d, "bank0", RESET_VECTOR, None, MAX_DEPTH, MAX_INSNS, True)
    reset_callees = dict.fromkeys(reset.callees)
    check(all(site in reset_callees for site, _r, _t, _s in DPTR_ROUTES),
          f"and the reset vector at 0x{RESET_VECTOR:04X} reaches both of those "
          f"routes by `lcall`, so the routes are reachable from the common "
          f"area and the walk descends them")
    # ...and the closure reaches both targets anyway, which is the half that
    # stops the pair above from being read as a counterexample to itself. Both
    # route sites are trampoline entries, so `seeds_for()` already seeds their
    # targets. Asserting it here is what keeps the claim honest: the missing
    # thing is the *edge*, not the address.
    check(all(site in tramp for site, _r, _t, _s in DPTR_ROUTES)
          and all(tramp[site][1] in seeds[tramp[site][0]]
                  for site, _r, _t, _s in DPTR_ROUTES),
          "and the closure reaches both targets regardless, because the route "
          "sites are themselves trampoline entries whose targets `seeds_for()` "
          "already seeds -- so the pair above shows the edge is missing from "
          "the vocabulary, NOT that these addresses are out of reach")
    # The census overlap, measured: on this image nearly every banked DPTR
    # immediate in a common-area arm is already named by a trampoline entry, so
    # the bare count is a frequency of the idiom and not a count of unfollowed
    # routes. Printed rather than pinned, because the numbers move with the
    # walk's bounds; what is asserted is that the overlap is the large majority,
    # which is what makes the distinction worth stating.
    named_targets = {t for _b, t in tramp.values()}
    for bank in (0, 1):
        common_eps = [a for a, (k, _f) in closures[bank][2].items()
                      if a < BANK_FLOOR and k == "common"]
        imms = set()
        for a in sorted(common_eps):
            for dp in descend(d, f"bank{bank}", a, None, MAX_DEPTH,
                              MAX_INSNS, True).code_immediates:
                imms.add(dp)
        beyond = {i for i in imms
                  if offset_for_runtime(i, f"bank{bank}") is not None}
        covered = beyond & named_targets
        check(beyond and len(covered) >= len(beyond) // 2,
              f"bank{bank}: the {len(common_eps)} entry points of kind `common` "
              f"name {len(beyond)} distinct banked DPTR immediates, of which "
              f"{len(covered)} the trampoline census already names -- so the "
              f"count is how often the idiom appears in the arms this walk "
              f"descended, not a count of routes nothing follows"
              + ("" if beyond and len(covered) >= len(beyond) // 2
                 else " -- the census no longer covers most of them, so the "
                      "wording in the write-up and the last section needs "
                      "re-measuring"))
    # What is left over, and why it is not the worked example the idiom wants.
    # The one immediate no trampoline names on this image is `0x9000` in the
    # XDATA-clearing routine at `0x0F75` -- `mov dptr,#0x9000` bounds a
    # `movx @dptr,a` loop, it does not route to code. So there is *no* banked
    # code route in the arms this walk reached that the census misses, which
    # is the real reason the delta is zero and not an artefact of one. Asserted
    # so the follow-up is sized on the whole closure rather than on an example
    # that does not exist: a DPTR immediate at or above CODE_FLOOR is a
    # code-pointer candidate, not a proved entry, and this one is neither.
    for bank in (0, 1):
        leftovers = {i for i in imms_for(d, f"bank{bank}", closures[bank])
                     if offset_for_runtime(i, f"bank{bank}") is not None
                     } - named_targets
        check(all(i in XDATA_CLEAR_IMMEDIATES for i in leftovers),
              f"bank{bank}: every DPTR immediate in a `common`-kind arm that no "
              f"trampoline names is an XDATA pointer rather than a code route "
              f"({', '.join(f'0x{i:04X}' for i in sorted(leftovers))}) -- so this "
              f"image offers no missed *code* route in the arms the walk "
              f"reached, and the follow-up has to be sized on the closure as a "
              f"whole"
              + ("" if all(i in XDATA_CLEAR_IMMEDIATES for i in leftovers)
                 else " -- a leftover appeared that is not a known XDATA clear, "
                      "so it needs reading before it is called a code route"))

    live_own = [p for p in pairs
                if p["own_bank"] != "erased" and p["other_bank"] == "erased"]
    both_erased = [p for p in pairs
                   if p["own_bank"] == "erased" and p["other_bank"] == "erased"]
    contra = [p for p in live_own if p["verdict"] == VERDICT_CONTRA]
    reached = [p for p in both_erased if p["verdict"] != VERDICT_NONE]
    got = (len(live_own), len(contra), len(both_erased), len(reached))
    check(got == CHECK_PINS,
          f"the closure's own check: {got[0]} own-live/other-erased pairs with "
          f"{got[1]} contradiction(s), and {got[2]} both-erased pairs with {got[3]} "
          f"attributed to a bank at all"
          + ("" if got == CHECK_PINS else f" -- expected {CHECK_PINS}"))
    for p in contra + reached:
        print(f"        {SHORT[p['verdict']]} at `{p['region']}` 0x{p['target']:04X}")

    # The `bounds` column, which is what the region map (#50) reads as "do not
    # trust this run's right-hand edge". Checked through bounds_for() -- the
    # function write_regions_csv() calls -- so this holds the column rather than
    # a restatement of it, and a row whose walks all finished carries nothing.
    got_runs = []
    for bank in (0, 1):
        reached_b, who_b, _e_b, cuts_b, _c_b = closures[bank]
        runs_b = runs_of(reached_b)
        covered_b = sum(1 for start, end in runs_b
                        if bounds_for({e for a in range(start, end)
                                       if a in reached_b
                                       for e in who_b[a]}, cuts_b))
        got_runs.append((covered_b, len(runs_b)))
    got_runs = tuple(got_runs)
    check(got_runs == CUT_RUNS,
          f"the per-run bounds column: {got_runs[0][0]} of {got_runs[0][1]} bank0 "
          f"runs and {got_runs[1][0]} of {got_runs[1][1]} bank1 runs are reached "
          f"by a walk that stopped, so the other {got_runs[0][1] - got_runs[0][0]} "
          f"and {got_runs[1][1] - got_runs[1][0]} carry no bound at all"
          + ("" if got_runs == CUT_RUNS else f" -- expected {CUT_RUNS}"))

    # `seed_entries` counts linker-written seeds, and only those, while
    # `sources` names every kind of edge that reached the run. Asserted against
    # the regions CSV's own rows rather than a restatement of the predicate,
    # because the two columns are the whole calibration a region map reads and
    # a future edit could widen one without touching the other. The check that
    # matters is the pair: a run with a table edge in `sources` must have its
    # table edges *excluded* from `seed_entries`.
    rows_csv = list(regions_rows(closures))
    table_only = [r for r in rows_csv if r["sources"] != ["trampoline"]
                  and "trampoline" not in r["sources"]]
    check(table_only and all(r["seed_entries"] == 0 for r in table_only),
          f"the regions CSV's `seed_entries` counts linker-written seeds and "
          f"nothing else: {len(table_only)} of its {len(rows_csv)} runs are "
          f"reached only through a table edge and every one of them reports "
          f"zero seeds, while `sources` still names the mechanism"
          + ("" if table_only and all(r["seed_entries"] == 0 for r in table_only)
             else f" -- {[r['start'] for r in table_only if r['seed_entries']][:4]}"))
    check(all(r["seed_entries"] <= r["entry_points"] for r in rows_csv),
          "and no run counts more seeds than entry points, so the column "
          "cannot exceed the population it is a subset of")

    for bank, want, entries_want in zip((0, 1), CLOSURE_SIZE, ENTRY_POINTS):
        got_size = len(closures[bank][0])
        got_entries = len(closures[bank][2])
        same = (got_size, got_entries) == (want, entries_want)
        print(f"  --   bank{bank} closure: {got_size} addresses from {got_entries} "
              f"entry points ({'as recorded' if same else 'document records ' + str(want) + ' and ' + str(entries_want)})")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--regions-csv", action="store_true",
                    help="write one row per attributed contiguous run per bank on "
                         "stdout instead of the tables")
    ap.add_argument("--pairs-csv", action="store_true",
                    help="write one row per distinct bucket-B (caller bank, target) "
                         "pair on stdout instead of the tables")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the stub decoding, the seed census, the two "
                         "hand-decoded pins, the four verdicts and the closure's own "
                         "check against the committed image")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)

    rows, stubs, tramp = survey(d)
    seeds = seeds_for(tramp)
    handlers = vector_handlers(d, tramp)
    # The vector handlers seed both banks alongside the trampolines, so
    # seeds_for()'s banked-only reading is kept and the two are unioned at the
    # call site. The last section needs the population without either, so that
    # is computed too rather than reconstructed.
    seeded = {b: seeds[b] | handlers[b] for b in (0, 1)}
    closures = {b: closure(d, b, seeded[b]) for b in (0, 1)}
    pairs = pair_rows(rows, closures)

    if args.regions_csv:
        return write_regions_csv(closures, seeded)
    if args.pairs_csv:
        return write_pairs_csv(pairs)

    without = {b: closure(d, b, seeds[b], follow_common=False) for b in (0, 1)}

    print_seeds(stubs, seeded, handlers)
    print_closure(closures, seeded)
    print_pairs(pairs)
    print_headline(pairs, closures)
    print_check(pairs)
    print_handoff(d, closures, seeded, tramp, handlers)
    print_cuts(d, closures, seeded)
    print_common(d, closures, without, handlers, seeds, tramp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
