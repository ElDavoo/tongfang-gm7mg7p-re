#!/usr/bin/env python3
"""Read the bytes Ghidra's function boundary cut out of a citing listing.

`citation_callers.py` vetoes a pair whose citing listing is an `0xFF` fill run
and corroborates one whose listing carries a transfer to the named callee. Both
rules read the citing row's *own* export, and there is a population they can
never reach: a real call at an address the export stops short of. 89 of the 105
citing rows `citing-listing-evidence.md` measured turned out to have no gap at
all, so for most of them the question is what sits at the head of the
*neighbouring* export -- but for the other 16 the call really is between two
exports, and nothing in the repository asked whether it was there.

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
           "verdict", "gap", "end", "next", "window", "transfers",
           "hit_site", "hit_text", "at_next", "neighbour_edge",
           "db", "unassigned", "truncated", "frame_onto", "frame_over"]

# `lcall`/`ljmp` are the widest transfer, so a window that stopped at the
# boundary could cut one in half. See the module docstring.
SLACK = 3

# The four byte values the MCS-51 map assigns to no instruction. Stated from
# the manual, not read out of `disasm8051.py`: an oracle derived from the tool
# it is testing asserts nothing, which is the note `disasm8051.TEXTBOOK_BIT_SITES`
# makes about its own `0xC1`/`0xC2` pair. The self-test pairs the two -- the
# manual says these are unassigned, `disasm8051` prints `db` for them -- because
# the pairing is the assertion, and it is what stops this list from quietly
# becoming a second copy of the decoder's coverage.
UNASSIGNED = (0x06, 0x07, 0x16, 0x17)

# Known answers, measured on the committed tree and asserted in --self-test.
# They are literals here rather than read out of the committed CSV, so a listing
# or annotation edit that moves one fails instead of quietly re-basing the claim.
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
#
# `docs/findings/citation-gap-scan.md` carries the correction in place.
EXPECT_ROWS = 99
EXPECT_PAIRS = 124
# The second cut is `common,3459` cited by `common,355E` -- #603's own rank-1
# tranche row, whose one-`ret` listing is followed by 25 bytes before the next
# common entry, and whose `ljmp 0x3459` sits at that boundary. It is the
# zero-gap case the write-up describes, turning out to carry a real transfer.
EXPECT_CUT = 2
EXPECT_NOT_CODE = 1
EXPECT_NO_TRANSFER = 121
# The issue's premise is the exception: 86 of the 99 citing rows have a
# zero-byte window, so for most of the population the question is the head of
# the neighbouring export rather than bytes stranded between two. 110 of the
# 124 pairs, counting a comment that names three callees three times.
EXPECT_ZERO_GAP_ROWS = 86
EXPECT_ZERO_GAP_PAIRS = 110
# Pairs where the callee's edge list already books a same-scope transfer under a
# *different* function -- the graph attributing to a neighbour what the comment
# attaches elsewhere. Up on #603 for the same reason the cut count is: the
# tranche's rows are `common`, and the six new citers each name callees whose
# inbound already sits on a neighbour.
EXPECT_NEIGHBOUR_EDGE = 32
EXPECT_COMMON_CITERS = 10
# How many of the common citers have a zero-byte window. This used to be all of
# them, and saying so was the point: a common listing abutting the next common
# entry is why the scope-boundary worry never bit. #603's `common,355E` breaks
# it -- a one-`ret` row with 25 bytes before the next common entry -- so the
# figure is a count and the exception is named in the assert that reads it.
EXPECT_COMMON_ZERO_GAP = 9
EXPECT_COMMON_NONZERO_CITER = "355E"
# Of the common citers, how many have a bank-scope entry nearer than the common
# one. The common window is the common scope's boundary by construction, and at
# runtime the executing bank's is the one that exists; this is that consequence
# counted rather than silently resolved. Zero on this tree.
EXPECT_COMMON_SHORTER_IN_BANK = 0

Context = collections.namedtuple("Context", "index edges listings pairs")


def listing_end(path):
    """The address one past the citing listing's last instruction, or None.

    Read from the byte column rather than from the mnemonic, because a
    `ret`/`nop`/`reti` line carries no operand and so is five tokens where
    `mov A, #0x10` is six -- and the bytes are what say how long the function
    is. `verify_reassembly.parse_listing` is the committed reader of that column
    and the one `verify_gap_text` already decodes from, so it is reused here
    rather than a third parse of the same lines.
    """
    last = None
    for addr, hexbytes, _mnem, _ops in V.parse_listing(path):
        last = (addr, len(hexbytes) // 2)
    if last is None:
        return None
    return last[0] + last[1]


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
    """
    index = cg.load_index()
    edges, _unresolved, _orphans, _total, listings = cg.scan(index)
    kept, rejected, undecided, _listing_kept = cg.citations(index, listings)
    pairs = set()
    for key, citers in kept.items():
        pairs.update((key, (scope, addr)) for scope, addr, _n in citers)
    pairs.update((c.callee, c.citer) for c in rejected)
    pairs.update((c.callee, c.citer) for c in undecided)
    return Context(index, edges, listings, pairs)


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

        onto, over = D.converges_from(image, end) if end else (0, 0)
        out.append({
            "callee_scope": callee[0],
            "callee_addr": callee[1],
            "citer_scope": scope,
            "citer_addr": addr,
            "verdict": verdict,
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
    print()
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
    print()
    print("  limit: %d of the %d pairs are `no-transfer`, which is this window "
          "carrying" % (tal.get("no-transfer", 0), len(rows)))
    print("  no transfer to the named callee -- not the comment being wrong, and")
    print("  not the call being absent. %d window(s) carry a transfer that lands "
          "elsewhere;" % with_transfer)
    print("  those are a different reading and are not pooled with the rest.")
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

    # The `not-code` criterion's own oracle, stated from the manual's opcode map
    # and paired with the decoder -- the `disasm8051.TEXTBOOK_BIT_SITES` shape.
    # A `db` on its own would be the partial table deciding; the manual and the
    # table agreeing is the assertion.
    assert_that(len(UNASSIGNED) == 4 and all(0 < b < 0x100 for b in UNASSIGNED),
                "the map-unassigned set is four byte values")
    assert_that(all(D.mnemonic(bytes([b]), 0, 0).startswith("db ")
                    for b in UNASSIGNED),
                "and disasm8051 prints `db` for each of 0x06, 0x07, 0x16, 0x17")
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

    # The population, and the pins the write-up quotes.
    ctx = context()
    pop_rows, pop_pairs = population(ctx)
    citers = set(pop_rows)
    assert_that(len(citers) == EXPECT_ROWS,
                "the population reproduces %d citing rows (measured %d)"
                % (EXPECT_ROWS, len(citers)))
    assert_that(len(pop_pairs) == EXPECT_PAIRS,
                "and %d (callee, citer) pairs over them (measured %d)"
                % (EXPECT_PAIRS, len(pop_pairs)))
    assert_that({p[1] for p in pop_pairs} == citers,
                "every pair's citing row is in the row set, so the two numbers "
                "describe one population and cannot be read as contradicting")
    assert_that(len({(p[0], p[1]) for p in pop_pairs}) == len(pop_pairs),
                "and the pairs are distinct")

    # The predicate is the transfer-line one and not the resolved-target one,
    # which is a *different* population: a listing can carry a transfer that
    # resolves to no index row, and those rows are the whole of the difference.
    alt_rows, alt_pairs = resolved_empty_population(ctx)
    extra = set(alt_rows) - citers
    assert_that(len(alt_rows) == EXPECT_ROWS + 2
                and len(alt_pairs) == EXPECT_PAIRS + 2,
                "the resolved-target predicate gives %d rows / %d pairs against "
                "the transfer-line predicate's %d / %d"
                % (len(alt_rows), len(alt_pairs), EXPECT_ROWS, EXPECT_PAIRS))
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

    # The worked example the issue names, and the census it sits in.
    cut = [r for r in by_verdict["boundary-cut"]]
    assert_that(len(cut) == EXPECT_CUT, "%d boundary-cut pair(s)" % EXPECT_CUT)
    e57e = cut[0]
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
    assert_that(len(by_verdict["not-code"]) == EXPECT_NOT_CODE,
                "%d not-code pair(s)" % EXPECT_NOT_CODE)
    nc = by_verdict["not-code"][0]
    assert_that(nc["citer_scope"] == "bank0" and nc["citer_addr"] == "3AD6",
                "the not-code pair's citing row is bank0,3AD6")
    assert_that(nc["end"] == "3AF0" and nc["next"] == "445E",
                "whose listing ends at 0x3AF0 and the next bank0 entry is "
                "0x445E -- a 2,417-byte window, not a boundary slip")
    assert_that(nc["window"].startswith("170017041708170c")
                and int(nc["unassigned"]) == 9 and int(nc["db"]) == 74,
                "and whose window opens `17 00 17 04 17 08 17 0c`: 0x17 is a "
                "byte the MCS-51 map assigns to no instruction, and 9 of the "
                "walk's instruction starts land on one. The `db` count is 74, "
                "not 9 -- the two counts differ, and the criterion reads the "
                "byte so it does not depend on disasm8051's table happening to "
                "print `db` for exactly those four")
    assert_that(len(by_verdict["no-transfer"]) == EXPECT_NO_TRANSFER,
                "%d no-transfer pairs" % EXPECT_NO_TRANSFER)
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

    # The three verdicts partition, and the shape figures the write-up quotes.
    assert_that(sum(len(v) for v in by_verdict.values()) == len(live)
                == EXPECT_PAIRS,
                "the three verdicts partition all %d pairs" % len(live))
    assert_that(sum(1 for r in live if r["gap"] == "0") == EXPECT_ZERO_GAP_PAIRS
                and len({(r["citer_scope"], r["citer_addr"]) for r in live
                         if r["gap"] == "0"}) == EXPECT_ZERO_GAP_ROWS,
                "%d of %d pairs (%d rows) have a zero-byte window, so the "
                "question for most of the population is the head of the "
                "neighbouring export"
                % (EXPECT_ZERO_GAP_PAIRS, len(live), EXPECT_ZERO_GAP_ROWS))
    assert_that(sum(1 for r in live if r["neighbour_edge"])
                == EXPECT_NEIGHBOUR_EDGE,
                "%d pairs' callee is already reached from the same scope under "
                "another function" % EXPECT_NEIGHBOUR_EDGE)
    assert_that(sum(1 for r in live if r["transfers"]) == 12,
                "12 windows carry a transfer that lands somewhere other than "
                "the named callee -- reported per pair, not pooled with the "
                "112 that carry none")
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
    assert_that(len({(r["citer_scope"], r["citer_addr"]) for r in live
                     if r["citer_scope"] == "common"}) == EXPECT_COMMON_CITERS,
                "%d `common` citers, whose window is the common scope's boundary"
                % EXPECT_COMMON_CITERS)
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
    common_rows = {(r["citer_scope"], r["citer_addr"]) for r in live
                   if r["citer_scope"] == "common"}
    common_zero = {k for k in common_rows
                   if all(r["gap"] == "0" for r in live
                          if (r["citer_scope"], r["citer_addr"]) == k)}
    common_nonzero = common_rows - common_zero
    assert_that(len(common_zero) == EXPECT_COMMON_ZERO_GAP
                and common_nonzero == {("common", EXPECT_COMMON_NONZERO_CITER)},
                "%d of the %d `common` citers are zero-gap and the only one "
                "that is not is common,%s -- the second `boundary-cut`, so the "
                "common listing that abuts its neighbour is the exception here "
                "rather than the rule"
                % (EXPECT_COMMON_ZERO_GAP, EXPECT_COMMON_CITERS,
                   EXPECT_COMMON_NONZERO_CITER))
    live_by_scope = by_scope_of(ctx)
    shorter = sum(1 for r in live if r["citer_scope"] == "common"
                  and nearer_in_bank(live_by_scope, "common",
                                     int(r["citer_addr"], 16), int(r["next"], 16)))
    assert_that(shorter == EXPECT_COMMON_SHORTER_IN_BANK,
                "and the report's own count of them agrees: %d `common` citers "
                "have a bank-scope entry nearer than the common boundary, which "
                "is what the re-export would have to change for this to move"
                % shorter)

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
