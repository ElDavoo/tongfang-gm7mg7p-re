# `0x08EB`: what each of its six bits is set, cleared and branched on by

`ec/annotations/registers.yaml` has carried `XDATA_08EB` since #224 with
`bits: [2, 3, 4, 5, 6, 7]` and `status: present-untested`, and a note that
explains bits 3 and 6 as a set/clear latch pair and lists the rest without
saying what they do. This is the per-bit accounting #224 left open: a writer
list, a reader list and a statement of which arm decides what, for each of the
six bits. The machine-readable form is
[`ec/annotations/xdata-08eb-bit-sites.csv`](../../ec/annotations/xdata-08eb-bit-sites.csv),
one row per site and bit; §1 is the command that produces it.

**Nothing here is a live observation.** No register was read back and no
hardware was touched. Every statement here is a statement about instructions
in the committed firmware, and the entry stays `present-untested` because
"the EC touches this bit" is not "the EC acts on it". What the bits govern --
dwell time, fan curve, anything behavioural -- is not establishable from a
disassembly and nothing below implies otherwise.

## 1. How to reproduce it

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x08EB \
        --csv --terminator-column
$ python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800 --at 0x0BB22 -n 8
```

The first is the whole of the site set: 21 direct `MOV DPTR,#0x08EB` sites,
20 in bank0 and one in bank1, none in the PD image, which is what
`static_refs: 21` in the entry already records. It is read-only, needs no
Ghidra and no hardware. The second is only for the three sites no committed
listing covers (§5).

`ec/tools/test_xdata_08eb_bit_sites.py` holds the table to that output in both
directions and derives every bit number from the sweep's own `window` string,
so a bit list cannot drift away from the image without the suite going red.

## 2. The per-bit table

`set` and `clear` are the instruction that changes the bit, `branch` is where
it is tested and nothing is stored at that address. Both access columns are
in the table; §5 is why there are two.

| bit | set | clear | branched on |
|---|---|---|---|
| 2 | `0xD487` | `0xD6A8`, and `0xCD3C` behind the `jnb acc.2` at `0xCD34` | `0xCD34` |
| 3 | `0xB690` | `0xB716` | `0xB65B`, `0x8931` |
| 4 | `0xCCBE`, when bit 1 of `0x0490` is **clear** | `0xCCC4`, when bit 1 of `0x0490` is **set** | `0xA916` in bank1, no store |
| 5 | `0xB53E` | `0xB5B2` | `0xB501` |
| 6 | `0xB7F4` | `0xB82E` | `0xB7BB`, `0x8931` |
| 7 | `0xC86A` | `0xB476`, and `0xB491` behind the `jnb acc.7` at `0xB489` | `0xB489`, `0xB497`, `0xC47E`, `0xC860` |

The two entries marked "behind the" are the ones a linear walk cannot see, and
they are the whole of what §5 is about. A site and the instruction that
carries the bit are not always the same address: bit 4's row names the two
arms because `0xCCB7` is a single site, and the table keeps both anyway, in
`runtime` for the site and `insn_addr` for the instruction.

Three sites are not exported into the decompiled tree and are read from the
image instead: `0xC860`, `0xC86A` and `0xD487`.

## 3. `0x8931`: what the `0x48` branch selects, and a correction

The two latch bits are read together at `0x8931`, which loads DPTR with
`0x08EB`, reads the byte, masks `0x48` -- exactly bits 3 and 6 -- and branches
on the result with `jz 0x8942`. What it decides is now decoded: **either bit
set and the routine does one thing; both clear and it runs its five blocks.**
The five-block body is described in `ec/annotations/ghidra-functions.csv`'s row
for `0x8931` and is not repeated here. The other arm is the nine bytes at
`0x8939`-`0x8941`, and it publishes 200.

**The committed row for `0x8931` is wrong about where 200 is staged, and the
correction is worth stating carefully because the decompile is wrong with it.**
Both `8931.c` and the annotation read the arm as `*puVar3 = 200` into XDATA
`0x08EB`, with `puVar3 = &XDATA_08EB` captured at function entry. The bytes
say otherwise:

```
8939     12 bb 22 lcall    0xbb22
893C     74 c8 -  mov      A, #0xc8
893E     f0 - -   movx     @DPTR, A
893F     02 8f 09 ljmp     0x8f09
```

The `lcall` is not a constant-supplying stub that returns.
`ec/decompiled/bank0/BB22.asm` is one instruction with **no `ret`**: it is the
head of a fifteen-byte sequence that `BB24.asm` and `BB28.asm` continue,
ending in the `ret` at `0xBB30`. Decoded from the image:

```
BB22  mov a,#0xc8      BB29  mov dptr,#0x075b
BB24  mov dptr,#0x1804 BB2C  movx @dptr,a
BB27  movx @dptr,a     BB2D  mov dptr,#0x1809
BB28  movx a,@dptr     BB30  ret
```

So the call leaves **DPTR pointing at XDATA `0x1809`**, and the
`movx @DPTR,A` at `0x893E` stores 200 there. The `ljmp 0x8F09` then copies
`0x1809` into `0x075C`. Four XDATA bytes are touched -- `0x1804`, `0x075B`,
`0x1809`, `0x075C` -- and `0x08EB` is not one of them.

This is what the header on every committed `.asm` listing is for: *where the
two disagree, this file is right and the C is a reading of it*. The C keeps its
reading, because it is generated and the next export reproduces it; the
correction belongs in the annotation and here. Per CLAUDE.md's rule the
sentence that was wrong is left standing in the `ghidra-functions.csv` row
with the correction next to it, not edited away.

So `0x8931` is a **reader** of `0x08EB` and only a reader, and the sweep's
`read x1` for that site is right. The two latch bits are not written by the
routine that tests them, which is the useful thing to know about them: the
test is a gate on the whole routine, not a flag the routine maintains.

What the routine publishes is 200 into MAIN_FAN_R_DUTY (`0x075C`) and
MAIN_FAN_L_DUTY (`0x075B`) and the two `0x18xx` cells. What 200 means there is
not decoded here.

## 4. `0xCCB7`: a set/clear pair whose polarity the note did not record

`CC64.asm` settles this one, and the answer is which way round. At `0xCCB3`
it loads DPTR with `0x0490` and reads the byte into A; at `0xCCB7` it loads
DPTR with `0x08EB`; at `0xCCBA` the `jb 0xe1` branches on **bit 1 of that
other byte**, still in A. Both arms re-read `0x08EB` and store it:

- not taken, bit 1 of `0x0490` **clear**: `orl A,#0x10` at `0xCCBE`, so bit 4
  is **set**;
- taken, bit 1 of `0x0490` **set**: `anl A,#0xef` at `0xCCC4`, so bit 4 is
  **cleared**.

The entry recorded the pair but not the direction, and the direction is the
whole content of it. `ec/annotations/ghidra-functions.csv` already names the
selector -- its `0xCC64` row spells out that the `jb acc.1` tests `0x0490`
rather than `0x08EB` -- so what is added here is which arm does what.
`0xCC64` is `init_06e6_1_clear_0743_07c5_and_07d5_ff`, an initialisation pass,
so **bit 4 of `0x08EB` is initialised from bit 1 of `0x0490`, set when that is
clear.**

That meets the second of the two leads #224 named. `bank1:0xA916`
(`clamp_078b_level_into_0804`) reads bit 4 with `anl A,#0x10` and branches on
it at `0xA91C`, with the store-back deliberately omitted -- it is the first of
that routine's four gates, and it returns through `0xA9B3` when bit 4 is set.
So bit 4 is *initialised* at power-on by one polarity of `0x0490` and
*gates* a bank1 clamp on the opposite. **The only site this reading finds that
clears bit 4 is the other arm of that same `jb`.** What sets bit 1 of `0x0490`
is not followed here and is the natural next question; nothing in this file
answers it.

`0xA916` also passes `0x08A1` and `0x08A2` to `0x88A4` on its way. That is
the reader #224 recorded for `0x08A2` and left explicitly undecoded; the
observation stands and is not restated here.

## 5. Three methods, and the three sites where they disagree

`trace_xdata_refs.py`'s `access` column and the `resolution` column in
`ec/annotations/site-resolution.csv` agree at every one of these sites --
they are two linear walks over the same bytes, and they stop at the same flow
opcodes -- so the useful third reading is the committed `.asm` listing, which
follows the branch the walk stops at. Every row of the table carries both, in
`sweep_access` and `listing_access`, and they differ at three sites. All three
are the same defect, and it is the one `ec/annotations/registers.yaml`'s header
names: **a store a branch jumps over is invisible to a linear walk.** In each
case the window ends on a flow opcode -- the tool's `terminator` column says
so -- and the store is on the fall-through.

| site | sweep | listing | what sits behind the branch |
|---|---|---|---|
| `0xB489` | `read x1` | `read+write` | `anl A,#0x7f` at `0xB491` clears bit 7 |
| `0xCD34` | `read x1` | `read+write` | `anl A,#0xfb` at `0xCD3C` clears bit 2 |
| `0xCCB7` | `no movx found in the decoded window` | `read+write` | both arms store, `0xCCBE` and `0xCCC4` |

`site-resolution.csv` records `0xCCB7` as `unresolved-none`, and that row stays
as it is: it is a true statement about the method that produced it, and
`ec/tools/check_status_vocabulary.py` reads that column. The table here
records the divergence beside it rather than overwriting it.

The three sites with **no** committed listing -- `0xC860`, `0xC86A` and
`0xD487` -- are read from the image with `disasm8051.py` instead, so their
`listing_access` column is a reading of the bytes rather than of a listing.
Naming them `not exported` is what they are, not a judgement about the code.

## 6. What this covers, and the two kinds of nothing

Every site the sweep finds appears in the table and every site in the table is
one the sweep found; the suite checks both directions rather than a count, so
the claim survives a firmware whose site set moves. Per bit, the sites are as
§2 lists them, and the entry's `bits:` field is unchanged by any of it --
all six are attested by a committed listing, so the field was already accurate
and what changed is the note beside it.

Two negatives have to stay apart, and the table keeps them apart by having an
access column per method rather than one corrected column:

- **not reached by this reading** -- a bit no site in the table names. Bits 0
  and 1 are the ones this reading says nothing about; they are outside the
  entry's `bits:` and are not claimed to be unused, only unaccounted for here.
- **no site this method finds** -- a byte with no writer. No such statement is
  made about `0x08EB` anywhere in this file, because none of its three
  methods is the kind that can support one: the sweep sees only direct
  `MOV DPTR` sites, so a byte reached by a computed DPTR or an anchored
  `movx @Ri` is outside it. `find_indirect_xdata.py` is that separate scan and
  **was not run here**, so this file makes no claim about it either way.

A store is a store. Reading a byte back and getting the value written would not
settle what any of these bits governs, and nothing here was read back.

## 7. Follow-ups

- What sets and clears bit 1 of `0x0490`, which is the gate that decides bit
  4's polarity (§4). Named rather than chased here.
- Naming the containing functions of the three `not exported` sites, and
  seeding entries for `0xC860`, `0xC86A` and `0xD487`. That re-exports the
  generated tree, so it is a change of its own.
- `ec/annotations/ghidra-functions.csv`'s rows for `0x8939`
  (`store_200_via_dptr_then_8f09`) and `0x893E`
  (`store_a_via_dptr_then_jump_8f09`) both carry a claim §3's decode refutes.
  The `0x8939` row says the single branch reaching it in this shard is the
  `ljmp` at `0x8755`, which arrives with DPTR = `0x06E6`, "so the byte written
  is XDATA 0x06E6"; the `0x893E` row carries the same clause. **The byte
  written is `0x1809` whichever way `0x8939` is entered**, because the
  `lcall 0xBB22` at `0x8939` runs before the store at `0x893E` and reloads
  DPTR to `0x1804` and then `0x1809` on every entry. Reachability is a second,
  separate defect in the `0x8939` row: the `jz 0x8942` at `0x8937` falls
  through into it too, and arrives with DPTR = `0x08EB` -- `0x8931`'s
  `mov DPTR,#0x08EB`, and neither the `movx a,@dptr` at `0x8934` nor the
  `anl A,#0x48` at `0x8935` changes it. DPTR becomes `0x1809` only when that
  `lcall` returns, which is after entry, not on it. Neither clause was
  corrected here: they are about the two forwarder rows rather than about
  `0x08EB`, and this change keeps its edits to shared files small.
- The decompile reading behind §3 -- a decompiler carrying a pointer across a
  call that reloads DPTR -- is a class, and one instance is not a census of it.
