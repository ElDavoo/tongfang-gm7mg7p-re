#!/usr/bin/env python3
"""A region map of the main EC image by recursive descent: which bytes a walk
from the image's own entry points decodes as instructions, which it consumes as
their operands, and which it never reaches at all.

**Three verdicts, and the third state is the reason this is not the tool the
issue sketched.** `code` is a byte the walk decoded as an instruction's first
byte. `operand` is a byte the walk consumed as a later byte of an instruction
it did decode. `unreached` is a byte no walk from this seed set decoded or
consumed. The two named sites in `ec/annotations/bank-call-audit.md` 7 -- the
`0x015BA` and `0x01110` byte-scan phantoms read by hand in
`docs/findings/paged-trampoline-hits-by-hand.md` -- are the second and third
bytes of a `mov dptr,#0xC881` and of a `clr 0x91`. Under a two-state
`code`/`unreached` map they come out **`code`**: a byte scan of any kind lands
on them, and so does a descent, because they are inside instructions the
descent decodes. A third state is the only way a map of this shape can say
what the hand read says, and the third state is what `--at` prints beside the
instruction that consumed the byte.

**`unreached` means "not reached by this method", never "data".** The word is
`docs/findings.md` 4c's and it is load-bearing here: a byte can be
unreached here because no seed reaches it, because its only in-edges are edges
this walk does not follow, or because the walk stepped over it as the inline
argument block or case table of a call. `disasm8051.CASE_TABLE_CALLS` names the
one such block this image has -- the `0x7151 switch_case_dispatch` tables, whose
claim to be data is `../../docs/findings/7151-case-tables-in-the-walk.md`'s --
and this map calls their bytes `unreached`, which is not the same statement and
does not restate it. Where another method disagrees with this one, the
disagreement is recorded in `../annotations/code-map.md` and neither verdict
adjudicates the other. The PD image at `0x20000`+ is a separate program with its
own address space and is not mapped here at all.

**Coverage is a property of the seed set, not of the image.** `--seeds narrow`
(the default) seeds from the image's own vector table and from the BL51
bank-switch trampolines: the entry points a reset vector on this part reaches
without any other committed input. `--seeds wide` adds every target the three
committed call censuses name, which reaches far more of the image and is
close to circular -- a site a census row names as a call target is a seed, so
it is `code` by construction and the coverage figure flatters the method. Both
figures are printed by `--report`, both are labelled, and the committed
`../annotations/code-map.csv` is the narrow one.

**What the walk follows, and what it declines to guess.** Every edge the bytes
resolve statically: `lcall`/`ljmp` absolute, `acall`/`ajmp` paged, and the
whole PC-relative family including `sjmp` -- a conditional falls through *and*
branches, `sjmp` branches only, and `ret`/`reti` end an arm. The one indirect
edge it follows is the BL51 trampoline, and that is a decision rather than an
omission: `find_banks.find_stubs()` recovers the selected bank from the stub's
own `clr`/`setb` port writes, so the bank is read, not inferred, and the
address the trampoline carries in DPTR is exact. Issue #53 lists "the
trampoline's DPTR-carried target" among the computed-target blind spots; that is
right for a walk that does not know which stub it called and wrong for this
one. What is left unfollowed is `jmp @a+dptr` and every other register-carried
target, and those are recorded as a walk that ended, with a reason.

**Nothing here is a decode claim beyond the framing.** Every bucket-B edge --
a `>= 0x8000` target from inside a bank -- is resolved by
`trace_xdata_refs.offset_for_runtime()`'s same-bank assumption, which
`../annotations/bank-call-audit.md` 3 shows cannot be proved from the bytes.
The map inherits that assumption unchanged and does not test it. A bucket-C
target (`>= 0x8000` from the common area) resolves to nothing at all and is
counted as an unresolved seed, never guessed into a bank.

No `status:` in `../annotations/registers.yaml` moves on this, and nothing here
needs the laptop or Windows: every input is a committed file, and no live test
is claimed.

Usage:
    python3 code_map.py ../firmware/GMxMGxx_11.800
    python3 code_map.py ../firmware/GMxMGxx_11.800 --report
    python3 code_map.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/code-map.csv
    python3 code_map.py ../firmware/GMxMGxx_11.800 --check
    python3 code_map.py ../firmware/GMxMGxx_11.800 --at 0x15BA
    python3 code_map.py ../firmware/GMxMGxx_11.800 --seeds wide --at 0x15BA
    python3 code_map.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from audit_call_targets import (AUDITED, bank_switch_stubs, erased_runs,
                                region_bounds, trampolines)
from build_ec_decompile import discover_vector_table
from disasm8051 import (OPCODE_LEN, REL_OPCODES, case_table_len, inline_arg_len,
                        mnemonic, paged_target, relative_target)
from trace_xdata_refs import (PD_MARKER, REGIONS, offset_for_runtime,
                              region_of, runtime_addr)

# The map's own vocabulary, closed. `code` and `operand` are the two halves of
# a byte a walk decoded; `unreached` is the whole of what is left, and the
# module docstring is what says it means not-reached rather than data.
VERDICTS = ("code", "operand", "unreached")

# The two `code`/`unreached` questions a walk has to keep apart, and the reason
# there are three verdicts rather than two. See the module docstring.
IS_INSTRUCTION = "code"
IS_OPERAND = "operand"
NOT_REACHED = "unreached"

# The three-byte absolute transfer forms and the two-byte paged ones, split
# because they answer different questions about the walk: an `lcall` returns
# and the arm continues, an `ljmp` does not.
ABS_CALL, ABS_JUMP = 0x12, 0x02
PAGED_OPCODES = (0x01, 0x11)     # ajmp, acall -- `op & 0x1F` is the whole test

RETURNS = {0x22, 0x32}           # ret, reti -- an arm ends and falls back
COMPUTED_JUMP = 0x73             # jmp @a+dptr -- a target no descent can follow

# The edges this walk wants and cannot take, as a closed vocabulary. Each is a
# property of the *method* rather than of the bytes, and each is counted and
# printed rather than folded into the map's own verdicts: an edge the walk
# declined leaves its target's bytes `unreached`, and the reader is entitled to
# know how many such edges there were.
CUT_UNRESOLVED = "target does not resolve from this region (bucket C, or outside every mapped region)"
CUT_OFF_MAP = "target resolves outside the three audited regions"
CUT_OFF_EDGE = "instruction would take a byte from the next region"
CUT_OFF_END = "fall-through ran past the end of the region"

# Instruction budget for the whole walk. It cannot fire on a well-formed run:
# every address is decoded at most once and each region is a fixed number of
# bytes, so the walk is bounded by the image rather than by this. It is here
# so that a malformed seed set -- a cycle the visited set does not close, an
# address outside every region -- stops with a reported cut instead of running,
# and `--report` prints `cuts` so a silent cut cannot read as a finished walk.
# `docs/findings/count-bounded-walk-invariant.md` is the same argument for the
# bounded walks this repository already has.
WALK_BUDGET = 200000

# Resolved off __file__ rather than the working directory, so the gate's cwd is
# irrelevant here exactly as it is for `disasm8051.main()`'s firmware default.
ANNOTATIONS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "annotations")

# The committed run map, and the censuses the wide seed set is drawn from.
CODE_MAP_CSV = "code-map.csv"
SEED_CENSUSES = ("bank-call-targets.csv", "bank-paged-call-targets.csv",
                 "bank-relative-branch-targets.csv")

# The two sites `bank-call-audit.md` 7 names and
# `docs/findings/paged-trampoline-hits-by-hand.md` read by hand: the byte is
# the second and third byte of a `mov dptr,#0xC881` and of a `clr 0x91`, and
# the three-state map is what lets it say so. As
# (site, owning instruction, owning bytes, owning mnemonic). Both are asserted
# against the image bytes by --self-test, never by re-running the scan that
# wrote the census the sites came from. The mnemonic is written with its column
# padding squeezed, because `mnemonic()`'s padding is a rendering choice and the
# claim here is about the instruction rather than the layout -- the same reason
# `audit_call_targets.earlier_record()` squeezes it into its column.
ACCEPTANCE_SITES = (
    (0x15BA, 0x15B8, b"\x90\xc8\x81", "mov dptr,#0xc881"),
    (0x1110, 0x110F, b"\xc2\x91", "clr 0x91"),
)


class Map:
    """What one walk over one seed set decided, and how it stopped.

    `state` is `{(region, file_offset): verdict}`; `owner` is the offset of the
    instruction a byte was consumed by, for every `operand` byte -- which is
    what makes `--at` able to answer "whose operand is this" rather than only
    "is this an operand".
    """

    def __init__(self):
        self.state = {}
        self.owner = {}
        self.insns = {}
        self.cuts = {}          # region -> {reason: count}
        self.ended = {}         # region -> {why an arm stopped: count}
        self.edges = collections.Counter()
        self.seeds = {}         # region -> {basis: count}

    def note(self, region, reason) -> None:
        self.cuts.setdefault(region, {})
        self.cuts[region][reason] = self.cuts[region].get(reason, 0) + 1

    def verdict(self, region, off):
        return self.state.get((region, off), NOT_REACHED)

    def count(self, region, verdict):
        lo, hi = region_bounds(region)
        return sum(1 for i in range(lo, hi)
                   if self.state.get((region, i), NOT_REACHED) == verdict)

    def live(self, region, d):
        """Region bytes not in an erased run -- the denominator a coverage
        figure about *code* wants. `audit_call_targets.erased_runs()` is the
        same test every population in that tool is scored against, at its own
        `MIN_ERASED_RUN`, so "live" means one thing across this repository."""
        lo, hi = region_bounds(region)
        erased = sum(b - a for a, b in erased_runs(d, lo, hi))
        return hi - lo - erased


def trampoline_target(target, bank_name):
    """Where a trampoline's DPTR immediate lands in `bank_name`, or None.

    The trampoline block is the firmware's own cross-bank path and it is the
    only indirect edge this walk follows. `bank_switch_stubs()` recovers which
    bank the stub selects from the stub's own port writes, so the bank half of
    `(region, offset)` is read off the image and the address half is the
    immediate the entry already carries -- there is no arithmetic here and no
    guess. The module docstring is where that is argued against the issue's own
    list of computed-target blind spots.
    """
    toff = offset_for_runtime(target, bank_name)
    return (bank_name, toff) if toff is not None else None


def narrow_seeds(d):
    """`(region, offset)` seeds from the image's own entry points, with the
    basis for each so `--report` can say what the map was seeded from.

    Four bases, and each is discovered rather than restated:

      `vector`          the reset/interrupt vector table, walked by
                        `discover_vector_table()` rather than read off a
                        hardcoded offset list, because that function's own
                        docstring records what a hardcoded one does -- it
                        seeds the wrong addresses on an image whose table is
                        laid out differently, and the failure reads as "the
                        firmware has no handler there".
      `vector-target`   the addresses those entries point at, when they name
                        the common area. A vector target at or above `0x8000`
                        is bucket C and resolves to nothing; it is counted as
                        an unresolved seed and never placed in a bank.
      `trampoline`      the BL51 entries themselves, `audit_call_targets.
                        trampolines()` finds them by shape.
      `trampoline-target`
                        where each trampoline's DPTR immediate lands, in the
                        bank `bank_switch_stubs()` says its stub selects.
    """
    out = {}
    unresolved = 0
    lo, hi = region_bounds("common")
    for off, target in discover_vector_table(d[lo:hi]):
        out[("common", off)] = "vector"
        if target is None:
            continue
        if target < 0x8000:
            out[("common", target)] = "vector-target"
        else:
            unresolved += 1
    for entry, (bank, target) in trampolines(d, bank_switch_stubs(d)).items():
        out[("common", entry)] = "trampoline"
        placed = trampoline_target(target, ("bank0", "bank1")[bank])
        if placed is not None:
            out[placed] = "trampoline-target"
    return out, unresolved


def wide_seeds(d, seeds, annotations):
    """`narrow_seeds()` plus every target the three committed censuses name.

    **This set is close to circular and the tool says so wherever it prints a
    figure from it.** Each row of `bank-call-targets.csv` and its two siblings
    is a *target* the scan found, and a target this set seeds is a byte the walk
    then decodes as an instruction start -- so the coverage a wide run reports
    is partly the coverage of the censuses restated, not evidence that a descent
    finds those routines. It is here because "what does the descent add on top
    of what we already enumerated" is a question worth one run, and because a
    reader comparing the two figures is meant to see the gap the seed set
    leaves, not to read the wide number as this method's reach.

    A censused target is resolved against the *calling* row's region, which is
    the same same-bank assumption the censuses themselves record for bucket B
    and the same unresolvable case for bucket C.
    """
    out = dict(seeds)
    for census in SEED_CENSUSES:
        path = os.path.join(annotations, census)
        if not os.path.exists(path):
            raise SystemExit(f"error: {path} is not on disk; --seeds wide is "
                             "built from the committed censuses")
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                region = row.get("region")
                target = row.get("target")
                if not region or not target:
                    continue
                toff = offset_for_runtime(int(target, 16), region)
                if toff is None:
                    continue
                # Keyed on the region the offset is actually in, not on the
                # calling row's: a bank caller naming a common-area target seeds
                # the common area, and keying on the caller's region would file
                # it under the bank and seed the wrong bytes.
                here, _lo, _base, _how = region_of(toff, True)
                if here in AUDITED:
                    out.setdefault((here, toff), f"census:{census}")
    return out


def edge_after(d, off, region):
    """(fall-through, [branch targets], [cut reasons]) for the instruction at
    `off`. Every flow class the walk has to get right, in one place.

    Split out from `descend()` so the suite can drive it off a hand-built
    fixture -- an `ajmp` whose next PC crosses a page, a `jz` whose fall-through
    runs on past the branch, a `jmp @a+dptr` -- without a whole region around
    it. Returns the address the walk continues at (None to stop) and the
    addresses it also jumps to.

    **A resolved target's region is looked up, not assumed to be the caller's.**
    A bank0 `lcall 0x0200` names the *common* area -- `offset_for_runtime()`
    returns file offset `0x0200`, which belongs to `common`, and the common area
    is mapped in every bank, so the edge lands there and the walk continues in
    that region. Assuming the caller's region instead would refuse every
    bucket-A edge out of a bank, which is most of the common area's inbound
    calls, and would report them as cuts.
    """
    op = d[off]
    n = OPCODE_LEN[op]
    rt = runtime_addr(off, True)
    cont, targets = None, []

    def resolve(addr):
        """((region, offset), reason). `reason` is None when the edge resolves
        into one of the audited regions, and otherwise one of `CUT_*` -- a
        closed vocabulary rather than a sentence carrying the address, so a
        report is a handful of rows instead of one per unresolvable target. The
        addresses are still recoverable: every row of the three committed
        censuses that produced one is a `bucket` C row of
        `../annotations/bank-call-targets.csv`, and `--at` names one directly."""
        toff = offset_for_runtime(addr, region)
        if toff is None:
            return None, CUT_UNRESOLVED
        name, _lo, _base, _how = region_of(toff, True)
        if name not in AUDITED:
            return None, CUT_OFF_MAP
        return (name, toff), None

    cut = None
    if op in (ABS_CALL, ABS_JUMP):
        target = (d[off + 1] << 8) | d[off + 2]
        edge, cut = resolve(target)
        if cut is None:
            targets.append(edge)
        cont = off + n if op == ABS_CALL else None
    elif op & 0x1F in PAGED_OPCODES:
        target = paged_target(op, d[off + 1], rt)
        edge, cut = resolve(target)
        if cut is None:
            targets.append(edge)
        # `acall` returns and the caller carries on; `ajmp` does not.
        cont = off + n if op & 0x1F == 0x11 else None
    elif op in REL_OPCODES:
        target = relative_target(op, d[off + OPCODE_LEN[op] - 1], rt)
        edge, cut = resolve(target)
        if cut is None:
            targets.append(edge)
        # Every conditional branch falls through as well as branching; `sjmp`
        # is unconditional and does not.
        cont = off + n if op != 0x80 else None
    elif op in RETURNS or op == COMPUTED_JUMP:
        cont = None
    else:
        cont = off + n

    # The two named inline-data shapes: an argument block and a case table are
    # data in the code stream, `disasm8051`'s tables name the exact addresses
    # that carry one, and the walk steps over it and resumes on the far side
    # rather than decoding the block as instructions. Both helpers key on a
    # `lcall` target, so `skip` is only ever non-zero where `cont` is the
    # fall-through, and the resume point is `off + n + skip` either way.
    skip = inline_arg_len(d, off) + case_table_len(d, off)
    if skip:
        cont = off + n + skip

    reasons = [] if cut is None else [cut]
    if cont is not None:
        lo, hi = region_bounds(region)
        if not lo <= cont < hi:
            reasons.append(CUT_OFF_END)
            cont = None
    return cont, targets, reasons


def arm_end(d, off):
    """Why the walk stops at `off` rather than continuing, or "" when it does
    not stop. `ret`/`reti` are the ordinary end of an arm; `jmp @a+dptr` is the
    computed-target blind spot and is worth its own number, because it is the
    one edge class here that is a real transfer and is never followed."""
    op = d[off]
    if op == 0x22:
        return "ret"
    if op == 0x32:
        return "reti"
    if op == COMPUTED_JUMP:
        return "jmp @a+dptr"
    return ""


def descend(d, seeds):
    """One worklist descent over every seed at once.

    The unit of work is an address, not a routine, and an address is decoded at
    most once: the `state` map doubles as the visited set, which is what makes
    the walk terminate without a recursion limit and without re-decoding a
    shared helper once per caller. It also means a byte that is one walk's
    operand and another walk's instruction start keeps the stronger verdict --
    `code` -- and the disagreement is counted rather than hidden, because two
    walks framing the same byte differently is exactly what a reader of this
    map needs to know about.
    """
    m = Map()
    m.seeds = {}
    for (region, off), basis in seeds.items():
        m.seeds.setdefault(region, {})
        m.seeds[region][basis] = m.seeds[region].get(basis, 0) + 1
    m.insns = {region: 0 for region in AUDITED}

    pending = collections.deque(sorted(seeds))
    queued = set(pending)
    budget = WALK_BUDGET
    while pending:
        if budget <= 0:
            # The one place this walk can stop without having finished, and it
            # says so: a cut that is silent would read as a complete map.
            m.note(AUDITED[0], f"instruction budget of {WALK_BUDGET} exhausted")
            break
        budget -= 1
        region, off = pending.popleft()
        key = (region, off)
        if key in m.state and m.state[key] == IS_INSTRUCTION:
            continue                          # already decoded: a loop, not more code
        if key in m.state:
            # Decoded once as part of a longer instruction and now reached as an
            # entry point. The stronger verdict wins -- it *is* an instruction
            # start -- and the disagreement is counted, because a byte two walks
            # frame differently is a claim about this map's own consistency and
            # is reported rather than smoothed over.
            m.note(region, "framed twice: an operand byte reached as an entry point")
        lo, hi = region_bounds(region)
        n = OPCODE_LEN[d[off]]
        if off + n > hi:
            # The instruction would take a byte from the next region. Refusing
            # to read across is the discipline every loop in
            # `audit_call_targets.py` has; the arm stops and says why.
            m.note(region, CUT_OFF_EDGE)
            continue
        m.state[key] = IS_INSTRUCTION
        m.insns[region] = m.insns.get(region, 0) + 1
        for k in range(1, n):
            operand = (region, off + k)
            if m.state.get(operand) == IS_INSTRUCTION:
                m.note(region, "framed twice: instruction start and operand")
                continue
            m.state[operand] = IS_OPERAND
            m.owner[operand] = off

        stop = arm_end(d, off)
        if stop:
            m.ended.setdefault(region, {})
            m.ended[region][stop] = m.ended[region].get(stop, 0) + 1
        cont, targets, reasons = edge_after(d, off, region)
        for why in reasons:
            m.note(region, why)
        for edge in ([(region, cont)] if cont is not None else []) + targets:
            if edge not in queued:
                queued.add(edge)
                pending.append(edge)
            m.edges[edge[0]] += 1
    return m


def runs(m, region):
    """Maximal same-verdict runs over `[lo, hi)` as `(start, end, verdict)`.

    Maximal because a shorter answer would carry the same information with more
    rows: two adjacent runs of one verdict are one run, and the suite checks
    that property rather than trusting it.
    """
    lo, hi = region_bounds(region)
    out = []
    for i in range(lo, hi):
        v = m.verdict(region, i)
        if out and out[-1][2] == v:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1, v])
    return [tuple(r) for r in out]


def csv_table(m):
    """The committed `../annotations/code-map.csv`, as text.

    `region,start,end,bytes,verdict` with no comment line, so `csv.DictReader`
    reads it -- the convention `../annotations/README.md` sets out. `start` and
    `end` are file offsets, which is what `audit_call_targets.py --map-column`
    joins its rows on, and `bytes` is `end - start` carried so a reader does not
    have to subtract hex to see a run's length.
    """
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(["region", "start", "end", "bytes", "verdict"])
    for region in AUDITED:
        for start, end, verdict in runs(m, region):
            w.writerow([region, f"0x{start:05X}", f"0x{end:05X}", end - start,
                        verdict])
    return buf.getvalue()


def check_table(m, path) -> int:
    """Fail on any difference between the committed map and a fresh walk."""
    try:
        with open(path, newline="") as fh:
            committed = fh.read()
    except FileNotFoundError:
        print(f"error: {path} is not on disk", file=sys.stderr)
        return 1
    fresh = csv_table(m)
    if committed == fresh:
        print(f"  ok  {path} matches a fresh walk ({len(fresh.splitlines()) - 1} runs)")
        return 0
    diff = list(difflib.unified_diff(committed.splitlines(True),
                                     fresh.splitlines(True),
                                     path, "recomputed"))
    print("".join(diff[:40]), file=sys.stderr)
    print(f"error: {path} differs from a fresh walk; regenerate it with --csv",
          file=sys.stderr)
    return 1


def explain(d, m, off, region=None):
    """The one-byte answer `--at` prints: the verdict, and for an `operand`
    the instruction that consumed the byte."""
    if region is None:
        for name, lo, hi in ((n, *region_bounds(n)) for n in AUDITED):
            if lo <= off < hi:
                region = name
                break
    if region is None:
        return (f"0x{off:05X} is outside every audited region ({', '.join(AUDITED)})")
    verdict = m.verdict(region, off)
    if verdict != IS_OPERAND:
        return (f"0x{off:05X} ({region}) is {verdict}"
                + (" -- no walk from this seed set decodes or consumes it"
                   if verdict == NOT_REACHED else
                   " -- a walk from this seed set decodes it as an instruction"))
    owner = m.owner[(region, off)]
    span = OPCODE_LEN[d[owner]]
    raw = d[owner:owner + span]
    rt = runtime_addr(owner, True)
    text = " ".join(mnemonic(d, owner, rt).split())
    return (f"0x{off:05X} ({region}) is {verdict}: byte {off - owner} of "
            f"{span} of `0x{owner:05X} {raw.hex(' ')}` `{text}`")


def print_report(d, m, label) -> None:
    print(f"## code map, seed set: {label}")
    print()
    print("`unreached` means not reached by this method, never data. `operand`")
    print("is a byte a decoded instruction consumed, which is a third answer and")
    print("not a synonym for either of the other two.")
    print()
    print("| region | code | operand | unreached | reached, all bytes | reached, live bytes |")
    print("|---|---:|---:|---:|---:|---:|")
    for region in AUDITED:
        c = m.count(region, IS_INSTRUCTION)
        o = m.count(region, IS_OPERAND)
        u = m.count(region, NOT_REACHED)
        total = c + o + u
        live = c + o + m.live(region, d)
        print(f"| `{region}` | {c} | {o} | {u} | "
              f"{100.0 * (c + o) / total:.1f}% | "
              f"{100.0 * (c + o) / live if live else 0.0:.1f}% |")
    print()
    print("Live bytes are the region's bytes outside an erased run -- the")
    print("denominator a coverage figure about code wants, at the same")
    print("`audit_call_targets.MIN_ERASED_RUN` every population there is scored")
    print("against.")
    print()
    print("| region | seeds | instructions | edges followed | runs |")
    print("|---|---:|---:|---:|---:|")
    for region in AUDITED:
        seeds = sum(m.seeds.get(region, {}).values())
        print(f"| `{region}` | {seeds} | {m.insns.get(region, 0)} | "
              f"{m.edges.get(region, 0)} | {len(runs(m, region))} |")
    print()
    print("| region | seed basis | seeds |")
    print("|---|---|---:|")
    for region in AUDITED:
        for basis, n in sorted(m.seeds.get(region, {}).items()):
            print(f"| `{region}` | `{basis}` | {n} |")
    print()
    print("Where arms stopped, by what stopped them. `ret`/`reti` are the")
    print("ordinary end of an arm. `jmp @a+dptr` is the computed-target blind")
    print("spot: a real transfer this walk never follows, so every byte past one")
    print("is `unreached` unless another seed reaches it by another route. The")
    print("last table is the edges it wanted and could not take.")
    print()
    print("| region | " + " | ".join(sorted({k for r in AUDITED
                                              for k in m.ended.get(r, {})})) + " |")
    print("|---" * (1 + len({k for r in AUDITED for k in m.ended.get(r, {})})) + "|")
    for region in AUDITED:
        ends = m.ended.get(region, {})
        cells = [str(ends[k]) if ends.get(k) else "-" for k in
                 sorted({k for r in AUDITED for k in m.ended.get(r, {})})]
        print(f"| `{region}` | " + " | ".join(cells) + " |")
    print()
    cuts = [(region, why, n) for region in AUDITED
            for why, n in sorted(m.cuts.get(region, {}).items())]
    if cuts:
        print("| region | edge the walk declined | arms |")
        print("|---|---|---:|")
        for region, why, n in cuts:
            print(f"| `{region}` | {why} | {n} |")
    else:
        print("No arm stopped on an edge this walk declined: every edge it")
        print("resolved from a decoded instruction landed inside one of the")
        print("three audited regions, no arm ran off a region edge, and no two")
        print("arms framed the same byte differently.")
    print()


def self_test(d, annotations) -> int:
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    seeds, unresolved = narrow_seeds(d)
    m = descend(d, seeds)

    # The issue's acceptance pair, asserted against the image bytes and the
    # hand read in paged-trampoline-hits-by-hand.md -- never by re-running the
    # scan that wrote the census the two sites came from.
    for site, owner, raw, text in ACCEPTANCE_SITES:
        region = "common"
        got_owner = m.owner.get((region, site))
        got_text = " ".join(mnemonic(d, owner, owner).split())
        check(d[owner:owner + len(raw)] == raw and got_owner == owner
              and m.verdict(region, site) == IS_OPERAND and got_text == text,
              f"0x{site:04X} is the operand byte of `0x{owner:04X} "
              f"{raw.hex(' ')}` `{text}` -- image holds "
              f"`{d[owner:owner + len(raw)].hex(' ')}`, map says "
              f"{m.verdict(region, site)} owned by "
              f"{'none' if got_owner is None else '0x%04X' % got_owner}")

    # The three verdicts partition the region, and the runs are maximal.
    for region in AUDITED:
        rs = runs(m, region)
        lo, hi = region_bounds(region)
        whole = sum(e - s for s, e, _ in rs)
        joined = all(rs[i][1] == rs[i + 1][0] for i in range(len(rs) - 1))
        maximal = all(rs[i][2] != rs[i + 1][2] for i in range(len(rs) - 1))
        verdicts = {v for _, _, v in rs}
        check(rs[0][0] == lo and rs[-1][1] == hi and whole == hi - lo and joined
              and maximal and verdicts <= set(VERDICTS),
              f"{region}: {len(rs)} runs tile [0x{lo:05X},0x{hi:05X}) exactly, "
              f"maximally, in verdicts {sorted(verdicts)}")

    # The walk terminates without the budget, and says so when it fires.
    total = sum(m.insns.values())
    budget = sum(n for reasons in m.cuts.values() for why, n in reasons.items()
                 if "budget" in why)
    check(budget == 0,
          f"the walk decoded {total} instruction(s) and finished inside its "
          f"budget of {WALK_BUDGET}, so no arm ended on a budget cut")

    # Narrow seeds reach strictly less than wide ones: the seed set is
    # load-bearing, and the direction is what this asserts rather than a figure.
    wide = descend(d, wide_seeds(d, seeds, annotations))
    reached = lambda mm: sum(mm.count(r, IS_INSTRUCTION) + mm.count(r, IS_OPERAND)
                             for r in AUDITED)
    check(reached(wide) > reached(m),
          f"the wide seed set reaches strictly more than the narrow one "
          f"({reached(m)} -> {reached(wide)} bytes of code+operand), so coverage "
          "is a property of the seed set rather than of the image")

    # No region bleed -- and the asymmetry is the point of the check rather than
    # an awkwardness in it. A bank's bytes are its own: bank0 and bank1 are
    # separate windows over separate flash, so one bank's walk reaches nothing in
    # the other. The *common* area is different, and must be: it is mapped at
    # the same runtime address in every bank, so a bank0 routine calling a
    # common helper reaches that helper, and a walk that refused to cross there
    # would silently drop the largest class of inbound edges in the image.
    for seeded, foreign in (("bank0", "bank1"), ("bank1", "bank0")):
        only = descend(d, {k: v for k, v in seeds.items() if k[0] == seeded})
        reached_common = sum(only.count("common", v)
                             for v in (IS_INSTRUCTION, IS_OPERAND))
        check(all(only.verdict(foreign, i) == NOT_REACHED
                  for i in range(*region_bounds(foreign)))
              and reached_common > 0,
              f"a {seeded}-only seed set marks no {foreign} byte and does reach "
              f"the common area ({reached_common} byte(s)), which is mapped in "
              "every bank")

    # The page-alignment property the paged-edge arithmetic leans on.
    misaligned = [n for n, lo, hi, base, _ in REGIONS
                  if base is not None and ((lo - base) % 0x800 or (hi - lo) % 0x800)]
    check(not misaligned,
          "every mapped region is a whole number of 2 KiB pages aligned "
          f"identically in file offset and runtime base{'' if not misaligned else ' -- broken at ' + ', '.join(misaligned)}")

    print()
    print("self-test FAILED" if bad else "self-test passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--seeds", choices=("narrow", "wide"), default="narrow",
                    help="entry points to descend from (default: narrow, which is "
                         "what the committed map is built from)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-region run map on stdout instead of the tables")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed run map differs from a fresh walk")
    ap.add_argument("--report", action="store_true",
                    help="print the coverage, seed and blind-spot tables for both "
                         "seed sets and nothing else")
    ap.add_argument("--at", help="file offset to explain, e.g. 0x15BA")
    ap.add_argument("--self-test", action="store_true",
                    help="re-derive the acceptance pair and the map's own invariants "
                         "from the committed image")
    args = ap.parse_args()

    if not args.firmware:
        ap.error("give a firmware image, or --self-test")
    d = open(args.firmware, "rb").read()
    annotations = ANNOTATIONS
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded runs were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d, annotations)

    narrow, unresolved = narrow_seeds(d)
    chosen = narrow if args.seeds == "narrow" \
        else wide_seeds(d, narrow, annotations)

    if args.csv:
        sys.stdout.write(csv_table(descend(d, chosen)))
        return 0

    if args.check:
        return check_table(descend(d, chosen),
                           os.path.join(annotations, CODE_MAP_CSV))

    if args.at is not None:
        print(explain(d, descend(d, chosen), int(args.at, 16)))
        return 0

    if args.report:
        print_report(d, descend(d, narrow), "narrow (vectors + BL51 trampolines)")
        print("The wide seed set below adds every target the three committed")
        print("censuses name. **It is close to circular** -- a censused target")
        print("is a seed, so it is `code` by construction -- and its figures")
        print("are printed so the gap the narrow set leaves is visible, not so")
        print("the wide number can be quoted as this method's reach.")
        print()
        print_report(d, descend(d, wide_seeds(d, narrow, annotations)),
                     "wide (narrow + the committed censuses)")
        print(f"Vector targets at or above 0x8000 that the narrow seed set cannot "
              f"place: {unresolved}. They are bucket C, "
              "`offset_for_runtime()` returns None for them, and no bank is "
              "guessed for one.")
        return 0

    print_report(d, descend(d, chosen),
                 f"{args.seeds} seed set")
    return 0


if __name__ == "__main__":
    sys.exit(main())