#!/usr/bin/env python3
"""`a8af_operand_role.py`'s contract: the block's reading is derived, not assumed.

Stands in for the checks on `ec/tools/a8af_operand_role.py`, the tool that
decides what `0xA8`-`0xAF` is from the committed listings alone. Its output is
what the write-up and the corrected `MCS51_LEN` rest on, so what needs pinning
is that each measurement *can come out the other way* -- a tool that has only
ever agreed with the answer it was built to reach is a tool that cannot fail.

So the cases below are built around fixtures constructed to contradict the
committed corpus: a block framed one byte on, a block whose operands are rare
opcodes rather than common addresses, a corpus with no block in it at all. The
last of those is the one that matters most for calibration -- "this scan found
nothing" has to come out as no reading at all, never as a reading that happens
to be the expected one.

The real corpus is exercised too, but only for *relations* that must hold for
the answer to mean anything -- the framing check has to agree with itself across
the neighbouring blocks, the adjacency count must not exceed the number of
sites that could produce it -- and never for a figure. A count of the committed
firmware is a property of that firmware and moves when a listing is seeded; a
case that pinned one would go red on a merge that taught the tool something
rather than broke it.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import a8af_operand_role as A


class TheFramingCheck(unittest.TestCase):
    """Whether the listings place the next instruction one byte on or two.

    The check that decides the length, and the one that has to be able to say
    "one". Both directions are here because a check that only ever recognises
    two-byte framing would answer the committed corpus correctly and a
    different firmware wrongly.
    """

    def test_a_one_byte_block_is_read_as_one_byte(self):
        # The fixture's block row is a single `a8` with an empty byte slot, and
        # the next row is at addr+1 -- which is what a one-byte reading of this
        # block predicts the corpus would look like. It has to come back as
        # one byte, or the committed corpus's 416-of-416 result means nothing.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            rows = A.corpus_by_fixture(tmp, A.FIXTURE_ONE_BYTE)
        starts, at_one, at_two = A.framing(rows)
        self.assertEqual((1, 1, 0), (starts, at_one, at_two))

    def test_a_two_byte_block_is_read_as_two_bytes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            rows = A.corpus_by_fixture(tmp, A.FIXTURE_TWO_BYTE)
        self.assertEqual((1, 0, 1), A.framing(rows))

    def test_the_verdict_follows_the_framing_and_not_a_default(self):
        # Two corpora, same tool, opposite answers. If verdict() returned
        # `MOV Rn,direct` for both then the committed corpus's answer would be
        # the tool's default rather than its conclusion.
        self.assertEqual(("XCH A,Rn", 1),
                         A.verdict(10, 10, 0, {0x82: 1}, {0x82: 99})[:2])
        self.assertEqual(("MOV Rn,direct", 2),
                         A.verdict(10, 0, 10, {0x82: 90}, {0x82: 1})[:2])

    def test_an_empty_corpus_names_no_reading(self):
        # The calibration case. Zero sites found is "not found by this method"
        # and must not resolve to whichever reading the corpus usually gives.
        name, length, why = A.verdict(0, 0, 0, {}, {})
        self.assertIsNone(name)
        self.assertIsNone(length)
        self.assertIn("not found by this method", why)

    def test_a_corpus_framed_at_neither_offset_names_no_reading(self):
        # Sites that exist but have no row at addr+1 *or* addr+2 are not
        # two-byte framing; they are a corpus that does not say. Reporting
        # them as agreement with the two-byte reading would be the overclaim.
        name, _length, why = A.verdict(5, 0, 0, {0x82: 5}, {0x82: 0})
        self.assertIsNone(name)
        self.assertIn("no framing evidence", why)


class TheOperandReading(unittest.TestCase):
    """Whether the operand byte is an address or an opcode."""

    def test_the_operand_column_is_not_mistaken_for_the_opcode_column(self):
        # The whole immediate reading rests on being able to tell these apart,
        # so the two counters are asserted to be genuinely different functions
        # of the corpus rather than one being a relabelling of the other.
        rows = [("common", 0x100, bytes([0xA8, 0x82])),
                ("common", 0x102, bytes([0x90, 0x00, 0x10]))]
        self.assertEqual({0x82: 1}, dict(A.operand_histogram(rows)))
        self.assertEqual({0xA8: 1, 0x90: 1}, dict(A.opcode_start_counts(rows)))

    def test_a_single_byte_instruction_has_no_operand_byte(self):
        # `0xC8` is `XCH A,Rn`: one byte, so there is no operand to histogram.
        # Counting a length check as if it had one would let the histogram
        # report a byte the instruction never had.
        rows = [("common", 0x200, bytes([0xC8]))]
        self.assertEqual({}, dict(A.operand_histogram(rows, 0xC8, 0xCF)))

    def test_the_control_excludes_opcodes_whose_byte_is_not_a_direct(self):
        # `0x12` is `lcall addr16`: `0xf0` there is the high byte of a code
        # address and says nothing about the SFR `B`. Counting it would make
        # the control for the address reading look better than it is, which is
        # the failure this tool is about.
        rows = [("common", 0x300, bytes([0x12, 0xF0, 0x00])),
                ("common", 0x303, bytes([0xF5, 0xF0]))]
        got = dict(A.direct_users(rows))
        self.assertNotIn((0x12, 0xF0), got)
        self.assertEqual(1, got[(0xF5, 0xF0)])

    def test_the_control_excludes_the_block_itself(self):
        # Otherwise the block's own sites would be counted as independent
        # evidence for the reading they are the evidence for.
        rows = [("common", 0x400, bytes([0xA8, 0x82])),
                ("common", 0x402, bytes([0xF5, 0x82]))]
        got = dict(A.direct_users(rows))
        self.assertEqual(1, got[(0xF5, 0x82)])
        self.assertNotIn((0xA8, 0x82), got)


class TheAdjacencyCheck(unittest.TestCase):
    """The DPL/DPH register-pair shape, and what it discriminates."""

    def test_a_consecutive_register_pair_is_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            rows = A.corpus_by_fixture(tmp, A.FIXTURE_DPLDPH)
        pairs = A.dpl_dph_adjacency(rows)
        self.assertEqual(1, len(pairs))
        self.assertEqual(0x1010, pairs[0][1])

    def test_non_consecutive_registers_are_not_counted(self):
        # The claim is about a *register pair*. Two block instructions naming
        # the two halves of DPTR into registers four apart is a different
        # shape, and counting it would inflate the number the write-up quotes.
        rows = [("common", 0x500, bytes([0xA8, 0x82])),
                ("common", 0x502, bytes([0xAC, 0x83]))]
        self.assertEqual([], A.dpl_dph_adjacency(rows))

    def test_either_half_may_come_first(self):
        # Both orders occur in the corpus. A check that only recognised one
        # would understate the shape by however many sites load DPH first, and
        # the direction is not something the reading predicts -- so requiring
        # DPL first would be reading the answer into the test.
        for first, second in ((0xA8, 0xA9), (0xA9, 0xA8)):
            rows = [("common", 0x600, bytes([first, 0x82])),
                    ("common", 0x602, bytes([second, 0x83]))]
            self.assertEqual(1, len(A.dpl_dph_adjacency(rows)),
                             "0x%02X then 0x%02X not counted" % (first, second))

    def test_an_adjacency_does_not_reach_across_a_program_boundary(self):
        # Addresses are per-program: 0xFFFF of one program is not the next
        # byte of another. Keying the neighbour lookup on address alone would
        # invent pairs at the seam.
        rows = [("common", 0x7FFE, bytes([0xA8, 0x82])),
                ("bank1", 0x8000, bytes([0xA9, 0x83]))]
        self.assertEqual([], A.dpl_dph_adjacency(rows))

    def test_a_block_site_is_not_matched_to_its_own_successor_in_another_block(self):
        # The neighbour has to be in this block too. A `mov r1,DPL` followed by
        # some unrelated `0xA9` in a *different* row of the map is not the
        # shape, and the block bounds are what say so.
        rows = [(("common", 0x700, bytes([0xA8, 0x82]))),
                ("common", 0x702, bytes([0xA9, 0x01]))]
        self.assertEqual([], A.dpl_dph_adjacency(rows))


class TheTablesItReportsOn(unittest.TestCase):
    """Relations between this tool's answer and the tables in the tree.

    Held as relations rather than as figures. A count of the committed listings
    is a property of the committed firmware and moves when a listing is seeded;
    a case holding one to a constant would fail on a merge that added
    knowledge, which is the failure mode CLAUDE.md's no-totals rule is about.
    What must hold is that the block's length in `OPCODE_LEN` and the reading
    this tool reaches agree -- if they ever stop agreeing, one of the two is
    wrong and the disagreement is the finding.
    """

    @classmethod
    def setUpClass(cls):
        cls.rows = A.load_corpus()

    def test_the_tables_agree_with_the_reading_on_every_block_row(self):
        name, length, _why = A.verdict(*A.framing(self.rows)[:1],
                                        *A.framing(self.rows)[1:],
                                        A.operand_histogram(self.rows),
                                        A.opcode_start_counts(self.rows))
        if name is None:
            self.skipTest("no block start in the committed corpus")
        self.assertEqual(2, length)
        self.assertEqual({length}, {A.D.OPCODE_LEN[op]
                                    for op in range(A.BLOCK[0], A.BLOCK[1] + 1)})

    def test_the_one_byte_control_block_is_actually_framed_one_byte(self):
        # If `0xC8`-`0xCF` ever stopped being framed one byte on, the framing
        # check would have lost its control and the block's result would be an
        # unfalsifiable reading. Stated as a relation -- more sites one byte on
        # than two -- rather than as a count.
        _starts, at_one, at_two = A.framing(self.rows, 0xC8, 0xCF)
        self.assertGreater(at_one, at_two)

    def test_the_block_has_more_two_byte_sites_than_one_byte_sites(self):
        starts, at_one, at_two = A.framing(self.rows)
        self.assertGreater(starts, 0)
        self.assertGreater(at_two, at_one)

    def test_adjacency_sites_are_a_subset_of_the_sites_that_could_produce_them(self):
        # Every adjacency needs two block sites, so the count can never exceed
        # the number of block starts. This is the invariant that a widening of
        # the adjacency window would break, and it is what a reader of the
        # write-up's number needs to be able to assume.
        starts, _one, _two = A.framing(self.rows)
        self.assertLessEqual(len(A.dpl_dph_adjacency(self.rows)), starts)


if __name__ == "__main__":
    unittest.main()