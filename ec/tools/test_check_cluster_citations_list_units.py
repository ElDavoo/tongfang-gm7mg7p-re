#!/usr/bin/env python3
"""Offline checks for `units()`'s list-item split, and for what it must not do.

A tight list -- consecutive items with no blank line between them -- has no
paragraph break for the walk to cut on, so before this split the whole list was
one unit and one cue word anywhere in it decided what every other item meant.
`gen_findings_index.py` renders every write-up title as such a list, so the
defect was reachable from any write-up: naming one
`cluster-citation-operand-exemption.md` moved the word `cluster` into the unit
and took `check_cluster_citations.py` from exit 0 to exit 1 on a tree whose
prose had not changed, with a dozen unrelated write-ups' addresses reported as
disagreements. `docs/findings/operand-bound-exemption-census.md` records the
reproduction; this suite is what keeps it fixed.

The split is a change to how the corpus is read, so the cases below are as much
about what it must **not** do as about what it does. A walk that stopped
separating items would put the corpus back; one that split too eagerly would
separate an address from the cluster id it belongs with, and that failure is
silent in the same direction -- a claim nothing checks reads exactly like a
claim that is not there.

**Both directions are pinned, and the second is the load-bearing one.**
`ASplitsTightItems` holds the unit boundary; `KeepsRealClaimsReachable` holds
that a genuine disagreement *inside* one item is still reported, and
`AWrappedItemStaysWhole` that the line joining a cluster id to its address
across a wrap is still read. A split that passes only the first class has
quietly stopped checking the corpus.

`test_check_cluster_citations.py` is not modified by this and nothing here
replaces its cases: `OneAttributionPerUnit` remains the control the write-up's
decision is measured against, and a suite that edited it would destroy the
measurement rather than extend it.

**No case asserts a count of the committed tree.** Every fixture is written
inline against a scratch census, so nothing here moves when a write-up lands.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'check_cluster_citations', HERE / 'check_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# A two-cluster census, written out rather than read from `ec/annotations/`, so
# a case fails for the reason it is about and not because the committed census
# was regenerated under it. `main-ec-003` holds `0x08A8`; `main-ec-002` does
# not, so an address attributed to `main-ec-002` is a real disagreement.
CLUSTERS = {"main-ec-003": {"0x08A8", "0x0460"},
            "main-ec-002": {"0x06C6"}}
COUNTS = {}
KNOWN = {"0x08A8", "0x06C6", "0x0460"}


def units_of(text):
    """The units `units()` reads, as text."""
    return [unit for _, unit in ccc.units(text)]


def cited(text):
    """(count, first address) the checker reports for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        problems, _, _ = ccc.check(path, CLUSTERS, COUNTS, KNOWN)
    finally:
        os.unlink(path)
    return len(problems), problems[0][3] if problems else None


def skipped(text):
    """The skip reasons the checker returns for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        _, _, reasons = ccc.check(path, CLUSTERS, COUNTS, KNOWN)
    finally:
        os.unlink(path)
    return reasons


class ASplitsTightItems(unittest.TestCase):
    """The unit boundary itself: one unit per item, whatever the list looks like.

    **The fixtures carry no trailing period, and that is load-bearing.**
    `TERMINATOR` splits a sentence from the next thing that starts like one, and
    `-` is in its lookahead, so a list whose items are full sentences was
    already being split before this rule existed. The rows
    `gen_findings_index.py` renders are *not* full sentences -- they are link,
    em dash, title, no full stop -- so there was no terminator to split on and
    the whole index was one unit. A fixture written as ordinary prose would
    pass against the unfixed walk, which is the mistake that made the first
    draft of this suite green on code it was supposed to be red against.
    """

    def test_a_tight_list_is_one_unit_per_item(self):
        # The index row shape, with the cue word in the first item only.
        # Joined, this is the defect: the first item's `main-ec-003` is held
        # against every address in the rest of the list.
        text = ('- [`a.md`](a.md) — a title naming `main-ec-003` in passing\n'
                '- [`b.md`](b.md) — a title with `0x06C6` in it\n'
                '- [`c.md`](c.md) — a title with `0x08A8` in it\n')
        units = units_of(text)
        self.assertEqual(len(units), 3)
        self.assertNotIn("main-ec-003",
                         " ".join(units[1:]),
                         "the first item's id reached a later item")

    def test_one_items_id_does_not_reach_a_later_items_address(self):
        # The defect as the checker saw it, end to end: `0x06C6` belongs to
        # `main-ec-002`, so under a joined unit it is reported against the
        # `main-ec-003` the list named once, for a tree that never said so.
        text = ('- [`a.md`](a.md) — a title naming `main-ec-003` in passing\n'
                '- [`b.md`](b.md) — a title with `0x06C6` in it\n')
        self.assertEqual(cited(text), (0, None))

    def test_a_sentinel_title_cannot_colour_the_whole_list(self):
        # The landmine itself: one item carrying a membership cue, the rest
        # naming clusters they say nothing about. Under the joined unit every
        # address in the list is held to the one cluster that item named, and
        # the run goes red on prose nobody wrote.
        text = ('- [`a.md`](a.md) — a `main-ec-003` cluster of interest\n'
                '- [`b.md`](b.md) — `0x06C6` and `0x08A8` and `0x0460` here\n')
        self.assertEqual(cited(text), (0, None))

    def test_a_continuation_line_stays_with_its_item(self):
        # A wrapped item is one item. Splitting on the marker rather than
        # between items would put `0x08A8` in a unit of its own with no
        # cluster beside it, and the claim would stop being checked -- which is
        # the same as not checking it, and is why this is a case and not a note.
        text = ('- The `0x08A8` listing is a member of\n'
                '  `main-ec-003` and nothing else\n'
                '- A separate item naming no cluster\n')
        units = units_of(text)
        self.assertEqual(len(units), 2)
        self.assertIn("0x08A8", units[0])
        self.assertIn("main-ec-003", units[0])
        self.assertEqual(cited(text), (0, None))

    def test_an_ordered_list_is_one_unit_per_item(self):
        text = ('1. A note about `main-ec-003`, with no address\n'
                '2. The `0x06C6` listing is separate\n')
        self.assertEqual(cited(text), (0, None))

    def test_a_nested_item_is_its_own_unit(self):
        # Indented items are items too; joined, the outer item's id would reach
        # the inner one's address.
        text = ('- An outer item naming `main-ec-003`\n'
                '  - An inner item carrying `0x06C6`\n')
        self.assertEqual(cited(text), (0, None))

    def test_a_list_after_prose_keeps_the_prose_as_its_own_unit(self):
        # No blank line between them, so this is the `buf`-is-non-empty branch.
        # The prose carries no cluster, so the case turns on the boundary rather
        # than on a disagreement.
        text = ('A sentence about nothing in particular\n'
                '- An item naming `main-ec-003`\n'
                '- An item carrying `0x08A8`\n')
        units = units_of(text)
        self.assertEqual(len(units), 3)
        self.assertNotIn("main-ec-003", units[0])


class KeepsRealClaimsReachable(unittest.TestCase):
    """The other direction, and the one a too-eager split would fail."""

    def test_real_drift_inside_one_item_is_still_reported(self):
        # The whole point of the walk: a wrong id is still a wrong id, and a
        # list item is where corpus prose puts plenty of them. If this went
        # quiet the split would have stopped checking rather than started.
        text = '- The `0x08A8` listing is a member of `main-ec-002`.\n'
        self.assertEqual(cited(text), (1, "0x08A8"))

    def test_drift_in_the_second_item_is_still_reported(self):
        # Not only the first item. A split that checked item one and passed
        # over the rest would satisfy the case above. "as a member of" is load-
        # bearing: without a membership cue the checker skips the unit by rule
        # and never reaches the address, which is the case below this one.
        text = ('- An item naming `main-ec-003` correctly, with `0x0460`.\n'
                '- An item calling `0x08A8` a member of `main-ec-002`.\n')
        self.assertEqual(cited(text), (1, "0x08A8"))

    def test_a_wrapped_claim_across_a_line_break_is_still_read(self):
        # The wrap case `units()` exists for: the id and the address it is
        # wrong about are on different lines, and an attribution that straddles
        # a wrap is one a line-based walk misses.
        text = ('- The `0x08A8` listing is a member of\n'
                '  `main-ec-002`, and of no other cluster.\n')
        self.assertEqual(cited(text), (1, "0x08A8"))

    def test_a_re_packed_list_item_still_reports_its_operand(self):
        # The §26 shape as a list item, which is what a membership claim in
        # this corpus often is: a claim and an operand in one item. The bound
        # is named with a cluster and the operand with another, so the pairing
        # rule has to see both inside the *one* item -- which is the property a
        # too-eager split would break, by separating the two halves.
        text = ('- The clear steps over `0x0460`, a member of `main-ec-003`, '
                'and the `setb c` makes the second bound `0x06C6`, which the '
                'same sentence also calls a member of `main-ec-003`.\n')
        self.assertEqual(cited(text), (1, "0x06C6"))


class DoesNotSplitWhatIsNotAList(unittest.TestCase):
    """Lines that look like markers and are not items, and the fence.

    A split here would be a split the walk already made for another reason, or
    one it has no business making: the first wastes nothing, and the second is
    the case where cutting a claim in half would stop it being checked.
    """

    def test_a_setext_underline_is_not_a_list_item(self):
        # `---` under a heading. A split here would cut the heading's paragraph
        # from the prose under it, for a line that carries no claim at all.
        text = ('A heading\n'
                '---\n'
                'The `0x08A8` listing is a member of `main-ec-003`.\n')
        self.assertEqual(len(units_of(text)), 1)

    def test_a_thematic_break_does_not_go_through_the_new_branch(self):
        # `***` carries no list marker, so the split here is `TERMINATOR`'s --
        # its lookahead already took `*` -- and not this suite's rule. The case
        # holds the line between the two: a break the walk already made must
        # not start making *different* ones, and the honest way to say that is
        # that the claim above the rule is still checked as one unit.
        text = ('The `0x08A8` listing is a member of `main-ec-003`.\n'
                '***\n')
        self.assertEqual(cited(text), (0, None))
        self.assertTrue(all("main-ec-003" in u for u in units_of(text)
                            if "0x08A8" in u),
                        "the id and the address it governs were separated")

    def test_a_list_inside_a_fence_is_not_split(self):
        # A fenced block is read as its own paragraph and cut into sentences,
        # which is the #605 shape; the list split is a paragraph rule and does
        # not reach inside one. A console transcript's list is still one unit.
        text = ('```\n'
                '- a `main-ec-003` note\n'
                '- the `0x06C6` listing\n'
                '```\n')
        self.assertEqual(len(units_of(text)), 1)


class TheSkipStillReadsTheSame(unittest.TestCase):
    """A split unit is still a unit the skip rules are asked about."""

    def test_a_list_item_is_still_subject_to_the_membership_skip(self):
        # An item naming a cluster and an address but claiming no membership is
        # skipped for that reason, and splitting it must not turn the skip into
        # a check. The reason is asserted rather than only the silence, because
        # "silent" and "passed over" are the same output and only the reason
        # tells them apart.
        text = '- The `0x08A8` block beside `main-ec-003`, read as a byte.\n'
        self.assertEqual(cited(text), (0, None))
        self.assertEqual(skipped(text), ["no membership claim"])

    def test_a_denial_in_one_item_is_not_read_as_a_denial_in_the_next(self):
        # The skip is a property of a unit. Splitting makes it narrower, which
        # is the conservative direction: the second item is checked on its own
        # words rather than inheriting the first item's denial.
        text = ('- `0x06C6` is not a member of `main-ec-003`.\n'
                '- The `0x08A8` listing is a member of `main-ec-003`.\n')
        self.assertEqual(cited(text), (0, None))


class TheSplitIsReportedAsSuch(unittest.TestCase):
    """`--verbose` still names what it passed over, after the split."""

    def test_verbose_names_a_split_unit_with_its_reason(self):
        # The contract `skip_reason()` carries is that a caller reading only
        # the exit code cannot tell a passed-over unit from a checked one, so a
        # split that made the reason unreadable would be a regression the exit
        # code would not show.
        text = ('- A first item naming `main-ec-003` in passing.\n'
                '- A second item naming `main-ec-002` and `0x08A8`, without '
                'claiming membership in either.\n')
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                _, _, reasons = ccc.check(path, CLUSTERS, COUNTS, KNOWN, None,
                                          None, True)
        finally:
            os.unlink(path)
        self.assertIn("no membership claim", reasons)
        self.assertIn("no membership claim", err.getvalue())


if __name__ == '__main__':
    unittest.main()