# The PD stride families `0x17`, `0x67` and `0x04`, read at site level

[pd-base-strides.csv](pd-base-strides.csv) carries these three as aggregate
rows — a site count, a base count, a base list — which is the right shape for a
census and the wrong one for what the rows raise. [pd-index-geometry.md](pd-index-geometry.md)
§7.5 left them as the three strides "nothing in this repository has looked at".
This reads each contributing `MOV DPTR` on its own and says where its address
stops being followable.

**What this establishes.** Three strides resolve to **two data-layout
shapes**, not one finding. `0x17` truncates the multiply's high byte;
`0x67` and `0x04` keep it. The `0x67` and `0x04` walks each stop on a second
index term the term model does not carry, so both families' addresses are known
only to the point the walk stops. And the site's own backward frame does not
reach its multiply at the `0x17` sites whose construction entry opens
`movx a,@dptr` — §3.1 gives the split and names the exceptions — which refutes
the frame-literal bound the issue expected and generalises past the site it
named.

**What this does not establish, in one place so no section below has to repeat
it.** No record count, record width or record content follows from a stride
constant — see [pd-index-geometry.md](pd-index-geometry.md) §7.4 for the
retraction that is the standing precedent. Every base below is a PD-program
**data-space** address, not a host-visible EC register, and
`ec/annotations/registers.yaml` is untouched by this work: static evidence cannot
re-grade a register. No EC, laptop or Windows host was reachable while this was
produced, no register was read back, and no live test ran. Everything here is
static analysis of committed bytes.

## 1. Input, reproduction and framing

Input: `ec/firmware/GMxMGxx_11.800`, 262,144 bytes, SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`.
The `trace_xdata_refs.py` map places PD at file `[0x20000,0x30000)`; file
`0x20040` holds `ITE8850-PD`. For **every instruction address below**, file
offset = runtime address + `0x20000`. XDATA operand addresses do not use that
conversion: they are addresses in the PD program's own data space.

Run from the repository root. Generate the temporary output first and compare;
none of these overwrite a committed baseline:

```sh
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --families
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 --csv \
    > /tmp/pd-stride-family-sites.csv
cmp /tmp/pd-stride-family-sites.csv ec/annotations/pd-stride-family-sites.csv
python3 ec/tools/pd_stride_families.py ec/firmware/GMxMGxx_11.800 \
    --sites 0x8077 0xCC5B 0x2F0B 0xA399

# the baselines this work reads, left byte-identical
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --self-test
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
    --strides-csv all > /tmp/pd-base-strides.csv
cmp /tmp/pd-base-strides.csv ec/annotations/pd-base-strides.csv
python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 \
    --accesses-csv all > /tmp/pd-index-accesses.csv
cmp /tmp/pd-index-accesses.csv ec/annotations/pd-index-accesses.csv
python3 ec/tools/pd_image_census.py --self-test
```

`--families` prints every figure this document quotes that is not a per-site
row: the site and base totals, the arithmetic class, the index at which the
class stops agreeing with an exact product, the framing split, the multiply's
operand split, the §8 access-join split, and the decoded body of every chain
entry reached. Each section's table is the committed
[pd-stride-family-sites.csv](pd-stride-family-sites.csv) restricted to that
family, so a per-site figure is read off the file the tool wrote.

Independent decoding used **radare2 5.5.0** on a temporary flat PD image, as
§7.3, §8.1 and [pd-0x38-consumers.md](pd-0x38-consumers.md) §1 all do. The
firmware, not r2's synthetic memory-hint comments, is the evidence:

```sh
sha256sum ec/firmware/GMxMGxx_11.800
r2 -v
dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd-75.bin bs=65536 skip=2 count=1
r2 -a 8051 -e scr.color=0 -q -c \
  's 0x10bc; pd 8; s 0x96eb; pd 9; s 0x96fe; pd 8; s 0x971b; pd 8; s 0xacbf; pd 8; s 0xacd1; pd 9; s 0xace4; pd 9; s 0xcc58; pd 8; s 0xcc92; pd 8' \
  /tmp/pd-75.bin
r2 -a 8051 -e scr.color=0 -q -c \
  's 0x2f0b; pd 5; s 0x2f6a; pd 6; s 0x9c15; pd 5; s 0x9c39; pd 5; s 0x9c46; pd 6; s 0x9c6d; pd 6; s 0xcf13; pd 5; s 0xa399; pd 4; s 0xa3ad; pd 4; s 0x8077; pd 4; s 0x104d; pd 8; s 0x1064; pd 8' \
  /tmp/pd-75.bin
```

**Framing is conditional, not a recovered call graph.** A site is an
`instruction-framing-candidate` when the byte before its `0x90` opcode is an
`lcall` or `ljmp` opcode, which makes that `0x90` the high half of a branch
target rather than a `MOV DPTR`. The class is evidence about framing, not a
claim about what the bytes do, and §4 gives its two instances with the bytes.
Backward convergence (`frame_onto` / `frame_over` in the CSV) measures framing
evidence, not likelihood of execution, and a site with no converging anchor is
not thereby misframed.

Every walk is bounded by both a count and `min(region_end, len(d))`, so a run
off the region end is a named stop rather than a listing of the fill past it.

## 2. The two shapes, from the bytes

`--families` prints each chain entry's decoded body. The two that define the
shapes, with the instruction that separates them underlined in prose rather than
in the table:

| entry | bytes | what feeds the `addc` | arithmetic class |
|---|---|---|---|
| `0x10BC` | `a4 25 82 f5 82 e5 f0 35 83 f5 83 22` | `e5 f0` — `mov a,b` | `full-product` |
| `0x96FE` | `e0 75 f0 17 a4 24 27 f5 82 e4 34 0a f5 83 22` | `e4` — `clr a` | `low8-truncated` |
| `0x96EB` | `e0 ff 75 f0 17 a4 24 13 f5 82 e4 34 0a f5 83 22` | `e4` — `clr a` | `low8-truncated` |
| `0x971B` | `f0 ef 75 f0 17 a4 24 15 f5 82 e4 34 0a f5 83 22` | `e4` — `clr a` | `low8-truncated` |
| `0xACBF` | `e0 75 f0 17 a4 24 35 f5 82 e4 34 0a f5 83 22` | `e4` — `clr a` | `low8-truncated` |
| `0xACD1` | `e0 ff 75 f0 17 a4 24 2c f5 82 e4 34 0a f5 83 22` | `e4` — `clr a` | `low8-truncated` |
| `0xACE4` | `e0 fb 75 f0 17 a4 24 2d f5 82 e4 34 0a f5 83 22` | `e4` — `clr a` | `low8-truncated` |

`0x10BC` is `mul ab ; add a,dpl ; mov dpl,a ; mov a,b ; addc a,dph ; mov
dph,a ; ret`: `mov a,b` carries the multiplication's **high** byte into the
`addc`, so the address is the full 16-bit product. Every `low8(...)` entry above
is `add a,#lo ; mov dpl,a ; clr a ; addc a,#hi ; mov dph,a`: `clr a` **discards**
the high byte, and only the carry out of `add a,#lo` survives into the `addc`.
`low8(x) = x & 0xFF`; every address wraps modulo `0x10000`; discarding the high
byte does not discard the base's carry. The `mov b,#0xNN` each `low8(...)`
entry loads before its `mul ab` is the stride, and `0x10BC` takes whatever B
its caller left.

`--families` also prints the index at which each family's two shapes stop
agreeing — the smallest index whose product leaves the low byte, computed in
integer arithmetic. `0x17` reaches it at index 12 (`low8 = 20`, exact `276`);
`0x67` at index 3 (`low8 = 53`, exact `309`); `0x04` at index 64 (`low8 = 0`,
exact `256`). Below its family's index the two shapes compute the same address
and above it they do not, which is what makes them two claims about the layout
rather than two spellings of one.

## 3. `0x17`: a truncating construction behind its chain entries

`--families` reads `0x17` as **17 site(s) over 7 base(s): 0x0A13 0x0A15 0x0A27
0x0A29 0x0A2C 0x0A2D 0x0A35**, all `low8-truncated`.

Every one of these sites reaches a `low8(...)` chain entry **except `0xCC5B` and
`0xCC95`, which reach no entry at all** — their `helpers` cell reads
`not found by this method`, and §4 is why. Every site's chain entry ends the
walk at a `movx` or at an entry the term model does not cover, and the CSV's
`chain_stop`, `stop_runtime` and `stop_file` columns say which of the two and
where; no site here has a chain that runs to a `ret` it modelled.

| site | file | `mov dptr` immediate | effective base | `base_source` | term | operand | chain entries | stops at |
|---|---|---|---|---|---|---|---|---|
| `0x75CD` | `0x275CD` | `0x07D1` | `0x0A35` | rebased | `DPTR ← 0x0A35 + low8(A×0x17)` | `movx-load` | `0xACBF 0x1041` | `0x75D3` |
| `0x768E` | `0x2768E` | `0x07D1` | `0x0A35` | rebased | `DPTR ← 0x0A35 + low8(A×0x17)` | `movx-load` | `0xACBF 0x104D` | `0x7694` |
| `0x769E` | `0x2769E` | `0x07D1` | `0x0A35` | rebased | `DPTR ← 0x0A35 + low8(A×0x17)` | `movx-load` | `0xACBF 0xAD1E` | `0x76A4` |
| `0x8068` | `0x28068` | `0x07D5` | `0x0A15` | rebased | `DPTR ← 0x0A15 + low8(R7×0x17)` | `register` | `0x971B` | `0x806E` |
| `0x8077` | `0x28077` | `0x07D4` | `0x0A27` | rebased | `DPTR ← 0x0A27 + low8(0x00×0x17)` | `movx-load` | `0x96FE` | `0x807D` |
| `0x80B9` | `0x280B9` | `0x07D4` | `0x0A27` | rebased | `DPTR ← 0x0A27 + low8(A×0x17)` | `movx-load` | `0x96FE` | `0x80BF` |
| `0x80E5` | `0x280E5` | `0x07D4` | `0x0A13` | rebased | `DPTR ← 0x0A13 + low8(A×0x17)` | `movx-load` | `0x96EB` | `0x80EB` |
| `0x81DD` | `0x281DD` | `0x07D4` | `0x0A13` | rebased | `DPTR ← 0x0A13 + low8(A×0x17)` | `movx-load` | `0x96EB` | `0x81E3` |
| `0xAED3` | `0x2AED3` | `0x07D1` | `0x0A2D` | rebased | `DPTR ← 0x0A2D + low8(A×0x17)` | `movx-load` | `0xACE4 0xADA4` | `0xAED9` |
| `0xAF70` | `0x2AF70` | `0x07D1` | `0x0A2C` | rebased | `DPTR ← 0x0A2C + low8(A×0x17)` | `movx-load` | `0xACD1` | `0xAF76` |
| `0xB39E` | `0x2B39E` | `0x07D1` | `0x0A35` | rebased | `DPTR ← 0x0A35 + low8(R7×0x17)` | `movx-load` | `0xACBF 0x104D` | `0xB3A4` |
| `0xB3AE` | `0x2B3AE` | `0x07D1` | `0x0A2D` | rebased | `DPTR ← 0x0A2D + low8(A×0x17)` | `movx-load` | `0xACE4 0xADA4` | `0xB3B4` |
| `0xB3C8` | `0x2B3C8` | `0x07D1` | `0x0A35` | rebased | `DPTR ← 0x0A35 + low8(A×0x17)` | `movx-load` | `0xACBF 0x1041` | `0xB3CE` |
| `0xC8F0` | `0x2C8F0` | `0x0819` | `0x0A13` | rebased | `DPTR ← 0x0A13 + low8(A×0x17)` | `movx-load` | `0x96EB` | `0xC8F8` |
| `0xCC5B` | `0x2CC5B` | `0xFCE0` | `0x0A29` | rebased | `DPTR ← 0x0A29 + low8(A×0x17)` | not named by this method | not found by this method | `0xCC6C` |
| `0xCC95` | `0x2CC95` | `0xFCE0` | `0x0A15` | rebased | `DPTR ← 0x0A15 + low8(A×0x17)` | not named by this method | not found by this method | `0xCCA5` |
| `0xD745` | `0x2D745` | `0x07D1` | `0x0A2C` | rebased | `DPTR ← 0x0A2C + low8(A×0x17)` | `movx-load` | `0xACD1` | `0xD74B` |

### 3.1 What the multiply actually consumes

`operand` is the column the term strings cannot answer, and it is the
substantive result of reading this family at site level. The committed decode
substitutes each site's own backward frame into every `{a}` a chain entry
leaves behind. At most of these sites that substitution describes a value the
multiply never sees, because the construction entry opens `movx a,@dptr`, which
replaces A with a byte read out of XDATA at the pointer DPTR already holds.

`--families` prints the split: `movx-load` at `0x75CD 0x768E 0x769E 0x8077
0x80B9 0x80E5 0x81DD 0xAED3 0xAF70 0xB39E 0xB3AE 0xB3C8 0xC8F0 0xD745`;
`register` at `0x8068`, whose entry `0x971B` opens `f0 ef` — `movx @dptr,a ;
mov a,r7` — so A survives the access and the operand is R7; and
`not named by this method` at `0xCC5B` and `0xCC95`, whose backward frame
converges on nothing.

**The bound this refutes.** Site `0x8077` looks locally pinned. Its frame puts a
literal `0x00` in A, the committed decode resolves that literal into the term,
and the resulting `0x0A27 + low8(0x00×0x17)` would name exactly `0x0A27`. It
does not. `pd[0x96fe:]` is `e0 75 f0 17 a4 24 27` —

```
96FE  e0        movx a,@dptr
96FF  75 f0 17  mov b,#0x17
9702  a4        mul ab
9703  24 27     add a,#0x27
```

— so A is replaced by a byte read from XDATA before `mul ab` executes, and the
`0x00` never becomes the multiplier's operand. `--self-test` holds the frame
value, the entry's opening bytes and the row's `operand` cell together, and the
row's `index_terms` is still reported as the committed decode resolves it: this
is a refutation with its bytes, not a corrected figure, and the correction
belongs in `pd_index_geometry.py` if anyone makes one.

The same reading applies to every row whose `operand` is `movx-load`, which is
why the claim is about the family and not about `0x8077` alone.

### 3.2 The sites the access census also reaches

The two censuses count different things and this is where they meet. A site's
join key is the handoff edge leaving the instruction **after** its `MOV DPTR`,
and only where that edge names an entry the site's own chain reached — the same
call seen from two walks. `--families` prints the split: `0x17` has **8 of 17**
sites with an access row, `0x67` and `0x04` have **0 of 7** and **0 of 2**.
That asymmetry is the gap §8's census left, and it is why this family is
reconciliation and the other two are new ground.

| site | row kind | status | direction | consumer | `access_id` |
|---|---|---|---|---|---|
| `0x8068` | `access` | `decoded-candidate` | `read` | `0x806E` | `template:0x9720@0x806B>0x971B/0x806E@body` |
| `0x8077` | `access` | `decoded-candidate` | `read` | `0x807D` | `template:0x9702@0x807A>0x96FE/0x807D@body` |
| `0x80B9` | `access` | `decoded-candidate` | `read` | `0x80BF` | `template:0x9702@0x80BC>0x96FE/0x80BF@body` |
| `0x75CD` | `construction-only` | `consumption-not-established` | no direction established by this method | not found by this method | `template:0xACC3@0x75D0>0xACBF/none` |
| `0x768E` | `construction-only` | `consumption-not-established` | no direction established by this method | not found by this method | `template:0xACC3@0x7691>0xACBF/none` |
| `0x769E` | `construction-only` | `consumption-not-established` | no direction established by this method | not found by this method | `template:0xACC3@0x75AF>0x769E;0x76A1>0xACBF/none` |
| `0xB39E` | `construction-only` | `consumption-not-established` | no direction established by this method | not found by this method | `template:0xACC3@0xB3A1>0xACBF/none` |
| `0xB3C8` | `construction-only` | `consumption-not-established` | no direction established by this method | not found by this method | `template:0xACC3@0xB3CB>0xACBF/none` |

Three of these reach a decoded **read** at the `movx` immediately after the
construction, which is the first supported consumer for those sites and the
only consumer this work establishes. The rest are §8's `construction-only`: the
arithmetic is decoded and the consumption is not. Where several §8 rows share
one edge they are the same call under different framings, and the CSV names the
first by `access_id` — a naming rule, not a judgement.

### 3.3 Base relationships inside the family

The committed bases sort to successive differences `0x02 0x12 0x02 0x03 0x01
0x08`, none of them the family's own stride. Exactly one pair of the seven is a
stride apart — `0x0A2C - 0x0A15 = 0x17` — and it is not an adjacent pair in the
sorted order. That is an observation about the arithmetic and not a lattice: two
bases differing by the stride says nothing about what sits at either address, and
one pair is not a pattern. Nothing here establishes that any of the six
differences is a field offset, and §8 says why nothing here can. The site's own
`MOV DPTR` immediate is a different set of addresses again (`0x07D1`, `0x07D4`,
`0x07D5`, `0x0819`), which is why `base_source` keeps `rebased` and
`site-immediate` apart rather than folding the two into one base column.

## 4. Where the `0x90` is an `lcall` operand

`--families` lists `0xCC5B` and `0xCC95` as the `0x17` family's
`instruction-framing-candidate`s, the sites whose chain reaches no helper. The
byte before each site's `0x90` is `0x12`, an `lcall` opcode:

```
CC58  c8           xch a,r0
CC59  ef           mov a,r7
CC5A  12 90 fc     lcall 0x90fc
CC5D  e0           movx a,@dptr
CC5E  ff           mov r7,a
CC5F  75 f0 17     mov b,#0x17
CC62  a4           mul ab
CC63  24 29        add a,#0x29

CC92  f3           movx @r1,a
CC93  ef           mov a,r7
CC94  12 90 fc     lcall 0x90fc
CC97  e0           movx a,@dptr
CC98  75 f0 17     mov b,#0x17
CC9B  a4           mul ab
CC9C  24 15        add a,#0x15
```

The byte scan read `90 fc e0` at `0xCC5B` and `90 fc e0` at `0xCC95` as
`mov dptr,#0xFCE0`, and that immediate is in both CSV rows. It is the high half
of the `lcall 0x90FC` target followed by the `movx a,@dptr` opcode. Both sites
are therefore **not** `MOV DPTR` sites at all; the `low8(...)` constructions
they appear to contribute are the inline templates at `0xCC62` and `0xCC9B`,
which is why their `helpers` cell is `not found by this method` — there is no
call to reach. The two are reported as framing candidates and not as code sites,
and `--self-test` holds both byte runs, both labels and both empty `helpers`
cells together.

## 5. `0x67`: full-product, and every chain stops on an unmodelled DPH addend

`--families` reads `0x67` as **7 site(s) over 6 base(s): 0x0661 0x0667 0x069A
0x069B 0x07A3 0x07C4**, all `full-product`, all `code-site`, all reaching
`0x10BC`, and none with an access row.

Every one of these chains stops on the same shape: after `0x10BC` returns, an
instruction adds a value to DPH that the multiply never consumed. That is a
second index term, and the term model does not carry it, so each address is
known only to the point the walk stops.

| site | file | `mov dptr` immediate | effective base | `base_source` | term | operand | chain entries | stops at | stop reason |
|---|---|---|---|---|---|---|---|---|---|
| `0x2F0B` | `0x22F0B` | `0x07C4` | `0x07C4` | site-immediate | `A×0x67` | not named by this method | `0x10BC` | `0x2F12` | `` `add  a,0x83` at 0x2F12`` |
| `0x2F6A` | `0x22F6A` | `0x07A3` | `0x07A3` | site-immediate | `A×0x67` | not named by this method | `0x10BC` | `0x2F71` | `` `add  a,0x83` at 0x2F71`` |
| `0x9C15` | `0x29C15` | `0x0661` | `0x0661` | site-immediate | `A×0x67` | not named by this method | `0x10BC` | `0x9C1F` | `` `add  a,0x83` at 0x9C1F`` |
| `0x9C39` | `0x29C39` | `0x0667` | `0x0667` | site-immediate | `A×0x67` | not named by this method | `0x10BC` | `0x9C40` | `` `add  a,0x83` at 0x9C40`` |
| `0x9C46` | `0x29C46` | `0x069A` | `0x069A` | site-immediate | `A×0x67` | not named by this method | `0x10BC` | `0x9C51` | `` `add  a,0x83` at 0x9C51`` |
| `0x9C6D` | `0x29C6D` | `0x069B` | `0x069B` | site-immediate | `R5×0x67` | `register` | `0x10BC` | `0x9C78` | `` `add  a,0x83` at 0x9C78`` |
| `0xCF13` | `0x2CF13` | `0x07C4` | `0x07C4` | site-immediate | `A×0x67` | not named by this method | `0x10BC` | `0xCF1A` | `` `add  a,0x83` at 0xCF1A`` |

The addends differ and the shape does not. The CSV's `stop_runtime` column
puts each walk at its own address, and the instruction immediately **before**
that address names the register the addend comes from:

| stop | three bytes ending at the stop | addend |
|---|---|---|
| `0x2F12` | `eb 25 83` | R3 |
| `0x2F71` | `ed 25 83` | R5 |
| `0x9C1F` | `ef 25 83` | R7 |
| `0x9C40` | `eb 25 83` | R3 |
| `0x9C51` | `ee 25 83` | R6 |
| `0x9C78` | `ed 25 83` | R5 |
| `0xCF1A` | `eb 25 83` | R3 |

`0x9C15` is the worked case:

```
9C15  90 06 61  mov dptr,#0x0661
9C18  75 f0 67  mov b,#0x67
9C1B  12 10 bc  lcall 0x10bc
9C1E  ef        mov a,r7
9C1F  25 83     add a,0x83
9C21  f5 83     mov 0x83,a
```

`lcall 0x10bc` leaves `DPTR = 0x0661 + A×0x67`, exact to 16 bits. `mov a,r7 ;
add a,0x83 ; mov 0x83,a` then adds **R7** to DPH, from a register the multiply
never consumed. Folding that into the address expression would be a guess about
R7's value at run time, so it is a stop and the term stays `A×0x67`.

The bases sort to successive differences `0x06 0x33 0x01 0x108 0x21`, none of
them the family's own stride and none of them another base. That is the whole
of what the base list supports: no lattice, and no bound on any of the six.

## 6. `0x04`: full-product, and the entry it hands DPTR to is a computed jump

`--families` reads `0x04` as **2 site(s) over 2 base(s): 0x00C0 0x00C8**, both
`full-product`, both `code-site`, both reaching `0x10BC` and then `0x104D`, and
neither with an access row.

| site | file | `mov dptr` immediate | effective base | `base_source` | term | operand | chain entries | stops at |
|---|---|---|---|---|---|---|---|---|
| `0xA399` | `0x2A399` | `0x00C0` | `0x00C0` | site-immediate | `R7×0x04` | `register` | `0x10BC 0x104D` | `0xA39F` |
| `0xA3AD` | `0x2A3AD` | `0x00C8` | `0x00C8` | site-immediate | `A×0x04` | not named by this method | `0x10BC 0x104D` | `0xA3B3` |

Both sites are the same three instructions:

```
A399  90 00 c0  mov dptr,#0x00c0
A39C  12 10 bc  lcall 0x10bc
A39F  12 10 4d  lcall 0x104d

A3AD  90 00 c8  mov dptr,#0x00c8
A3B0  12 10 bc  lcall 0x10bc
A3B3  12 10 4d  lcall 0x104d
```

`0x10BC` adds the exact 16-bit product to `0x00C0` / `0x00C8`, and the chain
then hands that DPTR to `0x104D`, which is outside the term model from its
first instruction:

```
104D  a8 82     mov r0,0x82
104F  85 83 f0  mov 0xf0,0x83
1052  d0 83     pop 0x83
1054  d0 82     pop 0x82
1056  12 10 64  lcall 0x1064
1059  12 10 64  lcall 0x1064
105C  12 10 64  lcall 0x1064
105F  12 10 64  lcall 0x1064
1062  e4        clr a
1063  73        jmp @a+dptr
```

and `0x1064`, the entry it calls four times, walks a code byte and stores
through it:

```
1064  e4        clr a
1065  93        movc a,@a+dptr
1066  a3        inc dptr
1067  c5 83     xch a,0x83
1069  c5 f0     xch a,0xf0
106B  c5 83     xch a,0x83
106D  c8        xch a,r0
106E  c5 82     xch a,0x82
1070  c8        xch a,r0
1071  f0        movx @dptr,a
```

So the first entry these chains reach after the construction ends in a
stack-dispatched `jmp @a+dptr`, and `0x1064`'s next XDATA write is the store at
`0x1071`. **Whether the constructed pointer reaches either is not established
here**: the dispatch target depends on a byte read at run time, and the walk
stops at `0x104D` rather than through it. Naming a consumer for these two sites
would be a claim the bytes do not carry.

## 7. The figures this issue was opened from, and what moved

The issue quotes the **struck pre-#67** rows, which
[pd-index-geometry.md](pd-index-geometry.md) §7.2 keeps beside the current ones.
The committed census is what this work covers; the table records the delta and
nothing else, because §7.2's own note already says the walker learned one
instruction and that figures not depending on it are unchanged.

| stride | issue's figures | committed census | delta |
|---|---|---|---|
| `0x17` | 9 sites, 3 bases (`0x0A15 0x0A27 0x0A35`) | 17 sites, 7 bases (`0x0A13 0x0A15 0x0A27 0x0A29 0x0A2C 0x0A2D 0x0A35`) | all three quoted survive; `0x0A13 0x0A29 0x0A2C 0x0A2D` added |
| `0x67` | 6 sites, 5 bases (`0x0661 0x0667 0x069B 0x07A3 0x07C4`) | 7 sites, 6 bases (`0x0661 0x0667 0x069A 0x069B 0x07A3 0x07C4`) | `0x069A` added; the five quoted survive |
| `0x04` | 2 sites, 2 bases (`0x00C0 0x00C8`) | 2 sites, 2 bases (`0x00C0 0x00C8`) | none |

Nothing is retracted. `pd-base-strides.csv` is a read-only input to this work and
`--self-test` fails if this tool's per-site rows disagree with it on any
family's sites or bases, so the two cannot drift apart silently.

## 8. What this does not establish

- **No record anything.** A stride constant is a step between addresses. How
  many records a family spans, how wide one is, and what sits in it are not
  established here and cannot be from a stride, which is
  [pd-index-geometry.md](pd-index-geometry.md) §7.4's standing correction.
- **No host-visible registers.** Every base here is a PD-program data-space
  address. `ec/annotations/registers.yaml` is not edited by this work, because
  static evidence cannot re-grade a register and the issue says so explicitly.
- **No index bound.** `index_source` says where the multiply's operand came
  from, not what it was. A byte read out of XDATA at a computed pointer is not
  a bounded index, and §3.1's finding removes the site's own literal rather
  than replacing it with a better one.
- **No execution.** No branch was taken, no register read back, no path proven
  reachable. `helpers` is an unaligned byte scan's target set: it over-counts
  (a `12 hi lo` inside a data table reads as an `lcall`) and under-counts (a
  computed jump carries no target bytes), so an empty `helpers` cell is "not
  found by this method", never "nothing is called".
- **No recovered function boundary.** `owning_function()` is a membership test
  against the committed `ec/decompiled/pd/*.asm` listings, and "outside the
  committed pd listings" means this repository has no listing covering the
  address — not that the bytes are data.
- **No hardware.** Nothing in this document was measured on a machine.

## 9. What remains unresolved

- **The second DPH addend on `0x67`.** Every `0x67` chain stops with a register
  added to DPH after the construction. What those registers hold is a caller
  question, and the callers are not named here.
- **The `0x104D` dispatch.** Whether the `0x04` construction reaches `0x1064`'s
  store at `0x1071` depends on a byte read at run time.
- **The consumers of the `0x17` chains that stop on an unmodelled entry.**
  `0x1041`, `0x104D`, `0xAD1E` and `0xADA4` are outside the term model, and
  `0xAD1E` and `0xADA4` reach `0x0FAF`, the reader
  [pd-0x38-consumers.md](pd-0x38-consumers.md) §2.2 transcribes.
- **Caller identity for both families.** Recovering it is
  [pd-index-geometry.md](pd-index-geometry.md) §6's runtime step, and the
  chains ending at an unmodelled entry hand their pointer to a caller this
  analysis cannot name.
