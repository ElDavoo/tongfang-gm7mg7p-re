# Six `check()` calls read a pin their message never names, and the sweep that found them (issue #1363)

**Written 2026-09-28, against `5b5b7f2`.** Every line number below is this
tree's. Nothing here is a hardware, firmware or Windows claim: no image is
opened, no register is read back, no capture is taken. What is read is one
committed Python tool, and what is run is `xdata_register_map.py --self-test`,
`check_pin_message_names.py`, and a one-figure edit to a dict in a scratch copy
of `ec/tools/` that is reverted in the same working tree.

## The property, and why a substring is not it

`--self-test` prints one line per assertion, and a reader turning a red line
into a failing argument needs the **pinned** figure and the **measured** one
both on it. The property is therefore: *every `check()` whose predicate
subscripts a module-level constant names that key in its message's f-string.*

**A substring test does not detect it, and the reason is the case this file
exists to record.** The message fixed here said "440 clusters" and "400 of the
committed cluster_keys" in plain English and interpolated none of the three keys
it compares against. A sweep that credited a key whose name appeared in the
message would find `clusters` and `cluster_keys` there and report one key
named, on a line where none is. So
`ec/tools/check_pin_message_names.py` matches on the **subscript expression
being interpolated**, by parse, and the English around it is not evidence either
way.

## The sweep, with a verdict per case

The sweep found six `check()` calls reading a constant in the predicate and
naming none of it; five of them still stand. The verdicts are not uniform,
which is the substance: an omission is a real defect only when nothing else on
the tree will show the pin moving.

| line | constant and key(s) read but not named | benign? |
|---|---|---|
| `:4411` | `OWNERSHIP['clusters']`, `['cluster_keys_kept']`, `['hand_names_kept']` | **Not benign — fixed by this change.** All three pins absent and both slots were the measured triple. The sharpest case of the six, and the one whose line the issue was filed against. |
| `:4322` | `DIRECTION_INVARIANT['assign_shaped']` | **Not benign — a follow-up.** The message prints a *different* key (`deref_surplus`) and the measured `sum(shaped.values())` appears nowhere either. A perturbation yields a `FAIL` whose whole content is about the `*`-dereference stores, with no figure on it belonging to the half that failed. Worse than `:4411` was, in that there is not even a lone measured number. |
| `:3867` | `ORACLE['both']`, and `PER_PROGRAM['both_main_buckets']` / `['both_pd_buckets']` | **Split, and the sharp half is a follow-up.** `ORACLE['both']` is benign: `:3924` prints it expected-then-got over `len(both)`, a different measurement of the same key, so a moved pin turns both lines red. The two `PER_PROGRAM` tuples are **not**: the message prints the measured five-tuples in both slots and neither pin, which is the `:4411` shape again. |
| `:3609` | `ORACLE['extmem_refs']` | **Real but mitigated — a follow-up.** The measured sum is printed and the pin is not, but the two component pins are printed expected-then-got on this same line, so a moved sum localises to a component that did not move — itself the evidence the sum moved. Cheap to fix, left for the follow-up to keep this change to one defect. |
| `:4385` | `OWNERSHIP['lost']` | **Benign, with a caveat worth recording.** The pin is `()`; its only legal rendering is the `none` the message already falls through to when the measured set is empty, and the measured lost-address set is the informative part. A *moved* pin would be a baked-in allowance, which the line's own prose — "the one thing it must never do" — is what contradicts. Worth writing down, not worth changing. |
| `:4435` | `ORACLE['main_distinct']`, `['main_refs']` | **Benign.** The message is pure prose with no figure at all, but `:3918-3923` asserts the same pair against the same measured quantity, expected-then-got. |

The issue filed against `:4411` named `ORACLE['both']` alone for the `:3867`
row. The parse finds two more keys on that same line, and they do not share its
verdict — the row is above as the tool reports it rather than as the issue
summarised it.

## The fixed case, before and after

Three perturbations, one per pin, each in a scratch copy of `ec/tools/`, each
reverted in the same working tree. **All six runs below exited 1** — before the
fix and after it — which is the whole point: the exit code could never have
told the two apart, and only the text can.

`"clusters": 440` → `441`:

```
  before   FAIL  and the flip would renumber: 440 clusters against the committed 439, 400 of the committed cluster_keys surviving, 4 of the 9 hand names in annotations/xdata-cluster-names.csv (got 440/400/4)
  after    FAIL  and the flip would renumber: 441 clusters against the committed 439, 400 of the committed cluster_keys surviving, 4 of the 9 hand names in annotations/xdata-cluster-names.csv (got 440/400/4)
```

`"cluster_keys_kept": 400` → `399`:

```
  before   FAIL  and the flip would renumber: 440 clusters against the committed 439, 400 of the committed cluster_keys surviving, 4 of the 9 hand names in annotations/xdata-cluster-names.csv (got 440/400/4)
  after    FAIL  and the flip would renumber: 440 clusters against the committed 439, 399 of the committed cluster_keys surviving, 4 of the 9 hand names in annotations/xdata-cluster-names.csv (got 440/400/4)
```

`"hand_names_kept": 4` → `5`:

```
  before   FAIL  and the flip would renumber: 440 clusters against the committed 439, 400 of the committed cluster_keys surviving, 4 of the 9 hand names in annotations/xdata-cluster-names.csv (got 440/400/4)
  after    FAIL  and the flip would renumber: 440 clusters against the committed 439, 400 of the committed cluster_keys surviving, 5 of the 9 hand names in annotations/xdata-cluster-names.csv (got 440/400/4)
```

The three `before` lines are byte-identical. The three `after` lines each name
the value that moved, in the expected slot, against the measured one beside it.

**The binding is unchanged.** The predicate at `:4417-4419` still compares
`len(own_clusters)`, `kept` and `hand_kept`, because a `got` slot that read the
constant would be the same self-consistent message one level down. Only the
message moved.

## Why the constant's own comment was right, and the message was not

`OWNERSHIP`'s comment at `:1445-1451` claims "**Every key below is read by a
check in the --self-test ownership block**", and on this tree that is true —
including the three cost-of-the-flip keys. The defect is a second level down
from the one #849 corrected: a value can be *read* by a check and still be
absent from the line that check prints, so the reader of a red line learns
nothing about it. **This is a different defect from #849's, not a recurrence
of it**, and a checker for the first does not catch the second.

## What the committed property is, and what it is not

`ec/tools/check_pin_message_names.py` is the sweep, committed rather than
re-derived, and `ec/tools/test_check_pin_message_names.py` asserts it. Three
things about it are deliberate:

- **The allowlist is keyed on a message prefix, not a line number.** This
  change moved the check it was written beside by five lines; an allowlist of
  line numbers would have needed editing for a change that fixed a different
  check. Each entry resolves to whatever line it is on today and prints that.
- **A stale allowlist entry is a failure.** An entry that excuses nothing must
  be deleted, so the list shrinks as cases are fixed and cannot decay into a
  standing exemption — the failure mode that would make this tool worse than
  no tool. Both directions have a case.
- **It is a property, not a census.** No count of `check()` calls, of
  violations, or of allowlist entries is asserted anywhere. The suite asserts
  that the cases still violating are exactly the ones the allowlist excuses,
  which fails in both directions without being a number any merge has to edit.

**Not in any gate.** `.github/scripts/agent-gates.sh` is a copy from
`ElDavoo/agent-pipeline` and this branch's token has no `workflow` scope, so a
gate line is prepared as a `docs/ci/agent-gates-*.patch` for a human rather
than committed. None is prepared here: the checker runs under its own suite,
which CI already discovers by filename, and the gate the issue names —
`agent-gates.sh:262-263`, `--check && --self-test` for this tool — already
covers the check itself and is what the three perturbations above exercise.

## What this opens

- **The stale comment above the constant.** `:1430-1431` still reads "the flip
  moves `cluster_key` on 35 of the 430 clusters, breaks 5 of the 10 hand names
  in xdata-cluster-names.csv, and adds 2 clusters" against pins of
  `440`/`400`/`4` and a committed 439 keys and 9 names. It is a pre-#279
  comment rather than a wrong pin, and it sits in the same block whose message
  was just corrected; correcting it is separate work on the same hot file, and
  is named here so the next pass need not rediscover it.
- **Two real cases, `:4322` and the `PER_PROGRAM` half of `:3867`**, each of
  which would put a third and fourth hunk in the hottest file in the tree for a
  defect this issue did not open. Both are in the table above with the
  reasoning, so a follow-up can file from it rather than from a re-run.
- **A tree-wide version of the sweep.** `check` is defined by twenty-one modules
  in `ec/tools/` with unrelated signatures, so a directory-wide walk of the
  callee name would read `check_capture_claims.check(path, index, verbose)` as a
  census assertion, and a version that resolves the callee per module is a
  different tool. This one needs no self-exclusion for reading its own suite the
  way `check_doc_figure_pins.py` does, because it is not in the set it reads.
- **What this change did to the line pins elsewhere.** It adds six lines to
  `xdata_register_map.py`, and three suites hold hand-written line numbers into
  that file: `test_check_doc_figure_pins.py`, `test_check_eq_guard_citations.py`
  and `test_check_cluster_citations.py`. **`bash tools/run-tests.sh` runs 85
  suites on this branch and six of them are red** — those three plus
  `test_check_pin_table_rows.py`, `test_check_site_resolution.py` and
  `windows/tools/test_gpu_block_watch.py`. **Every one of the six is red at the
  same count on a pristine `git archive` of `5b5b7f2`**, measured in the same
  run: 1, 2, 3, 2, 1 and 4 failures. So nothing here turns a green run red.
  What this change does is widen a drift three of them already carry
  (`test_check_doc_figure_pins.py` was 5 lines out before this change and is 11
  after). Re-cutting them is a separate piece of work on files this one does not
  otherwise touch, and is named rather than done.

## What is not claimed here

No pin was moved, and no census CSV or `registers.yaml` row was touched — the
value of the checks above is precisely that they go red when those move. The
correction to
[`xdata-ownership-main-keys-pin.md`](xdata-ownership-main-keys-pin.md)'s
closing generalisation is made in that file, beside the sentence it corrects,
per §4a-4d. Nothing here is a claim about what the EC does with a byte: no
file was opened, no register read back, and no capture taken.
