# The 833 enters `write` and never leaves it: the word was wrong, the number was not (issue #890)

**2026-09-26, issue #890.** `xdata_moved_ranks.py pair`'s §6a line printed

```python
f"references leaving write "
f"{sum(int(offreg[a]['write']) - int(on[a]['write']) for a in on if a in offreg)}"
```

— a sum of **signed** differences under a label asserting a direction. A
column that goes *up* contributes positively, so the figure is
`arrived − left`, not `left`. The tool's convention is committed →
guard-off, so the movement is the other way round: the references **enter**
`write` and none leave. **The number was always right. The word was always
wrong**, and the word is the whole of what three committed pages carried it
through.

The tool now prints gross movement in each direction beside the net, so no
label can again name a direction the arithmetic did not check; four
`--self-test` cases reach the line, which none did before; and the
per-address form of the same property — that no address's `write` *falls*
under `--no-eq-guard` — is measured over both censuses below and is held by
`test_xdata_cluster_names.py::TheGuardOffRegeneration::test_the_census_is_the_one_6a_measured`.

**No published figure moves.** The 210, the 0, the 833, the 1,326 and the
445 are reproduced exactly on today's tree, so §6a, §6b and
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) are unaffected apart
from the word itself, and every transcript quoted in any of them is left as
written.

**The #890/#900 merge moved three line pins in this file and no figure, and the
pre-merge values are kept here per §4a-4d.** #890 added `write_movement()` and
its four self-test cases; #900 added `rank_of()`, `signed()`, the
`rank_shift_report()` block and the `--cell` walk beside them, and the merge
takes both, so `write_movement()` is at **`ec/tools/xdata_moved_ranks.py:181`**
rather than `:147`, the `pair_report` block is at **`:270-283`** rather than
`:236-249`, and the four cases are at **`:1215-1277`** rather than
`:1108-1170`. **What the merge changed is where this correction's own code
sits, not what it does**: the `entering`/`leaving`/`net` figures, the `closes:`
arithmetic and the four cases are identical on both sides, and
`xdata_moved_ranks.py --self-test` is green with all of them.

**Nothing here is a hardware claim.** No image is opened, no register is
read back, and no laptop, EC or Windows machine is involved. Both censuses
are committed text plus a regeneration into `/tmp`, and every figure below is
Python over those two files or the output of a command printed beside it.

## The measurement

The guard-off regeneration, exactly as
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md)
specifies it, writing only to `/tmp`:

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/off-registers.csv --out-clusters /tmp/off-clusters.csv
wrote /tmp/off-registers.csv: 1326 rows
wrote /tmp/off-clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
```

Read per address against the committed `ec/annotations/xdata-registers.csv`:

| over the 1,326 committed rows | |
|---|---:|
| addresses whose `write` **increases** | **210** |
| addresses whose `write` **decreases** | **0** |
| gross increase, leaving the guard on | **833** |
| gross decrease | **0** |
| net `off − on` | +833 |
| addresses whose `refs` changes | 0 |
| addresses whose `write` is unchanged | 1,116 |

**The net and the gross coincide, and that is a property of these rows, not of
the sum.** 833 is the net *and* the gross because no address decreases; the
old line could not tell the two apart, which is why a reader was entitled to
believe either. Over the `program` partition it reproduces
`xdata-06c2-06db-timers.md` §6a's table row for row: main-EC `write`
3,206 → 3,948 (**+742**), PD 142 → 193 (**+51**), the 49 both-image addresses
239 → 279 (**+40**), summing to 833.

The per-address deltas are not uniform, which is the second thing the old line
hid. Of the 210 that move, **104 move by exactly 1** and **106 by more**; the
largest is **42**, at `0x0843`, `0x0844` and `0x08A8` — the first and third of
which are the two addresses §6a names in its table, arriving as the 42 that
turns their committed `write` of 0 and 2. So `write changes 210` and
`references ... 833` are counts of different things over the same comparison,
and no closure between them is available. The one that is, is per address, and
it is what the tool now prints.

## Why the label names a direction the census never had

`--no-eq-guard` sets `eq_guard=False`, and that drops **one** exclusion:
the `==` rejection at `xdata_register_map.py:1753`, inside `store_target()`.
The tool's own docstring says so in the terms this turns on — the flag "drops
only that second exclusion: the pre-#178 classifier, kept runnable so the
guard's effect stays measurable rather than becoming a paragraph of remembered
numbers" (`:1743-1745`).

An exclusion that stops being applied can only *admit* occurrences the
committed census did not count. It cannot make the classifier reject one it
counted. So a `write` column under `--no-eq-guard` is weakly greater than the
committed one address for address, and the signed sum is a sum of
non-negative terms. The number was right for that reason. The *word* was not:
"leaving" describes what the guard does when it is **installed** — the
references it keeps out — and the tool's own convention is the opposite one.
Both sentences are true about the same 833 and they read as contradictions
side by side, which is the defect in one line.

`ec/annotations/xdata-register-map.md:789` is the one place in the tree where
"leaving" is the right word, and it is left alone: it reads *"837 references
leaving the two store buckets: 833 `write` and 4 `read+write` became reads"*,
which is the guard-on convention, stated as what installing the guard removed.
Different sentence, opposite direction, correct as written. It is named here
because a reader who greps for `leaving write` will find it and should not
conclude from the hits alone that every one of them is a defect.

## Where the word was carried, and what happened to each

Every occurrence of the signed-sum label in the tree, with its verdict. Five
are corrected here and two more in place on the pages that carry it; the rest
are records of runs, a copy of a record, or the opposite convention, and the
reason each is left is beside it.

| where | what it is | verdict |
|---|---|---|
| `xdata_moved_ranks.py` `pair_report` | the f-string itself | **corrected here** — `write_movement()` at `:181` and the block at `:270-283` |
| `xdata_moved_ranks.py --self-test` | no case reached the line | **corrected here** — four cases, `:1215-1277` |
| `test_xdata_cluster_names.py` | the comment naming §6a's figure | **corrected here** — the word only |
| `test_xdata_cluster_names.py` | an `AssertionError` message quoting §6a's label | **corrected here** — the word only, so a re-deriver is not sent to a label the page no longer has |
| `xdata-census-rederivation-checklist.md:59` | a pointer row describing `:785` | **corrected here** — one cell; it names what `:785` says, and this branch changed what that is |
| `xdata-06c2-06db-timers.md:785` | §6a's bold row | **corrected in place**, wrong wording left visible in the 2026-09-25 re-derivation note below the table |
| `xdata-moved-ranks-fall.md:148` | §2's table row | **corrected in place**; both cells stay 833 |
| `xdata-moved-ranks-fall.md:156-165` | "the guard itself did not change" | **corrected in place**, the word only — the paragraph's claim is untouched and re-measured |
| `xdata-06c2-06db-timers.md` 2026-09-25 note | a re-derivation record | **left** — a record of that run, per §4a-4d; named from the footnote under the table |
| `xdata-06c2-06db-timers.md:980,987` | §6b's heredoc and its output | **left** — a runnable reproduction of §6a. Relabelling the `print()` would make the transcript below it something the command no longer prints |
| `xdata-moved-ranks-fall.md:116,129` | the two `pair` transcripts | **left** — records of two runs, the way the stale figures at `:297-307` are kept |
| `xdata-cluster-names-guard-off-recipe.md:129,153,160` | a copy of §6b's heredoc and a table derived from it | **left** — same reason, and it is §6b's page to correct |
| `xdata-6a-direction-rows-pinned.md:147` | a quoted `AssertionError` | **left** — a record of a failing run |
| `findings.md:4880` | a blockquoted historical claim | **left** — a quotation |
| `findings.md:8091` | §62's summary prose | **left** — a shared file, and §67 below is the correction beside it rather than an edit to it |
| `xdata-register-map.md:789` | the guard-on convention | **left on purpose** — correct as written, as above |

## What the code does now

`write_movement()` at `ec/tools/xdata_moved_ranks.py:181` is one
module-level helper returning
`(entering, leaving, net, entering_addrs, leaving_addrs)`, so the report and
the self-test read the same function rather than a print statement and a test
asserting the print statement. `pair_report` prints:

```console
  §6a: address universe identical (1326 rows); write changes 210 of 1326; refs changes 0 of 1326; references entering write 833, leaving write 0, net +833
  closes: 210 + 0 = 210, over the 210 address(es) whose write column changed
```

**The `closes:` line is over addresses, and the plan this implements asked for
a different one — stated plainly, because the difference is arithmetic and not
a matter of taste.** The issue's `sum(max(0, on - off))` would print **0** and
discard the 833 three committed pages carry, so that option is not usable; the
issue's alternative, "print the net *and* the gross beside it", is what this
does, with both grosses and both directions. What the issue then asked for as
the closure, `entering + leaving == changed`, **cannot hold and never did**:
`entering + leaving` is a sum over references and `changed` is a count of
addresses, and this census moves 833 references across 210 addresses, so the
two are equal only if every changed address moved by exactly one. Over these
1,326 rows **104 of the 210 do and 106 do not**, which is the histogram above. The
closure that *is* available is per address — `len(entering_addrs) +
len(leaving_addrs) == changed` — and that is what the line prints, because it
is the property that makes `write changes 210` and the direction pair one
measurement rather than two independent loops.

It has teeth, and the only input that reaches it is stated in the helper's
docstring: `changed` is a **string** inequality and the helper an **integer**
subtraction, so a cell that is numerically but not textually equal (`"05"`
against `"5"`) is a change to one and no movement to the other. Every `write`
cell in both censuses is canonical — 1,326 rows checked, 0 non-canonical in
each — so nothing real reaches it. The `MISMATCH` marker is the file's
existing idiom from `across_report`'s four-term close (`:349-352`), reused
rather than invented.

### The four new `--self-test` cases

The issue's structural point is the one that matters and it is correct: the
only `pair_report` call in `self_test()` passed `registers=None`, so the whole
registers block was dead to `--self-test` and `'leaving write'` appeared in no
case. Four now do, over fixtures the file already had where possible.

1. **`on_b`/`off_b`, generation B's own fixture**, where `0x62` goes 0 → 5.
   This is the issue's own reported case: it pins *entering* 5, *leaving* 0,
   and asserts the bare string `leaving write 5` is **absent** from the output.
   It is the load-bearing one — it fails against the code as it was, because
   that code printed `leaving write 5` for a fixture where nothing left and
   five arrived.
2. **A pair with a decrease in it**, one reference each way so the two cancel.
   The first fixture cannot make this case: with only an increase, "both
   directions are counted" and "the count happens to be right" are
   indistinguishable. Here a signed total prints `+0` and a one-sided gross
   prints `4`.
3. **A negative net**, read from the helper *and* from the printed line so the
   two are compared as a reader would read them, asserting the net is `-4`,
   entering `3` and leaving `7` are the counts, and neither carries a sign.
4. **The `MISMATCH` line fired**, over the `"05"`/`"5"` fixture above, so the
   closure is shown to be reachable rather than assumed to be.

All 34 `--self-test` checks pass (30 before this change).

## The known-answer run

The whole `pair` report over the committed census and the regeneration above,
`head`ed at the line that changed:

```console
$ python3 ec/tools/xdata_moved_ranks.py pair \
    --old ec/annotations/xdata-clusters.csv --new /tmp/off-clusters.csv \
    --old-registers ec/annotations/xdata-registers.csv \
    --new-registers /tmp/off-registers.csv
pair ec/annotations/xdata-clusters.csv
  committed  ec/annotations/xdata-clusters.csv: 439 rows
  guard-off  /tmp/off-clusters.csv: 445 rows
  moved      315  (main-ec 295, pd 20)
  intact     124
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 307 hold a guard-off row of the same size and 311 share no address with it
  guard-off membership delta over the 439 rank(s) the two censuses share: 1030 address-slots
  §6a: address universe identical (1326 rows); write changes 210 of 1326; refs changes 0 of 1326; references entering write 833, leaving write 0, net +833
  closes: 210 + 0 = 210, over the 210 address(es) whose write column changed
```

**Every figure on those eight lines is one a committed page already carried** —
the 439, the 445, the 315, the 124, the 1,030 address-slots, the 210, the 0
and the 833 — so the transcript doubles as a check that nothing moved. Only
the last two are new, and only the words in them.

## What this does not claim

- **"No address's `write` decreases" is a measurement, not a property of the
  classifier.** It is one committed census against one regeneration of that
  same tree on 2026-09-26, over 1,326 rows. The *reasoning* behind it is
  separate and stronger — one exclusion is lifted, and lifting an exclusion
  only admits — but the reasoning is about `--no-eq-guard` as a flag, and the
  measurement is about this tree. Per CLAUDE.md's rule, the assertion is
  written as the direction over these two censuses, and a re-derivation that
  produced a decrease would go red for the re-deriver to look at, not for a
  classifier defect to be declared.
- **The gross-read loss is 836, not 833, and the three-address difference is
  recorded rather than chased.** The same 210 addresses lose `read` — gross
  836, gross gain 0 — and `read` and `write` differ per address at exactly
  three of them: `0x06E6` (+41 write, −42 read), `0x07D5` (+2, −1) and
  `0x0860` (+11, −14), whose differences sum to the 3. This is an observation
  about two columns of the same addresses and is **not** part of this change;
  it is named because a reader comparing the two gross figures will find the
  gap and should not have to rediscover its address list.
- **Nothing about the EC, the firmware, or the machine.** The mechanism is the
  `==` rejection at `xdata_register_map.py:1753` and the fact that a CSV
  column moved; no firmware image was opened, no register was read back, no
  address was written. `833` remains a count of occurrences of a token in
  decompiled C, which is what it has always been.
- **The flag is not judged.** Whether `--no-eq-guard` *should* exist is a
  design question this does not touch. The direction of its effect is a fact
  about the tree, and this change only makes the tool's own output name that
  fact correctly.

## What is left open

- **Four places still carry the wrong wording as records, and one carries it
  as a defect this branch did not reach.** The four records are named in the
  table above and are left for the reason given there: two of them
  (`xdata-06c2-06db-timers.md:960` and
  `xdata-cluster-names-guard-off-recipe.md:153`) are a *runnable heredoc*, and
  the honest fix is to relabel the `print()` **and re-run it**, which is
  §6b's page and §6a's reproduction rather than this issue's. The fifth is
  `docs/findings.md:8091` (§62's summary), which a later section corrects by
  pointer; it is a one-word fix in a shared file and is deliberately not made
  here.
- **The `refs` column has the same shape and is not checked for it.** §6a's
  third figure is "0 of 1,326 addresses whose `refs` changes", and this
  measurement says the *same* 210 addresses are the only ones that move in any
  column — `refs` never moves at all, in either direction. Whether `refs`
  deserves a gross pair beside `write` is a question about the report's
  shape, not a defect, and is not answered here.
- **`--self-test` is in no gate and in no `tools/run-tests.sh` sweep**, the
  same limitation
  [`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md)
  records: the runner discovers `test_*.py` only, and wiring one tool's
  `--self-test` into `agent-gates.sh` is a prepared patch under `docs/ci/`
  because `.github/` is out of an agent branch's reach. The four new cases
  are therefore proven by the run quoted here, not by CI. The **per-address**
  assertion, unlike them, is in
  `test_xdata_cluster_names.py` and *is* in the runner's sweep.
- **`ec/tools/test_check_cluster_citations.py` is red on this branch and was
  red before it** — two disagreements on
  `docs/findings/xdata-cluster-names-guard-off-recipe.md:220`, about `0x0464`
  and `0x0465`, in a file this branch does not touch. Recorded so a reader who
  runs `tools/run-tests.sh` does not attribute the red to this change; the
  other 34 suites are green. `runner-red-suite-set.md` carries the sequence.

No register `status:` moved, no `registers.yaml` row was touched, no census
was re-derived, no CSV or threshold changed, no gate was edited, and nothing
is opened in another repository.
