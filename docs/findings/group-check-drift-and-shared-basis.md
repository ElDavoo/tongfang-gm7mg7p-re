# `group_functions.py --check` re-runs the rule, and `shared` was a basis no rule emitted (issue #442)

(2026-09-30. Static reading of committed files, a set of Python one-liners run
over them, and one `--check` against a scratch copy of the tree with a single
cell edited. No image is opened, no register is read back, and no laptop, EC or
Windows machine is involved: every figure below counts rows or strings in files
in this repository, and each one carries the command that produced it.)

## What the gate was not asking

`group_functions.py --check` ran five rules, and all five read the committed
file and asked only whether the file was *internally* well formed:
`misnamed_callgraph_groups` (a `callgraph` name's scope token against the rows
carrying it), `cross_bank_groups` (one group name collecting rows out of two
banks), `check_group_row` (the `group_basis` vocabulary, an empty `group`, an
`evidence` path that resolves on disk), a duplicate-key check, and "every
annotated function has a group row". None of them called `group_rows()`.

So a `group` cell on any row whose basis is not `callgraph` could be edited to
another non-empty value and all five passed: the vocabulary check reads
`group_basis`, not `group`; the two naming rules bucket only `callgraph` rows;
and the file stayed internally consistent. `--apply` then reverted the edit
without printing anything about it. The gate that runs per commit is
`.github/scripts/agent-gates.sh`, which already called this tool's `--check` and
`--self-test`, so this was a gate silence rather than a nightly one.

This is the same defect recorded for `grade_name_basis.py` under "Two bugs
worth recording, because both were silent" in
[`name-basis-and-groups.md`](name-basis-and-groups.md): there, the drift half
compared the committed `name_basis` with a value `grade_all()` had already
written over it, so the check could not fail and printed a tautology. The two
are the same shape and not the same bug — that one compared a cell with itself,
this one never compared it with anything — and the fix in both cases is the same
discipline: **two keys that cannot be the same value.**

## The committed tree already agrees, which is why this is a check and not a regeneration

`check()` now re-runs the rule and compares every committed `group` and
`group_basis` against it. On the committed tree that is zero disagreements,
both components:

```console
$ python3 -c "
import sys; sys.path.insert(0, 'ec/tools')
import group_functions as gf
for ann, groups, is_bios in ((gf.EC_CSV, gf.EC_GROUPS, False),
                             (gf.BIOS_CSV, gf.BIOS_GROUPS, True)):
    committed, computed = gf.drift_for(gf.read_csv(ann), gf.read_csv(groups),
                                       gf.REPO, is_bios)
    rel = groups[len(gf.REPO) + 1:]
    print(rel, len(committed), 'committed rows,',
          len(gf.drift_problems(committed, computed, rel)), 'disagreements')"
ec/annotations/function-groups.csv 1961 committed rows, 0 disagreements
bios/annotations/function-groups.csv 788 committed rows, 0 disagreements
```

That is the whole of the reason **neither `function-groups.csv` is regenerated
in this change**. A `--apply` would have been a no-op, and a pull request that
touched the CSVs would have been evidence that the recompute and the writer
disagree — which is a signal to stop and find out why, not a diff to commit.

The same run over all four cells the writer produces — `comment` and `evidence`
as well as the two compared — is also 0 disagreements on both files. The
comparison is **not** widened to those two, and the reason is a decision rather
than an oversight: a `comment` is prose somebody may legitimately want to
reword, and a check that refuses over a reworded comment is a check people
route around. `group_drift.CELLS` is the one line to widen if a hand-edited
comment ever turns out to be a real need, and the measurement is already taken.

The recompute is not free and it is not expensive: 0.233 s for both components
against 0.016 s for reading the two annotation CSVs, measured over five runs of
each in one process. `--check` stays in the cheap tier — python3, the committed
`.asm` listings, no Ghidra, no network.

## The other direction, measured before it was made a refusal

A committed row the rule produces **nothing** for is a second way to drift, and
it is not a cell comparison: there is no computed cell to compare against. It is
the case where a group row outlived the annotated function it was derived from,
or never had one, and nothing else in `check()` looks for it — the "no group for
annotated `<scope> <addr>`" rule asks the opposite question.

It was measured on the committed tree **before** being made fatal rather than
assumed empty. It is empty: 0 of the 1,961 EC rows and 0 of the 788 BIOS rows
are keyed at a `(scope, address)` the annotation file does not carry (the run
above reports 1,961 and 788 on both sides of that comparison, so the
`committed − computed` set has no members). It is a refusal, not a warning, for
the same reason the other five are: a warning in a per-commit gate is a line
nobody reads.

## `shared` was in the closed list and nothing emitted it

`GROUP_BASES` was closed at six values — `type`, `vector`, `module`,
`callgraph`, `shared`, `ungrouped` — and `group_rows()` emitted five. The
emitters, in the order the function reaches them: `seed_groups` writes `vector`
for a row in the 0x0000 interrupt table and `type` for a `type` that names a
family; the BIOS branch writes `module`; and every row ends as `callgraph` or
`ungrouped`. Nothing anywhere emitted the value.

Before this change the value named itself in exactly three places — the tuple,
the module docstring's closed list, and `cross_bank_groups`'s exemption list.
This is that grep over the file as it stood, hence the line numbers:

```console
$ grep -nE '(^|[^a-zA-Z_])shared([^a-zA-Z_]|$)' ec/tools/group_functions.py
17:graph), `shared`, and `ungrouped`.
135:GROUP_BASES = ("type", "vector", "module", "callgraph", "shared", "ungrouped")
697:      * `shared` -- the explicit way this file says a name is common to both
```

(A plain `grep shared` returns fifteen lines; the other twelve are a
`self_test` local variable of the same name holding fixture rows, and fixture
filenames. That is also why the count is taken with a word-boundary pattern
rather than quoted: the docstrings write the value in backticks, so a grep for
`"shared"` finds the tuple and nothing else.)

Measured over the committed files, with the bases as they are:

| file | rows | `group_basis` |
|---|---:|---|
| `ec/annotations/function-groups.csv` | 1,961 | `callgraph` 1102, `ungrouped` 463, `type` 390, `vector` 6 |
| `bios/annotations/function-groups.csv` | 788 | `module` 666, `type` 122 |

**The exemption was unreachable, which is a stronger statement than "untested".**
`cross_bank_groups()` is the function that would police a name a reader is told
is deliberately common to both banks, and its docstring listed `shared` as one
of the bases it spares. Its loop opens by skipping every row whose basis is not
`callgraph`, before anything is bucketed:

```python
    for row in grows:
        if (row.get("group_basis") or "").strip() != "callgraph":
            continue
```

So no `shared` row could enter that function's accounting. The bases its
docstring called exempt were exempt by omission, and `shared` was named there
only as prose about a row that could not exist. The same is true of the
`ungrouped` entry beside it, which is still true as a statement — a row
asserting no membership really is not a merge — and is now what the `continue`
says rather than a second branch the function checks.

`shared` is dropped, and the removal is recorded in the tuple's comment and in
both docstrings rather than being a silent deletion. The issue offers the other
half of the choice, a producer, and it is declined deliberately: the value is
meant to say "this name is common to both banks on purpose", and deciding when
a name qualifies for that is a decision about the vocabulary rather than a
missing line of code. It would also need three things at once — a rule in
`group_rows()` that emits the value, a committed row or fixture carrying it,
and a fixture that reaches the exemption — and none of the three can be added
without changing what the rule claims.

`group_functions.py`'s module docstring, `cross_bank_groups()`'s, `GROUP_BASES`,
and the two `annotations/README.md` files all still name the value where a
reader would look for it.
[`name-basis-and-groups.md`](name-basis-and-groups.md) lists it too, under
"Part 2 — the grouping layer"; that list describes the file as it stood, and
this page is the correction rather than an edit to a settled write-up.

## The guard is a relation, not a list

`test_group_functions.py` now asserts
`set(GROUP_BASES) - PRODUCED_BY_FIXTURES == DECLARED_UNREACHABLE`, where the
produced set is collected by running fixtures through `group_rows()` rather than
written down beside the test, and `DECLARED_UNREACHABLE` is an empty map whose
entries would each have to carry a reason. The opposite direction is asserted
too: a rule that emits a basis the closed list does not name would have
`--check` refuse the rows the rule itself wrote.

`DECLARED_UNREACHABLE` is empty, and that is the point of the exercise. Putting
`shared` back in the tuple with nothing behind it fails there:

```console
AssertionError: Items in the first set but not the second:
'shared' : a basis in the closed list that no rule emits and no fixture produces
```

This asserts a **claim** rather than a census. Adding a basis requires editing
`GROUP_BASES`, which is the deliberate act; the test does not have to be edited
by the merge that adds one, and no merge has to keep a count right.

## The fixture pair is the regression, and the exit status alone is not

`--self-test` drives the real `check()` over a scratch pair of CSVs it writes
itself — two rows with no calls between them, so both fall out `ungrouped` —
once with the file agreeing and twice with a single cell poisoned, once the
`group` and once the `group_basis`. The agreeing case and the poisoned cases are
asserted together, for the reason the sibling tool's pair is: **if the two keys
were ever collapsed back into one, both poisoned cases would return 0 and the
agreeing case would still pass.** A self-test that only asserted the refusals
could not tell the difference between a working check and a comparison that has
quietly stopped comparing.

The refusal prints its own diagnostic rather than being silenced, so a
`--self-test` run still shows what it is refusing:

```console
$ python3 ec/tools/group_functions.py --self-test
  FAIL  …/drift_groups.csv bank0 8000 (drift_a): committed group arithmetic/ungrouped, the rule gives ungrouped/ungrouped
  FAILURES ABOVE
  every committed group and group_basis agrees with a fresh run of the rule, …
  self-test passed
```

## The demonstration, as a tool run

On a scratch copy of the tree, one committed `group` cell edited and nothing
else touched:

```console
$ python3 - <<'PY'   # rewrite one row of ec/annotations/function-groups.csv:
…                    # bank0 0x2A6C, group ungrouped -> arithmetic
PY
$ python3 ec/tools/group_functions.py --check
  FAIL  ec/annotations/function-groups.csv bank0 2A6C (clear_4c_bits_4_5_7): committed group arithmetic/ungrouped, the rule gives ungrouped/ungrouped
  FAILURES ABOVE
$ echo $?
1
```

The unedited tree exits 0, and so does the **same poisoned file** with the one
`problems.extend(drift_problems(...))` line removed from `check()` — which is
the whole finding in one measurement: the other five rules see nothing wrong
with that edit, and they still print a clean bill of health.

## What this does not say

- **Nothing here is a statement about the machine.** A group is a structural
  claim about call structure, and this change is about whether the file on disk
  still matches the rule that wrote it. No hardware and no Windows machine is
  reachable from a GitHub-hosted runner.
- **The comparison is `group` and `group_basis`, not the other two cells**, on
  the reason given above.
- **The "1,804 rows" in `group_functions.py`'s module docstring is left alone.**
  This change did not re-derive that figure, and the row count of the file it
  was written against is not evidence for it: the number names a component's
  share of the rows, not the rows. It belongs to whoever measures it.
- **`shared` may be the right idea.** What is settled is that the file claimed a
  rule it did not have. If a reader can name the case the value is for, the
  rule is a small piece of work and the guard above will hold it to producing
  one.
