# Why the guard-off regeneration's moved-rank count fell from 366 to 315, measured (issue #852)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over committed text, with every scratch output under
`/tmp` and `git status --porcelain` printing nothing after the runs. The two
censuses this reads are files; the guard-off one is a regeneration of a
committed tree by `xdata_register_map.py --no-eq-guard`, which reads
`ec/decompiled/**` and `ec/firmware/GMxMGxx_11.800` as files. Same framing as
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):11
and [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):11.

The issue asks two things and this answers both: **which clusters stopped
moving and why**, and **whether `> 300` at
`ec/tools/test_xdata_cluster_names.py:417` still says what the comment beside it
says it says.** The answer to the second is *leave it there*, and it is decided
by §5 below rather than by the 15 ranks of headroom
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):170-175
counts.

**A note on the number 366, because it means two different measurements in this
tree.** Every occurrence below says which one. The `366` in
`ec/tools/check_cluster_citations.py:17-20` — and the 427, 425, 59 and 413 beside
it — is issue #274's **threshold-0.45 re-run**: 59 of 427 ids intact, 366
naming a different membership. It is not the 366 here. The 366 here is
`test_the_regeneration_really_moves_the_ranks`'s count for the **430 → 439
guard-off pair**, and it is what §1 re-derives from a commit.

The measurements come from a new read-only tool,
[`ec/tools/xdata_moved_ranks.py`](../../ec/tools/xdata_moved_ranks.py), which
reads four clusters CSVs and two registers CSVs, prints, and writes nothing.

**Two places in §2 carried the wrong direction word and no number moved,
2026-09-26 (issue #890).** The `833` row read "references leaving `write`"; the
references enter, and both corrections are in place at §2 with the measurement
behind them in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md).

## 1. M0 — the historical pair reproduces exactly, so the fall is a fall and not two different measurements

The 366 was never re-derived. The commit that carries the 430-row census is
`e169a0e4a736956f35af5ffff65e997154c76bdd` — "rank the 455 not-yet-owned
unannotated common-area functions … (#620)", 2026-09-25 — the last commit whose
`ec/annotations/xdata-clusters.csv` has 430 data rows. Its successor `6bf9c234`
(#279) is the one that re-derived the census to 439.

**`--no-eq-guard` is present at that commit**, so the old pair needs no
copy-and-patch route: #528 (`db6d7d2d`) added the flag, and
`git merge-base --is-ancestor db6d7d2d e169a0e4` says so. That is checked
because the plan named it as the thing to check before relying on the flag, and
because the recipe this suite used before #753 existed at all.

The old tree's own census is current there, so the committed half of the pair
is the tree and not a stale file:

```console
$ git log --format='%H %ad %s' --date=short -- ec/annotations/xdata-clusters.csv \
    | while read c rest; do echo "$c $(git show $c:ec/annotations/xdata-clusters.csv | wc -l)"; done
6bf9c2341b28ff8db1f0976a74d4ac2c9e04231e 440
e169a0e4a736956f35af5ffff65e997154c76bdd 431
f0be5173d2c9f6807cf5aaaaabb5de78902f8516 431
... twelve more, all 431 ...
e6c88864505068a5bcd43d1042bd22b3911503ee 428        # the last 427-row census

$ git show e169a0e4:ec/tools/xdata_register_map.py | grep -c 'no-eq-guard'
11
$ git worktree add --detach /tmp/xdata-old e169a0e4a736956f35af5ffff65e997154c76bdd
HEAD is now at e169a0e4 rank the 455 not-yet-owned unannotated common-area functions
by a stated criterion, and land a 37-row first tranche of the runtime-helper tail (#620)
$ cd /tmp/xdata-old && python3 ec/tools/xdata_register_map.py --check
  names: seeded 10, exact 0, carried by overlap 0, tied, not carried 0, with no name 420
/tmp/xdata-old/ec/annotations/xdata-registers.csv: 1171 rows match a fresh generation from the committed tree at threshold 0.5
/tmp/xdata-old/ec/annotations/xdata-clusters.csv: 430 rows match a fresh generation from the committed tree at threshold 0.5
$ cd /tmp/xdata-old && python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/old-off-clusters.csv --out-registers /tmp/old-off-registers.csv
  names: seeded 8, exact 0, carried by overlap 2, tied, not carried 0, with no name 429
    main-ec-001 carries mode-oem-init by overlap, Jaccard 0.97 from k7497cf885614 -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-022 carries page-0300 by overlap, Jaccard 0.78 from k3fdd14ddea2e -- re-key annotations/xdata-cluster-names.csv if the name moved
wrote /tmp/old-off-registers.csv: 1171 rows
wrote /tmp/old-off-clusters.csv: 439 rows
  main-ec: 1062 distinct addresses, 13964 references, 388 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
```

**The tool then computes the 366 from those two files, and it is 366.**

## 2. The two pairs, side by side

Both derivations, printed rather than summarised — the form
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):216-271
uses. Both runs write only to `/tmp`; `git worktree remove /tmp/xdata-old` runs
after them and `git status --porcelain` prints nothing.

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/new-off-clusters.csv --out-registers /tmp/new-off-registers.csv
  names: seeded 8, exact 0, carried by overlap 1, tied, not carried 0, with no name 436
    main-ec-002 carries mode-oem-init by overlap, Jaccard 0.97 from kefb63d82f8c7 -- this run's ids are not the committed census's (--no-eq-guard), and annotations/xdata-cluster-names.csv is anchored to the committed one, so a carry here is arithmetic over a different clustering, not a re-key request
wrote /tmp/new-off-registers.csv: 1326 rows
wrote /tmp/new-off-clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5

$ python3 ec/tools/xdata_moved_ranks.py pair --label 'the 430-row pair' \
    --old /tmp/xdata-old/ec/annotations/xdata-clusters.csv --new /tmp/old-off-clusters.csv \
    --old-registers /tmp/xdata-old/ec/annotations/xdata-registers.csv \
    --new-registers /tmp/old-off-registers.csv
pair the 430-row pair
  committed  /tmp/xdata-old/ec/annotations/xdata-clusters.csv: 430 rows
  guard-off  /tmp/old-off-clusters.csv: 439 rows
  moved      366  (main-ec 346, pd 20)
  intact     64
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 351 hold a guard-off row of the same size and 364 share no address with it
  guard-off membership delta over the 430 rank(s) the two censuses share: 1623 address-slots
  §6a: address universe identical (1171 rows); write changes 210 of 1171; refs changes 0 of 1171; references leaving write 833

$ python3 ec/tools/xdata_moved_ranks.py pair --label 'the 439-row pair' \
    --old ec/annotations/xdata-clusters.csv --new /tmp/new-off-clusters.csv \
    --old-registers ec/annotations/xdata-registers.csv --new-registers /tmp/new-off-registers.csv
pair the 439-row pair
  committed  ec/annotations/xdata-clusters.csv: 439 rows
  guard-off  /tmp/new-off-clusters.csv: 445 rows
  moved      315  (main-ec 295, pd 20)
  intact     124
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 307 hold a guard-off row of the same size and 311 share no address with it
  guard-off membership delta over the 439 rank(s) the two censuses share: 1030 address-slots
  §6a: address universe identical (1326 rows); write changes 210 of 1326; refs changes 0 of 1326; references leaving write 833

$ git worktree remove /tmp/xdata-old
$ git status --porcelain
```

The two pair blocks above, read together, are the whole measurement. Three of the
rows are the ones the count does not show:

| | 430-row pair | 439-row pair |
|---|---:|---:|
| committed rows | 430 | 439 |
| guard-off rows | 439 | 445 |
| **moved** | **366** | **315** |
| intact | 64 | 124 |
| moved, `main-ec` / `pd` | 346 / 20 | 295 / 20 |
| committed ranks absent from the guard-off census | 0 | 0 |
| §6a: addresses whose `write` changes | **210** of 1,171 | **210** of 1,326 |
| §6a: addresses whose `refs` changes | 0 of 1,171 | 0 of 1,326 |
| §6a: references entering `write` † | **833** | **833** |
| guard-off membership delta, address-slots | **1,623** | **1,030** |

**`intact` is verified rather than assumed.** No committed rank is missing from
either guard-off census, so `366 + 64 = 430` and `315 + 124 = 439` both close.
Had a committed id been absent, the arithmetic would not have, and that would
have been the finding instead.

**The guard itself did not change, and this is stronger than the counts
matching.** §6a's per-address triple is *identical* in both generations — the
same **210** addresses have their `write` column changed, the same **0** have
`refs` changed, the same **833** references enter `write` † — and the two runs
perturb **the same 210 addresses, address for address**, which a pair of matching
totals would not establish on its own. §3's transcript prints that comparison
from the same four registers CSVs. The address universe grew 1,171 → 1,326, the
**155** addresses `ec/annotations/xdata-cluster-names.csv`'s `mode-oem-init` note
records, and **none of the 155 is perturbed at all**: not one of the bytes this
re-derivation added is a byte the guard reaches.

† **The direction word, corrected 2026-09-26 (issue #890).** Both occurrences
on this page said *leaving*; the tool's convention is committed → guard-off and
the sum behind the figure is `off − on`, so the references **enter** `write` and
none leave. **The `833` is unchanged in both cells and the paragraph's claim is
untouched** — same 210 addresses, same 0 `refs` changes, same 833, same address
set, all four re-measured on today's tree. What was wrong was one word, and it
was wrong in the tool that printed it: `xdata_moved_ranks.py` summed signed
differences and printed the total under a label asserting a direction the
arithmetic never checked, which is what carried the word this far. The
measurement, the correction and the per-address property behind it are in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md).
The `pair` transcripts at `:116` and `:129` above print the old wording and
**stay as written** — they are records of two runs, the same way the stale
figures at `:297-307` below are kept rather than re-transcribed.

**What did change is what the guard's perturbation does to cluster boundaries:
1,623 address-slots of membership change became 1,030.** That is a fall of 593,
and it is the quantity §4 accounts for. The last two rows of the pair blocks are
the other half of why `moved` is not a magnitude of perturbation: **351 of 366**
and **307 of 315** moved ranks hold a guard-off row of *the same size*, and
**364 of 366** and **311 of 315** share *no address at all* with it. A moved
rank is overwhelmingly a **substitution** — one same-sized group replaced by
another at the same number — not an address added to a large group. Read as
"the guard perturbs N clusters", that count is close to meaningless; read as
"the guard-off ranking disagrees with the committed ranking on N rows", it is
exactly what the floor is about.

## 3. The flip table, keyed on `cluster_key` and not on the rank

`ec/annotations/xdata-06c2-06db-timers.md:885-896` (§6b's correction) is the
cautionary case: a transcript written out in the half-renumbered shape of a run
that never happened, caught because the ids and the counts disagreed. So the
cross-pair diff is keyed on **`cluster_key`**, and every row is about a key.
Ranks are printed as data, always beside the key, because the rank is what moved
and the key is what did not.

**The table below walks the flipped cells and only those, which is why the
other two had no row to give.** The 266 that moved in both and the 40 intact in
both are counted in the summary and in the rank-shift block, and before this
were printed nowhere at all — so no column could ever have shown them.
`--cell` names the four cells under six names (`flipped`, `moved-both`,
`moved-a-only`, `moved-b-only`, `intact-both`, `all`) and defaults to
`flipped`, so the report above is the one this file has always carried, with
the two rank columns added beside it.

```console
$ python3 ec/tools/xdata_moved_ranks.py across \
    --label-a 'the 430-row pair' --label-b 'the 439-row pair' \
    --old-a /tmp/xdata-old/ec/annotations/xdata-clusters.csv --new-a /tmp/old-off-clusters.csv \
    --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/new-off-clusters.csv \
    --old-a-registers /tmp/xdata-old/ec/annotations/xdata-registers.csv --new-a-registers /tmp/old-off-registers.csv \
    --old-b-registers ec/annotations/xdata-registers.csv --new-b-registers /tmp/new-off-registers.csv
across the 430-row pair -> the 439-row pair
  keys in both committed censuses: 400; in one only: 30 / 39
    71  moved in the 430-row pair, intact in the 439-row pair
   266  moved in both
    23  intact in the 430-row pair, moved in the 439-row pair
    40  intact in both
  of the one-sided keys, 29 moved in the 430-row pair and 26 moved in the 439-row pair
  closes: 366 - 315 = 51, over the four terms: (71 - 23) + (29 - 26) = 51

  the flipped set's size distribution, against the census: 1 1 1 1 2 2 4 4 5 6
                                            the census:  1 1 1 1 1 1 2 2 4 5
  of the 23 committed cluster(s) of 8 addresses or more, 5 flipped; the largest committed cluster is 152 addresses
  of the 7 of 16 or more, 1 flipped
  shared keys whose committed membership differs between the two censuses: 0 of 400 -- a key is a hash of the membership, so this is zero by construction and is printed rather than assumed

  §6a across the two generations, over the per-address columns:
    the 430-row pair: write changes 210 of 1171
    the 439-row pair: write changes 210 of 1326
    the perturbed address sets are identical (0 only in the 430-row pair, 0 only in the 439-row pair)
    the 439-row pair adds 155 address(es) to the universe and 0 of them are perturbed

  mean guard-off delta over   71 moved -> intact A   7.66   B   0.00
  mean guard-off delta over  266 moved in both   A   3.14   B   3.04
  mean guard-off delta over   23 intact -> moved A   0.00   B   3.65
  mean guard-off delta over   40 intact in both  A   0.00   B   0.00

  rank shift between the two committed censuses; a positive delta is down the size ordering, and a delta is only comparable within one program
    over the 400 shared keys; the 30 in one census only and the 39 in the other have no counterpart to difference, so they are in no figure below
    main-ec   345 of  350 changed rank; mean  +9.63 over those,  +9.49 over all (an unchanged key at 0); range -8 to +15
    pd          0 of   50 changed rank; mean      - over those,  +0.00 over all (an unchanged key at 0); range +0 to +0
    of the   71 moved->intact    67 changed rank
    of the  266 moved-in-both   246 changed rank
    of the   23 intact->moved    23 changed rank
    of the   40 intact-in-both    9 changed rank
    over all  400 shared keys,  345 changed rank -- the four cells above close on it

  cluster_key    name             rank A       rank B       size  grew  delta A  delta B  verdict
  k0121504b8669  -                main-ec-136  main-ec-143     2     0        0        4  intact->moved
  k01ed753bc8ac  -                main-ec-114  main-ec-120     2     0        0        4  intact->moved
  k047da7d61103  -                main-ec-219  main-ec-232     1     0        2        0  moved->intact
  k0498704b659b  -                main-ec-073  main-ec-080     3     0        6        0  moved->intact
  k04dddd85ead2  -                main-ec-153  main-ec-164     2     0        0        4  intact->moved
  k07947f325d97  -                main-ec-032  main-ec-036     5     0       11        0  moved->intact
  k0933c373f5ad  -                main-ec-216  main-ec-229     1     0        2        0  moved->intact
  k0b7f9545b4f2  -                main-ec-155  main-ec-166     2     0        0        4  intact->moved
  k0f280d94b049  -                main-ec-070  main-ec-077     4     0        8        0  moved->intact
  k0f4e69560e36  -                main-ec-064  main-ec-073     4     0        8        0  moved->intact
  k0f5c689b2cfc  -                main-ec-147  main-ec-153     2     0        0        4  intact->moved
  k133a4ac2e88c  -                main-ec-025  main-ec-027     6     0       13        0  moved->intact
  (82 more; --rows for all of them)
```

**The three counts, and the fourth term that has to be named.** 71 clusters
stopped moving, 23 started, and 266 of the 400 shared keys moved in both pairs.
The one-sided sets — 30 keys in the 430-row census only, 39 in the 439-row one
only — are **not** netted off silently, because a difference of two totals
written as a difference of two subtotals is the half-renumbered transcript
§6b's correction is about. Split by moved/intact they are 29 and 26, and then
it closes: `(71 − 23) + (29 − 26) = 51 = 366 − 315`.

The 266 that moved in both are the bulk, and the ranking they disagree about is
mostly a renumbering: **345 of the 350 shared `main-ec` keys changed rank**
between the two censuses, over a range of **−8 to +15** and so on balance
*down* the size ordering, which is the `main-ec-002` → `main-ec-003` shift the
recipe's own transcript shows. A positive delta is down that ordering because
`cluster_id` numbers clusters by descending size, and the tool says so on the
line that prints the figure rather than leaving the convention to the reader.

**The mean needs its population named, because two of them are true and they
differ.** The tool prints both, each labelled: **+9.63** over the 345 keys that
changed, and **+9.49** over all 350 with the 5 that sat still read as 0. This
paragraph previously carried one figure, `+9.5 on average`, and did not say
which of the two it was over. It is the second — the mean over all 350 — and the
two are **not** interchangeable, so the figure that stands is the one whose
population is named.
*(This paragraph first read "by +9.5 on average" without saying which of the two
populations it was over; the re-derivation behind `ec/tools/xdata_moved_ranks.py`'s
rank-shift block is what settled it, and the superseded reading is left here per
[`../findings.md`](../findings.md) §4a-4d rather than edited out.)*

**The shift is strongly but *not perfectly* correlated with the cell a key
lands in, and the four numbers are the claim.** Of the **266** that moved in
both, **246** also changed rank; of the **40** intact in both, **9** did; of the
**71** that stopped moving, **67** did; of the **23** that started, **23** did.
The four cells sum to the **345** of the whole-shared figure, so the correlation
is stated over a partition rather than over two cells picked out of it. It is
imperfect in both directions — 67 of the 71 that stopped moving changed rank
anyway, and 31 of the 40 that never moved did not — and it is a statement about
the size of the reordering, not an identity for the cell. A cluster's
membership and its rank move independently: 4 of the 71 changed cell at the
rank they already held.

**`pd` did not move at all, which the `main-ec` figure alone would have hidden.**
All **50** shared `pd` keys hold the same rank in both censuses — a range of
`+0 to +0`, and no mean over the changed set because nothing changed. A single
mean over all 400 shared keys would have reported `+8.31` and said nothing about
which program's ranking it was a mean of; a rank orders one program's clusters,
so the two are reported apart.

## 4. M3 — the checklist's guess, measured on both halves, and it is wrong

> The tree records the fall without attributing a cause; a re-derivation that
> lands addresses in already-large clusters would move fewer membership sets,
> which is the obvious shape of it, but that is a guess and not a measurement.
> — [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):193-196

The guess has two halves and **both are refuted**. The guess stays visible above
and here beside the measurement, per [`../findings.md`](../findings.md) §4a-4d.

**Half one — "lands addresses in already-large clusters" — cannot be the
mechanism, because the flipped clusters' committed membership did not grow at
all.** `cluster_key` is a content hash over the program and the sorted
membership (`xdata_register_map.py`), so a key present in both committed
censuses is present because its membership is in both. The tool prints this
rather than assuming it: **0 of 400** shared keys have a committed membership
that differs between the generations, and the `grew` column is `0` on every one
of the 94 flipped rows. A flipped cluster gained nothing. It is not a large
cluster that absorbed an address; it is an unchanged cluster the guard used to
disturb.

**"The large clusters", as a distribution rather than an adjective.** The 94
flipped keys have size deciles `1 1 1 1 2 2 4 4 5 6` against the census's
`1 1 1 1 1 1 2 2 4 5` — the same shape, shifted right by roughly one step. Of
the **23** committed clusters of 8 addresses or more, **5** flipped; of the
**7** of 16 or more, **1**; the largest committed cluster is **152** addresses
and it is not in the flipped set at all. The last two of those are the same
distribution cut at two points, and the tool prints both rather than leaving
"the large clusters" to a threshold a reader has to pick. §2a's "the large
`main-ec` clusters" are not what stopped moving.

**Note, 2026-09-26 (issue #889): what this read needs to be one, and what it
prints without.** `xdata_moved_ranks.py`'s `deciles()` is a nearest-rank read
of ten cells, and it needs **ten rows or more** to be one: below that it
returns the set itself, marked, rather than ten cells drawn from fewer than ten
rows. The two figures above are over 94 keys and 439 rows, so **neither moves**,
and neither did any other read quoted here. None of them was ever a below-floor
read; the tool used to clamp the other way, and a cell of a few keys printed as
a handful of values repeated across ten cells — a shape indistinguishable from
a real read on a line of its own, which is the reason the floor exists. The
contract and the measurement are in
[`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md).

**Half two — the column that does move, and it moves in both directions.** The
guard-off delta `|addrs(off) Δ addrs(committed)|` of the cluster carrying each
key, per cell, as a distribution rather than an average — a mean would hide that
the quiet cells are quiet *completely*:

| cell | n | old pair | new pair | what changed |
|---|---:|---|---|---|
| moved → intact | 71 | mean 7.66, range 2–29 | **0 on all 71** | the guard's delta closed completely, on every one |
| moved in both | 266 | mean 3.14 | mean 3.04 | the same shape, both generations |
| intact → moved | 23 | **0 on all 23** | mean 3.65: **2** on four, **4** on nineteen | the delta opened on every one of them |
| intact in both | 40 | 0 on all 40 | 0 on all 40 | undisturbed by the guard in both |

Two worked rows, in full, because the shape of the change is the finding:

| `cluster_key` | committed (both gens) | 430-row guard-off | 439-row guard-off |
|---|---|---|---|
| `k07947f325d97` | `0x0A56 0x0A57 0x0A58 0x0A59 0x0A5A` (5) | `0x0769 0x076A 0x076B 0x076C 0x076D 0x076E` (6) | the same 5 — undisturbed |
| `k0121504b8669` | `0x0858 0x0859` (2) | the same 2 — undisturbed | `0x00DC 0x00DD` (2) — substituted |

These are not addresses added to a cluster. They are whole clusters replaced,
at the same rank, by a different group of about the same size — in the first row
a five-address block swapped for a six-address block, in the second a pair for a
different pair. The 155 addresses #279 added across the `0x03xx`–`0x05xx`
working page changed the co-reading matrix enough to move which cluster the
guard-off partition puts at a given number, in both directions, and `moved`
counts that.

**How far the cause is established.** The flipped set is **fully accounted
for**: 94 of 94 keys are named, the arithmetic closes over four terms, and for
each the quantity that changed is measured. What is *not* derived is why a
re-partition closes the guard's delta on those 71 particular small clusters and
opens it on those 23 — that is a question about the co-reading matrix under the
155 added addresses, and the search did not go there. So the claim is: **the
fall is the re-partition's, not the guard's, and the 94 clusters it happened to
are named.** It is not the claim that a particular re-partition change caused
it.

## 5. The floor, decided from §1–§4 and not from the headroom

The decision rule, quoted from the issue's own framing: *is the fall caused by
an identified, already-happened change, or is `moved` a quantity that shrinks as
the census grows?*

**It is the first, and `> 300` stays at `test_xdata_cluster_names.py:417`,
untouched.** The re-derivation that produced the 439-row census is one already
happened and named commit (`6bf9c234`, #279), its 155 added addresses are
recorded, and the 94 clusters whose behaviour changed are named and measured. So
`moved` is a property of a classifier generation, not a drift with a direction.

**And the honest limit of that, which is why the floor is not narrowed either.**
There is **one** observed re-derivation here, so **one** data point: a census
that grew 430 → 439 saw `moved` fall 366 → 315. A single observation cannot
establish that `moved` decays as the census grows, and this file does not claim
it does. What the measurement does support is the *structural* claim the
`> 300` floor is actually resting on — the comment at
`test_xdata_cluster_names.py:412-414` asks that a regeneration that renumbers
nothing is not the case the identity columns exist for, and at 315 moved of 439
it is very much not that — and the floor is left exactly where the recipe's
argument put it, with the measurement recorded beside it. The expectation to
carry is the other direction from the one the issue anticipated: **a future
re-derivation moves it again, and this measurement does not predict by how
much.** The 15 ranks of headroom
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):170-175
counts are a snapshot of one merge, the same way every other figure in this
census's prose is, and this re-derivation is the second time that has been true.

**No assertion is edited, and no threshold moves.** `assertGreater(len(moved),
300)` is unchanged, and the figures in the class docstring are unchanged — this
file is a measurement beside them, not a replacement for them.

## 6. The nine hand names, per pair

Per pair, for each row of `ec/annotations/xdata-cluster-names.csv`: did the
guard-off run change the membership of the cluster carrying that name?

| name | 430-row pair | 439-row pair | key |
|---|---|---|---|
| `mode-oem-init` | **moved** | **moved** | re-keyed twice, `k7497cf885614` → `kefb63d82f8c7` → guard-off `kc0f2a0be0103` |
| `level-block-086x` | intact | intact | `ka39cda99615f`, seeded in both |
| `countdown-06c6` | intact | intact | `kebb1f590f488` |
| `countdown-06cd` | intact | intact | `k801a3e80698f` |
| `counter-sweep` | intact | intact | `k733222e83898` |
| `fan-step-08a0` | intact | intact | `kb787f7579eab` |
| `ff-fill-stubs` | intact | intact | `kea0c67af9b51` |
| `flag-pair-0442` | intact | intact | `kb07a0f522a7d` |
| `user-clear-bytes` | intact | intact | `k66512c56e77b` |

**Exactly one hand name moves in either pair, and it moves in both.**
`mode-oem-init` is the tree's own `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`
case, the one name that arrives on overlap rather than by key, and the only
`cluster_name` in the census whose membership the guard changes. It is **not**
in the flipped set: it moved in the 430-row pair and moved in the 439-row pair,
which is the same cell, not a flip.

The 430-row census carried **ten** names and the 439-row one **nine**; the one
that went is `page-0300`, which is not in the current names file at all and
whose key `k3fdd14ddea2e` the old guard-off run carried on overlap at Jaccard
0.78 onto `main-ec-022`. That difference is visible in §1's transcript and is
recorded here so the two `names:` lines are not read as the same run.

**The two names sitting a generation behind their ids** are `mode-oem-init` and
`level-block-086x`: `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`
pairs `main-ec-001` with the first and `main-ec-002` with the second, and the
committed census puts them at `main-ec-002` and `main-ec-004`. The tree records
that at
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):401-411
and in [`../findings.md`](../findings.md) §44. **The identification is taken from
the tree rather than from the issue**: `gh issue view 778` is refused in the
implement stage's environment, so the number could not be read and the two
names are named from the record the tree already holds. If #778 means a
different pair, this table is the place to correct it.

The answer the issue wanted from that pair: of the two, **`mode-oem-init` is the
one whose membership the guard changes, in both generations**, and
`level-block-086x` is intact in both. Neither is in the flipped set, so a fall
in `moved` is **not** explained by a hand-named cluster's membership being
absorbed.

## 7. The 43 swept addresses, per address

The addresses come from `test_xdata_cluster_names.py`'s own `SWEPT_43` — passed
to `--swept`, not copied into the tool a third time. **All 43** sit in one
committed `main-ec` cluster, `k733222e83898`, the key `counter-sweep` names, in
every one of the four censuses here; it is **intact in both pairs and not
flipped**. **Five** of the 43 are *also* members of a `pd` cluster, because both
programs touch those bytes, which is why the block below prints 48 rows for 43
addresses and why a cross-reference reporting one holder per address would be
right by accident on 38 of them.

```console
$ python3 ec/tools/xdata_moved_ranks.py across \
    --label-a 'the 430-row pair' --label-b 'the 439-row pair' \
    --old-a /tmp/xdata-old/ec/annotations/xdata-clusters.csv --new-a /tmp/old-off-clusters.csv \
    --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/new-off-clusters.csv \
    --swept 0x0460 0x0468 0x055F 0x0621 \
    0x0635 0x0636 0x0637 0x0638 \
    0x0639 0x063A 0x06C2 0x06C3 \
    0x06C5 0x06D1 0x06D2 0x06D6 \
    0x06D8 0x06D9 0x06DA 0x06DB \
    0x06F3 0x0706 0x070B 0x070D \
    0x0723 0x07F3 0x07F6 0x0809 \
    0x080C 0x080D 0x0811 0x0843 \
    0x0844 0x085B 0x0890 0x08A7 \
    0x08A8 0x08E4 0x0981 0x0982 \
    0x0985 0x0986 0x09CE
  swept addresses: 43
  address  cluster_key    program  rank A       rank B       verdict
  0x0460   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0468   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x055F   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0621   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0635   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0636   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0637   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0638   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0639   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x063A   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06C2   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06C3   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06C5   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06D1   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06D2   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06D6   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06D8   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06D9   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06DA   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06DB   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x06F3   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0706   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x070B   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x070D   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0723   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x07F3   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x07F3   kedee1182bba5  pd       pd-002       pd-002       intact in both
  0x07F6   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x07F6   kedee1182bba5  pd       pd-002       pd-002       intact in both
  0x0809   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0809   kedee1182bba5  pd       pd-002       pd-002       intact in both
  0x080C   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x080C   kedee1182bba5  pd       pd-002       pd-002       intact in both
  0x080D   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x080D   ke928434f6676  pd       pd-033       pd-033       moved in both
  0x0811   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0843   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0844   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x085B   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0890   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x08A7   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x08A8   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x08E4   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0981   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0982   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0985   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x0986   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  0x09CE   k733222e83898  main-ec  main-ec-002  main-ec-003  intact in both
  3 committed cluster(s) hold at least one of the 43: 1 main-ec, 2 pd; 1 hold all of them; 5 address(es) have a second holder
  of those 3, 0 flipped; 1 moved in A and 1 moved in B
```

**The answer to "are they the clusters §2a already sweeps": no, in the sense
that matters.** The cluster the sweep is *about* — the one holding all 43 — is
intact in both pairs and is not in the flipped set. The only swept address whose
cluster moves at all is `0x080D`, in `ke928434f6676` (`pd-033`), and that one
moved in **both** pairs, so it is in the `moved in both` cell and not among the
94. **Zero of the three holding clusters flipped.**

## 8. What this does not do

- **No CSV, YAML or tool is edited.** `xdata-clusters.csv`,
  `xdata-registers.csv`, `xdata-cluster-names.csv` and `registers.yaml` are
  byte-untouched; the guard-off runs wrote only to `/tmp`, and the tool refuses
  the committed output paths in any case. `xdata_register_map.py` is not
  touched at all.
- **No threshold, figure or assertion moves.** §5 says why, and the floor is
  where the recipe's argument put it.
- **Nothing here is opened in another repository.** No driver or firmware change
  is proposed, so there is nothing to send to `Wer-Wolf/uniwill-laptop` or
  `tuxedo-drivers`.
- **No live hardware, EC, BIOS or Windows step**, because nothing here needs
  one. No live run is planned, claimed or implied. The one thing this reads that
  a reader might not expect is `ec/firmware/GMxMGxx_11.800`, and reading a file
  is not an observation of a machine.
- **The re-partition itself is not derived**, only located: §4 names what
  changed and what did not, and stops there.
- **No gate is wired.** The tool is a read-only investigation aid; the checklist
  already tells a re-deriver what to run by hand, and adding two census runs to
  every push would cost more than the gate gets.

## 9. The test that proves it

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test
xdata_moved_ranks.py --self-test
  ok    a rank whose guard-off row holds a different membership is moved, and the two that hold their own membership are not
  ok    the tool's count equals the suite's own two-line predicate over the same pair (2 moved)
  ok    a committed rank the guard-off census does not carry is reported, not folded into either count
  ok    a committed rank missing from the guard-off census is named
  ok    the moved ranks are split by program, so a `pd` mover is not hidden inside a `main-ec` total
  ok    moved and intact are reported as separate counts, and they sum to the ranks the two censuses share
  ok    both flip directions are reported separately, each naming its key
  ok    a cluster that moved in both and one that moved in neither are their own rows, not the absence of the other two -- and k4's and k8's ranks moved on the way, which is a renumbering and not a membership change
  ok    the moved-count difference closes over the four terms it is made of
  ok    a flipped set of two clusters is reported as the two sizes it is, on the line itself -- not `2 2 2 2 2 2 2 2 2 2` read as a decile distribution beside the census's
  ok    an empty set is reported before the floor rule applies
  ok    ten rows is the floor: one whole row per cell, and crossing it does not change the shape of the read
  ok    nine rows is below the floor -- the cells already double up at the ends there, so the set is returned rather than repeated
  ok    a set below the floor comes back sorted and marked, as the set it is and not as ten numbers a reader would take for deciles
  ok    a key in only one generation is named as such, in both directions
  ok    an address both programs touch is reported once per committed cluster holding it, not once
  ok    a cluster that flipped is labelled FLIPPED, one that did not is not, and the summary counts the `pd` holders separately
  ok    the second-holder count is over both generations' holders, so it equals the number of addresses that printed more than one row: 2 rows for 1 address, counted once
  ok    whether the two generations perturb the same addresses is reported on its own, not inferred from two matching counts
  ok    two runs can agree on a count and disagree on which addresses, and an address a re-derivation adds can be outside the guard's reach entirely
  ok    all four cells are filled from the fixture, the two controls included -- a mode that read only the flipped cells would see two of these and pass nothing
  ok    the population a cell's rate is read against is printed, with the one-sided keys named and the survivors' rank deltas spread
  ok    a substitution that reappears at a neighbouring rank is reported as reappearing, with that rank, rather than as a row that went missing
  ok    a substitution built from the added addresses is counted against the page and the added set, and its members are reported as having no holder in the generation that predates them
  ok    a control cell is counted with the same verdicts as a flipped one, so a rate the controls show is visible as such
  ok    an address both programs touch is indexed under each program's own rows, so a `pd` holder is never reported for a `main-ec` row
  ok    a row whose addresses land in two of its own program's rows is a split, and a member that also has a home in the other program is counted rather than resolved
  ok    a cell with no substitution says so on its own line, so its reappearance rate is not read as a mechanism
  ok    whether the two generations' `pd` partitions are the same partition at all is reported on its own, so a `pd` cell above it is visible as a disagreement rather than a surprise
  ok    a committed rank with no row in the guard-off census is in no cell, rather than in a cell with a missing subject row -- `absent_ranks` is the one place that names it
  ok    a rank is the number after the last hyphen, so neither the two-part program name nor a rank wider than the id's three-digit field is read as a digit or as a fixed window
  ok    a key's membership and its rank move independently: k1 changes cell at the rank it already had, and k2 holds its cell at a different rank -- the two directions the shift is not perfectly correlated with
  ok    both means are printed and each names its population, so "changed by N on average" cannot be read the wrong way round: +1.00 over the four keys that changed, +0.80 over all five
  ok    a rank shift is reported per program, so a ranking that moved in one program and not in the other is two figures rather than one average
  ok    the four cells partition the shared keys, so the per-cell changed-rank counts close on the one figure for the whole set
  ok    two size cut points on one distribution, so "the large clusters" is a range and not a threshold a reader has to pick
  ok    the default cell is the flipped one, so the table is the one the report has always printed with two rank columns beside it
  ok    --cell walks a cell the default does not: a key that never changed cell gets a row of its own, and only that key gets one
  ok    --cell all is every shared key, so the cells are walkable together as well as one at a time
  all checks passed

$ python3 ec/tools/xdata_register_map.py --check && python3 ec/tools/xdata_register_map.py --self-test
... 1326 register rows, 439 cluster rows, both exit 0 ...

$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
............................
Ran 28 tests in 15.721s

OK
```

> **Merged-tree note (2026-09-26, #891 landing beside #884).** The block above is
> the merged tree's run, re-recorded rather than carried over, so the check count
> it prints is the one the merged tool prints. The two modes that landed beside
> this one each brought their own fixture block, and both are in the transcript
> above in the order they run: the 15 checks this file already listed are checks
> 1–9 and 15–20, #884's `cause` block
> ([`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md)) is
> 21–30, and this change's own rank-shift block is 31–39 — so the tree prints
> **39 checks**, not the 24 this file's own change left and not the 25 the
> `cause` merge left. **A third block landed beside both and is why that figure
> is 39 rather than the 34 this note first recorded**: #889's five `deciles()`
> floor cases ([`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md))
> print at 10–14, between the two halves of the first fifteen, and the count was
> re-run on the merged tool rather than carried over. `rank_of` is one function
> on the merged tree rather than
> the two the two changes each wrote: `cause` needs the program beside the
> number and the rank shift needs the number, and the shared one returns
> `(program, rank)` so the shift's per-key difference takes the number half of
> it. The rank-shift fixture is lettered **`F`/`G`** here, not `D`/`E`, because
> the `cause` fixture above it is `A`/`B` and the two blocks share one scratch
> directory — the one rename this merge forced in the tool. Nothing else moves:
> §1's and §2's regenerations and §3's and §7's `across` runs were all re-run on
> the merged tree and are **byte-identical** to the transcripts above them, so
> every figure in §1–§4 stands as printed, and the 1326/439 and 28-test lines
> in this block were re-measured the same way.

**The known-answer run is §1 through §4 above**: the tool is what produced
366/64/439 and 315/124/445, the 71/266/23/40 flip table, the size
distributions, the **23-of-8-and-more and 7-of-16-or-more cut points**, the
four cell distributions, the **committed-A → committed-B rank shift** (345 of
350 `main-ec`, +9.63 and +9.49, range −8 to +15, and the four per-cell
changed-rank counts), the §6a comparison and the three-cluster cross-reference.
A `--self-test` that can only go green is not a test, and the fixtures are
chosen so it can go red: a committed rank with no row in the regeneration, both
flip directions, a key in only one generation, a key whose rank moved while its
membership did not, an address held by two programs' clusters at once, and two
runs that agree on a perturbed *count* over different address *sets*.

**The rank-shift cases needed a fixture pair the earlier fixtures could not
supply, which is the reason they are not a variation on them.** `b_committed` is
written from the same `committed_rows` as `committed`, so the two committed
censuses in that fixture are content-identical and **no key changes rank between
them at all** — the A→B check that says k4's and k8's "ranks moved on the way" is
asserted about the *guard-off* rows, not about the two committed censuses. (The
`cause` block's own `A`/`B` pair, merged in beside this one, is not a candidate
either: its second census *gains* a cluster but renumbers nothing, so every
shared key sits at the rank it already had.) The `F`/`G` pair is the same keys
and the same memberships under a different
numbering, plus one cluster `G` gained, chosen so that a key changing cell
without changing rank (`k1`) and a key changing rank without changing cell
(`k2`) both exist, that a zero-delta key shares a program with four moved ones
so the two means differ, and that a 9- and a 20-address cluster are both
present so the two size cut points are distinguishable. Each new case was checked to be
able to fail, each applied and re-run: each turns at least one check red — the
delta's sign reversed 1, the per-program split dropped 2, one cell pointed at
the wrong list 3, the 16-address cut lowered to 8 turns 1 red, a second cell
leaking into `--cell intact-both` 1, one population under both mean labels 1.

**One defect in a transcript here, found by re-running rather than by reading,
and fixed in place because a transcript that does not paste-and-run is not a
transcript.** §3's `across` command was missing the trailing `\` that joins its
`--old-b` line to the four `--*-registers` lines after it, so the command as
written would have run half its arguments and stopped — with the shell treating
the next line as a new command, which is the shape §3's own preamble cites
`ec/annotations/xdata-06c2-06db-timers.md` for. The block was re-recorded from
the run that produced the figures above, so it carries the backslash now; every
other `console` block in this file was checked the same way and was already
sound, and §7's `across` invocation has always had it.


**The tree's own runner stands at 35 suites and 1076 tests**, re-measured on
the merged tree rather than carried over: this change adds no `test_*.py` and so
no row to `tools/README.md`'s table, and the two figures it started from — 32
suites and 974 tests — moved entirely because merges landed in the same
window, #849 (`a00fe940`) with `ec/tools/test_check_doc_figure_pins.py` at 44
tests, #851 (`a02de81b`) with `ec/tools/test_xdata_carry_notice.py` at 15,
#887 (`bb4c1d27`) with `ec/tools/test_census_test_line_pins.py` at 41 and
#850 with `TheExportOwnershipClusters`'s two cases in
`ec/tools/test_xdata_cluster_names.py`, so
`32 + 1 + 1 + 1 = 35` and `974 + 44 + 15 + 41 + 2 = 1076` closes with nothing
left over. That is the whole delta; `tools/README.md`'s own ninth merged-tree
note carries the same arithmetic and the runner prints `35 suite(s) run, 1076
tests; one or more FAILED`. *(This paragraph first read 33 suites and 1018 tests,
which
is the tree #852 branched from — #849's, before #851 landed — then 34 suites
and 1033 tests, which is the tree this change merged into and one merge before
#887's, and then 35 and 1074, which is the tree this change merged into once
#850's two cases were beside it. All three superseded pairs are left visible here
per [`../findings.md`](../findings.md) §4a-4d rather than edited out, and the
figures that stand are the ones re-measured on the tree this lands on.)* One
suite is red and was red before this change:
`ec/tools/test_check_cluster_citations.py`, at 48 tests, on
`xdata-cluster-names-guard-off-recipe.md:220` — **#822's** write-up, named in
that file's own closing note, in `tools/README.md`'s merged-tree note and in
`docs/findings.md` §59, and reproducible on a clean `origin/main` at the same
48 tests and the same line. This change neither fixes it nor adds to it:
`check_cluster_citations.py` reports the same two citations before and after,
and none of them is in a file this one added.

**`test_check_cluster_citations.py` is the constraint that shaped this file, and
it is a real one.** That suite's `test_committed_prose_matches_committed_census`
runs the checker over every committed markdown file and requires exit 0, and the
checker resolves ids, keys and names against the **committed** census only. A
file that prints a guard-off generation beside the committed one — which is
exactly what the transcripts here do — "names clusters from two rankings at
once" and goes red, which is how
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md)
was rejected once already. So every table here keeps `cluster_key` in the
**first cell**, which keeps the row out of the census-row rule, and no table
pairs a rank with an address.

**The `rank A` / `rank B` columns are the same constraint read from the other
side, and they were run rather than reasoned about.** §3's preamble has always
said ranks are printed beside the key because the rank moved and the key did
not; adding the columns is what makes the sentence true of the table rather than
only of §7's swept block, and §7 is the precedent that a row may carry a
`main-ec-NNN` pair beside a `cluster_key` without the checker's membership rule
reading it. What the columns do **not** do is add an address column, which is
the pairing that would go red: the checker holds a *membership* claim, and a
rank beside an address reads as one. The table above keeps `cluster_key` first,
introduces no address column, and the checker reports the same two `#822`
disagreements before and after this change and no new one.
