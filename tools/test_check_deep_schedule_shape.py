#!/usr/bin/env python3
"""The refusals on the *committed* schedule, and the process around them.

`tools/check_deep_schedule_shape.py --self-test` already holds its five rules
on typed fixtures. Two things it deliberately does not do are the two this file
is for, and both are the ones that would let it pass while having stopped
working.

**The fixtures are the tool's own idea of the file.** Every rule in `scan()`
was written beside a `schedule_text()` that produces the shape those rules
expect, so a rule and its fixture agreeing proves very little. What is not
circular is a mutation of the *committed* file, and that is why `--schedule`
exists: it lets each mutation here run as a **subprocess** over a copy, so what
the case sees is the exit code a consumer sees. Patching `SCHEDULE` in-process
could not -- the tool's own `main()` reads the module constant, and a case that
reached past it to set the constant would be testing the patch as much as the
rule.

**`--self-test` running is not the same as `--self-test` passing.** The
self-test is the tool's own answer sheet, and a self-test that raised before its
last assertion would look the same from outside as one that passed, unless
something turns its return value into a process status. The first case here is
that something.

**The two tools must not come to disagree.** `check_deep_schedule_shape` reads
comments and `$RUNNER_TEMP` through the sibling's `shell_code()` and
`RUNNER_TEMP_SHELL` rather than its own, so that a schedule cannot be clean to
one checker and red to the other over a spelling. `AgreementTests` pins that
import from outside, because the day it stops being an import and becomes a
copy is the day the two disagree, and a rule that fires on a comment is a rule
everybody switches off.

**No count is asserted.** Not the number of `uses:`, not the number of steps:
both move with the file, and an expected count turns every added step into a
failure. What is held is that the discovery is non-empty, that the committed
tree is clean, and that the exit code is 0 or 1 -- properties that are true of
the tree rather than of this tool. Nothing here runs a nightly:
`docs/ci/agent-gates-deep-schedule.yml` is prepared, not landed, so there is no
artifact to read and no hardware, no assembler and no Windows is involved at
all.
"""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_deep_schedule_shape as tool  # noqa: E402
import check_deep_schedule_emit as sibling  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parent


def run_tool(*argv):
    """The tool as a subprocess: (returncode, stdout, stderr).

    A subprocess rather than an in-process call throughout, because for a
    checker the exit code is the product and nothing in-process turns a return
    value into a status. Captured rather than inherited, so a refusal's own
    words land in the assertion's message and not in the suite's output, where
    the next real failure would be the one a reader has to find.
    """
    done = subprocess.run(
        [sys.executable, str(HERE / "check_deep_schedule_shape.py"), *argv],
        capture_output=True, text=True, cwd=str(REPO))
    return done.returncode, done.stdout, done.stderr


class ProcessTests(unittest.TestCase):
    """The run, because for a checker `main()` is the product and its exit code
    is the whole of it."""

    def test_self_test_passes_and_the_run_is_green(self):
        rc, out, _err = run_tool("--self-test")
        self.assertEqual(rc, 0, out)
        self.assertIn("all assertions passed", out)

    def test_check_on_the_committed_tree_is_green_with_a_quiet_stderr(self):
        rc, out, err = run_tool("--check")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(err, "", "a clean --check says nothing on stderr; a "
                                   "reader routing streams cannot tell a "
                                   "verdict from a note")
        self.assertIn("the shape is as documented", out)

    def test_check_names_its_own_scope_and_what_it_does_not_hold(self):
        # The calibration line, held. A green run that reads as "the workflow
        # linted clean" is the overclaim this whole change exists to stop: the
        # linters could not be run, and only one of actionlint's three checks
        # was measured. The tool says which in its own output rather than
        # leaving a reader to infer it from a green exit code.
        _rc, out, _err = run_tool("--check")
        self.assertIn("docs/ci/agent-gates-deep-schedule.yml", out,
                      "the scope line names the file it read, so a reader can "
                      "tell a clean file from a clean discovery")
        self.assertIn("not held here", out)
        self.assertIn("pipefail", out)
        self.assertIn("deep-schedule-lint-baseline.md", out,
                      "and it says where the measurement lives, so the limit "
                      "is a pointer rather than a shrug")

    def test_the_discovery_is_not_empty_on_a_clean_file(self):
        # The check that separates "clean" from "matched nothing". A rule set
        # that read no `uses:` at all would be silent on a file that has four.
        _rc, out, _err = run_tool("--check")
        self.assertRegex(out, r"and the [1-9][0-9]* `uses:` pin\(s\)",
                         "the scope line reports a non-zero number of `uses:`, "
                         "which is what makes the clean verdict a finding "
                         "rather than an absence")

    def test_a_schedule_that_is_not_there_is_reported_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _out, err = run_tool("--schedule", str(Path(tmp) / "gone.yml"))
        self.assertEqual(rc, 1)
        self.assertIn("cannot read", err)

    def test_help_reaches_every_mode(self):
        # Otherwise reached by nothing at all, since every other invocation here
        # names a mode.
        rc, out, _err = run_tool("--help")
        self.assertEqual(rc, 0, out)
        for flag in ("--check", "--self-test", "--schedule"):
            self.assertIn(flag, out)


class MutationTests(unittest.TestCase):
    """One case per way the committed schedule can stop being a nightly.

    Each mutates a **copy of the real file** and runs `--check` over it, so the
    rule and the expectation are both about the file a human will copy into
    `.github/workflows/` rather than about a fixture this tool wrote.
    """

    def setUp(self):
        self.real = tool.SCHEDULE.read_text(encoding="utf-8")
        # A guard rather than an assumption: every mutation below is a
        # substitution into this text, and a string that is not present would
        # make the case assert against an unmutated file and pass for the wrong
        # reason.
        self.assertIn("AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh",
                      self.real)

    def _mutated(self, mutate):
        """`--check` as a subprocess over a mutated copy, as (rc, out, err).

        The `assertNotEqual` is the load-bearing half and it is why this is a
        helper rather than a `subprocess` call per case: a substitution whose
        text is not present leaves the file unmutated, and a case written
        against a string that moved would then assert against the real schedule
        and pass for a reason that has nothing to do with the rule.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.yml"
            before, after = self.real, mutate(self.real)
            self.assertNotEqual(before, after,
                                "the mutation changed nothing, so this case "
                                "would pass without testing the rule")
            path.write_text(after, encoding="utf-8")
            return run_tool("--schedule", str(path))

    def refuses(self, mutate, needle):
        rc, out, err = self._mutated(mutate)
        self.assertEqual(rc, 1, "a mutated schedule was accepted:\n" + out)
        self.assertIn(needle, out + err)
        return out

    def accepts(self, mutate, needle):
        """The other half: an edit that must *not* turn the check red.

        Every helper that only refuses is satisfied by a `scan()` that refuses
        everything, so the mutations here are the ones that look like defects
        and are not -- a comment naming the gate command, a `#` inside a path.
        """
        rc, out, err = self._mutated(mutate)
        self.assertEqual(rc, 0, "an edit that changes nothing went red:\n"
                                 + out + err)
        self.assertIn(needle, out)
        return out

    def test_the_unmutated_copy_is_green(self):
        # The control for every case below. Without it, a `scan()` that refused
        # everything would pass all of them.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "copy.yml"
            path.write_text(self.real, encoding="utf-8")
            rc, out, err = run_tool("--schedule", str(path))
        self.assertEqual(rc, 0, out + err)

    # --- hold 1: the triggers ------------------------------------------------

    def test_the_manual_trigger_removed(self):
        # Not a nicety: a nightly GitHub silently drops has no other way to be
        # re-run, and that re-run is what tells "did not run" from "found
        # nothing".
        self.refuses(lambda t: t.replace("  workflow_dispatch:\n", ""),
                     "no `workflow_dispatch`")

    def test_the_cron_replaced_by_something_that_never_fires(self):
        self.refuses(lambda t: t.replace("    - cron: '23 4 * * *'",
                                         "    - run: nightly"),
                     "no `cron:`")

    def test_the_schedule_removed(self):
        self.refuses(lambda t: t.replace("  schedule:\n", ""), "no `schedule:`")

    # --- hold 2: the one gate command ---------------------------------------

    def test_the_deep_flag_dropped(self):
        # The most damaging single edit in this file, and the one nothing else
        # catches: the nightly would re-encode nothing and its log would be
        # shaped exactly like a pass.
        self.refuses(
            lambda t: t.replace("AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh",
                                ".github/scripts/agent-gates.sh"),
            "without the `AGENT_GATES_DEEP=1` prefix")

    def test_a_second_gate_invocation(self):
        out = self.refuses(
            lambda t: t.replace(
                "      - name: Upload the deep gates log",
                "      - name: Deep gates again\n        run: |\n"
                "          AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh\n"
                "\n"
                "      - name: Upload the deep gates log"),
            "named 2 time(s)")
        self.assertIn("'Deep gates again'", out,
                      "and both steps are named, so a reader is told which "
                      "two and not merely that there are two")

    # --- hold 3: the tee -----------------------------------------------------

    def test_the_tee_removed(self):
        # The step still runs; what goes is the pipe to the log, which is the
        # only thing that makes a run's absence observable.
        self.refuses(
            lambda t: t.replace('            | tee "$RUNNER_TEMP/deep-gates.log"\n',
                                ""),
            "does not pipe")

    def test_the_tee_pointed_inside_the_repository(self):
        self.refuses(
            lambda t: t.replace('"$RUNNER_TEMP/deep-gates.log"',
                                '"logs/deep-gates.log"'),
            "not under $RUNNER_TEMP")

    # --- hold 4: the permissions width --------------------------------------

    def test_the_token_widened(self):
        self.refuses(lambda t: t.replace("permissions:\n  contents: read",
                                         "permissions:\n  contents: write"),
                     "rather than `contents: read`")

    def test_a_second_scope_added_at_the_top_level(self):
        self.refuses(lambda t: t.replace("permissions:\n  contents: read",
                                         "permissions:\n  contents: read\n"
                                         "  actions: write"),
                     "wider than `contents: read`: actions")

    def test_a_job_widening_its_own(self):
        # The top-level block still reads correctly, which is exactly why the
        # hold is over every job rather than over the key the issue named.
        self.refuses(
            lambda t: t.replace("  deep:\n    runs-on: ubuntu-latest",
                                "  deep:\n    runs-on: ubuntu-latest\n"
                                "    permissions:\n      contents: write"),
            "declares its own `permissions:")

    # --- hold 5: the pins ---------------------------------------------------

    def test_an_action_unpinned_to_a_tag(self):
        self.refuses(
            lambda t: t.replace("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                                "actions/checkout@v7"),
            "not to a 40-character commit sha")

    def test_the_local_action_renamed_away(self):
        # A local `uses:` is exempt from the pin precisely because it is in this
        # repository, so a path that stopped resolving is the only thing that
        # can catch it -- and this file's `Set up the toolchain` step is the one
        # that would fail the night.
        self.refuses(
            lambda t: t.replace("uses: ./.github/actions/project-setup",
                                "uses: ./.github/actions/toolchain"),
            "has no `action.yml`")

    # --- the negative controls ----------------------------------------------

    def test_a_comment_naming_the_gate_command_is_not_an_invocation(self):
        # The clause that decides whether this tool survives a week. The
        # committed schedule documents what it does -- the deep flag, the tee,
        # where the log lands -- and has to be able to say so inside its own
        # `run:` blocks. A rule that fired on the sentence stating it would go
        # red on the correct file, which is how a gate gets switched off.
        out = self.accepts(
            lambda t: t.replace(
                "          set -o pipefail",
                "          # the same command is AGENT_GATES_DEEP=1\n"
                "          # .github/scripts/agent-gates.sh, and its output is\n"
                "          # written under $RUNNER_TEMP/deep-gates.log\n"
                "          set -o pipefail"),
            "the shape is as documented")
        self.assertIn("one AGENT_GATES_DEEP=1 gate invocation", out,
                      "and the count is one, so the comment did not read as a "
                      "second invocation")

    def test_a_comment_naming_a_tarball_is_not_a_pin(self):
        # The other side of hold 5. The pin rule reads a `uses:` key, not the
        # text around it, so a comment explaining a pin is not a pin failing.
        self.accepts(
            lambda t: t.replace("      - name: Checkout",
                                "      # every action below is a sha, not a tag\n"
                                "      - name: Checkout"),
            "the shape is as documented")

    def test_a_hash_inside_a_path_is_not_a_comment(self):
        # The other side of the strip, chosen so the two readings give
        # *different* verdicts rather than the same one. A strip that treated
        # any `#` as a comment would swallow the rest of the line, the `tee`
        # would stop being found, and the refusal would read "does not pipe" --
        # a different finding, about a different mistake. `#` is only a comment
        # at a line's start or after whitespace, so the destination is read
        # whole and the refusal is the narrow one.
        out = self.refuses(
            lambda t: t.replace('"$RUNNER_TEMP/deep-gates.log"',
                                '"logs#x/$RUNNER_TEMP/deep.log"'),
            "not under $RUNNER_TEMP")
        self.assertNotIn("does not pipe", out,
                         "the tee was still found, so the refusal is about "
                         "where it points and not about a `#` that swallowed "
                         "the line")


class AgreementTests(unittest.TestCase):
    """The two checkers must read the schedule the same way.

    `check_deep_schedule_shape` imports `shell_code` and `RUNNER_TEMP_SHELL`
    from `check_deep_schedule_emit` for the reason
    `docs/findings/…` — stated in the module docstring — gives: a prepared file
    that is clean to one checker and red to the other is a gate that gets
    switched off. These hold the arrangement rather than the outcome, because
    the day the import becomes a copy is the day the outcome stops meaning
    anything.
    """

    def test_the_strip_and_the_runner_temp_spellings_are_the_siblings(self):
        self.assertIs(tool.shell_code, sibling.shell_code,
                      "the two checkers no longer share one comment strip, so "
                      "a schedule can be clean to one and red to the other "
                      "over a comment")
        self.assertIs(tool.RUNNER_TEMP_SHELL, sibling.RUNNER_TEMP_SHELL,
                      "the two checkers no longer agree on which spellings of "
                      "$RUNNER_TEMP count")

    def test_both_checkers_are_green_on_the_committed_schedule(self):
        # The property the sharing exists for, asserted rather than assumed.
        for name, argv in (("check_deep_schedule_shape", ("--check",)),
                           ("check_deep_schedule_emit", ("--check",))):
            done = subprocess.run(
                [sys.executable, str(HERE / ("%s.py" % name)), *argv],
                capture_output=True, text=True, cwd=str(REPO))
            self.assertEqual(done.returncode, 0,
                             "%s is red on the committed schedule:\n%s"
                             % (name, done.stdout + done.stderr))

    def test_the_two_hold_disjoint_sets_of_claims(self):
        # The reason there are two tools rather than one, held as behaviour
        # rather than left to the two docstrings to agree about. Each edit is
        # refused by exactly one of them, which is what "a complement" means:
        # a claim both held would be duplicated and a claim neither held would
        # read as covered. Asserted through the two checkers' exit codes, so
        # this says nothing about either one's internals.
        def verdicts(text, name):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "mutated.yml"
                path.write_text(text, encoding="utf-8")
                done = subprocess.run(
                    [sys.executable, str(HERE / ("%s.py" % name)),
                     "--schedule", str(path)],
                    capture_output=True, text=True, cwd=str(REPO))
            return done.returncode

        real = tool.SCHEDULE.read_text(encoding="utf-8")
        mine = "check_deep_schedule_shape"
        theirs = "check_deep_schedule_emit"

        # The triggers, which the sibling never reads.
        no_dispatch = real.replace("  workflow_dispatch:\n", "")
        self.assertNotEqual(no_dispatch, real)
        self.assertEqual(verdicts(no_dispatch, mine), 1)
        self.assertEqual(verdicts(no_dispatch, theirs), 0,
                         "the sibling is red over the triggers, so the two "
                         "tools are not disjoint and this one is redundant")

        # The emit step's destination, which this one never reads. The flag
        # itself survives in the step's own log banner, so the sibling refuses
        # on the missing destination rather than on a missing step -- which
        # clause it picks is its business; the exit code is what is held here.
        no_emit = real.replace(
            '--emit-csv "$RUNNER_TEMP/deep-gates-csv.csv"',
            '--report "$RUNNER_TEMP/night.csv"')
        self.assertNotEqual(no_emit, real)
        self.assertEqual(verdicts(no_emit, theirs), 1)
        self.assertEqual(verdicts(no_emit, mine), 0,
                         "this checker is red over the second artifact, so the "
                         "two tools are not disjoint and one of them is "
                         "redundant")

    def test_the_shape_checkers_own_findings_are_read_off_the_committed_file(self):
        # What a green run actually looked at, held so a discovery that matched
        # nothing cannot read as a clean file. The counts are never asserted:
        # they move with the file, and an expected count is a value every edit
        # has to touch.
        found, problems = tool.scan(tool.SCHEDULE.read_text(encoding="utf-8"),
                                    root=REPO)
        self.assertEqual(problems, [])
        self.assertIn("workflow_dispatch", found.triggers)
        self.assertIn("schedule", found.triggers)
        self.assertEqual(found.permissions, tool.READ_ONLY)
        self.assertTrue(found.uses, "no `uses:` was read, so the pin rule held "
                                    "nothing")
        self.assertEqual(found.gate, "Deep gates")
        self.assertTrue(found.tee.startswith("$RUNNER_TEMP"), found.tee)


class NoWriteTests(unittest.TestCase):
    """Nothing in the tool writes to the tree it reads."""

    def test_a_full_run_leaves_the_working_tree_untouched(self):
        # Held for a *new* mode the way the sibling holds it for its own: the
        # only way to know a run has no second writer for a file nothing else
        # writes is to run every mode and see the tree come back identical.
        before = _tree_digest()
        for argv in (("--check",), ("--self-test",)):
            run_tool(*argv)
        self.assertEqual(_tree_digest(), before,
                         "a run wrote to the tree it reads")


def _tree_digest():
    """A digest of every file this tool's modes could plausibly write to.

    The schedule and the local action its `uses:` resolves to: the two paths
    named in this file and in the tool. Not the whole tree -- a digest of
    thousands of files to assert "this module opens no files for writing" is a
    slow way to say the same thing.
    """
    digest = hashlib.sha256()
    for path in (tool.SCHEDULE, REPO / tool.LOCAL_ACTION[2:] / "action.yml"):
        digest.update(str(path).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
