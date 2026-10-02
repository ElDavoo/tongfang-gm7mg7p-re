# `0x07D0` and `0x07CC` in the PD image: the `2000` in the decompile, the routine clustering, and what the byte is made of (#25)

**Read the scope, and then the second paragraph, before anything else.**
Everything below is a statement about instructions in a *second 8051 program*
— the `ITE8850-PD` image at file `0x20000` of `ec/firmware/GMxMGxx_11.800`.
Its XDATA `0x07D0` is **not** the EC's XDATA `0x07D0`; they are different
address spaces belonging to different programs, which
[`lightbar-bat-flow.md`](lightbar-bat-flow.md) §2 establishes and this file
does not re-argue. The EC image references `0x07D0` **zero** times by this
method (`lightbar-bat-flow.md` §6; §6 below reproduces the count).

**And `2000` in `ec/decompiled/pd/*.c` is the address `0x07D0` written in
decimal, not the charge limit.** Ghidra prints the number `2000` wherever the
decompiled C needs a *pointer* to `0x07D0` — an XDATA pointer at most of its
sites, a CODE pointer at one — and `0x07D0` is exactly
`ECSpec.ADDR_BATTERY_CHARGE_LIMIT_DOWN` =
`2000` (`windows/decompiled/v3.1.6.0/ECSpec.cs`). The two numbers coincide
exactly, so a reader who greps `2000` out of the PD decompile will believe a
2000-percentage charge cap was found in the PD firmware. It was not. §2
settles it from three transcripts.

This is static analysis of committed firmware. No hardware test ran, no
register was read back, no write was attempted, nothing ran on the machine.
"The routine computes X" throughout is a statement about opcodes, never about
observed behaviour. Nothing in this file lifts, proposes lifting, or weakens
`registers.yaml`'s `DO-NOT-WRITE-BLIND`; §6 says why, in those words.

## 1. Input, reproduction and the tool

Input: `ec/firmware/GMxMGxx_11.800`, 262,144 bytes, SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`. The
`trace_xdata_refs.py` map places the PD image at file `[0x20000,0x30000)`, so
**for every PD runtime address below, file offset = runtime address +
`0x20000`**. XDATA operand addresses do not use that conversion.

Every transcript in this file is the verbatim output of one of these
commands, run from the repository root. `-e asm.comments=false` suppresses
r2's synthetic `[0x…]` value hints — they are guesses about an uninitialised
machine, not bytes in the image — and the `┌─<` / `└─>` gutter is r2's
control-flow drawing, not part of the listing. `pd` counts instructions.

```sh
sha256sum ec/firmware/GMxMGxx_11.800
r2 -v
dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1

r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x8576; pd 12' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x8599; pd 4; s 0x34d9; pd 3' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xa5e5; pd 8' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x4b3c; pd 9; s 0x4b7a; pd 4' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x3e6f; pd 14' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdacf; pd 6' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xa571; pd 10; s 0xa678; pd 4' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xc2fa; pd 8' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xe8d4; pd 10' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdbd9; pd 14' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdbf2; pd 11' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdc02; pd 11' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdc20; pd 4' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x865a; pd 10' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x8716; pd 4; s 0xc398; pd 5' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xf63f; pd 5' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x7455; pd 8; s 0x7508; pd 9' /tmp/pd.bin
r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x9031; pd 12' /tmp/pd.bin

python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800
python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800 --check
```

The clustering is `ec/tools/pd_site_clusters.py`, a new tool. It finds the
sites with `trace_xdata_refs.py`'s own scan, region map and access
classification, reads the routine boundaries out of
`ec/decompiled/index.csv`, and asks which boundary a site falls inside. It
re-derives nothing about the dump layout or the 8051 encoding — the
discipline [`pd-index-geometry.md`](pd-index-geometry.md) §1 states. Its
table is `pd-0x07d0-07cc-clusters.csv`, committed beside this file the way
`ec-0x07d0-sites.csv` sits beside its own, one row per site per address, and
`--check` holds it against a fresh run.

The `0x07D0` sites themselves are not re-enumerated here.
[`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) and its `.csv` remain the
enumeration, and this tool's `--self-test` holds its derived runtime set
equal to that file's — a set, not a count, so a site gained on either side
moves the assertion.

## 2. `2000` is `0x07D0` in decimal

```console
$ grep -rn '\b2000\b' ec/decompiled/pd/*.c | wc -l
10
```

Ten occurrences, in four files, and every one of them sits where the
decompiled C needs a pointer. `2001` — the address one byte up — appears
nowhere in `ec/decompiled/pd/*.c`, which is itself the tell: this is not a
printer emitting arbitrary numbers, it is a printer emitting addresses it
computed. Nine of the ten are an **XDATA** pointer; the tenth is a **CODE**
one, and that difference is what the third transcript below is for.

Three of the ten settle it, each with the governing bytes beside it.

**`8576.c:38`, the cleanest.** The decompiled C reads
`read_xdata_at_dptr_34d9(*pbVar3 - 2,2000);`. The bytes that produced it:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x8599; pd 4; s 0x34d9; pd 3' /tmp/pd.bin
            0x00008599      9007d0         mov dptr, #0x07d0
            0x0000859c      1234d9         lcall 0x34d9
            0x0000859f      1237ed         lcall 0x37ed
            0x000085a2      1234cc         lcall 0x34cc
            0x000034d9      e0             movx a, @dptr
            0x000034da      75f05e         mov b, #0x5e
            0x000034dd      a4             mul ab
```

`0x34D9` is one instruction — `movx a,@dptr` — so `lcall 0x34D9` reads
whatever DPTR holds, and DPTR was loaded with `0x07D0` three bytes earlier
with no `inc dptr` and no intervening store. The decompiler hoisted that
DPTR into a call argument and printed it in decimal. The `*pbVar3 - 2` in
the same call is the same `movx`'s result being consumed; it is noise.

**`A5B3.c:48` and its twin `A571.c:64`, and this one is also the structural
finding of §4.** The decompiled C reads `sVar5 = 2000;` and then
`read_xdata_byte_to_r7((char *)(sVar5 + 1));`. The bytes:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xa5e5; pd 8' /tmp/pd.bin
            0x0000a5e5      9007d0         mov dptr, #0x07d0
            0x0000a5e8      e0             movx a, @dptr
            0x0000a5e9      129965         lcall 0x9965
            0x0000a5ec      1298df         lcall 0x98df
            0x0000a5ef      a3             inc dptr
            0x0000a5f0      129883         lcall 0x9883
            0x0000a5f3      e4             clr a
            0x0000a5f4      f5f0           mov b, a
```

`sVar5` is the 16-bit DPTR, so `sVar5 + 1` is `0x07D1` — and the `inc DPTR`
at `0xA5EF` is the machine's own version of that arithmetic, with the two
`lcall`s in between touching nothing in DPTR. **The `2000` is a base
conversion, and the `+ 1` on it is pointer arithmetic on an address**, which
is precisely why it reads like a stored value.

A caution on the citation: `A571.c` is not a decompile of the range
`A571.asm` shows. Ghidra decompiled the whole reachable function, which runs
past `0xA5B0` into `0xA5B4`–`0xA675`, so `A571.c`'s later half and
`A5B3.c`'s body are **the same code**, and both files' own headers say so.
The `sVar6 = 2000` pair is `0xA5E5`–`0xA5F0` above, not anything inside
`0xA571`–`0xA5B0`.

**`4D6F.c:188`, the one that is a CODE pointer rather than an XDATA one, and
therefore the decisive one.**

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x4b3c; pd 9; s 0x4b7a; pd 4' /tmp/pd.bin
            0x00004b3c      9007d2         mov dptr, #0x07d2
            0x00004b3f      e0             movx a, @dptr
            0x00004b40      9007d0         mov dptr, #0x07d0
        ┌─< 0x00004b43      7012           jnz 0x4b57
        │   0x00004b45      1234a5         lcall 0x34a5
        │   0x00004b48      12349b         lcall 0x349b
        │   0x00004b4b      c083           push dph
        │   0x00004b4d      c082           push dpl
        │   0x00004b4f      120faf         lcall 0x0faf
            0x00004b7a      12104d         lcall 0x104d
            0x00004b7d      ff             mov r7, a
            0x00004b7e      ff             mov r7, a
            0x00004b7f      ff             mov r7, a
```

The C reads `write4_inline_args();` then four `nop();` then `uVar6 = 2000;`
then `if (DAT_EXTMEM_07d2 == '\0')`. The four `nop()`s are the
`ff ff ff ff` at `0x4B7D`–`0x4B80`: `0x104D` is the inline-argument
trampoline, it copies the four code bytes at its own return address into
XDATA and tail-jumps past them
([`../../docs/findings/pd-inline-arg-trampoline.md`](../../docs/findings/pd-inline-arg-trampoline.md)),
so a linear decoder walks into them and Ghidra's C renders them as
instructions. `uVar6` is the DPTR that `0x4B40` loaded, hoisted across the
branch; the `if` that follows is the `jnz 0x4B57` at `0x4B43`, whose tested
value is the `movx` at `0x4B3F` reading `0x07D2`. The fall-through arm
opens with an `lcall` at `0x4B45`, and the C's `else` arm begins the same
way at `0x4B57`, which this window does not print. That is the next point.

**`puVar5` indexes the CODE table, and that is what the `2000` is for.** In
the C, every `puVar5['\x01'] = 0x48; puVar5['\x02'] = 0x4b;` pair patches
the two low bytes of a call instruction — `0x48`/`0x4b` is the low half of
`0x4B48`, the `lcall 0x349b` in the listing above. And inside each arm:

```c
        puVar5['\x01'] = (char)((ushort)uVar6 >> 8);
        puVar5['\x02'] = (char)uVar6;
```

Ghidra is splitting the 16-bit value `2000` into the high and low bytes of a
**CODE call target**. So at this site the `2000` is not an XDATA address at
all: it is a jump into the PD image's CODE space, at `0x07D0`, which
`ec-0x07d0-sites.md` §5 already places inside the float-formatting string
table (`"NaN"` at `0x07CD`, `"+INF"` at `0x07D1`).

Whether the decompiler's rendering of this relocated-call patch is
mechanically faithful is a separate question this file does not take up, and
the conclusion does not rest on it: **on either reading of that `2000` — an
XDATA pointer at the other nine sites, a CODE target here — it is the address
`0x07D0`, and a charge limit of 2000 is not something a USB-PD routine
points at.**

**What follows for the issue's either/or.** The issue offered two branches:
either the PD byte's role explains why Windows writes it, or the address
Windows reaches is a third address space again. **The second is the one the
evidence supports.** These are two different programs' XDATA maps that happen
to use the same number, and the resemblance to
`ADDR_BATTERY_CHARGE_LIMIT_DOWN = 2000` is a base conversion inside
Ghidra's C printer. This settles the *reading*; it does not settle what the
EC's own `0x07D0` is, which is a separate question with a separate answer
still open (§6).

## 3. The clustering

```console
$ python3 ec/tools/pd_site_clusters.py ec/firmware/GMxMGxx_11.800
```

| | `0x07D0` | `0x07CC` |
|---|---:|---:|
| `MOV DPTR` sites in the PD image | 254 | 6 |
| inside a routine `ec/decompiled/index.csv` commits | 43, across 19 | 1, across 1 |
| outside every committed routine boundary | 211 | 5 |

The `254` and the `6` are the figures `registers.yaml` records as
`static_refs` / `static_refs_pd_image` for `DBD1 (0x07D0)` and
`USB_C_POWER_PRIORITY (0x07CC)`, and the same ones
`trace_xdata_refs.py … --counts-only` prints; it is
`test_pd_site_clusters.py`'s `TestReconciliation` that holds the derived
totals against `registers.yaml`, so the three committed files cannot drift
apart without something going red.

**Read the second row with the third.** "43 of the 254 are inside a
committed routine" is a statement about the `pd` function boundaries in
`ec/decompiled/index.csv`, **not** about the firmware. A Ghidra function is
seeded from an annotation row; a site no annotation has named is in bytes
the project has no function over, and that is the ordinary state of a project
this size — `pd_unannotated_census.py` measures the residue and
`pd-index-geometry.md` §1 records the decision not to seed a routine at every
site. "211 outside" is not "211 sites with no routine", and it is not "211
sites that are not code" either: `ec-0x07d0-sites.md` §5 already found every
one of the 254 followed by a coherent `movx`, a handoff to a routine that
performs one, or a `ret` that leaves DPTR loaded.

The full table, one row per site, is `pd-0x07d0-07cc-clusters.csv`; the
`--check` that holds it is the same command with `--check`, and its refusal
behaviour is the subject of `test_pd_site_clusters.py`.

### 3.1 The nineteen routines

Five carry more than one site; the other fourteen are one site each, and
most of those fourteen are not really separate logic (see 3.2).

| sites | at | routine | what it is |
|---:|---|---|---|
| 13 | `0x8576` | `step_state_07d0_07d1` | the long state step; the only routine that both seeds and clears the pair |
| 8 | `0xC2FA` | `write_07d0_then_run_indexed_state_chain` | store the byte, then immediately use it as a `0x5E` array index |
| 4 | `0xDBD9` | `loop_c901_per_index_0x07d0` | a counted loop whose counter *is* the byte |
| 2 | `0xA5B3` | `and_16bit_fields_write_07d2_07d3` | the word read of §4, inside a routine that also ANDs `0x07D2`/`0x07D3` |
| 2 | `0xE8D4` | `index_07d0_by_0x17_then_fill_128d_and_call_f604` | store the byte, then use it as a `0x17` array index |
| 1 each | `0x4C12` `0x4C19` `0x4C20` `0x52EF` `0x531F` `0x7B0D` `0x856F` | `call_f739_then_return_dptr_07d0*` | seven byte-identical 3-instruction forwarders |
| 1 each | `0xA571` `0xA678` | `dispatch_on_state_07d0`, `inc_07d0_reenter_a571` | the dispatch and its own back edge |
| 1 each | `0x98A1` `0xAD3C` `0x8716` `0xC398` | `load_dptr_07d0`, `set_dptr_07d0`, `call_f22e_with_07d0`, `set_r7_r5_from_iram_then_read_07d0` | accessor thunks |
| 1 | `0xD085` | `decrement_00e2_and_tail_jump_to_d07b` | not an accessor: hands `0x07D0` to `0xB159` with `A = 6`, and this file does not follow that call |

### 3.2 Four shapes, not nineteen routines

Reading the committed listings rather than the row count, those nineteen
routines collapse into four shapes:

1. **The state step and its back edge** — `0x8576` and the `0xA571` /
   `0xA678` pair. `0x8576` seeds the byte from R7 and clears `0x07D1` in the
   same breath; `0xA571` dispatches on it; `0xA678` increments it in place
   and tail-jumps back to `0xA571`.

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x8576; pd 12' /tmp/pd.bin
               0x00008576      9007d0         mov dptr, #0x07d0
               0x00008579      ef             mov a, r7
               0x0000857a      f0             movx @dptr, a
               0x0000857b      e4             clr a
               0x0000857c      a3             inc dptr
               0x0000857d      f0             movx @dptr, a
               0x0000857e      9007d0         mov dptr, #0x07d0
               0x00008581      e0             movx a, @dptr
               0x00008582      fb             mov r3, a
               0x00008583      1234da         lcall 0x34da
               0x00008586      1236e9         lcall 0x36e9
               0x00008589      ef             mov a, r7
   ```

   The `clr a / inc dptr / movx @dptr,a` at `0x857B`–`0x857D` writes a zero
   to `0x07D1` — the pair is cleared together, which is the first hint of §4.

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xa571; pd 10; s 0xa678; pd 4' /tmp/pd.bin
               0x0000a571      9007d0         mov dptr, #0x07d0
               0x0000a574      e0             movx a, @dptr
               0x0000a575      ff             mov r7, a
               0x0000a576      c3             clr c
               0x0000a577      9401           subb a, #0x01
           ┌─< 0x0000a579      4003           jc 0xa57e
          ┌──< 0x0000a57b      02a681         ljmp 0xa681
          │└─> 0x0000a57e      ef             mov a, r7
          │    0x0000a57f      1298a5         lcall 0x98a5
          │    0x0000a582      129850         lcall 0x9850
               0x0000a678      9007d0         mov dptr, #0x07d0
               0x0000a67b      e0             movx a, @dptr
               0x0000a67c      04             inc a
               0x0000a67d      f0             movx @dptr, a
   ```

   The dispatch at `0xA571` reads the byte into R7, subtracts 1 and carries
   out of `0xA578`/`0xA579`: it is testing the byte against zero and branching
   on the borrow. `0xA678` is the matching increment — read, `inc a`, write,
   `ljmp 0xA571` — which makes `0x07D0` a **state variable advanced by its own
   dispatcher**, not a threshold anything compares against a limit.

2. **The byte as an array index, at two strides.** `0xC2FA` and `0xE8D4`
   have the same four-instruction head: take the caller's byte, store it,
   and multiply it.

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xc2fa; pd 8' /tmp/pd.bin
               0x0000c2fa      9007d0         mov dptr, #0x07d0
               0x0000c2fd      ef             mov a, r7
               0x0000c2fe      f0             movx @dptr, a
               0x0000c2ff      75f05e         mov b, #0x5e
               0x0000c302      a4             mul ab
               0x0000c303      24f8           add a, #0xf8
               0x0000c305      f582           mov dpl, a
               0x0000c307      e4             clr a
   ```

   `0xC2FA` forms `0x08F8 + low8(value × 0x5E)` — B is discarded by the
   `clr a` at `0xC307`, exactly as `pd-index-geometry.md` §8.1's correction
   records for this site — and `0xE8D4` forms `0x0A13 + value × 0x17` into
   R2:R1 and hands it to `0x128D`. Both are that file's §7 reading, reached
   from the other direction: this file does not re-decode the strides, it
   reads the routines that use them.

3. **The byte as a loop counter.** `0xDBD9` is the clearest statement of the
   role in the whole image, and it is the one that settles the "index or
   threshold" question: the loop bound *is* the byte.

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdbd9; pd 14' /tmp/pd.bin
               0x0000dbd9      9007cf         mov dptr, #0x07cf
               0x0000dbdc      ef             mov a, r7
               0x0000dbdd      f0             movx @dptr, a
               0x0000dbde      7e01           mov r6, #0x01
               0x0000dbe0      7f67           mov r7, #0x67
               0x0000dbe2      7d00           mov r5, #0x00
               0x0000dbe4      7b01           mov r3, #0x01
               0x0000dbe6      7a06           mov r2, #0x06
               0x0000dbe8      7961           mov r1, #0x61
               0x0000dbea      12128d         lcall 0x128d
               0x0000dbed      e4             clr a
               0x0000dbee      9007d0         mov dptr, #0x07d0
               0x0000dbf1      f0             movx @dptr, a
               0x0000dbf2      9007cf         mov dptr, #0x07cf
   ```

   (The four `mov rN,#imm` after `0xDBDD` are the argument block for the
   `0x128D` call; they are the only reason the reset at `0xDBED` is preceded
   by so much setup.)

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdbf2; pd 11' /tmp/pd.bin
               0x0000dbf2      9007cf         mov dptr, #0x07cf
               0x0000dbf5      e0             movx a, @dptr
               0x0000dbf6      fe             mov r6, a
               0x0000dbf7      a3             inc dptr
               0x0000dbf8      e0             movx a, @dptr
               0x0000dbf9      ff             mov r7, a
               0x0000dbfa      c3             clr c
               0x0000dbfb      9e             subb a, r6
           ┌─< 0x0000dbfc      502a           jnc 0xdc28
           │   0x0000dbfe      7b01           mov r3, #0x01
           │   0x0000dc00      e4             clr a
   ```

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdc02; pd 11' /tmp/pd.bin
               0x0000dc02      12c901         lcall 0xc901
               0x0000dc05      9007d0         mov dptr, #0x07d0
               0x0000dc08      e0             movx a, @dptr
               0x0000dc09      ff             mov r7, a
               0x0000dc0a      7b0b           mov r3, #0x0b
               0x0000dc0c      7d01           mov r5, #0x01
               0x0000dc0e      12c901         lcall 0xc901
               0x0000dc11      9007d0         mov dptr, #0x07d0
               0x0000dc14      e0             movx a, @dptr
               0x0000dc15      ff             mov r7, a
               0x0000dc16      900666         mov dptr, #0x0666
   ```

   `clr a; mov DPTR,#0x07d0; movx @dptr,a` at `0xDBED`–`0xDBF1` resets the
   counter to zero, then the loop reads `0x07CF` and — through one `inc
   dptr` — `0x07D0`, and loops while `0x07D0 < 0x07CF`, calling `0xC901`
   twice per pass. The loop's own increment is the second of the two
   increment-in-place sites in the whole image:

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdc20; pd 4' /tmp/pd.bin
               0x0000dc20      9007d0         mov dptr, #0x07d0
               0x0000dc23      e0             movx a, @dptr
               0x0000dc24      04             inc a
               0x0000dc25      f0             movx @dptr, a
   ```

   (The next instruction is the `sjmp 0xDBF2` back to the loop test.)
   Together the two windows say `for (i = 0; i < n; i++)` with the counter
   and the bound one byte apart in XDATA.

4. **Accessors, which are not fourteen pieces of logic.** The seven
   `call_f739_then_return_dptr_07d0*` entries are byte-identical:

   ```console
   $ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x8716; pd 4; s 0xc398; pd 5' /tmp/pd.bin
               0x00008716      9007d0         mov dptr, #0x07d0
               0x00008719      e0             movx a, @dptr
               0x0000871a      ff             mov r7, a
               0x0000871b      12f22e         lcall 0xf22e
               0x0000c398      af03           mov r7, r3
               0x0000c39a      12f75c         lcall 0xf75c
               0x0000c39d      ad07           mov r5, r7
               0x0000c39f      9007d0         mov dptr, #0x07d0
               0x0000c3a2      e0             movx a, @dptr
   ```

   `0x4C12`, `0x4C19`, `0x4C20`, `0x52EF`, `0x531F`, `0x7B0D` and `0x856F` are
   each `lcall 0xF739 ; mov DPTR,#0x07d0 ; ret` — a routine returning with DPTR
   left on the byte, which is the shape `ec-0x07d0-sites.md` §3 already named
   for its eight "no `movx`" sites. `0x98A1` and `0xAD3C` are bare
   `mov DPTR,#0x07d0` thunks with no `ret`; their committed `.c` bodies
   describe the work of the *next* entry, not the three bytes their listing
   shows, and are not read here as claims about `0x98A1`/`0xAD3C` themselves.

   The two accessors in the transcript above are the same shape with a
   difference worth naming: `0x8716` reads the byte into R7, calls `0xF22E`
   and returns **R7 as it stands after that call** — so the value it returns
   is `0xF22E`'s to change, and `8716.c`'s comment already records that its
   own C caches the byte and returns that instead. `0xC398` loads R7 and R5
   out of internal RAM at fixed `0x03` and `0x07` (the `af 03` / `ad 07`
   encodings are `mov Rn,direct`, not constants), calls `0xF75C`, and only
   then reads the byte. The one that is not an accessor at all is `0xD085`:
   its `0x07D0` site at `0xD0AA` loads DPTR and hands it to `0xB159` with
   `A = 6`, which is why the tool's report classes it `unresolved` — the
   routine's own work is on `0x00E2` and `0x0AE3`/`0x0AE4`, and `0x07D0` is
   an argument to a call this file does not follow.

**So: the 254 sites are not 254 independent decisions, and they are not one
function either.** They are one state variable, read by everything, written
by three entry points and two loops, and indexed by two different strides.
That is the reading `ec-0x07d0-sites.md` §4 reached from a linear decode;
this file reaches it from the committed routine boundaries, which is the gap
its §6 named.

## 4. The multi-byte structure: `0x07D0` is the low half of a 16-bit word

The issue asked whether `0x07D0` is the high byte of a 16-bit variable or an
array base. **It is both, and the two are not exclusive** — it is the low
byte of a little-endian 16-bit quantity whose high byte is `0x07D1`, *and*
the counter/array index §3.2 shows. Four places show the word; three are in
committed listings and one is not.

**The clearest, and inside a committed routine** — `0xA5B3`, shown in full in
§2: `mov DPTR,#0x07d0` / `movx A,@DPTR` / two `lcall`s that do not touch
DPTR / `inc DPTR` / `lcall 0x9883`, which is `movx A,@DPTR ; mov R7,A`. The
routine reads `[0x07D0]` then `[0x07D1]` as one word. The same routine ANDs
`[0x07D2]` and `[0x07D3]` into a 16-bit result immediately before, so the
block `0x07D0`–`0x07D3` is read as two 16-bit little-endian fields.

**The standalone one, in no committed routine** — `0xDACF`, which
`ec-0x07d0-sites.csv` records as a `0x07D0` site — a `read x2, walks 2
consecutive bytes (inc dptr)` row, which is what carries it to `0x07D1`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xdacf; pd 6' /tmp/pd.bin
            0x0000dacf      9007d0         mov dptr, #0x07d0
            0x0000dad2      e0             movx a, @dptr
            0x0000dad3      ff             mov r7, a
            0x0000dad4      a3             inc dptr
            0x0000dad5      e0             movx a, @dptr
            0x0000dad6      fd             mov r5, a
```

R7 takes the low byte and R5 the high — a 16-bit load, little-endian. There
is no `ec/decompiled/pd/DACF.*` listing, so this one is verified against the
image by r2 and against the committed site table, not against a decompile.

**The shift, and a correction to where it starts.** The `0x07D1` entry in
`registers.yaml` records that "`0x3E7D` shifts `[0x07D0]->0x07D1` and
`[0x07D1]->0x07D2` in one routine". The shift is real; the window that
performs it **begins at `0x3E6F`**, and `0x3E7D` is the `mov DPTR,#0x07d1` in
the middle of it (which is why `0x3E7D` is the address the `0x07D1` site
table records — the two statements are about different things and both hold):

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x3e6f; pd 14' /tmp/pd.bin
            0x00003e6f      9007d0         mov dptr, #0x07d0
            0x00003e72      123539         lcall 0x3539
            0x00003e75      ef             mov a, r7
            0x00003e76      12349b         lcall 0x349b
            0x00003e79      e0             movx a, @dptr
            0x00003e7a      fd             mov r5, a
            0x00003e7b      a3             inc dptr
            0x00003e7c      e0             movx a, @dptr
            0x00003e7d      9007d1         mov dptr, #0x07d1
            0x00003e80      cd             xch a, r5
            0x00003e81      f0             movx @dptr, a
            0x00003e82      a3             inc dptr
            0x00003e83      ed             mov a, r5
            0x00003e84      f0             movx @dptr, a
```

`[0x07D0]` and `[0x07D1]` are read into R5 and A across the `inc DPTR` at
`0x3E7B`, then `xch a,r5` at `0x3E80` swaps them and both are written one
byte up: `0x07D1 ← [0x07D0]`, `0x07D2 ← [0x07D1]`. It is **straight-line,
not a loop** — no branch and no counter is involved, and the `xch` is what
makes it a swap rather than two stores of the same value. There is no
`3E6F` or `3E7D` entry in `ec/decompiled/index.csv`, so this window is
verified against the image and the committed site tables, not a decompile.

**The pair is written together too.** `0x8576` seeds `[0x07D0]` from R7 and
zeroes `[0x07D1]` (§3.2), and later in the same routine — `0x865A` is one of
its sites — R7, loaded from `[0x07D0]` at `0x865D` and carried through
`0xF61C`, which is not decoded here and may have changed it, is stored into
`[0x07D1]`:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x865a; pd 10' /tmp/pd.bin
            0x0000865a      9007d0         mov dptr, #0x07d0
            0x0000865d      e0             movx a, @dptr
            0x0000865e      ff             mov r7, a
            0x0000865f      12f61c         lcall 0xf61c
            0x00008662      9007d1         mov dptr, #0x07d1
            0x00008665      ef             mov a, r7
            0x00008666      f0             movx @dptr, a
        ┌─< 0x00008667      8005           sjmp 0x866e
        │   0x00008669      e4             clr a
        │   0x0000866a      9007d1         mov dptr, #0x07d1
```

So the byte is not an isolated 8-bit cell with a neighbour that happens to be
popular. The PD firmware holds `0x07D0` and `0x07D1` as the two halves of
overlapping 16-bit windows, and `0x07D2`/`0x07D3` as another, which is what
`registers.yaml`'s `0x07D1` entry already concluded from the site counts and
what the listings above confirm byte for byte.

**What this does not give.** The *contents* of the indexed arrays and the
identity of the state machine are still unnamed.
`ec-0x07d0-sites.md` §4 declined to guess and that refusal stands: naming
them needs a PD packet capture or a string correlation this method does not
reach, and no string in the image was correlated with any of these routines.

## 5. `0x07CC`, the same pass

Six sites, all in the PD image, one inside a committed routine.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0xf63f; pd 5' /tmp/pd.bin
            0x0000f63f      9007cc         mov dptr, #0x07cc
            0x0000f642      ef             mov a, r7
            0x0000f643      f0             movx @dptr, a
            0x0000f644      900945         mov dptr, #0x0945
            0x0000f647      ed             mov a, r5
```

`0xF63F` `store_r7_to_07cc_r5_to_0945` is a **whole-byte** write of R7 to
`0x07CC`, immediately followed by a whole-byte write of R5 to `0x0945`. That
matters for issue #8: `registers.yaml` records the vendor's
`SetTypeCAdaptorSwitch` setting and clearing **bit 7** of this byte, and
nothing here is a bit-7 operation. No read, no compare, DPTR left on
`0x0945`.

The other five are outside every committed routine boundary, and four of them
sit in a listing gap worth naming: `0x7455`, `0x745E`, `0x7508` and `0x7519`
are in the neighbourhood of `7392 count_07cb_up_to_3_over_07ca_records`, but
`index.csv` records that routine as 141 bytes starting at `0x7392` — through
`0x741E` — and `7392.asm` itself has a display gap from `0x73ED` to `0x7551`.
The four sites are in bytes that neither the committed boundary nor the
committed listing covers, which is the honest form of "outside every
committed routine" for them.

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x7455; pd 8; s 0x7508; pd 9' /tmp/pd.bin
            0x00007455      9007cc         mov dptr, #0x07cc
            0x00007458      f0             movx @dptr, a
            0x00007459      9007ce         mov dptr, #0x07ce
            0x0000745c      e0             movx a, @dptr
            0x0000745d      ff             mov r7, a
            0x0000745e      9007cc         mov dptr, #0x07cc
            0x00007461      e0             movx a, @dptr
            0x00007462      fd             mov r5, a
            0x00007508      9007cc         mov dptr, #0x07cc
            0x0000750b      e0             movx a, @dptr
            0x0000750c      d082           pop dpl
            0x0000750e      d083           pop dph
            0x00007510      75f004         mov b, #0x04
            0x00007513      1210bc         lcall 0x10bc
            0x00007516      121041         lcall 0x1041
            0x00007519      9007cc         mov dptr, #0x07cc
            0x0000751c      e0             movx a, @dptr
```

Those four are one another's neighbours and read as a single loop body.
`0x7455` **stores** A into `0x07CC` — the window that establishes what A holds
sits above the eight instructions printed here and is not decoded in this
file, so the value is not claimed. `0x745E` reads `0x07CC` into R5 and
compares it against R7, which `0x7459`–`0x745D` just loaded from `0x07CE`:
a bound one page up. `0x7519` is `[0x07CC] += 1` in place followed by
`ljmp 0x7459`, re-entering that compare.

`0x7508` is the one that does not fit that reading, and it is worth being
precise about which half of it survives. It reads `0x07CC` into A, and the
next two instructions are `pop dpl` / `pop dph` — which write DPTR's halves,
not A. A therefore still holds `[0x07CC]` when the `0x10BC` call is made, and
`ec/decompiled/pd/10BC.asm` shows that helper is `mul AB / add A,DPL / mov
DPL,A / mov A,B / addc A,DPH / mov DPH,A / ret` — `DPTR += A × B`, with B set
to `0x04` at `0x7510`. So the **value** read is live, consumed as a ×4 index
into the DPTR the two pops supply; what is dead on this path is the
`mov DPTR,#0x07CC` the site itself loaded, which the pops overwrite before
the helper ever sees it. The site `pd-0x07d0-07cc-clusters.csv` classifies
`read x1` is therefore a real `movx a,@dptr` and nothing more, and the
encoding is why it is counted as a read; whether some other path reaches the
same `mov DPTR` with a different live A was not determined here.

*** CORRECTION 2026-10-02 (issue #25 fix round), leaving the paragraph above
as it was written: it read "which overwrite A before it can be used" and
concluded "the A it multiplies is not the byte that was read" and "**on this
path the value read is not consumed**". All three are wrong, and the error is
that `pop dpl` / `pop dph` were read as touching A — they touch DPTR. The
bytes are `90 07 cc | e0 | d0 82 | d0 83 | 75 f0 04 | 12 10 bc`, so the two
pops follow the `movx` without disturbing it. The paragraph also stated the
helper's own contract correctly (`DPTR += A × B`, B = `0x04`) and then drew
the opposite conclusion from it. Nothing else in §5 depends on this: the
other three `0x07CC` sites are unaffected, and the site count and
classification are unchanged. The same inverted sentence was copied into
`registers.yaml`'s `USB_C_POWER_PRIORITY` note and is corrected there.

The fifth is a different shape and a useful contrast:

```console
$ r2 -a 8051 -e scr.color=0 -e asm.comments=false -q -c 's 0x9031; pd 12' /tmp/pd.bin
            0x00009031      9007ca         mov dptr, #0x07ca
            0x00009034      e0             movx a, @dptr
            0x00009035      fe             mov r6, a
            0x00009036      e4             clr a
            0x00009037      2444           add a, #0x44
            0x00009039      9007cc         mov dptr, #0x07cc
            0x0000903c      fd             mov r5, a
            0x0000903d      ee             mov a, r6
            0x0000903e      34fd           addc a, #0xfd
            0x00009040      fc             mov r4, a
            0x00009041      e0             movx a, @dptr
            0x00009042      75f004         mov b, #0x04
```

`0x9039` reads `0x07CC` into A, multiplies by `0x04` and adds the carry
chain, and the window goes on to hand the 16-bit result back in `DPH:DPL` — a
pointer builder, `0x07CC` read as a `0x04`-scaled index, not written. Note
that this window is entered from `0x9031`, which loads `0x07CA`, and
**neither address is in `ec/decompiled/index.csv`**; the `0x07CA` read is the
one whose result the `0x44` is added to.

**Net for `0x07CC`.** Six sites: two whole-byte writes, one read-modify-write
increment, and three reads — one a loop counter compared against `0x07CE`,
one a ×4 index into a popped DPTR (`0x7508`, per the correction above), one a
pointer-building index. Same reading as `0x07D0` — an index/state byte
of the PD firmware — and again nothing about the EC's own `0x07CC`, which the
EC image references zero times by this method. `registers.yaml` re-graded
this entry to `unknown-not-absent` on 2026-09-27 (#32) on exactly that basis,
and nothing here moves it. Issue #8's live half is untouched by this file.

## 6. What this does not establish

- **Nothing about the EC's `0x07D0` or `0x07CC`.** This is the first line of
  the file and the reason it exists, restated because the `2000` coincidence
  makes it easy to lose. The register `ECSpec.cs` names and Windows writes
  lives in the main EC image's XDATA map, which references `0x07D0` zero times
  by this method:

  ```console
  $ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --counts-only
  0x07D0: 254 direct MOV DPTR site(s)  pd-image=254
  ```

  `pd-image=254` and no `ec=` term: every one is the other program.

- **`DO-NOT-WRITE-BLIND` stands, and this file says so rather than leaving it
  to be inferred.** On this evidence the grade does not move, and the reason
  is structural rather than a matter of how much was decoded: a decode of the
  *PD* image is not evidence about an *EC* byte for which the EC image has no
  site at all. The gap §4 and §3 close is "what the PD firmware's `0x07D0` is
  made of", and #1's live test is about the EC's `0x07D0`. A structural
  reading of one cannot substitute for an observation of the other, and
  nothing here is an observation of the other. If a later pass finds a
  committed writer of `0x07D0` **in the EC image**, that would move the grade
  and would be re-graded on its own evidence — not inferred from this one.

- **The paired `0x07B9`/`0x07D0` live write is still the experiment that would
  settle the EC-side question**, exactly as `docs/findings.md` §5 and
  `ec-0x07d0-sites.md` §7 describe it, and it is still a human at the
  machine. No register was read back, no write was attempted, and no hardware
  was involved in any statement above.

- **Zero EC-side references is "not found by this method", not "absent."**
  It is the same signal §4c retracted for `0x07B9`, with the same
  indirect-addressing blind spot: a `movx` through a computed DPTR carries no
  `90 07 D0` bytes for any scan to find. The honest status is undetermined.

- **"211 outside every committed routine boundary" is about this project.**
  It is not a claim that those sites have no function, that they are not
  code, or that they are unreachable. §3 says why, and the four 16-bit windows
  of §4 include two (`0xDACF`, `0x3E6F`) that are structurally the most
  informative windows in the image and are in exactly that residue.

- **Nothing about what the indexed arrays contain**, and no state machine is
  named. §4's last paragraph says why; the refusal in
  `ec-0x07d0-sites.md` §4 stands unchanged.

- **Nothing from the Windows side was re-derived here.** The `ECSpec.cs`
  constants are cited as they stand; no anti-tamper-protected method body was
  involved (`windows/antitamper/README.md`).

- **The tool is not in any gate.** `.github/` is template-copied and this
  branch's token has no `workflow` scope, so the deep tier's hand-listed
  `--self-test` set does not gain a line here. It does run under the cheap
  tier's `check_python_syntax`, which globs `ec/tools/*.py`. Adding it to
  `agent-gates.sh` is a human's change.

## 7. What would actually settle the rest

- **EC-side:** the paired `0x07B9`/`0x07D0` write, a human at the machine. The
  static route that does not need hardware is decrypting the
  `BatteryProtection2` bodies (`windows/antitamper/`, issue #3); it is a
  separate issue and this file does not touch it.
- **PD-side:** a PD packet capture, or a correlation of these routines
  against the image's own strings
  ([`pd-image-strings.csv`](pd-image-strings.csv)). Neither is reachable from
  a runner. What *is* reachable, and is the natural next tranche, is seeding
  Ghidra functions at a handful of the §3.1 singleton sites so the clustering
  covers more than 43 — deliberately not done here, because minting rows means
  a `--mode rebuild-project` run and `CLAUDE.md` records that two branches
  which both rebuild one cannot merge.
