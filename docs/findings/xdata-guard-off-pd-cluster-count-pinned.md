# The guard-off `pd` cluster count `51`, the one figure §2b named as held by nothing, pinned beside the `394` (issue #918)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure is a count
over committed text taken from the census tool's own flags, with both scratch
outputs under `/tmp` and nothing written into the tree. No CSV, no
`registers.yaml` row and no `status:` value changes.

## The gap, as §2b stated it

§2b of
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
is a command's output rather than prose:
`python3 ec/tools/check_doc_figure_pins.py` against that file with `--section 2b`
resolves each figure §2b's tables carry to a `file:line` that compares against
it, and exits non-zero when the marking and the measurement disagree. Its
all-held column says nothing about a figure the tables do not carry, and §6a does
not print this one — so the `51` was named in the section's prose instead, on the
understanding that a reader would go and pin it. It was the last figure §2b
could not vouch for.

The gap is the same shape as the `394` beside it, and that is what made it an
`assertEqual` rather than an investigation.
`TheGuardOffRegeneration.test_the_census_is_the_one_6a_measured` in
`ec/tools/test_xdata_cluster_names.py` pins the main-EC arm of the pair — the
guard-off run's `394` against the committed census's `389`, which §6a prints at
`xdata-06c2-06db-timers.md:789` — and did not pin the pd arm, although the same
run prints it on the same console line.

**What that left unreached is narrower than "the pd count could move", and the
narrower shape is the one to name.** A re-export that moved a cluster *across*
the two programs was already caught: that moves the main-EC count with it, and
the `394` is counted over the same guard-off rows by the same expression, so
`394` → `395` and the pre-existing assertion trips. The case nothing reached is
a **pd-arm-only** change — two pd clusters merging into one, or one splitting
into two — which takes `51` to `50` or `52` and leaves the `394` where it was.
That is the gap this pin closes, and it is the one worth closing, because §2b's
verdict column is what a re-deriver reads before touching anything and a figure
its tables do not carry is a figure that column says nothing about.

## The measurement

One run, both CSVs to a scratch directory, the committed decompile read in place:

```
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-clusters /tmp/…/clusters.csv --out-registers /tmp/…/registers.csv
wrote /tmp/…/registers.csv: 1326 rows
wrote /tmp/…/clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
```

`445` is `394 + 51`, and the committed census's `439` is `389 + 50`, so the
guard lifts five main-EC clusters and one pd cluster out of the committed one.
The two figures the assertions compare are counts of rows in those two CSVs
carrying `program == "pd"` — the same expression the `394` is counted with, over
the same two files, in the same case.

**The committed `50` is §6b's `pd` cluster count and was already measured
`held`** — though not by this suite: `check_doc_figure_pins.py` resolves it at
`SHARE_ORACLE["classes"]` in `ec/tools/export_ownership.py`, an unrelated
integer that happens to equal it, which is a coincidence rather than a pin. It
is asserted in the same case so that the two arms are one measurement and a
reader asking what the guard-off run added is looking at a pair rather than at a
lone `51` with nothing to compare it against — the shape #850 used for §2a's
four direction rows, where each numerator is pinned with its denominators.

## What the pin is, measured rather than promised

`check_doc_figure_pins.py` decides a figure is held by finding it as a value an
asserting call compares against, so `51` measures `held-by-check-literal` in
`ec/tools/test_xdata_cluster_names.py` and measured `unheld` before this change.
That is a measurement of the tree, and the tree can be asked again — not by
`check_doc_figure_pins.py --section 2b`, which does not print this figure at all,
because §2b's tables do not carry it and that is the whole reason this file exists
rather than a row in §2b, but by the case that watches it:

```
$ python3 -m unittest \
    ec.tools.test_check_doc_figure_pins.ClassifiesTheRealTree.test_the_guard_off_pd_cluster_count_is_pinned_beside_the_394
```

That case asserts the verdict *and* that it resolves in the census suite's own
file, so a `51` that some later constant happened to equal would fail it rather
than pass it as a promise.

**The watch used to run the other way.** The `51` was the real-tree witness in
`test_a_small_figure_is_not_pinned_by_an_unrelated_cell`, which asserted it
`unheld` to show that the checker refuses to borrow an unrelated cluster row's
cell of the same value. A witness has to be a figure the checker measures
`unheld`, so pinning it retired that use; the case now witnesses the same rule
with `31`, which is a cell in three committed cluster rows and which nothing in
`ec/tools/*.py` asserts. `31` is a weaker witness on purpose — no page names it,
so its verdict is stable — and a stronger one for the rule, since an
over-matching tool has three rows to borrow from rather than one.

## Why there is no row in §2a

§2a is the table of figures the test pins, and its third column is *where §6a
prints each figure*. This one is not printed there — that is the reason §2b had
to name it in prose and the reason it went unpinned for as long as it did — so a
row would have an empty cell in the one column that gives the table its point.
Adding one would also have made that section's row counts a number every merge
has to edit, which is what `docs/findings/no-append-logs.md` is the write-up
against. The pin is here instead, and the assertion carries the message.

## What this does not establish

- **The `51` is a property of this tree, not of the EC.** It is a count of rows
  in a generated CSV, and a re-derivation of the census moves it. Nothing here
  is evidence about any register's behaviour, and `unheld` in §2b's report is
  "not found by this method", never "absent" — the caveat
  `ec/annotations/registers.yaml` carries for a static scan.
- **This says nothing about what the `==` guard does to the PD program.** The
  census-wide figures for that are #713's, and
  [`pd-pair-unmoved-one-fold.md`](pd-pair-unmoved-one-fold.md) is the write-up:
  the ownership pass reaches the PD program, finds one fold in it, and that fold
  names no XDATA byte, so `0` of the pd references move while the same pass
  moves `296` addresses' references elsewhere. That a pd *cluster* count moves
  by one under `--no-eq-guard` and the pd reference count does not move under
  `--export-ownership` are two different questions about two different flags.
- **§2b's figures are unchanged by this.** The `157`/`858` row was marked `held`
  before the pin that now holds it, and
  [`xdata-ownership-arms-do-not-partition.md`](xdata-ownership-arms-do-not-partition.md)
  is the write-up for that pin and for the reason `pd_distinct` has no sum
  identity to assert beside it.
