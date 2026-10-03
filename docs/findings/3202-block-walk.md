# `0x3202` and the `0x32xx` block: four read sites, no writer found, and two addresses the census does not carry (issue #338)

This is the `0x32xx` block walk issue #290 asked for, and the `registers.yaml`
row it asked for as its deliverable. Both land here. The headline is not the
row — it is what the walk found *beside* `0x3202`: two more addresses in the
block carry direct sites, **both of which write**, and neither has a row.

**Nothing here is a hardware claim.** Every number below is a static scan of the
committed image. No register was read back, nothing was observed on the
machine, and no value is attributed to `0x3202` beyond the bits four routines
test. A zero in this write-up means "not found by this method", never "absent".

**The two images are separated throughout.** The 256 KiB dump holds two
programs — the main EC and, at file offset `0x20000`, the self-contained
`ITE8850-PD` image with its own XDATA map
(`ec/annotations/pd-xdata-overlap.md`). A file-wide count that added the two
together would be a category error, and §"The block" reports the split per
image rather than a total. The PD half of this block is zero.

## What the issue asserted, and what the committed tree says

Two of the issue's premises had moved before it was filed. The wrong versions
are left here beside the corrections, per the calibration rule.

1. **"`xdata-registers.csv` … none in 0x32xx"** — no longer true.
   `ec/annotations/xdata-registers.csv` carries a `0x3202` row and eight other
   `0x32xx` rows today. The block gap the issue describes was closed for
   `0x3202` before the issue was filed. **The census half of the issue was
   already done**, which is why this walk reports the census rather than
   regenerating it to "add" a row that exists.
2. **"The two known accessors … are the citation for bits 0, 1 and 2"** — there
   are **four** accessors, in two polarity pairs, and the census row already
   names all four: `0xC0B8`, `0xC0C9`, `0xC0DA` and `0xC0E7`. The issue names
   only the two non-inverted ones. The row carries all four, because the
   inverted pair is the reason the other pair exists (§"Two polarity pairs").
3. **The value-naming count** — the issue says `r7_from_1984` / `r7_from_19a8`
   is "eight rows" across seven addresses. `ec/annotations/ghidra-variables.csv`
   carries **four** rows under those two identifiers: `0x8DBC` and `0x90B8` as
   `r7_from_1984`, `0x9CC0` and `0xA064` as `r7_from_19a8`. Seven rows mention
   an `lcall 0x1984` or `0x19A8` in their comment text, and the three
   addresses the issue's list adds beyond those four (`0x9199`, `0xA4CF`,
   `0xC614`) carry the more general `r7_from_a_callee` rather than either
   specific identifier. `0xA389` carries a third identifier, `r7_from_198a`,
   which reaches `0xC1E7` and therefore tests `0x1664` — not this byte. The
   figure the issue gives is not repeated anywhere below; the four rows are.

The issue's substantive deliverable is therefore still open, and it is what
this change builds.

## How to reproduce every number here

From the repository root, against the committed image:

```
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x3202
0x3202: 4 direct MOV DPTR site(s)  bank0=4

$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x3200 0x32FF
0x3200-0x32FF: 256 addresses
  main EC :     28 sites over 11 addresses
  PD image:      0 sites over 0 addresses
  both    : 0 address(es) with sites in each image

$ python3 ec/tools/check_register_counts.py ec/firmware/GMxMGxx_11.800
```

The third is the authority for the row's `static_refs` triple: it recomputes
all three count keys from the image rather than trusting the YAML, and it
holds `4 / 4 / 0` for this address.

## The block

Per-address, for the addresses in `0x3200`-`0x32FF` that have any site. The
`common` column is the main EC's shared area, always mapped; `bank0` and
`bank1` are the CODE banks. **Every site is in the main EC, and none is in the
PD image** — the split the issue asked for, and the reason this write-up can
call the block EC-side without a caveat.

| addr | sites | main EC | PD | where | write sites | census row? |
|---|---|---|---|---|---|---|
| `0x3202` | 4 | 4 | 0 | bank0 | 0 | yes |
| `0x3203` | 3 | 3 | 0 | common | 0 | yes |
| `0x3204` | 3 | 3 | 0 | common ×2, bank0 ×1 | 3 | yes |
| `0x3205` | 2 | 2 | 0 | common | 1 | yes |
| `0x3206` | 7 | 7 | 0 | common ×5, bank0 ×2 | 7 | yes |
| `0x3207` | 2 | 2 | 0 | common | 0 | yes |
| `0x3240` | 1 | 1 | 0 | common | 1 | yes |
| `0x3241` | 1 | 1 | 0 | common | 0 | yes |
| `0x3290` | 1 | 1 | 0 | common | 1 | yes |
| `0x3291` | 3 | 3 | 0 | common | 1 | **no** |
| `0x3292` | 1 | 1 | 0 | bank0 | 1 | **no** |

The **write sites** column is the number of that address's sites that
`trace_xdata_refs.py` classifies as writing, from

```
$ python3 ec/tools/trace_xdata_refs.py --csv ec/firmware/GMxMGxx_11.800 \
      0x3202 0x3203 0x3204 0x3205 0x3206 0x3207 0x3240 0x3241 0x3290 0x3291 0x3292
```

where an `access` cell reading `read x1, write x1` is a read-modify-write and
counts once. It is here because **the block is not read-only**: 15 of the 28
sites write, at seven of the eleven addresses. `0x3202` is one of the four
that do not write (`0x3203`, `0x3207` and `0x3241` are the others).

The block is sparse: sites fall in a short run at `0x3202`-`0x3207`, then in
three isolated pairs at `0x3240`, `0x3241` and `0x3290`-`0x3292`, and nowhere
else in the 256-address span. That is what a direct-`MOV DPTR` scan sees. It is
not what the address space looks like to the firmware — see §"What this does
not establish".

**The two rows the census does not carry are reported here and left unrowed.**
`0x3291` has three sites in `common`, two reads and **one write** at `0x0517`
that stores the literal `0xff` and returns; `0x3292` has a single site at
bank0 `0xCD89`, a read-modify-write that ORs `0x80` into the byte. Neither has
a `registers.yaml` row. Both are the same one-line-each shape as `0x3202`, and
adding them is real progress — but it is a different issue from the one filed,
and the correct disposition for a block census that finds them is to say so
rather than fold them in. Dropping them silently would be the
`docs/findings.md` §4c error in miniature: **both write**, and a census that
omitted them would understate the block's writes by two sites — the only two
write sites in the block whose addresses the census does not name.

## Two polarity pairs, which is why four accessors exist

The four come in **two shapes**, one per polarity pair. The bit-0 pair,
`0xC0DA` and `0xC0E7`, is seven instructions — `mov DPTR,#0x3202` /
`movx A,@DPTR` / a bit test / `mov R7,#1` / `ret` / `mov R7,#0` / `ret`. The
bits-1-and-2 pair, `0xC0B8` and `0xC0C9`, is that shape plus **a reload of the
byte before the second bit test** (`movx A,@DPTR` at `0xC0BF` and `0xC0D0`),
which is nine instructions: two bits need a second test, and the second test
re-reads rather than reusing the first read's accumulator. All four have no
`inc DPTR` walk, no store and no call. The polarity is the name, so it is given
per site rather than as a blanket "inverted":

| addr | site | annotated name | tests | R7 = 1 when |
|---|---|---|---|---|
| `0x3202` | `0xC0C9` | `return_1_if_3202_bits_1_and_2` | bits 1 **and** 2 | both **set** |
| `0x3202` | `0xC0B8` | `return_1_unless_3202_bits_1_and_2` | bits 1 **and** 2 | either **clear** |
| `0x3202` | `0xC0E7` | `test_3202_bit0` | bit 0 | bit 0 **set** |
| `0x3202` | `0xC0DA` | `return_1_unless_3202_bit0` | bit 0 | bit 0 **clear** |

The two pairs are **exact complements** — the mirror-accessor shape
`xdata-1663-1667-1668.md` records for the `0x166x` run, where one caller wants
a bit and the other wants its complement. That agreement is a result, not a
risk to guard against: it is what the same test written twice is supposed to
look like. So bits 0, 1 and 2 are each read, and **no site here examines a bit
above 2** — which is what the row's `bits: [0, 1, 2]` asserts, and no more.

The census row's `refs=6` is a **different unit, not a disagreement**. It
counts C-level `movx` occurrences across the same four functions, and two of
them reload the byte before their second bit test, so four direct sites become
six C-level reads. `check_register_counts.py` recounts from the image and is
the authority for the `4 / 4 / 0` on the row; the two numbers meet
unexplained in neither direction, which is the same handling
`XDATA_1664`'s note gives the three-to-one gap it has.

**No writer for `0x3202` was found by this method.** That is a gap in the
search, not evidence that none exists: a store through a computed DPTR, an
indirect `movx @Ri`, or a CODE table are all invisible to both tools used
here, and `0x07B9` is the standing counter-example — writable, working, zero
direct sites anywhere in the image. With no writer, the value space is
unestablished, so what the three bits select is not stated.

## What the byte gates

`0x3202` is the register the `0x06D9` countdown actually reads. bank1 `0x8096`
lcalls `0x1984` and `0x198A` and decrements `0x06D9` only when **both** return
zero. `0x198A` reaches bank0 `0xC1E7` (`test_1664_bit0`), which is the
`XDATA_1664` row's own accessor. `0x1984` reaches bank0 `0xC10C`, a seven-
instruction thunk with no committed listing that lcalls `0xC0C9` and restates
its answer in R7 — so that arm tests bits 1 and 2 of `0x3202`, read one call
deeper. Both arms read bytes from outside the `0x06C2`-`0x06DB` block.

`ec/annotations/xdata-06c2-06db-timers.md` §4 and §8 item 2 carry the full
account; its §8 item 2 was the open question this change closes, and the three
annotation comments that said in their own text that the byte had no row are
corrected here rather than left to become false.

**What this byte does not have is a writer.** `0x3202`'s four sites are all
reads — the byte, not the block around it: seven of the block's other ten
addresses do write (§"The block"). `0x06D9`'s gate is therefore a predicate
over a byte set elsewhere — by something this method cannot see, or by hardware
that writes it directly. Neither is established here.

## What this does not establish

- **That `0x3202` is a hardware register, or that it is EC state.** High XDATA
  is *plausibly* a hardware block rather than the EC's own allocation — that
  was a hypothesis in the issue, and the walk neither confirms nor refutes it.
  A block this sparse in direct references is equally consistent with a
  hardware page touched through two predicates and a memory-mapped device
  written from outside the direct-addressing modes, and nothing measured here
  separates those.
- **That the byte has no writer**, or that the bits select anything. Both are
  "not found by this method".
- **That the PD image does not use the `0x32xx` range.** It has zero direct
  sites there by this scan, which is a different statement and is not
  evidence about its indirect or table-driven use.
- **Anything about behaviour.** No value was read back and nothing was
  observed on hardware. `docs/hardware-tests/xdata-06c2-06db-sweep.md` already
  carries the `0x3202` sampling step for a human at the machine; it is not
  edited here and was not run.

## What is still open

- **Rows for `0x3291` and `0x3292`.** Reported above, deliberately not landed
  here. `0x3291` is the more interesting of the two: of the pair, it is the one
  whose single write site is a **plain store of a whole-byte literal** rather
  than a read-modify-write — `mov a,#0xff` / `movx @dptr,a` at `0x0517`,
  against `0x3292`'s `ORL A,#0x80` / `MOVX @DPTR,A` at `0xCD89`. Plain literal
  stores are not unique to it: the block has five (`0x3204` at `0xCD90`,
  `0x3205` at `0x0BE6`, `0x3206` at `0x0B66` and `0x0B87`, and `0x3291` at
  `0x0517`), and `0x3291`'s is the only one of the five that stores all-ones.
- **The reload path.** Named, not bounded: a computed DPTR, a register-indirect
  access and a table are all invisible to both methods here. Whatever sets the
  bits of `0x3202` is behind that blind spot, and it is the one thing that
  would move the byte from a predicate to a known value space.
- **The `0xC10C` / `0xC118` export** (`xdata-06c2-06db-timers.md` §8 item 1).
  Seeding those routines needs a row in the single-writer
  `ec/ghidra/reassembly.csv`, so it stays open.
- **What any of this means to the silicon.** Out of scope by the issue's own
  scope note, and correctly so: with no writer found by either method, the
  honest statement is the address and the three bits four routines test.