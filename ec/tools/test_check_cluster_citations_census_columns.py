#!/usr/bin/env python3
"""Offline checks that a census row's three counts are read where they are.

`check_cluster_citations.py`'s count rule is the only thing holding
`ec/annotations/xdata-register-map.md` §5's hand-typed `size`, `refs` and
`named inside` columns to `ec/annotations/xdata-clusters.csv`. For as long as
the rule found its columns by fixed index, it read the size and the reference
count out of the wrong cells on §5's own table -- `row[1]` is a `cluster_key`
and `row[2]` a `cluster_name` there -- and `number()` returned `None` for both,
so the rule silently checked neither figure on any real row while its
docstring claimed it held both (issue #1240). A rule that reads nothing exits
0: the failure mode is silence, not a red suite, so what is pinned here is
that each of the three figures is read *from its own column* on the shapes the
corpus actually uses.

The fixtures are §5's real rows, at the figures the committed census has for
them, so a case reads as the row it is about. Each case perturbs one cell and
expects the disagreement that names that cell: a case that passes whether or
not the fix is in place is not holding anything, so `test_the_three_figures_are
_read_from_their_own_columns` is the one to delete-check first after any edit to
`census_row()`.

The two table shapes are both covered deliberately. §5 is nine columns wide
because `cluster_key` and `cluster_name` sit between the id and the size, and
the shorter `cluster | size | refs | range | named inside` shape is what the
tool's other suites build their fixtures in; a reader that resolved columns
one way would check the other shape never. This file stands beside
`test_check_cluster_citations.py`, which holds the rules themselves rather than
which column each figure is read from.
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


class ReadsEachFigureFromItsOwnColumn(unittest.TestCase):
    """§5's three counted figures, each perturbed on its own.

    The committed rows are right, so every fixture here is one cell moved: the
    point is that the figure a cell carries is the figure the rule reads, and
    a case that names the disagreement does that more sharply than an exit
    code would.
    """

    def test_the_three_figures_are_read_from_their_own_columns(self):
        # The case that goes red when the column resolution is reverted: all
        # three perturbed at once, and all three named. On the pre-fix reader
        # every one of these rows reads clean, because the size and the
        # reference count are looked for in the key and the name.
        text = ('| `main-ec-001` | `ke794087e13a6` | — | 999 | 888 | '
                '`0x0300`-`0x097B` | 77 | prose |')
        n, what = counted(text)
        self.assertEqual(n, 3)
        self.assertEqual(what, '152 addresses in the census, 999 in the row')

    def test_a_wrong_size_is_reported(self):
        # `size` is two columns before the range on §5's header, and one
        # before it on the short shape -- the same cell in each, which is what
        # makes the range the anchor rather than an index.
        text = NINE_COLUMN.replace('| 152 |', '| 999 |')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '152 addresses in the census, 999 in the row')

    def test_a_wrong_reference_count_is_reported(self):
        text = NINE_COLUMN.replace('| 873 |', '| 999 |')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '873 references in the census, 999 in the row')

    def test_a_reference_count_is_compared_as_a_number_not_as_its_text(self):
        # The table writes `1,130` where the census holds `1130`, and the two
        # have to be equal for the row to be right. Comparing the text would
        # flag every comma in the column for good.
        text = ('| `main-ec-002` | `kefb63d82f8c7` | `mode-oem-init` | 92 | '
                '`1,130` | `0x0456`-`0x1809` | 35 | prose |')
        self.assertEqual(counted(text), (0, None))

    def test_a_wrong_named_count_is_reported(self):
        # The cell after the range. This one was read before the fix and is
        # here to hold it still: an anchor that moved the named count off the
        # range would pass every other case in this class.
        text = NINE_COLUMN.replace('| 11 |', '| 40 |')
        n, what = counted(text)
        self.assertEqual(n, 1)
        self.assertEqual(what, '11 named addresses in the census, 40 in the row')

    def test_the_shorter_shape_is_still_read(self):
        # The same three figures with the key and the name columns absent, so
        # the cells the sizes occupy are different ones. A fix that resolved
        # columns only for §5's header would pass every case above and fail
        # this one.
        n, what = counted(SIX_COLUMN.replace('| 152 |', '| 999 |'))
        self.assertEqual(n, 1)
        self.assertEqual(what, '152 addresses in the census, 999 in the row')

        n, what = counted(SIX_COLUMN.replace('| 873 |', '| 999 |'))
        self.assertEqual(n, 1)
        self.assertEqual(what, '873 references in the census, 999 in the row')

    def test_an_alternate_census_without_a_range_column_still_holds_two_figures(self):
        # A hand-built `--clusters` CSV can carry `size` and `refs` without an
        # `addr_range` column at all. Nothing then holds the row's range or its
        # named count -- there is no column to hold them to -- but the two
        # counts beside them are ordinary columns of that same CSV and are
        # still checked. Moving the read to the anchor must not have taken the
        # two counts into the `addr_range` guard along with the other two.
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

        # The named count is 99 against the census's 0 and is *not* reported:
        # that column is absent, so there is nothing to hold it to.
        self.assertEqual(counted(NINE_COLUMN.replace("| 11 |", "| 99 |"),
                                 counts), (0, None))
        # The size and the reference count are columns this census does carry.
        n, what = counted(NINE_COLUMN.replace("| 152 |", "| 999 |"), counts)
        self.assertEqual(n, 1)
        self.assertEqual(what, "152 addresses in the census, 999 in the row")
        n, what = counted(NINE_COLUMN.replace("| 873 |", "| 999 |"), counts)
        self.assertEqual(n, 1)
        self.assertEqual(what, "873 references in the census, 999 in the row")


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


class TheCommittedWorklistIsHeldToTheCsv(unittest.TestCase):
    """§5 as committed, each of its rows read against the census beside it.

    The tool's own `TheCommittedTree` case runs the whole corpus and exits on
    any disagreement, which is the gate that has to stay green. This one is the
    narrower claim: it reads §5's rows *out of the committed file* rather than
    from fixtures, so a row that drifts fails here naming the row and the
    figure, and a table that loses its range column -- the shape this suite is
    about -- fails here too, by finding no rows to read at all.

    Deliberately not a census of rows: the number of rows §5 carries is a value
    every merge that adds a cluster has to edit, so the assertion is that each
    row found agrees, not how many were found.
    """

    WORKLIST = HERE.parent / "annotations" / "xdata-register-map.md"

    def _rows(self):
        """The §5 census rows, as (cluster id, row text) for each found."""
        found = []
        for line in self.WORKLIST.read_text(encoding="utf-8").split("\n"):
            row = ccc.cells(line.strip())
            if not row:
                continue
            head = ccc.clean(row[0])
            ids = ccc.CLUSTER_ID.findall(head)
            if len(ids) == 1 and head == ids[0]:
                found.append((ids[0], line.strip()))
        return found

    def test_every_committed_worklist_row_agrees_with_the_committed_census(self):
        counts = ccc.census()[2]
        rows = self._rows()
        self.assertTrue(rows, f"§5 rows were found in {self.WORKLIST}")
        for cluster_id, row in rows:
            with self.subTest(cluster=cluster_id):
                self.assertEqual(counted(row + "\n", counts), (0, None))

    def test_a_perturbed_committed_row_is_reported(self):
        # The negative of the case above, on the committed census rather than a
        # fixture one: it is what says the previous case passes because the
        # figures are read, not because nothing was read at all.
        counts = ccc.census()[2]
        self.assertEqual(counts["main-ec-002"]["size"], 92)
        self.assertEqual(counts["main-ec-002"]["refs"], 1130)
        self.assertEqual(counts["main-ec-002"]["named"], 35)
        wrong = ('| `main-ec-002` | `kefb63d82f8c7` | `mode-oem-init` | 93 | '
                 '`1,131` | `0x0456`-`0x1809` | 36 | prose |\n')
        n, what = counted(wrong, counts)
        self.assertEqual(n, 3)
        self.assertEqual(what, "92 addresses in the census, 93 in the row")


if __name__ == '__main__':
    unittest.main()