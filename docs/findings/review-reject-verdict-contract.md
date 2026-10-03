# The rejection hand-off and the verdict matrix: a prepared fix, and a check that reads the workflow

**2026-10-03, issue #410.** The `Reject` step of `.github/workflows/agent-review.yml`
hands an issue to a human on its second rejection and leaves the `agent:queued`
label its first rejection added still on the issue. Three statements already in
the tree say that is not the intended end state. The fix is one line, prepared
rather than landed. Alongside it,
`tools/test_review_verdict_contract.py` holds the review stage's two contracts —
that hand-off, and that each verdict combination runs exactly one of the three
terminal steps — by reading both out of the committed workflow.

The subject is a repository invariant, not a finding about the EC. Nothing here
reads firmware, opens a capture, or reads back a register.

## What was wrong

The `MAX_REJECTIONS` branch of the `Reject` step adds `agent:stuck` and removes
nothing:

```sh
if [ "$rejections" -ge "$MAX_REJECTIONS" ]; then
  gh issue comment "$ISSUE" --body "... Remove the \`agent:stuck\` label and add \`agent:queued\` to let the pipeline try once more. <!-- agent-rejected -->"
  gh issue edit "$ISSUE" --add-label 'agent:stuck'
else
  gh issue comment "$ISSUE" --body "... The retry sweep will plan it again from here. <!-- agent-rejected -->"
  gh issue edit "$ISSUE" --add-label 'agent:queued'
fi
```

So an issue rejected twice carries `agent:stuck` **and** `agent:queued`. What
says that is wrong:

- **The comment the branch posts.** It tells a human to remove `agent:stuck` and
  add `agent:queued` "to let the pipeline try once more" — an instruction that is
  wrong for precisely this state, because `agent:queued` is already there. This
  is the strongest of the three: it is not a description of the intended state,
  it is the thing a human would actually do in response to it.
- **`docs/agent-pipeline.md`**, in the bullet on the third `rejected` verdict
  (the "LOCAL CHANGE (2026-09-24, not in the template)" one, which also records
  that `MAX_REJECTIONS` counts `<!-- agent-rejected -->` markers): the second
  rejection "gets `agent:stuck` **instead**".
- **The step's own comment**, on the two `|| true` removals at the foot of the
  step: "an issue carries one of these, not both, and removing an absent label is
  an error". **This one is weaker evidence than it looks, and the issue that
  filed #410 over-read it.** Its "these" are `agent:working` and
  `agent:planned` — the two labels it guards — so it is about the state labels,
  not about `agent:stuck` against `agent:queued`. What it does establish is the
  convention this fix follows: these labels are alternatives, not a set to
  accumulate.

Neither the code nor the docs produce the state the first two describe.

**What this does *not* break, and is not written up as if it did.** The extra
label does not cause a runaway retry, because the consumers of these labels
already filter `agent:stuck` out of their candidate lists. In
`agent-retry.yml` the `Re-run what stalled` step skips an issue carrying it, as
do the steps that resolve a conflicting pull request, restart a pull request
whose review never came, start an issue whose turn never came, and plan an issue
whose turn never came; `agent-plan.yml`'s triage step declines an issue carrying
it. So an issue is planned at most twice and then waits for a human, as
intended. The cost is narrower than a runaway: an issue that reads as queued to
anything keying on the label alone, and a label list a human cannot act on from
the comment the step posts. **These are the consumers as they read today, not a
property of the design** — each filter is one line of a workflow that a template
re-copy replaces, and a consumer that stopped filtering would change the
conclusion without anything here noticing.

## The fix, prepared rather than landed

`docs/ci/agent-review-reject-stuck-label.patch` is the one-line change:

```sh
gh issue edit "$ISSUE" --add-label 'agent:stuck' --remove-label 'agent:queued'
```

A human lands it with `git apply docs/ci/agent-review-reject-stuck-label.patch`.
It is prepared because `.github/` is copied from the `agent-pipeline` template
and this pipeline's push token has no `workflow` scope, so a branch editing
`.github/workflows/agent-review.yml` fails at the *end* of a pull request rather
than at the start of one. That is the same reason every other prepared change in
`docs/ci/` is prepared, and `docs/ci/ci-workflow-lint-docs-ci.patch` is the
existing precedent for a `docs/ci/` patch aimed at a workflow rather than at the
gate script.

Two things about it are worth stating rather than leaving to the reader.

**It is a `LOCAL CHANGE` hunk, so unlike the `agent-gates-*.patch` files it is
not at risk from a template re-copy.** The `Reject` step and the third
`rejected` verdict are this repository's own, not the template's. The gate
patches cut a file that *is* re-copied, and their documented failure mode is a
re-copy moving the lines a hunk was cut against. This hunk cuts context this
repository wrote, and it also has none of their free-anchor problem: a hunk that
replaces one line needs no anchor, so it is not competing for an insertion point
with the rest of `docs/ci/`.

**It uses the combined `--add-label ... --remove-label ...` form**, which is
what the stuck branches of `agent-fix.yml` and `agent-implement.yml` already
use. The alternative — a second `gh issue edit` line — would have to be guarded
with `|| true` like the two removals at the foot of the step, because
`gh issue edit --remove-label` on a label the issue does not carry is an error,
which is what that step's own comment records. Fusing the removal into the call
that adds `agent:stuck` keeps the pair in one API call that cannot half-apply.

### Its name is outside the `agent-gates-` family on purpose

`tools/test_agent_gates_patches.py` globs `docs/ci/agent-gates-*.patch` and
holds that set equal to a hardcoded `PATCHES` list, and
`tools/check_doc_patch_refs.py`'s `on_disk()` globs the same family. A patch
with a different name is invisible to both, which is the point: this patch cuts
a different file, so putting it in either set would be a false failure, and
adding it to `PATCHES` would edit a shared file to accommodate a file that set
was never about.

**The cost of that choice is stated rather than hidden.** Nothing in
`check_doc_patch_refs.py` requires this patch to be cited, because the live
direction globs only the `agent-gates-` family — so unlike those patches, this
one is not held against being uncited. It is named in this write-up because a
human looking for the fix needs to find it, not because a gate would notice its
absence. It is named without a link: `check_doc_links` in the cheap tier reads
markdown *links*, and a `.patch` target is outside what that discovery matches.

## The check

`tools/test_review_verdict_contract.py` holds two things that nothing committed
held before.

### The verdict matrix

The review's output is a JSON verdict; `Unpack the verdict` derives two booleans
from it with `jq`; three steps branch on those booleans by name. The pairing is
what makes the review's output mean anything: a verdict has to run **exactly
one** of `Approve`, `Request changes` or `Reject`. Two would post two reviews
on one pull request; none would leave the issue in a state the next stage
cannot read.

The suite pushes one fixture verdict per combination through the jq programs and
evaluates the `if:` conditions extracted from the three named steps:

| fixture `approved` | fixture `rejected` | unpacked | runs |
|---|---|---|---|
| `true` | `false` | `approved=true, rejected=false` | `Approve` |
| `false` | `true` | `approved=false, rejected=true` | `Reject` |
| `true` | `true` | `approved=false, rejected=true` | `Reject` |
| `false` | `false` | `approved=false, rejected=false` | `Request changes` |

The third row is the one a later edit breaks first. `approved` is
`(.approved and (.rejected | not))`, so a verdict setting both booleans is read
as a rejection by design — the comment above it says why, and it is the failure
the expression exists to prevent: merging something the reviewer also said to
throw away.

### Everything is extracted, never transcribed

The single most important property of the suite: **a test carrying its own copy
of `(.approved and (.rejected | not))` would keep passing after the workflow's
copy changed**, which is exactly the gap this closes. So the jq programs are
pulled out of the committed file, run under `jq` as a subprocess, and the `if:`
conditions are read off the three named steps.

The `if:` conditions are read from the *step*, not from the file, because
`Capture the findings for the fix stage` carries the same comparison as
`Request changes` — a global search would find the wrong one and still be able
to prove exclusivity, over the wrong branch. Likewise the stuck branch is cut by
indentation from its own `if` to the `else` at its level, so the retry branch's
own `agent:queued` can never satisfy a search for the label the stuck branch is
supposed to remove.

`if_condition` evaluates the whole grammar it accepts — a comparison of a step
output against a quoted literal, joined by `&&` — and **raises on anything
else**. GitHub also accepts a bare reference, `!`, `||` and parentheses; none of
those is evaluated, because a suite that guessed would go on reporting
exclusivity for a condition it had not read. A refusal names the condition, so
the edit that needs the suite taught a new form says which one it is. This is
observable rather than hypothetical: pointing the suite at a workflow whose
`Approve` condition uses `||` produces that refusal, not a verdict.

### The hand-off, in both states of the patch

The suite is **green while the patch is prepared and green once it is landed**,
so it never lands a red gate — the cheapest way to make a gate get switched off.
`RejectionStateTests` classifies the committed workflow against the patch by the
two-fact rule `tools/test_agent_gates_patches.py` already uses: `git apply
--check` in a scratch tree says whether the patch still applies, and whether its
added lines are already present says whether the work is done. `prepared` and
`landed` are both green; `stale` and `landed, still applies` are red and say
which, and the last of those explains why applying it a second time would put a
second `--remove-label 'agent:queued'` in the same call.

The label check then reads from **wherever the content is**: the patched scratch
tree while the patch is prepared, the committed file once it is landed. The
header's `# LANDED in <sha>` marker is held in both directions, so a patch that
has been landed stops reading as "apply this", and one that is still prepared
cannot claim to be done.

### Negative controls

A check that reads nothing exits 0 and looks exactly like a clean tree, so each
extractor is held from the failing side. The suite was run against these
mutations of a scratch copy of the tree, and each was seen to land where this
table says:

| mutation | result |
|---|---|
| the committed workflow has the fix applied (the `landed` state) | green — the retention read follows the patch |
| `Request changes` no longer tests `rejected` | red — `approved=False, rejected=True` runs `['Request changes', 'Reject']` |
| the `approved` jq program drops its `.rejected` guard | red — the both-true fixture stops unpacking to a rejection |
| the `MAX_REJECTIONS` branch deleted | red — the extractor refuses and names what is missing |
| the `approved` jq line deleted | red — the extractor refuses and names the output |
| `docs/ci/agent-review-reject-stuck-label.patch` deleted | red — `test_the_patch_is_on_disk` names the file |
| a comment inside `Unpack the verdict` naming the combinations | green — a rule that fires on the sentence stating it gets disabled |

Two rows are green and are the point of being here. The first is the state a
human puts the tree in on the day they land the patch, and a check that went red
there would be a check that gets switched off. The last is a control on the
control: a rule that fires on the sentence stating it is a rule everybody
eventually disables, so a comment *inside the block the extractor reads*, naming
the combinations, has to change nothing.

The exclusivity mutation is the one worth reading: it stays inside the grammar
the suite evaluates, so nothing refuses it, and the failure names the
combination and both steps that ran. That is the check doing its job rather than
its parser declining.

**One control is a control on a *fixture*, not on the committed file.** The
hand-off-is-red-without-the-removal case builds its mutation from the landed
text rather than reading the committed workflow, so it holds in both states of
the patch. Because the committed workflow is the pre-image today, that case is
also the standing statement that the committed file does not do this yet.

## What was not checked, and what would check it

- **No rejection has been performed.** Deciding a verdict needs a real review
  run; #405 recorded the same gap for the unpacking it introduced, and this does
  not close it. Everything above is about committed text and what `jq` and
  `git apply` say about it. The first live confirmation of the label pair is the
  next real second rejection.
- **No label has been observed on a live issue**, before or after the fix. The
  claim that a twice-rejected issue carries both labels is read off the branch's
  two `gh issue edit` calls, not off an issue.
- **The consumers of these labels were read, not exercised.** That the extra
  label causes no runaway retry is a statement about what the label filters in
  `agent-retry.yml` and `agent-plan.yml` *say*, checked by reading them.
- **Nothing here touches the EC, the BIOS, the Windows stack or a driver**, so
  there is no live-run preparation to add and no `needs-hardware-test` framing.

## Why no gate call

`tools/run-tests.sh` is not called from `.github/scripts/agent-gates.sh`, and
that stays true: the gate script is copied from `ElDavoo/agent-pipeline`, so a
gate call is an upstream change and a re-copy rather than a line here. This
suite runs under the `tests` job in `ci.yml` and under `bash tools/run-tests.sh
tools`.

`docs/agent-pipeline.md` is deliberately untouched. Its sentence about the
second rejection getting `agent:stuck` "instead" becomes *true* once the patch
lands, and so do the step's own comment and the comment the branch posts. Three
currently-false statements are corrected by the one line, with no prose to
change and no second thing to keep in step. Appending the patch to its prepared
changes list is a one-line follow-up if a human decides that is where it
belongs; this write-up is named by `check_doc_patch_refs.py`'s reference
direction instead, and this file is where a reader looking for the fix will look.

## A note on the two line citations the issue carried

The issue cites `docs/agent-pipeline.md:229-231` and `agent-plan.yml:132-133`.
Both have drifted: the `agent-pipeline.md` bullet is now in the section on the
third `rejected` verdict under the review-stage differences, and the plan
stage's triage refusal is the `taken=` step of its capacity/claim block. The
current locations are cited here by heading and by the code they name rather
than by line, per this repository's rule about pinning prose to line numbers —
a bare `file:NNN` is true only until the next merge that grows the file above
it, and every one of these files grows.