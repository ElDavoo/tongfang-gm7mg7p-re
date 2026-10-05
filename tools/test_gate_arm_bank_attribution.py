#!/usr/bin/env python3
"""The `check_ghidra_tooling()` tail fold still lands `bank_attribution.py`'s call.

Stands in for the fold issue #1081 asked for: `bank_attribution.py`'s
`--self-test` folds into `docs/ci/agent-gates-reassembly-bound-check.patch`
rather than shipping a patch of its own, and a fold is exactly the thing that
can go half-right without anyone noticing.

**The mutation this exists to catch, and why it is silent.** A re-cut that keeps
the calls already in that tail and drops this one still applies cleanly. It still
composes in every ordered pair, because the calls share one contiguous region
and a dropped one leaves the region it was cut against untouched. It still passes
`bash -n` and `shellcheck`, because a tail call that is simply absent is not a
syntax error. And `check_gate_arm_coverage.py` stays green, because it reads the
tool *list* and its `case` arms and none of these calls is in either: they are
tail calls, below `done`. Every case in `tools/test_agent_gates_patches.py`
passes on the half-folded patch. The gate then runs one fewer check than it was
going to, and says so by being green.

This is the same shape as `tools/test_gate_arm_audit_call_targets.py`'s, applied
to a third tool in the same fold, and it is a **separate file** rather than a
class appended to that suite for the reason CLAUDE.md gives: the sibling suite is
shared, and two branches adding to one fold are two branches appending to one
long file, which collide at its last line. Its helpers are re-derived here rather
than imported, because they are that file's private API — importing them would
make this suite's subject depend on every refactor of it, which is a second
branch's edit away. The `git apply` plumbing is therefore re-derived rather than
borrowed. The one thing this file *does* import is
`ec/tools/check_gate_arm_coverage.py`, and it imports the production checker
rather than a test helper precisely because it is the authority on what a gate
claim is; see `DocstringClaimTests`.

**What is not exercised by any committed suite is the shipped command.** That
is narrower than "the checks are unasserted", and the difference is measured.
`ec/tools/test_bank_attribution_common_follow.py` is committed, is found by
`tools/run-tests.sh`, runs in CI, and `TheSelfTest::test_it_passes` calls
`self_test()` in-process over the committed image and asserts the status -- so
the stub decoding, the seed census and the hand-decoded pins, all of them checks
*inside* `self_test()`, are already red on a sweep that breaks any of them.
`ec/tools/test_dispatch_edges.py` imports `bank_attribution` and drives it as a
subprocess, but only with `--regions-csv` and `--pairs-csv`. Measured on the
committed tree, breaking `main()`'s `if args.self_test: return self_test(d)`
makes the shipped command exit 0 having printed the tool's own report and no
`self-test passed` line, and every one of those suites stays green, because
none of them goes through `main()`, `argparse` or the exit status; forcing one
hand-decoded pin's condition false turns the command red and
`TheSelfTest::test_it_passes` with it. Both rows are in
`docs/findings/bank-attribution-gate-arm.md`; the mutation table below is the
same one.

**The second thing it holds is the arm's behaviour, not only its presence.** A
re-cut that keeps `|| rc=1` and drops the transcript assertion is a patch that
still applies, still composes, still lints, and leaves the gate green on the
first row of that table — `--self-test` no longer dispatching, so the command a
person would type exits 0 having printed the tool's report with no
`self-test passed` line on it. An exit status alone cannot see
that, which is why the block greps the transcript as well.
`ArmBehaviourTests` runs the landed block against a stub tool, so that claim is
re-derived rather than asserted in prose here.

**The third thing it holds is where the block sits, which nothing else can see.**
`arm_block()` cuts the block out by its own opening line and the first `fi` at
that indent, and a block cut from inside the tool loop and the same block cut
from after it are byte-identical, so every case above passes either way. `git
apply` reads the pre-image and not the shape of the result, `bash -n` and
`shellcheck` accept both, and `check_gate_arm_coverage.py` reads the tool list
and its `case` arms -- which is neither. So a re-cut that slid the block up past
the loop's `done` applies, composes, lints, and turns this suite green while
every call in the fold runs once per entry in the tool list instead of once per
sweep. `PlacementTests` asserts the relation rather than a count of blocks.

**Not a gate, and not in the cheap tier**, for the reason the sibling suite's
docstring gives: `.github/scripts/agent-gates.sh` is a template-copied file and
the pipeline's push token has no `workflow` scope. This runs when
`tools/run-tests.sh` runs.

**No count of the tree is asserted.** Every case here is a property of the
patch: this call lands. A count of how many tools the fold carries, or of how
many suites exist, is a value every later fold has to edit -- the failure
CLAUDE.md records four times over -- so `REQUIRED` grows by a string per tool
and the sentences around it do not change.
"""
import difflib
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
GATE = '.github/scripts/agent-gates.sh'
PATCH = 'docs/ci/agent-gates-reassembly-bound-check.patch'

# The gate checker, imported by path because `ec/tools/` is not on `sys.path`
# when the runner invokes this file. Only its `claims()` is used, and only so
# that this suite and the gate cannot disagree about what a gate claim is --
# see `DocstringClaimTests` for why a copy of the predicate would be worse than
# no predicate at all.
_spec = importlib.util.spec_from_file_location(
    "check_gate_arm_coverage", REPO / "ec" / "tools" / "check_gate_arm_coverage.py")
coverage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(coverage)

# This tool's call, as a whole block rather than as the one line that differs
# from the calls beside it. `|| rc=1` and `cat` appear in the others too, so a
# single-line string would pass on a fold that dropped this block entirely; the
# block is what the patch's own `if` body is, and dropping it whole is the
# mutation.
REQUIRED = (
    '  if [ -f ec/tools/bank_attribution.py ]; then\n'
    '    python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 \\\n'
    '      --self-test > "$scratch/bank-attribution-self-test.txt" || rc=1\n'
    '    cat "$scratch/bank-attribution-self-test.txt"\n'
    '    if ! grep -q \'self-test passed\' '
    '"$scratch/bank-attribution-self-test.txt"; then\n'
    '      echo "bank_attribution.py --self-test printed no '
    '\'self-test passed\' line" >&2\n'
    '      rc=1\n'
    '    fi\n'
    '  fi'
)

# The image path the call passes. Held as its own case rather than as part of
# `REQUIRED` because it is a *different kind* of claim: the `if` block is what
# the fold carries, and this is what makes the carried call a check over the
# committed dump at all rather than a command that exits 2 on a missing file. A
# re-cut that points it at another image still applies, still composes and still
# lints.
IMAGE = 'ec/firmware/GMxMGxx_11.800'


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True,
                          text=True)


def has_git():
    return shutil.which('git') is not None


def has_git_repo():
    return (REPO / '.git').exists() and has_git()


def committed_gate_text():
    """The gate script at HEAD, which is what a patch is cut against."""
    shown = git('show', f'HEAD:{GATE}', cwd=REPO)
    if shown.returncode != 0:
        raise AssertionError(
            f'{GATE} cannot be read at HEAD:\n{shown.stderr.strip()}')
    return shown.stdout


def committed_mode():
    """The mode git recorded for the gate script, or None with no commit."""
    listed = git('ls-tree', 'HEAD', '--', GATE, cwd=REPO)
    if listed.returncode != 0 or not listed.stdout.strip():
        return None
    return int(listed.stdout.split()[0], 8) & 0o7777


@contextmanager
def scratch_tree():
    """A throwaway repo holding nothing but a copy of the committed gate script.

    Seeded from `git show HEAD:…` rather than from the working-tree file, which
    is the one deviation from the sibling suite's `scratch_tree()` and is
    deliberate: this suite's whole subject is a fold, so a working-tree edit to
    the gate script would be measured instead of the commit, and
    `tools/test_agent_gates_patches.py`'s `CommittedBaseTests` already holds
    that equality for its own scratch trees. Reading the commit directly means
    the seed is the thing the patch was cut against whether or not anyone has a
    local edit outstanding.

    The bytes are written and then the mode is set from the committed tree:
    every patch in `docs/ci/` carries `100755` on its `index` line, and `git
    apply` on a 0644 file warns on every call and exits 0 anyway -- so a mode
    that can only ever be wrong in the passing direction is not worth having.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / GATE
        target.parent.mkdir(parents=True)
        target.write_text(committed_gate_text())
        mode = committed_mode()
        if mode is not None:
            target.chmod(mode)
        git('init', '-q', '.', cwd=root)
        yield root


def landed_gate_text():
    """The gate script with this patch applied, and the apply's stderr."""
    with scratch_tree() as tree:
        done = git('apply', str(REPO / PATCH), cwd=tree)
        return (tree / GATE).read_text(), done


# The `if` this patch lands for this tool, and the line that closes it at the
# block's own indent. Both are named rather than inlined so `arm_block()` fails
# loudly on a re-cut that moved them, and neither is a count of the file.
ARM_OPEN = '  if [ -f ec/tools/bank_attribution.py ]; then\n'
ARM_CLOSE = '\n  fi\n'


def arm_block(gate_text):
    """The landed `if` block on its own, so it can be run against a stub.

    Cut by its own opening line and the first line at the block's own indent
    that closes it. The inner `if ! grep -q ...` closes at a deeper indent and
    is not what the second index finds, which is the same reading the shell
    gives the block.

    Sourced rather than executed by its caller: it sets `rc`, which is the gate
    function's own accumulator, and its value afterwards is the result.
    """
    for anchor in (ARM_OPEN, ARM_CLOSE):
        if anchor not in gate_text:
            raise AssertionError(
                f'{anchor!r} is not in the {GATE} this patch lands, so the '
                'block cannot be cut out of it and nothing below would be '
                'measuring the arm. Re-cut the patch, or move the anchor '
                'constant here to wherever the block now is.')
    start = gate_text.index(ARM_OPEN)
    return gate_text[start:gate_text.index(ARM_CLOSE, start) + len(ARM_CLOSE)]


class FoldRetentionTests(unittest.TestCase):
    """The folded patch lands this tool's call, and lands the image path too.

    The mutation is named in the module docstring because a reader who has not
    seen it will not guess what a half-folded tail call looks like: a gate that
    runs fewer checks than it was going to and is green.
    """

    def setUp(self):
        if not has_git_repo():
            self.skipTest('no git, or no .git beside the repository; there is '
                          'nothing to apply the patch to')
        self.patch_text = (REPO / PATCH).read_text()

    def test_the_patch_lands_the_call(self):
        landed, done = landed_gate_text()
        self.assertEqual(
            done.returncode, 0,
            f'{PATCH} no longer applies to the committed {GATE}:\n'
            f'{done.stderr.strip()}\nRe-cut it against the current file; the '
            'context a hunk needs is whatever the file has today, not whatever '
            'it had when the patch was cut.')
        # `assertTrue` rather than `assertIn`: `assertIn` prints the whole
        # container on failure, and the container is the gate script -- the
        # sentence below the assertion is what a reader needs instead.
        self.assertTrue(
            REQUIRED in landed,
            f'{PATCH} no longer lands {REQUIRED.splitlines()[0]!r}. This patch '
            "carries bank_attribution.py's call because the free region in "
            'agent-gates.sh is the tail of check_ghidra_tooling() and this '
            'file already held it: a patch cut at the same anchor applies '
            'cleanly alone and fails only against this one, in both orders. A '
            're-cut that drops this call still applies, still composes in every '
            'ordered pair, and still passes `bash -n` and `shellcheck` -- so '
            'the gate would run fewer checks and be green. Nothing else in '
            'tools/test_agent_gates_patches.py notices: '
            'check_gate_arm_coverage.py reads the tool list and its `case` '
            'arms, and these calls are in neither, because they are tail calls '
            'below `done`.')

    def test_the_landed_call_passes_the_committed_image(self):
        landed, _ = landed_gate_text()
        self.assertTrue(
            IMAGE in landed,
            f'{PATCH} no longer passes {IMAGE} to bank_attribution.py. The '
            'call is the one that runs the tool as a command, and it takes a '
            'positional firmware path -- an arm that named a path this '
            'repository does not commit would either check the wrong image or '
            'exit on a missing file, and both look like a green gate with a '
            'tool that stopped checking anything.')
        self.assertTrue(
            (REPO / IMAGE).is_file(),
            f'{IMAGE} is not on disk, so the arm this patch lands would fail '
            'on a path rather than on a check. The patch is cut against a tree '
            'where it exists; re-cut it if the image moved.')

    def test_the_folded_result_is_shell_that_parses(self):
        # The other half of "a patch can apply and still be wrong". `git apply`
        # checks the pre-image and says nothing about whether the result is
        # shell, and the cheap tier's own `shellcheck` gate runs over
        # `.github/scripts/agent-gates.sh` the moment a human lands this.
        with scratch_tree() as tree:
            done = git('apply', str(REPO / PATCH), cwd=tree)
            self.assertEqual(done.returncode, 0, done.stderr.strip())
            target = str(tree / GATE)
            parsed = subprocess.run(['bash', '-n', target],
                                    capture_output=True, text=True)
            self.assertEqual(
                parsed.returncode, 0,
                f'{PATCH} applies, but the script it lands does not parse:\n'
                f'{parsed.stderr.strip()}')
            if shutil.which('shellcheck') is None:
                self.skipTest('no shellcheck on PATH')
            linted = subprocess.run(['shellcheck', target],
                                    capture_output=True, text=True)
            self.assertEqual(
                linted.returncode, 0,
                f'{PATCH} lands a shellcheck failure:\n'
                f'{linted.stdout.strip()}')


class PlacementTests(unittest.TestCase):
    """The landed block is below the tool loop's `done`, not inside its body.

    Nothing else in this file can see this, which is why it is a case.
    `arm_block()` cuts the block out by its own opening line and the first `fi`
    at that indent, and a block cut from inside the loop and the same block cut
    from after it are byte-identical, so every behaviour case above passes
    either way. Nor can the gates around it: `git apply` reads the pre-image and
    says nothing about the shape of the result, `bash -n` and `shellcheck`
    accept both placements, and `check_gate_arm_coverage.py` reads the tool
    *list* and its `case` arms, which is neither of them.

    So a re-cut that slid the block up past the loop's `done` applies cleanly,
    composes in every ordered pair, lints, and turns this suite green -- while
    every call in it runs once per entry in the tool list rather than once per
    sweep, re-running the two the fold already carried. The relation is asserted,
    not a count of blocks or of loop entries: what has to hold is that the loop
    finished before the block starts.
    """

    # The scratch cleanup, which closes `check_ghidra_tooling()` and is the one
    # line present under *either* placement. Anchoring the search here is what
    # lets the case measure the block's position: a block correctly placed
    # separates `done` from this line, so a `done`/cleanup pair is adjacent only
    # in the *wrong* form and cannot be the anchor. Named rather than located by
    # counting `done`s, so a gate that grows a second loop reads as an anchor
    # that moved rather than as a number this file would have to keep editing.
    CLEANUP = '  rm -rf "$scratch"\n'

    # The `done` that closes a `for` loop, at the loop body's own indent. The
    # last one before the cleanup is the tool loop's under either placement.
    DONE = '  done\n'

    def setUp(self):
        if not has_git_repo():
            self.skipTest('no git, or no .git beside the repository; there is '
                          'nothing to apply the patch to')
        landed, done = landed_gate_text()
        self.assertEqual(
            done.returncode, 0,
            f'{PATCH} no longer applies to the committed {GATE}:\n'
            f'{done.stderr.strip()}')
        self.landed = landed

    def test_the_block_starts_after_the_loop_finishes(self):
        # `assertTrue` on membership rather than `assertIn`, for the reason
        # `FoldRetentionTests` gives: the container is the gate script, and
        # `assertIn` prints all of it, where the sentence below is what a
        # reader needs.
        for anchor, what in ((self.CLEANUP, 'the scratch cleanup'),
                             (ARM_OPEN, 'this tool\'s `if` block')):
            self.assertTrue(
                anchor in self.landed,
                f'{what} is not in the {GATE} {PATCH} lands, so the relation '
                'this case is about cannot be measured and the case would pass '
                f'on a patch that is not placed at all:\n{anchor!r}\n'
                'Re-cut the patch, or move the anchor here to wherever the '
                'script now has it.')
        # The last `done` before the cleanup is the tool loop's, whichever side
        # of it the block landed.
        cleanup = self.landed.index(self.CLEANUP)
        loop_ends = self.landed.rindex(self.DONE, 0, cleanup) + len(self.DONE)
        self.assertLess(
            loop_ends, self.landed.index(ARM_OPEN),
            f'{ARM_OPEN.strip()} is at or above the tool loop\'s `done`, so the '
            f'block {PATCH} lands is INSIDE the loop body. Every call in the '
            'fold -- this one and the two it was folded in beside -- then runs '
            'once per entry in the tool list rather than once per sweep, which '
            'is a cost the cheap tier pays silently on every run. The block '
            'belongs after the loop\'s `done` and before `rm -rf "$scratch"`, '
            'which is where the patch header says it is and where the sibling '
            'fold puts its own. `git apply`, `bash -n`, `shellcheck` and '
            '`check_gate_arm_coverage.py` are green either way, which is what '
            'makes this a case rather than a note.')


class MutationTests(unittest.TestCase):
    """A fold that drops this call is caught -- shown, not asserted.

    A case nobody has seen go red is worth nothing, and this suite's only
    reason to exist is the mutation. So the half-folded patch is *built* here,
    from the committed script and the calls it already carries, and every
    property that makes it dangerous is asserted to hold on it: it applies, it
    parses, it lints. Only then is the retention check held against it, and it
    has to fail.

    That ordering is the discipline `docs/findings/prepared-gate-patches.md`
    records: proving the mutation is realistic is what makes the green case mean
    something. A mutant that failed to apply would make the retention case pass
    for the wrong reason -- it would be catching a broken patch rather than a
    half-folded one.
    """

    # The tail of the committed gate script this fold's hunk is cut against, and
    # where a half-folded patch inserts what it still carries. The seed is the
    # committed script and the content comes from the patch, so neither is a
    # transcription here -- see `read_added_blocks`.
    ANCHOR = '  done\n  rm -rf "$scratch"\n'

    @classmethod
    def setUpClass(cls):
        if not has_git_repo():
            raise unittest.SkipTest(
                'no git, or no .git beside the repository; there is nothing to '
                'cut a half-folded patch against')
        seed = committed_gate_text()
        if cls.ANCHOR not in seed:
            raise AssertionError(
                f'the committed {GATE} no longer holds the tail this patch is '
                'cut against:\n' + cls.ANCHOR + '\nSo the half-folded fixture '
                'below would insert nothing, and this class would pass on a '
                'patch that is not half-folded.')
        kept = read_added_blocks()
        cls.mutant = seed.replace(cls.ANCHOR, kept + cls.ANCHOR, 1)

    def test_the_fixture_really_is_half_folded(self):
        # Both directions. The fixture must carry the calls the fold already had
        # and not this one, or it is a whole fold or an empty one and the case
        # below is checking something else. `assertTrue` on membership rather
        # than `assertIn`, because the container is the gate script and the
        # sentence below the assertion is what a reader needs.
        for block in read_added_blocks().splitlines():
            if not block.startswith('  if [ -f ec/tools/'):
                continue
            with self.subTest(call=block.strip()):
                self.assertTrue(
                    block in self.mutant,
                    'the fixture does not carry a call the fold already had, so '
                    'it is not the half-landing this class is about')
        self.assertFalse(
            REQUIRED in self.mutant,
            'the fixture carries this tool\'s call too, so this is a whole fold '
            'and the retention case below would pass on a patch that had '
            'dropped nothing')

    def test_a_half_folded_patch_applies_and_still_lints(self):
        # Every property that makes the mutation silent, asserted on the
        # fixture rather than assumed. If any of these stopped holding, the fold
        # would stop being dangerous in that direction -- and the case that
        # follows would be guarding against nothing.
        seed = committed_gate_text()
        patch = ('diff --git a/%s b/%s\n' % (GATE, GATE)
                 + ''.join(difflib.unified_diff(
                     seed.splitlines(True), self.mutant.splitlines(True),
                     fromfile='a/' + GATE, tofile='b/' + GATE, n=3)))
        with scratch_tree() as tree:
            (tree / 'half.patch').write_text(patch)
            done = git('apply', str(tree / 'half.patch'), cwd=tree)
            self.assertEqual(
                done.returncode, 0,
                f'the half-folded fixture does not apply to the committed '
                f'{GATE}:\n{done.stderr.strip()}\nIf this fails, the fixture '
                'is not the mutation this class is about -- a patch that '
                'cannot apply is not one a re-cut could ship by accident, and '
                'the case below would be guarding against nothing.')
            # Both lints run inside the `with`: the scratch tree is a
            # `TemporaryDirectory`, so a path read after it closes is a path
            # that does not exist, and `shellcheck` exits 2 on that -- which
            # reads exactly like the finding this case is asserting.
            target = str(tree / GATE)
            parsed = subprocess.run(['bash', '-n', target],
                                    capture_output=True, text=True)
            self.assertEqual(parsed.returncode, 0,
                             'the half-folded result does not parse, so the '
                             'mutation would have been caught by syntax alone '
                             'and this suite would be guarding against nothing')
            if shutil.which('shellcheck') is not None:
                linted = subprocess.run(['shellcheck', target],
                                        capture_output=True, text=True)
                self.assertEqual(linted.returncode, 0,
                                 'the half-folded result is not '
                                 'shellcheck-clean, so the mutation would have '
                                 'been caught by the cheap tier\'s own lint '
                                 'gate and this suite would be guarding against '
                                 f'nothing:\n{linted.stdout.strip()}')

    def test_the_retention_check_fails_on_it(self):
        missing = REQUIRED.splitlines()[0] if REQUIRED not in self.mutant else ''
        self.assertEqual(
            missing, REQUIRED.splitlines()[0],
            'the retention check did not find this tool\'s call missing in a '
            'half-folded patch, where it must find exactly the one the dropped '
            'half carried. Either it is not reading the script it is supposed '
            'to read, or the block is not where this case thinks it is. That '
            f'line is {REQUIRED.splitlines()[0]!r}: dropping it is the mutation '
            'this suite exists to catch, and the gate would then run one fewer '
            'check than it was going to and be green.')


def read_added_blocks():
    """The `if` blocks the patch lands for the other tools in this fold.

    Read out of the patch rather than transcribed, so this fixture cannot drift
    from the patch it is meant to be a half of. Everything the patch adds that
    opens an `if [ -f ec/tools/` at the block indent is taken, and this tool's
    own block is left out -- which is the whole mutation.

    Raises rather than returning a short answer, because a fixture that had
    quietly lost the calls it is supposed to keep would be a fixture the
    `apply` and `lint` cases pass on for the wrong reason.
    """
    text = (REPO / PATCH).read_text()
    body = text[text.find('diff --git '):]
    added = ''.join(line[1:] for line in body.splitlines(True)
                    if line.startswith('+') and not line.startswith('+++'))
    kept = added.replace(REQUIRED + '\n', '', 1)
    if REQUIRED in kept:
        raise AssertionError(
            f'{PATCH} carries {REQUIRED.splitlines()[0]!r} more than once, so '
            'the half-folded fixture below would drop one copy and keep the '
            'other, and every case in this class would be measuring a fold that '
            'still had the call this suite exists to watch.')
    if not kept.strip():
        raise AssertionError(
            f'{PATCH} adds no other `if [ -f ec/tools/` block, so the '
            'half-folded fixture would be the committed script unchanged and '
            'the "it still applies and still lints" claim would be trivially '
            'true rather than measured.')
    return kept


class ArmBehaviourTests(unittest.TestCase):
    """The landed block, run: a silent self-test is as red as a failing one.

    `FoldRetentionTests` holds that the block is in the patch. This holds what it
    does once it is, against the mutation it exists for: a re-cut that keeps
    `|| rc=1` and drops the transcript assertion still applies, still composes,
    still lints, and leaves the **gate** green on the break the call is here for
    -- `--self-test` no longer dispatching, so the command a person would type
    exits 0 having printed the tool's report with no `self-test passed` line.
    An exit status alone cannot see that, which
    is why the block greps the transcript as well;
    `ec/tools/test_call_graph_gaps.py` asserts its subprocess's stdout for the
    same reason, and it is the half that carries it there too.

    The block is run on its own rather than through `check_ghidra_tooling()`,
    which would run the whole cheap tier to reach two lines, and against a stub
    rather than the real tool, because the dispatch break cannot be expressed
    without editing `ec/tools/bank_attribution.py` itself. The stub is what the
    arm runs -- `python3 <tool> <image> --self-test` -- and it ignores both
    arguments, so no image has to be on disk beside it.
    """

    # The self-test that ran, and the transcript it prints. Also the arm's own
    # success path, and what the `cat` in the block exists to keep in the gate
    # log rather than swallow into the scratch dir.
    PASSING = 'print("  ok   a check")\nprint("self-test passed")\n'

    # (what the stub does, the status the arm must return for it, its body).
    # Each row is a row of the mutation table in
    # `docs/findings/bank-attribution-gate-arm.md`.
    #
    # The second row is the one the docstring is about, so its stub prints a
    # report and exits 0 rather than exiting 0 silently: that is what the named
    # mutation does, because `main()` falls through to the tool's ordinary
    # report path. A silent stub would model the *other* mutant (`return 0` in
    # place of the dispatch), which prints nothing -- and the two are caught by
    # the same grep for different reasons, so a silent stub would leave the case
    # standing for a failure shape this tool does not have.
    STUBS = (
        ('the self-test ran', 0, PASSING),
        ('`--self-test` no longer dispatches to self_test()', 1,
         'import sys\n'
         'print("## 1. The seeds: what the linker\'s own trampolines name")\n'
         'print("  stub 0x1100 selects bank 0: 350 seed(s) route through it")\n'
         'print("## 3. The verdict over both populations")\n'
         'print("  the 1305 bucket-B pairs split 625 / 75 / 510 / 95")\n'
         'sys.exit(0)\n'),
        ('a check in the self-test failed', 1,
         'import sys\nprint("  FAIL  a check")\nprint("self-test FAILED")\n'
         'sys.exit(1)\n'),
        ('`--self-test` no longer exists as a flag', 1,
         'import sys\nsys.stderr.write("unrecognized arguments\\n")\n'
         'sys.exit(2)\n'),
    )

    def setUp(self):
        if not has_git_repo():
            self.skipTest('no git, or no .git beside the repository; there is '
                          'nothing to apply the patch to')
        landed, done = landed_gate_text()
        self.assertEqual(
            done.returncode, 0,
            f'{PATCH} no longer applies to the committed {GATE}:\n'
            f'{done.stderr.strip()}')
        self.block = arm_block(landed)

    def run_arm(self, stub):
        """The landed block over a stub tool, and what it returned.

        Sourced rather than run, in a tree of its own: the block writes to
        `$scratch` and sets `rc`, so both have to exist and `rc`'s value
        afterwards is the result. The scratch dir is made here because the
        block only ever appends to it -- in the gate the function creates it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = root / 'ec' / 'tools' / 'bank_attribution.py'
            tool.parent.mkdir(parents=True)
            tool.write_text(stub)
            (root / 'scratch').mkdir()
            (root / 'block.sh').write_text(self.block)
            return subprocess.run(
                ['bash', '-c',
                 # `bash -c <script> <$0> <$1> <$2>`, so the scratch dir and
                 # the block are passed in rather than interpolated.
                 'scratch="$1"; rc=0; . "$2"; exit "$rc"',
                 'arm', str(root / 'scratch'), str(root / 'block.sh')],
                cwd=root, capture_output=True, text=True)

    def test_the_arm_catches_each_of_them(self):
        for name, want, stub in self.STUBS:
            with self.subTest(stub=name):
                ran = self.run_arm(stub)
                self.assertEqual(
                    ran.returncode, want,
                    f'the block {PATCH} lands returned {ran.returncode} where '
                    f'{want} is what {name!r} must produce.\n'
                    f'stdout:\n{ran.stdout}\nstderr:\n{ran.stderr}')

    def test_the_transcript_still_reaches_the_gate_log(self):
        """The `cat` is not decoration: the tool's output is the gate's log.

        Grepping the transcript into `$scratch` and reading it there is what
        lets the arm assert on it, and a re-cut that dropped the `cat` would
        make every self-test assertion invisible in the run that reports it.
        """
        ran = self.run_arm(self.PASSING)
        self.assertIn(
            'self-test passed', ran.stdout,
            f'the block {PATCH} lands no longer prints what the tool printed, '
            'so a gate run says the self-test ran and shows nothing of it:\n'
            f'{ran.stdout}')


class DocstringClaimTests(unittest.TestCase):
    """This tool's docstring may not claim a place in the gate.

    `check_gate_arm_coverage.py` direction 3 reads a tool docstring that puts
    its tool *in* `.github/scripts/agent-gates.sh` and requires a `case` arm to
    satisfy the claim. **A tail call is not a `case` arm.** So a docstring that
    gained a gate-membership claim would go red against an arm that is landed
    and working -- the opposite of what direction 3 is for, and a red cheap
    tier that is nobody's fault but the docstring's.

    That makes this the non-obvious way to break the fold: the instinct on
    landing the arm is to write down that it is landed, in the place that reads
    like the authority on the tool's own behaviour, and that is precisely the
    edit that goes red. The claim belongs in the patch header and in
    `docs/findings/bank-attribution-gate-arm.md`, which is where a reader comes
    to land the arm from.

    **The predicate is imported, not reimplemented.** A hand-copied version of
    direction 3's clause reading is a weaker check that passes for reasons the
    real one would not. `claims()` is the authority on what counts as a claim,
    so this asks it rather than agreeing with it by construction, and the gate's
    own checker keeps meaning what it means if its vocabulary moves.
    """
    TOOL = 'ec/tools/bank_attribution.py'

    def test_the_docstring_does_not_claim_gate_membership(self):
        import ast
        rel = self.TOOL
        docstring = ast.get_docstring(
            ast.parse((REPO / rel).read_text())) or ''
        found = coverage.claims(docstring)
        self.assertEqual(
            found, [],
            f'{rel} claims a place in the gate: {found!r}. Its arm is a tail '
            f'call in the fold of {PATCH}, not a `case` arm, so '
            '`check_gate_arm_coverage.py`\'s direction 3 cannot satisfy the '
            'claim -- it requires a `case` arm -- and the cheap tier would go '
            'red against a gate edit that works. The claim belongs in the patch '
            'header and in docs/findings/bank-attribution-gate-arm.md.')


if __name__ == '__main__':
    unittest.main()
