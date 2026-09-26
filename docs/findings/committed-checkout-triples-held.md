# What the checkout suite holds, which was seven of nine depths and no `stated` at all

**Issue #1035. Written 2026-09-26.** This page is about **what a suite reads out
of the committed tree**, not about what the workflows do.
[`history-checkout-claims.md`](history-checkout-claims.md) answers the second
question and its table is not changed by anything here — all nine of its rows are
still true. What was missing is a mechanism holding that table, and what follows
is the measurement of the mechanism: what it held before this change, what it
holds now, and the two edits it now turns red on, each one run rather than
predicted.

**What this is not.** It is not a correction to any committed sentence; nothing
published went false and nothing is retracted, so there is no §4a-4d correction
block anywhere on this page. It is not a claim that any gate has run in CI — no
gate calls either tool, for the reason
[`history-checkout-claims.md`](history-checkout-claims.md) gives. It is not a
claim that the workflows should change: neither edit below is proposed, and
`claude.yml` is not from the `agent-pipeline` template, so the template-re-copy
hazard that threatens the other eight does not reach it.

## The measurement the table is made of

Nine `actions/checkout` steps, eight workflow files, read out of the tree as it
stands by

```console
$ python3 ec/tools/check_history_checkouts.py
  agent-conflicts.yml / resolve / Checkout main: fetch-depth: 0  full
  agent-fix.yml / fix / Checkout the agent branch: fetch-depth: 0  full
  agent-followups.yml / followups / Checkout at the merge commit: depth 1 (the action's default)
  agent-implement.yml / implement / Checkout: fetch-depth: 0  full
  agent-plan.yml / plan / Checkout: depth 1 (the action's default)
  agent-review.yml / review / Checkout: fetch-depth: 0  full
  ci.yml / gates / Checkout: fetch-depth: 0  full
  ci.yml / workflows / Checkout: depth 1 (the action's default)
  claude.yml / claude / Checkout repository: fetch-depth: 1
```

(the report's remaining output is the two verdicts, both green, and the five
depth claims in the two tools). Carried into the suite as one literal, the
mapping is `{workflow: [(job, depth, stated)]}`:

| workflow | job | depth | stated |
|---|---|---:|---|
| `agent-conflicts.yml` | `resolve` | 0 | yes |
| `agent-fix.yml` | `fix` | 0 | yes |
| `agent-followups.yml` | `followups` | 1 | no |
| `agent-implement.yml` | `implement` | 0 | yes |
| `agent-plan.yml` | `plan` | 1 | no |
| `agent-review.yml` | `review` | 0 | yes |
| `ci.yml` | `gates` | 0 | yes |
| `ci.yml` | `workflows` | 1 | no |
| `claude.yml` | `claude` | 1 | yes |

## What the suite held before this change

`CommittedTreeTests.test_the_derivation_is_what_the_claim_says_it_is` read seven
of the nine depths by value and nothing else:

- **`ci.yml`** and **`claude.yml`** were held as `(job, depth)` pairs, and the
  four agent stages `implement`, `fix`, `review` and `resolve` each against a
  literal of their own. That is seven rows, all by value, and it is why the case
  was worth having.
- **`agent-plan.yml` / `plan`** was held by nothing. It appears in the suite once,
  as the substring `"agent-plan.yml / plan"` in
  `test_the_report_prints_every_checkout_it_found`, and that assertion is
  satisfied by any depth and any step name: the report prints what the tree says,
  so a `plan` job that moved from 1 to 0 would still print the substring. Its
  depth could move 1 → 0 and the whole suite would stay green.
- **`agent-followups.yml`** was held by nothing at all. The word appears nowhere
  in the file.
- **`stated` was read by no committed case.** Both cases that assert it run on
  synthetic trees in `DepthTests`, built by the `workflow()` helper a few lines
  above them. The committed class read `(job, depth)` and stopped.

Neither of the two unheld jobs runs a history reader, so `depth_problems()`
constrains neither and the tool's own verdicts are unmoved by both edits below.
That is the whole of why the gap survived: the one invariant the tool does assert
is the one that says nothing about either row.

## Why `stated` is the load-bearing half, and not a second copy of `depth`

The two halves of the triple are not redundant, and the measurement below is
what shows it: **`claude.yml` losing its `fetch-depth: 1` leaves its depth at 1.**
A comparison over `(job, depth)` alone cannot see that edit at all, because the
depth is genuinely unchanged — the step falls back to `actions/checkout`'s
default, which is also 1. Only `stated` distinguishes "this step says 1" from
"this step says nothing and gets 1", and that distinction is the whole content
of the correction.

It is what the `stated?` column of
[`history-checkout-claims.md`](history-checkout-claims.md)'s table is, and what
the paragraph in [`../findings.md`](../findings.md) §86 says when it corrects the
issue's own wording: the issue called `claude.yml`'s `fetch-depth: 1` "the only
shallow checkout", and the correction is that it is the only one that *states* a
depth other than 0. Four checkouts are shallow; one says so. Two published claims
turn on that word — the table's `stated?` column, and that sentence — and before
this change a suite read neither.

## The two edits, each run rather than predicted

Both are applied one at a time to a copy of the committed `.github/workflows/`
in a scratch root, and the committed assertion is then run against that copy, so
what is demonstrated is the assertion going red rather than a re-derivation
differing. Neither edit can be made to the committed workflows from this branch:
the push token has no `workflow` scope, and making the suite object to the edits
is the point — they are a human's to make.

**`agent-plan.yml`'s `plan` job moving to `fetch-depth: 0`.** One line inserted
into that job's existing `with:` block:

```
  agent-plan.yml / plan / Checkout: depth 1 (the action's default)   # before
  agent-plan.yml / plan / Checkout: fetch-depth: 0  full              # after
```

`("plan", 1, False)` becomes `("plan", 0, True)`, and the mapping no longer
equals the expected one. Depth alone would have caught this one; it is included
because it is the edit the retraction #1013 led with, and "every `agent-*.yml`
stage checks out with `fetch-depth: 0`" was false for exactly this job.

**`claude.yml` losing its `fetch-depth: 1` line.** The line removed, nothing
else touched:

```
  claude.yml / claude / Checkout repository: fetch-depth: 1                          # before
  claude.yml / claude / Checkout repository: depth 1 (the action's default)          # after
```

`("claude", 1, True)` becomes `("claude", 1, False)`. **The depth does not
change**, which is the point and the reason this half of the triple is not
redundant with the first: a suite holding `(job, depth)` would have stayed green
through this edit, and the table's `stated?` column and §86's sentence would both
have gone false with nothing in the tree noticing.

**Both edits leave the tool's own report green**, and the transcript says so:

```console
$ # agent-plan.yml's plan job gains fetch-depth: 0
  agent-plan.yml / plan / Checkout: fetch-depth: 0  full
  every job that runs a history reader has a full-depth checkout
$ echo $?
0
$ # claude.yml loses its stated fetch-depth: 1
  claude.yml / claude / Checkout repository: depth 1 (the action's default)
  every job that runs a history reader has a full-depth checkout
$ echo $?
0
```

## The consequence worth stating plainly

**A `fetch-depth: 0` added to `agent-plan.yml` is a legal workflow edit that no
invariant in this repository objects to.** The gate keeps running, no job breaks,
and the one decidable rule — every job that runs a history reader has a full-depth
checkout — puts no constraint on a job that runs no history reader, which
`plan` is not. `depth_problems()` reads a different question from the one the
table answers, and neither is wrong.

What objects is the table, and only the table, because it is what makes the
published sentences true. **Each edit falsifies a different one, and the pairing
is worth spelling out rather than leaving as "the sentences go stale":**

- **`plan` taking `fetch-depth: 0`** makes the table's *absent* cell for that row
  wrong — it would read `fetch-depth: 0`, not *absent* — and makes §86's
  "`agent-plan.yml`'s `plan` job and `agent-followups.yml`'s `followups` job
  state nothing" wrong, because `plan` would state something. §86's other
  sentence in that paragraph, that `claude.yml` is "the only one that *states* a
  depth other than 0", **survives it**: `0` is not a depth other than 0.
- **`claude.yml` losing its line** makes that sentence wrong, because nothing
  would then state a depth other than 0 at all, and makes the table's `claude.yml`
  row read *absent* rather than `fetch-depth: 1`. §86's "the `plan` job and the
  `followups` job state nothing" survives it untouched.

Whoever makes either edit updates the table row and the sentence it falsifies in
the same change. The other sentence in §86's paragraph is not a tripwire for that
edit, and saying so is the point: a claim held by a table is held against the
facts the table carries, not against everything in the same paragraph.

This is also why the comparison is the whole mapping and not nine assertions: a
**tenth** checkout anywhere under `.github/workflows/` — a new workflow, or a
second `actions/checkout` in one that has one — turns it red with the other two.
That is a tenth row the table would need, and it is the case
[`history-checkout-claims.md`](history-checkout-claims.md) would have to be
re-measured for. The narrower per-key form would leave it unheld.

## What is left unheld, said as "not found by this method"

None of these is a gap the change closes, and none is reported as absent:

- **The `step` name.** No committed assertion carries it, so a rename of
  `Checkout repository` to anything else is invisible. The report prints it and
  nothing compares it.
- **A checkout behind a composite action,** and a `fetch-depth` written as a
  `${{ }}` rather than a literal. Both are the checker's own standing caveat;
  a step either is or is not in the mapping and no case says which.
- **`agent-conflicts.yml`'s `resolve` job runs the gate from its prompt rather
  than from a `run:` step,** so `depth_problems()` does not count it as a
  history reader and its `fetch-depth: 0` is held by this table rather than by
  the invariant. It is right today, and it is held.
- **The `PROSE_FILES` half of the tool is not in this mapping at all.** It is
  held by the two other committed cases in the same class, which are unchanged
  by this.
- **Whether the tools' own two verdicts stay green** is held by a third case, and
  was not touched.

## A note on this page's own citation shape

This page names `ec/tools/test_check_history_checkouts.py` by path and by method
name and carries **no `test_*.py:NNN` pin anywhere**, in prose or in a fenced
block. That is deliberate and not an oversight. The suite is in the *unpinned
tail* of [`check_pin_table_by_cited_file.py`](../../ec/tools/check_pin_table_by_cited_file.py)'s
table, which reads **43 indexed / 12 named / 31 named by none** on the committed
tree, and a single pin naming it would move that to `12 → 13` and `31 → 30` and
redden a suite that has nothing to do with this issue.
[`pin-table-by-cited-file.md`](pin-table-by-cited-file.md) records the standing
rule, and both figures above are a run of
`python3 ec/tools/check_pin_table_by_cited_file.py` rather than carried forward.

## What is not claimed

- **That any of the two edits has been made.** Both are demonstrations on a
  scratch copy. The committed workflows are unchanged by this work, and neither
  edit is proposed.
- **That any gate has ever run this suite or either tool.** Neither is in
  `.github/scripts/agent-gates.sh`, and cannot be from an agent branch. They run
  under `tools/run-tests.sh`.
- **That the table is exhaustive of the claim's blast radius.** It holds the
  nine checkouts this method can see under `.github/workflows/`, which is the
  same population the tool's own docstring is careful about and for the same
  reason. Anything outside that directory is not found by this method.
- **Any hardware, Windows, EC or firmware fact.** None is involved, none is
  produced, and none could be.
- **That the workflows ought to change.** `depth 1` and `states 1` are different
  facts and both are published; this holds them, it does not argue about them.
