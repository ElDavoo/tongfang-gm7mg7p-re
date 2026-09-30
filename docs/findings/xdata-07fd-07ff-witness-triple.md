# The `0x07FD`-`0x07FF` triple: a three-byte witness whose third byte discriminates (issue #573)

`docs/findings/reset-vector-dptr-targets.md` established that the reset
vector's `0xD96C` clear sweeps `0x0100`-`0x0FFF` and steps over exactly three
bytes, `0x07FD`, `0x07FE` and `0x07FF`. It deliberately claimed nothing about
what those three bytes are and left "preserved across a warm reset" as a
hypothesis. This is the reading of them.

The block is a **three-byte handshake whose third byte chooses between two
outcomes**. Three bytes are written together, a pair of them is read back and
cleared by a consumer, and the byte that is *not* part of that pair decides
which of two paths runs. Two routines write the pair; two others write the pair
with the third byte zeroed instead of set; one routine reads the pair, writes
the third byte, and jumps the reset vector. Five routines in all, and **two of
them are in no committed table in this repository** — no listing, no
`xdata-registers.csv` row, no `bank-call-targets.csv` row.

The load-bearing evidence is the committed image and this repository's own
decoder, `ec/tools/disasm8051.py`, run as
`make_bank_image.py`'s address arithmetic gives it. The method is the same one
#559 used, for the same reason: the listings **anchored at the entry points in
question** stop short of the code that matters (§"The listings stop short"
below), so an entry's own `.asm` cannot be relied on past its
`listing-index.csv` size. Sibling committed listings do carry some of it — that
section names which — and the disassembly is still load-bearing for the framing
at `0x8624` and `0xA69F`, which no listing covers at all, and at `0xD856`,
whose covering listing is anchored at `0xD757` rather than at the address being
framed. `ec/tools/test_xdata_07fd_07ff_triple.py` pins every byte fact below
against `ec/firmware/GMxMGxx_11.800`, so a regenerated census that disagreed
would fail rather than pass on a stale pair.

## Establishing the method on a control address

`python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07FD 0x07FE 0x07FF 0x08EB`:

```
0x07FD  refs=7  ec=7  pd=0
0x07FE  refs=9  ec=7  pd=2
0x07FF  refs=8  ec=7  pd=1
0x08EB  refs=21 ec=21 pd=0
```

`0x08EB` is the control, and it is the reason the method's recall on this image
is licensed rather than assumed: 21 EC-side sites, exactly the
`static_refs_main_ec: 21` its committed `registers.yaml` row already carries.
A scan whose count matches a hand-audited address on the same firmware is
worth running on its neighbours.

**The EC-side count is 7 for all three bytes, and the census's `8`/`10`/`10` is
not that number.** The extra 1, 3 and 3 are sites in the separate ITE8850-PD
image at file `0x20000`, which is its own 8051 program with its own XDATA map
— a `MOV DPTR,#0x07FE` there is not a reference to the EC register of that
number. `scan_refs.py`'s own header and `docs/findings.md` §3a say the split
has to be kept, and keeping it is what turns the census's file-wide totals into
the 7/7/7 this write-up is built on. The issue's "lower bound over exported
code" is right in kind; the specific rows overstate the EC-side count.

## The five writers and readers

`python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07FD 0x07FE 0x07FF`
gives 7 EC-side `MOV DPTR` sites per byte, and they resolve to five distinct
routines:

| entry | bank | what it does to the triple | exported listing? |
|---|---|---|---|
| `0xCCFC` | bank0 | `0x55`/`0xAA`/`0x5A`, then `CD5A 80 fe` — spins forever | `CCFC.asm` |
| `0xD673` | bank0 | `0x55`/`0xAA`/`0x5A` through `lcall 0xD6EA`, then spins at `0xD6C7` | `D673.asm`, truncated before the spin |
| `0xD856` | bank0 | `0x55`/`0xAA`/`0x00`, carries on | inside `D757.asm` (`state_1500_1504_1510_1514_to_0200`) |
| `0x8624` | bank1 | `0x55`/`0xAA`/`0x00`, then `ret` | **none** |
| `0xA69F` | bank1 | tests `0x55`/`0xAA`, writes `0x5A`, `ljmp 0x0000` | **none** |

Of the five, **`0x8624` and `0xA69F` sit in no exported listing at all** — no
`ec/decompiled/` file covers them, and the regenerated
`ec/annotations/site-resolution.csv` records their containing function as
`not exported`, which is that tool's own way of saying the same thing. The
census's `main-ec-086` cluster carries none of the five sites individually;
`0xD856` is reachable only because it falls inside the exported `0xD757`.

The two writers that store `0x00` — `0xD856` and `0x8624` — are
byte-identical in that third store, and it is `mov a,#0x00` where `0xCCFC` and
`0xD673` have `mov a,#0x5a`. That is the substantive new fact, and it is what
the block is:

**the third byte is a discriminator, not a third copy of the same value.**

### The consumer at `0x94FA` branches on it

`ec/decompiled/bank1/94FA.asm` (`magic_55aa_and_0704_countdown`) is the reader
the census already knew about, and the branch is on the odd byte out:

```
0x9500  90 07 fe   mov  dptr,#0x07fe
0x9503  e0         movx a,@dptr
0x9504  b4 55 2b   cjne a,#0x55,0x9532
0x9507  90 07 ff   mov  dptr,#0x07ff
0x950a  e0         movx a,@dptr
0x950b  b4 aa 24   cjne a,#0xaa,0x9532
0x950e  e4         clr  a
0x950f  90 07 fe   mov  dptr,#0x07fe
0x9512  f0         movx @dptr,a
0x9513  90 07 ff   mov  dptr,#0x07ff
0x9516  f0         movx @dptr,a
0x9517  90 07 fd   mov  dptr,#0x07fd
0x951a  e0         movx a,@dptr
0x951b  b4 5a 03   cjne a,#0x5a,0x9521
0x951e  02 95 b7   ljmp 0x95b7
0x9521  90 00 45   mov  dptr,#0x0045
0x9524  e4         clr  a
0x9525  f0         movx @dptr,a
0x9526  90 07 fd   mov  dptr,#0x07fd
0x9529  74 00      mov  a,#0x00
0x952b  f0         movx @dptr,a
0x952c  90 1f 07   mov  dptr,#0x1f07
0x952f  74 00      mov  a,#0x00
```

On a `0x55`/`0xAA` match it clears **both** bytes of the pair, then reads the
third: `0x5A` takes `ljmp 0x95b7` (`load_0704_from_045d_then_branch`), and
anything else clears `0x0045`, `0x07FD` and `0x1F07` and falls through. So the
pair is consumed and the discriminator picks the arm — two outcomes, and only
one of them was visible from the three sites the census named.

### `0xA69F` reads the pair and jumps the reset vector

`0xA69F` is the third site, and it is what makes "preserved across a reset"
more than a shape. It *reads* `0x07FE`/`0x07FF` for `0x55`/`0xAA`, and on a
match writes `0x5A` to `0x07FD` and jumps `0x0000`:

```
0xa69f  90 07 fe   mov  dptr,#0x07fe
0xa6a2  e0         movx a,@dptr
0xa6a3  b4 55 10   cjne a,#0x55,0xa6b6
0xa6a6  90 07 ff   mov  dptr,#0x07ff
0xa6a9  e0         movx a,@dptr
0xa6aa  b4 aa 09   cjne a,#0xaa,0xa6b6
0xa6ad  90 07 fd   mov  dptr,#0x07fd
0xa6b0  74 5a      mov  a,#0x5a
0xa6b2  f0         movx @dptr,a
0xa6b3  02 00 00   ljmp 0x0000
```

`common,0x0000` is `reset_vector_forwarder_to_0070` and its first instruction
is `0000 02 00 70 ljmp 0x0070`, so `A6B3 02 00 00` is the reset vector and
this is a static path from a triple-tester to it. It is reached through the
far-call stub at index 341 of the `0x1150` table
(`ec/annotations/task-call-table.csv:343` → `0x194E` → `ljmp 0xA69F` in
bank1), and `0x1150` is itself entered from the reset path
(`common,0x0007 02 11 50 ljmp 0x1150`).

**This does not establish that the path runs.** It is a path in the image. The
gate that would decide it is a live one, and it is §"The open question" below.

`0x1F07` belongs to the same constant family and is already a
`registers.yaml` row (`XDATA_1F07`, `present-untested`): `init_1f01_1f06_1f07`
at `0xD065` stores `0x5A` there, and `0xCCFC` calls `0xD065` at `0xCD45`, three
instructions before writing the triple. It is the nearest thing to a named
constant the block has, and what the constants mean to the vendor is not
decoded here.

## The listings stop short, which is why this is read from the image

The claim here is narrow and is about the **entry-anchored** listings: each of
the two routines whose *own* entry point truncates is cut off before the code
that carries the reading, and both truncations are visible as a *size* in
`ec/decompiled/listing-index.csv`:

* `bank0,D673` has `size` 77, covering `0xD673`-`0xD6BF`. The spin at `0xD6C7`
  is eight bytes past the end of the listing, so it is invisible in
  `D673.asm` and present in the image.
* `bank0,D6EA` has `size` 5, covering `0xD6EA`-`0xD6EE`. Its `ret` at `0xD6F3`
  is past that too, which is why `D6EA.c`'s own comment says the entry "has no
  RET, so this entry never returns on its own account" — a true reading of a
  truncated listing and a false one about the routine.

What this does **not** say is that a committed `.asm` is insufficient evidence
in general, because sibling committed listings do carry both of the bytes those
two entries stop short of: `bank0,D6C0` (`size` 9, covering `0xD6C0`-`0xD6C8`)
contains `D6C7 80 fe sjmp 0xd6c7` directly, and its `D6C0.c` says in words that
the entry "executes SJMP 0xD6C7, a jump to its own address that spins forever
with no RET"; `bank0,D6EF` (`size` 5, covering `0xD6EF`-`0xD6F3`) carries
`D6F0 90 1f 09` and `D6F3 22 ret`, the exact bytes quoted below. So the entry's
own listing is the thing that cannot be relied on, and the image is read for
what neither `D673.asm` nor `D6EA.asm` shows *and* for the three addresses
below that no listing covers at all. The disassembly remains load-bearing
either way, and for a reason the two truncations do not explain: `0x8624` and
`0xA69F` have no listing in any program, and `0xD856` — the third address whose
framing is asserted — is covered only by a listing anchored at `0xD757`, so
none of the three has a listing that *starts* where the framing is claimed.

## Corrections to the issue's own reading

Both of the issue's load-bearing statements about `0xD673` are wrong, and both
are left here rather than dropped, because a reader who has the issue open
needs to see which sentence to stop believing.

### 1. `0xD673` hangs too — it does not "carry on"

The issue reads the second writer as writing the triple "and carr[ying] on
into `R7=0xFA` / `lcall 0x0EA2` rather than hanging". It does carry on, and it
also hangs. The linear walk from `0xD6A8` is:

```
0xd6a8  90 08 eb   mov  dptr,#0x08eb
0xd6ab  e0         movx a,@dptr
0xd6ac  54 fb      anl  a,#0xfb
0xd6ae  f0         movx @dptr,a
0xd6af  90 10 63   mov  dptr,#0x1063
0xd6b2  74 18      mov  a,#0x18
0xd6b4  f0         movx @dptr,a
0xd6b5  90 1f 01   mov  dptr,#0x1f01
0xd6b8  74 20      mov  a,#0x20
0xd6ba  f0         movx @dptr,a
0xd6bb  90 1f 06   mov  dptr,#0x1f06
0xd6be  74 01      mov  a,#0x01
0xd6c0  f0         movx @dptr,a
0xd6c1  90 1f 07   mov  dptr,#0x1f07
0xd6c4  74 5a      mov  a,#0x5a
0xd6c6  f0         movx @dptr,a
0xd6c7  80 fe      sjmp 0xd6c7
```

That is the same `0x08EB` bit 2 clear `0xCCFC` performs at `0xCD3C`, the same
`0x18` to `0x1063` it writes at `0xCD42`, and the `0xD065` sequence inlined —
then it falls into `D6C7 80 fe`, a spin to itself. The committed
`ec/decompiled/bank0/D673.c` agrees in its own words: it ends `do { } while(
true );`.

**Both** writers write the triple and then spin. That strengthens the witness
reading rather than weakening it, and it is the reason the issue's "one of the
writers is immediately followed by a permanent hang" is *under*-stated rather
than wrong. `disasm8051.py --converge` reads 24 of 24 preceding anchors
decoding onto `0xD6C7` and onto `0xD6C9`, with 0 stepping over, so the framing
is evidence rather than an artifact of the anchor I chose.

### 2. `0xD673`'s `0x03` goes to `0x1F09`, not `0x1F06`

The issue describes `bank0/D6EA.asm` as re-pointing DPTR at `0x1F06`, "where
`0x03` then goes". The routine stores A, clears A, stores that zero to
`0x1F06`, re-points DPTR at **`0x1F09`**, and returns — so the `0x03` at
`0xD697` lands at `0x1F09`:

```
0xd6ea  f0         movx @dptr,a
0xd6eb  e4         clr  a
0xd6ec  90 1f 06   mov  dptr,#0x1f06
0xd6ef  f0         movx @dptr,a
0xd6f0  90 1f 09   mov  dptr,#0x1f09
0xd6f3  22         ret
0xd697  74 03      mov  a,#0x03
0xd699  f0         movx @dptr,a
```

This does not change the reading of the triple — `0x07FD` is still written
`0x5A` through the call, and that is the byte `0x94FA` branches on — but the
address is wrong in a sentence a reader would otherwise use to find the byte.

### 3. `main-ec-086` attributes the cluster to two addresses that write neither byte

`ec/annotations/xdata-clusters.csv:87` (`main-ec-086`, over exactly
`0x07FD 0x07FE 0x07FF`) and `ec/annotations/xdata-registers.csv:735-737` tag
`bank0:0xD5D4` and `bank0:0xD74F` as `[writer]`. **Neither writes the triple.**
`0xD5D4` writes `0x33` to `0x1501` and `0xD74F` writes `0x33` to `0x1511`; they
are in the cluster through the functions around them, not through the bytes.
The real sites at those addresses' neighbours are `0xD683` and `0xCD48`, which
the `90 07 fe` / `90 07 ff` scans place directly.

This is recorded here rather than fixed in place. `xdata-registers.csv` and
`xdata-clusters.csv` are generated by `ec/tools/xdata_register_map.py`, and
correcting the tags means regenerating two large shared CSVs under a gate that
recounts them — its own change, and a merge-conflict surface this write-up
does not need to open.

## What the bytes establish, and what they do not

**Established, from the committed image:**

- Two routines write `0x55` to `0x07FE`, `0xAA` to `0x07FF` and `0x5A` to
  `0x07FD`; **both** then spin (`CD5A 80 fe`, `D6C7 80 fe`).
- Two further routines write `0x55`/`0xAA` with `0x07FD = 0x00`: bank0
  `0xD856`, which sits inside the exported `0xD757`, and bank1 `0x8624`, which
  is in no exported listing.
- `0x94FA` tests the pair, clears `0x07FE` and `0x07FF`, and branches on
  `0x07FD` between `ljmp 0x95B7` and a three-byte clear of `0x0045`, `0x07FD`
  and `0x1F07`.
- `0xA69F` tests the same pair, writes `0x5A` to `0x07FD`, and jumps
  `0x0000` — the reset vector, which `common,0x0000` forwards to `0x0070`,
  whose `0x1594` trampoline runs the `0xD96C` clear that steps over exactly
  these three bytes.
- The boot clear at `0xD96C` steps over `0x07FD`-`0x07FF` because the
  `setb c` at `0xD982` makes its second bound read `0x0800` rather than the
  `0x07FF` its own immediates spell out.

**Not established, and deliberately left open:**

- That the breadcrumb is read on the **next** boot. `0xA69F` reaches the reset
  vector statically; nothing here shows a boot reading it.
- That `0x08EB` bit 2 is the condition that produces the triple in practice.
  `0xCCFC` gates on it, which is a code path, not a frequency.
- That the linker excluded the three bytes *for* this reason. The clear is a
  range clear with a carry bug-shaped bound; a step-over is a fact about which
  bytes it writes, not a stated intent.
- That any of the five entries runs on real hardware.

`0xD673` has no inbound `bank-call-targets.csv` row and no `lcall`/`ljmp`
operand naming it anywhere in the image. Per this repository's rule that is
**"not found by this method"** and never "unreachable" — an indirect or
computed transfer would be invisible to both searches, and `docs/findings.md`
§4c is the standing retraction of what a static zero is worth.

**No `status:` is upgraded to a behavioural value, and the three new
`registers.yaml` rows are `present-untested`.** A range clear that steps over
a byte is not evidence the EC reads it, and a write whose readback matches is
not evidence the EC acts on it. Both are §4c, and `present-untested`'s own
gloss — "static-scan finds real references, not yet exercised live" — is
exactly what seven EC-side sites and no live run amount to.

## The open question, and what would settle it

Whether the triple survives a warm reset is the question this write-up cannot
close, and only hardware settles it. The static work leaves it open
deliberately.

`0xA6B3` jumps the reset vector, which makes this a cheap experiment for
someone at the machine: write a non-`0x55`/`0xAA` value to `0x07FD`-`0x07FF`,
trigger a warm reset, and read the three bytes back before anything else
touches XDATA. **This write-up records a procedure, not a result.** No live
run happened, no register was read back, and the staging issue a live run
needs is a separate piece of work — per this repository's rule that a live
test is never planned into an agent branch and never claimed without
hardware behind it.

Three things a runner should know before starting, all read off the image
above: the boot clear at `0xD96C` runs on the reset path and steps over these
three bytes, so a surviving value is evidence the clear is what spares them and
not evidence the reset did not happen; `0x94FA` clears `0x07FE` and `0x07FF` on
a matching read, so a read that lands after the consumer runs will see zeros
whatever the reset did; and `0xA69F` writes `0x5A` to `0x07FD` before jumping,
so a post-reset `0x5A` in that byte is `0xA69F` having run, not the original
value surviving.

## The unexported entries, and why none is exported here

Three addresses this write-up quotes are not covered by any listing in
`ec/decompiled/`: bank0 `0xD96C` (the boot clear), bank1 `0x8624` and bank1
`0xA69F`. Adding listings for them is deferred rather than attempted.
`verify_reassembly.py --check` fails the listing/report asymmetry in both
directions, and a runner's `sdas8051` rewrites all 2,707 `assembler` strings
and moves 52 outcomes, so the export wants the nix-pinned toolchain. #559
deferred it for the same reason and carried a row-by-row list; that list is the
right precedent and the disassembly here is quoted from `disasm8051.py` against
the committed image for the same reason.

`0xD856` and `0xAC02` need no export of their own and are not in that set:
`0xD856` falls inside the exported `0xD757`, and `0xAC02` is bank1's second
instruction inside the exported `0xABFF` (`call_a1f6_94fa_a3f7_aa39`), whose
listing shows `AC02 12 94 fa lcall 0x94fa` directly. `0xAC02` is the address
`bank-call-targets.csv:4682` records as the only inbound caller of `0x94FA`.

`0xD856`, `0x8624` and `0xA69F` read 24 of 24 on `--converge`, 0 stepping
over, so the framing at each is evidence about instruction boundaries rather
than an artifact of the anchor.

`ec/annotations/ghidra-functions.csv` gains no rows from this issue — the
one row this diff edits, `0xCCFC`, is a comment edit naming the three new
registers. The other two census CSVs *are* regenerated. `gen_xdata_symbols.py`
carries the three new `registers.yaml` names into `ec/ghidra/xdata-symbols.csv`
as `XDATA_07FD`/`XDATA_07FE`/`XDATA_07FF`, and `xdata_register_map.py`, which
reads that table for its `name` column, then puts them in the `0x07FD`/
`0x07FE`/`0x07FF` rows of `xdata-registers.csv` and the three addresses in the
`main-ec-086` and `pd-002` rows' `named_addrs` of `xdata-clusters.csv`. The
two mis-attributed `[writer]` tags are deliberately left as they are, for the
reason given in correction 3 above. The two sites with no containing function
have no exported function to annotate, and seeding one is the export above.
