# All 18 paged-trampoline hits, read one by one (issue #54)

[`ec/annotations/bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) §7
reports 18 sites in `bank-paged-call-targets.csv` whose `ajmp`/`acall` target
lands on a BL51 trampoline entry, read **two** of them by hand, and stopped
short of the other sixteen. This file reads all 18. Every row has a verdict and
a transcript, and §7 carries the correction.

**The settled statement: all 18 are the operand byte of an instruction that
starts one or two bytes earlier.** Not two of them — all eighteen, and not on
the strength of an anchor score. For every one, the byte at the site is an
operand byte of a named instruction that 23 or 24 of the 24 preceding anchors
decode onto, and 15 of the 18 have a committed listing in
`ec/decompiled/common/` covering that instruction. No site is a genuine paged
call; none is misframed data; none is `unresolved`. The verdicts and the bytes
are in [the table](#the-18-verdicts), and
[`ec/tools/test_paged_trampoline_framing.py`](../../ec/tools/test_paged_trampoline_framing.py)
holds all of them to the image.

Nothing else moves. No register `status:`, no row added to or removed from
`bank-paged-call-targets.csv`, no function entry seeded, no Ghidra rebuild, no
edit to `ghidra-functions.csv` — its `common,0x15B8` row already records the
0x15BA half of this verdict ("the `0x81` low byte of that mov dptr immediate
and is a scan phantom rather than a paged branch"), that claim stands, and no
row is extended to speak for the other seventeen. No hardware and no Windows:
nothing here needs either, so nothing is deferred to a human at the machine.

## Why framing is the only open question

A paged `ajmp`/`acall` can only ever reach inside its own 2 KiB page, and the
trampoline block `0x1150`-`0x1ABC` is in the common area, so **a common-area
caller can reach it and a bank never can.** That is a statement about opcode
semantics and the region table, not about this image: it makes all 18
*geometrically possible*, so it cannot by itself tell a real one from a
misframed one. The census reports a row when a paged-shaped byte computes a
target inside that block, and a paged-shaped byte occurs wherever a 2-byte
opcode's own first byte lands — which is to say, inside other instructions'
immediates. Framing is the whole question, and it is settled by reading the
byte before.

## The method

- The census predicate is `calls_trampoline` non-empty, read with
  `csv.DictReader`. Two traps in that column, both worth stating because either
  one produces a confidently wrong 18. **It holds the bank number the
  trampoline selects** (`0`/`1`), not a boolean — 17 rows say `0` and one
  (`0x15E3`) says `1`, so "17 are truthy" would be a wrong reading of a right
  one. And **the file is CRLF** (3482 `\r` for 3482 lines), which `csv` does not
  strip from a final field: `r['calls_trampoline']` is `'1\n'`, and it is
  `.strip()` on the parsed value that makes "non-empty" mean what it says.
- The byte oracle is the **committed listing** `ec/decompiled/common/<ADDR>.asm`,
  not the `r2` transcript. A listing carries a SHA-256 pin of the source image
  in its header, and [`bank1-e582-entry-framing.md`](bank1-e582-entry-framing.md)
  sets the house order: a listing that opens at its own first instruction with
  the bytes in question is a stronger claim than a transcript alone.
- Each `r2` seek lands on a **known instruction boundary at or before** the
  site, never on the site itself, which would reproduce the framing under test.
  The one deliberate exception is
  [the `0x15E3` section](#the-one-site-where-the-phantom-is-also-a-real-opcode),
  where the claim *is* about what the site decodes to; the real framing is shown
  beside it from `0x15E2` and from the committed listing.
- Frame scores come from `disasm8051.converges_from()` on the bank-0 image, at
  the *owning* address rather than the site's.

**One place where the obvious claim is wrong, and it is worth stating here
rather than in a footnote.** It is tempting to say every site has a committed
listing over its owning instruction. Fifteen do. Three — `0x1656`, `0x16FE` and
`0x1F8E` — sit in the gaps between listings, and for those the evidence is the
image bytes, `disasm8051.py`'s decode of them, and the anchor score alone. The
next subsection says what stands in for the missing listing in each case.

## The 18 verdicts

One row per site, read from the census by predicate. `owning instruction` is
the instruction the site's byte belongs to — it starts one or two bytes
earlier, and its bytes are given so the claim is checkable rather than
described. Seventeen sites are its last byte; `0x15E3` is the first of its two
immediate bytes, and [that site has its own note](#the-one-site-where-the-phantom-is-also-a-real-opcode)
below. The verdict vocabulary is the issue's three plus `unresolved`, which
[`docs/findings.md`](../findings.md) §4c requires to be available and which is
*not* a synonym for phantom.

| site | opcode | target | owning instruction | verdict |
|---|---|---|---|---|
| `0x01110` | `acall` | `0x14C2` | `0x0110F` `c2 91` `clr 0x91` | misframed-operand |
| `0x01124` | `acall` | `0x14C2` | `0x01123` `c2 91` `clr 0x91` | misframed-operand |
| `0x01138` | `acall` | `0x14C2` | `0x01137` `d2 91` `setb p1.1` | misframed-operand |
| `0x0114C` | `acall` | `0x14C2` | `0x0114B` `d2 91` `setb p1.1` | misframed-operand |
| `0x012C0` | `ajmp` | `0x1402` | `0x012BE` `90 bf 81` `mov dptr,#0xbf81` | misframed-operand |
| `0x01320` | `acall` | `0x1402` | `0x0131E` `90 bf 91` `mov dptr,#0xbf91` | misframed-operand |
| `0x015BA` | `ajmp` | `0x1402` | `0x015B8` `90 c8 81` `mov dptr,#0xc881` | misframed-operand |
| `0x015E3` | `ajmp` | `0x163C` | `0x015E2` `90 c1 3c` `mov dptr,#0xc13c` | misframed-operand |
| `0x01638` | `acall` | `0x1402` | `0x01636` `90 d9 91` `mov dptr,#0xd991` | misframed-operand |
| `0x01656` | `ajmp` | `0x1402` | `0x01654` `90 f3 81` `mov dptr,#0xf381` | misframed-operand |
| `0x016FE` | `ajmp` | `0x1702` | `0x016FC` `90 c7 e1` `mov dptr,#0xc7e1` | misframed-operand |
| `0x01AF4` | `ajmp` | `0x1870` | `0x01AF3` `64 01` `xrl a,#0x01` | misframed-operand |
| `0x01B5F` | `ajmp` | `0x1990` | `0x01B5D` `30 e0 21` `jnb acc.0,0x1b81` | misframed-operand |
| `0x01E62` | `ajmp` | `0x1822` | `0x01E61` `7f 01` `mov r7,#0x01` | misframed-operand |
| `0x01E8B` | `ajmp` | `0x1870` | `0x01E8A` `64 01` `xrl a,#0x01` | misframed-operand |
| `0x01F14` | `ajmp` | `0x1870` | `0x01F13` `64 01` `xrl a,#0x01` | misframed-operand |
| `0x01F1A` | `ajmp` | `0x1870` | `0x01F19` `64 01` `xrl a,#0x01` | misframed-operand |
| `0x01F8E` | `ajmp` | `0x1870` | `0x01F8D` `64 01` `xrl a,#0x01` | misframed-operand |

The four inside the stubs are at stub base + `0x10`, seven are inside the
trampoline block itself, and seven are outside both — the last group is where
the work was, and it is read [last](#c-seven-outside-both-blocks).

## A: the four stub sites, at base + `0x10`

`find_banks.find_stubs()` puts the four bank-switch stubs at `0x1100`, `0x1114`,
`0x1128` and `0x113C`, 20 bytes each, and the four sites are at `+0x10` in each.
All four are `0x91` — an `acall` opcode, targeting `0x14C2` in all four cases,
which is why §7 could pair them.

```console
$ python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1100; pd 8' /tmp/bank0.bin
            0x00001100      c008           push 0x08
            0x00001102      7411           mov a, #0x11
            0x00001104      c0e0           push acc
            0x00001106      c082           push dpl
            0x00001108      c083           push dph
            0x0000110a      75080a         mov 0x08, #0x0a
            0x0000110d      c290           clr p1.0
            0x0000110f      c291           clr p1.1
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1114; pd 8' /tmp/bank0.bin
            0x00001114      c008           push 0x08
            0x00001116      7411           mov a, #0x11
            0x00001118      c0e0           push acc
            0x0000111a      c082           push dpl
            0x0000111c      c083           push dph
            0x0000111e      75081e         mov 0x08, #0x1e
            0x00001121      d290           setb p1.0
            0x00001123      c291           clr p1.1
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1128; pd 8' /tmp/bank0.bin
            0x00001128      c008           push 0x08
            0x0000112a      7411           mov a, #0x11
            0x0000112c      c0e0           push acc
            0x0000112e      c082           push dpl
            0x00001130      c083           push dph
            0x00001132      750832         mov 0x08, #0x32
            0x00001135      c290           clr p1.0
            0x00001137      d291           setb p1.1
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x113c; pd 8' /tmp/bank0.bin
            0x0000113c      c008           push 0x08
            0x0000113e      7411           mov a, #0x11
            0x00001140      c0e0           push acc
            0x00001142      c082           push dpl
            0x00001144      c083           push dph
            0x00001146      750846         mov 0x08, #0x46
            0x00001149      d290           setb p1.0
            0x0000114b      d291           setb p1.1
```

The `0x91` at `0x1110`/`0x1124`/`0x1138`/`0x114C` is the **bit-address operand**
of the stub's own `clr p1.1` or `setb p1.1` — the bank-window port write that
selects the bank. `r2` prints `p1.1`; `disasm8051.mnemonic` prints the same bit
as `0x91` for `clr` and `p1.1` for `setb`, which is the tool's own bit-naming
and not a disagreement.

**These four are anchored twice over, which is why they need no argument from
me.** `find_stubs()` does not assume where a stub is: it scans for
`STUB_PROLOGUE == c0 08 74` at a 20-byte stride, and it reads the bank bits out
of the very `clr`/`setb` instructions these sites are the operands of —
`bits = [1 if d[a + 13 + 2*k] == 0xD2 else 0 for k in range(3)]`
(`ec/tools/find_banks.py:43`). **What that corroborates is the owner's opcode
byte, and nothing more.** For the `0x1128` stub the three reads land on `0x1135`,
`0x1137` and `0x1139` — the `c2`/`d2` opcode bytes of the stub's three port
writes. The site is `a + 0x10 = 0x1138`, an offset that expression never
touches: clobbering `0x1138` on its own leaves `find_stubs()` returning
`(0x1128, 2)` unchanged, and only clobbering the owner at `0x1137` moves the
bank to 0. So the stub finder confirms that `0x1137` is a `setb`, and is silent
on whether `0x1138` is that instruction's `0x91` operand or a `0x91` opcode of
its own — which is the question this reading is about. **The four therefore
rest on the committed listing each one has** (`110A.asm`, `1114.asm`,
`1128.asm`, `113C.asm`) **and the 23-of-24 anchor score**, not on the stub
finder. The four stubs come out `(0x1100, bank 0)`, `(0x1114, bank 1)`,
`(0x1128, bank 2)`, `(0x113C, bank 3)`, which is the arithmetic §2 of the audit
already rests on; that is the stub table's own claim, and it does not depend on
how these 18 sites are framed.

The anchor score is 23 of 24 rather than 24 on all four, and the one exception
is worth knowing because it is the misframing seen from the other side: the walk
that steps over `0x110F` starts at `0x110E`, reads the `0x91` there as an
`acall`, and lands on `0x1110` — the site. Twenty-three anchors agree on the
`clr 0x91`; the twenty-fourth is the phantoms themselves, in agreement with
each other.

```console
$ python3 ec/tools/disasm8051.py --converge --at 0x110F /tmp/bank0.bin
0x0110F: 23 of 24 preceding anchors decode onto it, 1 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1123 /tmp/bank0.bin
0x01123: 23 of 24 preceding anchors decode onto it, 1 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1137 /tmp/bank0.bin
0x01137: 23 of 24 preceding anchors decode onto it, 1 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x114B /tmp/bank0.bin
0x0114B: 23 of 24 preceding anchors decode onto it, 1 step over it
```

## B: seven inside the trampoline block

Six of the seven sit inside a committed listing, and the seventh (`0x16FE`) does
not. All seven are the same shape: the trampoline block is a dense table of
six-byte entries, `90 xx yy 02 11 00` (`mov dptr,#imm16 ; ljmp 0x1100`) or the
`… 11 14` bank-1 variant, so the two immediate bytes at `+2`/`+3` of every entry
are exactly the bytes a byte scan will read as `ajmp`/`acall` opcodes.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x12be; pd 3' /tmp/bank0.bin
        ╎   0x000012be      90bf81         mov dptr, #0xbf81
        └─< 0x000012c1      021100         ljmp 0x1100
            0x000012c4      90bf82         mov dptr, #0xbf82
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x131e; pd 3' /tmp/bank0.bin
        ╎   0x0000131e      90bf91         mov dptr, #0xbf91
        └─< 0x00001321      021100         ljmp 0x1100
            0x00001324      90bf92         mov dptr, #0xbf92
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x15b8; pd 3' /tmp/bank0.bin
        ╎   0x000015b8      90c881         mov dptr, #0xc881
        └─< 0x000015bb      021100         ljmp 0x1100
            0x000015be      90c927         mov dptr, #0xc927
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x15e2; pd 3' /tmp/bank0.bin
        ╎   0x000015e2      90c13c         mov dptr, #0xc13c
        └─< 0x000015e5      021100         ljmp 0x1100
            0x000015e8      90c134         mov dptr, #0xc134
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1636; pd 3' /tmp/bank0.bin
        ╎   0x00001636      90d991         mov dptr, #0xd991
        └─< 0x00001639      021100         ljmp 0x1100
            0x0000163c      9088f0         mov dptr, #0x88f0
```

So `0x12C0` is the `0x81` low byte, `0x1320` the `0x91` low byte and `0x1638` the
`0x91` low byte of a `mov dptr` immediate — all three the **low** immediate at
`+2` of the same three-byte `90 hi lo`, which is where the verdict table's
`owning instruction` column puts them. `0x15E3` is the one exception in shape:
it is the `0xC1` **high** byte of `mov dptr,#0xc13c`, a byte earlier in the
instruction at `+1`, which is why it is also the one row whose
`calls_trampoline` says `1` — a `0xC1` opcode contributes the middle of a page,
and `0x163C` is the entry fifteen entries after the one at `0x15E2`
(`0x163C - 0x15E2 = 0x5A = 15 x 6`, and `0x163C` is `90 88 f0 02 11 14`, a
bank-1 `ljmp 0x1114`).
`0x15BA` is the case §7 already read, and `ghidra-functions.csv`'s
`common,0x15B8` row says the same thing about it.

Two of the six remaining transcripts have no listing, and the three gap sites
(`0x1654`, `0x16FC`, `0x1F8D`) are read with the same instrument:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1654; pd 3' /tmp/bank0.bin
        ╎   0x00001654      90f381         mov dptr, #0xf381
        └─< 0x00001657      021114         ljmp 0x1114
            0x0000165a      90f35e         mov dptr, #0xf35e
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x16fc; pd 3' /tmp/bank0.bin
        ╎   0x000016fc      90c7e1         mov dptr, #0xc7e1
        └─< 0x000016ff      021100         ljmp 0x1100
            0x00001702      90c7f5         mov dptr, #0xc7f5
```

`0x1654` and `0x16FC` have no committed listing of their own, so what stands in
for one is (a) the six-byte stride the committed listings on both sides of them
establish — `1636.asm` ends at `0x163B` and `16D2.asm` opens with
`90 c7 8f 02 11 00`, and the entries between are six bytes apart with the same
`90 … 02 11 00/14` shape — and (b) 24 of 24 anchors. The pair is worth reading
together with [the artifact below](#the-tree-already-carries-one-of-these),
which is the same misframing already committed to disk.

All seven score 24 of 24:

```console
$ python3 ec/tools/disasm8051.py --converge --at 0x12be /tmp/bank0.bin
0x012BE: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x131e /tmp/bank0.bin
0x0131E: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x15b8 /tmp/bank0.bin
0x015B8: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x15e2 /tmp/bank0.bin
0x015E2: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1636 /tmp/bank0.bin
0x01636: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1654 /tmp/bank0.bin
0x01654: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x16fc /tmp/bank0.bin
0x016FC: 24 of 24 preceding anchors decode onto it, 0 step over it
```

## The one site where the phantom is also a real opcode

`0x15E3` is the single site of the 18 that is not merely *displaced*: decoded
at its own offset, the byte there completes a valid instruction too.

The 2-byte paged family is `0x01/0x11/0x21/…/0xF1`, keyed on the low five bits
being `0x01` or `0x11`. Fifteen of those sixteen values have exactly one
meaning in the 8051 table — the paged form — and the sixteenth does not.
`0xC1` is `CLR bit`, which is why a byte of that value at an instruction
boundary is ambiguous in a way no other member of the family is. Checked
against the committed decoder rather than the manual:

```console
$ python3 -c "
import sys; sys.path.insert(0,'ec/tools'); import disasm8051
d=bytearray(b'\x00'*0x200)
for i,op in enumerate((0x01,0x11,0x21,0x31,0x41,0x51,0x61,0x71,
                       0x81,0x91,0xA1,0xB1,0xC1,0xD1,0xE1,0xF1)):
    d[i*4]=op; d[i*4+1]=0x34
    print('%02X -> %s' % (op, ' '.join(disasm8051.mnemonic(bytes(d),i*4,i*4).split())))"
01 -> ajmp 0x0034
11 -> acall 0x0034
21 -> ajmp 0x0134
31 -> acall 0x0134
41 -> ajmp 0x0234
51 -> acall 0x0234
61 -> ajmp 0x0334
71 -> acall 0x0334
81 -> ajmp 0x0434
91 -> acall 0x0434
A1 -> ajmp 0x0534
B1 -> acall 0x0534
C1 -> clr 0x26.4
D1 -> acall 0x0634
E1 -> ajmp 0x0734
F1 -> acall 0x0734
```

So at `0x15E3`, where the byte is `0xC1`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x15e3; pd 2' /tmp/bank0.bin
       ┌──< 0x000015e3      c13c           ajmp 0x163c
       │└─< 0x000015e5      021100         ljmp 0x1100
$ python3 ec/tools/disasm8051.py --at 0x15e2 -n 2 /tmp/bank0.bin
0x015e2  90c13c   mov  dptr,#0xc13c
0x015e5  021100   ljmp 0x1100
$ python3 ec/tools/disasm8051.py --at 0x15e3 -n 2 /tmp/bank0.bin
0x015e3  c13c     clr  0x27.4
0x015e5  021100   ljmp 0x1100
$ python3 ec/tools/disasm8051.py --converge --at 0x15e2 /tmp/bank0.bin
0x015E2: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x15e3 /tmp/bank0.bin
0x015E3: 0 of 24 preceding anchors decode onto it, 24 step over it
```

**The two committed disassemblers resolve the collision in opposite
directions, and both land on the same next instruction.** `r2` follows the
paged family, so it reads the `c1 3c` at `0x15E3` as `ajmp 0x163c` — which is
the census's reading, and is why the row exists at all. `disasm8051.py` takes
`0xC1` as `CLR bit` and reads the same two bytes as `clr 0x27.4`. Either way
the stream arrives at the `ljmp 0x1100` at `0x15E5`, which is also where the
`mov dptr,#0xc13c` reading from `0x15E2` arrives. That is the honest statement
of what is going on at this one site: it is not a byte that cannot be
decoded, it is a byte whose two decodes agree about everything downstream.

`0x15E2` wins on the anchors (24 of 24 against 0 of 24) and on the committed
`15E2.asm`, which opens at its own first instruction with `90 c1 3c` and whose
second line is the `ljmp 0x1100` all three readings share.

Three things follow, and only the first is a correction:

- **The census's row is still a phantom.** The `ajmp` at `0x15E3` is not a real
  transfer; its byte is the `0xC1` high immediate of the `mov dptr,#0xc13c` at
  `0x15E2`, and the 0-of-24 score is the evidence. Nothing changes in the
  verdict.
- **Its row is scored 0 of 24, like the other thirteen it shares that with.**
  That is worth saying because it cuts against the reading: the ambiguity is
  real, the byte really does decode two ways, and the scan's own frame column
  nonetheless gives this site the same 0/24 it gives the thirteen
  straightforward misframes — the two sites where the other reading is *most*
  tempting, `0x12BF` and `0x1637`, score 0 of 24 too. The score is the same
  because the framing is the same, not because the column noticed anything about
  `0xC1`.
- **"These bytes are not an instruction" would have been false here.** For the
  other seventeen the byte's only meaning is the paged form, so nothing at the
  site's own offset decodes to a real instruction; for this one something
  does. That is why the suite checks each site's own byte against the census's
  predicate rather than asserting a blanket rule, and why this site gets its own
  case rather than a line in a loop.
- **`disasm8051.py` already knows the shape.** Its comment above
  `TEXTBOOK_BIT_SITES` says this firmware "contains no instruction-start byte
  `0xC1` at all (measured over every committed listing)", and calls the gap a
  "latent hole rather than a live one". `0x15E3` does not reopen it: that
  comment is about *instruction-start* bytes, and 0x15E3 is not one. Worth
  recording that the two agree, because a future reader who found this site by
  scanning for `0xC1` would otherwise reasonably think the comment was stale.

## C: seven outside both blocks

These are the ones the issue meant, and they are the ones where "the
trampoline block's own bytes, misframed" is not available by construction.
Nothing here is near a stub or near a six-byte table, so each needed its own
argument. **Seven sites, three distinct owners, and every one resolves without
appeal to the trampoline block at all.**

Five of the seven are the byte `0x01` — an `ajmp` opcode, whose high three bits
are zero — and in all five it is the immediate of a `64 01` (`xrl a,#0x01`),
the test-and-toggle idiom this code uses for every flag byte. The other two are
a `0x01` immediate of a `7f 01` (`mov r7,#0x01`) and a `0x21` displacement.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1af3; pd 3' /tmp/bank0.bin
            0x00001af3      6401           xrl a, #0x01
        ┌─< 0x00001af5      705e           jnz 0x1b55
        │   0x00001af7      78bc           mov r0, #0xbc
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1b5d; pd 3' /tmp/bank0.bin
        ┌─< 0x00001b5d      30e021         jnb acc.0, 0x1b81
        │   0x00001b60      900a55         mov dptr, #0x0a55
        │   0x00001b63      e0             movx a, @dptr
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1e61; pd 3' /tmp/bank0.bin
            0x00001e61      7f01           mov r7, #0x01
            0x00001e63      22             ret
            0x00001e64      ef             mov a, r7
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1e8a; pd 3' /tmp/bank0.bin
            0x00001e8a      6401           xrl a, #0x01
        ┌─< 0x00001e8c      7026           jnz 0x1eb4
       ┌──< 0x00001e8e      30480a         jnb 0x29.0, 0x1e9b
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1f13; pd 3' /tmp/bank0.bin
            0x00001f13      6401           xrl a, #0x01
        ┌─< 0x00001f15      706d           jnz 0x1f84
        │   0x00001f17      a3             inc dptr
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1f19; pd 3' /tmp/bank0.bin
            0x00001f19      6401           xrl a, #0x01
        ┌─< 0x00001f1b      7032           jnz 0x1f4f
       ┌──< 0x00001f1d      30480f         jnb 0x29.0, 0x1f2f
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1f8d; pd 3' /tmp/bank0.bin
            0x00001f8d      6401           xrl a, #0x01
        ┌─< 0x00001f8f      7034           jnz 0x1fc5
        │   0x00001f91      7bff           mov r3, #0xff
```

Six of those seven have a committed listing over the owner — `1AC2.asm` for
`0x1AF3` and `0x1B5D`, `1E30.asm` for `0x1E61`, `1E7F.asm` for `0x1E8A`,
`0x1F13` and `0x1F19` — so the `64 01` idiom is a line in a file committed
independently of this census at four addresses, at a site nobody had flagged.
The seventh, `0x1F8D`, has no listing: `1E7F.asm` ends at `0x1F84` and the next
common-area listing is further on. What stands in for one is that the identical
`64 01` is attested at those four addresses that do have one, and the score:

```console
$ python3 ec/tools/disasm8051.py --converge --at 0x1af3 /tmp/bank0.bin
0x01AF3: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1b5d /tmp/bank0.bin
0x01B5D: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1e61 /tmp/bank0.bin
0x01E61: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1e8a /tmp/bank0.bin
0x01E8A: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1f13 /tmp/bank0.bin
0x01F13: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1f19 /tmp/bank0.bin
0x01F19: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x1f8d /tmp/bank0.bin
0x01F8D: 24 of 24 preceding anchors decode onto it, 0 step over it
```

**`0x1B5F` is the one to look at twice**, because its owner is three bytes
rather than two. The census reads the `0x21` at `0x1B5F` as an `ajmp`; it is
the **displacement** of the `30 e0 21` (`jnb acc.0, 0x1b81`) at `0x1B5D`, two
bytes earlier, and the branch target checks out from the image —
`0x1B5D + 3 + 0x21 = 0x1B81`, which is where `1AC2.asm` says the jump goes. It
is the same class as the `bank0,0xAA19` displacement byte §9 of the audit
already retired, and unlike the other seventeen the site is *not* an immediate:
the argument is the displacement's landing address rather than an operand's
value.

**No site in this group is left `unresolved`, and the reason is that the
criterion for `unresolved` never arose.** A site earns `unresolved` when the
bytes before it sync onto nothing, so that no alternative framing can be named
— `converges_from` scores 0 onto against 24 over, and the preceding bytes may
be data no linear walk can align. Every one of the seven has a named owner with
24 of 24, so each is a displacement against a positive alternative rather than
an absence. `docs/findings.md` §4c's rule is respected precisely because it
never had to be invoked, not because it was overridden.

## The negative controls: the same bytes, framed the other way

Every verdict above is "the byte at the site belongs to the instruction one or
two bytes earlier". That is a claim about framing, so it has to be a *choice*,
and the choice has to be visible. At three of the sites the byte immediately
before the owner's site is itself a perfectly good instruction head, so the
same bytes frame two ways and only one of them is an instruction boundary:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x12be; pd 3' /tmp/bank0.bin
        ╎   0x000012be      90bf81         mov dptr, #0xbf81
        └─< 0x000012c1      021100         ljmp 0x1100
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x12bf; pd 2' /tmp/bank0.bin
            0x000012bf      bf8102         cjne r7, #0x81, 0x12c4
            0x000012c2      1100           acall 0x1000
$ python3 ec/tools/disasm8051.py --converge --at 0x12be /tmp/bank0.bin
0x012BE: 24 of 24 preceding anchors decode onto it, 0 step over it
$ python3 ec/tools/disasm8051.py --converge --at 0x12bf /tmp/bank0.bin
0x012BF: 0 of 24 preceding anchors decode onto it, 24 step over it
```

The same four bytes `90 bf 81 02` read as `mov dptr,#0xbf81 ; ljmp 0x1100` from
`0x12BE` or as `cjne r7,#0x81,0x12C4 ; acall 0x1000` from `0x12BF`. **Both
framings contain a paged call**, which is the point: "these bytes look like a
paged transfer" decides nothing, and a suite that answered `phantom` for all 18
without comparing the two framings would pass on a claim that cannot tell them
apart. `0x131F` (`cjne r7,#0x91,0x1324`; 0 of 24) and `0x1637`
(`djnz r1,0x15ca`; 0 of 24) are the same pair, and all three decoys are
asserted in the suite.

The same test applied in reverse: **the owning instruction is never itself a
paged instruction.** `d[owner] & 0x1F` is outside `{0x01, 0x11}` for all 18
owners, so the reading is not the circular one where a phantom is explained by
a neighbouring phantom. Checked for all 18 rather than the three worked above,
so the property is not a property of the examples chosen.

## The tree already carries one of these

While reading `0x16FC` the listings turned up `ec/decompiled/common/1706.asm`,
whose first instruction is `acall 0x1000` at `0x1706`. That address is **one
byte into an `ljmp` operand**, and it is a committed function boundary in the
decompiled tree:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1702; pd 3' /tmp/bank0.bin
        ╎   0x00001702      90c7f5         mov dptr, #0xc7f5
        └─< 0x00001705      021100         ljmp 0x1100
            0x00001708      90c717         mov dptr, #0xc717
$ sed -n '6,9p' ec/decompiled/common/1706.asm
; function boundary from a call-target byte scan; that census is an upper bound (ec/annotations/bank-call-audit.md §1),
; so this boundary is a hypothesis and the instructions below may not be the whole function.

1706     11 00 -  acall    0x1000
```

`0x1706` is one byte into the `ljmp 0x1100` at `0x1705`, and the listing's own
header says where its boundary came from: a call-target byte scan, which is
this repository's own over-counting census. There is **no** `ghidra-functions.csv`
row for it — it is a boundary the exporter derived and named
`FUN_CODE_1706`, which is why the pair is committed evidence rather than an
annotation choice. `bank-paged-call-targets.csv:501` carries it as an ordinary
paged row (`acall` → `0x1000`, `target_class=other`, scores 2/22) because
0x1000 is outside the trampoline block, so it is not one of the 18.

The *same misframing* is therefore already materialised in the tree, one
listing deep, at a site nobody had flagged: a byte-scan-derived function
boundary sitting one byte into an `ljmp`, exported as a listing whose first
line is an `acall` the image does not contain at that alignment. It is named in
[What this opens](#what-this-opens) as a follow-up rather than fixed here,
because retiring a function entry needs `--mode rebuild-project` and this issue
is a reading.

## What the reading does and does not license

**It does license:** "all 18 are misframed operands of named instructions", for
this image, on the bytes in the table. That is a statement about framing, and it
is the statement §7 needed.

**It does not license, and these are not hedges:**

- **A claim about behaviour.** Nothing here says the EC executes any of this.
  No register `status:` moves; `registers.yaml` is untouched.
- **A validation of the scan.** 18 phantoms found is not 18 phantoms avoided.
  `audit_call_targets.py`'s 2-byte paged family still over-counts, and §7's
  "3481 by byte scan, 1667 anchored — 48%" is unchanged by anything here. The
  upper bound is still an upper bound.
- **That the containing functions are correctly bounded.** Every listing
  involved carries its own caveat — *"function boundary from a call-target byte
  scan; that census is an upper bound … so this boundary is a hypothesis"*. The
  reading says the byte at the site is inside an instruction; it does not
  certify where the function around it starts or ends, and the three gap sites
  (`0x1654`, `0x16FC`, `0x1F8D`) are outside any listing precisely because of
  that uncertainty.
- **That a 24/24 score proves framing on its own.** `converges_from`'s
  docstring says a site everybody syncs onto is not thereby real, and §2 and §8
  of the audit already carry that. The score here is corroboration for a
  reading made from the bytes, not the reading itself.
- **That `r2` agreeing is an independent method.** `r2 -a 8051` and
  `disasm8051.py` are two implementations of the same linear walk. The
  independent evidence is the committed listings, and 15 of 18 have one.

**The shape of the result is expected, which is a reason to check it rather
than a substitute for checking it.** A row appears only when a paged-shaped
byte computes a target inside `0x1150`-`0x1ABC`. In a table of six-byte
`mov dptr`/`ljmp` entries and a codebase that writes `xrl a,#0x01` on every
flag byte, most bytes that qualify are immediates. That is why 18 of 18 come out
the same way — and it is also why "they all look alike" is not evidence, which
is what the negative controls above are for.

## The corrections §7 now carries

Two, both in place with the superseded wording left standing, per `CLAUDE.md`.

1. **The count.** §7 said "the best of the 18 scores 1 of 24 anchors and 14
   score 0". Recounted from the committed CSV, the 18 split **(0, 24) × 14 and
   (1, 23) × 4**, and the four are `0x15BA`, `0x1656`, `0x16FE` and `0x1B5F`.
   The old sentence names one of four.
2. **The hedge.** §7 said "The other 16 were **not** read one by one, so 'these
   18 are phantoms' is not the claim". They have now been read, one by one, and
   the claim is 18 of 18 — on byte evidence, with the two the old hedge leaned
   on (`0x15BA` and `0x1110`) among them.

The more useful half of the first correction is *why* the score was never
load-bearing. `converges_from`'s own docstring says the pair is evidence about
framing and not proof of it; §2 and §8 carry the same limit; and the strongest
anchor score among the 18 — `0x15BA` at 1 of 24 — is one of the two §7 had
already read and already settled as a phantom. A 1-of-24 score bought nothing
here, which is exactly what the per-site reading replaces it with.

## The test that proves it

`ec/tools/test_paged_trampoline_framing.py` (new; picked up by
`bash tools/run-tests.sh`, which globs `test_*.py` per directory — no gate edit,
since `agent-gates.sh` is pipeline-copied and must not be edited). It reads the
census by predicate and the image from `ec/firmware/GMxMGxx_11.800`, and
**deliberately does not re-run `audit_call_targets.py`** to regenerate the
census, for the reason
[`test_bank1_e582_framing.py`](../../ec/tools/test_bank1_e582_framing.py) gives
in its own docstring: that asserts the tool against itself, and a regenerated
census would then be free to disagree with the image.

1. The predicate yields **exactly 18** rows, all `region=common`, all
   `in_region=yes`, all `calls_stub` empty, and `calls_trampoline` splitting
   **17 `0` / 1 `1`**. A test asserting "17 rows are truthy" would be wrong, and
   the suite asserts the parsed value rather than its truthiness.
2. Every row's `target` equals `disasm8051.paged_target()` recomputed from the
   committed image at that offset — a wrong `+2` or a wrong mask fails — and
   every target lands inside `0x1150`-`0x1ABC`, the block whose extent is the
   whole reason these 18 form a group.
3. Per site: the owning instruction's offset, raw bytes and mnemonic, its
   `OPCODE_LEN` spanning the site, its `converges_from` score, and the census's
   own opcode label checked against `paged_sites()`'s `op & 0x1F` predicate.
   "The `0x81` low byte of a `mov dptr,#0xc881`" is a byte assertion, not a
   sentence.
4. **The negative controls** — the three decoy framings at `0x12BF`, `0x131F`
   and `0x1637` asserted to decode as `cjne`/`djnz` *and* to score 0 of 24
   while their owners score 24, plus the assertion that the wrong framing of
   `0x12BE`'s bytes **also** contains a paged call, and the non-circularity
   check that no owner is itself a paged opcode. This is the part that stops a
   suite which returned `phantom` for all 18 without looking at the byte before
   from passing.
5. The fifteen covering listings are checked to cover, to carry the pinned
   bytes, and — for the five in the trampoline block — to open at the owning
   instruction as their own first one. **The three gaps are pinned as gaps**,
   because a write-up claiming eighteen would be overclaiming and this is the
   assertion that catches it.
6. The write-up's verdict table parses to **18 rows, one per census address, no
   extras, none missing, every verdict in the declared vocabulary** — which is
   what makes the issue's "done" condition checkable rather than asserted, and
   what keeps `unresolved` in the vocabulary where a later reader can reach it.

It is 28 cases, and it was mutation-checked rather than assumed non-vacuous:
flipping one verdict to `unresolved`, deleting a row, re-transcribing an owner
byte, re-transcribing a mnemonic and re-labelling a verdict each fail at the
case that names them, and the unmutated tree is green.

**The new suite is not wired into `agent-gates.sh`**, which is copied from
`ElDavoo/agent-pipeline` and is not editable from here; it runs under
`tools/run-tests.sh` only, the same position
`test_bank1_e582_framing.py` is in. `tools/test_readme_suite_table.py` covers
the inventory, so the suite is not silently absent from it.

## Re-deriving

From the repository root.

```sh
python3 ec/tools/make_bank_image.py ec/firmware/GMxMGxx_11.800 0 0x08000 /tmp/bank0.bin
python3 ec/tools/disasm8051.py --converge --at 0x12be /tmp/bank0.bin
python3 ec/tools/disasm8051.py --converge --at 0x12bf /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x12be; pd 3' /tmp/bank0.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=0 -q -c 's 0x1af3; pd 3' /tmp/bank0.bin
```

The 18 rows, and the listings they rest on:

```sh
python3 -c "import csv;[print(r) for r in csv.DictReader(open('ec/annotations/bank-paged-call-targets.csv')) if r['calls_trampoline'].strip()]"
head -8 ec/decompiled/common/15B8.asm
head -8 ec/decompiled/common/1E7F.asm
head -8 ec/decompiled/common/110A.asm
```

The census is not edited. It is `audit_call_targets.py --paged-csv` output and
`census_ff_fill.py` and `decode_index_table.py` both read it as an input, so a
verdict column added to it would be a merge hazard on a 3482-row generated file
and would be undone on the next run. The verdicts live in
[the table](#the-18-verdicts) and in the suite that parses it.

## What this opens

- **The `FUN_CODE_1706` function entry is one byte into an `ljmp`** and its
  listing's first instruction, `acall 0x1000`, is not in the image at that
  alignment. `ec/decompiled/common/1706.{asm,c}` go away, and the
  `bank-paged-call-targets.csv` row for `0x1706` with them once the boundary
  stops being a byte-scan artefact. There is no `ghidra-functions.csv` row to
  delete — the boundary is derived — so the change is in how the exporter
  chooses them, and **it needs `--mode rebuild-project`**. `CLAUDE.md` records
  why that is a separate change: two branches that both rebuild the 7 MB EC
  database cannot merge.
- **A defence in depth for the paged family.** Nothing in
  `audit_call_targets.py` looks one byte back, so every paged row in a
  six-byte `mov dptr` table or a `xrl a,#0x01` idiom is a row. The 18 here are
  the ones that happened to land inside the trampoline block; the family has
  3481 by byte scan. That is a tool change, not a reading, and it is out of
  scope here — but it is the question this reading opens, and it is worth
  naming that the fix is not "drop the row" but "record why".
- **Whether `0x1F8D`, `0x1654` and `0x16FC` get a listing of their own.** They
  are the three sites whose owner is attested only by the image and the anchor
  score. All three score 24 of 24 and all three sit inside a six-byte table
  whose neighbours have listings, so the entry is very likely right — but a
  function boundary for them would be a boundary chosen on the strength of this
  reading, which is the wrong order of operations. Retiring `0x1706` first
  would narrow how such boundaries get drawn.
