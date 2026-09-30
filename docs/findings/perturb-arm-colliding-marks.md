# The perturbation arm's capture holds the colliding marks #1376 said had never been taken, and the Fn arm's negative survives both readings of its window (issue #1432)

`docs/findings/door-grader-same-timestamp-marks.md` justified the door
grader's refusal from what the committed writers *can* do, and said so in as
many words: "**This is not a frequency claim, and nothing here measures how
often it happens** — a capture with two marks at one instant can be
constructed, and the writers below can produce one, but no run has been taken
and no operator has been observed."

**One has been taken, and it is committed.**
`evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv` lines 1711-1712
are two MARK rows at one instant:

```
2026-09-24T21:21:11.447+02:00,MARK,,auto: event7 scan 0xb0
2026-09-24T21:21:11.447+02:00,MARK,,auto: event7 key 184 pressed
```

That is #1376's shape exactly: two labels, one instant, one keypress — `0xB0`
is the scan code `uniwill_laptop` delivers as `KEY_F14`, and both rows carry
the same `auto: event7` prefix, so one run of `input_mark_loop` wrote both,
one per evdev record. The route #1376 named from the writers' own source
(`ec/tools/ec_timer_capture.py:227`'s `input_mark_loop`, one press arriving
as `EV_MSC`/`MSC_SCAN` and then `EV_KEY`) is the route that produced it, at
millisecond resolution, on a machine, from hands on a keyboard.

**Nothing below is a hardware claim, and nothing here is a new capture.** Every
figure is read out of a committed CSV by `ec/tools/scan_mark_collisions.py`,
which writes nothing, opens no EC and reads no register. No run was taken for
this page; the run in question is `ed6e5b08`, taken 2026-09-24 for issue
#257, and the only thing new here is the reading of it.

## Six marks for four actions

§4a of `docs/hardware-tests/xdata-06c2-06db-sweep.md` records four actions —
AC out, AC in, the Fn power-mode key, and the lid — and the capture carries six
MARK rows. The extra two are this pair, so the capture has one more action
boundary than it has actions.

```
$ python3 ec/tools/scan_mark_collisions.py evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
  6 mark(s), 3789 change row(s)
  ...
  every mark, parsed:
    0: 2026-09-24T21:18:55.967000+02:00  'auto: AC0.online 1 -> 0'
    1: 2026-09-24T21:20:03.785000+02:00  'auto: AC0.online 0 -> 1'
    2: 2026-09-24T21:21:11.447000+02:00  'auto: event7 scan 0xb0'
    3: 2026-09-24T21:21:11.447000+02:00  'auto: event7 key 184 pressed'
    4: 2026-09-24T21:22:03.719000+02:00  'auto: lid LID1 open -> closed'
    5: 2026-09-24T21:22:23.506000+02:00  'auto: lid LID1 closed -> open'
```

The two `AC0` rows and the two `lid` rows are separate marks because their
actions were, and each pair is seconds apart. The two `event7` rows are one
press, at one instant.

## The corpus scan, and what it measured

`docs/findings/door-grader-same-timestamp-marks.md` said no operator had been
observed. Saying so is a claim about a population, and a population is
something a tool walks rather than something a page asserts, so the tool has a
corpus form: every committed `*.csv` carrying a MARK row, each read by
`grade_0751_isolation.read_capture` and each compared by
`grade_gpu_door.collided_marks` — the grader's own reader and the grader's own
comparison, because a collision is a property of the door grader's reading of
a file, and a second spelling of equality here could disagree with the refusal
it is describing.

Walked on 2026-09-30 over this tree:

```
$ python3 ec/tools/scan_mark_collisions.py
  files walked carrying a MARK row      50
  of those, refused by read_capture     0
  files carrying at least one mark      50
  files carrying a colliding pair       1
  colliding pairs in the whole tree     1
```

**These are that run's figures, not a census, and they are quoted rather than
asserted.** The population grows with every capture a human takes and commits,
so a total written into a page or a test is a value every landing capture has
to edit — the defect `ec/tools/check_pin_table_by_cited_file.py` records, where
four concurrent branches each bumped a count from a different base. The
tool prints no date either, so two runs diff cleanly; the date is here, in
prose, where a reader can see it go stale.

**The method, and what it does not cover.** The walk is bounded to files under
this repository, pruned of `.git`, `.claude`, `vendor` and `__pycache__` — the
pruning `tools/test_readme_suite_table.py` and `census_test_line_pins.py`
already carry, and for the same reason: a `git worktree` under
`.claude/worktrees/` is a second checkout inside this one, and a population
that depends on whether a developer has a worktree open is not a measurement
of this tree. The walk reads the filesystem rather than the index, so in a
clean checkout it *is* the committed set and here it and `git grep -l ',MARK,' -- '*.csv'`
both give 50 (the pathspec matters: without it `git grep` also matches this page and
`scan_mark_collisions.py`, and gives 78) — but an untracked `*.csv` left in the tree
would be counted, which is the same defect one level down, and `marked_captures`'
docstring says so.
A capture taken at the machine and not committed is not in it, and "one pair" is
a statement about the committed corpus and never about how often an operator
does this.

The prefilter is a narrowing and not a decision: a file with no `,MARK,` in it
cannot hold a mark, which is how the walk gets to 50 without being handed the
other `*.csv` files under the tree. Those are 100 files on the walk this
measures, and they are not one population. Some are junk the strict reader
refuses — an annotations table, a decompile index, a battery profile — and the
refusal is usually a header row read as a data row (`Invalid isoformat string:
'scope'` and its siblings), though a minority are refused on `int(addr, 16)`
instead. The rest are **real captures that carry no MARK row**, and
`read_capture` accepts all 8 of them: `evidence/ec-watch/2026-09-24-06c2-06db-sweep-linux.csv`,
`2026-09-24-06d6-reload-linux.csv`, `2026-09-24-06d9-hold-linux.csv`,
`2026-09-18-profile-switch-0400-07ff.csv`, `2026-09-18-profile-switch-0700-07ff.csv`,
`2026-09-23-power-mode-cycle-0f00-0f5f.csv`, `2026-09-23-power-mode-cycle-0700-07ff.csv`
and `ec/tools/testdata/capture-claims-example-power-mode-cycle-0700-07ff.csv` —
each parsing to 0 marks and to change rows — hundreds or thousands in the
seven captures, 13 in the testdata example. So the population stays
"files carrying a MARK row" for the reason the tool's own comment gives, and not
because everything else is unreadable: those 8 are the case that proves the
prefilter is a *population definition* rather than a parse filter, and dropping
them costs nothing here only because a mark is exactly what is being counted. A
file that carries the marker is
still read by the strict reader, and one it refuses is named in the population
block with its reason rather than dropped — a file that cannot be read is a
fact about the scan, and dropping it silently would make the population smaller
than the tree without saying so. The run above refused none of the 50.

**What #1376's file needs, and does not need, correcting.** Its "no run has
been taken" is scoped to a run of §3's *door* procedure — a
`gpu_block_watch.py --csv --mark` capture, one watcher on one console. This
capture is `ec_timer_capture.py`'s, on a different procedure, and nothing here
says an operator has been observed pressing a key twice at one instant. Its
"nothing here measures how often it happens" also stands: one instance in a
corpus that is mostly `testdata/` fixtures is not a rate, and the tool measures
a population rather than a frequency of the thing #1376 cares about. #1416's
paragraph is neither rewritten nor deleted: a dated qualification blockquote
sits beneath it in the `docs/findings.md` §4a shape, carrying the pointer back
here, so the reconciliation is in both files rather than this one alone.

## The Fn arm's negative, re-derived from the capture

§4a's table row 3 gives the action as "21:21:11.447: `MSC_SCAN 0xb0`, key 184
(`KEY_F14`)" and the result as "nothing; `0x0751` held `0x10`". Read as one
mark per action — the contract `gpu-tgp-07c4-07d7-door.md` §3 states as
"mark, act, hold, mark", and which `grade_gpu_door.py`'s module docstring
rests on — the Fn arm's window is `[21:21:11.447, 21:21:11.447)`, and
"nothing moved" over no time is true by construction rather than measured. So
the sentence's missing half is *which interval* the "nothing" was read over.
Two readings, and both hold.

### Over the whole capture: the interval does not matter

`0x0751` has **no change row anywhere in the file**, and the only value the
file carries for it is the `0x0751=0x10` on the `# baseline` line, line 8.
`grade_timer_sweep.load` is what reads both, so the figure below is that
grader's parse of the header rather than a comment re-read by eye:

```
$ python3 ec/tools/scan_mark_collisions.py evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
  watched set: 35 addresses, interval 0.01s, span 369.533s
  ...
    0x0751  baseline 0x10  0 change row(s)  no change row in the whole capture
```

So "held `0x10`" is a fact over 369.533 s and all 35 watched addresses, and it
depends on no window at all — not on where the action boundary was drawn, and
not on whether the boundary is the degenerate `[t, t)`. **That is what makes
the claim independent of the collision rather than lucky under it.**

**A zero here is a row count, not a verdict on the byte.** A change-row
capture records transitions, not values, so a byte that moved and came back
between two of the watcher's own sweeps reads as quiet, and `0x0751` holding
still is not evidence about what the EC does with it —
`ec/annotations/registers.yaml` says so in its own caveat, and
`docs/findings.md` §4c retracted a "does not exist" claim built on a
zero-reference scan. The tool prints the word it means, `no change row in the
whole capture`, and the write-up keeps that distinction in front of the figure
rather than after it.

### Over the interval the door grader would have graded: only the sweep moved

The other reading takes the window the door grader's own `build_windows` would
have used had it not refused — the second of the pair to the next mark:

```
$ python3 ec/tools/scan_mark_collisions.py evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
  collision: 'auto: event7 scan 0xb0' and 'auto: event7 key 184 pressed' are both 2026-09-24T21:21:11.447000+02:00
    the second of the pair to the next mark 'auto: lid LID1 open -> closed' at 2026-09-24T21:22:03.719000+02:00:
      52.272s, and 525 of the capture's change rows fall in it
        0x06D6  525 of this interval's change rows
        1 distinct address(es) in that interval, which is the whole of what moved in it
```

**Every one of those 525 rows is `0x06D6`** — the routine's own counter, the one
`grade_timer_sweep.py` measures the pass period from, and the one §4a's
`0x0480`/`0x05F0` bookkeeping does not run in. So under this reading too the
window is empty of anything but the sweep, and the Fn arm's negative holds
over an interval a reader can name.

Neither reading makes the row wrong, so no correction is recorded beside it.
What was missing was one clause naming the interval, and that is what the two
shared documents now carry.

## What the rule does to this file

`grade_gpu_door.py` **refuses this capture, and the refusal is the correct
one.** Pointed at the file it exits 1 and names the pair:

```
$ python3 ec/tools/grade_gpu_door.py evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
marks 'auto: event7 scan 0xb0' and 'auto: event7 key 184 pressed' are both 2026-09-24T21:21:11.447000+02:00, to the millisecond.
...
$ echo $?
1
```

The collision check (`collided_marks`, `ec/tools/grade_gpu_door.py:186`) runs
after the read and before `build_windows`, so no zero-length window is built
and there is no report over one to be half-right. The damage the refusal
avoids is this grader's own, and its message names it: the first of the pair
would have taken a span of `[t, t)`, no change row at all, and `????` for all
24 of its watched addresses.

**This is the first time that refusal has fired on a committed file.** Before
this it was pinned by a constructed fixture —
`ec/tools/test_grade_gpu_door.py`'s `COLLIDING_MARKS` over a capture written
into a temporary directory, which is the right way to test a shape and is not
the same as a shape that has happened. `ec/tools/test_scan_mark_collisions.py`
now runs the grader as a subprocess over the committed capture and holds the
exit code and the named pair, so "the instance is real" is a fact the suite
re-derives rather than a reading of the tool that found it.

**The rule is not changed by this, and neither grader is touched here.** The
refusal is correct as it stands and demonstrably fires; what the instance adds
is that its premise is now observed rather than constructed.

## What is not affected, and should not be chased

`grade_timer_sweep.py` is untouched by the collision, and the figures §4a and
`docs/findings.md` §17a drew from it are unaffected. `load()`
(`ec/tools/grade_timer_sweep.py:299`) reads only MARK rows whose label contains
`"resumed"` (`:355`); neither colliding label does, so `RESUMES` and `GAPS` come
back empty, and `find_gaps`, `steps` and `per` are all keyed off those lists.
What the sweep reports is computed from `rows`, which no mark touches. In the
block below, `0x8001` is a `bank1` **code** address — the routine's entry,
which the grader names as the pass it measures, and the interval that pass
came at, `median 100.0 ms` (mean 99.71 ms) — and not one of the 35 watched
XDATA bytes, so no capture carries a row for it and none is expected:
```
$ python3 ec/tools/grade_timer_sweep.py evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
span 369.533s, 3789 change rows, sample interval 0.01s, 35 addresses watched
  ...
  period / step = 10.00 (the code predicts 10: nine decrements and one reload)
```

So the 1000 ms decrement interval, the 10.00x post-return ratio, and the 24
decrements landing in the same 10 ms sample as a `0x06D6` reload all stand.
`RESUMES` being empty is why there is no gap to exclude anything across, which
is the one figure a resume mark would have moved. Stated here so a later
reader who finds the pair in the file does not go looking for a broken grader.

## The open question, and what is not taken here

The capture is not rewritten to have one mark. It is a committed input, and a
capture that had lost a row would be a fabricated record of a run that took
two.

The writer is the open question, and it is #1416's: `input_mark_loop`
(`ec/tools/ec_timer_capture.py`) writes one mark per evdev record, and
one keypress arrives as `EV_MSC`/`MSC_SCAN` then `EV_KEY`. Whether to coalesce
them into one mark is a design call about a writer two callers share, it would
change what a future capture looks like, and taking it here would decide
something for every future capture on the strength of one. Named, not taken.

Also not taken, and for the same kind of reason: withholding the window rather
than refusing the run, and the 0751 grader's 5 s fusion. Both are open on
#1416 and neither is this page's business.

**No register status moves with this.** `XDATA_06D8` and `XDATA_070B` went to
`confirmed-working` on the AC-unplug and decrement evidence in
`ed6e5b08`, which this page does not touch and does not re-open. Nothing here
is a live test: no mark was typed, no byte was written, and no register was
read back. The two documents that draw a negative from this capture now say
which interval it was read over, and that is the whole of the change to them.
