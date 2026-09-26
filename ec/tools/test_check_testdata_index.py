#!/usr/bin/env python3
"""Offline checks for check_testdata_index.py: committed files only.

The tool is a pointer-checker, so its failure mode is silence rather than a
crash. Loosen a rule and it stops catching a fixture with no row while still
exiting 0, and the only thing that notices is a reader who has already been
misled -- and no commit runs the tool until a human lands the gate patch, so
that reader has to be a person. So what is pinned here is the line between what
the tool refuses and what it waves through: each rule that makes it
conservative gets a case saying so, and each rule that makes it *strict* gets
one too, because a checker that has quietly started accepting everything looks
exactly like a checker that is working.

The fixtures are written inline into a scratch `testdata/` under a temporary
root, which keeps each case readable as the tree and the index beside it rather
than as a diff against a stored pair. The real committed tree is the last class,
and it is what says the index and the tree currently agree.

**Five sources, one rule.** A path the index names has to be there, and the five
places this tree reads one from are the five lines the tool prints: the table's
first column, its `Feeds` column, the tables in every self-indexed directory's
own README, and the `evidence` column of the CSVs those tables name. The first
two are one class each; the third is `ReadsASelfIndexedReadme`; the fourth is
`ReadsTheEvidenceColumn`; and the one rule over all five is
`assert_the_run_reached_something`, which every class below holds itself to.

**Nothing here reads a capture, an EC, or a laptop.** Every path is a
hand-written string in a `tempfile`, and the last class reads three committed
files with `open()`.
"""
import contextlib
import importlib.util
import io
import os
import re
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

# The `Feeds` cell a row gets when the case is about something else. Emitted
# verbatim, because the column carries three shapes -- plain, flag-suffixed and
# `via`-paired -- and a helper that wrapped the whole string in backticks could
# not write two of them. `ScratchIndex.setUp` puts the tool it names beside the
# scratch `testdata/`, so the default resolves from the moment the column is
# read and a case that is not about `Feeds` does not start reporting a miss.
FEEDS = '`../grade_0751_isolation.py`'

# A second table in a self-indexed README, in the committed `call-graph`
# fixture's own shape: the header is not `File`, which is what stops it being
# read as the top-level table's, and the separator is the short `|---|` form.
NESTED_HEADER = '| file / row | what it pins |\n|---|---|\n'


class RunsTheTool:
    """One run of the tool, over a tree that is not the committed one.

    Split out of `TheReachedSomethingRule` for the one case that needs the
    runner and not the rule: a refusal whose `Result` fields are right and whose
    *printed* line is wrong is only visible through a run, and the column-less
    CSV in `ReadsTheEvidenceColumn` is that shape. It is a base rather than a
    method on `ScratchIndex` because `TheCommittedTree` runs the tool too and
    inherits no scratch tree, so the runner belongs to neither the fixture
    builder nor the tally rule on its own.
    """

    def run_tool(self, root, repo=None):
        """(exit code, stdout, stderr) for one run of the tool over `root`.

        `main()` reads the committed `TESTDATA` and `INDEX` as module globals
        and has no flag pointing it anywhere else, so a scratch tree is reached
        by patching both -- `report()` prints `INDEX` on its summary line, so
        patching only the first would have a run over a `tempfile` report a
        disagreement against the committed index. `REPO` is the third of the
        same three, and it is what the `evidence` column resolves against, so a
        run over a scratch tree has to be given the scratch root or it would
        answer about the committed one. All three go back in the same `finally`
        that already restored `sys.argv`, for the reason `tools/` §16 records
        for the suites that used to leave a fake installed.
        """
        out, err = io.StringIO(), io.StringIO()
        argv, was = sys.argv, (ctti.TESTDATA, ctti.INDEX, ctti.REPO)
        sys.argv = ['check_testdata_index.py', '--check']
        ctti.TESTDATA, ctti.INDEX = root, os.path.join(root, "README.md")
        if repo is not None:
            ctti.REPO = repo
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = ctti.main()
        finally:
            sys.argv = argv
            ctti.TESTDATA, ctti.INDEX, ctti.REPO = was
        return rc, out.getvalue(), err.getvalue()


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
        # The repository root, for the `evidence` column: the one base that is
        # neither the fixture tree nor its parent, and the reason
        # `write_repo()` below can put a real-tree path on disk and have the
        # rule resolved rather than asserted. The same scratch root the tools
        # live in, for the same reason: it is a base, not a hardcoded
        # directory the committed tree happens to have.
        self.repo = self.root
        # The tools live beside `testdata/`, which is what a `../tool.py` in a
        # `Feeds` cell names. Without it every row built here would report a
        # `Feeds` miss the moment that column started being read.
        self.write_tool("grade_0751_isolation.py")
        self.rows, self.below = [], ""

    def write_tool(self, name):
        """Put a tool beside the scratch `testdata/`, where `../` finds it."""
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# a tool the index names\n")
        return path

    def write_repo(self, rel, text='; a listing under the real tree\n'):
        """Create `rel` under the scratch repository root, parents and all.

        The counterpart to `write()`, which creates under `testdata/`. A
        committed `evidence` cell is written from the repository root's point of
        view -- `ec/decompiled/bank0/0EA2.asm`, not `decompiled/bank0/0EA2.asm`
        -- so the two cannot be the same base, and a case that used `write()`
        would be asserting the rule rather than exercising it.
        """
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def row(self, cell, feeds=FEEDS, note='a fixture'):
        """Add one table row naming `cell`, and return the index it is in."""
        self.rows.append(f'| `{cell}` | {feeds} | {note} |')
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

    def nested_tables(self, name, *rows):
        """Put `rows` into a self-indexed directory's README as one table."""
        directory = self.mkdir(name)
        body = NESTED_HEADER + "".join(f"| {row} |\n" for row in rows)
        self.write(f"{name}/README.md", "# the set\n\n" + body)
        return directory

    def self_indexed(self, name="a-self-indexed-set", tables=1):
        """A directory the top-level index does not name, with its own tables.

        The one thing `reachable()` calls `self` on, and the only place a nested
        table is read from. It carries a listing and a CSV row so that both
        nested rules have something to resolve and neither is vacuous; a
        self-indexed directory whose README holds no table reaches the third
        direction not at all, which is a case of its own.

        The `index.csv` it writes carries an `evidence` column, and the file
        that column names is written under `self.repo` rather than under
        `testdata/`. Without it the four `TheTalliesAreNotAFloor` cases stop
        reaching the fifth direction at all and the shared helper refuses all
        four — which is the failure `ThatClassIsAbout`.
        """
        self.mkdir(f"{name}/decompiled/common")
        self.write(f"{name}/decompiled/common/00CF.asm", "; a listing\n")
        self.write_repo("ec/decompiled/common/00CF.asm")
        self.write(f"{name}/index.csv", "program,addr,name,evidence\n"
                  "common,00CF,walker,ec/decompiled/common/00CF.asm\n")
        body = NESTED_HEADER + (
            "| `decompiled/common/00CF.asm` | a listing |\n"
            "| `index.csv` row `0x00CF` | the row that listing came from, and "
            "the `evidence` cell in it names a real-tree listing |\n")
        if tables > 1:
            body += "\n" + NESTED_HEADER + (
                "| `decompiled/common/05E8.asm` | a second table's row |\n")
        self.write(f"{name}/README.md", "# the set\n\n" + body)
        if tables > 1:
            self.write(f"{name}/decompiled/common/05E8.asm", "; a listing\n")
        return name

    def write_index(self, index=None):
        """Put the index beside the tree, where a run of the tool would find it.

        `main()` opens `<root>/README.md` and parses a tally out of what it
        printed, so a case pointing it at a scratch tree has to leave the index
        on disk the way a committed tree has it. Nothing is kept in a variable
        a run never reads.
        """
        self.write("README.md", self.index if index is None else index)

    def check(self, index=None):
        """The tool's `Result` for this scratch tree.

        The index is written to disk rather than handed in, because the tool
        reads it from `testdata/README.md` and a case that bypassed that would
        pass against a reader no run ever uses. `repo` is the scratch root, for
        the reason `write_repo()` gives.
        """
        self.write_index(index)
        return ctti.check(self.testdata, repo=self.repo)

    def verdicts(self, index=None):
        """(gaps, missing, unresolved) as bare names, for compact assertions."""
        result = self.check(index)
        return ([name for _, name in result.gaps],
                [token for _, token, _ in result.missing],
                [token for _, token, _ in result.unresolved])

    def feeds(self, index=None):
        """(missing, unresolved) for the `Feeds` column, as bare names."""
        result = self.check(index)
        return ([token for _, token, _ in result.feeds_missing],
                [token for _, token, _ in result.feeds_unresolved])

    def nested(self, index=None):
        """(missing, unresolved) for the self-indexed READMEs, as bare names."""
        result = self.check(index)
        return ([token for _, token, _ in result.nested_missing],
                [token for _, token, _ in result.nested_unresolved])

    def evidence(self, index=None):
        """(missing, unresolved) for the `evidence` column, as bare names."""
        result = self.check(index)
        return ([token for _, token, _ in result.evidence_missing],
                [token for _, token, _ in result.evidence_unresolved])


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
        # a floor that a legitimate emptying of the directory would trip. Every
        # count is written out, which is what says the three directions added
        # later are reached by nothing here and fail on nothing either.
        result = self.check()
        self.assertEqual(result, ctti.Result([], [], [], [], [], [], [], [], [],
                                              [], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                                              0, 0, 0, 0))


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

    def test_the_feeds_column_is_read_as_a_tool_and_not_as_a_fixture(self):
        # The second column is a tool reference and the third is prose. A check
        # that read the third would resolve every address the descriptions
        # quote, which is not a rule this tool has; and a check that read the
        # second as a fixture path would report the tool it feeds as a missing
        # fixture. So the column is read, but as a *tool*: the fixture beside
        # it is on disk, the tool it names is not, and the finding is the
        # tool's -- in `feeds_missing`, and not in the first-column `missing`.
        self.row("`0751-isolation-example-quiet.csv`",
                 feeds="`../no_such_tool.py`",
                 note="the same marks as `0751-isolation-run/a.csv`")
        self.write("0751-isolation-example-quiet.csv")
        result = self.check()
        self.assertEqual((result.missing, result.unresolved), ([], []))
        self.assertEqual([token for _, token, _ in result.feeds_missing],
                         ["../no_such_tool.py"])
        self.assertEqual([token for _, token, _ in result.feeds_unresolved], [])
        self.assertEqual(ctti.resolve_tool("../no_such_tool.py", self.root)[0],
                         ctti.MISSING)


class ReadsTheFeedsColumn(ScratchIndex, unittest.TestCase):
    """The second column, read as a tool reference and not as a fixture path.

    Three shapes and one resolution: a plain name, a name with a flag suffix,
    and a `via` pair. The issue's condition on the whole direction is the same
    one it conditioned the `...` rule on -- a check that false-positives is
    worse than none -- and a checker that did not cut the flag suffix would
    report three misses on the committed tree on the day it landed.
    """

    def test_a_tool_beside_the_fixture_root_resolves(self):
        # The base is the *parent* of `testdata/`, because that is where a
        # fixture's tool is: `../grade_0751_isolation.py` written from the
        # fixture's point of view is a sibling of the fixture, not a path
        # inside it. Joining against `testdata/` would answer a different
        # question, and the default `Feeds` cell in every other case here would
        # report a miss.
        self.row("`a.csv`")
        self.write("a.csv")
        result = self.check()
        self.assertEqual((result.feeds_missing, result.feeds_unresolved), ([], []))
        self.assertEqual((result.feeds_cells, result.feeds_tokens), (1, 1))

    def test_a_tool_that_is_not_there_is_a_feeds_missing(self):
        self.row("`a.csv`", feeds="`../check_capture_claims.py`")
        self.write("a.csv")
        self.assertEqual(self.feeds()[0], ["../check_capture_claims.py"])

    def test_a_tool_renamed_out_from_under_the_column_fails_the_run(self):
        # The issue's "done looks like": renaming a tool is what this column
        # exists to catch. `main()` returns whatever `report()` returns, so
        # this is the exit code, asserted where the shipped calibration case
        # asserts the other half of it.
        self.row("`a.csv`", feeds="`../no_such_tool.py`")
        self.write("a.csv")
        result = self.check()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            total = ctti.report(result.gaps, result.missing, result.unresolved,
                               (result.feeds_missing, result.feeds_unresolved),
                               (result.nested_missing, result.nested_unresolved),
                               (result.evidence_missing, result.evidence_unresolved),
                               result.evidence_columnless)
        self.assertEqual(total, 1)
        self.assertIn('`Feeds` column names `../no_such_tool.py`',
                      err.getvalue())
        self.assertIn('not a tool on disk', err.getvalue())

    def test_the_flag_suffix_is_cut_and_the_cell_resolves(self):
        # Three committed rows carry `../grade_0751_isolation.py --dump-pair`,
        # and the tool is `grade_0751_isolation.py`. Without the cut this is
        # three false misses on the day the check lands.
        self.row("`a.csv` + `b.txt`", feeds="`../grade_0751_isolation.py --dump-pair`")
        self.write("a.csv")
        self.write("b.txt")
        result = self.check()
        self.assertEqual((result.feeds_missing, result.feeds_unresolved), ([], []))
        self.assertEqual((result.feeds_cells, result.feeds_tokens), (1, 1))
        self.assertEqual(ctti.feeds_pointers('`../grade.py --dump-pair`'),
                         ['../grade.py'])

    def test_a_via_clause_is_read_as_both_of_its_halves(self):
        # The committed shape, and the reason the `via` needs no rule of its
        # own: both halves are backticked, so reading every backticked token
        # reads both. Two pointers over one cell is what the tally counts.
        self.write_tool("check_capture_claims.py")
        self.write_tool("test_check_capture_claims.py")
        self.row("`a.csv`",
                 feeds="`../check_capture_claims.py`, via `../test_check_capture_claims.py`")
        self.write("a.csv")
        result = self.check()
        self.assertEqual((result.feeds_missing, result.feeds_unresolved), ([], []))
        self.assertEqual((result.feeds_cells, result.feeds_tokens), (1, 2))

    def test_a_via_second_half_that_is_not_there_is_its_own_finding(self):
        # Its own, and not a verdict about the cell: the first half still
        # resolves, so a reader who fixed only the second would be fixing the
        # wrong line.
        self.write_tool("check_capture_claims.py")
        self.row("`a.csv`",
                 feeds="`../check_capture_claims.py`, via `../no_such_tool.py`")
        self.write("a.csv")
        self.assertEqual(self.feeds()[0], ["../no_such_tool.py"])

    def test_a_plus_joined_feeds_cell_is_read_as_both(self):
        # A shape the committed index has none of, pinned here rather than
        # claimed to be exercised: two tools in one cell is the ` + ` rule the
        # first column already has, applied to a column that needed a reader.
        self.write_tool("grade_0751_isolation.py")
        self.write_tool("grade_gpu_door.py")
        self.row("`a.csv`",
                 feeds="`../grade_0751_isolation.py` + `../grade_gpu_door.py`")
        self.write("a.csv")
        result = self.check()
        self.assertEqual((result.feeds_missing, result.feeds_unresolved), ([], []))
        self.assertEqual((result.feeds_cells, result.feeds_tokens), (1, 2))

    def test_a_feeds_token_matching_no_rule_is_unresolved_and_does_not_fail(self):
        # The calibration line again, in the second column. A shape this tool
        # cannot read is "not resolved by this method" and never "absent", and
        # a check that failed on its own parser would be pushed to grow a rule
        # for whatever it could not read.
        self.row("`a.csv`", feeds="`0x0700-0x07FF`")
        self.write("a.csv")
        result = self.check()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            total = ctti.report(result.gaps, result.missing, result.unresolved,
                                (result.feeds_missing, result.feeds_unresolved),
                                (result.nested_missing, result.nested_unresolved),
                                (result.evidence_missing, result.evidence_unresolved),
                                result.evidence_columnless)
        self.assertEqual(total, 0)
        self.assertEqual([token for _, token, _ in result.feeds_unresolved],
                         ["0x0700-0x07FF"])
        self.assertIn('not checked, not absent', err.getvalue())


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
                                         result.unresolved, ([], []), ([], []),
                                         ([], []), []), 0)
        self.assertIn('not checked, not absent', err.getvalue())

    def test_the_shape_the_unresolved_note_prints_is_the_token(self):
        # For the `...` rule the note is the pattern the token was read as,
        # which is the only way a reader of an `unresolved` line can tell a
        # parser that gave up from one that read a rule and found nothing --
        # and it is the shape a new rule would have to change.
        verdict, note = ctti.resolve("0751-isolation-run-staged", self.testdata)
        self.assertEqual((verdict, note), (ctti.UNRESOLVED,
                                           "0751-isolation-run-staged"))


class ReadsASelfIndexedReadme(ScratchIndex, unittest.TestCase):
    """A self-indexed directory's own tables, which are a harder shape.

    The top-level reader cannot express these cells: a row names a `.asm`
    *and* a `ghidra-functions.csv` row, in one cell, and the file holds three
    tables rather than one. The rules are the same ones the top-level table
    states -- a path the index names has to be there -- in the two shapes that
    cell uses, plus the `unresolved` line for anything neither of them reads.
    """

    def test_a_second_and_a_third_table_are_read(self):
        # The defect the issue names, and the one `table_cells` had by
        # construction: a reader pointed at this file returned after the first
        # table that ended, so eight of nineteen rows were never looked at.
        # Located by shape rather than by header name, so the count is the
        # file's and not this tool's.
        name = "three-tables"
        self.write(f"{name}/decompiled/common/018C.asm", "; a listing\n")
        self.write(f"{name}/decompiled/common/029B.asm", "; a listing\n")
        self.write(f"{name}/index.csv", "program,addr,name\ncommon,DEAD,nothing\n")
        self.write(f"{name}/README.md", (
            "# the set\n\n"
            + NESTED_HEADER + "| `decompiled/common/018C.asm` | the first |\n\n"
            + NESTED_HEADER + "| `decompiled/common/029B.asm` | the second |\n\n"
            + NESTED_HEADER + "| `index.csv` row `0xDEAD` | the third |\n"))
        result = self.check()
        self.assertEqual((result.nested_missing, result.nested_unresolved),
                         ([], []))
        self.assertEqual((result.nested_indexes, result.nested_tables,
                          result.nested_rows, result.nested_checks),
                         (1, 3, 3, 3))

    def test_an_asm_path_not_on_disk_is_a_nested_missing(self):
        # The one cell the committed `call-graph` README got wrong, and the
        # reason the direction is worth having: this path has been named by a
        # table nothing read since the table was written.
        self.nested_tables("a-set", "`decompiled/common/0EA2.asm` | a listing")
        self.assertEqual(self.nested()[0], ["decompiled/common/0EA2.asm"])

    def test_an_asm_path_resolves_against_the_directory_and_not_testdata(self):
        # The resolution is the whole of the case: a `..` that escaped to
        # `testdata/` would answer about a tree this check never looked at, and
        # the committed path is relative to the README that names it.
        name = "a-set"
        self.write(f"{name}/decompiled/common/00CF.asm", "; a listing\n")
        self.nested_tables(name, "`decompiled/common/00CF.asm` | a listing")
        result = self.check()
        self.assertEqual((result.nested_missing, result.nested_unresolved),
                         ([], []))
        self.assertEqual(result.nested_checks, 1)

    def test_a_csv_row_reference_at_an_address_the_csv_does_not_hold_is_a_miss(self):
        # Existence, not identity: the row the index names has to be in the
        # file it names. The `program` column is not read, because requiring it
        # to match something the cell does not state would be inventing a
        # constraint the index does not make.
        name = "a-set"
        self.write(f"{name}/index.csv", "program,addr,name\ncommon,DEAD,nothing\n")
        self.nested_tables(name, "`index.csv` row `0x0EA2` | a row")
        result = self.check()
        self.assertEqual([token for _, token, _ in result.nested_missing],
                         ["0x0EA2"])
        self.assertEqual([note for _, _, note in result.nested_missing],
                         ["index.csv 0x0EA2"])

    def test_the_prefix_case_and_the_padding_are_not_spelling(self):
        # The three ways the two sides of one address differ, all three live in
        # the committed file -- `0x0EA2` against `0EA2`, `0xDEAD` against
        # `DEAD`, `0x0070` against `0070`. A string compare reports a miss on
        # every one, and the check would be wrong on the day it landed.
        name = "a-set"
        self.write(f"{name}/ghidra-functions.csv",
                   "scope,addr,name\ncommon,0EA2,one\ncommon,DEAD,two\n"
                   "common,0070,three\n")
        self.nested_tables(name,
                           "`ghidra-functions.csv` `0x0ea2` | lower case",
                           "`ghidra-functions.csv` `0xdead` | no prefix here",
                           "`ghidra-functions.csv` `0x0070` | padded here")
        result = self.check()
        self.assertEqual((result.nested_missing, result.nested_unresolved),
                         ([], []))
        self.assertEqual((result.nested_rows, result.nested_checks), (3, 3))
        self.assertEqual(ctti.as_address("0x0ea2"), ctti.as_address("0EA2"))
        self.assertIsNone(ctti.as_address("0x0ZZ"))

    def test_a_plus_joined_cell_is_read_as_both_an_asm_and_a_csv_reference(self):
        # One row and two references, the second naming two rows -- the shape
        # the count is per reference for, and the reason a tally taken per cell
        # would be wrong.
        name = "a-set"
        self.write(f"{name}/decompiled/common/0071.asm", "; a listing\n")
        self.write(f"{name}/index.csv", "program,addr,name\ncommon,1400,a\ncommon,1410,b\n")
        self.nested_tables(name, (
            "`decompiled/common/0071.asm` + `index.csv` rows `0x1400`/`0x1410`"
            " | the corroborated shape"))
        result = self.check()
        self.assertEqual((result.nested_missing, result.nested_unresolved),
                         ([], []))
        self.assertEqual((result.nested_rows, result.nested_checks), (1, 3))

    def test_a_part_matching_neither_rule_is_unresolved_and_does_not_fail(self):
        name = "a-set"
        self.write(f"{name}/index.csv", "program,addr,name\ncommon,00CF,a\n")
        self.nested_tables(name, "`0x0700-0x07FF` a window, spelled as prose")
        result = self.check()
        self.assertEqual(result.nested_missing, [])
        self.assertEqual([token for _, token, _ in result.nested_unresolved],
                         ["0x0700-0x07FF"])

    def test_a_csv_with_no_addr_column_is_unresolved_and_not_missing(self):
        # "this tool cannot read that shape" and "the row is not there" are
        # different claims, and only the second is a failure. Reporting the
        # first as the second is how a checker starts inventing constraints.
        name = "a-set"
        self.write(f"{name}/index.csv", "program,offset,name\ncommon,00CF,a\n")
        self.nested_tables(name, "`index.csv` row `0x00CF` | a row")
        result = self.check()
        self.assertEqual(result.nested_missing, [])
        self.assertEqual([note for _, _, note in result.nested_unresolved],
                         ["index.csv has no `addr` column"])

    def test_a_csv_named_without_an_address_is_unresolved(self):
        name = "a-set"
        self.write(f"{name}/index.csv", "program,addr,name\ncommon,00CF,a\n")
        self.nested_tables(name, "`index.csv` named, with no row named")
        result = self.check()
        self.assertEqual(result.nested_missing, [])
        self.assertEqual([note for _, _, note in result.nested_unresolved],
                         ["index.csv is named with no address"])

    def test_a_csv_the_index_names_that_is_not_there_is_a_nested_missing(self):
        name = self.nested_tables("a-set", "`no_such.csv` row `0x00CF` | a row")
        self.assertEqual([token for _, token, _ in self.check().nested_missing],
                         ["no_such.csv"])

    def test_a_self_indexed_readme_with_no_table_reads_no_rows(self):
        # Not a failure, and not a tally: the self-indexed clause is about the
        # directory's existence, and a directory that indexes itself in prose
        # still indexes itself. The count is what says so, rather than a
        # `missing` this tool would have to invent a shape for.
        self.mkdir("prose-only")
        self.write("prose-only/README.md", "# the set\n\nNo table here.\n")
        self.row("`a.csv`")
        self.write("a.csv")
        result = self.check()
        self.assertEqual((result.nested_indexes, result.nested_tables,
                          result.nested_rows, result.nested_checks), (1, 0, 0, 0))
        self.assertEqual((result.nested_missing, result.gaps), ([], []))

    def test_a_directory_the_index_merely_names_is_not_walked(self):
        # The two reachability clauses stay the two things they were: only a
        # directory that indexes *itself* carries a nested index, so a
        # directory the top-level table names has nothing here to walk. Its
        # README is not read, its files are not resolved a second time against
        # it, and `reachable()` is what decides -- which is why the one
        # self-indexed directory in the committed tree is named in the tool's
        # docstring as the case that motivated the clause and in no code path.
        self.mkdir("named-only/decompiled/common")
        self.write("named-only/decompiled/common/0EA2.asm", "; a listing\n")
        self.write("named-only/0DDD.asm", "; a listing nothing names\n")
        self.row("`named-only/*.csv`")
        self.write("named-only/a.csv")
        result = self.check()
        self.assertEqual((result.nested_indexes, result.nested_checks), (0, 0))
        self.assertEqual((result.nested_missing, result.gaps), ([], []))

    def test_nothing_is_double_counted(self):
        # Three findings, three files, which is the only way a reader of the
        # report knows which one to open: the top-level index, the self-indexed
        # README beside it, and the fixture CSV holding the disagreeing cell.
        # The last is why an `evidence` finding does not reuse the README's
        # `where` -- neither of the other two files contains the cell. All three
        # lists are handed to `report()` as the same triple, so this is where it
        # is said.
        self.write("a.csv")
        self.row("`a.csv`", feeds="`../no_such_tool.py`")
        name = "a-set"
        self.nested_tables(name, "`decompiled/common/0EA2.asm` | a listing",
                           "`ghidra-functions.csv` row `0x00CF` | the other one")
        self.write(f"{name}/ghidra-functions.csv",
                   "scope,addr,name,evidence\ncommon,00CF,walker,"
                   "ec/decompiled/common/0EA2.asm\n")
        result = self.check()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ctti.report(result.gaps, result.missing, result.unresolved,
                        (result.feeds_missing, result.feeds_unresolved),
                        (result.nested_missing, result.nested_unresolved),
                        (result.evidence_missing, result.evidence_unresolved),
                        result.evidence_columnless)
        out = err.getvalue()
        feeds_where = [where for where, _, _ in result.feeds_missing]
        nested_where = [where for where, _, _ in result.nested_missing]
        evidence_where = [where for where, _, _ in result.evidence_missing]
        self.assertEqual(len(set(feeds_where + nested_where + evidence_where)), 3)
        self.assertTrue(feeds_where[0].endswith('testdata/README.md'),
                        feeds_where[0])
        self.assertTrue(nested_where[0].endswith('testdata/a-set/README.md'),
                        nested_where[0])
        self.assertTrue(evidence_where[0].endswith('testdata/a-set/ghidra-functions.csv'),
                        evidence_where[0])
        self.assertNotIn(f'{nested_where[0]}: the `Feeds` column', out)
        self.assertNotIn(f'{evidence_where[0]}: the table names', out)


class ReadsTheEvidenceColumn(ScratchIndex, RunsTheTool, unittest.TestCase):
    """The one column that points at the real tree, read against the real root.

    A third base -- neither the fixture tree nor its parent -- and the only
    source here that reads a named column out of a file's contents rather than
    backticked tokens out of a cell. The three refusals the issue names are one
    case each, and the two rules the committed tree needs in order to be green
    at all are pinned here rather than left to the committed case. `RunsTheTool`
    is a base for the one case below that has to see what a run *printed*; the
    fields it asserts on their own are what the other cases read.
    """

    def self_indexed_with(self, header, rows, name="a-set"):
        """A self-indexed directory whose `index.csv` the README names.

        The `evidence` rule only reaches a CSV a nested table already names, so
        every case here has to go through the same door the committed
        `call-graph` fixture does rather than dropping a CSV beside a directory
        nothing points at.
        """
        self.write(f"{name}/index.csv", header + "".join(rows))
        self.nested_tables(name, "`index.csv` row `0x00CF` | the row")

    def test_a_real_listing_renamed_out_from_under_the_cell_fails_the_run(self):
        # The issue's "done looks like": a cell naming a path the real tree does
        # not have turns the run red with a line naming it. The listing is
        # written and then not written, so what is refused is the *cell* rather
        # than a tree that was never there to be right.
        self.write_repo("ec/decompiled/common/00CF.asm")
        self.self_indexed_with("program,addr,name,evidence\n",
                               rows=["common,00CF,walker,"
                                     "ec/decompiled/common/00CF.asm\n"])
        result = self.check()
        self.assertEqual((result.evidence_missing, result.evidence_unresolved),
                         ([], []))
        os.remove(os.path.join(self.repo, "ec/decompiled/common/00CF.asm"))
        missing, unresolved = self.evidence()
        self.assertEqual(missing, ["ec/decompiled/common/00CF.asm"])
        self.assertEqual(unresolved, [])
        # The `where` is the CSV rather than the README that named it, and the
        # note is the repository-relative path the token was read as: a reader
        # who opens either of the other two files finds no such cell.
        renamed = self.check()
        where, _, note = renamed.evidence_missing[0]
        self.assertTrue(where.endswith('testdata/a-set/index.csv'), where)
        self.assertTrue(note.endswith('ec/decompiled/common/00CF.asm'), note)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            total = ctti.report(renamed.gaps, renamed.missing, renamed.unresolved,
                                (renamed.feeds_missing, renamed.feeds_unresolved),
                                (renamed.nested_missing, renamed.nested_unresolved),
                                (renamed.evidence_missing,
                                 renamed.evidence_unresolved),
                                renamed.evidence_columnless)
        self.assertEqual(total, 1)
        self.assertIn('the `evidence` column names '
                      '`ec/decompiled/common/00CF.asm`', err.getvalue())
        self.assertIn('which is not on disk', err.getvalue())

    def test_a_row_with_no_evidence_value_yields_no_pointer(self):
        # The stated limit, made a case. An empty cell is not a path the tree
        # lacks -- it is a cell that carries nothing, which is the shipped
        # first-column behaviour that a cell with no backticked token yields no
        # reference. Six committed rows are in exactly this state, and they are
        # why: a rule invented to read an empty value would be a parser
        # guessing, and a guess here is a `missing` against the real tree.
        self.write_repo("ec/decompiled/common/00CF.asm")
        self.self_indexed_with("program,addr,name,evidence\n",
                               rows=["common,00CF,walker,\n",
                                     "common,00CE,other,   \n",
                                     "common,00CD,third,ec/decompiled/common/00CF.asm\n"])
        result = self.check()
        self.assertEqual((result.evidence_missing, result.evidence_unresolved),
                         ([], []))
        # Two cells carried nothing and one carried a path: counted as cells and
        # as tokens apart, which is what a per-cell tally could not say.
        self.assertEqual((result.evidence_csvs, result.evidence_cells,
                          result.evidence_tokens), (1, 1, 1))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctti.report(
                result.gaps, result.missing, result.unresolved,
                (result.feeds_missing, result.feeds_unresolved),
                (result.nested_missing, result.nested_unresolved),
                (result.evidence_missing, result.evidence_unresolved),
                result.evidence_columnless), 0)
        self.assertEqual(err.getvalue(), '')

    def test_a_csv_with_no_evidence_column_is_unresolved_and_not_missing(self):
        # "this tool cannot read that shape" and "the path is not there" are
        # different claims and only the second is a failure. The issue's
        # condition on the whole direction is the one #746 set: a check that
        # false-positives is worse than no check, and a column-less CSV is the
        # shape most likely to arrive by accident.
        self.self_indexed_with("program,addr,name\n",
                               rows=["common,00CF,walker\n"])
        result = self.check()
        self.assertEqual(result.evidence_missing, [])
        # Its own list rather than among the token findings, for the reason the
        # tool's docstring gives: this is a fact about the CSV and there is no
        # token behind it, so a reader counting tokens here would be counting
        # one the CSV never contributed.
        self.assertEqual(result.evidence_unresolved, [])
        self.assertEqual([token for _, token, _ in result.evidence_columnless],
                         ['index.csv'])
        self.assertEqual([note for _, _, note in result.evidence_columnless],
                         ['index.csv has no `evidence` column'])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctti.report(
                result.gaps, result.missing, result.unresolved,
                (result.feeds_missing, result.feeds_unresolved),
                (result.nested_missing, result.nested_unresolved),
                (result.evidence_missing, result.evidence_unresolved),
                result.evidence_columnless), 0)
        # Its own wording too, and the point of that is the clause this case
        # exists for: a column that is not in the file has not named anything,
        # so the line says the column was not found. The old wording opened
        # "the `evidence` column names `index.csv`", which is the false claim
        # and the part a reader skims.
        self.assertIn('has no `evidence` column', err.getvalue())
        self.assertNotIn('the `evidence` column names', err.getvalue())
        self.assertIn('not checked, not absent', err.getvalue())

        # And the printed tally, which is the half the fields above cannot
        # reach. This is the shape the tool's own docstring gives the fifth
        # line its purpose for -- "a run that checked nothing and a run that
        # found nothing look the same from the exit code alone" -- and it is
        # where the two populations used to disagree: the finding is not a
        # token, so leaving it among the token findings subtracted one more
        # than the count held and the line read `0 evidence path token(s): -1
        # resolved`, a tally contradicting itself in the one shape this
        # direction is most likely to meet. Asserted as the relation rather
        # than as today's wording, so the case says what has to hold: the
        # resolved count is the token count less the two that were subtracted
        # from it, and cannot go below zero however many CSVs have no column.
        rc, out, err = self.run_tool(self.testdata, self.repo)
        self.assertEqual(rc, 0, err)
        line = [one for one in out.splitlines()
                if 'evidence path token(s)' in one]
        self.assertEqual(len(line), 1, out)
        found = re.search(
            r'(\d+) with no `evidence` column, \d+ evidence cell\(s\), '
            r'(\d+) evidence path token\(s\): (-?\d+) resolved, (\d+) missing, '
            r'(\d+) unresolved', line[0])
        self.assertIsNotNone(found, line[0])
        columnless, tokens, resolved, missing, unresolved = (
            int(found.group(n)) for n in range(1, 6))
        self.assertEqual((columnless, tokens, resolved, missing, unresolved),
                         (1, 0, 0, 0, 0))
        self.assertEqual(resolved, tokens - missing - unresolved)

    def test_the_column_is_read_by_name_and_not_by_position(self):
        # `evidence` is column 7 of 8 in one committed CSV and column 10 of 12
        # in the other, so a position is right on the day it lands and wrong
        # after the next column is added. The two cells here hold the path in
        # the same column of a different width, and a positional read gets
        # neither.
        self.write_repo("ec/decompiled/common/00CF.asm")
        self.self_indexed_with(
            "program,addr,name,also_in,basis,evidence\n",
            rows=["common,00CF,walker,,hand-decoded,"
                  "ec/decompiled/common/00CF.asm\n"])
        result = self.check()
        self.assertEqual((result.evidence_missing, result.evidence_unresolved),
                         ([], []))
        self.assertEqual((result.evidence_cells, result.evidence_tokens), (1, 1))

    def test_a_semicolon_joined_cell_is_two_pointers_and_two_paths(self):
        # The committed `bank0,0EA2` row, in the shape it has there: one cell
        # naming a listing and its `.c` side by side. Read whole, the cell is a
        # single token no path rule can match, and the run would be green for
        # the wrong reason -- which is what the two tallies being separate is
        # there to make visible.
        self.write_repo("ec/decompiled/common/00CF.asm")
        self.write_repo("ec/decompiled/common/00CF.c", "; a decompile\n")
        self.self_indexed_with(
            "program,addr,name,evidence\n",
            rows=["common,00CF,walker,ec/decompiled/common/00CF.asm; "
                  "ec/decompiled/common/00CF.c\n"])
        result = self.check()
        self.assertEqual((result.evidence_missing, result.evidence_unresolved),
                         ([], []))
        self.assertEqual((result.evidence_cells, result.evidence_tokens), (1, 2))

    def test_a_path_the_repository_root_does_not_hold_is_a_missing(self):
        # The base is the repository root and not the fixture tree, which is the
        # half that has to be exercised rather than asserted: the same relative
        # path is a file under `testdata/` and not under the root, so a rule
        # that resolved against the wrong one would be green here.
        self.write("decompiled/common/00CF.asm", "; a listing\n")
        self.self_indexed_with("program,addr,name,evidence\n",
                               rows=["common,00CF,walker,"
                                     "decompiled/common/00CF.asm\n"])
        result = self.check()
        self.assertEqual([token for _, token, _ in result.evidence_missing],
                         ["decompiled/common/00CF.asm"])
        self.assertEqual(result.evidence_unresolved, [])

    def test_a_token_matching_no_path_rule_is_unresolved_and_does_not_fail(self):
        # The calibration line again, in the fifth direction: a URL or an
        # address range is "not resolved by this method" and never "absent".
        self.self_indexed_with(
            "program,addr,name,evidence\n",
            rows=["common,00CF,walker,0x0700-0x07FF\n",
                  "common,00CE,other,see the build log\n"])
        result = self.check()
        self.assertEqual(result.evidence_missing, [])
        self.assertEqual([token for _, token, _ in result.evidence_unresolved],
                         ['0x0700-0x07FF', 'see the build log'])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctti.report(
                result.gaps, result.missing, result.unresolved,
                (result.feeds_missing, result.feeds_unresolved),
                (result.nested_missing, result.nested_unresolved),
                (result.evidence_missing, result.evidence_unresolved),
                result.evidence_columnless), 0)
        self.assertIn('not checked, not absent', err.getvalue())

    def test_a_csv_named_twice_is_read_once(self):
        # Which CSVs are read is structural -- the ones a nested table names --
        # and the committed README names `ghidra-functions.csv` five times.
        # Reading it per row rather than per distinct name would count the same
        # cell five times and make the tally a statement about the README's
        # prose instead of about the column.
        self.write_repo("ec/decompiled/common/00CF.asm")
        name = "a-set"
        self.write(f"{name}/index.csv",
                   "program,addr,name,evidence\ncommon,00CF,walker,"
                   "ec/decompiled/common/00CF.asm\n")
        self.nested_tables(
            name, "`index.csv` row `0x00CF` | the row",
            "`index.csv` row `0x00CF` | named a second time",
            "`index.csv` row `0x00CF` | and a third")
        result = self.check()
        self.assertEqual((result.evidence_csvs, result.evidence_cells,
                          result.evidence_tokens), (1, 1, 1))
        self.assertEqual((result.evidence_missing, result.evidence_unresolved),
                         ([], []))

    def test_a_csv_nobody_names_is_not_read(self):
        # The discovery rule, from the other side. A `*.csv` beside a directory
        # is the "top-level files with no row" gap the shipped tool already
        # declines, and walking every CSV under `testdata/` would print an
        # `unresolved` line for each of the twenty-odd loose fixtures on every
        # run -- for a shape no index promised anything about.
        self.write(f"loose.csv", "program,addr,name,evidence\ncommon,00CF,w,\n")
        self.nested_tables("a-set", "`decompiled/common/00CF.asm` | a listing")
        result = self.check()
        self.assertEqual((result.evidence_csvs, result.evidence_cells,
                          result.evidence_tokens, result.evidence_missing,
                          result.evidence_unresolved), (0, 0, 0, [], []))


class ParsesOnlyTheFirstColumn(unittest.TestCase):
    """The parse itself, because a bad regex here passes vacuously.

    A `table_cells()` that found nothing matches an empty tree, and an empty
    tree is green -- the same §14b defect the runner's empty-discovery guard
    exists for, one level down. It also holds what the re-implementation onto
    `markdown_tables` must not have changed: the first column by default, the
    second on request, and no row at all out of a table headed something else.
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

    # A table ahead of the index's own, in the nested README's header and
    # separator spelling. A nested index is not the index, and the wrapper has
    # to say which is which.
    ScratchNESTED = '\n'.join([
        '| file / row | what it pins |',
        '|---|---|',
        '| `a.asm` | a listing |',
        '',
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

    def test_the_file_table_is_picked_out_of_several(self):
        # `table_cells` is a wrapper over the walker rather than a second
        # reader, so the thing worth pinning is that the wrapper still finds
        # the index's own table in a file carrying two -- the shape
        # `call-graph/README.md` has, and the shape the nested reader takes
        # three of. The `a \`| b.csv\` description` cell is split by its own
        # pipe, which is the shipped reader's behaviour and is harmless: the
        # third column is not read in either direction.
        self.assertEqual(ctti.markdown_tables(self.ScratchNESTED + self.INDEX),
                         [(['file / row', 'what it pins'],
                           [['`a.asm`', 'a listing']]),
                          (['File', 'Feeds', 'What it constructs'],
                           [['`a.csv`', '`../tool.py`', 'a `', 'b.csv` description'],
                            ['`c.csv` + `d.csv`', '`../tool.py`', 'two files']])])
        self.assertEqual(ctti.table_cells(self.ScratchNESTED + self.INDEX),
                         ['`a.csv`', '`c.csv` + `d.csv`'])

    def test_the_second_column_is_read_as_the_second_column(self):
        # Columns are counted from 1, so `column=2` is `Feeds` and not the prose
        # beside it. Reading the third column instead would resolve every
        # address the descriptions quote, which is not a rule this tool has.
        self.assertEqual(ctti.table_cells(self.INDEX, column=2),
                         ['`../tool.py`', '`../tool.py`'])


class TheReachedSomethingRule(RunsTheTool):
    """The one rule about a run's tallies, over whatever tree it is handed.

    `check_testdata_index.py`'s docstring says there is no floor on either tally
    and that the suite asserts non-emptiness instead. That is this. The root is
    a parameter rather than `ctti.TESTDATA` so the rule is a property of a run
    and can be pointed at a scratch tree beside the committed one; the two are
    held to the same method, so neither half can be edited alone.

    `run_tool()` is inherited from `RunsTheTool` rather than written here, so
    the committed case below and a scratch case that only wants the runner are
    the same runner.
    """

    def assert_the_run_reached_something(self, root, repo=None):
        """Assert a run over `root` read something, and that it read it.

        Each of the five tallies non-zero, and `tokens > rows` on top of them.
        The tallies are parsed out of what the run *printed* rather than read
        off a `Result`, because the claim being pinned is the docstring's: they
        print whether or not they found anything, since a run that checked
        nothing and a run that found nothing look the same from the exit code
        alone. The parse is part of what is held here, and each is named in its
        message so a case that is refused knows which clause said so.

        The order is the order the output prints, because a case that is
        refused should be refused by the *first* thing it failed to reach:
        a tree with a directory and a rowless index is short a row, not short
        everything, and a tree with one token per row is short only the
        relation between two tallies it did reach. Every label is unique across
        the printed lines, because the parse keys one flat dict by label --
        `row(s)` and `path token(s)` are already taken by the two directions
        before it.
        """
        rc, out, err = self.run_tool(root, repo)
        self.assertEqual(rc, 0, err)
        counts = {}
        for line in out.splitlines():
            for piece in re.split(r'[:,]', line):
                number, _, label = piece.strip().partition(' ')
                if number.isdigit() and label:
                    counts[label] = int(number)
        for name, label in (('directories', 'testdata/ directories'),
                            ('rows', 'table row(s)'),
                            ('tokens', 'path token(s)'),
                            ('feeds cells', 'Feeds cell(s)'),
                            ('feeds pointers', 'tool pointer(s)'),
                            ('nested rows', 'row(s)'),
                            ('nested checks', 'check(s)'),
                            ('fixture CSVs', 'fixture CSV(s)'),
                            ('evidence cells', 'evidence cell(s)'),
                            ('evidence tokens', 'evidence path token(s)')):
            self.assertGreater(
                counts.get(label, 0), 0,
                f"the run reached no {name}: a run that checked nothing and a "
                "run that found nothing look the same from the exit code alone")
        self.assertGreater(counts['path token(s)'], counts['table row(s)'],
                           "one row holds several paths; a token count that "
                           "equals the row count means only the first is read")


class TheCommittedTree(TheReachedSomethingRule, unittest.TestCase):
    """The real thing: the index and the tree beside it currently agree.

    This goes red on any future edit that drifts the index and the tree apart in
    any of the five directions. It does not go red on an edit to what a row says
    its fixture is: that is the third column, which this tool does not read, and
    which both of the index's past hand-repairs were. It does not go red on the
    tree being a different size either, which is what
    `TheTalliesAreNotAFloor` is about.
    """

    def test_the_committed_index_and_tree_agree(self):
        rc, out, err = self.run_tool(ctti.TESTDATA)
        self.assertEqual(rc, 0, err)
        self.assertIn('table row(s)', out)

    def test_the_run_actually_reached_every_source(self):
        # A run that reports 0 directories and 0 rows is green for the wrong
        # reason, and the tallies are the only way to tell. This is not a floor
        # on coverage: nothing says the numbers have to stay where they are,
        # only that a run reaching nothing fails.
        self.assert_the_run_reached_something(ctti.TESTDATA)

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
        # report nobody can paste into an editor is a report nobody opens. The
        # three pairs added later are passed here too, and they are where the
        # `where` earns its keep: one of the six lines names this index, one
        # names the self-indexed README beside it, one names the fixture CSV
        # holding the cell, and the sixth names the fixture CSV that has no
        # `evidence` column in it at all. The last three carry a path this tool
        # has to make relative against `REPO` rather than against a fresh
        # `HERE/../..`, which under a patched scratch base would print a `..`
        # chain. None of the six is a disagreement, so the count is still five.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(ctti.report(
                [('ec/tools/testdata', 'newset')],
                [('ec/tools/testdata/README.md', 'gone.csv', 'gone.csv')], [],
                ([('ec/tools/testdata/README.md', '../gone.py', 'gone.py')], []),
                ([('ec/tools/testdata/call-graph/README.md', 'gone.asm',
                   'gone.asm')], []),
                ([('ec/tools/testdata/call-graph/ghidra-functions.csv',
                   'ec/decompiled/bank0/0EA2.asm',
                   'ec/decompiled/bank0/0EA2.asm')], []),
                [('ec/tools/testdata/call-graph/index.csv', 'index.csv',
                  'index.csv has no `evidence` column')]), 5)
        lines = err.getvalue().splitlines()
        self.assertTrue(lines[0].startswith('ec/tools/testdata/newset/:'), lines[0])
        self.assertIn('ec/tools/testdata/README.md', lines[1])
        self.assertIn('`Feeds` column', lines[2])
        self.assertIn('ec/tools/testdata/call-graph/README.md', lines[3])
        self.assertIn('`evidence` column', lines[4])
        self.assertTrue(lines[5].startswith(
            'ec/tools/testdata/call-graph/index.csv:'), lines[5])
        # Six findings and the count, which is five because the sixth is not a
        # disagreement. A run whose line count drifted from its own total is a
        # report that has grown a seventh shape nobody is reading.
        self.assertEqual(len(lines), 7)
        self.assertTrue(lines[6].startswith('5 disagreement(s)'), lines[6])
        for line in lines:
            self.assertNotIn('/../', line)
            self.assertFalse(line.startswith('/'), line)

    def test_the_committed_run_reads_all_five_sources(self):
        # The figures are today's, and the claim is not that they have to stay:
        # it is that a run which reached nothing is distinguishable from a run
        # which found nothing. `TheTalliesAreNotAFloor` is what says the first
        # of those two things, and this is the same five tallies on the real
        # tree rather than a scratch one.
        rc, out, err = self.run_tool(ctti.TESTDATA)
        self.assertEqual(rc, 0, err)
        counts = {}
        for line in out.splitlines():
            for piece in re.split(r'[:,]', line):
                number, _, label = piece.strip().partition(' ')
                if number.isdigit() and label:
                    counts[label] = int(number)
        self.assertEqual(counts['testdata/ directories'], 13)
        self.assertEqual((counts['named in the index'], counts['self-indexed'],
                          counts['gap(s)']), (12, 1, 0))
        self.assertEqual((counts['table row(s)'], counts['path token(s)']),
                         (27, 34))
        self.assertEqual((counts['Feeds cell(s)'], counts['tool pointer(s)']),
                         (27, 29))
        self.assertEqual((counts['self-indexed README(s)'], counts['table(s)'],
                          counts['row(s)'], counts['check(s)']),
                         (1, 3, 19, 21))
        # Ten cells carry a value and eleven tokens are checked over them: the
        # one `;`-joined cell is the difference, and it is a decidable fact
        # about the two committed CSVs. Not a floor -- see the comment above.
        self.assertEqual((counts['fixture CSV(s)'], counts['evidence cell(s)'],
                          counts['evidence path token(s)']), (2, 10, 11))
        # Every pointer is resolved and nothing is unreadable, which is the
        # "the index and the tree currently agree" half. It is a statement
        # about today and not a floor: the tallies above are what a run that
        # reached nothing would be caught by, in either direction.
        self.assertEqual([line.rsplit(', ', 2)[1:] for line in out.splitlines()
                          if ' resolved, ' in line],
                         [['0 missing', '0 unresolved']] * 4)

    def test_the_committed_feeds_column_carries_a_flag_suffix(self):
        # The issue's "also asserted over the committed tree, where three rows
        # carry it": the flag suffix is not a shape this suite invented. The
        # three rows are also the reason the cut is not optional -- without it
        # this column reports three misses on the day the check lands.
        with open(ctti.INDEX, encoding='utf-8') as f:
            cells = ctti.table_cells(f.read(), column=2)
        flagged = [cell for cell in cells if '--dump-pair' in cell]
        self.assertEqual(len(flagged), 3)
        for cell in flagged:
            self.assertEqual(ctti.feeds_pointers(cell),
                             ['../grade_0751_isolation.py'])

    def test_the_committed_call_graph_readme_names_a_bank0_listing(self):
        # The one cell this branch corrects, pinned here so the fix is in the
        # suite and not only in the write-up. Both committed CSVs and the file
        # on disk agree it is a `bank0` row: `index.csv:2` and
        # `ghidra-functions.csv:2` both name `ec/decompiled/bank0/0EA2.asm`, and
        # the fixture carries `decompiled/bank0/0EA2.asm` and no `common` one.
        # A decidable fact about three committed files, and nothing at all about
        # what the fixture exercises.
        readme = os.path.join(ctti.TESTDATA, 'call-graph', 'README.md')
        with open(readme, encoding='utf-8') as f:
            cells = [row[0] for _, rows in ctti.markdown_tables(f.read())
                     for row in rows]
        self.assertIn('`decompiled/bank0/0EA2.asm`', cells)
        self.assertNotIn('`decompiled/common/0EA2.asm`', cells)
        self.assertTrue(os.path.isfile(os.path.join(
            ctti.TESTDATA, 'call-graph', 'decompiled', 'bank0', '0EA2.asm')))

    def test_the_committed_evidence_cells_name_listings_the_real_tree_has(self):
        # The fix #780 makes, pinned here so it is in the suite and not only in
        # the write-up: no `evidence` cell in either fixture CSV names a path the
        # real tree lacks, and the one `;`-joined cell resolves as two pointers
        # rather than one. A decidable fact about three committed files, and
        # nothing at all about what the fixture exercises -- the `.c` beside the
        # `.asm` is a pointer this check confirms exists, and says nothing
        # about whether it is a correct reading of the function.
        directory = os.path.join(ctti.TESTDATA, 'call-graph')
        found = ctti.evidence_pointers('ghidra-functions.csv', directory,
                                       ctti.REPO)
        self.assertEqual((found.missing, found.unresolved), ([], []))
        self.assertEqual((found.cells, found.tokens), (5, 6))
        found = ctti.evidence_pointers('index.csv', directory, ctti.REPO)
        self.assertEqual((found.missing, found.unresolved), ([], []))
        self.assertEqual((found.cells, found.tokens), (5, 5))
        # The `;` split is what makes the two tallies differ at all, and the
        # committed `bank0,0EA2` row is the one cell that carries both: without
        # it, `tokens` and `cells` would be the same number over both files and
        # a reader could not tell the rule apart from a per-cell count.
        self.assertEqual(found.tokens, found.cells)


class TheTalliesAreNotAFloor(ScratchIndex, TheReachedSomethingRule,
                             unittest.TestCase):
    """`TheReachedSomethingRule`, pointed at scratch trees, from both sides.

    `ParsesOnlyTheFirstColumn`'s docstring already names the failure this class
    walked into one level up -- "a `table_cells()` that found nothing matches an
    empty tree, and an empty tree is green" -- and the suite answered the parser
    for it with a case, while answering the run itself with three hand-typed
    integers. So the one check that a run reached anything was the one thing a
    new fixture directory turned red, as a bare
    `AssertionError: (14, 28, 35) != (13, 27, 34)`, in a suite whose module
    docstring says the only thing that notices a silent check is a reader who
    has already been misled.

    Two trees either side of today's size, so the assertion cannot be reading a
    minimum, and four it still refuses, so it cannot be reading nothing. Every
    case calls the method the committed case calls: a floor reinstated in the
    helper fails here, and a clause dropped here fails on the committed tree
    being the wrong size to notice.

    **This class is the reason `ScratchIndex.self_indexed()` grows an `evidence`
    column**, and the docstring above is why that edit is not optional rather
    than tidy. The helper now refuses a run that reached no `evidence` cell, so
    a `self_indexed()` without one would refuse all four of these on the fifth
    clause and answer the event this class exists to handle with a failure
    nobody had caused.
    """

    def test_a_tree_carrying_more_of_them_than_today_is_green(self):
        # The event #744 is about: a fourteenth `0751-isolation-run-<case>/`
        # arriving with its own row. Bigger than the committed tree on one
        # tally and smaller on the other two, which is the strongest form of
        # the pin -- any assertion reading a size, a minimum or an exact set,
        # refuses this tree. The directories are named in prose rather than by a
        # row each, which leaves the table carrying the one two-token row below.
        names = [f"0751-isolation-run-case{n:02d}" for n in range(14)]
        for name in names:
            self.mkdir(name)
            self.write(f"{name}/a.csv")
        self.write(f"{names[0]}/c.csv")
        self.prose(" ".join(f"`{name}/`" for name in names) + "\n")
        self.self_indexed()
        # The second token is load-bearing: a one-token table leaves
        # `tokens == rows`, the helper's `tokens > rows` refuses it, and the
        # case would be proving the wrong thing.
        self.row(f"`{names[0]}/a.csv` + `{names[0]}/c.csv`")
        self.write_index()
        self.assert_the_run_reached_something(self.testdata, self.repo)

    def test_a_tree_carrying_fewer_of_them_than_today_is_green(self):
        # The other direction a floor would catch, and the same two edits from
        # the other end: a directory removed, a row dropped. One of each where
        # the committed tree has thirteen and twenty-seven, so an assertion
        # reading a minimum is caught here even if the case above did not
        # reach it.
        self.mkdir("0751-isolation-run-only")
        self.write("0751-isolation-run-only/a.csv")
        self.write("0751-isolation-run-only/c.csv")
        self.prose("`0751-isolation-run-only/` is the set the procedure names.\n")
        self.self_indexed()
        self.row("`0751-isolation-run-only/a.csv` + `0751-isolation-run-only/c.csv`")
        self.write_index()
        self.assert_the_run_reached_something(self.testdata, self.repo)

    def test_an_empty_tree_reaches_nothing(self):
        # The rule is not "any tree passes". `(0, 0, 0)` is the vacuous check
        # the module docstring is about, on the tally side, and the clause that
        # refuses it names the first tally because that is the one that is zero.
        self.write_index()
        with self.assertRaises(AssertionError) as caught:
            self.assert_the_run_reached_something(self.testdata, self.repo)
        self.assertIn('directories', str(caught.exception))

    def test_a_tree_with_a_directory_and_a_rowless_index_reaches_no_row(self):
        # `ParsesOnlyTheFirstColumn`'s shape one level up: a `table_cells()`
        # that reads nothing over a tree that has something is the same
        # vacuous pass as an empty tree, and `rows == 0` is the clause that
        # catches it. The header is there and carries no row, which is what a
        # moved table header or a broken split would leave behind -- and the
        # directory is named in prose, so the run still exits 0 and only the
        # tally says what happened.
        self.mkdir("0751-isolation-run-rowless-index")
        self.write("0751-isolation-run-rowless-index/a.csv")
        self.prose("`0751-isolation-run-rowless-index/` is named in prose only.\n")
        self.self_indexed()
        self.write_index()
        with self.assertRaises(AssertionError) as caught:
            self.assert_the_run_reached_something(self.testdata, self.repo)
        self.assertIn('rows', str(caught.exception))

    def test_one_token_per_row_is_refused(self):
        # The sharpest of the five, because every other clause passes here: a
        # directory is reached, a row is read, `rc` is 0. `tokens > rows` is the
        # only thing standing between this tree and a green run, which is what
        # stops that clause being dropped as redundant -- the committed tree
        # carries six multi-path cells today and would be the only thing left to
        # notice.
        self.mkdir("0751-isolation-run-one-token")
        self.write("0751-isolation-run-one-token/a.csv")
        self.prose("`0751-isolation-run-one-token/` is the set the procedure names.\n")
        self.self_indexed()
        self.row("`0751-isolation-run-one-token/a.csv`")
        self.write_index()
        with self.assertRaises(AssertionError) as caught:
            self.assert_the_run_reached_something(self.testdata, self.repo)
        self.assertIn('only the first is read', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
