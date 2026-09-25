#!/usr/bin/env python3
"""Order the unannotated common-area functions no other open issue owns.

`ec/annotations/subsystems.md` §2 measures the largest single block of undecoded
firmware in this repository: 656 of the 753 exported `common`-area functions
carried no annotation row when this tool was written, 87% of the program. A size
is not a queue. This tool is the queue -- a stated, total, re-derivable ordering
over the rows no other issue has claimed, and the named cut that took the first
tranche out of it. **Those 37 rows are annotated now, 618 are left, and the cut
is exhausted**; what follows describes both the tranche and the remainder,
because the committed file is the tranche's record and this run is the
remainder's.

**The pool is what is left after three exclusions, each measured.** The whole
656 was not available: #574 owns the 403 BL51 cross-bank trampolines' DPTR
immediates in the contiguous common-area block `0x1150`-`0x1ABC` (201 of the
unannotated rows, and still 201 today), #555 owns the 42 seeds that tile
`bank1:0x8001`-`0x8189` (0 of them, because that window is past the common
area's `0x7FFF` end and cannot overlap by construction), and #456 owns five
specific boundary-hypothesis rows (all five already annotated, so it owns none
of the pool). That made the pool **455** when the tranche was cut and **417**
now, and every exclusion is an address range or a named address list read off
the committed tree, never a hand-typed skip list of the rows a previous run
happened to see.

**The ordering is composite, stated once, and leaves nothing to taste.**

  1. inbound call-graph degree, descending -- `ec/annotations/call-graph-callees.csv`;
  2. XDATA read+write weight, descending -- the `functions` column of
     `ec/annotations/xdata-registers.csv`, counting the `common:0xADDR=` tokens
     naming the address, over the registers with `read+write > 0`;
  3. address, ascending -- the tie-break, so the order is reproducible.

**The XDATA weight is read from `functions`, not `functions_touched`, and that
is the one correction this tool exists partly to carry.** The two columns look
like the same census and are not: `functions_touched` is a *count*, `functions`
is the token list. Reading the count as a list matches nothing, and the ranking
that comes out has a weight of exactly 0 for every row -- which looks like a
measurement, and sorts the whole pool on its address alone while appearing to
have consulted a second signal. `--self-test` runs both columns and asserts
the wrong one gives zero, so the check that has quietly stopped rejecting is
the one that goes red.

**Reachability from the vector table is a column, not a sort key.** The roots
are `build_ec_decompile.discover_vector_table()`'s own 12 targets, read out of
the firmware and not re-derived here; the walk forwards over the committed
`.asm` listings through `call_graph.Index.resolve`, the same resolution rule
the call graph itself uses. At the cut it reached 13 unannotated common-area
functions, 10 of them outside #574's band; 3 of the 13 are unannotated still.
Carrying that as a column rather than folding it into the sort is a choice
about what a reader has to hold in their head: as a sort key, one
vector-reached address with a single inbound call would outrank one with
twelve, for a reason the ordering never states. As a column it is a fact about
thirteen rows, and the cut is a union rather than a threshold.

**What the cut is, and what it is not.** `inbound >= 4` unioned with
"forward-reachable from the vector table", over the pool. A predicate over the
ranking, not a round number -- the same discipline
`ec/annotations/README.md` §"The second batch" used when it cut on a measurable
boundary rather than a count. It selected **37 rows totalling 999 bytes** of
committed listing, and it is now **exhausted**: every row that qualified
carries an annotation row, so a run today selects none. That is a fact about
the cut rather than a fault in it, and the report says so instead of printing
an empty tranche. The next tranche's cut has to move down the ranking -- the
top of the remainder is 30 rows tied at `inbound=3`.

**The committed CSV is the tranche's record, and is deliberately not this run's
output.** `ec/annotations/common-runtime-ranking.csv` holds the 455-row ordering
the 37 were cut from, in rank order, with an `in_tranche` column. Those 37 are
annotated now, so a fresh run cannot re-rank them and regenerating the file
would lose which rank each landed at -- the one thing a reader needs to judge
the next cut. The self-test holds the two apart: it pins the live population
*and* asserts that all 37 `in_tranche` rows carry an annotation row, that the
418 below them are the rest of the pool, and that the single row the tranche
annotated without a CSV row of its own is the `ljmp 0x0A74` thunk at `0x10FA`,
which the exporter renamed after its target -- 37 rows moved 38 index rows.

**What a rank is not.** Three limits, in the order they bite.

  * A count is a **ranking, not evidence of what a function does.** `inbound`
    is how many resolved transfers reach an address; it says nothing about the
    function's job. `common 0x355E` led the pool at 12 and its listing is one
    `ret` byte -- a shared epilogue, reached by twelve `ljmp` from two callers.
  * The **291 unannotated rows no transfer reaches are "not found by this
    method", never "unreachable"** (153 of the 417-row pool;
    `ec/annotations/registers.yaml` states the same rule for its own census). A
    row absent from `call-graph-callees.csv` is a row the listing walk placed
    nowhere: the boundary may cut the transfer, the caller may be reached only
    through data, and the common area is exported on a call-target byte scan
    that is an upper bound by construction
    (`ec/annotations/bank-call-audit.md` §1).
  * The XDATA weight is a **census of decompiled text** and shares the C-level
    blind spot `registers.yaml` documents, so it is not independent
    confirmation of anything the comment on a row says. It is a tie-break.

**Nothing here was observed on hardware.** No register was read, written or
read back, and no interrupt was delivered. Every input is a committed file: the
firmware for the vector walk, the export for the population, and the three
annotation CSVs for the signals. Ranking a function is not a claim about it.

Usage:
    python3 rank_common_runtime.py                # print every figure
    python3 rank_common_runtime.py --emit-csv     # the live ranking, to stdout
    python3 rank_common_runtime.py --self-test    # the known answers, the refusals
"""
import argparse
import collections
import csv
import os
import re
import sys

from build_ec_decompile import (FIRMWARE, discover_vector_table, file_offset)
from citation_callers import norm_addr, transfer_targets
import call_graph

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
ANNOTATIONS = os.path.join(EC, "annotations")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
FUNCTIONS_CSV = os.path.join(ANNOTATIONS, "ghidra-functions.csv")
CALL_GRAPH_CSV = os.path.join(ANNOTATIONS, "call-graph-callees.csv")
XDATA_CSV = os.path.join(ANNOTATIONS, "xdata-registers.csv")
RANKING_CSV = os.path.join(ANNOTATIONS, "common-runtime-ranking.csv")

# #574's block, as `ec/annotations/bank-call-audit.md` §7 gives it: 403
# contiguous common-area trampolines, 0x1150 through 0x1ABC. Excluded as an
# address range, so a row that arrives inside it later is excluded by the same
# rule rather than by being typed onto a skip list.
BAND_574 = (0x1150, 0x1ABC)

# #555's window, carried for the measurement rather than for the cut: the
# seeds it owns are `bank1` rows in a banked window, and the common area ends
# at 0x7FFF, so no pool address can be in it. The census prints the count (0)
# so a future reader sees a measurement and not an assumption.
BAND_555 = (0x8001, 0x8189)

# #456's five boundary-hypothesis rows. All five carry an annotation row today,
# so none is in the pool; the list is carried and the census prints each row's
# current state, so the exclusion stays correct if the rows are ever retyped
# back to unannotated ahead of this tranche.
ROWS_456 = (("common", "0x4A76"), ("common", "0x3B4E"), ("common", "0x7177"),
            ("common", "0x0200"), ("bank0", "0xD2BE"))

# The cut. A predicate over the ranking, stated here once and nowhere else, so
# `--self-test` can pin the 37 addresses it selects and a later tranche can
# widen it by editing this tuple rather than by re-deriving the population.
INBOUND_CUT = 4

# The `common:0xNNNN=` token shape inside `xdata-registers.csv`'s `functions`
# column. Anchored on `=` because that column spells `scope:addr=name`, and the
# address is the middle field: matching the column's `addr` (`0x0A53`) or
# `span_group` would both silently return nothing.
FUNC_TOKEN = re.compile(r"common:0x([0-9A-Fa-f]{4})=")

RANKING_COLUMNS = ["rank", "scope", "addr", "inbound", "xdata_weight",
                   "vector_reachable", "in_band_574", "in_tranche"]


def read_csv(path):
    """Rows of a committed CSV, read strictly.

    `strict=True` for `build_ec_decompile.read_index`'s reason: a quoting
    mistake must be a loud failure and not a row quietly missing, because every
    count below is a count of rows."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def common_unannotated():
    """The `common`-area exports `index.csv` marks unannotated, as hex addrs.

    Read off the export's own `annotated` column rather than recomputed from
    `ghidra-functions.csv`, because the two disagree on a measured 18 rows
    (`ec/annotations/subsystems.md` §2) and the export is the file the census
    table is held to. Sorted, so the pool's order does not depend on the CSV's.
    """
    return sorted({norm_addr(r["addr"]) for r in read_csv(INDEX_CSV)
                   if r["program"] == "common" and r["annotated"] == "no"})


def annotated_keys():
    """The `(scope, addr)` keys `ghidra-functions.csv` carries."""
    return {(r["scope"], norm_addr(r["addr"])) for r in read_csv(FUNCTIONS_CSV)}


def common_sizes():
    """`common` address -> the export's `size` for it, read once and cached.

    A function's size is what decides how much listing a tranche row is asking a
    reader to read, so the report quotes it rather than the reader estimating it
    from the row count. Cached because the self-test asks for it per row and
    the file is 2,710 rows.
    """
    if not hasattr(common_sizes, "_cache"):
        common_sizes._cache = {norm_addr(r["addr"]): int(r["size"])
                               for r in read_csv(INDEX_CSV)
                               if r["program"] == "common"}
    return common_sizes._cache


def inbound_counts():
    """`common`-area address -> the call graph's inbound count for it.

    Read from the committed `call-graph-callees.csv` rather than by re-walking
    the listings, so this ranking and `call_graph.py --check` cannot come to
    disagree about what a row's inbound count is. A missing address means this
    method placed no transfer there and reads as 0 for ranking purposes -- which
    is why the report separates "0 inbound calls" from "no call-graph row" and
    the write-up calls both not-found-by-this-method.
    """
    return {norm_addr(r["addr"]): int(r["inbound"])
            for r in read_csv(CALL_GRAPH_CSV)
            if r["scope"] == "common"}


def xdata_weights(column="functions"):
    """`common`-area address -> the XDATA read+write weight for it.

    `column` is a parameter so `--self-test` can run the same counting over
    `functions_touched` and show the zero it produces; the default is
    `functions`, and the whole difference between a measurement and a
    measurement that is always zero is which of the two is passed here.
    """
    out = collections.Counter()
    for row in read_csv(XDATA_CSV):
        if int(row["read+write"]) <= 0:
            continue
        for token in row[column].split(";"):
            m = FUNC_TOKEN.match(token.strip())
            if m:
                out[m.group(1).upper()] += 1
    return out


def vector_roots(fw=None):
    """The vector table's own 12 targets, read out of the firmware.

    `build_ec_decompile.discover_vector_table()` is imported and called, not
    reimplemented: the walk is the exporter's, it has defeated the textbook
    layout on both images, and a second copy here would be a second answer to
    the same question. Read from bank 0's window because that is where
    `ec/decompiled/common/**` was exported from; the common area is
    byte-identical in both banks either way.
    """
    if fw is None:
        fw = open(FIRMWARE, "rb").read()
    off = file_offset("bank0", 0)
    entries = discover_vector_table(fw[off:off + 0x8000])
    return sorted(norm_addr("%04X" % t) for _off, t in entries if t is not None)


def vector_reachable(index, decompiled=DECOMPILED):
    """Every `(scope, addr)` forward-reachable from the vector roots.

    The roots themselves are in the set, which is the point: `0x05E7` is reached
    by being a vector target and by nothing else, and a walk that only counted
    what its roots transfer to would drop the one address
    `ec/annotations/subsystems.md` §3 records as carrying no row at all.

    Transfers come from `citation_callers.transfers` and resolve through
    `call_graph.Index.resolve`, so this walk and `call_graph.py --check` share
    one grammar and one resolution rule. A target that resolves to nothing is
    not counted and not reported as a dead end: it is a transfer this method
    cannot place, the same class of thing as the 291 pool rows below.
    """
    seen = set()
    frontier = {("common", a) for a in vector_roots()}
    while frontier:
        key = frontier.pop()
        if key in seen:
            continue
        seen.add(key)
        scope, addr = key
        path = os.path.join(decompiled, scope, addr + ".asm")
        if not os.path.isfile(path):
            continue
        for target in transfer_targets(path):
            row = index.resolve(scope, target)
            if row is None:
                continue
            # Discovered is not visited. Marking a node seen on the way in
            # would make the `seen` test above skip the one listing that can
            # reach anything, and the walk would stop one hop out.
            frontier.add((row["program"], row["_addr"]))
    return seen


def in_band_574(addr):
    """True when an address is inside #574's trampoline block."""
    return BAND_574[0] <= int(addr, 16) <= BAND_574[1]


def pool():
    """The ordered pool: every common unannotated export, minus #574's band.

    #456's five rows are subtracted by membership in the committed annotation
    file rather than by the constant alone, because they are all annotated
    today and so are already outside `common_unannotated()`; naming them here
    makes the subtraction visible in the census rather than implicit, and means
    a future retyping is excluded without editing this function.
    """
    excluded = {norm_addr(addr) for _scope, addr in ROWS_456}
    return [a for a in common_unannotated()
            if not in_band_574(a) and a not in excluded]


def build(index=None, decompiled=DECOMPILED):
    """The whole population as dicts, in rank order.

    One place that assembles the signals, so the report, the CSV and the
    self-test cannot read them in three different orders and produce three
    different rankings.
    """
    index = index if index is not None else call_graph.load_index()
    reachable = {addr for scope, addr in vector_reachable(index, decompiled)
                 if scope == "common"}
    inbounds = inbound_counts()
    weights = xdata_weights()
    rows = []
    for addr in pool():
        rows.append({"scope": "common", "addr": addr,
                     "inbound": inbounds.get(addr, 0),
                     "xdata_weight": weights.get(addr, 0),
                     "vector_reachable": addr in reachable,
                     "in_band_574": False,
                     "in_tranche": (inbounds.get(addr, 0) >= INBOUND_CUT
                                    or addr in reachable)})
    rows.sort(key=lambda r: (-r["inbound"], -r["xdata_weight"], r["addr"]))
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


def report(rows):
    """The whole census as the lines `docs/findings/common-runtime-tranche.md`
    quotes. Every figure in the write-up is a line here, and the write-up's
    numbers are re-derivable by running this."""
    out = []
    say = out.append

    unannotated = common_unannotated()
    annotated = annotated_keys()
    inbounds = inbound_counts()
    in_band = [a for a in unannotated if in_band_574(a)]
    b555 = [a for a in unannotated if BAND_555[0] <= int(a, 16) <= BAND_555[1]]
    reached = [r for r in rows if r["vector_reachable"]]
    tranche = [r for r in rows if r["in_tranche"]]

    say("rank_common_runtime.py -- the unannotated common-area pool, ordered")
    say("")

    # --- the population, and every exclusion applied to it ---
    say("## population and exclusions")
    say(f"common-area exported and unannotated (index.csv): {len(unannotated)}")
    say(f"  #574's block 0x{BAND_574[0]:04X}-0x{BAND_574[1]:04X}: "
        f"{len(in_band)} unannotated row(s), excluded by address")
    say(f"  #555's window bank1:0x{BAND_555[0]:04X}-0x{BAND_555[1]:04X}: "
        f"{len(b555)} unannotated common row(s) -- the common area ends at "
        f"0x7FFF, so the overlap is zero by construction, and this is the "
        f"measurement of it")
    for scope, addr in ROWS_456:
        state = "annotated" if (scope, norm_addr(addr)) in annotated \
            else "UNANNOTATED (excluded)"
        say(f"  #456 boundary row {scope} 0x{norm_addr(addr)}: {state}")
    say(f"  pool: {len(rows)}")
    say("")

    # --- the three signals, each with what it did not reach ---
    say("## the three signals")
    placed = [r for r in rows if r["inbound"] > 0]
    all_placed = [a for a in unannotated if inbounds.get(a, 0) > 0]
    say(f"  inbound call-graph degree, from {os.path.basename(CALL_GRAPH_CSV)}: "
        f"{len(all_placed)} of the {len(unannotated)} unannotated common rows "
        f"have a non-zero count and {len(unannotated) - len(all_placed)} are "
        f"not found by this method, which is not 'unreachable'")
    say(f"    within the pool: {len(placed)} of {len(rows)} placed, "
        f"{len(rows) - len(placed)} not")
    weighted = [r for r in rows if r["xdata_weight"] > 0]
    say(f"  XDATA read+write weight, from the `functions` column of "
        f"{os.path.basename(XDATA_CSV)}: {len(weighted)} of {len(rows)} pool "
        f"rows have a non-zero weight")
    reached_all = {a for scope, a in vector_reachable(
        call_graph.load_index()) if scope == "common"} & set(unannotated)
    both = [r for r in reached if r["inbound"] >= INBOUND_CUT]
    say(f"  forward reachability from the vector table: "
        f"{len(reached_all)} of the {len(unannotated)} unannotated common rows "
        f"are reachable from {len(vector_roots())} roots, {len(reached)} of "
        f"them in the pool"
        + (f"; {len(both)} also clear the inbound cut, so the union below is a "
           f"union and not a second copy of the same predicate"
           if both else "; none of them is in the pool, so the reachability "
                "arm adds nothing to the cut today"))
    say("")

    # --- the cut, and the whole pool under it ---
    say("## the ranking (all %d pool rows, in order)" % len(rows))
    say("  %-4s %-6s %6s %5s %5s"
        % ("rank", "addr", "inbound", "xdata", "vec"))
    for row in rows:
        say("  %-4d %-6s %6d %5d %5s"
            % (row["rank"], row["addr"], row["inbound"], row["xdata_weight"],
               "yes" if row["vector_reachable"] else "-"))
    say("")

    say("## the cut")
    say(f"  cut: inbound >= {INBOUND_CUT}, unioned with forward reachability, "
        f"over the pool")
    if tranche:
        say(f"  {len(tranche)} row(s) of {len(rows)} pool rows qualify today")
        for row in tranche:
            say("    %-6s rank %-3d inbound %-2d xdata %-2d %s"
                % (row["addr"], row["rank"], row["inbound"],
                   row["xdata_weight"],
                   "vector-reachable" if row["vector_reachable"] else ""))
    else:
        # An exhausted cut is a result, and printing an empty tranche under a
        # heading that reads like a failure would be the wrong shape for it.
        top = [r for r in rows if r["inbound"] >= INBOUND_CUT - 2][:12]
        say(f"  0 row(s): the cut is EXHAUSTED. Every row that qualified at "
            f"`inbound >= {INBOUND_CUT}` or by vector reachability carries an "
            f"annotation row, so the next tranche's cut has to move down the "
            f"ranking rather than reuse this one.")
        say(f"  the {len(rows)} rows below it start at `inbound="
            f"{rows[0]['inbound'] if rows else 0}`; the first "
            f"{len(top)} are:")
        for row in top:
            say("    %-6s rank %-3d inbound %-2d xdata %-2d"
                % (row["addr"], row["rank"], row["inbound"],
                   row["xdata_weight"]))

    landed = committed_tranche()
    if landed:
        say("")
        say("## the tranche that tool cut, as committed")
        say(f"  {os.path.relpath(RANKING_CSV, os.path.dirname(HERE))} holds the "
            f"455-row ordering issue #603 cut from; those rows are annotated "
            f"now, so a fresh run cannot re-rank them and the file is that "
            f"tranche's record rather than this run's output.")
        say(f"  {len(landed)} row(s) carry `in_tranche=yes`, "
            f"{len([a for a, _r in landed if ('common', a) not in annotated])}"
            f" of them without an annotation row")
        say("    " + " ".join(a for a, _r in landed))
    return "\n".join(out), rows


def committed_tranche():
    """The `in_tranche=yes` rows of the committed ranking, in rank order.

    Read rather than re-derived, for the reason the docstring gives: the tranche
    is annotated, so the live pool no longer contains it and the committed file
    is the only place the rank each row landed at still exists.
    """
    if not os.path.isfile(RANKING_CSV):
        return []
    rows = [r for r in read_csv(RANKING_CSV) if r.get("in_tranche") == "yes"]
    return sorted(((norm_addr(r["addr"]), r) for r in rows),
                  key=lambda pair: int(pair[1].get("rank") or 0))


def emit_csv(rows, stream=sys.stdout):
    """The live ranking, in the committed file's column order, to a stream.

    `--emit-csv` is how the file is *created*, once, from the 455-row pool the
    tranche was cut from. It is deliberately not a regeneration of it: the
    tranche is annotated, so a run today emits the 417-row remainder and
    writing that over the file would erase the ranks the 37 landed at. The
    self-test holds the two apart instead, and the report prints both.
    """
    writer = csv.DictWriter(stream, fieldnames=RANKING_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("yes" if row[k] is True else
                             "no" if row[k] is False else row[k])
                         for k in RANKING_COLUMNS})


def self_test() -> int:
    """Known answers, and the refusals that make them worth anything.

    Every figure below is transcribed by hand from a read of the committed
    listings, the export and the three annotation CSVs, so this suite fails the
    day any of them moves rather than agreeing with a tool that drifted. The
    refusals are the half that matters: a check that has quietly stopped
    rejecting looks exactly like a check that is working.
    """
    bad = 0
    print("rank_common_runtime.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    index = call_graph.load_index()
    rows = build(index)
    by_addr = {r["addr"]: r for r in rows}
    tranche = [r for r in rows if r["in_tranche"]]
    inbounds = inbound_counts()

    # --- the population ---
    unannotated = common_unannotated()
    check("618 common-area exports are unannotated, 656 before issue #603's "
          "37-row tranche landed",
          len(unannotated) == 618, "got %d" % len(unannotated))
    in_band = [a for a in unannotated if in_band_574(a)]
    check("201 of them are in #574's 0x1150-0x1ABC block, untouched by the "
          "tranche", len(in_band) == 201, "got %d" % len(in_band))
    check("the block's unannotated rows run 0x116E to 0x1800, the annotated "
          "trampolines interleaved",
          min(in_band) == "116E" and max(in_band) == "1800",
          "got %s..%s" % (min(in_band), max(in_band)))
    check("no common unannotated row is in #555's bank1 window",
          not [a for a in unannotated
               if BAND_555[0] <= int(a, 16) <= BAND_555[1]])
    annotated = annotated_keys()
    check("#456's five boundary rows all carry a row today",
          all((s, norm_addr(a)) in annotated for s, a in ROWS_456),
          "missing " + ", ".join("%s,%s" % (s, norm_addr(a))
                                 for s, a in ROWS_456
                                 if (s, norm_addr(a)) not in annotated))
    check("the pool is 417 rows, the 455 the tranche was cut from less its 37 "
          "and the one row the tranche annotated without a row of its own",
          len(rows) == 417, "got %d" % len(rows))

    # --- the exclusion is by address, not by a skip list ---
    # Every #574 row is out and every pool row is in, checked by the range
    # itself rather than by comparing against a list of the rows an earlier run
    # saw: a skip list would pass this too, and a renamed or moved row would
    # not.
    check("every #574 row is excluded and no other address is",
          all(not any(r["addr"] == a for r in rows) for a in in_band)
          and all(not in_band_574(r["addr"]) for r in rows)
          and {a for a in unannotated if not in_band_574(a)} == {r["addr"] for r in rows},
          "pool %d, in-band leaked %d"
          % (len(rows), sum(1 for a in in_band
                            if any(r["addr"] == a for r in rows))))

    # --- the column-name trap ---
    # The whole difference between a second signal and a constant zero.
    right = xdata_weights("functions")
    wrong = xdata_weights("functions_touched")
    check("the XDATA weight is read from `functions`",
          len(wrong) == 0 and len(right) > 0,
          "functions=%d, functions_touched=%d" % (len(right), len(wrong)))
    check("109 pool rows have a non-zero XDATA read+write weight, 191 tokens "
          "over all of them",
          sum(1 for r in rows if r["xdata_weight"] > 0) == 109
          and sum(r["xdata_weight"] for r in rows) == 191,
          "got %d rows, %d tokens"
          % (sum(1 for r in rows if r["xdata_weight"] > 0),
             sum(r["xdata_weight"] for r in rows)))
    check("the heaviest pool row is 0x0D4A at six read+write registers",
          max(rows, key=lambda r: (r["xdata_weight"], r["addr"]))["addr"] == "0D4A"
          and by_addr["0D4A"]["xdata_weight"] == 6,
          "got %s at %d" % (max(rows, key=lambda r: (r["xdata_weight"],
                                                     r["addr"]))["addr"],
                            max(r["xdata_weight"] for r in rows)))
    check("the weight is 0x1059's, read from the CSV's own `functions` cell",
          by_addr["1059"]["xdata_weight"] == right["1059"] > 0,
          "weight %d, CSV %d" % (by_addr["1059"]["xdata_weight"],
                                 right.get("1059", 0)))

    # --- the vector walk ---
    roots = vector_roots()
    check("the vector walk finds the 12 targets subsystems.md §3 names",
          len(roots) == 12 and roots == ["0070", "052F", "0530", "0556", "05B6",
                                         "05E6", "05E7", "1150", "1156", "115C",
                                         "1162", "1168"],
          "got %d: %s" % (len(roots), ", ".join(roots)))
    reached = [r for r in rows if r["vector_reachable"]]
    reached_all = {a for scope, a in vector_reachable(index)
                   if scope == "common"} & set(unannotated)
    check("13 unannotated common rows were forward-reachable from the roots "
          "when the tranche was cut; 3 of them are unannotated still",
          len(reached_all) == 3 and not reached,
          "got %d over the %d and %d in the pool"
          % (len(reached_all), len(unannotated), len(reached)))
    check("all 10 of the tranche's reachability arm are annotated now",
          committed_reachable_tranche(roots) == [],
          "unannotated: " + ", ".join(committed_reachable_tranche(roots)))

    # --- the ranking is total, and reproducible ---
    check("the ranking is sorted by inbound desc, xdata desc, addr asc",
          all((-a["inbound"], -a["xdata_weight"], a["addr"])
              <= (-b["inbound"], -b["xdata_weight"], b["addr"])
              for a, b in zip(rows, rows[1:])))
    check("no two pool rows tie on all three keys",
          len({(r["inbound"], r["xdata_weight"], r["addr"]) for r in rows})
          == len(rows))
    check("rebuilding gives byte-identical rows", build(index) == rows)

    # --- a pool row cannot vanish without the count moving ---
    # The refusal that matters most for the file this commits: dropping a row
    # from the pool must be visible as a moved count rather than as a shorter
    # ranking that still looks sorted.
    check("refusal: a pool row missing from the ranking moves the count",
          len(rows) - 1 == 416
          and [r["rank"] for r in rows[1:]] == list(range(2, 418)))

    # --- the committed CSV, which is the tranche's record and not this run ---
    landed = committed_tranche()
    want = ["355E", "2F1D", "0C86", "3ACC", "3239", "30B5", "3BAE", "220A",
            "43A5", "4AFB", "0937", "2E9C", "09A2", "3983", "3AD1", "3B32",
            "2B6C", "21DC", "221F", "0A74", "3835", "3B20", "3BDD", "4368",
            "436F", "4A42", "5A55", "07E7", "07D0", "07B6", "0E72", "07D6",
            "05E7", "07C1", "0E5E", "0E7D", "1048"]
    check("the committed ranking names those 37 as its tranche, in rank order",
          [a for a, _r in landed] == want,
          "got %d: %s" % (len(landed), ", ".join(a for a, _r in landed)))
    check("the committed ranking holds 455 rows, the pool it was cut from",
          len(read_csv(RANKING_CSV)) == 455
          and committed_ranking_problems() == [],
          "%d row(s); %s" % (len(read_csv(RANKING_CSV)),
                             "; ".join(committed_ranking_problems())))
    check("all 37 of them carry an annotation row, so the tranche landed",
          all(("common", a) in annotated for a, _r in landed),
          "unannotated: " + ", ".join(a for a, _r in landed
                                      if ("common", a) not in annotated))
    # The 418 below the cut are the rest of the pool -- less one row, and the
    # one is the thunk the exporter renamed after its target. 37 rows moved 38
    # index rows, and this is where the 38th is pinned. The test is against
    # `index.csv`'s own `annotated` column, which is what the pool is defined
    # from, and not against the annotation CSV: `0x10FA` has no CSV row of its
    # own, which is the whole of what makes it the 26th "named without a CSV
    # row" in ec/annotations/subsystems.md §2.
    rest = [r for r in read_csv(RANKING_CSV) if r["in_tranche"] == "no"]
    unannotated = set(common_unannotated())
    still = {norm_addr(r["addr"]) for r in rest
             if norm_addr(r["addr"]) in unannotated}
    check("the 418 rows the tranche did not take are the pool, less 0x10FA -- "
          "the bare `ljmp 0x0A74` thunk the exporter renamed after its target, "
          "which has no CSV row of its own",
          len(rest) == 418 and still == {r["addr"] for r in rows}
          and "10FA" not in still and "10FA" not in {r["addr"] for r in rows}
          and ("common", "10FA") not in annotated,
          "%d row(s), %d still unannotated, 0x10FA unannotated=%s in pool=%s "
          "has a CSV row=%s"
          % (len(rest), len(still), "10FA" in unannotated,
             "10FA" in {r["addr"] for r in rows},
             ("common", "10FA") in annotated))
    check("the tranche's 28 short rows and nine large ones, and its 999 bytes",
          committed_sizes() == (999, 28, ["0C86", "43A5", "2E9C", "2F1D",
                                          "2B6C", "30B5", "09A2", "0937",
                                          "07D6"]),
          "got %s" % (committed_sizes(),))

    # --- the cut, which is now exhausted ---
    check("the cut selects nothing today: every row that qualified is annotated",
          not tranche, "got %d: %s" % (len(tranche),
                                       ", ".join(r["addr"] for r in tranche)))
    check("and the remainder starts at inbound 3, so the next cut moves down",
          rows and max(r["inbound"] for r in rows) == INBOUND_CUT - 1,
          "max inbound %d" % (max(r["inbound"] for r in rows) if rows else 0))
    check("refusal: the committed ranking is not regenerated from the live pool",
          committed_tranche() != [] and len(committed_tranche()) == 37
          and not any(a == r["addr"] for a, _r in committed_tranche()
                      for r in rows),
          "the tranche and the live pool overlap, which would mean the file was "
          "overwritten with a fresh run")

    # --- the three limits, as counts the census can print ---
    not_placed = [r for r in rows if r["inbound"] == 0]
    check("291 of the common unannotated rows are not placed by the call "
          "graph's transfer walk, and 153 of the pool",
          len([a for a in unannotated if inbounds.get(a, 0) == 0]) == 291
          and len(not_placed) == 153,
          "got %d of %d and %d of the pool"
          % (len([a for a in unannotated if inbounds.get(a, 0) == 0]),
             len(unannotated), len(not_placed)))
    check("none of those has a call-graph row carrying a zero count",
          not [r for r in not_placed if r["addr"] in inbounds],
          "got " + ", ".join(r["addr"] for r in not_placed
                             if r["addr"] in inbounds))

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the hand "
              "transcriptions above")
        return 1
    print("self-test passed: 618 unannotated, 201 in #574's block, a 417-row "
          "pool, the `functions`-not-`functions_touched` weight, the 12 vector "
          "roots, the committed 455-row ranking with its 37 annotated and 418 "
          "remaining, the exhausted cut, and the three refusals")
    return 0


def committed_ranking_problems():
    """Every disagreement between the committed ranking and its own columns.

    A **self-consistency** check on the committed file, not a comparison against
    a fresh build: the file is the tranche's record and the tranche is annotated,
    so a live pool no longer contains it and diffing against one would report
    all 38 differences as faults. What is checked is the arithmetic a reader
    relies on -- the file sorts by the three keys, the ranks are 1..N with no
    gap, every `in_tranche` cell agrees with the `inbound`/`vector_reachable`
    cells beside it under the cut, and the `in_tranche` set is exactly the set
    the cut selects over the file's own signals. A hand-edited cell that broke
    the ordering would fail here; a tranche row that landed without being
    recorded would fail in the self-test, which compares the set to the
    annotation CSV.
    """
    if not os.path.isfile(RANKING_CSV):
        return ["%s is missing; the ordering the next tranche inherits is a "
                "committed file, not a re-derivation" % RANKING_CSV]
    rows = read_csv(RANKING_CSV)
    out = []
    if [int(r["rank"]) for r in rows] != list(range(1, len(rows) + 1)):
        out.append("the `rank` column is not 1..%d with no gap" % len(rows))
    keyed = [(-int(r["inbound"]), -int(r["xdata_weight"]), r["addr"])
             for r in rows]
    if keyed != sorted(keyed):
        out.append("the rows are not in the stated order: inbound desc, "
                   "xdata_weight desc, addr asc")
    for row in rows:
        want = "yes" if (int(row["inbound"]) >= INBOUND_CUT
                         or row["vector_reachable"] == "yes") else "no"
        if row["in_tranche"] != want:
            out.append("common 0x%s has in_tranche=%r and its own inbound=%s / "
                       "vector_reachable=%r say %r"
                       % (row["addr"], row["in_tranche"], row["inbound"],
                          row["vector_reachable"], want))
    if len({r["addr"] for r in rows}) != len(rows):
        out.append("the file repeats an address")
    return out


def committed_reachable_tranche(roots):
    """The tranche rows that were in the pool only by the reachability arm.

    Those are the ten `vector_reachable=yes` rows with `inbound` below the cut,
    and the assertion that matters is that **all ten are annotated** -- they
    were the arm no inbound count would have selected, so a tranche that missed
    them would look complete on the inbound column alone.
    """
    annotated = annotated_keys()
    return [norm_addr(r["addr"]) for r in read_csv(RANKING_CSV)
            if r["in_tranche"] == "yes"
            and r["vector_reachable"] == "yes"
            and int(r["inbound"]) < INBOUND_CUT
            and ("common", norm_addr(r["addr"])) not in annotated]


def committed_sizes():
    """(bytes, short rows, the rows over 16 bytes) for the committed tranche.

    Read off `index.csv` by address rather than carried, so a listing that grew
    fails the pin instead of being reported from a stale note. 28 of the 37 are
    16 bytes or fewer; the nine that are not are the five large ones plus
    `0x30B5`, `0x09A2`, `0x0937` and `0x07D6`.
    """
    sizes = common_sizes()
    tranche = [norm_addr(r["addr"]) for r in read_csv(RANKING_CSV)
               if r["in_tranche"] == "yes"]
    big = sorted((a for a in tranche if sizes[a] > 16), key=lambda a: -sizes[a])
    return (sum(sizes[a] for a in tranche), len(tranche) - len(big), big)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit-csv", action="store_true",
                    help="write the live ranking to stdout in the committed "
                         "file's column order; the committed file is that "
                         "tranche's record and is not regenerated by it")
    ap.add_argument("--self-test", action="store_true",
                    help="check the live ordering and the committed ranking "
                         "against the hand-transcribed answers, and the "
                         "refusals")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rows = build()
    if args.emit_csv:
        emit_csv(rows)
        return 0
    text, _rows = report(rows)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
