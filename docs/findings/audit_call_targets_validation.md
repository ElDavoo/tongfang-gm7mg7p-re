# Validation of audit_call_targets.py call-target CSV tables

## Summary

Three committed CSV files record call targets enumerated from the EC firmware by
`audit_call_targets.py`:

- `ec/annotations/bank-call-targets.csv` — 5,998 rows of absolute-form calls
  (`lcall`/`ljmp`)
- `ec/annotations/bank-paged-call-targets.csv` — 3,481 rows of paged-form calls
  (`ajmp`/`acall`)
- `ec/annotations/bank-relative-branch-targets.csv` — 9,076 rows of relative-form
  branches (`sjmp`, `jc`, `jnc`, `jz`, `jnz`, `jb`, `jnb`, `jbc`, `cjne`, `djnz`)

Total: **18,555 rows** across all three tables.

These tables are machine-generated from the committed firmware image
`ec/firmware/GMxMGxx_11.800` by the three survey functions `survey()`,
`paged_survey()`, and `relative_survey()`. A new `--check` mode regenerates all
three tables and compares them byte-for-byte against the committed versions.

## Verification

All three tables regenerate identically from the committed firmware image:

```bash
$ python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --check
ok  bank-call-targets.csv: 5998 rows
  ok  bank-paged-call-targets.csv: 3481 rows
  ok  bank-relative-branch-targets.csv: 9076 rows
all committed tables verified: 18555 rows total
```

The `earlier_record` column in all three CSVs is deterministically generated and
is part of the byte-for-byte check. No hand-editing of this column is permitted;
if regeneration produces a different value, the check fails.

## Gate integration

The `--check` mode is wired into `.github/scripts/agent-gates.sh` as part of the
cheap-tier tooling checks. It runs without Ghidra, without network access, and
without a scratch directory. On every agent commit, regeneration must produce
identical output or the gate fails.

The `--self-test` mode includes assertions that verify both the nominal case
(all three tables match) and poisoned cases (single-cell edits to each CSV are
caught as failures).

## What this establishes

1. **Deterministic regeneration**: The three survey functions produce identical
   output when run over the same firmware image.

2. **No hand-editing**: The committed tables are the canonical source of truth.
   Any hand-edited cell is detected immediately by the gate.

3. **Alignment with other tools**: Following the pattern established by
   `xdata_register_map.py`, `call_graph.py`, `group_functions.py`, and others:
   committed machine-generated CSVs are validated on every run.
