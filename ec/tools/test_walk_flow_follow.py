#!/usr/bin/env python3
"""Offline checks for walk_flow_follow.py and the `--follow-flow` mode of
register_ref_table.py: no hardware, and for the parts that would need a live
read nothing but the committed firmware.

The oracle is split in two on purpose. The three EC-side `none` cells
`../annotations/static-refs-audit.md` 5.3 hand-checked against `r2 -a 8051`
are asserted **from the committed image**, with the expected verdicts
transcribed by hand from that transcript, so the answers do not come from the
code under test. Everything else builds its own byte fixtures in the `common`
region, whose file offset equals its runtime address, so a case keeps testing
what it was written to test if the bytes around some address in the image
change.

What the fixtures are for is the part the image cannot show: that the
branch-taken arm is not walked, that a bound names itself, that a loop
terminates, and -- the load-bearing one -- that a site which already
classifies is not decoded again. A bug in any of those produces a confident
wrong cell rather than a crash, which is the failure mode worth pinning.
"""
import contextlib
import csv
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
# walk_flow_follow imports disasm8051 and trace_xdata_refs by bare module
# name, the way register_ref_table.py does, so the tool directory has to be on
# the path before they are loaded rather than after.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'walk_flow_follow', HERE / 'walk_flow_follow.py')
wff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wff)

import register_ref_table as rrt           # noqa: E402  (needs the path above)
import trace_xdata_refs as txr             # noqa: E402
from disasm8051 import FLOW_OPCODES, REL_OPCODES   # noqa: E402

FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# The bounds the fixtures are walked at, named so a case can change one
# without repeating the other's.
DEPTH = wff.MAX_DEPTH
INSNS = wff.MAX_INSNS


def fixture(*insns: bytes, size: int = 0x40) -> bytes:
    """A flat `common`-region image with `insns` laid down from offset 0."""
    img = bytearray(b"\x00" * size)
    at = 0
    for insn in insns:
        img[at:at + len(insn)] = insn
        at += len(insn)
    return bytes(img)


def follow(img, start=0x00, depth=DEPTH, insns=INSNS):
    return wff.follow_site(img, 0x0751, start, True, depth, insns)


# The access shapes, as the tool decodes them. Each starts with
# `mov dptr,#0x0751` because that is what makes a byte offset a *site*:
# sites_for() only reports one where the `mov dptr` is.
READ = bytes([0x90, 0x07, 0x51, 0xE0, 0x22])                      # ; movx a,@dptr ; ret
WRITE = bytes([0x90, 0x07, 0x51, 0xF0, 0x22])                     # ; movx @dptr,a ; ret
BOTHE = bytes([0x90, 0x07, 0x51, 0xE0, 0xF0, 0x22])                # ; read then write
MOVC = bytes([0x90, 0x07, 0x51, 0x93, 0x22])                      # ; movc a,@a+dptr ; ret
JMPD = bytes([0x90, 0x07, 0x51, 0x73, 0x22])                      # ; jmp @a+dptr ; ret
LCALL = bytes([0x90, 0x07, 0x51, 0x12, 0x81, 0x00])                # ; lcall 0x8100
# The 0x0A39C shape: the access is on the fall-through of a bit test.
FALLTHROUGH = bytes([0x90, 0x07, 0x51, 0x30, 0xE6, 0x06, 0xE0, 0xF0, 0x22])
# The 0x0E066 shape: the site's own window ends in an sjmp, and the load is one
# jump away, at 0x08.
SJMP = bytes([0x90, 0x07, 0x51, 0x80, 0x03, 0x00, 0x00, 0x00, 0xE0, 0x22])

# The six spellings of a conditional branch, each with a displacement chosen
# so the *taken* target skips the `movx ; ret` laid down at its fall-through.
# A table that listed only the two the image happens to use would pass the
# ground-truth cases and fail the rest of the family.
CONDITIONALS = (
    (b"\x30\xe6\x02", "jnb acc.6"),
    (b"\x70\x02", "jnz"),
    (b"\x40\x03", "jc"),
    (b"\x60\x03", "jz"),
    (b"\xb4\xa5\x02", "cjne a,#0xa5"),
    (b"\xd5\x82\x02", "djnz 0x82"),
)


class VocabularyTests(unittest.TestCase):
    """The two things a changed vocabulary would silently break.

    `NO_MOVX` is read off `classify()` rather than written out, and that only
    works while `classify()` says what this file assumes. And
    `continuation()` has to know what to do with every opcode `walk_why()` can
    stop at: an opcode it does not recognise stops the walk with a named
    reason, which is the safe direction, but it would be a silent one if no
    test said so.
    """

    def test_no_movx_is_classify_own_empty_window_verdict(self):
        # The fixture is built on its own line because
        # check_doc_figure_pins.py reads every int inside an asserting call as
        # a claim about a counted figure, and an opcode is not a figure.
        site = bytes(READ)
        self.assertEqual(wff.NO_MOVX, txr.classify([], skip=0))
        self.assertEqual(wff.NO_MOVX, txr.classify(txr.walk(site, 0)))

    def test_every_flow_opcode_either_continues_or_says_why(self):
        # Anything walk_why() can stop at gets an answer out of
        # continuation(): a next address, or a reason by name. The one that
        # would be a silent failure is the fall-through, and this drives the
        # decision function directly rather than through follow_site(),
        # because classify() answers a window that ends in a call, a tail jump
        # or `jmp @a+dptr` before continuation() is ever reached.
        for op in sorted(FLOW_OPCODES):
            raw = bytes([op] + [0x00] * (txr.OPCODE_LEN[op] - 1))
            nxt, why = wff.continuation(bytes(0x40), [(0, raw, "")], True)
            self.assertTrue(nxt is not None or why, f"0x{op:02X}")
            self.assertNotEqual(why, wff.END_UNFOLLOWED,
                                f"0x{op:02X} has no continuation")

    def test_a_window_classify_answers_is_not_re_decoded(self):
        # The other half of the same property, end to end: a site whose own
        # window already classifies comes back untouched whatever the branch
        # opcode after it was.
        for op in sorted(FLOW_OPCODES):
            img = fixture(bytes([0x90, 0x07, 0x51, 0xE0, op]),
                          bytes([0x00, 0x00, 0x00]), bytes([0xE0, 0x22]))
            res = follow(img)
            self.assertEqual(res.linear, "read x1", f"0x{op:02X}")
            self.assertEqual(res.via_cell, wff.VIA_SITE, f"0x{op:02X}")
            self.assertEqual(res.ends, [], f"0x{op:02X}")

    def test_the_bounds_name_the_number_that_produced_them(self):
        # A cell reading "budget exhausted" cannot be re-derived at another
        # bound; `budget_end()`'s argument is in the token for that reason.
        self.assertEqual(wff.depth_end(4), "max_depth (4) exhausted")
        self.assertEqual(txr.budget_end(8), "max_insns (8) exhausted")
        self.assertTrue(wff.is_cut("max_depth (4) exhausted"))
        self.assertTrue(wff.is_cut("max_insns (8) exhausted"))

    def test_a_ret_and_a_loop_are_not_cuts(self):
        # Both have been walked as far as they go: a return is the end of the
        # routine and a cycle comes back round. Calling either a cut would
        # understate what was read, the reason walk_branch_arms.py keeps
        # `loop` out of its own CUTS.
        self.assertFalse(wff.is_cut(wff.END_RET))
        self.assertFalse(wff.is_cut(wff.END_RETI))
        self.assertFalse(wff.is_cut("loop back to 0x0010"))

    def test_the_window_budget_is_read_off_walk_why_not_written_out(self):
        # The `linear` column is the cell the nine committed tables carry, so
        # the number has to be walk()'s own rather than a constant here.
        self.assertEqual(wff.WINDOW, txr.walk_why.__defaults__[0])


class ContinuationTests(unittest.TestCase):
    """`continuation()` on its own, over hand-built triples.

    Reached through `follow_site()`, three of its branches never fire: a
    window ending in a call, a tail jump or `jmp @a+dptr` is a DPTR handoff or
    a CODE pointer as far as `classify()` is concerned, so the site is
    bucketed before this gets a look. They are the decision function's whole
    answer set, though, and a change to `classify()` would start routing them
    here -- so they are driven directly rather than left uncovered.
    """

    def cont(self, *insns: bytes):
        img = fixture(*insns)
        triples = txr.walk_why(img, 0)[0]
        return wff.continuation(img, triples, True)

    def test_a_conditional_continues_at_its_fallthrough(self):
        nxt, via = self.cont(bytes([0x30, 0xE6, 0x06]))
        self.assertEqual(nxt, 3)
        self.assertEqual(via, "fall-through past jnb acc.6,+0x06 at 0x0000")

    def test_an_sjmp_continues_at_its_target(self):
        nxt, via = self.cont(bytes([0x80, 0x02]))
        self.assertEqual(nxt, 4)
        self.assertEqual(via, "sjmp target 0x0004")

    def test_an_ajmp_continues_at_its_paged_target(self):
        # The paged form takes its page from the address of the *next*
        # instruction, which is why the branch's own runtime address is what
        # goes in and not the site's.
        nxt, via = self.cont(bytes([0x01, 0x20]))
        self.assertEqual(nxt, 0x0020)
        self.assertEqual(via, "ajmp target 0x0020")

    def test_an_ljmp_continues_at_its_absolute_target(self):
        nxt, via = self.cont(bytes([0x02, 0x00, 0x30]))
        self.assertEqual(nxt, 0x0030)
        self.assertEqual(via, "ljmp target 0x0030")

    def test_a_call_is_refused_rather_than_continued(self):
        for raw in (bytes([0x12, 0x81, 0x00]), bytes([0x11, 0x20])):
            nxt, via = self.cont(raw)
            self.assertIsNone(nxt)
            self.assertEqual(via, wff.END_HANDOFF)

    def test_a_return_and_an_indirect_jump_end_the_walk(self):
        # Each shape is decoded on its own line first, for the reason
        # test_no_movx_is_classify_own_empty_window_verdict() gives: 0x22, 0x32
        # and 0x73 are 34, 50 and 115, and check_doc_figure_pins.py would read
        # all three as counted figures.
        ret = self.cont(bytes([0x22]))
        reti = self.cont(bytes([0x32]))
        indirect = self.cont(bytes([0x73]))
        self.assertEqual(ret, (None, wff.END_RET))
        self.assertEqual(reti, (None, wff.END_RETI))
        self.assertEqual(indirect, (None, wff.END_INDIRECT))

    def test_the_carry_flag_opcodes_are_in_neither_branch_table(self):
        # `clr c` (0xC3), `setb c` (0xD3) and the `clr`/`setb`/`cpl bit` forms
        # sit inside 0xB4-0xDF, and reading that range as the PC-relative
        # branches is a mistake this repository has already made once -- it
        # decoded the rest of a routine as garbage. disasm8051's table is asked
        # rather than a range written here, and this is what holds it there.
        for op in (0xB2, 0xC2, 0xC3, 0xD2, 0xD3):
            self.assertNotIn(op, REL_OPCODES, f"0x{op:02X}")
            self.assertNotIn(op, FLOW_OPCODES, f"0x{op:02X}")

    def test_a_carry_flag_opcode_in_a_window_does_not_stop_it(self):
        # The same trap through the whole path: `clr c ; jc ; ret` is three
        # instructions and one branch. A window that stopped on the `clr c`
        # would end there and never reach the `jc`, so the fall-through the
        # row reports names the `jc` at 0x04 and not the byte in front of it.
        res = follow(fixture(bytes([0x90, 0x07, 0x51, 0xC3, 0x40, 0x02,
                                    0x22, 0x00, 0xE0, 0x22])))
        self.assertEqual(res.linear, wff.NO_MOVX)
        self.assertEqual(res.via_cell, "fall-through past jc +0x02 at 0x0004")
        self.assertEqual(res.ends, [wff.END_RET])


class FallThroughTests(unittest.TestCase):
    """Continuing past a conditional onto its fall-through, and *not* taking
    the other arm. The second half is the issue's own hedge: a site resolved
    this way is a weaker claim than one resolved where it sits, and the
    branch-taken arm is walk_branch_arms.py's, not this tool's."""

    def test_a_bit_test_on_the_fallthrough_finds_the_movx(self):
        res = follow(fixture(FALLTHROUGH))
        self.assertEqual(res.linear, wff.NO_MOVX)
        self.assertEqual(res.followed, "read x1, write x1")
        self.assertEqual(res.via_cell, "fall-through past jnb acc.6,+0x06 at 0x0003")

    def test_the_taken_arm_is_not_walked(self):
        # The same bytes with the load only on the taken side. A tool that
        # followed both arms would report a read here, and would be making
        # walk_branch_arms.py's claim rather than this tool's.
        img = fixture(bytes([0x90, 0x07, 0x51, 0x30, 0xE6, 0x02, 0x22]),
                      bytes([0x00]), bytes([0xE0, 0x22]))
        res = follow(img)
        self.assertEqual(res.followed, wff.NO_MOVX)
        self.assertEqual(res.ends, [wff.END_RET])
        self.assertEqual([b[0] for b in res.blocks], [0, 6])

    def test_every_conditional_shape_takes_its_fallthrough(self):
        for insn, name in CONDITIONALS:
            img = fixture(bytes([0x90, 0x07, 0x51]) + insn, bytes([0xE0, 0x22]))
            res = follow(img)
            self.assertEqual(res.linear, wff.NO_MOVX, f"{name}")
            self.assertEqual(res.followed, "read x1", f"{name}")
            self.assertIn(name, res.via_cell)


class JumpTargetTests(unittest.TestCase):
    """An unconditional jump is followed and the walk resumes there."""

    def test_an_sjmp_target_is_followed(self):
        res = follow(fixture(SJMP))
        self.assertEqual(res.linear, wff.NO_MOVX)
        self.assertEqual(res.followed, "read x1")
        self.assertEqual(res.via_cell, "sjmp target 0x0008")
        self.assertEqual([b[0] for b in res.blocks], [0, 8])

    def test_a_target_outside_the_region_is_reported_not_followed(self):
        # An `sjmp` out of the `common` region, which ends at 0x7FFF. Nothing
        # in the bytes says which bank is mapped above that, so following the
        # target against a bank's bytes is a confident wrong answer and the row
        # has to say it could not be resolved instead. (The absolute forms
        # would say the same, but classify() answers a window ending in one
        # with a handoff before the target is ever computed -- which is why
        # this case is built with an `sjmp`.)
        img = bytearray(b"\x00" * 0x8000)
        img[0x7FF0:0x7FF3] = b"\x90\x07\x51"
        img[0x7FF3:0x7FF5] = b"\x80\x7f"          # sjmp +127 -> 0x8074
        res = wff.follow_site(bytes(img), 0x0751, 0x7FF0, True)
        self.assertEqual(res.linear, wff.NO_MOVX)
        # `via` names the transfers actually taken and this one was not, so the
        # failed target is in `ends` instead -- which is where a reader looks
        # for why a follow stopped.
        self.assertEqual(res.via_cell, wff.VIA_SITE)
        self.assertEqual(res.ends,
                         ["target 0x8074 is not reachable from region common"])
        self.assertTrue(wff.is_cut(res.ends[0]))

    def test_a_target_is_taken_from_the_decoded_stream_not_from_the_site(self):
        # The walk_branch_arms.py framing trap. The site is at 0x00 and the
        # `sjmp` at 0x04, one `nop` in; `80 25` from 0x04 lands on 0x2B, and
        # the same arithmetic from the site lands on 0x2A -- a `nop`, which
        # decodes cleanly and would report an unresolved walk rather than an
        # error.
        img = fixture(bytes([0x90, 0x07, 0x51, 0x00, 0x80, 0x25]),
                      bytes([0x00]) * (0x2B - 6), bytes([0xE0, 0x22]))
        res = follow(img)
        self.assertEqual(res.via_cell, "sjmp target 0x002B")
        self.assertEqual(res.followed, "read x1")


class BoundTests(unittest.TestCase):
    """Every bound has to stop the walk and name itself, and a path that
    cycles has to terminate without being walked twice."""

    def test_the_depth_limit_is_named_on_the_row(self):
        res = follow(fixture(SJMP), depth=0)
        self.assertEqual(res.followed, wff.NO_MOVX)
        self.assertEqual(res.ends, ["max_depth (0) exhausted"])
        self.assertTrue(wff.is_cut(res.ends[0]))
        self.assertEqual(res.via_cell, wff.VIA_SITE)

    def test_the_instruction_budget_is_named_on_the_row(self):
        # A fall-through that decodes without reaching a movx, at a budget too
        # small to see one. The token carries the number that produced it.
        img = fixture(bytes([0x90, 0x07, 0x51, 0x30, 0xE6, 0x08] + [0x00] * 6))
        res = follow(img, insns=2)
        self.assertEqual(res.followed, wff.NO_MOVX)
        self.assertEqual(res.ends, [txr.budget_end(2)])

    def test_a_budget_is_not_continued_past(self):
        # walk()'s window ending on its budget is not a branch, so the follow
        # stops rather than reading "the budget ran out" as "keep going" --
        # re-cutting the committed tables at a larger budget is
        # walk_budget_census.py's question and not this one's.
        res = follow(fixture(bytes([0x90, 0x07, 0x51] + [0x00] * 12)), insns=20)
        self.assertEqual(res.via_cell, wff.VIA_SITE)
        self.assertEqual(res.ends, [txr.budget_end(wff.WINDOW)])

    def test_a_dptr_reload_ends_the_walk_with_walk_why_own_token(self):
        # One event, one spelling: the reload is walk_why()'s reason and is
        # passed through rather than renamed here. The fall-through carries
        # `mov dptr,#0x0832` and two more instructions, and walk_why() stops
        # on the *next* `mov dptr` boundary after decoding it.
        img = fixture(bytes([0x90, 0x07, 0x51, 0x30, 0xE6, 0x02]),
                      bytes([0x00, 0x00, 0x00, 0x90, 0x08, 0x32, 0x22]))
        res = follow(img)
        self.assertEqual(res.via_cell, "fall-through past jnb acc.6,+0x02 at 0x0003")
        self.assertEqual(res.ends, [txr.RELOAD_END])

    def test_a_loop_terminates_and_is_not_walked_twice(self):
        # `80 fb` at 0x03 is an `sjmp -5`, back to the site itself. The anchor
        # counts as seen, so the walk stops on the first return rather than
        # decoding the same window twice.
        res = follow(fixture(bytes([0x90, 0x07, 0x51, 0x80, 0xFB])), depth=8)
        self.assertEqual(res.ends, ["loop back to 0x0000"])
        self.assertEqual(len(res.blocks), 1)
        self.assertFalse(wff.is_cut(res.ends[0]))


class StrengthTests(unittest.TestCase):
    """The issue's own hedge: a site resolved only by following a branch has
    to be distinguishable from one resolved at the site, and a site that was
    never re-decoded has to come back untouched."""

    def test_only_none_sites_are_re_decoded(self):
        # The structural half of "no static_refs* count moves": every other
        # bucket is classify() over the bytes walk() decoded, and this says so
        # for one site of every shape the classifier can return.
        cases = ((READ, "read x1"),
                 (WRITE, "write x1"),
                 (BOTHE, "read x1, write x1"),
                 (MOVC, "movc a,@a+dptr x1 -- CODE pointer, not an XDATA access"),
                 (LCALL, "DPTR handed to lcall 0x8100 -- direction unresolved here"))
        for img, want in cases:
            res = follow(fixture(img))
            self.assertEqual(res.linear, want)
            self.assertEqual(res.followed, want)
            self.assertEqual(res.via_cell, wff.VIA_SITE)
            self.assertEqual(res.ends, [])
            self.assertFalse(res.redecoded)

    def test_a_jmp_at_a_dptr_is_a_code_pointer_not_re_decoded(self):
        # classify() names `jmp @a+dptr` before continuation() ever sees it,
        # so the row comes back resolved at the site and untouched.
        res = follow(fixture(JMPD))
        self.assertIn("CODE pointer into a jump table", res.linear)
        self.assertEqual(res.followed, res.linear)
        self.assertEqual(res.via_cell, wff.VIA_SITE)
        self.assertFalse(res.redecoded)

    def test_via_reads_at_site_when_nothing_was_followed(self):
        # The two strengths differ in a column, so a downstream reader can
        # tell them apart without parsing the class label.
        self.assertEqual(follow(fixture(READ)).via_cell, wff.VIA_SITE)
        self.assertNotEqual(follow(fixture(SJMP)).via_cell, wff.VIA_SITE)

    def test_a_followed_verdict_is_a_separate_bucket_from_an_at_site_one(self):
        # A `read` at the site and a `read` reached past a branch are both
        # reads and are not the same claim, so register_ref_table.py gives
        # them different columns.
        at_site = rrt.bucket(follow(fixture(READ)).followed)
        followed = rrt.flow_bucket(follow(fixture(SJMP)).followed)
        self.assertEqual(at_site, "read")
        self.assertEqual(followed, rrt.FLOW_CLASSES[0][0])
        self.assertNotEqual(at_site, followed)

    def test_a_handoff_found_only_by_following_is_not_the_handoff_bucket(self):
        # flow_bucket() is deliberately not bucket(): the same verdict one
        # level down is a weaker claim, and merging the two columns would let
        # a reader treat them as equal.
        verdict = follow(fixture(bytes([0x90, 0x07, 0x51, 0x30, 0xE6, 0x02,
                                        0x12, 0x81, 0x00]))).followed
        self.assertEqual(rrt.bucket(verdict), rrt.HANDOFF)
        self.assertEqual(rrt.flow_bucket(verdict), rrt.FLOW_CLASSES[3][0])
        self.assertNotEqual(rrt.flow_bucket(verdict), rrt.HANDOFF)

    def test_an_unresolved_follow_stays_in_the_none_bucket(self):
        verdict = follow(fixture(bytes([0x90, 0x07, 0x51, 0x30, 0xE6, 0x02,
                                        0x22]))).followed
        self.assertEqual(verdict, wff.NO_MOVX)
        self.assertEqual(rrt.flow_bucket(verdict), rrt.NONE)


class GroundTruthTests(unittest.TestCase):
    """The three EC-side `none` cells, asserted from the committed image.

    The expected verdicts below are transcribed by hand from the
    `r2 -a 8051` transcripts in `../annotations/static-refs-audit.md` 5.3 and
    reproduced in `../../docs/findings/walk-flow-follow.md`, so the oracle is
    the disassembly and not this tool. Issue #40 calls these three the
    regression test, and they are the reason the tool exists.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = txr.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        cls.by_off = {}
        for addr in (0x043E, 0x0768, 0x07D0):
            for r in wff.follow_rows(cls.d, [addr], cls.pd):
                cls.by_off[r.off] = r

    def test_0x0a39c_reads_and_rewrites_on_the_fallthrough(self):
        # r2: `mov dptr,#0x0768 ; jnb acc.6,0xa3a8 ; movx a,@dptr ;
        # anl a,#0xfd ; movx @dptr,a`. The read-modify-write is on the
        # fall-through, and the `jnb` is at site+3, not site+4.
        res = self.by_off[0x0A39C]
        self.assertEqual(res.linear, wff.NO_MOVX)
        self.assertEqual(res.followed, "read x1, write x1")
        self.assertEqual(res.via_cell,
                         "fall-through past jnb acc.6,+0x06 at 0xA39F")

    def test_0x0a848_reads_and_rewrites_past_a_cjne(self):
        # r2: `mov dptr,#0x0768 ; cjne a,#0xa5,0xa854 ; movx a,@dptr ;
        # orl a,#0x10 ; movx @dptr,a`. The same shape behind a compare.
        res = self.by_off[0x0A848]
        self.assertEqual(res.followed, "read x1, write x1")
        self.assertEqual(res.via_cell,
                         "fall-through past cjne a,#0xa5,+0x06 at 0xA84B")

    def test_0x0e066_reads_at_the_sjmp_target(self):
        # r2 at 0xE091: `movx a,@dptr`, the one shared load a per-sensor DPTR
        # chain jumps to. The access is at the target, not in the window.
        res = self.by_off[0x0E066]
        self.assertEqual(res.followed, "read x1")
        self.assertEqual(res.via_cell, "sjmp target 0xE091")
        self.assertEqual([b[0] for b in res.blocks], [0xE066, 0xE091])

    def test_the_three_are_the_only_re_decoded_EC_side_sites(self):
        # static-refs-audit.md 5.3 names exactly three, and a fourth appearing
        # means the population moved under a committed table.
        ecside = sorted(f"0x{r.rt:04X}" for r in self.by_off.values()
                        if r.region != "pd-image" and r.redecoded)
        self.assertEqual(ecside, ["0xA39C", "0xA848", "0xE066"])

    def test_no_site_of_the_three_addresses_is_dropped(self):
        # walk_branch_arms.py's reconciliation, for this tool: the population
        # is what sites_for() found, and a site that vanished would make every
        # count above it look smaller than it is.
        for addr, want in ((0x043E, 15), (0x0768, 8), (0x07D0, 254)):
            self.assertEqual(len(wff.follow_rows(self.d, [addr], self.pd)), want)

    def test_the_committed_csv_holds_exactly_the_eleven_none_cells(self):
        # The measurement the write-up quotes, and the population issue #40
        # is about: 2 of 0x0768, 1 of 0x043E and 8 of 0x07D0.
        rows = [r for r in self.by_off.values() if r.redecoded]
        self.assertEqual(len(rows), 11)
        self.assertEqual(sum(1 for r in rows if r.resolved), 4)
        self.assertEqual(sum(1 for r in rows if not r.resolved), 7)


class RegisterRefTableTests(unittest.TestCase):
    """`--follow-flow` on the consuming tool: the flag is opt-in, its columns
    still partition the sites, and the reconciliation still fails loudly."""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(FIRMWARE).read_bytes()
        off, magic = txr.PD_MARKER
        cls.pd = cls.d[off:off + len(magic)] == magic
        import yaml
        with open(rrt.DEFAULT_YAML) as f:
            cls.regs = yaml.safe_load(f)["registers"]

    def rows(self, addr, follow_flow):
        return list(rrt.site_rows(self.d, addr, self.pd, 0, follow_flow))

    def rows_the_pre_flag_way(self, addr):
        """The rows, built the way the file was before the flag: walk() then
        bucket(classify()), with no follow and no via."""
        out = []
        for o in txr.sites_for(self.d, addr):
            insns = txr.walk(self.d, o)
            out.append((o, txr.region_of(o, self.pd)[0],
                        txr.runtime_addr(o, self.pd),
                        rrt.bucket(txr.classify(insns)), None, None,
                        " ; ".join(" ".join(mn.split())
                                   for _, _, mn in insns[1:]), None))
        return out

    def test_depth_0_without_the_flag_is_byte_identical(self):
        # The guard rail the issue asks for: the class set, and every site's
        # label and window, are what they were before the flag existed.
        self.assertEqual(rrt.classes_for(0), rrt.CLASSES)
        for addr in (0x043E, 0x0768, 0x07D0, 0x04A6, 0x07E2):
            self.assertEqual(self.rows(addr, False), self.rows_the_pre_flag_way(addr))
            for row in self.rows(addr, False):
                self.assertIsNone(row[7], "a via on a site that was not followed")

    def test_the_flow_columns_replace_the_none_column_in_place(self):
        classes = rrt.classes_for(0, True)
        labels = [label for label, _ in classes]
        # One column in, five out, at the same position -- so the columns after
        # it (`none` is last at depth 0) do not move either.
        self.assertEqual(len(labels), len(rrt.CLASSES) - 1 + len(rrt.FLOW_CLASSES))
        self.assertEqual(labels[-len(rrt.FLOW_CLASSES):],
                         [label for label, _ in rrt.FLOW_CLASSES])
        for label, _ in rrt.FLOW_CLASSES:
            self.assertIn(label, labels)

    def test_the_flow_columns_are_a_partition_of_the_none_sites(self):
        # If they were not, a site would fall between two of them and
        # reconcile() would report it -- which is the check below, asserted
        # directly here so a failure names the bucket rather than the tool.
        for addr in (0x043E, 0x0768, 0x07D0):
            for o, _, _, label, _, _, _, via in self.rows(addr, True):
                pre = rrt.bucket(txr.classify(txr.walk(self.d, o)))
                if pre == rrt.NONE:
                    self.assertIn(label,
                                  {l for l, _ in rrt.FLOW_CLASSES}, f"0x{o:05X}")
                    self.assertTrue(via)
                else:
                    self.assertEqual(label, pre, f"0x{o:05X} moved buckets")
                    self.assertIsNone(via)

    def test_the_buckets_still_sum_to_the_site_count(self):
        # The check the issue says must keep passing, over the whole file
        # rather than three addresses. It is what makes the new columns safe.
        classes = rrt.classes_for(0, True)
        for name, addr in rrt.addresses(self.regs):
            rows = self.rows(addr, True)
            total, main, pd, hist = rrt.row_for(self.d, addr, self.pd, rows)
            self.assertEqual(sum(hist.values()), total, f"{name} 0x{addr:04X}")
            self.assertEqual(main + pd, total, f"{name} 0x{addr:04X}")
            self.assertEqual(rrt.reconcile(name, addr, total, main, pd, hist,
                                           classes), 0)

    def reconcile(self, *args):
        """`reconcile()` with its stderr captured, and the message kept.

        The message is the point -- a check that fails without saying what is
        wrong is a check nobody can act on -- and capturing it keeps the four
        deliberate failures below out of the suite's own output."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            problems = rrt.reconcile(*args)
        return problems, err.getvalue()

    def test_reconcile_still_fails_loudly(self):
        # The check is only worth keeping while it is still loud. A dropped
        # site, an image split that does not add up and a class nothing buckets
        # all have to be failures -- the third is the one the new columns could
        # have introduced.
        problems, msg = self.reconcile("X", 0x0768, 8, 8, 0,
                                       {"no such bucket": 8}, rrt.CLASSES)
        self.assertEqual(problems, 1)
        self.assertIn("unbucketed class(es)", msg)
        # A dropped site trips the count *and* the split, so it reports twice.
        problems, msg = self.reconcile("X", 0x0768, 9, 8, 0,
                                       {rrt.NONE: 8}, rrt.CLASSES)
        self.assertEqual(problems, 2)
        self.assertIn("a site was dropped", msg)
        self.assertIn("do not add up to", msg)
        problems, _ = self.reconcile("X", 0x0768, 8, 7, 0,
                                     {rrt.NONE: 8}, rrt.CLASSES)
        self.assertEqual(problems, 1)
        self.assertEqual(self.reconcile("X", 0x0768, 8, 8, 0,
                                        {rrt.NONE: 8}, rrt.CLASSES)[0], 0)


class CliTests(unittest.TestCase):
    """`main()` over the committed image: the exit codes and the two
    refusals, which are the parts a caller can see."""

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, str(HERE / 'walk_flow_follow.py'),
             FIRMWARE, *args],
            capture_output=True, text=True, check=False)

    def test_check_reproduces_the_committed_csv(self):
        proc = self.run_tool('0x043E', '0x0768', '0x07D0', '--check')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("byte for byte", proc.stdout)

    def test_check_refuses_bounds_the_file_does_not_record(self):
        # A --check at a bound the committed rows do not carry would diff a
        # different measurement against them and report a difference that
        # says nothing. Refused rather than defaulted.
        proc = self.run_tool('0x043E', '0x0768', '0x07D0',
                             '--max-depth', '1', '--check')
        self.assertEqual(proc.returncode, 1)
        self.assertIn("records max_depth", proc.stderr)

    def test_check_on_a_doctored_table_is_red(self):
        # Well-formed, the right bounds, one cell changed: this has to be the
        # diff path rather than the refusal path, or --check would go green on
        # a census it never compared.
        with open(wff.FOLLOW_CSV, newline="") as f:
            rows = list(csv.reader(f))
        rows[1][6] = "sjmp target 0xDEAD"
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'doctored.csv'
            with open(bad, 'w', newline="") as f:
                csv.writer(f).writerows(rows)
            proc = self.run_tool('0x043E', '0x0768', '0x07D0', '--check', str(bad))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("0xDEAD", proc.stderr)

    def test_check_refuses_a_file_that_is_not_one_of_its_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'wrong.csv'
            bad.write_text("addr,file_offset\n0x0768,0x0A39C\n")
            proc = self.run_tool('0x043E', '0x0768', '0x07D0', '--check', str(bad))
            self.assertEqual(proc.returncode, 1)
            self.assertIn("max_depth", proc.stderr)

    def test_no_addresses_is_an_error_not_a_silent_empty_table(self):
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("at least one address", proc.stderr)

    def test_check_alone_takes_the_addresses_the_table_records(self):
        # The no-address error names --check as the way out of it, so --check
        # has to work without an address list rather than reject the very flag
        # it points at. Same re-decode, same result as spelling them out.
        alone = self.run_tool('--check')
        self.assertEqual(alone.returncode, 0, alone.stderr)
        spelled = self.run_tool('0x043E', '0x0768', '0x07D0', '--check')
        self.assertEqual(spelled.returncode, 0, spelled.stderr)
        self.assertEqual(alone.stdout, spelled.stdout)

    def test_check_refuses_a_partial_address_list(self):
        # The bounds are guarded by load_recorded(); the address set needs the
        # same guard, or a subset diffs a partial re-decode against the whole
        # table and the missing rows read as drift in the committed file.
        proc = self.run_tool('0x0768', '--check')
        self.assertEqual(proc.returncode, 1)
        self.assertIn("records 0x043E, 0x0768, 0x07D0", proc.stderr)
        # ...and the refusal names what the run actually asked for, so a
        # dropped address is visible rather than inferred.
        self.assertIn("asked for 0x0768", proc.stderr)

    def test_a_zero_depth_or_a_zero_budget_is_refused(self):
        self.assertEqual(self.run_tool('0x0768', '--max-insns', '0').returncode, 1)
        # A depth of 0 is a real question with a real answer -- follow nothing,
        # and name the bound on every row -- so it is not the same refusal.
        self.assertEqual(self.run_tool('0x0768', '--max-depth', '0').returncode, 0)

    def test_an_image_with_no_pd_marker_is_refused(self):
        # A buffer that is not this dump would give every region `unknown` and
        # a table that reads as a claim about the real one.
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / 'not-the-dump.bin'
            stub.write_bytes(bytes(0x30000))
            proc = subprocess.run(
                [sys.executable, str(HERE / 'walk_flow_follow.py'),
                 str(stub), '0x0768'],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("ITE8850-PD", proc.stderr)

    def test_the_human_output_carries_the_calibration_caveat(self):
        # A `none` cell this tool leaves alone is still "not found by this
        # method", and the sentence that says so has to be on the run that
        # prints the cell.
        proc = self.run_tool('0x07D0')
        self.assertEqual(proc.returncode, 0)
        self.assertIn("not found by this method", proc.stdout)
        self.assertIn("0x07B9", proc.stdout)
        self.assertIn("measured on", proc.stdout)


if __name__ == '__main__':
    unittest.main()
