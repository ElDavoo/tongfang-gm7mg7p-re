# The 427-row census is stale at `e6c88864` and unreadable at `1fcd5f1e`, and the guard's per-address effect is measured a third time (issue #885)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure below is
the output of a command over committed text, with every scratch output under
`/tmp` and `git status --porcelain` printing nothing after the runs. The
censuses this reads are files; the guard-off ones are regenerations of committed
trees by `xdata_register_map.py --no-eq-guard`, which reads
`ec/decompiled/**` and `ec/firmware/GMxMGxx_11.800` as files. Same framing as
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):3-11.

The issue asks for a third data point on `moved`, to sit beside the one
observed fall, and to say whether it agrees in direction. **The answer is that
there is no third data point to take, and §5 gives the reason.** Two commits
carry a 427-row census, and neither of them can be paired. At `e6c88864`, the
commit the issue named, the committed file had already fallen behind its own
tree and that tree derives the *430-row* census. At `1fcd5f1e`, the other
427-row commit, the tree does derive 427 rows — and that is the census commit
immediately *before* `e6c88864` added `cluster_key`, so
`xdata_moved_ranks.py` cannot read its census at all; §5 records that negative
with its transcript rather than asserting it. Measured like for like, the
427-era tree and the 430-era tree are the same census: same `cluster_key` set,
same membership for every key, same 210 perturbed addresses, `moved` **366** in
both, and **zero** clusters that flip between them.

**A note on the number 366 before anything else, because in a file about the
427-row census it means three different measurements and a reader will meet them
in the wrong order.** `ec/tools/check_cluster_citations.py`:17-20 carries a
`366` beside 427, 425, 59 and 413: that is issue #274's **threshold-0.45
re-run**, where 59 of 427 ids are intact and 366 name a different membership.
It is not this file's 366. The other two are *the same number reached twice*:
the 430-row pair's 366, re-derived in
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md), and the 427-era
tree's own guard-on/guard-off 366, which §4 below shows to be that same
measurement rather than a new one. Every occurrence below says which.

The measurements come from [`ec/tools/xdata_moved_ranks.py`](../../ec/tools/xdata_moved_ranks.py),
which this work left alone — it needed nothing here, and §3 is a measurement
with it. *(Merged-tree note, added when this landed beside #886's: that fix
does edit the tool, so "unchanged" means unchanged **by this work**.)* Its
change is confined to `swept_report()` and the self-test, and `swept_report()`
is reached only under `--swept` — which no command below passes — so neither
`pair` nor `across` reads a line of it and every figure here is the one its
own tree produced.

## 1. The issue's first check comes back negative, and what replaced it

`--no-eq-guard` was added by #528 (`db6d7d2d`), and
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §1 establishes it is an
ancestor of `e169a0e4`. Whether it reaches back past the 430-row era to
`e6c88864` is not established anywhere in the tree. **It does not.**

```console
$ git log --format='%H %ad %s' --date=short -- ec/annotations/xdata-clusters.csv \
    | while read c rest; do echo "$c $(git show $c:ec/annotations/xdata-clusters.csv | wc -l)"; done
6bf9c2341b28ff8db1f0976a74d4ac2c9e04231e 440
e169a0e4a736956f35af5ffff65e997154c76bdd 431
f0be5173d2c9f6807cf5aaaaabb5de78902f8516 431
d8525eae42501ca99054be5631742ca08b5be417 431
e30dbd2db37d89e5aca9d2b527909edc173d0a64 431
f4fb9d82664f50b9f8735f7712d2d5f093d20470 431
ba8a3f81b7009309459e9a80b13b12baf867ee4d 431
05af8c321252ffa6c353ec4014394550f1a7b360 431
88a0e0ba6edd62f10161146322cf940a6e6f821f 431
0b04a8b93da25a50421af538ab71930330b4dbf2 431
7896c5f82d7c1cd6616b893c50bcabed74f10c07 431
37140548cb3f10986517bae6575591b4f06d1d0c 431
e6c88864505068a5bcd43d1042bd22b3911503ee 428        # the 427-row census the issue names
1fcd5f1e12cfaf369b55e65347cd56a537d0a342 428        # the only other 427-row census
6ff6c6d2827143057db63d3221bc663dcd4e4ca6 427
40744da28ff859b5a0c574bc750eff6f81204bd7 427
50bc4b5114c99baf62a178fdb96e4eb046475c64 427
906c5bc1dd40d333c0d12ec8343cad05222df3fd 427
c9e0c2c45de692a4b8bb72f5ff3b2d308478e087 427
6c32923aeb6a2a7afc20f26b81db1df40bfe1bed 436
a34c3d6ea4b9e08bc77a8d705f87bb95bf4d0327 436
a121ff63a3db48031c1bedc7fe521cee6ba1e196 436

$ git merge-base --is-ancestor db6d7d2d e6c88864505068a5bcd43d1042bd22b3911503ee; echo $?
1
$ git merge-base --is-ancestor db6d7d2d e169a0e4a736956f35af5ffff65e997154c76bdd; echo $?
0
$ git grep -l -- '--no-eq-guard' e6c88864505068a5bcd43d1042bd22b3911503ee -- | wc -l
0
```

The row counts are lines, so `428` is a 427-row census with a header. **All
twenty-two lines are above and none is elided**, because the abbreviated form
hides what matters here: the file has been committed at **five** distinct
sizes, not the three the issue's 427 → 430 → 439 names. Those three are real
and they are the later era. In full, oldest first, the sizes run **435 → 426 →
427 → 430 → 439** — five 426-row commits, two 427-row, eleven 430-row, three
435-row and one 439-row, 22 in all. `e6c88864` is the **second** 427-row
commit, not the first, and the 430-row census the issue means is `e169a0e4`'s,
the last of the eleven. §5 is where the missing sizes matter.

`--no-eq-guard` appears **nowhere** in the 427-era tree: not in the tool, not
in a docstring, not in the recipe. So the pair needs a route the 430-row pair
did not.

**The route is a back-port of #528's own diff, and it is checkable rather than
asserted.** The `==` guard's *logic* is not new at #528 — the flag is a switch on
an exclusion that #206 added, and what #528 changed is the plumbing. The three
functions the switch threads through are **byte-identical** at the 427-era tool
and at #528's parent, so #528's diff is a mechanical fit rather than an
invention:

```console
$ git show db6d7d2d -- ec/tools/xdata_register_map.py > /tmp/528-tool.patch
$ git worktree add --detach /tmp/xdata-427 e6c88864505068a5bcd43d1042bd22b3911503ee
HEAD is now at e6c88864 give a cluster an identity that is not its rank, and a
name that carries across a regeneration (#298)
$ cd /tmp/xdata-427 && cp ec/tools/xdata_register_map.py /tmp/xdata_register_map.py.orig
$ patch -p1 --no-backup-if-mismatch < /tmp/528-tool.patch
patching file ec/tools/xdata_register_map.py
Hunk #3 succeeded at 854 (offset -59 lines).
... 9 more, all with the same offset ...
Hunk #12 succeeded at 2655 (offset -59 lines).
$ ls ec/tools/*.rej
ls: cannot access 'ec/tools/*.rej': No such file or directory

$ diff -u /tmp/xdata_register_map.py.orig ec/tools/xdata_register_map.py > /tmp/applied.patch
$ for p in /tmp/528-tool.patch /tmp/applied.patch; do
    grep -E '^[+-]' "$p" | grep -vE '^(\+\+\+|---)' | sed 's/^@@.*@@//' | sort > "$p.norm"; done
$ diff /tmp/528-tool.patch.norm /tmp/applied.patch.norm && echo "identical change set"
identical change set
```

Twelve hunks, no rejects, and the resulting change set is **line for line
#528's own** — the same 82 added and 8 removed lines. The patched tool's
`--self-test` then differs from the unpatched tool's by exactly the two
assertions #528 added, and nothing else:

```console
$ cd /tmp/xdata-427 && cp /tmp/xdata_register_map.py.orig ec/tools/_orig427.py
$ diff <(python3 ec/tools/_orig427.py --self-test 2>&1) \
       <(python3 ec/tools/xdata_register_map.py --self-test 2>&1)
25a26,27
>   ok    --no-eq-guard flips exactly the 3 `==` snippets in CLASSIFIER_SHAPE and no other (flipped 3)
>   ok    and each flipped `==` snippet becomes a `write`, which is the pre-#178 miscount this flag exists to reproduce
$ rm ec/tools/_orig427.py
```

Two added lines, which are #528's two assertions, and no other difference
anywhere in either output: the two copies fail identically, and both exit 1 —
**on nine pre-existing `FAIL` lines apiece, not one**, of which §2 takes up the
one this file is about.

So the flag is genuinely re-derivable from a named commit at the 427 era, with
its behaviour pinned three ways: the change set is #528's, the guard-on path is
byte-unchanged, and the flag's two refusals are inherited with it — refused with
`--check` and `--self-test`, and refused unless given scratch outputs, both
verified before any measurement below was taken.

**What the issue's fallback was, and why it was not taken.** The alternative was
to compare the committed 427 CSV against *today's* tree's guard-off regeneration
and label the result a cross-era comparison. That route was not needed, and it
would not have answered the question asked: it confounds the guard with every
census-relevant change to the tool and the decompiled tree between the two
commits, and those inputs demonstrably drift — the two trees' own guard-on
censuses differ in reference totals on 8 clusters (§4). The back-port instead
puts the guard on a named commit with a patch whose every line is checked, which
is what makes the result in §4 attributable. The cost of the route taken is one
patched file inside a throwaway worktree, and §2 shows it was that file's own
`--self-test` that caught the thing the issue did not anticipate.

## 2. The 427-row census is stale in its own commit, and the tool there said so

This is the finding that reshapes the rest, and it is not visible from the file
alone. The 427-era tool's own `--check` does not agree with the 427-era
committed CSV:

```console
$ cd /tmp/xdata-427 && python3 ec/tools/xdata_register_map.py --check; echo "exit=$?"
/tmp/xdata-427/ec/annotations/xdata-registers.csv differs from a fresh generation
  (1172 on disk vs 1172 generated) -- run without --check to rewrite
/tmp/xdata-427/ec/annotations/xdata-clusters.csv differs from a fresh generation
  (428 on disk vs 431 generated) -- run without --check to rewrite
exit=1
```

(The two row-dump lines the tool prints after each of those are elided: they are
one whole census row each, and they name ranks and address lists together, which
this file's own citation constraints forbid reproducing outside a transcript.)

**The same commit's own `--self-test` carries a check for exactly this, and it is
red there** — this is not an artifact of the patch:

```console
$ cd /tmp/xdata-427 && python3 ec/tools/xdata_register_map.py --self-test 2>&1 | tail -3
  FAIL  the committed CSVs match a fresh generation (run without --check after
        changing anything the census reads)
  430 clusters at threshold 0.5; 1062 main-EC and 157 PD addresses
  FAILURES ABOVE
```

So at `e6c88864` the tree derives **430** clusters and the file carries **427**:
a three-row gap, opened by that commit. The 430-era commit is green, which is
what makes the asymmetry the point rather than a general property of the tool:

```console
$ cd /tmp/xdata-430 && python3 ec/tools/xdata_register_map.py --check; echo "exit=$?"
/tmp/xdata-430/ec/annotations/xdata-registers.csv: 1171 rows match a fresh generation
  from the committed tree at threshold 0.5
/tmp/xdata-430/ec/annotations/xdata-clusters.csv: 430 rows match a fresh generation
  from the committed tree at threshold 0.5
exit=0
```

**How far this is scoped, which is a spot check and not a census.** Seven of the
twenty-two commits that have touched the file, run through the same `--check` at
their own trees:

| commit | committed rows | `--check` | fresh |
|---|---:|---|---|
| `6c32923a` | 435 | `0` | 1172 register rows and 435 cluster rows match |
| `6ff6c6d2` | 426 | `0` | 426 rows match |
| `1fcd5f1e` | 427 | `1` | 428 on disk vs 428 generated — same count, different content |
| `e6c88864` | 427 | `1` | 428 on disk vs **431** generated |
| `37140548` | 430 | `0` | green |
| `e169a0e4` | 430 | `0` | green |
| `6bf9c234` | 439 | `0` | 1326 register rows and 439 cluster rows match |

**Two of the seven are red, and they are the two 427-row commits.** The gap is
not "this tool's `--check` is unreliable on old trees": the 435- and 426-row
commits below them and the 430- and 439-row commits above them are green at
their own trees. The two reds are not the same defect either. At `e6c88864` the
row count itself is behind — 427 committed against 430 derived. At `1fcd5f1e`
the count matches and the **content** does not: the tree derives 427 rows, so a
427-row derived census does exist, and this file is not the one that measured
it (§5 says why, and says "not measured" rather than "no such generation"). *Why*
either file was committed that way is not established here and is left as a
follow-up; what is measured is that `e6c88864` and `1fcd5f1e` are the two
commits where the committed census and that commit's own tree disagree, and that
the disagreement is a red `--self-test` line in each. The other fifteen commits
that touched the file were not run, so **this is not a claim that the other
fifteen are green.**

## 3. Three pairs at `e6c88864`, because the committed half is not the tree

Because the committed file is stale, "the pair at `e6c88864`" does not name one
measurement. Three are run, so the guard's part and the stale file's part can be
told apart rather than added together. The guard-off regeneration is common to
all three.

```console
$ cd /tmp/xdata-427 && python3 ec/tools/xdata_register_map.py \
    --out-clusters /tmp/427-on-clusters.csv --out-registers /tmp/427-on-registers.csv
wrote /tmp/427-on-registers.csv: 1171 rows
wrote /tmp/427-on-clusters.csv: 430 rows
  main-ec: 1062 distinct addresses, 13957 references, 380 clusters at threshold 0.5
  pd: 157 distinct addresses, 861 references, 50 clusters at threshold 0.5

$ cd /tmp/xdata-427 && python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/427-off-clusters.csv --out-registers /tmp/427-off-registers.csv
wrote /tmp/427-off-registers.csv: 1171 rows
wrote /tmp/427-off-clusters.csv: 439 rows
  main-ec: 1062 distinct addresses, 13957 references, 388 clusters at threshold 0.5
  pd: 157 distinct addresses, 861 references, 51 clusters at threshold 0.5
```

| pair | old | new | `moved` | `intact` | same size | shares no address | membership delta | §6a `write` / `refs` / refs entering `write` † |
|---|---|---|---:|---:|---|---|---:|---|
| **literal** — committed vs guard-off | 427 | 439 | **379** (main-ec 359, pd 20) | 48 | 357 | 377 | 1,836 | 216 / 16 / 842 |
| **guard** — guard-on vs guard-off | 430 | 439 | **366** (main-ec 346, pd 20) | 64 | 351 | 364 | 1,623 | 210 / 0 / 833 |
| **staleness** — committed vs guard-on | 427 | 430 | 370 (main-ec 370, pd 0) | 57 | 355 | 369 | 1,691 | 9 / 16 / 9 |

All three close (`366 + 64 = 430`, `379 + 48 = 427`, `370 + 57 = 427`), and no
committed rank is missing from either regeneration in any of them, so nothing is
folded into a count to make it add up.

**The three runs behind that table are printed here**, so the table is a summary
of transcripts on the page rather than the page's only record of them. Each is
this tree's `ec/tools/xdata_moved_ranks.py` over the four CSVs named above, in the
table's own order:

```console
$ python3 ec/tools/xdata_moved_ranks.py pair --label 'the literal pair' \
    --old /tmp/xdata-427/ec/annotations/xdata-clusters.csv --new /tmp/427-off-clusters.csv \
    --old-registers /tmp/xdata-427/ec/annotations/xdata-registers.csv \
    --new-registers /tmp/427-off-registers.csv
pair the literal pair
  committed  /tmp/xdata-427/ec/annotations/xdata-clusters.csv: 427 rows
  guard-off  /tmp/427-off-clusters.csv: 439 rows
  moved      379  (main-ec 359, pd 20)
  intact     48
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 357 hold a guard-off row of the same size and 377 share no address with it
  guard-off membership delta over the 427 rank(s) the two censuses share: 1836 address-slots
  §6a: address universe identical (1171 rows); write changes 216 of 1171; refs changes 16 of 1171; references entering write 842, leaving write 0, net +842
  closes: 216 + 0 = 216, over the 216 address(es) whose write column changed
... 427 more: the per-rank table, one row per rank the two censuses share ...

$ python3 ec/tools/xdata_moved_ranks.py pair --label 'the guard pair' \
    --old /tmp/427-on-clusters.csv --new /tmp/427-off-clusters.csv \
    --old-registers /tmp/427-on-registers.csv --new-registers /tmp/427-off-registers.csv
pair the guard pair
  committed  /tmp/427-on-clusters.csv: 430 rows
  guard-off  /tmp/427-off-clusters.csv: 439 rows
  moved      366  (main-ec 346, pd 20)
  intact     64
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 351 hold a guard-off row of the same size and 364 share no address with it
  guard-off membership delta over the 430 rank(s) the two censuses share: 1623 address-slots
  §6a: address universe identical (1171 rows); write changes 210 of 1171; refs changes 0 of 1171; references entering write 833, leaving write 0, net +833
  closes: 210 + 0 = 210, over the 210 address(es) whose write column changed
... 430 more: the per-rank table, elided the same way ...

$ python3 ec/tools/xdata_moved_ranks.py pair --label 'the staleness pair' \
    --old /tmp/xdata-427/ec/annotations/xdata-clusters.csv --new /tmp/427-on-clusters.csv \
    --old-registers /tmp/xdata-427/ec/annotations/xdata-registers.csv \
    --new-registers /tmp/427-on-registers.csv
pair the staleness pair
  committed  /tmp/xdata-427/ec/annotations/xdata-clusters.csv: 427 rows
  guard-off  /tmp/427-on-clusters.csv: 430 rows
  moved      370  (main-ec 370, pd 0)
  intact     57
  committed ranks the guard-off census does not carry: 0
  of the moved ranks, 355 hold a guard-off row of the same size and 369 share no address with it
  guard-off membership delta over the 427 rank(s) the two censuses share: 1691 address-slots
  §6a: address universe identical (1171 rows); write changes 9 of 1171; refs changes 16 of 1171; references entering write 9, leaving write 0, net +9
  closes: 9 + 0 = 9, over the 9 address(es) whose write column changed
... 427 more: the per-rank table, elided the same way ...
```

**Every column of the table above is a line of one of those three blocks**, so
each of the three is re-derivable from the page rather than asserted by it. The
per-rank table each run appends is the one thing cut: one row per rank the two
censuses share — 427, 430 and 427 of them, the committed row count of each pair —
carrying `cluster_key`, name, both ranks, size and delta, none of which a column
above reads. The cut is mine, not a flag the tool honours, and nothing else in
the three blocks is altered. Two details of the output are the tool's wording
rather than this file's, and a reader needs both to read the staleness pair:
**`guard-off` labels whichever census `--new` names**, so in that pair it labels a
guard-*on* regeneration of the 427-era tree and the file path beside it is the
disambiguation; and the §6a line prints `entering`, `leaving` and `net` as three
numbers, which is the corrected convention the footnote below is about.

† **The direction word, corrected 2026-09-26 (issue #890), in both this table's
header and §6's.** They read *references leaving `write`*; the tool's convention
is committed → guard-off and the sum behind the figure is `off − on`, so the
references **enter** `write` and none leave. **Every number in both tables is
unchanged** — 842, 833, 833 and 9, and the 210 / 0 / 9 the rows pair them with —
and only the word moved; the measurement, the correction and the per-address
property behind it are in
[`xdata-write-direction-correction.md`](xdata-write-direction-correction.md).
**No transcript on this page carries the old wording**: the table above is three
`xdata_moved_ranks.py pair` runs — its `moved` / `intact` columns, the same-size
and shares-no-address counts, the membership-delta figure and the §6a triple are
that report's, field for field — and the three runs are printed above it, so the
wording this footnote corrects is on the page and is the corrected one. The only
other `pair` run the page shows is the `KeyError` in §5, which never reaches the
line. Re-running the three printed the corrected word, which is why there is
nothing here to leave as a record of the old one, and the correction above is the
whole of it.

**The three separate cleanly, and the separation is the useful part.** The
`refs` column is the discriminator, because the guard moves it on none of the
three pairs measured here — `0` `refs` against 210 addresses perturbed, where
the stale file's 9 addresses move `refs` on 16, so the two causes are separable
on that column alone. **The guard re-buckets an occurrence that is already
counted, which is why that is the expected answer, and it is measured here
rather than derived**: the three runs below are what establish it, and the
`refs` side then closes the same way the address side does. The stale file moves
`refs` because it is a different generation's file rather than a re-bucketing of
this one.

```console
  guard       perturbs 210 addresses, changes refs on  0
  staleness   perturbs   9 addresses, changes refs on 16
  literal     perturbs 216 addresses, changes refs on 16
```

(Those three lines are a summary of the three `pair` runs above rather than a
run's output — the per-address sets the `refs` figures are counted over are the
ones each run perturbs, gathered here so the set arithmetic below has a form to
read.)

Over the address sets, `|guard| = 210`, `|staleness| = 9`, `|guard ∩ staleness| = 3`,
and `|guard ∪ staleness| = 216` — the literal pair's figure, which is that union
and not a sum: **210 + 9 − 3 = 216**. The `refs` side closes the same way,
`0 + 16 − 0 = 16`. So the literal pair's 379 is not a third measurement of the
guard; it is the 366 with a stale file mixed in, and the mixture is 9 addresses
of it.

## 4. The 427-era tree and the 430-era tree are the same census

This is the result, and `xdata_moved_ranks.py across` states it in the same
shape [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §3 used, with the
guard-on side as pair A so the comparison is like for like — at `e169a0e4` the
committed file *is* the guard-on generation, which is why §1 of that file could
use the committed CSV there and cannot here. **The two `across` comparison blocks
in this section are the tool's whole output, unedited and unwrapped** — the
rank-shift block and the flip table included — so a reader can diff either
against the command beside it. Every other `console` block on the page that is
not a run's output says so where it appears: the two summaries, §3's `perturbs`
block and §4's four-comparison block below, are arithmetic over the CSVs §3
names, and §3's three `pair` blocks are runs' output with one part of each cut
and the cut marked in the block.

```console
$ python3 ec/tools/xdata_moved_ranks.py across \
    --old-a /tmp/427-on-clusters.csv --new-a /tmp/427-off-clusters.csv \
    --old-a-registers /tmp/427-on-registers.csv --new-a-registers /tmp/427-off-registers.csv \
    --old-b /tmp/xdata-430/ec/annotations/xdata-clusters.csv \
    --new-b /tmp/430-off-clusters.csv \
    --old-b-registers /tmp/xdata-430/ec/annotations/xdata-registers.csv \
    --new-b-registers /tmp/430-off-registers.csv \
    --label-a 'the 427-row pair (guard-on)' --label-b 'the 430-row pair'
across the 427-row pair (guard-on) -> the 430-row pair
  keys in both committed censuses: 430; in one only: 0 / 0
     0  moved in the 427-row pair (guard-on), intact in the 430-row pair
   366  moved in both
     0  intact in the 427-row pair (guard-on), moved in the 430-row pair
    64  intact in both
  of the one-sided keys, 0 moved in the 427-row pair (guard-on) and 0 moved in the 430-row pair
  closes: 366 - 366 = 0, over the four terms: (0 - 0) + (0 - 0) = 0

  the flipped set's size distribution, against the census: no rows
                                            the census:  1 1 1 1 1 1 2 2 3 5
  of the 21 committed cluster(s) of 8 addresses or more, 0 flipped; the largest committed cluster is 109 addresses
  of the 8 of 16 or more, 0 flipped
  shared keys whose committed membership differs between the two censuses: 0 of 430 -- a key is a hash of the membership, so this is zero by construction and is printed rather than assumed

  §6a across the two generations, over the per-address columns:
    the 427-row pair (guard-on): write changes 210 of 1171
    the 430-row pair: write changes 210 of 1171
    the perturbed address sets are identical (0 only in the 427-row pair (guard-on), 0 only in the 430-row pair)
    the 430-row pair adds 0 address(es) to the universe and 0 of them are perturbed

  mean guard-off delta over    0 moved -> intact A      -   B      -
  mean guard-off delta over  366 moved in both   A   4.43   B   4.43
  mean guard-off delta over    0 intact -> moved A      -   B      -
  mean guard-off delta over   64 intact in both  A   0.00   B   0.00

  rank shift between the two committed censuses; a positive delta is down the size ordering, and a delta is only comparable within one program
    over the 430 shared keys; the 0 in one census only and the 0 in the other have no counterpart to difference, so they are in no figure below
    main-ec    17 of  380 changed rank; mean  +0.00 over those,  +0.00 over all (an unchanged key at 0); range -24 to +11
    pd          0 of   50 changed rank; mean      - over those,  +0.00 over all (an unchanged key at 0); range +0 to +0
    of the    0 moved->intact     0 changed rank
    of the  366 moved-in-both    17 changed rank
    of the    0 intact->moved     0 changed rank
    of the   64 intact-in-both    0 changed rank
    over all  430 shared keys,   17 changed rank -- the four cells above close on it

  cluster_key    name             rank A       rank B       size  grew  delta A  delta B  verdict
```

**Zero flipped clusters. The flipped set's size distribution is `no rows`.** The
two censuses share all 430 keys with no key on one side only, and the guard
perturbs the same 210 addresses in both — so they are one census, and the two
censuses are membership-identical rather than merely similar. This block is
**not** a tool's output — it is four comparisons computed over the four CSVs §3
names, so it is a summary and is marked as one:

```console
  427-on vs 430-committed:  430 keys each, 0 one-sided, 430/430 identical membership
                            17 shared keys carry a different rank, 8 a different refs total
  427-off vs 430-off:       439 keys each, 0 one-sided, 439/439 identical membership
                            18 shared keys carry a different rank, 8 a different refs total
```

Only bookkeeping differs between the two trees — rank numbering on 17 and 18
keys, reference totals on 8 clusters — and the reference totals differ because
the trees differ (`main-ec` 13957 references at `e6c88864`, 13964 at
`e169a0e4`), which changes neither the partition nor anything the `moved`
predicate reads.

**And the three-way comparison against the 439 pair is where this becomes
unambiguous.** Run against the 439 generation, the 427-era pair reproduces
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §3's 430-vs-439 table on
**every cell but one** — 400 keys shared, 30 and 39 one-sided, the same
71 / 266 / 23 / 40, the same `51` closing over the same four terms, the same
size distribution `1 1 1 1 2 2 4 4 5 6`, the same 5 of 23 large clusters, the
same mean deltas, and the same twelve flip rows with 82 more behind them:

```console
$ python3 ec/tools/xdata_moved_ranks.py across \
    --old-a /tmp/427-on-clusters.csv --new-a /tmp/427-off-clusters.csv \
    --old-a-registers /tmp/427-on-registers.csv --new-a-registers /tmp/427-off-registers.csv \
    --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/439-off-clusters.csv \
    --old-b-registers ec/annotations/xdata-registers.csv \
    --new-b-registers /tmp/439-off-registers.csv \
    --label-a 'the 427-row pair (guard-on)' --label-b 'the 439-row pair'
across the 427-row pair (guard-on) -> the 439-row pair
  keys in both committed censuses: 400; in one only: 30 / 39
    71  moved in the 427-row pair (guard-on), intact in the 439-row pair
   266  moved in both
    23  intact in the 427-row pair (guard-on), moved in the 439-row pair
    40  intact in both
  of the one-sided keys, 29 moved in the 427-row pair (guard-on) and 26 moved in the 439-row pair
  closes: 366 - 315 = 51, over the four terms: (71 - 23) + (29 - 26) = 51

  the flipped set's size distribution, against the census: 1 1 1 1 2 2 4 4 5 6
                                            the census:  1 1 1 1 1 1 2 2 4 5
  of the 23 committed cluster(s) of 8 addresses or more, 5 flipped; the largest committed cluster is 152 addresses
  of the 7 of 16 or more, 1 flipped
  shared keys whose committed membership differs between the two censuses: 0 of 400 -- a key is a hash of the membership, so this is zero by construction and is printed rather than assumed

  §6a across the two generations, over the per-address columns:
    the 427-row pair (guard-on): write changes 210 of 1171
    the 439-row pair: write changes 210 of 1326
    the perturbed address sets are identical (0 only in the 427-row pair (guard-on), 0 only in the 439-row pair)
    the 439-row pair adds 155 address(es) to the universe and 0 of them are perturbed

  mean guard-off delta over   71 moved -> intact A   7.66   B   0.00
  mean guard-off delta over  266 moved in both   A   3.14   B   3.04
  mean guard-off delta over   23 intact -> moved A   0.00   B   3.65
  mean guard-off delta over   40 intact in both  A   0.00   B   0.00

  rank shift between the two committed censuses; a positive delta is down the size ordering, and a delta is only comparable within one program
    over the 400 shared keys; the 30 in one census only and the 39 in the other have no counterpart to difference, so they are in no figure below
    main-ec   345 of  350 changed rank; mean  +9.63 over those,  +9.49 over all (an unchanged key at 0); range -11 to +24
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

**The one cell it does not reproduce is the `main-ec` rank-shift range, and it is
worth naming rather than leaving to a reader who diffs the two blocks.** Run the
fall file's own pair beside this one, with the label normalised so only the data
differs, and the two outputs differ on exactly one line:

```console
$ python3 ec/tools/xdata_moved_ranks.py across \
    --label-a 'the 430-row pair' --label-b 'the 439-row pair' \
    --old-a /tmp/xdata-430/ec/annotations/xdata-clusters.csv --new-a /tmp/430-off-clusters.csv \
    --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/439-off-clusters.csv \
    --old-a-registers /tmp/xdata-430/ec/annotations/xdata-registers.csv --new-a-registers /tmp/430-off-registers.csv \
    --old-b-registers ec/annotations/xdata-registers.csv --new-b-registers /tmp/439-off-registers.csv \
    > /tmp/across-430-439.txt
$ sed 's/the 427-row pair (guard-on)/the 430-row pair/g' /tmp/across-427-439.txt > /tmp/a1.txt
$ diff /tmp/a1.txt /tmp/across-430-439.txt
29c29
<     main-ec   345 of  350 changed rank; mean  +9.63 over those,  +9.49 over all (an unchanged key at 0); range -11 to +24
---
>     main-ec   345 of  350 changed rank; mean  +9.63 over those,  +9.49 over all (an unchanged key at 0); range -8 to +15
```

**The reason is the 17 keys, and it is measured rather than argued.** A rank
shift is differenced against *pair A's own* numbering, so moving pair A's
numbering moves the deltas even when nothing else moves — and pair A is the one
side that differs between the two runs. The block above already records that the
427-era census numbers **17** keys differently from `e169a0e4`'s, and both ends
of this run's wider range fall on two of them:

```sh
python3 -c "
import sys; sys.path.insert(0, 'ec/tools'); import xdata_moved_ranks as m
K = lambda p: m.keyed_by(m.clusters_of(p))
a427, a430, b = K('/tmp/427-on-clusters.csv'), K('/tmp/xdata-430/ec/annotations/xdata-clusters.csv'), K('ec/annotations/xdata-clusters.csv')
renum = {k for k in a427 if m.rank_of(a427[k]) != m.rank_of(a430[k])}
print(f'{len(renum)} of the 430 keys are numbered differently in 427-on than in 430-committed')
for name, a in (('427-on', a427), ('430-committed', a430)):
    d = {k: m.rank_of(b[k])[1] - m.rank_of(a[k])[1] for k in a if k in b and a[k]['program'] == 'main-ec'}
    ends = [k for k, v in d.items() if v in (min(d.values()), max(d.values()))]
    hits = sum(1 for k in ends if k in renum)
    print(f'  {name:>15}: {len(d)} shared main-ec keys, range {min(d.values()):+d} to {max(d.values()):+d}; {hits} of its 2 extreme keys are among those {len(renum)}')
"
17 of the 430 keys are numbered differently in 427-on than in 430-committed
           427-on: 350 shared main-ec keys, range -11 to +24; 2 of its 2 extreme keys are among those 17
    430-committed: 350 shared main-ec keys, range -8 to +15; 0 of its 2 extreme keys are among those 17
```

That is a difference in the two trees, not a transcription slip, and it is the
*same* bookkeeping difference §4's four-comparison block reports — it moves no
membership, so it moves nothing the `moved` predicate or the set comparison
reads. It is also the one figure in the block that is a function of pair A's
numbering at all, which is why it is the one figure that can differ when the two
pairs are the same census.

**And the set comparison the paragraph below rests on is untouched by that one
cell.** It is a three-way comparison printed as sets, which is the thing
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):150-159 is careful about
— two matching totals cannot establish it, and here they are not two matching
totals but the *whole table*, every cell agreeing but the rank-numbering cell
that pair A's own numbering sets, with the 427-era pair on one side of it.

## 5. The direction question, answered: there is no third point to pair

The series is `moved` at each of the three censuses the issue names: **427 →
(new), 430 → 366, 439 → 315.** The new figure is **366**.

**It is 366, which is the 430 figure, and that is because it is the 430
measurement.** §4 measured that the 427-era tree derives the 430-row census —
430 of 430 keys with identical membership, 439 of 439 on the guard-off side,
`moved` 366 in both, zero clusters flipped, an identical 210-address
perturbation set. So the "third point" is the first point re-measured on an
earlier tree, and **it agrees with the 430 point exactly, which is not
corroboration of a direction because it is not an independent observation.**

Read against the two alternatives the issue named, the honest answer is neither:
it is not above 366 and it is not below 366. It is equal, for a reason now
measured. And the conclusion the issue warned against is the one this file
declines to draw in both directions:

- **No "and it decays."** Nothing here adds a point to 366 → 315. The series is
  still **two** points, one observed fall, and a two-point series cannot
  establish a trend in either direction. §5 of
  [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) states that limit and
  it stands unamended; this file records which trees could not be paired and
  why, not a reason to move the limit.
- **No threshold edit.** `assertGreater(len(moved), 300)` at
  `ec/tools/test_xdata_cluster_names.py:392` stays, and the 15 ranks of headroom
  are as they were. The 427-era tree's `moved` of 366 is not a count to bank: it
  is the 430 count, and a floor argued from it would be argued from a
  measurement of the wrong tree. The count that is the floor's remains **315**.
  *(Corrected at this merge, 2026-09-26, and the sentence above is left as it
  was written per §4a-4d: **the floor is untouched and the 15 ranks of headroom
  and the 315 stand**, but the line number is not. #850 put 239 lines into that
  suite in the same window, so the assertion was at **`:563`** on the tree this
  merged into, and #890's later thirty lines put it at **`:588`** on the tree
  this lands in; `:392` there is `decreased, {},`, the last line of the
  assertion holding that no address's `write` decreases. This is one of two pins
  — this one and §69's in
  [`../findings.md`](../findings.md) — that were correct against the tree they
  were written on and are wrong on the merged one, and they are recorded as
  finding 8 in [`test-line-pin-census.md`](test-line-pin-census.md) with the
  cause beside the verdict. **Neither is repointed**, and that is the same
  decision that file's §7 makes for the four it already found: which line a
  stale pin was meant to name is a next pass's call, not a merge's.)*

**What the size sequence is, and the real reason there is no third point.** The
issue's 427 → 430 → 439 is a sequence of *committed file sizes*, and it is
correct for the era it covers. It is not the whole history: §1's unelided log
has the file committed at **five** sizes — 435, 426, 427, 430 and 439 rows —
so "three sizes" undercounts and "430 → 439" describes only the era the pair
tool can read.

**The reason there is no third point is narrower than "427 was never a
derived state", and it is checkable.** `1fcd5f1e`'s tree *does* derive 427
rows: §2 records `--check` there as `428 on disk vs 428 generated` — the same
count, the wrong content — so a 427-row derived census exists and **this work
did not measure the pair at it**. It could not be measured with the committed
tools. `cluster_key` first exists at `e6c88864` (#298), the census commit
immediately *after* `1fcd5f1e` in this file's own history, and every census
before it lacks the column:

```console
$ head -1 <(git show 1fcd5f1e:ec/annotations/xdata-clusters.csv)
cluster_id,program,size,refs,addrs,addr_range,functions_touched,shared_functions,callees,named_addrs
$ head -1 <(git show e6c88864:ec/annotations/xdata-clusters.csv)
cluster_id,program,size,refs,addrs,addr_range,functions_touched,shared_functions,callees,named_addrs,cluster_key,cluster_name

$ python3 ec/tools/xdata_moved_ranks.py pair --old /tmp/1fcd-clusters.csv \
    --new ec/annotations/xdata-clusters.csv \
    --old-registers /tmp/1fcd-registers.csv \
    --new-registers ec/annotations/xdata-registers.csv --label 'the 1fcd5f1e pair'
Traceback (most recent call last):
  File ".../ec/tools/xdata_moved_ranks.py", line 1667, in <module>
    sys.exit(main())
             ^^^^^^
  File ".../ec/tools/xdata_moved_ranks.py", line 1624, in main
    lines, _c, _o, _m = pair_report(args.label or args.old, args.old,
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File ".../ec/tools/xdata_moved_ranks.py", line 235, in pair_report
    moved = moved_ranks(committed, off)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File ".../ec/tools/xdata_moved_ranks.py", line 149, in moved_ranks
    out[row["cluster_key"]] = (row, other)
        ~~~^^^^^^^^^^^^^^^
KeyError: 'cluster_key'
exit=1
```

(The absolute prefix on the four frames is elided; the line numbers, the
`out[row["cluster_key"]]` line, the carets and the `KeyError` are as printed.
The read itself succeeds — `csv.DictReader` takes the file — and the missing
column only bites where the row is indexed, which is why this is a measurement
about the census's columns and not about the pair's arithmetic.)

**Nine of the twenty-two censuses predate `cluster_key`**: the five 426-row
commits, the three 435-row commits, and `1fcd5f1e` — the 427-row commit
*before* `e6c88864`, the one that added the column. None of the nine is readable
by the tool that would measure it. So the era the pair exists in begins at
`e6c88864` — and `e6c88864` is a commit whose file carries 427 rows and whose
tree derives 430. **427 never appears as a paired generation**: the two commits
carrying it are the one whose file is stale and the one the tool cannot read.

**This work did not back-port `cluster_key` to reach the older censuses**, and
no figure is claimed for them. `moved` at `1fcd5f1e` is **not measured here** —
not zero, not absent, not equal to 366 — and a key synthesised for a pre-#298
census would be a measurement of this work's own construction rather than of
that tree, which is why the route was not taken. The series is two points
because of what could be measured here, not because a third generation has been
ruled out.

## 6. What the third measurement does establish

One half of the issue's ask survives the negative, and it is the half the floor's
argument leans on. #852 established that the guard perturbs **the same 210
addresses** in the two generations it measured, and offered that as a third
generation's worth of independent check. **The check passes, and it is genuinely
independent**: this is a tree 50 commits before the 430 pair
(`git rev-list --count e6c88864..e169a0e4`), reached by a back-port of the flag
rather than by inheriting it.

| generation's tree | address universe | `write` changes | `refs` changes | references entering `write` † |
|---|---:|---:|---:|---:|
| `e6c88864` (427-row) | 1171 | **210** | **0** | **833** |
| `e169a0e4` (430-row) | 1171 | 210 | 0 | 833 |
| `6bf9c234` (439-row) | 1326 | 210 | 0 | 833 |

Three trees, three tool generations, one figure. The 155 addresses the 439
generation adds are again **0** perturbed, so the guard's reach is a fixed set
that does not grow with the address universe — the structural claim
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §2 made, now resting on
three measurements rather than two.

**And the direction question has a second, sharper half.** #852's measurement
that the *cluster-level* delta fell 1,623 → 1,030 while the *per-address* effect
held is a claim about a fall, and the 427-era tree carries the same **1,623**.
The fall's *starting* value therefore holds on a third tree **50 commits
earlier** (`git rev-list --count e6c88864..e169a0e4`), which extends how far
back that value reaches and says nothing about what happens next. The 1,030 end
is #852's own 439-row pair at `6bf9c234` and is **not re-measured here**; §4
records that the 427-era tree derives the 430-row census, so it cannot supply
the other end either. For the reason §5 gives, neither end is an *independent*
observation of the fall from this tree, so what the third tree adds is the reach
of the starting value, not a second witness to the fall. That is the same
two-point limit, approached from the other side.

## 7. What this does not do

- **No CSV, YAML or tool is edited.** `xdata-clusters.csv`, `xdata-registers.csv`,
  `xdata-cluster-names.csv` and `registers.yaml` are byte-untouched; every
  regeneration wrote to `/tmp`, and the tool refuses the committed output paths
  in any case. `xdata_register_map.py` is not touched at all. The one patched
  file in this work is a copy of the 427-era tool inside a `/tmp` worktree that
  has been removed.
- **No threshold, figure or assertion moves.** §5 says why, and the floor is
  where [`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):170-175
  put it.
- **No new tool, no new test, no gate.** `xdata_moved_ranks.py` is unchanged, so
  there is no `tools/README.md` row and no `check_testdata_index.py` obligation.
- **Why the 427-row census was committed stale is not derived.** §2 measures
  that it happened, at two commits, and that the tool's own `--self-test` was red
  at both. Which edit produced the three-row gap is a separate question and is
  left as a follow-up rather than guessed at — a census this stale is a fact
  about a commit, and the seven-commit spot check is a spot check, not a census
  of the file's whole history.
- **Nothing is opened in another repository.** No issue or pull request is filed
  against `Wer-Wolf/uniwill-laptop`, `tuxedo-drivers` or anywhere else.
- **No live hardware, EC, BIOS or Windows step**, because nothing here needs one.
  No live run is planned, claimed or implied. Reading
  `ec/firmware/GMxMGxx_11.800` is reading a file.
- **§6 and §7 of the fall file are not redone.** The nine hand names and the 43
  swept addresses are not re-litigated for this pair, and no inference is drawn
  from the guard's per-address figures about which clusters those addresses
  belong to.

## 8. The test that proves it

```console
$ python3 ec/tools/xdata_moved_ranks.py --self-test
  all checks passed

$ python3 ec/tools/xdata_register_map.py --check && python3 ec/tools/xdata_register_map.py --self-test
  ... 1326 register rows, 439 cluster rows, both exit 0 ...

$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
  ..............................
  Ran 30 tests in 15.257s
  OK

$ python3 ec/tools/check_cluster_citations.py
docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0464 is not a member of any
  cluster this line names (...); it is a member of `main-ec-145`
docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0465 is not a member of any
  cluster this line names (...); it is a member of `main-ec-145`
2 citation(s) disagree with ec/annotations/xdata-clusters.csv

$ bash tools/run-tests.sh
35 suite(s) run, 1076 tests; one or more FAILED.
```

**The runner's totals, re-measured on this tree rather than carried over: 35
suites and 1076 tests.** The figure
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md) §9 records for the
merged tree it landed on — 34 suites and 1033 tests — was right for that tree
and is superseded here. The superseded pair was itself corrected once already,
to `35 = 34 + 1` and `1074 = 1033 + 41`, where the missing term
is **#887's `ec/tools/test_census_test_line_pins.py` at 41 tests**, landed in the
same merge window. **That correction did not reproduce, and the figure here is
run on three trees rather than argued:** `35` suites and `1076` tests on this
tree, on a clean `origin/main`, and on the fork point `d62730e1` this branch
started from — so **nothing in this merge, and nothing on `main` since the fork,
moves the runner at all**, and `1074` is a figure that reproduces on none of the
three. It is left visible in the two correction blocks it appears in rather than
deleted, per §4a-4d. This change adds no `test_*.py` of its own and so no row to
`tools/README.md`'s table, which is the other half of why the figure does not
move. Both superseded pairs are left visible with the correction beside them per
§4a-4d rather than edited out — in the fall file's §9 paragraph and in
[`../findings.md`](../findings.md) §63 — and those two pointers are the whole
of the change to either file. The runner exits 1, and the one red assertion is
**still only** `test_committed_prose_matches_committed_census`.

**The known-answer run is §1 through §6 above.** The ancestry check, the
back-port's 12 hunks and its line-for-line identity with #528's diff, the red
`--check` and the red `--self-test` line at `e6c88864`, the seven-commit
`--check` table, the three pairs and the `210 + 9 − 3 = 216` closure, the
`0 of 430` and `no rows` of §4, the three-way table that reproduces §3 of the
fall file cell for cell, and the `KeyError: 'cluster_key'` of §5 are the
evidence, printed rather than summarised. A `--self-test` that can only go green
is not the test, and the one assertion here that could have gone red and did not
is the membership-identity comparison in §4 — which is what makes "zero
flipped" a measurement rather than a coincidence of counts. §5's is the other
kind: a check that was red, and is recorded at its traceback because a negative
that is only described is a claim.

**The citation checker's state, recorded the way the fall file records its red
suite.** `check_cluster_citations.py` reports the same **two** citations before
and after this file was added, both at
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):220
— **#822's** write-up, named in that file's closing note, in `tools/README.md`'s
merged-tree note and in [`../findings.md`](../findings.md) §59, and reproducible
on a clean `origin/main`. So `ec/tools/test_check_cluster_citations.py` stands at
48 tests with that one failure, exactly as it did before this change, and this
change neither fixes it nor adds to it.

**That checker is the constraint that shaped this file, and it is a real one.**
`test_committed_prose_matches_committed_census` runs the checker over every
committed markdown file and requires exit 0, and the checker resolves ids, keys
and names against the **committed** census only — so a file that prints a
guard-off generation beside the committed one "names clusters from two rankings
at once" and goes red, which is how
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md)
was rejected once already. So no table here pairs a rank with an address, no
table's first cell is a `main-ec-NNN` id, the §2 table's first cell is a commit
and §3's is the pair's own name, and the two `--check` row dumps that *would*
have paired ranks with address lists are elided where they appear in §2. The
flip table in §4 is quoted with its addresses absent because the tool prints none
in that shape.
