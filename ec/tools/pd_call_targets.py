#!/usr/bin/env python3
"""A control-flow-aware call-target census of the PD image, so "sixteen
candidates, one confirmed" becomes sixteen verdicts.

`docs/findings/pd-common-address-spaces.md` byte-scans
`ec/firmware/GMxMGxx_11.800[0x20000:0x30000]` for the `12 11 c2` encoding,
gets sixteen hits, and says in so many words that this method "can neither
call them callers nor data". That is the right sentence about a byte scan and
not the last word: a byte triple is not an instruction, and what settles it is
decoding the bytes under an aligned walk. This walks the image from a stated
entry set, follows control flow rather than matching byte patterns, and books
every candidate offset with a verdict.

**The verdict is about framing, never about behaviour.** `decoded-lcall` says
an aligned walk from a stated seed decoded an `lcall` at this offset and named
the target the encoding names. It does not say the EC executes it, and it does
not say the framing is right -- `audit_call_targets.py`'s module docstring
establishes that framing is unsettled in *both* directions, that its anchored
count is "demonstrably not phantom-free", and that a same-bank and a
cross-bank direct call are byte-identical. `unreached-by-this-method` means no
walk from this entry set decoded this offset: never "absent", never "data".
Nothing here is behavioural, nothing here was observed on hardware, and the
only inputs are `ec/firmware/GMxMGxx_11.800` and committed CSVs.

**The entry set is four sets and each row is tagged with its own.** `vector`
(the table `pd_image_census.vector_table()` walks rather than looks up),
`listing` (the `pd` rows of `ec/decompiled/listing-index.csv`), `call-graph`
(the `pd` rows of `ec/annotations/call-graph-callees.csv`, less the overlap),
and `discovered` (a target a walk itself decoded, which closes the loop). An
address two of them name is one entry with two witnesses: reporting it twice
would inflate the walk and misstate the denominators.

**The boundary rule, and why it is load-bearing.** A walk from entry *E* stops
at the lowest committed `pd` listing start strictly above *E* and records
`next listing boundary` in `ends`. Without it a mis-seeded entry runs for
thousands of bytes and every candidate site gets the wrong enclosing function;
with it, `enclosing` is a *listing* fact and not a discovered boundary.

The boundary is that next listing **start**, not the seed listing's own **end**,
and the two are different addresses wherever a gap or a short listing sits
between them. So a walk from a listing's own entry can and does leave that
listing's extent, and the rule decides where `enclosing` comes from rather than
guaranteeing that `enclosing` contains the site: `0x8288` is decoded only by
the walk from `0x821B`, whose listing ends at `0x825B`. Because the nearest
listing below a site is not the same claim as the site lying inside it --
`0x821B`'s extent provably does not contain `0x8288` -- `in_listing` is a
separate column and not an inference from `enclosing`.

**Coverage is a relationship, never a pinned figure.** The walk and the
committed listings are each below the image size, and *neither contains the
other*: there are bytes the walk decodes that no listing covers, and bytes the
listings cover that no walk decodes. That two-sided partial overlap is the
honest shape and it is the opposite of what the phrase "the walk reaches more"
would suggest. Two different things put ground on each side, and neither is the
boundary rule. The listings' figure is the *union of their byte extents* while
the walk's is the set of distinct instruction *starts*, so a byte a walk
consumed as an operand is counted by the listings and not by the walk. And a
walk stops *inside* a listing at a terminator -- `ret`, `reti`, a tail jump, an
indirect jump or a `loop` -- which leaves the rest of that listing's extent
undecoded from its own entry.

`--report` prints both figures and both differences live;
`check_coverage()` asserts the relationships on every run and requires both
differences to be non-empty, so a method that degenerated into containing the
other would be a red run. `--check` has exactly two halves, regenerate the
committed CSV and diff it byte for byte, and assert those relationships, and
both run so a table mismatch cannot skip the rest. No figure of any of the four
is written down here, in the write-up, or in a test -- the previous attempt of
this tool pinned them and went red for a change that never touched it.

**Annotate, never suppress.** A site inside an `ec/annotations/data-regions.yaml`
region is labelled in the `region` column and still counted;
`refuse_filtering()` is a named function called from `--self-test`, so the rule
survives someone adding a `--only-in-data` flag. The reason is
`data_regions.py:refuse_filtering()`'s own: a smaller number nobody can audit
is indistinguishable from absence.

**Deliberately out.** The 2-byte paged (`ajmp`/`acall`) and PC-relative
families have their own committed censuses for the bank images --
`bank-paged-call-targets.csv`, `bank-relative-branch-targets.csv` -- and
adding them here would be a second tool's census in a first tool's file;
`--paged-csv` is the obvious follow-up. What the dispatch tables at `0x11C2`
and `0x119C` *select* is a question about table contents, not about whether a
call exists.

Usage:
    python3 ec/tools/pd_call_targets.py --check
    python3 ec/tools/pd_call_targets.py --report
    python3 ec/tools/pd_call_targets.py --for-target 0x11C2
    python3 ec/tools/pd_call_targets.py --seed-verdicts
    python3 ec/tools/pd_call_targets.py --csv > ec/annotations/pd-call-targets.csv
    python3 ec/tools/pd_call_targets.py --self-test
"""
import argparse
import bisect
import collections
import csv
import difflib
import io
import os
import sys

from data_regions import load as load_data_regions, region_at
from disasm8051 import (OPCODE_LEN, REL_OPCODES, case_table_len,
                        converges_from, inline_arg_len, mnemonic, paged_target,
                        relative_target)
from pd_image_census import read_region, vector_table
from trace_xdata_refs import PD_MARKER, REGIONS, budget_end
from walk_branch_arms import (END_DEPTH, END_IMAGE, END_INDIRECT, END_LOOP,
                             END_RET, END_RETI, END_TAIL)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
FIRMWARE = os.path.join(REPO, "ec", "firmware", "GMxMGxx_11.800")
TABLE_CSV = os.path.join(REPO, "ec", "annotations", "pd-call-targets.csv")
LISTING_INDEX = os.path.join(REPO, "ec", "decompiled", "listing-index.csv")
CALLEE_CSV = os.path.join(REPO, "ec", "annotations", "call-graph-callees.csv")
PD_DECOMPILED = os.path.join(REPO, "ec", "decompiled", "pd")

# The 3-byte absolute forms: `0x02` is `ljmp`, `0x12` is `lcall`. They are the
# whole reason this image is the interesting one -- the two dispatchers
# `pd-common-address-spaces.md` names, `dispatch_code_table` at `0x119C` and
# `dispatch_code_table_2byte_key` at `0x11C2`, have no `ret`, so their only exit
# is `jmp @A+DPTR` and a tail `ljmp` into either is a real and distinguishable
# call shape. The same tuple `audit_call_targets.py:CALL_OPCODES` carries, and
# the same population `bank-call-targets.csv` reports for three bank images.
CALL_OPCODES = (0x02, 0x12)

PAGED_OPCODES = (0x01, 0x11)      # ajmp, acall -- `op & 0x1F` is the whole test
RET_OPCODES = {0x22, 0x32}        # ret, reti
COMPUTED_JUMP = 0x73              # jmp @a+dptr -- a target no walk can follow
SJMP = 0x80                       # the unconditional rel8 branch

# This walk's own terminator, beside the vocabulary `walk_branch_arms.py`
# already established -- imported above rather than re-spelled, because a
# census that calls one stop "next listing boundary" here and "DPTR reloaded"
# in the tool beside it is two vocabularies to learn to read a row.
END_BOUNDARY = "next listing boundary"

# Bounds. Both are named on every row that hits them, in `budget_end()`'s
# idiom, so a bound that fired is visible on the row rather than inferred from
# a smaller figure somewhere else. `walk_flow_follow.py` names them the same
# way for the same reason.
MAX_DEPTH = 12
MAX_INSNS = 400

# The closed vocabulary every `ends` cell is drawn from, as the *stems*
# `end_stem()` reads back. A walk that stops for a reason not named here is a
# bug, and the suite holds this set rather than a sample of it. The budget's
# stem is `budget_end()`'s own `max_insns`, which is why that function is
# imported and re-used here rather than re-spelled -- a second copy of the
# wording would be a second thing to keep in step.
TERMINATORS = (END_RET, END_RETI, END_TAIL, END_INDIRECT, END_BOUNDARY,
               END_LOOP, END_DEPTH, budget_end(MAX_INSNS).partition(" (")[0],
               END_IMAGE)

DECODED_LCALL = "decoded-lcall"
DECODED_LJMP = "decoded-ljmp"
OPERAND = "operand"
MID_INSTRUCTION = "mid-instruction"
UNREACHED = "unreached-by-this-method"
DATA_REGION = "data-region"
VERDICTS = (DECODED_LCALL, DECODED_LJMP, OPERAND, MID_INSTRUCTION, UNREACHED,
            DATA_REGION)

COLUMNS = ["file_offset", "runtime", "candidate", "verdict", "target",
           "enclosing", "in_listing", "ends", "frame_onto", "frame_over",
           "region"]

# `candidate` records which population put the row in the table, so the union
# in `survey()` is auditable from the CSV alone rather than from prose.
BYTE_SCAN = "byte-scan"
WALK_ONLY = "walk"
BOTH = "byte-scan+walk"

SOURCE_VECTOR = "vector"
SOURCE_LISTING = "listing"
SOURCE_CALLGRAPH = "call-graph"
SOURCE_DISCOVERED = "discovered"
SOURCES = (SOURCE_VECTOR, SOURCE_LISTING, SOURCE_CALLGRAPH, SOURCE_DISCOVERED)

# How far back `converges_from()` looks for an anchor, and the same constant
# `audit_call_targets.py` uses, so a `frame_onto`/`frame_over` cell here and
# one in `bank-call-targets.csv` are the same measurement.
FRAME_BACK = 24

# The PD image's file offset inside the committed firmware, read off
# `trace_xdata_refs.REGIONS` rather than re-spelled, so `data_regions`' file
# offsets and this module's cannot drift apart.
REGION_ROW = next(row for row in REGIONS if row[0] == "pd-image" and row[3] == 0)
REGION_FILE_BASE = REGION_ROW[1]


def end_stem(end):
    """The vocabulary token an `ends` cell starts with.

    `walk()` writes the terminator plus the address it fired at -- `loop back
    to 0x1234`, `depth limit at 0x1234`, `max_insns (400) exhausted` -- because
    a reader looking at a cell needs to see *which* address, not a bare token.
    The closed vocabulary is over the stem, so this strips the address back off
    and the suite asserts every `ends` value a walk produced is one of the
    stems followed by an address or a bound.
    """
    for tail in (" at 0x", " back to 0x", " ("):
        head, sep, _rest = end.partition(tail)
        if sep:
            return head
    return end


def repo_path(path):
    """`path` relative to the repository root, for a message a reader can act on."""
    try:
        return os.path.relpath(path, REPO)
    except ValueError:
        return path


def refuse_filtering() -> None:
    """Why this module offers no way to drop a candidate site.

    Called by `--self-test` and reachable from nowhere else, deliberately, and
    for `data_regions.py:refuse_filtering()`'s reason: annotate, never
    suppress. A site inside a listed data region keeps its row and its verdict;
    a mode that filtered those rows would make a smaller number nobody can
    audit, which is the failure `docs/findings.md` §4c records twice already.
    A function with a name rather than a sentence in a docstring, so a future
    edit that adds a filtering mode has to delete this to do it.
    """
    raise SystemExit(
        "error: no output mode filters rows out of this census. A site inside\n"
        "       a listed data region is labelled in the `region` column, not\n"
        "       dropped: dropping it makes a future scan's zero look like\n"
        "       absence, which is the failure docs/findings.md §4c records\n"
        "       twice already.")


def listing_extents():
    """[(start, size, name)] for every committed `pd` listing, in address order.

    Read from `ec/decompiled/listing-index.csv`, the committed index the rest of
    the tree cross-checks against, rather than from the `.asm` files. Sorted,
    because `Extents` bisects it once per row and once per block decoded.
    """
    out = []
    with open(LISTING_INDEX, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["program"] != "pd":
                continue
            out.append((int(row["addr"], 16), int(row["size"]), row["name"]))
    out.sort()
    return out


def callee_addrs():
    """{addr} for every `pd` row of `ec/annotations/call-graph-callees.csv`.

    A second entry set, produced by a different method. Its value here is not
    that it is larger but that it is independent: an address it names and
    `listing-index.csv` does not is an entry one committed artifact knows about
    and the other has not seen.
    """
    out = set()
    with open(CALLEE_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["scope"] == "pd":
                out.add(int(row["addr"], 16))
    return out


def entry_set(region):
    """{addr: source} for the seed set, each address tagged with where it came from.

    An address two sets name is one entry with two witnesses, and it keeps the
    first tag: `vector` is the image's own reset path, `listing` is the
    committed index, `call-graph` is the other committed artifact.
    """
    extents = listing_extents()
    entries = collections.OrderedDict()
    for _slot, target in vector_table(region):
        entries.setdefault(target, SOURCE_VECTOR)
    starts = set()
    for start, _size, _name in extents:
        entries.setdefault(start, SOURCE_LISTING)
        starts.add(start)
    for addr in sorted(callee_addrs() - starts):
        entries.setdefault(addr, SOURCE_CALLGRAPH)
    return entries


class Extents:
    """The committed listings, indexed for the two questions asked per site.

    Both questions are "what is the nearest listing at or below this address",
    asked once per row and once per block decoded, so the index is built once
    and bisected rather than scanned.
    """

    def __init__(self, extents=None):
        self.rows = listing_extents() if extents is None else sorted(extents)
        self.starts = [start for start, _size, _name in self.rows]
        self.sizes = [size for _start, size, _name in self.rows]
        self.names = [name for _start, _size, name in self.rows]

    def below(self, addr):
        """The listing at or below `addr`, or None."""
        i = bisect.bisect_right(self.starts, addr) - 1
        if i < 0:
            return None
        return (self.starts[i], self.sizes[i], self.names[i])

    def containing(self, addr):
        """The listing whose extent covers `addr`, or None.

        Not the same question as `below()`, and the two disagree in the tree:
        `0x8288`'s nearest listing is `0x821B` and `0x821B`'s extent does not
        reach it. That disagreement is why `enclosing` and `in_listing` are two
        columns -- the nearest listing below a site is a fact about where the
        site sits, and whether the site is inside that listing is separate.
        """
        row = self.below(addr)
        if row is None or not row[0] <= addr < row[0] + row[1]:
            return None
        return row

    def next_start(self, addr):
        """The lowest committed listing start strictly above `addr`, or None.

        This is the boundary rule's whole mechanism: a walk from `addr` stops
        when it reaches this, so one mis-seeded entry cannot run for thousands
        of bytes and hand every candidate site the wrong enclosing function.
        """
        i = bisect.bisect_right(self.starts, addr)
        return None if i >= len(self.starts) else self.starts[i]


def walk(d, seed, extents, max_depth=MAX_DEPTH, max_insns=MAX_INSNS,
         respect_boundary=True):
    """Everything reachable from `seed` under the boundary rule, within bounds.

    The unit of work is the *linear block*: decode forward from one address
    until a control-flow instruction, then start again wherever that
    instruction leads. A conditional branch contributes both arms, so the
    result is a "reachable from here" set rather than a guess about the hot
    path; the fall-through arm is walked first, which keeps the reported order
    in address order for the part a reader reads.

    `starts` is the visited set, and it holds *block starts* -- not every
    address decoded. That is stated because the distinction is load-bearing
    rather than pedantic, and because an earlier version of this tool's
    docstring claimed the stronger guarantee the code did not provide: a branch
    back into the middle of a block this walk already crossed starts a fresh
    decode of that block, and the bytes in between are recorded again as
    operands of it. The figure `--report` calls bytes reached counts distinct
    starts, so a block decoded twice is counted once there and charged twice
    against the budget -- the honest division, since the budget is spent work
    and coverage is not.

    A `boundary` of `None` -- the highest committed listing, or the ablation
    that removes the rule -- means the walk runs until something in the bytes
    stops it. That is the whole of what `boundary_ablation()` measures.

    Explicit list rather than recursion: a walk that re-enters itself through a
    routine would raise `RecursionError` on this image, which is a crash rather
    than a reported result.
    """
    boundary = extents.next_start(seed) if respect_boundary else None
    starts = {}
    operands = {}
    calls = []
    jumps = []
    ends = []
    pending = [(seed, 0)]
    queued = {seed}
    budget = max_insns
    while pending:
        pc, depth = pending.pop(0)
        if pc in starts:
            ends.append(f"{END_LOOP} back to 0x{pc:04X}")
            continue
        if depth > max_depth:
            ends.append(f"{END_DEPTH} at 0x{pc:04X}")
            continue
        # A byte that is one walk's operand and another's instruction start keeps
        # the stronger claim -- `starts` is written after `operands` for the
        # same address within one block, and across blocks `starts` is checked
        # first. The disagreement is visible in the returned pair rather than
        # smoothed over: `operands` still names the block that consumed it.
        while True:
            if boundary is not None and pc >= boundary:
                ends.append(END_BOUNDARY)
                break
            if not 0 <= pc < len(d):
                ends.append(f"{END_IMAGE} at 0x{pc:04X}")
                break
            if budget <= 0:
                ends.append(budget_end(max_insns))
                break
            op = d[pc]
            n = OPCODE_LEN[op]
            if pc + n > len(d):
                ends.append(f"{END_IMAGE} at 0x{pc:04X}")
                break
            raw = d[pc:pc + n]
            starts[pc] = True
            for k in range(1, n):
                operands.setdefault(pc + k, pc)
            budget -= 1

            if op in RET_OPCODES:
                ends.append(END_RET if op == 0x22 else END_RETI)
                break
            if op == COMPUTED_JUMP:
                ends.append(END_INDIRECT)
                break
            if op in CALL_OPCODES or op & 0x1F in PAGED_OPCODES:
                if op in CALL_OPCODES:
                    target = (d[pc + 1] << 8) | d[pc + 2]
                else:
                    target = paged_target(op, d[pc + 1], pc)
                if op == 0x12 or op & 0x1F == 0x11:
                    # Recorded, and the walk continues: the code after a call
                    # is still this routine's own.
                    calls.append((pc, target))
                    # `disasm8051`'s tables name the one inline argument block
                    # and the one case table this image has. The walk steps
                    # over both rather than decoding them, which is why these
                    # two helpers are consulted here and nowhere else.
                    pc += n + inline_arg_len(d, pc) + case_table_len(d, pc)
                    continue
                jumps.append((pc, target))
                ends.append(END_TAIL)
                break
            if op in REL_OPCODES or op == SJMP:
                target = relative_target(op, raw[-1], pc)
                if op == SJMP:
                    ends.append(END_TAIL)
                    break
                fall = pc + n
                if fall not in starts and fall not in queued:
                    queued.add(fall)
                    pending.append((fall, depth + 1))
                if target not in starts and target not in queued:
                    queued.add(target)
                    pending.append((target, depth + 1))
                ends.append(None)       # both arms queued; the block ends
                break
            pc += n
    ends = [e for e in ends if e is not None]
    return {"seed": seed, "starts": starts, "operands": operands,
            "calls": calls, "jumps": jumps, "ends": ends,
            "insns": len(starts), "boundary": boundary}


def survey(d, max_depth=MAX_DEPTH, max_insns=MAX_INSNS, respect_boundary=True,
           frame=True):
    """The whole census: every entry walked, every candidate offset booked.

    The candidate set is the union of two populations, and the union is the
    point. (a) Every offset whose byte is `0x02` or `0x12` with two bytes after
    it -- the byte-scan upper bound, the population
    `pd-common-address-spaces.md` scanned and the same one
    `bank-call-targets.csv` reports for three bank images. (b) Every offset a
    walk decoded as a call or a jump. (a) alone over-counts, because those two
    byte values occur as operand bytes inside other instructions and inside
    tables; (b) alone under-counts, because it cannot see a call whose site no
    walk reached. A site in (a) that (b) never reached still gets its row, with
    `unreached-by-this-method` as the verdict, which is what makes the sixteen
    countable by `grep` rather than by subtraction.

    A target a walk named is queued as an entry in its own right and tagged
    `discovered`, so a target reachable only by tail call is still walked. It is
    reported separately from the seeds because the two are different claims: "a
    walk named this address" is not "a walk decoded anything there", and a name
    is recorded whether or not the bytes at the named address were ever framed.
    """
    extents = Extents()
    entries = entry_set(d)
    regions = load_data_regions()

    decoded = {}
    reached_from = {}
    operand_owner = {}
    call_sites = {}
    jump_sites = {}
    site_ends = {}
    terminators = collections.Counter()
    discovered = []
    insns = 0

    queue = collections.deque(entries)
    queued_entries = set(entries)
    while queue:
        seed = queue.popleft()
        arm = walk(d, seed, extents, max_depth, max_insns, respect_boundary)
        decoded.update(arm["starts"])
        # What each entry's own walk reached, keyed by the entry -- so the
        # report can ask how far a walk got once it arrived at a target it
        # named, which is the question "of those, how many did the walk
        # decode" cannot ask here: every discovered target is itself walked,
        # so that figure would be true of all of them and worth nothing.
        reached_from[seed] = tuple(arm["starts"])
        operand_owner.update(arm["operands"])
        for site, target in arm["calls"]:
            call_sites.setdefault(site, target)
        for site, target in arm["jumps"]:
            jump_sites.setdefault(site, target)
        # The first walk in seed order to decode a site owns its `ends` cell;
        # later walks of the same site would be a second opinion about a row
        # that has one `ends` column.
        final = arm["ends"][-1] if arm["ends"] else END_IMAGE
        for addr in arm["starts"]:
            site_ends.setdefault(addr, final)
        for end in arm["ends"]:
            terminators[end] += 1
        insns += arm["insns"]
        for target in sorted({t for _s, t in arm["calls"] + arm["jumps"]}):
            if target not in queued_entries and 0 <= target < len(d):
                queued_entries.add(target)
                entries[target] = SOURCE_DISCOVERED
                discovered.append(target)
                queue.append(target)

    byte_scan = {off for off in range(len(d) - 2) if d[off] in CALL_OPCODES}
    walked = set(call_sites) | set(jump_sites)
    candidates = byte_scan | walked

    rows = []
    for off in sorted(candidates):
        listing = extents.below(off)
        holder = extents.containing(off)
        region = region_at(regions, REGION_FILE_BASE + off)
        onto, over = converges_from(d, off, FRAME_BACK) if frame else (0, 0)
        if off in call_sites:
            verdict, target = DECODED_LCALL, call_sites[off]
        elif off in jump_sites:
            verdict, target = DECODED_LJMP, jump_sites[off]
        elif off in decoded:
            # Unreachable over the current candidate set, and kept rather than
            # deleted because it is the reading that makes the vocabulary
            # closed: a candidate the walk decoded as an instruction that is
            # neither a call nor a jump. Every candidate is either a `0x02`/
            # `0x12` byte or an offset a walk framed as a transfer, so on this
            # image the branch does not fire -- the two populations cannot
            # produce a non-transfer instruction start. The suite asserts the
            # branch is unreachable rather than asserting a count of zero, so
            # a change that widens the candidate set has to say which reading
            # the new rows get.
            verdict, target = MID_INSTRUCTION, None
        elif off in operand_owner:
            verdict, target = OPERAND, None
        elif region is not None:
            verdict, target = DATA_REGION, None
        elif over and not onto:
            # No walk decoded or consumed this byte, and no anchor walk from
            # the preceding bytes lands on it either -- every anchor steps over
            # it. The byte is inside an instruction as far as framing evidence
            # can say, and this method's walk never crossed that instruction.
            # Distinct from `unreached-by-this-method`, which says nothing at
            # all about framing.
            verdict, target = MID_INSTRUCTION, None
        else:
            verdict, target = UNREACHED, None
        if target is None and d[off] in CALL_OPCODES:
            # What the byte scan would have claimed here. Carried on every row
            # whose bytes spell a call, so a refuted candidate shows the claim
            # it refutes beside the verdict that refutes it.
            target = (d[off + 1] << 8) | d[off + 2]
        rows.append({
            "file_offset": f"0x{REGION_FILE_BASE + off:05X}",
            "runtime": f"0x{off:04X}",
            "candidate": (BOTH if off in byte_scan and off in walked else
                          WALK_ONLY if off in walked else BYTE_SCAN),
            "verdict": verdict,
            "target": f"0x{target:04X}" if target is not None else "",
            "enclosing": f"0x{listing[0]:04X}" if listing else "",
            "in_listing": "yes" if holder else "no",
            "ends": site_ends.get(off, ""),
            "frame_onto": onto,
            "frame_over": over,
            "region": region["name"] if region else "not listed",
        })

    return {
        "rows": rows,
        "extents": extents,
        "entries": entries,
        "discovered": discovered,
        "reached_from": reached_from,
        "decoded": decoded,
        "operand_owner": operand_owner,
        "call_sites": call_sites,
        "jump_sites": jump_sites,
        "terminators": terminators,
        "byte_scan": byte_scan,
        "walked": walked,
        "candidates": candidates,
        "region_extents": [(r["name"], r["file_lo"], r["file_hi"])
                           for r in regions],
        "insns": insns,
    }


def coverage(context, d):
    """(walk bytes, listing bytes, image bytes): the three `--report` compares.

    `walk bytes` is the number of distinct offsets some walk decoded as an
    instruction start; `listing bytes` is the *union* of the committed `pd`
    listing extents rather than the sum of their `size` cells, because two
    listings overlap on this image and only a set of offsets can be compared
    with another set of offsets. Neither figure is a claim that the bytes are
    code: the walk's are "framed by this method from these seeds", the
    listings' are "a committed artifact says so". No figure of the pair is
    written down anywhere.
    """
    listing = set()
    for start, size, _name in context["extents"].rows:
        listing |= set(range(start, start + size))
    return len(context["decoded"]), len(listing), len(d)


def below_entry_listings(context):
    """Committed `pd` listings no walk decoded an instruction strictly inside.

    Every committed listing start is an entry by construction, so this is not a
    statement about seeding. It is about what a walk does once it arrives: a
    `ret`, a `reti`, a tail jump, an indirect jump or a `loop` stops it, and the
    rest of that listing's extent is then never decoded from its own entry.
    These are the listings the entry set names and this method does not
    re-derive the whole of. `--report` prints them by name.

    The boundary rule is *not* what stops these walks, and saying so is the
    point: the boundary is the next listing *start*, which for a listing
    followed by a gap lies above that listing's own *end*, so a walk from a
    listing's own entry can and does leave its extent. `0x8288` is reached only
    by the walk from `0x821B`, whose listing ends at `0x825B`. An earlier version
    of this docstring asserted the opposite -- that a listing's own walk cannot
    leave its extent upwards -- and the committed image refutes it.

    "Strictly inside" excludes the start byte, because every listing start is an
    entry by construction and the walk trivially decodes its own seed; a
    listing whose extent is exactly one instruction therefore never appears
    here, which is the right reading rather than a hole. The list is computed
    and never written down, so a listing landing cannot make a sentence in this
    file wrong.
    """
    decoded = context["decoded"]
    return [(start, size, name) for start, size, name in context["extents"].rows
            if not any(start < a < start + size for a in decoded)]


def boundary_ablation(d, extents, entries, max_depth=MAX_DEPTH,
                      max_insns=MAX_INSNS):
    """(extra sites, extra bytes) from walking with the boundary rule removed.

    The rule's cost, measured rather than asserted. A walk with the rule stops
    at the next committed listing; the same walk without it continues until the
    bytes stop it, so it reaches a strict superset. Asserted as a relationship
    -- superset, and non-empty -- because a count of it is a number this
    repository's own listings would move, while the fact that the rule costs
    reach is a fact about the firmware under two methods. Recomputed on every
    `--report` and `--check`, so it cannot go stale silently either: if the rule
    stopped costing reach, the superset would be empty and the suite would say
    so.
    """
    with_rule, without = set(), set()
    for seed in entries:
        with_rule |= set(walk(d, seed, extents, max_depth, max_insns,
                              respect_boundary=True)["starts"])
        without |= set(walk(d, seed, extents, max_depth, max_insns,
                            respect_boundary=False)["starts"])
    extra = without - with_rule
    return sorted(extra), len(extra)


def seed_verdicts(context, d):
    """What the walk says about each listing the stale `pd/*.c` comments name.

    The issue's premise is that `.asm` headers at `pd/10F1.asm`, `1229.asm` and
    others note the boundary "came from a call-target byte scan and is a
    hypothesis". No `pd/*.asm` carries that note -- the phrase is in `pd/*.c`
    comments citing a header beside them that does not contain it. Rather than
    plan around that, this measures the question the issue actually wanted, per
    listing those comments name: does the walk reach it, is it an entry in its
    own right, does `converges_from()` frame it.

    The seed list is derived from the comments themselves rather than written
    down, so it moves with the prose it is about and no figure of it is pinned.
    """
    entries = context["entries"]
    decoded = context["decoded"]
    extents = context["extents"]
    out = []
    for name in sorted(os.listdir(PD_DECOMPILED)):
        if not name.endswith(".c"):
            continue
        with open(os.path.join(PD_DECOMPILED, name), encoding="utf-8",
                  errors="replace") as handle:
            text = handle.read()
        if "call-target byte scan" not in text and \
                "call-target-scan" not in text:
            continue
        start = int(name[:-2], 16)
        row = extents.containing(start)
        onto, over = converges_from(d, start, FRAME_BACK)
        out.append({"file": name, "addr": start,
                    "name": row[2] if row else "",
                    "reached": start in decoded,
                    "entry": entries.get(start, ""),
                    "framed": (onto, over)})
    return out


def ascii_carries_the_note() -> list:
    """The `pd/*.asm` files carrying the note the `pd/*.c` comments attribute
    to them. Always empty on this tree; returned so the suite can assert the
    premise refutation mechanically rather than as a sentence.

    Both spellings are looked for, because the comments use both: seven files
    say "call-target byte scan" and `1229.c` alone says "call-target-scan".
    """
    out = []
    for name in sorted(os.listdir(PD_DECOMPILED)):
        if not name.endswith(".asm"):
            continue
        with open(os.path.join(PD_DECOMPILED, name), encoding="utf-8",
                  errors="replace") as handle:
            text = handle.read()
        if "call-target byte scan" in text or "call-target-scan" in text:
            out.append(name)
    return out


def csv_table(context):
    """The committed `ec/annotations/pd-call-targets.csv`, as text.

    No comment line, so `csv.DictReader` reads it -- the convention
    `../annotations/README.md` sets out. Written with the csv module's own
    dialect, so the committed file carries its CRLF terminator and `--check`
    reads it with `newline=""`; universal-newline translation would rewrite
    every row and report a difference on every run, which is a check nobody
    trusts.
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(COLUMNS)
    for row in context["rows"]:
        writer.writerow([row[c] for c in COLUMNS])
    return buf.getvalue()


def check_table(generated, path=TABLE_CSV) -> int:
    """Exit code for the table half of `--check`: 0 when this run reproduces it.

    Read with `newline=""` so the comparison is the bytes on disk. A missing
    file fails rather than being created: `--check` is a check, and a check
    that manufactures its own subject is not one.
    """
    try:
        with open(path, newline="") as handle:
            on_disk = handle.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{repo_path(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced; the "
          f"file is the product of the command the page names, so regenerate "
          f"rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(),
                                     generated.splitlines(),
                                     "committed", "generated", lineterm="",
                                     n=0):
        print(line, file=sys.stderr)
    return 1


def check_coverage(context, d) -> int:
    """Exit code for the relationship half of `--check`.

    Two relationships, both over live values and neither a pinned figure:

      * the walk and the committed listings are each below the image size, and
      * neither contains the other -- there are bytes the walk decodes that no
        listing covers, and bytes the listings cover that no walk decodes.

    The second is the one that matters and it is the opposite of what a reader
    would assume. The walk's reach is *not* a superset of the listings': it
    partly overlaps it and each side has ground the other does not. Stating the
    coverage comparison as "the walk reaches more" would be a confident claim
    about a relationship that does not hold on this image, which is the failure
    `docs/findings.md` §4 records; the relation is asserted as the two-sided
    partial overlap it actually is, and both differences are required to be
    non-empty so a method that quietly degenerates into one of the other two
    states is a red run.

    What puts ground on each side is *not* the boundary rule, which is the
    obvious guess and is wrong: the boundary is the next listing *start*, not
    the seed listing's own *end*, so for a listing followed by a gap it sits
    above that listing's end and the walk leaves the extent. Two things do
    explain the overlap. The listings' figure is the union of their byte extents
    while the walk's is the set of distinct instruction starts, so a byte a walk
    consumed as an operand counts for the listings and not for the walk. And a
    walk stopped by a terminator -- `ret`, `reti`, a tail jump, an indirect
    jump, a `loop` -- leaves the rest of its listing undecoded from that
    listing's own entry.

    A landing `pd` listing can shrink the second difference without falsifying
    it, so no merge makes this red for a change that never touched this tool.
    """
    walk = set(context["decoded"])
    listing = set()
    for start, size, _name in context["extents"].rows:
        listing |= set(range(start, start + size))
    walk_only = walk - listing
    listing_only = listing - walk
    image_bytes = len(d)
    ok = True
    if len(walk) < image_bytes and len(listing) < image_bytes:
        print(f"coverage: both are below the image size -- the walk reaches "
              f"{len(walk)}, the listings cover {len(listing)}, of "
              f"{image_bytes} bytes")
    else:
        print(f"error: a method covers the whole image -- walk {len(walk)}, "
              f"listings {len(listing)}, image {image_bytes}. Either figure at "
              f"or above the image size means a coverage count has stopped "
              f"meaning what it says.", file=sys.stderr)
        ok = False
    if walk_only and listing_only:
        print(f"coverage: neither contains the other -- {len(walk_only)} "
              f"byte(s) the walk decodes that no listing covers, and "
              f"{len(listing_only)} byte(s) the listings cover that no walk "
              f"decodes. Two partial methods, each with reach the other lacks; "
              f"neither figure is pinned.")
    else:
        print(f"error: the two methods no longer partly overlap -- walk-only "
              f"{len(walk_only)}, listing-only {len(listing_only)}. One side "
              f"containing the other would mean this check has stopped "
              f"comparing two methods.", file=sys.stderr)
        ok = False
    return 0 if ok else 1


def report_lines(context, d):
    """Everything `--report` prints, as a list of lines.

    A function so the suite can assert the *printed prose* against the same live
    values the report is built from -- the case that makes the report
    self-consistent by construction rather than by a figure someone retyped.
    """
    out = []
    verdicts = collections.Counter(r["verdict"] for r in context["rows"])
    by_source = collections.Counter(context["entries"].values())
    walk_bytes, listing_bytes, image_bytes = coverage(context, d)
    listing_set = set()
    for start, size, _name in context["extents"].rows:
        listing_set |= set(range(start, start + size))
    walk_set = set(context["decoded"])
    walk_only = len(walk_set - listing_set)
    listing_only = len(listing_set - walk_set)
    labelled = sum(1 for r in context["rows"] if r["region"] != "not listed")
    pd_regions = [r for r in context["region_extents"]
                  if REGION_FILE_BASE <= r[1] < REGION_FILE_BASE + len(d)]

    out.append("PD image call-target census")
    out.append(f"  image       {image_bytes} bytes at firmware "
               f"0x{REGION_FILE_BASE:05X}, marker {PD_MARKER[1].decode()!r} at "
               f"0x{PD_MARKER[0]:05X}")
    out.append(f"  candidates  {len(context['candidates'])} -- every offset "
               f"whose byte is 0x02 or 0x12 with two bytes after it, plus every "
               f"offset a walk decoded as a call or a jump")
    out.append("")
    out.append("Entry set, by source:")
    for source in SOURCES:
        out.append(f"  {source:<11} {by_source.get(source, 0)}")
    out.append("")
    out.append("Verdicts:")
    for verdict in VERDICTS:
        out.append(f"  {verdict:<26} {verdicts.get(verdict, 0)}")
    out.append("")
    out.append("Coverage -- two methods' figures, compared and neither pinned:")
    out.append(f"  walk reached        {walk_bytes} of {image_bytes} bytes "
               f"({100.0 * walk_bytes / image_bytes:.2f}%)")
    out.append(f"  committed listings  {listing_bytes} of {image_bytes} bytes "
               f"({100.0 * listing_bytes / image_bytes:.2f}%)")
    # The two are not the same quantity and conflating them is the easy
    # mistake: the coverage line counts *distinct* instruction starts across
    # the whole census, while this counts every seed's own decode, so a helper
    # reached from several seeds is walked once per caller. The gap between
    # them is the walk's own redundancy, and it is the honest reason the budget
    # is per-walk.
    out.append(f"  instruction starts decoded across the per-seed walks "
               f"{context['insns']}")
    out.append(f"  bytes only the walk decodes   {walk_only}")
    out.append(f"  bytes only the listings cover {listing_only}")
    # Not the boundary rule, which is the obvious guess here and is wrong: the
    # boundary is the next listing *start*, which for a listing followed by a
    # gap lies above that listing's own end, so a walk from a listing's own
    # entry can and does leave its extent. What puts ground on each side is that
    # the listings' figure is a byte union and the walk's a set of instruction
    # starts, and that a terminator stops a walk inside a listing.
    out.append("  the two partly overlap and neither contains the other: the "
               "listings' figure is a union of byte extents and the walk's a "
               "set of instruction starts, and a walk stopped by a terminator "
               "leaves the rest of its listing undecoded")
    out.append("  none of the four is a claim that its bytes are code; the "
               "walk's are framed by this method from these seeds")
    out.append("")
    out.append("Walks that ended, by terminator:")
    for token, count in sorted(context["terminators"].items()):
        out.append(f"  {token:<48} {count}")
    out.append("")
    # The heading says what `below_entry_listings()` means, which is not the
    # vacuous "no entry covers it": every committed listing start is an entry by
    # construction, so that reading could never return anything.
    out.append("Committed pd listings no walk decoded an instruction inside:")
    below = below_entry_listings(context)
    for start, size, name in below:
        out.append(f"  0x{start:04X}  {size:>4} bytes  {name}")
    out.append(f"  -- computed on this run and named here, never written down; "
               f"{len(below)} such listing(s)")
    out.append("")
    # Derived, never hardcoded. A report that prints `data-region 1` in the
    # verdict table and "the row is 0" two lines later contradicts itself the
    # moment a region lands inside the PD extent; both sentences are built from
    # the same live count and the same live extents, so they cannot.
    out.append("Data regions:")
    out.append(f"  `data-regions.yaml` holds {len(context['region_extents'])} "
               f"region(s), {len(pd_regions)} of them inside the PD extent")
    out.append(f"  this run labels {labelled} candidate row(s) with a region "
               f"name, and the `data-region` verdict is "
               f"{verdicts.get(DATA_REGION, 0)}")
    if not pd_regions:
        out.append("  so the `region` column reads `not listed` throughout, "
                   "which is a statement about this file's coverage and never "
                   "about the image")
    out.append("")
    out.append("Targets a walk named, and what became of each:")
    # A discovered target is queued as an entry and so is itself walked, which
    # makes "of those, addresses a walk decoded" true of all of them and
    # therefore worth nothing. What is worth reporting is how far each walk got
    # once it arrived: naming an address and decoding a routine at it are
    # different claims, and a target whose walk stopped on its first
    # instruction has been named and not otherwise explained.
    past_first = [t for t in context["discovered"]
                  if len(context["reached_from"].get(t, ())) > 1]
    in_listing = [t for t in context["discovered"]
                  if context["extents"].containing(t)]
    out.append(f"  jump and call targets named by a walk          "
               f"{len(context['discovered'])}")
    out.append(f"  of those, a walk decoded more than the one named "
               f"byte  {len(past_first)}")
    out.append(f"  of those, the target is inside a committed pd "
               f"listing      {len(in_listing)}")
    out.append("  each is queued as an entry in its own right, so each is "
               "walked; a target named and not otherwise explained is one the "
               "walk reached and read nothing past the entry instruction")
    out.append("")
    out.append("Boundary rule, ablated on this same image:")
    extra_sites, extra_bytes = boundary_ablation(d, context["extents"],
                                                 context["entries"])
    out.append(f"  without it the walk reaches a strict superset: "
               f"{extra_bytes} more byte(s), of which the first are "
               f"{' '.join('0x%04X' % a for a in extra_sites[:6])}")
    out.append("  asserted as a relationship rather than a figure, because a "
               "count of it is a number this repository's own listings would "
               "move")
    out.append("")
    out.append("Seed verdicts -- the listings the pd/*.c comments call a "
               "call-target byte-scan hypothesis:")
    for row in seed_verdicts(context, d):
        onto, over = row["framed"]
        out.append(f"  {row['file']:<10} 0x{row['addr']:04X} "
                   f"{row['name'][:36]:<36} "
                   f"reached={'yes' if row['reached'] else 'no ':<3} "
                   f"entry={row['entry'] or '-':<10} framed={onto}/{over}")
    out.append(f"  no pd/*.asm carries either spelling of the note the pd/*.c "
               f"comments attribute to it ({len(ascii_carries_the_note())} "
               f"file(s))")
    out.append("")
    out.append(f"`ends` vocabulary, closed -- every value a walk can report: "
               f"{', '.join(TERMINATORS)}")
    return out


def print_report(context, d):
    """Print `report_lines()`. Every figure is computed on the run that prints it.

    None of them is written down in this file, in the write-up, or in a test.
    A figure that counts this repository's own committed listings is a value
    every landing `pd` listing moves, which is what made the previous attempt
    of this tool red for a change that never touched it.
    """
    print("\n".join(report_lines(context, d)))


def self_test(d):
    """The hand-transcribed oracle, the refusals, and the boundary mechanism.

    The oracle is transcribed from `r2 -a 8051` over
    `make_bank_image.py --pd`'s `pd.bin`, not from this tool's decoder: a
    self-test that asserts its own output against itself passes when both are
    wrong. Each entry is a site the byte scan found, with the bytes and the
    mnemonic an independent 8051 disassembler gives when told to decode *at*
    that address -- which settles the encoding and settles nothing about
    whether any walk reaches it.
    """
    ok = True

    def check(cond, text):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {text}")
        if not cond:
            ok = False

    oracle = [
        (0x13F6, "1211c2", "lcall 0x11c2"),
        (0x153E, "1211c2", "lcall 0x11c2"),
        (0x1AB6, "1211c2", "lcall 0x11c2"),
        (0x3A46, "1211c2", "lcall 0x11c2"),
        (0x4FFA, "1211c2", "lcall 0x11c2"),
        (0x8288, "1211c2", "lcall 0x11c2"),
        (0x92EF, "1211c2", "lcall 0x11c2"),
        (0xCB4A, "1211c2", "lcall 0x11c2"),
        (0x136C, "12119c", "lcall 0x119c"),
        (0x4C35, "12119c", "lcall 0x119c"),
        (0x6B4C, "12119c", "lcall 0x119c"),
        (0xC879, "12119c", "lcall 0x119c"),
    ]
    print("r2 -a 8051 oracle, transcribed by hand, at a named set of the "
          "`12 11 c2` and `12 11 9c` sites:")
    for addr, raw, text in oracle:
        got = " ".join(mnemonic(d, addr, addr).split())
        check(d[addr:addr + len(raw) // 2].hex() == raw and got == text,
              f"0x{addr:04X} reads {raw} {text}")

    print("Refusals and the boundary mechanism, on hand-built fixtures:")
    try:
        refuse_filtering()
        check(False, "refuse_filtering() refuses")
    except SystemExit:
        check(True, "refuse_filtering() refuses")

    # A run of `0x00`, which is `nop` and one byte, so the fixture walks
    # forward rather than stopping on an opcode it cannot frame. With a
    # committed listing immediately above the seed the walk must stop there
    # and name it; without the rule it runs on to the end of the buffer. A
    # transfer would not exercise this -- an `ljmp` or a `ret` ends the walk
    # before the boundary is ever reached, which is the other terminator and
    # is checked separately below.
    fixture = bytes([0x00] * 8)
    extents = Extents(extents=[(0x0004, 4, "next_listing")])
    bounded = walk(fixture, 0x0000, extents)
    check(bounded["ends"] == [END_BOUNDARY] and sorted(bounded["starts"]) ==
          [0x0000, 0x0001, 0x0002, 0x0003],
          f"a walk stops at the next listing start and names it, having "
          f"decoded nothing above it ({bounded['ends']}, "
          f"{sorted(bounded['starts'])})")
    free = walk(fixture, 0x0000, extents, respect_boundary=False)
    check(END_BOUNDARY not in free["ends"] and len(free["starts"]) >
          len(bounded["starts"]),
          f"the same walk without the rule runs past it "
          f"({len(free['starts'])} starts against {len(bounded['starts'])})")

    # A `ret` is an ordinary end and not a cut, and `jmp @a+dptr` is the
    # computed-target blind spot -- the one edge class here that is a real
    # transfer and is never followed.
    ret_extents = Extents(extents=[])
    ret_walk = walk(bytes([0x22, 0x00]), 0x0000, ret_extents)
    check(ret_walk["ends"] == [END_RET], f"`ret` ends a walk ({ret_walk['ends']})")
    ind_walk = walk(bytes([0x73, 0x00]), 0x0000, ret_extents)
    check(ind_walk["ends"] == [END_INDIRECT],
          f"`jmp @a+dptr` is recorded as a cut ({ind_walk['ends']})")

    print("Closed vocabularies:")
    # Every `ends` value these walks produced, read back to its stem. This is
    # the check that the vocabulary is closed rather than merely documented:
    # a terminator that is not in TERMINATORS fails here by name.
    observed = {end_stem(e) for e in
                bounded["ends"] + free["ends"] + ret_walk["ends"] +
                ind_walk["ends"]}
    check(observed <= set(TERMINATORS),
          f"every terminator a walk reported is in the vocabulary "
          f"({sorted(observed)})")
    check({end_stem(t) for t in TERMINATORS} == set(TERMINATORS),
          "TERMINATORS holds stems, so every one of them is its own stem")
    check(all(v in VERDICTS for v in
              (DECODED_LCALL, DECODED_LJMP, OPERAND, MID_INSTRUCTION, UNREACHED,
               DATA_REGION)),
          "every verdict this module assigns is in VERDICTS")
    check(not ascii_carries_the_note(),
          "no pd/*.asm carries the note the pd/*.c comments attribute to it")

    print("ok" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="regenerate the committed CSV and diff it against "
                             "the committed bytes, and assert the coverage "
                             "relationship; both halves run")
    parser.add_argument("--self-test", action="store_true",
                        help="re-derive the hand-transcribed r2 oracle and the "
                             "invariants from the committed image")
    parser.add_argument("--report", action="store_true",
                        help="print the entry, verdict, coverage, terminator, "
                             "data-region and seed tables and nothing else")
    parser.add_argument("--for-target", metavar="ADDR",
                        help="print every candidate site naming this target, "
                             "e.g. 0x11C2")
    parser.add_argument("--seed-verdicts", action="store_true",
                        help="for each listing the pd/*.c comments call a "
                             "call-target byte-scan hypothesis, print whether "
                             "the walk reaches it, whether it is an entry, and "
                             "whether converges_from() frames it")
    parser.add_argument("--csv", action="store_true",
                        help="write the committed table on stdout")
    args = parser.parse_args(argv)

    # `--check` is refused alongside every other output mode rather than
    # silently losing to one: a mode flag ahead of it in `main()` made
    # `--check --for-target 0x11C2` exit 0 having run no check at all, so a
    # gate line that appended a flag would have passed without checking
    # anything. A check that cannot be reached is not a check.
    modes = [args.self_test, args.report, args.seed_verdicts, args.csv,
             args.for_target is not None]
    if args.check and any(modes):
        parser.error("--check cannot be combined with another output mode; run "
                     "it on its own, so a gate line that appends a flag fails "
                     "loudly instead of skipping the check")

    region, _how = read_region(FIRMWARE)

    if args.self_test:
        return self_test(region)

    context = survey(region)

    if args.check:
        # Both halves run and the return codes combine, so a table mismatch
        # does not skip the relationship check. The two failures are different
        # and neither hides the other.
        rc = check_table(csv_table(context))
        return rc or check_coverage(context, region)

    if args.csv:
        sys.stdout.write(csv_table(context))
        return 0

    if args.for_target is not None:
        try:
            target = int(args.for_target, 16)
        except ValueError:
            parser.error(f"--for-target wants a hex address, not "
                         f"{args.for_target!r}")
        rows = [r for r in context["rows"]
                if r["target"] and int(r["target"], 16) == target]
        for row in rows:
            print(f"{row['runtime']} {row['verdict']:<26} target "
                  f"{row['target']} enclosing {row['enclosing'] or '-':<8} "
                  f"in_listing={row['in_listing']}")
        print(f"\n{len(rows)} candidate site(s) name 0x{target:04X}. A "
              f"`decoded-lcall` row is a call as read by an aligned walk from a "
              f"stated seed, not a confirmed caller; "
              f"`unreached-by-this-method` is not absence.")
        return 0

    if args.seed_verdicts:
        rows = seed_verdicts(context, region)
        for row in rows:
            onto, over = row["framed"]
            print(f"{row['file']:<10} 0x{row['addr']:04X} "
                  f"{row['name']:<44} "
                  f"reached={'yes' if row['reached'] else 'no '} "
                  f"entry={row['entry'] or '-'} framed={onto}/{over}")
        print(f"\n{len(rows)} listing(s) named by the pd/*.c comments; "
              f"{len(ascii_carries_the_note())} pd/*.asm file(s) carry either "
              f"spelling of the note they attribute to it.")
        return 0

    print_report(context, region)
    return 0


if __name__ == "__main__":
    sys.exit(main())