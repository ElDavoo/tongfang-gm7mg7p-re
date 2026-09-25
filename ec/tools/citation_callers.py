#!/usr/bin/env python3
"""Ask a citing row's own listing whether it can make the call its comment names.

`call_graph.py` credits a comment to the anonymous callee it names, and
`citation_frames.py` decides whether the *prose* frames the mention as a call.
Neither can see the other half of the question. Seven `bank1` comments each end
"is not supported by these instructions, and that code is not present at this
address", and each still writes a call enumeration -- every mention reads as a
call to a code address, which is exactly what the frame test is for -- but the
address those comments hang off is an unbroken `0xFF` run, `mov R7, A` repeated
to the end of the function. A listing like that cannot make the calls. The
defect was never the sentence; it is the caller.

**Parse the `.asm`, not the `.c`, and not the comment.** That is the whole
discriminator. A rule keyed on the *name* a previous agent gave the row
(`unimplemented_ff_fill_*`) is a convention a future rename breaks silently, in
the quiet direction this gate exists to prevent; a rule keyed on denial prose
("is not supported by these instructions") is a second bag of words beside the
frame test's, and would need re-measuring for wrong rejections exactly as
`citation_frames.FILLER_BUDGET` did. The listing is decidable, is what
`call_graph.py` already trusts over the `.c`, and makes the gate a fact about
code rather than a reading of prose.

**Two questions, one file, and they are independent.**

  * `is_fill(path)` -- the veto. True when every instruction line's first byte
    token is `ff`, and there is at least one instruction line. A 1-byte `0xFF`
    is `MOV R7, A` in the 8051 map, so an all-`ff` run also settles the rest of
    the shape without being asked: every transfer and branch opcode is a
    different byte, so the run carries no `lcall`, no `ljmp`, no `ajmp`/`acall`
    and no `ret`. A listing with *no* instruction line is **not** fill -- that
    is not found by this method, not absent.
  * `transfer_targets(path)` -- the corroboration. The set of transfer targets
    one listing carries, unresolved. `call_graph.py` resolves them through the
    same `Index.resolve` the inbound scan uses, so a corroborated pair is
    settled by the identical rule a real edge is.

The veto is the narrow fill test and not "this listing has no transfer at all".
Measured on the committed tree, 979 commented annotation rows sit on a listing
with zero transfer instructions and 107 of them cite something -- many of them
real calls the listing does not carry because Ghidra's function boundary cut the
call into a neighbouring export, `bank1,E57E`'s "push r7, call 0xE5D6, pop r7"
the clearest. The broad form is a wrong-rejection machine; the `0xFF`-run form
cannot be. `docs/findings/citing-listing-evidence.md` carries both numbers with
the command that re-derives them.

Usage:
    from citation_callers import is_fill, transfer_targets
    is_fill('ec/decompiled/bank1/F512.asm')       # True
    transfer_targets('ec/decompiled/common/0070.asm')
"""
import collections
import re

# All four reach a function. lcall/ljmp are the 3-byte absolute forms; ajmp/
# acall are the 2-byte paged forms, which is exactly why a fixed-width column
# regex drops them -- see the module docstring of `call_graph.py`.
TRANSFERS = ("lcall", "ljmp", "ajmp", "acall")

# The listing's own address column.
ADDRCOL = re.compile(r"[0-9A-Fa-f]{4}")

# What one listing says about the pairs a comment on it might claim. `fill` is
# the veto and `targets` the corroboration; a `(scope, addr)` absent from the
# map built by `call_graph.scan()` has no listing at all, which is neither.
Listing = collections.namedtuple("Listing", "fill targets")


def norm_addr(text):
    """`05E8`, `0x05e8`, `0X5E8` -> `05E8`. One spelling everywhere, because
    every comparison in both tools is a string comparison and the listings are
    inconsistent about the prefix."""
    return text.strip().lstrip("0x").lstrip("0X").upper().zfill(4)


def iter_instructions(path):
    """Yield the whitespace tokens of every instruction line in one `.asm`.

    A line is `<addr> <b0> <b1> <b2> <mnemonic> <operands...>`, where a short
    instruction's absent slots are the single character `-`. The byte region is
    a fixed 9 columns wide, so the mnemonic is always token 4 -- but a
    fixed-width *regex* over the columns is what fails here, because the `-` pads
    are one character, not two. Split on whitespace runs and read by position.

    `ret`, `nop` and `reti` carry no operand and so are five tokens, not six.
    They are instruction lines like any other, and dropping them is how a `ret`
    would slip past the fill test below.
    """
    with open(path, errors="replace") as f:
        for line in f:
            if line.startswith(";"):
                continue
            parts = line.split()
            if len(parts) < 5 or not ADDRCOL.fullmatch(parts[0]):
                continue
            yield parts


def is_fill(path):
    """True when the listing's instruction bytes are an unbroken `0xFF` run.

    The test is on the bytes and not on the mnemonic, because the bytes are what
    the 8051 map fixes: `0xFF` is `MOV R7, A` and nothing else, so "every
    instruction's first byte is `ff`" already rules out the transfer, branch and
    `ret` opcodes without this module carrying a second opcode table to keep in
    step with the first.

    A listing with no instruction line at all is **not** fill. That is the
    calibration rule in the direction that matters: not found by this method is
    never absent, and treating an empty listing as fill would refuse a citation
    on evidence that was never gathered.
    """
    seen = False
    for parts in iter_instructions(path):
        if parts[1].lower() != "ff":
            return False
        seen = True
    return seen


def transfer_targets(path):
    """The set of `norm_addr` targets one listing transfers to, unresolved.

    Unresolved on purpose: which index row a target reaches is
    `call_graph.Index.resolve`'s rule -- a bank listing calling a common-area
    address resolves to the `common` row, and one that reaches two banks' rows
    at the same address resolves to neither -- and that rule has exactly one
    implementation, in the file that owns the index.
    """
    return {target for _site, _form, target in transfers(path)}


def transfers(path):
    """Yield `(site_addr, form, target_addr)` for every transfer in one `.asm`.

    The transfer half of the listing grammar, and the same token-by-position
    rule `call_graph.parse_listing` applies; this is where it lives, so the two
    tools cannot come to disagree about which byte column an `ajmp` puts its
    target in.
    """
    for parts in iter_instructions(path):
        if len(parts) < 6 or parts[4] not in TRANSFERS:
            continue
        operand = parts[5]
        if not operand.lower().startswith("0x"):
            continue
        try:
            target = norm_addr(operand[2:])
        except ValueError:
            continue
        if not ADDRCOL.fullmatch(target):
            continue
        yield norm_addr(parts[0]), parts[4], target
