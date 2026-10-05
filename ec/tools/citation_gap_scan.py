#!/usr/bin/env python3
"""Read the bytes Ghidra's function boundary cut out of a citing listing.

`citation_callers.py` vetoes a pair whose citing listing is an `0xFF` fill run
and corroborates one whose listing carries a transfer to the named callee. Both
rules read the citing row's *own* export, and there is a population they can
never reach: a real call at an address the export stops short of. Most of the
citing rows `citing-listing-evidence.md` measured turned out to have no gap at
all, so for those the question is what sits at the head of the *neighbouring*
export; for the rest the call really is between two exports, and nothing in the
repository asked whether it was there. Run this tool for that split on the tree
as it is -- the figures move every time an annotation lands, so they are not
written down here.

This tool asks, per (callee, citing row) pair: take the citing listing's last
instruction address, the next exported entry in that row's own scope, and the
image bytes between them plus three; decode that window with `disasm8051.py`,
which shares no code with Ghidra's SLEIGH, the same cross-check pairing
`verify_gap_text.py` was built for; and return one of three verdicts.

**The window carries 3 bytes of slack past the boundary, and they are
load-bearing.** `lcall`/`ljmp` are 3 bytes, so a transfer starting one or two
bytes before the boundary only completes by reading into the next entry. The
worked case proves it: the window `[0xE580, 0xE585)` decodes `12 e5 d6` to
`lcall 0xE5D6` at 0xE580, and a window stopping at the boundary decodes nothing
there at all.

**`walk()` below is not a workaround for `disasm8051.decode()` raising, and it
survives the fix for a different reason.** ~~**`disasm8051.decode()` cannot be
called in a loop over these windows.** It evaluates `OPCODE_LEN[d[i]]` *before*
its own `i + n > len(d)` guard, so a window whose last byte is a 1-byte opcode
walks off the end and raises `IndexError` -- and a gap window ends on one
routinely (`bank0,B5D2` is a bare `ret`). `walk()` below does the same linear
decode over the same committed tables and stops when the instruction does not
fit. Sharing `OPCODE_LEN` and `mnemonic` means there is no second opcode or
mnemonic table here to keep in step; the one-line upstream fix
(`if i >= len(d): return`) is recorded as a follow-up in
`docs/findings/citation-gap-scan.md` rather than done here, so that this stays a
new-file change and stays off a file another agent may be touching.~~
**Corrected 2026-09-25, issue #679:** the end-of-buffer check now runs before
the index it guards, so `decode()` stops cleanly rather than raising and the
reason this tool did not route through it is gone. `walk()` stays for the two
things it carries that `decode()` does not produce: the per-instruction
map-unassigned flag that the `not-code` verdict reads, and the `truncated`
column. Sharing `OPCODE_LEN` and `mnemonic` with `decode()` is a property of
`walk()` rather than a reason for it, and it means there is no second opcode or
mnemonic table here to keep in step; the retraction is in place in
`docs/findings/citation-gap-scan.md`.

**The unit is the pair, and there are more pairs than rows.** The gate
enumerates `(callee, citer)` pairs, so one citing comment that names three
callees is three pairs over one row. Both numbers are printed and both are
pinned: a tool that reported only the larger could be read as contradicting the
row count the write-up it extends measured.

**`not-code` outranks the other two, and the criterion is on the bytes rather
than on the mnemonic count.** The four byte values the MCS-51 map assigns to no
instruction are `0x06`, `0x07`, `0x16` and `0x17`; a window whose linear walk
lands on one of them is a data or unprogrammed region, and a transfer read out
of it would be the vacuous agreement `verify_gap_text.verdict_of` exists to
refuse. A `db` *count* is reported as a column and is never the verdict,
because `disasm8051`'s mnemonic table is partial by design and a count
threshold would be a number fitted to this tree. Stricter and looser forms, and
what the split becomes under each, are in the write-up.

**Calibration, in the direction that matters.** `no-transfer` means *this window
carries no transfer to the named callee* -- not that the comment is wrong; the
call may be somewhere the export does not reach at all. `not-code` is a third
answer, never a zero. `boundary-cut` is evidence about framing and about the
comment's accuracy, and is **not** proof that a function entry belongs at the
site: a data island inside a function's range decodes exactly as convincingly as
code, which is what the `bank0,D091` correction in
`docs/findings/citing-listing-evidence.md` is standing warning about.

**The `why` column says which `citations()` partition a pair came from, because
a verdict alone is not one reading.** The population is all three partitions of
`call_graph.citations()` put together, and the three already disagree about
whether the pair is a code citation at all: `kept` credits it as one,
`undecided` says the frame settled nothing, and `rejected` says the pair is a
data mention or a cross-program collision. A `no-transfer` on the last of those
is a statement about a window that was never evidence about a comment, and
pooling the three publishes it as though it were the same finding. The column
is `"<partition>:<reason>"`: for `rejected` the reason is the first of the
`Candidate.reasons` strings `citations()` recorded, which is its own precedence
order and puts the program veto ahead of the frame, and for `kept` it is which
of the two keep arms fired. A rejected pair can carry several reasons and the
column shows one, so the report says how many and names them. Nothing here is
re-derived from the prose; the report prints the split and what each partition
means on every run, and `docs/findings/citation-gap-why-partition.md` is the
reading.

**`fall_through` is a column rather than a fourth verdict, for the reason
`neighbour_edge` is one.** A pair whose two listings abut is crossed by running
off the end of one into the other, which no transfer-based verdict can express
and which scores as an unprovenanced citation. Either direction counts: the
citing listing ending where the callee's begins, or the callee's ending where
the citing row begins. **Abutting is not the same as crossed, so the junction's
own instruction is read**: a listing ending in `ret`, `sjmp`, `ljmp`, `ajmp`,
`jmp` or `reti` hands control elsewhere and the pair is `blocked`, which keeps
it apart from the `no` that says the rows do not abut at all. A conditional
branch can fall through and stays `yes`. Making it a verdict would repartition
every split `docs/findings/citation-gap-scan.md` publishes, so it is graded in a
column and `docs/findings/citation-gap-why-partition.md` says what promoting it
would cost.

Usage:
    python3 ec/tools/citation_gap_scan.py              # census, write nothing
    python3 ec/tools/citation_gap_scan.py --report     # write the CSV
    python3 ec/tools/citation_gap_scan.py --check      # recompute and diff
    python3 ec/tools/citation_gap_scan.py --self-test  # known answers
"""
import argparse
import collections
import csv
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import call_graph as cg                                        # noqa: E402
import citation_callers as cc                                  # noqa: E402
import disasm8051 as D                                         # noqa: E402
import verify_reassembly as V                                  # noqa: E402
import verify_gap_text as G                                    # noqa: E402

REPO = cg.REPO
REPORT = os.path.join(REPO, "ec", "ghidra", "gap-citation-scan.csv")

COLUMNS = ["callee_scope", "callee_addr", "citer_scope", "citer_addr",
           "verdict", "why", "gap", "end", "next", "window", "transfers",
           "hit_site", "hit_text", "at_next", "neighbour_edge",
           "db", "unassigned", "truncated", "frame_onto", "frame_over",
           "fall_through"]

# `lcall`/`ljmp` are the widest transfer, so a window that stopped at the
# boundary could cut one in half. See the module docstring.
SLACK = 3

# **These four are NOT the byte values the MCS-51 map assigns to no instruction,
# and the sentence this comment used to make was wrong.** The map assigns all
# four: `0x06`/`0x07` are `INC @R0`/`INC @R1` and `0x16`/`0x17` are `DEC @R0`/
# `DEC @R1`, one byte each. `disasm8051.OPCODE_LEN` sized them correctly all
# along, `opcode_coverage.MCS51_LEN` -- the table this comment cited as the
# manual -- assigns all four a length, and the committed Ghidra listings place
# real instruction starts on every one and name them (`ec/decompiled/bank0/
# B065.asm` `inc @R0`, `ec/decompiled/bank0/D091.asm` `dec @R1`). This is the
# same class of mis-transcription as the `0x96`/`0x97` row this repository has
# already corrected twice. *Corrected 2026-10-05, issue #1153: `mnemonic()` named
# the four, so this comment could not keep calling them unassigned without
# contradicting the decoder `self_test()` below asserts against.*
#
# **The set is nevertheless left exactly as it was**, and the reason is the
# point. This constant drives the `not-code` verdict directly, so changing it
# changes a published verdict and re-cuts the committed
# `ec/ghidra/gap-citation-scan.csv` for one row -- a different piece of work
# from making the decoder name what it prints, and named as its own follow-up in
# ../../docs/findings/mnemonic-db-fallthrough-coverage.md. What this module
# asserts about itself is the weaker, true statement: the bytes are ones the
# `not-code` criterion grades on, which is not the same claim as saying the map
# assigns them nothing.
#
# Stated as a literal here rather than read out of `disasm8051.py`, and rather
# than derived from the manual as this comment once claimed: an oracle derived
# from the tool it is testing asserts nothing, which is the note
# `disasm8051.TEXTBOOK_BIT_SITES` makes about its own `0xC1`/`0xC2` pair.
UNASSIGNED = (0x06, 0x07, 0x16, 0x17)

# Instructions that cannot hand control to the address after them, so a listing
# ending in one is not crossed by running off its end. Mnemonic names, because
# that is what `verify_reassembly.parse_listing` yields and reading the listing
# is the whole point: the address-only criterion this replaces called
# `bank0,C26E`'s `C277 ret` a fall-through into `bank0,C278`, which the
# committed listing contradicts. **A conditional branch is absent deliberately**
# -- `jc` falls through when it is not taken, so those rows keep `yes` -- and so
# is a call, because `lcall`/`acall` return to the instruction after them rather
# than leaving. `reti` is here for the reason `ret` is: it is the same exit.
# `jmp` is `jmp @A+DPTR`, the only `jmp` the map has.
NO_FALL_THROUGH = ("ret", "reti", "sjmp", "ljmp", "ajmp", "jmp")

# Known answers, asserted in --self-test **as relationships rather than as
# figures.** The census this tool prints moves every time an export is added, so
# a pinned row, pair or per-verdict tally here is a value the next merge has to
# edit, and a stale one is a false failure on a tree that is merely bigger. What
# --self-test holds instead is that the population is the one the committed
# tables propose, that each verdict is read off its own pair's window, and that
# the `boundary-cut` and `not-code` cases are the *named* pairs and not a tally
# of them -- which pins strictly more than a count did, because a count permits
# any set of the same size. The figures belong to
# `docs/findings/citation-gap-scan.md`, which quotes them beside the command
# that prints them, and a literal that stops moving is a number nobody edits.
#
# **The predicate has never been the same twice, and it moves both ways.**
#
# **The plan stage measured 100 rows / 114 pairs.** The predicate is unchanged --
# the same `transfers()`-yields-nothing test on the citing listing, minus the rows
# the `is_fill` veto already refuses. Two merges have moved it since, and both
# are recorded rather than absorbed:
#
#   * five more comments merged into `ghidra-functions.csv` took it to 105 / 123;
#   * issue #603's 37-row common-runtime tranche (PR #620) then took it to
#     99 / 124. That move runs *both* ways and is not a rename: the tranche's
#     own re-derivation of `call-graph-callees.csv` stopped listing 12 rows as
#     citing anything (11 `pd`, plus `common,05E6`), and six of the tranche's
#     newly-commented listings -- `common,2B6C`, `355E`, `3BDD`, `4368`, `4AFB`,
#     `5A55` -- are citing rows themselves, because a comment naming a callee
#     over a listing that transfers to nothing is the predicate.
#   * issue #489's 37 `pd` rows took it to 96 / 121, by the first of those two
#     mechanisms again but **not** for the same reason, and the difference is
#     why this note is here at all. `call_graph.citations()` proposes a
#     candidate only when the address a comment names still resolves to a row
#     whose name begins `FUN_` (`call_graph.py:343`), so #489 naming `pd 06EA`,
#     `39E6` and `E930` stopped the predicate firing for the three pairs whose
#     callee each is. **No citing comment changed** -- `bank0 D045`, `pd 39E7`
#     and `bank1 E924` are byte-for-byte what they were, and each is still a
#     citer in `call-graph-callees.csv`. So these three are *retired, not
#     answered*: all three were `no-transfer` rows, and the question each asks
#     is whether the citing listing can reach the address its own comment names,
#     which naming the callee does not decide. They want their own reading.
#
# `docs/findings/citation-gap-scan.md` carries the correction in place.
#
# The `boundary-cut` pairs, named rather than counted: the issue's worked case,
# and `common,3459` cited by `common,355E` -- #603's own rank-1 tranche row,
# whose one-`ret` listing is followed by 25 bytes before the next common entry,
# and whose `ljmp 0x3459` sits at that boundary. It is the zero-gap case the
# write-up describes, turning out to carry a real transfer.
EXPECT_CUT_PAIRS = {("bank1", "E5D6", "bank1", "E57E"),
                    ("common", "3459", "common", "355E")}
# The `not-code` pair, named for the same reason: the assertion below reads its
# window in full, and this is what says no second pair lands there.
EXPECT_NOT_CODE_PAIR = ("common", "1300", "bank0", "3AD6")
# The one `common` citer that does *not* abut the next common entry. That every
# other `common` listing does is why the scope-boundary worry never bit; #603's
# `common,355E` breaks it -- a one-`ret` row with 25 bytes before the next
# common entry -- so the exception is the one thing here worth naming, and how
# many of the rest abut is not.
EXPECT_COMMON_NONZERO_CITER = "355E"

# What each of the three `citations()` partitions means, printed on every run.
# A partition is not a finer verdict: it is the caller's own answer to whether
# the pair is a code citation at all, and the verdicts below are read off bytes.
# Pooling them is what put `no-transfer` on pairs that were never a claim.
PARTITION_GLOSS = {
    "kept": "credits this as a code citation (a code frame, or a listing "
            "transfer); the verdict is about corroboration",
    "undecided": "the frame settled nothing; the window walk is the only "
                 "evidence there is",
    "rejected": "citations() already decided this is not a code citation (a "
                "data frame, or the program veto), so the verdict describes a "
                "window, not a claim",
}

Context = collections.namedtuple(
    "Context",
    "index edges listings pairs kept reasons listing_kept undecided")


def listing_end(path):
    """The address one past the citing listing's last instruction, or None.

    Read from the byte column rather than from the mnemonic, because a
    `ret`/`nop`/`reti` line carries no operand and so is five tokens where
    `mov A, #0x10` is six -- and the bytes are what say how long the function
    is. `verify_reassembly.parse_listing` is the committed reader of that column
    and the one `verify_gap_text` already decodes from, so it is reused here
    rather than a third parse of the same lines. `listing_tail()` is that read,
    shared with the junction test so one file is not parsed two ways.
    """
    return listing_tail(path)[0]


def next_entry(by_scope, scope, addr):
    """The smallest exported entry address in `scope` strictly after `addr`.

    Ghidra's own per-program boundary, which is the thing the boundary argument
    is about. A `common` function is exported once for both banks, so for a
    `common` citer this is the common scope's boundary and not necessarily the
    executing bank's -- reported by `nearer_in_bank()` rather than resolved.
    """
    return min((a for a in by_scope.get(scope, ()) if a > addr), default=None)


def nearer_in_bank(by_scope, scope, addr, next_addr):
    """A bank-scope entry strictly nearer than `next_addr`, for a `common` row.

    The consequence of reading "the next exported entry in that program" as the
    citing row's own scope: at runtime a `common` call site executes against a
    bank window, and a nearer bank-scope entry can exist. Which of the two
    boundaries matters is a runtime question this text measurement cannot
    settle, so the tool counts and reports rather than picking one.
    """
    if scope != "common" or next_addr is None:
        return ""
    found = []
    for bank in ("bank0", "bank1"):
        nearer = min((a for a in by_scope.get(bank, ())
                      if addr < a < next_addr), default=None)
        if nearer is not None:
            found.append("%s:0x%04X" % (bank, nearer))
    return " ".join(found)


def walk(window, base):
    """`(site, raw, text, unassigned)` for each instruction the window holds.

    The linear decode `disasm8051.decode()` does, carrying two things it does
    not produce: the per-instruction map-unassigned flag, which is the
    `not-code` criterion below, and a `truncated` column saying the walk
    stopped on an instruction that did not fit rather than on the end of the
    buffer. `OPCODE_LEN` is indexed only after the remaining length is known to
    cover it, and an instruction that does not fit ends the walk and is
    reported rather than decoded, because there are not the bytes for it.
    """
    out = []
    i = 0
    while i < len(window):
        n = D.OPCODE_LEN[window[i]]
        if i + n > len(window):
            return out, True
        out.append((base + i, window[i:i + n],
                    D.mnemonic(window, i, base + i), window[i] in UNASSIGNED))
        i += n
    return out, False


def resolve_site(index, scope, text):
    """`(callee_key, target_addr)` for a transfer the window decoded, else None.

    Through the *same* `Index.resolve` the graph uses, under the citing row's
    scope. Comparing raw addresses here instead would let this tool disagree
    with `call_graph.py` about a bank listing reaching a `common` row, or about
    an ambiguous target that resolves to neither.
    """
    parts = text.split()
    if len(parts) < 2 or parts[0] not in cc.TRANSFERS:
        return None
    target = parts[1]
    if not target.lower().startswith("0x"):
        return None
    addr = target[2:].upper().zfill(4)
    if not cc.ADDRCOL.fullmatch(addr):
        return None
    row = index.resolve(scope, addr)
    if row is None:
        return None
    return (row["program"], row["_addr"]), addr


def verdict_of(insns):
    """`not-code` when the walk lands on a byte the map leaves unassigned.

    Checked before the transfer question for the reason
    `verify_gap_text.verdict_of` checks a `db` first: a window that did not
    decode cannot support a verdict about a transfer read out of it, and
    reporting one would be the same vacuous agreement. It is *not* a `db` count
    -- `disasm8051`'s mnemonic table is partial by design, so a count threshold
    would be a number fitted to this tree rather than a fact about the bytes.
    """
    return "not-code" if any(unassigned for _a, _r, _t, unassigned in insns) \
        else None


def context():
    """One `call_graph` pass, shared by the census and the classification.

    The scan is the expensive half (it walks all 2,707 listings), and
    `--self-test` needs both the population and the verdicts, so it is built
    once here rather than once per question.

    **The partition is carried, not discarded.** `citations()` splits its answer
    three ways and the caller used all three to build `pairs`, so keeping only
    the union left the reason behind in this function -- which is what let a
    `no-transfer` on a data mention publish as though it were about a comment.
    `kept`, `reasons`, `listing_kept` and `undecided` are the caller's own
    values, held for `why_of()` to read rather than a second derivation of them.
    """
    index = cg.load_index()
    edges, _unresolved, _orphans, _total, listings = cg.scan(index)
    kept, rejected, undecided, listing_kept = cg.citations(index, listings)
    kept_pairs, reasons = set(), {}
    for key, citers in kept.items():
        for scope, addr, _n in citers:
            kept_pairs.add((key, (scope, addr)))
    for c in rejected:
        reasons[(c.callee, c.citer)] = tuple(c.reasons)
    undecided_pairs = {(c.callee, c.citer) for c in undecided}
    pairs = set(kept_pairs) | set(reasons) | undecided_pairs
    return Context(index, edges, listings, pairs, kept_pairs, reasons,
                   listing_kept, undecided_pairs)


def why_of(ctx, pair):
    """`"<partition>:<reason>"` for one pair, from what `citations()` decided.

    The reason is the caller's own, in the caller's own precedence: a
    `Candidate.reasons` tuple starts with the program veto when one fired and
    carries every data reason after it, so taking the first is not a choice this
    tool makes about which veto mattered. A `kept` pair is split by
    `listing_kept`, which is the subset the citing listing's own bytes settled
    rather than the prose.

    **A pair in none of the three is blank, not `undecided`.** `classify()` can
    be driven over a pair the caller never returned, and answering
    `undecided` for one would claim the frame settled nothing when it was never
    read -- the same not-found-is-not-absent rule the rest of this repository
    keeps. `--self-test` asserts the blank is absent from every live row.
    """
    if pair in ctx.reasons:
        reasons = ctx.reasons[pair]
        return "rejected:%s" % (reasons[0] if reasons else "")
    if pair in ctx.kept:
        arm = "listing-corroborated" if pair in ctx.listing_kept else "code-frame"
        return "kept:%s" % arm
    if pair in ctx.undecided:
        return "undecided:undecided"
    return ""


def partition_of(why):
    """The partition half of a `why` value, for grouping without re-deriving."""
    return why.split(":", 1)[0]


def population(ctx):
    """The `(callee, citer)` pairs this tool measures, and their citing rows.

    **The predicate is a transfer-line test, and it has to be.** A citing row
    whose listing yields nothing from `citation_callers.transfers()`, minus the
    rows the `is_fill` veto already refuses -- the same population
    `docs/findings/citing-listing-evidence.md` measured, one
    `citations()` partition rather than a second derivation of it. The gate
    enumerates pairs, so the population is pairs; keying instead on the
    *resolved* target set yields a different number (a listing can carry a
    transfer that resolves to nothing), which is why the report prints the
    alternative rather than leaving the choice implicit.
    """
    with open(cg.ANNOTATIONS, newline="") as f:
        ann = list(csv.DictReader(f, strict=True))
    commented = {(r["scope"], cg.norm_addr(r["addr"]))
                 for r in ann if r.get("comment")}
    citers = {citer for _callee, citer in ctx.pairs}
    rows = []
    for scope, addr in sorted(commented):
        path = os.path.join(cg.DECOMPILED, scope, addr + ".asm")
        if not os.path.isfile(path) or list(cc.transfers(path)):
            continue
        listing = ctx.listings.get((scope, addr))
        if listing is not None and listing.fill:
            continue
        if (scope, addr) in citers:
            rows.append((scope, addr))
    pairs = sorted(pair for pair in ctx.pairs if pair[1] in set(rows))
    return rows, pairs


def resolved_empty_population(ctx):
    """The population under the other predicate, printed so the choice is not
    implicit: a citing row whose listing's *resolved* target set is empty.

    It is a different and slightly larger population, because a listing can
    carry a transfer that resolves to no index row -- `bank1,8802` and
    `bank1,E954` are the two here -- and the two of them are the only rows the
    two predicates disagree on. `population()` uses the transfer-line test
    because that is the predicate `citing-listing-evidence.md` measured and the
    one this tool is re-measuring; a tool that silently switched would report a
    different population under the same name.
    """
    citers = {citer for _callee, citer in ctx.pairs}
    rows = sorted(key for key, listing in ctx.listings.items()
                  if key in citers and not listing.targets and not listing.fill)
    keep = set(rows)
    pairs = sorted(pair for pair in ctx.pairs if pair[1] in keep)
    return rows, pairs


def listing_tail(path):
    """`(end, last mnemonic)` for a listing, or `(None, "")` if it has none.

    One read of the listing for both halves, because the junction question and
    the length question are asked about the same last line and two readers of
    one file is the hazard `listing_end`'s own docstring names. The mnemonic is
    read here rather than re-derived from the image so that the junction test
    below is a statement about the committed listing and not about this tool's
    decode of it.
    """
    last = None
    for addr, hexbytes, mnem, _ops in V.parse_listing(path):
        last = (addr + len(hexbytes) // 2, mnem)
    return last if last is not None else (None, "")


def ends_with_transfer(path):
    """Whether the listing's last instruction cannot hand control onward.

    The junction test for `falls_through()`. Read from the listing with the
    committed reader `verify_reassembly.parse_listing`, rather than inferred
    from the addresses either side of the junction: two listings can abut
    exactly and still not be crossed, because the instruction sitting on the
    boundary leaves. An empty listing has no last instruction and so nothing to
    read, which is `False` -- not-found-is-not-absent again, one step in from
    the blank the caller leaves for a missing file.
    """
    return listing_tail(path)[1] in NO_FALL_THROUGH


def junction_mnemonic(path):
    """The last mnemonic in `path`, or `""` for a listing that has none."""
    return listing_tail(path)[1]


def junction_of(scope, addr, callee, end):
    """The `.asm` path whose last instruction sits on the junction, or None.

    Whichever of the two listings abuts: the citing row's own when its end is
    the callee's address, the callee's when its end is the citing row's. None
    means the two do not abut, or the abutting listing is not on disk.
    """
    if end == int(callee[1], 16):
        return os.path.join(cg.DECOMPILED, scope, addr + ".asm")
    path = os.path.join(cg.DECOMPILED, callee[0], callee[1] + ".asm")
    if not os.path.isfile(path) or listing_end(path) != int(addr, 16):
        return None
    return path


def falls_through(callee, scope, addr, end):
    """`"yes"` when the two rows are crossed by running off an end, not a
    transfer; `"blocked"` when they abut but the instruction on the boundary
    leaves instead; `""` when the callee has no listing on disk to read.

    Either direction counts, and both are the same relation with the two rows
    swapped: the citing listing ends exactly where the callee's begins, so
    execution runs from the citer into the callee; or the callee's own listing
    ends exactly where the citing row begins, so it runs the other way. The
    second is the shape issue #489 left open -- `pd 0x39E7`'s comment names
    `0x39E6`, whose listing is one `mov R5,A` and no `ret` of its own -- and it
    is invisible to a verdict that only looks forward from the citing row.

    **The junction's own instruction decides, not the addresses.** Deciding
    from addresses alone graded `bank0,C26E`'s `C277 ret` as a fall-through into
    `bank0,C278`, which the committed listing contradicts: control returns to
    the caller. `bank0,D5DB`/`bank0,D5D4` and `bank1,C931`/`bank1,C924` are the
    same shape, ending in `sjmp` and `jmp @A+DPTR`. Those are `blocked` rather
    than `no`, which keeps the two readings apart: `no` says the rows do not
    abut, `blocked` says they do and the crossing is closed. A *conditional*
    branch at the junction can fall through, so it stays `yes` -- `bank0,B4A8`
    ends in `jc 0xb5d2` and `bank0,B737` in `jnc 0xb83a`, and both are real.

    **Same-scope only.** Two exports in different programs that share an
    address are a collision, not an adjacency: `bank1 0xE924`'s comment names a
    fall-through into `bank1 0xE931`, and the token resolved to a `pd` row at
    0xE930 that merely shares the number.

    The blank is not-found-is-not-absent, the direction this repository keeps
    everywhere else: an index row need not have a `.asm` beside it -- `bank0,
    F0A1` is an index row in this tree with no listing, as are `bank1,17FE` and
    `bank1,D235` -- and a missing listing decides nothing about whether it
    falls. No pair in the population lands on that blank.
    """
    if callee[0] != scope:
        return "no"
    if end == int(callee[1], 16):
        # Forward: the citing listing ends where the callee begins, so the
        # instruction on the junction is the citing row's own last one, and it
        # is on disk because `classify()` has just read it.
        return ("blocked" if ends_with_transfer(
            os.path.join(cg.DECOMPILED, scope, addr + ".asm")) else "yes")
    path = os.path.join(cg.DECOMPILED, callee[0], callee[1] + ".asm")
    if not os.path.isfile(path):
        return ""
    if listing_end(path) != int(addr, 16):
        return "no"
    return "blocked" if ends_with_transfer(path) else "yes"


def classify(ctx, images=None, pairs=None):
    """One report row per pair, with its window and its verdict.

    `images` and `pairs` are parameters so `--self-test` can drive the same
    path over a fixture pair: the check is that the window comes from the
    firmware image and the resolution from the same `Index.resolve` the graph
    uses, and an assertion that rebuilt those itself could not tell a
    regression in them from a regression in the code they are meant to feed.
    """
    images = images if images is not None else G.load_images()
    by_scope = by_scope_of(ctx)
    if pairs is None:
        _rows, pairs = population(ctx)

    out = []
    for callee, citer in pairs:
        scope, addr = citer
        path = os.path.join(cg.DECOMPILED, scope, addr + ".asm")
        end = listing_end(path)
        nxt = next_entry(by_scope, scope, int(addr, 16))
        image = images.get(scope) or images["bank0"]
        hi = (nxt + SLACK) if nxt is not None else end + SLACK
        hi = min(hi, len(image))
        window = image[end:hi]
        insns, truncated = walk(window, end)

        # Only the window's *transfers* are listed here, and the split is
        # reported per pair rather than pooled: "a transfer is there, but not
        # the one named" is a different reading from "no transfer at all", and
        # the two should not be averaged into one number.
        transfers, hit_site, hit_text = [], "", ""
        for site, _raw, text, _un in insns:
            got = resolve_site(ctx.index, scope, text)
            if got is None and text.split()[0] not in cc.TRANSFERS:
                continue
            transfers.append("0x%04X %s" % (site, text))
            if got is not None and got[0] == callee and not hit_site:
                hit_site, hit_text = "0x%04X" % site, text

        nc = verdict_of(insns)
        verdict = nc or ("boundary-cut" if hit_site else "no-transfer")
        if hit_site and nxt is not None and int(hit_site, 16) >= nxt:
            at_next = "yes"
        elif hit_site:
            at_next = "no"
        else:
            at_next = ""

        # The same-scope transfer the callee's edge list already books under a
        # *different* function. The graph is attributing to a neighbour what the
        # comment attaches here; a column rather than a fourth verdict, so the
        # three still partition.
        neighbour = ""
        for nscope, ncaller, form in ctx.edges.get(callee, ()):
            if nscope == scope and ncaller != addr:
                neighbour = "%s:%s %s" % (nscope, ncaller, form)
                break

        # A citation crossed by falling off the end of one listing into the other.
        # No transfer carries it, so the window cannot either; a column for the
        # reason the module docstring gives, so the verdicts still partition.
        fall_through = falls_through(callee, scope, addr, end)

        onto, over = D.converges_from(image, end) if end else (0, 0)
        out.append({
            "callee_scope": callee[0],
            "callee_addr": callee[1],
            "citer_scope": scope,
            "citer_addr": addr,
            "verdict": verdict,
            "why": why_of(ctx, (callee, (scope, addr))),
            "gap": "" if nxt is None else str(nxt - end),
            "end": "%04X" % end,
            "next": "" if nxt is None else "%04X" % nxt,
            "window": window.hex(),
            "transfers": "; ".join(transfers),
            "hit_site": hit_site,
            "hit_text": hit_text,
            "at_next": at_next,
            "neighbour_edge": neighbour,
            "db": sum(1 for _a, _r, t, _u in insns if t.startswith("db ")),
            "unassigned": sum(1 for _a, _r, _t, u in insns if u),
            "truncated": "yes" if truncated else "no",
            "frame_onto": str(onto),
            "frame_over": str(over),
            "fall_through": fall_through,
        })
    return out


def render(rows):
    buf = []
    w = csv.DictWriter(_Sink(buf), fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return "".join(buf)


class _Sink:
    def __init__(self, sink):
        self._sink = sink

    def write(self, text):
        self._sink.append(text)


def diff_table(have, want):
    """The per-row, per-cell differences between two renderings of the report.

    Empty when every row parses equal, which is **not** the same as identical:
    the byte comparison is the pass condition and it lives in `check_table()`.
    This renders a difference and never decides one, for the reason
    `call_graph.diff_table` gives -- asserting against a re-implementation of
    the diff would prove the re-implementation works.
    """
    have_rows = list(csv.DictReader(have.splitlines()))
    want_rows = list(csv.DictReader(want.splitlines()))
    lines, shown = [], 0
    for a, b in zip(have_rows, want_rows):
        if a != b:
            lines.append("  %s,%s cited by %s,%s:"
                         % (a["callee_scope"], a["callee_addr"],
                            a["citer_scope"], a["citer_addr"]))
            for k in COLUMNS:
                if a.get(k) != b.get(k):
                    lines.append("    %-14s committed %r, recomputed %r"
                                 % (k, a.get(k), b.get(k)))
            shown += 1
            if shown >= 20:
                lines.append("  ... more")
                break
    if len(have_rows) != len(want_rows):
        lines.append("  row count: committed %d, recomputed %d"
                     % (len(have_rows), len(want_rows)))
    return lines


def check_table(have, want):
    """`(exit_code, lines)`: what `--check` returns, and the lines it prints.

    Byte equality is the pass condition, for `call_graph.check_table`'s reason:
    a table whose rows read the same while its bytes do not is a table this
    tool did not write, and `ec/annotations/*.csv` is not covered by the
    `.gitattributes` `-text` entries the decompiled tree has for exactly that
    hazard. `lines` is never empty when the code is 1.
    """
    if have == want:
        return 0, []
    lines = diff_table(have, want)
    if not lines:
        lines = ["  bytes differ and every row parses equal: line endings, a "
                 "trailing blank line, column order or quoting differ from "
                 "what this tool writes"]
    return 1, lines


def by_scope_of(ctx):
    """{program: [exported addresses, ascending]} from the index."""
    by_scope = collections.defaultdict(list)
    for r in ctx.index.rows:
        by_scope[r["program"]].append(int(r["_addr"], 16))
    for addrs in by_scope.values():
        addrs.sort()
    return by_scope


def report(ctx, rows, images=None):
    """Print the census, every figure twice-framed where a second framing
    exists, and the method's stated limits. These are the numbers
    `docs/findings/citation-gap-scan.md` quotes."""
    images = images if images is not None else G.load_images()
    pop_rows, pop_pairs = population(ctx)
    tal = collections.Counter(r["verdict"] for r in rows)
    part = collections.Counter(partition_of(r["why"]) for r in rows)
    blocked = [r for r in rows if r["fall_through"] == "blocked"]
    multi = [r for r in rows if len(ctx.reasons.get(
        ((r["callee_scope"], r["callee_addr"]),
         (r["citer_scope"], r["citer_addr"])), ())) > 1]
    row_keys = {(r["citer_scope"], r["citer_addr"]) for r in rows}
    scopes = collections.Counter(scope for scope, _addr in row_keys)
    zero_rows = len({(r["citer_scope"], r["citer_addr"])
                     for r in rows if r["gap"] == "0"})
    zero_pairs = sum(1 for r in rows if r["gap"] == "0")
    with_transfer = sum(1 for r in rows if r["transfers"])
    alt_rows, alt_pairs = resolved_empty_population(ctx)
    by_scope = by_scope_of(ctx)
    # Counted here rather than printed from a constant: this is the one
    # consequence of reading "the next exported entry in that program" as the
    # citing row's own scope, and a literal would go stale without saying so.
    shorter = sum(1 for r in rows if r["citer_scope"] == "common" and
                  nearer_in_bank(by_scope, "common", int(r["citer_addr"], 16),
                                 None if r["next"] == "" else int(r["next"], 16)))
    print("citation_gap_scan.py -- the bytes a function boundary cut out of a "
          "citing listing")
    print()
    print("  %-52s %6d" % ("citing rows in the population", len(pop_rows)))
    print("  %-52s %6d" % ("  (callee, citer) pairs", len(pop_pairs)))
    print("  %-52s %6d" % ("  pairs whose citing row is one of those rows",
                           len(row_keys)))
    print("  %-52s %6d" % ("  the resolved-target predicate instead: rows",
                           len(alt_rows)))
    print("  %-52s %6d" % ("  ... and its pairs", len(alt_pairs)))
    print()
    print("  %-52s %6d" % ("citers by scope: " + ", ".join(
        "%s %d" % kv for kv in sorted(scopes.items())), len(scopes)))
    print("  %-52s %6d" % ("  of those, a `common` citer", scopes["common"]))
    print("  %-52s %6d" % ("    with a bank-scope entry nearer than the "
                           "common one", shorter))
    print()
    print("  the population is all three partitions of call_graph.citations(), and")
    print("  the `why` column says which one each pair came from -- a pair is")
    print("  credited as a code citation, left undecided, or already refused, and")
    print("  the verdicts below are read off bytes either way:")
    for partition in ("kept", "undecided", "rejected"):
        print(textwrap.fill(
            PARTITION_GLOSS[partition], width=79,
            initial_indent="    %-10s %6d  " % (partition,
                                                 part.get(partition, 0)),
            subsequent_indent=" " * 23))
    print("    %-10s %6d" % ("", sum(part.values())))
    print()
    print("  %-52s %6d" % ("window, zero bytes (the next export starts where "
                           "this one stops)", zero_pairs))
    print("  %-52s %6d" % ("  rows", zero_rows))
    print("  %-52s %6d" % ("  window, non-zero", len(rows) - zero_pairs))
    print("  %-52s %6d" % ("window carries some transfer at all", with_transfer))
    print("  %-52s %6d" % ("  carries none", len(rows) - with_transfer))
    print()
    for verdict in ("boundary-cut", "no-transfer", "not-code"):
        print("  %-52s %6d" % ("verdict %s" % verdict, tal.get(verdict, 0)))
    print("  %-52s %6d" % ("  the three verdicts add up to the pair count",
                           sum(tal.values())))
    print("  the same three verdicts within each partition, which is what the")
    print("  pooled tally above hides -- a verdict on a refused pair describes a")
    print("  window, not a claim:")
    print("    %-10s %6s %14s %13s %9s" % ("", "pairs", "boundary-cut",
                                          "no-transfer", "not-code"))
    for partition in ("kept", "undecided", "rejected"):
        cell = collections.Counter(
            r["verdict"] for r in rows
            if partition_of(r["why"]) == partition)
        print("    %-10s %6d %14d %13d %9d"
              % (partition, part.get(partition, 0), cell.get("boundary-cut", 0),
                 cell.get("no-transfer", 0), cell.get("not-code", 0)))
    print()
    print("  %-52s %6d" % ("pairs whose two listings abut, and the junction "
                           "falls through",
                           sum(1 for r in rows if r["fall_through"] == "yes")))
    print("  %-52s %6d" % ("pairs whose two listings abut, and the junction "
                           "instruction leaves",
                           sum(1 for r in rows if r["fall_through"] == "blocked")))
    print("  %-52s %6d" % ("pairs whose `why` shows one of several reasons "
                           "citations() recorded", len(multi)))
    print("  %-52s %6d" % ("pairs whose callee is already reached from the "
                           "same scope by another function",
                           sum(1 for r in rows if r["neighbour_edge"])))
    print("  %-52s %6d" % ("windows whose linear walk did not tile the buffer",
                           sum(1 for r in rows if r["truncated"] == "yes")))
    print("  %-52s %6d" % ("  windows with a `db` at an instruction start",
                           sum(1 for r in rows if int(r["db"]))))
    print("  %-52s %6d" % ("  windows landing on a map-unassigned byte",
                           sum(1 for r in rows if int(r["unassigned"]))))
    print()
    print("  boundary-cut pairs, read one by one:")
    for r in rows:
        if r["verdict"] == "boundary-cut":
            print("    %s,%s cited by %s,%s: %s at %s, listing ends 0x%s, "
                  "next entry 0x%s, %s byte(s) of gap"
                  % (r["callee_scope"], r["callee_addr"], r["citer_scope"],
                     r["citer_addr"], r["hit_text"], r["hit_site"],
                     r["end"], r["next"], r["gap"]))
    print("  not-code pairs, read one by one:")
    for r in rows:
        if r["verdict"] == "not-code":
            print("    %s,%s cited by %s,%s: the window is %d byte(s) from "
                  "0x%s to the next entry at 0x%s, and %d instruction(s) of it "
                  "land on a"
                  % (r["callee_scope"], r["callee_addr"], r["citer_scope"],
                     r["citer_addr"], len(r["window"]) // 2, r["end"],
                     r["next"], int(r["unassigned"])))
            print("      byte the MCS-51 map assigns to no instruction; it "
                  "opens `%s`" % r["window"][:18])
    if multi:
        print("  pairs refused for more than one reason, the `why` column "
              "carrying the first:")
        for r in multi:
            print("    %s,%s cited by %s,%s: %s"
                  % (r["callee_scope"], r["callee_addr"], r["citer_scope"],
                     r["citer_addr"], " and ".join(ctx.reasons[(
                         (r["callee_scope"], r["callee_addr"]),
                         (r["citer_scope"], r["citer_addr"]))])))
    if blocked:
        print("  abutting pairs whose junction instruction leaves, read one by "
              "one -- these are `blocked`, not `yes`:")
        for r in blocked:
            abutting = junction_of(r["citer_scope"], r["citer_addr"],
                                   (r["callee_scope"], r["callee_addr"]),
                                   int(r["end"], 16))
            print("    %s,%s cited by %s,%s: the junction is `%s` in %s, so "
                  "control does not run into the other row"
                  % (r["callee_scope"], r["callee_addr"], r["citer_scope"],
                     r["citer_addr"], junction_mnemonic(abutting),
                     os.path.relpath(abutting, REPO)))
    print()
    print("  limit: %d of the %d pairs are `no-transfer`, which is this window "
          "carrying" % (tal.get("no-transfer", 0), len(rows)))
    print("  no transfer to the named callee -- not the comment being wrong, and")
    print("  not the call being absent. %d window(s) carry a transfer that lands "
          "elsewhere;" % with_transfer)
    print("  those are a different reading and are not pooled with the rest.")
    print("  limit: that pooled tally spans all three partitions, and on a `rejected`")
    print("  pair there was no code claim for the window to miss -- citations()")
    print("  had already read the mention as a data frame or a cross-program")
    print("  collision. Read the per-partition table above, not the pooled one, for")
    print("  anything about a comment.")
    print("  limit: a `fall_through` row is a column, not a fourth verdict, so it")
    print("  still reads `no-transfer` and the comment is neither credited nor")
    print("  faulted by it. `blocked` is not `no`: it says the two listings abut")
    print("  and the instruction on the boundary leaves. `pd 0x39E6`/`0x39E7` is")
    print("  the shape; the reading is in")
    print("  docs/findings/citation-gap-why-partition.md.")
    print("  limit: a `boundary-cut` is evidence about framing and about the")
    print("  comment's accuracy, not proof that a function entry belongs at the")
    print("  site. `bank0,D091` -- a CODE table read as ACALLs -- decodes exactly")
    print("  as convincingly as code; see docs/findings/citing-listing-evidence.md.")
    print("  limit: this is a text measurement over the committed listings and the")
    print("  committed image. No register status: changed, no listing re-read, no")
    print("  live test run, and nothing observed on hardware.")
    print("  limit: `call_graph.py` is not changed by this tool, and")
    print("  ec/annotations/call-graph-callees.csv is byte-identical either way.")


def check():
    rows = classify(context())
    text = render(rows)
    if not os.path.isfile(REPORT):
        print("  FAIL no report at %s; run citation_gap_scan.py --report"
              % os.path.relpath(REPORT, REPO))
        return 1
    with open(REPORT, newline="") as f:
        have = f.read()
    rc, lines = check_table(have, text)
    if rc:
        for line in lines:
            print(line)
        print("gap-citation-scan.csv differs from the committed listings; "
              "re-run with --report", file=sys.stderr)
        return 1
    tally = collections.Counter(r["verdict"] for r in rows)
    print("  gap citation scan: %d row(s); verdicts %s"
          % (len(rows), ", ".join("%d %s" % (v, k)
                                   for k, v in sorted(tally.items()))))
    print("  all checks passed")
    return 0


def self_test():
    """Known answers, oracles stated from committed inputs and the 8051 map.

    Never recorded from this tool: a self-test that derives its oracle from the
    code it is testing asserts nothing, which is the note
    `disasm8051.self_test` and `verify_gap_text.self_test` both make about
    their own digests.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    # The `not-code` criterion's own oracle, paired with the decoder -- the
    # `disasm8051.TEXTBOOK_BIT_SITES` shape. **Corrected, because the assertion
    # it replaced was false.** This used to read "disasm8051 prints `db` for
    # each of 0x06, 0x07, 0x16, 0x17", as a corollary of the manual assigning
    # them nothing. Both halves of that were wrong: the manual assigns all four
    # (`INC @R0`/`@R1`, `DEC @R0`/`@R1`), and `mnemonic()` now names them, so it
    # would have failed the moment the decoder was corrected rather than when the
    # module was. What the pairing is actually for -- keeping this list from
    # quietly becoming a second copy of the decoder's coverage -- is unchanged,
    # and so is what the set is for: the `not-code` verdict reads the literal
    # above, not this function. The old text is left visible in the comment on
    # `UNASSIGNED` itself; see ../../docs/findings/mnemonic-db-fallthrough-
    # coverage.md.
    assert_that(len(UNASSIGNED) == 4 and all(0 < b < 0x100 for b in UNASSIGNED),
                "the byte set this module grades a window's `not-code` verdict "
                "on is four values")
    assert_that([D.mnemonic(bytes([b]), 0, 0) for b in UNASSIGNED]
                == ["inc  @r0", "inc  @r1", "dec  @r0", "dec  @r1"],
                "and disasm8051 names each of 0x06, 0x07, 0x16, 0x17 -- which "
                "is the correction this pairing exists to catch: the set is not "
                "the map's hole, and the verdict reads the literal regardless")
    # The neighbours of that set, so the assertion is about the boundary of the
    # map and not about the decoder's coverage: 0x05/0x15 are the 2-byte INC
    # and DEC direct either side of 0x06/0x07, and 0x18 is DEC R0 below 0x16.
    assert_that([D.mnemonic(bytes([b, 0x20]), 0, 0).split()[0]
                 for b in (0x05, 0x15, 0x18)]
                == ["inc", "dec", "dec"],
                "and the bytes either side of it are the real thing: 0x05 INC "
                "direct, 0x15 DEC direct, 0x18 DEC R0")
    assert_that([t.split() for _a, _r, t, _u in
                 walk(b"\x12\xe5\xd6\xd0\x07", 0xE580)[0]]
                == [["lcall", "0xe5d6"], ["pop", "0x07"]],
                "0x12 is the 3-byte `lcall` and 0xD0 the 2-byte `pop`, read out "
                "of the same table")
    assert_that(verdict_of([(0x10, b"\x17", "db 0x17", True)]) == "not-code",
                "a walk landing on a map-unassigned byte is `not-code`")
    assert_that(verdict_of([(0x10, b"\x22", "ret", False)]) is None,
                "and a clean window is not")

    # The junction set's own oracle, stated from the manual and paired with the
    # decoder -- the same shape as the `UNASSIGNED` block above, and for the
    # same reason: `NO_FALL_THROUGH` is a list of mnemonic *names*, so the
    # pairing is what stops it drifting into a second, partial copy of the
    # decoder's transfer coverage. Each byte is fed to `mnemonic()` at its own
    # length and the two answers are read together.
    junction_cases = [(0x22, "ret", True), (0x32, "reti", True),
                      (0x02, "ljmp", True), (0x80, "sjmp", True),
                      (0x73, "jmp", True), (0x01, "ajmp", True),
                      (0x21, "ajmp", True), (0x40, "jc", False),
                      (0x50, "jnc", False), (0x60, "jz", False),
                      (0x70, "jnz", False), (0x10, "jbc", False),
                      (0x20, "jb", False), (0x30, "jnb", False),
                      (0xD5, "djnz", False), (0x12, "lcall", False),
                      (0x11, "acall", False)]
    assert_that(all(D.mnemonic(bytes([op]) + bytes(D.OPCODE_LEN[op] - 1),
                              0, 0).split()[0] == name
                    and (name in NO_FALL_THROUGH) is blocks
                    for op, name, blocks in junction_cases),
                "every mnemonic `NO_FALL_THROUGH` names is what `disasm8051` "
                "prints for a byte that leaves, and every one it omits is a "
                "byte that can fall through -- conditional branches, which "
                "reach the next row when not taken, and the calls, which "
                "return to the instruction after them")

    # The overrun guard, on `walk()` and on `decode()`. A gap window ends on a
    # 1-byte opcode routinely (`bank0,B5D2` is a bare `ret`), so the shape that
    # matters is a window that holds less than the caller asked for. `walk()`
    # reports that through `truncated`; `decode()` now stops rather than
    # raising, which is what removed the reason this tool did not route
    # through it, so the same window is asserted on both and the two answers
    # are read together.
    got, truncated = walk(b"\x22", 0xB5D2)
    assert_that([t for _a, _r, t, _u in got] == ["ret"] and not truncated,
                "a window that is one 1-byte `ret` decodes to that one "
                "instruction and stops")
    got, truncated = walk(b"\x12\xe5\xd6", 0xE580)
    assert_that([t for _a, _r, t, _u in got] == ["lcall 0xe5d6"]
                and not truncated,
                "and a window that is exactly one 3-byte `lcall` decodes whole")
    _got, truncated = walk(b"\x12\xe5", 0xE580)
    assert_that(_got == [] and truncated,
                "while one that stops short of its 3 bytes decodes nothing and "
                "reports the truncation rather than reading past the end")
    assert_that([(a, t) for a, _r, t in D.decode(b"\x22", 0, 4, 0xB5D2)]
                == [(0, "ret")],
                "and disasm8051.decode() asked for four instructions over that "
                "one yields the same `ret` and stops, which is why this tool "
                "keeps walk() for the unassigned flag and the truncated column "
                "rather than for the bounds check")

    # The population, as the two-way identity it is rather than as a pair of
    # pinned figures: re-derived here from the committed `call-graph-callees.csv`
    # and `ghidra-functions.csv` through the predicate `population()`'s own
    # docstring states, so an annotation edit that moves the population has to
    # move this. Which rows the filter keeps is the whole claim, and it is
    # checked both ways -- a row it wrongly drops fails here as surely as one it
    # wrongly keeps.
    ctx = context()
    pop_rows, pop_pairs = population(ctx)
    citers = set(pop_rows)
    with open(cg.ANNOTATIONS, newline="") as f:
        ann = list(csv.DictReader(f, strict=True))
    commented = {(r["scope"], cc.norm_addr(r["addr"]))
                 for r in ann if r.get("comment")}
    proposed = set()
    for key in {citer for _callee, citer in ctx.pairs}:
        listing = os.path.join(cg.DECOMPILED, key[0], key[1] + ".asm")
        if (key in commented and os.path.isfile(listing)
                and not list(cc.transfers(listing))
                and not cc.is_fill(listing)):
            proposed.add(key)
    assert_that(proposed == citers and proposed,
                "the population is exactly the citers the committed annotations "
                "carry a comment for whose listing yields no transfer and is not "
                "a fill run -- the two refusals `population()` names")
    assert_that(set(pop_pairs) == {p for p in ctx.pairs if p[1] in citers},
                "and the pairs are exactly the ones the graph proposes over "
                "those rows: none dropped by the filter, none invented")
    assert_that({p[1] for p in pop_pairs} == citers,
                "every pair's citing row is in the row set, so the two describe "
                "one population and cannot be read as contradicting")
    assert_that(len({(p[0], p[1]) for p in pop_pairs}) == len(pop_pairs),
                "and the pairs are distinct")

    # The predicate is the transfer-line one and not the resolved-target one,
    # which is a *different* population: a listing can carry a transfer that
    # resolves to no index row, and those rows are the whole of the difference.
    alt_rows, alt_pairs = resolved_empty_population(ctx)
    extra = set(alt_rows) - citers
    assert_that(set(pop_pairs) < set(alt_pairs)
                and set(alt_rows) - citers == extra
                and set(alt_pairs) - set(pop_pairs)
                == {p for p in alt_pairs if p[1] in extra},
                "the resolved-target predicate's population is this one's plus "
                "exactly the rows it adds and exactly the pairs over them -- and "
                "never narrower, since a listing carrying no transfer line at all "
                "resolves no target either")
    assert_that(extra == {("bank1", "8802"), ("bank1", "E954")},
                "and the two rows it adds are %s -- each carries a transfer "
                "line whose target resolves to no index row, which is why the "
                "two predicates cannot be used interchangeably"
                % ", ".join("%s,%s" % k for k in sorted(extra)))

    # The whole live population, classified once; the cases below are read out
    # of it rather than re-derived, so a regression in the census and a
    # regression in one window cannot be told apart.
    live = classify(ctx)
    images = G.load_images()
    by_verdict = collections.defaultdict(list)
    for r in live:
        by_verdict[r["verdict"]].append(r)

    def pair_key(r):
        return (r["callee_scope"], r["callee_addr"],
                r["citer_scope"], r["citer_addr"])

    def row_of(verdict, key):
        """The classified row for one *named* pair, or a blank one.

        The blocks below read their case by name rather than by position, so a
        pair that is renamed or loses its verdict has to be a second failing
        assertion rather than an `IndexError` that stops the run before the
        ones after it are reached.
        """
        return next((r for r in by_verdict[verdict] if pair_key(r) == key),
                    collections.defaultdict(lambda: "0"))

    # The worked example the issue names, and the census it sits in. The set of
    # cut pairs is named rather than counted: a count would license any two
    # pairs, this says which two, and it is also what keeps the `common`
    # exception below and this one the same claim.
    cut = [r for r in by_verdict["boundary-cut"]]
    assert_that({pair_key(r) for r in cut} == EXPECT_CUT_PAIRS,
                "the `boundary-cut` verdict lands on the two named pairs -- "
                "bank1,E5D6 cited by bank1,E57E, and common,3459 cited by "
                "common,355E -- and on no third")
    e57e = row_of("boundary-cut", ("bank1", "E5D6", "bank1", "E57E"))
    # Oracle: bank-call-targets.csv:5766 reads
    # `0x16580,bank1,0xE580,lcall,0xE5D6,B,24,0,,,entry,entry` and bank1/E57E.asm
    # is a single `push 0x07`, so the listing ends at 0xE580 and the lcall is
    # two bytes into the window.
    assert_that(e57e["citer_scope"] == "bank1" and e57e["citer_addr"] == "E57E"
                and e57e["callee_scope"] == "bank1"
                and e57e["callee_addr"] == "E5D6",
                "the cut pair is bank1,E5D6 cited by bank1,E57E")
    assert_that(e57e["hit_text"] == "lcall 0xe5d6"
                and e57e["hit_site"] == "0xE580",
                "the cut transfer is `lcall 0xE5D6` at 0xE580 -- "
                "bank-call-targets.csv:5766, transcribed")
    assert_that(e57e["end"] == "E580" and e57e["next"] == "E582"
                and e57e["gap"] == "2" and e57e["window"] == "12e5d6d007",
                "with the window [0xE580, 0xE585) the issue describes: 2 bytes of "
                "gap, 3 of slack, `12 e5 d6 d0 07`")
    assert_that(e57e["at_next"] == "no",
                "and the transfer site is at 0xE580, inside the gap and not at "
                "the next export")
    assert_that(e57e["neighbour_edge"] == "bank1:E5A7 lcall",
                "the same callee is already reached from bank1 by E5A7, which "
                "is the second signal the write-up reports")
    # The slack is load-bearing: without it the window is 2 bytes and the lcall
    # cannot complete, which is the whole reason `SLACK` is 3.
    short = images["bank1"][0xE580:0xE582]
    _got, short_trunc = walk(short, 0xE580)
    assert_that(_got == [] and short_trunc,
                "and the same two bytes without the slack decode to nothing at "
                "all -- which is why the window runs 3 past the boundary")

    # The one `not-code` pair, and the one `no-transfer` pair read in full.
    assert_that({pair_key(r) for r in by_verdict["not-code"]}
                == {EXPECT_NOT_CODE_PAIR},
                "the `not-code` verdict lands on the one named pair, "
                "common,1300 cited by bank0,3AD6, and on no second")
    nc = row_of("not-code", EXPECT_NOT_CODE_PAIR)
    assert_that(nc["citer_scope"] == "bank0" and nc["citer_addr"] == "3AD6",
                "the not-code pair's citing row is bank0,3AD6")
    assert_that(nc["end"] == "3AF0" and nc["next"] == "445E",
                "whose listing ends at 0x3AF0 and the next bank0 entry is "
                "0x445E -- a 2,417-byte window, not a boundary slip")
    assert_that(nc["window"].startswith("170017041708170c")
                and int(nc["unassigned"]) == 9 and int(nc["db"]) == 1
                and int(nc["db"]) != int(nc["unassigned"]),
                "and whose window opens `17 00 17 04 17 08 17 0c`: 9 of the "
                "walk's instruction starts land on `0x17`. The `db` count is 1, "
                "not 9 -- the two counts differ, and the criterion reads the "
                "byte so it does not depend on disasm8051's table happening to "
                "print `db` for exactly those four. **Corrected here, and the "
                "two counts now disagree for a new reason.** This read 25, and "
                "before that 74 until #1294 gave `mnemonic()` its six "
                "`0x42`/`0x43`/`0x52`/`0x53`/`0x62`/`0x63` cases. "
                "`mnemonic()` has since named the rest of the map the manual "
                "assigns, so the only instruction start in this window that "
                "still renders as `db` is the one byte value the manual "
                "assigns nothing (`0xA5`). What the case was written to protect "
                "is unchanged and is why it still holds: the verdict is driven "
                "by `window[i] in UNASSIGNED`, a literal in this module, so it "
                "reads 9 against 1 rather than 9 against 25 whichever way "
                "`mnemonic()` is spelled. Note that `UNASSIGNED`'s own comment "
                "calls `0x17` a value the map assigns to no instruction, which "
                "is wrong -- `mnemonic()` names it `dec @r1` and the listings "
                "agree -- so the two counts differ for a reason no longer to be "
                "described as agreement. The set is left as it is, deliberately: "
                "changing it moves a published verdict, and that is its own "
                "issue. See ../../docs/findings/mnemonic-db-fallthrough-"
                "coverage.md")
    assert_that(all((r["verdict"] == "not-code") == bool(int(r["unassigned"]))
                    and (r["verdict"] == "no-transfer")
                    == (r["hit_site"] == "" and not int(r["unassigned"]))
                    for r in live),
                "every pair's verdict is read off its own window: `not-code` "
                "exactly when the walk landed on a byte the MCS-51 map assigns "
                "to no instruction, and `no-transfer` exactly when that is not "
                "the case and the window resolved no transfer to the named "
                "callee -- a per-pair property, not a share of the population")
    zero = [r for r in by_verdict["no-transfer"]
            if r["citer_scope"] == "bank0" and r["citer_addr"] == "B5B2"]
    assert_that(len(zero) == 1 and zero[0]["gap"] == "0"
                and zero[0]["end"] == "B5CC" and zero[0]["next"] == "B5CC"
                and zero[0]["window"] == "90089c",
                "the zero-gap shape: bank0,B5B2 ends 0xB5CC, bank0,B5CC starts "
                "there, and the window is its head `90 08 9c`")
    assert_that(zero[0]["hit_site"] == "" and zero[0]["transfers"] == "",
                "which carries no transfer at all, so it is a `no-transfer` and "
                "not a cut to something else")
    assert_that(zero[0]["verdict"] == "no-transfer",
                "read from the window, not from the byte column: the neighbour's "
                "head is `mov DPTR,#0x089C`, not a call to 0xB4A8")

    # The three verdicts partition, and the shapes the write-up's figures describe.
    assert_that(len(live) == len(pop_pairs)
                and {r["verdict"] for r in live} == set(by_verdict)
                and sum(len(v) for v in by_verdict.values()) == len(live),
                "the three verdicts partition the population exactly: it "
                "classifies the pairs `population()` returned, every pair "
                "carries one of the three, and none is left unclassified")

    # The `why` column, against `citations()` called again here rather than
    # against the `Context` the rows were built from -- otherwise a `context()`
    # that had quietly stopped carrying the partition would agree with itself.
    # `citations()` is cheap next to `scan()`, which is the expensive half and
    # is not re-run: it re-reads the annotation CSV and re-frames the comments.
    kept2, rejected2, undecided2, listing_kept2 = cg.citations(ctx.index,
                                                               ctx.listings)
    caller_kept, caller_reasons = set(), {}
    for key, citers in kept2.items():
        for scope, addr, _n in citers:
            caller_kept.add((key, (scope, addr)))
    for c in rejected2:
        caller_reasons[(c.callee, c.citer)] = tuple(c.reasons)

    def four(pair):
        """A pair flat, so the caller's set and the rows' compare directly."""
        callee, citer = pair
        return (callee[0], callee[1], citer[0], citer[1])

    pop_set = {four(p) for p in pop_pairs}

    def live_pairs(partition):
        return {four(((r["callee_scope"], r["callee_addr"]),
                      (r["citer_scope"], r["citer_addr"])))
                for r in live if partition_of(r["why"]) == partition}

    assert_that(live_pairs("kept")
                == {four(p) for p in caller_kept if four(p) in pop_set},
                "every row the `why` column calls `kept` is one `citations()` "
                "itself kept, over the population `population()` returned -- the "
                "column is the caller's partition, not a second reading of the "
                "prose")
    assert_that(live_pairs("rejected")
                == {four(p) for p in caller_reasons if four(p) in pop_set},
                "and every row it calls `rejected` is one `citations()` refused, "
                "for the same reason and over the same pairs")
    assert_that(live_pairs("undecided")
                == pop_set - live_pairs("kept") - live_pairs("rejected"),
                "and every row it calls `undecided` is the remaining one, so the "
                "three partitions together are exactly the population: none "
                "dropped, none invented, none claimed twice")

    by_part = collections.Counter(partition_of(r["why"]) for r in live)
    assert_that(set(by_part) == set(PARTITION_GLOSS)
                and all(r["why"] and ":" in r["why"]
                        and r["why"].split(":", 1)[1]
                        for r in live)
                and sum(by_part.values()) == len(live),
                "no row's `why` is blank or carries a fourth partition or an "
                "empty reason: every row names one of the three and says why, "
                "and they add up to the pair count")

    bad = [r for r in live if partition_of(r["why"]) == "rejected"
           and r["why"].split(":", 1)[1]
           not in caller_reasons.get(((r["callee_scope"], r["callee_addr"]),
                                      (r["citer_scope"], r["citer_addr"])), ())]
    assert_that(not bad,
                "and every `rejected` row's reason is one `citations()` recorded "
                "for that same pair -- a fabricated, defaulted or invented reason "
                "fails here rather than reading as a finding")
    assert_that(live_pairs("kept") and all(
                    ("listing-corroborated" in r["why"])
                    == (((r["callee_scope"], r["callee_addr"]),
                         (r["citer_scope"], r["citer_addr"])) in listing_kept2)
                    for r in live if partition_of(r["why"]) == "kept"),
                "a `kept` row names the arm that kept it -- the citing listing's "
                "own bytes, or the comment's frame -- checked against the "
                "caller's own `listing_kept` set rather than against the column")

    fall = {(r["citer_scope"], r["citer_addr"], r["callee_scope"],
             r["callee_addr"]) for r in live if r["fall_through"] == "yes"}
    rederived = set()
    blocked = set()
    for r in live:
        scope, addr = r["citer_scope"], r["citer_addr"]
        callee = (r["callee_scope"], r["callee_addr"])
        if callee[0] != scope:
            continue
        abutting = junction_of(scope, addr, callee, int(r["end"], 16))
        if abutting is None:
            continue
        # The junction instruction is read here from the committed listing, not
        # from the column, so a `falls_through()` that went back to deciding on
        # addresses alone would fail this rather than agree with itself.
        (blocked if ends_with_transfer(abutting)
         else rederived).add((scope, addr, callee[0], callee[1]))
    assert_that(fall and fall == rederived,
                "the `fall_through` column's `yes` rows are exactly the pairs "
                "whose two listings abut *and* whose junction instruction falls "
                "through -- the citing listing ending where the callee's "
                "begins, or the callee's ending where the citing row begins -- "
                "re-derived here from the committed `.asm` files rather than "
                "from the column, so it cannot drift from the arithmetic that "
                "defines it")
    assert_that({(r["citer_scope"], r["citer_addr"], r["callee_scope"],
                  r["callee_addr"]) for r in live
                 if r["fall_through"] == "blocked"} == blocked and blocked,
                "and its `blocked` rows are exactly the abutting pairs whose "
                "junction is `ret`, `reti`, `sjmp`, `ljmp`, `ajmp` or `jmp` -- "
                "abutting is not crossed, and `bank0,C26E` ends in `C277 ret` "
                "where `bank0,C278` begins, so control returns to the caller "
                "rather than running into the next row")
    assert_that(not (fall & blocked),
                "the two are disjoint: a junction either falls through or it "
                "does not, and no pair is claimed as both")
    assert_that(all(r["fall_through"] == "no"
                    for r in live if r["callee_scope"] != r["citer_scope"]),
                "and it is `no` on every cross-program pair: two exports in "
                "different programs sharing an address are a collision, not an "
                "adjacency, and grading one as the other would credit a data "
                "mention with a control-flow relation it does not have")
    assert_that(all((r["fall_through"] == "")
                    == (not os.path.isfile(os.path.join(
                        cg.DECOMPILED, r["callee_scope"],
                        r["callee_addr"] + ".asm")))
                    for r in live if r["callee_scope"] == r["citer_scope"]
                    and int(r["end"], 16) != int(r["callee_addr"], 16)),
                "and the blank it leaves is exactly the row whose callee has no "
                "listing on disk to read -- not found by this method, never "
                "absent, and not silently scored either way")
    # A conditional branch falls through when it is not taken, so an abutting
    # pair whose junction is one is a real `yes` rather than a `blocked` --
    # read off the listing by name, not counted and not matched against a second
    # table of conditional mnemonics to keep in step with `NO_FALL_THROUGH`.
    b4a8 = next((r for r in live if (r["callee_scope"], r["callee_addr"],
                                     r["citer_scope"], r["citer_addr"])
                 == ("bank0", "B4A8", "bank0", "B5B2")), None)
    assert_that(b4a8 is not None and b4a8["fall_through"] == "yes"
                and junction_mnemonic(os.path.join(
                    cg.DECOMPILED, "bank0", "B4A8.asm")) == "jc",
                "a conditional branch at the junction falls through when it is "
                "not taken, so the pair stays `yes`: bank0,B4A8 cited by "
                "bank0,B5B2 abuts at 0xB5B2 and the junction is `jc 0xb5d2` "
                "inside bank0/B4A8.asm, which reaches the next row on the "
                "not-taken path")
    blocked_rows = [r for r in live if r["fall_through"] == "blocked"]
    assert_that(blocked_rows
                and all(ends_with_transfer(junction_of(
                    r["citer_scope"], r["citer_addr"],
                    (r["callee_scope"], r["callee_addr"]), int(r["end"], 16)))
                    for r in blocked_rows),
                "and every `blocked` row's junction really is one of the "
                "unconditional transfers, read off its own listing -- so "
                "`blocked` is a claim about the instruction sitting on the "
                "boundary and not a restatement of `no`")
    zero_gap_rows = {(r["citer_scope"], r["citer_addr"]) for r in live
                     if r["gap"] == "0"}
    abut_rows = {(r["citer_scope"], r["citer_addr"]) for r in live
                 if r["next"] and int(r["next"], 16) == listing_end(
                     os.path.join(cg.DECOMPILED, r["citer_scope"],
                                  r["citer_addr"] + ".asm"))}
    assert_that(zero_gap_rows and zero_gap_rows == abut_rows
                and all(int(r["next"], 16) - int(r["end"], 16) == int(r["gap"])
                        for r in live if r["next"]),
                "a zero-byte window is a shape, not a tally: the citing rows the "
                "report reads a zero `gap` for are exactly the ones whose listing "
                "ends where the next export in their own scope begins, read back "
                "from the committed listings -- which is why for those rows the "
                "question is the head of the neighbouring export")

    def booked_under_another(r):
        """The callee's inbound edges booked from the citing row's own scope
        under a *different* function -- what the `neighbour_edge` column is."""
        return [edge for edge in ctx.edges.get(
            (r["callee_scope"], r["callee_addr"]), ())
            if edge[0] == r["citer_scope"] and edge[1] != r["citer_addr"]]

    booked = {pair_key(r) for r in live if booked_under_another(r)}
    assert_that(booked and booked == {pair_key(r) for r in live
                                      if r["neighbour_edge"]}
                and all(r["neighbour_edge"]
                        in {"%s:%s %s" % e for e in booked_under_another(r)}
                        for r in live if r["neighbour_edge"]),
                "the `neighbour_edge` column is filled for exactly the pairs "
                "whose callee the graph already reaches from the same scope under "
                "another function, and names one of those edges -- the graph "
                "attributing to a neighbour what the comment attaches here")
    carries = [r for r in live if r["transfers"]]
    assert_that(carries
                and all(r["hit_site"] == "" for r in carries
                        if r["verdict"] != "boundary-cut")
                and all("0x%04X %s" % (int(r["hit_site"], 16), r["hit_text"])
                        in r["transfers"].split("; ")
                        for r in carries if r["hit_site"]),
                "some windows do carry a transfer, and where one does it lands "
                "somewhere other than the named callee -- \"a transfer is there, "
                "but not the one named\" stays a reading of its own, reported "
                "per pair rather than pooled with the windows that carry none")
    assert_that(all(int(r["db"]) == 0 for r in live if r["verdict"] != "not-code"),
                "no window outside the `not-code` pair has a `db` at an "
                "instruction start, which is why the looser `db` form of the "
                "criterion gives the same split on this tree")

    # The two scopes that read a different image. `common` is an export
    # grouping rather than a fourth image and reads against bank 0; `pd` is its
    # own 64 KiB program with its own address space.
    common = [r for r in live
              if r["citer_scope"] == "common" and r["citer_addr"] == "0EF3"]
    assert_that(len(common) >= 1
                and all(r["end"] == "0F12" and r["next"] == "0F12" for r in common),
                "a `common` citer decodes against bank 0: common,0EF3 ends at "
                "0x0F12 and the next common entry is 0x0F12")
    pd_row = [r for r in live
              if r["citer_scope"] == "pd" and r["citer_addr"] == "1041"]
    assert_that(len(pd_row) >= 1
                and all(r["end"] == "104D" and r["next"] == "104D"
                        for r in pd_row),
                "and a `pd` citer against its own image: pd,1041 ends 0x104D and "
                "the next pd entry is 0x104D")
    live_by_scope = by_scope_of(ctx)
    common_rows = {(r["citer_scope"], r["citer_addr"]) for r in live
                   if r["citer_scope"] == "common"}
    common_boundary = {key: next_entry(live_by_scope, "common", int(key[1], 16))
                       for key in common_rows}
    assert_that(common_rows and all(
        b is not None and r["next"] == "%04X" % b
        for r in live if r["citer_scope"] == "common"
        for b in [common_boundary[(r["citer_scope"], r["citer_addr"])]]),
        "every `common` citer's next entry is the next *common*-scope export, "
        "so its window is the common scope's boundary rather than the "
        "executing bank's -- which is the reading the whole `common` scope "
        "split exists to report on")
    # ... and the consequence of reading "the next exported entry in that
    # program" as the citing row's own scope, counted rather than resolved.
    by_scope = {"common": [0x05E7], "bank0": [0x05E6, 0x05E8, 0x9CA6],
                "bank1": [0x05E6, 0x05E8, 0x1738]}
    assert_that(nearer_in_bank(by_scope, "common", 0x05E0, 0x0600)
                == "bank0:0x05E6 bank1:0x05E6",
                "nearer_in_bank names a bank entry strictly between the row and "
                "the common boundary rather than picking one")
    assert_that(nearer_in_bank(by_scope, "common", 0x05E6, 0x05E7) == ""
                and nearer_in_bank(by_scope, "bank0", 0x9C48, 0x9CA6) == "",
                "and reports nothing when no bank entry is nearer, or the citer "
                "is not a `common` one")
    common_zero = {k for k in common_rows
                   if all(r["gap"] == "0" for r in live
                          if (r["citer_scope"], r["citer_addr"]) == k)}
    common_nonzero = common_rows - common_zero
    assert_that(common_nonzero == {("common", EXPECT_COMMON_NONZERO_CITER)},
                "every `common` citer's listing abuts the next common entry "
                "except the one named here, common,%s -- which is the second "
                "`boundary-cut`, so the abutting listing is the rule and this "
                "row is the exception the assertion has to carry"
                % EXPECT_COMMON_NONZERO_CITER)
    nearer = [(r["citer_scope"], r["citer_addr"]) for r in live
              if r["citer_scope"] == "common"
              and nearer_in_bank(live_by_scope, "common",
                                 int(r["citer_addr"], 16), int(r["next"], 16))]
    assert_that(not nearer,
                "and no `common` citer has a bank-scope entry nearer than the "
                "common boundary -- the consequence of reading \"the next "
                "exported entry in that program\" as the citing row's own "
                "scope, reported rather than silently resolved, and empty here")

    # The report's own table, through the same render/compare `--check` runs.
    text = render(live)
    assert_that(render(list(csv.DictReader(text.splitlines()))) == text,
                "the rendered table is a csv.DictReader fixed point")
    assert_that(check_table(text, text) == (0, []),
                "and compares equal against itself, which is --check's passing "
                "case")
    drifted = text.replace(",boundary-cut,", ",no-transfer,")
    rc, lines = check_table(drifted, text)
    assert_that(rc == 1 and lines
                and any("recomputed 'boundary-cut'" in ln for ln in lines),
                "and a table with one verdict altered is rejected, naming that "
                "row and that column")
    drifted = text.replace("kept:code-frame", "kept:listing-corroborated", 1)
    rc, lines = check_table(drifted, text)
    assert_that(rc == 1 and lines
                and any("recomputed 'kept:code-frame'" in ln for ln in lines),
                "and a table with one `why` altered is rejected the same way, so "
                "the partition is held by --check and not only by the census")
    dropped = "\n".join(text.splitlines()[:-1]) + "\n"
    rc, lines = check_table(dropped, text)
    assert_that(rc == 1
                and lines == ["  row count: committed %d, recomputed %d"
                              % (len(live) - 1, len(live))],
                "and a table with its last row dropped is rejected on the row "
                "count, which no cell-by-cell comparison can see")

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true",
                      help="write ec/ghidra/gap-citation-scan.csv")
    mode.add_argument("--check", action="store_true",
                      help="recompute the table and fail on any diff")
    mode.add_argument("--self-test", action="store_true",
                      help="known answers from committed inputs and the 8051 map")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.check:
        return check()

    ctx = context()
    rows = classify(ctx)
    report(ctx, rows)
    if args.report:
        with open(REPORT, "w", newline="") as f:
            f.write(render(rows))
        print()
        print("wrote %s (%d rows)" % (os.path.relpath(REPORT, REPO), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
