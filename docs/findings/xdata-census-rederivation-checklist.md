# The xdata census re-derivation checklist: what a re-export moves, and what to do about it (issue #820)

Issue #753 added the first test in the tree that goes **red because the census
was re-derived**, and wrote the response down in a comment inside the test. The
three places the tree tells a person or an agent to re-derive that census did
not mention it — the issue's third is two sentences on one page, which is why
there are four pointers and not three. This file is the checklist, and the four
pages that carry the procedure now point at it, so a trip is a **known cost of
the procedure** rather than a surprise found halfway through it.

Nothing here is a hardware claim. No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved — same framing as
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):11.
Every figure below is the output of a command over committed text (`--check`,
`--self-test`, and the two suites that read these CSVs), all re-measured on this
tree at 1,326 register rows and 439 cluster rows.

## 1. The tripwire, and the response

`ec/tools/test_xdata_cluster_names.py:339`
`TheGuardOffRegeneration.test_the_census_is_the_one_6a_measured` compares the
guard-off census against **§6a's published figures** rather than against a fresh
run of the same recipe, which would agree with itself by construction. Its own
comment states the rule at `:378-380`:

> The denominators are pinned with the numerators because a re-derivation that
> changes them has changed what §6a measured, and the response to that is to
> re-derive §6a, not to move a number here.

**All seven of its figures are functions of `ec/decompiled/**` and
`ec/firmware/GMxMGxx_11.800`** — **eleven since #850, which added §2a's four
per-subset direction rows, and thirteen counting the two §6b cluster counts
`TheExportOwnershipClusters` holds beside it** — so a re-export moves all of
them at once. The
precedent for what that costs is the #279 re-derivation note at
`ec/annotations/xdata-06c2-06db-timers.md:799-814`: a full paragraph of
superseded figures, kept visible, because that pass re-derived every *level* in
§6a's table and none of its *differences*.

## 2. The figures, in two groups — eleven rows pinned by the test, eighteen measured

*(Fifteen when #820 wrote this file: seven in §2a and the eight §2b named. #849
made §2b a command's output rather than prose, and #850 added four rows to §2a
and did not remove any from §2b — the §2b rows stayed where they are and are now
marked, because a re-deriver looks for a figure in §2b whether or not anything
holds it, and a table that had quietly dropped four rows would be a worse place
to look. **The two counts are not the same count and the two sides' headings
used one each**: eleven plus eight is table *rows* across §2a and §2b, which is
the "nineteen" one side wrote down, and eighteen is §2b's *figures* — four of
its rows carry two each.)*

### 2a. Eleven, pinned by the test — a trip here is the machine saying the census moved

Seven of these were here when this file was written; the last four arrived with
#850 and are the ones in bold.

| figure | what it is | where §6a prints it |
|---|---|---|
| `833` | references entering `write`, all three programs † | `xdata-06c2-06db-timers.md:785` |
| `210` of `1,326` | addresses whose `write` column changes | `:786` |
| `0` of `1,326` | addresses whose `refs` column changes | `:969` |
| `0x08A8` `84/44` guard-off, `126/2` committed | read / write | `:787` |
| `0x0843` `84/42` guard-off, `126/0` committed | read / write | `:788` |
| `394` guard-off, `389` committed | main-EC clusters at threshold 0.50 | `:789` |
| `set(off) == set(on)` | the 1,326-row address universe both runs are over | the heredoc's two `of 1326` denominators, `:952-969` |
| **`3,948` / `3,206`** | **main-EC `write` references, over the 1,169 `program=main-ec` rows** | **`:781`** |
| **`7,189` / `7,935`** | **main-EC `read` references, over that same arm** | **`:782`** |
| **`193` / `142`** | **PD-image `write` references, over the 108 `program=pd` rows** | **`:783`** |
| **`279` / `239`** | **`write` references for the 49 `program=both` rows** | **`:784`** |

† **The word, corrected 2026-09-26 (issue #890); the figure is unchanged.** The
`833` row read *references leaving `write`* and the arithmetic behind it was
always a signed sum of *guard-off minus committed*, which is positive: the
references **enter** `write` and none leave, because `--no-eq-guard` lifts one
exclusion and lifting an exclusion only admits. §6a's row is corrected in place
with the wrong wording left visible, and the measurement behind the word — over
both censuses, 210 addresses' `write` rises and none falls — is in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md).
Nothing else in either table changes.

The four bold rows carry their arm's denominators in the same assertion, for the
reason the `210` and the `0` carry theirs: `1,169` addresses / `13,891` refs,
`108` / `603`, and `49` / `1,202`, each equal in the guard-off and the committed
census because the guard re-buckets occurrences and moves no address. `program`
is a **partition** of the 1,326, so these are the *terms* of the `833` rather
than a second reading of it — which is what a re-export that moved a direction
between the PD set and the main-EC set, or moved an address from one arm to
another, now trips. Before #850 it moved the `210` and left the `833` standing.
**Two of those denominators are §6a's and one is not, and the assertion's
message now says which is which:** `:781` prints `1,169 addresses, 13,891 refs`
for the `main-ec` arm and `:783` prints `108 addresses, 603 refs`, but `:784`
says only "the 49 addresses in both images" — the `1,202` is the sum of `refs`
over the `program=both` rows, equal in both censuses by the same partition
argument and added by the assertion rather than transcribed from the page.

### 2b. Eighteen figures, measured: eighteen held, and what that verdict does not reach

**This split is a command's output, not prose.**
`python3 ec/tools/check_doc_figure_pins.py` against this file with `--section
2b` resolves every figure below to one of four verdicts, prints the `file:line`
that decided it, and exits non-zero if the marking here disagrees with the
measurement. Re-run it after any edit below; the method and its limits are in
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md), and **every `unheld` there
is "not found by this method", never "absent"** — the same caveat
`ec/annotations/registers.yaml` carries for a static scan.

**An all-held column is a fact about the method, and on two of the eighteen it
is the wrong answer for the figure on the page.** The tool resolves a figure to a
*`file:line` that compares against it*; it cannot see which census that line
measures. The `157`/`858` row is held by `ORACLE["extmem_pd_distinct"]` /
`["extmem_pd_refs"]`, which measure the **default** census's token spellings —
§6b prints that pair for its own **de-duplicated** run, and `OWNERSHIP` carries
no `pd_*` key at all, so nothing measures that run's pd width. Different
measurement, same digits, and it is the narrower of the two gaps. **And one
figure still open is not in these tables at all**, because §6a does not print
it: the guard-off run's pd cluster count `51`. It is named below, and it is why
"eighteen held" is not "nothing left to do".

#### §6b's console block, `ec/annotations/xdata-06c2-06db-timers.md:901-904`

**§6b's `--export-ownership` run, not §6a's**, which is easy to misread as
part of the table below:

| figure | what it is | line | verdict | pin |
|---|---|---|---|---|
| `1326` | the `wrote … after-registers.csv` row count | `:901` | held | `ORACLE["distinct"]`, `ec/tools/xdata_register_map.py:743`, asserted `:3864-3869` |
| `440` | the `after-clusters.csv` row count | `:902` | held | `OWNERSHIP["clusters"]`, `ec/tools/xdata_register_map.py:1442`, asserted `:4347-4354` |
| `1218` | main-EC distinct addresses | `:903` | held | `ORACLE["main_distinct"]`, `ec/tools/xdata_register_map.py:744`, asserted `:3864-3869`; and, for the de-duplicated run this row is about, `OWNERSHIP["main_distinct"]`, `ec/tools/xdata_register_map.py:1414`, read by the "and its main-EC half is" check at `:4315-4319` |
| `9320` | main-EC references | `:903` | held | `OWNERSHIP["main_refs"]`, `ec/tools/xdata_register_map.py:1414`, asserted `:4315-4319` |
| `157` / `858` | pd distinct addresses / references | `:904` | held | `ORACLE["extmem_pd_distinct"]` / `["extmem_pd_refs"]`, `ec/tools/xdata_register_map.py:738`, asserted `:3555-3572` — **but for the *default* census, not this run's; see the paragraph above** |
| `390` / `50` | main-EC / pd cluster counts | `:903-904` | held | `ec/tools/test_xdata_cluster_names.py:734`, `TheExportOwnershipClusters.test_the_440_splits_the_way_6b_prints_it` — **#850**; the `440` above is their sum and is held to it there |

#### §6a's table, `ec/annotations/xdata-06c2-06db-timers.md:779-790`

| figure | what it is | line | verdict | pin |
|---|---|---|---|---|
| `3,948` / `3,206` | main-EC `write` references, guard removed / as committed | `:781` | held | `ec/tools/test_xdata_cluster_names.py:473`, `test_the_census_is_the_one_6a_measured` — **#850** |
| `7,189` / `7,935` | main-EC `read` references | `:782` | held | `ec/tools/test_xdata_cluster_names.py:490`, same case — **#850** |
| `193` / `142` | PD-image `write` references | `:783` | held | `ec/tools/test_xdata_cluster_names.py:507`, same case — **#850** |
| `279` / `239` | references in `write` for the 49 addresses in both images | `:784` | held | `ec/tools/test_xdata_cluster_names.py:524`, same case — **#850** |
| 43 addresses, `4,966` refs | `main-ec-003` (this block), **identical either way** | `:790` | held | the `size` and `refs` cells of `main-ec-003`, `ec/annotations/xdata-clusters.csv:4`, compared cell-for-cell by `check()` at `ec/tools/xdata_register_map.py:3289` (`:3304`) |

**The four §6a rows were `unheld` on this page until #850, and the reason is the
shape of the measurement rather than a missing number.** Their per-subset sums
are computed inline in §6a's heredoc, and the census they come from is the
guard-off run, which is written to `/tmp` and committed nowhere — so there was no
committed cell for `--check` to hold them to either, and the method read them
`unheld` however carefully a case looked at them. #850 made them the **terms of
the `833`**, which is what §2a says above and what makes them trip at all, and
asserted each with the denominator §6a prints beside it.

*(The paragraph this one replaces said the same thing in the present tense, and
is kept here verbatim rather than deleted, per §4a-4d — it is what the table
above read `unheld` beside until #850, and its claim that the denominator checks
"cover §2a's seven, not these" is the claim #850 falsified: they are at
`ec/tools/test_xdata_cluster_names.py:339` and cover eleven now. Its `:307` is
the pre-#850 file's, which is what that tree said, and the eight it counts are
the four §6a direction rows' eight figures and nothing else:)*

> **The eight `unheld` figures are unheld because the per-subset sums are computed
> inline in §6a's heredoc and asserted nowhere.** The census they come from is the
> guard-off run, which is written to `/tmp` and committed nowhere, so there is no
> committed cell for `--check` to hold them to either. They are *not found* by the
> method above; the recipe's own denominator checks live in
> `ec/tools/test_xdata_cluster_names.py:307` and cover §2a's seven, not these.

**`390` and `50` are a residual the tree no longer has, and the paragraph that
called them one is kept here verbatim** rather than deleted, per §4a-4d. It was
true of the tree it was written on, and the call it records as the next one was
taken:

> **`390` and `50` are the residual, and only their sum is pinned.** `440` above
> is their total, so a re-deriver can cross-check the pair by subtraction — but
> either half can move without the other, and nothing in the tree catches that
> today. A `"clusters_by_program": {"main-ec": 390, "pd": 50}` key on `OWNERSHIP`
> would close the pair, and it is a *new* pin rather than a correction of a false
> claim, so it is not folded in here. The write-up records it as the next call.

*(#850, 2026-09-25. `TheExportOwnershipClusters.test_the_440_splits_the_way_6b_prints_it`
holds the split against the clusters CSV the run itself wrote, and holds it to
`OWNERSHIP["clusters"]` as well, so the breakdown and the total cannot drift apart;
a second case reads the two `N clusters at threshold 0.5` figures back out of
that run's own stdout, which is the only way a transcript renumbered the way
§6b's once was is caught rather than believed. **A `clusters_by_program` key on
`OWNERSHIP` was the other way to close the pair and was not taken** — the
in-process census is a stronger pin than a constant, because the constant is a
promise and this is a measurement.)*

**Read every figure above off the page before quoting it; three are commonly
transcribed wrong.** `14,838` is *not* a per-program total — it is §6b's own
table cell (`main-EC refs | 14,838 | 9,320`, `:866`), and the per-program figure
beside it is `9320`. It is also the one figure in this file with a name for
where it is held: `ORACLE["main_refs"]` (`ec/tools/xdata_register_map.py:744`),
asserted at `:3864-3869`. `394` is not unpinned at all: it is the guard-off
main-EC cluster count §2a already pins, and §6b's `390` is a *different* number
that looks like its predecessor — and, since #850, a *held* one. The cluster row
here is `440`, not `445` (445 is the guard-off census at
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):168,
a different run of a different flag). These are the figures a paste silently
gets wrong, and a checklist that carried the wrong one would be worse than no
checklist.

*(Correction, 2026-09-25, issue #849. The heading this replaces read **"Eight,
unpinned — these are the ones that decay silently"** — eight being the count of
table *rows* above, and the section listing eighteen figures between them. It
called every one of them unpinned, and that was wrong in both directions: eight
are held by the cheap gate, so a re-deriver was being sent to redo work the tree
already does, and `9320` / `390` / `50` — the ones that really were unpinned on
the tree this was written on — were left looking like company. `9320` was the
sharpest case, because it was `OWNERSHIP["main_refs"]`, and **a value in a
constant that no check reads is a promise wearing the costume of a pin**; that
key is now read by the "and its main-EC half is" check at
`ec/tools/xdata_register_map.py:4315-4319`, so the console block was six held
against two unheld rather than five against three. **#850 has since closed the
other four**, so the heading above counts eighteen held and none unheld, and the
only figures this section still cannot vouch for are the `157`/`858` pair and the
`51`. The wrong classification is kept here verbatim, per
[`../findings.md`](../findings.md) §4a-4d:)*

> ### 2b. Eight, unpinned — these are the ones that decay silently
>
> `ec/annotations/xdata-06c2-06db-timers.md:779-790`, §6a's table:
>
> | figure | what it is | line |
> |---|---|---|
> | `3,948` / `3,206` | main-EC `write` references, guard removed / as committed | `:781` |
> | `7,189` / `7,935` | main-EC `read` references | `:782` |
> | `193` / `142` | PD-image `write` references | `:783` |
> | `279` / `239` | references in `write` for the 49 addresses in both images | `:784` |
> | 43 addresses, `4,966` refs | `main-ec-003` (this block), **identical either way** | `:790` |
>
> And the console block at `:869-872` — **§6b's `--export-ownership` run, not
> §6a's**, which is easy to misread as part of the table above:
>
> | figure | what it is | line |
> |---|---|---|
> | `1326 rows` / `440 rows` | the two `wrote …` lines | `:869-870` |
> | `1218` distinct addresses, `9320` references, `390` clusters | `main-ec` total at threshold 0.5 | `:871` |
> | `157` distinct addresses, `858` references, `50` clusters | `pd` total at threshold 0.5 | `:872` |

**The heading was an overclaim a second time, and it is worth keeping both
corrections rather than only the last.** "Eight, unpinned" was wrong about three
of the eight rows — the `4,966` is a `refs` cell in the committed
`xdata-clusters.csv` that `--check` compares cell for cell, `1326`/`440` are
`ORACLE`/`OWNERSHIP` keys asserted in `--self-test`, and `157`/`858` are
`ORACLE["extmem_pd_*"]` — for the **default** census, which is a partial hold and
not a whole one. Counted by row and before either issue's change, that is **five
wholly unheld, two wholly held, and one — `157/858/50` — held for part of its
contents.** #849 closed the `9320`; #850 closed the four §6a rows and the `390`
and the `50` with them. **What is left is the `157`/`858` pair alone, and it is
left for a narrow reason**: `ORACLE["extmem_pd_*"]` measures the PD half of the
**default** census's token spellings and `OWNERSHIP` carries no `pd_*` key at
all, so nothing holds §6b's de-duplicated `157`/`858`.

*(Corrected at review, 2026-09-25, and the wrong version stays visible per
§4a-4d. The heading above first counted **four** of the eight rows as wholly
held "and two more are now", and this paragraph first counted them four unheld,
two wholly held and two partly held; it also gave the first two figures of the
`main-ec` line to `OWNERSHIP["main_distinct"]`/`["main_refs"]` "asserted at
`:3840-3842`". That assertion reads `OWNERSHIP["distinct"]`/`["refs"]` —
`1326`/`10178`, the census-wide pair — and `grep -n 'OWNERSHIP\['
ec/tools/xdata_register_map.py` showed the `main_*` pair defined and read by
nothing in the tree. `9,320` was asserted nowhere at all, and the `1218` that is
asserted is `ORACLE["main_distinct"]` for the **default** census, beside
`ORACLE["main_refs"]` = `14,838` where §6b prints `9,320`. The seventh row was
therefore unheld for the pair rather than partly held, which is what moves the
count from four/two/two to five/two/one and put `1218`/`9320` on the open list
beside `157`/`858` and the `51` below. **#849 then closed that pair in the same
window** — the "and its main-EC half is" check reads both keys, over the
de-duplicated census, which is the row's own run — so the open list that
correction left is one figure shorter than it reads here, and the wrong version
stays.)*

**And the figure that is still open is not in the tables above.** The guard-off
run prints a `pd` cluster count of `51` beside §6a's `394`, and nothing holds
that one — the case pins the main-EC arm of a pair and not the pd arm, which is
the same shape of gap the four direction rows were, and `assertEqual` away. §6a
does not print it in its table, which is why §2b's tables cannot carry it and why
this paragraph has to. The derivation of every figure in this section, and the
list of what is still open, are in
[`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md).

## 3. The other four items

**`BUCKET_TOTALS`, five figures** — `ec/tools/xdata_register_map.py:1362-1363`:
`read 8826`, `write 3587`, `read+write 2482`, `passed-to-call 534`,
`address-taken 267`. They cross-check by sum: `8826 + 3587 + 2482 + 534 + 267 =
15696 = ORACLE["refs"]`, which is the cross-check the comment above them states.
The page cites this oracle at `xdata-06c2-06db-timers.md:770-772`, but prints
the older `:668` in its prose; **cite the live line, `:1362`.**

**The two committed CSVs** — `ec/annotations/xdata-clusters.csv` at **439** rows
and `ec/annotations/xdata-registers.csv` at **1,326**. `--check`
(`ec/tools/xdata_register_map.py:3289`) compares every `read`, `write`, `refs`
and `addrs` cell against a fresh generation from the committed tree, cell for
cell. It is the only mode that does.

**The names-file re-key** — 9 keys in `ec/annotations/xdata-cluster-names.csv`,
**anchored to the committed census**: the two CSVs as committed, which is the run
`--check` reproduces — the `==` guard on, no `--export-ownership`, `--threshold 0.5`.
A run that re-classifies occurrences is a different clustering and cannot be made
into that one: `--export-ownership` on this tree moves 39 of the 439 committed
`cluster_key`s and breaks 5 of the 9 hand names outright
(`xdata-06c2-06db-timers.md:883-887`), so its three `carried by overlap` lines are
arithmetic over ids that were never the committed ones. **The notice carries that
distinction on the line, so read the tail and not the count** — on the committed
census a carry ends `-- re-key annotations/xdata-cluster-names.csv if the name
moved` and *is* the request; on any other shape it names the flag that took the
run off the anchor, names the file, and says it is not a re-key request
(`xdata_register_map.py:3253` is the emitting function, `census_shape` the
predicate, `carry_advice` the clause). All of it is **on stderr** so the CSVs stay
pipeable — **so read it off the terminal, not off a redirected `--check` pipe**,
the pipe that keeps the CSVs usable being the same pipe the hint is kept out of. A
committed-shape re-derivation that moves a key leaves the names file attached to a
membership that has gone, which is what `--self-test`'s check at `:4128` exists to
catch ("every key … names a cluster of the committed census"). **Re-key by hand;
there is no command that writes that file for you.**

*(#850, 2026-09-25, and the correction this section carries was to citations
rather than to a claim. #850 found every `file:line` here stale on `main` before
it landed — the emitting function cited at `:2968` and the print at `:2984-2987`
when they were at `:2960` and `:2976-2979`, `--self-test`'s stale-key check cited
at `:4049` against a `:4030`, and `--check`'s own `def` named nowhere at all,
because the re-key print was cited in its place — and repointed them in a
paragraph of its own, on the grounds that a checklist whose subject is citations
that have moved is the worst place for one that has. #851 and then #872 rewrote
this paragraph to say what a carry is a claim *about*, which answers the same
drift better than repointing it, and every `file:line` above is measured on the
tree that carries it. **#850's repointed numbers are not carried across**: the
sentences they annotated are gone, and leaving them beside a paragraph that
already carries current ones would be a second stale citation in the one place
this tree forbids them.)*

**The `> 300` floor** — `ec/tools/test_xdata_cluster_names.py:588`,
`assertGreater(len(moved), 300)`, measured at **315** today: **15 of headroom**.
It is left there deliberately, and the argument is
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):170-175:
lowering the floor to buy room "would be the one change that makes the suite look
green while checking less". So read a trip as **"the floor is where it was left,
here is the new number"**, not as a discovery. The count has already fallen once,
**366 → 315** (`xdata-cluster-names-guard-off-recipe.md:345-352`, with the
earlier pairs kept beside it; not this test file, whose `:381-394` is the pointer
to this checklist). The tree records the fall without attributing a cause; a
re-derivation that lands addresses in already-large clusters would move fewer
membership sets, which is the obvious shape of it, but that is a guess and not a
measurement.

> **The guess above has since been measured, and it is wrong** (issue #852).
> [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) re-derives the
> intermediate pair from `e169a0e4` — it reproduces 366 / 64 / 439 exactly, so
> the two figures are one measurement's worth of each — and finds that the 94
> clusters that changed their guard-off membership did **not** grow: a
> `cluster_key` is a hash of the membership, so all 400 keys shared by the two
> committed censuses have byte-identical membership and the `grew` column is `0`
> on every flipped row. "The large clusters" is also not the shape of it: 5 of
> the 23 committed clusters of 8 addresses or more flipped, and the largest, at
> 152 addresses, is not among them. What moved is the guard's *membership
> delta* — 7.66 address-slots on average over the 71 that went quiet, 0.00 after
> — and the guard's per-address effect is unchanged (210 addresses, 833
> references, both figures identical in the two generations). The floor stays
> where it is, argued from that measurement rather than from the headroom.
>
> **The step that measurement named and did not take has since been taken, and
> both mechanisms it named are refuted** (issue #884).
> [`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md) follows each
> moved rank's substitution into the other generation's guard-off census.
> Rank displacement accounts for at most **10 of the 71** substitutions landing
> within two ranks — **10 of the 60** that reappear, at the rate the whole
> census reappears at (**79 in 408**) —
> and the 155 added addresses reach **none of the 71** and **one key of the 23**.
> Both are stated at their counts there, each against the two cells that did not
> flip — which is what turns a per-cell number into a null rather than a
> mechanism.

> **There is no third pair to find, and the count above is the floor's to this
> day** (issue #885).
> [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md) went looking
> for the generation before `e169a0e4` and did not find one. Two commits carry a
> 427-row census. At `e6c88864` it is a file its own tree does not derive —
> `--check` exits 1 there, and that commit's own `--self-test` fails on "the
> committed CSVs match a fresh generation" — and that tree derives the
> **430-row** census, so measuring there re-measures `e169a0e4` (**366**, **0**
> clusters flipped, the same 210 addresses). At `1fcd5f1e`, the only other
> 427-row commit, the tree does derive 427 rows and the pair is **not
> measurable with the committed tools**: `cluster_key` first exists at
> `e6c88864`, the census commit right after it, and `xdata_moved_ranks.py`
> raises `KeyError: 'cluster_key'` on any earlier census. Two points, not three,
> and nothing here says `moved` decays. **Run
> `--check` on the tree you are about to measure**: a stale committed census is
> a pair whose `moved` counts the guard and the drift together, and the two are
> separable only because the guard cannot change `refs`.

## 4. The order the work happens

1. **`python3 ec/tools/xdata_register_map.py --check` — first.** It is the only
   mode that compares the committed CSVs to a fresh generation, and
   `check_ghidra_tooling` has run it since #256. **Since #823 (`244c992b`) it runs
   step 2's mode as well** — the arm at
   `.github/scripts/agent-gates.sh:261-263` reads
   `*xdata_register_map.py) python3 "$tool" --check && python3 "$tool" --self-test || rc=1`,
   and the comment above it now ends "So the honest description of what is gated
   here is no longer the two CSVs" (`:253-254`). A re-deriver is therefore caught
   by the cheap gate itself, before the suites in step 3 are reached.
2. **`python3 ec/tools/xdata_register_map.py --self-test`.** The `BUCKET_TOTALS`
   and direction-invariant oracles behind §2b and §3.
3. **The two suites that read these CSVs** — `ec/tools/test_xdata_cluster_names.py`
   and `ec/tools/test_xdata_register_map.py`, both collected by
   `bash tools/run-tests.sh`. The first's `setUpClass` builds the guard-off census
   with `--no-eq-guard` and is the longest run in the tree; budget for it. Since
   #850 it builds a **second** census as well — `export_ownership_census()` runs
   `--export-ownership` to another temp dir, ~1 s more — because §2b's last row
   is that flag's and is not derivable from the first. Both go to a temp dir: each
   flag refuses to run without scratch `--out-` paths, which is the refusal
   contract the sibling page is about.
4. **Re-derive §6a's figures from the two scratch CSVs**, per its own printed
   heredoc (`:952-969`), which prints the 833 / 210 / 0 triple itself.
5. **Re-key `xdata-cluster-names.csv`** if a **committed-shape** run — step 1's
   `--check`, or a bare write at the default threshold with the guard on —
   reports a key that is no longer `seeded`/`exact` for its own cluster, which is
   what `--self-test` reports as `stale` (§3). **§6b's `--export-ownership` run is
   not a trigger.** Its three `carried by overlap` lines are that run's *own* ids,
   and the tail on each says so in as many words; a run measured to break five of
   the nine names cannot be reporting that three of them moved. Re-key by hand;
   there is no command that writes that file for you. *(#850 first wrote this
   step as the one line "if step 1's *stderr* (§3) or a scratch run moved a
   key", which is what §3 was pointing at before #851 gave a carry a
   census-shape test — on that wording `--export-ownership` *is* a trigger, which
   is the re-key of nine correct keys that #872 measured and closed.)*
6. **Re-run `--check`** to confirm.

A `bash .github/scripts/agent-gates.sh` run covers **all of steps 1 and 2** —
that is what #823 added — and the cheap half of step 3 (`doc links` and `python
syntax` are what touch anything written by hand). So a re-derivation that moves
the committed CSVs now turns the cheap gate red on its own, and the runner in
step 3 is the second witness rather than the first.

## 5. What this checklist is not

**Every figure above is today's snapshot, the way §6a's re-derivation note is**
— a total pasted into a file is a snapshot of the merge it was measured on, and
this one has been overtaken before. Nothing here asserts what a re-derivation
*would* produce. §6b's own correction (`:917-931`) is the cautionary case, and
it is not a hypothetical one: a transcript there was written out in the
half-renumbered shape of a run that never happened, and the correction that
finally caught it came from noticing the ids and the counts disagreed. Re-derive
from the two scratch CSVs, print what the command printed, and correct beside
the wrong version if one slips in — do not hand up a block that reads like a run
nobody ran.

It is not a retraction and it corrects nothing. The #279 note's superseded
figures stay exactly where they are, per [`../findings.md`](../findings.md) §4d;
this file adds a pointer beside them, not a replacement for them.

And nothing in it needs hardware, Windows, an image, or a register read back —
the deliverable is this document and its four pointers, all of it unattended.
