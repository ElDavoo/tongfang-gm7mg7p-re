# Every all-`0xFF` listing in the export, and the byte scan that made seventeen of them (issue #561)

Thirty listings in `ec/decompiled` are an unbroken `0xFF` run: every
instruction line's first byte is `ff`, which the 8051 map fixes to `MOV R7, A`
and nothing else, so each is a listing of `mov R7, A` repeated with no `ret`, no
branch, no transfer and no XDATA access. **Twelve** carried a row in
`ec/annotations/ghidra-functions.csv` saying so. **Eighteen carried none**, and
nothing else in the tree recorded that they were fill rather than functions.

Seventeen of the eighteen are `common` listings inside one unprogrammed band;
the eighteenth is `pd,0012`, which issue #489 already covers. All seventeen were
put there by a *byte scan* — `seed_basis=call-target` in
`ec/decompiled/index.csv`, every one of them, and the only exported functions
anywhere in `common`'s `0x728F`-`0x7FFF` band. The census below measures what
that scan matched, and the answer is: **28 byte patterns, none of them at an
instruction boundary.** That is a result about the byte scan's reach, not about
the firmware.

Every figure here comes from `python3 ec/tools/census_ff_fill.py`, which reads
committed files only and writes none. **Nothing here is a behavioural claim.**
No register `status:` changed, no listing was re-read, no Ghidra export ran, and
nothing was observed on hardware.

## The census

`ec/tools/citation_callers.py`'s `is_fill` is the only implementation of "is this
listing fill" in the tree, and this census imports it rather than reimplementing
it — so the 30 here and the 30 `call_graph.py` counts for its `fill-at-citer`
veto are the same population by construction, not by two tools happening to
agree.

Before this change: **30** fill listings, **12** annotated (seven
`unimplemented_ff_fill_*` in `bank1`, five `ff_filler_not_a_function_*` in
`bank0`), **18** unannotated. After it: **29** annotated, **1** unannotated,
and that one is `pd,0012` — #489's, deliberately left out of this diff and
reported here rather than dropped.

The eighteen, with the facts each row now carries. `insns` is the instruction
count re-read out of the listing; `size` is the same number as
`ec/decompiled/index.csv` records it, and the two agreeing is the check that the
listing did not move.

| scope | addr | listing span | insns | size | `seed_basis` | annotated | nearest entry below / above |
|---|---|---|---:|---:|---|---|---|
| common | 7401 | 7401-7403 | 3 | 3 | call-target | no → yes | 7281 / 7404 |
| common | 7404 | 7404-7404 | 1 | 1 | call-target | no → yes | 7401 / 7405 |
| common | 7405 | 7405-7407 | 3 | 3 | call-target | no → yes | 7404 / 7408 |
| common | 7408 | 7408-740F | 8 | 8 | call-target | no → yes | 7405 / 7410 |
| common | 7410 | 7410-7414 | 5 | 5 | call-target | no → yes | 7408 / 741C |
| common | 741C | 741C-742C | 17 | 17 | call-target | no → yes | 7410 / 7602 |
| common | 7602 | 7602-7612 | 17 | 17 | call-target | no → yes | 741C / 7848 |
| common | 7848 | 7848-7858 | 17 | 17 | call-target | no → yes | 7602 / 7883 |
| common | 7883 | 7883-7893 | 17 | 17 | call-target | no → yes | 7848 / 7BFF |
| common | 7BFF | 7BFF-7C01 | 3 | 3 | call-target | no → yes | 7883 / 7C02 |
| common | 7C02 | 7C02-7C12 | 17 | 17 | call-target | no → yes | 7BFF / 7DF2 |
| common | 7DF2 | 7DF2-7E00 | 15 | 15 | call-target | no → yes | 7C02 / 7E01 |
| common | 7E01 | 7E01-7E11 | 17 | 17 | call-target | no → yes | 7DF2 / 7F01 |
| common | 7F01 | 7F01-7F01 | 1 | 1 | call-target | no → yes | 7E01 / 7F02 |
| common | 7F02 | 7F02-7F11 | 16 | 16 | call-target | no → yes | 7F01 / 7FF1 |
| common | 7FF1 | 7FF1-7FFE | 14 | 14 | call-target | no → yes | 7F02 / 7FFF |
| common | 7FFF | 7FFF-7FFF | 1 | 1 | call-target | no → yes | 7FF1 / **none** |
| pd | 0012 | 0012-0012 | 1 | 1 | annotation | no — #489 | 000B / 0013 |

**`none` above `0x7FFF` is a fact, not a gap**: `0x7FFF` is the last byte of the
common area, so there is nothing above it to name. Every "nearest entry" is the
closest row in `ec/decompiled/index.csv` for the same program, in either
direction.

All seventeen `common` rows also carry `also_in=bank1`, and
`ec/decompiled/index.csv` records `common=yes` for each — the common area is
shared, and `ec/tools/make_bank_image.py` grafts the one `0x0000`-`0x7FFF` image
at file `0x0000` onto **both** bank images rather than there being two
byte-identical copies. One set of bytes, two programs that can both reach it.

## Byte confirmation

Every byte of every fill listing's span — 377 bytes across the 30 spans, 172 of
them inside the seventeen — is read from `ec/firmware/GMxMGxx_11.800` through
`build_ec_decompile.file_offset`, and **every one is `0xFF`**. That is a
separate read from `is_fill`'s, and deliberately so: `is_fill` asks what
instructions Ghidra drew, this asks whether the image holds those bytes. They
agree everywhere here, and the place they could disagree is the place a listing
that does not match the firmware would show up.

The enclosing run is measured, not assumed from a listing. A listing is a
function boundary the byte scan drew; the pad is not bounded by it —
`common/7401.asm` stops at `0x7403` because `0x7404` is another seeded
function, not because the fill ends there.

| pad | bytes | listings in it | byte below | byte above |
|---|---:|---:|---|---|
| `common` file `0x0728F`-`0x07FFF` | 3441 | 17 | `0x22` at `0x728E` | the common window ends here |
| `bank0` file `0x0F4CE`-`0x0FDFF` | 2354 | 3 | `0x22` | `0xE4` |
| `bank0` file `0x0FF01`-`0x0FFFF` | 255 | 2 | `0x22` | the bank window ends here |
| `bank1` file `0x17460`-`0x17FFF` | 2976 | 7 | `0x44` | the bank window ends here |
| `pd` file `0x2000E`-`0x20012` | 5 | 1 | `0x94` | `0x02` |

The band is **`0x728F`-`0x7FFF`, 3441 bytes, all `0xFF`** — measured, and not
`0x7400` as the issue's title has it: `0x7400` is simply the lowest address the
call-target scan happened to seed. `0x728E` is `0x22`, the `ret` that ends
`ec/decompiled/common/7281.asm`; `0x8000`, bank 0's first byte, is `0xE4`.

## Provenance: what the byte scan actually matched

`ec/annotations/bank-call-targets.csv` holds **28 rows** naming the seventeen
addresses — every one covered, all of them bucket A. By caller region: `common`
20, `bank1` 5, `bank0` 3. Classified against the committed listings:

| | count |
|---|---:|
| at an instruction boundary | **0** |
| inside another instruction | **22** |
| no committed listing covers the site | **6** |

The three worked examples, read byte by byte, and each is the scan reading a
`call`'s three bytes out of two unrelated instructions:

- **`common`, site `0x7159`, `lcall` → `0x7401`.** `common/7151.asm:12` is
  `7158  70 12  jnz 0x716c` and `:13` is `715A  74 01  mov A, #0x1`. The `12`
  at `0x7159` is that branch's rel8 operand, and the `74 01` at `0x715A` is the
  next instruction's opcode and immediate. Read as an `lcall` they spell
  `12 74 01` → `0x7401`, which is unprogrammed.
- **`bank1`, site `0xD756`, `ljmp` → `0x7E01`.** `bank1/D6EE.asm:68` is
  `D755  50 02  jnc 0xd759` and `:69` is `D757  7e 01  mov R6, #0x1`. Same
  shape: the `02` is a rel8, the `7e 01` is a `mov` immediate.
- **`bank0`, site `0xE716`, `lcall` → `0x7F01`.** `bank0/E6F4.asm:26` is
  `E715  7b 12  mov R3, #0x12` and `:27` is `E717  7f 01  mov R7, #0x1`.

**The 6 sites under no listing are reported, not dropped.** `common,0x0372`,
`common,0x0375`, `common,0x2090`, `common,0x285F`, `common,0x55EE` and
`bank1,0xE7C9` each name a fill address and sit in no committed listing. That
is *not found by this method*, never *there is no code here*: the caller may be
code Ghidra never exported, and the census has no way to tell that from an
address nothing was decoded at. It is the same calibration rule `is_fill`
applies to a listing it reads no instruction from, in the same direction.

What the 28 support is narrow and worth stating exactly: `anchored` in
[`bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) §1 means at
least one of the 24 preceding byte anchors decodes exactly onto the site — a
candidate decoded entry point, not a call. Only 7 of the 28 clear that bar, and
not one of the 28 is at an instruction boundary in a committed listing, so in
this band `anchored` is not an opcode either. The census is an upper bound, the
listing headers already say so, and this is the band where that caveat stops
being a formality.

## The band in the wider censuses

- `bank-call-targets.csv`: **90** rows target the band across **54** distinct
  targets. **28** of those rows name one of the seventeen exported functions; of
  the 54 distinct targets, the other **37** have no index row at all.
- `bank-paged-call-targets.csv`: **4** rows, 3 distinct targets. Neither family
  seeds a function.
- `bank-relative-branch-targets.csv`: **5** rows, 4 distinct targets. Not a
  seeding family either.
- `index-table-entries.csv` (216 entries) and `bank0-8038-dispatch-table.csv`
  (9 entries): **0** point into the band.

So 99 rows across the three scans reach into `0x728F`-`0x7FFF`, and of the 54
distinct addresses the direct-call census names there, only 17 have an exported
function at all. The other 37 are not "wrong" in the same way — they are
addresses the scan named that nothing was ever exported at — but they are not
evidence that anything is there either.

## The same runtime addresses in the other program

The EC's common area and the PD image are two separate 64 KiB programs, and they
disagree about every address in the band. **Every one of the seventeen spans
holds live PD bytes**: 172 bytes read through `file_offset("pd", addr)`, 165 of
them not `0xFF`, and the `pd` program holds **7** exported functions at runtime
addresses inside `0x728F`-`0x7FFF` where the EC's common area is `0xFF` from end
to end.

`ec/annotations/pd-xdata-overlap.md` §3.1 already records the sharpest instance:
runtime `0x7421` is `90 04 a6 12 90` in the PD (`mov dptr, #0x04A6 ; lcall
0x90CB`) and `0xFF` in the EC. `0x7421` is not one of the seventeen — it is
*inside* `common/741C`'s span, so the EC's own listing covers it as three more
`mov R7, A`, which is the whole shape of the collision.

**Neither reading of the band is settled here.** "The EC's `0x728F`-`0x7FFF` is a
reserved region the vendor left unprogrammed" and "it is a linker artefact of
whatever produced this dump" both fit every number above, and this repository
cannot choose between them: the verdict needs a Keil linker map or `.M51` from
the vendor build, or a sibling dump to compare against, and neither is here.
What the census can say is the size of the hole, who pointed at it, and that the
other program does use the same addresses. No table entry and no real transfer
points into the band is evidence about the *byte scan*, not about the linker's
intent.

## The `.c` bodies

All seventeen `.c` files are identical to each other apart from the address in
the header comment and the function name in the declaration. That body writes
XDATA `0x1654`-`0x1657` and `0x1900`-`0x1902`, then calls a named writer
routine. **None of it is supported by the instructions**, which are `mov R7, A`
to the end of the listing. Why Ghidra emitted a body like that for a run of
`0xFF` is an open question this census does not answer; the measurable facts are
the bytes and the identity, and both are recorded.

## What changed

`ec/annotations/ghidra-functions.csv` gains **17** rows, one per `common` fill
listing, named `ff_filler_not_a_function_<addr>` to match the five `bank0`
siblings rather than the `unimplemented_ff_fill_*` form. That is a load-bearing
choice and not only a stylistic one: the verifiable fact is structural — the
address is inside a contiguous `0xFF` pad and is not an entry point — which is
exactly the `bank0` family's rationale, and these seventeen have the same
provenance. `unimplemented_*` would read as "a routine waiting to be
implemented" and invite a future reader to treat the `.c` as a to-do. It also
decides the `name_basis` cell: `grade_name_basis.PLACEHOLDER` matches
`[0-9a-z_]*ff_filler[0-9a-z_]*` and not `unimplemented_ff_fill_*`, so the
committed cell is `unresolved` with `type=unresolved`, which is what
`grade_name_basis.py --check` recomputes.

`build_ec_decompile.py`'s record-count pins and `ec/annotations/subsystems.md`'s
census move 1,851 → **1,872** in the merged tree, and both re-pins name the
movers — issue #558's four rows in `../findings.md` §27 and the seventeen here.
`unresolved rows` moves 152 → **169**, every row of that step these seventeen.
`ec/annotations/function-groups.csv` gains the seventeen too, every one
`ungrouped` with basis `ungrouped` and the file's own "no typed seed and no
connected component at or above the minimum size, not found by this method"
comment — which is the right answer for an address that is not a function, and
what `group_functions.py --check` refuses to leave out.
`ec/ghidra/cross-decoder.csv` is regenerated: the seventeen join its
`backbone`, all seventeen come back **`vacuous`** — the tool's own 8051 decode
finds no `MOV DPTR` in any of them, which agrees with the fill reading from a
third direction — and four `pd` rows join the sample because the sample set
moved. Measured on the merged tree the file goes 1,964 rows → **1,978** (18
join, 4 leave) against main; on this census's own branch, without §27's four
rows, it was 1,961 → 1,976.

**Until a Ghidra export runs, the seventeen keep `FUN_CODE_*` in
`ec/decompiled/index.csv` and in their listing headers.** No export is in this
change: it rewrites ~2,700 generated files and drags
`ec/annotations/call-graph.md` and `ec/annotations/xdata-register-map.md` into
the diff, which is merge-conflict surface a census does not need. The rows are
the editable surface `CLAUDE.md` points at; applying them is a separate
mechanical change. The consequence is that the anonymous-name counts #458
measures (813 / 475 / 822) do not move here, and a reader counting `FUN_CODE_*`
in the index will find seventeen that have an annotation row. The census prints
both names apart for that reason.

## One citation pair moved, and it moved the right way

`call_graph.citations()` turns any canonical 4-hex mention in a comment that
resolves to a `FUN_`-prefixed index row into a candidate pair. One of the new
comments does: `common,7DF2`'s names the `mov R3, #0x2` at `0x375E` that its own
byte match sits inside — the evidence for "not an entry point" — and
`common,375E` is an unannotated anonymous export. The comment does not claim a
call there, and the `fill-at-citer` veto rejects the pair anyway, because the
citing listing is fill. So the fill-rejection count goes **0 → 1** in the merged
tree and no credit moves. Measured on this census's own branch it was 21 → 22;
the twenty-one are gone here because issue #558's four rows named `common,0F75`,
`common,158E` and `common,1594`, and a named callee is not an anonymous one, so
all seven `bank1` rows × three call sites left the candidate set without the rule
changing. `docs/findings/citing-listing-evidence.md` carries the re-derived
figures and names the pair.

The other sixteen carry the same evidence without manufacturing a pair. That is
a property of how `citations()` reads prose rather than a choice made to protect
a number: a canonical `0x` + 4-hex mention is a call candidate, so a comment
that has to name a file offset, a pad boundary and a callee spells them the way
the rest of the file spells a sibling row — the file offset in the six-digit
form (`0x007401`, which the canonical-width test skips), the pad's upper bound as
"the last byte of the common area" with `0x8000` as the boundary marker, and the
`.c` body's callee by name rather than by address. No claim is weaker for it.

## Limits

- **A listing being fill is not a statement about what the EC does.** It is a
  statement about `0xFF` bytes at an address, in a program this repository has
  never run. No `status:` in `ec/annotations/registers.yaml` moves, and
  `ec/ghidra/xdata-symbols.csv` is untouched.
- **"No committed listing covers this address" is not "there is no code
  here"**, for the 6 sites. It is the same rule as everywhere else in this tree.
- **`is_fill` reads nothing is not fill.** All 2707 committed listings parse to
  at least one instruction line, so that guard is defensive here, and the
  census's own `--self-test` pins it against a fixture rather than against the
  tree.
- **The band is measured; its cause is not.** [§The same runtime addresses in
  the other program](#the-same-runtime-addresses-in-the-other-program) sets out
  both readings and what would settle each.
- **The cross-decoder comparison is advisory.** It is a stride decode of the
  listing against the committed `.c`, not a second decompiler, and its
  `vacuous` verdict on the seventeen means the decode found nothing to compare —
  not that the `.c` and the `.asm` agree.

## Re-deriving

One command, from the repository root, prints every figure in this file. Its
`--self-test` pins the 30/29/1 split, the seventeen addresses with their
instruction counts, the `0x728F`-`0x7FFF` band, the 28/0/22/6 provenance split,
the `0x7421` cross-program read, and the three refusals.

```console
$ python3 ec/tools/census_ff_fill.py --self-test
$ python3 ec/tools/census_ff_fill.py
```

This tool is deliberately **not** wired into `.github/scripts/agent-gates.sh`:
that file is a template copy under `.github/`, and the agent pipeline's token
has no `workflow` scope, so a branch touching it fails at the very end. The
`--self-test` is the check, run by hand and quoted here; a human can add the
`case` arm upstream in [`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline)
if it should be gated.
