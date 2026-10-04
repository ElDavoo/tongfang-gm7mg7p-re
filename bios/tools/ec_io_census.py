#!/usr/bin/env python3
r"""Census the BIOS's EC index/data writes: every 0xA3/0xA2/0xA4/0xA5 exchange,
with the base, index and data byte each one sends.

Input is committed text -- the per-function `.asm` listings under
`bios/ghidra/listings/`, one file per function, each naming its module,
address and name in its first line. No ROM, no UEFIExtract, no Ghidra: this
tool only reads listings that are already in review.

    python3 bios/tools/ec_io_census.py                    the whole census
    python3 bios/tools/ec_io_census.py --addr 0x07A6      one base:index pair
    python3 bios/tools/ec_io_census.py --module Setup     one module
    python3 bios/tools/ec_io_census.py --unresolved       what it could not read
    python3 bios/tools/ec_io_census.py --write            regenerate the CSV
    python3 bios/tools/ec_io_census.py --check            the committed CSV is current
    python3 bios/tools/ec_io_census.py --self-test        known answers, fixture listings

Why a table, and why this shape. The EC's index/data channel is reached over
the ACPI EC port pair with four command bytes -- `0xA3` for the high byte of
an EC RAM address, `0xA2` for the low byte, `0xA4` to read the byte there and
`0xA5 <val>` to write it (`bios/annotations/ghidra-functions.csv`, row
`OemOcDxe,0xF38`). An address on that channel is therefore **a pair**, never
a literal: `0xA3 0x07` followed by `0xA2 0x41` reaches EC RAM `0x0741`, and
no scan for `0x0741`, `7A6`, `1958` or `0xFE4107A6` can match it. So the row
is keyed on the pair, and a byte scanned on its own answers nothing.

**The row is one access sequence**, the `0xA3`/`0xA2` run with the `0xA4` or
`0xA5` that terminates it. That grouping is the point: the base and the index
mean nothing apart, and a row per command byte would put them in different
rows and make "is this address touched" a question about pairs of rows.

**Three forms, and the middle one is why this is not a text scan.** The value
byte reaches the command in a register or a stack slot, not as an immediate
beside the port byte:

- `immediate` -- `mov R8B, 0x7` next to `mov DL, 0xa3`, or `push 0x7` in the
  32-bit TE modules.
- `caller` -- the byte is the function's own argument, aliased in at entry
  (`mov DIL, R8B`, `mov R8B, DL`, `push dword ptr [ESP + 0x8]`) and loaded
  into it by whoever calls the function. The row is emitted once per call
  site that reads an immediate, and the resolved byte is the one that caller
  passes.
- `unresolved` -- anything else, recorded with the register named and never
  guessed into an address.

**A stack slot is read as this tree's shape reads it, not as an ABI claim.**
The two TE modules that take one push a value, `call`, and `pop` the value
themselves -- so the callee leaves it on the stack -- and they then reach their
own arguments at `[ESP + 0x8]` and `[ESP + 0xc]` (`OemOcPei` `0xFFF827BE`,
`OemHooksPei` `0xFFF818CC`). Those two offsets are therefore the first and
second argument here, and any other offset is reported unresolved by name.
Reading a stack slot as an argument is otherwise a guess, and the whole table
is a claim about which byte goes where.

**The window a value is read in is the call it feeds.** Between two `call`s
nothing else can observe a register, so a scan that walked further would
attribute a value to a command the register was not live for. That is why a
register the window does not define comes back `unresolved` rather than
resolved from an earlier assignment in the same function.

**What this is not.** It reads only what the BIOS sends over this channel. It
does not decide what the EC does with a byte, it does not cover the `0xFE41xxxx`
memory window -- that is a separate survey -- and a site the tool cannot read
is a hole in the table, not an absence of a write.

**The site's shape is an assumption, and a second encoding misses it entirely.**
A site is `mov DL, <command>` followed by a helper call, and `OemI2cDevices`
reaches the same two ports without either: it loads `EDX` with the port and
issues `out DX, AL` inline, so `port_sites()` returns nothing and the module
contributes no row at all -- invisible rather than unresolved. That is a
boundary on the negative this tool supports, recorded in
`docs/findings/bios-ec-io-census.md` section 7; it is not something a wider
scan here would have caught.

The CSV is derived from committed input, which is what makes `--check` a real
gate: it re-derives the file and fails on any difference, so a hand-edited
table cannot survive. This tool is not in `.github/scripts/agent-gates.sh`, and
cannot be from an agent branch; it stands on `tools/run-tests.sh` and its own
`--check` meanwhile.
"""
import argparse
import csv
import io
import os
import re
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LISTINGS = os.path.join(REPO, "bios", "ghidra", "listings")
DEFAULT_CSV = os.path.join(REPO, "bios", "annotations", "ec-io-writes.csv")

CSV_COLUMNS = [
    "module", "func", "func_addr", "site_addr", "port_helper", "abi",
    "base", "index", "data", "direction", "caller", "resolved", "evidence",
]

# --------------------------------------------------------------------------
# The listing format
# --------------------------------------------------------------------------

# `00000F38 48 89 5c 24 08 - - - - - -       mov      qword ptr [RSP + 0x8], RBX`
# The byte column is padded with `-` past the instruction's length, so the
# mnemonic is found by matching the column rather than by counting spaces --
# a fixed-width split mis-reads the short forms, which are most of a listing's
# `mov`s and all of its `push`es.
INSN = re.compile(
    r"^(?P<addr>[0-9A-F]{8})\s+"
    r"(?P<bytes>(?:[0-9a-f]{2}|-)(?:\s+(?:[0-9a-f]{2}|-))*)\s+"
    r"(?P<mn>[a-z][a-z0-9]*)\s*(?P<ops>.*?)\s*$")

# `; OemOcDxe @ 00000F38   EcWriteCommandData   [named]` -- and, for an
# unnamed function, `; Setup @ 0001BA3C   FUN_0001ba3c`. The name is what puts
# a row next to the annotation CSV, so it is read rather than reconstructed.
HEADER = re.compile(r"^;\s+(?P<module>\S+)\s+@\s+(?P<addr>[0-9A-F]+)\s+(?P<name>\S+)")

# The four command bytes, and what each one does to an EC RAM address.
PORT_BASE = "0xa3"
PORT_INDEX = "0xa2"
PORT_READ = "0xa4"
PORT_WRITE = "0xa5"
PORTS = (PORT_BASE, PORT_INDEX, PORT_READ, PORT_WRITE)


class Listing(object):
    """One `.asm` file: a single function, and where it came from."""

    def __init__(self, path, module, addr, name, insns):
        self.path = path
        self.module = module
        self.addr = addr
        self.name = name
        self.insns = insns

    def hex_addr(self, index):
        return "0x" + self.insns[index]["addr"]

    def evidence(self):
        return os.path.relpath(self.path, REPO)


def parse_listing_text(path, text):
    """A `Listing` from its text, or `None` for something that is not one.

    The header is what makes a file a listing; a directory read picks up
    nothing else, and returning `None` rather than raising keeps the caller's
    walk a single comprehension. `path` is carried for `evidence()` only, so
    the fixture half can name the tree it invented.
    """
    lines = text.splitlines()
    head = HEADER.match(lines[0]) if lines else None
    if head is None:
        return None
    insns = []
    for line in lines:
        m = INSN.match(line)
        if m:
            insns.append({"addr": m.group("addr"), "mn": m.group("mn"),
                          "ops": m.group("ops").strip()})
    return Listing(path, head.group("module"), head.group("addr").upper(),
                   head.group("name"), insns)


def parse_listing(path):
    with open(path) as f:
        return parse_listing_text(path, f.read())


def read_listings(root):
    listings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith(".asm"):
                continue
            listing = parse_listing(os.path.join(dirpath, name))
            if listing is not None:
                listings.append(listing)
    return listings


# --------------------------------------------------------------------------
# Which register an operand names, and which instruction writes it
# --------------------------------------------------------------------------

# The 64-bit register a byte, dword or qword name is a view of. Width is
# irrelevant to the question being asked here -- whether the register holds
# the value a command sends -- and folding the widths together is what lets
# `mov R8B, DIL` and a `mov R8D, ...` in the same window be read as two
# statements about one thing. The `E`-prefixed dwords are listed because the
# 32-bit TE modules name their registers both ways (`xor EDI, EDI` against
# `mov DIL, R8B`), and a name the map does not hold reads as not a register.
_FAMILY = {}
for _full, _mid, _lo in (("RAX", "EAX", "AL"), ("RCX", "ECX", "CL"),
                         ("RDX", "EDX", "DL"), ("RBX", "EBX", "BL"),
                         ("RSI", "ESI", "SIL"), ("RDI", "EDI", "DIL"),
                         ("RBP", "EBP", "BPL"), ("RSP", "ESP", "SPL")):
    _FAMILY[_full] = _full
    _FAMILY[_mid] = _full
    _FAMILY[_mid + "W"] = _full
    _FAMILY[_lo] = _full
    _FAMILY[_lo.upper()] = _full
for _n in range(8, 16):
    for _w in ("", "D", "W", "B"):
        _FAMILY["R%d" % _n + _w] = "R%d" % _n


def reg_family(operand):
    """The 64-bit register `operand` names, or `None` if it is not one."""
    return _FAMILY.get(operand.strip().upper())


# The registers an x64 caller fills before a call. A value that traces to one
# of these with nothing in the window writing it is the caller's to decide,
# which is the `caller` form; one that traces to anything else is not, and
# naming it is the honest answer.
ARG_FAMILIES = frozenset(("RCX", "RDX", "R8", "R9"))


def byte(value):
    """A value byte as the table prints it: `0x07`, not `0x7`.

    Every byte in the CSV is two digits so that a base and an index read as
    the halves of one address and `--addr` can match on what the table says.
    A `mov R8B, 0x7` in the listing is not a different byte from a `0x07`.
    """
    return "0x%02x" % (int(value, 16) & 0xFF)


def operands(insn):
    return [p.strip() for p in insn["ops"].split(",")]


def first_call(insns):
    """The index of the function's first `call`, or its length if it has none.

    Everything before it is the entry block, and it is the only place a
    register's incoming value is still readable: past the first call the
    argument registers are whatever the callee left behind.
    """
    for j, insn in enumerate(insns):
        if insn["mn"] == "call":
            return j
    return len(insns)


def window(insns, index):
    """The span of instructions over which a register still holds its value.

    Bounded by the `call` on either side, because a call is where a register
    stops being this function's to read: the callee may write any of them.
    """
    lo = 0
    for j in range(index - 1, -1, -1):
        if insns[j]["mn"] == "call":
            lo = j + 1
            break
    hi = len(insns)
    for j in range(index, len(insns)):
        if insns[j]["mn"] == "call":
            hi = j
            break
    return lo, hi


# How far a byte is chased through register-to-register moves before the
# answer stops being about this function. Four covers the entry aliasing and
# the one or two local moves every form in the tree uses; a longer chain would
# be a dataflow problem this table does not claim to solve, and stopping early
# costs a resolved byte rather than a wrong one.
TRACE_DEPTH = 4

# A register written more than once between the same two calls is a byte this
# table cannot name: `Setup` `0x1A5C` sets `DL` to `0x10`, to `0xA0` or from a
# stack slot and passes whichever it reached, so reading the last `mov`
# backwards would report `0xA0` for all three.
def definitions(insns, lo, hi, family):
    """Every index in `[lo, hi)` at which an instruction writes `family`.

    The count is what decides, not the presence of a branch: the
    `test RAX, RAX` / `js` status guard between two calls is in nearly every
    window in this tree and writes nothing, so a rule keyed on branches would
    throw away almost every byte this table can read.
    """
    return [j for j in range(lo, hi) if writes(insns[j], family)]


def writes(insn, family):
    """Whether `insn` gives a register of `family` a new value.

    A `push` is not one. It saves the old value and the register goes on
    holding it, which is what makes the entry-block alias readable at all:
    `Setup` `0x1BA3C` opens with `push RDI` and closes with `pop RDI`, and
    counting the push would make `mov DIL, R8B` look like the second of two
    writes to `RDI` rather than the only one that gives it a value.
    """
    if insn["mn"] == "push":
        return False
    ops = operands(insn)
    return bool(ops) and reg_family(ops[0]) == family


def trace(insns, lo, hi, reg, depth=TRACE_DEPTH):
    """What `reg` holds at `hi`: `("imm", "0x07")`, `("caller", "R8")` or
    `("unresolved", "DL")`.

    Read inside the window first, where a single write is the value on every
    path that reaches the command. Failing that the entry block is searched,
    which is how `mov DIL, R8B` at a function's top makes a later
    `mov R8B, DIL` the caller's byte rather than an unreadable one.

    An unresolved answer names the register whose value is unknown -- the one
    the chase ended on, not the one it started from and not the memory
    operand it was read from, so the reader is pointed at the register to look
    at rather than at the instruction to re-read.
    """
    family = reg_family(reg)
    if family is None:
        return ("unresolved", reg)
    entry = first_call(insns)
    found = definitions(insns, lo, hi, family)
    if len(found) == 1:
        return definition(insns, found[0], family, depth)
    if len(found) > 1:
        # Several writes are only ambiguity if they disagree. `OemKbLightDxe`
        # `0x5A4` sets `R8B` to `0x66` on both arms of a branch and passes
        # `0x66`, while `Setup` `0x1A5C` sets `DL` to `0x10`, to `0xA0` or from
        # a stack slot and passes whichever it reached -- so the first is a
        # byte and the second is not one.
        answers = set(definition(insns, j, family, depth) for j in found)
        return answers.pop() if len(answers) == 1 else ("unresolved", reg)
    # Not written in the window. The entry block is what is left, and under
    # the x64 calling convention the caller's four argument registers hold
    # what the caller passed even with no alias at all.
    aliased = definitions(insns, 0, min(entry, lo), family)
    if len(aliased) == 1:
        return definition(insns, aliased[0], family, depth)
    if family in ARG_FAMILIES:
        return ("caller", reg)
    return ("unresolved", reg)


def definition(insns, j, family, depth):
    """How instruction `j` gives a register of `family` its value, or `None`.

    `("imm", "0x00")` for `xor R8D, R8D` and for a `mov` of a literal,
    `("caller", "R8")` for a `mov` from a register the chase follows, and
    `("unresolved", ...)` for anything this tool does not read -- a memory
    operand, a port, a `lea`, an arithmetic combination.
    """
    insn = insns[j]
    ops = operands(insn)
    if not ops or reg_family(ops[0]) != family:
        return None
    if insn["mn"] == "xor" and len(ops) == 2 and reg_family(ops[1]) == family:
        return ("imm", "0x00")
    if insn["mn"] != "mov" or len(ops) != 2:
        return ("unresolved", ops[0])
    src = ops[1]
    if re.match(r"^0x[0-9a-fA-F]+$", src):
        return ("imm", byte(src))
    if reg_family(src) is None:
        return ("unresolved", ops[0])
    if depth <= 0:
        return ("unresolved", ops[0])
    return trace(insns, 0, j, src, depth - 1)


def x64_value(listing, index):
    """The byte the command at `index` sends, read from R8B.

    The port byte and the value byte are set in either order across the tree
    (`mov DL, 0xa3` then `mov R8B, 0x7` in one, the reverse in another), so
    the whole window is searched rather than the instructions before it.
    """
    lo, hi = window(listing.insns, index)
    return trace(listing.insns, lo, hi, "R8B")


# The stack slots these TE modules read their own arguments from. Both of them
# -- `OemOcPei` `0xFFF827BE` and `OemHooksPei` `0xFFF818CC` -- push a value,
# `call`, and then `pop` it themselves, so the callee leaves the pushed byte
# on the stack and the `pop` is this function's own cleanup. That is what fixes
# the offsets: with the callee popping instead, the same `push [ESP + 0x8]`
# would name the *second* argument and neither module's call sites would
# supply one. They push two values each, which is what settles it -- so
# `[ESP + 0x8]` is the first argument and `[ESP + 0xc]` the second, and any
# other offset is not read.
STACK_ARGS = {"0x8": "arg1", "0xc": "arg2"}


def te_value(listing, index):
    """The byte the command at `index` sends, read from the stack (TE).

    The value is whatever the `call` this command feeds finds on top of the
    stack, so the pushes and pops between the surrounding calls are replayed
    and the top of the stack at that `call` is read. Replaying rather than
    taking the nearest `push` is what `OemOcPei` `0xFFF827F3` needs: it pushes
    `0x7`, pushes `0x62` and pops that straight back into `EBX`, so the byte
    the command carries is the one underneath.
    """
    lo, hi = window(listing.insns, index)
    stack = []
    for j in range(lo, hi):
        insn = listing.insns[j]
        if insn["mn"] == "push":
            stack.append(insn["ops"].strip())
        elif insn["mn"] == "pop" and stack:
            # A `pop` pairing a push the call already consumed, or an
            # unrelated spill; either way it takes the top off.
            stack.pop()
    if not stack:
        return ("unresolved", "stack")
    value = stack[-1]
    if re.match(r"^0x[0-9a-fA-F]+$", value):
        return ("imm", byte(value))
    m = re.match(r"^dword ptr \[ESP \+ (0x[0-9a-f]+)\]$", value)
    if m and m.group(1) in STACK_ARGS:
        return ("caller", "stack:" + STACK_ARGS[m.group(1)])
    return ("unresolved", value)


def is_te(listing):
    """Whether the module's calls carry their bytes on the stack.

    Decided from the module rather than from the listing: `OemOcPei` and
    `OemHooksPei` are the two TE modules, and a site in either is a stack
    site whatever its instructions happen to look like. Naming the two is a
    fact about this firmware, not a generalisation about TE.
    """
    return listing.module in ("OemOcPei", "OemHooksPei")


def site_value(listing, index):
    """The byte the command at `index` sends, read by whichever ABI fits."""
    return te_value(listing, index) if is_te(listing) else x64_value(listing, index)


# --------------------------------------------------------------------------
# The access sequence
# --------------------------------------------------------------------------

def port_sites(listing):
    """`(index, port)` for every command byte in the listing, in address order."""
    sites = []
    for i, insn in enumerate(listing.insns):
        if insn["mn"] != "mov":
            continue
        ops = operands(insn)
        if len(ops) == 2 and ops[0] == "DL" and ops[1] in PORTS:
            sites.append((i, ops[1]))
    return sites


def port_helper(listing, index):
    """The routine the command at `index` calls, as `module@0xADDR`."""
    _, hi = window(listing.insns, index)
    if hi < len(listing.insns) and listing.insns[hi]["mn"] == "call":
        target = listing.insns[hi]["ops"].strip()
        if target.startswith("0x"):
            return "%s@0x%s" % (listing.module, target[2:].rjust(8, "0").upper())
    return ""


def access_sequences(listing):
    """Each `0xA3`/`0xA2` run with the `0xA4` or `0xA5` that ends it.

    A site that no run claims is returned on its own, so that every command
    byte in the tree reaches the table and a change to a listing's shape shows
    up as a row rather than as a quiet omission.
    """
    sites = port_sites(listing)
    taken, sequences = set(), []
    for pos, (index, port) in enumerate(sites):
        if port != PORT_BASE or pos in taken:
            continue
        taken.add(pos)
        seq = {"base": (index, PORT_BASE), "index": None, "end": None}
        for nxt_pos, nxt in enumerate(sites[pos + 1:], pos + 1):
            if nxt[1] == PORT_BASE or nxt_pos in taken:
                break
            taken.add(nxt_pos)
            if nxt[1] == PORT_INDEX and seq["index"] is None:
                seq["index"] = nxt
            else:
                seq["end"] = nxt
                break
        sequences.append(seq)
    for pos, (index, port) in enumerate(sites):
        if pos not in taken:
            sequences.append({"base": None, "index": (index, port), "end": None})
    sequences.sort(key=lambda s: (s["base"] or s["index"])[0])
    return sequences


# --------------------------------------------------------------------------
# Resolving a `caller` byte at the call sites of the function
# --------------------------------------------------------------------------

def call_index(listings):
    """`{(module, addr): [(listing, pos)]}` over every committed listing.

    Every `call` to a named address, from any listing in the tree, holding the
    listing rather than its module because a module holds many functions and
    the caller's own instructions are what a byte has to be read out of. A
    helper reached through a pointer rather than a direct call is not in here,
    which is one of the bounds the `unresolved` rows carry.
    """
    index = defaultdict(list)
    for listing in listings:
        for pos, insn in enumerate(listing.insns):
            if insn["mn"] != "call":
                continue
            target = insn["ops"].strip()
            if target.startswith("0x"):
                index[(listing.module,
                       target[2:].rjust(8, "0").upper())].append((listing, pos))
    return index


def caller_value(listing, pos, want):
    """The byte a caller puts in `want` for the call at `pos`.

    `want` is what `trace()` reported: an argument register (`R8`, `DL`, ...)
    or `stack:arg1` / `stack:arg2`. Read over the call's own window, so a
    definition the caller made for an earlier call is not read as this one's.

    A stack argument is the pushes immediately before the `call`, counted back
    from the last one: `OemHooksPei` `0xFFF818CC`'s two callers each push two
    values and nothing else, and the value at the top is the first argument.
    """
    insns = listing.insns
    lo, _ = window(insns, pos)
    if not want.startswith("stack:"):
        return trace(insns, lo, pos, want)
    slot = 1 if want == "stack:arg1" else 2
    pushed = []
    for j in range(pos - 1, lo - 1, -1):
        if insns[j]["mn"] != "push":
            break
        pushed.append(j)
        if len(pushed) == slot:
            break
    if len(pushed) != slot:
        return ("unresolved", want)
    j = pushed[slot - 1]
    value = insns[j]["ops"].strip()
    if re.match(r"^0x[0-9a-fA-F]+$", value):
        return ("imm", byte(value))
    if reg_family(value) is not None:
        # A pushed register holds whatever the caller put in it, so it is
        # chased the same way an argument register would be.
        return trace(insns, lo, j, value)
    return ("unresolved", value)


# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------

def empty_row(listing, seq):
    site = seq["base"] or seq["index"]
    index = site[0]
    return {
        "module": listing.module,
        "func": listing.name,
        "func_addr": "0x" + listing.addr,
        "site_addr": listing.hex_addr(index),
        "port_helper": port_helper(listing, index),
        "abi": "te32" if is_te(listing) else "x64",
        "base": "",
        "index": "",
        "data": "",
        "direction": "",
        "caller": "",
        "resolved": "",
        "evidence": listing.evidence(),
    }


def rows(listings):
    """Every access in the tree, one row per resolved instance of it.

    A sequence whose bytes are immediates is one row. A sequence that takes an
    argument is one row per call site, because the address it reaches is the
    caller's to decide -- and one row naming the argument when no call site in
    the tree settles it.

    `resolved` says what could not be read and in which column, so that a row
    with an unresolved *data* byte is not read as a row with an unresolved
    *address*. The question this table answers is "does this pair appear", and
    that turns on `base` and `index` alone.
    """
    callers = call_index(listings)
    out = []
    for listing in sorted(listings, key=lambda l: (l.module, l.addr)):
        for seq in access_sequences(listing):
            fields = []
            if seq["base"]:
                fields.append(("base", seq["base"][0]))
            if seq["index"]:
                fields.append(("index", seq["index"][0]))
            if seq["end"] and seq["end"][1] == PORT_WRITE:
                fields.append(("data", seq["end"][0]))

            # What is known without leaving this function, and what a caller
            # has to supply. A field the caller supplies is left empty rather
            # than filled with the name of a register: the address an access
            # reaches is the caller's to decide, and a row that put `R8` in
            # the `index` column would read as though the table had settled it.
            known, pending, bad = {}, [], []
            for field, at in fields:
                kind, value = site_value(listing, at)
                if kind == "imm":
                    known[field] = value
                elif kind == "caller":
                    pending.append((field, value))
                else:
                    bad.append("no:" + field + ":" + value)

            def emit(misses, caller="", extra=None):
                # A fresh row each time rather than one merged into: a byte one
                # caller resolves and the next does not has to come back empty,
                # or the second row reads with the first caller's value in it.
                row = dict(known)
                row.update(extra or {})
                row["caller"] = caller
                row["resolved"] = (misses + bad)[0] if (misses or bad) else "yes"
                base = empty_row(listing, seq)
                base["direction"] = (
                    "read" if seq["end"] and seq["end"][1] == PORT_READ
                    else "write" if seq["end"] else "")
                base.update(row)
                out.append(clean(base))

            if not pending:
                emit([])
                continue

            # One row per call site: the same function reaches a different EC
            # address from each of them.
            sites = callers.get((listing.module, listing.addr), [])
            for caller_listing, pos in sites:
                values, misses = {}, []
                for field, want in pending:
                    kind, value = caller_value(caller_listing, pos, want)
                    if kind == "imm":
                        values[field] = value
                    else:
                        misses.append("no:" + field + ":" + value)
                emit(misses,
                     "%s@%s" % (caller_listing.module,
                                caller_listing.hex_addr(pos)), values)
            if not sites:
                # Nothing in the tree calls it, so nothing settles a byte it
                # takes as an argument. The row says so and leaves the column
                # empty, which is what bounds the negative: an address no
                # caller settles is not an address this table has looked for.
                # Where there are call sites each one already carries its own
                # `no:` for whatever it could not read, and a further row here
                # would be a second copy of that rather than a new fact.
                field = pending[0][0]
                emit(["no:%s:%s" % (field, pending[0][1])])
    return out


def clean(row):
    return {k: row[k] for k in CSV_COLUMNS}


# --------------------------------------------------------------------------
# The committed CSV
# --------------------------------------------------------------------------

def render_csv(table):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in table:
        writer.writerow(row)
    return buf.getvalue()


def derive(args):
    return render_csv(rows(read_listings(args.listings)))


def write(args):
    text = derive(args)
    path = os.path.abspath(args.csv)
    with open(path, "w", newline="") as f:
        f.write(text)
    print("wrote %s: %d row(s)"
          % (os.path.relpath(path, REPO), len(text.splitlines()) - 1))
    return 0


def check(args):
    """The `--check` half: the committed CSV is what this tool derives.

    A missing file is a failure rather than a "would create", because the file
    is derived from committed listings and its absence is a hole in the tree,
    not a state a verification run should repair.
    """
    path = os.path.abspath(args.csv)
    if not os.path.isfile(path):
        print("error: no %s. It is derived from %s; run --write."
              % (os.path.relpath(path, REPO),
                 os.path.relpath(args.listings, REPO)))
        return 1
    text = derive(args)
    with open(path, newline="") as f:
        on_disk = f.read()
    if on_disk == text:
        print("%s: %d row(s), unchanged"
              % (os.path.relpath(path, REPO), len(text.splitlines()) - 1))
        return 0
    want, have = text.splitlines(), on_disk.splitlines()
    print("error: %s is not what %s derives."
          % (os.path.relpath(path, REPO), os.path.relpath(args.listings, REPO)))
    for n, (a, b) in enumerate(zip(have, want)):
        if a != b:
            print("  line %d\n    committed: %s\n    derived:   %s"
                  % (n + 1, a, b))
            break
    if len(have) != len(want):
        print("  %d committed line(s), %d derived" % (len(have), len(want)))
    print("  If the derivation is the one that should stand, run --write.")
    return 1


# --------------------------------------------------------------------------
# Reading the census
# --------------------------------------------------------------------------

def load(args):
    if not os.path.isdir(args.listings):
        raise SystemExit("error: no %s. The census reads the committed listings."
                         % os.path.relpath(os.path.abspath(args.listings), REPO))
    return rows(read_listings(args.listings))


def print_census(table):
    for row in table:
        print("%-20s %-34s %-10s %-11s base=%-5s index=%-5s data=%-5s %-5s "
              "%-22s %s"
              % (row["module"], row["func"], row["site_addr"],
                 row["port_helper"], row["base"] or "-", row["index"] or "-",
                 row["data"] or "-", row["direction"], row["caller"] or "-",
                 row["resolved"]))
    print("\n%d access(es); %d with a byte this tool could not read"
          % (len(table), sum(1 for r in table if r["resolved"] != "yes")))
    return 0


def print_addr(table, spec):
    # `0x07A6`, `0x7A6`, `7A6` and `0x07:A6` all name the same pair; the two
    # halves mean nothing apart, so the separated form is the one that says so.
    m = re.match(r"^(?:0x)?([0-9a-fA-F]{1,2}):([0-9a-fA-F]{1,2})$", spec)
    if m:
        base, index = byte(m.group(1)), byte(m.group(2))
    else:
        m = re.match(r"^(?:0x)?([0-9a-fA-F]{3,4})$", spec)
        if not m:
            raise SystemExit("error: --addr wants an EC RAM address, e.g. "
                             "0x07A6 or 0x07:A6")
        pair = m.group(1).rjust(4, "0").lower()
        base, index = byte(pair[:2]), byte(pair[2:])
    print_census([r for r in table
                  if r["base"] == base and r["index"] == index])
    return 0


def print_unresolved(table):
    table = [r for r in table if r["resolved"] != "yes"]
    if not table:
        print("every access resolved")
        return 0
    print_census(table)
    return 0


# --------------------------------------------------------------------------
# Known answers, on hand-built listings
# --------------------------------------------------------------------------

# Stated as (module, address, name, body) rather than as finished files, so
# the header a listing is parsed by cannot drift from the values a case
# asserts on -- the first version of this fixture got that wrong twice, with
# a module named in one place and spelled another in the assertion.
FIXTURE = [
    ("Fix", "00000000", "imm_write", """
00000000 b2 a3                    mov      DL, 0xa3
00000002 41 b0 07                 mov      R8B, 0x7
00000005 b1 62                    mov      CL, 0x62
00000007 e8 00 00 00 00           call     0x000000f0
0000000C 41 b0 a6                 mov      R8B, 0xa6
0000000F b2 a2                    mov      DL, 0xa2
00000011 b1 62                    mov      CL, 0x62
00000013 e8 00 00 00 00           call     0x000000f0
00000018 41 b0 5a                 mov      R8B, 0x5a
0000001B b2 a5                    mov      DL, 0xa5
0000001D b1 62                    mov      CL, 0x62
0000001F e8 00 00 00 00           call     0x000000f0
00000024 c3                       ret
"""),
    ("Fix", "00000030", "reg_write", """
00000030 41 8a f8                 mov      DIL, R8B
00000033 b2 a3                    mov      DL, 0xa3
00000035 41 b0 07                 mov      R8B, 0x7
00000038 b1 62                    mov      CL, 0x62
0000003A e8 00 00 00 00           call     0x000000f0
0000003F 44 8a c7                 mov      R8B, DIL
00000042 b2 a2                    mov      DL, 0xa2
00000044 b1 62                    mov      CL, 0x62
00000046 e8 00 00 00 00           call     0x000000f0
0000004B c3                       ret
"""),
    ("Fix", "00000060", "caller_set", """
00000060 41 b0 41                 mov      R8B, 0x41
00000063 e8 c8 ff ff ff           call     0x00000030
00000068 41 b0 77                 mov      R8B, 0x77
0000006B e8 c0 ff ff ff           call     0x00000030
00000070 c3                       ret
"""),
    ("Fix", "000000A0", "unresolved_write", """
000000A0 b2 a3                    mov      DL, 0xa3
000000A2 41 b0 07                 mov      R8B, 0x7
000000A5 b1 62                    mov      CL, 0x62
000000A7 e8 00 00 00 00           call     0x000000f0
000000AC 44 8a c3                 mov      R8B, BL
000000AF b2 a2                    mov      DL, 0xa2
000000B1 b1 62                    mov      CL, 0x62
000000B3 e8 00 00 00 00           call     0x000000f0
000000B8 c3                       ret
"""),
    ("Fix", "000000D0", "mem_operand", """
000000D0 66 85 83 a6 00 00 00     test     word ptr [RBX + 0xa6], AX
000000D7 c3                       ret
"""),
    ("OemOcPei", "FFF82700", "te_write", """
FFF82700 6a 07                    push     0x7
FFF82702 b2 a3                    mov      DL, 0xa3
FFF82704 b1 62                    mov      CL, 0x62
FFF82706 e8 f5 08 00 00           call     0xfff83000
FFF8270B 59                       pop      ECX
FFF8270C 6a a6                    push     0xa6
FFF8270E b2 a2                    mov      DL, 0xa2
FFF82710 b1 62                    mov      CL, 0x62
FFF82712 e8 e9 08 00 00           call     0xfff83000
FFF82717 59                       pop      ECX
FFF82718 c3                       ret
"""),
]


def fixture_listings():
    """The fixture as `Listing`s, each with the header its parser needs."""
    listings = []
    for module, addr, name, body in FIXTURE:
        text = "; %s @ %s   %s   [named]\n%s" % (module, addr, name, body)
        listings.append(parse_listing_text(
            os.path.join("fixture", module, addr + ".asm"), text))
    return listings


def self_test():
    problems = []

    def want(ok, message):
        if not ok:
            problems.append(message)

    listings = fixture_listings()
    want(all(listings), "every fixture entry should parse as a listing")
    table = rows([l for l in listings if l is not None])
    named = defaultdict(list)
    for row in table:
        named[row["func"]].append(row)

    # The immediate form: base, index and data all read where they are set,
    # with the value byte's instruction before or after the port byte's --
    # the two orders the tree uses, and only one of them is the usual one.
    imm = named["imm_write"]
    want(len(imm) == 1, "the immediate fixture should be one row, got %d"
         % len(imm))
    if imm:
        row = imm[0]
        want((row["base"], row["index"], row["data"]) ==
             ("0x07", "0xa6", "0x5a"),
             "the immediate fixture resolved to %r"
             % ((row["base"], row["index"], row["data"]),))
        want(row["direction"] == "write",
             "a 0xA5-terminated run is a write, got %r" % row["direction"])
        want(row["resolved"] == "yes" and row["caller"] == "",
             "the immediate fixture needs no caller, got %r/%r"
             % (row["resolved"], row["caller"]))
        want(row["abi"] == "x64", "imm_write is x64, got %r" % row["abi"])
        want(row["port_helper"] == "Fix@0x000000F0",
             "the helper is named from the call, got %r" % row["port_helper"])

    # The register-passed form: the index is the function's first argument, so
    # the address the run reaches is the caller's to decide, and one row is
    # emitted per call site rather than one for the helper.
    reg = sorted(named["reg_write"], key=lambda r: r["caller"])
    want(len(reg) == 2,
         "the register-passed fixture should resolve at both of its two call "
         "sites, got %d" % len(reg))
    want([r["caller"] for r in reg] == ["Fix@0x00000063", "Fix@0x0000006B"],
         "the register-passed rows should name both callers, got %r"
         % ([r["caller"] for r in reg],))
    want([(r["base"], r["index"]) for r in reg]
         == [("0x07", "0x41"), ("0x07", "0x77")],
         "each caller's own immediate should reach its own row, got %r"
         % ([(r["base"], r["index"]) for r in reg],))
    want(all(r["resolved"] == "yes" for r in reg),
         "a caller that loads an immediate resolves every byte, got %r"
         % ([r["resolved"] for r in reg],))
    if reg:
        want(reg[0]["direction"] == "",
             "a run with no 0xA4 or 0xA5 has no direction, got %r"
             % reg[0]["direction"])

    # A register the window does not define is named, not guessed into an
    # address, and the column it would have filled is left empty.
    unres = named["unresolved_write"]
    want(len(unres) == 1, "the unresolvable fixture should be one row, got %d"
         % len(unres))
    if unres:
        want(unres[0]["resolved"] == "no:index:BL",
             "an undefined register is reported by name and by column, got %r"
             % unres[0]["resolved"])
        want(unres[0]["index"] == "",
             "an unresolved byte is not filled in, got %r" % unres[0]["index"])
        want(unres[0]["base"] == "0x07",
             "the resolved half of the same run still reads, got %r"
             % unres[0]["base"])

    # A 0xA6 that is a memory operand is not an index byte: this is the shape
    # a scan for the byte would have found and had to decline.
    want(not named["mem_operand"],
         "a memory operand carrying 0xa6 was read as a command byte")
    mem = [l for l in listings if l and l.name == "mem_operand"][0]
    want(port_sites(mem) == [],
         "port_sites() found a command byte in a memory operand")

    # The 32-bit TE form: the bytes are pushed, and each is read forward to the
    # call it feeds rather than taken from wherever it was written.
    te = named["te_write"]
    want(len(te) == 1, "the TE fixture should be one row, got %d" % len(te))
    if te:
        want((te[0]["base"], te[0]["index"]) == ("0x07", "0xa6"),
             "the TE fixture resolved to %r"
             % ((te[0]["base"], te[0]["index"]),))
        want(te[0]["abi"] == "te32", "te_write is te32, got %r" % te[0]["abi"])
    want(named["caller_set"] == [],
         "a listing with no command byte of its own produces no row")

    # Every command byte in the fixture tree is claimed by exactly one run, so
    # a shape this tool does not understand shows up as a row rather than as a
    # silent omission.
    sites = sum(len(port_sites(l)) for l in listings if l)
    claimed = sum(1 + (1 if s["index"] else 0) + (1 if s["end"] else 0)
                  for l in listings if l for s in access_sequences(l))
    want(sites == claimed,
         "%d command byte(s) in the fixture, %d claimed by a run"
         % (sites, claimed))

    for problem in problems:
        print("  FAIL %s" % problem)
    if problems:
        return 1
    print("  self-test: %d access(es) from the fixture, all as expected"
          % len(table))
    return 0


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listings", default=DEFAULT_LISTINGS,
                    help="the listing tree to read (default bios/ghidra/listings)")
    ap.add_argument("--csv", default=DEFAULT_CSV,
                    help="the derived census (default "
                         "bios/annotations/ec-io-writes.csv)")
    ap.add_argument("--addr", metavar="BASE:INDEX",
                    help="print only the accesses for one EC RAM address, "
                         "e.g. 0x07A6 or 0x07:A6")
    ap.add_argument("--module", metavar="MODULE",
                    help="print only one module's accesses")
    ap.add_argument("--unresolved", action="store_true",
                    help="print only the accesses this tool could not resolve")
    ap.add_argument("--write", action="store_true",
                    help="regenerate the committed CSV from the listings")
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed CSV is not what this tool "
                         "derives; needs neither the ROM nor Ghidra")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against hand-built listings")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    # --write first of the two modes that touch the committed CSV: it is the
    # one that writes it, and it is refused alongside --check for the same
    # reason ifr_census.py refuses it there -- a run that both re-blessed the
    # file and compared against it would exit green on anything.
    if args.check and args.write:
        raise SystemExit("error: --write regenerates %s from the current "
                         "listings; it cannot be combined with --check, which "
                         "compares against it."
                         % os.path.relpath(DEFAULT_CSV, REPO))
    if args.check:
        return check(args)
    if args.write:
        return write(args)
    table = load(args)
    if args.addr:
        return print_addr(table, args.addr)
    if args.module:
        shown = [0]
        print_census([r for r in table if r["module"] == args.module])
        return 0
    if args.unresolved:
        return print_unresolved(table)
    return print_census(table)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)