#!/usr/bin/env python3
"""Offline checks for check_history_checkouts.py: a scratch tree and the real one.

The tool holds two claims about the repository's own workflows, and the tree
satisfies both today, so neither can be shown to have teeth by running it
against `main`: a checker that had quietly stopped finding anything would print
the same clean report. The scratch-tree cases below are therefore the ones that
matter most in this suite -- the synthetic workflow that resolves to the depths
it spells, the gate job that goes red on a shallow checkout, the actionlint job
that does not, the sentence that names `ci.yml` without naming a job, the one
that names two workflows and a job of only one of them, and the gate reached
from a `prompt:` rather than a `run:` step.

**The two prompt shapes are a matched pair, and the pair is the point.** A
marker alone on an indented line of a prompt is a command and its job's shallow
checkout is a failure; the same marker as the fourth word of a bullet is a
review criterion, its job needs no clone, and it is neither a failure nor a
reader -- it is printed under *named in a `prompt:` but not read as a run*,
with the line the citation resolves to. A rule that only tested whether the
prompt had any text on the line would count the second, and four of the cases
below go red when it is loosened that way.

**The stale sentences are the control, in the spelling they actually had.** Four
of them went stale the same way, and #1009's own claim -- that a checker
reading the sentence back would catch it -- is worth nothing unless the checker
is shown rejecting the text that was wrong. They are pasted here verbatim from
the pre-#1009 sources rather than paraphrased, because a paraphrase that
accidentally names a job is a control that passes for the wrong reason.

The committed-tree cases at the end are tripwires, not floors: they hold the
derivation against the workflows, so a template re-copy that drops
`fetch-depth: 0` from `ci.yml`'s `gates` job turns this suite red, and so do the
two edits the class's last case exists for -- `agent-plan.yml`'s `plan` job
taking a `fetch-depth: 0`, and `claude.yml`'s stated `fetch-depth: 1` going
away. All nine `(job, depth, stated)` triples are compared as one mapping rather
than as nine separate assertions, so a tenth checkout anywhere under
`.github/workflows/` turns it red with them; this paragraph used to say one that
adds a workflow does not, which was a property of the narrower form and is not
one any more. **The corrected prose sites are held by value too, in
`ec/tools/history_checkout_sites.py`** -- each one by its file and a fragment of
its sentence, rather than by the count and the file-set comparison that could
not see a site go missing -- and the six cases in `ProseTests` that reach it
are what show that hold: four of them name a row that goes red, and the other
two show the hold surviving a rewrap and the phrase the two tools share. A
seventh, in `CommittedTreeTests` beside the keyed hold itself, is the
`PROSE_FILES` shrink the file-set comparison could not see: that comparison
green on the committed tree, both of the dropped file's rows named.
"""
import importlib.util
import io
import os
import re
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

# The expected-site table, a plain sibling import for the reason the three tools
# `check_testdata_row_claims.py` imports are: these files are not a package, and
# `HERE` is on the path for this suite's own reasons. It is a *second* module
# object for the tool, which is deliberate -- a case that rebound `chc` instead
# would be testing the rebinding.
import history_checkout_sites as hcs

# The two prose files, from the tool's own list rather than written out here.
# What the controls below demonstrate is a file going unread, so the set of
# files the tool reads is not something this suite should hold a second copy
# of, and a second copy is what a `PROSE_FILES` shrink looks like from in here.
FIRST_TOOL, SECOND_TOOL = chc.PROSE_FILES

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

# The sentence issue #1034 is filed with, **verbatim**, and the one its *Done*
# rests on. It is a module constant for the reason the four above are, and
# sharper here: `claude.yml`'s job is `claude`, so the job id is a substring of
# the filename the sentence is required to carry. A paraphrase that spelled
# either job differently, or that dropped `claude.yml` and left a bare `claude`
# behind, would stop being a control for the thing it is a control for -- the
# way the pre-#1009 paraphrases would have stopped catching the stale rule.
ISSUE_TWO_WORKFLOW = (
    "# ci.yml's `gates` job is full-depth and claude.yml is shallow throughout")

# The nine committed checkouts, as `(job, depth, stated)`, which is what the
# table in `docs/findings/history-checkout-claims.md` and the paragraph that
# corrects the issue's own wording in `docs/findings.md` §86 are both written
# from. Held by value rather than by count, because a count is satisfied by any
# nine checkouts and the sentence is about which are which.
#
# `stated` is the half that separates `fetch-depth: 0` from `depth 1 (the
# action's default)`, and it is not a second copy of `depth`: `claude.yml`'s row
# is the one checkout here that states a depth other than 0, so the same
# integer reads as a decision there and as the action's default on the three rows
# below it. Every case that asserted `stated` before this one ran on a synthetic
# tree, which is what left the sentence "the only checkout that *states* a depth
# other than 0" held by nothing on the committed tree.
EXPECTED_CHECKOUTS = {
    "agent-conflicts.yml": [("resolve", 0, True)],
    "agent-fix.yml": [("fix", 0, True)],
    "agent-followups.yml": [("followups", 1, False)],
    "agent-implement.yml": [("implement", 0, True)],
    "agent-plan.yml": [("plan", 1, False)],
    "agent-review.yml": [("review", 0, True)],
    "ci.yml": [("gates", 0, True), ("workflows", 1, False)],
    "claude.yml": [("claude", 1, True)],
}


def checkout_triples(repo):
    """-> (derived, expected) for the tree at `repo`, both sides sorted.

    Both halves, so the committed case and the control beside it compare the
    same two objects: a control that re-derived the mapping its own second way
    would be watching that copy go red rather than the committed assertion's.
    Sorted on both sides, so which job a workflow's YAML happens to list first
    is not part of what is held -- "which job has which depth" is, and that is
    the claim.
    """
    workflows, _unreadable = chc.load_workflows(repo)
    derived = {}
    for name, jobs in workflows.items():
        for job in jobs.values():
            for checkout in job.checkouts:
                derived.setdefault(name, []).append(
                    (checkout.job, checkout.depth, checkout.stated))
    return ({name: sorted(rows) for name, rows in derived.items()},
            {name: sorted(rows) for name, rows in EXPECTED_CHECKOUTS.items()})


# What the site-identity controls cut on, both spelled rather than counted:
# a control that cut at a line number would be the one thing in this suite that
# broke on a rewrap of the very comment it edits, and the table's fragment-keyed
# identity exists to be immune to that.
COMMENT_HEAD = "# The mode reads two revisions out of the repository's own history"
REQUIREMENT_HEAD = "HISTORY_REQUIREMENT = ("

# Control A's replacement constant: one line, and no depth word anywhere in it,
# so the sentence is not one the tool recognises as a claim at all. The 5 -> 4
# that leaves is the demonstration, and it is the issue's own argument
# executable -- the `len(sites) >= 4` the committed case used to carry is green
# on exactly this tree.
NO_DEPTH_REQUIREMENT = ('HISTORY_REQUIREMENT = "This mode needs the '
                        'repository\'s history."\n')

# Control C's copy of site 2's comment: the committed file's words at different
# line breaks. The *words* are the point, and the case asserts the squashed
# sentence is the committed one rather than assuming it, so a rewrap that
# quietly edited a sentence cannot pass as a demonstration of rewrap-immunity.
REWRAPPED_COMMENT = '''\
# The mode reads two revisions out of the repository's own history, so
# how deep the clone is is part of its contract the way the assembler is
# part of --report's. Every job that runs
# `.github/scripts/agent-gates.sh` -- ci.yml's `gates` and the agent
# stages' `implement`, `fix` and `resolve` -- checks out with
# `fetch-depth: 0` and can run it. ci.yml's other checkout, its
# `workflows` job, is the default-depth one and runs actionlint and
# zizmor only, so it never reaches the mode. The four are re-derived
# from the committed workflows by `check_history_checkouts.py`, and see
# docs/agent-pipeline.md.
'''

# A depth claim no row names, in the same voice as the five that are -- which is
# what makes it a control rather than a sixth claim. It is true of the scratch
# tree the fixture writes (`gates` is `fetch-depth: 0` there), so the case is
# about the table's second direction and not about whether a sentence is right.
NEW_CLAIM = ('# `ci.yml`\'s `gates` job checks out with `fetch-depth: 0`, and a\n'
             '# re-copy of the template that drops it turns the gate red with a\n'
             '# history requirement rather than a workflow failure.\n')

# Control F's copy of the sibling's site 4, **merged into one comment**: the
# committed words of the row that names the comment and the row that names the
# `HISTORY_REQUIREMENT`, in a single sentence. This is the rewrap of control C
# taken one step further, and it is here because it is the move that makes the
# table's fourth direction reachable -- two of one file's rows landing on one
# sentence. Every fragment is verbatim from the committed file rather than
# retyped, so the two rows really do both match and the case is about the
# direction rather than about the words.
MERGED_SIBLING = """\
# ci.yml's `gates` job has been `fetch-depth: 0` since #407 (`cc2ab10d`) while
# its `workflows` job is default-depth, and a default-depth checkout has
# neither of them, and this tool would go on to report a count of zero over a
# tree it never read.
"""

# The phrase both tools' `HISTORY_REQUIREMENT` sentences carry, one in each
# file. It is here to be *not* a fragment, and the case below says why.
SHARED_PHRASE = "which is what ci.yml's `workflows` job uses"

# Where the sibling's site 4 begins, so control F can replace the comment *and*
# the constant with one sentence. Spelled rather than derived from the tree so
# the case does not depend on a comment that has since been reworded, in the
# same way `COMMENT_HEAD` and `REQUIREMENT_HEAD` are spelled for control C.
SIBLING_HEAD = "# The mode answers from the repository's own history"


def committed(rel):
    """A committed file's text, read rather than pasted.

    The controls below rewrap and truncate real prose, so a copy pasted here
    would be a copy of this suite's memory of the file rather than of the file
    -- the same reason the corrected sentences are read out of the tree rather
    than carried above.
    """
    with open(REPO / rel, encoding="utf-8") as handle:
        return handle.read()


def carrying(row, sites):
    """-> the sites `row` matches. One per site on the committed tree."""
    return [site for site in sites
            if site[0] == row.rel and row.fragment in hcs.squash(site[2])]


def with_requirement(text, replacement):
    """`text` with everything from `HISTORY_REQUIREMENT = (` onwards replaced."""
    head, sep, _tail = text.partition(REQUIREMENT_HEAD)
    if not sep:
        raise AssertionError(f"{REQUIREMENT_HEAD!r} is not in the committed text")
    return head + replacement


def rewrapped(text):
    """`text` with site 2's comment replaced by `REWRAPPED_COMMENT`.

    The span cut is from the comment's first line to the line before the
    constant, so the comment is replaced whole rather than appended to itself --
    a splice that left the original in place would report the same sentence
    twice and redden the table on the more-than-one-match rule, which is a bug
    in the control rather than a demonstration of anything.
    """
    return (text[:text.index(COMMENT_HEAD)] + REWRAPPED_COMMENT
            + text[text.index(REQUIREMENT_HEAD):])


def workflow(name, jobs):
    """A workflow file's text, from `{job id: steps}`.

    A step is a checkout with `"uses"`, a `with: prompt:` with `"prompt"`, and
    a `run:` otherwise. The prompt is emitted as a literal block indented the
    way the repository's own workflows indent one, so a case's line numbers are
    the ones a reader of the scratch file would count.
    """
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
            elif "prompt" in step:
                lines.append("      - uses: anthropics/claude-code-action@v1")
                lines.append("        with:")
                lines.append("          prompt: |")
                for line in step["prompt"].splitlines():
                    lines.append("            " + line)
            else:
                lines.append("      - name: %s" % step.get("name", "Run"))
                lines.append("        run: %s" % step["run"])
    return "\n".join(lines) + "\n"


def at_line(path, line):
    """The text of one 1-based line of a workflow, for checking a citation."""
    with open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()[line - 1]


def cited_line(text, workflow):
    """The workflow line the report's one `file:line` citation points at.

    Read out of the report rather than written into the case, so a case pins
    the property that matters -- the citation resolves to the line carrying
    the marker -- and not this helper's own line numbering, which a change to
    the scratch-workflow layout above would move for no reason.
    """
    return int(re.search(r"%s:(\d+)" % re.escape(workflow), text).group(1))


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

    def sites(self):
        """(sites, depth problems, prose problems, report) over the scratch tree.

        The list and the two verdicts come from one run, so a case that wants
        what the report found and a case that wants the verdicts cannot be
        looking at two different reads of the tree.
        """
        out = io.StringIO()
        with redirect_stdout(out):
            workflows, unreadable = chc.load_workflows(self.root)
            depth, prose = chc.report(self.root)
            found = chc.prose_sites(self.root, workflows, unreadable)
        return found, depth, prose, out.getvalue()

    def problems(self):
        """(depth problems, prose problems, report) over the scratch tree."""
        _found, depth, prose, out = self.sites()
        return depth, prose, out


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

    def test_a_gate_in_a_prompt_on_a_shallow_checkout_is_a_failure(self):
        # The case `agent-conflicts.yml`'s `resolve` is, and the one the
        # widening exists for. A re-copy of that workflow that dropped
        # `fetch-depth: 0` would break no job and turn no gate red, and before
        # the widening this checker stayed green through it because the gate
        # was reached from a prompt and only a `run:` was read.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "resolve": [{"uses": True},
                        {"prompt": "Resolve it, then run:\n\n"
                                   ".github/scripts/agent-gates.sh"}],
        }))
        depth, _prose, out = self.problems()
        self.assertEqual(len(depth), 1, out)
        self.assertIn("ci.yml/resolve", depth[0])
        self.assertIn(".github/scripts/agent-gates.sh", depth[0])
        self.assertIn("depth 1", depth[0])

    def test_a_gate_in_a_prompt_on_a_full_depth_checkout_is_not_a_failure(self):
        # The committed shape, so the widening cannot make a correct tree go
        # red -- and the job has to be *on* the list, not merely tolerated,
        # because a job quietly excluded and a job correctly included read the
        # same from the exit code.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "resolve": [{"uses": True, "depth": 0},
                        {"prompt": "Resolve it, then run:\n\n"
                                   ".github/scripts/agent-gates.sh"}],
        }))
        depth, _prose, out = self.problems()
        self.assertFalse(depth, f"a full-depth prompt-reached job failed:\n{out}")
        self.assertIn("resolve (.github/scripts/agent-gates.sh, from its prompt)",
                      out)

    def test_a_gate_named_inline_in_a_criterion_is_not_a_reader(self):
        # `agent-review.yml:169`'s shape: the marker is the fourth word of a
        # bullet, so the line's first non-whitespace text is a hyphen. Counting
        # it would put a job that runs no gate and needs no clone inside a
        # full-depth invariant, which is the rule being wrong rather than
        # strict -- so it is reported, not counted and not dropped.
        path = self.put(".github/workflows/ci.yml", workflow("CI", {
            "review": [{"uses": True, "depth": 0},
                       {"prompt": "Reject a PR that:\n"
                                  "- a gate weakened rather than satisfied -- "
                                  "`.github/scripts/agent-gates.sh` relaxed"}],
        }))
        depth, _prose, out = self.problems()
        self.assertFalse(depth, f"a criterion counted as a reader:\n{out}")
        self.assertIn("no job's `run:` or `prompt:` names a history reader", out)
        self.assertIn("not in command position", out)
        cited = cited_line(out, "ci.yml")
        self.assertIn("review: .github/scripts/agent-gates.sh", out)
        self.assertIn("`.github/scripts/agent-gates.sh`", at_line(path, cited))

    def test_a_run_step_outranks_a_prompt_that_reaches_the_same_gate(self):
        # `agent-fix.yml`'s `fix` reaches the gate both ways, at its `:220` and
        # its `:316`, and the step is the route a checkout depth can be held
        # against -- a `run:` is executed and a prompt is read. The report has
        # to say which one put the job on the list, or a reader comparing it
        # against the workflow has to work out which of the two mattered.
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "fix": [{"uses": True, "depth": 0},
                    {"prompt": "Then run:\n\n.github/scripts/agent-gates.sh"},
                    {"run": "bash .github/scripts/agent-gates.sh"}],
        }))
        depth, _prose, out = self.problems()
        self.assertFalse(depth, out)
        self.assertIn("fix (.github/scripts/agent-gates.sh, from a run: step)", out)

    def test_a_prompt_that_is_not_a_string_is_not_read_and_not_a_crash(self):
        # The same answer a non-string `run:` gets, and the same answer a
        # non-integer `fetch-depth` gets: this method has not read it. A
        # prompt arriving as a list or a `${{ }}` handed in from elsewhere is
        # not a sentence to be scanned, and stringifying one would manufacture
        # a line of "prose" out of a value that has none.
        self.put(".github/workflows/ci.yml",
                 "name: CI\njobs:\n  gates:\n    steps:\n"
                 "      - uses: actions/checkout@v4\n        with:\n"
                 "          fetch-depth: 0\n"
                 "      - uses: anthropics/claude-code-action@v1\n"
                 "        with:\n"
                 "          prompt: ${{ inputs.prompt }}\n")
        depth, _prose, out = self.problems()
        self.assertFalse(depth, out)
        self.assertIn("no job's `run:` or `prompt:` names a history reader", out)
        self.assertIn("not found by this method", out)

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
    """The reported half: a depth claim names the job of every workflow it names.

    **Per workflow and not per sentence**, and that is the half of the rule the
    last six cases are about. A sentence naming two workflows is judged once for
    each of them, so the cases come in pairs with the job named on either side,
    against a control that names a job of both -- without which a checker that
    flagged every multi-workflow sentence would pass the pair.
    """

    def workflow(self):
        self.put(".github/workflows/ci.yml", workflow("CI", {
            "gates": [{"uses": True, "depth": 0},
                      {"run": ".github/scripts/agent-gates.sh"}],
            "workflows": [{"uses": True}],
        }))

    def claude(self, job_id="claude"):
        """A second readable workflow, default-depth like the committed one.

        The job id is a parameter because two of the cases below need one that
        is *not* `claude`, and a builder that spelled its own would make them
        read as though `claude.yml` could only ever hold that job.
        """
        self.put(".github/workflows/claude.yml", workflow("Claude", {
            job_id: [{"uses": True}],
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

    def test_a_job_of_the_first_workflow_does_not_satisfy_the_second(self):
        # The issue's sentence, verbatim, and the case its *Done* rests on: a
        # job of `ci.yml` says nothing about `claude.yml`, which the same
        # sentence asserts a depth of and names no job of. Judged on the first
        # readable name alone this returned nothing at all.
        self.workflow()
        self.claude()
        self.tool("ec/tools/verify_reassembly.py", ISSUE_TWO_WORKFLOW + "\n")
        depth, prose, out = self.problems()
        self.assertFalse(depth, out)
        self.assertEqual(len(prose), 1, out)
        # The message names the workflow that has no job, and not the one that
        # has -- read off the head, because the sentence itself is quoted in the
        # tail and carries both names.
        head = prose[0].split(" -- ", 1)[0]
        self.assertIn("names claude.yml and no job of it", head)
        self.assertNotIn("ci.yml", head)

    def test_a_job_of_the_second_workflow_does_not_satisfy_the_first(self):
        # The other direction, and the one the old code got *right* for the
        # wrong reason -- it reported this, naming both workflows in a message
        # about one. So this case pins the message as much as the verdict: the
        # answer must not depend on which name sorts first.
        self.workflow()
        self.claude()
        self.tool("ec/tools/verify_reassembly.py",
                  "# claude.yml's claude job is full-depth and ci.yml is shallow "
                  "throughout\n")
        depth, prose, out = self.problems()
        self.assertFalse(depth, out)
        self.assertEqual(len(prose), 1, out)
        head = prose[0].split(" -- ", 1)[0]
        self.assertIn("names ci.yml and no job of it", head)
        self.assertNotIn("claude.yml", head)

    def test_a_sentence_naming_a_job_of_each_workflow_is_not_flagged(self):
        # The positive control, and the reason it cannot be left out: a checker
        # that flagged every sentence naming two workflows would pass both cases
        # above, so without this the suite could not tell "two workflows" from
        # "two workflows and one job each".
        self.workflow()
        self.claude()
        self.tool("ec/tools/verify_reassembly.py",
                  "# ci.yml's gates job is full-depth and claude.yml's claude "
                  "job is shallow\n")
        _depth, prose, out = self.problems()
        self.assertFalse(prose, f"a sentence naming a job of each was flagged:\n{out}")

    def test_an_unreadable_workflow_beside_a_readable_one_rescues_nothing(self):
        # The third ask: a workflow this tool could not read is not judged, and
        # that must not become an excuse for the one it could. `broken.yml` is
        # still reported as not found by this method, so the pass is not a
        # second one -- the sentence is flagged for `ci.yml` and only `ci.yml`.
        self.workflow()
        self.put(".github/workflows/broken.yml", "jobs: [oops\n")
        self.tool("ec/tools/verify_reassembly.py",
                  "# ci.yml and broken.yml both check out shallow\n")
        _depth, prose, out = self.problems()
        self.assertEqual(len(prose), 1, out)
        self.assertIn("names ci.yml and no job of it", prose[0].split(" -- ", 1)[0])
        self.assertIn("broken.yml: jobs not found by this method", out)

    def test_a_job_id_two_workflows_share_satisfies_the_rule_for_both(self):
        # The floor and not a proof, at its bluntest: one word, both workflows,
        # and no way to tell which the sentence meant. The rule passes both
        # rather than guessing, which is the honest answer and a real blind spot
        # -- `gates` is not a rare job id and `ci.yml` really has one.
        self.workflow()
        self.claude("gates")
        self.tool("ec/tools/verify_reassembly.py",
                  "# ci.yml and claude.yml are shallow except for gates, which is "
                  "full-depth\n")
        _depth, prose, out = self.problems()
        self.assertFalse(prose, f"a shared job id did not satisfy both:\n{out}")

    def test_a_workflow_name_is_not_read_as_a_mention_of_its_own_stem_job(self):
        # The other half of the pair above, and the reason `job_text()` blanks
        # the names rather than the rule tightening its boundary: `claude.yml`'s
        # job is `claude`, so a matcher reading the raw sentence found that job
        # inside the filename the sentence had to carry anyway, and the issue's
        # sentence passed on its own name. Blanking the name's span has to leave
        # a real mention of the job alone, which is the half that could
        # over-reach into flagging correct sentences.
        self.claude()
        self.tool("ec/tools/verify_reassembly.py",
                  "# claude.yml is shallow, and the claude job is the one that "
                  "fetches\n")
        _depth, prose, out = self.problems()
        self.assertFalse(prose, f"a real mention of the job was missed:\n{out}")

    # The site-identity cases below all reach `hcs.problems()` through
    # `self.sites()`, which is the same call the committed-tree case makes, and
    # each names the row it expects to be red rather than asserting that some
    # list is non-empty -- the same argument this module's docstring makes about
    # the `STALE_*` paraphrases, and the reason a control that passed for the
    # wrong reason would be worth nothing.

    def test_a_corrected_site_that_stops_being_reported_is_a_failure(self):
        # Control A, the 5 -> 4. `HISTORY_REQUIREMENT` replaced by a one-line
        # version carrying no depth word, so the report finds the other four
        # sentences and not this one. The count is pinned at four because four
        # is what satisfies the `len(sites) >= 4` the committed case used to
        # carry, so the old floor is green here by arithmetic -- and the rule the
        # tool asserts is green too, which is the other half of why the old pair
        # could not see this.
        self.workflow()
        self.tool(FIRST_TOOL,
                  with_requirement(committed(FIRST_TOOL), NO_DEPTH_REQUIREMENT))
        self.tool(SECOND_TOOL, committed(SECOND_TOOL))
        sites, _depth, prose, out = self.sites()
        self.assertEqual(len(sites), 4, f"the committed tree holds five:\n{out}")
        self.assertFalse(prose, f"this control is for the keyed hold, "
                                f"not for the rule:\n{out}")
        row = hcs.SITES[2]
        self.assertEqual(carrying(row, sites), [], out)
        found = hcs.problems(sites)
        self.assertEqual(len(found), 1, found)
        self.assertIn(row.fragment, found[0])
        self.assertIn(row.what, found[0])

    def test_the_sibling_going_unread_is_two_rows_named_not_a_shorter_list(self):
        # Control B, and the tree-absence case only: a prose file the reader
        # cannot open is silence, and the keyed hold names a row for each of the
        # two sentences that file was carrying. **This is not the `PROSE_FILES`
        # edit**, and claiming it here would claim the opposite: with the sibling
        # gone from the tree but still listed, the old file-set comparison goes
        # *red* -- it can fire on a file the reader did not find, which is the
        # one direction it could see. The shrink that leaves it green is the
        # committed case below. Reached through a scratch tree rather than by
        # rebinding `PROSE_FILES`, which reaches identical code and keeps the
        # fixture this suite already uses.
        self.workflow()
        self.tool(FIRST_TOOL, committed(FIRST_TOOL))
        sites, _depth, _prose, out = self.sites()
        self.assertEqual(len(sites), 3, out)
        rows = [row for row in hcs.SITES if row.rel == SECOND_TOOL]
        self.assertEqual(len(rows), 2, rows)
        found = hcs.problems(sites)
        self.assertEqual(len(found), len(rows), found)
        for row in rows:
            self.assertEqual(carrying(row, sites), [], out)
            named = [message for message in found if row.fragment in message]
            self.assertEqual(len(named), 1, found)
            self.assertIn(row.what, named[0])

    def test_a_rewrapped_site_is_still_the_same_site(self):
        # Control C, the executable form of "a fragment-keyed identity needs no
        # drift rule". Site 2's comment at different line breaks: the report
        # gives the sentence a different line, and the table still holds it.
        # Without this case that claim is asserted rather than shown, and a
        # line-keyed identity would have needed a stated rule for exactly the
        # move made here.
        self.workflow()
        self.tool(FIRST_TOOL, rewrapped(committed(FIRST_TOOL)))
        self.tool(SECOND_TOOL, committed(SECOND_TOOL))
        sites, _depth, prose, out = self.sites()
        self.assertFalse(prose, out)
        self.assertEqual(len(sites), len(hcs.SITES), out)
        self.assertEqual(hcs.problems(sites), [], out)
        workflows, unreadable = chc.load_workflows(str(REPO))
        before = carrying(hcs.SITES[1], chc.prose_sites(str(REPO),
                                                       workflows, unreadable))
        after = carrying(hcs.SITES[1], sites)
        self.assertEqual(len(before), 1, before)
        self.assertEqual(len(after), 1, after)
        self.assertEqual(hcs.squash(after[0][2]), hcs.squash(before[0][2]))
        self.assertNotEqual(after[0][1], before[0][1],
                            "the rewrap did not move the line the report gives "
                            "this site, so this case is not demonstrating what "
                            "it is written for")

    def test_a_depth_claim_no_row_names_is_a_failure(self):
        # The table's second direction, which a floor has no way to express: a
        # sixth depth claim in either tool is invisible to a count, because the
        # count is satisfied by the five that are named. Without this direction
        # the table would be a floor the other way round and a tool that grows a
        # claim would get no sentence about it.
        self.workflow()
        self.tool(FIRST_TOOL, committed(FIRST_TOOL) + "\n" + NEW_CLAIM)
        self.tool(SECOND_TOOL, committed(SECOND_TOOL))
        sites, _depth, prose, out = self.sites()
        self.assertFalse(prose, out)
        self.assertEqual(len(sites), len(hcs.SITES) + 1, out)
        found = hcs.problems(sites)
        self.assertEqual(len(found), 1, found)
        self.assertIn("matches no row", found[0])
        self.assertIn("ci.yml`'s `gates` job checks out with `fetch-depth: 0`",
                      found[0])

    def test_a_fragment_is_matched_against_its_own_file_only(self):
        # The file scope, which is what keeps a row to one sentence. Both tools'
        # `HISTORY_REQUIREMENT` sentences carry `SHARED_PHRASE` -- one in each
        # file -- so a row written from the wording the two of them share would
        # match a site in each. Asserted through `hcs.match()` and not through
        # `carrying()` above, because `carrying()` applies the scope itself and
        # a case that used it would be testing this suite's own filter: with the
        # matcher's scope dropped, one row would come back carrying a sentence
        # from each file and this is the case that has to notice.
        self.workflow()
        self.tool(FIRST_TOOL, committed(FIRST_TOOL))
        self.tool(SECOND_TOOL, committed(SECOND_TOOL))
        sites, _depth, _prose, out = self.sites()
        self.assertEqual(len([site for site in sites
                              if SHARED_PHRASE in hcs.squash(site[2])]), 2, out)
        row = hcs.Site(SECOND_TOOL, SHARED_PHRASE, "the phrase both sentences carry")
        matched = [site for site, got in zip(sites, hcs.match(sites, [row])) if got]
        self.assertEqual(len(matched), 1, out)
        self.assertEqual(matched[0][0], SECOND_TOOL, out)

    def test_two_rows_matching_one_sentence_is_a_bug_in_the_table(self):
        # Control F, and the direction #1030 filed by its own words: *"a site
        # matching two rows -- reported as a bug in the table, not as a
        # drift"*. The sibling's site 4 occupies two sentences, so the rewrap
        # of control C taken one step further -- both of them merged into one
        # comment, in the committed words -- lands two of that file's rows on
        # one site. That is the move a reader has to be able to make without a
        # false red on the way, and it is the one condition this table used to
        # name in a message without checking, so the case asserts the direction
        # is judged *and* that it is judged as a table fault: nothing has gone
        # missing here, the site is still found.
        self.workflow()
        self.tool(FIRST_TOOL, committed(FIRST_TOOL))
        text = committed(SECOND_TOOL)
        self.assertIn(SIBLING_HEAD, text,
                      "the sibling's site 4 has been reworded away from where "
                      "this control cuts, so it is not the control it says it is")
        self.tool(SECOND_TOOL, text[:text.index(SIBLING_HEAD)] + MERGED_SIBLING)
        sites, _depth, prose, out = self.sites()
        self.assertFalse(prose, out)
        # The two rows, named: one site, both of the sibling's rows on it.
        rows = [row for row in hcs.SITES if row.rel == SECOND_TOOL]
        self.assertEqual(len(rows), 2, rows)
        for row in rows:
            self.assertEqual(len(carrying(row, sites)), 1, out)
        merged = [site for site in sites if site[0] == SECOND_TOOL]
        self.assertEqual(len(merged), 1,
                         f"the merge did not produce one sentence:\n{out}")
        hits = hcs.match(sites)
        carried = [i for i, got in enumerate(hits) if len(got) > 1]
        self.assertEqual(len(carried), 1, hits)
        self.assertEqual(sorted(hits[carried[0]]),
                         sorted(hcs.SITES.index(row) for row in rows), hits)
        found = hcs.problems(sites)
        self.assertEqual(len(found), 1, found)
        self.assertIn("carried by 2 rows", found[0])
        self.assertIn("a bug in this table", found[0])
        for row in rows:
            self.assertIn(row.what, found[0])

class CommittedTreeTests(unittest.TestCase):
    """The committed workflows and the committed prose, as they stand."""

    def test_the_committed_workflows_are_read_and_hold_the_claim(self):
        workflows, unreadable = chc.load_workflows(str(REPO))
        self.assertFalse(unreadable,
                         f"a committed workflow was not read: {unreadable}")
        self.assertFalse(chc.depth_problems(workflows),
                         chc.depth_problems(workflows))

    def test_the_derivation_is_what_the_claim_says_it_is(self):
        # The whole mapping against one literal rather than seven per-key
        # readings of it, so a failure names the row that moved instead of only
        # which key, and so a tenth checkout -- a new workflow, or a second
        # `actions/checkout` in one that has one -- is a failure with them. That
        # is what a re-copy of a template adding `fetch-depth: 0` to a stage this
        # suite had never heard of would produce, and it is the case the table in
        # `docs/findings/history-checkout-claims.md` would need a tenth row for.
        derived, expected = checkout_triples(str(REPO))
        self.assertEqual(
            derived, expected,
            "a committed checkout's (job, depth, stated) triple is not the one "
            "the table in docs/findings/history-checkout-claims.md and the "
            "paragraph in docs/findings.md §86 say it is")

    def test_the_report_names_the_reader_that_put_each_job_on_the_list(self):
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        self.assertIn("every job that runs a history reader has a full-depth "
                      "checkout", text)
        for job in ("gates", "implement", "fix", "resolve"):
            self.assertIn(job, text)
        self.assertIn(".github/scripts/agent-gates.sh", text)

    def test_the_reader_set_is_exactly_the_four_jobs_the_prose_names(self):
        # Held by name and not by count, for the reason the depth table above
        # gives: a count is satisfied by any four. `resolve` is the job the
        # widening added -- it reaches the gate from its prompt at
        # `agent-conflicts.yml:248` -- and it is the one a re-copy of that
        # workflow would take the `fetch-depth: 0` from, so leaving it off this
        # list is the miss that has to stay red.
        workflows, _unreadable = chc.load_workflows(str(REPO))
        readers = {f"{name}/{job.job}": (job.reader, job.route)
                   for name in workflows for job in workflows[name].values()
                   if job.reader}
        self.assertEqual(readers, {
            "ci.yml/gates": (".github/scripts/agent-gates.sh", "a run: step"),
            "agent-implement.yml/implement": (".github/scripts/agent-gates.sh",
                                              "a run: step"),
            "agent-fix.yml/fix": (".github/scripts/agent-gates.sh", "a run: step"),
            "agent-conflicts.yml/resolve": (".github/scripts/agent-gates.sh",
                                            "its prompt"),
        })

    def test_a_prompt_naming_the_gate_in_a_criterion_is_printed_and_not_counted(self):
        # `agent-review.yml`'s `review` is the shape the command-position rule
        # exists to keep out, and it has to be out of it from both sides: absent
        # from the reader list above, and *present* in the line this tool prints
        # for what it declined to count. A rule that neither counts a job nor
        # says it saw one is indistinguishable from a rule that never looked.
        workflows, _unreadable = chc.load_workflows(str(REPO))
        job = workflows["agent-review.yml"]["review"]
        self.assertIsNone(job.reader)
        self.assertEqual(job.named, [(169, ".github/scripts/agent-gates.sh")])
        # And the line is one a reader can go and check, which is the whole
        # reason the loader keeps a position for a parsed scalar.
        self.assertIn(".github/scripts/agent-gates.sh",
                      at_line(REPO / ".github" / "workflows" /
                              "agent-review.yml", 169))

    def test_the_report_prints_the_prompt_it_did_not_count(self):
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        self.assertIn("not in command position", text)
        self.assertIn("agent-review.yml:169 review", text)
        # The blind-spot footer is the report's half of the docstring's own
        # paragraph, and the second declared blind spot is in it: the prepared
        # workflow outside the glob.
        self.assertIn("docs/ci/agent-gates-deep-schedule.yml", text)
        self.assertIn("not found by this method", text)

    def test_the_two_tools_name_the_job_in_every_depth_claim_they_make(self):
        # The control that makes the rest of this suite mean something: on the
        # tree as it stands, the committed prose passes the rule. When a tool's
        # contract paragraph goes stale again, this is what goes red.
        #
        # The `len(sites) >= 4` this case also used to assert is gone, and the
        # keyed hold below subsumes it with the half a count cannot have: *which*
        # site stopped being found. A reader that has stopped finding every site
        # at all is still diagnosed, by that keyed hold rather than by a case
        # elsewhere: with no sites at all, no row matches anything, so
        # `hcs.problems()` returns one message per row.
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        self.assertFalse(chc.prose_problems(sites), chc.prose_problems(sites))

    def test_each_corrected_site_is_still_one_of_the_sites(self):
        # The four sites, held by value. This is literally a list now rather than
        # the file set: each row names a file and a fragment of the sentence at
        # it, and a site that stops being found leaves its row unmatched, which
        # is what neither the `>= 4` floor nor the comparison against
        # `PROSE_FILES` could see -- the first because the tree holds five
        # sentences for four sites, and the second because `prose_sites()`
        # iterates `PROSE_FILES` itself, so a file dropped from it left the set
        # it was compared against holding the answer.
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        self.assertEqual(hcs.problems(sites), [])

    def test_a_file_dropped_from_prose_files_left_the_old_comparison_green(self):
        # Control G, and the edit control B above is not: dropping a file from
        # `PROSE_FILES` rather than losing it from the tree. `prose_sites()`
        # iterates that tuple, so the file leaves the set its found paths are
        # compared against at the same moment it leaves the set that is read --
        # both sides shrink together, the old assert stays green, and two
        # corrected sites go unread under it. The old comparison is run verbatim
        # below, and the message on that assertion says so: a run of it that went
        # red would be showing the other edit.
        #
        # The committed tree, because the point is two rows that really are in a
        # file: a scratch tree has to lose the file outright to make the
        # comparison see anything, and that is control B. `PROSE_FILES` is
        # restored by the cleanup rather than at the end of the case, so a
        # failing assertion here cannot leave the rest of the suite reading a
        # one-entry tuple.
        saved = chc.PROSE_FILES
        self.addCleanup(setattr, chc, "PROSE_FILES", saved)
        chc.PROSE_FILES = tuple(rel for rel in saved if rel != SECOND_TOOL)
        self.assertEqual(len(chc.PROSE_FILES), len(saved) - 1,
                         "`PROSE_FILES` does not hold the sibling this case "
                         "drops, so the edit is not the one it names")
        workflows, unreadable = chc.load_workflows(str(REPO))
        sites = chc.prose_sites(str(REPO), workflows, unreadable)
        found = {rel for rel, _line, _sentence, _named, _job in sites}
        self.assertEqual(
            found, set(chc.PROSE_FILES),
            "the file-set comparison this replaced went red on the tree it was "
            "blind to, so the argument that it could not see this edit does not "
            "hold and the page beside it is wrong")
        # And the keyed hold, on the same read, names the two rows the file was
        # carrying -- each by its own fragment, not by a count.
        rows = [row for row in hcs.SITES if row.rel == SECOND_TOOL]
        self.assertEqual(len(rows), 2, rows)
        problems = hcs.problems(sites)
        self.assertEqual(len(problems), len(rows), problems)
        for row in rows:
            named = [message for message in problems if row.fragment in message]
            self.assertEqual(len(named), 1, problems)
            self.assertIn(row.what, named[0])

    def test_the_report_prints_every_checkout_it_found(self):
        out = io.StringIO()
        with redirect_stdout(out):
            chc.report(str(REPO))
        text = out.getvalue()
        for name in ("ci.yml / gates", "ci.yml / workflows",
                     "claude.yml / claude", "agent-plan.yml / plan"):
            self.assertIn(name, text)


class TheTwoEdits(ScratchTree):
    """The two edits the table exists to object to, on a copy of the workflows.

    A scratch root, because neither edit can be made to the committed workflows
    from this branch: the push token has no `workflow` scope, and the point is
    the suite's reaction rather than the workflows' new contents. `load_workflows`
    reads only `.github/workflows/` and `report()` degrades to silence on absent
    prose, so a workflows-only root is all any of this needs.

    **The control is watching the committed assertion, not a second copy of it.**
    Both halves come from `checkout_triples`, the same helper the committed case
    compares with, and the copy is asserted to hold the table before either edit
    is applied -- a scratch tree that did not would make both edits below pass
    for the wrong reason, which is the failure this suite's own docstring names
    twice over and the reason the stale sentences up there are pasted verbatim.
    """

    def copy_workflows(self):
        """The committed workflows into the scratch root, unchanged."""
        source = os.path.join(REPO, ".github", "workflows")
        for name in sorted(os.listdir(source)):
            if name.endswith(".yml"):
                with open(os.path.join(source, name), encoding="utf-8") as handle:
                    text = handle.read()
                self.put(os.path.join(".github", "workflows", name), text)

    def edit(self, rel, old, new):
        """Replace `old` with `new` in `rel` under the scratch root, once.

        The refusal is the point. An anchor that has stopped being unique would
        otherwise leave the file either alone or changed somewhere the case does
        not name, and a mutation that moved nothing reds nothing -- which reads
        exactly like a table that does not notice the edit.
        """
        path = os.path.join(self.root, rel)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        self.assertEqual(text.count(old), 1,
                         f"the anchor this case edits {rel} with is not unique "
                         f"there, so the edit would not be the one it names")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.replace(old, new))

    def test_the_table_turns_red_on_each_of_the_two_edits_it_exists_for(self):
        # Each is one of the two published sentences going false with nothing
        # moving to contradict it: `plan` joining the four full-depth stages the
        # retraction was about, and `claude.yml` losing the only depth in these
        # workflows that a step *states* rather than inherits. Neither job runs a
        # history reader, so `depth_problems()` puts no constraint on either and
        # the table is the only thing that objects -- which is why the assertion
        # is re-run here rather than a check of the tool's own verdicts.
        #
        # The last element of each case is what the edit should have produced,
        # asserted positively: a mutation that landed under the wrong job, or one
        # that broke the YAML and dropped the file out of the derivation
        # altogether, would redden the table too, and for a reason that has
        # nothing to do with the claim.
        edits = (
            ("agent-plan.yml's plan job takes a full-depth checkout",
             ".github/workflows/agent-plan.yml",
             "        with:\n          persist-credentials: false\n",
             "        with:\n          fetch-depth: 0\n"
             "          persist-credentials: false\n",
             ("agent-plan.yml", [("plan", 0, True)])),
            ("claude.yml's stated fetch-depth: 1 goes away",
             ".github/workflows/claude.yml",
             "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
             "        with:\n          fetch-depth: 1\n",
             "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4\n"
             "        with:\n",
             ("claude.yml", [("claude", 1, False)])),
        )
        self.copy_workflows()
        derived, expected = checkout_triples(self.root)
        self.assertEqual(
            derived, expected,
            "an unmodified copy of the committed workflows does not hold the "
            "table, so every edit below would pass for the wrong reason")
        for name, rel, old, new, row in edits:
            with self.subTest(edit=name):
                # A fresh copy per edit, so the two do not compose and a failure
                # says which one of them the table let past.
                self.copy_workflows()
                self.edit(rel, old, new)
                derived, expected = checkout_triples(self.root)
                self.assertEqual(derived.get(row[0]), row[1],
                                 f"the edit did not land where it says it did: "
                                 f"{derived.get(row[0])}")
                self.assertNotEqual(
                    derived, expected,
                    f"the table still holds after {name}, which is the edit the "
                    f"committed case above cannot see and this one exists for")


if __name__ == '__main__':
    unittest.main()
