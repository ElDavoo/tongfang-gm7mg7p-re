#!/usr/bin/env python3
"""Classify every bucket-C site -- a common-area `lcall`/`ljmp` to `>= 0x8000` --
against a code map of the common area recovered by recursive descent, so the
140 sites `audit_call_targets.py` enumerates stop being one undifferentiated
population and start being three named ones.

**What this settles and what it does not.** A bucket-C target is genuinely
unresolvable from the bytes: `REGIONS` gives bank0 and bank1 the same base
`0x8000`, so `offset_for_runtime()` correctly returns `None` and this tool does
not change that. What *is* resolvable is the **site** -- whether the opcode byte
the census found sits on an instruction boundary this walk decoded, or inside
a table the walk never entered, or in a place the walk could not decide. That
is a question about the common area alone, and the common area has one
address space, so a code map answers it where a bank overlay cannot.

**The seed set, and why every element's code-ness is not in question.** Four
bases, all discovered rather than restated, and sorted so two branches produce
the same table:

  `vector-target`     the targets the image's own vector table points at, found
                      by `build_ec_decompile.discover_vector_table()` walking
                      the image. Discovered rather than hardcoded because that
                      function's docstring records what a hardcoded list does:
                      it silently seeds the wrong addresses on the PD image,
                      and the failure then reads as "the firmware has no handler
                      there".
  `stub`              the four BL51 bank-switch stubs at
                      `0x1100`/`0x1114`/`0x1128`/`0x113C`, whose
                      `C0 08 74` prologue `audit_call_targets.py --self-test`
                      counts four of in this image and zero of in the PD one.
  `trampoline`        the 403 entries `audit_call_targets.trampolines()` finds
                      by shape -- `90 hi lo 02 11 xx` -- which is the same
                      framing `find_banks.py` keys on and which the same
                      self-test pins as one unbroken 6-byte-stride run.
  `bank-call-target`  every distinct `target < 0x8000` a `bank-call-targets.csv`
                      row in a bank names. **This base inherits the census's own
                      framing caveat in full** (`bank-call-audit.md` §1: a byte
                      scan is an upper bound, and the anchored subset is
                      demonstrably not phantom-free). It is a seed because the
                      question is the reverse of the census's -- "is a name the
                      scan produced a real entry" is precisely what this walk
                      asks -- but a seed drawn from an upper bound can seed a
                      phantom, and `walk_reason` is where that shows.

**The walk is `walk_branch_arms.descend()` with a worklist above it.**
`descend()` is the repository's only reusable descent primitive and it does not
recurse into a call: it records an `lcall`/`acall` as a callee and walks on,
and it ends the arm at an `ljmp`/`ajmp` after recording that too. So the entry
points those callees name belong to the caller -- which is exactly the
arrangement `bank_attribution.closure()` already demonstrates over the same
function, one region further up. `bank_attribution.closure()` is also the
reason this is a new file rather than a mode on it: it hard-refuses to descend
below `0x8000` (`BANK_FLOOR`), which *is* the gap this tool fills.

**Three verdicts, and the third is the honest one.** `reached-by-walk` means the
site offset is an instruction boundary inside a span this walk decoded from
this seed set. `not-reached` means it is outside every such span *and* the walk
stopped for a reason that decided the question -- a `ret`, a tail jump, a
byte the walk decoded over, a table it never entered. `unknown` is the cell for
a walk that could not decide: a computed `jmp @a+dptr`, the instruction budget,
the transfer depth, the end of the image, a **branch out of the common area
into a bank window** (`bank-edge-jump`, 31 descents stop on it in this image),
or an end this tool does not recognise. A third value exists so that "this
method gave up here" is a reported outcome with a reason next to it rather than
a silent drop into the same column as a real negative.

**What a verdict is not.** `not-reached` is not "is a data table", and
`reached-by-walk` is not "is a call": a flow walk cannot distinguish code from a
table it wandered into, and `bank_attribution.py` and `disasm8051.py` both say
so in their own module docstrings. Every count this tool prints is a count *of
this walk from this seed set*. A zero anywhere is "not found by this method",
never "absent" -- the `registers.yaml` caveat, and `docs/findings.md` §4c.

**Three membership columns, reported against each other and not reconciled.**
`in_data_region` is `data_regions.region_at()`'s answer and is a *label*, never
a filter: a site inside a table is still classified, and a site outside every
listed table is not thereby a call. `in_ghidra_function` is membership in a
`[addr, addr+size)` from a `common` row of `ec/decompiled/index.csv` -- an
independent second opinion, from a boundary set this walk never saw. Where the
two disagree with each other or with the walk, the write-up reports the
disagreement and does not pick a winner.

Nothing here measures the byte. No register is read, no capture was opened, no
`status:` in `registers.yaml` moves, and nothing needs hardware or Windows.

Usage:
    python3 bucket_c_codemap.py ../firmware/GMxMGxx_11.800
    python3 bucket_c_codemap.py ../firmware/GMxMGxx_11.800 --check
    python3 bucket_c_codemap.py ../firmware/GMxMGxx_11.800 --csv > codemap.csv
    python3 bucket_c_codemap.py ../firmware/GMxMGxx_11.800 --spans > spans.csv
    python3 bucket_c_codemap.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import bisect
import collections
import csv
import difflib
import io
import os
import sys

from audit_call_targets import (erased_runs, region_bounds, survey,
                                trampolines)
from build_ec_decompile import BANK_STUBS, discover_vector_table
from data_regions import load as load_data_regions, region_at
from disasm8051 import FLOW_OPCODES, OPCODE_LEN, mnemonic
from trace_xdata_refs import PD_MARKER, REGIONS
from walk_branch_arms import (CUTS, END_BUDGET, END_DEPTH, END_IMAGE, END_INDIRECT,
                              END_LOOP, END_RET, END_RETI, END_TAIL, REL_BRANCHES,
                              descend)

# Bounds for one descent. Both are named rather than inlined so a run that
# stopped on either says which, and so a case in the suite can move one without
# repeating the other. The instruction budget is a budget on *work*, not a bound
# on the buffer: whichever end actually stopped a descent is reported, because
# "ran out of instructions" and "ran out of image" are different claims about the
# same routine (docs/findings/count-bounded-walk-invariant.md).
SEED_BUDGET = 2000
TRANSFER_DEPTH = 12

# Seed bases in the order they are named in a row. Sorting is by (address,
# basis), so a base that is also an entry point of another base reports the
# first by this order rather than by whichever walk happened to reach it first
# -- the walk order is a BFS, so it is not a stable answer to "why this one".
SEED_BASES = ("vector-target", "stub", "trampoline", "bank-call-target")

# The two regions a seed may name, and the only two a bucket-C census row can
# have as its caller: `common` for the sites themselves, and a bank for the
# targets those sites' callers reach. Written as a set of REGIONS names rather
# than a "starts with bank" test because REGIONS is the source of truth for what
# is mapped, and a fourth bank region should have to be added here.
BANK_REGIONS = frozenset(name for name, _, _, _, _ in REGIONS
                         if name.startswith("bank"))

# `walk_reason`, as a closed vocabulary. A reason outside this set is a bug in
# this tool rather than a cell to render, so classify() refuses it; a table
# whose reason column can hold an unbounded number of shapes is a column nobody
# can grep.
#
# `reached` is the only member that goes with `reached-by-walk`. The next three
# are how the walk says a byte is not an instruction: it decoded straight over
# it, there is no seed anywhere near it, or the bytes are an erased run. The
# next four are terminators the walk *decided* on, so they make a site
# `not-reached`. The last six are the ones it could not see past -- a computed
# jump, the budget, the depth, the image, an instruction the buffer does not
# hold whole, and an end this tool does not recognise -- and those make a site
# `unknown`.
#
# There is deliberately no "a branch led elsewhere" member. It looks like the
# one that should be here, and it is unreachable: `descend()` walks a
# PC-relative branch's fall-through inside the same block, so the nearest
# decoded instruction below a gap is never a branch, and a block that does end
# on one did so because a cut fired at it -- which the cut rule below reports
# instead, and which is a different claim about the same byte.
# A transfer whose target is in a bank window, so the bytes are not in this
# walk's address space at all. `descend()` reaches it when a branch target
# fails `offset_for_runtime()` for the `common` region, and it is the same
# unresolvability this whole tool is about seen from the other side: nothing in
# the bytes says which bank is mapped, so the walk stops rather than picking
# one. Its own reason because it is a *transfer out of the region* rather than a
# terminator inside it, and because it is the one class here with a settled
# name already -- `audit_call_targets.py` section 6 counts the same escapes.
BANK_EDGE = "bank-edge-jump"

# An end this tool does not recognise. `descend()` also records notes that are
# not terminators at all -- "DPTR built at run time (a store to DPL/DPH)" is
# one, and the walk continues past it -- so this third shape exists to keep
# them visible. They are reported as their own cell, which makes a site
# `unknown` because the walk did not say why it stopped, rather than silently
# folded into a real terminator. The suite pins the count at zero on the
# committed image, so an end added upstream is a red run rather than a cell
# somebody finds in the table.
UNCLASSIFIED = "unclassified-end"

WALK_REASONS = frozenset({
    "reached", "mid-instruction", "no-seed-nearby", "erased-run",
    "ret", "reti", "tail-jump", "loop", "no-control-flow",
    "indirect-jump", "instruction-budget", "depth-limit", "end-of-image",
    "undecodable-byte", BANK_EDGE, UNCLASSIFIED,
})

# The terminators `descend()` records, mapped to the cell each becomes. The
# three cut reasons are not a set of constants of their own because
# `descend()` builds them by formatting an address into the string -- the
# address is what lets a cut be told apart from an ordinary terminator, so the
# address is parsed back out rather than pattern-matched away.
CUT_TOKENS = {
    END_BUDGET: "instruction-budget",
    END_DEPTH: "depth-limit",
    END_IMAGE: "end-of-image",
}
PLAIN_TOKENS = {
    END_RET: "ret",
    END_RETI: "reti",
    END_TAIL: "tail-jump",
    END_INDIRECT: "indirect-jump",
}

# A `descend()` end that is one of these means the walk gave up rather than
# finished. It is the module's own `CUTS`, re-read here rather than restated,
# and the two halves are kept apart for the reason `walk_branch_arms` keeps them
# apart: a `loop` is not a cut (the arm is fully explored, it comes back round),
# and `end-of-image` is (the arm stopped at the first address it could not
# read, and that is not a result).
GAVE_UP = frozenset(CUTS)

# Reasons that make a site `unknown`. Everything else that is not `reached` is a
# negative the walk decided, which is the whole difference between the two
# non-reached verdicts.
UNKNOWN_REASONS = frozenset({
    "indirect-jump", "instruction-budget", "depth-limit", "end-of-image",
    "undecodable-byte", BANK_EDGE, UNCLASSIFIED,
})

# The three verdicts. `verdict_for()` refuses a fourth rather than rendering it:
# a closed column is what makes a count of it mean something, and a new value
# appearing in a CSV is a change to a claim rather than a new row.
REACHED = "reached-by-walk"
NOT_REACHED = "not-reached"
UNKNOWN = "unknown"
VERDICTS = (REACHED, NOT_REACHED, UNKNOWN)

# The CSV. Columns 1-8 are `bank-call-targets.csv`'s own, in its own spelling,
# so the two files join on `file_offset` and `--check` can re-derive the shared
# eight from the census rather than trusting the committed copy: a drift between
# the two files is a red run instead of a stale row.
CSV_HEAD = ["file_offset", "runtime", "opcode", "target", "bucket", "frame_onto",
            "frame_over", "in_data_region", "in_ghidra_function", "walk_verdict",
            "walk_reason", "containing_function", "target_is_trampoline_entry"]

DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"
DEFAULT_CSV = "../annotations/bucket-c-codemap.csv"
DEFAULT_INDEX = "../decompiled/index.csv"
NOT_LISTED = "not listed"
NOT_A_FUNCTION = "no"


# --- the census this tool reads, never edits ---------------------------------

def bucket_c_rows(d: bytes):
    """[(row, ...)] for the bucket-C sites, in file-offset order.

    `audit_call_targets.survey()` is *run*, not reimplemented: the census
    belongs to another issue's tool, its 140/83 figures are what every other
    file quotes, and a second enumeration in this file is a second answer to
    their question. Sorted by `file_offset` so the CSV and the tool's stdout
    cannot disagree on row order between two runs.
    """
    rows, _, _ = survey(d)
    return sorted((r for r in rows if r["bucket"] == "C"),
                  key=lambda r: r["file_offset"])


def common_targets_from_banks(d: bytes) -> set:
    """The distinct `target < 0x8000` a bank-region census row names.

    This is the `bank-call-target` seed base, and it is read off the **whole**
    census rather than off the bucket-C rows this tool classifies: a bank-side
    call naming a common-area address is bucket A from that caller's side, and
    restricting to bucket C would ask a population that by definition contains
    no common-area targets to name one.

    It is *not* filtered to anchored rows. The issue's phrase is "every
    common-area target already reached from an anchored bank-side call", and
    reading it that way is what makes the question circular -- a site is
    reached because the scan named it, and then the walk is reported to have
    reached it, which says nothing. Taken whole, the population is the census's
    upper bound, and the caveat is inherited and stated in the write-up rather
    than assumed away.
    """
    rows, _, _ = survey(d)
    return {r["target"] for r in rows
            if r["region"] in BANK_REGIONS and r["target"] < 0x8000}


def seed_set(d: bytes) -> list:
    """[(address, basis)] for every common-area entry point to walk from.

    Sorted by (address, basis rank), deduped on address keeping the strongest
    basis. The bases overlap -- most of the common-area addresses a bank-side
    call names are trampoline entries, and the trampoline block is a
    dispatcher over the common area -- so the bases are counted in the report
    by what each *contributed* after the stronger ones, not before. Bank-side
    targets are filtered to the common area here rather than inside `walk()`,
    so the refusal a case checks -- a seed outside the common area -- is one
    the walk itself makes and one the seed builder cannot launder.
    """
    _, _, tramp = survey(d)
    raw = {t: "vector-target"
           for _, t in discover_vector_table(d[:region_bounds("common")[1]])
           if t is not None and t < 0x8000}
    for addr in BANK_STUBS:
        raw.setdefault(addr, "stub")
    for addr in tramp:
        raw.setdefault(addr, "trampoline")
    for target in common_targets_from_banks(d):
        raw.setdefault(target, "bank-call-target")
    rank = {basis: i for i, basis in enumerate(SEED_BASES)}
    return sorted(raw.items(), key=lambda ab: (ab[0], rank[ab[1]]))


# --- the walk ---------------------------------------------------------------

class Descent:
    """One entry point's descent: the blocks it decoded and how it ended.

    `cuts` are the ends that carry an address, kept parsed so a site can be
    told "the budget ran out at 0x1A2B" from "the budget ran out somewhere
    else in this descent". `descend()` formats the address into the string
    because its caller is a human reading a listing; here it is the difference
    between two verdicts.
    """

    def __init__(self, basis):
        self.basis = basis
        self.blocks = []            # [(lo, [instruction pcs], last opcode)]
        self.cuts = []              # [(pc, token)] a cut stopped the walk at
        self.terminal = "no-control-flow"

    def add_cut(self, pc, token):
        self.cuts.append((pc, token))

    def block_of(self, pc):
        """The block whose instruction list contains `pc`, else None."""
        for lo, pcs, _ in self.blocks:
            if pc in pcs:
                return lo, pcs
        return None


# `_op_at` above cannot close over the image without threading it through every
# caller, and the byte a block covers is the byte in the image -- the `common`
# region's file offset and its runtime address are the same number, which is
# what makes the fixture-based cases in the suite address-relative at all. So
# the lookup is a module-level helper over the image rather than a method.
def opcode_at(d: bytes, pc: int) -> int:
    return d[pc] if 0 <= pc < len(d) else None


def split_cut(end: str):
    """("instruction budget", 0x1A2B) for a `CUTS` end, else (end, None).

    Strict on purpose. `descend()` formats the address as ` at 0xNNNN` onto
    the end it already had, so the whole suffix after the separator is the
    address and nothing else -- and a looser split that kept the separator, or
    took the first four characters of the remainder, would leave a prefix no
    key in `CUT_TOKENS` matches. That failure is quiet: the end is real, the
    walk really did stop there, and the cell says `unclassified-end` and the
    site says `unknown`, which is a worse answer than the right one rather than
    an obviously broken one.
    """
    head, sep, tail = end.rpartition(" at 0x")
    if not sep or head not in CUT_TOKENS:
        return end, None
    if len(tail) != 4 or any(c not in "0123456789abcdefABCDEF" for c in tail):
        return end, None
    return head, int(tail, 16)


def token_for_ends(ends):
    """[(address or None, token)] for every end `descend()` recorded.

    The three `CUTS` are parsed for the address they carry, because that
    address is what separates "the budget ran out at 0x1A2B" from a terminator
    two blocks away. The four plain terminators and the loop map straight
    through. Everything else becomes `UNCLASSIFIED` rather than being dropped
    or folded into a real terminator: `descend()` records notes that are not
    terminators at all, and a note the walk continued past must not decide a
    verdict.
    """
    out = []
    for end in ends:
        head, addr = split_cut(end)
        token = CUT_TOKENS.get(head)
        if token:
            out.append((addr, token))
        else:
            plain = PLAIN_TOKENS.get(end)
            if plain:
                out.append((None, plain))
            elif end.startswith(END_LOOP):
                out.append((None, "loop"))
            elif end.endswith("runs past the end of the image"):
                out.append((None, "undecodable-byte"))
            elif end.endswith("is not reachable from region common"):
                out.append((None, BANK_EDGE))
            else:
                out.append((None, UNCLASSIFIED))
    return out


def walk(d: bytes, seeds, max_insns=SEED_BUDGET, max_depth=TRANSFER_DEPTH):
    """({pc: (entry, basis)}, {entry: Descent}) for a whole common-area walk.

    The worklist is the part `descend()` does not do. It records an
    `lcall`/`acall` as a callee and an `ljmp`/`ajmp` as a tail call and in both
    cases ends, so the entry points those name are this function's business; a
    callee is pushed and walked from its own entry with a fresh, unknown DPTR,
    because a callee inherits the caller's pointer and that value is not
    carried across.

    Seeds are consumed in the order given and a `pc` is attributed to the first
    descent that decoded it, which is why `seed_set()` sorts: the attribution in
    the `containing_function` column is then a function of the seed set and not
    of the traversal.
    """
    if max_insns < 1:
        raise SystemExit("error: --max-insns must be at least 1; a budget of "
                         f"{max_insns} cannot be honoured, and a walk that "
                         "cannot run is not a zero result")
    lo, hi = region_bounds("common")
    reached = {}
    descents = {}
    work = list(seeds)
    while work:
        entry, basis = work.pop(0)
        if entry in descents or not lo <= entry < hi:
            continue
        arm = descend(d, "common", entry, None, max_depth, max_insns, True)
        rec = Descent(basis)
        for start, block in arm.blocks:
            pcs = [pc for pc, _ in block]
            rec.blocks.append((pcs[0], pcs, opcode_at(d, pcs[-1])))
            for pc in pcs:
                reached.setdefault(pc, (entry, basis))
        rec.terminal = terminal_token(arm.ends)
        for addr, token in token_for_ends(arm.ends):
            if addr is not None:
                rec.add_cut(addr, token)
        descents[entry] = rec
        for callee in arm.callees:
            if lo <= callee < hi and callee not in descents:
                work.append((callee, "call-from-0x%04X" % entry))
    return reached, descents


def terminal_token(ends) -> str:
    """The token a descent's *last* end becomes, for a site past its frontier.

    `descend()`'s ends accumulate across the whole arm, so this is the last one
    recorded -- the terminator the walk finished on, which is the one adjacent
    to a byte just past the frontier. A loop is deliberately not a cut: an arm
    that cycles has been fully explored, and reporting `unknown` for the byte
    after one would understate what was read.
    """
    tokens = [t for _, t in token_for_ends(ends)]
    gave_up = [t for t in tokens if t in GAVE_UP]
    if gave_up:
        return gave_up[-1]
    # A note the walk continued past is not a terminator, so the *last
    # terminator* is the answer, not the last string. Reading it the other way
    # labelled 2 of this image's 950 descents `unclassified-end` for having
    # stored through DPTR at some point, which is not a fact about how they
    # ended at all.
    terminators = [t for t in tokens if t != UNCLASSIFIED]
    return terminators[-1] if terminators else UNCLASSIFIED


def terminator_token(op) -> str:
    """What the last instruction of a block says about the bytes after it.

    Read off the opcode rather than off `descend()`'s end string, because the
    end string is recorded for the arm and this is a question about one block.
    A PC-relative branch is the interesting case: the walk followed it to a
    target and decoded that, so the bytes between this block and the next are
    bytes execution did *not* reach, and the site is a negative rather than a
    gap the walk failed to close.
    """
    if op is None:
        return "undecodable-byte"
    if op in (0x22,):
        return "ret"
    if op in (0x32,):
        return "reti"
    if op in (0x02, 0x80) or op & 0x1F == 0x01:
        return "tail-jump"
    if op == 0x73:
        return "indirect-jump"
    if op in REL_BRANCHES:
        return "gap-after-block"
    return "no-control-flow"


# --- classification ---------------------------------------------------------

def flow_disposition(op: int) -> str:
    """What the walk does with a flow opcode: `call`, `follow`, or a reason.

    Closed over `disasm8051.FLOW_OPCODES` -- the table the rest of this
    repository reads for exactly this question, rather than a range written
    here. Writing `0xB4 <= op <= 0xDF` looks equivalent and is not, and
    `walk_branch_arms` says why at the definition of `REL_BRANCHES`: the
    carry-flag opcodes sit in the middle of that range, and treating them as
    branches resolves a "target" out of the following byte. A new member of
    `FLOW_OPCODES` is refused here rather than rendered as a fourth disposition
    nobody has reasoned about.
    """
    if op not in FLOW_OPCODES:
        raise SystemExit(f"error: opcode 0x{op:02X} is not in "
                         "disasm8051.FLOW_OPCODES, so it is not a terminator")
    if op in (0x22, 0x32, 0x73, 0x02, 0x80) or op & 0x1F == 0x01:
        return terminator_token(op)
    if op in (0x12,) or op & 0x1F == 0x11:
        return "call"
    return "follow"


DISPOSITIONS = ("call", "follow", "ret", "reti", "tail-jump", "indirect-jump")


def verdict_for(reason: str) -> str:
    """The verdict a `walk_reason` becomes. A fourth is refused, not rendered."""
    if reason not in WALK_REASONS:
        raise SystemExit(f"error: {reason!r} is not a member of WALK_REASONS; a "
                         "walk_verdict is a count of three and a fourth makes "
                         "the count mean nothing")
    if reason == "reached":
        return REACHED
    return UNKNOWN if reason in UNKNOWN_REASONS else NOT_REACHED


class Codemap:
    """The three questions one site is asked, and the answers kept together."""

    def __init__(self, d, reached, descents, covered, erased):
        self.d = d
        self.reached = reached
        self.descents = descents
        self.covered = covered
        self.erased = erased
        self.sorted_pc = sorted(reached)

    def reason_for(self, off: int):
        """(reason, seed) for one bucket-C site offset.

        The order of the questions is the order of how much each answer tells
        you. The walk reached it -- nothing else matters. The bytes are an
        erased run -- that is a statement about the bytes, whatever the walk
        did. The walk decoded straight over it -- that is what a phantom is, and
        it is the strongest thing this tool can say against a site. Otherwise
        the site sits in a gap, and the reason is the terminator of the nearest
        block below it, which is a *decided* gap unless that terminator is one
        the walk could not see past.

        The second element is always a **seed** address, never an instruction
        address: it is what the `containing_function` column names, and a
        column that mixed the two would read as a claim about a routine when it
        is a claim about where the walk started. `None` means this walk
        produced nothing to name.
        """
        if off in self.reached:
            return "reached", self.reached[off][0]
        if off in self.erased:
            return "erased-run", None
        if off in self.covered:
            return "mid-instruction", self.reached[self.covered[off]][0]
        i = bisect.bisect_left(self.sorted_pc, off)
        if i == 0:
            return "no-seed-nearby", None
        below = self.sorted_pc[i - 1]
        entry = self.reached[below][0]
        return self._block_reason(entry, below, off), entry

    def _block_reason(self, entry, pc, site):
        """The token for the bytes between `pc` and `site` in `entry`'s descent.

        A cut between them wins over the opcode at `pc`, and that ordering is
        the whole point. A block can only end on a PC-relative branch if the
        walk was stopped there -- a budget or an image end -- so reading the
        branch's own opcode would report a *decided* gap where in fact nothing
        was decided, and `not-reached` is exactly the claim this column must not
        overstate. The address `descend()` formats into its cut string is what
        makes the two tellable apart, which is why `Descent.cuts` keeps it
        rather than a boolean.
        """
        rec = self.descents[entry]
        for addr, token in rec.cuts:
            if addr is not None and pc <= addr <= site:
                return token
        found = rec.block_of(pc)
        if found is None:
            return rec.terminal
        return terminator_token(self.d[pc])

    def verdict(self, off):
        reason, _ = self.reason_for(off)
        return reason, verdict_for(reason)


def erased_index(d: bytes) -> set:
    """Every byte inside a run of at least `MIN_ERASED_RUN` 0xFF bytes.

    `audit_call_targets.MIN_ERASED_RUN` is 16 and not 1 for a reason its own
    comment gives: 0xFF is `mov r7,a`, one of the commonest bytes in Keil C51
    output, so a one-byte test would call ordinary code erased. Reused rather
    than re-decided so the two files cannot disagree about what "erased" means.
    """
    out = set()
    for start, stop in erased_runs(d, *region_bounds("common")):
        out.update(range(start, stop))
    return out


def covered_index(d: bytes, descents) -> dict:
    """{byte: owning instruction pc} across every descent.

    A site landing in this map was decoded *over*: it is an operand byte of an
    instruction the walk produced, not the first byte of one. That is a
    stronger statement than "not reached" and it is the answer the census's
    over-count needs, so it is a reason of its own rather than a variant of
    `not-reached`.
    """
    out = {}
    for rec in descents.values():
        for lo, pcs, _ in rec.blocks:
            for pc in pcs:
                for step in range(1, OPCODE_LEN[d[pc]]):
                    out[pc + step] = pc
    return out


def ghidra_functions(index_path: str = None):
    """{addr: (end, name)} for every `common` row of `ec/decompiled/index.csv`.

    The boundary set Ghidra committed, read as the independent second opinion
    the write-up compares against. The `common` rows only: a bank row is
    `[addr, addr+size)` in a bank window, which is a different address space
    from the one this walk decoded.
    """
    out = {}
    path = index_path or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      DEFAULT_INDEX)
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("program") or "").strip() != "common":
                continue
            try:
                addr = int(row["addr"], 16)
                size = int(row["size"])
            except (KeyError, TypeError, ValueError):
                continue
            out[addr] = (addr + size, (row.get("name") or "").strip())
    return out


def containing_function(functions, off: int) -> str:
    """The Ghidra function `off` falls inside, or `no`."""
    lo, hi = region_bounds("common")
    for addr in sorted(functions):
        end, name = functions[addr]
        if addr <= off < end:
            return f"0x{addr:04X} {name}" if name else f"0x{addr:04X}"
    return NOT_A_FUNCTION


def build(d: bytes, index_path: str = None):
    """Everything one run needs: the rows, the walk, the census, the map."""
    rows = bucket_c_rows(d)
    seeds = seed_set(d)
    reached, descents = walk(d, seeds)
    covered = covered_index(d, descents)
    codemap = Codemap(d, reached, descents, covered, erased_index(d))
    _, _, tramp = survey(d)
    known = {t for _, t in tramp.values()}
    functions = ghidra_functions(index_path)
    regions = load_data_regions()
    return rows, seeds, reached, descents, codemap, known, functions, regions


def csv_text(d: bytes, index_path: str = None) -> str:
    """The whole classification as CSV text, from the image.

    Written to a string rather than to a file so `--check` can diff it against
    the committed copy and `--csv` can hand it to stdout: this tool writes no
    committed file, which is the arrangement `data_regions.py` and
    `rank_common_runtime.py` use.
    """
    rows, seeds, reached, descents, codemap, known, functions, regions = build(
        d, index_path)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_HEAD)
    for r in rows:
        off = r["file_offset"]
        reason, entry = codemap.reason_for(off)
        verdict = verdict_for(reason)
        region = region_at(regions, off)
        w.writerow([
            f"0x{off:05X}", f"0x{r['runtime']:04X}", r["opcode"],
            f"0x{r['target']:04X}", r["bucket"], r["frame_onto"],
            r["frame_over"],
            region["name"] if region else NOT_LISTED,
            containing_function(functions, off),
            verdict, reason,
            f"0x{entry:04X} ({codemap.descents[entry].basis})" if entry is not None else "",
            "yes" if r["target"] in known else "no",
        ])
    return buf.getvalue()


# --- reporting --------------------------------------------------------------

def histogram(codemap, off_list):
    """`{reason: count}` over the sites, in `WALK_REASONS` declaration order."""
    counts = collections.Counter()
    for off in off_list:
        counts[codemap.reason_for(off)[0]] += 1
    return counts


def base_populations(d):
    """{basis: how many addresses the base names}, before the dedup.

    Reported beside the contributed counts because the bases overlap heavily and
    the overlap is the interesting part: most of the common-area addresses a
    bank-side call names are trampoline entries, so a base showing a small
    contribution is not a base with a small population. It is a base the
    stronger ones already had.
    """
    _, _, tramp = survey(d)
    return {
        "vector-target": len({t for _, t in
                              discover_vector_table(d[:region_bounds("common")[1]])
                              if t is not None and t < 0x8000}),
        "stub": len(BANK_STUBS),
        "trampoline": len(tramp),
        "bank-call-target": len(common_targets_from_banks(d)),
    }


def print_report(d, rows, seeds, descents, codemap, known, functions, regions):
    """The plain run: the seed set, the counts, the budget, the one target."""
    contributed = collections.Counter(basis for _, basis in seeds)
    populations = base_populations(d)
    print(f"## 1. The seed set: {len(seeds)} common-area entry point(s)")
    print()
    print("| base | names | contributes |")
    print("|---|---:|---:|")
    for basis in SEED_BASES:
        print(f"| `{basis}` | {populations.get(basis, 0)} "
              f"| {contributed.get(basis, 0)} |")
    print(f"| **the seed set** | | **{len(seeds)}** |")
    print()
    print(f"Spanning 0x{seeds[0][0]:04X}-0x{seeds[-1][0]:04X}. A base contributing")
    print("fewer than it names is not a smaller population: the stronger bases")
    print("already held those addresses, which is most of what a bank-side call")
    print("names, since the trampoline block is itself a dispatcher over the")
    print("common area. `bank-call-target` is the census's upper bound rather than")
    print("its anchored subset, and it inherits bank-call-audit.md 1's framing")
    print("caveat whole.")
    print()

    offs = [r["file_offset"] for r in rows]
    counts = histogram(codemap, offs)
    verdicts = collections.Counter(codemap.verdict(o)[1] for o in offs)
    print(f"## 2. The {len(offs)} bucket-C sites, classified")
    print()
    print("| verdict | sites | meaning |")
    print("|---|---:|---|")
    meaning = {
        REACHED: "on an instruction boundary this walk decoded",
        NOT_REACHED: "outside every reached span, and the walk decided it",
        UNKNOWN: "outside every reached span, and the walk could not decide",
    }
    for v in VERDICTS:
        print(f"| `{v}` | {verdicts.get(v, 0)} | {meaning[v]} |")
    print()
    print("By reason. `reached` is the only member of the first kind; the rest")
    print("are how a site came out, and every one of them is a count of *this*")
    print("walk from *this* seed set:")
    print()
    for reason in sorted(counts):
        print(f"  {reason:<20} {counts[reason]}")
    print()
    print("A zero in that table is \"not found by this method\", never \"absent\".")
    print("`not-reached` is not \"is a data table\" and `reached-by-walk` is not")
    print("\"is a call\": a flow walk cannot tell code from a table it wandered")
    print("into. So the three membership columns are reported against each")
    print("other and none of them is allowed to decide a verdict:")
    print()
    seed_offs = {a for a, _ in seeds}
    print("| reason | sites | in a listed data region | in a Ghidra function | is a seed |")
    print("|---|---:|---:|---:|---:|")
    for reason in sorted(counts):
        sel = [o for o in offs if codemap.reason_for(o)[0] == reason]
        print(f"| `{reason}` | {len(sel)} "
              f"| {sum(1 for o in sel if region_at(regions, o))} "
              f"| {sum(1 for o in sel if containing_function(functions, o) != NOT_A_FUNCTION)} "
              f"| {sum(1 for o in sel if o in seed_offs)} |")
    print()
    reached_offs = [o for o in offs if codemap.verdict(o)[1] == REACHED]
    both = sum(1 for o in reached_offs
               if region_at(regions, o) or o in seed_offs)
    print(f"  {both} of the {len(reached_offs)} reached site(s) sit inside a span")
    print("  data-regions.yaml lists as a table, or are a seed this walk was given.")
    print("  A seed is circular here by construction: a site the census named")
    print("  cannot then be evidence that the census found a real entry. The")
    print("  write-up reports that rather than resolving it.")
    print()

    print("## 3. Which end stopped the walk")
    print()
    tokens = collections.Counter(rec.terminal for rec in descents.values())
    for token, n in sorted(tokens.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {token:<20} {n} descent(s)")
    print()
    print("`instruction-budget` and `end-of-image` are different claims about the")
    print("same routine, so they are separate rows rather than one \"stopped\".")
    print()

    targets = {r["target"] for r in rows}
    shared = sorted(targets & known)
    print("## 4. The one bucket-C target a trampoline also names")
    print()
    print(f"  {len(shared)} of the {len(targets)} distinct bucket-C targets is/are")
    print("  also an entry `audit_call_targets.trampolines()` found by shape.")
    for t in shared:
        named = [(e, bank) for e, (bank, tg) in tramp_for(d) if tg == t]
        print()
        print(f"  0x{t:04X}, named by {len(named)} trampoline entr"
              + ("y" if len(named) == 1 else "ies") + ": "
              + ", ".join(f"0x{e:04X} (routes to bank {bank})"
                          for e, bank in named))
        for off in [r["file_offset"] for r in rows if r["target"] == t]:
            reason, entry = codemap.reason_for(off)
            print(f"  bucket-C site 0x{off:05X}: {codemap.verdict(off)[1]}"
                  f" ({reason})")
        for bank, off_file in ((0, 0x08000), (1, 0x10000)):
            print(f"  bank {bank} @ 0x{t:04X}: {decode_bank(d, t, off_file)}")
    print()
    print("The bank the trampoline names is the linker's own answer to which")
    print("bank holds code at the target. It is reported because it is evidence,")
    print("not because it settles the site: a byte scan does not say which bank")
    print("is mapped when the common area runs, and that is the whole of §4c.")
    print()
    print("Two decoders, kept apart on purpose: the lines above are this")
    print("repository's decoder on the committed image, and the `r2 -a 8051`")
    print("transcripts for the same bytes are in the write-up. Neither is")
    print("arbitrated by the other here.")
    print()


def tramp_for(d):
    """[(entry, (bank, target))], re-derived from the census's own scan."""
    _, _, tramp = survey(d)
    return sorted(tramp.items())


def decode_bank(d: bytes, target: int, bank_file_offset: int, count: int = 6) -> str:
    """`count` instructions at `target` in one bank, as one line.

    A bucket-C target names an address above `0x8000` and nothing in the bytes
    says which bank is mapped, so the two readings are shown rather than
    chosen. `offset_for_runtime()` is not used here on purpose: it returns
    `None` for a target seen from `common`, which is the fact this whole tool
    is about, so the mapping is done by hand from the region table instead.
    """
    off = bank_file_offset + (target - 0x8000)
    if off < 0 or off >= len(d):
        return "outside the image"
    parts = []
    at = off
    for _ in range(count):
        if at >= len(d):
            break
        n = OPCODE_LEN[d[at]]
        if at + n > len(d):
            break
        parts.append(f"0x{target + (at - off):04X} {d[at:at + n].hex(' ')} "
                     f"{mnemonic(d, at, target + (at - off))}")
        at += n
    return "; ".join(parts)


def spans_note(seeds, descents) -> str:
    """The `#` block the export opens with, saying which population it covers.

    The coverage statement belongs in the file rather than only in the write-up,
    because the failure it exists to catch is an export that is silently short:
    a reader holding the file and not the write-up cannot otherwise tell a
    complete descent set from the seed set alone. Every figure below is counted
    from the walk this run performed rather than transcribed, so a seed set that
    moves moves them too instead of leaving a number to be believed.

    `seeds` is what lets the note split the population, and the split is what
    keeps `basis` readable: a `SEED_BASES` member is a seed the walk was given,
    a `call-from-0xNNNN` names the caller whose callee this entry is. A consumer
    that wants the seed-derived view -- which is all this export carried before
    the callee-discovered descents were added -- filters on that column and gets
    exactly it back.

    A consumer has to drop the `#` lines before parsing: `csv.DictReader` run on
    the whole file reads the first one as the fieldnames and every later one as
    a row, which is a parse that succeeds and answers nothing. The obligation is
    the same one `bank_call_regions.HEADER_NOTE` and
    `call_graph_gaps.read_rows()` carry, and the note says so rather than
    leaving a consumer to find out.
    """
    walked = sum(1 for a, _ in seeds if a in descents)
    blocks = sum(len(rec.blocks) for rec in descents.values())
    counts = (("descents", len(descents), "every entry walk() returned a "
               "Descent for"),
              ("blocks", blocks, "their decoded blocks, summed"),
              ("from the seed set", walked, "basis is a member of SEED_BASES"),
              ("discovered", len(descents) - walked,
               "basis is call-from-0xNNNN"))
    table = "".join(f"#   {label:<18} {n:>5}   {what}\n"
                    for label, n, what in counts)
    return (
        "# Written to stdout by ec/tools/bucket_c_codemap.py --spans, so there\n"
        "# is no committed copy to drift: re-derive with `python3\n"
        "# ec/tools/bucket_c_codemap.py ec/firmware/GMxMGxx_11.800 --spans >\n"
        "# spans.csv`. One row per (entry point, block), and `basis` says how\n"
        "# the walk reached that entry -- a member of SEED_BASES for a seed it\n"
        "# was given, `call-from-0xNNNN` for one it reached by pushing a caller\n"
        "# callee. Filtering on `basis` recovers the seed-only view and loses\n"
        "# nothing.\n"
        "#\n"
        "# COVERAGE, counted from this run rather than transcribed. This file\n"
        "# holds every descent the walk made:\n"
        "#\n"
        f"{table}"
        "#\n"
        "# A file whose descent or block count is below those two totals is\n"
        "# short, and says so rather than by omission.\n"
        "#\n"
        "# `csv.DictReader` does NOT skip this block: on the whole file it\n"
        "# reads the first `#` line as the fieldnames and every later one as a\n"
        "# row, so drop the lines starting with `#` first -- what\n"
        "# bank_call_regions.py's `parse()` and call_graph_gaps.py's\n"
        "# `read_rows()` both do.\n"
    )


def write_spans(seeds, descents):
    """Every descent's decoded blocks, for #20 to consume.

    One row per (entry point, block): the address range a descent decoded and
    the token it ended on. Issue #20's goal is a full code/data separation of
    the image, and this is the half of it that is already a function of the
    walk rather than of a reader's judgement.

    Over `descents`, not `seeds`. `walk()` pushes every callee it discovers onto
    the worklist, so the descents it returns are the seed set *and* everything
    reachable through a call from it; iterating the seeds dropped the second
    population while carrying no sign that it had. Entries are sorted by address
    so two branches produce the same file -- the walk is a BFS, so its own order
    is a function of which seed happened to be popped first.
    """
    sys.stdout.write(spans_note(seeds, descents))
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["entry", "basis", "block_lo", "block_hi", "insns", "end"])
    for entry in sorted(descents):
        rec = descents[entry]
        for lo, pcs, _ in rec.blocks:
            last = pcs[-1]
            w.writerow([f"0x{entry:04X}", rec.basis, f"0x{lo:04X}",
                        f"0x{last:04X}", len(pcs), rec.terminal])


# --- self-test --------------------------------------------------------------

def self_test(d: bytes) -> int:
    """The refusals and the oracle. `--check` is the reproducibility half."""
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else 'FAIL'}  {text}")

    print("bucket_c_codemap.py --self-test")
    print()

    # 1. A seed outside the common area is refused rather than walked. The bank
    #    window addresses are the natural mistake: a walk that read a bank as
    #    common would report a second, wrong code map rather than an error.
    _, _, tramp = survey(d)
    check(all(a < 0x8000 for a in list(BANK_STUBS) + list(tramp)),
          "every BL51 stub and every trampoline entry is a common-area address, "
          "so the refusal below is a real refusal and not a trap that fires on "
          "the seed set itself")
    reached, _ = walk(d, [(0x1100, "stub"), (0x8000, "trampoline")])
    check(0x8000 not in reached and 0x1100 in reached,
          "a seed at or above 0x8000 is skipped, not decoded as common")

    # 2. A budget that cannot be honoured. A walk with no instructions is not a
    #    zero result, so it is a refusal rather than a table of `no-seed-nearby`.
    try:
        walk(d, [(0x1100, "stub")], max_insns=0)
        check(False, "a budget of 0 instructions is refused")
    except SystemExit as exc:
        check("cannot be honoured" in str(exc),
              f"a budget of 0 instructions is refused: {exc}")
    try:
        walk(d, [(0x1100, "stub")], max_insns=-5)
        check(False, "a negative budget is refused")
    except SystemExit:
        check(True, "a negative budget is refused")

    # 3. A fourth verdict, and a reason outside the closed set. The two are
    #    separate refusals: a new `walk_reason` and a new `walk_verdict` are
    #    different mistakes, and a column that could hold either unbounded is a
    #    column a count of means nothing in.
    for reason in ("reached", "ret", "erased-run", "mid-instruction"):
        check(verdict_for(reason) in VERDICTS,
              f"reason {reason!r} maps to a member of the three")
    for bad_reason in ("probably-code", "", "reached ", "Reached", None):
        try:
            verdict_for(bad_reason)
            check(False, f"reason {bad_reason!r} is refused")
        except SystemExit:
            check(True, f"reason {bad_reason!r} is refused, not rendered")
    check(UNKNOWN_REASONS <= WALK_REASONS and not (UNKNOWN_REASONS & {"reached"}),
          f"the {len(UNKNOWN_REASONS)} reason(s) that make a site `unknown` are "
          "members of the vocabulary and none of them can describe a reached one")

    # 4. The terminator vocabulary is closed over FLOW_OPCODES: every member is
    #    either followed or given a reason, and the dispositions are the five
    #    shapes `descend()` actually has.
    #
    #    The three split figures are transcribed from `disasm8051.FLOW_OPCODES`
    #    rather than computed here, and the arithmetic is worth writing down
    #    because the paged families are the trap: `ajmp`/`acall` read as "16 of
    #    the 256 byte values" all over this repository's prose, and that is the
    #    count of *shapes*, not of opcodes -- an 8-bit opcode space has eight
    #    rows of the 0x20 stride, so each family is 8 opcodes and the two
    #    together are 16, which is where the number people quote comes from.
    #    9 + 28 + 13 = 50 = len(FLOW_OPCODES).
    dispositions = {op: flow_disposition(op) for op in sorted(FLOW_OPCODES)}
    unknown = sorted({v for v in dispositions.values()} - set(DISPOSITIONS))
    check(not unknown, f"every one of the {len(FLOW_OPCODES)} FLOW_OPCODES "
          f"members is followed or given a reason"
          f"{'' if not unknown else ' -- unrecognised: ' + ', '.join(unknown)}")
    calls = [op for op, v in dispositions.items() if v == "call"]
    follows = [op for op, v in dispositions.items() if v == "follow"]
    terminators = [op for op, v in dispositions.items() if v != "call"
                   and v != "follow"]
    check(len(calls) == 9 and len(follows) == 28 and len(terminators) == 13,
          f"9 call opcodes (`lcall` + 8 `acall`) are recorded and walked past, "
          f"28 PC-relative branches are followed on both sides, and 13 "
          f"terminate an arm (got {len(calls)}, {len(follows)} and "
          f"{len(terminators)})")
    check(len(calls) + len(follows) + len(terminators) == len(FLOW_OPCODES),
          f"the three dispositions account for all {len(FLOW_OPCODES)} members, "
          "so none is followed and given a reason at once")
    try:
        flow_disposition(0x00)      # `nop`: not a flow opcode at all
        check(False, "a non-flow opcode is refused")
    except SystemExit:
        check(True, "a non-flow opcode is refused rather than silently "
                    "dispositioned")

    # 5. The oracle, transcribed into the suite's docstring from
    #    bank-call-audit.md 5 rather than read from this tool's own output --
    #    see test_bucket_c_codemap.py. What is checked here is that the tool
    #    still describes the same population the audit did.
    rows, seeds, reached, descents, codemap, known, _, _ = build(d)
    targets = {r["target"] for r in rows}
    check(len(rows) == 140 and sum(1 for r in rows if r["anchored"]) == 83,
          f"bucket C still holds {len(rows)} site(s), "
          f"{sum(1 for r in rows if r['anchored'])} anchored")
    check(len(targets) == 102, f"across {len(targets)} distinct targets")
    check(len(targets & known) == 1,
          f"{len(targets & known)} of them is an entry a trampoline names")
    check(len(seeds) > 0 and all(0 <= a < 0x8000 for a, _ in seeds),
          f"all {len(seeds)} seed(s) are inside the common area")

    # 6. The budget is reported as a token and the walk is bounded, so a run
    #    that gave up says so rather than reading as a clean negative.
    terminals = collections.Counter(rec.terminal for rec in descents.values())
    check(sum(terminals.values()) == len(descents),
          f"every one of the {len(descents)} descent(s) carries a terminator")
    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the refusals or "
              "with bank-call-audit.md 5")
        return 1
    print("self-test passed: the refusals hold, the terminator vocabulary is "
          "closed over FLOW_OPCODES, and the census still reads 140 / 83 across "
          "102 targets")
    return 0


def check_csv(d, path) -> int:
    """Diff the regenerated table against the committed one. Exit 1 on a diff.

    A *missing* file fails rather than being created. Writing it would make
    `--check` the thing that decides what the committed table is, which is the
    arrangement this repository's other `--check` modes deliberately refuse:
    the tool re-derives and the file is compared, and a file that has not been
    committed yet is a red run saying so.
    """
    if not os.path.exists(path):
        print(f"error: {path} does not exist. --check compares; it never "
              "creates. Generate the table with --csv and commit it.", file=sys.stderr)
        return 1
    want = open(path).read()
    got = csv_text(d)
    if got == want:
        print(f"bucket-c-codemap.csv: {got.count(chr(10)) - 1} row(s) match the "
              "committed file, byte for byte")
        return 0
    diff = list(difflib.unified_diff(want.splitlines(True), got.splitlines(True),
                                     fromfile=f"committed {path}", tofile="regenerated"))
    sys.stdout.writelines(diff)
    print("error: the committed table is not what this run derives from the "
          "image", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default %(default)s)")
    ap.add_argument("--check", action="store_true",
                    help="regenerate the committed table in memory and diff it")
    ap.add_argument("--self-test", action="store_true",
                    help="check the refusals and the census oracle, and exit")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per bucket-C site on stdout")
    ap.add_argument("--spans", action="store_true",
                    help="write every descent's decoded blocks on stdout, with "
                         "a `#` header saying what population they cover, for #20")
    ap.add_argument("--csv-path", default=DEFAULT_CSV,
                    help="the committed table --check compares against")
    ap.add_argument("--index", default=None,
                    help="ec/decompiled/index.csv, for the Ghidra membership column")
    ap.add_argument("--max-insns", type=int, default=SEED_BUDGET,
                    help="instruction budget per descent (default %(default)s)")
    ap.add_argument("--max-depth", type=int, default=TRANSFER_DEPTH,
                    help="nested control transfers to follow per descent "
                         "(default %(default)s)")
    args = ap.parse_args()

    if args.check and args.self_test:
        ap.error("--check and --self-test are two different claims about this "
                 "image; run them separately")
    if args.csv and args.spans:
        ap.error("--csv and --spans are two different tables; run them separately")

    here = os.path.dirname(os.path.abspath(__file__))
    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    if d[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    if args.self_test:
        return self_test(d)
    if args.check:
        return check_csv(d, args.csv_path if os.path.isabs(args.csv_path)
                         else os.path.join(here, args.csv_path))
    if args.csv:
        sys.stdout.write(csv_text(d, args.index))
        return 0

    rows, seeds, reached, descents, codemap, known, functions, regions = build(
        d, args.index)
    if args.spans:
        write_spans(seeds, descents)
        return 0
    print_report(d, rows, seeds, descents, codemap, known, functions, regions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
