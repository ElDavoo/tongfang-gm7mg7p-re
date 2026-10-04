# The `0x0436` band ladder: `0x0436` is compared against descending scalings of `0x0404`, and one of its eight writers stores `0x0404`'s own value

`bank1 0xB50E derive_scaled_values_from_0404` computes six values from the
16-bit little-endian pair at XDATA `0x0404`/`0x0405` and stores each one
somewhere. Four of those destinations — `0x040A`, `0x040C`, `0x040E` and
`0x0410` — carried the note "what is written still is not established"
because the store was of a computed pair. The derivation is in the
committed bytes, and it is now in the record.

The second half is the pair that reads back. Six routines branch on
comparisons of `0x0436`/`0x0437` against `0x040A`, `0x0544` and `0x040C` —
the first, second and third of those same scalings — and against the
literal `1`. They are reached through a jump table keyed on a second
register, `0x056A`, which is itself a band cursor. Together they make
`0x0436` a value the EC sorts into descending bands of a `0x0404`-derived
scale, and one of `0x0436`'s eight writers (`0xB2A0`) stores `0x0404`'s own
value into it.

Nothing here was measured on hardware, no register was read back, and no
`status:` moves. This is the static half of #1310 and does not replace it.

## 1. The `0x0404` derivation, read out of the committed bytes

`ec/decompiled/bank1/B50E.asm` is the machine code and the `.c` beside it
is a reading of it; where they disagree the `.asm` is right, as that
file's own header says. Reading the `.asm`:

| instruction | effect |
|---|---|
| `mov DPTR,#0x404` / `lcall 0x8886` | `R1:R2` = `0x0404`/`0x0405`, low byte first |
| `mov 0x06,R2` / `mov 0x05,R1` | stash the pair in direct bytes |
| `mov R7,#0x4` / `lcall 0x8844` | `ror16_r1r2_by_r7`, four iterations of `rrc` — a 16-bit rotate right by 4 |
| `mov DPTR,#0x40a` / `lcall 0x888c` | store `R1:R2` to `0x040A`/`0x040B` |
| `mov R2,0x06` / `mov R1,0x05` | restore the stashed pair |
| `mov R7,#0x5` / `lcall 0x8844` | shift right by 5 |
| `mov DPTR,#0x40c` / `lcall 0x888c` | store to `0x040C`/`0x040D` |
| `mov DPTR,#0x40e` / `lcall 0x888c` | store the *same* `R1:R2` to `0x040E`/`0x040F` |
| `add A,#0x28` / `jnc` / `inc R2` | add `0x28` to the 16-bit result, carry into the high byte |
| `mov DPTR,#0x544` / `lcall 0x888c` | store that to `0x0544`/`0x0545` |
| `mov R4,0x06` / `mov R3,0x05` | `R3:R4` = the stashed pair again |
| `mov DPTR,#0x40a` / `lcall 0x8886` | `R1:R2` = what was just stored at `0x040A`/`0x040B` |
| `lcall 0x885b` | `sub_r1r2_from_r3r4` — `R3:R4` = `0x0404` − `ror16(0x0404, 4)` |
| `mov DPTR,#0x546` / `lcall 0x889e` | store to `0x0546`/`0x0547` |
| `mov R4,0x06` / `mov R3,0x05` | `R3:R4` = the stashed pair again |
| `mov DPTR,#0x40e` / `lcall 0x8886` | `R1:R2` = what was stored at `0x040E`/`0x040F` |
| `lcall 0x885b` | `R3:R4` = `0x0404` − `ror16(0x0404, 5)` |
| `mov DPTR,#0x410` / `lcall 0x889e` | store to `0x0410`/`0x0411` |

So, writing `V` for the 16-bit little-endian value at `0x0404`/`0x0405`, and
`ror16(V, n)` for the helper's 16-bit rotate:

| destination | value |
|---|---|
| `0x040A`/`0x040B` | `ror16(V, 4)` |
| `0x040C`/`0x040D` | `ror16(V, 5)` |
| `0x040E`/`0x040F` | `ror16(V, 5)` |
| `0x0544`/`0x0545` | `ror16(V, 5) + 0x28` |
| `0x0546`/`0x0547` | `V - ror16(V, 4)` |
| `0x0410`/`0x0411` | `V - ror16(V, 5)` |

**The rotate is a shift only when the bits shifted out are zero.** This is
the one place where reading the routine as a shift would be wrong, and it
is worth being explicit because `0x8844`'s own name already says *rotate*.
Its body is `rrc` of the high byte through a carry cleared beforehand, then
`rrc` of the low byte, `djnz R7` and back — so the bit leaving the bottom of
`R1` re-enters at the top of `R2` rather than being discarded. Whenever `V`'s
low five bits are zero, `ror16(V, 4)` and `V >> 4` agree and so do the two
at count 5; otherwise they differ. **Which case holds on this board is not
established here**, because nothing in this repository records a live reading
of `0x0404`/`0x0405` — so the table above states the rotate, which is what
the bytes do, and treats the shift reading as the special case it is. A
reader who wants the shift form needs a capture of the source pair.

Everything else about the pair holds either way: the two scalings differ
from each other, they are the same two values the ladder bands against, and
the two differences are differences from `V` either way.

Three more details are worth stating because the `.c` loses them.

**`R7` is the rotate count.** `ror16_r1r2_by_r7` returns immediately on
`R7 == 0`, so the count is a loop bound and not a mask, and the two counts
in the routine are 4 and 5. `sub_r1r2_from_r3r4` at `0x885B` opens with an
explicit `clr CY`, so neither difference borrows in.

**`0x040C` and `0x040E` receive the same value.** The `R1:R2` pair is not
reloaded between the two stores — the only reload is the `mov R2,0x06` /
`mov R1,0x05` pair before the `R7 = 5` rotate. So `0x040C` and `0x040E` are
two copies of one value, which is what makes the two of them a comparison in
the next section rather than two scalings.

**The `+0x28` is added to the rotated value, not to `V`.** The `add A,#0x28`
at `0xB539` reads `A` from `mov A,R1` at `0xB538`, and `R1` at that point
holds the low byte of the count-5 rotate. The carry path `jnc` / `inc R2` is
a 16-bit add of `0x28` onto that.

The `.c` renders `0x8886` and `0x889E` as writes. They are reads and
writes respectively — `0x8886 read_xdata_pair_to_r1r2` is two `movx A,@DPTR`,
`0x889E write_r3r4_to_xdata_pair` is two `movx @DPTR,A` — and the annotation
row at `ec/annotations/ghidra-functions.csv` for `bank1,B50E` already
records that correction. This section is the derivation that row claims and
the store-site count could not supply.

### Which of the unentered addresses are the same decision, and which are not

The issue asks this explicitly, and the answer is mechanical rather than
editorial. Every one of these addresses is written by the `0x888C`/`0x889E`
pair helpers, which store the low byte at `DPTR` and the high byte at
`DPTR+1`. **The two halves are therefore reached differently**, and
`ec/tools/scan_refs.py` — which counts `MOV DPTR,#imm16` and so sees the low
half directly — finds nothing for any high half, because the helper reaches it
with its own `inc DPTR`:

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 \
    0x0544 0x0545 0x0546 0x0547 0x040B 0x040D 0x040F 0x0411
0x0544  refs=2     ec=2     pd=0     referenced   in_data_region=0   0x0544
0x0545  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x0545
0x0546  refs=2     ec=2     pd=0     referenced   in_data_region=0   0x0546
0x0547  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x0547
0x040B  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x040B
0x040D  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x040D
0x040F  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x040F
0x0411  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x0411
```

Those zeros are **not found by this scan**, not absent: the high halves are
demonstrably touched, by the `inc DPTR` inside the pair helpers.

So there are two decisions here, and the low halves make the first while the
high halves repeat it:

- **`0x0544` and `0x0546` are the same decision `0x040A` already has.** Each
  has an EC-side image site (`0xAE65` and `0xADCC` besides `0xB53F` and
  `0xB552`), each resolves to one read and one write in
  `ec/annotations/xdata-registers.csv`, and each is entered or not entered on
  the same warrant as `0x040A` — a site count and a direction, with no
  behaviour behind either. They are left out of `registers.yaml` here, and
  the last section says why.
- **The four high halves are the existing convention, not a new one.**
  `registers.yaml` already declines to enter the high half of every entered
  pair on this ground: `BAT_FULL_CAPACITY_1`'s note says of `0x0405` that it
  "has no site in any image and is therefore not entered", and
  `BAT_DESIGN_VOLTAGE_1`, `BAT_STATUS_1` and `XDATA_0436_PAIR` each say the
  same of theirs. The census disagrees with that sentence for the high
  halves and agrees with it for the low ones — `0x040B`, `0x040D`, `0x040F`,
  `0x0411`, `0x0545` and `0x0547` all have rows in
  `ec/annotations/xdata-registers.csv` with `spelled_as` `pair-literal` and a
  non-zero `refs`, because the census resolves the literal first argument of
  the pair accessor and follows its `inc DPTR`. That is the same blind spot
  `XDATA_0420`'s note describes from the other side, and the convention is
  not disturbed by it.

## 2. Six routines band `0x0436` against those same scalings

Three comparators do the banding, each five instructions and a `ret`:

```console
$ cat ec/decompiled/bank1/AE92.asm
AE92     90 04 36 mov      DPTR, #0x436
AE95     12 88 92 lcall    0x8892
AE98     90 04 0c mov      DPTR, #0x40c
AE9B     12 88 86 lcall    0x8886
AE9E     12 88 63 lcall    0x8863
AEA1     22 - -   ret
```

`0x8892 read_xdata_pair_to_r3r4` loads `0x0436`/`0x0437`, `0x8886
read_xdata_pair_to_r1r2` loads the bound, and `0x8863
cmp_r3r4_against_r1r2_16bit` compares. `0xAE2B cmp_0436_0437_against_040a_040b`
is the same shape against `0x040A`; `0xAE5F cmp_0436_0437_against_0544_0545`
against `0x0544`.

The carry `0x8863` sets is a borrow. Its body is two `subb` pairs, the
second inheriting the first's carry, then a `jc` past an equality test on
`R4`/`R3` against `0x02`/`0x01`; the borrow path lands on the `A = 1` return
with carry still set, and the non-borrow paths clear it. So carry means
`0x0436` is **below** the bound, and every caller branches on exactly that.

A fourth comparator, `0xAEBC cmp_0436_0437_against_1_or_test_0514`, closes
the ladder. On the `0x0497` bit-7-clear path it loads `0x0436` into `R3:R4`,
puts `R2 = 0x00` and `R1 = 0x01`, and calls `0x8863` — the bound is the
literal `1`. On the other path it reads `0x0514` and does `clr CY` /
`subb A,#0x1`, which is the same comparison against the same literal without
the pair machinery.

### What the carry decides, and what selects the routine

The plan this implements expected a straight-line chain. It is not
straight-line: **the six routines are selected through a jump table keyed on
a second register**, and one of them is not reachable from that table at
all. That is the substantive correction to what the issue asked for, so it
is set out in full.

`bank1 0xADFD dispatch_on_056a_low3` reads `0x056A`, masks it with `0x07`,
multiplies by three by adding `R0` to `A` twice, and does `jmp @A+DPTR` with
`DPTR` at `0xADE2`:

```console
$ cat ec/decompiled/bank1/ADFD.asm
ADFD     90 04 90 mov      DPTR, #0x490
AE00     e0 - -   movx     A, @DPTR
AE01     20 e2 01 jb       0xe2, 0xae05
AE04     22 - -   ret
AE05     90 05 6a mov      DPTR, #0x56a
AE08     e0 - -   movx     A, @DPTR
AE09     54 07 -  anl      A, #0x7
AE0B     90 ad e2 mov      DPTR, #0xade2
AE0E     f8 - -   mov      R0, A
AE0F     28 - -   add      A, R0
AE10     28 - -   add      A, R0
AE11     50 02 -  jnc      0xae15
AE13     05 83 -  inc      DPH
AE15     73 - -   jmp      @A+DPTR
```

The table's own bytes are in no committed listing — the gap between `0xADFD`
and `0xAE16` is not exported — but they are in the image, and
`ec/annotations/bank-call-targets.csv` classifies each three-byte entry as an
`ljmp`. Read out of the firmware:

```console
$ python3 -c "d=open('ec/firmware/GMxMGxx_11.800','rb').read(); \
    o=0x10000+(0xADE2&0x7FFF); print(' '.join('%02x'%b for b in d[o:o+27]))"
02 ae 16 02 ae 42 02 ae 78 02 ae a2 02 ae e2 02 ae f3 02 ae 16 02 ae 16 02 ae 16
```

Eight three-byte `ljmp`s, one per value of `0x056A & 7`:

| `0x056A & 7` | table entry | lands on |
|---|---|---|
| 0 | `0xADE2` | `0xAE16` |
| 1 | `0xADE5` | `0xAE42` |
| 2 | `0xADE8` | `0xAE78` |
| 3 | `0xADEB` | `0xAEA2` |
| 4 | `0xADEE` | `0xAEE2` |
| 5 | `0xADF1` | `0xAEF3` |
| 6 | `0xADF4` | `0xAE16` |
| 7 | `0xADF7` | `0xAE16` |

So the six routines are the six distinct targets, entered by the *value of
`0x056A`*, and `0x056A` is written by the ladder itself. That makes it a
state machine whose state and whose output are the same register, and it is
why the sixth routine matters less than its five siblings.

Each routine loads its own `R6`, branches on one or two comparators, and
either writes `0x056A` or falls into `0xAE6F or_r6_into_0496_low5`, which
masks `0x0496` with `0xE0` and ORs `R6` in. `0xAE6F`'s own annotation row
already records the six `R6` values and labels the pattern an inference from
the call sites; the table above is what makes it a mechanism rather than a
coincidence of six literals.

| routine | `R6` | gate | compares, in order | writes `0x056A` | else |
|---|---|---|---|---|---|
| `0xAE16 set_056a_1_on_carry_from_ae2b` | `0x00` | `0x0490` bit 7 set → skip | `0xAE2B` vs `0x040A` | `1` | `0xAE6F` |
| `0xAE42 chain_probes_update_056a_0_1_2` | `0x01` | `0x0490` bit 7 set → `0xAED9` | `0xAE2B` vs `0x040A`, then `0xAE5F` vs `0x0544` | `0`, then `2` | `0xAE6F` |
| `0xAE78 chain_probes_update_056a_1_3` | `0x03` | `0x0490` bit 7 set → `0xAED9` | `0xAE5F` vs `0x0544`, then `0xAE92` vs `0x040C` | `1` (via `0xAE24`), then `3` | `0xAE6F` |
| `0xAEA2 chain_probes_update_056a_2_4` | `0x07` | `0x0490` bit 7 set → `0xAED9` | `0xAE92` vs `0x040C`, then `0xAEBC` vs `1` | `2` (via `0xAE58`), then `4` | `0xAE6F` |
| `0xAEE2 set_056a_3_or_0496_low5_0f` | `0x0F` | `0x0490` bit 7 set → `0xAED9` | `0xAEBC` vs `1` | `3` (via `0xAE8B`) | `0xAE6F` |
| `0xAEF3 set_056a_3_or_0496_low5_1f` | `0x1F` | `0x0490` bit 7 set → `0xAED9` | `0xAEBC` vs `1` | `3` (via `0xAE8B`) | `0xAE6F` |

Read down the `R6` column and it is a thermometer: `0x00`, `0x01`, `0x03`,
`0x07`, `0x0F`, `0x1F` — each value the previous one with one more bit set,
and `0xAE6F` masking `0x0496` with `0xE0` keeps them in the low five bits
where they cannot collide with whatever else lives in the top three. Read
down the comparator column and each routine starts one rung lower than the
one above it: `0x040A` (= `ror16(V,4)`), then `0x0544` (=
`ror16(V,5)+0x28`), then `0x040C` (= `ror16(V,5)`), then the literal `1`.
**The bands are denominated in the `0x0404` unit, and three of the four
bounds are the scalings `0xB50E` computes in §1.**

Two things about that ladder are worth being precise about, because neither
is what the shape suggests.

**The bounds descend, but not by a constant step.** `ror16(V,4)` and
`ror16(V,5)+0x28` are not adjacent for any `V` that is a plausible capacity:
the gap between them is roughly `ror16(V,5) - 0x28`, which is most of
`ror16(V,5)`. The ladder is therefore coarse at the top and fine at the
bottom — two bounds within a factor of two of each other, then
`ror16(V,5)`, then `1` — and it is that shape, not an even subdivision, that
the `0x056A` cursor walks.

**`0x056A` is a band index, and the routine for a band both reads and
rewrites it.** `0xAE42` writes `0` and `2`; `0xAE78` writes `1` and `3`;
`0xAEA2` writes `2` and `4`; `0xAEE2` and `0xAEF3` write `3`. So the cursor
moves one step at a time in either direction depending on which comparator
borrowed, and the six `0x056A` values the table can select are 0 through 5 —
with 6 and 7 aliasing back to `0xAE16`, the state whose `R6` is `0x00`.
`ec/annotations/boot-xdata-sites.csv` records `0x056A` as cleared to `0x00`
at boot, which is the `0xAE16` entry.

**The sixth routine's `R6` is set on a different condition from the other
five.** `0xAEF3` is the target of the `0xADF1` entry, so the table does reach
it, but it is the only routine that loads `R6` *after* its comparator rather
than before — `mov R6,#0x1f` sits at `0xAF01`, past the `jc` at `0xAEFD`. So
the `0x1F` thermometer top is written only on the borrow path, while the other
five write their mask whichever way the compare went. That is a fact about
the instruction order, and it is worth recording because the `0xAE6F`
annotation calls the six-`R6` pattern an inference: on this routine the
pattern holds only one of the two ways through.

**One gate is not about `0x0436` at all.** `0x0490` bit 7 sends `0xAE42`
through `0xAEA2` and `0xAEF3` to `0xAED9 store_0_to_056a`, which stores zero
to `0x056A` — so the bit forces the cursor to the bottom rather than
selecting a band. `0xAE16` treats the same bit as a skip (`jb 0xe0, 0xae6f`),
which lands on `0xAE6F` with `R6` still `0x00`. `0x0490` bit 7 is written by
`bank1 0xC11C latch_0490_bit3_or_bit7`, which sets bit 3 or bit 7 and clears
the other, and by no other committed listing this suite can reach.
`0x056A` and `0x0496` have no `registers.yaml` row and none is added here;
`0x0496`'s low five bits are read at `0x8D3A` and `0x8E71` and stored at
`0xB940`, and `bank1 0x8DE4 dispatch_on_0490_0495_0496_0498` tests `0x0496`
bit 4 — inside the mask — as one of several `0x0490`/`0x0495` selectors.

### `0x0544` is a band bound, which is a second reason to enter it

`0x0544` is written by `0xB53F` and read by `0xAE65`, inside the comparator
that bands `0x0436`. That is a *consumer*, not just a store site, and it is
the argument for entering `0x0544`/`0x0545` that §1's site count alone does
not make. `0x0546`/`0x0547` has the same derivation and the same pair of
sites (`0xB552` writes, `0xADCC` reads, the read inside
`bank1 0xAD8B`, which compares the result against `0x0518`/`0x0519` with
`0x8863`). Neither is entered here; the last section says why, and this is
the follow-up they would carry.

## 3. The writer that makes the unit question answerable

`docs/findings/0436-0437-writer-census.md` established that `0x0436` has
eight writing sites in eight routines, and that the note's older "the only
writer is the zero-clear" sentence was wrong. That correction is already in
`registers.yaml`, dated `*** 2026-10-03 (issue #213) ***`, beside the
original sentence and not in place of it. This change does not repeat it and
does not touch that half of the note.

What that census did not do is connect the writer to the comparators. One of
the eight does exactly that. `bank1 0xB2A0 cmp_0404_vs_0518_then_store_0436`:

```console
$ cat ec/decompiled/bank1/B2A0.asm
B2A0     12 b2 14 lcall    0xb214
B2A3     50 08 -  jnc      0xb2ad
B2A5     90 04 a0 mov      DPTR, #0x4a0
B2A8     e0 - -   movx     A, @DPTR
B2A9     30 e5 01 jnb      0xe5, 0xb2ad
B2AC     22 - -   ret
B2AD     90 05 19 mov      DPTR, #0x519
B2B0     e0 - -   movx     A, @DPTR
B2B1     f9 - -   mov      R1, A
B2B2     90 05 1b mov      DPTR, #0x51b
B2B5     e0 - -   movx     A, @DPTR
B2B6     b5 01 1b cjne     A, 0x01, 0xb2d4
B2B9     90 04 04 mov      DPTR, #0x404
B2BC     12 88 92 lcall    0x8892
B2BF     90 05 18 mov      DPTR, #0x518
B2C2     12 88 86 lcall    0x8886
B2C5     12 88 63 lcall    0x8863
B2C8     40 04 -  jc       0xb2ce
B2CA     ac 02 -  mov      R4, 0x02
B2CC     ab 01 -  mov      R3, 0x01
B2CE     90 04 36 mov      DPTR, #0x436
B2D1     12 88 9e lcall    0x889e
B2D4     22 - -   ret
```

`0x8892` loads `0x0404`/`0x0405` into `R3:R4`; `0x8886` loads `0x0518`/`0x0519`
into `R1:R2`; `0x8863` compares them. The `jc` at `0xB2C8` skips the two
immediate loads, so **on borrow the pair receives `0x0404`'s own value** and
on no-borrow it receives `R3 = 0x01`, `R4 = 0x02` — `0x0201`, little-endian.
`0x0436` is therefore written from full capacity on one arm and from a
constant on the other.

`bank1 0xB214 set_carry_if_0404_0405_is_0201` is the same constant read back:
it loads `0x0404` into `R3:R4`, loads `0x0436` into `R1:R2`, and calls
`0x887A set_carry_if_r3r4_is_0102`, whose body is `R3` against `0x01` and
`R4` against `0x02`. The `0x0436` read is incidental — `R1:R2` is loaded and
never consulted — so the test is against `0x0404`, and `0x0436` is only
alongside it. The writer census already made this point and it holds.

## 4. Grading the two readings

The issue asks for a grade rather than a pick. Mine, from the bytes above.

**The capacity reading is better supported than it was, and not because a
compare exists.** A writer and its consumers agreeing on a unit is a
different kind of evidence from either alone: `0xB2A0` stores `V` into
`0x0436` when `V` is below `0x0518`, and six routines band `0x0436` against
`ror16(V,4)`, `ror16(V,5)+0x28`, `ror16(V,5)` and `1`. `0x0544` is the
sharpest case, because it is written and read inside the same comparison
chain — the ladder's second bound is a value `0xB50E` derives, and the only
committed listing that reads `0x0544` back is the comparator holding it.

**The `+0x14` ramp is not refuted by any of this, and stays a real
observation.** `docs/findings/0436-0437-writer-census.md` established that
none of the eight writers increments, so the periodic `+0x14` sweep in
`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` is unexplained by
any writer these methods find — and this change does not explain it either.
A monotonic sweep is also what a banding ladder's *input* looks like walking
through its bands, so the ramp and the capacity reading are compatible rather
than competing: one can be the value the ladder sorts, the other the
transition between bands.

So the pair keeps the placeholder name and `status: present-untested`. The
note gains a stated constraint — what the value is measured against, and by
which six routines — and not a name. Naming it a capacity would need a live
read beside a WMI RemainingCapacity, which is what
`docs/hardware-tests/remain-capacity-0436.md` is written to produce and what
no one has run. **#1310 stays open**, and this is its static half: nothing
here reads a register back, and the run is still the thing that would settle
the name.

## What is not established here

- **No hardware and no Windows machine was involved.** No register was read
  back, no capture was taken, and no claim in this write-up rests on
  observed behaviour. Every statement above is a statement about committed
  bytes.
- **What the band mask *means* is not decoded.** `0xAE6F` writes a
  thermometer into `0x0496`'s low five bits and `0x8DE4` tests bit 4 of it,
  but what a band *is* — a state of charge, a fan or power mode, a timer
  phase — is not established, and the routine names (`chain_probes_*`)
  suggest rather than demonstrate one.
- **What `0x0490` bit 7 means is not decoded.** That it gates the ladder and
  is written by `0xC11C` is established; what sets it in the first place,
  beyond `0xC11C`'s own two-bit alternation, is not.
- **The table's bytes are read from the image, not from a listing.** No
  committed `.asm` covers `0xADE2`-`0xADF9`, so the eight targets are read
  out of `ec/firmware/GMxMGxx_11.800` and cross-checked against
  `ec/annotations/bank-call-targets.csv`, which classifies the same offsets
  as `ljmp`. Seeding them as functions is issue #175's shape of work.
- **How `0xADFD` itself is reached is not established.** Its one forwarder,
  `bank1 0xAD7A forwarder_to_adfd`, is a bare `ljmp` and no committed
  listing calls or jumps to `0xAD7A` or `0xADFD`. That is "not found by
  this method", not "unreachable".
- **The `0x040x` and `0x054x` high halves are "not found by this scan".**
  The pair helpers' `inc DPTR` reaches them; `scan_refs.py` counts
  `MOV DPTR,#imm16` and cannot see that.
- **No register `status:` changed, and no `static_refs*` value moved.** A
  derived value is a static instruction; a band a static routine walks is
  not a behaviour.

## What this unblocks

The two open readings of `XDATA_0436_PAIR` now have a static constraint on
one side of them, and the note says which side. A live run of
`docs/hardware-tests/remain-capacity-0436.md` can now be read against a
prediction rather than against nothing: the value should move in `0x0404`
units if it is a capacity, and the mask in `0x0496` should step as it crosses
`ror16(V,4)`, `ror16(V,5)+0x28` and `ror16(V,5)`. A run that shows a `+0x14`
sweep which does *not* step the mask at those crossings would count against
the capacity reading, which is a test neither reading currently offers.

Entering `0x0544`/`0x0545` and `0x0546`/`0x0547` is the natural follow-up and
is deliberately not started here: entering them means choosing a `status:`
for an address whose only warrant is a site count and a direction, which is
the move the issue's own "Done" list rules out. That is a choice rather than
a discovery, and it belongs to whoever takes it on.

Re-derive anything here with:

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0544 0x0545 0x0546 0x0547
$ python3 ec/tools/check_site_resolution.py --check --committed
$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
$ bash tools/run-tests.sh ec/tools
```
