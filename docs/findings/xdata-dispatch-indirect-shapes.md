# Three of the six indirect dispatch shapes have no reader, and a `self`-receiver wrapper closes the tripwire green

**Issue #1407, 2026-10-02.** `dispatch_names` and `mode_attributes` in
`ec/tools/test_xdata_register_map.py` are the two readers that hold the
`TripwireCoverage` claim, and between them their docstrings name six ways a
mode can be reached that neither is a bare-name call in `main()`. No case
pinned any of them. This page measures all six on synthetic source against the
readers **as merged**, says which reader owns which shape, and records one
shape where the two layers disagree in a way that closes the tripwire green.

Its predecessors, all three in this family and none of whose figures are a
figure for this one:
[`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md),
which owns `dispatch_names` and the three-mutation table this page does not
restate; [`xdata-dispatch-position-pins.md`](xdata-dispatch-position-pins.md),
the precedent for a follow-up page about one reader and its synthetic pins; and
[`xdata-attribute-dispatch-boundary.md`](xdata-attribute-dispatch-boundary.md),
which owns `mode_attributes` and whose "what this change does not settle" named
the wrapper edge as open and unmeasured.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and every case runs
offline against committed text. `MODES` is nine before and after,
`xdata_register_map.py` is not edited, and both committed census CSVs are
byte-identical before and after this work and after each of the two mutation
runs below.

## The six shapes, measured

Every cell is the readers' own answer, imported from the suite and run over
synthetic source — not read off the `ast` module. The source is the whole of
each case: `main()` and nothing else.

| source in `main()` | `dispatch_names` | residue (`mode_attributes`) | residue ∩ `module_level_names` |
|---|---|---|---|
| `return run(demo_mode(args))` | `['run']` | `[]` | `[]` |
| `return run(xrm.demo_mode(args))` | `['run']` | `['demo_mode']` | `[]` |
| `return self.run(demo_mode(args))` | `[]` | `['run']` | `[]` |
| `return TABLE[args.mode](args)` | `[]` | `[]` | `[]` |
| `return getattr(xrm, args.mode)(args)` | `[]` | `[]` | `[]` |
| `return (lambda f: f(args))(demo_mode)` | `[]` | `[]` | `[]` |

Which reader owns which, read off that table rather than asserted:

- **The bare-name wrapper** is owned by `dispatch_names`, and owned correctly.
  It records the wrapper, and registering that wrapper in `MODES` where the
  reader found it makes the exact-tuple equality green again. This is what
  `dispatch_names`'s docstring instructs, and measured, it works.
- **The attribute wrapper** is owned by `mode_attributes`: the residue reaches
  `demo_mode` by name, and the derived rule is the only thing that can keep it
  from being silenced.
- **The `self`-receiver wrapper** is owned by neither. That is the section
  below.
- **The table, `getattr` and lambda dispatches have no reader at all.** Both
  readers answer `[]`. Stated in the negative because a negative here means
  *not reached by these two functions*, which is a statement about what was run
  and not about what the tool could grow: `mode_attributes` reports any
  attribute call the benign set does not account for, and a `getattr` dispatch
  reaches `getattr` only as a bare-name call, so the one reader with a residue
  to report has nothing to report for it.

## The derived rule's subject is not what the rule is about

`module_level_names` returns every top-level binding the tool's source carries,
and the docstring's rule is stated as *suspicious **if and only if** the
terminal name is bound at module level*. The `if and only if` is the sentence
this change corrects, in both directions.

The **if** over-calls. The rule's subject is what a mode is — the entry points
`main()` dispatches to — and the reader ranges over a population far larger than
that. Measured on the committed tool, and derivable from the reader itself:

```
$ python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('t', 'ec/tools/test_xdata_register_map.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
tool = m.TOOL.read_text()
names = m.module_level_names(tool)
print(len(names), sum(n in names for n in m.MODES))"
157 9
```

157 top-level bindings, of which 9 are `MODES`. The breakdown is `def`/`class`
bindings, plain `Assign` targets, and import bindings — the `def`/`class`
subset is the one the issue quoted, at 69 against 9, and it is right *as far as
it goes*; it is not the population the rule means. A name the tool binds at
module level and that is no entry point — a constant, an import — is called
suspicious by a rule that means it is not. **The direction of that imprecision
matters and is the reason to record it:** it is a false red, not a silent miss,
so it costs a maintainer an unnecessary classification rather than hiding one.

The **only if** is the direction with teeth. The rule is silent on the shape
that matters most to it, because a terminal name reached as a method on a
receiver `main()` dispatches through is not a module-level binding at all. It
falls outside the rule's subject rather than inside it, and a rule with a hole
in its subject cannot object to anything that goes through that hole.

## The `self`-receiver is where the two layers disagree

Carrying the residue's own remedy to its end closes the hole **completely, with
every case in the suite green.** Measured on a mirror — the committed tool's
source with one dispatch branch added ahead of `main()`'s final
`return write(args)`, so all nine committed dispatches are still present and a
tenth sits behind `return self.run(demo_mode(args))`:

1. `self.run` is an `ast.Attribute`, so `dispatch_names` records nothing for it.
   And on its own documented rule it does not descend into a call's arguments,
   so `demo_mode` is never reached either. **The recorded list is exactly the
   nine. The exact-tuple equality against `MODES` is green.**
2. The residue reports `['run']` — red — and its failure message carries the
   benign set and what a name outside it is, which makes the next step a
   classification.
3. Classifying the call widens `BENIGN_ATTRIBUTES` with `run`. **The residue is
   now `[]`.**
4. The partition still holds, in both directions: the mirror's `main()` really
   does make the call being classified, so this is
   `xdata-attribute-dispatch-boundary.md`'s own case, where *a correct
   classification and a silencing are the same edit*.
5. The derived guard is now the only thing that could object, and it cannot.
   `run` on a `self` receiver is not bound at module level, so the guard holds
   an empty intersection.

**Suite green, tenth mode unmocked, guard relocated below the dispatch reaches
it.** That is the exact failure `TripwireCoverage` exists to prevent, reached
through a shape the docstring calls correct.

The bare-name wrapper is the same shape one step later. `dispatch_names`
records `run`, a tenth name turns up, the coverage change fires — and once
`run` is registered in `MODES` at the position the reader found it, **the
equality is green and the residue is `[]`.** So "that is correct rather than a
gap" is not merely unmeasured; measured, it is true for that shape and false
for the receiver one, and the sentence says neither.

### What this says about the issue's own calibration

The issue is careful, and its caution is right where it applies: on five of the
six shapes the exact-tuple equality does go red for a tenth mode, so the
tripwire's load-bearing sentence is *expected* to hold and no silent hole is
claimed for them. **The sixth row is not that.** For `return
self.run(demo_mode(args))` the equality is green with the tenth mode in place —
measured above, not argued. The one shape where the layers disagree is also the
one where the issue's table records the wrong verdict in its own calibration
column.

Both of those are measurements on synthetic source with the configuration
named. Nothing here is a statement about the committed tree, which dispatches
all nine modes as a `return` and is unchanged.

## What each case holds

Three cases in `TripwireCoverage`, alongside the existing ones:

| case | pins |
|---|---|
| `test_every_indirect_shape_the_docstrings_name_is_measured` | all six shapes, each against the `(dispatch_names, mode_attributes)` pair it answered — one `subTest` per shape, keyed by the words the docstrings use |
| `test_registering_a_wrapper_makes_the_equality_green` | the docstring's instruction, followed: a wrapper recorded in `MODES` at the position the reader found it does make the equality green, while the residue is `[]` |
| `test_the_derived_rule_does_not_object_to_a_self_receiver_name` | the escape above, step by step, on a mirror rather than on a description of one — including the non-vacuity control that shows the derived guard *does* object to the same name when it is bound at module level |

The six sources are module-level constants beside `ATTRIBUTE_DISPATCH`, and the
measured pairs live in `INDIRECT_DISPATCHES` keyed by those same words, for the
reason `DISPATCH_POSITIONS` gives: so the reading and the pin cannot drift
apart, and a failure names the claim rather than an index into a tuple. It is a
**second mapping, not an extension of `DISPATCH_POSITIONS`** — those three are
positions `dispatch_names` reaches, and every entry here is a shape it may not
reach at all. Folding them together would assert one equality over two
populations that do not share a subject, and the empty recorded lists would
read as over-collection rather than as what they are.

The assertions are equalities, not memberships, for the same reason the
position cases give: `[]` is the finding for three of these shapes, and a
membership check could not tell a reader that reached nothing from one that
reached something else.

## Shown to fail, not merely shown to pass

The recipe is
[`xdata-dispatch-position-pins.md`](xdata-dispatch-position-pins.md)'s,
unchanged: both mutations below are edits to the test file alone, so no scratch
mirror of `ec/` is needed. The two accepted runs write only into a
`tempfile.TemporaryDirectory()` and each asserts the committed census CSVs are
byte-identical afterwards, which is the property a mirror existed to protect.
Each mutation was reverted immediately, and both CSVs were `cmp`-ed against
their pre-run bytes after every run.

**Mutation A** restores `generic_visit` in the `Dispatch` visitor, so the walk
descends into a call's arguments. Four of the six `subTest`s go red and the
other two stay green:

| shape | verdict |
|---|---|
| `bare-name wrapper` | red, `Lists differ: ['run', 'demo_mode'] != ['run']` |
| `self` receiver | red, `Lists differ: ['demo_mode'] != []` |
| `getattr` dispatch | red, `Lists differ: ['getattr'] != []` |
| `lambda dispatch` | red, `Lists differ: ['f'] != []` |
| `attribute wrapper` | **green** — descending into `run`'s arguments reaches `xrm.demo_mode`, an `ast.Attribute`, which this reader does not record |
| `table dispatch` | **green** — the subscript is not a `Call` at all |

Those two greens are the useful part rather than a gap in the pin: they are the
two shapes where descending into the arguments is *not* the right answer, so a
fix that widened the reader that way would be wrong exactly there.

Both of the new consequence cases go red under it as well, and so does the
committed-dispatch case, which is the pre-existing protection rather than
anything this change adds: `Tuples differ`, with `list` at index 0, which is
the over-collection `xdata-dispatch-tripwire-coverage.md` §"The reading"
records and the reason the rule is positional.

**Mutation B** restores the pre-`#694` reader — the residue filtered by `MODES`
again rather than by the benign set. The two attribute-dependent `subTest`s go
red, `[] != ['demo_mode']` and `[] != ['run']`, along with the new
self-receiver case and the two cases issue #694 added. The other four shapes
stay green, because their residues were `[]` before the mutation too: a filter
that drops a name not in `MODES` cannot change an answer that was already
empty. **The two shapes that move are exactly the two whose residue was doing
work**, which is the point of pinning them by name rather than as a set.

## Calibration

- **Every cell above is a measurement on synthetic source against the readers
  as merged**, run by importing them. Nothing in the table is inferred from
  reading the `ast` module, and each source is named so a reader can paste it.
- **The committed tree is unchanged and the suite is green.** This change
  measures and pins; it does not widen a reader, because a measurement that
  also changes its subject is not a measurement. A measurement that also fixes
  its subject would leave nothing to compare the fix against.
- **The empty cells are "not reached by these two functions"**, never "absent".
  The table, `getattr` and lambda rows are a statement about what was run.
- **The `self`-receiver escape is a measurement on a named configuration** — a
  mirror carrying the committed nine plus a tenth behind that shape — not a
  claim that the tripwire is broken. On the committed tree it cannot fire,
  because the committed `main()` dispatches all nine modes as a `return`.
- **The `if and only if` correction is stated in the direction it over-calls.**
  It is a false red, not a silent miss, and the population figure above is a
  measurement of this tree with the command that derives it beside it, not a
  threshold any case asserts.
- **The derived-rule figure is stated once, here.** No case pins 157 or 9 or
  any count of the tool's bindings; a case that did would be red for an
  unrelated edit to `xdata_register_map.py`.
- **Nothing here is an EC finding.** The suite reads the same committed text
  the tool reads, offline, and the dispatch it reads is a CLI contract.

## What this change does not settle

- **It does not fix the escape.** This measures it, pins it and corrects the
  prose that called the shape correct; it does not widen a reader. The obvious
  candidate fix — the derived rule's subject should be *bound at module level
  **or reached as a method on a receiver `main()` dispatches through*** — has
  its own consequence to work through (it would put `run` back in the residue's
  reach on the committed tree too, if `main()` ever grew a receiver), and
  belongs in its own issue with its own mutations.
- **It does not edit `xdata_register_map.py`, add a tenth mode, or change the
  tool's dispatch.** `MODES` is nine, and `Refusals`, `AcceptedWrite` and
  `AcceptedExportOwnershipWrite` are untouched.
- **It does not restate the three-mutation table**
  [`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md)
  owns. The two rows above are this run's own, on the reduced recipe.
- **It does not touch `tools/README.md`.** The suite's row states the rule
  rather than enumerating shapes, and the two-position enumeration it does
  carry is narrower than the reading rather than broader, so it needs no edit.
  Should a later reading make one of its clauses too strong, that is a
  one-clause issue rather than an edit bolted on here — that file is the most
  conflict-prone in the tree.
- **It does not change either committed census CSV or any `status:` in
  `registers.yaml`.**
- **It is not a gate arm.** `.github/scripts/agent-gates.sh` compiles
  `ec/tools/*.py` and does not run this suite; wiring the run in is **#512**,
  and a `.github/` change the pipeline token has no `workflow` scope for.
  `bash tools/run-tests.sh` picks the file up with no wiring edit.
- **It does not reconcile this suite with
  `test_xdata_cluster_names.py::guard_off()`.** That recipe is **#568** and is
  untouched by this change.
- **No live hardware or Windows run, and no sentence implying one.** Every case
  runs offline against committed text, and the mutations are edits to the test
  file, reverted immediately.