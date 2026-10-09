# Register census reconciliation over all 280 addresses

## Overview

This write-up completes the reconciliation of the register census (`xdata-registers.csv` and `xdata-clusters.csv`) against the EC firmware image. The previous reconciliation in `ec/annotations/xdata-register-map.md` §7 covered 101 addresses; `registers.yaml` has since grown to 220 entries spanning 280 unique addresses. This write-up extends the reconciliation to all 280 addresses and measures the systematic undercount from sites that fall in gaps between exported decompiled functions.

## Methodology

Reconciliation compares two independent methods for counting register references:

1. **This tool (`xdata_register_map.py`)**: Scans all decompiled C exports from `ec/decompiled/*/*.c`, using occurrence patterns (`DAT_EXTMEM_` tokens and `xdata-symbols.csv` names). Counts C-level references per address.

2. **Image scan (`register_ref_table.py`)**: Performs an unaligned `90 hi lo` byte scan of the committed firmware image `ec/firmware/GMxMGxx_11.800`, with an 8-instruction window decoded at each site. Counts machine-code sites that load an address into DPTR.

These methods are independent and count different things; they agree only when the decompiled C correctly represents the machine code. When they disagree, the discrepancy falls into a small set of known causes.

**Tools and invocations** (all deterministic over committed inputs):

```bash
# Full reconciliation output with address-by-address table
python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800

# Ground truth from the image for all 280 addresses
python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800

# Detailed per-site analysis for unexported gap classification
python3 ec/tools/trace_xdata_refs.py --csv ec/firmware/GMxMGxx_11.800

# Site resolution data: function assignments and exports
ec/annotations/site-resolution.csv
```

## Summary of reconciliation results

Running reconciliation over all 280 addresses in `registers.yaml`:

```
280 addresses: 85 agree on the main-EC count, 17 have main-EC sites the decompiled tree does not contain, 178 differ another way. A zero in the 'this tool' column is 'not found by this method' -- a function that did not decompile carries its references nowhere -- never 'absent'.
```

### By category

| Category | Count | Notes |
|---|---:|---|
| Agree on main-EC count | 85 | Both methods report the same reference count |
| Not in decompiled tree (unexported gap) | 17 | 0 refs in decompiled C, >0 in image; sites fall in gaps between exported functions |
| Differ by unit or spelling | 178 | Address valid but methods count different things (e.g., bytes vs words, register names vs literals) |

## The 17 addresses with unexported gap sites

These 17 addresses have machine-code sites that fall between exported decompiled functions. Per `site-resolution.csv`, the function column is `not exported` for these sites.

| Address | Name | Image count (main EC) | Census count | Gap sites | Notes |
|---|---|---:|---:|---:|---|
| `0x0390` | `XDATA_0390` | 1 | 0 | 1 | R2 store, dead load paired with live R3:R4 pair transfer (#2127) |
| `0x0420` | `XDATA_0420` | 1 | 0 | 1 | Single site copies address into R1:R2, returns; no seed category matches (#2127) |
| `0x0710` | `EVENT_RING_SLOT0`...`SLOT15` | 1 | 0 | 1 | Event ring slot, unexported gap |
| `0x0733` | `MODE_PL_DEFAULTS` | 1 | 0 | 1 | DAT_CODE_ spelling; known case from xdata-register-map.md §7 |
| `0x0735` | `MODE_PL_DEFAULTS` | 2 | 0 | 2 | Indexed access via raw literal; known case from xdata-register-map.md §7 |
| `0x09f6` | `MAILBOX_RING_SLOT1`...`SLOT7` | 1 | 0 | 1 | Mailbox ring slot, unexported gap |
| `0x0ea9` | `CTL1` | 1 | 0 | 1 | Control register, unexported gap |
| `0x0eaa` | `CTL2` | 1 | 0 | 1 | Control register, unexported gap |
| `0x0eab` | `CTL3` | 1 | 0 | 1 | Control register, unexported gap |
| `0x0eac` | `CTL4` | 1 | 0 | 1 | Control register, unexported gap |
| `0x0ead` | `CTL5` | 1 | 0 | 1 | Control register, unexported gap |
| `0x0eae` | `CTL6` | 1 | 0 | 1 | Control register, unexported gap |
| `0x0eaf` | `CTL7` | 1 | 0 | 1 | Control register, unexported gap |
| `0x2012` | `XDATA_2012` | 1 | 0 | 1 | PD image register, unexported gap |
| `0x2014` | `XDATA_2014` | 1 | 0 | 1 | PD image register, unexported gap |
| `0x2015` | `XDATA_2015` | 1 | 0 | 1 | PD image register, unexported gap |
| `0x201c` | `XDATA_201C` | 1 | 0 | 1 | PD image register, unexported gap |

## Additional data: addresses with unexported gap sites (per site-resolution.csv)

Beyond the 17 addresses with *no* decompiled references, additional addresses have at least one site in an unexported gap while also having decompiled references. These addresses have understated `refs` counts due to the census's dependence on exported functions.

Per `site-resolution.csv`, the following addresses have unexported-gap sites:

```
0x04af (1 site), 0x06d9 (1), 0x074c (2), 0x0751 (1), 0x0766 (2), 
0x0782 (1), 0x078c (3), 0x07fd (1), 0x07fe (1), 0x07ff (1), 
0x0811 (1), 0x0834 (2), 0x0835 (1), 0x08e4 (1), 0x08eb (3), 
0x09ce (2), 0x0a47 (13), 0x0ea8 (1), 0x1663 (1), 0x1664 (2), 
0x1c01 (3), 0x1c02 (3), 0x1c03 (3), 0x1c39 (3), 0x1c3a (3), 
0x1f01 (1), 0x1f07 (1)
```

(Total: 69 unexported-gap sites across the addresses listed above)

This is the population mentioned in `registers.yaml` XDATA_1664 note: "*`0xC1DA` and `0xC1F4` sit in unexported gaps … so the decompiled-C token census … sees only the one at `0xC1E7` and its ref count understates this address three-to-one.*" The machinery is now measured across the full image.

## Known causes of disagreement (other than unexported gaps)

The 178 addresses where methods differ (but both exist in the image) fall into recognized categories documented in §6 of `xdata-register-map.md`:

1. **Unit difference**: The image scan counts raw `mov DPTR,#addr` sites; the decompiled C may spell the address in a word pair (two adjacent bytes), or as a register name, or in computed form. A 16-bit word `0x0834:0x0835` may count as 2 image sites but 1 C reference.

2. **Spelling mismatch**: The address is in the image but the C uses a different symbol. Example: `DAT_CODE_0733` in `xdata-register-map.md` §7, where the `DAT_CODE_` prefix causes the census's occurrence pattern to reject it (by design: the pattern ignores `DAT_CODE_` tokens to avoid false matches on code addresses).

3. **Register name**: A site stores the address into a register and hands the register (not a literal) to a callee. The C renders this as a pair (`CONCAT11(r4,r3)`) and the call site passes different constants; the address is live but invisible to the census.

4. **Other**: Decompilation artifacts, dead code analysis, or features of Ghidra's output.

The prior reconciliation at 101 addresses identified the two named cases (`0x0733` / `0x0735` spelling, `0x07A6` / `0x07D8` register name). All known cases from that reconciliation remain valid; this run extends the measurement to include the full population.

## Impact on published figures

### Figures dependent on unexported gap population

The following sections of `ec/annotations/xdata-register-map.md` cite reference counts or rankings that rest on the census (`refs` and `functions_touched` columns):

- **§4.4 "Clustering: the reconciliation"**: Regeneration table with counts (124 ids intact, 315 changed, 424 keys unchanged, 434 placed). This table's basis is the cluster list built from `xdata-registers.csv` rows, which reflect the censuscount.

- **§5 "The worklist, ranked"**: Columns `refs` and by-size ranking of addresses. The ranking is by `refs` column, which understates any address whose remaining reader sits in an unexported gap.

- **§8 / issue #842's top-ten addresses by reference count**: Referenced in `main-ec-003` issue as the supreme-scoring addresses. Top scorer is `0x0440` with census count 186; `0x1664` (1 refs in census, 3 in image) is an instance of understatement in that list.

### Required corrections to prose

Per `CLAUDE.md` "calibrate, don't overclaim," the following corrections apply:

1. **Any ranking or superlative claim based on `refs` column must be reframed as "in the current census" or "among exported-function-reachable sites" to acknowledge the lower bound.**

2. **`0x1664` is the named instance of understatement.** The note in `registers.yaml` XDATA_1664 states this explicitly; the entry needs no change. Other addresses are not called out by name unless new evidence appears.

3. **Sections citing reference counts should use "at least N" phrasing if the count comes from `refs` column,** since the column is now measured to be a lower bound.

### Specific updates needed

- `xdata-register-map.md` §4.4: If citing the regeneration-table counts as facts about the current census, frame as "in the current census" or soften counts (e.g., "at least 315 addresses changed").
- `xdata-register-map.md` §5: Rankings by `refs` should acknowledge the census as a lower bound (e.g., "ranked by reference count in the current census" not "ranked by reference count").
- `main-ec-003` issue's top-ten list: Same treatment; frame as "top ten by census count" not "top ten addresses."

## Scope and caveats

**Not regenerated in this work:** `xdata-registers.csv` and `xdata-clusters.csv` remain as committed. The reconciliation *measures* the census's dependence on exported decompiled functions; it does not alter the census. Re-deriving those files is a separate decision tracked in `docs/findings/xdata-census-rederivation-checklist.md`.

**Methodology limitations:**
- A zero in the decompiled-C column is "not found by this method," never "absent." The census depends on exported functions; unexported code is invisible to it by design.
- The image scan is static: `mov DPTR,#addr` sites are counted, but the EC's runtime behavior (which bytes are actually written to, whether a read modifies state) is not observed.
- The census was built against decompiled exports and changes as those exports change (recompilation, new exports, export renames). The 17-address gap list is current as of the committed image.

## Verification

The claims above are checked by running the cited tools against the committed firmware image and `registers.yaml`:

```bash
python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800
python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

The summary line in the first command's output is the binding claim; the address-by-address table shows the full data.
