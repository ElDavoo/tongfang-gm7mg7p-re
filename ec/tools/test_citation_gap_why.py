#!/usr/bin/env python3
"""Unit checks for citation_gap_scan.py's `why` and `fall_through` columns, the
two that say *which* reading a row is rather than what its bytes decoded to.

`citation_gap_scan.py --self-test` holds these against the live population and
against a second `citations()` call, which is the claim that matters: the column
is the caller's partition, not a second reading of the prose. This file covers
the pieces on their own, because they fail differently from the census. A
`why_of()` that inverted the kept/rejected precedence would still leave the
live population dividing into three sets that summed to the pair count; only a
fixture where the same pair is *placed* in each partition in turn can tell which
way it reads. Same for `fall_through`: on the live population every pair it
marks is same-scope and adjacent, so dropping the scope from the comparison, or
reading only one of its two directions, changes nothing the census can see --
and a criterion that decided on the addresses alone would put the abutting
pairs whose junction is a `ret` or an `sjmp` in the same column as the genuine
ones, which the census cannot see either because it never asks the question.

The pairs are real committed listings rather than invented ones, because
`classify()` reads each citing row's `.asm` off disk to find where its window
starts -- a synthetic address would test the column arithmetic and not the path
that produces it.
"""
import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'citation_gap_scan', HERE / 'citation_gap_scan.py')
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)

# Loaded once here for the reason `test_citation_gap_scan.py` gives its own
# copy of this: the images are 192 KiB of the committed firmware, read from the
# cache `verify_reassembly` builds, and unittest's warning filters turn the
# reader's unclosed-file ResourceWarning on. Both suites pay it once between
# them and neither is in a position to fix it.
DECOMPILED = HERE.parent / 'decompiled'

_IMAGES = scan.G.load_images()

# Real (callee, citer) pairs, one per shape, chosen so each citing listing is a
# committed `.asm` in the tree. The two fall-through pairs are the two
# directions, and both are same-scope: `common,4A76`'s listing ends where
# `common,4A77` begins, and `bank0,B4A8`'s listing ends where `bank0,B5B2`
# begins. `bank0,B4A8` cited by `bank0,B5CC` is the same callee from a row it
# is not adjacent to, so the column can be asked both ways about one address.
KEPT_PAIR = (("bank0", "B4A8"), ("bank0", "B5CC"))
CROSS_PROGRAM = (("common", "0408"), ("pd", "34FB"))
FALLS_FORWARD = (("common", "4A77"), ("common", "4A76"))
FALLS_BACKWARD = (("bank0", "B4A8"), ("bank0", "B5B2"))
NOT_ADJACENT = (("bank0", "B4A8"), ("bank0", "B5CC"))
# The same two directions again, with a junction that *leaves* rather than
# falling through -- the shape a criterion reading only addresses gets wrong.
# Forward: `bank0,D5D4` ends at 0xD5DB where `bank0,D5DB` begins, in `sjmp`.
# Backward: `bank0,C26E` ends at 0xC278 where `bank0,C278` begins, in `ret`.
BLOCKED_FORWARD = (("bank0", "D5DB"), ("bank0", "D5D4"))
BLOCKED_BACKWARD = (("bank0", "C26E"), ("bank0", "C278"))


def fixture(kept=(), reasons=None, listing_kept=(), undecided=()):
    """A `Context` with the real index and edges but a chosen partition.

    Everything except the partition fields is the committed tree, because
    `classify()` resolves the window's transfers through the real `Index` and
    reads the real `.asm`; only the partition is being varied, and varying it
    away from the real one is what makes this a fixture rather than a rerun of
    the census.
    """
    ctx = scan.context()
    return ctx._replace(kept=set(kept), reasons=dict(reasons or {}),
                        listing_kept=set(listing_kept),
                        undecided=set(undecided))


def classify_one(ctx, pair):
    """The single row `classify()` produces for `pair`."""
    rows = scan.classify(ctx, images=_IMAGES, pairs=[pair])
    assert len(rows) == 1, "expected one row for one pair, got %d" % len(rows)
    return rows[0]


class WhyColumn(unittest.TestCase):
    """`why` is `"<partition>:<reason>"`, read off the caller's own answer and
    carrying nothing the caller did not decide."""

    def test_each_partition_reads_back_as_its_own_name(self):
        kept = classify_one(fixture(kept=[KEPT_PAIR]), KEPT_PAIR)
        refused = classify_one(
            fixture(reasons={CROSS_PROGRAM: ("cross-program",)}), CROSS_PROGRAM)
        settled_nothing = classify_one(fixture(undecided=[KEPT_PAIR]),
                                       KEPT_PAIR)
        self.assertEqual(kept["why"], "kept:code-frame")
        self.assertEqual(refused["why"], "rejected:cross-program")
        self.assertEqual(settled_nothing["why"], "undecided:undecided")

    def test_rejection_outranks_a_keep_for_the_same_pair(self):
        # The precedence is `citations()`'s own and this tool does not get a
        # vote: a pair it both credited and refused is refused, because a data
        # frame vetoes whatever a code frame says. A `why_of()` that tested
        # `kept` first would answer `kept:code-frame` here and the live
        # population would still divide into three sets that summed right.
        both = classify_one(
            fixture(kept=[CROSS_PROGRAM],
                    reasons={CROSS_PROGRAM: ("data-marker:dptr",)}),
            CROSS_PROGRAM)
        self.assertEqual(both["why"], "rejected:data-marker:dptr")

    def test_a_rejected_pair_shows_the_callers_first_reason_not_the_most_likely(self):
        # `citations()` concatenates the program veto ahead of the data
        # reasons, so `common,0408` cited by `pd,34FB` -- which carries both --
        # answers `cross-program` and not the data frame. That is the reading:
        # the mention names a *pd* address from a *common* row's number, and the
        # data frame is a second true thing about the same mention.
        both = classify_one(
            fixture(reasons={CROSS_PROGRAM: ("cross-program",
                                             "data-marker:dptr")}),
            CROSS_PROGRAM)
        self.assertEqual(both["why"], "rejected:cross-program")

    def test_the_two_keep_arms_are_distinguished_by_the_callers_own_set(self):
        # `listing_kept` is `citations()`'s fourth return: the subset kept by
        # the citing listing's bytes rather than by the comment's frame. Same
        # pair, same listing, one field changed, and the column follows it --
        # which is what stops `kept` being one undifferentiated bucket.
        row = classify_one(
            fixture(kept=[KEPT_PAIR], listing_kept=[KEPT_PAIR]), KEPT_PAIR)
        self.assertEqual(row["why"], "kept:listing-corroborated")

    def test_a_pair_the_caller_placed_nowhere_is_blank_rather_than_invented(self):
        # Not found by this method, never absent: `classify()` can be driven
        # over a pair `citations()` did not return, and answering `undecided`
        # for one would claim the frame settled nothing when it was never read.
        # The blank is what `--self-test` asserts is absent from every live row.
        self.assertEqual(scan.why_of(fixture(), KEPT_PAIR), "")
        self.assertEqual(classify_one(fixture(), KEPT_PAIR)["why"], "")
        # A rejected pair whose reasons tuple is empty is the same case one
        # step in: the partition is known, the reason is not.
        self.assertEqual(scan.why_of(
            fixture(reasons={CROSS_PROGRAM: ()}), CROSS_PROGRAM), "rejected:")

    def test_partition_of_is_the_half_before_the_colon(self):
        for why, partition in (("kept:code-frame", "kept"),
                               ("kept:listing-corroborated", "kept"),
                               ("undecided:undecided", "undecided"),
                               ("rejected:data-marker:dptr", "rejected")):
            self.assertEqual(scan.partition_of(why), partition)


class FallThroughColumn(unittest.TestCase):
    """A column rather than a fourth verdict, so the three still partition."""

    def test_the_citing_listing_ending_where_the_callees_begins_is_yes(self):
        row = classify_one(fixture(), FALLS_FORWARD)
        self.assertEqual(row["fall_through"], "yes")
        self.assertEqual(row["end"], "4A77")
        self.assertEqual(row["callee_addr"], row["end"])

    def test_the_callees_listing_ending_where_the_citing_row_begins_is_also_yes(self):
        # The direction issue #489 left open, and the one a verdict reading
        # only forward from the citing row cannot see: `pd 0x39E7`'s comment
        # names `0x39E6`, whose listing is one `mov R5,A` with no `ret` of its
        # own and runs into the citing row. Here `bank0,B4A8` is that callee
        # and `bank0,B5B2` the citing row. Same relation, the two rows swapped.
        row = classify_one(fixture(), FALLS_BACKWARD)
        self.assertEqual(row["fall_through"], "yes")
        self.assertEqual(
            scan.listing_end(DECOMPILED / 'bank0' / 'B4A8.asm'), 0xB5B2)

    def test_abutting_is_not_the_same_as_crossed_in_either_direction(self):
        # Both directions, with a junction that leaves. Reading only the
        # addresses calls each of these a fall-through, which is a confident
        # claim about the firmware's control flow that the committed listing
        # contradicts: `bank0,D5D4`'s last instruction is `sjmp 0xd607` and
        # `bank0,C26E`'s is `C277 ret`, so in neither case does control run into
        # the abutting row. `blocked` says exactly that, and keeps it apart from
        # the `no` that means the two rows do not abut at all.
        for pair, mnemonic in ((BLOCKED_FORWARD, "sjmp"),
                               (BLOCKED_BACKWARD, "ret")):
            row = classify_one(fixture(), pair)
            self.assertEqual(row["fall_through"], "blocked")
            # The adjacency itself still holds -- only the crossing is closed --
            # so the pair is not silently demoted to the `no` of a pair whose
            # two rows are nowhere near each other.
            self.assertEqual(scan.junction_mnemonic(scan.junction_of(
                row["citer_scope"], row["citer_addr"],
                (row["callee_scope"], row["callee_addr"]),
                int(row["end"], 16))), mnemonic)

    def test_a_conditional_branch_at_the_junction_still_falls_through(self):
        # `jc` reaches the next row when it is not taken, so an abutting pair
        # whose junction is one is a real `yes`. This is what keeps `blocked` a
        # claim about the instruction rather than a coarser restatement of
        # `no`: the two pairs are adjacent in the same way and differ only in
        # what sits on the boundary.
        row = classify_one(fixture(), FALLS_BACKWARD)
        self.assertEqual(row["fall_through"], "yes")
        self.assertEqual(scan.junction_mnemonic(scan.junction_of(
            row["citer_scope"], row["citer_addr"],
            (row["callee_scope"], row["callee_addr"]),
            int(row["end"], 16))), "jc")

    def test_the_junction_set_is_the_leaving_instructions_and_no_others(self):
        # `NO_FALL_THROUGH` is a list of mnemonic names, so what holds it is
        # that each name is one the committed decoder actually prints and that
        # the instructions it omits are the ones that can reach the next row.
        # Paired here rather than restated, because a set that drifted would
        # make both directions above pass for the wrong reason.
        for mnemonic in scan.NO_FALL_THROUGH:
            self.assertIn(mnemonic, {"ret", "reti", "sjmp", "ljmp", "ajmp",
                                     "jmp"})
        for mnemonic in ("jc", "jnc", "jz", "jnz", "jb", "jnb", "jbc", "cjne",
                         "djnz", "lcall", "acall", "mov", "nop"):
            self.assertNotIn(mnemonic, scan.NO_FALL_THROUGH)

    def test_an_empty_listing_blocks_nothing_and_an_absent_one_is_not_read(self):
        # `ends_with_transfer()` answers `False` for a listing with no
        # instructions: there is no last instruction to read, which is not the
        # same as having read one that leaves. Not-found-is-not-absent, one
        # step in from the blank the caller leaves for a file that is not there.
        with tempfile.NamedTemporaryFile("w", suffix=".asm") as handle:
            handle.write("; only a comment\n")
            handle.flush()
            self.assertFalse(scan.ends_with_transfer(handle.name))
            self.assertEqual(scan.junction_mnemonic(handle.name), "")

    def test_the_same_callee_from_a_row_it_is_not_adjacent_to_is_no(self):
        # One address, one column, both answers: `bank0,B4A8` is read here and
        # not there, and the difference is the citing row rather than anything
        # about the callee. A column that could only answer `yes` would be
        # saying the address is adjacent to everything.
        self.assertEqual(classify_one(fixture(), NOT_ADJACENT)["fall_through"],
                         "no")
        self.assertEqual(classify_one(fixture(), FALLS_BACKWARD)["fall_through"],
                         "yes")

    def test_a_callee_with_no_listing_on_disk_is_blank_rather_than_no(self):
        # `bank0,F0A1` is an index row with no `.asm` beside it, so there are
        # no bytes to read and the question is undecided rather than answered
        # either way. Not found by this method, never absent -- the same rule
        # `listing_end()`'s own None return follows. No pair in the live
        # population lands here, so the census cannot check it; `bank0,B5CC`
        # is a real citing row and is not adjacent to 0xF0A1, so scoring it
        # `no` would be a claim about bytes that were never read.
        row = classify_one(fixture(), (("bank0", "F0A1"), ("bank0", "B5CC")))
        self.assertEqual(row["fall_through"], "")
        self.assertFalse((DECOMPILED / 'bank0' / 'F0A1.asm').exists())
        self.assertIn(("bank0", "F0A1"), scan.context().index.by_scope_addr)

    def test_the_comparison_is_on_the_pair_not_on_the_address_alone(self):
        # `pd,34FB` ends where the next `pd` export, 0x3500, begins. Naming it
        # as a `pd` callee is the fall-through; naming the *same number* in
        # another scope is the cross-program collision the three #489 pairs
        # turned out to be, and reading it as a control-flow relation would
        # credit a data mention with an adjacent entry it does not have.
        #
        # The `bank0` callee is built rather than looked up: no index row sits
        # at 0x3500 in any scope but `pd`, so the shape this column has to get
        # right does not occur in the committed tree today. That is a gap in
        # the corpus, not permission to read a bare address as a scope --
        # `classify()` uses the callee only to compare transfer targets and to
        # look up inbound edges, so it does not need the row to exist.
        same_scope = classify_one(fixture(), (("pd", "3500"), ("pd", "34FB")))
        self.assertEqual(same_scope["fall_through"], "yes")
        self.assertEqual(same_scope["next"], "3500")
        other_scope = classify_one(fixture(), (("bank0", "3500"), ("pd", "34FB")))
        self.assertEqual(other_scope["fall_through"], "no")
        self.assertEqual(other_scope["callee_addr"], other_scope["next"])


class TableRoundTrip(unittest.TestCase):
    """The column survives `render()` -> `csv.DictReader` and is held by
    `--check`, which is the only reason a reader of the committed CSV can trust
    it over a value printed in a write-up."""

    def rows(self):
        return scan.classify(
            fixture(kept=[KEPT_PAIR],
                    reasons={CROSS_PROGRAM: ("cross-program",
                                             "data-marker:dptr")},
                    undecided=[FALLS_FORWARD]),
            images=_IMAGES,
            pairs=[KEPT_PAIR, CROSS_PROGRAM, FALLS_FORWARD])

    def test_why_and_fall_through_survive_the_round_trip(self):
        text = scan.render(self.rows())
        back = list(csv.DictReader(text.splitlines()))
        self.assertEqual(len(back), 3)
        self.assertEqual({(r["callee_scope"], r["callee_addr"]): r["why"]
                          for r in back},
                         {("bank0", "B4A8"): "kept:code-frame",
                          ("common", "0408"): "rejected:cross-program",
                          ("common", "4A77"): "undecided:undecided"})
        # One row is a fall-through and the other two are not, so the column is
        # per-pair rather than a property of the render. Two of the three are
        # `common` rows, so the check keys on the address rather than the scope.
        self.assertEqual({r["callee_addr"]: r["fall_through"] for r in back},
                         {"B4A8": "no", "0408": "no", "4A77": "yes"})
        self.assertEqual(text, scan.render(back))

    def test_check_rejects_a_table_whose_why_was_altered(self):
        text = scan.render(self.rows())
        rc, lines = scan.check_table(
            text.replace("kept:code-frame", "kept:listing-corroborated"), text)
        self.assertEqual(rc, 1)
        self.assertTrue(any("recomputed 'kept:code-frame'" in ln for ln in lines),
                        lines)


if __name__ == '__main__':
    unittest.main()