# The guards table is a reading of `main()`, and a flag with no guard is still uncovered

**Issue #695, 2026-10-03.** `ec/tools/test_xdata_register_map.py`'s
`GUARDED_FLAGS` was the last hand-kept entry-point table in that suite. After
#675 made `MODES` a reading of `main()`'s own AST, this one was checked against
nothing: a third flag added to the parser with its two refusals would have been
parsed, guarded and never exercised, because the `Refusals` cases loop over
the table and a flag not in it is not in the loop. This page is what the table
holds now, the reading that gets it there, the one shape dependence that
survives and is measured rather than hoped away, the mutations that show it going
red, and — the half the issue asked to be decided rather than assumed — what is
still not covered and the measurement that says what would cover it.

Its predecessors are
[`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md) for
the dispatch reading this one is a sibling of, and
[`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md)
for the refusal contract the table under test exists to pin. This page names
symbols rather than line numbers throughout, for the reason those pages give:
those numbers move.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and every case runs
offline against committed text. `xdata_register_map.py` is not edited by this
change; the whole of it is in the test's reading of the tool, which is what the
dispatch sibling says of its own. The two committed census CSVs are
byte-identical before and after this work, and after every mirror run below.

## What the table held, and what it holds now

The suite's module docstring said, under "Not tested, deliberately": *"And no
*third* flag is covered: the two here are the two `main()` carries today, and
`TripwireCoverage` reads the mode dispatch rather than the guards, so a flag
added without its refusals would be a gap this suite could not see."*

That was a correct statement of the gap and a wrong account of it — the gap is
larger than the sentence claims, and half of it is now closed. **A flag added
*with* its refusals was uncovered too**, because nothing reconciled the table
with the guards. That is #608's shape one table over: a check whose coverage is a
list nobody reads against the thing it covers. The docstring is corrected beside
itself rather than deleted, and this page is what the correction rests on.

What is unchanged is the table's purpose. `Refusals` still loops over
`GUARDED_FLAGS`, and the tripwire is still flag-agnostic: it mocks the same
entry points either way, so adding a flag is a row in a loop rather than a
class. What changed is that a flag has to be *found* before it can be added.

## The reading: the guard's left operand

A guard is an `if` whose body calls `.error(...)` — what `argparse` refuses an
argument with, and the only refusal `main()` writes today. Each such guard's
test is read for the attributes of the name `parse_args()` is bound to, and the
**right-hand operands of the test's top-level `and`** are taken back out. What
survives, mapped back to its own spelling through `main()`'s `add_argument`
first long option, is the guarded-flag set.

Measured on the committed `main()`, one row per guard, in source order:

| guard | every `args.<name>` in its test | the `and`'s right-hand side | derived |
|---|---|---|---|
| `no_eq_guard` / modes | `no_eq_guard`, `check`, `self_test` | `check`, `self_test` | `--no-eq-guard` |
| `no_eq_guard` / defaults | `no_eq_guard`, `out_registers`, `out_clusters` | `out_registers`, `out_clusters` | `--no-eq-guard` |
| `export_ownership` / modes | `export_ownership`, `check`, `self_test` | `check`, `self_test` | `--export-ownership` |
| `export_ownership` / defaults | `export_ownership`, `out_registers`, `out_clusters` | `out_registers`, `out_clusters` | `--export-ownership` |

Two guards per flag, and the derivation is the same both times, which is the
point of reading them rather than listing them.

**The subtraction is the rule a later reader will second-guess, so it is argued
rather than asserted.** The right-hand side of a guard is by construction *not*
a guarded flag: it is what the flag is refused **with** — `--check` and
`--self-test`, the mode namespace `MODES` lives in — or refused **against** —
`--out-registers` and `--out-clusters` still at their committed defaults, the
output namespace. Keeping every attribute the test carries returns those names
alongside the flag's and answers nothing about which flag is being guarded,
which is the only question `GUARDED_FLAGS` asks. The reader takes the namespace
name from the assignment `parse_args()` is bound to and the spellings from each
`add_argument`, so no mode name, no output name and no dest-to-spelling list
sits in the middle of it — the failure mode `BENIGN_ATTRIBUTES` and the reader
#694 replaced both came from.

## The one dependence: it is positional, and that is measured

The rule assumes the guarded flag is the **left** operand of the `and`. A guard
written the other way round — `if (args.check or args.self_test) and
args.demo_flag:` — leaves the reader subtracting the wrong side and deriving
`{--check, --self-test}`, the mode namespace, as the guarded set.

That is a boundary, and the property worth having at a boundary is that it is
**loud**. `GUARD_SOURCES` pins it on synthetic source, with the set the reader
must derive beside the source it derives it from, and the `subTest` label spells
out that the wrong side is the expected answer. The reader is not promised to
handle the shape; it is pinned to be wrong about it in a way a table without the
flag would catch.

The other pin is the shape the committed tree cannot show. Both of its guarded
flags are already in `GUARDED_FLAGS`, so a reader that gets the committed tree
right by *keeping* rather than by deriving — the right-hand side as a
mode/output name list, or a guard found by its message rather than by `.error` —
leaves the committed case green. Both kinds were measured against the
committed tree with the reader swapped and nothing else changed:

| reader narrowed to | committed case | synthetic `subTest`s |
|---|---|---|
| the right-hand side kept as a `{"check", "self_test", "out_registers", "out_clusters"}` set instead of read off the `and` | **green** | the flag-on-the-right row **red** |
| a guard found by its message carrying `"cannot be combined with --check or --self-test"` instead of by `.error` | **green** | **both red** |

Dropping the subtraction altogether is a narrowing the committed case *does*
catch: the reader then returns the mode and output names alongside the flag's,
and the comparison fails on the real tree. It is recorded because the two rows
above are not the whole argument — the committed case is not blind, it is blind
to the narrowings that need no arithmetic to survive.

## Shown to fail, not merely shown to pass

The recipe is the dispatch sibling's §"Shown to fail": a scratch copy of `ec/`
with `annotations/` and `tools/` copied and `decompiled/`, `firmware/`, `ghidra/`
and `datasheets/` symlinked back, so the mirror's census CSVs are the property
under test and the big trees are not copied. Each mutation was reverted
immediately, and the mirror's two census CSVs were `cmp`-ed against their
pre-run bytes after every run.

The first row uses this branch's **base** version of the test file — the reader
as it was before this change — dropped into the mirror with `git show
08892cfd:ec/tools/test_xdata_register_map.py`. The commit is named directly
rather than derived from a moving ref, because that is what keeps the recipe
re-runnable by someone who is not standing in this branch, once `origin/main`
has moved on. The property the row needs is that the commit holds the
pre-change file, and that is checked rather than asserted: `08892cfd` is this
branch's base and the parent of the commit carrying this change, and
`git show 08892cfd:ec/tools/test_xdata_register_map.py | grep -c guarded_flags`
answers `0`. The sibling page carries several corrections for using `HEAD` here
instead, which is the thing a named commit avoids.

The mutation adds `--demo-flag` the way `--export-ownership` was added: a plain
`ap.add_argument(..., action="store_true")` and the same two refusals, whose
messages carry the fragments `Refusals` asserts on. It changes
nothing else — the flag is a no-op in the census, which is what keeps the row
about coverage rather than about argparse.

| mutation | what the suite said | census CSVs after |
|---|---|---|
| `--demo-flag` added to the parser with the same two refusals, suite at this branch's **base** version | **green** — the flag is in neither list and `Refusals` is unaffected | byte-identical |
| same mutation, **fixed** suite | **red** on `TripwireCoverage.test_guarded_flags_is_every_flag_main_refuses`, naming `--demo-flag` in both directions' message | byte-identical |
| same mutation plus `--demo-flag` added to `GUARDED_FLAGS`, fixed suite | **green**, and `Refusals` loops over three flags: the mirror's own guards refuse `--demo-flag` in every combination `Refusals` drives — with `--check`, with `--self-test`, bare at the defaults, and with each `--out-` path alone — so each `subTest` is a real refusal rather than a vacuous pass | byte-identical |

The two census CSVs compared after every row are `xdata-registers.csv` and
`xdata-clusters.csv`, the two files every `main-ec-NNN` citation and
`check_cluster_citations.py` is keyed to. The real tree is checked only for
having not moved; the mirror is where the property is measured.

**The first row is the whole of the issue.** A third guarded flag is invisible to
the base table: the reader does not exist, the table does not name the flag,
every case is green, and the `Refusals` cases never reach it. The third row
is what the fix buys and it is the property #675 bought for `MODES`: the table
needed a third entry and the tool's refusals did not change, so those cases
picked the flag up for nothing.

## The other half: a flag with no guard is still uncovered

The issue asked this to be decided and recorded rather than assumed, and the
answer is that the reader above closes one half of the docstring's sentence and
the other half is still open. **A flag that re-buckets occurrences and carries
no refusal at all is nothing for a guard reader to find**, and nothing for
`Refusals` to loop over either: the hazard is a bare run writing a census the
committed CSVs do not match, and the two refusals are what stop it. There is no
`ap.error` to read.

Two candidate signals were measured on the committed tree. **Help text is
circular and was rejected.** Both guarded flags' `help=` strings carry "refused";
`--no-writer-axis`, the other `ap`-level `store_true` flag, does not. But the
help string is written by the same hand in the same commit as the guard, and a
flag added *with* its refusals would carry the same sentence — so the check
would pass today and be unfalsifiable, which is worse than no check.

**"Read on the census path" is a real signal and is recorded, not built.** The
walk: module-level `def`s in `xdata_register_map.py`, bare-name calls between
them, transitively from the three modes that build a census (`write`, `check`,
`map_census`), then the `args.<dest>` reads. It was a throwaway `ast` walk and
is not committed — the walk is the *measurement*, and what would need to be
committed is the check, which is the follow-up.

| flag | read in | inside that closure |
|---|---|---|
| `--no-eq-guard` | `census_shape`, `census_and_groups`, `main` | `census_shape`, `census_and_groups` |
| `--export-ownership` | `census_shape`, `census_and_groups`, `main`, `self_test` | `census_shape`, `census_and_groups` |
| `--no-writer-axis` | `threshold_sweep`, `collapse_co_readings` | neither |

The signal separates cleanly on this tree, and it separates for the reason that
matters rather than by accident: `threshold_sweep` and `collapse_co_readings`
make no `open`/`write_text`/`write_bytes` call, and `main()` is the only caller
of either, so `--no-writer-axis` is a flag that changes what a mode *prints* and
nothing that reaches a census. A `--fold-equal` flag — the grouping
`ec/annotations/xdata-export-ownership.md` §3 names and
`export_ownership.py --self-test` pins on a fixture, though the committed map
is the strict-subset derivation — would land in the covered shape, and the
closure reader would be what noticed. What the tree does not carry is that
grouping's figure over the committed tree (**#590**, which is about the
measurement rather than about a flag's refusals). The ledger's verdict against
`common/0806.c` is already recorded and needs nothing from either this page or
that one; what a `--fold-equal` figure would leave to the sibling issue is
folding the three stubs together, which
`export-ownership-relative-containment.md` names as `--fold-equal`'s job.

**Decision: record, do not build.** The check would be a transitive call-graph
closure whose own soundness needs its own docstring, its own synthetic pins and
its own boundary case, and a false positive on it is a *false alarm* — a flag
that legitimately re-buckets only for the print-only modes. Shipping that inside
a change about reading the guards table would widen the claim past what the
change measures. The gap is bounded and named here rather than closed and
implied.

## Calibration

- **The check holds for a guard whose body calls `.error(...)` and whose test
  puts the flag on the left of a top-level `and`.** Both halves are measured on
  the committed `main()` and on the synthetic sources in `GUARD_SOURCES`, not
  read off the `ast` module's documentation.
- **It does not hold for a guard written flag-on-the-right, and that is pinned
  as a case rather than left open.** The reader reports the mode namespace for
  that shape; a table that does not carry those names is red. What it cannot do
  is report a *set that reads naturally* for that shape, which is why the
  expectation is the wrong set rather than the right one.
- **A refusal the tool writes in some other way is not found.** `ap.exit`,
  `raise` and `print`-and-return are not guards to this reader, and `main()`
  carries none today. That is a property of the committed `main()`, not a claim
  about how the tool would be written.
- **A dest no `add_argument` in `main()` produces has no spelling** and is
  reported under the dest name. Every `args.<name>` in the committed guards
  comes from this `main()`'s own `add_argument` calls, so the case does not
  arise here; the fallback is there so a future one is visible rather than
  dropped.
- **The census-path closure is a measurement, not a check.** It was a throwaway
  walk over committed text, its result is the table above, and nothing in the
  suite asserts it. Before anything asserts it, it needs its own reader, its
  own synthetic pins and its own boundary case.
- **Nothing is an EC finding.** The suite reads the same committed text the tool
  reads, offline, and the refusals it pins are a CLI contract.

## What this change does not do

- **It does not edit `xdata_register_map.py`.** The whole of the fix is in the
  test's reading of the tool, the mirror mutations above are text edits to a
  *copied* tree, and each was reverted immediately.
- **It does not add a flag, a guard or a refusal.** `--demo-flag` exists only in
  the scratch mirror; the committed tool is byte-identical before and after.
- **It does not regenerate, re-key or sweep either census CSV**, and no `status:`
  in `ec/annotations/registers.yaml` changes.
- **It does not cover the unguarded-flag half**, for the reason the section above
  gives. The module docstring says so beside the sentence it corrects, and this
  page carries the measurement a follow-up starts from.
- **It does not reconcile this suite with
  `test_xdata_cluster_names.py::guard_off()`.** That recipe is **#568** and is
  independent of the table read here.
- **It is not a gate arm.** `.github/scripts/agent-gates.sh` compiles
  `ec/tools/*.py` and does not run this suite; wiring the run in is **#512**,
  and a `.github/` change is a human's edit — the pipeline token has no
  `workflow` scope. `tools/run-tests.sh` finds the file with no wiring edit.
- **No live hardware or Windows run, and no sentence implying one.** Every case
  runs against committed text.
- **Nothing is opened in another repository.** No upstream pull request or issue
  is prepared by this change either.