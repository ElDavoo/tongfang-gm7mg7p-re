# A gate reached from a `prompt:` was outside the invariant, and the count was three where the prose says four (issue #1032)

**Nothing here is a hardware, Windows or firmware claim, and nothing here is a
claim that `--verify-provenance` has ever passed in CI.** No EC is opened, no
register is read back, no image is re-encoded, and no laptop is involved. What
follows is read out of committed files: the workflows under `.github/workflows/`
and one tool's own output over them. A workflow that says a job runs a gate is
not an observation of that gate having run, and the same is true of a workflow
that says a job checks out with `fetch-depth: 0`.

**The finding in one line.** `ec/tools/check_history_checkouts.py` derived a
checkout depth for every `actions/checkout` step in the repository's workflows
and asserted that every job running a history reader has a full-depth one. It
found a reader only in a step's `run:`, so it counted **three** jobs where the
corrected prose names **four**. `ec/tools/verify_reassembly.py:1315-1317`
enumerates them — *"ci.yml's `gates` and the agent stages' `implement`, `fix`
and `resolve`"* — while `docs/agent-pipeline.md` item 3's heading
(*"every job that reaches it has one"*) and [`../findings.md`](../findings.md)
§86 (*"every job that runs a history reader has a full-depth checkout"*) state
the same claim as a rule rather than as a list, so three is a count of three
places naming the four and a count of one place disagreeing. The fourth job,
`agent-conflicts.yml`'s `resolve`, reaches the gate from its `prompt:` and from
nowhere else. **The prose was right and the checker was reading less than the
prose**, and the difference is exactly the case the file exists to catch: a
template re-copy dropping `fetch-depth: 0` from that job would break no job,
turn no gate red, and leave this checker green.

**The tool is not wrong about the tree, and this changes nothing about it.**
`resolve` is `fetch-depth: 0` today and was before this change. What changed is
what the method can *see* — the prompt case moves from *not found* to *read*,
which is a different claim from a change in what the workflows do, and
`CLAUDE.md`'s calibration rule is why the two are kept apart here.

## The rule, and the two sites it separates

The marker set is unchanged — `HISTORY_READERS` is matched exactly as it was
before, on the same three strings. What changed is *where* it is looked for, and
the difference between the two prompt sites in this tree is mechanical rather
than a judgement about English:

- A step's `run:` is **executed by the runner**, so a marker anywhere in it is
  a run. Unchanged, and still a plain substring test.
- A `prompt:` is **read by a model**, so a marker in one is a run only where
  the *marker itself* is in command position: the first non-whitespace text on
  its line, which is how an indented block spells a shell line.

The test being on the marker and not on the line is the whole of it, and
`agent-review.yml` is what shows why. Its marker at `:169` is the fourth word of
a line that begins `- a gate weakened rather than satisfied --`, so the line's
first non-whitespace text is a hyphen. A rule that asked only whether the line
had *any* text on it would count `review` — and that mistake was made and caught
while this was written, which is why the rule is stated this way and why the
suite has a case that rejects the looser form (see below).

| site | shape | a reader? |
|---|---|---|
| `agent-conflicts.yml:248` | alone on an indented line | **yes** — this is the change |
| `agent-fix.yml:220`, `:279` | alone on an indented line | already counted via `run:` at `:316-317` |
| `agent-implement.yml:291` | alone on an indented line | already counted via `run:` at `:337-338` |
| `agent-review.yml:169` | fourth word of a bullet, inside a review criterion | **no** — guidance, not a run |

`fix` and `implement` reach the gate both ways, so the count moves by exactly
one: three becomes four, and the job added is `resolve`.

**`history_reader()` is now `run_reader()`, and the rename is the point of it.**
The issue named the function that returned `step.get("run")` and nothing else,
which was an honest name for a function that had only one place to look. With a
second place to look it would be a name that did not say which, so it reads
`run_reader()` and its prompt-side siblings are `prompt_text()` and
`prompt_mentions()`. `Job` gained `route` and `named` beside `reader`; `reader`
itself is still the bare marker string, because `depth_problems()`'s messages
are about the marker and their wording is held by the suite.

**A `run:` outranks a prompt when a job has both.** The route is reported
beside each job for that reason — a `run:` is executed and a prompt is read, so
the step is the route a checkout depth can be held against. `fix` is on the list
for the one that does not depend on a model reading the sentence.

## Both branch reports, transcribed

Not summaries. The first is the tool as it stands on `origin/main`
(`git show 5244f119:ec/tools/check_history_checkouts.py`) run over this tree,
the second is this change's. **The revision is named rather than written
`HEAD`, because `HEAD` is this branch's tip and the tip holds this change's
tool** — a reader who ran that command would get the four-job version and
wonder what the three-job one was. Every "before" line on this page is that
revision's.

```console
$ python3 ec/tools/check_history_checkouts.py
  ...
3 job(s) run a history reader: fix (.github/scripts/agent-gates.sh), gates (.github/scripts/agent-gates.sh), implement (.github/scripts/agent-gates.sh)
  every job that runs a history reader has a full-depth checkout
```

```console
$ python3 ec/tools/check_history_checkouts.py
  ...
4 job(s) run a history reader: fix (.github/scripts/agent-gates.sh, from a run: step), gates (.github/scripts/agent-gates.sh, from a run: step), implement (.github/scripts/agent-gates.sh, from a run: step), resolve (.github/scripts/agent-gates.sh, from its prompt)
  every job that runs a history reader has a full-depth checkout
named in a `prompt:` but not read as a run, because the marker is not in command position:
  agent-review.yml:169 review: .github/scripts/agent-gates.sh -- in a sentence, not a command, so this method does not count it a reader

not found by this method, which is not the same as absent: a checkout behind a composite action; a `fetch-depth` that is a `${{ }}` rather than a literal; a `prompt:` that is not a string; a workflow file that will not parse; a marker in a prompt behind another word on its line, so `bash .github/scripts/agent-gates.sh` is not counted; a marker in an `env:`, an `if:` or a YAML comment, where `ci.yml:11` is the committed case; and `docs/ci/agent-gates-deep-schedule.yml`, which is prepared rather than landed and so outside the glob read above
```

**The number and the exit code together are the claim.** The count moved from 3
to 4 while the verdict stayed clean, and the job that appeared is named rather
than counted: a count that moved because something *else* was counted would
show up as a different name in the list. Both runs exit 0, because the tree is
correct — and a run that exits 0 says nothing about coverage, which is the
second thing this change is for.

## The failure itself, on a tree built to have it

The committed tree is correct, so nothing in it can show the widened rule
firing. This scratch root is the shape the issue describes: one job, a
default-depth `actions/checkout`, and a `prompt:` that puts the gate in command
position — i.e. exactly what a re-copy of `agent-conflicts.yml` that dropped
`fetch-depth: 0` from `resolve` would leave behind. The committed tool first,
pointed at it with `--repo`:

```console
$ python3 ec/tools/check_history_checkouts.py --repo /tmp/scratch-wf   # before
check_history_checkouts.py: every actions/checkout under .github/workflows/.
  s.yml / s / Checkout: depth 1 (the action's default)

no job's `run:` names a history reader -- not found by this method, which is not the same as there being none
  every job that runs a history reader has a full-depth checkout

0 sentence(s) in the two tools assert a checkout depth:
  every one of them names the job of every workflow it names
$ echo $?
0
```

**That is the issue in five lines.** The job does run the gate, the gate cannot
run, and the tool prints its verdict line — *every job that runs a history reader
has a full-depth checkout* — and exits 0. The line is vacuously true, which is
the whole failure: nothing was found to be wrong, and a reader has no way to
tell that from a clean run over a correct tree. The same tree, after:

```console
$ python3 ec/tools/check_history_checkouts.py --repo /tmp/scratch-wf
check_history_checkouts.py: every actions/checkout under .github/workflows/.
  s.yml / s / Checkout: depth 1 (the action's default)

1 job(s) run a history reader: s (.github/scripts/agent-gates.sh, from its prompt)
  1 job(s) do not

not found by this method, which is not the same as absent: a checkout behind a composite action; a `fetch-depth` that is a `${{ }}` rather than a literal; a `prompt:` that is not a string; a workflow file that will not parse; a marker in a prompt behind another word on its line, so `bash .github/scripts/agent-gates.sh` is not counted; a marker in an `env:`, an `if:` or a YAML comment, where `ci.yml:11` is the committed case; and `docs/ci/agent-gates-deep-schedule.yml`, which is prepared rather than landed and so outside the glob read above

0 sentence(s) in the two tools assert a checkout depth:
  every one of them names the job of every workflow it names

  FAIL s.yml/s: runs '.github/scripts/agent-gates.sh' but its checkout is depth 1 (actions/checkout default), not `fetch-depth: 0` -- the mode will report a history requirement rather than an answer
check_history_checkouts.py: 1 problem(s). The history requirement itself is unchanged by any of this; what is at issue is the sentence describing which job needs it.
$ echo $?
1
```

**Pasted whole rather than trimmed, and the last three lines are `stderr`.** The
report is `stdout` and the two `FAIL` lines are `stderr`, so the block is the
order a terminal shows them in and a reader piping `stdout` alone would see the
whole report and neither the failure nor the exit code — which is the other half
of why the report and the count have to be read together.

The marker is printed back, the route is `from its prompt`, and the depth is
named. `ec/tools/test_check_history_checkouts.py`'s
`test_a_gate_in_a_prompt_on_a_shallow_checkout_is_a_failure` holds the same
shape as a case.

## Why counting, and not naming

The issue offered two acceptable outcomes: count a prompt-reached job, or name
it in a *reached from somewhere this method does not read* list beside the
table. Both are now done, and they are not alternatives — but the counting is
what makes the failure visible, and the naming is what keeps the rule's misses
visible. Naming alone would have left the checker green through exactly the
re-copy the file exists to catch, which is the state the issue was filed
against. So the invariant widened, and the report gained the second line
regardless.

**`review` is named, not counted, and that is the rule being right.** A prompt
is not an execution, `review` runs no gate and needs no clone, and putting a
job that runs none inside a full-depth invariant would be the rule being wrong
rather than strict. It is left out of the invariant and put in the output.

**Whitelisting prompts to `anthropics/claude-code-action` steps was considered
and rejected.** The `uses:` set is exactly what a template re-copy rewrites, so
a whitelist reintroduces the template-coupling the tool exists to shed, one
level down. Reading `with: prompt:` on any step is the more general and more
stable rule and costs nothing today.

**`env:`, `if:`, the job name and YAML comments are deliberately not read.**
`history_reader()`'s docstring already declined them, and widening into them
would put `ci.yml:11`'s hand-written comment about the gate on a list of jobs
that run it. Those stay in *not found by this method*.

## What the suite shows, and what it cannot

`ec/tools/test_check_history_checkouts.py` grew from twenty-four cases to
thirty-two, and to **thirty-nine** at the merge this write-up lands in, where
#1034's six cases and #1039's one case on the same suite arrived in the same
window and are kept whole — the `twenty-four`, the `thirty-two` and the
`thirty-eight` this suite read at the earlier merge stay written per
[`../findings.md`](../findings.md) §4a-4d, and none of the seven is a case this
issue's rule decides. Four of the new ones are the pair that matters — a
prompt-reached
gate on a shallow checkout **is** a failure, the same prompt on
`fetch-depth: 0` is not and the job is on the list, a marker inside a bullet is
neither, and a `with: prompt:` that is not a string yields *not found by this
method* rather than a count or a crash. Four more are committed-tree tripwires:
the reader set held as an exact `{workflow/job: (marker, route)}` dict rather
than a count, `resolve` added to the report case at the foot, and the not-counted
line checked from both sides — `review` absent from the reader list *and*
present at `agent-review.yml:169`, with the citation resolved against the file
so the line number means something.

**The looser form of the rule was tried and is rejected by four cases.** A rule
that tested whether the prompt's line had any text on it counts `review`; run
against the suite as shipped, that variant fails four cases. It was not a
hypothetical — it was the first implementation, caught because the committed
tree has a bullet whose marker is mid-line.

**What this suite still cannot show.** The committed tree satisfies the
invariant, so only the scratch cases can demonstrate the widened rule has teeth.
And a checker that has quietly stopped finding *anything* prints the same clean
report — which is why the committed cases are held by name and not by count, and
why the exact-dict tripwire matters more than the figure it replaces.

## What is still not found by this method

- A **checkout behind a composite action**, and a `fetch-depth` that is a
  `${{ }}` rather than a literal.
- A **`prompt:` that is not a string** — a list, a number, an expression handed
  in from elsewhere. It is read as nothing, exactly as a non-string `run:` is,
  rather than stringified into a line of prose that never existed.
- A **workflow file that will not parse.** Named, and the rest of the tree still
  read.
- **A marker in a prompt behind another word on its line.** A prompt spelling
  the command `bash .github/scripts/agent-gates.sh` is *not* counted. Where a
  shell command ends inside a line of prose is not decidable mechanically, and a
  list of command prefixes would be the whitelist rejected above.
- **A marker in an `env:`, an `if:`, a job name or a YAML comment.** `ci.yml:11`
  is the committed case.
- **The line a marker in a *folded* prompt block is reported on.** Folding joins
  the lines with spaces before the text is a value, so such a marker is reported
  at the block's first line — where the text begins — rather than on a line it
  may not be on. Every prompt in this tree is a literal block, where the
  resolution is exact.
- **`docs/ci/agent-gates-deep-schedule.yml`**, which is prepared rather than
  landed and so outside the glob. Its `fetch-depth: 0` and its comment naming
  `--verify-provenance` are both recorded in
  [`history-checkout-claims.md`](history-checkout-claims.md). Not found by this
  method, which is not the same as absent.

**Out of scope, and stated rather than left implied.** No file under
`.github/workflows/` or `.github/actions/` is edited: the issue is *about* a
workflow and the change is to a tool that reads it, and this branch's token has
no `workflow` scope. The tool is not wired into `agent-gates.sh`, which is
copied from `ElDavoo/agent-pipeline` — its suite is already picked up by
`tools/run-tests.sh`'s `find`. `ec/tools/verify_reassembly.py:1315-1317`,
`docs/agent-pipeline.md` item 3 and [`../findings.md`](../findings.md) §86
already carry the four-job claim and are correct today; none of them is edited,
and **the agreement between them and the tool is the point of this change, not
a further correction to them.**
