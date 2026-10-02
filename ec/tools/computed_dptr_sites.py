#!/usr/bin/env python3
"""Find the XDATA sites that build `DPH` at run time: `add a,#imm` / `addc
a,#imm` followed by `mov 0x83,a`, and the page each one reaches.

`scan_refs.py` counts `MOV DPTR,#imm16` and `trace_xdata_refs.py` takes the
same sites down to the individual one. Both therefore see one way of naming an
XDATA address in a 8051 instruction out of the several there are, and
`ec/annotations/manual-fan-ctrl-0751.md` §6 is this repository's own worked
counter-example: the EC reads and writes bytes on page `0x0F`, and those tools
report **zero** direct sites for it, because the EC reaches the page by
assembling the pointer in the accumulator over two instructions --
`add a,#lo ; mov DPL,a ; clr a ; addc a,#0x0f ; mov DPH,a` -- and the address
is in neither instruction. This is the `0x07B9` argument again on a second
address, and the same class of error `docs/findings.md` §4d had to retract.

**A sibling tool, not a mode of `trace_xdata_refs.py`, and the reason is
compatibility rather than taste.** That tool's `--csv` default is what
`registers.yaml`'s `static_refs_main_ec` and the committed `0x086x`/`0x0400`/
`0x07C4` tables are reproduced byte for byte from, and its `csv_table()`
docstring says in so many words that the default carries no extra column *so
that the other tables reproduce unchanged*. A new bucket in that output would
change the meaning of a number the rest of the repository quotes without
changing its value. This file imports the region map from it, so there is one
definition of where the PD image starts and no shared output.

**The population is the eight `DPH` builds the issue names, found with no
seeding, and the window width does not decide that.** Every anchored
`mov 0x83,a` is a candidate; the backward window supplies the immediate
`add`/`addc` that put the high byte in A, and the *nearest* one in the window
is the one in force at the store, exactly as `find_indirect_xdata.py` takes the
*last* `P2` write. That yields exactly eight sites on page `0x0F`, all in
bank0, at `0x8AC6`, `0x8AD8`, `0x8AF3`, `0x8B0C`, `0xBCE3`, `0xBDEC`, `0xE86B`
and `0xF312` -- the addresses §6 hand-decoded, and the run prints the `0x0F`
count at several window widths beside the default, because a "8" that is a
function of a knob is not a finding.

**The population is not filtered on a following `movx`, and that is a
decision, not an oversight.** Six of the eight are followed by `movx @dptr`
within two instructions; `0x8AD8` and `0x8AF3` do `setb c ; lcall 0xBDF2` and
`clr c ; lcall 0xBDF2` instead, handing DPTR to a subroutine.
`trace_xdata_refs.classify()` already has a token for that, so the read/write
versus handoff split is a **reported column**. A population filtered on `movx`
would find six of the eight and would have failed the issue's own test while
looking like a clean run.

**The page is carried, not assumed.** `addc` is carry-dependent, so the
immediate alone is not the high byte, and the accumulator's own value decides
whether the immediate is *any* of it. This tool reads A and the carry from the
one instruction before the `add`/`addc` -- the only place it can see them --
and gets three answers, none of them a guess:

  * **determinate** where that instruction establishes both. `clr a` (0xE4)
    clears A *and* the carry, which is the idiom the whole eight use, so
    `clr a ; addc a,#0x0f` is provably `0x0F` and not `0x0F`-or-`0x10`.
  * **a candidate set** `{page, page+1}` where A is known and the carry is not
    -- `mov a,#NN` before the `addc`. A candidate set is printed as a set and
    is **never** collapsed to its low member: that collapse is the §4d shape.
  * **not established**, naming the encoding that defeated it, for everything
    else. An `lcall` before the `addc` leaves A whatever the callee returned,
    and `clr c` (0xC3) establishes the carry *and not the accumulator* -- it
    is a real 8051 spelling and treating it as a page source is the mistake
    this paragraph exists to prevent.

**Only the page is resolved, and the low byte is reported as not resolved.**
`--page 0xNN` answers per image and exits non-zero when the main EC reaches
the page by no site it can establish, which is the answer for `0x07B9` and
`0x07D0` and it is a negative. The *concrete* address the issue also asked for
is not derivable at any of the eight, and the tool says so per row rather than
inventing one: the instruction before each `mov DPL,a` is an `add a,#imm` or
an `add a,r7` whose own base load is a `movx a,@dptr` or a `mov a,#0x80`, so
the low byte is a run-time value. The `low` cell names that supplying
instruction and its offset so a reader can chase it, and the `window` column
carries the decode it was read against.

**A zero is still "not found by this method", and the sentence naming it now
names this scan beside the ones before it.** What it covers is the
`MOV DPTR,#imm16` of `scan_refs.py` and `trace_xdata_refs.py`, the `movx @Ri`
with `P2` paging of `find_indirect_xdata.py`, and this scan; a `DPTR` built
from a stored pointer or a table, one handed in through a subroutine's own
`DPL`/`DPH` writes, and a CODE jump table are not, and neither is the
`mov @Ri,#data` form. `ec/annotations/computed-dptr-sites.md` §"What this
does not establish" carries the same list, and the `movx @Ri` half of it
belongs to `find_indirect_xdata.py`.

**Why no `0x0F00` row was added to `registers.yaml`.** The obvious thing to do
with eight sites on page `0x0F` is to enter the page, and it would break a
prepared upstream patch: `tools/check_power_profile.py` rule 2 *requires*
`0x0F00` to have no `registers.yaml` entry, because `linux/patches/
gm7mg7p-power-profile/` is a fan-table map whose whole claim about that
address is a deliberate absence, and `tools/test_check_power_profile.py` pins
the requirement by deleting `0x0F00` from its own fixture. This pass finds
sites on the page; it says nothing about what the EC *does* with them, and
`0x0F00` is left absent on purpose.

Reads the committed image and writes nothing but stdout.
`ec/annotations/computed-dptr-sites.md` is the write-up and
`ec/annotations/computed-dptr-sites.csv` is the table this reproduces.

Usage:
    python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800
    python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --csv > ../annotations/computed-dptr-sites.csv
    python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --check
    python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --page 0x0F
    python3 computed_dptr_sites.py ../firmware/GMxMGxx_11.800 --page 0x07
"""
import argparse
import bisect
import collections
import csv
import io
import os
import re
import sys

from disasm8051 import OPCODE_LEN, converges_from, inline_arg_len, mnemonic
from trace_xdata_refs import (PD_MARKER, REGIONS, check_table, classify,
                              region_of, repo_path, runtime_addr, walk_why)

SITES_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "annotations", "computed-dptr-sites.csv")

# The two immediate forms that build a DPTR high byte, as {opcode: name}. Both
# are two-byte instructions whose second byte is the immediate, which is the
# page half. The register forms (`add a,r7`, 0x2F, and `addc a,r4`, 0x3C) are
# deliberately not here: `0xE86B` and `0xF312` are found because of the
# `addc a,#0x0f` that precedes their `mov 0x83,a`, and admitting the register
# forms would mean modelling what the register holds, which is the `P2`-from-a-
# register blind spot `find_indirect_xdata.py` already declines to cross.
ADDS = {0x24: "add a,#imm", 0x34: "addc a,#imm"}

# The DPTR bytes. `disasm8051.mnemonic()` prints these as bare `0x82`/`0x83`
# in its `direct` forms and does not name them DPL/DPH, which is the same
# spelling difference `trace_xdata_refs.py`'s DPL/DPH comment is about.
DPL = 0x82
DPH = 0x83
# `mov direct,a` -- the one opcode that stores A into either half. The *low*
# half is read for the address and the *high* half is the anchor, and they are
# distinguished by the operand byte rather than by two tables, so a `mov
# 0x83,a` can never be read as a `mov 0x82,a` by a mistyped constant.
MOV_DIRECT_ACC = 0xF5

# The backward window, in **instructions**. A byte budget is the right shape
# for `find_indirect_xdata.py`, whose population is a one-byte opcode and whose
# window is looking for a *write* of an SFR it did not model. This window is
# looking for a fixed idiom -- `add a,#lo ; mov DPL,a ; clr a ; addc a,#hi ;
# mov DPH,a` -- whose instructions are two bytes each in the form that matters,
# so counting instructions is what makes the number mean the same thing at
# every site. Four is the width of the idiom behind the anchor, and
# `window_sensitivity()` prints what the `0x0F` count does at other widths so a
# reader is never asked to take four on trust.
WINDOW = 4

# The widths the summary prints beside the default, and why these: 2 is the
# narrowest that can still hold an `add`/`addc` (the store is the anchor and is
# not itself in the window), 3 adds the `clr a` that decides the carry, and 6
# and 8 are wide enough to reach past a `mov DPL,a` and the `add` feeding it.
# No claim in this repository rests on which of these is the default.
SENSITIVITY_WIDTHS = (2, 3, 4, 5, 6, 8)

# The main EC, as `region_of()` spells its three regions, and the PD image
# beside it. Named rather than computed so a reader can see that the split is
# a split and not a total: a DPTR in the PD image is another program's byte.
MAIN_EC_REGIONS = ("common", "bank0", "bank1")
PD_REGION = "pd-image"
# `region_of()`'s own refusal, spelled here because `page_report()` has to name
# it: without the `ITE8850-PD` marker the `0x20000-0x2FFFF` span is no program's
# region rather than the PD image's, and a row found there belongs to neither
# total. Never in `MAIN_EC_REGIONS` for the reason `PD_REGION` is not.
UNKNOWN_REGION = "unknown"

# The page a row carries, in the three states it can be in. Two are functions
# because two of the three carry a value, and a reader looking at a cell has to
# be able to see which value produced it.
DETERMINATE = "determinate"
CARRY_UNKNOWN = "carry not established"
# The `access_of()` bucket for a pointer the site only ever reads as CODE.
# Named here rather than spelled at the one call site so `--page`'s closing
# sentence and `access_of`'s own test cannot disagree about which bucket it is.
CODE_ONLY = "CODE pointer, not an XDATA access"

NO_HALF = "not a `mov 0x83,a`"
NO_ADD = "no immediate add/addc in the window"
NO_DPL = "no DPL store in the window"
NO_BEFORE = "no instruction before it in the window"
REGION_START = "start of region"

# A store the anchored walk reached whose high-byte build a nearer store has
# already claimed: the `ret`-then-`F5 83` case `sites()`'s own docstring names.
# It is a limit on the anchored pass rather than on the window, so it carries
# its own token -- folding it into `NO_ADD` would claim "no add in the window"
# about a store whose `add` is sitting in that window.
DUP_BUILD = "high-byte build already claimed by a nearer store"


def window_end(back: int) -> str:
    """The token for a window that used every instruction it was given.

    A function for the reason `trace_xdata_refs.budget_end()` gives: the number
    is the loop's own argument, and a reader looking at a `window exhausted
    (4 instructions)` cell has to be able to see which four."""
    return f"window exhausted ({back} instructions)"


def accum_before(d: bytes, at):
    """(A, carry, how) as of the instruction before `at`.

    `None` for a value is "not established by the one instruction in front of
    the add", which is a limit on the look and not a claim that the accumulator
    held anything in particular. `how` names what was read, so a refusal says
    which encoding defeated it rather than only that something did.

    Only four encodings are read, and the two that are left out are the two
    that matter:

      * `clr a` (0xE4) clears the accumulator **and** the carry on an 8051 --
        the double effect is in the instruction table and is the whole reason
        the eight sites are decidable at all.
      * `mov a,#imm` (0x74) establishes A and leaves the carry alone, which is
        the one spelling that makes a candidate set necessary rather than
        hypothetical.
      * `clr c` (0xC3) and `setb c` (0xD3) establish the carry and leave the
        accumulator alone. **That is why `clr c` is not a determinate
        predecessor**, even though it is the ordinary way to write "no carry":
        `clr c ; addc a,#0x0f` computes `A + 0x0f`, not `0x0f`, and reading it
        as a page is the same over-claim as reading an unresolved `P2` as one.

    `mov a,rN` (0xE8-0xEF) and `inc a` (0x04) write A from a value this tool
    does not model, and a call may return anything; both are refusals naming
    the encoding, for the reason `P2_WRITERS` in `find_indirect_xdata.py` names
    the one that beat it.
    """
    if at is None:
        return None, None, NO_BEFORE
    op = d[at]
    if op == 0xE4:
        return 0, 0, "clr a"
    if op == 0x74 and at + 1 < len(d):
        return d[at + 1], None, f"mov a,#0x{d[at + 1]:02X}"
    if op == 0xC3:
        return None, 0, "clr c"
    if op == 0xD3:
        return None, 1, "setb c"
    return None, None, norm(d, at)


def norm(d: bytes, at: int) -> str:
    """`mnemonic()`'s text, whitespace-normalised.

    Its own docstring's reason for the same call in
    `find_indirect_xdata.py`: the renderer pads operands to a column, so the
    same instruction reads `mov a,r6` in one cell and `mov  a,r6` in another
    and a cell a reader compares against a listing does not match.
    """
    return " ".join(mnemonic(d, at).split())


def page_of(d: bytes, add: int, before):
    """(the page cell, the value or None, the state, the pages it could be).

    Three states and no fourth, and the middle one is a **set**: where the
    accumulator is known and the carry is not, the high byte is one of two
    values, and this returns both. Collapsing that set to its low member is the
    §4d shape -- a claim as though the method had established something it had
    not -- so `page_value` is None in that state and `--page` does not count
    the row either way.

    The fourth element is that set as **data**, and it is the quantity that
    decides the page rather than the immediate: the high byte is `A + imm [+ C]`
    and the two agree only where the accumulator happens to be zero. A
    determinate row's set is the one page it builds, a `CARRY_UNKNOWN` row's is
    the two it might, and a **refusal's is None** -- the accumulator was not
    read, so *every* page is open and no queried page can be ruled out by it.
    Keying that decision on the immediate instead is what let `--page` print a
    bare zero beside a refusal whose page it could not have established.
    """
    acc, carry, how = before
    imm = d[add + 1] if add + 1 < len(d) else 0
    if acc is None:
        if how == NO_BEFORE:
            return NO_BEFORE, None, "refused", None
        return (f"not established; the instruction before it is `{how}`",
                None, "refused", None)
    # `add` and `addc` are two different instructions here and the branch is
    # the whole of it: `add a,#imm` (0x24) is `A + imm` and never reads the
    # carry, so a `setb c` in front of it supplies nothing and adding it would
    # be an off-by-one page. `addc a,#imm` (0x34) is `A + imm + C`, which is
    # why it is the one that needs a candidate set.
    if d[add] == 0x24:
        value = (acc + imm) & 0xFF
        return f"0x{value:02X}", value, DETERMINATE, frozenset({value})
    if carry is not None:
        value = (acc + imm + carry) & 0xFF
        return f"0x{value:02X}", value, DETERMINATE, frozenset({value})
    low = (acc + imm) & 0xFF
    return (f"{{0x{low:02X}, 0x{((low + 1) & 0xFF):02X}}} -- {CARRY_UNKNOWN}",
            None, CARRY_UNKNOWN, frozenset({low, (low + 1) & 0xFF}))


def xaddr_of(page, value, low, lowvalue) -> str:
    """The `xaddr` cell: the concrete address, or which half stopped it.

    Both halves literal is a real address and is rendered as one. A determinate
    page over a run-time low byte is the shape the eight sites have, and the
    cell says *page* and names the supply rather than spelling an address with
    a low byte nobody read -- a cell reading `0x0F20` where the low byte is a
    `movx a,@dptr` result would be exactly the claim the issue's "where the low
    byte is also an immediate" clause is asking the tool to decline.
    """
    if value is None:
        return f"no page; {page}"
    if lowvalue is None:
        return f"page 0x{value:02X}, low byte {low}"
    return f"0x{((value << 8) | lowvalue):04X}"


def mov_half(d: bytes, at: int, half: int) -> bool:
    """Whether the instruction at `at` is `mov {half},a`.

    The opcode and the operand byte both, which is what stops a `mov 0x82,a`
    being read as the anchor and a `mov 0x83,a` as the low half.
    """
    return (d[at] == MOV_DIRECT_ACC and at + 1 < len(d) and d[at + 1] == half)


def dpl_write(d: bytes, at):
    """The `mov DPL,a` at `at`, else None."""
    return at if mov_half(d, at, DPL) else None


def window_before(starts: list, site: int, back: int):
    """(the instruction starts before `site`, why the look stopped).

    The starts are the anchored walk's own, so the window is contiguous with
    the framing the site was found under: an `add` in here is one the linear
    decode actually reaches as an instruction start, not a byte that happens to
    decode. `why` is which of the two guards ended it, because a window that
    ran out and one that reached the region edge are otherwise the same list.
    """
    k = bisect.bisect_left(starts, site)
    out, why = [], None
    while k > 0:
        at = starts[k - 1]
        if len(out) >= back:
            why = window_end(back)
            break
        out.append(at)
        k -= 1
    return out[::-1], why or REGION_START


def anchored_starts(d: bytes, lo: int, hi: int) -> list:
    """Every offset the linear decode of `d[lo:hi]` reaches as an instruction
    start, in order.

    The same walk `find_indirect_xdata.py` makes, and for the same reason: the
    framing evidence (`converges_from()`) and the window behind a site have to
    come from one decision or they are two decisions. `OPCODE_LEN` for the
    length, `inline_arg_len()` for the PD image's inline-argument block, and a
    one-byte re-sync where an instruction would run past the region's end.
    """
    starts, i = [], lo
    while i < hi and i < len(d):
        n = OPCODE_LEN[d[i]]
        if i + n > hi or i + n > len(d):
            i += 1
            continue
        starts.append(i)
        i += n + inline_arg_len(d, i)
    return starts


def resolve_low(d: bytes, behind: list, add: int):
    """(the `low` cell, the value or None) for the address's low byte.

    The nearest `mov DPL,a` at or before `add`, because that is the store whose
    value the high half is built beside -- a `mov DPL,a` after the `add` belongs
    to a different site. The value is read off the one instruction in front of
    the store on the same terms as the page: `mov a,#imm` gives a literal and
    so a concrete address, and every other encoding is a refusal that names it.

    On the committed image no row resolves, which is the issue's "where the low
    byte is also an immediate or a known-value read" answered as an evidenced
    negative: the instruction in front of each store is an `add a,#imm` or an
    `add a,r7` whose own base load is a `movx a,@dptr` or a `mov a,#0x80`.
    """
    store = next((at for at in reversed(behind) if dpl_write(d, at)), None)
    if store is None:
        return NO_DPL, None
    j = behind.index(store)
    supply = behind[j - 1] if j > 0 else None
    if supply is not None and d[supply] == 0x74 and supply + 1 < len(d):
        return f"literal 0x{d[supply + 1]:02X}", d[supply + 1]
    what = NO_BEFORE if supply is None else f"`{norm(d, supply)}` at 0x{supply:05X}"
    return f"at run time; A from {what}", None


def store_verdict(d: bytes, starts: list, store: int, pd_verified: bool,
                  back: int = WINDOW):
    """(the row for one anchored `mov 0x83,a`, or None; why it is not a site).

    One store in, one verdict out, so `sites()` and the summary's census of
    what it declined are the same walk and cannot disagree.

    The two refusals are kept apart because they are different claims, and the
    suite pins them separately:

      * `NO_ADD` -- the window held no immediate `add`/`addc`, so nothing in it
        built this store's high byte. The store is a `mov DPH,a` fed some other
        way, and the window is where the tool was looking.
      * `window_end(back)` -- the window ran out before it reached one. That is
        a limit on the look rather than a fact about the instruction, and a
        wider `--window` may turn it into a site or may not.

    Every offset is bounds-checked here rather than left to the caller's loop,
    for the reason `trace_xdata_refs.is_dptr_rebuild()` documents: a truncated
    buffer has to get a verdict and not an `IndexError`, and a crash on a
    short fixture is the shape of a latent hole.
    """
    if store < 0 or store + 1 >= len(d) or not mov_half(d, store, DPH):
        return None, NO_HALF
    behind, why = window_before(starts, store, back)
    # Nearest first: the last write to A before the store is the one in force at
    # it, so an `add a,#lo` four instructions back behind a nearer
    # `addc a,#0x0f` supplies nothing.
    add = next((at for at in reversed(behind) if d[at] in ADDS), None)
    if add is None:
        return None, NO_ADD if why == REGION_START else f"{NO_ADD} ({why})"
    j = behind.index(add)
    before = accum_before(d, behind[j - 1] if j > 0 else None)
    page, value, state, pages = page_of(d, add, before)
    low, lowvalue = resolve_low(d, behind[:j + 1], add)
    onto, over = converges_from(d, add)
    return {
        "offset": add,
        "dph_store": store,
        "region": region_of(add, pd_verified)[0],
        "runtime": runtime_addr(add, pd_verified),
        "form": norm(d, add),
        "frame_onto": onto,
        "frame_over": over,
        "page": page,
        "page_value": value,
        "page_state": state,
        # The pages this row can be, or None where the accumulator was not
        # established and every page is open. The immediate is deliberately not
        # a field of its own: it is already spelled in `form`, and carrying it
        # separately is what let `--page` read a page off it instead of off this.
        "page_candidates": pages,
        "low": low,
        "low_value": lowvalue,
        "xaddr": xaddr_of(page, value, low, lowvalue),
        # The walk starts at the store rather than at the add, because the
        # store is where DPTR is complete; `classify`'s `skip=0` is its
        # "already mid-routine" spelling, the one its own docstring gives for a
        # walk that does not begin with the `MOV DPTR`.
        "access": classify(walk_why(d, store)[0]),
        # The anchoring store is appended to the window so the column reads as
        # the idiom §6 spells -- `... ; add a,#0x20 ; mov 0x82,a ; clr a ;
        # addc a,#0x0f ; mov 0x83,a` -- rather than as a fragment that stops one
        # instruction short of the instruction it explains.
        "window": " ; ".join(norm(d, at) for at in behind + [store]),
        "window_why": why,
    }, None


def stores(d: bytes):
    """Yields (that region's anchored instruction starts, its `mov 0x83,a`s).

    A generator rather than a list because the summary walks all of them to
    count and `sites()` walks them again to resolve, and a 256 KiB image's two
    walks are not worth a third copy of both. `starts` is yielded beside the
    stores rather than recomputed by the caller, because a store resolved
    against a *different* walk's framing than the one that found it would be a
    site whose window is not contiguous with its own evidence.

    Split out of `sites()` because the summary needs the anchored `mov 0x83,a`
    count whether or not each store turned out to be a site: a run that reports
    only the sites cannot show the reader how many stores it declined and why,
    and "how many did you look at" is the question a zero invites.
    """
    for _name, lo, hi, base, _how in REGIONS:
        if base is None:
            # No runtime base: the two `erased` rows of REGIONS, and the one
            # definition of what they are stays REGIONS'. 0xFF is `mov r7,
            # direct` on a 8051, so a walk through them would decode filler as
            # instructions and report it as sites.
            continue
        starts = anchored_starts(d, lo, hi)
        yield starts, [s for s in starts if mov_half(d, s, DPH)]


def sites(d: bytes, pd_verified: bool, back: int = WINDOW) -> list:
    """Every anchored `mov DPH,a` an immediate `add`/`addc` supplies the high
    byte for, with the row this tool prints for it.

    One function so the `--csv` table, the summary and the `--page` answer are
    three views of the same walk and cannot disagree about the population or a
    site's region. `region_of()` decides the region and returns `unknown`
    rather than `pd-image` when the marker is absent, so a dump that is not
    this one gets the refusal instead of a borrowed conclusion.

    **A store is a site, and a high-byte build is a site once.** The linear
    walk does not stop at control flow, so a `ret` in the middle of a routine
    leaves the next byte to be decoded as an instruction -- and where that byte
    is `F5 83`, a second store opens with the *same* `addc` in its window. The
    nearest store is the one the build feeds and the row names it, and a build
    already claimed is not claimed again. Claiming it twice would report one
    instruction twice and make the population a function of what follows a
    `ret`, which is the anchored pass's own limitation
    `indirect-xdata-sites.md` §5 names and no reader should have to rediscover.
    """
    out, claimed = [], set()
    for starts, found in stores(d):
        for store in found:
            row, _why = store_verdict(d, starts, store, pd_verified, back)
            if row is None or row["offset"] in claimed:
                continue
            claimed.add(row["offset"])
            out.append(row)
    return out


def declined(d: bytes, pd_verified: bool, back: int = WINDOW):
    """[(the store's offset, why it is not a site)] over the anchored stores.

    The offset is carried beside the reason so a reader who wants to go and
    look at one of them has the address the reason is about, rather than a
    count and a guess at which stores it named.

    Reported by the summary beside the sites, because a `mov 0x83,a` this scan
    did not count is a limit on the method and a reader is entitled to know how
    many there were.

    **This is the complement of `sites()`, under `sites()`'s own dedup rule, so
    the two partition the anchored stores.** A store is declined for one of
    three reasons and each is its own claim: the window held no immediate
    `add`/`addc`, the window ran out before it reached one, or the build is one
    a nearer store already claimed (`DUP_BUILD`). That third case is the reason
    a census built out of `store_verdict()`'s refusals alone would leave the
    arithmetic a reader checks on every run short by one reason per duplicated
    build -- the store *was* resolved, and it is the dedup rule, not the window,
    that keeps its row out of `sites()`. None of the three is a claim about the
    byte.
    """
    out, claimed = [], set()
    for starts, found in stores(d):
        for store in found:
            row, why = store_verdict(d, starts, store, pd_verified, back)
            if row is None:
                out.append((store, why))
            elif row["offset"] in claimed:
                out.append((store, DUP_BUILD))
            else:
                claimed.add(row["offset"])
    return out


def raw_sites(d: bytes) -> list:
    """Every offset holding the two bytes of a `mov 0x83,a`, framed or not.

    Reported, never tabulated. It exists so the summary can print the anchored
    count beside the count a two-byte byte scan would have found, which is the
    only way a reader can see that a `F5 83` inside somebody's immediate is not
    a site. It is printed beside the anchored count and is not a column of the
    committed table: it is a property of the image that any re-run reproduces,
    and a table column nothing queries would be a second number to keep true."""
    return [i for i in range(len(d) - 1)
            if d[i] == MOV_DIRECT_ACC and d[i + 1] == DPH]


def supply_shape(cell: str) -> str:
    """The shape of a run-time `low` cell's supplying instruction.

    `add a,#0x27` and `add a,#0xa5` are one shape and thirty rows, and a
    summary that printed the immediates would be a wall of singletons a reader
    stops looking at half way down -- the same defect `find_indirect_xdata.py`'s
    `writer_census()` exists to avoid. Immediates and register numbers are the
    site's own data and are in the CSV; what the summary has to say is *which
    kind* of instruction supplied the accumulator, and the per-immediate value
    of that is nil.
    """
    text = cell.split("A from ")[-1]
    text = text.rsplit(" at 0x", 1)[0]
    text = re.sub(r"#0x[0-9a-fA-F]{2}", "#imm", text)
    return re.sub(r"\br([0-7])\b", "rN", text)


def access_of(access: str) -> str:
    """The summary's bucket for one `classify()` cell.

    Keyed on the four shapes `classify()` actually returns rather than on a
    substring, because `"x" in access` is true of `read x1` and of `movc
    a,@a+dptr x1` alike and would file a CODE pointer under an XDATA heading --
    which is the confusion `trace_xdata_refs.classify()`'s own docstring opens
    by keeping `movc` and a jump table out of the "no movx" catch-all. The
    strings are that tool's, and a change to them is a change to this bucket's
    vocabulary rather than a silent reclassification.
    """
    if access.startswith("DPTR handed to"):
        return "hands DPTR to a subroutine"
    if "CODE pointer" in access:
        return CODE_ONLY
    if access == "no movx found in the decoded window":
        return "no movx in the decoded window"
    return "reads or writes through @dptr"


def page_histogram(rows: list) -> collections.Counter:
    """The determinate pages of `rows`, for the summary."""
    return collections.Counter(r["page_value"] for r in rows
                               if r["page_value"] is not None)


def page_of_sites(d: bytes, pd_verified: bool, page: int, back: int = WINDOW):
    """(hits per region, the rows whose page this tool could not establish but
    could not rule out either), for `--page` and the summary.

    Split in two because a refusal is not evidence. A site whose accumulator
    this tool could not read is neither a hit on page `0x07` nor a miss for it,
    and an answer that printed only the count would be claiming the second
    about every site in the second list.

    **A row is undecided for `page` when `page` is one of the pages it can
    build, and a row whose accumulator was not read is undecided for every
    page.** Both halves are the row's own `page_candidates`, which `page_of()`
    derives from `A + imm [+ C]`; the immediate is not the test, because it
    agrees with the high byte only where the accumulator is zero. Keying on it
    both missed rows that could reach the queried page and listed rows for a
    page their own candidate set rules out -- the second of which is the worse
    of the two, because it puts a row under a page it cannot be.
    """
    hits = collections.defaultdict(list)
    undecided = []
    for r in sites(d, pd_verified, back):
        if r["page_value"] is not None and r["page_value"] == page:
            hits[r["region"]].append(r)
        elif r["page_value"] is None and (r["page_candidates"] is None
                                          or page in r["page_candidates"]):
            undecided.append(r)
    return hits, undecided


def window_sensitivity(d: bytes, pd_verified: bool, page: int,
                       widths=SENSITIVITY_WIDTHS) -> list:
    """[(width, main-EC site count, main-EC count on `page`)].

    Printed on every run because the number a reader is most likely to quote --
    eight sites on `0x0F` -- is the kind of answer a tunable can manufacture.
    A count that is the same at every width beside the default is a property of
    the image; one that moves is a property of `--window`, and the printout is
    what tells the two apart without the reader re-running the tool."""
    out = []
    for width in widths:
        rows = sites(d, pd_verified, width)
        out.append((width,
                    sum(1 for r in rows if r["region"] in MAIN_EC_REGIONS),
                    sum(1 for r in rows if r["region"] in MAIN_EC_REGIONS
                        and r["page_value"] == page)))
    return out


def csv_table(rows: list) -> str:
    """The `--csv` table, as a string rather than a write.

    `--check` diffs the same bytes this prints, and the tool's contract is that
    it writes nothing but stdout. The columns are the site's identity, the
    framing evidence, the two halves' evidence, the resolution, what DPTR is
    then used for, and the window's own decode -- in that order, so the last
    four together let a reader re-derive every cell before it from the row
    rather than taking it on trust.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["file_offset", "runtime", "region", "form", "dph_store",
                "frame_onto", "frame_over", "page", "low", "xaddr", "access",
                "window"])
    for r in rows:
        w.writerow([
            f"0x{r['offset']:05X}",
            f"0x{r['runtime']:04X}" if r["runtime"] is not None else "",
            r["region"], r["form"], f"0x{r['dph_store']:05X}",
            r["frame_onto"], r["frame_over"],
            r["page"], r["low"], r["xaddr"], r["access"], r["window"]])
    return buf.getvalue()


def page_report(d: bytes, pd_verified: bool, page: int, back: int = WINDOW) -> int:
    """The `--page` answer: who reaches `page`, per image, and who might.

    Returns non-zero when the main EC reaches the page by no site this tool can
    establish, so a scripted caller can use it. The PD image is counted
    separately and never added: a DPTR in it is another program's byte, and
    that is `lightbar-bat-flow.md` §2's mistake and `trace_xdata_refs.py`'s
    docstring's first point. A page **this scan** finds no main-EC site on is
    the answer for `0x07B9` and `0x07D0`, and it is a negative scoped to this
    scan -- so the rows that could not be placed are printed under it rather
    than dropped, because they are the difference between "nothing here" and
    "nothing here that this method could establish". A refusal is in that list
    for *every* page, since the accumulator it could not read leaves the page
    open rather than closed, and a row in the unidentified span a missing
    `ITE8850-PD` marker creates is printed under its own refusal for the same
    reason: it is a row this tool found and would otherwise place nowhere.
    """
    hits, undecided = page_of_sites(d, pd_verified, page, back)
    print(f"page 0x{page:02X}, by the sites whose page this tool can "
          f"establish:\n")
    for region in MAIN_EC_REGIONS + (PD_REGION,):
        found = sorted(hits.get(region, []), key=lambda r: r["offset"])
        if not found:
            print(f"  {region:<9} 0  -- not reached by any site with an "
                  "established page")
            continue
        where = ", ".join(f"0x{r['offset']:05X}" for r in found)
        print(f"  {region:<9} {len(found):>2} site(s) building 0x{page:02X}  "
              f"({where})")
        # DPTR is DPTR, but a `movc a,@a+dptr` riding the same pointer makes it
        # a table lookup in CODE, which is `classify()`'s own docstring saying
        # the site says nothing about a *register* of that number. Reporting the
        # split rather than filtering on it is the same decision the
        # read/write-versus-handoff column is: both are the site's own evidence
        # and neither is a reason to drop a row.
        split = collections.Counter(access_of(r["access"]) for r in found)
        for what, count in sorted(split.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {'':<9} {count:>2} of them {what}")
    # `region_of()` files the `0x20000-0x2FFFF` span under `unknown` when the
    # marker is absent, and none of the three programs above is that. A
    # determinate row there is not a refusal -- it carries a page -- so it is in
    # none of the lists above, and the loop's own regions are what it fell
    # between. Printed under the refusal that named it rather than dropped: a row
    # the tool found and did not place is the one a reader cannot notice is
    # missing, and a zero beside it would read as a measurement.
    loose = sorted(hits.get(UNKNOWN_REGION, []), key=lambda r: r["offset"])
    if loose:
        where = ", ".join(f"0x{r['offset']:05X}" for r in loose)
        print(f"  {UNKNOWN_REGION:<9} {len(loose):>2} site(s) building "
              f"0x{page:02X}  ({where})\n  {'':<9} region unidentified: no "
              f"{PD_MARKER[1].decode()!r}\n  {'':<9} marker, so this is neither "
              "program's page count and it is added to neither.")
    if undecided:
        # "could not place" rather than "whose immediate names", because the
        # second is only true where the accumulator is zero and the list below
        # is now every row that could not rule this page out.
        print(f"\n  and {len(undecided)} site(s) this tool could not place, and "
              f"0x{page:02X} is not\n  ruled out by any of them -- neither a "
              "hit nor a miss, and listed so the zero above is a\n  measurement:")
        for r in sorted(undecided, key=lambda r: r["offset"]):
            print(f"    0x{r['offset']:05X}  {r['region']:<9} {r['page']}")
    main_rows = [r for region in MAIN_EC_REGIONS for r in hits.get(region, [])]
    main_ec = len(main_rows)
    if not main_ec:
        # Scoped to **this scan**, and the scoping is the whole of the claim.
        # `scan_refs.py` and `trace_xdata_refs.py` both find direct
        # `MOV DPTR,#imm16` sites on page `0x07` in the main EC, so a sentence
        # reaching "any of the scans" would be false on the image this tool
        # reads. `find_indirect_xdata.py`'s own `page_report()` scopes the same
        # negative to "this method" for the same reason.
        print(f"\nSo the main EC reaches page 0x{page:02X} at no computed-`DPH` "
              "site this\nscan can establish, and the PD image's computed DPTR "
              "is a different\nprogram's byte either way. That is \"not found "
              "by this method\", and it\nis a statement about the method.")
    elif all(access_of(r["access"]) == CODE_ONLY for r in main_rows):
        print(f"\nEvery one of those sites uses the pointer it built as a CODE "
              f"pointer rather than an XDATA\none, so no XDATA byte on page "
              f"0x{page:02X} is reached this way either. The count above is a "
              "count of\n`DPH` values, not of register references, and the two "
              "are not the same claim.")
    return 0 if main_ec else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write the per-site table as CSV on stdout instead "
                         "of the summary")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against a committed table and exit "
                         "non-zero on any difference (default: "
                         f"{repo_path(SITES_CSV)})")
    ap.add_argument("--page", metavar="0xNN",
                    help="answer the page question: which sites build this "
                         "XDATA page, per image. Exits non-zero when the main "
                         "EC reaches it by no site it can establish")
    ap.add_argument("--window", type=int, default=WINDOW, metavar="N",
                    help=f"backward window in instructions (default: {WINDOW})")
    args = ap.parse_args()

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF are reported as region 'unknown', "
              "not as another image's\n", file=sys.stderr)

    rows = sites(d, pd_verified, args.window)
    table = csv_table(rows)
    if args.check is not None:
        return check_table(table, args.check)
    if args.csv:
        sys.stdout.write(table)
        return 0

    raw = raw_sites(d)
    anchored = [s for _starts, found in stores(d) for s in found]
    by_region = collections.Counter(r["region"] for r in rows)
    anchored_by_region = collections.Counter(
        region_of(i, pd_verified)[0] for i in anchored)
    raw_by_region = collections.Counter(region_of(i, pd_verified)[0] for i in raw)
    main_ec = [r for r in rows if r["region"] in MAIN_EC_REGIONS]

    print(f"{len(raw)} raw `mov 0x83,a` byte pairs in {len(d)} bytes of image. "
          f"A byte scan is the\ngenerous reading, because `F5 83` is a common "
          "operand pair and not just an opcode: the\nanchored decode reaches "
          f"{len(anchored)} of them as an instruction, and\n{len(rows)} of "
          "those have an immediate `add`/`addc` in the window that supplies "
          "their\nhigh byte. The three numbers are populations, not a "
          "refinement of one claim.\n")
    print("  region      site(s)   anchored store(s)   raw pair(s)")
    for region in MAIN_EC_REGIONS:
        print(f"  {region:<9} {by_region.get(region, 0):>7}   "
              f"{anchored_by_region.get(region, 0):>16}   "
              f"{raw_by_region.get(region, 0):>10}")
    # The two totals, on their own lines and never as one number: a computed
    # DPTR in the PD image is another program's byte, and this is the printout
    # that says so every run rather than the docstring.
    for label, regions in (("main EC", MAIN_EC_REGIONS),
                           ("PD image", (PD_REGION,))):
        print(f"  {label:<9} "
              f"{sum(by_region.get(r, 0) for r in regions):>7}   "
              f"{sum(anchored_by_region.get(r, 0) for r in regions):>16}   "
              f"{sum(raw_by_region.get(r, 0) for r in regions):>10}")
    print("  main EC = common area + CODE banks 0 and 1. PD image is a "
          "separate ITE8850-PD\n  program with its own XDATA map, and is "
          "never added to the line above.\n")

    skips = collections.Counter(
        why for _at, why in declined(d, pd_verified, args.window))
    print(f"Of the {len(anchored)} anchored stores, this scan did not turn "
          f"{sum(skips.values())} into a site, and\nthe reason is not the "
          "same claim for all of them -- a window that found no `add` is a\nfact "
          "about the window, one that ran out before it could is a limit on "
          "the\nlook, and a build a nearer store already claimed is a limit on "
          "the anchored\npass rather than on the window:\n")
    for why, count in sorted(skips.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}  {why}")
    print("  These and the sites above are the anchored stores between them, "
          "once each. None of\n  them is a claim about the byte: each is a "
          "`mov 0x83,a` whose high byte did not\n  become a row of its own.")

    states = collections.Counter(r["page_state"] for r in rows)
    print(f"\nOf the {len(rows)} sites, the high byte resolves to a page in "
          f"{states.get(DETERMINATE, 0)}, and the rest are a candidate\nset or "
          "a refusal, named by what the instruction before the `add` was:\n")
    reasons = collections.Counter(
        r["page"] for r in rows if r["page_value"] is None)
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}  {reason}")
    print("  A candidate set is two possible pages, never one: a row whose "
          "carry this tool\n  could not read is not a site on its low member, "
          "and is not counted as one here\n  or by `--page`.")

    print("\nThe pages the main EC reaches by this method, all of them from a "
          "row the anchored\ndecode reaches and an accumulator this tool "
          "could read -- a page absent from this\nlist is built by no site "
          "whose page this scan can establish,\nwhich is a statement about "
          "the method:\n")
    for page, count in sorted(page_histogram(main_ec).items()):
        where = sorted(f"0x{r['offset']:05X}" for r in main_ec
                       if r["page_value"] == page)
        print(f"  0x{page:02X}  {count:>3} site(s)  {', '.join(where)}")

    print("\nWhat DPTR is used for at each site, from the opcodes after the "
          "store. This is a\n**reported column, not a filter**: of the eight "
          "`0x0F` sites, six are followed by a `movx` and\nthe other two hand "
          "DPTR to a subroutine. A population filtered on `movx` would find\n"
          "six of the eight and would have failed the issue's own test while "
          "looking like a\nclean run:\n")
    uses = collections.Counter(access_of(r["access"]) for r in main_ec)
    for what, count in sorted(uses.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:>4}  {what}")

    lows = collections.Counter(
        "literal -- a concrete address" if r["low_value"] is not None
        else "at run time" if r["low"].startswith("at run time")
        else "no DPL store in the window"
        for r in rows)
    print("\nThe low byte, which is what would turn a page into a concrete "
          "address, by what\nthe instruction before each `mov DPL,a` was. A "
          "`literal` cell is the concrete address; a\nrun-time cell names the "
          "instruction that supplied A, so a reader can chase it:\n")
    for what, count in sorted(lows.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}  {what}")
    supplies = collections.Counter(
        supply_shape(r["low"]) for r in rows
        if r["low"].startswith("at run time"))
    for what, count in sorted(supplies.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>4}    supplied by {what}")

    print("\nThe window width, and the `0x0F` count beside it, because a count "
          "a `--window`\ncan manufacture is not a finding. Same image, same "
          "walk, only the width moves:\n")
    print("  width   main-EC site(s)   on page 0x0F")
    for width, total, on0f in window_sensitivity(d, pd_verified, 0x0F):
        mark = "   <- the default" if width == args.window else ""
        print(f"  {width:>5}   {total:>15}   {on0f:>12}{mark}")

    if args.page is not None:
        print()
        return page_report(d, pd_verified, int(args.page, 16), args.window)
    print(f"\n{repo_path(SITES_CSV)} is the per-site table; `--csv` prints it "
          "and `--check` diffs this\nrun against it. "
          "ec/annotations/computed-dptr-sites.md is the write-up, and its "
          "\"what this does not\nestablish\" list is what a zero "
          "here does not cover.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
