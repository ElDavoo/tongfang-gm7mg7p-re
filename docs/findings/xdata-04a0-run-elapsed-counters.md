# `0x04A0`/`0x04A1` is a mirror of `0x0524`, and `0x04AE`/`0x04AF` and `0x04BE`/`0x04BF` are up-counters (issue #732)

**Nothing here was observed on hardware.** No register was read, written or
read back, no site was seen run, no capture was taken. This is a static
reading of the committed listings under `ec/decompiled/` and of scans run
against the committed image `ec/firmware/GMxMGxx_11.800`. **Arithmetic is not
behaviour**: `0x3C == 60` below is a reading of two committed `.c` files, never
a statement that either word has ever held the value it computes. A `write` in
the census is an instruction, not an observation, and "not found by this
method" is never "absent" — `ec/annotations/registers.yaml`'s own header says so
and this file does not restate it as settled.

Issue #732 asked that `0x04AF`'s four writes be read before it was named,
"if the writes are the zeroing, say so". They are not the whole of it, and the
answer is in §2 rather than at the top of this file because the check is what
displaced the issue's premise.

## 1. The zeroing, byte for byte

Two routines in `bank1` clear bits of the `0x0490` gate byte and store `0x0000`
to one of the two counter words in the same breath. From the listings, which
win over the decompiled C wherever the two disagree:

```console
$ sed -n '25,34p' ec/decompiled/bank1/B841.asm
B860     90 04 90 mov      DPTR, #0x490
B863     e0 - -   movx     A, @DPTR
B864     54 f9 -  anl      A, #0xf9
B866     f0 - -   movx     @DPTR, A
B867     12 b8 8c lcall    0xb88c
B86A     12 b9 37 lcall    0xb937
B86D     79 00 -  mov      R1, #0x0
B86F     7a 00 -  mov      R2, #0x0
B871     90 04 ae mov      DPTR, #0x4ae
B874     12 88 8c lcall    0x888c
$ sed -n '25,34p' ec/decompiled/bank1/B8E1.asm
B900     90 04 90 mov      DPTR, #0x490
B903     e0 - -   movx     A, @DPTR
B904     54 9f -  anl      A, #0x9f
B906     f0 - -   movx     @DPTR, A
B907     12 b9 1b lcall    0xb91b
B90A     12 b9 62 lcall    0xb962
B90D     79 00 -  mov      R1, #0x0
B90F     7a 00 -  mov      R2, #0x0
B911     90 04 be mov      DPTR, #0x4be
B914     12 88 8c lcall    0x888c
```

`anl A,#0xf9` clears bits 0, 1, 2 and 6 of `0x0490`; `anl A,#0x9f` clears bits
5 and 6. **Bit 1 is one of the bits the first routine clears**, and bit 1 is
the gate `charge_target_update` is reached on: `ec/decompiled/bank0/B158.c`'s
own header says "Reached by a conditional branch from 0xB141 (`jb acc.1` on
XDATA `0x0490` bit 1)", and `ec/decompiled/bank0/B12C.asm` is the two lines
that do it —

```console
$ sed -n '18,19p' ec/decompiled/bank0/B12C.asm
B141     90 04 90 mov      DPTR, #0x490
B144     e0 - -   movx     A, @DPTR
```

— `B145` being the `jb 0xe1, 0xb158` the next line carries. `0xB841` and
`0xB8E1` are named `arm_05f2_countdown_0575_clears_0490` and
`arm_05f4_countdown_0576_clears_0490` in the annotation CSV; both write `3` to
a byte (`0x05F2` / `0x05F4`) before testing the gate bit, which is where
"armed" in the names below comes from.

`ec/decompiled/bank1/BFD9.asm` is a third site and carries nothing else at all
— the same two 16-bit stores and a `ret`:

```console
$ sed -n '7,13p' ec/decompiled/bank1/BFD9.asm
BFD9     79 00 -  mov      R1, #0x0
BFDB     7a 00 -  mov      R2, #0x0
BFDD     90 04 ae mov      DPTR, #0x4ae
BFE0     12 88 8c lcall    0x888c
BFE3     90 04 be mov      DPTR, #0x4be
BFE6     12 88 8c lcall    0x888c
BFE9     22 - -   ret
```

## 2. The issue's check: the writes are not all zeroing

Issue #732 asked the note to "record explicitly that no committed routine has
been read setting them non-zero", and to check the four writes first. The check
fails that sentence. `ec/decompiled/bank1/BFBB.c` **increments** the word at
`0x04AE`/`0x04AF`:

```console
$ sed -n '21,26p;35,40p' ec/decompiled/bank1/BFBB.c
  if ((DAT_EXTMEM_0490 >> 3 & 1) == 1) {
    DAT_EXTMEM_04ad = DAT_EXTMEM_04ad + 1;
    if ((DAT_EXTMEM_04ad != 0x3c) && (DAT_EXTMEM_04ad < 0x3c)) {
      return;
    }
    DAT_EXTMEM_04ad = 0;
  bVar1 = DAT_EXTMEM_04ae == -1;
  DAT_EXTMEM_04ae = DAT_EXTMEM_04ae + '\x01';
  bVar3 = DAT_EXTMEM_04af + bVar1;
  if (!CARRY1(DAT_EXTMEM_04af,bVar1)) {
    DAT_EXTMEM_04af = bVar3;
  }
```

`bVar1` is `0x04AE == -1`, the increment's carry into the high byte — a 16-bit
`+1` read out of machine code, not a claim about the C. The word in front of it
is the byte in front of it that gates it: the routine counts `0x04AD` up, and on
the tick where it reaches `0x3C` and wraps, it counts the word once.
`ec/decompiled/bank1/C0A8.c` does the same for `0x04BE`/`0x04BF`, off `0x04BD`
reaching `0x3C` (`C0A8.c:18-22` and `:31-36`), and `BFBB` reaches it through
its `FUN_CODE_c0a8()` call at `BFBB.c:74`. The census's `functions` column
agrees and is narrower than the whole page: `0x04AD` and `0x04BD` each have
exactly one touching function, `BFBB` and `C0A8` respectively.

`BFBB` also clears both words, on the path where `0x0490` bit 0 is clear —
`BFBB.c:77-81` returns immediately when that bit is set, and otherwise stores
zero to `0x04AE` and `0x04BE`. So `B841`, `B8E1`, `BFD9` and `BFBB` are the
committed routines that store `0x0000` to these words, and `BFBB` and `C0A8`
are the ones that increment one. **The `0x0490` byte is not what every site
shares**: `BFD9` is the two stores and a `ret` and reads no `0x0490` byte, and
neither does `C0A8`, whose XDATA is `0x0472`, `0x0499`, `0x04BD`-`0x04BF` and
`0x0579`-`0x057C`. What the zeroing sites that do read it share is narrower
still — `BFBB` zeroes on its bit-0-clear path, a different bit from the two
`arm_*` routines.

## 3. What the counters are compared against

Both routines then compare the word against a byte times `0x3C`. From
`BFBB.c:45-52`, the multiplier is `0x057B`, or `0x057C` when `0x0472` bit 5 is
set, and `BFBB.c:59-61` repeats it with `0x057D` on the second path;
`C0A8.c:44-45` is the same comparison with `0x057B`/`0x057C`. The result lands
in bits of a flag byte — `0x0494` cleared at `BFBB.c:63` and set with
`& 0xf3 | param_2` at `BFBB.c:69`, and `0x049C` set the same way at
`C0A8.c:47`, with `param_2` being 4 or 8.

So the committed decompiles establish: an up-counter, counted once per `0x3C`
ticks of the byte in front of it, compared against a byte times `0x3C`, zeroed
along the paths §2 names, and setting bits in `0x0494`/`0x049C` when the
comparison goes the way the routine expects. `0x3C == 60` is arithmetic on the
committed `.c`; **no unit is claimed**, because nothing committed establishes
how often `BFBB` or `C0A8` is entered — see §7.

## 4. `0x04A0`/`0x04A1` is a mirror of `0x0524`/`0x0525`

Issue #732 read the `0x04A0`-`0x04C0` run as "a staging area of 16-bit slots".
The copy sites argue for a narrower reading of this pair.

`ec/decompiled/bank1/D0C4.c` mirrors `0x0524` into both `0x0526` and `0x04A0`
and clears both high bytes, at the top of the routine and again at the bottom:

```console
$ sed -n '29,33p;87,91p' ec/decompiled/bank1/D0C4.c
  DAT_EXTMEM_0526 = DAT_EXTMEM_0524;
  DAT_EXTMEM_04a0 = DAT_EXTMEM_0524;
  DAT_EXTMEM_0525 = 0;
  DAT_EXTMEM_0527 = 0;
  DAT_EXTMEM_04a1 = 0;
  DAT_EXTMEM_03c1 = 99;
  DAT_EXTMEM_0524 = 0x20;
  DAT_EXTMEM_0526 = 0x20;
  DAT_EXTMEM_04a0 = 0x20;
  DAT_EXTMEM_0492 = 0x20;
```

`ec/decompiled/bank1/B2D5.asm` is the same store from the other side, and shows
it is 16-bit rather than a byte copy: it loads `0x0524`, calls `0xB6C9`, and on
carry clear stores to `0x04A0` through the 16-bit writer `0x888C`.

The readers are what separate the two readings. **They test individual bits
across the two bytes**, which is what a mirror predicts and a staging slot does
not:

| byte | bit test | where |
|---|---|---|
| `0x04A0` | bit 5 | `ec/decompiled/bank1/B2A0.c:23`, `ec/decompiled/bank1/AD8B.c:35` |
| `0x04A1` | bit 6 | `ec/decompiled/bank1/BA43.c:27` |
| `0x04A1` | `& 0x90` | `ec/decompiled/bank1/BA43.c:49`, `ec/decompiled/bank1/C11C.c:32,43` |

`ec/decompiled/bank1/BA43.c:26-27` reads `0x04A0` into a parameter in the
same condition that tests `0x04A1` bit 6 — one reader pulling from both bytes
at once. A staging area holds a value between two writers; this one has two
writers that both take their value from `0x0524`, and readers that pick bits out
of it without a reader ever being the reason it was written. That is a mirror.
The issue's framing is kept here as the weaker inference the copy sites alone
support, because it is what the copy sites alone do support — the bit tests are
what displace it.

## 5. The `+0x10` column

The two counters are the same column ten bytes apart: `0x04AD` → `0x04BD`,
`0x04AE` → `0x04BE`, `0x04AF` → `0x04BF`. The byte that gates each is a
`+0x10` translation of the other, the gate bits differ (`BFBB` runs under
`0x0490` bit 3, and the two arming routines sit on `0x0490` bits 1 and 5), and
the two flag bytes the comparison feeds — `0x0494` and `0x049C` — are a `+0x08`
pair. The census records this as far as it records anything about structure:
`0x04AE`/`0x04AF` sit in span group `0x048A-0x04AF` with `0x04AD` in a cluster
of its own, `0x04BE`/`0x04BF` in span group `0x04BD-0x04BF` with `0x04BD`.

That is a shape, not a layout. **Whether the `+0x10` spacing is a column of
paired slots or two unrelated fields that happen to be ten apart is not
established here**, and no field layout is claimed for the rest of the
`0x04A0`-`0x04C0` run — `0x04AB`/`0x04AC` and `0x04A2`/`0x04A3` have their own
chains, written up elsewhere (`docs/findings/pack-temp-producer-chain.md` for the
latter, which is issue #715's and this work does not touch).

## 6. Counts

`MOV DPTR,#addr` site counts, recomputed from the committed image. The address
split is `trace_xdata_refs.py`'s and is the same one every `static_refs*` column
in `registers.yaml` is stated on; the `PD image` column is a **different
program's bytes at the same address numbers** and is never added to `main EC`.

| pair | file-wide | main EC | PD image |
|---|---|---|---|
| `0x04A0` / `0x04A1` | 9 / 8 | 9 / 5 | 0 / **3** |
| `0x04AE` / `0x04AF` | 6 / 1 | 6 / 1 | 0 / 0 |
| `0x04BE` / `0x04BF` | 3 / 1 | 3 / 1 | 0 / 0 |

```console
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

`0x04A1`'s three PD-image sites are that program's bytes, not this EC's high
half, and `PACK_TEMP_DK`'s note is the precedent for what to do with the same
collision on `0x04A3`: name the split, do not sum it. These figures are **not**
the census's. `ec/annotations/xdata-registers.csv` gives `0x04AF` 11 references
(7 read, 4 write) because it counts every pair-accessor call, and the single
`MOV DPTR` above is a different method finding a different thing; both are in
`registers.yaml` and neither is a behaviour.

## 7. What this does not establish

- **The tick rate, and therefore the unit.** `BFBB` and `C0A8` are counted once
  per `0x3C` ticks of a byte in front of them, and `0x3C` is 60. Nothing
  committed says how often either routine runs, so neither word can be given a
  unit. They are named `COUNTER_A` and `COUNTER_B` and not `*_SECONDS` or
  `*_MINUTES` for that reason. **This is the one open question here that needs
  the physical machine**: capture `0x04AE`/`0x04AF` against a wall clock across
  a charge and divide.
- **Who sets `0x0490` bits 1 and 5.** This file reads them being cleared and
  does not establish what sets them. Each has a candidate in the tree rather
  than an open search: `bank1` `0xB784` sets bit 1 with `& 0xeb | 2` and
  `0xB80A` `arm_05f5_countdown_0490_bit5` sets bit 5 with `& 0xbf | 0x20`, each
  after its own countdown reaches zero. Neither is shown here to be what puts
  `0xB158` on the path — that is a separate claim, and what these two establish
  is only that a setter exists. "Not found by this method" remains the honest
  wording for anything beyond them, not "nothing sets them".
- **The `+0x10` column's extent.** §5 establishes the three `+0x10`
  correspondences the three entries' own functions show and no more. Whether the
  rest of the run repeats the shape is open, and `0x0490` has no
  `registers.yaml` row, so nothing here should be read as documenting it.
- **That the words are on the charge-target path in the sense that matters.**
  `0x0490` bit 1 is the gate `charge_target_update` is reached on, and bit 1 is
  among the bits `0xB841` clears in the same breath as it zeroes
  `0x04AE`/`0x04AF`. That is a statement about control flow read out of
  committed listings. Whether the counters feed the derating is not established,
  and `charge-target-derating.md` §3 says so where this work replaces its
  "not decoded" line.
- **Nothing was observed live, and a register the EC arms and disarms is not
  thereby a register a Linux driver should write.** These three pairs are
  `present-untested` in `registers.yaml` and none of them should become a driver
  write target on the strength of this file. `0x0522`'s host-read-only note is
  how this tree words the refusal.

## 8. The suite

`ec/tools/test_xdata_04a0_run_counters.py` reads committed files and the
committed firmware image — no Ghidra, no network — and re-derives §1 through §5
out of the `.asm` and `.c` files rather than out of this file, so a regenerated
decompile that moves one of these sites turns the suite red and this page gets
re-checked. Each byte assertion is made twice, once against the listing's
operand text and once against the image at the runtime address, so a listing
that drifted from the firmware fails rather than agreeing with itself. It also
holds the note shape: each `registers.yaml` note has to name the functions it
relies on, carry both sentences in §7's last bullet, and not assert a unit.

**The suite is not wired into `.github/scripts/agent-gates.sh`.** That file
lives under `.github/`, which this branch's push token cannot write, so
registering it is a human's one-line change; `ec/annotations/xdata-inc-dptr-only.md`
§1 records the same situation and the same reason for
`test_inc_dptr_sites.py`. Until that is done the suite is run by hand and this
file does not imply CI runs it.

## 9. A follow-up

The symbols in `ec/ghidra/xdata-overrides.csv` land in the decompiled C only on
the next `--mode rebuild-project`. Until then **the committed `.c` files still
spell these `DAT_EXTMEM_04a0`, `DAT_EXTMEM_04af` and `DAT_EXTMEM_04be`**, which
is why this file cites addresses and function names throughout and never the
symbol names. Two branches that both rebuild the project cannot merge, so the
rebuild is a single branch's change and not this one's.