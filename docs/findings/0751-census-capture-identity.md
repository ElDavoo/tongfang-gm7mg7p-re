# The census counted a capture one way and its per-action line counted it another, and a list holding one file twice withheld a block on a clean run (issue #492)

The write-up for [issue
#492](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/492), opened by the
follow-ups pass out of #482. #482 gave `ec/tools/grade_0751_isolation.py` a
`distinct_captures()` and a `report_census()` that dedupes its header, its
mark total and its per-capture listing, on the rule that two spellings of one
file is one file. This is the half of that rule the per-action line and the
block-withholding checks were not applying, and it reaches a run that is wrong
about itself rather than a run that merely reads oddly.

**Everything below is a file-identity fact**, reproduced from the committed
`.csv` fixtures in `ec/tools/testdata/` by running the committed code. No
image is opened, no register is read back, and no EC, laptop or Windows machine
is involved. Every figure is a count over those fixtures and is reproducible
from the suite.

## The two symptoms

The census's per-action line built its numerator by keying on `m.source` — the
path **as given**, which is what `read_capture` stores — while its denominator
came from `distinct_captures`, which keys on `os.path.realpath`. One file
handed in under two spellings is one file by the second rule and two by the
first, so the line printed a ratio no reader can act on, over a listing that
named one console:

```console
$ # as_main_reads([QUIET, './' + QUIET]), then grade.report_census(...)
  1 capture(s), 2 mark row(s), 2 action(s) after the merge
  action 1 ...: 'wrote 0x0751=0xA0' in 2 of 1 capture(s):
    0751-isolation-example-quiet.csv             'wrote 0x0751=0xA0'
```

`2 of 1 capture(s)` is the arithmetic of the defect stated in one line. Note
what makes it reachable: the existing regression test
(`test_the_readers_count_a_capture_given_twice_as_one_capture`) hands the list
the **same string** twice. One `m.source` value, one key, however many rows sit
under it — so that test pins the count and cannot reach a keying defect at
all. The two-spellings case is a different input.

## The second half is the one that withholds a block

The census line is wrong about a count. The `check_block_marks` side is wrong
about a *verdict*, and it is reachable in a genuinely two-console run. The
`len(names) > 1` gate does stay off for a single file handed twice once — but a
real two-console run with one file given under a second spelling puts three
`m.source` keys against a two-element `known`, the gate opens, and the
`missing` check fires. Measured on the committed `fixed-load` pair, over the
readers' own results and `main`'s own withheld accounting (a window in a block
holding a problem is withheld, and `withheld` is what the last line of `main`
turns the exit code on):

| list handed to the readers | blocks withheld | windows withheld | exit |
|---|---|---|---|
| `a.csv b.csv` (control) | 0 | 0 of 3 | 0 |
| `a.csv b.csv ./b.csv` | **1** | **3 of 3** | **1** |

and the problem it manufactures names no capture at all:

```text
recorded in 3 of 2 capture(s), absent from .
```

One per window, so the block's three windows are all withheld and the whole
day is reported ungraded. The absent list is empty because it is the *same*
key mismatch filtered through `names`, so the one file that is "missing" is
named as nothing. Both consoles really do record every action, and both really
are absent from nothing.

## The fix: one identity, on both sides of every comparison

`capture_key(path)` is now a function beside `distinct_captures`, and
`distinct_captures` calls it — so there is one spelling of "which file is this"
in the module rather than a rule stated in a comment and re-derived by each
caller that has to agree with it. Every comparison that mixes a window's marks
with the run's capture list resolves **both** sides through it: the two
`known = set(names)` sites, `by_source`, the `labels` arm's lookup, the
`absent` list, `split_mark_gaps` on the way in and out, and the census's `said`
with the per-capture lookup under it.

**Both sides, not just the numerator.** The issue as filed asks for `said` to be
keyed by resolved path, and keying only `said` is not enough. `names` comes from
`distinct_captures`, which keeps the **first spelling as given**, so a
realpath-keyed `said` and a lookup underneath it that still asks for the
spelling in `names` disagree whenever the two are not the same string — which
is exactly what a repeated capture is. Measured on the committed disagreeing
pair with the repeated file handed in first under its second spelling, the
numerator-only fix prints:

```text
action 2 ...: 'wrote 0x0751=0xA0 / wrote 0x0751=0x10' in 2 of 2 capture(s):
  2026-01-01-0751-isolation-0700-07ff.csv      -- did not record it
  2026-01-01-0751-isolation-0400-045f.csv      'wrote 0x0751=0x10'
```

A capture named as not having recorded an action it did record, on the arm
whose entire subject is that the captures disagree. `distinct_captures` keeping
the first spelling is the real and separate fact; the consequence drawn from it
here is only that the two keys have to be built the same way.

The quiet single-capture fixture this section started from **cannot** show
that, and the write-up previously said it could. One capture under two spellings
takes the `one label each` short-circuit on every action, so the lookup below it
is never reached and both argument orders print the same bytes whether or not
the lookup is resolved — a numerator-only fix passes that test unchanged. The
discriminating case is the disagreeing pair above, where the per-action line
takes the other arm and asks `said` for each capture by the spelling `names`
holds; the second new test is that case, and it fails against a numerator-only
fix.

**There are two `known = set(names)` sites**, one in
`unplaced_window_problems` and one in `check_block_marks`, and they look up the
same set of the same run. A first attempt fixed one and broke 56 tests,
because the windows a block walk could not place are held to the same mark set
as the ones it could. This is the single most important thing to hand to
whoever reads the diff: they are one set, and they move together.

The key is for looking up, not for printing. Every site that names a capture
prints `os.path.basename` of a path `distinct_captures` kept, and what that
keeps is the first spelling *as it was handed in* rather than a resolved one,
so every capture in the report is still named the way the operator typed it.

## Deliberately not changed

- **The `len(names) > 1` gate** is correct, and it is what the census's
  one-capture notice mirrors. The issue asks that this comparison "agree with
  the census rather than be reached only when" the gate; read as *agree on
  identity*, that is what this change does. Read as *remove the gate*, it would
  engage the agreement checks on a single capture — a different claim, and one
  that contradicts `test_a_single_capture_says_the_cross_console_checks_did_not_run`.
- **`Block.marks_in` and the `w.source` join.** Both are bookkeeping over one
  spelling of one file. Measured: `marks_in` returns 3 rows for each spelling
  under a repeat, and no figure in the report depends on it. `w.source` prints
  both spellings in a parenthetical, which is accurate rather than wrong.
- **The refusal in `main`.** It refuses a repeated capture before
  `read_capture` runs, so the whole defect is unreachable from a command line:
  `grade_0751_isolation.py a.csv b.csv ./b.csv` exits 1 **on the refusal**, not
  on anything below. That is why this is a defect in the **direct-reader
  path** — the one `as_main_reads` reaches and the test suite uses — and not a
  report an operator has seen. The table above is measured over the readers'
  own results with `main`'s withheld accounting, which is what the refusal sits
  in front of. Making the defect reachable would mean weakening the refusal,
  which is the opposite of the fix. No operator has seen this, and nothing here
  is a claim about the machine.
- **The other graders.** `grade_gpu_door.py` and `grade_timer_sweep.py` import
  `distinct_captures` but group no marks by source, so neither shows the defect.
  Widening the diff into them is not what this issue asks for.

## Tests

Three cases beside the existing identical-string one, in
`ec/tools/test_grade_0751_isolation.py`:

- `test_the_census_counts_two_spellings_of_one_file_as_one_capture` — the
  numerator equals the denominator, the `N capture(s)` header agrees with the
  ratio, and the capture is listed once. **Both argument orders**, because the
  count has to come out the same whichever spelling `distinct_captures` keeps.
  This one does not discriminate a numerator-only fix, and the section above
  says why.
- `test_the_census_names_a_capture_the_way_the_capture_read_itself` — the
  per-capture lookup *under* the short-circuit, on the disagreeing pair with
  the repeated file handed in first under its second spelling. Each capture is
  named with the label it really recorded, and neither is named as not having
  recorded an action both recorded. This is the test that pins the lookup, and
  it fails against a fix that keys `said` without keying the lookup.
- `test_a_repeated_capture_does_not_manufacture_a_missing_mark` — the
  two-console pair with one file repeated: no `missing` problem, no block
  withheld. It asserts the control arm too, so a fix that simply switched the
  check off would fail it: both files really do record every action.

One existing test was updated rather than duplicated.
`test_the_unplaced_window_problems_name_their_kind_per_window` hand-built its
`known` as `set(names)`; it now builds it through `capture_key`, the way both
of the tool's callers do. It passed before and after, and that is the point —
a hand-written `set(names)` is only the same set while the fixture paths hold
no symlink, so it was testing a set the tool never compares against.

The suite is the regression pin, not a redundant copy: every test that
existed before this change stays green with **no fixture edited**, and
`grade_0751_isolation.py --self-test` is what counts them rather than a figure
written here.

## New questions this opens

- **The direct-reader path is now the only place this class of defect can
  live**, because `main` refuses a repeat before any of it runs. That is worth
  knowing when reading the next one: a counting rule the readers hold for
  themselves has no command line to be tested through, and the suite is the
  only thing holding it.
- **`capture_key` is the third caller of a rule that is still stated per
  file.** `docs/findings/grader-repeated-capture.md` already records that a
  third `nargs="+"` grader wanting this helper is the signal it wants a module
  of its own. Two callers inside one file is not that signal yet; naming it
  here so the follow-up pass can pick it up.
