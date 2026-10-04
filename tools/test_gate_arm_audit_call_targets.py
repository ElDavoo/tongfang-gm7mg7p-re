#!/usr/bin/env python3
"""The `check_ghidra_tooling()` tail fold still lands *both* tools' calls.

Stands in for the fold issue #1094 asked for: `audit_call_targets.py`'s
`--self-test` folds into `docs/ci/agent-gates-reassembly-bound-check.patch`
rather than shipping a patch of its own, and a fold is exactly the thing that
can go half-right without anyone noticing.

**The mutation this exists to catch, and why it is silent.** A re-cut that
keeps `reassembly_checked_bound.py --check` and drops `audit_call_targets.py`
--self-test` still applies cleanly. It still composes in every ordered pair,
because the two calls share one contiguous region and the dropped one leaves
the region it was cut against untouched. It still passes `bash -n` and
`shellcheck`, because a tail call that is simply absent is not a syntax error.
And `check_gate_arm_coverage.py` stays green, because it reads the tool *list*
and its `case` arms and neither of these two calls is in either: they are tail
calls, below `done`. Every existing case in
`tools/test_agent_gates_patches.py` passes on the half-folded patch. The gate
then runs one of the two checks it was going to run, and says so by being
green.

This is `ArmRetentionTests`' rationale applied to a tail call rather than to a
`case` arm, and the same shape as `FoldTests` and the fold
`docs/ci/agent-gates-disasm8051-self-test.patch` carries. It is a separate file
rather than a class appended to that suite for the reason CLAUDE.md gives: the
sibling suite is shared, and #1081 is going to add a third tool to this same
fold, so two branches appending to one long suite collide at its last line.
The sibling suite's helpers are not imported, and that is deliberate rather
than incidental: they are that file's private API, and reusing them would make
this suite's subject depend on every refactor of it -- and #1081 is editing that
suite too. The `git apply` plumbing is therefore re-derived here. The one thing
this file *does* import is `ec/tools/check_gate_arm_coverage.py`, and it imports
the production checker rather than a test helper precisely because it is the
authority on what a gate claim is; see `DocstringClaimTests`.

**The second thing it holds is the arm's behaviour, not only its presence.** A
re-cut that keeps `|| rc=1` and drops the transcript assertion is a patch that
still applies, still composes, still lints, and leaves the gate green on the one
break the call exists for — `--self-test` no longer dispatching, so the command
exits 0 having printed nothing. `ArmBehaviourTests` runs the landed block
against a stub tool for each row of the mutation table in
`docs/findings/audit-call-targets-gate-arm.md`, so that claim is re-derived
rather than asserted in prose here.

**Not a gate, and not in the cheap tier**, for the reason the sibling suite's
docstring gives: `.github/scripts/agent-gates.sh` is a template-copied file and
the pipeline's push token has no `workflow` scope. This runs when
`tools/run-tests.sh` runs.

**No count of the tree is asserted.** Every case here is a property of the
patch: these two calls land. A count of how many tools the fold carries, or of
how many suites exist, is a value every later fold has to edit -- the failure
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

# The two calls, as whole blocks rather than as the one line that differs
# between them. `reassembly_checked_bound.py --check || rc=1` appears once, so
# a single-line string would pass on a fold that dropped the other tool; the
# blocks are what the patch's own two `if` bodies are, and dropping either
# whole block is the mutation.
REQUIRED = [
    '  if [ -f ec/tools/reassembly_checked_bound.py ]; then\n'
    '    python3 ec/tools/reassembly_checked_bound.py --check || rc=1\n'
    '  fi',
    '  if [ -f ec/tools/audit_call_targets.py ]; then\n'
    '    python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 \\\n'
    '      --self-test > "$scratch/audit-call-targets-self-test.txt" || rc=1\n'
    '    cat "$scratch/audit-call-targets-self-test.txt"\n'
    '    if ! grep -q \'self-test passed\' '
    '"$scratch/audit-call-targets-self-test.txt"; then\n'
    '      echo "audit_call_targets.py --self-test printed no '
    '\'self-test passed\' line" >&2\n'
    '      rc=1\n'
    '    fi\n'
    '  fi',
]

# The image path the second call passes. Held as its own case rather than as
# part of `REQUIRED` because it is a *different kind* of claim: the two `if`
# blocks are what the fold carries, and this is what would make the carried
# call run at all. A re-cut that points it at another image still applies,
# still composes and still lints, and the gate would then check a dump this
# repository does not commit -- or fail on a path that is not there.
IMAGE = 'ec/firmware/GMxMGxx_11.800'


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True,
                          text=True)


def has_git():
    return shutil.which('git') is not None


@contextmanager
def scratch_tree():
    """A throwaway repo holding nothing but a copy of the committed gate script.

    Seeded from `git show HEAD:…` rather than from the working-tree file, which
    is the one deviation from the sibling suite's `scratch_tree()` and is
    deliberate: this suite's whole subject is a fold, so a working-tree edit to
    the gate script would be measured instead of the commit, and the sibling's
    `CommittedBaseTests` already holds that equality for its own scratch trees.
    Reading the commit directly means the seed is the thing the patch was cut
    against whether or not anyone has a local edit outstanding.

    `copy2` semantics are reproduced by writing the bytes and then setting the
    mode from the committed tree: every patch in `docs/ci/` carries `100755` on
    its `index` line, and `git apply` on a 0644 file warns on every call and
    exits 0 anyway -- so a mode that can only ever be wrong in the passing
    direction is not worth having.
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


def has_git_repo():
    return (REPO / '.git').exists() and has_git()


def landed_gate_text():
    """The gate script with this patch applied, and the apply's stderr."""
    with scratch_tree() as tree:
        done = git('apply', str(REPO / PATCH), cwd=tree)
        return (tree / GATE).read_text(), done


# The `if` this patch lands for the second tool, and the line that closes it at
# the block's own indent. Both are named rather than inlined so `arm_block()`
# fails loudly on a re-cut that moved them, and neither is a count of the file.
ARM_OPEN = '  if [ -f ec/tools/audit_call_targets.py ]; then\n'
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
    """The folded patch lands both calls, and lands the image path with them.

    The mutation is named in the module docstring because a reader who has not
    seen it will not guess what a half-folded tail call looks like: a gate that
    runs one of the two checks and is green.
    """

    def setUp(self):
        if not has_git_repo():
            self.skipTest('no git, or no .git beside the repository; there is '
                          'nothing to apply the patch to')
        self.patch_text = (REPO / PATCH).read_text()

    def landed_gate(self):
        """The gate script with this patch applied, and the apply's stderr."""
        return landed_gate_text()

    def test_the_patch_lands_both_calls(self):
        landed, done = self.landed_gate()
        self.assertEqual(
            done.returncode, 0,
            f'{PATCH} no longer applies to the committed {GATE}:\n'
            f'{done.stderr.strip()}\nRe-cut it against the current file; the '
            'context a hunk needs is whatever the file has today, not whatever '
            'it had when the patch was cut.')
        for block in REQUIRED:
            with self.subTest(block=block.splitlines()[0]):
                # `assertTrue` rather than `assertIn`: `assertIn` prints the
                # whole container on failure, and the container is the gate
                # script -- the sentence below the assertion is what a reader
                # needs instead.
                self.assertTrue(
                    block in landed,
                    f'{PATCH} no longer lands {block.splitlines()[0]!r}. This '
                    'patch carries two tools\' calls because the free region '
                    'in agent-gates.sh is the tail of check_ghidra_tooling() '
                    'and this file already held it: a second patch cut at the '
                    'same anchor applies cleanly alone and fails only against '
                    'this one, in both orders. A re-cut that lands one call and '
                    'drops the other still applies, still composes in every '
                    'ordered pair, and still passes `bash -n` and `shellcheck` '
                    '-- so the gate would run one of the two checks and be '
                    'green. Nothing else in tools/test_agent_gates_patches.py '
                    'notices: check_gate_arm_coverage.py reads the tool list '
                    'and its `case` arms, and these two calls are in neither, '
                    'because they are tail calls below `done`.')

    def test_the_landed_call_passes_the_committed_image(self):
        landed, _ = self.landed_gate()
        self.assertTrue(
            IMAGE in landed,
            f'{PATCH} no longer passes {IMAGE} to audit_call_targets.py. The '
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


class MutationTests(unittest.TestCase):
    """A fold that drops one call is caught -- shown, not asserted.

    A case nobody has seen go red is worth nothing, and this suite's only
    reason to exist is the mutation. So the half-folded patch is *built* here,
    from the committed script and a fixture block, and every property that makes
    it dangerous is asserted to hold on it: it applies, it parses, it lints, and
    the other tool's call is still in it. Only then is the retention check held
    against it, and it has to fail.

    That ordering is the discipline `docs/findings/prepared-gate-patches.md`
    records for the sibling suite: proving the mutation is realistic is what
    makes the green case mean something. A mutant that failed to apply would
    make the retention case pass for the wrong reason -- it would be catching a
    broken patch rather than a half-folded one.
    """

    @classmethod
    def setUpClass(cls):
        if not has_git_repo():
            raise unittest.SkipTest(
                'no git, or no .git beside the repository; there is nothing to '
                'cut a half-folded patch against')
        seed = committed_gate_text()
        # The anchor is the tail region both calls live in. Named as whole
        # lines rather than inlined, and checked below, for the reason
        # `LandedStateTests` gives its two: a seed edited out from under the
        # anchor would make the mutant add nothing and every case below would
        # pass on a patch that is not half-folded at all.
        cls.anchor = '  done\n  rm -rf "$scratch"\n'
        if cls.anchor not in seed:
            raise AssertionError(
                f'the committed {GATE} no longer holds the tail this patch is '
                'cut against:\n' + cls.anchor + '\nSo the half-folded fixture '
                'below would insert nothing, and this class would pass on a '
                'patch that is not half-folded.')
        landed = seed.replace(
            cls.anchor, cls.anchor.replace(
                '  done\n', REQUIRED[0] + '\n  done\n', 1),
            1)
        cls.mutant = landed

    def test_the_fixture_really_is_half_folded(self):
        # The other direction: the fixture must carry one call and not the
        # other, or the case below is checking a whole fold and would pass for
        # the wrong reason. `assertTrue` on membership rather than
        # `assertIn`/`assertNotIn`, because the container is the gate script
        # and the sentence below the assertion is what a reader needs.
        self.assertTrue(
            REQUIRED[0] in self.mutant,
            'the fixture does not carry the tool it keeps, so this is not '
            'the half-landing this class is about')
        self.assertFalse(
            REQUIRED[1] in self.mutant,
            'the fixture carries both calls, so this is a whole fold and the '
            'retention case below would pass on a patch that had dropped '
            'nothing')

    def test_a_half_folded_patch_applies_and_still_lints(self):
        # Every property that makes the mutation silent, asserted on the
        # fixture rather than assumed. If any of these stopped holding, the
        # fold would stop being dangerous in that direction -- and the case
        # that follows would be guarding against nothing.
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
                self.assertEqual(
                    linted.returncode, 0,
                    'the half-folded result is not shellcheck-clean, so the '
                    'mutation would have been caught by the cheap tier\'s own '
                    'lint gate and this suite would be guarding against '
                    f'nothing:\n{linted.stdout.strip()}')

    def test_the_retention_check_fails_on_it(self):
        missing = [b.splitlines()[0] for b in REQUIRED if b not in self.mutant]
        self.assertEqual(
            missing, [REQUIRED[1].splitlines()[0]],
            f'the retention check found {missing!r} missing in a half-folded '
            f'patch, where it must find exactly the call the dropped half '
            f'carried. Either it is not reading the script it is supposed to '
            f'read, or the halves are not where this case thinks they are. '
            f'{REQUIRED[1].splitlines()[0]!r} is the '
            '`audit_call_targets.py` call: dropping it is the mutation this '
            'suite exists to catch, and the gate would then run one of the two '
            'checks it was going to run and be green.')


class ArmBehaviourTests(unittest.TestCase):
    """The landed block, run: a silent self-test is as red as a failing one.

    `FoldRetentionTests` holds that the block is in the patch. This holds what
    it does once it is, against the mutation it exists for: a re-cut that keeps
    `|| rc=1` and drops the transcript assertion still applies, still composes,
    still lints, and leaves the **gate** green on the one break the call is here
    for -- `--self-test` no longer dispatching, so the command a person would
    type exits 0 having printed nothing. An exit status alone cannot see that,
    which is why the block greps the transcript as well;
    `ec/tools/test_call_graph_gaps.py` asserts its subprocess's stdout for the
    same reason, and it is the half that carries it there too.

    The block is run on its own rather than through `check_ghidra_tooling()`,
    which would run the whole cheap tier to reach two lines, and against a stub
    rather than the real tool, because the dispatch break cannot be expressed
    without editing `ec/tools/audit_call_targets.py` itself. The stub is what
    the arm runs -- `python3 <tool> <image> --self-test` -- and it ignores both
    arguments, so no image has to be on disk beside it.
    """

    # The self-test that ran, and the transcript it prints. Also the arm's own
    # success path, and what the `cat` in the block exists to keep in the gate
    # log rather than swallow into the scratch dir.
    PASSING = 'print("  ok   a check")\nprint("self-test passed")\n'

    # (what the stub does, the status the arm must return for it, its body).
    # Each row is a row of the mutation table in
    # `docs/findings/audit-call-targets-gate-arm.md`.
    STUBS = (
        ('the self-test ran', 0, PASSING),
        ('`--self-test` no longer dispatches to self_test()', 1,
         'import sys\nsys.exit(0)\n'),
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
            tool = root / 'ec' / 'tools' / 'audit_call_targets.py'
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
    """Neither tool's docstring may claim a place in the gate.

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
    `docs/findings/audit-call-targets-gate-arm.md`, which is where a reader
    comes to land the arm from.

    **The predicate is imported, not reimplemented.** A hand-copied version of
    direction 3's clause reading is a weaker check that passes for reasons the
    real one would not -- an earlier cut of this file tested one regex against
    one phrasing, could not be made to fail, and would have been a case that
    looked like coverage. `claims()` is the authority on what counts as a
    claim, so this asks it rather than agreeing with it by construction, and
    the gate's own checker keeps meaning what it means if its vocabulary moves.
    """
    TOOLS = ('ec/tools/audit_call_targets.py', 'ec/tools/bank_attribution.py')

    def test_neither_docstring_claims_gate_membership(self):
        import ast
        for rel in self.TOOLS:
            with self.subTest(tool=rel):
                docstring = ast.get_docstring(
                    ast.parse((REPO / rel).read_text())) or ''
                found = coverage.claims(docstring)
                self.assertEqual(
                    found, [],
                    f'{rel} claims a place in the gate: {found!r}. Its arm is '
                    f'a tail call in the fold of {PATCH}, not a `case` arm, '
                    'so `check_gate_arm_coverage.py`\'s direction 3 cannot '
                    'satisfy the claim -- it requires a `case` arm -- and the '
                    'cheap tier would go red against a gate edit that works. '
                    'The claim belongs in the patch header and in '
                    'docs/findings/audit-call-targets-gate-arm.md.')


if __name__ == '__main__':
    unittest.main()