# Two of the six indirect dispatch shapes turn a tenth mode up; the `self` receiver and the three with no reader close the tripwire green

**Issue #1407, 2026-10-02.** `dispatch_names` and `mode_attributes` in
`ec/tools/test_xdata_register_map.py` are the two readers that hold the
`TripwireCoverage` claim, and between them their docstrings name six ways a
mode can be reached that neither is a bare-name call in `main()`. No case
pinned any of them. This page measures all six on synthetic source against the
readers **as merged**, says which reader owns which shape, and records which
of them close the tripwire green with a tenth mode sitting behind them — four
of the six, and one of those four is a shape where the two layers disagree.

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

The last column is what a tenth mode behind that shape does to the tripwire's
own equality, and it is measured rather than read off the cells beside it: each
shape's own expression goes into a mirror of the committed tool behind a tenth
mode, and the recorded list is compared with what the committed `main()`
records. A name turning up is exactly what makes the exact-tuple equality go
red; nothing turning up is exactly what leaves it green with the mode unmocked.

| source in `main()` | `dispatch_names` | residue (`mode_attributes`) | residue ∩ `module_level_names` | a tenth mode behind it |
|---|---|---|---|---|
| `return run(demo_mode(args))` | `['run']` | `[]` | `[]` | **red** — records the wrapper `run` |
| `return run(xrm.demo_mode(args))` | `['run']` | `['demo_mode']` | `[]` | **red** — records the wrapper `run` |
| `return self.run(demo_mode(args))` | `[]` | `['run']` | `[]` | **green** |
| `return TABLE[args.mode](args)` | `[]` | `[]` | `[]` | **green** |
| `return getattr(xrm, args.mode)(args)` | `[]` | `[]` | `[]` | **green** |
| `return (lambda f: f(args))(demo_mode)` | `[]` | `[]` | `[]` | **green** |

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
  to report has nothing to report for it. **And that is the whole of why they
  are green in the last column**: nothing is recorded, so nothing turns up, so
  the equality holds — the same mechanism as the receiver below, reached one
  step earlier. A tenth mode behind any of the three turns up nothing for the
  tripwire to catch, and unlike the receiver there is not even a residue for a
  maintainer to classify on the way there.

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
for every shape that records nothing — which is the other four — and the
sentence says neither.

### Why the other three land in the same column

Because the mechanism above is one sentence long: **an empty recorded list
leaves the exact-tuple equality green**, because there is nothing in it that
could differ from `MODES`. The table, `getattr` and lambda dispatches record
nothing for exactly the reason the receiver records nothing, so a tenth mode
behind any of them leaves the list at the nine and the tripwire holds. The
receiver gets a further step the other three do not — a residue that reports
`['run']` and hands the maintainer a classification — and that step is the only
thing distinguishing them, so it is the only reason to talk about the receiver
as a separate shape rather than as the fourth instance of the same thing.

It is also why the three are the ones a maintainer is most likely to grow:
there is no name to register in `MODES` for them, because nothing was
recorded, and no residue to classify. A tenth mode behind any of them is
unmocked, and the two readers have nothing to say about it.

### What this says about the issue's own calibration

The issue is careful, and its caution is right where it applies: a negative
here means *not reached by these two functions*, so for the shapes the readers
do reach the tripwire's load-bearing sentence is *expected* to hold and no
silent hole is claimed for them. **Measured, it holds for two of the six, and
the four it does not hold for are green by one mechanism.** The two reds are
the rows that record the wrapper `run`: a tenth name turns up, the equality
goes red, and the coverage change fires. The four greens are the receiver and
the three shapes with no reader at all, and each of them is green because
nothing is recorded — not because anything reasoned its way to silence. For
`return self.run(demo_mode(args))` the equality is green with the tenth mode in
place, measured above rather than argued, and it is the one of the four where
the residue still has something to say. The one shape where the layers disagree
is also the one where the issue's table records the wrong verdict in its own
calibration column.

Each of those is a measurement on synthetic source with the configuration
named. Nothing here is a statement about the committed tree, which dispatches
all nine modes as a `return` and is unchanged.

## What each case holds

Cases added to `TripwireCoverage`, alongside the existing ones:

| case | pins |
|---|---|
| `test_every_indirect_shape_the_docstrings_name_is_measured` | all six shapes, each against the `(dispatch_names, mode_attributes)` pair it answered — one `subTest` per shape, keyed by the words the docstrings use |
| `test_a_tenth_mode_behind_each_shape_is_caught_or_is_not` | the last column of the table above, measured rather than read off the cells beside it: each shape's own expression goes behind a tenth mode on a mirror, and what it turns up beyond what the committed `main()` records is what decides red from green |
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
read as over-collection rather than as what they are. `TENTH_VERDICTS` is keyed
by those same words for the same reason, and the branch each shape is put behind
is derived from its own source rather than written out again, so a shape and
the expression measured on it cannot come apart.

That case compares against **what the committed `main()` records** rather than
against `MODES` directly. On the readers as merged the two are the same
question — `MODES` is what the committed-dispatch case holds the reader to — but
a reader that over-collects the committed dispatch is a different failure, and
letting it decide this verdict would bury the shape instead of holding it.

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
fix that widened the reader that way would be wrong exactly there. The
tenth-mode case answers to the same mutation on the same split — red where the
reading moved, green where it did not — which is the second case seeing the
table rather than a second claim about it.

`test_registering_a_wrapper_makes_the_equality_green` and
`test_the_derived_rule_does_not_object_to_a_self_receiver_name` go red under it
as well, and so does the committed-dispatch case, which is the pre-existing
protection rather than anything this change adds: `Tuples differ`, with `list`
at index 0, which is the over-collection
`xdata-dispatch-tripwire-coverage.md` §"The reading" records and the reason the
rule is positional.

**Mutation B** restores the pre-`#694` reader — the residue filtered by `MODES`
again rather than by the benign set. The two attribute-dependent `subTest`s go
red, `[] != ['demo_mode']` and `[] != ['run']`, along with the new
self-receiver case and the two cases issue #694 added; the tenth-mode case
reports the same two messages on the same two shapes. The other four shapes
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
  The table, `getattr` and lambda rows are a statement about what was run. They
  are also the shapes a tenth mode runs through unmocked, which is the same
  fact seen from the other side rather than a stronger claim: nothing was
  recorded, so nothing turns up, so the equality holds.
- **The `self`-receiver escape is a measurement on a named configuration** — a
  mirror carrying the committed nine plus a tenth behind that shape — not a
  claim that the tripwire is broken. On the committed tree it cannot fire,
  because the committed `main()` dispatches all nine modes as a `return`. The
  red/green column is the same kind of measurement: one mirror per shape, the
  configuration named, and no case asserting that any of them fires on the
  committed tree.
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