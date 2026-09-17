# PD `0x38` constructions: five manual consumer traces (#77)

This follows the four multiplication contexts and the independently entered
add-only suffix in [pd-index-geometry.md](pd-index-geometry.md) §8.4. All five
have identifiable **XDATA** consumers in the decoded paths. This is static
analysis of committed firmware, not evidence that any path executed or that
these bytes have an identified record meaning. No hardware test ran.

The census itself is unchanged: its construction-only classifications still
correctly describe the bounded tool. It does not admit consumer-only helpers
or recover DPTR stack saves. The manual evidence below is not a new global
consumer count and is not inserted into either generated access CSV.

## 1. Input, reproduction and framing

Input: `ec/firmware/GMxMGxx_11.800`, 262,144 bytes, SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`.
The existing `trace_xdata_refs.py` map places PD at file `[0x20000,0x30000)`;
file `0x20040` contains `ITE8850-PD`. For **every instruction address below**,
file offset = runtime address + `0x20000`. XDATA operand addresses do not
use that conversion: they are addresses in the PD program's data space.

Independent decoding used **radare2 5.5.0** on a temporary flat PD image.
Run from the repository root:

```sh
sha256sum ec/firmware/GMxMGxx_11.800
r2 -v
dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd-77.bin bs=65536 skip=2 count=1
r2 -a 8051 -e scr.color=0 -q -c \
  's 0xb28a; pd 5; s 0xb2ae; pd 8; s 0xb2b2; pd 6; s 0xb2d3; pd 8; s 0xb263; pD 11; s 0x0fcb; pd 12; s 0x0faf; pd 12; s 0x1041; pd 12; s 0x10bc; pd 7' \
  /tmp/pd-77.bin
r2 -a 8051 -e scr.color=0 -q -c \
  's 0x4d89; pD 45; s 0x4dd2; pD 28; s 0x4e84; pD 83' \
  /tmp/pd-77.bin
```

The listings in §§2–4 compact adjacent instructions onto one line; byte
strings are in execution order. The firmware, not r2's synthetic memory-hint
comments, is the evidence. `pD` counts bytes; `pd` counts instructions.

Framing is conditional, not a recovered whole-image call graph. In particular,
a linear decode through nearby calls to `0x104D` mistakes inline arguments for
instructions. The framing check and its reproduction commands are in §5.
Neither backward convergence nor a raw branch-byte match proves execution.

## 2. Constructions and complete short consumers

### 2.1 Immediate bases

| runtime / file | bytes | instructions |
|---|---|---|
| `B2AE / 2B2AE` | `75f038 a4` | MOV B,#38; MUL AB |
| `B2B2 / 2B2B2` | `2446 f582 e4 3409 f583 22` | ADD A,#46; MOV DPL,A; CLR A; ADDC A,#09; MOV DPH,A; RET |
| `B2D3 / 2B2D3` | `75f038 a4` | MOV B,#38; MUL AB |
| `B2D7 / 2B2D7` | `2476 f582 e4 3409 f583 22` | ADD A,#76; MOV DPL,A; CLR A; ADDC A,#09; MOV DPH,A; RET |
| `B28A / 2B28A` | `900832 e0 75f038 a4 22` | MOV DPTR,#0832; MOVX A,@DPTR; MOV B,#38; MUL AB; RET |

The multiply instructions are runtime `0xB2B1` (file `0x2B2B1`) and
`0xB2D6` (file `0x2B2D6`). Define `L(i) = low8(i×0x38)`, where
`low8(x) = x & 0xFF`. The returned pointers are:

- Entry `0xB2AE`: `P = 0x0946 + L(A_entry)`.
- Entry `0xB2D3`: `P = 0x0976 + L(A_entry)`.
- Entry **`0xB2B2`**: `P = 0x0946 + A_entry`. This entry executes **no MUL**.

CLR A discards the product's high byte B but preserves carry from ADD A,#lo.
ADDC therefore retains low-base carry. No R0–R7 register is written by these
three construction entries. `0xB28A` returns A=low8(XDATA[0832]×38), with the
high product in B, but leaves DPTR at `0x0832`; it is not itself a pointer
construction. All address expressions here are modulo `0x10000`.

### 2.2 Four-byte reader and writer (complete through RET)

| runtime / file | bytes | instructions / effect relative to entry pointer P |
|---|---|---|
| `0FAF / 20FAF` | `e0 fc a3` | MOVX A,@DPTR; MOV R4,A; INC DPTR — read P |
| `0FB2 / 20FB2` | `e0 fd a3` | MOVX A,@DPTR; MOV R5,A; INC DPTR — read P+1 |
| `0FB5 / 20FB5` | `e0 fe a3` | MOVX A,@DPTR; MOV R6,A; INC DPTR — read P+2 |
| `0FB8 / 20FB8` | `e0 ff 22` | MOVX A,@DPTR; MOV R7,A; RET — read P+3 |
| `1041 / 21041` | `ec f0 a3` | MOV A,R4; MOVX @DPTR,A; INC DPTR — write P |
| `1044 / 21044` | `ed f0 a3` | MOV A,R5; MOVX @DPTR,A; INC DPTR — write P+1 |
| `1047 / 21047` | `ee f0 a3` | MOV A,R6; MOVX @DPTR,A; INC DPTR — write P+2 |
| `104A / 2104A` | `ef f0 22` | MOV A,R7; MOVX @DPTR,A; RET — write P+3 |

Both return DPTR=P+3. `0x0FAF` overwrites R4–R7, not R3; `0x1041` preserves
those registers. The stores themselves are `0x1042/45/48/4B`, not the preceding
MOV A,Rn instructions. These are MOVX data transfers, not CODE reads.

### 2.3 Full-product additive helper

| runtime / file | bytes | instructions |
|---|---|---|
| `10BC / 210BC` | `a4 2582 f582 e5f0 3583 f583 22` | MUL AB; ADD A,DPL; MOV DPL,A; MOV A,B; ADDC A,DPH; MOV DPH,A; RET |

This helper adds the **full** A×B product to the incoming DPTR; MOV A,B retains
the multiplication high byte. It preserves R0–R7, and does no memory access.
Thus the `×2` below is not truncated like the outer `×0x38` term.

## 3. Five contexts and outcomes

`X_t[addr]` below denotes the byte at a particular decoded MOVX load, not a
claim about a live value or that separate reads return the same byte.

| caller runtime / file → entry | construction and index provenance on this path | consumer / terminal outcome |
|---|---|---|
| `4D9B / 24D9B → B2AE` | `P=0946+L(i)`, i loaded from XDATA[0832] at 4D8C into R7; intervening B263/0FCB preserve R7 | 4D9E calls 0FAF: four XDATA reads P..P+3 into R4..R7; returns to 4DA1 with DPTR=P+3 |
| `4DE8 / 24DE8 → B2AE` | `P=0946+L(i)`, i loaded at 4DD5 into R3; 10BC/B267/0FAF preserve R3 | 4DEB calls 1041: four XDATA writes P..P+3 from R4..R7; returns to 4DEE with DPTR=P+3 |
| `4E9B / 24E9B → B2D3` | `P=0976+L(i)`, i is A from 4E99 XDATA[0832], also saved in R6; j is R7 from 4E8C XDATA[083A] | 4EA2 adds 2×j; 4EA5/4EA8 read P+2j and P+2j+1; branch at 4EAA, zero arm replaces DPTR at 4EAF |
| `4EB8 / 24EB8 → B2D3` | `P=0976+L(i)`, i is preserved R6 from 4E99; saved DPTR survives stack detour; k is a fresh XDATA[083A] read at 4EC2 | 4ECA adds 2×k; 4ECE/4ED1 write P+2k and P+2k+1; DPTR overwritten with 083B at 4ED3 |
| `4DAA / 24DAA → B2B2` | locally `P=0946+A`; preceding 4DA7→B28A separately supplies A=L(i), i from B28D XDATA[0832] | 4DAD calls 0FAF: four XDATA reads P..P+3; returns to 4DB0 with DPTR=P+3; suffix itself still executes no multiply |

These are outcomes for the named paths, not a complete caller inventory. The
reader/writer returns are sufficient consumer outcomes; subsequent uses of
the loaded values are not followed to a record meaning.

### 3.1 First reader, suffix reader, and four-byte writer

| runtime / file | bytes | instructions |
|---|---|---|
| `4D89 / 24D89` | `900832 e0 ff 75f060 900491` | MOV DPTR,#0832; MOVX A,@DPTR; MOV R7,A; MOV B,#60; MOV DPTR,#0491 |
| `4D94 / 24D94` | `12b263 120fcb ef 12b2ae 120faf` | LCALL B263; LCALL 0FCB; MOV A,R7; LCALL B2AE; LCALL 0FAF |
| `4DA1 / 24DA1` | `c3 120f0e 6047` | CLR C; LCALL 0F0E; JZ 4DEE |
| `4DA7 / 24DA7` | `12b28a 12b2b2 120faf` | LCALL B28A; LCALL B2B2; LCALL 0FAF |
| `4DB0 / 24DB0` | `e4 12b24c 601c` | CLR A; LCALL B24C; JZ 4DD2 |
| `4DD2 / 24DD2` | `900832 e0 fb 75f060 900491` | MOV DPTR,#0832; MOVX A,@DPTR; MOV R3,A; MOV B,#60; MOV DPTR,#0491 |
| `4DDD / 24DDD` | `1210bc eb 12b267 120faf eb 12b2ae 121041` | LCALL 10BC; MOV A,R3; LCALL B267; LCALL 0FAF; MOV A,R3; LCALL B2AE; LCALL 1041 |

The R7 loaded at `0x4D8D` really survives the earlier helpers: `0xB263`
adds A×B through `0x10BC`, then adds the page term using R7; `0x0FCB`
reads into R0–R3, **not** R4–R7. Its complete bytes are in §5. The later
`0x0FAF` does overwrite R7, but only after B2AE has consumed the index.

For the writer, `0xB267` adds `0x100×low8(2×A)` to DPTR, preserving R3.
Along with 10BC and 0FAF, none of these calls invalidates the R3 source at
4DD6. R4–R7 at 4DEB are the four bytes read by 4DE4→0FAF from
`Q = 0x0491 + i×0x60 + 0x100×low8(2×i)` (modulo 65536).
B2AE preserves them while constructing the destination. This establishes a
four-byte copy on this path, not a name or width for a record.

The suffix caller does not reuse an assumed earlier index. B28A performs a
fresh XDATA load. Its MUL produces the supplied A; B2B2 only adds that A to
0946. Counting B2B2 as executing the MUL at B2B1 would erase the independent
entry that the census deliberately preserves.

### 3.2 Two-byte reader and stack-detour writer

| runtime / file | bytes | instructions |
|---|---|---|
| `4E84 / 24E84` | `e4 90083a f0` | CLR A; MOV DPTR,#083A; MOVX @DPTR,A |
| `4E89 / 24E89` | `90083a e0 ff c3 9402 4003 024fe1` | MOV DPTR,#083A; MOVX A,@DPTR; MOV R7,A; CLR C; SUBB A,#02; JC 4E96; LJMP 4FE1 |
| `4E96 / 24E96` | `900832 e0 fe 12b2d3` | MOV DPTR,#0832; MOVX A,@DPTR; MOV R6,A; LCALL B2D3 |
| `4E9E / 24E9E` | `75f002 ef 1210bc` | MOV B,#02; MOV A,R7; LCALL 10BC |
| `4EA5 / 24EA5` | `e0 fc a3 e0 4c 6003 024f53` | MOVX A,@DPTR; MOV R4,A; INC DPTR; MOVX A,@DPTR; ORL A,R4; JZ 4EAF; LJMP 4F53 |
| `4EAF / 24EAF` | `900834 e0 fc a3 e0 fd` | MOV DPTR,#0834; MOVX A,@DPTR; MOV R4,A; INC DPTR; MOVX A,@DPTR; MOV R5,A |
| `4EB7 / 24EB7` | `ee 12b2d3 c083 c082` | MOV A,R6; LCALL B2D3; PUSH DPH; PUSH DPL |
| `4EBF / 24EBF` | `90083a e0 d082 d083` | MOV DPTR,#083A; MOVX A,@DPTR; POP DPL; POP DPH |
| `4EC7 / 24EC7` | `75f002 1210bc` | MOV B,#02; LCALL 10BC |
| `4ECD / 24ECD` | `ec f0 a3 ed f0` | MOV A,R4; MOVX @DPTR,A; INC DPTR; MOV A,R5; MOVX @DPTR,A |
| `4ED2 / 24ED2` | `e4 90083b f0` | CLR A; MOV DPTR,#083B; MOVX @DPTR,A |

B2D3 and 10BC both preserve R6 and R7. From 4E99 through the zero arm at
4EAF, only R4 and R5 are replaced; thus R6 at 4EB7 still holds that outer
index. The earlier reader's second byte is loaded into A, **not R6**.

PUSH DPH then PUSH DPL uses the internal 8051 stack. POP DPL then POP DPH
restores the saved construction, assuming the ordinary balanced stack
semantics of the decoded path. There is no intervening call in this detour.
The temporary DPTR=083A is distinct from the saved P; its MOVX loads k into
A. POPs do not overwrite A. 10BC therefore receives the restored P and k×2,
not the temporary pointer and not a presumed preserved R7. The stores take
R4=XDATA[0834] and R5=XDATA[0835] from 4EB2/4EB5; neither helper clobbers them.
The store at 4ED6 is to the newly loaded 083B, not to the indexed construction.

The gate at 4E8F tests the R7-source byte against 2, not the outer 0832 index.
On that specific branch into 4E96, j<2 is a local path condition. It is not a
global bound on either index or on other entries. The fresh k read is not
compared here, and equality k=j is not established by static instruction
semantics. No unconditional runtime index range or record count follows.

## 4. Arithmetic and tests

| outer index | low8(index×38) | 0946 construction | 0976 construction |
|---:|---:|---:|---:|
| 0 | 00 | 0946 | 0976 |
| 4 | E0 | 0A26 | 0A56 |
| 5 | 18 (product 0118) | 095E | 098E |

At index 4 both base additions carry. At index 5 both constructions discard
B=01; they do **not** produce the full-product addresses 0A5E and 0A8E.
The inner `2×j`/`2×k` adds the full product, followed by the listed +1 access.
Neither contiguous four-byte transfers nor two-byte transfers make `0x38`
an unconditional record width.

`ec/tools/pd_index_geometry.py`'s existing `access_self_test()` now pins the
construction, caller, helper and stack byte spans independently decoded here.
It checks both committed multiply templates against the independent
byte-arithmetic checker for **all 256 byte indices**, explicitly checks
indices 4 and 5, and exercises the supplied-A suffix separately (including
nonzero B). These are local arithmetic tests, not feasible-index assertions.
It also pins the five **unchanged bounded census stops**, so manual evidence
cannot silently widen discovery or change its denominator.

Reproduce the tests and all five temporary CSV comparisons with
[pd-index-geometry.md](pd-index-geometry.md) §8.2. No generated CSV is edited;
the legacy denominators remain 151 low-run / 3,176 whole-image MOV-DPTR anchors.

## 5. Framing evidence

The caller spans above are decoded from branch-separated blocks rather than
by walking through inline constants. These additional commands checked the
boundaries, the dispatcher and the complete short helper dependencies:

```sh
r2 -a 8051 -b 8 -e scr.color=0 -q -c \
  'pD 0x11 @ 0x4c27; pD 0x26 @ 0x119c; px 0x25 @ 0x4c38; pD 0x1a @ 0x4d6f; pD 8 @ 0x4e7c' \
  /tmp/pd-77.bin
r2 -a 8051 -b 8 -e scr.color=0 -q -c \
  'pD 0x33 @ 0x4d89; px 4 @ 0x4dbc; pD 6 @ 0x4dc0; px 4 @ 0x4dc6; pD 0x27 @ 0x4dca; pD 0x53 @ 0x4e84; pD 0x31 @ 0x104d' \
  /tmp/pd-77.bin
r2 -a 8051 -b 8 -e scr.color=0 -q -c \
  'pD 7 @ 0xf75c; pD 0xe @ 0x716c; pD 0x11 @ 0x0f0e; pD 8 @ 0xb24c; pD 7 @ 0xb267' \
  /tmp/pd-77.bin
```

### 5.1 Dispatcher and case boundaries

The prologue `0x4C27..0x4C37`, immediately after RET at 4C26, is
`900832eff0900834eaf0a3ebf0ed12119c`. MOV A,R5 at 4C34 supplies the
selector to LCALL 119C at 4C35. The complete dispatcher `119C..11C1` is:

```text
119C  d083 d082 f8           POP DPH; POP DPL; MOV R0,A
11A1  e4 93 7012            CLR A; MOVC A,@A+DPTR; JNZ 11B7
11A5  7401 93 700d          MOV A,#01; MOVC A,@A+DPTR; JNZ 11B7
11AA  a3 a3                INC DPTR; INC DPTR
11AC  93 f8 7401 93         MOVC A,@A+DPTR; MOV R0,A; MOV A,#01; MOVC A,@A+DPTR
11B1  f582 8883 e4 73       MOV DPL,A; MOV DPH,R0; CLR A; JMP @A+DPTR
11B7  7402 93 68 60ef       MOV A,#02; MOVC A,@A+DPTR; XRL A,R0; JZ 11AC
11BD  a3 a3 a3 80df         INC DPTR; INC DPTR; INC DPTR; SJMP 11A1
```

It consumes the return address as a CODE-table pointer. Nonzero target pairs
have a third selector byte; a matched selector leaves A=0 before 11AC.
A zero target pair selects the following default target. Thus the bytes at
`4C38..4C5C` are data:

```text
4c5d00 4c9201 4c9e02 4d1503 4d2c04 4d5f05
4d6f06 4e8409 4f5c0a 4fc20b 4fd60c 0000 4fe1
```

In particular file `0x24C4A` holds `4d6f06` (case 06 → 4D6F), and file
`0x24C4D` holds `4e8409` (case 09 → 4E84). These are separate cases, not
successive execution regions. This framing relies on decoded dispatcher
semantics and table contents together, not a raw target match.

Starting at case 4D6F, the complete prefix to 4D89 is:

```text
4D6F  900834 e0 7004        MOV DPTR,#0834; MOVX A,@DPTR; JNZ 4D79
4D75  a3 e0 6401           INC DPTR; MOVX A,@DPTR; XRL A,#01
4D79  6003 024fe1          JZ 4D7E; LJMP 4FE1
4D7E  900832 e0 ff         MOV DPTR,#0832; MOVX A,@DPTR; MOV R7,A
4D83  12f75c ef 7065       LCALL F75C; MOV A,R7; JNZ 4DEE
```

`4D89` is the fallthrough of the last branch. The earlier entry `4D80`
would start in the operand of MOV DPTR,#0832, not at a RETI instruction.
F75C's full body `ef12716ce0ff22` calls 716C, whose full body is
`75f05ea424e3f582e43408f58322`; both have ordinary RET continuations.
They replace R7 before that test, but 4D89 reloads the index afterward.
Before case 4E84, `4E7C..4E83` is `900832e0ff02d8ee`, ending in LJMP
D8EE at 4E81; there is no sequential fallthrough into 4E84.

### 5.2 The inline-data trap and register clobbers

The direct branch at 4DB4 supports entry to 4DD2 without needing to follow
D8EE on the other arm. On that other arm, LCALL 104D at 4DB9 is followed by
four inline bytes `00000002` at 4DBC, resumes at 4DC0 (`90084112104d`),
then consumes `00000000` at 4DC6 and resumes at 4DCA. The fully checked
104D..107D byte run is:

```text
a8828583f0d083d082121064121064121064121064e473
e493a3c583c5f0c583c8c582c8f0a3c583c5f0c583c8c582c822
```

104D saves the destination halves, pops its caller's return address into
DPTR, calls 1064 four times, and finishes with CLR A; JMP @A+DPTR.
Each 1064 invocation reads one CODE byte using MOVC, advances that pointer,
swaps to the data destination for a MOVX store/increment, swaps back and
returns. That accounts for exactly four inline argument bytes, not four
executed caller instructions. In particular the apparent `029008` at 4DBF
is a false LJMP spanning the last argument and the real MOV DPTR at 4DC0.
It is not evidence for any path. Full D8EE behavior is not recovered here.

The complete clobber-sensitive bodies used by §3 are:

| runtime / file span (inclusive) | bytes | preservation relevant here |
|---|---|---|
| `B263..B26D / 2B263..2B26D` | `1210bc ef 25e0 2583 f583 22` | calls full-product 10BC, loads R7 into A, falls into B267 page add; no R7 write |
| `B267..B26D / 2B267..2B26D` | `25e0 2583 f583 22` | ADD A,ACC; ADD A,DPH; MOV DPH,A; RET; no R3 write |
| `0FCB..0FD6 / 20FCB..20FD6` | `e0 f8 a3 e0 f9 a3 e0 fa a3 e0 fb 22` | four MOVX reads into R0–R3 with three INC DPTR; preserves R7 |
| `0F0E..0F1E / 20F0E..20F1E` | `eb9ff5f0ea9e42f0e99d42f0e89c45f022` | subtract/OR comparison across R0–R3 and R4–R7, changes A/B/flags, ordinary RET |
| `B24C..B253 / 2B24C..2B253` | `fb fa f9 f8 c3 020f0e` | loads R3..R0 from A, clears carry, tail-jumps to 0F0E |

No register-bank switch occurs in these preservation paths. B24C's R3
clobber does not invalidate the writer's source: 4DD6 loads R3 again.
These bodies also establish ordinary return to the conditional branches
at 4DA5 and 4DB4. The 4E84..4ED6 span contains no inline argument calls;
its two local conditional exits are explicitly retained in §3.2.

This establishes local framing **conditional on entry to 4C27**. It does
not establish reset-to-4C27 reachability, all upstream callers, occurrence of
selectors 06/09, or execution of either conditional arm on hardware.

## 6. Remaining questions

- What do the four-byte and two-byte values mean, and who else reads/writes
  these PD XDATA addresses? The local copy and zero test do not identify them.
- What constrains the outer 0832 index, and under what conditions can the two
  083A loads differ? A whole-program flow/mutation analysis or physical trace
  is needed; no bounds are inferred from multiplication constants.
- Would a future census model consumer-only helpers and balanced stack detours?
  That needs positive/negative regressions and separately reported coverage,
  not a silent change to the existing construction-only rows.

These questions do not establish a dependency on #75's other multiplication
families, #67's recipient inventory, #69's 1253 convention, #25's PD 07D0
investigation, or #61's CODE-reader work. No connection to EC 07D0 is shown.
The separate PD/EC maps in `docs/findings.md` §3a–3b remain distinct, no
`registers.yaml` status changes, and no firmware or vendor input changes.
