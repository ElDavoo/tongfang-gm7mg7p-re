# The 94 flipped clusters: both named mechanisms are refuted, and what the working page does show instead (issue #884)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over committed text, with every scratch output under
`/tmp` and `git status --porcelain` printing nothing after the runs. Same
framing as
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):3 and
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):11.

[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §4 closed its
accounting with a stated limit: 94 of 94 keys named, the arithmetic closing
over four terms, and *"what is **not** derived is why a re-partition closes the
guard's delta on those 71 particular small clusters and opens it on those 23."*
§8 repeats it as "the re-partition itself is not derived, only located". This is
that step, and **the answer is two nulls and one located thing that is not a
mechanism** — stated at their counts, in §4, §5 and §6 below.

The measurements come from a new `cause` mode on the read-only tool
[`ec/tools/xdata_moved_ranks.py`](../../ec/tools/xdata_moved_ranks.py), which
`pair` and `across` already live in. It reads the same eight inputs and writes
nothing. `across`'s printed output is byte-unchanged; this is a mode beside it,
not a block inside it, for the reason
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §3 gives.

**What is new here beyond the issue's question, and is flagged as mine.** The
issue asks for a per-cell count and a mechanism-or-null. It does not ask for a
control, and without one the per-cell count is not decidable: "most of the rows
line up" is true of every cell and of the census as a whole, so a rate the two
cells that *did not* flip show at the same rate is not a mechanism. So **the two
control cells — 266 moved in both, 40 intact in both — are counted exactly the
way the two flipped ones are**, beside a population of all 439 guard-off keys.
The plan calls this the difference between a measurement and a story; it is
also the only reason §4 below can say *null* rather than *mostly*.

## 1. M0 — the tree has not moved since #852, so the figures are comparable

The 366 was re-derived from commit `e169a0e4` and the present tree gives 315;
`xdata-moved-ranks-fall.md` §1–§2 is the transcript. This branch runs the same
commands again because a `cause` figure is only comparable to a `pair` figure
if both came off the same tree. They did.

```console
$ git cat-file -e e169a0e4a736956f35af5ffff65e997154c76bdd^{commit} && echo present
present
$ python3 ec/tools/xdata_register_map.py --check
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5

$ git worktree add --detach /tmp/xdata-old e169a0e4a736956f35af5ffff65e997154c76bdd
$ cd /tmp/xdata-old && python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/old-off-clusters.csv --out-registers /tmp/old-off-registers.csv
  names: seeded 8, exact 0, carried by overlap 2, tied, not carried 0, with no name 429
    main-ec-001 carries mode-oem-init by overlap, Jaccard 0.97 from k7497cf885614 -- re-key annotations/xdata-cluster-names.csv if the name moved
    main-ec-022 carries page-0300 by overlap, Jaccard 0.78 from k3fdd14ddea2e -- re-key annotations/xdata-cluster-names.csv if the name moved
wrote /tmp/old-off-registers.csv: 1171 rows
wrote /tmp/old-off-clusters.csv: 439 rows
  main-ec: 1062 distinct addresses, 13964 references, 388 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5

$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/new-off-clusters.csv --out-registers /tmp/new-off-registers.csv
  names: seeded 8, exact 0, carried by overlap 1, tied, not carried 0, with no name 436
    main-ec-002 carries mode-oem-init by overlap, Jaccard 0.97 from kefb63d82f8c7 -- this run's ids are not the committed census's (--no-eq-guard), and annotations/xdata-cluster-names.csv is anchored to the committed one, so a carry here is arithmetic over a different clustering, not a re-key request
wrote /tmp/new-off-registers.csv: 1326 rows
wrote /tmp/new-off-clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
```

**`366/64/439` and `315/124/445` reproduce, and so does the 71/266/23/40 flip
table**, so every number in
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §2–§4 still describes
this tree. The one figure that is *not* reproduced anywhere is in §5 below, and
it is a disagreement with the tree's prose rather than with a measurement.

## 2. The population, which is what makes a rate a rate

`cluster_key` is a content hash over program and sorted membership
([`xdata_register_map.py:2355`](../../ec/tools/xdata_register_map.py)), and both
guard-off censuses compute it the same way, so a guard-off row of the 430-row
generation is matchable into the 445-key guard-off census of the 439-row one
without the two rankings agreeing about any rank. That is what makes the lookup
below well-founded rather than a coincidence hunt.

```console
$ python3 ec/tools/xdata_moved_ranks.py cause \
    --label-a 'the 430-row pair' --label-b 'the 439-row pair' \
    --old-a /tmp/xdata-old/ec/annotations/xdata-clusters.csv --new-a /tmp/old-off-clusters.csv \
    --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/new-off-clusters.csv \
    --old-a-registers /tmp/xdata-old/ec/annotations/xdata-registers.csv --new-a-registers /tmp/old-off-registers.csv \
    --old-b-registers ec/annotations/xdata-registers.csv --new-b-registers /tmp/new-off-registers.csv
cause the 430-row pair -> the 439-row pair
  page 0x0300-0x05FF; the added set is 155 address(es)

  the population: 439 guard-off key(s) in the 430-row pair, 445 in the 439-row pair
    408 of the first reappear in the second under the same key, 31 only in the first, 37 only in the second
    the rank delta of those 408: 0 on 56, +/-1 on 20, +/-2 on 3, further on 329; mean +6.80, range -9..+12
    their members: 1219 membership(s) over 1171 distinct address(es); 274 of them in the page, held 275 time(s) -- one address is in two rows, which is a `pd` holder and a `main-ec` holder of the same byte; the 439-row pair's holds 425
    the pd side: committed identical (50 pd row(s) either way); guard-off identical (51 pd row(s) either way)
```

**Three things are established here and every rate below is read against them.**

- **A guard-off row reappears in the other generation 408 times in 439 — 92.9%** —
  and when it does it lands *far* away in rank, mean **+6.80**. The population
  is not a quiet baseline. Any claim of the form "the rows mostly line up" has
  to beat 92.9% and a mean displacement of nearly seven ranks, and a reader who
  is handed only the per-cell number would not know that.
- **The page holds 274 distinct addresses held 275 times.** One address is in two
  rows of the same census, which is the `pd`-and-`main-ec` case `swept_report`
  already exists for. It is why the coverage figures in §6 are counted distinct
  and the rate figures counted as memberships, and the line prints both rather
  than picking one.
- **The `pd` side of both pairs is the same partition, byte for byte** — 50 `pd`
  rows in each committed census, 51 in each guard-off one. §7 says what that
  decides.

## 3. The four cells, each counted the same way

For each key, the row its committed rank carried in the generation where the
rank moved, and where that row's membership went in the other generation. The
`intact in both` cell is included on purpose: it has **no substitution at all**,
so its reappearance rate is its own committed membership coming back, and the
mode says so on the cell's line rather than leaving it to be read as a result.

```console
  per cell: the row the key's rank carried in the generation that moved,
  and where that row's membership went in the other generation

  moved -> intact: 71 key(s), main-ec 71 -- subject: the 430-row pair
    the subject row reappears in the other generation: 60 (main-ec 60) -- rank 0 on 2, |delta| <= 2 on 10, further on 50
    it does not: 11 (main-ec 11) -- split across rows 5, absorbed into one larger row 6, an address with no holder 0
    the subject rows' 273 address(es): 102 in the page, 0 of the 155 added
    the subject rows by size: 1 1 1 1 4 4 4 4 5 7   the committed rows at the same ranks: 1 1 1 1 4 4 4 4 5 6
    they touch 102 distinct page address(es) of the 274 in the 430-row pair's guard-off census

  moved in both: 266 key(s), main-ec 246, pd 20 -- subject: the 430-row pair
    the subject row reappears in the other generation: 252 (main-ec 232, pd 20) -- rank 0 on 20, |delta| <= 2 on 29, further on 223
    it does not: 14 (main-ec 14, pd 0) -- split across rows 0, absorbed into one larger row 14, an address with no holder 0
    the subject rows' 450 address(es): 86 in the page, 0 of the 155 added
    the subject rows by size: 1 1 1 1 1 1 1 1 2 3   the committed rows at the same ranks: 1 1 1 1 1 1 1 1 2 3
    they touch 86 distinct page address(es) of the 274 in the 430-row pair's guard-off census

  intact -> moved: 23 key(s), main-ec 23 -- subject: the 439-row pair
    the subject row reappears in the other generation: 22 (main-ec 22) -- rank 0 on 0, |delta| <= 2 on 0, further on 22
    it does not: 1 (main-ec 1) -- split across rows 0, absorbed into one larger row 0, an address with no holder 1
    the subject rows' 42 address(es): 5 in the page, 2 of the 155 added
    the subject rows by size: 1 1 2 2 2 2 2 2 2 2   the committed rows at the same ranks: 1 1 2 2 2 2 2 2 2 2
    they touch 5 distinct page address(es) of the 425 in the 439-row pair's guard-off census

  intact in both: 40 key(s), main-ec 10, pd 30 -- subject: the 430-row pair  [the row is the committed membership itself, so there is no substitution]
    the subject row reappears in the other generation: 40 (main-ec 10, pd 30) -- rank 0 on 31, |delta| <= 2 on 35, further on 5
    it does not: 0 (main-ec 0, pd 0) -- split across rows 0, absorbed into one larger row 0, an address with no holder 0
    the subject rows' 216 address(es): 18 in the page, 0 of the 155 added
    the subject rows by size: 1 1 2 2 3 3 3 4 6 9   the committed rows at the same ranks: 1 1 2 2 3 3 3 4 6 9
    they touch 18 distinct page address(es) of the 274 in the 430-row pair's guard-off census
```

**"Does not reappear" is one event with three shapes, and the split is worth
naming once.** A membership that comes back unchanged is the same content hash,
so it is *findable by key* — which means "still co-clustered together" and
"reappears" are the same event rather than two, and the only case left for
"still together" is absorption into a larger row. So the three shapes are: a
larger row holding all of it, a row holding only some of it, or a row in the
other generation that has none of it. The 71 split 6 / 5 / 0; the 266 split
14 / 0 / 0.

### The four cells beside each other, with the denominators they need

A cell of 71 keys whose rows hold four addresses and a cell of 266 whose rows
hold one are not comparable as raw counts, so every measure carries its
denominator, and the population is the last column for the same reason.

| measure | moved → intact | moved in both | intact → moved | intact in both | population |
|---|---:|---:|---:|---:|---:|
| reappears | 60/71 **84.5%** | 252/266 94.7% | 22/23 95.7% | 40/40 100.0% | 408/439 92.9% |
| reappears within 2 ranks | 10/60 **16.7%** | 29/252 11.5% | 0/22 0.0% | 35/40 87.5% | 79/408 19.4% |
| addresses in the page | 102/273 **37.4%** | 86/450 19.1% | 5/42 11.9% | 18/216 8.3% | 274/1219 22.5% |
| addresses of the added set | 0/273 **0.0%** | 0/450 0.0% | 2/42 4.8% | 0/216 0.0% | 0/1219 0.0% |

The population's added count is 0 by construction, and the mode prints that as a
parenthetical rather than leaving a bare `0/1219` to be read: the added set is
the difference between the two guard-on universes, so no address in it is a
member of any row of the older census.

## 4. Rank displacement — a null, and the control is what makes it one

The issue's first mechanism: *"if that exact row reappears in the 439-row
generation at a neighbouring rank — or is simply now a member of a cluster one
row over — then the 'delta closed' because the partition reordered."*

**It reappears, and it does not land nearby.** 60 of the 71 substitutions are
found in the other guard-off census, and of those 60, **10** are within two
ranks and **2** are at the same rank. The control cell and the population both
sit at the same rate:

| | reappears | of those, within 2 ranks |
|---|---:|---:|
| moved → intact (71) | **84.5%** | **16.7%** |
| moved in both (266) | 94.7% | 11.5% |
| population (439) | 92.9% | 19.4% |

**So the "neighbouring rank" reading accounts for at most 10 of the 71, and it
does so at the rate at which the whole census reappears.** The 71 are, on this
measure, slightly *less* likely to have their substitution come back at all
(84.5% against 92.9%) and, when it does, no more likely to land nearby (16.7%
against 19.4%). Neither difference is in the direction the mechanism needs, and
neither is large enough to carry a claim on 71 keys either way.

The `intact → moved` cell is the sharper null: **0 of its 22 reappearing
substitutions are within two ranks**, against 19.4% for the population. On 22
keys an expected 4.3 and an observed 0 is not a finding, and it is printed
because a reader scanning for a mechanism would otherwise stop there.

**The claim is therefore: rank displacement is not what closed the delta on
those 71, at 10 of 71 against a population rate of 79 in 408.** The rows did
reorder — the mean displacement of +6.80 in §2 is real and large — but
reordering is what happened to *every* guard-off row in the census, and so it
cannot be what distinguishes these 71 from the 266 that kept moving.

## 5. The 155 added addresses — a null for the 71, and one key of the 23

The issue's second mechanism, from
[`xdata-cluster-names.csv`](../../ec/annotations/xdata-cluster-names.csv)'s
`mode-oem-init` note: *"The pass added 155 addresses across the same
0x03xx-0x05xx working page, which merged three of the page's clusters into
one."*

The 155 set is `set(on_b) - set(on_a)` over the two guard-on registers CSVs —
the membership behind the "adds 155 address(es)" line
[`xdata_moved_ranks.py`](../../ec/tools/xdata_moved_ranks.py)'s
`registers_report` already prints the size of.

**Not one of the 71's 273 substitution addresses is in it. Not one of the
control's 450.** For the 23 that started moving, **2 of 42** are — which is
**one key of 23**, not a mechanism:

| `cluster_key` | the row that took its rank | membership | of the 155 |
|---|---|---|---:|
| `ka01f369d385f` | `ked71c48c3c52` | `0x036E 0x036F` | 2 |

So across all 94 flipped keys, **the 155 added addresses reach exactly one of
them, and it is one of the 23 that started moving rather than one of the 71 that
stopped.** The claim is that the added set cannot be the cause of the 71: it
contributes none of their addresses, and it contributes none of the 266
movers-that-stayed-moved's either, so a mechanism resting on it has nothing to
act on in the set it is supposed to explain.

**One correction to the tree's prose, recorded here rather than edited into the
CSV.** That note says the pass added the 155 *"across the same 0x03xx-0x05xx
working page"*. Measured against the two registers CSVs, **151 of the 155 are on
that page and 4 are not**: `0x060E`, `0x060F`, `0x0646`, `0x0647`. This does not
change any count above — the page range is a `--page` flag and the added set is
derived from the CSVs, not read from the note — but "across the page" reads as
a closed statement and is 151 in 155. Per
[`../findings.md`](../findings.md) §4a-4d the note is left as it is and the
disagreement sits beside it; `annotations/xdata-cluster-names.csv` is not this
work's to edit, and §5 of this file is where a re-deriver should read the count
from.

## 6. What the working page does show, and the two things that stop it being a mechanism

This is not a mechanism either, and it is reported because it is the one
measured difference that survives, not because it is the answer.

**At the same ranks, the substitutions that closed the delta moved onto the
page, and the control's did not move as far.** The comparison is paired: each
subject row against the *committed* row at its own rank, so the rank is held
constant by construction and the only thing that differs is the membership.

| | the committed row at that rank | the substitution that replaced it | shift |
|---|---:|---:|---:|
| moved → intact (71 ranks) | 45/271 **16.6%** | 102/273 **37.4%** | **+20.8** |
| moved in both (266 ranks) | 66/452 14.6% | 86/450 19.1% | +4.5 |
| intact → moved (23 ranks) | 2/42 4.8% | 5/42 11.9% | +7.1 |

Both mover cells shift *onto* the page; the 71 shift about five times as far.
And the two flip directions are opposite in kind: the 71 touch **102 distinct
page addresses of their own census's 274**, while the 23 touch **5 of the newer
census's 425** — the two censuses do not have the same page, and the 151 added
addresses of §5 are most of the difference between 274 and 425.

**Two things stop that being read as the cause, and the mode prints both.**

**One — the cells do not hold rows of the same size.** A ten-address row has ten
chances to sit on the page where a one-address row has one, and the 71's ranks
hold size-4-ish rows (`1 1 1 1 4 4 4 4 5 7`) while the 266's hold size-1 rows
(`1 1 1 1 1 1 1 1 2 3`). Broken out by row size, with the committed row at the
same rank beside it and the row count in brackets:

```console
  page rate by the size of the row, the committed row at the same rank
  written first, and the subject row count in brackets. A band holding a
  handful of rows is not a rate, which is what the brackets are for.
    band               moved -> intact           moved in both         intact -> moved
    size 1     28.0 ->  40.0 (  25) 18.0 ->  24.5 ( 188) 50.0 ->  75.0 (   4)
    size 2                           - 20.4 ->  30.4 (  46)  0.0 ->   5.3 (  19)
    size 3-4   15.5 ->  27.6 (  25)  9.4 ->  17.2 (  21)                       -
    size 5-8   25.0 ->  31.1 (  16)  3.3 ->   1.7 (   9)                       -
    size 9+     1.6 ->  61.7 (   5) 10.9 ->   0.0 (   2)                       -
```

In every band where both cells have a reasonable number of rows — size 1 at 25
and 188, size 3-4 at 25 and 21 — **both cells shift onto the page by a similar
amount** (+12.0 and +6.5 at size 1, +12.1 and +7.8 at size 3-4). The one band
where the 71 separate is **size 9+, and it is five rows against two**.

**Two — those five rows are the top of the ranking, and the page is down to a
few of them.** The five size-9+ rows carry **37 of the cell's 102** page
addresses; the other 66 carry 65 of 213, or **30.5%**, against the control's
19.1% and the population's 22.5%. Named, because "the large clusters" is the
adjective that §4 of
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) already refuted once and
should not be reintroduced:

| `cluster_key` | rank | size | subject row | in page | destination |
|---|---|---:|---|---:|---|
| `k66512c56e77b` | main-ec-012 | 10 | `k7b6fc2234771` | 4 | reappears |
| `k733571bb7f66` | main-ec-010 | 12 | `k0ebf038645b0` | 12 | split |
| `ka07bfc4f80cd` | main-ec-006 | 13 | `k4cd9afeeb040` | 9 | split |
| `ke96d2e265d5d` | main-ec-008 | 12 | `kea0c67af9b51` | 0 | reappears |
| `kea0c67af9b51` | main-ec-007 | 13 | `k45909c137449` | 12 | absorbed |

Three of them are wholly page rows and two of the five carry more page
addresses than the row they replaced. **Two of these five are the same clusters
seen from the other side of the pair** — `k733571bb7f66` is the committed key
of a `moved in both` row, and `kea0c67af9b51` is the subject row of
`ke96d2e265d5d`'s — so the large page clusters are being permuted among the top
ten ranks, and which of them lands in the quiet cell rather than the moving one
is close to arbitrary. This is `mode-oem-init`'s neighbourhood: the one hand
name that moves, at `main-ec-001`/`main-ec-002`, the ranks just above these.

**The claim, at its count: the guard's substitution at those 71 ranks sat on the
working page more often than the control's did — 37.4% against 19.1%, measured
at the same ranks — and that difference is 5 rows of the 71 plus a size
distribution the two cells do not share.** It says where the substitutions
landed. It does not say the page moved them there, and it is not offered as the
cause.

## 7. The `pd` diagnostic, which the tool treats as a precondition

§2 printed that the `pd` side of both pairs is byte-identical: 50 `pd` rows in
each committed census, 51 in each guard-off one, same keys and same membership.
That makes a `pd` flip arithmetically impossible, and the per-cell split
confirms it rather than leaving it to be checked: **the `moved → intact` and
`intact → moved` cells are 71 `main-ec` and 23 `main-ec`, with `pd` 0 in both**,
while the two control cells hold 20 and 30 `pd` keys.

So of the 94 flipped keys, **none is a `pd` cluster**, and that is what a
byte-identical `pd` partition predicts. The mode prints the comparison as its
own line so that a non-zero `pd` cell would be visible as a *disagreement* with
it rather than as a surprise — and the `--self-test` fixture carries both
branches, identical and different, so the line cannot pass by being one string.

## 8. What this does not do

- **No CSV, YAML, threshold or assertion moves.** `xdata-clusters.csv`,
  `xdata-registers.csv`, `xdata-cluster-names.csv` and `registers.yaml` are
  byte-untouched. `assertGreater(len(moved), 300)` stays at
  [`test_xdata_cluster_names.py:392`](../../ec/tools/test_xdata_cluster_names.py),
  and §5 of
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) is still the argument
  for leaving it there. The guard-off runs wrote only to `/tmp`.
- **No re-partition is derived, and no cause is asserted.** The two named
  mechanisms are refuted at their counts in §4 and §5. §6 is a located
  association with two things named against it, not a third mechanism. What
  *moved* a row is a question about the co-reading matrix under the added
  addresses, and this does not compare the matrix either way — so "the page
  moved it" is not available as a reading of this file.
- **The page test is a necessary-condition proxy, and is not a demonstration.**
  It says which side of a substitution those addresses landed on. Whether the
  co-reading matrix re-clustered a row *because* of them is not decidable from
  two censuses, and this file does not claim it.
- **The 151-in-155 correction is not an edit.** §5's disagreement with
  `xdata-cluster-names.csv`'s note is recorded beside the note, per
  [`../findings.md`](../findings.md) §4a-4d. The CSV is not this work's.
- **No live hardware, EC, BIOS or Windows step**, because nothing here needs
  one. No live run is planned, claimed or implied. The one thing this reads that
  a reader might not expect is `ec/firmware/GMxMGxx_11.800`, and reading a file
  is not an observation of a machine.
- **Nothing is opened in another repository.** There is no upstream patch here
  to submit.
- **No gate is wired**, matching
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §8: the tool is a
  read-only investigation aid, and a gate call is an upstream change to
  `tools/run-tests.sh` and a re-copy, not a line here.

## 9. The test that proves it

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test
  ok    a rank whose guard-off row holds a different membership is moved, and the two that hold their own membership are not
  ...
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
  all checks passed
```

**The known-answer run is §1 through §6 above.** The fixtures are over a fourth
pair of censuses, chosen so each case can go red: a substitution that reappears
one rank over, one built from the added addresses and with no holder in the
generation that predates them, one control cell carrying a split and an
absorption, a row whose addresses land in two `pd` rows while one of them also
has a `main-ec` home, a cell with no substitution at all, and both branches of
the `pd` comparison. Four mutations were tried against them — flattening the
per-program index, emptying the added set, zeroing the population's rank
deltas, and widening the page to the whole address space — and each turned two
or three checks red.

`across`'s printed output is unchanged and is still what
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §3 and §7 transcribe;
`pair`'s is unchanged and is still what §2 there transcribes.

```console
$ python3 ec/tools/xdata_register_map.py --check && python3 ec/tools/xdata_register_map.py --self-test
... 1326 register rows, 439 cluster rows, both exit 0 ...
$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
............................
Ran 28 tests in 12.590s

OK
$ bash tools/run-tests.sh
34 suite(s) run, 1033 tests; one or more FAILED.
```

**The one red suite is the one that was red before this change, and this change
adds nothing to it.** `ec/tools/test_check_cluster_citations.py` fails 1 of its
**48** tests on
[`xdata-cluster-names-guard-off-recipe.md:220`](xdata-cluster-names-guard-off-recipe.md)
— **#822's** write-up, named in that file's own closing note, in
`tools/README.md`'s merged-tree note, in
[`../findings.md`](../findings.md) §59 and in
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §9. `check_cluster_citations.py`
exits 1 for those same two citations (`0x0464` and `0x0465`), and its output is
**byte-identical with and without this file** — checked by running it with the
new file moved aside and diffing. The runner's totals are the **34 suites /
1033 tests** that #852 recorded, re-measured on this tree rather than carried
over: this change adds no `test_*.py` and so no row to `tools/README.md`'s
table, so that file is not touched either.

**That same test is the constraint that shaped this file**, the same one that
shaped [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §9. The checker
resolves ids, keys and names against the **committed** census only, so a
sentence that pairs a 4-hex-digit address with a cluster key is held to the
*committed* membership — and the guard-off generation printed beside the
committed one is what got
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md)
rejected once already. So every table here keeps `cluster_key` in the **first
cell**, no table pairs a rank with an address, and the one place a guard-off
membership appears (§5) states it against a guard-off key rather than against
the committed key it replaced.
