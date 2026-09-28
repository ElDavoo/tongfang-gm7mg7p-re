# What the linters say about the prepared nightly, and what now holds it

Issue [#774](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/774)
asked for three things about `docs/ci/agent-gates-deep-schedule.yml`: a
measurement of what `ci.yml`'s two linters say about it, an offline check of the
shape `docs/agent-pipeline.md` item 1 describes, and a decision about where
that check lives. Two are done and the first is **partial** — the linters
could not be run, and this write-up says so rather than writing down a green
result nobody observed.

**Nothing here is a live test, and nothing here is evidence about the
firmware.** No EC is opened, no register is read back, no capture is taken, and
no laptop, EC or Windows machine is involved. The subject is a YAML file a human
copies into `.github/workflows/`, and every claim below is about its text.

## The claim was not being enforced, and the sentence saying so was false

The file's header said:

> Why it is written to pass the `workflows:` job in ci.yml (actionlint and
> zizmor) before it lands: that job audits every file in this directory, so
> getting the action pin and the permissions right now is cheaper than getting
> them reviewed after a human has copied the file.

The first half is the issue's own reading and the tree confirms it.
`.github/workflows/ci.yml:82` runs `/tmp/actionlint -color` with no path
argument and `:90` runs `/tmp/zizmor --offline --color=always
.github/workflows/` with exactly one; neither is pointed at `docs/ci/`, and a
search of the tree finds no other consumer.

So **that job audits every file in this directory** is false, and it was the
load-bearing clause: with nothing enforcing it, the "cheaper now than after the
copy" argument had no force, and the first machine to see the file through
either linter was a human's, on the day they ran the `cp` — the moment the
sentence itself calls the expensive one. The old wording is left visible beside
its correction in the file's own header, per `docs/findings.md` §4a-4d.

**One correction to the issue's own attribution.** Its "Done looks like" clause
asks that `docs/agent-pipeline.md` item 1's *"that job audits every file in this
directory"* be made true or corrected in place. That sentence is not in
`docs/agent-pipeline.md` — it is in the schedule's header, and the correction
lands there, where the false claim is. Item 1 (`:52-79`) makes no comparable
claim; it correctly says the file is prepared and a human `cp`s it. Editing a
correct sentence in a shared document to look responsive would have cost a
merge-conflict site for nothing, so `docs/agent-pipeline.md` gets one sentence
at the end of item 1 naming the measurement and pointing here, and nothing
else.

## The measurement, and the part of it that could not happen

The plan had both linters downloaded at the versions and SHA-256s `ci.yml:73-74`
pins — actionlint `v1.7.12` (`8aca8db9…`), zizmor `v1.29.0` (`dd96df04…`) — and
run over the file twice: in place, and on a copy at
`.github/workflows/agent-gates-deep.yml` in a scratch tree. The second run is
the one that matters, because the landing is the second one.

**The download did not happen.** The stage that wrote this had no network: the
`curl` at `ci.yml:78-89` was refused by the execution sandbox, neither binary
was on `PATH`, and no source for either is vendored. So neither linter ran over
this file, at either path, and there is no result to report for either. **Any
statement that this file passes actionlint or zizmor is currently unmeasured**,
and the file's header says so in the same words rather than leaving a green
check standing in for one.

What *was* measurable is the one check of actionlint's three that needs no
download: shellcheck over every `run:` block, which is what actionlint runs
internally. Recorded on 2026-09-28, at `/usr/bin/shellcheck` 0.9.0, under
actionlint's own invocation:

```sh
shellcheck --norc -f gcc -x --shell=bash -e SC1091,SC2086 <block>
```

All three blocks — `Name the assembler`, `Deep gates`, `Emit the per-row CSV` —
exit 0 with no output, both where the file is prepared and on a byte-identical
copy at the landing path in a scratch tree carrying
`.github/actions/project-setup`. The two placements are byte-identical by
construction, so the same three blocks are being read; running it twice is
recorded because the landing is the run that matters and a reader should not
have to derive that the two agree.

**This is a lower bound and not a substitute.** The shellcheck here is the one
this stage happened to carry, which is not necessarily the one `ubuntu-latest`
ships; `project-setup`'s own description says it is preinstalled there, and
which version is not something this tree can say. And actionlint's other two
checks — every `${{ }}` type-checked against the event payload, and the syntax
of each `run:` block — were not run, nor were zizmor's audits beyond the two
held offline below.

The `uses: ./.github/actions/project-setup` question the plan flagged is
therefore **still open**: whether actionlint resolves a local `uses:` against
the repository root or against the file's own directory decides whether an
in-place run reports a missing local action, and this tree cannot answer it
without the binary. It matters because such a finding would be an artefact of
where the prepared file lives rather than a defect in it, and "fixing" it by
rewriting the `uses:` would break the real landing.

## Where the check lives: both, named for what each is

**`docs/ci/ci-workflow-lint-docs-ci.patch` — the honest answer.** One step
appended to `ci.yml`'s `workflows:` job. It copies the file to
`.github/workflows/agent-gates-deep.yml` and runs both linters over the copy.
Prepared rather than landed, because `.github/` is template-copied and the
pipeline's push token has no `workflow` scope.

The copy is used **without** the measurement having decided it, and not as a
guess: it is right under either answer to the question above. The claim being
protected is that this file passes the linters *in the state it will be linted
in*, and that state is a copy at the landing path — it is what the human's `cp`
does, and what the step above already lints. The in-place form tests a state
the file will never be in and carries a failure mode the copy does not. And
**the copy cannot make CI redder than the human's `cp` already would**: if
actionlint does report the local action as missing, it reports it for this copy
at the landing path too, and it will report it on the day the file is actually
landed, with or without this patch. This surfaces the same finding a few weeks
earlier; it does not create one.

**Verified in this branch, and not run:** `git apply --check` against the
committed `ci.yml` in a `tempfile` scratch tree, exit 0, and the applied file
parses as YAML with the new step third in the `workflows:` job and both of its
`run:` blocks clean under the same shellcheck invocation. **Neither linter was
executed against it**, for the reason above. The patch's own header says this,
and tells a human to run it on a branch before landing it — a patch that turns
a green job red is the cheapest way to get a lint switched off.

**`tools/check_deep_schedule_shape.py` — the floor, and the only one of the two
that runs today.** The patch is prepared, so between now and the day a human
lands it nothing lints this file. The floor holds five claims decidable from
committed bytes: a `cron:` schedule plus `workflow_dispatch`; the gate script
invoked once and as `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh`; that
invocation teed downstream to a path under `$RUNNER_TEMP`; top-level
`permissions: contents: read` with no job wider; and every `uses:` a 40-hex SHA
or a local path that resolves. The last two are zizmor's two audits over a file
like this one, held offline — **which converts the unmeasurable-in-CI part of
the lint into something that runs per commit, and is the whole argument for
having it.**

It is a complement to `tools/check_deep_schedule_emit.py`, not a second opinion
on it. That checker holds the *second artifact*; this one holds the file as a
*workflow*. The two share `shell_code()` and `RUNNER_TEMP_SHELL` rather than
restating them, so a prepared file cannot be clean to one and red to the other
over a comment or a `$RUNNER_TEMP` spelling, and
`tools/test_check_deep_schedule_shape.py` holds the disjointness in both
directions through the two exit codes.

**The floor is not the job and does not read as it.** Its own closing line
names the two things it does not hold — `set -o pipefail` before the tee, and
everything actionlint and zizmor do beyond the two audits — and points here.

## The `docs/ci/` reading, re-derived

The issue said `docs/ci/` "now holds four prepared artifacts". That was a census
of the tree at some earlier point, and `CLAUDE.md`'s no-hand-kept-totals rule is
about exactly this, so here it is as a dated observation with the command
beside it rather than as a number repeated anywhere else. On 2026-09-28, before
this branch:

```sh
ls docs/ci/; for p in docs/ci/*.patch; do grep -m1 '^--- a/' "$p"; done
```

eight files: seven `.patch`, every one of them in
`tools/test_agent_gates_patches.py`'s `PATCHES` list and every one of them
cutting `.github/scripts/agent-gates.sh` at `:64`, plus the one `.yml`. This
branch adds a ninth, `ci-workflow-lint-docs-ci.patch`, which cuts
`.github/workflows/ci.yml` — which is the next paragraph.

The exclusion comment at `tools/test_agent_gates_patches.py:82-86` (the issue
cites `:64-66`) is right about *staleness* and says nothing about the lint, and
the issue is right that the patch route does not cover the `.yml` at all.

**This branch's own patch cannot join that set, and that is not an oversight.**
`PATCHES`, its `classify()`, its `scratch_tree()` and every case above it are
against one pre-image, `.github/scripts/agent-gates.sh`. A patch cutting
`ci.yml` would fail `git apply --check` against that file, have none of its
added lines in it, and classify as `STALE` — a red that means nothing. Adding
it would be worse than leaving it out. The name is chosen so neither existing
*discovery* picks it up: `test_agent_gates_patches.py:121` globs
`agent-gates-*.patch` and `check_doc_patch_refs.py`'s `on_disk()` (`:262`)
globs the same family, so `ci-workflow-lint-docs-ci.patch` is outside both,
and **no shared suite is edited to accommodate it.**

**One correction to the plan's reading of that, and it cost a red run here.**
The plan expected `check_doc_patch_refs.py` not to reach the new file "in
either direction". It does not reach it in the direction the plan meant — the
*uncited* one, which is `on_disk()` against the name set. It **does** reach it
in the other: the *reference* direction, where a name prose gives is resolved
against that same `on_disk()`. A first draft of this branch's `tools/README.md`
row cited the patch as a **markdown link**, and `LINK` (`:197`) matches any
markdown link whose target ends in `.patch`, whatever the name is — so a
reference to a prepared change outside the `agent-gates-` family reads as
stale, and four cases in `tools/test_doc_patch_refs.py` went red. The row now
cites it the way `NAME` (`:183`) reads a citation, as a backticked name, which
the `agent-gates-` prefix being required makes invisible. The suite was not
edited either way; only the row was.

It then caught this paragraph. A first draft explained the rule by writing the
pattern out, and a link-shaped fragment naming a file that is not there is
exactly what `LINK` is for — so the sentence *about* the trap tripped it. The
rule is now described rather than reproduced, which is the only form of writing
it down that does not commit the mistake.

What survives that is narrower than the plan said and more useful than it
expected: `check_doc_patch_refs.py` holds this patch's **citations**, the same
half it holds for the other seven, and nothing holds its **staleness**.

Verified: the `PATCHES` list is unchanged at seven, `discover_patches()` returns
the same seven, and `check_doc_patch_refs.py --check` is green with the new file
on disk.

The cost is stated rather than hidden: **nothing holds this patch against
staleness.** That is the same gap the suite's own docstring records for
anything in `docs/ci/`, and it is named as the next issue.

## What is still not held, and what this opens

- **`set -o pipefail` before the tee.** The schedule's own comment calls it
  load-bearing — without it the pipeline's status is `tee`'s, which is zero
  however the gate ended, so a failing deep tier reads as a passing one, "the
  exact failure this file exists to stop". The new checker holds the tee and
  does **not** hold the `pipefail` beside it. It is not in the issue's five and
  adding a sixth rule unasked is a scope decision this branch does not make, so
  it is written down here instead. It is a one-line check and it belongs to
  whoever takes the floor next.
- **A suite holding the `ci.yml` patch against staleness.** It needs a second
  pre-image shape in `tools/test_agent_gates_patches.py`, a shared suite several
  branches are near. That is the next issue, not this branch.
- **Wiring the floor into the cheap tier.** `.github/scripts/agent-gates.sh` is
  template-copied, so the route is another prepared patch in the `agent-gates-*`
  set — and `docs/findings/history-checkouts-gate-wiring.md` records that the
  free `gate`-line anchors in it are already spent, which is why two earlier
  checks were folded rather than added. Folding a third into a patch another
  branch may also be editing is a merge conflict bought on purpose. The checker
  is discovered by `tools/run-tests.sh` and named in `tools/README.md`'s table;
  that is its whole wiring here.
- **The measurement itself, on a machine with a network.** Whoever has one runs
  both linters at `ci.yml`'s pinned versions over the file at both paths, and
  the answer either confirms the header's claim or retracts it in place. Until
  then the claim stays unmeasured, which is the honest state and not a defect
  in the file.
