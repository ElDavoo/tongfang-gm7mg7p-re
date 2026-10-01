# Two captures in one invocation filed one capture's change rows under the other capture's marks, and each capture is now its own run (issue #351)

A write-up for [issue
#351](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/351), which was
opened by the follow-ups pass out of #303. #491 gave this grader its
`distinct_captures()` and its refusal of a *repeated* file; this is the
adjacent case that refusal cannot see, because the command line there is
perfectly well formed. It is also the same error the tool's whole argument is
against, arriving from the other side: #351 files a movement under an action
that did not cause it, which is what the no-merge decision exists to prevent.

**Nothing below is a hardware claim.** The evidence is two constructed CSVs in
`ec/tools/testdata/`, built in a temporary directory where the case needs it,
and the grader's own source. No image is opened, no register is read back, and
no EC, laptop or Windows machine is involved. What keeps either file from
being mistaken for a run is the `CONSTRUCTED INPUT, NOT A CAPTURE` header it
carries; the dates cannot, because the two are a day apart on purpose.

## What the concatenation did, on the committed fixtures

`ec/tools/testdata/gpu-door-example-two-files-{a,b}.csv` are the issue's
repro as a fixture pair: two marks thirty seconds apart on 2026-01-01 in the
first, one mark with two rows before it on 2026-01-02 in the second. Before the
change, one invocation over both printed this (abridged to the lines the
argument is about; the full report is 24 address lines per window):

```console
$ python3 ec/tools/grade_gpu_door.py ec/tools/testdata/gpu-door-example-two-files-a.csv \
                                  ec/tools/testdata/gpu-door-example-two-files-b.csv
=== 3 window(s), one per mark, none merged ===

--- mark 2/3: 2026-01-01T12:00:40+01:00  'ac unplug' (…-two-files-a.csv)
    window runs to the next mark
    0x07C4-0x07D7: 2 of 20 addresses moved
      0x07C6  0x00 -> 0x01   (+75562.0s)   WMS0 b0-1
      0x07C4  0x28 -> 0x38   (+75565.0s)   DBEN b3, DBST b5

=== what this does and does not settle ===
  No window had both blocks moving (2 of 3 moved one block only), so §5's
```

`b.csv`'s two change rows are filed under `a.csv`'s `ac unplug` mark, **21
hours earlier**. Four separate things in that report are wrong, and the
offsets are the least of them:

- **A movement is filed under an action that did not cause it.** The rows were
  recorded on 2026-01-02 and are attributed to an action from 2026-01-01. That
  is the mis-attribution the module's no-merge paragraph is written against,
  and here it is silent: `report_close_marks` has a threshold and a threshold
  is not what was crossed — 21 hours is not "close", so the one check that
  would have said something says nothing.
- **`window runs to the next mark` is false.** The next mark after
  `a.csv`'s `ac unplug` is `b.csv`'s, so this window is bounded by a mark in
  another file, and the report never says a file boundary was crossed.
- **`=== 3 window(s) ===` is a count over two runs.** Three is the sum of two
  captures' windows, and every count in the report is a denominator over
  windows — so the closing's "2 of 3" describes a run nobody performed.
- **Nothing anywhere says two captures were handed in.** The per-file census
  lines are the only trace, and they are above a report that reads as one
  capture.

The reachability is not exotic. `ec_watch.py` and `gpu_block_watch.py` write
the same `ts,addr,old,new` schema on purpose (the issue says so, and
`windows/tools/gpu_block_watch.py` is written to it), so grading a sweep
beside a door capture is a well-formed command line an operator reaches
without pasting anything.

## The rule, and why this one rather than refusing a second path

The issue offers two options. **This takes the second**: keep `nargs="+"` and
cut windows per `source`, so each file is its own run with its own §6 closing.

The first option — one positional, full stop — is **defensible and was
already declined**, and the reason is on file rather than re-litigated here.
`docs/findings/grader-repeated-capture.md` records "One positional, full stop"
for this tool as the option not taken, so that the three `nargs="+"` capture
graders keep **one** rule over one input shape; `grade_timer_sweep.py`'s
docstring documents "one or more CSVs" and a test holds that two distinct
captures are one run. Refusing a second path would re-open a decision this
repository made and wrote down, to fix a hazard the per-`source` cut closes on
its own. The per-`source` cut is also the reading that keeps `ec_watch.py` and
`gpu_block_watch.py` grading side by side safely, which is the operator
workflow the issue names as the reachable case.

Both refusals in this grader are now per capture rather than per command line,
and that is a consequence of the rule rather than a second one: two marks at
one instant in *different* files are two windows in two runs, and only two
marks at one instant in the *same* capture are the phantom window the
shared-timestamp refusal is about.

## What the cut is, precisely

`build_windows` groups marks and change rows by `fan.capture_key(row.source)`
before it cuts, and hands each group to the same per-capture pass. Three
things follow, and each is a change to the report rather than to the arithmetic:

- **`report_window`'s "window runs to" names the file.** The last window of a
  capture runs to that capture's end, not to a mark another file recorded
  later. Before, the line read "the end of the capture" over a sequence that
  ended 21 hours later — true of the run, false of the window.
- **`report_close_marks` fires on a file boundary** the way it fires on a 5 s
  gap: naming both files, the distance, and the fact that the two are two runs.
  The threshold check does *not* fire on it, and that is the whole ordering:
  `CLOSE_MARKS_SECONDS` asks whether two action boundaries were close, which is
  a question about one console's hands, and has no answer to give about where
  one capture ended and the next began. Every pair *inside* a capture is still
  walked, so a one-capture run is unchanged.
- **`report_settle` closes each capture separately**, over its own windows.
  This is where the cut is most load-bearing, because every count in the
  closing is a denominator over windows: the pair now prints "1 of 2" for
  `a.csv` and the third bullet for `b.csv`, where the sum was "2 of 3".

## Two cases the cut created, which the issue does not name

Both were found by reading the new code against a command line rather than
from the report, and both are cases the concatenation used to absorb rather
than to refuse. Neither is in the issue; both are in the suite.

**A capture with change rows and no MARK row is now refused, by name.** The
no-marks refusal used to ask only whether *any* capture on the command line had
a mark, which was the whole question a single-capture invocation could ask and
is the wrong one the moment a second file is named. Under the cut such a
capture's rows belong to no window of its own, and they cannot be read as
another capture's either — that was the defect — so §5 has no column for them
and the run is refused rather than reported over with a figure quietly
missing. Before the cut the same input was graded, wrongly, under the other
file's marks; the case was never a refusal because there was never a need for
one.

**A capture with neither a mark nor a change row is still a run.** The
opposite side of the same line, and the one that would have been easy to get
wrong: building the run list from the rows alone drops such a file from the
report without saying so, so a reader sees one §6 reading where the command line
named two. It is now reported with a window count of zero and a closing that
says what is missing — a *missing* §6 reading would read as a capture whose
bytes held still, which is the `docs/findings.md` §4c shape reached by a
different road. The sentence says both halves: nothing was recorded, which is
not nothing moved. Such a file is not refused, because there is nothing in it
to misfile.

## Captures that overlap in time are graded, not refused

A file's change rows falling **between two marks of another file** are the
shape two watchers running at once produce, and the cut grades them: each
capture's windows are cut from its own marks, so such a row is filed under a
mark of the capture that recorded it, exactly as it would be if the other
capture had not been named. `test_rows_that_interleave_another_captures_marks_are_graded`
is that shape — the second capture's marks fall between the first's two and its
rows fall inside the first's window — and it asserts the rows land under its
own marks.

An earlier draft of this change **refused** that case instead, on the stated
ground that the row "is attributed to nothing". That ground does not hold, and
the write-up's own fixtures are why:

- The refusal was justified as *the one case the cut cannot grade*. It is not
  the one case, because there is no such case. The no-marks refusal runs first
  and refuses a capture carrying rows with no mark, so by the time any interleave
  check could run every capture carrying rows carries a mark — and
  `build_windows` then places every one of that capture's rows: under a mark of
  its own capture when it follows one, and as the opening `levels` of its first
  window when it precedes them.
- The refusal cost the operator workflow this change exists to enable. The
  argument for keeping `nargs="+"` is that `ec_watch.py` and
  `gpu_block_watch.py` write the same schema and can be graded side by side —
  and those two files interleave exactly when both watchers ran at once, so
  the refusal rejected the reachable case while the write-up claimed to have
  kept it.

## Calibration

- **A zero is "not moved by this method under this action", never "absent".**
  The new closing sentences were written to that rule, and
  `test_no_report_moves_a_status_or_claims_an_absence` keeps holding over the
  new fixtures, since it iterates `FIXTURES`.
- **The fixtures claim nothing.** Both carry the directory's
  `CONSTRUCTED INPUT, NOT A CAPTURE` header and the "not a prediction" clause
  every other row in `ec/tools/testdata/README.md` carries, and
  `test_each_fixture_is_a_constructed_capture_with_marks` asserts each of the
  two. Their rows are dated `2026-01-01` and `2026-01-02` — a day apart, which
  is what keeps either file's rows from falling between the other's marks —
  and only the first is the placeholder date that test asserts, so the second
  file's rows are described here rather than checked.
- **Marks are not merged, on purpose.** `coalesce_marks` is still not called
  and `collided_marks` still compares for equality alone; the per-`source` cut
  assigns changes within a capture and widens no threshold.
  `test_two_marks_a_millisecond_apart_are_two_windows` and
  `test_close_marks_are_flagged_and_never_fused` pass unchanged.
- **`+75562.0s` is an artefact of concatenating two days**, named as such
  above and asserted absent from the report, not read as a latency.

## The tests, and what they would catch

Eight new cases in `ec/tools/test_grade_gpu_door.py`, all offline and all over
committed inputs or a `tempfile`:

1. **The defect, closed** — grade the pair, walk every window's change rows
   against `w.source` through `capture_key`, and assert none is from another
   capture. Walked over the data rather than the printed report, so a report
   that filed a row correctly and printed a neighbouring line naming the other
   file cannot pass it. The count assertions in the same case are there to
   stop it being vacuous over an empty window set.
2. **The report says so** — per-capture window counts naming the file,
   `window runs to` naming the file it runs to, `b.csv`'s rows accounted for
   near its own mark, and no offset over an hour anywhere.
3. **The boundary note** — both files, the gap, "two captures and two runs",
   and the 5 s note *not* fired on it; with the close-marks fixture over one
   file as the case the threshold check still runs.
4. **The closing** — a closing per capture, the denominators each capture's,
   and the "2 of 3" sum absent.
5. **Captures that overlap in time** — a `tempfile` pair whose second file's
   marks fall between the first's two and whose rows fall inside the first's
   window, graded with each row under its own capture's mark. Built in a
   temporary directory rather than added to `FIXTURES` for the reason the
   `COLLIDING_MARKS` comment already gives: a file in `FIXTURES` is by
   definition one some run grades, and these two have to interleave, which the
   committed day-apart pair does not.
6. **The single-capture control** — each new fixture graded alone still
   reports what it did before, so the per-capture figures are pinned to the
   multi-capture command line and not to the fixture. This is what
   `test_a_capture_given_twice_is_refused` already does with its own control.
7. **A capture with rows and no marks is refused** by name.
8. **A capture with nothing in it is still a run** — zero windows, and a §6
   reading that says what is missing rather than being dropped.

Cases 1-6 fail against the pre-change grader, which is how a test for a defect
is told apart from a test that describes the code it ships with. Cases 7 and 8
are the two the cut created, and they fail against it on the same footing.

## Not taken, and why

- **`grade_0751_isolation.py`'s three-console merge.** #169 is open on it and
  its merge is correct *for its run*: that procedure runs one watcher per
  console, so one action lands in three files and merging them is the point.
  Here merging is the defect. A different module and a different question.
- **`grade_timer_sweep.py`'s contract.** It documents "one or more CSVs" and
  is not what this issue is about.
- **A `mark(s), change row(s)` line per file in the §6 closing.** The
  per-file line already prints at read time and this change does not remove
  it; what moves is the *closing*, which counts windows.
- **Judging whether two captures on consecutive days are a legitimate thing
  for an operator to grade.** That they can be is what this change preserves;
  whether a given pair *should* be is the reader's call against §6, and the
  boundary note is where the tool puts both files in front of them.
