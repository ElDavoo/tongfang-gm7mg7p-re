#!/usr/bin/env python3
"""Every construction that replaces DPTR ends `walk_why()`'s window, and the
ones that do not are pinned beside them.

`trace_xdata_refs.py`'s guard tested `d[i] == MOV_DPTR` and nothing else, so a
walk ran straight past `mov DPL,A` and past `pop 0x83`, and `classify()`'s
`reads`/`writes` counters charged the `movx` behind one to the address the
*original* `MOV DPTR,#imm16` named. Two instances of that were corrected by
hand against the `.asm` listings, in three files, before anything counted how
many there were; `../../docs/findings/dptr-rebuild-walk-guard.md` is that
count and `../../docs/findings/walk-window-terminators.md:107` printed one of
the forms annotated *"walk()'s guard cannot see this"* long before the guard
was widened. The blindness was documented; what no case drove was a DPL/DPH
store *through the guard*, which is why a one-line guard could carry one
opcode for this long. That is the gap this file closes.

Three things are held here, and the third is the one that stops the defect
coming back:

- **Per construction.** Each way of rebuilding the pointer is driven through a
  hand-built `common`-region fixture and asserted to end the window, with a
  `movx` behind it that must not be counted. `test_trace_xdata_refs.py` holds
  the `MOV DPTR` case and the shape of the loop; this file holds the other
  five, which is a different population rather than a bigger version of the
  same one.
- **The negatives.** `swap a` (`0xC4`), `xch a,0x82`, `mov a,0x82` and
  `push 0x82` read or touch A and replace nothing, so they must not end a
  window. `0xC4` is asserted absent *by name*, because issue #517 lists it as
  a DPTR construction and it is not one -- there is no 8051 opcode that swaps
  DPTR. A guard that grew `0xC4` would truncate windows on an instruction
  that changes nothing, and the issue's list is the likely source of that edit.
- **Cross-tool agreement.** Over all 256 opcodes crossed with the three
  operand bytes that matter, `is_dptr_rebuild()` and
  `walk_budget_census.is_direct_dp_store()` must return the same answer.
  `DIRECT_STORE_OPCODES` used to be `(0xF5, 0x8F)` -- `mov direct,a` and
  `mov direct,r7` only -- so the census's class-A diagnosis could not see
  r0-r6, `0x75`, `0x85` or `0xD0` either. Two lists for one question is how
  the second one got there, and this is what makes a third one a red suite.

**No hardware, no firmware image, no Ghidra.** Every case builds its own
buffer, where the file offset equals the runtime address, which is what lets
the offsets in a case be the addresses in the fixture. The firmware-level
regression stays where the repo puts it: the seven `--check` runs against the
committed CSVs, which is a stronger gate than a fixture asserting a count.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# trace_xdata_refs and walk_budget_census both import disasm8051 by bare
# module name, the way register_ref_table.py does, so the tool directory has
# to be on the path before either is loaded rather than after.
sys.path.insert(0, str(HERE))
import trace_xdata_refs as T          # noqa: E402
import walk_budget_census as W        # noqa: E402

# One instruction in none of the guards' way: the opcode table's 1-byte `nop`,
# not a flow opcode and not a DPTR construction. A 3-byte stand-in would not
# do -- `disasm8051.py` gives `0x75` a length of 3, so a fixture counting two
# bytes per filler would stop in the filler and every case would be about
# `0x75` instead.
NOP = bytes([0x00])
SITE = bytes([0x90, 0x07, 0xD0])      # mov dptr,#0x07D0 -- what a site is
READ = bytes([0xE0])                  # movx a,@dptr
WRITE = bytes([0xF0])                 # movx @dptr,a
RET = bytes([0x22])                   # ret -- a flow opcode

# Every construction `is_dptr_rebuild()` names, as bytes. The names are the
# disassembly's, not `mnemonic()`'s, and each case asserts the bytes rather
# than the rendering: the mnemonic table is disasm8051.py's subject, and a
# case that failed on a wording change would stop being evidence for a bounds
# or opcode defect.
DPL_FROM_A = bytes([0xF5, 0x82])      # mov 0x82,a
DPH_FROM_A = bytes([0xF5, 0x83])      # mov 0x83,a
DPL_FROM_R7 = bytes([0x8F, 0x82])     # mov 0x82,r7
DPTRH_FROM_R4 = bytes([0x8C, 0x83])   # mov 0x83,r4
DPH_IMM = bytes([0x75, 0x83, 0x03])   # mov 0x83,#0x03
DPTRH_POPPED = bytes([0xD0, 0x83])    # pop 0x83
DPH_FROM_P1 = bytes([0x85, 0x90, 0x83])  # mov 0x83,0x90 -- dst is d[i+2]

# What replaces nothing, and must not end a window.
SWAP_A = bytes([0xC4])                # swap a
XCH_DPL = bytes([0xC5, 0x82])         # xch a,0x82
READ_DPL = bytes([0xE5, 0x82])        # mov a,0x82
PUSH_DPL = bytes([0xC0, 0x82])        # push 0x82
# The in-place-modify forms, deliberately NOT terminators. See the module
# docstring of `is_dptr_rebuild()` and §3 of the write-up: they change the
# address, and the tool already treats `inc dptr` as a span walk rather than a
# terminator. Held here so a later widening of the guard to include them is a
# deliberate edit to this file rather than a silent one.
#
# `0x05` is `inc direct` at two bytes and the length table has it right.
# `0x54` does not: `OPCODE_LEN` gives the `0x54` group two bytes and
# `mnemonic()` renders `54 82` as `anl a,#0x82`, which is the accumulator form
# -- the 8051's `anl direct,#imm` is three. So the two-byte spelling below is
# what this tool decodes, and the three-byte direct form is asserted separately
# as a *predicate* answer only, where no length is involved. Fixing the table
# is out of scope here (it would change text other tools' committed output
# depends on); the point that matters for this file is that the guard keys on
# the opcode and the operand byte, so it is right on both spellings.
ANL_DPL = bytes([0x54, 0x82])         # anl a,#0x82 -- the two bytes the table decodes
ANL_DIRECT_DPL = bytes([0x54, 0x82, 0x7F])   # anl 0x82,#0x7f -- the 8051's form
INC_DPL = bytes([0x05, 0x82])         # inc 0x82

# walk()'s own default, named so a case says which budget it meant instead of
# relying on the signature's.
BUDGET = 8


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0.

    The same helper `test_trace_xdata_refs.py` and `test_walk_budget_census.py`
    each carry a copy of, and for the same reason: a case that pointed at the
    firmware would keep testing the same bytes only until the bytes around
    some address in the image changed.
    """
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def why(img, start=0, max_insns=BUDGET):
    return T.walk_why(img, start, max_insns)[1]


def access(img):
    return T.classify(T.walk_why(img, 0)[0])


class ConstructionTests(unittest.TestCase):
    """One case per construction, each with a `movx` behind it that the
    window must not reach.

    The negative half is inside each case rather than beside it: the same
    fixture is walked with the construction and with filler in its place, and
    only a stop that changes the token *and* the length *and* the `access`
    cell is the guard and not the budget or the buffer.
    """

    def _assert_rebuild_ends_the_walk(self, rebuild):
        with_rebuild = fixture(SITE, NOP, rebuild, READ, NOP, NOP, NOP, NOP)
        self.assertEqual(why(with_rebuild), T.RELOAD_END)
        # The site and the one filler, and not eight: the walk stops at the
        # rebuild, and the read behind it is never decoded. The rebuild
        # itself is *not* in the window -- the guard runs on the instruction
        # after the one just decoded, which is the same shape the pre-existing
        # `d[i] == MOV_DPTR` guard had, and the same reason `classify()`'s
        # `skip` is 1 for a reference site.
        self.assertEqual([at for at, _, _ in T.walk(with_rebuild, 0)], [0, 3])
        # And the `access` cell says so. `read x1` is the pre-fix reading of
        # this fixture, and it is the cell this work exists to correct.
        self.assertEqual(access(with_rebuild), "no movx found in the decoded window")
        # The same bytes with the construction replaced by filler run on to
        # the budget, which is what makes the token attributable to the
        # construction and not to the fixture's length.
        without = fixture(SITE, NOP, NOP, READ, NOP, NOP, NOP, NOP)
        self.assertEqual(why(without), T.budget_end(BUDGET))
        self.assertEqual(access(without), "read x1")
        self.assertEqual(len(T.walk(without, 0)), BUDGET)

    def test_mov_dpl_a_ends_the_walk(self):
        # Issue #517's first required case, and the form at 0xE372: `movx
        # @dptr,a ; anl a,#0x7f ; mov DPL,A ; mov DPH,#3 ; movx a,@dptr`
        # charged the second read to 0x1C02.
        self._assert_rebuild_ends_the_walk(DPL_FROM_A)

    def test_mov_dph_a_ends_the_walk(self):
        # The issue's other named case, and the DPH half of the same pair.
        self._assert_rebuild_ends_the_walk(DPH_FROM_A)

    def test_mov_dph_rn_ends_the_walk(self):
        # Issue #517's second required case. `mov 0x83,r4` / `mov 0x82,r3` is
        # the 0xE4AE shape: two register halves in a row, and the window must
        # end at the first of them.
        self._assert_rebuild_ends_the_walk(DPTRH_FROM_R4)

    def test_mov_dph_imm_ends_the_walk(self):
        # Three bytes, and the filler in `fixture()` is one, so a case that
        # stopped on a length rather than on the opcode would frame this
        # differently from the two-byte forms above.
        self._assert_rebuild_ends_the_walk(DPH_IMM)

    def test_pop_dph_ends_the_walk(self):
        # `pop 0x83` is in no list the tree carried before this one, and it
        # fires 25 times in the mapped image.
        self._assert_rebuild_ends_the_walk(DPTRH_POPPED)

    def test_mov_direct_direct_into_dph_ends_the_walk(self):
        # The form whose destination is `d[i+2]`, and therefore the one the
        # bounds case below exists for. `mov 0x83,0x90` is a write to DPH
        # taken from P1.
        self._assert_rebuild_ends_the_walk(DPH_FROM_P1)

    def test_the_rebuild_is_recognised_at_any_depth(self):
        # Every case above puts the construction third, where `i` is well
        # inside the buffer. A guard reading the operand at a fixed offset
        # from the *start* of the walk rather than from the instruction would
        # pass all of them and be wrong everywhere else, so the same three
        # bytes are driven at four depths and each one has to stop the walk.
        for filler in range(6):
            with self.subTest(filler=filler):
                img = fixture(SITE, NOP, *(NOP,) * filler, DPL_FROM_A, READ)
                self.assertEqual(why(img), T.RELOAD_END)
                self.assertEqual(access(img),
                                 "no movx found in the decoded window")

    def test_a_rebuild_at_the_walk_s_own_first_instruction_is_not_a_stop(self):
        # The negative half of the case above, and it is a property of the
        # loop rather than of this guard: the test runs on the instruction
        # *after* the one just decoded, so a walk that starts on a rebuild
        # decodes it and carries on. That is what a reference site needs --
        # `sites_for()` hands `walk_why()` a `MOV DPTR`, and `classify()`'s
        # `skip=1` is what accounts for it -- and a guard that fired on the
        # instruction at `i` instead of the one after would empty every
        # committed table. Asserted so a later edit to the guard's placement
        # goes red here rather than in a re-cut CSV.
        img = fixture(DPL_FROM_A, NOP, READ, NOP, NOP, NOP, NOP)
        self.assertEqual(why(img), T.budget_end(BUDGET))
        # `read x1` rather than nothing: `access()` uses `skip=1`, so the
        # rebuild this walk starts on is the instruction it does not count as
        # a direction. That is the site's own accounting, and it is why the
        # case above has to keep a `movx` behind its rebuild to be evidence
        # about the guard.
        self.assertEqual(access(img), "read x1")
        # And the rebuild is decoded rather than refused: it is the first
        # triple of the walk, not a gap in one.
        at, raw, _ = T.walk(img, 0)[0]
        self.assertEqual((at, raw), (0, DPL_FROM_A))


class NonConstructionTests(unittest.TestCase):
    """The instructions that touch or read DPTR without replacing it, which
    must not shorten a window.

    Each is asserted twice: that the walk runs past it to the budget, and --
    for the four that read or touch A -- that the instruction is not in
    `is_dptr_rebuild()`'s answer for these bytes. The second is the claim a
    reader checking the opcode table against the issue's list would make, and
    it is asserted against bytes rather than against the list, so it survives a
    re-wording of either.
    """

    def _assert_not_a_rebuild(self, insn):
        self.assertFalse(T.is_dptr_rebuild(insn, 0),
                         f"{insn.hex(' ')} is not a DPTR construction")
        img = fixture(SITE, NOP, insn, READ, NOP, NOP, NOP, NOP)
        self.assertEqual(why(img), T.budget_end(BUDGET))
        # The window still reaches the read, so the two assertions together
        # say the instruction is decoded *through* rather than merely
        # tolerated: a guard that broke on it would return RELOAD_END, and one
        # that treated it as a flow opcode would return FLOW_END.
        self.assertEqual(access(img), "read x1")
        self.assertEqual(len(T.walk(img, 0)), BUDGET)

    def test_swap_a_does_not_replace_dptr(self):
        # **0xC4 is not a DPTR instruction.** Issue #517 lists `swap` among the
        # DPTR-writing opcodes; there is no 8051 instruction that swaps DPTR,
        # and `0xC4` exchanges the nibbles of the accumulator. Adding it to
        # the guard would truncate windows on an instruction that changes
        # nothing. Asserted by name so the issue's list cannot be re-copied in.
        self._assert_not_a_rebuild(SWAP_A)
        self.assertNotIn(SWAP_A[0], T.DIRECT_STORE_OPS)
        self.assertNotEqual(SWAP_A[0], T.MOV_DIRECT_DIRECT)
        self.assertNotEqual(SWAP_A[0], T.MOV_DPTR)

    def test_xch_a_dpl_does_not_replace_dptr(self):
        # Also in the issue's list. It does write DPL -- with the old DPL's
        # partner in A -- so it is the honest edge of this file's subject, and
        # it is left out for the stated reason rather than by oversight. See
        # `is_dptr_rebuild()`'s docstring and §3 of the write-up.
        self._assert_not_a_rebuild(XCH_DPL)

    def test_mov_a_dpl_does_not_replace_dptr(self):
        # A read of the low byte. A guard that treated any `direct` operand
        # naming 0x82 as a rebuild would stop here.
        self._assert_not_a_rebuild(READ_DPL)

    def test_push_dpl_does_not_replace_dptr(self):
        self._assert_not_a_rebuild(PUSH_DPL)

    def test_the_in_place_modify_forms_are_not_rebuilds(self):
        # §3 of the write-up declines these, and the reason is a decision
        # rather than an oversight: they mask or increment the pointer that is
        # already there, which is the same treatment `inc dptr` (0xA3) already
        # gets as a span walk. Held here so that widening the guard to include
        # them is a deliberate edit to this file.
        for insn in (ANL_DPL, INC_DPL):
            with self.subTest(insn=insn.hex(" ")):
                self.assertFalse(T.is_dptr_rebuild(insn, 0))
                img = fixture(SITE, NOP, insn, READ, NOP, NOP, NOP, NOP)
                self.assertEqual(why(img), T.budget_end(BUDGET))
                self.assertEqual(access(img), "read x1")
        # The 8051's three-byte `anl direct,#imm`, which `OPCODE_LEN` frames
        # as two. The predicate keys on the opcode and `d[i+1]`, so it gives
        # the same answer on both spellings -- which is the whole argument for
        # a byte-keyed guard over a mnemonic-matching one, made concrete.
        self.assertFalse(T.is_dptr_rebuild(ANL_DIRECT_DPL, 0))

    def test_the_predicate_survives_a_mnemonic_that_misreports_the_operand(self):
        # The concrete case behind the byte-keying, and it is a real defect in
        # the tree rather than a hypothetical: `disasm8051.mnemonic()` renders
        # the `0x54`/`0x55`/`0x64`/`0x65` group as A-operand forms, so
        # `54 82` prints as `anl a,#0x82` and a guard written against the text
        # would be reasoning about the accumulator while the machine writes
        # DPL. Asserting the *rendering* is what makes this a test rather than
        # a note; fixing the table is out of scope and would move text other
        # tools' committed output depends on.
        from disasm8051 import mnemonic
        # The rendering says the accumulator; the bytes say DPL. Both are
        # asserted, because the defect is only visible where they disagree.
        self.assertEqual(mnemonic(ANL_DPL, 0), "anl  a,#0x82")
        self.assertNotIn("0x82", mnemonic(ANL_DPL, 0).replace("#0x82", ""))
        # And the guard consults the bytes, where the two forms differ.
        self.assertFalse(T.is_dptr_rebuild(ANL_DPL, 0))
        self.assertTrue(T.is_dptr_rebuild(DPL_FROM_A, 0))
        self.assertEqual(mnemonic(DPL_FROM_A, 0), "mov  0x82,a")


class BoundsTests(unittest.TestCase):
    """`is_dptr_rebuild()`'s own bounds check, and why it is not the caller's.

    `walk_why()` establishes `i + 2 < len(d)` immediately before asking, so
    `d[i+1]` and `d[i+2]` are in range there and the predicate's checks look
    like padding. They are not: the predicate is a public function that
    `walk_budget_census` calls on whatever bytes a hand-built fixture holds,
    and a three-byte instruction whose operand is one byte past the end is an
    `IndexError` there and nowhere else. `inline_arg_len()`'s comment
    documents the same shape of latent hole one guard away.
    """

    def test_a_truncated_two_byte_form_raises_nothing(self):
        # `0xF5` with no operand byte at all: the opcode is in range, `d[i+1]`
        # is not, and the answer is False because no operand is a fact about
        # the pointer either way.
        self.assertFalse(T.is_dptr_rebuild(bytes([0xF5]), 0))
        self.assertFalse(T.is_dptr_rebuild(bytes([0xD0]), 0))
        self.assertFalse(T.is_dptr_rebuild(bytes([0x88]), 0))

    def test_a_truncated_three_byte_form_raises_nothing(self):
        # The 0x85 case, and the one the `i + 2 < len(d)` guard exists for: the
        # destination is `d[i+2]`, and with the opcode and its source present
        # but not the destination there is nothing to read.
        self.assertFalse(T.is_dptr_rebuild(bytes([0x85, 0x90]), 0))
        # And the one that would be a false positive without the length test:
        # `85 90 82` truncated to two bytes leaves 0x90 as the *source*, and
        # a guard that read `d[i+1]` unconditionally would call that a write
        # to DPL. It is not -- the destination byte is the missing one.
        self.assertFalse(T.is_dptr_rebuild(bytes([0x85, 0x90]), 0))
        self.assertTrue(T.is_dptr_rebuild(bytes([0x85, 0x90, 0x82]), 0))

    def test_a_truncated_mov_dptr_imm16_still_counts(self):
        # The 3-byte form the guard already had, and the one case where a
        # short buffer does not make the answer False: `MOV DPTR,#imm16` names
        # no operand, so the opcode alone is the whole instruction's claim.
        # This is also why the predicate cannot be a single length test.
        self.assertTrue(T.is_dptr_rebuild(bytes([T.MOV_DPTR]), 0))

    def test_the_offset_argument_is_honoured(self):
        # A guard reading `d[0]` regardless of `i` would pass every case above
        # and be wrong here, which is the same shape as
        # `ConstructionTests.test_the_rebuild_is_recognised_at_either_offset`.
        self.assertFalse(T.is_dptr_rebuild(bytes([NOP[0], 0xF5, 0x82]), 0))
        self.assertTrue(T.is_dptr_rebuild(bytes([NOP[0], 0xF5, 0x82]), 1))


class TerminatorVocabularyTests(unittest.TestCase):
    """The decision not to add a sixth token, and the `RELOAD_END` cell.

    `opcode-len-bounds-census.md`'s reproducing snippet prints one name per
    guard, and `walk_why()` lifted those names in so the `--terminator-column`
    output and that snippet's tally are one measurement in two places. Widening
    the guard fires `RELOAD_END` more often; it does not make it a different
    event, and a sixth token would split one vocabulary in two -- the
    duplication the names exist to retire.
    """

    def test_the_vocabulary_is_still_five(self):
        self.assertEqual(len(T.TERMINATORS), 4)
        self.assertEqual(T.TERMINATORS,
                         (T.FLOW_END, T.RELOAD_END, T.BUFFER_END, T.SHORT_END))
        # Five counting `budget_end()`'s, which is a function of the budget
        # rather than a fifth string.
        self.assertEqual(len(T.TERMINATORS) + 1, 5)
        self.assertEqual(T.RELOAD_END, "DPTR reloaded")

    def test_every_construction_yields_the_same_token(self):
        # The load-bearing half of the case above: if a future change gave the
        # wider constructions their own token, the count would still be five
        # and this would catch it.
        for insn in (DPL_FROM_A, DPH_FROM_A, DPL_FROM_R7, DPTRH_FROM_R4,
                     DPH_IMM, DPTRH_POPPED, DPH_FROM_P1):
            with self.subTest(insn=insn.hex(" ")):
                img = fixture(SITE, NOP, insn, READ, NOP, NOP, NOP, NOP)
                token = why(img)
                self.assertEqual(token, T.RELOAD_END)
                self.assertIn(token, T.TERMINATORS)
                self.assertTrue(T.is_terminator(token))

    def test_the_mov_dptr_case_still_reads_the_same(self):
        # The pre-existing behaviour, so a guard that kept only the new
        # constructions would go red here rather than quietly changing what
        # `opcode-len-bounds-census.md`'s 119530 counted.
        self.assertEqual(why(fixture(SITE, NOP, SITE, NOP, NOP, NOP, NOP)),
                         T.RELOAD_END)


class CrossToolTests(unittest.TestCase):
    """`walk_budget_census` and `trace_xdata_refs` must answer one question
    the same way, over the whole opcode map.

    `DIRECT_STORE_OPCODES` was `(0xF5, 0x8F)` in `walk_budget_census.py` and
    is now `trace_xdata_refs.is_dptr_rebuild()`. That tuple covered
    `mov direct,a` and `mov direct,r7` and nothing else -- r0 to r6, `0x75`,
    `0x85` and `0xD0` were all invisible to the census's class-A diagnosis,
    which is the narrower copy of this same defect. A test that only exercised
    the forms both tools happen to cover would not have caught it; this one
    crosses every opcode with every operand byte that can appear in a `direct`
    position.
    """

    # The operand bytes a DPTR construction can name, plus one that is not
    # DPL or DPH. 0x00 is the fixture's filler byte, so a case that reached
    # the operand by walking rather than by indexing would be tested here too.
    OPERANDS = (0x82, 0x83, 0x00)

    def test_the_two_predicates_agree_over_every_opcode(self):
        checked = 0
        for op in range(0x100):
            for operand in self.OPERANDS:
                # The two- and three-byte forms, so `0x85`'s destination is
                # present rather than absent-by-accident.
                for insn in (bytes([op, operand]),
                             bytes([op, operand, operand])):
                    with self.subTest(insn=insn.hex(" ")):
                        self.assertEqual(
                            W.is_direct_dp_store(insn),
                            T.is_dptr_rebuild(insn, 0),
                            f"{insn.hex(' ')}: the census and the guard "
                            f"disagree about what rebuilds DPTR")
                    checked += 1
        # 256 opcodes x 3 operands x 2 lengths, so a sweep that stopped early
        # cannot pass this by returning nothing at all.
        self.assertEqual(checked, 256 * 3 * 2)

    def test_the_census_keeps_no_opcode_list_of_its_own(self):
        # The agreement above is structural -- `is_direct_dp_store()` is a
        # one-line delegation -- and a delegation is exactly what a later edit
        # would replace with a local tuple. Asserting the name is gone is the
        # part that catches that, and it is a shape rather than a count: a new
        # opcode list under a different name is not held, which is why the
        # sweep above rather than this case is the real gate.
        self.assertFalse(hasattr(W, "DIRECT_STORE_OPCODES"))
        # DPL and DPH are the 8051's, and they are imported rather than
        # re-declared, so a second spelling of either would be a second fact
        # about one architecture.
        self.assertEqual((W.DPL, W.DPH), (0x82, 0x83))
        self.assertIs(W.DPL, T.DPL)
        self.assertIs(W.DPH, T.DPH)

    def test_the_dptr_byte_helpers_name_the_byte_that_is_written(self):
        # `verdict_for()`'s A cell says which half of DPTR a store wrote, and
        # `raw[1]` is the destination for every form except `mov direct,direct`
        # -- whose destination is `raw[2]`. Reading the wrong operand would
        # name the half the instruction did not touch, in a cell that reads as
        # a finding.
        for raw, byte in ((DPL_FROM_A, 0x82), (DPH_FROM_A, 0x83),
                          (DPL_FROM_R7, 0x82), (DPTRH_FROM_R4, 0x83),
                          (DPH_FROM_P1, 0x83)):
            with self.subTest(insn=raw.hex(" ")):
                self.assertTrue(W.is_direct_dp_store(raw))
                self.assertEqual(W.dptr_store_byte(raw), byte)
        # The source byte of the 0x85 form is 0x90 (P1) and is not the answer.
        self.assertNotEqual(W.dptr_store_byte(DPH_FROM_P1), 0x90)


class AccessCellTests(unittest.TestCase):
    """The `access` cell, which is what a committed table actually carries.

    A window that ends on a rebuild leaves `classify()` with no `movx` in it,
    and the cell it writes is a refusal rather than an answer. That is the
    whole mechanism: the misfiled rows said `read x1, write x1` for a register
    whose only real access was the write, and they said it because a `movx`
    behind a pointer rebuild was in the window.
    """

    def test_a_window_cut_by_a_rebuild_says_so_rather_than_counting(self):
        # The 0xE372 shape, byte for byte: a write, a mask, a rebuild, and the
        # read that must not be attributed to the site.
        img = fixture(SITE, WRITE, ANL_DPL, DPL_FROM_A, DPH_IMM, READ)
        self.assertEqual(why(img), T.RELOAD_END)
        # The write before the rebuild is still counted -- the site *does* make
        # that access -- and the read after it is not.
        self.assertEqual(access(img), "write x1")

    def test_a_write_behind_a_rebuild_is_not_counted_either(self):
        # The same mechanism on the write side, which is the `0xE4AE` shape: a
        # site whose real access is one write, followed by a rebuild and a
        # second write to a pointer the site did not set.
        img = fixture(SITE, WRITE, DPTRH_FROM_R4, DPL_FROM_R7, WRITE)
        self.assertEqual(why(img), T.RELOAD_END)
        self.assertEqual(access(img), "write x1")

    def test_a_handoff_is_still_reported_as_a_handoff(self):
        # The guard sits between the flow check and the budget, so a window
        # that ends on a call has to keep saying so. `walk_flow_follow.py`
        # reads this cell and would otherwise be handed a rebuild it cannot
        # follow past.
        img = fixture(SITE, bytes([0x12, 0x90, 0xCB]), NOP, READ)
        self.assertEqual(why(img), T.FLOW_END)
        self.assertIn("direction unresolved", access(img))


if __name__ == '__main__':
    unittest.main()
