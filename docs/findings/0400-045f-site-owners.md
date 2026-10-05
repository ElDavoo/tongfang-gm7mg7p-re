# What the 23 unattributed `0x0400`-`0x045F` sites turned out to be once their routines were named

Issue #175 seeded the EC routines that own the 23 `0x0400`-`0x045F` sites
`ec/annotations/xdata-0400-045f.md` §5 could not attribute, so each of those
addresses is now inside a named, cited export instead of sitting between two.
The per-address ownership table and the decode of every one of the twenty-three
sites is §5's **Seeded, 2026-10-03 (issue #175)** block, and this document does
not restate it; what follows is only what the names make readable that the
addresses could not carry.

Three of those readings are real advances in what the firmware is doing —
`0x0457`'s low-three-bit field, the `0x0404`/`0x0436` pair comparison, and
`0x0440`'s reader shape — and they are §1 to §3 below. The rest is §4, which is
one line per remaining byte and points at §5 rather than repeating it.

**Nothing here is a behaviour.** No `status:` moved, no `static_refs*` count
changed, and every entry on the page stays as it was: a read-modify-write that
is now readable inside a named export is not evidence the EC acts on the byte,
and a whole-byte store of a constant is a stored constant, not a readback. No
live test ran; this pipeline has no machine, and every sentence below is read
from bytes in `ec/firmware/GMxMGxx_11.800`.

## 1. `0x0457`'s low three bits are loaded with three distinct constants, which is a shape and not a meaning

All four of the byte's EC-side `MOV DPTR` sites are read-modify-writes, and all
four now sit one in each of four named exports. Each clears bits 0-2 with
`anl a,#0xf8` and then either ORs a constant or does not:

| site | owning export | constant loaded into bits 0-2 |
|---|---|---|
| bank1 `0x8190` | `set_0472_20_and_0457_low3_101` | `0b101` |
| bank1 `0x81D1` | `clear_0457_low3_and_dispatch_0800_bit7` | `0b000` |
| bank1 `0x8246` | `set_0472_08_and_0457_low3_011` | `0b011` |
| bank1 `0x826A` | `set_0472_20_and_0457_low3_101_then_gate` | `0b101` |

`0x81D1` is the one site of the four with no `orl` after the mask, so it zeroes
the field rather than loading into it. Bits 3-7 pass through untouched at all
four. **`0xfd & 0x07 = 0b101`, which is what the `orl a,#0xfd` at `0x8190`
reproduces.**

The `0x0472` write beside each site is worth naming per routine rather than by
position, because the four are not the same kind of write.
`set_0472_20_and_0457_low3_101` (bank1 `0x8190`) stores the constant `0x20`
into `0x0472` whole — `mov A,#0x20 / movx @DPTR,A`, no mask and no `orl`. The
other three each rewrite `0x0472` as `anl A,#0x10 / orl A,#0xNN`, which **sets
their bit whether or not bit 4 was set** and leaves bit 4 as it was, the other six
bits going to zero: `clear_0457_low3_and_dispatch_0800_bit7` (bank1
`0x81CC`-`0x81CE`) sets bit 0, `set_0472_08_and_0457_low3_011` (bank1
`0x8241`-`0x8243`) sets bit 3, and
`set_0472_20_and_0457_low3_101_then_gate` (bank1 `0x8265`-`0x8267`) sets bit 5.
Those same three are the ones that clear bits 0-2 of `0x0457` and load `0b000`,
`0b011` and `0b101` respectively, so **three of the four routines rewrite one
byte of `0x0472` around a single bit — set, with bit 4 preserved and six bits
cleared — and load a constant into a three-bit field of another, and the fourth
only clears.**

A field that four routines load three distinct constants into is a small
enumerated state rather than a flag. That is the strongest reading the shape
supports and it is still a shape: **what any of the three values means is not
established.** The four whole-byte CODE-record stores that seed the byte
`0x00`, `0x05`, `0x80` and `0x83` are a second writer class on top
(`ec/annotations/xdata-0400-045f.md` §12), not an explanation of these four.

## 2. The EC compares `0x0404`/`0x0405` against `0x0436`/`0x0437` as two 16-bit values

`compare_0404_0405_pair_against_0436_0437` (bank0/AA04.asm) reads the pair and
exclusive-ORs it against the other pair, half at a time, and the ordering is
load-bearing. At bank0 `0xAA34`:

```
AA34     90 04 04 mov      DPTR, #0x404
AA37     e0 - -   movx     A, @DPTR
AA38     fe - -   mov      R6, A
AA39     a3 - -   inc      DPTR
AA3A     e0 - -   movx     A, @DPTR
AA3B     ff - -   mov      R7, A
AA3C     90 04 36 mov      DPTR, #0x436
AA3F     e0 - -   movx     A, @DPTR
AA40     6e - -   xrl      A, R6
AA41     70 03 -   jnz      0xaa46
AA43     a3 - -   inc      DPTR
AA44     e0 - -   movx     A, @DPTR
AA45     6f - -   xrl      A, R7
AA46     70 03 -   jnz      0xaa4b
AA48     02 c0 9c ljmp     0xc09c
```

The `inc dptr` at `0xAA43` sits **behind** the `jnz` at `0xAA41`, so `0x0437` is
read only when `0x0436` already matched, and a match on both halves tail-jumps to
`0xC09C`. That is a 16-bit equality test between the two pairs.

It says how the firmware uses the pair, not what either measures. `0x0436`/`0x0437`
keeps upstream's remaining-capacity name recorded and not adopted
(`ec/annotations/xdata-0400-045f.md` §8 and `docs/findings/0436-capacity-ladder.md`
are where that question stands), and the live read beside WMI `RemainingCapacity`
in `docs/hardware-tests/remain-capacity-0436.md` is still what would settle
counter-versus-capacity. **It has not been run.**

The same routine also reads `0x0432` at bank0 `0xAA13` and branches on it for
**bit 1 only** (`jnb 0xe1, 0xaa1c` — `0xE1` is `ACC.1`). Upstream reads bit 0 as
`BAT_DISCHARGING`, and this is the one site on the byte that tests any bit at
all, so which bit means discharging is still not established — the two readings
do not agree, and this is not the place to settle it.

## 3. `0x0440`'s five newly-named readers all gate on it, and three of them say which byte the gate opens

Five more of the page's readers are now inside named exports, and all five read
the byte the same way: for non-zero and nothing else, discarding the value. Three
are separate entries in bank1 — `gate_06e6_01_and_0440_nonzero_then_set_06ff_bit3`,
`_bit2` and `_bit1` (bank1/F31F.asm, F334.asm, F349.asm) — each gated on `0x06E6`
reading `0x01` *and* on `0x0440` being non-zero, differing only in which bit of
`0x06FF` they then set. So **a non-zero `0x0440` raises three separate bits of
`0x06FF`, and nothing in this repository's exports says what reads those bits.**

**That is narrower than it first reads.** Each of the three is still a zero test
whose zero arm is a bare `ret`, which is the enable-flag shape
`ec/annotations/xdata-0440-readers.md` §2/§3 already assigns to that address's
zero tests; the three add to the set of sites that are named, not to the shape,
and are additional to the counts that document measured. The
selector reading — zero not being one state either, so the byte choosing between
behaviours — is that document's §2/§3 and the `XDATA_0440` entry's own preceding
paragraph, recorded before this change, and is not claimed here.

The other two are bank0 `0xC703` in
`flip_0751_bit6_when_r7_zero_and_0440_nonzero` (bank0/C700.asm) and bank0 `0xC71A`
in `fan_mode_from_0440_into_0741_0751` (bank0/C717.asm). **These two are not a
complementary pair.** Both encode the `0x0440` test the same way — `jz` to their
own `ret` — so both bodies are reached only when the byte is **non-zero**: they
are two consumers of one condition, and which of the two runs is settled by the
caller rather than by `0x0440`. The first then exclusive-ORs bit 6 of `0x0751`, a
toggle whose effect depends on state this repository has not measured.

One consequence of that second routine is easy to get backwards.
`fan_mode_from_0440_into_0741_0751` ends its paths through `anl A,#0x6f` at
bank0 `0xC75D`, and `0x6F` is `0b01101111` — it clears bits 7 and 4 and
**preserves bit 6**. So the bit-6 toggle is not cleared by that mask; the bit it
does clear is bit 4.

## 4. The rest, one line each, with the decode in §5

Each of these is a coverage change — an address that had no enclosing export now
has one whose name says what the code does — and the disassembly is in §5's table
and in the committed listings it cites.

- **`0x0403`** — bank1 `0xBB68` is inside
  `stage_0834_from_0403_threshold_and_0497` (bank1/BB40.asm), which reads the
  byte, subtracts `0x14` with `subb a,#0x14` and branches on the borrow: one of
  the page's threshold comparisons, in the `subb`-against-A form rather than the
  `jz`-after-`subb` of bank1 `0xA269`.
- **`0x0404`** — bank1 `0xE70B` hands DPTR to `0x8886`
  (`read_xdata_pair_to_r1r2`) inside
  `read_0404_0405_into_r1r2_then_mul_and_clamp` (bank1/E6DC.asm), so the pair is
  read as a 16-bit value and fed to a multiply-and-clamp chain. bank0 `0xAA34` is
  §2 above.
- **`0x0420`** — bank1 `0xE779` was a blind spot because the holding routine was
  unnamed, which is why `docs/findings/handoff-site-warrant.md` records it as
  `unresolved-none` with no `movx` in the window. It is named:
  `clamp_r2r1_to_0420_above_3c0b`, entered at bank1 `0xE769`, and `0xE779` is
  four instructions into that body. **The byte's address is still handed to a
  caller this scan cannot see and the site is still neither a read nor a store;
  what changed is that the routine is no longer the gap.** The entry stays
  `present-untested`.
- **`0x043E`** — bank1 `0x8637` is `copy_043e_to_1501`, and bank1 `0x8640` is
  `copy_043f_to_1501`: each half of `CPU_TEMP`'s pair has its own entry and each
  clobbers the same `0x1501`, with no arithmetic on the byte.
- **`0x0456`** — bank1 `0x83E5` is inside
  `zero_045a_then_reset_0459_bit3_and_0456_low5` (bank1/8354.asm), which also holds
  the `0x83EE` store. It clears bits 0-4 and leaves bits 5-7, which makes it the
  **first writer found in bank 1 to touch this byte at all** — the two writers
  the page document names (bank0 `0xAD65` clearing bits 4-5, bank0 `0xDA81`
  setting bits 6 then 7) are both bank 0. So the byte's writers account for bits
  4-5 cleared, bits 6-7 set, and bits 0-4 cleared outright, and nothing here
  establishes what bits 0-3 hold in between. Upstream tests only bits 5-7. The
  bit-7 reading as `HAS_GPU` is unchanged and still a plausible reading of a
  consistent shape.
- **`0x0459`** — bank1 `0x83C0` is in the same routine, clearing bit 3
  (`anl a,#0xf7`), so the writer the page document could not name is named and
  bit 3 joins bits 1 and 2 as a bit this byte's writers assemble.
- **`0x045A`** — bank1 `0x8354` is the entry of that routine, and what it does to
  the byte is the plainest form on the page: `mov A,#0x00 / movx @DPTR,A`, a
  whole-byte zero with no mask and no OR, where the two read-modify-writes
  already named assemble single bits. **That `0x045A` is zeroed outright while its
  other writers assemble single bits is consistent with the packed-flag reading
  and does not settle it** — nothing here says which bits a non-zero value would
  carry.
- **`0x045F`** — the two writers the page document could not place are a set/clear
  pair rather than two independent stores. bank1 `0x8609` is
  `store_db_to_045f_and_set_04ff_bit5` (bank1/8609.asm), which stores the constant
  `0xDB` into the byte whole — no mask, so it does not preserve bits a reader may
  be testing — and then sets bit 5 of `0x04FF`; bank1 `0x8617` is `zero_045f`
  (bank1/8617.asm), four instructions writing `0x00` to the same byte. **So this
  byte has a stored-`0xDB` state and a stored-`0x00` state, and nothing in this
  repository's exports says which bits it is expected to hold between them.**

## 5. What is left open, and what would settle it

None of the following is answered by a name, and all three need the machine:

1. What any of `0x0457`'s four low-three-bit values means. A live read of the
   byte across the transitions would settle it. §1 poses it sharply; it does not
   answer it.
2. What reads the three bits of `0x06FF` that a non-zero `0x0440` raises.
3. What `0x0436`/`0x0437` measures. This one keeps its existing issue, and
   `docs/hardware-tests/remain-capacity-0436.md` is the prepared run.

A fourth is a method limit rather than a byte: `step_0628_nibble_against_92dc_table`
(bank1/9202.asm) has a non-contiguous body — it runs `0x9202`-`0x920B`, then
resumes at `0x926C` to its own `ret` — and `listing-index.csv`'s `size` column is
a byte count rather than an extent, so an `addr`+`size` containment test cannot
see an address a body reaches by a branch. One site of the twenty-three was
already covered for that reason. **Any containment check of that shape
under-reports coverage for a non-contiguous body**, and reading the `.asm` bodies
is what finds it. §5 of the page document records this against the table it
corrected.

## 6. Where the coverage table lives, and what did not run

`ec/annotations/xdata-0400-045f.md` §5 holds the per-address table for all
twenty-three sites, the decode behind each row, and the correction for the
`0x926C` row above. This document deliberately does not duplicate it: a second
table of the same addresses is a second thing to keep in step with the exports.

`ec/ghidra/project/` stays byte-identical to main, so **the seeded routines exist
in the committed `.c` and `.asm` and not yet in the committed project database.**
`docs/findings/ghidra-project-owner.md` measures why — the committed projects are
owned by `dave`, and `analyzeHeadless` refuses to open one for anyone else, which
scopes `--mode rebuild-project` out for an agent branch because that mode writes
the committed database rather than a copy. The exports here come from
`--mode export-only`, which copies the project, normalises the copy's owner and
seeds the annotation rows into the copy. The remaining step is a
`--mode rebuild-project` run on a machine that can open the project.