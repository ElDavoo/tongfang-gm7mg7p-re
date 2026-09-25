# `0x0860`-`0x086E`: the EC's own level block, and what it dispatches on

Issue #180 asked to read the `0x0860`-`0x086E` run in main-EC cluster
`main-ec-003` and settle four questions: what sets `0x0860`, what the sibling
bytes hold, what consumes the `0x1C39`/`0x1C3A` copy, and whether the
`0x044C`-`0x05F1` group — `main-ec-049`, a different cluster — is the same
mechanism. This is the answer.

> **Correction, 2026-09-24.** Issue #180 wrote that cluster as `main-ec-002`.
> It is `main-ec-003` in the census as re-derived on the merged tree, and
> `main-ec-002` is now the counter block over `0x0460`-`0x09CE`, which shares
> not one address with this run. The `0x044C`-`0x05F1` group is `main-ec-049`.
> This supersedes the issue #253 correction further down for the same reason and
> leaves it standing: that one is right about the census it was written against
> and wrong about this one. `xdata-register-map.md` §5 carries the re-derivation
> and `../tools/check_cluster_citations.py` holds this file to it.

The machine-readable table behind every number here is
**`xdata-086x-dispatch-sites.csv`**, the `--csv` output of
`ec/tools/trace_xdata_refs.py` over the 15 addresses this page is about; §8
carries the check that reproduces it byte for byte.

Nothing in this file is a live observation, and no entry it supports is above
`present-untested`. The block is real, its arithmetic is legible, and **what
the EC does with the numbers is not** — §7 writes that down as a step for a
human with the machine.

> **Correction, 2026-09-24 (issue #253).** This page used to scope its subject
> to `main-ec-003`, which is the inverse of the drift issue #253 is about — a
> real cluster named where a different real cluster belongs. All 15 addresses
> §1 sweeps are `main-ec-002` members in `xdata-clusters.csv` (row 3: 44
> addresses, 248 references) and carry `cluster_id=main-ec-002` in
> `xdata-registers.csv`. `main-ec-003` (row 4) is the 43-address counter block
> of `xdata-06c2-06db-timers.md` and shares no address with this one. The id
> moved for the same reason as every other id in issue #253, which is issue
> #4.3's census regeneration (#133 / #238), and
> `../tools/check_cluster_citations.py` is what holds the rest of the tree to
> the census.

## 1. How to reproduce it

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x0860 0x0862 0x0865 0x0866 0x0867 0x0868 0x0869 0x086A 0x086B \
      0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv --census-column \
  | diff - ec/annotations/xdata-086x-dispatch-sites.csv
```

That is the whole sweep, it is read-only, and it needs no hardware. Adding
`--check` to the same command turns the diff into an exit code, which is how
§3's per-site correspondence and this page's table are held to the image.
`--census-column` appends the ninth column of §3; it reads
`xdata-0860-census-sites.csv` and is **not** derived from the image, and the
sites it covers no mapping say so on stderr and in the cell rather than
leaving it blank. The `0x044C`-`0x05F1` group of §6 is swept the same way, and
the case table of §4 is re-derived by
`ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800 --at 0xD148`.

## 2. The blind spot, which travels with every number

`trace_xdata_refs.py` finds **direct** `MOV DPTR,#addr` sites and nothing
else. A byte reached through a computed DPTR, a register-indirect XDATA
access, or a table lookup is invisible to it. So:

- a **zero** anywhere in this file means *not found by this method*. It is
  never evidence a byte is unused, and no entry here is `absent`;
- a **write** means the instruction stores to the byte. It is not evidence
  the EC acts on the value, and nothing here is `confirmed-*` on the
  strength of one;
- the access column is a **linear 8-instruction walk**, not a disassembler
  (`ec/README.md`, and the tool's own docstring). `handoff` means DPTR went
  to a subroutine and the direction was not settled at the site; §5 resolves
  both handoffs one level down.

This is the caveat `docs/findings.md` §4c carries, and it is why
`0x0862` and `0x086D` are described as writerless rather than as inputs
nobody supplies.

> **CORRECTION (2026-09-25, issue #250) to that sentence's "writerless",
> which was right about the method and wrong about the bytes.** The direct
> `MOV DPTR` scan still finds no writer for either byte, and that half
> stands. The other half does not: `FUN_CODE_8294` at bank0 `0x8365` stores
> through a **computed** DPTR whose `DPH` is hard `0x08` and whose `DPL` is
> `(2*XDATA[0x0A56] + 0xD0) mod 256`, and it stores a **pair** of consecutive
> bytes. `0x0862` is the first of that pair when `XDATA[0x0A56]` holds
> `0x49`/`0xC9`; `0x086D` is the second of a pair at `0x086C`/`0x086D` when
> it holds `0x4E`/`0xCE`. The gate is observed nowhere in this repository, so
> this is a **conditional** writer and not evidence either byte ever moves —
> the same standard a readback fails to meet. It is the only page-`0x08`
> `DPH` construction in the EC (1 of 64 `addc A,#imm ; mov DPH,A` sites), and
> `ec/annotations/xdata-1c3x-consumers.md` §6.2 has the method, the counts
> and the six sites that remain open. No `status:` moves.

## 3. The `0x0860` direction counts, and a correction to this section

**One sentence per method, because they are not interchangeable.** The
opcode sweep — `trace_xdata_refs.py` and the `.asm` listings it walks —
carries the **structural** claims: which routine holds a read or a write, and
what the instruction there does. The C-level census behind
`xdata-registers.csv` carries the **per-address direction**: how the
decompiled C's occurrences of the address bucket out. Neither is derived from
the other's columns, and on this address they are not in conflict, because
they have different denominators. The sweep counts **opcode sites**, a direct
`MOV DPTR,#imm16` and the `movx` after it, which for `0x0860` is the 7
EC-side sites of §8 and the `read 4 / write 2` among them. The census counts
**C-level occurrences** of the address in the decompiled text, which is the
`refs: 17` of `ec/annotations/xdata-registers.csv:662`. The 14/2/0/1 below
is the bucketing of those 17, not a rival count of the 7.

> **CORRECTION (2026-09-24, issue #281) to this section's opening sentence,
> which read:**
>
> "**Every direction claim in this file comes from `trace_xdata_refs.py` or
> from a `.asm` listing, never from the `read`/`write` columns of
> `xdata-registers.csv`.**"
>
> The blanket "never" is wrong, and the section's own next sentence said so:
> the `14/2/0/1` row it introduced is the `read`/`write` columns of
> `xdata-registers.csv`. The convention the sentence was reaching for is the
> two sentences above — structural from the sweep, per-address direction from
> the census — and issue #281 left the old sentence in the file with the two
> contradicting, so a reader could not tell which source was authoritative for
> a given claim. The wrong version stays visible here for the same reason the
> two below do.

> **CORRECTION (2026-09-24, issue #249, correcting text added by PR #225)
> to this section as first merged, which read:**
> "`ec/tools/xdata_register_map.py:138` defines `ASSIGN` ... and
> `store_target()` at line 277 decides "is this the assignment target" by
> testing whether the text following the occurrence starts with any member of
> `ASSIGN`. A Ghidra comparison spells `==`, which also starts with `=`, so
> **every comparison is counted as a store**. ..." "The census row for
> `0x0860` therefore reads 13 `write`, 3 `read+write`, 1 `passed-to-call`,
> **0 `read`**." ... "**The census is read and cited here, never
> regenerated.** Re-running `xdata_register_map.py` today would re-freeze 838
> miscounted occurrences across 211 addresses into the committed CSVs and
> make the wrong row look authoritative." ... "One pre-existing condition,
> recorded rather than fixed: the census's own `--check` and `--self-test`
> already fail on `main` for an unrelated reason (`0x0400` gained the name
> `BAT_POWER_UNIT_0` and the CSVs were not regenerated), and 60 symbol-table
> addresses are named but not yet spelled in the decompile."
>
> **Every clause of that is false against the committed tree, and false in
> the same direction twice over: it describes a classifier that had already
> been fixed, and a census that had already been regenerated.** `==` is
> excluded. `ASSIGN` is at `ec/tools/xdata_register_map.py:191` and
> `store_target()` at `:769`; the rejection is at `:788-789`, the reason for
> it in the function's own comment at `:785-787`, and the tree-wide count of
> 838 at `:561`. The module docstring states the rule in the past tense at
> `:64-75` and credits **issue #178**, which merged before PR #225 did. Both
> CSVs are current: the committed `ORACLE` comment at `:305-306` records
> `named_in_tree` moving `131 -> 146` with issue #180's 15
> `0x086x`/`0x1Cxx`/`0x1Fxx` entries — this very cluster's — and `146 -> 150`
> with issue #183's four since. `--check` and `--self-test` both exit 0 on
> `main`. `0x0400` has carried
> `BAT_POWER_UNIT_0` in the census since `ec/ghidra/xdata-overrides.csv:4`
> put it there. And the "60 ... not yet spelled" figure was already wrong
> when it was written: `xdata-symbols.csv` holds 172 rows against
> `named_in_tree` 150, a gap of **22**.
>
> **FURTHER CORRECTION (2026-09-25, issue #254) to the line citations in the
> #249 block above, not to its findings.** Every one of them was correct when
> #249 wrote it and none of them resolves now, because the tool has grown since:
> `ASSIGN` is at `xdata_register_map.py:239` (was `:191`), `store_target()` at
> `:912` (was `:769`), the `==` rejection at `:935` (was `:788-789`), and the
> 838-occurrence comment at `:934` (was `:561`). The `:64-75` docstring
> paragraph still resolves. **The substance of the #249 correction is unchanged
> and is confirmed again here:** `==` is excluded, the committed census is
> post-guard, and `0x0860`'s committed row is 14 `read` / 2 `write` / 0
> `read+write` / 1 `passed-to-call` over 17 references — the `14/2/0/1` in §3's
> live table, not the `13/3/1/0` the quoted original text carried. The tool now
> also has a `--no-eq-guard` switch that re-derives the pre-#178 buckets from
> the committed tree; see `xdata-06c2-06db-timers.md` §6a for the measurement
> and for why a re-freeze is no longer the thing to fear.
>
> **CORRECTION (2026-09-24, issue #280) to the figures in that last
> sentence, which read as committed above.** `xdata-symbols.csv` now holds
> **173** rows, not 172, so the gap is **23**, not 22; `named_in_tree` is
> still 150. The extra row is `XDATA_0390`, added by issue #259, and the
> census did not move — which is the whole of issue #259's result, and why
> `0x0390` is one of the 23 below. The figure was always a difference between
> two files rather than a finding: nothing in the correction above turned 22
> into a defect, and nothing about its becoming 23 is one either.
>
> **What the 22 did leave unexplained, and no longer does: *which*
> addresses.** A gap of a size, checked as a count, says only that the 150 and
> the "60 ... not yet spelled" figure cannot both be right. It does not say
> what the missing addresses are, or why, and that is what the correction
> above was reaching for. It is now recorded per address in `NOT_IN_TREE` in
> `ec/tools/xdata_register_map.py`, beside `BLIND_SPOT`, and the self-test
> asserts the **set** rather than the count — so `ORACLE["named_in_tree"]` is
> `len(symbols) - len(NOT_IN_TREE)`, 173 − 23, arithmetic rather than a number
> to be taken on trust. **The accessor-argument reading lands there:** seven of
> the 23 are reached only as a bare hex literal handed to a helper
> (`read_xdata_pair_to_r1r2(0x40a)` at `bank1/AE2B.c:20`, and
> `add_full_product_to_dptr(0x420,0x60,…)` at `pd/34A5.c:18`), and two more
> through what is plainly a decompiler mistake — the export calls
> `FUN_CODE_0402` and `FUN_CODE_0408` where the assembly reads
> `mov DPTR,#0x402; lcall 0x889e`, and `index.csv` lists the two as
> functions. The reasons use a three-word vocabulary with no word for
> absence, and the self-test asserts that no line can acquire one.

**What the census says, and what pins it.** `0x0860` is **14 read, 2 write,
0 read+write, 1 passed-to-call**. The two stores are `bank0/D281.c:18`
(`XDATA_0860 = 0xff`) and `bank0/D289.c:17` (`XDATA_0860 = 0`), and the one
`passed-to-call` is the `switch_case_dispatch(XDATA_0860)` call in
`dispatch_on_0860` — an address handed to a call is that bucket and not a
read, which is why the census's 14 reads are all comparisons. The row is not
the tool's own sum: `HAND_CHECKED["0x0860"]` at
`ec/tools/xdata_register_map.py:766` pins exactly those buckets, and the
self-test's "hand-checked direction oracle" assertion at `:2250-2256` fails
loudly if a generated row ever parts company with it. It is one of five
addresses in that oracle — and since issue #280 it is **not** the only net:
the self-test now also asserts, over the whole tree rather than over these
five, that every occurrence the census buckets `write` or `read+write` has an
assignment and not a `==` after the address, measured by a second code path
that does not re-implement the classifier. That check covers 5,662
occurrences across 1,008 addresses, and against the pre-fix classifier it
fails naming `0x0860` and `0x0440` — so the hand check is now the per-address
*count* oracle and the wide one is the per-occurrence shape oracle, and the
two are not substitutes for each other.

`0x0860` is the one that shows how far the pre-fix classifier got: the row
then read 0 read / 13 `write` / 3 `read+write`, a pure write-side dispatch
byte, for a byte whose four opcode reads of §8 are this same routine's
early-out, two of the case tests, and the dispatch itself.

> **CORRECTION (2026-09-24, issue #281).** The same sentence named the oracle
> assertion at `:1872-1878`, which on `main` is the tail of the `0x0390`
> census-absence check (`not census_has_0390`), not the oracle. The live
> pointer is now `:1901-1907`. The bucket totals it pins were never affected;
> only the pointer to the assertion that holds them was wrong.

**The comparison count is high and the writer count is low because `0x0860`
is a dispatch selector, and that is structural rather than an artefact of any
classifier.** Fourteen of the 17 occurrences are `==` tests inside
`dispatch_on_0860`: the `0x00` and `0xFF` early-outs of §4, and the twelve
case values §4's table is built from, whose later tests are multi-line `||`
chains naming the address up to three times on a line. A byte the firmware
gates and dispatches on internally gets compared far more often than it gets
stored, and that one fact is what makes both this section's 14-read row and
§8's `read 4` sensible.

### The two methods, site by site

**`2 + 6 + 6 = 14` reads, `2` writes and `1` passed-to-call, and the
`census` column of `xdata-086x-dispatch-sites.csv` is where they are recorded
rather than reconciled in prose.** The correspondence is committed as
**`xdata-0860-census-sites.csv`**, one row per site keyed on the sweep's own
`file_offset`, and **`ec/tools/check_site_census.py`** joins the two against
the census and exits non-zero on any disagreement. The comparison constants
are in the table below so a reader can check them against
`ec/decompiled/bank0/D091.asm` by eye; the sweep reads the `.asm` and the
census reads `D091.c`, and neither number is inferred.

| site | sweep `access` | `census` | C occurrence(s) | why the two are not the same shape |
|---|---|---|---|---|
| `0x0D091` | `read x1` | `read x2` | `D091.c:43` (`== 0x00`), `:47` (`== -1`) | `0xD094 movx` (`jnz`) and `0xD09A movx` (`cpl`) — two early-outs behind one DPTR load |
| `0x0D0EF` | `read x1` | `read x6` | `D091.c:69,70` | the `0x48` chain: six `movx` re-reads at `0xD0F2`–`0xD10B` testing `0x06 0x16 0x36 0x07 0x17 0x37`, no DPTR reload between them |
| `0x0D117` | `read x1` | `read x6` | `D091.c:73,74,75` | the `0x4C` chain: six re-reads at `0xD11A`–`0xD133` testing `0x08 0x18 0x38 0x09 0x19 0x39` |
| `0x0D144` | `read x1` | `passed-to-call x1` | `D091.c:81` | `movx a,@dptr ; lcall 0x7151` — **the same instruction, two vocabularies** |
| `0x0D281` | `write x1` | `write x1` | `D281.c:18` | `XDATA_0860 = 0xff` |
| `0x0D28A` | `write x1` | `write x1` | `D289.c:17` | `XDATA_0860 = 0` — `clear_0860`'s decompile entry is `0xD289`, one byte before the site, so the file and the offset do not match |
| `0x0D31C` | `no movx found in the decoded window` | `no census occurrence` | — | `mask_dp_byte_7c_reset_dptr_0860` reloads DPTR and returns; `D319.c`'s body is `return *param_1 & 0x7c;` and never names the address |
| `0x25CE4`, `0x25CFC` | `read x1, walks 2 consecutive…`, `read x1` | `other program` | — | the PD image, which has its own XDATA map; `xdata-registers.csv:662`'s `0x0860` row is `main-ec` |

**The sums close on the committed data, which is the point of recording
them per site:** `2+6+6 = 14` read, `2` write, `1` passed-to-call and `refs:
17` here, against `read 4 / write 2 / no-movx 1` over §8's seven bank-0
sites. `check_site_census.py` asserts both — the direction at every site and
the per-bucket totals against `xdata-registers.csv:662` — so a hand-typed
number that drifts fails instead of reading as agreement.

**Three residues, named rather than left for a reader to infer.** The
`2/6/6` **collapse**: all 14 `==` occurrences do have a byte site, and they
land on three of them, because the sweep records one row per `MOV DPTR` and
the `||` chains re-read A without reloading DPTR. The counts are not
comparable per site, and the checker compares directions per site and counts
per bucket. `0x0D144`'s **two vocabularies**: the sweep reports the `movx` it
decoded, the census reports the call the value went into, and the census's
`passed-to-call` bucket exists *because* a value loaded for a call is not a
use. And `0x0D31C` plus the two PD sites, where one of the methods is
structurally blind and the answer is a token, not a zero — §9 says what that
costs.

**The 14 addresses other than `0x0860` carry `not recorded` and nothing
else.** That is "not done by this method", never "there is nothing there", and
a blank cell would have read as agreement — the skip-that-is-not-deliberate
failure `../tools/check_cluster_citations.py` is built to catch, in a table no
tool could see.

## 4. `0x0860`: two writers, and a gate that is its own early-outs

**The writer set is two instructions, and this method found no others.**

| site | loads DPTR | the store that follows | routine holding the site |
|---|---|---|---|
| bank0 `0xD281` | `0x0860` | `0xFF` at `0xD286` | `set_0860_ff_then_d284` |
| bank0 `0xD28A` | `0x0860` | a cleared `A` at `0xD28D` | `clear_0860` |

Both sit in the `0xD281`-`0xD2BD` block, and the existing `0xD284` row
already records that it writes `0xFF` through whatever DPTR the caller left,
with `mask_dp_byte_7c_reset_dptr_0860` at `0xD319` reloading DPTR to `0x0860`
immediately before. The seventh bank-0 site is that `0xD31C` one: it loads
DPTR and returns with no `movx`, which this method reports as its own
category rather than guessing a direction. Every other main-EC site for this
address is inside that block, and `static_refs_pd_image` is 2.

**The gate is `dispatch_on_0860`'s own early-outs**, and it is what makes the
comparison count so high and the writer count so low. Reading
`ec/decompiled/bank0/D091.asm` from `0xD091`:

- `0x0860 == 0x00` → `ljmp 0xD2BE`, a bare `RET`;
- `0x0860 == 0xFF` → `ljmp 0xD2BE`;
- bit 0 set in `0x1C00`, `0x1C11` or `0x1C29` → `ljmp 0xD2BE`.

So `0x00` and `0xFF` are the **idle and busy marks of a byte the firmware
sets on itself** — this is a byte the EC dispatches on internally, and the
census's "0 reads", which is what made that hard to see, was a miscount; §3
is the correction, and the row is 14 reads. Two things that are *not*
being claimed: that no other program can reach the byte, and that no writer
exists that this method cannot see. A host path would have to arrive through
a computed DPTR to be invisible here, which is the same blind spot §2 names
for every address on this page.

**The `0xD14B` island is a case table, not code.** The existing `0xD091` row
recorded it as unsettled; it is settled, and the correction is in that row
with the old sentence left visible beside it. The bytes are the inline table
the `0x7151` case reader consumes — the same reader the table at `0x8038`
uses, which pops the return address that the `lcall` at `0xD148` pushed.
Read as `(big-endian address, case byte)` triples:

| case | target | case | target |
|---|---|---|---|
| `0x06` | `0xD173` | `0x07` | `0xD198` |
| `0x08` | `0xD173` | `0x09` | `0xD198` |
| `0x16` | `0xD1C0` | `0x17` | `0xD1EF` |
| `0x18` | `0xD1C0` | `0x19` | `0xD1EF` |
| `0x36` | `0xD221` | `0x37` | `0xD24E` |
| `0x38` | `0xD221` | `0x39` | `0xD24E` |

Twelve entries at file `0x0D14B`-`0x0D16E`, a `0x0000` terminator at
`0x0D16F`, and a default of `0xD289` — `clear_0860` — at `0xD171`. The case
values are exactly the twelve the comparison chain above tests.

> **A trap worth naming.** The `.asm` decodes these bytes as `ACALL` to
> `0xD673`, `0xD698`, `0xD6C0`, `0xD6EF` and the `SETB`s of `0x21`, `0x4E`
> and `0x89`. That is the table read as instructions, and its targets are
> `0x500` higher than the table's. A linear disassembly of data is not a
> reading of the data; `decode_index_table.py` checks the entry layout
> against the code that consumes it, which is why it gets this right and the
> `.asm` does not. The corrected `0xD091` row says the same thing.

## 5. `0x0865`-`0x086B` is a working set, and `0x9D9B` computes three results

**Not one block: three, with three results.** The corrected reading of
`bank0:0x9D9B` (now `compute_level_blocks_086b_086c_086e`, 627 bytes) is
that `0x0865`-`0x0869` is a five-byte working set **reused by all three
blocks**, and `0x086B`, `0x086C` and `0x086E` are the three results:

| block | seeds from | overrides (when non-zero) | result | clamps |
|---|---|---|---|---|
| `0x9DA0`-`0x9E88` | `0x08C0` | `0x0783`→`0x0866`, `0x0872`→`0x0867`, `0x0873`→`0x0868`, `0x0874`→`0x0869` | `0x086B` | `0x23`, `0x14`, `0x0F` |
| `0x9E89`-`0x9FA2` | `0x08C1` | `0x0784`→`0x0866`, `0x087A`→`0x0867`, `0x087B`→`0x0868`, `0x087C`→`0x0869` | `0x086C` | same three, via `0xBC7B`/`0xBC7E` |
| `0x9FA3`-`0xA00D` | `0x08C3` | `0x0785`→`0x0866`, `0x088A`→`0x0867`, `0x088B`→`0x0868` | `0x086E` | **none** |

Each block calls `sub_0866_from_0865` (`0x0865` minus `0x0866`), then
`sub_dptr_byte_from_0867` and `sub_dptr_byte_from_0868`, each of which reads
the running result through the caller's DPTR and returns a difference with
the borrow in `CY`, keeping the smaller; then the first two cap the result at
`0x0869` and apply their three clamps, and the third clamps nothing at all.
Each clamp is guarded by bit 7 of `0x0751`
(`MANUAL_FAN_CTRL`) together with a different pairing of bits 1 and 0 of
`0x07C6` (`AP_OEM_6`). The middle block's third clamp works through
`0x0A47`, which is then compared against `0x09EF` and, on a change, passed
to `0xA73F` with `R7=0xBC`.

**The two handoffs this sweep leaves open are settled one level down, and
both are reads.** `sub_dptr_byte_from_0867` and `sub_dptr_byte_from_0868`
begin `movx A,@DPTR` on the caller's pointer, so the `0x086B`, `0x086C` and
`0x086E` sites that hand DPTR to them are reads in every case. That takes
`0x086B` to 9 reads against 5 writes and `0x086E` to 4 against 3.

**The units are not fixed by anything here, and none is named.** The same
`0x0865` is written from a per-mode seed in one routine and from two
constants (`0x48`, `0x4C`) plus a zero in another. `dispatch_on_0860` sets
those constants; `compute_level_blocks_086b_086c_086e` sets the seeds; the
three results are what the rest of the block stages out. A wrong unit baked
into a symbol outlives the note that would have to correct it, so the entries
stay `XDATA_086x`.

`bank0:0xA00E` (now `seed_0872_087a_088a_then_select_level`) is part of
the same mechanism and says so: it seeds the override sources in one run —
`0x08C0` into `0x0872`, `0x08C1` into `0x087A`, `0x08C3` into `0x088A` —
which is what the overrides in the table above read. Several of its arms
tail-call `select_code_table_entry_and_store_0872_087a_088a`, the code table
that actually fills those three bytes; that routine's body is not in this
listing, so the arm is recorded as a call and not decoded further.

## 6. The copy is not a mirror, and the pair is not a second buffer

`copy_0866_86b_to_1c04_1c3a` writes six source bytes to **three
non-contiguous pairs at three different strides**:

| source | destination | gap from the previous destination |
|---|---|---|
| `0x0866` | `0x1C04` | — |
| `0x0867` | `0x1C05` | +1 |
| `0x0868` | `0x1C15` | +0x10 |
| `0x0869` | `0x1C16` | +1 |
| `0x086A` | `0x1C39` | +0x23 |
| `0x086B` | `0x1C3A` | +1 |

So the same six values go to three separate pairs — **not a copy at a fixed
offset**, and the layout of `0x0866`-`0x086B` is not reproduced at
`0x1C39`. "A second buffer of the same field layout" is not a claim the
bytes support, and the `0x1C3A` entry in `registers.yaml` says so.

**The `0x1C39`/`0x1C3A` pair carries a second, different source.** Each has
five direct sites, all bank 0 and all between `0xD0DF` and `0xD2B5`: two
reads and three writes. The reads are `0xD0DF`/`0xD0E7` (in
`dispatch_on_0860`, copying in from the pair) and `0xD26F`/`0xD277`; the
writes are `0xD225`/`0xD22D`, `0xD24F`/`0xD253`, and `0xD2B2`/`0xD2BA` in
the copy. Reading those windows against the case table of §4, six of them
sit in the **case-`0x36`/`0x37`/`0x38`/`0x39` handlers** at `0xD221` and
`0xD24E`:

```asm
0d221  900863   mov dptr,#0x0863     ; 0xD221, case 0x36/0x38
0d224  e0       movx a,@dptr
0d225  901c39   mov dptr,#0x1c39     ; <- a writer that is NOT the copy
0d228  f0       movx @dptr,a
0d229  900864   mov dptr,#0x0864
0d22c  e0       movx a,@dptr
0d22d  901c3a   mov dptr,#0x1c3a
0d230  f0       movx @dptr,a
...
0d24e  e4       clr  a              ; 0xD24E, case 0x37/0x39
0d24f  901c39   mov dptr,#0x1c39     ; <- cleared, not copied
0d252  f0       movx @dptr,a
...
0d26f  901c39   mov dptr,#0x1c39     ; <- read back
0d272  e0       movx a,@dptr
0d273  900863   mov dptr,#0x0863
0d276  f0       movx @dptr,a
```

So the same two bytes are a destination for `0x086A`/`0x086B` in one place
and a staging area for `0x0863`/`0x0864` — an entirely different pair — in
another. That is a **stronger** answer to the issue's question than the
stride argument alone: the pair is not even dedicated to one field.

**What consumes the pair downstream is not answered by the decompile, and
this file does not guess.** No consumer of `0x1C39`/`0x1C3A` is identified
here. They sit at the tail of the case handlers and of the copy, and a
writer next to a reader is co-occurrence, not a consumer. `0x0862` and
`0x0865` are staged by the two 21-byte routines `0xD2EF` and `0xD304` (now
`stage_0862_0865_into_1c12_1c14` and `..._1c36_1c38`) into `0x1C12`-`0x1C14`
and `0x1C36`-`0x1C38`, the same shape with every destination differing by
`0x24`; `stage_1c03_1c02_1c01` stages them into `0x1C01`-`0x1C03`. Which
routine, if any, reads those bytes is not established.

> **Answered, 2026-09-25 (issue #250).** The eleven bytes this section left
> open have now been swept over the whole image and searched with ten named
> methods. The full result is
> **`ec/annotations/xdata-1c3x-consumers.md`**, with the machine-readable
> table **`xdata-1c3x-consumers-sites.csv`** (67 rows, reproducing byte for
> byte by the command its §1 prints). What it settles, in the order the
> question was asked:
>
> - **No consumer of `0x1C39`/`0x1C3A` is named.** Ten methods return zero,
>   and each is bounded by the thing it cannot see — the computed-DPTR
>   remainder is issue #110, and §6 of that document is the method table.
>   This stays "not found by method X", never "no consumer exists".
> - **`0x1C36`-`0x1C38` have no read site in any image.** Their only site
>   each is `stage_0862_0865_into_1c36_1c38` — the routine that writes them.
>   That is the sharpest negative in the set.
> - **`0x1C01`-`0x1C03` have 43 direct sites between them and not one read.**
> - **The `0x1C12`-`0x1C14` trio has five writers, not the one this page
>   names.** Two bank-1 routines this page's fifteen-address list cannot see
>   — `FUN_CODE_9ce8` and `FUN_CODE_9d53`, both behind a `0x1C11 == 0` test,
>   seeding `0x48`/`0x00` with `0x99` and `0x9F` respectively — sit alongside
>   `stage_0862_0865_into_1c12_1c14` and the two `set_1c12_*` constants. The
>   census already carried the row (`refs 5, 0 read, 5 write`); the question
>   was never swept by the one table that would have answered it.
> - **`0x0862` and `0x086D` do have a writer** — a conditional computed-DPTR
>   one, §2's correction above.
>
> The nine `0x1Cxx` bytes are now recorded in `registers.yaml` at
> `present-untested`. That is an entry existing, **not** a status moving, and
> `ec/ghidra/xdata-symbols.csv` was regenerated from the file rather than
> edited. No name is coined for the block.

## 7. The `0x044C`-`0x05F1` group is a different mechanism

**It is not the same mechanism, and the only address the two halves share is
`0x0466` — a shared gate, not a data path.** Sweeping the group the same way
puts `0x04FE`/`0x04FF`, `0x05F0`/`0x05F1` and `0x06D0`/`0x06F1`-`0x06F7`
almost entirely in bank 1, in a state block gated on `0x0490` and `0x06E6`:
`0x04FF` is reached only from bank 1 (`0x860F`, `0x9088`, `0x94A8`, `0x9581`,
`0xAF0D`, `0xBE10`), `0x05F0` and `0x05F1` only from bank 1, and
`magic_55aa_and_0704_countdown` at `0x94FA` holds eight of the group's sites
across `0x04FE`, `0x04FF`, `0x06D0`, `0x06F1`, `0x06F2` and `0x06F7` — a
different signature from anything in the `0x086x` run, and none of those
addresses appears in `dispatch_on_0860`, `0x9D9B` or the copy. (Eight is what
the sweep returns for those six addresses; over the whole `0x044C`-`0x05F1`
range the same routine holds nine, and across the wider
`0x06D0`/`0x06E3`/`0x06E4`/`0x06F1`-`0x06F7` set named here, fifteen.)

`0x0466` is the one overlap: `bank0:0x9C50` tests bit 4 of it and
`bank0:0x9D89` tests bit 1, while three bank-1 sites read the same byte —
`bank1:0x9104` (in `step_counter_084e_dispatch`), `bank1:0x9B3C` and
`bank1:0x9D5B`. That is a shared gate, and a shared gate is not a data path.
(The bank-1 routine at `0x9088` listed above,
`count_down_06e4_and_toggle_06e3`, is 47 bytes long and reaches `0x045F`,
`0x04FF`, `0x06E3` and `0x06E4` but never `0x0466`, which is why `0x9088`
is not among these three.) (The bit-4 test is at
`0x9C50`, inside the bank-0 code just before `gate_06e6_442_then_sync_046a_from_086b`
at `0x9CA6`, not inside it — `0x9CA6`'s own gate is `0x06E6 == 1` plus bit 4
of `0x0442`.) This is a co-occurrence, and `xdata-register-map.md` §6's
"evidence about shape, not about meaning" applies verbatim.

**`0x1F01`/`0x1F07` are a third thing again.** `bank0:0xD065` writes three
constants unconditionally (`0x20` to `0x1F01`, `0x01` to `0x1F06`, `0x5A` to
`0x1F07`) with no read, and `magic_55aa_and_0704_countdown` writes `0x1F07`
from bank 1 at `0x952C`. `0x1F07` is also a site of the same `0xD6C0`-neighbour
group `0x1F06` is (the sweep puts `0x1F06` at `0xD6BB`, `0xD6EC` and
`0xD757`), which is why this page records the pair and not just `0x1F07`.
Neither address is touched by the `0x086x` run. Recorded as a third thing;
**not merged**.

**Nothing here names the block.** The mechanism is describable; the units of
`0x0865`-`0x086E` are not fixed by anything on this page, so no name is
coined for them.

## 8. The per-address table

EC/PD split and the `b0` column are site counts; the access columns classify
the EC-side sites only, and the last column names the routines holding them.
Every cell is re-derivable from `xdata-086x-dispatch-sites.csv`; the two
`handoff` cells are resolved in §5 and the starred rows below count them as
reads. **That table's ninth column, `census`, is the other method's answer for
the same site** — §3's per-site table is where `0x0860`'s nine rows are read
out of it, and `../tools/check_site_census.py` is what holds the two to each
other. The other 14 addresses carry `not recorded` there, which is §9's first
concession.

| addr | EC | PD | b0 | read | write | handoff | no-`movx` | routines holding EC sites |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `0x0860` | 7 | 2 | 7 | 4 | 2 | 0 | 1 | dispatch_on_0860 ×4, set_0860_ff_then_d284, clear_0860, mask_dp_byte_7c_reset_dptr_0860 |
| `0x0862` | 3 | 2 | 3 | 3 | 0 | 0 | 0 | stage_1c03_1c02_1c01, stage_0862_0865_into_1c12_1c14, stage_0862_0865_into_1c36_1c38 |
| `0x0865` | 10 | 0 | 10 | 4 | 6 | 0 | 0 | compute_level_blocks_086b_086c_086e ×3, dispatch_on_0860 ×3, sub_0866_from_0865, and the three staging routines |
| `0x0866` | 12 | 0 | 12 | 5 | 7 | 0 | 0 | compute_level_blocks_086b_086c_086e ×9, sub_0866_from_0865, dispatch_on_0860, copy_0866_86b_to_1c04_1c3a |
| `0x0867` | 9 | 6 | 9 | 2 | 7 | 0 | 0 | compute_level_blocks_086b_086c_086e ×6, sub_dptr_byte_from_0867, dispatch_on_0860, copy_0866_86b_to_1c04_1c3a |
| `0x0868` | 9 | 2 | 9 | 2 | 7 | 0 | 0 | compute_level_blocks_086b_086c_086e ×6, sub_dptr_byte_from_0868, dispatch_on_0860, copy_0866_86b_to_1c04_1c3a |
| `0x0869` | 8 | 0 | 8 | 3 | 5 | 0 | 0 | compute_level_blocks_086b_086c_086e ×6, dispatch_on_0860, copy_0866_86b_to_1c04_1c3a |
| `0x086A` | 2 | 0 | 2 | 1 | 1 | 0 | 0 | dispatch_on_0860, copy_0866_86b_to_1c04_1c3a |
| `0x086B` * | 14 | 0 | 14 | 9 | 5 | 2 | 0 | compute_level_blocks_086b_086c_086e ×10, gate_06e6_442_then_sync_046a_from_086b ×2, dispatch_on_0860, copy_0866_86b_to_1c04_1c3a |
| `0x086D` | 2 | 0 | 2 | 2 | 0 | 0 | 0 | gate_06e6_442_then_sync_046a_from_086b ×2 |
| `0x086E` * | 7 | 0 | 7 | 4 | 3 | 2 | 0 | compute_level_blocks_086b_086c_086e ×5, gate_06e6_442_then_sync_046a_from_086b ×2 |
| `0x1C39` | 5 | 0 | 5 | 2 | 3 | 0 | 0 | dispatch_on_0860, copy_0866_86b_to_1c04_1c3a, 3 in the `0xD221`/`0xD24E` case handlers (no enclosing export) |
| `0x1C3A` | 5 | 0 | 5 | 2 | 3 | 0 | 0 | dispatch_on_0860, copy_0866_86b_to_1c04_1c3a, 3 in the `0xD221`/`0xD24E` case handlers (no enclosing export) |
| `0x1F01` | 4 | 0 | 3 | 0 | 4 | 0 | 0 | init_1f01_1f06_1f07, FUN_CODE_d673, poll_1304_1500_dispatch_0083, 1 in bank1 (no export) |
| `0x1F07` | 5 | 0 | 3 | 0 | 5 | 0 | 0 | init_1f01_1f06_1f07, write_5a_to_1f07_then_spin, poll_1304_1500_dispatch_0083, magic_55aa_and_0704_countdown, 1 in bank1 (no export) |

`ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800` (run by
`.github/scripts/agent-gates.sh`) is the same check against the image: it
recomputes all three count keys for every entry and fails on a mismatch.

**The nine `0x1Cxx` rows (issue #250).** They are not in the sweep this
table is built from, which is a literal fifteen-address list; the counts and
directions below come from `xdata-1c3x-consumers-sites.csv` and are
reconciled field-for-field with this table on the ten rows the two share
(`0x1C39`, `0x1C3A` — 0 differences). The routines are named as in that
table's §2 and §4.

| addr | EC | PD | b0 | b1 | read | write | routines holding EC sites |
|---|---:|---:|---:|---:|---:|---:|---|
| `0x1C01` | 16 | 0 | 1 | 15 | 0 | 16 | stage_1c03_1c02_1c01, plus 15 bank-1 sites across 8 routines, 3 of them with no enclosing export |
| `0x1C02` | 13 | 0 | 1 | 12 | 0 | 13 | stage_1c03_1c02_1c01, plus 12 bank-1 sites across 8 routines, 3 of them with no enclosing export |
| `0x1C03` | 14 | 0 | 1 | 13 | 0 | 14 | stage_1c03_1c02_1c01, plus 13 bank-1 sites across 8 routines, 3 of them with no enclosing export |
| `0x1C12` | 5 | 0 | 1 | 4 | 0 | 5 | stage_0862_0865_into_1c12_1c14, FUN_CODE_9ce8, FUN_CODE_9d53, set_1c12_2_and_68c_81, set_1c12_0_and_68c_83 |
| `0x1C13` | 3 | 0 | 1 | 2 | 0 | 3 | stage_0862_0865_into_1c12_1c14, FUN_CODE_9ce8, FUN_CODE_9d53 |
| `0x1C14` | 3 | 0 | 1 | 2 | 0 | 3 | stage_0862_0865_into_1c12_1c14, FUN_CODE_9ce8, FUN_CODE_9d53 |
| `0x1C36` | 1 | 0 | 1 | 0 | 0 | 1 | stage_0862_0865_into_1c36_1c38 — the only site in any image |
| `0x1C37` | 1 | 0 | 1 | 0 | 0 | 1 | stage_0862_0865_into_1c36_1c38 — the only site in any image |
| `0x1C38` | 1 | 0 | 1 | 0 | 0 | 1 | stage_0862_0865_into_1c36_1c38 — the only site in any image |

The `0x1C02` row's `read 0` is a correction to the sweep's own `access`
column, which prints two of the thirteen as `read x1, write x1`. Both are
writes; the two `movx a,@dptr` it counts as reads load `0x03C4` and a
computed `0x03(A&0x7F)` at bank1 `0xE372`, and the XDATA address a CODE
table names at bank1 `0xE4AE`. `xdata-1c3x-consumers.md` §4.1 has the
listings.

## 9. What this does not establish

- **What the EC does with `0x086B`/`0x086C`/`0x086E`.** The arithmetic is
  legible; the units are not fixed by anything here. §10 is the step that
  would settle it.
- **What consumes `0x1C39`/`0x1C3A`, `0x1C12`-`0x1C14` or `0x1C36`-`0x1C38`.**
  **Answered, in the bounded form, by issue #250** — see §6's dated block and
  `ec/annotations/xdata-1c3x-consumers.md`. No consumer is named by any of
  ten methods, and the computed-DPTR remainder those methods cannot see is
  issue #110. What that does *not* settle is whether a consumer exists; the
  result is "not found by method X", and §7 of that document says which X.
- **Whether the case handlers at `0xD173`, `0xD198`, `0xD1C0`, `0xD1EF`,
  `0xD221` and `0xD24E` are complete functions.** They are reached by the
  `0x7151` reader's `jmp @a+dptr`, so no `lcall` names them and they have no
  function entry in the committed project. Seeding one needs
  `--mode rebuild-project`, which is out of scope here (two branches that
  both rebuild the 7 MB project cannot merge), so the addresses are named in
  this file rather than in `ghidra-functions.csv`. **That is a gap in
  coverage, not a finding about the bytes.**
- **The census's answer for the 14 addresses other than `0x0860`.** They carry
  `not recorded` in the `census` column, which says this work did not join the
  two methods for them and nothing about their direction. Recording the other
  fourteen is the same job in the same format.
- **That a `no census occurrence` cell means the byte is unused.** It means
  the decompile names no address at that site, and `0x0D31C` is the reason to
  be careful: a `MOV DPTR,#0x0860` the decompiler folded away is invisible to
  the census by construction, so every address reached that way is undercounted
  by the census alone. §11's last bullet.
- **Anything about the two programs' address spaces.** The 2 PD-image sites
  for `0x0860` are a separate program with its own XDATA map;
  `pd-xdata-overlap.md` is not reopened.

## 10. The live step, for a human with the machine

This is written down to be run later. **It has not been run**, and no result
from it is claimed anywhere in this file.

**The runnable form is
[`docs/hardware-tests/level-block-0860-086e.md`](../../docs/hardware-tests/level-block-0860-086e.md)**,
and it is the one a run is taken from: the five steps below are the question,
that file is the procedure, and the instrument is
`windows/tools/manual_fan_ctrl_probe.py --level-block --csv`. They are kept
separate so they cannot drift into two shapes the way §3 of
`manual-fan-ctrl-0751-isolation.md` and its probe did (issue #146) — a
procedure that is never run still has to be quotable, and quoting a number off
a tool instead of off the procedure is how that happened last time.

The question is narrow: are `0x086B`/`0x086C`/`0x086E` a fan-speed or a
power-level, and do they track the mode the selector `0x0860` chose?

1. With the machine at rest, dump `0x0860`-`0x086E` and note the mode.
   Expect `0x0860` at `0x00` — the idle mark of §4 — and the three result
   bytes wherever the last computation left them.
2. Switch modes once (the same vendor service or DSDT method the isolation
   run in `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` uses), and
   dump again. Watch `0x0860` and the three results.
3. If `0x0860` is seen at `0xFF`, that is the busy mark, and the transition
   is the dispatch in progress — the register is worth sampling faster than
   once a second to catch it.
4. Read the three result bytes against a known fan-speed readout for the
   mode. **A proportional relationship across three or more modes is what
   would justify a name; a constant, or nothing resembling the fan curve,
   is a result too and would say the block is not a level.**
5. The clamps are the cross-check: if the results ever sit exactly at `0x23`,
   `0x14` or `0x0F`, the clamp of §5 is live and `MANUAL_FAN_CTRL`/`AP_OEM_6`
   are gating it — record which, because that is a direct read of the guard
   conditions.

Only a live read beside a known quantity settles any of this. Until then the
entries stay `present-untested`, and the names stay placeholders.

## 11. What this changes, and what it leaves open

- **Four new rows** in `ec/annotations/ghidra-functions.csv`
  (`0x9D9B`, `0xA00E`, `0xD2EF`, `0xD304`) and **one corrected** (`0xD091`),
  each with a comment, a non-empty `evidence` path and `basis:
  hand-decoded`; `build_ec_decompile.py --check` confirms every address
  resolves to a real function.
- **15 new entries** in `ec/annotations/registers.yaml`, all
  `present-untested`, and `ec/ghidra/xdata-symbols.csv` regenerated from
  them by `gen_xdata_symbols.py` — never by hand.
- **`xdata-086x-dispatch-sites.csv` added**, the machine-readable table
  behind every number here.
- **Issue #281 joins the two direction methods instead of reconciling them in
  prose.** A ninth `census` column on that table, the per-site correspondence
  committed as **`xdata-0860-census-sites.csv`**, a
  **`ec/tools/check_site_census.py`** that holds the sweep, the correspondence
  and the census to each other and exits non-zero on any disagreement, its
  `test_check_site_census.py`, and `trace_xdata_refs.py --census-column` /
  `--check` so §1's reproduction is an assertion. The column is read from the
  correspondence file and is **not** derived from the image; §3 carries the
  sentence that says so and the four tokens that keep "not established" from
  reading as "checked and empty". `xdata-0860-census-sites.csv` covers
  `0x0860` only, and the other 14 addresses carry `not recorded`.
- **CORRECTION (2026-09-24, issue #281) to §3's opening sentence**, left
  visible in a dated blockquote there rather than only in the history, and
  **the stale `bank0/D091.c` line numbers in
  `HAND_CHECKED["0x0860"]`'s comment** corrected the same way: they were low
  (the seven `==` lines by 13, the dispatch argument by 12), every bucket total
  in that entry was right throughout, and
  `check_site_census.py` now re-checks them per site because a line number is
  not a number the census sums.
- **CORRECTION (2026-09-24, issue #249) to the bullet this section first
  carried**, which read: "**The census CSVs are read, not regenerated** (§3).
  Regenerating today would re-freeze the miscounted direction columns into
  the committed files." It reports a breakage that does not exist. The census
  CSVs are `xdata_register_map.py` output, kept current by its `--check`, in
  the same relationship `ec/ghidra/xdata-symbols.csv` has with
  `registers.yaml` through `gen_xdata_symbols.py`; §3 is the long form of
  this correction.
- **Issue #250 settles §6's open question in the bounded form**, and §11.1
  item 1 is closed by it rather than left open. Its own summary of what
  changed: the new **`ec/annotations/xdata-1c3x-consumers.md`** and its
  **`xdata-1c3x-consumers-sites.csv`** (67 rows, byte-for-byte reproducible
  by the command the document's §1 prints); **nine new `registers.yaml`
  entries** for `0x1C01`-`0x1C03`, `0x1C12`-`0x1C14` and `0x1C36`-`0x1C38`,
  all created **at** `present-untested` rather than promoted to it, with
  `ec/ghidra/xdata-symbols.csv` **regenerated** by `gen_xdata_symbols.py`
  and never hand-edited; **three new rows and one corrected** in
  `ghidra-functions.csv` (`0x9CE8`, `0x9D53`, `0xE2D3` new, `0xE490`
  corrected), all four resolving to existing exported functions so none needs
  `--mode rebuild-project`; the `0x1C02` direction corrected against two
  `.asm` listings; and a **conditional computed-DPTR writer found for
  `0x0862` and `0x086D`**, which corrects §2 above in place.
- **Open questions this reading raised**, for the follow-up pass:
  1. **CLOSED by issue #250, in the bounded form.** What consumes
     `0x1C39`/`0x1C3A` and the two staging trios: no consumer is named by any
     of ten methods, `0x1C36`-`0x1C38` have no read site in any image, and the
     `0x1C12` trio turned out to have five writers rather than one.
     `ec/annotations/xdata-1c3x-consumers.md` carries the method table, the
     reproduction, and the follow-ups it opens — issue #110's
     computed-DPTR remainder first, then a live read of `XDATA[0x0A56]` to
     settle whether §2's conditional writer ever fires.
  2. The six case handlers at `0xD173`-`0xD24E` have no function entry
     (§9). Seeding them is a `--mode rebuild-project` change.
  3. `0x0862` and `0x086D` have no writer this method can see (§2, §8). A
     computed-DPTR search, or a live read to see whether they ever move,
     would settle whether they are inputs or dead.
  4. **The decompiler-lost `MOV DPTR` at `0x0D31C`**, which the census cannot
     see because the decompile folded it away and `D319.c`'s body never names
     the address. That is a per-address undercount **by construction** for
     every address reached the same way, which is a wider question than this
     one site: how many other `no census occurrence` cells across the tree are
     the same shape rather than an absence. Worth its own issue; §9 says what
     the cell does and does not mean.
  5. The live step of §10, which needs the physical machine.
