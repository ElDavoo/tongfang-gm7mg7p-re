# What `--no-eq-guard` moves at census scale, joined one register row at a time

The write-up for [issue
#832](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/832), which is
about `ec/tools/xdata_register_map.py`'s `--no-eq-guard` refusal arguing from
an instruction where the `--export-ownership` refusal eighteen lines below it
argues from a measurement. What this branch adds is the measurement, at the
granularity the issue said had never been measured: the 1,326 rows of
`ec/annotations/xdata-registers.csv` joined row by row against a guard-off
regeneration, split by program.

**Nothing here is a hardware claim.** No register was read back, no firmware
image was opened, and no laptop, EC or Windows machine is involved. Every
figure below is the output of a command over committed CSVs, run with its
scratch outputs under `/tmp`; both runs write nothing into this repository and
`git status --porcelain` is unchanged by them. A row that moves under the flag
is **different under the flag** — never "mis-clustered", which is a verdict
about the firmware that two classification runs cannot support. That is the
same line `check_cluster_citations.py`'s own docstring and the caveat at the
top of `ec/annotations/registers.yaml` both draw, and it is drawn here because
this page is the one a reader comes to when they want to know which of the two
censors is right.

**Neither refusal is relaxed, and neither is reworded.** The `--check`/
`--self-test` refusal and the committed-output refusal stand exactly as they
were. What the issue compared was the two *comments* above them — the
`--export-ownership` one quotes measured numbers and this one quoted none — so
what changed is the six-line comment block above the first, which now carries
the figures below and points here. The measurement is the argument *for* keeping
the refusals, not a proposal to relax either, and the new tool writes nothing at
all, so it cannot violate the second by construction.

## The question the tree had not answered

Most of the answer was already committed when this issue was opened, and the
measurement sits on top of it rather than beside it:

| already committed | where | what it is |
|---|---|---|
| 439 → 445 cluster rows; 124 ranks intact, 315 changed | [`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md) §"The six cases" | the cluster-level answer |
| 424 of 439 `cluster_key`s unchanged, i.e. **15 move**; of the 15, 10 reach a new cluster on overlap and 5 reach none | `ec/annotations/xdata-register-map.md` §4.4 | the `cluster_key` answer |
| **0 of 1,326** rows change `refs`; **210 of 1,326** change `write` | the recipe page's own heredoc, §6a's transcript | the `write`/`refs` answer, already measured |
| nine names: 3 movers, 1 changed on both columns, 5 untouched | the recipe page's table | the names, at key level |

Every one of those is counted over **clusters or names**. None is counted over
rows, and the issue is right that this was the gap: "of the 1,326 rows, how many
change `cluster_id`" and "of the 439 clusters, how many change `cluster_key`"
are different questions, and a reader holding the registers CSV is holding the
first one. So that is what `ec/tools/xdata_guard_off_row_join.py` is for, and
the last section below is what putting the two answers next to each other
turned up.

## The join, and the key it uses

The join key is `addr` alone. That is sound here because all 1,326 rows of the
committed CSV carry a distinct `addr`, and the tool **measures** it on both
inputs and prints it rather than assuming it — a fact about this file on this
tree, not about the format, and one that stops being true without anyone
noticing. An address present in one census and not the other is reported as its
own bucket and never dropped: a row that disappeared is a different fact from a
row that did not move, and a join that drops the first goes on reporting the
second.

Both runs write only to `/tmp`, and the two the second is read from are the
same pair every other page in the tree uses — `--no-eq-guard` on the committed
tool, which is the switch §6a re-runs:

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/off-clusters.csv --out-registers /tmp/off-registers.csv
  names: seeded 8, exact 0, carried by overlap 1, tied, not carried 0, with no name 436
    ...
wrote /tmp/off-registers.csv: 1326 rows
wrote /tmp/off-clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
$ python3 ec/tools/xdata_guard_off_row_join.py \
    --off-clusters /tmp/off-clusters.csv --off-registers /tmp/off-registers.csv
join key: addr
committed rows: 1326 over 1326 distinct addresses
guard-off rows: 1326 over 1326 distinct addresses
addresses under more than one program: 0 committed, 0 guard-off
addresses compared: 1326 in both
addresses committed only: 0
addresses guard-off only: 0
```

The last line is the one worth stopping on. The census has a `program` column
with three values and 49 rows carry `both`; an address under more than one
program would be two rows sharing one join key, which is why the report splits
by program rather than summing, and why the number is printed rather than left
implied. It is 0 here, and a case in the suite holds that it is measured rather
than assumed.

## What moves, at the row level

Of the 1,326 register rows:

| column | differs | `main-ec` | `pd` | `both` |
|---|---:|---:|---:|---:|
| `cluster_id` | **507 of 1,326** | 464 of 1,169 | 9 of 108 | 34 of 49 |
| `cluster_key` | **336 of 1,326** | 291 of 1,169 | 35 of 108 | 10 of 49 |
| `write` | 210 of 1,326 | 173 of 1,169 | 19 of 108 | 18 of 49 |
| `refs` | **0 of 1,326** | 0 of 1,169 | 0 of 108 | 0 of 49 |

The `write` and `refs` rows are §6a's, reproduced rather than assumed: the
suite reads them back off the two CSVs the run above wrote, not off a fresh run
of the same recipe, because a case that re-derives its expectations from its own
inputs agrees with itself by construction. `refs` is the row that matters most
and is the one most easily missing from a report — it is the column that does
not move, and a report that stopped comparing it would print nothing for it
rather than a wrong number, which is the failure the suite's assertion on it is
shaped to catch.

The `both` column is the one nobody had a figure for, and it is the least
intuitive: **34 of the 49** rows the census marks `both` change `cluster_id`,
against 464 of 1,169 for `main-ec` alone. Those 49 are addresses both programs
touch, so both programs' classifications of them moved, and they moved at a
rate four times the main-EC one. That is a property of this flag's effect on
this census, and it is a reason a per-program figure quoted without its
denominator should be read carefully: `464 of 1,169` and `9 of 108` are both
"the flag moved some rows", and only one of them is 40%.

## The 439 `cluster_key`s, and the 15 among them

Fifteen of the 439 committed `cluster_key`s are absent from the guard-off set,
and 21 guard-off keys are new. That is §4.4's "15" and the recipe page's
"439 → 445", both reproduced. What the row join adds is *which* rows those 15
are, and the answer is the last section's.

The split of the 15 is §4.4's as well — 10 reach a new cluster on overlap, 5
reach none — and the scores are its too, which is the check worth having: a tool
that called all fifteen a match would have matched the total and missed the
claim. From the report:

```
cluster_key that moves: 15 of 439 committed keys are absent from the guard-off set; 21 guard-off keys are new
  distinct committed keys a key-changing row sits in: 15
  of those, absent from the guard-off set: 15
  reach a new cluster on overlap: 10 of 15 at or above 0.50
  reach none: 5 of 15
    pd-001: kb5652a66acb4 -> pd-001 at 0.97
    main-ec-002: kefb63d82f8c7 -> main-ec-002 at 0.97
    main-ec-001: ke794087e13a6 -> main-ec-001 at 0.94
    main-ec-012: k2a30862cf8eb -> main-ec-012 at 0.91
    main-ec-018: k8752aa6b045e -> main-ec-022 at 0.88
    main-ec-019: k462303ed5f86 -> main-ec-023 at 0.88
    main-ec-032: k516793bfb8af -> main-ec-018 at 0.75
    main-ec-020: kaed8fb28e30d -> main-ec-051 at 0.50
    main-ec-086: ka4f882015765 -> main-ec-029 at 0.50
    main-ec-115: k1beb7f80aed2 -> main-ec-240 at 0.50
    main-ec-122: k1aeee4fb86d3 -> none at 0.33
    main-ec-169: ka59f2949e659 -> none at 0.25
    main-ec-321: k20bd67848123 -> none at 0.17
    main-ec-048: kf2f3b6d27ea4 -> none at 0.03
    main-ec-145: k2a740ad8c603 -> none at 0.02
```

0.50–0.97 for the ten and 0.02–0.33 for the five: §4.4's ranges, on this tree,
measured by the same `jaccard` and `CARRY_MIN_JACCARD` the carry rule uses
(imported from the tool rather than re-derived — a second copy of the threshold
in a second file is a second number for one rule). **The tool reuses the rule
rather than restating it, and that is why the two agree.**

## The nine hand names

All nine committed names resolve in the guard-off census. Eight arrive by key
and one by overlap:

```
name countdown-06c6: main-ec-128 -> main-ec-125, key same, 2 -> 2 addrs, carried seeded at 1.00
name countdown-06cd: main-ec-214 -> main-ec-214, key same, 1 -> 1 addrs, carried seeded at 1.00
name counter-sweep: main-ec-003 -> main-ec-003, key same, 43 -> 43 addrs, carried seeded at 1.00
name fan-step-08a0: main-ec-292 -> main-ec-297, key same, 1 -> 1 addrs, carried seeded at 1.00
name ff-fill-stubs: main-ec-007 -> main-ec-007, key same, 12 -> 12 addrs, carried seeded at 1.00
name flag-pair-0442: main-ec-125 -> main-ec-122, key same, 2 -> 2 addrs, carried seeded at 1.00
name level-block-086x: main-ec-004 -> main-ec-004, key same, 28 -> 28 addrs, carried seeded at 1.00
name mode-oem-init: main-ec-002 -> main-ec-002, key changed kefb63d82f8c7 -> kc0f2a0be0103, 92 -> 93 addrs, carried overlap at 0.97
name user-clear-bytes: main-ec-013 -> main-ec-013, key same, 9 -> 9 addrs, carried seeded at 1.00
names: 9 committed, 9 resolve in the guard-off census
```

That is the recipe page's table, from the same rule rather than from a second
opinion about it: `mode-oem-init` re-keys and changes membership by one address,
three names move rank while keeping key and membership, and the other five do
not move at all.

**And the prose corpus against the guard-off census.** The issue raises this
because `check_cluster_citations.py`'s `name_re()` builds its alternation from
the census it is given, so a name whose cluster moved under the guard would be
*silently unresolvable* there — "not found by this method", never reported. The
tool already has a flag for exactly this question, and running the same corpus
against both censuses is the whole of it:

```console
$ python3 ec/tools/check_cluster_citations.py
3 citation(s) disagree with ec/annotations/xdata-clusters.csv
$ python3 ec/tools/check_cluster_citations.py \
    --clusters /tmp/off-clusters.csv --registers /tmp/off-registers.csv
51 citation(s) disagree with ../../../../../tmp/off-clusters.csv
```

3 against the committed census, **51 against the guard-off one** — 48 membership
and 3 census-count, where the committed run's three are 2 membership and 1
census-count. Exactly **one** of the fifty-one is the same line under both
censuses, the census-count row that disagrees either way. The other fifty are
the tree's prose read against a clustering its ranks do not describe, and the
two membership lines the committed run already reports come back in a
different spelling, because the message names the clusters the line cites and
those are the ids that moved.

**That number is not a verdict on the prose.** It is what the checker reports
when the census under it moves, and it is the same shape as the 507: many
sentences that were correct against the committed ranks read against a
different ranking. Which of the two censuses describes the firmware better is
not a question four CSVs answer, and this page does not answer it. What the run
does show is that the prose is a **function of the census**, which is the
argument for the guard's committed-output refusal rather than against it.

## The 15 and the 336 are one population

This is the issue's sharpest sub-question, and the answer is that the two
figures are not two populations that happen to be near each other.

| | count |
|---|---:|
| committed `cluster_key`s absent from the guard-off set | **15** |
| distinct committed keys that a key-changing row sits in | **15** |
| …of those, absent from the guard-off set | **15** |
| register rows whose `cluster_key` differs | **336** |
| register rows whose `cluster_id` differs | **507** |
| …both columns change | 54 |
| …rank only (the key held) | 453 |
| …key only (the rank held) | 282 |
| …neither | 537 |

Every committed cluster a key-changing row sits in is one of the 15 whose key
the flag took away, and the two sets are equal. So the 15 and the 336 are one
set of clusters at two granularities — 15 clusters, 336 rows — and neither
figure can be checked without the other: a report of "15 moved" on its own says
nothing about how much of the census that is, and a report of "336 rows" on its
own reads as if a quarter of the register map had been re-clustered rather than
fifteen clusters out of 439.

**The cross-tab is the part the cluster-level count cannot have.** `cluster_id`
is a rank and `cluster_key` is a content hash, so they answer different
questions and neither implies the other. **282 rows change their key while
keeping their rank** — the row is in the same numbered position and a different
cluster — and **453 rows change rank while keeping their key**, which is the
ordinary consequence of the renumbering §4.4 is about. A census-scale sweep
driven off `cluster_id` would have chased 507 rows and found 453 of them to be
the same cluster they started in. That is a small argument for reading the key
column when the question is "did this change", and the `507` alone is not it.

## What this does not do

- **No register's behaviour is claimed, and no `status:` moves.** This is a
  measurement of one classifier flag's effect on a committed grouping. Nothing
  in `ec/annotations/registers.yaml` is edited, and no `status:` value is in
  question.
- **No committed census is regenerated or re-keyed.**
  `xdata-registers.csv`, `xdata-clusters.csv` and `xdata-cluster-names.csv` are
  byte-untouched and are read as *inputs*; both generations of the comparison go
  to a scratch directory. A row that moves under the flag is different under
  the flag, never mis-clustered — "not found by this method", which is the
  standing caveat on every static scan in this tree and is load-bearing here
  rather than decorative.
- **Neither refusal is relaxed, and the flag's default is untouched.** The
  measurement is the argument for the refusals. The `--export-ownership`
  sibling's own denominators are stale (1,171 / 430 / 10 against 1,326 / 439 /
  9) and out of scope here, the same way `check_cluster_citations.py`'s "the
  ten committed names" is; both are left for their own issue.
- **The 22 pre-existing `check_eq_guard_citations.py` failures are not
  repaired.** That gate is red on this tree before this change and red after it,
  by the same count: every declared citation into `xdata_register_map.py` sits
  tens of lines below where the code now is, because the tool has grown since
  the pins were written. Re-pointing them means editing four shared files, one
  of which is the frozen `docs/findings.md`, and it is a question about the
  pins rather than about this finding. This change is built not to add to the
  count: the `--no-eq-guard` comment above the refusal is **six lines before
  the edit and six after**, and the four `ap.error` lines below it are four
  either way, because `check_eq_guard_citations.py` resolves `check_refusal` to
  `:5030` and `committed_output_refusal` to `:5039` out of the code immediately
  below that block. A suite case holds the line counts, because the reason for
  the constraint is mechanical and a reader should not have to reconstruct it.
- **No live hardware or Windows step**, because nothing here needs one. No live
  run is planned, claimed or implied.
- **Nothing is opened in another repository.** No driver or firmware change is
  proposed here, so there is nothing to send to `Wer-Wolf/uniwill-laptop` or
  `tuxedo-drivers`.
- **`docs/findings.md` is not edited.** It is frozen, and
  `ec/tools/check_findings_frozen.py` fails an addition; the page is discoverable
  through the regenerated `docs/findings/INDEX.md` instead, which is how a new
  write-up becomes visible in this tree.

## The test that proves it

`ec/tools/test_xdata_guard_off_row_join.py` splits the two jobs it has apart on
purpose. `ThePublishedFigures` holds every figure on this page to a page that
already prints it, **against the CSVs the run actually wrote** — §6a's 445/439,
210 of 1,326 `write`, 0 of 1,326 `refs`, 394/389 main-EC clusters, 124/315
ranks, the 15 and its 10/5 split and its two score ranges. `TheRowLevelJoin`
holds the arithmetic instead: the denominators (1,169 / 108 / 49 over 1,326)
are asserted because they are properties of the committed CSV, and **no count of
moved rows is typed**, because a typed 507 is a claim that goes stale silently.
`TheToolWritesNothing` holds the read-only contract from the tool's own side —
no write mode anywhere in it, no `--out-`, the flag still refused against the
committed paths, and a full run leaving `git status --porcelain` byte-identical
to what it was.

```console
$ python3 -m unittest discover -s ec/tools -p 'test_xdata_guard_off_row_join.py'
..............................

Ran 30 tests in 5.9s

OK
```

The count is reported as the run prints it and is a property of this merge,
not a claim about any suite.

**Landing the suite moved one other gate, and it moved the way that gate is
built to move.** `check_pin_table_by_cited_file.py` indexes every `test_*.py`
in the tree and files the ones no committed markdown cites a *line* of. This
page names the suite's tool and the census it reads but never a
`test_*.py:NNN`, so the new suite joins that tail: the suite count and the
unpinned tail each take one, and the pinned count does not move. The two
assertions above the one changed say so in place rather than silently, which
is the same reason the comment is there at all.

**The cases were checked for the ability to fail.** The refusal comment's page
pointer, its figure, and the report's per-program split were each perturbed in
turn — the pointer removed, every figure removed, one program bucket dropped
from the tool's `PROGRAMS` — and each perturbation turned a named case red
before being reverted. A case that cannot fail has not been shown to check
anything.
