# The attribute reader is measured against the six benign calls in `main()`, not filtered by `MODES`

**Issue #694, 2026-09-29.** `mode_attributes` in
`ec/tools/test_xdata_register_map.py` is the boundary `dispatch_names` cannot
close by itself: a mode dispatched as `return xrm.demo_mode(args)` is not a
bare-name call, so the first reader records nothing for it. The second reader
collected the attribute calls in `main()` *whose terminal name is already in
`MODES`* — so it was green for exactly the case it exists to catch, because a
tenth mode is by definition not in `MODES`. This page is what holds that
boundary now, the reading that got it there, and the mutations that show it
going red.

Its predecessor is
[`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md),
which owns the reader and the three-mutation table this one does not restate; and
[`xdata-dispatch-position-pins.md`](xdata-dispatch-position-pins.md), which is
the direct precedent for a follow-up page about one reader and its synthetic
pins. Neither page's figures are a figure for this one.

Nothing here is an EC finding. No register's `status:` changed, no register was
read back, no hardware or Windows machine was involved, and every case runs
offline against committed text. `MODES`, `Refusals` and `AcceptedWrite` are
untouched, and the two committed census CSVs are byte-identical before and after
this work and after each of the three mirror runs below.

## The blind spot, measured

The reader before this change was

```python
    return sorted({call.func.attr for call in ast.walk(main_of(source))
                   if isinstance(call, ast.Call)
                   and isinstance(call.func, ast.Attribute)
                   and call.func.attr in MODES})
```

and the `MODES` clause is the whole defect. On synthetic source, a tenth mode
reached attribute-qualified:

| reader | records |
|---|---|
| `dispatch_names` | `[]` — `xrm.demo_mode` is an `ast.Attribute`, not an `ast.Name` |
| `mode_attributes` | `[]` — the filter drops a name that is not in `MODES` |

and `test_the_dispatch_reaches_no_mode_as_an_attribute` asserted `[]`, so the
suite was green with the tenth mode in place. Its sibling,
`test_a_mode_reached_as_an_attribute_is_caught_by_the_other_reader`, pinned
`ATTRIBUTE_DISPATCH` on `xrm.write` — and `write` **is** in `MODES`, so it
measured the filter the reader already had rather than the path that fails. It
is re-pinned here on `xrm.demo_mode`, with `assertNotIn("demo_mode", MODES)` as
an explicit precondition so the case cannot drift back to a name the old filter
covers.

This is issue #608's failure one axis over, and the same lesson its page draws
about a maintained exclusion list: **a list is wrong the first time it is
written down.**

## The benign set is six names, and the issue named four

The issue's own list of the benign attribute calls in the committed `main()` is
`add_mutually_exclusive_group`, `add_argument`, `error` and `join`. **That is
wrong by two.** Parsing `main()` and collecting every `call.func.attr` over
attribute-qualified `Call` nodes gives six distinct terminal names:

| terminal name | where it comes from |
|---|---|
| `ArgumentParser` | `argparse.ArgumentParser(...)` |
| `add_mutually_exclusive_group` | the group carrying the two guarded flags |
| `add_argument` | every flag, on the parser and on the group |
| `parse_args` | `ap.parse_args()` |
| `error` | the four refusal guards |
| `join` | the default `--registers` path, `os.path.join(EC_DIR, …)` |

`ArgumentParser` and `parse_args` are missing from the issue's list, and both are
real. That is the same defect in a second place: an assertion written from the
four-name list is red on the committed tree before any mutation is attempted,
and the person who writes it next has a red they cannot explain from the list in
front of them. `BENIGN_ATTRIBUTES` is the six, each with a one-clause reason at
its definition, and it is held as a **partition in both directions** rather than
by omission — a new attribute call nobody classified, and a name nothing calls,
are different defects and the case names each.

## The two-layer reader, and why there are two

The issue asks for a deliberate decision between a spelled-out set and a derived
one. **Both, layered, because they fail in opposite directions.**

1. **Spelled out, and asserted by residue.** `attribute_calls(source)` is a new
   unfiltered reader: every `call.func.attr` for an attribute-qualified call in
   `main()`, sorted, with no reference to `MODES` anywhere in it.
   `mode_attributes(source)` is the residue — `attribute_calls` less
   `BENIGN_ATTRIBUTES` — asserted `[]` on the committed tree. This is the
   strictest property available: **any** new attribute call in `main()` is red,
   whether or not it could be a mode.

2. **Derived, and asserted against the spelled-out set.** `module_level_names`
   collects the tool's own module-level bindings. The rule it implements is
   stated in its own docstring: *an attribute call in `main()` is suspicious if
   and only if its terminal name is bound at module level in the tool's own
   source*, because that is what a mode is — a top-level `def` in
   `xdata_register_map.py` that `main()` dispatches to.

The second layer exists for the failure the first cannot see. A maintainer who
widens `BENIGN_ATTRIBUTES` to silence a red has to add a name the tool itself
defines, and the derived guard is what says so. Measured on the committed tool,
the rule separates the two sets cleanly:

- none of the six benign names is bound at module level in
  `xdata_register_map.py`, and
- all nine of `MODES` are.

So `BENIGN_ATTRIBUTES ∩ module_level_names(TOOL) == ∅` fails the moment the
benign set is widened to swallow anything the tool itself defines. That guard is
**vacuous unless a positive control exists**, so the same case asserts the other
direction too — every name in `MODES` *is* a module-level binding — in the
spirit of `check_eq_guard_citations.py`'s "a checker that located nothing must
say so rather than exit 0".

`dispatch_names` and `mode_attributes` keep their names and their owners. The
`MODES`-filtered reader is not kept alongside the residue as a second opinion: it
cannot fail for a tenth mode, and a test that cannot fail is not a second
opinion.

## What each case holds

All in `TripwireCoverage`, the class that owns the readers:

| case | pins |
|---|---|
| `test_modes_is_every_entry_point_main_dispatches_to` | the committed dispatch is `MODES` — unchanged by this issue |
| `test_a_mode_dispatched_as_a_statement_is_collected_too` | `dispatch_names` on statement position, since #608 |
| `test_every_position_the_docstring_names_is_collected_too` | the other three positions, by `DISPATCH_POSITIONS`, since #696 |
| `test_the_dispatch_reaches_no_mode_as_an_attribute` | the **residue** is `[]` on the committed tree, and the failure message carries the offending name rather than a bare `Lists differ` |
| `test_a_mode_reached_as_an_attribute_is_caught_by_the_other_reader` | re-pinned on `xrm.demo_mode`: `dispatch_names` records `[]`, the residue records `["demo_mode"]`, and `demo_mode` is asserted **not** in `MODES` |
| `test_the_benign_attribute_set_is_exactly_the_committed_one` | the partition, **both directions**, with a message naming each side |
| `test_the_benign_set_names_nothing_the_tool_defines` | the derived guard, plus its non-vacuity control (`set(MODES) <= module_level_names(TOOL)`) |
| `test_a_dispatched_name_the_tool_defines_is_a_suspect` | the derived rule in both directions, on synthetic source: `xrm.demo_mode(args)` in a tool that defines `demo_mode` is a suspect, and the same call in a tool that does not is not |

The partition and the derived guard are **set relations, not counts**. No
integer in this change is a number any merge has to edit, and no message says how
many names there are; the suite's total is `bash tools/run-tests.sh`'s own last
line.

## Shown to fail, not merely shown to pass

The recipe is
[`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md)
§"Shown to fail", reduced: a scratch copy of `ec/` with `annotations/` and
`tools/` copied and `decompiled/`, `firmware/`, `ghidra/` and `datasheets/`
symlinked back, so the mirror's census CSVs are the property under test and the
big trees are not copied. Every mutation was reverted immediately, and the
mirror's `xdata-registers.csv` and `xdata-clusters.csv` were `cmp`-ed against
their pre-run bytes after every run. A tenth mode is added the way a tenth mode
is added: a `demo_mode` defined at module level, a `--demo-mode` flag registered
on the mutually-exclusive group, and a branch in the dispatch. The unmutated
mirror is green first, so the rows below are mutations and not a broken harness.

| mutation | what the suite said | census CSVs after |
|---|---|---|
| A — the branch dispatched as a statement (`demo_mode(args); return 0`) | **1 failure**: `test_modes_is_every_entry_point_main_dispatches_to`, `Tuples differ` with `demo_mode` recorded at index 0 and absent from `MODES`; `TripwireCoverage`'s attribute cases **green** | byte-identical |
| B — the branch dispatched attribute-qualified (`return xrm.demo_mode(args)`) | **2 failures**: `test_the_dispatch_reaches_no_mode_as_an_attribute`, residue `['demo_mode']`; and `test_the_benign_attribute_set_is_exactly_the_committed_one`, `main() reaches ['demo_mode'] as an attribute and BENIGN_ATTRIBUTES does not account for it`. The committed-dispatch case is **green**, which is the point: the tenth mode is still a `return` in a position `dispatch_names` reads | byte-identical |
| C — B, and `demo_mode` added to `BENIGN_ATTRIBUTES` | **4 failures**: `test_the_benign_set_names_nothing_the_tool_defines` (`BENIGN_ATTRIBUTES covers ['demo_mode'], which the tool defines at module level`), `test_a_dispatched_name_the_tool_defines_is_a_suspect` on both `subTest`s, and `test_a_mode_reached_as_an_attribute_is_caught_by_the_other_reader`. The residue case is now **green** — the widening silenced it, which is the failure row C exists to show | byte-identical |

The failure counts in the middle column are **this run's figures on this tree**,
and are that run and no other; they are not the ones the tripwire page recorded
on its own.

**Row B is the issue's second requirement.** A tenth mode dispatched
attribute-qualified is red, and the committed-dispatch case stays green through
it, so the two shapes are independent: the positional reader is unmoved by this
issue and the attribute reader is unmoved by a statement dispatch.

**The partition case going red on row B is not a second defect.** The mirror's
`main()` genuinely grew a seventh attribute name, and the partition case is the
one that says so; the residue case is the same event caught at the reader, with
a message that names the call. Two cases, one cause, and the partition is the
earlier of the two in a reviewer's reading order because it is the wider
statement.

**Row C is what the second layer is for, and it is the row the issue did not ask
for.** Under a widened `BENIGN_ATTRIBUTES` the residue case is green again — the
one failure a maintainer would have silenced is silenced — and the derived guard,
the synthetic pin, and the re-pinned case all go red on the same tree. The
partition case stays green, and it has to: `demo_mode` really is an attribute
call the mirror's `main()` makes, so classifying it is not the mistake. **A
correct classification and a silencing are the same edit, and only the derived
rule tells them apart.**

## Calibration

- **The blind spot is measured on synthetic source**, as the issue states:
  both readers answer `[]` to `def main():\n    return xrm.demo_mode(args)\n`.
  Nothing here is inferred from reading the `ast` module.
- **The six-name correction to the issue's four-name list is a measurement**
  against the committed `main()`, not a preference. A residue assertion written
  from the issue's list is red on the committed tree before any mutation.
- **The derived rule's separation is measured on the committed tool** and
  reported as two sentences — six benign names and none module-level, nine
  `MODES` and all nine module-level — not as a general property of Python.
- **The residue is a superset of "a mode reached as an attribute".** It reports
  any attribute call the six do not account for, which on this tree is nothing
  and on a future tree is whatever `main()` grew. That is deliberate: the strict
  reading is the one that cannot be widened from the outside.
- **The derived rule is stated for a terminal name bound at module level.** The
  walk is over `ast.parse(source).body` and does not descend, so a name bound
  inside a function, or inside a `def` nested in a top-level `if`, is not
  covered by it; neither is a name the source reaches under a spelling it does
  not bind. Nothing here claims otherwise.
- **`MODES` is unchanged at nine, and the tool is not edited at all.** The fix is
  entirely in the test's reading of `main()`, so no ninth-to-tenth count
  argument arises.
- **Nothing here is an EC finding.** The suite reads the same committed text the
  tool reads, offline, and the dispatch it reads is a CLI contract.

## What this change does not settle

- **It does not establish that this is the only remaining shape `main()` could
  grow.** The wrapper edge — `return run(demo_mode(args))` — is argued rather
  than measured in
  [`xdata-dispatch-tripwire-coverage.md`](xdata-dispatch-tripwire-coverage.md),
  and this change does not measure it. Measured here, for the record, on
  synthetic source: `dispatch_names` records `['run']` and `attribute_calls`
  records `[]` for the bare-name form, so neither reader reaches the mode; for
  the attribute form `return run(xrm.demo_mode(args))`, `dispatch_names` records
  `['run']` and the residue does reach `demo_mode`. The bare-name wrapper edge is
  **open**, and this page does not close it.
- **It does not edit `xdata_register_map.py`, add a tenth mode, or change the
  tool's dispatch.** `MODES`, `Refusals` and `AcceptedWrite` are untouched, as
  in #675: the fix is in the test's reading, not the tool.
- **It does not restate the tripwire page's three-mutation table.** The table
  above is this run's own, on a reduced recipe, and the owning page keeps its.
- **It does not add a second suite file.** `dispatch_names`, `mode_attributes`,
  `attribute_calls` and `module_level_names` are already module-level in the
  suite that owns them, and a separate file would have to import from a test file
  to reach them.
- **It is not a gate arm.** `.github/scripts/agent-gates.sh` compiles
  `ec/tools/*.py` and does not run this suite; wiring the run in is **#512**, and
  a `.github/` change the pipeline token has no `workflow` scope for.
  `tools/run-tests.sh` picks the file up with no wiring edit.
- **It does not reconcile this suite with
  `test_xdata_cluster_names.py::guard_off()`.** That recipe is **#568** and is
  untouched by this change.
- **No live hardware or Windows run, and no sentence implying one.** Every case
  here runs against committed text, and the mirror mutations are text edits to a
  copied tree, reverted immediately.
