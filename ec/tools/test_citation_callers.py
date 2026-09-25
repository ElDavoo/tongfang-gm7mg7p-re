#!/usr/bin/env python3
"""Unit checks for citation_callers.py, the question asked of a citing listing.

`call_graph.py --self-test` covers the gate end to end, on a committed fixture
whose listings and index rows both exist. This file covers the two predicates
alone, on listings written here as text, because the two fail differently: a
predicate that reads the byte column by fixed width finds nothing on a 1-byte
instruction's `-` pads and returns "not fill" for a fill listing, which is the
same answer it gives for a listing that genuinely is not fill. A guard whose
wrong answer is indistinguishable from its right one is the failure this file
exists to catch, so the `-` pad gets a case of its own.

Every listing here is a shape the committed tree has, quoted from it where the
shape is a real address. The all-`0xFF` one is `bank1/F512.asm`; the transfer
ones carry all four forms, because a `lcall`-only reader misses the paged pair
and `0x5A43` is third-most-called in the real census on 11 `ajmp` and zero
`lcall`.
"""
import importlib.util
import tempfile
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'citation_callers', HERE / 'citation_callers.py')
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


def listing(text):
    """A path holding `text`, so a predicate can be handed a real file."""
    handle = tempfile.NamedTemporaryFile('w', suffix='.asm', delete=False)
    with handle as f:
        f.write(text)
    return handle.name


class FillTest(unittest.TestCase):
    """An unbroken 0xFF run is the veto, and nothing weaker is."""

    def test_the_real_bank1_fill_listing_is_fill(self):
        # ec/decompiled/bank1/F512.asm, the shape seven bank1 comments hang off.
        self.assertTrue(cc.is_fill(
            HERE.parent / 'decompiled' / 'bank1' / 'F512.asm'))

    def test_the_one_byte_pad_is_read_by_position_and_not_by_width(self):
        # `ff - -` is a 1-byte instruction whose two absent slots are the single
        # character `-`. A `[0-9a-f-]{2}` column regex matches nothing on this
        # line, so a fill listing built from them reads as empty -- not fill, and
        # not a veto either, which is how the rule that is supposed to catch this
        # case loses it.
        self.assertTrue(cc.is_fill(listing(
            "F6A0     ff - -   mov      R7, A\n"
            "F6A1     ff - -   mov      R7, A\n")))

    def test_one_non_ff_byte_anywhere_makes_it_not_fill(self):
        # The `ret` is the case that matters: it is a five-token line, so a
        # reader that requires six tokens per instruction never sees it and
        # calls a function ending in `ret` a fill run.
        self.assertFalse(cc.is_fill(listing(
            "F6A0     ff - -   mov      R7, A\n"
            "F6A1     ff - -   mov      R7, A\n"
            "F6A2     22 - -   ret\n")))

    def test_a_two_byte_instruction_is_not_a_fill_run(self):
        # `90` is `mov DPTR,#imm16`: the first byte is not ff, so a listing that
        # merely *starts* in a fill region is not itself one.
        self.assertFalse(cc.is_fill(listing(
            "0070     90 10 01 mov      DPTR, #0x1001\n"
            "0073     ff - -   mov      R7, A\n")))

    def test_a_listing_with_no_instruction_line_is_not_fill(self):
        # Not found by this method, not absent. Calling a listing fill without
        # having read an instruction from it would refuse a citation on evidence
        # this module never gathered, and `is_fill` has to answer differently
        # from the case above, where it read the bytes and ruled the run out.
        #
        # No committed listing reaches this path -- all 2707 in `ec/decompiled`
        # parse to at least one instruction line -- so both inputs here are
        # synthetic and the case is the guard, not a measured population; the
        # census is in `docs/findings/citing-listing-evidence.md` §Re-deriving.
        # The near miss is the opposite shape and is real: 83 listings are made
        # up only of operand-less instructions, which `iter_instructions` reads
        # (a bare `ret` is five tokens) and `is_fill` rules out on their first
        # byte -- 78 `ret` (`22`), 26 `nop` (`00`), 3 `reti` (`32`) across their
        # lines, none of them `ff`. 62 of the 83 carry an annotation row, so
        # they are evaluated, not skipped.
        self.assertFalse(cc.is_fill(listing("; only a header, no code\n")))
        self.assertFalse(cc.is_fill(listing("")))

    def test_comment_and_blank_lines_are_not_instructions(self):
        # The `;` header of every committed listing carries a SHA-256, and a
        # header line that parsed as an instruction would end every run.
        self.assertTrue(cc.is_fill(listing(
            "; bank1 @ F6A0   unimplemented_ff_fill_f6a0   [named]\n"
            "\n"
            "F6A0     ff - -   mov      R7, A\n"
            "; Ghidra 12.1.3 disassembly, generated by build_ec_decompile.py\n")))

    def test_a_fill_run_carries_no_transfer_and_no_ret(self):
        # The consequence the veto rests on, asserted rather than assumed: every
        # transfer and branch opcode differs from `ff`, so an all-ff run is a
        # listing that cannot make a call. If a future opcode table grew a
        # transfer spelled `ff`, this is the case that notices.
        self.assertEqual(cc.transfer_targets(listing(
            "F6A0     ff - -   mov      R7, A\n"
            "F6A1     ff - -   mov      R7, A\n")), set())


class TransferTargets(unittest.TestCase):
    """The corroboration half: what transfers a listing actually carries."""

    def test_all_four_forms_are_read(self):
        # 0x5A43 is reached by 11 `ajmp` and zero `lcall` in the real census,
        # and 0x00CF by a single `ljmp`; a reader keyed on `lcall` calls all
        # three unreachable, and the first one loudly.
        targets = cc.transfer_targets(listing(
            "0EA2     12 e8 05 lcall    0x05e8\n"
            "0EA5     02 43 5a ljmp     0x5a43\n"
            "0EA8     01 43 5a ajmp     0x5a43\n"
            "0EAB     11 43 5a acall    0x5a43\n"))
        self.assertEqual(targets, {"05E8", "5A43"})

    def test_the_paged_forms_survive_the_dash_pad(self):
        # `01`/`11` are 2-byte, so their third byte slot is the single character
        # `-` -- the spelling every committed `ajmp` and `acall` site uses. The
        # operand is still token 5 because the byte region is a fixed 9 columns
        # wide, which is the whole reason a fixed-width *regex* over the columns
        # drops them.
        self.assertEqual(cc.transfer_targets(listing(
            "0EA2     01 43 -  ajmp     0x5a43\n"
            "0EA4     11 43 -  acall    0x5a43\n")), {"5A43"})

    def test_a_short_target_is_padded_to_four_digits(self):
        # `common,0x0064` is a real one-byte function and a comment's `0x64` is
        # overwhelmingly a data value; the listing side has no such ambiguity,
        # so a short operand is the same address written narrow.
        self.assertEqual(cc.transfer_targets(listing(
            "0070     12 64 00 lcall    0x64\n")), {"0064"})

    def test_an_operand_that_is_not_an_address_is_skipped(self):
        # A transfer to a register-relative or immediate target reaches no
        # function, and handing `norm_addr` a non-address would invent one.
        self.assertEqual(cc.transfer_targets(listing(
            "0070     12 81 00 lcall    ?\n"
            "0073     12 00 7f lcall    0x12g0\n")), set())

    def test_the_real_reset_entry_carries_the_three_calls_its_comment_names(self):
        # ec/decompiled/common/0070.asm:12-14 is the evidence the three
        # common,0F75/0x158E/0x1594 citations rest on, and the reason a
        # corroborated pair is settled from the listing rather than from the
        # sentence that names it.
        self.assertEqual(
            cc.transfer_targets(HERE.parent / 'decompiled' / 'common'
                                / '0070.asm'),
            {"110A", "158E", "0F75", "1594", "00CF", "0200"})


class GrammarOwnership(unittest.TestCase):
    """The two tools share one listing grammar, and this is what holds them to
    it -- a reader that came to disagree about which byte column a paged
    transfer puts its target in would corrupt the inbound graph and the citation
    gate in opposite directions at once."""

    def test_call_graph_parse_listing_agrees_token_for_token(self):
        import call_graph
        for path in (HERE.parent / 'decompiled' / 'common' / '0070.asm',
                     HERE.parent / 'decompiled' / 'bank0' / '0EA2.asm',
                     HERE.parent / 'decompiled' / 'bank1' / 'F512.asm'):
            self.assertEqual(list(call_graph.parse_listing(path)),
                             list(cc.transfers(path)), path.name)


if __name__ == '__main__':
    unittest.main()
