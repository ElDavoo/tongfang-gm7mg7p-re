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

**And it has an answer for the state a landing creates.** A patch that has
been applied and committed has by definition stopped applying, so every "must
apply" case above goes red on the day the first landing lands -- and that day
is expected rather than hypothetical, because every header in `docs/ci/` tells
a human how to create it. The patch file is kept after a landing, as a record
of what it was rather than of what is left to do, so each patch is classified
against the committed script into one of four states and each state carries
its own expectation. A landed patch's header is marked `# LANDED in <sha>`,
which is what stops it reading as "apply this" once applying it a second time
would add a second `check_*()` and a second `gate` line. The decision, its
rejected alternative, and the two-step landing procedure are in
`docs/findings/landed-gate-patch-state.md`.

What this is not: it is not in the cheap tier, and it is not per-commit
coverage. `docs/agent-pipeline.md` records that `tools/run-tests.sh` has no
gate call for the same template-copied-file reason, and that stays true. This
is a suite that runs when someone runs the runner.
"""
import difflib
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
    'docs/ci/agent-gates-bank-map-score.patch',
    'docs/ci/agent-gates-0751-writer-census.patch',
    'docs/ci/agent-gates-capture-claims.patch',
    'docs/ci/agent-gates-cross-decoder-disagreement.patch',
    'docs/ci/agent-gates-disasm8051-self-test.patch',
    'docs/ci/agent-gates-findings-frozen.patch',
    'docs/ci/agent-gates-gap-text-check.patch',
    'docs/ci/agent-gates-pin-table-rows.patch',
    'docs/ci/agent-gates-py-source-citations.patch',
    'docs/ci/agent-gates-reassembly-bound-check.patch',
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

# How a landed patch's header says so: `# LANDED in <sha>`, naming the commit
# whose `git apply` put the content in the gate script. The sha is what makes
# it checkable -- a marker naming no commit is a marker the next re-cut
# quietly drops, which is exactly the moment it is for.
#
# **The marker must not contain a `git apply <path>.patch` string.** `GIT_APPLY`
# captures the whole header, so such a line becomes a second apply target and
# `test_each_header_applies_its_own_path` fails on a marker that landed
# correctly. The existing capture already enforces that; the marker only has
# to respect it.
LANDED_MARKER = re.compile(r'^#\s*LANDED in ([0-9a-f]{7,40})\b', re.M)

# The four cells a patch can be in against the committed gate script, and none
# of them undefined. Two facts pick the cell: `git apply --check` says whether
# the patch still applies, and whether the lines it adds are already in the
# file says whether its work is done. Either fact alone is ambiguous -- a
# patch that stopped applying is stale *or* landed, and telling those apart is
# the whole of the work, because today's rule reads the first as the second
# and tells a human to re-cut a patch whose content is in the file and apply
# it again. A patch whose content is already there and which still applies is
# a fourth thing: it would be applied twice.
PREPARED = 'prepared'
LANDED = 'landed'
STALE = 'stale'
DOUBLE_LANDED = 'landed, still applies'


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


def added_lines(text):
    """The lines a patch adds, from its diff body alone.

    `+++ b/…` is a `+` line that names the file rather than contributing to
    it, and a `+` carrying nothing but the newline adds a blank line, so both
    are dropped -- kept, the first would have to appear in the gate script and
    would never, and the second would match anything. Each line is compared
    stripped, so a landing that reindents is not read as a patch that is still
    prepared.
    """
    cut = text.find('diff --git ')
    body = text[cut:] if cut >= 0 else text
    return [line[1:].strip() for line in body.splitlines()
            if line.startswith('+') and not line.startswith('+++')
            and line[1:].strip()]


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True,
                          text=True)


def has_git():
    return shutil.which('git') is not None


@contextmanager
def scratch_tree(gate_text=None):
    """A throwaway repo holding nothing but a copy of the gate script.

    Every case that applies a patch is mutating, and the composition cases
    apply several in sequence, so this is where that happens: a suite that
    patched the real tree would leave a working directory full of half-landed
    gate edits and would have no order to be order-dependent in. Seeded from
    the working-tree file, because that is the file a human's `git apply`
    would meet; `CommittedBaseTests` below is what keeps that seed equal to
    the commit the patches name.

    `copy2` rather than a byte write, because `write_bytes` creates the file
    0644 and every patch in this set carries `… 100755` on its `index` line.
    `git apply` compares the mode of the file it is patching, prints
    `warning: … has type 100644, expected 100755` at every call, and **exits
    0 anyway** -- so the mode bit the patches carry was being carried and
    never exercised, and the only trace was a warning nothing read. Passing
    `gate_text` writes over that copy rather than replacing it, which keeps
    the mode: a truncating open does not change a file's permissions, so the
    synthetic trees below are seeded as the committed one is.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / GATE
        target.parent.mkdir(parents=True)
        shutil.copy2(REPO / GATE, target)
        if gate_text is not None:
            target.write_text(gate_text)
        git('init', '-q', '.', cwd=root)
        yield root


def committed_mode():
    """The mode git has recorded for the gate script, or None without a commit.

    `ls-tree` rather than `stat`, because the mode under test is the one the
    patches' `index` lines were cut against, which is a property of the commit
    and not of whichever checkout the suite happens to be running in. The
    working tree's mode is deliberately not the fallback: `copy2` would copy
    it, so comparing against it asserts that `copy2` copies, which is not the
    claim. Without a commit there is no committed mode to compare, and the
    case holding this says so out loud rather than passing on a tautology.
    """
    listed = git('ls-tree', 'HEAD', '--', GATE, cwd=REPO)
    if listed.returncode != 0 or not listed.stdout.strip():
        return None
    return int(listed.stdout.split()[0], 8) & 0o7777


def apply_patch(tree, patch, *extra):
    return git('apply', *extra, str(REPO / patch), cwd=tree)


def land(tree, patches):
    """Apply each patch in order, returning the first failure or None."""
    for patch in patches:
        done = apply_patch(tree, patch)
        if done.returncode != 0:
            return patch, done
    return None


def state_of(applies, present):
    """The cell two facts put a patch in: four of them, and never None."""
    if applies and present:
        return DOUBLE_LANDED
    if applies:
        return PREPARED
    return LANDED if present else STALE


def classify(patch, gate_text):
    """`(applies, present)` for one patch against one gate script.

    The two halves are deliberately not folded into the cell here: the cases
    below assert on the facts themselves, so a predicate that answered the
    question for them would make the assertions tautological.
    """
    with scratch_tree(gate_text) as tree:
        applies = apply_patch(tree, patch, '--check').returncode == 0
    present = all(line in gate_text
                  for line in added_lines((REPO / patch).read_text()))
    return applies, present


# Classified once per run. The pair cases below would otherwise re-run
# `git apply --check` for every ordered pair they visit, which is most of the
# suite's runtime spent re-deriving an answer that cannot change inside a run.
_CLASSIFIED = {}


def patch_facts(patch):
    """`(applies, present)` for `patch` against the committed gate script."""
    if patch not in _CLASSIFIED:
        _CLASSIFIED[patch] = classify(patch, (REPO / GATE).read_text())
    return _CLASSIFIED[patch]


def prepared_patches():
    """The patches still waiting to be landed, in `PATCHES` order.

    The landed ones are excluded rather than skipped, because the cases that
    compose the set can only ask whether *these* still compose: the content of
    a landed one is already in the seed they are applied to.
    """
    return [p for p in PATCHES if state_of(*patch_facts(p)) == PREPARED]


@contextmanager
def retention_gate(patch, gate_text=None):
    """The gate script to read a patch's retention strings out of, and why not.

    Yields `(path, problem)`. `problem` is '' when there is nothing to say.

    Prepared, that is the scratch tree the patch was applied to, because the
    content is not in the committed file yet and there is nowhere else to look
    for it. Landed, it is the committed file itself: the content went there,
    that is what landing *is*, and a scratch tree seeded from it in that state
    would hold the seed and nothing else. A caller passing its own
    `gate_text` gets that text seeded instead, which is how the synthetic
    landed tree below reaches this branch at all.

    The `problem` is the point of the whole thing. A landed patch does not
    apply, and the two retention cases below used to assert that it did
    before they read anything -- so on the day the first landing lands, the
    one case in this suite that exists to notice a half-landed fold went red
    on the apply and **never looked at the landed file at all**. A fold that
    had lost half its checks would have read exactly the same as a whole one.
    Here the apply is only a problem in the state where applying is the claim.
    """
    facts = (patch_facts(patch) if gate_text is None
             else classify(patch, gate_text))
    if state_of(*facts) == PREPARED:
        with scratch_tree(gate_text) as tree:
            done = apply_patch(tree, patch)
            problem = (f'{patch} no longer applies:\n{done.stderr.strip()}'
                       if done.returncode else '')
            yield tree / GATE, problem
    elif gate_text is None:
        yield REPO / GATE, ''
    else:
        with scratch_tree(gate_text) as tree:
            yield tree / GATE, ''


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

    def test_the_seeded_gate_script_keeps_the_committed_mode(self):
        # The half of "the committed file" that is not its bytes. Every patch
        # in this set whose `index` line exists says `100755`, and the seed
        # used to be created 0644, so `git apply` warned on every single call
        # and returned 0 -- a suite in which the mode the patches carry can
        # only ever be wrong in the direction that still passes.
        expected = committed_mode()
        if expected is None:
            self.skipTest('no HEAD to read the committed mode from; there is '
                          'no mode at the commit to hold the seed to')
        with scratch_tree() as tree:
            seeded = (tree / GATE).stat().st_mode & 0o7777
        self.assertEqual(
            seeded, expected,
            f'scratch_tree() seeds the gate script {oct(seeded)}, and the '
            f'committed one is {oct(expected)}. Every `git apply` here then '
            'prints "has type %s, expected %s" and exits 0, so the mode the '
            'patches carry is exercised only in the direction that passes. '
            'Seed it with `shutil.copy2` (which keeps the mode) rather than '
            'writing the bytes.' % (oct(seeded)[2:], oct(expected)[2:]))


@unittest.skipUnless(has_git(), 'no git on PATH')
class SinglePatchTests(unittest.TestCase):
    """Each patch alone, against the seeded gate script.

    One case per patch rather than four, because the four are not four
    independent checks: they are one check whose *answer* depends on the
    cell, and a case that asserted only `applies` would go red on the day the
    first landing lands, having told a human to re-cut a patch whose content
    is already in the file and apply it a second time. So the expectation
    branches on the cell, and so does the advice.
    """

    def test_each_patch_is_in_a_state_the_suite_has_an_answer_for(self):
        for patch in PATCHES:
            with self.subTest(patch=patch):
                applies, present = patch_facts(patch)
                state = state_of(applies, present)
                if state == PREPARED:
                    self.assertTrue(
                        applies,
                        f'{patch} is in the {PREPARED} cell but does not '
                        f'apply to the committed {GATE}. Re-cut it against '
                        'the current file; the context a hunk needs is '
                        'whatever the file has today, not whatever it had '
                        'when the patch was cut.')
                elif state == LANDED:
                    # The landing is done. What is left to check is that it
                    # is not done twice, and the header's claim is checked in
                    # `HeaderInstructionTests`; asserting the apply here would
                    # be asserting the state that put us in this branch.
                    self.assertFalse(
                        applies,
                        f'{patch} is {LANDED}: its content is already in '
                        f'{GATE} and it still applies. Following its header '
                        'would add a second copy of every line it carries -- a '
                        'second check_*() definition and a second `gate` line, '
                        'and the gate list admits no free anchor for either. '
                        'If this is a re-cut whose content is genuinely still '
                        'needed, take the lines back out of the script, or cut '
                        'the patch against a file that does not have them.')
                elif state == STALE:
                    self.assertTrue(
                        applies,
                        f'{patch} does not apply to the committed {GATE} and '
                        f'none of the lines it adds are in the file either, so '
                        'there is no landing to have happened:\n'
                        f'{_applies_message(patch)}\n'
                        'Its header tells a human to run exactly that. Re-cut '
                        'it against the current file; the context a hunk needs '
                        'is whatever the file has today, not whatever it had '
                        'when the patch was cut.')
                else:
                    self.fail(
                        f'{patch} is {DOUBLE_LANDED}: every line it adds is '
                        f'already in {GATE}, *and* it still applies cleanly. '
                        'Those are the two states that look identical from the '
                        'patch and are not: a landing is expected to stop '
                        'applying, and one that does not means the script and '
                        'the patch disagree about what "landed" is. Following '
                        'the header would add a second copy of every line it '
                        'carries, and `git apply` would not stop it -- it '
                        'prints nothing and exits 0.')


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

    The set these cases walk is the *prepared* one. A landing takes a patch
    out of it, which is what a landing is: its content is in the seed, so
    composing it against that seed would be composing the seed with itself.
    """

    def test_every_ordered_pair_lands(self):
        # Over the *prepared* patches only. A landed one is already in the
        # seed, so asking whether it composes is asking whether the seed
        # composes with itself -- and the honest answer to "what does this
        # suite still have to say about a landed patch" is nothing about
        # ordering, because ordering is what a landing spends.
        prepared = prepared_patches()
        if len(prepared) < 2:
            left = f' ({prepared[0]})' if prepared else ''
            self.skipTest(
                f'only {len(prepared)} patch(es) in the set are still prepared'
                f'{left}, so there is no ordered pair left to compose. This is '
                'the state a tree is in once its landings are done -- the case '
                'has nothing to say, and says that rather than passing on an '
                'empty loop.')
        for first in prepared:
            for second in prepared:
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
        #
        # Once every patch is landed this applies nothing and lints the
        # committed script, which is not a vacuous degradation: that is the
        # check running on the thing a human just landed, which is the moment
        # it has anything to say.
        with scratch_tree() as tree:
            failed = land(tree, prepared_patches())
            self.assertIsNone(failed, _landed_message(failed))
            parsed = subprocess.run(['bash', '-n', str(tree / GATE)],
                                    capture_output=True, text=True)
            self.assertEqual(
                parsed.returncode, 0,
                f'the prepared set applies, but the result does not parse:\n'
                f'{parsed.stderr.strip()}')

    def test_the_landed_result_is_shellcheck_clean(self):
        # Not because a patch should carry a lint fix, but because the gate
        # shellchecks every *.sh under the tree the moment a human lands
        # these, and a prepared patch that lands a warning is a prepared
        # surprise. Same command the cheap tier runs.
        if shutil.which('shellcheck') is None:
            self.skipTest('no shellcheck on PATH')
        with scratch_tree() as tree:
            failed = land(tree, prepared_patches())
            self.assertIsNone(failed, _landed_message(failed))
            linted = subprocess.run(['shellcheck', str(tree / GATE)],
                                    capture_output=True, text=True)
            self.assertEqual(linted.returncode, 0,
                             f'the prepared set lands a shellcheck failure:\n'
                             f'{linted.stdout.strip()}')


@unittest.skipUnless(has_git(), 'no git on PATH')
class FoldTests(unittest.TestCase):
    """The folded patch still carries every check it absorbed, and its gates.

    `check_testdata_index()` came out of its own patch because that patch and
    `check_capture_claims()` could not both be landed, and two more joined the
    same file for the same reason: `check_history_checkouts()`, two folds
    later, and `check_sweep_summary()`, three. Each was cut as its own file
    first and refused by `test_every_ordered_pair_lands` below -- a patch with
    no `gate` line it can insert that composes with the ones already here is
    what each of those cut runs turned out to be, and
    `docs/findings/history-checkouts-gate-wiring.md` is where that saturation
    is measured anchor by anchor. **A fourth fold went the other way**:
    `check_testdata_grader_claims()` joined `agent-gates-testdata-row-claims.patch`
    rather than the file above, because the `gate` line it wanted was at the end
    of the list where that patch's own already sits, and two files here is
    better than one that cannot land beside a fourth. Folding is only the right
    answer while every half is still there: a later re-cut that keeps some
    functions and drops others would apply cleanly, pass every case above, and
    quietly lose a gate. This is the case that says so, and it grows a line per
    fold for the same reason.

    It reads whichever file the patch's state says the content is in -- the
    scratch tree while the patch is prepared, the committed script once it is
    landed -- so it keeps saying this after the landing rather than going red
    on the apply that the landing makes stop working. `LandedStateTests` below
    builds that second state and holds the case against it, so the reading
    has been seen go red before anyone relies on it.
    """

    FOLDED = 'docs/ci/agent-gates-capture-claims.patch'
    REQUIRED = [
        'check_capture_claims() {',
        'check_testdata_index() {',
        'check_history_checkouts() {',
        'check_sweep_summary() {',
        "gate 'capture claims'   check_capture_claims",
        "gate 'testdata index'   check_testdata_index",
        "gate 'history checkouts'  check_history_checkouts",
        "gate 'sweep summary'  check_sweep_summary",
    ]

    # A second fold, into a different file and for the same reason: the `gate`
    # list is saturated at every line a hunk's context can reach, so
    # `check_testdata_grader_claims()` joined the row-claims patch rather than
    # shipping a file of its own. Held here rather than by naming the strings in
    # the one above, because the two files carry different tools and a shared
    # `REQUIRED` would read as if one file carried all of them.
    FOLDED_SECOND = 'docs/ci/agent-gates-testdata-row-claims.patch'
    REQUIRED_SECOND = [
        'check_testdata_row_claims() {',
        'check_testdata_grader_claims() {',
        "gate 'testdata row claims'  check_testdata_row_claims",
        "gate 'testdata grader claims'  check_testdata_grader_claims",
    ]

    def assert_every_line_lands(self, patch, required, absorbed):
        with retention_gate(patch) as (gate, problem):
            self.assertFalse(problem, problem)
            landed = gate.read_text()
        for line in required:
            with self.subTest(patch=patch, line=line):
                # `assertTrue(line in landed, …)` rather than `assertIn`:
                # `assertIn` prints the whole container on failure, and the
                # container is the gate script -- 17 KB of shell ahead of the
                # sentence that says what to do about it.
                self.assertTrue(
                    line in landed,
                    f'{patch} no longer lands {line!r}. That patch has '
                    f'absorbed {absorbed} because the checks could not be '
                    'landed at the same anchors as separate patches. A re-cut '
                    'that keeps some halves and drops others still applies, '
                    'still composes, and still passes every other case here, '
                    'so nothing else in this suite would notice. If the patch '
                    'is already landed, this is saying the landing lost it: '
                    'the string is the one the landed script is supposed to '
                    'carry.')

    def test_every_check_and_every_gate_line_land(self):
        self.assert_every_line_lands(
            self.FOLDED, self.REQUIRED,
            'three others -- agent-gates-testdata-index.patch in #745, the '
            'history-checkouts check in #1033, and the sweep-summary check in '
            '#316')

    def test_the_second_fold_still_lands_both_halves(self):
        self.assert_every_line_lands(
            self.FOLDED_SECOND, self.REQUIRED_SECOND,
            'one other -- check_testdata_grader_claims.py, the index\'s third '
            'column read for what it says the grader prints')


@unittest.skipUnless(has_git(), 'no git on PATH')
class ArmRetentionTests(unittest.TestCase):
    """The disasm8051 patch still lands both halves of *each* tool's change.

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
    never reaches. It reads the committed script once the patch is landed,
    for the reason `FoldTests`' docstring gives -- the arm is what the landed
    script is missing, and a case that stops reading it at the landing has
    stopped watching the one thing it was written to watch.

    **Several tools since issue #50**, folded into this one file rather than
    shipped as a seventh and an eighth, because the free hunks in
    `agent-gates.sh` are already spent
    (`docs/findings/prepared-gate-patches.md`). A fold is
    exactly what can go half-right without anyone noticing: a re-cut that
    lands `data_regions.py`'s two halves and drops `disasm8051.py`'s, or the
    reverse, or lands one tool's and drops both of the others', still
    applies, still composes in every ordered pair, and still
    passes `bash -n` and `shellcheck` -- because the dropped arm is precisely
    what keeps its tool off the `*)` default. So both halves of every tool are
    here, and dropping any one of them is a failure.

    **This is not a count of the tree and must not become one.** Each further
    fold adds a list-entry edit and an arm string; it does not edit the
    sentence above to name a number, and no case here should ever assert how
    many tools the patch carries. What is asserted is the shape -- a list entry
    and a whole arm per tool -- which is a claim the patch can keep making as it
    grows, where "this patch carries N tools" is a value every later fold has to
    edit.
    """

    PATCH = 'docs/ci/agent-gates-disasm8051-self-test.patch'
    # Each arm is one string rather than the two lines the issue names, because
    # `python3 "$tool" --self-test || rc=1` is already in the
    # merge_annotation_shards and grade_0751 arms -- checking it on its own
    # would pass with this patch's arm dropped, which is the exact case this
    # class exists to catch. The list entry is the whole ` \`-continued run
    # because none of the folded tools is the last line in the `for tool in`
    # list: each fold moved the `; do` to the line after, so a re-cut that
    # un-folds them would put `; do` back on a line checked here.
    REQUIRED = [
        'ec/tools/disasm8051.py \\\n'
        '              ec/tools/data_regions.py \\\n'
        '              ec/tools/dsdt_ec_fields.py \\\n'
        '              ec/tools/bank_call_regions.py; do',
        '      *disasm8051.py)\n'
        '        python3 "$tool" --self-test || rc=1\n'
        '        ;;',
        '      *data_regions.py)\n'
        '        python3 "$tool" --check && python3 "$tool" --self-test || rc=1\n'
        '        ;;',
        # The only arm here that passes an argument, because
        # `--check` reads the committed image for its `static_refs*` columns.
        # That makes the two halves inseparable in a way the others are
        # not: dropping this arm does not just lose the mode, it hands the tool
        # to the `*)` default, which passes `--work` and a flag the tool refuses.
        '      *dsdt_ec_fields.py)\n'
        '        python3 "$tool" ec/firmware/GMxMGxx_11.800 --csv --check && \\\n'
        '        python3 "$tool" --self-test || rc=1\n'
        '        ;;',
        # Its body line is the `data_regions.py` arm's, character for character;
        # only the `case` line differs, because each names its own tool. That is
        # why it is spelled out rather than derived from the one above: a single
        # shared string would be satisfied by either arm landing, so a fold that
        # dropped this one would still pass here -- and would hand
        # `bank_call_regions.py` to the `*)` default, which passes
        # `--work "$scratch"` and a flag the tool does not take.
        '      *bank_call_regions.py)\n'
        '        python3 "$tool" --check && python3 "$tool" --self-test || rc=1\n'
        '        ;;',
    ]

    def test_both_the_list_entry_and_the_arm_land(self):
        with retention_gate(self.PATCH) as (gate, problem):
            self.assertFalse(problem, problem)
            landed = gate.read_text()
        for line in self.REQUIRED:
            with self.subTest(line=line):
                # `assertTrue`, not `assertIn` -- see the note in `FoldTests`.
                self.assertTrue(
                    line in landed,
                    f'{self.PATCH} no longer lands {line!r}. Each tool\'s two '
                    'halves are what keep it off the `*)` default arm, and a '
                    're-cut that lands some of the tools and drops the rest '
                    'still applies, so nothing else here would notice. If the '
                    'patch is already landed, this is saying the landing lost '
                    'it -- the tool would be running the `*)` default, which '
                    'passes `--work "$scratch"` and a flag it does not take.')


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

    def test_a_header_says_whether_it_is_landed(self):
        # Checked in both directions, so neither half passes on an empty
        # loop. A prepared patch must not claim to be landed -- that would
        # tell a human its work is done while the content is not in the file
        # -- and a landed one must, because the `git apply` line above it is
        # the rest of the header and it is no longer a thing to do. This is
        # the cost of keeping a patch after landing it, and it is the reason
        # the alternative -- deleting the file -- was rejected; the marker is
        # not free, it is one more thing a landing has to do, and
        # `docs/findings/landed-gate-patch-state.md` records that trade.
        for patch in PATCHES:
            with self.subTest(patch=patch):
                text = header((REPO / patch).read_text())
                marked = LANDED_MARKER.search(text)
                if state_of(*patch_facts(patch)) == LANDED:
                    self.assertIsNotNone(
                        marked,
                        f'{patch} has been landed -- every line it adds is '
                        f'already in {GATE} and it no longer applies -- and '
                        'its header still says "git apply this, and that is '
                        'the whole change". That is the one line in the file '
                        'that is now false, and it is the line a human reads '
                        'first. Add `# LANDED in <sha of the landing commit>` '
                        'to the header; do not add a `git apply` line, which '
                        'the capture above would read as a second target.')
                else:
                    self.assertIsNone(
                        marked,
                        f'{patch} carries the marker `LANDED in '
                        f'{marked.group(1) if marked else ""}` but is still '
                        'prepared, so the marker is wrong rather than the '
                        'header being incomplete. Nothing has landed it, and a '
                        'reader who trusts the marker skips a gate edit that '
                        'is still waiting.')


@unittest.skipUnless(has_git(), 'no git on PATH')
@unittest.skipUnless(has_git(), 'no git on PATH')
class LandedStateTests(unittest.TestCase):
    """The landed state, built here, because nobody has watched it go red.

    A landed tree is a real state with a real answer, and every case above
    only reaches it once something has actually been applied and committed --
    which is a human's `git apply` and a commit, and the first of those has
    not happened yet. So the state is built instead, in a `tempfile`, and the
    production helpers are driven over it: the classifier says `landed`, and
    the retention case reads the landed text rather than a tree the patch did
    not apply to.

    **The fixture is synthetic on purpose.** Borrowing the real
    `agent-gates-capture-claims.patch` cannot work, and the reason is the
    point: in a tree where that patch is already landed, applying it to the
    committed script is impossible -- which is the very state this case exists
    to describe. A fixture is the only pre-image that is the same in every
    state, and it is the `HeaderParseTests` shape for the same reason, one
    bad assumption away from passing vacuously.

    The half-landed case is the discipline
    `docs/findings/prepared-gate-patches.md` already records for this suite:
    a case nobody has seen go red is worth
    nothing. It lands the fixture's first hunk and drops its second, which is
    a landing that went half-right -- it still applies, it still composes, and
    the functions it defines are no longer in the `gate` list, so nothing runs
    them.
    """

    # A seed with two widely separated insertion points, so `difflib` cuts the
    # patch into two hunks rather than one. Seven unchanged lines is the most
    # that can separate two `n=3` context windows without them merging.
    SEED = """# a synthetic gate script

check_doc_links() {
  true
}

gate 'python syntax'  check_python_syntax
gate 'shellcheck'  check_shellcheck
gate 'doc links'  check_doc_links
gate 'doc patch refs'  check_doc_patch_refs
gate 'ghidra tooling'  check_ghidra_tooling
gate 'findings frozen'  check_findings_frozen
gate 'conflict markers'  check_no_conflict_markers
gate 'append logs'  check_no_append_logs
gate 'suite table'  test_readme_suite_table

for check in "${GATES[@]}"; do
  "$check" || rc=1
done
exit "$rc"
"""
    FUNCTIONS = """check_synthetic_one() {
  true
}

check_synthetic_two() {
  true
}

"""
    GATE_LINES = """gate 'synthetic one'  check_synthetic_one
gate 'synthetic two'  check_synthetic_two
"""
    # Two per hunk, so dropping either hunk loses exactly two and the case can
    # say which hunk went rather than only that something did.
    REQUIRED = [
        'check_synthetic_one() {',
        'check_synthetic_two() {',
        "gate 'synthetic one'  check_synthetic_one",
        "gate 'synthetic two'  check_synthetic_two",
    ]

    # The two insertion points, as whole lines. Named rather than inlined
    # because `setUpClass` asserts each is in the seed before replacing it: a
    # seed edited under one of them would otherwise build a landed script
    # identical to the seed, and every case below would pass on a patch that
    # adds nothing.
    ANCHOR_FUNCTION = 'check_doc_links() {\n  true\n}\n'
    ANCHOR_GATE = "gate 'suite table'  test_readme_suite_table\n"

    @classmethod
    def setUpClass(cls):
        # The patch is cut from the seed rather than transcribed, so it applies
        # by construction in any state of the repository and any of the lines
        # above can be edited without a second cut to keep in step.
        for anchor in (cls.ANCHOR_FUNCTION, cls.ANCHOR_GATE):
            if anchor not in cls.SEED:
                raise AssertionError(
                    f'the fixture seed no longer holds {anchor!r}, so the '
                    'landed script this class builds would be identical to the '
                    'seed and every case in it would pass on a patch that '
                    'adds nothing')
        landed = cls.SEED.replace(cls.ANCHOR_FUNCTION,
                                  cls.ANCHOR_FUNCTION + cls.FUNCTIONS, 1)
        landed = landed.replace(cls.ANCHOR_GATE,
                                cls.ANCHOR_GATE + cls.GATE_LINES, 1)
        cls.landed = landed
        cls.patch = (f'diff --git a/{GATE} b/{GATE}\n'
                     + ''.join(difflib.unified_diff(
                         cls.SEED.splitlines(True), landed.splitlines(True),
                         fromfile='a/' + GATE, tofile='b/' + GATE)))

    def _seeded(self, gate_text):
        """A scratch tree holding `gate_text`, and this class's patch in it."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        root = Path(tmp)
        target = root / GATE
        target.parent.mkdir(parents=True)
        target.write_text(gate_text)
        patch = root / 'synthetic.patch'
        patch.write_text(self.patch)
        git('init', '-q', '.', cwd=root)
        return root, patch

    def test_the_applied_patch_classifies_as_landed_not_stale(self):
        # The classifier in one assertion. A patch whose content is already in
        # the file and which no longer applies is *landed*; read by the old
        # rule -- applies or it does not -- that is indistinguishable from a
        # template re-copy, and the advice is to re-cut it and apply it again.
        root, patch = self._seeded(self.SEED)
        self.assertEqual(
            state_of(*classify(patch, self.SEED)), PREPARED,
            'the fixture patch does not apply to the seed it was cut from, so '
            'this case is not building what it claims to build')
        applied = git('apply', str(patch), cwd=root)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        landed = (root / GATE).read_text()
        self.assertEqual(landed, self.landed, 'applying the fixture patch did '
                         'not reproduce the landed text it was cut for')
        applies, present = classify(patch, landed)
        self.assertEqual(
            state_of(applies, present), LANDED,
            f'the applied patch classifies as {state_of(applies, present)} '
            f'(applies={applies}, its lines already present={present}). '
            'Applying a patch is what landing one is, so the content is there '
            'by construction and the state has to be `landed`; `stale` is what '
            'would tell a human to re-cut a patch whose content is in the '
            'file and apply it a second time.')

    def test_the_retention_check_reads_the_landed_script(self):
        # Seeded only to get the patch onto disk at a path `retention_gate`
        # can read; the landed branch builds its own tree from `self.landed`
        # and never applies it, which is the whole point of the state.
        _, patch = self._seeded(self.SEED)
        with retention_gate(patch, self.landed) as (gate, problem):
            self.assertFalse(
                problem, problem or
                'a patch in the landed state raised a problem here. The apply '
                'is only a problem while applying is the claim; past that the '
                'content is where the landing put it.')
            landed = gate.read_text()
        for line in self.REQUIRED:
            with self.subTest(line=line):
                # `assertTrue`, not `assertIn` -- the container is the gate
                # script, and the sentence is what a reader needs.
                self.assertTrue(
                    line in landed,
                    f'the landed script is missing {line!r}, which is the '
                    'string the retention case exists to hold. This is the '
                    'check reading a landed file for the first time, and if it '
                    'is reading something else it finds nothing here.')

    def test_a_half_landed_patch_is_caught(self):
        # First hunk only: the two functions, without the `gate` lines that
        # call them. Both facts are asserted before the retention case is held
        # against the result, because a case that cannot fail is worth nothing
        # and one that fails for the wrong reason is worse.
        hunks = [m.start() for m in re.finditer(r'^@@ ', self.patch, re.M)]
        self.assertEqual(
            len(hunks), 2,
            f'the fixture patch has {len(hunks)} hunk(s) where this case '
            'needs 2 to halve. Its two insertion points are too close for '
            '`difflib` to cut them apart, so the half-landing below would be '
            'a whole one.')
        half = self.patch[:hunks[1]]
        root, patch = self._seeded(self.SEED)
        (root / 'half.patch').write_text(half)
        done = git('apply', str(root / 'half.patch'), cwd=root)
        self.assertEqual(
            done.returncode, 0,
            f'the first hunk of the fixture patch does not apply alone:\n'
            f'{done.stderr.strip()}')
        landed = (root / GATE).read_text()
        for line in self.REQUIRED[:2]:
            with self.subTest(line=line):
                self.assertIn(
                    line, landed,
                    f'the first hunk did not land {line!r}, so this is not '
                    'the half-landing this case is about')
        for line in self.REQUIRED[2:]:
            with self.subTest(line=line):
                self.assertNotIn(
                    line, landed,
                    f'the first hunk already carried {line!r}, so dropping the '
                    'second hunk loses nothing and this case would be '
                    'checking a landing that is not half-right')
        with retention_gate(patch, landed) as (gate, problem):
            self.assertFalse(problem, problem)
            read_back = gate.read_text()
        missing = [line for line in self.REQUIRED if line not in read_back]
        self.assertEqual(
            missing, self.REQUIRED[2:],
            f'the retention case found {missing!r} missing in a half-landed '
            'patch, where it must find exactly the `gate` lines the dropped '
            'hunk carried. Either it is not reading the file it is supposed '
            'to read, or the halves are not where this case thinks they are.')


def _landed_message(failed):
    """The `git apply` output of the patch that failed, with its name."""
    if failed is None:
        return ''
    patch, done = failed
    return f'{patch} failed:\n{done.stderr.strip()}'


def _applies_message(patch):
    """What `git apply --check` says about one patch.

    Re-derived rather than carried out of `classify()`, so that the facts do
    not have to hold git's prose around them; only a failing branch asks for
    it, so the extra apply costs nothing a passing run notices.
    """
    with scratch_tree() as tree:
        done = apply_patch(tree, patch, '--check')
    return done.stderr.strip()


if __name__ == '__main__':
    unittest.main()
