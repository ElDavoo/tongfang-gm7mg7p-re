# The dispatch reader reads statement position too, and one boundary it does not

**Issue #608, 2026-09-25.** `ec/tools/test_xdata_register_map.py`'s
`TripwireCoverage` is the check that the refusal tripwire's recorder set is
complete, and it read one dispatch shape: its visitor implemented `visit_Return`,
so it saw `return <name>(args)` and nothing else. A tenth mode dispatched as a
statement landed in neither the recorded list nor `MODES`, and every case in the
suite stayed green with that mode unmocked. This page is what the check holds
now, the reading that got it there, the one shape dependence that survives and
is asserted rather than hoped away, and the three mutations that show it going
red.

Its predecessor is
[`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md),
which argues the tripwire design this is one reading of; the
[`--export-ownership`](xdata-export-ownership-refusal-contract.md) sibling
carries the same design for the other flag. This page names symbols rather than
line numbers wherever it can, for the reason that one records about its own §6a
recipe: those line numbers move.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and every case runs
offline against committed text. The two committed census CSVs are
byte-identical before and after this work, and after each of the three mirror
runs below. The counts of suites and tests are this repository's own, and they
move whenever a commit adds one.

## What the check claimed, and what it actually held

The `TripwireCoverage` docstring said the list is read out of `main()`'s own AST
"and a tenth mode fails here rather than going unmocked", and
`tools/README.md` carried the same promise in the tree: *"read out of `main()`'s
own AST so a tenth fails here rather than going unmocked."*

> **Both are corrected, 2026-09-25, issue #608.** The reader then implemented
> `visit_Return`, so it held for a mode dispatched as a `return` and for nothing
> else. A tenth mode reached as `demo_mode(args); return 0` — the shape issue
> #608 measured on the committed tree — recorded `[]` against a `MODES` of nine,
> so the case comparing the two stayed green, the recorder set stayed nine, and
> the new mode ran unmocked whenever a guard was relocated past the dispatch.
> That is the exact failure the class was written to close, reopened one shape
> over. Both sentences are now written for the shape the reader actually reads.

The class docstring is the corrected one; the sentences quoted above are left
standing here because the point of the correction is that they were believed, by
this page's predecessor and by the row in the tools table, for the life of the
suite. `xdata-no-eq-guard-refusal-contract.md`'s own §"The tripwires are the
design, not the decoration" carried the same over-claim and is corrected in place
there.

## The reading: position, not an exclusion list

Issue #608 offered two acceptable outcomes — stop depending on dispatch shape, or
narrow the claim to the shape it really holds. This is the first, and it is by
**position** rather than by an exclusion list. Three readers, all run against
the committed `main()`:

| reader | records on the committed `main()` | verdict |
|---|---|---|
| `visit_Return` (the committed one) | the nine, in source order | blind to statement position |
| every bare-name `Call`, full descent | `['list', 'list', …the nine]` | **wrong** — see below |
| every bare-name `Call`, no descent past a call | the nine, in source order | the one that works |

**The exclusion list the issue proposed does not work on this tool.** It names
`ap.error`, `ap.add_argument` and `os.path.join` to be skipped. The attribute
calls do fall out for free under an `ast.Name` restriction, with no list
maintained — but the two bare-name constructor calls do not. `main()` carries

```python
    ap.add_argument("--thresholds", type=float, nargs="+", default=list(SWEEP_THRESHOLDS), …)
    ap.add_argument("--floors", type=int, nargs="+",
                    default=list(SWEEP_COREADING_FLOORS), …)
```

and a reader that collects every bare-name call records `list` twice on top of
the nine. Any name-based exclusion has to carry those two, and a maintained list
that was wrong the first time it was written down is a poor thing to hand the
next reader.

**The rule that works is positional: record a bare-name `Call`, and do not
descend past a call into its arguments.** A call that is only *another call's*
argument is that callee's business, not `main()`'s dispatch, so the walk stops
at the call and never reaches the `list(...)` nested inside `ap.add_argument(...)`.
On the committed `main()` this yields exactly `MODES`, in source order, with no
change to `MODES` and no change to the tool. On a `main()` carrying the issue's
tenth mode it records the tenth, whether that mode sits as a top-level `Expr`,
inside a `try` body or inside a `for` body.

**The order property survives, and it is pre-order rather than source order by
accident.** A `NodeVisitor` walks the fields in order, which for the flat
`if args.*` chain the committed dispatch is *is* source order, and that is what
the old comment said. A mode reached through a wrapper —
`return run(demo_mode(args))` — records the wrapper rather than the mode, and
that is correct rather than a gap: the entry point `main()` dispatches to has
changed, so `MODES` has to change with it, and a tenth name turning up is the
coverage change firing. The old `ast.walk` remark (`ast.walk` is breadth-first
and would put the trailing `return write(args)` first) was about the wrong
walker for the job; the visitor is the right one and the comment now says why.

## The residual boundary: asserted, not hoped away

One shape dependence survives the widening, and it is stated rather than closed
by the reader. A mode dispatched attribute-qualified — `return xrm.write(args)` —
is not a bare-name call, so `dispatch_names` records nothing for it. Widening the
reader to attribute calls brings back every `ap.error`, `ap.add_argument` and
`os.path.join` on the way, which is the fragile list the positional rule exists
to replace.

So the boundary is its own assertion rather than a caveat in a docstring.
`mode_attributes(source)` scans `main()` for calls whose `func` is an `ast.Attribute`
whose `attr` is a name in `MODES`; on the committed tree it is `[]`, and a mode
reached that way fails **loudly** rather than being missed quietly. That is the
difference between a shape-independence the check has and one it is hoped for.

`TripwireCoverage` now holds four cases, each pinning one of those claims:

| case | pins |
|---|---|
| `test_modes_is_every_entry_point_main_dispatches_to` | the committed dispatch is `MODES` — unchanged, and evidence the fix did not over-collect |
| `test_a_mode_dispatched_as_a_statement_is_collected_too` | the issue's shape, on synthetic source |
| `test_the_dispatch_reaches_no_mode_as_an_attribute` | the boundary is clean on the committed tree |
| `test_a_mode_reached_as_an_attribute_is_caught_by_the_other_reader` | the shape is actually caught, so the case above is a property and not a helper that answers `[]` to anything |

**The two synthetic cases are the regression pins, and they are on synthetic
source for a reason that is the point.** The committed `main()` dispatches all
nine of its modes as a `return`, so an edit narrowing the reader back to
`visit_Return` would leave `test_modes_is_every_entry_point_main_dispatches_to`
green. Only a source that does not come from the tool can show the reader stopped
depending on that shape. Measured: with the reader narrowed back to
`visit_Return`, the committed-dispatch case stays green and the
statement-position case goes red with `Lists differ: [] != ['demo_mode']`.

## Shown to fail, not merely shown to pass

The recipe is the sibling page's §"Shown to fail" verbatim: a scratch copy of
`ec/` with `annotations/` copied and `decompiled/`, `firmware/` and `ghidra/`
symlinked back, so the mirror's census CSVs are the property under test and the
big trees are not copied. Each mutation was reverted immediately, and the
mirror's two census CSVs were `cmp`-ed against their pre-run bytes after every
run. To get the first row honestly, this branch's **base** version of the test
file — the reader as it was before this change — was dropped into the mirror
(`git show 4efb8eb0:ec/tools/test_xdata_register_map.py`; `4efb8eb0` is
`origin/main`, *"guard the probe's `--csv` hold against the grader's mark-merge
window (#667)"*, the commit this branch forks from) and the mutated mirror run
against it, then against the fixed one. The commit rather than the branch name
is what keeps the recipe re-runnable by someone who is not standing in this
branch, once `origin/main` has moved on.

> **Corrected 2026-09-25, issue #608 (PR #675 review).** This recipe first said
> `git show HEAD:ec/tools/test_xdata_register_map.py`, and `HEAD` is the wrong
> ref for it: on this branch `HEAD` is the commit that carries the fix, so that
> command yields the **fixed** file — it has
> `test_a_mode_dispatched_as_a_statement_is_collected_too`, its `Dispatch`
> reader is a `visit_Call` where the base file's is a `visit_Return`, and it is
> not the base file. A reader following the page as written would have run the
> mutated mirror against the fixed suite and seen 1 failure where this section
> promises 20 green, which is the one claim the section exists to make
> checkable. The row itself was always right; it is **20 tests, green** against
> `origin/main`'s test file, which is what the command above now names, and the
> base file at `4efb8eb0` is verified to be that 20-test version.

The tenth mode is added the way a tenth mode is added: a `--demo-mode` flag
registered on the mutually-exclusive group, and a branch dispatched as a
statement. Adding the branch without the flag was tried first and is not the
mutation — the accepted runs reach the dispatch and the mirror died with
`AttributeError: 'Namespace' object has no attribute 'demo_mode'` in
`setUpClass`, which measures argparse rather than coverage.

| mutation | what the suite said | census CSVs after |
|---|---|---|
| tenth mode dispatched as a statement, suite at this branch's **base** version | **20 tests, green** — the tenth is in neither list | byte-identical |
| same mutation, **fixed** suite | **23 tests, 1 failure**: `TripwireCoverage.test_modes_is_every_entry_point_main_dispatches_to`, `Lists differ` with `demo_mode` recorded at index 7 and absent from `MODES` | byte-identical |
| guard 2 (the `or` on the `--no-eq-guard` defaults) moved below `return write(args)`, fixed suite | **23 tests, 3 failures**, each `Lists differ: ['write'] != []` from `Refusals`; `TripwireCoverage` **green** (4 tests) | byte-identical |

The census CSVs compared after every row are `xdata-registers.csv` and
`xdata-clusters.csv` — 1,171 and 430 rows, `md5` `bc442d04…` and `623f62e2…`
on this tree, and the real tree's two files carry the same digests as the
mirror's. That is the property the suite exists to protect, so the mirror is
where it is checked and the real tree is only checked for having not moved.

**The first two rows are the whole of this issue.** A tenth mode in statement
position is invisible to the base reader — the recorded list is the nine, `MODES`
is the nine, every case is green, and the mode runs unmocked whenever a guard is
relocated past the dispatch. The fixed reader records it and the case comparing
against `MODES` goes red, which is the tenth failing here rather than going
mocked. `MODES` itself needed no tenth entry and the tool's dispatch did not
change: the whole of the fix is in the test's reading of the tool.

**The third row is the issue's other requirement, and it is the recorder rather
than the coverage check that catches a relocated guard.** The relocation does not
change the dispatch, so `TripwireCoverage` correctly has nothing to say about it
— the three red cases are all `Refusals`, each firing on the tripwire because
`write` ran before the guard was reached. The five `Refusals` cases stay green
in the first two rows and the mock set is still nine, so widening the reader did
not disturb the tripwire the reader exists to keep complete.

## Calibration

- **The check holds for a bare-name call in statement or return position, and
  for a call reached through a wrapper it holds the wrapper's name.** All three
  are measurements on the committed tree and on the two synthetic sources named
  as constants in the suite, not readings of the AST module.
- **It does not hold for an attribute-qualified dispatch, and that is asserted
  rather than left open.** `mode_attributes` is `[]` on the committed tree and
  reports `['write']` for `return xrm.write(args)`. A mode reached that way goes
  red; what it cannot do is report a *list* that reads naturally, which is why
  the assertion is membership rather than equality.
- **The pre-order property is stated as pre-order.** It coincides with source
  order for the flat dispatch the committed tool has, and would fire on a
  wrapped call — correctly, since a wrapper changes which entry point `main()`
  dispatches to. It is not a promise to survive an arbitrary rewrite of the
  dispatch into a table.
- **`MODES` is unchanged and the tool is untouched.** The fix is entirely in the
  test's reading of `main()`, so the ninth-to-tenth count argument does not
  arise here: `MODES` was nine before this change and is nine after.
- **Nothing is an EC finding.** The suite reads the same committed text files
  the tool reads, offline, and the refusals it exists to pin are a CLI contract.

## What this change does not do

- **It does not add a tenth mode, and it does not change the tool's dispatch.**
  `xdata_register_map.py` is not edited by this issue; the reader was the whole
  of the gap.
- **It does not regenerate, re-key or sweep either census CSV**, and no `status:`
  in `ec/annotations/registers.yaml` changes.
- **It does not touch `--export-ownership`'s pair of refusals.** That is #604,
  and it is already landed — this suite's `Refusals` cases loop over both flags.
  The change here is confined to the `Dispatch` reader, the two synthetic-source
  constants, and the cases in `TripwireCoverage`; `MODES`, `Refusals`,
  `AcceptedWrite` and the module docstring are untouched.
- **It is not a gate arm.** `.github/scripts/agent-gates.sh` compiles
  `ec/tools/*.py` and does not run this suite; wiring the run in is **#512**,
  and a `.github/` change the pipeline token has no `workflow` scope for.
  `tools/run-tests.sh` picks the file up with no wiring edit.
- **It does not reconcile this suite with
  `test_xdata_cluster_names.py::guard_off()`.** That recipe is **#568**; a case
  asserting the flag and that recipe agree needs it fixed first and belongs
  beside it.
- **No live hardware or Windows run, and no sentence implying one.** Every case
  here runs against committed text, and the mirror mutations are text edits to a
  copied tree, reverted immediately.
