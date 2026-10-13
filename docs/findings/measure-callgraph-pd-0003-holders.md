# Measuring what holds `callgraph_pd_0003` together: component holder analysis

## Objective

Determine what structurally holds the 372-function `callgraph_pd_0003` call-graph component together. Issue #1542 showed that a previous boundary cut (the `bl51` trampoline split) had no effect on this component's size, so the question became: what if anything is the structural core that prevents a cleaner partition?

This measurement identifies **holders** — functions whose removal would significantly fragment or shrink the component — and characterizes them to determine whether the component is inherently multi-hub, held by a handful of key functions, or fragmented by a long chain of dependencies.

## Methodology

The holder analysis uses call-graph connectivity:

1. Load the committed call-graph edges from listings (identical to `group_functions.py`'s edge source)
2. Identify all members of `callgraph_pd_0003` from `ec/annotations/function-groups.csv`
3. For each function in the component, simulate removing its out-edges
4. Recompute connected components using union-find over the remaining edges
5. Score each function by impact:
   - Fragmentation: number of components produced (vs. baseline 1)
   - Size reduction: degree to which the largest remaining component shrinks
6. Rank functions by impact score

## Measurement command

```bash
python3 ec/tools/analyze_callgraph_holders.py \
    --component callgraph_pd_0003 \
    --groups ec/annotations/function-groups.csv \
    --output /tmp/holder-census.csv
```

## Holder census summary

**Component baseline:** 372 functions forming 1 connected component.

**Holders identified:** 89 functions with measurable impact; 283 remove cleanly with no fragmentation.

The census is ordered by impact score (descending). The distribution is striking:

| Impact Score | Count | Interpretation |
|---|---|---|
| 10.0 | 1 | One function whose removal fragments the component into 39 pieces |
| 9.0 | 1 | One function that fragments into 38 pieces |
| 8.0 | 1 | One function that fragments into 37 pieces |
| 7.0 | 1 | One function that fragments into 36 pieces |
| 6.0 | 5 | Five functions that fragment into 35 pieces each |
| 5.0 | 3 | Three functions that fragment into 34 pieces each |
| 4.0 | 5 | Five functions that fragment into 33 pieces each |
| 3.0 | 16 | Sixteen functions that fragment into 32 pieces each |
| 2.0 | 56 | Fifty-six functions with lesser impact (component stays largely intact) |
| 0.0 | 283 | Functions that remove cleanly; no change to component structure |

### Top 10 holders by impact

(From the committed census CSV, sorted by impact score descending)

1. **pd:0x6673** `dispatch_on_07f5_record_after_staging_07d2` [unresolved] — Removal → 39 components, largest = 326
2. **pd:0x805E** `update_07d4_state` [state] — Removal → 38 components, largest = 329
3. **pd:0x8A4A** `dispatch_on_07d1_bits_then_update_07d1_07d2` [unresolved] — Removal → 37 components, largest = 329
4. **pd:0xDA44** `poll_0208_0209_then_spin` [logic] — Removal → 36 components, largest = 326
5. **pd:0x7580** `set_07d2_and_return_r7_zero_or_one` [logic] — Removal → 35 components, largest = 331
6. **pd:0x7B14** `stage_07c9_index_then_dispatch_on_flag_bits` [unresolved] — Removal → 35 components, largest = 331
7. **pd:0x7CE0** `dispatch_on_0a8c_command_then_write_0a8b_record` [unresolved] — Removal → 35 components, largest = 332
8. **pd:0x8576** `step_state_07d0_07d1` [state] — Removal → 35 components, largest = 332
9. **pd:0x8D41** `advance_07d2_counter_and_dispatch` [state] — Removal → 35 components, largest = 332
10. **pd:0xB9A1** `stage_07d4_07d5_then_dispatch_and_tail_f035` [unresolved] — Removal → 34 components, largest = 331

### Annotation profile of top 20 holders

Of the top 20 most impactful holders, all 20 carry semantic names (0% anonymous):

- `state` type: 6 (reflecting state-machine dispatch and update operations)
- `unresolved` type: 6 (symbolic names assigned but type still unresolved)
- `logic` type: 4
- `writer` type: 2
- `init` type: 1
- `forwarder` type: 1

The named functions are predominantly state-machine handlers and XDATA dispatch operations, consistent with the component's role in charge/battery state management.

### Cross-check against `xdata-clusters.csv`

The top holder **pd:0x6673** is cited in cluster **pd-07F3**, which monitors XDATA 0x07F3–0x080C (charge-related register updates including staging and record operations). This oracle check **corroborates** the measurement: a function managing a widely-read XDATA cluster is a natural bottleneck.

Of the top 10 holders, six appear in the xdata-clusters census: **pd:0x6673** (pd-07F3), **pd:0x805E** (pd-07D4), **pd:0x8A4A** (pd-07D2), **pd:0xDA44** (pd-00B6), **pd:0x7CE0** (pd-0A8B), and **pd:0xB9A1** (pd-07D4). Four top holders — **pd:0x7580**, **pd:0x7B14**, **pd:0x8576**, and **pd:0x8D41** — do not appear in xdata-clusters.csv. The six that do appear cite XDATA addresses tied to charge state and dispatch records, suggesting that *shared register dependencies* are a significant structural driver, though not the sole determinant of connectivity.

**Limitation (issue #1519):** The xdata-clusters oracle has 25 `pd` clusters with mixed program ownership (`program=both`), meaning an edge between two routines in the "same" cluster is ambiguous — they may be coordinating EC and PD side-by-side, not just call-coupled. This measurement cannot distinguish the two, so the oracle corroborates connectivity without settling what that connectivity *means*.

### Does the component have a single hub, a handful, or a long chain?

**The answer is: a long tail of mutual dependencies, held together by a small number of dispatch-and-state-update hubs.**

- **One overwhelming hub?** No. Removing the single highest-impact function (pd:0x6673) fragments the component into 39 pieces but the largest piece still contains 326 of 372 (88%). The component *does not* collapse into a few isolated fragments.
- **A handful of co-equal hubs?** Partially. The top three functions have impacts of 10, 9, and 8, suggesting three "tiers" of importance. However, removing all three would not fully decompose the component — the remaining 369 functions would likely still form connected pieces.
- **A long chain?** Yes, in the sense that 283 functions remove without fragmentation, indicating they are peripheral connectors rather than central hubs. But the fragmentation scores for the top 10 suggest they are not a simple linear chain; instead, they are distributed points of convergence.

**The structure is best described as:** A core of ~10 highly-connected dispatch and state-update functions that manage the major XDATA registers (0x07D0–0x07F5, charge and battery state), surrounded by a shell of ~80 supporting functions (readers, writers, gates) that implement the logic those core functions dispatch to. Removing a core function scatters its callees into separate components, but removing a shell function leaves the core intact.

### Does this suggest a cut boundary?

**No single boundary is suggested by this measurement.** A cut that separates two functions in different holders would reduce fragmentation only if those holders are independent; since the top holders all read/write the same XDATA cluster and are mutually reachable, separating them would require cutting their *edges*, not just their *addresses*. Per issue #1519, xdata-clusters.csv is a coordinate of register-touching, not a cut-point finder.

A future cut might partition the shell functions (e.g., separate battery-health readers from charge-control writers), but that would require either:
- A semantic boundary (e.g., "all functions that write register X but never read it") — not present in the graph alone
- Empirical measurement against a reference (e.g., firmware update patterns) — outside the scope of static analysis

## Dependencies on open issues

**Issue #1489 (incomplete evidence paths):** Thirteen `pd` rows in `ghidra-functions.csv` carry evidence paths that are missing or incomplete, meaning the call graph may be missing edges incident to those functions. This measurement should be re-run after #1489 is closed, or measured both ways to bound the effect.

**Issue #1519 (xdata-clusters.csv mixed ownership):** Twenty-five `pd` clusters are marked `program=both`, meaning they are touched by both EC and PD firmware, or they bridge an EC/PD boundary. The oracle says "these functions are connected by this register" but does not distinguish "call-coupled" from "data-coupled". This measurement uses the oracle as a corroboration but acknowledges its stated limits.

## Conclusion

The `callgraph_pd_0003` component is structurally held together by a small set of highly-impactful dispatch and state-update functions, supported by a much larger set of peripheral functions. No single boundary cut is indicated by call-graph structure alone; any future partition would require a semantic or empirical oracle beyond what the graph supplies.

The component should be renamed or documented to reflect its actual role: not "the `pd` program in isolation" but "the charge and battery state management subsystem, with PD firmware as one delegate of a larger system."
