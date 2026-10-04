#!/usr/bin/env python3
"""Read the PD stride census's `0x17`, `0x67` and `0x04` rows at site level,
one contributing `MOV DPTR` at a time, and say where each address stops being
followable.

`pd-base-strides.csv` gives those three strides as aggregate rows: a site
count, a base count, a base list. That is the right shape for a census and the
wrong shape for the question the rows raise, because a `--strides` line reading
`17 site(s) over 7 base(s)` does not say which sites, what shape of arithmetic
each one does, or where the address goes next.
../annotations/pd-index-geometry.md §7.5 left them as the three strides
"nothing in this repository has looked at". This is that look, bounded, over the
same committed image.

**The three are two data-layout shapes, not one.** `0x17` reaches its base
through the `= DPTR <- {base} + low8(...)` template, whose `clr a` before the
`addc` discards the multiply's high byte, so its addresses are not linear in
the index. `0x67` and `0x04` reach DPTR through helper `0x10BC`, whose
`mov a,b` before its own `addc` keeps it. `--families` prints the decoded body
of every chain entry either shape runs through, so the distinction is read off
bytes rather than taken from this paragraph.

**Where each family's chain reaches, stated with the exceptions attached.**
Every `0x17` site runs through one of the `low8(...)` chain entries *except
`0xCC5B` and `0xCC95`, which reach no entry at all*: their `helpers` cell reads
`not found by this method` and both are labelled `instruction-framing-candidate`,
because the byte before each site's `0x90` is an `lcall` opcode, so that `0x90`
is the high half of a branch target and the three bytes the census read as
`mov dptr,#imm16` are one instruction and the MOVX after it. Every `0x67` and
`0x04` site reaches `0x10BC`; the walks that go on to hand DPTR to `0x104D` or
`0x1041` stop there, because those entries are outside the term model.

**What the accumulator held at each multiply** is its own column, and it is the
one that decides a question the term strings cannot: a site's own backward frame
reaches its multiply only where the chain leaves the accumulator alone, and for
the `0x17` family it does not at most sites -- the construction entry opens
`movx a,@dptr`, which replaces A with a byte read out of XDATA at the pointer
DPTR already holds. **`0x8068` is the one `0x17` site whose operand is a
register**, because the entry it reaches opens `mov a,r7` instead, and
**`0xCC5B` and `0xCC95` name no operand at all** (`not named by this method`):
their backward frame converges on nothing. `--families` prints the split per
family, so the exception list is readable off the tool rather than kept here
alone. Site `0x8077` is the worked case: its frame reads `A=0x00` and the
committed decode resolves `0x0A27 + low8(0x00x0x17)`, while `pd[0x96fe:]` is
`e0 75 f0 17 a4 24 27` -- `movx a,@dptr ; mov b,#0x17 ; mul ab`. The term is
reported as the committed tool resolves it and the row's `index_source` says why
that term's `0x00` is not the multiplier's operand. That is a refutation with
its bytes, not a corrected figure.

**Three classifications, each from a different body of evidence.** *Which
arithmetic* comes from the template the term resolved through. *Code or data*
comes from `pd_image_census.owning_function()`, whose third return value is a
real answer ("outside the committed pd listings") rather than a gap. *Supported
code site or framing candidate* comes from the byte before the site's opcode, as
above.

**What this cannot do, stated once so no output below has to repeat it:**

  * It is not a call graph and it recovers no function boundary. `helpers` is
    the same unaligned byte scan's target set, so it over-counts (a `12 hi lo`
    inside a data table reads as an `lcall`) and under-counts (a computed jump
    carries no target bytes). An empty `helpers` cell is "not found by this
    method", never "nothing is called" -- the blind spot that forced the 0x07B9
    retraction in ../../docs/findings.md 4c.
  * `owning_function()` attributes a site to a committed `.asm` listing's own
    address set, which is a membership test and not a claim that the bytes are
    the code the export read. "outside the committed pd listings" means this
    repository has no listing covering the address, not that the bytes are
    data.
  * No chain stop here names a record width, a record count or a record
    meaning. A stride constant is a step between addresses; what sits at those
    addresses is not established here, and §7.4's retraction is the standing
    precedent for reading one into it.
  * Nothing here observes hardware. No register is read, written or read back,
    and no index register's value at run time is knowable from these bytes. The
    bases are PD-program data-space addresses and are not described as
    host-visible EC registers; `ec/annotations/registers.yaml` is not touched by
    this file and static evidence cannot re-grade one.

Every stop reason is a mandatory cell rather than a footnote, so a truncated
chain and a complete one cannot look alike; every null is the token
`not found by this method`, never an empty cell. Walks are bounded by both a
count and `min(region_end, len(d))`, the arrangement
../../docs/findings/count-bounded-walk-invariant.md records.

Read-only: it opens the firmware image and the committed CSVs for reading and
writes nothing.

Usage, from the repository root:

    python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --families
    python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --csv
    python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 \
            --sites 0x8077 0xCC5B 0x2F0B 0xA399
    python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    # pd_index_geometry imports its neighbours by bare module name, so the tool
    # directory has to be on the path before it is loaded rather than after.
    # The pattern ec/tools/test_check_site_census.py already uses.
    sys.path.insert(0, HERE)

import pd_image_census as census
from pd_index_geometry import (A_WRITERS, MOV_B_IMM, MOV_DPTR,
                               MOV_R_FROM_A, MUL_AB, OPCODE_LEN, STRIDE_RE,
                               WHOLE_IMAGE, _match_template, ab_of, base_sites,
                               branch_target, check_site_addr, effective_base,
                               effective_terms, frame_of, is_call, is_jmp,
                               mnemonic, pd_bounds, pd_verified, rebased,
                               walk_helper)

ANNOT = os.path.join(HERE, os.pardir, "annotations")
STRIDES_CSV = os.path.join(ANNOT, "pd-base-strides.csv")
ACCESSES_CSV = os.path.join(ANNOT, "pd-index-accesses.csv")
SITES_CSV = os.path.join(ANNOT, "pd-stride-family-sites.csv")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")

# The three aggregate rows pd-index-geometry.md §7.5 names. Held as the
# uppercase hex the committed pd-base-strides.csv prints, so a drift between
# this list and that file is a comparison rather than a reading.
FAMILIES = ("0x17", "0x67", "0x04")

# The arithmetic classes, as two distinct values rather than one field a reader
# has to interpret. `low8-truncated` is a construction whose multiply's high
# byte is dropped before it reaches DPTR; `full-product` is one that keeps it.
# The vocabularies below are module constants for the reason
# pd_index_geometry.UNRESOLVED_STRIDE is: they are machine-readable cells the
# annotation quotes by string, so --self-test asserts them against the
# committed CSV rather than against a copy in prose.
LOW8_TRUNCATED = "low8-truncated"
FULL_PRODUCT = "full-product"

# Which side of the site the effective base came from. `rebased` means a chain
# term replaced the `MOV DPTR` immediate with an immediate base of its own, so
# the site's own literal is not the address the family indexes from; the two
# are never conflated into one `base` cell.
REBASED = "rebased"
SITE_IMMEDIATE = "site-immediate"

# The framing classes. A supported code site is one whose `0x90` opcode is
# preceded by a byte that does not make it a branch operand half; a framing
# candidate is one where it is, which is a statement about framing evidence and
# not about what the routine does.
CODE_SITE = "code-site"
FRAMING_CANDIDATE = "instruction-framing-candidate"

# What the accumulator held at the site's multiply. `movx-load` is the one that
# refutes a frame literal: an instruction ahead of the multiply read a byte
# from XDATA at the pointer DPTR already held, so the site's own frame never
# reaches the product. `clobbered` is the residue -- some other accumulator
# writer this walk names no source for -- and it is a separate value because
# "something wrote A" and "a byte came out of XDATA" are different claims.
# `not named` is what a site gets when neither its backward frame nor the walk
# to the multiply puts a value there, and it is a different answer from the walk
# failing to arrive.
INDEX_FROM_FRAME = "site-frame"
INDEX_FROM_REGISTER = "register"
INDEX_FROM_MOVX = "movx-load"
INDEX_CLOBBERED = "clobbered"
INDEX_NOT_NAMED = "not named by this method"
INDEX_NOT_REACHED = "multiply not reached by this method"

# The instruction budget index_source_of() walks before it gives up, which is
# chain_from()'s own window: the two ask the same question of the same bytes and
# a different budget would make them answer about different ranges.
CHAIN_WINDOW = 12

NOT_FOUND = census.NOT_FOUND       # "not found by this method"
UNRESOLVED_DIRECTION = "no direction established by this method"

FIELDS = (
    "stride", "site_runtime", "site_file", "mov_dptr_immediate",
    "effective_base", "base_source", "index_terms", "index_source", "destination",
    "arithmetic", "frame_onto", "frame_over", "in_pd_listing", "owning_function",
    "site_class", "helpers", "chain_stop", "stop_runtime", "stop_file",
    "access_row_kind", "access_status", "consumer_runtime", "consumer_file",
    "direction", "access_id",
)

# The edge a §8 access row records for a handoff, e.g. `0x807A>0x96FE`: the
# runtime address of the call instruction and the entry it names. A site's join
# key is the edge leaving the instruction *after* its `MOV DPTR`, and only when
# the edge names an entry the site's own chain reached -- both halves, because
# either alone would match rows that are about a different call.
HANDOFF_RE = re.compile(r"(?:^|[@;])(0x[0-9A-F]{4})>(0x[0-9A-F]{4})(?=$|[;/])")

# The instructions the two walks below name. `MOVX_A_DPTR` is the one that
# refutes a frame literal in index_source_of(): it replaces A with a byte read
# out of XDATA. The register load is the benign case, because what it reads is
# whatever the routine's caller left in the register bank. `MOVX_DPTR_A` writes
# rather than reads, so it leaves A alone and only ends a chain walk.
MOVX_A_DPTR = 0xE0
MOVX_DPTR_A = 0xF0
MOV_A_RN = range(0xE8, 0xF0)
MOV_A_IMM = 0x74
CLR_A = 0xE4
RET = 0x22
RETI = 0x32


def _rt(addr: int) -> str:
    """PD runtime address, the form every committed PD CSV prints."""
    return f"0x{addr:04X}"


def _file(off: int) -> str:
    return f"0x{off:05X}"


def _term_at(d: bytes, i: int):
    """(length, term) for the term template at file offset `i`, else (0, None).

    `pd_index_geometry`'s own matcher, imported under its underscore rather
    than copied: those byte runs *are* the term model, and a second copy of
    them here would be a second model that could disagree with the first
    without anything noticing.
    """
    return _match_template(d, i)


def chain_stop_at(d: bytes, site_off: int, max_insns: int = CHAIN_WINDOW):
    """The file offset a base site's chain walk stops at, and why.

    `chain_from()` returns the reason but not the address, and this file needs
    both in cells of their own -- a stop reason that names no address reads
    exactly like one that never stopped, and that is the difference between a
    bounded walk and an unbounded one that a reader cannot see.

    This is a second walk over the same dispatch rather than a
    re-implementation of the analysis: --self-test asserts that the reason
    produced here is the one `chain_from()` returns, for every site on the
    committed image, so the two cannot drift apart without a red run.

    The offset returned is always the last instruction this walk read, so the
    column means one thing in every row. When that instruction is a handoff to
    an entry the term model does not cover, the entry and the instruction
    inside it that broke the model are named in the reason rather than in the
    address, and the call site is what the address column carries.
    """
    lo, hi = pd_bounds()
    hi = min(hi, len(d))
    i = site_off + OPCODE_LEN[MOV_DPTR]
    for _ in range(max_insns):
        if not lo <= i < hi:
            return i, (f"walk left the pd-image at runtime {_rt(i - lo)}, "
                       f"its end at file {_file(hi)}")
        n, term = _term_at(d, i)
        if term:
            i += n
            continue
        op = d[i]
        if i + OPCODE_LEN[op] > hi:
            return i, (f"the instruction at runtime {_rt(i - lo)} is cut by "
                       f"the pd-image end at file {_file(hi)}")
        raw = d[i:i + OPCODE_LEN[op]]
        here = i - lo
        if op in (MOVX_A_DPTR, MOVX_DPTR_A):
            return i, "movx: DPTR dereferenced here"
        if op == MOV_DPTR:
            return i, "DPTR reloaded"
        if is_call(op) or is_jmp(op):
            target = branch_target(raw, here)
            if target is None:
                return i, f"unresolvable handoff at {_rt(here)}"
            _, _, note, _ = walk_helper(d, target)
            if note:
                return i, f"0x{target:04X} is {note}"
            if is_jmp(op):
                return i, f"tail call into 0x{target:04X}"
        elif raw[:2] == MOV_B_IMM or MOV_A_RN[0] <= op <= MOV_A_RN[-1] \
                or op in (MOV_A_IMM, CLR_A, MUL_AB) \
                or MOV_R_FROM_A[0] <= op <= MOV_R_FROM_A[1]:
            # The loads a chain steps over on its way to a multiply: they
            # change no register the walk is tracking toward the address.
            pass
        else:
            return i, f"`{mnemonic(d, i, here).strip()}` at {_rt(here)}"
        i += OPCODE_LEN[op]
    return i, f"{max_insns}-instruction window ended"


def index_source_of(d: bytes, site_off: int, a_sym: str,
                    max_insns: int = CHAIN_WINDOW) -> str:
    """What the accumulator held when this site's chain reached its multiply.

    The committed decode substitutes the site's own backward frame into every
    `{a}` a helper's term leaves behind, and that substitution is what prints
    `0x0A27 + low8(0x00x0x17)` at site `0x8077`. This walk decides instead
    whether A survives to the multiply: `movx a,@dptr` on the way reads a byte
    out of XDATA at the pointer DPTR already holds, `mov a,rN` reads the
    register bank, and any other accumulator writer leaves a value this walk
    names no source for. Only the frame's own literal is the site's frame, and
    only when nothing on the way replaced it -- and only where the frame names
    one at all, which is not the same as the frame having been looked at.

    It follows a modelled handoff into the called entry's own bytes, which is
    where the refuting instruction lives -- at `0x96FE`, three bytes past the
    `lcall` the site itself decodes. Where it steps over an instruction the term
    model does not cover, it does so only when that instruction writes no
    register it is tracking; anything that writes the accumulator is recorded
    and the walk continues, and a `ret` or a tail call ends it because nothing
    after either is this site's construction. A framing candidate's row is read
    over the same framing the row already flags in `site_class`, so its value
    is evidence about that framing and not about an established instruction
    boundary.
    """
    lo, hi = pd_bounds()
    hi = min(hi, len(d))
    source = _frame_source(a_sym)
    seen = set()
    i = site_off + OPCODE_LEN[MOV_DPTR]
    for _ in range(max_insns):
        if not lo <= i < hi or i in seen:
            return INDEX_NOT_REACHED
        seen.add(i)
        if _term_at(d, i)[1]:
            return source
        op = d[i]
        if i + OPCODE_LEN[op] > hi:
            return INDEX_NOT_REACHED
        raw = d[i:i + OPCODE_LEN[op]]
        if op == MOVX_A_DPTR:
            source = INDEX_FROM_MOVX
        elif MOV_A_RN[0] <= op <= MOV_A_RN[-1]:
            source = INDEX_FROM_REGISTER
        elif op in (MOV_A_IMM, CLR_A):
            source = INDEX_FROM_FRAME
        elif op in A_WRITERS:
            source = INDEX_CLOBBERED
        elif op in (RET, RETI):
            return INDEX_NOT_REACHED
        elif is_call(op) or is_jmp(op):
            target = branch_target(raw, i - lo)
            # A tail call does not come back here, so nothing after it is this
            # site's construction and the walk ends where the caller ends.
            if target is None or is_jmp(op):
                return INDEX_NOT_REACHED
            if walk_helper(d, target)[2]:
                return INDEX_NOT_REACHED
            i = lo + target
            continue
        i += OPCODE_LEN[op]
    return INDEX_NOT_REACHED


def _frame_source(a_sym: str) -> str:
    """What the site's own backward frame leaves in A, as one of the values
    above. A frame that names no value is `not named`, which is what
    `ab_of()`'s `{a}` placeholder means -- the frame was looked at and came
    back empty-handed, which is not the same answer as the frame never having
    been consulted.
    """
    if re.fullmatch(r"R[0-7]", a_sym):
        return INDEX_FROM_REGISTER
    if re.fullmatch(r"0x[0-9A-F]{2}", a_sym):
        return INDEX_FROM_FRAME
    return INDEX_NOT_NAMED


def site_class(d: bytes, off: int) -> str:
    """Supported code site, or a candidate whose opcode byte is a branch operand.

    The test is the byte before the `0x90`. An `lcall` or `ljmp` opcode there
    makes the `0x90` the high half of that branch's 16-bit target, so the three
    bytes the census read as `mov dptr,#imm16` are one instruction and a MOVX
    that follows it. This is framing evidence and not a claim about what the
    bytes do, which is why the class is `candidate` rather than a rejection.
    """
    prev = d[off - 1] if off else None
    if prev is not None and (is_call(prev) or is_jmp(prev)):
        return FRAMING_CANDIDATE
    return CODE_SITE


def _access_index():
    """{handoff edge: [access row, ...]} from the committed access census.

    Read rather than re-derived: §8's rows carry its own discovery decisions,
    and re-running that scan to reproduce them would be a second census whose
    agreement with the committed one is a thing to discover rather than a thing
    the reader can take.
    """
    out = {}
    with open(ACCESSES_CSV, newline="") as f:
        for row in csv.DictReader(f):
            for src, dst in HANDOFF_RE.findall(row["construction_id"]):
                out.setdefault((src, dst), []).append(row)
    for rows in out.values():
        rows.sort(key=lambda r: r["access_id"])
    return out


def access_join(site: dict, index) -> dict:
    """The §8 access row for this site, or a token per cell.

    The key is the handoff edge leaving the instruction after the site's
    `MOV DPTR`, and only where that edge names an entry this site's own chain
    reached. Where several §8 rows share the edge they are the same call
    reached from different framings; this takes the first by ascending
    `access_id`, which is a naming rule and not a judgement, so the row it
    landed on is named in the CSV's own `access_id` column and can be looked up
    in `pd-index-accesses.csv` rather than taken on trust.
    """
    src = _rt(site["runtime"] + OPCODE_LEN[MOV_DPTR])
    for entry in site["helpers"]:
        rows = index.get((src, _rt(entry)))
        if rows:
            row = rows[0]
            return {
                "access_row_kind": row["row_kind"],
                "access_status": row["status"],
                "consumer_runtime": row["consumer_runtime"] or NOT_FOUND,
                "consumer_file": row["consumer_file"] or NOT_FOUND,
                "direction": row["direction"] or UNRESOLVED_DIRECTION,
                "access_id": row["access_id"],
            }
    return {
        "access_row_kind": NOT_FOUND, "access_status": NOT_FOUND,
        "consumer_runtime": NOT_FOUND, "consumer_file": NOT_FOUND,
        "direction": UNRESOLVED_DIRECTION, "access_id": NOT_FOUND,
    }


def _cross_check(rows) -> list:
    """Where this tool's rows disagree with the committed stride census.

    That CSV is a read-only input and was derived by a different walk, so
    agreement is a property worth checking rather than an assumption: a stride
    row whose sites or bases differ means one of the two has drifted, and the
    reader is told which instead of inheriting whichever this file happened to
    produce.
    """
    problems = []
    with open(STRIDES_CSV, newline="") as f:
        census_rows = {r["stride"]: r for r in csv.DictReader(f)}
    for stride in FAMILIES:
        got = [r for r in rows if r["stride"] == stride]
        row = census_rows.get(stride)
        if row is None:
            problems.append(f"{stride} is absent from {os.path.basename(STRIDES_CSV)}")
            continue
        if len(got) != int(row["sites"]):
            problems.append(
                f"{stride}: {len(got)} site(s) here against "
                f"{row['sites']} in {os.path.basename(STRIDES_CSV)}")
        want_bases = row["base_list"].split()
        got_bases = sorted({r["effective_base"] for r in got})
        if got_bases != want_bases:
            problems.append(
                f"{stride}: bases {' '.join(got_bases)} here against "
                f"{row['base_list']} in {os.path.basename(STRIDES_CSV)}")
    return problems


def family_rows(d: bytes) -> list:
    """One dict per contributing site, in the committed CSV's sort order.

    `base_sites()` is called once over the whole image and then filtered,
    rather than re-walked per stride: `stride_census()` cannot be reused
    because it aggregates, and the per-site rows it discards are the whole
    subject here.
    """
    lo, _ = pd_bounds()
    wanted = {s[2:].upper() for s in FAMILIES}
    index = _access_index()
    extents = census.function_extents()
    owners = census.address_owners(extents)
    names = census.function_names()
    out = []
    for site in base_sites(d, WHOLE_IMAGE):
        terms = effective_terms(site["terms"])
        found = set()
        for term in terms:
            found.update(STRIDE_RE.findall(term))
        if not found & wanted:
            continue
        # A site resolving two of these strides would emit two rows here, and
        # `--self-test` asserts that none does -- so a row's `stride` column is
        # read off the site rather than chosen between alternatives.
        for stride in sorted(found & wanted):
            stop, reason = chain_stop_at(d, site["file_offset"])
            entry, name, why = census.owning_function(site["runtime"], owners, names)
            joined = access_join(site, index)
            first = terms[0] if terms else ""
            out.append(dict(zip(FIELDS, (
                f"0x{stride}",
                _rt(site["runtime"]),
                _file(site["file_offset"]),
                f"0x{site['base']:04X}",
                f"0x{effective_base(site):04X}",
                REBASED if rebased(site["terms"]) else SITE_IMMEDIATE,
                " + ".join(terms) if terms else NOT_FOUND,
                index_source_of(d, site["file_offset"], site["a"]),
                first.split(" ← ")[0] if " ← " in first else "DPTR",
                LOW8_TRUNCATED if any("low8(" in t for t in terms) else FULL_PRODUCT,
                site["frame_onto"],
                site["frame_over"],
                "yes" if entry is not None else "no",
                (f"0x{entry:04X} {name}" if entry is not None else why),
                site_class(d, site["file_offset"]),
                (" ".join(_rt(h) for h in site["helpers"]) if site["helpers"]
                 else NOT_FOUND),
                reason,
                _rt(stop - lo),
                _file(stop),
                joined["access_row_kind"], joined["access_status"],
                joined["consumer_runtime"], joined["consumer_file"],
                joined["direction"], joined["access_id"],
            ))))
    out.sort(key=lambda r: tuple(str(r[k]) for k in FIELDS))
    return out


def divergence_index(stride: int) -> int:
    """The smallest index at which `low8(index*stride)` stops being the product.

    Integer arithmetic throughout, so this is the first index whose product
    leaves the low byte rather than a rounded-up division that says the same
    thing. It is the number at which a truncating construction and a
    full-product one disagree about the address they name, and it is what makes
    the two shapes different claims rather than two spellings.
    """
    index = 1
    while (index * stride) & 0xFF == index * stride:
        index += 1
    return index


def csv_text(rows) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def print_sites_table(rows, out=sys.stdout) -> None:
    print(f"{'stride':>6}  {'site':>6}  {'base':>6}  {'src':<14} "
          f"{'arith':<15} {'class':<28} helpers", file=out)
    for r in rows:
        print(f"{r['stride']:>6}  {r['site_runtime']:>6}  {r['effective_base']:>6}  "
              f"{r['base_source']:<14} {r['arithmetic']:<15} {r['site_class']:<28} "
              f"{r['helpers']}", file=out)
    print("\nEvery base is a PD-program data-space address, not a host-visible "
          "EC register;\nno record count, width or content follows from a stride "
          "constant, and no\nhardware was observed: this is static analysis of "
          "committed bytes.", file=out)


def helper_bodies(d: bytes, entries):
    """`entry -> decoded body bytes` for the chain entries this report names.

    Printed rather than asserted, because the byte run is what separates the
    two arithmetic classes and a reader who is asked to take that on trust is
    being asked for the thing the annotation exists to show. Spaced one byte per
    group so the run reads against a listing rather than as a hex string.
    """
    out = {}
    for entry in entries:
        body = b"".join(raw for _, raw in walk_helper(d, entry)[1])
        out[entry] = " ".join(f"{b:02x}" for b in body)
    return out


def print_families(rows, d: bytes, out=sys.stdout) -> None:
    """The per-family summary, including every figure the annotation quotes.

    Each block prints its own site and base totals, the arithmetic class, the
    index at which the class stops agreeing with an exact product, how the
    framing, the multiply's operand and the §8 join split, and the decoded body
    of every chain entry it reached. A figure the annotation states has to be
    readable off one of these lines or out of the committed CSV; that is the
    whole point of the mode.
    """
    problems = _cross_check(rows)
    print("Stride families, read at site level over the whole PD image", file=out)
    print(f"cross-check against {os.path.basename(STRIDES_CSV)}: "
          f"{'agrees' if not problems else 'DISAGREES'}", file=out)
    for problem in problems:
        print(f"  {problem}", file=out)
    for stride in FAMILIES:
        got = [r for r in rows if r["stride"] == stride]
        if not got:
            print(f"\n{stride}: no site resolved this stride by this method",
                  file=out)
            continue
        value = int(stride, 16)
        classes = sorted({r["arithmetic"] for r in got})
        frames = sorted({r["site_class"] for r in got})
        candidates = [r["site_runtime"] for r in got
                      if r["site_class"] == FRAMING_CANDIDATE]
        reached = [r for r in got if r["helpers"] != NOT_FOUND]
        joined = [r for r in got if r["access_id"] != NOT_FOUND]
        index_at = divergence_index(value)
        print(f"\n{stride}  {len(got)} site(s) over "
              f"{len({r['effective_base'] for r in got})} base(s): "
              f"{' '.join(sorted({r['effective_base'] for r in got}))}", file=out)
        print(f"  arithmetic: {' '.join(classes)}", file=out)
        print(f"  low8/product divergence at index {index_at} "
              f"(low8 = {(index_at * value) & 0xFF}, "
              f"exact = {index_at * value})", file=out)
        print(f"  framing: {' '.join(frames)}", file=out)
        if candidates:
            print(f"  framing candidates, whose chain reaches no helper: "
                  f"{' '.join(candidates)}", file=out)
        else:
            print("  framing candidates, whose chain reaches no helper: none",
                  file=out)
        print(f"  sites whose chain reaches a helper: {len(reached)} of "
              f"{len(got)}", file=out)
        print(f"  sites with an access row: {len(joined)} of {len(got)}", file=out)
        for name in (INDEX_FROM_MOVX, INDEX_FROM_REGISTER, INDEX_FROM_FRAME,
                     INDEX_NOT_NAMED, INDEX_CLOBBERED, INDEX_NOT_REACHED):
            sel = [r["site_runtime"] for r in got if r["index_source"] == name]
            if sel:
                print(f"  multiply operand is {name}: {' '.join(sel)}", file=out)
        for name in (LOW8_TRUNCATED, FULL_PRODUCT):
            sel = [r for r in got if r["arithmetic"] == name]
            if sel:
                print(f"  {name} sites: "
                      f"{' '.join(r['site_runtime'] for r in sel)}", file=out)
        entries = sorted({int(h, 16) for r in reached
                          for h in r["helpers"].split()})
        for entry, body in helper_bodies(d, entries).items():
            print(f"  chain entry {entry:04X}: {body}", file=out)


def print_site_detail(d: bytes, addrs, out=sys.stdout) -> None:
    """The anchored listing and every derived cell for the named sites.

    The listings are what make a wrong assertion visible, which is the
    precondition `pd_index_geometry.site_rows()` states for its own `--sites`
    and the reason this mode decodes rather than summarises.
    """
    lo, _ = pd_bounds()
    rows = {r["site_runtime"]: r for r in family_rows(d)}
    for addr in addrs:
        row = rows.get(_rt(addr))
        if row is None:
            print(f"{_rt(addr)} resolves no {', '.join(FAMILIES)} site by this "
                  f"method", file=out)
            continue
        print(f"\n{row['site_runtime']} (file {row['site_file']})  "
              f"{row['stride']}  base {row['mov_dptr_immediate']} "
              f"effective {row['effective_base']} ({row['base_source']})",
              file=out)
        for key in ("index_terms", "index_source", "destination", "arithmetic",
                    "frame_onto", "frame_over", "in_pd_listing",
                    "owning_function", "site_class", "helpers", "chain_stop",
                    "stop_runtime", "stop_file", "access_row_kind",
                    "access_status", "consumer_runtime", "consumer_file",
                    "direction", "access_id"):
            print(f"  {key:<18} {row[key]}", file=out)
        off = lo + addr
        i = off
        print("  listing:")
        for _ in range(10):
            n = OPCODE_LEN[d[i]]
            print(f"    {_rt(i - lo)}  {d[i:i + n].hex(' '):<9} "
                  f"{mnemonic(d, i, i - lo).strip()}", file=out)
            i += n


# --- self-test -------------------------------------------------------------
#
# Every expectation below is transcribed from bytes or from a committed CSV, so
# the tool cannot disagree with the annotation that cites it. The byte runs come
# from the `r2 -a 8051` listings in ../annotations/pd-stride-families.md §2;
# the site terms, bases and stop reasons from --sites and --bases on the same
# image; the §8 join rows from pd-index-accesses.csv itself.

# The two byte runs that separate the shapes, transcribed whole. 0x10BC keeps
# the multiply's high byte (`mov a,b` before its `addc`); the `0x96FE` body
# drops it (`clr a` before its `addc`). The `0x96FE` run is pinned in full
# rather than from its template onward because its opening `e0` -- the
# `movx a,@dptr` the refutation below turns on -- is part of the shape.
FULL_PRODUCT_BYTES = "a42582f582e5f03583f58322"
TRUNCATED_BYTES = "e075f017a42427f582e4340af58322"

# Every site of every family, with the effective base and the term string the
# committed decode resolves. Properties of the committed firmware, not counts
# of this repository's text.
SITE_TERMS = {
    "0x2F0B": ("0x07C4", "A×0x67"), "0x2F6A": ("0x07A3", "A×0x67"),
    "0x75CD": ("0x0A35", "DPTR ← 0x0A35 + low8(A×0x17)"),
    "0x768E": ("0x0A35", "DPTR ← 0x0A35 + low8(A×0x17)"),
    "0x769E": ("0x0A35", "DPTR ← 0x0A35 + low8(A×0x17)"),
    "0x8068": ("0x0A15", "DPTR ← 0x0A15 + low8(R7×0x17)"),
    "0x8077": ("0x0A27", "DPTR ← 0x0A27 + low8(0x00×0x17)"),
    "0x80B9": ("0x0A27", "DPTR ← 0x0A27 + low8(A×0x17)"),
    "0x80E5": ("0x0A13", "DPTR ← 0x0A13 + low8(A×0x17)"),
    "0x81DD": ("0x0A13", "DPTR ← 0x0A13 + low8(A×0x17)"),
    "0x9C15": ("0x0661", "A×0x67"), "0x9C39": ("0x0667", "A×0x67"),
    "0x9C46": ("0x069A", "A×0x67"), "0x9C6D": ("0x069B", "R5×0x67"),
    "0xA399": ("0x00C0", "R7×0x04"), "0xA3AD": ("0x00C8", "A×0x04"),
    "0xAED3": ("0x0A2D", "DPTR ← 0x0A2D + low8(A×0x17)"),
    "0xAF70": ("0x0A2C", "DPTR ← 0x0A2C + low8(A×0x17)"),
    "0xB39E": ("0x0A35", "DPTR ← 0x0A35 + low8(R7×0x17)"),
    "0xB3AE": ("0x0A2D", "DPTR ← 0x0A2D + low8(A×0x17)"),
    "0xB3C8": ("0x0A35", "DPTR ← 0x0A35 + low8(A×0x17)"),
    "0xC8F0": ("0x0A13", "DPTR ← 0x0A13 + low8(A×0x17)"),
    "0xCC5B": ("0x0A29", "DPTR ← 0x0A29 + low8(A×0x17)"),
    "0xCC95": ("0x0A15", "DPTR ← 0x0A15 + low8(A×0x17)"),
    "0xCF13": ("0x07C4", "A×0x67"),
    "0xD745": ("0x0A2C", "DPTR ← 0x0A2C + low8(A×0x17)"),
}

# The two sites whose `0x90` is an `lcall` operand half, and what the byte
# before each says. `pd[0xcc5a:]` and `pd[0xcc94:]` are both `12 90 fc e0`.
FRAMING_BYTES = {"0xCC5A": "1290fce0", "0xCC94": "1290fce0"}

# Where each family's chain walk stops, and why. The stop reason is the
# committed decode's own string, so a divergence here means chain_stop_at() and
# chain_from() have parted ways rather than that the firmware moved.
STOP_REASONS = {
    "0x2F0B": ("0x2F12", "`add  a,0x83` at 0x2F12"),
    "0x2F6A": ("0x2F71", "`add  a,0x83` at 0x2F71"),
    "0x9C15": ("0x9C1F", "`add  a,0x83` at 0x9C1F"),
    "0x9C39": ("0x9C40", "`add  a,0x83` at 0x9C40"),
    "0x9C46": ("0x9C51", "`add  a,0x83` at 0x9C51"),
    "0x9C6D": ("0x9C78", "`add  a,0x83` at 0x9C78"),
    "0xCF13": ("0xCF1A", "`add  a,0x83` at 0xCF1A"),
    "0xA399": ("0xA39F", "0x104D is unmodelled: 0x104D `mov  r0,0x82` is outside "
                        "the term model"),
    "0xA3AD": ("0xA3B3", "0x104D is unmodelled: 0x104D `mov  r0,0x82` is outside "
                        "the term model"),
    "0x8077": ("0x807D", "movx: DPTR dereferenced here"),
    "0xCC5B": ("0xCC6C", "movx: DPTR dereferenced here"),
    "0x8068": ("0x806E", "movx: DPTR dereferenced here"),
}

# The refutation: site `0x8077`'s frame puts a literal `0x00` in A, the
# committed decode resolves that literal into the term, and the helper the
# chain reaches opens `movx a,@dptr`, so the byte the multiply consumes came
# from XDATA and not from the frame.
REFUTATION = ("0x8077", "0x96FE", "e075f017a4", INDEX_FROM_MOVX)

# The three construction byte runs the arithmetic classes are read from, each
# at the runtime address a named site reaches it through. The class is checked
# against that site's own row as well, so the bytes and the label the CSV
# carries are held to each other and not only to this list.
CONSTRUCTIONS = (
    ("0x10BC", FULL_PRODUCT_BYTES, FULL_PRODUCT, "0x2F0B"),
    ("0x9702", "a42427f582e4340af583", LOW8_TRUNCATED, "0x8077"),
    ("0xCC62", "a42429f582e4340af583", LOW8_TRUNCATED, "0xCC5B"),
)

# The index at which low8() and the exact product first disagree, per family.
# 0x17*11 = 253 stays in the low byte and 0x17*12 = 276 does not; the same
# arithmetic for the other two.
DIVERGENCE = {"0x17": (12, 20, 276), "0x67": (3, 53, 309), "0x04": (64, 0, 256)}


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
        print("  !   no ITE8850-PD marker: 0x20000-0x2FFFF is not the image "
              "this tool decodes")
        return 1

    for addr, want in ((0x10BC, FULL_PRODUCT_BYTES),
                       (0x96FE, TRUNCATED_BYTES)):
        _, listing, _, _ = walk_helper(d, addr)
        got = b"".join(raw for _, raw in listing).hex()
        check(got == want, f"helper {_rt(addr)} body is `{want}` (got `{got}`)")

    rows = family_rows(d)
    check(bool(rows), "the three families resolve at least one site each")

    # The committed CSV is this tool's own output, so its disagreement is the
    # thing worth reading first.
    problems = _cross_check(rows)
    check(not problems,
          f"every family agrees with {os.path.basename(STRIDES_CSV)} on its "
          f"sites and bases ({'; '.join(problems) or 'no disagreement'})")

    by_site = {r["site_runtime"]: r for r in rows}
    check(len(by_site) == len(rows),
          f"no site resolves two of the three strides, so one row is one site "
          f"({len(by_site)} site(s), {len(rows)} row(s))")
    for addr, (base, terms) in SITE_TERMS.items():
        row = by_site.get(addr)
        if row is None:
            check(False, f"{addr} resolves a stride family site (absent)")
            continue
        check(row["effective_base"] == base and row["index_terms"] == terms,
              f"{addr} resolves {base} as {terms} "
              f"(got {row['effective_base']} as {row['index_terms']})")

    for addr, want in FRAMING_BYTES.items():
        off = lo + int(addr, 16)
        got = d[off:off + len(want) // 2].hex()
        check(got == want, f"pd[{addr}:] is `{want}` (got `{got}`)")
    for addr in ("0xCC5B", "0xCC95"):
        row = by_site.get(addr, {})
        check(row.get("site_class") == FRAMING_CANDIDATE
              and row.get("helpers") == NOT_FOUND,
              f"{addr} is labelled {FRAMING_CANDIDATE} and reaches no helper "
              f"(got {row.get('site_class')}, helpers {row.get('helpers')})")

    supported = [r for r in rows if r["site_class"] == CODE_SITE]
    check(all(r["helpers"] != NOT_FOUND for r in supported),
          f"every one of the {len(supported)} supported code sites reaches a "
          f"helper")

    for addr, (stop, reason) in STOP_REASONS.items():
        row = by_site.get(addr, {})
        check(row.get("stop_runtime") == stop and row.get("chain_stop") == reason,
              f"{addr} stops at {stop} with `{reason}` "
              f"(got {row.get('stop_runtime')}, `{row.get('chain_stop')}`)")

    # chain_stop_at() is a second walk; this is what holds it to chain_from().
    committed = {r["runtime"]: r["stopped"] for r in base_sites(d, WHOLE_IMAGE)}
    drifted = [r["site_runtime"] for r in rows
               if r["chain_stop"] != committed.get(int(r["site_runtime"], 16))]
    check(not drifted,
          f"every stop reason matches the committed decode's own "
          f"({'; '.join(drifted) or 'all match'})")

    site, entry, opening, want_source = REFUTATION
    off = lo + int(site, 16)
    frame = ab_of(frame_of(d, off))
    source = by_site.get(site, {}).get("index_source")
    entry_off = lo + int(entry, 16)
    got_opening = d[entry_off:entry_off + len(opening) // 2].hex()
    check(frame[0] == "0x00" and got_opening == opening
          and source == want_source,
          f"{site}'s frame puts {frame[0]} in A, and helper {entry} opens "
          f"`{opening}` (`movx a,@dptr ; mov b,#0x17 ; mul ab`), so the "
          f"multiply's operand is {want_source} rather than the frame literal "
          f"(got frame {frame[0]}, opening `{got_opening}`, source {source})")

    for addr, want, klass, site_addr in CONSTRUCTIONS:
        off = lo + int(addr, 16)
        got = d[off:off + len(want) // 2].hex()
        got_class = by_site.get(site_addr, {}).get("arithmetic")
        check(got == want and got_class == klass,
              f"construction {addr} is `{want}` and site {site_addr} reads as "
              f"{klass} (got `{got}`, {got_class})")

    for stride, (index, low, exact) in DIVERGENCE.items():
        got = divergence_index(int(stride, 16))
        check(got == index and (index * int(stride, 16)) & 0xFF == low
              and index * int(stride, 16) == exact,
              f"{stride} diverges at index {index} (low8 {low}, exact {exact}; "
              f"got index {got})")

    joined = [r for r in rows if r["access_id"] != NOT_FOUND]
    check(all(r["access_id"] and r["access_status"] and r["direction"]
              for r in joined),
          f"every one of the {len(joined)} joined sites carries its §8 row's "
          f"status and direction")

    # A CSV round trip that checks the lengths before zipping, so a truncated
    # table cannot silently align one row's cells with another's.
    text = csv_text(rows)
    parsed = list(csv.DictReader(io.StringIO(text)))
    check(len(parsed) == len(rows)
          and all(set(r) == set(FIELDS) for r in parsed),
          f"--csv round-trips through DictReader with {len(FIELDS)} columns "
          f"and one row per site")
    for row in parsed:
        empties = [k for k, v in row.items() if v == ""]
        if empties:
            check(False, f"{row['site_runtime']} leaves {', '.join(empties)} empty")
            break
    else:
        check(True, f"no cell of the {len(FIELDS)} columns is empty")

    if os.path.exists(SITES_CSV):
        with open(SITES_CSV, encoding="utf-8") as f:
            committed_csv = f.read()
        check(committed_csv == text,
              f"ec/annotations/{os.path.basename(SITES_CSV)} regenerates byte "
              f"for byte from the committed firmware")
    else:
        check(False, f"ec/annotations/{os.path.basename(SITES_CSV)} exists")

    print(f"\n  {bad} failure(s)" if bad else "\n  all assertions passed")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?",
                    default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--families", action="store_true",
                    help="per-family summary: the arithmetic shape, the index "
                         "at which it stops agreeing with an exact product, "
                         "how the framing, the multiply's operand and the "
                         "access join split, and the decoded body of every "
                         "chain entry reached")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout")
    ap.add_argument("--sites", nargs="+", metavar="ADDR",
                    help="anchored listing and every derived cell for these "
                         "PD runtime addresses, e.g. 0x8077 0xCC5B")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the decode against the committed annotations "
                         "and CSVs")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args.firmware)

    d = open(args.firmware, "rb").read()
    if not pd_verified(d):
        print("note: 0x20000-0x2FFFF is not the ITE8850-PD image this tool "
              "decodes", file=sys.stderr)
        return 1

    if args.sites:
        try:
            addrs = [int(a, 16) for a in args.sites]
            # The committed refusal, reused rather than restated: it names the
            # region and answers the file-offset confusion with the runtime
            # address at it, which is the mistake this tool's own two address
            # columns invite.
            for addr in addrs:
                check_site_addr(addr)
        except ValueError as exc:
            ap.error(str(exc))
        print_site_detail(d, addrs)
    rows = family_rows(d)
    if args.csv:
        sys.stdout.write(csv_text(rows))
    elif args.families:
        print_families(rows, d)
    elif not args.sites:
        print_sites_table(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
