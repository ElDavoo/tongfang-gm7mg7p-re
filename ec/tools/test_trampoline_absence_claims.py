#!/usr/bin/env python3
"""Cases for the shape of an "is not present in this decompiled tree" claim.

Every annotation row that described the BL51 trampoline `0x1114` as absent from
the decompiled tree, and every row that said the same of `0x1100`, was wrong:
both are in `ec/decompiled/index.csv` with their `.asm` and `.c` committed
beside them. The rows now carry a dated correction instead, and this suite is
what keeps the class of error from coming back through a different row.

The rule is deliberately narrow and deliberately not about `0x1114`. It asks
one question of every comment: *if this row says an address is missing, is it
missing?* A claim that names an address the index does not list is still
allowed, because that is the ordinary case the phrase was written for -- the
error is asserting absence of something that is there, which reads as
settled fact to the next person and is exactly what CLAUDE.md's calibration
rule is about.

The negative case matters at least as much as the positive one. A check that
has never rejected anything is not a check, and one that fires on the very
sentence stating it is worse than none, so both directions are exercised
against committed files and against fixtures built here.
"""

import csv
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
FUNCTIONS_CSV = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
INDEX_CSV = os.path.join(REPO, "ec", "decompiled", "index.csv")

# The phrase as the rows wrote it, with the address it claims is missing.
ABSENCE = re.compile(
    r"0x([0-9A-Fa-f]{4})\s+is not present in this decompiled tree")

TRAMPOLINES = ("1114", "1100")


def indexed_addresses():
    """Every `(scope, addr)` the committed index lists."""
    out = set()
    with open(INDEX_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.add((row["program"], row["addr"].upper()))
    return out


def annotated_comments():
    """Every `(addr, comment)` in the annotations CSV."""
    with open(FUNCTIONS_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield row["addr"], row.get("comment") or ""


def absence_claims(comments):
    """`(owner, claimed_absent_addr)` for each absence claim in `comments`."""
    for owner, comment in comments:
        for match in ABSENCE.finditer(comment):
            yield owner, match.group(1).upper()


class TheCommittedTree(unittest.TestCase):
    def test_no_row_claims_absence_of_an_address_the_index_lists(self):
        listed = indexed_addresses()
        offenders = [
            (owner, addr) for owner, addr in absence_claims(annotated_comments())
            if ("common", addr) in listed
        ]
        self.assertEqual(offenders, [],
                         "rows asserting an indexed address is absent")

    def test_the_two_trampolines_are_indexed_with_both_listings(self):
        # The specific rows this came from, pinned positively: a correction
        # that survives because the address stays listed is the outcome, and
        # `index.csv` dropping it would silently make the old claim true
        # again without anything here failing.
        listed = indexed_addresses()
        for addr in TRAMPOLINES:
            self.assertIn(("common", addr), listed)
            for suffix in (".asm", ".c"):
                path = os.path.join(REPO, "ec", "decompiled", "common",
                                    addr + suffix)
                self.assertTrue(os.path.exists(path), path)

    def test_the_correction_survives_its_own_retracted_clause(self):
        # Each corrected row has to keep the wrong sentence AND carry the
        # correction; a row that quietly drops the clause is not a retraction
        # in the shape CLAUDE.md asks for, and one that drops the correction
        # is the error coming back.
        corrected = [
            (addr, comment) for addr, comment in annotated_comments()
            if "not present in this decompiled tree" in comment
        ]
        for addr, comment in corrected:
            for word in ("2026-10-03", "#1444"):
                self.assertIn(word, comment,
                              f"{addr} lost the {word} half of its correction")

    def test_a_row_that_makes_no_claim_is_not_caught_by_the_phrase(self):
        # A regex loose enough to match every mention of the tree would pass
        # the first case for the wrong reason, so the selectivity is checked
        # against a real row whose comment talks about the tree throughout and
        # asserts absence of nothing.
        comments = dict(annotated_comments())
        self.assertIn("0xA73F", comments)
        self.assertEqual(
            [addr for _owner, addr in absence_claims([("0xA73F",
                                                       comments["0xA73F"])])],
            [])


class TheRule(unittest.TestCase):
    """The check itself, on comments of our own."""

    @staticmethod
    def claims(comment):
        return [addr for _owner, addr in absence_claims([("x", comment)])]

    def test_it_recognises_the_phrase_and_the_address_it_names(self):
        self.assertEqual(
            self.claims("but 0x1114 is not present in this decompiled tree, so "
                        "what it does with DPTR is not decoded here."),
            ["1114"])

    def test_a_prose_use_of_the_words_is_not_a_claim(self):
        # The phrase describes the tree, and a row may say so without
        # asserting that any address is absent from it.
        self.assertEqual(self.claims("Nothing in this decompiled tree shows "
                                    "what 0x1666 does with the register "
                                    "value."), [])

    def test_a_broken_claim_is_rejected(self):
        listed = indexed_addresses()
        comment = "0x1114 is not present in this decompiled tree."
        claimed = self.claims(comment)
        self.assertEqual(claimed, ["1114"])
        self.assertIn(("common", "1114"), listed,
                      "the fixture stopped testing what it was written for")

    def test_a_claim_about_an_unindexed_address_still_reads_as_a_claim(self):
        # The rule is not "delete the phrase". An address nothing lists is
        # the ordinary case the phrase exists for, and the check has to leave
        # it alone or it would be a blanket ban rather than a correctness
        # check.
        self.assertEqual(self.claims("0xDEAD is not present in this "
                                    "decompiled tree."), ["DEAD"])


if __name__ == "__main__":
    unittest.main()