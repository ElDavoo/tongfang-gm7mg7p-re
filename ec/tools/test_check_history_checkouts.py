#!/usr/bin/env python3
"""Offline checks for check_history_checkouts.py: a scratch tree and the real one.

The tool holds two claims about the repository's own workflows, and the tree
satisfies both today, so neither can be shown to have teeth by running it
against `main`: a checker that had quietly stopped finding anything would print
the same clean report. The scratch-tree cases below are therefore the ones that
matter most in this suite -- the synthetic workflow that resolves to the depths
it spells, the gate job that goes red on a shallow checkout, the actionlint job
that does not, and the sentence that names `ci.yml` without naming a job.

**The stale sentences are the control, in the spelling they actually had.** Four
of them went stale the same way, and #1009's own claim -- that a checker
reading the sentence back would catch it -- is worth nothing unless the checker
is shown rejecting the text that was wrong. They are pasted here verbatim from
the pre-#1009 sources rather than paraphrased, because a paraphrase that
accidentally names a job is a control that passes for the wrong reason.

The committed-tree cases at the end are tripwires, not floors: they hold the
derivation against the workflows, so a template re-copy that drops
`fetch-depth: 0` from `ci.yml`'s `gates` job turns this suite red, and one that
adds a workflow does not.
"""
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_history_checkouts', HERE / 'check_history_checkouts.py')
chc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chc)

# The four sentences #1009 corrects, **verbatim from the sources as they were
# before it**, line breaks and quoting included. Verbatim is the point: a
# paraphrase that happened to name a job, or that lost the wrap a claim sits
# across, would be a control passing for the wrong reason -- and the second is
# not hypothetical here, because the depth word and the workflow name live on
# different lines of the real `HISTORY_REQUIREMENT`, and a one-line rendering
# of it is a sentence the rule does not even recognise as a claim.
STALE_DOCSTRING = r'''
    # audit a digest migration against history; needs a full clone,
    # so ci.yml's default-depth checkouts cannot run it
'''

STALE_COMMENT = r'''
# The agent stages check out with `fetch-depth: 0` and can run it;
# both of ci.yml's checkouts are default-depth and cannot resolve the
# revisions §14f names at all. See docs/agent-pipeline.md.
'''

STALE_REQUIREMENT = r'''
HISTORY_REQUIREMENT = (
    "  This mode answers from the repository's history, so it needs a full\n"
    "  clone: `git clone` without --depth, or `git fetch --unshallow` in one\n"
    "  that is shallow. A default-depth checkout -- actions/checkout's default,\n"
    "  which is what ci.yml uses -- has neither revision, and a mode that\n"
    "  carried on anyway would be auditing whatever happened to be checked out.")
'''

# The fourth copy, in the shape it took after #978 reworded it rather than
# carrying it over: `ci.yml` named, both depths asserted, no job in either
# sentence -- which is what made it a near-miss rather than the same defect.
STALE_SIBLING = r'''
HISTORY_REQUIREMENT = (
    "  This tool answers from the repository's history, so it needs a full\n"
    "  clone: `git clone` without --depth, or `git fetch --unshallow` in one\n"
    "  that is shallow. The agent stages and ci.yml both check out with\n"
    "  `fetch-depth: 0` and can resolve these revisions; a default-depth\n"
    "  checkout has neither of them, and this tool would go on to report a\n"
    "  count of zero over a tree it never read.")
'''

# What replaced the first of them, in the same source shape. The other three
# are read from the committed tree rather than copied here, so a correction that
# later goes stale again is caught against the file rather than against this
# suite's memory of it.
CORRECTED_DOCSTRING = r'''
    # audit a digest migration against history; needs a full clone.
    # ci.yml's `gates` job has one (`fetch-depth: 0`) and is the job that
    # runs the gate; its `workflows` job is default-depth and runs no
    # history reader, so it never reaches this mode
'''


def workflow(name, jobs):
    """A workflow file's text, from `{job id: steps}`."""
    lines = ["name: %s" % name, "on: [push]", "jobs:"]
    for job_id, steps in jobs.items():
        lines.append("  %s:" % job_id)
        lines.append("    runs-on: ubuntu-latest")
        lines.append("    steps:")
        for step in steps:
            if "uses" in step:
                lines.append("      - uses: actions/checkout@v4")
                if "depth" in step:
                    lines.append("        with:")
                    lines.append("          fetch-depth: %d" % step["depth"])
            else:
                lines.append("      - name: %s" % step.get("name", "Run"))
                lines.append("        run: %s" % step["run"])
    return "\n".join(lines) + "\n"


class ScratchTree(unittest.TestCase):
    """A throwaway repository root the checker is pointed at with `--repo`."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        os.makedirs(os.path.join(self.root, ".github", "workflows"))
        os.makedirs(os.path.join(self.root, "ec", "tools"))

    def put(self, rel, text):
        """A file at `rel` under the scratch root."""
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def tool(self, rel, text):
        """One of the two prose files, at a path the checker actually reads."""
        return self.put(rel, text)

    def problems(self):
        """(depth problems, prose problems) over the scratch tree."""
        out = io.StringIO()
        with redirect_stdout(out):
            depth, prose = chc.report(self.root)
        return depth, prose, out.getvalue()


class DepthTests(ScratchTree):
    """The measured half: what a checkout resolves to, and what fails on it."""

    def test_a_stated_depth_and_an_absent_one_resolve_differently(self):
        # The distinction the whole issue turns on. A step that states
        # `fetch-depth: 0` and a step that states nothing are not the same
        # checkout, and a reader that answered "unspecified" for the second
        # would be declining the question the tool exists to ask.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0}],
            "workflows": [{"uses": True}],
        }))
        workflows, unreadable = chc.load_workflows(self.root)
        self.assertEqual(unreadable, [])
        depths = {(c.job): c.depth
                  for c in workflows["ci.yml"]["gates"].checkouts
                  + workflows["ci.yml"]["workflows"].checkouts}
        self.assertEqual(depths, {"gates": 0, "workflows": 1})

    def test_a_default_depth_is_reported_as_the_default_and_not_as_stated(self):
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0}],
            "workflows": [{"uses": True}],
        }))
        workflows, _ = chc.load_workflows(self.root)
        by_job = {c.job: (c.depth, c.stated)
                  for c in (workflows["ci.yml"]["gates"].checkouts
                            + workflows["ci.yml"]["workflows"].checkouts)}
        self.assertEqual(by_job["gates"], (0, True))
        self.assertEqual(by_job["workflows"], (1, False))

    def test_a_gate_job_on_a_shallow_checkout_is_a_failure(self):
        # The case the invariant exists for: a re-copy of `ci.yml` that drops
        # the `fetch-depth: 0`, which is what a *workflow* accident looks like
        # from inside the tool rather than a provenance failure.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True},
                      {"run": ".github/scripts/agent-gates.sh"}],
        }))
        depth, _prose, out = self.problems()
        self.assertEqual(len(depth), 1, out)
        self.assertIn("ci.yml/gates", depth[0])
        self.assertIn(".github/scripts/agent-gates.sh", depth[0])
        self.assertIn("depth 1", depth[0])

    def test_a_job_running_the_mode_itself_is_a_history_reader(self):
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": "python3 ec/tools/verify_reassembly.py --verify-provenance"}],
        }))
        depth, _prose, _out = self.problems()
        self.assertFalse(depth, "a job running --verify-provenance was not counted")

    def test_a_job_running_only_the_cheap_half_of_the_tool_is_not(self):
        # `verify_reassembly.py --check` never reads history, so counting the
        # tool's name alone would put a job that needs no clone into the rule and
        # make the rule wrong rather than merely strict.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True},
                      {"run": "python3 ec/tools/verify_reassembly.py --check"}],
        }))
        depth, _prose, _out = self.problems()
        self.assertFalse(depth, f"--check was counted as a history reader: {depth}")

    def test_a_job_running_the_sibling_measurement_tool_is_a_history_reader(self):
        # The third marker, which matches nothing in the repository's own
        # workflows today: this tool is not in a gate, and the marker is here so
        # that a workflow which does add it is caught rather than discovered.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True},
                      {"run": "python3 ec/tools/measure_index_repair_visibility.py "
                              "--base HEAD~2 --repair HEAD"}],
        }))
        depth, _prose, _out = self.problems()
        self.assertTrue(depth, "the sibling tool was not counted as a history reader")
        self.assertIn("measure_index_repair_visibility.py", depth[0])

    def test_a_shallow_lint_job_is_not_a_failure(self):
        # `ci.yml`'s `workflows` job is default-depth on the committed tree and
        # always was. The check has to leave it alone, or it fires on the tree
        # it is meant to describe.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": ".github/scripts/agent-gates.sh"}],
            "workflows": [{"uses": True},
                          {"run": "/tmp/actionlint -color"}],
        }))
        depth, _prose, out = self.problems()
        self.assertFalse(depth, f"a lint job on a default-depth checkout failed:\n{out}")
        self.assertIn("ci.yml / workflows / Checkout: depth 1", out)

    def test_a_history_job_with_no_checkout_is_reported_as_not_found(self):
        # "not found by this method" and not a depth of 1: a checkout this
        # method cannot see is a different answer from a shallow one, and
        # reporting it as the latter would be the claim the tool is against.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"run": ".github/scripts/agent-gates.sh"}],
        }))
        depth, _prose, _out = self.problems()
        self.assertTrue(depth)
        self.assertIn("not found by this method", depth[0])
        self.assertIn("no `actions/checkout` step", depth[0])

    def test_a_fetch_depth_that_is_not_an_integer_is_not_guessed(self):
        self.put(".github/workflows/ci.yml",
                 "name: CI\njobs:\n  gates:\n    steps:\n"
                 "      - uses: actions/checkout@v4\n        with:\n"
                 "          fetch-depth: ${{ inputs.depth }}\n"
                 "      - run: .github/scripts/agent-gates.sh\n")
        depth, _prose, _out = self.problems()
        self.assertTrue(depth)
        self.assertIn("not found by this method", depth[0])

    def test_a_workflow_that_will_not_parse_is_named_and_the_rest_still_runs(self):
        self.put(".github/workflows/broken.yml", "jobs:\n  - this is not a map\n")
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0}],
        }))
        workflows, unreadable = chc.load_workflows(self.root)
        self.assertIn("ci.yml", workflows)
        self.assertEqual(len(unreadable), 1)
        self.assertIn("broken.yml", unreadable[0])


class ProseTests(ScratchTree):
    """The reported half: a depth claim has to name the job it is about."""

    def workflow(self):
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": ".github/scripts/agent-gates.sh"}],
            "workflows": [{"uses": True}],
        }))

    def test_a_sentence_naming_a_workflow_and_no_job_is_flagged(self):
        self.workflow()
        self.tool("ec/tools/verify_reassembly.py", STALE_DOCSTRING)
        depth, prose, out = self.problems()
        self.assertFalse(depth, out)
        self.assertEqual(len(prose), 1)
        # The line is the one the depth word is on, not the one the sentence
        # starts on: the two differ by the whole usage block above it, and a
        # citation to `Usage:` is a citation to the wrong line.
        self.assertIn("ec/tools/verify_reassembly.py:2", prose[0])
        self.assertIn("no job", prose[0])

    def test_each_stale_site_in_the_first_tool_is_flagged_on_its_own(self):
        # Three sites, three sentences, one shape -- so the rule is demonstrated
        # per copy rather than once, and a fix to one of them cannot be read as
        # a fix to the other two.
        self.workflow()
        self.tool("ec/tools/verify_reassembly.py",
                  STALE_DOCSTRING + STALE_COMMENT + STALE_REQUIREMENT)
        _depth, prose, out = self.problems()
        self.assertEqual(len(prose), 3, out)
        self.assertTrue(all("no job" in p for p in prose), prose)
        self.assertEqual(len({p.split(":", 1)[0] for p in prose}), 1)

    def test_the_stale_sentence_in_the_sibling_tool_is_flagged(self):
        # The fourth copy, in the shape it took after being reworded rather than
        # carried over: `ci.yml` named, both depths asserted, no job.
        self.workflow()
        self.tool("ec/tools/measure_index_repair_visibility.py", STALE_SIBLING)
        _depth, prose, out = self.problems()
        self.assertEqual(len(prose), 1, out)
        self.assertIn("measure_index_repair_visibility.py:", prose[0])

    def test_the_corrected_sentence_is_accepted(self):
        self.workflow()
        self.tool("ec/tools/verify_reassembly.py", CORRECTED_DOCSTRING)
        _depth, prose, out = self.problems()
        self.assertFalse(prose, f"a sentence naming the job was flagged:\n{out}")

    def test_a_sentence_naming_a_workflow_with_no_depth_word_is_not_a_claim(self):
        # `docs/agent-pipeline.md` is named beside every one of these claims,
        # and naming a document is not a claim about how deep a checkout is.
        self.workflow()
        self.tool("ec/tools/verify_reassembly.py",
                  "See docs/agent-pipeline.md, and docs/findings.md §14f.\n")
        _depth, prose, _out = self.problems()
        self.assertFalse(prose)

    def test_the_gate_script_is_not_mistaken_for_a_job_named_gates(self):
        # The word-boundary rule, on the pair that would otherwise pass for the
        # wrong reason: a sentence naming `.github/scripts/agent-gates.sh` and
        # `ci.yml` and no job must still be flagged.
        self.workflow()
        self.tool("ec/tools/verify_reassembly.py",
                  "# ci.yml is checked out by the agent-gates.sh step, and a "
                  "shallow one cannot run it\n")
        _depth, prose, _out = self.problems()
        self.assertEqual(len(prose), 1, prose)
        self.assertIn("no job", prose[0])

    def test_a_claim_about_a_workflow_that_will_not_parse_is_not_judged(self):
        # It cannot be, and saying so beats a pass this method has not earned.
        self.put(".github/workflows/ci.yml", "jobs: [oops\n")
        self.tool("ec/tools/verify_reassembly.py", STALE_DOCSTRING + "\n")
        _depth, prose, out = self.problems()
        self.assertFalse(prose, out)
        self.assertIn("jobs not found by this method", out)

    def test_a_missing_prose_file_is_silence_rather_than_a_crash(self):
        self.workflow()
        _depth, prose, out = self.problems()
        self.assertFalse(prose, out)


class CommittedTreeTests(unittest.TestCase):
    """The committed workflows and the committed prose, as they stand."""

    def test_the_committed_workflows_are_read_and_hold_the_claim(self):
        workflows, unreadable = chc.load_workflows(str(REPO))
        self.assertFalse(unreadable,
                         f"a committed workflow was not read: {unreadable}")
        self.assertFalse(chc.depth_problems(workflows),
                         chc.depth_problems(workflows))

    def test_the_derivation_is_what_the_claim_says_it_is(self):
        # Held by value rather than by count, because a count is satisfied by
        # any nine checkouts and this sentence is about which are which.
        workflows, _unreadable = chc.load_workflows(str(REPO))
        depths = {}
        for name, jobs in workflows.items():
            for job in jobs.values():
                for checkout in job.checkouts:
                    depths.setdefault(name, []).append((checkout.job,
                                                        checkout.depth))
        self.assertEqual(sorted(depths["ci.yml"]), [("gates", 0), ("workflows", 1)])
        self.assertEqual(depths["claude.yml"], [("claude", 1)])
        # The four agent stages, named by the job each stage runs in, because
        # "all of them are 0" is the half of the claim that goes stale and
        # "which four" is the half a reader has to be able to check.
        for name, job in (("agent-implement.yml", "implement"),
                          ("agent-fix.yml", "fix"),
                          ("agent-review.yml", "review"),
                          ("agent-conflicts.yml", "resolve")):
            self.assertEqual(depths[name], [(job, 0)],
                             f"{name}'s stage checkout is not full-depth")

    def test_the_report_names_the_reader_that_put_each_job_on_the_list(self):
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        self.assertIn("every job that runs a history reader has a full-depth "
                      "checkout", text)
        for job in ("gates", "implement", "fix"):
            self.assertIn(job, text)
        self.assertIn(".github/scripts/agent-gates.sh", text)

    def test_the_two_tools_name_the_job_in_every_depth_claim_they_make(self):
        # The control that makes the rest of this suite mean something: on the
        # tree as it stands, the committed prose passes the rule. When a tool's
        # contract paragraph goes stale again, this is what goes red.
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        self.assertGreaterEqual(
            len(sites), 4,
            "fewer than four depth claims in the two tools. Each of the four "
            "sites #1009 corrected carries one, so fewer means a reader has "
            "quietly stopped finding them -- which reads exactly like a tool "
            "that is working.")
        self.assertFalse(chc.prose_problems(sites), chc.prose_problems(sites))

    def test_each_corrected_site_is_still_one_of_the_sites(self):
        # The four sites, named. A reader that found three of them would leave
        # this green, which is why the count above is a floor and this is a list.
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        found = {rel for rel, _line, _sentence, _named, _job in sites}
        self.assertEqual(found, set(chc.PROSE_FILES))

    def test_the_report_prints_every_checkout_it_found(self):
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        for name in ("ci.yml / gates", "ci.yml / workflows",
                     "claude.yml / claude", "agent-plan.yml / plan"):
            self.assertIn(name, text)


if __name__ == '__main__':
    unittest.main()
