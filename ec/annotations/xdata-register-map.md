# The XDATA register map: 1,172 addresses, attributed and clustered

Issue #132 asks for a register map, on the argument that the decompiled EC
touches 1,134 XDATA addresses and that "**six** of those 1,134 are named" — so
99.5% read as `DAT_EXTMEM_0a56` and friends, and every comment, variable name
and function name is stuck describing a hex number. Its numbers reproduce
exactly. The reading does not, because *named* in that count means "written
as a `DAT_EXTMEM_` token that `xdata-symbols.csv` also names" — and every
address the main EC touches under a real symbol was outside the count.

**Headline verdict.** *The map is now a regenerable census, and the two
corrections to the issue are both about the census rather than the firmware.*

* **The decompiled C spells an XDATA address two ways**, and reading only
  `DAT_EXTMEM_` misses 41 main-EC addresses. `build_ec_decompile.py` applies
  `ec/ghidra/xdata-symbols.csv` before exporting, so the registers the symbol
  table can name come out as `CPU_TEMP` and
  `MODE_TCC_OFFSET_DEFAULTS_GAMING_0`, never as `DAT_EXTMEM_043e`. Reading both
  spellings gives **1,063** main-EC addresses in **13,937** references, of
  which **41 carry a name** and 1,022 do not. The main EC's named count is not
  zero and not six; §2 is the proof, and §7 reconciles the three the issue
  listed against the other method.
* **Nine of the issue's 14,399 references are this repository's own annotation
  text** quoting the decompile back at itself, in eight files. A hand-written
  comment is not the firmware touching an address, so the count is **14,390**.

The deliverable is `xdata-registers.csv` (one row per touched address) and
`xdata-clusters.csv` (one row per cluster), both regenerable by
`../tools/xdata_register_map.py` and both checked by its `--check`. The
clustering is the worklist; §5 is it, ranked. **It gives no register a purpose
and names nothing** — §6 says why, and the reading of a cluster is the
follow-up issue's job, not this file's.

## 1. Reproducing it

The issue's evidence, re-run unchanged, and the tool beside it:

```console
$ grep -rhoE 'DAT_EXTMEM_[0-9a-fA-F]{4}' ec/decompiled/*/*.c | wc -l
14399
$ grep -rhoE 'DAT_EXTMEM_[0-9a-fA-F]{4}' ec/decompiled/*/*.c | sort -u | wc -l
1134
$ python3 ec/tools/xdata_register_map.py
wrote /home/runner/.../ec/annotations/xdata-registers.csv: 1172 rows
wrote /home/runner/.../ec/annotations/xdata-clusters.csv: 435 rows
  main-ec: 1063 distinct addresses, 13937 references, 384 clusters at threshold 0.5
  pd: 157 distinct addresses, 864 references, 51 clusters at threshold 0.5
$ python3 ec/tools/xdata_register_map.py --check
/home/runner/.../ec/annotations/xdata-registers.csv: 1172 rows match a fresh generation from the committed tree at threshold 0.5
/home/runner/.../ec/annotations/xdata-clusters.csv: 435 rows match a fresh generation from the committed tree at threshold 0.5
```

The self-test is the oracle, and it pins the issue's numbers *and* the
corrections, so a change to what counts as a reference fails loudly instead of
making this file quietly wrong:

```console
$ python3 ec/tools/xdata_register_map.py --self-test
xdata_register_map.py --self-test
  ok    index.csv and the committed .c files still describe each other
  ok    the annotation CSV and index.csv agree on every address they share
  ok    no generated symbol name is also a function, parameter or local in the decompiled tree
  ok    every reference is in one of the five buckets ['read', 'write', 'read+write', 'passed-to-call', 'address-taken']
  ok    bucket counts sum to the reference count for every address
  ok    passed-to-call and address-taken both fire, so the two unresolved-direction buckets are not dead vocabulary
  ok    the issue's 14399 file-wide DAT_EXTMEM_ occurrences and the 9 of them that are this repository's own annotation text quoting the decompile are still where they were (raw: {'DAT_EXTMEM': 14399, 'symbol': 471})
  ok    oracle: DAT_EXTMEM_ only, what issue #132 counted -- main EC 1022 distinct / 13526 refs, PD 157/864, which is 1134 distinct addresses in all after the 48 both programs touch (got (1022, 13526) and (157, 864))
  ok    oracle: the 41 main-EC addresses the decompiler named, 411 references, and 0/0 of them in the PD image (got (41, 411) and (0, 0))
  ok    within each program the two spellings are disjoint address for address, so a named address is never also a DAT_EXTMEM_ token
  ok    the PD image is spelled entirely in DAT_EXTMEM_ tokens, which is gen_xdata_symbols.py's own refusal to name it
  ok    oracle: the full census, both spellings -- 1172 distinct / 14801 references, main EC 1063/13937 (got 1172/14801, (1063, 13937))
  ok    oracle: 109 PD-only, 48 touched by both (got 109 / 48)
  ok    main + PD equals the file-wide total on both axes
  ok    oracle: the top two main-EC addresses by reference count are 0x0440=181, 0x08A8=170 (got 0x0440=181, 0x08A8=170)
  ok    the 0x07D8 correction: its main-EC reference is spelled MODE_TCC_OFFSET_DEFAULTS_GAMING_0, and the PD image spells the same address DAT_EXTMEM_07d8 because it is not named there
  ok    of the 56 named addresses, 44 appear in the decompiled tree at all (got 44: 0x030E, 0x030F, 0x043E, 0x044F, 0x049F, 0x04A6, 0x04A7, 0x0522, 0x0523, 0x0730, 0x0731, 0x0732, 0x0734, 0x0736, 0x0737, 0x0740, 0x0741, 0x0743, 0x0744, 0x0745, 0x0746, 0x074E, 0x0751, 0x0766, 0x0767, 0x0768, 0x0782, 0x0783, 0x0784, 0x0785, 0x0786, 0x078C, 0x07A6, 0x07A7, 0x07A8, 0x07A9, 0x07AA, 0x07C6, 0x07CC, 0x07D0, 0x07D8, 0x07D9, 0x07DA, 0x07E2)
  ok    every address the tree spells by symbol is in the generated symbol table, so the name column can never be empty for one
  ok    the two blind-spot addresses are 0x0733, 0x0735; of them the one that is spelled at all is 0x0733, behind a CODE pointer (got 0x0733), and 0x0735 is not findable by any spelling
  ok    the `name` column is populated exactly for the addresses the symbol table names, independently of how the tree spells them
  ok    every address is in exactly one cluster
  ok    cluster sizes sum to the address count of each program
  ok    every shared function a cluster names resolves to a row in index.csv
  ok    the two unresolved-direction buckets survive into the CSV as their own columns
  ok    each reader function has a read or read+write reference of its own, and each writer a write or read+write one
  ok    readers and writers are subsets of the functions that touch the address, and neither exceeds it
  ok    the rank the report's worklist uses is total: no two clusters tie on size, references and lowest address
  ok    the clusters CSV is a projection of the registers CSV, not a separate count
  ok    the committed CSVs match a fresh generation (run without --check after changing anything the census reads)
  435 clusters at threshold 0.5; 1063 main-EC and 157 PD addresses
  all assertions passed
```

## 2. The two spellings, and what the issue's "six" actually counted

`ec/ghidra/README.md` step 3 of the decompilation order is "**XDATA named from
`registers.yaml` before decompiling**", so an address
`ec/ghidra/xdata-symbols.csv` can name is not written as a `DAT_EXTMEM_` token
anywhere in the export. That is visible in one line:

```console
$ grep -n 'CPU_TEMP' ec/decompiled/bank0/8749.c | sed -n '3p'
97:      if ((CPU_TEMP < 0x51) && (GPU_TEMP < 0x51)) {
$ grep -rhoE '\bCPU_TEMP\b' ec/decompiled/common/*.c ec/decompiled/bank0/*.c ec/decompiled/bank1/*.c | wc -l
54
```

Fifty-four mentions of `CPU_TEMP` in the EC programs, and **zero** of them
under a `DAT_EXTMEM_043e`. The same holds for the other 40 named main-EC
addresses. The split, from `xdata-registers.csv`:

| `program` | `spelled_as` | distinct | references |
|---|---|---:|---:|
| main-ec | `DAT_EXTMEM` | 977 | 12,692 |
| main-ec | `symbol` | 38 | 408 |
| both | `DAT_EXTMEM` | 45 | 1,056 |
| both | `symbol+DAT_EXTMEM` | 3 | 40 |
| pd | `DAT_EXTMEM` | 109 | 605 |
| **total** | | **1,172** | **14,801** |

Read the `symbol` and `symbol+DAT_EXTMEM` rows as the addresses the issue's
grep could not see: **41 addresses, 448 references**, all main EC. The
corrected form of the issue's claim is therefore

> 41 of the 1,063 XDATA addresses the main EC touches carry a name from
> `ec/ghidra/xdata-symbols.csv`. The other **1,022** read as
> `DAT_EXTMEM_xxxx`.

1,022 is unchanged — the issue's main-EC distinct count is right, and its
coverage of it was not. That gap is still the blocker the issue describes, and
it is still why this issue is on the critical path: 96% of the register file
the firmware actually uses has no name.

**The nine comment occurrences** are the smaller correction; the count is
pinned by the self-test's raw figure, so a tenth appearing fails the test
rather than passing quietly. `ec/decompiled/bank0/B9DF.c` line 9 writes ``the
decompiled C's `DAT_EXTMEM_0a56 = DAT_EXTMEM_1919` and its return value`` to
make a point *about* that code, and `ec/decompiled/pd/8210.c` line 9 writes
``renders it as FUN_CODE_dc29(0, DAT_EXTMEM_07d4)`` to make one about the PD
image. Seven of the nine are in `bank0`/`bank1` and two in `pd/`;
`strip_comments()` blanks them before the census reads, keeping line numbers
intact so a reader can still be pointed at the line. An annotation that quotes
an address is not the firmware touching it.

**`spelled_as` and `name` are different facts.** `spelled_as` is how the
decompiled text refers to the address; `name` is what the symbol table calls
it. The three `symbol+DAT_EXTMEM` rows are where they come apart: `0x07D0` is
`BATTERY_CHARGE_LIMIT_DOWN` in the `name` column and `DAT_EXTMEM_07d0` in the
PD image's own source, because `gen_xdata_symbols.py` emits `programs=bank0;bank1`
and refuses to name the PD program at all. Reading that row as the PD firmware
calling it `BATTERY_CHARGE_LIMIT_DOWN` is `pd-xdata-overlap.md`'s mistake in a
new place.

## 3. Two programs, and the split the clustering never crosses

`ec/decompiled/pd/` is the self-contained `ITE8850-PD` image at file `0x20000`
with its own address space and its own XDATA map (`../README.md`'s Layout
section; `pd-xdata-overlap.md` §5 is the standing argument for exactly
`0x04A6`). `../../docs/findings.md` §3a is what mixing the two cost last time,
so the split is the tool's first act and the similarity graph is built twice,
once per program.

| | distinct addresses | references |
|---|---:|---:|
| main EC (`common` + `bank0` + `bank1`) | 1,063 | 13,937 |
| PD image (`pd`) | 157 | 864 |
| PD-only, never touched by the main EC | 109 | |
| touched by both programs | 48 | |
| **all of it** | **1,172** | **14,801** |

45 of the 48 both-programs addresses are `DAT_EXTMEM_`-spelled in both; the
other three (`0x07D8`/`0x07D9`/`0x07DA`) are named in the EC and written as
`DAT_EXTMEM_` in the PD image. A shared address *number* is not a shared byte,
and the `program` column is on every row so no downstream reader can lose that.

## 4. The method, and where it can be argued with

### 4.1 Five direction buckets, one per reference

Each occurrence lands in exactly one, decided from the C around it:

| bucket | what it is | total |
|---|---|---:|
| `read` | the value is used | 7,483 |
| `write` | an `=` target, including Ghidra's `DAT_EXTMEM_1300 = DAT_EXTMEM_1300 & 0x0f` spelling | 4,019 |
| `read+write` | an `=` target whose right-hand side names the same address | 2,480 |
| `passed-to-call` | an argument of a call to a routine `index.csv` records | 548 |
| `address-taken` | `&DAT_EXTMEM_xxxx` | 271 |
| | | **14,801** |

`passed-to-call` is a bucket of its own on purpose, mirroring the `handoff`
bucket `../tools/register_ref_table.py` already reports: an 8051 has no Keil
calling-convention model, so `FUN_CODE_2990(DAT_EXTMEM_0a54)` may be passing a
value or a pointer the callee writes through, and the decompiled C cannot say
which. Folding it into "read" is the confident-sounding phrasing
`../../CLAUDE.md` rules out. The test is membership in `index.csv`'s name set
rather than a `FUN_CODE_` prefix, because `dptr_add_4x_a(DAT_EXTMEM_0a4c)` has
the same unresolved direction and does not carry the prefix; it also keeps
Ghidra's `CONCAT11`/`CARRY1` pseudomacros out, which are value expressions and
not handoffs.

`*DAT_EXTMEM_048a = DAT_EXTMEM_048d;` is the one shape the store rule
special-cases: the `=` lands on a dereference, so the byte at `0x048A` is read
as a pointer and the write goes wherever it points, not to `0x048A`. The
address is a `read`, and there are two such sites in the tree — both of them
the same shape, in `bank1/EF26.c` and the `bank1/EF32.c` that duplicates it. A
`*` followed by a *space* is Ghidra's multiplication rather than a
dereference (`(param_2 + (ushort)param_1) * DAT_EXTMEM_0826;`) and is a
`read` for the ordinary reason, the value being used.

### 4.2 The clustering, and the threshold

1. The address × function incidence matrix, built over the main EC and again
   over the PD image. Never across the two.
2. Two addresses are neighbours if Jaccard over their **combined
   touching-function set**, or over their **writer set**, is at least the
   threshold. The writer axis is the narrower one and is what keeps a block
   written by one routine and read by disjoint callers together. `0x04FE` and
   `0x04FF` are the worked case: 10 and 6 touching functions with exactly one
   in common (`bank1:0x94FA`, Jaccard 0.07), the same single writer for both
   (Jaccard 1.00). The touching relation alone scores the pair 0.07 and so
   never links them; the writer axis is what puts a 16-bit store's halves
   together. It is not a marginal addition, and the tool measures it:

   ```console
   $ python3 ec/tools/xdata_register_map.py --threshold-sweep --no-writer-axis | sed -n '1p;6p'
   threshold,relations,main-ec clusters,main-ec largest,main-ec singletons,pd clusters,pd largest
   0.50,touching,479,43,278,61,16,36
   ```

   against the 384 clusters with a largest of 109 that both relations give at
   the same threshold, in the full table below.
3. Clusters are **connected components**, not a greedy cover — the relation is
   not transitive, and a greedy pass would make the output depend on address
   order. Every address lands in exactly one; one with no neighbour is a
   size-1 cluster (212 of them on the main EC) rather than a drop.
4. Contiguity is reported as a `span_group` column and **never merged** into a
   cluster. Adjacent addresses are often one multi-byte store, and
   `gen_xdata_symbols.py` names those `_0`/`_1` by address order precisely
   because it refuses to bake a byte order into a symbol; merging on contiguity
   would make that same claim invisibly.
5. `shared_functions` in the clusters table is the subset touching two or more
   of the cluster's addresses — the co-occurrence that put them together.
   `callees` is the call-graph axis: the routines the most of the cluster's
   functions call, capped at three with the overflow counted in the cell
   (`(+232 more called by the cluster's functions)`). A cap that is not printed
   reads as "covered" when it is not.

The threshold is a flag (`--threshold`, default **0.50**) and the whole curve:

```console
$ python3 ec/tools/xdata_register_map.py --threshold-sweep
threshold,relations,main-ec clusters,main-ec largest,main-ec singletons,pd clusters,pd largest
0.30,touching+writers,242,401,127,35,38,11
0.35,touching+writers,340,114,173,48,35,23
0.40,touching+writers,352,111,183,49,35,24
0.45,touching+writers,381,110,210,51,34,26
0.50,touching+writers,384,109,212,51,34,26
0.55,touching+writers,534,42,331,69,16,41
0.60,touching+writers,543,42,339,69,16,41
0.65,touching+writers,555,42,351,69,16,41
0.70,touching+writers,603,42,393,78,14,52
```

0.50 is a recorded choice, not a tuned one: from 0.35 to 0.50 the largest
main-EC cluster holds at 109–114 while the cluster count only moves 340 → 384,
and 0.55 halves the largest cluster and adds 150 more. 0.30 collapses 401 of
the 1,063 into one component, which is the shape the issue warned about when it
said a cluster of functions that share them is a list someone can work
through. A reviewer who wants a different granularity passes `--threshold` and
`--check` fails until the committed CSVs match, so the choice is visible in the
diff rather than buried in a constant.

## 5. The worklist, ranked

By size, then reference count, then lowest address. Full rows in
`xdata-clusters.csv`; the `addrs` column there is the complete membership.

The last column is the repository's own hand annotations for the functions
`ghidra-functions.csv` names, not this tool's reading of them — which is the
point of §6 below.

| cluster | size | refs | range | named inside | the functions the cluster's addresses share |
|---|---:|---:|---|---|---|
| `main-ec-001` | 109 | 1,097 | `0x030E`-`0x1809` | 20 | `fill_08xx_from_code_table`, `apply_oem_overrides_then_fill_08xx`, `mode_tick_084c_07a5_09ee`, `charge_target_update` — the mode/OEM initialisation set |
| `main-ec-002` | 43 | 4,965 | `0x0460`-`0x09CE` | none | `decrement_nonzero_xdata_counters`, `read_06c6`, `dec_06c6_value` — one loop walking a block of counters |
| `main-ec-003` | 43 | 239 | `0x044C`-`0x1F07` | none | `gate_06e6_442_then_sync_046a_from_086b`, `dispatch_on_0860`, `clear_0860`, `copy_0866_86b_to_1c04_1c3a` |
| `main-ec-004` | 17 | 80 | `0x030A`-`0x082F` | none | `gate_1c00_init_defaults`, `gate_030a_030b_then_8892_887a` — init-time |
| `main-ec-005` | 17 | 70 | `0x0382`-`0x03C9` | none | `mul_0342_0514_into_0388_when_03d0_lt_0384` and one other |
| `main-ec-006` | 16 | 94 | `0x043E`-`0x300E` | `0x043E` | `init_163e_16f1_300e_3008` |
| `main-ec-007` | 13 | 184 | `0x0318`-`0x097C` | none | `bump_counter_054d`, `store_054d_set_bit_on_10` |
| `main-ec-008` | 12 | 280 | `0x0045`-`0x1504` | none | `poll_1304_1500_dispatch_0083`, three `ff_filler_not_a_function_*` |
| `main-ec-009` | 12 | 107 | `0x0A43`-`0x0FC3` | none | `store_16bit_sum_to_0a43_0a44`, `rotate_16bit_pair_and_range_check_0fc3` |
| `main-ec-010` | 12 | 40 | `0x049A`-`0x05B9` | none | `clear_049a_049e_0579_057a_05c2`, `combine_0490_0495_049d_flags_into_carry` |
| `main-ec-011` | 12 | 35 | `0x00C0`-`0x2275` | none | `copy_direct_65_66_to_x00c0`, `copy_x00c0_pair_to_iram_67_68` |
| `main-ec-012` | 10 | 91 | `0x0875`-`0x09E7` | none | `clamp_078b_level_into_0804`, two bit-clearing writers |

`main-ec-001` is the one that matters most and the one most likely to be
misread. It is where 20 named registers land, so it looks like "the named
registers, discovered again", but what the clustering actually found is that
the *initialisation* routines touch them all: a cluster is a co-occurrence, and
109 addresses reached by one mode tick and one OEM override pass is a statement
about init order, not about the registers' purposes. Reading it is one issue.
The top ten addresses by reference count (`0x0440` 181, `0x08A8` 170,
`0x0843` 168, `0x0844` 168, `0x0706` 160, `0x06D6` 148, then `0x080D` 137,
`0x063A` 136, `0x0986` 135, `0x07F3` 133) are the issue's own list and belong
in that reading: nine of the ten are in `main-ec-002`, and the tenth,
`0x0440`, is a size-1 cluster on its own. Its 181 references are 166 reads and
15 writes spread over 91 functions, and at threshold 0.50 it has no neighbour.
The most-referenced address in the firmware is the one the clustering cannot
place, which is worth an issue of its own.

The PD clusters are listed in the same table file. `pd-001` (34 addresses,
`0x00B6`-`0xFFE2`) and `pd-002` (20, `0x07F3`-`0x080C`) are the two worth an
issue; the other 49 are 26 singletons and 23 groups of two to seven.

**A judgement call on which cluster to read first is deliberately not made
here.** The report ranks by size and reference count and stops. That ordering
is a human's, and the issue says so too.

## 6. What this does not establish

- **Nothing observed on hardware.** No register was read, written or read
  back; nothing ran on the machine. This is static analysis of committed text
  and that is all it is (`../../CLAUDE.md`, "Cloud agents cannot reach the
  hardware"). Several clusters will end at "the code stores a value here and
  nothing in the dump reads it back", and only a live test settles what the EC
  then does with it.
- **No register is named and no cluster is given a purpose.** A cluster is a
  co-occurrence pattern in static code — "these 43 addresses are reached by
  126 functions between them, and four of those touch all 43" — and that is
  evidence about *shape*, not about *meaning*. §5's function names are the
  repository's own annotations; repeating them here attributes the reading to
  whoever wrote them, not to a cluster. Naming a block of XDATA from it would put a guess where a later
  reader takes it for a fact, which is the failure mode
  `../../docs/findings.md` §4 exists to prevent. That reading is the follow-up
  issue's work, one issue per cluster, and the titles should be written from
  §5 rather than from this paragraph.
- **A `write` count is not evidence the EC acts on the value.** Only a live
  behavioural test is. Nothing in either CSV is a `status:`, and no entry or
  status in `registers.yaml` changed in this work.
- **Every zero is "not found by this method", never "absent"** — and the two
  methods disagree on most rows for a reason that is not an error. §7 is the
  reconciliation; the short form is that a `MOV DPTR,#0x043E` is one
  instruction site and can be several C-level references, and a function that
  did not decompile carries its sites nowhere at all. `CPU_TEMP` reads 43
  against 15; `CHARGE_TARGET_MV` at `0x0522` reads 4 against 10. Opposite
  directions, both expected.
- **The census is a lower bound on the image.** It cannot see a function that
  did not decompile, a `DAT_CODE_`-typed value, or any address reached by
  pointer arithmetic — which is the indirect-addressing blind spot
  `../../docs/findings.md` §4c already forced the `0x07B9` retraction over.
  That cuts against the verdict as much as for it: the census can be missing
  addresses inside the clusters it reports.
- **The two programs' maps are separate in the census's bookkeeping, not
  proven separate in hardware.** That is `pd-xdata-overlap.md` §6's boundary
  and nothing here moves it. What this file does is make the split mechanical
  instead of remembered.
- **The `callees` column over-counts depth.** A name in a call position
  anywhere in a function's body counts as its callee, so a callee of a callee
  is credited to the outer function. It is a name-frequency column for picking
  a place to start reading, not a call graph.

## 7. Reconciling against the other method: one non-gap and two real ones

`../tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800` runs
both methods over all 56 `registers.yaml` addresses: this one over the
decompiled C, `register_ref_table.py` over an unaligned `90 hi lo` byte scan
of the committed image with an 8-instruction window decoded at each site. They
are independent, and they do not count the same thing.

```console
$ python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800 2>&1 >/dev/null
56 addresses: 26 agree on the main-EC count, 2 have main-EC sites the decompiled tree does not contain, 28 differ another way. A zero in the 'this tool' column is 'not found by this method' -- a function that did not decompile carries its references nowhere -- never 'absent'.
```

Most of the 28 differ because the units differ (§6). Two rows are worth
naming, and the first of them is a non-gap that reads exactly like one:

- **`0x07A6`** (`OEM_4_CHARGING_PROFILE`) and, with it,
  `0x07D8`/`0x07D9`/`0x07DA`, are the addresses a `DAT_EXTMEM_`-only reading
  would call blind spots. None of them is one. `0x07A6` has 7 byte sites and
  15 C-level references, all under the symbol; the three `0x07D8` family come
  out agreeing *exactly* — 1 main-EC site each — with the added wrinkle that
  the PD image spells them `DAT_EXTMEM_07d8` and friends because it is not
  named at all. Nothing was missing from the firmware; the grep could not see
  the names. That is why the self-test pins these three as agreeing rather
  than leaving them as a caution.
- **`0x0733`** (`MODE_PL_DEFAULTS_GAMING_DSTATE_3`) **and `0x0735`**
  (`MODE_PL_DEFAULTS_OFFICE_PL2_5`) are the two genuine gaps, and they fail in
  two different ways, both inside
  `bank0:0x94D0=copy_code_table_into_0730_07a7`:

  ```c
  puVar3 = &DAT_CODE_0733;                                    /* 0x0733 spelled, as a code pointer */
  MODE_PL_DEFAULTS_TURBO_PL1_8 = puVar3[0xc];
  ...
  sVar5 = 0x735;                                              /* 0x0735 never spelled at all */
  MODE_PL_DEFAULTS_OFFICE_DSTATE_7 = *(char *)(sVar5 + (ushort)bVar2) + '\x01';
  ```

  (`ec/decompiled/bank0/94D0.c`, verbatim except for the two trailing
  comments and the `...` lines, which stand for the ten and twelve
  intervening lines of that function.)

  `register_ref_table.py` finds 1 and 2 main-EC sites for them, all three
  `mov dptr,#0x073x` followed by `lcall 0xB939`. The census sees none: `0x0733`
  is behind a `DAT_CODE_` spelling, and `0x0735` is an indexed access off a raw
  base literal that no spelling search can reach.

  The tool deliberately does **not** add `DAT_CODE_xxxx` to its occurrence
  pattern, and the reason is the same PD/main discipline: of the 52
  `DAT_CODE_` tokens in the tree, `DAT_CODE_0460` and `DAT_CODE_049f` are just
  as likely to be common-area code as XDATA, and importing them would claim an
  XDATA address on a token that says *code*. The self-test pins the one
  address this hides, and §6 is where the other limit lives.

## 8. What follows

- One issue per cluster in §5's first twelve rows, each scoped to reading the
  functions in it and ending at whatever the code settles — with the live-test
  step written down as a human's where the code does not settle it.
- The top ten addresses by reference count get folded into the `main-ec-002`
  issue rather than opened separately: nine of the ten are in that cluster
  already, and the tenth is the `0x0440` singleton, so the cluster reading and
  the address reading should not be two efforts over the same code.
- `xdata_register_map.py --check` and `--self-test` belong in
  `check_ghidra_tooling` in `.github/scripts/agent-gates.sh`, next to
  `gen_xdata_symbols.py`'s `--check`. **A human makes that one-line change** —
  the branch's push token has no `workflow` scope, so it fails at the end
  rather than the start. Both modes need no Ghidra, no network and no image,
  which is what makes them affordable in that gate; `--reconcile` does need the
  image and is deliberately not in the list.
- A cluster that turns out to be a record table should say so in
  `pd-index-geometry.md`'s terms (base and stride, then the field layout), not
  here.
