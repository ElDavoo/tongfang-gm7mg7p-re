# Markdown-evidence rows and the call-graph closure

## Summary

`ec/annotations/ghidra-functions.csv` carries rows whose `evidence` column names only `.md` write-ups and no `.asm` files. All such rows have corresponding `.asm` listings on disk at the address in `ec/decompiled/index.csv`, but were skipped by `asm_path()` — the resolver that walks `evidence` paths and returns the first one ending in `.asm`. The `asm_path()` resolver now falls back to the index when `evidence` names no `.asm`, including all such listings in the call-graph closure.

These rows classify into two categories:
- **Table cells** — dispatch arms and vector forwarders where `ljmp` edges are structural and expected
- **Accidental naming** — regular functions whose `.md` evidence is a documentation choice, not a semantic marker

This PR consolidates the two copies of `asm_path()`, fixes the resolver, and documents which rows are table cells. The findings below record what moved under the closure.

## Rows classified by whether ljmp edges are expected

### Table cells: dispatch and vector arms

These rows' names indicate they are dispatch arms or vector forwarders. A function at one of these addresses is a cell in a lookup table or a vector entry, so `ljmp` edges reaching it are structural — the table itself is the call site, not a direct function call. The `.md`-only evidence is a documentation choice: these rows are named and documented to explain what the dispatch does, not to separate them from call-graph closure.

| scope | addr   | name                      | evidence                                       |
|-------|--------|---------------------------|------------------------------------------------|
| bank0 | 0x8054 | index_case_00             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x8094 | index_case_01             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x80D7 | index_case_02             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x811A | index_case_03             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x815D | index_case_04             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x819D | index_case_05             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x81DF | index_case_06             | ec/annotations/bank-call-audit.md              |
| bank0 | 0x821F | index_case_epilogue       | ec/annotations/bank-call-audit.md              |
| bank0 | 0x8274 | index_table_default       | ec/annotations/bank-call-audit.md              |
| bank0 | 0x8283 | reserved_not_dispatched   | ec/annotations/bank-call-audit.md              |
| bank0 | 0x8292 | dispatch_0x80              | ec/annotations/bank-call-audit.md              |
| pd    | 0x0000 | reset_vector_forwarder    | ec/annotations/pd-reset-vector.md              |
| pd    | 0x0003 | int0_vector_forwarder     | ec/annotations/pd-interrupts.md                |
| pd    | 0x000B | int1_vector_forwarder     | ec/annotations/pd-interrupts.md                |
| pd    | 0x0013 | timer1_vector_forwarder   | ec/annotations/pd-interrupts.md                |
| pd    | 0x0017 | serial0_vector_forwarder  | ec/annotations/pd-interrupts.md                |

### Accidental naming: regular functions

Regular annotated functions whose `.md`-only evidence is a naming choice — they are documented in markdown write-ups (charge flow, fan control, etc.) rather than having decompiled `.c` files committed. They are not table cells and have no structural reason to exclude their `ljmp` edges. Including them closes the call graph. These rows span bank0, common, and pd scopes.

**Sample rows** (charge-target functions):
- bank0 0xB158 charge_target_update (ec/annotations/charge-target-derating.md)
- bank0 0xB112 check_0xB112 (ec/annotations/charge-target-derating.md)
- bank0 0xB12C manual_ctrl_profile_gate (ec/annotations/charge-profile-flow.md)

**Sample rows** (PD functions, diverse):
- pd 0x0500 c_startup_idata_clear (ec/annotations/lightbar-bat-flow.md)
- pd 0x0F0E sub_or_cmp_r0_r7 (ec/annotations/pd-0x38-consumers.md)
- pd 0x0FAF read4xdata_to_r4_r7 (ec/annotations/pd-0x38-consumers.md)

## Verification

When `asm_path()` fell back to the index, the closure changed as follows:

- **bl51_trampolines.py census**: newly-resolved markdown-only listings were added to the shape's annotated set
  - Run `python3 ec/tools/bl51_trampolines.py` to verify the count of resolved listings
  - All newly-resolved rows continue to name stubs (unchanged shape constraint)

- **group_functions.py --report**: call-graph components remain consistent
  - The largest component is unaffected by the new listings
  - The closure adds edges to existing clusters or extends ungrouped rows; no existing edge is reclassified
  - Run `python3 ec/tools/group_functions.py --report` to verify the component structure

- **Invariant preserved**: the shape pinning and total decision endpoint counts remain stable across the closure

## Invariant checked

Both `bl51_trampolines.py` and `group_functions.py` now use the same `asm_path()` resolver, consolidating the two independent implementations that were drifting. Every row in `ec/annotations/ghidra-functions.csv` whose `evidence` names only `.md` is now included in the listing closure, and a new test (`test_trampoline_split.py`) asserts that every such row either contributes its edges to a group or is documented as a table cell in this file.
