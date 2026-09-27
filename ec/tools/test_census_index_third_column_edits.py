#!/usr/bin/env python3
"""Tests for `census_index_third_column_edits.py`.

The tool's output is the number the corpus's next several sentences are about,
so what is worth pinning is not the number -- the repository's standing rule is
that an expected count turns every added fixture into a failure -- but the four
ways it could be wrong quietly:

  * **the reader comparing nothing.** `table_cells(text, column=3)` returns
    `[]` for a file whose tables are headed `file / row`, so over the committed
    **nested** index it compares two empty lists, finds the lengths equal and
    reports no third-column difference. That is the committed tree's own
    silent zero, and it is why the population is two populations and why an
    image the reader cannot locate is `not read by this method` rather than
    quiet. Both the inline case and the scratch one are below, and the second
    exists because a guard that only fires on a string is not a guard.
  * **a refusal being read as an edit.** Two images with different row counts
    are refused rather than aligned, and that refusal **is** the separation
    between a cell edit and a row addition -- adding a row moves the count, so
    row additions land in the refused class and on neither side.
  * **a failure being read as a zero.** A revision this clone cannot resolve is
    `not measurable in this clone` at exit 2; a census that located no index
    exits non-zero rather than returning clean. Every negative in this tool is
    `not found by this method`.
  * **a count being read as a judgement.** An edit is an edit, and the word for
    whether one was wrong lives in the write-up. That is asserted over the
    tool's own rendered output rather than left in the docstring's promise --
    and the exemption is pinned beside it, because there is one and it is real:
    a **commit subject is quoted verbatim**, and this history's carries the word.

The cases that need a repository build one, in a `tempfile` scratch tree, on
the `tools/test_agent_gates_patches.py` precedent: `git init` into a throwaway
tree, `shutil.which('git')` to skip, repo-local identity, and nothing here
writes to the working tree. The last class reads this repository's own history
and **skips** when the clone is too shallow to answer, so the suite stays
green in a depth-1 checkout the way `test_agent_gates_patches.py` does -- and
not the way `test_walk_budget_census.py` does, which asserts and fails, and
which is right for a count of a *committed* tree and wrong here.
"""
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import census_index_third_column_edits as ct  # noqa: E402

# The revisions this suite names, given here rather than discovered. A case
# that discovered its own subject could not tell a detector that stopped
# working from a detector with nothing to find; what the census adds over
# #978's pair is that the pair was never the population, which is what the
# committed class below is for. These are the shas the suite pins, not a
# claim about how many the history holds — the census reports that count and
# this suite deliberately never asserts it.
REPAIRS = (("565b6f3c", "#502"), ("8f4f211f", "#720"))
NESTED_REPAIR = ("1813fe98", "#746")

# A `File`/`Feeds`/description table with the header
# `check_testdata_index.py` locates the root index by, and a `Feeds` cell
# naming a tool beside `testdata/`.
HEADER = ("| File | Feeds | What it constructs |\n"
          "|---|---|---|\n")

# The nested shape, and the header that makes a third-column reader return
# nothing at all. This is the committed `call-graph/README.md`'s own header, and
# it is the whole of finding 1: `table_cells` matches on the first header cell
# being `File`, finds no such table, and answers `[]`.
NESTED_HEADER = "| file / row | what it pins |\n|---|---|\n"


def index(rows, fixture='fix.csv', feeds='../grade_thing.py'):
    """A root-index image over `rows`, each a description cell."""
    return ("# scratch\n\n" + HEADER
            + "".join(f"| `{fixture}` | `{feeds}` | {cell} |\n" for cell in rows)
            + "\nA paragraph below the table, which no row reader reads.\n")


def nested(rows, first='decompiled/common/0EA2.asm'):
    """A nested-index image over `rows`, each a what-it-pins cell."""
    return ("# scratch\n\n" + NESTED_HEADER
            + "".join(f"| `{first}` | {cell} |\n" for cell in rows)
            + "\nA paragraph below the table.\n")


def git(*args, cwd):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                          text=True)


def has_git():
    return shutil.which("git") is not None


@contextmanager
def scratch_repo():
    """A throwaway repository, holding nothing until a case writes to it.

    Two commits are the shape this tool measures between, and both are made by
    the cases rather than imported: the tool's subject is a repository's
    history, and a suite that reached into this one for it would be skipped in
    a shallow checkout along with the case that can catch a regression.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        git("init", "-q", ".", cwd=root)
        # Repo-local, not global: a suite that wrote a global identity to make
        # its own commits would edit the machine it runs on, and CI runners and
        # a developer's laptop should come out of it the same.
        git("config", "user.email", "census@example.invalid", cwd=root)
        git("config", "user.name", "census index third column edits", cwd=root)
        yield root


def commit(root, message):
    git("add", "-A", cwd=root)
    done = git("commit", "-q", "-m", message, cwd=root)
    if done.returncode != 0:
        raise AssertionError(f"scratch commit failed: {done.stderr}")
    return git("rev-parse", "HEAD", cwd=root).stdout.strip()


def readme(root, text):
    """Write `text` where the root index lives and commit it, -> the sha."""
    data = root / "ec" / "tools" / "testdata"
    data.mkdir(parents=True, exist_ok=True)
    (data / "README.md").write_text(text)
    return commit(root, "index")


def seed(root):
    """An unrelated first commit, so the revisions a case measures between are
    not a root commit.

    A root commit has no parent, which is its own class and a fact about the
    revision rather than a measurement. A two-revision case that wanted the
    first of them to be `no-parent` would be testing the ordering of the class
    list rather than the class, and the case that wants `no-parent` says so
    directly instead.
    """
    (root / "unrelated.txt").write_text("nothing the index names\n")
    return commit(root, "unrelated")


def record(sha, verdict="edited", path="ec/tools/testdata/README.md",
           kind="root", why="", rows=()):
    return ct.Revision(path, kind, sha, f"{sha} -- a subject", verdict, why,
                       list(rows))


class DescriptionColumnTests(unittest.TestCase):
    """`repair_rows()` over inline text, with no git in it at all.

    A detector that found nothing would agree with a detector that found no
    edit, on any pair of images that differ only where the tool cannot look.
    """

    def test_a_changed_description_cell_is_reported_with_its_row(self):
        rows, why = ct.repair_rows(index(["the mark label", "unchanged"]),
                                   index(["the mark label", "reworded"]))
        self.assertIsNone(why)
        self.assertEqual(rows, [2])

    def test_a_first_column_only_edit_is_not_a_description_edit(self):
        before = index(["the same cell"])
        rows, why = ct.repair_rows(before,
                                   before.replace("`fix.csv`", "`other.csv`"))
        self.assertIsNone(why)
        self.assertEqual(rows, [])

    def test_a_feeds_only_edit_is_not_a_description_edit(self):
        before = index(["the same cell"])
        rows, _why = ct.repair_rows(
            before, before.replace("`../grade_thing.py`", "`../other.py`"))
        self.assertEqual(rows, [])

    def test_a_reworded_sentence_is_an_edit_even_with_the_literals_kept(self):
        # The detector is about the cell, not the literals. An implementation
        # keyed on addresses would report nothing here and the report would
        # read as "no edit", which is the same silent zero as finding 1 with a
        # different cause.
        rows, _why = ct.repair_rows(index(["the label `0x0751` everywhere"]),
                                   index(["the label `0x0751`, everywhere"]))
        self.assertEqual(rows, [1])

    def test_images_with_different_row_counts_are_refused_not_aligned(self):
        # Row numbers are positions. Zipping a 2-row image against a 3-row one
        # would call rows 1 and 2 "changed" and say nothing about row 3, which
        # does not exist on one side -- and it is this refusal, not a guess,
        # that is what tells a cell edit from a row addition.
        rows, why = ct.repair_rows(index(["a", "b"]), index(["a", "b", "c"]))
        self.assertEqual(rows, [])
        self.assertIsNotNone(why)
        self.assertIn("not found by this method", why)

    def test_text_with_no_table_reports_nothing_rather_than_raising(self):
        rows, why = ct.repair_rows("prose only\n", "prose only\n")
        self.assertEqual(rows, [])
        self.assertIsNone(why)


class UnreadableGuardTests(unittest.TestCase):
    """The guard that keeps finding 1 from printing a clean, wrong zero.

    `table_cells(text, column=3)` returns `[]` for a file whose tables are
    headed `file / row`, so a census built only on `repair_rows()` compares two
    empty lists over the committed nested index, finds the lengths equal and
    reports no third-column difference. These are the cases that would fail if
    a later edit "fixed" the census into printing a zero.
    """

    def test_a_nested_shaped_image_is_not_located_by_the_third_column_reader(self):
        # The reader agrees there are no description cells, and the *shape*
        # check is what says the file plainly carries tables anyway. Without
        # the second, the first is indistinguishable from an empty answer.
        self.assertEqual(ct.table_cells(nested(["a case"]), column=3), [])
        self.assertEqual(len(ct.markdown_tables(nested(["a case"]))), 1)
        self.assertFalse(ct.located(nested(["a case"]), "root"))
        self.assertTrue(ct.located(nested(["a case"]), "nested"))

    def test_a_root_shaped_image_with_no_rows_is_located_rather_than_unread(self):
        # The other half of the distinction. A `File`-headed table with no data
        # rows is a real, empty answer; refusing it would put every row
        # addition in the population in a class it does not belong to.
        self.assertTrue(ct.located(HEADER, "root"))
        self.assertFalse(ct.located("prose only, no table here\n", "root"))

    def test_repair_rows_over_two_nested_images_finds_nothing_and_says_so(self):
        # What the guard is protecting against, shown as the failure it would
        # be without one: the two lists are equal, the lengths match, and the
        # answer looks exactly like "this index was never edited in its third
        # column" -- which for a two-column file is true and useless.
        rows, why = ct.repair_rows(nested(["a case"]), nested(["another case"]))
        self.assertEqual(rows, [])
        self.assertIsNone(why)
        # ... and what a caller has to ask before believing it.
        self.assertFalse(ct.located(nested(["a case"]), "root"))


class NestedColumnTests(unittest.TestCase):
    """The nested reader, which is a differently-shaped measurement."""

    def test_a_repointed_pointer_is_found_with_its_table_and_row(self):
        edited, refused = ct.nested_edits(
            nested(["the worked example"], first="decompiled/common/0EA2.asm"),
            nested(["the worked example"], first="decompiled/bank0/0EA2.asm"))
        self.assertEqual(refused, [])
        # The backticks are part of the cell: `row_cells()` splits on `|` and
        # strips whitespace, and a reader that also stripped the backticks
        # would be a second reader that could disagree about what a cell is.
        self.assertEqual(edited, [(1, 1, "`decompiled/common/0EA2.asm`",
                                   "`decompiled/bank0/0EA2.asm`")])

    def test_a_second_cell_edit_is_not_a_pointer_edit(self):
        # The second column of a nested table is prose about the case, and a
        # token lifted out of it is a pointer the index never made. Rewording
        # it is a prose edit, not the repointing the reader is for.
        edited, refused = ct.nested_edits(nested(["a case"]),
                                          nested(["a reworded case"]))
        self.assertEqual(edited, [])
        self.assertEqual(refused, [])

    def test_a_growth_refuses_that_table_and_leaves_the_others_readable(self):
        # Two images with a different number of *tables* are not a comparison.
        # Two images where one table grew are, for every other table, and a
        # census that gave up on the whole file would report the rows beside
        # the growth as "not found by this method" for no reason at all.
        grew = "# scratch\n\n" + NESTED_HEADER \
            + "| `a.asm` | first |\n| `b.asm` | second |\n"
        both = "# scratch\n\n" + NESTED_HEADER \
            + "| `a.asm` | first |\n| `b.asm` | second |\n| `c.asm` | third |\n"
        edited, refused = ct.nested_edits(grew, both)
        self.assertEqual(edited, [])
        self.assertEqual(len(refused), 1)
        self.assertIn("grew", refused[0][1])

    def test_a_growth_that_also_edited_a_cell_is_stated_as_not_separable(self):
        # The three rows are the same three before and after, and one of them
        # is reworded. The method cannot tell that apart from a row added
        # beside an edit, and says so rather than reporting the one row it
        # could line up as though it were the whole answer.
        before = nested(["a", "b", "c"])
        after = nested(["a", "b", "c", "d"])
        _edited, refused = ct.nested_edits(before, after)
        self.assertEqual(len(refused), 1)
        self.assertIn("not separable", refused[0][1])

    def test_a_table_that_disappeared_refuses_rather_than_aligning(self):
        one, two = nested(["a"]), nested(["a"]) + nested(["b"], first="x.asm")
        edited, refused = ct.nested_edits(one, two)
        self.assertEqual(edited, [])
        self.assertEqual(len(refused), 1)
        self.assertIn("1 and 2 table(s)", refused[0][1])
        self.assertIn("counted on neither side", refused[0][1])


class PopulationTests(unittest.TestCase):
    """Which reader a path gets, and why the pathspec is a glob magic one.

    The bare `ec/tools/testdata/**/README.md` matches the nested index and not
    the root one, so a census built on it would measure the nested population
    and publish it as a count over the root. A missing root index is not a
    zero; it is a census that looked at half a tree.
    """

    def test_the_reader_follows_the_path_rather_than_a_list(self):
        self.assertEqual(ct.reader_for("ec/tools/testdata/README.md"), "root")
        self.assertEqual(
            ct.reader_for("ec/tools/testdata/call-graph/README.md"), "nested")
        # A self-indexed directory this file has never seen is covered with no
        # edit, the same argument the index checker's own clause makes.
        self.assertEqual(
            ct.reader_for("ec/tools/testdata/next-one/README.md"), "nested")

    def test_the_population_pathspec_is_the_glob_magic_spelling(self):
        self.assertTrue(ct.POPULATION.startswith(":(glob)"),
                        "without :(glob) the ** matches the nested index and "
                        "not the root one, and the census silently measures "
                        "half the population")


@unittest.skipUnless(has_git(), 'no git on PATH')
class ScratchCensusTests(unittest.TestCase):
    """The classes over a repository this suite builds, one per class.

    Each case is the shape of a committed answer at a size where the answer is
    not in doubt, and each is a class the tool can be wrong about quietly: a
    census that put a row addition in `edited`, or a first-column-only commit
    in it, would publish a number nobody could check against the cells.
    """

    def setUp(self):
        if not has_git():
            self.skipTest('no git on PATH')

    def _classify(self, root, path=ct.ROOT_INDEX if hasattr(ct, "ROOT_INDEX")
                  else "ec/tools/testdata/README.md"):
        return [ct.classify(path, rev, repo=str(root)) for rev in
                ct.revisions(path, repo=str(root))[0]]

    def test_a_third_column_edit_lands_in_edited_with_both_cells(self):
        with scratch_repo() as root:
            seed(root)
            readme(root, index(["the mark label", "unchanged"]))
            readme(root, index(["the mark label", "reworded"]))
            records = [r[0] for r in self._classify(root)]
        # Newest first, and the older record is the commit that *created* the
        # file: its first parent has no `README.md`, so there is no image to
        # compare and it is `unborn` rather than a revision with no edit in it.
        self.assertEqual([r.verdict for r in records],
                         [ct.EDITED, ct.UNBORN])
        found = records[0]
        self.assertEqual(found.kind, "root")
        self.assertEqual(len(found.rows), 1)
        self.assertEqual(found.rows[0].position, "row 2")
        self.assertEqual(found.rows[0].first, "`fix.csv`")
        self.assertIn("unchanged", found.rows[0].before)
        self.assertIn("reworded", found.rows[0].after)

    def test_adding_a_row_lands_in_refused_and_on_neither_side(self):
        with scratch_repo() as root:
            seed(root)
            readme(root, index(["a", "b"]))
            readme(root, index(["a", "b", "c"]))
            found = self._classify(root)[0][0]
        self.assertEqual(found.verdict, ct.REFUSED)
        self.assertEqual(found.rows, [])
        self.assertIn("grew", found.why)
        self.assertIn("counted on neither side", found.why)

    def test_a_first_column_only_commit_lands_in_unchanged(self):
        # The population's most common answer, and the one a census that
        # reported silence over would let a reader take for "no edit anywhere".
        with scratch_repo() as root:
            seed(root)
            readme(root, index(["a case"], fixture="fix.csv"))
            readme(root, index(["a case"], fixture="other.csv"))
            found = self._classify(root)[0][0]
        self.assertEqual(found.verdict, ct.UNCHANGED)
        self.assertEqual(found.rows, [])

    def test_a_repointed_nested_pointer_lands_in_the_nested_edited_class(self):
        path = "ec/tools/testdata/fixture/README.md"
        with scratch_repo() as root:
            seed(root)
            data = root / "ec" / "tools" / "testdata" / "fixture"
            data.mkdir(parents=True)
            (data / "README.md").write_text(
                nested(["a case"], first="decompiled/common/0EA2.asm"))
            commit(root, "nested")
            (data / "README.md").write_text(
                nested(["a case"], first="decompiled/bank0/0EA2.asm"))
            target = commit(root, "repointed")
            found = ct.classify(path, target, repo=str(root))[0]
        self.assertEqual(found.verdict, ct.EDITED)
        self.assertEqual(found.kind, "nested")
        self.assertEqual(found.rows[0].position, "table 1, row 1")

    def test_a_nested_index_read_as_a_root_one_is_unreadable_not_silent(self):
        # Finding 1, through `classify()` rather than through a string. The
        # file is at the root index's own path, so the population says the
        # third-column reader, and the shape check is the only thing between
        # that and a clean "no edit" over a file that carries two tables.
        with scratch_repo() as root:
            seed(root)
            readme(root, nested(["a case"]))
            readme(root, nested(["another case"]))
            records = [r[0] for r in self._classify(root)]
        # The older record is `unborn` and not `unreadable`, and the order is
        # the point: one image of that pair does not exist, so saying anything
        # about what a reader could have read in it is a claim about nothing.
        self.assertEqual([r.verdict for r in records],
                         [ct.UNREADABLE, ct.UNBORN])
        self.assertIn("not read by this method", records[0].why)

    def test_a_commit_before_the_file_existed_lands_in_unborn(self):
        with scratch_repo() as root:
            (root / "unrelated.txt").write_text("nothing the index names\n")
            commit(root, "unrelated")
            readme(root, index(["a case"]))
            found = self._classify(root)[0][0]
        self.assertEqual(found.verdict, ct.UNBORN)
        self.assertIn("not at the first parent", found.why)

    def test_a_root_commit_lands_in_no_parent_and_not_in_a_zero(self):
        # A root commit is the one revision with nothing to compare against,
        # and it is a fact about the revision rather than a measurement. The
        # committed history has none of these on either index, so a scratch
        # repository is the only place the class can be exercised at all.
        with scratch_repo() as root:
            readme(root, index(["a case"]))
            found = self._classify(root)[0][0]
        self.assertEqual(found.verdict, ct.NO_PARENT)
        self.assertIn("not a count of zero", found.why)

    def test_a_census_that_located_nothing_exits_non_zero(self):
        # "Looked at nothing" and "found nothing" print the same way from a
        # clean exit code, so the run that reached nothing says so and does
        # not return clean.
        with scratch_repo() as root:
            (root / "unrelated.txt").write_text("no index here\n")
            commit(root, "unrelated")
            with mock.patch.object(sys, "argv",
                                   ["x", "--census", "--repo", str(root)]):
                with mock.patch("builtins.print") as printed:
                    code = ct.main()
        self.assertNotEqual(code, 0)
        said = " ".join(str(call) for call in printed.call_args_list)
        self.assertIn("no index was found at all", said)

    def test_a_clone_that_cannot_answer_is_exit_2_and_not_a_count_of_zero(self):
        with scratch_repo() as root:
            readme(root, index(["a case"]))
            answer, why = ct.census(repo=str(root.parent))
        # `root.parent` is a directory that is not a repository at all, which
        # is the failure this tool's `None`-not-`[]` discipline is for.
        self.assertIsNone(answer)
        self.assertTrue(why)

    def test_no_git_on_path_is_exit_2_before_anything_is_measured(self):
        with mock.patch.object(ct.shutil, "which", return_value=None), \
                mock.patch.object(sys, "argv", ["x", "--census"]):
            with mock.patch("builtins.print") as printed:
                code = ct.main()
        self.assertEqual(code, 2)
        said = " ".join(str(call) for call in printed.call_args_list)
        self.assertIn("git is not on PATH", said)
        self.assertIn("git fetch --unshallow", said)


class ReportTests(unittest.TestCase):
    """The rendered output, over records built here rather than read from git.

    Two properties, and both are about what a pasted transcript can be made to
    say. One is the word: an edit is an edit, and a report that labelled one a
    repair would be making the judgement this tool exists to leave to the
    write-up. The other is that every class is counted whether or not it found
    anything, because a tally printed only for the classes that hit is a tally
    whose zeros are indistinguishable from a run that did not look.
    """

    def _render(self, records, paths=("ec/tools/testdata/README.md",)):
        out = io.StringIO()
        with redirect_stdout(out):
            ct.report(records, list(paths))
        return out.getvalue()

    def test_the_tool_never_calls_an_edit_a_repair(self):
        said = self._render([record("a" * 40, rows=[
            ct.Cell("row 1", "`fix.csv`", "before", "after")])])
        self.assertNotIn("hand-repair", said)
        self.assertNotIn("hand repair", said)
        # And the distinction is said rather than left implied.
        self.assertIn("an edit is not a repair", said)

    def test_a_commit_subject_is_quoted_even_when_it_says_hand_repair(self):
        # The exemption, and the reason it is narrow. `99c01938`'s own subject
        # is "the two index hand-repairs are measured, and ...", so the word
        # does reach the output -- as git's sentence about itself, on a line
        # headed by the sha. Redacting it would make a report unable to say what
        # a revision was about, which is the only reason the subject is printed.
        # Asserted here so the exemption cannot widen to the tool's own wording
        # without this going red first.
        said = self._render([ct.Revision(
            "ec/tools/testdata/README.md", "root", "a" * 40,
            f"{'a' * 40} -- the two index hand-repairs are measured",
            ct.UNCHANGED, "", [])])
        self.assertIn("hand-repairs", said)
        # Still the tool's wording beside it, and not a verdict.
        self.assertIn("an edit is not a repair", said)
        self.assertIn("unchanged", said)

    def test_every_class_is_counted_even_the_ones_that_found_nothing(self):
        said = self._render([record("a" * 40, verdict=ct.REFUSED,
                                    why="a row was added")])
        for verdict in ct.VERDICTS:
            self.assertIn(verdict, said, f"{verdict} is not in the tally")
        self.assertIn("0 edited", said)

    def test_the_population_and_the_column_each_index_is_read_in_are_printed(self):
        # A count is not readable without knowing which column produced it, and
        # the two populations are the whole reason this tool is not one census.
        said = self._render([], paths=["ec/tools/testdata/README.md",
                                       "ec/tools/testdata/fixture/README.md"])
        self.assertIn("third column", said)
        self.assertIn("first column", said)
        self.assertIn("2 index(es)", said)

    def test_a_refusal_line_carries_its_reason_and_not_only_its_token(self):
        said = self._render([record("a" * 40, verdict=ct.REFUSED,
                                    why="a row was added or removed")])
        self.assertIn("a row was added or removed", said)
        self.assertIn("a subject", said)


class CommittedHistoryTests(unittest.TestCase):
    """This repository's own history, read by the census.

    Skipped rather than failed when the clone cannot answer: a depth-1
    checkout has no pre-repair parent to compare against, and saying so is the
    correct result, not a defect in the suite. **Never how many** -- the count
    the corpus publishes is a number about prose, and a case that hardcoded it
    would fail the day another edit is made, which would say the detector
    broke when only the population grew. What is asserted instead is that the
    named revisions are reached and classified, and that the classes behave.
    """

    def setUp(self):
        paths, why = ct.population()
        if why is not None or not paths:
            self.skipTest('the population does not resolve in this clone; '
                          'this census needs a full clone '
                          '(`git fetch --unshallow`)')
        self.records = []
        for path in paths:
            for rev in ct.revisions(path)[0]:
                found, why = ct.classify(path, rev)
                if found is None:
                    self.skipTest(f'{path}@{rev[:8]} is not measurable here: '
                                  f'{why}')
                self.records.append(found)

    def _of(self, sha, kind="root"):
        """The records for one revision of one population.

        The kind is a parameter rather than a filter applied afterwards,
        because a revision that touches both indexes is in the report **twice**
        and can land in a different class each time -- `1813fe98` is that
        case, `unchanged` for the root and `edited` for the nested one, and a
        lookup that took the first match would answer about the wrong file.
        """
        return [r for r in self.records
                if r.sha.startswith(sha) and r.kind == kind]

    def test_each_named_repair_is_among_the_revisions_the_census_reports(self):
        # #978's two shas, found again by content rather than by the list this
        # suite holds. The property is that the census reaches them, not that
        # it stops there -- the committed answer is in the write-up.
        for sha, label in REPAIRS:
            with self.subTest(repair=label):
                found = self._of(sha)
                self.assertTrue(found, f"{sha} is not in the report")
                self.assertEqual(found[0].verdict, ct.EDITED)
                self.assertTrue(found[0].rows)
                self.assertTrue(found[0].rows[0].first.startswith("`"),
                            f"row token is not a backticked path: "
                            f"{found[0].rows[0].first!r}")

    def test_the_nested_pointer_repair_is_among_them_too(self):
        # The other population, and the one a third-column census cannot see:
        # the repaired cell is a **path** in column 1 of a two-column table.
        found = self._of(NESTED_REPAIR[0], kind="nested")
        self.assertTrue(found, f"{NESTED_REPAIR[0]} is not in the report")
        self.assertEqual(found[0].verdict, ct.EDITED)
        self.assertRegex(found[0].rows[0].first, r"\.(asm|csv)`")
        # The same commit against the other population. One revision is two
        # records, and reading it as one is how a count across the two
        # populations could come out one too high or one too low.
        self.assertEqual([r.verdict for r in
                          self._of(NESTED_REPAIR[0], kind="root")],
                         [ct.UNCHANGED])

    def test_the_population_holds_the_root_index_and_every_nested_one(self):
        paths, _why = ct.population()
        self.assertIn("ec/tools/testdata/README.md", paths)
        nested_paths = [p for p in paths if ct.reader_for(p) == "nested"]
        self.assertTrue(nested_paths,
                        "the committed tree self-indexes call-graph/, so a "
                        "population with no nested index has lost it")
        for path in nested_paths:
            with self.subTest(index=path):
                self.assertTrue(
                    [r for r in self.records if r.path == path],
                    f"no revision of {path} reached the report")

    def test_a_revision_whose_row_count_moved_is_a_refusal_not_an_edit(self):
        # The separation, held against the committed tree rather than against a
        # figure: the corpus's row additions are the population the detector
        # cannot measure, and counting them as edits would be the error this
        # tool's shape exists to avoid.
        refused = [r for r in self.records if r.verdict == ct.REFUSED]
        self.assertTrue(refused, "the committed history grew the table many "
                                 "times, so this cannot be vacuous")
        for record_ in refused:
            self.assertEqual(record_.rows, [])
            self.assertIn("counted on neither side", record_.why)
        edited = [r for r in self.records if r.verdict == ct.EDITED]
        for record_ in edited:
            self.assertNotIn("counted on neither side", record_.why)

    def test_the_report_is_non_empty_and_holds_the_whole_population(self):
        out = io.StringIO()
        with redirect_stdout(out):
            ct.report(self.records, ct.population()[0])
        said = out.getvalue()
        self.assertIn("index(es) ever added", said)
        self.assertIn("an edit is not a repair", said)
        for sha, _label in REPAIRS:
            self.assertIn(sha, said)

    def test_no_committed_revision_falls_in_the_unreadable_class(self):
        # Both committed indexes are readable by the reader their path selects.
        # If this ever went non-zero it would be a real finding -- a file whose
        # shape its own population had stopped matching -- and not a reason to
        # relax the guard.
        self.assertEqual([r for r in self.records if r.verdict == ct.UNREADABLE],
                         [])


if __name__ == "__main__":
    unittest.main()
