#!/usr/bin/env python3
"""Offline checks that a census row's range is read where it is.

`check_cluster_citations.py`'s census-row rule holds
`ec/annotations/xdata-register-map.md` §5's hand-typed range column to
`ec/annotations/xdata-clusters.csv`. It used to hold the `size` and `refs`
columns as well; since 2026-10-04 it holds none of the three counts, because
seeding a routine moves them and §5 is a shared file every such branch would
have to edit (#1849). For as long as the rule found its columns by fixed index,
it read the wrong cells on §5's own table -- `row[1]` is a `cluster_key` and
`row[2]` a `cluster_name` there -- and silently checked nothing on any real row
while its docstring claimed otherwise (issue #1240). A rule that reads nothing
exits 0: the failure mode is silence, not a red suite, so what is pinned here
is that the range is read *from its own column* on the shapes the corpus
actually uses, and that the counts beside it are passed over.

The fixtures are §5's real rows, at the figures the committed census has for
them, so a case reads as the row it is about. Each case perturbs one cell:
`test_a_wrong_range_is_reported_on_the_nine_column_shape` is the one to
delete-check first after any edit to `census_row()`.

The two table shapes are both covered deliberately. §5 is nine columns wide
because `cluster_key` and `cluster_name` sit between the id and the size, and
the shorter `cluster | size | refs | range | named inside` shape is what the
tool's other suites build their fixtures in; a reader that resolved columns
one way would check the other shape never. This file stands beside
`test_check_cluster_citations.py`, which holds the rules themselves rather than
which column the range is read from.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    'check_cluster_citations', HERE / 'check_cluster_citations.py')
ccc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ccc)

# §5's own two rows, at the figures `ec/annotations/xdata-clusters.csv` holds
# for them, so a fixture row is the real row rather than an idealisation of it.
# The `refs` counts are written the way the table writes them -- thousands
# commas and all -- because that is one of the two things the reader has to get
# right before it can compare anything.
COUNTS = {
    'main-ec-001': {'size': 152, 'refs': 873, 'named': 11,
                    'addr_range': '0x0300-0x097B'},
    'main-ec-002': {'size': 92, 'refs': 1130, 'named': 35,
                    'addr_range': '0x0456-0x1809'},
}

# The committed §5 header, which is the shape the column-index defect was
# invisible in: `row[1]` and `row[2]` are the key and the name, and neither is
# a number, so a reader looking there found nothing to disagree with. The two
# trailing columns are the ones that carry prose and so are never counts.
NINE_COLUMN = (
    '| `main-ec-001` | `ke794087e13a6` | — | 152 | 873 | `0x0300`-`0x097B` '
    '| 11 | 37/100 fns, 479 (55%) | the working page |\n')

# The same cluster in the shorter shape the tool's other fixtures use: no key
# and no name, so the figures sit one and two columns along rather than three
# and four. It has to keep being checked, because the anchor reaches the same
# two cells in both shapes by different offsets — a reader written for §5's
# header alone would pass every case above and silently stop reading this one.
SIX_COLUMN = (
    '| `main-ec-001` | 152 | 873 | `0x0300`-`0x097B` | 11 | the page |\n')


def counted(text, counts=COUNTS):
    """(how many cells disagree, what it says about the first) for a row.

    The count rule's own figures only, so a membership disagreement in the
    same row cannot stand in for the count one a case is about.
    """
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False) as f:
        f.write(text)
        path = f.name
    try:
        members, known, by_key, by_name = {}, set(), {}, {}
        problems, _, _ = ccc.check(path, members, counts, known, by_key, by_name,
                                   False)
    finally:
        os.unlink(path)
    problems = [p for p in problems if p[4] != "membership"]
    return len(problems), problems[0][3] if problems else None


class OnlyTheRangeIsHeld(unittest.TestCase):
    """§5's range, read from its own column, and the three counts beside it not.

    The committed rows are right, so every fixture here is one cell moved. The
    size, the reference count and the named count are figures of the census,
    which seeding a routine moves -- #1849 turned §5 rows red
    -- so the rule holds none of them (2026-10-04). The range is the cell that
    says which cluster a row is about, and it is still read from its own column
    on both shapes.
    """

    def test_the_three_counts_are_not_held(self):
        text = ('| `main-ec-001` | `ke794087e13a6` | — | 999 | 888 | '
                '`0x0300`-`0x097B` | 77 | prose |')
        self.assertEqual(counted(text), (0, None))
        self.assertEqual(counted(SIX_COLUMN.replace('| 152 | 873 |',
                                                    '| 999 | 888 |')), (0, None))

    def test_a_wrong_range_is_reported_on_the_nine_column_shape(self):
        # The case that goes red when the column resolution is reverted: on
        # §5's header `row[1]` and `row[2]` are the key and the name, and a
        # fixed-index reader finds no range there to disagree with.
        n, what = counted(NINE_COLUMN.replace('`0x097B`', '`0x097C`'))
        self.assertEqual(n, 1)
        self.assertEqual(what, 'range `0x0300-0x097B` in the census, '
                               '`0x0300-0x097C` in the row')

    def test_a_wrong_range_is_reported_on_the_shorter_shape(self):
        n, what = counted(SIX_COLUMN.replace('`0x097B`', '`0x097C`'))
        self.assertEqual(n, 1)
        self.assertEqual(what, 'range `0x0300-0x097B` in the census, '
                               '`0x0300-0x097C` in the row')

    def test_an_alternate_census_without_a_range_column_holds_nothing(self):
        # A hand-built `--clusters` CSV can carry `size` and `refs` without an
        # `addr_range` column at all. There is then nothing to hold the row's
        # range to, and the counts are not held on any census.
        with tempfile.TemporaryDirectory() as d:
            clusters = os.path.join(d, "clusters.csv")
            registers = os.path.join(d, "registers.csv")
            with open(clusters, "w") as f:
                f.write("cluster_id,program,size,refs,addrs\n")
                f.write("main-ec-001,main-ec,152,873,0x0300 0x0301\n")
            with open(registers, "w") as f:
                f.write("addr,program,cluster_id\n")
                f.write("0x0300,main-ec,main-ec-001\n")
            counts = ccc.census(clusters, registers)[2]
        self.assertEqual(counts["main-ec-001"]["addr_range"], "")
        self.assertEqual(counted(NINE_COLUMN.replace('`0x097B`', '`0x097C`'),
                                 counts), (0, None))


class WhatTheAnchorCannotPlace(unittest.TestCase):
    """The rows the anchor does not resolve, which are left alone rather than guessed at.

    A census row says which column is which by carrying a range, so a row
    without one -- or with one too near the front to have a size and a
    reference count before it -- has not said. These cases hold that such a row
    is passed over rather than read against a guess, and that the pass-over is
    visible to the caller as no problem rather than as a wrong one.
    """

    def test_a_row_with_no_range_is_not_read(self):
        # The shape a table gets when the range column is dropped. The
        # figures are wrong on purpose: a reader that fell back to fixed
        # indices would flag this row, and one that guessed the columns from
        # position would flag it wrongly.
        text = '| `main-ec-001` | 999 | 999 | 11 | prose |\n'
        self.assertEqual(counted(text), (0, None))

    def test_a_range_with_no_room_before_it_is_not_read(self):
        # The range is the first cell after the id, so there is nowhere for a
        # size or a reference count to be. Both are wrong on purpose.
        text = '| `main-ec-001` | `0x0300`-`0x097B` | 999 | 999 | prose |\n'
        self.assertEqual(counted(text), (0, None))

    def test_a_listing_in_the_named_column_is_still_not_a_count(self):
        # §5 writes `0x043E` in `main-ec-005`'s named cell, because a single
        # name is worth the space. That is a listing and not a count of one, and
        # the anchor fix must not have turned it into a disagreement.
        counts = {'main-ec-001': {'size': 152, 'refs': 873, 'named': 1,
                                  'addr_range': '0x0300-0x097B'}}
        text = ('| `main-ec-001` | `ke794087e13a6` | — | 152 | 873 | '
                '`0x0300`-`0x097B` | `0x043E` | prose |')
        self.assertEqual(counted(text, counts), (0, None))

    def test_only_the_first_span_anchors(self):
        # A second span in the named column is not another anchor: taken as
        # one, it would move the size and reference cells onto the wrong side
        # of the row and read the named count out of the last cell instead.
        counts = {'main-ec-001': {'size': 152, 'refs': 873, 'named': 11,
                                  'addr_range': '0x0300-0x097B'}}
        text = ('| `main-ec-001` | `ke794087e13a6` | — | 152 | 873 | '
                '`0x0300`-`0x097B` | `0x0430`-`0x0440` | prose |')
        self.assertEqual(counted(text, counts), (0, None))


class TheCommittedWorklistIsStillReadable(unittest.TestCase):
    """§5 as committed: every row is found, and carries a range the rule anchors on.

    §5's rows are not held to the live census any more (2026-10-04). They name
    clusters by rank, and seeding a routine renumbers the ranks, so a committed
    row would go red for a cluster it never described; the committed-tree run
    of `check_cluster_citations.py` passes rank-cited units over for the same
    reason. What stays true of every tree is the shape the fixtures above test
    against: §5 still has census rows, and each still carries a range in a
    column with room for a size and a reference count before it.

    Deliberately not a census of rows: the number of rows §5 carries is a value
    every merge that adds a cluster has to edit.
    """

    WORKLIST = HERE.parent / "annotations" / "xdata-register-map.md"

    def _rows(self):
        """The §5 census rows, as (cluster id, cells) for each found."""
        found = []
        for line in self.WORKLIST.read_text(encoding="utf-8").split("\n"):
            row = ccc.cells(line.strip())
            if not row:
                continue
            head = ccc.clean(row[0])
            ids = ccc.CLUSTER_ID.findall(head)
            if len(ids) == 1 and head == ids[0]:
                found.append((ids[0], row))
        return found

    def test_every_committed_worklist_row_has_an_anchored_range(self):
        rows = self._rows()
        self.assertTrue(rows, f"§5 rows were found in {self.WORKLIST}")
        for cluster_id, row in rows:
            with self.subTest(cluster=cluster_id):
                anchors = [i for i, cell in enumerate(row[2:], start=2)
                           if ccc.SPAN.fullmatch(ccc.clean(cell))]
                self.assertTrue(anchors, "no range cell in the row")
                self.assertGreaterEqual(anchors[0], 3,
                                        "the range has no room for a size and "
                                        "a reference count before it")


if __name__ == '__main__':
    unittest.main()