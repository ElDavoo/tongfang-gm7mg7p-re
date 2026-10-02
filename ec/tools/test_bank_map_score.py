#!/usr/bin/env python3
"""Checks for `bank_map_score.py`, over the committed image and a fixture.

`--self-test` holds the known answers and the refusals that make them worth
anything. This file adds what it cannot reach: a mapping that is *not* the one
`make_bank_image.py` builds from, so a tool that had quietly hardcoded the
committed answer would be caught here and nowhere else.

**That is the whole reason `testdata/bank-map-score/` exists.** Every assertion
against the committed image is satisfied by returning `0x08000` and `0x10000`,
so on its own it would pin nothing about how the answer is arrived at. The
fixture is a four-block image in which the two banks' targets land on live
bytes in the *third* and *fourth* blocks instead, with the fourth erased, so a
tool reading the bytes and a tool reciting the mapping disagree.

The fixture also carries the population's drop path as bytes rather than as a
synthetic row: its last CSV row claims bank 1's stub over an instruction that
is not `MOV DPTR`, which is the disagreement between the committed CSV and the
committed image that `population()` refuses to score.

Nothing here was observed on hardware; the fixture is hand-written and the
committed image is a committed file.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bank_map_score as bms

FIXTURE_DIR = os.path.join(HERE, "testdata", "bank-map-score")
FIXTURE_IMAGE = os.path.join(FIXTURE_DIR, "score-example-image.bin")
FIXTURE_CSV = os.path.join(FIXTURE_DIR, "score-example-targets.csv")


def load_fixture():
    with open(FIXTURE_IMAGE, "rb") as f:
        d = f.read()
    return d, bms.read_csv(FIXTURE_CSV)


class CommittedImage(unittest.TestCase):
    """The population and the ranking the write-up cites."""

    @classmethod
    def setUpClass(cls):
        with open(bms.FIRMWARE, "rb") as f:
            cls.d = f.read()
        cls.rows = bms.read_csv(bms.TARGETS_CSV)
        cls.pop, cls.dropped = bms.population(cls.d, cls.rows)
        cls.ranked = bms.score_banks(cls.d, cls.pop)

    def test_the_population_is_read_out_of_the_image_not_the_csv(self):
        # The runtime target is not a column. If the tool ever stopped reading
        # the two operand bytes and started taking the CSV's `target` -- which
        # names the *stub*, not the destination -- every target would come out
        # near 0x1100 and below the window base, which this holds.
        self.assertEqual(self.dropped, [])
        for bank, targets in self.pop.items():
            self.assertTrue(all(t >= bms.WINDOW_BASE for t in targets), bank)
            self.assertTrue(all(t >= 0x8000 for t in targets), bank)
        # Bank 0's lowest real target is 0x8031, so a population of stub
        # addresses could not produce it.
        self.assertEqual(min(self.pop[0]), 0x8031)

    def test_the_ranking_matches_the_offsets_make_bank_image_builds_from(self):
        self.assertEqual(self.ranked[0][0][1], 0x08000)
        self.assertEqual(self.ranked[1][0][1], 0x10000)
        self.assertEqual(self.ranked[0][0][0], (0, 0, 0))
        self.assertEqual(self.ranked[1][0][0], (0, 0, 0))

    def test_an_erased_block_is_the_worst_a_bank_can_be_pointed_at(self):
        # 0x18000 is 100% 0xFF, so every one of a bank's targets landing there
        # is a landing on erased flash. This is what stops the search from
        # having a trivially good answer in a gap.
        for bank, targets in self.pop.items():
            t = bms.tally(self.d, targets, 0x18000)
            self.assertEqual(t[bms.ERASED], len(targets), bank)

    def test_no_pair_may_name_one_block_twice(self):
        pairs = bms.score_pairs(self.d, self.pop, [0, 1])
        self.assertTrue(all(p[1] != p[2] for p in pairs))
        self.assertEqual((pairs[0][1], pairs[0][2]), (0x08000, 0x10000))

    def test_the_framing_walk_is_depth_sensitive_and_that_is_reported(self):
        # Bank 0's walk ranking moves with the limit: 0x08000 leads on the
        # short walks and 0x10000 on the long ones. A tool that hid this
        # behind one number would assert a ranking the data does not carry, so
        # the assertion is on the disagreement itself.
        def best(bank, limit):
            scored = [(bms.framing(self.d, self.pop[bank], base, limit)[1],
                       base) for base in bms.candidates(self.d)]
            return max(scored)[1]

        self.assertEqual(best(0, 8), 0x08000)
        self.assertEqual(best(0, 64), 0x10000)
        self.assertNotEqual(best(0, 8), best(0, 64))
        # The composite reads one byte and so cannot move with the limit. That
        # is the property the ranking rests on, and it is what makes the
        # framing columns diagnostic rather than load-bearing.
        for bank in (0, 1):
            winners = {base for btup, base in self.ranked[bank]
                       if btup == self.ranked[bank][0][0]}
            self.assertEqual(winners, {self.ranked[bank][0][1]}, bank)

    def test_the_chance_baseline_weakens_with_population_size(self):
        small = bms.chance_baseline(53)[1]
        large = bms.chance_baseline(350)[1]
        self.assertGreater(small, large)
        self.assertGreater(small, 0.1)


class Fixture(unittest.TestCase):
    """A mapping that is not the committed one, so the bytes have to be read."""

    @classmethod
    def setUpClass(cls):
        cls.d, cls.rows = load_fixture()
        cls.pop, cls.dropped = bms.population(cls.d, cls.rows)
        cls.ranked = bms.score_banks(cls.d, cls.pop)

    def test_the_row_without_a_mov_dptr_is_dropped_not_scored(self):
        # Six rows name a bank; five have `MOV DPTR` in front of them.
        # Scoring the sixth against bytes read from the wrong place is how a
        # target would be invented, so it is dropped and named.
        self.assertEqual(len(self.dropped), 1)
        self.assertEqual(self.dropped[0], 0x0250)
        self.assertEqual(sum(len(v) for v in self.pop.values()), 5)

    def test_the_tool_finds_the_offsets_the_fixture_bytes_name(self):
        # Bank 0's targets live in the block at 0x10000 and bank 1's in the
        # one at 0x18000 -- deliberately not the offsets the committed image
        # resolves to, so this is what a hardcoded answer fails and nothing
        # else is.
        self.assertEqual(self.ranked[0][0][1], 0x10000)
        self.assertEqual(self.ranked[1][0][1], 0x18000)
        self.assertNotIn(self.ranked[0][0][1], (0x08000,))
        self.assertNotIn(self.ranked[1][0][1], (0x10000,))

    def test_every_other_candidate_is_rejected_on_erased_landings(self):
        for bank in (0, 1):
            base = self.ranked[bank][0][1]
            self.assertEqual(bms.bad(bms.tally(self.d, self.pop[bank], base)),
                             (0, 0, 0))
            for _btup, other in self.ranked[bank][1:]:
                self.assertGreater(bms.bad(bms.tally(self.d, self.pop[bank],
                                                     other))[0], 0)

    def test_the_joint_search_still_forbids_a_shared_block_on_the_fixture(self):
        pairs = bms.score_pairs(self.d, self.pop, [0, 1])
        self.assertTrue(all(p[1] != p[2] for p in pairs))
        self.assertEqual((pairs[0][1], pairs[0][2]), (0x10000, 0x18000))

    def test_the_report_from_the_fixture_names_the_dropped_row(self):
        text = bms.report(self.d, self.pop, self.dropped, self.rows)
        self.assertIn("not scored", text)
        self.assertIn("`0x%05X`" % self.dropped[0], text)

    def test_no_report_asserts_a_confirmed_pair(self):
        for text in (bms.report(self.d, self.pop, self.dropped, self.rows),
                     self.committed_report()):
            for line in text.splitlines():
                if "confirmed" in line.lower():
                    self.assertTrue(line.startswith("- **No pair is confirmed."),
                                    line)

    @classmethod
    def committed_report(cls):
        with open(bms.FIRMWARE, "rb") as f:
            d = f.read()
        rows = bms.read_csv(bms.TARGETS_CSV)
        pop, dropped = bms.population(d, rows)
        return bms.report(d, pop, dropped, rows)


if __name__ == "__main__":
    unittest.main()