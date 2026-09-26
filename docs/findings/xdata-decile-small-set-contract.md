# `deciles()` had a floor in its docstring and none in its code, and the report was already printing the stretch (issue #889)

**2026-09-26, issue #889.** One sentence of
`ec/tools/xdata_moved_ranks.py`'s `deciles()` said a set too small to cut ten
ways is reported as the set it is rather than stretched over ten cells. The
body did the opposite: it returned ten cells for every non-empty input, with
`min(len(ordered) - 1, ...)` clamping the last cut onto the final row. The
docstring was wrong and the code was stretched. The choice was between
returning the set itself below a stated floor and documenting the clamp; this
takes the first, puts the floor at **ten**, and pins it with five
`--self-test` cases — three of which fail against the code as it was.

**No published figure moves.** The two reads §4 of
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) rests on are over 94
keys and 439 rows, and every other published `deciles` read is over 23 keys at
least, so all of them are byte-identical after this branch. That is measured
rather than assumed, and the measurement is in its own section below because
it is the claim a reader has most reason to doubt.

**Nothing here is a hardware claim.** No image is opened, no register is read
back, and no laptop, EC or Windows machine is involved. The tool reads
committed CSVs and writes nothing. Every figure below is Python over those
files, or `git`.

## What was measured, before anything was changed

Against committed blob `1aa0826` (`ec/tools/xdata_moved_ranks.py` at
`bb4c1d2`), `deciles(range(1, n + 1))`:

| n | returned |
|---|---|
| 0 | `no rows` |
| 1 | `1 1 1 1 1 1 1 1 1 1` |
| 2 | `1 1 1 1 1 2 2 2 2 2` |
| 3 | `1 1 1 1 2 2 2 3 3 3` |
| 5 | `1 1 2 2 3 3 4 4 5 5` |
| 9 | `1 1 2 3 4 5 6 7 8 9` |
| 10 | `1 2 3 4 5 6 7 8 9 10` |
| 11 | `1 2 3 4 5 6 7 8 9 10` |

Every row below ten is the stretch the docstring denies: the input's own
distinct values laid over ten cells, so the cells repeat wherever there are
fewer than ten rows to give them. The issue's own table carries one
transcription slip — its `n = 3` reads `1 1 1 2 2 2 3 3 3`, nine cells where
the tool emits ten — which changes nothing about the finding, since the finding
is the shape rather than the count. What is not in doubt is the gap between
the two rows at nine and at ten, which is the whole of the next section.

## The report was already printing the stretch, on a green self-test

The issue says no `--self-test` case calls `deciles`. The narrower truth is
better than that: `across_report` calls it twice and `cause_report` twice
more, and the A/B fixture the self-test already runs goes through
`across_report`. The stretched string was being computed and thrown away on
every green run — and, in the one place it was not thrown away, printed.

Running that fixture, the report's two lines read:

```
  the flipped set's size distribution, against the census: 2 2 2 2 2 2 2 2 2 2
                                            the census:  1 1 1 1 2 2 2 2 2 2
```

**The first line is a two-element set.** The fixture flips two clusters and
both hold two addresses, so the string is one distinct value printed ten
times — set beside a census read as a distribution, on the very line whose
purpose is to let a reader compare two distributions. That is the defect
running, in a suite that was green, and it is why the fix has to be asserted
on the *report* and not only on the helper: a helper that stopped stretching
would still leave a caller free to print the stretched string itself.

## The reading taken: a floor of ten, and the set itself below it

Ten is not a round number picked for the sentence. It is the smallest `n` at
which the formula the docstring describes — cell `i` is the value at 0-based
rank `(n * i) // 10` — is **one whole row per cell with none doubled up**. The
step from cell to cell is `n / 10`, so from ten rows upward every cut advances
at least one rank, and the ten cuts are ten distinct rows in order. At nine
that already fails: the first two cuts are both rank 0, and the string reads
`1 1 2 3 4 5 6 7 8 9`.

That property is the reason for the floor rather than a taste. §4 of
`xdata-moved-ranks-fall.md` reads one of these strings against another, cell
for cell, and concludes the two are "the same shape, shifted right by roughly
one step". **That comparison has a valid form and an invalid one, and the
count of rows is the only thing that tells them apart.** Under the clamp, a
cell holding two keys produced a ten-cell string that satisfied every visual
property a distribution has — ten numbers, non-decreasing, sitting on a line
of its own — while being two numbers drawn ten times. A reader would have had
to notice the input was small in order not to read a shape off it.

**The alternative is rejected rather than deferred.** Keeping the ceiling
behaviour and documenting the clamp in the docstring would satisfy the
docstring clause of the issue and leave the defect, because the failure is not
that the code stretched a small set — it is that the stretched form was
*indistinguishable in the output* from a real read. Writing down "the cells
are clamped" does not make a 23-key cell's three distinct values into a
distribution, and a floor is what removes the indistinguishable form instead
of describing it. Both of the issue's two options are named in the opening
paragraph above; this is the one taken, and the reason.

The `cause` cells are what make the argument concrete rather than theoretical.
They are per-cell reads of the same kind, over sets a re-derivation can make
small: the self-test's own `cause` fixture has four cells holding 1, 2, 2 and
1 keys, and all four of their `the subject rows by size:` lines were stretches
before this branch and are now the sets they are.

## What the code does now

Three branches, in the order the docstring states them, at
`ec/tools/xdata_moved_ranks.py:243`:

- **empty** — `no rows`, reported before the floor rule applies. An empty set
  is not a set too small to cut; it is no set at all, and the two are told
  apart in the output because a reader counting flipped clusters should not
  have to distinguish "none" from "some too few to measure".
- **1 to 9 rows** — the sorted sizes as themselves, behind the marker
  `N row(s), too few to cut ten ways:`. The marker is load-bearing rather than
  decorative: it is what keeps the below-floor form unconfusable with a decile
  read in a transcript, which is the property the whole floor is for.
- **10 rows and up** — the ten-cell nearest-rank read, **byte-identical to
  what it was**. This is what keeps every published string standing.

## The published figures did not move

Recomputing the census side from the committed
`ec/annotations/xdata-clusters.csv`, over all **439** of its rows:

```
1 1 1 1 1 1 2 2 4 5
```

byte-identical to `xdata-moved-ranks-fall.md:199` and `../findings.md:7989`.
The flipped side is 94 keys and the census side 439, both far above the floor,
which is why neither can move. The four `deciles` reads quoted in
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) are over
**71**, **266**, **23** and **40** keys — the four cells' own headings, at
`:136`, `:143`, `:150` and `:157` — so all four are above the floor too and
none changes. There is no published read anywhere in the tree over fewer than
ten rows.

**The whole transcript, not just its decile lines.** §2's and §3's commands
were re-run as recorded, both writes going to `/tmp` and the 430-row half
rebuilt through `git worktree add --detach` at `e169a0e4` exactly as that
section does. The two census regenerations land on **439** and **445** rows as
recorded, and `across` then diffs against the transcription in
`xdata-moved-ranks-fall.md` **byte for byte** — the `71 / 266 / 23 / 40` cells,
the `366 − 315 = 51` close over four terms, §6a's `210 of 1171` and `210 of
1326`, the mean-delta table and the twelve flipped rows.

`cause` was re-run the same way, on the command
`xdata-flip-cause-derivation.md:88-93` records flag for flag. That write-up
transcribes the output across several sections rather than in one block, so the
comparison is per-figure rather than a single diff: the eight-line header
block in §1 comes back identical, and so do all four
`the subject rows by size:` lines at `:136`, `:143`, `:150` and `:157`. The
floor is a branch only a below-ten input can reach, and no published input is
below ten.

**This is not a claim that every read is informative.** The `intact -> moved`
cell at `xdata-flip-cause-derivation.md:150` is 23 keys whose ten cells read
`1 1 2 2 2 2 2 2 2 2` — three distinct values, and it stays that way after
this branch. The floor is a property of the *input's* size, not a judgement
about how much variety a 23-key cell has. What the floor removes is exactly
one thing: a set too small to cut ten ways being drawn out to fill ten cells
anyway. A 23-key cell with three distinct values is a real read of a real set,
and thinning it would discard information rather than protect a reader from a
shape.

## Two corrections to the issue's reading of where the claim lives

**1. The issue's `xdata-moved-ranks-fall.md:220` does not hold the sentence.**
That line is one of the twelve rows of the flipped-cluster transcript, under
the `cluster_key / name / size / grew / delta A / delta B / verdict` header at
`:214` — a data row, `moved->intact`. Repo-wide before this branch, the phrase
existed in exactly one place: the tool's own docstring. The correction that
was needed was therefore not beside a claim in that document but **in the
tool**, and §4's decile sentence — which the issue cites correctly, and which
is the one a reader would over-read — carries a short note pointing here rather
than a retraction, because §4's own figures were never wrong.

**2. "All 14 cases in `--self-test`" understates the suite by eleven.** There
were **25** cases before this branch and **30** after. The finding the count
was attached to holds regardless: none of the 25 reached a size distribution,
which is the whole of why the stretch was never noticed.

## What is left open

- **The clamp above the floor is now inert and was left in place.** For
  `n >= 10` the last cut is `(n * 9) // 10 <= n - 1`, so `min(..., len - 1)`
  can never bind, and every cut is distinct — both stated in the docstring's
  terms and worth saying here so the line is not read as load-bearing. It is
  left deliberately: removing it would change no output and would make this
  diff touch a line the floor does not require touching.
- **This tool's `--self-test` is in no gate and in no `tools/run-tests.sh`
  sweep** — `xdata_moved_ranks.py` is named in neither `.github/` nor the
  runner, and `run-tests.sh` discovers `test_*.py` only — so the five new
  cases are proven by the run quoted in the PR, not by CI. That is a real
  limitation and it is not new: it applies to all 25 cases that were already
  there, which is why fixing it is a different defect from this one. The gate
  file is copied from `ElDavoo/agent-pipeline` and the plan stage's token has
  no `workflow` scope, so the in-repo route is a prepared patch under
  `docs/ci/`, in the shape
  `docs/ci/agent-gates-disasm8051-self-test.patch` and
  `docs/ci/agent-gates-0751-self-test.patch` already take for exactly this job
  — wiring one tool's `--self-test` into `agent-gates.sh` — and described by
  [`prepared-gate-patches.md`](prepared-gate-patches.md), not an edit to
  `.github/`. That is the follow-up's content.
- **No new `test_xdata_moved_ranks.py` suite**, following the choice
  `../findings.md:8022` records for #852 — `--self-test` over synthetic
  fixtures rather than a new suite row, which would also oblige a row in the
  shared `tools/README.md` table that `tools/test_readme_suite_table.py`
  checks. Both new floors live in the same `--self-test` the tool already had.
- **`ec/tools/test_check_cluster_citations.py` is red on this branch, and was
  red before it.** It reports two disagreements on
  `docs/findings/xdata-cluster-names-guard-off-recipe.md:220`, about `0x0464`
  and `0x0465` not being members of the clusters that line names. Re-running
  it against a pristine `HEAD` tree gives the same two, character for
  character, so it is a separate defect in a file this branch does not touch
  and it is named here only so that a reader who runs `tools/run-tests.sh` on
  this branch does not attribute the red to it. The other 34 suites are green.

No register `status:` moved, no `registers.yaml` row was touched, no CSV, YAML
or threshold changed, no gate was edited, no image was opened, no register was
read back, and nothing is opened in another repository.
