#!/usr/bin/env python3
"""The DPL/DPH form census, per form and on the committed windows.

Issue #1027 counted one direction of the 8051's `direct` operand -- `mov
0x82,<src>`, which writes DPTR's low byte -- and warned about the other, `mov
<dst>,0x82`, which only reads it. The read forms had never been counted
anywhere in the tree, so the sweep the issue proposes would have had to invent
its own answer to the question it was careful to ask.
`../../docs/findings/dptr-guard-census-vs-1027.md` is the write-up and the
counts; this is the part of it that has to stay true.

Three things are held here, and the third is the one a re-cut can break:

- **Per form, from bytes.** Every opcode in each of the three buckets, driven
  through `form_at()` as a bare `bytes` fixture, asserted on the bucket *and*
  on the byte the instruction actually touches. The 8051's one form that names
  its operands in the other order, `mov direct,direct` (`0x85`), is a case of
  its own: the byte this census keys on is its **second** operand there, so a
  classifier reading `d[i+1]` reads the *source* and would find none of the 35
  references this image has. The operand index is delegated to
  `walk_budget_census.dptr_store_byte()`, and the case here is what stops this
  file growing a second opinion about it.
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
import csv
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

# The reads, which rebuild nothing and must never be swept in with the stores.
READ_DPL = bytes([0xE5, 0x82])        # mov a,0x82
READ_DPH_INTO_R5 = bytes([0xAD, 0x82])  # mov r5,0x82
PUSH_DPL = bytes([0xC0, 0x82])        # push 0x82

# In place: a direct operand naming DPL/DPH that changes it without replacing
# it. `0x54` is here in the 8051's three-byte spelling, and the two-byte one
# the length table decodes is asserted beside it, because the two differ only
# after the operand and this census never looks at the length.
XCH_DPL = bytes([0xC5, 0x82])         # xch a,0x82
ANL_DIRECT_DPL = bytes([0x54, 0x82, 0x7F])   # anl 0x82,#0x7f -- the 8051's form
ANL_DPL_TWO_BYTE = bytes([0x54, 0x82])        # what OPCODE_LEN frames
INC_DPL = bytes([0x05, 0x82])         # inc 0x82

# `ec-07c4-07d5-sites.csv` 0x0AD99, verbatim: the committed window cell reads
# `movx @dptr,a ; mov r7,#0xe1 ; ljmp 0x83d6`, and the `0x83` in it is a jump
# **target address** rather than an operand. A sweep that searched the rendered
# cell for `0x83` would count this row as a DPTR store.
LJMP_TARGET = bytes([0x02, 0x83, 0xD6])
# And the store that stood at the same place, which is the other half of the
# pair: `0x2C305` after `0x0AD99`'s shape is `mov 0x82,a`.
DPL_STORE_AT_TARGET = bytes([0xF5, 0x82])


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
        hit = F.form_at(d, off)
        if hit is not None and hit[2] in (T.DPL, T.DPH):
            out.append(hit)
    return out, why


class StoreFormTests(unittest.TestCase):
    """Every construction that replaces DPTR or one of its bytes, keyed on
    the byte it writes."""

    def test_each_store_form_is_a_store_and_names_the_byte_it_writes(self):
        for insn, byte in ((DPL_FROM_A, 0x82), (DPH_FROM_A, 0x83),
                           (DPL_FROM_R7, 0x82), (DPTRH_FROM_R4, 0x83),
                           (DPH_IMM, 0x83), (DPTRH_POPPED, 0x83),
                           (DPH_FROM_P1, 0x83)):
            with self.subTest(insn=insn.hex(" ")):
                self.assertEqual(form_at(insn, 0),
                                 ("store", insn[0], byte))

    def test_the_operand_order_case_reads_its_second_operand(self):
        # `mov direct,direct` is `0x85 src dst`, so the byte the instruction
        # **writes** is its destination at d[i+2] and not its source. This is
        # the form a `d[i+1]` classifier gets wrong in the direction that
        # matters: `85 90 83` writes DPH, and reading d[i+1] would name a
        # store to P1 (`0x90`) and find no DPTR reference at all.
        self.assertEqual(DPH_FROM_P1[1], 0x90)
        self.assertEqual(form_at(DPH_FROM_P1, 0), ("store", 0x85, 0x83))
        # The mirror: a `0x85` whose *source* is DPL writes whatever P1 holds.
        # One form, two directions, and the cell names the destination both
        # times.
        self.assertEqual(form_at(bytes([0x85, 0x82, 0x90]), 0),
                         ("store", 0x85, 0x90))
        # And the operand index is the census's, not this file's, so the two
        # cannot disagree about it.
        self.assertEqual(DPH_FROM_P1[0], W.MOV_DIRECT_DIRECT)
        self.assertIs(F.dptr_store_byte, W.dptr_store_byte)

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
        accepted = set()
        for op in range(0x100):
            for operand in (0x82, 0x83, 0x00):
                for insn in (bytes([op, operand]),
                             bytes([op, operand, operand]),
                             bytes([op, operand, operand, operand])):
                    if T.is_dptr_rebuild(insn, 0) and \
                            F.form_at(insn, 0) != ("store", op, operand):
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
        self.assertIsNone(F.form_at(bytes([0xF5]), 0))
        self.assertIsNone(F.form_at(bytes([0xE5]), 0))
        self.assertIsNone(F.form_at(bytes([0x05]), 0))
        self.assertIsNone(F.form_at(bytes([0x85, 0x90]), 0))
        # The two-byte forms still answer on the same buffer, so the case is
        # about the missing operand and not about the length of the buffer.
        self.assertEqual(F.form_at(bytes([0xE5, 0x82]), 0),
                         ("read", 0xE5, 0x82))


class ReadFormTests(unittest.TestCase):
    """The other side of the operand order, which is a load and not a
    rebuild. Issue #1027 names the discriminator and this is where it is held
    against every read form rather than against the list of four rows the
    committed tables happen to carry."""

    def test_each_read_form_is_a_read(self):
        for insn, byte in ((READ_DPL, 0x82), (READ_DPH_INTO_R5, 0x82),
                           (PUSH_DPL, 0x82)):
            with self.subTest(insn=insn.hex(" ")):
                self.assertEqual(form_at(insn, 0), ("read", insn[0], byte))

    def test_no_read_form_is_a_rebuild(self):
        # The claim the two buckets being separate rests on. `mov a,0x82` and
        # `mov 0x82,a` are one byte apart in the opcode map and are the same
        # byte of DPTR read and written; a sweep that counted a window's
        # `0x82` references without asking which direction would charge a
        # window ending on a *load* to a pointer rebuild it never had.
        for insn in (READ_DPL, READ_DPH_INTO_R5, PUSH_DPL):
            with self.subTest(insn=insn.hex(" ")):
                self.assertFalse(T.is_dptr_rebuild(insn, 0))
        self.assertTrue(T.is_dptr_rebuild(DPL_FROM_A, 0))

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
                                     ("read", op, byte))


class InPlaceFormTests(unittest.TestCase):
    """The forms that name DPL/DPH and change it without replacing it.

    They are in the census because the census's subject is *every way this
    image names the two bytes*. A third bucket that did not exist would let
    `dptr-rebuild-walk-guard.md` §3's decision to decline them read as an
    absence of evidence rather than as the choice it is.
    """

    def test_each_in_place_form_is_neither_a_store_nor_a_read(self):
        for insn, byte in ((XCH_DPL, 0x82), (ANL_DIRECT_DPL, 0x82),
                           (ANL_DPL_TWO_BYTE, 0x82), (INC_DPL, 0x82)):
            with self.subTest(insn=insn.hex(" ")):
                self.assertEqual(form_at(insn, 0),
                                 ("in place", insn[0], byte))
                self.assertFalse(T.is_dptr_rebuild(insn, 0))

    def test_the_masking_forms_classify_the_same_at_both_spellings(self):
        # `disasm8051.OPCODE_LEN` gives the `0x54` group two bytes where the
        # 8051 has three, and this census keys on the operand byte rather than
        # on a decode, so the two spellings of the same instruction agree.
        # A census that walked instruction boundaries would put the immediate
        # of the three-byte form where the next instruction begins and count
        # it; the byte keying is what makes the length irrelevant here.
        self.assertEqual(form_at(ANL_DIRECT_DPL, 0),
                         form_at(ANL_DPL_TWO_BYTE, 0))


class BucketShapeTests(unittest.TestCase):
    """The three tables, as a shape rather than as a count."""

    def test_the_three_buckets_are_disjoint(self):
        # Two opcodes in two buckets would mean a window whose verdict depended
        # on the order the tables were consulted, which is the one thing a
        # classifier keyed on bytes is supposed to make impossible.
        buckets = [F.STORE_FORMS, F.READ_FORMS, F.IN_PLACE_FORMS]
        for i, first in enumerate(buckets):
            for second in buckets[i + 1:]:
                self.assertEqual(set(first) & set(second), set())

    def test_every_form_the_census_names_is_the_8051_spelling_it_claims(self):
        # The three tables spell their forms out rather than generating them,
        # because `disasm8051.mnemonic()` renders the `0x44`/`0x45`/`0x54`/
        # `0x55`/`0x64`/`0x65` group as A-operand forms -- `54 82` prints
        # `anl a,#0x82` where the machine writes DPL. Asserting each table
        # against `trace_xdata_refs.DIRECT_STORE_OPS` keeps the two honest
        # about each other without this file depending on the defective
        # rendering, and the rendering itself is asserted once below as a fact
        # about the tree rather than as a note.
        for op in F.STORE_FORMS:
            with self.subTest(op=hex(op)):
                self.assertIn(op, T.DIRECT_STORE_OPS | {T.MOV_DIRECT_DIRECT})
        for op in F.IN_PLACE_FORMS:
            with self.subTest(op=hex(op)):
                self.assertNotIn(op, T.DIRECT_STORE_OPS)
        from disasm8051 import mnemonic
        self.assertEqual(mnemonic(ANL_DPL_TWO_BYTE, 0), "anl  a,#0x82")
        self.assertEqual(F.form_at(ANL_DPL_TWO_BYTE, 0)[0], "in place")

    def test_the_store_table_is_the_guard_opcode_set(self):
        # `DIRECT_STORE_OPS` plus the `0x85` exception is what
        # `trace_xdata_refs.is_dptr_rebuild()` consults, and the census's
        # store table has to be that set or the census is counting something
        # else. Asserted as equality rather than as a count, so an opcode
        # added to one and not the other is red whichever way it went.
        self.assertEqual(set(F.STORE_FORMS), set(T.DIRECT_STORE_OPS) | {0x85})


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
        self.assertIsNone(F.form_at(fixture(LJMP_TARGET), 0))
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
                         ("store", 0xF5, 0x82))
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
