#!/usr/bin/env python3
"""Read the `ITE8850-PD` image's five interrupt handler targets out of the
`CODE` word table, and settle what the bytes at the four of them no committed
listing holds are.

`pd_image_census.py` pins the *left* half of `pd-image.md` §2.1: that each of
the five interrupt vectors is a wrapper loading DPTR with its own `CODE`
address, and that `0x0050 call_10f1_then_jmp_1229` reads three `CODE` bytes
there and jumps to them. That fixes the five selector addresses and the five
words. What it does not do is read what the words *point at*, and on this
image four of the five land in the two gaps the committed extents leave, so
the page's answer was "whether those four are real handlers, padding, or an
artefact of reading a constant pool as code is not determined here". This tool
is that half: the selector, the three `CODE` bytes, the word, the target, the
opcode at the target, whether a listing starts at or spans it, and who branches
to it.

**The run reads as code, and the finding is the shape rather than any one
entry.** `0xF78B`-`0xF7B7` sits between two committed `forwarder` rows and a
committed bank of `ret`-only stubs, and every entry in it ends the same way: a
bare `ret`, or a `ljmp` forwarder whose own body is nothing. `0xF790` is
`lcall 0xEFEA` then `ret`; `0xF7AE`, `0xF7AF` and `0xF7B0` are each a single
`0x22`. Three of the five interrupt vectors are therefore wired to a no-op
return, which is a statement about the image rather than a guess.

**Why a bare `ret` is the handler's terminator here, and not padding -- the
load-bearing part, and it comes only from committed bytes.** `0x010E
vector_wrapper_dp_015d` pushes 13 registers, `mov dptr,#0x015d`, `lcall
0x0050`, pops 13, `reti`. `0x0050` is `lcall 0x10f1` then `ljmp 0x1229`, so
it pushes nothing of its own. `0x10f1` ends in a `ret`, so
the shared body's own push is gone before the tail jump runs. `0x1229` builds
DPTR from R2:R1 and falls through into `0x122D`, whose last instruction is
`jmp @a+dptr` (`0x73`) and which pushes nothing. **So a handler is reached by a
jump, and the top of stack on entry is the return address the wrapper's `lcall
0x0050` pushed.** A `ret` there pops exactly that and resumes the wrapper at
its first `pop`, which unwinds and executes `reti`.

`chain_is_jump_not_call()` holds that argument to the bytes, link by link, and
the fourth link is the one that makes the third load-bearing: a linear walk
that only asked "does the body end in a jump" would keep saying yes after the
tail jump had become a *call*, because a call falls through.
`calls_left_open()` is that link -- every `lcall` on the shared body's straight
line has to be popped by its own callee, or its return address is still on the
stack when the handler's `ret` runs. Take any one of the four away and the
conclusion stops following from the bytes.

**The same `0x22` bytes are demonstrably callable.** `0xF7B2`, `0xF7B3`,
`0xF7B4` and `0xF7B7` are bare-`ret` stubs *inside this same run*, and
`ec/decompiled/pd/DA44.asm` and `A8AE.asm` `lcall` them. A `0x22` here is a
no-op stub that committed code calls, which is what rules out padding: padding
has no caller.

**A null in this tool is a statement about a search, never about the image.**
The two referrer populations answer different questions and are reported side
by side rather than exchanged. `referrers_in_listings()` reads *decoded*
`lcall`/`ljmp` instructions out of the committed `pd` listings, so an operand
byte cannot masquerade as an opcode. `referrers_in_bytes()` counts every
position in the 64 KiB whose three bytes spell `lcall`/`ljmp` at the target,
which is strictly wider and whose rows are **candidates, not callers**. The
five handler targets are named by no instruction at all -- they are reached by
`jmp @a+dptr` and by nothing else this image spells -- and `0xEFEA` and
`0xE5EB`, the two bodies `0xF790` and `0xF798` call, have **zero** decoded
referrers against byte-scan candidates that no committed listing holds. That is
*not found by this method*, never *unreachable*.
`docs/findings/pd-e2e4-entry-forms.md` is the same two-population contract on
another address, and this tool borrows its vocabulary rather than writing a
third one.

**Framing is reported as framing, and one conflict is left standing.** The
run's interior is read two ways -- one linear walk from `0xF78B`, and one walk
per annotated entry, which is what an entry means -- and `0xF790` is where they
cannot both be right. The `0x1B` vector's word names it, so something jumps
there; the walk from `0xF78B` reads `inc a` at `0xF78E` and then a `jbc` at
`0xF78F` whose operand bytes are `0xF790`-`0xF791`, so it steps over it.
`framing_conflict()` returns the handler targets the walk refuses to land on
rather than picking the reading that closes the gap, because
`disasm8051.py`'s own docstring is that it cannot tell you whether the byte you
pointed it at starts an instruction and nothing else here can either. The
suite asserts the conflict is there, so an edit that resolved it silently takes
the run red.

**The seeds are named, not written.** Seeding the run's interior is what would
put these bytes in `ec/decompiled/pd/`, and it needs `--mode rebuild-project`,
which writes the committed `.gpr`/`.rep` rather than a scratch copy.
`ghidra/project_owner.py` refuses any `rep_dir` outside a scratch root, and
`docs/findings/ghidra-project-owner.md` records that this leaves
`--mode rebuild-project` uncovered and "the mode an agent branch cannot
usefully run". So the annotation rows that would carry these names are the next
step and not this one; `uncovered_in_run()` names the address spans a seed would
have to cover so the next person does not re-derive them. Nothing here needs
Ghidra at all.

Usage:
    python3 ec/tools/pd_vector_handlers.py
    python3 ec/tools/pd_vector_handlers.py --check
    python3 ec/tools/pd_vector_handlers.py --run 0xF78B,0xF790

`--check` re-derives `pd-image.md` §2.1's handler table in both directions and
exits non-zero on any difference. Nothing here needs Ghidra, a network or
hardware: every input is a committed file.

**The tool is not registered in any gate.**
`.github/scripts/agent-gates.sh` is a pipeline file and this branch's token has
no `workflow` scope, so registering it is a human's change; it is runnable and
cited standalone, and `bash tools/run-tests.sh` finds its suite by the runner's
own `test_*.py` rule. That is the arrangement `pd-image.md` §0 records for
`pd_image_census.py`, for the same reason.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from disasm8051 import (OPCODE_LEN, REL_OPCODES, decode, mnemonic,  # noqa: E402
                        paged_target, relative_target)
import pd_image_census as census  # noqa: E402

DECOMPILED = census.DECOMPILED
PAGE = census.PAGE

# The region read, the marker refusal, the vector walk, the wrapper shape and
# the extents all belong to `pd_image_census.py`; imported rather than restated
# so the two tools cannot answer the same question differently. The import is
# one-way on purpose, so each still runs on its own.
NOT_FOUND = census.NOT_FOUND
Refusal = census.Refusal

# The opcodes this tool reads by name, so a table of three numbers never has to
# carry `0x22` where `ret` is the claim. PUSH_DIRECT comes from the census
# rather than being restated.
LCALL = census.LCALL
LJMP = census.LJMP
RET = 0x22
RETI = 0x32
JMP_AT = 0x73
PUSH_DIRECT = census.PUSH_DIRECT

# What ends a function body, as opposed to what ends a linear walk. `lcall`
# falls through, so a routine that calls something and then returns is one
# body across both -- which is why the per-entry reading stops here and the
# linear one does not.
BODY_END = (LJMP, RET, RETI)

# The chain `ret`-terminates on. `0x010E` is the `0x23` vector's wrapper, the
# long form; `0x0050` is the shared body all five call; `0x1229` builds the
# handler's DPTR out of the two bytes `0x10f1` read. Take any one of the three
# away and "a `ret` at the handler pops the wrapper's return address" stops
# following from the bytes.
WRAPPER_ENTRY = 0x010E
SHARED_BODY = 0x0050
DPTR_LOAD = 0x1229

# The run this tool reads as a whole, and the two addresses whose referrer
# census the reading depends on: they are the bodies `0xF790` and `0xF798`
# call, and neither has a committed listing.
RUN_FIRST = 0xF78B
RUN_LAST = 0xF7B7
HANDLER_BODIES = (0xEFEA, 0xE5EB)

# The two bytes in front of the conflicted target, whose framing nothing here
# settles. Named because `branches_to()` is asked about them by name rather
# than about "whatever is unframed", so a future run reports over a fixed set.
UNFRAMED = (0xF78E, 0xF78F)

# The bare-`ret` stubs in the run that committed code `lcall`s. They are the
# negative control for "a 0x22 here is a no-op stub, not padding"; the suite
# pins the set by value, so a value restated here could only ever be wrong in
# one place.
RETS_CALLED = (0xF7B2, 0xF7B3, 0xF7B4, 0xF7B7)

# The instruction-line pattern a committed listing's rows match: the address
# column, then the byte column, then `lcall`/`ljmp` and an absolute operand.
# Anchored to the start of a line, so a `0xf7b2` inside a comment is not read
# as an instruction, and the byte column is required, so a line that names an
# address without decoding one is not either.
LISTING_CALL = re.compile(r"^([0-9A-Fa-f]{4})\s+[0-9a-f]{2}"
                          r"(?:[ 0-9a-f]{2})*\s+(lcall|ljmp)\s+"
                          r"0x([0-9a-f]+)\s*$", re.M)


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, census.REPO)


# --------------------------------------------------------------------------
# The handler table


def handlers(region: bytes, extents=None, names=None):
    """One row per interrupt vector, from the wrapper down to the target byte.

    Reads the same two facts `census.vector_pointer_table()` reads -- the
    wrapper's `mov dptr` immediate, and the three bytes `0x10f1` fetches there
    -- and then keeps going, which is the half that tool stops at. The word is
    big-endian over the *second and third* of those three bytes, because
    `0x1229` builds DPTR from R2:R1 and R2:R1 are the second and third
    (`pd,0x10F1`'s own comment says so); the first is fetched into R3 and the
    jump does not use it.

    `starts` / `spans` come from the committed listings' own address columns
    rather than from a nearest-preceding-start rule, for the reason
    `census.owning_function()` gives: the export's bodies overlap, so "the
    nearest function start at or below" attributes an address to a function
    that demonstrably does not contain it.

    Returns [(vector, selector, target, sites, triple, opcode, starts, spans,
    listing name)].
    """
    extents = census.function_extents() if extents is None else extents
    names = census.function_names() if names is None else names
    owners = census.address_owners(extents)
    out = []
    for vector, dptr, sites, _readers in census.vector_pointer_table(region,
                                                                     owners,
                                                                     names):
        triple = region[dptr:dptr + 3]
        if len(triple) != 3:
            out.append((vector, dptr, None, sites, b"", None,
                        NOT_FOUND, NOT_FOUND, NOT_FOUND))
            continue
        target = (triple[1] << 8) | triple[2]
        op = region[target]
        # `extents` is keyed on the entry address, so a listing *starts* here
        # exactly when the address is one of its keys; a listing that merely
        # holds the byte is a span.
        starts = target if target in extents else None
        spans = sorted(e for e, addrs in extents.items()
                       if e != target and target in addrs)
        out.append((vector, dptr, target, sites, triple, op,
                    "yes" if starts is not None else NOT_FOUND,
                    ", ".join(f"0x{e:04X}" for e in spans) or NOT_FOUND,
                    census.function_name(starts, names)
                    if starts is not None else NOT_FOUND))
    return out


def handler_shapes(region: bytes, extents=None, names=None):
    """{target: a short phrase for what is at it} over the handler table.

    The phrase is what `pd-image.md` §2.1's "that target is" column states, so
    the page and this tool are held to each other on the claim as well as on
    the address -- a page edit that kept every address and lost the shape is the
    drift `--check` exists to catch. Derived from the bytes and the committed
    listing set, never transcribed: a handler at a committed entry reads as
    that entry's name, a target whose first byte is `ret` reads as `ret`, and
    a `lcall` immediately followed by a `ret` reads as both, because that is
    the body as far as the bytes say it goes.
    """
    extents = census.function_extents() if extents is None else extents
    names = census.function_names() if names is None else names
    out = {}
    for _v, _d, target, _sites, _triple, _op, starts, _spans, name in handlers(
            region, extents, names):
        if target is None:
            continue
        if starts == "yes":
            out[target] = f"a committed entry, `{name}`"
        elif region[target] == RET:
            out[target] = "`ret`"
        elif region[target] == LCALL:
            callee = (region[target + 1] << 8) | region[target + 2]
            tail = target + OPCODE_LEN[LCALL]
            out[target] = (f"`lcall 0x{callee:04X}`"
                           + (" then `ret`" if region[tail] == RET else ""))
        else:
            out[target] = mnemonic(region, target, target)
    return out


# --------------------------------------------------------------------------
# The chain that makes `ret` the terminator


def wrapper_pushes_return_address(region: bytes, entry: int = WRAPPER_ENTRY):
    """(the `lcall` a wrapper makes, how many `push direct` instructions it has,
    whether it ends in `reti`) at `entry`.

    The count is over the whole wrapper, not only what comes before the call:
    it is what the report prints beside the `lcall`, and the property the link
    rests on is that the wrapper saves and restores at all.

    The `lcall` is what puts a return address on the stack, and therefore what
    a `ret` at the handler will pop. This is the load-bearing link of the
    `ret`-is-not-padding argument, and it is walked over the image rather than
    read off the export, so the argument does not rest on the very export the
    question is about.
    """
    i, callee, pushes, reti = entry, None, 0, False
    while i < len(region) and i - entry < 128:
        op = region[i]
        if op == LCALL and callee is None:
            callee = (region[i + 1] << 8) | region[i + 2]
        elif op == PUSH_DIRECT:
            pushes += 1
        elif op == RETI:
            reti = True
            break
        i += OPCODE_LEN[op]
    return callee, pushes, reti


def last_transfer(region: bytes, entry: int):
    """The first unconditional transfer at or after `entry`, as (addr, opcode).

    `BODY_END` rather than every flow opcode, because `lcall` falls through:
    a routine that calls something and then returns is one body across both,
    and a walk that stopped at the call would report the rest of it as absent.
    """
    i = entry
    while i < len(region) and i - entry < 64:
        op = region[i]
        if i + OPCODE_LEN[op] > len(region):
            break
        if op in BODY_END:
            return i, op
        i += OPCODE_LEN[op]
    return None, None


def calls_left_open(region: bytes, entry: int):
    """[(site, callee)] for the `lcall`s on `entry`'s straight line whose own
    return address survives to the body's tail jump.

    `0x0050` is `lcall 0x10f1` then `ljmp 0x1229`. The `lcall` pushes, and
    whether that push matters depends entirely on whether the callee pops it:
    `0x10f1` ends in a `ret`, so the stack is back to where the wrapper left it
    when the tail jump runs. An `lcall` to a routine that does *not* return --
    which is what an edit turning the tail jump into a call would produce, since
    the next `lcall` would target `0x1229`, whose body ends in
    `jmp @a+dptr` -- leaves a return address on top, and a `ret` at the handler
    would then pop *that* rather than the wrapper's.

    This is the link that makes the tail-jump link load-bearing rather than
    decorative: `last_transfer()` on its own only says the body's last
    transfer is a jump, and would keep reporting that after the jump became a
    call, because a call falls through.
    """
    out = []
    i = entry
    while i < len(region) and i - entry < 64:
        op = region[i]
        n = OPCODE_LEN[op]
        if i + n > len(region):
            break
        if op == LCALL:
            callee = (region[i + 1] << 8) | region[i + 2]
            _at, callee_op = last_transfer(region, callee)
            if callee_op != RET:
                out.append((i, callee))
        elif op in BODY_END:
            break
        i += n
    return out


def dispatch_reaches_target_by_jump(region: bytes, entry: int = DPTR_LOAD):
    """(address, is a jump) of the transfer that carries control to a handler.

    `0x1229` sets DPTR from R2:R1 and falls through into `0x122D`, whose last
    instruction is `jmp @a+dptr`. A `jmp` pushes nothing; a `call @a+dptr`
    would push a return address that a `ret` at the handler would then pop
    instead of the wrapper's. So the *form* of this instruction is part of the
    argument, not decoration on it -- which is why the suite pins the `0x73`
    and not merely the routine's name.

    Stopped on the indirect jump itself rather than on `BODY_END`, which does
    not list it: an indirect `jmp` is a transfer but not one of the three that
    end a function body, and a walk that kept going past it would report
    whatever it found next as the instruction that carries control here.
    """
    i = entry
    while i < len(region) and i - entry < 16:
        op = region[i]
        if i + OPCODE_LEN[op] > len(region):
            break
        if op == JMP_AT:
            return i, True
        if op in (LJMP, LCALL, RET, RETI):
            return i, False
        i += OPCODE_LEN[op]
    return None, False


def chain_is_jump_not_call(region: bytes):
    """[(ok, phrase)] for each link of the argument, in order.

    All four must hold for "a `ret` at a handler pops the wrapper's return
    address" to follow from the bytes, and each is reported on its own so a
    failure says *which* link broke rather than that the chain did. Three of
    them are single instructions and one is a property of the body's own calls;
    together they are what stops the conclusion resting on a sentence rather
    than on the bytes.
    """
    callee, pushes, reti = wrapper_pushes_return_address(region)
    body_at, body_op = last_transfer(region, SHARED_BODY)
    open_calls = calls_left_open(region, SHARED_BODY)
    at, is_jump = dispatch_reaches_target_by_jump(region)
    return [
        (callee == SHARED_BODY and reti,
         f"0x{WRAPPER_ENTRY:04X} pushes {pushes}, `lcall 0x{callee:04X}`"
         + (", and ends in `reti`" if reti else ", and does not end in `reti`")),
        (body_op == LJMP,
         f"0x{SHARED_BODY:04X} ends in "
         + (f"`{mnemonic(region, body_at, body_at)}` at 0x{body_at:04X}"
            if body_at is not None else "nothing this walk reaches")),
        (not open_calls,
         "every `lcall` on 0x%04X's straight line is popped by its own callee"
         % SHARED_BODY if not open_calls else
         "0x%04X calls %s, which does not return, so its return address "
         "survives to the handler"
         % (SHARED_BODY, ", ".join(f"0x{c:04X} at 0x{s:04X}"
                                   for s, c in open_calls))),
        (is_jump,
         f"0x{DPTR_LOAD:04X} reaches "
         + (f"`{mnemonic(region, at, at)}` at 0x{at:04X}" if at is not None
            else "no indirect jump")),
    ]


# --------------------------------------------------------------------------
# Referrers: two populations, never exchanged


_LISTING_CALLS = None


def listing_calls():
    """[(site, kind, target)] over every committed pd listing, once per run.

    Cached so that asking about seven targets reads the listings once. The
    cache is of the committed tree rather than of an argument, which is the
    trade `census.function_extents()` records about its own; a caller wanting a
    different tree is a different process.
    """
    global _LISTING_CALLS
    if _LISTING_CALLS is not None:
        return _LISTING_CALLS
    try:
        listing_names = sorted(os.listdir(DECOMPILED))
    except OSError as e:
        raise Refusal(f"cannot read {repo_path(DECOMPILED)}: {e}")
    out = []
    for fname in listing_names:
        if not fname.endswith(".asm"):
            continue
        try:
            with open(os.path.join(DECOMPILED, fname), encoding="utf-8",
                      errors="replace") as f:
                body = f.read()
        except OSError:
            continue
        for m in LISTING_CALL.finditer(body):
            out.append((int(m.group(1), 16), m.group(2),
                        int(m.group(3), 16)))
    out.sort()
    _LISTING_CALLS = out
    return out


def referrers_in_listings(target: int, extents=None):
    """Decoded `lcall`/`ljmp` instructions in the committed pd listings.

    Returns [(site, owning entry or None, owning name, kind)]. Zero here is
    *not found by this method* over those listings, never *unreachable*.
    """
    extents = census.function_extents() if extents is None else extents
    names = census.function_names()
    owners = census.address_owners(extents)
    out = []
    for site, kind, tgt in listing_calls():
        if tgt != target:
            continue
        entry = owners.get(site)
        out.append((site, entry,
                    census.function_name(entry, names) if entry is not None
                    else NOT_FOUND, kind))
    return sorted(out)


def referrers_in_bytes(region: bytes, target: int):
    """Every position in the 64 KiB whose bytes spell a call or jump to
    `target`, as [(site, kind)].

    Strictly wider than the decoded population, and every row is a
    **candidate, not a caller**: a byte-aligned scan cannot know whether the
    three bytes it found start an instruction, sit inside one, or are the tail
    of something the export framed differently. Reported beside the decoded
    count rather than instead of it, because the difference says whether a
    target the image does reach is reached by code this repository has read.
    """
    out = []
    for op, kind in ((LCALL, "lcall"), (LJMP, "ljmp")):
        needle = bytes((op, target >> 8, target & 0xFF))
        i = region.find(needle)
        while i != -1:
            out.append((i, kind))
            i = region.find(needle, i + 1)
    return sorted(out)


def refcount_phrase(target: int, region: bytes, extents=None) -> str:
    """The one sentence the report prints, for one target's referrer census.

    Both populations in it, so a reader who saw only the decoded count would
    be missing half of what was searched -- and so a null can never read as an
    absence.
    """
    extents = census.function_extents() if extents is None else extents
    owners = census.address_owners(extents)
    decoded = referrers_in_listings(target, extents)
    candidates = referrers_in_bytes(region, target)
    parts = [f"0x{target:04X}:"]
    if decoded:
        where = ", ".join(sorted({name for _s, _e, name, _k in decoded}))
        parts.append(f"{len(decoded)} decoded referrer(s) from {where}")
    else:
        parts.append(f"{NOT_FOUND} among decoded `lcall`/`ljmp` in the "
                     f"committed pd listings")
    if not candidates:
        parts.append(f"and {NOT_FOUND} in a byte scan of the 64 KiB either")
    else:
        inside = sorted(f"0x{site:04X}" for site, _k in candidates
                        if owners.get(site) is not None)
        outside = sorted(f"0x{site:04X}" for site, _k in candidates
                         if owners.get(site) is None)
        where = (f"inside a committed listing at {', '.join(inside)}"
                 if inside else "none inside a committed listing")
        bits = [f"{len(candidates)} byte-scan candidate(s), of which {where}"]
        if outside:
            bits.append(f"the other {len(outside)} at {', '.join(outside)}, "
                        f"{NOT_FOUND} to hold them")
        parts.append(" and ".join(bits))
    return " ".join(parts)


# --------------------------------------------------------------------------
# The run


def entry_body(region: bytes, entry: int):
    """[(offset, text)] for one entry: its instructions to the transfer that
    ends it.

    A walk instruction by instruction rather than a byte span, so every address
    in it is an instruction start. `lcall` falls through and is stepped over,
    which is what makes a routine that calls something and then returns one body
    across both instead of two.
    """
    out = []
    i = entry
    while len(out) < 64:
        out.append((i, mnemonic(region, i, i)))
        nxt, _op = last_transfer(region, i)
        if nxt is None or nxt <= i:
            break
        i = nxt
    return out


def run_entries(region: bytes):
    """[(entry, [(offset, text)], name)] for every annotated entry in the
    run, entry first in address order.

    The entry set is read out of `ghidra-functions.csv` rather than listed
    here, because the annotation file *is* this repository's record of what is
    an entry -- a row seeds a function in the Ghidra project, and a row whose
    address has no listing fails the build. Hardcoding the addresses would give
    the tool a second opinion of the very thing it is measuring.
    """
    names = census.function_names()
    out = []
    for entry in sorted(a for a in names if RUN_FIRST <= a <= RUN_LAST):
        out.append((entry, entry_body(region, entry), names[entry]))
    return out


def linear_reading(region: bytes):
    """[(offset, text)] for one walk from `RUN_FIRST` to the end of the run.

    Kept separate from `run_entries()` because the two disagree, and the
    disagreement is the finding: this walk steps `0xF78F`'s `jbc` over
    `0xF790`, and `0xF790` is an entry on the other reading because the `0x1B`
    vector's word names it. This is `disasm8051.decode`'s linear reading --
    forward, one instruction at a time, through `ret`s and `ljmp`s alike --
    which is exactly the reading that cannot tell a handler from padding, and
    so the one worth printing next to the per-entry one.
    """
    out = []
    for off, _raw, text in decode(region, RUN_FIRST, len(region),
                                  addr=RUN_FIRST):
        if off > RUN_LAST:
            break
        out.append((off, text))
    return out


def branches_to(region: bytes, addrs):
    """[(site, kind, target)] for every transfer in the region naming one of
    `addrs`, over all four 8051 transfer forms.

    Absolute `lcall`/`ljmp`, the PC-relative branch family and the paged
    `ajmp`/`acall` forms, scanned at every byte offset rather than only at the
    committed instruction starts -- the wider population, so a null from it is
    *not found by this method* and never *nothing branches here*. Used for the
    two unframed bytes in front of `0xF790`, which is the only place this
    write-up says anything reaches nothing, and it would be exactly the wrong
    sentence to say without a search behind it.
    """
    wanted = set(addrs)
    out = []
    for i in range(len(region) - 2):
        op = region[i]
        if op in (LCALL, LJMP):
            kind = "lcall" if op == LCALL else "ljmp"
            target = (region[i + 1] << 8) | region[i + 2]
        elif op in REL_OPCODES:
            kind = mnemonic(region, i, i)
            target = relative_target(op, region[i + OPCODE_LEN[op] - 1], i)
        elif (op in range(0x01, 0x100, 0x20)
              or op in range(0x11, 0x100, 0x20)):
            kind = mnemonic(region, i, i)
            target = paged_target(op, region[i + 1], i)
        else:
            continue
        if target in wanted:
            out.append((i, kind, target))
    return sorted(out)


def uncovered_in_run(extents=None):
    """[(first, last)] for the address spans of the run no listing holds.

    The gaps the committed extents leave inside `RUN_FIRST`-`RUN_LAST`, which
    is where the four unlisted handler targets live and where a seed row would
    have to go. Derived from the listings' own address sets rather than from
    anything the annotations say, so it cannot drift into agreeing with either.
    """
    extents = census.function_extents() if extents is None else extents
    held = set()
    for entry, addrs in extents.items():
        held |= {a for a in addrs if RUN_FIRST <= a <= RUN_LAST}
    out = []
    for addr in range(RUN_FIRST, RUN_LAST + 1):
        if addr in held:
            continue
        if out and out[-1][1] == addr - 1:
            out[-1][1] = addr
        else:
            out.append([addr, addr])
    return [tuple(span) for span in out]


def framing_conflict(region: bytes):
    """Handler targets the linear walk does not put an instruction start at.

    The one place the two readings of the run cannot both be right, and it is
    a *derived* answer rather than a narrated one: a handler target that no
    committed listing holds, and that the walk from `RUN_FIRST` steps over
    rather than landing on. `0xF790` is the live case -- the `0x1B` vector's
    word names it, and the walk reads `0x04` at `0xF78E` and then a `jbc` at
    `0xF78F` whose operand bytes are `0xF790`-`0xF791`.

    Which framing is the executed one is **not settled by anything in this
    image**, and this function says so rather than picking the one that closes:
    `disasm8051.py`'s own docstring is that it cannot tell you whether the byte
    you pointed it at starts an instruction, and nothing else here can either.
    The suite asserts the conflict exists, so an edit that silently resolved it
    takes the run red rather than passing for a reading nobody established.
    """
    linear_starts = {i for i, _t in linear_reading(region)}
    extents = census.function_extents()
    uncovered = {a for span in uncovered_in_run(extents) for a in
                 range(span[0], span[1] + 1)}
    return sorted({h[2] for h in handlers(region)
                   if h[2] is not None and h[2] in uncovered
                   and h[2] not in linear_starts})


# --------------------------------------------------------------------------
# The page


def page_tables(text: str):
    """The `pd-image.md` §2.1 five-word table, as [rows].

    Matched on the header row rather than by table index, because §2.1 holds
    two tables and grows; an index would silently start reading the wrong one.
    """
    out = []
    for block in re.findall(r"(?:^\|.*\n)+", text, re.M):
        rows = [r for r in (ln.strip() for ln in block.strip().splitlines())
                if r]
        cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
        head = [re.sub(r"[`*]", "", c).strip().lower() for c in cells[0]]
        if head[0] == "vector" and head[1].startswith("3 code bytes"):
            out.append(cells)
    return out


def backticked(cell: str):
    """The first backticked token in a table cell, or None."""
    m = re.search(r"`([^`]+)`", cell)
    return m.group(1) if m else None


def _address(token: str):
    """The address in a backticked cell, or None if the cell holds no one."""
    token = token.strip()
    return int(token[2:], 16) if token.lower().startswith("0x") else None


def page_targets(text: str):
    """{vector: (selector, target)} from the committed page's five-word table.

    Read out of the page rather than restated, so a page edit and this tool's
    derivation are two readings of one table rather than one checking a copy of
    the other.
    """
    out = {}
    for cells in page_tables(text):
        for row in cells[2:]:
            if len(row) < 4:
                continue
            vector = backticked(row[0])
            target = _address(backticked(row[3]) or "")
            selector = re.search(r"`0x([0-9A-Fa-f]{4})`-", row[1])
            if vector is None or target is None or selector is None:
                continue
            out[vector.lower()] = (int(selector.group(1), 16), target)
    return out


def derived_targets(region: bytes):
    """{vector: (selector, target, shape)} as this tool derives it."""
    shapes = handler_shapes(region)
    out = {}
    for vector, dptr, target, _sites, _triple, _op, _st, _spans, _name in \
            handlers(region):
        out[f"0x{vector:02x}"] = (dptr, target, shapes.get(target))
    return out


def check_page(path: str = PAGE, region: bytes = None) -> int:
    """Exit code for `--check`: 0 when the page and this tool agree.

    Walks the union of both key sets. A page row this tool does not derive is a
    row nothing re-derives; a row this tool derives and the page does not state
    is one the page could drift on. The "that target is" cell is compared as
    the tool's own phrase, so the shape claim is held to the same standard as
    the address.
    """
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"note: cannot read {repo_path(path)}: {e}", file=sys.stderr)
        return 1
    if region is None:
        region, _how = census.read_region()
    derived = derived_targets(region)
    pinned = page_targets(text)
    rc = 0
    for key in sorted(set(pinned) | set(derived)):
        if key not in pinned:
            sel, tgt, shape = derived[key]
            print(f"  {key}: this tool derives selector 0x{sel:04X}, target "
                  f"0x{tgt:04X} ({shape}); the page states no such row",
                  file=sys.stderr)
            rc = 1
        elif key not in derived:
            sel, tgt = pinned[key]
            print(f"  {key}: the page states selector 0x{sel:04X}, target "
                  f"0x{tgt:04X}; this tool does not derive the row",
                  file=sys.stderr)
            rc = 1
        else:
            page_sel, page_tgt = pinned[key]
            d_sel, d_tgt, _shape = derived[key]
            if page_sel != d_sel:
                print(f"  {key} selector: page says 0x{page_sel:04X}, the "
                      f"bytes say 0x{d_sel:04X}", file=sys.stderr)
                rc = 1
            if page_tgt != d_tgt:
                print(f"  {key} target: page says 0x{page_tgt:04X}, the bytes "
                      f"say 0x{d_tgt:04X}", file=sys.stderr)
                rc = 1
    for cells in page_tables(text):
        for row in cells[2:]:
            if len(row) < 4:
                continue
            vector = backticked(row[0])
            key = vector.lower() if vector else None
            if key not in derived or derived[key][2] is None:
                continue
            if derived[key][2] not in row[3]:
                print(f"  {key} 'that target is': the page cell reads "
                      f"{row[3]!r}; this tool derives {derived[key][2]!r}",
                      file=sys.stderr)
                rc = 1
    if rc == 0:
        print(f"{repo_path(path)} §2.1: every handler row re-derives from the "
              f"committed bytes")
    return rc


# --------------------------------------------------------------------------
# The report


def report(region: bytes) -> str:
    """The human-readable read; every number measured by the call above it."""
    out = []
    w = out.append
    extents = census.function_extents()
    shapes = handler_shapes(region, extents)

    w("pd_vector_handlers.py -- the five interrupt handler targets in the "
      "ITE8850-PD image")
    w("  region at file 0x20000-0x2FFFF of ec/firmware/GMxMGxx_11.800, "
      "identified by its ITE8850-PD marker")
    w("")
    w("1. The five CODE words, and what is at each target")
    w("  vector  selector  3 CODE bytes  word     a listing starts here  "
      "that target is")
    for vector, dptr, target, _sites, triple, op, starts, spans, _name in \
            handlers(region, extents):
        w(f"    0x{vector:02X}      0x{dptr:04X}    {triple.hex(' '):<12} "
          f"0x{target:04X}  {starts}")
        w(f"       {shapes[target]}"
          + (f"  (a listing spans it: {spans})" if spans != NOT_FOUND
             else ""))
    w("  selector = the CODE address the wrapper loads DPTR with; word = the "
      "big-endian")
    w("  second and third of the three bytes 0x10f1 fetches there")
    w("")
    w("2. The chain that makes a bare `ret` the handler terminator here")
    for ok, phrase in chain_is_jump_not_call(region):
        w(f"  [{'ok' if ok else 'NO'}] {phrase}")
    w("  a handler is therefore reached by a jump, so the top of stack on entry")
    w("  is the return address the wrapper's `lcall 0x0050` pushed, and a")
    w("  `ret` there resumes the wrapper at its first `pop`")
    w("")
    w("3. Referrers, as two populations that are never exchanged")
    targets = sorted({h[2] for h in handlers(region, extents)
                      if h[2] is not None} | set(HANDLER_BODIES))
    for target in targets:
        w(f"  {refcount_phrase(target, region, extents)}")
    w("  'decoded' counts instructions out of the committed pd listings;")
    w("  'byte-scan candidate' counts positions whose three bytes spell the")
    w("  call, which is not the same thing and is never reported as a caller")
    w("")
    w(f"4. The run 0x{RUN_FIRST:04X}-0x{RUN_LAST:04X}, read two ways")
    w(f"  one linear walk from 0x{RUN_FIRST:04X}, the reading a disassembler "
      f"gives:")
    for off, text in linear_reading(region):
        w(f"    0x{off:04X}  {text}")
    w("  one walk per annotated entry, which is what an entry means:")
    for entry, walk, name in run_entries(region):
        w(f"    0x{entry:04X} ({name}): "
          + "; ".join(f"0x{off:04X} {text}" for off, text in walk))
    # `gaps`, not `spans`: the name above is the listings that hold a handler
    # target without starting at it, and reusing it here for the run's uncovered
    # ranges would make one name mean two things three hundred lines apart.
    gaps = uncovered_in_run(extents)
    conflict = framing_conflict(region)
    w("")
    w("  addresses in the run no committed listing holds: "
      + ", ".join(f"0x{lo:04X}-0x{hi:04X}" if lo != hi else f"0x{lo:04X}"
                  for lo, hi in gaps))
    w("  of those, the handler targets the linear walk puts no instruction "
      "start at: "
      + (", ".join("0x%04X" % a for a in conflict) or "none"))
    if conflict:
        w("  reported, not resolved: the 0x1B vector's word names 0xF790, and")
        w("  the walk from 0xF78B reads `inc a` at 0xF78E and a `jbc` at")
        w("  0xF78F whose operand bytes are 0xF790-0xF791. Which framing is")
        w("  the executed one is not settled by anything in this image.")
    w("  a scan of every transfer form in the region -- absolute, "
      "PC-relative and")
    w("  paged, at every byte offset -- naming 0xF78E or 0xF78F: "
      + (", ".join(f"0x{site:04X} {kind}" for site, kind, _t in
                   branches_to(region, UNFRAMED))
         if branches_to(region, UNFRAMED) else NOT_FOUND))
    w("")
    w("5. The negative control: bare `ret`s in this run that code calls")
    for stub in RETS_CALLED:
        decoded = referrers_in_listings(stub, extents)
        where = ", ".join(f"0x{site:04X} in {name}"
                          for site, _e, name, _k in decoded) or NOT_FOUND
        w(f"    0x{stub:04X} = `{mnemonic(region, stub, stub)}`, lcall'd from "
          f"{where}")
    w("  a 0x22 here is a no-op stub committed code calls, which is what rules")
    w("  out padding: padding has no caller")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="re-derive pd-image.md §2.1 and exit non-zero on any "
                         "difference")
    ap.add_argument("--run", metavar="ADDR,ADDR",
                    help="print one linear walk from each comma-separated "
                         "address")
    args = ap.parse_args()
    try:
        region, _how = census.read_region()
    except Refusal as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.run:
        for tok in args.run.split(","):
            addr = int(tok.strip().lower().removeprefix("0x"), 16)
            w = [(i, mnemonic(region, i, i))
                 for i, _raw, _t in decode(region, addr, 12, addr=addr)]
            print(f"0x{addr:04X}: "
                  + "; ".join(f"0x{o:04X} {t}" for o, t in w))
        return 0
    if args.check:
        return check_page(region=region)
    print(report(region))
    return 0


if __name__ == "__main__":
    sys.exit(main())