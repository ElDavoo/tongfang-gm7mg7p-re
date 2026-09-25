# The `--no-eq-guard` refusal contract

**Issue #556, 2026-09-25.** `ec/tools/test_xdata_register_map.py` holds the two
refusals `--no-eq-guard` carries, so that neither can be moved, deleted or
reordered without a suite going red. This page is what that suite asserts, how
it was shown to actually fail when the guards are broken, and what it does not
cover.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and the two committed
census CSVs are byte-identical before and after this work. The census figures
quoted below are `xdata-06c2-06db-timers.md` §6a's, re-derivable by the command
that section prints; the counts of suites, tests and CSV rows are this
repository's own, and they move whenever a commit adds one.

## What the flag claims, and where each claim is now held

`--no-eq-guard` re-runs the census with the `==` rejection turned off, so the
pre-#178 classifier stays measurable from the committed tree. It carries three
claims, and until now only the first was tested.

| | claim | held by |
|---|---|---|
| 1 | it flips exactly the `==` snippets in `CLASSIFIER_SHAPE` and nothing else | the tool's own `--self-test`, at `xdata_register_map.py:2467-2487`, and `test_xdata_cluster_names.py::TheGuardOffRegeneration`, which runs the census the flag produces — but that class has been in error in `setUpClass` since #528 and runs none of its six cases (see below), so of the two only the first is green today |
| 2 | it is refused with `--check` and with `--self-test` | `Refusals.test_it_is_refused_with_check`, `..._with_self_test` |
| 3 | it is refused unless given scratch `--out-registers` **and** `--out-clusters` | `Refusals.test_it_is_refused_bare_with_the_default_outputs`, `..._with_scratch_registers_only`, `..._with_scratch_clusters_only` |

Claim 3 is the one that matters, and the hazard is specific. `OUT_REGISTERS`
and `OUT_CLUSTERS` (`xdata_register_map.py:298-299`) default to
`ec/annotations/xdata-registers.csv` and `ec/annotations/xdata-clusters.csv`,
which is what `check_cluster_citations.py` reads and what every `main-ec-NNN`
citation in the tree names. A bare `--no-eq-guard` run therefore writes the
pre-#178 census over both, and the two files it lands on are what the rest of
the tree is keyed to.

**That run is caught, but loudly and by other tools — not silently, and not by
these two files agreeing with each other.** `--check` is refused with
`--no-eq-guard` (guard 1, `:3618`), so it always regenerates the *guard-on*
census and compares the on-disk file to that. A guard-off file can never match
it, by construction: an on-disk guard-off file and a fresh guard-on generation
disagree by definition, not by accident. So the harm a bare run gets to do is
a corrupted committed source of truth plus a red `--check` and a red
`check_cluster_citations.py`, not a wrong census that quietly certifies itself.
No mutation is needed to see it — write a guard-off census to scratch, then
point `--check` at it:

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/guardoff-r.csv --out-clusters /tmp/guardoff-c.csv
wrote /tmp/guardoff-r.csv: 1171 rows
wrote /tmp/guardoff-c.csv: 439 rows
$ python3 ec/tools/xdata_register_map.py --check \
    --out-registers /tmp/guardoff-r.csv --out-clusters /tmp/guardoff-c.csv
/tmp/guardoff-r.csv differs from a fresh generation (1172 on disk vs 1172 generated) -- run without --check to rewrite
/tmp/guardoff-c.csv differs from a fresh generation (440 on disk vs 431 generated) -- run without --check to rewrite
  names: seeded 10, exact 0, carried by overlap 0, tied, not carried 0, with no name 420
$ echo $?
1
```

Against the committed CSVs the same command exits **0**, 1,171 and 430 rows
matching. With guard 2 deleted in a scratch `ec/`, a bare run does overwrite
both committed files, and the fallout is again loud rather than silent:
`--check` exits 1 naming both files, and `check_cluster_citations.py` reports
**45** disagreements — 37 in `ec/annotations/`, 8 in `docs/`. Both totals are
this tree's and move as the tree's citations do; the split is what makes 45
reconcilable with a 37 measured over `ec/annotations/` alone.

**The tool's own comment said otherwise, and said so in this write-up's first
draft too.** `xdata_register_map.py:3623-3626` claimed, from #528, that a bare
run leaves `--check` green "because the files now agree with each other". That
is false on this tree, for the reason above, and the comment is corrected in
place here rather than left standing for the next reader to re-derive from.
This paragraph originally restated the comment as if it were a measurement;
it is a disproof of it.

## The tripwires are the design, not the decoration

Each refusal case replaces every one of `main()`'s mode entry points —
`self_test`, `threshold_sweep`, `co_reading_sweep`, `co_reading_group_table`,
`collapse_co_readings`, `map_census`, `reconcile`, `check`, `write` — with
recorders, and then asserts three things: no mode ran, the exit code was
non-zero, and both committed CSVs are byte-identical to the snapshot taken
immediately before.

Asserting the third alone would be satisfied by a run that wrote **identical
bytes**. What `main()`'s own comment claims is stronger — the refusal happens
*before* any mode runs — and that is the property that has to be tested, because
the named failure is a refactor that relocates an `ap.error` below the dispatch.

That ordering is the point. If a guard regresses, the tripwire fires, the
assertion fails, and the real `write()` never runs: **a failing run of this
suite cannot damage the repository.** A test that could overwrite the two
census files *as a side effect of reporting a regression* would be the wrong
place to pin this property.

**The list is nine long because #566 made it nine, and the gap would have been
silent.** The branch was written against a six-entry dispatch; #566 added the
three co-reading modes, and a tripwire naming only the old six would have let a
relocated guard reach one of the three it did not mock. That is not a
hypothetical failure mode: none of the three writes anything, so a run that
reached `co_reading_sweep` instead of `write` would have left both committed
CSVs untouched and every refusal case still green. `TripwireCoverage` now reads
the entry points out of `main()`'s own AST and fails on a tenth mode rather
than going unmocked.

## Shown to fail, not merely shown to pass

A green suite proves nothing on its own, so each guard was broken in a scratch
copy of `ec/` — a copied `annotations/` with `decompiled/`, `firmware/` and
`ghidra/` symlinked back — and the suite re-run. Every mutation was reverted
immediately and the mirror's census CSVs were compared after each one. The five
rows below are what that run says **on the tree this work lands on**, with the
suite at 12 tests rather than the 11 it had on its own branch. Rows one, three
and four reproduce what the branch recorded; row two is a placement its recipe
did not distinguish, and row five now fails twice where it failed once.

| mutation | what the suite said | census CSVs after |
|---|---|---|
| guard 2 (the `or` at `:3627-3628`) moved below the dispatch | 3 failures, each `Lists differ: ['write'] != []` | byte-identical |
| guard 2 moved below the `if args.*` chain but above the fallthrough | **12 tests, green** | byte-identical |
| guard 1 (`:3618`) moved below the dispatch | 2 failures, `['check']` and `['self_test']` | byte-identical |
| guard 1 deleted outright | 2 failures, `['check']` and `['self_test']` | byte-identical |
| `--no-eq-guard` made a no-op in `census_and_groups()` | 2 failures: `3195 not greater than 3195`, and the not-a-copy case | byte-identical |

**The first three rows are the ones the case design was changed for.** Written
the obvious way — `--no-eq-guard --check` at the default outputs — moving guard
1 below the dispatch was caught, but by the *wrong* assertion: the second guard
was still above the dispatch and caught the same run, so the case failed on a
message mismatch while the tripwire never fired. Passing scratch outputs in the
`--check` and `--self-test` cases removes the second guard as a possible cause,
so each case now tests the guard it is about and a relocation trips the wire
directly. The issue's literal invocation is still covered: the bare case is
that run with the flag alone, and it is the only one where a mode would reach
the committed paths.

**"Below the dispatch" has to mean past the fallthrough, and the second row is
why that is worth saying.** A guard parked between the `if args.*` chain and the
trailing `return write(args)` is still, in every sense the property cares about,
*above* the dispatch: a bare `--no-eq-guard` run is refused, no mode runs, and
nothing is written. The suite is green on that relocation, and it is right to
be — the hazard does not exist there. Move the same guard one line further
down, past `return write(args)`, and the write has already happened before the
refusal is reached. The recipe in the first row is the second placement, which
is the only one of the two that damages anything; the recipe is what the table
above measures, not "somewhere below the guards".

**The last row is why the effect assertion is directional.** The guard only
ever *removes* writes, so the guard-off `write` total is strictly greater than
the committed one and at least one address differs — a relation that survives
an unrelated re-derivation of the census, where a pinned count would not.
Measured on this tree: **4,028 guard-off against 3,195 committed `write`
references, 210 of 1,171 addresses differing**, and 0 of 1,171 `refs` totals
differing — §6a's "210 of 1,171" and "0 of 1,171", still reproducing.

That row used to fail on the directional case alone. It is two failures now,
because #566 regenerated the committed census and the not-a-copy case has
become a second opinion rather than an existence claim: with the committed CSV
matching a fresh generation, a run that ignored the flag would reproduce it byte
for byte. The directional one stays load-bearing — a tree that had moved since
§6a measured it would still be caught by the relation and not by the bytes.

Each total sums the `write` column over every row of the register CSV, and the
CSV's own `program` column splits those 1,171 rows three ways, not two:
`main-ec` (1,014 addresses), `pd` (109) and `both` (48). Summing all three
buckets gives 3,577 + 193 + 258 = 4,028 guard-off and 2,835 + 142 + 218 = 3,195
committed. §6a's main-EC and PD rows therefore *omit* the `both` bucket rather
than subtracting a double count — 2,835 + 142 = 2,977 and 3,577 + 193 = 3,770,
neither of which is a total above.

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/before-registers.csv \
    --out-clusters  /tmp/before-clusters.csv
$ python3 -c "
import csv, collections
for p in ('/tmp/before-registers.csv', 'ec/annotations/xdata-registers.csv'):
    w, n = collections.Counter(), collections.Counter()
    for r in csv.DictReader(open(p)):
        w[r['program']] += int(r['write']); n[r['program']] += 1
    print('%-34s' % p, {k: '%d over %d' % (w[k], n[k]) for k in ('main-ec', 'pd', 'both')}, '=>', sum(w.values()))
"
/tmp/before-registers.csv          {'main-ec': '3577 over 1014', 'pd': '193 over 109', 'both': '258 over 48'} => 4028
ec/annotations/xdata-registers.csv {'main-ec': '2835 over 1014', 'pd': '142 over 109', 'both': '218 over 48'} => 3195
```

## Calibration

- **The exit code is pinned as non-zero, not as `2`.** `ap.error` happens to
  raise `SystemExit(2)` today. Rewriting the refusal as `print(...); return 1`
  would still be a refusal, and failing that would be a false alarm about the
  property that matters. The load-bearing half — no mode ran, the committed
  CSVs are untouched — is asserted directly, so the looser exit spelling costs
  nothing in safety.
- **The effect is asserted as direction, not as counts.** 833, 210, 3,577 are
  §6a's figures, recorded on a committed page. Pinning them here would make
  this suite red for an unrelated re-derivation, which is a §6a and
  `docs/findings.md` matter, not a refusal-contract one.
- **The refusals are asserted to be a CLI contract, never anything about the
  EC.** The suite reads the same committed text files the tool reads.

## Three suites are already red on `main`, and one of them is this flag's doing

`bash tools/run-tests.sh` on this tree is **19 of 22 suites passing**. All
three failures reproduce byte-for-byte on a pristine `git archive origin/main`,
so none is caused by this work and none is absorbed by it. Recorded here
because a reader running the runner will hit all three, and because the first
one is a regression **from the commit that added the flag this issue is about**
(#528).

**`test_xdata_cluster_names.py::TheGuardOffRegeneration` — 6 tests, none of
which run, and 1 error in `setUpClass`.** The module reports `Ran 21 tests …
FAILED (errors=1)`.
Its `GUARD` recipe is the literal line pair

```python
    if stripped.startswith("=="):
        return False
```

and that pair **no longer exists in the tool.** #528 threaded the flag through
as a parameter — `store_target(text, start, end, eq_guard=True)` at `:1220`,
`if eq_guard and stripped.startswith("==")` at `:1243`, carried to `scan()` at
`:1604` and flipped by `not args.no_eq_guard` at `:2292` — so deleting the two
lines no longer removes the rejection; it removes a conditional and the guard
stays on for every run. The suite's own guard against exactly this fires
first, which is why the error is an `AssertionError` and not a silently
doubled census: *"the `==` guard is not where §6a's recipe deletes it; the
guard-off census this suite builds is not the one §6a measured."*

The flip used to sit in `generate()`; #566 moved the census into
`census_and_groups()` when it added the co-reading relation, so the line to
follow moved with it. That is the third time this recipe has been re-pointed at
a line number, which is itself the argument for the flag.

So, as of this tree, **the accepted run in `test_xdata_register_map.py` is
the only working scripted route to a guard-off census from the committed
tree** — the only one of the two checked-in suites that needs no hand-edit
of the tool. The sibling's §6a route — copy the tool and patch it — is what
the flag was built to replace, and the build broke the thing it replaced. The
fix belongs with the follow-up that makes the two mechanisms agree (delete the
`==` branch from the `if eq_guard and …` line instead, or drop the class in
favour of this suite's run); it is **not** fixed here, because it is a
regression in another file from another issue and the fix is a one-line recipe
change that deserves its own PR rather than a drive-by in an unrelated one.

**`test_check_site_census.py` — 45 tests, 1 failure.** 14 disagreements
between `xdata-086x-dispatch-sites.csv`, `xdata-0860-census-sites.csv` and the
census, all of them `bank0/D091.c` and the `0x0860` occurrences in it. It is
the line-pin drift `docs/findings/name-basis-and-groups.md` (issue #135) records
under "A consequence worth recording: a plate line moved a pinned citation".
That CSV pins **line numbers** into the committed `.c`, and the pins no longer
land on the `XDATA_0860` occurrences the census reads — `:44,48,70,74,82` cited
against `:45,49,72,77,84` found — so the tool emits the message that page
quotes, *"the line moved, or the reference was dropped"*. That page records the
first time this happened and the re-pin that closed it (#432); the mover this
time is **#503**, which edited `D091.c` to name the incoming accumulator and
shifted the bodies again. `check_site_census.py` is green at `0b04a8b9^` (7
sites agree, 17 occurrences accounted for) and red with exactly these 14 at
`0b04a8b9`, so that one edit is the whole of it.

It is **not** the drift `test_xdata_cluster_names.py`'s
`TheGeneratorsAreUnchanged` steps around: that class names neither `D091` nor
`0x0860`, its comment is about `bank0/CC64`'s annotation adding an address, and
the equality it steps around is a whole-file identity comparison — a different
file, a different check. Untouched here; neither census CSV is regenerated,
re-keyed or swept by this work.

**`test_check_cluster_citations.py` — 46 tests, 1 failure.** One citation in
`docs/findings.md` disagrees with the committed census, and it is **main's own
prose**: §26 reads the reset vector's `0xD96C` and writes that the three bytes
it "steps over" "are the whole of the `main-ec-081` cluster" — `0x0800` is not
in `main-ec-081` in the committed census, and which half of that sentence is
wrong is a finding for #564 to make in place rather than a formatting fix this
issue absorbs:

```console
$ python3 ec/tools/check_cluster_citations.py
docs/findings.md:5520: 0x0800 is not a member of any cluster this line names (`main-ec-081`); it is a member of `main-ec-100`
1 citation(s) disagree with ec/annotations/xdata-clusters.csv
```

That is #564's correction to make in place — either the `main-ec-081` name or
the membership claim is wrong, and which one is a finding, not a formatting
fix. It is recorded here because this suite is a reader of `docs/findings.md`
and a reader running the runner will hit it, and it is left unfixed because it
is another file's finding from another issue.

## The `--check` verdict, before and after

The requirement for this change is *"this changed nothing about the verdict"*,
**not** *"the verdict is green"*. On the tree this work lands on, `--check` is
**green**, and it was green before this work — main's #566 regenerated the two
CSVs when it added the co-reading columns, which is what cleared #326's symptom:

| | exit | the two CSVs against a fresh generation |
|---|---:|---|
| pristine `origin/main` | 0 | `xdata-registers.csv` 1,171 rows match, `xdata-clusters.csv` 430 rows match |
| this tree | 0 | the same two, and the full output is byte-identical once the repository path is normalised out |

**The refusals are worth pinning on this tree for the reason they were worth
pinning on the branch's, and not for a sharper one.** A green `--check` here
does not make a bare `--no-eq-guard` run any less damaging than it was when
the check was red: `--check` is refused with the flag, so it regenerates
guard-on either way and a guard-off file fails it either way. The run is caught
immediately and loudly — `--check` goes red on both files,
`check_cluster_citations.py` goes red with 45 disagreements — because `--check`
and the citation check both re-derive from the committed tree and neither can
be satisfied by a census that was written with the guard off.

What the refusals buy is narrower and is worth saying precisely: they stop the
run **before** it writes. The harm a run gets to do is a corrupted committed
source of truth plus two red checks, and the refusals reduce that to nothing,
rather than leaving the repository's integrity to a reader noticing the red
afterwards. That is a real saving, but it is a saving on a *detected* failure,
not on a silent one.

## What this suite does not cover

- **Not a gate arm.** `.github/scripts/agent-gates.sh` compiles it
  (`check_python_syntax` globs `ec/tools/*.py`) and does not run it. Adding the
  run is a `.github/` change, which the pipeline token has no `workflow` scope
  for, and it belongs to **#512** in any case. `tools/run-tests.sh` picks the
  file up with no wiring edit, because it discovers by `find`.
- **`--check --self-test --no-eq-guard` together.** Refused, but by argparse's
  mutually-exclusive group. That is testing argparse, and the resulting exit
  code is indistinguishable from a guard firing.
- **The `--self-test` redness on `main`.** Pre-existing, and #566's gate
  comment names the cause and deliberately leaves the mode out of the gate: the
  annotation CSV has **renamed 17** functions that `ec/decompiled/index.csv`
  still spells `FUN_CODE_*`, so the "annotation CSV and index.csv agree" check
  at `xdata_register_map.py:2431` fails and clearing it means re-exporting the
  generated decompiled tree. The direction is the easy half to get backwards:
  the hand-annotated side is the one that moved — all 17 are
  `ff_filler_not_a_function_*`, the names #561's byte scan gave them — and
  `index.csv` is the side still holding Ghidra's placeholder. All 17 are
  `common` listings inside `docs/findings.md` §28's unprogrammed
  `0x728F`-`0x7FFF` band, and not one of them is in the census, so the redness
  is entirely outside what the census measures. This bullet first gave the count
  as three; a reader who goes looking for that 3 will find it in a different
  assertion, the `--no-eq-guard` block's own "flips exactly the 3 `==` snippets"
  line at `:2482-2484`. The 17 is the tool's own loader pair, so it needs no
  interpretation:

  ```console
  $ python3 -c "
  import sys; sys.path.insert(0, 'ec/tools')
  import xdata_register_map as xrm
  funcs, _ = xrm.load_index(); names = xrm.load_names(funcs)
  bad = [(k, r['name']) for k, r in funcs.items() if names[k][0] != r['name']]
  print(len(bad), 'disagreements, all', sorted({k[0] for k, _ in bad}))
  "
  17 disagreements, all ['common']
  ```

  `--check` is no longer part of this — it is green, and #566 wired it into the
  gate. Making `--self-test` green here would silently absorb #512 and #433.
- **Agreement with `test_xdata_cluster_names.py::guard_off()`.** That case
  reaches the same guard-off census by a different mechanism — deleting the
  `==` guard line rather than passing the flag — so the two are independent
  rather than redundant. A case asserting the two agree is a reasonable
  follow-up; it is not this issue.
- **`--export-ownership`'s own pair of refusals.** #565 added a second flag
  carrying the same two guards for the same two reasons, immediately below the
  `--no-eq-guard` pair and immediately above the same dispatch
  (`xdata_register_map.py:3644-3653`), and this suite pins only the
  `--no-eq-guard` half. The tripwire would catch a relocated `--export-ownership`
  guard just as well — it mocks the same nine entry points — so the coverage is
  one flag short of what the dispatch now carries, and that is recorded here
  rather than quietly widened, because a third flag is not this issue's to add.
- **The committed census CSVs.** Not regenerated, not re-keyed, not swept. They
  are what the refusal contract exists to protect, so a suite that rewrote
  them to check something about their contents would contradict its own point.

## One observation, left as a follow-up

`tools/README.md` carried "twenty today, 551 tests in all" against a table of 19
suites, and both numbers were stale on `main` before this work: there were 20
suites and **547** tests. This work adds one suite and corrects the two count
words to the measured figures; it does not add the missing row for
`ec/tools/test_group_functions.py` — 24 of them — because that is a shared-file
edit about a different file and the table is the most contested surface in the
tree. The measured numbers have since moved twice more, from #566 and #564
landing together with this and then #565 landing under it: **22 suites and 587
tests** on the tree this lands on, of which this suite is 12, and `main` alone
is 21 and 575. The table is now two rows short rather than one —
`test_export_ownership.py` (26 of them, #565) is unlisted for the same reason
`test_group_functions.py` is. The count is printed by the runner, so it is a
thing to re-measure rather than to maintain by hand.
