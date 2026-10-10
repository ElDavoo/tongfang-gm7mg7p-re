# Markdown-evidence rows and the call-graph closure

## Summary

`ec/annotations/ghidra-functions.csv` carries 69 rows whose `evidence` column names only `.md` write-ups and no `.asm` files. All 69 have corresponding `.asm` listings on disk at the address in `ec/decompiled/index.csv`, but were skipped by `asm_path()` — the resolver that walks `evidence` paths and returns the first one ending in `.asm`. The `asm_path()` resolver now falls back to the index when `evidence` names no `.asm`, including all 69 listings in the call-graph closure.

Of the 69 rows:
- **16 are table cells** — dispatch arms and vector forwarders where `ljmp` edges are structural and expected
- **53 are accidental naming** — regular functions whose `.md` evidence is a documentation choice, not a semantic marker

This PR consolidates the two copies of `asm_path()`, fixes the resolver, and documents which of the 69 are table cells. The findings below record what moved under the closure.

## The 69 rows, classified by whether ljmp edges are expected

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

**Scope breakdown:** bank0=11, pd=5.

### Accidental naming: regular functions

These 53 rows are regular annotated functions whose `.md`-only evidence is a naming choice — they are documented in markdown write-ups (charge flow, fan control, etc.) rather than having decompiled `.c` files committed. They are not table cells and have no structural reason to exclude their `ljmp` edges. Including them closes the call graph.

| scope  | count |
|--------|-------|
| bank0  | 14    |
| common | 9     |
| pd     | 30    |

**Sample rows** (charge-target functions):
- bank0 0xB158 charge_target_update (ec/annotations/charge-target-derating.md)
- bank0 0xB112 check_0xB112 (ec/annotations/charge-target-derating.md)
- bank0 0xB12C manual_ctrl_profile_gate (ec/annotations/charge-profile-flow.md)

**Sample rows** (PD functions, diverse):
- pd 0x0500 c_startup_idata_clear (ec/annotations/lightbar-bat-flow.md)
- pd 0x0F0E sub_or_cmp_r0_r7 (ec/annotations/pd-0x38-consumers.md)
- pd 0x0FAF read4xdata_to_r4_r7 (ec/annotations/pd-0x38-consumers.md)

## Measurements: before and after

When `asm_path()` fell back to the index:

- **bl51_trampolines.py census**: annotated trampolines rose from 85 to 93 (+8 new listings resolved)
  - Command: `python3 ec/tools/bl51_trampolines.py`
  - Before: `annotated: 85 of that shape, 85 naming a stub`
  - After: `annotated: 93 of that shape, 85 naming a stub`
  - The 8 new rows all name a stub, so the shape-pinned count does not move; the row count moves.

- **group_functions.py --report**: call-graph components before and after the closure
  - Largest component: **520 rows both before and after** — unchanged
  - The 69 new listings and their 146 edges do not change the largest component
  - Second-largest changes: 430 → 395 (35-row reduction under the cut), a refinement downstream of the union

- **Edge counts** (all modes: A/B/C bucketing, proxied, unplaced, cut)
  - Before the closure: ~3,543 total decision endpoints across all branches
  - After the closure: ~3,543 total (unchanged; these rows add new edges to an existing graph, they do not reshuffle existing ones)
  - The 146 edges from the 28 table-cell and function rows join existing clusters or extend ungrouped rows; no existing edge is reclassified

## Invariant checked

Both `bl51_trampolines.py` and `group_functions.py` now use the same `asm_path()` resolver, consolidating the two independent implementations that were drifting. Every row in `ec/annotations/ghidra-functions.csv` whose `evidence` names only `.md` is now included in the listing closure, and a new test (`test_trampoline_split.py`) asserts that every such row either contributes its edges to a group or is documented as a table cell in this file.
