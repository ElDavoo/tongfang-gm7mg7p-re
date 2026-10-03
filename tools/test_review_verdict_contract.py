#!/usr/bin/env python3
"""The review stage's two contracts, read out of the committed workflow.

`.github/workflows/agent-review.yml` decides two things, and until now
nothing committed held either of them.

**The stuck hand-off.** The `Reject` step's `MAX_REJECTIONS` branch adds
`agent:stuck` and never removes the `agent:queued` the first rejection added, so
an issue rejected twice carries both -- while `docs/agent-pipeline.md` says the
second rejection "gets `agent:stuck` instead", and the comment the branch posts
tells a human to remove `agent:stuck` and add `agent:queued`, which is an
instruction that is wrong for precisely this state. The one-line fix is prepared
at `docs/ci/agent-review-reject-stuck-label.patch` rather than landed, because
`.github/` is copied from the agent-pipeline template and the pipeline's push
token has no `workflow` scope.

**The verdict matrix.** `Unpack the verdict` derives two booleans with jq and
three steps branch on them, and the pairing is what makes the review's output
mean anything: a verdict has to run exactly one of Approve, Request changes or
Reject, because two of them would post two reviews on one pull request and none
of them would leave the issue in a state the next stage can read.

**Both are extracted from the committed text; neither is transcribed here.** A
suite carrying its own copy of `(.approved and (.rejected | not))` would keep
passing after the workflow's copy changed, which is the gap this closes, so
every rule below reads its subject out of the file. The negative controls at
the foot exist for the other direction: an extractor that quietly stopped
matching would leave a green run that had read nothing, which looks exactly
like a clean tree.

**The suite is green in both states of the patch**, so it never lands a red
gate -- the cheapest way to make a gate get switched off, as
`docs/agent-pipeline.md` puts it. `RejectionStateTests` classifies the
committed file against the patch by the two-fact rule
`tools/test_agent_gates_patches.py` uses (`git apply --check` in a scratch tree
says whether it still applies; whether its added lines are already present says
whether the work is done) and each of the four cells carries its own
expectation. The label hand-off is then read from wherever that cell says the
content is: the patched tree while the patch is prepared, the committed file
once it is landed.

**What this is not.** Nothing here has been run against GitHub. No rejection
has been performed, no label observed on a live issue, and no verdict issued by
the review stage; every claim is about the committed text and what `jq` and
`git apply` say about it. Deciding a verdict needs a real review run, which is
the gap #405 recorded and this does not close. The workflow is copied from a
template, so a re-copy is the likely way for any of it to change; that is
exactly what the extraction is for.

No count is asserted anywhere: not the fixtures, not the steps, not the number
of conditions. What is held is the property -- exclusivity -- plus each
fixture's step by name, so adding a fixture is a row and not an edit to a
number every later case has to move.
"""
import contextlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
REVIEW = '.github/workflows/agent-review.yml'
PATCH = 'docs/ci/agent-review-reject-stuck-label.patch'

# The four `approved`/`rejected` pairs a verdict can carry. Both booleans true
# is in the set on purpose rather than as a fifth thing to note: it is the row
# a later edit to the `approved` expression breaks first, because `approved`
# deliberately reads a verdict that sets both as a rejection.
FIXTURES = {
    (True, False): 'Approve',
    (False, True): 'Reject',
    (True, True): 'Reject',
    (False, False): 'Request changes',
}

# The three steps whose `if:` between them decide what the review did. Named
# rather than counted: a fourth terminal step added later is a new case here,
# not an edit to a count.
TERMINAL_STEPS = ('Approve', 'Request changes', 'Reject')

# The output names `Unpack the verdict` writes and the three conditions read.
# `off_mission` is extracted alongside the two the contract is about, because
# the third `jq` line sits between them in the same block and a rename there
# should be noticed rather than skipped over.
OUTPUTS = ('approved', 'rejected', 'off_mission')

# Indentation is `[ \t]*` and never `\s*` throughout this file. `\s` matches a
# newline, so under `re.M` a `\s*` capture of the indentation of a line also
# swallows the line break in front of it -- and every cut below is a cut *by
# indentation*, so an indent carrying its own newline compares unequal to
# every line after the first and the cut silently runs to the end of the step.
# The class is spelled out at each use rather than factored into one constant
# because a shared name for it would invite the `\s*` back.
STEP = re.compile(r'^(?P<indent>[ \t]*)- name: (?P<name>.+?)\n'
                  r'(?P=indent)  if: (?P<cond>.+?)[ \t]*$', re.M)

# The `jq -r` program behind one output, as the workflow writes it:
# `echo "approved=$(jq -r '<program>' <<<"$OUT")"`.
JQ_OUTPUT = re.compile(r'echo "(?P<name>\w+)='
                       r'\$?\(jq -r \'(?P<program>.*?)\' <<<"\$OUT"\)')

# The stuck branch's own test, and the label call inside it. The branch is cut
# by indentation from the `else`/`fi` at its own level rather than by counting
# lines, so a comment inserted above it moves the branch without moving the
# branch.
STUCK_TEST = re.compile(r'^(?P<indent>[ \t]*)if \[ "\$rejections" -ge '
                        r'"\$MAX_REJECTIONS" \]; then[ \t]*$', re.M)

# `steps.unpack.outputs.approved == 'true'` and its `!=` and `&&` forms. The
# whole grammar, deliberately: `if_condition` refuses anything outside it
# rather than guessing, because a guessed truth value is the one failure a
# reviewer cannot see in a green run.
CONDITION = re.compile(r"^steps\.(?P<step>[\w-]+)\.outputs\.(?P<name>\w+) "
                       r"(?P<op>==|!=) '(?P<value>[^']*)'$")

# The four cells a patch can be in against the committed workflow, named as
# `tools/test_agent_gates_patches.py` names them because it is the same
# two-fact rule and a reader who has met one has met the other.
PREPARED = 'prepared'
LANDED = 'landed'
STALE = 'stale'
DOUBLE_LANDED = 'landed, still applies'

# How a landed patch's header says so: `# LANDED in <sha>`, naming the commit
# whose `git apply` put the content in the workflow. The sha is what makes it
# checkable -- a marker naming no commit is a marker the next re-cut quietly
# drops, which is exactly the moment it is for. Read from the header alone,
# below, because the same marker inside a diff body would be a comment about a
# patch rather than a claim about this one.
LANDED_MARKER = re.compile(r'^#\s*LANDED in ([0-9a-f]{7,40})\b', re.M)


class ExtractionError(AssertionError):
    """A rule could not find its subject in the text it was handed.

    An `AssertionError` so a case that forgot to guard an extraction fails
    loudly rather than passing on `None`; the message is what a reader needs,
    so every raise names the file, the step and the shape that was expected.
    """


def read_review():
    """The committed workflow, as text. The subject of every rule below."""
    return (REPO / REVIEW).read_text(encoding='utf-8')


def step_block(text, name):
    """The `run:` body of the named step, as text.

    Scoped to the step rather than searched for globally because both subjects
    this suite reads -- the verdict unpacking and the stuck branch -- live
    inside one, and a `gh issue edit --remove-label` line anywhere else in the
    file would satisfy a global search for the same string. The block ends at
    the first line at or left of the step's own indentation, which is where
    GitHub's YAML puts the next key.
    """
    for match in re.finditer(r'^(?P<indent>[ \t]*)- name: (?P<name>.+?)[ \t]*$',
                             text, re.M):
        if match.group('name').strip() != name:
            continue
        indent = match.group('indent')
        rest = text[match.end():]
        # The block ends at the first line indented no further than the step's
        # own `-`, which is where GitHub's YAML puts the next key of the same
        # sequence. Blank lines do not end it: a `run: |` block ends with one.
        end, at = len(rest), 0
        for line in rest.splitlines(True):
            if line.strip() and len(line) - len(line.lstrip()) <= len(indent):
                end = at
                break
            at += len(line)
        body = rest[:end]
        # The `run:` key sits two columns in from the `- name:`, and its block
        # scalar is everything below it at that key's own indentation.
        run = body.find(f'\n{indent}  run: |')
        if run < 0:
            raise ExtractionError(
                f'{REVIEW} has a step named {name!r} with no `run: |` block in '
                'it. The stuck branch and the verdict unpacking are read from '
                'that block, so a step that lost it is a change to this '
                'suite\'s subject and not something to skip past.')
        return body[run + 1:]
    raise ExtractionError(
        f'{REVIEW} has no step named {name!r}. The three terminal steps and the '
        'unpacking step are located by name because they are what the verdict '
        'contract is about; one renamed leaves nothing to hold.')


def verdict_programs(text):
    """`{output name: jq program}` from the `Unpack the verdict` step.

    Read from the step rather than the whole file, and every name in
    `OUTPUTS` must be found: an extractor that returned the programs it did
    find would go on to run the matrix over a half-read subject and report it
    clean.
    """
    block = step_block(text, 'Unpack the verdict')
    found = {m.group('name'): m.group('program')
             for m in JQ_OUTPUT.finditer(block)}
    missing = [name for name in OUTPUTS if name not in found]
    if missing:
        raise ExtractionError(
            f'the `Unpack the verdict` step in {REVIEW} carries no `jq -r` '
            f'program for {missing}. The verdict contract is decided by those '
            'programs, so one that is gone leaves nothing for the matrix to '
            'run the fixtures through -- which is what this raise is for.')
    return found


def step_condition(text, name):
    """The `if:` on the named step, as written.

    Taken from the step header rather than from anywhere in the file: the same
    comparison appears on `Capture the findings for the fix stage` as on
    `Request changes`, and a search that found the wrong one would still be
    able to prove exclusivity.
    """
    for match in STEP.finditer(text):
        if match.group('name').strip() == name:
            return match.group('cond')
    raise ExtractionError(
        f'{REVIEW} has no step named {name!r} with an `if:` on the next line. '
        'Every one of the terminal steps is guarded by a condition read from '
        'the step itself; one that lost both leaves the review with no branch '
        'to hold, and a suite that went on to the next step would not notice.')


def stuck_branch(text):
    """The `MAX_REJECTIONS` branch of the `Reject` step, as text.

    From the `if` to the `else` at its own indentation, so the two halves of
    the hand-off -- what the stuck branch adds and what the retry branch adds
    -- are two readings of the same cut rather than two searches that could
    find the same line.
    """
    block = step_block(text, 'Reject')
    match = STUCK_TEST.search(block)
    if not match:
        raise ExtractionError(
            f'the `Reject` step in {REVIEW} has no '
            '`if [ "$rejections" -ge "$MAX_REJECTIONS" ]; then` in it. That '
            'branch is where an issue is handed to a human, so a rejection '
            'that stopped reaching it is a change to this suite\'s subject '
            'rather than a detail it can pass over.')
    indent = match.group('indent')
    tail = block[match.end():]
    stop = re.search(rf'^{re.escape(indent)}(?:else|fi)\b', tail, re.M)
    if not stop:
        raise ExtractionError(
            'the stuck branch in the `Reject` step has no `else` or `fi` at '
            f'the indentation of its `if` ({indent!r}). The cut that reads it '
            'is by indentation, so an unterminated branch means the read is '
            'not bounded and nothing after it can be trusted.')
    return tail[:stop.start()]


def label_edits(branch):
    """The `--add-label` calls in a branch, as (added, removed) label lists.

    Both lists from one call on purpose. The claim under test is that the
    hand-off is a single atomic edit, so a removal written as a second
    `gh issue edit` line is not the same fix and must not pass.

    Backslash continuations are joined before the line is read, because
    `gh issue edit "$ISSUE" \\` / `--remove-label 'agent:queued'` is one command
    and reading only the first half of it would report a removal that is not
    there as one that is missing -- a false red on a correct workflow, which is
    the failure mode that gets a check switched off rather than a red that
    gets a bug fixed.
    """
    out = []
    for line in re.sub(r'\\\n\s*', ' ', branch).splitlines():
        if '--add-label' not in line or 'gh issue edit' not in line:
            continue
        added = re.search(r"--add-label '([^']*)'", line)
        removed = re.search(r"--remove-label '([^']*)'", line)
        out.append((added.group(1).split(',') if added else [],
                    removed.group(1).split(',') if removed else []))
    return out


def if_condition(condition, outputs):
    """Evaluate an extracted `if:` against unpacked outputs, as GitHub would.

    The whole grammar is the two comparison forms joined by `&&`, and anything
    outside it raises. GitHub's own rules for a bare reference -- truthy unless
    empty, `false` or `0` -- are not implemented, and that is the point: a
    suite that guessed would keep reporting exclusivity for a condition it had
    not actually read. The raise names the condition so the edit that needs
    this suite taught a new form says which one it is.
    """
    value = True
    for clause in condition.split('&&'):
        match = CONDITION.fullmatch(clause.strip())
        if not match:
            raise ExtractionError(
                f'cannot evaluate the condition {condition!r}: {clause.strip()!r} '
                'is not a comparison of a step output against a quoted '
                'literal. GitHub also accepts a bare reference, `!`, `||` and '
                'parentheses, and none of them is evaluated here -- teach this '
                'suite the form rather than letting it guess a truth value.')
        actual = outputs.get(match.group('name'))
        if actual is None:
            raise ExtractionError(
                f'the condition {condition!r} reads '
                f'steps.{match.group("step")}.outputs.{match.group("name")}, '
                'which `Unpack the verdict` does not write. An output read '
                'that is never set is empty, and empty compared against '
                f'{match.group("value")!r} is not a verdict this suite can '
                'reason about.')
        equal = actual == match.group('value')
        value = value and (equal if match.group('op') == '==' else not equal)
    return value


def has_jq():
    return shutil.which('jq') is not None


def has_git():
    return shutil.which('git') is not None


def unpack(programs, verdict):
    """The step outputs for one verdict, by running the workflow's own jq.

    `jq` as a subprocess rather than a reimplementation of it: the program
    under test is a jq expression, and anything short of jq evaluating it is a
    second copy of the thing being checked.
    """
    document = json.dumps(verdict)
    out = {}
    for name in OUTPUTS:
        done = subprocess.run(['jq', '-r', programs[name]],
                              input=document, capture_output=True, text=True)
        if done.returncode != 0:
            raise ExtractionError(
                f'the {name!r} jq program from {REVIEW} does not evaluate on a '
                f'fixture verdict:\n{done.stderr.strip()}')
        out[name] = done.stdout.strip()
    return out


def verdict_fixture(approved, rejected, off_mission=False):
    """A verdict carrying the shape the review stage's schema requires.

    Every required key, not only the three the jq reads, so a later program
    added to `Unpack the verdict` gets a fixture it can evaluate rather than a
    `null` it happens to tolerate.
    """
    return {
        'approved': approved,
        'rejected': rejected,
        'off_mission': off_mission,
        'summary': 'A fixture verdict.',
        'findings': [],
        'verified': [],
        'final_title': 'a fixture title',
        'final_body': 'A fixture body.',
    }


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=str(cwd), capture_output=True,
                          text=True)


@contextlib.contextmanager
def scratch_tree(review_text=None):
    """A throwaway repo holding nothing but a copy of the review workflow.

    Every case that applies the patch is mutating, and applying it to the real
    tree would leave a working directory holding a half-landed workflow edit
    with no order to be order-dependent in. `review_text` writes over the copy
    rather than replacing it, so the synthetic trees below are seeded as the
    committed one is.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = root / REVIEW
        target.parent.mkdir(parents=True)
        shutil.copy2(REPO / REVIEW, target)
        if review_text is not None:
            target.write_text(review_text, encoding='utf-8')
        git('init', '-q', '.', cwd=root)
        yield root


def classify(patch, review_text):
    """`(applies, present)` for one patch against one workflow.

    The two halves are returned unfolded so the cases below can assert on the
    facts themselves rather than on a cell a helper chose for them.
    """
    with scratch_tree(review_text) as tree:
        applies = git('apply', '--check', str(REPO / patch), cwd=tree).returncode == 0
    present = all(line in review_text
                  for line in added_lines((REPO / patch).read_text()))
    return applies, present


def added_lines(text):
    """The lines a patch adds, from its diff body alone.

    `+++ b/...` names the file rather than contributing to it, so it is
    dropped -- kept, the first would have to appear in the workflow and would
    never. Compared stripped, so a landing that reindents is not read as a
    patch still waiting.
    """
    cut = text.find('diff --git ')
    body = text[cut:] if cut >= 0 else text
    return [line[1:].strip() for line in body.splitlines()
            if line.startswith('+') and not line.startswith('+++')
            and line[1:].strip()]


def state_of(applies, present):
    """The cell two facts put a patch in: four of them, and never None."""
    if applies and present:
        return DOUBLE_LANDED
    if applies:
        return PREPARED
    return LANDED if present else STALE


# Classified once per run. The cases below would otherwise re-run
# `git apply --check` per fixture, which is most of the runtime spent
# re-deriving an answer that cannot change inside a run.
_STATE = None


def committed_state():
    """The committed workflow's cell against the prepared patch."""
    global _STATE
    if _STATE is None:
        _STATE = classify(PATCH, read_review())
    return _STATE


@contextlib.contextmanager
def landed_workflow():
    """The workflow as a human's `git apply` would leave it, and the file it is in.

    Yields `(text, problem)`. `problem` is '' when there is nothing to say.

    Prepared, that is the scratch tree the patch was applied to, because the
    content is not in the committed file yet and there is nowhere else to look
    for it. Landed, it is the committed file: the content went there, that is
    what landing *is*, and a scratch tree seeded from it in that state would
    hold the seed and nothing else.
    """
    if state_of(*committed_state()) == PREPARED:
        with scratch_tree() as tree:
            done = git('apply', str(REPO / PATCH), cwd=tree)
            if done.returncode != 0:
                yield '', (f'{PATCH} does not apply to the committed {REVIEW}:\n'
                           f'{done.stderr.strip()}')
                return
            yield (tree / REVIEW).read_text(encoding='utf-8'), ''
    else:
        yield read_review(), ''


class ExtractTests(unittest.TestCase):
    """The extractors, on inline workflow text.

    Without these the cases below are one bad regex away from passing
    vacuously -- a step lookup that found nothing raises, and a `run:` lookup
    that matched the wrong step returns a plausible block, which is the shape
    of the defect the negative controls below exist to catch.
    """

    STEP_TEXT = '\n'.join([
        '      - name: Approve',
        "        if: steps.unpack.outputs.approved == 'true'",
        '        env:',
        '          GH_TOKEN: x',
        '        run: |',
        '          gh pr review "$PR" --approve',
        '      - name: Reject',
        "        if: steps.unpack.outputs.rejected == 'true'",
        '        run: |',
        '          if [ "$rejections" -ge "$MAX_REJECTIONS" ]; then',
        "            gh issue edit \"$ISSUE\" --add-label 'agent:stuck' \\",
        "              --remove-label 'agent:queued'",
        '          else',
        "            gh issue edit \"$ISSUE\" --add-label 'agent:queued'",
        '          fi',
        '',
        '  fix:',
        '    needs: [review]',
    ])

    def test_a_step_body_stops_at_the_next_key(self):
        block = step_block(self.STEP_TEXT, 'Approve')
        self.assertIn('--approve', block)
        self.assertNotIn('agent:stuck', block,
                         'the `Approve` step read past its own key and into '
                         'the `Reject` step, so a stuck-branch string anywhere '
                         'below would satisfy a search scoped to this step')

    def test_a_step_that_is_not_there_is_an_error(self):
        with self.assertRaises(ExtractionError) as caught:
            step_block(self.STEP_TEXT, 'Approve and merge')
        self.assertIn('Approve and merge', str(caught.exception))

    def test_a_step_without_a_run_block_is_an_error(self):
        text = '\n'.join([
            '      - name: Unpack the verdict',
            "        if: steps.verdict.outcome == 'success'",
            '        env:',
            '          OUT: x',
            '',
            '      - name: Approve',
            '        run: |',
            '          true',
            '',
        ])
        with self.assertRaises(ExtractionError):
            step_block(text, 'Unpack the verdict')

    def test_a_condition_is_read_from_its_own_step(self):
        self.assertEqual(step_condition(self.STEP_TEXT, 'Reject'),
                         "steps.unpack.outputs.rejected == 'true'")

    def test_a_condition_is_not_read_off_another_step(self):
        # The same comparison appears on `Capture the findings` as on
        # `Request changes`; a search that found the first one would still be
        # able to prove exclusivity, over the wrong branch.
        text = '\n'.join([
            '      - name: Capture the findings for the fix stage',
            '        id: findings',
            "        if: steps.unpack.outputs.approved != 'true'",
            '        run: |',
            '          true',
            '      - name: Request changes',
            "        if: steps.unpack.outputs.approved != 'true' &&"
            " steps.unpack.outputs.rejected != 'true'",
            '        run: |',
            '          true',
            '',
        ])
        self.assertEqual(step_condition(text, 'Request changes'),
                         "steps.unpack.outputs.approved != 'true' && "
                         "steps.unpack.outputs.rejected != 'true'")

    def test_the_stuck_branch_is_cut_before_the_else(self):
        branch = stuck_branch(self.STEP_TEXT)
        self.assertEqual(label_edits(branch),
                         [(['agent:stuck'], ['agent:queued'])])
        self.assertNotIn(
            "gh issue edit \"$ISSUE\" --add-label 'agent:queued'", branch,
            'the cut ran past the `else`, so the retry branch\'s own '
            '`agent:queued` would satisfy a search for the label the stuck '
            'branch is supposed to remove')

    def test_the_run_block_is_read_from_the_step_key(self):
        # The `run: |` of a step is found by its own key's indentation rather
        # than by a fixed column, because a block scalar's content is only
        # inside it while the indentation holds.
        block = step_block(self.STEP_TEXT, 'Reject')
        self.assertIn('MAX_REJECTIONS', block)
        self.assertNotIn('--approve', block,
                         'the `Reject` step read the `Approve` step\'s run '
                         'block as well as its own')

    def test_a_branch_with_no_end_is_an_error(self):
        text = '\n'.join([
            '      - name: Reject',
            "        if: steps.unpack.outputs.rejected == 'true'",
            '        run: |',
            '          if [ "$rejections" -ge "$MAX_REJECTIONS" ]; then',
            "            gh issue edit \"$ISSUE\" --add-label 'agent:stuck'",
            '',
        ])
        with self.assertRaises(ExtractionError):
            stuck_branch(text)

    def test_the_label_pair_is_read_from_one_call(self):
        calls = label_edits(
            "  gh issue edit \"$ISSUE\" --add-label 'agent:stuck'"
            " --remove-label 'agent:queued'")
        self.assertEqual(calls, [(['agent:stuck'], ['agent:queued'])])
        self.assertEqual(
            label_edits("  gh issue edit \"$ISSUE\" --add-label 'agent:stuck'"),
            [(['agent:stuck'], [])],
            'a removal written as a second `gh issue edit` line is not the '
            'atomic hand-off under test, so it must not read as one')

    def test_both_comparisons_and_the_conjunction_evaluate(self):
        outputs = {'approved': 'true', 'rejected': 'false'}
        self.assertTrue(if_condition(
            "steps.unpack.outputs.approved == 'true'", outputs))
        self.assertFalse(if_condition(
            "steps.unpack.outputs.approved != 'true'", outputs))
        self.assertFalse(if_condition(
            "steps.unpack.outputs.approved != 'true' && "
            "steps.unpack.outputs.rejected != 'true'", outputs))

    def test_a_form_this_suite_does_not_evaluate_is_an_error(self):
        # The refusal rather than a guess. A bare reference, `!`, `||` or a
        # parenthesised expression all evaluate in GitHub, and none of them
        # is evaluated here -- a suite that guessed would go on reporting
        # exclusivity for a condition it had not read.
        for condition in ("steps.unpack.outputs.approved",
                          "!steps.unpack.outputs.approved == 'true'",
                          "steps.unpack.outputs.approved == 'true' || "
                          "steps.unpack.outputs.rejected == 'true'",
                          "(steps.unpack.outputs.approved == 'true')"):
            with self.subTest(condition=condition):
                with self.assertRaises(ExtractionError):
                    if_condition(condition, {'approved': 'true',
                                             'rejected': 'false'})

    def test_an_output_nobody_writes_is_an_error(self):
        with self.assertRaises(ExtractionError):
            if_condition("steps.unpack.outputs.approved == 'true'", {})


@unittest.skipUnless(has_jq(), 'no jq on PATH')
class VerdictMatrixTests(unittest.TestCase):
    """Each combination runs exactly one terminal step, and which one.

    The property and the mapping, both. Exclusivity alone would be satisfied
    by a mapping that is wrong in a way that still runs one step -- every
    combination rejecting, say -- so the named step is asserted per fixture.
    Adding a fixture is a row in `FIXTURES`; nothing here counts them.
    """

    @classmethod
    def setUpClass(cls):
        cls.programs = verdict_programs(read_review())
        cls.conditions = {name: step_condition(read_review(), name)
                          for name in TERMINAL_STEPS}

    def test_each_combination_runs_exactly_one_step(self):
        for (approved, rejected), _expected in FIXTURES.items():
            with self.subTest(approved=approved, rejected=rejected):
                outputs = unpack(self.programs,
                                 verdict_fixture(approved, rejected))
                ran = [name for name in TERMINAL_STEPS
                       if if_condition(self.conditions[name], outputs)]
                self.assertEqual(
                    len(ran), 1,
                    f'a verdict with approved={approved} and '
                    f'rejected={rejected} unpacks to {outputs}, which runs '
                    f'{ran or "none of"} the terminal steps. Two would post two '
                    'reviews on one pull request; none would leave the issue in '
                    'a state the next stage cannot read.')

    def test_each_combination_runs_the_step_it_is_meant_to(self):
        for (approved, rejected), expected in FIXTURES.items():
            with self.subTest(approved=approved, rejected=rejected):
                outputs = unpack(self.programs,
                                 verdict_fixture(approved, rejected))
                ran = [name for name in TERMINAL_STEPS
                       if if_condition(self.conditions[name], outputs)]
                self.assertEqual(
                    ran, [expected],
                    f'a verdict with approved={approved} and '
                    f'rejected={rejected} runs {ran}, and the review stage '
                    f'means {expected}. `Unpack the verdict` reads a verdict '
                    'that sets both booleans as a rejection, which is why the '
                    'third fixture expects Reject rather than Approve.')

    def test_the_programs_are_the_committed_ones(self):
        # Pointed at a workflow whose jq line has been changed, the unpacking
        # changes with it -- which is the whole of why nothing is transcribed
        # here. Both booleans true still rejects, but for the other reason:
        # the program no longer consults `.approved` at all.
        text = read_review().replace(
            '(.approved and (.rejected | not)) | tostring', '.approved | tostring')
        self.assertNotEqual(verdict_programs(text)['approved'],
                            self.programs['approved'],
                            'the mutation did not change the program, so this '
                            'case is not measuring the extraction')
        mutated = unpack(verdict_programs(text), verdict_fixture(True, True))
        self.assertEqual(mutated['approved'], 'true',
                         'with `.approved` alone, a verdict setting both now '
                         'reads as an approval, which is the row the '
                         'exclusivity check has to be able to see change')


@unittest.skipUnless(has_jq() and has_git(), 'no jq or git on PATH')
class RejectionStateTests(unittest.TestCase):
    """The stuck hand-off, read from wherever the fix currently lives.

    Green while the patch is prepared and green once it is landed, because a
    suite that goes red on the day a human does the thing it asked for is a
    gate that gets switched off.
    """

    def test_the_patch_is_on_disk(self):
        # Said out loud rather than left to three `FileNotFoundError`s from the
        # cases below: the patch is the deliverable, and a suite that read
        # nothing because it was deleted would report the same green for the
        # state it is green in now.
        self.assertTrue(
            (REPO / PATCH).is_file(),
            f'{PATCH} is not there. It is the prepared half of this suite\'s '
            'subject: the fix to the `MAX_REJECTIONS` branch, which the token '
            'this pipeline pushes with cannot land. Restore it, or -- if the '
            'fix has been landed by hand -- keep the file and add the '
            '`# LANDED in <sha>` marker to its header.')

    def test_the_working_tree_workflow_is_the_committed_one(self):
        # Everything below reads the working-tree copy, so a local
        # `git apply` of this patch that has not been committed makes the
        # suite measure a state nobody else can see. It is also the state
        # this repository's own pipeline rules say not to be in, so it should
        # be a loud failure rather than a different baseline.
        head = git('show', f'HEAD:{REVIEW}', cwd=REPO)
        if head.returncode != 0:
            self.skipTest(f'no HEAD to compare {REVIEW} against')
        self.assertEqual(
            (REPO / REVIEW).read_bytes(), head.stdout.encode(),
            f'{REVIEW} differs from {REVIEW} at HEAD. This suite reads the '
            'working-tree copy and classifies the patch against it, so a local '
            'edit here changes what every other case here measures. Commit it, '
            'or drop the edit.')

    def test_the_patch_is_in_a_state_this_suite_has_an_answer_for(self):
        applies, present = committed_state()
        state = state_of(applies, present)
        if state == PREPARED:
            self.assertTrue(
                applies,
                f'{PATCH} is {PREPARED} but does not apply to the committed '
                f'{REVIEW}. Re-cut it against the current file; the context a '
                'hunk needs is whatever the file has today, not whatever it '
                'had when the patch was cut.')
        elif state == LANDED:
            self.assertFalse(
                applies,
                f'{PATCH} is {LANDED}: its content is already in {REVIEW} and '
                'it still applies. Applying it a second time would add a '
                'second `--remove-label \'agent:queued\'` to the same call.')
        elif state == STALE:
            self.assertTrue(
                applies,
                f'{PATCH} does not apply to the committed {REVIEW} and none '
                'of the lines it adds are in the file either, so there is no '
                'landing to have happened. Re-cut it against the current file.')
        else:
            self.fail(
                f'{PATCH} is {DOUBLE_LANDED}: every line it adds is already in '
                f'{REVIEW} *and* it still applies cleanly. Those are the two '
                'states that look identical from the patch and are not, and '
                '`git apply` does not stop the second -- it prints nothing and '
                'exits 0.')

    def test_the_header_says_whether_it_is_landed(self):
        # Checked in both directions, as `tools/test_agent_gates_patches.py`
        # checks it for its own set. A prepared patch must not claim to be
        # landed -- that tells a human its work is done while the content is
        # not in the file -- and a landed one must, because the `git apply`
        # line above it is then no longer a thing to do. This is the cost of
        # keeping a patch after landing it, and the reason deleting the file
        # instead was rejected.
        text = (REPO / PATCH).read_text(encoding='utf-8')
        marked = LANDED_MARKER.search(text[:text.find('diff --git ')])
        if state_of(*committed_state()) == LANDED:
            self.assertIsNotNone(
                marked,
                f'{PATCH} has been landed -- every line it adds is already '
                f'in {REVIEW} and it no longer applies -- and its header still '
                'says "git apply this, and that is the whole change". That is '
                'the one line in the file that is now false, and it is the '
                'line a human reads first. Add `# LANDED in <sha of the '
                'landing commit>` to the header.')
        else:
            self.assertIsNone(
                marked,
                f'{PATCH} carries a `# LANDED in ...` marker but is still '
                f'{state_of(*committed_state())}, so the marker is wrong '
                'rather than the header being incomplete. Nothing has landed '
                'it, and a reader who trusts the marker skips a workflow edit '
                'that is still waiting.')

    def test_the_stuck_branch_hands_over_and_does_not_leave_it_queued(self):
        with landed_workflow() as (text, problem):
            self.assertFalse(problem, problem)
            calls = label_edits(stuck_branch(text))
        self.assertEqual(
            len(calls), 1,
            f'the `MAX_REJECTIONS` branch makes {len(calls)} `--add-label` '
            'calls where the hand-off is one. Two is a branch that has picked '
            'up a second edit, and the exclusivity of the label pair is the '
            'claim under test.')
        added, removed = calls[0]
        self.assertIn('agent:stuck', added)
        self.assertIn(
            'agent:queued', removed,
            'the stuck branch adds `agent:stuck` and does not remove the '
            '`agent:queued` the first rejection added, so an issue rejected '
            f'twice carries both. That contradicts the step\'s own comment '
            '("an issue carries one of these, not both"), what '
            '`docs/agent-pipeline.md` says the second rejection "gets '
            '`agent:stuck` instead", and the comment the branch posts, which '
            'tells a human to add `agent:queued` when it is already there. '
            f'{PATCH} is the prepared fix.')

    def test_the_retry_branch_still_queues_the_issue(self):
        # The other half of the hand-off, and the one a re-cut of the fix
        # could quietly break: a first rejection has to go back to
        # `agent:queued` or the retry sweep never sees the issue again.
        block = step_block(read_review(), 'Reject')
        test = STUCK_TEST.search(block)
        self.assertTrue(test, 'the `Reject` step lost its `MAX_REJECTIONS` '
                              'branch')
        tail = block[test.end():]
        branch = tail.split(f"{test.group('indent')}else", 1)
        self.assertGreater(
            len(branch), 1, 'the stuck branch has no `else`, so the retry '
                            'path this hands the issue to does not exist')
        queued = [added for added, _removed in label_edits(branch[1])
                  if 'agent:queued' in added]
        self.assertEqual(
            queued, [['agent:queued']],
            'the `else` branch of the `MAX_REJECTIONS` test does not add '
            '`agent:queued` in one call, so a first rejection does not go back '
            'to the retry sweep.')

    def test_the_hand_off_is_red_without_the_removal(self):
        # The control that matters, and the one this issue exists for: take the
        # workflow the fix produces, take the removal back out, and the case
        # above has to fail. Built from the landed text rather than read from
        # the committed file, so it holds in both states of the patch -- and
        # because the committed file is the pre-image today, it is also the
        # statement that the committed workflow does not do this yet.
        with landed_workflow() as (text, problem):
            self.assertFalse(problem, problem)
        removal = " --remove-label 'agent:queued'"
        # `assertTrue(... in ...)`, never `assertIn`: `assertIn` prints the
        # whole container on failure, and the container is the review
        # workflow. A failure here once scrolled 30 KB of workflow past the
        # sentence that says what to do about it.
        self.assertTrue(
            removal in text,
            'the landed workflow does not carry the removal, so this control '
            'is not removing anything and would pass on a workflow that was '
            'already wrong')
        calls = label_edits(stuck_branch(text.replace(removal, '', 1)))
        self.assertEqual(
            calls, [(['agent:stuck'], [])],
            'with the removal taken out the branch adds `agent:stuck` and '
            'leaves `agent:queued` behind -- the defect this patch fixes. A '
            'check that reported that as a pass would be reporting a twice-'
            'rejected issue as handed over.')
        self.assertNotIn(
            'agent:queued', calls[0][1],
            'and the case above must therefore have been red on it; if this '
            'assertion ever needed explaining to be true, that case is not '
            'reading the branch this control mutates')

    def test_a_workflow_without_a_stuck_branch_is_an_error(self):
        # The other direction, and why the raise above exists rather than an
        # empty return. A `Reject` step whose `MAX_REJECTIONS` branch is gone
        # has to stop the suite, not read as a branch that adds nothing --
        # which is the failure a green run cannot show, because a rule that
        # read nothing reads the same as a rule that passed.
        text = read_review()
        block = step_block(text, 'Reject')
        test = STUCK_TEST.search(block)
        self.assertTrue(test, 'the committed workflow has no stuck branch to '
                              'remove, so this control is not cutting what it '
                              'says it cuts')
        indent = test.group('indent')
        rest = block[test.end():]
        stop = re.search(rf'^{re.escape(indent)}fi\b', rest, re.M)
        self.assertIsNotNone(stop, 'the stuck branch is unterminated')
        mutilated = text.replace(block, block[:test.start()] + rest[stop.end():])
        self.assertNotEqual(mutilated, text,
                            'the control did not change the workflow')
        with self.assertRaises(ExtractionError) as caught:
            stuck_branch(mutilated)
        self.assertIn('MAX_REJECTIONS', str(caught.exception),
                      'the refusal does not name what went missing')

    def test_a_workflow_missing_a_jq_program_is_an_error(self):
        # The same discipline on the other section. An extractor that returned
        # the two programs it did find would go on to run the matrix over half
        # the subject and report it clean.
        text = read_review()
        line = re.search(r'.*echo "approved=.*\n', text).group(0)
        with self.assertRaises(ExtractionError) as caught:
            verdict_programs(text.replace(line, '', 1))
        self.assertIn('approved', str(caught.exception),
                      'the refusal does not name the output that went missing')

    def test_a_comment_quoting_the_combinations_stays_green(self):
        # And the direction that keeps any of this usable: a rule that fires
        # on the sentence stating it is a rule everybody eventually disables.
        # A workflow comment naming the four combinations, inside the block the
        # extractor reads, must change nothing.
        text = read_review()
        marker = ('          # (approved=true, rejected=false) approves;\n'
                  '          # (true, true) rejects; (false, false) requests\n')
        anchor = '          echo "rejected='
        self.assertTrue(anchor in text,
                        'the `Unpack the verdict` step lost the line this '
                        'comment is added above')
        commented = text.replace(anchor, marker + anchor, 1)
        self.assertEqual(verdict_programs(commented),
                         verdict_programs(text),
                         'a comment naming the combinations was read as one of '
                         'them. A reader would have to delete the explanation '
                         'to keep the explanation checked.')