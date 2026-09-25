# The XDATA register map: 1,326 addresses / 15,696 references, attributed and clustered

> **Census update, 2026-09-25 (issue #279).** The figures in this file's body
> say 1,171 addresses / 14,819 references; the committed tree is now
> **1,326 / 15,696** (main EC 1,218 / 14,838, PD 108 / 603, 439 clusters),
> which is what the H1 above, §2's table, §3's table and §4.1's table now
> carry. §4.7 is the new pass and is the whole of the movement: the seeded
> 16-bit XDATA **pair accessors** at `bank1:0x8886`/`0x888C`/`0x8892`/`0x8898`/
> `0x889E`/`0x9193` take the address as a *first argument*, so `0x0402` arrives
> in the decompiled C as `FUN_CODE_0402` and as a bare `0x434`, and
> `occurrence_re` matches neither — 437 call sites, two adjacent bytes each,
> +155 distinct addresses and +874 references. No `.asm` and no `registers.yaml`
> row changed; `check_register_counts.py` still reproduces every `static_refs*`
> unchanged, which is the proof that the two counts are two methods rather than
> one number in two places.
>
> **Three numbers now describe the same byte and must be kept apart.**
> `registers.yaml`'s `static_refs_main_ec: 3` for `0x0402` is a `MOV DPTR`
> byte-scan of the image; 3 is also the number of `mov DPTR,#0x0402` +
> `lcall <accessor>` encodings in bank1; and the census now reads **10**, because
> Ghidra emitted one block into five overlapping `.c` files. The census is
> per-`.c`-file in its counting and has always been a lower bound on the machine
> code — a lower bound whose *inflation* here is the decompiler's, not this
> pass's. §4.7 works that through.
>
> **What a resolved site is, in one sentence: the EC reads or writes this byte
> in static code.** It is not evidence the EC *acts* on the byte, no `status:`
> moved, and the `DAT_CODE_`/`FUN_CODE_` spelling is not evidence the address
> is CODE — the discriminator is the callee's own committed `.asm`, where
> `movx` names the external space. `0x0733`, a real code pointer, is not passed
> to an accessor and stays excluded; that is asserted in the self-test after the
> pass has run, not before it.
>
> The superseded 1,171 / 14,819 figures are kept below rather than deleted, as
> every superseded figure in this file is, each beside the correction that
> replaces it.

> **Census update, 2026-09-24 (merge of issue #133, PR #238; settled by issue
> #259).** The figures below say 1,172 addresses / 14,801 references; the
> committed tree is now **1,171 / 14,792** (main EC 1,062 / 13,931, PD
> references 864 -> 861), and the self-test transcript further down is the
> current one. Nothing in the firmware or the `.asm` changed. Applying
> `ghidra-variables.csv` fixes some functions' signatures in Ghidra, and at
> bank1 `0x9EA1` that dropped an argument at the call site: `bank1/E100.c` no
> longer passes `DAT_EXTMEM_0390`, which was this census's only reference to
> `0x0390`. Nine C-level references moved: `0x0390` -1 (and so leaves the
> census), `0x0391` -1, `0x04AB` -3, `0x07D8` -3, `0x08AD` -1, and in the PD
> image `0x07D0` -1, `0x07C9` +1.
>
> **None of the nine is a reference genuinely gone from the machine code**, and
> **§7.1 accounts for all seven addresses** — with one exception worth reading
> before anything else here: `0x0390` still has its `mov DPTR,#0x390` site at
> `bank1/E100.asm:70`, is read at `9EA1.asm:19` and written at `9EA1.asm:43`,
> and a `0x0390` row with no census reference to go with it is what a present
> byte whose *spelling* fell out of one method looks like. The census is a
> lower bound on the machine code; a zero in it is "not found by this method",
> never absent.
>
> What the nine settled, for the next annotation author: a variable row **may**
> change a caller's arity, and that is a correction rather than a loss — the
> committed four-argument signature is the one that matches the listing. A pin
> moves only with a measured reason recorded in the same change. Issue #259
> took that measurement and the pins did not move: naming the byte changed no
> exported `.c` and no `manifest.csv` row. The rule is carried in
> `ghidra/scripts/ApplyAnnotations.java`, `ec/annotations/README.md` and
> `../../docs/findings.md` §18.
>
> **Correction, 2026-09-25 (issue #557).** The committed tree is not
> **1,171 / 14,792**: nothing in the committed CSVs, in the tool, or in
> `xdata-06c2-06db-timers.md` §6a sums to 14,792, and **14,792 / 13,931 / 861
> above are kept as the superseded version rather than deleted.** That trio
> **was** a real, checkable measurement — the census as pinned at the #238
> merge (`1fcd5f1e`, `xdata_register_map.py`'s `ORACLE`) — and it was
> *superseded by later drift*, not invented: by issue #263's own measurement
> that pin sat 26 references behind a pristine `main` (14,818), and #263's
> `+1` brought the committed tree to 14,819. So the claim here is "not the
> current figure", which is checkable; it is not "never was a tree". The
> current figures are **1,171 addresses / 14,819 references** — main EC 1,062 /
> 13,961, PD 157 / 858, 430 clusters — which is what the H1 above, §2's table,
> §3's table and §4.1's table now carry. The 1,171 is unchanged from the line
> above; the other three are not. The
> self-test transcript further down is **not** the current one either, and did
> not become so when this correction landed: it is issue #263's parent tree,
> and §7.2 is what moved the pins. Re-derive, do not remember:
> `../../docs/findings/xdata-census-totals.md` carries the three commands and
> this file's every superseded figure.
>
> **The rule, for every number in this file.** A figure measured from the
> committed `xdata-registers.csv` / `xdata-clusters.csv` is the current one; any
> other figure here is historical and sits beside a correction naming the tree
> it was measured against. Re-measure rather than pin — census-dedup
> (#254/#256/#326) and the pair-accessor pass (#279) move these — and re-measure
> the *table body*, not just its total row, because a total its own rows do not
> sum to is a worse error than a stale one. What this rule is about is agreement
> between the committed CSVs and this page; it is not a claim that the census
> lists every address the firmware touches. It does not — the note above is why,
> and a zero in it is "not found by this method", never absent.

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
  `DAT_EXTMEM_` misses 147 main-EC addresses. `build_ec_decompile.py` applies
  `ec/ghidra/xdata-symbols.csv` before exporting, so the registers the symbol
  table can name come out as `CPU_TEMP` and
  `MODE_TCC_OFFSET_DEFAULTS_GAMING_0`, never as `DAT_EXTMEM_043e`. Reading both
  spellings gives **1,062** main-EC addresses in **13,961** references, of
  which **147 carry a name** and 915 do not. The main EC's named count is not
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
  writer**" all along. *(The 1,172 / 14,801 is the tree §4.3 ran on, and the
  correction at the top of this file names the committed one. §4.3's claim is
  about buckets rather than totals, and it holds on the committed tree too:
  `--no-eq-guard` moves no address's `refs` there either.)*
* **A third spelling is not a spelling: 155 addresses are reached only as an
  argument** to one of the seeded 16-bit pair accessors, which the issue calls
  out by name and §4.7 resolves. `0x0402` is `FUN_CODE_0402` at ten bank1 call
  sites and a bare `0x404`/`0x434`/`0x0834` at many more, and `occurrence_re`
  matched none of them. This is a correction to the census's *coverage*, in the
  same family as the `symbol` correction above and for the same reason: the
  exporter wrote the address somewhere this tool's regex could not reach.

The deliverable is `xdata-registers.csv` (one row per touched address) and
`xdata-clusters.csv` (one row per cluster), both regenerable by
`../tools/xdata_register_map.py` and both checked by its `--check`. The
clustering is the worklist; §5 is it, ranked. **It gives no register a purpose
and names nothing** — §6 says why, and the reading of a cluster is the
follow-up issue's job, not this file's.

## 1. Reproducing it

The issue's evidence, re-run unchanged, and the tool beside it:

```console
$ python3 ec/tools/xdata_register_map.py --check
/home/runner/.../ec/annotations/xdata-registers.csv: 1326 rows match a fresh generation from the committed tree at threshold 0.5
/home/runner/.../ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
```

The two lines above are the current ones. **Everything below them is the
transcript this section was written with**, kept whole and with its own dated
corrections, because the issue's evidence is the point of the section and
rewriting it would destroy the comparison. The pair-accessor pass of §4.7 is
what moved the last three figures in it; re-derive rather than remember:

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

*(Correction, 2026-09-24. The two `--check` lines above are what that command
printed when this transcript was written; **it no longer does.** Re-run on the
merged tree it exits 1 and reports `differs from a fresh generation` for both
CSVs: `1172 on disk vs 1172 generated` for `xdata-registers.csv`, `428 on disk
vs 431 generated` for `xdata-clusters.csv`. Those two counts are the whole of
what the command prints — `diff()` names the first differing line and stops, so
it reports no total of differing lines and none is attributed to it here. How
much of each file actually differs, counted instead by generating to scratch
with `--out-registers`/`--out-clusters` and diffing: 857 of the 1,172 register
lines, 374 of the 428 cluster lines. **Every count in this parenthetical is the
2026-09-24 merge tree it was measured on and none of them is the current one**,
including the `1,172`/`428` in it: `--check`'s mismatch line counts the header
on both sides, so the `428 on disk vs 431 generated` here is 427 clusters on
disk against 430 generated, while the `1172 rows match` line in the transcript
above counts data rows and is that tree's own 1,172. The
second-pass correction immediately below is the one that supersedes this
paragraph, and the correction at the top of this file carries the figures from
there to the committed CSVs. This is pre-existing rather than this
change's doing: the identical failure is on `origin/main`, and `--self-test`
fails 9 assertions on both, the `ok the committed CSVs match a fresh generation`
line in the transcript below among them. (Nine, not ten: the run's tenth line
reading `FAIL` is the `FAILURES ABOVE` summary, not an assertion.) The cause is
#310's `bank0/CC64` (`init_06e6_1_clear_0743_07c5_and_07d5_ff`), whose
annotation adds an address the committed census still had to itself in a
one-address cluster at 1/4: a fresh generation moves it into the largest
main-EC cluster at 109/1,149 against the committed 108/1,136, and the ids of
the clusters it displaces move with it. **§5's four corrected rows are held to
the committed CSV**, which is the authority this file's own rule makes them,
and not to a fresh generation that would move the top row again. Re-deriving
the census to close the gap belongs to #254/#256/#326, and #326 already records
the census as a lower bound for the same reason: it is what the committed tree
spells, not a claim about every address the firmware touches.)*

*(Correction, 2026-09-24, second pass — the census has since been re-derived, so
the correction above no longer describes the tree.) The generated CSVs are
regenerated from the committed tree and committed, which is what closes the
`--check` gap it recorded. Re-run on this tree:

```console
$ python3 ec/tools/xdata_register_map.py
wrote /home/runner/.../ec/annotations/xdata-registers.csv: 1171 rows
wrote /home/runner/.../ec/annotations/xdata-clusters.csv: 430 rows
  main-ec: 1062 distinct addresses, 13957 references, 380 clusters at threshold 0.5
  pd: 157 distinct addresses, 861 references, 50 clusters at threshold 0.5
$ python3 ec/tools/xdata_register_map.py --check
/home/runner/.../ec/annotations/xdata-registers.csv: 1171 rows match a fresh generation from the committed tree at threshold 0.5
/home/runner/.../ec/annotations/xdata-clusters.csv: 430 rows match a fresh generation from the committed tree at threshold 0.5
```

So `--check` now exits 0, where it exited 1 on both sides of this merge, and
`--self-test` fails **8** assertions rather than the 9 above — the same eight,
minus the `ok the committed CSVs match a fresh generation` line, which is the one
the regeneration fixes. The other eight are not re-pinned here: they are the
pre-existing failures the note above declines to re-derive, so fixing them is
#254/#256/#326's work and not this merge's. Seven of the eight measure the same
on `origin/main` and on the branch. The eighth is the §4.1 bucket totals, and
there the honest statement is narrower than "untouched": its pin reads 8,317
`read` and was already 8,328 on `origin/main` — 11 adrift before this merge —
and the naming this merge did moves it five cells further, to 8,333, with
`passed-to-call` 543 → 538. §8 records what those five cells are and why. The pin
is left at 8,317 because this merge's five cells ride on top of a gap it did not
open, and re-pinning to 8,333 would close that gap by accident and call the
result a measured pin. §5 is re-transcribed
from the 430-row census below, and the cluster ids that moved with it are
corrected in `docs/findings.md` §17, `xdata-06c2-06db-timers.md`,
`xdata-086x-dispatch.md` and `manual-fan-ctrl-0751.md`. The census is 1,171
addresses in 14,818 references — the 1,172/14,801 the paragraph below quotes is
that paragraph's own historical figure, and the 14,801 is not the current
total.)*

*(Correction, 2026-09-25, issue #557: the `--self-test` count in that block has
moved again, and the current one is smaller than "8" rather than the 9 above
it. On the committed tree `--self-test` fails **one** assertion — "the
annotation CSV and index.csv agree on every address they share", the
`FUN_CODE_*` naming drift in `index.csv` that issue #256's §8 bullet records —
and every counting assertion holds, `named_in_tree` (162 against 162), the five
§4.1 bucket totals, the full-census oracle and the `ORACLE_TOP_MAIN` pair among
them. `--check` still exits 0. The block above is left as the 2026-09-24 run it
records, which is what the correction at the top of this file asks for; the one
number a reader needs today is in §8's `xdata_register_map.py` bullet.)*

The census is the same 1,172 addresses in the same 14,801 references as before
— §4.3 changed which *direction* each reference is, and not one address or
reference moved. The cluster count did, because the writer axis is built on
direction. *(Correction, 2026-09-25, issue #557. 1,172 / 14,801 is the tree
§4.3 ran on; the committed census is 1,171 / 14,819, and the correction at the
top of this file names it. The claim this paragraph actually makes still holds
on the committed tree and is worth the re-derivation: `--no-eq-guard` against
today's CSVs changes the `refs` of **0 of 1,171** addresses, so §4.3 moved
direction then and moves it now.)*

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
re-exported. *(Correction, 2026-09-25, issue #557. "Are all unchanged, and all
still pinned" was true of #181's branch, the one the paragraph's own opening
line names, and is no longer true of the committed tree: the census is
1,171 / 14,819, main EC 1,062, and §2's `spelled_as` table has been
re-transcribed from the committed CSV — 147 symbol-spelled main-EC addresses
against the 41 above, because `.c` files *have* been re-exported since, by
#194 and #179/#180/#183. The 109 PD-only, 48 both and the top two addresses
are unchanged and still pinned. The wrong version is kept above rather than
deleted.)*

The self-test is the oracle, and it pins the issue's numbers *and* the
corrections, so a change to what counts as a reference fails loudly instead of
making this file quietly wrong. The three `classify(...)` lines per shape and
the two direction oracles are §4.3's; everything above and below them is the
census, and the census did not move.

```console
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
  ok    the issue's 8741 file-wide DAT_EXTMEM_ occurrences and the 9 of them that are this repository's own annotation text quoting the decompile are still where they were (raw: {'DAT_EXTMEM': 8741, 'symbol': 6179})
  ok    oracle: DAT_EXTMEM_ only, what issue #132 counted -- main EC 916 distinct / 7871 refs, PD 157/861, which is 1036 distinct addresses in all after the 37 both spell there (got (916, 7871) and (157, 861), 1036 distinct / 8732 refs in all)
  ok    oracle: the 146 main-EC addresses the decompiler named, 6060 references, and 0/0 of them in the PD image (got (146, 6060) and (0, 0))
  ok    within each program the two spellings are disjoint address for address, so a named address is never also a DAT_EXTMEM_ token
  ok    the PD image is spelled entirely in DAT_EXTMEM_ tokens, which is gen_xdata_symbols.py's own refusal to name it
  ok    oracle: the full census, both spellings -- 1171 distinct / 14792 references, main EC 1062/13931 (got 1171/14792, (1062, 13931))
  ok    oracle: 109 PD-only, 48 touched by both (got 109 / 48)
  ok    main + PD equals the file-wide total on both axes
  ok    oracle: the top two main-EC addresses by reference count are 0x0440=181, 0x08A8=170 (got 0x0440=181, 0x08A8=170)
  ok    the 0x07D8 correction: its main-EC reference is spelled MODE_TCC_OFFSET_DEFAULTS_GAMING_0, and the PD image spells the same address DAT_EXTMEM_07d8 because it is not named there
  ok    of the 189 named addresses, 164 appear in the decompiled tree at all (got 164: 0x030E, 0x030F, 0x0400, 0x0401, 0x0403, 0x0432, 0x0434, 0x0435, 0x0436, 0x0437, 0x0438, 0x0439, 0x043C, 0x043D, 0x043E, 0x043F, 0x0440, 0x0442, 0x0443, 0x0448, 0x0449, 0x044B, 0x044C, 0x044F, 0x0450, 0x0451, 0x0452, 0x0454, 0x0455, 0x0456, 0x0458, 0x0459, 0x045A, 0x045B, 0x045C, 0x045D, 0x045E, 0x045F, 0x0460, 0x0468, 0x049F, 0x04A6, 0x04A7, 0x0522, 0x0523, 0x055F, 0x0621, 0x0635, 0x0636, 0x0637, 0x0638, 0x0639, 0x063A, 0x06C2, 0x06C3, 0x06C5, 0x06D1, 0x06D2, 0x06D6, 0x06D8, 0x06D9, 0x06DA, 0x06DB, 0x06F3, 0x0706, 0x070B, 0x070D, 0x0723, 0x0730, 0x0731, 0x0732, 0x0734, 0x0736, 0x0737, 0x0740, 0x0741, 0x0743, 0x0744, 0x0745, 0x0746, 0x074E, 0x0751, 0x075B, 0x075C, 0x0766, 0x0767, 0x0768, 0x0782, 0x0783, 0x0784, 0x0785, 0x0786, 0x078C, 0x07A6, 0x07A7, 0x07A8, 0x07A9, 0x07AA, 0x07C4, 0x07C6, 0x07CC, 0x07D0, 0x07D1, 0x07D3, 0x07D4, 0x07D5, 0x07D6, 0x07D7, 0x07D8, 0x07D9, 0x07DA, 0x07E2, 0x07F3, 0x07F6, 0x0809, 0x080C, 0x080D, 0x0811, 0x0843, 0x0844, 0x085B, 0x0860, 0x0862, 0x0865, 0x0866, 0x0867, 0x0868, 0x0869, 0x086A, 0x086B, 0x086D, 0x086E, 0x0890, 0x089E, 0x089F, 0x08A0, 0x08A2, 0x08A7, 0x08A8, 0x08E4, 0x08EB, 0x0981, 0x0982, 0x0985, 0x0986, 0x09CE, 0x09E6, 0x09E7, 0x09EA, 0x09EB, 0x1664, 0x1C01, 0x1C02, 0x1C03, 0x1C12, 0x1C13, 0x1C14, 0x1C36, 0x1C37, 0x1C38, 0x1C39, 0x1C3A, 0x1F01, 0x1F07)
  ok    every address the tree spells by symbol is in the generated symbol table, so the name column can never be empty for one
  ok    the two blind-spot addresses are 0x0733, 0x0735; of them the one that is spelled at all is 0x0733, behind a CODE pointer (got 0x0733), and 0x0735 is not findable by any spelling
  ok    issue #181: all 10 of pd-001's 0xFFxx addresses are carried by a `mov DPTR,#imm16` in the committed .asm, each to a `movx` -- and no 8051 direct-addressing opcode takes a 16-bit operand, so none of them can be a direct address whatever the decompiler spelled it (not found by this method: none)
  ok    and each is reached by the form the annotation records -- a `mov DPTR,#imm16` for 8 of them, a `mov DPTR` one byte below plus `inc DPTR` for 0xFFC1, 0xFFD1 (got a different form for: none)
  ok    and no other instruction in the PD tree names one of the ten -- a direct address and a bit address are both one byte wide, so there is no form in which a 0xFFxx value could be either (found: none)
  ok    oracle: the PD census holds 23 addresses at or above 0xF000, the same address for address (got 23: 0xFF40, 0xFF42, 0xFF4A, 0xFF62, 0xFF80, 0xFF84, 0xFF88, 0xFFC0, 0xFFC1, 0xFFC2, 0xFFC6, 0xFFD0, 0xFFD1, 0xFFD3, 0xFFD4, 0xFFD5, 0xFFD8, 0xFFDA, 0xFFDB, 0xFFDF, 0xFFE0, 0xFFE1, 0xFFE2)
  ok    every one of those 23 is backed by an encoding in the .asm, so the region is XDATA by opcode and not only by the decompiler's spelling (not found by this method: none)
  ok    exactly 3 of them -- 0xFFC1, 0xFFD1, 0xFFDB -- are reached by `inc DPTR` from the address below and never by a `mov DPTR` of their own, which is why a `90 hi lo` byte scan finds 20 of the 23 and misses these 3 (got 0xFFC1, 0xFFD1, 0xFFDB)
  ok    and no main-EC census address reaches 0xF000 either, the main EC's highest being 0x9000 (got 0 at or above 0xF000 and a ceiling of 0x9000), so the 0xF000-0xFFFF run is the PD image's own in the census -- which is a claim about a census, and a census is a lower bound
  ok    issue #259: 0x0390 is carried by a `mov DPTR,#imm16` in the committed bank1 .asm, reached at bank1/E100.asm:E176 -- an .asm is never rewritten by an annotation, so the byte has a site in the machine code whatever the C spells
  ok    and it still has no row in the census, because the callee at bank1 0x9EA1 renders the address as CONCAT11(r4_value,r3_value) over register names and the call site passes only the constants 0x90 and 3, which this token pattern cannot reach (census row present: False)
  ok    the hand-checked direction oracle: 5 addresses, 0x0440, 0x0443, 0x04FE, 0x04FF, 0x0860, each read off the decompiled C by hand rather than by this tool
  ok    the §4.1 bucket totals, read 8317 write 3186 read+write 2476 passed-to-call 543 address-taken 270 (got read 8317 write 3186 read+write 2476 passed-to-call 543 address-taken 270)
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
  427 clusters at threshold 0.5; 1062 main-EC and 157 PD addresses
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
`xdata-registers.csv` have an address in `ec/ghidra/xdata-symbols.csv`. *(Both
figures in that last sentence were 2026-09-24's, and the merge note below
corrects the 79 to 88. Re-derived from the committed CSV it is **162 of
1,171**, and re-derived from a *fresh generation* over the same tree it is
**162 of 1,171** as well: the two agree on this column today, where on #557's
own branch they did not (the committed CSV read 153 against a fresh 162, and
`ORACLE['named_in_tree']` held the CSV's 153 rather than corroborating it, so
the self-test measured 162 against the pin). That gap is closed, not papered
over: issue #256's regeneration rewrote both CSVs from the committed tree, which
filled the `name` column and carried `ORACLE['named_in_tree']` to 162 with it,
and `--self-test` now measures 162 against that pin and passes. The 101 above
is the symbol table's size on that older tree, and it holds 187 on this one —
187 rows and 187 distinct `addr`/`name` pairs, so the count is the same under
either reading.)*

**The `of the N named addresses, M` line moved again on 2026-09-25 (issue
#264), and is re-transcribed above rather than left as the run it was.** It
now reads **189 named / 164 in the tree**, and `ORACLE['named_in_tree']` went
162 -> 164 with it, so `--self-test` measures 164 against the pin and passes.
Cause: `XDATA_09EA` and `XDATA_09EB` in `registers.yaml`, both reached by a
decompiled function. The 189 is the symbol table's size on this tree (187 + the
two new rows), and the in-tree half moved by 2, not by a re-clustering — the
full census below it is unmoved at 1,171 distinct. The same two renames are
what moved the `DAT_EXTMEM_`/symbol half of the ORACLE, and the cross-check
that says this is explained rather than mysterious is in
`ec/tools/xdata_register_map.py`'s own comment: -2/+2 distinct and -15/+15
references, and 15 is the census's 7+8 references to `0x09EA` and `0x09EB`.
The "162 of 1,171" figures in the paragraph above are left as they were
written, describing the tree of 2026-09-24.

**The transcript's own census figures are the pre-#263 tree too, and three of
them are the numbers a reader is most likely to quote.** It prints
`1171 distinct / 14792 references, main EC 1062/13931`, `427 clusters`, and a
§4.1 bucket total of `read 8317 write 3186 read+write 2476 passed-to-call 543
address-taken 270`. The committed tree reads **14,819 / main EC 13,961 / 430
clusters**, and §4.1's five cells are the ones the table further down now
carries. This is not a transcription slip in either direction: those were the
`ORACLE` and `BUCKET_TOTALS` values issue #263 re-pinned after finding them
already 26 references behind on `main`, and §7.2 is the record of that
measurement. The transcript is left as the run it was, because a rewritten
transcript is not a run anybody can check.

**That block did not pass when it was first written, and the two failures
were both staleness rather than method.** The committed `xdata-registers.csv`
had an empty `name` column for every row and the committed
`xdata-clusters.csv` an empty `named_addrs` column for all 25 clusters that
have named addresses (25 then; 162 rows of the census name one now, 145
`main-ec`, 11 `both` and 6 `pd`, spread over 56 clusters), while the tool fills
both and its own self-test
asserts `name` is populated exactly for the addresses the symbol table names.
So `--check` and `--self-test` both failed on the tree this file describes —
nothing in `.github/scripts/agent-gates.sh` runs either mode, which is why it
went unnoticed. `ORACLE['named_in_tree']` had the same problem: it read 44
from when the 0x0400-0x045F page entries were added to `registers.yaml`
without the constant being re-derived, against 79 in the tree. Both are
corrected here, and §5's "named inside" column is a reading of the corrected
CSV. That work was also said to move four of §5's rows — `main-ec-001` 20 to
28, `main-ec-003` and `main-ec-007` from `none`, and `main-ec-012` from
`none` to 6 — and it did not: the table kept reading `none` for three of
them, and `main-ec-001` at 29 rather than the 28 named here. **Issue #272
settled that against the census**, which reads `main-ec-001` 33,
`main-ec-002` 19, `main-ec-003` 43 (every member of the cluster), and
`main-ec-004` at the census's 26/278 rather than the 30/312 the row carried.
The `6` was never `main-ec-012`'s: the census names no address in
`main-ec-012`, and 6 is `main-ec-011`'s, the row above, which does read 6.
**Those ids are the #256 census's and are left as they were written**, per
`../../docs/findings.md` §4a — same rule as §5's drift record below. Two of the
rows they name are not rows of the committed census at all: it carries no
26-address cluster (that membership is inside `main-ec-001`) and no cluster with
19 named addresses, so there is nothing to re-derive those two *to*.
The count in the CSV rather than the hand-typed one in this table is the
authority, and `tools/check_cluster_citations.py` now holds the table to it.

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
below, `main-ec-002`'s "named inside" is 33 for the same reason — 29 was the
figure in the table this note was written against, and issue #272 settled the
row at the census's 33.)*

## 2. The two token spellings, a third value that is not a spelling, and what the issue's "six" actually counted

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
under a `DAT_EXTMEM_043e`. The same holds for the other 146 named main-EC
addresses. The split, from `xdata-registers.csv`:

| `program` | `spelled_as` | distinct | references |
|---|---|---:|---:|
| main-ec | `DAT_EXTMEM` | 822 | 7,334 |
| main-ec | `DAT_EXTMEM+pair-literal` | 42 | 394 |
| main-ec | `pair-literal` | 155 | 461 |
| main-ec | `symbol` | 137 | 5,515 |
| main-ec | `symbol+pair-literal` | 13 | 187 |
| both | `DAT_EXTMEM` | 34 | 349 |
| both | `DAT_EXTMEM+pair-literal` | 4 | 139 |
| both | `symbol+DAT_EXTMEM` | 11 | 714 |
| pd | `DAT_EXTMEM` | 108 | 603 |
| **total** | | **1,326** | **15,696** |

**A `both` row's `spelled_as` is the union across the two programs, and cannot
be read per-program.** `build()` absorbs a `both` row's two per-program entries
into one, and the cell holds every spelling either image gives that address
number — which is a statement about two programs, not about one. The CSV
carries the per-program halves in a second column, `spellings_by_program`
(column 21, appended last so the positional `awk -F,` commands in
`../../docs/findings/xdata-census-totals.md` keep meaning what they mean), so
a per-program question is read from that. Its contract, the 15 `both` rows
whose halves differ, and the reconciliation below are
`../../docs/findings/xdata-spelled-as-union.md`. The four `both` rows this
matters for are the `DAT_EXTMEM+pair-literal` ones, and **only three of them
are mixed inside the main EC**:

| address | main-EC | main-EC refs | pd | pd refs | row `refs` |
|---|---|---:|---|---:|---:|
| `0x04A3` | `pair-literal` | 7 | `DAT_EXTMEM` | 1 | 8 |
| `0x0834` | `DAT_EXTMEM+pair-literal` | 48 (1 + 47) | `DAT_EXTMEM` | 18 | 66 |
| `0x0835` | `DAT_EXTMEM+pair-literal` | 48 (1 + 47) | `DAT_EXTMEM` | 4 | 52 |
| `0x0836` | `DAT_EXTMEM+pair-literal` | 9 (1 + 8) | `DAT_EXTMEM` | 4 | 13 |

**`pair-literal` is the one value in the `spelled_as` column this tool infers
rather than reads**, and it is not a spelling at all: it records that the
address is also reached as a literal *argument* to one of the pair accessors
§4.7 describes. That is why the mixed rows exist — 58 addresses carry it
alongside a token spelling **within a program** (59 counting the CSV's union
across both, which differs on `0x04A3` alone), and `symbol` and `DAT_EXTMEM`
are still never both on one row within a program, which is the invariant the
self-test asserts. The distinct column now sums to more than the count of
`symbol` rows because an address reached three ways is three rows of this table
and one row of the CSV; the `refs` column does not double-count, since each row
carries that address's whole reference count once — and on a `both` row that
count is still the sum over both programs, which `spellings_by_program` does
not split.

*(Correction, 2026-09-25, issue #557, re-transcribed against the tree #279
superseded. Every cell of the table above is read from the committed CSV. The
2026-09-25 version, kept here rather than deleted: main-ec `DAT_EXTMEM` 878 /
7,636, main-ec `symbol` 136 / 5,487, both `DAT_EXTMEM` 37 / 378, both
`symbol+DAT_EXTMEM` 11 / 714, pd `DAT_EXTMEM` 109 / 604, total 1,171 /
14,819. The wrong version before that one, kept in the same way: main-ec
`DAT_EXTMEM` 977 / 12,692, main-ec `symbol` 38 / 408, both `DAT_EXTMEM` 45 /
1,056, both `symbol+DAT_EXTMEM` 3 / 40, pd `DAT_EXTMEM` 109 / 605, total 1,172
/ 14,801. The first move is not #259's nine-reference correction — it is the
`symbol` rows growing when `.c` files were re-exported, which §1's merge note
and its #181-branch correction both record, and which the tool's own dated
comment above `ORACLE` walks through: #194 took the named main-EC addresses 41
to 82, #237 two more, #179/#180/#183's 62 timer/counter and dispatch entries
the rest of the way to 146, and the committed CSV carried 147. The second is
§4.7's pair-accessor pass and is additive on the `pair-literal` rows. The total
row is unchanged in kind — it is the whole census — and moves only with the
census.)*

Read the `symbol` rows as the addresses the issue's grep could not see. **On
§3's basis** — every row the main EC touches, which is the 1,218 the tool
prints rather than the 1,169 `program=main-ec` rows above, the 49 difference
being the `program=both` rows — that is **161 addresses in 6,416 references**.
The corrected form of the issue's claim is therefore a *three*-way split, not a
two-way one:

> 161 of the 1,218 XDATA addresses the main EC touches carry a name from
> `ec/ghidra/xdata-symbols.csv`. Of the other 1,057, **902** read as
> `DAT_EXTMEM_xxxx` and **155** are named nowhere and reach the census only as a
> literal argument to one of the pair accessors of §4.7.

*(Two superseded versions, both kept rather than deleted. The 2026-09-25 one,
against the tree #279 superseded: **147 addresses, 6,201 references**, and "147
of the 1,062 XDATA addresses the main EC touches carry a name … the other 915
read as `DAT_EXTMEM_xxxx`" — a two-way split, which is what that tree allowed
and no longer is. The version this section was written against: **41 addresses,
448 references**, and "41 of the 1,063 XDATA addresses the main EC touches carry
a name … the other 1,022 read as `DAT_EXTMEM_xxxx`", with "1,022 is unchanged —
the issue's main-EC distinct count is right, and its coverage of it was not".
Both corrections were right on their own trees and both are still the
correction §2 exists for; only the size of the gap has moved, and 1,022 is no
longer unchanged. The 161/902/155 above is a partition — 161 + 902 + 155 is
1,218 exactly, and the eleven `both` rows that carry both token spellings are
counted in the 161 and not again in the 902. **That partition is worked on the
union column, and `0x04A3` is the row where the distinction bites**: counted
within the main EC the last term is **156**, not 155, because the main EC
reaches `0x04A3` as a `pair-literal` and nothing else, and it is the PD image
that spells it `DAT_EXTMEM_xxxx` — so the union moves it into the 902 and
leaves 155 here. Both thirds are right, and the row's `spellings_by_program`
cell is where a reader of this paragraph goes for the split;
`../../docs/findings/xdata-spelled-as-union.md` has the whole reconciliation.)*
The gap is still the blocker the issue describes, and it is still why this
issue is on the critical path:
**74%** of the register file the main EC actually uses is still spelled
`DAT_EXTMEM_xxxx` rather than carrying a name, against 96% when this was
written. That is better and it is not good enough — the exporter catches up with
a symbol table that has been growing faster than the census is re-derived,
which is the thing to fix. §4.7 closes 155 more addresses and closes none of
this gap: it gives a *count* where there was none, and a count is not a name.

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
it. The eleven `symbol+DAT_EXTMEM` rows are where they come apart: `0x07D3` is
`GFID` in the `name` column and `DAT_EXTMEM_07d3` in the PD image's own source,
because `xdata-symbols.csv` carries `programs=bank0;bank1` and refuses to name
the PD program at all. Reading that row as the PD firmware calling it `GFID` is
`pd-xdata-overlap.md`'s mistake in a new place.

*(The three rows and the `0x07D0` example above are that tree's, and the wrong
version is kept rather than deleted. The eleven are `0x07D3`-`0x07D5`
(`GFID`/`CPUA`/`DBAP`), the `MODE_TCC_OFFSET_DEFAULTS_*` trio at
`0x07D8`-`0x07DA`, and `0x07F3`/`0x07F6`/`0x0809`/`0x080C`/`0x080D`. `0x07D0`
is no longer one of them at all: `registers.yaml` now derives that byte's name
as `DBD1`, and the generated `ec/ghidra/xdata-symbols.csv` (`:16`) carries
`BATTERY_CHARGE_LIMIT_DOWN` in its `from_register` column instead. The census
holds `0x07D0` as a `pd` row that is `DAT_EXTMEM`-spelled with no main-EC
side. The point the paragraph makes is unchanged and is better supported by the
eleven than by the three: a `name` in the CSV is not a statement about how the
committed `.c` spells the byte.)*

## 3. Two programs, and the split the clustering never crosses

`ec/decompiled/pd/` is the self-contained `ITE8850-PD` image at file `0x20000`
with its own address space and its own XDATA map (`../README.md`'s Layout
section; `pd-xdata-overlap.md` §5 is the standing argument for exactly
`0x04A6`). `../../docs/findings.md` §3a is what mixing the two cost last time,
so the split is the tool's first act and the similarity graph is built twice,
once per program.

| | distinct addresses | references |
|---|---:|---:|
| main EC (`common` + `bank0` + `bank1`) | 1,218 | 14,838 |
| PD image (`pd`) | 157 | 858 |
| PD-only, never touched by the main EC | 108 | |
| touched by both programs | 49 | |
| **all of it** | **1,326** | **15,696** |

34 of the 49 both-programs addresses are `DAT_EXTMEM_`-spelled in both; the
other eleven are named in the EC and written as `DAT_EXTMEM_` in the PD image
(§2's `symbol+DAT_EXTMEM` row), and four are `DAT_EXTMEM+pair-literal`. A
shared address *number* is not a shared byte, and the `program` column is on
every row so no downstream reader can lose that.

**The `both` count moved 48 -> 49 and the PD-only count 109 -> 108, and neither
is the pair pass touching the PD image.** Its own `read_be16_from_dptr` at
`pd:0x38D3` is selected by the same rule as the bank1 accessors and its single
caller passes no argument at all, so the PD half's 157 / 858 are untouched, and
so are the `program=pd` rows' own figures but for one address: 109 rows / 604
references become 108 / 603. The address that left them is **`0x04A3`**, a
`program=pd` row on `origin/main` — read at `pd/0xF22E`, in
`read_04a3_then_call_9a90` — which the pass newly reaches in six bank1
functions as the `inc DPTR` half of the `0x04A2`/`0x04A3` pair, so the number
0x04A3 now names a byte in both images. Diffing the `program` column of the
committed CSV against `origin/main` returns that one change and no other, which
is where the address comes from; the 155 addresses the pass adds are new
`program=main-ec` rows, of which `0x03DE` and `0x03B8` are two. A shared
address *number* is not a shared byte, which is exactly what the `program=both`
column exists to carry and why §3a is the standing argument against reading one
map into the other.

*(Correction, 2026-09-25, issue #557, against the tree issue #279 superseded.
The wrong version, kept here rather than deleted: main EC 1,063 / 13,937, PD
image 157 / 864, all of it 1,172 / 14,801, and "45 of the 48 both-programs
addresses are `DAT_EXTMEM_`-spelled in both; the other three
(`0x07D8`/`0x07D9`/`0x07DA`)". The main EC / PD / PD-only / both rows are the
tool's own split — what `xdata_register_map.py` prints, 1062 distinct addresses
and 13961 references for the main EC against 157 / 858 for the PD image — so the
two reference rows sum to the 14,819 total while the distinct column
double-counts the 48 `both` addresses by construction, as it always has. 45 + 3
was 48 there exactly as 34 + 11 + 4 is 49 here: the three groups are disjoint
and all three come straight from §2's `both` rows. The 109 PD-only and 48 both
figures are unchanged between that correction and this one.)*

## 4. The method, where it can be argued with, and one correction to it

### 4.1 Five direction buckets, one per reference

Each occurrence lands in exactly one, decided from the C around it:

| bucket | what it is | total |
|---|---|---:|
| `read` | the value is used, which includes every `==` comparison | 8,826 |
| `write` | an `=` target, including Ghidra's `DAT_EXTMEM_1300 = DAT_EXTMEM_1300 & 0x0f` spelling | 3,587 |
| `read+write` | an `=` target whose right-hand side names the same address | 2,482 |
| `passed-to-call` | an argument of a call to a routine `index.csv` records | 534 |
| `address-taken` | `&DAT_EXTMEM_xxxx` | 267 |
| | | **15,696** |

**`read` and `write` are the two buckets §4.7's pass moves, and the three that
describe a handoff rather than a direction are the three it cannot.** A
resolved pair site is a store or a load in the *callee*, six bytes away in
another routine, so the caller's own expression carries no `=` and no `==` for
this classifier to read. The direction is the callee's committed `.asm`, which
is why the two directional buckets take the +482 and +392 and the other three
stand at 2,482 / 534 / 267 — the same three they read before. The arithmetic
cross-check is the total: 8,826 + 3,587 + 2,482 + 534 + 267 is 15,696, which is
§3's all-of-it row.

**Drift record, 2026-09-25 (issue #256).** Every total in this table was
stale, and the table is re-derived here rather than left to disagree with the
tool it describes. The row above this block read `8,319 / 3,186 / 2,476 / 549 /
271`, totalling **14,801** — that is the census as §4.3's `==` fix left it, and
`xdata_register_map.py`'s own comment records the movement since: issue #263
read the buckets against a pristine checkout of its parent commit and found
`read` 8,317→8,341, `passed-to-call` 543→534 and `address-taken` 270→267, with
`write` and `read+write` standing, most of it already on `main` before that
branch touched anything. The totals now published are the ones
`--self-test` pins as `BUCKET_TOTALS`, which is where a reader should take a
figure from; the wrong ones stay here because a drift record that deletes the
drift records nothing. **None of this is §4.5's doing**: the co-reading columns
are appended to both CSVs and `refs` is unchanged on every row, so the bucket
totals are the same numbers a fresh generation produced before this change.

*(Correction, 2026-09-25, issue #557 — a second record of the same
re-derivation, written from the committed CSVs rather than from the diff above,
and kept beside it rather than folded into it. The two agree cell for cell on
the tree that correction was measured against: same five superseded values, same
five published values, same 14,819. All five cells and the total move together,
because correcting the total alone would leave a table whose rows do not sum to
it. The superseded cells, kept here rather than deleted: `read` 8,319, `write`
3,186, `read+write` 2,476, `passed-to-call` 549, `address-taken` 271, total
14,801 — this table's own row before either record, which is the 1,172-address
census rather than §1's transcript, and that transcript carries an older set
again (8,317 / 3,186 / 2,476 / 543 / 270) that §1 names beside itself. **Those
are the values issue #279 supersedes**, 8,344 / 3,195 / 2,482 / 534 / 267 and
14,819, which are what the table carried until this update; the paragraph above
is the third record and the first one written against a census this pass
enlarged rather than against a re-export that only re-spelled addresses. The
published cells are the committed CSVs' own columns, re-derived with the same
five columns over `xdata-registers.csv`, and they are also what the tool's
`BUCKET_TOTALS` pins and what `xdata-06c2-06db-timers.md` §6a already quotes.
From the 8,319/3,186 row the five cells moved by +22 / +9 / +6 / −15 / −4, which
sums to the +18 the census moved on that re-derivation: **+37** references into
the three buckets whose spelling is settled (`read`, `write`, `read+write`)
against **−19** out of `passed-to-call` and `address-taken`, a net +18. From
the 8,344/3,195 row §4.7 moves them by +482 / +392 / 0 / 0 / 0, a net +874, and
the shape is the opposite: a pass that *adds* reach rather than re-spelling it
can only push references into the two buckets that record an access at all.
Which of the earlier 19 were re-bucketed and which were genuinely gone is not
something the column arithmetic can say, and the drift record above measures the
same movement from the other end (#263, against a pristine checkout) rather than
asserting a mechanism. That is a re-derivation and not §4.3 again —
`--no-eq-guard` still changes the `refs` of 0 of 1,326 addresses on this tree
(198 of them move `write`, against 210 of 1,171 before). §6's `&&` bullet and
§8's fix for it are restated against these numbers rather than the superseded
ones.)*

**A second set of totals exists, and the difference is the 42 overlapping
exports rather than the buckets.** `ec/decompiled/index.csv` splits
`bank1:0x8001`-`0x8189` into 42 rows whose `.c` files all decompile the same
body, and the census walks one row at a time, so every reference in that
routine is counted 42 times. `xdata_register_map.py --export-ownership` reads
each routine once, from the export that owns it
(`ec/tools/export_ownership.py`), and the five buckets read:

| bucket | as committed | with `--export-ownership` |
|---|---:|---:|
| `read` | 8,826 | 5,361 |
| `write` | 3,587 | 3,043 |
| `read+write` | 2,482 | 1,018 |
| `passed-to-call` | 534 | 500 |
| `address-taken` | 267 | 256 |
| | **15,696** | **10,178** |

Every bucket moves and none of them moves by a factor of 42 on its own — the
`read+write` row nearly halves because the routine's read-modify-writes are
most of what the 42 copies contribute, and `passed-to-call` barely moves
because the routine makes no calls. **The three buckets that do *not* move
between the two columns are the three §4.7's pass cannot touch either**, and
that is the check worth reading: a resolved site lives in exactly one `.c` per
call site, and a `shared` export is skipped by this pass for the same reason it
is skipped by the occurrence walk, so de-duplication cannot merge a pair site
away. `read` +438 and `write` +336 are the pass, in both columns.

**Neither column is in the committed CSVs as a `refs` total and the default is
unchanged**; the middle column is what a plain run produces. The "as committed"
column is not stale: `--check` reports 0 differences over the 1,326 register
rows, and `--self-test` pins both columns' figures as `BUCKET_TOTALS` and
`OWNERSHIP["buckets"]`. §4.6 records what flipping the default would cost, and
`xdata-export-ownership.md` §6 what the pass does not establish.

The two records above are about different things and neither replaces the
other: both re-derive the **published** five buckets from the committed CSVs and
agree cell for cell, and the table above adds a **second, unpublished** set
alongside them, reachable only behind `--export-ownership`. The published
column is what the CSVs carry and what every citation in this file points at;
the de-duplicated column is a measurement of a switch that is deliberately off,
so a reader who takes a figure from it is reading a number no committed artefact
carries.

The totals are the tool's own, and the self-test pins them — but a pin on this
table is internal: these are the buckets summed back to themselves, so they
catch a classifier that changes and not one that was wrong. §4.3 is what the
`read` row's size is *evidence* of, and it needed an external check. What moved
in §4.3 is 837 references leaving the two store buckets: 833 `write` and 4
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
   0.50,touching,507,74,274,61,16,36
   ```

   against the 389 clusters with a largest of 152 that both relations give at
   the same threshold, in the full table below. That **507** is the one number
   in §4.2 that the §4.3 correction does **not** move, and it should not: the
   `touching`-only mode never reads a writer set, so the phantom writers could
   not reach it. The worked example survives the correction intact, because
   `0x04FE`/`0x04FF`'s one real writer at `bank1:0x94FA` was never a comparison.

   *(Corrected 2026-09-25, issue #582: the sentence above said 479, which is
   what the `--threshold-sweep --no-writer-axis` row read on the tree §4.2 was
   written against. The console block beside it already carried 507, having
   moved with issue #279's pair-accessor pass (`6bf9c234`), so the prose was
   the stale half of one paragraph rather than a figure that was wrong twice.
   Re-derived on the committed tree: `0.50,touching,507,74,274,61,16,36`.)*
3. Clusters are **connected components**, not a greedy cover — the relation is
   not transitive, and a greedy pass would make the output depend on address
   order. Every address lands in exactly one; one with no neighbour is a
   size-1 cluster (200 of them on the main EC) rather than a drop.
4. Contiguity is reported as a `span_group` column and **never merged** into a
   cluster. Adjacent addresses are often one multi-byte store, and
   `gen_xdata_symbols.py` names those `_0`/`_1` by address order precisely
   because it refuses to bake a byte order into a symbol; merging on contiguity
   would make that same claim invisibly.
5. `shared_functions` in the clusters table is the subset touching two or more
   of the cluster's addresses — the co-occurrence that put them together.
   `callees` is the call-graph axis: the routines the most of the cluster's
   functions call, capped at three with the overflow counted in the cell
   (`(+194 more called by the cluster's functions)`). A cap that is not printed
   reads as "covered" when it is not.

The threshold is a flag (`--threshold`, default **0.50**) and the whole curve.
The first block is the current one; the second is the pre-#279 tree it
supersedes, kept because the *shape* of the argument is that the plateau has not
moved:

```console
$ python3 ec/tools/xdata_register_map.py --threshold-sweep
threshold,relations,main-ec clusters,main-ec largest,main-ec singletons,pd clusters,pd largest
0.30,touching+writers,229,531,115,35,55,12
0.35,touching+writers,340,273,163,49,35,24
0.40,touching+writers,350,261,169,49,35,24
0.45,touching+writers,384,153,195,50,35,25
0.50,touching+writers,389,152,200,50,35,25
0.55,touching+writers,548,82,314,68,16,39
0.60,touching+writers,562,82,327,69,16,41
0.65,touching+writers,579,81,341,69,16,41
0.70,touching+writers,624,42,382,76,14,50
```

```console
$ python3 ec/tools/xdata_register_map.py --threshold-sweep    # pre-#279 tree
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

0.50 is a recorded choice, not a tuned one, and neither the fix nor §4.7's pass
retuned it. Re-derived on the committed tree after the pair-accessor pass, the
curve is in the console block above and 0.50 still sits on the plateau: from
0.35 to 0.50 the largest main-EC cluster falls 273 → 152 while the cluster
count rises only 340 → 389, and 0.55 drops the largest to 82 and adds 159 more.
0.30 collapses 531 of the 1,218 into one component, which is the shape the
issue warned about when it said a cluster of functions that share them is a
list someone can work through. **The superseding version of that paragraph, kept
rather than deleted: the same claim on the pre-#279 tree — "from 0.35 to 0.50
the largest main-EC cluster holds at 108–112 while the cluster count only moves
337 → 376, and 0.55 drops the largest to 43 and adds 149 more. 0.30 collapses
306 of the 1,063 into one component".** The plateau is where it was, which is
the point of recording a choice rather than tuning one: a pass that adds 155
addresses moves the numbers on the curve and not the place on it. A reviewer who wants a different granularity passes
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
`bank0/D281.c:19` and `bank0/D289.c:18` and the handoff `bank0/D091.c:84`.

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
>
> **CORRECTION (2026-09-25, issue #557) to the `bank0/A747.c:24` line number
> above, which is kept as it was written.** `:24` was right where it was
> written: at `c9e0c2c4` (#206), `grep -n 'DAT_EXTMEM_076a'` over that file
> returns lines **24 and 26**, so `:24` named this site and was the `&&` test,
> not the store. #432's re-export `20b48329` added a line above it and moved
> both, to **25 and 27** — so on the committed tree the site is
> `bank0/A747.c:25`. Only the line number moved; the site, the `&&`, the bucket
> it is misfiled under and the 838/837 arithmetic above all still hold. §6's
> bullet and §8's follow-up carry the current `:25`.

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
because the misclassification is itself internally consistent. Three
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
- a **corpus-wide direction invariant** (issue #280), which asks the same
  question of the whole tree instead of five addresses: every occurrence the
  census buckets `write` or `read+write` must have an assignment — not `==` —
  after the address. It is measured by `direction_invariant()`, a second walk
  of the same text whose predicate is only "an `=` that is not `==` follows",
  so it never consults the `store_target()` being tested. Today that is
  **5,662 occurrences across 1,008 distinct addresses** of the census's 1,171,
  and it holds with no exemptions. The failure message names every offending
  occurrence as `file!line address`, so a failure is a worklist rather than a
  number to re-derive by hand.

**What the invariant adds, and what it does not.** It is *not* a second pair
of eyes: same files, same regex, same `strip_comments()`, and the buckets it
is measured against are the ones this tool just produced. What makes it worth
asserting is that it is not a re-implementation either — the `==` rejection
lives in `store_target()`, and re-running the rule under test would agree with
itself by construction. Re-introducing the pre-fix guard in a scratch copy
fails it on **837 occurrences across 210 distinct addresses**, naming
`0x0440` (15) and `0x0860` (14) and leaving `0x0443`, `0x04FE` and `0x04FF` at
zero — so the 210 of §6a, measured before issue #133's re-export, is
reproducible from the committed tree after all. The 837 and the 838 of the
preceding paragraph are different figures and both are right: 838 is the
count of `==` occurrences in the tree, 837 the count that changed bucket (the
eighth-hundred-and-thirty-eighth is the `&&` site filed as `address-taken`
both before and after). What the invariant cannot reach is a store the
decompiler mis-spelled, a write through a pointer, and a per-address *count*
that is wrong while every occurrence is assignment-shaped — which is the
hand check's remaining job, and the reason five addresses are still kept
rather than folded into the wider net.

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

### 4.4 Two identities, because a rank is not one (2026-09-24, issue #274)

`main-ec-NNN` is what sorts into that position, not what the cluster *is*. This
section measures what that costs and records the two columns the census now
carries so a citation can outlive the ranking. Every number below is a command
re-run over the committed tree, and the recipe is
`xdata-06c2-06db-timers.md` §6a's with the `==` guard issue #178 added
**removed** instead — the classifier-and-everything-it-counts regeneration, in
its cheapest form. That is the `--no-eq-guard` flag
(`../tools/xdata_register_map.py:4457`) with scratch outputs, which is what §6a
and this block's transcript now do rather than a source edit: the flag is
refused with the committed output paths
(`../tools/xdata_register_map.py:4495-4499`), so everything below is a report
about the committed census and not a replacement for it. The derivation, with
the commands and their output, is
`../../docs/findings/xdata-4-4-identity-rederivation.md`.

**The cost, measured.** 439 clusters become 445. Of the 439 committed ids, **124
survive intact** and **315 change what the number names** — 311 land on a
different id outright and 4 keep the number while the membership under it moves
— so an id is stable for one generation, not across one. That is the whole of
issue #253's mechanism, and it is a property of the ordering key, not of the
census.

*(This paragraph and the table below were re-run 2026-09-25, issue #582. The
superseded figures are issue #274's, true of the census #274 measured against
before #327's unnamed-callee pass and #279's pair-accessor pass moved it: 427
clusters become 439, 48 intact and 379 changed, 409 keys unchanged and 420
reaching a new cluster. The wrong version is kept rather than deleted, per
`../../docs/findings.md` §4a; this section's own issue-#279 correction already
carried the 315/124 split this re-run confirms.)*

| | of 439 committed clusters |
|---|---:|
| rank (`main-ec-NNN`) intact across the regeneration | 124 |
| `cluster_key` — a content hash — unchanged | 424 |
| committed rows reaching a new cluster by key, else best membership overlap ≥ 0.50 | 434 |
| …where the new cluster is claimed by more than one old row | 0 |

**The header and the third cell count different things, and it is worth saying
which.** 439 is a count of `ec/annotations/xdata-clusters.csv`; 434 is a count
of what the regeneration did with those 439 rows, and the five it did not place
are the summary's "5 with no match at 0.50". Neither is **430**, the count of
committed clusters carrying a key and no `cluster_name` — that is 439 minus the
nine names, and it is the same number `--check` prints as `with no name 430`.
The old table's 420 and the old prose's 417 were that collision from the other
direction; these figures no longer share an integer, and the two questions
still do not answer each other.

**`cluster_key` is the cheap half.** `sha256` over the program's name and the
cluster's space-joined sorted `addrs`, truncated to 12 hex digits and spelled
`k<hex>`, computed in `build()` where the cluster is formed and never read back
out of a CSV to decide a key — a key that came from the file it is written to
could drift with the file. It is in both census CSVs, is exact, and says
nothing about a near miss: two clusters whose membership differs by one address
have keys with nothing in common. The self-test asserts the keys are distinct
rather than taking a truncated hash's word for it, and does it in both places
that can hold it: over a fresh generation's rows, and over the **committed**
census read back from `xdata-clusters.csv` — its 439 keys, the ones every
`cluster_key` citation in the tree resolves against.

**The 15 that a key cannot carry include the two largest clusters in the
committed census, which is why the key is not the answer.** `main-ec-001` (152
addresses) and `main-ec-002` (92) are two of them, and `main-ec-002` is the
cluster `mode-oem-init` names, cited by seven pages of the tree for a membership
it holds. A key-only design hands the two biggest a brand-new identity under
exactly the regeneration this section is about. Of the 15, **10 reach a new
cluster on overlap and 5 do not reach one at all** by this rule (best scores
0.50-0.97 for the ten, 0.02-0.33 for the five).

*(Correction, 2026-09-25, issue #582's re-run. This paragraph used to read "The
18 that a key cannot carry include the two the prose cares about most …
`main-ec-002` (108 addresses) and `main-ec-003` (44) … the two largest clusters
any page in the tree cites … Of the 18, **11 reach a new cluster on overlap and
7 do not reach one at all**", at 0.50-0.97 and 0.01-0.33. Those are issue #274's
figures against the census #274 measured: the second and third largest clusters
then, which are not the two largest now. `main-ec-003` has not changed key at
all — it is `counter-sweep`, `seeded` at 1.00 — and it is the most-cited cluster
in the tree (`grep -rl 'main-ec-003\b' --include=*.md .` names nine files,
against seven for `main-ec-002`), so the "largest" claim and the "a key cannot
carry" claim were never about the same set. The old sentence is kept in this
correction rather than deleted, per `../../docs/findings.md` §4a.)*

**`cluster_name` is the half that does.** `annotations/xdata-cluster-names.csv`
is a hand-edited `cluster_key,cluster_name,note` file — the one place a human
adds a row, the way `ghidra-functions.csv` is for functions, and the `note` is
the evidence for the name the way that file's `evidence` column is. A generation
carries each named cluster forward by exact key first and otherwise by best
Jaccard against the membership the key was last seen with, at
`CARRY_MIN_JACCARD` = 0.50 (the clustering's own default, so a name and a
cluster are carried by the same number). All nine names survive this
regeneration; the one whose membership moved — `mode-oem-init`, 92 addresses in
the committed census and 93 in this run — carries at 0.97, and the other eight
are `seeded` — the names file's key is still this cluster's key. **The margin
is not close**: for each of the nine, the best match scores 0.97 to 1.00 and
the *next* named cluster scores **0.00**, so the threshold is not a tuned
number sitting on a cliff — any value between 0.01 and 0.97 gives these nine
the same nine answers. **That the nine are the nine clusters the committed
prose makes a membership claim about is the point, and it is also the limit:
430 clusters in the committed census have a key and no `cluster_name` — a count
of that CSV, not of this regeneration, and not the 434 above — and a name
nobody cites is a column that reads as coverage it does not have.** Adding one
is a one-row edit.

*(Correction, 2026-09-25, issue #582's re-run. This paragraph used to read "All
ten names survive this regeneration; the four whose membership moved carry at
0.96, 0.64, 0.90 and 0.78, and the other six are `seeded` … for each of the ten,
the best match scores 0.64 to 1.00 … any value between 0.01 and 0.64 gives these
ten the same ten answers … 417 clusters have a key and no name". The names file
holds nine rows and the committed census nine `cluster_name` cells: the tenth
name was `page-0300`, whose row issue #279's pair-accessor pass dropped when the
nine-address `0x0300` cluster it named was absorbed into `main-ec-001` (§5's
re-derivation records that merge, and this change re-keys nothing). So the four
overlap carries collapse to one, and 417 is the `with no name` line of a census
that has since been regenerated. The superseded text is kept here rather than
deleted, per `../../docs/findings.md` §4a, and the re-keys that moved the nine
are recorded in `xdata-cluster-names.csv`'s own `Re-keyed` notes.)*

**Four outcomes, four claims.** `seeded` and `exact` are the same claim and are
reported as two because they are two different facts about where the name came
from. `overlap` is a weaker one and the score travels with it, in the write
transcript, in `--self-test` and in `--map`: a name carried at 0.98 and one
carried at 0.78 are not the same statement about the firmware. `tie` — a named
cluster claimed by two old names at the same best score — is reported and **no
winner is picked**, because which of them the new cluster is, is a fact about
the clustering rather than a coin to flip. And a cluster nothing matched is
reported as **not carried by this method**: never *gone*, never *lost*. A
function that stopped decompiling, a threshold that moved and a cluster that
stopped existing are three different things, and this column can only report
that its own rule did not fire.

```console
$ rm -rf /tmp/census && mkdir -p /tmp/census
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/census/registers.csv \
    --out-clusters /tmp/census/clusters.csv
wrote /tmp/census/registers.csv: 1326 rows
wrote /tmp/census/clusters.csv: 445 rows
  main-ec: 1218 distinct addresses, 14838 references, 394 clusters at threshold 0.5
  pd: 157 distinct addresses, 858 references, 51 clusters at threshold 0.5
  names: seeded 8, exact 0, carried by overlap 1, tied, not carried 0, with no name 436
    main-ec-002 carries mode-oem-init by overlap, Jaccard 0.97 from kefb63d82f8c7 -- re-key annotations/xdata-cluster-names.csv if the name moved
```

**The copy-and-`str.replace` this transcript used to open with is gone, and its
replacement is the flag the block's preamble names.** The old recipe copied the
tool into `/tmp`, symlinked the inputs back, and deleted the `==` guard from the
copy's source, because when the block was written nothing else removed it. It
was a workaround one rename away from silently regenerating the guard-on census
instead, and the tree has since taken that step: issue #302 parameterised the
guard (`../tools/xdata_register_map.py:1582` is `if eq_guard and
stripped.startswith("==")`) so `--no-eq-guard` could be a flag. A regeneration
now writes to a scratch path and reads the committed decompile in place, with
no copy of the tool and no source edit. The `--out-*` flags are not decoration
either: the tool refuses `--no-eq-guard` with the committed output paths
(`../tools/xdata_register_map.py:4495-4499`), which is what keeps a run of
this transcript from overwriting the census it is measuring.

*(Correction, 2026-09-25, issue #582's re-run. The transcript above is the same
experiment re-run against the tree as it now stands; the one it supersedes
built 1,171 register rows and 439 clusters from a copy of the tool, seeded 6
names and carried 4 on overlap at 0.96, 0.64, 0.90 and 0.78, including
`page-0300` from `k3fdd14ddea2e` — a name the committed names file no longer
carries, for the reason the correction beside "All nine names survive" gives.
The superseded transcript is kept in the correction record at
`../../docs/findings/xdata-4-4-identity-rederivation.md` rather than here, so
that this block holds one run rather than two.)*

The `re-key` is the one hand-edit this costs, and it is named because it is
real: the names file is keyed by `cluster_key`, so a name that survives in
changed form is now anchored to a key the current census no longer has. A
regeneration's owner re-keys it once; the committed self-test fails on a stale
key rather than letting the names file drift quietly out of the census.

**The names are anchored to the committed census, and this tree already needs
the re-key it describes.** The census committed here is behind a fresh
generation of the same tree — 427 clusters to 430, the gap §5's correction
block records — so three of the ten names already name a membership a fresh
run does not produce: `mode-oem-init` (`k5be7031564f8`), `level-block-086x`
(`k2d9004f7707b`) and `user-clear-bytes` (`k76e75f349ea7`). Every key here
resolves against `xdata-clusters.csv` as committed, which is what a
`cluster_key` or `cluster_name` citation in this tree resolves against, so
that is what the self-test checks and what the names file is written against.
The gap is the pre-existing staleness `--self-test` already reports on `main`
as "the committed CSVs match a fresh generation", not something this issue
introduced, and closing it is a regeneration of the committed CSVs rather than
a re-key of the names: `xdata_register_map.py --check` without `--map` is the
command that settles it. It is written down here because the alternative is a
red self-test that looks like this file's doing.

*(Correction, 2026-09-25, issue #256's regeneration: this paragraph describes a
gap that has since been closed, not a finding that was wrong. The re-key it
calls for was done — `xdata-cluster-names.csv` carries `k7497cf885614` and its
eight siblings where this transcript prints the three superseded keys, and
`--self-test` reports no stale key — and the committed census is no longer
behind a fresh generation, so the `main-ec-013` row below it names a membership
the census holds. The assertion this paragraph says the self-test reports as
red, "the committed CSVs match a fresh generation", is green; the one assertion
still red is the `index.csv` function-naming drift, which is a different thing.
The paragraph is kept because the gap was real on its tree and because the
re-key it describes is what the names file's own `Re-keyed 2026-09-24` note
cites.)*

**`--map OLD_CSV` is the report a prose sweep is driven from.** One row per old
cluster: where it went, whether its key changed, the carried name and how, the
Jaccard, and the membership delta address by address — the thing issue #253
needed and did not have. Rows go to stdout as CSV and the summary to stderr, so
the report redirects without the prose ending up in it.

```console
$ python3 ec/tools/xdata_register_map.py --no-eq-guard \
    --out-registers /tmp/census/registers.csv \
    --out-clusters /tmp/census/clusters.csv \
    --map ec/annotations/xdata-clusters.csv > /tmp/census/map.csv
439 rows: 15 whose cluster_key changed, 15 whose membership changed, 5 with no
match at 0.50, 10 carrying a name
```

`--map` reports and does not write: `--out-clusters`/`--out-registers` default
to the committed CSVs, so a `--map` run that honoured them would overwrite the
very census it is mapping. The CSVs for a regeneration come from the writing
run above — the same command without `--map` — and those are the files
`../tools/check_cluster_citations.py --clusters/--registers` reads, so the two
compose on one tree without either overwriting the other.

**The "10 carrying a name" is not a tenth name.** It counts *old rows* whose
new cluster carries one, and `--map` fills a `cluster_name` cell even on a row
whose `match` is `none`: `main-ec-145`, a two-address row, is printed with
`mode-oem-init` beside a 0.02 Jaccard because that is the best guess `--map`
found. Nine is the number of names, 10 the number of rows that mention one, and
the report's own rule — a claim is counted only for a row that actually matched
(`../tools/xdata_register_map.py:4298-4300`) — is what keeps the near miss out
of the "claimed by more than one old row" cell, which is 0 above.

**The test that settles it** is `../tools/test_xdata_cluster_names.py`, which
runs that regeneration out of a `tempfile` and then holds four things: that the
name `counter-sweep` still resolves to a cluster containing all 43 addresses
`xdata-06c2-06db-timers.md` §1 sweeps; that the tool says what moved about it;
that `main-ec-002` and `main-ec-004` are carried by **overlap and not by key**;
and that no name is lost. What it measures is sharper than "nothing moved": the
counter-sweep cluster keeps its key *and* its exact 43-address membership here.
On the census this tree commits its **rank** survives that too — the
regeneration `--no-eq-guard` builds leaves `counter-sweep` at `main-ec-003`
with key `k733222e83898` and the same 43 addresses — and what moves instead is
everything else in the ranking: of the 439 committed clusters, **315 change
what their `main-ec-NNN` names** and 124 do not. `main-ec-002` is one of them
either way, naming the committed 92-address `mode-oem-init` and a 93-address
cluster here, so the same id is a different cluster in the two censuses — which
is the point, and is why the rank is not an identity.

*(Correction, 2026-09-25, issue #582's re-run. The 315/124 split, the
`main-ec-003`/`k733222e83898`/43 addresses and the 92→93 are re-derived and
stand. One clause of the paragraph above does not: the suite no longer builds
the regeneration this paragraph describes, so none of its four holds is
currently *running*, and the clause naming `main-ec-004` as "carried by overlap
and not by key" is not what the committed census would give anyway —
`level-block-086x` is `seeded` there, key and membership both unchanged, and
`main-ec-002` is the only one of the two carried on overlap (0.97). The suite's
own recipe is two generations behind: `GUARD`
(`../tools/test_xdata_cluster_names.py:54`) is a literal the parameterised guard
at `../tools/xdata_register_map.py:1582` no longer contains, and its
two-largest case pairs `main-ec-001` with `mode-oem-init` and `main-ec-002`
with `level-block-086x`, which the committed census puts at `main-ec-002` and
`main-ec-004`. **The suite is red on `main` and is not wired into
`.github/scripts/agent-gates.sh`**, so nothing has been failing CI over it.
Fixing it is a change to a test and is a follow-up, not a line to move inside a
documentation change; `../../docs/findings/xdata-4-4-identity-rederivation.md`
carries the reading in full.)*

*(Correction, 2026-09-25, issue #279. This paragraph used to read that only the
rank moved — "`main-ec-003` → `main-ec-002`", the 44-address cluster ahead of
it shrinking to 28 once the `==` guard is gone — which was true of the census
issue #274 measured against and is not true of this one. The wrong version is
kept here rather than deleted, per `../../docs/findings.md` §4a. The two ids
the paragraph names beside it are re-derived from the committed
`xdata-clusters.csv`: `mode-oem-init` is `kefb63d82f8c7` on `main-ec-002` and
`level-block-086x` is `ka39cda99615f` on `main-ec-004`, against the
`main-ec-001` and `main-ec-002` the #274 text named.)*

**What this does not make true.** A `cluster_name` in the CSV cell does not
record how it got there — that is what `--map` and the write transcript are for,
and a name is only as good as the carry that put it there. A name that clears
0.50 on Jaccard is a *guess about which cluster it is*, and this file's §6
still says what a cluster is: a co-occurrence pattern in static code, evidence
about shape and not about meaning. The counter-sweep cluster is 43 addresses and
4,965 references and 93% of those references are one 393-byte routine counted 42
times over (`xdata-06c2-06db-timers.md` §2a) — a name does not make that
smaller, and `counter-sweep` names the block a page read, not a mechanism.
A census is still a lower bound on the image: `cluster_key` is a hash of a
membership, so a cluster the decompiler never produced has no key to lose.

**The rank stays.** `cluster_id` keeps the exact values it has today, in both
CSVs and in every page that names one, because switching over is a prose sweep
and not a decision this change makes. `../tools/check_cluster_citations.py`
resolves all three citation forms — `main-ec-NNN`, `cluster_key` and
`cluster_name` — and takes `--clusters`/`--registers`, so the *same* sentences
can be run against a regeneration's output, which is the half of the issue's
test the committed checker could not do on its own.

### 4.5 A source count is a count of files, and 42 files can be one routine (2026-09-25, issue #256)

Numbered after §4.4 rather than before it, so every page that cites §4.4's
identities still resolves.

`refs` counts *references*, and a reference is attributed to a source function
file — `blank_entry()["funcs"]` has been that per-file incidence matrix since
the beginning, and §5's `functions` column is its published form. What the
census had no notion of is the other half: **42 `.c` files naming the same
addresses.** The counter sweep of `xdata-06c2-06db-timers.md` §2 is 393 bytes
the exporter split into 42 listings, and all 42 decompiled the routine rather
than their own bytes, so the 19 addresses every one of them names are each
counted 42 times over — `0x0843` is credited with 168 references and has **one**
direct `MOV DPTR,#0x0843` in the image. The relation this section adds is:

> **Two `.c` files in one program are co-readings when they name the same
> `COREADING_MIN_CORE` (8) or more XDATA addresses. A co-reading group is a
> connected component of that relation, computed per program, exactly as
> `components()` does for addresses.**

Components rather than a cover, for `components()`'s reason: the relation is
not transitive, so a greedy pass would make the output depend on file order.
Per program, because the two images have separate XDATA maps and a shared
address *number* is not a shared byte — `--self-test` asserts no group ever
spans two.

**The floor is recorded, not tuned.** `python3 ../tools/xdata_register_map.py
--co-reading-sweep` prints it:

| floor | 2 | 4 | 6 | **8** | 10 | 12 | 16 | 20 | 24 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| largest group | 282 | 61 | 42 | **42** | 42 | 42 | 42 | 41 | 40 |
| files in groups | 723 | 335 | 213 | **120** | 89 | 79 | 62 | 50 | 48 |

Floors 2 and 4 are the trivially-equal-address-set artefact — two files that
each name one address score a Jaccard of 1.00 — and 6 to 16 hold the sweep's 42
together while the file count keeps falling. 8 is where files-in-groups halves
against 6 with the largest group unchanged, the same "recorded, not tuned"
argument §4.2 makes for `DEFAULT_THRESHOLD`.

**The groups, all 24 of them**
(`--co-reading-group-table` prints this; `core` is the addresses *every* member
names, `bytes` the sum of the group's `index.csv` listing sizes, `1-byte` how
many of those listings are a single instruction):

| program | files | core | bytes | 1-byte | first → last |
|---|---:|---:|---:|---:|---|
| `bank1` | **42** | 19 | **393** | **16** | `bank1/8001.c` → `bank1/80EF.c` |
| `bank0` | 8 | 8 | 720 | 0 | `bank0/D5D4.c` → `bank0/FE0F.c` |
| `bank1` | 7 | 11 | 465 | 0 | `bank1/AD85.c` → `bank1/B43B.c` |
| `bank0` | 6 | **1** | 1,969 | 0 | `bank0/8749.c` → `bank0/8DE0.c` |
| `bank0` | 6 | 4 | 1,597 | 0 | `bank0/95DD.c` → `bank0/9D9B.c` |
| `bank0` | 4 | 6 | 708 | 0 | `bank0/A00E.c` → `bank0/A1C8.c` |
| `bank0` | 4 | 8 | 82 | 0 | `bank0/EFDC.c` → `bank0/F012.c` |
| `bank1` | 4 | 2 | 808 | 0 | `bank1/DB0B.c` → `bank1/E090.c` |
| `common` | 4 | 8 | 394 | 0 | `common/223F.c` → `common/22EF.c` |
| `bank0` | 3 | 21 | 562 | 0 | `bank0/B12C.c` → `bank0/B1F0.c` |
| `bank0` | 3 | 12 | 316 | 0 | `bank0/D091.c` → `bank0/D28E.c` |
| `bank1` | 3 | 10 | 159 | 0 | `bank1/8AE5.c` → `bank1/8B04.c` |
| `bank1` | 3 | 8 | 194 | 0 | `bank1/C4D2.c` → `bank1/C54C.c` |
| `bank1` | 3 | 7 | 404 | 0 | `bank1/E2D3.c` → `bank1/E490.c` |
| `bank0` | 2 | 9 | 159 | 0 | `bank0/8038.c` → `bank0/83FF.c` |
| `bank0` | 2 | 8 | 33 | 0 | `bank0/8048.c` → `bank0/8054.c` |
| `bank1` | 2 | 9 | 324 | 0 | `bank1/976E.c` → `bank1/9817.c` |
| `bank1` | 2 | 8 | 279 | 0 | `bank1/9B3C.c` → `bank1/9C53.c` |
| `bank1` | 2 | 8 | 277 | 0 | `bank1/9CE8.c` → `bank1/9D53.c` |
| `bank1` | 2 | 9 | 306 | 0 | `bank1/B98D.c` → `bank1/BA43.c` |
| `bank1` | 2 | 8 | 237 | 0 | `bank1/D0C4.c` → `bank1/D17E.c` |
| `bank1` | 2 | 10 | 285 | 0 | `bank1/E100.c` → `bank1/E237.c` |
| `common` | 2 | 8 | 155 | 0 | `common/0200.c` → `common/0213.c` |
| `pd` | 2 | 17 | 363 | 0 | `pd/A8AE.c` → `pd/AE9C.c` |

Three rows of that table are the whole argument, and they are three different
kinds of row.

**The 42 are one group, and the tool now reproduces §2's three checkable
facts.** The largest group is 42 files, `bank1/8001.c` through `bank1/80EF.c`
— the sweep's own seeds, all of them inside `0x8001`-`0x8189` — with a
**19-address common core**, `index.csv` listing sizes summing to **393** and
**16** of them one instruction. `--self-test` asserts the file count, the byte
total, the one-instruction count and the core, so §2's hand count and the
census agree. The core is 19 and not the 46 addresses `8001.c` itself names,
because the listings start at different points in the body: `8001.c` spells out
`0x06C6` where `8018.c` opens at the store-back, and the 19-address tail
`80EF.c` names 19, exactly as §2 records.

**The `bank0/8749.c` six is the counter-example, and it is why the core column
is published.** Six files, a **one-address** common core (`0x1804`, which all
six read), and 1,969 listing bytes between them. Three of the six also read
`0x0440`; the other three do not, and that is the whole of what a one-address
core means — a shared address, not a shared body. They are six real readers
that a neighbour connects, and the component — not a pair — is what puts them
in one group. Reading a group as "one routine" would merge them; the `bytes`
column is what says no. `bank1/8008.c` is the sharpest single illustration of
what the observable is: `index.csv` records it at **one byte** — the single
`movx @DPTR, A` §2 names — and the census finds **45** addresses in it. A
one-byte listing naming 45 addresses is the fact; "this file is a slice of a
larger routine" is the hypothesis, and `xdata-06c2-06db-timers.md` §2 is where
it is stated.

**The `pd` pair is in its own program, on purpose.** `pd/A8AE.c` and
`pd/AE9C.c` share 17 addresses including seven of `pd-001`'s ten `0xFFxx` bytes
(§5.1), and no group crosses into the main EC — which is the split §3 insists
on, now asserted rather than assumed.

**Per address, the new `co_reading` and `sources_beyond` columns.** `refs` is
unchanged; `sources_beyond` is the count of source functions this relation
cannot pair with another copy of, which is the closest thing here to a distinct
source count and is a count of *files*:

| addr | `refs` | `functions_touched` | `co_reading` | `sources_beyond` |
|---|---:|---:|---:|---:|
| `0x0843` | 168 | 42 | 42 | **0** |
| `0x0844` | 168 | 42 | 42 | **0** |
| `0x08A8` | 170 | 44 | 44 | **0** |
| `0x06D6` | 148 | 37 | 37 | **0** |
| `0x080D` | 137 | 48 | 42 | 6 |
| `0x06C2` | 126 | 52 | 39 | 13 |
| `0x0460` | 115 | 48 | 46 | 2 |
| `0x0440` | 181 | 91 | 46 | 45 |

`0x0440` is the row that keeps this a count and not a verdict: it loses 46 of
91 sources to groups and **keeps 45**, is all-read with no writer (§4.3,
`HAND_CHECKED`), and is the most-referenced address in the firmware. A flag
that retired it would be reporting a shape as a conclusion. `0x0843` keeps
none. `0x00B6` — one PD function, no group — is in the tool's hand-read table
to pin that the relation never crosses the two programs.

**Per cluster, three more columns.** `co_reading` is how many of the cluster's
touching functions are in a group, `co_reading_refs` is what the largest single
group supplies *of that cluster's own references*, and `co_reading_dominant`
says whether that is more than half. It reads `yes` for **37 of the 439**
clusters — 7/225 at size 1, 22/160 at 2-4, 4/40 at 5-9, 3/12 at 10-49, 1/2 at
50+ — so it is a place to look rather than a defect, and it is uninformative
at size 1, where one function is all of the refs by construction. **The share
is the readable number, not the boolean.** By share, `main-ec-003` is 4,642 of
4,966 = **93%** and the next clusters of size ≥10 are `main-ec-008` at 79%,
`main-ec-007` at 75%, the new `main-ec-001` at 55% and `pd-001` at 50%.

*(Corrected 2026-09-25, issue #279, re-derived from the committed
`xdata-clusters.csv`. The wrong version, kept here rather than deleted: `yes`
for 24 of the 430 clusters, 7/229 at size 1, 11/151 at 2-4, 3/37 at 5-9, 3/12 at
10-49 and 0/1 at 50+, which is what the pre-#279 census read. The
`main-ec-003` share and the `main-ec-008` / `main-ec-007` / `pd-001` figures
are unmoved; `main-ec-001` is the one the pass added into the run, at 479 of
873.)*

**What the boundary hypothesis would imply, printed and not adopted.**
`--collapse-co-readings` maps each group to one pseudo-function and re-clusters,
writing neither CSV:

| | clusters | largest | singletons |
|---|---:|---:|---:|
| `main-ec` | 380 → **466** | 109 → **150** | 204 → 282 |
| `pd` | 50 → **61** | 35 → **16** | 25 → 36 |

**The collapse does not dissolve the co-occurrence — it merges it into
something bigger, and that is the strongest argument against adopting it.** The
largest main-EC cluster grows from 109 addresses to **150**, spanning
`0x030A`-`0x1F07`. The same command says where the old clusters' addresses went:

```
  109 addresses over 0x030E-0x1809: 63 stay together in a 150-address cluster, 46 do not, across 26 other clusters
   43 addresses over 0x0460-0x09CE: 30 stay together in a 150-address cluster, 13 do not, across 13 other clusters
   28 addresses over 0x045C-0x1C3A: 24 stay together in a 150-address cluster,  4 do not, across 3 other clusters
```

So 30 of the counter block's 43 addresses are pulled into the 150 by the
sweep's single pseudo-function, and each of the other 13 lands in a cluster of
its own — 11 of them singletons, one sharing with a single other address and
one (`0x09CE`) with six, those six from a six-address cluster of their own.
`0x0440`, which the sweep reads 42 times and which no single function
dominates, is **not in the 150 at all**. A de-duplicated source count
here therefore neither tidies the clustering up nor rescues the block: it turns
one overlapping routine into one very widely-shared function and hands it a
*larger* cluster than the one the 42 copies were propping up, while the
addresses only the copies shared fall out the bottom. (`main-ec-002` loses 46
of its 109 across 26 clusters the same way, so the 150 is not "the counter block
plus its friends" — three old clusters now share one pseudo-function and
nothing else.) So the honest reading of the committed census is neither "93% of
this cluster is an artefact, ignore the cluster" nor "collapse the sweep and the
block is a clean 43" — it is that the cluster's membership is a property of the
export's boundaries either way, and `cluster_id = main-ec-003` is no more a
description of the firmware than a 150-address cluster would be.

**This is not the committed clustering and does not become it**, because a
group is a relation over files and adopting the collapsed counts would be
deciding the boundary question with a count of files. `cluster_id`, every
`refs`, every `cluster_key` and the whole worklist order are exactly what they
were before this section: the rank is `(size, refs, lowest address)` and the
new columns move none of the three, so **nothing can reorder** — the
`refs`-driven reordering a de-duplicated census would cause is the one thing
this change declines to do.

**What it does not establish.** A co-reading group is a *count of files*. It
is not a claim that the files are one routine, that a reference is wrong, or
that an address is read fewer times than `refs` says; `refs` is unchanged on
every row and no de-duplication heuristic is attached to the tokenizer. The
`bank0/8749.c` row is the standing counter-example, and `0x0440`'s 45 surviving
sources is the standing control. And a group is a relation over *this* export:
a re-export that moved a boundary would move the groups, which is another
reason the durable citation is §4.4's `cluster_key` and not an id or a flag.

### 4.6 What flipping the default would cost, measured (2026-09-25, issue #554)

Numbered after §4.5 rather than before it, for the reason §4.5 gives: the
co-reading relation is the reading and this is the price of acting on it, and
the two are the same argument read in the other order. A §4.5 that landed first
is why the section is 4.6 rather than 4.5.

This subsection is the second identity doing its job. Everything above is
about a key surviving a regeneration; this is the measurement of what a
regeneration actually costs, for the one change that was on the table.

`--export-ownership` reads each routine once, from the export that owns it,
instead of once per overlapping export (§4.1). Run against the committed tree
it is a good deal on the numbers and a bad one on the identities:

| | as committed | with `--export-ownership` |
|---|---:|---:|
| clusters | 439 | 440 |
| committed `cluster_key`s that survive | — | **400 of 439** |
| new `cluster_key`s | — | 40 |
| hand names in `xdata-cluster-names.csv` that still resolve | — | **4 of 9** |
| `counter-sweep`'s key `k733222e83898` | 43 addrs, 4,966 refs | gone; nearest is `k22aecb4dc595` at 43 addrs, 280 refs |
| addresses lost from the census | — | **0** |

**So 39 keys and 5 hand names would have to be re-issued, and `main-ec-003`'s
membership would not survive whole as any single cluster** — which is the same
hazard the top of this file records for the ids, one level down. That is why
the default does not flip here. The pass is a containment heuristic over
decompiled text rather than a function boundary, and the root cause — the
exporter cutting one routine into 42 functions — needs
`--mode rebuild-project`, which cannot share a branch
(`xdata-06c2-06db-timers.md` §8 item 7). The flip is that fix's PR.

The plan stage estimated this flip at 39 of 430 keys, 4 of 10 names, and **one
address lost** (`0x05E0`, whose only export is a non-owner in its class). The
committed tool measured 35, 5, and none: `bank1/8E91.c` owns its own two-file
class here, so the one file in the tree that spells `DAT_EXTMEM_05e0` is still
read. **§4.7's pair-accessor pass re-measured it at 39 of 439, 5 of 9, and
none** — the key figure got worse and the name figure got better, and the two
are one event. The pass makes the default census's clusters larger, so more of
them no longer coincide with the de-duplicated build; `page-0300` left
`xdata-cluster-names.csv` outright (its nine-address cluster is now nine
addresses inside a 152-address one, Jaccard 0.07, **not carried by this method**
rather than gone), which takes the name denominator from ten to nine while the
numerator stays at five. The `lost` set is pinned in the tool's `OWNERSHIP` oracle so that if a
re-export ever makes it non-empty, that is a failing check rather than a
census that quietly lost a byte. `xdata-export-ownership.md` §4 has the whole
account, including why a detector's membership is worth committing rather than
carrying forward.

### 4.7 The pair accessors: an address as an argument, not a token (2026-09-25, issue #279)

This is the pass that moved the census's totals, and it is the first one in
this file that adds *reach* rather than correcting a count.

**The shape.** `bank1` has six seeded routines whose whole committed body is
two `movx @DPTR` dereferences an `inc DPTR` apart:

| routine | direction | its body |
|---|---|---|
| `bank1:0x8886` `read_xdata_pair_to_r1r2` | read | `movx A,@DPTR` / `mov R1,A` / `inc DPTR` / `movx A,@DPTR` / `mov R2,A` / `ret` |
| `bank1:0x888C` `write_r1r2_to_xdata_pair` | write | `mov A,R1` / `movx @DPTR,A` / `inc DPTR` / `mov A,R2` / `movx @DPTR,A` / `ret` |
| `bank1:0x8892` `read_xdata_pair_to_r3r4` | read | as `0x8886`, into `R3`/`R4` |
| `bank1:0x8898` `read_xdata_pair_to_b_and_a` | read | `movx A,@DPTR` / `mov B,A` / `inc DPTR` / `movx A,@DPTR` / `ret` |
| `bank1:0x889E` `write_r3r4_to_xdata_pair` | write | as `0x888C`, from `R3`/`R4` |
| `bank1:0x9193` `store_r1_r2_to_xdata_at_dptr` | write | byte-for-byte `0x888C` |

Their callers pass the address as a **first argument**, and the decompiler
gives these accessors a three-parameter signature it never established, so the
common shape is `write_r1r2_to_xdata_pair(0x434,0,0)` rather than a bare
`DAT_EXTMEM_0434`. `occurrence_re` matches a `DAT_EXTMEM_xxxx` token or a
generated symbol name, and **neither is what an argument looks like**:

```console
$ grep -n 'read_xdata_pair_to_r3r4' ec/decompiled/bank1/B407.c
73:  read_xdata_pair_to_r3r4(FUN_CODE_0402);
$ grep -rn 'FUN_CODE_0402' ec/decompiled/ | wc -l
15
```

`B407.c` matches that accessor name once, at `bank1/B407.c:73`, so the line
number is that one. The 15 are not 15 call sites: ten are the bank1 call
sites this pass resolves, two are inside the invented routine's own body
(`common/0402.c`), and the remaining three are the one `common/0402.asm` line
plus the two index rows (`index.csv` and `listing-index.csv`) that list it.

`FUN_CODE_0402` is the decompiler's own name for a routine it *invented* at
`0x0402` because it read `mov DPTR,#0x0402; lcall 0x889E` as a call rather than
as a pointer — and exported two files for it, `common/0402.c` and
`common/0408.c`. The address is data. The spelling says it is code. **The
committed `.asm` settles it and nothing else does**, because `movx` is the
instruction that names the external data space: a literal handed to a routine
whose whole body is two `movx` is XDATA whatever Ghidra called the token.

**The discriminator, stated as a rule and not as a name list.** The tool
selects the set from `ghidra-functions.csv` *and* the committed `.asm`
together: an annotated `reader`/`writer` whose listing is exactly two `movx
@DPTR` an `inc DPTR` apart, with only register shuffles and a closing `ret`
beside them. A disagreement between the annotation's `type` and the listing's
direction is an error, not a reclassification. Two things fall out of reading
the set out of the tree rather than listing the ones that pay:

* **`0x8898` is a fifth accessor the issue does not name**, of identical shape
  and already annotated `reader,hand-decoded`. It is found by the rule.
* **`0x9193` is a sixth**, byte-for-byte the same body as `0x888C`, and *both*
  its callers pass a register (`bank1/D946.c:43`, `bank1/D4D3.c:25`) — so it
  resolves nothing. Its presence in the set costs no figure, which is the
  point: what makes a call site resolve is the literal, not the name.

`bank1:0x9182` reads a pair too and is correctly **excluded**: its body has
`add`/`addc`/`rrc` after the second `movx`, so it is a routine that reads a
pair and then does arithmetic rather than an accessor, and its two callers pass
a variable anyway. The pd image has one accessor of the same shape,
`read_be16_from_dptr` at `pd:0x38D3`, and its single caller passes no argument
at all — so **the whole set resolves inside bank1** and the pass needed no
program carve-out to say so.

**Three gates on each call site**, and each is load-bearing:

1. **The callee must be a selected accessor.** This is the only place in the
   tool that reads a `FUN_CODE_`/`DAT_CODE_` argument at all, and it does so
   only for routines whose committed `.asm` dereferences XDATA. Everywhere else
   the code-pointer exclusion stands, which is why `0x0733` — a real code
   pointer into `bank0:0x94D0=copy_code_table_into_0730_07a7` — is still
   excluded. The self-test asserts `code_only == {0x0733}` *after* the pass has
   run, not before it.
2. **The argument must not already be an occurrence.** `bank1/9354.c:19` passes
   `DAT_EXTMEM_0318` to `read_xdata_pair_to_r3r4`, which the token pass already
   counts; resolving it as a pair as well would give `0x0318` a read it has no
   site for and `0x0319` a reference with no site behind it. **Three
   independent gates stop that, and it would be wrong to credit this one
   alone.** On this tree the *literal* gate does it — `DAT_EXTMEM_0318` is not
   one of the accepted literal forms, and zero of the tree's 461 first
   arguments are both a literal and an occurrence. Widening the literal gate is
   then caught by this one, and dropping this one is caught by the `int()`
   below, which cannot read `DAT_EXTMEM_0318` as a number and skips it. There
   is no single-point edit that opens the trap, which is why the redundancy
   stays rather than being trimmed to the shortest form that works today.
   `--self-test` pins the **outcome** rather than any gate: `0x0318` is reached
   through an accessor from exactly two files, and its row keeps 14
   `DAT_EXTMEM_` references separable from 2 `pair-literal` ones out of 16.
3. **The argument must be a bare literal** — `0x…`, `FUN_CODE_…`/`DAT_CODE_…`
   or decimal, which is the form all six of the tree's decimal first arguments
   take: `900` for `0x0384` at `C931.c:26`, `C979.c:22`, `CFB1.c:24` and
   `D946.c:85`, and `1000` for `0x03E8` at `CF0B.c:23` and `CF3C.c:26`.
   Arithmetic (`DAT_EXTMEM_04ab + 0xa6` at `B224.c:37`, `DAT_EXTMEM_0577 - 6`
   at `BABF.c:39`, `DAT_EXTMEM_0514 - 2` at `CC95.c:76`), a `CONCAT11(3,bVar3)`
   index and a bare register are all the same shape — a base plus something
   this tool cannot name without guessing which one runs. For each the honest
   answer is the one the rest of this file already uses: **not found by this
   method.**

**What it resolved.** 437 call sites across 107 bank1 `.c` files, 241 read and
196 write, each contributing two adjacent references because the accessor's
`inc DPTR` is what makes the access a pair: **+155 distinct addresses, +874
references, +482 `read` and +392 `write`,** and nothing in the three buckets
that describe a handoff. The arithmetic of the first argument, counted over
every occurrence of an accessor name — 461, of which 7 are the accessors' own
parameter lists rather than calls:

| first argument | count |
|---|---:|
| bare hex, `0x434` | 416 |
| `FUN_CODE_0402` and its two siblings | 15 |
| decimal, `900` for `0x0384` and `1000` for `0x03E8` | 6 |
| **resolved** | **437** |
| arithmetic, `CONCAT11`, a register, a parameter | 16 |
| already an occurrence (`bank1/9354.c`'s `DAT_EXTMEM_0318`) | 1 |

The 214 addresses reached include 58 that also carry a token spelling and
**156 reached this way only** — within the main EC no other spelling names
them. 155 of those 156 had no `xdata-registers.csv` row at all before this
pass; the 156th is `0x04A3`, which `origin/main` already carried as a
`program=pd` row with 1 reference, and which this pass widens to
`program=both`. So against `origin/main` the census gains **155 new rows** and
**59 existing rows have a moved `refs`**, where the issue forecast 153 and 61.
`xdata-registers.csv` is the per-address enumeration of both sets. §5's new
`main-ec-001` is largely made of them. **That 58/156 is counted within one
program, and the CSV's own split of the same 214 is 59/155** — `0x04A3` is
`pair-literal` in the main EC and `DAT_EXTMEM` in the PD image, so the row's
union `spelled_as` reads it as mixed. Both numbers are right; the CSV's
`spellings_by_program` column is where the difference is shown rather than
argued, and `../../docs/findings/xdata-spelled-as-union.md` is the write-up.

**The two worked examples, as the exact multiset rather than a total.**

| address | new sites | read | write | at |
|---|---:|---:|---:|---|
| `0x0402` | 10 | 7 | 3 | `AD85.c`, `B33B.c`, `B407.c`, `B40E.c`, `B415.c`, `B41C.c`, `B43B.c` (read); `DB0B.c`, `DEE8.c`, `DEF1.c` (write) |
| `0x0408` | 3 | 0 | 3 | `DB0B.c`, `DEE8.c`, `DEF1.c`, all `write_r1r2_to_xdata_pair` |

`0x0402` is `BAT_DESIGN_CAPACITY_0` and `0x0408` is `BAT_DESIGN_VOLTAGE_1`; both
are in `../registers.yaml`, which is why a `grep '^0x0402,'` over
`xdata-registers.csv` on `origin/main` — the issue's evidence — finds nothing
while the address was documented all along. It finds the row this pass added
now; the two are the same query either side of the change. `0x0403`, the
`inc DPTR` half of the first, was already a row at 18 references, all 18 of
them reads, over 13 functions; it moves to **28 references, 25 reads, 3 writes
and 3 writers**, so it picks up a writer for the first time. All eight
`NOT_IN_TREE` entries this closes are listed in the tool: `0x0402 0x0404
0x0408 0x040A 0x040C 0x040E 0x0410 0x043A`, which is the 25-entry set becoming
17 and `named_in_tree` 167 → 175.

**Three numbers describe `0x0402`, and they are three methods.** This is the
calibration the whole issue turns on, so they are kept apart rather than left
for a reader to compare and conclude one is wrong:

| number | what counted it |
|---:|---|
| **3** | `static_refs_main_ec` in `../registers.yaml` — a `MOV DPTR` byte scan of the image, **unchanged by this pass** |
| **3** | `mov DPTR,#0x0402` + `lcall <accessor>` encodings in bank1 — the machine-code truth, and what the row above is counting |
| **10** | the census, because Ghidra emitted one block into five overlapping `.c` files |

The third is not this pass's doing and not a defect in it. `B407` forwards to
`B40E`; `B40E`, `B415`, `B41C` and `B43B` are successive seeds over
`0xB40E`-`0xB4B6`; and the `MOV DPTR,#0x0402` at `0xB4BD` is inside that span.
The census is per-`.c`-file in its counting and has always been a lower bound
on the machine code; here the same fact makes it an *upper* bound on that one
block. A de-duplication pass over overlapping decompiles is its own issue and
`--export-ownership` (§4.6) is the half of it this tree has.
`check_register_counts.py` still exits 0, which is the mechanical proof that
the first row did not move.

**The 73 zero-`MOV DPTR` high halves are deliberately not entered in
`registers.yaml`.** 107 of the addresses this pass reaches are only ever the
`inc DPTR` half of an accessor's pair, and **73 of those have no
`MOV DPTR,#addr` encoding in `common`, `bank0` or `bank1` at all**:
`0x0309 0x0311 0x0313 0x0317 0x031B 0x0333 0x0337 0x0341 0x0346 0x034F` and 63
more, running to `0x0647`. They are reached only as `param_1 + 1` inside an
accessor. The count is re-derivable with `trace_xdata_refs.sites_for` over
those three regions of `ec/firmware/GMxMGxx_11.800`, which is the same
`MOV DPTR` encoding `xdata-0400-045f.md` §4 admits a byte on — the regions are
`0x00000`-`0x08000`, `0x08000`-`0x10000` and `0x10000`-`0x18000`, and a bank
boundary read at `0x10000` rather than `0x08000` misses six of them.
`xdata-0400-045f.md` §4 admits a byte to that file's table **if and only if**
the image has at least one direct `MOV DPTR,#seed` site, and this pass does not
change that. The census is a different method and must not become a back door
into it. They have census rows — that is what this section is for — and no
`registers.yaml` entry, and no `status:` anywhere moved.

> **Update, 2026-09-25 (issue #707).** The 73 are now a committed list, the
> 107 split three ways (73 / 7 entered / 27 not), and the rule above is stated
> rather than only applied: **`xdata-inc-dptr-only.md` and
> `xdata-inc-dptr-only.csv`**, produced by `ec/tools/inc_dptr_sites.py`. The
> ten addresses named in this paragraph are the **first ten** of the 73 — the
> issue's prose called them eleven, and the eleventh is `0x0364`, which this
> paragraph does not name; §2a of that page has the correction. Two figures
> this paragraph does not give: the 73 is **71 + 2**, the two being `0x043B` and
> `0x04A5`, whose 2 and 3 pd-image sites are another program's bytes rather than
> main-EC ones; and all 73 are `pair-literal`-only in the census, carrying 196
> references between them. Nothing entered `registers.yaml` and no `status:`
> moved. The sentence above — "they have census rows and no `registers.yaml`
> entry" — is correct and stands; the issue's contrary claim that "the 73 are
> not a census figure" is retracted on §7 of that page, and the two lists that
> partition the `0x0400`-`0x045F` page's 50 meet at `0x043B` alone.

**What it does not establish.** A resolved site is a **static** read or write:
the EC reads or writes this byte in code, and nothing here is evidence the EC
*acts* on it, that the byte is a register, or that any two of the sites agree
about what the value means. The direction is the callee's, which is stronger
than reading an `=` in the caller and weaker than knowing what the pair is
for — `write_r1r2_to_xdata_pair(0x434,0,0)` stores the constant zero, and the
census records that as a write of `0x0434` and `0x0435` without recording that
it is a clear. And 155 addresses is a count of *what the decompiler emitted*:
a call site the exporter dropped, or a decompiler that spelled an address some
other way again, is still out of reach, which is the reason the `NOT_IN_TREE`
vocabulary has no word for absence.

**The self-test pins the resolved set, not a total.** `--self-test` asserts
the accessor set equals the seven names above — the six bank1 routines and
`pd:0x38D3 read_be16_from_dptr` — that every one of them still has
two `movx` in its committed `.asm` (the encoding half of the discriminator,
read back out of the tree rather than taken from the table), the exact
`(file, direction)` multiset for `0x0402` and `0x0408`, that `9354.c` is not
double-counted, that `0x0733` and `0x0735` are still unresolved, and that
`BLIND_SPOT` is unchanged. A per-address multiset fails on *which* site moved;
a bucket total would only say that something did.

## 5. The worklist, ranked

By size, then reference count, then lowest address. Full rows in
`xdata-clusters.csv`; the `addrs` column there is the complete membership.

The last column is the repository's own hand annotations for the functions
`ghidra-functions.csv` names, not this tool's reading of them — which is the
point of §6 below.

**The `key` and `name` columns are §4.4's**, and are the two ways to cite a row
of this table that survive a regeneration. `name` is empty for six of the twelve
rows because nothing outside this table's own census column names them, and an
invented name would read as a reading this file does not have.

**The ids in this table are not the ids the first version of this file
published, and almost none of that is §4.3's doing.** The writer axis is built
on direction, so removing 837 phantom writers moved the clusters, and the
ranking is by size — which reorders everything below the top. A second,
independent movement comes from the `named inside` column alone: that column
counts addresses `ec/ghidra/xdata-symbols.csv` names, and the table grew from
56 names to 101 without these CSVs being regenerated. (101 is this
paragraph's figure; `xdata-symbols.csv` holds 177 names in the tree now — 177
rows, and 177 distinct `addr`/`name` pairs, so the count is the same under
every reading — and it is that table §5's "named inside" column counts. The
branch that added §4.4 forked before the GPU-boost bytes `0x07D6`/`0x07D7`
were annotated and measured 150; the 177 here is the merged tree's.)
Sizes, reference counts and ranges are §4.3; `named inside` is mostly the
symbol table.

> **Drift record, 2026-09-24 (issue #274).** Every mechanical column of this
> table — `key`, `name`, `size`, `refs`, `range`, `named inside` — is
> transcribed from the **committed `ec/annotations/xdata-clusters.csv`**, not
> from a fresh `xdata_register_map.py` run, and four of them were **stale**
> against it. `main-ec-004` was 30 addresses / 312 references and is 26 / 278;
> `main-ec-002` had 4 named addresses inside and has 19; `main-ec-003` had
> `none` and has all 43 of its members named; and `main-ec-001` had 29 and has
> 33. **Those four ids are the 2026-09-24 table's and are left as they were
> written**, per `../../docs/findings.md` §4a: they name the census this
> record was measured against, not the one the table below carries, and two of
> the memberships they name — the 26-address row and the 19-named one — are no
> longer rows of their own in the committed census at all, so there is nothing
> to re-derive them *to*. The cause is the same as the movement the paragraph
> above describes and none of it is about the firmware: the symbol table grew
> and §4.3's regeneration moved the clusters, and this table is a transcription
> that was not re-run. The hand-written last column is unchanged and is
> unaffected — it is a reading, not a count.
>
> **The committed CSV is itself behind a fresh generation, and this table is
> the committed CSV's row for row.** A fresh run of the committed tree gives
> 430 clusters to the committed 427, and `main-ec-013` is `k66512c56e77b` /
> 52 references where this table records `k3fdd14ddea2e` / 36. The gap is the
> pre-existing census staleness `--self-test` already reports on `main` as "the
> committed CSVs match a fresh generation", not something issue #274
> introduced, and it is left visible here rather than re-transcribed away:
> transcribing from a fresh run would make this table disagree with the CSVs
> `check_cluster_citations.py` resolves it against, which is the direction
> that check exists to prevent.
>
> *(Correction, 2026-09-25, issue #256's regeneration: the gap named above has
> been closed, so this record is overtaken rather than contradicted. The
> committed CSV is no longer behind a fresh generation — both hold 430 clusters
> — and the `main-ec-013` row it contrasts against that CSV is the row the census
> now holds. What stays is the record of what this table was transcribed against
> and why it was held to the committed CSV rather than to a fresh run, which is
> the direction `check_cluster_citations.py` exists to keep. The `named inside`
> figure in the paragraph above is stale in the same way and for the same
> reason: `xdata-symbols.csv` holds 187 names, not 177.)*
>
> Issue #272 reached the same four rows independently, from the other
> direction: it put §5's hand-typed figures behind `check_cluster_citations.py`
> so they could not drift again, rather than re-transcribing them once. Both
> fixes are in this tree, and the row values above are the post-#272 ones
> re-read from the committed census — so this block is a record of the drift
> rather than of the only repair.
>
> **The drift this records is now closed, and the table below is the
> re-derivation, not a third reading of the same census.** Issue #134's merge
> regenerated `xdata-clusters.csv` from the committed tree, so the committed
> census is what a fresh generation produces and the "stale against the
> committed CSV" half of this record can no longer happen: what it found
> instead is a census that had moved underneath the table, not a table that had
> fallen behind one. Every figure in the drift record above is kept as measured
> — that is the point of a drift record, and the four rows it names are the ones
> to read if you want to know what #274 found. What the table now carries is
> the re-derived census, and the differences are not small: the counter block
> is `main-ec-003` again and the gate block `main-ec-004`, both of which §5's
> own note below and the pages that cite those ids
> (`../../docs/findings.md` §17, `xdata-06c2-06db-timers.md`,
> `xdata-086x-dispatch.md`, `manual-fan-ctrl-0751.md`) now say in correction of
> the ids they used. Two numbers in the drift record's own table are the ones
> that moved most: it read 26 addresses / **280** references, not 278, and the
> old `main-ec-003` was no longer a 44-address row at all. *Issue #279 takes
> that 26-address row one step further: it is not a row of its own any more
> either — all 26 of its addresses are inside the 152-address `main-ec-001`
> (§4.7) — so `main-ec-004` is the gate block and there is no 26-address row
> left to name.*

| cluster | key | name | size | refs | range | named inside | co-reading (§4.5) | the functions the cluster's addresses share |
|---|---|---|---:|---:|---|---|---|---|
| `main-ec-001` | `ke794087e13a6` | — | 152 | 873 | `0x0300`-`0x097B` | 10 | 37/100 fns, 479 (55%) | `FUN_CODE_dee8`, `FUN_CODE_def1`, `FUN_CODE_db0b` — **new, and the pass is what made it**: §4.7's 155 addresses are spread across this same `0x0300`-`0x05xx` working page, and the three routines whose `FUN_CODE_0402`/`FUN_CODE_0408` calls the pass resolves are the ones this cluster's addresses share. The old `0x0300`-page row is inside it (§4.7) |
| `main-ec-002` | `kefb63d82f8c7` | `mode-oem-init` | 92 | 1,130 | `0x0456`-`0x1809` | 27 | 25/136 fns, 294 (26%) | `fill_08xx_from_code_table`, `apply_oem_overrides_then_fill_08xx`, `mode_tick_084c_07a5_09ee`, `charge_target_update` — the mode/OEM initialisation set |
| `main-ec-003` | `k733222e83898` | `counter-sweep` | 43 | 4,966 | `0x0460`-`0x09CE` | 43 | **63/127 fns, 4,642 (93%)** | `decrement_nonzero_xdata_counters`, `read_06c6`, `skip_06c6_decrement` — one loop walking a block of counters |
| `main-ec-004` | `ka39cda99615f` | `level-block-086x` | 28 | 181 | `0x045C`-`0x1C3A` | 14 | 8/21 fns, 66 (36%) | `gate_06e6_442_then_sync_046a_from_086b`, `dispatch_on_0860`, `compute_level_blocks_086b_086c_086e` — the `0x06E6`/`0x0860` gate block |
| `main-ec-005` | `ka07bfc4f80cd` | — | 16 | 94 | `0x043E`-`0x300E` | `0x043E` | 6/22 fns, 34 (36%) | `FUN_CODE_9b3c`, `FUN_CODE_9c53`, `stage_3000_block_then_probe_3000_3007` |
| `main-ec-006` | `k49c52e2b2052` | — | 15 | 68 | `0x0388`-`0x03C9` | none | 0/5 fns, 0 (0%) | `mul_0342_0514_into_0388_when_03d0_lt_0384`, `FUN_CODE_d6ee`, `add_03a6_plus_0388_into_039e` |
| `main-ec-007` | `kea0c67af9b51` | `ff-fill-stubs` | 12 | 280 | `0x0045`-`0x1504` | none | 10/31 fns, 209 (75%) | three `ff_filler_not_a_function_*`, the fill stub block |
| `main-ec-008` | `ke96d2e265d5d` | — | 12 | 107 | `0x0A43`-`0x0FC3` | none | 4/8 fns, 85 (79%) | `call_ef17_then_copy_0f80_to_0fb1`, `store_dptr_byte_to_0fb2_copy_0f82`, `FUN_CODE_f002` |
| `main-ec-009` | `ka9cca0a3e2d8` | — | 12 | 37 | `0x049A`-`0x05C3` | none | 0/9 fns, 0 (0%) | `clear_049a_049e_0579_057a_05c2`, `FUN_CODE_c0a8`, `latch_0490_bit3_or_bit7` |
| `main-ec-010` | `k733571bb7f66` | — | 12 | 35 | `0x00C0`-`0x2275` | none | 0/10 fns, 0 (0%) | `copy_direct_65_66_to_x00c0`, `copy_x00c0_pair_to_iram_67_68` |
| `main-ec-011` | `k57522564ddd8` | — | 12 | 26 | `0x040A`-`0x0547` | 4 | 2/6 fns, 4 (15%) | `derive_scaled_values_from_0404`, `forwarder_to_ad8b`, `update_0492_from_0490_0524` — §4.7's `write_r1r2_to_xdata_pair(0x40a…)` block |
| `main-ec-012` | `k2a30862cf8eb` | — | 11 | 43 | `0x045E`-`0x1F07` | 4 | 8/21 fns, 3 (7%) | `magic_55aa_and_0704_countdown`, `init_1f01_1f06_1f07`, `count_down_06e4_and_toggle_06e3` |

The `co-reading` column is §4.5's `co_reading / functions_touched` and
`co_reading_refs` as a share, and it is a column rather than a re-sort because
nothing about the ranking moved: the order is still `(size, refs, lowest
address)`, and the two of those three the new columns could have disturbed are
untouched. `main-ec-003` is the row the whole section is about — 93% of its
references come from the one 42-file group — and `main-ec-007`/`main-ec-008` at
75% and 79% are the two that were not obvious from the size column. Four of the
twelve have no co-reading source at all, which is the other half of the
answer: the export artefact is concentrated, not general.

**Three rows are not the twelve this section was written about, and each is
worth a sentence because the reason is different.** `main-ec-001` is new and
large; `main-ec-002` lost 17 addresses to it; and the `0x0300`-page row is
gone as a cluster of its own. §4.7 is where all three are derived, and the
short form is that §4.7's 155 new addresses fall on the same `0x0300`-`0x05xx`
working page the old small clusters sat on, so the graph there got denser and
three components merged into one. That is the clustering doing what a
connectivity threshold does when the graph around it gets denser — and it is a
statement about the export's co-occurrence structure, not about the firmware
merging three unrelated blocks into one.

*(Re-derived again, 2026-09-25, for issue #279. The superseded version of the
table above, kept rather than deleted, is the one §4.7's pass replaced: twelve
rows of a 430-cluster census, headed by `main-ec-002`/`k7497cf885614` at 109
addresses / 1,150 references, and including two rows that no longer exist as
clusters — `kffd18a7555bf` (26 addrs, the three `FUN_CODE_dee8`/`_def1`/`_db0b`
routines, now inside `main-ec-001`) and `k3fdd14ddea2e` (`page-0300`, 9 addrs,
now nine addresses inside the same `main-ec-001`). The two earlier
re-derivations, 2026-09-24 and 2026-09-25, are in the paragraphs below and are
left as they were.)*

*(Re-derived on the merged tree, 2026-09-24. These twelve rows are the twelve
largest clusters of the 430-row census, re-sorted, and three of them changed
home: the counter-loop cluster and the `0x0860` gate block each changed number,
and the `0x0875`-`0x09E7` and `0x0300` rows both landed on the same rank because
a new 11-address cluster over `0x045E`-`0x1F07` took the id between them. **This
paragraph cites `cluster_key` rather than `cluster_id` where it names a cluster
of a superseded tree, and that is §4.4's own remedy rather than a new
convention:** a rank is a fact about one ranking, and a re-derivation moves it.
The keys are `k66512c56e77b` for the `0x0875`-`0x09E7` row, `k3fdd14ddea2e` for
`page-0300`, and `k2a30862cf8eb` for the 11-address cluster. The two that
swapped did not trade places by accident: the old top cluster split, and the
`addrs` columns of `xdata-clusters.csv` are where the three pieces of it are —
28 addresses in the gate block, 11 in `k2a30862cf8eb`, and `0x044C 0x05F0
0x05F1 0x0841` in what is now `main-ec-055`. A reader who remembers the gate
block by rank is reading a table that no longer exists; the cluster that
sentence is about is `ka39cda99615f`.)*

*(Re-derived again, 2026-09-25, on the tree that also carries issue #267. Only
`main-ec-002` moved, and only because `0x1666` and `0x166A` became named: #267
added `registers.yaml` rows for the three GFID-select bytes, and two of them
sit in this cluster, so 35 → 37 named addresses. The reference count follows the
new `0x1665` test routines (1,149 → 1,150) and the co-reading denominator is
`functions_touched` 133 → 134, the four `bank0` functions #267 seeded. The share
is unchanged at 26%, the key is unchanged, and no other row of the twelve
moved.)*

*(The `key` and `name` columns are §4.4's, and they are the reason two of these
rows can still be cited after this table moved. Three of the ten names in
`xdata-cluster-names.csv` were re-keyed with it: `mode-oem-init` gained an
address (Jaccard 0.99), `user-clear-bytes` lost one (0.90), and
`level-block-086x` followed one half of the split above (0.64 — the weakest of
the three, and the one that is a choice among the pieces rather than a
consequence of the census. Its row in the names file says so.) `counter-sweep`
needed no re-key: the counter block's membership did not move, only its rank
and its reference count, 4,965 to 4,966. The ids, keys and counts in the table
are the committed CSV's, and the committed CSV is what a fresh generation
produces — `--check` exits 0 on this tree, where it exited 1 on both sides of
this merge.)*

`main-ec-002` is the one that matters most and the one most likely to be
misread. It is where 33 named registers land, so it looks like "the named
registers, discovered again", but what the clustering actually found is that
the *initialisation* routines touch them all: a cluster is a co-occurrence, and
109 addresses reached by one mode tick and one OEM override pass is a statement
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
  evidence about *shape*, not about *meaning*. The figures are `main-ec-004`'s,
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
- **The corpus-wide direction invariant is a second code path over the same
  text, not an independent reading of it.** §4.3's third assertion covers 5,662
  occurrences across 1,008 addresses and catches the `==`-as-store mistake on
  any of them, which is far wider than the five hand-checked rows. What it
  establishes is a *shape*: that an assignment, rather than a comparison,
  follows the address. It is measured over the same files, by the same regex,
  with the same `strip_comments()`, against the buckets this tool itself
  produced, so a store the decompiler spelled wrongly, a write through a
  pointer, or a per-address count that is wrong while every occurrence looks
  like an assignment all pass it. It raises the floor under the classifier; it
  does not certify the decompiler's spelling, and it is not a second opinion
  from outside this tool the way the five hand-read addresses are. The narrow
  net is kept for exactly that reason, and `HAND_CHECKED`'s comment says what
  the five are for and which shape they leave uncovered.
- **A co-reading group is a count of files, not a count of routines (§4.5).**
  Two `.c` files naming the same eight XDATA addresses are *similar*, and a
  connected component of that relation is *connected*; neither is one routine,
  and the relation is transitive by component, so a group's members need not
  resemble each other pairwise at all. The six-file `bank0` group around
  `0x8749.c` has a one-address common core and 1,969 listing bytes between its
  members, which is the counter-example in one row. So `co_reading` is not a
  count of "copies" and `sources_beyond` is not a distinct-source count in any
  sense a register reading could be built on: it is the number of source files
  this relation cannot pair, and a file can be in a group and still be a
  routine in its own right. `0x0440` is the control — 46 of its 91 sources in
  groups, **45 not** — and no `refs` value, bucket total or cluster id moved to
  produce any of it.
- **The relation is a property of this export, and a re-export would move it.**
  A group is a set of `.c` files; the decompiler's function boundaries are
  hypotheses (`bank-call-audit.md` §1, an upper bound rather than a partition),
  so a different export is a different set of groups over the same firmware.
  This is the same reason §4.4's `cluster_key` and not `cluster_id` is the
  durable citation: a group has no key of its own, and the honest way to cite
  one is by its members and its `index.csv` listing sizes, which is what
  `--co-reading-group-table` prints.
- **The `callees` column over-counts depth.** A name in a call position
  anywhere in a function's body counts as its callee, so a callee of a callee
  is credited to the outer function. It is a name-frequency column for picking
  a place to start reading, not a call graph.
- **`address-taken` is a one-character test, and `&&` satisfies it.**
  `classify()` asks only whether the text before the token ends in `&`, and
  tests that *before* it reaches the store rule, so the second `&` of a boolean
  `&&` files a plain comparison under `address-taken` instead of `read`. There
  is exactly one such site in the committed tree — `bank0/A747.c:25`
  (`:24` on the tree §4.3's correction was written against; see the correction
  block above), `DAT_EXTMEM_076a` — so §4.1's 267 is 266 genuine
  `&DAT_EXTMEM_xxxx` and one comparison. (This bullet said 271 / 270 when §4.1's
  table was written against the older census; both are re-derived on the
  committed tree, where the one misfiled site is still `bank0/A747.c` and the
  arithmetic is 266 / 1.) No total
  is restated here, because none was recomputed for it and the census the CSVs
  publish is the tool's own buckets either way; the fix is
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

### 7.1 The nine references the annotation layer moved, address by address

PR #238 lowered the census by nine C-level references and the first thing a
reader owes them is whether that is a loss. **It is not: none of the seven
addresses is gone from the machine code.** All of them still carry their
`mov DPTR,#addr` site or sites in `ec/firmware/GMxMGxx_11.800`, counted with
`trace_xdata_refs.sites_for()` and split per image exactly as
`check_register_counts.py` splits it.

What moved is the *spelling*. This census is a token pattern —
`occurrence_re()` in `xdata_register_map.py` matches `DAT_EXTMEM_([0-9a-fA-F]{4})`
plus the names in `xdata-symbols.csv`, and nothing else — so it cannot see an
address the decompiler spells as arithmetic or as a register name. The `.asm`
sites are the ground truth and the C is a reading of them, which is the same
order this file takes everywhere else.

| address | `.asm` sites | main EC | PD | census `refs` after |
|---|---:|---:|---:|---:|
| `0x0390` | 1 | 1 (`bank1`) | 0 | row gone |
| `0x0391` | 3 | 3 (`bank1`) | 0 | 2 |
| `0x04AB` | 16 | 16 | 0 | 30 |
| `0x07D8` | 34 | 1 | 33 | 28 |
| `0x08AD` | 7 | 7 (`bank0`) | 0 | 10 |
| `0x07D0` | 254 | 0 | 254 | 41 |
| `0x07C9` | 15 | 0 | 15 | 23 |

- **`0x0390` — reference moved, and the R2 store beside it is a dead load.**
  `bank1/E100.asm:70` is the site's `mov DPTR, #0x390`. `E100.asm:72` moves the
  byte into R2, and *that* R2 is dead: `9EA1` reads R1, R3, R4, R5, R6 and R7
  and never names R2, and `E100.asm:100` overwrites R2 with no intervening
  read. But the same site hands the **address** to the callee as R3:R4
  (`E100.asm:73-74`), and `0x9EA1` dereferences that pair — reading it at
  `9EA1.asm:19` and writing it at `9EA1.asm:43`. So the dead store is a sibling
  of a live reference, not the whole of it, and the byte has both a reader and
  a writer. The C spells neither: the callee renders the pair
  `CONCAT11(r4_value,r3_value)` (`9EA1.c:35`, `:49`) and the call site passes
  only the constants `0x90, 3` (`E100.c:51`). `0x0390` now has a
  `registers.yaml` row (`XDATA_0390`, `present-untested`) and a `.asm` witness
  in `--self-test`.
- **`0x0391` — reference moved**, by the same mechanism one byte up, and it has
  three sites: `E237.asm:33`, `E100.asm:67`, `DB0B.asm:101`. The census's two
  surviving references are the `E100` read and the `DB0B` write. The one that
  left is the `E237` call site's R2 argument, whose value that same site hands
  the callee as R3:R4 (`E237.asm:36-37`) — alive exactly as `0x0390` is, and
  `E237.asm` likewise writes R2 once at line 35 and never reads it. The census
  row understates the byte.
- **`0x04AB` (-3) and `0x08AD` (-1) — reference moved**, the same class, and
  not new: 16 and 7 `.asm` sites against 30 and 10 C references. Both have been
  partly out of the token pattern's reach for some time, in places the
  decompiler spells arithmetically.
- **`0x07D8` (-3) — reference moved, and the symbol layer is involved.** It is
  `MODE_TCC_OFFSET_DEFAULTS_GAMING_0` at `xdata-symbols.csv:100`, so part of
  the movement is `DAT_EXTMEM_`-to-symbol renaming and part is the arity change.
  1 main-EC and 33 PD `.asm` sites against 28 C references.
- **`0x07D0` (-1, PD) — reference moved.** 254 PD `.asm` sites against 41 C
  references. `gen_xdata_symbols.py` refuses to name the PD image, so this one
  stays `DAT_EXTMEM_`-spelled and its movement is not a symbol effect.
- **`0x07C9` (+1, PD) — not an annotation effect, and not unexplained either.**
  This is the one that gained, so it is worth being exact about. Across the
  #238 merge the only one of the two files the census names for this address
  that moved is `ec/decompiled/pd/7B14.c`, 21 -> 22 `DAT_EXTMEM_07c9` tokens;
  `EA67.c` and `7B14.asm` are byte-identical across the merge, and `0x7B14` has
  no row in `ghidra-functions.csv` or `ghidra-variables.csv`, so no annotation
  touched it. The added token is the statement `cVar2 = DAT_EXTMEM_07c9;`, and
  the old call's first argument, the constant `0x1c`, is gone from the C —
  while `7B14.asm:233-234` still shows `clr A` / `add A, #0x1c` building it. By
  this tree's own rule that makes the new C a *worse* reading at that argument.
  So the census gained a C-level token that does not correspond to a new
  machine access, and dropped a constant it had been printing correctly. What
  made Ghidra re-render the file is not recorded in the committed tree — there
  is no annotation on `0x7B14` to point at — and that is the honest limit of
  this account.

**The policy these seven lines settle.** A variable row may change a caller's
arity, and that is a correction rather than a loss: the committed four-argument
signature is the one that matches the listing, and the fifth argument the
decompiler used to promote was an unconsumed scratch register. The census
counts C-level references and is therefore a lower bound on the machine code; a
pin moves only with a measured reason recorded in the same change; and an
address that leaves the census is "not found by this method" until an `.asm`
witness says otherwise. The same rule is written where an annotation author
meets it — `ghidra/scripts/ApplyAnnotations.java`, `ec/annotations/README.md`,
and `../../docs/findings.md` §18.

**The measurement, which is the part that was actually open.** Issue #259 added
the `XDATA_0390` row, so `xdata-symbols.csv` names the byte and
`ApplyAnnotations.java`'s `createData` defines it. Re-running the export in the
default export-only mode moved no `.c` and no `manifest.csv` row: the export is
byte-identical to the committed tree, the decompiler still renders the pair as
`CONCAT11`, and the census does not rise. `ORACLE` and `BUCKET_TOTALS`
therefore stand as committed, and the transcript in §1 carries a `0x0390`
witness that fails if *either* half of the fact stops being true — the site
still in the `.asm`, and the census row still absent.

### 7.2 The 88 rows moved six addresses, and the pins were already 26 behind (2026-09-25, issue #263)

§7.1 is the first time an *annotation* moved this census. It is the second, and
it moves less: **14,818 → 14,819 references over six addresses**, with
`distinct` unmoved at 1,171.

| address | before | after | Δ |
|---|---:|---:|---:|
| `0x07D6` | 37 | 36 | −1 |
| `0x07F3` | 133 | 132 | −1 |
| `0x0832` | 78 | 77 | −1 |
| `0x086F` | 24 | 28 | **+4** |
| `0x0A56` | 108 | 109 | +1 |
| `0x0F80` | 6 | 5 | −1 |

The mechanism is §7.1's, running in the direction #238 did not see.
`ec/annotations/ghidra-variables.csv` grew by 88 rows, each of which commits a
function's signature, and a committed signature changes how many arguments the
decompiler infers **at the call sites**. Measured by diffing the declared
placeholders of every `.c` against a pristine checkout of the parent commit:

- **86** of the 88 functions lost their `param_1` — the two `kind=unresolved`
  rows keep theirs on purpose.
- **17** functions this batch never annotated lost one each (−17).
- **11** functions this batch never annotated gained parameters (+25).

Net −78 against the −86 the renames account for, which is arithmetically the
census's own Δ and is the reason the address list above is six rows and not 88.
Two worked examples, both committed in the diff:

- `ec/decompiled/common/7401.c` **lost** an argument. It used to call
  `store_a_then_clear_08e0(0x80, param_1)`; committing that callee's signature
  made the decompiler read the second argument as a pointer constant,
  `(undefined1 *)0x1905`, so the caller no longer needs a parameter at all and
  its signature is now `void FUN_CODE_7401(void)`.
- `ec/decompiled/pd/F4CD.c` **gained** one. `store_a_to_dptr(0)` is now
  `store_a_to_dptr(0, (undefined1 *)0x7d6, param_1)`, and the caller's own
  accumulator became an argument.

**None of the six addresses is gone from the machine code**, and none is here
for the first time: `verify_reassembly.py --check` passes with 0 disagreements
over 45,624 instructions, which is what makes "the census moved because of the
annotation, not the code" checkable rather than asserted. `0x07D6` and `0x07F3`
are §4.4's own example addresses and `0x086F` is the fan-control byte the
`0xA87x` handlers mask, so all three are already carried.

**And the pins were already wrong before any of this.** Run against a pristine
checkout of the parent commit, this census read 14,818 references against a pin
of 14,792, `named_in_tree` 153 against 150, and `BUCKET_TOTALS` read 8,333 /
passed-to-call 538 against 8,317 / 543. `xdata_register_map.py --self-test` was
red on `main` for that reason, not because of this batch. The pins are now set
to what was measured; the dated comment block above `ORACLE` carries the
pre-existing drift and this batch's +1 as two separate rows, because folding
them into one number would credit this issue with 26 references of drift it
did not cause and hide a red gate behind a green one.

**One failure is left, and it is not this issue's.** The `NOT_IN_TREE`
assertion wants every address `xdata-symbols.csv` names and the census does not
reach to carry a recorded reason, and **`0x07C7` and `0x07C8` do not**: both are
`unknown-not-absent` in `registers.yaml` with `static_refs: 0`, and no reason
row was written for either. That is true of the parent commit identically, and
adding the two reasons is a finding about two addresses rather than a
re-measurement, so it is left for its own issue rather than folded in here.

## 8. What follows

- **A longer callee name can move a reference between `read` and
  `passed-to-call` without the firmware changing (2026-09-24, issue #134).**
  Naming `bank1 0x8863` `cmp_r3r4_against_r1r2_16bit` made Ghidra wrap four of
  its call sites across two lines, because the name is longer than
  `FUN_CODE_8863` and the decompiler breaks before the argument list:

  ```
        cmp_r3r4_against_r1r2_16bit
                  ((char)((ushort)DAT_EXTMEM_039a * 10), ...);
  ```

  The census's call-site pattern is line-based, so on the wrapped lines the
  argument no longer reads as "passed to a call" and falls back to `read`. Five
  cells move and **no total moves**: `0x039A` 5 refs, `read` 0→4 and
  `passed-to-call` 4→0; `0x04BE` 4 refs, `read` 2→3 and `passed-to-call` 1→0.
  Read it as a classifier limit, not as a change in what the code does — the
  same pattern that put `bank0 0xCD64`'s callers in the wrong bucket for 838
  rows in §4.3, and with the same consequence for a reader: **a `read` that is
  really a call argument is a lower-bound artefact, not a second read.** The
  fix is to join the wrapped line before matching, which belongs in its own
  issue rather than inside a change about naming call-graph callees.

  The rest of the drift in this regeneration is **not** issue #134's. Naming
  `bank0 0xCC64` in the previous commit (#310) moved 72 numeric cells over 16
  addresses: 58 across `0x0490`, `0x06E6`, `0x0743`, `0x0786`-`0x0788`,
  `0x07C5`, `0x07D5`, `0x08A5`, `0x08A6`, `0x08EB`, `0x0988` and `0x09CE`, and
  the other 14 across `0x0495` (refs 34→36, read 20→22), `0x0498` and
  `0x049D`. And `xdata_register_map.py --check` was already failing on `main`
  before this change began. Verified by regenerating at `HEAD` in a clean
  worktree and diffing. Those moves are recorded here because this
  regeneration is what first commits them; the addresses themselves are
  unchanged, and the `main-ec-002` cluster grew 108→109 functions and
  1,136→1,149 sites because `0xCC64` joined it.

- One issue per cluster in §5's first twelve rows, each scoped to reading the
  functions in it and ending at whatever the code settles — with the live-test
  step written down as a human's where the code does not settle it.
- The top ten addresses by reference count get folded into the `main-ec-003`
  issue rather than opened separately: nine of the ten are in that cluster
  already, and the tenth is the `0x0440` singleton, so the cluster reading and
  the address reading should not be two efforts over the same code. (This bullet
  read `main-ec-004`, which was right for the census the first version of this
  table was written against and is wrong for the one committed here: the nine
  are in the counter block, which is `main-ec-003` after the 2026-09-24
  re-derivation. §5's table is the one to read an id from.) Note that
  the cluster ids moved when §4.3 landed and again when the census was
  re-derived, so any follow-up issue opened against
  an id from the first version of this table is pointing at a different cluster
  — re-read `xdata-clusters.csv` before scoping one. **Open it against the
  `name` column, not the `cluster_id` column** (§4.4): a name is a function of
  the cluster and follows it through a regeneration in changed form, an id is a
  rank and does not. `../tools/xdata_register_map.py --map <old clusters CSV>`
  is what says where an id went, and the name column in its output is what an
  issue should quote.
- `xdata_register_map.py --check` belongs in `check_ghidra_tooling` in
  `.github/scripts/agent-gates.sh`, next to `gen_xdata_symbols.py`'s `--check`.
  Both modes need no Ghidra, no network and no image, which is what makes them
  affordable in that gate; `--reconcile` does need the image and is
  deliberately not in the list. **Partly done by #256:** the `--check` half is
  wired (that bullet's "a human makes that one-line change" was itself stale —
  `.github/scripts/` is pushable, only `.github/workflows/` and
  `.github/actions/` are not). **The `--self-test` half is still open and is
  not a one-liner:** `--self-test` is red on `main` for a reason that predates
  any co-reading work, so wiring it would turn the gate red for an unrelated
  cause. The failure is one assertion — *"the annotation CSV and index.csv
  agree on every address they share"* — and it is real:
  `ec/annotations/ghidra-functions.csv` names `bank1:0x9CE8`, `bank1:0x9D53` and
  `bank1:0xE2D3`, and `ec/decompiled/index.csv` still spells all three
  `FUN_CODE_*`, because the export has not been re-run since those renames
  landed. Clearing it means `python3 ec/tools/build_ec_decompile.py --work
  <scratch>` in its default export-only mode, which rewrites the generated
  `ec/decompiled/**` tree, and that belongs to whoever added the renames rather
  than to a measurement issue: it would sweep every annotation landed since the
  last export into whatever diff it rode in on. Until that run happens,
  `--check` is the half that can be gated. Two other suites that read these
  CSVs are red for their own separate reasons and are not in that loop either:
  `test_xdata_cluster_names.py` patches a literal `if stripped.startswith("==")`
  that the tool's `--no-eq-guard` switch grew an `eq_guard and` conjunct in
  front of, and `test_check_site_census.py` wants 14 mapped `0x0860` sites at
  `bank0/D091.c` line numbers the file has moved past.

  > **CORRECTION (2026-09-25, issue #752) to the second of those two:** it is
  > green. The `xdata-0860-census-sites.csv` rows cited `bank0/D091.c` lines
  > `44, 48`, `70, 71`, `74, 75, 76` and `82`, and #180's CORRECTION header
  > rewrite on 2026-09-24 moved them again — by one for the `==` lines and by
  > two for the dispatch argument — after #281 had corrected the same numbers
  > in `HAND_CHECKED`'s comment earlier the same day. The four rows now cite
  > `45, 49`, `71, 72`, `75, 76, 77` and `84`. No `census_count` moved: all 17
  > occurrences and every bucket total in this section are unchanged, because the
  > header rewrite added *lines* and added, removed and reflowed no comparison.
  > The sentence above is left as it was written rather than edited to the new
  > figure, for the §4a-4d reason, and the set is re-derived by running
  > `tools/run-tests.sh` rather than by editing the prose. That leaves **one**
  > suite of the two red, and `docs/findings/runner-red-suite-set.md` is the file
  > that tracks the set. Nothing about the firmware is established by the
  > correction; `XDATA_0860` stays `present-untested`.
  >
  > **(Correction, 2026-09-25, issue #819) — the set is empty, so the paragraph
  > above names two suites that are both green, and this block's own closing
  > clause goes with it.** `python3 -m unittest discover -s ec/tools -p
  > 'test_xdata_cluster_names.py'` runs 28 tests, `OK`; `python3 -m unittest
  > discover -s ec/tools -p 'test_check_site_census.py'` runs 45, `OK`; and
  > `bash tools/run-tests.sh` prints `All 30 suite(s) passed`. **The two were
  > cleared by two different commits rather than by one**, which is why the
  > paragraph above is wrong twice over and each half is wrong for its own
  > reason. The `test_check_site_census.py` half is the one this block has
  > already retracted — those four rows cite the lines `D091.c` has since
  > `23240095` — and that correction stands, unchanged. The
  > `test_xdata_cluster_names.py` half describes a **recipe that no longer
  > exists**: the suite patches no literal at all now, it runs the committed
  > tool with `--no-eq-guard` (`../tools/test_xdata_cluster_names.py:68-90`,
  > `guard_off()`), which is #753's own change and is written up in
  > `../../docs/findings/xdata-cluster-names-guard-off-recipe.md` (`64dbde19`).
  > So `../../docs/findings/runner-red-suite-set.md` is now tracking a set with
  > no members, and the whole measurement is in
  > `../../docs/findings/xdata-green-set.md` — which also covers the tool's two
  > modes, phrased as red on the sibling page and corrected there. **The same
  > commit also falsified #816's "only working scripted route to a guard-off
  > census"**, so this paragraph and that page went stale together; that
  > sentence is left to #816, and the `--self-test` half of the bullet above to
  > #815, because each is mid-way through its own issue.
  >
  > **CORRECTION (2026-09-25, issue #815) to the `--self-test` half being
  > "still open and is not a one-liner":** it is wired, and the reason this
  > bullet gave for not wiring it is false. `--self-test` exits **0** on the
  > committed tree — measured at `64dbde1`, 5.11 s and 101 assertions ending
  > `all assertions passed`, against `--check`'s 2.03 s. The `FUN_CODE_*` claim
  > was already untrue when written, for the reason
  > `docs/findings/thunk-prefix-collision.md:271-289` records from the rename
  > side: `ec/decompiled/index.csv:996`, `:999` and `:1333` have read
  > `seed_1c12_trio_or_update_1c11_1c15_1c16`,
  > `seed_1c12_trio_9f_or_run_0x9d7a_ladder` and
  > `dispatch_036c_low3_then_seed_1c00_block` for `bank1:0x9CE8`, `0x9D53` and
  > `0xE2D3` for a while. No `build_ec_decompile.py` run was needed to clear
  > it, and the export-only rewrite this bullet warned about was not the
  > mechanism. `agent-gates.sh` now runs both modes, so "until that run
  > happens, `--check` is the half that can be gated" no longer describes
  > anything. The two suites this bullet closes with are untouched by it.
  > Measured, with the commands, in
  > `docs/findings/xdata-census-self-test-gate.md`.
- **The 42 boundaries, now that §4.5 measures them.**
  `build_ec_decompile.py --mode rebuild-project` writes the 7 MB database, and
  two branches that both rebuild one cannot merge, so this still wants a branch
  of its own — but it is no longer a bare "the census double counts" note. Two
  things are measured and re-derivable: the sweep is one co-reading group of
  exactly 42 files whose `index.csv` sizes sum to 393 with 16 one-instruction
  listings, and collapsing the groups moves `main-ec` from 380 clusters with a
  109-address largest to 466 with a **150**-address largest that takes in 30 of
  the sweep's 43 addresses and pushes the other 13 out (`--collapse-co-readings`).
  Neither is the boundary fix, and adopting the collapsed counts on the strength
  of either would be deciding the question with a count of files. The second
  figure is also the argument *against* adopting them: de-duplicating the
  sources makes the largest cluster **bigger**, not smaller, so the collapse is
  not the tidying-up the "it's just double counting" reading assumes.
- A cluster that turns out to be a record table should say so in
  `pd-index-geometry.md`'s terms (base and stride, then the field layout), not
  here.
- **The day §4.3's corpus-wide invariant names rows, the work is to hand-read
  those rows, not to widen the check.** It currently holds across all 1,008
  addresses with a write or read+write reference and no exemptions, so this is
  the path, not a live task. If a future export or a future `classify()`
  change makes it fail, its message names every offender as `file!line
  address`: take each one and read the decompiled C at that line. A row the
  reading confirms and the tool gets wrong becomes a `HAND_CHECKED` entry, and
  if any prose here quotes the wrong figure a `*** CORRECTION ***` goes beside
  it in the form of the block above. A row where the *second pass* is the thing
  that is wrong is a bug in `assign_after()` and is fixed there — an exemption
  list inside the invariant is the five-address problem at larger scale, and an
  unrecorded one is worse than not checking.
- **`classify()`'s `&` test should learn to tell `&&` from address-of.** It
  files a boolean `&&` under `address-taken`, which is the one occurrence at
  `bank0/A747.c:25` that §4.3's 838 could not correct (§6's bullet, and the
  correction block above). The fix is one clause — `left.endswith("&") and not
  left.endswith("&&")` — and it moves one reference from `address-taken` to
  `read` (267/8,341 → 266/8,342, the committed cells; §4.1's table carried
  271/8,319 when this was written) and touches no other bucket, so it is a
  re-run and a diff of two numbers rather than a re-derivation. It belongs in
  its own issue: the ordering is pre-existing on `main`, it is not a regression
  from #206, and folding it in here would put an unrelated classifier change
  inside a correction about `==`.
