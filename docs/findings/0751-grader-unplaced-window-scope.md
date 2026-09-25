# The sentence §7's verdict is read from did not say which windows are a window of a value under test (issue #530)

The write-up for [issue
#530](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/530), which is
about `ec/tools/grade_0751_isolation.py`'s closing summary making a
capture-level claim over a set of graded windows that includes windows which
belong to no block at all. It is a disclosure change: **no byte is read
differently, no window is graded or withheld differently, and the exit code is
unchanged** on every fixture that was 0 before and every fixture that was 1
before. Nothing here is a register behaviour and nothing here is evidence about
the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the command the
operator runs, one invocation per value, and §7 is where the call is made.

This is the fourth sentence in the same paragraph, after
[`0751-grader-partial-grade-claims.md`](0751-grader-partial-grade-claims.md)
(#477), [`0751-grader-block-scope-claims.md`](0751-grader-block-scope-claims.md)
(#497) and [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md) (#498,
landed as #502). The fourth change in that family is
[`0751-grader-unplaced-window-checks.md`](0751-grader-unplaced-window-checks.md)
(#529), and it is not one of these: it makes the agreement checks *refuse* a
window in no block, where all three of the above change what a run says about a
window it read. It is the reason the two strays `unplaced-window/` carries reach
the branch below at all, and the two compose rather than overlap.

---

## The defect, on a committed fixture with nothing edited

`ec/tools/testdata/0751-isolation-run-unplaced-window/` is §6's two-value day
with two `restored 0x0751=0x99` marks in no block — one ahead of both blocks
and one between them. Both labels parse, so both windows are read and graded;
`0x99` is no block's value, so neither window is a window of any value under
test. The run therefore reports **8 marks, 0 withheld, 8 graded, 2 of them in
no block**, both blocks `intact`, and exit 0.

`shown` is `range(len(windows))` when nothing is selected, so both strays are in
it. `report_window` prints each with `block: unplaced`, its rows feed
`moved_groups`, and the no-movement chain's final `else` — the bare
`consistent with the static prediction` — fired.

    python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-unplaced-window/*.csv

printed, before this change. "Before" is the tool at `565b6f3c`, this branch's
merge base with `main`, and "after" is the file on this branch, so the
transcripts name the revision each was recorded against rather than leaving the
reader to assume the one checked out — the "before" lines are the output of
`git show 565b6f3c:ec/tools/grade_0751_isolation.py` on the same command:

```
=== what this does and does not settle ===
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static prediction, for this capture's window only (§5: a byte that does not move inside the window may still move at the next suspend, AC transition or EC reset).
```

and prints, after it:

```
=== what this does and does not settle ===
  2 of the 8 graded window(s) above are in no block: a window is a window of a value under test only by the mark that opened it, so these rows are real and the arm they belong to is unknown, and the static prediction is a claim about the whole capture. The census above names each of these by timestamp and label, in no block and so beyond what `--block` can select.
  None of the §4.1-§4.3 bytes moved in any of the 6 window(s) that belong to a value under test: that is what those 6 windows show, and the 2 graded window(s) in no block above are not part of it. The static prediction is a claim about the whole capture, and this output does not make it over a run in which 2 of its 8 graded window(s) are in no block. §7's `confirmed-inert` needs all three values, and a window in no block is one this run read and cannot say is a window of any of them -- so the paragraph below is as far as this run goes.
```

**The exit code did not change; what changed is that there is now a sentence to
read.** Before, a reader saw `intact` twice, eight graded windows of which two
carried `block: unplaced`, exit 0, and the strongest claim the tool makes — one
about the whole capture.

The issue offers "a scope line, **or** a count of the graded windows that are
in no block". A count printed *beside* an otherwise unqualified sentence would
leave the overclaim standing: the reader would still get "in any window:
consistent with the static prediction" with a fact about attribution in the
margin. So the reading taken is the scoping one, and the count is part of it —
a count line in the closing section whenever the count is non-zero, **and** a
scoping sentence on every path that can print one: a new branch in the
no-movement chain, so the bare `else` is reached only when every graded window
*is* a window of a value under test, and a narrowed form of the withheld
branch's sentence, so a run that both withheld a window and read an
unattributed one does not claim over both. The count carries none of the scope
itself; it cannot, because it is printed above a chain whose next sentence is
not known until the branch is taken.

## Why a graded window in no block is not a lesser problem than a refused one

The withheld branches scope by what the run could not read. Nothing here was
unreadable, so those branches do not fire — which is what made this quiet. But
attribution does not come from the rows: a window is a window of a value under
test **only by the mark that opened it**, and a mark in no block names a value
no block under test wrote. The rows are real arithmetic; the *arm* is unknown.
That is the same reasoning `INTACT_BLOCK_NOTE` and `MARK_SET_NOTE` are already
written on, and it is why the new prose states a fact about the capture rather
than a verdict about the machine.

The new branch does **not** reuse the withheld branch's "a run it only read
part of" clause, because that would be *inaccurate*: this run read every window
it was shown. What it cannot do is say what an unattributed window is a window
of, and the sentence says that narrower thing and declines over the rest. Where
a run *did* withhold a window the clause stays, because it is true there, and
the unattributed windows are added as a second and separate reason beside the
withheld ones — two reasons, one sentence, neither borrowed from the other.

## The count, and why it is taken where the window is printed

`graded_unplaced` is incremented inside the `for i in shown:` loop
(`ec/tools/grade_0751_isolation.py:1967`), at the same point `moved_groups` is
filled — only on a window that actually reached `report_window`, and only when
`w.block is None`. **This placement is the whole of the no-double-count
requirement and is not moved up to a `shown`-wide comprehension.** A window can
be both in no block and withheld: the 12:00 stray in `unread-window/` is exactly
that, and the withheld banner already names it. Counting at the print point
makes the two figures disjoint *by construction*, so the banner's `1 of the 8`
and the note's `1 of the 7` cannot be one window counted twice, and the
denominators differ the way the existing `graded = len(shown) - withheld` figure
does.

## How the branches compose

The count line is printed beside `UNREAD_MARK_NOTE` and **before** the
`moved_groups` branch rather than inside any one arm, so it is silent when the
count is zero. That is what keeps it from *adding* anything to a branch — but it
is not the same as the branches being unable to disagree with it, and the
difference is this PR's one substantive change. `elif withheld:` is reached by
the same code with the same text when the count is zero, and takes a narrowed
form when it is not: the two now agree about the claim's denominator instead of
one contradicting the other, which is the whole point. A run that both selected
a block and withheld part of it is scoped by the more specific of the two, as
the comment inside the `moved_groups` branch already argues at `:2024-2027`,
and that argument is unaffected.

The new branch sits **after** `elif withheld:` and **before** the `selected`
case, and cannot compete with the selected case on any input: a `--block` run's
`shown` is `[i for i, w in enumerate(windows) if w.block is selected]`, and
`w.block is None` cannot be in it. The count is structurally 0 there rather than
guarded to be, which is the stronger of the two answers — a guard is a claim
about the current shape of `shown`, and the shape is the reason. The same shape
is why the withheld branch's narrowing cannot fire on a `--block` run either, so
a run that both selected a block and read an unattributed window is not a
combination that exists.

Measured over the pair: `unplaced-window/*.csv --block 0xA0` still exits 0, still
prints the per-block sentence from `:2202`, and prints neither the count line
nor `UNREAD_MARK_NOTE`.

## The other half, on the fixture that has both

`ec/tools/testdata/0751-isolation-run-unread-window/` is `unplaced-window/`
with the 12:00 stray's label changed to `'restored it somehow'`, a form §6 does
not fix. The 12:00 window is then refused and the 12:04 one is still read, so
the run reports **8 marks, 1 withheld, 7 graded, 1 of those 7 in no block**,
exit 1. It already printed the withheld banner, `UNREAD_MARK_NOTE` and the
withheld branch's scoped sentence — and counted neither stray. It now prints
between the note and the movement sentence:

    1 of the 7 graded window(s) above are in no block: a window is a window of a value under test only by the mark that opened it, so these rows are real and the arm they belong to is unknown, and the static prediction is a claim about the whole capture. The census above names each of these by timestamp and label, in no block and so beyond what `--block` can select.

and the withheld branch's own sentence underneath it now reads:

    None of the §4.1-§4.3 bytes moved in any of the 6 window(s) that were graded and belong to a value under test: that is what those 6 windows show, and neither the 1 window(s) withheld above nor the 1 graded window(s) in no block are part of it. The static prediction is a claim about the whole capture, and this output does not make it over a run it only read part of -- a run in which every window was graded, and every one of them a window of a value under test, is what would. §7's `confirmed-inert` needs all three values, and a window in no block, or one this report refused to read, is one this run cannot speak for -- whether the refused one sits in a block of its own is not something this output can say -- so the paragraph below is as far as this run goes.

## Why the count is bare, and why the withheld branch narrows too

An earlier draft of this PR put the scope on the *count* — "the claim below is
therefore over the other 6 window(s) rather than over the day" — and left the
withheld branch alone. On `unread-window/` that printed a count disclaiming one
window and, one line below it, a sentence claiming over **all 7**: the
disclosure contradicted the claim it was annotating, and the run still made its
movement claim over a window in no block. This is the defect the issue names
("the sentence still says 'in any of the 7 window(s) that were graded' when 1
of those 7 is in no block"), so it is fixed at both ends rather than one.

**The note states the count and stops.** It is printed above the whole
`moved_groups` / `withheld` / `graded_unplaced` chain, and which sentence
follows it is not its to decide: the movement line, the withheld branch and the
no-block branch carry three different denominators, and the movement line
carries none at all. A scope sentence there is true of exactly one of them.
Each branch that owns a scoping sentence now states the scope, so a reader never
takes a claim's denominator from a line that does not carry one.

**The withheld branch narrows when `graded_unplaced > 0`.** A window this run
*read* is not thereby a window of a value under test, which is the same
attribution argument the new branch is written on and the same one the count
line is making directly above it. The movement goes over the `graded -
graded_unplaced` windows that are a window of a value under test, and *both*
kinds of excluded window — the withheld ones and the unattributed graded ones —
are named as outside it. The branch keeps its refusal-based wording and its own
§7 clause: `unread-window/` withheld a window whether or not it also read an
unattributed one, and the new sentence says both, because both are true. The
"whether it sits in a block of its own" caveat moves to "whether **the refused
one** sits in a block of its own", because that is the window whose block this
output cannot name — and is not a question a window in no block raises.

The scope is unchanged on every run with `graded_unplaced == 0`: the
`withheld:` sentence is reached by the same code with the same text, and the
40-pair measurement below is what shows it.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, 72 tests on `main` and 74 after, all
passing under `python3 ec/tools/test_grade_0751_isolation.py` (the two
difference are this one; the count is the merged tree's, `main` plus these
three):

*(**Correction, 2026-09-25, issue
[#726](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/726).** The two
figures are not wrong, and were not wrong when written: 72 + 2 = 74 is this
change's two new methods, and 72 is what `main` held when this branch cut. Three
things are. **The parenthetical reads as a delta of three** — "the count is the
merged tree's, `main` plus these three" cannot be reconciled with 74, and the
delta is two added methods plus one *updated* test, which is what the third row
of the table below says in its own words ("unchanged in what it is for, updated
for the narrowing"). **The section is headed "What is pinned" and read as
current while it was 19 merges stale:** on the tree this file now sits in the
suite runs **93**. And **the two figures are each right against a different
revision, which the sentence does not name** — see the `565b6f3c` note below.
The wrong reading is left above rather than edited out.)*

The count is `python3 -m unittest test_grade_0751_isolation` from `ec/tools`,
the form the neighbouring write-ups use
([`0751-grader-unplaced-window-checks.md`](0751-grader-unplaced-window-checks.md):198-199,
[`0751-stage-mark-labels.md`](0751-stage-mark-labels.md):247,
[`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md):207-208). The
`python3 ec/tools/test_grade_0751_isolation.py` spelling this section used works
equally well and is **not** what is being corrected: the suite locates its
fixtures off `Path(__file__).parent` at
`ec/tools/test_grade_0751_isolation.py:16`, so the working directory does not
matter either way.

Re-derived rather than restated, one count per commit that touches the suite
plus the two commits between them that did not move it, each row self-labelling
(`grep -c "    def test_"` at each revision, which agrees with the run at the
tip). Every step is attributed to a commit, so **no step is a residual**:

| revision | count | step | what it is |
|---|---|---|---|
| `565b6f3c` | 69 | | #498 as #502 — the revision the "before" transcript at :46-50 is taken from |
| `004ad3d7` | 72 | +3 | #529 as #537 — the last suite change before this one, and so `main` when this branch cut |
| `b3f30987` | 74 | +2 | #530 as #533, this change |
| `7a26a932` | 76 | +2 | #532 as #538 |
| `619afcb2` | 82 | +6 | #472 as #638, [`0751-stage-mark-labels.md`](0751-stage-mark-labels.md):246 |
| `3f713159` | 82 | — | #500 as #657, assertions added inside an existing method |
| `f0f3b251` | 88 | +6 | #664 as #674, [`0751-early-exit-row.md`](0751-early-exit-row.md):230 |
| `0a1fef97` | 88 | — | #549 as #710, `test_ec_watch.py` only |
| `1e0bc0f2` | **93** | +5 | #548 as #712, [`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md):210 |
| `061b2213` | 93 | — | #707 as #723, the tip; touches no 0751 test file |

The 74 to 93 is +19, and it is +2 (→76) +6 (→82) +6 (→88) +5 (→93) with the two
zero steps contributing nothing. The +6 at `619afcb2` is seven methods added and
one renamed: `test_a_mark_that_is_not_one_of_the_three_forms_is_an_error` became
`test_a_mark_that_is_not_one_of_the_forms_is_an_error`, because #472 extended
§3's forms from three to six. That rename is the subject of its own correction
further down this file.

**On which `main` the 72 is counted against.** `565b6f3c` is named at :46 as
this branch's merge base, and it is the right revision for the *tool* transcript
above — but it is an **ancestor** of this change whose suite has **69**, not 72,
because #529 landed between them and added the three cases
[`0751-grader-unplaced-window-checks.md`](0751-grader-unplaced-window-checks.md):197
records. The count is about the suite, and #529 is the last thing that moved it
before this branch, so 72 is the right figure for the count and `565b6f3c` the
right one for the transcript. The ambiguity is the section using one revision
word for both, not either number.

At the tip, 2026-09-25:

    $ cd ec/tools && python3 -m unittest test_grade_0751_isolation
    .............................................................................................
    ----------------------------------------------------------------------
    Ran 93 tests in 0.197s

    OK

    $ grep -c "    def test_" ec/tools/test_grade_0751_isolation.py
    93

The two agreeing is the point: a suite whose static method count and whose run
count disagree would mean the figure is not what it claims. The 0.197 s is one
runner's figure, recorded for the reason
[`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md):80-95 records
its own.

**Two figures in the files this section cites do not survive the same
measurement.** Neither file is this change's and neither is edited here; both are
recorded so the chain above is not read as agreeing with them.

- [`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md):210 puts the
  grader suite at "88 to 92". The commit it describes, `1e0bc0f2`, takes it
  **88 to 93** — five methods, of which that table names four;
  `test_a_byte_the_encoding_cannot_read_does_not_stop_the_preflight` is the one
  it does not. The same sentence's `test_ec_watch.py` "21 tests to 29" has both
  endpoints 10 low for the same reason: #549's ten grader-lookup cases (five of
  them named `test_a_grader_*`) landed in between at `0a1fef97`, so that file's
  step is 31 to 39, not 21 to 29.
- [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):165 and :189
  cite `test_a_mark_that_is_not_one_of_the_three_forms_is_an_error` by its
  pre-#472 name. That is #498's file, so the same correction is not applied
  here.

| test | what it holds |
|---|---|
| `test_a_graded_window_in_no_block_is_scoped_where_the_prediction_is_read_from` | `unplaced-window/` unscoped: rc 0; the count over the graded denominator; **the note ending at the count, with `The claim below is therefore over the other` and `rather than over the day` asserted absent**, so the count cannot grow a cross-reference to a sentence it does not own; the movement over the 6 that belong to a value under test with the other 2 named as outside it; the capture-level comparison declined for the count's reason and *not* the withheld branch's; neither refusal shape reached; `block 1/2: intact`, `block 2/2: intact` and both `` `--block` cannot select it `` census lines still printed, so a note that quietly changed a block verdict fails a test that only reads prose. Second half: `unplaced-window/ --block 0xA0` still exits 0, still gets the per-block sentence, and prints neither the count nor `UNREAD_MARK_NOTE` |
| `test_an_unreadable_mark_does_not_count_twice_in_the_graded_unplaced_line` | `unread-window/` unscoped: the banner's `1 of the 8` and the count's `1 of the 7` over **different denominators**; `UNREAD_MARK_NOTE` still printed; **the withheld branch's sentence over the 6 that are a window of a value under test, naming both the 1 withheld and the 1 in no block as outside it, and `in any of the 7 window(s)` asserted absent** — the pairing the count cannot leave alone; and `block: unplaced -- NOT GRADED` exactly once against `block: unplaced` twice, so the 12:00 window is named as refused once and only once |
| `test_a_withheld_window_in_no_block_claims_no_block_was_refused` | `unread-window/` unscoped, and the test that held this branch's §7 clause from #498: unchanged in what it is for, updated for the narrowing. It no longer pins a movement claim over 7 graded windows; it pins the 6, both excluded windows, the §7 clause naming the window in no block *and* the refused one, and the "sits in a block of its own" caveat on the refused window specifically. It still asserts that no block is claimed to have been refused, which is the §7 fact the branch exists for |

All three rows above were checked against the suite as it stands, not taken on
trust: each method is present, and each row's prose still matches what the method
asserts. `test_a_graded_window_in_no_block_…` is at
`ec/tools/test_grade_0751_isolation.py:1862` and still asserts rc 0, the count
over the graded denominator, both scope phrases absent, the movement over the 6,
the count's reason for declining, neither refusal shape, both `intact` lines and
both `` `--block` cannot select it `` census lines — then the `--block 0xA0`
second half. `test_an_unreadable_mark_…` is at :1937 and still asserts the
banner's `1 of the 8` and the count's `1 of the 7`, `UNREAD_MARK_NOTE`, the
narrowed sentence over the 6 with both exclusions named, `in any of the 7
window(s)` absent, and `block: unplaced -- NOT GRADED` exactly once against
`block: unplaced` twice. `test_a_withheld_window_in_no_block_…` is at :1804 and
still asserts what row three says it asserts. **No test named in this section
has vanished.** The one name in this file that has not survived is the
`test_a_mark_that_is_not_one_of_the_three_forms_is_an_error` at "What must not
change" below, which was renamed rather than removed.

The second test is pinned on the *lesser* fixture deliberately. On
`unplaced-window/` the two denominators coincide (8 shown, 8 graded), so a
count taken over `shown` would print the same `2 of the 8` and the cleaner
fixture could not tell the two placements apart. `unread-window/` is the only
committed fixture where they differ, and a count of the wrong set prints
`2 of the 8` there.

**That claim was re-checked here, in its own right, and not inherited.**
[#720](https://github.com/ElDavoo/tongfang-gm7mg7p-re/pull/720)'s body re-ran
the two unscoped fixtures and the `--block 0xA0` run, and this claim is
downstream of all three, so a reader should not have to assume that re-run
covered it. Run again over the committed CSVs on 2026-09-25:

    $ python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-unplaced-window/*.csv   # exit 0
      === 8 window(s), one per mark ===
      2 of the 8 graded window(s) above are in no block: ...
      None of the §4.1-§4.3 bytes moved in any of the 6 window(s) that belong to a value under test: ...

    $ python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-unread-window/*.csv     # exit 1
      === 8 window(s), one per mark ===
      1 of the 8 window(s) above were not graded: ...          <- the withheld banner
      1 of the 7 graded window(s) above are in no block: ...    <- the count line

    $ python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-unplaced-window/*.csv --block 0xA0   # exit 0
      None of the §4.1-§4.3 bytes moved in any of the 3 window(s) in block 1 of 2, value under test 0xA0: ...
      (no `graded window(s) above are in no block` line)

The paragraph holds as written. On `unplaced-window/` there is no withheld
banner at all and both denominators read 8; only `unread-window/` separates
`1 of the 8` from `1 of the 7`, over 8 shown and 7 graded. The `--block 0xA0`
half of row one holds too — exit 0, the per-block sentence, and neither the
count line nor `UNREAD_MARK_NOTE`.

It is also the only committed fixture where `withheld > 0` and
`graded_unplaced > 0` together, which is why two tests reach the narrowed
withheld branch and not one: `test_an_unreadable_mark…` pins the count beside
the claim it disclaims, and `test_a_withheld_window_in_no_block…` pins the
claim itself. A change that narrowed the count's scope but not the branch's
sentence would pass the first and fail the second.

That "only committed fixture" was re-checked the same way, over every
`0751-isolation-run-*/` directory rather than the three runs above, and it still
holds. Nine of them print a withheld banner or the count line; `unread-window/`
is the only one that prints both, and the census over all eleven committed
`0751-isolation-run-*/` directories changes neither half of the claim. Only
`staged/` has landed since this write-up was written (`b3f30987`, the commit
that added it); the other ten were already in the tree then, which
`git ls-tree --name-only b3f30987:ec/tools/testdata/` shows.

All three fail against the unfixed tool, and for the reasons they are here:
the first on the count and the absence of `consistent with the static
prediction`; the second because the count line does not exist; and the #498
test because the withheld branch claims over 7 graded windows where the tool
now claims over 6. That last one is the check that this fix is pinned rather
than only described — a change that narrowed the count's scope but left the
sentence underneath it alone would pass the first two and fail it.

**One test from #529 changed with it, and that is the only edit outside the
three above.** `test_a_window_in_no_block_whose_marks_agree_is_not_refused`
runs `unplaced-window/` unscoped and pinned the bare whole-capture sentence
there as the one a fully-graded run reaches — which is the sentence this change
removes from that exact fixture, because "every window graded" is not "every
graded window a window of a value under test" and the two strays are not one.
Its refusals are untouched and are what it is for: `NOT GRADED` and `were not
graded` still asserted absent, the window list, the two `block: unplaced`
headers, both blocks `intact`. Only the closing sentence moved, to #530's
narrowed one, and the comment above it says which change moved it and why. Its
second half asserted `7 window(s) that were graded` on `unread-window/`; that
figure is still the run's, and it is now read from the count line rather than
from the sentence under it, which states the movement over the 6 of the 7. Both
edits move a test *toward* what this change claims, and neither removes a
refusal assertion.

## What must not change, and did not

Measured rather than asserted, and re-measured after the merge so the pair is
the one a reader can reproduce on the tree this lands in: `origin/main`'s copy of
the tool and this one were run over every
`ec/tools/testdata/0751-isolation-run-*/` directory four ways — unscoped, and
`--block` at each of `0xA0`, `0x10` and `0x00` — and all 40 pairs of reports
were diffed. **Two changed, and they are the two invocations the issue is
about:** the unscoped `unplaced-window/` run (one line added, the bare `else`
sentence replaced by the new branch's) and the unscoped `unread-window/` run
(one line added, the withheld sentence replaced by the narrowed one). **No exit
code moved, and the other 38 reports are byte-identical** — which is also what
shows the withheld branch's `graded_unplaced == 0` text is untouched, since
`3blocks/` and `3blocks-moved/` are the fixtures that reach it.

The census is untouched, so its `unplaced:` lines are exactly where they were;
the note points at them rather than restating them. The new note deliberately
does not contain the literal string `block: unplaced`, which is the coupling
`test_a_mark_that_is_not_one_of_the_three_forms_is_an_error` already relies on
(#498) — it still passes unedited.

*(**Correction, 2026-09-25, issue
[#726](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/726).** The
coupling holds and the case still passes, but "unedited" no longer describes the
method: #472 renamed it, in `619afcb2`, to
`test_a_mark_that_is_not_one_of_the_forms_is_an_error` — the "three" is gone
because §3's forms went from three to six, and the case now quotes all six
rather than three. It is at `ec/tools/test_grade_0751_isolation.py:2594` under
the new name and is in the 93 above. The pre-rename spelling is left in the
paragraph above so the reference is still findable.
[`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):165 and :189
carry the same old spelling; that is #498's file and is not corrected here.)*

## Left out on purpose

- **The `moved_groups` half of the branch chain.** When `graded_unplaced > 0`
  and something moved, the count line fires directly above the movement line, so
  the reader sees the attribution gap immediately before the claim — but the
  movement sentence is not re-worded. That scoping is #477's, it is already
  correct for the cases it covers, and rewording it would touch sentences three
  other issues' tests pin. **What is left open on that path, stated rather than
  hidden:** the movement line itself names no denominator, so with the count now
  bare there is nothing above it contradicting anything, and the one line in
  that half that *does* carry a denominator — "That is the N window(s) that were
  graded", under a run that also withheld — would name a set that includes an
  unattributed window if a run ever reached it. No committed fixture does:
  `3blocks-moved/` is the only one that both moves and withholds and it has no
  unattributed graded window, so a change there would be untested prose. It is
  left for a fixture that reaches it rather than written blind. **The fixture
  that reaches it is issue #725**, and it is the other side of this bullet
  rather than this bullet's own line: `withheld == 0`, `moved_groups` non-empty,
  `graded_unplaced > 0`. #725 takes reading (a), the branch scoped, over
  reading (b), the bare form, for the reason this bullet named higher up and
  which is restated here in full: the sentence directly under the movement
  line is a whole-capture claim, and the
  count two lines above it has just said 2 of the run's 8 graded windows are
  attributable to no value under test. It cannot reuse this bullet's withheld
  wording, because `moved_groups` carries no window identity — the same row
  moved into an unattributed window rather than a block's own leaves the output
  byte-identical — so it declines in the no-movement arm's words instead. **The
  withheld half of the line named here is
  [#724](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/724)'s** and is
  deliberately untouched. See
  [`0751-grader-moved-unplaced-scope.md`](0751-grader-moved-unplaced-scope.md).
- **A new `testdata/` fixture.** Both cases are committed, and widening the
  shared fixture tree is what the other three write-ups in this family decline.
- **`ec/README.md`.** Its `grade_0751_isolation.py` entry describes `--block`
  scoping and the dump groups; it does not enumerate the closing section's
  cases, so nothing there goes stale. Leaving it alone is also one fewer shared
  file open against the other agent PRs.
- **`ec/annotations/registers.yaml`.** This is not a register-status change.
  `MANUAL_FAN_CTRL` stays `present-untested` and its `static_refs*` counts stay
  29/29/0. **There is no row edit to look for** — none was missed.
- **`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`.** §6/§7 are the
  procedure, not this tool's report. #506 (no command line in §6 for the
  unscoped run) stays open and is not duplicated here.
- **#500, #506, #495, #515.** Named by the issue as staying open; none is
  fixed, duplicated or closed here.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/` and
over committed sources — the suite counts are counts of methods in
`ec/tools/test_grade_0751_isolation.py` at named revisions, and the chain that
reaches the current one is a count per commit — reproducible offline with the
commands above against the revisions each transcript names, and with the tests
named. No live run, no register readback, no hardware observation; no line of
this change may be read as a report of a capture, and none is one.
`confirmed-inert` is §7's call, made by a human holding the rest of the notes,
and nothing here bears on it either way.
