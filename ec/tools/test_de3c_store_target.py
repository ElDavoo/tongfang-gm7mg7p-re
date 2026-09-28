#!/usr/bin/env python3
"""The store at `bank1:0xDE96` writes the `0x1C04` byte to the address the
`0x0564:0x0563` pair spells, and the two halves of that claim are held here
separately because they are separate claims.

`r1r2_predecessor.py` answers the first half: at the `movx @DPTR,A` the
pointer is `XDATA 0x0564` in the high byte and `XDATA 0x0563` in the low one,
both last written inside the callee `bank1:0xB6DE` rather than by the caller.
`../docs/findings/de3c-1c04-to-0563.md` is the write-up, and
`../docs/findings/dptr-rebuild-walk-guard.md` §2 is the claim this work
retracts.

What is held here, and why each is a claim rather than a number:

- **The chain, on hand-built fixtures.** The same two instructions that make
  the real answer (`mov DPH,R2` / `mov DPL,R1` behind a `lcall`, a callee that
  writes both, and a `jc` on the call's carry) are laid down in a buffer this
  file owns, so the mechanism is tested rather than the bytes it happens to
  land on. Four fixtures, and the third is the one that matters: a callee
  that sets carry **without** going through the `jz`, on a path where `R2`
  *is* already defined. That is the case that would falsify the answer, and
  the walk has to reject it.
- **The carry argument is a prune, not an assumption.** The real run's report
  names `bank1:0xB726` and says why, and the inverted-guard fixture has to
  produce the disjunction instead of the single address. A tool that simply
  ignored carry would pass the first fixture and fail this one.
- **The address set, from the committed bytes.** The two CODE tables at
  `0xDD3C` and `0xDDBC` are read out of the image and the store's target set
  is derived from them, then asserted as a set: the contiguous run
  `0x0300`-`0x035F`, seven named outliers, and `0x0000` **absent**. The
  absence is the load-bearing half -- `0x0000` is what all twenty-five
  rejected indices give, and it is excluded by the same `jz` the answer's
  soundness rests on.
- **The blind spot, as a claim about the tools' population.**
  `trace_xdata_refs.py` over `0x0563`/`0x0564` reports no site at `0xDE96`,
  and that is what "a DPTR assembled from a register pair is not a
  `MOV DPTR,#imm16` site" means; a reader who took the four-row table as the
  whole story would think the store was accounted for elsewhere.
- **The retraction is still visible.** `dptr-rebuild-walk-guard.md` keeps its
  wrong sentence with a correction beside it, per CLAUDE.md's calibration
  rule, and a test that only checked the corrected text would pass on a
  silent edit -- which is the failure the rule exists to prevent.

No image is required for the fixtures, no hardware, no Windows and no Ghidra:
the house pattern, and the same reason `test_dptr_rebuild_guard.py` gives for
building its own buffers.
"""
import csv
import os
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import r1r2_predecessor as P        # noqa: E402  (needs the path set first)

FIRMWARE = REPO / "ec" / "firmware" / "GMxMGxx_11.800"
ANNOT = REPO / "ec" / "annotations"
DECOMPILED = REPO / "ec" / "decompiled"
WALK_GUARD = REPO / "docs" / "findings" / "dptr-rebuild-walk-guard.md"
THIS_WRITEUP = REPO / "docs" / "findings" / "de3c-1c04-to-0563.md"

# ---------------------------------------------------------------------------
# Fixtures. One buffer, two entry points, the file offset equal to the runtime
# address so an offset in a case reads as the address it is -- which is what
# `test_dptr_rebuild_guard.py` does for the same reason.
# ---------------------------------------------------------------------------

CALLER = 0x0000
CALLEE = 0x4000
SIZE = 0x5000

# `lcall 0x4000` ; `jc +9` over the block ; the store ; `mov A,#0xff` ;
# `mov DPTR,#0x1c00` ; `movx @DPTR,A` ; `ret`. The `jc` is the carry guard
# the whole answer turns on, so it is the second instruction here; the
# displacement is +9 because next PC 0x0005 + 9 = 0x000E, which is the byte
# *after* the store. Getting that wrong lands the target on the operand byte
# of `mov DPH,R2` and the walk stops there, which is what a case asserting the
# inverted guard found the hard way.
CALLER_BYTES = bytes([
    0x12, 0x40, 0x00,                    # 0x0000 lcall 0x4000
    0x40, 0x09,                          # 0x0003 jc 0x000E
    0x90, 0x1C, 0x04,                    # 0x0005 mov DPTR,#0x1C04
    0xE0,                                # 0x0008 movx A,@DPTR
    0x8A, 0x83,                          # 0x0009 mov DPH,R2
    0x89, 0x82,                          # 0x000B mov DPL,R1
    0xF0,                                # 0x000D movx @DPTR,A  <- the store
])
STORE = 0x000D
# The rest of the caller, after the store, so the routine is well formed.
CALLER_TAIL = bytes([0x74, 0xFF, 0x90, 0x1C, 0x00, 0xF0, 0x22])

# The callee: read 0x0563 into R1, read 0x0564, and either return carry clear
# with R2 set or fall into the carry-setting arm the `jz` selects.
CALLEE_HEAD = bytes([
    0x90, 0x05, 0x63,                    # 0x4000 mov DPTR,#0x0563
    0xE0,                                # 0x4003 movx A,@DPTR
    0xF9,                                # 0x4004 mov R1,A
    0x90, 0x05, 0x64,                    # 0x4005 mov DPTR,#0x0564
    0xE0,                                # 0x4008 movx A,@DPTR
    0x60, 0x1C,                          # 0x4009 jz 0x4027
    0xFA,                                # 0x400B mov R2,A
])
SETB_CY, RET = 0xD3, 0x22
CLR_CY = 0xC3
GUARDED = {                                   # the real shape
    0x400C: bytes([CLR_CY, RET]),             # carry clear, R2 defined
    0x400E: bytes([0x00] * 30),
    0x4027: bytes([SETB_CY, RET]),            # carry set, R2 undefined
    0x402E: bytes([0x00] * 2),
}
# **The falsifying shape.** A second exit that sets carry *without* going
# through the `jz`, on a path where `mov R2,A` has already run. Nothing about
# the pointer changes there, so an answer that ignored carry would report the
# same two addresses either way -- which is exactly why the carry has to be a
# prune the test can see rather than a property the reader has to trust.
FALSIFIED = {
    # `jnz +2` at 0x400C: next PC 0x400E + 2 = 0x4010, so both of the two
    # exits below are reached and neither is dead.
    0x400C: bytes([0x70, 0x02]),             # -> 0x4010
    0x400E: bytes([SETB_CY, RET]),           # carry set, R2 *defined*
    0x4010: bytes([CLR_CY, RET]),            # carry clear, R2 defined
    0x4027: bytes([SETB_CY, RET]),           # carry set, R2 undefined
}
# The same body with the caller's guard inverted, so the carry-*setting*
# returns are the ones that reach the store. The answer must then stop being
# a single address, because one of those returns never wrote R2.
INVERTED = {k: bytes(v) for k, v in FALSIFIED.items()}


def fixture(callee_body, caller_head=CALLER_BYTES) -> bytes:
    """A flat image with the caller at 0x0000 and the callee at 0x4000.

    The caller's tail is placed one byte past whatever `caller_head` ends on
    rather than at a fixed offset, so a case that hands in a different head
    (an inverted `jnc`, an unmodelled opcode in the middle) still lays the
    routine down whole instead of overwriting its own store.
    """
    img = bytearray(b"\x00" * SIZE)
    img[CALLER:CALLER + len(caller_head)] = caller_head
    tail_at = max(CALLER + len(caller_head), STORE + 1)
    img[tail_at:tail_at + len(CALLER_TAIL)] = CALLER_TAIL
    img[CALLEE:CALLEE + len(CALLEE_HEAD)] = CALLEE_HEAD
    for at, blob in sorted(callee_body.items()):
        img[at:at + len(blob)] = blob
    return bytes(img)


def walk(img, entries=(CALLER, CALLEE), at=STORE, wanted=(P.DPH, P.DPL)):
    return P.Walk(img, 0, SIZE, 0, "fixture", 20000).seed(entries).run(at, wanted)


def terminal(w, site, sym, depth=0):
    """The last address in `sym`'s definition chain -- the `movx` that read
    the pointer, or the instruction that set the register. The chain is
    followed, not the first link: the `mov DPH,R2` in the *caller* is where
    the question is asked, and the answer is where R2 came from."""
    found = w.defs.get((site, sym)) or []
    if depth > 8 or not found:
        return None
    dsite, kind, note = found[0]
    if kind == P.FROM and note:
        return terminal(w, dsite, note, depth + 1)
    return dsite


def values(img, **kw):
    return {sym: P._render(walk(img, **kw), STORE, sym)
            for sym in (P.DPH, P.DPL)}


def pruned_sites(img, **kw):
    w = walk(img, **kw)
    return sorted({w.addr(site) for site, _ in w.pruned})


class CalleeClobberOverTheCall(unittest.TestCase):
    """The mechanism, on bytes this file owns."""

    def test_r1_and_r2_come_from_the_callee_not_the_caller(self):
        got = values(fixture(GUARDED))
        self.assertEqual(got[P.DPH], "XDATA 0x0564")
        self.assertEqual(got[P.DPL], "XDATA 0x0563")

    def test_the_definitions_are_the_callees_two_writes(self):
        w = walk(fixture(GUARDED))
        # The caller's own `mov DPH,R2` / `mov DPL,R1` are where the question
        # is asked; the chain behind them is what has to land in the callee.
        self.assertEqual([w.addr(r[0]) for r in w.defs[(STORE, P.DPH)]], [0x0009])
        self.assertEqual([w.addr(r[0]) for r in w.defs[(STORE, P.DPL)]], [0x000B])
        # ... and each chain ends at the `movx` that read the XDATA byte.
        self.assertEqual(terminal(w, STORE, P.DPH), 0x4008)
        self.assertEqual(terminal(w, STORE, P.DPL), 0x4003)

    def test_the_caller_never_writes_the_registers_it_reads(self):
        # The point of the fixture: nothing between the entry and the store
        # mentions R1 or R2, so the answer can only have come from the call.
        img = fixture(GUARDED)
        for addr in range(CALLER, STORE + 1):
            self.assertNotIn(0xF9, img[addr:addr + 1],
                             "caller writes R1 at %04X" % addr)
            self.assertNotIn(0xFA, img[addr:addr + 1],
                             "caller writes R2 at %04X" % addr)

    def test_a_callee_that_survives_the_call_leaves_no_definition(self):
        # The same caller, a callee that touches neither register. The walk
        # must then say so rather than reach past the call into the caller's
        # own history, which is the claim `dptr-rebuild-walk-guard.md` §2
        # made before this work corrected it.
        body = {at: bytes(len(blob)) for at, blob in GUARDED.items()}
        got = values(fixture(body))
        self.assertEqual(set(got.values()),
                         {"not written on any path followed"})


class TheCarryGuardIsTheArgument(unittest.TestCase):
    """The negative that would falsify the answer, and the guard's removal."""

    def test_a_callee_that_sets_carry_without_the_jz_is_rejected(self):
        w = walk(fixture(FALSIFIED))
        # 0x400E sets carry on a path where R2 *is* defined. It is pruned, so
        # it contributes no definition and the answer stays one address.
        self.assertIn(0x400E, pruned_sites(fixture(FALSIFIED)))
        got = values(fixture(FALSIFIED))
        self.assertEqual(got[P.DPH], "XDATA 0x0564")
        self.assertEqual(got[P.DPL], "XDATA 0x0563")

    def test_the_prune_names_the_instruction_that_caused_it(self):
        w = walk(fixture(FALSIFIED))
        text = " ".join(t for _, t in w.pruned)
        self.assertIn("0x400E", text)
        self.assertIn("CY=0", text)

    def test_inverting_the_guard_makes_the_answer_a_disjunction(self):
        # `jnc` instead of `jc` at the call site: now the carry-*setting*
        # returns are the ones that reach the store, and the `jz` arm never
        # wrote R2. DPH has to stop being a single value. DPL does not, and
        # the asymmetry is the shape of the real routine: `mov R1,A` sits
        # *before* the `jz` and `mov R2,A` *after* it, so only the high byte
        # was ever conditional. An answer that treated the pair as one thing
        # would get this fixture wrong.
        img = fixture(INVERTED,
                      caller_head=bytes([0x12, 0x40, 0x00, 0x50, 0x09])
                      + CALLER_BYTES[5:])
        got = values(img)
        self.assertEqual(got[P.DPH],
                         "XDATA 0x0564 or " + P.UNWRITTEN_SOME)
        self.assertEqual(got[P.DPL], "XDATA 0x0563")

    def test_a_store_behind_an_unmodelled_opcode_is_reported_not_answered(self):
        # The safe direction: an opcode with no writer model stops the path and
        # says so, rather than the walk stepping over it and reporting a
        # definition that may not be the last one.
        head = bytes([0x12, 0x40, 0x00, 0x40, 0x05]) + bytes([0xA5, 0x00, 0x00])
        img = fixture(GUARDED, caller_head=head + CALLER_BYTES[8:])
        w = walk(img)
        self.assertTrue(any("no writer model for opcode 0xa5" in t
                            for _, t in w.unfollowed))
        # The limit, and not "nothing wrote it": the walk never reached the
        # instructions that would have said which.
        self.assertEqual(P._render(w, STORE, P.DPH), P.CUT_PATH)


class WriterTableIsKeyedOnBytes(unittest.TestCase):
    """`disasm8051.mnemonic()` renders the A-operand half of the
    `0x44`/`0x45`/`0x54`/`0x55`/`0x64`/`0x65` group and prints the direct
    half -- `0x43`/`0x53`/`0x63` -- as `db`. A writer table keyed on that text
    would be blind on the opcodes that write a direct byte, which is where
    DPTR is written from. The two spellings are held apart here."""

    def test_the_direct_and_accumulator_spellings_write_different_things(self):
        direct = bytes([0x53, 0x82, 0x0F, 0x00, 0x00, 0x00])   # anl 0x82,#0x0f
        acc = bytes([0x54, 0x82, 0x00, 0x00, 0x00, 0x00])      # anl a,#0x82
        self.assertIn(P.DPL, P.writers(direct, 0))
        self.assertNotIn(P.DPL, P.writers(acc, 0))
        self.assertIn(P.A, P.writers(acc, 0))

    def test_a_direct_write_of_dpl_has_no_value_this_walk_can_carry(self):
        got = P.writers(bytes([0x53, 0x82, 0x0F]), 0)
        self.assertEqual(got[P.DPL][0], P.UNKNOWN)

    def test_mov_dptr_is_the_only_const_form_of_a_pointer_write(self):
        got = P.writers(bytes([0x90, 0x1C, 0x04]), 0)
        self.assertEqual(got[P.DPH], (P.CONST, 0x1C))
        self.assertEqual(got[P.DPL], (P.CONST, 0x04))

    def test_jc_and_jnc_do_not_write_the_carry_they_branch_on(self):
        # Getting this wrong releases every condition at the branch that
        # created it, which is the mechanism the answer depends on. Held
        # because it was got wrong once: `cjne` and `djnz` do write carry and
        # `jc`/`jnc` do not, and the two sets are one line apart.
        for op in (0x40, 0x50, 0x60, 0x70, 0x80):
            self.assertEqual(P.writers(bytes([op, 0x05, 0x00]), 0), {},
                             "0x%02X must not write a tracked symbol" % op)
        for op in (0xB4, 0xB5, 0xD5):
            self.assertIn(P.CY, P.writers(bytes([op, 0x05, 0x00]), 0),
                          "0x%02X must write CY" % op)


@unittest.skipUnless(FIRMWARE.exists(), "firmware image not present")
class TheRealRoutine(unittest.TestCase):
    """`bank1:0xDE96`, from the committed bytes."""

    @classmethod
    def setUpClass(cls):
        cls.img = FIRMWARE.read_bytes()
        lo, hi, base = 0x10000, 0x18000, 0x8000
        cls.walk = P.Walk(cls.img, lo, hi, base, "bank1", 20000).seed()
        cls.at = lo + (0xDE96 - base)
        cls.walk.run(cls.at, (P.DPH, P.DPL))

    def value(self, sym):
        return P._render(self.walk, self.at, sym)

    def test_the_pointer_is_the_pair_the_callee_read(self):
        self.assertEqual(self.value(P.DPH), "XDATA 0x0564")
        self.assertEqual(self.value(P.DPL), "XDATA 0x0563")

    def test_both_chains_end_inside_the_callee(self):
        # `0xDE3C`'s own frame never writes R1 or R2, so a chain that ended
        # outside `0xB6DE` would mean the walk had reached past the call into
        # the caller's own history -- the reading this work retracts.
        lo, hi = 0x10000 + (0xB6DE - 0x8000), 0x10000 + (0xB728 - 0x8000)
        for sym in (P.DPH, P.DPL):
            end = terminal(self.walk, self.at, sym)
            self.assertIsNotNone(end, "no definition for %s" % sym)
            self.assertTrue(lo <= end < hi,
                            "0x%04X is outside the callee" % self.walk.addr(end))

    def test_the_carry_setting_return_is_pruned_and_says_why(self):
        pruned = {self.walk.addr(site): text
                  for site, text in self.walk.pruned}
        self.assertIn(0xB726, pruned)
        self.assertIn("CY=0", pruned[0xB726])

    def test_nothing_branch_reaches_the_store_but_the_fall_through(self):
        # The single-clobber argument needs `0xDE8E` to have no other way in,
        # or a path could reach the store without passing `0xB6DE` at all.
        self.assertEqual(sorted(self.walk.pred.get(self.at, ())), [self.at - 2])

    def test_a_pointer_assembled_from_registers_is_invisible_to_the_site_scan(self):
        # The blind spot, as a claim about `trace_xdata_refs.py`'s population:
        # over these two addresses it reports two sites each and none of them
        # is the store, so the four rows read as a complete account of the
        # accesses to `0x0563`/`0x0564` and are not.
        import subprocess
        out = subprocess.run(
            [sys.executable, str(HERE / "trace_xdata_refs.py"), str(FIRMWARE),
             "0x0563", "0x0564", "--csv"],
            capture_output=True, text=True, check=True).stdout
        rows = list(csv.DictReader(out.splitlines()))
        self.assertTrue(rows)
        self.assertNotIn("0xDE96", [r["runtime"] for r in rows])
        self.assertIn("0xB6DE", [r["runtime"] for r in rows])
        self.assertIn("0xDE64", [r["runtime"] for r in rows])

    def test_the_address_set_is_read_out_of_the_two_code_tables(self):
        # `0xDE5B` writes 0x0564 from the table at 0xDD3C and `0xDE64` writes
        # 0x0563 from the one at 0xDDBC, both indexed by `0x0561 & 0x7F`.
        hi, lo_ = 0xDD3C, 0xDDBC
        n = 128
        off = lambda rt: 0x10000 + (rt - 0x8000)          # noqa: E731
        high = self.img[off(hi):off(hi) + n]
        low = self.img[off(lo_):off(lo_) + n]
        targets = {(h << 8) | l for h, l in zip(high, low) if h != 0}
        self.assertEqual(
            targets,
            set(range(0x0300, 0x0360)) | {0x0398, 0x0399, 0x03B5, 0x03C0,
                                          0x0514, 0x09C9, 0x09CA})

    def test_the_rejected_indices_are_exactly_the_zero_page(self):
        # Every index the two `jz`/`jnz` guards reject is the one that would
        # make the store write XDATA 0x0000, so the carry argument is what
        # keeps the address out of the set rather than a coincidence.
        off = lambda rt: 0x10000 + (rt - 0x8000)          # noqa: E731
        high = self.img[off(0xDD3C):off(0xDD3C) + 128]
        low = self.img[off(0xDDBC):off(0xDDBC) + 128]
        rejected = [(h << 8) | l for h, l in zip(high, low) if h == 0]
        self.assertTrue(rejected)
        self.assertEqual(set(rejected), {0x0000})

    def test_two_of_the_targets_are_already_named_registers(self):
        # The pair's *addresses* and the pair's *values* are different
        # questions, and the write-up's §6 says so only because this holds:
        # none of 0x0563/0x0564/0x0561/0x054C/0x1C00/0x1C04/0x0490 has a
        # `registers.yaml` row, but two of the 103 addresses the store can
        # reach are already rows. Asserted as the claim -- "these two, and
        # the pair's names do not" -- rather than as a census of the file,
        # which is a value every added register moves.
        off = lambda rt: 0x10000 + (rt - 0x8000)          # noqa: E731
        high = self.img[off(0xDD3C):off(0xDD3C) + 128]
        low = self.img[off(0xDDBC):off(0xDDBC) + 128]
        targets = {(h << 8) | l for h, l in zip(high, low) if h != 0}
        self.assertIn(0x030E, targets)
        self.assertIn(0x030F, targets)
        text = (ANNOT / "registers.yaml").read_text(encoding="utf-8")
        self.assertIn("- name: SBS_CHARGING_VOLTAGE", text)
        # ... and the addresses the pair itself lives at stay uncharacterised,
        # which is the half a reader is likelier to over-read. Read off the
        # `addr` column, not the prose: a note mentioning 0x030E is not a row
        # for it, and `grep` over the file cannot tell the two apart.
        import yaml
        rows = yaml.safe_load(text)["registers"]
        covered = set()
        for row in rows:
            a = row["addr"]
            covered.update(a if isinstance(a, list) else [a])
        self.assertEqual(sorted(covered & {0x030E, 0x030F}), [0x030E, 0x030F])
        for addr in (0x0563, 0x0564, 0x0561, 0x054C, 0x1C00, 0x1C04, 0x0490):
            self.assertNotIn(addr, covered)


class TheRetractionIsStillVisible(unittest.TestCase):
    """CLAUDE.md's calibration rule: the wrong version stays, with a
    correction beside it. A test that only looked for the corrected text
    would pass on a silent edit, which is the failure the rule prevents."""

    def setUp(self):
        self.text = WALK_GUARD.read_text(encoding="utf-8")

    def test_the_original_claim_is_still_there(self):
        self.assertIn("whatever the caller *above* `0x8A04` left in those registers",
                      self.text)

    def test_a_correction_sits_beside_it(self):
        idx = self.text.index("whatever the caller *above* `0x8A04` left in those registers")
        window = self.text[idx:idx + 1200]
        self.assertRegex(window, r"CORRECTION\b")

    def test_section_7_no_longer_leaves_the_address_unestablished(self):
        seven = self.text[self.text.index("## 7."):self.text.index("## 8.")]
        self.assertIn("0x0563", seven)
        self.assertIn("0x0564", seven)

    def test_the_writeup_calibrates_the_two_open_questions(self):
        # Not a word-ban: "no register read back" is the disclaimer, not a
        # claim, and banning the phrase would ban the calibration. What is
        # held is that the section exists and names both things a reader would
        # otherwise assume were settled -- what the EC does with the byte, and
        # what `0x0561` held at the time -- because both need hardware.
        text = THIS_WRITEUP.read_text(encoding="utf-8")
        self.assertIn("What this does not establish", text)
        after = text[text.index("What this does not establish"):]
        self.assertIn("what the ec does with", after.lower())
        self.assertIn("0x0561", after)
        self.assertIn("no hardware", text.lower())


class TheCommittedShape(unittest.TestCase):
    """Shape claims about committed tables, not counts of them."""

    def test_the_one_recorded_transfer_into_de3c_is_the_tail_jump(self):
        rows = list(csv.DictReader(
            (ANNOT / "bank-call-targets.csv").open(encoding="utf-8")))
        into = [r for r in rows if r["target"] == "0xDE3C"]
        self.assertEqual([(r["runtime"], r["opcode"]) for r in into],
                         [("0xAC40", "ljmp")])

    def test_b6de_is_a_recorded_call_target_and_not_a_guessed_one(self):
        # The plan this work implements asked for the opposite -- that
        # `0xB6DE` is *not* among the recorded targets -- and the committed
        # table says it is, from exactly the `lcall` at `0xDE89` that this
        # work's answer turns on. The table is the evidence; the request is
        # recorded here as a disagreement rather than quietly dropped.
        rows = list(csv.DictReader(
            (ANNOT / "bank-call-targets.csv").open(encoding="utf-8")))
        into = [(r["runtime"], r["opcode"]) for r in rows if r["target"] == "0xB6DE"]
        self.assertEqual(into, [("0xDE89", "lcall")])

    def test_no_committed_listing_covers_the_8a04_frame(self):
        # `bank1,0x8A03` is a one-byte `ret` and nothing follows it, so the
        # frame the old walk read cannot be re-read from a committed file.
        # This is what makes "the walk above `0xAC36` is unrepeatable" a
        # checkable claim rather than an assertion.
        body = re.compile(r"^([0-9A-F]{4})\s+[0-9a-f]{2} ", re.M)
        covered = []
        for path in (DECOMPILED / "bank1").glob("*.asm"):
            for match in body.finditer(path.read_text(encoding="utf-8")):
                addr = int(match.group(1), 16)
                if 0x8A04 <= addr <= 0x8A22:
                    covered.append((path.name, addr))
        self.assertEqual(covered, [])

    def test_the_three_seeded_rows_cite_a_listing_that_exists(self):
        # Both spellings of the address are in the committed CSV and both are
        # in use, so a lookup normalises rather than assuming -- the same thing
        # build_ec_decompile.norm_addr() does to join the two.
        rows = {r["addr"].upper().replace("0X", ""): r
                for r in csv.DictReader(
                    (ANNOT / "ghidra-functions.csv").open(encoding="utf-8"))
                if r["scope"] == "bank1"}
        for addr in ("DE3C", "B6DE", "8F6B"):
            # The message names the one address rather than the whole table:
            # a dict of 600 rows in an assertion diff is unreadable, and the
            # table is not what is being claimed.
            self.assertTrue(rows.get(addr), "no bank1 row at %s" % addr)
            row = rows[addr]
            self.assertTrue(row["name"], "%s has no name" % addr)
            self.assertTrue(row["evidence"], "%s cites nothing" % addr)
            for path in row["evidence"].split(";"):
                self.assertTrue((REPO / path.strip()).exists(), path)
            self.assertEqual(row["basis"], "hand-decoded")

    def test_the_ac36_row_no_longer_says_de3c_is_undecoded(self):
        rows = list(csv.DictReader(
            (ANNOT / "ghidra-functions.csv").open(encoding="utf-8")))
        row = next(r for r in rows
                   if r["scope"] == "bank1"
                   and r["addr"].upper().replace("0X", "") == "AC36")
        self.assertNotIn("What 0xDE3C does is not decoded here", row["comment"])
        self.assertIn("0xDE3C", row["comment"])


if __name__ == "__main__":
    unittest.main()
