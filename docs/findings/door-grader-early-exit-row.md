# The door grader dropped the watcher's "the run ended early" row, and a 3-second window graded as a 31-second one (issue #684)

The write-up for [issue
#684](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/684), the
follow-up `docs/findings/0751-early-exit-row.md` left open by name. That
change taught `grade_0751_isolation.py` to read the `# the run ended early:`
row `manual_fan_ctrl_probe.py` writes, and recorded that `grade_gpu_door.py`
"has the same blind spot. It reads the same probe captures through the same
`read_capture` and so drops the same row. It is not in this change's scope and
the decision may not be the same one."

This is that follow-up, and the decision is *not* the same one: the 0751 rule
is taken, with the **window** as the unit rather than the block. Nothing here is
evidence about the machine and no register status moves. `MANUAL_FAN_CTRL`
stays `present-untested` and #663 still owns the fan run; `0x07D0`/`0x07D1`
stay DO-NOT-WRITE-BLIND. Both ends are exercised offline, against a faked
`ecrw` and a constructed capture in a temporary directory; no laptop and no
Windows host was involved.

## The reach, as the code stood

Two ends, each already in the tree.

The writer, `windows/tools/gpu_block_watch.py`, caught `KeyboardInterrupt` and
`EcError` and closed its sink in a `finally`, and neither arm wrote anything:
so a door capture could not carry the phrase at all.

The reader, `ec/tools/grade_gpu_door.py`, calls `fan.read_capture(path)` per
path, which skips every `#` row — deliberately, and for the same reason the
0751 side skips them, so an operator can annotate a capture by hand. Between
that call and `return 0`, nothing looked at a `#` row: every mark opened a
window, every window printed, and the exit code was 0.

Measured on a copy of `ec/tools/testdata/gpu-door-example-close-marks.csv` with
one row written in after its second MARK line, stamped inside the second window
(12:00:11 to 12:00:42), against `git show HEAD:ec/tools/grade_gpu_door.py`:

```
    python3 /tmp/e684/old/grade_gpu_door.py /tmp/e684/close.csv
```

```
/tmp/e684/close.csv: 3 mark(s), 3 change row(s)
=== 3 window(s), one per mark, none merged === (/tmp/e684/close.csv)
```

exit **0**, and `grep -in 'early\|ended early\|not graded\|withheld'` over the
whole report matched nothing. The row is not counted — not because it was
refused, but because nothing looked. Each of those three windows prints its
`0x07C4-0x07D7: N of 20 addresses moved` and `0x0743-0x0746: N of 4 addresses
moved` lines, and those are the lines §5's third and fourth cells are read
from: a window cut at 3 s of a 31 s hold reports the same two figures in the
same format as one that ran its hold. That is the false green, and a reader of
the table cannot see it.

`ec/tools/testdata/` is deliberately untouched: every fixture there is one some
run grades and every one of those has to exit 0, and a fixture carrying this row
exits 1 by design. `test_every_door_fixture_is_one_this_suite_runs` holds the
directory equal to the suite's `FIXTURES` set, and the new cases build their
captures in a `tempfile.TemporaryDirectory()` — which is what `write_capture`'s
own docstring says that directory is for.

## The decision: the window, not the block

The 0751 rule with a different unit, and the difference is forced rather than
chosen.

The 0751 grader charges a placed row to `Block.problems`, and a block with a
problem has its windows withheld by the machinery that withholds every other
block with one. The door grader has no `Block` and no `Block.problems`, so
there is nothing to charge a row to — and its unit of grading *is* one window,
because §3 of `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` asks for each
action to be "its own pair of marks with a hold between them — mark, act, hold,
mark" and one mark opens exactly one window.

That gives the rule a placement the block version does not need to argue about:
a run that stops during a hold never writes that hold's closing mark, so the row
falls in the window its action mark opened, and there is no later window to
absorb it. The 0751 grader's "last window at or before the row" is kept as it
stands, because it is the same rule with a different name for the thing: a row
says *when* a run stopped, and the window it stopped inside is the one whose
mark is the last one before it.

The blast radius is bounded the same way the 0751 procedure states it — "The
rest of the day is unaffected". The windows that closed normally are graded in
full, and a second capture named on the same command line is graded as it would
have been: placement is per capture, through `fan.capture_key`, which is this
module's existing per-capture cut and the rule `capture_runs` already exists to
enforce. One file's crash cannot withhold another file's windows, and there is
a case for that over two captures.

## Why the span rule was declined

The in-tree precedent for the other answer is `ec/tools/grade_timer_sweep.py`,
where `span` is the extent of the data, printed in the header, and every claim
the report makes is qualified "over this span". That is what makes a truncated
timer capture's report honestly bounded with no terminator at all, and it is
the answer #674 explicitly left open.

It is not available on the door side today, for a checkable reason rather than a
preference: the span is not derived from the data rows. `grade_timer_sweep.py`'s
`load()` reads it off the `# baseline <ts>` and `# ended <ts>` comment rows that
`ec_timer_capture.py` writes, and `gpu_block_watch.py` writes neither. Adopting
the rule would first need that same writer change, on top of the one this
change makes.

So it is recorded here as a residual rather than silently dropped. It is worth
revisiting as a *second* mechanism rather than an alternative one: the span
bounds prose, and the exit code is what the issue asks for, which the row
gives. The two are complementary, and adopting the span later would not retire
this row.

## The writer's arm, and why it is not the probe's

`manual_fan_ctrl_probe.py` catches `BaseException`, and this change deliberately
does not copy that. The probe's unit is a block with a `finally` restore and a
known end: whatever ended the run, the restore is written and the block reads
`intact`, which is precisely why its row has to say what the check cannot.

`gpu_block_watch.py` cannot copy it. §3 of the door procedure says `--seconds`
"defaults to running until Ctrl-C, which is the right default here", and the
tool's own console prompt says "Ctrl-C to stop". Ctrl-C is the documented way
to end a run that finished. Writing "the run ended early" on every Ctrl-C would
stamp a stopped run onto every *successful* door capture — §4c's shape, with a
method reporting an absence as a fact, arrived at from the other direction.

So `except EcError` writes the row and `except KeyboardInterrupt` writes
nothing. An EC read that fails mid-sweep is a run that stopped part way through
— that arm already returned 1 — and the sweep it was in the middle of is not a
sweep anyone can read. The row is written before the `finally` closes the sink,
so it is in the file rather than in a terminal nobody reads twice.

The tag is a second spelling of `grade_0751_isolation.EARLY_EXIT_TAG` and is
transcribed rather than imported, because `from ecrw import Ec, EcError` binds
kernel32 at import time: this file loads only on Windows and the grader would
load nowhere else. What holds the two equal is
`windows/tools/test_gpu_block_watch.py`, which asserts the equality and then
reads the row this writer actually produced through the grader's own reader —
the twin of the drift guard `manual_fan_ctrl_probe.py`'s `--self-test` carries
for its own copy. A drifted tag is not a wrong-looking string: it is a reader
that matches no stopped capture, and a capture of a crashed run that grades
green.

## What the report can now say, and what it cannot

Every new printed sentence is a claim about **which files were handed in and
which windows this run graded**. The three that matter:

- A **placed** row withholds the window it names, the section above the windows
  names it, and the exit code is 1. The withheld window keeps its
  `--- mark n/total` heading and its `window runs to ...` line, so the mark stays
  locatable and the numbering still matches a run in which nothing was
  withheld; what is replaced is the movement block, the ordering lines and all
  24 `net`/`total`/`max` lines. Half a hold is not a smaller claim than a whole
  one, it is no claim at all.
- The §6 closing counts the withheld windows rather than reading their absence
  as movement. That is the same shape as the branch it already had for a
  capture holding nothing — which exists because "no window" and "nothing
  moved" are different answers — reached through one withheld window rather
  than through a window count of zero. None of §6's three readings is available
  from a run whose own capture records it stopping.
- An **unplaceable** row — no readable timestamp, or stamped before its
  capture's first mark — refuses the whole run before any window is built, to
  stderr by name, alongside the three refusals `main` already had. That is
  `grade_0751_isolation.EARLY_EXIT_REFUSAL`'s tier: a row that says a run ended
  and not when leaves every window's length uncertifiable.

Named here because they are the sentences most able to overclaim: none of them
says the door did not execute, none says a byte did not move *because* of
anything, and none of the words `absent`, `unused`, `unreferenced`,
`confirmed-working` or `confirmed-inert` appears anywhere above
`=== what this does and does not settle` — which
`test_no_report_moves_a_status_or_claims_an_absence` already checks over every
committed fixture, and which the new section prints inside.

Two things are unchanged and were held that way. `read_capture` is not touched:
its `#`-row skip is the invariant #674 built `read_early_exits` *beside* rather
than through, its two-tuple is a contract with `check_capture_claims.py` as well
as with this file, and every committed fixture opens with a `#` block. The
second reader runs beside it, which is what `capture_rows` is a shared seam
for. And the census line gains `, N early-exit row(s)` **only when N > 0**, so
every committed fixture and every hand-annotated capture grades byte for byte
as it did — the invariant `test_a_hand_annotated_capture_grades_exactly_as_it_did`
holds on the 0751 side, and now over this one too.

The operator-facing rule went into the module docstring (which is argparse's
`description`) and into §3 and §5 of the procedure, and not into the `csv`
argument's help: `test_the_csv_help_promises_no_refusal_this_tool_does_not_make`
holds that string against promising a refusal the code does not make, and a
sentence outlived the refusal it described that way once already.

## The offline proof

Over the temp copy above, with the row in the same place:

```
    python3 ec/tools/grade_gpu_door.py /tmp/e684/close.csv
```

```
/tmp/e684/close.csv: 3 mark(s), 3 change row(s), 1 early-exit row(s)

=== early-exit rows (a run that did not reach its closing mark) ===
  close.csv (1 row(s)):
    2026-01-01 12:00:14+01:00  in mark 2/3 of /tmp/e684/close.csv ('gpu
    tgp 115W->130W'): gpu_block_watch: EcError: DeviceIoControl failed
```

exit **1**, `--- mark 2/3` printed with its heading and its `window runs to`
line and then `NOT GRADED` in place of its body, windows 1 and 3 in the usual
format, and the closing reading `1 of the 3 window(s) above was withheld`.

The two refusal shapes, over copies of the same fixture: a row with no
readable timestamp, and one stamped at 12:00:05 — before the capture's first
mark at 12:00:10. Both exit 1 with nothing window-shaped printed, and the
second is refused because placement is by timestamp rather than by where in the
file the row was written, so being in the middle of the capture does not rescue
it.

A capture whose *only* content is the row is refused too, with no mark there is
no window for it to have cut short — which is the §4c case this closes: before,
that file graded as a capture that recorded nothing and said nothing, which
reads the same as one that recorded nothing because nothing moved.

The writer side is exercised against the suite's existing faked `ecrw`: an
`EcError` raised mid-sweep writes the row into the sink before it is closed and
it is in the file the run leaves behind; a `KeyboardInterrupt` — which is how
`FakeEc` ends every run in that suite, so it is the ordinary case — writes
none.

`ec/tools/test_grade_gpu_door.py` grew an `EarlyExitTests` class over those
cases and `windows/tools/test_gpu_block_watch.py` an `EarlyExitRowTests` one.
Run them with `python3 -m unittest discover -s ec/tools` and
`-s windows/tools`, or `bash tools/run-tests.sh` for the tree.

## What this opens, as a fact rather than a fix

Three things this change does not do, named so they are follow-ups rather than
oversights.

- **A run Ctrl-C'd before its closing mark still grades in the usual format.**
  This is the "no fallback" gap the issue names. Nothing in the file records
  that a mark is missing: the marks are the only evidence an action was taken,
  and a file that ends after an action's opening mark ends the same way whether
  the operator pressed Ctrl-C or the machine slept. The writer's `EcError` arm
  cannot see it, and the reader has no mark-pairing check — `grade_gpu_door.py`
  takes every `MARK` row as opening a window and never asks whether the marks
  pair up. That is a separate question with its own answer: mark pairing, or a
  span, taken on its own.
- **The span question**, for the reason given above. `gpu_block_watch.py`
  writes no `# ended` row, so there is nothing to read one from; a
  `#`-terminator convention for the door capture is a capture-format decision
  and not this issue's to make.
- **`windows/tools/ec_watch.py` still writes no such row**, which
  `docs/findings/0751-early-exit-row.md` already recorded as a separate change
  with its own capture-format question.