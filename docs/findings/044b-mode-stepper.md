# `0x044B` is a five-value mode byte, and `bank0 0x9AAD` is the routine that re-decides it

**Issue #649, 2026-10-02.** Issue #456 typed `bank0 0x9C47` as a bail-out
forwarder by reading `ec/decompiled/bank0/9AAD.asm`, and its write-up said the
arms' behaviour was not decoded. It is now, for the transition each arm takes.
The byte is not a counter that advances — two of the five transitions step
back down — so this page calls it a mode and the name of the routine that
drives it a *stepper* only in the loose sense of *it changes the step*.

Everything below is read from committed bytes: `ec/decompiled/bank0/9AAD.asm`
and the listings its arms reach. No register `status:` changed, nothing was
read back, no hardware or Windows machine was involved, and no live test ran.
The one thing this page does **not** deliver is what the five values mean, and
it says so in [§What is not decoded here](#what-is-not-decoded-here) rather than
leaving a reader to infer that from the transition table.

## The dispatch

`ec/decompiled/index.csv` records `bank0,9AAD` at 336 bytes, and
`0x9AAD`+336 is `0x9BFD` — the next entry, `forward_to_9a86`. The boundary is
confirmed by its neighbour rather than assumed, so the listing is the whole
function rather than a fragment of one. The export and the decompiled C were
already committed; what was missing was the annotation row, which now exists.

Adding it has one further effect worth naming, because it is the export that
reports it rather than this page. While the entry was seeded from the
call-target scan, `9AAD.asm` carried a header saying the boundary was a
hypothesis and the instructions might not be the whole function. An
annotation-seeded entry is not, so the re-export drops that caveat, and the
`seed_basis` column in `index.csv` moves from `call-target` to `annotation`.
The instructions themselves are unchanged by the re-export — only the header
and the name differ — which is the check that this page read bytes rather than
re-transcribing them.

The prologue runs first and the dispatch opens at `0x9B33`:

```
9B33     90 04 4b mov      DPTR, #0x44b
9B36     e0 - -   movx     A, @DPTR
9B37     14 - -   dec      A
9B38     60 29 -  jz       0x9b63
9B3A     14 - -   dec      A
9B3B     60 38 -  jz       0x9b75
9B3D     14 - -   dec      A
9B3E     60 59 -  jz       0x9b99
9B40     14 - -   dec      A
9B41     70 03 -  jnz      0x9b46
9B43     02 9c 00 ljmp     0x9c00
9B46     24 04 -  add      A, #0x4
9B48     60 03 -  jz       0x9b4d
9B4A     02 9c 47 ljmp     0x9c47
```

Three `dec`/`jz` pairs give 1 at `0x9B63`, 2 at `0x9B75` and 3 at `0x9B99`.
Neither of the remaining two cases is a `jz`. A value of 4 leaves the
accumulator at 0 after the fourth `dec`, fails the `jnz`, and falls through to
the `ljmp` at `0x9B43`; every other value is still non-zero, takes the `jnz` to
`0x9B46`, and there `add A,#0x4` restores the original byte so that a `jz`
picks out 0. `0x9B4A` is the default, so 0x044B is a byte with five enumerated
values and a catch-all — not a free-running counter.

## The five transitions

Every arm tests something first. On a failed test it returns at `0x9C47`
without writing; on a passed test it leaves for one of four small routines that
write a constant — by `ljmp` in five of the seven paths below, and by falling
through into the next entry in the other two. The tail targets, and the
constant each one leaves in `0x044B`:

| value | arm | the test it must pass | writes |
|---|---|---|---|
| 0 | `0x9B4D` | the incremented XDATA 0x08BF has reached 0xC8 | 1 |
| 1 | `0x9B63` | bit 0 of XDATA 0x08AD is set | 2 |
| 2 | `0x9B75` | bit 0 of 0x08AD set, and 0xBBC7 returns with carry clear | 3 |
| 2 | `0x9B75` | bit 0 of 0x08AD clear, and 0xB9F5 returns with carry clear | 1 |
| 3 | `0x9B99` | bit 0 of 0x08AD set, 0xBBC7 carry clear, 0x0873 <= 0x08C7 and 0x087B <= 0x08C8 | 4 |
| 3 | `0x9B99` | bit 0 of 0x08AD clear, 0xB9F5 carry clear, 0x0873 >= 0x08C4 and 0x087B >= 0x08C5 | 2 |
| 4 | `0x9B43` | `0x9C00` clears 0x09E9 unless bit 2 of 0x0743, then needs bit 0 of 0x08AD clear and 0xB9F5 carry clear | 3 |
| anything else | `0x9B4A` | — | nothing |

As a transition map, with the arms' two-way cases collapsed:

```
  0 ──(0x08BF ramps to 0xC8)──▶ 1
  1 ──(0x08AD bit 0)─────────▶ 2
  2 ──(0x08AD bit 0)─────────▶ 3        2 ──(0x08AD bit 0 clear)──▶ 1
  3 ──(thresholds hold)──────▶ 4        3 ──(0x08AD bit 0 clear)──▶ 2
  4 ──(0x08AD bit 0 clear)───▶ 3
```

**Two of those arrows go down.** 4 returns to 3, and 2 can return to 1. That is
the reason this page does not call the byte a counter: an incrementing counter
has no back edge, and an issue that predicted a "mode counter" would have been
wrong about two of the five cases. The value-0 arm is the one that does behave
like a ramp — it increments 0x08BF on every pass and refuses to move until the
incremented byte reaches 0xC8, which is what makes it the entry state rather
than a peer of the other four.

The bail-out sites and the conditions behind them are already enumerated, one by
one, in the `bank0 0x9C47` and `bank0 0x9C00` rows of
`../../ec/annotations/ghidra-functions.csv`, so they are not repeated here.

## The four writers, and why the constant is a constant

`0x044B` is written by four separate routines, reached by `ljmp` or by falling
through into a neighbour. They do **not** share one write path, which is worth
stating because the first reading of them did:

| routine | how it stores |
|---|---|
| `store_bd20_result_masked_7f` (`0x9A7B`) | `lcall 0xBD20` — DPTR is set inside the callee |
| `call_bd20_with_03_then_or_80_into_dptr` (`0x9A90`) | `lcall 0xBD20` — DPTR is set inside the callee |
| `call_ba15_then_write_02_to_044b` (`0x9A86`) | loads DPTR itself, then `movx @DPTR,A` |
| `write_04_to_044b_and_set_08e2_bit7` (`0x9A9C`) | loads DPTR itself, then `movx @DPTR,A` |

`0xBD20` is nine bytes and is the shared store for the first pair:

```
BD20     90 04 4b mov      DPTR, #0x44b
BD23     f0 - -   movx     @DPTR, A
BD24     90 08 e2 mov      DPTR, #0x8e2
BD27     e0 - -   movx     A, @DPTR
BD28     22 - -   ret
```

It stores the caller's accumulator to `0x044B` and leaves the accumulator
holding `0x08E2` — which is why both of its callers mask or set a bit in that
byte on the way out.

What makes the four constants *constants* rather than values carried in from
the arms is one shared instruction. All four routines open with
`lcall 0xBA15`, and `0xBA15` is a single byte, `clr A`. `0x9A7B` is the case
where this matters: it does `inc A` immediately after the call, so the byte it
stores is 1 unconditionally. Without that `clr A` it would be storing whatever
the arm had left in the accumulator, and the value-0 arm in particular arrives
with a subtraction result in A rather than a count.

## The prologue decides the polarity the arms act under

The value-1, value-2 and value-3 arms branch on bit 0 of XDATA `0x08AD`, and
so does `0x9C00`, which is where the value-4 arm goes. That bit is set or
cleared by the prologue itself, immediately before it falls into the dispatch:

```
9B12     90 08 ad mov      DPTR, #0x8ad
9B15     e0 - -   movx     A, @DPTR
9B16     44 01 -  orl      A, #0x1
9B18     f0 - -   movx     @DPTR, A
9B19     80 18 -  sjmp     0x9b33
...
9B27     90 08 ad mov      DPTR, #0x8ad
9B2A     e0 - -   movx     A, @DPTR
9B2B     54 fe -  anl      A, #0xfe
9B2D     f0 - -   movx     @DPTR, A
9B2E     80 03 -  sjmp     0x9b33
```

This is the link between the two halves of the routine, and it is what the
issue's "roughly 120 bytes decide whether the dispatch runs at all" was
reaching for. The prologue does not merely gate the dispatch — it selects which
of the two branches inside the value-2 and value-3 arms is even reachable, and
therefore which of their two successors can happen.

**One of the three prologue exits does neither.** The exits are the block at
`0x9B0B` (which falls into the set at `0x9B12`), the block at `0x9B24` (which
falls into the clear at `0x9B27`), and the block at `0x9B30`, which calls
`0xBA16` and falls straight into `0x9B33` without touching `0x08AD`. So the
polarity is chosen on two exits of three and inherited unchanged on the third,
rather than being written on every pass.

## The prologue's three bail-outs

Each of these returns at `0x9C24` before the dispatch is reached:

| site | the test |
|---|---|
| `0x9AB7` | `0xB9D8` returns non-zero |
| `0x9AC1` | bit 0 of XDATA 0x0490 is clear |
| `0x9ACA` | `0xC26E` leaves R7 at zero |

The issue counted four. The listing has three, and this page records three; the
fourth `ljmp 0x9C24` it expected is not in the function.

`0xC26E` is `FUN_CODE_c26e` in `ec/decompiled/index.csv` and still has no row of
its own. It is four instructions: read XDATA `0x0456`, `jb 0xe7, 0xc278`, and
otherwise `mov R7,#1` and return. The `0xC278` arm is already recorded by that
address's own row, so a separate row here would repeat it for a body this
short — **but the transfer is a branch into the next entry, and that is a
boundary question, not a settled fact.** `0xC26E` is 10 bytes and `0xC278` is
13, and whether the call-target byte scan cut one routine in two here is not
established by anything on this page. It is flagged rather than asserted
either way.

## A carry inherited across a comparison

The value-3 arm's first threshold is one less than it looks:

```
9BBD     d3 - -   setb     CY
9BBE     9f - -   subb     A, R7
9BBF     40 03 -  jc       0x9bc4
...
9BCC     e0 - -   movx     A, @DPTR
9BCD     9f - -   subb     A, R7
9BCE     50 77 -  jnc      0x9c47
```

`0x9BCD` has no `clr CY` of its own, so it inherits whatever `0x9BBE` left.
Reaching `0x9BC4` means `0x9BBF` branched, which means that `subb` borrowed, so
the carry arriving at `0x9BCD` is **set**. The second threshold is therefore
`0x087B - 0x08C8 - 1`, and the test is `0x087B <= 0x08C8` rather than
`0x087B < 0x08C8`. The first threshold is off by one for the same reason, in the
other direction: `setb CY` before `subb` makes it `0x0873 <= 0x08C7`.

The bit-0-clear half of the same arm has no such offset, because `0x9BED` clears
the carry before its `subb` and `0x9BFA` inherits a carry that is known to be
clear (the `jc` at `0x9BEF` is not taken on the path that reaches it). So the
two halves of the value-3 arm compare the same pair of bytes against two
*different* thresholds, `0x08C7`/`0x08C8` against `0x08C4`/`0x08C5`, and they
agree on the boundary rather than on the side: the first half continues at or
below its threshold, the second at or above. Reading either `subb` without its
predecessor's flag state gives the wrong boundary.

## The listing and the decompiled C disagree once, and the listing is right

In the value-2 bit-0-clear arm, `9AAD.c` clears XDATA `0x08AD` and `0x08AE`:

```c
    entry_dptr = (undefined1 *)0x8ad;
    ...
    *entry_dptr = 0;
    dptr_from_bd20 = entry_dptr + 1;
    *dptr_from_bd20 = 0;
```

The listing has no `mov DPTR,#0x08AD` between the `lcall 0xB9F5` and the two
`movx @DPTR,A` that do the clearing. It stores through whatever DPTR the callee
left behind, and `0xB9F5`'s own listing ends

```
BA0E     90 08 cc mov      DPTR, #0x8cc
BA11     e0 - -   movx     A, @DPTR
BA12     95 f0 -  subb     A, B
BA14     22 - -   ret
```

so DPTR is `0x08CC` and the bytes cleared are `0x08CC` and `0x08CD`. The C has
carried a DPTR set before the call across it. This is not a cosmetic
disagreement: `0x08AD` is the byte the dispatch itself branches on, and a
routine that cleared it here would be destroying the very state the arm read to
decide which path to take. The same stale-DPTR shape appears in the C's
value-2 bit-0-set path, where it passes the same `0x8AD` pointer to
`clear_two_bytes_at_dptr_then_9a90` — whose caller has just had `0xBADB` and
`0xBBC7` leave DPTR at `0x08CE`.

`9AAD.asm`'s own header states the rule this page follows: where the two
disagree, the listing is right and the C is a reading of it.

## What is not decoded here

- **What the five values of `0x044B` mean.** No register, subsystem or mode
  name is claimed. The transition map says which value leads to which; it does
  not say what any of them selects. The name `dispatch_044b_then_write_01_02_03_or_04`
  in `../../ec/annotations/ghidra-functions.csv` is deliberately written that
  way for the same reason.
- **What `0x94D0` does with the R7 the arms load.** The five arms pass 4, 5, 6,
  7 and 8 to `copy_code_table_into_0730_07a7`, and this page does not say what
  that routine does with any of them.
- **What `0xB9F5` and `0xBBC7` compare.** Both are read only for the carry they
  leave and the DPTR they leave behind, which is all the arms use. Neither is
  decoded here.
- **Whether `0xC26E` and `0xC278` are one routine.** Flagged above, not
  answered.
- **Whether the EC acts on any of it.** Every statement here is a statement
  about which arm stores which constant. A write being issued is not a
  behavioural observation, and nothing here was read back from hardware.
