#!/usr/bin/env python3
"""The DPL/DPH form census, per form and on the committed windows.

Issue #1027 counted one direction of the 8051's `direct` operand -- `mov
0x82,<src>`, which writes DPTR's low byte -- and warned about the other, `mov
<dst>,0x82`, which only reads it. The read forms had never been counted
anywhere in the tree, so the sweep the issue proposes would have had to invent
its own answer to the question it was careful to ask.
`../../docs/findings/dptr-guard-census-vs-1027.md` is the write-up and the
counts; this is the part of it that has to stay true.

Five things are held here, and the last is the one a re-cut can break:

- **Per form, from bytes.** Every opcode in each of the three buckets, driven
  through `form_at()` as a bare `bytes` fixture, asserted on the bucket *and*
  on the byte the instruction actually touches. The 8051's one form that names
  its operands in the other order, `mov direct,direct` (`0x85`), is a case of
  its own twice over: the byte this census keys on for the **store** is its
  second operand there, so a classifier reading `d[i+1]` would find none of
  the 35 store references this image has; and its **source** is a read the same
  instruction makes, which a form that can return one reference drops on the
  floor. The operand index is delegated to
  `walk_budget_census.dptr_store_byte()`, and the case here is what stops this
  file growing a second opinion about it.
- **That those three tables are the whole map, checked against a second
  list.** The 256-opcode cross-check below holds the *store* table to
  `is_dptr_rebuild()`, which is a store list: the two omitted `0x86`/`0x87`
  together and so agreed on exactly the rows that were wrong, and a missing
  *read* form was invisible to it twice over because it never looked at the
  read table at all. The oracle here is `DIRECT_BEARING`, the 8051/8052 map
  of byte-addressed `direct` operands written out below from the instruction
  set, which shares no source with any of the three tables or with the
  guard, and is what makes the union a claim rather than a tautology. It is
  held by a case with a **negative control** beside it, because a
  completeness check that has only ever accepted one union is
  indistinguishable from one that cannot fail.
- **That second map against the committed Ghidra listings**, in
  `ListingCrossCheckTests`. Two transcriptions of the instruction set can
  still be wrong in the same place, and were: the map above once carried
  `0x26`/`0x27`/`0x36`/`0x96`/`0x97`, which the listings decode `add A, @R0`
  and `subb A, @R1` -- one byte, register-indirect, naming no address. So
  the listings are opened rather than quoted, and the check reads each
  instruction's length out of their byte columns: a byte-addressed `direct`
  operand is a second byte, so a one-byte decode refutes the row. That is
  the whole of what a length decides and it is what this class asserts;
  `0x24` against `0x25` is not something a length separates, and stays the
  operand-position claim the prose states.
- **The discriminator, both ways.** A window that contains a real `mov 0x82,a`
  and a window that contains `ljmp 0x83d6` where that store stood are the same
  bytes to a substring search over a rendered `window` cell and not the same
  instruction. The second is `ec-07c4-07d5-sites.csv` `0x0AD99`, committed and
  real, and it is a *third* false positive for the counting trap the issue
  describes: the `0x83` in that cell is a jump **target address**. Both
  fixtures are asserted, the verdicts are asserted to differ, and the case
  asserts that the substring search really does find `0x83` there -- so the
  thing the byte keying is protecting against is shown to exist rather than
  assumed.
- **The rule over the committed data**, in place of the issue's list of 27
  addresses: **no row of the six tables holds a DPL/DPH store inside its
  `window` at all**, and in particular none of the budget-truncated ones. The
  stronger form is not a decision -- `walk_why()` runs its reload guard on the
  instruction *after* the one it has just decoded, so a window stops *at* a
  store without decoding one, and the corollary follows. That is the
  invariant the widened guard established, it holds by shape, and a re-cut
  that broke it goes red here without anyone editing an address list: the
  case was checked against the pre-#517 guard, which is the one the issue's
  census was taken under, and it fails there on the first row. The rule's own
  trigger is asserted non-zero, so a re-cut that emptied the budget rows
  cannot pass it vacuously -- and nothing here asserts how many rows there
  are, how many tables, or what any of them total: a figure every re-cut has
  to edit is the shape `CLAUDE.md` warns against, and
  `../../docs/findings/dptr-rebuild-walk-guard.md` §8 records this repository
  making that mistake once already.

**No hardware, no Windows, no capture.** The per-form half reads nothing but
its own fixtures; the rule half reads the committed firmware and the six
committed CSVs, which is a stronger gate than a fixture asserting a count.
"""
import collections
import csv
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
ANNOT = HERE.parent / "annotations"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
# dptr_rebuild_forms imports trace_xdata_refs and walk_budget_census by bare
# module name, the way register_ref_table.py does, so the tool directory has
# to be on the path before any of them is loaded rather than after.
sys.path.insert(0, str(HERE))
import dptr_rebuild_forms as F        # noqa: E402
import trace_xdata_refs as T          # noqa: E402
import walk_budget_census as W        # noqa: E402

# walk()'s own budget, named rather than relied on, so a case that says "the
# budget" says which budget and a change to the signature moves this file's
# cases with it rather than silently past them.
BUDGET = W.BUDGET

# The six tables `walk-window-terminators.md` re-cut under the `terminator`
# column, and therefore the six that carry one. Listed here rather than taken
# from a glob so a reader can see what a seventh table would have to be added
# to; `test_walk_budget_census.py` holds the other direction, that these six
# are exactly the tables with that column.
SIX = ("ec-07c4-07d5-sites.csv", "ec-07d6-07d7-sites.csv",
       "ec-0x07d0-sites.csv", "ec-0x07d1-sites.csv",
       "manual-fan-ctrl-0751-sites.csv", "xdata-0400-045f-sites.csv")

# What a site's window starts with, and the one instruction of the 0x0AD99
# window that this file reuses as a stand-in for the `movx` at its head.
SITE = bytes([0x90, 0x07, 0xD0])      # mov dptr,#0x07D0 -- what a site is
WRITE = bytes([0xF0])                 # movx @dptr,a

# The six store forms, as bytes, in the spellings the 8051 has rather than the
# ones `disasm8051.mnemonic()` would render.
DPL_FROM_A = bytes([0xF5, 0x82])      # mov 0x82,a
DPH_FROM_A = bytes([0xF5, 0x83])      # mov 0x83,a
DPL_FROM_R7 = bytes([0x8F, 0x82])     # mov 0x82,r7
DPTRH_FROM_R4 = bytes([0x8C, 0x83])   # mov 0x83,r4
DPH_IMM = bytes([0x75, 0x83, 0x03])   # mov 0x83,#0x03
DPTRH_POPPED = bytes([0xD0, 0x83])    # pop 0x83
DPH_FROM_P1 = bytes([0x85, 0x90, 0x83])  # mov 0x83,0x90 -- dst is d[i+2]

# The two `mov direct,@Ri` forms. `direct` is the **destination** in both, so
# they are stores, and they are the two a table held to `is_dptr_rebuild()`
# silently left out.
DPL_FROM_R0_PTR = bytes([0x86, 0x82])   # mov 0x82,@r0
DPL_FROM_R1_PTR = bytes([0x87, 0x82])   # mov 0x82,@r1

# The reads, which rebuild nothing and must never be swept in with the stores.
READ_DPL = bytes([0xE5, 0x82])        # mov a,0x82
READ_DPH_INTO_R5 = bytes([0xAD, 0x82])  # mov r5,0x82
PUSH_DPL = bytes([0xC0, 0x82])        # push 0x82
# The two `mov @Ri,direct` forms: `direct` is the **source**, so they are
# reads. The other two half of the four the store and read tables both
# omitted, and the reason a completeness claim could not be true of them.
READ_DPL_VIA_R0 = bytes([0xA6, 0x82])   # mov @r0,0x82
READ_DPL_VIA_R1 = bytes([0xA7, 0x82])   # mov @r1,0x82
# `0x85`'s source, which is a read the same instruction that stores its
# destination makes. `85 83 f0` is `mov B,DPH` in the committed Ghidra
# listings; these two are `mov 0x0e,DPL` and `mov DPL,DPL`.
READ_DPH_FROM_85 = bytes([0x85, 0x83, 0xF0])  # mov B,DPH   -- reads DPH
READ_DPL_FROM_85 = bytes([0x85, 0x82, 0x0E])  # mov 0x0e,DPL -- reads DPL
# ...and the case the review asked for and the two above do not reach: both
# halves naming a DPTR byte. There is no such instruction in this image, so
# nothing counts it -- the case is here because `form_at()` has to be able to
# say so, and a fixture is the only place that is checkable.
BOTH_HALVES_85 = bytes([0x85, 0x82, 0x82])    # mov DPL,DPL
# The arithmetic group, which names DPL/DPH in the same `direct` position and
# which the earlier tables carried only one member of (`0x45`, `0x64`).
ADD_DPL_TO_A = bytes([0x25, 0x82])       # add a,0x82    -- read
DEC_DPL = bytes([0x15, 0x82])            # dec 0x82      -- in place
ADD_DPH_CARRY = bytes([0x35, 0x83])      # addc a,0x83   -- read
CLR_DPH = bytes([0xC2, 0x83])            # clr 0x83      -- in place

# The logical group's two halves, which the committed Ghidra listings decode
# as `45 82 orl A, DPL` and `42 f0 orl B, A` respectively. The accumulator is
# the destination in the first and the byte at `0x82` is in the second, which
# is the whole reason one is a read and the other an in-place modify. Both
# spellings name `0x82` in the same position, so nothing about the byte
# separates them -- the operand order does.
ORL_A_FROM_DPL = bytes([0x45, 0x82])     # orl a,0x82 -- read
ORL_DPL_FROM_A = bytes([0x42, 0x82])     # orl 0x82,a -- in place
# The three-byte `direct,#data` form of the 8052 addition, and -- the
# contrast the case below turns on -- the base-8051 accumulator form of the
# same group, which names a *literal* rather than a byte address. The census
# must decline the second, which is what keeps the immediate spellings out
# of all three tables.
ANL_DIRECT_DPL = bytes([0x53, 0x82, 0x7F])   # anl 0x82,#0x7f -- byte address
ORL_A_LITERAL = bytes([0x54, 0x82, 0x7F])     # anl a,#0x82  -- an immediate
# `0x54` is two bytes, so the trailing `0x7F` is the *next* instruction's byte
# and is not part of this one; the immediate this decodes is `0x82`.

# In place: a direct operand naming DPL/DPH that changes it without replacing
# it, with the byte after the operand laid down as well. The two spellings
# differ only after the operand, and this census keys on the operand byte
# rather than on a decode, so it never looks at the length.
XCH_DPL = bytes([0xC5, 0x82])         # xch a,0x82
INC_DPL = bytes([0x05, 0x82])         # inc 0x82
# `0x53` is three bytes -- `anl direct,#data` -- so the trailing `0x7F` here
# is the *next* instruction's byte and not part of this one. It is the
# three-byte case rather than a two-byte one because a two-byte form's
# following byte is indistinguishable from an operand of a different
# instruction to a length-driven walk, and the point of the case below is
# that this census is not length-driven.
ANL_DPL_THEN_NEXT = bytes([0x53, 0x82, 0x7F])   # anl 0x82,#0x7f and what follows

# `ec-07c4-07d5-sites.csv` 0x0AD99, verbatim: the committed window cell reads
# `movx @dptr,a ; mov r7,#0xe1 ; ljmp 0x83d6`, and the `0x83` in it is a jump
# **target address** rather than an operand. A sweep that searched the rendered
# cell for `0x83` would count this row as a DPTR store.
LJMP_TARGET = bytes([0x02, 0x83, 0xD6])
# And the store that stood at the same place, which is the other half of the
# pair: `0x2C305` after `0x0AD99`'s shape is `mov 0x82,a`.
DPL_STORE_AT_TARGET = bytes([0xF5, 0x82])

# The map of opcodes whose operand is a **byte** address, written out here
# from the instruction set and deliberately derived from neither the census's
# tables nor `trace_xdata_refs.is_dptr_rebuild()`. It is the oracle for the
# claim the module docstring makes -- that the three tables are the whole map
# -- and it exists because the 256-opcode cross-check could not be that
# oracle: it held the store table to `is_dptr_rebuild()`, and the two omitted
# the same four opcodes, so they agreed on exactly the rows that were wrong.
# Two lists that share a source are one list counted twice.
#
# **`disasm8051.mnemonic()` is not the authority for writing it.** That
# renderer gets the accumulator rows right -- `54 82` prints as
# `anl a,#0x82` and `OPCODE_LEN[0x54] == 2` is correct -- but it renders
# `42 f0` as `db 0x42` and `63 65 ff` as `db 0x63` where the machine writes
# a byte address, so a list read off it carries the renderer's errors rather
# than the instruction set's. The authority is the committed Ghidra listings
# under `ec/decompiled/*/*.asm`, which decode the operand position: they
# render `45 82` as `orl A, DPL`, `42 f0` as `orl B, A`, `63 65 ff` as
# `xrl 0x65, #0xff` and `54 07` as `anl A, #0x7`. Two consequences are
# visible in the list below, and neither is a matter of taste: the
# accumulator forms `0x45`/`0x55`/`0x65` are
# **here** (they load the byte) while the immediate forms `0x44`/`0x54`/
# `0x64` are **not**, because their operand is a literal rather than an
# address; and the six 8052 additions -- the logical group's `direct,A`/
# `direct,#data` rows, which the listings decode and which are the *only*
# 8052 additions naming a byte address -- are here, so a base-MCS-51 list
# would be six short of the map.
#
# **`0x26`, `0x27`, `0x36`, `0x96` and `0x97` are deliberately *not* here,
# and that is the row this list was corrected on.** A transcription read off
# the opcode neighbourhood rather than off the operand puts them in beside
# `0x25`/`0x35`/`0x95`, on the reasoning that the base 8051's `SUBB` group is
# `0x94`/`0x95` alone so `0x96`/`0x97` must be 8052 additions. The committed
# listings say otherwise: `0x26` decodes `26 - - add A, @R0`, `0x27` decodes
# `27 - - add A, @R1`, `0x36` decodes `36 - - addc A, @R0`, `0x96` decodes
# `96 - - subb A, @R0` and `0x97` decodes `97 - - subb A, @R1` -- one byte
# each, register-indirect, naming no address at all. They are the base 8051's
# own `@Ri` forms, so there is no `direct`-operand spelling of them to be
# corroborated anywhere, and `disasm8051.OPCODE_LEN` -- which was called
# defective for agreeing -- agrees with all five.
#
# The bit-addressed forms are deliberately *not* here: `0x82` is the low byte
# of SFR `0x88` in a bit address and is not DPL, and `BIT_ADDRESSED` below
# names them so the exclusion is asserted rather than assumed.
DIRECT_BEARING = frozenset(
    (0x05, 0x15,                                    # inc / dec direct
     0x25, 0x35,                                    # add a,direct / addc a,direct
     0x42, 0x43, 0x45,                              # orl direct,A / ,#data / a,direct
     0x52, 0x53, 0x55,                              # anl, the same three
     0x62, 0x63, 0x65,                              # xrl, the same three
     0x75, 0x85, 0x86, 0x87,                        # mov direct, <src>
     0x95,                                          # subb a,direct
     0xA6, 0xA7,                                    # mov @Ri,direct
     0xB5,                                          # cjne a,direct,rel
     0xC0, 0xC2, 0xC5,                              # push / clr / xch
     0xD0, 0xD5,                                    # pop / djnz
     0xE5, 0xF5)                                    # mov a,direct / mov direct,a
) | frozenset(range(0x88, 0x90)) | frozenset(range(0xA8, 0xB0))

# The one class `DIRECT_BEARING` leaves out, held so the exclusion is a claim.
# Every one of these takes a *bit* address, and `0x82` in that position is
# the low byte of SFR `0x88` rather than DPL -- so counting them would be
# counting a different address under the same two characters. The `jb`/`jnb`/
# `jbc` rows and the `sjmp` displacement are on their own excluded class
# rather than this one, which is why they are not listed.
BIT_ADDRESSED = frozenset(
    (0x0A, 0x2A,                                    # orl
     0x4A, 0x5A,                                    # anl
     0x6A, 0x72, 0x7A,                              # xrl / orl c,bit
     0x82,                                          # anl c,bit
     0x92, 0xA0, 0xA2,                              # mov bit,C / mov C,bit
     0xB0,                                          # anl c,/bit
     0xB2, 0xC1, 0xD2))                             # cpl / clr / setb bit

# The two forms the census counts and `is_dptr_rebuild()` does not. `mov
# direct,@Ri` replaces DPTR's byte by exactly the argument the rest of the
# store table replaces it by, so leaving them out of the guard is a gap rather
# than a decision -- and the census is not allowed to inherit it silently,
# which is what naming them here is for. `dptr-rebuild-walk-guard.md` §3
# records it against the guard and `dptr-guard-census-vs-1027.md` §3 counts
# it; this file only holds the delta from being anything else.
GUARD_GAP_OPS = frozenset((0x86, 0x87))

# The committed Ghidra listings, which are the authority `DIRECT_BEARING` is
# checked against. Read from disk rather than transcribed: the whole point of
# the check is that the oracle shares no source with the thing it is checking,
# and a handful of decoded lines quoted in a comment is not an oracle.
LISTINGS = HERE.parent / "decompiled"

# **The check is on instruction length, and that is stated rather than
# smuggled.** Every byte-addressed `direct` form is two bytes, or three where
# the form carries a second operand byte as well -- the `direct,#data` rows,
# `mov direct,direct`, and the two relative forms. A form carrying no address
# is one byte or is not this map at all. Length is the property checked
# because it is the one the listings state unambiguously: operand *kind* is
# not decidable from their text, since Ghidra renders the accumulator and
# direct address `0xE0` both as `A`, so `add A, @R0` and `xrl A, B` are
# spelled alike and only their length separates them.
#
# What this decides is the class the five corrected rows came from, and it
# decides it soundly: a one-byte instruction cannot carry a byte-addressed
# operand, so any opcode in this map that the listings decode at one byte is
# wrong by construction. What it does **not** decide is `0x24` against `0x25`
# -- both `add` two-byte forms, one immediate and one direct -- which stays
# the operand-position claim the prose above states rather than something a
# length can separate.
DIRECT_LENGTH = {op: 2 for op in DIRECT_BEARING} | {
    0x43: 3, 0x53: 3, 0x63: 3,   # the logical group's direct,#data rows
    0x75: 3,                      # mov direct,#data
    0x85: 3,                      # mov direct,direct
    0xB5: 3,                      # cjne a,direct,rel
    0xD5: 3,                      # djnz direct,rel
}

# The five rows the committed listings refute, named rather than written only
# inside the prose above: the base 8051's register-indirect forms, which sit
# in the opcode neighbourhood of the `direct` arithmetic rows and share none
# of their shape. They are held here so the negative control below can drive
# the real mistake instead of an invented one.
REFUTED_REGISTER_INDIRECT = frozenset((0x26, 0x27, 0x36, 0x96, 0x97))


def listing_instruction_lengths() -> dict:
    """`{opcode: {length, ...}}` -- every committed listing instruction.

    A listing line is `ADDR  BB BB|- BB|-  MNEMONIC  operands`, so the three
    byte columns are positional and a `-` marks a byte the instruction does
    not have. Counting the non-`-` columns gives the instruction's length
    without decoding anything, which is what keeps this an oracle rather than
    a second opinion: it reads the listings' own bytes and nothing else.

    A line that does not parse is collected and returned beside the map rather
    than skipped, so a listing format that drifts fails the check instead of
    quietly shrinking the population it is drawn from.
    """
    lengths = collections.defaultdict(set)
    unparsed = []
    for path in sorted(LISTINGS.glob("*/*.asm")):
        for line in path.read_text(encoding="utf-8",
                                   errors="replace").splitlines():
            f = line.split()
            if not f or f[0].startswith(";") or not re.fullmatch(r"[0-9A-F]+",
                                                                  f[0]):
                continue
            cols = f[1:4]
            if len(f) < 5 or not all(
                    c == "-" or re.fullmatch(r"[0-9a-f]{2}", c) for c in cols):
                unparsed.append(f"{path.name}: {line}")
                continue
            lengths[int(cols[0], 16)].add(sum(1 for c in cols if c != "-"))
    return dict(lengths), unparsed


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_dptr_rebuild_guard.py`, `test_trace_xdata_refs.py`
    and `test_walk_budget_census.py` each carry a copy of, and for the same
    reason: a case that pointed at the firmware would keep testing the same
    bytes only until the bytes around some address in the image changed.
    """
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def form_at(img, insn):
    """`form_at()` on a bare `bytes` instruction, which is what a case
    actually has. An IndexError here would be a case that failed for the
    wrong reason."""
    return F.form_at(img, 0)


def one(insn, byte):
    """The single reference `insn` is expected to make, in the list form.

    Most forms make exactly one, and a case that wants one should say so
    rather than writing the list out: a two-element result where the case
    expected one is the failure this is here to make legible.
    """
    got = form_at(insn, 0)
    assert len(got) == 1, "%s made %d references: %r" % (
        insn.hex(" "), len(got), got)
    return got[0]


def window_forms(d, start, max_insns=BUDGET):
    """(every DPL/DPH reference inside `walk_why()`'s window, the token).

    Every decoded instruction is asked, the site's own included. That is not a
    detail: the site's first triple is a `mov DPTR,#imm16`, which names no
    `direct` operand and so is in none of the three form tables -- and the
    guard runs on the instruction *after* the one just decoded, which is why a
    DPL/DPH store is never itself decoded into a window. `walk_why()` stops on
    one instead. `CommittedWindowTests` below is that fact stated as a rule
    about the committed tables, and this helper is what measures it.
    """
    insns, why = T.walk_why(d, start, max_insns)
    out = []
    for off, _, _ in insns:
        for hit in F.form_at(d, off):
            if hit[2] in (T.DPL, T.DPH):
                out.append(hit)
    return out, why


class StoreFormTests(unittest.TestCase):
    """Every construction that replaces DPTR or one of its bytes, keyed on
    the byte it writes."""

    def test_each_store_form_is_a_store_and_names_the_byte_it_writes(self):
        # `0x85` is not in this loop: it is two references rather than one,
        # and the case below holds it. Every other form in the store table
        # makes exactly one, which is what `one()` checks.
        for insn, byte in ((DPL_FROM_A, 0x82), (DPH_FROM_A, 0x83),
                           (DPL_FROM_R7, 0x82), (DPTRH_FROM_R4, 0x83),
                           (DPH_IMM, 0x83), (DPTRH_POPPED, 0x83),
                           (DPL_FROM_R0_PTR, 0x82), (DPL_FROM_R1_PTR, 0x82)):
            with self.subTest(insn=insn.hex(" ")):
                self.assertEqual(one(insn, 0), ("store", insn[0], byte))

    def test_the_operand_order_case_reads_its_second_operand(self):
        # `mov direct,direct` is `0x85 src dst`, so the byte the instruction
        # **writes** is its destination at d[i+2] and not its source. This is
        # the form a `d[i+1]` classifier gets wrong in the direction that
        # matters: `85 90 83` writes DPH, and reading d[i+1] would name a
        # store to P1 (`0x90`) and find no DPTR reference at all.
        self.assertEqual(DPH_FROM_P1[1], 0x90)
        self.assertIn(("store", 0x85, 0x83), form_at(DPH_FROM_P1, 0))
        # The mirror: a `0x85` whose *source* is DPL writes whatever P1 holds,
        # and the store cell names the destination both times.
        self.assertIn(("store", 0x85, 0x90),
                      form_at(bytes([0x85, 0x82, 0x90]), 0))
        # And the operand index is the census's, not this file's, so the two
        # cannot disagree about it.
        self.assertEqual(DPH_FROM_P1[0], W.MOV_DIRECT_DIRECT)
        self.assertIs(F.dptr_store_byte, W.dptr_store_byte)

    def test_the_operand_order_case_is_also_a_read_of_its_source(self):
        # The other half of the same form, and the one a classifier that
        # returns a single reference cannot express. `85 83 f0` is `mov B,DPH`:
        # it reads DPH and writes B, so the source is a read-form reference
        # and the destination is not a DPTR write at all. Classifying the
        # instruction by its store half alone drops the read, and the store
        # half is not optional -- `85 82 0e` reads DPL *and* writes 0x0e, so
        # the instruction is in `READ_FORMS` and `STORE_FORMS` at once.
        self.assertEqual(form_at(READ_DPH_FROM_85, 0),
                         [("read", 0x85, 0x83), ("store", 0x85, 0xF0)])
        self.assertEqual(form_at(READ_DPL_FROM_85, 0),
                         [("read", 0x85, 0x82), ("store", 0x85, 0x0E)])
        # The two halves need not agree on being DPTR bytes, and here neither
        # the store half of the first nor the destination of the second is.
        self.assertNotIn(("store", 0x85, T.DPL), form_at(READ_DPH_FROM_85, 0))
        self.assertNotIn(("store", 0x85, T.DPH), form_at(READ_DPL_FROM_85, 0))
        # And they need not even be *different* bytes: `85 82 82` is one
        # instruction that both reads and writes DPL, so it is a read and a
        # store of the same operand. Nothing in this image does that, which is
        # exactly why it needs a fixture rather than a counted claim.
        self.assertEqual(form_at(BOTH_HALVES_85, 0),
                         [("read", 0x85, 0x82), ("store", 0x85, 0x82)])
        # The two directions are distinguished only by the operand, so the
        # read really is the source and not the destination re-sorted.
        self.assertEqual(READ_DPL_FROM_85[1], T.DPL)
        self.assertNotEqual(READ_DPL_FROM_85[1], READ_DPL_FROM_85[2])

    def test_every_opcode_the_guard_accepts_is_in_the_store_table(self):
        # The load-bearing structural case, and the reason the store table is
        # allowed to be written out by hand: it is a *second* list of the
        # constructions, and a second list is exactly the thing that drifts.
        # `is_dptr_rebuild()` is the guard `walk_why()` actually runs, so an
        # opcode the guard accepts and this table does not name is a
        # construction the census would not count -- and a census that
        # under-counts its own subject looks like a firmware that does not use
        # it. The sweep is the whole opcode map crossed with the three operand
        # bytes that can appear in a `direct` position, at three lengths, and
        # it is a set of opcodes rather than a list of byte strings so the
        # assertion names the disagreement instead of its encoding.
        #
        # **It is a one-way check and cannot be the completeness one.** Both
        # lists omitted `0x86`/`0x87` before this was written, so they agreed
        # on exactly the rows that were wrong -- the sweep had a blind spot
        # and the tables had the same one, which is what
        # `test_the_three_tables_are_the_whole_direct_map` is for.
        accepted = set()
        for op in range(0x100):
            for operand in (0x82, 0x83, 0x00):
                for insn in (bytes([op, operand]),
                             bytes([op, operand, operand]),
                             bytes([op, operand, operand, operand])):
                    if T.is_dptr_rebuild(insn, 0) and \
                            ("store", op, operand) not in F.form_at(insn, 0):
                        accepted.add(op)
        # `mov DPTR,#imm16` is the one construction that names no operand at
        # all, so there is no byte for this census to key on and it is not a
        # gap in the table. It is why the census is a byte census and not a
        # count of every way DPTR is replaced, and the assertion says so by
        # naming it and nothing else.
        self.assertEqual(accepted, {T.MOV_DPTR})

    def test_a_form_whose_operand_runs_past_the_end_is_not_a_reference(self):
        # The bounds discipline that lets the sweep run to the last offset of
        # the file. A half-written instruction at the end of a buffer is not a
        # reference to anything, and returning the byte anyway would put a
        # store into a cell on the strength of a byte that is not there.
        self.assertEqual(F.form_at(bytes([0xF5]), 0), [])
        self.assertEqual(F.form_at(bytes([0xE5]), 0), [])
        self.assertEqual(F.form_at(bytes([0x05]), 0), [])
        self.assertEqual(F.form_at(bytes([0x87]), 0), [])
        self.assertEqual(F.form_at(bytes([0x85, 0x90]), 0), [])
        # The two-byte forms still answer on the same buffer, so the case is
        # about the missing operand and not about the length of the buffer.
        self.assertEqual(F.form_at(bytes([0xE5, 0x82]), 0),
                         [("read", 0xE5, 0x82)])


class ReadFormTests(unittest.TestCase):
    """The other side of the operand order, which is a load and not a
    rebuild. Issue #1027 names the discriminator and this is where it is held
    against every read form rather than against the list of four rows the
    committed tables happen to carry."""

    def test_each_read_form_is_a_read(self):
        for insn, byte in ((READ_DPL, 0x82), (READ_DPH_INTO_R5, 0x82),
                           (PUSH_DPL, 0x82), (READ_DPL_VIA_R0, 0x82),
                           (READ_DPL_VIA_R1, 0x82), (ADD_DPL_TO_A, 0x82),
                           (ADD_DPH_CARRY, 0x83), (ORL_A_FROM_DPL, 0x82)):
            with self.subTest(insn=insn.hex(" ")):
                self.assertEqual(one(insn, 0), ("read", insn[0], byte))

    def test_no_read_form_is_a_rebuild(self):
        # The claim the two buckets being separate rests on. `mov a,0x82` and
        # `mov 0x82,a` are one byte apart in the opcode map and are the same
        # byte of DPTR read and written; a sweep that counted a window's
        # `0x82` references without asking which direction would charge a
        # window ending on a *load* to a pointer rebuild it never had.
        for insn in (READ_DPL, READ_DPH_INTO_R5, PUSH_DPL, READ_DPL_VIA_R0,
                     READ_DPL_VIA_R1, ADD_DPL_TO_A, ADD_DPH_CARRY,
                     ORL_A_FROM_DPL):
            with self.subTest(insn=insn.hex(" ")):
                self.assertFalse(T.is_dptr_rebuild(insn, 0))
        self.assertTrue(T.is_dptr_rebuild(DPL_FROM_A, 0))

    def test_the_logical_group_splits_on_the_operand_order(self):
        # The discriminator applied to the one group where nothing about the
        # byte separates the two directions. `0x45` and `0x42` both name
        # `0x82` in the same position and both take a byte address; the
        # accumulator is the destination in the first and the source in the
        # second, so the first reads DPL and the second rewrites it. The
        # committed Ghidra listings decode them as `45 82 orl A, DPL` and
        # `42 f0 orl B, A`, and that is the authority for the operand order --
        # `disasm8051.mnemonic()` renders the first as `orl a,0x82` and the
        # second as `db 0x42`, so neither the label nor the bucket can be
        # read off it.
        self.assertEqual(form_at(ORL_A_FROM_DPL, 0),
                         [("read", 0x45, 0x82)])
        self.assertEqual(form_at(ORL_DPL_FROM_A, 0),
                         [("in place", 0x42, 0x82)])
        # Same byte, same position, opposite buckets, and neither is a store:
        # one rewrites DPL with A and the other only ever reads it.
        self.assertFalse(T.is_dptr_rebuild(ORL_A_FROM_DPL, 0))
        self.assertFalse(T.is_dptr_rebuild(ORL_DPL_FROM_A, 0))
        # The immediate spellings of the same group name a *literal* rather
        # than a byte address, so `54 82` is not a reference to DPL at all and
        # the census has to decline it. This is the assertion the correction
        # turned on: the byte is `0x82`, the opcode sits in the middle of the
        # logical group, and there is nothing to count.
        self.assertEqual(form_at(ORL_A_LITERAL, 0), [])
        self.assertEqual(form_at(bytes([0x44, 0x82]), 0), [])
        self.assertEqual(form_at(bytes([0x64, 0x82]), 0), [])

    def test_the_rn_and_the_accumulator_forms_are_both_reads(self):
        # `0xE5 mov a,direct` and `0xA8`-`0xAF mov rN,direct` are the same
        # read written two ways, and the committed tables carry three rows of
        # the second against none of the first. Asserting the whole `0xA8`
        # group rather than `0xAD` alone is the part that matters: a table
        # carrying only the register the four rows happen to name would pass
        # every case the committed data can reach.
        for op in range(0xA8, 0xB0):
            for byte in (0x82, 0x83):
                with self.subTest(op=hex(op), byte=hex(byte)):
                    self.assertEqual(F.form_at(bytes([op, byte]), 0),
                                     [("read", op, byte)])


class InPlaceFormTests(unittest.TestCase):
    """The forms that name DPL/DPH and change it without replacing it.

    They are in the census because the census's subject is *every way this
    image names the two bytes*. A third bucket that did not exist would let
    `dptr-rebuild-walk-guard.md` §3's decision to decline them read as an
    absence of evidence rather than as the choice it is.
    """

    def test_each_in_place_form_is_neither_a_store_nor_a_read(self):
        for insn, byte in ((XCH_DPL, 0x82), (ANL_DIRECT_DPL, 0x82),
                           (INC_DPL, 0x82), (DEC_DPL, 0x82),
                           (ORL_DPL_FROM_A, 0x82), (CLR_DPH, 0x83)):
            with self.subTest(insn=insn.hex(" ")):
                self.assertEqual(one(insn, 0), ("in place", insn[0], byte))
                self.assertFalse(T.is_dptr_rebuild(insn, 0))

    def test_a_form_classifies_the_same_at_both_spellings(self):
        # This census keys on the operand byte rather than on a decode, so
        # the same instruction classifies the same whether or not the byte
        # that follows it is present. A census that walked instruction
        # boundaries would have to know the instruction is three bytes to
        # know that `0x7F` starts the next one; the byte keying is what makes
        # the length irrelevant here.
        #
        # `disasm8051.OPCODE_LEN[0x53] == 3` is asserted alongside it because
        # a case guarding against a length table that is already right is
        # guarding against nothing, and this one is right: the committed
        # listings decode `53 00 07` as `anl 0x00, #0x7`, three bytes.
        from disasm8051 import OPCODE_LEN
        self.assertEqual(OPCODE_LEN[0x53], 3)
        self.assertEqual(form_at(ANL_DPL_THEN_NEXT, 0),
                         form_at(ANL_DIRECT_DPL, 0))


class BucketShapeTests(unittest.TestCase):
    """The three tables, as a shape rather than as a count."""

    def test_only_the_operand_order_form_is_in_two_buckets(self):
        # Two opcodes in two buckets would mean a window whose verdict depended
        # on the order the tables were consulted, which is the one thing a
        # classifier keyed on bytes is supposed to make impossible. The one
        # exception is the point rather than a leak: `mov direct,direct` makes
        # a read and a store at one instruction, so it is held to *that* pair
        # by name rather than being allowed anywhere.
        self.assertEqual(set(F.STORE_FORMS) & set(F.READ_FORMS),
                         {T.MOV_DIRECT_DIRECT})
        self.assertEqual(set(F.STORE_FORMS) & set(F.IN_PLACE_FORMS), set())
        self.assertEqual(set(F.READ_FORMS) & set(F.IN_PLACE_FORMS), set())

    def test_every_form_the_census_names_is_the_8051_spelling_it_claims(self):
        # The three tables spell their forms out rather than generating them,
        # because `disasm8051.mnemonic()` does not render all of them -- it
        # prints `42 f0` as `db 0x42` and `63 65 ff` as `db 0x63` where the
        # machine executes `orl B, A` and `xrl 0x65, #0xff`. Asserting each
        # table against `trace_xdata_refs.DIRECT_STORE_OPS` keeps the two
        # honest about each other without this file depending on the
        # defective rendering, and the rendering itself is asserted once below
        # as a fact about the tree rather than as a note.
        for op in F.STORE_FORMS:
            with self.subTest(op=hex(op)):
                self.assertIn(op, T.DIRECT_STORE_OPS | {T.MOV_DIRECT_DIRECT}
                              | GUARD_GAP_OPS)
        for op in F.IN_PLACE_FORMS:
            with self.subTest(op=hex(op)):
                self.assertNotIn(op, T.DIRECT_STORE_OPS)
        # And the spellings the tables write out are the machine's, not the
        # renderer's: the three table rows that name the accumulator forms
        # say `a,direct` where the renderer would agree only by accident,
        # and the two-byte `direct,a` row says what `42 f0` actually is.
        from disasm8051 import mnemonic
        self.assertEqual(F.IN_PLACE_FORMS[0x42], "orl  direct,a")
        self.assertEqual(F.READ_FORMS[0x45], "orl  a,direct")
        # The renderer is right about this half of the group and the census
        # declines it for a different reason, which is the point of holding
        # both in one place: `0x54` is `ANL A,#data`, two bytes, and
        # `54 82` really is `anl a,#0x82` -- the trailing `0x7F` is the next
        # instruction's byte, not a third byte of this one. The census
        # declines the same bytes because the operand is a *literal* and so
        # names no byte address. Asserted as a pair because either half alone
        # is satisfied by a table that simply omitted the group, and because a
        # reader who thought the renderer wrong here would be "fixing" a row
        # that is already correct.
        self.assertEqual(mnemonic(ORL_A_LITERAL, 0), "anl  a,#0x82")
        self.assertEqual(F.form_at(ORL_A_LITERAL, 0), [])
        # And the half the renderer does get wrong, which is the other side of
        # the same group: the `direct,A` and `direct,#data` rows it has no
        # spelling for and emits as `db`.
        self.assertEqual(mnemonic(bytes([0x42, 0xF0]), 0), "db   0x42")
        self.assertEqual(mnemonic(bytes([0x63, 0x65, 0xFF]), 0), "db   0x63")

    def test_the_store_table_is_the_guard_opcode_set_plus_a_named_gap(self):
        # `DIRECT_STORE_OPS` plus the `0x85` exception is what
        # `trace_xdata_refs.is_dptr_rebuild()` consults, and the census's
        # store table has to be that set or the census is counting something
        # else. Asserted as equality rather than as a count, so an opcode
        # added to one and not the other is red whichever way it went.
        #
        # The equality is against the guard's set **plus the two `mov
        # direct,@Ri` forms the guard does not name**. That delta is
        # `GUARD_GAP_OPS`, written out here so it is a decision on the page
        # rather than a difference a reader has to notice themselves;
        # `dptr-rebuild-walk-guard.md` §3 records what it is and
        # `dptr-guard-census-vs-1027.md` §3 counts it.
        self.assertEqual(set(F.STORE_FORMS),
                         set(T.DIRECT_STORE_OPS) | {0x85} | GUARD_GAP_OPS)

    def test_the_two_mov_direct_at_ri_forms_are_the_only_gap(self):
        # The census counts the two forms the guard declines, and nothing
        # else. Asserted against the guard's own set rather than as "two",
        # so widening either list without the other is red whichever way it
        # went -- and so the delta cannot quietly grow into a different claim.
        self.assertEqual(GUARD_GAP_OPS, frozenset((0x86, 0x87)))
        for op in GUARD_GAP_OPS:
            with self.subTest(op=hex(op)):
                self.assertFalse(T.is_dptr_rebuild(bytes([op, 0x82]), 0))

    def test_the_three_tables_are_the_whole_direct_map(self):
        # The completeness claim, against an oracle that shares no source with
        # the tables. `DIRECT_BEARING` is written out above from the
        # instruction set; the three tables are written out in the tool. The
        # two cannot drift together, which is the failure this case exists
        # for: the store table and `is_dptr_rebuild()` omitted the same four
        # opcodes and so agreed on every row that was wrong.
        tables = set(F.STORE_FORMS) | set(F.READ_FORMS) | set(F.IN_PLACE_FORMS)
        self.assertEqual(tables, set(DIRECT_BEARING))
        # And the excluded class is the bit-addressed one, by name, rather
        # than by whatever happened to be left over.
        self.assertEqual(tables & set(BIT_ADDRESSED), set())
        # `mov DPTR,#imm16` is the fourth thing that replaces the pointer and
        # is in none of them, because it names no `direct` operand at all.
        self.assertNotIn(T.MOV_DPTR, tables)

    def test_the_completeness_check_can_reject_a_wrong_union(self):
        # The negative control for the case above, and the reason the case
        # above is not a tautology that happens to pass. A completeness check
        # that has only ever accepted one union is indistinguishable from one
        # that cannot fail, so each way of getting the union wrong is driven
        # through the same comparison and asserted to be caught.
        tables = set(F.STORE_FORMS) | set(F.READ_FORMS) | set(F.IN_PLACE_FORMS)
        # One member missing from the oracle -- the shape of a list that is
        # *nearly* complete, which is what this file's own lead names as the
        # failure a hand-written list cannot detect by eye.
        self.assertNotEqual(tables, set(DIRECT_BEARING) - {0x45})
        # One non-member added. `0x2C` is `add a,r4`: a register form with no
        # operand byte at all, and one of the five this table wrongly carried
        # before the correction the listings forced.
        self.assertNotEqual(tables | {0x2C}, set(DIRECT_BEARING))
        # A whole class gone, rather than a lone member -- the 8052 additions,
        # which is what reading the instruction set as base-MCS-51-only looks
        # like: the six `direct,A`/`direct,#data` rows of the logical group,
        # without which the list is six short of the map.
        without_8052 = set(DIRECT_BEARING) - {0x42, 0x43, 0x52, 0x53,
                                              0x62, 0x63}
        self.assertNotEqual(tables, without_8052)


class ListingCrossCheckTests(unittest.TestCase):
    """`DIRECT_BEARING` against the committed Ghidra listings, for real.

    The completeness case above compares the tool's three tables against a
    transcription of the opcode map, and both were 49 members written by the
    same reading of the instruction set -- so it passed by construction on the
    five rows the listings refute. This is the check that does not share a
    source with what it checks: it opens `ec/decompiled/*/*.asm` and reads the
    instruction's own length out of the listing's byte columns.

    Read once for the class rather than per case; the parse is asserted here
    so a listing format that drifts is a failure of *this* class and not a
    mysterious disagreement in the cases below it.
    """

    @classmethod
    def setUpClass(cls):
        cls.lengths, cls.unparsed = listing_instruction_lengths()

    def _refuted(self, lengthmap):
        """`[(opcode, decoded lengths, required)]` the listings refute.

        The comparison itself, written once so the case below and the negative
        control beside it cannot drift into checking different things. It is
        handed the map rather than reading the global so the control can drive
        a map the committed one does not contain.
        """
        return [(op, sorted(self.lengths.get(op, ())), lengthmap[op])
                for op in sorted(lengthmap)
                if self.lengths.get(op) != {lengthmap[op]}]

    def test_every_listing_line_was_read(self):
        # The population the cases below are drawn from. A parse that
        # silently skipped half the listings would leave them passing on a
        # fraction of the evidence, which is the shape of claim
        # `CLAUDE.md` warns about rather than a bug in a tool.
        self.assertEqual(self.unparsed, [])
        self.assertGreater(sum(len(v) for v in self.lengths.values()), 0)

    def test_every_direct_bearing_opcode_is_decoded_in_the_listings(self):
        # The check's trigger, asserted per opcode: a member of the map that
        # no listing decodes cannot be corroborated by the listings, and a
        # whole class of them being absent would leave this class passing on
        # the members that happen to survive.
        for op in sorted(DIRECT_BEARING):
            with self.subTest(op=hex(op)):
                self.assertIn(op, self.lengths,
                              f"0x{op:02X} is in DIRECT_BEARING but no "
                              f"committed listing decodes it, so the map's "
                              f"claim about it rests on the transcription "
                              f"alone")

    def test_no_direct_bearing_opcode_decodes_at_one_byte(self):
        # The claim itself, and the whole of it: a byte-addressed `direct`
        # operand is a second byte, so a one-byte decode refutes the row.
        self.assertEqual(self._refuted(DIRECT_LENGTH), [])

    def test_the_cross_check_rejects_the_map_this_one_corrected(self):
        # The negative control, driven through the *same* comparison as the
        # case above, and over the mistake this file actually made rather than
        # an invented one: the pre-correction map carried `0x26`, `0x27`,
        # `0x36`, `0x96` and `0x97`, which the listings decode `add A, @R0`,
        # `add A, @R1`, `addc A, @R0`, `subb A, @R0` and `subb A, @R1`. All
        # five are one byte, all five are refused, and the assertion names
        # each of them so a check that quietly stopped refusing some of them
        # is red here rather than silently weaker.
        #
        # A completeness check that has only ever accepted one map is
        # indistinguishable from one that cannot fail.
        pre = {**DIRECT_LENGTH, **{op: 2 for op in REFUTED_REGISTER_INDIRECT}}
        self.assertEqual([op for op, _, _ in self._refuted(pre)],
                         sorted(REFUTED_REGISTER_INDIRECT))


class DiscriminatorTests(unittest.TestCase):
    """The counting trap, in the shape its own false positive took.

    A sweep for `0x82` in a rendered `window` cell has three ways to be wrong
    and issue #1027 names two of them: a *read* rather than a store, and this
    file's third one, a `0x83` that is a jump **target address** rather than
    an operand. Both halves of that third case are driven from one fixture,
    so the verdicts are asserted to differ rather than one of them merely
    being asserted.

    **The store is never inside the window, and that is the mechanism, not a
    detail of the fixture.** `walk_why()` runs its reload guard on the
    instruction *after* the one just decoded, so it stops *at* a DPTR store
    without decoding it. The two windows below therefore differ in their
    terminator -- `flow opcode` against `DPTR reloaded` -- and not in a
    decoded store, and a case written any other way would be asserting
    something the guard makes impossible.
    """

    # The three instructions of `ec-07c4-07d5-sites.csv` 0x0AD99's committed
    # window, and the same three with a real DPTR store where the `ljmp` is.
    AS_COMMITTED = (WRITE, bytes([0x7F, 0xE1]), LJMP_TARGET)
    WITH_STORE = (WRITE, bytes([0x7F, 0xE1]), DPL_STORE_AT_TARGET)
    # The offset both fixtures put their third instruction at, and the one the
    # two verdicts differ at. The two are the same length in bytes, so
    # nothing about the fixture gives the difference away.
    AT = len(SITE) + len(WRITE) + 2

    def _window(self, insns):
        return T.walk_why(fixture(SITE, *insns), 0, BUDGET)[0]

    def _rendered(self, insns):
        d = fixture(SITE, *insns)
        return " ; ".join(T.mnemonic(d, off) for off, _, _ in self._window(insns))

    def test_a_jump_target_is_not_a_store(self):
        # The discriminator itself, on the bytes. `0x02` is in none of the
        # three form tables, so the `0x83` that follows it is a target address
        # and there is no reference to classify at all.
        self.assertEqual(F.form_at(fixture(LJMP_TARGET), 0), [])
        forms, why = window_forms(fixture(SITE, *self.AS_COMMITTED), 0)
        self.assertEqual(forms, [],
                         "the `0x83` of `ljmp 0x83d6` is a target address, "
                         "not an operand")
        # The site, the `movx`, the immediate and the jump are all decoded, so
        # the empty verdict is the classifier's and not a window that decoded
        # nothing -- and the jump is decoded *before* the flow stop, which is
        # why the window is four instructions and not three.
        self.assertEqual(why, T.FLOW_END)
        self.assertEqual(len(self._window(self.AS_COMMITTED)), 4)

    def test_a_store_where_the_jump_target_was_is_a_store(self):
        # The other half of the pair, at the same offset, so the difference
        # between the two verdicts is the discriminator and not the fixture's
        # length or its position in the window.
        self.assertEqual(F.form_at(fixture(SITE, *self.WITH_STORE), self.AT),
                         [("store", 0xF5, 0x82)])
        # And the window changes with it -- one instruction shorter, and it
        # stops on the reload rather than on the flow opcode. The store itself
        # is not decoded, which is why `window_forms` finds nothing here
        # either and why `CommittedWindowTests` can hold a rule over the
        # committed tables that no window violates.
        _, why = window_forms(fixture(SITE, *self.WITH_STORE), 0)
        self.assertEqual(why, T.RELOAD_END)
        self.assertNotEqual(why, T.FLOW_END)
        self.assertEqual(len(self._window(self.WITH_STORE)), 3)
        self.assertEqual(len(fixture(SITE, *self.WITH_STORE)),
                         len(fixture(SITE, *self.AS_COMMITTED)))

    def test_a_substring_search_would_have_found_the_jump_target(self):
        # The half that keeps the case from being a test of a problem nobody
        # has. The rendered window cell does contain `0x83` -- the committed
        # cell at `0x0AD99` reads `movx @dptr,a ; mov r7,#0xe1 ; ljmp 0x83d6` --
        # so a sweep that searched it for the byte would have counted this row
        # as a DPTR store. Asserted here rather than assumed, because a
        # discriminator guarding against nothing is indistinguishable from one
        # that has been left switched off.
        rendered = self._rendered(self.AS_COMMITTED)
        self.assertIn("ljmp", rendered)
        self.assertIn("0x83", rendered)


class CommittedWindowTests(unittest.TestCase):
    """The rule over the committed tables, in place of the issue's 27.

    Issue #1027's count of budget-truncated rows holding a DPTR store is a
    measurement of the tree **before** the guard was widened, and
    `dptr-rebuild-walk-guard.md` §6 lists those 27 as the rows whose `window`
    *and* `terminator` moved. What is left is a rule about the tree as it
    stands, and the rule is the point: a re-cut that put a store back inside a
    window is the defect those 27 rows were, and it is caught here by shape
    rather than by an address list a re-cut would have to edit.

    **The rule is stronger than the issue's, and the strength is the guard's
    own doing rather than a decision.** `walk_why()` tests the reload guard on
    the instruction *after* the one just decoded, so a window can never contain
    a DPTR store at all: it stops at one. The issue's form of the claim --
    only over the budget-truncated rows -- is therefore a corollary of a
    statement about *every* row, and the corollary is held beside it because
    it is the one a reader of #1027 arrives with.
    """

    @classmethod
    def setUpClass(cls):
        cls.image = FIRMWARE.read_bytes()

    def _rows(self, name):
        with open(ANNOT / name, newline="") as f:
            return list(csv.DictReader(f))

    def test_no_committed_window_holds_a_store(self):
        budget_rows = 0
        for name in SIX:
            for row in self._rows(name):
                off = int(row["file_offset"], 16)
                forms, why = window_forms(self.image, off)
                if why == T.budget_end(BUDGET):
                    budget_rows += 1
                stores = [f for f in forms if f[0] == "store"]
                self.assertEqual(
                    stores, [],
                    f"{name} row {row['file_offset']}: its window holds a "
                    f"DPTR store, so the window ran past a pointer rebuild "
                    f"and every `access` cell behind it is charging the "
                    f"`movx` to the site's own address")
        # The rule's own trigger, asserted non-zero: a re-cut that emptied the
        # budget rows altogether would satisfy it by never being applied.
        self.assertGreater(budget_rows, 0)

    def test_no_budget_truncated_row_holds_a_store(self):
        # The issue's own framing, kept beside the stronger claim above so the
        # sentence a reader arrives with is the one that is held. Measured
        # through the committed `terminator` cell rather than a re-derived
        # one, so it is a statement about the tables and not about this run.
        budget_rows = 0
        for name in SIX:
            for row in self._rows(name):
                if row["terminator"] != T.budget_end(BUDGET):
                    continue
                budget_rows += 1
                forms, _ = window_forms(self.image, int(row["file_offset"], 16))
                stores = [f for f in forms if f[0] == "store"]
                with self.subTest(table=name, offset=row["file_offset"]):
                    self.assertEqual(
                        stores, [],
                        "a budget-truncated row whose window holds a DPTR "
                        "store is the defect the widened guard removed")
        # Asserted non-zero for the same reason as above. This is the
        # corollary of the rule before it rather than an independent one -- no
        # committed `terminator` cell is both budget-truncated and
        # re-derivable as store-holding -- so the only thing that could make
        # it vacuous is a re-cut that emptied the budget rows.
        self.assertGreater(budget_rows, 0)

    def test_every_committed_terminator_is_what_the_image_gives(self):
        # The premise the two rules above rest on, stated separately so a
        # failure in it is not reported as a failure of the rules: a
        # `terminator` cell that had drifted from the guard would make the
        # whole six look budget-truncated or not by accident.
        for name in SIX:
            for row in self._rows(name):
                off = int(row["file_offset"], 16)
                with self.subTest(table=name, offset=row["file_offset"]):
                    self.assertEqual(T.walk_why(self.image, off, BUDGET)[1],
                                     row["terminator"])

    def test_the_committed_access_cells_still_come_out_of_those_windows(self):
        # `classify()` re-derived from the image must give back the committed
        # cell, or the windows this file is reading are not the ones the tables
        # were cut with. The same refusal `walk_budget_census` makes, run over
        # the six rather than over the census.
        for name in SIX:
            for row in self._rows(name):
                off = int(row["file_offset"], 16)
                got = T.classify(T.walk_why(self.image, off, BUDGET)[0])
                self.assertEqual(got, row["access"],
                                 f"{name} row {row['file_offset']}")

    def test_a_read_of_dpl_in_a_committed_window_is_a_read_here(self):
        # The issue names four rows of `xdata-0400-045f-sites.csv` whose
        # `window` cells read `mov r3,0x82`, `mov r1,0x82` and the like, and
        # warns they must not be swept in with the stores. Asserted on the
        # rows that carry a read rather than on those four addresses: the
        # claim is about the direction, and a table that grew or lost a row
        # would break a list while leaving the rule true. The count is
        # asserted only as non-zero, so the case fails if the direction is
        # never exercised and never has to be edited when a re-cut moves one.
        reads = 0
        for name in SIX:
            for row in self._rows(name):
                forms, _ = window_forms(self.image, int(row["file_offset"], 16))
                reads += sum(1 for f in forms if f[0] == "read")
        self.assertGreater(reads, 0,
                           "no committed window holds a read of DPL/DPH, so "
                           "the direction the issue warns about is never "
                           "exercised here")


class OutputTests(unittest.TestCase):
    """The tool's own words, which are claims.

    A census that prints a bare `0` for a form the file does not use is a
    cell that reads as an absence, and that is the overclaim
    `ec/annotations/registers.yaml` and `CLAUDE.md` both warn against. The
    phrasing is asserted rather than trusted, and the run is a subprocess so
    the exit code is part of what is held.
    """

    def test_a_form_the_file_does_not_use_says_so(self):
        # A fixture holding one store and one read, so the masking forms --
        # opcodes in the in-place table with no `0x82` or `0x83` operand
        # anywhere in it -- come back empty and have to say why.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.bin"
            path.write_bytes(fixture(SITE, DPL_FROM_A, READ_DPL))
            run = subprocess.run(
                [sys.executable, str(HERE / "dptr_rebuild_forms.py"),
                 str(path)],
                capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("not found by this method", run.stdout)
        # The one that is used is reported as a number, so the phrase cannot
        # be satisfying the check on its own.
        self.assertIn("mov  direct,a", run.stdout)
        # And the two directions are separated in the output rather than
        # summed, which is the point of the three buckets.
        self.assertIn("store forms", run.stdout)
        self.assertIn("read forms", run.stdout)
        self.assertIn("in place forms", run.stdout)
        # The byte-census caveat is printed on every run rather than left to
        # the module docstring, because the numbers are what a reader takes
        # out of this output and the numbers are not what they look like.
        self.assertIn("not a disassembly", run.stdout)

    def test_the_csv_is_the_same_census_in_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.bin"
            path.write_bytes(fixture(SITE, DPL_FROM_A, DPL_FROM_A, READ_DPL,
                                     READ_DPH_INTO_R5))
            run = subprocess.run(
                [sys.executable, str(HERE / "dptr_rebuild_forms.py"),
                 str(path), "--csv"],
                capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = list(csv.DictReader(run.stdout.splitlines()))
        got = {(r["bucket"], r["opcode"]): int(r["references"]) for r in rows}
        self.assertEqual(got[("store", "0xF5")], 2)
        self.assertEqual(got[("read", "0xE5")], 1)
        self.assertEqual(got[("read", "0xAD")], 1)
        # A form the fixture does not use is still a row, carrying nothing:
        # a table that listed only the forms it found could not be read as an
        # answer about the ones it did not.
        self.assertIn(("in place", "0xC5"), got)
        self.assertEqual(got[("in place", "0xC5")], 0)

    def test_a_file_that_is_not_there_is_an_error_not_an_empty_census(self):
        # A sweep that found nothing because it could not read its input is
        # the same output as a sweep that found nothing in a file full of
        # `0x00`, and the second is a finding.
        run = subprocess.run(
            [sys.executable, str(HERE / "dptr_rebuild_forms.py"),
             "/nonexistent/firmware.bin"],
            capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 1)
        self.assertIn("note:", run.stderr)
        self.assertEqual(run.stdout, "")


if __name__ == "__main__":
    unittest.main()
