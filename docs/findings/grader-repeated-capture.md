# A repeated capture opens phantom windows in the door grader and a ZeroDivisionError in the timer grader, and the rule that closes it is identity rather than a single capture (issue #491)

The write-up for [issue
#491](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/491), which was
opened by the follow-ups pass out of #482. #482 gave
`ec/tools/grade_0751_isolation.py` a `distinct_captures()` and a refusal of a
repeated `--csv`, because one file agreeing with itself satisfies every
cross-console check that grader runs. Two other graders in the same directory
take `nargs="+"` over captures and had none of it, and this is what a repeat
costs each of them.

**Everything below is a command-line and file-identity fact**, reproduced from
committed `.csv` files on disk. No image is opened, no register is read back,
and no EC, laptop or Windows machine is involved. The two graders read files;
neither writes anything, and `0x07D0`/`0x07D1` remain `DO-NOT-WRITE-BLIND`.

## What a repeated capture cost, measured

**`grade_gpu_door.py`, the §5 grader.** Its §5 line passes one capture, and
naming that capture twice is a fat finger:

```console
$ python3 ec/tools/grade_gpu_door.py ec/tools/testdata/gpu-door-example-one-block.csv
=== 2 window(s), one per mark, none merged ===
  0x07C4-0x07D7: 1 of 20 addresses moved

$ python3 ec/tools/grade_gpu_door.py ec/tools/testdata/gpu-door-example-one-block.csv \
                                  ec/tools/testdata/gpu-door-example-one-block.csv
=== 4 window(s), one per mark, none merged ===
  0x07C4-0x07D7: 0 of 20 addresses moved          # window 1
        window delta  0x07C4  ???? -> ????  ...  # all 24 addresses
  0x07C4-0x07D7: 1 of 20 addresses moved, 2 change rows   # window 2
        0x07C4  0x08 -> 0x28   (+0.4s)   DBEN b3, DBST b5
        0x07C4  0x08 -> 0x28   (+0.4s)   DBEN b3, DBST b5   # the same row, twice
  note  marks 'gpu tgp 115W->130W' and 'gpu tgp 115W->130W' are 0.0s apart, ...
```

and it **exited 0**. The damage is four shapes, and each is a way the run reads
as a §3 run that happened:

- **The window count doubles.** Two marks became four windows, so the report's
  `=== N window(s) ===` header and every count read off it are for a run that
  was never performed.
- **Half the windows are empty.** The duplicate marks land at one timestamp, so
  `build_windows` gives each a zero-length span: all 24 addresses print
  `???? -> ????` with "nothing in this block moved". One console typing two
  labels puts two marks seconds apart, so a shared timestamp points at a
  duplicate rather than pacing -- not proof: `_loop` does not refuse a paste.
- **Every change row is counted twice**, which is where the `2 change rows`
  suffix comes from: `report_window` prints the row count when it exceeds the
  distinct-address count, and here one address moved on two rows.
- **The `0.0s` close-marks note is a duplicate read as a judgement.**
  `report_close_marks` (`:290`) does exactly what its docstring says — the
  marks stay two windows, the distance is printed, and the reader is left to
  judge whether two close marks were one action. Here the answer is not the
  operator's to judge; it is a mistyped command line, and the tool presents it
  as a question about pacing.

## Correction: §5's millisecond column does not move

The issue as filed says the `orders` list — §5 column 5, which block moved
first and by how many milliseconds — "is computed over duplicated marks".
**That is structurally true and numerically inert on these fixtures**, and the
distinction changes what the refusal should say. Measured, single against
doubled:

| fixture | single | doubled | moved? |
|---|---|---|---|
| `gpu-door-example-acpi-first.csv` | `by 800 ms`, `by 1300 ms` | `by 800 ms`, `by 1300 ms` | no |
| `gpu-door-example-host-first.csv` | `by 650 ms`, `by 950 ms` | `by 650 ms`, `by 950 ms` | no |
| closing line, both of those | `Both blocks moved in 2 of the windows above` | `Both blocks moved in 2 of the windows above` | no |
| `gpu-door-example-one-block.csv` closing | `No window had both blocks moving (2 of 2 ...)` | `... (2 of 4 ...)` | **yes — the denominator only** |

The reason is `first_change` (`:197`), which takes `min` on the timestamp
rather than `hits[0]`. Rows duplicated at one timestamp collapse, and the
phantom windows contribute no ordering at all. So the ms figure is not what a
repeat breaks, and the one figure that does move is a **denominator counting
windows** — which is the window count again, wearing a different hat.

Both refusals and the grader docstring now say this explicitly. A refusal that
implied the millisecond figure moved would send a reader looking for damage
where there is none, which is the same overclaim the issue made.

## The two graders do not fail alike, and that is load-bearing

`grade_timer_sweep.py:318` was the same `nargs="+"` shape, so the obvious move
was to copy the refusal across. Measured on the clean capture its own suite
constructs (`test_clean_capture_gives_period_ten_and_ratio_ten`), doubled:

```console
$ python3 ec/tools/grade_timer_sweep.py clean.csv clean.csv
  step interval (= one pass of 0x8001): median 0.0 ms, mean 49.49 ms, min 0.0, max 100.0
  WARNING: median step is under 3 sample intervals (10.0 ms); the step is not resolved
  reload period over 9 complete cycles: median 0.0000s, ...
  ZeroDivisionError: float division by zero    # grade_timer_sweep.py:240, pre-change
```

**Not a wrong number, and not a refusal — a traceback**, after a report has
already been half printed. `load()` (`:116`) merges the rows of every path it
is given, so a file listed twice puts two rows at one timestamp, every interval
between two of 0x06D6's own steps becomes 0, the median step collapses to
`0.0 ms`, and `statistics.median(per) / step` at `:255` divides by it. The
door grader degrades quietly; this one crashes. The two refusals therefore
cannot be one message, and each says what a repeat costs *it* — windows and
change rows in one, the period and the division in the other.

## The rule: identity, not a single capture

Both graders now call `grade_0751_isolation.distinct_captures` (`:1671`),
which keys on `os.path.realpath` and returns `(kept, repeats)` with each repeat
as a `(given, first, resolved)` triple. Three reasons, in order of weight:

1. **It is the rule the 0751 grader already ships *and* tests**
   (`test_grade_0751_isolation.py:1118-1163`), so one rule covers the tree
   rather than three graders growing three spellings of "the same file twice".
2. **It is strictly more permissive than refusing a second positional**, so it
   cannot break `grade_timer_sweep.py`'s *documented* contract. Its docstring
   (`:5`) says "one or more CSVs", its usage line (`:55`) is
   `capture.csv [capture2.csv ...]`, and `load()` merges rows from every path.
   Refusing more than one would be a contract change to that tool, not a bug
   fix — two captures either side of a suspend are a legitimate command line,
   and `test_two_distinct_captures_are_still_one_run` holds that they are.
3. **It still catches the filed failure exactly**: the same path twice,
   `./x.csv` beside `x.csv`, or a symlink to either.

`grade_timer_sweep.py` **imports** the helper rather than copying it. It is
stdlib-only, imports no grader, and its module body is constants and
definitions rather than a scan — so the import cannot cycle, and it costs an
offline grader a few milliseconds of interpreter startup, a figure that moves
with the machine and that nothing here rests on. The comment at the import
says so, so a second copy cannot appear by accident later: a copy would be a
third rule, which is the defect this refusal exists to close.

### The alternative reading, recorded rather than buried

**"One positional, full stop" for `grade_gpu_door.py` alone** is defensible on
that tool — its docstring (`:6`) is singular and the procedure runs one watcher
on one console. It is not taken, for one reason: it would require a *different*
rule in `grade_timer_sweep.py`, leaving two graders over one input shape with
two contracts, and the whole point of the identity rule is that there is one.
Stated here so the decision is reversible with evidence rather than
re-litigated — if a third `nargs="+"` capture grader appears with a singular
docstring and no multi-capture use, the wider rule is the one to revisit.

## What did not change

- **`report_close_marks` (`:290-315`) is untouched.** The 5 s note is correct
  behaviour for genuinely close marks, and `test_close_marks_are_flagged_and_never_fused`
  still holds it. The duplicate is caught upstream of it, at the point of error.
- **`build_windows` (`:166`) keeps its own pass.** Issue #169 is open on the
  0751 file, and the docstring already explains why the pass is repeated rather
  than shared.
- **No §5 column moves for a single-capture run.** The change is additive on
  the refusal path only; the existing suite is that pin, and it was run green
  before and after rather than duplicated by a redundant test.
- **`grade_timer_sweep.py:255` is still unguarded.** A capture whose median
  step is 0 reaches that division with no repeat anywhere in sight, so this is
  a separate defect and fixing it here would widen the diff into unrelated
  code. Named below as a follow-up.

## New questions this opens

- **`grade_timer_sweep.py:255` divides by a step that can be zero without any
  repeat** — an unguarded crash reachable on a legitimate capture. The refusal
  closes one route to it, not the route.
- **The rule is shared by import rather than by a module of its own.** That is
  the right shape for two graders and the wrong one for three: a third
  `nargs="+"` capture grader reaching into a fourth file for a seven-line
  helper is a sign the rule wants a small shared module of its own.
