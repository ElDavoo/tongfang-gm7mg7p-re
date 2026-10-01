# The refusal on a stray in no block was scoped by accident, and "census-only is enough" said nothing about what the run did with the window (issue #539)

The write-up for [issue
#539](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/539), which asked
for a fork in
[`grade_0751_isolation.py`](../../ec/tools/grade_0751_isolation.py) to be taken
and the one taken to be pinned. It is a disclosure change plus a held decision:
**no window is graded or withheld differently, no exit code moves on any
committed fixture, and the change is one clause on one census line and one
test.** Nothing here is a register behaviour and nothing here is evidence about
the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value.

It settles an alternative that
[`0751-grader-unplaced-window-checks.md`](0751-grader-unplaced-window-checks.md)
(#529) named and left standing, and it is the fourth change in this family
after
[`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md)
(#530),
[`0751-grader-block-scoping.md`](0751-grader-block-scoping.md) (#498, landed as
#502) and
[`0751-grader-moved-unplaced-scope.md`](0751-grader-moved-unplaced-scope.md)
(#725). #529 is where the refusal itself came from and is cited rather than
restated here.

---

## The fork

#529 refused a window in no block when the captures disagree about the action
it opened — spelled two ways (`labels`), or absent from one console
(`missing`) — and counted the refusal into `withheld`. The exit expression is
`1 if (void or unreads or withheld) else 0`, and it was not touched.

That makes the scope a property of where `withheld` is accumulated, which is
over `shown`. Under `--block`, `shown` is the selected block's own windows:

```python
        shown = [i for i, w in enumerate(windows) if w.block is selected]
```

A window `assign_blocks` could not place has `w.block is None`, so it is in
`shown` on an unscoped run and in none of them under `--block`. So:

| run | exit | what the window section says |
|---|---|---|
| unscoped | 1 | both strays `block: unplaced -- NOT GRADED` |
| `--block 0xA0` | 0 | neither stray printed, not printed nor withheld; block 1 `intact` |
| `--block 0x10` | 0 | as above, block 2 `intact` |

That is #529's table, and it was correct when measured. What it did not do was
say that a `--block 0xA0` attachment would keep saying it, and the sentence
#529 left for the other reading — *"hoist `unagreed` out of the `shown` loop
into a run-wide count and add it to the return at the end, the way `unreads` is
handled"* — described a change that moves all three of §6's per-value
attachments from 0 to 1 with **nothing in the tree failing**. `UNPLACED_FAILURES`
was reached in exactly two places in
`ec/tools/test_grade_0751_isolation.py` — `test_a_window_in_no_block_fails_the_
same_agreement_checks` unscoped, and `test_the_unplaced_window_problems_name_
their_kind_per_window` as a direct call to `unplaced_window_problems`; neither
passed `--block`, while the two run-wide refusals beside it were both pinned
over it. A decision recorded as an alternative and owned by nobody is a
decision the next change takes by accident.

## What was chosen, and why it is not a coin turn

**Window-scoped**, like a block's own problems. The argument is #529's and it
holds:

`unreads` is run-wide because an unreadable label could *be* a `write` — so it
can change which blocks there are at all — or *be* a `restore` typed inside a
block, which would close that block early and leave it void rather than
intact. Either way the capture is then holding a block the run cannot name, and
every block's completeness rests on it. `unplaceable_marks`' docstring says
this, and the comment in front of the exit expression says it again in those
terms.

The disagreement on a stray is a property of a window that is **already in no
block**. It cannot re-shape the block structure: it is not a block's last
recorded mark in any capture, so it cannot make a block `void`, and it is not
a label, so it cannot re-attribute one. It is also a property of *what the two
checks are defined over* — `window_mark_problems` reads which captures recorded
the action and whether they spelled it alike, and neither question names a
block — rather than a case that was looked for and not found. That is the
distinction the calibration rule turns on, and it is the reason this is a
decision rather than an observation.

The direction it errs in is the conservative one for the operator's question.
A `--block 0xA0` fold-in attachment answers "what did value `0xA0` do", and a
window in no block is not a window of any value under test — the census says so
on the line itself. Exit 1 over it would be a claim about the day, from an
attachment whose own closing section says it is not about the day.

## What "census-only is enough" cost, and the one clause that closes it

`report_census` prints whole under `--block` — its own documented choice, and
the reason a reader can see the scoping rather than infer it. It already names
both strays, with the diagnosis: the per-capture label list under `action 1`
and the absent console under `action 5`. **So the finding survives. What it did
not say is what this run did with those windows** — refused them, or graded
them.

Measured on the fixture, before this change:

```
$ python3 ec/tools/grade_0751_isolation.py \
    ec/tools/testdata/0751-isolation-run-unplaced-window-failures/*.csv --block 0xA0
$ echo $?
0
```

no `NOT GRADED` in the window section, no `were not graded` in the closing one,
`block 1/2: intact`, three windows in the usual format — over a census whose
`unplaced:` lines and per-capture diagnosis are identical across the two
attachments, the block line aside: there the census appends `-- not selected in
this run` to the block this attachment did not take, which is the scoping said
out loud rather than hidden. A reader holding the two attachments side
by side, which is what §6 asks them to do, sees `block: unplaced -- NOT GRADED`
in one and nothing in the other. That is the accident the issue is pointing
at, and it is why "census-only" needed a word in it rather than the whole
argument being won.

So the `unplaced:` line gains a clause naming the agreement problems on that
window, in the vocabulary a block's verdict line already uses:

> `… -- and \`--block\` cannot select it either`
>
> becomes
>
> `… -- and \`--block\` cannot select it either -- NOT GRADED, 1 problem(s): labels`

One function, one argument, one clause. `report_census` takes the `unagreed`
dict alongside `unreads`, and `main` passes it at the call site; the kinds come
from `window_mark_problems` — the function `unplaced_window_problems` itself
calls, over a capture set keyed the way that function compares — so a window
cannot be named here under a kind the refusal did not carry. The keying is the
whole of it, and it is not free: a `known` built from the paths *as handed in*
rather than from `capture_key` is a set that is false against the keys for any
spelling that is not already the resolved one, and it fires a `missing` no
capture earned — beside a count computed with the right keys, so the line names
two kinds and a count of one. `test_a_disagreeing_stray_is_refused_by_the_whole_capture_run_and_not_by_a_block_run`
holds the clause against both spellings for that reason.

**It says `NOT GRADED`, not "the mark was wrong."** The clause is what the run
did, not a verdict about the bytes. `unreads`' reason is fatal because a mark
no block can be attributed to leaves every block uncertifiable; this one's is
fatal because the captures do not agree about which action the window opened.
Different reasons, different remedies, and the census is naming the first half
of this because the window section cannot.

**It prints identically scoped and unscoped**, because the clause is a property
of the marks and not of the run's scoping. That is the whole point, and it is
why `unagreed` is computed once in `main` and handed in rather than
re-derived in the census where the two could drift.

### A window the parse could not read never reaches it

`unplaceable_marks` keys on `parse_mark(w.label)[0] is None`, and the census's
`unplaced:` loop is already guarded by `role is not None`. The two predicates
are complementary over `unplaced`, so no window in `unreads` ever gets the
clause — **not** because the branch order in `main`'s `shown` loop happens to
put `unreads` first, though it does, and not because a case was found and
checked: the guard cannot be reached by a window in `unreads`. No committed
fixture has a window in both sets, and that is a fact about the fixtures rather
than the mechanism.

This is worth saying because it *looks* like a collision.
`test_an_unreadable_mark_refuses_a_block_run_and_says_why` holds a
whole-output `assertNotIn('NOT GRADED', out)` over `unread-window/`, and this
change puts the string `NOT GRADED` into the census. That test stays green
unedited, and for the reason above rather than by luck: `unread-window/`'s only
refused stray is an unreadable label, so it has no `unplaced:` line to carry a
clause, and the refusal it pins is announced by `UNREAD_MARK_NOTE` instead.

## What the run-wide reading would have cost

It is not one term in isolation, and the predecessor's "one term in the exit
expression" left a reader with that impression.

1. **A fourth clause** in `1 if (void or unreads or withheld) else 0`, fed by
   `unagreed` hoisted out of the `shown` loop — the shape `unreads` has.
2. **A run-wide note** in the closing section where the exit code is read from.
   It would have to tell this refusal apart from `UNREAD_MARK_NOTE`'s, because
   the two are fatal for different reasons and send the operator to different
   places: one to fix a mistyped label, the other to go back to the terminals
   and retype a mark whose action the consoles did not agree on. A single note
   covering both would send a reader after the wrong repair, and the two have
   different `--block` semantics that the note's own scoping clause would then
   have to state separately.
3. **The census clause's scope reworded.** It is written as a property of the
   marks. Under a run-wide refusal it becomes a property of the run, and a
   scoped attachment would carry a verdict the run had made about the day —
   which is the thing the window section's own sentence declines to do.

And the three §6 attachments would move 0 → 1 together, so a single day's
captures would produce three failing exits and one unscoped exit, and the
operator could no longer tell from an attachment which value to re-run.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`,
`test_a_disagreeing_stray_is_refused_by_the_whole_capture_run_and_not_by_a_block_run`
— one method, in `MarkSetTests` beside the three #529 tests. It has three
halves, and none of them is left to chance.

**One subtest per `--block` value** over `UNPLACED_FAILURES`, so a failure
names which value flipped: rc 0; `NOT GRADED` and `were not graded` absent
from *everything after the census* (cut with `after_census`, because the census
carries the string by design and a whole-output absence would be an absence
asserted against the thing this change adds); the
`=== block N of 2, value under test V, 3 window(s) in it ===` header with that
block's own three windows at their numbers in the whole mark stream; `block
N/2: intact`; and the per-block movement sentence in the closing section rather
than the whole-capture one.

**The diagnosis survives**, and is held as a property rather than as two
strings that happen to be in the output: two `` `--block` cannot select it ``
lines, two `the void check cannot` lines, `action 1`'s per-capture list
carrying `'restored 0x0751=0x0a'` against `'restored 0x0751=0x99'`,
`action 5`'s `2026-01-01-0751-isolation-0f00-0f5f.csv` with
`-- did not record it`, the two clauses `labels` and `missing` each read off
the line of the window it is about, and the two `unplaced:` lines
**byte-identical** to the unscoped run's two lines of the same fixture. That
last one is the load-bearing assertion; the block lines around them
legitimately differ, so the comparison is cut to the `unplaced:` lines by a
helper, `unplaced_census_lines`.

**The unscoped half**, asserted rc 1 with two `block: unplaced -- NOT GRADED`
and `2 of the 8 window(s) above were not graded`. The whole difference between
the two halves is `--block`.

**The clean half**: `UNPLACED_WINDOW` under both `--block` values, rc 0 and no
`NOT GRADED` anywhere. A check that had quietly started refusing everything
looks exactly like a check that is working, and the existing unscoped clean
assertions do not cover this — they stand on rc 0 plus a census count, which a
run-wide refusal would have kept green. The two pre-existing clean cases stay
**unedited** and green, which is the over-refusal guard from the other side.

All three mutations were run against this branch's tool and each is red on its
own: hoisting `unagreed` into the exit expression turns it red on `rc` alone
(`1 != 0`, both subtests); deleting the clause turns it red on the clause
(`['', ''] != ['NOT GRADED, 1 problem(s): labels', ...]`); a clause that fires
on agreeing marks turns it red on the clean half, at
`block='0xA0', clean=True`.

## What must not change, measured rather than asserted

`git show origin/main:ec/tools/grade_0751_isolation.py` and this one were run
over **every** `ec/tools/testdata/0751-isolation-run*/` directory four ways —
unscoped, and `--block` at `0xA0`, `0x10` and `0x00` — and every pair diffed,
exit code and text:

    for d in ec/tools/testdata/0751-isolation-run*/; do
        for a in "" "--block 0xA0" "--block 0x10" "--block 0x00"; do
            python3 ec/tools/grade_0751_isolation.py $d*.csv $a; echo "$d $a $?"
        done
    done

**No exit code moves on any of them.** The only text that differs anywhere is
the new clause, and only on the runs of the one fixture whose strays parse and
disagree — the `unplaced:` line there and nowhere else. This is stated as a
claim and not as a count of directories on purpose: a directory census is a
number every landing fixture has to edit, which is the trap `CLAUDE.md` names
by name. Re-run the loop to check it against whatever the tree holds then.

**`bash tools/run-tests.sh` passes on this tree, and passed on this branch
before the change.** `test_census_test_line_pins.py` and
`test_check_pin_table_rows.py` were red for part of the way here — the two that
say whether the citations this change moved were left wrong — and are green
again now that the re-anchoring below is done. Which suites are green is a
property of a tree rather than a claim this page can carry into the next merge,
so re-run it against whatever the tree holds then rather than reading the state
off here.

## The citations this move, and how they were repaired

The grader suite is cited by line from four write-ups, and the lines added above
them move every target below the insertion. **Leaving them would have made each
of those citations name a line it is not cited for**, so they were re-anchored —
the repair
[`docs/findings/test-line-pin-census.md`](test-line-pin-census.md) records, and
the one its `#485` paragraph records for the same reason.

Each re-anchored target was read against the line its citation held before,
which is what a re-anchoring has to be rather than a guess: both ends of
`:1118-1163` are `:1143-1188`'s, the same
`def test_a_capture_given_twice_is_refused(self):` and the same
`self.assertIn('3 capture(s)', out)`. So each row's verdict is the one its old
line carried, and **no shape moves either**, which is why
`test_census_test_line_pins.py`'s landing-shape split is unmoved — the reason
it was the right repair rather than re-deriving the split is that re-deriving
would have frozen stale citations as though they were intended, and the split's
whole purpose is to tell a re-anchoring from an addition.

Two records are the exception, and both are corrections rather than
re-anchorings. `0751-mark-provenance-column.md`:206 named the class header and
had been moved off it; it is put back on the header. `0751-capture-row-shape.md`:41
is not re-anchored at all, its pin being qualified by a commit, and the values
it carried in between are left visible in its census row rather than
deleted. The rows carry their own cause, and
[`test-line-pin-census.md`](test-line-pin-census.md)'s note under the table
carries the rest.

## The suite's own addition

One named method in `MarkSetTests`,
`test_a_disagreeing_stray_is_refused_by_the_whole_capture_run_and_not_by_a_block_run`,
is the only thing this change adds to
`ec/tools/test_grade_0751_isolation.py` — the path-spelling half named above
is asserted inside that same method, not as a second one. The count the suite
holds is `bash tools/run-tests.sh`'s output, not a figure restated here: a test
count in this file is a value the next merge invalidates without touching this
page, and the chain in
[`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):229-282
is where a figure about this suite is argued from.

**The pre-existing tests stay green, and the only lines this change edits among
them are the three `report_census(...)` calls that pass positional arguments**
— in `test_the_readers_count_a_capture_given_twice_as_one_capture`,
`test_the_census_counts_two_spellings_of_one_file_as_one_capture` and
`test_the_census_names_a_capture_the_way_the_capture_read_itself`, each of
which needs the new argument the section now takes. That is the checkable form
of the claim: `git diff -U0 origin/main...HEAD -- ec/tools/test_grade_0751_isolation.py`
returns those removals and nothing else, so nothing else moved.

## Left out on purpose

- **The run-wide refusal.** Named and argued against above, with what it would
  cost. Decided, not deferred.
- **The `rem` block in §6 of the procedure doc**
  (`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:879-884`), which
  describes the refusal in whole-capture terms and is incomplete for the same
  reason its predecessor left it. §3's text at `:244-252` already states the
  contract this change makes the tool meet — *per capture*, so a block that
  fails has its windows left out and the exit code is 1 — so nothing there is
  falsified. A long shared file with agent PRs open against it, and the
  predecessor already recorded it as a follow-up.
- **#506** (the missing day-level `--block`-less command line in §6) and **#515**
  (`--dump-pair` scoping gated on a run-wide total). The same family, named
  adjacent by the issue; neither is answered here and neither is closed.
- **`.github/workflows/` and `.github/actions/`.** The pipeline's push token has
  no `workflow` scope, so a branch touching them fails at the very end. The
  `--self-test` gate patch at `docs/ci/agent-gates-0751-self-test.patch` stays
  prepared and unlanded; landing it is a human's change.
- **Running §6 on the machine.** No laptop and no Windows host is reachable
  from a GitHub-hosted runner. What §3's six mark rounds would do on real
  consoles is what this change makes the grader able to notice; the next §6/§7
  day is a human's run.
- **`ec/annotations/registers.yaml`.** No register status is in question;
  `MANUAL_FAN_CTRL` stays `present-untested` with its `static_refs*` counts at
  29/29/0. A refusal is not a verdict, and this one is not even a verdict —
  which is the sentence the census clause says in `NOT GRADED` rather than in
  prose.
- **`ec/README.md`, `ec/tools/testdata/README.md`, `tools/README.md`.**
  `ec/README.md:547-564` describes `--block` scoping at a level this change
  does not alter; no new fixture means the testdata index needs no row; and the
  suite table's row for `test_grade_0751_isolation.py` carries no count, so
  adding a test does not make it stale. Leaving all three alone is also three
  fewer shared files open against the other agent PRs.
- **Anything in the four write-ups whose citations moved, beyond the pin
  numbers themselves.** The re-anchoring is a line-number repair; it re-reads
  no claim and rewords no sentence, and a broader edit of a merge surface
  would be this branch asserting things about pages that are not its own.
- **Any suite failure the tree happens to be carrying.** The run is green here,
  and a suite that goes red is another issue's work that this branch has no
  standing on — not something to fold into this diff.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above, against the revision each
transcript names, and the test named. No live run, no register readback, no
hardware observation; no line of this change may be read as a report of a
capture, and none is one.
