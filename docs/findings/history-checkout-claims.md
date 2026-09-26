# The checkout-depth claim, corrected at seven sites and re-derived by a checker

**Issue #1009. Written 2026-09-26.** Seven committed sentences described what
this repository's CI checkouts can do, and all seven were wrong in the same
direction: they said the whole of `ci.yml` was default-depth, and the one job
in it that runs anything needing history has been `fetch-depth: 0` since
2026-09-24. This page holds what each one said, what it says now, and the
measurement both were derived from — because the corrected sentences have
nothing else holding them up, and the next one to decay will decay the same way
unless the derivation is written where the reader of the sentence can find it.

**What this is not.** It is a correction to prose, not to behaviour.
`verify_reassembly.py --verify-provenance` still needs a full clone; that
contract does not change here and nothing in this change touches what the mode
does. **Nothing on this page is a claim that the mode has ever run in CI**,
which is the one thing the issue does not claim either: what follows is read
out of committed files, and a workflow that says a job runs a gate is not an
observation of that gate having run.

## The measurement the sentences should have come from

Nine `actions/checkout` steps are committed under `.github/workflows/`, and this
is what `ec/tools/check_history_checkouts.py` prints for them. It is a
transcription of a run, not a summary of one:

| workflow / job | depth | stated? | runs a history reader? |
|---|---|---|---|
| `ci.yml` / `gates` | 0 | `fetch-depth: 0` | yes — `agent-gates.sh` at `:45` |
| `ci.yml` / `workflows` | 1 | *absent* (the action's default) | no — actionlint and zizmor |
| `agent-implement.yml` / `implement` | 0 | `fetch-depth: 0` | yes |
| `agent-fix.yml` / `fix` | 0 | `fetch-depth: 0` | yes |
| `agent-review.yml` / `review` | 0 | `fetch-depth: 0` | no |
| `agent-conflicts.yml` / `resolve` | 0 | `fetch-depth: 0` | from its prompt, not a `run:` step |
| `agent-plan.yml` / `plan` | 1 | *absent* | no |
| `agent-followups.yml` / `followups` | 1 | *absent* | no |
| `claude.yml` / `claude` | 1 | `fetch-depth: 1` | no |

**The sentence that is true in both directions, and is now what both tools
carry:** a full clone resolves the revisions; a default-depth clone does not;
`ci.yml`'s `gates` job is full-depth and its `workflows` job is not; and **the
one checkout in these workflows that states a depth other than 0 is
`claude.yml:72`'s `fetch-depth: 1`** — the other three shallow ones state
nothing and are the action's default. The issue text and the plan both said
`claude.yml`'s was "the only shallow checkout", and that is not what the tree
says; it is the only one that says so. The difference is the whole reason the
word *stated* is in the table.

`.github/scripts/agent-gates.sh:160-163` is the branch that calls
`--verify-provenance --base 08b72e2 --migration a56b3bb --listings-from
8c7985e`, after `--check` and `--self-test`, and it has said so in its own words
at `:157-159` all along: *"ci.yml's gates checkout and the agent stages' all use
`fetch-depth: 0` for it."* That sentence was already correct. It is the one the
tools should have been agreeing with.

`docs/ci/agent-gates-deep-schedule.yml:58` is `fetch-depth: 0` too, with a
comment naming `--verify-provenance` at `:56-57`. It is **prepared rather than
landed** — `docs/ci/` holds patches and this proposed workflow — so it is
outside the glob the checker reads and appears in no table above. Not found by
this method, which is not the same as absent.

## Where the change came from, and what it cost

One commit, `cc2ab10d` (2026-09-24, PR #411, closing #407), did both halves:
it put `fetch-depth: 0` on `ci.yml`'s `gates` checkout **and** added the
`--verify-provenance` call to `agent-gates.sh`. So the sentence that said the
mode "is not part of the per-commit gate" was wrong in the same commit that
put it in the gate, and `docs/agent-pipeline.md` recorded the decision the same
day. `docs/findings.md` §14f's sentence and `ec/ghidra/README.md`'s were both
written before it and neither was revisited; `docs/agent-pipeline.md`'s heading
was contradicted by its own decision paragraph eleven lines below, and nothing
in the tree notices a sentence that disagrees with the paragraph under it.

## The seven sites

Each row keeps the old wording, because a retraction that deletes the wrong
version leaves a reader with no way to tell a correction from a change of mind
([`../findings.md`](../findings.md) §4a-4d). In the two *tools* the corrected
sentence is the only one left in the file — a wrong sentence in a docstring is
the defect itself, and a reader copies it — so this page is where the old
wording is kept, next to the correction.

| # | site, as it stands now | what it said | what it says now |
|---|---|---|---|
| 1 | `ec/tools/verify_reassembly.py:81-84` (docstring) | "needs a full clone, so ci.yml's default-depth checkouts cannot run it" | names the `gates` job as the full-depth one and the `workflows` job as the one that never reaches the mode |
| 2 | `ec/tools/verify_reassembly.py:1313-1320` (comment) | "The agent stages check out with `fetch-depth: 0` and can run it; both of ci.yml's checkouts are default-depth and cannot resolve the revisions §14f names at all." | the four jobs that run the gate, all `fetch-depth: 0`; ci.yml's other checkout named as the default-depth one that runs only the two linters |
| 3 | `ec/tools/verify_reassembly.py:1321-1327` (`HISTORY_REQUIREMENT`, printed to the user on a revision that will not resolve) | "A default-depth checkout -- actions/checkout's default, which is what ci.yml uses -- has neither revision" | "which is what ci.yml's `workflows` job uses, though that job runs no history reader" |
| 4 | `ec/tools/measure_index_repair_visibility.py:107-124` (comment and string) | "The agent stages and ci.yml both check out with `fetch-depth: 0`" — a claim that `ci.yml` has one checkout, which it has two of | the jobs that run a history reader, and `ci.yml`'s `workflows` job named as the default-depth example |
| 5 | `ec/ghidra/README.md:800-817`, correction at `:806` | "both of `ci.yml`'s checkouts are default-depth and cannot resolve `08b72e2` at all, which is why it is a full-clone command and **not part of the per-commit gate**" | *is* part of the per-commit gate, via the `gates` job and `agent-gates.sh:160-163` |
| 6 | `docs/findings.md` §14f, correction at `:3380` | "the agent stages have one (`fetch-depth: 0`) and `ci.yml`'s two checkouts do not" | every job that runs a history reader has one, `ci.yml`'s `gates` included |
| 7 | `docs/agent-pipeline.md` item 3, correction at `:99` | heading "**`--verify-provenance` needs a full git history, and `ci.yml` does not have one**"; body "both of `ci.yml`'s checkouts (`:34`, `:64`) are default-depth" and "it is not in the gate for that reason" | heading names the jobs rather than the file; body's stale line refs repointed and its 2026-09-23 state marked as the record it is, since the decision paragraph below it landed the next day |

Two of the seven are the tools' own contract paragraphs, and site 4's comment
is itself the record of the divergence: before this change it said the sentence
was *"worded from what the workflows say today rather than carried over from
`verify_reassembly.py`'s own copy of that sentence, which was written before
`ci.yml` moved to a full checkout and no longer matches it."* That was
accurate as a description of the state on 2026-09-25, and after this change it
is a description of nothing — the two copies now agree — so the comment says
so. Leaving it would have been a fifth copy of the same claim, in a file whose
subject is whether two copies agree.

## Why the two copies drifted, and why nothing caught it

`verify_reassembly.py`'s sentence was written before `cc2ab10d`.
`measure_index_repair_visibility.py`'s was written after it and noticed the
sibling was stale — which is the whole of the one divergence that was ever
recorded anywhere. The gap the two left between them is that each is a
*description* of a workflow, held by no mechanism: the workflow can change and
the sentence cannot notice, because the sentence is prose and the workflow is
YAML and nothing reads both. `docs/agent-pipeline.md`'s item 3 is the sharpest
case, because there the two halves sat eleven lines apart in the same file, one
of them dated the day after the other, and no reader of the first has to reach
the second to be misled.

The issue asked whether the two tool copies could share one definition. **No,
and this is the reason:**

- The strings differ by a word each — "This mode" against "This tool" — and a
  shared module would impose one wording on both tools' failure messages, which
  are user-facing and about different programs.
- The repository has already tried the other direction and declined it: the
  sibling already *copies* `git_lines()` "with attribution" from
  `verify_reassembly.py` (`:136`) rather than importing it, and the tools in
  `ec/tools/` are not a package and are not importable by name from outside
  their directory. A shared constant would be a second import edge into a
  directory whose files deliberately do not have one.
- **The thing that failed here was not the sharing decision.** It was that
  nothing compared the copies against the workflows. A checker is the fix for
  that; a shared string would not have been.

**Generating the sentence from the workflows at run time was also declined.** It
would make the staleness impossible rather than detectable, and it is tempting
for that reason. It was not done because it puts a YAML parse inside a failure
path whose entire job is to be readable at the moment git has just failed — a
reader holding a `HISTORY_REQUIREMENT` on a shallow clone should not be waiting
on a file parse to be told what to do — and because a module docstring cannot be
generated at all, so the site that was wrong longest would be the one the
mechanism could not reach.

## `ec/tools/check_history_checkouts.py`

A new file rather than a mode on either sibling, per `CLAUDE.md`'s rule: those
two read git history, this reads the workflows. Two halves that stay separate
because their failure semantics differ.

**The measured half**, which is the part that earns the file. It parses every
`actions/checkout` step under `.github/workflows/`, resolves each step's
effective depth (the explicit `fetch-depth`, or the action's default of 1), and
prints the table above. Then it asserts one invariant, the *inverse* of the
claim that was stale: **every job that runs a history reader has a full-depth
checkout.** A job's step is a history reader when its `run:` names
`.github/scripts/agent-gates.sh`, `--verify-provenance`, or
`measure_index_repair_visibility.py` — decided from the committed files rather
than from prose, and deliberately not from the *name* `verify_reassembly.py`,
because `--check` is that tool's cheap tier and never touches history.

This is the failure the tool exists to catch. A re-copy of `ci.yml` from the
`agent-pipeline` template that drops the `fetch-depth: 0` does not break any
job: the `gates` job still runs the gate. It turns the cheap gate red with a
**history requirement** message that reads like a provenance failure rather than
like a workflow accident, and a reader chasing it would go looking at the
firmware. Demonstrated on a scratch tree by
`ec/tools/test_check_history_checkouts.py`, which deletes the `fetch-depth: 0`
from a synthetic `gates` job and watches the checker fail on it.

**The reported half**, which never fails the tree. It locates every sentence in
the two tools that makes a depth claim about a workflow, prints each with its
`file:line` and the derived fact it should have come from, and asserts the one
rule that is decidable without reading English meaning: **a sentence that
asserts a workflow's checkout depth names the job.** All four stale sentences
fail that rule — "ci.yml's checkouts", "ci.yml uses", "both of ci.yml's
checkouts" name no job — and all four corrected ones pass. The rule is a floor
and not a proof: job ids here are ordinary English words (`plan`, `fix`,
`gates`), so a sentence that names one by accident passes, and a sentence that
names the *wrong* job also passes. What it holds is the defect's shape, not its
content.

The line number it reports is the depth word's, not the sentence's. The
docstring's claim sits eleven lines below the `Usage:` line it belongs to,
because a list of commands is not prose and nothing in it ends a sentence until
the last comment does; a citation to where the sentence starts sends a reader to
the wrong line, and one to where the claim is written does not.

**What it does not find, said as "not found by this method"** rather than as
absent, per `CLAUDE.md`'s rule and `ec/annotations/registers.yaml`'s own caveat:
a checkout behind a composite action, a `fetch-depth` that is a `${{ }}` rather
than a literal, a workflow file that will not parse, a job that reaches the gate
from its prompt rather than from a `run:` step, and anything outside
`.github/workflows/` — `docs/ci/agent-gates-deep-schedule.yml` among them. The
prompt case is not hypothetical: `agent-conflicts.yml`'s `resolve` job does run
the gate, from the prompt at its `:248`, and this run does not count it. Its
checkout is `fetch-depth: 0` anyway, which is the sentence's own half of the
truth and the reason nothing is at risk today.

### The checker run against the tree as it stood before this change

The control for all of it — the checker, pointed at a scratch root holding the
pre-#1009 sources and a `ci.yml` whose `gates` job has lost its
`fetch-depth: 0`, exits 1 on five problems: the shallow `gates` job, and four
sentences, at the lines below. This is the evidence that it is a check and not
a report.

```
FAIL ci.yml/gates: runs '.github/scripts/agent-gates.sh' but its checkout is
     depth 1 (actions/checkout default), not `fetch-depth: 0` -- the mode will
     report a history requirement rather than an answer
FAIL ec/tools/verify_reassembly.py:81:   … names ci.yml and no job of it …
FAIL ec/tools/verify_reassembly.py:1313: … names ci.yml and no job of it …
FAIL ec/tools/verify_reassembly.py:1319: … names ci.yml and no job of it …
FAIL ec/tools/measure_index_repair_visibility.py:117: … names ci.yml and no job …
```

(The four line numbers are the depth word's line, as the tool reports them
everywhere: `:81` is `needs a full clone,` in the docstring's usage block, whose
`ci.yml` half is the next line. On the corrected file the same tool reports
`:82` for that site, because the correction ends a sentence where the old text
did not and the claim is now a sentence of its own. Nothing about the count
changes — five problems either way, one of them the checkout and four of them
the sentences.)

## The suite, and why the checker needed one

`ec/tools/test_check_history_checkouts.py`, picked up by `tools/run-tests.sh`
by `find` with no edit to it. Testing a checker matters more than usual here
because **a checker that has quietly stopped finding anything is
indistinguishable from one that is working** — the same failure
`tools/run-tests.sh:97-102` refuses to accept for an empty glob, one level up.
The committed tree satisfies both claims today, so nothing in it can show the
tool has teeth; the scratch-tree cases are the ones that can, and the four stale
sentences are pasted into the suite **verbatim from the pre-#1009 sources,
line breaks and quoting included**, because a paraphrase that happened to name a
job, or that lost the wrap a claim sits across, would be a control passing for
the wrong reason.

**Not in any gate**, and for the reason
`tools/test_agent_gates_patches.py` and `tools/test_readme_suite_table.py` are
not either: `agent-gates.sh` is copied from `ElDavoo/agent-pipeline`, so a gate
call is an upstream change and a re-copy rather than a line here, and this
branch's token has no `workflow` scope. It runs under `tools/run-tests.sh`,
which is where those two live.

## Two facts recorded for other issues

**#997's "the tree's only suite that reads git history" is no longer true of
the tree, and no committed file carries the sentence to correct.** Grepped for
it; there is nothing here to retract. What is true instead:
`ec/tools/test_measure_index_repair_visibility.py:373-391`
(`CommittedRepairTests`) resolves both repair revisions and their first parents
in `setUp` and *skips* when the clone is shallow — so it reads history and
degrades to a skip rather than a pass. `verify_reassembly.py --verify-provenance`
is the other reader, through the gate. Recorded here so #997 can pick it up in
whichever of the two lands second, which is what the issue asked for by naming
it.

**A prose contract duplicated across tools has no mechanism holding the copies
together.** The shared-definition option is declined above with a reason, and
the checker reads two of the copies. That is enough to keep *these* two
sentences honest and not enough to be general: a third tool with the same
paragraph would be a fourth sentence this checker does not read. The underlying
question is open, and is not resolved by what is on this page.

## What is not claimed

- That `--verify-provenance` has ever passed in CI. Nothing here runs it, and
  the fact that `ci.yml` puts it in a full-depth checkout says what the workflow
  asks for, not what a runner observed.
- That the corrected sentences are *exhaustive* of the claim's blast radius.
  `check_history_checkouts.py` reads the two tools it was written for; a
  sentence in a third file is not found by this method.
- Any verdict of any tool, any register status, and any hardware or Windows
  fact. None of this needs a laptop, and none of it produces a hardware claim.
