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

Six modes, in increasing order of how much they assume:

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
              framing counts, the length of the frame those counts describe, and
              any literal `mov rN,#imm` its frame contains in a register this
              site indexes on. A load into a register the site's term decode
              does not name is listed and bounds nothing, and a frame too short
              to have held one says so rather than reading as a search that
              found nothing. Both are heuristics; printing them side by side is
              the point.
  --reached   Every entry the base sites in a span hand DPTR to, one per entry
              rather than one per site, with the decode outcome each one gets:
              its term string, or `unmodelled` with the listing. --helpers
              names eleven entries; this is the population behind that table,
              and `named_in_table` says which rows are those eleven.
              --reached-csv is the same table as a committed CSV.

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
    these bytes, which is why --callers reports a literal load only into a
    register the site's term decode names as an index, and reports every
    other row unresolved.

The --accesses/--accesses-csv and --access-strides/--access-strides-csv
modes independently scan immediate-base templates and bounded direct helper
handoffs. They retain each MOVX snapshot and unconsumed construction. Their
SPAN filters the constructed effective base, not the MOV-DPTR immediate.
These candidates have separate denominators from --bases/--strides; body-only
evidence is not an extra caller access. low8(x) = x & 0xFF; base-add carry is
retained and every address wraps modulo 0x10000.

Every walk here is bounded by the pd-image region, not only by its instruction
count: walk_helper() and chain_from() take both ends of pd_bounds() and stop at
0x30000 the way access_walk() does, so a run off the region end is a named stop
rather than a listing of the 0xFF fill past it. Six other functions have always
kept that `hi` for their own loops; the census of every function that discards
it is in ../../docs/findings/pd-sites-address-range.md, and the decision this
bound rests on in ../../docs/findings/count-bounded-walk-invariant.md.

Read-only: it opens the firmware image for reading and writes nothing.

Usage:
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers 0x34D9 0x578E
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --bases
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --bases all
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --reached
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --sites 0xC2FA 0xDA9B
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --strides all
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 \
            --callers 0x7421 0x9DEC 0xB5D3 0xE9F5
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --helpers-csv
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --reached-csv
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --strides-csv all
    python3 pd_index_geometry.py ../firmware/GMxMGxx_11.800 --self-test
"""
import argparse
import csv
import io
from contextlib import redirect_stdout
import os
import re
import sys

from disasm8051 import FLOW_OPCODES, OPCODE_LEN, converges_from, mnemonic, paged_target
# `band_faults` is the one implementation of "is this band all 0xFF" in the
# tree, imported rather than rewritten so the self-test's floor below and
# check_image_map.py's own --check cannot come to disagree about it. The
# vocabulary comes with it for a second reason: the band predicate only knows
# how to test the `how` strings that tool declares a test for, so asking
# through `CHECKED` is what keeps an edited row from being measured against a
# claim it no longer makes.
from check_image_map import CHECKED, band_faults
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
# Three of them *replace* DPTR (or build a generic pointer in A:R1) from an
# immediate base instead of advancing whatever it held, so their term carries
# the REBASE marker below. They were transcribed from the sites
# ../annotations/ec-0x07d0-sites.md 4 names: 0x34D9 and 0xC2FA for the first,
# helper 0x5950 (called from 0xDA9B) for the second, 0x578E for the third.
TERM_TEMPLATES = (
    # mul ab ; add a,dpl ; mov dpl,a ; mov a,b ; addc a,dph ; mov dph,a
    ("a42582f582e5f03583f583", "{a}×{b}"),
    # mul ab ; add a,#lo ; mov dpl,a ; clr a ; addc a,#hi ; mov dph,a
    ("a424..f582e434..f583", "=DPTR ← {base} + low8({a}×{b})"),
    # add a,#lo ; mov dpl,a ; clr a ; addc a,#hi ; mov dph,a -- the same 16-bit
    # add with no multiply, so the addend is A alone. It drops B, which means
    # a caller that reached it through `mul ab` loses the product's high byte;
    # 0xDA9B does exactly that, and the annotation says so rather than assuming
    # the index is small enough for it not to matter.
    ("24..f582e434..f583", "=DPTR ← {base} + {a}"),
    # mul ab ; add a,#lo ; mov r1,a ; mov a,#hi ; addc a,b
    ("a424..f974..35f0", "=A:R1 ← {base} + {a}×{b}"),
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
MOV_R_FROM_A = (0xF8, 0xFF)              # mov rN,a -- source is A, so A survives
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

# A register name standing alone in a term. No hex literal can contain `R`, so
# a match here is a register and never part of a number; the `\b` on each side
# is defence against a longer name it would otherwise match inside. The term
# model's five templates name no such name today.
INDEX_REG_RE = re.compile(r"\bR[0-7]\b")

# The --callers status vocabulary, kept as constants for the same reason
# UNRESOLVED_STRIDE is: these are machine-readable cells that three documents
# quote by string, so they are defined once here and asserted against the
# committed CSV by --self-test.
#
# Each value says no more than the decode behind it. The positive one stops at
# the *load*: --callers traces no further than the caller frame, the entry pick
# is a heuristic, and literals_in() does not follow what a callee leaves in the
# register bank, so nothing here says the value survives the call. The
# "none an index register" value says only that these loads are not the index --
# not that the index is provably unbounded. The short-frame one says nothing at
# all about the index: it is about how much of the frame there was to scan.
UNRESOLVED_CALLER = "unresolved"
CALLER_NO_INDEX = "literals found, none an index register"
CALLER_INDEX_LOAD = "literal load into an index register"
CALLER_UNRESOLVED_INDEX = "literals found; site index registers unresolved"
CALLER_SHORT_FRAME = "frame too short to say"

# Instructions a caller frame must hold before a row that carries no literal
# load is filed `unresolved` at all. Below it the row says nothing -- a frame
# with no room in it cannot hold a load, so `unresolved` there asserts a search
# that had nowhere to happen.
#
# Two facts fix the threshold, both measured in
# ../../docs/findings/pd-caller-frame-quality.md and reproduced by
# pd_caller_frame_quality.py: the four committed rows with real frames are
# 13/16/16/19 instructions against the 0xC9DD phantom's one, so four sits above
# every frame the committed table trusts; and of the whole-image rows that do
# carry literals, exactly one falls below it -- and that one already reads
# `literals found; site index registers unresolved`, which makes no negative
# claim about an index in either direction, so no positive finding is lost by
# drawing the line here. Higher would discard real negatives; lower would let a
# two-instruction frame certify that nothing was loaded into it.
MIN_FRAME_INSNS = 4

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


def check_site_addr(addr: int) -> None:
    """Refuse an address that is not a PD runtime address at all.

    A `--sites` anchor is the caller's, and the region it indexes is flat, so a
    value wider than the region has no file offset to read and the failure would
    otherwise be an IndexError from whichever line read first. What this tests
    is the *argument*, not this image's bytes: the region is the same width on
    any dump, which is what separates it from the reachability guard
    ../../docs/findings/opcode-len-bounds-census.md row 10 declined to add. The
    instruction-boundary precondition beside it is not the tool's to make --
    no byte says where a routine's instructions begin.

    Three modes call it and each takes a caller's address: `--sites` through
    site_rows(), `--callers` through the same site_rows() it now decodes each
    site's index registers with, and `--helpers` through print_helpers(). The
    message is already mode-neutral, which is why the function is not named
    for any of them.
    """
    lo, hi = pd_bounds()
    if 0 <= addr < hi - lo:
        return
    msg = (f"0x{addr:05X} is not a {PD_REGION} runtime address: that region is "
           f"0x0000-0x{hi - lo - 1:04X} at run time, "
           f"0x{lo:05X}-0x{hi - 1:05X} in the file")
    if lo <= addr < hi:
        # The plausible mistake, and the columns are the tool's own: --sites
        # prints `file_offset` beside `runtime` and the committed CSVs carry
        # both. What that number is, is left to the reader.
        msg += (f"\n  0x{addr:05X} is inside the file range, which is where a "
                f"site's file_offset lives; the runtime address there is "
                f"0x{addr - lo:04X}")
    raise ValueError(msg)


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
    `low8(...)` is what keeps a wrapped address from reading as an exact one."""
    return f"low8({a_sym}×{b_sym})"


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
    """Decode the helper at PD runtime `entry` into (terms, listing, note, gap).

    `terms` is the list of symbolic DPTR addends in the order the routine
    applies them, with A and B rendered as whatever the routine last put in
    them ('A'/'B' where the caller supplies it). `note` is empty when every
    byte from the entry to the `ret` was accounted for, and otherwise says
    which instruction the term model does not cover -- that row is
    `unmodelled` and its listing is the whole of what is claimed about it.
    `gap` is that first uncovered instruction's runtime address, and None when
    the walk ended on a bound instead -- a budget stop covers every byte it
    read, so it has no gap to point at.

    A count bounds work, not the buffer: the region's end bounds the walk and
    HELPER_MAX_INSNS stays the cap on a walk that never reaches it. Which end
    ended the walk is said in both cases, because they are different claims."""
    lo, hi = pd_bounds()
    # The buffer as well as the region, so a short image ends the walk where it
    # ends rather than raising from whichever read went first. On the committed
    # image the region ends first and this changes nothing.
    hi = min(hi, len(d))
    if entry in seen or depth > 3:
        return [], [], f"unmodelled: tail chain not followed past 0x{entry:04X}", entry
    seen = seen | {entry}
    terms, listing, note, gap = [], [], "", None
    a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
    i = lo + entry
    for _ in range(HELPER_MAX_INSNS):
        if not lo <= i < hi:
            return terms, listing, (
                f"unmodelled: walk left the {PD_REGION} at runtime "
                f"0x{i - lo:04X}, its end at file 0x{hi:05X}"), i - lo
        n, term = _match_template(d, i)
        if term and not note:
            if i + n > hi:
                return terms, listing, (
                    f"unmodelled: the {n}-byte term template at runtime "
                    f"0x{i - lo:04X} crosses the {PD_REGION} end at file "
                    f"0x{hi:05X}"), i - lo
            for j, raw, _ in _insns(d, i, n):
                listing.append((j, raw))
            terms.append(term.format(a=a_sym, b=b_sym))
            # `mul ab` leaves the product in A:B, so neither symbol survives
            # the template; a later term has to re-load them to be named.
            a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
            i += n
            continue
        op = d[i]
        if i + OPCODE_LEN[op] > hi:
            return terms, listing, (
                f"unmodelled: the instruction at runtime 0x{i - lo:04X} is cut "
                f"by the {PD_REGION} end at file 0x{hi:05X}"), i - lo
        here = i - lo
        raw = d[i:i + OPCODE_LEN[op]]
        listing.append((i, raw))
        if op == RET:
            return terms, listing, note, gap
        if note:
            # Past the first unmodelled instruction nothing is claimed, but the
            # walk keeps going so the row carries a whole routine's listing.
            if is_jmp(op):
                return terms, listing, note, gap
        elif raw[:2] == MOV_B_IMM:
            b_sym = f"0x{raw[2]:02X}"
        elif 0xE8 <= op <= 0xEF:
            a_sym = f"R{op - 0xE8}"
        elif op == MOV_A_IMM:
            a_sym = f"0x{raw[1]:02X}"
        elif op == CLR_A:
            a_sym = "0x00"
        elif MOV_R_FROM_A[0] <= op <= MOV_R_FROM_A[1]:
            # `mov rN,a` takes its source from A and writes nothing else, so
            # the accumulator's symbol carries through and the walk continues.
            # It contributes no term: it adds nothing to DPTR, which is what
            # separates it from the `add`/`mul` idioms above. A_WRITERS
            # excludes this range already, so the frame walkers read it the
            # same way; the difference is only that these two forward walks
            # used to treat it as the end of a decode.
            pass
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
                gap = here
            else:
                sub_terms, _, sub_note, sub_gap = walk_helper(d, target, depth + 1, seen)
                terms += resolve_terms(sub_terms, a_sym, b_sym)
                note, gap = sub_note, sub_gap
                if is_jmp(op):
                    return terms, listing, note, gap  # tail call: the callee returns
                a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
        else:
            note = (f"unmodelled: 0x{here:04X} `{mnemonic(d, i, here).strip()}` "
                    "is outside the term model")
            gap = here
        i += OPCODE_LEN[op]
    return terms, listing, note or f"unmodelled: no `ret` within {HELPER_MAX_INSNS} instructions", gap


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
    the caller named the address deliberately, turns it on.

    The same bound as walk_helper(): `max_insns` is a budget on work and the
    region end is the bound, so the stops read differently on purpose."""
    lo, hi = pd_bounds()
    hi = min(hi, len(d))
    helpers, terms = [], []
    i = start
    for _ in range(max_insns):
        if not lo <= i < hi:
            return helpers, terms, (
                f"walk left the {PD_REGION} at runtime 0x{i - lo:04X}, its end "
                f"at file 0x{hi:05X}")
        # An inline template, as opposed to one reached through a call: the
        # 0x07D0 sites of ../annotations/ec-0x07d0-sites.md 4 multiply in place
        # rather than calling 0x10BC, and stopping at their `mul ab` would
        # report no term for arithmetic the model does cover.
        n, term = _match_template(d, i)
        if term:
            if i + n > hi:
                return helpers, terms, (
                    f"the {n}-byte term template at runtime 0x{i - lo:04X} "
                    f"crosses the {PD_REGION} end at file 0x{hi:05X}")
            terms.append(term.format(a=a_sym, b=b_sym))
            a_sym, b_sym = UNKNOWN_A, UNKNOWN_B
            i += n
            continue
        op = d[i]
        if i + OPCODE_LEN[op] > hi:
            return helpers, terms, (
                f"the instruction at runtime 0x{i - lo:04X} is cut by the "
                f"{PD_REGION} end at file 0x{hi:05X}")
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
            sub_terms, _, note, _ = walk_helper(d, target)
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
        elif MOV_R_FROM_A[0] <= op <= MOV_R_FROM_A[1]:
            # `mov rN,a` reads A and writes only the register bank, so the
            # chain steps over it with the accumulator's symbol intact and
            # reaches the template behind it. No term: it adds nothing to
            # DPTR. The same rule and the same reason as walk_helper's.
            pass
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
    mid-routine anchor gets a chain at all. Two preconditions, and only one of
    them is the tool's to make. Nothing checks that the address is an
    instruction boundary -- the caller asserts that by naming it, and the
    listing is there so a wrong assertion is visible. The *range* is checked:
    check_site_addr() refuses an address outside 0x0000-0xFFFF and names the
    file range beside it, because the tool's own output puts `file_offset`
    next to `runtime`."""
    lo, _ = pd_bounds()
    # Checked over the whole run first, so one bad address in a multi-address
    # call is the diagnostic rather than a partial listing and then a traceback.
    for addr in addrs:
        check_site_addr(addr)
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


def reached_entries(d: bytes, span=BASE_RUN):
    """Every entry the base sites in `span` hand DPTR to, one row each, sorted
    by entry.

    A projection of base_sites(), not a second scan: an entry is here exactly
    when --bases reaches it, and `sites` is how many of those sites call it.
    So the two can never disagree about the population, and
    ../annotations/pd-reached-helpers.md is the file that says what each one
    turns out to be.

    The eleven entries of §2 are reached too, so this supersedes
    pd-index-helpers.csv rather than shadowing it: `named_in_table` says which
    rows are those. `terms` is empty wherever the model does not cover the
    body, and the listing is then the whole of what is claimed -- the same
    contract pd-index-helpers.csv already has, and the reason a site whose
    chain reaches an unmodelled entry carries no term either."""
    lo, _ = pd_bounds()
    per = {}
    for r in base_sites(d, span):
        for entry in r["helpers"]:
            per.setdefault(entry, []).append(r)
    rows = []
    for entry in sorted(per):
        sites = per[entry]
        terms, listing, note, gap = walk_helper(d, entry)
        tail = ""
        if listing:
            off, last = listing[-1]
            if is_call(last[0]) or is_jmp(last[0]):
                t = branch_target(last, off - lo)
                tail = f"0x{t:04X}" if t is not None else ""
        rows.append({
            "entry": entry, "file_offset": lo + entry,
            "bytes": sum(len(raw) for _, raw in listing),
            "terms": "" if note else fmt_terms(terms),
            "tail_target": tail, "unmodelled": bool(note), "note": note,
            "first_unmodelled": "" if gap is None else f"0x{gap:04X}",
            "sites": len(sites),
            # Effective rather than the site's own immediate, for the reason
            # stride_census() reads that instead: the base is the array being
            # indexed, and a rebasing chain replaces the one the site loaded.
            "bases": sorted({effective_base(r) for r in sites}),
            "named_in_table": entry in HELPERS,
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


def index_registers(terms):
    """The R0-R7 registers a site's effective terms name as an index factor.

    Only the right-hand side of a construction's `←` is read. One template
    lands its result in `A:R1`, where the `R1` is a *destination* and not
    something the access indexes on -- 0x578E produces that form, and no
    committed caller row reaches it, which is why --self-test covers it
    synthetically instead.

    `A` and `B` are excluded because the site's own frame reloads both, so
    neither is a value a caller's literal could bound. That leaves R0-R7 as
    the only registers a frame's literal load and a site's index can share,
    which is what makes the intersection in caller_status() well defined.
    """
    out = set()
    for term in terms:
        out.update(INDEX_REG_RE.findall(term.split(" ← ")[-1]))
    return out


def caller_status(literals, index_regs, frame_insns) -> str:
    """The status cell for one caller row: a function of the *intersection* of
    the frame's literal register loads with the index registers the site's own
    term decode names, not of the mere presence of literals. A caller loading
    literals into registers this access does not index on bounds nothing about
    it, and saying so is the whole difference between the row and the claim
    pd-index-geometry.md 4.2 spends its length denying.

    Branch order is load-bearing, twice over.

    "Does the decode name any index register at all" is tested before the
    intersection, so a site whose terms resolve nothing keeps its own wording:
    "not found by this method" is a different claim from "a match was sought
    here and none was found", and collapsing the two is the mistake this
    function exists to stop.

    The whole literal branch comes *before* the frame test, because a literal
    found in a frame of any length is a literal found: `mov rN,#imm` in two
    instructions is still a load, and grading the frame first would throw a
    positive finding away. The frame test therefore decides only between the
    two values a literal-free row can take -- and it is strictly the weaker of
    them, `CALLER_SHORT_FRAME` claiming nothing about the index at all where
    `unresolved` claims a search happened in it.
    """
    if literals:
        if not index_regs:
            return CALLER_UNRESOLVED_INDEX
        return CALLER_INDEX_LOAD if literals.keys() & index_regs else CALLER_NO_INDEX
    return CALLER_SHORT_FRAME if frame_insns < MIN_FRAME_INSNS else UNRESOLVED_CALLER


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
        # Once per site, outside the picks and rows loops: the decode is the
        # same for every caller of it, and the status is that decode's index
        # registers intersected with each frame's own literals.
        regs = index_registers(effective_terms(site_rows(d, [site])[0]["terms"]))
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
                    # Once, because the two readings below are the same walk:
                    # literals_in() needs the frame and the status needs its
                    # length, and frame_of() re-derives it from the image each
                    # time it is called.
                    frame = frame_of(d, off)
                    lits = literals_in(frame)
                    rows.append({
                        "site": site, "entry": entry, "kind": kind,
                        "file_offset": off, "runtime": off - lo,
                        "opcode": mnemonic(d, off, off - lo).strip(),
                        "frame_onto": onto, "frame_over": over,
                        "frame_insns": len(frame),
                        "literals": lits,
                        "status": caller_status(lits, regs, len(frame)),
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
    base templates lands in A:R1 and never touches DPTR, and labelling it
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
        # Over the whole run first, as site_rows() does, so one bad entry in a
        # multi-entry call is the diagnostic rather than a partial listing --
        # and ahead of the count line, not behind it, so that a refusal leaves
        # stdout empty on a redirect as it does for --sites and --callers.
        for entry in entries:
            check_site_addr(entry)
        print(f"{len(entries)} helper entry/entries named on the command line\n")
    for entry in entries:
        terms, listing, note, _ = walk_helper(d, entry)
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


def print_reached(d: bytes, span=BASE_RUN) -> None:
    lo, _ = pd_bounds()
    rows = reached_entries(d, span)
    unmodelled = [r for r in rows if r["unmodelled"]]
    # The same three counts pd-index-geometry.md 2.3 reports, so a reader can
    # check the prose against this run without re-deriving it. The span is
    # named for the reason print_bases() names it.
    print(f"{len(rows)} DPTR-recipient entry/entries reached by the PD-image "
          f"MOV DPTR site(s) with a base in {fmt_span(span)}")
    print(f"{len(rows) - len(unmodelled)} decode, {len(unmodelled)} do not; "
          f"{sum(1 for r in rows if r['named_in_table'])} of them are in the "
          f"{len(HELPERS)}-entry table\n")
    for r in rows:
        bases = " ".join(f"0x{b:04X}" for b in r["bases"])
        # Terms and a note together is the ordinary case for a mid-routine
        # entry, and print_helpers() reads it the same way: the arithmetic can
        # be known while the tail it falls into is not.
        head = r["terms"] or ""
        head = f"{head}; {r['note']}" if head and r["note"] else head or r["note"]
        print(f"0x{r['entry']:04X}  (file 0x{r['file_offset']:05X})  "
              f"{r['sites']} site(s)  {bases}  {head}")
        for i, raw in r["listing"]:
            print(f"    0x{i - lo:04x}  {raw.hex():<8} {mnemonic(d, i, i - lo)}")
        print()


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
                # The status on every row, not only where the literals are
                # empty: printing `lits or status` made the one row that
                # carries a status the one row whose status was invisible, in
                # the very view a reader reads the claim off.
                print(f"    file 0x{r['file_offset']:05X}  runtime 0x{r['runtime']:04X}  "
                      f"{r['kind']:<9} {r['opcode']:<16} "
                      f"frame {r['frame_onto']}/{r['frame_onto'] + r['frame_over']} "
                      f"({r['frame_insns']} insn)  "
                      f"{lits or '-'} [{r['status']}]")
        print()


def write_helpers_csv(d: bytes) -> None:
    lo, _ = pd_bounds()
    w = csv.writer(sys.stdout)
    w.writerow(["entry", "file_offset", "bytes", "terms", "tail_target", "unmodelled"])
    for entry in HELPERS:
        terms, listing, note, _ = walk_helper(d, entry)
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


REACHED_FIELDS = ("entry", "file_offset", "bytes", "terms", "tail_target",
                  "unmodelled", "note", "first_unmodelled", "sites", "bases",
                  "named_in_table", "listing")


def reached_csv_row(d: bytes, r) -> list:
    """One reached entry as the REACHED_FIELDS list of strings.

    The single formatter for that CSV -- write_reached_csv() and the --self-test
    comparison both go through it, so a regenerated file and a re-derived row
    cannot disagree about a column. `listing` is filled only where `unmodelled`
    is yes: a resolved row is one short line of terms, and a row the model does
    not cover is quoted rather than fitted, which is the whole of what is
    claimed about it.
    """
    lo, _ = pd_bounds()
    return [f"0x{r['entry']:04X}", f"0x{r['file_offset']:05X}", r["bytes"],
            r["terms"], r["tail_target"],
            "yes" if r["unmodelled"] else "no", r["note"],
            r["first_unmodelled"], r["sites"],
            " ".join(f"0x{b:04X}" for b in r["bases"]),
            "yes" if r["named_in_table"] else "no",
            "; ".join(f"0x{i - lo:04X} {mnemonic(d, i, i - lo).strip()}"
                      for i, _ in r["listing"]) if r["unmodelled"] else ""]


def write_reached_csv(d: bytes, span=BASE_RUN) -> None:
    w = csv.writer(sys.stdout)
    w.writerow(REACHED_FIELDS)
    for r in reached_entries(d, span):
        w.writerow(reached_csv_row(d, r))


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
                "frame_insns", "literals", "status"])
    for group in caller_rows(d, sites):
        for pick in group["picks"]:
            for r in pick["rows"]:
                w.writerow([f"0x{r['site']:04X}", f"0x{pick['entry']:04X}",
                            pick["label"], pick["reaches"], pick["entry_shape"],
                            pick["entry_gap_jmps"],
                            f"0x{r['file_offset']:05X}", f"0x{r['runtime']:04X}",
                            r["kind"], r["opcode"], r["frame_onto"], r["frame_over"],
                            r["frame_insns"],
                            " ".join(f"{k}=#0x{v:02X}"
                                     for k, v in sorted(r["literals"].items())),
                            r["status"]])


# This census has different units from base_sites(): templates and consumers,
# not MOV-DPTR anchors. Keep its bounds and state separate from the baseline.
ACCESS_MAX_INSNS = 48
ACCESS_MAX_DEPTH = 3
ACCESS_FIELDS = (
    "construction_id", "access_id", "row_kind", "methods", "anchors",
    "construction_runtime", "construction_file", "context", "matched_bytes",
    "frame_start", "frame_onto", "frame_over", "effective_base", "destination",
    "terms", "semantics", "consumer_runtime", "consumer_file", "direction",
    "status", "stop_reason", "stop_runtime", "stop_file",
)


def immediate_templates(d):
    lo, hi = pd_bounds()
    d = d[:min(hi, len(d))]
    out = {}
    i = lo
    while i < min(hi, len(d)):
        n, term = _match_template(d, i)
        if term and term.startswith(REBASE):
            out[i] = (n, term)
        # A direct handoff can enter the add-only suffix without executing MUL.
        # Keep overlaps until the walk establishes their entry context; walks
        # through the full template still merge by construction and consumer.
        i += 1
    return out


def access_load(raw, a, b):
    op = raw[0]
    if raw[:2] == MOV_B_IMM:
        return a, f"0x{raw[2]:02X}"
    if 0xE8 <= op <= 0xEF:
        return f"R{op - 0xE8}", b
    if op == MOV_A_IMM:
        return f"0x{raw[1]:02X}", b
    if op == CLR_A:
        return "0x00", b
    if op == MUL_AB:
        return product_sym(a, b), "B"
    if op == MOVX_A_DPTR:
        return "A", b
    if op in (MOVX_DPTR_A, MOV_DPTR):
        return a, b
    return None


def access_frames(d, off):
    """Maximal supported backward frames, retaining every suffix anchor.

    A suffix lacks context, not contradicts its own longer frame. Disjoint
    framings remain alternatives; no longest-frame confidence vote is taken.
    """
    lo, _ = pd_bounds()
    runs = []
    for start in range(max(lo, off - FRAME_BACK), off + 1):
        i, run = start, []
        while i < off:
            n = OPCODE_LEN[d[i]]
            raw = d[i:i + n]
            if i + n > off or access_load(raw, "A", "B") is None:
                break
            run.append(i)
            i += n
        if i == off:
            runs.append(tuple(run + [off]))
    maximal = [r for r in runs if not any(len(q) > len(r) and
               q[-len(r):] == r for q in runs)]
    return [(r[0], sorted({a for q in runs if len(q) <= len(r) and
                          r[-len(q):] == q for a in q})) for r in maximal]


def access_walk(d, start, templates, entries, budget=ACCESS_MAX_INSNS):
    lo, hi = pd_bounds()
    hi = min(hi, len(d))
    a, b = "A", "B"
    pointers, records, constructions = {}, [], []
    stack, path, seen = [], (), set()
    i, used = start, 0
    reason = "instruction-budget"

    def construct(off, base, dest, term, raw, kind):
        obj = dict(off=off, base=base, dest=dest, term=term, raw=raw,
                   path=path, kind=kind, accesses=[])
        constructions.append(obj)
        pointers[dest] = obj
        return obj

    while used < budget:
        if not lo <= i < hi:
            reason = "image-bound"
            break
        if (i, path) in seen:
            reason = "loop"
            break
        seen.add((i, path))
        op, n = d[i], OPCODE_LEN[d[i]]
        if i + n > hi:
            reason = "truncated-instruction"
            break
        raw = d[i:i + n]
        if i in templates:
            n, term = templates[i]
            cost = len(list(_insns(d, i, n)))
            if used + cost > budget:
                reason = "instruction-budget"
                break
            term = term.format(a=a, b=b)[1:]
            base = int(re.search(r"0x([0-9A-F]{4})", term)[1], 16)
            dest = term.split(" ←")[0]
            construct(i, base, dest, term, d[i:i + n].hex(), "template")
            # The address halves replace A. B is also unknown after multiply;
            # add-only forms preserve it, but it is not used to invent a term.
            a = "A"
            if op == MUL_AB:
                b = "B"
            used += cost
            i += n
            continue
        used += 1
        if op == MOV_DPTR:
            base = int.from_bytes(raw[1:], "big")
            construct(i, base, "DPTR", f"DPTR ← 0x{base:04X}", raw.hex(), "anchor")
        elif op in (MOVX_A_DPTR, MOVX_DPTR_A):
            ptr = pointers.get("DPTR")
            if ptr:
                access = (i, path, "read" if op == MOVX_A_DPTR else "write")
                ptr["accesses"].append(access)
            if op == MOVX_A_DPTR:
                a = "A"
        elif op == RET:
            if not stack:
                reason = "return-consumption-not-established"
                break
            i, path = stack.pop()
            continue
        elif is_call(op) or is_jmp(op):
            target = lo + branch_target(raw, i - lo)
            if target not in entries:
                reason = "unmodelled-handoff"
                break
            if len(path) >= ACCESS_MAX_DEPTH:
                reason = "recursion-bound"
                break
            if is_call(op):
                stack.append((i + n, path))
            path += ((i, target),)
            i = target
            continue
        else:
            state = access_load(raw, a, b)
            if state is None:
                reason = ("stack-detour" if op in (0xC0, 0xD0) else
                          "unsupported-branch" if op in FLOW_OPCODES else
                          "unsupported-instruction")
                break
            a, b = state
        i += n
    for c in constructions:
        # The MOV-DPTR snapshots are contextual evidence only, not a second
        # whole-image MOV-DPTR census. Keep those actually consumed here.
        if c["kind"] == "anchor" and not c["accesses"]:
            continue
        for consumer in c["accesses"] or [None]:
            records.append(dict(c, consumer=consumer, stop=i, reason=reason))
    return records


def access_entries(d, templates):
    """Direct branch targets reaching a template in a bounded supported prefix."""
    lo, hi = pd_bounds()
    hi = min(hi, len(d))
    branches = {}
    for i in range(lo, hi):
        n = OPCODE_LEN[d[i]]
        if i + n <= hi and (is_call(d[i]) or is_jmp(d[i])):
            branches[i] = lo + branch_target(d[i:i + n], i - lo)

    def reaches_template(start, seen=(), depth=0):
        i = start
        if i in seen or depth > ACCESS_MAX_DEPTH:
            return False
        for _ in range(HELPER_MAX_INSNS):
            if i in templates:
                return True
            if not lo <= i < hi:
                return False
            n = OPCODE_LEN[d[i]]
            if i + n > hi:
                return False
            if i in branches:
                return reaches_template(branches[i], seen + (start,), depth + 1)
            if access_load(d[i:i + n], "A", "B") is None:
                return False
            i += n
        return False

    entries = {t for t in branches.values() if reaches_template(t)}
    return entries, {i: t for i, t in branches.items() if t in entries}


def access_rows(d, span=WHOLE_IMAGE, budget=ACCESS_MAX_INSNS):
    templates = immediate_templates(d)
    entries, branches = access_entries(d, templates)
    lo, _ = pd_bounds()
    merged = {}
    for seed in sorted(set(templates) | set(branches)):
        method = "template-scan" if seed in templates else "direct-handoff"
        for start, anchors in access_frames(d, seed):
            for r in access_walk(d, start, templates, entries, budget):
                if not span[0] <= r["base"] <= span[1]:
                    continue
                context = r["path"]
                consumer = r["consumer"]
                key = (r["off"], context, consumer, r["term"], r["reason"], r["stop"])
                item = merged.setdefault(key, dict(r, anchors=set(), methods=set(), frames=set()))
                item["anchors"].update(anchors)
                item["methods"].add(method)
                if r["raw"].startswith("a424") and r["dest"] == "DPTR":
                    item["methods"].add("overlapping-add-suffix")
                item["frames"].add(start)
    contextual = {r["off"] for r in merged.values() if r["path"]}
    interpretations = {}
    for r in merged.values():
        interpretations.setdefault((r["off"], r["path"], r["consumer"]), set()).add(r["term"])

    def rt(i):
        return f"0x{i - lo:04X}"

    def file(i):
        return f"0x{i:05X}"

    def ctx(path):
        return ";".join(f"{rt(a)}>{rt(t)}" for a, t in path)

    out = []
    for r in merged.values():
        consumer = r["consumer"]
        cid = f"{r['kind']}:{rt(r['off'])}@{ctx(r['path']) or 'body'}"
        aid = cid + (f"/{rt(consumer[0])}@{ctx(consumer[1]) or 'body'}" if consumer else "/none")
        evidence = not r["path"] and r["off"] in contextual
        kind = ("body-evidence" if evidence else "anchor-access" if r["kind"] == "anchor"
                else "access" if consumer else "construction-only")
        conflict = len(interpretations[(r["off"], r["path"], consumer)]) > 1
        onto, over = converges_from(d, r["off"], min(24, r["off"] - lo))
        out.append(dict(zip(ACCESS_FIELDS, (
            cid, aid, kind, " ".join(sorted(r["methods"])),
            " ".join(file(a) for a in sorted(r["anchors"])), rt(r["off"]), file(r["off"]),
            ctx(r["path"]), r["raw"], " ".join(file(f) for f in sorted(r["frames"])),
            onto, over, f"0x{r['base']:04X}", r["dest"], r["term"],
            "low8(x)=x&0xFF; carry retained; address modulo 0x10000",
            rt(consumer[0]) if consumer else "", file(consumer[0]) if consumer else "",
            consumer[2] if consumer else "", "unresolved-alternative" if conflict else
            "decoded-candidate" if consumer else "consumption-not-established",
            r["reason"], rt(r["stop"]), file(r["stop"]),
        ))))
    return sorted(out, key=lambda r: tuple(str(r[k]) for k in ACCESS_FIELDS))


def access_totals(rows):
    canonical = [r for r in rows if r["row_kind"] != "body-evidence"]
    templates = [r for r in canonical if r["construction_id"].startswith("template:")]
    return dict(constructions=len({r["construction_id"] for r in templates}),
                accesses=len({r["access_id"] for r in templates if r["consumer_file"]}),
                construction_only=len({r["construction_id"] for r in templates if not r["consumer_file"]}),
                anchor_accesses=len({r["access_id"] for r in canonical if r["row_kind"] == "anchor-access"}),
                evidence_records=len(rows))


def access_stride_rows(rows):
    groups = {}
    for r in rows:
        if r["row_kind"] == "body-evidence":
            continue
        unit = r["row_kind"]
        for s in set(STRIDE_RE.findall(r["terms"])) or {UNRESOLVED_STRIDE}:
            group = groups.setdefault((s, unit), {"ids": set(), "bases": set()})
            group["ids"].add(r["access_id"])
            group["bases"].add(r["effective_base"])
    return [dict(stride=s if s == UNRESOLVED_STRIDE else f"0x{s}",
                 counting_unit=unit, candidates=len(g["ids"]),
                 base_list=" ".join(sorted(g["bases"])))
            for (s, unit), g in sorted(groups.items())]


def write_access_csv(rows, strides=False):
    if strides:
        rows = access_stride_rows(rows)
    fields = ("stride", "counting_unit", "candidates", "base_list") if strides else ACCESS_FIELDS
    writer = csv.DictWriter(sys.stdout, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)


def print_accesses(rows, span, strides=False):
    print(f"Immediate-base census; effective-base filter: {fmt_span(span)}")
    print("Candidates, not execution evidence; distinct from MOV-DPTR anchor totals")
    print(" ".join(f"{k}={v}" for k, v in access_totals(rows).items()))
    if strides:
        print("Each candidate counts once per distinct constant; totals are not additive")
        write_access_csv(rows, True)
    else:
        for r in rows:
            print(f"{r['access_id']} {r['row_kind']} {r['terms']} "
                  f"{r['direction'] or 'no consumer'} [{r['status']}; "
                  f"{r['stop_reason']} at {r['stop_runtime']}]")


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
    0xC2FA: ("DPTR ← 0x08F8 + low8(R7×0x5E)", "mov 0xf0,#0x5e"),
    0xDA9B: ("DPTR ← 0x0870 + low8(R7×0x77)", "mov 0xf0,#0x77"),
}
STRIDE_HELPER_TERMS = {
    0x34D9: "DPTR ← 0x08FC + low8(A×0x5E)",
    0x578E: "A:R1 ← 0x089B + A×0x77",
}

# The strides whose sites the whole-image census finds carrying the 0x200×
# page term. pd-index-geometry.md 7 answers the issue's question off this set,
# so it is pinned rather than re-read from the prose.
PAGED_STRIDES = {"60", "1F"}

# The literals, status and frame length every row of
# ../annotations/pd-index-callers.csv carries, keyed by (site, caller runtime).
# Transcribed from pd-index-geometry.md 4 and 4.2 rather than read back out of
# the CSV, so the committed cell, the value this run computes and the prose it
# comes from are three separate things and a disagreement between any two of
# them fails here.
#
# 4's net is "not one index register bounded by a literal"; 4.2's is "None of
# the three literals is an index for this access", for a site indexing on R7
# and R6 that its frame loads R1/R2/R3 into. The literals sit beside each
# status so the second of those is checkable and not just assertable: an empty
# literals column would make CALLER_NO_INDEX true for the wrong reason. The
# frame length is the third element for the same reason one column further on:
# a hand-set `frame_insns` would make the status true for the wrong frame, and
# the byte-comparison below only stops the file and the tool drifting apart --
# not both drifting from these numbers together.
CALLER_STATUSES = {
    ("0x7421", "0xC9DD"): ("", CALLER_SHORT_FRAME, 1),
    ("0x7421", "0x7CD1"): ("", UNRESOLVED_CALLER, 19),
    ("0x9DEC", "0xB452"): ("", UNRESOLVED_CALLER, 16),
    ("0xB5D3", "0xB838"): ("", UNRESOLVED_CALLER, 13),
    ("0xE9F5", "0x66E4"): ("R1=#0x00 R2=#0x08 R3=#0x01", CALLER_NO_INDEX, 16),
}

SITES_CSV = "../annotations/ec-0x07d0-sites.csv"
HELPERS_CSV = "../annotations/pd-index-helpers.csv"
CALLERS_CSV = "../annotations/pd-index-callers.csv"
STRIDES_CSV = "../annotations/pd-base-strides.csv"
REACHED_CSV = "../annotations/pd-reached-helpers.csv"
DEFAULT_FIRMWARE = "../firmware/GMxMGxx_11.800"

# ../annotations/pd-reached-helpers.md reports what widening the term model by
# one rule measured. These are its figures, pinned so the write-up cannot drift
# from the tool that produced them; the eleven named entries, the 151/3176
# denominators and the access census below are unchanged by that rule and say
# so where they are checked.
REACHED_TOTALS = dict(entries=80, decoded=60, unmodelled=20, no_term_sites=11)

# 0x99E2 is the entry pd-index-geometry.md 2.3 names as the reason the low run
# has sites with no term, and it decodes under the new rule. 0x9A71 is named
# here because it is *not* reached from the low run -- it belongs to a site
# pd-xdata-overlap.md 3.2 has, not to this span -- so its pin is against the
# decode directly. It is the one row that must stay unmodelled: a rule that
# widened past `mov rN,a` would start fitting it, and an empty term there is
# what 2.2 says it is.
REACHED_BY_NAME = {0x99E2: "A×0x60"}
REACHED_STILL_UNMODELLED = (0x9A71,)

# One entry per class the model still does not cover, so none of the five can
# quietly start "decoding" into nothing. Each value is the tool's own note.
REACHED_GAPS = {
    0x0FAF: "unmodelled: 0x0FB1 `inc  dptr` is outside the term model",
    0x3627: "unmodelled: 0x3627 `mov  a,0x82` is outside the term model",
    0x104D: "unmodelled: 0x104D `mov  r0,0x82` is outside the term model",
    0x35F3: "unmodelled: 0x35F5 `mov  dptr,#0x0408` is outside the term model",
    0x99D4: "unmodelled: 0x99D5 `add  a,#0x01` is outside the term model",
}

# pd-index-geometry.md 3.2's question, one row further on. The last is the
# load-bearing number: it is what says 0x260 survived the widening rather than
# being an artefact of the subset the old templates happened to resolve.
BOTH_TERM_SITES, SAME_REGISTER, DIFFERENT_REGISTER = 98, 40, 0


def _csv_rows(path: str):
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, path), newline="") as fh:
        return list(csv.DictReader(fh))


def fixture(chunks, end=None):
    """Synthetic image for a walk that the committed one cannot exercise: a
    `ret` fill over the region, truncated at runtime `end` when given, with
    each `{runtime offset: hex bytes}` chunk written at that offset.

    `ret` is the fill because a walk that has not been pointed anywhere useful
    should look finished rather than decode whatever follows it. `end` shortens
    the *buffer* below the region, which the committed image never does."""
    lo, hi = pd_bounds()
    image = bytearray(b"\x22" * (hi if end is None else lo + end))
    for off, text in chunks.items():
        raw = bytes.fromhex(text)
        image[lo + off:lo + off + len(raw)] = raw
    return bytes(image)


def erased_band_holds(d: bytes, lo: int, hi: int) -> bool:
    """True when the `REGIONS` row spanning `lo`-`hi` really is what it claims.

    The premise the `--sites 0xFFFF` floor and the `0x1FFF1` boundary both rest
    on, asked of the table rather than of a comment: the row is looked up by
    its own bounds, and its `how` is put to `band_faults` only if it is a claim
    `CHECKED` declares a test for. A row whose `how` has been edited therefore
    answers false here rather than being measured against a claim the table no
    longer makes -- the self-test goes red on a figure whose source moved, which
    is the failure a longer comment would have hidden.
    """
    row = next((r for r in REGIONS if r[1] == lo and r[2] == hi), None)
    return (row is not None and row[4] in CHECKED
            and not band_faults(d, lo, hi, row[4]))


def reached_self_test(d, check):
    """Pin ../annotations/pd-reached-helpers.csv against a fresh decode.

    The same contract `pd-index-helpers.csv` is pinned under, one row per
    entry this time: the file is not an oracle, so every field is re-derived
    and compared, and the row set is checked against what --bases actually
    reaches rather than against the CSV's own length.
    """
    committed = {r["entry"]: r for r in _csv_rows(REACHED_CSV)}
    fresh = {f"0x{r['entry']:04X}": r for r in reached_entries(d)}
    reached = {f"0x{h:04X}" for r in base_sites(d) for h in r["helpers"]}
    check(reached == set(committed) == set(fresh),
          f"{REACHED_CSV} has one row per entry --bases reaches "
          f"({len(reached)}; got {len(committed)} committed, "
          f"{len(fresh)} re-derived)")
    for entry in sorted(committed):
        got = dict(zip(REACHED_FIELDS, reached_csv_row(d, fresh[entry])))
        # The committed file is read back as text and the row is re-derived as
        # the writer's own values, so both sides are compared as strings.
        drifted = [k for k in REACHED_FIELDS
                   if committed[entry][k] != str(got[k])]
        check(not drifted,
              f"{REACHED_CSV} row {entry} regenerates unchanged "
              f"(terms {committed[entry]['terms']!r}, "
              f"unmodelled={committed[entry]['unmodelled']}"
              f"{'; ' + ', '.join(drifted) + ' differ' if drifted else ''})")

    for entry, want in REACHED_BY_NAME.items():
        got = fresh.get(f"0x{entry:04X}", {})
        check(got.get("terms") == want and not got.get("unmodelled"),
              f"--reached 0x{entry:04X} decodes to {want} "
              f"(got {got.get('terms', '(not reached)')!r})")
    for entry in REACHED_STILL_UNMODELLED:
        terms, _, note, _ = walk_helper(d, entry)
        check(bool(note) and not terms,
              f"0x{entry:04X} stays unmodelled with no term, as "
              f"pd-index-geometry.md 2.2 says it is (got note {note!r})")
    for entry, want in REACHED_GAPS.items():
        _, _, note, _ = walk_helper(d, entry)
        check(note == want, f"0x{entry:04X} still stops where it stopped "
                            f"(got {note!r})")

    totals = dict(entries=len(fresh),
                  decoded=sum(1 for r in fresh.values() if not r["unmodelled"]),
                  unmodelled=sum(1 for r in fresh.values() if r["unmodelled"]),
                  no_term_sites=sum(1 for r in base_sites(d)
                                    if not effective_terms(r["terms"])))
    check(totals == REACHED_TOTALS,
          f"reached-helpers.md's counts hold: {totals['entries']} entries, "
          f"{totals['decoded']} decode, {totals['unmodelled']} do not, "
          f"{totals['no_term_sites']} site(s) with no term")

    # pd-index-geometry.md 3.2's arithmetic, on the widened decode.
    def strides_of(r):
        return {s for t in effective_terms(r["terms"])
                for s in STRIDE_RE.findall(t)}

    def register_in(term, stride):
        # The factor before the multiply, not the whole string before it: a
        # rebasing term writes `=DPTR ← 0x08F8 + low8(R7×0x60)`, and the
        # register in that is R7.
        m = (re.search(r"0x200×([^\s+×)]+)", term) if stride == PAGE_TERM
             else re.search(r"(?:^|[+×(])([A-Za-z0-9{}]+)×" + stride, term))
        return m.group(1) if m and m.group(1) in REGISTER_NAMES else None

    both = [r for r in base_sites(d)
            if "60" in strides_of(r) and PAGE_TERM in " ".join(effective_terms(r["terms"]))]
    same = different = 0
    for r in both:
        sixty = {s for s in (register_in(t, "0x60") for t in effective_terms(r["terms"])) if s}
        page = {s for s in (register_in(t, PAGE_TERM) for t in effective_terms(r["terms"])) if s}
        # One side unresolved counts neither way, which is 3.2's own rule and
        # the reason it reported 40 of 82 rather than a verdict on all of them.
        if not sixty or not page:
            continue
        same, different = (same + 1, different) if sixty == page else (same, different + 1)
    check((len(both), same, different) == (BOTH_TERM_SITES, SAME_REGISTER, DIFFERENT_REGISTER),
          f"{len(both)} site(s) apply both a x0x60 and a 0x200x term; "
          f"{same} name an identified register on both sides and {different} "
          "of those name two different ones -- 3.2's 0x260 collapse")

    # The rule itself, on a chain the committed image cannot pin: A's symbol
    # has to survive `mov rN,a` for the template behind it to be reached, and
    # has to survive it as the *old* symbol rather than as the register's name.
    for load, want, text in (("ef", "R7×0x5E", "carries A's symbol through"),
                             ("ee", "R6×0x5E", "does not rename A")):
        raw = fixture({0x100: load + "75f05ef8a42582f582e5f03583f583e022"})
        check(walk_helper(raw, 0x100)[0] == [want],
              f"mov rN,a {text}: the term behind it is {want}")


def access_self_test(d, check):
    lo, _ = pd_bounds()

    rows = access_rows(d)
    check(access_totals(rows) == dict(constructions=653, accesses=428,
          construction_only=225, anchor_accesses=186, evidence_records=977),
          "inspected census totals: 653 constructions, 428 accesses, 225 construction-only, 186 anchor accesses, 977 evidence rows")
    check(len(base_sites(d)) == 151 and len(base_sites(d, WHOLE_IMAGE)) == 3176,
          "legacy denominator remains 151 low-run / 3176 whole-image anchors")
    templates = immediate_templates(d)
    suffixes = {i for i in templates if i - 1 in templates and d[i - 1] == MUL_AB}
    check(len(templates) == 304 and len(suffixes) == 134,
          "304 immediate-base matches: 170 non-overlapping templates plus 134 add-only suffixes")
    check(d[lo + 0x2BE1:lo + 0x2BE4].hex() == "1256d1" and
          d[lo + 0x56D0:lo + 0x56DC].hex() == "a4246ff582e43408f583e022",
          "committed bytes: 0x2BE1 calls 0x56D1, bypassing MUL at 0x56D0")
    check(any(r["context"] == "0x2BE1>0x56D1" and
              r["construction_runtime"] == "0x56D1" and
              r["terms"] == "DPTR ← 0x086F + A" and
              r["consumer_runtime"] == "0x56DA" and r["direction"] == "read"
              for r in rows), "independently entered 0x56D1 suffix reaches MOVX at 0x56DA")
    for off, raw in {0xC2FA: "9007d0eff075f05ea424f8f582e43408f583e0",
                     0xDA9B: "9007d0eff075f077a4125950e0",
                     0x34D9: "e075f05ea424fcf582e43408f583020faf",
                     0x578E: "e075f077a4249bf9740835f022"}.items():
        check(d[lo + off:lo + off + len(raw)//2].hex() == raw,
              f"0x{off:04X} bytes match independent r2 listing")
    for off, base, consumer, term, anchor in (
            ("0xC302", "0x08F8", "0xC30C", "low8(R7×0x5E)", "0x2C2FA"),
            ("0x5950", "0x0870", "0xDAA7", "low8(R7×0x77)", "0x2DA9B")):
        found = [r for r in rows if r["construction_runtime"] == off and
                 r["effective_base"] == base and r["consumer_runtime"] == consumer and
                 term in r["terms"] and anchor in r["anchors"]]
        check(bool(found), f"automatic discovery {anchor} -> {base} read {consumer}")
    check(any(r["context"] == "0xDAA4>0x5950" and r["consumer_runtime"] == "0xDAA7"
              for r in rows), "direct 0xDAA4 -> 0x5950 handoff retained")
    for consumer in ("0xC2FE", "0xDA9F"):
        check(any(r["consumer_runtime"] == consumer and r["effective_base"] == "0x07D0"
                  and r["direction"] == "write" for r in rows),
              f"preceding {consumer} store remains a separate 0x07D0 snapshot")
    check(any(r["construction_runtime"] == "0x34DD" and "low8(A×0x5E)" in r["terms"]
              and not r["consumer_file"] and r["stop_reason"] == "unmodelled-handoff"
              for r in rows), "mid-routine MOVX clobbers old A; completed arithmetic survives reader tail")
    check(any(r["construction_runtime"] == "0x5792" and r["destination"] == "A:R1"
              and not r["consumer_file"] for r in rows), "0x578E returns A:R1 without an R2 assignment")

    # pd-0x38-consumers.md pins manual traces without widening the census's
    # handoff/stack policy. The short readers/writers must include every access.
    for off, raw in {
            0xB2AE: "75f038a42446f582e43409f58322",
            0xB2B2: "2446f582e43409f58322",
            0xB2D3: "75f038a42476f582e43409f58322",
            0xB28A: "900832e075f038a422",
            0xB263: "1210bcef25e02583f58322",
            0x0FCB: "e0f8a3e0f9a3e0faa3e0fb22",
            0x0F0E: "eb9ff5f0ea9e42f0e99d42f0e89c45f022",
            0xB24C: "fbfaf9f8c3020f0e",
            0x4C27: "900832eff0900834eaf0a3ebf0ed12119c",
            0x4C38: "4c5d004c92014c9e024d15034d2c044d5f054d6f064e8409"
                    "4f5c0a4fc20b4fd60c00004fe1",
            0x119C: "d083d082f8e4937012740193700da3a393f8740193f5828883"
                    "e4737402936860efa3a3a380df",
            0x4D6F: "900834e07004a3e064016003024fe1900832e0ff12f75cef7065",
            0x4E7C: "900832e0ff02d8ee",
            0xF75C: "ef12716ce0ff22",
            0x716C: "75f05ea424e3f582e43408f58322",
            0x104D: "a8828583f0d083d082121064121064121064121064e473"
                    "e493a3c583c5f0c583c8c582c8f0a3c583c5f0c583c8c582c822",
            0x4DB6: "90083d12104d0000000290084112104d00000000",
            0x4D89: "900832e0ff75f06090049112b263120fcbef12b2ae120faf",
            0x4DA7: "12b28a12b2b2120faf",
            0x4DD2: "900832e0fb75f0609004911210bceb12b267120fafeb12b2ae121041",
            0x4E84: "e490083af090083ae0ffc394024003024fe1",
            0x4E96: "900832e0fe12b2d375f002ef1210bce0fca3e04c6003024f53",
            0x4EAF: "900834e0fca3e0fdee12b2d3c083c08290083ae0d082d083"
                    "75f0021210bcecf0a3edf0e490083bf0",
            0x0FAF: "e0fca3e0fda3e0fea3e0ff22",
            0x1041: "ecf0a3edf0a3eef0a3eff022",
    }.items():
        check(d[lo + off:lo + off + len(raw)//2].hex() == raw,
              f"0x{off:04X} manual 0x38 trace bytes match independent r2 listing")
    for context, construction, term, stop, reason in (
            ("0x4D9B>0xB2AE", "0xB2B1", "low8(R7×0x38)", "0x4D9E", "unmodelled-handoff"),
            ("0x4DE8>0xB2AE", "0xB2B1", "low8(R3×0x38)", "0x4DEB", "unmodelled-handoff"),
            ("0x4E9B>0xB2D3", "0xB2D6", "low8(A×0x38)", "0x4EA2", "unmodelled-handoff"),
            ("0x4EB8>0xB2D3", "0xB2D6", "low8(R6×0x38)", "0x4EBB", "stack-detour"),
            ("0x4DAA>0xB2B2", "0xB2B2", "DPTR ← 0x0946 + A", "0x4DAD", "unmodelled-handoff")):
        found = [r for r in rows if r["context"] == context and
                 r["construction_runtime"] == construction]
        check(len(found) == 1 and term in found[0]["terms"] and
              found[0]["row_kind"] == "construction-only" and
              not found[0]["consumer_file"] and found[0]["stop_runtime"] == stop and
              found[0]["stop_reason"] == reason,
              f"{context} retains bounded census outcome despite manual consumer evidence")

    # Byte execution is independent of the string template: in particular CLR
    # does not clear carry, and MOV A,#hi does not add the product high byte.
    def byte_address(raw, a, b):
        carry, regs = 0, {0x82: 0, 0x83: 0, 1: 0}
        i = 0
        while i < len(raw):
            op = raw[i]
            if op == 0xA4:
                product = a*b
                a, b, carry = product & 255, product >> 8, 0
            elif op == 0x24:
                total = a + raw[i+1]
                a, carry = total & 255, total >> 8
            elif op == 0x34:
                total = a + raw[i+1] + carry
                a, carry = total & 255, total >> 8
            elif op == 0x35:
                total = a + b + carry
                a, carry = total & 255, total >> 8
            elif op == 0xF5:
                regs[raw[i+1]] = a
            elif op == 0xF9:
                regs[1] = a
            elif op == 0xE4:
                a = 0
            elif op == 0x74:
                a = raw[i+1]
            else:
                raise AssertionError(f"fixture opcode {op:02x}")
            i += OPCODE_LEN[op]
        return (a << 8 | regs[1]) if 0xF9 in raw else (regs[0x83] << 8 | regs[0x82])

    arithmetic_ok = True
    for base in (0x08F8, 0x0870, 0x089B, 0xFFFC):
        for mult in (0x5E, 0x77):
            for index in (0, 1, 2, 3, 4, 127, 255):
                for full in (False, True):
                    text = (f"a424{base&255:02x}f974{base>>8:02x}35f0" if full else
                            f"a424{base&255:02x}f582e434{base>>8:02x}f583")
                    raw = bytes.fromhex(text)
                    _, term = _match_template(raw, 0)
                    expr = term.format(a=str(index), b=str(mult)).split(" + ")[1]
                    symbolic = (base + eval(expr.replace("×", "*"),
                                {"__builtins__": {}, "low8": lambda x: x & 255})) & 65535
                    arithmetic_ok &= symbolic == byte_address(raw, index, mult)
                add = bytes.fromhex(f"24{base&255:02x}f582e434{base>>8:02x}f583")
                arithmetic_ok &= byte_address(add, index*mult & 255, index*mult >> 8) == (
                    base + (index*mult & 255)) & 65535
    check(arithmetic_ok, "byte-level arithmetic agrees across product overflow, low-add carry, discarded B and 16-bit wrap")

    # pd-index-geometry.md 8.1's four addresses, each pinned against an address
    # worked out by hand from the opcodes rather than from the term string. The
    # sweep above proves the two agree; two wrong strings in agreement sail
    # straight through it, so the expectation has to be a third thing. `not_` is
    # the address the row exists to rule out -- the pre-#74 full product, or the
    # no-carry base, whichever that row is about -- and the row is refused if the
    # bytes produce it. The bytes are the committed ones, so a re-widened
    # template cannot satisfy these by reformatting.
    ctor_runs = {0xC302: "a424f8f582e43408f583",   # 0xC2FA: 0x08F8 + low8(R7x0x5E)
                 0x34DD: "a424fcf582e43408f583",   # 0x34D9: 0x08FC + low8(Ax0x5E)
                 0x5950: "2470f582e43408f583",     # 0xDA9B's suffix: 0x0870 + A
                 0x5792: "a4249bf9740835f0"}       # 0x578E: 0x089B + Ax0x77, A:R1
    for off, run in ctor_runs.items():
        check(d[lo + off:lo + off + len(run)//2].hex() == run,
              f"0x{off:04X} construction bytes are the committed ones")
    for off, a, b, want, not_ in (
            (0xC302, 2, 0x5E, 0x09B4, 0x08B4),   # 2x0x5E = 0xBC; 0xBC+0xF8 carries
            (0xC302, 3, 0x5E, 0x0912, 0x0A12),   # 3x0x5E = 0x011A; B never added
            (0x34DD, 3, 0x5E, 0x0916, 0x0A16),
            # 0x5950 is the add-only suffix, entered with the product already in
            # A:B, so a and b are the halves of Rx0x77 rather than R and 0x77
            # separately. At index 2 that product is below 0x100, which leaves
            # the base-low carry as the only thing left to test there.
            (0x5950, 0xEE, 0x00, 0x095E, 0x085E),
            (0x5950, 0x65, 0x01, 0x08D5, 0x09D5),
            # 0x5792 ends `addc a,b`, so B survives and the full product stands.
            # 0x0900 is what this site would build if it dropped B the way the
            # three DPTR rows do -- `clr a` in place of `mov a,#hi`, which
            # still leaves the carry out of `add a,#0x9B` live into
            # `addc a,#0x08`. 0x0800 would need that carry dropped too, which
            # is not what those rows do.
            (0x5792, 3, 0x77, 0x0A00, 0x0900)):
        got = byte_address(bytes.fromhex(ctor_runs[off]), a, b)
        check(got == want and got != not_,
              f"0x{off:04X} at A=0x{a:02X} B=0x{b:02X} builds 0x{want:04X}, not 0x{not_:04X}")

    # The same rule as a property of the whole census rather than of the four
    # rows above: a multiply addend keeps its full product only where the
    # template ends `addc a,b`. All 21 untruncated rows are the A:R1 form, so a
    # re-widened template shows up here as a DPTR row that kept its product --
    # and the CSV regeneration checks above would not refuse it, because the
    # CSVs would have been regenerated to match.
    untruncated = [r for r in rows if any("×" in p and not p.startswith("low8(")
                                           for p in r["terms"].split(" + "))]
    check(len(untruncated) == 21 and
          all(r["destination"] == "A:R1" for r in untruncated),
          "the census's 21 untruncated products are all the A:R1 form")

    for off, base in ((0xB2B1, 0x0946), (0xB2D6, 0x0976)):
        raw = d[lo + off:lo + off + 10]
        _, term = _match_template(d, lo + off)
        arithmetic_ok = True
        for index in range(256):
            expr = term.format(a=str(index), b="56").split(" + ")[1]
            symbolic = base + eval(expr.replace("×", "*"),
                                   {"__builtins__": {}, "low8": lambda x: x & 255})
            arithmetic_ok &= byte_address(raw, index, 0x38) == symbolic == (
                base + (index * 0x38 & 255))
        check(arithmetic_ok, f"0x{off:04X}: all byte indices retain low8 product and base carry")
        check(byte_address(raw, 4, 0x38) == base + 0xE0 and
              byte_address(raw, 5, 0x38) == base + 0x18,
              f"0x{off:04X}: index 4 carries low-base addition; index 5 discards product high byte")
    suffix = d[lo + 0xB2B2:lo + 0xB2BB]
    check(all(byte_address(suffix, a, b) == 0x0946 + a
              for a in range(256) for b in (0, 0x38, 255)),
          "0xB2B2 uses supplied A, without multiplying again or adding B")
    check(all(byte_address(suffix, index * 0x38 & 255, index * 0x38 >> 8) ==
              byte_address(d[lo + 0xB2B1:lo + 0xB2BB], index, 0x38)
              for index in range(256)),
          "B28A product followed by B2B2 agrees with B2AE for all byte indices")

    raw = fixture({0x100: "ef75f05ea424f8f582e43408f583e0f022"})
    found = access_rows(raw)
    check(len(immediate_templates(raw)) == 2 and access_totals(found)["constructions"] == 1
          and access_totals(found)["accesses"] == 2,
          "no MOV-DPTR anchor: overlapping suffix merges; two consumers stay distinct")
    check(all(len(r["anchors"].split()) > 1 for r in found),
          "multiple backward anchors contribute provenance, not counts")
    raw = fixture({0x100: "ef12030122", 0x200: "ee75f07712030022",
                   0x300: "a4246ff582e43408f583e022"})
    templates = immediate_templates(raw)
    entries, _ = access_entries(raw, templates)
    check(lo + 0x301 in templates and lo + 0x301 in entries and
          any(r["term"] == "DPTR ← 0x086F + R7" and
              r["consumer"] == (lo + 0x30A, ((lo + 0x101, lo + 0x301),), "read")
              for r in access_walk(raw, lo + 0x100, templates, entries)),
          "suffix survives discovery, direct-entry selection and caller walk")
    found = access_rows(raw)
    check({(r["context"], r["terms"], r["consumer_runtime"])
           for r in found if r["row_kind"] == "access"} == {
              ("0x0101>0x0301", "DPTR ← 0x086F + R7", "0x030A"),
              ("0x0204>0x0300", "DPTR ← 0x086F + low8(R6×0x77)", "0x030A")}
          and access_totals(found)["constructions"] == 2
          and access_totals(found)["accesses"] == 2,
          "independent MUL and ADD entries retain distinct terms at the same consumer")
    raw = fixture({0x100: "75f074e4a424f8f582e43408f583e022"})
    ambiguous = access_rows(raw)
    check(len(ambiguous) == 2 and all(r["status"] == "unresolved-alternative" for r in ambiguous)
          and access_totals(ambiguous)["accesses"] == 1,
          "conflicting frames retain two unresolved alternatives but count one access")
    raw = fixture({0x100: "ef75f05ea424f8f582e43408f583e0"
                   "ef75f077a424f8f582e43408f583e022"})
    check(access_totals(access_rows(raw))["constructions"] == 2 and
          access_totals(access_rows(raw))["accesses"] == 2,
          "two constructions at the same base remain separate after one anchor")
    raw = fixture({0x100: "ef75f077a4120300e022", 0x200: "ee75f05ea4120300e022",
                   0x300: "2470f582e43408f58322"})
    found = access_rows(raw)
    check(access_totals(found)["constructions"] == 2 and
          access_totals(found)["accesses"] == 2 and
          any(r["row_kind"] == "body-evidence" for r in found),
          "two callers remain distinct; context-free helper evidence does not count again")
    check({r["terms"] for r in found if r["row_kind"] == "access"} == {
          "DPTR ← 0x0870 + low8(R7×0x77)", "DPTR ← 0x0870 + low8(R6×0x5E)"},
          "bare multiply low product survives the helper handoff")
    for movx, sym in (("f0", "R7"), ("e0", "A")):
        raw = fixture({0x100: f"ef{movx}75f05ea424f8f582e43408f583e022"})
        check(any(f"low8({sym}×0x5E)" in r["terms"] for r in access_rows(raw)),
              f"MOVX {movx} accumulator preservation/clobber")
    for tail, reason in (("700022", "unsupported-branch"), ("c08322", "stack-detour"),
                         ("0422", "unsupported-instruction"), ("020100", "recursion-bound")):
        raw = fixture({0x100: "ef75f05ea424f8f582e43408f583" + tail})
        found = access_rows(raw)
        check(bool(found) and all(r["stop_reason"] == reason for r in found),
              f"completed arithmetic survives {reason}")
    raw = fixture({0x100: "ef75f05ea424f8f582e43408f583e022"})
    templates = immediate_templates(raw)
    found = access_walk(raw, lo+0x100, templates, set(), budget=8)
    check(bool(found) and all(r["reason"] == "instruction-budget" for r in found),
          "instruction budget stops after completed template without dropping it")
    check(access_rows(b"") == [] and access_rows(b"\x22" * (lo+2)) == [],
          "short images are bounded")
    raw = fixture({0x100: "a424f8f582e43408f58390"}, end=0x10B)
    found = access_rows(raw)
    check(bool(found) and all(r["stop_reason"] == "truncated-instruction" for r in found),
          "truncated instruction retains preceding construction")
    filtered = access_rows(d, (0x0800, 0x08FF))
    check(all(0x800 <= int(r["effective_base"], 16) <= 0x8FF for r in filtered)
          and any(r["consumer_runtime"] == "0xC30C" for r in filtered)
          and not any(r["consumer_runtime"] == "0xC2FE" for r in filtered),
          "new spans filter effective base, not preceding MOV-DPTR immediate")
    for name, writer in ((HELPERS_CSV, lambda: write_helpers_csv(d)),
                         (CALLERS_CSV, lambda: write_callers_csv(d, DEFAULT_CALLER_SITES)),
                         (STRIDES_CSV, lambda: write_strides_csv(d, WHOLE_IMAGE)),
                         ("../annotations/pd-index-accesses.csv", lambda: write_access_csv(rows)),
                         ("../annotations/pd-access-strides.csv", lambda: write_access_csv(rows, True))):
        output = io.StringIO(newline="")
        with redirect_stdout(output):
            writer()
        path = os.path.join(os.path.dirname(__file__), name)
        try:
            with open(path, "rb") as fh:
                expected = fh.read()
        except FileNotFoundError:
            expected = None
        check(expected == output.getvalue().encode(), f"{name}: complete CSV bytes/schema/order regenerate")


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
        terms, _, note, _ = walk_helper(d, entry)
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

    # check_site_addr() is a statement about the caller's argument, not about
    # this image, so the top of the legal range is pinned to still walk its
    # whole window: the last read lands at 0x3000E here, inside the 0x3002C
    # ../../docs/findings/opcode-len-bounds-census.md row 10 puts at the end of
    # it as the worst case of 15 three-byte instructions.
    #
    # 0x3002C is that census's arithmetic and 0x3000E is these bytes, and the
    # two do not have the same backing: 0x3000E is `0x2FFFF + 15`, one byte per
    # instruction, and it is only right because the 15 bytes past the region are
    # the ("erased", 0x30000, 0x40000, None, "all 0xFF") row of
    # trace_xdata_refs.REGIONS and disasm8051.OPCODE_LEN[0xFF] == 1. That row
    # was a string in a column every consumer of REGIONS discards, so the floor
    # below used to rest on a comment. It is asserted now, immediately above
    # the assertion that needs it, through the same predicate
    # check_image_map.py measures the whole column with -- imported, not
    # rewritten, for the reason census_ff_fill.py gives about is_fill -- and
    # `python3 ec/tools/check_image_map.py <image>` is the named command that
    # prints the band's size, its distinct byte values and its 0x90 count.
    erased = erased_band_holds(d, 0x30000, 0x40000)
    check(erased and OPCODE_LEN[0xFF] == 1,
          "the 0x30000-0x3FFFF band is the 0xFF fill "
          "trace_xdata_refs.REGIONS calls `all 0xFF` and 0xFF is a one-byte "
          "opcode, so the floor below is these bytes "
          f"(got band holds {erased}, OPCODE_LEN[0xFF] == {OPCODE_LEN[0xFF]})")
    hi = pd_bounds()[1]
    top = site_rows(d, [0xFFFF])[0]
    peak = top["listing"][-1][0]
    check(len(top["listing"]) == SITE_WINDOW and 0x3000E <= peak <= 0x3002C,
          f"--sites 0xFFFF still walks its {SITE_WINDOW}-instruction window, "
          f"last read at file 0x{peak:05X} (got 0x{peak:05X})")
    # 0x1FFF1 is the first address whose window ran off the end of this image
    # before the check, and 0x23478 is a file_offset out of
    # ../annotations/ec-0x07d0-sites.csv -- the plausible wrong column.
    #
    # 0x1FFF1 is `0x40000 - 15 - 0x20000` -- the same arithmetic as 0x3000E
    # above, read from the other end, and it came from the same place: the run
    # of 0xFF from 0x30000 with disasm8051.OPCODE_LEN[0xFF] == 1 puts the
    # pre-change boundary at 0x1FFF1 rather than at the 0x1FFFB the issue
    # predicted, which predicted it on three-byte instructions. 0x3002C is that
    # worst case and 0x1FFF1 is this image's realised figure, so
    # ../../docs/findings/pd-sites-address-range.md's correction 1 carries
    # both, and both now cite the ("erased", 0x30000, 0x40000, None,
    # "all 0xFF") row asserted above.
    #
    # **What the arithmetic above explains is not what makes these two
    # assertions pass, and the difference is the point.** The refusal is
    # check_site_addr()'s, which bounds the caller's *argument* by the width of
    # a DPTR and the region's extent -- not a property of the fill past
    # 0x30000 at all. Measured: splicing 0x00, 0x74 or 0x90 into 0x30000 of a
    # copy of this image moves the `--sites 0xFFFF` peak by one or two bytes
    # and leaves both refusals here exactly as they are, while the premise
    # assertion above goes red. So 0x1FFF1 is where the pre-change walk
    # stopped, and it is still the right arithmetic for that; what the fill
    # decides is the peak, not the boundary.
    for addr in (0x1FFF1, 0x23478):
        try:
            site_rows(d, [addr])
            msg = "<no refusal>"
        except ValueError as exc:
            msg = str(exc)
        check(PD_REGION in msg and "0x0000-0xFFFF" in msg
              and f"0x{lo:05X}-0x{hi - 1:05X}" in msg,
              f"--sites 0x{addr:05X} is refused naming {PD_REGION} and both "
              f"ranges (got {msg!r})")
    # The same argument, the other mode that takes one. 0x1FFE9 and 0x1FFFF
    # raised IndexError from inside the decode before print_helpers() checked;
    # 0x1FFE8, one below the first of them, exited 0 and listed 24 erased
    # bytes. ../../docs/findings/count-bounded-walk-invariant.md has the run.
    for entry in (0x1FFE9, 0x1FFFF):
        try:
            with redirect_stdout(io.StringIO()):
                print_helpers(d, [entry])
            msg = "<no refusal>"
        except ValueError as exc:
            msg = str(exc)
        check(PD_REGION in msg and "0x0000-0xFFFF" in msg
              and f"0x{lo:05X}-0x{hi - 1:05X}" in msg,
              f"--helpers 0x{entry:05X} is refused naming {PD_REGION} and both "
              f"ranges (got {msg!r})")
    # The third mode, and the one whose refusal it inherits rather than
    # declares: caller_rows() has no check_site_addr() call of its own and
    # reaches one through the site_rows(d, [site]) it already makes to decode
    # the site's index registers. So an edit to caller_rows() that stopped
    # calling site_rows() would drop --callers' refusal silently, and this is
    # the only assertion that would notice -- the other two pin their own
    # modes' checks directly. Suppressed because that edit's failure is to
    # start printing a caller list where the diagnostic belongs.
    for site in (0x1FFFF, 0x23478):
        try:
            with redirect_stdout(io.StringIO()):
                print_callers(d, [site])
            msg = "<no refusal>"
        except ValueError as exc:
            msg = str(exc)
        check(PD_REGION in msg and "0x0000-0xFFFF" in msg
              and f"0x{lo:05X}-0x{hi - 1:05X}" in msg,
              f"--callers 0x{site:05X} is refused naming {PD_REGION} and both "
              f"ranges (got {msg!r})")

    # A count bounds work, not the buffer: the region end bounds the walk and
    # the count stays the cap. 0xFFFF is a legal address and the fill past the
    # region is 0xFF, one byte per opcode, so a count-bounded walk listed 24
    # lines here and 23 of them were the fill past the region's end.
    _, top_walk, top_note, _ = walk_helper(d, 0xFFFF)
    check(len(top_walk) == 1 and top_walk[-1][0] == hi - 1
          and top_note.startswith("unmodelled:") and f"0x{hi:05X}" in top_note,
          f"--helpers 0xFFFF stops at the {PD_REGION} end, {len(top_walk)} "
          f"listing line(s) at file 0x{top_walk[-1][0]:05X}, note {top_note!r}")
    # chain_from() cannot be reached on the committed image: the fill there is
    # 0xFF, which is `mov r7,a` -- an instruction the term model now covers, so
    # a walk bounded by len(d) would step over the 0xFF tail silently until its
    # own budget ran out, and report a window that ended rather than a bound.
    # The fixture is SITE_WINDOW of `mov a,rN` at the top of the region instead
    # -- one byte each, and modelled for the same reason, so the chain steps
    # over them too -- and the walk starts eight in, which leaves the region
    # end inside the 12-instruction budget. What is being pinned is that the
    # region end and not the budget stops this walk, and neither `mov` form
    # would stop it.
    run = fixture({0x10000 - SITE_WINDOW: "e8" * SITE_WINDOW}) + b"\xff" * 0x100
    stopped = chain_from(run, lo + 0x10000 - 8, UNKNOWN_A, UNKNOWN_B)[2]
    check(f"0x{hi:05X}" in stopped and not stopped.endswith("ended"),
          f"chain_from stops at the {PD_REGION} end rather than at its budget "
          f"(got {stopped!r})")
    # The buffer is the bound too, and the committed image cannot show it: it
    # carries 65536 bytes of 0xFF past the region, so only a truncated fixture
    # reaches the clamp. Both walkers read past `hi` on one of these and raise.
    short = fixture({0x1F0: "e8" * SITE_WINDOW}, end=0x200)
    _, short_walk, short_note, _ = walk_helper(short, 0x1F8)
    check(short_walk[-1][0] == lo + 0x1FF and f"0x{lo + 0x200:05X}" in short_note,
          f"walk_helper stops at the end of a short image, last line at file "
          f"0x{short_walk[-1][0]:05X}, note {short_note!r}")
    stopped = chain_from(short, lo + 0x1F8, UNKNOWN_A, UNKNOWN_B)[2]
    check(f"0x{lo + 0x200:05X}" in stopped and not stopped.endswith("ended"),
          f"chain_from stops at the end of a short image (got {stopped!r})")

    for entry, want in STRIDE_HELPER_TERMS.items():
        terms, _, _, _ = walk_helper(d, entry)
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
        terms, _, note, _ = walk_helper(d, entry)
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
    groups = caller_rows(d, DEFAULT_CALLER_SITES)
    got_callers = sum(len(p["rows"]) for g in groups for p in g["picks"])
    check(len(want_callers) == got_callers,
          f"{CALLERS_CSV} has {got_callers} row(s) for the four 0x04A6 sites "
          f"(got {len(want_callers)} committed)")

    # The status is a claim about an intersection of two decodes, so it is
    # pinned on both sides rather than against the CSV alone: access_self_test
    # below byte-compares the whole file, which stops it drifting from the tool
    # but could not stop both drifting from the prose together. That is how this
    # column came to contradict 4.2 in the first place. The frame length rides
    # along in the same tuple for the same reason it is a column of its own.
    absent = ("<absent>", "<absent>", "<absent>")
    fresh = {(f"0x{r['site']:04X}", f"0x{r['runtime']:04X}"):
             (" ".join(f"{k}=#0x{v:02X}"
                       for k, v in sorted(r["literals"].items())),
              r["status"], r["frame_insns"])
             for g in groups for p in g["picks"] for r in p["rows"]}
    committed = {(row["site"], row["caller_runtime"]):
                 (row["literals"], row["status"], int(row["frame_insns"]))
                 for row in want_callers}
    check(set(committed) == set(fresh) == set(CALLER_STATUSES),
          f"{CALLERS_CSV}'s keys are exactly the {len(CALLER_STATUSES)} pinned "
          f"site/caller pairs (committed {len(committed)}, computed {len(fresh)})")
    for key, want in sorted(CALLER_STATUSES.items()):
        site, runtime = key
        got = fresh.get(key, absent)
        was = committed.get(key, absent)
        check(got == want and was == want,
              f"{CALLERS_CSV} site {site} caller {runtime}: literals "
              f"`{want[0] or '-'}` / status `{want[1]}` / {want[2]} instruction "
              f"frame (computed `{got[1]}`/`{got[2]}`, committed "
              f"`{was[1]}`/`{was[2]}`)")
    # The 0xE9F5 status is not vacuously true: its three loads are what 4.2's
    # own `r2` listing shows, and emptying the column they are derived from
    # would leave CALLER_NO_INDEX satisfied by a frame with nothing in it.
    e9f5 = [row for row in want_callers
            if (row["site"], row["caller_runtime"]) == ("0xE9F5", "0x66E4")]
    check(len(e9f5) == 1
          and e9f5[0]["literals"] == "R1=#0x00 R2=#0x08 R3=#0x01",
          "0xE9F5's frame still loads R1=#0x00 R2=#0x08 R3=#0x01, so `none an "
          "index register` is a statement about those three, not about none")

    # The two values no committed row reaches, and the two every committed row
    # agrees on. caller_status() is pure, so all five are reachable without an
    # image; the two that matter for a reader who finds a new site are the
    # positive one and the one saying the decode itself resolved nothing.
    #
    # The last two are the frame test, and between them they are what makes the
    # threshold falsifiable rather than merely present: a literal-free row on
    # either side of MIN_FRAME_INSNS gets the value that side implies, and a
    # *literal-bearing* row below the threshold keeps its literal-based value --
    # so moving the frame test above the literal test, or dropping it back to
    # `not literals -> unresolved`, each fails one of the two.
    for lits, regs, insns, want in (
            ({}, {"R3"}, MIN_FRAME_INSNS, UNRESOLVED_CALLER),
            ({"R1": 0, "R2": 8, "R3": 1}, {"R7", "R6"}, 24, CALLER_NO_INDEX),
            ({"R7": 4, "R3": 1}, {"R7", "R6"}, 24, CALLER_INDEX_LOAD),
            ({"R1": 0, "R2": 8, "R3": 1}, set(), 24, CALLER_UNRESOLVED_INDEX),
            ({}, {"R3"}, MIN_FRAME_INSNS - 1, CALLER_SHORT_FRAME),
            ({"R7": 4, "R3": 1}, {"R7", "R6"}, 2, CALLER_INDEX_LOAD)):
        got = caller_status(lits, regs, insns)
        check(got == want,
              f"caller_status({lits or '{}'}, {regs or 'set()'}, {insns}) is "
              f"`{want}` (got `{got}`)")
    # 0x578E's `A:R1 ← 0x089B + A×0x77`: the R1 is a destination, not an
    # index factor. None of the four committed sites has that form, which is
    # why the stripping is covered here rather than left to a real run.
    check(index_registers(["A:R1 ← 0x089B + A×0x77"]) == set(),
          "index_registers reads only the right-hand side of `←`, so 0x578E's "
          "A:R1 destination is not taken for an index register")
    check(index_registers(["DPTR ← 0x08F8 + low8(R7×0x5E)", "0x200×R7"]) == {"R7"}
          and index_registers(["R3×0x60", "0x200×R3"]) == {"R3"}
          and index_registers(["A×0x60", "0x200×R7"]) == {"R7"}
          and index_registers(["R5×0x1F", "{a}×{b}", "A×B"]) == {"R5"},
          "index_registers finds R0-R7 as whole names in a term's right-hand "
          "side, and leaves A, B, {a} and {b} out")

    access_self_test(d, check)

    print()
    if bad:
        print(f"self-test FAILED: {bad} check(s) disagree with the committed "
              "annotations or CSVs")
    else:
        print(f"self-test passed: the helper bodies and terms match "
              f"pd-xdata-overlap.md 3, the four 0x04A6 sites sit where "
              f"trace_xdata_refs.py puts them, the four 0x5E/0x77 addresses sit "
              f"where ec-0x07d0-sites.md 4 puts them, and all six CSVs "
              f"regenerate unchanged (PD image at file 0x{lo:05X})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=None,
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--helpers", nargs="*", metavar="ADDR",
                    help="decode each named index helper and report its DPTR "
                         "term(s); with no argument, the eleven named ones. ADDR "
                         "is a PD runtime address like --sites' and --callers', "
                         "one outside 0x0000-0xFFFF is refused the same way, and "
                         "one inside the file range is answered with the runtime "
                         "address at that file_offset")
    ap.add_argument("--bases", nargs="?", const=BASE_RUN, metavar="SPAN",
                    help="every PD site whose MOV DPTR immediate is in SPAN "
                         "(`all`, or 0xLO-0xHI); with no argument, the low "
                         f"base run 0x{BASE_RUN[0]:04X}-0x{BASE_RUN[1]:04X}")
    ap.add_argument("--sites", nargs="+", metavar="ADDR",
                    help="decode forward from these PD runtime addresses, e.g. 0xC2FA. "
                         "One outside 0x0000-0xFFFF is refused, and one inside the "
                         "file range is answered with the runtime address at that "
                         "file_offset")
    ap.add_argument("--strides", nargs="?", const=BASE_RUN, metavar="SPAN",
                    help="census of the stride constants the decode resolves over SPAN")
    ap.add_argument("--callers", nargs="+", metavar="ADDR",
                    help="bound the caller set of these PD runtime sites, e.g. 0x7421. "
                         "One outside 0x0000-0xFFFF is refused, and one inside the "
                         "file range is answered with the runtime address at that "
                         "file_offset")
    ap.add_argument("--reached", nargs="?", const=BASE_RUN, metavar="SPAN",
                    help="every entry the base sites in SPAN hand DPTR to, with "
                         "the decode outcome each gets; with no argument, the "
                         f"low base run 0x{BASE_RUN[0]:04X}-0x{BASE_RUN[1]:04X}")
    ap.add_argument("--helpers-csv", action="store_true",
                    help="write the helper table as CSV on stdout")
    ap.add_argument("--reached-csv", nargs="?", const=BASE_RUN, metavar="SPAN",
                    help="write the reached-entry table as CSV; with no "
                         "argument, the low base run, which is what the "
                         "committed CSV holds")
    ap.add_argument("--strides-csv", nargs="?", const=WHOLE_IMAGE, metavar="SPAN",
                    help="write the stride census as CSV; with no argument, "
                         "the whole image, which is what the committed CSV holds")
    ap.add_argument("--callers-csv", action="store_true",
                    help="write the caller table for the four 0x04A6 sites as CSV")
    ap.add_argument("--self-test", action="store_true",
                    help="re-check the decode against the committed annotations and CSVs")
    for mode in ("accesses", "accesses-csv", "access-strides", "access-strides-csv"):
        ap.add_argument("--" + mode, nargs="?", const=WHOLE_IMAGE, metavar="SPAN",
                        help="immediate-base candidates; SPAN filters constructed effective base, not MOV-DPTR anchors (default all)")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    fw = args.firmware or os.path.join(here, DEFAULT_FIRMWARE)
    if args.self_test:
        return self_test(fw)
    modes = (args.helpers, args.bases, args.sites, args.strides, args.callers,
             args.reached, args.helpers_csv, args.reached_csv, args.strides_csv,
             args.callers_csv, args.accesses, args.accesses_csv,
             args.access_strides, args.access_strides_csv)
    if all(m is None or m is False for m in modes):
        ap.error("pick a mode: --helpers, --bases, --sites, --strides, "
                 "--callers, --reached, --helpers-csv, --reached-csv, "
                 "--strides-csv, --callers-csv or --self-test")
    try:
        bases_span = parse_span(args.bases)
        strides_span = parse_span(args.strides)
        strides_csv_span = parse_span(args.strides_csv)
        reached_span = parse_span(args.reached)
        reached_csv_span = parse_span(args.reached_csv)
        access_spans = [parse_span(v) for v in (args.accesses, args.accesses_csv,
                        args.access_strides, args.access_strides_csv)]
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

    for idx, span in enumerate(access_spans):
        if span is not None:
            rows = access_rows(d, span)
            if idx % 2:
                write_access_csv(rows, idx >= 2)
            else:
                print_accesses(rows, span, idx >= 2)
    if args.helpers is not None:
        try:
            print_helpers(d, [int(a, 16) for a in args.helpers] or None)
        except ValueError as exc:
            ap.error(str(exc))
    if bases_span is not None:
        print_bases(d, bases_span)
    if reached_span is not None:
        print_reached(d, reached_span)
    if args.sites:
        try:
            print_sites(d, [int(a, 16) for a in args.sites])
        except ValueError as exc:
            ap.error(str(exc))
    if strides_span is not None:
        print_strides(d, strides_span)
    if args.callers:
        try:
            print_callers(d, [int(a, 16) for a in args.callers])
        except ValueError as exc:
            ap.error(str(exc))
    if args.helpers_csv:
        write_helpers_csv(d)
    if reached_csv_span is not None:
        write_reached_csv(d, reached_csv_span)
    if strides_csv_span is not None:
        write_strides_csv(d, strides_csv_span)
    if args.callers_csv:
        write_callers_csv(d, DEFAULT_CALLER_SITES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
