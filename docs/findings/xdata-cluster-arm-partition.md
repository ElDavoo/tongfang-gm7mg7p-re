# The `main-ec` and `pd` cluster counts are a partition of the §6a census, and only its arms were held (issue #919)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every figure is a count
over committed text, from the committed tool run against the committed decompile
with both scratch outputs under `/tmp`. No CSV, no `registers.yaml` row and no
`status:` value changes, and no gate is touched.

## What was already pinned, and what was not

`TheGuardOffRegeneration.test_the_census_is_the_one_6a_measured` in
`ec/tools/test_xdata_cluster_names.py` pins §6a's cluster row — the guard-off
run's `394` against the committed census's `389` — and beside it the pd arm of
the same pair, which
[`xdata-guard-off-pd-cluster-count-pinned.md`](xdata-guard-off-pd-cluster-count-pinned.md)
is the write-up for.

**What no assertion held was that the two arms are a partition.** Each was a
count over its own program; nothing said the two accounted for the census. The
claim is stronger than either pair and is a different kind of thing: `program` is
a *partition* on a clusters CSV, so every row belongs to exactly one arm, and
the arms therefore sum to the row count. Two counts that happen to be near each
other are not that.

The gap is the same shape the same case already closes one file over: the `834`
sum there partitions the *register* rows by `program`, and
`test_xdata_guard_off_row_join.py` partitions the register rows' denominators.
The §6a committed and guard-off censuses' clusters were the third instance of
that shape to be unheld rather than the first — `test_the_440_splits_the_way_6b_prints_it`
already held the §6b export-ownership census' clusters `program` column to
`OWNERSHIP["clusters"]` — so what was missing is narrower than the column: it is
the two §6a censuses, which are the ones §2b's verdict column is silent about,
since §6a prints no pd arm and so neither `445` nor its breakdown is in §2b's
tables for the checker to audit.

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
The two figures are also each census's own cluster count, which is the part worth
having: that the arms' sum and the count agree *is* the partition, and it is
asserted both ways rather than as one number that could be read as either.

The second assertion is not a restatement of the first, and the difference is the
shape that separates them. Measured on the run's own CSV:

| shape | `394` | `51` | arms' sum | row count |
| --- | --- | --- | --- | --- |
| as written | holds | holds | `445` | `445` |
| a row gains a third `program` value | holds | holds | `445` | **`446`** |
| a row gains no `program` at all | holds | holds | `445` | **`446`** |
| a pd row's own value becomes a third one | holds | **red** | **red** | `445` |

A row in neither arm is in no arm count and in no arm *sum* either, so the first
assertion passes on the two shapes in the middle and the row count is the only
thing that moves. That is what the second assertion is for, and it is why
`self.off`/`self.committed` being `{cluster_id: row}` dicts is incidental rather
than a claim: they count distinct ids, which on this tree is the same `445` the
run printed.

## What the assertion reaches that the arms do not

A `program` column that stopped partitioning over the **clusters** — a third
value, or a row carrying none — is the shape the arm counts cannot see. Each
arm would hold at `394` and `51` while the census grew past `445`, and every
other cluster assertion in the tree would go on passing. The same failure on the
register rows' `program` column is already closed:
`test_xdata_guard_off_row_join.py` asserts the denominators partition to their
total, and this case's `834` sum partitions the register rows by `program`.

A census that emitted **two rows under one `cluster_id`** is not a shape this
assertion reaches and the arms do not, and the reason is in the tool rather than
in the case: `cid = f"{g}-{n:03d}"` in `xdata_register_map.py`'s `build` bakes
the program into the id, so a repeated id is necessarily same-program and always
takes an arm count with it. Rewriting one of the run's `445` main-EC rows to
carry `main-ec-001` — an id already present — does leave the CSV at `445` lines,
but `clusters_of` keys by id, so it collapses to `444` distinct rows and that arm
drops to `393`: the `394` assertion above goes red first, and the arms' sum with
it, at `444`. There is no shape here the arms do not already catch.

That is the whole of it, and it is worth being exact rather than expansive: this
is a property of the census the committed tool writes, not of the EC.

## Why the message sends a re-deriver to stdout rather than to §6a

§6a prints the main-EC arm of the pair (`xdata-06c2-06db-timers.md:789`) and the
committed census's `439` in prose (`:770`), but **no pd arm and no row total** in
its table. A message pointing at a §6a line that does not carry the figure is the
failure the whole case exists to prevent, so the message names the run's own
`wrote …/clusters.csv: 445 rows` line instead. That is the same treatment the
`1,202` `both`-refs figure gets in the same case, and for the same reason: the
figure is real and printed, just not by the page.

`docs/findings/xdata-cluster-names-guard-off-recipe.md` does print the pair as a
`cluster rows` row beside the `394`/`389` one, and
`test_xdata_guard_off_row_join.py` already reproduces that row from the report.
Neither held the figure as an int literal in a numeric assertion, so
`check_doc_figure_pins.py` measured `445` `unheld` — "no occurrence in
`ec/tools/*.py` and no committed cell" — while a page in the tree printed it.

## What the pin is, measured rather than promised

The command prints a verdict and a `file:line`. The line is quoted here as
`test_xdata_cluster_names.py:NNN` rather than as whatever number it carries when
this is read: a transcript is the one place a pin is declined as a citation, so
naming a line only inside one would make this the tree's sole record of a line
the census then declines — which
`test_census_test_line_pins.py::test_every_declined_pin_is_also_cited_in_live_prose`
is there to refuse. The claim is the verdict and the module.

```
$ python3 -c "
import importlib.util
s=importlib.util.spec_from_file_location('cdfp','ec/tools/check_doc_figure_pins.py')
m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
f=m.index(); print(m.measure(445, [], f)[0])"
held-by-check-literal
```

`445` resolves in `test_xdata_cluster_names.py`, the census suite, and nowhere
else.

**The expected pair is a literal inside the `assertEqual`, not a `for` header or
a table above it.** That is load-bearing rather than stylistic:
`check_doc_figure_pins.py` decides a figure is held by finding an int inside a
`check()`/numeric-`assert*` call, so a pair written only in a loop header
measures `unheld` however many cases hold it — the trap #849/#850 merged over,
which `test_the_census_is_the_one_6a_measured` records beside its own four
direction blocks.

## A stale count, corrected in place

`docs/findings/xdata-6a-direction-rows-pinned.md` carried a bullet reporting that
`guard_off()`'s docstring "says 'six cases want the same regeneration'" and that
it was "left alone" as a count in a file the change edited. Issue #962 had
already rewritten that sentence to attribute the regeneration to both of the
classes that share the cached run — `TheGuardOffRegeneration` and
`TheGuardOffKeyDistinctness` — and kept the old "six" visible beside the reason
it was wrong. The bullet is corrected there under §4a-4d, with the wrong version
left in place.

Neither place restates how many cases either class holds. A reader who wants
that runs `bash tools/run-tests.sh` and reads the class definitions in
`ec/tools/test_xdata_cluster_names.py`; the figure is one every landing suite
moves, which is how the "six" went stale in the first place.

## What this does not establish

- **Nothing about the EC.** `445` and `439` are properties of CSVs the committed
  tool writes; a re-derivation of the census moves them, exactly as it moves the
  `394` and the `51` this case already holds. Re-derive §6a rather than moving a
  number here, which is what the assertion messages say.
- **Not a claim that the two programs are the only ones that exist.** It is a
  claim about the `program` column of a clusters CSV, which carries `main-ec` and
  `pd` and nothing else on this census. The register rows' `program` column
  carries a third value, `both`, and that partition is asserted separately.
- **It says nothing about what the `==` guard does to either program.** The
  census-wide figures for that are #713's, and
  [`pd-pair-unmoved-one-fold.md`](pd-pair-unmoved-one-fold.md) is the write-up:
  the ownership pass reaches the PD program, finds one fold in it, and that fold
  names no XDATA byte, so `0` of the pd references move while the same pass moves
  `296` addresses' references elsewhere.
