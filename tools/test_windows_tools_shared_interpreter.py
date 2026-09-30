#!/usr/bin/env python3
r"""The `windows/tools` suites in one interpreter: the property, asserted.

`tools/run-tests.sh` gives every suite its own interpreter. That was load-bearing
once: each `windows/tools` suite used to install a fake `ecrw` into `sys.modules`
with `setdefault`, and the fakes were not the same shape, so whichever suite
imported first won the name and the others died on `from ecrw import ...`.
`docs/findings.md` §16 has the reproduction. There is now one shape
(`windows/tools/ecrw_fake.py`) and one way to install it, so the loop is
insurance rather than the thing keeping a red build away.

Insurance is the weak reading, though -- nothing would notice it stop being
true. This asserts it instead, on both sides of the tree. Live: the shared run
really does load every suite in the directory and fails nothing the per-file
loop does not (`CollectionTests`), and a rename that reverses the sort order
changes nothing (`OrderingTests`). And over the sources, so a suite that
follows the pattern passes without anyone editing a list of them: the install
shape (`InstallShapeTests`) and the names the fake has to export
(`FakeSurfaceTests`). `NegativeControlTests` is what stops those last two
passing on a directory that has simply stopped containing the word.

**It lives in `tools/`, not in the directory it runs, and that placement is
load-bearing too**: a suite inside `windows/tools` would be collected by the
discovery below and would spawn a second copy of itself, once per rename.

**What "no new red" means here, and why it is not a plain `assertEqual(0, rc)`.**
One shared interpreter is asserted to be *no worse than one interpreter per
file*, not to be green outright, and the difference matters on this tree.
`test_gpu_block_watch.py` currently fails four cases reading `registers.yaml`
and its own door procedure, on its own and identically under both runners -- that
is a data-drift failure of another suite, in no way a consequence of anything
about `ecrw`. Asserting the whole run green would either make this suite red for
someone else's breakage, or -- the tempting fix -- teach it to ignore failures,
which is the failure mode a check is supposed to have. So `CollectionTests`
compares the shared run against the per-file baseline instead: any problem it
reports has to be one that suite already reports alone. A shared-interpreter-only
failure fails this suite and names the module, and that comparison is not
vacuous -- it is exactly what the last one-interpreter run tripped over, in a
`test_charge_target_test` error that a suite-local `EcError` lookalike let escape
`main()` under one interpreter and that no per-file run has ever seen.

Nothing here opens an EC, reads a register back, or touches Windows. Every case
is either a subprocess running the committed suites offline, or a read of their
sources; `docs/findings/ecrw-fake-one-shape.md` is the write-up.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
WINDOWS_TOOLS = REPO / 'windows' / 'tools'
RUN_TESTS = HERE / 'run-tests.sh'

# The suites under test, read from the tree rather than listed here. A list of
# paths would be a census every landing suite has to edit, which is the same
# trap `run-tests.sh`'s totals and `tools/README.md`'s old lead were in; the
# relation below is meant to hold for whatever suites exist.
SUITE_NAMES = sorted(p.stem for p in WINDOWS_TOOLS.glob('test_*.py'))

# What unittest prints when a module it could not import is collected: it
# synthesises a single `_FailedTest` and says so on the next line. Both spellings
# are matched because the first is the test id and the second is the message,
# and a check that only watched the id would miss a unittest that stops
# printing it.
LOADING_FAILURES = ('_FailedTest', 'Failed to import test module')
RUN_SUMMARY = re.compile(r'^Ran (\d+) tests?\b', re.M)
RESULT_LINE = re.compile(r'^(?:ERROR|FAIL): \S+ \(([^)]+)\)', re.M)
# `-v` prints one line per test as `name (module.Class.name)`, so the leading
# dotted path before the first dot is the module discovery imported it under.
COLLECTED = re.compile(r'^\S+ \((test_[A-Za-z0-9_]+)\.', re.M)

# The id unittest gives a module it could not import. Its tail is the suite's
# real name and its head is unittest's own, so reading the head -- which is what
# splitting on the first dot would do -- sends the per-file baseline looking for
# a suite called `unittest`, finds no such file, and reports a passing suite as
# one that does not run alone.
FAILED_TEST = 'unittest.loader._FailedTest.'

# The scratch-mirror case is the only one that can reorder anything, and
# renaming to a fixed prefix is the whole mechanism -- see `OrderingTests`.
FIRST = 'aaa_'
LAST = 'zzz_'

# The three suites that used to `setdefault` their own shape. They are what the
# mirror renames to demonstrate that the sort order no longer decides anything;
# the naming is not an assertion that they exist (that is `InstallShapeTests`),
# only that whatever sorts wrongly cannot matter.
RENAMED = ('test_ec_validate.py', 'test_system_id_probe.py',
           'test_charge_target_test.py')


def discover(directory, cwd, pattern='test_*.py', verbose=True):
    """Run `unittest discover` over `directory` and return (rc, stdout+stderr).

    `cwd` is passed rather than inherited because several of the suites resolve
    the repository by walking up from `__file__`, and a mirror has to be run
    from the root it actually has. Verbose because the per-test lines are the
    only record of which modules loaded, and "one interpreter imported every
    suite" is a claim about exactly that.
    """
    argv = [sys.executable, '-m', 'unittest', 'discover', '-s', str(directory)]
    if verbose:
        argv.append('-v')
    if pattern != 'test_*.py':
        argv += ['-p', pattern]
    done = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr


def ran_count(output):
    """The `Ran N tests` figure, or None when the run never printed one."""
    found = RUN_SUMMARY.findall(output)
    return int(found[-1]) if found else None


def results(output):
    """The `module.Class.case` id of every error and failure, as a set."""
    return set(RESULT_LINE.findall(output))


def suite_of(test_id):
    """The `test_*` suite a result id belongs to, loaded or not."""
    if test_id.startswith(FAILED_TEST):
        return test_id[len(FAILED_TEST):]
    return test_id.split('.')[0]


def shared_fake():
    """`windows/tools/ecrw_fake.py`, imported without leaving it on the path.

    Importing it installs nothing -- `install()` is a separate call -- so this
    is safe to do in a suite that goes on to run the directory's own suites in
    subprocesses.
    """
    sys.path.insert(0, str(WINDOWS_TOOLS))
    try:
        import ecrw_fake
    finally:
        sys.path.remove(str(WINDOWS_TOOLS))
    return ecrw_fake


class CollectionTests(unittest.TestCase):
    """One interpreter, every suite, and no failure the per-file loop lacks."""

    # Run once for the class: the shared run costs what the whole directory
    # costs, and three cases reading it off three processes would triple that
    # for one answer.
    @classmethod
    def setUpClass(cls):
        cls.rc, cls.out = discover(WINDOWS_TOOLS, REPO)

    def test_the_shared_run_loads_every_suite_in_the_directory(self):
        # unittest synthesises a single `_FailedTest` for a module it could not
        # import, so a suite that died on `from ecrw import EcError` shows up
        # here as one line about a module that does not exist. Asserting on the
        # text rather than on the exit status is also what makes the failure
        # legible: a red run that only says "non-zero" is the runner's own
        # complaint, and this suite has to say which module.
        for phrase in LOADING_FAILURES:
            self.assertNotIn(phrase, self.out,
                             f"windows/tools discovery: {phrase} -- a suite in "
                             "this directory did not import:\n" + self.out)
        loaded = set(COLLECTED.findall(self.out))
        missing = set(SUITE_NAMES) - loaded
        self.assertFalse(missing, f"never imported in one interpreter: {missing}")

    def test_the_shared_run_collected_something(self):
        # A discovery that matched no file exits 0 and prints nothing, which
        # every other case here would read as success: the §14b vacuous pass one
        # level up, the same defect `run-tests.sh` guards its own empty glob
        # against. The figure is floored at one and never compared, so a suite
        # that adds a test does not turn this red.
        count = ran_count(self.out)
        self.assertIsNotNone(count, self.out)
        self.assertGreater(count, 0, self.out)

    def test_one_interpreter_fails_nothing_the_per_file_runner_does_not(self):
        # The claim is "no worse than one interpreter per file", not "green",
        # and the module docstring says why the two are not the same claim on
        # this tree. Anything here that the per-file run also reports is that
        # suite's own problem; anything it does not is this property's, and the
        # baseline is read from the tree rather than pinned so it moves with it.
        shared = results(self.out)
        self.assertFalse(
            shared - self.per_file_problems(shared),
            "fail under one shared interpreter but pass under the per-file "
            "loop, which is the ordering accident this suite exists to hold "
            "down:\n" + self.out)

    def per_file_problems(self, shared):
        """Every problem a module reports when run in its own interpreter.

        Only the implicated modules are re-run, and only when the shared run
        found something: on a tree where the shared run is clean this costs one
        subprocess, and the cost is spent only when there is a question to ask.
        """
        known = set()
        for module in sorted({suite_of(m) for m in shared}):
            rc, out = discover(WINDOWS_TOOLS, REPO, pattern=module + '.py')
            known |= results(out)
            self.assertNotEqual(rc, 0,
                                f"{module} was reported by the shared run and "
                                f"does not run alone:\n{out}")
        return known


class OrderingTests(unittest.TestCase):
    """A rename that reverses the sort order changes nothing. Live, on a mirror.

    The suites are copied rather than moved, and everything else in the
    repository is symlinked in beside them: most of them resolve the repository
    by walking up from `__file__` and then open committed files, so a bare copy
    of the directory fails on missing paths and proves nothing about ordering.
    Symlinking *every* entry rather than the handful this suite can enumerate is
    what keeps that honest -- a suite that resolves a path nobody thought of has
    to fail the way it would in the tree, not on a directory this file failed to
    guess. The mirror is resolved before use, because
    `test_system_id_probe.py` calls `Path(__file__).resolve()` and a
    `TemporaryDirectory` under a symlinked `/tmp` would hand it back a path
    outside the root it just built.

    Two renames are the honest bound of what a scratch copy can demonstrate --
    first and last are the extremes, and nothing between them is claimed. They
    are also the two directions that were broken.
    """

    def test_the_result_does_not_depend_on_the_sort_order(self):
        first, last = self.orders()
        for label, run in (('first', first), ('last', last)):
            self.assertNotIn('_FailedTest', run['output'],
                             f"{label} order:\n" + run['output'])
        self.assertFalse(
            first['results'] - last['results'],
            'the suites that sort first fail and the same suites sorted last '
            'do not, so the order still decides the outcome:\n'
            + first['output'])
        self.assertFalse(
            last['results'] - first['results'],
            'the suites that sort last fail and the same suites sorted first '
            'do not:\n' + last['output'])

    def orders(self):
        """The problems and the raw output of each of the two mirror orders.

        The two are compared to each other rather than to an expected value,
        because the tree is not green and they have to be equal to each other
        for that to mean anything: a failure both orders agree on is that
        suite's own problem, not an ordering accident.

        The mirror's prefix is stripped back out of each id before the
        comparison, so the question is which suite failed and not what this
        file happened to call it in this mirror -- otherwise a suite that
        cannot be imported at all reports as two different suites, one per
        order, and the comparison reports a difference in a cause both runs
        share.
        """
        answers = []
        for prefix in (FIRST, LAST):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve() / 'root'
                _, out = discover(self.mirror(root, prefix), root)
            answers.append({'results': {i.replace(prefix, '')
                                       for i in results(out)},
                            'output': out})
        return answers

    def mirror(self, root, prefix):
        """A scratch root whose `windows/tools` is the real one, renamed.

        `__pycache__` is pruned rather than copied: a renamed module and its
        original share a stem in the cache directory's namespace, and the copy
        would let one answer be served by the other's bytecode.
        """
        tools = root / 'windows' / 'tools'
        shutil.copytree(WINDOWS_TOOLS, tools,
                        ignore=shutil.ignore_patterns('__pycache__'))
        # `.git` and `.claude` are the two entries `run-tests.sh` and the
        # README table prune for the same reason: `.claude/worktrees/` holds
        # whole second checkouts, which would put suites nobody committed into
        # this run's answer.
        self.link(REPO, root, skip={'windows', '.git', '.claude'})
        self.link(REPO / 'windows', root / 'windows', skip={'tools'})
        for name in RENAMED:
            (tools / name).rename(tools / name.replace('test_', f'test_{prefix}'))
        return tools

    def link(self, source, target, skip):
        """Symlink every entry of `source` into `target` but the ones skipped."""
        target.mkdir(parents=True, exist_ok=True)
        for entry in sorted(source.iterdir()):
            if entry.name in skip:
                continue
            os.symlink(entry, target / entry.name)


class InstallShapeTests(unittest.TestCase):
    """The relation, read from the sources, over whatever suites exist.

    A census would be the same check with a worse failure mode: it names the
    suites it knows and goes red the moment a fourth shape appears, which is
    the moment the check has something to say. This holds the property instead,
    so a suite that follows the pattern passes without anyone editing a list.
    """

    def sources(self):
        for name in SUITE_NAMES:
            yield name, (WINDOWS_TOOLS / f'{name}.py').read_text()

    def test_no_suite_reaches_for_sys_modules_setdefault(self):
        # The whole accident in one call: `setdefault` is a race whose winner
        # is decided by import order, and the fix was assignment by a shared
        # installer. A suite reaching for it has reintroduced a shape that is
        # safe only by sort order.
        offenders = {name: [n for n, line in enumerate(text.splitlines(), 1)
                            if 'sys.modules.setdefault' in line]
                     for name, text in self.sources()}
        offenders = {name: lines for name, lines in offenders.items() if lines}
        self.assertFalse(offenders, f"sys.modules.setdefault in {offenders}")

    def test_a_suite_writing_the_ecrw_name_is_the_one_that_may(self):
        # `test_ecrw.py` borrows the name to put the real module in front of a
        # fake `ctypes.WinDLL` and puts back whatever was there in a `finally`.
        # Any other suite writing it is building a shape of its own again. The
        # other file that writes the name is `ecrw_fake.py`, the fixture rather
        # than a suite, and `sources()` reads suites only.
        allowed = {'test_ecrw'}
        writers = set()
        for name, text in self.sources():
            for line in text.splitlines():
                if re.search(r"""sys\.modules\[["']ecrw["']\]\s*=""", line):
                    writers.add(name)
        self.assertLessEqual(writers, allowed,
                             f"writing sys.modules['ecrw'] outside {allowed}: "
                             f"{writers - allowed}")

    def test_something_in_the_directory_still_installs_the_fake(self):
        # So the two cases above cannot pass on a tree where the fake stopped
        # being installed altogether: `writers` empty and `setdefault` absent is
        # also what a directory in which every suite has stopped importing the
        # tool at all looks like.
        installers = {name for name, text in self.sources()
                      if 'ecrw_fake.install()' in text}
        self.assertTrue(installers, "no suite in windows/tools installs the fake")

    def test_the_installer_replaces_whatever_was_under_the_name(self):
        # Called rather than read, and deliberately: `ecrw_fake.py` explains at
        # length why it assigns instead of `setdefault`, so a text search for
        # either word would match its own explanation. A sentinel left under
        # the name is the property, and it is the one thing every suite in the
        # directory now depends on.
        sentinel = types.ModuleType('ecrw')
        had = sys.modules.get('ecrw', None)
        sys.modules['ecrw'] = sentinel
        try:
            installed = shared_fake().install()
        finally:
            if had is None:
                del sys.modules['ecrw']
            else:
                sys.modules['ecrw'] = had
        self.assertIs(sys.modules.get('ecrw', None), had)
        self.assertIsNot(installed, sentinel)
        # The module's own name is what `from ecrw import ...` resolves to, so
        # a module installed under any other name would leave the tools binding
        # whatever was already there -- which is the accident in its quietest
        # form, and the one no assertion above would catch.
        self.assertEqual(installed.__name__, 'ecrw')


class FakeSurfaceTests(unittest.TestCase):
    """Every name a tool binds from `ecrw` is one the fake exports.

    The set is derived from the tools' own import lines rather than listed, so
    a tool that starts importing a fourth name is covered by this case rather
    than by whoever remembers to extend a list -- which is what makes "one
    shape is enough" a fact about the tree instead of an intention.
    """

    # The tools, as opposed to the suites: a `test_*.py` importing `ecrw`
    # directly would be a second shape, which `InstallShapeTests` covers, and
    # `ecrw.py` itself is the real module and `ecrw_fake.py` the fixture.
    IMPORT_FROM = re.compile(r'^from ecrw import (.+)$', re.M)

    def wanted(self):
        names = set()
        for path in sorted(WINDOWS_TOOLS.glob('*.py')):
            if path.name in ('ecrw.py', 'ecrw_fake.py'):
                continue
            for line in self.IMPORT_FROM.findall(path.read_text()):
                for name in line.strip('()').split(','):
                    name = name.split(' as ')[0].strip()
                    if name.isidentifier():
                        names.add(name)
        return names

    def test_the_set_of_names_the_tools_bind_is_not_empty(self):
        # The parse finding nothing would make the case below compare an empty
        # expectation against an empty answer and pass, which is the shape the
        # README-table suite spends four cases pinning on its own parser.
        self.assertTrue(self.wanted(), "no `from ecrw import` found in the tools")

    def test_the_fake_exports_every_name_a_tool_binds(self):
        ecrw_fake = shared_fake()
        missing = {name for name in self.wanted()
                   if not hasattr(ecrw_fake, name)}
        self.assertFalse(missing, f"ecrw_fake.py does not export {missing}")


class NegativeControlTests(unittest.TestCase):
    """The same two suites the landmine was, which still have to fail together.

    Without this, `InstallShapeTests` is satisfied by any directory that has
    stopped containing the word `setdefault` -- by a tool that has been deleted,
    by a rename, by a suite that quietly stopped importing `ecrw`. The control
    reproduces the original shape in a scratch directory and asserts the shared
    run is *red*, so the green above is a property of these suites rather than
    of the check.
    """

    EC_ONLY = (
        'import sys, types\n'
        'import unittest\n'
        '\n'
        'fake = types.ModuleType("ecrw")\n'
        'fake.Ec = object\n'
        'sys.modules.setdefault("ecrw", fake)\n'
        '\n'
        '\n'
        'class T(unittest.TestCase):\n'
        '    def test_the_tool_imports_what_the_fake_exports(self):\n'
        '        from ecrw import Ec, EcError  # noqa: F401\n'
    )
    NEEDS_ECERROR = (
        'import unittest\n'
        '\n'
        '\n'
        'class T(unittest.TestCase):\n'
        '    def test_the_second_suites_import_resolves(self):\n'
        '        from ecrw import EcError  # noqa: F401\n'
    )

    def test_the_control_run_is_red_with_the_import_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / 'test_a_ec_only.py').write_text(self.EC_ONLY)
            (root / 'test_b_needs_ecerror.py').write_text(self.NEEDS_ECERROR)
            rc, out = discover(root, root)
        self.assertNotEqual(rc, 0,
                            "an Ec-only fake setdefault-ing next to a suite "
                            "that imports EcError went green, so nothing above "
                            "is asserting anything:\n" + out)
        self.assertIn('cannot import name', out, out)


class RunnerCommentTests(unittest.TestCase):
    """The loop's comment still points at the suite that holds the property.

    A floor, not a proof: it says the next reader of `run-tests.sh` is told
    where the claim is checked, and it goes red if the claim's only pointer is
    dropped. It cannot tell whether what the comment says is true, and it is
    not trying to -- `OrderingTests` and `CollectionTests` are what check that.
    """
    POINTER = 'test_windows_tools_shared_interpreter.py'

    def test_the_per_file_loop_comments_where_the_property_is_asserted(self):
        script = RUN_TESTS.read_text()
        self.assertIn(self.POINTER, script,
                      f"{RUN_TESTS.name} no longer names this suite, so the "
                      "reason the loop is not collapsed reads as a warning "
                      "with nothing behind it")


if __name__ == '__main__':
    unittest.main()
