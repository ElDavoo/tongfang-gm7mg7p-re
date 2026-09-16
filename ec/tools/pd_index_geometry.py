#!/usr/bin/env python3
"""Decode the ITE8850-PD image's DPTR index-helper family, the bases it is
called against, and who calls the routines that do it.

trace_xdata_refs.py prints `DPTR handed to lcall 0x90cb -- direction
unresolved here` and stops, because it is a linear walk that cannot follow a
call. That line is the last one in three annotation files:
../annotations/ec-0x07d0-sites.md 4 ("contents unidentified"),
../annotations/pd-xdata-overlap.md 4 ("would be a guess and is not made
here") and 6 ("no control-flow recovery"). This tool answers the mechanical
half of it -- *what address the helper computes* -- and bounds, without
resolving, the half that needs a call graph.

Three modes, in increasing order of how much they assume:

  --helpers   Decode each named helper entry to its `ret`, following a tail
              `ljmp`/`ajmp` and stepping into an `lcall`, and report the
              symbolic term(s) it adds to DPTR. The term model is two byte
              templates (Keil's `DPTR += A*B`, and `DPH += 2*A`) plus the
              instructions that load A and B; a routine whose body is not
              built out of those is reported `unmodelled` with its listing
              rather than force-fitted into a term. This mode assumes only
              that the entry address is an instruction boundary.
  --bases     Every PD-image `MOV DPTR,#imm16` whose immediate is in the low
              base run, with the chain of helpers it hands DPTR to, their term
              sum resolved against the A/B the site's own frame sets, and what
              ended the chain. The frame comes from the longest backward walk
              that converges on the site (disasm8051.converges_from()'s
              idiom), so A and B are "as decoded from an anchor", not "as
              executed".
  --callers   For a PD runtime site: two candidate routine entries -- the
              nearest preceding call target by byte scan, and the nearest that
              also passes the two structural tests in reaches() and
              is_entry_shaped() -- and every site calling each, with its own
              framing counts and any literal `mov rN,#imm` its frame contains.
              Both are heuristics; printing them side by side is the point.

What this cannot do, stated once so no output below has to repeat it:

  * It is not a call graph. Targets come from the same unaligned byte scan
    scan_refs.py uses, so the caller lists over-count (a `12 hi lo` inside a
    data table looks like an `lcall`; ../annotations/bank-call-audit.md 1 has
    the measured size of that effect) and simultaneously under-count, because
    a computed `jmp @a+dptr` or a call reached through a table carries no
    target bytes at all. An empty caller list means "not found by this
    method", never "nothing calls it" -- the blind spot that forced the
    0x07B9 retraction in ../../docs/findings.md 4c.
  * Neither entry choice is a recovered function boundary. If a routine is
    only ever reached by falling through, or only through a computed jump,
    both picks are wrong, and nothing in the bytes says which case holds. Each
    row carries the evidence behind its own pick -- whether a linear walk from
    the entry reaches the site, what precedes the entry, and how many
    `ljmp`/`ajmp` targets lie in between -- rather than an averaged score;
    read those before trusting a row.
  * Nothing here observes hardware. No register is read, written or read
    back; the index registers' *values* at run time are not knowable from
    these bytes, which is why --callers reports literal loads it happens to
    see and reports every other row unresolved.

Read-only: it opens the firmware image for reading and writes nothing.

Usage:
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --bases
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 \
            --callers 0x7421 0x9DEC 0xB5D3 0xE9F5
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers-csv
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import os
import sys

from disasm8051 import OPCODE_LEN, converges_from, mnemonic, paged_target
from trace_xdata_refs import (MOV_DPTR, PD_MARKER, REGIONS, offset_for_runtime,
                              runtime_addr)

PD_REGION = "pd-image"

# The eleven routines ../annotations/pd-xdata-overlap.md 3 and 5.2 name as
# taking DPTR from a base site. Four are decoded there (0x10BC, 0x90CB,
# 0x998B, 0x9180); the other seven were listed as "not yet decoded".
HELPERS = (0x10BC, 0x90CB, 0x998B, 0x9180, 0x998F, 0x9A99, 0x9A71, 0x9A98,
           0x9A3F, 0x9A1B, 0x9987)

# The low-address run pd-xdata-overlap.md 5.2 found in this image: a stride-4
# set of bases, then a second stride-4 set, then the contiguous 0x04A1-0x04A6
# and 0x04A8. Bounded rather than open-ended so --bases stays a statement
# about that run and not a whole-image census.
BASE_RUN = (0x0400, 0x04A8)

# The four 0x04A6 sites this work exists to bound (pd-xdata-overlap.md 3).
DEFAULT_CALLER_SITES = (0x7421, 0x9DEC, 0xB5D3, 0xE9F5)

# Byte templates the term model recognises, longest first. Both are Keil
# library bodies, matched as whole byte runs rather than reconstructed from a
# symbolic interpreter -- an interpreter would happily produce a term for
# code that does something else, which is exactly the overclaim this file is
# trying not to make.
#   mul ab ; add a,dpl ; mov dpl,a ; mov a,b ; addc a,dph ; mov dph,a
#   add a,acc ; add a,dph ; mov dph,a
TERM_TEMPLATES = (
    (bytes.fromhex("a42582f582e5f03583f583"), "{a}×{b}"),
    (bytes.fromhex("25e02583f583"), "0x200×{a}"),
)

# Placeholders for an accumulator or B register the caller supplies. They stay
# unsubstituted through a helper's own decode and are filled in per base site,
# which is the only place the bytes say what is in them.
UNKNOWN_A, UNKNOWN_B = "{a}", "{b}"

RET = 0x22
RETI = 0x32
MOV_B_IMM = bytes((0x75, 0xF0))          # mov b,#imm
MOV_A_IMM = 0x74                          # mov a,#imm
CLR_A = 0xE4                              # clr a
CALL_OPS = (0x12,)                        # lcall; acall is op & 0x1F == 0x11
JMP_OPS = (0x02,)                         # ljmp;  ajmp  is op & 0x1F == 0x01

FRAME_BACK = 32       # bytes of backward anchor sweep for a site's own frame
HELPER_MAX_INSNS = 24  # a leaf helper that has not hit `ret` by here is not one

# Every opcode that leaves a new value in the accumulator. Needed in full,
# because a frame scan that only watched the loads it recognises would report
# `A=R7` for `mov a,r7 ; movx a,@dptr ; mov dptr,#…` -- naming a register the
# access demonstrably does not use.
A_WRITERS = frozenset(
    {0x03, 0x04, 0x13, 0x14, 0x83, 0x84, 0xA4, 0xC4, 0xD4, 0xD6, 0xD7}
    | set(range(0x23, 0x30)) | set(range(0x33, 0x40)) | set(range(0x44, 0x50))
    | set(range(0x54, 0x60)) | set(range(0x64, 0x70)) | set(range(0x74, 0x75))
    | set(range(0x93, 0xA0)) | set(range(0xC5, 0xD0)) | set(range(0xE0, 0xF0))
)

# Opcodes whose destination is the `direct` byte at raw[1] (raw[2] for the
# direct-to-direct `mov`), so `mov b,#imm` is only one of the ways B changes.
DIRECT_DST_OPS = frozenset(
    {0x05, 0x15, 0x42, 0x43, 0x52, 0x53, 0x62, 0x63, 0x75, 0xC5, 0xD5, 0xF5}
    | set(range(0x86, 0x90))
)
B_SFR = 0xF0

# Every opcode that leaves a new value in R0-R7, `mov rN,#imm` excepted --
# that one is the literal load literals_in() is looking for. The register
# number is the opcode's low three bits in all of them.
R_WRITERS = frozenset(
    set(range(0x08, 0x10)) | set(range(0x18, 0x20)) | set(range(0xA8, 0xB0))
    | set(range(0xC8, 0xD0)) | set(range(0xD8, 0xE0)) | set(range(0xF8, 0x100))
)


def pd_verified(d: bytes) -> bool:
    off, magic = PD_MARKER
    return d[off:off + len(magic)] == magic


def pd_bounds():
    lo, hi = next((lo, hi) for name, lo, hi, _, _ in REGIONS if name == PD_REGION)
    return lo, hi


def is_call(op: int) -> bool:
    return op in CALL_OPS or op & 0x1F == 0x11


def is_jmp(op: int) -> bool:
    return op in JMP_OPS or op & 0x1F == 0x01


def branch_target(raw: bytes, addr: int):
    """Runtime target of `raw` at runtime address `addr`, or None.

    Same rule as trace_xdata_refs.call_target(), except that the paged forms
    always resolve here: the PD image is flat and 64 KiB, so every site in it
    has a runtime address and a paged target cannot leave the image."""
    op = raw[0]
    if op in (0x02, 0x12) and len(raw) >= 3:
        return (raw[1] << 8) | raw[2]
    if op & 0x1F in (0x01, 0x11) and len(raw) >= 2:
        return paged_target(op, raw[1], addr)
    return None


def _match_template(d: bytes, i: int):
    for raw, term in TERM_TEMPLATES:
        if d[i:i + len(raw)] == raw:
            return len(raw), term
    return None, None


def walk_helper(d: bytes, entry: int, depth: int = 0, seen: frozenset = frozenset()):
    """Decode the helper at PD runtime `entry` into (terms, listing, note).

    `terms` is the list of symbolic DPTR addends in the order the routine
    applies them, with A and B rendered as whatever the routine last put in
    them ('A'/'B' where the caller supplies it). `note` is empty when every
    byte from the entry to the `ret` was accounted for, and otherwise says
    which instruction the term model does not cover -- that row is
    `unmodelled` and its listing is the whole of what is claimed about it."""
    lo, _ = pd_bounds()
    if entry in seen or depth > 3:
        return [], [], f"unmodelled: tail chain not followed past 0x{entry:04X}"
    seen = seen | {entry}
    terms, listing, note = [], [], ""
    a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
    i = lo + entry
    for _ in range(HELPER_MAX_INSNS):
        n, term = _match_template(d, i)
        if term and not note:
            for j, raw, _ in _insns(d, i, n):
                listing.append((j, raw))
            terms.append(term.format(a=a_sym, b=b_sym))
            # `mul ab` leaves the product in A:B, so neither symbol survives
            # the template; a later term has to re-load them to be named.
            a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
            i += n
            continue
        op = d[i]
        here = i - lo
        raw = d[i:i + OPCODE_LEN[op]]
        listing.append((i, raw))
        if op == RET:
            return terms, listing, note
        if note:
            # Past the first unmodelled instruction nothing is claimed, but the
            # walk keeps going so the row carries a whole routine's listing.
            if is_jmp(op):
                return terms, listing, note
        elif raw[:2] == MOV_B_IMM:
            b_sym = f"0x{raw[2]:02X}"
        elif 0xE8 <= op <= 0xEF:
            a_sym = f"R{op - 0xE8}"
        elif op == MOV_A_IMM:
            a_sym = f"0x{raw[1]:02X}"
        elif op == CLR_A:
            a_sym = "0x00"
        elif is_call(op) or is_jmp(op):
            target = branch_target(raw, here)
            if target is None:
                note = f"unmodelled: unresolvable handoff at 0x{here:04X}"
            else:
                sub_terms, _, sub_note = walk_helper(d, target, depth + 1, seen)
                terms += resolve_terms(sub_terms, a_sym, b_sym)
                note = sub_note
                if is_jmp(op):
                    return terms, listing, note  # tail call: the callee returns
                a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
        else:
            note = (f"unmodelled: 0x{here:04X} `{mnemonic(d, i, here).strip()}` "
                    "is outside the term model")
        i += OPCODE_LEN[op]
    return terms, listing, note or f"unmodelled: no `ret` within {HELPER_MAX_INSNS} instructions"


def _insns(d: bytes, start: int, length: int):
    """The instructions covering d[start:start+length], so a matched template
    lists as the instructions it is rather than as one long byte run."""
    i = start
    while i < start + length:
        n = OPCODE_LEN[d[i]]
        yield i, d[i:i + n], n
        i += n


def frame_of(d: bytes, off: int, back: int = FRAME_BACK):
    """Longest backward linear walk that lands exactly on `off`, as a list of
    (offset, raw) pairs. Empty when no anchor in the window converges, which
    converges_from() already warns is evidence about framing and not proof of
    it -- a site preceded by a dispatch table has no converging anchor and is
    not thereby misframed."""
    best = []
    for b in range(back, 0, -1):
        i = off - b
        if i < 0:
            continue
        run = []
        while i < off:
            run.append((i, d[i:i + OPCODE_LEN[d[i]]]))
            i += OPCODE_LEN[d[i]]
        if i == off and len(run) > len(best):
            best = run
    return best


def literals_in(frame) -> dict:
    """Literal register loads visible in a frame: `mov rN,#imm` directly, and
    the `mov a,#imm ; mov rN,a` pair Keil emits when A is already live. Later
    loads win, since the last one before the site is what reaches it.

    A call inside the frame discards everything found so far: what the callee
    leaves in the register bank is not traced here, so a literal loaded before
    it bounds nothing about the value that reaches the site."""
    out = {}
    pending = None
    for _, raw in frame:
        op = raw[0]
        if is_call(op):
            out, pending = {}, None
        elif 0x78 <= op <= 0x7F:
            out[f"R{op - 0x78}"] = raw[1]
        elif op == MOV_A_IMM:
            pending = raw[1]
        elif op == CLR_A:
            pending = 0x00
        elif 0xF8 <= op <= 0xFF and pending is not None:
            out[f"R{op - 0xF8}"] = pending
        # Anything else that writes rN drops whatever was recorded for it: a
        # literal overwritten by a computed value bounds nothing.
        elif op in R_WRITERS:
            out.pop(f"R{op & 0x07}", None)
            pending = None
        elif op in A_WRITERS:
            pending = None
    return out


def ab_of(frame) -> tuple:
    """What the frame leaves in A and B, as symbols. Same vocabulary
    walk_helper() uses, so a base site's A/B substitute straight into a
    helper's term -- and the same conservatism: an opcode that writes A or B
    without naming a source this model knows resets the symbol to unknown
    rather than letting a stale one through."""
    a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
    for _, raw in frame:
        op = raw[0]
        if raw[:2] == MOV_B_IMM:
            b_sym = f"0x{raw[2]:02X}"
        elif is_call(op) or op in (0xA4, 0x84) \
                or (op in DIRECT_DST_OPS and raw[1] == B_SFR) \
                or (op == 0x85 and raw[2] == B_SFR):
            b_sym = UNKNOWN_B

        if 0xE8 <= op <= 0xEF:
            a_sym = f"R{op - 0xE8}"
        elif op == MOV_A_IMM:
            a_sym = f"0x{raw[1]:02X}"
        elif op == CLR_A:
            a_sym = "0x00"
        elif op in A_WRITERS or is_call(op):
            a_sym = UNKNOWN_A
    return a_sym, b_sym


def chain_from(d: bytes, off: int, a_sym: str, b_sym: str, max_insns: int = 12):
    """Follow the run of index helpers a base site hands DPTR to, as
    (helper entries, term list, stop reason).

    A site rarely applies one term. ../annotations/pd-xdata-overlap.md 3.2 has
    three stacked calls before the `movx`, so reporting only the first handoff
    would understate the address by two terms. The run is followed only
    through instructions the term model covers -- a register load or another
    modelled helper -- and the reason it stopped is reported alongside it, so
    a truncated chain reads as truncated. Notably it stops at the `push dph`
    of 3.1's save-and-restore detour: DPTR surviving a stack round trip is
    control flow, and this is not a control-flow recovery tool."""
    lo, _ = pd_bounds()
    helpers, terms = [], []
    i = off + OPCODE_LEN[d[off]]
    for _ in range(max_insns):
        op = d[i]
        raw = d[i:i + OPCODE_LEN[op]]
        here = i - lo
        if op in (0xE0, 0xF0):
            return helpers, terms, "movx: DPTR dereferenced here"
        if op == MOV_DPTR:
            return helpers, terms, "DPTR reloaded"
        if is_call(op) or is_jmp(op):
            target = branch_target(raw, here)
            if target is None:
                return helpers, terms, f"unresolvable handoff at 0x{here:04X}"
            sub_terms, _, note = walk_helper(d, target)
            helpers.append(target)
            if note:
                return helpers, terms, f"0x{target:04X} is {note}"
            terms += resolve_terms(sub_terms, a_sym, b_sym)
            if is_jmp(op):
                return helpers, terms, f"tail call into 0x{target:04X}"
            a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
        elif raw[:2] == MOV_B_IMM:
            b_sym = f"0x{raw[2]:02X}"
        elif 0xE8 <= op <= 0xEF:
            a_sym = f"R{op - 0xE8}"
        elif op == MOV_A_IMM:
            a_sym = f"0x{raw[1]:02X}"
        elif op == CLR_A:
            a_sym = "0x00"
        else:
            return helpers, terms, f"`{mnemonic(d, i, here).strip()}` at 0x{here:04X}"
        i += OPCODE_LEN[op]
    return helpers, terms, f"{max_insns}-instruction window ended"


def resolve_terms(terms, a_sym: str, b_sym: str):
    """Substitute a frame's A and B into a helper's term list. Placeholder
    substitution rather than string replacement, because a literal `0xBA` in
    one symbol would otherwise be rewritten by the other's pass."""
    return [t.format(a=a_sym, b=b_sym) for t in terms]


def base_sites(d: bytes):
    """Every PD-image `MOV DPTR,#imm16` with an immediate in BASE_RUN, as
    dicts. `terms` is the chain of helper terms with the site's own A/B
    substituted, and `stopped` says what ended the chain -- read them
    together, since a short chain and a complete one look alike otherwise."""
    lo, hi = pd_bounds()
    rows = []
    for i in range(lo, hi - 2):
        if d[i] != MOV_DPTR:
            continue
        base = (d[i + 1] << 8) | d[i + 2]
        if not BASE_RUN[0] <= base <= BASE_RUN[1]:
            continue
        a_sym, b_sym = ab_of(frame_of(d, i))
        helpers, terms, stopped = chain_from(d, i, a_sym, b_sym)
        onto, over = converges_from(d, i)
        rows.append({
            "base": base, "file_offset": i, "runtime": runtime_addr(i, True),
            "helpers": helpers, "frame_onto": onto, "frame_over": over,
            "a": a_sym, "b": b_sym, "terms": terms, "stopped": stopped,
        })
    return rows


def branch_index(d: bytes):
    """Byte scan of the PD image for the four direct branch families, as
    (call targets, jump targets) each mapping runtime target -> [file offsets].

    Unaligned, so both maps over-count; see this module's preamble."""
    lo, hi = pd_bounds()
    calls, jumps = {}, {}
    for i in range(lo, hi - 2):
        op = d[i]
        if not (is_call(op) or is_jmp(op)):
            continue
        here = i - lo
        raw = d[i:i + OPCODE_LEN[op]]
        target = branch_target(raw, here)
        if target is None:
            continue
        (calls if is_call(op) else jumps).setdefault(target, []).append(i)
    return calls, jumps


def reaches(d: bytes, entry: int, site: int):
    """Does a linear walk from PD runtime `entry` arrive at `site` without
    returning first? (bool, reason).

    `ret`/`reti` is the only break treated as decisive: a routine's forward
    `sjmp`/`ljmp` over a branch is ordinary and breaking on it would reject
    real entries (0x9D51 contains an `ljmp` at 0x9D9C, 0x50 bytes before its
    0x9DEC site). This is linear extent, not reachability -- it says the two
    addresses are in one `ret`-delimited run of bytes, not that control ever
    gets from one to the other."""
    lo, _ = pd_bounds()
    i = lo + entry
    while i < lo + site:
        if d[i] in (RET, RETI):
            return False, f"`ret` at 0x{i - lo:04X}"
        i += OPCODE_LEN[d[i]]
    if i != lo + site:
        return False, "the walk steps over the site"
    return True, "reaches the site with no intervening `ret`"


def is_entry_shaped(d: bytes, entry: int):
    """Does `entry` look like a routine entry rather than a label inside one?
    (bool, the instruction a backward walk puts before it).

    The test is that some anchor decodes into `entry` and the instruction it
    lands on is an unconditional flow break: a routine begins where the
    previous one stopped. It is how both phantoms around PD `0x7421` give
    themselves away -- `lcall 0x7420` is preceded by `mov b,#0x60`, and
    `acall 0x7415` points at the operand byte of an `add a,#0x42`, which no
    anchor reaches at all.

    The failure direction, since it is the one that costs a real answer: a
    genuine entry sitting immediately after a data table has no converging
    anchor and is rejected here. That is a miss, not a refutation, and it is
    why --callers prints the byte-scan pick beside this one instead of
    replacing it."""
    lo, _ = pd_bounds()
    frame = frame_of(d, lo + entry)
    if not frame:
        return False, "no anchor decodes into it"
    off, raw = frame[-1]
    op = raw[0]
    flow_break = op in (RET, RETI, 0x02, 0x80) or op & 0x1F == 0x01
    return flow_break, mnemonic(d, off, off - lo).strip()


def caller_rows(d: bytes, sites):
    """For each PD runtime site: the entries it is attributed to, and one row
    per site calling each.

    Two entries per site, not one, because the byte scan's nearest preceding
    call target is only an *upper* bound and can be a phantom -- `90 00 12 74
    20` reads as an `lcall 0x7420` that one anchor in 24 syncs onto. The
    `containing` pick adds the two structural tests above; it is still a
    heuristic, but it is the one whose failure mode is named. Reporting both
    is the byte-scan-bound-beside-anchored-count pairing
    audit_call_targets.py uses, for the same reason: neither settles alone."""
    lo, _ = pd_bounds()
    calls, jumps = branch_index(d)
    out = []
    for site in sites:
        picks = []
        candidates = sorted((e for e in calls if e <= site), reverse=True)
        containing = next((e for e in candidates
                           if reaches(d, e, site)[0] and is_entry_shaped(d, e)[0]
                           and any(converges_from(d, o)[0] for o in calls[e])), None)
        for label, entry in (("byte-scan", candidates[0] if candidates else None),
                             ("containing", containing)):
            if entry is not None and entry not in [p["entry"] for p in picks]:
                picks.append({"label": label, "entry": entry,
                              "reaches": reaches(d, entry, site)[1],
                              "entry_shape": is_entry_shaped(d, entry)[1]})
        for pick in picks:
            entry = pick["entry"]
            pick["entry_gap_jmps"] = sum(1 for t in jumps if entry < t <= site)
            rows = []
            for kind, index in (("call", calls), ("tail-jump", jumps)):
                for off in index.get(entry, []):
                    onto, over = converges_from(d, off)
                    lits = literals_in(frame_of(d, off))
                    rows.append({
                        "site": site, "entry": entry, "kind": kind,
                        "file_offset": off, "runtime": off - lo,
                        "opcode": mnemonic(d, off, off - lo).strip(),
                        "frame_onto": onto, "frame_over": over,
                        "literals": lits,
                        # A frame that names no index register bounds nothing.
                        # That is the expected row, not a broken one.
                        "status": "literal index loads found" if lits else "unresolved",
                    })
            pick["rows"] = sorted(rows, key=lambda r: r["file_offset"])
        out.append({"site": site, "picks": picks})
    return out


def fmt_terms(terms, note: str = "") -> str:
    """The term sum as a reader sees it, with any still-unsubstituted
    placeholder printed as the bare register name it stands for."""
    if note:
        return note
    return " + ".join(t.format(a="A", b="B") for t in terms) if terms else "(no term)"


def print_helpers(d: bytes) -> None:
    lo, _ = pd_bounds()
    print(f"{len(HELPERS)} helper entries named by ../annotations/pd-xdata-overlap.md "
          "3 and 5.2\n")
    for entry in HELPERS:
        terms, listing, note = walk_helper(d, entry)
        head = note if note else f"DPTR += {fmt_terms(terms)}"
        print(f"0x{entry:04X}  (file 0x{lo + entry:05X})  {head}")
        for i, raw in listing:
            print(f"    0x{i - lo:04x}  {raw.hex():<8} {mnemonic(d, i, i - lo)}")
        print()


def print_bases(d: bytes) -> None:
    rows = base_sites(d)
    per_base = {}
    for r in rows:
        per_base.setdefault(r["base"], []).append(r)
    print(f"{len(rows)} PD-image MOV DPTR site(s) with a base in "
          f"0x{BASE_RUN[0]:04X}-0x{BASE_RUN[1]:04X}, over {len(per_base)} base(s)\n")
    for base in sorted(per_base):
        print(f"0x{base:04X}: {len(per_base[base])} site(s)")
        for r in per_base[base]:
            chain = " ".join(f"0x{h:04X}" for h in r["helpers"]) or "-"
            print(f"    file 0x{r['file_offset']:05X}  runtime 0x{r['runtime']:04X}  "
                  f"frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']}  "
                  f"A={r['a'].format(a='A')} B={r['b'].format(b='B')}  -> {chain}")
            print(f"      DPTR = 0x{base:04X} + {fmt_terms(r['terms'])} "
                  f"[chain ends at {r['stopped']}]")
        print()


def print_callers(d: bytes, sites) -> None:
    for group in caller_rows(d, sites):
        print(f"PD runtime 0x{group['site']:04X}")
        if not group["picks"]:
            print("    no preceding call target found by this byte scan\n")
            continue
        for pick in group["picks"]:
            print(f"  {pick['label']} entry 0x{pick['entry']:04X}: {pick['reaches']}; "
                  f"preceded by {pick['entry_shape']}; "
                  f"{pick['entry_gap_jmps']} jump target(s) in between")
            for r in pick["rows"]:
                lits = ", ".join(f"{k}=#0x{v:02X}"
                                 for k, v in sorted(r["literals"].items()))
                print(f"    file 0x{r['file_offset']:05X}  runtime 0x{r['runtime']:04X}  "
                      f"{r['kind']:<9} {r['opcode']:<16} "
                      f"frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']}  "
                      f"{lits or r['status']}")
        print()


def write_helpers_csv(d: bytes) -> None:
    lo, _ = pd_bounds()
    w = csv.writer(sys.stdout)
    w.writerow(["entry", "file_offset", "bytes", "terms", "tail_target", "unmodelled"])
    for entry in HELPERS:
        terms, listing, note = walk_helper(d, entry)
        tail = ""
        if listing:
            off, last = listing[-1]
            if is_call(last[0]) or is_jmp(last[0]):
                t = branch_target(last, off - lo)
                tail = f"0x{t:04X}" if t is not None else ""
        w.writerow([f"0x{entry:04X}", f"0x{lo + entry:05X}",
                    sum(len(raw) for _, raw in listing),
                    "" if note else fmt_terms(terms),
                    tail, "yes" if note else "no"])


def write_callers_csv(d: bytes, sites) -> None:
    w = csv.writer(sys.stdout)
    w.writerow(["site", "entry", "entry_pick", "entry_reaches_site",
                "entry_preceded_by", "entry_gap_jmps", "caller_file_offset",
                "caller_runtime", "kind", "opcode", "frame_onto", "frame_over",
                "literals", "status"])
    for group in caller_rows(d, sites):
        for pick in group["picks"]:
            for r in pick["rows"]:
                w.writerow([f"0x{r['site']:04X}", f"0x{pick['entry']:04X}",
                            pick["label"], pick["reaches"], pick["entry_shape"],
                            pick["entry_gap_jmps"],
                            f"0x{r['file_offset']:05X}", f"0x{r['runtime']:04X}",
                            r["kind"], r["opcode"], r["frame_onto"], r["frame_over"],
                            " ".join(f"{k}=#0x{v:02X}"
                                     for k, v in sorted(r["literals"].items())),
                            r["status"]])


# --- self-test -------------------------------------------------------------
#
# Every expectation below is transcribed from text already committed to this
# repository, so the tool cannot silently disagree with the annotations that
# cite it. Byte runs come from the `r2 -a 8051` listings in
# ../annotations/pd-xdata-overlap.md 3; the term strings from the same
# section's prose; the site offsets and per-base counts from 1 and 5.2 of
# that file, which trace_xdata_refs.py produced.

# pd-xdata-overlap.md 3 and 3.1 transcribe these two helper bodies in full.
HELPER_BYTES = {
    0x10BC: "a42582f582e5f03583f58322",
    0x90CB: "1210bceb25e02583f58322",
}

# The term claims those sections make in prose: "0x10BC ... is DPTR += A x B"
# (3), "0x90CB is 0x10BC plus one more term, DPH += 2 x R3" (3.1), "0x998B is
# 0x90CB's twin, 0x10BC followed by DPH += 2 x R7" (3.3), and "0x9180 is
# mov b,#0x1f ; ljmp 0x10bc, i.e. DPTR += A x 0x1F" (3.1).
HELPER_TERMS = {
    0x10BC: "A×B",
    0x90CB: "A×B + 0x200×R3",
    0x998B: "A×B + 0x200×R7",
    0x9180: "A×0x1F",
}

# pd-xdata-overlap.md 3's four site offsets, as trace_xdata_refs.py reports
# them, and 1/5.2's per-base PD site counts.
SITE_OFFSETS = {0x7421: 0x27421, 0x9DEC: 0x29DEC, 0xB5D3: 0x2B5D3, 0xE9F5: 0x2E9F5}
BASE_COUNTS = {0x04A6: 4, 0x04A3: 5}

HELPERS_CSV = "../annotations/pd-index-helpers.csv"
CALLERS_CSV = "../annotations/pd-index-callers.csv"
DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"


def _csv_rows(path: str):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, path), newline="") as fh:
        return list(csv.DictReader(fh))


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
        off, magic = PD_MARKER
        print(f"  !   no {magic.decode()!r} marker at file 0x{off:05X}")
        return 1

    for entry, want in HELPER_BYTES.items():
        got = bytes(b for _, raw in walk_helper(d, entry)[1] for b in raw).hex()
        check(got == want, f"0x{entry:04X} body is `{want}` (got `{got}`)")

    for entry, want in HELPER_TERMS.items():
        terms, _, note = walk_helper(d, entry)
        got = fmt_terms(terms, note)
        check(got == want, f"0x{entry:04X} adds {want} to DPTR (got {got})")

    for runtime, want in SITE_OFFSETS.items():
        got = offset_for_runtime(runtime, PD_REGION)
        raw = d[want:want + 3]
        check(got == want and raw == bytes((MOV_DPTR, 0x04, 0xA6)),
              f"PD runtime 0x{runtime:04X} is file 0x{want:05X} and holds "
              f"`mov dptr,#0x04a6` (got 0x{got:05X}, `{raw.hex()}`)")

    rows = base_sites(d)
    for base, want in BASE_COUNTS.items():
        got = sum(1 for r in rows if r["base"] == base)
        check(got == want, f"--bases finds {want} site(s) for 0x{base:04X} (got {got})")

    want_helpers = _csv_rows(HELPERS_CSV)
    check(len(want_helpers) == len(HELPERS),
          f"{HELPERS_CSV} has one row per helper ({len(HELPERS)}; "
          f"got {len(want_helpers)})")
    for row in want_helpers:
        entry = int(row["entry"], 16)
        terms, _, note = walk_helper(d, entry)
        got = "" if note else fmt_terms(terms)
        check(got == row["terms"],
              f"{row['entry']} terms match the committed CSV "
              f"(`{row['terms']}`, got `{got}`)")
        check((row["unmodelled"] == "yes") == bool(note),
              f"{row['entry']} unmodelled={row['unmodelled']} matches the decode")

    want_callers = _csv_rows(CALLERS_CSV)
    got_callers = sum(len(p["rows"]) for g in caller_rows(d, DEFAULT_CALLER_SITES)
                      for p in g["picks"])
    check(len(want_callers) == got_callers,
          f"{CALLERS_CSV} has {got_callers} row(s) for the four 0x04A6 sites "
          f"(got {len(want_callers)} committed)")

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the committed "
              "annotations or CSVs")
    else:
        print(f"self-test passed: the helper bodies and terms match "
              f"pd-xdata-overlap.md 3, the four 0x04A6 sites sit where "
              f"trace_xdata_refs.py puts them, and both CSVs regenerate "
              f"unchanged (PD image at file 0x{lo:05X})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--helpers", action="store_true",
                    help="decode each named index helper and report its DPTR term(s)")
    ap.add_argument("--bases", action="store_true",
                    help="every PD site whose MOV DPTR immediate is in the low base run")
    ap.add_argument("--callers", nargs="+", metavar="ADDR",
                    help="bound the caller set of these PD runtime sites, e.g. 0x7421")
    ap.add_argument("--helpers-csv", action="store_true",
                    help="write the helper table as CSV on stdout")
    ap.add_argument("--callers-csv", action="store_true",
                    help="write the caller table for the four 0x04A6 sites as CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the decode against the committed annotations and CSVs")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    fw = args.firmware or os.path.join(here, DEFAULT_FIRMWARE)
    if args.self_test:
        return self_test(fw)
    if not (args.helpers or args.bases or args.callers
            or args.helpers_csv or args.callers_csv):
        ap.error("pick a mode: --helpers, --bases, --callers, --helpers-csv, "
                 "--callers-csv or --self-test")

    d = open(fw, "rb").read()
    if not pd_verified(d):
        off, magic = PD_MARKER
        # stderr, so that a --*-csv redirect stays a clean CSV.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "0x20000-0x2FFFF is not the image this tool decodes",
              file=sys.stderr)
        return 1

    if args.helpers:
        print_helpers(d)
    if args.bases:
        print_bases(d)
    if args.callers:
        print_callers(d, [int(a, 16) for a in args.callers])
    if args.helpers_csv:
        write_helpers_csv(d)
    if args.callers_csv:
        write_callers_csv(d, DEFAULT_CALLER_SITES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
