# The withheld banner counted one way over windows numbered another (issue #500)

The write-up for [issue
#500](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/500), which is
about `ec/tools/grade_0751_isolation.py`'s withheld banner naming a count
`--block` runs cannot read off the windows printed above it. It is a
**presentation fix: no byte is read differently, no window is graded or
withheld differently, and the exit code is unchanged.** Nothing here is a
register behaviour and nothing here is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §6 is the
one-attachment-per-value workflow and §7 is the call the output feeds.

---

## The defect, on a committed fixture with nothing edited

`ec/tools/testdata/0751-isolation-run-3blocks/` is a three-value day: blocks
`0xA0`/`0x00`/`0x10`, all three blocks' marks in one set the way §3 takes them,
and block 2's restore mark absent in all three captures. Two of the day's 8
windows are withheld, both of them in the block under test.

    python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-3blocks/*.csv --block 0x00

printed, before this change:

```
=== block 2 of 3, value under test 0x00, 2 window(s) in it ===

--- mark 4/8: ... 'no-op wrote 0x0751=0xA0' ...
    block: 0x00 (block 2 of 3) -- NOT GRADED
--- mark 5/8: ... 'wrote 0x0751=0x00' ...
    block: 0x00 (block 2 of 3) -- NOT GRADED
...
  2 of the 2 window(s) above were not graded: the mark set of the block they fall in does not hold, ...
```

and prints, after it:

```
  2 of the 2 window(s) of this block (2 of the capture's 8 window(s)) were not graded: the mark set of the block they fall in does not hold, ...
```

"of the 2 window(s) above" is false about the two windows printed directly
above it, which the same run numbered **4 and 5 of 8**. Those windows are 2 of
the day's 8, and 8 is the number a reader needs before §7's `confirmed-inert`
call.

## Why the banner, and not the other two counts

One run puts three counts on one set of windows, and only one of them was wrong.
The three were not collapsible onto a single number, so the choice was which to
fix:

- **The per-window headers stay numbered over the whole mark stream** (`mark
  4/8`, `grade_0751_isolation.py:2116`, `:2129`, `:2134` and `:2149` all pass
  `i + 1, len(windows)`). That is deliberate, and the comment above `shown`
  (`:2090-2092`) says why: it is what makes a `--block` run a *subset* of the
  whole-capture run, which is how §6's one attachment-per-value workflow reads
  the two side by side. Renumbering them to the block's count would destroy that
  and contradict the issue's own "that is deliberate".
- **The section header's `2 window(s) in it` is correct.** The block does have
  2 windows. Moving it to `len(windows)` would make a true line false.
- **The banner's denominator was the wrong one**, and it is the only line a
  `--block` attachment prints that carries a count at all.

So the fix makes the banner unambiguous rather than collapsing the three onto
one figure. On a whole-capture run `len(shown) == len(windows)`, so **the
defect exists only under `--block`** and the whole-capture wording is correct
today — which is why the change is `--block`-conditional and byte-identical
otherwise, leaving every existing whole-capture attachment's wording unchanged
and the pins [#486](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/486)
added green without editing them.

**The census is not restructured either.** It already prints
`8 action(s) after the merge` and lists all 8 actions in the same run, so the
day's 8 was never missing from a `--block` attachment. The banner was a
presentation defect, not a missing fact, and the fix belongs in the banner.

## What a `--block` run can print, and why the blast radius is one line

Walking the per-window loop (`:2105-2153`) against a `--block` run bounds what
the banner is the only count of. `shown` (`:2089`) holds only windows with
`w.block is selected`, and that makes two of the three withholding paths
**unreachable** under `--block`:

- `unreads` is fed from `unplaceable_marks(unplaced)` and `unagreed` from
  `unplaced_window_problems(unplaced, captures)`, and both iterate
  `assign_blocks`'s `unplaced` list. `Window.block` defaults to `None` for
  those, so `--block` cannot select them — the same fact
  `0751-grader-partial-grade-claims.md` records for the label path.
- What is left keys on `w.block.problems`, and `check_block_marks` appends
  per-block, so a block either has problems or does not.

Hence under `--block` the withheld count is **0 or all of `len(shown)`**, and
`graded` is correspondingly `len(shown)` or 0. Two consequences, both of them
why the diff is this small:

- the banner (`:2198-2215`) is the only line a `--block` attachment prints with
  a count, and the only one with the mismatch;
- the two sentences that print `graded` — `:2251` under `if withheld:` inside
  the `moved_groups` branch, and the `elif withheld:` pair at `:2327`/`:2343` —
  are **unreachable on a `--block` run**. A withheld block grades nothing, so
  `graded == 0` takes `elif graded == 0` (`:2286`) first; and a run that graded
  nothing records no `moved_groups` at all, so the first cannot fire either.

**Left byte-identical, with the reason stated rather than assumed:** those two
sentences. Editing them would move the output of every whole-capture fixture,
to fix nothing observable on a `--block` run.

## The change

Confined to the closing-summary block in `ec/tools/grade_0751_isolation.py`,
plus the `graded` comment above it and one new module constant.

- The reason clause and its refusal — every sentence after `were not graded:` —
  moved to a `WITHHELD_REASON` constant (`:477`) so both paths share one
  sentence. It is load-bearing: "What they would have shown is not reported
  here and is not to be quoted from this run" is what keeps a withheld window
  unquotable, and it survives the rewrite on **both** paths. The reason still
  names all three withholding paths on both, even though `--block` reaches only
  the first: narrowing it would be a claim about which path the run took, which
  is the loop above the print's to decide.
- The banner (`:2198-2215`) selects its scope on `selected is None`. A
  whole-capture run prints the old string byte for byte; a `--block` run prints
  the block's own count first and the capture's second, the withheld count
  written out on both halves. It prints the real `withheld` rather than `All`,
  even though `withheld == len(shown)` is provable here: the text reports what
  the loop counted and does not bake in an invariant a future refusal path could
  break.
- The `graded` comment (`:2155-2171`) is **corrected**, not just moved. It used
  to justify `len(shown)` as "the denominator the withheld banner already uses,
  so the two counts agree by construction" — a property the banner no longer
  has once it names both. Its replacement states the reason `len(shown)` is the
  right denominator in its own right, and records the reachability fact above so
  the next reader does not re-open whether the two sentences below it are dead
  code on a `--block` run.

## No new fixture, and why

The invariant is observable in exactly one committed shape: a capture whose
block window count differs from the capture's, read with `--block`. The
single-block fixtures (`void-block`, `missing-mark`, `disagreeing-marks`) have
2 windows in 2, where the two denominators **coincide** and nothing is visible
— a `--block` run over them printed the ambiguous wording and it happened to be
correct. `0751-isolation-run-3blocks/` already reproduces it, and
`3blocks-moved/` is the same structure. `ec/tools/testdata/` and its README are
untouched.

## What is pinned

`ec/tools/test_grade_0751_isolation.py`, one existing test extended and no test
method added, so the suite's count is unchanged. All passing under `bash tools/run-tests.sh ec/tools`:

| test | case | what it holds |
|---|---|---|
| `test_a_void_block_is_graded_on_its_own_and_says_so` | `3blocks/` with `--block 0x00` | rc 1; the section header's `2 window(s) in it`; `marked_windows` is still `[(4, ...), (5, ...)]`; the banner names **both** of its denominators with the real withheld count; the ambiguous `2 of the 2 window(s) above` string is **absent**; the refusal clause still present |

That test is the one place a `--block` run's three denominators meet: the
section header's 2, the headers' `/8`, and the banner's own pair. The first two
were already asserted; the banner is the third, and the `assertNotIn` pins the
defect as a regression rather than a rewording — no phrasing of that single
ambiguous denominator may come back.

**Whole-capture non-regression needs no new assertions.** The old banner string
is already pinned in five places, all whole-capture runs, none of them edited:

| test | fixture | banner string pinned |
|---|---|---|
| `test_a_partly_withheld_run_says_what_its_graded_windows_show` | `3blocks/` | `2 of the 8 window(s) above were not graded` |
| `test_a_withheld_window_in_no_block_claims_no_block_was_refused` | `unread-window/` | `1 of the 8 ...` |
| `test_an_unreadable_mark_does_not_count_twice_in_the_graded_unplaced_line` | `unread-window/` | `1 of the 8 ...` |
| `test_a_window_in_no_block_fails_the_same_agreement_checks` | `unplaced-window-failures/` | `2 of the 8 ...` |
| `test_a_window_in_no_block_whose_marks_agree_is_not_refused` | `unread-window/` | `1 of the 8 ...` |

Their failing *is* the signal that the whole-capture wording moved.

## Left out on purpose

- **#497** — a wholly-graded `--block` run printing the unqualified prediction
  sentence. Excluded by the issue and a different defect: no count is wrong
  there, and the `--block` run's denominator is right. Fixed under
  [#497](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/497); see
  [`0751-grader-block-scope-claims.md`](0751-grader-block-scope-claims.md).
- **#498** — `unreads` not being scoped by `--block`. It cannot produce this
  banner: an `unreads` window is in no block, so `--block` never selects it,
  which is the reachability fact above.
- **The two sentences that print `graded`** — byte-identical, because they are
  unreachable under `--block`, as shown.
- **Renumbering the per-window headers**, or changing the section header — the
  first destroys the deliberate whole-stream numbering §6 depends on, the
  second would make a correct line false.

Also unchanged: `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` quotes
no closing-summary text (`window(s) above` / `were not graded` match nothing in
it) and §6/§7 need no rewording; `ec/README.md`'s `grade_0751_isolation.py`
bullet describes what the tool is and where its suite is, not how the closing
summary branches; and `ec/annotations/registers.yaml` does not move — no
register status is in question, only what a report may say about the windows it
read.

## What this opens, as a fact rather than a fix

The same walk that settles the blast radius turns up a second gap, and it is
narrower than "a `--block` run says nothing about the rest of the day" — §6
already records that it does say something, and it does: the census prints the
whole mark stream and marks the other blocks `-- not selected in this run`, and
the block section says "the other 2 block(s) were not checked in this run".
Both disclosures are in the same run as the banner.

What is missing is narrower, and it is the part this change's second
denominator happens to make visible. The **closing summary** states the
withheld count as 2 of the capture's 8 and nothing else states, anywhere in
that section, that the run *read* 2 of those 8 — so a reader who reads
`=== what this does and does not settle ===` alone gets the day's total
without the run's share of it, and has to go back to the census for that.
Before this change the same reader got neither, from a banner whose 2 read as
the day's.

That is adjacent to #497 and is best folded into it rather than widened here —
it is the same question one step along, of what a `--block` run says about the
capture it is a subset of. Named here because a merge is expected to say what
it opens, not because this PR does anything about it.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above and the tests named. No fixture was
added, edited or regenerated by this change, and no line of it may be read as a
report of a capture or a live observation.
