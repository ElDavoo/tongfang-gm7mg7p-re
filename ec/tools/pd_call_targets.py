#!/usr/bin/env python3
"""A control-flow-aware census of the absolute call and jump sites in the
ITE8850-PD image, with a verdict per candidate.

`docs/findings/pd-common-address-spaces.md` byte-scans the whole PD image for
the `12 11 c2` encoding, finds sixteen sites, and says of the fifteen outside a
committed listing that "this method can neither call them callers nor data" --
and then names what would settle it: "A control-flow-aware scan that
disassembles instead of pattern-matching would separate calls from data in one
pass." This is that scan. `ec/annotations/pd-call-targets.csv` gives every
candidate site a verdict, so "sixteen candidates, one confirmed" becomes
sixteen answers.

**What the candidate set is, and why it is the wider half.** A row is every
offset whose byte is `0x02` or `0x12` with two bytes after it, *plus* every
offset an aligned walk decoded as a call or jump. The first half is the
byte-scan upper bound `audit_call_targets.py:call_sites()` reports for the bank
images, and it is the population `pd-common-address-spaces.md`'s sixteen come
out of; the second is a decoded instruction a byte scan should not have missed.
Both halves are kept and `verdict` is what tells them apart. No output mode
drops a row: `refuse_filtering()` is a refusal, for `data_regions.py`'s reason
-- a smaller number nobody can audit is indistinguishable from absence.

**The descent, and what "reachable from here" means.** A walk starts at a
stated entry and decodes forward one instruction at a time, following **both**
arms of every conditional branch, so the answer is a reachable set and not a
guess about the hot path. `lcall` is recorded and the walk continues past it;
`ljmp` ends the walk and its target joins the worklist, so a tail jump is a real
and distinguishable call shape -- which matters here specifically, because
`pd 0x119C` and `pd 0x11C2` have no `ret` at all and their only exit is
`jmp @A+DPTR`. A `jmp @a+dptr` ends the walk and says so: that target is not in
the bytes.

**`enclosing` is a listing fact, not a discovered boundary.** A walk from entry
*E* stops at the lowest committed `pd` listing start strictly above *E* and
records `next listing boundary` among its terminators. Without that rule a
mis-seeded entry runs for thousands of bytes and every call site inside it is
attributed to the wrong function; with it, the attribution is a reading of
`ec/decompiled/listing-index.csv` and this tool decides none of it. A row's
`ends` is the terminator set of the walk seeded at that row's `enclosing` --
one cell, one meaning, and it is why `--max-depth` and `--max-insns` are named
on the rows whose walk they cut and blank on the rows whose walk they did not.

**The verdict is about framing, and nothing here is a confirmed caller.**
`decoded-lcall` means an aligned walk from a stated entry decoded this offset as
an `lcall`, and `audit_call_targets.py`'s docstring is the reason that is not
more than it says: framing is unsettled in *both* directions there, and its
anchored count is "demonstrably not phantom-free". So a decoded site is a call
as read by this walk from these seeds, and an undecoded one is
`unreached-by-this-method` -- never absent, never data.
`disasm8051.converges_from()`'s pair (`frame_onto`/`frame_over`) is carried on
every row and never collapsed to one number, because its own docstring says to
read the pair.

**The two coverage figures are two methods', and they are printed side by
side.** What this walk reached, and what the committed listings reach. Neither
is "these bytes are code": the first is what a stated entry set decodes to, the
second is what a quarter of the image has a listing for. The second is
re-derived here from the listings' own instruction streams rather than from
`listing-index.csv`'s `size` column, so a hand-edited cell cannot make the
figure quietly wrong. The two agree on the committed tree, and
`--check` derives rather than quotes;
`docs/findings/pd-common-address-spaces.md` is where that quantity was first
measured, over an earlier and smaller set of listings.

**The eight seed verdicts correct the issue's premise rather than planning
around it.** The issue says the `.asm` headers at `pd/10F1.asm`, `1229.asm` and
others note that a function boundary "came from a call-target byte scan and is a
hypothesis". No `pd` `.asm` carries that note -- it is in eight `pd/*.c` files,
whose comments cite the `.asm` beside them. `listing-index.csv` gives all eight
`seed_basis=annotation`. `--seed-verdicts` measures what the walk makes of
them, and `docs/findings/pd-call-target-census.md` states the correction with
the wrong version left visible, the way CLAUDE.md asks for a retraction.

Usage:
    python3 ec/tools/pd_call_targets.py --report
    python3 ec/tools/pd_call_targets.py --csv > ec/annotations/pd-call-targets.csv
    python3 ec/tools/pd_call_targets.py --check
    python3 ec/tools/pd_call_targets.py --for-target 0x11C2
    python3 ec/tools/pd_call_targets.py --seed-verdicts
    python3 ec/tools/pd_call_targets.py --self-test

`--check` regenerates the CSV and diffs it, then re-derives every figure the
write-up's pinned-figures block states. It refuses a missing CSV rather than
creating one, and refuses any write mode alongside itself.

Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch: the
plan stage's push token has no `workflow` scope. The recipe for adding it is in
`../../docs/findings/pd-call-target-census.md`; until a human lands it, the
suite covers `--check` on every `bash tools/run-tests.sh`.
"""
import argparse
import bisect
import collections
import csv
import difflib
import io
import os
import re
import sys

from data_regions import load as load_data_regions, region_at
from disasm8051 import (OPCODE_LEN, REL_OPCODES, case_table_len, converges_from,
                        inline_arg_len, mnemonic, paged_target, relative_target)
from pd_image_census import vector_table
from trace_xdata_refs import PD_MARKER, REGIONS

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
EC = os.path.join(HERE, os.pardir)
ANNOT = os.path.join(EC, "annotations")
FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
INDEX_CSV = os.path.join(EC, "decompiled", "listing-index.csv")
CALLEES_CSV = os.path.join(ANNOT, "call-graph-callees.csv")
SITES_CSV = os.path.join(ANNOT, "pd-call-targets.csv")
PAGE = os.path.join(REPO, "docs", "findings", "pd-call-target-census.md")

PROGRAM = "pd"
PD_REGION = "pd-image"
PD_LEN = 0x10000

# The byte-scan upper bound, and the same two opcodes
# `audit_call_targets.py`'s CALL_OPCODES names: `ljmp` and `lcall`, the 3-byte
# absolute forms. The paged and PC-relative families are not here, and the
# write-up says why: they are `bank-paged-call-targets.csv` and
# `bank-relative-branch-targets.csv` for the bank images, and a second tool's
# census inside a first tool's file is how two vocabularies merge. A
# `--paged-csv` mode is the obvious follow-up.
CALL_OPCODES = (0x02, 0x12)

# The two dispatchers the question names. Both are here rather than only the
# first because neither has a `ret` -- the only exit is `jmp @A+DPTR` -- so a
# tail `ljmp` into either is a real call shape and the `ljmp` half of
# CALL_OPCODES is not decorative.
CODE_TABLE_DISPATCHERS = (0x119C, 0x11C2)

# The verdict vocabulary, closed, in the order `verdict_of()` applies it.
#
#   decoded-lcall           an aligned walk from a stated entry decoded this
#                           offset as an `lcall`
#   decoded-ljmp            ... as an `ljmp`
#   operand                 an aligned walk decoded a *longer* instruction
#                           through this byte, so the byte is an operand of a
#                           real instruction rather than an opcode. This is the
#                           refutation the issue asked for: a `12 11 c2` inside
#                           an instruction's operand is a candidate that gets
#                           refuted rather than a caller.
#   mid-instruction         a committed listing holds an instruction covering
#                           this byte and no walk from the entry set decoded it
#                           -- a disagreement between two committed readings,
#                           which is an answer in its own right
#   data-region             it falls inside a listed `data-regions.yaml` region
#                           and nothing above applies
#   unreached-by-this-method
#                           none of the above: a byte scan found it and no walk
#                           from the stated entries decoded anything there.
#                           Never "absent", never "data" -- a search that
#                           reached nothing has found nothing about itself.
VERDICTS = ("decoded-lcall", "decoded-ljmp", "operand", "mid-instruction",
            "data-region", "unreached-by-this-method")
DECODED_VERDICTS = ("decoded-lcall", "decoded-ljmp")
# Named because the token is the whole point: a search that reached nothing has
# found nothing *about itself*, and a verdict called `not-found` is read as
# `absent` about a third of the time.
VERDICT_UNREACHED = "unreached-by-this-method"

# The terminator vocabulary, borrowed from `walk_branch_arms.py` so one event
# does not acquire two names in this tree, plus the one this tool adds:
# `next listing boundary` is `enclosing`'s own rule and nothing else ends a walk
# on it. A terminator cell is a vocabulary term with an address or a bound
# appended in `walk_branch_arms.py`'s idiom, and `ends_vocabulary()` is what
# makes the vocabulary closed -- a cell naming anything else is a cell no reader
# can classify, and the suite fails on it.
END_RET = "ret"
END_RETI = "reti"
END_TAIL = "tail jump to a callee"
END_INDIRECT = "indirect jump -- target not resolvable from the bytes"
END_BOUNDARY = "next listing boundary"
END_LOOP = "loop"
END_DEPTH = "depth limit"
END_BUDGET = "instruction budget"
END_IMAGE = "index past the end of the image"
ENDS_VOCABULARY = (END_RET, END_RETI, END_TAIL, END_INDIRECT, END_BOUNDARY,
                   END_LOOP, END_DEPTH, END_BUDGET, END_IMAGE)

# The entry set's three seeded sources, named because the denominator is only
# auditable if a reader can say which rows came from where. `discovered` is the
# fourth and is not seeded: a target this walk decoded that is not a seed
# enters the worklist like any other entry, which is what closes the loop
# instead of running one pass and stopping.
SRC_VECTOR = "vector"
SRC_LISTING = "listing"
SRC_CALLGRAPH = "call-graph"
SRC_DISCOVERED = "discovered"
ENTRY_SOURCES = (SRC_VECTOR, SRC_LISTING, SRC_CALLGRAPH, SRC_DISCOVERED)

# What a cell reads when the lookup found nothing. Spelled out, because an
# empty string would read as an answer rather than as the absence of one.
NOT_LISTED = "not listed"
NO_WALK = "no walk seeded above this address"

# The two bounds. A transfer depth, and an instruction budget **per seeded
# walk** rather than for the whole descent, so that a bound is attributable to
# the walk it cut instead of to whichever seed happened to run last. Both are
# named in the cell, in `trace_xdata_refs.budget_end()`'s idiom: a bound is not
# a branch and there is nothing to follow past it, so a reader looking at
# `max_insns (2000) exhausted` has to be able to see which 2000 produced it.
MAX_DEPTH = 16
MAX_INSNS = 2000

COLUMNS = ["file_offset", "runtime", "candidate", "verdict", "target",
           "enclosing", "ends", "frame_onto", "frame_over", "in_listing",
           "region"]

# The address columns, rendered as hex the way the sibling tables carry them, so
# a reader pasting one into `disasm8051.py --at` gets the right thing. Written
# as a bare integer a 16-bit address is a decimal number that looks like a file
# offset and is not one.
HEX_COLUMNS = {"file_offset": 5, "runtime": 4, "candidate": 4, "target": 4,
               "enclosing": 4}

# The listing's own address column, anchored to the start of a line: the operand
# text carries four-hex-digit branch targets of its own, and an unanchored match
# reads those as addresses. `pd_entry_forms.py`'s LINE_RE also reads the byte
# columns; this census needs the address alone, so the narrower pattern is the
# one written here.
LISTING_LINE_RE = re.compile(r"^([0-9A-Fa-f]{4})\s")

# The eight `pd` listings whose committed `.c` files say the function boundary
# came from a call-target byte scan and is a hypothesis. Named rather than
# found by a grep, so a landing write-up cannot silently change the set the
# write-up discusses; `--self-test` holds the list against the files that
# actually carry the sentence, and against `listing-index.csv`'s `seed_basis`.
#
# The sentence is in **two spellings**, which is why a grep for one of them
# finds seven files and not eight: seven say "call-target byte scan" and
# `1229.c` says "call-target-scan hypothesis". A single-spelling search would
# have dropped the one file the issue names alongside the others, so
# `SEED_SENTENCE_RE` matches both and `--self-test` holds the list against the
# regex rather than against a literal.
SEED_SENTENCE_RE = re.compile(r"call-target[ -]byte scan|call-target-scan")

SEED_LISTINGS = (0x0EF3, 0x10F1, 0x1229, 0x9A1B, 0x9A90, 0xF109, 0xF126,
                 0xF4AB)


class Refusal(Exception):
    """Something this tool will not describe, and why.

    The contract `pd_image_census.py:read_region()` implements: raised rather
    than returned, because every caller has nothing useful to say about a dump
    whose PD region is not this image -- there is no report to print and no
    table to check, and an empty table is not an answer.
    """


def refuse_filtering() -> None:
    """Why this module offers no way to drop a candidate site.

    `data_regions.py`'s function for `data_regions.py`'s reason: a site inside a
    listed region is labelled in the `region` column and still counted, and a
    filter mode would report a smaller number nobody can audit -- which is
    indistinguishable from absence, the failure `docs/findings.md` §4c records
    twice. It is a function with a name so a future edit adding a filtering mode
    has to delete this to do it, and `--self-test` calls it so the deletion is a
    red run rather than a review comment.
    """
    raise SystemExit(
        "error: no output mode filters rows out of this census. A candidate "
        "inside a\n       listed data region is labelled in the `region` "
        "column, not dropped: dropping it\n       makes a future scan's zero "
        "look like absence, which is the failure\n       docs/findings.md §4c "
        "records twice already.")


def repo_path(path: str) -> str:
    return os.path.relpath(path, REPO)


def seed_claim_files():
    """[file stem] for every committed `pd` `.c` file carrying the claim.

    The measurement the correction rests on, and the reason it is a function
    rather than a paragraph: the claim is in the *generated* `.c` files and not
    in any `.asm`, and `--self-test` holds `SEED_LISTINGS` against this. A
    ninth file carrying the sentence, or `1229.c` losing its hyphenated
    spelling, turns the list stale and the check red.
    """
    directory = os.path.join(EC, "decompiled", PROGRAM)
    try:
        names = sorted(os.listdir(directory))
    except OSError as e:
        raise Refusal(f"cannot read {repo_path(directory)}: {e}")
    out = []
    for name in names:
        if not name.endswith(".c"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8",
                  errors="replace") as f:
            if SEED_SENTENCE_RE.search(f.read()):
                out.append(name[:-2])
    return sorted(out)


# --------------------------------------------------------------------------
# The region


def pd_base() -> int:
    """File offset the PD image's runtime 0x0000 sits at.

    Read off `trace_xdata_refs.REGIONS` rather than written as 0x20000, so this
    tool and the PD tools that already ask the question cannot disagree about
    where the second program starts. `PD_MARKER` is the *marker's* file offset
    and not the image's -- the marker sits 0x40 bytes into a program that starts
    at 0x20000 -- so using the marker as the base reads every one of the 64 KiB
    0x40 bytes early, which still decodes, at the wrong address.
    """
    lo, base = next((lo, base) for name, lo, _, base, _ in REGIONS
                    if name == PD_REGION)
    return lo - base


def read_region(firmware: str = FIRMWARE):
    """(the 64 KiB PD image, how it was identified) or raise Refusal.

    The marker is *checked*, not assumed, and a dump without it is refused
    rather than reported as an empty region: a refusal that names the offset is
    a measurement and an empty table is not.

    Restated rather than imported from `pd_image_census.py`, which keeps the
    same contract -- that module's `read_region()` is a census function that
    also carries a provenance half over the vendor zip, and importing the whole
    of it for three lines would couple this tool to that tool's file list.
    `vector_table()` *is* imported from there, for the reason its geometry
    should not be walked twice.
    """
    with open(firmware, "rb") as f:
        dump = f.read()
    base = pd_base()
    if len(dump) < base + PD_LEN:
        raise Refusal(f"{repo_path(firmware)} is {len(dump)} bytes, too short "
                      f"to hold a region at 0x{base:05X}-"
                      f"0x{base + PD_LEN - 1:05X}; not described")
    off, magic = PD_MARKER
    found = dump[off:off + len(magic)]
    if found != magic:
        raise Refusal(
            f"no {magic.decode()!r} marker at file 0x{off:05X} in "
            f"{repo_path(firmware)} -- found {found!r} there. Whatever is at "
            f"0x{base:05X} in that dump is not this image, and this tool "
            f"describes only this one; it will not report the region as empty")
    return dump[base:base + PD_LEN], (
        f"marker {magic.decode()!r} read at file 0x{off:05X}")


# --------------------------------------------------------------------------
# The entry set
#
# Every source is read from the committed file that owns it and none is
# re-derived from the image. The vector geometry in particular is
# `pd_image_census.vector_table()`, imported, because that module's `--self-test`
# holds the 8-aligned answer as *wrong* on these bytes and a second walk here
# would have to be pinned against it a second time.


def vector_seeds(region: bytes):
    """[target] for the six vector-table entries.

    `vector_table()` reads the table at `0x00` and `0x03 + n*8` and stops at the
    first byte that is not an `LJMP`; the six entries it returns are the ones
    the reset vector and the five interrupt wrappers reach. The *targets* are the
    seeds, not the slots: a vector slot is an `ljmp`, and the code it reaches is
    what a walk starts in.
    """
    return [target for _off, target in vector_table(region)]


def listing_entries(index_rows):
    """Sorted [entry address] for every `pd` row of `listing-index.csv`.

    The `addr` column is a function's entry, which is the seed a walk wants and
    the boundary a walk stops at -- the same list, read twice, so the entry set
    and the attribution cannot drift apart. The `size` column is not an extent
    and nothing here reads it as one: `pd_entry_forms.py`'s docstring is the
    argument, and read as an extent it stops a body short of its own `ret`.
    """
    return sorted(int(r["addr"], 16) for r in index_rows
                  if r["program"] == PROGRAM)


def callgraph_entries(callee_rows):
    """Sorted [entry address] for every `pd` row of `call-graph-callees.csv`.

    The overlap with the listing seeds is *measured* and printed, never assumed
    either way: a reader who added the two lists without knowing which way the
    overlap runs would credit the entry set with more reachability than it has.
    """
    return sorted(int(r["addr"], 16) for r in callee_rows
                  if r["scope"] == PROGRAM)


def entry_set(region: bytes, index_rows, callee_rows):
    """[(entry address, sources)] for the whole stated entry set, sorted.

    Every source that would have seeded an address is recorded for it rather
    than the first one read winning, so the per-source breakdown is a property
    of the seeds and not an artefact of the order they were read in.
    """
    found = collections.defaultdict(list)
    for target in vector_seeds(region):
        found[target].append(SRC_VECTOR)
    for addr in listing_entries(index_rows):
        found[addr].append(SRC_LISTING)
    for addr in callgraph_entries(callee_rows):
        found[addr].append(SRC_CALLGRAPH)
    return [(addr, tuple(found[addr])) for addr in sorted(found)]


def entry_stats(entries, discovered):
    """[{source: count, 'distinct': n}] for the entry set and its breakdown.

    The per-source counts and `distinct` are printed together for a reason: the
    per-source numbers sum to more than `distinct` wherever a row has more than
    one source, and a reader who added them to get the walk size has added an
    overlap. `discovered` is 0 for a first pass and is filled in from `walk()`'s
    return value, so a run that never discovers anything says so rather than
    omitting the row.
    """
    by = {s: 0 for s in ENTRY_SOURCES}
    for _addr, srcs in entries:
        for s in srcs:
            by[s] += 1
    by["distinct"] = len(entries)
    by[SRC_DISCOVERED] = len(discovered)
    return by


# --------------------------------------------------------------------------
# The descent


def budget_end(max_insns: int) -> str:
    """The token for a walk that used every instruction it was given.

    A function rather than a constant, for `trace_xdata_refs.budget_end()`'s
    reason: the number is the walk's own argument, and a reader looking at a
    `max_insns (2000) exhausted` cell has to be able to see which 2000 produced
    it.
    """
    return f"max_insns ({max_insns}) exhausted"


def ends_vocabulary(cell: str):
    """[vocabulary term] for one terminator cell.

    What makes the vocabulary closed rather than a convention: a cell naming
    anything else -- a bare number, a new word -- is a cell a reader cannot
    classify, and the suite fails on it. Matched longest-first so
    `index past the end of the image` is not read as `index` and
    `next listing boundary` is not truncated.
    """
    return [term for term in sorted(ENDS_VOCABULARY, key=len, reverse=True)
            if term in cell]


def decode_block(region: bytes, pc: int, depth: int, max_depth: int,
                 budget: list, boundary: int, pending: list, seen: set,
                 out: dict) -> None:
    """One linear block, and whatever it hands back to `pending`.

    The unit is the linear block: decode forward from one address until a
    control-flow instruction, then start again wherever it leads. A conditional
    branch contributes both sides, so the result is "reachable from here" and
    not a guess about the hot path. `lcall` is recorded and the walk continues
    past it, because the code after a call is still the block's own. `ljmp` and
    `ajmp` are tail jumps: the block ends and the target joins the worklist,
    because the walk has no caller to return to.

    `budget` is a one-element list rather than an integer so the whole
    worklist shares one budget for a walk and the walk terminates; it is a
    mutable carrier, not a return value, and `budget_end()` names the number
    the cell carries.

    The inline-argument and case-table skips are `disasm8051`'s, called for the
    reason `converges_from()` calls them: a walk that stepped *through*
    0x104D's four argument bytes would decode them as instructions and then
    disagree with the framing evidence carried on every row. On this image
    `case_table_len()` is always 0 -- `CASE_TABLE_CALLS` names the main EC's
    0x7151 -- and it is called anyway so a future entry cannot make this walk
    and `converges_from()` disagree silently.

    `seen` holds every address decoded, not just every block start, so a branch
    back into the middle of a block already crossed is one loop and not a
    second decode of the same instruction.
    """
    while True:
        if pc >= len(region):
            out["ends"].append(f"{END_IMAGE} at 0x{pc:04X}")
            return
        if pc >= boundary:
            out["ends"].append(f"{END_BOUNDARY} at 0x{boundary:04X}")
            return
        if budget[0] <= 0:
            out["ends"].append(budget_end(out["max_insns"]))
            return
        op = region[pc]
        n = OPCODE_LEN[op]
        if pc + n > len(region):
            out["ends"].append(f"{END_IMAGE} at 0x{pc:04X}")
            return
        budget[0] -= 1
        out["starts"][pc] = op
        extra = inline_arg_len(region, pc)
        table = case_table_len(region, pc)
        out["operands"].update(range(pc + 1, pc + n + extra + table))

        if op in CALL_OPCODES:
            out["sites"][pc] = ("lcall" if op == 0x12 else "ljmp",
                               (region[pc + 1] << 8) | region[pc + 2])
            out["targets"].add((region[pc + 1] << 8) | region[pc + 2])
            if op == 0x02:                     # ljmp: a tail jump
                out["ends"].append(END_TAIL)
                if depth < max_depth:
                    pending.append(
                        ((region[pc + 1] << 8) | region[pc + 2], depth + 1))
                return
        elif op in (0x22, 0x32):              # ret / reti
            out["ends"].append(END_RET if op == 0x22 else END_RETI)
            return
        elif op == 0x73:                      # jmp @a+dptr
            out["ends"].append(END_INDIRECT)
            return
        elif op & 0x1F in (0x01, 0x11):       # ajmp / acall
            target = paged_target(op, region[pc + 1], pc)
            out["targets"].add(target)
            out["ends"].append(END_TAIL)
            if depth < max_depth:
                pending.append((target, depth + 1))
            return
        elif op in REL_OPCODES or op == 0x80:
            target = relative_target(op, region[pc + n - 1], pc)
            if depth < max_depth:
                pending.append((target, depth + 1))
            else:
                out["ends"].append(f"{END_DEPTH} ({max_depth}) at "
                                   f"0x{target:04X}")
            if op == 0x80:                    # sjmp: a transfer, not a split
                out["ends"].append(END_TAIL)
                return
        pc += n + extra + table


def walk(region: bytes, entries, starts, max_depth: int = MAX_DEPTH,
         max_insns: int = MAX_INSNS):
    """(result, discovered) -- the whole descent over `region`.

    `result` carries the decoded instruction starts, the operand bytes, the
    call/jump sites, every terminator, the per-walk terminator list, the
    instruction count, and the decoded byte extent. `discovered` is the sorted
    set of targets the walk decoded that were not seeds -- what `--report`
    prints as the `discovered` row, and the fact that the loop closed over its
    own output rather than running one pass and stopping.

    Every seeded walk gets its own terminator list, its own budget and its own
    `seen` set, so code two seeds share is decoded once per seed; the `ends` a
    reader reads on a row is the terminator of the walk that owns the listing
    the row is in. `insns` is therefore the *distinct* decoded starts rather
    than a sum over the seeds: `starts` is one dict, so an address two seeds
    reach is one entry, and it is that entry count `--report` prints beside
    `extent`, so the instruction count and the byte count describe one decode.
    """
    out = {"starts": {}, "operands": set(), "sites": {}, "targets": set(),
           "ends": [], "by_entry": {}, "insns": 0, "max_insns": max_insns,
           "extent": set()}
    for addr, _srcs in entries:
        before = len(out["ends"])
        pending = [(addr, 0)]
        budget = [max_insns]
        seen = set()
        boundary = next_boundary(starts, addr)
        while pending:
            pc, depth = pending.pop(0)
            if pc in seen:
                out["ends"].append(f"{END_LOOP} back to 0x{pc:04X}")
                continue
            seen.add(pc)
            decode_block(region, pc, depth, max_depth, budget, boundary,
                         pending, seen, out)
        out["by_entry"][addr] = out["ends"][before:]
    for pc, op in out["starts"].items():
        out["extent"].update(range(pc, pc + OPCODE_LEN[op]))
    out["insns"] = len(out["starts"])
    seeded = {a for a, _ in entries}
    return out, sorted(t for t in out["targets"] if t not in seeded)


def next_boundary(starts, addr: int) -> int:
    """The lowest committed listing start strictly above `addr`.

    `enclosing`'s other half, in one function because the walk and the report
    must not read it differently. Half-open at the top: a listing start *at*
    `addr` is that entry's own listing and not its end, so a walk seeded there
    is given the next listing to run to rather than stopping on its own first
    instruction.
    """
    lo = bisect.bisect_right(starts, addr)
    return starts[lo] if lo < len(starts) else PD_LEN


def enclosing_of(starts, addr: int):
    """The committed listing a walk from `addr` is inside, or None.

    Nearest start at or below, and deliberately not a membership test: the
    export's bodies overlap, and `pd_image_census.address_owners()` holds a
    tie-break for that (the latest-starting owner wins) which this tool does not
    need, because it never asks which listing a *byte* belongs to. It asks which
    walk covers a row, and a walk is seeded at a start and bounded by the next
    one, so a row in the overlap is in the walk seeded at the later start and
    `ends` says which walk that was.
    """
    i = bisect.bisect_right(starts, addr) - 1
    return starts[i] if i >= 0 else None


# --------------------------------------------------------------------------
# The verdict


def verdict_of(candidate: int, starts: dict, operands: set,
               listing_bytes: set, region_name) -> str:
    """The one verdict for `candidate`, from the four readings of it.

    The order is `VERDICTS`' and each step is a *different* question:

      * did an aligned walk from a stated entry decode this offset as a call or
        a jump -- the two things this census exists to separate from the rest;
      * did an aligned walk decode a longer instruction through this byte, so
        the byte is an operand of a real instruction;
      * does a committed listing hold an instruction covering this byte that no
        walk decoded -- a disagreement between two committed readings, which is
        an answer in its own right and not a fallthrough;
      * does it fall inside a listed data region;
      * otherwise `unreached-by-this-method`, which is what a search that
        reached nothing found out about itself.

    Every argument is a plain value, so a suite can call this with a stub and
    read the branch it wanted rather than a whole survey.
    """
    op = starts.get(candidate)
    if op in CALL_OPCODES:
        return "decoded-lcall" if op == 0x12 else "decoded-ljmp"
    if op is not None or candidate in operands:
        return "operand"
    if candidate in listing_bytes:
        return "mid-instruction"
    if region_name is not None:
        return "data-region"
    return VERDICT_UNREACHED


# --------------------------------------------------------------------------
# The census


def candidate_sites(region: bytes):
    """Every offset whose byte is `0x02` or `0x12` with two bytes after it.

    The byte-scan upper bound, and the population
    `pd-common-address-spaces.md`'s sixteen and nine come out of. Stops at
    `len(region) - 2` so both operand bytes are inside the image, for
    `audit_call_targets.call_sites()`'s reason: the alternative reads the first
    byte of the next region as an operand, which is a cross-region claim.

    It over-counts, and pairing it with the walk rather than replacing it is the
    point -- those two bytes also occur as opcode bytes inside data tables, and
    `verdict` is what says which reading won.
    """
    return [i for i in range(len(region) - 2) if region[i] in CALL_OPCODES]


def listing_starts(region: bytes):
    """{address: listing file name} for every committed `pd` `.asm` instruction.

    The listings' own instruction streams, not `listing-index.csv`'s `size`
    column: that column is the sum of a listing's instruction bytes and the
    listing is not contiguous, so a `size`-keyed lookup attributes a site to a
    function that does not contain it -- the defect
    `pd_image_census.owning_function()`'s docstring names and the reason this
    reads the files.

    Only the address is taken, and the *length* comes from the image at the same
    address, for `disasm8051.OPCODE_LEN`. That is deliberate: it is the same
    length `converges_from()` and the walk use, so the coverage figure this
    prints and the framing evidence on every row are the same decoder's, and a
    listing line that disagreed with the image would change the figure rather
    than being quietly believed.
    """
    out = {}
    directory = os.path.join(EC, "decompiled", PROGRAM)
    try:
        names = sorted(os.listdir(directory))
    except OSError as e:
        raise Refusal(f"cannot read {repo_path(directory)}: {e}")
    for name in names:
        if not name.endswith(".asm"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8",
                  errors="replace") as f:
            for line in f:
                m = LISTING_LINE_RE.match(line)
                if m:
                    out.setdefault(int(m.group(1), 16), name)
    return out


def below_entry_listings(streams: dict):
    """{listing file: (entry, lowest instruction start)} for every committed
    `pd` listing whose body begins *below* its own entry address.

    The method's own blind spot, measured rather than described. A walk runs
    forward from a seed and `enclosing` bounds it at the next listing start, so
    a listing whose export begins above its first instruction has a span no
    walk seeded at that entry can reach -- the bytes are below the seed. The
    `mid-instruction` verdict is where this shows: a committed listing holds an
    instruction covering a candidate byte, and no walk decoded it.

    Four of the committed `pd` listings have this shape, and they are named
    here because a reader who sees a `mid-instruction` row and no `decoded-*`
    row for the same listing should be able to say which of the two causes it
    was. The other cause is ordinary: a listing can hold an instruction no
    walk from any seed reaches, because the walk that would have fallen into it
    ended at a `ret` or a tail jump first.
    """
    out = {}
    for name in set(streams.values()):
        entry = int(name[:-4], 16)
        addrs = [a for a, f in streams.items() if f == name]
        if addrs and min(addrs) < entry:
            out[name] = (entry, min(addrs))
    return out


def listing_extent(region: bytes, starts_map: dict) -> set:
    """Every address a committed `pd` listing holds, from its instruction
    lengths.

    `pd_image_census.py` measures the same quantity from `listing-index.csv`'s
    `size` column, and the two agree byte for byte on the committed tree --
    `size` *is* a listing's instruction bytes, which is also what summing
    `OPCODE_LEN` over the listing's own decoded starts gives. The figure is
    derived from the listings rather than read from the column anyway, because a
    coverage number a hand-edited cell can move is not a measurement.

    A byte two overlapping listings hold is counted twice. That is the
    deliberate direction -- an over-count of coverage understates the gap the
    figure exists to show -- and `pd_image_census.overlaps()` is where the
    overlap itself is measured.
    """
    out = set()
    for addr in starts_map:
        if 0 <= addr < len(region):
            out.update(range(addr, addr + OPCODE_LEN[region[addr]]))
    return out


def boundary_ablation(region: bytes, entries, bounded, max_depth: int = MAX_DEPTH,
                      max_insns: int = MAX_INSNS):
    """What the `enclosing` boundary rule actually decides, as measured numbers.

    The rule exists so that `enclosing` is a reading of
    `listing-index.csv` rather than a boundary this tool discovered, and it is
    worth knowing whether it is also deciding any *verdict*. A rule described as
    load-bearing that turns out to decide nothing is a rule nobody can trust on
    the rows where it does, and a rule that quietly decides many is a rule that
    belongs in the write-up's "what this does not establish".

    So the same descent is run a second time with every walk bounded by the end
    of the image rather than by the next listing start, and the two decoded-site
    sets are compared. `bounded` is the result the caller already has, passed in
    rather than recomputed -- the ablation costs one walk, not two, and a caller
    that passed a different result would be comparing two different questions.

    Returns `(extra sites, extra bytes)`: what the unbounded walk decodes that
    the bounded one does not, in each unit.
    """
    unbounded, _ = walk(region, entries, [0], max_depth, max_insns)
    return (sorted(set(unbounded["sites"]) - set(bounded["sites"])),
            len(unbounded["extent"]) - len(bounded["extent"]))


def survey(region: bytes, index_rows, callee_rows, data_regions,
           max_depth: int = MAX_DEPTH, max_insns: int = MAX_INSNS):
    """(rows, context) -- one pass, so the CSV, `--check` and the report cannot
    disagree.

    `context` holds the walk's totals, the entry breakdown and the terminator
    tally, because the coverage figures are properties of the walk and not of
    any one row.
    """
    base = pd_base()
    entries = entry_set(region, index_rows, callee_rows)
    starts = listing_entries(index_rows)
    streams = listing_starts(region)
    extent = listing_extent(region, streams)
    result, discovered = walk(region, entries, starts, max_depth, max_insns)

    candidates = sorted(set(candidate_sites(region)) | set(result["sites"]))
    rows = []
    for site in candidates:
        op = region[site]
        onto, over = converges_from(region, site)
        listed = region_at(data_regions, base + site)
        verdict = verdict_of(site, result["starts"], result["operands"], extent,
                             listed["name"] if listed else None)
        enclosing = enclosing_of(starts, site)
        walk_ends = result["by_entry"].get(enclosing, [])
        # The `target` cell is what the bytes at this site name, decoded or not,
        # so a row no walk reached still carries the operand a byte scan read.
        # On a decoded row it is the same number the walk resolved; on any other
        # row it is a *candidate* target and the `verdict` says which it is.
        target = (result["sites"][site][1] if site in result["sites"]
                  else (region[site + 1] << 8) | region[site + 2])
        rows.append({
            "file_offset": base + site,
            "runtime": site,
            "candidate": site,
            "verdict": verdict,
            "target": target,
            "enclosing": enclosing,
            "ends": ends_cell(walk_ends) if walk_ends else NO_WALK,
            "frame_onto": onto,
            "frame_over": over,
            "in_listing": "yes" if site in streams else "no",
            "region": listed["name"] if listed else NOT_LISTED,
        })
    terminators = collections.Counter()
    for ends in result["by_entry"].values():
        for cell in ends:
            for term in ends_vocabulary(cell):
                terminators[term] += 1
    context = {
        "entries": entries,
        "entry_stats": entry_stats(entries, discovered),
        "discovered": discovered,
        "insns": result["insns"],
        "decoded_bytes": len(result["extent"]),
        "image_bytes": len(region),
        "listing_bytes": len(extent),
        "listing_starts": len(streams),
        "terminators": dict(terminators),
        "by_entry": result["by_entry"],
        "decoded_sites": set(result["sites"]),
        "decoded_starts": set(result["starts"]),
        "byte_scan": len(candidate_sites(region)),
        # Vocabulary-complete rather than only the verdicts some row happens to
        # carry. A counter built from the rows omits a term nothing hit, and an
        # omitted term reads as an absence of the *category* rather than a zero
        # in it -- which for `data-region` is the honest answer on this image,
        # since `data-regions.yaml` lists no region in the PD extent at all.
        "verdicts": {v: sum(1 for r in rows if r["verdict"] == v)
                     for v in VERDICTS},
        "data_region_extents": sum(1 for r in data_regions
                                   if r["file_lo"] >= base),
        "below_entry": below_entry_listings(streams),
        "listing_starts_undecoded": sorted(a for a in streams
                                           if a not in result["starts"]),
        "ablation": boundary_ablation(region, entries, result, max_depth,
                                      max_insns),
    }
    return rows, context


def ends_cell(ends) -> str:
    """A walk's terminators as one cell, in vocabulary order and deduplicated.

    Sorted rather than in the order they fired, because two runs over the same
    tree have to produce the same cell byte for byte for `--check` to be a check
    at all. A terminator that fired twice is one fact about the walk and is
    written once; the count of fires is `--report`'s terminator table.
    """
    terms = []
    for cell in ends:
        for term in ends_vocabulary(cell):
            if term not in terms:
                terms.append(term)
    order = {t: i for i, t in enumerate(ENDS_VOCABULARY)}
    return "; ".join(sorted(terms, key=lambda t: order[t]))


def csv_values(row):
    out = []
    for c in COLUMNS:
        v = row[c]
        if v is None:
            out.append("")
        elif c in HEX_COLUMNS:
            out.append(f"0x{v:0{HEX_COLUMNS[c]}X}")
        else:
            out.append(str(v))
    return out


def csv_table(rows) -> str:
    """`pd-call-targets.csv` as a string, for `--check` to diff.

    A string rather than a write to stdout, for the reason
    `pd_image_census.csv_table()` gives: `--check` compares the same bytes
    `--csv` prints, and the committed file is the product of the command this
    module's docstring names. Written with the csv module's own dialect, so the
    committed file carries its CRLF terminator and `--check` reads it with
    `newline=""` -- universal-newline translation would rewrite every row and
    report a difference on every run, which is a check nobody trusts.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for row in rows:
        w.writerow(csv_values(row))
    return buf.getvalue()


# --------------------------------------------------------------------------
# --check


def pinned_figures(path: str = PAGE):
    """{key: value} from the write-up's pinned-figures block.

    A fenced block of `key = value` lines that `--check` re-derives, in
    `pd_image_census.pinned_figures()`'s shape. The block exists because a
    figure written down in prose is a figure nothing holds, and every number in
    the write-up's tables is either a count of this repository's own files or a
    count over the committed image. CLAUDE.md's rule is that such a number is
    stated once, beside the command that produced it, and held by the tool that
    re-derives it -- which is this.
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise Refusal(f"cannot read {repo_path(path)}: {e}")
    m = re.search(r"```text\n# pd-call-target-census pinned figures\n(.*?)```",
                  text, re.S)
    if m is None:
        raise Refusal(f"{repo_path(path)} has no `pd-call-target-census pinned "
                      f"figures` block for --check to read")
    out = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def figures(region: bytes, rows, context) -> dict:
    """Every figure the write-up states, re-derived from the bytes.

    Keys are the write-up's, and `check_figures()` walks the **union** of both
    key sets: a key the page pins and this does not produce is a missing figure,
    and a key this produces and the page does not pin is one the page could
    drift on. A check that walked only the page's keys would report clean on a
    page that had gained a figure, which is the drift it exists to catch.

    Nothing here is a total of the tree that nothing holds: the entry and
    listing figures are counts over committed files, re-derived from them on
    every run, and the suite asserts the *relationships* between them rather
    than their values.
    """
    by = context["verdicts"]
    stats = context["entry_stats"]
    return {
        "base_offset": f"0x{pd_base():05X}",
        "image_bytes": str(context["image_bytes"]),
        "candidate_sites": str(len(rows)),
        "candidate_byte_scan": str(context["byte_scan"]),
        "verdicts": " ".join(f"{v}={by[v]}" for v in VERDICTS),
        "entry_distinct": str(stats["distinct"]),
        "entry_vector": str(stats[SRC_VECTOR]),
        "entry_listing": str(stats[SRC_LISTING]),
        "entry_callgraph": str(stats[SRC_CALLGRAPH]),
        "entry_discovered": str(stats[SRC_DISCOVERED]),
        "walk_instructions": str(context["insns"]),
        "walk_decoded_bytes": str(context["decoded_bytes"]),
        "walk_coverage_pct":
            f"{100.0 * context['decoded_bytes'] / context['image_bytes']:.2f}",
        "listing_starts": str(context["listing_starts"]),
        "listing_bytes": str(context["listing_bytes"]),
        "listing_coverage_pct":
            f"{100.0 * context['listing_bytes'] / context['image_bytes']:.2f}",
        "terminators": " ".join(f"{t}={context['terminators'][t]}"
                                for t in ENDS_VOCABULARY
                                if context["terminators"].get(t)),
        "dispatch_sites": " ".join(
            f"0x{t:04X}=" + ",".join(
                f"{r['candidate']:04X}:{r['verdict']}"
                for r in rows if r["target"] == t)
            for t in CODE_TABLE_DISPATCHERS),
        "dispatch_in_listing": " ".join(
            f"0x{t:04X}=" + (",".join(f"{r['candidate']:04X}" for r in rows
                                      if r["target"] == t
                                      and r["in_listing"] == "yes") or "-")
            for t in CODE_TABLE_DISPATCHERS),
    }


def check_figures(pinned, derived) -> int:
    """Exit code for the write-up's figures: 0 when every one re-derives.

    Walks the *union* of both key sets, and that is the half that matters; see
    `figures()`.
    """
    rc = 0
    for key in sorted(set(pinned) | set(derived)):
        if key not in pinned:
            print(f"  {key} = {derived[key]}  <- not pinned by the write-up",
                  file=sys.stderr)
            rc = 1
        elif key not in derived:
            print(f"  {key} = {pinned[key]}  <- the write-up pins it and this "
                  f"tool does not re-derive it", file=sys.stderr)
            rc = 1
        elif pinned[key] != derived[key]:
            print(f"  {key}: write-up says {pinned[key]!r}, the bytes say "
                  f"{derived[key]!r}", file=sys.stderr)
            rc = 1
    if rc == 0:
        print(f"{os.path.basename(PAGE)}: all {len(pinned)} pinned figure(s) "
              f"re-derive")
    return rc


def check_table(generated: str, path: str) -> int:
    """Exit code for the CSV half of `--check`: 0 when this run reproduces it.

    Read with `newline=""` so the comparison is the bytes on disk -- see
    `csv_table()`'s note on the CRLF terminator. A *missing* file is a failure
    rather than something to create: `--check` holds the committed table to the
    command, and a check that writes the file it is checking cannot fail on a
    table nobody generated.
    """
    if not os.path.exists(path):
        print(f"note: {repo_path(path)} does not exist, and --check does not "
              f"create it. Generate it with `--csv` or with the command in the "
              f"write-up.", file=sys.stderr)
        return 1
    try:
        with open(path, newline="") as f:
            on_disk = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{repo_path(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced; the "
          f"file is the product of the command in this module's docstring, so "
          f"regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(),
                                     generated.splitlines(),
                                     "committed", "generated", lineterm="",
                                     n=0):
        print(line, file=sys.stderr)
    return 1


# --------------------------------------------------------------------------
# The report


def report(region: bytes, how: str, rows, context) -> str:
    """The human-readable census.

    Every number here is measured by the call above it, and every zero carries
    the token that says a search ran. It returns one string rather than a dict
    because a report that reads as a claim is the thing the calibration rule is
    about, and the wording is load-bearing rather than decoration.
    """
    out = []
    w = out.append
    stats = context["entry_stats"]
    total = context["image_bytes"]
    w(f"pd_call_targets.py -- the absolute call/jump candidates in the "
      f"ITE8850-PD image at file 0x{pd_base():05X}")
    w(f"  identified by: {how}")
    w("")
    w("1. The entry set")
    w(f"  {stats['distinct']} distinct entries walked. Per source, an address "
      f"seeded by two is")
    w("  counted under both, so these do not sum to the line above:")
    for source in ENTRY_SOURCES:
        w(f"    {source:<11} {stats[source]}")
    w(f"  {len(context['discovered'])} target(s) the walk decoded that are "
      f"not seeds, added to the worklist so the")
    w("  loop closes. Every seed is a committed address -- a vector-table "
      "target, a")
    w("  `listing-index.csv` row or a `call-graph-callees.csv` row. None is "
      "found by scanning")
    w("  the image, which is the whole difference from a linear decode.")
    w("")
    w("2. Coverage, and it is two methods'")
    w(f"  this walk decoded {context['decoded_bytes']} of {total} bytes "
      f"({100.0 * context['decoded_bytes'] / total:.2f}%) as "
      f"{context['insns']} instructions")
    w("    what a stated entry set reaches. It is not a claim that the rest is "
      "data, and the")
    w("    budget named in any `max_insns` cell is why this is not the figure "
      "below.")
    w(f"  the committed `pd` listings hold {context['listing_bytes']} bytes "
      f"({100.0 * context['listing_bytes'] / total:.2f}%)")
    w("    what has a committed listing for it, counted from the listings' own "
      "instruction streams.")
    w("    `listing-index.csv`'s `size` column gives the same number on the "
      "committed tree, and")
    w("    that is not a coincidence -- `size` is a listing's instruction bytes "
      "-- but the figure is")
    w("    derived from the listings here so a hand-edited cell cannot move it "
      "quietly.")
    w("    `pd-common-address-spaces.md` measured the same quantity over an "
      "earlier, smaller set of")
    w("    listings. Neither figure is \"these bytes are code\".")
    w("")
    w("3. The candidates, and no row is filtered out of any of it")
    w(f"  {len(rows)} row(s): every offset whose byte is 0x02 or 0x12 with two "
      f"bytes after it, plus")
    w(f"  every offset the walk decoded as a call or jump "
      f"({context['byte_scan']} by byte scan, "
      f"{len(context['decoded_sites'])} decoded)")
    w("  the second half adds no row on this image, and cannot: an instruction "
      "the walk decodes")
    w("  as `lcall`/`ljmp` is by definition an offset whose byte is 0x12/0x02, "
      "which the byte scan")
    w("  already has. It is in the union so that a decoder given a different "
      "opcode set still")
    w("  cannot lose a decoded site, not because it changed the population "
      "here.")
    for verdict in VERDICTS:
        w(f"    {verdict:<26} {context['verdicts'][verdict]}")
    w("  `refuse_filtering()` is a refusal, not a convention: a site inside a "
      "listed data")
    w("  region is labelled in `region` and still counted, because a smaller "
      "number nobody can")
    w("  audit is indistinguishable from absence.")
    w(f"  the `data-region` row is 0 and the `region` column reads "
      f"`{NOT_LISTED}` throughout because")
    w(f"  `data-regions.yaml` lists {context['data_region_extents']} region(s) "
      f"in the PD extent at all. That is a fact about")
    w("  the annotation map, not about the image: no PD byte is thereby code, "
      "and a region added")
    w("  there would label rows here without changing any count above.")
    w("")
    w("4. The two dispatchers the question names")
    for t in CODE_TABLE_DISPATCHERS:
        sites = [r for r in rows if r["target"] == t]
        decoded = [r for r in sites if r["verdict"] in DECODED_VERDICTS]
        inside = [r for r in sites if r["in_listing"] == "yes"]
        w(f"  0x{t:04X}: {len(sites)} candidate site(s), {len(decoded)} decoded "
          f"by an aligned walk,")
        w(f"           {len(inside)} inside a committed listing")
        w("    " + "  ".join(f"{r['candidate']:04X}={r['verdict']}"
                            for r in sites))
    w("  neither has a `ret` -- the only exit is `jmp @A+DPTR` -- so a tail "
      "`ljmp` into either is a")
    w("  real call shape, and it is counted as one rather than as an opcode "
      "byte in a table.")
    w("")
    w("5. How each seeded walk ended")
    for t in ENDS_VOCABULARY:
        n = context["terminators"].get(t)
        if n:
            w(f"    {t:<48} {n} walk(s)")
    w("  a bound is not a branch: a walk stopped at one saw nothing after it, "
      "and the row it is")
    w("  named on says so in its own `ends` cell, in the vocabulary above and "
      "nothing else.")
    w("")
    w("6. What the walk does not reach, and one reason it cannot")
    undecoded = context["listing_starts_undecoded"]
    w(f"  {len(undecoded)} committed `pd` listing instruction start(s) that no "
      f"seeded walk decodes.")
    w("  `mid-instruction` is where that shows: a committed listing holds an "
      "instruction covering")
    w("  the byte and no walk reached it. Two causes, and only one is a "
      "property of the method:")
    w("    * a listing whose export begins *above* its own first instruction. A "
      "walk runs forward")
    w("      from a seed, so the bytes below that seed are unreachable from it. "
      f"{len(context['below_entry'])}")
    w("      committed `pd` listing(s) have this shape:")
    for name, (entry, low) in sorted(context["below_entry"].items()):
        w(f"        {name}  entry 0x{entry:04X}, first instruction "
          f"0x{low:04X}")
    w("    * a listing whose instructions are simply not on any path the walk "
      "took, because the")
    w("      walk ended at a `ret` or a tail jump first. That is ordinary "
      "reachability, not a")
    w("      defect, and it is why the other count above is not attributed to "
      "the first cause.")
    extra_sites, extra_bytes = context["ablation"]
    w(f"  dropping the boundary rule and letting a walk run to the end of the "
      f"image decodes "
      f"{len(extra_sites)}")
    w(f"  more call/jump site(s) and {extra_bytes} more bytes. The rule is "
      f"there so `enclosing` is a listing")
    w("  fact, and the write-up says what that costs rather than claiming the "
      "rule is free.")
    w("")
    w("7. What this does not establish")
    w("  a `decoded-lcall` row is a call as read by an aligned walk from a "
      "stated entry set.")
    w("  `audit_call_targets.py` holds that framing is unsettled in both "
      "directions and that its")
    w("  anchored count is \"demonstrably not phantom-free\", so no row here is "
      "a confirmed caller.")
    w("  an `unreached-by-this-method` row is not found by this method, and a "
      "`mid-instruction` row is a")
    w("  disagreement between two committed readings rather than a verdict on "
      "either.")
    w("  the boundary rule is not what the 0x11C2 verdicts rest on, and the "
      "ablation above is")
    w("  the measurement: it changes the walk's reach, not which of those "
      "sixteen sites is a call.")
    w("  Nothing here is behavioural: every input is a committed file, and no "
      "register was read back")
    w("  on any hardware.")
    return "\n".join(out)


def print_for_target(region: bytes, target: int, rows) -> int:
    """Every row whose bytes name `target`, decoded at its own offset.

    A query against the survey, not a second scan: the two named dispatchers are
    the two this mode exists for, and running the byte scan again to answer them
    would be a second way for the same number to exist.
    """
    sel = [r for r in rows if r["target"] == target]
    print(f"lcall 0x{target:04X}: {len(sel)} candidate site(s) over the whole "
          f"image")
    if not sel:
        print(f"  not found by this method -- no 0x02/0x12 site in the image "
              f"has 0x{target:04X} as its operand")
        return 0
    for r in sel:
        text = " ".join(mnemonic(region, r["candidate"], r["runtime"]).split())
        encl = (f"0x{r['enclosing']:04X}" if r["enclosing"] is not None
                else "-")
        print(f"  0x{r['candidate']:04X}  file 0x{r['file_offset']:05X}  "
              f"{text:<16} {r['verdict']:<22} in_listing={r['in_listing']:<3} "
              f"enclosing={encl}  frame {r['frame_onto']}/"
              f"{r['frame_onto'] + r['frame_over']}")
    return 0


def seed_verdicts(region: bytes, rows, context, index_rows) -> list:
    """[{listing, seed_basis, seeded, reached, decoded_call, frame}] for the
    eight listings whose `.c` files claim a call-target-scan boundary.

    The issue asks "a control-flow pass says which of those seeds survive", and
    this is the measurement that answers it. It is several questions per listing
    rather than one, because they come apart: is the listing an entry in its own
    right (`seeded`), did a walk decode an instruction at its first address
    (`reached`), was that instruction a call or a jump (`decoded_call`), and does
    `converges_from()` frame it (`frame`).

    `reached` reads the walk's own `starts`, so it is false for a listing start
    no walk decoded -- `--report` counts those in its section 6, and there are
    more than none -- and a column that cannot be false is not a measurement.
    `decoded_call` is the weaker, narrower fact kept beside it: most listings
    open with something that is not a transfer, so the two are not one column.

    `seed_basis` is read from `listing-index.csv` and not from the `.c`
    comment, because the column is the machine-readable half and the comment
    cites a `.asm` header that does not carry the note.
    """
    basis = {int(r["addr"], 16): (r.get("seed_basis") or "")
             for r in index_rows if r["program"] == PROGRAM}
    seeded = {a for a, _ in context["entries"]}
    out = []
    for addr in SEED_LISTINGS:
        onto, over = converges_from(region, addr)
        out.append({
            "listing": addr,
            "seed_basis": basis.get(addr, "not a listing row"),
            "seeded": addr in seeded,
            "reached": addr in context["decoded_starts"],
            "decoded_call": addr in context["decoded_sites"],
            "frame": f"{onto}/{onto + over}",
            "name": listing_name(addr),
        })
    return out


def listing_name(addr: int):
    """The `pd` name in a listing's own header, or None.

    `pd_image_census.listing_name()`'s job and its source: the function entry
    `.asm` header carries the name, so a listing with no `ghidra-functions.csv`
    row is still nameable and this report does not print a bare address where a
    name exists.
    """
    path = os.path.join(EC, "decompiled", PROGRAM, f"{addr:04X}.asm")
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.readline()
    except OSError:
        return None
    m = re.match(r"^;\s*pd\s*@\s*[0-9A-Fa-f]{4}\s+(\S+)", head)
    return m.group(1) if m else None


def print_seed_verdicts(seeds) -> None:
    print("The eight `pd` listings whose committed `.c` files say the function")
    print("boundary \"came from a call-target byte scan and is a hypothesis\". "
          "`seed_basis` is")
    print("`listing-index.csv`'s own column. `reached` says a walk from the "
          "stated entries decoded an")
    print("instruction at the listing's first address, which is not the same "
          "as that instruction being a")
    print("call or a jump; `frame` is `converges_from()`.")
    print()
    for s in seeds:
        print(f"  0x{s['listing']:04X} {s['name'] or '':<28} "
              f"seed_basis={s['seed_basis']:<12} seeded={str(s['seeded']):<5} "
              f"reached={str(s['reached']):<5} frame {s['frame']}")
    print()
    print("`seed_basis=annotation` on all of them is the refutation of the "
          "issue's premise: no `pd`")
    print("`.asm` header carries the note those `.c` comments cite, and the "
          "index records these")
    print("boundaries as hand annotations. The correction, with the wrong "
          "version left visible, is")
    print("in `docs/findings/pd-call-target-census.md`.")


# --------------------------------------------------------------------------
# --self-test
#
# The oracle is the half that makes the rest mean anything: a census that graded
# its own output against itself would pass whatever the walk decided. The
# decodes below are transcribed from `r2 -a 8051` and asserted against the image,
# not against the scan that wrote the CSV -- `test_bank1_e582_framing.py`'s
# argument, applied.

# Read with
#   python3 ec/tools/make_bank_image.py --pd ec/firmware/GMxMGxx_11.800 /tmp/pd.bin
#   r2 -a 8051 -e scr.color=0 -q -c 'p8 0x08 @ 0x13f6; pD 0x08 @ 0x13f6' /tmp/pd.bin
#
# and copied as (offset, bytes, decoded text). Two groups, and they check
# different things.
#
# The five call sites are the framing question: three of the sixteen 0x11C2
# sites, and two of the nine 0x119C ones. They are asserted against the *image*
# rather than against the scan that wrote the CSV, so a regenerated table that
# disagreed with r2 would fail rather than pass on a stale pair -- which is
# `test_bank1_e582_framing.py`'s argument, applied here.
#
# The eight listing heads are the other half: each is the first instruction of
# one of the `pd` listings the issue calls seeds, so the oracle also says the
# walk's entry set lands on real, correctly framed code and not on the middle
# of a table. 0xF126 is the one worth reading twice -- it opens with an
# `lcall 0x6F96`, so a walk reaching it has already committed to a target
# before the listing's own `jnz` at 0xF129 splits the two arms.
#
# **The bytes are r2's and the text is this repository's**, and the two
# differences are known and stated rather than smoothed over. `p8` gives the
# bytes and nothing else disputes them; the operand spelling is
# `disasm8051.mnemonic()`'s, which renders `a,r7` without the space r2 puts
# after the comma and prints `mov 0x83,r2` where r2 prints `mov dph, r2` --
# `trace_xdata_refs.py` documents that DPL/DPH are nowhere named by
# `mnemonic()` and that the two spellings are one address, not two. Writing
# r2's text here instead would mean asserting a rendering this decoder does not
# produce, and an oracle that fails on a correct run is an oracle nobody reads.
R2_ORACLE = (
    (0x13F6, b"\x12\x11\xc2", "lcall 0x11c2"),
    (0xCB4A, b"\x12\x11\xc2", "lcall 0x11c2"),
    (0x1F2D, b"\x12\x11\x9c", "lcall 0x119c"),
    (0xC879, b"\x12\x11\x9c", "lcall 0x119c"),
    (0xA34B, b"\x12\x11\x9c", "lcall 0x119c"),
    (0x0EF3, b"\xef\x4b\xff\xee", "mov a,r7"),
    (0x10F1, b"\xe4\x93\xfb\x74", "clr a"),
    (0x1229, b"\x8a\x83\x89\x82", "mov 0x83,r2"),
    (0x9A1B, b"\xeb\x75\xf0\x60", "mov a,r3"),
    (0x9A90, b"\xef\x75\xf0\x60", "mov a,r7"),
    (0xF109, b"\xed\x70\x0d", "mov a,r5"),
    (0xF126, b"\x12\x6f\x96\x70", "lcall 0x6f96"),
    (0xF4AB, b"\x90\x0a\x82\xef", "mov dptr,#0x0a82"),
)


def self_test(region: bytes, rows, context, index_rows) -> int:
    """The oracle, the refusals, the closed vocabularies and the tallies.

    Every case below is a red run or it is not a check, and the ones that would
    pass vacuously -- a count instead of a site-by-site assertion, a verdict
    vocabulary no row was asked to stay inside -- are written the other way on
    purpose.
    """
    bad = 0

    def check(ok, text):
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {text}")

    print("pd_call_targets.py --self-test")

    for off, raw, want in R2_ORACLE:
        # `mnemonic()` pads the mnemonic to four columns and r2 does not, so
        # both sides are compared with the padding collapsed -- the same
        # normalization `pd_direct_offset_sites.py` makes, and the only reason
        # a transcription taken from one and a decode produced by the other can
        # be equal.
        got = " ".join(mnemonic(region, off, off).split())
        check(region[off:off + len(raw)] == raw
              and got == " ".join(want.split()),
              f"0x{off:04X} is `{raw.hex(' ')}` = `{got}` (expected "
              f"`{want}`, image has `{region[off:off + len(raw)].hex(' ')}`)")

    # `in_listing` against a re-read of the listings, because a column nothing
    # recomputes is a column that can only be wrong quietly.
    streams = listing_starts(region)
    wrong = [r["candidate"] for r in rows
             if (r["in_listing"] == "yes") != (r["candidate"] in streams)]
    check(not wrong, "every row's `in_listing` agrees with a re-read of "
          f"ec/decompiled/pd/*.asm{'' if not wrong else ' -- wrong at ' + ', '.join('%04X' % c for c in wrong[:8])}")
    entries = listing_entries(index_rows)
    check(all(a in streams for a in entries),
          f"all {len(entries)} committed `pd` listing entries are instruction "
          f"starts in the exported `.asm` files")

    # The two named dispatchers, site by site rather than as a count: a count
    # passes on the wrong sixteen.
    for target, want in ((0x11C2, 16), (0x119C, 9)):
        sites = [r for r in rows if r["target"] == target]
        check(len(sites) == want,
              f"0x{target:04X} has {len(sites)} candidate site(s) "
              f"(expected {want})")
        check(all(r["verdict"] in VERDICTS for r in sites),
              f"and every one of the 0x{target:04X} sites carries a verdict "
              f"of the closed vocabulary")
        check(all(r["verdict"] in VERDICTS for r in rows),
              "and so does every row of the table")

    check(sorted(r["candidate"] for r in rows
                 if r["target"] == 0x11C2 and r["in_listing"] == "yes")
          == [0xCB4A],
          "the 0x11C2 `in_listing=yes` set is exactly {0xCB4A}, which is the "
          "claim pd-common-address-spaces.md makes")

    # The two coverage figures as a *relationship*, not as two totals: both
    # move whenever a listing lands, and a test that asserted either value
    # would be a value every merge has to edit.
    total = context["image_bytes"]
    walk_pct = 100.0 * context["decoded_bytes"] / total
    check(0 < context["listing_bytes"] < context["decoded_bytes"] < total,
          f"the listings hold less than the walk decoded, and both are less "
          f"than the image "
          f"({context['listing_bytes']} < {context['decoded_bytes']} < {total})")
    check(0.0 < walk_pct < 100.0,
          f"the walk's coverage is between 0 and 100% ({walk_pct:.2f}%) -- a "
          f"method that reached everything would not need a verdict column")

    # The closed terminator vocabulary.
    unknown = [c for ends in context["by_entry"].values() for c in ends
               if not ends_vocabulary(c)]
    check(not unknown, "every walk terminator names a vocabulary term"
          f"{'' if not unknown else ' -- unnamed: ' + '; '.join(unknown[:4])}")
    check(all(ends_vocabulary(r["ends"]) or r["ends"] == NO_WALK
              for r in rows),
          f"every row's `ends` is a vocabulary term or the explicit "
          f"`{NO_WALK}`, never a bare number")

    # The refusals.
    try:
        refuse_filtering()
        check(False, "refuse_filtering() raises")
    except SystemExit:
        check(True, "refuse_filtering() raises -- no output mode filters a row")

    try:
        read_region(os.path.join(REPO, "tools", "run-tests.sh"))
        check(False, "a dump with no PD region is refused")
    except (Refusal, OSError):
        check(True, "a dump with no PD region is refused rather than reported "
                    "as empty")

    # The seeds. The issue's premise is a claim about `listing-index.csv`'s
    # `seed_basis` column and about which files carry the note, and both are
    # asserted here rather than left to the write-up.
    carrying = seed_claim_files()
    check(carrying == sorted(f"{a:04X}" for a in SEED_LISTINGS),
          f"the {len(carrying)} `pd` .c file(s) carrying the call-target-scan "
          f"claim are exactly SEED_LISTINGS -- in two spellings, so a "
          f"single-spelling grep would "
          f"{'match' if len(carrying) == len(SEED_LISTINGS) else 'MISS'}")
    directory = os.path.join(EC, "decompiled", PROGRAM)
    in_asm = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".asm"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8",
                  errors="replace") as f:
            if SEED_SENTENCE_RE.search(f.read()):
                in_asm.append(name)
    check(not in_asm,
          "and no `pd` .asm header carries it, which is what makes the .c "
          "comments cite a note that is not there"
          f"{'' if not in_asm else ' -- found in ' + ', '.join(in_asm[:4])}")
    for addr in SEED_LISTINGS:
        row = next((r for r in index_rows if r["program"] == PROGRAM
                    and int(r["addr"], 16) == addr), None)
        check(row is not None and row.get("seed_basis") == "annotation",
              f"0x{addr:04X} is a committed listing whose seed_basis is "
              f"`annotation` (got "
              f"{row.get('seed_basis') if row else 'no row'}), so its boundary "
              f"did not come from a call-target byte scan")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the `r2 -a 8051` "
              f"transcription, the committed listings or the closed "
              f"vocabularies")
        return 1
    print(f"self-test passed: the {len(R2_ORACLE)} hand transcriptions decode "
          f"as r2 read them, every row's `in_listing` agrees with a re-read "
          f"of the")
    print("exported listings, the terminator vocabulary is closed, and the "
          "refusals refuse")
    return 0


# --------------------------------------------------------------------------
# main


def load_csvs(index_path: str = INDEX_CSV, callees_path: str = CALLEES_CSV):
    """(index rows, call-graph rows) from the two committed CSVs.

    Both are inputs, read-only. Neither is edited by this tool and neither is
    re-derived here: they are the committed annotation layer, and a
    disagreement between one of them and the image is a question for a reader,
    not something to resolve by regenerating a file.
    """
    for path in (index_path, callees_path):
        if not os.path.exists(path):
            raise Refusal(f"{repo_path(path)} is missing; the entry set is "
                          f"stated in committed files and this tool does not "
                          f"guess one")
    with open(index_path, newline="") as f:
        index_rows = list(csv.DictReader(f))
    with open(callees_path, newline="") as f:
        callee_rows = list(csv.DictReader(f))
    return index_rows, callee_rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--firmware", default=FIRMWARE,
                    help=f"raw EC firmware image (default: {repo_path(FIRMWARE)})")
    ap.add_argument("--csv", action="store_true",
                    help="write the census as CSV on stdout")
    ap.add_argument("--check", action="store_true",
                    help="diff the generated CSV against the committed table "
                         "and re-derive every figure the write-up pins; "
                         "non-zero on any difference")
    ap.add_argument("--report", action="store_true",
                    help="the human-readable census (the default)")
    ap.add_argument("--for-target", type=lambda s: int(s, 0),
                    help="every candidate site whose bytes name this target, "
                         "e.g. 0x11C2")
    ap.add_argument("--seed-verdicts", action="store_true",
                    help="what the walk makes of the eight listings whose `.c` "
                         "files claim a call-target-scan boundary")
    ap.add_argument("--self-test", action="store_true",
                    help="the r2 oracle, the refusals, the closed "
                         "vocabularies and the seed verdicts")
    ap.add_argument("--max-depth", type=int, default=MAX_DEPTH,
                    help=f"nested control transfers to follow per walk "
                         f"(default {MAX_DEPTH})")
    ap.add_argument("--max-insns", type=int, default=MAX_INSNS,
                    help=f"instruction budget per seeded walk (default "
                         f"{MAX_INSNS})")
    args = ap.parse_args()

    if args.check and args.csv:
        # A check that writes the file it is checking cannot fail on it. The
        # refusal is here rather than in `--check` itself so the two modes
        # cannot be ordered into a pass by accident.
        ap.error("--check and --csv are not combinable: --check compares the "
                 "committed table against a regenerated one, and a write mode "
                 "alongside it would be writing the file it is checking")

    try:
        region, how = read_region(args.firmware)
        index_rows, callee_rows = load_csvs()
        data_regions = load_data_regions()
        rows, context = survey(region, index_rows, callee_rows, data_regions,
                               args.max_depth, args.max_insns)
        if args.csv:
            sys.stdout.write(csv_table(rows))
            return 0
        if args.for_target is not None:
            return print_for_target(region, args.for_target, rows)
        if args.seed_verdicts:
            print_seed_verdicts(seed_verdicts(region, rows, context, index_rows))
            return 0
        if args.self_test:
            return self_test(region, rows, context, index_rows)
        if args.check:
            rc = check_table(csv_table(rows), SITES_CSV)
            return rc or check_figures(pinned_figures(), figures(region, rows,
                                                                 context))
        print(report(region, how, rows, context))
        return 0
    except Refusal as e:
        print(f"note: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
