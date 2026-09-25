#!/usr/bin/env python3
"""Unit checks for citation_frames.py, the code/data frame test.

`call_graph.py --self-test` covers the guard end to end, through a fixture
whose listings and index rows are committed. This file covers the classifier
alone, on sentences taken from `ec/annotations/ghidra-functions.csv` and
truncated to the clause under test, because the two fail differently: a
fixture that is wrong about the *caller* is a fixture problem, and a lexicon
that is wrong about a *sentence* is a census problem, and the second one moves
counts nobody would notice move.

Every expectation here is a sentence the committed comments actually contain,
with the address that matters in it. The ones that matter most are the two
that a whole-sentence rule gets backwards: "calls to 0x110A, 0x158E, ..." is a
code list that a data veto over the sentence would throw away, and "reached by
8 of the 0x07D0 sites" is a data byte count that a code-verb search alone would
credit.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'citation_frames', HERE / 'citation_frames.py')
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)


def verdict(comment, addr=None):
    """The frame for one canonical-width mention in `comment`.

    `addr` picks which one when the sentence names several, which most of the
    committed sentences do; without it the sentence must name exactly one.
    """
    import re
    spans = list(re.finditer(r"0x[0-9A-F]{4}", comment))
    if addr is not None:
        spans = [m for m in spans if m.group(0)[2:] == addr]
    assert len(spans) == 1, (comment, addr, [m.group(0) for m in spans])
    frame = cf.classify(comment, spans[0])
    assert frame.verdict in cf.VERDICTS, frame
    return frame


class CodeFrames(unittest.TestCase):
    """A code frame is necessary, and the window is where it is looked for."""

    def test_a_verb_immediately_left_is_a_code_frame(self):
        self.assertEqual(verdict("it calls 0x07D0 and returns").verdict, cf.CODE)

    def test_the_listing_forms_are_code_frames_too(self):
        for text in ("Three bytes: lcall 0xD5E1 then ret",
                     "Three bytes: ljmp 0xE322, with nothing",
                     "One instruction: ajmp 0xE822"):
            self.assertEqual(verdict(text).verdict, cf.CODE, text)

    def test_a_tail_jump_is_a_code_frame(self):
        self.assertEqual(
            verdict("Anything else tail-jumps to 0x9A0D, and all").verdict,
            cf.CODE)

    def test_the_verb_that_governs_a_list_reaches_every_item_in_it(self):
        # bank1,0xF512 in the committed comments. "to" is a data marker, which
        # is the whole reason the window is walked rather than the sentence
        # scanned: 21 of these are real citations and a sentence-wide data
        # veto would drop all of them.
        text = ("The .c body (SP=0xC0, a write of 0x3F to XDATA 0x1001, then "
                "calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF) is not "
                "supported by these instructions")
        for addr in ("110A", "158E", "0F75", "1594", "00CF"):
            span = text.index("0x" + addr)
            self.assertEqual(
                cf.classify(text, (span, span + 6)).verdict, cf.CODE, addr)

    def test_a_list_introduced_across_a_dash_aside_is_still_a_list(self):
        # common,0x0556: "Between them it calls six routines -- 0x14C8, ..."
        text = "Between them it calls six routines -- 0x14C8, 0x012F, 0x018C"
        span = text.index("0x14C8")
        self.assertEqual(cf.classify(text, (span, span + 6)).verdict, cf.CODE)

    def test_the_verb_can_be_two_words_back_through_a_preposition(self):
        self.assertEqual(
            verdict("then branches to 0x451A when bit 7 of 0x0A57 is clear",
                    "451A").verdict, cf.CODE)


class DataFrames(unittest.TestCase):
    """A data frame is a veto, on either side of the mention."""

    def test_xdata_before_the_address(self):
        self.assertEqual(
            verdict("Stores the caller's byte at XDATA 0x07D0 and clears")
            .verdict, cf.DATA)

    def test_a_listing_operand_is_a_data_frame(self):
        self.assertEqual(
            verdict("One instruction: MOV DPTR,#0x08CE. There is no RET")
            .verdict, cf.DATA)

    def test_the_store_verb_is_a_data_frame(self):
        self.assertEqual(
            verdict("and copies 0x0A5A into 0x0096, then calls 0x05E8",
                    "0A5A").verdict, cf.DATA)

    def test_a_range_end_is_a_data_frame(self):
        self.assertEqual(
            verdict("writes 0x0F, 0x60, 0x00, 0x00, 0x00 to "
                    "XDATA 0x0A56-0x0A5A", "0A5A").verdict, cf.DATA)

    def test_the_word_after_the_address_vetoes_a_code_verb_to_its_left(self):
        # pd,0x347B: "reached by 8 of the 0x07D0 sites". The verb is a code
        # verb and the mention is still a byte count -- the PD image's own
        # 0x07D0 sites are handing their DPTR to the helper, not calling it.
        frame = verdict("Handoff helper reached by 8 of the 0x07D0 sites and")
        self.assertEqual(frame.verdict, cf.DATA)
        self.assertIn("sites", frame.reason)

    def test_a_bare_operand_is_a_data_frame(self):
        # bank1,0xD2A3: a 0x0064 divisor, canonical width, and a data value.
        self.assertEqual(
            verdict("them through helper 0xA5E6 (always called with a 0x0064 "
                    "divisor)", "0064").verdict, cf.DATA)

    def test_the_data_verb_closest_to_the_mention_wins(self):
        # common,0x018C: "The other arm calls 0x07D0, writes 1 to 0xAA". The
        # address is a call and the 0xAA is not, and the two are told apart by
        # which verb is nearest, not by the sentence containing both.
        text = "The other arm calls 0x07D0, writes 1 to 0xAA"
        span = text.index("0x07D0")
        self.assertEqual(cf.classify(text, (span, span + 6)).verdict, cf.CODE)


class Undecided(unittest.TestCase):
    """No frame in the window is its own answer, not a default."""

    def test_a_mention_with_no_verb_near_it_is_undecided(self):
        frame = verdict("The shared helper here is 0x5A43.")
        self.assertEqual(frame.verdict, cf.UNDECIDED)
        self.assertEqual(frame.reason, "no-frame-in-window")

    def test_a_read_is_a_data_frame_even_with_no_data_noun_near_it(self):
        # pd,0x0D085: "What address 0xD078 reads is not determined here."
        # Nothing in the window says XDATA and the address is a real function
        # row, so a guard that only knew the `XDATA` spelling would credit it.
        frame = verdict("What address 0xD078 reads is not determined here.")
        self.assertEqual(frame.verdict, cf.DATA)
        self.assertIn("address", frame.reason)

    def test_the_budget_is_one_word(self):
        # "runs a borrow chain over 0x08CD": the verb is two ordinary words
        # back and the address is XDATA. FILLER_BUDGET=1 is what keeps this
        # unsettled instead of letting the walk find "runs" and believe it.
        self.assertEqual(cf.FILLER_BUDGET, 1)
        self.assertEqual(
            verdict("multiplies it by 10 with MUL AB, and runs a borrow chain "
                    "over 0x08CD and then").verdict, cf.UNDECIDED)

    def test_widening_the_budget_would_credit_this_one_wrongly(self):
        # The reason the budget is 1, on one sentence: at 2 the same mention
        # reads as a call. Over the committed comments a budget of 2 credits
        # no new citation at all, so the constant is a measurement and not a
        # guess -- see docs/findings/citation-code-vs-data.md.
        text = ("multiplies it by 10 with MUL AB, and runs a borrow chain "
                "over 0x08CD and then")
        span = text.index("0x08CD")
        saved = cf.FILLER_BUDGET
        try:
            cf.FILLER_BUDGET = 2
            self.assertEqual(cf.classify(text, (span, span + 6)).verdict,
                             cf.CODE)
        finally:
            cf.FILLER_BUDGET = saved


class ProgramIdentity(unittest.TestCase):
    def test_a_pd_comment_cannot_cite_an_ec_row(self):
        for callee in ("common", "bank0", "bank1"):
            self.assertEqual(cf.program_reason("pd", callee),
                             "cross-program")

    def test_a_pd_comment_may_cite_its_own_program(self):
        self.assertEqual(cf.program_reason("pd", "pd"), "")

    def test_a_bank_comment_may_cite_a_common_row(self):
        # A common-area function is exported once and reached from both bank
        # programs, so this is legitimate and only the frame test may judge it.
        self.assertEqual(cf.program_reason("bank0", "common"), "")
        self.assertEqual(cf.program_reason("common", "common"), "")


class Reporting(unittest.TestCase):
    """The rejected population is rendered, not dropped."""

    def setUp(self):
        self.candidates = [
            cf.Candidate(("common", "07D0"), ("pd", "10BC"),
                         ("cross-program",)),
            cf.Candidate(("common", "07D0"), ("pd", "347B"),
                         ("data-noun:sites", "cross-program")),
            cf.Candidate(("common", "0A5A"), ("common", "018C"),
                         ("data-marker:xdata",)),
        ]

    def test_every_candidate_appears_in_the_rendering(self):
        lines = cf.rejected_rows(self.candidates)
        self.assertEqual(len(lines), len(self.candidates))
        for line in lines:
            self.assertRegex(line, r"^  (common|pd),\w{4} cited by "
                                 r"(common|pd|bank\d):\w{4} -- ")

    def test_the_callee_with_the_most_candidates_comes_first(self):
        lines = cf.rejected_rows(self.candidates)
        self.assertTrue(lines[0].startswith("  common,07D0 "))
        self.assertTrue(lines[-1].startswith("  common,0A5A "))

    def test_both_reasons_are_named_when_both_fired(self):
        line = [l for l in cf.rejected_rows(self.candidates)
                if "pd:347B" in l][0]
        self.assertIn("data-noun:sites+cross-program", line)

    def test_the_limit_caps_the_rendering_without_hiding_the_population(self):
        self.assertEqual(len(cf.rejected_rows(self.candidates, limit=1)), 1)

    def test_reason_counts_do_not_double_count_one_candidate(self):
        counts = cf.reason_counts(self.candidates)
        self.assertEqual(counts["cross-program"], 2)
        self.assertEqual(sum(counts.values()), 4)


if __name__ == '__main__':
    unittest.main()
