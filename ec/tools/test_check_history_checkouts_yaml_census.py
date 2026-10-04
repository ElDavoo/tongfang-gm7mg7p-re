#!/usr/bin/env python3
"""The census reads both workflow spellings: `.yml` and `.yaml`.

Stands in for the half of #1054 the sibling `check_history_checkouts*` suites do
not reach. `test_check_history_checkouts_run.py` holds the run's contract on a
tree spelled `.yml` throughout -- the spelling the committed tree is written in
(`ls .github/workflows/` is the command that says so), and therefore the only
one any case over this tree had exercised. The other side of that is the case
that was missing: `load_workflows()` globbed `*.yml` and nothing else, so a tree
whose only workflow is a `.yaml` was handed to a refusal written for a tree the
tool could not read, and exited 1 on a tree the pipeline runs perfectly well.
Actions reads the two interchangeably, so the refusal's diagnosis pointed at the
tree's files when the fault was the glob.

**Every case here but the bound is red on the tool as it stood.** The
`.yaml`-only tree exited 1 with the broken-census refusal instead of a
measurement, and the same bytes under `.yml` measured cleanly beside it; the
mixed tree exited 0 with a shallow reader in its `.yaml` half reported by
nobody; and the unparseable `.yaml` was never opened at all, so the clause the
sibling suite pins for `.yml` -- an unreadable file beside a conforming one is
not a broken census -- had no `.yaml` to reach. The bound is the exception and
is green on both sides on purpose: it holds under the narrow glob too, and it
is here because a bound nothing exercises is not a bound. It is what a later
reader widening this to everything YAML-ish would break, and it is the
counterpart to the docstring's old worry about a glob that widens too far.

**Subprocess where the claim is about the exit code, `load_workflows()` where it
is about the census**, which is the same split
`test_check_history_checkouts_run.py` takes and for its reason: the return
value is this tool's product, and an in-process call cannot observe a process
status. The bound is about which files the census holds rather than about what
the run did with them, and reads `load_workflows()` because that is where the
answer is.

**The scratch trees, never the committed workflows.** The pipeline's token has
no `workflow` scope, so renaming a committed workflow to `.yaml` is not a thing
this change can demonstrate; it is also the wrong demonstration, since the point
is that a *tree* is read either way and the committed tree is read either way
already. Every case here builds a tree under a temporary root.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
TOOL = HERE / 'check_history_checkouts.py'
sys.path.insert(0, str(HERE))

from test_check_history_checkouts import ScratchTree, workflow  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'check_history_checkouts_yaml', TOOL)
chc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chc)


class YamlCensusTests(ScratchTree):
    """One scratch tree, one run of the tool as a program over it."""

    def run_tool(self, *args):
        """(returncode, stdout, stderr) from one run as a program.

        `sys.executable` rather than `python3` so the run cannot pick up a
        different interpreter from the one this suite is running under, which
        is the sibling suite's reason for the same call.
        """
        proc = subprocess.run([sys.executable, str(TOOL), *args],
                              capture_output=True, text=True)
        return proc.returncode, proc.stdout, proc.stderr

    def scratch_with(self, name, rel):
        """A second scratch root holding `rel`'s text as `.github/workflows/name`.

        For the case that reads one tree against another, since `ScratchTree`
        gives a case one root and these need two runs over the same bytes under
        different names.
        """
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other)
        directory = os.path.join(other, ".github", "workflows")
        os.makedirs(directory)
        with open(REPO / ".github" / "workflows" / rel, encoding="utf-8") as handle:
            text = handle.read()
        with open(os.path.join(directory, name), "w", encoding="utf-8") as out:
            out.write(text)
        return other

    def committed_ci_as_yaml(self):
        """The committed `ci.yml`, byte for byte, as this tree's only workflow.

        A copy rather than a rebuilt one, so the case turns on the suffix and on
        nothing else: this is a tree whose checkouts and history readers are the
        ones the committed tree has, with the one thing changed that the issue
        is about.
        """
        source = REPO / ".github" / "workflows" / "ci.yml"
        with open(source, encoding="utf-8") as handle:
            self.put(".github/workflows/ci.yaml", handle.read())

    def conforming_yaml(self):
        """A `.yaml` whose reader job is at the action's default depth.

        The mixed tree's second half, and the defect the narrow glob could not
        see: the conforming `.yml` beside it puts the census over zero, so
        `main()`'s refusal never fires and the `.yaml` job is measured by nobody.
        """
        self.put(".github/workflows/ci.yaml", workflow("CI", {
            "gates": [{"uses": True},
                      {"run": ".github/scripts/agent-gates.sh"}],
        }))

    def conforming_yml(self):
        """The same shape in `.yml`, at the depth the invariant requires."""
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": ".github/scripts/agent-gates.sh"}],
        }))


class YamlOnlyTreeTests(YamlCensusTests):
    """A tree whose workflows are spelled `.yaml` is measured, not refused."""

    def test_a_yaml_only_tree_exits_zero_and_is_measured(self):
        self.committed_ci_as_yaml()
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 0, f"{out}\n{err}")
        # The refusal's own wording, gone from both streams. Checked on each
        # rather than on one: the verdict says a run that read nothing does
        # not pass, and the report says the same, and a tool that kept the
        # report's half while passing would have printed a census it did not
        # believe.
        self.assertNotIn("no workflow was read", out)
        self.assertNotIn("broken census", err)
        self.assertIn("every job that runs a history reader has a full-depth "
                      "checkout", out)

    def test_the_two_spellings_of_one_workflow_are_measured_identically(self):
        # The claim the issue makes, stated so a widening cannot pass by reading
        # the `.yaml` and reporting something *else* about it. The same bytes
        # under each name, both runs' reports compared after the filename is
        # put back, so the whole report is the assertion rather than a line of
        # it -- a census that read the `.yaml` and reached a different verdict
        # would differ here.
        #
        # **The committed tree's depths are not re-pinned by this.** They are
        # held by `CommittedTreeTests` against the committed workflows, and a
        # case here that wrote `fetch-depth: 0` down would be a second place to
        # move it when `ci.yml` changes.
        as_yaml = self.scratch_with("ci.yaml", "ci.yml")
        as_yml = self.scratch_with("ci.yml", "ci.yml")
        yaml_code, yaml_out, yaml_err = self.run_tool("--repo", as_yaml)
        yml_code, yml_out, yml_err = self.run_tool("--repo", as_yml)
        self.assertEqual((yaml_code, yml_code), (0, 0), f"{yaml_err}\n{yml_err}")
        self.assertEqual(yaml_out.replace("ci.yaml", "ci.yml"), yml_out)
        # Both verdicts, so the comparison above is not two empty reports
        # agreeing with each other. Which jobs and depths they name is the
        # sibling suite's hold; that there is a report at all is this one's.
        self.assertIn("ci.yaml / gates / Checkout", yaml_out)


class MixedSuffixTreeTests(YamlCensusTests):
    """A conforming `.yml` beside a `.yaml` that has to be measured too."""

    def test_the_yaml_halfs_shallow_reader_is_a_failure_the_run_reports(self):
        self.conforming_yml()
        self.conforming_yaml()
        code, out, err = self.run_tool("--repo", self.root)
        # This is the case the issue asked to be pinned as a miss and that the
        # widening pins as a catch: `if not workflows` is all-or-nothing, so
        # before the widening the conforming `.yml` beside it kept the exit at
        # 0 and the `.yaml` reader was invisible to every rule in the file.
        self.assertEqual(code, 1, f"{out}\n{err}")
        fails = [line for line in err.splitlines() if line.startswith("  FAIL ")]
        self.assertEqual(len(fails), 1, err)
        self.assertIn("ci.yaml/gates", fails[0])
        self.assertIn("depth 1", fails[0])
        # The measurement the tree actually produced is on both sides of it, so
        # a report that failed the run without having read the file would be
        # caught by the same case.
        self.assertIn("ci.yaml / gates / Checkout: depth 1", out)
        self.assertIn("ci.yml / gates / Checkout: fetch-depth: 0", out)


class UnreadableYamlTests(YamlCensusTests):
    """The refusal keys on zero workflows read, not on the suffix."""

    def test_one_yaml_that_will_not_parse_is_not_a_broken_census(self):
        # The `.yml` spelling's case is in `BrokenCensusTests` in the sibling
        # suite, and this is the same clause reached through the suffix that
        # used to be invisible: `main()` keys on the mapping being empty, so a
        # tree one bad file short of complete is measured rather than refused,
        # whichever suffix the bad file is spelled in. That the file was opened
        # at all is the part the narrow glob could not show.
        self.conforming_yml()
        self.put(".github/workflows/broken.yaml", "jobs: [oops\n")
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 0, f"{out}\n{err}")
        self.assertIn("broken.yaml: not read", out)
        self.assertIn("ci.yml / gates", out)


class SuffixBoundTests(YamlCensusTests):
    """The widening is two suffixes, and not everything the directory holds."""

    def test_a_file_that_is_neither_spelling_is_not_a_workflow(self):
        # The honest counterpart to the docstring's old worry, and the bound a
        # later reader needs: Actions reads `.yml` and `.yaml`, so both are
        # read, and nothing else is -- a `.txt` or a `.json` sitting in the
        # workflow directory is not a workflow however much it parses. The
        # contents are a workflow's, so a glob widened to everything YAML-ish
        # would measure this one and fail the run over it.
        self.conforming_yml()
        self.put(".github/workflows/notes.txt", workflow("Notes", {
            "gates": [{"uses": True},
                      {"run": ".github/scripts/agent-gates.sh"}],
        }))
        self.put(".github/workflows/config.json", workflow("Config", {
            "gates": [{"uses": True},
                      {"run": ".github/scripts/agent-gates.sh"}],
        }))
        workflows, unreadable = chc.load_workflows(self.root)
        self.assertEqual(sorted(workflows), ["ci.yml"])
        # Neither was read and neither was refused: `unreadable` is for a file
        # this census looked at and could not use, and a file it never looked
        # at is out of scope rather than a failure -- the same distinction
        # `walk_prose_files()` draws between a declined path and a claimed one.
        self.assertEqual(unreadable, [])
        code, out, err = self.run_tool("--repo", self.root)
        self.assertEqual(code, 0, f"{out}\n{err}")
        self.assertNotIn("notes.txt", out)
        self.assertNotIn("config.json", out)


if __name__ == '__main__':
    unittest.main()