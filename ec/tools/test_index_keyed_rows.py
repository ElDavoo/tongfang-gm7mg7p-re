#!/usr/bin/env python3
"""Tests for `index_keyed_rows.py`, the keyed comparison two index images are
read with.

The module replaces a refusal with an answer, so what is worth pinning is not
the answer -- the count a census publishes is a number about prose, and a case
that hardcoded it would fail the day another edit is made -- but **the four ways
a keyed comparison can be wrong quietly**:

  * **the reader comparing nothing.** Two images this cannot read yield two
    empty key sets, which are equal, so the comparison reports no difference over
    a file that plainly carries a table. The guard for that is the caller's
    `located()` and it is stated in the module's docstring; what is pinned here
    is that the reader really does return an empty set (and no refusal) for a
    nested-shaped image read as a root one, so the guard is known to be load
    bearing rather than believed to be.
  * **a refusal being read as an answer, and an answer as a refusal.** A row
    added in the same revision as an edited cell is the case this module exists
    for: the old comparison could only say *not separable by this method*, and
    this one returns **both** the edit and the addition. The other half is that a
    refusal is still a refusal and says which of its three reasons it is -- a
    duplicate key, an empty key and a row with no measured cell are three
    different defects and a reader who cannot tell them apart has a census that
    cannot be argued with.
  * **a key being read as a rename.** A removed key and an added key are two
    rows with their surviving cells, never one edit: pairing them would be a
    judgement about which row became which, which is exactly what a key does not
    know. A nested pointer change is the live instance, and the two cells of it
    are both printed so the evidence for #746 survives the class change intact.
  * **a guard that is not one.** A dict keyed on the first cell would keep one of
    two rows sharing a key and drop the other, and a blank key matches every
    blank key, so both are refusals with the key named rather than a comparison
    over rows nobody can identify. On the committed tree both indexes' keys are
    asserted **duplicate-free** -- the precondition the file-level nested
    comparison rests on, held as a property of the images rather than as a count
    of them.

There is no git in this file: the comparison is over texts, so a case that built
a repository would be testing `git` rather than the keying. `census_index_
third_column_edits.py` is what reads these texts out of a history, and its suite
is where a revision is classified end to end.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import index_keyed_rows as keyed  # noqa: E402

# The root index's own header, and a two-column nested header. These are the
# committed `ec/tools/testdata/README.md` and `call-graph/README.md` spellings,
# and the difference between them is the whole reason there are two populations.
HEADER = ("| File | Feeds | What it constructs |\n"
          "|---|---|---|\n")
NESTED_HEADER = "| file / row | what it pins |\n|---|---|\n"

# The measured column each population is read in. Root is the third -- the
# description a reader opens the table to read -- and nested is the first,
# which is the same column as its key. Stated here rather than derived, so a
# change to either is a change this suite has to be told about.
ROOT = 3
NESTED = 1


def index(*rows, **kwargs):
    """A root-index image; each row is a (file, description) pair.

    `raw` takes pre-spelled rows instead, for the two shapes this helper's own
    spelling cannot express: a genuinely **empty** first cell (an empty string
    wrapped in backticks is `` `` ``, which is a non-empty cell holding nothing
    between two ticks) and a row with no measured cell at all.
    """
    raw = kwargs.pop("raw", None)
    if raw is not None:
        if kwargs:
            raise TypeError("index() takes raw rows or (file, cell) pairs")
        return "# scratch\n\n" + HEADER + "".join(raw)
    return ("# scratch\n\n" + HEADER
            + "".join("| `%s` | `../grade.py` | %s |\n" % row for row in rows)
            + "\nA paragraph below the table.\n")


def nested(*rows):
    """A nested-index image over one table; each row is a (path, pins) pair."""
    return ("# scratch\n\n" + NESTED_HEADER
            + "".join("| `%s` | %s |\n" % row for row in rows)
            + "\nA paragraph below the table.\n")


class KeyReaderTests(unittest.TestCase):
    """The reader, over inline text, with no repository in it at all.

    A reader that found nothing would agree with a reader that found no
    difference, on any pair of images that differ only where it cannot look.
    """

    def test_a_row_is_keyed_by_its_first_cell_and_reads_the_named_column(self):
        rows, why = keyed.keyed_rows(index(("fix.csv", "the mark label")),
                                     ROOT, root=True)
        self.assertIsNone(why)
        self.assertEqual([(row.key, row.cell) for row in rows],
                         [("`fix.csv`", "the mark label")])
        # And the key column is not the measured one: a first-column-only change
        # is a change of key, which is a different thing from an edit.
        other, _why = keyed.keyed_rows(index(("other.csv", "the mark label")),
                                       ROOT, root=True)
        self.assertNotEqual(rows[0].key, other[0].key)

    def test_a_nested_image_is_keyed_by_its_path_and_its_measured_cell_is_that_path(self):
        # The structural fact the whole nested comparison rests on: a nested
        # table is two columns wide, so its measured cell *is* its key. A path
        # change is therefore a key change and cannot be an edit, which is why
        # #746 lands in `one-sided` and not in `edited`.
        rows, why = keyed.keyed_rows(nested(("decompiled/common/0EA2.asm",
                                              "the worked example")),
                                     NESTED, root=False)
        self.assertIsNone(why)
        self.assertEqual(rows[0].key, rows[0].cell)
        self.assertEqual(rows[0].key, "`decompiled/common/0EA2.asm`")

    def test_a_nested_image_is_keyed_across_every_table_in_the_file(self):
        # A nested index has no header that identifies it -- its tables share
        # one -- so the key has to be unique over the whole file. Two tables,
        # four rows, and the third key repeated would be a refusal (below).
        text = ("# scratch\n\n" + NESTED_HEADER
                + "| `a.asm` | one |\n| `b.asm` | two |\n\n"
                + NESTED_HEADER
                + "| `c.asm` | three |\n")
        rows, why = keyed.keyed_rows(text, NESTED, root=False)
        self.assertIsNone(why)
        self.assertEqual([row.key for row in rows],
                         ["`a.asm`", "`b.asm`", "`c.asm`"])

    def test_the_reader_comparing_nothing_returns_an_empty_set_and_no_refusal(self):
        # The silent zero, shown as the thing it is. A nested-shaped image read
        # with the root reader locates no `File`-headed table, so `table_cells()`
        # answers `[]` twice -- and `[] == []` is a clean "no difference" over a
        # file that carries a table. That is why the caller asks `located()`
        # first, and this is the case that says the guard is load bearing.
        rows, why = keyed.keyed_rows(nested(("a.asm", "a case")), ROOT,
                                     root=True)
        self.assertEqual(rows, [])
        self.assertIsNone(why)
        # The same pair through `compare()`, which is where the wrong zero would
        # actually be published.
        answer = keyed.compare(nested(("a.asm", "a case")),
                               nested(("b.asm", "another case")),
                               column=ROOT, root=True)
        self.assertEqual(answer.edits, [])
        self.assertEqual(answer.one_sided, [])
        self.assertIsNone(answer.refusal)


class ComparisonTests(unittest.TestCase):
    """Two images, keyed -- the shapes the census reports."""

    def _compare(self, before, after, column=ROOT, root=True):
        return keyed.compare(before, after, column=column, root=root)

    def test_a_shared_key_whose_cell_differs_is_an_edit(self):
        answer = self._compare(index(("fix.csv", "the mark label")),
                               index(("fix.csv", "the reworded label")))
        self.assertIsNone(answer.refusal)
        self.assertEqual(answer.one_sided, [])
        self.assertEqual(len(answer.edits), 1)
        self.assertEqual(answer.edits[0].key, "`fix.csv`")
        self.assertEqual(answer.edits[0].before, "the mark label")
        self.assertEqual(answer.edits[0].after, "the reworded label")

    def test_a_growth_and_an_edit_in_one_revision_reports_both(self):
        # The case this module exists for, and the one the positional
        # comparison could only refuse as *not separable by this method*. The
        # edit is over the keys both images carry; the addition is reported
        # beside it; neither is inferred from the other.
        answer = self._compare(index(("fix.csv", "the mark label"),
                                     ("other.csv", "unchanged")),
                               index(("fix.csv", "the reworded label"),
                                     ("other.csv", "unchanged"),
                                     ("new.csv", "a new row")))
        self.assertIsNone(answer.refusal)
        self.assertEqual([(e.key, e.before, e.after) for e in answer.edits],
                         [("`fix.csv`", "the mark label", "the reworded label")])
        self.assertEqual([(s.direction, s.key) for s in answer.one_sided],
                         [(keyed.ADDED, "`new.csv`")])

    def test_a_row_on_one_side_only_is_reported_with_the_cell_that_exists(self):
        answer = self._compare(index(("gone.csv", "a row that went away")),
                               index(("kept.csv", "a row that stayed")))
        self.assertIsNone(answer.refusal)
        self.assertEqual(answer.edits, [])
        self.assertEqual(len(answer.one_sided), 2)
        removed, added = answer.one_sided
        self.assertEqual((removed.direction, removed.key, removed.cell),
                         (keyed.REMOVED, "`gone.csv`", "a row that went away"))
        self.assertEqual((added.direction, added.key, added.cell),
                         (keyed.ADDED, "`kept.csv`", "a row that stayed"))
        # Removals first, then additions, each in its own image's order.
        self.assertEqual([s.direction for s in answer.one_sided],
                         [keyed.REMOVED, keyed.ADDED])

    def test_a_removed_and_an_added_key_are_two_rows_and_never_one_edit(self):
        # The rename rule this module declines. Pairing a key that went with a
        # key that arrived is a judgement about which row became which, and the
        # key is precisely what cannot answer it. Two rows, each with the cell
        # that exists, so a reader can make the pairing themselves.
        answer = self._compare(index(("old.asm", "the pointer it named")),
                               index(("new.asm", "the pointer it names now")),
                               column=NESTED, root=False)
        self.assertIsNone(answer.refusal)
        self.assertEqual(answer.edits, [])
        self.assertEqual([(s.direction, s.key) for s in answer.one_sided],
                         [(keyed.REMOVED, "`old.asm`"),
                          (keyed.ADDED, "`new.asm`")])
        # Both cells survive, which is what keeps #746's evidence readable.
        self.assertEqual([s.cell for s in answer.one_sided],
                         ["`old.asm`", "`new.asm`"])

    def test_a_first_column_only_change_is_a_key_change_not_a_description_edit(self):
        # A `File` cell is the key, so renaming a fixture moves the key and is
        # reported as one key removed and one added -- never as the description
        # cell having changed.
        answer = self._compare(index(("fix.csv", "the mark label")),
                               index(("renamed.csv", "the mark label")))
        self.assertEqual(answer.edits, [])
        self.assertEqual([(s.direction, s.key) for s in answer.one_sided],
                         [(keyed.REMOVED, "`fix.csv`"),
                          (keyed.ADDED, "`renamed.csv`")])

    def test_a_reworded_sentence_is_an_edit_even_with_the_literals_kept(self):
        # The comparison is about the cell, not the backticked literals inside
        # it, for `measure_index_repair_visibility.repair_rows()`'s reason: a
        # reworded sentence that keeps every literal is still an edit, and an
        # implementation keyed on addresses would report nothing here.
        answer = self._compare(index(("fix.csv", "the label `0x0751` everywhere")),
                               index(("fix.csv", "the label `0x0751`, everywhere")))
        self.assertEqual(len(answer.edits), 1)

    def test_a_reorder_is_not_an_edit(self):
        # Both images carry the same keys reading the same, so nothing was
        # changed -- but the column read in order is not byte-identical, which
        # is why `census_index_third_column_edits.py`'s `unchanged` reason says
        # what it measured rather than claiming byte-identity. This case is the
        # difference between those two claims.
        answer = self._compare(index(("a.csv", "first"), ("b.csv", "second")),
                               index(("b.csv", "second"), ("a.csv", "first")))
        self.assertEqual(answer.edits, [])
        self.assertEqual(answer.one_sided, [])
        self.assertIsNone(answer.refusal)

    def test_the_two_key_set_sizes_come_back_with_the_comparison(self):
        # So a caller can say which way the move went without reading the images
        # a second time -- and the direction is only decidable from the sizes.
        answer = self._compare(index(("a.csv", "one")), index(("a.csv", "one"),
                                                                ("b.csv", "two")))
        self.assertEqual((answer.before_rows, answer.after_rows), (1, 2))


class RefusalTests(unittest.TestCase):
    """The three cases a key cannot settle, each refused with its own reason.

    Every negative here is "not read by this method". A refusal that said only
    *that* would leave a reader unable to say which defect to go and look for, so
    each names itself -- and none of them is a silent skip.
    """

    def test_the_same_key_twice_in_one_image_is_refused_and_says_so(self):
        # A dict would keep one row and drop the other, and the comparison would
        # then be over a row that was never in the image. The reason names the
        # key, so the row that collided is findable rather than merely counted.
        text = index(("fix.csv", "one row"), ("fix.csv", "the same key again"))
        rows, why = keyed.keyed_rows(text, ROOT, root=True)
        self.assertEqual(rows, [])
        self.assertIn("appears twice", why)
        self.assertIn("`fix.csv`", why)
        self.assertIn("not read by this method", why)

    def test_a_duplicate_key_in_the_nested_population_is_refused_too(self):
        # The nested key has to be unique across the whole file, and the guard
        # is per image rather than assumed. Two tables, one shared path.
        text = ("# scratch\n\n" + NESTED_HEADER + "| `a.asm` | one |\n\n"
                + NESTED_HEADER + "| `a.asm` | and again |\n")
        rows, why = keyed.keyed_rows(text, NESTED, root=False)
        self.assertEqual(rows, [])
        self.assertIn("appears twice", why)

    def test_an_empty_key_cell_is_refused_and_says_so(self):
        # A blank key has no identity: it matches nothing on the other side and
        # every blank key matches every other one, so both the intersection and
        # the leftovers would be fiction. Spelled as a genuinely empty cell --
        # an empty string between backticks is `` `` ``, which is not empty.
        rows, why = keyed.keyed_rows(
            index(raw=["| `fix.csv` | `../grade.py` | a row |\n",
                       "|  | `../grade.py` | a row with no name |\n"]),
            ROOT, root=True)
        self.assertEqual(rows, [])
        self.assertIn("empty first cell", why)
        self.assertIn("not read by this method", why)

    def test_a_row_with_no_measured_cell_is_refused_and_says_so(self):
        # `table_cells()` drops a row that has no cell in the column asked for,
        # so a table holding one short row yields more keys than cells -- and
        # zipping those two lists would compare one row's key against a
        # different row's cell. The refusal is what stops that reaching a report
        # as an edit.
        rows, why = keyed.keyed_rows(
            index(raw=["| `fix.csv` | `../grade.py` | a row |\n",
                       "| `short.csv` | `../grade.py` |\n"]),
            ROOT, root=True)
        self.assertEqual(rows, [])
        # The reason is worded from the two counts, because the root branch reads
        # the table through `table_cells()`, which drops the short row rather
        # than reporting how wide it was -- so it cannot name the row.
        self.assertIn("2 key(s) in column 1 but 1 cell(s) in column 3", why)
        self.assertIn("no cell in the column being read", why)

    def test_a_short_nested_row_is_refused_by_its_table_and_row(self):
        # The nested population is read in column 1, and a two-column table's
        # row carrying only its first cell is short of the *second* column --
        # which this population never reads. So the refusal fires when the
        # measured column is the one that is absent, and this is what it says.
        rows, why = keyed.keyed_rows(
            "| file / row | what it pins |\n|---|---|\n"
            "| `a.asm` | one |\n| `b.asm` |\n", 2, root=False)
        self.assertEqual(rows, [])
        self.assertIn("table 1, row 2", why)
        self.assertIn("column 2", why)

    def test_a_refusal_names_which_image_it_came_from(self):
        # Two images, one of them broken: the refusal says which, because "this
        # pair is not comparable" and "this half is not readable" are different
        # facts and only the second is a defect in the tree.
        answer = keyed.compare(
            index(raw=["| `a.csv` | `../grade.py` | one |\n",
                       "|  | `../grade.py` | a row with no name |\n"]),
            index(("a.csv", "one")), column=ROOT, root=True)
        self.assertIsNotNone(answer.refusal)
        self.assertIn("before image", answer.refusal)
        self.assertEqual(answer.edits, [])
        self.assertEqual(answer.one_sided, [])


class CommittedImageTests(unittest.TestCase):
    """This repository's own indexes, read by the reader the census reads them with.

    **Never how many.** What is asserted is the property the file-level nested
    comparison rests on -- every key unique, no key empty, every row carrying a
    cell in the column it is read in -- and it is a property of the images, not
    a count of them. A census over the history moves the moment a row is added,
    and a case that pinned a number would fail then and say the reader broke.
    """

    def _index(self, name, column, root):
        path = REPO / "docs" / ".." / name
        rows, why = keyed.keyed_rows(path.resolve().read_text(encoding="utf-8"),
                                     column, root)
        self.assertIsNone(why, f"{name}: {why}")
        return rows

    def test_the_root_index_keys_are_unique_and_never_empty(self):
        rows = self._index("ec/tools/testdata/README.md", ROOT, root=True)
        self.assertTrue(rows, "the committed root index read as no rows at all")
        keys = [row.key for row in rows]
        self.assertEqual(len(keys), len(set(keys)),
                         "a duplicate `File` cell in the committed root index")
        self.assertNotIn("", keys, "an empty `File` cell in the committed root index")

    def test_every_committed_index_keys_are_unique_and_never_empty(self):
        # The nested precondition, over every self-indexed index in the tree
        # rather than the one this repository had when the census was written --
        # a new self-indexed directory needs no edit here, which is the same
        # argument `check_testdata_index.py`'s self-indexed clause makes.
        indexes = sorted((REPO / "ec" / "tools" / "testdata").glob("*/README.md"))
        self.assertTrue(indexes, "no nested index is committed under testdata/")
        for path in indexes:
            with self.subTest(index=path.parent.name):
                rows, why = keyed.keyed_rows(
                    path.read_text(encoding="utf-8"), NESTED, root=False)
                self.assertIsNone(why, why)
                keys = [row.key for row in rows]
                self.assertEqual(len(keys), len(set(keys)),
                                 f"a duplicate first-column cell in {path.name}")
                self.assertNotIn("", keys,
                                 f"an empty first-column cell in {path.name}")

    def test_the_committed_indexes_read_without_going_through_the_emptiness(self):
        # The precondition behind the census's own `located()` guard, held here
        # as a property: the readers find rows in the committed tree. A run of
        # the comparison over two real images would then compare something.
        root_rows = self._index("ec/tools/testdata/README.md", ROOT, root=True)
        nested_rows = self._index("ec/tools/testdata/call-graph/README.md",
                                  NESTED, root=False)
        self.assertTrue(root_rows)
        self.assertTrue(nested_rows)
        answer = keyed.compare(
            (REPO / "ec/tools/testdata/README.md").read_text(encoding="utf-8"),
            (REPO / "ec/tools/testdata/README.md").read_text(encoding="utf-8"),
            column=ROOT, root=True)
        self.assertEqual(answer.edits, [])
        self.assertEqual(answer.one_sided, [])
        self.assertIsNone(answer.refusal)


if __name__ == "__main__":
    unittest.main()