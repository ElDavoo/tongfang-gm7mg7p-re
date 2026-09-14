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

15/9/4/10 is exactly what `scan_refs.py` reports and what
`annotations/registers.yaml` and the issue both cite — the two tools agree on
*where the bytes are*; they disagree only about what a file-wide total means.
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

| addr | file | runtime | what the site does |
|---|---|---|---|
| `0x07E2` | `0x204F9` | `0x04F9` | handoff → `lcall 0xB1F2` |
| `0x07E2` | `0x26E00` | `0x6E00` | write ×2, walks 2 bytes |
| `0x07E2` | `0x26E54` | `0x6E54` | write ×2, walks 2 bytes |
| `0x07E2` | `0x26E5C` | `0x6E5C` | read ×3, walks 3 bytes |
| `0x07E2` | `0x28EB3` | `0x8EB3` | write ×2, walks 3 bytes |
| `0x07E2` | `0x28F00` | `0x8F00` | read ×1 |
| `0x07E2` | `0x28F6F` | `0x8F6F` | read ×1 |
| `0x07E2` | `0x28F94` | `0x8F94` | handoff → `lcall 0x9CC2` |
| `0x07E2` | `0x28FCA` | `0x8FCA` | handoff → `lcall 0x9CA4` |
| `0x07E2` | `0x28FED` | `0x8FED` | read ×1 |
| `0x07E2` | `0x29007` | `0x9007` | read ×1 |
| `0x07E2` | `0x2B7A4` | `0xB7A4` | handoff → `lcall 0x10E8` |
| `0x07E2` | `0x2CEB4` | `0xCEB4` | write ×1 |
| `0x07E2` | `0x2CEE7` | `0xCEE7` | read ×1 |
| `0x07E2` | `0x2CF0B` | `0xCF0B` | read ×1 |
| `0x07E3` | `0x25F03` | `0x5F03` | handoff → `lcall 0x10E8` |
| `0x07E3` | `0x26482` | `0x6482` | handoff → `lcall 0x35DA` |
| `0x07E3` | `0x264AD` | `0x64AD` | handoff → `lcall 0x35DA` |
| `0x07E3` | `0x264BE` | `0x64BE` | write ×2, walks 2 bytes |
| `0x07E3` | `0x264DD` | `0x64DD` | read ×2, walks 2 bytes |
| `0x07E3` | `0x281A8` | `0x81A8` | handoff → `lcall 0x10E8` |
| `0x07E3` | `0x28F3E` | `0x8F3E` | read ×1 (bit-field pack, §3.3) |
| `0x07E3` | `0x2CEC7` | `0xCEC7` | write ×2, walks 2 bytes |
| `0x07E3` | `0x2D833` | `0xD833` | handoff → `lcall 0x10C8` |
| `0x07E4` | `0x26DD1` | `0x6DD1` | write ×2, walks 2 bytes |
| `0x07E4` | `0x26E2B` | `0x6E2B` | read ×1 (16-bit `subb`, §3.2) |
| `0x07E4` | `0x26E4C` | `0x6E4C` | read ×2, walks 2 bytes |
| `0x07E4` | `0x28F34` | `0x8F34` | read ×1 (bit-field pack, §3.3) |
| `0x07E5` | `0x254AC` | `0x54AC` | write ×3, walks 3 bytes |
| `0x07E5` | `0x26610` | `0x6610` | handoff → `lcall 0x1041` |
| `0x07E5` | `0x2662D` | `0x662D` | handoff → `lcall 0x383A` |
| `0x07E5` | `0x26C65` | `0x6C65` | write ×1 |
| `0x07E5` | `0x26E26` | `0x6E26` | read ×1 (16-bit `subb`, §3.2) |
| `0x07E5` | `0x28EF1` | `0x8EF1` | read ×1 |
| `0x07E5` | `0x28F4A` | `0x8F4A` | read ×2, walks 2 bytes |
| `0x07E5` | `0x28FB9` | `0x8FB9` | read ×1 |
| `0x07E5` | `0x28FE6` | `0x8FE6` | read ×1 |
| `0x07E5` | `0x2CEDE` | `0xCEDE` | write ×1 |

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
PD firmware, not the EC. Worth re-checking `0x07CC`
(`USB_C_POWER_PRIORITY`, 6 refs, all in the PD image) on the same basis before
anyone treats its reference count as EC-side evidence.
