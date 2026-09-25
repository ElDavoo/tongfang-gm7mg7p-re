# What `ec_watch.py --mark` records, and what a blank press no longer records

**A blank line is not a mark.** Since 2026-09-25 (issue #474) the prompt
records nothing for one, prints that it recorded nothing, and asks for the
next line. Before that it substituted `mark N` for the empty label, which
wrote a row no grader of a §3 capture can read — see *Why the substitution
went* below. The rule is pinned in `test_ec_watch.py`'s `BlankMarkTests`, and
this file is the reasoning that does not belong in a runbook paragraph.

Nothing here has been run at a machine. The refusal, the notice and the count
are offline behaviour of the tool, checked against a fake EC; a human running
[the §3 procedure](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md)
is the one who sees the new prompt, and that is their step.

## What a mark is

With `--mark`, each line read from stdin is one mark, and it lands in three
places at once:

- in the capture, as its own row `ts,MARK,,label` (`ts` to the millisecond,
  the label exactly as typed), which is what makes a `--csv` capture
  self-contained rather than a log plus a set of notes;
- on the console, as `--- ts  MARK: label ---`;
- in the end-of-run `marks:` summary, one line per mark the run took.

The label is the operator's own words, and the tool does not read it. The
grader does: `grade_0751_isolation.py`'s `parse_mark` reads the leading word
and the value after `0x0751=`, which is why §3 fixes three forms and why they
are load-bearing rather than illustrative.

**CORRECTION (issue #531, 2026-09-25), leaving the sentence above as it was
written.** *The tool does not read it* was true when this was written, and is
still true whenever `--label-vocab` is absent — which is every caller in this
tree except §3's three commands. With `--label-vocab 0751` the prompt reads
every label against that same `parse_mark` and refuses the ones it cannot place
— see *The refused label* below. Nothing else changes, so the sentence above
still describes what `gpu_block_watch.py` and `system_id_probe.py` get through
their mark prompts, which is the reason the check is a flag and not a rule.
Only `gpu_block_watch.py` shares this class; the other keeps its own.

## The blank press

`ec_watch.py` strips the line. If what is left is empty — an empty line, or
one holding nothing but spaces — the tool writes no row, appends nothing to
its mark list, does not advance the mark number, and says so before reading
again:

```
--- blank line: nothing recorded, no mark 1 taken; type a label + Enter ---
```

The notice is not framed as a mark on purpose. A line that looks like the
`MARK:` frames is the confusion the refusal exists to remove, and the notice
is on the same stream the operator is already reading.

Closed stdin still ends the thread: the EOF check is ahead of the blank check,
so a redirected or closed input stops the marker rather than spinning it on a
line that will never come.

## The refused label

`--label-vocab 0751` is that same refusal one step along, and it is opt-in for
a reason that is not caution: `gpu_block_watch.py:59,166` imports this `Marker`
and stamps free-form labels through it, so a blanket check would refuse labels
that procedure is entitled to write. `system_id_probe.py:232` keeps a class of
its own of the same shape, still carrying the `strip() or` default at `:252`
(#483, #484, named there as still open). So the check is a flag, and §3's
three commands are where the operator turns it on.

With it on, a label `grade_0751_isolation.py`'s own `parse_mark` cannot place is
refused exactly as a blank press is — no row, nothing appended, the counter held
back, the same notice shape:

```
--- unplaceable label: nothing recorded, no mark 1 taken; one of: no-op wrote 0x0751=0xA0 / wrote 0x0751=0x10 / restored 0x0751=0xA0; type a label + Enter ---
```

Both halves of that are the grader's rather than a copy of it. The predicate is
`parse_mark(label)[0] is not None` — the test `unplaceable_marks` applies to
decide a mark is unreadable — and the three forms are that module's own
`REQUIRED_LABEL_FORMS`, loaded from it by path. A copy could drift from the
grader, and a prompt that has drifted promises something the grading does not
do. What is left is the operator correcting the label while the run is still
going, instead of finding out at the grading that a day is withheld.

**What it does not catch is as much of the point as what it does.** `parse_mark`
reads the leading word and the value after `0x0751=`, and it knows nothing about
which values this run means to write or what its sequence of actions should be.
So:

- `wrote 0x0751=0xB0` parses, and is recorded — the prompt cannot know that §3's
  three values are `0xA0`/`0x00`/`0x10`;
- `WROTE 0x0751=0xA0` parses, because `parse_mark` is case-insensitive, and is
  written verbatim, which is as it should be;
- a dropped hex *digit* parses too: `0x0751=0xA` is a value of its own. A
  dropped `0x` from the address is caught; a dropped digit is not;
- a wrong *sequence* — two writes in a row, a restore with no block open — is
  not a per-line question at all. Those still reach `build_windows` and
  `check_block_marks` at grading time.

The promise is exactly *the grader can place this row*, and the mistyped digit
that survives is what §3's three-console comparison is for.

A grader that will not load is a refusal rather than a fallback, printed before
the CSV is opened and long before the EC is:
`error: --label-vocab 0751 needs ec/tools/grade_0751_isolation.py at <path>`.
A capture taken under a promise the tool silently did not keep is #502's
failure caught a step later rather than a step earlier, and an operator told a
label was refused by a check that was never there has been told something
false.

## Why the substitution went

It was `label = label.strip() or f"mark {self._n}"` — a default that made
three wrong things true at once.

**A missing mark read as a deliberate one.** `mark 3` is a label, so at the
console and in the capture it is indistinguishable from a label somebody
typed on purpose. The operator's actual mistake — a press of Enter instead of
a word — left no trace anywhere, which is the one thing a mark is for.

**It wrote a label no form can parse.** `grade_0751_isolation.py`'s
`parse_mark` returns `(None, None)` for it, and `unplaceable_marks` treats one
such mark as fatal for **the whole run** rather than for one block, because
block attribution rests entirely on the labels: a mark the grader cannot read
leaves every block's completeness uncertifiable, not only the one it would
have landed in. `--block` scoping narrows what is graded, not what is known.
The day's windows are withheld and the grader exits 1.

**The grader cannot recover a mark that was never described.** This is the
part that decides it. A lenient parse or a "best effort" flag would make a
mark the operator never typed grade as though they had, and the whole §3
comparison rests on the labels meaning what they say. The right place to stop
an undescribed mark is where it would have been invented.

## What a capture with one action missing looks like now

The refusal is honest rather than clever: it does not invent a mark, and it
does not know what the press was meant to be. So a capture whose operator
simply did not type a label is a capture with that action's mark absent, and
`build_windows` opens each window on a mark and closes it on the next one.
Two actions and one mark is **one window holding both actions' changes**, not
two windows — the bytes really did move between the marks that exist, and the
timestamps are perfectly happy. Nothing in the capture says a mark is
missing; the window is simply longer, and the three-console merge opens it on
the two labels joined with ` / ` where
[§3](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md) says it will
when a digit is mistyped in one console.

That is the honest consequence, and it is the reason to type the label rather
than press Enter.

## The counting rule

The mark counter counts **marks recorded**, not lines read. A refused press
does not advance it, which is what lets the notice name the number the press
would have taken: a blank at the start says `no mark 1 taken`, and the label
typed next is the capture's first mark. So the number in a notice is always
the number the operator's next accepted mark will carry, and a run where three
presses are refused still reads 1, 2, 3 at the console. A label `--label-vocab`
refuses is held back by the same rule and for the same reason, which is why the
two notices read alike: the counter is on marks recorded, and neither press
recorded one. Nothing else in the output numbers the marks — the grader reads
labels, not numbers — so this is about the console being readable rather than
about the capture.

## Where the refusal shows up

- [manual-fan-ctrl-0751-isolation.md](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md)
  §3 is where the operator is told what to type, and its "three forms are
  load-bearing" paragraph carries the dated correction: a blank press is no
  longer one way to produce an unplaceable mark, and the mistyped digit that
  survives is what the three-console comparison is for. Its three commands also
  carry `--label-vocab 0751`, which is where the operator turns the second
  refusal on.
- `windows/tools/ec_watch.py` — `load_label_vocab` and the `check`/`forms`
  keyword parameters on `Marker`. The parameters default to no check because
  `windows/tools/gpu_block_watch.py:166` constructs `Marker(sink)` and stamps
  free-form labels, so a default that checked anything would refuse that
  procedure's own marks.
- `windows/tools/test_ec_watch.py`'s `RefusedLabelTests`, beside
  `BlankMarkTests`. It pins the refusal, the notice, the counter, and the
  default: with the flag absent an unplaceable label is recorded unchanged,
  which is what those two other tools depend on.
- `ec/tools/grade_0751_isolation.py` — `parse_mark`, `unplaceable_marks` and
  `build_windows` are the three functions above. None of them changed: the
  grader's refusal was correct and still is.
- `ec/tools/test_grade_0751_isolation.py` — its `mark 3` case is a
  hand-written fixture of the shape, and it still exits 1, because a capture
  carrying that row is still fatal however it got there.
- `docs/findings.md` §16a is the one-paragraph version of this file.

## The same substitution, in two other tools

Neither was changed here: `system_id_probe.py` has its own suite and its own
runbook, and `ec_timer_capture.py`'s marks are read by the timer-sweep grader
under a different label convention. Both write the same `ts,MARK,,mark N` row
for a blank press, and both are follow-ups.

- `windows/tools/system_id_probe.py:252` — the same
  `label = label.strip() or f"mark {self._n}"`, in a `Marker._loop` of the
  same shape. Its mark rows are the shape the 0751 grader reads, so a mark
  captured with that tool and graded with this one fails the same way.
- `ec/tools/ec_timer_capture.py:162` — `mark_loop`, the same `strip() or`
  default over a plain `for line in sys.stdin`. `grade_timer_sweep.py` reads a
  `resumed` label rather than §3's three forms, so the consequence there is a
  misleading row rather than a withheld run — a smaller cost, not a smaller
  bug.
