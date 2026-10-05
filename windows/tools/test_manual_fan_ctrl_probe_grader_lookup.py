#!/usr/bin/env python3
"""Offline checks on how `manual_fan_ctrl_probe.py --self-test` finds its grader.

The self-test is the pre-flight for the §3 hardware run
(`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`): it hands a
synthesised capture to the grader's own reader, so a tools directory staged
onto a Windows box has to be able to reach that grader or the check cannot be
run there at all. It used to reach for it at one hard-coded path, which a
staged directory either has no depth for or has no checkout under -- the two
shapes `ec_watch.py`'s ordered lookup was written for (#549), and what this
suite holds the probe to now that it shares that lookup rather than its own.

Every case is offline: a temporary directory standing in for the staged tools
directory, `ecrw_fake` for the EC, no Windows, no EC opened and no register
read. Whether a staged directory is where an operator actually puts this file
is a human's observation, and it is #663's run to record.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import ecrw_fake

ecrw_fake.install()

# Imported by name, not by path under a second module object: the probe's
# lookup is a lazy `import ec_watch`, so a private name would leave the probe
# importing this directory's file -- the one whose `__file__` the cases below
# stage, and the one whose `grader_candidates` they record.
import ec_watch

spec = importlib.util.spec_from_file_location(
    'manual_fan_ctrl_probe',
    Path(__file__).with_name('manual_fan_ctrl_probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

# The grader a checkout holds, which is what the cases below copy into a staged
# directory. The self-test drives that module's own reader, block walk and
# `EARLY_EXIT_TAG`, so a stub would answer a different question than the one a
# box asks.
COMMITTED = Path(__file__).resolve().parents[2] / "ec" / "tools" \
    / "grade_0751_isolation.py"


class GraderLookupTests(unittest.TestCase):
    """The probe's own lookup, over temporary directories.

    These are the cases #549 wrote for `ec_watch.py` turned on the second
    caller, because a shared list is only shared if the caller asks for it. Each
    holds a relation -- which candidate the search reached, and which one it
    named when it reached nothing -- rather than a count of candidates.
    """

    # What a refusal looks like from here: this tool refuses with `sys.exit` and
    # a message rather than a return, which `main` does for its other two
    # refusals too, so the run never comes back and `SystemExit.code` carries
    # the sentence the operator reads.
    RETURNED = "the self-test returned instead of refusing"

    def checkout_tree(self, root):
        """Where a checkout puts the tools directory, under `root`.

        `root/windows/tools/ec_watch.py` is the committed shape and the one both
        built-in candidates are derived from, so a case that puts a grader at
        either of those places is putting it inside its own temporary
        directory, where no other case can have left one.
        """
        tools = root / "windows" / "tools"
        tools.mkdir(parents=True)
        return tools / "ec_watch.py"

    def checkout_copy(self, tool):
        """Where the committed copy sits, given `checkout_tree`'s `tool`.

        `parents[2]` of `root/windows/tools/ec_watch.py` is `root`, so this is
        `root/ec/tools/grade_0751_isolation.py` whichever tree it was handed.
        Resolved the way `grader_candidates` resolves `__file__`, so a case can
        compare against what the lookup returned rather than against the string
        it was handed.
        """
        return tool.resolve().parents[2] / "ec" / "tools" \
            / "grade_0751_isolation.py"

    def beside(self, tool):
        """The beside-the-tool candidate, which is what a staged one is.

        `ec_watch.py`'s own directory rather than the probe's, because
        `grader_candidates` reads that file's `__file__` and these tools are
        staged as a directory -- so it is the directory the probe sits in too,
        and the message names a place an operator can act on.
        """
        return tool.resolve().with_name("grade_0751_isolation.py")

    def staged_tools(self, root):
        """A tools directory copied onto a box: no checkout above it.

        `root/staged/tools/ec_watch.py` is `C:\\tools\\ec_watch.py` in shape --
        deep enough that `parents[2]` names a directory, which here is the
        temporary one, and with nothing above it but the temporary directory
        itself. The checkout candidate is therefore this case's to leave empty,
        which is the situation the beside-the-tool candidate exists for.
        """
        tools = root / "staged" / "tools"
        tools.mkdir(parents=True)
        return tools / "ec_watch.py"

    def shallow_tools(self):
        """The staged depth with no `parents[2]` to index at all.

        Never created, and for the reason `test_ec_watch.py`'s own case gives:
        what is under test is that the lookup survives the depth, and a real
        directory at a drive root is not something a suite can stage portably.
        Nothing is written at `/tools` either, so a machine that kept a grader
        there would fail this case rather than pass it by accident. The
        candidates it derives are compared the way `grader_candidates` reads
        `__file__`, after `resolve()`.
        """
        return Path("/tools/ec_watch.py")

    def copy_grader(self, path):
        """The committed grader, put at `path` as a staged one is left."""
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(COMMITTED, path)
        return path

    def run_self_test(self, tool, candidates=None):
        """(code, refusal, report, offered) from the probe's `--self-test`.

        `refusal` is `SystemExit.code`, the sentence this tool refuses with,
        and is None when the run came back instead. `offered` is what
        `ec_watch.grader_candidates` returned on the call the probe made,
        recorded there rather than recomputed: a suite that recomputed it would
        ask the same question twice and would stay green if the probe stopped
        asking. `candidates` substitutes a list of the case's own, for the one
        shape the shared list cannot produce.

        Both `__file__`s go to the same staged path. The lookup reads
        `ec_watch.py`'s, which is the whole of why sharing it resolves to the
        same grader rather than only to less code; patching the probe's as well
        is what makes these regression cases rather than descriptions, since a
        probe that went back to a path of its own would read that one instead.
        """
        out, offered = io.StringIO(), []
        shared = ec_watch.grader_candidates

        def record(*args, **kwargs):
            offered.extend(shared(*args, **kwargs) if candidates is None
                           else candidates)
            return offered

        with patch.object(ec_watch, "grader_candidates", record), \
             patch.object(ec_watch, "__file__", str(tool)), \
             patch.object(probe, "__file__",
                          str(tool.with_name("manual_fan_ctrl_probe.py"))), \
             patch.object(probe, "Ec", lambda: self.fail("opened an EC")), \
             contextlib.redirect_stdout(out):
            try:
                return probe.main(["0xA0", "--self-test"]), None, \
                    out.getvalue(), offered
            except SystemExit as e:
                return None, str(e.code), out.getvalue(), offered

    def test_the_checkout_copy_is_reached_before_one_beside_the_tool(self):
        # Both candidates hold a file, so the search order alone decides the
        # run -- and the staged one raises at load, which is what makes this a
        # statement about order rather than about either file working. The list
        # the probe was offered is `ec_watch.py`'s own, so a probe carrying a
        # private copy of it fails here rather than quietly reaching the same
        # answer.
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.checkout_tree(Path(tmp))
            self.copy_grader(self.checkout_copy(tool))
            self.beside(tool).write_text(
                "raise RuntimeError('the staged copy must not be reached')\n")
            code, refusal, report, offered = self.run_self_test(tool)
        self.assertIsNone(refusal, msg=report)
        self.assertEqual(code, 0)
        self.assertIn("self-test passed", report)
        # The relation rather than a count: the search leads with the copy the
        # checkout holds, and the beside-the-tool copy is offered behind it
        # rather than not at all.
        self.assertEqual(offered[0], self.checkout_copy(tool))
        self.assertIn(self.beside(tool), offered)

    def test_a_candidate_that_is_there_and_will_not_load_is_refused(self):
        # The candidate order is only safe if a file that is there and broken
        # stops the search. A staged copy quietly standing in for a committed
        # grader broken since the checkout was made is a self-test that passes
        # against a rule the tree does not hold, and the operator finds that
        # out at the grading rather than at the box.
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.checkout_tree(Path(tmp))
            self.copy_grader(self.beside(tool))
            broken = self.checkout_copy(tool)
            broken.parent.mkdir(parents=True, exist_ok=True)
            broken.write_text("REQUIRED_LABEL_FORMS = (\n")       # SyntaxError
            code, refusal, report, _ = self.run_self_test(tool)
        self.assertIsNone(code, msg=self.RETURNED)
        self.assertIn(str(broken), refusal)
        # And the loadable candidate behind it never got a say: this refused
        # rather than running against the copy that does load.
        self.assertNotIn(str(self.beside(tool)), refusal)
        self.assertNotIn("self-test passed", report)

    def test_a_candidate_importlib_cannot_load_is_refused_the_same_way(self):
        # `spec_from_file_location` returns None for a suffix importlib has no
        # loader for, and `module_from_spec(None)` is an AttributeError naming
        # no file an operator can act on. The shared list names a `.py` at
        # every entry, so that is not a shape it produces -- which is why
        # this case hands the probe a list of its own rather than staging one.
        # What is under test is that such a candidate is refused by name
        # rather than raised out of a traceback, the same one refusal a
        # syntax error gets.
        with tempfile.TemporaryDirectory() as tmp:
            notes = Path(tmp) / "notes.txt"
            notes.write_text("these are not a grader\n")
            code, refusal, _, _ = self.run_self_test(
                self.staged_tools(Path(tmp)), [notes])
        self.assertIsNone(code, msg=self.RETURNED)
        self.assertIn(str(notes), refusal)
        self.assertIn("will not load", refusal)

    def test_a_tool_with_no_checkout_above_it_is_refused_by_name(self):
        # No `IndexError`, and a refusal naming the one place it looked rather
        # than a traceback. Through `main`, so the whole startup path is what
        # refuses, with both tools at that depth together -- which is what a
        # directory copied onto a box is.
        tool = self.shallow_tools()
        code, refusal, _, offered = self.run_self_test(tool)
        self.assertIsNone(code, msg=self.RETURNED)
        # The beside-the-tool copy is offered alone at this depth: a path that
        # cannot be named is not a place a checkout can be.
        self.assertEqual(offered, [self.beside(tool)])
        self.assertIn(str(self.beside(tool)), refusal)

    def test_a_refusal_names_every_place_it_looked(self):
        # The sentence an operator at a staged box reads, and the two ways out
        # of it are not something they can be expected to guess from a path
        # they have no way to create. Checked on the names rather than on an
        # exact string, so a rewording does not redden this while a *missing*
        # name does.
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.checkout_tree(Path(tmp))
            code, refusal, _, _ = self.run_self_test(tool)
            for candidate in (self.checkout_copy(tool), self.beside(tool)):
                self.assertIn(str(candidate), refusal)
                self.assertFalse(candidate.is_file())
        self.assertIsNone(code, msg=self.RETURNED)
        self.assertIn("ec_watch.py", refusal)
        self.assertIn("checkout", refusal)

    def test_the_self_test_runs_from_a_staged_tools_directory(self):
        # The whole of the issue: a `__file__` at a staged depth, with a grader
        # beside the tools, reaches a self-test that completes rather than
        # raising. Asserted through the tool's own report, so what is checked
        # is the run a human gets rather than the load that fed it.
        with tempfile.TemporaryDirectory() as tmp:
            tool = self.staged_tools(Path(tmp))
            self.copy_grader(self.beside(tool))
            code, refusal, report, _ = self.run_self_test(tool)
        self.assertIsNone(refusal, msg=report)
        self.assertEqual(code, 0)
        self.assertIn("self-test passed", report)
        # And the calibration the tool's own last line carries: nothing here
        # opened the EC, read a register, or says anything about the machine.
        self.assertIn("No EC was opened, no register was read", report)


if __name__ == "__main__":
    unittest.main()