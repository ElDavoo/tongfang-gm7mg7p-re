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
* **838 `==` comparisons were classified as stores**, which is the correction
  §4.3 is about. The direction buckets, the writer axis and the clustering all
  move; the census — 1,172 addresses, 14,801 references — does not. This one
  is the file correcting *itself*: `xdata-registers.csv` as first merged
  credited `0x0440` with 15 writers, and `registers.yaml` has said "**No
  writer**" all along.

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
wrote /home/runner/.../ec/annotations/xdata-clusters.csv: 426 rows
  main-ec: 1063 distinct addresses, 13937 references, 376 clusters at threshold 0.5
  pd: 157 distinct addresses, 864 references, 50 clusters at threshold 0.5
$ python3 ec/tools/xdata_register_map.py --check
/home/runner/.../ec/annotations/xdata-registers.csv: 1172 rows match a fresh generation from the committed tree at threshold 0.5
/home/runner/.../ec/annotations/xdata-clusters.csv: 426 rows match a fresh generation from the committed tree at threshold 0.5
```

The census is the same 1,172 addresses in the same 14,801 references as before
— §4.3 changed which *direction* each reference is, and not one address or
reference moved. The cluster count did, because the writer axis is built on
direction.

*(Written on issue #181's branch before #206 merged, and describing the same
regeneration from the other side; the figures in it are that branch's and
the transcript below is the merged tree's.)* **One regeneration note, so the next reader is not misled by a diff.** The
committed `name` column was stale against `ec/ghidra/xdata-symbols.csv` before
issue #181 touched either file: `registers.yaml` names 101 addresses, and the
two CSVs were still carrying the 56-address generation, so 36 register rows and
23 cluster rows had an empty `name`/`named_addrs` where a fresh generation
fills them in. `--check` was red on that alone. Regenerating for #181 swept it
in, and **every other field of both files is byte-identical**: no address,
cluster, size, reference count, bucket count or function list moved. The
`named_in_tree` oracle moved with it, 44 to 79, and that is the one number in
this file that the symbol table's growth changes — issue #132's own counts
(1,172 / 14,801, 1,063 main-EC, 109 PD-only, 48 both, the top two addresses,
and the 41 symbol-spelled main-EC addresses) are all unchanged, and all still
pinned. The `spelled_as` table in §2 is unchanged for the same reason: the
census reads how the committed `.c` spells an address, and no `.c` was
re-exported.

The self-test is the oracle, and it pins the issue's numbers *and* the
corrections, so a change to what counts as a reference fails loudly instead of
making this file quietly wrong. The three `classify(...)` lines per shape and
the two direction oracles are §4.3's; everything above and below them is the
census, and the census did not move.

```console
$ python3 ec/tools/xdata_register_map.py --self-test
xdata_register_map.py --self-test
  ok    index.csv and the committed .c files still describe each other
  ok    the annotation CSV and index.csv agree on every address they share
  ok    no generated symbol name is also a function, parameter or local in the decompiled tree
  ok    every reference is in one of the five buckets ['read', 'write', 'read+write', 'passed-to-call', 'address-taken']
  ok    bucket counts sum to the reference count for every address
  ok    passed-to-call and address-taken both fire, so the two unresolved-direction buckets are not dead vocabulary
  ok    classify('DAT_EXTMEM_0440 = 0;') is 'write'
  ok    classify('DAT_EXTMEM_0440 = DAT_EXTMEM_0440 & 0x0f;') is 'read+write'
  ok    classify('DAT_EXTMEM_0440 &= 0x0f;') is 'write'
  ok    classify('DAT_EXTMEM_0440 |= 0x0f;') is 'write'
  ok    classify('if (DAT_EXTMEM_0440 == 0) {') is 'read'
  ok    classify('if (DAT_EXTMEM_0440 == 0) {\n}') is 'read'
  ok    classify('if (DAT_EXTMEM_0440 != 0) {') is 'read'
  ok    classify('if (DAT_EXTMEM_0440 <= 7) {') is 'read'
  ok    classify('if (DAT_EXTMEM_0440 >= 7) {') is 'read'
  ok    classify('if (DAT_EXTMEM_0440 < 7) {') is 'read'
  ok    classify('if (DAT_EXTMEM_0440 > 7) {') is 'read'
  ok    classify('switch (DAT_EXTMEM_0440) {\ncase 1:\n}') is 'read'
  ok    classify('*DAT_EXTMEM_0440 = 5;') is 'read'
  ok    classify('param_1 = DAT_EXTMEM_0440;') is 'read'
  ok    classify('&DAT_EXTMEM_0440') is 'address-taken'
  ok    classify('switch_case_dispatch(DAT_EXTMEM_0440);') is 'passed-to-call'
  ok    classify('if (CPU_TEMP == 0) {') is 'read'
  ok    classify('CPU_TEMP = 0;') is 'write'
  ok    the issue's 8750 file-wide DAT_EXTMEM_ occurrences and the 9 of them that are this repository's own annotation text quoting the decompile are still where they were (raw: {'DAT_EXTMEM': 8750, 'symbol': 6176})
  ok    oracle: DAT_EXTMEM_ only, what issue #132 counted -- main EC 917 distinct / 7877 refs, PD 157/864, which is 1037 distinct addresses in all after the 37 both spell there (got (917, 7877) and (157, 864), 1037 distinct / 8741 refs in all)
  ok    oracle: the 146 main-EC addresses the decompiler named, 6060 references, and 0/0 of them in the PD image (got (146, 6060) and (0, 0))
  ok    within each program the two spellings are disjoint address for address, so a named address is never also a DAT_EXTMEM_ token
  ok    the PD image is spelled entirely in DAT_EXTMEM_ tokens, which is gen_xdata_symbols.py's own refusal to name it
  ok    oracle: the full census, both spellings -- 1172 distinct / 14801 references, main EC 1063/13937 (got 1172/14801, (1063, 13937))
  ok    oracle: 109 PD-only, 48 touched by both (got 109 / 48)
  ok    main + PD equals the file-wide total on both axes
  ok    oracle: the top two main-EC addresses by reference count are 0x0440=181, 0x08A8=170 (got 0x0440=181, 0x08A8=170)
  ok    the 0x07D8 correction: its main-EC reference is spelled MODE_TCC_OFFSET_DEFAULTS_GAMING_0, and the PD image spells the same address DAT_EXTMEM_07d8 because it is not named there
  ok    of the 172 named addresses, 150 appear in the decompiled tree at all (got 150: 0x030E, 0x030F, 0x0400, 0x0401, 0x0403, 0x0432, 0x0434, 0x0435, 0x0436, 0x0437, 0x0438, 0x0439, 0x043C, 0x043D, 0x043E, 0x043F, 0x0440, 0x0442, 0x0443, 0x0448, 0x0449, 0x044B, 0x044C, 0x044F, 0x0450, 0x0451, 0x0452, 0x0454, 0x0455, 0x0456, 0x0458, 0x0459, 0x045A, 0x045B, 0x045C, 0x045D, 0x045E, 0x045F, 0x0460, 0x0468, 0x049F, 0x04A6, 0x04A7, 0x0522, 0x0523, 0x055F, 0x0621, 0x0635, 0x0636, 0x0637, 0x0638, 0x0639, 0x063A, 0x06C2, 0x06C3, 0x06C5, 0x06D1, 0x06D2, 0x06D6, 0x06D8, 0x06D9, 0x06DA, 0x06DB, 0x06F3, 0x0706, 0x070B, 0x070D, 0x0723, 0x0730, 0x0731, 0x0732, 0x0734, 0x0736, 0x0737, 0x0740, 0x0741, 0x0743, 0x0744, 0x0745, 0x0746, 0x074E, 0x0751, 0x075B, 0x075C, 0x0766, 0x0767, 0x0768, 0x0782, 0x0783, 0x0784, 0x0785, 0x0786, 0x078C, 0x07A6, 0x07A7, 0x07A8, 0x07A9, 0x07AA, 0x07C4, 0x07C6, 0x07CC, 0x07D0, 0x07D1, 0x07D3, 0x07D4, 0x07D5, 0x07D8, 0x07D9, 0x07DA, 0x07E2, 0x07F3, 0x07F6, 0x0809, 0x080C, 0x080D, 0x0811, 0x0843, 0x0844, 0x085B, 0x0860, 0x0862, 0x0865, 0x0866, 0x0867, 0x0868, 0x0869, 0x086A, 0x086B, 0x086D, 0x086E, 0x0890, 0x089E, 0x089F, 0x08A0, 0x08A2, 0x08A7, 0x08A8, 0x08E4, 0x08EB, 0x0981, 0x0982, 0x0985, 0x0986, 0x09CE, 0x09E6, 0x09E7, 0x1C39, 0x1C3A, 0x1F01, 0x1F07)
  ok    every address the tree spells by symbol is in the generated symbol table, so the name column can never be empty for one
  ok    the two blind-spot addresses are 0x0733, 0x0735; of them the one that is spelled at all is 0x0733, behind a CODE pointer (got 0x0733), and 0x0735 is not findable by any spelling
  ok    issue #181: all 10 of pd-001's 0xFFxx addresses are carried by a `mov DPTR,#imm16` in the committed .asm, each to a `movx` -- and no 8051 direct-addressing opcode takes a 16-bit operand, so none of them can be a direct address whatever the decompiler spelled it (not found by this method: none)
  ok    and each is reached by the form the annotation records -- a `mov DPTR,#imm16` for 8 of them, a `mov DPTR` one byte below plus `inc DPTR` for 0xFFC1, 0xFFD1 (got a different form for: none)
  ok    and no other instruction in the PD tree names one of the ten -- a direct address and a bit address are both one byte wide, so there is no form in which a 0xFFxx value could be either (found: none)
  ok    oracle: the PD census holds 23 addresses at or above 0xF000, the same address for address (got 23: 0xFF40, 0xFF42, 0xFF4A, 0xFF62, 0xFF80, 0xFF84, 0xFF88, 0xFFC0, 0xFFC1, 0xFFC2, 0xFFC6, 0xFFD0, 0xFFD1, 0xFFD3, 0xFFD4, 0xFFD5, 0xFFD8, 0xFFDA, 0xFFDB, 0xFFDF, 0xFFE0, 0xFFE1, 0xFFE2)
  ok    every one of those 23 is backed by an encoding in the .asm, so the region is XDATA by opcode and not only by the decompiler's spelling (not found by this method: none)
  ok    exactly 3 of them -- 0xFFC1, 0xFFD1, 0xFFDB -- are reached by `inc DPTR` from the address below and never by a `mov DPTR` of their own, which is why a `90 hi lo` byte scan finds 20 of the 23 and misses these 3 (got 0xFFC1, 0xFFD1, 0xFFDB)
  ok    and no main-EC census address reaches 0xF000 either, the main EC's highest being 0x9000 (got 0 at or above 0xF000 and a ceiling of 0x9000), so the 0xF000-0xFFFF run is the PD image's own in the census -- which is a claim about a census, and a census is a lower bound
  ok    the hand-checked direction oracle: 5 addresses, 0x0440, 0x0443, 0x04FE, 0x04FF, 0x0860, each read off the decompiled C by hand rather than by this tool
  ok    the §4.1 bucket totals, read 8319 write 3186 read+write 2476 passed-to-call 549 address-taken 271 (got read 8319 write 3186 read+write 2476 passed-to-call 549 address-taken 271)
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
  426 clusters at threshold 0.5; 1063 main-EC and 157 PD addresses
  all assertions passed
```

The `of the N named addresses, M` line (101 and 79 when this was written) is a
second correction that has
nothing to do with the direction buckets, and it is **stale-pin damage from the
symbol table growing**, not from anything in §4.3: the table held 56 names when
that figure was measured and 44 of them were in the tree, it holds 101 now, and
79 of those are. The pin was never updated, so that assertion has been red on
`main` since the tool landed — the table already held 100 names in the very
commit that added it. Re-derivable without this tool: 79 of the 1,172 rows in
`xdata-registers.csv` have an address in `ec/ghidra/xdata-symbols.csv`.

**That block did not pass when it was first written, and the two failures
were both staleness rather than method.** The committed `xdata-registers.csv`
had an empty `name` column for every row and the committed
`xdata-clusters.csv` an empty `named_addrs` column for all 25 clusters that
have named addresses, while the tool fills both and its own self-test asserts
`name` is populated exactly for the addresses the symbol table names. So
`--check` and `--self-test` both failed on the tree this file describes —
nothing in `.github/scripts/agent-gates.sh` runs either mode, which is why it
went unnoticed. `ORACLE['named_in_tree']` had the same problem: it read 44
from when the 0x0400-0x045F page entries were added to `registers.yaml`
without the constant being re-derived, against 79 in the tree. Both are
corrected here, and §5's "named inside" column is a reading of the corrected
CSV — which is why four of its rows moved here too (`main-ec-001` 20 to 28,
`main-ec-003` and `main-ec-007` from `none`, and `main-ec-012` from `none` to
6). Only the `main-ec-012` row is this change's doing; the other three are the
drift above catching up, and the count in the CSV rather than the hand-typed
one in this table is the authority.

*(Merge note, 2026-09-24. The transcript above is re-run on the merged tree,
not copied from either branch. `named_in_tree` is 88 now, not 79 or 86: the two
extra are `0x075B`/`0x075C`, which #237 entered in `registers.yaml` as
`MAIN_FAN_L_DUTY`/`MAIN_FAN_R_DUTY` and which were exported by name once the
decompile was regenerated. (It is 150 in the transcript above, after issue
#179's 43 `XDATA_*` timer/counter entries, issue #180's 15 and issue #183's 4
were merged and exported the same way; the `DAT_EXTMEM_`-only figures fall accordingly and the full census does
not move.) The same regeneration moved 17 references from the
`DAT_EXTMEM_` spelling to those names, so the `DAT_EXTMEM_`-only oracle reads
13,878 raw and 979/13,005 for the main EC; the full census is unchanged. In §5
below, `main-ec-001`'s "named inside" is 29 for the same reason.)*

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

## 4. The method, where it can be argued with, and one correction to it

### 4.1 Five direction buckets, one per reference

Each occurrence lands in exactly one, decided from the C around it:

| bucket | what it is | total |
|---|---|---:|
| `read` | the value is used, which includes every `==` comparison | 8,319 |
| `write` | an `=` target, including Ghidra's `DAT_EXTMEM_1300 = DAT_EXTMEM_1300 & 0x0f` spelling | 3,186 |
| `read+write` | an `=` target whose right-hand side names the same address | 2,476 |
| `passed-to-call` | an argument of a call to a routine `index.csv` records | 549 |
| `address-taken` | `&DAT_EXTMEM_xxxx` | 271 |
| | | **14,801** |

The totals are the tool's own, and the self-test pins them — but a pin on this
table is internal: these are the buckets summed back to themselves, so they
catch a classifier that changes and not one that was wrong. §4.3 is what the
`read` row's size is *evidence* of, and it needed an external check. What moved
here is 837 references leaving the two store buckets: 833 `write` and 4
`read+write` became reads, 836 of them, plus **one that became
`passed-to-call`** because a comparison inside a call's argument list is a
handoff and not a bare read. Nothing moved into `address-taken`.

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

`*DAT_EXTMEM_048a = DAT_EXTMEM_048d;` is the other shape the store rule
special-cases: the `=` lands on a dereference, so the byte at `0x048A` is read
as a pointer and the write goes wherever it points, not to `0x048A`. The
address is a `read`, and there are two such sites in the tree — both of them
the same shape, in `bank1/EF26.c` and the `bank1/EF32.c` that duplicates it. A
`*` followed by a *space* is Ghidra's multiplication rather than a
dereference (`(param_2 + (ushort)param_1) * DAT_EXTMEM_0826;`) and is a
`read` for the ordinary reason, the value being used.

The two exclusions the store rule makes are both about what the `=` belongs to
rather than to the lvalue: a `*` before the address, and a `==` after it. The
second one is §4.3, and it is the larger of the two by three orders of
magnitude.

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

   against the 376 clusters with a largest of 108 that both relations give at
   the same threshold, in the full table below. That 479 is the one number in
   §4.2 that the §4.3 correction does **not** move, and it should not: the
   `touching`-only mode never reads a writer set, so the phantom writers could
   not reach it. The worked example survives the correction intact, because
   `0x04FE`/`0x04FF`'s one real writer at `bank1:0x94FA` was never a comparison.
3. Clusters are **connected components**, not a greedy cover — the relation is
   not transitive, and a greedy pass would make the output depend on address
   order. Every address lands in exactly one; one with no neighbour is a
   size-1 cluster (203 of them on the main EC) rather than a drop.
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
0.30,touching+writers,238,306,122,35,55,12
0.35,touching+writers,337,112,169,49,35,24
0.40,touching+writers,345,109,176,49,35,24
0.45,touching+writers,371,108,199,50,35,25
0.50,touching+writers,376,108,203,50,35,25
0.55,touching+writers,525,43,321,68,16,39
0.60,touching+writers,538,42,335,69,16,41
0.65,touching+writers,551,42,345,69,16,41
0.70,touching+writers,594,42,383,76,14,50
```

0.50 is a recorded choice, not a tuned one, and the fix did not retune it: from
0.35 to 0.50 the largest main-EC cluster holds at 108–112 while the cluster
count only moves 337 → 376, and 0.55 drops the largest to 43 and adds 149 more.
0.30 collapses 306 of the 1,063 into one component, which is the shape the issue
warned about when it said a cluster of functions that share them is a list
someone can work through. A reviewer who wants a different granularity passes
`--threshold` and `--check` fails until the committed CSVs match, so the choice
is visible in the diff rather than buried in a constant.

### 4.3 Correction: 838 `==` comparisons were classified as stores (2026-09-23, issue #178)

**What this file said.** §4.1's `write` and `read+write` totals, §4.2's writer
axis, and §5's clusters were all computed by a `store_target()` that asked
whether the operator after an address is in `ASSIGN` — and `ASSIGN` begins with
`'='`. A Ghidra comparison, `if (DAT_EXTMEM_0440 == '\0')`, satisfies that test
exactly. So 838 occurrences were classified as stores, and §5's row for
`0x0440` read *"Its 181 references are 166 reads and 15 writes spread over 91
functions."*

**Why that was wrong.** All 15 were `if (DAT_EXTMEM_0440 == ...)` tests. There
is no `DAT_EXTMEM_0440 =` anywhere in `ec/decompiled/`. The address is read 181
times and written never, which is what the `XDATA_0440` entry in
`../registers.yaml` has said — "**No writer**, no PD site, no upstream name" —
since before the map existed. The independent `trace_xdata_refs.py` sweep in
`xdata-0400-045f.md` agrees: 43 references, 0 writes.

This is the one case in this file where the **newer** record was the wrong one,
so the retraction runs backwards from the usual direction. The pre-fix CSVs
stay in git history, which is where those numbers remain visible; nothing here
is deleted to make room for the correction.

**What the corrected run gives.** 838 raw `==` in the tree, all 838 of them in
the census, and 837 of those 838 change bucket: 836 become reads, and one that
sits in a call argument becomes `passed-to-call`. The worst-hit addresses were
`0x06E6`, `0x0843`, `0x0844` and `0x08A8` (42 each) and `0x0706` (40).
`0x0860` is the
row that shows how far off it could get: it read as 0 read / 13 `write` / 3
`read+write` / 1 `passed-to-call` — a pure write-side dispatch byte — and is
14 read / 2 `write` / 0 `read+write` / 1 `passed-to-call`, the two stores being
`bank0/D281.c:18` and `bank0/D289.c:17` and the handoff `bank0/D091.c:69`.

> **CORRECTION (2026-09-24, review of PR #206) to the first version of that
> paragraph, which read:** "838 raw `==` in the tree, 837 of them in the
> census — the eighth-hundred-and-thirty-eighth is inside a comment, which
> `strip_comments()` blanks. All 837 become reads, except one that sits in a
> call argument and becomes `passed-to-call`." **The mechanism is wrong.**
> `strip_comments()` blanks none of the 838: counting the occurrences before
> and after it gives 838 of 838, and the nine token occurrences it does remove
> (§2's "nine comment occurrences") are `DAT_EXTMEM_` sites in annotation
> prose, not comparisons. So the census has always seen all 838. What the 837
> counts is the occurrences that **changed bucket**, and the one that did not
> is `DAT_EXTMEM_076a` at `bank0/A747.c:24` — `address-taken` before this fix
> and `address-taken` after it, because `classify()` tests
> `left.endswith("&")` before it ever reaches `store_target()`, and in
>
> ```c
> if (DAT_EXTMEM_076b == '\0' && (DAT_EXTMEM_0769 == '\0' && DAT_EXTMEM_076a == '\0')) {
> ```
>
> the token is preceded by the **second** `&` of a `&&`. 838 in the census, 837
> moved; the two were never the same number, and the difference is that site
> rather than a comment. This is §6's `&&` limitation below, and it is the
> adjacent finding this paragraph's wrong mechanism had hidden.

`0x0443` is the control, and it does not move: four genuine
read-modify-writes at `bank1/F11C.c:21`, `F11F.c:23`, `F2CA.c:23` and
`F2F3.c:25` stay `read+write`, because
`DAT_EXTMEM_0443 = (DAT_EXTMEM_0443 & 7) ± 1` is a store, not a comparison.
`!=`, `<`, `>`, `>=` and `<=` were never in `ASSIGN` and already fell through
— that is now measured by the self-test rather than asserted here, and no
`case DAT_EXTMEM_xxxx:` occurs in the tree either.

**How it is pinned.** The old self-test could not have caught this. Every
direction assertion in it was internal — "bucket counts sum to the reference
count for every address", "each writer function has a write or read+write
reference of its own" — and a misclassified comparison satisfies all of them,
because the misclassification is itself internally consistent. Two new
assertions fix that, and they are deliberately different in kind:

- a **classifier-shape table**, literal Ghidra-shaped lines run through
  `classify()`, which pins the `==` rejection itself and cannot be satisfied by
  a tree that happens to contain no comparisons;
- a **hand-checked direction oracle**, five addresses whose per-bucket counts
  were read off the decompiled C by hand with the greps cited beside each entry
  in the source. This is the only direction check in the tool that compares
  against something outside it. Run against the pre-fix classifier it fails on
  `0x0440` and `0x0860` and passes on `0x0443`, `0x04FE` and `0x04FF` — which
  is the point: it catches the mistake and does not fire on the cases the fix
  was not supposed to touch.

**Two things this correction did not do.** `DEFAULT_THRESHOLD` is untouched:
the sweep moved around 0.50, and re-tuning it to recover a prettier plateau
would be exactly the tuned-not-recorded outcome its own comment warns against.
And no `status:` in `../registers.yaml` moves — a miscounted comparison bucket
is not new evidence about the firmware, and `0x0440` was already
`present-untested` on a correct reading.

**The sweep of the other 100 `registers.yaml` addresses, since the question
"what else does this break?" deserves an answer rather than an assurance.** The
fix changed the direction of **210** addresses. Ten of those are named in
`registers.yaml`: `0x0403`, `0x0432`, `0x043C`, `0x0440`, `0x044B`, `0x0450`,
`0x045D`, `0x045F`, `0x07D1` and `0x07D8`. Eight of them claim a writer in
their note and still have one — their counts shrink, their direction claim
does not change. The other two, `0x0440` and `0x0403`, **had their last writer
removed and now agree with a note that was already in the file** ("**No
writer**", and "0x0403's 11 sites are all direct reads"). So the correction
makes the corpus more self-consistent, not less, and no note is contradicted
by it.

Thirteen other addresses do disagree with their note about direction — `0x07D0`,
`0x0443`, `0x07C6`, and the nine per-mode `MODE_PL_DEFAULTS` bytes — and
**this work neither caused nor cured any of them.** All thirteen are a
`registers.yaml` note written from `register_ref_table.py`'s site count read
against this tool's C-level reference count, which is the units difference §6
already describes. Two are recorded rather than resolved: `0x0443`, whose note
says "no writer" and then says the routines it names "move `0x0443`" (the C
holds four read-modify-writes, `register_ref_table.py` sees two reads), and
`0x07D0`, whose "the only committed writer … is the DSDT" is about the **EC's**
`0x07D0` while the census's `0x07D0` row is `program=pd` and belongs to a
different byte in a different program — `docs/findings.md` §3a's trap, now
with a row in a CSV that a careless reader can join to the wrong program.

**What it opens.** The `write` count is a C-level *shape*, not an
instruction-level one: it says the decompiler's output has an `=` with this
address as its lvalue, which is not quite the same as a store instruction.
Separately, the two methods now disagree about `0x0443` in a way this file
does not adjudicate — `../tools/register_ref_table.py`'s site-level linear walk
calls it two reads with no writer, the C-level census finds four
read-modify-writes. Different methods over different units, and a real open
question rather than an error in either.

## 5. The worklist, ranked

By size, then reference count, then lowest address. Full rows in
`xdata-clusters.csv`; the `addrs` column there is the complete membership.

The last column is the repository's own hand annotations for the functions
`ghidra-functions.csv` names, not this tool's reading of them — which is the
point of §6 below.

**The ids in this table are not the ids the first version of this file
published, and almost none of that is §4.3's doing.** The writer axis is built
on direction, so removing 837 phantom writers moved the clusters, and the
ranking is by size — which reorders everything below the top. A second,
independent movement comes from the `named inside` column alone: that column
counts addresses `ec/ghidra/xdata-symbols.csv` names, and the table grew from
56 names to 101 without these CSVs being regenerated. Sizes, reference counts
and ranges are §4.3; `named inside` is mostly the symbol table.

| cluster | size | refs | range | named inside | the functions the cluster's addresses share |
|---|---:|---:|---|---|---|
| `main-ec-001` | 108 | 1,136 | `0x030E`-`0x1809` | 29 | `fill_08xx_from_code_table`, `apply_oem_overrides_then_fill_08xx`, `mode_tick_084c_07a5_09ee`, `charge_target_update` — the mode/OEM initialisation set |
| `main-ec-002` | 44 | 248 | `0x044C`-`0x1F07` | 4 | `gate_06e6_442_then_sync_046a_from_086b`, `dispatch_on_0860`, `FUN_CODE_9d9b` — the `0x06E6`/`0x0860` gate block |
| `main-ec-003` | 43 | 4,965 | `0x0460`-`0x09CE` | none | `decrement_nonzero_xdata_counters`, `read_06c6`, `skip_06c6_decrement` — one loop walking a block of counters |
| `main-ec-004` | 30 | 312 | `0x030A`-`0x082F` | `0x0403` | three unnamed `bank1` routines (`0xDEE8`, `0xDEF1`, `0xDB0B`) — unnamed here, so this one needs reading before it can be titled |
| `main-ec-005` | 17 | 70 | `0x0382`-`0x03C9` | none | `mul_0342_0514_into_0388_when_03d0_lt_0384`, `FUN_CODE_d6ee`, `FUN_CODE_d946` |
| `main-ec-006` | 16 | 94 | `0x043E`-`0x300E` | `0x043E` | `FUN_CODE_9b3c`, `FUN_CODE_9c53`, `FUN_CODE_de83` |
| `main-ec-007` | 12 | 280 | `0x0045`-`0x1504` | none | three `ff_filler_not_a_function_*`, the fill stub block |
| `main-ec-008` | 12 | 107 | `0x0A43`-`0x0FC3` | none | `call_ef17_then_copy_0f80_to_0fb1`, `store_dptr_byte_to_0fb2_copy_0f82`, `FUN_CODE_f002` |
| `main-ec-009` | 12 | 40 | `0x049A`-`0x05B9` | none | `clear_049a_049e_0579_057a_05c2`, `latch_0490_bit3_or_bit7` |
| `main-ec-010` | 12 | 35 | `0x00C0`-`0x2275` | none | `copy_direct_65_66_to_x00c0`, `copy_x00c0_pair_to_iram_67_68` |
| `main-ec-011` | 10 | 91 | `0x0875`-`0x09E7` | 6 | `clear_08eb_bit5_09e6_09e7_08a1_089c_089d` and two unnamed `bank0` routines |
| `main-ec-012` | 9 | 36 | `0x0300`-`0x03FE` | none | `zero_0300_03ff_then_set_3fe_3a8_3fb`, `scan_table_03de_down_stride2` — the `0x0300` page |

`main-ec-001` is the one that matters most and the one most likely to be
misread. It is where 28 named registers land, so it looks like "the named
registers, discovered again", but what the clustering actually found is that
the *initialisation* routines touch them all: a cluster is a co-occurrence, and
108 addresses reached by one mode tick and one OEM override pass is a statement
about init order, not about the registers' purposes. Reading it is one issue.
The top ten addresses by reference count (`0x0440` 181, `0x08A8` 170,
`0x0843` 168, `0x0844` 168, `0x0706` 160, `0x06D6` 148, then `0x080D` 137,
`0x063A` 136, `0x0986` 135, `0x07F3` 133) are the issue's own list and belong
in that reading: nine of the ten are in `main-ec-003`, and the tenth,
`0x0440`, is a size-1 cluster on its own. **All 181 of its references are reads
and none of them is a write**, spread over 91 functions, and at threshold 0.50
it has no neighbour. The most-referenced address in the firmware is the one the
clustering cannot place, which is worth an issue of its own — and it is also
the address the §4.3 correction empties of writers, so a reading of it should
start from "91 functions consult this and none of them sets it".

The PD clusters are listed in the same table file. `pd-001` (35 addresses,
`0x00B6`-`0xFFE2`) and `pd-002` (20, `0x07F3`-`0x080C`) are the two worth an
issue; the other 48 are 25 singletons and 23 groups of two to seven.

### 5.1 `pd-001`'s ten high addresses are XDATA, and it is the encoding that says so

Ten of `pd-001`'s 34 addresses sit in `0xFF80`, `0xFF84`, `0xFFC0`-`0xFFC2`,
`0xFFD0`, `0xFFD1` and `0xFFE0`-`0xFFE2` — inside the width of an SFR byte, which
is what made them worth an issue. The census counted them because Ghidra wrote
`DAT_EXTMEM_ff80` in `ec/decompiled/pd/A8AE.c`, and a decompiler's spelling is
not an address-space fact. **They are XDATA, and two independent arguments
settle it (issue #181).**

**The structural half needs no decompile at all.** No 8051 direct-addressing
opcode takes a 16-bit operand. `MOV direct, ...` is `0x74`-`0x7F` / `0x84`-`0x87`
/ `0xA5`-`0xA7` with an 8-bit `direct` byte, `MOV A,direct` is `0xE5`, `MOV
direct,A` is `0xF5`, and the bit forms are `0xC2`/`0xD2`/`0x20`/`0x22`/`0x40`/
`0x60`/`0xA0` with an 8-bit `bit` byte. `disasm8051.py`'s `OPCODE_LEN` table —
the one its own `--self-test` pins — has every one of those at 2 or 3 bytes with
the address in a single byte, and the *only* opcode whose operand is a full
16-bit immediate is `0x90`, `MOV DPTR,#imm16`. So `0xFF80` cannot be a direct
address whatever anything spelled it as. `0x00AF` *is* a legal bit address,
which is a different claim and is where the one genuine error in this area was:
`c2 af` and `d2 af` are `CLR bit` and `SETB bit`, and the bit they name is
`IE.7`, the global interrupt enable — not `PSW.EA`, which is in `IE`'s
neighbour `PSW` at SFR `0xD0`. `disasm8051.py` and `r2 -a 8051` both print
`clr ie.7` and `setb ie.7` for the pair, and the repository's own `pd,0xEBBB`
row already described `0xAF` that way.

**The positive half is what the bytes actually do.** Each of the ten is loaded
by `mov DPTR,#imm16` and dereferenced by `movx` (`0xE0`/`0xF0`), and `movx` is
the instruction that names the external space — there is no `movx` form for the
direct or SFR space:

(r2's trailing `; [0x2000…]` memory-hint column is stripped from the listings
here for width, the same convention `pd-xdata-overlap.md` §1 states; that
file's §5.3.1 keeps the column and says what it is and is not.)

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa8ae; pd 3' /tmp/pd.bin
            0x0000a8ae      c2af           clr ie.7
            0x0000a8b0      90ff80         mov dptr, #0xff80
            0x0000a8b3      e0             movx a, @dptr
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa9be; pd 2' /tmp/pd.bin
            0x0000a9be      d2af           setb ie.7
            0x0000a9c0      22             ret
```

**The rule, and the case that needs the disassembly rather than the image.**
`mov DPTR,#imm16` seeds the pointer, `inc DPTR` (`0xA3`) walks it one byte on,
and `movx` dereferences it. Twenty of the PD image's **23** census addresses at
or above `0xF000` are a literal `mov DPTR` operand; the other three — `0xFFC1`,
`0xFFD1` and `0xFFDB` — are reached **only** by an `inc DPTR` from the address
below:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xc6a9; pd 6' /tmp/pd.bin
            0x0000c6a9      90ffc0         mov dptr, #0xffc0
            0x0000c6ac      e0             movx a, @dptr
            0x0000c6ad      fe             mov r6, a
            0x0000c6ae      a3             inc dptr
            0x0000c6af      e0             movx a, @dptr
            0x0000c6b0      fd             mov r5, a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xf2fb; pd 5' /tmp/pd.bin
            0x0000f2fb      90ffda         mov dptr, #0xffda
            0x0000f2fe      7410           mov a, #0x10
            0x0000f300      f0             movx @dptr, a
            0x0000f301      a3             inc dptr
            0x0000f302      f0             movx @dptr, a
```

**A `90 hi lo` byte scan therefore finds 20 of the 23 and cannot find those
three at all**, which is why the discrimination in `--self-test` reads the
committed `ec/decompiled/pd/*.asm` rather than the image. `0xFFDB` is the
detail worth keeping: it is not one of the issue's ten (it sits in another
cluster), so reading the issue's list alone would have made the count
twenty-one and the gap invisible. `--self-test` pins all three by name, and
pins the 23 address for address so a future export cannot add or drop one
without a failing check.

**What this does not settle, and is not claimed to.** The encoding says the
address is *external* memory. It does not say whether that memory is RAM or a
memory-mapped peripheral window, and nothing in a `movx` distinguishes the two.
`pd-xdata-overlap.md` §6 and §7 are where that limit and the live test for it
live; the census's answer here is the narrower one, and it is the one its
correctness depended on.

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
  126 functions between them, and eleven of those touch all 43" — and that is
  evidence about *shape*, not about *meaning*. The figures are `main-ec-003`'s,
  so they are checkable against `xdata-clusters.csv`; the point is not that they
  are true of anything but the code's shape. §5's function names are the
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
- **A `DAT_EXTMEM_` token is a decompiler decision, not an address-space fact,
  and "XDATA" is not "register".** The census reads the spelling, so every
  address in both CSVs rests on Ghidra having typed the right space — true as
  far as anyone has checked, and settled by encoding for exactly one region
  (§5.1, the PD image's `0xF000`-`0xFFFF` run), and unchecked for the rest.
  Three further limits ride on the same distinction, and all three are
  separate claims from the one the census makes:
  - **XDATA is a space, not a meaning.** An address being in the external
    address space says the firmware reaches it with `movx`. It does not say the
    byte is storage, does not say it is a register rather than a memory-mapped
    peripheral window, and does not say what writes it. `pd-001`'s ten `0xFFxx`
    addresses are in the space; whether the space is RAM is `pd-xdata-overlap.md`
    §6 and §7, not this file.
  - **`MOV DPTR,#imm16` also builds CODE pointers**, so the opcode alone was
    never going to be enough. What settles it is the `movx` that dereferences
    the pointer — and `../../docs/findings.md` §3b records the case where 68 of
    254 `0x07D0` sites needed a decode window to tell the two apart.
  - **Three of the PD image's 23 census addresses at or above `0xF000` are not
    `mov DPTR` operands at all** (§5.1), so a `90 hi lo` byte scan — the method
    `register_ref_table.py` uses — undercounts this region by three however
    carefully it is run. The two methods disagree on most rows for a reason
    that is not an error, and this is one of the reasons.
- **The two programs' maps are separate in the census's bookkeeping, not
  proven separate in hardware.** That is `pd-xdata-overlap.md` §6's boundary
  and nothing here moves it. What this file does is make the split mechanical
  instead of remembered. The one `90 hi lo` hit in the main EC's `common` area
  is *not* a shared object with the PD image and must not be read as one: it is
  a byte pair inside a 26-group run at file `0x690A` whose 16-bit big-endian
  values step by six through `0xFF00`-`0xFFFF`, which is a data table and not a
  decoded instruction. No decompiled main-EC function covers that range
  (`0x6817` and `0x6A02` bracket it), which is why the census shows no main-EC
  address at or above `0xF000` at all. What reads that table, and whether its
  values are XDATA addresses or code offsets, is **not established here** and
  is not claimed.
- **The `callees` column over-counts depth.** A name in a call position
  anywhere in a function's body counts as its callee, so a callee of a callee
  is credited to the outer function. It is a name-frequency column for picking
  a place to start reading, not a call graph.
- **`address-taken` is a one-character test, and `&&` satisfies it.**
  `classify()` asks only whether the text before the token ends in `&`, and
  tests that *before* it reaches the store rule, so the second `&` of a boolean
  `&&` files a plain comparison under `address-taken` instead of `read`. There
  is exactly one such site in the committed tree — `bank0/A747.c:24`,
  `DAT_EXTMEM_076a` — so §4.1's 271 is 270 genuine `&DAT_EXTMEM_xxxx` and one
  comparison. No total is restated here, because none was recomputed for it and
  the census the CSVs publish is the tool's own buckets either way; the fix is
  `left.endswith("&") and not left.endswith("&&")`, which would move one
  reference from `address-taken` to `read` and change no other bucket. The
  ordering is pre-existing — `git show main:ec/tools/xdata_register_map.py`
  has the same three-branch `classify()` — so §4.3 neither caused nor fixed
  it, and it is not a regression from this work. Found by review of #206; §8
  carries it as follow-up work.

## 7. Reconciling against the other method: one non-gap, and twelve rows the tree says zero on

`../tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800` runs
both methods over all 101 `registers.yaml` addresses: this one over the
decompiled C, `register_ref_table.py` over an unaligned `90 hi lo` byte scan
of the committed image with an 8-instruction window decoded at each site. They
are independent, and they do not count the same thing.

```console
$ python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800 2>&1 >/dev/null
101 addresses: 36 agree on the main-EC count, 12 have main-EC sites the decompiled tree does not contain, 53 differ another way. A zero in the 'this tool' column is 'not found by this method' -- a function that did not decompile carries its references nowhere -- never 'absent'.
```

**The §4.3 correction does not move this table, and the count changing from 56
addresses to 101 is not it either.** `--reconcile` prints reference counts, and
the correction changed which *direction* a reference is, not how many there
are; running the mode with the pre-fix `store_target()` gives a per-address
table byte-identical to the one above. The growth is a second, independent
staleness: `registers.yaml` gained 45 addresses — mostly the `0x0400`-`0x045F`
fan-probe page from issue #160 — and this section was never re-run.

That staleness is visible in the summary line and in the heading, so it is
worth stating plainly: the "2 have main-EC sites the decompiled tree does not
contain" this section used to quote is now 12, and ten of the new ones are
`0x0402`, `0x0404`, `0x0408`, `0x040A`, `0x040C`, `0x040E`, `0x0410`, `0x0420`,
`0x043A` and `0x0457` — the fan-probe page. This is the census's known lower
bound, not ten new gaps in the decompile, and the independent record already
says why: `xdata-0400-045f.md` §5 lists `0x0404` and `0x0457` among **"the 23
sites in no exported function"**, and its per-address site table shows
`0x0402`'s three EC sites all classified `ho` — handoffs, which the decompiled
C may not spell at all. "Not found by this method" is the whole claim.

Most of the 53 differ because the units differ (§6). The rows worth naming are
a non-gap that reads exactly like one, the twelve the tree says zero on, and
within those the two this file has always named:

- **`0x07A6`** (`OEM_4`) and, with it,
  `0x07D8`/`0x07D9`/`0x07DA`, are the addresses a `DAT_EXTMEM_`-only reading
  would call blind spots. None of them is one. `0x07A6` has 7 byte sites and
  15 C-level references, all under the symbol; the three `0x07D8` family come
  out agreeing *exactly* — 1 main-EC site each — with the added wrinkle that
  the PD image spells them `DAT_EXTMEM_07d8` and friends because it is not
  named at all. Nothing was missing from the firmware; the grep could not see
  the names. That is why the self-test pins these three as agreeing rather
  than leaving them as a caution.
- **Twelve rows are genuine gaps, and only two of them are the ones this file
  named when it had 56 addresses to reconcile.** The other ten are
  `0x0402`, `0x0404`, `0x0408`, `0x040A`, `0x040C`, `0x040E`, `0x0410`,
  `0x0420`, `0x043A` and `0x0457` — all inside `0x0400`-`0x0457`, all named in
  `registers.yaml` after this census was last generated, all with main-EC byte
  sites and no reference the decompiled tree can show. Seven of the ten also
  have PD-image sites. **Nothing here says why**, and the two possibilities are
  very different: a function that did not decompile (the census's standing
  lower bound) or a spelling the census does not read, the `0x0733` case
  below being the worked example. Reconciling them is its own issue; the
  numbers are recorded here so the next reader does not have to re-derive that
  they exist.
- **`0x0733`** and **`0x0735`** (both `MODE_PL_DEFAULTS`, the
  `0x0730`-`0x0737` block's one register name) are
  the two gaps this file has always named, and they fail in
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
- The top ten addresses by reference count get folded into the `main-ec-003`
  issue rather than opened separately: nine of the ten are in that cluster
  already, and the tenth is the `0x0440` singleton, so the cluster reading and
  the address reading should not be two efforts over the same code. Note that
  the cluster ids moved when §4.3 landed, so any follow-up issue opened against
  an id from the first version of this table is pointing at a different cluster
  — re-read `xdata-clusters.csv` before scoping one.
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
- **`classify()`'s `&` test should learn to tell `&&` from address-of.** It
  files a boolean `&&` under `address-taken`, which is the one occurrence at
  `bank0/A747.c:24` that §4.3's 838 could not correct (§6's bullet, and the
  correction block above). The fix is one clause — `left.endswith("&") and not
  left.endswith("&&")` — and it moves one reference from `address-taken` to
  `read` (271/8,319 → 270/8,320) and touches no other bucket, so it is a
  re-run and a diff of two numbers rather than a re-derivation. It belongs in
  its own issue: the ordering is pre-existing on `main`, it is not a regression
  from #206, and folding it in here would put an unrelated classifier change
  inside a correction about `==`.
