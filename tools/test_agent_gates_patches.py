#!/usr/bin/env python3
"""Offline checks for the prepared gate patches in `docs/ci/`.

`docs/ci/agent-gates-*.patch` is the shape `CLAUDE.md` and
`docs/agent-pipeline.md` both call for: `.github/scripts/agent-gates.sh` is
copied from the agent-pipeline template and the pipeline's push token has no
`workflow` scope, so a branch editing it fails at the *end* of a PR rather than
at the start. The gate changes a human wants are prepared beside the file
instead, and a human lands them with `git apply` when they are ready.

That arrangement has a failure mode with nothing watching it. Every patch
carries the same instruction in its own header -- `git apply
docs/ci/agent-gates-<name>.patch`, "and that is the whole change" -- and the
instruction only stays true while the file it edits stays put. A template
re-copy, or another item-8-style landing in `check_ghidra_tooling()`, moves
the context lines a hunk was cut against, and the patch stops applying. The
discoverer of that was a person reaching for `git apply`, which is the outcome
this suite exists to prevent.

The set also has to *compose*. Two patches that insert at the same anchor in
the same function cannot both be landed, in either order, and neither is stale
-- each applies cleanly alone. That is what happened to
`agent-gates-capture-claims.patch` and `agent-gates-testdata-index.patch`, and
it is why the two are one file now.

So this checks three things, all against the committed
`.github/scripts/agent-gates.sh`: that the set on disk is the set named here,
that every patch applies alone, and that they compose in any order and yield
shell that still parses. It runs `git`, which the cheap tier already requires
(`verify_reassembly.py --verify-provenance` needs a full clone), and every
mutation happens in a `tempfile` scratch tree -- nothing here writes to
`.github/`, because `.github/` is what the patches exist to avoid editing.

What this is not: it is not in the cheap tier, and it is not per-commit
coverage. `docs/agent-pipeline.md` records that `tools/run-tests.sh` has no
gate call for the same template-copied-file reason, and that stays true. This
is a suite that runs when someone runs the runner.
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
CI = REPO / 'docs' / 'ci'
GATE = '.github/scripts/agent-gates.sh'

# The set, held here. A patch cannot be added or deleted without this noticing,
# which is the `tools/test_readme_suite_table.py` arrangement for the same
# reason: a directory the runner globs is picked up silently by having a file
# committed, and the index that says what is *supposed* to be there is prose
# nothing checks. The reasons each of these three is one file and not two are
# in docs/findings/prepared-gate-patches.md.
PATCHES = [
    'docs/ci/agent-gates-0751-self-test.patch',
    'docs/ci/agent-gates-capture-claims.patch',
    'docs/ci/agent-gates-disasm8051-self-test.patch',
    'docs/ci/agent-gates-gap-text-check.patch',
    'docs/ci/agent-gates-testdata-row-claims.patch',
]

# `agent-gates-deep-schedule.yml` is deliberately not in this set and is not
# matched by the discovery glob below. It is a `cp` into
# `.github/workflows/`, not a `git apply`, so it has no pre-image to go stale
# against and no order relative to the others; docs/agent-pipeline.md item 1
# carries its own `cp` line across a re-copy.

# A header's instruction to the human, captured rather than prose-matched:
# `git apply <path>.patch`. The path is the claim under test, so it is the
# path this checks.
GIT_APPLY = re.compile(r'git apply (\S+\.patch)')


def discover_patches():
    """The `docs/ci/agent-gates-*.patch` files on disk, relative to the repo."""
    return sorted(p.relative_to(REPO).as_posix()
                  for p in CI.glob('agent-gates-*.patch'))


def header(text):
    """The comment block above the first `diff --git` -- the part a human reads.

    A patch's header is every line before the diff proper, each starting with
    `#`. Taking the text before `diff --git` rather than filtering on `#` means
    a header that grew an uncommented line still parses, and the
    `GIT_APPLY` cases below say so rather than reading as an empty header that
    happens to be clean.
    """
    cut = text.find('diff --git ')
    return text if cut < 0 else text[:cut]


def apply_targets(text):
    """Every path the header tells a human to `git apply`, in order."""
    return GIT_APPLY.findall(text)


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True,
                          text=True)


def has_git():
    return shutil.which('git') is not None


@contextmanager
def scratch_tree():
    """A throwaway repo holding nothing but a copy of the gate script.

    Every case that applies a patch is mutating, and the composition cases
    apply several in sequence, so this is where that happens: a suite that
    patched the real tree would leave a working directory full of half-landed
    gate edits and would have no order to be order-dependent in. Seeded from
    the working-tree file, because that is the file a human's `git apply`
    would meet; `CommittedBaseTests` below is what keeps that seed equal to
    the commit the patches name.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / GATE
        target.parent.mkdir(parents=True)
        target.write_bytes((REPO / GATE).read_bytes())
        git('init', '-q', '.', cwd=root)
        yield root


def apply_patch(tree, patch, *extra):
    return git('apply', *extra, str(REPO / patch), cwd=tree)


def land(tree, patches):
    """Apply each patch in order, returning the first failure or None."""
    for patch in patches:
        done = apply_patch(tree, patch)
        if done.returncode != 0:
            return patch, done
    return None


class HeaderParseTests(unittest.TestCase):
    """The header parse, on inline text.

    Without these the cases below are one bad regex away from passing
    vacuously -- a parse that found nothing matches a header that names no
    path, which is the same defect as a run that found nothing. That is the
    §14b shape the runner's empty-discovery guard and this suite's set checks
    both exist for.
    """

    def test_the_header_stops_at_the_diff(self):
        text = '\n'.join([
            '# run this:',
            '#   git apply docs/ci/a.patch',
            '',
            'diff --git a/f b/f',
            '--- a/f',
            '+++ b/f',
            '@@ -1 +1 @@',
            '+# git apply docs/ci/not-the-header.patch',
        ])
        self.assertEqual(apply_targets(header(text)), ['docs/ci/a.patch'])

    def test_several_instructions_are_all_captured(self):
        text = '# git apply docs/ci/a.patch\n# not: git apply docs/ci/b.patch\n'
        self.assertEqual(apply_targets(header(text)),
                         ['docs/ci/a.patch', 'docs/ci/b.patch'])

    def test_a_header_naming_no_path_names_no_path(self):
        # The other failure direction: a rewritten header that dropped the
        # instruction. This has to read as empty rather than as clean.
        self.assertEqual(apply_targets(header('# just prose\n')), [])

    def test_a_patch_with_no_diff_yields_its_whole_text(self):
        self.assertEqual(apply_targets(header('# git apply a.patch\n')), ['a.patch'])


class PatchSetTests(unittest.TestCase):
    """The set on disk against the set named here, both directions."""

    def test_every_patch_on_disk_is_listed(self):
        extra = sorted(set(discover_patches()) - set(PATCHES))
        self.assertFalse(
            extra,
            f'{len(extra)} patch(es) in docs/ci/ are not in this suite\'s '
            f'PATCHES list:\n  ' + '\n  '.join(extra) +
            '\nA new one is picked up silently by the glob, and this file is '
            'the only place that says what the set is. Add it here, and the '
            'cases below start checking it.')

    def test_every_listed_patch_is_on_disk(self):
        gone = sorted(set(PATCHES) - set(discover_patches()))
        self.assertFalse(
            gone,
            f'{len(gone)} patch(es) in this suite\'s PATCHES list are not in '
            f'docs/ci/:\n  ' + '\n  '.join(gone) +
            '\nEither the file was renamed, or it was folded into another and '
            'this list did not follow. The stale entry would have the cases '
            'below checking a file that is not there.')


class CommittedBaseTests(unittest.TestCase):
    """The seed is the committed file, and the patches name that commit.

    Everything below checks a patch against a copy of
    `.github/scripts/agent-gates.sh`. If that copy is not the committed file,
    the checks quietly stop being what they claim -- a template re-copy or a
    half-landed patch in a working tree would be measured instead, and the
    whole suite would agree with it.
    """

    def setUp(self):
        if not (REPO / '.git').exists():
            self.skipTest('no .git beside the repository; nothing to compare '
                          'the gate script against')
        if not has_git():
            self.skipTest('no git on PATH')
        self.head = git('show', f'HEAD:{GATE}', cwd=REPO)

    def test_the_gate_script_is_readable(self):
        self.assertEqual(self.head.returncode, 0, self.head.stderr)

    def test_the_working_tree_gate_script_is_the_committed_one(self):
        # A dirty `.github/scripts/agent-gates.sh` is the one state that makes
        # every case below measure something other than what it names. It is
        # also the state `CLAUDE.md` and this repository's own pipeline rules
        # say not to be in, so it should be a loud failure rather than a
        # different baseline.
        if self.head.returncode != 0:
            self.skipTest('no HEAD to compare against')
        self.assertEqual(
            (REPO / GATE).read_bytes(), self.head.stdout.encode(),
            f'{GATE} differs from {GATE} at HEAD. The patches are cut against '
            'the committed file and this suite seeds its scratch trees from '
            'the working-tree one, so a local edit here silently changes what '
            'every other case here measures. Commit it and re-cut the patches, '
            'or drop the edit.')


@unittest.skipUnless(has_git(), 'no git on PATH')
class SinglePatchTests(unittest.TestCase):
    """Each patch alone, against the seeded gate script."""

    def test_each_patch_applies_on_its_own(self):
        # The header's own claim, one patch at a time. This is the case that
        # catches a template re-copy: the hunk's context is gone and
        # `git apply` says so here instead of at a human's `git apply`.
        for patch in PATCHES:
            with self.subTest(patch=patch):
                with scratch_tree() as tree:
                    done = apply_patch(tree, patch, '--check')
                self.assertEqual(
                    done.returncode, 0,
                    f'{patch} does not apply to the committed {GATE}:\n'
                    f'{done.stderr.strip()}\n'
                    'Its header tells a human to run exactly that. Re-cut it '
                    'against the current file; the context a hunk needs is '
                    'whatever the file has today, not whatever it had when the '
                    'patch was cut.')


@unittest.skipUnless(has_git(), 'no git on PATH')
class CompositionTests(unittest.TestCase):
    """The set lands together, in any order, and yields shell that parses.

    `agent-gates-capture-claims.patch` and the
    `agent-gates-testdata-index.patch` it absorbed were each applicable alone
    and could not be applied after one another in either order: same anchor
    for the function, same anchor for the `gate` line, and a gate list short
    enough that re-anchoring collides identically. So the order is the thing
    under test, and recording it is not the fix -- a human would have to know
    it, and a reader of the headers has no way to infer it. Every ordered pair
    is checked, so no order has to be written down anywhere.
    """

    def test_every_ordered_pair_lands(self):
        for first in PATCHES:
            for second in PATCHES:
                if first == second:
                    continue
                with self.subTest(first=first, second=second):
                    with scratch_tree() as tree:
                        failed = land(tree, [first, second])
                    self.assertIsNone(
                        failed,
                        f'{first} and {second} cannot both be landed, in that '
                        'order.\n' + _landed_message(failed) +
                        '\nTwo patches editing one region cannot both be '
                        'independently applicable: whichever lands first '
                        'inserts a line between the other\'s leading and '
                        'trailing context. They have to ship as one patch.')

    def test_the_whole_set_lands_and_still_parses(self):
        # A patch that applies but yields broken shell is still wrong, and
        # `git apply` will not tell you. `bash -n` is the cheap half of that;
        # the gate's own `shellcheck` is the rest, and it runs over this file
        # the moment the patches land, with no edit here.
        with scratch_tree() as tree:
            failed = land(tree, PATCHES)
            self.assertIsNone(failed, _landed_message(failed))
            parsed = subprocess.run(['bash', '-n', str(tree / GATE)],
                                    capture_output=True, text=True)
            self.assertEqual(
                parsed.returncode, 0,
                f'the full set applies, but the result does not parse:\n'
                f'{parsed.stderr.strip()}')

    def test_the_landed_result_is_shellcheck_clean(self):
        # Not because a patch should carry a lint fix, but because the gate
        # shellchecks every *.sh under the tree the moment a human lands
        # these, and a prepared patch that lands a warning is a prepared
        # surprise. Same command the cheap tier runs.
        if shutil.which('shellcheck') is None:
            self.skipTest('no shellcheck on PATH')
        with scratch_tree() as tree:
            failed = land(tree, PATCHES)
            self.assertIsNone(failed, _landed_message(failed))
            linted = subprocess.run(['shellcheck', str(tree / GATE)],
                                    capture_output=True, text=True)
            self.assertEqual(linted.returncode, 0,
                             f'the full set lands a shellcheck failure:\n'
                             f'{linted.stdout.strip()}')


@unittest.skipUnless(has_git(), 'no git on PATH')
class FoldTests(unittest.TestCase):
    """The folded patch still carries both of the checks it absorbed.

    `check_testdata_index()` came out of its own patch because that patch and
    `check_capture_claims()` could not both be landed. Folding is only the
    right answer while both halves are still there: a later re-cut that keeps
    the one function and drops the other would apply cleanly, pass every case
    above, and quietly lose a gate. This is the case that says so.
    """

    FOLDED = 'docs/ci/agent-gates-capture-claims.patch'
    REQUIRED = [
        'check_capture_claims() {',
        'check_testdata_index() {',
        "gate 'capture claims'   check_capture_claims",
        "gate 'testdata index'   check_testdata_index",
    ]

    def test_both_checks_and_both_gate_lines_land(self):
        with scratch_tree() as tree:
            done = apply_patch(tree, self.FOLDED)
            self.assertEqual(done.returncode, 0, done.stderr)
            landed = (tree / GATE).read_text()
        for line in self.REQUIRED:
            with self.subTest(line=line):
                self.assertIn(
                    line, landed,
                    f'{self.FOLDED} no longer lands {line!r}. That patch '
                    'absorbed agent-gates-testdata-index.patch because the two '
                    'could not both be landed at the same anchors; a re-cut '
                    'that keeps one half and drops the other still applies, so '
                    'nothing else here would notice.')


@unittest.skipUnless(has_git(), 'no git on PATH')
class ArmRetentionTests(unittest.TestCase):
    """The disasm8051 patch still lands both halves of its change.

    Every other patch here is one function and one `gate` line, or one tool
    line and one arm, and every case above checks that the patch *applies*.
    None of them checks that it applies whole. For
    `agent-gates-disasm8051-self-test.patch` that gap is not academic: a re-cut
    that kept the tool-list line and dropped the `case` arm would apply
    cleanly, pass every other case in this suite, and hand the tool back to
    the `*)` default -- which is `--work "$scratch" --check` and `--self-test`,
    three flags `--self-test` does not take. That is the whole reason the arm
    exists, and it is the reason the same is checked in both directions here:
    a patch that dropped the list entry instead would carry an arm the loop
    never reaches.
    """

    PATCH = 'docs/ci/agent-gates-disasm8051-self-test.patch'
    # The arm is one string rather than the two lines the issue names, because
    # `python3 "$tool" --self-test || rc=1` is already in the
    # merge_annotation_shards and grade_0751 arms -- checking it on its own
    # would pass with this patch's arm dropped, which is the exact case this
    # class exists to catch.
    REQUIRED = [
        'ec/tools/disasm8051.py; do',
        '      *disasm8051.py)\n'
        '        python3 "$tool" --self-test || rc=1\n'
        '        ;;',
    ]

    def test_both_the_list_entry_and_the_arm_land(self):
        with scratch_tree() as tree:
            done = apply_patch(tree, self.PATCH)
            self.assertEqual(done.returncode, 0, done.stderr)
            landed = (tree / GATE).read_text()
        for line in self.REQUIRED:
            with self.subTest(line=line):
                self.assertIn(
                    line, landed,
                    f'{self.PATCH} no longer lands {line!r}. Its two halves are '
                    'what keep disasm8051.py off the `*)` default arm, and a '
                    're-cut that lands one without the other still applies, '
                    'so nothing else here would notice.')


class HeaderInstructionTests(unittest.TestCase):
    """Each header names its own path, in a `git apply` line that matches it.

    The issue this suite answers is that the instruction in each header should
    be true. The applying cases above check the `git apply` part of it; this
    checks that the path in the instruction is the file the reader is holding,
    which is the half a rename or a fold breaks.
    """

    def test_each_header_applies_its_own_path(self):
        for patch in PATCHES:
            with self.subTest(patch=patch):
                text = (REPO / patch).read_text()
                named = apply_targets(header(text))
                self.assertTrue(
                    named,
                    f'{patch} names no `git apply docs/ci/...` line in its '
                    'header. That line is the whole deliverable -- a human '
                    'lands this by copying it -- and a header without one '
                    'leaves the prepared change with no instruction attached.')
                self.assertEqual(
                    sorted(set(named)), [patch],
                    f'{patch} tells a human to apply {sorted(set(named))}, '
                    f'which is not the file they are holding. A header that '
                    'names another patch is worse than one that names none: '
                    'it reads as a working instruction and lands the wrong '
                    'gate edit, or none.')


def _landed_message(failed):
    """The `git apply` output of the patch that failed, with its name."""
    if failed is None:
        return ''
    patch, done = failed
    return f'{patch} failed:\n{done.stderr.strip()}'


if __name__ == '__main__':
    unittest.main()
