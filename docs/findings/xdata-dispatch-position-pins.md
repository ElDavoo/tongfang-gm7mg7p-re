# The three dispatch positions the docstring names are pinned on synthetic source

**Issue #696, 2026-09-28.** The `TripwireCoverage` docstring in
`ec/tools/test_xdata_register_map.py` states the rule `dispatch_names` reads
`main()` by, and the sentence names five positions — statement, `return`,
assignment right-hand side, `with` header, bare comprehension. The suite pinned
one of them explicitly, on synthetic source, and the other fell out of the
committed `main()` happening to dispatch all nine modes as a `return`. The
remaining three were named by the sentence and held by nothing. This page is
what the three are now held by, the measurement that says the reader really does
reach them, and the two mutations that show the pins going red.

Its predecessor is
[`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md),
which owns the reader: the positional rule it is built on, the `visit_Return`
version issue #608 replaced, and the three-mutation table that recipe is run by.
That table is **not** restated here — a second copy is a thing that drifts, and
it is a page about a different question. Its `23 tests` figures are that page's
own dated run on the tree it names, not a figure for this one.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and every case runs
offline against committed text. The two committed census CSVs are byte-identical
before and after this work and after each of the two mutation runs below.

## The positions the sentence names, and what the reader does with them

All five measured against the **committed** `dispatch_names`, on synthetic
source and on the committed `main()`:

| position | the source it is measured on | what the reader records | pinned by |
|---|---|---|---|
| `return` | the committed `main()`, all nine modes | the nine, in source order — `MODES` | `test_modes_is_every_entry_point_main_dispatches_to`, incidentally |
| statement | `STATEMENT_DISPATCH` | `['demo_mode']` | `test_a_mode_dispatched_as_a_statement_is_collected_too`, since #608 |
| assignment right-hand side | `ASSIGNMENT_DISPATCH` | `['demo_mode']` | `test_every_position_the_docstring_names_is_collected_too`, by this issue |
| `with` header | `WITH_DISPATCH` | `['demo_mode']` | the same case, the same issue |
| bare comprehension | `COMPREHENSION_DISPATCH` | `['demo_mode']` | the same case, the same issue |

The last three are one mapping, `DISPATCH_POSITIONS`, whose keys are the words
the docstring uses for each position. The keys are the `subTest` labels, so a
failure names the phrase the claim was written in rather than an index into a
tuple. The sources are module-level constants beside `STATEMENT_DISPATCH` rather
than inline strings in the case, for the reason the file already gives for its
own constants: so the reading and the pin cannot drift apart.

**The claim was true, and it was unpinned.** That is the whole of the finding,
and it is deliberately not dressed up as a defect. The reader reaches all five
positions because `visit_Call` records a bare-name call and the walk
deliberately does not descend past it — the reading
`xdata-dispatch-tripwire-coverage.md` argues for. What was missing was the
keeping of the measurement. An edit narrowing the reader to "a bare-name call in
statement or `return` position" would have left both surviving cases green: the
committed dispatch really is all `return`, and `STATEMENT_DISPATCH` is the one
synthetic source. That is issue #608's failure one level down and one axis
over — the regression pin lives on synthetic source because the committed tree
cannot show the reader stopped depending on a shape, and the three shapes with
no synthetic source had nothing to fail on.

So **no retraction is needed and no correction block is written.** Nothing
claimed was false. The three sentences elsewhere that rest on the reader holding
the shape it says it holds — the row in `tools/README.md`, and the correction
blocks in this page's predecessor and in the two sibling refusal-contract pages
— are all narrower than the docstring sentence and all stay true; the
`tools/README.md` row states the rule and never enumerates the positions, so
this change leaves it needing no edit. §4a-4d keeps a wrong *figure* visible
beside its correction, and what was here was a missing test, not a wrong figure.

## Shown to fail, not merely shown to pass

The recipe is this page's predecessor's, reduced. Both mutations below are edits
to the test file alone, so no scratch mirror of `ec/` is needed: the two accepted
runs write only into a `tempfile.TemporaryDirectory()` and each asserts the
committed census CSVs are byte-identical afterwards, which is the property a
mirror existed to protect. Each mutation was reverted immediately, and both
census CSVs were `md5`-checked against their pre-run bytes after every run —
`xdata-registers.csv` and `xdata-clusters.csv`, both `OK` after both rows. The
committed tool, `MODES` and both CSVs are not edited by either mutation, so
there is no tree outside the test file to protect.

Mutation A narrows the visitor to the `visit_Return` shape issue #608 left
behind:

```python
    class Dispatch(ast.NodeVisitor):
        def __init__(self):
            self.names = []

        def visit_Return(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                self.names.append(node.value.func.id)
            self.generic_visit(node)
```

Mutation B gives it `visit_Return` *and* `visit_Expr` and drops the generic
`visit_Call`:

```python
        def visit_Return(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                self.names.append(node.value.func.id)
            self.generic_visit(node)

        def visit_Expr(self, node):
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                self.names.append(node.value.func.id)
            self.generic_visit(node)
```

| mutation | what the suite said | census CSVs after |
|---|---|---|
| A — `visit_Return` only | the committed-dispatch case **green** — the real `main()` really is all `return`; the statement case red with `Lists differ: [] != ['demo_mode']`, the string this page's predecessor records; **all three position `subTest`s red with the same string** | byte-identical |
| B — statement plus `return` | the committed-dispatch case **green** and the statement case **green**; **all three position `subTest`s red**, each `Lists differ: [] != ['demo_mode']` | byte-identical |

**Mutation A is the issue's first requirement, and it is the row that matters
most**: the committed dispatch and the statement pin both stay green, which is
exactly the pair the issue names as what a narrowing would have to leave alone.

**Mutation B is the issue's "what done looks like", and the comprehension case
is not the only thing it trips.** The issue asks for a comprehension case to go
red under a statement-plus-return reader, and it does. But `visit_Expr` reaches
neither a `with` header nor an assignment right-hand side either, so the widest
narrowing still leaves **three** pins red rather than one. That is the useful
part: a reader that had kept statement and `return` and dropped everything else
would have gone red on all three, not slipped through on two of them.

## Calibration

- **The reader reaches all five positions.** Four of them on synthetic source
  and the fifth on the committed dispatch, and both are measurements of this
  reader against these sources — not a reading of the `ast` module and not an
  argument that `visit_Call` ought to work.
- **The residual attribute boundary is unchanged and still asserted.**
  `mode_attributes` is the second reader, a mode dispatched as
  `return xrm.write(args)` records nothing in `dispatch_names`, and that stays
  the one shape `dispatch_names` cannot close. Nothing here widens it, and
  `ATTRIBUTE_DISPATCH` and its case are untouched.
- **Each synthetic source carries exactly one bare-name call**, so the assertion
  is `==` and not membership: it says the reader records that one name and no
  other, where a membership check would pass a reader that over-collected. The
  attribute reader needs `assertIn` for the opposite reason — a real `main()`
  carries `os.path` and `ap` calls, so a list is the wrong shape there. The
  committed-dispatch case is what holds the reader against over-collection on a
  real `main()`.
- **The positions are real, but the reader still does not promise to survive an
  arbitrary rewrite of the dispatch.** A mode reached through a wrapper records
  the wrapper, which this page's predecessor argues and
  [`xdata-dispatch-indirect-shapes.md`](xdata-dispatch-indirect-shapes.md)
  measures is correct rather than a gap. That is unchanged.
- **This is a measurement of the test's own reading, not an EC finding.** The
  suite reads the same committed text the tool reads, offline, and the dispatch
  it reads is a CLI contract rather than anything about the machine.

## What this change does not do

- **It does not edit `xdata_register_map.py`, add a tenth mode, or change the
  tool's dispatch.** The reader was already correct; what was missing was the
  test. `MODES`, `Refusals` and both `AcceptedWrite` cases are untouched.
- **It does not regenerate, re-key or sweep either census CSV**, and no
  `status:` in `ec/annotations/registers.yaml` changes.
- **It does not fold `STATEMENT_DISPATCH` into `DISPATCH_POSITIONS`.** The
  issue's shape would have fitted a single table, but this page's predecessor
  names `test_a_mode_dispatched_as_a_statement_is_collected_too` by name as how
  a reader identifies the fixed file, and deleting that case would falsify a
  committed page. It keeps its own case; the mapping covers the three additions.
- **It does not add a second suite file.** The reader is a closure defined
  *inside* `dispatch_names` in the existing file, so a new suite would have to
  copy the reader and pin the copy — the pin would not hold the shipped reading,
  which is the entire point. Importing the existing module would work, but a new
  suite file also needs a new `tools/README.md` row, putting this repository's
  most conflict-prone file back in the diff.
- **It is not a gate arm.** `.github/scripts/agent-gates.sh` compiles
  `ec/tools/*.py` and does not run this suite; wiring the run in is **#512**,
  and a `.github/` change the pipeline token has no `workflow` scope for.
  `tools/run-tests.sh` picks the file up with no wiring edit.
- **It does not reconcile this suite with
  `test_xdata_cluster_names.py::guard_off()`.** That recipe is **#568**; a case
  asserting the flag and that recipe agree needs it fixed first and belongs
  beside it.
- **No live hardware or Windows run, and no sentence implying one.** Every case
  here runs against committed text, and the two mutations are edits to the test
  file, reverted immediately.
