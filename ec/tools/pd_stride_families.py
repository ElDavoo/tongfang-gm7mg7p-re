#!/usr/bin/env python3
"""Read the `0x17`, `0x67` and `0x04` stride families site by site, over the
whole PD image.

`../annotations/pd-index-geometry.md` 7.5 lists these three as strides nothing
in this repository has looked at, and `../annotations/pd-base-strides.csv`
carries their site and base counts and nothing more. They are three different
shapes of arithmetic wearing one row of a census, and the aggregate hides that:

  * `0x17` is reached only through a helper, and the helper's arithmetic is
    `mul ab ; add a,#lo ; mov dpl,a ; clr a ; addc a,#hi` -- B discarded, so
    the construction is `low8(index * 0x17)` and not a product. Twelve of its
    sites sit inside `ec/decompiled/pd/*.asm` listings and five do not, so
    "is this code" is a per-site question here rather than a family-wide one.
  * `0x67` and `0x04` reach DPTR through helper `0x10BC`, whose body is
    `mul ab ; add a,dpl ; mov dpl,a ; mov a,b ; addc a,dph` -- B retained, so
    those are full 16-bit products. Every `0x67` chain then stops on
    `add a,dph` after a `mov a,rN`, a *second* index term the term model does
    not cover and this tool does not fold into the address. The two `0x04`
    chains stop earlier, on the `0x104D` dispatch.
  * The two shapes are entered differently, which is why their two denominators
    do not meet. The `0x17` sites are `MOV DPTR` anchors whose chains reach an
    immediate-base template, and `../annotations/pd-index-accesses.csv` files
    that template as the construction; the `0x67`/`0x04` sites reach `0x10BC`
    and build no immediate base at all, so that census has no row for them
    anywhere. Reconciling the two is most of what is here.

Two classifications, on separate columns because they are separate questions
with separate denominators, which is §8.3 of the geometry file's own rule:

  * `framing` -- whether a backward linear walk in the 24-byte window lands
    exactly on the site (`supported-code-site`) or none does
    (`instruction-framing-candidate`). A zero from `converges_from()` is
    evidence about instruction boundaries and never about data: it is the
    measurement §8.3 calls framing evidence and not likelihood of execution,
    and a site preceded by a dispatch table has no converging anchor and is
    not thereby misframed. Two `0x17` sites are in this class, and for both
    the `MOV DPTR` byte sits inside an `lcall` a byte earlier -- so the
    immediate that byte-scan decodes is not an address this code loads.
    `effective_base` and `arithmetic` are unaffected, because the term the
    chain resolves comes from the template the chain reaches and not from the
    site's own immediate. `pd-stride-families.md` 3.4 has the listing.
  * `in_pd_listing` -- whether `ec/decompiled/pd/*.asm` holds the site
    (`inside a committed pd listing`, with the function that does in the next
    column) or `pd_image_census.NOT_FOUND` where none does. That is a real
    answer and not a gap: the export covers a set of functions, not 64 KiB.

What this cannot do, stated once so no output below has to repeat it:

  * It establishes no record count, no record width and no record content. A
    stride constant is a multiply factor in an address expression, and §7.4's
    correction (PR #74) is the standing precedent that `low8(index * constant)`
    is not an unconditional record width. `--families` prints the first index
    at which the two forms diverge, because that figure is the claim and
    quoting it from memory is how it goes stale.
  * The bases are addresses in the PD program's own data space. Nothing here
    makes them host-visible EC registers, and `../annotations/registers.yaml`
    is not touched: static evidence cannot re-grade a register.
  * Nothing here observes hardware. No register is read, written or read back,
    and the index registers' values at run time are not knowable from these
    bytes. No site in these three families is bounded by the analysis:
    `pd-stride-families.md` 3.2 refutes the one bound that looked available,
    because the helper reloads A before the multiply.
  * It is not a call graph. An unaligned `MOV DPTR` byte scan finds data-table
    bytes as readily as opcodes, and a consumer reached through a computed jump
    carries no target bytes at all. An unestablished consumer is reported as
    `not found by this method`, never as absent.

Read-only: it opens the firmware image for reading and writes nothing. Every
walk is bounded by both a count and `min(pd-image end, len(image))`, the
invariant `../../docs/findings/count-bounded-walk-invariant.md` records.

Usage:
    python3 pd_stride_families.py ../firmware/GMxMGxx_11.800
    python3 pd_stride_families.py ../firmware/GMxMGxx_11.800 --families
    python3 pd_stride_families.py ../firmware/GMxMGxx_11.800 \
            --sites 0x8077 0x9C15 0xA399
    python3 pd_stride_families.py ../firmware/GMxMGxx_11.800 --csv
    python3 pd_stride_families.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import io
import os
import re
import sys
from contextlib import redirect_stdout

# pd_index_geometry imports disasm8051, check_image_map and trace_xdata_refs by
# bare module name, so this file's own directory has to be on the path before
# any of them is loaded -- not after, and not only when this file is the one
# being run. The same two lines test_check_site_census.py carries, for the same
# reason.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pd_index_geometry import (  # noqa: E402
    DEFAULT_FIRMWARE, MOVX_A_DPTR, MOVX_DPTR_A, MOV_DPTR, OPCODE_LEN, SITE_WINDOW,
    STRIDE_RE, WHOLE_IMAGE, base_sites, branch_target, check_site_addr,
    effective_base, effective_terms, fmt_address, immediate_templates,
    is_call, is_jmp, pd_bounds, pd_verified, rebased, walk_helper, CLR_A,
    MOV_A_IMM, MUL_AB,
)
import pd_image_census  # noqa: E402
from disasm8051 import decode  # noqa: E402

# The three constants 7.5 names as unexplored, in the term model's own `×0xNN`
# spelling rather than the census CSV's, so a term string and a census row
# compare without a second spelling in between.
FAMILIES = ("17", "67", "04")

# The classification vocabularies, as constants for the reason §8.3 gives: these
# are machine-readable cells a document quotes by string, so they are defined
# once here and --self-test asserts them against the committed CSV. Each value
# says no more than the measurement behind it -- a convergence count, a listing
# membership -- and neither is a claim about execution.
FRAMING_ANCHORED = "supported-code-site"
FRAMING_CANDIDATE = "instruction-framing-candidate"
IN_LISTING = "inside a committed pd listing"

# How a stop address was found. `chain_stop` carries pd_index_geometry.py's own
# reason string unchanged, so the vocabulary of stops is that module's and is not
# restated here; these three name only the step that turned a reason into an
# address, which is this tool's own work and which a reader needs in order to
# know whether the address was quoted or derived.
STOP_AT_MOVX = "first-movx-in-the-chain"
STOP_AT_HANDOFF = "branch-to-the-helper-the-reason-names"
STOP_AT_NAMED = "the-address-the-reason-names"

# Which of the two documented arithmetic forms built the stride term, and so
# whether the multiplication's high byte survives it. Both labels are earned
# from bytes rather than read off a term string: --self-test checks the `clr a`
# inside the template and the `mov a,b` inside the helper before trusting
# either, because a label invented from a term string would agree with itself
# forever.
ARITH_TRUNCATED = "low8-truncated"
ARITH_FULL = "full-product"

# The helper that retains the high byte, and the two instruction sequences the
# two labels rest on. The helper is named rather than searched for, so a sixth
# arithmetic idiom cannot quietly join the full-product class.
FULL_PRODUCT_HELPER = 0x10BC
FULL_PRODUCT_BODY = "a42582f582e5f03583f58322"
CLEAR_A = bytes((0xE4,))                  # clr a -- drops B before the high add
MOV_A_B = bytes((0xE5, 0xF0))             # mov a,b -- carries B into the high add
# One `0x17` template, transcribed from the r2 listing in
# ../annotations/pd-stride-families.md 3.1 and read back out of the image below.
TRUNCATED_TEMPLATE_AT = 0xCC62
TRUNCATED_BODY = "a42429f582e4340af583"

# `add a,dph` is not one of the five term templates, so every `0x67` chain ends
# on it. The register it adds is the second index term the issue asks about, and
# it is readable off the one instruction before -- a fact about two bytes, not a
# continuation of the address expression the chain never completed.
ADD_A_DPH = bytes((0x25, 0x83))

# The factor a stride term multiplies, read out of the term itself. It has to
# reach inside `low8(...)` as well as stand alone, which is why the pattern is
# anchored on the multiply rather than on the term.
FACTOR_RE = re.compile(r"([A-Za-z0-9_]+)×0x[0-9A-F]+")

# The two ways an index can reach a construction, as tokens. `index_factor` is
# what the *term string* says and `index_source` is what the *bytes* say, and
# they are separate columns because they disagree: `chain_from()` substitutes
# the caller's frame A into a helper's `{a}` placeholder, and for a helper that
# reloads A itself that substitution names a value the multiply never sees.
# Reading the difference off the helper's own instructions is the point -- see
# index_source() and ../annotations/pd-stride-families.md 3.2.
SOURCE_XDATA = "XDATA byte read by the helper"
SOURCE_CALLER = "caller-supplied A, unresolved"
SOURCE_REGISTER = "caller-supplied register"

NOT_FOUND = pd_image_census.NOT_FOUND

SITES_CSV = "../annotations/pd-stride-family-sites.csv"
STRIDES_CSV = "../annotations/pd-base-strides.csv"
ACCESSES_CSV = "../annotations/pd-index-accesses.csv"

FIELDS = (
    "stride", "site_runtime", "site_file", "mov_dptr_immediate", "effective_base",
    "base_source", "index_terms", "destination", "arithmetic", "index_factor",
    "index_source",
    "frame_onto", "frame_over", "framing", "in_pd_listing", "owning_function",
    "helpers", "construction_runtime", "construction_file", "chain_stop",
    "stop_source", "stop_runtime", "stop_file", "unmodelled_dph_term",
    "chain_consumer_runtime", "chain_consumer_file", "chain_direction",
    "access_row_kinds", "access_statuses", "access_consumers",
)

# One row per `MOV DPTR` site, and that site is the counting unit. The access
# census reaches one construction through as many caller contexts as the
# firmware has, and copying each of them onto every site that reaches it would
# repeat the site's own columns a dozen times to add one cell. So the
# `access_*` columns carry the distinct row kinds, statuses and consumers, and
# `construction_runtime` is the join key back into
# `../annotations/pd-index-accesses.csv` for the individual rows. Nothing is
# lost: a set of statuses and a set of consumers determine which rows those are,
# and the document names the command that re-derives them.


def _rt(i):
    return f"0x{i:04X}"


def _file(i):
    return f"0x{i:05X}"


def _csv_rows(path):
    with open(os.path.join(os.path.dirname(__file__), path), newline="") as fh:
        return list(csv.DictReader(fh))


def family_terms(row):
    """The stride constants one site's effective terms carry.

    `effective_terms()` and not the raw list, because a rebasing chain discards
    the terms before it: a `0x17` site's `MOV DPTR,#0x07D1` is the index it
    reads, not part of the address it builds, and reading the raw list would
    file the site under an arithmetic its chain never applies.
    """
    return sorted(set(STRIDE_RE.findall(" ".join(effective_terms(row["terms"])))))


def index_factor(row):
    """What each of this site's stride terms is multiplied by, in header order.

    The whole factor, not only the R0-R7 names in it: `pd_index_geometry`'s
    `index_registers()` deliberately drops `A` and `B` because the site's own
    frame reloads both, and that is the right rule for intersecting a frame's
    literals with the index -- but it is the wrong cell to report here, where
    the question is what the arithmetic multiplies. A term can index on a
    register, on the caller-supplied accumulator, or on a literal the frame put
    there, and all three are index sources this tool can read off the bytes.
    """
    terms = [t for t in effective_terms(row["terms"]) if STRIDE_RE.search(t)]
    factors = [m.group(1) for t in terms
               for m in FACTOR_RE.finditer(t)]
    return " ".join(dict.fromkeys(factors)) or NOT_FOUND


def index_source(d, row):
    """What is actually in A at the multiply this chain performs.

    The term string is not enough, and reading it is how a wrong bound nearly
    got committed to ../annotations/pd-stride-families.md. `chain_from()` hands
    the helper's `{a}` placeholder the *caller's* frame A, which is right for a
    helper that multiplies what it is given and wrong for one that reloads A
    first: every `0x17` helper opens with `movx a,@dptr`, so the accumulator the
    multiply consumes is the byte that load returned and the caller's A never
    reaches it. So this walks each helper's own instructions to its `mul ab` and
    reports the last write to A before it.

    The distinction is the whole point of the column, because the two answers
    support different claims. A register the helper copies out of the bank is a
    value these bytes pin; `A` is not a value at all; and the XDATA byte is a
    value read at run time from an address this decode does not follow. Keyed on
    the multiply rather than on the construction address so it also answers for
    `0x67` and `0x04`, which build no immediate base to key on.
    """
    lo, _ = pd_bounds()
    found = []
    # A site whose stride term is built in its own instruction stream rather than
    # in a helper is walked from the instruction after its `MOV DPTR`, which is
    # where chain_from() started -- but only when that `MOV DPTR` is an
    # instruction at all. At the two framing candidates it is an `lcall`
    # operand, so the walk would begin mid-instruction and the answer would be a
    # statement about a boundary that does not exist. NOT_FOUND is the honest
    # cell there; ../annotations/pd-stride-families.md 3.4 has the listing.
    if not row["helpers"] and not row["frame_onto"]:
        return NOT_FOUND
    runs = [walk_helper(d, entry)[1] for entry in row["helpers"]]
    if not runs:
        runs = [[(off, raw) for off, raw, _t
                 in decode(d, row["file_offset"] + OPCODE_LEN[MOV_DPTR],
                           SITE_WINDOW, addr=row["runtime"] + OPCODE_LEN[MOV_DPTR])]]
    for listing in runs:
        source = SOURCE_CALLER
        for off, raw in listing:
            op = raw[0]
            if op == MUL_AB:
                found.append(source)
                break
            if op == MOVX_A_DPTR:
                source = SOURCE_XDATA
            elif 0xE8 <= op <= 0xEF:
                source = f"{SOURCE_REGISTER} R{op - 0xE8}"
            elif op == MOV_A_IMM:
                source = f"literal 0x{raw[1]:02X} in the helper"
            elif op == CLR_A:
                source = "literal 0x00 in the helper"
    return "; ".join(dict.fromkeys(found)) or NOT_FOUND


def construction_at(d, row):
    """The runtime address of the immediate-base template the chain's stride term
    was built by, or [] when the chain built none.

    The first match in walk order, not every match in the window.
    `immediate_templates()` keeps overlapping runs on purpose -- §8.3 retains
    independently entered add-only suffixes as their own constructions -- and
    the add-only suffix of a `mul ab` template begins one byte into it. This
    chain entered at the full template and consumed the whole run, so the
    suffix is not where its term came from; the suffix is filed separately and
    `../annotations/pd-stride-families.md` 3.5 says where.

    A `0x67`/`0x04` chain hands DPTR to `0x10BC` and stops: there is no
    immediate base anywhere in it, which is why `pd-index-accesses.csv` -- whose
    seeds are immediate-base templates and direct handoffs into one -- has no
    row for those sites. An empty list here is that reconciliation, not a gap.
    """
    lo, _ = pd_bounds()
    base = f"0x{effective_base(row):04X}"
    templates = immediate_templates(d)

    def first_match(offsets):
        return next((off for off in offsets
                     if off in templates and base in templates[off][1]), None)

    hits = set()
    for entry in row["helpers"]:
        off = first_match(o for o, _raw in walk_helper(d, entry)[1])
        if off is not None:
            hits.add(off - lo)
    start = row["file_offset"] + OPCODE_LEN[MOV_DPTR]
    off = first_match(o for o, _raw, _t
                      in decode(d, start, SITE_WINDOW, addr=start - lo))
    if off is not None:
        hits.add(off - lo)
    return sorted(hits)


def stop_point(d, row):
    """(the address the bounded walk stopped at, how it was found).

    `chain_from()` reports its stop as prose, and the prose names an address in
    one of the three shapes it produces here. Where it names one, the address is
    read back out of the reason rather than re-derived, so the two cannot drift
    apart. Where it does not -- the `movx` stop names the instruction and not
    where it is -- the address comes from the same forward decode `chain_from()`
    walked. A shape this function does not recognise yields None, which the
    caller writes as NOT_FOUND and --self-test fails on.
    """
    lo, _ = pd_bounds()
    reason = row["stopped"]
    start = row["file_offset"] + OPCODE_LEN[MOV_DPTR]
    steps = list(decode(d, start, SITE_WINDOW, addr=start - lo))
    named = re.match(r"^0x([0-9A-F]{4}) is unmodelled", reason)
    if named:
        # The reason names the helper whose body stopped the walk, not the
        # instruction in this site that hands DPTR to it. That instruction is
        # the site-level stop, so it is found by target.
        target = int(named.group(1), 16)
        for off, raw, _text in steps:
            if (is_call(raw[0]) or is_jmp(raw[0])) \
                    and branch_target(raw, off - lo) == target:
                return off - lo, STOP_AT_HANDOFF
        return None, STOP_AT_HANDOFF
    if reason.startswith("movx:"):
        for off, raw, _text in steps:
            if raw[0] in (MOVX_A_DPTR, MOVX_DPTR_A):
                return off - lo, STOP_AT_MOVX
        return None, STOP_AT_MOVX
    found = re.findall(r"0x([0-9A-F]{4})", reason)
    if len(found) == 1:
        return int(found[0], 16), STOP_AT_NAMED
    return None, STOP_AT_NAMED


def unmodelled_dph_term(d, runtime):
    """The register `add a,dph` adds at `runtime`, or NOT_FOUND.

    Read from the instruction at the stop and the one before it. The chain
    stopped precisely because that instruction is outside the term model, and
    folding the register into the address anyway would be the overclaim §7.4's
    correction was made about.
    """
    if runtime is None:
        return NOT_FOUND
    lo, _ = pd_bounds()
    off = lo + runtime
    if off - 1 < lo or d[off:off + 2] != ADD_A_DPH:
        return NOT_FOUND
    op = d[off - 1]
    return f"R{op - 0xE8}" if 0xE8 <= op <= 0xEF else NOT_FOUND


def arithmetic(row):
    """Which of the two documented forms built this site's stride term.

    Read from the entry that built it: a rebasing template clears A before the
    high-byte add and so drops B, while `0x10BC` moves B into A first and keeps
    it. --self-test reads both instruction sequences out of the image before
    either label is used.
    """
    if FULL_PRODUCT_HELPER in row["helpers"] and not rebased(row["terms"]):
        return ARITH_FULL
    return ARITH_TRUNCATED


def site_rows(d, owners, names):
    """One dict per `MOV DPTR` site in the three families.

    `base_sites()` is called once over the whole image and filtered here rather
    than rescanned per family, so the three families share one denominator --
    which is what lets the committed census be cross-checked against this run
    instead of restated, and what keeps a site resolving two of the three
    constants a single row carrying both.
    """
    lo, _ = pd_bounds()
    out = []
    for row in base_sites(d, WHOLE_IMAGE):
        strides = [s for s in family_terms(row) if s in FAMILIES]
        if not strides:
            continue
        entry, name, missing = pd_image_census.owning_function(
            row["runtime"], owners, names)
        stop, how = stop_point(d, row)
        # A chain that ends on a `movx` *is* its own first supported consumer:
        # the access dereferences the pointer the chain built. One that ends on
        # a handoff has none, and NOT_FOUND says this method did not establish
        # one rather than that none exists.
        consumer = stop if how == STOP_AT_MOVX else None
        out.append({
            "row": row, "strides": strides,
            "framing": (FRAMING_ANCHORED if row["frame_onto"]
                        else FRAMING_CANDIDATE),
            "in_listing": IN_LISTING if entry is not None else missing,
            "owning_function": name or NOT_FOUND,
            "constructions": construction_at(d, row),
            "arithmetic": arithmetic(row),
            "index_factor": index_factor(row),
            "index_source": index_source(d, row),
            "stop": stop, "stop_how": how,
            "dph_term": unmodelled_dph_term(d, stop),
            "consumer": consumer,
            "direction": (None if consumer is None else
                          "read" if d[lo + consumer] == MOVX_A_DPTR else "write"),
        })
    return out


def access_index():
    """{construction runtime: [row, ...]} over pd-index-accesses.csv, in file
    order.

    Read from the committed CSV rather than recomputed. The two walkers are
    independent -- `access_walk()` never calls `chain_from()` -- so a row
    appearing here that this tool did not predict is evidence, and a row
    disagreeing with the chain is a drift to fail on rather than to reconcile
    quietly. Keyed on the construction address because that is the only place
    the two censuses meet: §8's rows are files, not `MOV DPTR` anchors.
    """
    out = {}
    for r in _csv_rows(ACCESSES_CSV):
        out.setdefault(r["construction_runtime"], []).append(r)
    return out


def access_summary(constructions, access):
    """(row kinds, statuses, consumers) at this site's constructions.

    `NOT_FOUND` in all three when §8 has no row there, which is what makes
    "this census has nothing here" a value in the artifact instead of a missing
    line. A consumer is written with its direction, and a §8 row that reached no
    MOVX at all is written `-`, so a construction-only row is distinguishable
    from a row whose consumer column happens to be empty.
    """
    rows = [r for c in constructions for r in access.get(_rt(c), ())]
    if not rows:
        return NOT_FOUND, NOT_FOUND, NOT_FOUND
    kinds = " ".join(sorted({r["row_kind"] for r in rows}))
    statuses = " ".join(sorted({r["status"] for r in rows}))
    consumers = " ".join(sorted({
        f"{r['consumer_runtime'] or '-'} {r['direction'] or '-'}".strip()
        for r in rows}))
    return kinds, statuses, consumers


def site_table(sites, access):
    """The committed per-site table, one row per site, sorted the way §8.3
    requires: lexicographically by every field in header order, uppercase hex."""
    lo, _ = pd_bounds()
    rows = []
    for s in sites:
        row = s["row"]
        stop, consumer = s["stop"], s["consumer"]
        kinds, statuses, consumers = access_summary(s["constructions"], access)
        rows.append({
            "stride": " ".join(f"0x{x}" for x in s["strides"]),
            "site_runtime": _rt(row["runtime"]),
            "site_file": _file(row["file_offset"]),
            "mov_dptr_immediate": f"0x{row['base']:04X}",
            "effective_base": f"0x{effective_base(row):04X}",
            "base_source": "rebased" if rebased(row["terms"]) else "site-immediate",
            "index_terms": fmt_address(row["terms"], row["base"]),
            "destination": "DPTR",
            "arithmetic": s["arithmetic"],
            "index_factor": s["index_factor"],
            "index_source": s["index_source"],
            "frame_onto": str(row["frame_onto"]),
            "frame_over": str(row["frame_over"]),
            "framing": s["framing"],
            "in_pd_listing": s["in_listing"],
            "owning_function": s["owning_function"],
            "helpers": " ".join(_rt(h) for h in row["helpers"]) or NOT_FOUND,
            "construction_runtime": " ".join(_rt(c) for c in s["constructions"])
            or NOT_FOUND,
            "construction_file": " ".join(_file(lo + c) for c in s["constructions"])
            or NOT_FOUND,
            "chain_stop": row["stopped"],
            "stop_source": s["stop_how"],
            "stop_runtime": _rt(stop) if stop is not None else NOT_FOUND,
            "stop_file": _file(lo + stop) if stop is not None else NOT_FOUND,
            "unmodelled_dph_term": s["dph_term"],
            "chain_consumer_runtime": _rt(consumer) if consumer is not None
            else NOT_FOUND,
            "chain_consumer_file": _file(lo + consumer) if consumer is not None
            else NOT_FOUND,
            "chain_direction": s["direction"] or NOT_FOUND,
            "access_row_kinds": kinds,
            "access_statuses": statuses,
            "access_consumers": consumers,
        })
    return sorted(rows, key=lambda r: tuple(str(r[k]) for k in FIELDS))


def write_csv(rows):
    writer = csv.DictWriter(sys.stdout, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)


def first_wrapping_index(stride, arith):
    """The first index at which `index * stride` no longer fits in the low byte,
    or None for a full-product chain, which keeps the high half.

    Computed rather than quoted, because this is the one figure a reader is
    likely to use as a bound and it moves with the constant: §7.4's correction
    is that the two forms agree only below it, and a stale index in prose is
    the overclaim all over again.
    """
    if arith == ARITH_FULL:
        return None
    n = int(stride, 16)
    return next(i for i in range(1, 0x10000) if i * n > 0xFF)


def group_of(sites, stride):
    """The sites carrying one family's constant. Factored out because the
    rollup and the self-test both need it and neither should own the filter."""
    return [s for s in sites if stride in s["strides"]]


def family_summary(sites):
    """Per-family rollup, in FAMILIES order. The counts are over the committed
    image and no change to this repository can move them; the row count of the
    committed CSV is not printed, because that one can."""
    out = {}
    for stride in FAMILIES:
        group = group_of(sites, stride)
        arith = sorted({s["arithmetic"] for s in group})
        out[stride] = {
            "sites": len(group),
            "bases": sorted({effective_base(s["row"]) for s in group}),
            "listing": sum(1 for s in group if s["in_listing"] == IN_LISTING),
            "anchored": sum(1 for s in group if s["framing"] == FRAMING_ANCHORED),
            "reached": sum(1 for s in group if s["constructions"]),
            "consumed": sum(1 for s in group if s["consumer"] is not None),
            "dph": sorted({s["dph_term"] for s in group} - {NOT_FOUND}),
            "arith": arith,
            "wraps": first_wrapping_index(stride, arith[0]) if arith else None,
            "stops": sorted({s["row"]["stopped"] for s in group}),
        }
    return out


def print_sites(d, sites, with_listing):
    lo, _ = pd_bounds()
    for s in sorted(sites, key=lambda s: (s["strides"], s["row"]["runtime"])):
        row = s["row"]
        print(" ".join(f"0x{x}" for x in s["strides"])
              + f"  site runtime {_rt(row['runtime'])} (file {_file(row['file_offset'])})")
        print(f"  MOV DPTR immediate 0x{row['base']:04X}, effective base "
              f"0x{effective_base(row):04X} "
              f"({'rebased' if rebased(row['terms']) else 'site-immediate'})")
        print(f"  {fmt_address(row['terms'], row['base'])}   [{s['arithmetic']}]")
        print(f"  index factor {s['index_factor']} (term) / "
              f"{s['index_source']} (bytes)   frame "
              f"{row['frame_onto']}/{row['frame_onto'] + row['frame_over']}   "
              f"{s['framing']}")
        print(f"  listing: {s['in_listing']}"
              + (f" -- {s['owning_function']}" if s["in_listing"] == IN_LISTING else ""))
        print(f"  chain {' '.join(_rt(h) for h in row['helpers']) or NOT_FOUND}"
              f"   construction "
              f"{' '.join(_rt(c) for c in s['constructions']) or NOT_FOUND}")
        print(f"  chain ends at {row['stopped']}")
        print(f"  stop {_rt(s['stop']) if s['stop'] is not None else NOT_FOUND} "
              f"({s['stop_how']})   unmodelled DPH addend {s['dph_term']}")
        if s["consumer"] is not None:
            print(f"  first supported consumer {_rt(s['consumer'])} "
                  f"({s['direction']})")
        else:
            print(f"  first supported consumer {NOT_FOUND}")
        if with_listing:
            print(f"  decode at {_rt(row['runtime'])}:")
            for off, raw, text in decode(d, lo + row["runtime"], SITE_WINDOW,
                                         addr=row["runtime"]):
                print(f"    {_rt(off - lo)}  {raw.hex():<8} {text}")
        print()


# --- self-test -------------------------------------------------------------
#
# Every expectation below is transcribed from
# ../annotations/pd-stride-families.md, so the tool cannot silently disagree with
# the annotation that cites it. The two arithmetic labels are not taken on trust
# from that document either: each is checked against the instruction sequence in
# the firmware that earns it, so a decode that widened would have to widen the
# bytes and the label together.

# The per-family figures the document states. Sites and bases are counts over
# the committed image; listing/anchored/reached/consumed are the two
# classifications this module's docstring keeps apart.
FAMILY_FIGURES = {
    "17": dict(sites=17, bases=7, listing=12, anchored=15, reached=17, consumed=10,
               arith=(ARITH_TRUNCATED,), wraps=12, dph=()),
    "67": dict(sites=7, bases=6, listing=1, anchored=7, reached=0, consumed=0,
               arith=(ARITH_FULL,), wraps=None, dph=("R3", "R5", "R6", "R7")),
    "04": dict(sites=2, bases=2, listing=0, anchored=2, reached=0, consumed=0,
               arith=(ARITH_FULL,), wraps=None, dph=()),
}

# Every site's effective base, keyed by family and runtime, transcribed from the
# document's per-family tables. The two `0x17` sites whose own `MOV DPTR`
# immediate is not a base at all (§3.4) are keyed here by the base the chain
# resolves, which is unaffected -- their immediates are pinned separately, by
# their bytes.
SITE_BASES = {
    ("17", 0x75CD): 0x0A35, ("17", 0x768E): 0x0A35, ("17", 0x769E): 0x0A35,
    ("17", 0x8068): 0x0A15, ("17", 0x8077): 0x0A27, ("17", 0x80B9): 0x0A27,
    ("17", 0x80E5): 0x0A13, ("17", 0x81DD): 0x0A13, ("17", 0xAED3): 0x0A2D,
    ("17", 0xAF70): 0x0A2C, ("17", 0xB39E): 0x0A35, ("17", 0xB3AE): 0x0A2D,
    ("17", 0xB3C8): 0x0A35, ("17", 0xC8F0): 0x0A13, ("17", 0xCC5B): 0x0A29,
    ("17", 0xCC95): 0x0A15, ("17", 0xD745): 0x0A2C,
    ("67", 0x2F0B): 0x07C4, ("67", 0x2F6A): 0x07A3, ("67", 0x9C15): 0x0661,
    ("67", 0x9C39): 0x0667, ("67", 0x9C46): 0x069A, ("67", 0x9C6D): 0x069B,
    ("67", 0xCF13): 0x07C4,
    ("04", 0xA399): 0x00C0, ("04", 0xA3AD): 0x00C8,
}

# Every site's address expression, as `--sites` prints it. 0x8077 is here as the
# tool emits it and not as it is: its frame puts a literal `0x00` in A and the
# term says `low8(0x00 x 0x17)`, but helper 0x96FE opens with `movx a,@dptr`
# and the multiply never sees that zero. The document's 3.2 is the correction
# and SITE_BOUND_CLAIMS below is what pins it.
SITE_TERMS = {
    0x8077: "DPTR ← 0x0A27 + low8(0x00×0x17)",
    0x8068: "DPTR ← 0x0A15 + low8(R7×0x17)",
    0x2F0B: "DPTR = 0x07C4 + A×0x67",
    0x9C6D: "DPTR = 0x069B + R5×0x67",
    0xA399: "DPTR = 0x00C0 + R7×0x04",
    0xA3AD: "DPTR = 0x00C8 + A×0x04",
}

# What actually reaches each family's multiply, per the `index_source` column.
# This is the correction the term strings need and do not carry: `chain_from()`
# substitutes the caller's frame A into a helper's `{a}` placeholder, and every
# `0x17` helper reloads A with `movx a,@dptr` before multiplying, so the
# caller's value never reaches the multiply. The two `not found by this method`
# cells are the two framing candidates of 3.4, where the walk would have to
# begin on an `lcall` operand.
INDEX_SOURCES = {
    "17": (NOT_FOUND, SOURCE_XDATA, "caller-supplied register R7"),
    "67": (SOURCE_CALLER,),
    "04": (SOURCE_CALLER,),
}

# What each family's stride terms are multiplied by. A family is not one kind of
# index: `0x17` multiplies a register, a literal the frame left in A, or the
# caller-supplied accumulator; `0x67` does the first two of those; `0x04` does
# the last two. The
# `A` row is the point -- it is why `pd_index_geometry`'s own
# `index_registers()` drops A and B, and why the index range is not knowable
# here.
INDEX_FACTORS = {"17": ("0x00", "A", "R7"), "67": ("A", "R5"),
                 "04": ("A", "R7")}

# The bound the issue's own framing suggested and the bytes refute, pinned on
# both sides so neither can be quietly reinstated: the helper that builds
# 0x8077's construction reloads A with a MOVX, so `index_source` is the XDATA
# byte and not the caller's frame literal.
BOUND_CLAIM = (0x8077, 0x96FE, "e0")

# Every stop reason, verbatim and per family, so a walk that ends somewhere new
# fails here rather than adding a line to a CSV nobody reads.
STOP_REASONS = {
    "17": {"movx: DPTR dereferenced here",
           "0x1041 is unmodelled: 0x1043 `inc  dptr` is outside the term model",
           "0x104D is unmodelled: 0x104D `mov  r0,0x82` is outside the term model",
           "0xAD1E is unmodelled: 0x0FB1 `inc  dptr` is outside the term model",
           "0xADA4 is unmodelled: 0x0FB1 `inc  dptr` is outside the term model"},
    "67": {"`add  a,0x83` at 0x2F12", "`add  a,0x83` at 0x2F71",
           "`add  a,0x83` at 0x9C1F", "`add  a,0x83` at 0x9C40",
           "`add  a,0x83` at 0x9C51", "`add  a,0x83` at 0x9C78",
           "`add  a,0x83` at 0xCF1A"},
    "04": {"0x104D is unmodelled: 0x104D `mov  r0,0x82` is outside the term model"},
}

# The two `0x17` sites whose `MOV DPTR` byte is an `lcall` operand. The value is
# the three bytes centred on the site, which decode as one `lcall` where a byte
# scan reads `mov dptr` plus two of its own -- so the check is against the bytes
# and not against the number of sites that happen to look like this.
PHANTOM_LCALL = {0xCC5B: "12 90 fc", 0xCC95: "12 90 fc"}


def self_test(fw_path: str) -> int:
    d = open(fw_path, "rb").read()
    lo, _ = pd_bounds()
    bad = 0

    def check(ok: bool, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        print(f"  {'ok ' if ok else '!  '} {text}")

    if not pd_verified(d):
        print(f"  !   no {b'ITE8850-PD'.decode()!r} marker at file 0x{0x20040:05X}")
        return 1

    # The two arithmetic labels are only as good as the instructions they name,
    # so they are read out of the image before anything is labelled with them.
    body = bytes(b for _, raw in walk_helper(d, FULL_PRODUCT_HELPER)[1]
                 for b in raw).hex()
    check(body == FULL_PRODUCT_BODY
          and MOV_A_B in d[lo + FULL_PRODUCT_HELPER:lo + FULL_PRODUCT_HELPER + 12],
          f"helper {_rt(FULL_PRODUCT_HELPER)} is `{FULL_PRODUCT_BODY}`, which "
          "moves B into A and so keeps the product's high byte")
    at = lo + TRUNCATED_TEMPLATE_AT
    truncated = d[at:at + len(TRUNCATED_BODY) // 2]
    check(truncated.hex() == TRUNCATED_BODY and CLEAR_A in truncated,
          f"the immediate-base template at {_rt(TRUNCATED_TEMPLATE_AT)} is "
          f"`{TRUNCATED_BODY}`, which clears A before the high-byte add and so "
          "drops B")

    extents = pd_image_census.function_extents()
    owners = pd_image_census.address_owners(extents)
    names = pd_image_census.function_names()
    sites = site_rows(d, owners, names)
    access = access_index()
    rows = site_table(sites, access)

    # The census this file cross-checks rather than restates. The committed CSV
    # is the figure a reader has already been given, so a drift between it and
    # this decode fails rather than being quietly reconciled.
    committed = {r["stride"]: r for r in _csv_rows(STRIDES_CSV)}
    summary = family_summary(sites)
    for stride, want in FAMILY_FIGURES.items():
        got, label = summary[stride], f"0x{stride}"
        check(got["sites"] == want["sites"] and len(got["bases"]) == want["bases"]
              and [f"0x{b:04X}" for b in got["bases"]]
              == committed[label]["base_list"].split()
              and committed[label]["sites"] == str(want["sites"]),
              f"{label}: {want['sites']} site(s) over {want['bases']} base(s), "
              f"regenerating {committed[label]['base_list']} from {STRIDES_CSV}")
        check(got["listing"] == want["listing"] and got["anchored"] == want["anchored"],
              f"{label}: {want['listing']} site(s) inside a committed pd listing, "
              f"{want['anchored']} anchored by a converging frame "
              f"(got {got['listing']}, {got['anchored']})")
        check(got["reached"] == want["reached"] and got["consumed"] == want["consumed"],
              f"{label}: {want['reached']} site(s) reach an immediate-base "
              f"construction and {want['consumed']} have a decoded first consumer "
              f"(got {got['reached']}, {got['consumed']})")
        check(tuple(got["arith"]) == want["arith"] and tuple(got["dph"]) == want["dph"],
              f"{label}: arithmetic {want['arith'][0]}, unmodelled DPH addends "
              f"{' '.join(want['dph']) or 'none'} "
              f"(got {got['arith'][0]}, {' '.join(got['dph']) or 'none'})")
        check(got["wraps"] == want["wraps"],
              f"{label}: low8 and the full product diverge from index "
              f"{want['wraps']} (got {got['wraps']})")
        # Compared as a set: the order is the CSV's sort, and pinning it would
        # make a column reordering a failure rather than the diff it is.
        sources = {s["index_source"] for s in group_of(sites, stride)}
        check(sources == set(INDEX_SOURCES[stride]),
              f"{label}: what reaches the multiply is {INDEX_SOURCES[stride]} "
              f"(got {sources})")
        check(tuple(sorted({f for s in group_of(sites, stride)
                            for f in s["index_factor"].split()}))
              == INDEX_FACTORS[stride],
              f"{label}: index factors {INDEX_FACTORS[stride]} "
              f"(got {tuple(sorted({f for s in group_of(sites, stride) for f in s['index_factor'].split()}))})")
        check(set(got["stops"]) == STOP_REASONS[stride],
              f"{label}: {len(STOP_REASONS[stride])} stop reason(s), verbatim, "
              "none new and none missing")

    for (stride, runtime), want in sorted(SITE_BASES.items()):
        s = next((s for s in sites if s["row"]["runtime"] == runtime
                  and stride in s["strides"]), None)
        check(s is not None and effective_base(s["row"]) == want,
              f"0x{stride} site {_rt(runtime)} indexes from 0x{want:04X} "
              f"(got {s and _rt(effective_base(s['row']))})")
    runtime, entry, opcode = BOUND_CLAIM
    s = next(s for s in sites if s["row"]["runtime"] == runtime)
    check(s["index_source"] == SOURCE_XDATA
          and d[lo + entry] == int(opcode, 16),
          f"site {_rt(runtime)} has no locally evidenced index bound: helper "
          f"{_rt(entry)} begins `{opcode}`, which replaces A before the "
          f"multiply, so the frame's literal never reaches it (got "
          f"{s['index_source']})")

    for runtime, want in sorted(SITE_TERMS.items()):
        s = next(s for s in sites if s["row"]["runtime"] == runtime)
        got = fmt_address(s["row"]["terms"], s["row"]["base"])
        check(got == want, f"site {_rt(runtime)} decodes to `{want}` (got `{got}`)")

    # The framing claim, checked against the bytes at each site rather than
    # against the count of sites that look like it. `converges_from()` returning
    # zero is what files a site as a candidate, and the three bytes centred on
    # the site are what make the class mean something.
    for runtime, want in sorted(PHANTOM_LCALL.items()):
        s = next(s for s in sites if s["row"]["runtime"] == runtime)
        got = d[lo + runtime - 1:lo + runtime + 2].hex(" ")
        check(s["framing"] == FRAMING_CANDIDATE and got == want
              and d[lo + runtime] == MOV_DPTR,
              f"{_rt(runtime)} is an instruction-framing candidate: the bytes "
              f"centred on its `mov dptr` are `{want}`, one `lcall` (got `{got}`)")

    # Every site is located. A stop address that could not be derived would
    # otherwise be a NOT_FOUND in `stop_runtime` that reads like a claim about
    # the firmware rather than about this tool.
    check(all(r["stop_runtime"] != NOT_FOUND for r in rows),
          "every site has a located chain stop, none left as "
          f"{NOT_FOUND}")
    check(all(r["chain_consumer_runtime"] != NOT_FOUND
              or r["stop_source"] in (STOP_AT_HANDOFF, STOP_AT_NAMED) for r in rows),
          "every site with no decoded consumer stopped on a located handoff or a "
          "named address, so a missing consumer reads as a stop reason and not "
          "as a silence")

    # The reconciliation the issue asks for. `pd-index-accesses.csv` files the
    # 0x17 constructions and has nothing for the other two families, because
    # neither reaches an immediate base. Asserted on both sides: a family that
    # started appearing there, or a 0x17 site that stopped being reached, breaks
    # one of these.
    for stride in ("67", "04"):
        got = [r for r in rows if r["stride"] == f"0x{stride}"
               and r["access_row_kinds"] != NOT_FOUND]
        check(not got, f"no 0x{stride} site is reached by {ACCESSES_CSV}, as the "
                       f"document records (got {len(got)})")
    reached = {r["site_runtime"] for r in rows
               if r["access_row_kinds"] != NOT_FOUND and r["stride"] == "0x17"}
    check(len(reached) == FAMILY_FIGURES["17"]["sites"],
          f"all {FAMILY_FIGURES['17']['sites']} 0x17 sites are reached by "
          f"{ACCESSES_CSV} (got {len(reached)})")

    # One construction reached by two sites stays one row each, because that is
    # what says how many `MOV DPTR` anchors reach the same arithmetic. Pinned on
    # the pair the document names rather than on a count, which every landing
    # site in that census moves.
    shared = sorted(r["site_runtime"] for r in rows
                    if r["construction_runtime"] == "0x9702")
    check(shared == ["0x8077", "0x80B9"],
          "the construction at 0x9702 is reached by 0x8077 and 0x80B9 and keeps "
          f"one row per site (got {shared})")

    # Both classes of both classification are reachable, so neither is vacuous,
    # and every token in the vocabulary is in use somewhere in the table.
    check(len({r["arithmetic"] for r in rows}) == 2
          and len({r["framing"] for r in rows}) == 2
          and len({r["stop_source"] for r in rows}) == 3,
          "both arithmetic labels, both framing labels and all three stop "
          "sources are reachable, so none of them is vacuous")
    for token in (FRAMING_ANCHORED, FRAMING_CANDIDATE, ARITH_TRUNCATED,
                  ARITH_FULL, IN_LISTING, NOT_FOUND):
        check(token in {r["framing"] for r in rows} | {r["arithmetic"] for r in rows}
              | {r["in_pd_listing"] for r in rows} | {r["owning_function"] for r in rows}
              | {r["helpers"] for r in rows} | {r["stop_runtime"] for r in rows}
              | {r["construction_runtime"] for r in rows}
              | {r["access_row_kinds"] for r in rows},
              f"the vocabulary token `{token}` is in use")

    # The committed CSV, byte for byte. Length is compared before the rows are
    # zipped: a truncated file would otherwise align its own first N rows
    # against this run's first N rows and pass.
    output = io.StringIO(newline="")
    with redirect_stdout(output):
        write_csv(rows)
    text = output.getvalue()
    try:
        with open(os.path.join(os.path.dirname(__file__), SITES_CSV), "rb") as fh:
            expected = fh.read().decode()
    except FileNotFoundError:
        expected = None
    if expected is None:
        check(False, f"{SITES_CSV} is missing; regenerate it with --csv")
    else:
        check(len(list(csv.DictReader(io.StringIO(expected, newline="")))) == len(rows)
              and text == expected,
              f"{SITES_CSV} regenerates byte-identically from the committed "
              f"firmware ({len(rows)} row(s) over "
              f"{len({r['site_runtime'] for r in rows})} site(s))")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with "
              f"pd-stride-families.md or the committed CSVs")
    else:
        print("self-test passed: the three families' sites, bases, address "
              "expressions, arithmetic and framing classes, stop reasons and "
              f"access joins match pd-stride-families.md, and {SITES_CSV} "
              f"regenerates unchanged (PD image at file 0x{lo:05X})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--families", action="store_true",
                    help="one rollup block per family instead of the per-site report")
    ap.add_argument("--sites", nargs="+", metavar="ADDR",
                    help="report only these PD runtime sites, each with an "
                         "anchored instruction listing. One outside "
                         "0x0000-0xFFFF is refused, and one inside the file range "
                         "is answered with the runtime address at that file_offset")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the decode against pd-stride-families.md and "
                         "the committed CSVs")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    fw = args.firmware or os.path.join(here, DEFAULT_FIRMWARE)
    if args.self_test:
        return self_test(fw)
    if not any((args.families, args.sites, args.csv)):
        ap.error("pick a mode: --families, --sites, --csv or --self-test")
    try:
        wanted = {int(a, 16) for a in args.sites} if args.sites else set()
    except ValueError as exc:
        ap.error(str(exc))
    # Checked over the whole run first, so one bad address in a multi-site call
    # is the diagnostic rather than a partial report and then a traceback.
    for addr in sorted(wanted):
        check_site_addr(addr)

    d = open(fw, "rb").read()
    if not pd_verified(d):
        # stderr, so a --csv redirect stays a clean CSV.
        print(f"note: no {b'ITE8850-PD'.decode()!r} marker at file 0x{0x20040:05X} "
              "-- 0x20000-0x2FFFF is not the image this tool decodes",
              file=sys.stderr)
        return 1

    extents = pd_image_census.function_extents()
    owners = pd_image_census.address_owners(extents)
    names = pd_image_census.function_names()
    sites = site_rows(d, owners, names)

    if args.csv:
        write_csv(site_table(sites, access_index()))
    if args.families:
        summary = family_summary(sites)
        print(f"{len(sites)} PD-image MOV DPTR site(s) carry "
              f"{', '.join('0x' + s for s in FAMILIES)} over the whole image\n")
        print("in-a-listing and anchored are separate questions: a committed pd "
              "listing holds the site, or a backward frame lands on it")
        for stride, got in summary.items():
            print(f"0x{stride}  {got['sites']:>2} site(s)  "
                  f"{len(got['bases'])} base(s)  {got['listing']} in a listing  "
                  f"{got['anchored']} anchored  {got['reached']} reach a "
                  f"construction  {got['consumed']} consumed")
            print(f"        {got['arith'][0]}  bases "
                  + " ".join(f"0x{b:04X}" for b in got["bases"]))
            if got["wraps"] is not None:
                print(f"        low8 and the full product agree below index "
                      f"{got['wraps']} and diverge from it")
            if got["dph"]:
                print(f"        unmodelled DPH addends {' '.join(got['dph'])}")
            print(f"        stop reasons: {'; '.join(got['stops'])}")
        print()
    if args.sites:
        chosen = [s for s in sites if s["row"]["runtime"] in wanted]
        for addr in sorted(wanted - {s["row"]["runtime"] for s in chosen}):
            print(f"PD runtime {_rt(addr)} carries none of "
                  f"{', '.join('0x' + s for s in FAMILIES)}: {NOT_FOUND} by this "
                  "method\n")
        print_sites(d, chosen, args.sites)
    elif not args.families and not args.csv:
        print_sites(d, sites, ())
    return 0


if __name__ == "__main__":
    sys.exit(main())
