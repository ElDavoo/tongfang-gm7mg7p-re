# Two captures whose three consoles marked 0.2 s apart and 4.9 s apart graded identically, and said nothing about it (issue #676)

The write-up for [issue
#676](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/676). It is the
reader-side half of what [issue
#665](probe-hold-mark-merge.md) fixed on the writer side, and it is **a report,
not a refusal**: §3's three consoles are supposed to fuse, so the exit code,
the verdicts, which windows are graded or withheld, and what `--block`
selects are all unchanged by this. An intact block still exits 0. What
changed is that a window built from more than one raw mark now says how far
apart those marks landed, so a reader can tell a 0.2 s three-console join
from a 4.9 s one without re-deriving either from the CSVs.

Nothing here is a register behaviour and nothing here is evidence about the
machine. `MANUAL_FAN_CTRL` stays `present-untested` and
`ec/annotations/registers.yaml` does not move.

## The defect

`coalesce_marks` (`ec/tools/grade_0751_isolation.py`) is the only place that
knows which raw `MARK` rows were recorded as one action, and the decision it
makes *is* the gap: each mark is compared to the last mark in the open group
and the group closes at `<= MARK_MERGE_SECONDS`. The gap that decided it was
then dropped. `Window` carried `.ts`, `.label`, `.source` and the raw
`.marks`, and nothing that recorded how close the group came to splitting.

So two captures differing only in that — three consoles marking one action
0.2 s apart, and three marking it 4.9 s apart — produced byte-identical
verdicts and said nothing that told them apart. The second is the one worth
worrying about: 4.9 s is 0.1 s short of splitting, so that group only just
stayed one window, and the report did not say so.

The in-repo precedent for the missing half is `grade_gpu_door.py`. It does
**not** fuse — its `CLOSE_MARKS_SECONDS` is a warning threshold, not a merge
— and `report_close_marks` walks adjacent windows, computes the gap, and when
it is inside the threshold prints how far apart the two marks were together
with `They stay two windows`, and then says that *this* grader fuses marks
that close and why the two procedures differ. The door grader makes a claim
about the 0751 grader's window and backs it by measuring; the 0751 grader
fused and said nothing. This change is the 0751 grader measuring.

## What the report says now, and where

`coalesce_marks` records the gap it decided each join on, one entry per
adjacent pair, on the window as `mark_gaps` — `(earlier mark, later mark,
seconds)`. It rides **beside** `.marks` rather than inside it, because a gap
is a property of the join — of two consoles' rows together — and not of any
one console's row. `.marks` stays exactly the per-capture record that
`check_block_marks`, `window_mark_problems` and `existing_mark_findings`
read; nothing about it changed.

`mark_gap_note(w)` is the one implementation. It returns `[]` for a group of
one mark (there is no join to describe, and a line saying there was none
would be noise on the ordinary window), one headline line for a fused group
naming the raw row count, every adjacent gap, and the window it was measured
against, and a second note when the widest gap is close.

Three call sites print it, so a graded window, a withheld window and the
census all read the same:

- `report_window`, under the `block:` line.
- `report_withheld_window`, under the same line. Withholding a window's
  verdict is not a reason to withhold a fact about the capture with it.
- `report_census`'s **per-action** line. This is the one that matters most for
  a `--block` run: the census prints whole-capture while only the selected
  block's windows print, so a fused group in a block this run did not grade is
  visible there and nowhere else.

Deliberately not printed:

- **In the per-capture census rows.** Each of those is one console's marks.
  A distance between two consoles printed under one of them would misattribute
  it.
- **In `report_blocks`, `report_early_exits`, `report_dumps` or the closing
  section.** Those aggregate over windows and would restate the same gap
  under a heading that does not own it.

## The form, and why 4.0 s

Over a three-console fixture whose first action's marks land 1.0 s and 4.9 s
apart, the census now prints:

```
  action 1 at 2026-01-01 12:00:00+01:00  block 0xA0: 'no-op wrote 0x0751=0x10' in 3 of 3 capture(s), one label each
    joined 3 mark row(s), adjacent gap(s) 1.0s, 4.9s, window 5s
    the widest of those, 4.9s, is at or above the 4.0s this report calls
    close: the group stayed together by under a second of the 5s window,
    so a reader who expected two actions has the distance here to judge
    the join rather than take it on trust
```

and the same day's other two actions, staggered a second apart:

```
  action 2 at 2026-01-01 12:00:30+01:00  block 0xA0: 'wrote 0x0751=0xA0' in 3 of 3 capture(s), one label each
    joined 3 mark row(s), adjacent gap(s) 1.0s, 1.0s, window 5s
```

`CLOSE_GAP_SECONDS` is 4.0, and it is a **floor rather than a ceiling**, which
is the whole design of it and the part most likely to be misread as a bug. The
note fires when a group came *close to splitting*, not when it fused
confidently. That reading is placed by a committed fixture:
`ec/tools/testdata/0751-isolation-run/*.csv` has its three consoles marking
one action at `12:00:10`, `12:00:11` and `12:00:12`, so being three consoles
costs about 1 s per adjacent pair. A group that fused for that reason alone
has a widest gap near 1 s and is not what a reader needs warning about. 4.0 s
is a hesitation rather than a press and sits 1 s short of the edge at which
the group would have been two windows.

Two numbers were rejected, and the constant's comment says so:

- **`MARK_MERGE_SECONDS`.** Every group in this grader is already at or under
  it by construction, so a close threshold equal to it would name every group
  in every report — a warning on every line, which is the same as none.
- **`grade_gpu_door.py`'s `CLOSE_MARKS_SECONDS` of 5.** It equals its own
  window, and that equality is meaningful only because *that* grader does not
  merge, so its number says nothing about where a fuse came close. Copying it
  here would be copying a number whose meaning does not travel.

The three-console costs quoted above are the *committed fixture's* spacing.
They are what places the threshold; they are not a measurement of a real
operator, and no live run is claimed anywhere in this file.

## What this does and does not measure

The headline reports **a measured distance between two recorded rows**, and
that is the whole of the claim. It is not a claim that the operator took two
actions, and it deliberately does not attribute the distance to anything on
the writer side.

In particular it does not measure the inter-arm re-snapshot.
[`probe-hold-mark-merge.md`](probe-hold-mark-merge.md) records, as unmeasured,
the cost of the 206 ECRR reads that sit between two marks (`--level-block`
adds 16 when on) — that is why the probe's guard judges `hold` alone and on
the conservative side. Timing those reads is a live run at the machine and
stays a human's step. A figure measured on the reader side from recorded
timestamps does not measure the writer side, and this report does not pretend
it does. The close note says the group *stayed together*; it does not say why
the gap is what it is.

## The tests

Seven, in a new `MarkGapReportTests` class in
`ec/tools/test_grade_0751_isolation.py`, over two hand-built three-console
fixtures (temp-dir, not committed `testdata/`) that differ only in how far
apart the first action's three marks land — 1.0 s and 4.9 s, or 1.0 s and
0.2 s. Both are under the window, so neither is a case the merge refused and
the gap is the only thing that separates their reports.

- `test_marks_4_9s_apart_report_the_gap_and_are_named_close` — the figure
  prints and the close note is present.
- `test_marks_0_2s_apart_report_the_gap_and_are_not_named_close` — the figure
  prints and the close note is **absent**. This is the "printing it
  unconditionally" pin.
- `test_the_two_fixtures_report_differently` — the two reports differ, while
  the exit code, the closing verdict section and the mark headers are
  identical. This is what pins "a report, not a refusal": a change that moved
  a verdict or an exit code to accommodate the note goes red here.
- `test_a_group_of_one_mark_says_nothing_extra` — over the committed
  `0751-isolation-example-quiet.csv`, whose two marks are 60 s apart and so
  are both single-mark groups, neither marker appears anywhere.
- `test_the_gap_is_recorded_per_adjacent_pair` — calls `coalesce_marks`
  directly; asserts one gap per adjacent pair, each equal to the measured
  difference of the two marks it names, those marks being the window's own by
  identity and in order. This is the "dropping the recorded gap" pin.
- `test_a_three_mark_group_names_every_gap_not_just_the_widest` — the headline
  names 1.0 s *and* 4.9 s; the close note names the widest and only the widest.
- `test_block_selection_is_unchanged` — `--block 0xA0` over the committed
  three-console run still prints the same `=== block 1 of 1 …` header, the
  same whole-stream `--- mark i/3:` numbering and the same exit code.

The `--block` guard is structural rather than asserted-and-hoped: `main`
filters with `shown = [i for i, w in enumerate(windows) if w.block is
selected]` **after** `build_windows`, so a new attribute on `Window` cannot
take part in the selection. The test is the regression pin for that, and it is
here because the `--block` scoping family — #497, #498, #530 and #725, in
[`0751-grader-block-scope-claims.md`](0751-grader-block-scope-claims.md),
[`0751-grader-block-scoping.md`](0751-grader-block-scoping.md),
[`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md)
and [`0751-grader-moved-unplaced-scope.md`](0751-grader-moved-unplaced-scope.md)
— reads these same windows and must keep reading the same set of them.

## Two corrections to the issue as filed

Recorded here rather than left to be repeated, and neither is a disagreement
about the work:

- The issue's "seven pinned rows the way #667's were" are **#665's**, at
  `windows/tools/test_manual_fan_ctrl_probe.py`. #667 appears nowhere in the
  tree. `probe-hold-mark-merge.md` is #665's write-up and is what this change
  cites.
- The issue's "#661 and #662" appear nowhere either. The `--block` closing
  shapes that read these same windows are **#497, #498, #530 and #725**,
  named above.

The issue's line numbers are about 1100 lines stale against the tree it was
filed on (`coalesce_marks` is not at `:651-680`), so everything above is cited
by symbol name and file rather than by line.

## Left out on purpose

- **`MARK_MERGE_SECONDS`.** Stays 5. A different fuse window is a decision
  about the grader's own procedure, and #665's write-up already declined it on
  the probe side. `windows/tools/test_manual_fan_ctrl_probe.py` asserts the
  probe's copy against this one; changing it would redden a suite in a file
  this change does not otherwise touch.
- **A `--merge-seconds` or `--i-mean-it` override.** A flag that lets an
  operator write a capture the reader cannot read is the defect, not a
  feature — the same reasoning `probe-hold-mark-merge.md` records against
  `ctgp_dben_probe.py`'s refusal to grow one.
- **A probe-side copy of `CLOSE_GAP_SECONDS`.** The probe's guard is
  *constrained by* the grader's window, which is why its copy is pinned;
  this threshold is the grader's own report vocabulary and constrains nothing,
  so a second copy would be a number to keep in sync for no reader.
- **Committed `testdata/` fixtures and the `testdata/README.md` row.** A row in
  a hand-written shared file is a merge-conflict magnet and needs
  `check_testdata_index.py` registration. The suite's own
  `self.capture(rows, tmp)` idiom builds both cases in a temp dir instead.
- **`report_blocks`, `report_early_exits`, `report_dumps` and the closing
  section.** Aggregates over windows; see above.
- **§3 and #639.** The by-hand `rem mark each console:` boundary spacing is a
  different lever in a different file, and
  [`probe-hold-mark-merge.md`](probe-hold-mark-merge.md) keeps the two apart.
  #639 stays open.
- **`.github/workflows/` and `.github/actions/`,** including landing
  `docs/ci/agent-gates-0751-self-test.patch`. The pipeline's token has no
  `workflow` scope, so prepared-not-landed stays prepared-not-landed. The
  suite is still run by `tools/run-tests.sh` and by the tool's own
  `--self-test`.
- **`docs/findings.md`.** Frozen; a new finding is a new file under
  `docs/findings/`, and `docs/findings/INDEX.md` is regenerated by
  `ec/tools/gen_findings_index.py` rather than edited.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs, reproducible offline with
the commands and the tests named above. **No line of this change may be read
as a report of a capture or a live observation, and none is one.** The two
fixtures are described by the tests that build them and are written by
`MarkGapReportTests.captures`; no fixture was added to `ec/tools/testdata/`
and no committed fixture was edited. §6's day has still not been run on the
machine, which is issue #380's and stays a human's step.
