#!/usr/bin/env python3
"""The run's contract, as a subprocess: the exit code and the two streams.

`test_check_history_checkouts.py` reads the report. This file reads the
*process*: `main()`'s return value, which is what a consumer reads and what
nothing else in the tree reaches. Deleting `if problems:` from `main()` turns
the stale tree's five problems into a silent exit 0 and leaves all thirty
report-reading cases green (twenty-four when #1009 wrote them, six more added
by #1034 on `main`, none of which reaches `main()` either), which is the same
defect #948 records for
`check_pin_table_rows.py:547` -- the exit code is the product, and a checker
whose only observable behaviour is a report has no product.

**Subprocess, not an in-process call.** The two sibling checkers' suites import
the tool and call its functions; that arrangement cannot observe a process
status, and it cannot observe `--repo`'s default either without patching the
constant under test, which would make the case a statement about the patched
value rather than about `__file__`. So the module is run as a program, over the
same scratch trees the report suite builds, and each case states one fact about
what a caller of this tool can rely on.

**The four stale sentences are imported, not copied.** They are the control for
the whole of #1009's work, and a second copy is a second thing to drift from
the sources the first one was pasted from -- a paraphrase that happened to name
a job would be a control passing for the wrong reason, which is why the report
suite holds them verbatim.
"""
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / 'check_history_checkouts.py'
sys.path.insert(0, str(HERE))

from test_check_history_checkouts import (  # noqa: E402
    CORRECTED_DOCSTRING,
    STALE_COMMENT,
    STALE_DOCSTRING,
    STALE_REQUIREMENT,
    STALE_SIBLING,
    ScratchTree,
    workflow,
)


class RunTests(ScratchTree):
    """One subprocess run of the tool, over a scratch tree this suite builds."""

    def run_tool(self, *args, cwd=None):
        """(returncode, stdout, stderr) from one run of the tool as a program.

        `cwd` is a keyword because one case has to put a *different* tree under
        the process than the one it built, and `sys.executable` rather than
        `python3` so the run cannot pick up a different interpreter from the
        one this suite is running under.
        """
        proc = subprocess.run([sys.executable, str(TOOL), *args],
                              capture_output=True, text=True, cwd=cwd)
        return proc.returncode, proc.stdout, proc.stderr

    def stale_tree(self):
        """The pre-#1009-shaped control: a `gates` job off full depth, and the
        four stale sentences verbatim. Five problems, which is the number
        `docs/findings/history-checkout-claims.md` records."""
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True},
                      {"run": ".github/scripts/agent-gates.sh"}],
            "workflows": [{"uses": True}],
        }))
        self.tool("ec/tools/verify_reassembly.py",
                  STALE_DOCSTRING + STALE_COMMENT + STALE_REQUIREMENT)
        self.tool("ec/tools/measure_index_repair_visibility.py", STALE_SIBLING)

    def conforming_tree(self):
        """The same tree with #1009's correction applied: `gates` back at
        `fetch-depth: 0`, and a sentence that names it."""
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": ".github/scripts/agent-gates.sh"}],
            "workflows": [{"uses": True},
                          {"run": "/tmp/actionlint -color"}],
        }))
        self.tool("ec/tools/verify_reassembly.py", CORRECTED_DOCSTRING)

    def assertNoTraceback(self, stderr):
        """No Python traceback on the error stream.

        Red on the tool as #1009 left it, and here for that reason:
        `load_workflows()` returned a *list* on its two failure paths where
        every caller read a mapping, so a tree whose `.github/workflows/` is
        missing or empty took the run to an `AttributeError` after the report
        had already printed its refusal.
        """
        self.assertNotIn("Traceback", stderr)


class StaleTreeTests(RunTests):
    """Exit 1 with the failures, and exit 0 with neither stream used as noise."""

    def test_a_stale_tree_exits_one_with_the_failures_and_the_summary(self):
        self.stale_tree()
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 1, err)
        # The report goes to stdout and the verdict to stderr, and which stream
        # carries which is the contract: a caller that captures one of them has
        # to be able to say what it read.
        fails = [line for line in err.splitlines() if line.startswith("  FAIL ")]
        self.assertEqual(len(fails), 5, err)
        self.assertTrue(any("ci.yml/gates" in line for line in fails), err)
        self.assertIn("5 problem(s).", err)
        # The report's own prose verdict line, as #1034's landing on `main` left
        # it and #1031's landed on top: that change judged the rule per
        # *workflow* rather than per sentence, and this one counts the sentences
        # the rule was applied to rather than the sentences the walk found, since
        # a quoted one is reported beside these. The stale tree has no
        # quotations, so the number is still 4 and 4 -- every stale sentence
        # names one workflow and no job of it -- and the fix is the wording, not
        # a figure that moved.
        self.assertIn("4 of the claims name no job, in 4 judged sentence(s)", out)
        self.assertIn("ci.yml / gates / Checkout: depth 1", out)

    def test_a_conforming_tree_exits_zero_with_an_empty_stderr(self):
        self.conforming_tree()
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 0, f"{out}\n{err}")
        # Empty rather than merely quiet: the depth verdict and the prose
        # verdict are the run's product, and a 0 that means "read nothing"
        # would read exactly like this one.
        self.assertEqual(err, "")
        self.assertIn("every job that runs a history reader has a full-depth "
                      "checkout", out)
        # #1034's wording of the clean verdict, on `main` before this suite:
        # the rule is judged for every workflow a sentence names, so the line
        # says so rather than the per-sentence "the job it is about".
        self.assertIn("every one of them names the job of every workflow it "
                      "names", out)


class RepoArgumentTests(RunTests):
    """`--repo`, and the tree it reads when it is not given."""

    def test_the_default_repo_is_this_repository_and_not_the_working_directory(self):
        self.stale_tree()
        # Run from the stale tree, so a `--repo` that resolved to the working
        # directory would print *its* `ci.yml / gates / Checkout: depth 1` and
        # exit 1. The default is derived from `__file__` at `:110-111`, and this
        # is the only way to see that as a fact rather than as a constant read
        # back out of the module.
        code, out, err = self.run_tool(cwd=self.root)
        self.assertEqual(code, 0, f"{out}\n{err}")
        self.assertIn("ci.yml / gates / Checkout: fetch-depth: 0", out)


class BrokenCensusTests(RunTests):
    """A tree the run located nothing in is refused, not passed."""

    def test_a_tree_whose_workflow_directory_is_empty_is_refused_and_does_not_crash(self):
        shutil.rmtree(os.path.join(self.root, ".github", "workflows"))
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 1, f"{out}\n{err}")
        # The report's own phrase, in its own vocabulary: "broken census, not an
        # empty one" is `report()`'s `:550-551` and is repeated on stderr so a
        # caller reading only the verdict can still tell which premise stopped.
        self.assertIn("broken census, not an empty one", out)
        self.assertIn("broken census, not an empty one", err)
        self.assertNoTraceback(err)

    def test_a_missing_workflow_directory_is_refused_the_same_way(self):
        shutil.rmtree(os.path.join(self.root, ".github"))
        code, out, err = self.run_tool("--repo", self.root)
        self.assertNotEqual(code, 0, f"a tree with no .github/ passed:\n{out}")
        self.assertIn("not listed (No such file or directory)", out)
        self.assertNoTraceback(err)

    def test_one_workflow_that_will_not_parse_is_not_a_broken_census(self):
        # The other side of the same clause. The refusal keys on *zero*
        # workflows read, not on any unreadable file, so a tree that is one bad
        # file short of complete still gets a real measurement and still exits 0.
        self.conforming_tree()
        self.put(".github/workflows/broken.yml", "jobs: [oops\n")
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 0, f"{out}\n{err}")
        self.assertIn("broken.yml: not read", out)
        self.assertIn("ci.yml / gates", out)


class UsageTests(RunTests):
    """The `argparse` block, which nothing else in either suite reaches."""

    def test_the_usage_block_is_this_tools_own_docstring(self):
        code, out, _err = self.run_tool("--help")
        self.assertEqual(code, 0, out)
        # The docstring's own usage line, with its columns as written: it is
        # there because `description=__doc__`, and it keeps its shape only
        # because the formatter is `RawDescriptionHelpFormatter` -- the default
        # would fold a list of commands into one paragraph.
        self.assertIn("python3 ec/tools/check_history_checkouts.py --repo DIR "
                      "# a scratch tree", out)
        self.assertIn("--repo REPO  repository root to read (default: this one)",
                      out)


if __name__ == '__main__':
    unittest.main()
