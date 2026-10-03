# The exit code deliberately does not read the count of graded windows in no block, and the comment now says so (issue #552)

The write-up for [issue
#552](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/552), which asked
what [`grade_0751_isolation.py`](../../ec/tools/grade_0751_isolation.py)'s exit
expression is *meant* to cover now that `graded_unplaced` exists. It is a
**held decision, recorded where the expression is accounted for and pinned by
tests. No exit code moves, no output byte moves, and the diff to the tool is a
comment.** Nothing here is a register behaviour and nothing here is evidence
about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value, and §7 is the call the output feeds.

---

## The decision

**Unchanged, and stated as a choice rather than left as an absence.** The exit
code stays `1 if (void or unreads or withheld or repeated) else 0`, and
`graded_unplaced` is not read by it.

The argument is the vocabulary the accounting comment above the return already
uses: every term in that expression counts something the run *declined to
grade* — a window it would not print, or a value it would not grade twice.
`graded_unplaced` counts windows the run **read, printed with their rows, and
graded** — over an arm the labels cannot name. Folding it in would report a run
that read and graded every window it was shown as one that could not read
them, which is the one thing the closing section is careful not to say about
itself. It is a disclosure and not a refusal.

Three further reasons belong with it, and all three are in the comment rather
than only here:

- **The section already says it, in prose, where §7's call is read from.** The
  `elif graded_unplaced:` branch declines the capture-level comparison and ends
  on *"so the paragraph below is as far as this run goes."* A second
  machine-readable channel for the same fact would be one fact owned twice, and
  the prose is the one an operator reads.
- **The term is structurally zero under `--block`**, so it could only move the
  exit code of a day-level run — and §6's documented command line passes
  `--block` per value. The day-level counterpart is **#506**, which is a named
  dependency and not a duplicate here.
- **`unagreed`'s fold into `withheld` is not the argument for this.** That is a
  *refusal* counted under a term already in the expression — a different shape,
  with its own `--block` semantics, argued in
  [`0751-grader-unplaced-window-block-scope.md`](0751-grader-unplaced-window-block-scope.md)
  ([#539]). A window that cannot be graded is not the case this is, and the two
  must not be argued from each other.

## Measured before deciding, over committed fixtures

Four ways — unscoped, and `--block` at `0xA0`, `0x10`, `0x00` — over the two
fixtures the decision rests on:

| fixture | scope | exit | count line | decline sentence |
|---|---|---|---|---|
| `unplaced-window/` | unscoped | 0 | fires | fires |
| `unplaced-window/` | `--block 0xA0` | 0 | **absent** | absent |
| `unplaced-window/` | `--block 0x10` | 0 | **absent** | absent |
| `unplaced-window/` | `--block 0x00` | 1 | absent | absent |
| `unread-window/` | unscoped | 1 | fires | fires |

Reproduce with the command in *What must not change* below, one fixture at a
time.

The `0x00` row is not this issue's business and is worth reading carefully
rather than skipping: that exit is 1 because the run **names no block in that
capture** — "the values under test are 0xA0, 0x10" — a refusal above the closing
section entirely. It is not the strays turning the exit on, which is exactly
what makes it a control: a different reason, the same 1.

The two middle rows are the structural zero, measured rather than assumed.
`unplaced-window/` unscoped is the case the issue is about, and it is the one
fixture where the count is the *only* thing the report has to say about those
windows: nothing was withheld, so there is no banner to point at. The count
line and exit 0 co-occur there, which is the co-occurrence the decision turns
on, and which the existing unscoped method already holds over that one run.

## What a comment-only change needs to be testable at all

A decision recorded only in prose rots silently, which is the failure this
issue was opened about: the accounting comment described a population the
report no longer had, and **nothing said the omission was a choice**. The
accounting comment is where the expression is already explained, so that is
where the answer belongs — and a comment is not something a test can reach
unless a test reads it.

`ec/tools/test_grade_0751_isolation.py` gains
`GradedUnplacedExitCodeTests`, a class appended at the end of the file with
three methods.

**What was already held, so the class does not repeat it.** The pairing this
decision turns on is not a gap.
`test_a_graded_window_in_no_block_is_scoped_where_the_prediction_is_read_from`
runs `unplaced-window/` unscoped once and already asserts, over that same
invocation, `rc == 0`, the count line `2 of the 8 … are in no block`, the
sentence declining the capture-level comparison, and both refusal sentences
absent. The per-block exit codes are held too:
`test_a_block_is_its_own_windows_over_one_in_no_block` loops `0xA0` and `0x10`
over the same fixture asserting `rc == 0` for each, and the method named above
already runs `--block 0xA0` and requires the count line absent. An earlier
version of this class restated most of that as if it were new; the review of
this branch found it, and it was deleted rather than hedged.

What was left is the two ends those methods leave open:

- **`test_the_decline_branch_ends_where_the_decision_says_it_does`** — the one
  assertion no existing method makes, and the sentence the decision leans on:
  the report declines the capture-level comparison *and then stops*, saying "so
  the paragraph below is as far as this run goes". The existing method holds
  where that branch begins; this holds where it ends, which is the whole reason
  a second machine-readable channel would be one fact owned twice.
- **`test_the_count_line_is_absent_under_the_second_block_too`** — the count
  line absent under `--block 0x10` on this fixture. The `0xA0` half is already
  asserted, and both values already assert `rc == 0`, but neither reaches the
  count line under the second value. Both values matter because §6 runs one
  attachment per value, and a zero held for only one would be a fact about the
  fixture and not about `shown`.
- **`test_the_exit_expression_says_it_does_not_read_the_count`** — reads
  `grade_0751_isolation.py`'s own source and requires the contiguous run of
  comment lines immediately above the return to name `graded_unplaced`, to call
  it *not a refusal*, and to say it is *left out on purpose*. It also requires
  the tool's own return line **not** to contain `graded_unplaced`.

  Reading the comment run rather than the enclosing function is load-bearing,
  and it is what makes the assertion say what it claims to. The block is not
  separated from the closing section above it by a blank line, so an extraction
  that reads back to the last blank line reaches into `main` — where every term
  is named by the code that reads it — and deleting the decision out of the
  comment entirely would leave the test green. Walked back from the return
  instead, the same deletion fails with `'graded_unplaced' not found`.

  The anti-fold-in guarantee comes from two assertions, not one.
  `assertEqual(source.count(anchor), 1)` is the one that turns red on a
  fold-in: the expression string no longer occurs, so it fails `0 != 1` before
  any assertion about the comment is reached. That alone is not enough — it is
  also satisfied by moving the test's own anchor to match the new expression —
  so the return line is separately required not to name the term. A fold-in
  that rewrites the comment alongside it, and moves the anchor to keep the
  count at one, fails there.

The source assertion anchors on the expression string, which occurs exactly
once in the file, rather than on a line number: `CLAUDE.md` is explicit that a
bare `file:NNN` in prose is true only until the next merge, and the same
applies to a test that anchors on one.

The class is **appended, not inserted inside `GradeTests`**, for the reason
`RefusedPairReadbackTests` records: a class added inside `GradeTests` moves
every `test_grade_0751_isolation.py:NNN` pin in the tree onto a line that no
longer says what its citing sentence says it does, and the citations are
reconciled against
[`test-line-pin-census.md`](test-line-pin-census.md) by
`check_pin_table_rows.py`. A class at the end costs nothing.

## What is pinned, by mutation

Each mutation was run against this branch's tool and the messages below are as
the runner prints them. **Not all three are red in this class**, and saying so
is the point of the table:

| mutation | what fails, and with what |
|---|---|
| add `graded_unplaced` to the return | the decline-branch method — `1 != 0`, the run's own exit code; and in the source method, the anchor count — `0 != 1` |
| neutralise the count the report prints (`UNPLACED_GRADED_NOTE`'s `{unplaced}` → `0`) | **nothing in this class.** The count line's text is asserted by `test_a_graded_window_in_no_block_is_scoped_where_the_prediction_is_read_from` and by others in `MarkSetTests`, and those are what go red |
| delete the two new comment paragraphs | the source assertion — `'graded_unplaced' not found` |

The first is the one the issue is about, and it is why the decline-branch method
is not redundant with the existing unscoped test. That test pins `rc == 0` *for
the exit expression as it stands*; this one fails when the expression changes
under it, so a fold-in turns the run's own exit code red rather than being
caught by a comment drifting out of date.

The second row is a property of the reduction, not a gap, and it is recorded
rather than papered over. This class does not assert the count line's text, so
it cannot catch a change to it; the methods that already did are what hold it,
and they go red when the note is neutralised. A write-up claiming this class
caught that would be claiming coverage it does not have.

The third is what a comment-only change is otherwise untestable without —
deleting the decision out of the comment is silent everywhere else in the tree.

The third mutation is worth reading as a correction rather than as a result. An
earlier version of this method read the comment back to the last blank line
above the return, which — there being no blank line between the block and the
closing section — reached into `main` and matched every term against the code
that reads it. Under that extraction the deletion above left the test **green**,
while the write-up and the PR description both said it went red. The extraction
walks back from the return line instead, and the failure above is the measured
consequence of that change rather than of the comment's content. Both readings
were re-checked against the tool as this branch now stands: after the deletion,
the walk-back extraction finds no `graded_unplaced` and the blank-line extraction
still finds one, having reached into `main`.
## What must not change, measured rather than asserted

The tool at the merge base and the tool at this branch's tip were run over
**every** `ec/tools/testdata/0751-isolation-run*/` directory four ways —
unscoped, and `--block` at `0xA0`, `0x10`, `0x00` — and each pair compared on
stdout, stderr and exit code:

    git show origin/main:ec/tools/grade_0751_isolation.py > /tmp/base_grade.py
    for d in ec/tools/testdata/0751-isolation-run*/; do
        for a in "" "--block 0xA0" "--block 0x10" "--block 0x00"; do
            python3 /tmp/base_grade.py $d*.csv $a >/tmp/base.out 2>/tmp/base.err; brc=$?
            python3 ec/tools/grade_0751_isolation.py $d*.csv $a \
                >/tmp/tip.out 2>/tmp/tip.err; trc=$?
            [ "$brc" = "$trc" ] \
                && diff -q /tmp/base.out /tmp/tip.out \
                && diff -q /tmp/base.err /tmp/tip.err \
                || echo "DIFFERENCE: $d $a ($brc vs $trc)"
        done
    done

**No difference on any of them.** This is a comment-only diff, so byte-identity
is the honest expected result rather than a lucky one; a difference here would
mean the diff is wrong. This is stated as a property of the loop rather than as
a count of directories on purpose — a directory census is a number every landing
fixture would have to edit, which is the trap `CLAUDE.md` names by name.
Re-run the loop against whatever the tree holds then.

The loop compares stderr and the exit code as well as stdout, and it compares
the merge base rather than `HEAD`: a branch that is ahead of `origin/main` by
nothing has no commit of its own to compare against, so `git show HEAD:` would
have diffed the change against itself and reported the result below on an empty
comparison.

`bash tools/run-tests.sh` is the checkable form of the tree's own state; this
write-up does not restate what it prints.

## Left out on purpose

- **Changing the exit expression.** Decided against, with the reasons above,
  not deferred. A distinct exit code, a stderr warning, and counting the term
  are each considered and rejected: the first two would move a code or a stream
  on §6's own per-value attachments to record a fact §7's own prose already
  states, and the third is the disagreement this write-up is about.
- **#506** (no day-level command line in §6) — named as the dependency that
  makes the structural zero matter. Until it lands, no documented command line
  reaches a run where this term is non-zero. Not duplicated here.
- **#513** (the live re-run `confirmed-inert` will be made on) and **#540**
  (the stale refusal-set enumerations in §6 and
  `ec/tools/testdata/README.md`). Different files; not reached.
- **§6 of `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`.** Its
  refusal-set enumerations are #540's and the day-level command line is #506's.
  #539 already recorded the same omission and why; repeating it is a second
  request asking one shared file the same question.
- **A new `testdata/` fixture.** Every case the decision rests on is committed
  and is reached by the existing ones; a new fixture would widen the shared
  fixture tree for no new case.
- **`docs/findings.md`** — frozen, and `check_findings_frozen.py` fails a change
  that adds a section. This finding is cited by file and heading.
- **`ec/annotations/registers.yaml`.** No register status is in question;
  `MANUAL_FAN_CTRL` stays `present-untested`.
- **`.github/workflows/` and `.github/actions/`.** The pipeline's push token has
  no `workflow` scope, so a branch touching them fails at the very end. The
  `--self-test` gate patch at `docs/ci/agent-gates-0751-self-test.patch` stays
  prepared and unlanded; landing it is a human's change.
- **Submitting anything upstream.** Not this issue's end point, and no `gh pr
  create` against another repository's slug from here under any circumstances.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above, and over the test named.
`MANUAL_FAN_CTRL` stays `present-untested` and `confirmed-inert` stays §7's call
by a human. No live run, no register readback, no hardware observation; no line
of this change may be read as a report of a capture, and none is one.