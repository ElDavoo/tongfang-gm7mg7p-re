#!/usr/bin/env python3
"""Offline checks for check_pin_table_rows.py: a scratch tree and the committed one.

The tool this suite covers reconciles the write-up's per-pin table against the
census's own run, so the failure mode it has to not have is the one every
pointer-checker in this tree has: **silence**. A row whose citing line has
quietly moved is a row that still reads as a perfectly normal row, which is
the shape of defect this repository has already paid for by hand four times --
#930 re-registered one, #891 two, #889's note two more -- and the whole cost
was a human re-reading `--verbose` against 105 rows.

The five cases the issue names are here first, one per way it can fail: a row
whose citing line moved, a row whose shape changed under it, a record with no
row, a row with no record, and a run that placed nothing. The rest are the
cases a loosened version would let through, and they are the ones that matter
most:

  * **exit 0 on a tree where every verdict is wrong.** The standing. A
    reconciler that reddened on a verdict would be the checker
    `docs/findings/test-line-pin-census.md`'s `*Why no checker*` declines to
    ship, and it would redden on sentences that are true. The tool never reads
    that cell, so this is a claim about the code and a case that would catch
    the cell being read.
  * **both citing-cell spellings, and the `†` marker.** 104 rows write the
    line outside the link and one writes it inside the code span, so a reader
    handling only the first reports the whole table unparsed -- and one that
    silently skipped what it could not parse would place nothing and pass.
  * **the `beside` abbreviation, an unknown read cell, a duplicate key.** The
    first is the table's own spelling, the second has to fail rather than pass
    as "close enough", and the third is the ambiguity `ambiguous-path` exists
    for: a key two rows or two records share is reported, not taken from the
    first.

`test_path_differs_fires_when_the_record_and_the_row_disagree` is the one
white-box case, and it is here because of a measurement rather than a
hypothesis: on a placed row `path-differs` is an identity, because a record's
`path` has exactly one source and the match key pins both of its inputs. The
class is kept -- it is the assertion that fires if `census.resolve()` stops
being a pure function -- and a class that can only be exercised by a tree that
cannot occur is a class nothing has tested. This case hands `compare_row()` a
record the run could not have produced and watches the class fire.

The fixtures are small enough to write inline, so each case reads as the error
it is about. They are not the real rows but they are the real shapes: the
`by-path`/`by-name`/`beside` split, the `../tools/…` path written relative to
the citing file, the em dash a declined row carries, the fenced transcript, and
the two spellings of the citing cell. The last class is the real thing, and it
is what says the table's own size rather than leaving the write-up's 105 as
another unpinned figure.
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
    "check_pin_table_rows", HERE / "check_pin_table_rows.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

census = check.census

# The table's own header, read from the tool rather than retyped, so a change
# to it is a change to the fixture rather than a fixture that stopped matching
# what the tool looks for. Everything else in this file is written out longhand
# on purpose: a case that read its expectations out of the code it is checking
# would agree with any change to it.
HEADER = check.TABLE_HEADER
SEPARATOR = "|---|---|---|---|---|"
DOC = census.SELF_DOC

# A four-cell row, the shape every case here starts from, and the target file
# the census resolves it to. The second line is an assertion so the shape is
# `assertion`; a case that wants another shape changes the target, not the row.
ROW = "| `a.md:1` | `ec/tools/test_a.py:2` | by-path | assertion | carries |"
TARGET = "one\n        self.assertEqual(1, 1)\n"
CITE = "`ec/tools/test_a.py:2`\n"


def table(*rows):
    """The write-up as a scratch tree's census file: a header and some rows."""
    return "\n".join([HEADER, SEPARATOR, *rows]) + "\n"


def tree(files):
    """A scratch repository holding `files`, as {relpath: text}.

    Built per call rather than shared, so a case that mutates a file mutates
    its own tree. The census reads the tree it is handed rather than
    `git ls-files`, and this tool reads `--root`, which is what makes this
    possible at all.
    """
    root = tempfile.mkdtemp(prefix="check-pin-table-rows-")
    for rel, text in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return root


def green(**overrides):
    """A tree whose table and run agree, with the given files replaced.

    The one reconciler a case is about is the one that is green: a fixture that
    drifted would make every other case in this file assert something about a
    defect it did not build.
    """
    files = {DOC: table(ROW), "a.md": CITE, "ec/tools/test_a.py": TARGET}
    files.update(overrides)
    return files


def problems_of(root):
    """The `(class, where, detail)` triples `reconcile()` found in `root`."""
    return check.reconcile(root)[3]


def classes_of(root):
    """{class: count} over a reconciliation, every class present.

    The zeros are kept rather than dropped, so a case can compare the whole
    vocabulary: a rule that stopped firing reads as a missing key, and a dict
    over the tool's own `CLASSES` says so as a diff.
    """
    counted = {}
    for kind, _where, _detail in problems_of(root):
        counted[kind] = counted.get(kind, 0) + 1
    return {kind: counted.get(kind, 0) for kind in check.CLASSES}


def run_main(root, *argv):
    """(exit code, stdout, stderr) for a run over `root`, streams captured."""
    err, out, saved = io.StringIO(), io.StringIO(), sys.argv
    sys.argv = ["check_pin_table_rows.py", "--root", str(root), *argv]
    try:
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            rc = check.main()
    finally:
        sys.argv = saved
    return rc, out.getvalue(), err.getvalue()


class RowParseTests(unittest.TestCase):
    """How a row is read, which is the reader's whole population.

    Without these the reconciler is a regex with no stated scope, and the scope
    is the part a reader has to be able to check: which spellings of the
    citing cell exist in the committed table, and what a row of the wrong
    arity is.
    """

    def test_the_citing_cell_is_read_in_both_spellings_the_table_writes(self):
        # 104 rows write [`path](path) with the line outside the link and one
        # writes `path:NNN` with it inside the code span. A reader that took
        # only the first reports the whole committed table unparsed, which
        # looks like a broken write-up rather than a half-spelled column.
        linked = check.read_citing("[`a.md`](a.md):12")
        spanned = check.read_citing("`docs/agent-pipeline.md:345`")
        self.assertEqual(linked, ("a.md", 12, ""))
        self.assertEqual(spanned, ("docs/agent-pipeline.md", 345, ""))

    def test_the_dagger_is_kept_and_the_line_it_marks_is_still_read(self):
        # One committed row carries it, and it marks the row the write-up is
        # superseding. Dropping it would name a different row than the message
        # is about, and refusing the row would report 104 of 105 as unreadable.
        self.assertEqual(check.read_citing("[`a.md`](a.md):7191 †"),
                         ("a.md", 7191, "†"))

    def test_a_citing_cell_in_neither_spelling_is_not_a_citing_cell(self):
        self.assertIsNone(check.read_citing("see a.md:1"))
        self.assertIsNone(check.read_citing("[`a.md`](a.md)"))

    def test_the_target_cell_splits_its_path_from_its_line_or_span(self):
        # `rsplit(":", 1)`, which is the split `census.report()` uses on a
        # record's own spelling, so the path half is what `census.resolve()`
        # gets and the half it is asking about is the same half the census had.
        self.assertEqual(check.read_target("`ec/tools/test_a.py:3-6`"),
                         ("ec/tools/test_a.py", "3-6"))
        self.assertEqual(check.read_target("`./ec/tools/test_a.py:3`"),
                         ("./ec/tools/test_a.py", "3"))
        self.assertIsNone(check.read_target("`ec/tools/test_a.py`"))

    def test_the_separator_row_is_not_a_row(self):
        # It is the one `|`-prefixed line in the table that is not a row, and
        # counted as one it is a five-cell row of dashes whose cells name no
        # shape the census emits -- a failure invented by the reader.
        rows = check.find_table(table(ROW).split("\n")[:-1])
        self.assertEqual([at for at, _cells in rows], [3])

    def test_a_row_that_lost_a_cell_is_reported_and_not_skipped(self):
        # Four cells means the row has no verdict cell, so this tool cannot say
        # which column drifted. It says that, rather than reading a shape out
        # of the verdict or dropping the row and going quiet about it.
        found = problems_of(tree(green(**{DOC: table("| `a.md:1` | "
                                                      "`ec/tools/test_a.py:2` "
                                                      "| by-path | assertion |")})))
        self.assertEqual([kind for kind, _w, _d in found],
                         [check.UNPARSED, check.NO_ROW])
        self.assertIn("4 cell(s)", found[0][2])

    def test_the_table_is_found_by_its_header_and_by_nothing_else(self):
        # The whole reason the tool does not pin its own table's line numbers:
        # a paragraph inserted above the table moves every row, and a checker
        # invalidated by that is invalidated by the class of edit it exists to
        # catch.
        root = tree(green(**{DOC: "## The per-pin table\n\n" + table(ROW)}))
        self.assertEqual(check.reconcile(root)[2], 1)

    def test_two_headers_are_reported_rather_than_one_of_them_chosen(self):
        # A write-up that grew a second table leaves the location ambiguous,
        # and picking the first would measure whichever pair of rows happened
        # to come first.
        rc, _out, err = run_main(tree({DOC: table(ROW) + "\n" + table(ROW),
                                       "a.md": CITE,
                                       "ec/tools/test_a.py": TARGET}))
        self.assertNotEqual(rc, 0)
        self.assertIn("2 line(s)", err)


class ReconcileTests(unittest.TestCase):
    """The five ways this can fail, one case each -- the issue's own list.

    Each of these is a tree the committed one is not, built by moving one
    thing: a line, a shape, a row, a record. What a merge does to a 105-row
    table is one of exactly these.
    """

    def test_a_row_whose_citing_line_moved_is_reported_on_both_sides(self):
        # The defect this whole issue exists for, and the one #930 paid for by
        # hand: a paragraph lands above the citing line, the row still names the
        # old one, and the row still reads as an ordinary row. Both halves fire
        # -- the row has no record, and the record has no row -- because a
        # drifted row is a pair of facts rather than one.
        moved = green()
        moved["a.md"] = "a paragraph landed above the pin\n" + CITE
        found = classes_of(tree(moved))
        self.assertEqual(found[check.UNPLACED], 1)
        self.assertEqual(found[check.NO_ROW], 1)

    def test_the_unplaced_message_names_the_line_the_run_did_read(self):
        moved = green()
        moved["a.md"] = "a paragraph landed above the pin\n" + CITE
        _t, records, placed, problems, _u = check.reconcile(tree(moved))
        self.assertEqual(placed, 0)
        self.assertEqual(len(records), 1)
        unplaced = [p for p in problems if p[0] == check.UNPLACED][0]
        self.assertIn("a.md:1", unplaced[1])
        self.assertIn("a.md:2", problems[1][1])

    def test_a_row_whose_shape_changed_under_it_is_reported(self):
        # A cited line that stops being an assertion and becomes a comment
        # above the assertion it was cited for. The table is still describing
        # the run's *resolution* perfectly here -- same file, same line -- so
        # this is the only class that can see it, and it is the reason the
        # shape column is in the table at all.
        found = classes_of(tree(green(**{"ec/tools/test_a.py":
                                          "one\n        # the case is here\n"})))
        self.assertEqual(found[check.SHAPE_DIFFERS], 1)
        _t, _r, placed, problems, _u = check.reconcile(
            tree(green(**{"ec/tools/test_a.py": "one\n        # a comment\n"})))
        self.assertEqual(placed, 1)
        self.assertIn("'assertion'", problems[0][2])
        self.assertIn("'comment'", problems[0][2])

    def test_a_record_with_no_row_is_reported(self):
        # A pin added to a markdown file and no row written for it. The table
        # then under-reports the class, which is a quieter failure than a stale
        # row because nothing in the table looks wrong -- there is simply
        # nothing there.
        found = classes_of(tree(green(**{DOC: table()})))
        self.assertEqual(found[check.NO_ROW], 1)
        self.assertEqual(found[check.UNPLACED], 0)

    def test_a_row_with_no_record_is_reported(self):
        # A row added for a pin that is not in the run: a transcription from
        # an earlier tree, or a row for a line that has stopped being a pin.
        found = classes_of(tree(green(**{DOC: table(
            ROW,
            "| `a.md:9` | `ec/tools/test_a.py:2` | by-path | assertion | "
            "carries |")})))
        self.assertEqual(found[check.UNPLACED], 1)
        self.assertEqual(found[check.NO_ROW], 0)

    def test_a_run_that_placed_nothing_reports_rather_than_returning_clean(self):
        # The vacuous-pass guard, and the one the census's own docstring makes
        # the same way: a check that located nothing has to be visible in the
        # exit code, because "checked nothing" and "found nothing wrong" are
        # the same run from the outside. A header with no rows under it and a
        # census with no pins to match is the tree that produces it.
        rc, out, err = run_main(tree({DOC: table()}))
        self.assertNotEqual(rc, 0)
        self.assertIn("no row was placed", err)
        self.assertIn("0 placed", out)


class StandingTests(unittest.TestCase):
    """What a loosened version would let through.

    These are the cases the tool's own docstring makes a claim about, so each
    one is the claim as an assertion rather than as prose.
    """

    WRONG = "| `a.md:1` | `ec/tools/test_a.py:2` | by-path | assertion | " \
            "**not one word of this is true** |"

    def test_a_tree_where_every_verdict_is_wrong_still_exits_zero(self):
        # The standing, and the reason this is not the checker
        # `docs/findings/test-line-pin-census.md` declines to ship. It renders
        # no verdict, so the reading stays a reading somebody looked at, and
        # `docs/findings/test-line-repoint-563.md`'s "carries is a reading, and
        # it is a reading somebody looked at" stays true.
        rc, out, _err = run_main(tree(green(**{DOC: table(self.WRONG)})))
        self.assertEqual(rc, 0)
        self.assertIn("1 placed", out)

    def test_the_verdict_cell_is_never_read_at_all(self):
        # The standing from the other side: a table whose verdict cells have
        # been emptied, which is what "never read" has to mean if it is to
        # mean anything. A reader that indexed the cell would trip over the
        # missing one.
        rc, _out, _err = run_main(tree(green(**{DOC: table(
            "| `a.md:1` | `ec/tools/test_a.py:2` | by-path | assertion |  |")})))
        self.assertEqual(rc, 0)

    def test_the_beside_abbreviation_is_honoured(self):
        # The table writes `beside` where the census writes
        # `beside-the-citing-file`, in the two rows that need it. A naive
        # equality check reddens on a correct tree, and normalising the two
        # cells in the table instead would edit a shared, actively churning
        # file for a cosmetic reason.
        found = classes_of(tree({
            DOC: table("| [`a.md`](a.md):1 | `../tools/test_a.py:2` | beside "
                       "| assertion | carries |"),
            "docs/findings/a.md": "`../tools/test_a.py:2`\n",
            "ec/tools/test_a.py": TARGET,
        }))
        self.assertEqual(found, {kind: 0 for kind in check.CLASSES})

    def test_a_read_cell_the_census_never_emitted_is_reported(self):
        # And the other half of the same rule. A cell this cannot read is a
        # cell it cannot check, so a fourth spelling has to fail rather than
        # slip through as "close enough" -- which is what a `.get(cell,
        # cell)` against a default would have done.
        found = classes_of(tree(green(**{DOC: table(
            "| `a.md:1` | `ec/tools/test_a.py:2` | sideways | assertion | "
            "carries |")})))
        self.assertEqual(found[check.READ_DIFFERS], 1)
        _t, _r, _p, problems, _u = check.reconcile(tree(green(**{DOC: table(
            "| `a.md:1` | `ec/tools/test_a.py:2` | sideways | assertion | "
            "carries |")})))
        self.assertIn("not a read kind the census emits at all", problems[0][2])

    def test_a_declined_row_is_matched_on_the_em_dash_the_table_writes(self):
        # The census records `-` for a declined record's read kind and shape;
        # the table writes an em dash. 32 of the 105 committed rows are
        # declined transcripts, so reading the dash as an unknown cell would
        # redden a third of a correct tree.
        found = classes_of(tree({
            DOC: table("| `a.md:2` | `ec/tools/test_a.py:2` | — | — | "
                       "**declined** (fenced) |"),
            "a.md": "```console\n$ grep -n x ec/tools/test_a.py:2\n```\n",
            "ec/tools/test_a.py": TARGET,
        }))
        self.assertEqual(found, {kind: 0 for kind in check.CLASSES})

    def test_a_duplicate_row_key_is_reported_rather_than_taken_from_the_first(self):
        # The ambiguity `ambiguous-path` exists for, in the row direction. Two
        # rows carrying one key is a table that has been copied, and taking the
        # first would leave the second silently unchecked.
        found = classes_of(tree(green(**{DOC: table(ROW, ROW)})))
        self.assertEqual(found[check.DUPLICATE], 1)
        self.assertEqual(found[check.UNPLACED], 0)
        self.assertEqual(found[check.NO_ROW], 0)

    def test_a_row_the_reader_cannot_parse_is_reported_and_not_skipped(self):
        # The half of the two-spellings problem that a forgiving reader gets
        # wrong. Skipping an unparsed row leaves the record it should have
        # matched with no row, which reads as a census that lost a pin rather
        # than a table that grew a third spelling.
        found = classes_of(tree(green(**{DOC: table(
            "| see a.md:1 | `ec/tools/test_a.py:2` | by-path | assertion | "
            "carries |")})))
        self.assertEqual(found[check.UNPARSED], 1)
        self.assertEqual(found[check.NO_ROW], 1)

    def test_a_citing_path_that_resolves_by_neither_naming_is_reported(self):
        # A wrong directory prefix and a deleted file look identical from an
        # exit code and have opposite fixes, so the message has to name both
        # readings the resolver tried and the one file of that name in the
        # tree. This is the census's own `resolve()` rule, applied to the
        # citing side.
        found = problems_of(tree(green(**{DOC: table(
            "| `sub/a.md:1` | `ec/tools/test_a.py:2` | by-path | assertion | "
            "carries |")})))
        kinds = [kind for kind, _w, _d in found]
        self.assertIn(check.UNPARSED, kinds)
        detail = [d for k, _w, d in found if k == check.UNPARSED][0]
        self.assertIn("docs/findings/sub/a.md", detail)
        self.assertIn("the only file of that name in the tree is a.md", detail)


class PathClassTests(unittest.TestCase):
    """`path-differs`, which is an identity on a placed row and is kept anyway.

    Measured rather than assumed: a record's `path` comes from
    `census.resolve()` and from nowhere else, the match key pins both of that
    function's inputs, and so on a placed row the re-derivation cannot differ.
    The class is worth keeping for the one thing it still catches -- a
    `census.resolve()` that stops being a pure function of its inputs, which
    nothing else here would notice -- and it needs a case of its own, because
    a check only ever exercised by a tree that cannot occur is a check nothing
    has tested.
    """

    CELLS = ["`a.md:1`", "`ec/tools/test_a.py:2`", "by-path", "assertion", "x"]

    def compare(self, record, root):
        """`compare_row()` over `record`, with the resolver's real inputs."""
        files, index = census.suites(root)
        return check.compare_row(record, self.CELLS, "t.md:3", "a.md:1",
                                 "ec/tools/test_a.py", "a.md", index, files)

    def test_a_record_carrying_another_path_is_reported(self):
        root = tree(green())
        records, _f = census.census(root)
        doctored = records[0][:4] + ("ec/tools/test_elsewhere.py",) + records[0][5:]
        found = self.compare(doctored, root)
        self.assertEqual([kind for kind, _w, _d in found], [check.PATH_DIFFERS])
        self.assertIn("ec/tools/test_a.py", found[0][2])

    def test_a_record_carrying_its_own_path_is_not_reported(self):
        # The other half, and the one the committed tree runs 105 times: with
        # nothing doctored there is nothing to report, which is the identity
        # the class comment above is about.
        root = tree(green())
        records, _f = census.census(root)
        self.assertEqual(self.compare(records[0], root), [])

    def test_the_committed_tree_reports_no_path_difference(self):
        # Held from the tree's own side rather than only from the white-box
        # case, so a change that made every row unplaceable could not be read
        # as a green path class.
        self.assertEqual(classes_of(check.REPO)[check.PATH_DIFFERS], 0)


class RunTests(unittest.TestCase):
    """The run's contract: the exit code, and every figure it prints.

    These drive `main()` with argv against a scratch tree, because the exit
    code and the lines it prints are the tool's whole output surface -- a rule
    that located nothing has to be visible there and not in a return value
    nobody calls.
    """

    def test_a_green_tree_exits_zero_and_prints_every_class(self):
        rc, out, _err = run_main(tree(green()))
        self.assertEqual(rc, 0)
        self.assertIn("1 table row(s) against 1 census record(s)", out)
        for kind in check.CLASSES:
            with self.subTest(kind=kind):
                self.assertIn(f"0 {kind}", out)

    def test_a_missing_table_header_reports_and_exits_non_zero(self):
        # The write-up renamed its columns, or the table was cut. Either way a
        # run that found no header and passed would be a check that checked
        # nothing for as long as the file stayed that way. The message carries
        # the header it looked for, because a renamed column is a one-word fix
        # and a reader should not have to go and read the file to find it.
        rc, _out, err = run_main(tree(green(**{DOC: "## The per-pin table\n"})))
        self.assertNotEqual(rc, 0)
        self.assertIn("0 line(s)", err)
        self.assertIn(HEADER, err)

    def test_a_write_up_that_cannot_be_read_reports_and_exits_non_zero(self):
        rc, _out, err = run_main(tree({"a.md": CITE, "ec/tools/test_a.py": TARGET}))
        self.assertNotEqual(rc, 0)
        self.assertIn("could not be read", err)

    def test_the_run_says_it_read_no_verdict(self):
        # Otherwise the summary reads as a pass rate over the table, and a
        # reader who has not been told the other half is a human reading takes
        # "105 placed" as 105 pins that are right.
        _rc, out, _err = run_main(tree(green()))
        self.assertIn("no verdict cell was read", out)
        self.assertIn(DOC, out)

    def test_verbose_names_the_row_the_target_and_both_mechanical_cells(self):
        _rc, out, _err = run_main(tree(green()), "--verbose")
        self.assertIn(f"{DOC}:3", out)
        self.assertIn("a.md:1", out)
        self.assertIn("ec/tools/test_a.py", out)
        self.assertIn("by-path", out)
        self.assertIn("assertion", out)

    def test_a_record_the_run_could_not_resolve_is_counted_not_skipped(self):
        # A pin whose file is not in the tree. The census records a reason in
        # place of a read kind and never reaches the shape rule, so there is
        # nothing for a row to be held to -- and the run says how many rows it
        # left uncompared, so a class that stopped firing reads as a number
        # rather than as a clean run.
        rc, out, _err = run_main(tree(green(**{
            "a.md": "`tools/test_gone.py:1`\n",
            DOC: table("| `a.md:1` | `tools/test_gone.py:1` | by-path | other | "
                       "**does not carry** |")})))
        self.assertEqual(rc, 0)
        self.assertIn("1 row(s) not compared", out)


class TheCommittedTree(unittest.TestCase):
    """The real thing: the committed table, reconciled against the real run.

    The figures below are this file's own measurement of the merged tree, and
    pinning them is what stops `105` from becoming another unpinned figure --
    `doc-figure-pin-audit.md`'s "a pin is a check, not a promise" applied to
    the reconciliation about the pins. They are also the one thing here a
    reader cannot re-derive without running the tool, which is why they are in
    a case and not only in the write-up.
    """

    def test_the_committed_table_reconciles_and_exits_zero(self):
        rc, out, err = run_main(check.REPO)
        self.assertEqual(rc, 0, err)
        self.assertIn("105 table row(s) against 105 census record(s)", out)
        self.assertIn("105 placed", out)

    def test_every_class_is_zero_on_the_committed_tree(self):
        # Not left to a prose figure. Zero is the measurement here -- the
        # table does describe the run today, which is the whole point of the
        # tool: it makes the *next* drift loud rather than the last one silent.
        # A case that only asserted a zero exit would pass on a run that
        # reported nothing at all.
        self.assertEqual(classes_of(check.REPO),
                         {kind: 0 for kind in check.CLASSES})

    def test_the_committed_table_places_something(self):
        # The vacuous-pass guard, held from the other side: a table this could
        # not read would print a clean run of zeroes, and that is the one
        # outcome a report of reconciled-versus-not cannot produce.
        table, records, placed, _problems, _uncompared = check.reconcile(check.REPO)
        self.assertTrue(records)
        self.assertTrue(table)
        self.assertEqual(placed, 105)

    def test_the_committed_read_and_shape_cells_are_the_census_vocabulary(self):
        # The two vocabularies the table's own cells have to be drawn from, and
        # the fact that every committed cell is one of them. A cell outside
        # both is reported rather than passed, so this is also the case that
        # says the alias map has not grown a hole: 52 `by-path`, 19 `by-name`
        # and the two `beside` rows the map exists for, with the 32 declined
        # rows carrying the em dash on both sides.
        read, shape = {}, {}
        for _at, cells in check.reconcile(check.REPO)[0]:
            for at, vocabulary, counts in ((2, check.READ_CELLS, read),
                                           (3, check.SHAPE_CELLS, shape)):
                key = check.canonical(cells[at], vocabulary)
                with self.subTest(cell=cells[at]):
                    self.assertIsNotNone(key)
                counts[key] = counts.get(key, 0) + 1
        self.assertEqual(read, {census.BY_PATH: 52, census.BY_NAME: 19,
                                census.BY_BESIDE: 2, "-": 32})
        self.assertEqual(shape, {census.DEF_TEST: 5, census.ASSERTION: 19,
                                 census.COMMENT: 10, census.BLANK: 6,
                                 census.OTHER: 33, "-": 32})

    def test_the_tool_is_not_in_the_cheap_gate_yet(self):
        # A check nobody runs is the shape of defect #819 was, so the standing
        # is held here rather than left for a reader to assume a gate exists.
        # `.github/` cannot be edited from an agent branch at all; the name
        # appearing there means somebody landed
        # `docs/ci/agent-gates-pin-table-rows.patch` without this being redone,
        # and deleting this case is the visible half of landing it.
        gate = os.path.join(check.REPO, ".github", "scripts", "agent-gates.sh")
        with open(gate, encoding="utf-8") as f:
            self.assertNotIn("check_pin_table_rows.py", f.read())


if __name__ == "__main__":
    unittest.main()
