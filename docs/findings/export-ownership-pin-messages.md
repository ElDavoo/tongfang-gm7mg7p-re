# `export_ownership.py`'s `--self-test` named a measured figure in both slots and its pin in neither, and the sweep that found it (issue #1386)

**Written 2026-10-04, against `ed4483b1`.** Every line number below is this
tree's. Nothing here is a hardware, firmware or Windows claim: no image is
opened, no register is read back, no laptop is reached. What is read is one
committed Python tool and the `.c` files it already derives from, and what is
run is `export_ownership.py --self-test`,
`check_pin_message_names.py --population`, and a one-figure edit to a dict in a
scratch copy of `ec/tools/export_ownership.py` that never touches the committed
file.

This is the sibling of [`xdata-check-message-pin-sweep.md`](xdata-check-message-pin-sweep.md),
which found the same shape in `xdata_register_map.py` and wrote the checker
that finds it. That write-up's *What this opens* asks for a tree-wide version
and gives up on it, on the grounds that `check` is defined across `ec/tools/`
with unrelated signatures. This is the narrower reading — a named list, and a
population mode so a reader sees what the list is not covering — and it does not
deliver that bullet or contradict it.

## The property

A `--self-test` line that goes red has to carry the **pinned** figure and the
**measured** one both, or a reader turning it into a failing argument cannot:
the missing number is the number that moved. Issue #1363 is this in
`xdata_register_map.py`, and the fix's shape is the pinned figure in the
expected slot and the measured one in a `got` clause beside it.

`check_pin_message_names.py` reads the predicate's subscript expressions and
asks whether the message's f-string interpolates them. It is a parse, not a
substring search, because a substring search credits the *word* — and the #1363
message said "440 clusters" and "400 of the committed cluster_keys" while
interpolating none of the three keys it compared against.

## What the sweep found here

Pointed at `export_ownership.py`, the sweep reads two module-level dict
constants and reports every `check()` whose predicate holds a pin the message
does not name:

```
python3 ec/tools/check_pin_message_names.py
```

Each row below is one check, keyed on the leading literal run of its own
message — the same key the allowlist uses, and a stable one where a line number
is not. **The predicates did not change.** What changed is that each names its
pins expected-then-got; the last column is the `FAIL` line a perturbation of
one of that check's pins now produces, which is what a reader is shown when a
re-export moves it.

| the check, by its own message | pins read and unnamed | the FAIL line after the fix |
|---|---|---|
| `one row per index.csv row, …` | `OWNERSHIP_ORACLE["rows"]` | `… 2722 rows expected (got 2721)` |
| `… containment classes, … non-owner rows` | `OWNERSHIP_ORACLE["classes"]`, `["shared_rows"]` | `57 containment classes, 146 non-owner rows (got 56/146)` |
| `the body floor is load-bearing: …` | `OWNERSHIP_ORACLE["bridged"]`, `["bridged_no_floor"]`, `["classes_no_floor"]`, `["flood_no_floor"]` | `… 8 chained classes with it, 14 without it, … (got 7/14/29/562)` |
| `… of the … bodies are too short …` | `OWNERSHIP_ORACLE["tiny_bodies"]` | `1283 of the 2721 bodies are too short … (got 1282)` |
| `a --min-share floor of …` | `SHARE_ORACLE["classes"]`, `["shared_rows"]`, `["newly_read"]` | `… across 51 classes, and hands 13 files back to the census (got 133/50/13)` |

**The last row was not in the issue, because the issue is older than the case.**
`SHARE_ORACLE` arrived with issue #1651, which added the `--min-share` cost
block and the check that asserts it. An issue filed against the tree before that
commit could not have seen that check, so the fix here follows the sweep's
output rather than the issue's table — which is what `CLAUDE.md`'s calibration
rule asks for.

**The `SHARE_ORACLE` row is the sharpest of them**, and it is worth saying why
rather than leaving it in the table. Its message interpolates
`OWNERSHIP_ORACLE['shared_rows']` — the *committed* figure, correctly, as the
"from" of the move — while its predicate compares against
`SHARE_ORACLE["shared_rows"]`. Two different pins under one key name. A sweep
that credited a key by its name would find `shared_rows` on that line and
report it named; it is not. This is the case `check_pin_message_names.py`'s
subscript-level test exists to catch, sitting inside the tool that test was
written for.

**A pin's own check was the only thing that named it.** Unlike the
`ORACLE["both"]` and `ORACLE["main_distinct"]` cases the #1363 write-up calls
benign, no sibling check printed these figures expected-then-got, so there was
no other line on which a moved pin would have shown. That sibling-mitigation is
what makes those two benign, and it does not apply to any check in the table
above.

## The scope fix, and what it costs

`TARGET` was one module and `ALLOWLIST` was flat. Pointing the tool at a second
file therefore did not answer a second question — it answered the first one
wrongly: every census entry was scored against a module that does not contain
it, and each came back `excuses nothing`. Both halves are now per module:

- `TARGETS` is a named list of repo-relative paths, resolved against `REPO` so
  a sibling under `windows/tools/` or `bios/tools/` needs no second rule;
- `ALLOWLIST` is `{module: {prefix: (keys, why)}}`, so an entry is read only
  against the module whose checks it describes, and the stale-entry check
  iterates that module's own entries;
- `export_ownership.py`'s entry is `{}`, because this change fixed every case
  the sweep found in it. The empty dict is the correct end state and not an
  omission: the list is meant to shrink as cases are fixed, and
  `test_check_pin_message_names.py` fails if a case comes back without one.

The scope is a list rather than a tree because **the callee is matched by bare
name and is not resolved per module**. `check_capture_claims.check(path, index,
verbose)` and `check_findings_frozen.check(repo)` among them read as assertions
with no predicate at all. `--population` prints what a walk of the bare name
finds over every module under `POPULATION_DIRS`, so the population is a run's
output rather than a figure kept in a docstring:

```
python3 ec/tools/check_pin_message_names.py --population
```

It answers with more than the issue expected, and the honest reading is that
the named list is a stopping point rather than a completed sweep: the closing
line names modules carrying an unnamed pin that are **not** in `TARGETS` —
`bank_attribution.py`, `check_status_vocabulary.py`,
`counter_sweep_entry.py` and `pd_no_ret_fallthrough.py`. None has been read, so
none is claimed here as a case; each is a question for a follow-up, and the
issue's claim that a walk of the whole population finds no other violation does
not survive the measurement.

### The two `check` definitions, which the filter disambiguates by accident

`export_ownership.py` defines `check` twice: a module-level `check(args)` that
is the `--check` mode's own dispatch, and a `check(label, cond)` nested in
`self_test` that the census is about. What separates them is
`len(node.args) < 2` — the dispatch call site takes one argument and no
predicate. **That is a coincidence of two signatures, not a property of either
definition**, and it is why the tool's scope paragraph says so and why
`TheTwoCheckDefinitions` measures it on the committed file rather than restating
the prose.

## `OWNERSHIP_ORACLE["rows"]` was stale by one, and this is why it was legible

`export_ownership.py --self-test` was **red on the base of this issue**, which
the issue did not say:

```console
$ python3 ec/tools/export_ownership.py --self-test
  FAIL  one row per index.csv row (2721), at threshold 0.9 and floor 3
```

The pin was `2720` and the tree derives `2721` rows. Issue #337 added one
`bank0` seed, `0xC118`, and `build_ec_decompile.py` re-pinned its own figure
for it in the same change — `2,720 -> 2,721 with issue #337's one bank0 seed
0xC118`, with a write-up — while `export_ownership.py` was not re-pinned. The
CSV on disk was a fresh derivation of the current tree (that check was `ok`), so
only the pinned figure was wrong.

`tiny_bodies` did not move, and the reason is the one worth recording: `0xC118`
is a twelve-byte thunk whose body is three statements, and three is
`MIN_BODY_STMTS`, so it is *at* the floor rather than under it — `tiny` counts
`len(body) < MIN_BODY_STMTS`, not `<=`. The two figures move together for
#1101's six 7-byte stubs and separately for this.

The pin is re-pinned here with that reason in the comment block, in the file's
own idiom. **It is worth being clear about what the message fix bought here**:
before it, that red line printed `2721` and the pin `2720` was nowhere on it,
so the one stale figure in the tree was the one figure a reader could not
diagnose from its own output.

## What is left stale, and where

`docs/findings/xdata-export-ownership-page-census.md`, under *What re-derived
and did not move*, pastes a `--self-test` transcript as the census's
derivation. Measured against the pins this change re-pins, **the paste is
already stale on these keys, for reasons that predate this work** — #489 moved
the two floor figures, #1101 moved `tiny_bodies` with `rows`, and the
transcript's `rows` still carries #267's value:

| key | pinned | in the paste |
|---|---|---|
| `rows` | 2721 | 2714 |
| `bridged_no_floor` | 14 | 13 |
| `classes_no_floor` | 29 | 28 |
| `tiny_bodies` | 1282 | 1276 |

`classes`, `shared_rows`, `largest_class`, `bridged` and `flood_no_floor`
agree. The same write-up's held-figures table under *The reconciliation, every
cell against every oracle* carries the affected rows as `held`.

**This change makes that block stale in a second, new way**: the message lines
this issue fixed are quoted in that transcript, so it now shows the pre-fix
text as well as the older figures. Fixing it properly is a §4a-4d correction in a
long shared document — the transcript, the held-figures rows that cite it, and
the prose above them — and the staleness is not this change's to own. It is
recorded here so a follow-up can be filed from this file without a re-run.

What the fix does buy that block is the ability to *notice* the next move: a
re-export that moved `tiny_bodies` produced, before, a FAIL line identical to
the one in the transcript, and produces now one that names both figures.

## Left alone, and why

- **The per-module callee resolution**, the other option the issue offers. It
  needs a signature discriminator to tell `check_capture_claims.check(path,
  index, verbose)` from an assertion — the "different tool" the #1363 write-up's
  *What this opens* already describes. `--population` shows the reader the
  population the named list is not covering.
- **The modules `--population` flagged.** Each would need its own
  per-case verdict read off the module before it could join `TARGETS`, which is
  a decision this change does not make.
- **The remaining real cases in `xdata_register_map.py`**, `assign_shaped` and
  the `PER_PROGRAM` half of the split-partitions case. Already carried as
  follow-ups in the #1363 write-up with their verdicts; fixing them here would
  put more hunks in the hottest file in the tree for a defect this issue did not
  open.
- **`docs/findings.md`**, which is frozen. This file is the record.

## The tests that stand in for it

`ec/tools/test_export_ownership_pin_messages.py` writes a textually perturbed
copy of the committed source — the committed source, one dict figure changed,
not an in-memory mutation of an imported module, which would prove the dict
moved and not that the source *names* the pin — loads it by path, repoints its
`__file__`-derived paths at the committed tree, and runs the real
`--self-test`. The assertion is a **split**, not a membership test: the FAIL
line is cut at the `"(got "` every message now carries, the perturbed figure
has to be on one side of that cut and the measured one on the other. A
substring search anywhere on the line would pass on the pre-fix text for half
of them, because `56` and `146` are both *on* that line as measured figures.
`ThePreFixLine` is the control: it restores the pre-fix label and moves a pin,
and asserts the harness is not passing by construction.

No figure is written in that suite. It names the `(table, key)` pairs and reads
each figure from the module's own oracle, because a figure written in the test
would be a second copy of the pin — the same mistake the suite exists to catch.