#!/usr/bin/env python3
"""Compare two index images by their rows' **first-column cells**, not by position.

**The key is the first cell of the row, and it is the identity every other tool
in this directory already resolves from.** `ec/tools/testdata/README.md`'s first
column is `File`, and `check_testdata_index.py` resolves every path a row names
out of it; a nested index's first column is the backticked listing the row is
about. So a keyed comparison asks each row for its own name and matches rows by
that, which is what lets a row addition and a cell edit in the same table be
**two things rather than one refusal**: the edit is found over the keys both
images carry, and the addition is reported beside it, and neither is inferred
from the other's position.

**A positional comparison cannot do this, and the difference is not a detail.**
Row numbers are positions, so with 25 rows on one side and 27 on the other,
every row past the shorter one is a different row on each, and a list of "changed"
rows computed by zipping the two is a list of positions. That is the refusal
`measure_index_repair_visibility.repair_rows()` states on purpose for the pair it
is pointed at, and this module is the other answer to the same question over the
whole population: match over the **intersection** of the two key sets, and report
what is left over as rows present on one side only.

**The two populations are read by two different rules, and that is not an
accident of the code.** The root index's measured cell is its *third* one -- the
description a reader opens the table to read -- while a nested index's tables are
two columns wide and their first column holds a **path**, so its measured cell
*is* its key. The consequences are stated where they bite rather than left for a
reader of a transcript to work out:

  * **A nested pointer change cannot be an edit under a key.** A key that differs
    is by definition not shared, so a nested row whose path was repointed comes
    back as a key removed and a key added, with **both** cells printed -- the
    evidence survives, and the class it lands in does not claim it was an edit
    over a row both images agreed the name of.
  * **A removed key and an added key are two rows, never one edit.** Pairing them
    is a judgement about which row became which, which is the thing a key does
    not know and this tool does not guess. Both are reported, each with the cell
    that exists, so a reader can make the pairing themselves.
  * **A key that is not duplicated is a precondition, not an assumption.** The
    nested keys have to be unique across the whole file for a file-level keyed
    comparison to be the right instrument; `test_index_keyed_rows.py` asserts that
    over the committed images, and the duplicate-key refusal below holds this
    module to it per image rather than leaving it assumed.

**Every case a key cannot settle is refused with a reason, and none is a silent
skip.** A duplicate key, an empty key cell and a row with no cell in the measured
column are each named and each says why the comparison would otherwise be over
something other than what it says it is over. Two further refusals are
**delegated rather than reimplemented**, so this module does not grow a second
copy of either: an image the reader cannot locate is the census's `located()`
guard, asked before this is called; and a revision this clone cannot resolve is
the census's exit-2 branch, which reuses `HISTORY_REQUIREMENT` verbatim so the
two tools cannot disagree about what a clone has to be to answer. **A caller that
has not asked `located()` gets an empty key set and a comparison that found no
difference**, which is the silent zero this whole arrangement exists to prevent --
so it is stated here, in this tool's own words, beside the code that would
silently produce it.

**Nothing here reads a fixture, a capture or an EC image.** It compares two
**texts**, the two `git show <rev>:<path>` outputs the census already reads, so
the direction is the census's: today's text over yesterday's, and no checker is
run over an old tree.

Usage:
    from index_keyed_rows import compare
    answer = compare(before_text, after_text, column=3, root=True)
"""
import collections

# The same readers the census and both checkers use, imported rather than
# copied for the reason the census's own import comment gives: a second reader of
# the same table could come to disagree with the tool it is measuring, and a
# change to what a table is should land in one place. `table_cells()` owns the
# rule for *which* table is the root index's -- the one whose first header cell
# is `HEADER` -- so the root branch below asks it rather than re-spelling that
# test, and only the nested branch, which has no such rule because it reads every
# table in the file, reaches for `markdown_tables()` directly.
from check_testdata_index import (  # noqa: F401
    HEADER, markdown_tables, table_cells)

# The key's column, named rather than left as the `1` a reader would have to
# count to. It is the same column for both populations; what differs is which
# cell is *measured*, and that is the caller's argument.
KEY_COLUMN = 1

# The direction vocabulary for a row present on one side only. Two words rather
# than a boolean, because which side a row is missing from is the whole content
# of the finding and a bare `True` would send a reader back to the code to learn
# which is which.
ADDED = "added"
REMOVED = "removed"

# One row of one image: `where` locates it for a report without being its
# identity, `key` is its identity, `cell` is what this tool compares. The
# separation is deliberate -- a row number is a position, and a report that
# printed one beside a keyed result would invite reading the two as the same
# row number on both sides, which is exactly what this module stops assuming.
Row = collections.namedtuple("Row", "where key cell")

# A key both images carry whose measured cell differs. `where` is the row's
# place in the **after** image -- the state the revision left behind, and so the
# one a reader holding the file can go and look at.
Edit = collections.namedtuple("Edit", "where key before after")

# A key one image carries and the other does not. `cell` is the cell that
# **exists** -- the only one there is, the other side having no row to hold it --
# and `direction` says which side it is missing from.
Side = collections.namedtuple("Side", "direction where key cell")

# The whole of one comparison: what was measured, what was left over, and the
# refusal when there is nothing to report because a key could not settle the
# question. `edits` and `one_sided` are both populated when a revision did both,
# which is the case a positional method could only refuse; `refusal` is set
# instead of either, never beside them.
#
# `before_rows` and `after_rows` are the two key sets' sizes, carried so a caller
# can say which way the move went without reading the images a second time. They
# are sizes of **key sets**, which is what changed, and not the row count of any
# one table -- the two happen to agree here because a key is one row, and they
# would stop agreeing the moment a key ever stood for more.
Comparison = collections.namedtuple(
    "Comparison", "edits one_sided refusal before_rows after_rows")


def _short(where, have, column):
    """The refusal for a row with no cell in the column being read.

    `where` names the row and `have` is how many cells it actually has, which is
    something the nested branch knows because it reads the row. **The root branch
    cannot say that** -- it reads the table through `table_cells()`, which drops
    the short row rather than reporting it -- so it passes a count of the *rows
    it did get* and words its own refusal; see `keyed_rows()`.
    """
    return ("%s has %d cell(s) and the cell read here is column %d, so the row "
            "has nothing to compare; reading the rows beside it would pair one "
            "row's key with another row's cell and call the difference an edit. "
            "the edits are not read by this method" % (where, have, column))


def _checked(rows):
    """-> ([Row], None), or ([], why) if a key cannot identify these rows.

    The two guards that make a dictionary the wrong tool here, stated once and
    applied to both populations:

      * **the same key twice in one image.** A dict keyed on the first cell would
        keep one row and silently drop the other, and the comparison would then be
        over a row that was never in the image. Which of the two it kept would be
        the dict's business rather than the reader's, so this refuses instead.
      * **an empty first cell.** A blank key has no identity: it matches nothing
        on the other side, and every blank key matches every other blank key, so
        both the intersection and the leftovers would be fiction.

    Neither shape is one the committed indexes have. Both are shapes a hand-edited
    index can have, and this is a tool that reads the history of hand-edited
    indexes.
    """
    seen = {}
    for number, row in enumerate(rows, 1):
        if not row.key:
            return [], ("row %d of the image has an empty first cell, so it has "
                        "no identity to be compared by: a blank key matches "
                        "nothing on the other side and every blank key matches "
                        "every other one. the edits are not read by this method"
                        % number)
        if row.key in seen:
            return [], ("the key `%s` appears twice in the image, at row %d and "
                        "row %d, so keeping one row per key would drop one of "
                        "them and the comparison would be over a row that was "
                        "never in the image. the edits are not read by this "
                        "method" % (row.key, seen[row.key], number))
        seen[row.key] = number
    return rows, None


def keyed_rows(text, column, root):
    """-> ([Row], None) for `text`'s rows keyed by their first cell, or
    ([], why) when a key cannot settle what a row is.

    `column` is the cell to read into each row, counted the way a reader counts
    a table's columns; `root` selects which population's reading applies. For the
    root index that is the one table whose first header cell is `File`, located by
    `table_cells()` rather than by a re-spelling of its rule. For a nested index
    it is **every table in the file**, because a nested index has no header that
    identifies it -- its tables share one -- so the key has to be unique across
    the whole file, which is what `_checked()` holds this to per image.

    The root branch reads the key column and the measured column with two calls
    and compares their lengths. That is not belt and braces: `table_cells()`
    drops a row with no cell in the column asked for, so a table holding one
    short row yields **more** keys than cells, and zipping those two lists would
    compare one row's key against a different row's cell. The two lengths can
    only disagree when some row is missing its measured cell, so the check names
    that rather than letting a misalignment reach the report as an edit.

    **An image this cannot read yields an empty list and no refusal**, which
    compares equal to another empty list and reports no difference. That is the
    silent zero, and the caller's `located()` guard is what stands in front of it;
    see the module docstring.
    """
    if not root:
        rows = []
        for table, (_header, body) in enumerate(markdown_tables(text), 1):
            for position, row in enumerate(body, 1):
                if column > len(row):
                    return [], _short("table %d, row %d" % (table, position),
                                      len(row), column)
                rows.append(Row("table %d, row %d" % (table, position),
                                row[KEY_COLUMN - 1], row[column - 1]))
        return _checked(rows)

    keys = table_cells(text, column=KEY_COLUMN)
    cells = table_cells(text, column=column)
    if len(keys) != len(cells):
        # Worded from the two counts rather than from the short row's own width,
        # which this branch cannot know: `table_cells()` drops the row instead of
        # reporting it, so the only evidence here is that the two lists disagree.
        return [], ("the index's own table yields %d key(s) in column %d but %d "
                    "cell(s) in column %d, so at least one row has no cell in "
                    "the column being read and reading the two side by side "
                    "would pair one row's key with another row's cell. the "
                    "edits are not read by this method"
                    % (len(keys), KEY_COLUMN, len(cells), column))
    return _checked([Row("row %d" % number, key, cell)
                     for number, (key, cell) in enumerate(zip(keys, cells), 1)])


def compare(before_text, after_text, column, root):
    """-> a `Comparison` over two images of one index, keyed on the first cell.

    The whole of the measurement, and the shape the census reports: the shared
    keys whose measured cell differs, the keys present on one side only with the
    cell that exists, or the refusal saying a key could not settle this pair.

    **Rows are matched over the intersection and the leftovers are reported, not
    dropped.** A revision that both adds a row and edits a shared one therefore
    returns **both**: the edit over the keys the two images agree on, and the
    addition beside it. That pair used to be one line saying the two were *not
    separable by this method*, and the difference is the whole of this module.

    A refusal is returned for the cases a key cannot settle and for no others. In
    particular a row present on one side only is **not** a refusal: the tool knows
    which key moved, in which direction, and what the cell that exists says.
    Calling that a refusal would claim the method did not answer when it did, and
    folding it into "nothing changed" would claim the two images agree, which they
    plainly do not.

    **The caller must have asked `located()` first.** See the module docstring.
    """
    images = {}
    for side, text in (("before", before_text), ("after", after_text)):
        rows, refusal = keyed_rows(text, column, root)
        if refusal is not None:
            return Comparison([], [], "the %s image: %s" % (side, refusal), 0, 0)
        images[side] = {row.key: row for row in rows}
    before, after = images["before"], images["after"]

    answer = Comparison([], [], None, len(before), len(after))
    for key, row in before.items():
        other = after.get(key)
        if other is None:
            answer.one_sided.append(Side(REMOVED, row.where, key, row.cell))
        elif other.cell != row.cell:
            answer.edits.append(Edit(other.where, key, row.cell, other.cell))
    for key, row in after.items():
        if key not in before:
            answer.one_sided.append(Side(ADDED, row.where, key, row.cell))
    # Removals come first because a Python dict preserves insertion order and
    # this iterates the before image then the after one, so a revision that
    # dropped rows and a revision that added them both read in the order their
    # own image has them in.
    return answer