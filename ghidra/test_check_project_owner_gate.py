#!/usr/bin/env python3
"""Offline checks for `ghidra/check_project_owner_gate.py`: that the committed
Ghidra projects still record an owner, and that every driver which copies one
for a run still retakes it on the copy.

**What this stands in for.** Issue #572's fourth "done looks like" -- the gate
that fails with a readable message naming the project and the owner rewrite, and
a regression check that fails if the rewrite is dropped. The tool under test is
cheap by construction (committed text, no Ghidra, no image), so every case here
is too: nothing opens a project and nothing starts a JVM.

**The refusals carry the weight, and they run over a mirror tree rather than
over arguments alone.** A check that finds nothing wrong is what a clean run
reports, so `check()` has to have been seen to go red or nothing it says means
anything. `MirrorTreeTests` builds the whole repository shape the check reads --
three `.rep`s and the drivers -- in a `tempfile`, faults one thing at a time,
and runs `check()` over each. Reading a driver's source is the part under test,
and that only happens through the file.

**The case that decides whether the drivers' own self-tests are worth
anything.** `build_ec_decompile.py --self-test` used to make its own copy and
call `rewrite_owner()` on it, which proved the helper works and said nothing
about whether `analyze()` still called it: deleting the rewrite from the export
path left every assertion green while the default export stopped running. The
fix is that the self-test now drives `copy_project_for_export()`.
`DriverSelfTestsDriveTheCopyPathTests` is what holds that shape, because a driver
going back to a self-made copy would otherwise be a green suite and a broken
export at the same time -- the exact state this repository had.

**What a green run here does not show.** That a non-owner can complete an
export, that the committed `.rep` survives a real run byte-identical, or that
the rewrite is *sufficient* for the open rather than merely present in the copy
path. Those are the drivers' `--self-test --oracle` and the run recorded in
`docs/findings/ghidra-project-owner.md`.
"""
import ast
import contextlib
import getpass
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import check_project_owner_gate as gate  # noqa: E402  (the path insert above is what makes this work)

# A driver carrying both halves `check()` looks for: the copy and the rewrite in
# one function. Written out rather than patched out of the committed driver, so
# a case can fault one line of it without touching the tree.

# What Ghidra writes: one OWNER state, whose value is the fixture's to choose.
PRP = """<?xml version="1.0" encoding="UTF-8"?>
<FILE_INFO>
    <BASIC_INFO>
        <STATE NAME="OWNER" TYPE="string" VALUE="%s" />
    </BASIC_INFO>
</FILE_INFO>
"""

# A driver carrying both halves `check()` looks for: the copy and the rewrite in
# one function. Written out rather than patched out of the committed driver, so
# a case can fault one line of it without touching the tree.
DRIVER_GOOD = '''\
import getpass
import os
import shutil

import project_owner

PROJECT = "/somewhere/project"


def copy_project_for_export(project_dir, work):
    copy_dir = os.path.join(work, "project-copy")
    shutil.copytree(project_dir, copy_dir)
    rep_dir = os.path.join(copy_dir, "ec.rep")
    project_owner.rewrite_owner(rep_dir, work)
    project_owner.owner_problems(rep_dir, getpass.getuser())
    return copy_dir
'''


def run_check(repo):
    """-> (exit status, everything `check()` printed). Both halves or neither."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        status = gate.check(repo=repo, quiet=True)
    return status, buf.getvalue()


class CommittedTreeTests(unittest.TestCase):
    """The committed tree, through `check()`'s own entry point.

    These hold the property rather than a census: each row is read and each
    driver is looked at by name, and nothing here says how many of either there
    are.
    """

    def test_the_committed_tree_is_clean(self):
        status, printed = run_check(REPO)
        self.assertEqual((status, printed), (0, ""))

    def test_every_named_project_and_driver_is_on_disk(self):
        for rel in gate.PROJECTS + gate.COPY_SITES + gate.NO_COPY_SITE:
            with self.subTest(rel=rel):
                self.assertTrue(os.path.exists(os.path.join(REPO, rel)), rel)

    def test_the_copy_sites_and_no_copy_sites_do_not_overlap(self):
        # The two lists answer different questions about the same driver, so a
        # path in both would be one that both requires a rewrite and reports has
        # none -- a contradiction nothing else would catch.
        self.assertFalse(set(gate.COPY_SITES) & set(gate.NO_COPY_SITE))

    def test_a_committed_project_records_someone(self):
        # Read through the tool's own function, so a project.prp that grew a
        # second OWNER state or became unreadable is caught here rather than by
        # whichever export opens it first.
        for rel in gate.PROJECTS:
            with self.subTest(rel=rel):
                self.assertEqual(gate.project_problems(os.path.join(REPO, rel)),
                                 [])

    def test_the_committed_owner_is_never_asserted_to_be_anyone_in_particular(self):
        # The point of the rewrite is that this repository does not depend on the
        # recorded name, so a check that pinned one value would be a check that
        # goes red when the project is legitimately retaken. What is held is the
        # shape of the state; the value is read and not compared.
        for rel in gate.PROJECTS:
            prp = os.path.join(REPO, rel, "project.prp")
            with self.subTest(rel=rel), open(prp) as handle:
                self.assertIn('NAME="OWNER" TYPE="string" VALUE="',
                              handle.read())


class MirrorTreeTests(unittest.TestCase):
    """`check()` over a tree built to be wrong, one thing at a time.

    A fresh tree per case, or the second case is faulting a file the first one
    left behind and the failure names the wrong cause. An override of None means
    "do not write this file at all", which is a different fault from writing a
    broken one and reaches a different refusal.
    """

    def mirror(self, projects=None, drivers=None):
        """A whole repository shape for `check()` to read. -> its path.

        Every path `check()` reads, so the case is reaching the real reading of a
        driver's source rather than a function called with a string.
        """
        box = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, box, True)
        projects = {} if projects is None else projects
        drivers = {} if drivers is None else drivers
        for rel in gate.PROJECTS:
            rep = os.path.join(box, rel)
            os.makedirs(rep)
            text = projects.get(rel, PRP % "dave")
            if text is not None:
                with open(os.path.join(rep, "project.prp"), "w") as handle:
                    handle.write(text)
        for rel in gate.COPY_SITES:
            self._write_driver(box, rel, drivers.get(rel, DRIVER_GOOD))
        for rel in gate.NO_COPY_SITE:
            self._write_driver(box, rel,
                               "# opens the committed project in place\n")
        return box

    def _write_driver(self, box, rel, source):
        path = os.path.join(box, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if source is None:
            return
        with open(path, "w") as handle:
            handle.write(source)

    def assert_clean(self, box):
        self.assertEqual(run_check(box), (0, ""))

    def assert_flags(self, needle, **overrides):
        status, printed = run_check(self.mirror(**overrides))
        self.assertEqual(status, 1, printed)
        self.assertIn(needle, printed)

    def test_a_whole_mirror_of_correct_files_is_clean(self):
        # The known-good case first, because a guard exercised only on known-bad
        # input cannot tell "clean" from "never ran".
        self.assert_clean(self.mirror())

    def test_a_project_with_no_owner_state_is_reported(self):
        self.assert_flags(
            "carries no OWNER state",
            projects={gate.PROJECTS[0]: (PRP % "dave").replace(
                '        <STATE NAME="OWNER" TYPE="string" VALUE="dave" />\n',
                "")})

    def test_a_project_with_no_prp_at_all_is_reported(self):
        self.assert_flags("is not a .rep directory",
                          projects={gate.PROJECTS[0]: None})

    def test_a_driver_with_no_rewrite_is_reported(self):
        self.assert_flags(
            "no owner rewrite is reachable",
            drivers={gate.COPY_SITES[0]: DRIVER_GOOD.replace(
                "    project_owner.rewrite_owner(rep_dir, work)\n", "")})

    def test_a_driver_that_copies_something_else_is_reported(self):
        # The direction of the argument matters, and this is the case that says
        # so: `shutil.copytree(src, copy_dir)` copies a program's export
        # directory into the tree, and requiring an owner rewrite on it would be
        # requiring a mechanism that copy does not have. Both real drivers make
        # exactly that copy, which is why the check reads the source argument.
        self.assert_flags(
            "copies no project",
            drivers={gate.COPY_SITES[0]: DRIVER_GOOD.replace(
                "shutil.copytree(project_dir, copy_dir)",
                "shutil.copytree(src, copy_dir)")})

    def test_a_driver_that_cannot_be_parsed_is_reported(self):
        self.assert_flags(
            "does not parse",
            drivers={gate.COPY_SITES[0]: DRIVER_GOOD.replace(
                "def copy_project_for_export(project_dir, work):",
                "def copy_project_for_export(project_dir, work)\n")})

    def test_a_driver_that_does_not_exist_is_reported(self):
        # The other way a scan can find nothing: a path that is simply gone.
        # Reported as unreadable rather than passing for a driver with no copy.
        self.assert_flags("does not read",
                          drivers={rel: None for rel in gate.COPY_SITES})

    def test_a_fault_in_the_second_copy_site_is_reported(self):
        # Not the first path: a check that only ever faulted one of the two would
        # pass on a driver the loop below had stopped reading.
        self.assert_flags(
            "no owner rewrite is reachable",
            drivers={gate.COPY_SITES[-1]: DRIVER_GOOD.replace(
                "    project_owner.rewrite_owner(rep_dir, work)\n", "")})


class NamesAProjectTests(unittest.TestCase):
    """Which expressions count as naming a project, asserted on the parse."""

    def _names(self, expr):
        value = next(n.value for n in ast.walk(ast.parse("x = %s" % expr))
                     if isinstance(n, ast.Assign))
        return gate._names_a_project(value)

    def test_a_name_or_a_path_naming_a_project_counts(self):
        for expr in ("PROJECT", "project_dir", "self.project",
                     "os.path.join(work, 'project-copy')"):
            with self.subTest(expr=expr):
                self.assertTrue(self._names(expr))

    def test_a_path_that_is_not_a_project_does_not(self):
        for expr in ("src", "scratch", "out_fn",
                     "os.path.join(OUTDIR, program)",
                     "os.path.join(work, 'out')"):
            with self.subTest(expr=expr):
                self.assertFalse(self._names(expr))


class ReachesRewriteTests(unittest.TestCase):
    """Whether a copy is joined to an owner rewrite in the module's own graph."""

    def _reaches(self, source, func):
        return gate._reaches_rewrite_owner(ast.parse(source), func)

    def test_a_rewrite_in_the_same_function_is_reached(self):
        self.assertTrue(self._reaches(DRIVER_GOOD, "copy_project_for_export"))

    def test_a_rewrite_in_a_helper_the_copy_calls_is_reached(self):
        # Downward: the copy delegates to something that retakes.
        source = '''\
import shutil

import project_owner

def copy_project_for_export(project_dir, work):
    shutil.copytree(project_dir, work)
    retake(work)


def retake(work):
    project_owner.rewrite_owner(work, work)
'''
        self.assertTrue(self._reaches(source, "copy_project_for_export"))

    def test_a_rewrite_at_the_call_site_of_a_copy_helper_is_reached(self):
        # Upward, which is the shape a refactor produces: the copy moves into a
        # helper and the retake stays where the copy was called from. A check
        # that only walked downward would report this correct driver as broken,
        # and the fix a maintainer would reach for is to delete the rewrite.
        source = '''\
import shutil

import project_owner

def copy_project_for_export(project_dir, work):
    rep_dir = make_the_copy(project_dir, work)
    project_owner.rewrite_owner(rep_dir, work)


def make_the_copy(project_dir, work):
    shutil.copytree(project_dir, work)
    return work
'''
        self.assertTrue(self._reaches(source, "make_the_copy"))

    def test_a_module_with_no_rewrite_at_all_is_not_reached(self):
        source = ('import shutil\n'
                  'def copy_project_for_export(project_dir, work):\n'
                  '    shutil.copytree(project_dir, work)\n')
        self.assertFalse(self._reaches(source, "copy_project_for_export"))

    def test_a_rewrite_on_an_unrelated_path_is_not_reached(self):
        # The opposite error: the driver still calls the helper, but not on
        # anything connected to the copy.
        source = '''\
import shutil

import project_owner

def copy_project_for_export(project_dir, work):
    shutil.copytree(project_dir, work)


def somewhere_else():
    project_owner.rewrite_owner("/tmp/other", "/tmp")
'''
        self.assertFalse(self._reaches(source, "copy_project_for_export"))

    def test_a_function_that_is_not_in_the_module_is_not_reached(self):
        # The degenerate input. A checker that cannot find its target must not
        # answer "clean", because clean is what a correct tree reports.
        self.assertFalse(self._reaches(DRIVER_GOOD, "no_such_function"))


class CommittedDriverShapeTests(unittest.TestCase):
    """The real drivers, read for the shapes `check()` reasons about.

    Not a copy of `--check`: this asserts that the functions the check walks are
    there, which a driver rewritten around them would otherwise lose silently --
    the check would go on passing over a driver that no longer copies a project,
    and would say so in a message describing a different fault.
    """

    def _tree(self, rel):
        with open(os.path.join(REPO, rel), encoding="utf-8") as handle:
            return ast.parse(handle.read())

    def test_every_copy_site_copies_a_project(self):
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                self.assertTrue(gate._copies_a_project(self._tree(rel)),
                                "%s copies no project" % rel)

    def test_every_copy_site_reaches_an_owner_rewrite(self):
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                tree = self._tree(rel)
                graph = gate._call_graph(tree)
                for name in gate._copies_a_project(tree):
                    self.assertTrue(
                        gate._reaches_rewrite_owner(tree, name, graph),
                        "%s: %s() copies a project with no owner rewrite on it"
                        % (rel, name))

    def test_every_named_no_copy_site_really_makes_no_copy(self):
        # The named omission is a claim about `decompile_native.py`, and this is
        # what keeps it one: a driver that grew a scratch copy without being
        # moved into `COPY_SITES` is reported here rather than missed.
        for rel in gate.NO_COPY_SITE:
            with self.subTest(rel=rel):
                self.assertEqual(gate._copies_a_project(self._tree(rel)), [])

    def test_each_driver_has_one_copy_function(self):
        # Two copy functions in a driver is not a failure -- `--mode
        # rebuild-project` is a legitimately different path in one of them -- but
        # the one carrying the rewrite is the one `--self-test` has to reach, so
        # the count is worth being able to see even though nothing asserts it as
        # a figure.
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                names = gate._copies_a_project(self._tree(rel))
                self.assertEqual(len(names), len(set(names)), rel)


def _self_test_function(tree):
    return next((n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef)
                 and n.name == "self_test"), None)


class DriverSelfTestsDriveTheCopyPathTests(unittest.TestCase):
    """Each driver's `--self-test` goes through its own copy function.

    This is the whole of #572's "a regression check that fails if the OWNER
    rewrite is dropped". The EC driver used to make its own copy and call
    `rewrite_owner()` on it directly, which proved the helper works and said
    nothing about whether the export path still called it: deleting the rewrite
    from `analyze()` left that self-test green while the default export stopped
    running, which is how the gap stayed open as long as it did. The BIOS
    `--self-test` had no owner assertion at all.
    """

    def _tree(self, rel):
        with open(os.path.join(REPO, rel), encoding="utf-8") as handle:
            return ast.parse(handle.read())

    def _self_test_calls(self, rel):
        body = _self_test_function(self._tree(rel))
        self.assertIsNotNone(body, "%s has no self_test()" % rel)
        return {node.func.id for node in ast.walk(body)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)}

    def test_each_self_test_calls_its_own_copy_function(self):
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                self.assertIn(
                    "copy_project_for_export", self._self_test_calls(rel),
                    "%s --self-test must go through the copy function its export "
                    "path uses, or it proves the helper works and not that the "
                    "call site does" % rel)

    def test_each_copy_function_preflights_inside_itself(self):
        # The preflight's placement is what makes it a check of the call site.
        # Beside the function, a self-test that reached the function would still
        # never see a rewrite deleted from it.
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                fn = next((n for n in ast.walk(self._tree(rel))
                           if isinstance(n, ast.FunctionDef)
                           and n.name == "copy_project_for_export"), None)
                self.assertIsNotNone(fn, rel)
                called = {c.func.id for c in ast.walk(fn)
                          if isinstance(c, ast.Call)
                          and isinstance(c.func, ast.Name)}
                self.assertIn("owner_preflight", called,
                              "%s: the preflight has to run inside "
                              "copy_project_for_export(), or nothing checks the "
                              "rewrite when a real export is about to open it"
                              % rel)

    def test_each_copy_function_passes_its_scratch_root_not_the_repo(self):
        # The scratch-root guard is in `rewrite_owner`'s signature, so what a
        # driver has to get right is passing the work directory as that argument
        # rather than the repository root. A driver that passed REPO would refuse
        # every copy -- loudly, but only at run time, and only on the machine
        # that noticed.
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                fn = next(n for n in ast.walk(self._tree(rel))
                          if isinstance(n, ast.FunctionDef)
                          and n.name == "copy_project_for_export")
                calls = [c for c in ast.walk(fn)
                         if isinstance(c, ast.Call)
                         and isinstance(c.func, ast.Attribute)
                         and c.func.attr == "rewrite_owner"]
                self.assertEqual(len(calls), 1, rel)
                args = [a.id for a in calls[0].args if isinstance(a, ast.Name)]
                self.assertIn("work", args,
                              "%s passes no work directory as the scratch root"
                              % rel)
                self.assertNotIn("REPO", args,
                                 "%s passes REPO as the scratch root, so every "
                                 "copy would be refused" % rel)


class DriverPreflightTests(unittest.TestCase):
    """The preflight each driver ships, driven on a fixture.

    The drivers' own `--self-test` covers their preflight through the driver;
    this is the check that it refuses, run directly so the refusal does not
    depend on which driver calls it or on the committed project being there. A
    preflight exercised only on its passing case cannot tell "checked" from
    "never ran".
    """

    def setUp(self):
        self.box = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.box, True)
        self.rep = os.path.join(self.box, "ec.rep")
        os.makedirs(self.rep)

    def _write(self, owner):
        with open(os.path.join(self.rep, "project.prp"), "w") as handle:
            handle.write(PRP % owner)

    def _preflight(self, rel):
        """The named driver's `owner_preflight`, imported fresh each call.

        The import is repeated per call on purpose: `build_ec_decompile` and
        `bios_extract` are both import-safe and both name a module-level
        `PROJECT`, so a cached import is whichever one a previous case loaded.
        """
        name = os.path.splitext(os.path.basename(rel))[0]
        for cached in (name,):
            sys.modules.pop(cached, None)
        sys.path.insert(0, os.path.join(REPO, os.path.dirname(rel)))
        try:
            module = __import__(name)
        finally:
            sys.path.pop(0)
        return module.owner_preflight(self.rep)

    def test_a_copy_owned_by_the_running_user_passes(self):
        self._write(getpass.getuser())
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                self.assertIsNone(self._preflight(rel))

    def test_a_copy_owned_by_someone_else_is_refused(self):
        self._write("dave")
        for rel in gate.COPY_SITES:
            with self.subTest(rel=rel):
                with self.assertRaises(SystemExit):
                    self._preflight(rel)

    def test_the_refusal_names_the_project_and_the_fix_on_the_terminal(self):
        # The defect was that the only account of this was an abort inside an
        # analyzeHeadless log, minutes downstream and in another file. The
        # message has to carry the project and the rewrite where a reader sees it
        # or the preflight has not fixed the thing it was added for.
        self._write("dave")
        with self.assertRaises(SystemExit) as caught:
            self._preflight(gate.COPY_SITES[0])
        message = str(caught.exception)
        for want in ("ec.rep", "NotOwnerException", "rewrite_owner",
                     "copy_project_for_export", self.rep):
            with self.subTest(want=want):
                self.assertIn(want, message)


if __name__ == "__main__":
    unittest.main()