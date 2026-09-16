# `0x07E2`-`0x07E5` ("battery lightbar") reference sites — EC firmware `GMxMGxx_11.800`

Traced with `ec/tools/trace_xdata_refs.py`; every disassembly excerpt below was
re-checked against `r2 -a 8051` on the same image (command line beside each
one).

**Headline, and it is not the question the issue asked.** All 38 reference
sites are in a *second, self-contained 8051 firmware image* that shares the
flash dump with the EC firmware — an `ITE8850-PD` USB Power-Delivery image at
file offset `0x20000`. Its XDATA `0x07E2` is not the EC's XDATA `0x07E2`; they
are different address spaces belonging to different programs. The main EC
image (common area + banks 0/1, file `0x00000`-`0x17FFF`) contains **zero**
direct references to any of the four addresses.

So the `15 / 9 / 4 / 10` counts that made these registers look implemented are
an artefact of counting `MOV DPTR` sites across the whole 256 KiB file. What
the PD image does with its own `0x07E2` is traced below for completeness, but
it is not evidence about the `uniwill-laptop` lightbar registers either way.

What this does **not** establish: that the EC ignores `0x07E2`-`0x07E5`. That
is the same "zero direct references" signal that `docs/findings.md` §4c
retracted for `0x07B9`, and it carries the same blind spot (indirect/pointer
addressing is invisible to this method). The honest position is *undetermined*,
now for a narrower reason than before. §4 below is the live probe that would
settle it, left for a human with the machine.

## 1. Reproducing the site map

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 \
          0x07E2 0x07E3 0x07E4 0x07E5 --counts-only
0x07E2: 15 direct MOV DPTR site(s)  pd-image=15

0x07E3: 9 direct MOV DPTR site(s)  pd-image=9

0x07E4: 4 direct MOV DPTR site(s)  pd-image=4

0x07E5: 10 direct MOV DPTR site(s)  pd-image=10
```

15/9/4/10 is exactly what `scan_refs.py` reports as the file-wide total and
what `annotations/registers.yaml` and the issue both cite — the two tools agree
on *where the bytes are*; they disagreed only about what a file-wide total
means, and `scan_refs.py` now prints the same `ec=`/`pd=` split rather than the
bare total that caused this.
Drop `--counts-only` for the per-site decode, add `--r2-commands` for
paste-able seek lines.

## 2. Why `0x20000`-`0x2FFFF` is a separate program

Four independent facts, each re-runnable against the committed image:

1. **Its own identity strings.** File `0x20040` = `ITE8850-PD`, `0x20160` =
   `ProtoVer:01.00`, `0x20170` = `DriverVer:01.00`, `0x2E1C0` =
   `UsbPdVer:01.00`. The region is full of USB-PD protocol strings the main EC
   image has none of: `PR Swap`, `DR Swap`, `FR Swap`, `Error Recovery`,
   `SRC Negotiate done`, `SINK Negotiate done`, `VCONN On`, `Set VBUS 5V`.
   The main EC image's own identity string is `ITE EC-V14.6` at file `0x50`
   (`ec/README.md`).
2. **Its own 8051 vector table, at its own offset 0.** File `0x20000` onward:

   | vector | main EC (file `0x00000`+) | this region (file `0x20000`+) |
   |---|---|---|
   | reset `0x00` | `ljmp 0x0070` | `ljmp 0x0500` |
   | `0x03` | `ljmp 0x052F` | `ljmp 0x0056` |
   | `0x0B` | `ljmp 0x0530` | `ljmp 0x0094` |
   | `0x13` | `ljmp 0x0556` | `ljmp 0x00B2` |
   | `0x1B` | `ljmp 0x05B6` | `ljmp 0x00F0` |

   Two programs cannot both own CODE `0x0000` on one running core.
3. **Its reset vector lands on a C startup stub.** `0x0500` in the region's own
   address space is the textbook Keil/SDCC IDATA clear:

   ```console
   $ dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1
   $ r2 -a 8051 -e scr.color=0 -q -c 's 0x500; pd 5' /tmp/pd.bin
   0x00000500      787f    mov r0, #0x7f
   0x00000502      e4      clr a
   0x00000503      f6      mov @r0, a
   0x00000504      d8fd    djnz r0, 0x0503
   0x00000506      900000  mov dptr, #0x0000
   ```
4. **It is not one of the EC's CODE banks.** It contains none of the Keil BL51
   bank-switch stub prologues (`C0 08 74`) that appear 4 times in the main EC
   image, its `ljmp`/`lcall` targets spread flat across the full 64 KiB rather
   than clustering in a `0x8000` window, and `find_banks.py` finds zero callers
   for banks 2 and 3 in this build.

Whether that image runs on a physically separate PD controller or is a payload
the EC hands off is *not* determined here, and does not change the conclusion:
its variables are allocated in its own XDATA map.

## 3. What the PD image does with `0x07E2`-`0x07E5`

Included because it is what the trace actually shows, not because it says
anything about the lightbar. All addresses are runtime addresses in the flat
`/tmp/pd.bin` image from §2.

### 3.1 The four bytes sit inside one dense variable block

`MOV DPTR` histogram of the whole `0x07xx` page within the PD image: every byte
from `0x07CF` to `0x07E9` is referenced, with no gaps — `0x07D0`:254,
`0x07D6`:142, `0x07D1`:76, `0x07D7`:71, `0x07D4`:68, `0x07CF`:55, `0x07DA`:52,
… `0x07E2`:15, `0x07E3`:9, `0x07E4`:4, `0x07E5`:10, `0x07E6`:6. That is the
shape of a compiler-allocated global block, not of a four-byte control
register window that happens to start where `uniwill-laptop` expects one.

### 3.2 They are accessed as multi-byte quantities, not as four control bytes

Nine of the 38 sites write or read `0x07E2`/`0x07E4` as adjacent pairs through
`inc dptr`, in Keil's big-endian R6:R7 16-bit idiom:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x6e54; pd 6' /tmp/pd.bin
0x00006e54      9007e2   mov dptr, #0x07e2
0x00006e57      ee       mov a, r6
0x00006e58      f0       movx @dptr, a
0x00006e59      a3       inc dptr
0x00006e5a      ef       mov a, r7
0x00006e5b      f0       movx @dptr, a
```

and read back the same way, three bytes deep at `0x6E5C`:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x6e5c; pd 8' /tmp/pd.bin
0x00006e5c      9007e2   mov dptr, #0x07e2
0x00006e5f      e0       movx a, @dptr
0x00006e60      fe       mov r6, a
0x00006e61      a3       inc dptr
0x00006e62      e0       movx a, @dptr
0x00006e63      ff       mov r7, a
0x00006e64      a3       inc dptr
0x00006e65      e0       movx a, @dptr
```

`0x6E26`-`0x6E31` compares `{0x07E4,0x07E5}` against `B:R7` as one 16-bit
`subb` pair and branches on the borrow — a numeric `<` on a 16-bit variable,
not a colour byte test.

### 3.3 One site packs them as bit-fields

`0x8F34`-`0x8F53` shifts three of the bytes into disjoint bit positions and
ORs them into one value (`0x07E4` << 3 masked `0xF8`, `0x07E3` rotated masked
`0x80`, `0x07E5` << 2):

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x8f34; pd 15' /tmp/pd.bin
0x00008f34      9007e4   mov dptr, #0x07e4
0x00008f37      e0       movx a, @dptr
0x00008f38      33       rlc a
0x00008f39      33       rlc a
0x00008f3a      33       rlc a
0x00008f3b      54f8     anl a, #0xf8
0x00008f3d      fc       mov r4, a
0x00008f3e      9007e3   mov dptr, #0x07e3
0x00008f41      e0       movx a, @dptr
0x00008f42      c4       swap a
0x00008f43      33       rlc a
0x00008f44      33       rlc a
0x00008f45      33       rlc a
0x00008f46      5480     anl a, #0x80
0x00008f48      4c       orl a, r4
```

Naming the resulting field layout (a PD message header? a source/sink
capability object?) would be a guess — the containing routines were not traced
to a transmit path, and nothing here was correlated with a PD packet capture.
It is recorded as "packed bit-fields in the PD stack, role unidentified".

### 3.4 Full site table

From `trace_xdata_refs.py` without `--counts-only`; "handoff" means the site
loads DPTR and `lcall`s a helper, so the direction is not resolvable at the
site. File offsets are in the dump; runtime = file − `0x20000`.

The eleven handoff rows carry what the *callee's* own entry point does with
that DPTR, from `register_ref_table.py --callee-depth 1`, which decodes one
level down the way §3 of [`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) and §3 of
[`pd-xdata-overlap.md`](pd-xdata-overlap.md) did by hand for `0x07D0` and
`0x04A6`. §3.5 lists the eight callees and cross-reads each against `r2`.

The first block below keeps only the four rows this file is about; the other
25 addresses the tool prints, and the separator row, are elided where marked.
Nothing else is edited.

```console
$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1
| addr | register | total | main EC | PD | read | write | r+w | movc | jmp | handoff->read | handoff->write | handoff->r+w | handoff->unresolved | none |
[...25 other rows...]
| `0x07E2` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 15 | 0 | 15 | 7 | 4 | 0 | 0 | 0 | 2 | 1 | 0 | 1 | 0 |
| `0x07E3` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 9 | 0 | 9 | 2 | 2 | 0 | 0 | 0 | 1 | 4 | 0 | 0 | 0 |
| `0x07E4` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 4 | 0 | 4 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `0x07E5` | `LIGHTBAR_BAT_CTRL / RED / GREEN / BLUE` | 10 | 0 | 10 | 5 | 3 | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
19 entries / 29 addresses: class buckets sum to the site count and main + PD to the file-wide total for every address

$ python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1 --csv \
  | python3 -c "
import csv, sys
for r in csv.DictReader(sys.stdin):
    if r['addr'].startswith('0x07E') and r['callee']:
        print(r['addr'], r['runtime'], r['callee'], '|', r['class'])"
0x07E2 0x04F9 0xB1F2 | handed to lcall/ljmp (unresolved)
0x07E2 0x8F94 0x9CC2 | handed to lcall/ljmp -> callee reads
0x07E2 0x8FCA 0x9CA4 | handed to lcall/ljmp -> callee reads
0x07E2 0xB7A4 0x10E8 | handed to lcall/ljmp -> callee writes
0x07E3 0x5F03 0x10E8 | handed to lcall/ljmp -> callee writes
0x07E3 0x6482 0x35DA | handed to lcall/ljmp -> callee writes
0x07E3 0x64AD 0x35DA | handed to lcall/ljmp -> callee writes
0x07E3 0x81A8 0x10E8 | handed to lcall/ljmp -> callee writes
0x07E3 0xD833 0x10C8 | handed to lcall/ljmp -> callee reads
0x07E5 0x6610 0x1041 | handed to lcall/ljmp -> callee writes
0x07E5 0x662D 0x383A | handed to lcall/ljmp (unresolved)
```

Every one of the eleven sites is a bare `mov dptr,#addr` immediately followed
by the `lcall` — the `window` column holds nothing else — so no instruction
changes DPTR between the two, and the byte spans named in the table below are
the helper's own `inc dptr` run from the address the site loaded. That is a
statement about the instructions, not about anything observed running.

| addr | file | runtime | what the site does |
|---|---|---|---|
| `0x07E2` | `0x204F9` | `0x04F9` | handoff → `lcall 0xB1F2` → unresolved (§3.5) |
| `0x07E2` | `0x26E00` | `0x6E00` | write ×2, walks 2 bytes |
| `0x07E2` | `0x26E54` | `0x6E54` | write ×2, walks 2 bytes |
| `0x07E2` | `0x26E5C` | `0x6E5C` | read ×3, walks 3 bytes |
| `0x07E2` | `0x28EB3` | `0x8EB3` | write ×2, walks 3 bytes |
| `0x07E2` | `0x28F00` | `0x8F00` | read ×1 |
| `0x07E2` | `0x28F6F` | `0x8F6F` | read ×1 |
| `0x07E2` | `0x28F94` | `0x8F94` | handoff → `lcall 0x9CC2` → read ×1 |
| `0x07E2` | `0x28FCA` | `0x8FCA` | handoff → `lcall 0x9CA4` → read ×1 |
| `0x07E2` | `0x28FED` | `0x8FED` | read ×1 |
| `0x07E2` | `0x29007` | `0x9007` | read ×1 |
| `0x07E2` | `0x2B7A4` | `0xB7A4` | handoff → `lcall 0x10E8` → write ×3 (`0x07E2`-`0x07E4`) |
| `0x07E2` | `0x2CEB4` | `0xCEB4` | write ×1 |
| `0x07E2` | `0x2CEE7` | `0xCEE7` | read ×1 |
| `0x07E2` | `0x2CF0B` | `0xCF0B` | read ×1 |
| `0x07E3` | `0x25F03` | `0x5F03` | handoff → `lcall 0x10E8` → write ×3 (`0x07E3`-`0x07E5`) |
| `0x07E3` | `0x26482` | `0x6482` | handoff → `lcall 0x35DA` → write ×2 (`0x07E3`-`0x07E4`) |
| `0x07E3` | `0x264AD` | `0x64AD` | handoff → `lcall 0x35DA` → write ×2 (`0x07E3`-`0x07E4`) |
| `0x07E3` | `0x264BE` | `0x64BE` | write ×2, walks 2 bytes |
| `0x07E3` | `0x264DD` | `0x64DD` | read ×2, walks 2 bytes |
| `0x07E3` | `0x281A8` | `0x81A8` | handoff → `lcall 0x10E8` → write ×3 (`0x07E3`-`0x07E5`) |
| `0x07E3` | `0x28F3E` | `0x8F3E` | read ×1 (bit-field pack, §3.3) |
| `0x07E3` | `0x2CEC7` | `0xCEC7` | write ×2, walks 2 bytes |
| `0x07E3` | `0x2D833` | `0xD833` | handoff → `lcall 0x10C8` → read ×3 (`0x07E3`-`0x07E5`) |
| `0x07E4` | `0x26DD1` | `0x6DD1` | write ×2, walks 2 bytes |
| `0x07E4` | `0x26E2B` | `0x6E2B` | read ×1 (16-bit `subb`, §3.2) |
| `0x07E4` | `0x26E4C` | `0x6E4C` | read ×2, walks 2 bytes |
| `0x07E4` | `0x28F34` | `0x8F34` | read ×1 (bit-field pack, §3.3) |
| `0x07E5` | `0x254AC` | `0x54AC` | write ×3, walks 3 bytes |
| `0x07E5` | `0x26610` | `0x6610` | handoff → `lcall 0x1041` → write ×4 (`0x07E5`-`0x07E8`) |
| `0x07E5` | `0x2662D` | `0x662D` | handoff → `lcall 0x383A` → unresolved (§3.5) |
| `0x07E5` | `0x26C65` | `0x6C65` | write ×1 |
| `0x07E5` | `0x26E26` | `0x6E26` | read ×1 (16-bit `subb`, §3.2) |
| `0x07E5` | `0x28EF1` | `0x8EF1` | read ×1 |
| `0x07E5` | `0x28F4A` | `0x8F4A` | read ×2, walks 2 bytes |
| `0x07E5` | `0x28FB9` | `0x8FB9` | read ×1 |
| `0x07E5` | `0x28FE6` | `0x8FE6` | read ×1 |
| `0x07E5` | `0x2CEDE` | `0xCEDE` | write ×1 |

### 3.5 The eight callees behind the handoffs

Eight distinct entry points take the eleven handoffs. Each is shown below as
an independent `r2 -a 8051` listing against the flat PD image from §2
(`dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1`),
and each agrees instruction-for-instruction with the `callee_window` column
`--callee-depth 1 --csv` prints.

Four of the eight are Keil multi-byte move helpers — a run of `movx` plus
`inc dptr` that copies two, three or four bytes between XDATA and a register
group. Three of those four live in the same `0x10xx` compiler-library
neighbourhood as the `DPTR += A × B` arithmetic helper at `0x10BC` that
[`pd-xdata-overlap.md`](pd-xdata-overlap.md) §3 found behind `0x04A6`'s PD
handoffs, but they are not that routine and not its kind: these dereference
DPTR, `0x10BC` only adds to it. Two more load a single byte, and the last two
hand DPTR on again without touching it.

| callee | sites | head | reading |
|---|---|---|---|
| `0x10E8` | 3 | `mov a,r3 ; movx @dptr,a ; inc dptr ; mov a,r2 ; movx @dptr,a ; inc dptr ; mov a,r1 ; movx @dptr,a ; ret` | 3-byte store from `R3:R2:R1` |
| `0x35DA` | 2 | `mov a,r6 ; movx @dptr,a ; inc dptr ; mov a,r7 ; movx @dptr,a` | 2-byte store from `R6:R7`, then reloads DPTR with `0x07D8` and calls `0x10C8` on it |
| `0x10C8` | 1 | `movx a,@dptr ; mov r3,a ; inc dptr ; movx a,@dptr ; mov r2,a ; inc dptr ; movx a,@dptr ; mov r1,a ; ret` | 3-byte load into `R3:R2:R1`, the inverse of `0x10E8` |
| `0x1041` | 1 | `mov a,r4 ; movx @dptr,a ; inc dptr ; … ; mov a,r7 ; movx @dptr,a ; ret` | 4-byte store from `R4:R5:R6:R7` |
| `0x9CC2` | 1 | `mov r7,a ; movx a,@dptr ; mov r6,a ; mov b,#0x67 ; ret` | 1-byte load, returned in `R6`, leaving `0x67` in `B` |
| `0x9CA4` | 1 | `movx a,@dptr ; mov r7,a ; mov r6,#0x00 ; mov r4,#0x01 ; mov r5,#0x67 ; ljmp 0x0C7A` | 1-byte load widened to 16 bits, then tail-calls `0x0C7A` — whose head is the Keil 16×16 multiply — against `R4:R5` = `0x0167` |
| `0xB1F2` | 1 | `lcall 0x10C8 ; mov a,#0x01 ; ljmp 0x0C46` | **unresolved** — hands DPTR on again |
| `0x383A` | 1 | `lcall 0x0FCB ; clr c ; ljmp 0x0F0E` | **unresolved** — hands DPTR on again |

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x10e8; pd 9' /tmp/pd.bin
            0x000010e8      eb             mov a, r3
            0x000010e9      f0             movx @dptr, a
            0x000010ea      a3             inc dptr
            0x000010eb      ea             mov a, r2
            0x000010ec      f0             movx @dptr, a
            0x000010ed      a3             inc dptr
            0x000010ee      e9             mov a, r1
            0x000010ef      f0             movx @dptr, a
            0x000010f0      22             ret
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x10c8; pd 9' /tmp/pd.bin
            0x000010c8      e0             movx a, @dptr
            0x000010c9      fb             mov r3, a
            0x000010ca      a3             inc dptr
            0x000010cb      e0             movx a, @dptr
            0x000010cc      fa             mov r2, a
            0x000010cd      a3             inc dptr
            0x000010ce      e0             movx a, @dptr
            0x000010cf      f9             mov r1, a
            0x000010d0      22             ret
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x35da; pd 8' /tmp/pd.bin
            0x000035da      ee             mov a, r6
            0x000035db      f0             movx @dptr, a
            0x000035dc      a3             inc dptr
            0x000035dd      ef             mov a, r7
            0x000035de      f0             movx @dptr, a
            0x000035df      9007d8         mov dptr, #0x07d8
            0x000035e2      1210c8         lcall 0x10c8
            0x000035e5      020f45         ljmp 0x0f45
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x1041; pd 12' /tmp/pd.bin
            0x00001041      ec             mov a, r4
            0x00001042      f0             movx @dptr, a
            0x00001043      a3             inc dptr
            0x00001044      ed             mov a, r5
            0x00001045      f0             movx @dptr, a
            0x00001046      a3             inc dptr
            0x00001047      ee             mov a, r6
            0x00001048      f0             movx @dptr, a
            0x00001049      a3             inc dptr
            0x0000104a      ef             mov a, r7
            0x0000104b      f0             movx @dptr, a
            0x0000104c      22             ret
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9cc2; pd 5' /tmp/pd.bin
            0x00009cc2      ff             mov r7, a
            0x00009cc3      e0             movx a, @dptr
            0x00009cc4      fe             mov r6, a
            0x00009cc5      75f067         mov b, #0x67
            0x00009cc8      22             ret
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x9ca4; pd 6' /tmp/pd.bin
            0x00009ca4      e0             movx a, @dptr
            0x00009ca5      ff             mov r7, a
            0x00009ca6      7e00           mov r6, #0x00
            0x00009ca8      7c01           mov r4, #0x01
            0x00009caa      7d67           mov r5, #0x67
            0x00009cac      020c7a         ljmp 0x0c7a
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xb1f2; pd 3' /tmp/pd.bin
            0x0000b1f2      1210c8         lcall 0x10c8
            0x0000b1f5      7401           mov a, #0x01
            0x0000b1f7      020c46         ljmp 0x0c46
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x383a; pd 3' /tmp/pd.bin
            0x0000383a      120fcb         lcall 0x0fcb
            0x0000383d      c3             clr c
            0x0000383e      020f0e         ljmp 0x0f0e
```

and the two routines the last three rows lean on — `0x0C7A`, which `0x9CA4`
tail-calls, and `0x0FCB`, which `0x383A` hands DPTR to:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0c7a; pd 8' /tmp/pd.bin
            0x00000c7a      ef             mov a, r7
            0x00000c7b      8df0           mov b, r5
            0x00000c7d      a4             mul ab
            0x00000c7e      a8f0           mov r0, b
            0x00000c80      cf             xch a, r7
            0x00000c81      8cf0           mov b, r4
            0x00000c83      a4             mul ab
            0x00000c84      28             add a, r0
$ r2 -a 8051 -e scr.color=0 -q -c 's 0x0fcb; pd 8' /tmp/pd.bin
            0x00000fcb      e0             movx a, @dptr
            0x00000fcc      f8             mov r0, a
            0x00000fcd      a3             inc dptr
            0x00000fce      e0             movx a, @dptr
            0x00000fcf      f9             mov r1, a
            0x00000fd0      a3             inc dptr
            0x00000fd1      e0             movx a, @dptr
            0x00000fd2      fa             mov r2, a
```

Turning a callee's runtime address back into the file offset its bytes live at
is `trace_xdata_refs.offset_for_runtime()`, derived from the same `REGIONS`
table as the `runtime` column above so the two cannot drift apart:

```console
$ cd ec/tools && python3 -c "
from trace_xdata_refs import REGIONS, offset_for_runtime, runtime_addr
for name, lo, hi, base, _ in REGIONS:
    if base is None: continue
    for off in (lo, lo + 0x137, hi - 1):
        assert offset_for_runtime(runtime_addr(off, True), name) == off
print('round-trip ok for every mapped region')
print('bank1 calling 0x0500 ->', hex(offset_for_runtime(0x0500, 'bank1')), '(common area)')
print('common calling 0x8000 ->', offset_for_runtime(0x8000, 'common'), '(which bank is unknowable)')"
round-trip ok for every mapped region
bank1 calling 0x0500 -> 0x500 (common area)
common calling 0x8000 -> None (which bank is unknowable)
```

The banking assumption in those last two lines — a call below `0x8000` reaches
the common area, a call at or above it stays in the caller's own bank — is the
ordinary Keil convention, and a cross-bank call would be decoded against the
wrong bytes; a call the helper cannot place returns `None` and leaves the site
`handoff→unresolved`. [`bank-call-audit.md`](bank-call-audit.md) enumerates
every direct call in the main EC image against exactly that question — the
absolute `lcall`/`ljmp` forms in §1-§6, the paged `ajmp`/`acall` ones in §7,
which cannot leave the caller's own 2 KiB page and so never reach the
question at all. For the absolute forms: no
direct cross-bank call was found by that method, the linker's own cross-bank
path turns out to be an indirect trampoline block, and the assumption still
cannot be *verified* from the bytes because a same-bank and a cross-bank direct
call are byte-identical. None of that touches this file either way: the PD
image is flat, so all eleven sites and all eight callees here are one region
with one mapping. The one place it does bite is `0x04A6`'s EC-side handoff, and
there the result is the same `0x888C` store
[`pd-xdata-overlap.md`](pd-xdata-overlap.md) §2 reached by hand against a
`make_bank_image.py` bank-1 image — one agreement, on the one site, which
`bank-call-audit.md` §6 records as such rather than as a validation.

**The two unresolved ones, and why they stay unresolved.** `0xB1F2` and
`0x383A` each pass the DPTR they were given straight to a further routine —
`0x10C8` and `0x0FCB`, both of which read three bytes from it by the same
reading as the table above. That is a second level down, which the tool deliberately does not
follow and which this file does not claim as a result: a chain resolved by eye
is exactly the kind of one-linear-walk claim `../../docs/findings.md` §4
warns about, and neither site's remaining control flow (`ljmp 0x0C46`,
`ljmp 0x0F0E`) was traced. They are recorded as `handoff→unresolved`.

Neither of the eight is one of the `lcall 0x104D` inline-argument routines
that **#36** owns, so nothing here depends on that framing question. `0x1041`
sits immediately before `0x104D` in the image, but it is a separate routine:
it `ret`s at `0x104C` and takes no inline arguments.

**What this does and does not say.** These are instructions that store to or
load from the address the site handed over, in the PD image, found by a linear
decode of eight instructions from each entry point. A `write` here is not
evidence that anything acts on the value, and none of it is evidence about the
EC's own `0x07E2`-`0x07E5` — the headline at the top of this file is unchanged.
What it does add is that of the 38 sites, 20 now resolve to a read and 16 to a
write with 2 left unresolved, where before it was 17 / 10 with 11 unresolved:
the byte spans in §3.4 (`0x10E8` reaching `0x07E5` from a
`0x07E3` handoff, `0x1041` reaching `0x07E8` from `0x07E5`) are more of the
same multi-byte structure access §3.1 and §3.2 already described, not the
four separate control bytes `uniwill-laptop` expects.

## 4. Corroborating greps, and what they are worth

Both are absence-by-this-grep, on the pattern `docs/findings.md` §4c warns
about. Neither is proof of anything; they are recorded so the next person does
not redo them.

- **Vendor spec.** `windows/decompiled/v3.1.6.0/ECSpec.cs:327-333` defines
  `ADDR_LIGHTBAR_CONTROL_BYTE = 1864` (`0x0748`) / `REDBAR` `1865` / `GREENBAR`
  `1866` / `BLUEBAR` `1867` — the **AC-side** addresses, the ones
  `docs/findings.md` §3 found dead. No constant anywhere in
  `windows/decompiled/` has the value 2018-2021 (`0x07E2`-`0x07E5`). The
  Windows service does not appear to know these addresses as anything.
- **DSDT.** `evidence/acpi/dsdt.dsl:52193` declares `OperationRegion (ECMG,
  SystemMemory, 0xFE410000, 0x00010000)`; its field list runs `Offset (0x7D4)`
  → `CPUA/DBAP/DBSP/CGCT` (through `0x7D7`) and then jumps straight to
  `Offset (0xE0D)`. `0x07E2`-`0x07E5` is never named. Per §4c's re-grading of
  the same signal for `0x07B9`, read that as "ACPI can't reach it", not "the EC
  doesn't have it" — Windows talks to the EC through `ACPIDriver.sys`'s IOCTL,
  not through this region.

No anti-tamper-protected method bodies were involved; nothing here depended on
decompiling `GCUService.exe` (`windows/antitamper/README.md`).

## 5. The live probe this still needs — for a human, at the machine

Nothing in this file was run on hardware, and no write to `0x07E2`-`0x07E5`
has ever been attempted on this machine. The question "do these EC bytes drive
anything" is *still open*; the trace only removed the reason to think the EC
firmware handles them.

Procedure, in the order that keeps it attributable — one variable at a time,
same discipline as `docs/findings.md` §2:

1. Read `0x07E2`-`0x07E5` (and `0x07E6` as a control byte outside the claimed
   register set) via the driver's regmap debugfs, with AC **unplugged** — the
   `uniwill-laptop` name for these is the battery-mode set, so if a firmware
   path exists it is most likely gated on discharging. Record the values.
2. Write `0x07E3`/`0x07E4`/`0x07E5` = `0xC8`/`0x00`/`0x00` and re-read.
   - **Readback does not match** → something else owns the byte; stop, that is
     already the answer, and it makes `absent`/`unknown-not-absent` moot.
   - **Readback matches** → this proves the byte is writable RAM and *nothing
     more* (CLAUDE.md, and §4a/§4c for what happens when that gets over-read).
3. With the readback matching, toggle `0x07E2` bit 0 and watch, for at least
   one full animation period: the lightbar, and — because the containing image
   is a USB-PD stack — `/sys/class/power_supply/*/` current/voltage and any
   USB-C behaviour. A visible change in either is the discriminating result.
4. Repeat step 3 on AC. If nothing changes in either state, the honest outcome
   is `confirmed-inert` for the *write* path only, matching how
   `LIGHTBAR_AC_CTRL` was graded in `registers.yaml` — and it should be
   recorded with the same three-way corroboration that entry has, not from the
   null result alone.

Until step 3 or 4 produces an observation, `registers.yaml` keeps
`unknown-not-absent`.

## 6. Knock-on: `0x07D0`'s 254 references are in this image too

`registers.yaml`'s `BATTERY_CHARGE_LIMIT_DOWN` entry and `docs/findings.md`
§4d both cite `0x07D0`'s **254** direct references as the busiest address in
the `0x0780`-`0x07FF` range — and reason from "too busy to be a single-purpose
threshold byte". The count is correct; all 254 sites are in the PD image, and
the main EC image references `0x07D0` zero times by this method:

```console
$ python3 ec/tools/trace_xdata_refs.py ec/firmware/GMxMGxx_11.800 0x07D0 --counts-only
0x07D0: 254 direct MOV DPTR site(s)  pd-image=254
```

That does not change the `DO-NOT-WRITE-BLIND` status — if anything a byte with
no traceable EC-side handler is *less* understood, not more — but the "too
busy" argument no longer supports what it was doing, and mapping those 254
sites (the next step `docs/findings.md` §5 flags) is now a question about the
PD firmware, not the EC. That map has since been made —
[`ec-0x07d0-sites.md`](ec-0x07d0-sites.md) — and lands where this section
predicted: a PD-image index variable, nothing EC-side. Worth re-checking `0x07CC`
(`USB_C_POWER_PRIORITY`, 6 refs, all in the PD image) on the same basis before
anyone treats its reference count as EC-side evidence.
