# A day whose three consoles marked one action 7 s apart was reported as two captures that never recorded it (issue #1372)

The write-up for [issue
#1372](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1372), which
[issue #676](0751-mark-gap-report.md) opened and left half-closed: that one
measured the gap a join was *made* on and stopped at the boundary. This one is
the other side of it — the marks that did **not** join, and the window length
§4.4's control-vs-write comparison has no time base without.

Both are **reports, not refusals**, in the sense #676 fixed and the issue
drew again: the run is still refused for a day that mis-shapes into nine
windows and three blocks, the same windows are still withheld, the exit code
is still 1, and no `window delta` figure moves. What changed is the sentence
the report gives for *why*, and the fact that a window now says how long it is.

`MANUAL_FAN_CTRL` stays `present-untested` and
`ec/annotations/registers.yaml` does not move. Nothing in this file is a claim
about the machine; the §6 day has still not been run, and issue #380's.

## The defect

`coalesce_marks` (`ec/tools/grade_0751_isolation.py`) fuses marks that land
within `MARK_MERGE_SECONDS` of each other and opens a window per group. Three
consoles marking one action **7 s** apart is over that window, so it is three
groups, so each console's mark opens its own window — and the two that follow
are windows a capture is absent from.

`window_mark_problems`'s `missing` check then said:

> recorded in 1 of 3 capture(s), absent from console-1.csv, console-2.csv. The
> capture(s) that missed it have their rows for this arm filed under whichever
> window their timestamps fall in, and nothing in the result ties them to the
> arm whose mark is gone -- so this arm can read quiet for want of a mark
> rather than because nothing moved.

**Every capture recorded every mark.** The sentence sends the operator looking
for a watcher that exited early, which is a different fault with a different
fix, and `0751-early-exit-row.md` and the `=== N sweeps over Ms` line would
also have had to be ruled out before anyone suspected the timing. The distance
that settles it was in the capture the whole time and in no line of the report:
`mark_gaps` holds the gap that *made* a join, and a group with one mark has
none, so `grep -c 'adjacent gap'` on the report is **0**.

## What the report says now

Two changes, and they are separate.

### 1. `boundary_gaps`: the marks of the same action that fell outside the merge

`coalesce_marks` records, per window, the marks of the **same `(role, value)`**
that did not join, as `boundary_gaps` — `(mark, seconds)` measured from the
window's own mark. It rides beside `marks` for the reason `mark_gaps` does: a
distance is a property of two captures' rows together, not of either.

Three decisions in it, each with a case behind it:

- **The run of same-action groups either side, walked outwards until one is a
  different action.** Not the two adjacent groups. Three consoles 7 s apart put
  the first window 14 s from the third, so a neighbour-only rule would name
  console 2 and leave console 3 reading as a capture that never recorded the
  action — half the fix, and the half that is on screen.
- **One mark per capture, the nearer side.** The question is per console:
  `window_mark_problems` has to say that *this* capture recorded the action
  7.0 s out, and one mark for a side cannot answer that for the second and
  third console.
- **Nothing for a different action, and nothing for a label that does not
  parse.** A `restore` thirty seconds later is the next arm, not a console
  that was slow with this one; recording it would put a distance on every
  window of every run. A day whose three consoles fused has no mark of the
  same action outside the merge anywhere, so the ordinary window records
  none at all.

`split_mark_gaps(w, names, by_source)` is the condition that chooses between
the two arms of `missing`: it returns a distance for an absent capture only
when **every** capture the window is short a mark for recorded that same
action within `MARK_SPLIT_SECONDS`. One capture that recorded the action and
one that never did are two different days' worth of trouble, and a sentence
naming the second would be false about the first. When it holds, the census
lists the absent capture with its distance rather than `-- did not record it`,
and the window's problem reads:

> recorded in 1 of 3 capture(s), absent from console-1.csv, console-2.csv --
> and every one of them recorded this same action just outside the 5s merge
> (console-1.csv at 7.0s after, console-2.csv at 14.0s after). That is the
> consoles marking one action further apart than the merge fuses, not captures
> losing it: the split opened a window per console and each later one reads as
> a capture that missed the mark. Redo the block, marking each console within
> 15s of the others.

`MARK_SPLIT_SECONDS` is a **distance**, so it bounds the magnitude of the gap
and not its sign. `boundary_marks` records `m.ts - w.ts`, negative for a mark a
window looks *back* to, and a signed compare against the threshold let a
console that marked 20 s early past a 15 s bound — `-20.0 > 15.0` is false. The
report then told the operator to mark within 15 s of the others while naming,
in the same sentence, the console that was 20 s out. The comparison is `abs()`
and the sentence prints the magnitude with a `before`/`after` word, the way the
census's own line under a capture has always formatted it; `straddled` and its
one test cover the sign on both sides.

Otherwise today's sentence stands, **verbatim**. The `in N of M capture(s)`
head is a fact about the group either way and is not touched.

The census is the site that matters most under `--block`: it prints
whole-capture while only the selected block's windows print, so a split in a
block this run did not grade is visible there and nowhere else. That is the
same argument `0751-mark-gap-report.md` made for putting the gap note on the
per-action line, and it is why the distance is not in `report_blocks`,
`report_early_exits`, `report_dumps` or the closing section — those aggregate
over windows and would restate it under a heading that does not own it.

### 2. The window's span

§4.4's comparison is the duty byte's `total` under the control arm against its
`total` under the write, and neither figure carries a time base: a byte that
drifts for 30 s and one that drifts for 3 s have totals that are not two
answers to the same question. `build_windows` now records each window's
`span`, and `report_window` and `report_withheld_window` both print it, on a
line of its own.

**The last window's span is a lower bound, and says so on its face.** It has
no next mark, so it is measured to the last change row it holds — and
`ec_watch.py` writes a row when a byte changes, so a quiet tail after that row
is in no row of the file and the window's real end is not in the capture:

```
    window span 30.0s
    window span at least 5.0s, to the last row in the capture
```

— the two figures the committed `0751-isolation-run/` fixture produces. That
fixture is the **hand-built three-console input** `ec/tools/testdata/README.md`
describes, not a capture: every byte and timestamp in it was written by hand to
exercise the tool's branches, and each of its three CSVs says so on line 1.
The figures are arithmetic over it and are reproducible offline; they are not
a reading of a machine. That is why `span_is_bound` exists,
and why `span_note` draws no conclusion from a bound that is *under* the band:
a lower bound of 0.0 s says the window was at least nothing, which is not
evidence that it was short. A bound *over* the lid still fires — that much
length is established however much longer the window was.

The span is kept visibly separate from the existing `window runs to ...` line.
Under `--block` that line is where this **read** stops, which is the end of the
block rather than the end of the window; a reader who took it for the span
would be reading a scoping fact as a measurement.

## The two numbers, and what they are

Both are **transcribed from §3 and are judgements, not measurements.** No run
of the day has been timed; the write-up that would give them a measurement is
#380's, and it has not happened.

- **`MARK_SPLIT_SECONDS = 15.0`.** §3 says to mark each console "within a few
  seconds of each other" and paces the arms ~30 s apart, so 15 s is half the
  shortest stretch the procedure leaves between two of its own marks — past
  which a mark is more plausibly the next arm than a slow press on this one.
  It **cannot** be `MARK_MERGE_SECONDS`: a mark inside the merge window was
  joined by construction, so there is no mark of the same action inside it and
  a threshold equal to it could never fire. That is a stronger argument than
  the one `CLOSE_GAP_SECONDS`'s own comment gives for the same mistake, and the
  constant's comment says so.
  `test_the_band_is_two_transcribed_numbers_not_a_measurement` pins the
  relation, and both sides of the threshold are pinned on the hand-built
  fixtures: the 7 s day fires, the committed 1 s day does not.
- **`SPAN_FLOOR_SECONDS = 10.0`, `SPAN_CEILING_SECONDS = 240.0`.** The floor is
  §3's own "~10 s settle", the shortest stretch the procedure budgets for
  anything. The lid is §3's `--seconds 240`, the whole of what one set of
  three watchers runs for — so a real day cannot reach it, and what does is a
  capture that was cut short, edited, or written by something other than that
  watcher. It is not placed lower to make it reachable: a threshold below what
  the watcher can produce is a check that cannot fail, which is the same defect
  in a different place.

The note says what the cost is — §4.4's two arms are then over windows of
unequal and unknown length, so a difference in `total` is not attributable to
the write alone — and it **reports rather than refuses**, on the line #676
drew.

## The 9-windows-3-blocks mis-shape

A day that marks this way produces

```
  block 1 of 3: value under test 0xA0, roles control, control, control, write -- NOT GRADED, ...
  block 2 of 3: value under test 0xA0, roles write -- NOT GRADED, ...
  block 3 of 3: value under test 0xA0, roles write, restore -- NOT GRADED, ...
```

plus two `unplaced` restores, all three blocks carrying the same `0xA0`.
**The refusal is correct and this change does not repair it**: a day whose
three consoles marked one action 7 s apart has not produced §6's ten files, and
the report should say so. Only the reason it gave was wrong. It is recorded
here as a description of the shape, not as a defect this fixes.

## The procedure, in two sentences

Both edits are **below line 163** of
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`, because
`ec/tools/measure_mark_provenance.py` pins `:159`, `:161` and `:163` into §3's
command block and an insert above them silently mis-aims those pins.

1. "the grader treats marks less than five seconds apart as one action" →
   **five seconds apart or less**. `coalesce_marks` closes at `<= 5`, and
   `windows/tools/manual_fan_ctrl_probe.py`'s `marks_clear` already reasons
   about the equality edge in its own docstring. The procedure should match
   the code it describes.
2. **A suspend during the day costs the run**, in the paragraph that explains
   `--seconds 240` and "a mark after the watcher has exited is written
   nowhere". Modelled on the sentence
   `docs/hardware-tests/system-id-0456-bit6-divisor.md` already gives its
   operator. Its evidence is
   `evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv`: a **12.3 s
   hole** for the freeze, S3 and the thaw of a `systemctl suspend` to
   `mem_sleep=deep`, in a capture that is otherwise complete
   (`evidence/README.md`). That is a statement about the contents of a
   committed file, not a live run, and §3's ~30 s hold is what a 12.3 s hole
   lands in the middle of. The sentence is careful about what the span can do
   with it, and the arithmetic names its clock because the capture's own
   header warns about a different one: that header says the capture's clock is
   `CLOCK_MONOTONIC` and stops in suspend, which is true of the `--seconds`
   deadline (`ec_timer_capture.py:334`) and of the "~7.2 s suspended" it
   derives from `CLOCK_BOOTTIME` minus `CLOCK_MONOTONIC` (`:201`) — but the
   **row stamps are wall clock**, `datetime.datetime.now()` (`:79`), as they
   are on the Windows watcher §3 actually runs (`ec_watch.py:122`). The span
   is arithmetic over those stamps, so a 12.3 s hole between them makes a
   30 s arm about 42 s long, which is **inside** the band: the note does not
   fire and the tool cannot say a suspend happened. What the span buys is that
   the number is on the page. Whether a suspend long enough to run past the
   watchers' own `--seconds 240` is reachable at all is not something §6's day
   has established — the mechanism is there on the Windows watcher, whose
   `--seconds` check is `time.time()` (`ec_watch.py:651`), but no committed
   run has been suspended long enough to show it, and the ceiling is not
   placed on the strength of a prediction. The row-gap detector below is what
   would name the rest.

## The tests

A new `MarkSplitBoundaryTests` in
`ec/tools/test_grade_0751_isolation.py`, **appended at the end of the file**,
after `ReadbackNoticeTests` and before the `__main__` guard. End-of-file is
load-bearing rather than stylistic: 21 pins across five write-ups, and the
per-pin table in `docs/findings/test-line-pin-census.md` on top of them, cite
into this file below `GradeTests`, and the placement note above
`ReadbackNoticeTests` (which cites the same census) already argues that
inserting anywhere else moves all of them onto the wrong line without changing
a word of the citing sentences. The new class's own comment repeats the
argument for the next branch.

Three temp-dir builders, all in the class: `staggered(step)` copies the
committed `0751-isolation-run/` bytes and moves only the mark timestamps, so
`step=1.0` is that fixture's own spacing and `step=7.0` is the same day marked
too slowly to fuse; `paced(spacing)` holds the three consoles at the same
instants and varies only the gap between actions, so the window length is the
sole variable the span band is tested over; `straddled(offsets)` moves the
*first* action's three marks to explicit per-console offsets and leaves the
rest of the day alone, which is the only one of the three that reaches a
**before-side** distance. `boundary_marks` records `m.ts - w.ts`, negative for a
mark a window looks back to, and `staggered` only ever makes forward gaps
because the captures' marks stay in the same order — so the sign of the
threshold comparison was untested until this builder existed.

No test asserts a count of the tree or of the suite — each asserts the claim
its fixture is about, for the reason CLAUDE.md gives and
`test_check_pin_table_by_cited_file.py` was bitten by four times.

The mutation pins, each verified to redden on its own:

| Mutation | What reddens |
| --- | --- |
| `boundary_gaps` left empty | the 7 s day names no distance, and `-- did not record it` comes back |
| split arm printed whenever *a* capture is absent | `missing-mark/`'s existing sentence, and six tests that already pinned it |
| `SPAN_FLOOR_SECONDS = 0` | the short-window note, the bound test, the band test |
| `SPAN_CEILING_SECONDS` above any capture | the long-window note, the band test |
| `MARK_SPLIT_SECONDS = MARK_MERGE_SECONDS` | the 7 s day, the band test |
| no span line on a withheld window | the graded-and-withheld test |
| the split arm's threshold compared signed, as first written | the before-side test: a 20 s gap passes a 15 s bound on `-20.0 > 15.0` |

`MarkGapReportTests.test_block_selection_is_unchanged` is the structural guard
that the two new `Window` attributes cannot take part in `--block` selection —
`main` filters with `shown = [...]` after `build_windows` — and it stays green.

## A note on the plan's own test bullets

The plan for this issue asked for the split day and the 1 s day to have
"identical exit code, identical withheld window count, identical closing
section". **They do not, and cannot: the split day is a refusal and the 1 s
day is not** — that is the entire difference the issue is about, and a day
that grades cannot be a day the change refuses. What the two *do* share is
pinned where each claim is actually true: the 7 s day is pinned for what it
changed and did not (same nine windows, same block verdicts, same withheld
set, same closing section, same exit code as the mark-set rules alone produce),
and the 1 s day for what it must not reach (no split wording, no boundary
distance, no span note, unchanged verdict section and mark headers). One pin
each, on the fixture where it is a fact.

The plan also read `boundary_gaps` as "at most one mark per side". That does
not work for three consoles: the first window is 14 s from the third, and one
mark per side would answer for console 2 alone. It is recorded **per capture,
the nearer side**, which is what the census needs to name each console's own
distance and is what the issue's done-looks-like bullet requires.

## Left out on purpose

- **A committed `testdata/` fixture and its `README.md` row.** A row in a
  hand-written shared file is a merge-conflict magnet and needs
  `check_testdata_index.py` registration. The temp-dir builders are what
  `MarkGapReportTests` uses and what the issue offers as the alternative.
- **A row-gap / hole detector in the grader.** The 12.3 s hole is the evidence
  for the procedure sentence and the motivation for the span, not a third
  check. **Worth filing as a follow-up**: a per-window maximum gap between
  consecutive rows would name a suspend directly rather than through an
  inflated span, and it is the only thing that would catch the common case —
  a freeze short enough to leave the window inside the band, where the span
  note is silent and the arm is quietly longer than §3's ~30 s.
- **`MARK_MERGE_SECONDS`.** Stays 5. A different fuse window is a decision
  about the grader's own procedure, `0751-mark-gap-report.md` already declined
  it, and `windows/tools/test_manual_fan_ctrl_probe.py` pins the probe's copy
  against this one.
- **The 9-windows-3-blocks mis-shape.** See above: the refusal is correct.
- **Running the §6 day on the machine.** Issue #380's, and a human's step.
- **Landing `docs/ci/agent-gates-0751-self-test.patch`, or any edit under
  `.github/workflows/` or `.github/actions/`.** The pipeline's token has no
  `workflow` scope. The suite is still run by `tools/run-tests.sh` and by the
  tool's own `--self-test`.
- **Submitting anything upstream.** No `gh pr create` or `gh issue create`
  against another repository's slug, for this or any issue.
- **`docs/findings.md`.** Frozen; `check_findings_frozen.py` fails the add,
  and `docs/findings/INDEX.md` is regenerated by
  `ec/tools/gen_findings_index.py` rather than edited.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-built CSVs, reproducible offline from the
committed `0751-isolation-run/` bytes and the two builders named above.
**No line of this change may be read as a report of a capture or a live
observation, and none is one.** The 12.3 s figure is a statement about the
contents of a committed file under `evidence/`. The two constants are
transcriptions of §3's own numbers and are named as judgements, not
measurements. §6's day has still not been run on the machine.
