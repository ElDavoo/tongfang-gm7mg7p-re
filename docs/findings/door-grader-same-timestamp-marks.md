# Two marks on one timestamp open a phantom window in the door grader, and the grader refuses it rather than the writer catching it (issue #1376)

A write-up for [issue
#1376](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1376), which was
opened by the follow-ups pass out of #1307. #491 closed a different door: it
refuses a capture *file* listed twice, which is a fact about the command line
and is decided before anything is read. What is written up here is a fact about
the *marks* inside one capture, which that refusal cannot see, and which one
perfectly well formed command line can carry.

**Nothing below is a hardware claim.** The evidence is two constructed CSVs in
a temporary directory, the committed writers' own source read as text, and the
grader's own source. No image is opened, no register is read back, and no EC,
laptop or Windows machine is involved.

## Which side owns it, and why

**The grader.** The issue's own argument for the grader-side option is that it
"does not rest on the operator never pasting", and that is the whole of it: a
rule at the writer is a rule in a class that has no rule to put it in.

`Marker`'s constructor (`windows/tools/ec_watch.py:436`) takes `check` and
`forms` and documents why both default to `None` rather than to a rule:
`windows/tools/gpu_block_watch.py:166` builds `Marker(sink)` with neither, so
that §3's free-form labels go straight in. A millisecond floor inside `Marker`
is not the same kind of addition as the two refusals `_loop` already has — the
blank press (`:484`) and the unplaceable label (`:497`) — because those test
the *label*, and a shared timestamp is a property of the *clock*. It would also
not be a side effect of this issue to add one: it is a design decision for a
class two callers share, and the second of them is the reason the class has no
rule today.

The second reason is the one the decision turns on: **a capture assembled by
hand from two files never passes a writer at all.** The door procedure's
capture is `gpu_block_watch.py --csv --mark`; two of those pasted into one file
are a file, and a rule in `Marker._loop` has nothing to say about it. The
grader is the only place that sees the result.

And this grader is the one place that *needs* the rule, because
`grade_0751_isolation.py` cannot produce the shape. Its `build_windows`
(`:1981`) calls `coalesce_marks` (`:1882`) first, which fuses anything within
`MARK_MERGE_SECONDS` (`:315`, 5 s) into one window. That fusion is correct
there — §3 of *that* procedure runs one watcher per console, so one action
lands as three MARK rows and the alternative is a window reporting "nothing
moved" for a write that did move things. This procedure runs one watcher on one
console, and fusing is the *mistake* for it, in the same way a repeat is a
mistake here. The 0751 grader is immune to a phantom window because it fuses by
default; this one cannot fuse without attributing one action's movement to
another, so the collision has to be refused instead.

> **Corrected 2026-09-30, review of #1432: the three anchors in the paragraph
> above were `:1816`, `:1773` and `:284`, and none of them named what it was
> cited for.** In `ec/tools/grade_0751_isolation.py` today `def build_windows`
> is at `:1981`, `def coalesce_marks` at `:1882`, and `MARK_MERGE_SECONDS = 5`
> at `:315`; the three lines the old anchors landed on are a `with open(path…)`
> inside a capture reader, a sentence of a docstring, and the module's own
> `--wrote` example. Corrected in place per `docs/findings.md` §4a rather than
> edited silently, and nothing else in the paragraph is disturbed. The three
> old anchors were correct in the tree #1416 merged (`edf0f4f2`), and the drift
> came afterwards: #1409's `126a67c8` added 346 lines to that file and moved the
> three to `:1948`, `:1849` and `:310`, #1437's `6b58bc17` moved them again to
> `:1953`, `:1854` and `:315`, and #1450's `ab594a22` to the three above.
> Three commits moved that file and no page re-read its pins, so re-derive
> them with
> `grep -n -e "def build_windows" -e "def coalesce_marks" -e "^MARK_MERGE_SECONDS" ec/tools/grade_0751_isolation.py`
> rather than by shifting the previous set: the moves are not the same size.
> #1450 moved the two functions +28 and left `MARK_MERGE_SECONDS` at `:315`, so
> a read that stops at #1437 leaves `:1953` and `:1854` — and both of those are
> blank lines today. Review of #1432 is only what put these three in the same
> screen as the path correction below.
>
> **All three edits to this page are outside #1432's stated scope, and are kept
> anyway.** The issue lists *Editing
> `docs/findings/door-grader-same-timestamp-marks.md`* under *Not taken*, and
> the plan said it did not. What is here is the qualification of "no run has
> been taken" — that one is #1432's own, since the capture it records is what
> #1432 is about — beside two pre-existing errors this PR read past and then
> cited: these three anchors, and the `windows/tools/` directory in the bullet
> further down. Both were already wrong on `origin/main`, and a page about wrong
> pins leaving two of them standing behind new ones is not a state this
> repository should merge, so they are corrected and disclosed here rather than
> dropped. Reverting either is one `git checkout origin/main --` away, and the
> call belongs to the maintainer rather than to the branch that noticed.

## How two marks reach one instant, from the writers' own source

Stated as what the committed code does. **This is not a frequency claim, and
nothing here measures how often it happens** — a capture with two marks at one
instant can be constructed, and the writers below can produce one, but no run
has been taken and no operator has been observed.

> **Qualified in place, 2026-09-30, by issue #1432:** the second half of that
> — "no run has been taken and no operator has been observed" — was written
> about §3's *door* procedure, a `gpu_block_watch.py --csv --mark` capture with
> one watcher on one console, and for that procedure it still holds. It does
> not hold for the second writer named below, `input_mark_loop`
> (`ec/tools/ec_timer_capture.py:227`), which has since produced one committed
> instance of the collision, in
> `evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv` lines 1711-1712:
> `auto: event7 scan 0xb0` and `auto: event7 key 184 pressed`, both at
> `2026-09-24T21:21:11.447+02:00`, written by one run of that loop on a
> machine. The first half is untouched by this: one instance is not a rate, and
> nothing here or there measures how often this happens. The paragraph above is
> kept as it stood rather than edited out, per `docs/findings.md` §4a; the
> reconciliation is
> [`perturb-arm-colliding-marks.md`](perturb-arm-colliding-marks.md).

- `windows/tools/ec_watch.py:121` stamps a mark with
  `datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")`.
  Millisecond resolution, and `Marker._loop` (`:466`) writes one row per
  `sys.stdin.readline()` unconditionally once the label is accepted — one line
  in, one row out, with nothing between two lines that arrive in the same
  millisecond.
- `ec/tools/ec_timer_capture.py:78` is the same `now()`. `auto_mark_loop`
  (`:205`) calls it once per changed key inside a single poll, so one AC or lid
  transition that moves two keys writes two marks back to back;
  `input_mark_loop` (`:227`) writes one mark per evdev record, and one
  keypress arrives as `EV_MSC`/`MSC_SCAN` and then `EV_KEY`, so a capture
  taken with the operator's hands on the machine writes a mark for each of
  those.

> **Corrected 2026-09-30, review of #1432: the bullet above named the file
> `windows/tools/ec_timer_capture.py`, and no such file has ever existed here** —
> `git log --all -- windows/tools/ec_timer_capture.py` is empty and
> `find . -name 'ec_timer_capture*'` returns only the one copy. The capture is
> Linux-side and lives at `ec/tools/ec_timer_capture.py`; it names itself that
> way in the banner it writes at the top of its own CSV (`:304`), and every
> other citation of it in the tree spells it the same way —
> `grade_timer_sweep.py`, `measure_mark_provenance.py`,
> `docs/hardware-tests/xdata-06c2-06db-sweep.md`, and the other files under
> `docs/findings/` that name it. The line numbers were never the problem:
> `now()`, `auto_mark_loop` and `input_mark_loop` sit at `:78`, `:205` and
> `:227` in the real file, and the blockquote above already cites `:227` for
> the third. So this was one directory prefix, and correcting it is what keeps
> the page from carrying two homes for one symbol — the blockquote above and
> this bullet name the same two functions. Corrected in place per
> `docs/findings.md` §4a rather than edited silently, since #1416 merged the
> bullet as written.

`docs/findings/grader-repeated-capture.md:47-48` already recorded the route
and declined to close it: "`_loop` does not refuse a paste". It is recorded
here for the same reason, and #1376 does not close it either — it moves the
consequence to the one component that has to handle it.

## What a shared timestamp costs, measured

The grader as it stood before the refusal, over a capture written by
`write_capture` and `COLLIDING_MARKS` in `ec/tools/test_grade_gpu_door.py`'s
`RefusalTests`, which is where a reader can change the two timestamps and get
any of the variants above. The file is reproduced in full below, so the run can
be repeated against the commit before the refusal:

```csv
ts,addr,old,new
2026-01-01T12:00:10.000+01:00,MARK,,fn mode balanced->performance
2026-01-01T12:00:10.000+01:00,MARK,,gpu tgp 115W->130W
2026-01-01T12:00:10.400+01:00,0x07C4,0x08,0x28
2026-01-01T12:00:11.900+01:00,0x0743,0x00,0x0A
```

```console
$ python3 ec/tools/grade_gpu_door.py collide.csv
collide.csv: 2 mark(s), 2 change row(s)

=== 2 window(s), one per mark, none merged ===

--- mark 1/2: 2026-01-01T12:00:10+01:00  'fn mode balanced->performance'
    window runs to the next mark
    0x07C4-0x07D7: 0 of 20 addresses moved
      nothing in this block moved by this method under this action
    0x0743-0x0746: 0 of 4 addresses moved
      nothing in this block moved by this method under this action
    no ordering to report: neither block moved in this window
      0x07C4-0x07D7:
        window delta  0x07C4  ???? -> ????  net +0  total 0  max 0  (0 changes, level not in these captures)
        ...                                    # all 24 watched addresses
--- mark 2/2: 2026-01-01T12:00:10+01:00  'gpu tgp 115W->130W'
    window runs to the end of the capture
    0x07C4-0x07D7: 1 of 20 addresses moved
      0x07C4  0x08 -> 0x28   (+0.4s)   DBEN b3, DBST b5
    0x0743-0x0746: 1 of 4 addresses moved
      0x0743  0x00 -> 0x0A   (+1.9s)   GNEN b0, ECDC b1
    which block moved first: 0x07C4-0x07D7 (0x07C4, +0.4s after the mark)
      led 0x0743-0x0746 (0x0743, +1.9s after the mark) by 1500 ms

  note  marks 'fn mode balanced->performance' and 'gpu tgp 115W->130W' are 0.0s apart, inside the 5s flag threshold.
  ...
  Both blocks moved in 1 of the windows above, so §5's ordering column has a
```

and it **exited 0**.

Three shapes of damage, and each is one
`docs/findings/grader-repeated-capture.md:27-36` measured for a repeated file,
one level down — with a fourth below them that the repeat has and this does
not.

- **One of the two windows is empty.** `build_windows` (`:207`) sets each
  mark's `end` to `marks[n + 1].ts` (`:230`), so the first of a pair at one
  instant is given a span of `[t, t)` and takes no change row at all. A window
  that spans no sweep has no level to print, so all 24 watched addresses read
  `???? -> ????`. The second window receives every row.
- **The window count reads one per mark**, and the first of them is a boundary
  no action took.
- **The `0.0s` close-marks note is a timestamp offered as a question about
  pacing.** `report_close_marks` (`:331`) does exactly what its docstring
  says — the marks stay two windows, the distance is printed, the reader is
  left to judge whether two close marks were one action. Here the answer is not
  the reader's to reach: there is no interval to reach it from.

**What a shared timestamp does not cost, unlike a repeated file: every change
row printed twice.** That is the `2 change rows` suffix in #491's message, and
it is a statement about the *same row* appearing in two windows' `changes`
lists. `build_windows` advances a single index `i` (`:224` and `:231-234`), so
one file's rows are each assigned to exactly one window, once. The colliding
marks share an instant, so there is no row between them to duplicate. Copying
#491's message across would have sent a reader looking for a damage that is not
there.

## Correction: §5's millisecond column does not move here either

Same correction as `grader-repeated-capture.md:59-82`, and for a stronger
reason on this fixture. `first_change` (`:238`) takes `min` on the timestamp,
and the phantom window contributes no changes to take it over, so the
ordering line is the surviving window's and the figure is what it would have
been. Measured, collided against the single-mark control of the same file:

| figure | collided | single mark | moved? |
|---|---|---|---|
| `which block moved first` | `0x07C4-0x07D7 (0x07C4, +0.4s …)` | same | no |
| `led … by` | `1500 ms` | `1500 ms` | no |
| change-row offsets | `+0.4s`, `+1.9s` | `+0.4s`, `+1.9s` | no |
| `Both blocks moved in` | `1` | `1` | no |
| `window(s), one per mark` | `2` | `1` | **yes** |
| `????` lines in the report | `46` | `22` | **yes — 24 of them are the phantom's** |

The control's 22 are the 24 watched addresses less the two that moved, in a
window that spans the whole capture; the collided run has those 22 in its
surviving window and 24 more in the phantom one, every address of it, because
that window opened and closed on one instant and so has no level to open on.

So the figure that moves is the **window count**, and it moves as a
denominator: `report_settle`'s closing line counts over exactly that count. The
refusal message names it as firmly as it names the figures that do not move,
because a message that implied the millisecond figure moved would be sending a
reader after damage that is not there — the overclaim
`grader-repeated-capture.md` was itself corrected for.

## The alternative readings, recorded rather than buried

**Grade the separable windows and withhold only the ambiguous one**, in the
0751 grader's "partly graded" shape: three marks where two collide would keep
its readable half. Not taken, for two reasons. The withheld-window machinery
— the banner, the withheld count, the denominators that do not double-count —
exists in the 0751 grader and not here, and building it here would be a design
call this issue does not ask for. And a whole-run refusal does have a real
cost: a three-mark run with one colliding pair loses the other two windows
entirely. That is the strongest argument for revisiting this, and it is
recorded as a question below rather than settled here.

**Merge the pair instead of refusing.** Contradicts
`ec/tools/grade_gpu_door.py:30-39` directly, and asserts a fact the capture
does not carry: that two labels on one instant were one action. That is the
mis-attribution `coalesce_marks`' own docstring warns against, and it would be
worse than the phantom, because the movement would then be filed under a label
that did not cause it.

**Compare timestamps by string rather than by instant.** Cheaper, and wrong:
`2026-01-01T12:00:10.000+01:00` and `2026-01-01T12:00:10+01:00` are one
instant, and so is the same instant written at another UTC offset. Both are what
"assembled by hand from two files" looks like. `collided_marks`
(`ec/tools/grade_gpu_door.py:186`) compares the parsed `datetime` the reader
produced, and `test_a_collision_written_two_ways_is_one_instant` holds both
spellings.

## What did not change

- **Marks are not merged, on purpose** (`ec/tools/grade_gpu_door.py:30-39`).
  The refusal does not fuse and does not widen into a proximity test.
  `collided_marks` compares for equality and nothing else, because
  `CLOSE_MARKS_SECONDS` (`:169`) already owns how close is too close and taking
  that over would be the same decision the paragraph forbids.
  `test_two_marks_a_millisecond_apart_are_two_windows` is the pin, and
  `test_close_marks_are_flagged_and_never_fused` is untouched and still green.
- **`build_windows` (`:207`) keeps its own pass.** Issue #169 is open on the
  0751 file, and the collision is caught before it rather than inside it.
- **`report_close_marks` (`:331`) is untouched.** The 5 s note is right for
  marks that are genuinely close; the collision is caught upstream, at the point
  of error.
- **The #491 refusal message is not re-edited.** It hardcodes "all 24" where
  the new one derives the count from `WINDOWS`, which is a real inconsistency
  and a small one. Re-editing merged prose in a file other changes are touching
  is the merge conflict this repository keeps paying for; the inconsistency is
  named here instead. The two refusals are independent and a capture that is
  both repeated and collided is stopped by the earlier one, unchanged.
- **No writer is edited.** `windows/tools/ec_watch.py`,
  `windows/tools/gpu_block_watch.py` and `ec/tools/ec_timer_capture.py` are
  cited as evidence and read as text.
- **No §5 column moves for a capture that grades.** The change is additive on
  the refusal path only; the existing suite is that pin.

## New questions this opens

- **`ec_timer_capture.py`'s `input_mark_loop` writes a mark per evdev record**,
  and one keypress is an `EV_MSC`/`MSC_SCAN` then an `EV_KEY`. A committed
  writer is now known to be able to produce captures this grader refuses.
  Whether it should coalesce that pair into one mark at the writer is a
  question about the writer, and it belongs in an issue about the writer. Note
  only that coalescing there would *remove* a mark rather than refuse one, and
  the two are different decisions.
- **Withhold-the-window rather than refuse-the-run**, in the 0751 grader's
  "partly graded" shape, for a run where only some marks collide. The cost of
  the refusal for a three-mark run is named above and is real.
- **The 0751 grader's 5 s fusion is a different kind of move**, and whether
  three consoles marking inside one millisecond is a correct join or the same
  phantom seen from the other side is not settled here. Named, not claimed.
  `coalesce_marks` and issue #1372 are the adjacent question; this file does
  not take a position on it.
