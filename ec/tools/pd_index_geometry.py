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

Five modes, in increasing order of how much they assume:

  --helpers   Decode each named helper entry to its `ret`, following a tail
              `ljmp`/`ajmp` and stepping into an `lcall`, and report the
              symbolic term(s) it adds to DPTR. The term model is five byte
              templates (Keil's `DPTR += A*B` and `DPH += 2*A`, and the three
              `base + A*B` forms that build a pointer from an immediate base)
              plus the instructions that load A and B; a routine whose body is
              not built out of those is reported `unmodelled` with its listing
              rather than force-fitted into a term. This mode assumes only
              that the entry address is an instruction boundary. With no
              argument it decodes the eleven named helpers; with addresses it
              decodes those instead, which is how a mid-routine entry such as
              0x34D9 gets a term chain.
  --bases     Every PD-image `MOV DPTR,#imm16` whose immediate is in a base
              span, with the chain of helpers it hands DPTR to, their term
              sum resolved against the A/B the site's own frame sets, and what
              ended the chain. The span defaults to the low run and can be
              widened (`--bases all`, `--bases 0x0800-0x08FF`); the header line
              always names the span it actually walked. The frame comes from
              the longest backward walk that converges on the site
              (disasm8051.converges_from()'s idiom), so A and B are "as decoded
              from an anchor", not "as executed".
  --sites     The same decode anchored on PD runtime addresses the caller
              names rather than on a `MOV DPTR` opcode, for the sites whose
              base never appears as a `MOV DPTR` immediate because it is added
              as `add a,#imm` inside the multiply itself. Unlike --bases the
              chain is followed across a `movx`: the access consumes the
              pointer but does not change DPTR, and at these sites the
              arithmetic that matters comes after it.
  --strides   Census of the stride constants the term decode resolves over a
              span: how many sites and which bases produce each, and how many
              sites in the span resolve no stride at all. A stride absent from
              the census was not resolved by this method over that span, which
              is not the same as it not being there.
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
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers 0x34D9 0x578E
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --bases
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --bases all
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --sites 0xC2FA 0xDA9B
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --strides all
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 \
            --callers 0x7421 0x9DEC 0xB5D3 0xE9F5
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers-csv
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --strides-csv all
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import os
import re
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
# and 0x04A8. It is the *default* span rather than the only one, so --bases
# with no argument stays the statement about that run the annotations quote;
# --bases all is the whole-image census.
BASE_RUN = (0x0400, 0x04A8)
WHOLE_IMAGE = (0x0000, 0xFFFF)

# The four 0x04A6 sites this work exists to bound (pd-xdata-overlap.md 3).
DEFAULT_CALLER_SITES = (0x7421, 0x9DEC, 0xB5D3, 0xE9F5)

# Byte templates the term model recognises, longest first. All five are Keil
# library bodies, matched as whole byte runs rather than reconstructed from a
# symbolic interpreter -- an interpreter would happily produce a term for
# code that does something else, which is exactly the overclaim this file is
# trying not to make. A `..` stands for one byte the run does not pin; the
# only bytes left open are the immediate halves of a base address, which the
# match reads out and substitutes for {base}.
#
# Three of them *replace* DPTR (or build a generic pointer in R2:R1) from an
# immediate base instead of advancing whatever it held, so their term carries
# the REBASE marker below. They were transcribed from the sites
# ../annotations/ec-0x07d0-sites.md 4 names: 0x34D9 and 0xC2FA for the first,
# helper 0x5950 (called from 0xDA9B) for the second, 0x578E for the third.
TERM_TEMPLATES = (
    # mul ab ; add a,dpl ; mov dpl,a ; mov a,b ; addc a,dph ; mov dph,a
    ("a42582f582e5f03583f583", "{a}×{b}"),
    # mul ab ; add a,#lo ; mov dpl,a ; clr a ; addc a,#hi ; mov dph,a
    ("a424..f582e434..f583", "=DPTR ← {base} + {a}×{b}"),
    # add a,#lo ; mov dpl,a ; clr a ; addc a,#hi ; mov dph,a -- the same 16-bit
    # add with no multiply, so the addend is A alone. It drops B, which means
    # a caller that reached it through `mul ab` loses the product's high byte;
    # 0xDA9B does exactly that, and the annotation says so rather than assuming
    # the index is small enough for it not to matter.
    ("24..f582e434..f583", "=DPTR ← {base} + {a}"),
    # mul ab ; add a,#lo ; mov r1,a ; mov a,#hi ; addc a,b
    ("a424..f974..35f0", "=R2:R1 ← {base} + {a}×{b}"),
    # add a,acc ; add a,dph ; mov dph,a
    ("25e02583f583", "0x200×{a}"),
)

# A term beginning with this replaces every term before it instead of adding
# to them: the templates that build a pointer from an immediate base discard
# whatever DPTR held at the site.
REBASE = "="

# Placeholders for an accumulator or B register the caller supplies. They stay
# unsubstituted through a helper's own decode and are filled in per base site,
# which is the only place the bytes say what is in them.
UNKNOWN_A, UNKNOWN_B = "{a}", "{b}"

RET = 0x22
RETI = 0x32
MOV_B_IMM = bytes((0x75, 0xF0))          # mov b,#imm
MOV_A_IMM = 0x74                          # mov a,#imm
CLR_A = 0xE4                              # clr a
MOVX_A_DPTR = 0xE0                        # movx a,@dptr
MOVX_DPTR_A = 0xF0                        # movx @dptr,a
MUL_AB = 0xA4                             # mul ab
CALL_OPS = (0x12,)                        # lcall; acall is op & 0x1F == 0x11
JMP_OPS = (0x02,)                         # ljmp;  ajmp  is op & 0x1F == 0x01

FRAME_BACK = 32       # bytes of backward anchor sweep for a site's own frame
HELPER_MAX_INSNS = 24  # a leaf helper that has not hit `ret` by here is not one
SITE_WINDOW = 16      # instructions --sites decodes forward from a named anchor
STRIDE_BASES_SHOWN = 12  # bases per --strides line before the text view elides

# The multiplier in a resolved term, e.g. `R7×0x5E`. The page term is written
# `0x200×R7` and deliberately does not match: it is the same register's page
# stride, not a second record size.
STRIDE_RE = re.compile(r"×0x([0-9A-F]+)")
REBASE_BASE_RE = re.compile(re.escape(REBASE) + r"[^←]*← 0x([0-9A-F]{4})")
PAGE_TERM = "0x200×"
UNRESOLVED_STRIDE = "unresolved"

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


def parse_span(arg):
    """`None` -> None, a (lo, hi) tuple -> itself, `all` -> the whole 16-bit
    space, `0xLO-0xHI` -> that span. Tuples pass through so argparse's `const`
    can be the default span itself."""
    if arg is None or isinstance(arg, tuple):
        return arg
    if arg.lower() == "all":
        return WHOLE_IMAGE
    lo, _, hi = arg.partition("-")
    if not hi:
        raise ValueError(f"span {arg!r} is not `all` or 0xLO-0xHI")
    lo, hi = int(lo, 16), int(hi, 16)
    if not 0 <= lo <= hi <= 0xFFFF:
        raise ValueError(f"span {arg!r} is not inside 0x0000-0xFFFF")
    return lo, hi


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


def product_sym(a_sym: str, b_sym: str) -> str:
    """What a bare `mul ab` -- one that is not the head of a template -- leaves
    in A: the low half of the product, the high half having gone to B. The
    base templates such a multiply feeds take A alone, so writing the term as
    `low(...)` is what keeps a wrapped address from reading as an exact one."""
    return f"low({a_sym}×{b_sym})"


def _match_template(d: bytes, i: int):
    """(length, term) for the first template matching at `i`, else (None, None).

    A template's two open bytes are the low and high halves of an immediate
    base, in that order -- the order Keil emits them, `add a,#lo` before
    `addc a,#hi` -- so they are read out as one 16-bit base rather than left
    as two loose numbers."""
    for pattern, term in TERM_TEMPLATES:
        n = len(pattern) // 2
        if len(d) - i < n:
            continue
        open_bytes = []
        for k in range(n):
            want = pattern[2 * k:2 * k + 2]
            if want == "..":
                open_bytes.append(d[i + k])
            elif d[i + k] != int(want, 16):
                break
        else:
            if open_bytes:
                base = (open_bytes[1] << 8) | open_bytes[0]
                term = term.replace("{base}", f"0x{base:04X}")
            return n, term
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
        elif op in (MOVX_A_DPTR, MOVX_DPTR_A):
            # A `movx` consumes the pointer but does not change DPTR, so the
            # term chain carries across it. `movx a,@dptr` does clobber A, and
            # what it loaded is not knowable from these bytes.
            if op == MOVX_A_DPTR:
                a_sym = UNKNOWN_A
        elif op == MUL_AB:
            a_sym, b_sym = product_sym(a_sym, b_sym), UNKNOWN_B
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


def chain_from(d: bytes, start: int, a_sym: str, b_sym: str, max_insns: int = 12,
               through_movx: bool = False):
    """Follow the run of index helpers a base site hands DPTR to, as
    (helper entries, term list, stop reason). `start` is the file offset of the
    first instruction to decode, i.e. the one *after* the site's `MOV DPTR`.

    A site rarely applies one term. ../annotations/pd-xdata-overlap.md 3.2 has
    three stacked calls before the `movx`, so reporting only the first handoff
    would understate the address by two terms. The run is followed only
    through instructions the term model covers -- a register load or another
    modelled helper -- and the reason it stopped is reported alongside it, so
    a truncated chain reads as truncated. Notably it stops at the `push dph`
    of 3.1's save-and-restore detour: DPTR surviving a stack round trip is
    control flow, and this is not a control-flow recovery tool.

    `through_movx` keeps the walk going across the access instead of stopping
    there. DPTR survives a `movx` unchanged, so continuing is arithmetic and
    not a guess -- but for a base site the access is the end of what that base
    was loaded for, which is why it is off by default and only --sites, where
    the caller named the address deliberately, turns it on."""
    lo, _ = pd_bounds()
    helpers, terms = [], []
    i = start
    for _ in range(max_insns):
        # An inline template, as opposed to one reached through a call: the
        # 0x07D0 sites of ../annotations/ec-0x07d0-sites.md 4 multiply in place
        # rather than calling 0x10BC, and stopping at their `mul ab` would
        # report no term for arithmetic the model does cover.
        n, term = _match_template(d, i)
        if term:
            terms.append(term.format(a=a_sym, b=b_sym))
            a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
            i += n
            continue
        op = d[i]
        raw = d[i:i + OPCODE_LEN[op]]
        here = i - lo
        if op in (MOVX_A_DPTR, MOVX_DPTR_A):
            if not through_movx:
                return helpers, terms, "movx: DPTR dereferenced here"
            if op == MOVX_A_DPTR:
                a_sym = UNKNOWN_A
            i += OPCODE_LEN[op]
            continue
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
        elif op == MUL_AB:
            a_sym, b_sym = product_sym(a_sym, b_sym), UNKNOWN_B
        else:
            return helpers, terms, f"`{mnemonic(d, i, here).strip()}` at 0x{here:04X}"
        i += OPCODE_LEN[op]
    return helpers, terms, f"{max_insns}-instruction window ended"


def resolve_terms(terms, a_sym: str, b_sym: str):
    """Substitute a frame's A and B into a helper's term list. Placeholder
    substitution rather than string replacement, because a literal `0xBA` in
    one symbol would otherwise be rewritten by the other's pass."""
    return [t.format(a=a_sym, b=b_sym) for t in terms]


def base_sites(d: bytes, span=BASE_RUN):
    """Every PD-image `MOV DPTR,#imm16` with an immediate in `span`, as dicts.
    `terms` is the chain of helper terms with the site's own A/B substituted,
    and `stopped` says what ended the chain -- read them together, since a
    short chain and a complete one look alike otherwise.

    The span is a parameter and not the module constant, so widening it is a
    caller's decision: every count the annotations quote comes from BASE_RUN
    and has to stay reproducible from the default."""
    lo, hi = pd_bounds()
    rows = []
    for i in range(lo, hi - 2):
        if d[i] != MOV_DPTR:
            continue
        base = (d[i + 1] << 8) | d[i + 2]
        if not span[0] <= base <= span[1]:
            continue
        a_sym, b_sym = ab_of(frame_of(d, i))
        helpers, terms, stopped = chain_from(d, i + OPCODE_LEN[MOV_DPTR],
                                             a_sym, b_sym)
        onto, over = converges_from(d, i)
        rows.append({
            "base": base, "file_offset": i, "runtime": runtime_addr(i, True),
            "helpers": helpers, "frame_onto": onto, "frame_over": over,
            "a": a_sym, "b": b_sym, "terms": terms, "stopped": stopped,
        })
    return rows


def site_rows(d: bytes, addrs, max_insns: int = SITE_WINDOW):
    """The same decode as base_sites(), anchored on PD runtime addresses the
    caller names. One row per address, each carrying the window it walked so
    an unmodelled row is read off its own listing rather than taken on trust.

    An address that begins with `MOV DPTR,#imm16` is treated exactly as a base
    site; any other address is decoded from its first byte, which is how a
    mid-routine anchor gets a chain at all. Nothing checks that the address is
    an instruction boundary -- the caller asserts that by naming it, and the
    listing is there so a wrong assertion is visible."""
    lo, _ = pd_bounds()
    rows = []
    for addr in addrs:
        i = lo + addr
        base = (d[i + 1] << 8) | d[i + 2] if d[i] == MOV_DPTR else None
        start = i + OPCODE_LEN[MOV_DPTR] if base is not None else i
        a_sym, b_sym = ab_of(frame_of(d, i))
        helpers, terms, stopped = chain_from(d, start, a_sym, b_sym, max_insns,
                                             through_movx=True)
        onto, over = converges_from(d, i)
        listing, j = [], i
        for _ in range(max_insns):
            listing.append((j, d[j:j + OPCODE_LEN[d[j]]]))
            j += OPCODE_LEN[d[j]]
        rows.append({
            "addr": addr, "base": base, "file_offset": i,
            "helpers": helpers, "frame_onto": onto, "frame_over": over,
            "a": a_sym, "b": b_sym, "terms": terms, "stopped": stopped,
            "listing": listing,
        })
    return rows


def effective_terms(terms):
    """The terms that survive, with A and B rendered as the bare register names
    they stand for. A REBASE term drops everything before it, since the pointer
    those terms built no longer exists once an immediate base replaces it --
    which is why the census reads this and not the raw list."""
    out = []
    for term in terms:
        term = term.format(a="A", b="B")
        if term.startswith(REBASE):
            out = [term[len(REBASE):]]
        else:
            out.append(term)
    return out


def effective_base(row) -> int:
    """The base the chain actually indexes from: the site's `MOV DPTR`
    immediate, unless a REBASE term replaced it with an immediate of its own.
    Without this the census would file 0xC2FA's array under 0x07D0, which is
    the index it reads, not the base it indexes."""
    for term in reversed(row["terms"]):
        m = REBASE_BASE_RE.match(term)
        if m:
            return int(m.group(1), 16)
    return row["base"]


def stride_census(d: bytes, span):
    """Which stride constants the term decode resolves over `span`, as
    (per-stride rows, site total). Each row is one constant with the sites and
    effective bases that produced it, and how many of those sites also apply
    the `0x200×` page term; `UNRESOLVED_STRIDE` collects the sites whose chain
    resolved no `×0xNN` term at all. A site resolving two strides is counted
    under both.

    A constant missing from the census was not resolved *by this method over
    this span*. The 0x07B9 retraction in ../../docs/findings.md 4c is the
    standing reminder of what a zero from a static scan is worth."""
    per = {}
    rows = base_sites(d, span)
    for r in rows:
        found, page = set(), False
        for term in effective_terms(r["terms"]):
            found.update(STRIDE_RE.findall(term))
            page = page or PAGE_TERM in term
        for stride in found or {UNRESOLVED_STRIDE}:
            bases, paged = per.setdefault(stride, (set(), []))
            bases.add(effective_base(r))
            paged.append(page)
    out = [{"stride": s, "sites": len(paged), "bases": sorted(bases),
            "paged": sum(paged)}
           for s, (bases, paged) in per.items()]
    out.sort(key=lambda x: (x["stride"] == UNRESOLVED_STRIDE, -x["sites"],
                            x["stride"]))
    return out, len(rows)


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
    placeholder printed as the bare register name it stands for. A REBASE term
    drops everything before it, since the pointer those terms built no longer
    exists once an immediate base replaces it."""
    if note:
        return note
    out = effective_terms(terms)
    return " + ".join(out) if out else "(no term)"


def rebased(terms) -> bool:
    """Does the chain end up on a pointer of its own rather than on an offset
    from the site's `MOV DPTR` base? True once any REBASE term has applied."""
    return any(t.startswith(REBASE) for t in terms)


def fmt_address(terms, base=None, note: str = "") -> str:
    """The address line as a reader sees it: `DPTR += ...` for a helper's
    addend, `DPTR = <base> + ...` for a site's, and whatever destination a
    rebasing term names for itself. The last of those matters -- one of the
    base templates lands in R2:R1 and never touches DPTR, and labelling it
    `DPTR` would be the sort of almost-right this file exists not to print."""
    body = fmt_terms(terms, note)
    if note or rebased(terms):
        return body
    return f"DPTR += {body}" if base is None else f"DPTR = 0x{base:04X} + {body}"


def print_helpers(d: bytes, entries=None) -> None:
    lo, _ = pd_bounds()
    if entries is None:
        entries = HELPERS
        print(f"{len(HELPERS)} helper entries named by "
              "../annotations/pd-xdata-overlap.md 3 and 5.2\n")
    else:
        print(f"{len(entries)} helper entry/entries named on the command line\n")
    for entry in entries:
        terms, listing, note = walk_helper(d, entry)
        # Terms *and* a note is the ordinary case for a mid-routine entry that
        # finishes its arithmetic and then tail-jumps into something else: the
        # terms are resolved, the tail is not, and printing only the note would
        # throw away the half that is known.
        head = fmt_address(terms) if terms else ""
        head = f"{head}; {note}" if head and note else head or note
        print(f"0x{entry:04X}  (file 0x{lo + entry:05X})  {head}")
        for i, raw in listing:
            print(f"    0x{i - lo:04x}  {raw.hex():<8} {mnemonic(d, i, i - lo)}")
        print()


def fmt_span(span) -> str:
    return "the whole image" if tuple(span) == WHOLE_IMAGE \
        else f"0x{span[0]:04X}-0x{span[1]:04X}"


def print_bases(d: bytes, span=BASE_RUN) -> None:
    rows = base_sites(d, span)
    per_base = {}
    for r in rows:
        per_base.setdefault(r["base"], []).append(r)
    # The span is in the header because a widened run must never be mistaken
    # for the low-run figures the annotations quote.
    print(f"{len(rows)} PD-image MOV DPTR site(s) with a base in "
          f"{fmt_span(span)}, over {len(per_base)} base(s)\n")
    for base in sorted(per_base):
        print(f"0x{base:04X}: {len(per_base[base])} site(s)")
        for r in per_base[base]:
            chain = " ".join(f"0x{h:04X}" for h in r["helpers"]) or "-"
            print(f"    file 0x{r['file_offset']:05X}  runtime 0x{r['runtime']:04X}  "
                  f"frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']}  "
                  f"A={r['a'].format(a='A')} B={r['b'].format(b='B')}  -> {chain}")
            print(f"      {fmt_address(r['terms'], base)} "
                  f"[chain ends at {r['stopped']}]")
        print()


def print_sites(d: bytes, addrs) -> None:
    lo, _ = pd_bounds()
    for r in site_rows(d, addrs):
        anchor = (f"MOV DPTR base 0x{r['base']:04X}" if r["base"] is not None
                  else "not a MOV DPTR site; decoded from the anchor itself")
        chain = " ".join(f"0x{h:04X}" for h in r["helpers"]) or "-"
        print(f"PD runtime 0x{r['addr']:04X}  (file 0x{r['file_offset']:05X})  "
              f"{anchor}")
        print(f"  frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']}  "
              f"A={r['a'].format(a='A')} B={r['b'].format(b='B')}  -> {chain}")
        print(f"  {fmt_address(r['terms'], r['base'])} "
              f"[chain ends at {r['stopped']}]")
        for i, raw in r["listing"]:
            print(f"    0x{i - lo:04x}  {raw.hex():<8} {mnemonic(d, i, i - lo)}")
        print()


def print_strides(d: bytes, span=BASE_RUN) -> None:
    rows, total = stride_census(d, span)
    resolved = sum(1 for r in rows if r["stride"] != UNRESOLVED_STRIDE)
    print(f"stride census over {fmt_span(span)}: {total} PD-image MOV DPTR "
          f"site(s), {resolved} stride constant(s) resolved")
    print("bases are effective bases: the one a rebasing chain ends on, not "
          "the site's own immediate\n")
    for r in rows:
        shown = r["bases"][:STRIDE_BASES_SHOWN]
        bases = " ".join(f"0x{b:04X}" for b in shown)
        if len(shown) < len(r["bases"]):
            # Truncated in the text view only, and said out loud: the CSV
            # carries every base, so nothing is silently dropped.
            bases += f" ... and {len(r['bases']) - len(shown)} more (see --strides-csv)"
        label = ("no stride resolved" if r["stride"] == UNRESOLVED_STRIDE
                 else f"0x{r['stride']}")
        print(f"{label:<18} {r['sites']:>4} site(s)  {len(r['bases']):>3} base(s)  "
              f"{r['paged']:>4} with 0x200×  {bases}")
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


def write_strides_csv(d: bytes, span=WHOLE_IMAGE) -> None:
    rows, _ = stride_census(d, span)
    w = csv.writer(sys.stdout)
    w.writerow(["stride", "sites", "sites_with_page_term", "bases", "base_list"])
    for r in rows:
        w.writerow([r["stride"] if r["stride"] == UNRESOLVED_STRIDE
                    else f"0x{r['stride']}",
                    r["sites"], r["paged"], len(r["bases"]),
                    " ".join(f"0x{b:04X}" for b in r["bases"])])


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

# The four addresses ../annotations/ec-0x07d0-sites.md 4 names for the 0x5E and
# 0x77 strides, and the term each one has to keep producing. The first two are
# `MOV DPTR` sites and are pinned against ec-0x07d0-sites.csv's own
# file_offset/window columns as well, so a decode that drifts off the sites
# that section is about fails here rather than in prose; the last two are
# routine entries and are not rows in that CSV.
STRIDE_SITE_TERMS = {
    0xC2FA: ("DPTR ← 0x08F8 + R7×0x5E", "mov 0xf0,#0x5e"),
    0xDA9B: ("DPTR ← 0x0870 + low(R7×0x77)", "mov 0xf0,#0x77"),
}
STRIDE_HELPER_TERMS = {
    0x34D9: "DPTR ← 0x08FC + A×0x5E",
    0x578E: "R2:R1 ← 0x089B + A×0x77",
}

# The strides whose sites the whole-image census finds carrying the 0x200×
# page term. pd-index-geometry.md 7 answers the issue's question off this set,
# so it is pinned rather than re-read from the prose.
PAGED_STRIDES = {"60", "1F"}

SITES_CSV = "../annotations/ec-0x07d0-sites.csv"
HELPERS_CSV = "../annotations/pd-index-helpers.csv"
CALLERS_CSV = "../annotations/pd-index-callers.csv"
STRIDES_CSV = "../annotations/pd-base-strides.csv"
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

    site_csv = {r["runtime"]: r for r in _csv_rows(SITES_CSV)}
    for runtime, (want, want_window) in STRIDE_SITE_TERMS.items():
        row = site_csv.get(f"0x{runtime:04X}", {})
        check(row.get("file_offset") == f"0x{lo + runtime:05X}"
              and want_window in row.get("window", ""),
              f"{SITES_CSV} puts 0x{runtime:04X} at file 0x{lo + runtime:05X} "
              f"with `{want_window}` in its window "
              f"(got {row.get('file_offset')}, `{row.get('window')}`)")
        got = fmt_terms(site_rows(d, [runtime])[0]["terms"])
        check(got == want, f"--sites 0x{runtime:04X} decodes to {want} (got {got})")

    for entry, want in STRIDE_HELPER_TERMS.items():
        terms, _, _ = walk_helper(d, entry)
        got = fmt_terms(terms)
        check(got == want,
              f"--helpers 0x{entry:04X} decodes to {want} (got {got})")

    rows = base_sites(d)
    for base, want in BASE_COUNTS.items():
        got = sum(1 for r in rows if r["base"] == base)
        check(got == want, f"--bases finds {want} site(s) for 0x{base:04X} (got {got})")

    # The widened span has to be exercised, not merely accepted: every default
    # site must reappear in it, at the same offset and with the same terms.
    wide = {r["file_offset"]: r for r in base_sites(d, WHOLE_IMAGE)}
    check(all(r["file_offset"] in wide
              and wide[r["file_offset"]]["terms"] == r["terms"] for r in rows),
          f"--bases all is a superset of the default run ({len(rows)} site(s) "
          f"of {len(wide)})")

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

    want_strides = _csv_rows(STRIDES_CSV)
    got_strides, _ = stride_census(d, WHOLE_IMAGE)
    check(len(want_strides) == len(got_strides),
          f"{STRIDES_CSV} has one row per census entry ({len(got_strides)}; "
          f"got {len(want_strides)})")
    for want, got in zip(want_strides, got_strides):
        label = got["stride"] if got["stride"] == UNRESOLVED_STRIDE \
            else f"0x{got['stride']}"
        check(want["stride"] == label and want["sites"] == str(got["sites"])
              and want["sites_with_page_term"] == str(got["paged"])
              and want["base_list"] == " ".join(f"0x{b:04X}" for b in got["bases"]),
              f"{STRIDES_CSV} row {label} regenerates unchanged "
              f"({want['sites']} site(s), {want['sites_with_page_term']} paged)")
    check({r["stride"] for r in got_strides
           if r["paged"] and r["stride"] != UNRESOLVED_STRIDE} == PAGED_STRIDES,
          f"only {sorted(PAGED_STRIDES)} have sites carrying the 0x200× page "
          "term over the whole image -- the question pd-index-geometry.md 7 "
          "answers")

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
              f"trace_xdata_refs.py puts them, the four 0x5E/0x77 addresses sit "
              f"where ec-0x07d0-sites.md 4 puts them, and all three CSVs "
              f"regenerate unchanged (PD image at file 0x{lo:05X})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--helpers", nargs="*", metavar="ADDR",
                    help="decode each named index helper and report its DPTR "
                         "term(s); with no argument, the eleven named ones")
    ap.add_argument("--bases", nargs="?", const=BASE_RUN, metavar="SPAN",
                    help="every PD site whose MOV DPTR immediate is in SPAN "
                         "(`all`, or 0xLO-0xHI); with no argument, the low "
                         f"base run 0x{BASE_RUN[0]:04X}-0x{BASE_RUN[1]:04X}")
    ap.add_argument("--sites", nargs="+", metavar="ADDR",
                    help="decode forward from these PD runtime addresses, e.g. 0xC2FA")
    ap.add_argument("--strides", nargs="?", const=BASE_RUN, metavar="SPAN",
                    help="census of the stride constants the decode resolves over SPAN")
    ap.add_argument("--callers", nargs="+", metavar="ADDR",
                    help="bound the caller set of these PD runtime sites, e.g. 0x7421")
    ap.add_argument("--helpers-csv", action="store_true",
                    help="write the helper table as CSV on stdout")
    ap.add_argument("--strides-csv", nargs="?", const=WHOLE_IMAGE, metavar="SPAN",
                    help="write the stride census as CSV; with no argument, "
                         "the whole image, which is what the committed CSV holds")
    ap.add_argument("--callers-csv", action="store_true",
                    help="write the caller table for the four 0x04A6 sites as CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the decode against the committed annotations and CSVs")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    fw = args.firmware or os.path.join(here, DEFAULT_FIRMWARE)
    if args.self_test:
        return self_test(fw)
    modes = (args.helpers, args.bases, args.sites, args.strides, args.callers,
             args.helpers_csv, args.strides_csv, args.callers_csv)
    if all(m is None or m is False for m in modes):
        ap.error("pick a mode: --helpers, --bases, --sites, --strides, "
                 "--callers, --helpers-csv, --strides-csv, --callers-csv or "
                 "--self-test")
    try:
        bases_span = parse_span(args.bases)
        strides_span = parse_span(args.strides)
        strides_csv_span = parse_span(args.strides_csv)
    except ValueError as exc:
        ap.error(str(exc))

    d = open(fw, "rb").read()
    if not pd_verified(d):
        off, magic = PD_MARKER
        # stderr, so that a --*-csv redirect stays a clean CSV.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "0x20000-0x2FFFF is not the image this tool decodes",
              file=sys.stderr)
        return 1

    if args.helpers is not None:
        print_helpers(d, [int(a, 16) for a in args.helpers] or None)
    if bases_span is not None:
        print_bases(d, bases_span)
    if args.sites:
        print_sites(d, [int(a, 16) for a in args.sites])
    if strides_span is not None:
        print_strides(d, strides_span)
    if args.callers:
        print_callers(d, [int(a, 16) for a in args.callers])
    if args.helpers_csv:
        write_helpers_csv(d)
    if strides_csv_span is not None:
        write_strides_csv(d, strides_csv_span)
    if args.callers_csv:
        write_callers_csv(d, DEFAULT_CALLER_SITES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
