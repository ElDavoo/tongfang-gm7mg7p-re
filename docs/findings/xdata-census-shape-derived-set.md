# The re-clustering flag set `census_shape` names, derived rather than kept (issue #882)

Issue [#882](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/882) came
off the follow-up pass on #851. #851 built `census_shape()` -- the predicate that
decides whether a carry line is a re-key request -- by naming three flags, and
`ec/tools/test_xdata_carry_notice.py` holds that each is named and in `main()`'s
declaration order. What no case held was that the list is **complete**, and
completeness is the whole claim. This file is the derivation that closes it, and
the decision on `--no-writer-axis`.

**None of this is a live test, and none of it is evidence about the firmware.**
No EC image is opened, no register is read back, no Ghidra project is loaded, no
laptop or Windows machine is involved. Every measurement below is `ast.parse`
over a committed source file or an in-process `main()` call, and every figure is
re-derivable from the commands printed beside it. No register's `status:` moved,
and neither census CSV nor the names file was edited.

## What the derivation is

`ec/tools/test_xdata_census_shape_set.py` reads both sides out of
`ec/tools/xdata_register_map.py`'s own AST, so **neither is a set held in the
test** -- not even the expected set. The derived side is every `args.<name>`
read anywhere in `generate()`'s transitive call closure over the tool's
module-level `def`s, less the two output paths; the named side is
`census_shape`'s own `args` reads. `TheShape` compares the two, in both
directions.

Measured on the tree this was written against:

| | read from | value |
|---|---|---|
| derived | `generate()`'s call closure | `export_ownership`, `no_eq_guard`, `threshold` |
| named | `census_shape()`'s body | the same three |
| excluded | `outputs()`'s own reads | `out_clusters`, `out_registers` |

They agree. `census_and_groups` reads the first two on the way into `scan`;
`generate` reads the third where it hands the floor to `build`, which calls
`components(groups[g], threshold)` -- the clustering itself.

## Two properties that change what the suite may claim

**The output-path exclusion is currently inert, and the suite says so as a
measurement.** `outputs()` is *not* in `generate()`'s closure -- `check` and
`write` call it beside `generate`, not through it -- so the subtraction removes
nothing on this tree. It guards a future refactor that inlines the writers into
the generator. Three cases hold it rather than one, because each has its own
failure:

- `test_the_exclusion_names_outputs_own_reads` is an **equality** against
  `outputs()`'s own reads. Containment would let the filter grow over a third
  dest without comment; growing it over a real flag would also fail the control
  case, but this one says *which* dest.
- `test_the_exclusion_is_currently_inert` is the measurement, stated as one. It
  measures the *closure* rather than the filter, so it intersects the derived
  set taken with the subtraction switched off: the default already subtracts both
  names, so intersecting the default would be empty for any source and the case
  could never fail. `test_the_exclusion_excludes_when_the_closure_reads_them`
  carries its injected read through that same expression, so the measurement is
  shown going red rather than only asserted to be one.
- `test_the_exclusion_excludes_when_the_closure_reads_them` is the only one that
  can catch a **deleted** filter, and it needs an injected read: with the
  committed tree, a reader that stopped subtracting anything would pass the other
  two, because there is nothing left to subtract.

**The closure is transitive, so it collects from anything reachable**, not only
from `census_and_groups` and `build`. That is the right reading -- the question
is what a flag can *reach* -- but it means a future helper taking `args` for an
unrelated reason over-collects. `derived_flags` therefore returns
`{dest: frozenset(contributing functions)}` rather than a set, and the failure
message names the contributor: the difference between `Lists differ` and a flag
plus a function to go and look at.

**One rule choice worth recording.** The closure descends into call arguments,
which is the opposite of what `test_xdata_register_map.py`'s `dispatch_names`
does. That reader is enumerating an entry-point *dispatch*, where a call that is
only another call's argument is the callee's business; here reachability is the
whole question. The rules disagree on this tool -- `generate()` calls
`name_clusters(..., load_cluster_rows(...), load_cluster_names())`, and under a
no-descent rule those two are invisible, along with everything else reachable
only through them. A blind spot is the failure this suite exists to close, so
the rule that closes it is the one taken.

## The negative controls, and what they are for

A suite that cannot show its own reader failing is not evidence that the reader
works, and every case in `TheNegativeControls` is therefore on an injected copy
of the committed source. An injected `args.<name>` read is put into
`census_and_groups`, into `build`, and into `census_shape` on the named side
alone; each is asserted to be collected, to name its contributing function, and
to break the comparison the control case makes. The exemption is exercised too:
recorded with a reason, the comparison passes; recorded with an empty or
whitespace reason, it does not -- so silencing the control case costs a second
edit.

The controls were run against the tool as well as the reader. A `_ignored =
args.floors` line added to `census_and_groups` on the committed tool -- no other
edit, the shape a real fourth flag would take -- is what turns
`test_the_derived_set_equals_the_named_one` red:

```
$ python3 -m unittest ec.tools.test_xdata_census_shape_set
FAIL: test_the_derived_set_equals_the_named_one
```

That is the issue's request met: the omission is caught rather than shipped.

## `--no-writer-axis`: refused, not ignored

The issue offered two defensible readings and rejected a third. A silent no-op
was the third, and that is what the tool was doing.

Measured on the tree this was written against, before the guard below existed:
`--no-writer-axis` is declared once for the whole parser and read in two
module-level functions, `threshold_sweep` and `collapse_co_readings`. Every
other mode parsed it and did nothing. `python3 ec/tools/xdata_register_map.py
--check` and the same command with `--no-writer-axis` both exit 0 with **stdout
and stderr byte-identical**:

```
$ python3 ec/tools/xdata_register_map.py --check > /tmp/a 2>&1; echo $?
0
$ python3 ec/tools/xdata_register_map.py --check --no-writer-axis > /tmp/b 2>&1; echo $?
0
$ cmp /tmp/a /tmp/b && echo byte-identical
byte-identical
```

That transcript is the state the guard was added to, reproducible by removing
it. What the guard refuses is the invocation *carrying the flag*, and `--check`
on its own is untouched:

```
$ python3 ec/tools/xdata_register_map.py --check >/dev/null 2>&1; echo $?
0
$ python3 ec/tools/xdata_register_map.py --check --no-writer-axis >/dev/null 2>&1; echo $?
2
```

The first of those is what the arm in `.github/scripts/agent-gates.sh` runs the
tool with -- `python3 "$tool" --check && python3 "$tool" --self-test` -- and no
committed invocation in `.github/` or `tools/` passes `--no-writer-axis`, so the
guard is invisible to the chain and refuses only the runs that named the flag.

So a reader could believe a run had measured what the second relation is worth
when it had measured nothing of the kind -- and the flag is *about* the second
relation, which is why this is a claim rather than a cosmetic default.
`main()` now refuses it beside the two flags that were already refused there,
with the same reasoning the existing guard comment states: a flag that re-buckets
while writing nothing must not reach a mode whose claim is that the committed
CSVs already match.

The refused and accepted sets are **derived in the suite**, from the same AST --
readers from the source, dests from `main()`'s own dispatch -- and compared
against the guard's own condition. So the guard is not a third hand-kept list: a
third function reaching `args.no_writer_axis` moves the derived pair and
`test_the_guard_admits_exactly_the_functions_that_read_the_flag` goes red, which
is the direction that matters, since the guard is the thing with to be wrong.

Two dependences are stated rather than promised, and both are pinned:

- `guard_accepts` is **positional**: it finds the `ap.error` guard whose test
  names the flag on the *left* of its `and`, and reads the `or` under the `not`
  beside it. `GUARD_SHAPES` holds the other shape and holds what the reader then
  derives (`set()`) rather than what it ought to.
- The refusal cases tripwire every mode entry point, so they assert that the
  refusal happens *before* the dispatch -- a property asserting only "the CSVs
  are unchanged" would also be satisfied by a run that wrote identical bytes.
  `test_the_bare_run_would_write_the_committed_pair` is the one thing here not
  asserted through a mock: the tripwires mean the bare case would otherwise pass
  whether or not a committed file was behind it.

## What was and was not touched

- **The `--no-writer-axis` cases went in the new suite, not in
  `ec/tools/test_xdata_register_map.py`.** The issue offers that suite as an
  option, and it was checked and found not to fit: every case in its `Refusals`
  class asserts one of the two message shapes its table's flags carry, and this
  flag carries neither -- it is refused by which mode asked for it, not by what
  the run would do. The tripwire and the "no mode reached" assertion were copied
  from there rather than invented, which is why the two suites read alike.
- **`ec/tools/test_xdata_register_map.py` was edited, because its own assertion
  went false.** `TripwireCoverage`'s
  `guarded_flags` reads which flags `main()` refuses off `main()`'s `ap.error`
  guards and compares that to `GUARDED_FLAGS`; a fifth guard makes the two
  disagree, and `test_guarded_flags_is_every_flag_main_refuses` goes red with
  `main() refuses ['--no-writer-axis'], which GUARDED_FLAGS does not name`. That
  is the suite working as designed -- it exists to catch exactly this -- so the
  edit is in the suite rather than worked around in the tool. The addition is a
  second constant, `REFUSED_ELSEWHERE`, holding the flags whose refusals are not
  the pair `Refusals` asserts, plus the case comparing against both tables. Adding
  the flag to `GUARDED_FLAGS` instead would have put it through every case in
  `Refusals`, all of which assert a message shape it does not have.

  An earlier draft of this write-up said the suite "was not edited", on the
  grounds that `BENIGN_ATTRIBUTES` already covers `error` and the bare-name
  dispatch is unchanged. Both of those are true and neither is the assertion
  that failed: the check that went red is the *guarded-flags* table, which reads
  the guards rather than the attribute calls.
- **`ec/tools/test_xdata_carry_notice.py` was not edited**, per the
  new-work-in-new-files rule and the issue's own preference. It holds the other
  half of the claim -- that each of the three is named, in a stated order -- and
  that half is unaffected.
- **`tools/README.md` was not edited.** The suite table this repository used to
  carry there was removed on 2026-10-02, and
  `tools/test_readme_suite_table.py` now *fails* if a row comes back; a suite
  describes itself in its own docstring, which is where
  `tools/list_suites.py` finds it. An earlier draft of this work planned a table
  row, which would have failed the gate it was meant to satisfy.
- **`docs/findings.md` was not touched**, and no `registers.yaml` row was
  involved.

## What this unblocks

Nothing about the firmware directly. What it removes is a way for a future flag
to reach the clustering and quietly turn a carry line back into a re-key request
the run has no standing to make -- the failure #851 fixed and this issue
restates as a completeness claim rather than a sentence. `--no-writer-axis`
becomes a flag with a refusal rather than a flag with no reader, which is one
item closer to open issue [#880](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/880)'s
inventory of constants with no reader; that inventory is a separate sweep over
the other side of `ec/tools/` and is not started here.

The census-scale consequences of a future fourth flag -- how many ids it would
move, which hand names it would break -- are deliberately out of scope. That is
work for the issue raised *after* such a flag exists, and this change only
guarantees the omission is caught before then.