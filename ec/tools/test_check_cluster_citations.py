#!/usr/bin/env python3
"""Offline checks for check_cluster_citations.py: committed files only.

The tool is a checker whose failure mode is silence rather than a crash.
Loosen a regex and it stops catching drift while still exiting 0, and the only
thing that notices is a reader who has already been misled. So what is pinned
here is the line between what the tool claims and what it skips: each rule that
makes it conservative gets a case saying so, because a skip that is not
deliberate is the bug.

The two rules are pinned apart as well as together. Membership and the census
counts are separate gates over the same walk, and a fixture is free to satisfy
one and not the other — so where a case is about the counts, its row is
correct about them, and where it is about membership, its cells are counted
right. A fixture that is wrong in both directions tests neither.

The fixtures are small enough to write inline, which keeps each case readable
as the sentence it is about rather than as a diff against a stored file. The
census they check against is not the real one; the last case is, and it is
what says the tree's prose currently agrees with the CSVs beside it.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'check_cluster_citations', HERE / 'check_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# A census small enough to reason about by hand: two clusters that share no
# address, which is the property the real main-ec-002 and main-ec-003 also have
# and the reason a wrong id cannot be caught by "close enough".
MEMBERS = {
    'main-ec-002': {'0x044C', '0x0860', '0x086E'},
    'main-ec-003': {'0x0460', '0x08A8'},
}
KNOWN = {'0x044C', '0x0860', '0x086E', '0x0460', '0x08A8', '0x06C6', '0x06CD',
         '0x09CE'}

# The two clusters the `xdata-06c2-06db-timers.md` split sentence names, as
# the census has them rather than as the small census above: `main-ec-121` is
# `0x0443 0x06C6` and `main-ec-198` is `0x06CD`, and they share no address, so
# neither id is "close enough" for the other.
SPLIT_MEMBERS = {
    'main-ec-121': {'0x0443', '0x06C6'},
    'main-ec-198': {'0x06CD'},
}

# The counted columns of the same two clusters, at the figures the real
# xdata-register-map.md §5 rows carry, so a fixture row can be the real one.
COUNTS = {
    'main-ec-002': {'size': 44, 'refs': 248, 'named': 19,
                    'addr_range': '0x044C-0x1F07'},
    'main-ec-003': {'size': 43, 'refs': 4965, 'named': 43,
                    'addr_range': '0x0460-0x09CE'},
}

def _problems(text, members=None, counts=None):
    """The problem tuples the tool reports for one piece of prose."""
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        problems, _ = ccc.check(path, members or MEMBERS, counts or COUNTS,
                                KNOWN, False)
    finally:
        os.unlink(path)
    return problems


def cited(text, members=None):
    """(count, first address) the tool reports for one piece of prose."""
    problems = _problems(text, members)
    return len(problems), problems[0][3] if problems else None


def counted(text, counts=None):
    """(how many cells disagree, what it says about the first) for a row."""
    problems = [p for p in _problems(text, COUNTS, counts)
                if p[4] != "membership"]
    return len(problems), problems[0][3] if problems else None


class ReportsRealDrift(unittest.TestCase):
    """The four shapes issue #253 found, and the two numbers they turn on."""

    def test_wrong_id_with_one_address(self):
        n, addr = cited('The `0x0860` run is in cluster `main-ec-003`.\n')
        self.assertEqual((n, addr), (1, '0x0860'))

    def test_right_id_is_silent(self):
        self.assertEqual(cited('The `0x0860` run is in cluster `main-ec-002`.\n'), (0, None))

    def test_address_in_either_named_cluster_passes(self):
        # The shape the any-of rule was written for, still silent -- and
        # silent now for the stronger reason: each address is a member of the
        # id its own clause names, so the pairing rule answers it without the
        # fallback.
        text = ('the clustering put `0x0860` in `main-ec-002` and `0x08A8` in '
                '`main-ec-003`\n')
        self.assertEqual(cited(text), (0, None))

    def test_address_in_neither_named_cluster_fails(self):
        text = 'the clustering put `0x06C6` in `main-ec-002` and `main-ec-003`\n'
        n, addr = cited(text)
        self.assertEqual((n, addr), (1, '0x06C6'))

    def test_wrapped_attribution_is_still_seen(self):
        # The manual-fan-ctrl-0751.md case: the address and the id it is wrong
        # about are on different lines, and a line-based scan misses it.
        text = ('The one reader found for `0x0860` (bank1 `0xA987`) was not\n'
                'decoded, and the members of the `main-ec-003` cluster are unnamed.\n')
        n, addr = cited(text)
        self.assertEqual((n, addr), (1, '0x0860'))

    def test_reported_line_is_the_address_line_not_the_unit_start(self):
        text = ('A sentence that opens here and names no address, and goes on.\n'
                'It mentions `0x0860` and the `main-ec-003` cluster in one breath.\n')
        with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
            f.write(text)
            path = f.name
        try:
            problems, _ = ccc.check(path, MEMBERS, COUNTS, KNOWN, False)
        finally:
            os.unlink(path)
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0][1], 2)


class HoldsThePairing(unittest.TestCase):
    """The split the `xdata-06c2-06db-timers.md` sentence claims, both ways.

    Issue #253 corrected that sentence from `main-ec-118` to `main-ec-121` by
    reading the census by hand, because a unit naming two clusters used to be
    satisfied by either and an exchange in it was invisible. These are the two
    directions of that sentence the tool now has to tell apart.
    """

    def test_committed_split_sentence_is_silent(self):
        text = ('but the clustering put `0x06C6` in `main-ec-121` and `0x06CD` '
                'in `main-ec-198` — 7 and 26 references on their own rows\n')
        self.assertEqual(cited(text, SPLIT_MEMBERS), (0, None))

    def test_swapped_ids_in_a_split_fail(self):
        # Both addresses, each against the id its own clause put it with: the
        # rule this replaces reported neither, and one that paired only the
        # first would read as a smaller catch than it is.
        text = ('but the clustering put `0x06C6` in `main-ec-198` and `0x06CD` '
                'in `main-ec-121` — 7 and 26 references on their own rows\n')
        # p[5] is the id the line's own wording pairs the address with, which
        # is the report's "not in `main-ec-198`" -- the whole point of the
        # pairing rule, so the case reads that field and not just the count.
        found = _problems(text, SPLIT_MEMBERS)
        self.assertEqual([(p[3], p[5]) for p in found],
                         [('0x06C6', 'main-ec-198'), ('0x06CD', 'main-ec-121')])

    def test_enumeration_shaped_split_falls_back_to_any_of(self):
        # `docs/findings.md:3671` claims the same split with the ids first and
        # the addresses in a trailing list. Nothing pairs, so the any-of rule
        # answers it — and answers the ids exchanged the same way. That is the
        # blind spot the docstring's third limit states, and the case is here
        # so the docstring cannot start claiming more than the tool does.
        text = ('the two the clustering cut into `main-ec-121` and `main-ec-198` '
                '(`0x06C6`, `0x06CD`) are countdowns\n')
        self.assertEqual(cited(text, SPLIT_MEMBERS), (0, None))
        swapped = ('the two the clustering cut into `main-ec-198` and '
                   '`main-ec-121` (`0x06C6`, `0x06CD`) are countdowns\n')
        self.assertEqual(cited(swapped, SPLIT_MEMBERS), (0, None))

    def test_an_unpaired_address_in_a_run_is_still_checked(self):
        # `manual-fan-ctrl-0751.md:694`'s shape, where "of" joins `main-ec-011`
        # to the first of a run of ten addresses and pairs only that one. The
        # fallback is per address on purpose, so a unit that pairs one byte
        # does not silence the rest of the run: `0x06C6` is in neither cluster
        # here, and is still reported.
        text = ('`main-ec-002` is the cluster of `0x044C 0x086E 0x06C6`, and '
                '`main-ec-003` holds `0x08A8`\n')
        self.assertEqual(cited(text), (1, '0x06C6'))


class SkipsDeliberately(unittest.TestCase):
    """Every rule that makes the tool conservative, as a case saying so."""

    def test_denial_is_skipped(self):
        text = '`0x08A8` and `0x06C6` are not in `main-ec-002`, and both reload.\n'
        self.assertEqual(cited(text), (0, None))

    def test_singleton_wording_is_skipped(self):
        # "is a size-1 cluster on its own" denies membership in the cluster the
        # same sentence names, and does it without a negation word.
        text = ('nine of the ten are in `main-ec-002`, and the tenth, `0x06C6`, '
                'is a cluster on its own\n')
        self.assertEqual(cited(text), (0, None))

    def test_singleton_wording_naming_two_clusters_is_still_skipped(self):
        # The `manual-fan-ctrl-0751.md:701` shape with a second cluster named,
        # so the pairing rule is one the branches could reach. The preposition
        # in "rather than part of" would pair `0x06C6` with the cluster the
        # sentence says it is not part of, and `0x06C6` is in neither, so were
        # this skip to move behind the pairing it would report a denial.
        text = ('six of the ten are in `main-ec-002`, and `0x06C6` is a '
                'size-1 cluster of its own rather than part of `main-ec-003`\n')
        self.assertEqual(cited(text), (0, None))

    def test_mention_without_a_membership_claim_is_skipped(self):
        # The xdata-register-map.md §5 row shape: a cluster id, its address
        # range, and a title naming a byte the shared function reads. The count
        # cell is right on purpose -- this is the membership skip, and
        # `CensusCounts.test_none_is_not_the_same_as_no_names` is the case
        # about the counts.
        text = ('| `main-ec-003` | 43 | 4,965 | `0x0460`-`0x09CE` | 43 | the '
                '`0x06C6`/`0x0860` gate block |\n')
        self.assertEqual(cited(text), (0, None))

    def test_code_address_is_not_an_xdata_address(self):
        # bank0:0x9D9B is code. It is not in the census, so it is not a
        # cluster member claim, however much it looks like one.
        text = 'The `0x9D9B` routine in cluster `main-ec-003` is where it happens.\n'
        self.assertEqual(cited(text), (0, None))

    def test_adjacent_list_items_do_not_bleed(self):
        # Without a sentence boundary at a list marker, the first item's
        # cluster id reaches into the next item's addresses.
        text = ('The census is wrong for this block.\n'
                '- A note about `main-ec-003`, with no address.\n'
                '- The `0x08A8` listing is separate.\n')
        self.assertEqual(cited(text), (0, None))

    def test_table_rows_are_separate_units(self):
        text = ('| `main-ec-003` | 43 | 4,965 | `0x0460`-`0x09CE` | 43 | the block |\n'
                '| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | 19 | the '
                'gate block |\n')
        self.assertEqual(cited(text), (0, None))

    def test_a_prose_cell_is_not_a_count_claim(self):
        # The xdata-06c2-06db-timers.md:491 shape: a cluster id, then a
        # deliberate contrast between the committed cluster and the shape a
        # code guard would produce. The prose under that table says the
        # right-hand column is a shape and carries no id, so a rule that read
        # counts out of `**43 addresses, 4,965 refs**` would flag those two
        # figures for good and for no reason.
        text = ('| **`main-ec-003`** | **43 addresses, 4,965 refs** | '
                '**44 addresses, 248 refs** |\n')
        self.assertEqual(counted(text), (0, None))

    def test_a_row_whose_first_cell_is_not_a_cluster_id_is_not_a_census_row(self):
        # The gpu-tgp-07c4-07d7-door.md shape, with the fixture's own cluster
        # id where the real row carries main-ec-001: an address, a DSDT field,
        # and a source line number. The id is in the cross-reference cell
        # rather than the first, so the row is not a census row at all and
        # 52204 is never read as a count of anything.
        text = ('| `0x0743` | `GNEN` b0 (`dsdt.dsl:52204`) | `main-ec-002`, '
                '`main-ec`, no `[writer]`-tagged site in the row |\n')
        self.assertEqual(counted(text), (0, None))

    def test_a_bare_address_in_the_named_column_is_a_listing(self):
        # The shape of main-ec-004's and main-ec-006's own §5 cells: the one
        # address a small cluster names, written out rather than counted.
        # Reading it as a count of one would flag a row that is right.
        text = ('| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | `0x044C` | '
                'the gate block |\n')
        self.assertEqual(counted(text), (0, None))

    def test_a_span_is_the_row_range_and_never_a_count(self):
        # The range anchors the named cell and is held to the row's own
        # `addr_range`, but a span is two addresses and is never read as a
        # number in any column -- here a second one sits where the named count
        # goes, and the first span is still the only anchor.
        text = ('| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | '
                '`0x0860`-`0x086E` | the gate block |\n')
        self.assertEqual(counted(text), (0, None))

    def test_free_text_in_the_named_column_is_not_a_count(self):
        text = ('| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | most of the '
                'dispatch run | the gate block |\n')
        self.assertEqual(counted(text), (0, None))

    def test_a_dash_in_a_size_or_refs_column_is_not_a_count_of_zero(self):
        # The xdata-06c2-06db-timers.md convention: `—` in a count column
        # means the figure does not apply to that row, which is not the same
        # claim as zero. Only the "named inside" column reads it as zero,
        # which is why the two cell readers are separate.
        text = ('| `main-ec-002` | — | 248 | `0x044C`-`0x1F07` | 19 | the '
                'gate block |\n')
        self.assertEqual(counted(text), (0, None))

    def test_a_row_naming_two_clusters_is_not_a_census_row(self):
        # Whose figures would they be? The first cell has to be one id, so a
        # cell naming two is left unread rather than read against one of them.
        # The count is deliberately wrong, so a rule that picked an id out of
        # the cell would flag it.
        text = ('| `main-ec-002`/`main-ec-003` | 44 | 248 | '
                '`0x044C`-`0x1F07` | 4 | the gate block |\n')
        self.assertEqual(counted(text), (0, None))


class CensusCounts(unittest.TestCase):
    """The figures issue #272 put a hand-typed census table behind.

    Four of §5's twelve rows disagreed with `xdata-clusters.csv` while nothing
    held them there, and these are the shapes they took. The fixtures are §5's
    own rows with one cell moved, so a case reads as the table it is about.
    """

    def test_a_census_row_that_agrees_is_silent(self):
        text = ('| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | 19 | the '
                '`0x06E6`/`0x0860` gate block |\n')
        self.assertEqual(counted(text), (0, None))

    def test_a_wrong_size_is_reported(self):
        # main-ec-004's row read 30 for a cluster the census sizes at 26.
        text = ('| `main-ec-003` | 42 | 4,965 | `0x0460`-`0x09CE` | 43 | one '
                'loop walking a block of counters |\n')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '43 addresses in the census, 42 in the row')

    def test_a_wrong_reference_count_is_reported(self):
        # main-ec-004's row read 312 for a cluster the census puts at 278.
        text = ('| `main-ec-003` | 43 | 4,900 | `0x0460`-`0x09CE` | 43 | one '
                'loop walking a block of counters |\n')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '4965 references in the census, 4,900 in the row')

    def test_a_wrong_named_count_is_reported(self):
        # main-ec-002's row read 4 for a cluster the census names 19 in.
        text = ('| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | 4 | the '
                '`0x06E6`/`0x0860` gate block |\n')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '19 named addresses in the census, 4 in the row')

    def test_a_wrong_range_is_reported(self):
        text = ('| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F08` | 19 | the '
                '`0x06E6`/`0x0860` gate block |\n')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, 'range `0x044C-0x1F07` in the census, '
                               '`0x044C-0x1F08` in the row')

    def test_none_is_not_the_same_as_no_names(self):
        # The sharpest of the four rows. #179 gave the counter block 43
        # `XDATA_*` names, so the census names every member of main-ec-003,
        # and the row still read `none`. This is the one cell that is not a
        # number and still a count claim, and it is what makes the row
        # checkable rather than merely wrong.
        text = ('| `main-ec-003` | 43 | 4,965 | `0x0460`-`0x09CE` | none | one '
                'loop walking a block of counters |\n')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '43 named addresses in the census, none in the row')

    def test_none_is_right_for_a_cluster_the_census_names_nothing_in(self):
        text = ('| `main-ec-003` | 43 | 4,965 | `0x0460`-`0x09CE` | none | one '
                'loop walking a block of counters |\n')
        facts = {cid: dict(v) for cid, v in COUNTS.items()}
        facts['main-ec-003']['named'] = 0
        self.assertEqual(counted(text, facts), (0, None))

    def test_the_count_rule_does_not_need_a_membership_claim(self):
        # The two gates are independent, and this is the reason they had to
        # be: a §5 row carries a range and a title and never the word
        # "member", so the membership rule skips every one of them and this
        # is the only rule that reads it.
        text = '| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | 4 | the block |\n'
        self.assertIsNone(ccc.MEMBERSHIP.search(text))
        self.assertEqual(counted(text)[0], 1)


class CensusParsing(unittest.TestCase):
    """The CSV read, so a change to the tool's idea of the columns is caught."""

    def test_members_known_addresses_and_counts(self):
        # The count rule reads `size` and `refs` as numbers and the range as
        # text, so a fixture that does the same is what keeps the two apart.
        header = 'cluster_id,program,size,refs,addrs,addr_range,named_addrs\n'
        with tempfile.TemporaryDirectory() as d:
            clusters = os.path.join(d, 'clusters.csv')
            registers = os.path.join(d, 'registers.csv')
            with open(clusters, 'w') as f:
                f.write(header)
                f.write('main-ec-002,main-ec,2,10,0x0860 0x086E,'
                        '0x0860-0x086E,0x0860\n')
            with open(registers, 'w') as f:
                f.write('addr,program,cluster_id\n')
                f.write('0x0860,main-ec,main-ec-002\n')
                f.write('0x086E,main-ec,main-ec-002\n')
            old = (ccc.CLUSTERS, ccc.REGISTERS)
            ccc.CLUSTERS, ccc.REGISTERS = clusters, registers
            try:
                members, known, counts = ccc.census()
            finally:
                ccc.CLUSTERS, ccc.REGISTERS = old
        self.assertEqual(members, {'main-ec-002': {'0x0860', '0x086E'}})
        self.assertEqual(known, {'0x0860', '0x086E'})
        self.assertEqual(counts, {'main-ec-002': {'size': 2, 'refs': 10,
                                                   'named': 1,
                                                   'addr_range': '0x0860-0x086E'}})


class TheCommittedTree(unittest.TestCase):
    """The real thing: the prose and the CSVs beside it currently agree.

    This is the assertion that would have caught issue #253. It is also the
    one that goes red on any future edit that drifts an id, which is the
    point of having the tool in the tree at all.
    """

    def test_committed_prose_matches_committed_census(self):
        err = io.StringIO()
        out = io.StringIO()
        argv = sys.argv
        sys.argv = ['check_cluster_citations.py']
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
                rc = ccc.main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, err.getvalue())
        self.assertIn('every checked', out.getvalue())


if __name__ == '__main__':
    unittest.main()
