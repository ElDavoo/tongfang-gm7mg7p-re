# XDATA `0x1C39`/`0x1C3A` and the three staging trios: who writes them, and no consumer is named

`ec/annotations/xdata-086x-dispatch.md` §6 and §11.1 name this as the most
useful thing a follow-up could settle and correctly decline to guess at it: a
writer next to a reader is co-occurrence, not a consumer. This is that
follow-up, answered by static means. The machine-readable table behind every
number is **`xdata-1c3x-consumers-sites.csv`**, one row per direct `MOV DPTR`
site over the eleven addresses, keyed row-for-row to the `0x086x` page's own
table where the two overlap.

**Nothing here is a live observation.** No hardware is reachable from a
GitHub-hosted runner, so every status is `present-untested`, no `status:`
moves, and every zero is "not found by this method" rather than "absent"
(`docs/findings.md` §4c). The words *absent*, *unused* and *no consumer
exists* are not claims about any of the eleven bytes.

**The answer, in one line each.** `0x1C39`/`0x1C3A` are written and read
only inside `dispatch_on_0860`'s block, all ten sites in bank 0, and **no
consumer of either byte is identified by any method below**. `0x1C12`-`0x1C14`
and `0x1C36`-`0x1C38` have **no read site in any image** — the sharpest
negative here, because the only site each of `0x1C36`-`0x1C38` has is the
routine that writes it. `0x1C01`-`0x1C03` have **43 direct sites between them
and not one read**; all 43 are writes. The one positive this delivers is a
**second writer set for `0x1C12`-`0x1C14` in bank 1** (§3), which the page
document does not record at all.

## 1. How to reproduce it

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
      0x1C39 0x1C3A 0x1C12 0x1C13 0x1C14 0x1C36 0x1C37 0x1C38 \
      0x1C01 0x1C02 0x1C03 --csv \
  | diff - ec/annotations/xdata-1c3x-consumers-sites.csv
```

`67 rows`: 0 common, 19 bank0, 48 bank1, **0 in the PD image**. Every number
below is read out of that file. The page sweep that checks nothing on the
`0x1C00` page was missed is the span tool, which counts a whole span in one
pass rather than rescanning 256 KiB per address:

```console
$ python3 ec/tools/xdata_span_survey.py ec/firmware/GMxMGxx_11.800 0x1C00 0x1C3F
0x1C00-0x1C3F: 64 addresses
  main EC :   197 sites over 26 addresses
  PD image:     0 sites over 0 addresses
  both    : 0 address(es) with sites in each image
```

**No address on the `0x1C00` page has a single site in the PD image**, so for
all eleven bytes the PD image's own XDATA map cannot be a confound — the
opposite of the `0x0800` page, where §6 needs it. The 26 touched addresses
are `0x1C00`-`0x1C05`, `0x1C0A`, `0x1C10`, `0x1C11`-`0x1C16`, `0x1C1B`,
`0x1C20`, `0x1C21`, `0x1C29`, `0x1C31`, `0x1C34`-`0x1C3A`; 38 of the 64
have no direct site at all, and that is "not found by this method".

The two tables that already cover part of this ground agree with each other
field for field, which is the check that a count was not typed from memory:

```console
$ python3 - <<'EOF'
import csv
key = lambda r: (r['region'], r['runtime'])
old = list(csv.DictReader(open('ec/annotations/xdata-086x-dispatch-sites.csv', newline='')))
new = list(csv.DictReader(open('ec/annotations/xdata-1c3x-consumers-sites.csv', newline='')))
shared = {(r['addr'], key(r)): r for r in new}
rows = [r for r in old if (r['addr'], key(r)) in shared]
diff = [f for r in rows for f in ('frame_onto','frame_over','access','window')
        if r[f] != shared[(r['addr'], key(r))][f]]
print(len(rows), 'shared rows,', len(diff), 'field differences')
EOF
10 shared rows, 0 field differences
```

The ten shared rows are `0x1C39`/`0x1C3A`, all bank 0, and they are byte-for-
byte the rows the `0x086x` page already published.

## 2. The direct-method result, per byte

| addr | EC | b0 | b1 | read | write | the bank-1 writers the sweep names |
|---|---:|---:|---:|---:|---:|---|
| `0x1C39` | 5 | 5 | 0 | 2 | 3 | — |
| `0x1C3A` | 5 | 5 | 0 | 2 | 3 | — |
| `0x1C12` | 5 | 1 | 4 | 0 | 5 | `FUN_CODE_9ce8`, `FUN_CODE_9d53`, `set_1c12_2_and_68c_81`, `set_1c12_0_and_68c_83` |
| `0x1C13` | 3 | 1 | 2 | 0 | 3 | `FUN_CODE_9ce8`, `FUN_CODE_9d53` |
| `0x1C14` | 3 | 1 | 2 | 0 | 3 | `FUN_CODE_9ce8`, `FUN_CODE_9d53` |
| `0x1C36` | 1 | 1 | 0 | 0 | 1 | — |
| `0x1C37` | 1 | 1 | 0 | 0 | 1 | — |
| `0x1C38` | 1 | 1 | 0 | 0 | 1 | — |
| `0x1C01` | 16 | 1 | 15 | 0 | 16 | nine routines, §4 |
| `0x1C02` | 13 | 1 | 12 | 0 | 13 | eight routines, §4 — the classifier's two `read`s are not reads of this byte, §4.1 |
| `0x1C03` | 14 | 1 | 13 | 0 | 14 | nine routines, §4 |

The census agrees on the direction and not on the denominator, which is the
distinction the `0x086x` page's §3 draws: `ec/annotations/xdata-registers.csv`
counts **C-level occurrences**, the sweep counts **opcode sites**. For the
nine trio bytes the census reads `0 read` and all-`write` across the board
(`0x1C01` 14, `0x1C02` 11, `0x1C03` 12, `0x1C12` 5, `0x1C13` 3, `0x1C14` 3,
`0x1C36`/`0x1C37`/`0x1C38` 1 each), and the sweep's totals are 16/13/14/5/3/3
and 1/1/1. The two methods have different denominators and are not in
conflict; neither is derived from the other's columns.

**These nine bytes already had census rows.** The premise the issue starts
from — that the two existing methods "see these addresses only as
`XDATA_1C39`/`XDATA_1C3A` in `registers.yaml`" — is right about
`registers.yaml`, which carried no entry for any of the nine, and **wrong
about `xdata-registers.csv`**, which carried a row for all nine with the
bank-1 writer names above. The question was not invisible; it was never swept
by the one document that would have answered it, because
`xdata-086x-dispatch-sites.csv` is the `--csv` output over a literal
fifteen-address list (§1 of that page prints it) and none of the nine is in
it. This is recorded because "the tools agreed it was invisible" and "one
list was not swept" are different diagnoses, and only the second one is
actionable.

## 3. The positive: a second writer set for `0x1C12`-`0x1C14`, in bank 1

`stage_0862_0865_into_1c12_1c14` (bank0 `0xD2EF`) is the writer the page
document knows. It is not the only one. Two bank-1 routines hold the other
four sites, and they are **siblings of each other**: same guard, same low two
bytes, and one differing high byte.

`ec/decompiled/bank1/9CE8.asm`, at `0x9D00`:

```asm
9d00     74 99      mov      A, #0x99
9d02     90 1c 14   mov      DPTR, #0x1c14
9d05     f0         movx     @DPTR, A
9d06     74 00      mov      A, #0x0
9d08     90 1c 13   mov      DPTR, #0x1c13
9d0b     f0         movx     @DPTR, A
9d0c     74 48      mov      A, #0x48
9d0e     90 1c 12   mov      DPTR, #0x1c12
9d11     f0         movx     @DPTR, A
9d12     22         ret
```

reached only when `0x1C11 == 0` (`0x9CFA`-`0x9CFE`: `mov DPTR,#0x1c11 / movx
a,@dptr / jnz 0x9d16`), and `ec/decompiled/bank1/9D53.asm` at `0x9D91` is the
same eleven instructions with `0x9F` in place of `0x99`, behind the same
`0x1C11 == 0` test at `0x9D8B`.

So the trio has **three** writer sets, not one, and they write two different
shapes of value:

| writer | `0x1C12` | `0x1C13` | `0x1C14` | guard |
|---|---|---|---|---|
| `stage_0862_0865_into_1c12_1c14` (bank0 `0xD2EF`) | `0x0865` | `0x0862` | caller's `A` | none — unconditional, 21 bytes, no branch |
| `FUN_CODE_9ce8` (bank1 `0x9CE8`) | `0x48` | `0x00` | `0x99` | `0x1C11 == 0` |
| `FUN_CODE_9d53` (bank1 `0x9D53`) | `0x48` | `0x00` | `0x9F` | `0x1C11 == 0` |
| `set_1c12_2_and_68c_81` (bank1 `0x9E37`) | `0x02` | — | — | dispatch case 0 at `0x9E26` |
| `set_1c12_0_and_68c_83` (bank1 `0x9E4B`) | `0x00` | — | — | dispatch case 2 at `0x9E26` |

**This is the finding the page document's §8 table cannot hold**, because its
`0x1C12` row is not in the fifteen-address list it sweeps: `0x1C12` is
recorded there only as a *destination* inside §6's prose, and the census row
it does carry (`refs 5, 0 read, 5 write, 5 writers`) is not reconciled to
any site table anywhere. Two of the five writers are 21 bytes of constants
and three of the five are named in `ghidra-functions.csv` already — this is
prior art the page document never picked up, and it changes the answer to
"what writes the trio" from one routine to five.

**What the constants do not establish.** `0x48` and `0x00` recur as the low
two bytes of both seeds, and `0x48` also seeds `0x1C01` in four bank-1
routines (§4). `0x99`/`0x9F` differ in two bits and nothing here says why.
`0x1C11` has 14 direct sites — 5 reads and 9 writes, 6 in bank 0 and 8 in
bank 1 — and the two seeds take its `== 0` arm while the other arms of the
same two routines write `0xFF` to it, so the seeds look like a first-run fill
rather than a steady state. That is a shape, not a reading of the units, and
the trio's units stay unfixed: `XDATA_1C12` and friends are placeholders and
this change does not rename them (§5 of the page document's warning).

## 4. The `0x1C00`-block write side, and the two mislabelled `0x1C02` sites

`0x1C01`-`0x1C03` are the busiest of the eleven: **43 direct sites between
the three bytes and not one read.** All of them are inside bank 1, in nine
routines that also write `0x1C00`, `0x1C04` or `0x1C05`, which is why they
read as one block rather than three fields:

| routine | bank1 | what it writes into the `0x1C00` block |
|---|---|---|
| `gate_1c00_init_defaults` | `0xE237` | `0x1C01`=`0x48`, `0x1C02`=`0x01`, `0x1C03`=`0x9B` when `0x1C00 == 0` |
| `setup_1c00_block_with_arg_4c` | `0xC4D2` | `0x0975`→`0x1C03`, `0x0976`→`0x1C02`, `0x1C00`=`0xFF`, `0x1C01`=`0x4C` |
| `poll_1c00_status_up_to_100_cycles` | `0xC4F0` | as above with `0x1C01`=`0x48`, then polls `0x1C00` 100× |
| `setup_and_poll_1c00_block_with_arg_48` | `0xC54C` | `0x0975`→`0x1C03`, `0x0976`→`0x1C02`, `0x0978`→`0x1C04`, `0x0979`→`0x1C05`, `0x1C01`=`0x48` |
| `FUN_CODE_de3c` | `0xDE3C` | the three, from `R5` and a computed pointer |
| `FUN_CODE_e100` | `0xE100` | the three, from `R3`/`R4` |
| `FUN_CODE_e2d3` | `0xE2D3` | `0x1C02`←`0x03C4`, `0x1C04`←`0x1C05`←`0x03(A&0x7F)`, `0x1C03`=`0xA0`, `0x1C01`=`0x48` |
| `copy_03cd_03ce_03cf_to_1c02_1c04_1c05` | `0xE3B5` | `0x03CD`→`0x1C02`, `0x03CE`/`0x03CF`→`0x1C04`/`0x1C05`, `0x1C03`=`0xA0` or `0xA1` |
| `stage_1c00_block_from_code_table_indexed_03c4` | `0xE490` | CODE-table byte 2→`0x1C02`, table address's byte→`0x1C04`/`0x1C05`, `0x1C03`=`0xA0`, `0x1C01`=`0x48` |

Five of the nine write the literal `0x48` to `0x1C01` — the same constant
`0x48` that seeds `0x1C12` in §3. Six of the nine gate on `0x1C00 == 0`, and
`0x1C00` is a 35-site byte on its own. **No units are named here.** That
`0x48` recurs across both the `0x1C00` block and the `0x1C12` trio is a
co-occurrence of a constant, and a wrong unit baked into a symbol outlives
the note that would correct it, so nothing is renamed.

### 4.1 The two `0x1C02` sites the classifier calls reads

`0x1C02`'s thirteen sites are eleven `write x1` and two
`read x1, write x1`. Both of the two are **writes**, and the `movx a,@dptr`
the classifier counted as a read is of a different address. Only the listing
settles it, which is the point of `ec/README.md`'s instruction to read `.asm`
for anything load-bearing.

`ec/decompiled/bank1/E2D3.asm` at `0xE36E`, inside `FUN_CODE_e2d3`:

```asm
e36e     90 03 c4   mov      DPTR, #0x3c4
e371     e0         movx     A, @DPTR        ; <- the "read": this loads 0x03C4
e372     90 1c 02   mov      DPTR, #0x1c02   ; <- the site
e375     f0         movx     @DPTR, A        ;    0x1C02 <- 0x03C4
e376     54 7f      anl      A, #0x7f
e378     f5 82      mov      DPL, A
e37a     75 83 03   mov      DPH, #0x3
e37d     e0         movx     A, @DPTR        ; <- the second "read": 0x03(A&0x7F)
```

Neither `movx a,@dptr` reads `0x1C02`: the first reads `0x03C4` and the
second reads a **computed** address in `0x0300`-`0x037F` whose `DPH` is built
at `0xE37A`. So the corrected row is **`0x1C02`: 0 read, 13 write**, and the
`mov DPH,#0x3` at `0xE37A` is one of the eight `DPH` immediates §6.2 counts —
`0x1C02` gains a reader from that construction only if the accumulator
happens to hold a value that makes `0x03(A&0x7F)` equal `0x1C02`, which the
byte cannot express, since `0x03xx` is a different page from `0x1Cxx`.

`ec/decompiled/bank1/E490.asm` at `0xE4AE`, in
`stage_1c00_block_from_code_table_indexed_03c4`, is the same shape with the
source built out of CODE rather than out of `0x03C4`:

```asm
e4a3     93         movc     A, @A+DPTR      ; R4 = table byte 0 (destination high)
e4a7     93         movc     A, @A+DPTR      ; R3 = table byte 1 (destination low)
e4ab     93         movc     A, @A+DPTR      ; A  = table byte 2 (the value)
e4ac     60 53      jz       0xe501          ; a zero value leaves
e4ae     90 1c 02   mov      DPTR, #0x1c02   ; <- the site
e4b1     f0         movx     @DPTR, A        ;    0x1C02 <- the table's byte 2
e4b2     8c 83      mov      DPH, R4
e4b4     8b 82      mov      DPL, R3
e4b6     e0         movx     A, @DPTR        ; <- the "read": the XDATA byte at the table's own address
```

Here the second `movx` reads whatever XDATA address the **CODE table itself**
names — `0x1C04` and `0x1C05` are both set from it — and not `0x1C02`. The
routine advances `0x03C4` by 3 per call and wraps it at `0x78`, so it walks
`40` records; `ec/annotations/xdata-086x-dispatch.md` §6.2's byte-pair
argument (§6.3 below) is what bounds whether any of them names one of the
eleven bytes.

## 5. The sequential-walk exclusion

A consumer need not name an address: `inc dptr` walks into the bytes above a
site, and the sweep's `walks N consecutive bytes` column is where that shows.
Across **all 197 sites on the `0x1C00`-`0x1C3F` page, not one row's access
column reports a walk, and not one decoded window contains an `inc dptr`.**

`0x1C00` is the address that would have to walk into `0x1C01`-`0x1C03`, and
it has **35 direct sites** (3 bank0, 32 bank1) — the busiest on the page,
ahead of `0x1C04`'s 23 and `0x1C05`'s 17. None of the 35 decodes a walk.
`0x1C11` (14 sites) would have to walk into `0x1C12`-`0x1C14` and does not;
`0x1C35` (4 sites) and `0x1C38` (1 site) would have to walk into
`0x1C36`-`0x1C38` and neither does.

**What this does not exclude.** The walk is the tool's **linear
8-instruction** decode, which stops at the first control-flow instruction
(`trace_xdata_refs.py`'s `walk()`, and its own docstring). An `inc dptr`
placed after a branch is not decoded, so this bounds the walk to the straight
line immediately after a `MOV DPTR` and nothing further. A sequential walk
into the trios from a *computed* base is §6's subject, not this section's.

## 6. `0x0862` and `0x086D`: writerless by the direct method, and one conditional writer found

The page document describes both as "writerless rather than an input nobody
supplies", and §2 of that page is right that a direct `MOV DPTR` scan cannot
settle it. Four methods, each named with what it does not exclude. **Two of
the four turn up a writer, and it is the same store for both bytes.**

### 6.1 Register-indirect `movx @Ri` — not found

The opcode class is `0xF2`/`0xF3`, not `0xE6`/`0xE7`: on this map
`0xE6`/`0xE7` are `mov a,@Ri` / `mov @Ri,A` against **internal** RAM.
`xdata-0440-readers.md` §7.1 settles it and
`ec/tools/disasm8051.py:205-212` is the table. Over the EC window
`0x00000`-`0x17FFF`:

```console
$ python3 -c "
d=open('ec/firmware/GMxMGxx_11.800','rb').read()[0x00000:0x18000]
for n,ops in (('movx @Ri,a  (F2/F3)',(0xF2,0xF3)),('movx a,@Ri  (E2/E3)',(0xE2,0xE3)),
              ('mov a,@Ri   (E6/E7)',(0xE6,0xE7)),('mov @Ri,a   (F6/F7)',(0xF6,0xF7))):
    print(f'  {n:22}', '  '.join(f'0x{o:02X}={sum(1 for b in d if b==o)}' for o in ops))"
  movx @Ri,a  (F2/F3)    0xF2=84  0xF3=70
  movx a,@Ri  (E2/E3)    0xE2=190  0xE3=125
  mov a,@Ri   (E6/E7)    0xE6=422  0xE7=183
  mov @Ri,a   (F6/F7)    0xF6=199  0xF7=78
```

| step | count |
|---|---:|
| `0xF2`/`0xF3` byte occurrences in the EC image | 154 |
| on an instruction boundary in an exported `.asm` listing | 21 |
| with `mov R0/R1,#0x0862` or `#0x086D` anywhere in the same listing | **0** |
| with `mov R0/R1,#` any of the eleven `0x1Cxx` bytes in the same listing | **0** |

**Excluded:** any `movx @Ri,a` in code no exported listing covers, and any
pointer register set from memory or a subroutine rather than an immediate.

### 6.2 Computed DPTR — **one page-`0x08` writer found**

> **CORRECTION (2026-09-25, issue #250) to `xdata-0440-readers.md` §7.2,
> whose third row reads "`addc a,#imm` immediately followed by `mov DPH,A` /
> `mov DPL,A` | **0**", and whose second row depends on it.** The count is
> not 0. A byte-level scan of the EC window finds **64** `34 xx f5 83`
> sequences (`addc A,#imm` then `mov DPH,A`) and **0** of the `DPL` form, of
> which **58** are immediately preceded by `clr A` — so the high byte is the
> immediate exactly, with no carry — and **exactly one** of the 64 builds
> page `0x08`, which is the page `0x0862` and `0x086D` live on. The
> consequence runs the other way from the row it corrects: the predecessor
> document's §7.2 exclusion, "a DPTR built from a register or memory value
> that reaches `0x0440` without any `DPH`/`DPL` immediate in the preceding 12
> instructions", is a **real and open** hole rather than a closed one, and
> one instance of it is a store. The old row stays visible here for the
> reason the rest of the tree's corrections do.

The 64 are enumerable and the interesting one is unambiguous. Scanning the
whole EC window for the byte pattern `34 xx f5 83`, and separating the sites
by the value of `xx`:

| `xx` | sites | `xx` | sites | `xx` | sites |
|---|---:|---|---:|---|---:|
| `0x00` | 11 | `0x0B` | 4 | `0x2A` | 2 |
| `0x02` | 1 | `0x0D` | 7 | `0x3A` | 6 |
| `0x08` | **1** | `0x0E` | 1 | `0x49` | 6 |
| `0x09` | 1 | `0x0F` | 8 | `0x55` | 1 |
| `0x10` | 2 | `0x21` | 1 | `0x63`/`0x64`/`0x6B`/`0x6C`/`0x6D`/`0x6E` | 1/2/2/3/2/2 |

**No site builds page `0x1C`** — `0x1C` does not appear as `xx` at all — so
the ten `0x1Cxx` bytes are not reachable by this construction, which is a
stronger negative than the page document's and is worth stating in the form
it takes. The other 63 build pages `0x00`, `0x02`, `0x08`, `0x09`, `0x0B`,
`0x0D`, `0x0E`, `0x0F`, `0x10`, `0x21`, `0x2A`, `0x3A`, `0x49`, `0x55`,
`0x63`, `0x64`, `0x6B`, `0x6C`, `0x6D` and `0x6E` — the twenty distinct
values in the table above, and nothing else.

The one that matters, `ec/decompiled/bank0/8294.asm` at `0x8357` — a
**store**, and the same two instructions for both bytes:

```asm
8354     90 0a 56   mov      DPTR, #0xa56
8357     e0         movx     A, @DPTR      ; A = XDATA 0x0A56
8359     25 e0      add      A, ACC        ; A = 2*A
835b     24 d0      add      A, #0xd0      ; A = 2*A + 0xD0
835d     f5 82      mov      DPL, A        ; DPL = (2*A + 0xD0) mod 256
835f     e4         clr      A
8360     34 08      addc     A, #0x8       ; A = 0x08, CY = 0
8362     f5 83      mov      DPH, A        ; DPH = 0x08  <- the only page-0x08 construction
8364     ee         mov      A, R6
8365     f0         movx     @DPTR, A      ; XDATA[0x08DPL]      = R6
8366     a3         inc      DPTR
8367     ef         mov      A, R7
8368     f0         movx     @DPTR, A      ; XDATA[0x08DPL + 1]  = R7
```

`DPH` is hard `0x08` and `DPL = (2·XDATA[0x0A56] + 0xD0) mod 256`, which is
**always even** — so the store always lands on an even/odd **pair** on the
`0x0800` page. Solving `2·A + 0xD0 ≡ DPL (mod 256)` for the four `0x086x`
bytes this issue is about:

| target | role in the pair | reached when `XDATA[0x0A56]` is |
|---|---|---|
| `0x0862` | first, at `DPL`=`0x62` | `0x49` or `0xC9` |
| `0x0863` | second, at `DPL`=`0x62` | `0x49` or `0xC9` |
| `0x0864` | first, at `DPL`=`0x64` | `0x4A` or `0xCA` |
| **`0x086D`** | **second, at `DPL`=`0x6C`** | **`0x4E` or `0xCE`** |

So **both `0x0862` and `0x086D` have a writer the direct scan cannot see**,
and it is one store: `FUN_CODE_8294` at bank0 `0x8365`. `0x0862` and `0x0863`
are written together, which is the pair the case-`0x36`/`0x37`/`0x38`/`0x39`
handlers stage into `0x1C39`/`0x1C3A` — so the same store supplies both the
`0x1C12`/`0x1C36` trios' source byte and the `0x1C39`/`0x1C3A` pair's staging
source. `0x086D` is written as the second byte of a pair at `0x086C`/`0x086D`,
and `0x086C` is one of the three results `compute_level_blocks_086b_086c_086e`
computes, so this store can overwrite a computed result.

**What this is not.** The gate is `XDATA[0x0A56]` holding one of two specific
values, and **no observation of that byte exists in this repository** — the
live read is a human's step, written down in §8 and not claimed. A conditional
store whose condition has never been seen is not a claim that the byte is
ever written; per CLAUDE.md the same standard as a readback applies, and a
readback is not a behavioural test either. Both bytes stay
`present-untested` and the page document's §2 sentence is corrected in place
rather than left to imply there is no writer at all.

**The residual, named.** The six `34 xx f5 83` sites **not** preceded by
`clr A` take their high byte from whatever `A` already held, so the "exactly
the immediate" argument does not cover them. All six are in the common area —
four carrying `xx`=`0x0D` after a `lcall 0x2A7B` (`0x2266`, `0x2270`, `0x2278`,
`0x22DF`) and two carrying `xx`=`0x2A` with `A` from `R6` (`0x28EF`, `0x2912`)
— and `0x2266` and `0x28EF` are confirmed real instructions against the raw
image (`mov a,0x66 / movx @dptr,a` at `0x226A`-`0x226C` stores through the
computed pointer). Their `A` is a subroutine return value or `R6` whose range
this method does not establish, so **a store through one of the six reaching
either `0x0862`/`0x086D` or any `0x1Cxx` byte is not excluded.** The
generalisation is issue #110's: computed-DPTR visibility inside
`trace_xdata_refs.py`. It stays open, and this document leads its follow-up
list with it.

**Excluded:** a DPTR built inside a callee and handed back, and any
construction other than the `addc`-into-`DPH` form — a `mov DPH,A` after a
`mov A,imm`, a `pop`, or a `swap` is not enumerated by the pattern above.

### 6.3 CODE-table copy class — not found, bounded by a whole-dump byte scan

`code_table_scatter_to_xdata` (bank1 `0xA530`) writes a CODE table's third
byte to the XDATA address formed by its first two, so a record naming
`0x0862` **must** contain the contiguous byte pair `08 62` in the image.
Scanning all 256 KiB for that pair and classifying every hit:

```console
$ python3 -c "
d=open('ec/firmware/GMxMGxx_11.800','rb').read()
for pair,name in ((b'\x08\x62','0x0862'),(b'\x08\x6d','0x086D')):
    print(name, [f'0x{i:05X}' for i in range(len(d)-1) if d[i:i+2]==pair])"
0x0862 ['0x00993', '0x0D2DF', '0x0D2F4', '0x0D309', '0x25EAD', '0x27F58']
0x086D ['0x09D2A', '0x09D52', '0x26B60']
```

| hit | region | what it actually is |
|---|---|---|
| `0x0D2DF`, `0x0D2F4`, `0x0D309` | bank0 | the three `mov DPTR,#0x0862` reads in the three staging routines |
| `0x25EAD`, `0x27F58` | PD image | `mov DPTR,#0x0862` against the **PD image's own** XDATA map — a different byte (§6.1 of the page document) |
| **`0x00993`** | common | **not an XDATA operand at all** — see below |
| `0x09D2A`, `0x09D52` | bank0 | the two `mov DPTR,#0x086D` reads in `gate_06e6_442_then_sync_046a_from_086b` |
| `0x26B60` | PD image | the page substitution bytes of a paged `ajmp 0x6908` — a **CODE** address in the PD image |

The `0x00993` hit is the one that would have made a naive scan report a
writer. `ec/decompiled/common/0979.asm` reads it as
`FUN_CODE_0979`'s own tail:

```asm
0987     24 f2      add      A, #0xf2
0989     60 13      jz       0x099e
098b     24 12      add      A, #0x12
098d     70 12      jnz      0x09a1
098f     02 08 59   ljmp     0x0859
0992     02 08 62   ljmp     0x0862
0995     02 08 6b   ljmp     0x086b
```

`0x0993` is the low byte of a **`ljmp 0x0862` operand** — a bank-0 CODE
address in a five-way dispatch on `R7`, not an XDATA address. This is the
same trap §4 of the page document names for the `0xD14B` case table: a linear
disassembly of data is not a reading of the data, and a `MOV DPTR,#imm` byte
pattern is not a reading of a `MOV DPTR`.

**So: no CODE-table record anywhere in the 256 KiB dump names `0x0862` or
`0x086D` as a destination.** That is a whole-image bound, not a per-caller
one, and it needs no per-caller table decoding: all nine byte-pair hits are
accounted for above. The other init-time table writer,
`init_xdata_from_code_table_64fd` (bank0 `0xBFDE`, 90 three-byte records at
CODE `0x64FD`), is inside this bound for free — its 90 records' destinations
are all in `0x1600`-`0x16F0` per `xdata-0440-readers.md` §7.3, and no
`08 62`/`08 6D` pair appears among them.

**Excluded:** a table walked by an unexported caller of a helper whose name
does not say it is a table copy, and a record built at runtime rather than
stored in the image.

### 6.4 The `DPTR`-handoff class — no caller found, which is the larger gap

`xdata-0440-readers.md` §7.5 names seven parameterised "zero N bytes at
DPTR" helpers — bank0 `0xB963`, `0xEDE1`, `0xEE58`, `0xF07C`, `0xF099`,
`0xF17B`, `0xF4AD` — and records that a caller handing one of them
`0x0440` would be invisible. Checking `ec/annotations/bank-call-targets.csv`
for callers of any of the seven:

| target | recorded call sites |
|---|---:|
| `0xB963`, `0xEDE1`, `0xEE58`, `0xF07C`, `0xF099`, `0xF17B`, `0xF4AD` | **0 each** |

**None of the seven is the target of any recorded direct `lcall`/`ljmp` in
this image.** That is a wider blind spot than the one the predecessor
document describes, and it is worth stating as such: whatever reaches these
helpers does so through a path this method cannot see at all, so the
handoff class is not narrowed by this pass, it is only bounded. The seven
`code_table_scatter_to_xdata` call sites (`0x82C9`, `0x82FD`, `0x83B7`,
`0x841D`, `0xC740`, `0xC7AC`, `0xC7F2`) all pass a literal `DPTR`, and
§6.3's byte-pair bound settles their record content regardless.

**Excluded:** everything a `DPTR` handoff can carry, and every helper reached
through a function-pointer table or a return address.

## 7. What consumes the eleven bytes: the method-by-method negatives

Each row is a method, its count, and **what it does not exclude**. The
precedent is `xdata-0440-readers.md` §7's shape and `docs/findings.md` §4c.

| method | result for the eleven bytes | what it does not exclude |
|---|---|---|
| direct `MOV DPTR,#imm16` (`trace_xdata_refs.py`, 67 rows) | **0 read sites** for the nine trio bytes; 4 read sites for `0x1C39`/`0x1C3A`, all inside `dispatch_on_0860`'s own block | a DPTR built from a register, memory, ACC or a stack pop; a table lookup; a `DPTR` handoff |
| sequential `inc dptr` walk from a base below (the 197 `0x1C00`-page sites) | **0** windows decode a walk; `0x1C00`'s 35 sites none | a walk past a branch, since the walk stops at the first control-flow instruction; a walk from a computed base |
| `movx @Ri,a` register-indirect (154 bytes, 21 on instruction boundaries) | **0** with `R0`/`R1` preloaded to any of the eleven | any `movx @Ri,a` in code no listing covers; a pointer set from memory or a subroutine |
| `addc A,#imm ; mov DPH,A` computed DPTR (64 sites, 58 after `clr A`) | **0** build page `0x1C`; the one page-`0x08` site cannot reach page `0x1C` at all | the six non-`clr A` sites of §6.2's residual, whose `A` is a return value or `R6`; a `mov DPH,A` after `mov A,imm` or a `pop` |
| CODE-table copy class (whole-dump `08 62`/`08 6D` byte-pair scan) | **0** records name any of the eleven as a destination | a table walked by an unexported caller; a record built at runtime |
| `DPTR`-handoff class (7 parameterised helpers) | **0** recorded callers, which bounds nothing | everything a handoff can carry — the largest single gap in this table |
| host: DSDT `ECMG` fields (§8.1) | **0** fields and **0** literals | anything not in the committed `dsdt.dsl` |
| host: Windows `ECSpec.cs` (§8.2) | **0** constants | the anti-tamper-obscured `GCUService.exe` bodies; a fresh `ilspycmd` run |
| host: BIOS `0x62`/`0x66` index-data port (§8.3) | **structurally cannot** address page `0x1C` | anything in a raw BIOS image that is not in the committed decompiles |
| computed DPTR inside `trace_xdata_refs.py` | **not attempted** — issue #110's work | named as the leading follow-up (§9) rather than claimed |

**So the `0x1C36`-`0x1C38` negative, in its sharpest available form:** the
only site each of those three bytes has, in any image, is the routine that
writes it — `stage_0862_0865_into_1c36_1c38`, the 21-byte copy at bank0
`0xD304`. Not "no consumer was found", but "one writer and nothing else, by
each of the nine methods above". `0x1C36`-`0x1C38` are the three bytes this
issue most clearly cannot resolve, and they are the right first target for
whatever method comes next.

## 8. Host visibility — the cheapest wrong guess, ruled out

"The consumer is the host" is the most likely wrong answer to this question,
and ruling it out costs three greps.

### 8.1 DSDT — no field, no literal

`evidence/acpi/dsdt.dsl` declares
`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`, and its field
list proves ECMG offsets are EC XDATA addresses with no base offset (`CPTM` at
`Offset (0x43E)`, `VGAT` at `Offset (0x44F)`, per `xdata-0440-readers.md`
§8.1). There is **no `Offset (0x1c..)` line anywhere in the file** — the
count of that pattern is **0** — and the literals `0x1c01`, `0x1c02`,
`0x1c03`, `0x1c12`, `0x1c13`, `0x1c14`, `0x1c36`, `0x1c37`, `0x1c38`,
`0x1c39`, `0x1c3a`, `0x0862` and `0x086D` each appear **0** times. The
general `ECRW` method of §8.1 there is defined and uncalled, and is the
"uncalled in the DSDT is not unreachable" case: an externally-invoked ACPI
entry point could pass any 16-bit address, and the only thing that says it
does not is §8.2 and §8.3.

### 8.2 Windows — no address constant, and the anti-tamper boundary

`windows/decompiled/v3.1.6.0/ECSpec.cs` is a flat decimal `const ushort`
table. **None of the thirteen literals appears in it**, and no `const ushort`
is declared in the `7185`-`7229` decimal window that `0x1C11`-`0x1C3D` falls
in. The battery-info cluster the predecessor document maps runs
`ADDR_EC_BIF_DV_BYTE1` = 1032 through `ADDR_EC_BST_BPV_BYTE2` = 1081
(`0x0439`, `:215`) and the next declared address jumps to 1190 (`:217`), so
the `0x1Cxx` page is a gap in the host's own address table, not a range the
table skips over.

`windows/native/ACPIDriver.sys.analysis.md:279-302` records that the Windows
ACPI driver marshals a 16-bit address into the DSDT's general `ECRW`, so
Windows *could* write these bytes and no committed caller does.

**Excluded:** the anti-tamper-obscured `GCUService.exe` bodies that do not
decompile (`windows/antitamper/README.md`) — their address constants would be
in the managed decompiles, which are covered — and a fresh `ilspycmd` run.

### 8.3 BIOS — structurally cannot reach either page

The BIOS reaches the EC through the ITE `0x62`/`0x66` index-data port pair,
and its write sequence is `0xA3` handshake → `0xA2` **address byte** → `0xA5`
data byte. The address argument is typed `undefined1` in
`bios/decompiled/OemApControlDxe.c` (`FUN_00000a14`), i.e. 8-bit. The
distinct address bytes the module actually passes are:

```console
$ python3 -c "
import re
t = open('bios/decompiled/OemApControlDxe.c', errors='replace').read()
print(' '.join(sorted({m.group(2) for m in re.finditer(
    r'FUN_00000a(14|74)\(\s*[^,]+,\s*[^,]+,\s*(0x[0-9a-fA-F]+)\s*,', t)})))"
0x3c 0x65 0x66 0x6c 0x6d 0x6e 0x82 0xa3
```

(`0xA3` is the handshake marker, not an address.) The highest EC address byte
written is `0x82` and **`0x1C` is not in the set at all**, so the BIOS cannot
address page `0x1C00` by this module; and `0x0862`/`0x086D` would need a
16-bit address or a page select, and there is no page-select helper in the
module. Tree-wide, `0x862` and `0x86d` have **0** hits in
`bios/decompiled/`.

**Excluded:** anything in a raw firmware image that is not in the committed
decompiles, and a partial decompile. Per-module copies of the `0x62`/`0x66`
helper mean a name-based per-file summary is incomplete, but the tree-wide
grep covers every module.

## 9. What this changes, and what it leaves open

- **The nine `0x1Cxx` bytes are recorded** in `ec/annotations/registers.yaml`
  at `status: present-untested` — **an entry existing, not a status moving** —
  with the three count keys read out of the committed CSV, and
  `ec/ghidra/xdata-symbols.csv` regenerated from them by
  `ec/tools/gen_xdata_symbols.py`, never by hand. The PR body says this in
  the same words so a later follow-up pass cannot misread the diff as a
  promotion.
- **The four `0x086x` bytes' notes are corrected** in place. `XDATA_0862` and
  `XDATA_086D` said "this method found no writer"; both now name the
  conditional computed-DPTR writer of §6.2 **and keep the "not found by this
  method" wording for the direct scan**, because that is what remains true of
  it. `XDATA_1C39` and `XDATA_1C3A` gain the §2 per-byte result and the
  pointer here.
- **No name is coined for the block.** §5 of the page document's warning
  stands: a wrong unit in a symbol outlives the note that would correct it.
  The nine new symbols are `XDATA_1Cnn` placeholders, the nine existing names
  do not change, and the `0x1C00`-block routines keep the names their own
  listings already support.
- **`ec/annotations/xdata-086x-dispatch.md` §2 and §8 change.** The `0x0862`
  row's `write 0` and the `0x086D` row's `write 0` are the *direct-scan*
  counts and stay; §2's "writerless" sentence gains the §6.2 correction, in
  place, with the old wording visible.
- **Three new rows and one corrected** in `ec/annotations/ghidra-functions.csv`
  — `0x9CE8`, `0x9D53`, `0xE2D3` new, `0xE490` corrected — each with a
  comment, a `type` from the closed list, a non-empty `evidence` path and
  `basis: hand-decoded`. All four addresses resolve to existing exported
  functions in the committed project, so none of them needs
  `--mode rebuild-project`. **Nine** of the 43 `0x1C01`-`0x1C03` bank-1 sites
  have **no enclosing export** — `0x9919`, `0x997D` and `0xE764` for `0x1C01`;
  `0x9913`, `0x9977` and `0xE74C` for `0x1C02`; `0x990D`, `0x9971` and
  `0xE75E` for `0x1C03`. They stay named by address here rather than forced,
  which is the same position §9 of the page document records for the six
  unseeded case handlers.
- **`xdata-0440-readers.md` §7.2 is corrected in place** (§6.2's blockquote):
  its `addc`-into-`DPH` count of 0 is not 0, and the correction runs in the
  direction that opens a hole rather than closing one. The nine-versus-eight
  discrepancy in the same section — its ninth `mov DPH`/`mov DPL` immediate
  is at PD `0x0E1B`, `ec/decompiled/pd/0E54.asm`, not the EC common area, so
  the EC window holds **eight** — is recorded there too.
- **The six `0xD173`-`0xD24E` case handlers are still unseeded.** Two of the
  ten `0x1C39`/`0x1C3A` sites (`0xD26F`, `0xD277`) sit in them and two more
  (`0xD22D`, `0xD253`) do not; the `.asm` listings cover the same bytes, so
  this is not required here, and seeding them is a `--mode rebuild-project`
  change that cannot merge alongside anything else. That issue stays open.
- **Follow-ups this opens**, in rough value order:
  1. **issue #110**, general computed-DPTR visibility in
     `trace_xdata_refs.py` — the leading item. §6.2 found the one page-`0x08`
     construction by a byte pattern, and the six non-`clr A` sites of its
     residual are exactly the shape a tool change would settle;
  2. the six non-`clr A` `addc`-into-`DPH` sites (`0x2266`, `0x2270`,
     `0x2278`, `0x22DF`, `0x28EF`, `0x2912`) and what `A` holds at each —
     the only remaining writer candidate this document names;
  3. **a live read of `XDATA[0x0A56]`** at a moment when `0x0862` or
     `0x086D` is expected to move, which is the only thing that settles
     whether §6.2's conditional store ever fires. A human with the machine;
     not run here;
  4. the seven parameterised "zero N bytes at DPTR" helpers of §6.4, none of
     which has a recorded caller — the largest single gap in the writer hunt;
  5. seeding the six `0xD173`-`0xD24E` case handlers, and the three
     unexported bank-1 routines that hold the rest of the `0x1C01`-`0x1C03`
     sites (needs a rebuild);
  6. the `0x1C00` byte itself: 35 direct sites, the busiest on the page, and
     it gates six of the nine `0x1C01`-`0x1C03` writers. It has no
     `registers.yaml` entry, and it is the address the next pass should read
     the same way this one read the trios.
