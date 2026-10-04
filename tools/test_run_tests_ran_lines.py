#!/usr/bin/env python3
r"""`run-tests.sh`'s handling of a suite that runs other suites, asserted.

`unittest` prints one `Ran N tests` line per *run*. A suite that runs another
suite with `subprocess` prints that run's summary on the same stream, so its
transcript carries more than one line -- `ec/tools/test_pd_image_census.py`
carries three, because it calls `pd_image_census.self_test()` twice over two
throwaway suites it writes itself. Which of those lines is the suite's own run
is not a property of the transcript: this suite is last because the suites it
drives run inside its own cases, and a suite that drove them afterwards would
be first, and the two outputs would be identical.

The runner therefore *records* the choice per suite (`ran_line_for`), names the
suite in its output on every run, and refuses a multi-line suite it has no
record for rather than counting one of the lines silently. These cases hold
those three things:

- a plain suite's total is its own count, unchanged (`PlainSuiteTests`) --
  the negative control for every case below, since a rule that fired on every
  suite would pass the refusal and break this;
- a recorded nesting suite is counted by its own run, not by the sum, and is
  named (`RecordedNestingTests`), against a scratch fixture that nests the way
  the real one does rather than by asserting a number off the real suite;
- an unrecorded one is detected (`UnrecordedNestingTests`), paired with the
  plain case asserted green in the same run;
- every path in the record is a suite the runner finds (`RecordTests`) -- a
  *relation*, not a census: adding a suite moves nothing here, and a record
  naming a suite that has gone is caught;
- and the real tree's nesting suite, on its own (`RealSuiteTests`), so the
  record is checked against the suite it was written for rather than only
  against a fixture shaped like it.

Every run here is a subprocess running committed code. The scratch trees open
no file; the real suite reads the committed firmware image, which is a file
read and not an observation of a machine. No EC is opened, no register is read
back, and nothing here touches Windows. The write-up is
`docs/findings/run-tests-ran-lines.md`.
"""
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
RUN_TESTS = HERE / 'run-tests.sh'

# The totals figure on the line the runner ends on, read by its figure rather
# than by the line's whole shape: the clauses differ between the two ways a
# run can end (`All N suite(s) passed, M tests.` and
# `N suite(s) run, M tests; ...`), and a regex written to both would break the
# moment a third clause is added -- which is the sort of brittleness the
# runner's own counting is not supposed to have. Every figure below is read
# off the run under test rather than pinned, so a suite that gains a case moves
# none of them.
TESTS_FIGURE = re.compile(r'(\d+) tests\b')
# unittest's own summary line, read off a transcript of a nesting suite.
NESTED = re.compile(r'^Ran (\d+) tests?\b', re.M)
PER_SUITE = re.compile(r'^(?P<path>\S+\.py): (?P<body>.*)$', re.M)

# The suites under `tools/`, by the runner's own `find` rule. Copied rather
# than shared with `test_readme_suite_table.py` because importing another
# suite's discovery would make this one green or red with that one's, and the
# two are about different things: this is about what `find` in `run-tests.sh`
# sees, not about the README.
PRUNED = ('.git', '.claude', 'vendor')

# A throwaway suite that nests the way `test_pd_image_census.py` does: it runs
# two one-case suites by `subprocess.call`, so their summaries reach the same
# stream. Two own cases of its own, so the outer count (2) is distinguishable
# from the sum of all three lines (4) -- the whole point of the property. The
# red one is what makes the fixture honest: a nesting suite whose children all
# pass is a suite that would also pass if it ran nothing.
NESTING = '''\
"""A scratch suite that runs two throwaway suites, so its transcript has three."""

import os
import subprocess
import sys
import tempfile
import unittest


class Nesting(unittest.TestCase):
    def test_it_runs_two_throwaway_suites(self):
        with tempfile.TemporaryDirectory() as d:
            for name, body in (("green.py", "self.assertTrue(True)"),
                               ("red.py", "self.assertTrue(False)")):
                path = os.path.join(d, name)
                with open(path, "w") as f:
                    f.write("import unittest\\n"
                            "class T(unittest.TestCase):\\n"
                            "    def test_x(self):\\n"
                            "        %s\\n"
                            "if __name__ == '__main__':\\n"
                            "    unittest.main()\\n" % body)
                subprocess.call([sys.executable, path])

    def test_a_second_case_of_its_own(self):
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
'''

PLAIN = '''\
"""A scratch suite that runs nothing, so its transcript has one summary line."""

import unittest


class Plain(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)

    def test_b(self):
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
'''


def run_runner(root, *dirs):
    """(rc, stdout, stderr) of `run-tests.sh` run against `root` as the repo.

    The committed script is *copied* into `root/tools/` rather than invoked
    from this repository. `run-tests.sh` resolves its own directory and `cd`s
    to its parent, so a copy at `<root>/tools/` makes `<root>` the tree it runs
    -- which is what lets a scratch suite be named by the same repo-relative
    path the record is keyed on. Invoking the committed script with an
    absolute scratch path instead would print `/tmp/.../test_x.py` as the
    suite's name, and the record would never match it: the cases below would
    be testing a lookup that cannot succeed.

    The file is the committed one, byte for byte, so what runs is the script
    and not a copy of it with the cases edited -- `RecordTests` reads the
    record out of this same file.
    """
    tools = root / 'tools'
    if not (tools / RUN_TESTS.name).exists():
        tools.mkdir(parents=True, exist_ok=True)
        shutil.copy(RUN_TESTS, tools / RUN_TESTS.name)
    done = subprocess.run(['bash', str(tools / RUN_TESTS.name), *dirs],
                          cwd=str(root), capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr


def totals_of(stdout):
    """The test figure from the runner's last line, or None if it has none.

    The last *non-blank* line, which is the one both endings put their figure
    on. Reading it by position rather than by shape is what keeps a run that
    ends with a clause this file has never seen from reading as no figure at
    all -- a parse that finds nothing would make the assertions below compare
    `None` against a count and fail for a reason that is not the property.
    """
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        return None
    found = TESTS_FIGURE.search(lines[-1])
    return int(found.group(1)) if found else None


def suite_lines(stdout):
    """The per-suite line for each path the runner reported, in order."""
    return {m.group('path'): m.group('body')
            for m in PER_SUITE.finditer(stdout)}


def scratch(files):
    """A temp directory holding `files` as {name: source}, as a context manager.

    A scratch tree rather than a committed fixture, so the suite that nests has
    somewhere real to write the throwaway children its mechanism writes -- that
    is the thing under test, and a fixture without it would not nest at all.

    `mkdtemp` rather than `TemporaryDirectory` because the runner resolves its
    own directory and `cd`s to its parent, so the tree has to exist before the
    subprocess starts; the cleanup is the context manager's own `__exit__`.
    """
    class Scratch:
        def __enter__(self):
            self.root = Path(tempfile.mkdtemp()).resolve()
            for name, source in files.items():
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding='utf-8')
            return self.root

        def __exit__(self, *exc):
            shutil.rmtree(self.root, ignore_errors=True)
            return False
    return Scratch()


class PlainSuiteTests(unittest.TestCase):
    """A suite that runs nothing is counted by its own run, as before."""

    def test_the_total_is_the_suite_s_own_count(self):
        with scratch({'test_plain.py': PLAIN}) as root:
            rc, out, err = run_runner(root)
        self.assertEqual(rc, 0, f"plain suite did not pass:\n{out}\n{err}")
        self.assertEqual(totals_of(out), 2, out)

    def test_a_suite_that_needed_no_decision_is_not_told_it_did(self):
        # The half that keeps the record from becoming noise. A runner that
        # annotated every suite would satisfy every other case here and turn
        # the one line a reader reads for an ordinary suite into a wall of
        # bookkeeping.
        with scratch({'test_plain.py': PLAIN}) as root:
            _, out, _ = run_runner(root)
        self.assertNotIn('summary lines', out, out)


class RecordedNestingTests(unittest.TestCase):
    """A nesting suite with a record is counted by its own run, and named."""

    def setUp(self):
        # The record is `ran_line_for` in the committed script, keyed on the
        # path the runner prints. The fixture is written to that same path in
        # a scratch tree, so the case exercises the committed record rather
        # than a copy of it -- a record tested by a fixture nobody edited is a
        # record tested by itself.
        self.recorded = Path('ec/tools/test_pd_image_census.py')

    def test_the_total_is_the_outer_count_and_not_the_sum_of_the_lines(self):
        with scratch({str(self.recorded): NESTING}) as root:
            rc, out, err = run_runner(root)
        self.assertEqual(rc, 0, f"recorded nesting suite did not pass:\n{out}\n{err}")
        # Asserted as a relation between two readings of the same run, not as
        # a number: the total must be the outer run's own count and must not be
        # the sum, which is the failure this is about. The suite line carries
        # the figure too, so the two can be compared without a constant.
        body = suite_lines(out)[self.recorded.as_posix()]
        counted = int(re.match(r'(\d+) tests', body).group(1))
        self.assertEqual(totals_of(out), counted, out)
        self.assertNotEqual(counted, 4,
                            'the fixture nests two one-case suites inside two '
                            'of its own, so its own count is 2 and the sum of '
                            'all three summary lines is 4; a total of 4 means '
                            'the runner summed them')

    def test_the_suite_is_named_with_the_number_of_lines_and_the_choice(self):
        # The "invisible" half of the property. A total a reader cannot check
        # is the defect, so the line has to say how many summary lines the
        # suite carried and which one was counted -- unconditionally, on every
        # run, which is what `RecordTests` holds separately.
        with scratch({str(self.recorded): NESTING}) as root:
            _, out, _ = run_runner(root)
        body = suite_lines(out)[self.recorded.as_posix()]
        self.assertIn('3 summary lines', body, out)
        self.assertIn('last', body, out)


class UnrecordedNestingTests(unittest.TestCase):
    """A nesting suite with no record is refused, not silently summed."""

    def setUp(self):
        # A path `ran_line_for` does not carry, in the same directory shape as
        # the recorded one, so the only thing separating the two runs is the
        # record. That is what makes the pair the property: the recorded case
        # above passes and this one fails on the same fixture.
        self.unrecorded = Path('ec/tools/test_not_recorded.py')

    def run_both(self):
        """The plain suite and the unrecorded one in one run, so one being
        green cannot be the other being right by accident."""
        with scratch({'test_plain.py': PLAIN,
                      str(self.unrecorded): NESTING}) as root:
            rc, out, err = run_runner(root)
            return rc, out, err, self.unrecorded.as_posix()

    def test_the_run_does_not_pass(self):
        rc, out, err, _ = self.run_both()
        self.assertNotEqual(rc, 0,
                            'a suite whose transcript carried several summary '
                            "lines and no recorded choice passed:\n" + out)

    def test_the_message_names_the_offending_path_and_the_step(self):
        _, _, err, path = self.run_both()
        self.assertIn(path, err)
        self.assertIn('ran_line_for', err,
                      'the refusal has to name the one step that resolves it, '
                      'or a reader is left with a complaint and no way to act '
                      f'on it:\n{err}')

    def test_it_is_not_reported_as_a_failing_suite(self):
        # A shape defect is not a red suite. Reporting it in the clause that
        # means "one or more FAILED" would put a suite that never ran a
        # failing case into the red set, and every figure read off that line
        # after it.
        _, out, _, path = self.run_both()
        self.assertIn(f'{path}:', out, out)
        # The suite passed -- it is named as NOT counted, not as FAILED -- so
        # the word appearing anywhere in the output at all is the defect.
        self.assertNotIn('FAILED', out, out)

    def test_the_plain_suite_in_the_same_run_is_still_counted(self):
        # Without this the refusal could be passing by refusing everything.
        _, out, _, _ = self.run_both()
        self.assertEqual(totals_of(out), 2, out)
        self.assertIn('test_plain.py: 2 tests, passed', out, out)

    def test_an_answer_the_loop_cannot_read_is_refused_like_a_missing_one(self):
        # A record edited to name something the loop does not recognise is not
        # a count of zero: it is a decision nobody can act on, and falling
        # through to "count nothing" quietly would make it indistinguishable in
        # the output from a suite that was never looked at.
        script = RUN_TESTS.read_text(encoding='utf-8')
        broken = script.replace("printf 'last\\n' ;;", "printf 'middle\\n' ;;")
        self.assertNotEqual(script, broken,
                            'ran_line_for no longer prints a recognisable '
                            "answer, so this case cannot be built")
        with scratch({'test_plain.py': PLAIN,
                      str(self.unrecorded): NESTING}) as root:
            (root / 'tools').mkdir(parents=True, exist_ok=True)
            (root / 'tools' / RUN_TESTS.name).write_text(broken, encoding='utf-8')
            rc, out, err = run_runner(root)
        self.assertNotEqual(rc, 0, out)
        self.assertIn(self.unrecorded.as_posix(), err)


class RecordTests(unittest.TestCase):
    """The record and the tree agree, read from the script and the finder."""

    @classmethod
    def setUpClass(cls):
        cls.script = RUN_TESTS.read_text(encoding='utf-8')

    def recorded_paths(self):
        """Every path `ran_line_for` names, out of the script's own text.

        Read rather than kept here on purpose: a list in this file is a second
        copy of the decision, and a copy is what goes stale. Parsing the case
        arms also means a record added to the script is covered here the
        moment it lands, with nothing in this file edited.
        """
        block = self.script.split('ran_line_for() {', 1)[-1].split('\n}', 1)[0]
        return re.findall(r'^\s{4}([^\s*][^\s)]*\.py)\)$', block, re.M)

    def test_the_parse_finds_the_record(self):
        # The §14b shape one level down: an empty parse matches an empty
        # assertion, so a regex that stopped matching would make every case
        # below pass vacuously.
        self.assertTrue(self.recorded_paths(),
                        'no case arms read out of ran_line_for() in '
                        f'{RUN_TESTS.name}; the parse, not the record, is what '
                        'has stopped working')

    def test_every_recorded_path_is_a_suite_the_runner_finds(self):
        # One direction, and deliberately not the other. Every discovered
        # suite being recorded would make adding an ordinary suite an edit
        # here, which is the trap the table exists to avoid; the other
        # direction is what a stale record looks like, and it is the one that
        # makes the runner refuse a suite that no longer exists.
        found = {p.relative_to(REPO).as_posix()
                 for p in REPO.rglob('test_*.py')
                 if p.relative_to(REPO).parts[0] not in PRUNED}
        recorded = set(self.recorded_paths())
        self.assertFalse(recorded - found,
                         f'ran_line_for() records suite(s) `find` does not '
                         f'find: {sorted(recorded - found)}')

    def test_a_recorded_path_is_named_the_way_the_runner_names_it(self):
        # The record is matched against `${path#./}`, so a path written with a
        # leading `./` would never match and the suite would be refused on
        # every run. Cheap to check here and invisible until someone writes it.
        for path in self.recorded_paths():
            self.assertFalse(path.startswith(('./', '/')),
                             f'recorded path {path!r} is not relative to the '
                             'repository root the way `shown` is')


class RealSuiteTests(unittest.TestCase):
    """The real tree's nesting suite, run on its own through the runner.

    Everything above runs a fixture shaped like `ec/tools/test_pd_image_census.py`.
    This runs the suite itself, so the record is checked against the thing it
    was written for -- and the figure is read off the run, not asserted, so
    adding a case to that suite does not turn this red.

    A real run of committed code: it reads the committed firmware image as a
    file and opens no EC. The path is a file rather than a directory, and
    `find <file> -name 'test_*.py'` yields that one file, so this cannot
    recurse into the repository.
    """

    PATH = 'ec/tools/test_pd_image_census.py'

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.out, cls.err = run_runner(REPO, cls.PATH)

    def test_it_passes_and_the_record_counts_it(self):
        self.assertEqual(self.rc, 0, self.out + self.err)
        body = suite_lines(self.out)[self.PATH]
        counted = int(re.match(r'(\d+) tests', body).group(1))
        # Its own run, and *not* the sum of its own and the two it drives. The
        # second half is the one that can bite: a runner that summed every
        # summary line would report a larger figure here, and "the total is
        # the suite's own count" alone would not tell the two apart. Both
        # figures come off runs -- the outer's from this run, the transcript's
        # from running the suite directly -- so a case added to that suite
        # moves neither.
        transcript = self.transcript_counts()
        self.assertEqual(counted, transcript[-1], self.out)
        self.assertLess(counted, sum(transcript),
                        'the runner reported the sum of every summary line in '
                        f"the transcript rather than the suite's own run; the "
                        f'lines were {transcript}:\n{self.out}')

    @classmethod
    def transcript_counts(cls):
        """Every summary figure the suite's own transcript carries.

        Run directly rather than read out of the runner's output, because the
        runner only prints a transcript for a suite that failed, and this one
        passes. The last figure is the suite's own run -- the record says so,
        and `RecordedNestingTests` is what holds that reading -- and the ones
        before it are the suites it drives.

        Empty is a failure rather than an empty list for the caller to index:
        a unittest that stopped printing its summary would make every
        assertion below compare against nothing.
        """
        done = subprocess.run(
            [sys.executable, '-m', 'unittest', 'discover', '-s',
             str(REPO / 'ec' / 'tools'), '-p', Path(cls.PATH).name],
            cwd=str(REPO), capture_output=True, text=True)
        transcript = done.stdout + done.stderr
        found = [int(n) for n in NESTED.findall(transcript)]
        if not found:
            raise AssertionError(
                f'{cls.PATH} printed no `Ran N tests` line of its own:\n'
                + transcript)
        return found

    def test_the_suite_really_does_nest(self):
        # So the case above is testing something. If that suite stopped running
        # other suites, its transcript would carry one summary line, the sum
        # would equal its own count, and `assertLess` would hold -- while the
        # property the runner exists for went untested.
        transcript = self.transcript_counts()
        self.assertGreater(len(transcript), 1,
                           f'{self.PATH} no longer runs other suites, so the '
                           'record and the refusal it feeds have nothing to '
                           'decide here and the cases around it prove nothing:\n'
                           f'{transcript}')

    def test_the_line_names_it_and_the_choice(self):
        body = suite_lines(self.out)[self.PATH]
        self.assertIn('summary lines', body, self.out)
        self.assertIn('last', body, self.out)


if __name__ == '__main__':
    unittest.main()
