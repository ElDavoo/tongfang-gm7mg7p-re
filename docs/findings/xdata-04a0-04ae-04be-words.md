# The `0x04AE`/`0x04BE` up-counters, and the `0x04A0`/`0x04A1` provenance (issue #732)

**Nothing here was observed on hardware.** No register was read, written or
read back, and no site was seen run. This is a static reading of committed
listings (`ec/decompiled/`) and committed scans run against the committed image
`ec/firmware/GMxMGxx_11.800`. **Arithmetic is not behaviour**: the `0x3C` below
says what a byte sequence computes, never that a byte held that value, that a
code path executes, or that the EC acted on it. A `write` in a census is an
instruction, not an observation, and "not found by this method" is never
"absent" — `ec/annotations/registers.yaml`'s own header says so and this file
does not restate it as settled.

Four addresses enter `registers.yaml` here: `0x04AE`/`0x04AF` and `0x04BE`/`0x04BF`
as two 16-bit up-counters whose zeroing rides the `0x0490` gate bits, and
`0x04A0` and `0x04A1` as **two separate bytes**, because the listing gives them
different provenances and the pairing that was proposed for them does not hold
(§4). The counters are new: nothing in `main` named them, and the two words sit
on the charge-target path through the same gate bit.

Every function here is cited by name and by address (`bank1 0xB841`), never by
`file:NNN`; where a byte run is the point, the prose anchors on the address
range the way the console transcripts do.

## 1. The two zeroing sites, composed from the listings

The two arming routines clear `0x0490` bits and store `0x0000` to a counter word
in the same run. `ec/decompiled/bank1/B841.asm`, `0xB860`–`0xB874`:

```
B860     90 04 90 mov      DPTR, #0x490
B863     e0 - -   movx     A, @DPTR
B864     54 f9 -  anl      A, #0xf9        <- clears bits 1, 2
B866     f0 - -   movx     @DPTR, A
B867     12 b8 8c lcall    0xb88c
B86A     12 b9 37 lcall    0xb937
B86D     79 00 -  mov      R1, #0x0
B86F     7a 00 -  mov      R2, #0x0
B871     90 04 ae mov      DPTR, #0x4ae
B874     12 88 8c lcall    0x888c          <- 16-bit store of 0x0000
```

`0xf9` is `0b11111001`, so the mask clears **bits 1 and 2**. `ec/decompiled/bank1/B8E1.asm`,
`0xB900`–`0xB914` is the same shape with `anl A,#0x9f` — `0b10011111`, bits
5 and 6 — and `DPTR,#0x4be`:

```
B900     90 04 90 mov      DPTR, #0x490
B903     e0 - -   movx     A, @DPTR
B904     54 9f -  anl      A, #0x9f        <- clears bits 5, 6
B906     f0 - -   movx     @DPTR, A
B907     12 b9 1b lcall    0xb91b
B90A     12 b9 62 lcall    0xb962
B90D     79 00 -  mov      R1, #0x0
B90F     7a 00 -  mov      R2, #0x0
B911     90 04 be mov      DPTR, #0x4be
B914     12 88 8c lcall    0x888c
```

`ec/decompiled/bank1/BFD9.asm`, named `zero_04ae_and_04be`, is the same two
stores with nothing else between them, and it **reads no `0x0490` byte at all**:

```
BFD9     79 00 -  mov      R1, #0x0
BFDB     7a 00 -  mov      R2, #0x0
BFDD     90 04 ae mov      DPTR, #0x4ae
BFE0     12 88 8c lcall    0x888c
BFE3     90 04 be mov      DPTR, #0x4be
BFE6     12 88 8c lcall    0x888c
BFE9     22 - -   ret
```

So the zeroing of the `0x04AE` word rides the `0x0490` bit-1 clear in `0xB841`
and appears independently in `0xBFD9`; the `0x04BE` word rides the bit-5 clear
in `0xB8E1` and appears in the same `0xBFD9`. That asymmetry is why the two
entries are separate rows and not one.

> **Corrected here, 2026-10-04 (issue #732): the `0xB841` mask clears bits 1
> and 2, not "bits 0, 1, 2 and 6".** Issue #732's text said the latter, and
> the `B841` row of `ec/annotations/ghidra-functions.csv` carried it, so the
> wrong bit list was already in the tree and is corrected in that row too. The
> mask is `0xf9`; the list "bits 0, 1, 2 and 6" is what `0xb8` would clear, so
> the two differ in bits 0 and 6 and the error came from reading the intent
> rather than the byte. **It does not change what this file is for**: bit 1 is
> in both lists, and it is bit 1 that `0xB12C` gates `charge_target_update` on.
> The suite pins the mask's derived bit list rather than the prose, so a
> re-encoded mask fails rather than a differently-worded sentence passing.

**Bit 1 is the charge-target gate.** `ec/decompiled/bank0/B12C.asm` reads the
gate byte and branches into `charge_target_update` on it:

```
B141     90 04 90 mov      DPTR, #0x490
B144     e0 - -   movx     A, @DPTR
B145     20 e1 10 jb       0xe1, 0xb158
```

`0xe1` is bit 1 of the accumulator, and `0xB158` is `charge_target_update`. Bit
1 is therefore one of the bits `0xB841` clears, in the same breath as it zeroes
the `0x04AE` word — which is what puts that word on the charge-target path.

## 2. The increments, and why the issue's premise is false

Issue #732 asked that the notes record "no committed routine has been read
setting them non-zero". **That is false of these two words, and it is not
written down.** Both are incremented as 16-bit values with carry.
`ec/decompiled/bank1/BFBB.asm`, `0xC01B`–`0xC031`:

```
C01B     90 04 ae mov      DPTR, #0x4ae
C01E     e0 - -   movx     A, @DPTR
C01F     7a 00 -  mov      R2, #0x0
C021     24 01 -  add      A, #0x1
C023     50 02 -  jnc      0xc027
C025     7a 01 -  mov      R2, #0x1        <- R2 is the carry
C027     f0 - -   movx     @DPTR, A
C028     f9 - -   mov      R1, A
C029     90 04 af mov      DPTR, #0x4af
C02C     e0 - -   movx     A, @DPTR
C02D     2a - -   add      A, R2
C02E     40 01 -  jc       0xc031
C030     f0 - -   movx     @DPTR, A
C031     fa - -   mov      R2, A
```

`ec/decompiled/bank1/C0A8.asm`, `0xC0D9`–`0xC0EF`, is the identical shape
against `0x04BE`/`0x04BF`. The increment is reached once the byte in front of
it reaches `0x3C`: `0xBFBB`'s `0xBFF0` is `cjne A,#0x3c` on `0x04AD`, and
`0xC0A8`'s `0xC0AE` the same on `0x04BD`.

**The `0x3C` is the gate, and it takes reading the pair rather than either
instruction alone.** `0xBFEA`–`0xBFFA`, `ec/decompiled/bank1/BFBB.asm`:

```
BFEA     90 04 ad mov      DPTR, #0x4ad
BFED     e0 - -   movx     A, @DPTR
BFEE     24 01 -  add      A, #0x1        <- the carry that matters is not this one's
BFF0     b4 3c 04 cjne     A, #0x3c, 0xbff7
BFF3     e4 - -   clr      A
BFF4     f0 - -   movx     @DPTR, A
BFF5     80 04 -  sjmp     0xbffb         <- into the C01B increment
BFF7     50 fa -  jnc      0xbff3
BFF9     f0 - -   movx     @DPTR, A
BFFA     22 - -   ret
```

`CJNE` writes the carry itself: it is set when `A` is unsigned-less than the
immediate and cleared otherwise, so `0xBFF7`'s `JNC` tests **that comparison**,
not the `0xBFEE` `ADD` — reading the two as one `if` is what makes the `0x3C`
look incidental. `0xBFF0`'s not-equal arm lands at `0xBFF7`, and `A == 0x3C`
falls through it to `0xBFF3`; both then reach the increment, and only
`A < 0x3C` — the one case that sets the carry — stores the incremented byte and
returns at `0xBFFA` without incrementing. So the byte counts up to `0x3C`, and
each wrap bumps the word: a modulo-60 prescaler, `0x3C` being 60.
`ec/decompiled/bank1/BFBB.c` agrees, rendering the same test as
`if ((DAT_EXTMEM_04ad != 0x3c) && (DAT_EXTMEM_04ad < 0x3c)) return;` — which is
`A < 0x3C`, and so the return that skips the increment. `0xC0AE`/`0xC0B5` are
the same pair over `0x04BD`. The suite pins both branch targets, because the
claim fails if the `jnc` is read as belonging to the `ADD`.

**This is why the pairing is structural rather than inferred.** The two bytes
of each word are written together by the pair store at `0x888C`
(`ec/decompiled/bank1/888C.asm` stores `R1` then `R2` across an `inc DPTR`) and
incremented together with an explicit carry. Nothing about the pairing is a
reading of a layout; both operations treat the two addresses as one value.

## 3. The `* 0x3C` comparison is `0xC032`'s, not `0xBFBB`'s

`ec/decompiled/bank1/BFBB.c` reads as though the `* 0x3C` comparison and all
three `0x0494` accesses were `0xBFBB`'s own bytes. **They are not.**
`ec/decompiled/bank1/BFBB.asm` ends at `0xC031` and contains no `0x0494` site
and no `mov B,#0x3c`; its one `0x3C` is the `cjne` on `0x04AD` above.
`ec/decompiled/bank1/C032.asm` holds the multiplier at `0xC059` and `0xC07E`
(`mov B,#0x3c`, then `mul AB`) and every `0x0494` access at `0xC08A`, `0xC090`
and `0xC09F`.

The reason the `.c` reads the other way is at the top of `0xBFBB`: its first
instruction is `lcall 0xc032`, so the decompiler follows the call and the
callee's bytes appear in the caller's body. That is a property of the
decompilation, not of the code — the same trap `docs/findings.md` §4 records for
`.c` files elsewhere, and the reason every claim above is taken from a listing.

`0x3C` is 60. **No unit is claimed**: nothing committed establishes the tick
rate of `0xBFBB` or `0xC0A8`, so the words count ticks of a byte whose period
is unknown, and "seconds" and "minutes" appear nowhere in these notes.

## 4. `0x04A0` and `0x04A1`: what the mirror argument was, and why it is withdrawn

> **Withdrawn, 2026-10-04 (issue #732), leaving the argument as it was made.**
> The rejected reading was that `0x04A0` is a **mirror** of the 16-bit word at
> `0x0524`/`0x0525`, and that the evidence for it was that "the readers are what
> separate the two readings. They test individual bits across the two bytes,
> which is what a mirror predicts and a staging slot does not" — the bit-5
> tests on `0x04A0` at `bank1 0xAD8B`, `0xB224` and `0xB2A0`, and the
> bit-6 and `& 0x90` tests on `0x04A1` at `bank1 0xBA43` and
> `0xC11C`. On that reading the entry was named
> `XDATA_04A0_MIRROR_OF_0524` and the two addresses were filed as one
> 16-bit pair.
>
> **The argument is withdrawn.** It rested on the provenance, and the
> provenance is wrong: `bank1 0xB2D5` does not deliver `0x0524` to `0x04A0`.
> And its supporting evidence does not survive either, because
> `0x04A1` is a byte no committed writer sets non-zero, so the `0x04A1` bit
> tests cannot distinguish a mirror from anything else — they are tests of zero.

The provenance, from the listings. `ec/decompiled/bank1/B2D5.asm`,
`0xB2E5`–`0xB2F0`:

```
B2E5     90 05 24 mov      DPTR, #0x524
B2E8     12 b6 c9 lcall    0xb6c9
B2EB     40 06 -  jc       0xb2f3
B2ED     90 04 a0 mov      DPTR, #0x4a0
B2F0     12 88 8c lcall    0x888c
```

`0xB6C9` loads **four** bytes, and `0x888C` stores the last two.
`ec/decompiled/bank1/B6C9.asm`, `0xB6C9`–`0xB6D3`:

```
B6C9     e0 - -   movx     A, @DPTR
B6CA     fb - -   mov      R3, A          <- 0x0524
B6CB     a3 - -   inc      DPTR
B6CC     e0 - -   movx     A, @DPTR
B6CD     fc - -   mov      R4, A          <- 0x0525
B6CE     a3 - -   inc      DPTR
B6CF     e0 - -   movx     A, @DPTR
B6D0     f9 - -   mov      R1, A          <- 0x0526
B6D1     a3 - -   inc      DPTR
B6D2     e0 - -   movx     A, @DPTR
B6D3     fa - -   mov      R2, A          <- 0x0527
```

and `ec/decompiled/bank1/888C.asm` is `mov A,R1` / `movx @DPTR,A` / `inc DPTR`
/ `mov A,R2` / `movx @DPTR,A`. So with `DPTR=0x0524`, `R3`/`R4` hold
`0x0524`/`0x0525`, `R1`/`R2` hold `0x0526`/`0x0527`, and the pair store at
`0xB2F0` lands **`0x0526` at `0x04A0` and `0x0527` at `0x04A1`** — one hop
downstream of `0x0524`, not `0x0524`.

`ec/decompiled/bank1/D0C4.c` is what made the hop invisible: the adjacent
statement `DAT_EXTMEM_0526 = DAT_EXTMEM_0524` reads as though `0x04A0` were
being given the same value, and the listing shows the same thing two
instructions apart (`0xD0C8`–`0xD0CF` copy one byte to `0x0526` and `0x04A0`).
So reading the `.c` gives the same answer as reading the `.asm` here, and the
error survives both. This tree's own rule is that the listing wins where the
two disagree.

### The reader census, in full

Every routine whose **own listing** carries a `0x04A0` or `0x04A1` DPTR
literal. Taken from the `.asm` files, not from `DAT_EXTMEM_04a*` tokens in the
decompiles, and §3 above is why that distinction is load-bearing here:

| routine | what it tests | kind of test |
|---|---|---|
| `bank1 0xAD8B` | `0x04A0 >> 5 & 1`, against `0x0494 == 0` (twice) | `0x04A0` bit 5 |
| `bank1 0xB224` | `0x04A0 >> 5 & 1` | `0x04A0` bit 5 |
| `bank1 0xB2A0` | `0x04A0 >> 5 & 1`, under `PSW` sign | `0x04A0` bit 5 |
| `bank1 0xB2D5` | writes the pair (§4 above) | writer |
| `bank1 0xBA43` | `0x04A0` read; `0x04A1 >> 6 & 1`; `0x04A1 & 0x90` | `0x04A1` bits |
| `bank1 0xC11C` | `0x04A1 & 0x90` (twice) | `0x04A1` bits |
| `bank1 0xC778` | clears it, with `0x0524` and `0x0526` | writer |
| `bank1 0xD0C4` | clears it, and copies `0x0524` into it | writer |

This is the complete set, not a selection: the suite derives it from the
listings and fails if the table here misses one **or names one the listings do
not support**. The two directions matter — a census intersected with the set it
is checking can only ever report a routine missing, never one spurious, and a
spurious row is what the `.c`-derived version produced.

Three decompiles name `DAT_EXTMEM_04a0`/`DAT_EXTMEM_04a1` with **no such byte
in their own listing**, each because the decompiler followed control flow into
a neighbour. They are listed here so they are dropped with a reason rather than
silently:

- **`bank1 0xAD80`** is one instruction, `sjmp 0xad8b`. The `0x04A0` sites its
  decompile shows are `0xAD8B`'s, at `0xADA5` (a load into `R1`) and `0xADB9`
  (the bit-5 test).
- **`bank1 0xB98D`** runs `0xB98D`–`0xBA40` and then a separate `0xBAB2`–`0xBABC`
  block, with no `0x04A1` byte anywhere in it. The `0xBA43`–`0xBAAF` region its
  decompile renders as a continuation is `BA43`'s, and the two tests at
  `0xBA5F` and `0xBA90` are `BA43`'s.
- **`bank1 0xD17E`** contains no `0x04A0` byte. The `0x20` store its decompile
  shows is `0xD166`, inside `D0C4` (already writer route 1 below), reached by
  `0xD19C`'s `sjmp 0xd14c` into the middle of it.

Nothing the table was cited for changes: the `0x04A1` bit-6 and `& 0x90` tests
exist, at `BA43` and `C11C`. What changed is the derivation — this argument
previously read the `.c` tokens and so counted three of these neighbours a
second time.

### The three writer routes for `0x04A0`, which do not agree

Recorded per writer, because a single sentence cannot carry three facts that
disagree:

1. **`bank1 0xD0C4`** gives it the value `0x0524` holds — `0xD0C4`–`0xD0CF`
   load `0x0524` and store it to `0x0526` and `0x04A0` — and on its later path
   (`0xD15C`–`0xD16D`) writes the literal `0x20` to `0x0524`, `0x0526`,
   `0x04A0` and `0x0492` together.
2. **`bank1 0xC778`** clears it, in the same run that clears `0x0524` and
   `0x0526` (`0xC78D`/`0xC790`, with `A` cleared at `0xC788`).
3. **`bank1 0xB2D5`** gives it the byte at `0x0526` (§4 above).

Route 3 is the sharper fact, and it is the one that replaces the mirror claim:
`0x0526`'s writers are a **strict subset** of `0x0524`'s. `0x0527` aside,
`0x0526` is written by `bank1 0xC778` and `0xD0C4`, while `0x0524` is
written by those two plus `bank1 0xAD8B`, `0xB2D5`, `0xBA43`, `0xC7A7` and
`0xCBF3`, which clear `0x0524` without touching `0x0526`. So `0x04A0` does not
even track `0x0524` across all three of its own routes, and **no reader is the
reason any of them wrote it** — the bit-5 tests are observations about a byte,
not the purpose of a store.

Those two sets are taken from the listings for the reason the census above is:
`0xD17E` used to appear among `0x0526`'s writers because `D17E.c` writes
`DAT_EXTMEM_0526`, and `D17E.asm` holds no `0x0526` byte at all — the store is
`0xD0C4`'s at `0xD165`, which `0xD17E` reaches by `sjmp 0xd14c`. Dropping it
does not weaken the subset claim; the relation is a **strict** subset either
way, and it is the routines unique to `0x0524` that make it strict.

### `0x04A1`: never read set non-zero

**No committed routine has been read setting `0x04A1` non-zero.** Its only
direct store is `bank1 0xD0C4` at `0xD0D9`/`0xD0DC`, with `A` cleared at
`0xD0D0`. Its one helper-written path is `0xB2D5`'s pair store, which delivers
`0x0527`; and `0x0527`'s only committed writer is that same `0xD0C4`, storing
zero (`0xD0D5`–`0xD0D8`, `A` still cleared).

So the bit-6 and `& 0x90` tests at `0xBA43` and `0xC11C` are tests of
a byte no committed writer sets. **That is the limit of the claim, and it is a
limit of method rather than a property of the byte**: a computed DPTR, a
register-indirect store and a pointer handed to a helper are all outside what
these listings and the committed decompiles show, so this is "not found by this
method" and never "is always zero". A live run is the only thing that settles
it, and there is no machine here.

Three of `0x04A1`'s eight `MOV DPTR` sites are in the ITE8850-PD image, a
separate 8051 program with its own XDATA map (`ec/tools/trace_xdata_refs.py`'s
own docstring opens with why they must not be added together). They are
counted in `static_refs_pd_image` and named by nobody.

## 5. Site counts

The per-address `MOV DPTR,#addr` counts are recorded in
`ec/annotations/registers.yaml` and re-derived from the committed image by

```console
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

so they are not restated here. The shape they have is the point, and it needs no
figure: each high half has a single site, and it is the increment's carry
target, while the low halves also carry the zeroing and the `0x8886`/`0x888C`
call sites. `0x04A1`'s sites are the exception that makes the split necessary —
three of them are in the PD image, counted in their own column and never added
to the main-EC one.

## 6. What this does not establish

- **The tick rate, and so the unit, of either counter word.** `0x3C` is 60 and
  nothing more; the period of `0x04AD` and `0x04BD` is not established here.
- **What sets `0x0490` bits 1 and 5.** Two routines clear them; the writer that
  arms them is not decoded. The live reading on
  `ec/annotations/charge-target-derating.md` has bit 1 set and bit 5 clear,
  which is consistent with both and settles neither.
- **Whether `0x04A1` ever goes non-zero live** — the question §4 leaves open,
  and the one a machine at the laptop could answer.
- **What the `0x04A0` bit-5 test selects.** It is read in four routines and
  none of them is a writer, so the store and the test are separate facts and
  this file does not join them.
- **Whether the symbols land in the decompiles.** `ec/ghidra/xdata-symbols.csv`
  is regenerated here, but the committed `.c` files still spell these
  `DAT_EXTMEM_04a0`, `DAT_EXTMEM_04af`. The symbols reach a decompilation only
  on the next project rebuild, which is out of scope here (two branches that
  both rebuild cannot merge). Everything above is therefore cited by address and
  function name, never by the new symbol names.

## 7. Follow-ups this opens

- A `registers.yaml` row for `0x0490` itself, which still has none. The notes
  must not imply it is documented.
- The rest of #723's population; `0x04A3` is #715's and is untouched here.
- The `+0x10` column structure of the `0x04A0`–`0x04C0` run beyond what these
  four addresses' own routines show.
- Making `test_inc_dptr_sites.py`'s two entered-set figures derived rather than
  hand-kept. Its entered constant is checked against `registers.yaml` in both
  directions now, but the list itself still has to be extended by hand.