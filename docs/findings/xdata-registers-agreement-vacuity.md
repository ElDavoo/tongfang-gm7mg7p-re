# The guard-off registers loop was coverage-blind, and 17 of the 50 `pd` clusters are named by no register row at all (issue #968)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every transcript
below is the output of a command over two committed CSVs, over a regeneration
of them, or over a doctored copy of such a regeneration, with every scratch
output under `/tmp` and nothing written into the tree. **The committed census
files are the only real inputs** — `ec/annotations/xdata-clusters.csv` and
`ec/annotations/xdata-registers.csv`, plus the guard-off regeneration
`test_xdata_cluster_names.py` builds from the committed tree. Same framing as
[`xdata-guard-off-key-distinctness.md`](xdata-guard-off-key-distinctness.md),
which this page follows from and whose §2 is corrected here.

**The calibration comes first: no published figure moves.** The two censuses
§2 measures are the committed pair and are re-derived by their own commands
from the tree as it stands. What is below is that the *case* holding the
guard-off pair's agreement had nothing standing behind two ways its input can
be broken, that the case is not held by the suite as a whole but only by an
unrelated equality in a different class, and — measured, not assumed — that
the assertion the issue proposes in place of those two floors is a claim this
tree does not satisfy, for a reason that is itself worth having written down.

## 1. What the case holds, and the two ways it passes on nothing

`ec/tools/test_xdata_cluster_names.py::TheGuardOffKeyDistinctness::test_the_guard_off_registers_csv_agrees_with_its_clusters`
holds that every register row the guard-off generation wrote carries the
`cluster_key` its own clusters CSV gives that row's `cluster_id`. As written
that was a loop and nothing else:

```python
by_id = {cid: row["cluster_key"] for cid, row in self.rows.items()}
with open(self.registers, newline="") as f:
    for r in csv.DictReader(f):
        self.assertEqual(r["cluster_key"], by_id[r["cluster_id"]])
```

The comparison asks over the rows that are *there*, so two defects in the file
it reads leave nothing to ask about. Neither is a disagreement, and that is
what makes them invisible to a comparison:

- **A registers CSV with no data row** — a header and nothing else, or a
  writer that failed partway — makes the loop body never execute. It passes on
  the emptiness.
- **A registers CSV missing a program** does the same per program. Every
  remaining row can agree with its cluster and the case is green, while every
  cluster of the missing program is unchecked. The per-program split is live
  on this tree, so this is not a hypothetical shape.

The case's own comment gave the reason it must not be a no-op, and it was
right: these are the CSVs nobody reads — they land in a scratch directory and
are gone with the next run — so a registers CSV that disagreed with its own
clusters CSV would break the lookup and be caught by nothing. That argument is
about a *disagreement*. It says nothing about an *absence*, and an absence is
the likelier defect of a file a writer failed to finish.

## 2. Why the split the issue proposes is not a claim this tree satisfies

The issue's suggested floor — that the registers CSV's per-program split
matches its clusters CSV's — is false as a count, and the reason is worth
recording, because it is a property of how the generator joins the two files
rather than a fact about the numbers.

**The two CSVs are not a per-program mirror of one another.** The registers
CSV is a census of *addresses*; the clusters CSV is a clustering *per program*,
so it has a row an address-level census has no column for:

```sh
python3 -c 'import csv, sys, collections
for p in sys.argv[1:]:
    rows = list(csv.DictReader(open(p, newline="")))
    print(p, len(rows), "rows,", dict(collections.Counter(r["program"] for r in rows)))' \
  ec/annotations/xdata-clusters.csv ec/annotations/xdata-registers.csv
```

```
ec/annotations/xdata-clusters.csv 439 rows, {'main-ec': 389, 'pd': 50}
ec/annotations/xdata-registers.csv 1326 rows, {'main-ec': 1169, 'pd': 108, 'both': 49}
```

`both` is the third value in the registers CSV and has no counterpart in the
clusters CSV: a row is `both` when the address is touched by *both* images.
This is the `#906`/`#907`/`#918` `both`/pd family the issue points at, and it
is the reason a row-count comparison over the two is not on offer.

**Seventeen clusters are named by no register row at all.** Not a thin edge of
the `pd` clustering but every one of them a cluster the address census cannot
name, and the reason is the same in all seventeen:

```sh
python3 -c 'import csv, sys
cl = list(csv.DictReader(open(sys.argv[1], newline="")))
rg = {r["addr"]: r for r in csv.DictReader(open(sys.argv[2], newline=""))}
named = {r["cluster_id"] for r in rg.values()}
miss = [r for r in cl if r["cluster_id"] not in named]
print(len(miss), "of", len([r for r in cl if r["program"] == "pd"]), "pd clusters are named by no register row:",
      [r["cluster_id"] for r in miss])' ec/annotations/xdata-clusters.csv ec/annotations/xdata-registers.csv
```

**The mechanism is one line of the generator, and the set is exact.** A
register row has a single `cluster_id`, and `xdata_register_map.py` picks the
`main-ec` one wherever the two images share an address — `entry, primary =
combined, "main-ec" if "main-ec" in seen else "pd"` in its row builder,
followed by `cid = cluster_id.get((primary, addr))`. So a shared address is
recorded under its main-EC cluster and its `pd` cluster is left unnamed.

That row-builder rule is not new here, and the page that already states it is
[`xdata-no-eq-guard-census-scale-join.md`](xdata-no-eq-guard-census-scale-join.md):
"On a `program=both` row `xdata_register_map.py` picks one program and reads
the clustering from it", quoted with the same line, and drawing the same
consequence — "a `both` row carries one `cluster_id` cell and it is main-EC's".
`ec/tools/test_xdata_guard_off_row_join.py::test_a_both_row_mixes_the_main_ec_clustering_with_summed_counts`
holds the same rule in a comment and pins it. What is new here is the step
from that rule to its consequence for *coverage*: which clusters the rule
leaves unnamed, and the fact that the set is exact. The prediction below is
therefore exact rather than approximate, and holds both ways:

```sh
python3 -c 'import csv, sys
cl = list(csv.DictReader(open(sys.argv[1], newline="")))
rg = {r["addr"]: r for r in csv.DictReader(open(sys.argv[2], newline=""))}
named = {r["cluster_id"] for r in rg.values()}
pd = [r for r in cl if r["program"] == "pd"]
miss = sorted(r["cluster_id"] for r in pd if r["cluster_id"] not in named)
allboth = sorted(r["cluster_id"] for r in pd
                 if all(rg[a]["program"] == "both" for a in r["addrs"].split()))
print("pd clusters with no register row:", len(miss), "| pd clusters whose members are all `both`:", len(allboth), "| the same set:", miss == allboth)' \
  ec/annotations/xdata-clusters.csv ec/annotations/xdata-registers.csv
```

```
pd clusters with no register row: 17 | pd clusters whose members are all `both`: 17 | the same set: True
```

**What that is about, in the firmware.** Those seventeen are `pd` clusters
built entirely out of address *numbers* the main-EC map also uses — which
`xdata_register_map.py`'s own comment on its `PROGRAM_COL` table is careful to
put the other way from a byte: "A row is `both` when the address number is
touched by each program, which is a collision in the numbering and not a shared
byte". So they are the two images' XDATA address spaces overlapping, not a gap
in the PD image's own and not evidence that any byte is shared between them. The
asymmetry is the interesting half: the same condition on a `main-ec` cluster is
harmless, because the shared address's row names that cluster, so the
equivalence above is a property of the `pd` side alone and would not survive
being stated about `main-ec`.

**What it rules out.** A row-count floor per program, and a row-count split
comparison against the clusters CSV, are both claims this tree does not
satisfy, so neither is available as the fix. What is available, and what the
case now holds, is **set coverage**: every program the clusters CSV has is a
program the registers CSV mentions. That survives any re-derivation that moves
the counts, which is the property `CLAUDE.md`'s no-hand-kept-totals rule asks
for and the one `programs_not_mentioned()` is written to.

## 3. The floors, and the negative control

The assertions are in the order that makes them mean anything, and every
figure in them is derived at run time from the two CSVs rather than written
into the suite:

- the registers CSV is **non-empty** — with a derived exhibit naming the
  clusters CSV it was written beside, so the message says what was unchecked;
- it **names every program** its clusters CSV has — `programs_not_mentioned()`
  returns the offenders rather than asserting, so the hold case and the
  control ask one question;
- and only then the **byte-to-key comparison**, routed through
  `key_disagreements()` and over a list read once, with the offender's address
  and both of its keys in the failure message.

**The control is a permanent case, not a transcript**, over one forgery per
shape the case has to survive: a row carrying a different cluster's
`cluster_key`, which is the disagreement and the only thing the comparison
catches by itself; every row deleted; and every row of each program the
clusters CSV has deleted in turn. Each is written to a scratch file and read
back, because what is being modelled is the file a run left behind rather than
a list this case built — a writer that failed partway leaves a well-formed CSV
that still parses, which is why nothing about reading one complains. Each
asserts the assertion that catches it. The per-program forgery iterates the
*clusters* side's programs rather than a typed one, so a census that grew or
lost a program changes which hole it punches; and it is guarded by
`assertNotEqual` against a deletion that removed nothing, because a forgery
that dropped no rows would let the floor pass on the strength of a deletion
that never happened.

**The transcript, and what it is for.** A `/tmp` script rebuilds the guard-off
pair, writes two doctored copies of the real registers CSV — header and no data
row; every `pd` row deleted, every other row untouched — and runs both through
the loop as it stood and through the assertions as they now stand:

```
===== the loop as it stood, over both doctored copies =====
test_the_loop_as_it_stood (__main__.OldLoop.test_the_loop_as_it_stood) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.042s

OK
===== the assertions as they now stand, over the same copies =====
test_the_assertions_as_they_now_stand (__main__.NewFloor.test_the_assertions_as_they_now_stand) ...
  test_the_assertions_as_they_now_stand (__main__.NewFloor.test_the_assertions_as_they_now_stand) (csv='zero data rows') ... FAIL
  test_the_assertions_as_they_now_stand (__main__.NewFloor.test_the_assertions_as_they_now_stand) (csv='every pd row deleted') ... FAIL

======================================================================
FAIL: test_the_assertions_as_they_now_stand (__main__.NewFloor.test_the_assertions_as_they_now_stand) (csv='zero data rows')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/vacuity_demo.py", line 45, in test_the_assertions_as_they_now_stand
    self.assertTrue(
AssertionError: [] is not true : the guard-off registers CSV has a header and no data row, so the byte-to-key comparison below has nothing to compare and passes on the emptiness rather than on the agreement

======================================================================
FAIL: test_the_assertions_as_they_now_stand (__main__.NewFloor.test_the_assertions_as_they_now_stand) (csv='every pd row deleted')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/vacuity_demo.py", line 51, in test_the_assertions_as_they_now_stand
    self.assertEqual(
AssertionError: Lists differ: ['pd'] != []

First list contains 1 additional elements.
First extra element 0:
'pd'

- ['pd']
+ [] : the guard-off registers CSV never names ['pd']

----------------------------------------------------------------------
Ran 1 test in 0.048s

FAILED (failures=2)
```

The first block is the gap: the loop is green over both files. The second is
the case going red over the same two, naming what each one lost. The
`assertTrue` is the one that fires on the empty copy and the `assertEqual` on
the `pd`-deleted one, in the order they are written.

Which assertion *would* catch the empty copy is not the same question, and it
was measured rather than assumed: both floors reach it, because an empty CSV
mentions no program and so fails the coverage floor too. Removing the
non-empty assertion leaves the case unable to pass over an empty CSV — the
mutation was run and the class stays green only because the control asserts
the coverage floor's behaviour directly. The non-empty assertion is kept for
the **diagnosis**: it says the file has no rows, where the coverage floor can
only report which programs went missing.

## 4. The case was not unheld by the suite — it was unheld by itself

This is the calibrated version of the issue's claim, and it is a weaker one.
**A truncated or half-programmed guard-off registers CSV is already caught
today**, by `TheGuardOffRegeneration::test_the_census_is_the_one_6a_measured`,
which asserts that the guard-off and committed registers CSVs cover the same
address universe — `self.assertEqual(set(off), set(on))`. Both of the
absences §1 names lose addresses, so both go red there.

That is not the protection the case needs, for three reasons:

- **It is a census-identity failure, not a coverage one.** The reader is told
  the census moved, which is a different and much larger claim than "this file
  is short". A case asserting §6a reproduction should not be the thing that
  reports a missing header row.
- **It evaporates the moment that equality is loosened.** It is not a floor on
  this property; it is a side effect of another case holding a different one.
  Anything that made the guard-off census legitimately cover a different
  address universe would silently withdraw the only thing standing behind this
  loop.
- **It is one class's incidental collateral.** Nothing in `TheGuardOffRegeneration`
  mentions the agreement, and a reader of it has no reason to know the loop
  depends on it.

So: the case is not *unheld by the suite*, it is **unheld by itself**. That is
an argument for the floors and the control, not against them.

## 5. The committed pair is held by `--check`, and that is not a gap

`TheContentKey::test_the_committed_census_has_no_colliding_keys` has the same
registers half over `ec/annotations/xdata-registers.csv`, and its registers
loop has no floor either. **It is deliberately left that way**, and the reason
is mechanical rather than rhetorical: `xdata_register_map.py --check`
regenerates both committed CSVs from the committed tree and compares them byte
for byte — its `check()` reads each committed file whole and hands it to the
tool's own `diff()` when the bytes differ — and `.github/scripts/agent-gates.sh`
runs that mode. A truncated, emptied or half-programmed committed registers CSV
is a **byte diff** there: caught before the file is read as a census at all,
and caught under the name of the file rather than the name of a collision.

The guard-off pair has no such floor *by construction*: `--no-eq-guard` is
refused together with `--check` and refused again without scratch outputs,
which is the entire reason `TheGuardOffKeyDistinctness` exists at all. That is
the whole difference between the two halves of the issue, and it is why the
fix goes to one and not the other. Recorded in the class docstring as well, so
a reader of the guard-off case learns why the committed one looks different
without opening this file.

## 6. Calibration: what is measured, what is derived, what is structural

- **The `both`/pd split and the seventeen are measurements** over the committed
  pair, and each is printed by the command beside it above. They are counts
  over committed data files, not over this repository's own text. **Only the
  seventeen is single-sourced**: searching the tree's suites for it turns up
  no case holding it by value, so a re-derivation that moved it moves this
  page alone. The split is already held by value in two places, so a
  re-derivation that moved it means moving those suites as well, not this
  page alone —
  `ec/tools/test_xdata_guard_off_row_join.py::TheRowLevelJoin::test_the_denominators_are_the_committed_csv_own`
  pins `(1169, 108, 49)` over `1326` rows of the committed registers CSV,
  which is §2's second line exactly, and
  `ec/tools/test_xdata_cluster_names.py` pins the clusters CSV's `pd: 50`
  (with `main-ec: 389`) in
  `TheGuardOffRegeneration::test_the_census_is_the_one_6a_measured`, and the
  same `pd: 50` again over the export-ownership census in
  `TheExportOwnershipClusters::test_the_440_splits_the_way_6b_prints_it`.
- **The floors are sets, not counts**, and every figure in them is derived at
  run time from the two CSVs — including the per-program forgery's choice of
  which program to delete. `CLAUDE.md`'s rule is the reason, and it is also
  why a count would not have worked: §2 measures why.
- **The equivalence in §2 is exact today and is a claim about the generator's
  `primary` choice, not a law.** If `xdata_register_map.py` were to attribute
  a shared address's row differently, the seventeen would become some other
  number or none; nothing here asserts it is permanent, and nothing in the
  suite holds it.
- **This is not a claim that any census disagrees or that any check failed.**
  The real pair agrees, the real run is clean, and §3's fixtures are
  forgeries — the shape a *writer that failed partway* leaves, which
  `xdata_register_map.py` does not itself emit and which the `--check` byte
  diff on the committed pair would catch before this case ever saw it.
- **The seventeen are not a defect.** They are the expected consequence of one
  address appearing in two images and one row being written for it. This page
  records where they are and what causes them; it does not propose a change to
  the generator, and no register status, hardware or BIOS claim is made or
  implied anywhere in it.
- **The accidental protection of §4 is not relied on** and is not weakened
  either. `test_the_census_is_the_one_6a_measured` is untouched.

## 7. What this opens

- **The per-address/per-program join is now enumerated, not merely stated.**
  Which clusters a registers row can name, and which it cannot, is a property
  of `xdata_register_map.py`'s row builder, and that property itself is
  already written down in
  [`xdata-no-eq-guard-census-scale-join.md`](xdata-no-eq-guard-census-scale-join.md)
  and held by `ec/tools/test_xdata_guard_off_row_join.py::test_a_both_row_mixes_the_main_ec_clustering_with_summed_counts`.
  What this page adds is the enumeration the rule implies but that page does
  not make: *which* clusters go unnamed, and that on the `pd` side the set is
  exactly the all-`both` clusters. Nothing checked here is broken by it: the
  tools that read both CSVs join them on `addr` or read the registers table
  for its address column alone, so they reach the clusters CSV directly and
  the seventeen do not cost them anything. The cost falls on anything that
  reaches clusters *through* the registers table, which is exactly the shape
  the byte-to-key comparison is — and the reason its coverage floor is a set
  over programs rather than a row count is that the table cannot name every
  cluster in the first place.
- **A coverage claim in this suite now has to name its witness.** The class
  docstring's "the property is the claim, not a count" was sound for a
  collision and unsound for coverage; the split is recorded there rather than
  left implicit, and it is the rule a further case here would be held to.