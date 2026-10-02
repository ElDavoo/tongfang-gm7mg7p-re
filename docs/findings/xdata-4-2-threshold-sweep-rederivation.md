# §4.2's threshold sweep, re-run against the committed census (issue #581)

`ec/annotations/xdata-register-map.md` §4.2 carries two `--threshold-sweep`
blocks. Issue #581 quotes a third set of figures against them and calls the table
wrong. This is the record behind the edit that landed with it: the sweep on the
committed tree, §4.2's first block against it cell for cell, **which commit each
of the other two sets belongs to**, and the one claim in §4.2 that did need
tightening.

**Nothing here is a live observation.** The census is a static measurement of
committed decompiled C, and `--threshold-sweep` re-clusters in memory and returns:
it writes no CSV even when the `--out-` flags are given, so a figure below is a
statement about text and not about the machine. The CSVs are inputs, not outputs;
every regeneration in this file goes to `/tmp`, which is structural rather than a
promise — `--no-eq-guard` on its own is refused, because the paths it defaults to
are the committed census.

## The sweep on this tree

```console
$ python3 ec/tools/xdata_register_map.py --threshold-sweep
threshold,relations,main-ec clusters,main-ec largest,main-ec singletons,pd clusters,pd largest
0.30,touching+writers,229,531,115,35,55,12
0.35,touching+writers,340,273,163,49,35,24
0.40,touching+writers,350,261,169,49,35,24
0.45,touching+writers,384,153,195,50,35,25
0.50,touching+writers,389,152,200,50,35,25
0.55,touching+writers,548,82,314,68,16,39
0.60,touching+writers,562,82,327,69,16,41
0.65,touching+writers,579,81,341,69,16,41
0.70,touching+writers,624,42,382,76,14,50
$ python3 ec/tools/xdata_register_map.py --threshold-sweep --no-writer-axis | sed -n '1p;6p'
threshold,relations,main-ec clusters,main-ec largest,main-ec singletons,pd clusters,pd largest
0.50,touching,507,74,274,61,16,36
```

**§4.2's first block is this block**, all nine rows and all seven cells of each,
and it was already this block before this change: it was written at `6bf9c234`
(#279, the pair-accessor pass), the same block is in that commit's copy of the
file, and `xdata-clusters.csv` is the same 439 rows at both ends of the range, so
nothing since moved the numbers under it. The `--no-writer-axis` block beside it
reads 507/74/274, which is what #582's correction already put in the prose, and
the prose's `389` and item 3's `200` singletons are the `0.50` row above.

The `0.50` row is also the committed census, which is the cross-check that costs
nothing:

```console
$ python3 ec/tools/xdata_register_map.py --out-registers /tmp/h-r.csv --out-clusters /tmp/h-c.csv
  names: seeded 9, exact 0, carried by overlap 0, tied, not carried 0, with no name 430
wrote /tmp/h-r.csv: 1326 rows
wrote /tmp/h-c.csv: 439 rows
  main-ec: 1218 distinct addresses, 14838 references, 389 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 50 clusters at threshold 0.5
```

389 + 50 = 439, the committed `xdata-clusters.csv` row for row, and 1,218 is
what `xdata-registers.csv` holds as main-EC distinct addresses — 1,169 rows with
`program=main-ec` plus the 49 with `program=both`. That is the denominator §4.2's
`0.30` sentence uses, and it is current.

## The other two blocks are two different trees, and neither is this one

The issue's table is real, and it is reproducible — on a commit the tree no
longer holds. `git archive` one commit's `ec/` and re-run the tool that commit
carried:

```console
$ rm -rf /tmp/rev && mkdir -p /tmp/rev
$ git archive 37140548 ec | tar -x -C /tmp/rev      # #327's unnamed-callee pass
$ cd /tmp/rev && python3 ec/tools/xdata_register_map.py --threshold-sweep
threshold,relations,main-ec clusters,main-ec largest,main-ec singletons,pd clusters,pd largest
0.30,touching+writers,240,302,123,35,55,12
0.35,touching+writers,339,113,169,49,35,24
0.40,touching+writers,348,110,176,49,35,24
0.45,touching+writers,375,109,200,50,35,25
0.50,touching+writers,380,109,204,50,35,25
0.55,touching+writers,524,43,320,68,16,39
0.60,touching+writers,538,42,334,69,16,41
0.65,touching+writers,552,42,344,69,16,41
0.70,touching+writers,595,42,383,76,14,50
$ python3 ec/tools/xdata_register_map.py --threshold-sweep --no-writer-axis | sed -n '1p;6p'
0.50,touching,481,43,279,61,16,36
```

Every cell of that is the cell issue #581 quotes, including the `0.60` row it
marks unchanged and the `481` it calls a correction. It is not this tree, it is not
§4.2's table, and it is not the tree immediately before #279 either — that one
reads the same at 0.30 through 0.50 but differs in four of the upper rows. The
issue's block is `37140548`'s reading, then, and neither `6bf9c234^`'s nor a
blend of the two:

| row | `37140548` (#327) | `6bf9c234^` (before #279) |
|---|---|---|
| 0.30 – 0.50 | 240/302, 339/113, 348/110, 375/109, **380/109** | identical |
| 0.55 – 0.70 | 524/43/320, 538/42/334, 552/42/344, 595/42/383 | 525/43/321, 539/42/335, 553/42/345, 596/42/384 |

So there are **three** readings in play. The issue compared two of them and
declared the second wrong; the third is the one anyone running the command today
gets, and it is the one the issue never mentions:

| reading | measured on | at 0.50, `touching+writers` |
|---|---|---|
| §4.2's second block | `c9e0c2c4` (#206) | 376 / 108 / 203 |
| the issue's table | `37140548` (#327) | 380 / 109 / 204 |
| §4.2's first block | the committed tree | 389 / 152 / 200 |

The issue's arithmetic is self-consistent throughout — 337 → 376 becoming
339 → 380, "adds 149 more" becoming +144, the largest "holding at 108–112"
becoming 109–113, and 1,063 becoming the 1,062 that commit's tool prints. It is
a correct re-measurement of the wrong tree, and `docs/findings/xdata-census-totals.md`
follow-up 4 has been carrying its numbers as current since it was written.

## Which tree the second block was measured on

`c9e0c2c4`, and not merely "before #279". Running that commit's own tool over
its own `ec/` reproduces §4.2's second block cell for cell:

```console
$ rm -rf /tmp/rev206 && mkdir -p /tmp/rev206
$ git archive c9e0c2c4 ec | tar -x -C /tmp/rev206     # #206, the == -guard fix
$ cd /tmp/rev206 && python3 ec/tools/xdata_register_map.py --threshold-sweep
0.30,touching+writers,238,306,122,35,55,12
0.35,touching+writers,337,112,169,49,35,24
0.40,touching+writers,345,109,176,49,35,24
0.45,touching+writers,371,108,199,50,35,25
0.50,touching+writers,376,108,203,50,35,25
0.55,touching+writers,525,43,321,68,16,39
0.60,touching+writers,538,42,335,69,16,41
0.65,touching+writers,551,42,345,69,16,41
0.70,touching+writers,594,42,383,76,14,50
$ python3 ec/tools/xdata_register_map.py --threshold-sweep --no-writer-axis | sed -n '6p'
0.50,touching,479,43,278,61,16,36
```

The `479` and the `278` are §4.2's own words in the sentence #582 corrected to
`507`, so that correction named the right tree when it said "the tree §4.2 was
written against" — it is `c9e0c2c4`'s.

**The block was then carried, not re-run.** `6bf9c234` added the second block by
copying the first's predecessor out of §4.2 and labelling it, and in the 101
commits between the two the block's figures are unchanged — of the 102 commits in
that range, `6bf9c234` is the only one whose §4.2 sweep block differs from
`c9e0c2c4`'s, and 17 of the 102 edit this map. So "the pre-#279 tree" was true of
the *direction* (#279 is what superseded it) and false of the *tree* (the sweep
reads 380/109/204 there, not 376/108/203), and a reader who ran the command the
label names would have got figures the block does not carry. That is the whole of
the edit to §4.2: the label now names `c9e0c2c4 (#206)`, the sentence that
introduced it says the same, and the superseded-paragraph sentence below it stops
calling `c9e0c2c4`'s claim a claim about the pre-#279 tree.

The block's figures are **not** changed. It is a record of one commit's run, which
is what it is kept for.

## Is 0.50 still a recorded choice rather than a tuned one

Re-made from the fresh curve, because the old argument was made from numbers that
have since moved a long way.

The claim is not "the largest cluster is stable" — on this tree it is not. Across
0.35 → 0.50 it falls 273 → 152, where on `c9e0c2c4`'s tree it *held* at 108–112,
because #279's 155 pair-accessor addresses landed in the same `0x03xx`-`0x05xx`
working page and merged into the components that were already there. What does
survive is the **shape of the choice**: on every tree measured here the run of
thresholds from 0.35 to 0.50 is one plateau and 0.55 is where it breaks.

| tree | largest at 0.35 → 0.50 | clusters at 0.35 → 0.50 | 0.55 largest | 0.55 adds |
|---|---|---|---|---|
| `c9e0c2c4` (#206) | 112 → 108 | 337 → 376 | 43 | 149 |
| `37140548` (#327) | 113 → 109 | 339 → 380 | 43 | 144 |
| committed tree | 273 → 152 | 340 → 389 | 82 | 159 |

0.50 is the last threshold before the largest cluster collapses and the count
takes off — on this tree the next step, 0.55, cuts the largest by nearly half
again (152 → 82) and adds 159 clusters, against the 49 the whole 0.35 → 0.50 run
adds. A value chosen on the plateau is not moved by a pass that adds addresses on
the plateau; that is the argument, and it does not depend on how steep the plateau
is. `--check` failing until the committed CSVs match a different `--threshold` is
the other half of it, and is what makes the choice visible in a diff rather than
buried in a constant.

## The 1,063 denominator was right when it was written

§4.2's superseded paragraph reads "0.30 collapses 306 of the 1,063 into one
component". The two halves are `c9e0c2c4`'s `0.30` largest and `c9e0c2c4`'s
main-EC distinct address count, and that commit's tool prints both:

```console
$ cd /tmp/rev206 && python3 ec/tools/xdata_register_map.py \
    --out-registers /tmp/r206-r.csv --out-clusters /tmp/r206-c.csv
  main-ec: 1063 distinct addresses, 13937 references, 376 clusters at threshold 0.5
```

The `13,937` is the same figure `docs/findings/xdata-census-totals.md`'s
superseded-figures table gives for `c9e0c2c4`'s generation, which is the
cross-check that the commit identified here is the one the rest of this file's
history is measured against too.

So the denominator is **not** a stale figure left behind by a correction that
predates the sentence. It moved after — to 1,062 somewhere between `c9e0c2c4` and
`37140548`, which this repository attributes to #259 and #263, and to the 1,218
the current paragraph uses at #279. §1 and §3 correcting 1,062 in place is
history beside history rather than a live discrepancy, and no correction to that
sentence is warranted — which is why none was made. `docs/findings.md`'s rule is
that a superseded figure sits beside the correction that replaces it, and here
the replacement is the current paragraph two sentences earlier.

## What this issue proposed, and what the tree says

| what issue #581 asserts | what the committed tree says | command |
|---|---|---|
| `0.30` reads `240,302,123` | 229 clusters, largest **531**, 115 singletons | `--threshold-sweep` |
| `0.50` reads 380 clusters, largest 109 | **389 / 152**, and that is §4.2's first block already | same |
| `--no-writer-axis` reads `481,43,279` | **507 / 74 / 274**, which §4.2's block and #582's correction already carried | `--no-writer-axis` |
| "the largest main-EC cluster holds at 108–112" is 109–113 | 108–112 is `c9e0c2c4`'s and 109–113 is `37140548`'s; §4.2's live sentence is 273 → 152 | the two extracted trees above |
| "the cluster count only moves 337 → 376" is 339 → 380 | 337 → 376 is `c9e0c2c4`'s and 339 → 380 is `37140548`'s; the current sentence is 340 → 389 | same |
| "0.55 … adds 149 more" is +144 | +149 is `c9e0c2c4`'s and +144 is `37140548`'s; the current sentence is +159 | same |
| "0.30 collapses 306 of the 1,063" is 302 of the 1,062 | 302 and 1,062 are `37140548`'s; the current sentence is 531 of the 1,218 | same |
| "§4.2 quotes 479,43,278" for `--no-writer-axis` | it did, and `c9e0c2c4` is the tree it was quoting — #582 already corrected it to 507 | same |

Every arithmetic correction the issue makes is right *for `37140548`*. None of
them is a statement about this tree, which is the form the rule at the top of the
map asks for: name the tree a figure was measured against, not the date it was
wrong.

## The gates this change was measured against

| command | reading on this tree |
|---|---|
| `python3 ec/tools/xdata_register_map.py --check` | green — 1,326 register rows, 439 cluster rows |
| `python3 ec/tools/xdata_register_map.py --self-test` | green — all assertions passed |
| `python3 ec/tools/gen_findings_index.py --check` | green — 218 write-ups |
| `python3 ec/tools/check_pin_table_rows.py` | green — 132 rows against 132 records, 0 unplaced |
| `python3 ec/tools/check_no_append_logs.py` | green |
| `python3 ec/tools/check_findings_frozen.py` | green |
| `bash .github/scripts/agent-gates.sh` | green, including `doc links` |
| `bash tools/run-tests.sh` | green — 107 suites |

`--check` is the mechanical half of the claim that this change moved no input: the
census, `registers.yaml` and the CSVs are untouched, so the tool's own
regeneration still matches the committed files byte for byte.

The pin table is here because §4.2's edit pushed two lines down and
`docs/findings/test-line-pin-census.md` records the citing line of every
`test_*.py:NNN` the markdown carries. Both rows are re-anchored, in the shape
their verdict cells already use for the four times the same thing had happened —
a move, and not an edit, with the cited text unchanged.