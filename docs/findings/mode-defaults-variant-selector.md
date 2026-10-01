# Which writer seeds the per-mode PL defaults, and what the `0xABxx`/`0xC7xx` gate is (issue #111)

`ec/annotations/manual-fan-ctrl-0751.md` §5 quotes the block at `0x95C0`
writing `0x2D` to `0x0730`, records that `registers.yaml` has `0x3C` live
there, and calls the two "consistent with this block not being the branch
that runs on this machine — but 'consistent with' is all it is." This file
resolves what §5 left open, and it resolves it in a direction neither the
§5 sentence nor the framing of the issue anticipated.

Three answers, in the order the evidence forced them.

1. **The discriminator is GFID, `0x07D3`** — a byte `registers.yaml` already
   names (§3). It is a run-time value the EC computes at boot, not a
   build-time constant (§4).
2. **The discriminator does not change the values written.** All three seed
   tables are byte-identical over the sixteen bytes the copy reads (§5). So
   the twelve defaults come out the same whichever arm runs, and the
   `0x0730 = 0x3C` the issue asks about is produced by *all three*, not by one
   of them. The issue's fallback — "record the set of candidate branches and
   the read that would distinguish them" — is not needed, because the set does
   not exist: there is one answer, and it is not a set.
3. **The `0xABxx`/`0xC7xx` duplication is gated differently**, and neither
   gate is GFID (§7). The issue bundles the two questions as if they share an
   answer. They do not.

The `r2` transcripts are in §2, the tool in §9, and the live read that would
close the one thing static evidence cannot reach is
[`docs/hardware-tests/mode-defaults-variant-read.md`](../hardware-tests/mode-defaults-variant-read.md),
written and **not run**.

**What this file does not claim.** Nothing here is a measurement. The twelve
values derived in §5 are arithmetic over committed firmware bytes; the live
values they are compared against are `registers.yaml`'s 2026-09-23 read. That
the two agree is a strong consistency, and it is still not a statement about
which arm executed on any machine.

## 1. The routine, and the two writers

`site-resolution.csv` puts sixteen of the eighteen EC-side sites of the
twelve-byte block in one routine, `0x94D0 copy_code_table_into_0730_07a7`;
the other two are the three-instruction helpers `0xBEC8` and `0xBED2` that it
calls. So "several per-model variants" is one routine with several arms, and
the question is what picks the arm.

Two writers of `0x0730` sit in it:

| writer | value | reached when |
|---|---|---|
| `0x9527 movc A,@A+DPTR` | table byte 0 | always, once the entry gate passes |
| `0x95CD mov A,#0x2D` | `0x2D` | `0x0770 == 0x04` |

The second is the one §5 quotes. §6 takes it apart.

## 2. Spot-checks against an independent disassembler

Run per `manual-fan-ctrl-0751.md` §7's method, so a reader opening the
listing gets an independent read rather than this file's summary of it.

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x94d0; pd 21' /tmp/bank0.bin
```

```
            0x000094d0      900a50         mov dptr, #0x0a50
            0x000094d3      ef             mov a, r7
            0x000094d4      f0             movx @dptr, a
            0x000094d5      9007d3         mov dptr, #0x07d3
            0x000094d8      e0             movx a, @dptr
            0x000094d9      54f0           anl a, #0xf0
            0x000094db      6430           xrl a, #0x30
        ┌─< 0x000094dd      7026           jnz 0x9505
        │   0x000094df      12ba36         lcall 0xba36
       ┌──< 0x000094e2      7005           jnz 0x94e9
       ││   0x000094e4      900a51         mov dptr, #0x0a51
       ││   0x000094e7      800a           sjmp 0x94f3
       │└──> 0x000094e9      12ba36         lcall 0xba36
       │ │   0x000094ec      ff             mov r7, a
       │ │   0x000094ed      900a51         mov dptr, #0x0a51
       │┌──< 0x000094f0      bf0309         cjne r7, #0x03, 0x94fc
       └───> 0x000094f3      7461           mov a, #0x61
       ││   0x000094f5      f0             movx @dptr, a
       ││   0x000094f6      a3             inc dptr
       ││   0x000094f7      74fe           mov a, #0xfe
```

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9575; pd 5' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x95b7; pd 10' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xda22; pd 18' /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xab9e; pd 4'  /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xc709; pd 14' /tmp/bank0.bin
```

The `0x957C` and `0xDA26`/`0xDA30` lines matter more than the rest, and §3
is about why.

## 3. The bit operand, which is the one thing to get right

`0x957C` is `30 e2 1a`, and reading it wrong is the one mistake in this
area that would have been committed to a structured source of truth. The plan
written from the issue read the `0xe2` as the P2 latch, and therefore as a
bit of the address `0x0A51` had just been loaded into, rather than as a bit of
the byte `0x0782` read two instructions earlier — and proposed correcting the
`0x94D0` annotation row accordingly.

It is not. `0xE2` is the **bit address of ACC.2**; the P2 latch's bits are
`0xA0`–`0xA7`, so P2.2 would be `0xA2`. Three committed methods agree:

- `r2 -a 8051` prints `jnb acc.2, 0x9599`;
- `ec/tools/disasm8051.py` prints the same, from its own `BIT_SFR` table;
- **Ghidra's decompile of this very routine** reads the branch as
  `if ((BIOS_OEM_2 >> 2 & 1) == 0)`, and `BIOS_OEM_2` is `registers.yaml`'s
  name for `0x0782` (the decompiled `ec/decompiled/bank0/94D0.c`).

`mov dptr,#0xa51` at `0x9579` does not touch the accumulator, so at `0x957C`
`A` still holds the `0x0782` byte `0x9578` read. The branch is **bit 2 of
`0x0782`** — which is what the `0x94D0` row of `ghidra-functions.csv` has
always said.

The same reading settles `0xDA26` and `0xDA30` in `0xD9FE`, which the
`XDATA_1666` and `XDATA_166A` notes in `registers.yaml` already record as bit
2 of `0x1666` and bit 4 of `0x166A`. `mov A,#0x30` at `0xDA33` comes *after*
the `jnb` at `0xDA30`, so the accumulator still holds the `0x166A` byte.

**Consequence for the annotations: none, deliberately.** The `0x94D0` CSV row
needed no correction and has not been given one. Had the P2 reading been
written in, the tree would now hold a confidently wrong claim in a structured
source of truth, with a `*** CORRECTION ***` beside it saying so. The
committed row was right; this section is the receipt.

`ec/tools/variant_selector.py --self-test` holds the `0x957C` bytes and
separately asserts `bit_name(0xE2) == "acc.2"`, because a mnemonic comparison
alone would let a wrong-but-stable decoder pass.

## 4. The discriminator is GFID, and GFID is computed at run time

`0x94D5`–`0x94DD` load `0x07D3`, mask the high nibble and XOR `0x30`. The
seed block is reached only when that field is 3 — `registers.yaml` names it
**GFID**, so per the issue's own test this is not a new register.

Within the GFID == 3 arm a second condition applies: `0xBA36` returns the low
nibble of `0x074C`, and `0x94F0 cjne R7,#0x3` splits on it. The three
outcomes are the three seeds of §5.

So the chain is:

```
0x0A50  entry R7, stored by 0x94D3; non-zero tail-jumps to 0x95DD at 0x951F
0x07D3  GFID & 0xF0 == 0x30        -> 0x61/FE or 0x61/C8
        anything else               -> 0x61/0x92
0x074C  low nibble (within GFID == 3 only)
0x0770  == 0x04 -> the fixed bytes overwrite; else 0x9A0D
```

`0x0A51`/`0x0A52` are **not written only here** — `trace_xdata_refs.py` finds
bank0 writes at `0x873A` and `0xE7EA` for the high byte and at `0xE3A5` and
`0xE453` for the low one, none of them inside `0x94D0`. So the chain above is
what `0x94D0` does with the pair, not a claim that the pair's value always
reflects it. That is why §8's
read treats a pair disagreeing with `0x07D3` as a question rather than a
contradiction, and why none of this file reads the live bytes.

`0xD9FE seed_07d3_gfid_and_08xx_defaults` writes the whole byte at
`0xDA33`/`0xDA38`/`0xDA47`/`0xDA4C` as `0x30`, `0x40`, `0x50` or `0x70` —
GFID 3, 4, 5 or 7 — picking by bit 2 of `0x1666` and bit 4 of `0x166A`. So the
value the firmware branches on is computed by the EC at run time from the
`0x16xx` board-identification block. **That this machine's GFID is 3 is a
live value nobody has read**; §8 is the read.

## 5. The three seed tables are byte-identical — the finding

This is the part that changes the question. Read the sixteen bytes at each
of the three CODE pointers:

```console
$ for a in 0x61c8 0x61fe 0x6192; do r2 -a 8051 -e scr.color=0 -q -c "s $a; px 16" /tmp/bank0.bin; done
```

```
0x000061c8  3c3c a500 2323 a500 2323 a500 4b4b a500
0x000061fe  3c3c a500 2323 a500 2323 a500 4b4b a500
0x00006192  3c3c a500 2323 a500 2323 a500 4b4b a500
```

Identical. They diverge later (`0x61FE` from index `0x1A`, `0x6192` from
`0x33`), which does not matter: the copy reads indices `0x00`–`0x0F` and
nothing else.

So the twelve defaults are:

| XDATA | table index | stored value |
|---|---|---|
| `0x0730` | `0x00` | `0x3C` |
| `0x0731` | `0x01` | `0x3C` |
| `0x0732` | `0x02` | `0xA5` |
| `0x0733` | `0x03` + 1 | `0x01` |
| `0x0734` | `0x04` | `0x23` |
| `0x0735` | `0x05` | `0x23` |
| `0x0736` | `0x06` | `0xA5` |
| `0x0737` | `0x07` + 1 | `0x01` |
| `0x07A7` | `0x0C` | `0x4B` |
| `0x07A8` | `0x0D` | `0x4B` |
| `0x07A9` | `0x0E` | `0xA5` |
| `0x07AA` | `0x0F` + 1 | `0x01` |

— `3C 3C A5 01 / 23 23 A5 01 / 4B 4B A5 01`, which is **exactly** what
`registers.yaml` records live on 2026-09-23, all three four-byte groups. The
`+1` at `0x9547` and `0x9570` is why the table's `00` bytes appear as `01`.

The `0x0782` bit-2 branch is the same story one level down. Indices
`0x04`–`0x07` and `0x08`–`0x0B` hold the same four bytes, so the branch
selects between identical values.

**Therefore the answer to "which branch produces this machine's `0x3C`" is:
the `movc` path, and it does so under all three seeds.** The discriminator
named in §4 is real and does gate the routine — it just does not change the
result, which is the more interesting half and the one the issue's framing
("some other branch must produce `0x3C`") did not anticipate.

## 6. What §5's "consistent with" now rests on, and what it does not

§5 says the `0x2D` is "consistent with this block not being the branch that
runs on this machine". That remains the right shape of claim, and the reason
is now sharper than a value mismatch:

`0xB8C0` returns R7 = 1 when `0x0770 == 0x04`, and `0x95BB jnz` sends **that
case into** the block. So the fixed bytes are written when `0x0770 == 0x04`
and skipped when it is not — the polarity runs opposite to the obvious
reading, which is why "the block did not run" is not the same claim as
"`0x0770 != 0x04`" and neither is established here.

Two things must not be said about it:

- **Not** "the fixed arm did not run". That would be a statement about a
  machine, from static evidence.
- **Not** "`0x0770` must be something other than `0x04`". The live
  `0x3C` at `0x0730` is *consistent with* that, and consistency is the whole
  of it — the block could have run earlier and been overwritten by a later
  `movc`, or `0x0770` could have held `0x04` at a different moment than the
  recorded read.

§8 reads `0x0770` for exactly this.

## 7. The `0xABxx` / `0xC7xx` duplication, and why it is a different answer

No committed listing covers the `0xC7xx` run — `site-resolution.csv` records
it as not exported, and seeding a Ghidra function there needs a project
rebuild, which is a follow-up and not this change. The two copies were
therefore read out of the image with `disasm8051.py --at` and `r2`.

They are the same code. Aligning the shared tail at `0xABC7` ↔ `0xC720`
gives 25 instructions byte-identical and 9 differing only in a relocated
branch target or in the address of one callee — and that callee is not a
different function: `0xCA4C` and `0xBB40` are the same seven bytes,
`90 07 51 e0 54 90 22`, a three-instruction `0x0751 & 0x90` reader. So
"identical masks at identical relative offsets" is stronger than §2 claimed:
it is the same bytes modulo relocation.

The **entry gates differ**, which is the answer to the issue's second
question:

| | `0xABxx` copy | `0xC7xx` copy |
|---|---|---|
| entry | bit 1 of `0x0782` (`jnb acc.1`, `0xAB9E`) | — |
| | `0x0440` non-zero (`jz`, `0xABA9`) | `0x0440` non-zero (`jz`, `0xC71E`) |
| | `0x06E6 == 0x01` via `0xB9D8` (`0xABAB`) | — |
| | bit 5 of `0x1603` via `0xC1CB` (`0xABB0`) | bit 0 of `0x0741` (`jnb acc.0`, `0xC724`) |

The only gate byte the two share is `0x0440`, and neither set contains
`0x07D3`. The `0xABxx` copy is gated by a bit in the `0x16xx`
board-identification block — the issue's own contrast, and the right one.
**A driver cannot take the `0xC7xx` copy's behaviour as describing the
`0xABxx` one on the strength of a shared tail**, because the tails are entered
under different conditions.

The `cjne r0,#0x12` this was expected to hold does not exist. The issue's
own wording asked "find what `r0` holds at the head of the `cjne` chain", and
the plan written from it came back quoting `0x0C77E cjne r0,#0x12,0xc728` as
a real instruction in the `0xC7xx` run. There is no such instruction:
`0xC77D` is `7f b8` (`mov r7,#0xb8`) and `0xC77E` is its immediate, and
anchoring a linear decoder mid-instruction produces a confident
`cjne r0,#0x12,+0xa7` there. That is the mis-framing hazard §2's spot-checks
exist to catch, and it is why the `0xC7xx` chain above was read with r2 and
not from `disasm8051.py` alone. Recording it here because the same decoder
will be pointed at `0xC7xx` again.

**Both copies are entered the same way**, which is what makes them one
duplication rather than two coincidences. `bank-call-targets.csv`'s
`0xAB9A lcall 0xAB9E` row buckets as an `entry`, and
`task-call-table.csv` has thirteen `far-call-stub` rows reaching into the
`0xC7xx` run — `0x16C0 → 0xC761`, `0x16EA → 0xC711`, `0x1708 → 0xC717` and ten
more, indices 232–244. Nothing in the image `lcall`s or `ljmp`s to `0xC761`
directly, so a scan that looks only for direct transfers would find no caller
at all and conclude the run is dead.

## 8. What a live read would settle, and what it would not

`docs/hardware-tests/mode-defaults-variant-read.md` reads `0x07D3`, `0x1666`,
`0x166A`, `0x0770`, `0x0A50`–`0x0A52` and the twelve defaults at boot. It is
**written and not run**; no hardware was involved in this change and nothing
above reports a register read-back.

What it would settle: whether `0x0770` held `0x04`, which is the gate §6
turns on; and whether `0x0A51`/`0x0A52` hold one of the three seed pairs,
which would confirm which arm last ran — a *different* question from which
one is capable of running, which §5 has already answered.

What it would not settle: anything about whether the EC acts on the twelve
bytes. Nothing in this file establishes that, and the write direction found
here is a write direction.

## 9. The tool

`ec/tools/variant_selector.py` re-derives every claim above from
`ec/firmware/GMxMGxx_11.800`: the store sites of the twelve bytes and their
containing routines (joining through `ec/decompiled/listing-index.csv`, as
`check_site_resolution.py` does), the seed tables and their equality over the
copied window, the derived values, §7's tail alignment and its helper
comparison, and the two gate sets. `--self-test` holds the r2 transcriptions
of §2 as hand-typed bytes; `ec/tools/test_variant_selector.py` asserts the
claims and pins the refusals.

**No figure in this file is a count of the tree**, and none of the tool's
output asserts one. The suite asserts *which* addresses have *which* sites in
*which* routines and *which* bytes the tables hold — so it stays true when a
listing is exported or a suite lands, and goes red when the bytes move.

The table the tool derives, committed so `--check` has something to diff
against and a reader does not have to run anything:

```
variant_selector.py -- twelve-byte MODE_PL_DEFAULTS block
seeder 0x94D0   GFID byte 0x07D3   entry 0x0A50   seed pair 0x0A51/0x0A52

store sites of the twelve bytes, and the routine each sits in
  0x0730  0x9528 bank0  copy_code_table_into_0730_07a7
  0x0730  0x95CA bank0  copy_code_table_into_0730_07a7
  0x0731  0x9533 bank0  copy_code_table_into_0730_07a7
  0x0731  0x95D0 bank0  copy_code_table_into_0730_07a7
  0x0732  0x953C bank0  copy_code_table_into_0730_07a7
  0x0733  0x9548 bank0  copy_code_table_into_0730_07a7
  0x0734  0xBEC9 bank0  load_code_byte_to_0734
  0x0735  0x958A bank0  copy_code_table_into_0730_07a7
  0x0735  0x95A4 bank0  copy_code_table_into_0730_07a7
  0x0736  0xBED3 bank0  load_code_byte_to_0736
  0x0737  0x95B3 bank0  copy_code_table_into_0730_07a7
  0x0737  0x95D6 bank0  copy_code_table_into_0730_07a7
  0x07A7  0x9551 bank0  copy_code_table_into_0730_07a7
  0x07A7  0x95C0 bank0  copy_code_table_into_0730_07a7
  0x07A8  0x955C bank0  copy_code_table_into_0730_07a7
  0x07A8  0x95C6 bank0  copy_code_table_into_0730_07a7
  0x07A9  0x9565 bank0  copy_code_table_into_0730_07a7
  0x07AA  0x9571 bank0  copy_code_table_into_0730_07a7

seed pairs and the discriminator that picks each
  0x0A51=0x61 0x0A52=0xFE  -> CODE 0x61FE
  0x0A51=0x61 0x0A52=0xC8  -> CODE 0x61C8
  0x0A51=0x61 0x0A52=0x92  -> CODE 0x6192
  guard: 0x07D3 & 0xF0 == 0x30 (GFID == 3) reaches the first two; anything else reaches 0x61/0x92

the first 16 bytes at each seed table
  0x61FE  3C 3C A5 00 23 23 A5 00 23 23 A5 00 4B 4B A5 00
  0x61C8  3C 3C A5 00 23 23 A5 00 23 23 A5 00 4B 4B A5 00
  0x6192  3C 3C A5 00 23 23 A5 00 23 23 A5 00 4B 4B A5 00
  identical over the 16 bytes the copy reads: True

values each seed table yields for the twelve bytes
  0x61FE  3C 3C A5 01 23 23 A5 01 4B 4B A5 01
  0x61C8  3C 3C A5 01 23 23 A5 01 4B 4B A5 01
  0x6192  3C 3C A5 01 23 23 A5 01 4B 4B A5 01

the 0x0782 bit-2 index group, over the same table
  bit 2 clear, indices 0x04-0x07: 23 23 A5 01
  bit 2 set,   indices 0x08-0x0B: 23 23 A5 01
  the two groups agree on all four bytes: True

the fixed arm at 0x95C0, and the gate in front of it
  0xB8C0 returns R7 = 1 when 0x0770 == 0x04
  0x95BB `jnz` sends that case into the block, so:
    0x0770 == 0x04  -> the fixed bytes are written
    0x0770 != 0x04  -> 0x9A0D, and the table values stand
      0x07A7 <- 0x64
      0x07A8 <- 0x64
      0x0730 <- 0x2D
      0x0731 <- 0x3C
      0x0737 <- 0x01
  registers.yaml has 0x3C live at 0x0730; the fixed arm writes 0x2D there
  the table path writes 0x3C there, and the two differ: yes

the duplicated mode routines
  0xAB9E and 0xC717 share a tail aligned at 0xABC7 <-> 0xC720
  over 34 instructions from those anchors: 25 identical, 9 differing
  the differing ones are branch displacements and one callee; 0xBB40 and 0xCA4C are the same 7 bytes (`90 07 51 e0 54 90 22`), so the callee is not a different routine
  0xABxx gate  0x0782  bit 1 of 0x0782 (0xAB9E, `jnb acc.1`)
  0xABxx gate  0x0440  0x0440 non-zero (0xABA9, `jz`)
  0xABxx gate  0x06E6  0x06E6 == 0x01 via 0xB9D8 (0xABAB)
  0xABxx gate  0x1603  bit 5 of 0x1603 via 0xC1CB (0xABB0)
  0xC7xx gate  0x0440  0x0440 non-zero (0xC71E, `jz`)
  0xC7xx gate  0x0741  bit 0 of 0x0741 (0xC724, `jnb acc.0`)
  gate bytes the two copies share: 0x0440
  GFID (0x07D3) gates neither copy
```
variant_selector.py -- twelve-byte MODE_PL_DEFAULTS block
seeder 0x94D0   GFID byte 0x07D3   entry 0x0A50   seed pair 0x0A51/0x0A52

store sites of the twelve bytes, and the routine each sits in
  0x0730  0x9528 bank0  copy_code_table_into_0730_07a7
  0x0730  0x95CA bank0  copy_code_table_into_0730_07a7
  0x0731  0x9533 bank0  copy_code_table_into_0730_07a7
  0x0731  0x95D0 bank0  copy_code_table_into_0730_07a7
  0x0732  0x953C bank0  copy_code_table_into_0730_07a7
  0x0733  0x9548 bank0  copy_code_table_into_0730_07a7
  0x0734  0xBEC9 bank0  load_code_byte_to_0734
  0x0735  0x958A bank0  copy_code_table_into_0730_07a7
  0x0735  0x95A4 bank0  copy_code_table_into_0730_07a7
  0x0736  0xBED3 bank0  load_code_byte_to_0736
  0x0737  0x95B3 bank0  copy_code_table_into_0730_07a7
  0x0737  0x95D6 bank0  copy_code_table_into_0730_07a7
  0x07A7  0x9551 bank0  copy_code_table_into_0730_07a7
  0x07A7  0x95C0 bank0  copy_code_table_into_0730_07a7
  0x07A8  0x955C bank0  copy_code_table_into_0730_07a7
  0x07A8  0x95C6 bank0  copy_code_table_into_0730_07a7
  0x07A9  0x9565 bank0  copy_code_table_into_0730_07a7
  0x07AA  0x9571 bank0  copy_code_table_into_0730_07a7

seed pairs and the discriminator that picks each
  0x0A51=0x61 0x0A52=0xFE  -> CODE 0x61FE
  0x0A51=0x61 0x0A52=0xC8  -> CODE 0x61C8
  0x0A51=0x61 0x0A52=0x92  -> CODE 0x6192
  guard: 0x07D3 & 0xF0 == 0x30 (GFID == 3) reaches the first two; anything else reaches 0x61/0x92

the first 16 bytes at each seed table
  0x61FE  3C 3C A5 00 23 23 A5 00 23 23 A5 00 4B 4B A5 00
  0x61C8  3C 3C A5 00 23 23 A5 00 23 23 A5 00 4B 4B A5 00
  0x6192  3C 3C A5 00 23 23 A5 00 23 23 A5 00 4B 4B A5 00
  identical over the 16 bytes the copy reads: True

values each seed table yields for the twelve bytes
  0x61FE  3C 3C A5 01 23 23 A5 01 4B 4B A5 01
  0x61C8  3C 3C A5 01 23 23 A5 01 4B 4B A5 01
  0x6192  3C 3C A5 01 23 23 A5 01 4B 4B A5 01

the 0x0782 bit-2 index group, over the same table
  bit 2 clear, indices 0x04-0x07: 23 23 A5 01
  bit 2 set,   indices 0x08-0x0B: 23 23 A5 01
  the two groups agree on all four bytes: True

the fixed arm at 0x95C0, and the gate in front of it
  0xB8C0 returns R7 = 1 when 0x0770 == 0x04
  0x95BB `jnz` sends that case into the block, so:
    0x0770 == 0x04  -> the fixed bytes are written
    0x0770 != 0x04  -> 0x9A0D, and the table values stand
      0x07A7 <- 0x64
      0x07A8 <- 0x64
      0x0730 <- 0x2D
      0x0731 <- 0x3C
      0x0737 <- 0x01
  registers.yaml has 0x3C live at 0x0730; the fixed arm writes 0x2D there
  the table path writes 0x3C there, and the two differ: yes

the duplicated mode routines
  0xAB9E and 0xC717 share a tail aligned at 0xABC7 <-> 0xC720
  0xABxx gate  0x0782  bit 1 of 0x0782 (0xAB9E, `jnb acc.1`)
  0xABxx gate  0x0440  0x0440 non-zero (0xABA9, `jz`)
  0xABxx gate  0x06E6  0x06E6 == 0x01 via 0xB9D8 (0xABAB)
  0xABxx gate  0x1603  bit 5 of 0x1603 via 0xC1CB (0xABB0)
  0xC7xx gate  0x0440  0x0440 non-zero (0xC71E, `jz`)
  0xC7xx gate  0x0741  bit 0 of 0x0741 (0xC724, `jnb acc.0`)
  gate bytes the two copies share: 0x0440
  GFID (0x07D3) gates neither copy
```

## 10. Open

- **A `ghidra-functions.csv` row for the `0xC7xx` copy.** It has no exported
  listing. Seeding a function at an address with no function is what the
  annotation CSV is for, but it needs `--mode rebuild-project`, and two
  branches that both rebuild cannot merge. The row would name
  `0xC717 copy_of_mode_setter` with the §7 alignment as its comment.
- **Which copy of the mode routines runs.** §7 shows the *entry gates* differ,
  which is the static half; the run-time half is a live read of `0x0782`,
  `0x0440`, `0x06E6`, `0x1603` and `0x0741`, and nothing in this file says
  which of the two conditions holds on this machine.
- **The `0x0A54` store at `0xC711`**, which the `0xABxx` copy has no
  counterpart for, and the eleven other `0xC7xx` routines the stub table
  reaches.
- **Whether `0x0770` has a writer this tree can find.** Its
  `xdata-registers.csv` row records readers and no writer, so that is "not
  found by either committed method", not "absent" — and it has no
  `registers.yaml` entry.
