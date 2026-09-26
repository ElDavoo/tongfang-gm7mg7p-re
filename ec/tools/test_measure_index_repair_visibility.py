#!/usr/bin/env python3
"""Tests for `measure_index_repair_visibility.py`.

The tool's output is a number the corpus's next ten sentences are about, so
what is worth pinning is not the number -- the repository's standing rule is
that an expected count turns every added fixture into a failure -- but the
three things that could make the number wrong quietly:

  * **the detector comparing nothing.** `repair_rows()` over two images that
    differ and over two that do not, and over a pair whose row counts do not
    match, which is refused rather than aligned;
  * **a red pre-repair run meaning nothing without a green post-repair one.**
    The scratch-repository cases are the shape of the committed answer, and
    they are built to be red before a repair and green after one;
  * **the confound being absorbed.** A row whose fixture does not exist at the
    measured revision fails every claim it has for a reason that has nothing to
    do with the claim, and the tool has to say "not runnable" rather than count
    it. This is the case that would fail if a future edit folded an unrunnable
    row into the `missing` total.

The cases that need a repository build one, in a `tempfile` scratch tree, on
the `tools/test_agent_gates_patches.py` precedent: `git init` into a throwaway
tree, `shutil.which('git')` to skip, and nothing here writes to the working
tree. The last case reads the two real repairs out of the committed history
and **skips** when this clone cannot resolve them, so the suite stays green in
a shallow checkout the way `test_agent_gates_patches.py` does -- and not the
way `test_walk_budget_census.py` does, which asserts and fails, and which is
right for a count of a *committed* tree and wrong here.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import measure_index_repair_visibility as mrv  # noqa: E402

# The two hand-repairs the corpus's disclaimer is about, named here rather than
# discovered, because a case that discovers its own subject cannot tell a
# detector that stopped working from a detector with nothing to find. The tool
# itself finds the repaired rows by content; this only says *which* pair of
# revisions the committed answer is about.
REPAIRS = (
    ("#502", "565b6f3c"),
    ("#720", "8f4f211f"),
)

# Addresses for the scratch trees. `0x0751` is the door byte the committed
# index's mark labels carry, and `0x0A5B` is nothing in particular; both are
# outside `check_testdata_row_claims.py`'s firmware-code census, so neither is
# passed over as a code address and both reach the file set as claims. A
# literal in the census would make every case below vacuously green.
CLAIMED, HELD = "0x0A5B", "0x0751"

# A `File`/`Feeds`/`Description` table with the header `check_testdata_index.py`
# locates it by, and a `Feeds` cell naming a tool that lives beside `testdata/`
# -- which is what makes the extraction's `PATHS` a decision this suite pins.
HEADER = ("| File | Feeds | Description |\n"
          "|---|---|---|\n")


def index(rows, fixture='fix.csv'):
    """An index image over `rows`, each a description cell.

    `fixture` is the first-column token, and it is a parameter rather than
    fixed because the unrunnable case is a row that names a file the measured
    revision does not have -- a name the helper cannot invent by accident.
    """
    return ("# scratch\n\n" + HEADER +
            "".join(f"| `{fixture}` | `../grade_thing.py` | {cell} |\n"
                    for cell in rows) +
            "\nA paragraph below the table, which no row reader reads.\n")


def git(*args, cwd):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                          text=True)


def has_git():
    return shutil.which("git") is not None


@contextmanager
def scratch_repo():
    """A throwaway repository holding an index, a fixture and a tool.

    Two commits are the shape this tool measures between, and both are made
    here rather than imported: the tool's own subject is a repository's
    history, and a suite that reached into this one for it would be skipped
    in a shallow checkout along with the case that can catch a regression.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "ec" / "tools" / "testdata").mkdir(parents=True)
        (root / "ec" / "tools" / "grade_thing.py").write_text("# tool\n")
        (root / "ec" / "tools" / "testdata" / "fix.csv").write_text(
            f"# ts,addr,old,new\n2026-01-01T00:00:00.000,{HELD},0x00,0x01\n")
        git("init", "-q", ".", cwd=root)
        # Repo-local, not global: a suite that wrote a global identity to make
        # its own commits would edit the machine it runs on, and CI runners and
        # a developer's laptop should come out of it the same.
        git("config", "user.email", "measure@example.invalid", cwd=root)
        git("config", "user.name", "measure index repair visibility", cwd=root)
        yield root


def commit(root, message):
    git("add", "-A", cwd=root)
    done = git("commit", "-q", "-m", message, cwd=root)
    if done.returncode != 0:
        raise AssertionError(f"scratch commit failed: {done.stderr}")
    return git("rev-parse", "HEAD", cwd=root).stdout.strip()


class RepairRowTests(unittest.TestCase):
    """`repair_rows()` on inline text, with no git in it at all.

    A detector that found nothing would agree with a detector that found no
    repair, on any pair of images that differ only where the tool cannot look.
    """

    def test_a_changed_description_cell_is_reported_with_its_row(self):
        before = index(["the mark label `0x0751`", "unchanged"])
        after = index(["the mark label `0x0751`", "reworded"])
        rows, why = mrv.repair_rows(before, after)
        self.assertIsNone(why)
        self.assertEqual(rows, [2])

    def test_row_numbers_are_the_checkers_own(self):
        # A report line has to be readable against
        # `check_testdata_row_claims.py`'s own output, and that tool counts
        # table rows from 1, so this is the mapping the two agree on.
        before = index([f"row {n}" for n in range(1, 6)])
        after = index([f"row {n}" for n in range(1, 5)] + ["row 5, edited"])
        rows, _why = mrv.repair_rows(before, after)
        self.assertEqual(rows, [5])
        self.assertEqual(len(mrv.table_cells(after, column=3)), 5)

    def test_a_first_column_edit_is_not_a_repair(self):
        before = ("| File | Feeds | Description |\n|---|---|---|\n"
                  "| `fix.csv` | `../grade_thing.py` | the same cell |\n")
        after = before.replace("`fix.csv`", "`other.csv`")
        rows, why = mrv.repair_rows(before, after)
        self.assertIsNone(why)
        self.assertEqual(rows, [])

    def test_a_feeds_only_edit_is_not_a_repair(self):
        before = index(["the same cell"])
        after = before.replace("`../grade_thing.py`", "`../grade_other.py`")
        rows, _why = mrv.repair_rows(before, after)
        self.assertEqual(rows, [])

    def test_a_reworded_sentence_is_a_repair_even_with_the_literals_kept(self):
        # The detector is about the cell, not about the literals, and this is
        # the case that says so: an expected count keyed on literals would
        # report nothing here and the report would read as "no repair".
        before = index(["the mark label `0x0751` in every capture"])
        after = index(["the mark label `0x0751`, in every one of them"])
        rows, _why = mrv.repair_rows(before, after)
        self.assertEqual(rows, [1])

    def test_images_with_different_row_counts_are_refused_not_aligned(self):
        # Row numbers are positions. Zipping a 2-row image against a 3-row one
        # would call rows 1 and 2 "changed" and say nothing about row 3, which
        # does not exist on one side.
        rows, why = mrv.repair_rows(index(["a", "b"]), index(["a", "b", "c"]))
        self.assertEqual(rows, [])
        self.assertIsNotNone(why)
        self.assertIn("not found by this method", why)

    def test_text_with_no_table_reports_nothing_rather_than_raising(self):
        rows, why = mrv.repair_rows("prose only\n", "prose only\n")
        self.assertEqual(rows, [])
        self.assertIsNone(why)


class GitFailureTests(unittest.TestCase):
    """`git_lines()` and `resolve_revision()` when git does not answer.

    Every measurement this tool makes is "git said nothing", so a git that
    failed has to be distinguishable from a tree with nothing in it. A run
    that cannot tell them apart reports a count of zero over a revision it
    never read.
    """

    def setUp(self):
        if not has_git():
            self.skipTest('no git on PATH')

    def test_a_bad_revision_is_none_with_a_reason_not_an_empty_list(self):
        with scratch_repo() as root:
            git("commit", "-q", "--allow-empty", "-m", "one", cwd=root)
            sha, why = mrv.resolve_revision("no-such-revision", repo=str(root))
        self.assertIsNone(sha)
        self.assertTrue(why)
        self.assertIn("no-such-revision", why)

    def test_a_good_revision_resolves_to_a_sha(self):
        with scratch_repo() as root:
            sha = commit(root, "one")
            found, why = mrv.resolve_revision(sha, repo=str(root))
        self.assertIsNone(why)
        self.assertEqual(found, sha)

    def test_a_missing_git_is_a_reason_and_not_a_crash(self):
        # `subprocess.run` raises rather than returning nonzero when the
        # executable is not there, and the OSError arm is the one a checkout
        # without git on PATH would take.
        with mock.patch.dict(os.environ, {"PATH": ""}):
            lines, why = mrv.git_lines("rev-parse", "HEAD", repo=HERE)
        self.assertIsNone(lines)
        self.assertIn("git could not be run", why)

    def test_the_tool_reports_not_measurable_rather_than_a_count_of_zero(self):
        with scratch_repo() as root:
            sha = commit(root, "one")
            lines, code = mrv.repair("no-such-revision", sha, repo=str(root))
        self.assertEqual(code, 2)
        self.assertIn("not measurable in this clone", "\n".join(lines))
        # The number that would have been a count of zero if the failure had
        # been read as an empty tree.
        self.assertNotIn("\n0 ", "\n".join(lines))

    def test_no_git_on_path_is_exit_2_before_anything_is_measured(self):
        with mock.patch.object(mrv.shutil, "which", return_value=None), \
                mock.patch.object(sys, "argv",
                                  ["x", "--base", "a", "--repair", "b"]):
            with mock.patch("builtins.print") as printed:
                code = mrv.main()
        self.assertEqual(code, 2)
        said = " ".join(str(call) for call in printed.call_args_list)
        self.assertIn("git is not on PATH", said)


@unittest.skipUnless(has_git(), 'no git on PATH')
class ScratchMeasurementTests(unittest.TestCase):
    """The measurement over a repository this suite builds.

    The shape of the committed answer, at a size where the answer is not in
    doubt: red before a repair, green after one. A harness that could not
    return red would make the committed number unfalsifiable.
    """

    def setUp(self):
        if not has_git():
            self.skipTest('no git on PATH')

    def _measure(self, before_cell, after_cell, before_fixture='fix.csv',
                 added_at_repair=None):
        """Build two commits and measure between them.

        `before_fixture` is the name the row's first column carries at the
        pre-repair commit, and `added_at_repair` is a file the repair adds.
        Pointing the row at a name the pre-repair commit does not have on disk
        is the vacuous case, so the two are separate parameters: naming an
        absent fixture and then adding it is one story, and a helper that did
        both at once would not be able to tell it from the red one.
        """
        with scratch_repo() as root:
            data = root / "ec" / "tools" / "testdata"
            (data / "README.md").write_text(index([before_cell],
                                                  before_fixture))
            base = commit(root, "before")
            (data / "README.md").write_text(index([after_cell],
                                                  before_fixture))
            if added_at_repair:
                (data / added_at_repair).write_text(f"# {HELD}\n")
            target = commit(root, "repair")
            return mrv.repair(base, target, repo=str(root))

    def test_a_row_claiming_an_address_its_fixture_lacks_is_red_before(self):
        lines, code = self._measure(f"the mark label `{CLAIMED}`",
                                    f"the mark label `{HELD}`")
        said = "\n".join(lines)
        self.assertEqual(code, 0, said)
        self.assertIn("backticked address literals in the description: 1 before,"
                      " 1 after", said)
        self.assertIn("runnable at that revision: first column resolved to "
                      "1 file(s)", said)
        self.assertIn("pre-repair: 1 missing claim(s) in this row", said)
        self.assertIn(CLAIMED, said)
        self.assertIn("post-repair: 0 missing claim(s) in this row", said)

    def test_the_run_is_green_after_the_repair_and_the_tool_still_exits_0(self):
        # The tool's exit code is not the check's verdict: a red pre-repair run
        # is the answer, not a failure of this tool. 1 is reserved for a
        # *post*-repair control that is red, which would make the pre-repair
        # number beside it meaningless.
        _lines, code = self._measure(f"the mark label `{CLAIMED}`",
                                     f"the mark label `{HELD}`")
        self.assertEqual(code, 0)

    def test_a_row_whose_fixture_is_absent_is_reported_unrunnable(self):
        # The confound. The row names a fixture the pre-repair commit does not
        # carry, so every claim in it would be missing for a reason that has
        # nothing to do with the claim, and folding that into the count would
        # read as "the checker caught it". The repair adds the file and fixes
        # the prose, which is exactly the case the issue says must be a stated
        # limit rather than a negative result.
        lines, code = self._measure(f"the mark label `{CLAIMED}`",
                                    f"the mark label `{HELD}`",
                                    before_fixture='late.csv',
                                    added_at_repair='late.csv')
        said = "\n".join(lines)
        self.assertIn("not runnable at that revision, because its first column "
                      "resolved to no file on disk", said)
        # And it is not folded into a count of either shape.
        self.assertNotIn("missing claim(s) in this row", said)
        self.assertEqual(code, 0, said)

    def test_a_red_post_repair_control_fails_the_run(self):
        # The control is the check this tool can fail on. Here the repair
        # leaves the row still missing -- the repair changed the prose and not
        # the fixture -- so the pre-repair number beside it proves nothing.
        with scratch_repo() as root:
            data = root / "ec" / "tools" / "testdata"
            (data / "README.md").write_text(
                index([f"the mark label `{CLAIMED}`"]))
            base = commit(root, "before")
            (data / "README.md").write_text(index([f"also `{CLAIMED}` here"]))
            target = commit(root, "repair")
            lines, code = mrv.repair(base, target, repo=str(root))
        said = "\n".join(lines)
        self.assertEqual(code, 1, said)
        self.assertIn("the post-repair control is red on the repaired row(s)",
                      said)

    def test_a_pair_with_no_third_column_change_reports_not_found(self):
        # The second commit touches a file the detector does not read, so the
        # two description cells are byte-identical and there is no repair to
        # find. That is a different answer from a count of zero over a repair
        # that was found, and the report has to say which.
        with scratch_repo() as root:
            data = root / "ec" / "tools" / "testdata"
            (data / "README.md").write_text(index([f"the label `{HELD}`"]))
            base = commit(root, "before")
            (data / "unrelated.txt").write_text("nothing the index names\n")
            target = commit(root, "unrelated")
            lines, code = mrv.repair(base, target, repo=str(root))
        said = "\n".join(lines)
        self.assertEqual(code, 0, said)
        self.assertIn("not found by this method", said)

    def test_the_feeds_column_resolves_in_the_extracted_tree(self):
        # `PATHS` is `ec/tools` and not `ec/tools/testdata/` because
        # `check_testdata_index.check()` resolves `Feeds` against the *parent*
        # of the testdata root. An extraction that missed the tool would report
        # a `Feeds` miss on every row and bury the one number this tool exists
        # to print, so the control line is asserted rather than assumed.
        with scratch_repo() as root:
            (root / "ec" / "tools" / "testdata" / "README.md").write_text(
                index([f"the label `{HELD}`"]))
            base = commit(root, "before")
            (root / "ec" / "tools" / "testdata" / "README.md").write_text(
                index([f"the label `{HELD}`, reworded"]))
            target = commit(root, "repair")
            lines, code = mrv.repair(base, target, repo=str(root))
        said = "\n".join(lines)
        self.assertEqual(code, 0, said)
        self.assertIn("0 Feeds miss(es)", said)
        self.assertIn("0 gap(s), 0 path miss(es)", said)


@unittest.skipUnless(has_git(), 'no git on PATH')
class CommittedRepairTests(unittest.TestCase):
    """The two real repairs, read out of this repository's own history.

    Skipped rather than failed when a revision does not resolve: a shallow
    checkout cannot answer this and saying so is the correct result, not a
    defect in the suite. What is asserted is that the report is non-empty and
    that the detector found a row -- never how many, because the count the
    corpus publishes is a number about prose, and hardcoding it here would fail
    the day a third repair is made.
    """

    def setUp(self):
        for label, rev in REPAIRS:
            if not mrv.resolve_revision(rev)[0]:
                self.skipTest(f'{label} ({rev}) is not in this clone; '
                              'this mode needs a full clone '
                              '(`git fetch --unshallow`)')
        if not mrv.resolve_revision(f"{REPAIRS[0][1]}^")[0]:
            self.skipTest('a pre-repair parent does not resolve in this clone')

    def test_each_repair_is_measured_over_its_own_first_parent(self):
        for label, rev in REPAIRS:
            with self.subTest(repair=label):
                base, _why = mrv.parent(rev)
                lines, code = mrv.repair(base, rev)
                said = "\n".join(lines)
                self.assertIn(rev, said)
                self.assertIn("rows whose description cell differs: ", said)
                self.assertIn("control, pre-repair: ", said)
                self.assertIn("control, post-repair: ", said)
                # 0 for a reason, or 1 for a reason: both are measurements, and
                # the third outcome is a row that could not be run at all.
                self.assertNotIn("not measurable in this clone", said)
                self.assertNotIn("not runnable at that revision", said)
                self.assertIn(code, (0, 1), said)

    def test_the_row_claims_checker_was_run_and_said_something(self):
        # "The run reached nothing" and "the run found nothing" look the same
        # from a report that printed a zero, so the report has to carry the
        # denominator the zero is a fraction of.
        for label, rev in REPAIRS:
            with self.subTest(repair=label):
                base, _why = mrv.parent(rev)
                lines, _code = mrv.repair(base, rev)
                said = "\n".join(lines)
                self.assertRegex(
                    said, r"control, pre-repair: \d+ literal\(s\), \d+ resolved")

    def test_the_repaired_rows_are_runnable_at_their_own_revision(self):
        # The stated limit, checked against the real pairs rather than assumed:
        # a row whose fixture the repair had to add would be unrunnable, and
        # the published answer would have to say so instead of counting it.
        for label, rev in REPAIRS:
            with self.subTest(repair=label):
                base, _why = mrv.parent(rev)
                lines, _code = mrv.repair(base, rev)
                self.assertIn("runnable at that revision",
                              "\n".join(lines))


if __name__ == "__main__":
    unittest.main()
