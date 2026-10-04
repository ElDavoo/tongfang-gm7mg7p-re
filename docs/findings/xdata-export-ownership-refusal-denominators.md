# The export-ownership refusal now quotes the census it protects

The `--export-ownership` refusal is the one place in this tree where a stale
number does damage rather than sitting quietly in a page. It is what a user
reads when they have decided to ignore the flag: it tells them what flipping it
would cost, and they act on that. It was quoting denominators from a census
this tree had not had for some time — **1,171 / 430 / 10** against the
**1,326 / 439 / 9** the committed CSVs actually have. The figures have been
corrected, at five sites in `ec/tools/xdata_register_map.py`, and a case now
goes red if they stop describing the census.

**What the deferral was, and where it was recorded.** Issue #832 opened the
asymmetry this closes: the `--no-eq-guard` refusal argued from an instruction
with no measured result, and its `--export-ownership` sibling argued from
numbers. The sibling's numbers were fixed, and the write-up recorded that they
were still stale and deferred them —
`docs/findings/xdata-no-eq-guard-census-scale-join.md` §"What this does not
do" says the denominators are "out of scope here, the same way
`check_cluster_citations.py`'s 'the ten committed names' is; both are left for
their own issue", and `ec/tools/test_xdata_guard_off_row_join.py`'s
`test_the_two_refusals_now_argue_from_the_same_kind_of_number` asserted only
the **shape** of the sibling's comment — that it quotes a figure of some kind —
which passed on three wrong ones. That deferral is what this change lifts.

## The figures, and where each one comes from

Every number below is read off a committed CSV, printed by a committed tool, or
a figure in a page that the tool re-derives. None is a hand-typed numeral in a
test, which is the property §"Why a correspondence and not a restatement"
below is about.

| figure | what it counts | where it is measured |
|---|---|---|
| **296** of **1,326** register rows | addresses whose `refs` move | `OWNERSHIP["moved"]`, asserted by `--self-test`; the join's `rows whose refs differs` |
| **39** of the **439** clusters | committed `cluster_key`s the flip does not keep (400 survive, 40 are new) | `OWNERSHIP["cluster_keys_kept"]`, asserted by `--self-test`; §4/§5 |
| **5** of the **9** hand names | names the flip does not carry the same key | `OWNERSHIP["hand_names_kept"]`, asserted by `--self-test`; §4/§5 |
| **439 → 440** | clusters after the flip, one more than committed | `OWNERSHIP["clusters"]`, asserted by `--self-test`; §4.6 |

`xdata-registers.csv` has one row per address, so "296 of the 1,326 register
rows" and "296 of the 1,326 addresses" are the same statement on this tree —
worth saying because both phrasings are in use and the join is on `addr` alone.

## The five sites that now carry them

All in `ec/tools/xdata_register_map.py`, and all five state the identical claim,
which is why they are corrected together:

1. **the refusal comment** above `if args.export_ownership and (args.check or
   args.self_test)` in `main()` — the block that argues the flag should not be
   combined with a gate.
2. **the `--export-ownership` `--help` string** — the same figures, printed by
   `argparse` to every user who runs `xdata_register_map.py --help`.
3. **the module docstring's flip paragraph** — `argparse` passes the docstring
   as `description=`, so this is on the *same* `--help` screen as (2).
4. **the `OWNERSHIP` comment's flip paragraph** — which contradicted the dict
   printed immediately below it (`"clusters": 440`, `"hand_names_kept": 4`).
5. **`scan()`'s own docstring**, above `pattern = occurrence_re(symbols)` — the
   paragraph that says why the default stays off, stating the same cost in the
   routine that actually implements the pass.

Only (2) and (3) are user-visible, and they are the two on the same `--help`
run; (1), (4) and (5) are read by whoever opens the source. All five are held
by the same case, so a site corrected here cannot drift back alone.

Each is line-count neutral. `check_eq_guard_citations.py` resolves
`no_eq_guard_flag`, `reconcile_help`, `check_refusal` and
`committed_output_refusal` by grepping this tool's own source, and
`docs/findings/xdata-no-eq-guard-citation-anchors.md` records the lines those
resolve to, so a reflow that added or dropped a line above them would turn that
gate red for a reason unrelated to any finding. The `--help` block sits above two
of those anchors, so its ten lines are held for that reason; the refusal
comment's eleven are held alongside the six-line and four-line blocks the
sibling refusal already holds, so that the next correction to these figures stays
a same-length edit.

## The `:95` settle: a live denominator, so corrected rather than relabelled

The same change settles the question the issue left open about the direction
paragraph's "5,662 occurrences across 1,008 distinct addresses of the census's
**1,171**". It is **live**, not a historical record, on three counts: it is the
module docstring, so `argparse` prints it on every `--help`; its two figures are
the ones `DIRECTION_INVARIANT` pins and `--self-test` asserts; and the census
it divides by is `ORACLE["distinct"]`. So it is corrected to the constants'
values rather than relabelled as a record, and a case holds it to
`DIRECTION_INVARIANT` and `ORACLE` so it cannot drift again.

The 5,662 → 5,677 step is issue #263's re-pin, already recorded in the
constant's own comment, and 1,171 → 1,326 is #279's. Neither was re-derived
here; both were read off the constants the self-test already asserts.

By contrast, the `1,171` in the `ORACLE` block above it is left exactly as it
is. That one is #256's kept-wrong-version record under `docs/findings.md`
§4a-4d — the census as it stood on the day the drift was measured, kept visible
beside its correction. Re-reading it as a live denominator is the mistake this
issue exists to correct, so it stays.

## Why a correspondence and not a restatement

`test_xdata_guard_off_row_join.py`'s own docstring states the failure mode:
**a case that re-derives its expectations from its own inputs agrees with
itself by construction**, and the tree has been bitten by it (#753: a recipe
re-pointed three times, and a `source.replace()` that stopped matching failed
silently, so a suite compared the tool against itself).

So the new class holds a **chain** and types no size of the tree:

    refusal comment  ↔  cited page  ↔  fresh --export-ownership run  ↔  OWNERSHIP

The figures are parsed out of `annotations/xdata-export-ownership.md` §4/§5;
the denominators are the row counts of `xdata-registers.csv`,
`xdata-clusters.csv` and `xdata-cluster-names.csv`; the numerators come from a
fresh two-run join; and the oracle they must equal is `xrm.OWNERSHIP`, imported
rather than copied. Editing the page and every prose site together to a new
wrong number still fails, because the census end of the chain does not move with
them — which is a property of the design and not a hope, and the mutation was
run to confirm it rather than assumed.

**One caveat worth stating because it shaped a case.** The join tool's `names:`
line reports how many names *resolve* in the other census, and that number is
not `OWNERSHIP["hand_names_kept"]` — a name can resolve onto a different cluster
and still have had to be re-keyed, which is the thing a `cluster_key` citation
does not survive. The count that matches is the number of names the report
prints `key same` for, so `Report.names_by_key()` reads that split rather than
the `resolves` total, and the case holds the key-same count against the oracle.

## Re-deriving the register-row figure

Not copied from the page — measured, with the fence §5 already prints:

```
python3 ec/tools/xdata_register_map.py --out-registers /tmp/before-registers.csv \
    --out-clusters /tmp/before-clusters.csv
python3 ec/tools/xdata_register_map.py --export-ownership \
    --out-registers /tmp/after-registers.csv --out-clusters /tmp/after-clusters.csv
python3 ec/tools/xdata_guard_off_row_join.py --committed-clusters /tmp/before-clusters.csv \
    --committed-registers /tmp/before-registers.csv \
    --off-clusters /tmp/after-clusters.csv --off-registers /tmp/after-registers.csv
```

The join is already parameterised exactly this way, so no tool change was
needed. The three lines of the run the corrected sites rest on, verbatim:

```
rows whose refs differs: 296 of 1326
clusters: committed 439, guard-off 440
cluster_key that moves: 39 of 439 committed keys are absent from the guard-off set; 40 guard-off keys are new
```

One cost is recorded rather than paid: the join tool's report has
**"guard-off" hard-coded** into its wording, so a report produced from an
`--export-ownership` pair describes itself as a guard-off one. The tool is left
alone — its docstring, its `--off-*` flag names and the guard-off suite all read
the current spelling, so re-spelling it would mean churning all of them to fix a
reader-facing wart in a report most readers meet through the guard-off pair. Its
report **keys** are already census-neutral (`rows whose refs differs`,
`cluster_key that moves`, `names`), which is why the new case can read the
`--export-ownership` figures out of it at all.

## The second named site was already fixed

The issue's deferral also named `ec/tools/check_cluster_citations.py`'s "the
**ten** committed names are all multi-token slugs", where
`ec/annotations/xdata-cluster-names.csv` holds nine. That one **is already
corrected**, by another issue: `docs/findings/name-shape.md` (§ "The count")
records the decision to drop the numeral rather than replace it, and the bullet
in `check_cluster_citations.py` now reads "What a name may **look** like is a
check rather than advice", citing `ec/tools/cluster_name_shape.py` in its
place.
`grep -n "ten committed names" ec/tools/check_cluster_citations.py` returns
nothing. There is no diff for it here and re-adding a count would be the wrong
direction; recorded so a reader does not go looking for the second fix.

## What this does not do

- **The other sites carrying 35-of-430 / 5-of-10.** The correction above is
  scoped to `xdata_register_map.py`. These still carry the superseded figures,
  each recorded so a reader lands on it rather than re-deriving where it is:
  - `ec/tools/export_ownership.py:106`
  - `ec/tools/test_xdata_register_map.py:731`, `:930`
  - `ec/annotations/xdata-06c2-06db-timers.md:1313`
  - `docs/findings.md:5189`, `:7254`
  - `docs/findings/xdata-export-ownership-refusal-contract.md:45`, `:214`,
    `:216`, `:331`
  - `docs/findings/xdata-check-message-pin-sweep.md:129`
  - `docs/findings/xdata-census-self-test-gate.md:148`
  - `docs/findings/xdata-export-ownership-page-census.md:253`, `:430`
  They are deferred rather than fixed because each is a shared file other
  branches are editing, `docs/findings.md` is frozen, and each is a separate
  issue's work. This is the `docs/findings/name-shape.md` precedent ("recorded
  as deliberately unfixed").
- **The 9,404 → 10,178 census-total family.** `xdata_register_map.py`'s own
  docstring and `OWNERSHIP` comment state 9,404 in the present tense against
  `OWNERSHIP["refs"]`, and write-ups carry 9,404 as the record of that
  measurement. It is a different claim — the census total, not a
  denominator of the flip argument — it is already recorded as superseded in
  `annotations/xdata-export-ownership.md`'s re-derivation note and in the
  `ORACLE` comment's own `1171/9404 -> 1326/10178` line, and correcting it
  properly means re-reading historical write-ups.
- **The flip itself.** None of this argues for or against landing it. §5's
  argument is unchanged and its figures are now correct; the flip is still
  blocked on the export boundary (`xdata-06c2-06db-timers.md` §8 item 7), which
  needs `--mode rebuild-project` and cannot share a branch.
- **Any register behaviour.** Nothing here says a byte is absent or that the EC
  acts on a value. Every figure is a count over decompiled text.

## Calibration

Nothing in this change needed hardware, Windows, or the firmware image. Every
input is a committed CSV, a committed page, or a regeneration of the committed
tool into a scratch directory; no image is opened, no register is read back, and
no laptop, EC or Windows machine was involved. The `--export-ownership` and
`--no-eq-guard` runs write to scratch paths only — the tool refuses the
committed output paths, which `TheToolWritesNothing` in the same suite holds
from the other side.