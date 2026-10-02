# PD stride families `0x17`, `0x67` and `0x04`: site-level analysis

[pd-index-geometry.md](pd-index-geometry.md) §7.5 lists these three constants as
strides nothing in this repository has looked at. [pd-base-strides.csv](pd-base-strides.csv)
carries their site and base counts in one aggregate row each and nothing else.
This takes the three apart at site level, over the whole PD image, and commits
the result as [pd-stride-family-sites.csv](pd-stride-family-sites.csv) beside
this file.

**They are not three parallel families.** `0x17` is a truncating construction
reached through a helper and already half-traced by
[pd-index-geometry.md](pd-index-geometry.md) §8; `0x67` and `0x04` are exact
16-bit products reached through a different helper, and §8's template census
does not cover either. The work here is the reconciliation between the two
censuses for `0x17` and the first site-level read of the other two.

**Nothing here was observed on hardware.** It is static analysis of committed
firmware: no EC, no laptop and no Windows host was reachable. No register was
read, written or read back, and no claim below depends on a runtime value.

## 1. Input, reproduction and the two checks

Input: `ec/firmware/GMxMGxx_11.800`, 262,144 bytes, SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`. The PD image
is the region at file `[0x20000,0x30000)`, `ITE8850-PD` at file `0x20040`, so
for every **instruction** address below, file offset = runtime address +
`0x20000`. XDATA operand addresses do not use that conversion: they are
addresses in the PD program's own data space.

Run from the repository root:

```sh
# 1. the per-family rollup, which prints every figure §2 and §3 quote
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --families

# 2. one site, with an anchored instruction listing
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 \
        --sites 0x8077 0x9C15 0xA399

# 3. the committed table, and the self-test that holds it to this document
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --csv \
        > /tmp/pd-sf.csv
cmp /tmp/pd-sf.csv ec/annotations/pd-stride-family-sites.csv
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --self-test
```

The census this file cross-checks rather than restates:

```sh
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
        --strides-csv all > /tmp/a.csv && cmp /tmp/a.csv ec/annotations/pd-base-strides.csv
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
        --accesses-csv all > /tmp/b.csv && cmp /tmp/b.csv ec/annotations/pd-index-accesses.csv
python3 ec/tools/pd_image_census.py --self-test
```

All five are green on this tree, and the three committed CSVs regenerate
byte-identically: this change reads them and writes none of them. The tool is
imported-from, not forked — `ec/tools/pd_index_geometry.py`, `ec/tools/
pd_image_census.py` and `ec/tools/disasm8051.py` are the only decoders, so a
wording fix in any of them moves this file's numbers too rather than leaving
them stale.

Independent decoding of the listings below used **radare2 5.5.0** on a
temporary flat PD image extracted from the committed input:

```sh
r2 -v
dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd-75.bin bs=65536 skip=2 count=1
r2 -a 8051 -e scr.color=0 -q -c \
  's 0x96fe; pd 7; s 0x971b; pd 8; s 0xacc3; pd 7; s 0x10bc; pd 7' /tmp/pd-75.bin
r2 -a 8051 -e scr.color=0 -q -c \
  's 0xcc58; pd 6; s 0xcc92; pd 6' /tmp/pd-75.bin
r2 -a 8051 -e scr.color=0 -q -c \
  's 0x2f0b; pd 6; s 0x9c15; pd 6; s 0x9c6d; pd 6' /tmp/pd-75.bin
r2 -a 8051 -e scr.color=0 -q -c \
  's 0xa395; pd 8; s 0x1041; pd 7; s 0x104d; pD 22; s 0x1064; pD 26' /tmp/pd-75.bin
```

The firmware, not r2's synthetic memory-hint comments, is the evidence. `pd`
counts instructions and `pD` counts bytes.

## 2. The framing rule, and what it does not prove

Two classifications, on separate columns because
[pd-index-geometry.md](pd-index-geometry.md) §8.3 is explicit that they have
separate denominators. Neither is a statement about execution.

- **`framing`** — whether a backward linear walk inside the 24-byte window
  lands exactly on the site's `MOV DPTR` byte. `supported-code-site` when at
  least one anchor converges, `instruction-framing-candidate` when none does.
  This is the measurement `converges_from()` returns and nothing more. A zero
  is evidence about instruction boundaries, **not** about data:
  `disasm8051.py`'s own docstring on that function says a site preceded by a
  dispatch table has no converging anchor and is not thereby misframed. §3.4
  shows what the two candidates here turn out to be, and the answer happens to
  be checkable from the bytes; that is a result, not a premise.
- **`in_pd_listing`** — whether `ec/decompiled/pd/*.asm` holds the site's
  address, with the holding function in `owning_function`, or
  `not found by this method` where none does. That last is a real answer and
  not a gap: the export covers a set of function bodies, not the whole 64 KiB,
  and `pd_image_census.owning_function()` returns that string for exactly this
  reason.

What neither classification establishes: that any of these sites executed, that
the arithmetic is the only way the pointer is built, or that the address
expression is complete. Every chain below stops somewhere named, and §5 lists
where.

## 3. The three families

The rollup, verbatim from `--families`:

```console
26 PD-image MOV DPTR site(s) carry 0x17, 0x67, 0x04 over the whole image

in-a-listing and anchored are separate questions: a committed pd listing holds the site, or a backward frame lands on it
0x17  17 site(s)  7 base(s)  12 in a listing  15 anchored  17 reach a construction  10 consumed
        low8-truncated  bases 0x0A13 0x0A15 0x0A27 0x0A29 0x0A2C 0x0A2D 0x0A35
        low8 and the full product agree below index 12 and diverge from it
0x67   7 site(s)  6 base(s)  1 in a listing  7 anchored  0 reach a construction  0 consumed
        full-product  bases 0x0661 0x0667 0x069A 0x069B 0x07A3 0x07C4
        unmodelled DPH addends R3 R5 R6 R7
0x04   2 site(s)  2 base(s)  0 in a listing  2 anchored  0 reach a construction  0 consumed
        full-product  bases 0x00C0 0x00C8
```

### 3.1 `0x17`: a truncating construction behind seven helpers

Every `0x17` site is a `MOV DPTR` anchor whose chain reaches a helper, and every
one of those helpers ends in the same byte run — `mul ab ; add a,#lo ; mov
dpl,a ; clr a ; addc a,#hi ; mov dph,a`. The `clr a` at `0xCC68` is the
load-bearing instruction: it discards B, the multiplication's high byte, so the
address is `base + low8(index * 0x17)` and **not** the product.

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x96fe; pd 7; s 0x971b; pd 8; s 0xacc3; pd 7' /tmp/pd-75.bin
            0x000096fe      e0             movx a, @dptr
            0x000096ff      75f017         mov b, #0x17
            0x00009702      a4             mul ab
            0x00009703      2427           add a, #0x27
            0x00009705      f582           mov dpl, a
            0x00009707      e4             clr a
            0x00009708      340a           addc a, #0x0a
            0x0000971b      f0             movx @dptr, a
            0x0000971c      ef             mov a, r7
            0x0000971d      75f017         mov b, #0x17
            0x00009720      a4             mul ab
            0x00009721      2415           add a, #0x15
            0x00009723      f582           mov dpl, a
            0x00009725      e4             clr a
            0x00009726      340a           addc a, #0x0a
            0x0000acc3      a4             mul ab
            0x0000acc4      2435           add a, #0x35
            0x0000acc6      f582           mov dpl, a
            0x0000acc8      e4             clr a
            0x0000acc9      340a           addc a, #0x0a
            0x0000accb      f583           mov dph, a
```

`clr a` clears the accumulator but **not** the carry, so the carry out of
`add a,#lo` survives into `addc a,#hi` and the address can leave the base's
page. That is §8.1's `low8` rule applied here, and it is why the base column
below is not a page number.

| site / file | `MOV DPTR` immediate | effective base | address expression | index | construction | stop | first consumer |
|---|---|---|---|---|---|---|---|
| `0x75CD` / `0x275CD` | `0x07D1` | `0x0A35` | `DPTR ← 0x0A35 + low8(A×0x17)` | `A` | `0xACC3` | `0x75D3` handoff to `0x1041` | not found by this method |
| `0x768E` / `0x2768E` | `0x07D1` | `0x0A35` | `DPTR ← 0x0A35 + low8(A×0x17)` | `A` | `0xACC3` | `0x7694` handoff to `0x104D` | not found by this method |
| `0x769E` / `0x2769E` | `0x07D1` | `0x0A35` | `DPTR ← 0x0A35 + low8(A×0x17)` | `A` | `0xACC3` | `0x76A4` handoff to `0xAD1E` | not found by this method |
| `0x8068` / `0x28068` | `0x07D5` | `0x0A15` | `DPTR ← 0x0A15 + low8(R7×0x17)` | `R7` | `0x9720` | `0x806E` | `0x806E` read |
| `0x8077` / `0x28077` | `0x07D4` | `0x0A27` | `DPTR ← 0x0A27 + low8(0x00×0x17)` | `0x00` | `0x9702` | `0x807D` | `0x807D` read |
| `0x80B9` / `0x280B9` | `0x07D4` | `0x0A27` | `DPTR ← 0x0A27 + low8(A×0x17)` | `A` | `0x9702` | `0x80BF` | `0x80BF` read |
| `0x80E5` / `0x280E5` | `0x07D4` | `0x0A13` | `DPTR ← 0x0A13 + low8(A×0x17)` | `A` | `0x96F0` | `0x80EB` | `0x80EB` read |
| `0x81DD` / `0x281DD` | `0x07D4` | `0x0A13` | `DPTR ← 0x0A13 + low8(A×0x17)` | `A` | `0x96F0` | `0x81E3` | `0x81E3` read |
| `0xAED3` / `0x2AED3` | `0x07D1` | `0x0A2D` | `DPTR ← 0x0A2D + low8(A×0x17)` | `A` | `0xACE9` | `0xAED9` handoff to `0xADA4` | not found by this method |
| `0xAF70` / `0x2AF70` | `0x07D1` | `0x0A2C` | `DPTR ← 0x0A2C + low8(A×0x17)` | `A` | `0xACD6` | `0xAF76` | `0xAF76` read |
| `0xB39E` / `0x2B39E` | `0x07D1` | `0x0A35` | `DPTR ← 0x0A35 + low8(R7×0x17)` | `R7` | `0xACC3` | `0xB3A4` handoff to `0x104D` | not found by this method |
| `0xB3AE` / `0x2B3AE` | `0x07D1` | `0x0A2D` | `DPTR ← 0x0A2D + low8(A×0x17)` | `A` | `0xACE9` | `0xB3B4` handoff to `0xADA4` | not found by this method |
| `0xB3C8` / `0x2B3C8` | `0x07D1` | `0x0A35` | `DPTR ← 0x0A35 + low8(A×0x17)` | `A` | `0xACC3` | `0xB3CE` handoff to `0x1041` | not found by this method |
| `0xC8F0` / `0x2C8F0` | `0x0819` | `0x0A13` | `DPTR ← 0x0A13 + low8(A×0x17)` | `A` | `0x96F0` | `0xC8F8` | `0xC8F8` write |
| `0xCC5B` / `0x2CC5B` | `0xFCE0` | `0x0A29` | `DPTR ← 0x0A29 + low8(A×0x17)` | `A` | `0xCC62` | `0xCC6C` | `0xCC6C` read |
| `0xCC95` / `0x2CC95` | `0xFCE0` | `0x0A15` | `DPTR ← 0x0A15 + low8(A×0x17)` | `A` | `0xCC9B` | `0xCCA5` | `0xCCA5` read |
| `0xD745` / `0x2D745` | `0x07D1` | `0x0A2C` | `DPTR ← 0x0A2C + low8(A×0x17)` | `A` | `0xACD6` | `0xD74B` | `0xD74B` read |

`MOV DPTR` immediate and effective base are two different columns on purpose.
Every `0x17` site is `rebased`: the immediate it loads is the index variable it
reads (`0x07D1`, `0x07D4`, `0x07D5`, `0x0819`), and the array base arrives later
inside the helper. Collapsing the two is how §7.1 of the geometry file explains
why `--bases` misses three of its four addresses.

The index is not one kind of thing either, and what the term strings say about
it needs correcting before it can be used — §3.2. Fourteen of the seventeen
multiply a byte the helper itself loads out of XDATA, one multiplies a
caller-supplied register, and two are not resolved at all.

**Bases.** Seven, `0x0A13` through `0x0A35`, spanning `0x22` bytes with
successive differences `0x02 0x12 0x02 0x03 0x01 0x08`. Every difference is
smaller than the `0x17` stride, and no base is a whole number of strides from
another. So no two of them are consecutive records of one array at the same
index: they are seven field offsets inside a region, in the shape §3.3 of the
geometry file found for `0x04A1`–`0x04A6`. That is the whole of the
relationship the arithmetic supports, and §5 says why it stops there.

### 3.2 The index is not what the term strings say, and one bound is refuted

**The issue's own framing suggested a locally evidenced bound at `0x8077`, and
the bytes refute it.** `0x8077`'s frame does put a literal `0x00` in A, and the
committed tool duly prints `DPTR ← 0x0A27 + low8(0x00×0x17)` — which would make
the address exactly `0x0A27`. It is not. Helper `0x96FE` opens with
`movx a,@dptr`, which replaces A before the multiply at `0x9702`, so the zero
never reaches it. `pd-stride-families.md` records this as a correction because
`chain_from()` hands a helper's `{a}` placeholder the **caller's** frame A, and
that substitution is only sound for a helper that multiplies what it is given:

```console
$ python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --sites 0x8077
0x17  site runtime 0x8077 (file 0x28077)
  MOV DPTR immediate 0x07D4, effective base 0x0A27 (rebased)
  DPTR ← 0x0A27 + low8(0x00×0x17)   [low8-truncated]
  index factor 0x00 (term) / XDATA byte read by the helper (bytes)   frame 24/24   supported-code-site
```

So the tool carries two columns and they are not redundant. `index_factor` is
what the term string says; `index_source` is what the helper's own instructions
say reaches the multiply. Across the three families:

| family | what actually reaches the multiply | sites |
|---|---|---|
| `0x17` | the byte the helper's `movx a,@dptr` returns | 14 |
| `0x17` | a caller-supplied register (`R7` at `0x8068`, via `0x971B`'s `mov a,r7`) | 1 |
| `0x17` | not found by this method — the two framing candidates of §3.4 | 2 |
| `0x67` | the caller-supplied accumulator, unresolved | 7 |
| `0x04` | the caller-supplied accumulator, unresolved | 2 |

`0x8068` is the one `0x17` site whose helper copies the index out of the
register bank instead of reloading it, which is why its term string and the
bytes agree. Every other `0x17` helper begins `movx a,@dptr`, so the index is
**the byte stored at the address the site just loaded** — `XDATA[0x07D1]` for
the sites that load `0x07D1`, and so on. That is a materially better answer
than "unresolved accumulator", and it is checkable from the bytes; it is still
not a bound, because the *value* in that XDATA cell is not knowable from the
firmware.

The same substitution reaches the `0x5E` family: §8.1 of the geometry file
already carries the correction there (`0x34D9` is `low8(A×0x5E)`, and `A` is
"the byte loaded by the entry's MOVX, not a preserved caller accumulator").
This is the same defect seen from the site side, and `pd-base-strides.csv` is
unmoved by it — the constant, the base and the site list are all read before
the factor is substituted. The document records the mechanism rather than
restating §8.1.

**What is bounded, then.** Nothing in this family. The two `0x67`/`0x04`
multiplies that name `R5` and `R7` are bounded by their helpers' register bank
only to the extent the caller's value is, which this method does not follow.

### 3.3 `0x67` and `0x04`: exact products through `0x10BC`

Both families reach DPTR through helper `0x10BC`, and that helper keeps the
multiplication's high byte where the `0x17` template drops it. `mov a,b` at
`0x10C1` is the whole difference:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x10bc; pd 7' /tmp/pd-75.bin
            0x000010bc      a4             mul ab
            0x000010bd      2582           add a, dpl
            0x000010bf      f582           mov dpl, a
            0x000010c1      e5f0           mov a, b
            0x000010c3      3583           addc a, dph
            0x000010c5      f583           mov dph, a
            0x000010c7      22             ret
```

So `DPTR = base + index × 0x67` is exact to sixteen bits here, modulo
`0x10000`. That is a materially different data-layout claim from §3.1's
`low8`, and it is the reason the two families are not one finding.

`0x67`, seven sites over six bases:

| site / file | immediate = base | address expression | index | stop | unmodelled DPH addend | listing |
|---|---|---|---|---|---|---|
| `0x2F0B` / `0x22F0B` | `0x07C4` | `DPTR = 0x07C4 + A×0x67` | `A` | `0x2F12` | `R3` | not found by this method |
| `0x2F6A` / `0x22F6A` | `0x07A3` | `DPTR = 0x07A3 + A×0x67` | `A` | `0x2F71` | `R5` | not found by this method |
| `0x9C15` / `0x29C15` | `0x0661` | `DPTR = 0x0661 + A×0x67` | `A` | `0x9C1F` | `R7` | not found by this method |
| `0x9C39` / `0x29C39` | `0x0667` | `DPTR = 0x0667 + A×0x67` | `A` | `0x9C40` | `R3` | not found by this method |
| `0x9C46` / `0x29C46` | `0x069A` | `DPTR = 0x069A + A×0x67` | `A` | `0x9C51` | `R6` | `read_xdata_to_r6_set_dptr_069a` |
| `0x9C6D` / `0x29C6D` | `0x069B` | `DPTR = 0x069B + R5×0x67` | `R5` | `0x9C78` | `R5` | not found by this method |
| `0xCF13` / `0x2CF13` | `0x07C4` | `DPTR = 0x07C4 + A×0x67` | `A` | `0xCF1A` | `R3` | not found by this method |

`0x04`, two sites over two bases:

| site / file | immediate = base | address expression | index | stop | listing |
|---|---|---|---|---|---|
| `0xA399` / `0x2A399` | `0x00C0` | `DPTR = 0x00C0 + R7×0x04` | `R7` | `0xA39F` handoff to `0x104D` | not found by this method |
| `0xA3AD` / `0x2A3AD` | `0x00C8` | `DPTR = 0x00C8 + A×0x04` | `A` | `0xA3B3` handoff to `0x104D` | not found by this method |

Neither family rebases: the `MOV DPTR` immediate *is* the base here
(`site-immediate` in the CSV), which is the third reason the two shapes do not
share a row.

**Bases.** `0x67`'s six run `0x0661` to `0x07C4` with differences
`0x06 0x33 0x01 0x108 0x21` — a `0x108` gap and a set of sub-stride
differences, and no base a whole number of `0x67` from another. `0x04`'s two
are `0x00C0` and `0x00C8`, exactly two strides apart, which *is* a whole-number
relationship. One family shows a two-record relationship and the other does
not; with two and six points respectively, and §4's stops on every one of them,
that is as far as the arithmetic goes.

### 3.4 The two `0x17` sites whose `MOV DPTR` byte is an `lcall` operand

`0xCC5B` and `0xCC95` are the only two sites `converges_from()` refuses: no
backward anchor in the 24-byte window lands on either. The bytes say why, and
the reason is checkable rather than inferred — the `0x90` a byte scan reads as
`mov dptr` is the **middle byte of an `lcall`** a byte earlier:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xcc58; pd 6; s 0xcc92; pd 6' /tmp/pd-75.bin
            0x0000cc58      c8             xch a, r0
            0x0000cc59      ef             mov a, r7
            0x0000cc5a      1290fc         lcall 0x90fc
            0x0000cc5d      e0             movx a, @dptr
            0x0000cc5e      ff             mov r7, a
            0x0000cc5f      75f017         mov b, #0x17
            0x0000cc62      a4             mul ab
            0x0000cc92      f3             movx @r1, a
            0x0000cc93      ef             mov a, r7
            0x0000cc94      1290fc         lcall 0x90fc
            0x0000cc97      e0             movx a, @dptr
            0x0000cc98      75f017         mov b, #0x17
            0x0000cc9b      a4             mul ab
```

The census reads `0xCC5B` as `mov dptr,#0xFCE0`; the instruction stream has
`lcall 0x90FC` at `0xCC5A` and a `movx` at `0xCC5D`, and `0xFCE0` is the
`lcall`'s own operand bytes. So the site's `mov_dptr_immediate` cell is a byte
scan artefact and **not an address this code loads** — which is why
`effective_base` and `index_terms` are reported from the chain and not from that
cell, and why the two columns are separate in the CSV.

The `0x17` arithmetic at both sites is real and is *not* affected: the
`mul ab` at `0xCC62` and `0xCC9B` is in the stream r2 decodes, and the
constructions the chains reach (`0xCC62`, `0xCC9B`) are in
[pd-index-accesses.csv](pd-index-accesses.csv) as `access` rows. This is the
concrete case where `framing` earns its keep: the family is otherwise uniform
and these two are not, and only the framing measurement separates them.

### 3.5 The overlapping add-only suffix is not this chain's construction

`immediate_templates()` retains overlapping runs on purpose —
[pd-index-geometry.md](pd-index-geometry.md) §8.3 keeps independently entered
add-only suffixes as their own constructions, so a `mul ab` template at
`0xACC3` also matches its own `add a,#35 ; mov dpl,a ; clr a ; addc a,#0a ;
mov dph,a` suffix at `0xACC4`. These chains entered at the full template and
consumed the whole run, so `construction_runtime` names `0xACC3` and not
`0xACC4`. The suffix is a separate row in
[pd-index-accesses.csv](pd-index-accesses.csv) with its own context — reached
from outside, not by this chain — and this file does not re-count it.

## 4. The two censuses, reconciled

`pd-index-accesses.csv` has rows for the `0x17` constructions and **none at
all** for `0x67` or `0x04`, anywhere in the file. That is not a gap in this
analysis; it is the shape of the two tools, and it is worth stating precisely
because §7.5 read the absence as "nothing has looked at them".

- `access_rows()` seeds on `immediate_templates()` and on direct branch targets
  whose supported prefix reaches one. A rebasing template is a seed, so the
  `0x17` constructions are found — at the **template address** (`0xACC3`,
  `0x9702`, `0x96F0`, `0x9720`, `0xACE9`, `0xACD6`, `0xCC62`, `0xCC9B`), not
  at the `MOV DPTR` anchor that reached them.
- A `0x67` or `0x04` site reaches `0x10BC`, which is an *additive* helper: it
  advances whatever DPTR already holds and builds no immediate base. There is
  no template to seed on and no rebasing to file, so the construction census
  cannot see these sites by construction.
- The two walks are independent — `access_walk()` never calls `chain_from()` —
  so this file **reads** the committed access CSV rather than recomputing it,
  and the `access_*` columns are a summary of what is filed at the
  construction address. The individual rows come back by joining
  `construction_runtime` against `construction_runtime` in
  [pd-index-accesses.csv](pd-index-accesses.csv).

So the denominators do not meet and are not meant to. `0x17` is described twice,
once as `MOV DPTR` anchors and once as template constructions, and the join
above is what says they are the same arithmetic. `0x67` and `0x04` are
described once, here.

## 5. What this does not establish

- **No record count, no record width, no record content.** A stride constant is
  a multiply factor in an address expression. `low8(index * 0x17)` and
  `index * 0x17` agree only below index 12, which `--families` computes rather
  than asserts, and §7.4's correction (PR #74) is the standing precedent that
  neither form is an unconditional record width. The `0x17` bases' sub-stride
  spacing in §3.1 is consistent with field offsets inside a region and with
  nothing else; it does not name a region, a field, or a byte.
- **The address expressions are complete only as far as the chain walked.** Ten
  `0x17` sites stop at their first `movx`, which is a real first consumer with
  a direction. Seven `0x67` sites stop at `add a,dph` and the register it adds
  is recorded — but it is recorded as an **unmodelled second index term and a
  stop**, not folded into the address, because the term model does not cover
  that instruction and §3.3's expressions are what the model resolved.
- **The `0x04` chain's terminal is a computed jump, not a MOVX.** Both sites
  hand DPTR to `0x104D`, which moves DPTR's halves into `R0` and `B`, restores
  DPTR from the stack, calls `0x1064` four times and ends in `clr a ; jmp
  @a+dptr`; `0x1064` reads a byte with `movc` and stores it through `movx
  @dptr,a` at `0x1071`. So the constructed pointer is the *destination* of that
  store and the dispatch is through the caller's restored pointer — a different
  shape from either `0x17` or `0x67`, and one this tool deliberately does not
  reduce to a term. `--sites 0xA399` shows the handoff; whether that path ran is
  not established.
- **No index range, and no index bound.** §3.2 corrects the one bound this
  analysis was expected to contain: `0x8077`'s index is an XDATA byte, not the
  literal its frame supplies, so no `0x17` site is bounded by these bytes. The
  `0x67` and `0x04` sites multiply the caller-supplied accumulator throughout,
  whose value this method does not follow.
- **The bases are PD-program data-space addresses.** Nothing here makes them
  host-visible EC registers, and `../annotations/registers.yaml` is unchanged:
  static evidence cannot re-grade a register.
- **No hardware observation, and no call graph.** An unaligned `MOV DPTR` scan
  finds data bytes as readily as opcodes — §3.4 is what that looks like here —
  and a consumer behind a computed jump carries no target bytes at all. An
  unestablished consumer is `not found by this method`, never "none".

## 6. What remains unresolved

- **Callers, for both `0x67` and `0x04`.** Every chain in those two families
  ends at a `ret`-bearing entry whose caller this tool does not recover; naming
  it is full call-graph work and is issue #26's territory, not a bounded static
  step. The two `0x04` sites are one case: `0x104D`'s dispatch target is a value
  read at run time, so the code it jumps to is not in the bytes at all.
- **The unmodelled `DPH` addend.** `add a,dph` after `mov a,rN` is a real second
  index term on seven sites and the term model does not cover it. Widening the
  model to admit it is a change to `pd_index_geometry.py` that would move
  `pd-base-strides.csv`, so it is a separate, deliberate change rather than a
  line here.
- **What the `0x17` region is.** Seven field offsets between `0x0A13` and
  `0x0A35`, reached from five `ec/decompiled/pd/` listings — `update_07d4_state`,
  `set_07d2_and_return_r7_zero_or_one`, `write_07d1_then_call_chain`,
  `write_07d2_then_dispatch_on_07d1` and
  `stage_07d1_set_0ffd4_bit5_then_tail_c755` — whose own names describe the index
  variable and the dispatch around it, not the array. Nothing in these bytes
  names what is stored there.
- **The `A` a helper's term carries, in `pd_index_geometry.py` itself.**
  §3.2 reads the substitution off each helper's own instructions and reports it
  in a separate column, but the substitution is still in place: `--sites` and
  `--bases` keep printing a caller's frame A into a helper that reloads A
  first. §8.1 of the geometry file carries the same correction for the `0x5E`
  family, and the committed CSVs are unaffected because none of them records an
  index factor. Changing `chain_from()` to stop substituting would move the term
  strings the existing annotations quote, so it belongs in its own change with
  those annotations updated alongside — not in a file this work only reads.
- **The `0x17` `0x2C`/`0x2D`/`0x35` trio.** `0x0A2C`, `0x0A2D` and `0x0A35` are
  one, two and eight bytes apart, and the helpers that build them differ only
  in the register the loaded index is parked in. Whether that is one array
  indexed three ways or three arrays is not settled by the arithmetic, and this
  file does not guess.

## 7. Corrections to the figures this supersedes

The issue that opened this quoted
[pd-base-strides.csv](pd-base-strides.csv) as it stood before #67 widened the
walker. Those are the struck pre-#67 numbers §7.2 of the geometry file already
keeps beside the current ones; nothing is retracted here — #67 taught
`chain_from()` one instruction and every figure that did not depend on it is
unchanged. The delta is recorded once so a reader holding the older numbers can
place them:

| family | as filed in the issue | committed `pd-base-strides.csv` | this file |
|---|---|---|---|
| `0x17` | 9 sites, bases `0x0A15 0x0A27 0x0A35` | 17 sites, 7 bases | 17 sites, 7 bases, listed per site in §3.1 |
| `0x67` | 6 sites, 5 bases `0x0661 0x0667 0x069B 0x07A3 0x07C4` | 7 sites, 6 bases | 7 sites, 6 bases; the sixth base is `0x069A` |
| `0x04` | 2 sites, bases `0x00C0 0x00C8` | 2 sites, 2 bases | 2 sites, 2 bases |

One further statement is superseded, and it is the one that made this an issue.
§7.5 of the geometry file said these three "are three strides nothing in this
repository has looked at", with the bases in
[pd-base-strides.csv](pd-base-strides.csv) and nothing more claimed. That was
true of the tree it was written against; this file is the look. The pointer
added to that section says so in place, in the note the section already has.

**A claim this analysis was expected to make, and does not.** The framing that
opened the issue proposed a "locally evidenced bound" for one `0x17` site, on
the reasoning that a frame putting a literal `0x00` in A makes the address at
`0x8077` exactly `0x0A27`. §3.2 refutes it from the bytes: the helper reloads A
before the multiply, so the frame's literal never reaches it and no site in
these three families is bounded by this method. The committed
`pd-base-strides.csv` is unaffected — it records constants, bases and site
counts, all read before the index factor is substituted — and the refuted bound
was never committed to it.
