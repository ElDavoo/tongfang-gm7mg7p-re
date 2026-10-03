# One `open()` of a capture in `main`, and a truncated early-exit row (issue #767)

The write-up for [issue
#767](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/767), which
`docs/findings/0751-notice-two-moments.md`'s **What this opens** recorded as
deferred: `main` read the same capture twice, and the per-capture census line
it prints is a composite of the two reads. This takes one `capture_snapshot` per
path and feeds both passes, and — separately — it closes a crash the issue named
in the same breath and described as a row "charged and never re-read."

Nothing here is evidence about the machine. No §3 run was performed, no Windows
box was reached, no EC was opened, no capture was taken and no mark was typed.
The whole of the evidence is offline behaviour of a tool over hand-written rows
in a temporary directory.

---

## Two corrections to the issue's premises

**There were two opens per capture on this tree, not three.** The issue counted
the two readers and stopped there, and its own text ("`:2694` `read_capture`",
"`:2703` `read_early_exits`") is right about that. An earlier draft of the plan
this implements counted three, adding the three-byte `path_starts_with_bom`
probe — but that probe is gone: #786 made `read_capture` a single `open()` of
the buffer it tests the mark against. Measured on this tree before the change,
wrapping `builtins.open` around `main` over a hand-written capture and filtering
to that path:

```
opens of the capture path in main(): 2
```

Two. That is the number the case in
`ec/tools/test_grade_0751_one_capture_read.py` asserts was one before, and the
assertion is what makes the count checkable rather than remembered. The same
"one `open()` is not one reader" distinction #749 was careful about, read in the
other direction: the issue under-counted, and the direction of the error does
not matter to the count.

**`check_capture_claims.py` is not a consumer of the grader's two-tuple.** It
defines a `read_capture` of its own, returning a three-tuple, and imports
nothing from the grader (`grep -c grade_0751` over that file is 0). The issue
lists it beside `grade_gpu_door.py` as a program that unpacks the contract, and
`measure_mark_provenance.py`'s citation for it said "a third" of the two-tuple's
consumers. That was wrong about the file rather than out of date about a line,
so it is corrected in place there. The two-tuple's real holders are
`grade_gpu_door.py` and `windows/tools/manual_fan_ctrl_probe.py`, and
`ec/tools/test_grade_0751_one_capture_read.py` holds the reader to the contract
they rely on.

**The pin `measure_mark_provenance.py` holds over this grader.** That tool
checks its citations against the tree, so an edit to the grader can turn the
tool red without touching it, and this change moved one pin: the citation naming
`existing_mark_provenance`'s mark-row branch.

That pin is one of the ambiguous ones
[0762-provenance-citation-reanchor.md](0762-provenance-citation-reanchor.md)
already lists — its text is carried by `mark_labels_of` as well, and
`resolve` picks the nearer of the two to a number that is only a hint. This
edit moved both branches and the hint not at all, which put the nearer one on
the wrong side: the two citations that between them name the pair both resolved
onto `mark_labels_of`'s line, and `existing_mark_provenance`'s became the one
scanned site no citation named. `measure_mark_provenance.py` and its citation
suite went red on a grader edit that was correct on its own, so a red tool run
is not by itself evidence that the edit was wrong. The citation is retargeted
at its own branch.

## What the two reads were

`main`'s read loop called `read_capture` for the marks and the change rows, then
`read_early_exits` a few lines later for the crash rows, and appended the second
count to a string the first had already been built from — so the line an
operator reads was assembled in two steps, from two opens:

```
...0700-07ff.csv: 6 mark(s), 15 change row(s)                       <- read_capture
...0700-07ff.csv: 6 mark(s), 15 change row(s), 1 early-exit row(s)   <- + read_early_exits
```

**On every capture measured, this change altered no output of the grader's** —
measured: the `multi-block/` fixture with a crash row inserted, run through the
grader before this change and after it, gives byte-identical stdout, stderr and
exit code over the whole report, and the same diff over each committed capture
under `ec/tools/testdata/` is empty. **The one kind of file where the output did
change is one carrying two faults at once**, where `main`'s refusal moved; that
is *The refusal order changed* below, and it is the reason this sentence is
scoped to the captures measured rather than to quiet files in general. The
measurement is not a reason to have left the two reads: they are a defect
whether or not the race lands during a particular run, and the count is what a
test can assert on every run rather than only when the filesystem is unlucky.
But it does bound the claim sharply, and the bound — including where it does not
hold — is stated here rather than left for a reader to infer.

The hazard is one printed line, two `open()` calls on a file §3 runs three
watchers against by design — `CsvSink.row` flushes every row — so the two reads
were microseconds apart or not, and a row landing between them was a row the two
halves of one line disagreed about. #749 had already fixed this for the startup
notice's own read; `main` was the same shape one level down, with the heavier
consequence it predicted: a contradictory notice is a line an operator reads at
the start of a run, a contradictory grade is a block withheld at the end of a
day.

## What it is now

One `capture_snapshot(path)` per path — the read the notice has used since
#749 — and both passes over its one row list: the strict rules through
`skippable_row` and `take_capture_row`, the crash rows through a new
`early_exits_of(rows, path)`. `read_early_exits` keeps its signature and its
body and is now the open plus a delegate, which is the shape
`mark_labels_of` and `partition_capture_rows` already had.

**`read_capture` itself is not called and is not changed.** Its two-tuple is a
contract with two other programs, and taking it over would be a change to a
reader those programs depend on in order to fix a problem in this one. The
strict rules are now spelled in `main` where its own read feeds them, and the
case `test_read_capture_still_returns_the_two_tuple_the_other_tools_unpack`
holds the reader to the contract while
`test_early_exits_of_is_read_early_exits_over_one_row_list` holds the sibling to
the reader's body.

## The refusal order changed, and it changed for the better

`main` now raises the two file-level refusals itself, off the one buffer, rather
than getting them from `read_capture`. **Which refusal names a file carrying
both a byte-order mark and an undecodable byte is unchanged** — the mark is
`bom_refusal`'s one sentence, asked of three bytes without a decode, and
`existing_mark_findings` already puts it first. What did change is the case
where the two faults are a *short row* and an undecodable byte, because
`read_capture` streams the text layer and `TextIOWrapper` decodes 8 KiB at a
time: which of the two it named was a function of how far apart they fell.
Measured before the change, over the same two rows:

| the two rows | `read_capture` refused with | `main` refuses with now |
|---|---|---|
| adjacent | `UnicodeDecodeError` | `UnicodeDecodeError` |
| 400 KB apart | `ValueError: short row` | `UnicodeDecodeError` |

Deterministic rather than buffer-size-dependent: `main` decides the decode
first, on the whole buffer, at every size. That is an improvement and it is
stated rather than glossed, and it is pinned by
`test_a_two_fault_file_is_refused_the_same_way_at_every_size`, which asserts the
new verdict at both sizes and the old size-dependence in the same case — so the
write-up's before-and-after is checkable rather than remembered.

## The truncated trailing row, which was a crash and not only a mischarge

The issue's second item says a truncated `# the run ended early:` row is
"charged and never re-read." That is right for one truncation and wrong for the
others, and the difference is the whole of what was closed here.

`parse_ts` is `datetime.fromisoformat`, which accepts a bare
`YYYY-MM-DDThh:mm:ss` and returns a **naive** datetime. A stamp truncated before
its offset therefore still parses, and `EarlyExit.ts` is then naive while every
window's `ts` carries the offset `manual_fan_ctrl_probe.now()` wrote — so
`charge_early_exits`'s `w.ts <= e.ts` raises. Measured before the change, over a
capture whose last line is the truncated row, run through the committed tool:

| trailing row left on disk | before | now |
|---|---|---|
| `…12:00:57` (cut before the offset) | `TypeError` traceback out of `main`, exit 1 | refused, named |
| `…12:00:57.4` / `.48` / `.480` (cut inside the ms) | `TypeError` traceback | refused, named |
| `…12:00:57.` / `…:57.480+` / `…:57.480+0` (cut so `parse_ts` raises) | refused, named | refused, named |

**No race is needed for any of them.** A watcher killed mid-`flush` leaves
exactly that on disk, and so does a hand-edited row. The two families are not
the same defect: the first crashed the run with a traceback, and the second was
the mischarge the issue describes. The snapshot fix alone does not close either
— it makes the marks and the crash row come from the same bytes, so the charge is
consistent, but the row is still unreadable. The guard is one comparison in
`charge_early_exits` and is a separate hunk from the snapshot, so a reader can
take one and leave the other.

The refusal names the mismatch rather than asserting that nothing raised:

```
2026-01-01 12:00:57  NOT PLACED -- its timestamp 2026-01-01 12:00:57 carries
no UTC offset and the marks in these captures do not agree, so the two cannot
be compared and there is no window for it to have cut short
```

It is checked there rather than in the reader because the two ends are the
question: the row alone is well-formed, and it is only against *these* windows
that it cannot be placed. That is why the sentence names the mismatch and not a
fault of the row.

### What this opens

**A second `TypeError`, at a different site, which this does not close.** The
site is **`coalesce_marks`**, not `charge_early_exits`: `main` reaches
`windows = build_windows(marks, changes)`, `build_windows` calls
`coalesce_marks(marks)`, and `coalesce_marks`'s `sorted(marks, key=lambda w:
w.ts)` raises `TypeError: can't compare offset-naive and offset-aware datetimes`
when the *marks themselves* disagree among themselves about awareness — one
carrying an offset and another not.

`charge_early_exits` does sort its windows by `w.ts` before the loop, and that
`sorted()` would raise the same way. It cannot be the one that raises: it is
downstream of `coalesce_marks`, and a window's `ts` is the `ts` of the first
mark of its group, so any window reaching it came from marks that sort already
compared successfully — which means the windows are uniform in awareness by the
time `charge_early_exits` sees them. Measured on this tree, a capture whose
marks disagree about awareness raises at `coalesce_marks` and not at
`charge_early_exits`, identically before this change and after it: the guard
added here is in the second function, which this sort never reaches.

**It is not narrower than the defect closed here, and that is the part worth
stating.** A killed watcher reproduces this one too. `CsvSink.row`
(`windows/tools/ec_watch.py`) does `writerow` then `flush`, so a kill mid-write
leaves a partial row — the same mechanism, and the same file, as the truncated
early-exit row above. The mark-row analogue is a trailing MARK row whose
timestamp is cut before its offset, e.g. a capture ending
`2026-01-01T12:00:40,MARK,,restored 0x0751=0xA0` after two offset-bearing
marks. Measured, with nothing hand-edited: that raises the identical
`TypeError` out of `main`, before this change and after it. The same truncation
in a trailing *change* row raises the same way one function along, in
`build_windows`' own `sorted(changes, key=lambda c: c.ts)` — so the site is the
first sort in `main`'s path to see a mixed set, whichever of the two row kinds
carries it.

What the writers do is true and is not the point: every writer in this family
stamps with `now()`, so a *complete* row carries an offset and a mixed set does
not arise from ordinary operation. But a truncated row is not a complete row,
and the truncation is what a killed watcher produces.

Left open rather than folded in here: it is at different lines, and the fix is a
decision about what a capture with mixed stamps *is* — a guard on the `key=`, or
a refusal for the whole set — rather than a bug fix of the kind this change
already makes twice.

## What is not claimed

**No block has been shown to have been withheld by the two-read defect, and no
line has been shown to have come out wrong.** The window is microseconds wide,
no case in this repository has been seen to land inside one, §3 normally grades
captures a watcher has finished with, and — measured, as above, over the
captures run — this change altered no output of the grader's at all, the
two-fault file excepted. What is established is the count (two opens where there
is now one), the composite assembly, and the truncation table above. That last
one needs no race at all and is a property of
a static file, and the first two families in it killed the run with a traceback.
That asymmetry is worth stating rather than smoothing over: the defect with the
worse consequence here is the one the issue described least accurately.

**One `open()` is one moment, not a lock.** A row landing after the read is
still graded, by the whole-file grading that `report_census` already tells the
operator about. What the fold removes is the moment *inside* one run, where the
marks and the crash rows could come from different bytes of a moving file.

**It is still not one reader.** `skippable_row`, the four-field test and the
`MARK` branch stay per-reader, deliberately: they are three different contracts
rather than one rule spelled four times, which is #750's argument and is
unchanged here. What the row shape does own — the skip rule and the first field
— is owned once and shared, as before.

**The strict/lenient asymmetry stays.** `read_capture` refuses a short row, a
bad timestamp, non-hex and a mark; the early-exit reader refuses none of them.
That is deliberate and documented, and this change does not touch it. What it
does remove is that `main` ran the two *in sequence over different bytes* and
printed the numbers in that order.

## What a human still has to do, and has not

§3's three watchers against a real `CsvSink`, and a capture truncated by a
killed watcher, are a step at the physical laptop. This repository has no EC, no
Windows box and no laptop. The deliverable here is the offline test over
hand-written rows; the live confirmation is a human's.

---

## Where the rest of it lives

- `ec/tools/grade_0751_isolation.py` — the change, in `early_exits_of`,
  `read_early_exits`, `main`'s read loop and `charge_early_exits`.
- `ec/tools/test_grade_0751_one_capture_read.py` — the cases: the open counted
  once, the census line as one moment, the truncated row refused by name, the
  two-tuple contract, and the refusal order at two sizes.
- `ec/tools/measure_mark_provenance.py` — the citation corrected from "a third"
  to what `check_capture_claims.py` actually is.