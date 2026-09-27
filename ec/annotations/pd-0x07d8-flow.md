# The PD image's `0x07D8`-`0x07DA`, and what `0x35DA`'s `ljmp 0x0F45` does with it (#45)

**Read the scope first.** Everything below is a statement about instructions in
a *second 8051 program* — the `ITE8850-PD` image at file `0x20000` of
`ec/firmware/GMxMGxx_11.800`. Its XDATA `0x07D8` is **not** the EC's XDATA
`0x07D8`; the two are different address spaces belonging to different
programs, which [`lightbar-bat-flow.md`](lightbar-bat-flow.md) §2 establishes
and this file does not re-argue.
`ec/annotations/registers.yaml`'s `MODE_TCC_OFFSET_DEFAULTS` entry
(`addr: [0x07D8, 0x07D9, 0x07DA]`, CPU TCC offset defaults, `live` source
`05 05 05`) describes the **EC** map, is read live against the EC, and is
**unchanged** by anything in this file. No `status:` value moves, no
`registers.yaml` row is edited, and nothing here is evidence about
`uniwill-laptop`'s view of these bytes.

This is static analysis of committed firmware. No hardware test ran, no
register was read back, and "the routine computes X" throughout is a statement
about opcodes, never about observed behaviour.

**Two of the issue's premises are false against files already in the tree**,
and the work is different because of it:

1. *"`0x07D8` is not in `ec/annotations/registers.yaml`."* It is, as one of the
   three addresses of the `MODE_TCC_OFFSET_DEFAULTS` entry, with
   `static_refs: [34, 16, 53]`, `static_refs_main_ec: [1, 1, 1]`,
   `static_refs_pd_image: [33, 15, 52]`, `status: present-untested`, and a note
   that already names this issue. **The issue's own parenthetical is therefore
   already answered**: the committed entry groups exactly `0x07D8`, `0x07D9`
   and `0x07DA`, so the 3-byte load's span does make them one variable *as far
   as `registers.yaml` is concerned*. That also means `register_ref_table.py`
   runs over all three addresses unmodified (§4), and that the
   status-vocabulary question the issue defers to **#32** is not engaged: this
   is an EC-map address that a second program reuses the *number* for, not a
   PD-only address, so no new `status:` value is needed and none was invented.
2. *"`0x0F45` needs disassembling."* It is already named and decoded:
   `pd,0F45,read4_ptr_kind_dispatch` in `ec/annotations/ghidra-functions.csv`,
   with all fifteen instructions committed in `ec/decompiled/pd/0F45.asm` and
   `ec/ghidra/reassembly.csv` recording the row as `match`. What the issue
   actually wants is the ground that annotation explicitly left — its
   "the other three targets are outside this listing and are not decoded here"
   — plus a **cross-decoder confirmation**, which is worth having precisely
   because `ec/ghidra/cross-decoder.csv` records that row's outcome as
   `vacuous`: both sides of that comparison come from the annotation, so
   nothing independent has ever checked it. §2 is that check.

## 1. Input, reproduction and framing

Input: `ec/firmware/GMxMGxx_11.800`, 262,144 bytes, SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`. The
existing `trace_xdata_refs.py` map places PD at file `[0x20000,0x30000)`; for
**every PD runtime address below**, file offset = runtime address + `0x20000`.
XDATA operand addresses do not use that conversion. The one main-EC address in
§5 is in `bank0`, where runtime and file offset are both `0x93AE`.

Independent decoding used **radare2 5.5.0** on a temporary flat PD image. Every
transcript in this file is the verbatim output of one of these six commands,
run from the repository root:

```sh
sha256sum ec/firmware/GMxMGxx_11.800
r2 -v
dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1

r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x0f45; pd 15' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x0faf; pd 12; s 0x0fbb; pd 13; s 0x12b9; pd 12; s 0x12c5; pd 12' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x35da; pd 8; s 0x10c8; pd 9' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x6482; pd 12; s 0x6492; pd 6' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x6460; pd 12; s 0xb2a6; pd 5' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x93ab; pd 16' ec/firmware/GMxMGxx_11.800
```

`-e asm.comments=false` suppresses r2's synthetic `[0x…]` value hints; they
are guesses about an uninitialised machine, not bytes in the image, and
[`pd-0x38-consumers.md`](pd-0x38-consumers.md) §1 makes the same point about
the same output. The `┌─<` / `└─>` gutter is r2's control-flow drawing of the
listing, not part of it. `pd` counts instructions, so §3's four counts are
chosen to stop on each routine's `RET`; one more instruction prints the first
instruction of the next routine, which is what fixes where each of the four
ends.

`0x35DA`'s and `0x0F45`'s windows are straight-line-and-tail-call, so r2 walks
them whole. `0x6482`'s does not: the block ends at the `ljmp` at `0x648F`, and
§4's classification for the `0x6498` site is a direct consequence of that, not
of what the code does.

## 2. `0x0F45`, decoded independently

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x0f45; pd 15' /tmp/pd.bin
        ┌─< 0x00000f45      bb0107         cjne r3, #0x01, 0x0f4f
        │   0x00000f48      8982           mov dpl, r1
        │   0x00000f4a      8a83           mov dph, r2
        ┌──< 0x00000f4c      020faf         ljmp 0x0faf
      ┌─└─> 0x00000f4f      5005           jnc 0x0f56
        ││    0x00000f51      e9             mov a, r1
        ││    0x00000f52      f8             mov r0, a
        ││┌─< 0x00000f53      0212b9         ljmp 0x12b9
     ┌└───> 0x00000f56      bbfe05         cjne r3, #0xfe, 0x0f5e
     │ ││   0x00000f59      e9             mov a, r1
     │ ││   0x00000f5a      f8             mov r0, a
     │┌───< 0x00000f5b      0212c5         ljmp 0x12c5
     └────> 0x00000f5e      8982           mov dpl, r1
      │││   0x00000f60      8a83           mov dph, r2
     ┌────< 0x00000f62      020fbb         ljmp 0x0fbb
```

This agrees instruction for instruction with the committed
`ec/decompiled/pd/0F45.asm` — same fifteen, same addresses, same operand
order, no gap — and it was produced by a decoder that has not read that file,
which is the point. `ec/ghidra/cross-decoder.csv`'s `0F45` row reads
`outcome=vacuous`, so the two frames the tree compares there are the same
frame twice; this transcript is the first independent one, and it agrees.

**What the fifteen instructions are.** The issue asks whether the routine is
"an arithmetic combine, a compare, a store elsewhere". It is a **four-way
compare-and-dispatch that then reads four bytes**, and it stores nothing
itself:

| `R3` on entry | taken at | sets | jumps to | reads 4 bytes from |
|---:|---|---|---|---|
| `1` | `0x0F48` | `DPTR = R1:R2` | `0x0FAF` | XDATA at `@DPTR` |
| `0` | `0x0F51` | `R0 = R1` | `0x12B9` | internal RAM at `@R0` |
| `0xFE` | `0x0F59` | `R0 = R1` | `0x12C5` | XDATA at `@R0` |
| anything else (`>= 2`, `!= 0xFE`) | `0x0F5E` | `DPTR = R1:R2` | `0x0FBB` | CODE at `@DPTR` |

There is no arithmetic on the loaded bytes in this routine. The `0` case is
selected by the *carry* out of the first `CJNE` rather than by a second
compare: `CJNE R3,#0x01` sets carry exactly when `R3 < 1`, i.e. when `R3 == 0`,
and `JNC 0x0F56` then skips the `0` arm for every `R3 >= 2`. So `1` and `0`
cost one `CJNE` between them, and `0xFE` costs a second.

All four targets load into **`R4:R7`**, in the same order, and three of them
advance the pointer they used. That is what makes the entry a *four-byte
loader with an address-space selector* rather than a compare.

**Register aliasing, stated as such.** `0x35DA` stores its caller's `R6:R7` to
the handed address and then tail-calls into this routine, which overwrites all
four of `R4:R7` — `R6` third and `R7` fourth. So the value `0x35DA` had just
stored is *not* the source of the value `0x0F45` produces: the two halves of
`R4:R7` are reused, and the `MOVX @DPTR,A` pair that precedes the `LJMP` is
unrelated to the `MOV R6,A` / `MOV R7,A` that follows the dispatch. That is a
statement about the instruction stream, and it is why §3.1's two facts about
`0x35DA` — it stores to the caller's `0x07E3`, and it reads the `0x07D8`
triple — are two separate things rather than one.

## 3. The four arms, and what each one actually addresses

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x0faf; pd 12; s 0x0fbb; pd 13; s 0x12b9; pd 12; s 0x12c5; pd 12' /tmp/pd.bin
            0x00000faf      e0             movx a, @dptr
            0x00000fb0      fc             mov r4, a
            0x00000fb1      a3             inc dptr
            0x00000fb2      e0             movx a, @dptr
            0x00000fb3      fd             mov r5, a
            0x00000fb4      a3             inc dptr
            0x00000fb5      e0             movx a, @dptr
            0x00000fb6      fe             mov r6, a
            0x00000fb7      a3             inc dptr
            0x00000fb8      e0             movx a, @dptr
            0x00000fb9      ff             mov r7, a
            0x00000fba      22             ret
            0x00000fbb      e4             clr a
            0x00000fbc      93             movc a, @a+dptr
            0x00000fbd      fc             mov r4, a
            0x00000fbe      7401           mov a, #0x01
            0x00000fc0      93             movc a, @a+dptr
            0x00000fc1      fd             mov r5, a
            0x00000fc2      7402           mov a, #0x02
            0x00000fc4      93             movc a, @a+dptr
            0x00000fc5      fe             mov r6, a
            0x00000fc6      7403           mov a, #0x03
            0x00000fc8      93             movc a, @a+dptr
            0x00000fc9      ff             mov r7, a
            0x00000fca      22             ret
            0x000012b9      e6             mov a, @r0
            0x000012ba      fc             mov r4, a
            0x000012bb      08             inc r0
            0x000012bc      e6             mov a, @r0
            0x000012bd      fd             mov r5, a
            0x000012be      08             inc r0
            0x000012bf      e6             mov a, @r0
            0x000012c0      fe             mov r6, a
            0x000012c1      08             inc r0
            0x000012c2      e6             mov a, @r0
            0x000012c3      ff             mov r7, a
            0x000012c4      22             ret
            0x000012c5      e2             movx a, @r0
            0x000012c6      fc             mov r4, a
            0x000012c7      08             inc r0
            0x000012c8      e2             movx a, @r0
            0x000012c9      fd             mov r5, a
            0x000012ca      08             inc r0
            0x000012cb      e2             movx a, @r0
            0x000012cc      fe             mov r6, a
            0x000012cd      08             inc r0
            0x000012ce      e2             movx a, @r0
            0x000012cf      ff             mov r7, a
            0x000012d0      22             ret
```

All four agree instruction for instruction with the committed
`ec/decompiled/pd/{0FAF,0FBB,12B9,12C5}.asm`, and each is a complete routine
ending in an ordinary `RET` rather than another tail call. So the whole chain
`0x35DA` → `0x0F45` → arm returns to whoever `LCALL`ed `0x35DA` — `0x6488` on
the `0x6482` path — with `R4:R7` loaded and no `DPTR` fixup on the way out.

All four also already have their own rows in `ghidra-functions.csv` and their
own committed listings, so the `0x0F45` row's "the other three targets are
outside this listing and are not decoded here" is a statement about *that
file*, not about the tree: the two it points at have been decoded since, in
`ec/decompiled/pd/12B9.asm` and `ec/decompiled/pd/12C5.asm`. What §2 needs
from them is only what the dispatch site itself does not show — the addressing
mode each one uses:

- **`0x0FAF` `read4xdata_to_r4_r7`** — four `MOVX A,@DPTR` with three `INC
  DPTR`; returns with DPTR one past the last byte read. XDATA through `DPTR`.
- **`0x0FBB` `read4_code_to_r4r7`** — `MOVC A,@A+DPTR` at offsets `0`..`3`.
  CODE, and no XDATA at all. Its own `0x0FBB.c` decompile reports only the
  last byte; the listing above is the same thirteen instructions with all four
  loads kept, which is the reading `ghidra-functions.csv` already records for
  it.
- **`0x12B9` `read4_idata_to_r4r7`** — `MOV A,@R0` four times with `INC R0`
  between. `E6` is the 8051 **internal RAM** indirect form: this is the one arm
  that reads neither XDATA nor CODE.
- **`0x12C5` `read4_xdata_to_r4r7`** — the same shape with `E2`, `MOVX A,@R0`,
  i.e. **XDATA addressed through `R0` rather than through `DPTR`**. It is a
  different addressing mode from `0x0FAF` for the same space, which is why the
  two carry different names.

So the `R2:R1` pair is a **16-bit address in two arms and an 8-bit one in
two others**, decided by the same `R3` selector. That is the concrete content
of "the triple is one tag byte in front of a pointer, and the tag selects which
address space to read" — with the extra wrinkle that in the two `@R0` arms
only the low byte survives, because `0x0F51` and `0x0F59` both set `R0` from
`R1` alone. Four readers, three address spaces, one destination register
group.

[`pd-0x38-consumers.md`](pd-0x38-consumers.md) overlaps this section on
`0x0FAF` alone and from the other side: it traces five *callers* that build a
pointer and then reach the XDATA reader, and never mentions `0x0F45` itself.
This section is the dispatch that chooses between `0x0FAF` and its three
siblings, and what selects it. (`0x10FD` `read3_ptr_kind_dispatch` in
`ghidra-functions.csv` is the same shape over three bytes rather than four; it
is named here only because `pd-image.md` used to pair the two, and nothing
below is a claim about it.)

### 3.1 `0x35DA`, and the sites that hand it its address

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x35da; pd 8; s 0x10c8; pd 9' /tmp/pd.bin
        ╎   0x000035da      ee             mov a, r6
        ╎   0x000035db      f0             movx @dptr, a
        ╎   0x000035dc      a3             inc dptr
        ╎   0x000035dd      ef             mov a, r7
        ╎   0x000035de      f0             movx @dptr, a
        ╎   0x000035df      9007d8         mov dptr, #0x07d8
        ╎   0x000035e2      1210c8         lcall 0x10c8
        └─< 0x000035e5      020f45         ljmp 0x0f45
            0x000010c8      e0             movx a, @dptr
            0x000010c9      fb             mov r3, a
            0x000010ca      a3             inc dptr
            0x000010cb      e0             movx a, @dptr
            0x000010cc      fa             mov r2, a
            0x000010cd      a3             inc dptr
            0x000010ce      e0             movx a, @dptr
            0x000010cf      f9             mov r1, a
            0x000010d0      22             ret
```

`0x10C8` is the inverse of `0x10E8` and reads **three** bytes at the incoming
DPTR into `R3`, `R2`, `R1`. With DPTR reloaded to `0x07D8` immediately before
it, that is unambiguous and it is the whole answer to the issue's arithmetic
question:

- `R3` = the byte at XDATA `0x07D8` — the **selector** `0x0F45` dispatches on;
- `R2:R1` = the bytes at XDATA `0x07D9` and `0x07DA` — the **address**, in that
  order, with `R1` low (`MOV DPL,R1`) and `R2` high (`MOV DPH,R2`).

The `MOV DPTR,#0x07D8` is a hardcoded operand and not a handoff-derived
address, exactly as the issue says; what the issue could not yet supply is what
it is then *used for*, and §2 is that.

The two sites that reach `0x35DA` by `LCALL`, and the neighbouring `0x07D8`
`MOV DPTR` that the classifier calls `no movx in window`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x6482; pd 12; s 0x6492; pd 6' /tmp/pd.bin
            0x00006482      9007e3         mov dptr, #0x07e3
            0x00006485      1235da         lcall 0x35da
            0x00006488      1238e5         lcall 0x38e5
            0x0000648b      fd             mov r5, a
            0x0000648c      fc             mov r4, a
            0x0000648d      7b32           mov r3, #0x32
        ┌─< 0x0000648f      0264d2         ljmp 0x64d2
        │   0x00006492      9007e9         mov dptr, #0x07e9
        │   0x00006495      e0             movx a, @dptr
        │   0x00006496      6402           xrl a, #0x02
        │   0x00006498      9007d8         mov dptr, #0x07d8
       ┌──< 0x0000649b      701b           jnz 0x64b8
            0x00006492      9007e9         mov dptr, #0x07e9
            0x00006495      e0             movx a, @dptr
            0x00006496      6402           xrl a, #0x02
            0x00006498      9007d8         mov dptr, #0x07d8
        ┌─< 0x0000649b      701b           jnz 0x64b8
        │   0x0000649d      1235e2         lcall 0x35e2
```

`0x6482` and `0x64AD` are the two handoffs
[`lightbar-bat-flow.md`](lightbar-bat-flow.md) §3.5 records; both load `DPTR`
with `0x07E3` and `LCALL 0x35DA`, so the pair of `MOVX @DPTR,A` there stores
the caller's `R6:R7` to `0x07E3`/`0x07E4` and nothing to `0x07D8`.

The `0x6498` site is the one that reads as the question's "coincidental
`MOV DPTR`" and is not one: `0x6498` loads `0x07D8` and the very next
instruction is the `JNZ` at `0x649B` that leaves the block, which is why
`register_ref_table.py`'s eight-instruction walk records
`no movx in window` (`window` is the single instruction `jnz +0x1b`). The
window, not the address, is what the verdict is about — that bucket means "this
method stopped at a control-flow instruction before it saw an access", which is
the standing §4c "not found by this method" and never an absence.

One adjacent observation, **not traced here and recorded as a follow-up
question**: on the arm `0x649B` does *not* take, control reaches `0x649D`'s
`LCALL 0x35E2` — an address *inside* `0x35DA`'s body, past the
`MOV DPTR,#0x07D8`. Entering at `0x35E2` skips the pointer load, so DPTR is
whatever the `0x07D8` load at `0x6498` left it, and the same `0x10C8` →
`0x0F45` tail follows. Whether that is a second route into the same read, and
what `R6:R7` hold on it, is not decoded in this file and is not claimed here.

## 4. The read / write / handoff split

The census, from the committed image, is the issue's own numbers:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D8 0x07D9 0x07DA --counts-only
0x07D8: 34 direct MOV DPTR site(s)  bank0=1  pd-image=33

0x07D9: 16 direct MOV DPTR site(s)  bank0=1  pd-image=15

0x07DA: 53 direct MOV DPTR site(s)  bank0=1  pd-image=52
```

`register_ref_table.py` takes its address list from `registers.yaml`, so it
covers all three with no shim and no override — which is what premise
correction 1 buys. With `--callee-depth 1` the `handed to lcall/ljmp` bucket
splits by what the callee's own entry point does with DPTR:

```console
$ cd ec/tools && python3 register_ref_table.py ../../ec/firmware/GMxMGxx_11.800 --callee-depth 1
...
| `0x07D8` | `MODE_TCC_OFFSET_DEFAULTS` | 34 | 1 | 33 | 19 | 9 | 1 | 0 | 0 | 3 | 1 | 0 | 0 | 1 |
| `0x07D9` | `MODE_TCC_OFFSET_DEFAULTS` | 16 | 1 | 15 | 7 | 4 | 0 | 0 | 0 | 1 | 2 | 1 | 0 | 1 |
| `0x07DA` | `MODE_TCC_OFFSET_DEFAULTS` | 53 | 1 | 52 | 25 | 8 | 1 | 0 | 0 | 9 | 6 | 0 | 4 | 0 |
...
160 entries / 192 addresses: class buckets sum to the site count and main + PD to the file-wide total for every address
```

| `0x07D8` | `0x07D9` | `0x07DA` | class |
|---:|---:|---:|---|
| 19 | 7 | 25 | read |
| 9 | 4 | 8 | write |
| 1 | 0 | 1 | read+write |
| 0 | 0 | 0 | movc (CODE pointer) |
| 0 | 0 | 0 | jmp @a+dptr |
| 3 | 1 | 9 | handoff → callee reads |
| 1 | 2 | 6 | handoff → callee writes |
| 0 | 1 | 0 | handoff → callee reads+writes |
| 0 | 0 | 4 | handoff → unresolved |
| 1 | 1 | 0 | no movx in window |

The two all-zero rows are a result and not padding: no site on any of the three
addresses builds a CODE pointer or a jump-table entry out of it, which is what
distinguishes this triple from `0x07D0` and `0x04A6` — the two
`ec/annotations/ec-0x07d0-sites.md` §5 and `ec/annotations/pd-xdata-overlap.md`
§3 record as pointer constructions. They are ordinary XDATA variables on the
PD-image side.

Reconciliation is the point, not the printed numbers: the tool exits non-zero
if a site's class is dropped or if main + PD stops summing to the file-wide
total, and it exits 0 here for all 192 addresses. `check_register_counts.py` —
which every count in `registers.yaml` rests on — re-derives all three of
`static_refs`, `static_refs_main_ec` and `static_refs_pd_image` for all 192
addresses and exits 0, which covers this entry's `34 / 16 / 53` and `1 / 1 / 1`
too. It reports only that total and no per-address line, so the readable
per-address figures are the `trace_xdata_refs.py` block above.

**A `write` class is a store instruction.** The tool's own docstring says so
("a `write` class is not evidence that the EC acts on the value, only that an
instruction stores to the address"), and it is repeated here because the
alternative reading — 9 instructions in the PD image store to its `0x07D8` —
sounds like 9 places that *use* it. They are not; they are nine `MOVX @DPTR,A`
and nothing more.

The four `handoff → unresolved` rows on `0x07DA` are worth naming, because
three of them are one known routine rather than four questions. `0xBBA3`,
`0xBDD3` and `0xE46A` all `LCALL 0x104D`, the inline-argument dispatcher
`pd-0x38-consumers.md` §5.2 decodes and **#36** owns;
`lightbar-bat-flow.md` §3.5 already noted that `0x1041` sits next to it and is
a *different* routine, which is why those rows are `unresolved` rather than
resolved to the 4-byte store. The fourth, `0x5511` → `0x9C27`, is a 16-bit
add across `R5:R6:R7` with no memory access in its window. All four are
verdicts of an eight-instruction walk, not statements that the callees do
nothing.

The per-site record is
[`pd-0x07d8-ref-table.csv`](pd-0x07d8-ref-table.csv) — 103 rows, one per
site, with `class`, `window`, `callee` and `callee_window`. It is a **filtered
extract of a whole-`registers.yaml` run, not the output of a tool pointed at
three addresses**: the `register` column is the EC-map name `registers.yaml`
gives the address, and it says nothing about the PD image's own `0x07D8`. The
command that produces the file byte for byte is

```sh
cd ec/tools && python3 register_ref_table.py ../../ec/firmware/GMxMGxx_11.800 --csv --callee-depth 1 \
  | tr -d '\r' | grep -E '^(addr,|0x07D8,|0x07D9,|0x07DA,)' \
  > ../../ec/annotations/pd-0x07d8-ref-table.csv
```

(`tr -d '\r'` because the tool's CSV writer emits CRLF and every committed CSV
in this tree is LF.)

### 4.1 Two corroborations already in the tree, cited rather than re-derived

- `ghidra-functions.csv`, `pd,0xE458,store_07d8_and_dispatch_07da` — writes
  `R7` to XDATA `0x07D8`, then loads DPTR with `0x07DA` and calls the store
  helper. Same two-addresses-in-one-block shape as §5's main-EC site, on the
  other side of the file boundary.
- `ghidra-variables.csv`, the `pd,0xB2A7` row — a `0x07d8` DPTR load
  tail-jumping to `0x0FAF`, carrying the note "0x07d8 is this program's own
  XDATA, not an EC register". That is this file's scope statement, already
  written down by someone else:

  ```console
  $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x6460; pd 12; s 0xb2a6; pd 5' /tmp/pd.bin
          ┌─< 0x00006460      5003           jnc 0x6465
         ┌──< 0x00006462      02665a         ljmp 0x665a
         │└─> 0x00006465      120f45         lcall 0x0f45
         │    0x00006468      7811           mov r0, #0x11
         │    0x0000646a      120f1f         lcall 0x0f1f
         │    0x0000646d      e4             clr a
         │    0x0000646e      fe             mov r6, a
         │    0x0000646f      7b64           mov r3, #0x64
         │    0x00006471      1235cf         lcall 0x35cf
         │    0x00006474      7808           mov r0, #0x08
         │    0x00006476      120f1f         lcall 0x0f1f
         │    0x00006479      e4             clr a
          ╎   0x0000b2a6      ef             mov a, r7
          ╎   0x0000b2a7      f0             movx @dptr, a
          ╎   0x0000b2a8      9007d8         mov dptr, #0x07d8
          └─< 0x0000b2ab      020faf         ljmp 0x0faf
              0x0000b2ae      75f038         mov b, #0x38
  ```

  The `0x6465` block is also the only place in this file where the `R4:R7`
  destination of §2 is visible being *used*: the instruction after the
  `LCALL 0x0F45` is `MOV R0,#0x11` / `LCALL 0x0F1F`, and `0x0F1F` is
  annotated `shr_32bit_r4r7_by_r0` — a 32-bit right shift of `R4:R7`. So the
  four bytes land in a register group the very next routine treats as a 32-bit
  quantity. That is the whole of the consumer evidence here: one site, one
  instruction stream, and no claim about what the 32-bit value means.

  **The call-graph count is not a census of the image.**
  `call-graph-callees.csv` records `0F45` with `inbound=1`, `ljmp=1` — the
  tail call at `0x35E5`. The `LCALL` at `0x6465` is not in that table, because
  the table is built from the committed `.asm` listings and `0x6465` falls in
  a `0x6xxx` region with no committed listing. That is a coverage limit of the
  table, stated here so the number is not read as the number of callers.

## 5. The single main-EC site is a real one

`registers.yaml` records `static_refs_main_ec: [1, 1, 1]` for the three
addresses, and the issue asks whether those three `MOV DPTR` sites are real
EC-side references or coincidences. They are real, and they are **one
straight-line block writing all three**, in `bank0` at file offset = runtime =
`0x93AE`, inside the routine `ghidra-functions.csv` already names
`bank0,0x9334,seed_tcc_defaults_from_ba36`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x93ab; pd 16' ec/firmware/GMxMGxx_11.800
            0x000093ab      7407           mov a, #0x07
            0x000093ad      93             movc a, @a+dptr
            0x000093ae      9007d8         mov dptr, #0x07d8
            0x000093b1      f0             movx @dptr, a
            0x000093b2      8f82           mov dpl, r7
            0x000093b4      8e83           mov dph, r6
            0x000093b6      740b           mov a, #0x0b
            0x000093b8      93             movc a, @a+dptr
            0x000093b9      9007d9         mov dptr, #0x07d9
            0x000093bc      f0             movx @dptr, a
            0x000093bd      900a47         mov dptr, #0x0a47
            0x000093c0      12b987         lcall 0xb987
            0x000093c3      7403           mov a, #0x03
            0x000093c5      93             movc a, @a+dptr
            0x000093c6      9007da         mov dptr, #0x07da
            0x000093c9      f0             movx @dptr, a
```

This is the committed `ec/decompiled/bank0/9334.asm` instruction for
instruction over the same span. Each address is written from a **byte of a CODE
table** the routine indexes: `0x07D8` from offset `0x07`, `0x07D9` from offset
`0x0B`, `0x07DA` from offset `0x03`, with the table pointer in `DPTR` before
each `MOVC` and `R7:R6` re-formed as that pointer between the first and the
second. The `0x9334` annotation already says as much — "a call to `0xB93D`
then leaves indexed CODE-table bytes in `0x07D8`, `0x07D9` and `0x07DA`" — so
this is a *third* premise of the issue the tree had already answered, recorded
here with an independent decoder behind it.

The distinction that matters for §4: this is the **EC's** `0x07D8`, the one
`registers.yaml` names `MODE_TCC_OFFSET_DEFAULTS` and the one read live as
`05 05 05`. It shares a *number* with 33 PD-image sites and nothing else. The
PD image's `0x07D8` is a different byte in a different address space, and the
`05 05 05` reading is not evidence about it. `lightbar-bat-flow.md` §2 is the
canonical statement and this file only applies it.

## 6. What this does and does not say

**Does.** `0x0F45` is a four-way compare-and-dispatch on `R3` that reads four
bytes into `R4:R7` from one of three address spaces, and the tag that selects
between them is the byte at the PD image's XDATA `0x07D8` while the address
behind it is `0x07D9`/`0x07DA`. The 33 PD-image sites on `0x07D8` split
19 read / 9 write / 1 read+write / 4 handoff / 1 no-access-in-window, and the
one EC-image site is a three-in-a-row seed from a CODE table in
`seed_tcc_defaults_from_ba36`. Every one of those is an instruction in a
committed image, re-decodable from the six `r2` command lines in §1.

**Does not.** Nothing here is a behavioural claim. That the PD program acts on
the value in `0x07D8`, that the `R3` selector takes any particular value at
run time, or that the four bytes mean anything, are all open. The 19 `read`
and 9 `write` classes are instruction classifications with
`register_ref_table.py`'s stated limits — a linear eight-instruction walk that
stops at the first control-flow instruction, blind to indirect and
pointer-mediated XDATA access — so a `0` or a `no movx in window` anywhere in
§4 is "not found by this method", never "absent" (§4c's standing rule, and
`0x07B9` the standing counter-example). The other 30 PD-image sites on
`0x07D8` are **not** individually traced; the CSV carries the census and
`0x6482`/`0x64AD` are the two worth a follow-up, with `0x649D`'s interior
`LCALL 0x35E2` the question this file opened and did not close.

And it is not evidence about the EC's `0x07D8`, nor about `0x07E2`-`0x07E5`,
nor about `uniwill-laptop`'s lightbar registers either way.
`lightbar-bat-flow.md` §5's live probe is unchanged and still needs a human at
the machine; this file needs none, and ran none.

### 6.1 A retraction, in place

`ghidra-functions.csv`'s `pd,0x35DA,store_2byte_r6r7_then_0x10c8` row used to
end:

> Reached by lcall from the 0x6482 and 0x64AD sites, and what it then does
> with the 0x07D8 pointer is not read in this file

That clause is now false and the row says what is read instead, with this
file as its evidence. It is recorded here rather than edited away so the
correction is visible: the old wording is a `git log -p` away, but only a
reader who knows to look would find it, and the claim it made was a statement
about the state of the reading, not a statement about the code.

## 7. The re-export this needed, and what else it moved

`ec/decompiled/pd/35DA.c`'s plate comment is the annotation comment, so §6.1's
row edit needs `ec/tools/build_ec_decompile.py` to follow — export-only mode,
which copies the committed project to scratch and never writes the database
itself. The regenerated file is the only `.c` this issue's own edit changes.

The export also refreshed six `ec/decompiled/bank1/*.c` files whose committed
text was already behind `ghidra-functions.csv`: each gains the same
`xdata_register_map.py` census sentence, which **is** in the CSV today and was
simply not in the `.c` when that row landed. No decompiled C body changes in
any of them — the diff is the plate comment only. `ec/ghidra/c-digests.csv`
moves with them: `--write-digests` re-hashes the whole tree and `--check` then
compares every committed `.c` against its row, so a re-export that picks up
files this issue did not ask about still has to carry them. The order is
export, then `--write-digests`, then `--check`.

Worth recording because it is a gate-shaped hole rather than a finding: a CSV
comment edit does **not** by itself make `build_ec_decompile.py --check` fail.
The check holds every committed `.c` against `c-digests.csv`, and the digest
against the bytes on disk — neither of which knows what the CSV now says. The
`.c` and the annotation row can therefore drift apart silently, and they had.
The only thing that caught it was running the export. A check that compared
each `.c` plate comment against its CSV row would close that, and
`ghidra-functions.csv` is small enough to do it in; that is a follow-up
question, not something to bolt onto this issue.
