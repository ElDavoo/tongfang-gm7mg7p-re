# The guard-off generation's `cluster_key` distinctness had no case behind it, and the coverage sentences named two of the four censuses (issue #962)

**Nothing here is a hardware claim.** No register was read back, no image was
opened, and no laptop, EC or Windows machine is involved. Every transcript
below is the output of a command over a committed CSV, over a regeneration of
one, or over a doctored copy of such a regeneration, with every scratch output
under `/tmp` and nothing written into the tree. **The committed census files
are the only real inputs** — `ec/annotations/xdata-clusters.csv`,
`ec/annotations/xdata-registers.csv` and guard-off regenerations of them, all
of them files — plus, for the two `e169a0e4` rows of §4 and nothing else, that
commit's decompiled tree. The one fixture in here is a duplicated `cluster_key`
that `cluster_key`'s own content hash would never emit, and §3 says why that is
the point rather than a flaw. Same framing as
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md):3-23,
which is the page this is a follow-up to and whose §5 second bullet this
change makes false.

**The calibration comes first, and it is the same narrow claim #929 made: no
published figure moves.** §4 re-derives all four censuses of that page's §4
table and the movement and cell figures on this tree, and gets every one of
them back. What is below is that the *producer* half of the check had nothing
standing behind the guard-off census — the census `cause`'s rates divide by —
and that the sentences stating the coverage named two of the four censuses in
a voice that read as all of them. A gap in what a suite would say, and an
overclaim in a docstring, corrected in place. Not a collision found.

## 1. Which census was unheld, and why it is the one that matters

Four censuses are reachable by a view that re-keys one. Three are behind a case
after this change; one is not, and it is not a case of picking the least
interesting row of the table.

| # | census | behind a case | by what |
|---|---|---|---|
| 1 | `ec/annotations/xdata-clusters.csv` as committed (439 rows) | yes | `test_xdata_cluster_names.py::TheContentKey::test_the_committed_census_has_no_colliding_keys` |
| 2 | a fresh **guard-on** generation over this tree (439 rows) | yes | the two `check()`s at `xdata_register_map.py:4439-4451`, inside `--self-test` |
| 3 | the **guard-off** regeneration of the committed pair (445 rows) | **yes, by this change** | `test_xdata_cluster_names.py::TheGuardOffKeyDistinctness::test_the_guard_off_census_has_no_colliding_keys` |
| 4 | the 430-row pair at `e169a0e4` — both its committed census and its guard-off regeneration | **no** | nothing; see below |

**Why row 3 is the one that was missing.** Both producer checks are guard-on by
construction and cannot be pointed anywhere else: `--no-eq-guard` is refused
together with `--check` and `--self-test` at `xdata_register_map.py:4976-4978`,
and `:4985-4987` refuses the flag without scratch outputs. That is a correct
refusal — the flag changes what the census says — and this change does not
relax it. [`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md)
and `ec/tools/test_xdata_register_map.py::Refusals` hold it, and moving it is a
different issue. The coverage had to come from the suite instead, which is
what §2 adds.

It is row 3 rather than either other row because it is the census every rate in
`cause` is a rate *of*. `cause_report` re-keys the guard-off pair for its
population, and that population is:

- the `N guard-off key(s)` figure the report's header prints, per generation;
- the `population` column every rate in the four-cell block divides by, so a
  short map is a short denominator and every ratio beside it is quietly wrong;
- `holders_by_program`'s census, and the per-cell lookup's
  (`ec/tools/xdata_moved_ranks.py`).

A collision does not fail such a run. It makes a count smaller, and a smaller
count reads as a smaller measurement — which is why
`xdata-moved-ranks-collision-scope.md` §5 put the check at each *view* in the
first place, and why a census no case reaches was the gap left over.

**Why row 4 is the one that stays open.** Reaching either of its censuses needs
the decompiled tree at `e169a0e4`, which this tree does not have and which no
case in `ec/tools` can synthesize from committed text. Its two rows of §4 are
hand-measured transcripts and stay that way. This is a statement about this
suite, not about that pair: nothing here says its keys are or are not distinct,
and §4 measures it rather than asserting either way.

## 2. The cases, and what each one holds

`ec/tools/test_xdata_cluster_names.py::TheGuardOffKeyDistinctness`, three cases
over the one `guard_off()` regeneration the module already caches (~2 s,
`lru_cache`d, shared with `TheGuardOffRegeneration` — no second run).

**`test_the_guard_off_census_has_no_colliding_keys`** is the hold case. It asks
`xdata_moved_ranks.py`'s own `duplicate_keys()` — the same function every
`cluster_key unique ...` / `CLLISION` line in a report is printed from, reached
by the same `importlib` route the module already uses for `xdata_register_map.py`
— so the suite's check and the report's printed line cannot drift into being
two implementations of the same question. The failure message names the
colliding keys **and the ranks carrying each**, not a bare count: "N collisions"
sends a reader back to the tool to find out which, which is the tool's job and
not the failure message's.

**`test_the_guard_off_registers_csv_agrees_with_its_clusters`** is the second
half of `TheContentKey`'s case, over the pair this generation wrote rather than
the pair on disk. Held twice because the guard-off CSVs are the ones no reader
looks at: they land in a scratch directory and are gone with the next run, so
a registers CSV that disagreed with its own clusters CSV would break the
byte-to-key lookup there and be caught by nobody.

**`test_a_duplicated_key_is_named_with_both_its_ranks`** is the negative
control; §3 is its transcript.

Three things about the shape of this, each deliberate:

- **A sibling class, not an eighth case in `TheGuardOffRegeneration`.**
  `docs/findings.md` §50 calls that class's seventh case "a seventh case", and
  an eighth would falsify a sentence this change has no business touching.
  `TheExportOwnershipClusters` gives the same reason for itself.
- **The property is the claim, not a count.** Nothing pins 445 or 439. The row
  count appears in the failure message, where a reader chasing a collision sees
  it, and nowhere else — the same reasoning `TheGuardOffRegeneration` applies to
  its `> 300` floor and its `assertTrue(movers, ...)` exhibit.
- **It runs in the default sweep.** `bash tools/run-tests.sh` collects
  `ec/tools/test_*.py`, so the property is now held by a run CI performs.
  `xdata_moved_ranks.py --self-test` keeps its 53 checks unchanged; the issue
  this answers is #921's, that `--self-test` is not gated, and adding a 54th
  check there would not have moved it.

## 3. The negative control

A hold case that has never gone red is a case that has never been shown capable
of going red. This one is shown, and shown permanently: the third case copies
one row's `cluster_key` onto a second row and asserts that the predicate names
that key and both ranks. The fixture is a **forgery** — `cluster_key` is a
content hash over the program and the sorted membership, so two different
memberships sharing one key is not something this tool emits. That is the
point rather than a flaw in the fixture: the collision the precondition exists
to catch cannot come from the generator, only from a census assembled by
something else.

The hold case itself, run against a doctored copy of the real guard-off
census, is the other half. `/tmp` script over the committed tree — it rebuilds
the guard-off census, copies one row's key onto a second row *of the census
file*, points `guard_off()` at the copy, and lets `unittest` report:

```
the real guard-off census: 445 rows, 445 distinct cluster_key, 0 collision(s)

forged: main-ec-002 now carries main-ec-001's key kb224d2c2f0c2

FAIL: test_the_guard_off_census_has_no_colliding_keys
  (tcn.TheGuardOffKeyDistinctness.test_the_guard_off_census_has_no_colliding_keys)
----------------------------------------------------------------------
Traceback (most recent call last):
  File ".../ec/tools/test_xdata_cluster_names.py", line 1066, in test_the_guard_off_census_has_no_colliding_keys
    self.assertEqual(
AssertionError: {'kb224d2c2f0c2': ['main-ec-001', 'main-ec-002']} != {}
- {'kb224d2c2f0c2': ['main-ec-001', 'main-ec-002']}
+ {} : 1 colliding cluster_key(s) over the 445 guard-off row(s) -- kb224d2c2f0c2 on main-ec-001, main-ec-002

Ran 1 test in 0.003s

FAILED (failures=1)
```

The negative-control case is the standing version of that transcript: same
predicate, same forged census, asserted rather than demonstrated once.

## 4. No published figure moves, re-derived rather than asserted

**All four censuses, each with the command that derives it.** The counting step
is the same in all four:

```sh
python3 -c 'import csv, sys
rows = list(csv.DictReader(open(sys.argv[1], newline="")))
keys = {r["cluster_key"] for r in rows}
print(f"{len(rows)} rows, {len(keys)} distinct cluster_key, "
      f"{len(rows) - len(keys)} collision(s)")' CLUSTERS.csv
```

| census | rows | distinct `cluster_key` | collisions | deriving command |
|---|---:|---:|---:|---|
| `ec/annotations/xdata-clusters.csv` | 439 | 439 | 0 | the command above, on that path |
| the 430-row census at `e169a0e4` | 430 | 430 | 0 | `git archive e169a0e4 \| tar -x -C /tmp/old`, then the command on `/tmp/old/ec/annotations/xdata-clusters.csv` |
| guard-off regeneration of the 430-row pair | 439 | 439 | 0 | `(cd /tmp/old && python3 ec/tools/xdata_register_map.py --no-eq-guard --out-clusters /tmp/der/old-off-clusters.csv --out-registers /tmp/der/old-off-registers.csv)`, then the command on that CSV |
| guard-off regeneration of the 439-row pair | 445 | 445 | 0 | `python3 ec/tools/xdata_register_map.py --no-eq-guard --out-clusters /tmp/der/off-clusters.csv --out-registers /tmp/der/off-registers.csv`, then the command on that CSV |

Identical to the four rows
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
§4 publishes, which is the claim: the merged tree did not move any of them.

**The archive is the right input, and here is the check** rather than the
assertion: the extraction reproduces that tree's own 430-row census, and
`xdata_register_map.py` says so on its own stdout —

```
$ (cd /tmp/old && python3 ec/tools/xdata_register_map.py --out-clusters /tmp/der/old-on-clusters.csv \
     --out-registers /tmp/der/old-on-registers.csv)
wrote /tmp/der/old-on-clusters.csv: 430 rows
  main-ec: 1062 distinct addresses, 13964 references, 380 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 50 clusters at threshold 0.5
```

A guard-on generation from the extracted tree is 430 rows, which is the
committed length of that commit's own census. Had the archive resolved to some
other commit, this is where it would have shown.

**The movement and cell figures, re-derived the same way.** All come back
unchanged:

| figure | published | measured | deriving command |
|---|---:|---:|---|
| moved / intact, `e169a0e4` pair (430 → 439) | 366 / 64 | 366 / 64 | `python3 ec/tools/xdata_moved_ranks.py pair --old /tmp/old/ec/annotations/xdata-clusters.csv --new /tmp/der/old-off-clusters.csv --label e169a0e4` |
| moved / intact, merged pair (439 → 445) | 315 / 124 | 315 / 124 | the same with `--old ec/annotations/xdata-clusters.csv --new /tmp/der/off-clusters.csv` |
| `366 - 315` | 51 | 51 | the two `moved` lines above, subtracted |
| `cause` cells moved→intact / moved-in-both / intact→moved / intact-in-both | 71 / 266 / 23 / 40 | 71 / 266 / 23 / 40 | `python3 ec/tools/xdata_moved_ranks.py cause --old-a /tmp/old/ec/annotations/xdata-clusters.csv --new-a /tmp/der/old-off-clusters.csv --old-b ec/annotations/xdata-clusters.csv --new-b /tmp/der/off-clusters.csv --old-a-registers /tmp/old/ec/annotations/xdata-registers.csv --new-a-registers /tmp/der/old-off-registers.csv --old-b-registers ec/annotations/xdata-registers.csv --new-b-registers /tmp/der/off-registers.csv --label-a e169a0e4 --label-b merged` — `cause` refuses to run without all four `--*-registers`, so the table above is a two-line command with a long tail rather than a short one |

Both `pair` runs print the collision line this change is about, over the guard-off
census each read, and both are clean:

```
  cluster_key unique across the 430 committed row(s): 0 collision(s)
  cluster_key unique across the 439 guard-off row(s): 0 collision(s)
```

## 5. Calibration: what is and is not claimed

- **This is not a claim that any census collides.** All four measure 0
  collisions today, §4 re-derives that, and #929 measured it first. Nothing here
  refutes `TheContentKey`'s uniqueness assertion or `xdata_register_map.py`'s
  content hash, and nothing here is evidence about a real cluster.
- **Three of four is an enumeration, not a target.** It falls out of §1's table:
  the committed census, a fresh guard-on generation, and the guard-off
  regeneration are each behind a named case, and the `e169a0e4` pair is behind
  none. The requirement worth holding is the narrower one — that a sentence
  naming the coverage says *which* censuses it reaches, and says plainly that
  the `e169a0e4` pair is not among them. A suite that grew to four would be
  better; a sentence that said "four" today would be the overclaim.
- **The two `e169a0e4` rows of §4 are hand-measured transcripts, and no suite
  in this repository can hold them.** They are listed because this run read
  them and re-derives them on demand (§4 prints the extraction), not because a
  case would notice if they moved. A reader wanting a guarantee there needs
  that commit's decompiled tree checked out, which §1 says.
- **The forged census of §3 is not evidence about any census.** A duplicated
  `cluster_key` is a fixture the tool's own hash cannot produce, for the reason
  §3 gives. The check has to hold for one anyway, because the census it is not
  guaranteed to receive is written by a regeneration rather than by
  `xdata_register_map.py`'s hash of the same tree.
- **No refusal was relaxed.** `--no-eq-guard` is still refused with `--check`
  and `--self-test` and still refused without scratch outputs, and
  `ec/tools/test_xdata_register_map.py::Refusals` and
  [`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md)
  are untouched. Its row 1 says the guard-off class "runs the census the flag
  produces", which was true before this and is still true; it is now merely less
  than what the suite checks.
- **`--self-test` keeps its 53 checks.** The coverage belongs in the default
  sweep, which is the issue's point about #921. `xdata_moved_ranks.py` is
  changed in one docstring and no code.
- **No gate was wired.** `.github/scripts/agent-gates.sh` is copied from the
  pipeline template, and the check belongs in the sweep rather than in the
  cheap tier, for the reason
  [`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md)
  §5 gives.
- **The red set is unmoved.** `test_check_cluster_citations` is red on this
  merge exactly as on the base — 48 tests, one failure, #822's
  `xdata-cluster-names-guard-off-recipe.md:220` on `0x0464`/`0x0465` — and this
  file adds no disagreement to it.

## 6. What this opens

- **The per-pin table moved, 25 rows with it, and 8 verdicts were re-read.**
  Editing `guard_off()`'s docstring in `test_xdata_cluster_names.py` and adding
  a class to it shifted every line below the import block by 34, and a
  registered `test_*.py:NNN` pin names a *line* — so the line it lands on moved
  under every pin into that one file. All 25 affected shape cells were
  re-derived from the census's own `--verbose` run rather than by reading the
  file, the published `5/19/10/6/34` landing-shape split became `0/16/22/5/31`
  and both places that pin it were re-derived to the measured value rather than
  loosened, and **eight verdicts that had gone stale were re-read** — the pins
  that left a `def test_` header or an assertion. That is why
  [`test-line-pin-census.md`](test-line-pin-census.md)'s "the eleven that do not
  carry" is now nineteen, and its item 9 records them. **The read column
  (`53/19/2/32`), the headcounts (106 pins, 28 files, 79 spellings, 58 targets,
  74 resolving, 32 declined) and the red set are all unchanged**, which is the
  control that makes the shape the one column a line shift moves on its own.
  No citing prose is repointed here — that file's rule is that a change which
  invalidates a citation does not get to fix it — so the eight repoints are
  follow-ups, and each verdict cell names its target's new line so a re-pointer
  has the destination rather than the arithmetic.
- **`TheExportOwnershipClusters` is now two of a kind, not a special case.**
  Two classes hold a regeneration's own key distinctness and each carries a
  documented reason for not being a case in `TheGuardOffRegeneration`. A third
  flag whose census no `check()` can be aimed at would be worth a sweep for the
  same reason: the shape to look for is any census written to scratch that only
  a view can reach.
