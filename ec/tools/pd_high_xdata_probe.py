#!/usr/bin/env python3
"""Classify every `MOV DPTR` target in the PD image's `0xFFxx` region.

`annotations/pd-xdata-overlap.md` 5.3 measures that region twice and stops: a
`90 hi lo` byte scan of `ec/firmware/GMxMGxx_11.800` finds 45 distinct `0xFFxx`
targets in the PD image across 170 sites, and `xdata_register_map.py` pins 23 of
them in `XSPACE_PD_HIGH`. The gap is this tool's subject, address by address,
and the point of it is that a per-address reason is a measurement and a
per-address absence is not.

**The population is a union, because the two sets are not the same set.** Three
of the 23 pinned addresses -- `0xFFC1`, `0xFFD1` and `0xFFDB` -- are reached
only by an `inc DPTR` from the address below, so a byte scan never counts them,
and comparing the scan's 45 against the census's 23 compares two populations
rather than measuring a gap. This tool classifies the union, so every address
either side names gets a verdict, and it prints all three figures rather than
only the difference between two of them. A site is likewise counted under the
address it names and under the address one byte above it, which is why the
per-address site lists are longer than the scan's 170 and the scan's own figure
is printed beside them rather than reconciled by hand.

**The distinction that matters is a pointer against an integer.**
`pd/122F.asm` is `add_dptr_to_word_0d0e_ea_guard`: it adds DPTR into the
internal-RAM word at `0x0D`/`0x0E` and contains no `movx` at all, so a
`mov DPTR,#0xFFFF` in front of it is not a pointer being loaded. Reading such a
site as an XDATA access is exactly the overclaim
`annotations/xdata-register-map.md` 5.1 is about, and it is why
`callee-non-xdata` is a verdict rather than a silent skip. The same reasoning
separates `callee-rebases` -- `pd/0D38.asm` dereferences `DPTR + R1:R2`, so the
seed is a base and the byte touched is somewhere else -- from `callee-derefs`,
where the callee dereferences DPTR as it stands and the address really is the
one accessed.

**Two window rules would be two answers, so there is one.** A site on a listed
instruction boundary is read out of the committed `.asm`; a site in bytes no
listing covers is decoded from the image with `disasm8051.py`, which shares no
code with Ghidra's SLEIGH and is the instrument `citation_gap_scan.py` already
uses for exactly this gap. Both are put into the listing's own spelling first
(`listing_shape`) and both are then read by one `window()` implementing
`xdata_space()`'s rule: the straight-line run after the seed, `XSPACE_WINDOW`
rows long, no control transfer, nothing that can move DPTR, at most one
`inc DPTR`. `--self-test` holds that rule to `xdata_space()` itself on all 23
pinned addresses, so the uncovered path is checked against the oracle on every
address where the oracle has an answer.

**One word per address, and the tally beside it.** `verdict_of` resolves an
address's several sites to the strongest claim any of them supports, which is
one word and is frequently not the whole truth: `0xFFFC` hands DPTR to the
adder at fourteen sites and to a routine that dereferences it at one. The
report therefore prints the per-site tally as well as the word, so a reader who
wants the weaker reading is not left to divide.

**The census is a lower bound and this does not extend it.** `XSPACE_PD_HIGH`
is read, never written: the addresses a `movx` is found behind would need new
Ghidra functions seeded at their sites before `xdata-clusters.csv` could carry
them, and CLAUDE.md records that two branches that both rebuild one project
cannot merge. They are listed here with their seed sites so that is the next
tranche's work-list rather than a rediscovery.

**"Not found by this method" is the floor, and it is a floor rather than a
claim about the firmware.** A site in uncovered bytes is decoded by walking
forward from the seed's own bytes, so a misframed seed would produce a window
decoding nothing real; `framed` is the `disasm8051.converges_from()` score for
every decoded site and the report prints it. A window that ends at a branch or a
`ret` rather than a call is reported as ending there and is not followed, and
the callee chase recurses at most `MAX_CALLEE_DEPTH` levels and says which level
it reached. None of this is hardware evidence: every figure is read off
committed files, and no register was read back.

Usage:
    python3 ec/tools/pd_high_xdata_probe.py              # the per-address table
    python3 ec/tools/pd_high_xdata_probe.py --notes      # and every site's reason
    python3 ec/tools/pd_high_xdata_probe.py --self-test  # known answers
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import disasm8051 as D                                       # noqa: E402
import xdata_register_map as X                               # noqa: E402

EC_DIR = os.path.dirname(HERE)
FIRMWARE = os.path.join(EC_DIR, "firmware", "GMxMGxx_11.800")
# The PD image's own address space at file 0x20000, sized as its own 0x20000
# bytes. `pd_image_census.py` owns the region and a dump that did not hold it
# would make every count below a statement about a short file.
PD_OFF = 0x20000
PD_SIZE = 0x20000
PD_PROGRAM = X.PD_PROGRAM
# The region's own lower edge, and the top of the classic 8051's 16-bit address
# space, which is what makes the region a region rather than a scatter.
REGION_LO = 0xFF00
REGION_HI = 0xFFFF
# How far the callee chase goes past the site. Depth 1 is the routine the site's
# own window names, depth 2 the one that routine names. The bound is a number
# rather than a stop condition because a chase with no bound reports a depth it
# never reached, and one bounded by "we found something" reports a depth it
# chose.
MAX_CALLEE_DEPTH = 2
# How many preceding bytes `converges_from` is asked about, and so the score a
# site is out of. disasm8051's own default, named here so the column means the
# same thing in both tools.
FRAMING_BACK = 24

# The verdicts, strongest claim first, and the order `verdict_of` resolves an
# address's several sites in. `callee-derefs` outranks `callee-rebases` because
# a site where something is dereferenced at the address is a stronger statement
# than one where something is dereferenced at a base plus an offset, and both
# outrank a callee that never dereferences at all.
VERDICTS = (
    "census",
    "literal-read",
    "literal-write",
    "inc-continuation",
    "callee-derefs",
    "callee-rebases",
    "callee-non-xdata",
    "not-found-by-this-method",
)
# The reaches that assert a dereference happened, which is what makes a
# direction meaningful beside them and what lets a census address be renamed
# `census` without losing the reach underneath.
KINDS_DIRECTION = ("literal", "inc", "callee-derefs")
# How each verdict is reached, which is the granularity a direction is read
# over. The read and the write of one address are two sites with two verdicts
# and one reach, and a `dir` column that could only say `read` for an address
# that is also written would understate it.
KINDS = {"literal-read": "literal", "literal-write": "literal",
         "inc-continuation": "inc", "callee-derefs": "callee-derefs",
         "callee-rebases": "callee-rebases",
         "callee-non-xdata": "callee-non-xdata",
         "not-found-by-this-method": "not-found-by-this-method"}
# The control transfers whose operand names a routine this tool will chase. A
# window that ends at a conditional branch or at a `ret` ends there: the next
# instruction is not the one that runs, and following it would answer a
# different question. `inc DPTR` is not in the set either, for the same reason
# `xdata_space()` leaves it out -- a walk is not a transfer.
CALLS = ("lcall", "ljmp", "acall", "ajmp")
# `xdata_register_map`'s window helpers read the `.asm` spelling -- a lower-case
# mnemonic, the register upper case, the immediate lower case -- and
# `disasm8051.mnemonic` writes every instruction all lower case with no space
# after the comma. Recasing one decoded row is cheaper than carrying a second
# copy of the window rule, and a second rule is a second answer to the same
# question. A bare register name is what is recased; an immediate and a branch
# target are left alone, because `DPTR_IMM` and every target here are read in
# lower case.
REGISTERS = frozenset((
    "a", "ab", "b", "c", "acc", "dpl", "dph", "dptr", "pc", "psw", "sp",
    "r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7",
))


def hexaddr(addr: int) -> str:
    return f"0x{addr:04X}"


def listing_shape(mnem: str, oper: str) -> tuple:
    """`disasm8051`'s spelling of one instruction, in the `.asm` exporter's.

    Idempotent on a row already in that shape, which is what lets one `window()`
    read a listed row and a decoded one without either being special-cased at
    the call site."""
    parts = []
    for part in oper.split(","):
        part = part.strip()
        low = part.lower()
        bare = low[1:] if low.startswith("@") else low
        if bare in REGISTERS:
            part = ("@" if low.startswith("@") else "") + bare.upper()
        parts.append(part)
    return mnem.lower(), ", ".join(parts)


def dptr_sites(image: bytes) -> dict:
    """`{address: [runtime site, ...]}` for every `90 hi lo` in the region.

    A byte scan, deliberately, and not a walk of the decoded instructions: the
    question is which *bytes* name the address, and a walk would have already
    decided the framing this tool then has to report evidence about. The cost
    is that a data byte can be a site, which is why no site is a finding on its
    own and every decoded one carries its framing score."""
    out = collections.defaultdict(list)
    for i in range(len(image) - 2):
        if image[i] != 0x90:
            continue
        value = (image[i + 1] << 8) | image[i + 2]
        if REGION_LO <= value <= REGION_HI:
            out[value].append(i)
    return dict(out)


def load_image() -> bytes:
    with open(FIRMWARE, "rb") as f:
        blob = f.read()
    return blob[PD_OFF:PD_OFF + PD_SIZE]


def listed_index(asm: dict) -> dict:
    """`{runtime address: (function, index into that function's rows)}`.

    Per function rather than flattened, for `read_asm`'s own reason: a window
    that ran from the end of one export into the next would pair a seed with a
    dereference not reachable from it."""
    out = {}
    for stem, seq in asm.items():
        for i, (at, _mnem, _oper) in enumerate(seq):
            out.setdefault(int(at, 16), (stem, i))
    return out


def image_run(image: bytes, off: int, count: int = None) -> list:
    """`count` rows decoded forward from `off` in the image.

    `stop_at_flow` is not set, because the window rule is what stops: it has to
    see the transfer to name it, and a decoder that returned early would make
    "the window ended at a call" indistinguishable from "the window ran out"."""
    rows = []
    for at, _raw, text in D.decode(image, off, count or X.XSPACE_WINDOW, addr=off):
        mnem, _, oper = text.partition(" ")
        mnem, oper = listing_shape(mnem, oper)
        rows.append((at, mnem, oper))
    return rows


def listing_run(asm: dict, stem: str, i: int, count: int = None) -> list:
    rows = []
    seq = asm[stem][i:] if count is None else asm[stem][i:i + count]
    for at, mnem, oper in seq:
        mnem, oper = listing_shape(mnem, oper)
        rows.append((int(at, 16), mnem, oper))
    return rows


def window(rows: list, addr: int, seed: int) -> tuple:
    """`xdata_space()`'s rule, over one straight-line run.

    `rows` starts at the `mov DPTR,#seed` itself. The return is
    `("literal"|"inc", direction, None)`, `("transfer", target, mnemonic)` for a
    call or jump the window ended on, or `("stop", why, None)` for anything
    else -- a branch, a `ret`, a second `inc DPTR`, anything that moves DPTR, or
    the end of the run.

    The three `stop` reasons are kept apart in the site column because "the
    window ended at a `jz`" and "the window ended at a `lcall`" are different
    facts about the same site, and collapsing them would file a branch beside a
    chaseable callee.

    **A `movx` that does not dereference the address under test does not end
    the window; the walk continues past it.** That is `xdata_space()`'s own
    rule and the reason its comment says "keep looking": at `pd/F2FB.asm`
    `0xF300` dereferences the seed, `0xF301` walks DPTR up one and `0xF302`
    dereferences the address above it, so `0xFFDB` is an `inc` continuation
    found *behind* a `movx` for `0xFFDA`. Returning at the first `movx` loses
    all three of the census's inc-only addresses, and does so silently.
    """
    walked = 0
    for _at, mnem, oper in rows[1:1 + X.XSPACE_WINDOW]:
        if mnem in X.XSPACE_FLOW:
            if mnem in CALLS:
                return ("transfer", int(oper.split(",")[0].strip(), 16), mnem)
            return ("stop", f"{mnem} ends the window", None)
        if mnem == "inc" and oper == "DPTR":
            walked += 1
            if walked > 1:
                return ("stop", "second inc DPTR", None)
            continue
        if X.clobbers_dptr(mnem, oper):
            return ("stop", f"{mnem} {oper} moves DPTR", None)
        if mnem == "movx" and "@DPTR" in oper:
            direction = "write" if oper.split(",")[0].strip() == "@DPTR" else "read"
            if walked == 1 and seed == addr - 1:
                return ("inc", direction, None)
            if walked == 0 and seed == addr:
                return ("literal", direction, None)
            # A dereference of the seed itself says nothing about the address
            # one byte up, and an address's own seed says nothing about a walk
            # past it. Keep looking, which is what the oracle does.
    return ("stop", "window end", None)


def callee(image: bytes, listed: dict, asm: dict, target: int,
           depth: int = 1) -> tuple:
    """What a routine the site's window names does with DPTR, and how far the
    chase got: `(verdict, direction, note)`.

    Read from the callee's own listing where there is one and decoded from the
    image where there is not -- the same two sources `window()` takes, for the
    same reason and under the same rule. The three answers are the three things
    a routine can be here: it never names the external data space, it
    dereferences DPTR only after moving it by something this listing does not
    fix, or it dereferences DPTR as it stands.

    **"Never names the external data space" is asked of the whole listing, not
    of the window.** The window is `XSPACE_WINDOW` rows because a seed's
    straight-line run is that long; a routine is longer than that, and a verdict
    about a routine read from eight of its seventeen rows would be a claim
    about the window wearing the routine's name. A callee with no listing has no
    end to read to, and says so in the note instead.

    **A forwarder is followed, and a branch is not.** `pd/7059.asm` is one
    `lcall 0x122f` and `pd/8845.asm` is one `ljmp 0x0D38`; a routine whose entry
    run's first transfer is a call hands the question to the routine it reaches,
    which is what turns "this one has no `movx`" into a statement about the
    routine doing the work. A conditional branch or a `ret` is the other thing
    entirely -- the next instruction is not the one that runs -- and an entry run
    that ends there has *not* been shown not to dereference, so it comes back
    `not-found-by-this-method` rather than `callee-non-xdata`.
    """
    if depth > MAX_CALLEE_DEPTH:
        return ("not-found-by-this-method", "none",
                f"chase stopped at depth {MAX_CALLEE_DEPTH}")
    if target in listed:
        stem, i = listed[target]
        whole = listing_run(asm, stem, i)
        rows, source = whole[:X.XSPACE_WINDOW], f"listing {stem}"
        extent = f"its {len(whole)} rows"
    else:
        whole = rows = image_run(image, target)
        source = f"decoded {hexaddr(target)}"
        extent = f"the {len(whole)} rows decoded from it"
    anywhere = [at for _a, m, o in whole if m == "movx" and "@DPTR" in o
                for at in (_a,)]
    ended = "its entry run holds no control transfer and no movx"
    for at, mnem, oper in rows:
        if mnem in X.XSPACE_FLOW:
            if mnem in CALLS:
                inner = int(oper.split(",")[0].strip(), 16)
                verdict, direction, note = callee(image, listed, asm, inner,
                                                  depth + 1)
                return (verdict, direction,
                        f"{source} {mnem} at {hexaddr(at)} to {hexaddr(inner)}, "
                        f"which {note}")
            ended = f"its entry run ends at {mnem} {hexaddr(at)} before any movx"
            break
        if mnem == "movx" and "@DPTR" in oper:
            for before, bmnem, boper in rows[1:]:
                if before == at:
                    break
                if X.clobbers_dptr(bmnem, boper):
                    return ("callee-rebases", "none",
                            f"{source}: {bmnem} {boper} at {hexaddr(before)} "
                            f"moves DPTR before the first movx at "
                            f"{hexaddr(at)}, so the seed is a base")
            direction = "write" if oper.split(",")[0].strip() == "@DPTR" else "read"
            return ("callee-derefs", direction,
                    f"{source}: first movx at {hexaddr(at)}")
    # The entry run stopped without reaching a dereference. Whether that is a
    # statement about the routine or only about the run is the whole-listing
    # question, and the two answers are different verdicts: "this routine never
    # names the external data space" is a claim about 0x122F, while "this arm
    # does not reach one" is a claim about one path through a routine that
    # reaches one on another.
    if not anywhere:
        return ("callee-non-xdata", "none", f"{source}: no movx in {extent}")
    return ("not-found-by-this-method", "none",
            f"{source}: {ended}, and its listing has a movx at "
            f"{hexaddr(anywhere[0])}")


def classify_site(image: bytes, listed: dict, asm: dict, off: int,
                  seed: int, addr: int) -> dict:
    """One `90 hi lo` site: whether a listing covers it, how well framed it is,
    and what its window does.

    `framed` is `converges_from()`'s onto-count out of `FRAMING_BACK` for a
    decoded site and `None` for a listed one, where the exporter's own record of
    the framing is the stronger evidence and a linear walk's opinion would be a
    second opinion on a row already aligned.

    **A site nothing lands on is not reasoned about, and the window it would
    have given is kept beside the verdict rather than in place of it.** A `90 hi
    lo` three-byte group sitting at 0xCC53 in the PD image is the tail of a
    `lcall 0x90FF` at 0xCC52, so the byte scan names `0xFFA3` at an address
    where there is no instruction to name it; `converges_from` scores that site
    0 of 24 for exactly this reason. The window would have read it as a seed
    and chased a callee, and reporting that as a verdict would be reading a data
    byte as code. So the site's verdict is `not-found-by-this-method` and
    `unframed` carries what the window said, which is the claim a reader can
    check against the bytes rather than a claim this tool stands behind.
    """
    stem = listed.get(off, (None, None))[0]
    rows = listing_run(asm, *listed[off], count=X.XSPACE_WINDOW) if stem \
        else image_run(image, off)
    onto, _over = D.converges_from(image, off, back=FRAMING_BACK)
    out = {"site": off, "seed": seed, "listing": stem, "target": None,
           "framed": None if stem else onto, "verdict": None, "unframed": None,
           "direction": "none", "note": ""}
    kind, value, why = window(rows, addr, seed)
    if kind in ("literal", "inc"):
        out["verdict"] = ("literal-write" if value == "write" else "literal-read") \
            if kind == "literal" else "inc-continuation"
        out["direction"] = value
    elif kind == "transfer":
        out["target"] = value
        verdict, direction, note = callee(image, listed, asm, value)
        out["verdict"] = verdict
        out["direction"] = direction
        out["note"] = f"window ended on {why} {hexaddr(value)}; {note}"
    else:
        out["verdict"] = "not-found-by-this-method"
        out["note"] = why
    if onto == 0:
        out["unframed"] = out["verdict"]
        out["verdict"] = "not-found-by-this-method"
        out["direction"] = "none"
        out["note"] = (f"no linear walk from any of the {FRAMING_BACK} "
                       f"preceding bytes lands on this seed, so the window "
                       f"that would have read {out['unframed']} is not "
                       f"reported as a verdict")
    return out


def verdict_of(sites: list) -> str:
    """The one verdict an address gets out of all of its sites: the strongest
    claim any of them supports, in `VERDICTS` order."""
    found = {s["verdict"] for s in sites}
    for verdict in VERDICTS:
        if verdict in found:
            return verdict
    return "not-found-by-this-method"


def reach_of(sites: list) -> str:
    """How the address is reached, as a `KINDS` value rather than a verdict.

    `census` is a fact about `XSPACE_PD_HIGH` and says nothing about how the
    address is reached, so it cannot be the thing this returns; and an address
    that is both read and written is reached one way, not two, which is what
    makes this the right granularity for reading a direction over."""
    for verdict in VERDICTS:
        if verdict in {s["verdict"] for s in sites}:
            return KINDS[verdict]
    return "not-found-by-this-method"


def directions_of(sites: list, reach: str) -> str:
    """`read`, `write`, `read+write` or `none`, over the sites whose reach is
    `reach`. `none` rather than an empty cell, because an empty cell reads as a
    row nobody filled in."""
    dirs = {s["direction"] for s in sites
            if KINDS[s["verdict"]] == reach and s["direction"] != "none"}
    return "+".join(sorted(dirs)) if dirs else "none"


def classify(image: bytes = None, asm: dict = None) -> dict:
    """`{address: {verdict, direction, tally, census, scanned, sites}}` over
    the union of the two populations.

    The union, and not the scan's 45 alone, because three of the 23 pinned
    addresses are `inc` continuations a byte scan cannot see and classifying the
    scan alone would leave the census's own three without a verdict."""
    image = load_image() if image is None else image
    asm = X.read_asm(PD_PROGRAM) if asm is None else asm
    listed = listed_index(asm)
    scan = dptr_sites(image)
    census = set(X.XSPACE_PD_HIGH)
    out = {}
    for addr in sorted(set(scan) | census):
        sites = []
        for seed in (addr, addr - 1):
            for off in scan.get(seed, []):
                sites.append(classify_site(image, listed, asm, off, seed, addr))
        reach = reach_of(sites)
        verdict = "census" if addr in census and reach in KINDS_DIRECTION \
            else verdict_of(sites)
        out[addr] = {
            "addr": addr,
            "census": addr in census,
            "scanned": addr in scan,
            "verdict": verdict,
            "reach": reach,
            "direction": directions_of(sites, reach),
            "tally": collections.Counter(s["verdict"] for s in sites),
            "sites": sites,
        }
    return out


def coverage(asm: dict) -> dict:
    """How much of the image the PD listings decode, and where they stop.

    This is the measurement the correction to `annotations/pd-xdata-overlap.md`
    5.3 rests on, so it is computed here rather than quoted: the count of
    distinct instruction addresses, the share of the region, and the highest
    one."""
    addrs = {int(at, 16) for seq in asm.values() for at, _m, _o in seq}
    return {"addresses": len(addrs), "region": PD_SIZE,
            "percent": 100.0 * len(addrs) / PD_SIZE,
            "highest": max(addrs) if addrs else 0}


def framing_of(row: dict) -> str:
    """`converges_from()`'s onto-count for the sites that produced the address's
    reach, over `FRAMING_BACK`. `listed` where a listing covered the site and
    the score is the exporter's framing rather than this tool's, and `0` is
    printed as `0/24` rather than blanked, because a site no linear walk syncs
    onto is a fact about the site and not a formatting choice."""
    scores = [s["framed"] for s in row["sites"]
              if KINDS[s["verdict"]] == row["reach"] and s["framed"] is not None]
    if not scores:
        return "listed" if any(s["listing"] for s in row["sites"]) else "-"
    if min(scores) == max(scores):
        return f"{scores[0]}/{FRAMING_BACK}"
    return f"{min(scores)}-{max(scores)}/{FRAMING_BACK}"


def via_of(row: dict) -> str:
    """Where the sites producing the address's reach came from."""
    stems = {s["listing"] or "decoded" for s in row["sites"]
             if KINDS[s["verdict"]] == row["reach"]}
    return "+".join(sorted(stems))


def report(rows: dict, cover: dict) -> str:
    census = [r for r in rows.values() if r["census"]]
    scan = [r for r in rows.values() if r["scanned"]]
    both = [r for r in scan if r["census"]]
    unc = [r for r in rows.values() if not r["census"]]
    out = ["pd_high_xdata_probe: the PD image's 0xFFxx MOV DPTR region", ""]
    out.append(f"  image            {PD_OFF:#06x}-{PD_OFF + PD_SIZE - 1:#06x} "
               f"of ec/firmware/GMxMGxx_11.800, its own address space")
    out.append(f"  listings decode  {cover['addresses']} instruction addresses, "
               f"{cover['percent']:.1f}% of the region, highest "
               f"{hexaddr(cover['highest'])}")
    out.append(f"  byte scan        {len(scan)} distinct targets across "
               f"{len({s['site'] for r in rows.values() for s in r['sites']})} "
               f"sites")
    out.append(f"  census pins      {len(census)} addresses at or above "
               f"{hexaddr(REGION_LO)}; {len(both)} of them are byte-scan "
               f"targets and {len(census) - len(both)} are inc continuations")
    out.append(f"  in no census row {len(unc)} = {len(scan)} scanned minus "
               f"{len(both)} in both, which is not {len(scan)} minus "
               f"{len(census)}")
    out.append("")
    out.append(f"  {'address':<8} {'in':<6} {'verdict':<23} {'reach':<16} "
               f"{'dir':<10} {'framed':<8} via")
    for r in rows.values():
        out.append(f"  {hexaddr(r['addr']):<8} "
                   f"{'census' if r['census'] else '-':<6} {r['verdict']:<23} "
                   f"{r['reach']:<16} {r['direction']:<10} "
                   f"{framing_of(r):<8} {via_of(r)}")
    out.append("")
    out.append("  One verdict per address is the strongest claim any of its "
               "sites supports;")
    out.append("  the tally under the table is what the weaker sites said, and "
               "a site is")
    out.append("  counted both under the address it names and under the address "
               "one byte up,")
    out.append("  which is why these site lists run to more than the scan's "
               "figure above.")
    out.append("")
    out.append(f"  {'address':<8} {'in census':<10} sites by verdict")
    for r in rows.values():
        tally = ", ".join(f"{v} {k}" for k, v in sorted(r["tally"].items()))
        out.append(f"  {hexaddr(r['addr']):<8} "
                   f"{'yes' if r['census'] else 'no':<10} {tally}")
    out.append("")
    unframed = [s for r in rows.values() for s in r["sites"] if s["unframed"]]
    if unframed:
        out.append("  Seeds no linear walk lands on, so not reported as "
                   "verdicts:")
        for s in unframed:
            out.append(f"    {hexaddr(s['site'])} (seed {hexaddr(s['seed'])}) "
                       f"would have read {s['unframed']}")
        out.append("")
    out.append("  " + "  ".join(f"{k} {sum(1 for r in rows.values() if r['verdict'] == k)}"
                                for k in VERDICTS
                                if any(r["verdict"] == k for r in rows.values())))
    out.append("")
    out.append("  Every figure is read off committed files. No register was read "
               "back and no")
    out.append("  hardware was involved. `not-found-by-this-method` is what this "
               "tool's window")
    out.append("  reached, not a statement about the firmware.")
    return "\n".join(out)


def notes(rows: dict) -> list:
    """Every site's own reason, so a claim about a named routine is checkable
    from the tool's output rather than from a reader's memory."""
    out = []
    for r in rows.values():
        for s in r["sites"]:
            origin = f"listing {s['listing']}" if s["listing"] else \
                f"decoded, {s['framed']}/{FRAMING_BACK} framed"
            out.append(f"  {hexaddr(r['addr'])} at {hexaddr(s['site'])} "
                       f"(seed {hexaddr(s['seed'])}, {origin}): "
                       f"{s['verdict']}"
                       + (f" -- {s['note']}" if s["note"] else ""))
    return out


def self_test() -> int:
    ok = []

    def check(label, got, want):
        ok.append(f"  ok    {label}" if got == want
                  else f"  FAIL  {label}: got {got!r}, want {want!r}")

    asm = X.read_asm(PD_PROGRAM)
    image = load_image()
    rows = classify(image, asm)
    cover = coverage(asm)
    scan = dptr_sites(image)
    census = set(X.XSPACE_PD_HIGH)

    check("the byte scan finds 45 distinct 0xFFxx targets in the PD image",
          len(scan), 45)
    check("across 170 sites", sum(len(v) for v in scan.values()), 170)
    check("of the 23 pinned census addresses, 20 are byte-scan targets",
          len(census & set(scan)), 20)
    check("so the residue is 25, and not 45 - 23 = 22",
          len(set(scan) - census), 25)
    check("the three the scan cannot see are the three inc continuations",
          sorted(census - set(scan)), sorted(X.XSPACE_INC_ONLY))
    check("every address classified is a scan target, a pinned census address, "
          "or both", len(rows), len(set(scan) | census))
    check("the listings decode under a tenth of the region and stop below "
          "0xF800", cover["percent"] < 10.0 and cover["highest"] < 0xF800, True)

    # The rule, held to the oracle. The uncovered path is only trustworthy
    # because on the 23 addresses where xdata_space has an answer, this tool's
    # own window over the same rows reaches the same one.
    for addr in sorted(census):
        oracle = X.xdata_space(asm, addr)
        check(f"{hexaddr(addr)} is reached as {oracle[0]} by xdata_space and by "
              f"this tool's window", rows[addr]["reach"], oracle[0])

    for row in rows.values():
        check(f"{hexaddr(row['addr'])} carries a declared verdict",
              row["verdict"] in VERDICTS, True)
        for s in row["sites"]:
            check(f"{hexaddr(s['site'])} still decodes to the seed it was "
                  f"found by", f"{image[s['site']]:02x}", "90")

    add = [r for r in rows.values() if not r["census"]]
    backed = [r for r in add if r["reach"] == "literal"]
    check("the addresses a dereferencing movx is found behind are exactly "
          "these eleven", [hexaddr(r["addr"]) for r in backed],
          ["0xFF00", "0xFF02", "0xFF04", "0xFF08", "0xFF0A", "0xFF0E", "0xFFC4",
           "0xFFCF", "0xFFD9", "0xFFDC", "0xFFDD"])
    check("and each of them carries a direction",
          sorted({r["direction"] for r in backed}),
          ["read", "read+write", "write"])
    check("and every site carrying one of those verdicts is framed at 20 of 24 "
          "or better", all(s["framed"] is None or s["framed"] >= 20
                           for r in backed for s in r["sites"]
                           if KINDS[s["verdict"]] == "literal"), True)

    # A seed no linear walk lands on is the tail of a longer instruction rather
    # than an instruction, and the one site on this tree that proves it is
    # `0xFFA3`: the `90 ff a3` at 0xCC53 is the operand of the `lcall 0x90FF`
    # at 0xCC52. Read from one byte earlier, the three bytes decode as part of
    # that call, and the site scores 0 of 24 -- so the address is reported
    # unresolved with the verdict the window would have given kept beside it.
    ffa3 = [s for r in rows.values() for s in r["sites"]
            if r["addr"] == 0xFFA3]
    check("0xFFA3's only site is the one no linear walk lands on",
          [(hexaddr(s["site"]), s["framed"], s["verdict"], s["unframed"])
           for s in ffa3],
          [("0xCC53", 0, "not-found-by-this-method", "callee-derefs")])
    check("and the byte before it starts an lcall that swallows the seed",
          [f"{image[0xCC52 + i]:02x}" for i in range(3)], ["12", "90", "ff"])
    check("so 0xFFA3 is not found by this method rather than read",
          rows[0xFFA3]["verdict"], "not-found-by-this-method")

    # The category the issue did not name, held as a claim about two named
    # routines rather than as a class: every site whose window ends where
    # nothing dereferences DPTR ends it on 0x122F or on the one-line forwarder
    # that reaches 0x122F, and nothing else.
    nonx = {s["site"]: s for r in add for s in r["sites"]
            if s["verdict"] == "callee-non-xdata"}
    check("every seed handed to a routine that never dereferences it is handed "
          "to 0x122F or to 0x7059",
          sorted({hexaddr(s["target"]) for s in nonx.values()}),
          ["0x122F", "0x7059"])
    listed_nonx = [s for s in nonx.values() if s["listing"]]
    check("of the sixteen of those a listing covers, fifteen name 0x122F and "
          "one names 0x7059",
          (len(listed_nonx),
           sum(1 for s in listed_nonx if s["target"] == 0x122F),
           [hexaddr(s["site"]) for s in listed_nonx if s["target"] == 0x7059]),
          (16, 15, ["0xB3F2"]))
    check("and 0x122F's own listing contains no movx at all",
          sum(1 for _at, m, _o in asm["122F"] if m == "movx"), 0)
    check("and 0x7059 is the single lcall that reaches it",
          [(m, o) for _at, m, o in asm["7059"]], [("lcall", "0x122f")])
    check("and the four addresses every one of whose sites lands there are "
          "these", sorted(hexaddr(r["addr"]) for r in add
                          if r["verdict"] == "callee-non-xdata"),
          ["0xFFDE", "0xFFF4", "0xFFFE", "0xFFFF"])

    # The negative controls, and the reason a suite of only positives would
    # mean nothing: a seed with no dereference behind it must come back
    # unresolved rather than borrow a neighbour's, and the boundary rules must
    # each be seen to fire.
    check("an address no seed names is not found by this method",
          X.xdata_space(asm, 0xF1FF), None)
    check("a run that ends at a branch is not chased",
          window([(0, "mov", "DPTR, #0xff00"), (3, "jz", "0x0100")], 0xFF00, 0xFF00),
          ("stop", "jz ends the window", None))
    check("a run that moves DPTR is not read past",
          window([(0, "mov", "DPTR, #0xff00"), (3, "mov", "DPH, A")], 0xFF00, 0xFF00),
          ("stop", "mov DPH, A moves DPTR", None))
    check("a second inc DPTR ends the window",
          window([(0, "mov", "DPTR, #0xff00"), (3, "inc", "DPTR"),
                  (4, "inc", "DPTR")], 0xFF00, 0xFF00),
          ("stop", "second inc DPTR", None))
    check("a movx that does not dereference the address does not end the "
          "window", window([(0, "mov", "DPTR, #0xff00"), (3, "movx", "A, @DPTR"),
                            (4, "inc", "DPTR"), (5, "movx", "A, @DPTR")],
                           0xFF01, 0xFF00), ("inc", "read", None))

    print("\n".join(ok))
    bad = [line for line in ok if line.startswith("  FAIL")]
    if bad:
        print(f"\n{len(bad)} of {len(ok)} assertions failed")
        return 1
    print(f"\nself-test passed: {len(ok)} assertions")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true",
                    help="known answers, including the negative controls")
    ap.add_argument("--notes", action="store_true",
                    help="also print every site's own reason")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    asm = X.read_asm(PD_PROGRAM)
    rows = classify(load_image(), asm)
    print(report(rows, coverage(asm)))
    if args.notes:
        print("\n  per-site reasons")
        print("\n".join(notes(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
