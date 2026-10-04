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
it would let a closure claim code the linker says is in the other bank); and
`jmp @a+dptr` is a computed target no byte-derived walk can resolve.

**What is deliberately not a seed, and named rather than quietly dropped:** the
reset vector and the interrupt vectors. They are common-area entry points no
trampoline names, and adding them changes the closure's size materially. This
is the single change most likely to move the residue below, so it is a
follow-up and not an oversight.

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


def closure(d: bytes, bank: int, seeds, max_depth: int = MAX_DEPTH,
            max_insns: int = MAX_INSNS):
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

    `common` is the other half of the same honest accounting. A call below
    0x8000 leaves the bank window, and this closure does not follow it, so
    every routine the common area can reach -- and everything a common-area
    routine dispatches to in turn -- is outside the attribution. That is not a
    detail: the `?C?CCASE` reader at 0x7151 that dispatches all 15 of this
    image's inline index tables (bank-call-audit.md 9, 10) is itself common
    area, and its handlers are only reachable through it.
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
                # offset_for_runtime() resolves it there rather than refusing.
                # The common area is mapped in every bank, so attributing those
                # bytes to one of them would be a claim about a region no bank
                # owns.
                if pc >= BANK_FLOOR:
                    reached[pc] += 1
                    who[pc].add(start)
        for why in arm.ends:
            if why.startswith(CUTS):
                cuts[why.split(" at ")[0]].add(start)
        for callee in dict.fromkeys(arm.callees):
            if callee < BANK_FLOOR:
                common[callee].add(start)
            elif offset_for_runtime(callee, region) is not None:
                pending.append((callee, "call", start))
    return reached, who, entries, cuts, common


def entry_chain(entries, addr):
    """The entry-point chain that reaches `addr`, seeds first. Stops at the
    seed, whose `frm` is None."""
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


def print_seeds(stubs, seeds) -> None:
    print("## 1. The seeds: what the linker's own trampolines name")
    print()
    for addr, bank in sorted(stubs.items()):
        print(f"  stub 0x{addr:04X} selects bank {bank}: "
              f"{len(seeds.get(bank, ()))} seed(s) route through it")
    print(f"  {sum(len(v) for v in seeds.values())} seeds in all, every target "
          f">= 0x{BANK_FLOOR:04X}")
    print()
    print("A seed is a (target, bank) pair the linker itself wrote down: the")
    print("trampoline's DPTR immediate, and the bank its stub selects. That bank")
    print("is `find_stubs()` decoding the stub body's `setb`/`clr` on")
    print("P1.0-P1.2, not a header field -- the same reading bank-call-audit.md 3")
    print("records, corroborated by make_bank_image.py --self-test. It is the one")
    print("link in the chain here that is not new evidence, and it is not new.")
    print()


def print_closure(closures, seeds) -> None:
    print("## 2. The closure, per bank")
    print()
    print("An address is attributed to a bank when a walk seeded from that")
    print("bank's own seeds decodes it. `entry points` counts the trampoline")
    print("seeds plus the same-bank call targets they led to, each descended")
    print("once; `runs` is how many contiguous spans those addresses fall into.")
    print()
    print("| bank | seeds | entry points | call-derived | addresses | runs |")
    print("|---|---:|---:|---:|---:|---:|")
    for bank in sorted(closures):
        reached, _who, entries, _cuts, _common = closures[bank]
        derived = sum(1 for kind, _frm in entries.values() if kind == "call")
        print(f"| `bank{bank}` | {len(seeds[bank])} | {len(entries)} | {derived} "
              f"| {len(reached)} | {len(runs_of(reached))} |")
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
    depth = collections.Counter()
    for p in own:
        bank = int(p["region"][-1])
        depth[len(entry_chain(closures[bank][2], p["target"])) - 1] += 1
    shallow = depth[0] + depth[1]
    deepest = max(depth, default=0)
    print(f"  {len(own)} of the {len(amb)} have the target as an entry point of the")
    print("  caller's own closure, which is the strongest sub-class: a seed the")
    print(f"  linker wrote down ({depth[0]}), or a same-bank call target one to")
    print(f"  {deepest} hops from one ({len(own) - depth[0]}). Those hops are")
    print("  measured, each chain walked back to the seed that reaches it:")
    print()
    print("    " + "  ".join(f"{k}: {depth[k]}" for k in sorted(depth)))
    print()
    print(f"    {shallow} at one hop or fewer, {len(own) - shallow} at two or more")
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


def print_handoff(d, closures, seeds, tramp) -> None:
    """The site issue #48 was opened for: bank-1 runtime 0xDFD0's
    `lcall 0x888C`, whose `handoff->write` verdict rests on the same-bank
    assumption plus one hand decode (pd-xdata-overlap.md 2)."""
    site, target, bank = 0xDFD0, 0x888C, 1
    print("## 6. The `0x04A6` handoff at bank-1 `0xDFD0`")
    print()
    reached, _who, entries, _cuts, _common = closures[bank]
    print(f"  the call site 0x{site:04X} (`lcall 0x{target:04X}`) is "
          f"{'inside' if site in reached else 'OUTSIDE'} bank 1's closure")
    print(f"  the target 0x{target:04X} is {'inside' if target in reached else 'OUTSIDE'} "
          f"bank 1's closure and "
          f"{'inside' if target in closures[0][0] else 'outside'} bank 0's")
    if target in reached:
        chain = entry_chain(entries, target)
        print(f"  reached from entry point(s) "
              f"{' -> '.join(f'0x{a:04X}' for a in chain)}")
        for a in chain:
            if a not in seeds[bank]:
                continue
            names = [e for e, (b, t) in sorted(tramp.items()) if t == a and b == bank]
            print(f"  0x{a:04X} is a seed: trampoline(s) "
                  f"{', '.join(f'0x{e:04X}' for e in names)} name it")
    print()
    print("The two halves answer differently, and the difference is the point.")
    print("The closure reaches the *target* from a bank-1 seed, so the 16-bit")
    print("store pd-xdata-overlap.md 2 decoded by hand is attributed to bank 1")
    print("by this closure as well as by that hand decode -- a second line of")
    print("evidence, and it agrees. It does not reach the *call site*, so the")
    print("caller side is unchanged: 0xDFD0 being bank-1 code is still the")
    print("assumption plus the hand decode, and no amount of the target's")
    print("attribution settles it.")
    print()
    print("Neither half turns \"assumed\" into \"proved\". The walk has no")
    print("function-boundary recovery, so every attribution here is")
    print("\"attributed by this closure\"; and a negative is a statement about")
    print("this closure's coverage, never about 0x888C or 0xDFD0 themselves.")
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


def print_cuts(closures, seeds) -> None:
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
    print("closure records it and follows nothing. What that costs is larger than")
    print("the count suggests. The `?C?CCASE` reader at 0x7151 dispatches all 15")
    print("of this image's inline index tables (bank-call-audit.md 9, 10; every")
    print("one of the 15 sites in index-table-entries.csv is an `lcall 0x7151`),")
    print("and it is itself common area -- so all 15 handlers are out of reach")
    print("of this closure unless some other path reaches them too. Eleven of the")
    print("15 dispatch sites sit inside bank0's window, four in the common area.")
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
    print("Named blind spots, none of which this tool closes:")
    print()
    print("  * `jmp @a+dptr` is a computed target no byte-derived walk can")
    print("    resolve, and bank1's closure stops at seven of them: 0x8A6B,")
    print("    0x98E4, 0x99DF, 0x9B02, 0x9E36, 0xC82F and 0xEFE7. The two read")
    print("    by hand are the dispatch idiom bank-call-audit.md 9 reads at the")
    print("    common-area 0x7151, with the table base in a `mov dptr,#table`")
    print("    rather than popped off the stack -- and a jump table is exactly the")
    print("    thing a byte-derived walk cannot enumerate. bank0's closure stops")
    print("    at none; that is a property of which routines its seeds reach, not")
    print("    evidence that bank0 has no dispatch.")
    print("  * The reset vector and the interrupt vectors are not seeds, so")
    print("    whatever they reach is outside both closures. This is the single")
    print("    change most likely to move the residue in section 4.")
    print("  * A second bank-switch idiom spelled differently would be invisible:")
    print("    this walk treats every same-bank call as intra-bank.")
    print("  * Banks 2 and 3 are taken as unused on find_banks.py's word and were")
    print("    not re-derived.")
    print("  * A call into the common area is not a failure of the walk and is")
    print("    not an attribution: the common area is mapped in every bank, so")
    print("    no bank owns those bytes.")
    print("  * The seeds are byte-derived too. audit_call_targets.trampolines()")
    print("    finds them by shape, and a shape match inside a data table would")
    print("    be indistinguishable here from a real one.")
    print()
    print("Nothing in this file was measured on hardware. No register was read")
    print("back, no capture was taken, and no `status:` in")
    print("../annotations/registers.yaml moves.")
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


def write_regions_csv(closures, seeds) -> int:
    """One row per attributed contiguous run per bank.

    The entry-point columns are what a later region map (#50) needs and a
    per-address list cannot give it: how many independent paths reach the run,
    how many of those start at a name the linker wrote down, and which bounds
    fired for the walks that covered it. `bounds` is bounds_for() over those
    walks, so a run whose entry points hit a bound is a run whose right-hand
    edge is the walk's decision and not the image's, and a run with none is not
    labelled by a bound that fired somewhere else in the bank.
    """
    w = csv.writer(sys.stdout)
    w.writerow(["bank", "start", "end", "bytes", "entry_points", "seed_entries",
                "min_paths", "max_paths", "bounds"])
    for bank in sorted(closures):
        reached, who, entries, cuts, _common = closures[bank]
        for start, end in runs_of(reached):
            addrs = [a for a in range(start, end) if a in reached]
            paths = [reached[a] for a in addrs]
            eps = {e for a in addrs for e in who[a]}
            seeded = sum(1 for e in eps if entries[e][0] == "trampoline")
            bounds = bounds_for(eps, cuts)
            w.writerow([f"bank{bank}", f"0x{start:04X}", f"0x{end:04X}",
                        len(addrs), len(eps), seeded, min(paths), max(paths),
                        " ; ".join(bounds)])
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

# The two of bank1's seven `jmp @a+dptr` sites the write-up describes rather
# than just lists, as (address, the `mov dptr,#table` three bytes above the
# dispatch that the walk stops on). Both were read in `r2 -a 8051` against a
# make_bank_image.py bank-1 image; the seventh and the rest are named by the
# tool and not characterised.
DISPATCH = ((0x8A65, b"\x90\x8a\x45"), (0x98DE, b"\x90\x98\xb4"))

# The four verdicts over all the bucket-B pairs and over the both-banks-live
# ones. A different dump re-derives them rather than inheriting this image's
# answer, which is the whole point of pinning them.
PAIR_PINS = {
    "all": (573, 207, 115, 410),
    "both_live": (568, 207, 115, 398),
    "populations": (1305, 1288),
}

# The 17 pairs outside the 1288: zero contradictions among the 11
# own-live/other-erased pairs, and zero attributions among the 6 both-erased.
CHECK_PINS = (11, 0, 6, 0)

# The regions CSV's `bounds` column, per bank: the runs a stopped walk reaches,
# and the runs in all. The two differ by an order of magnitude, and that gap is
# the pin. `cuts` is every reason that fired *anywhere* in the bank, so a
# consumer -- or a future edit to bounds_for() -- that unions it over a run
# reports all 9662 rows as bound-limited when 603 are. Pinned per run because
# the per-address figures §5 already prints (849 of 12694, 115 of 4159) do not
# constrain it: a run of 1 byte and a run of 40 both count once.
CUT_RUNS = ((535, 7006), (68, 2656))

# The closures' own sizes, reported rather than pinned. They are a property of
# this image's bounds, and a pin here would fail a correct tool over a
# different dump -- the seed census and the four verdicts above are the pins
# that mean something independent of how much a walk happened to cover.
CLOSURE_SIZE = (12694, 4159)
ENTRY_POINTS = (816, 182)


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
    census = (len(tramp), len(seeds[0]), len(seeds[1]))
    check(census == SEEDS and all(t >= BANK_FLOOR for _e, (_b, t) in tramp.items()),
          f"{census[0]} trampolines, {census[1]} through the bank-0 stub and "
          f"{census[2]} through the bank-1 one, every target >= "
          f"0x{BANK_FLOOR:04X}"
          + ("" if census == SEEDS else f" -- expected {SEEDS}"))

    closures = {b: closure(d, b, seeds[b]) for b in (0, 1)}

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
    closures = {b: closure(d, b, seeds[b]) for b in (0, 1)}
    pairs = pair_rows(rows, closures)

    if args.regions_csv:
        return write_regions_csv(closures, seeds)
    if args.pairs_csv:
        return write_pairs_csv(pairs)

    print_seeds(stubs, seeds)
    print_closure(closures, seeds)
    print_pairs(pairs)
    print_headline(pairs, closures)
    print_check(pairs)
    print_handoff(d, closures, seeds, tramp)
    print_cuts(closures, seeds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
