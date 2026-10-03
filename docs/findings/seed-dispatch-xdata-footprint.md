# What the trio the old gate comment blamed actually does to XDATA, and the one seed byte still unexplained (2026-10-03, issue #628)

The gate comment that #628 was filed against named three functions by address and
said the self-test was red because `index.csv` spelled them `FUN_CODE_*`. That
reason was settled under #815 and is recorded in
[`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md). What was never
done is the thing the comment's three addresses invite: **read them, and say what
they do to XDATA registers.** This file does that, from the committed listings,
and cross-checks the result against the census in both directions.

The three are `bank1:0x9CE8` `seed_1c12_trio_or_update_1c11_1c15_1c16`,
`bank1:0x9D53` `seed_1c12_trio_9f_or_run_0x9d7a_ladder`, and `bank1:0xE2D3`
`dispatch_036c_low3_then_seed_1c00_block`. Per this repository's standing order
the `.asm` is right and the `.c` is a reading of it.

## The footprint, from the listings

Every `movx` in the three listings, with `DPTR` tracked across `mov dptr,#imm`,
`mov DPH` and `mov DPL`, so a recomputed pointer is not silently read as the
previous one:

| function | XDATA addresses touched | `movx` reads / writes |
|---|---|---|
| `0x9CE8` | `0x043F` `0x068B` `0x068D` `0x1C11` `0x1C12` `0x1C13` `0x1C14` `0x1C15` `0x1C16` | 3 / 10 |
| `0x9D53` | `0x044F` `0x0456` `0x045B` `0x0466` `0x068B` `0x068C` `0x068D` `0x0694` `0x069D` `0x1C11` `0x1C12` `0x1C13` `0x1C14` `0x1C15` `0x1C16` | 10 / 17 |
| `0xE2D3` | `0x036C` `0x03A1` `0x03C4` `0x045F` `0x0680` `0x1C00` `0x1C01` `0x1C02` `0x1C03` `0x1C04` `0x1C05` | 11 / 12 |

The counts are per `movx` site, not per byte. **Five of these addresses are
genuinely read-modify-written** — loaded into A, changed in A, stored back — and
that matters for a driver author, because a blind store can destroy a bit a host
set while a read-modify-write provably preserves every bit the EC does not name:

| address | function | the change |
|---|---|---|
| `0x068D` | `0x9CE8`, `0x9D53` | `dec` |
| `0x069D` | `0x9D53` | `inc`, and only when the value was not already `0x0A` |
| `0x0694` | `0x9D53` | `add #0x02`, and only with no carry out |
| `0x044F` | `0x9D53` | `add R1`, then `rrc` — the `0x1C15` averaging step |
| `0x03C4` | `0xE2D3` | `orl #0x40` at one site, `inc` at another |

`0x068B` and `0x068C` are the counter pair `0x9D53` and `0xE2D3` write on
almost every exit, and `0x1C11` is read early and written `0xFF` later on paths
where the read is not the write's source — so those are **not** counted as
read-modify-write here, and a reader counting "read then later write" in the
listing rather than following A would get them wrong.

**`0x9CE8` and `0x9D53` are the same routine with two constants changed.** Their
countdown prologue is ten instructions, identical instruction for instruction
except its own branch targets, and the `0x1C11 == 0` seed block that follows is
thirteen instructions of which **eleven are identical**: the two that differ are
the `jnz` target (a consequence of the different code after it) and the immediate
at `0x9D00` / `0x9D91`, `0x99` against `0x9F`. Both write `0x48` to `0x1C12` and
`0x00` to `0x1C13`; only the `0x1C14` byte differs, and **nothing in either
listing says why those two bits differ.**

## What the census says about the same three, and where the two agree

Checked both directions — every address a listing touches is attributed to that
function in `xdata-registers.csv`, and every address the census attributes to a
function appears in that function's listing:

- `0x9CE8` and `0x9D53`: **exact correspondence, no address on either side
  unaccounted for.**
- `0xE2D3`: the census attributes four addresses the listing does not contain —
  `0x036E`, `0x036F`, `0x03AF`, `0x0681`. These arrive through the C, not the
  listing: `0x036E` is the argument to the call `read_xdata_pair_to_r1r2(0x36e)`,
  and `0x03AF` and `0x0681` are written in code the decompiler reached past the
  listing's extent, in the arms that `increment_03af_clear_03a1_on_wrap` owns.
  That is the `beyond-listing-extent` case
  [`c_asm_counterpart.py`](../../ec/tools/c_asm_counterpart.py) exists to name,
  and it is a property of the export's cut rather than a disagreement about the
  firmware.

**One caveat on reading the census's direction columns as per-function facts.**
`xdata-registers.csv`'s `read` / `write` / `read+write` columns are **counts of
occurrences of the address token in the decompiled C text**, one bucket per
occurrence, produced by `xdata_register_map.py`'s `classify()`; they are not
per-site and not per-function. The genuinely per-function columns are `readers`
and `writers`, which are built from the per-(address, function) bucket *set*. So
the footprint table above is derived from the listings rather than read out of
those columns, and a `read+write` cell in the CSV means one C expression is a
read-modify-write — **not** that a function both reads and writes the byte. The
two vocabularies legitimately disagree and the repository says so.

## What `0x9CE8`'s callee at `0x9CD8` actually computes

`0x9CE8`'s second arm calls `0x9CD8` with `DPTR = 0x0615` and
`R1 = XDATA 0x1C15`, then stores **A** to `0x043F` if carry came back clear
(`bank1/9CE8.asm` at `0x9D25`–`0x9D2D`). The callee's listing is three-term, not
two: it adds `R1` into the **low** byte at `DPTR`, halves that, stores it back,
`inc DPTR` to the **high** byte at `0x0616`, adds the halved low byte into that,
and halves that too — so it returns with **A holding the high-byte result**:

```
((XDATA 0x0616 + ((XDATA 0x0615 + XDATA 0x1C15) >> 1)) >> 1)
```

That is what `0x043F` receives. Simulating the listing instruction for
instruction, `lo = 0x61`, `hi = 0x62`, `R1 = 0x10` returns `0x4D`, which is what
the three-term expression gives and not what the two-byte one would. The
decompiled C agrees: `bank1/9CE8.c` reads
`uVar1 = halve_be16_after_add_r1(0x615,DAT_EXTMEM_1c15); ... XDATA_043F = uVar1;`.

On the two overflow paths the routine differs in what it has already written. If
the **low**-byte addition overflows it branches straight to `ret` having written
nothing; if the **high**-byte addition overflows the halved low byte has already
been stored, and the routine returns carry set without touching `0x0616`. Either
way the caller's `jc` skips the `0x043F` store.

Nothing in either listing accumulates across calls, so this is a **per-call**
half-sum and not evidence of a running average — an argument that rests on the
census row rather than on the arithmetic: `0x043F` has `writers=1` and
`single_function=yes`, so nothing else in the committed tree writes it. A single
writer is a fact about the listings, not evidence the EC acts on it, so its
`status:` stays where it is.

## What this does not establish

Nothing here is a hardware or Windows observation. Every claim above is read off
the committed `.asm` listings; where the arithmetic was checked, it was by
simulating the listing instruction for instruction, not by reading the generated
C.

The units of `0x1C12`–`0x1C14` remain undetermined, and the `0x99` / `0x9F`
difference remains unexplained — this file locates the two differing bytes
exactly and does not guess why. No consumer of the trio is found by any of the
ten methods in [`xdata-1c3x-consumers.md`](../../ec/annotations/xdata-1c3x-consumers.md)
section 7, and that negative is scoped to those methods. No register's `status:`
in `registers.yaml` moves on any of this.