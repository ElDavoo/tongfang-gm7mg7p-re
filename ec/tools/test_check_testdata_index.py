#!/usr/bin/env python3
"""Offline checks for check_testdata_index.py: committed files only.

The tool is a pointer-checker, so its failure mode is silence rather than a
crash. Loosen a rule and it stops catching a fixture with no row while still
exiting 0, and the only thing that notices is a reader who has already been
misled -- which is how both of the hand-repairs this tool exists to stop
happened. So what is pinned here is the line between what the tool refuses and
what it waves through: each rule that makes it conservative gets a case saying
so, and each rule that makes it *strict* gets one too, because a checker that
has quietly started accepting everything looks exactly like a checker that is
working.

The fixtures are written inline into a scratch `testdata/` under a temporary
root, which keeps each case readable as the tree and the index beside it rather
than as a diff against a stored pair. The real committed tree is the last class,
and it is what says the index and the tree currently agree.

**Nothing here reads a capture, an EC, or a laptop.** Every path is a
hand-written string in a `tempfile`, and the last class reads two committed
files with `open()`.
"""
import contextlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).parent
# The tool imports nothing of its own, so this is only about finding it; the
# directory is the same sys.path entry its siblings load through.
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_testdata_index', HERE / 'check_testdata_index.py')
ctti = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctti)

HEADER = '| File | Feeds | What it constructs |\n| --- | --- | --- |\n'


class ScratchIndex:
    """A throwaway `testdata/` and the index that is supposed to describe it.

    `row()` and `prose()` build the two things a reader of the real index
    actually has: a table, and eleven paragraphs under it. Both are needed,
    because the committed index names one directory only in prose and the rule
    that finds it is the whole-file search.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.testdata = os.path.join(self.root, "testdata")
        os.mkdir(self.testdata)
        self.rows, self.below = [], ""

    def row(self, cell, feeds='../grade_0751_isolation.py', note='a fixture'):
        """Add one table row naming `cell`, and return the index it is in."""
        self.rows.append(f'| `{cell}` | `{feeds}` | {note} |')
        return self.index

    def prose(self, text):
        """Add a paragraph under the table, as the committed index carries its
        per-directory notes."""
        self.below += text + "\n"
        return self.index

    @property
    def index(self):
        return HEADER + "".join(row + "\n" for row in self.rows) + self.below

    def write(self, rel, text=''):
        """Create `rel` under the scratch `testdata/`, parents and all."""
        path = os.path.join(self.testdata, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def mkdir(self, rel):
        path = os.path.join(self.testdata, rel)
        os.makedirs(path, exist_ok=True)
        return path

    def check(self, index=None):
        """The tool's `Result` for this scratch tree.

        The index is written to disk rather than handed in, because the tool
        reads it from `testdata/README.md` and a case that bypassed that would
        pass against a reader no run ever uses.
        """
        self.write("README.md", self.index if index is None else index)
        return ctti.check(self.testdata)

    def verdicts(self, index=None):
        """(gaps, missing, unresolved) as bare names, for compact assertions."""
        result = self.check(index)
        return ([name for _, name in result.gaps],
                [token for _, token, _ in result.missing],
                [token for _, token, _ in result.unresolved])


class DirectoryReachability(ScratchIndex, unittest.TestCase):
    """Direction 1's line, pinned from both sides of it.

    The first two cases are the issue's first Done criterion and what the
    eleventh fixture directory is about: a directory no index names is a gap.
    The two after them hold the other side, because a rule that refuses
    everything is as useless as one that accepts everything -- a mention in the
    third column is a mention, and a name that is only a *prefix* of a real
    mention is not one.
    """

    def test_a_directory_named_nowhere_is_a_gap(self):
        self.mkdir("0751-isolation-run-scratch")
        self.row("`some-other.csv`")
        self.write("some-other.csv")
        gaps, missing, _ = self.verdicts()
        self.assertEqual((gaps, missing), (["0751-isolation-run-scratch"], []))

    def test_the_prefix_of_another_rows_name_does_not_index_it(self):
        # The sharpest case in the tool, and the reason the trailing slash is
        # required: `0751-isolation-run/` is a prefix of
        # `0751-isolation-run-3blocks/`, so a bare substring test passes the
        # directory that matters most -- §6's set, the one
        # `test_grade_0751_isolation.py` holds equal against that section's
        # file list -- on the strength of a row about a different fixture.
        self.mkdir("0751-isolation-run")
        self.mkdir("0751-isolation-run-3blocks")
        self.write("0751-isolation-run-3blocks/a.csv")
        self.row("`0751-isolation-run-3blocks/*.csv`")
        gaps, missing, _ = self.verdicts()
        self.assertEqual(gaps, ["0751-isolation-run"])
        self.assertEqual(missing, [], "the sibling's own row is fine")

    def test_a_third_column_mention_is_a_mention(self):
        # The search is over the whole index rather than the table, and this is
        # the other half of why: the committed index's own third column
        # cross-references directories this way -- the void-block row says
        # `0751-isolation-run-void-block/` "below is that same void condition"
        # -- so a table-only scan would read a gap on a directory the index does
        # name. It is a weaker mention than a row, which is the trade the
        # whole-file search makes; a directory named in neither a cell nor a
        # paragraph is still a gap, which is the first case in this class.
        self.mkdir("0751-isolation-run-void-block")
        self.mkdir("other")
        self.write("other/a.csv")
        self.row("`other/*.csv`",
                 note='the same void condition `0751-isolation-run-void-block/` has')
        gaps, missing, _ = self.verdicts()
        self.assertEqual((gaps, missing), ([], []))

    def test_a_directory_mentioned_by_a_prefix_only_is_a_gap(self):
        # The same trade from the other side: a name that is only a *prefix* of
        # a real mention is not one. Drop the slash from the search and this
        # directory passes on a mention of a sibling that does not exist.
        self.mkdir("0751-isolation-run-void-block")
        self.row("`other/*.csv`", note='as `0751-isolation-run-void-block-moved/` is')
        self.mkdir("other")
        self.write("other/a.csv")
        self.assertEqual(self.verdicts()[0], ["0751-isolation-run-void-block"])


class AcceptsBothReachableDirectories(ScratchIndex, unittest.TestCase):
    """Direction 1's success cases, including the self-indexed clause.

    The self-indexed rule is the one that has to stay structural: a check that
    special-cased today's self-indexed directory would be an exemption list, and
    the eleventh such directory would arrive as a false gap. So the case that
    pins it uses a name this tool has never seen.
    """

    def test_a_directory_with_its_own_readme_is_indexed(self):
        self.mkdir("a-directory-nobody-has-heard-of")
        self.write("a-directory-nobody-has-heard-of/README.md", "its own index\n")
        self.write("a-directory-nobody-has-heard-of/row.csv")
        result = self.check()
        self.assertEqual((result.gaps, result.missing), ([], []))
        self.assertEqual((result.directories, result.self_indexed), (1, 1))

    def test_a_directory_named_below_the_table_is_indexed(self):
        # The committed index's own shape: `0751-isolation-run/` is named in
        # prose at the bottom, not in a row, and a table-only scan would report
        # a gap on the one directory the grader holds §6's list against.
        self.mkdir("0751-isolation-run")
        self.write("0751-isolation-run/a.csv")
        self.prose("`0751-isolation-run/` is the set the procedure names.\n")
        result = self.check()
        self.assertEqual(result.gaps, [])
        self.assertEqual((result.directories, result.named), (1, 1))

    def test_build_leftovers_are_neither_indexed_nor_counted(self):
        # A `__pycache__` under testdata/ is what an interpreter run from the
        # directory leaves, and a dot-name is a tool's scratch space. Neither
        # is a fixture a reader of the index is missing, and counting them
        # would put a number in the output that no edit to the index can move.
        self.mkdir("__pycache__")
        self.mkdir(".ipynb_checkpoints")
        result = self.check()
        self.assertEqual((result.directories, result.gaps), (0, []))

    def test_an_empty_tree_and_an_empty_index_are_green(self):
        # Stated rather than assumed: a checker with no fixtures to look at has
        # nothing to be wrong about, and this says so rather than reaching for
        # a floor that a legitimate emptying of the directory would trip.
        result = self.check()
        self.assertEqual(result, ctti.Result([], [], [], 0, 0, 0, 0, 0))


class RefusesARowWithNoFile(ScratchIndex, unittest.TestCase):
    """Direction 2: the index naming something the tree does not have.

    Same class of mistake as a fixture with no row -- an index is a promise
    about which files exist -- and the half that reads the shorthand is the
    half a future edit can get wrong, so every shape has its own case.
    """

    def test_a_bare_filename_that_is_not_on_disk_is_missing(self):
        self.row("`0751-isolation-example-quiet.csv`")
        _, missing, _ = self.verdicts()
        self.assertEqual(missing, ["0751-isolation-example-quiet.csv"])

    def test_a_directory_glob_over_a_directory_that_is_not_there_is_missing(self):
        self.row("`0751-isolation-run-staged/*.csv`")
        _, missing, _ = self.verdicts()
        self.assertEqual(missing, ["0751-isolation-run-staged/*.csv"])

    def test_a_directory_glob_over_a_directory_with_no_match_is_missing(self):
        # The directory is there and the row is wrong about what is in it,
        # which is the case a "does the directory exist" reading of the shape
        # would pass. The fixture exists because the issue asks the check to
        # hold the row, not the directory.
        self.mkdir("0751-isolation-run-staged")
        self.write("0751-isolation-run-staged/notes.md")
        self.row("`0751-isolation-run-staged/*.csv`")
        _, missing, _ = self.verdicts()
        self.assertEqual(missing, ["0751-isolation-run-staged/*.csv"])

    def test_the_feeds_column_is_not_a_fixture_path(self):
        # The second column is a tool reference and the third is prose; a check
        # that read either would report the tool it feeds as a missing fixture
        # on the day it is renamed, which is a different invariant with a
        # different owner.
        self.row("`0751-isolation-example-quiet.csv`", feeds="../no_such_tool.py",
                 note="the same marks as `0751-isolation-run/a.csv`")
        self.write("0751-isolation-example-quiet.csv")
        result = self.check()
        self.assertEqual((result.gaps, result.missing, result.unresolved),
                         ([], [], []))


class ResolvesTheShorthand(ScratchIndex, unittest.TestCase):
    """The `...` and `*` rules, which is the whole of direction 2's risk.

    The issue's condition on this direction is that a check which false-positives
    on the `...-0400-045f.csv` abbreviations is worse than no check, so what is
    pinned is that each abbreviation resolves by glob and that a `missing` says
    which pattern it failed on.
    """

    def test_the_ellipsis_resolves_to_a_glob_not_a_spliced_name(self):
        # The stem to splice onto is not in the token: `...-0400-045f.csv` is a
        # sibling of `0751-isolation-example-fixed-load-0700-07ff.csv` in the
        # real table, and splicing that stem's `-fixed-load-0700-07ff` onto it
        # produces `0751-isolation-example-fixed-load-0700-07ff-0400-045f.csv`,
        # which is not on disk. A check that spliced would report a false gap on
        # a row that has been true since the row was written.
        self.write("0751-isolation-example-fixed-load-0700-07ff.csv")
        self.write("0751-isolation-example-fixed-load-0400-045f.csv")
        self.row("`0751-isolation-example-fixed-load-0700-07ff.csv`"
                 " + `...-0400-045f.csv`")
        result = self.check()
        self.assertEqual((result.gaps, result.missing), ([], []))
        self.assertEqual(result.tokens, 2, "both tokens of the cell are read")
        self.assertEqual(ctti.resolve("...-0400-045f.csv", self.testdata),
                         (ctti.RESOLVED, "*-0400-045f.csv"))

    def test_an_ellipsis_naming_nothing_real_is_missing(self):
        # The other half, and the reason the glob is not simply waved through:
        # the same token in a tree with no such file is a `missing`, and the
        # report says which pattern it was read as so the reader can see that
        # the abbreviation was read and not merely tolerated.
        self.row("`...-0400-045f.csv`")
        _, missing, _ = self.verdicts()
        self.assertEqual(missing, ["...-0400-045f.csv"])
        self.assertEqual(ctti.resolve("...-0400-045f.csv", self.testdata),
                         (ctti.MISSING, "*-0400-045f.csv"))

    def test_a_bare_glob_is_resolved_recursively(self):
        # The `multi-block` row's second token, which names a dump in a
        # directory whose name is not in the token at all.
        self.write("0751-isolation-run-multi-block/a.csv")
        self.write("0751-isolation-run-multi-block/"
                   "2026-01-01-0751-isolation-a0-before-0700.txt")
        self.row("`0751-isolation-run-multi-block/*.csv` + `*-a0-before-0700.txt`")
        result = self.check()
        self.assertEqual((result.gaps, result.missing), ([], []))

    def test_a_bare_glob_that_matches_nothing_is_missing(self):
        self.row("`*-a0-before-0700.txt`")
        _, missing, _ = self.verdicts()
        self.assertEqual(missing, ["*-a0-before-0700.txt"])

    def test_a_directory_name_with_a_trailing_slash_is_resolved_by_its_existence(self):
        self.mkdir("0751-isolation-run-staged")
        self.row("`0751-isolation-run-staged/`")
        self.assertEqual(self.verdicts()[:2], ([], []))

    def test_a_bare_filename_resolves_against_the_top_of_testdata(self):
        self.write("0751-isolation-example-quiet.csv")
        self.row("`0751-isolation-example-quiet.csv`")
        self.assertEqual(self.verdicts()[:2], ([], []))


class SaysUnresolvedRatherThanAbsent(ScratchIndex, unittest.TestCase):
    """The calibration line, as a case: a shape this tool cannot read is a
    `missing`-free outcome, and the run still exits 0.

    `CLAUDE.md`'s rule is that a static scan finding zero references means "not
    found by this method" and never "absent". A pointer-checker that reported
    its own parser's blind spot as a broken index would be pushed to grow a
    rule for whatever it could not read, which is how a check starts inventing
    the thing it is checking.
    """

    def test_an_unparseable_token_is_unresolved_and_does_not_fail(self):
        self.row("`0x0700-0x07FF`")
        self.write("0751-isolation-example-quiet.csv")
        result = self.check()
        self.assertEqual([(token, note) for _, token, note in result.unresolved],
                         [("0x0700-0x07FF", "0x0700-0x07FF")])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctti.report(result.gaps, result.missing,
                                         result.unresolved), 0)
        self.assertIn('not checked, not absent', err.getvalue())

    def test_the_shape_the_unresolved_note_prints_is_the_token(self):
        # For the `...` rule the note is the pattern the token was read as,
        # which is the only way a reader of an `unresolved` line can tell a
        # parser that gave up from one that read a rule and found nothing --
        # and it is the shape a new rule would have to change.
        verdict, note = ctti.resolve("0751-isolation-run-staged", self.testdata)
        self.assertEqual((verdict, note), (ctti.UNRESOLVED,
                                           "0751-isolation-run-staged"))


class ParsesOnlyTheFirstColumn(unittest.TestCase):
    """The parse itself, because a bad regex here passes vacuously.

    A `table_cells()` that found nothing matches an empty tree, and an empty
    tree is green -- the same §14b defect the runner's empty-discovery guard
    exists for, one level down.
    """

    INDEX = '\n'.join([
        'prose naming `0751-isolation-run/` above the table',
        '',
        '| File | Feeds | What it constructs |',
        '|---|---|---|',
        '| `a.csv` | `../tool.py` | a `| b.csv` description |',
        '| `c.csv` + `d.csv` | `../tool.py` | two files |',
        '',
        'after the table, a `|` line that is not a row',
    ])

    def test_only_lines_after_the_file_header_are_rows(self):
        self.assertEqual(ctti.table_cells(self.INDEX), ['`a.csv`',
                                                        '`c.csv` + `d.csv`'])

    def test_every_backticked_token_in_a_cell_is_read(self):
        # The difference from `tools/test_readme_suite_table.py`, whose
        # single-token fullmatch is right for its one-path-per-row table and
        # would read both of these rows as no row at all.
        self.assertEqual(ctti.TOKEN.findall('`c.csv` + `d.csv`'), ['c.csv', 'd.csv'])

    def test_a_table_with_no_header_reads_no_rows(self):
        self.assertEqual(ctti.table_cells('| a | b |\n|---|---|\n| `x.csv` | y |'),
                         [])


class TheCommittedTree(unittest.TestCase):
    """The real thing: the index and the tree beside it currently agree.

    This is the assertion that would have caught either hand-repair, and it
    goes red on any future edit that drifts the two apart in either direction.
    """

    def run_tool(self):
        out, err = io.StringIO(), io.StringIO()
        argv = sys.argv
        sys.argv = ['check_testdata_index.py', '--check']
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ctti.main()
        finally:
            sys.argv = argv
        return rc, out.getvalue(), err.getvalue()

    def test_the_committed_index_and_tree_agree(self):
        rc, out, err = self.run_tool()
        self.assertEqual(rc, 0, err)
        self.assertIn('table row(s)', out)

    def test_the_run_actually_reached_both_directions(self):
        # A run that reports 0 directories and 0 rows is green for the wrong
        # reason, and the tallies are the only way to tell. This is not a floor
        # on coverage: nothing says the numbers have to stay where they are,
        # only that a run reaching nothing fails.
        _, out, _ = self.run_tool()
        directories = int(out.split(' testdata/ ')[0])
        rows = int(out.split(' table row(s)')[0].split('\n')[1])
        tokens = int(out.split('path token(s): ')[0].split(' table row(s), ')[1])
        self.assertEqual((directories, rows, tokens), (13, 27, 34))
        self.assertGreater(tokens, rows,
                           "one row holds several paths; a token count that "
                           "equals the row count means only the first is read")

    def test_the_committed_call_graph_directory_is_self_indexed(self):
        # `call-graph/` is the case the issue names: a directory the top-level
        # table does not mention, self-indexed with its own README, which is
        # the right call and must not read as a gap.
        with open(ctti.INDEX, encoding='utf-8') as f:
            index = f.read()
        self.assertEqual(ctti.reachable('call-graph', ctti.TESTDATA, index), 'self')
        self.assertTrue(os.path.isfile(
            os.path.join(ctti.TESTDATA, 'call-graph', 'README.md')))

    def test_the_run_directory_is_indexed_in_prose_and_not_by_prefix(self):
        # `0751-isolation-run/` reaches the index through a paragraph at the
        # bottom of the file, so the whole-file search is load-bearing: a
        # table-only scan would report a gap on the set §6 names. The
        # assertion is that the *rule* holds, not that the index is written
        # this way today -- naming it in a row later would be an improvement,
        # not a regression, and must not fail here.
        with open(ctti.INDEX, encoding='utf-8') as f:
            index = f.read()
        self.assertIsNotNone(ctti.reachable('0751-isolation-run', ctti.TESTDATA, index))
        self.assertIn('0751-isolation-run/', index)
        for cell in ctti.table_cells(index):
            self.assertFalse(cell.startswith('`0751-isolation-run/*'),
                             'a cell that reads as the run set itself')

    def test_the_report_names_the_path_it_is_given(self):
        # `check()` hands back a repository-relative path, so `report()` joins
        # it rather than resolving it again against the working directory. A
        # report nobody can paste into an editor is a report nobody opens.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctti.report(
                [('ec/tools/testdata', 'newset')],
                [('ec/tools/testdata/README.md', 'gone.csv', 'gone.csv')], []), 2)
        lines = err.getvalue().splitlines()
        self.assertTrue(lines[0].startswith('ec/tools/testdata/newset/:'), lines[0])
        self.assertIn('ec/tools/testdata/README.md', lines[1])
        for line in lines:
            self.assertNotIn('/../', line)
            self.assertFalse(line.startswith('/'), line)


if __name__ == '__main__':
    unittest.main()
