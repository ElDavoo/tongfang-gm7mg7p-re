# `0x0860`-`0x086E`: the EC's own level block, and what it dispatches on

Issue #180 asked to read the `0x0860`-`0x086E` run in main-EC cluster
`main-ec-002` and settle four questions: what sets `0x0860`, what the sibling
bytes hold, what consumes the `0x1C39`/`0x1C3A` copy, and whether the
`0x044C`-`0x05F1` group is the same mechanism. This is the answer. The
machine-readable table behind every number here is
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
      0x086D 0x086E 0x1C39 0x1C3A 0x1F01 0x1F07 --csv \
  | diff - ec/annotations/xdata-086x-dispatch-sites.csv
```

That is the whole sweep, it is read-only, and it needs no hardware. The
`0x044C`-`0x05F1` group of §6 is swept the same way, and the case table of §4
is re-derived by `ec/tools/decode_index_table.py ec/firmware/GMxMGxx_11.800
--at 0xD148`.

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

## 3. The `0x0860` census row is wrong, and here is the mechanism

**Every direction claim in this file comes from `trace_xdata_refs.py` or
from a `.asm` listing, never from the `read`/`write` columns of
`xdata-registers.csv`.** That is deliberate, and the reason is worth
recording.

`ec/tools/xdata_register_map.py:138` defines

```python
ASSIGN = ("=", "|=", "&=", "+=", "-=", "*=", "/=", "^=", "%=", "<<=", ">>=")
```

and `store_target()` at line 277 decides "is this the assignment target" by
testing whether the text following the occurrence starts with any member of
`ASSIGN`. A Ghidra comparison spells `==`, which also starts with `=`, so
**every comparison is counted as a store**. Running the committed
`classify()` over `ec/decompiled/bank0/D091.c` returns `write` for eleven of
its fourteen `==` sites on `0x0860` and `read+write` for the other three,
because the chained `||` forms put the address on the right-hand side of the
`==` as well; the one genuine read, the `switch_case_dispatch(XDATA_0860)`
site, is bucketed `passed-to-call`. So no occurrence in that file is
classified `read` at all. The "14 of 17 references are `==`" figure the issue
quotes is unaffected by that split, and now accounted for.

The census row for `0x0860` therefore reads 13 `write`, 3 `read+write`, 1
`passed-to-call`, **0 `read`**. The truth by the other method is **4 reads
and 2 writes** in bank 0, plus one site that loads DPTR and returns with no
`movx`, plus 2 sites in the PD image. `0x0860` is not a near-pure
write-side byte, and this file says so with the method named on every count.

**The census is read and cited here, never regenerated.** Re-running
`xdata_register_map.py` today would re-freeze 838 miscounted occurrences
across 211 addresses into the committed CSVs and make the wrong row look
authoritative. Fixing the classifier is a separate change; the reading is
complete without it, because `trace_xdata_refs.py` decodes opcodes rather
than C and is unaffected.

One pre-existing condition, recorded rather than fixed: the census's own
`--check` and `--self-test` already fail on `main` for an unrelated reason
(`0x0400` gained the name `BAT_POWER_UNIT_0` and the CSVs were not
regenerated), and 60 symbol-table addresses are named but not yet spelled in
the decompile. That is staleness independent of this cluster.

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
census's "0 reads" is what made that hard to see. Two things that are *not*
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
reads.

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

## 9. What this does not establish

- **What the EC does with `0x086B`/`0x086C`/`0x086E`.** The arithmetic is
  legible; the units are not fixed by anything here. §10 is the step that
  would settle it.
- **What consumes `0x1C39`/`0x1C3A`, `0x1C12`-`0x1C14` or `0x1C36`-`0x1C38`.**
  Not answered by the decompile, and not inferred from co-occurrence.
- **Whether the case handlers at `0xD173`, `0xD198`, `0xD1C0`, `0xD1EF`,
  `0xD221` and `0xD24E` are complete functions.** They are reached by the
  `0x7151` reader's `jmp @a+dptr`, so no `lcall` names them and they have no
  function entry in the committed project. Seeding one needs
  `--mode rebuild-project`, which is out of scope here (two branches that
  both rebuild the 7 MB project cannot merge), so the addresses are named in
  this file rather than in `ghidra-functions.csv`. **That is a gap in
  coverage, not a finding about the bytes.**
- **The census's `--check`/`--self-test`**, which fail on `main` for the
  unrelated `0x0400` reason in §3.
- **Anything about the two programs' address spaces.** The 2 PD-image sites
  for `0x0860` are a separate program with its own XDATA map;
  `pd-xdata-overlap.md` is not reopened.

## 10. The live step, for a human with the machine

This is written down to be run later. **It has not been run**, and no result
from it is claimed anywhere in this file.

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
- **The census CSVs are read, not regenerated** (§3). Regenerating today
  would re-freeze the miscounted direction columns into the committed files.
- **Open questions this reading raised**, for the follow-up pass:
  1. What consumes `0x1C39`/`0x1C3A` and the two staging trios — the single
     most useful thing a follow-up could settle, and it needs the code
     around the handlers, not a live test.
  2. The six case handlers at `0xD173`-`0xD24E` have no function entry
     (§9). Seeding them is a `--mode rebuild-project` change.
  3. `0x0862` and `0x086D` have no writer this method can see (§2, §8). A
     computed-DPTR search, or a live read to see whether they ever move,
     would settle whether they are inputs or dead.
  4. The live step of §10, which needs the physical machine.
