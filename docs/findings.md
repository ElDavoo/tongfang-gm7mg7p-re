# Findings

Research log for reverse-engineering charging behaviour, RGB lighting, and
other `uniwill-laptop` driver features on the PCSpecialist/TongFang
`GM7MG7P` (Uniwill `GM5MG7Y`). See `hardware-identity.md` for the board
identity and `../ec/annotations/registers.yaml` for the full register
cross-reference. This document is the narrative; that file is the data.

**This document includes three retractions of earlier conclusions in this same
investigation** (§4l, §9, and the gate claim corrected in §14). They're kept
in, not edited out, because the *reason* each one was wrong is itself a finding
about the limits of the methods used.

## 1. Battery health, honestly

`charge_full` / `charge_full_design` = 2000/4100 mAh, 445 cycles. Genuinely
degraded — not a scaling artifact. This matters because the EC's own `_BIF`/
`_BST` ACPI methods (`evidence/acpi/dsdt.dsl`) deliberately mask early
capacity fade: below 50 cycles they report *design* capacity and rescale the
remaining-capacity reading to match; only at cycle ≥50 do they report the
true measured full-charge capacity. At 445 cycles, the numbers on this
machine are the honest ones.

*(**Qualification, 2026-09-19, §4l.** "Honest" needs one qualifier. The EC
charges this pack to 16.4 V (4.1 V/cell) while the pack requests 17.4 V
(4.35 V/cell), so the gauge learns full-charge capacity from charges that
stop 0.25 V/cell short. The 2000 mAh is the capacity to 4.1 V/cell. That is
still real fade: 4100 mAh is rated at 4.35 V/cell, and nothing here says
how much of the gap is fade and how much is the lower ceiling. That split
is unmeasured.)*

## 2. Feature-by-feature driver verification

Tested one feature at a time, live, with the user observing (not batch
tested — an EC is a single shared resource and batch writes make it
impossible to attribute cause). Full detail in
`../ec/annotations/registers.yaml`; summary:

| feature | verdict |
|---|---|
| `CPU_TEMP` / `GPU_TEMP` | confirmed (cross-checked vs. coretemp / nvidia-smi) |
| `PRIMARY_FAN` / `SECONDARY_FAN` | confirmed (RPM sysfs matches physical sound) |
| `FN_LOCK` | confirmed (physical F10 behaviour changes) |
| `SUPER_KEY` | confirmed (physical Super key goes dead) |
| `TOUCHPAD_TOGGLE` | fails — Fn+F5 emits no WMI event at all |
| `KEYBOARD_BACKLIGHT` (hotkey path) | confirmed (Fn+F6/F7, WMI codes 177/178) |
| `LIGHTBAR` (EC path) | **wrong mechanism, not a hardware fault** — see §3 |
| `BATTERY_CHARGE_MODES` | **writes accepted, does not cap charging** — see §4 |
| `BATTERY_CHARGE_LIMIT` | **status corrected from "absent" to "unknown"** — see §4 |
| `AC_AUTO_BOOT`, `USB_POWERSHARE` | EC bit flips on write; real-world effect untested |
| `USB_C_POWER_PRIORITY`, `NVIDIA_CTGP_CONTROL` | untested |

## 3. The lightbar: EC path is real, just not for this chassis

Live testing wrote every uniwill EC lightbar register (`0x0748`-`0x074B`:
colour, `WELCOME`/rainbow toggle, `S0_OFF`) with the animation running the
whole time. Every write landed (read back correctly) and changed nothing
visible — the lightbar kept its own rainbow pattern regardless.

That looked at first like "hardware doesn't support it here." It isn't.
Three independent facts, found after the user recalled Windows *could*
control it:

1. Static scan: `0x0748`-`0x074B` have **zero** direct references anywhere
   in the 256 KiB EC image.
2. The Windows service logs `LM_Manager|LB_Init for HidLightbar : ITE
   solution` — found via `strings -e l` on the raw `.exe`; the containing
   method (`LM_Manager.LB_Init`, in
   `windows/decompiled/v3.9.18.0/LightingModel/LM_Manager.cs`) is
   itself anti-tamper encrypted and did not decompile, so this came from
   the string table, not from reading the logic (see
   `windows/antitamper/README.md`).
3. Live hardware exposes **two** ITE 8291 HID devices, not one:
   `048D:CE00` (usage page `0xFF12`, matches `ITE_SPEC.USAGE_PAGE_4Zone`) and
   `048D:6005` (usage page `0xFF03`, matches `ITE_SPEC.USAGE_PAGE_Ligbar`).
   Only the first is claimed, by `hid-generic`. Nothing claims `6005`.

The lightbar on this chassis is a USB HID peripheral running its own
firmware default, not an EC-mapped device. `tuxedo-drivers`' `ite_8291_lb`
already implements this protocol for PIDs `7000`/`7001`/`6010`; `6005` would
be a new PID, likely a small addition rather than new driver work.

**2026-09-17 correction and live result (issue #5).** The old statement above
that nothing claims `6005` does not describe the current machine: the live
probe found it bound to `hid-generic`, accessible through hidraw. Also,
`new_id` or a one-line device-table change alone does **not** enable stock
`ite_8291_lb` control: its command functions switch on `hdev->product` and
return `-ENOSYS` for `6005`, even after binding. This was checked against
`tuxedo-drivers` commit `2c6bf54075fb38a7fdbefc560734281984bf65bc`; exact source
locations and request framing are in [the probe notes](../linux/lightbar/README.md).

Instead, `linux/lightbar/probe-6005.py` sent the **6010 static-colour sequence**
through hidraw to the physical `048d:6005` on GM7MG7P, Linux 7.2.6. Starting
from the user's reported default BIOS rainbow, the user observed **red, then
dark, with no keyboard change**. Four 8-byte feature requests returned 8;
those returns alone are not the behavioural proof — the separate human
observation is. Evidence: `evidence/hid/2026-09-17-6005-6010-static.jsonl` and
[the user's observation](../evidence/hid/2026-09-17-6005-observation.md).

This confirms static red/off control via USB HID on this machine, not full
6010 protocol compatibility. The requested 20/100 brightness was not measured;
green/blue, effects, persistence, driver initialization and suspend/resume
remain untested. No module was loaded, no driver rebound, and no EC register
was written by this HID probe. The lightbar was left dark, not restored to
rainbow. The next driver work is an explicit 6005 static-protocol path and
lifecycle testing, not an ID-only patch; #5 remains open for that work.

### 3a. The battery-side lightbar registers: the reference count was counting the wrong program

`0x07E2`-`0x07E5` (`LIGHTBAR_BAT_CTRL/RED/GREEN/BLUE` in `uniwill-laptop`'s
layout) were the one part of §3 that looked alive: 15/9/4/10 direct references,
against zero for the AC-side set. Tracing those sites
(`../ec/annotations/lightbar-bat-flow.md`) shows the counts are real and the
inference from them was not.

All 38 sites are in a **second 8051 program sharing the flash dump** — an
`ITE8850-PD` USB Power-Delivery image at file offset `0x20000`, with its own
reset and interrupt vectors, its own C startup stub, none of the EC's Keil
bank-switch stubs, and therefore its own XDATA allocation. Its `0x07E2` is not
the EC's `0x07E2`. In that image the four bytes are ordinary variables inside a
dense compiler-allocated block spanning `0x07CF`-`0x07E9` with no gaps: written
and read as 16-bit big-endian pairs, compared with a 16-bit `subb`, and packed
into bit-fields at `0x8F34`-`0x8F53`. The main EC image (`0x00000`-`0x17FFF`)
references all four addresses **zero** times.

The open question therefore narrows rather than closing: the reason to think
the EC firmware handles these bytes is gone, but "zero direct references" is
exactly the signal §4c retracted for `0x07B9`, and it carries the same
indirect-addressing blind spot. `registers.yaml` moves them from
`present-untested` to `unknown-not-absent`. **No write to `0x07E2`-`0x07E5`
has ever been attempted on this machine**; the discriminating experiment is
written up as a step-by-step probe in `../ec/annotations/lightbar-bat-flow.md`
§5, for a human at the hardware.

Two knock-on notes, since the same conflation reaches other entries:

- `0x07D0`'s 254 references (§4d, and the `BATTERY_CHARGE_LIMIT_DOWN` entry in
  `../ec/annotations/registers.yaml`) are **all** in the PD image; the EC image
  references it zero times. The count is right; the "too busy to be a
  single-purpose threshold byte" reading of it was a statement about the PD
  firmware's variables. `DO-NOT-WRITE-BLIND` is unchanged — a byte Windows
  demonstrably writes, with no traceable EC-side handler, is less understood
  than before, not more — but "map the 254 call sites" is now a PD-firmware
  task.
- `0x07CC` (`USB_C_POWER_PRIORITY`, 6 refs) is in the same position.
- `ec/tools/scan_refs.py` was correct for what it claimed to count but handed
  out a bare file-wide total, which is the number that caused this; it now
  prints the same `ec=`/`pd=` split `ec/tools/trace_xdata_refs.py` does.
  All 29 addresses in `../ec/annotations/registers.yaml` have since been
  audited per image — the table is `../ec/annotations/static-refs-audit.md`,
  and `ec/tools/check_register_counts.py` re-derives every number in it from
  the committed image. Measured result: each of the 10 live-working addresses
  the repo records an address for has references in the EC image, and the 4
  live-negative ones have none in either image, so the §4d validation set is
  not affected by this. `BAT_CYCLE_COUNT`'s `0x04A6` turns out to be split
  3 EC-side / 4 PD-side, which changes nothing about a register confirmed
  live. Those seven sites have since been decoded — the split is the one
  place the "separate XDATA maps" premise could be tested, and it held:
  `../ec/annotations/pd-xdata-overlap.md`. The caveat on that sentence is
  the audit's own: §4d's 20 registers
  include features (`PRIMARY_FAN`/`SECONDARY_FAN`, `TOUCHPAD_TOGGLE`,
  `USB_POWERSHARE`) whose EC addresses are nowhere in this repo, so they
  could not be checked either way.

The same "separate program, separate map" premise, approached from the other
end, is §3e: the ten `0xFF00`-`0xFFFF` addresses in the PD image's largest
XDATA cluster, and whether a decompiler's `DAT_EXTMEM_` spelling is an
address-space fact. It is not, and the encoding settles it.

### 3b. The 254 `0x07D0` sites, one by one

§3a left "map the 254 call sites" as a PD-firmware task. It is done:
`../ec/annotations/ec-0x07d0-sites.md`, with the site table beside it as
`ec-0x07d0-sites.csv`. Short version — the issue asked whether this is one
function called 254 times or 254 distinct sites, and it is the second: 254
distinct offsets spread over every populated 4 KiB page of the PD image, from
runtime `0x3478` to `0xE8F9`. 229 read the byte, 15 write it, 2 increment it
in place, 8 are unresolved by this method. Read sites feed it into address
arithmetic (`DPTR = base + value × stride`, strides `0x5E`/`0x60`/`0x77`),
which is the shape of an index or iteration state, not of a threshold. What
it indexes is not identified and was not guessed at.

**This changes nothing about the EC's `0x07D0`**, which is a different
program's address space and still has zero direct references in the EC image.
`registers.yaml` moves the entry from `present-untested` to
`unknown-not-absent` — "present" had rested on those 254 references — and
keeps `DO-NOT-WRITE-BLIND`. §4c's paired UP/DOWN write is still the
experiment that would settle it, and still a human step at the machine.

Two further boundaries on what a `MOV DPTR,#addr` count can mean, found while
doing this and distinct from the indirect-addressing blind spot in §4c and
the two-programs-in-one-dump problem in §3a:

- **`MOV DPTR,#imm16` also builds CODE pointers**, not only XDATA ones. In
  the PD image, CODE `0x07D0` sits inside the float-formatting string table
  (`"NaN"`/`"+INF"`/`"-INF"`). None of the 254 turned out to be that — every
  site whose direction resolves is a `movx` — but the byte pattern alone
  cannot tell the two apart.
- **Inline call arguments defeat linear framing.** 68 of the 254 sit directly
  after `lcall 0x104D`, a helper that pops its own return address and reads
  four argument bytes out of the code stream before resuming past them. A
  linear decoder walks into those bytes and comes out misaligned, which is
  why `disasm8051.py --converge` reports evidence about instruction framing
  rather than a verdict on it.

### 3c. The register corpus and the firmware's are nearly disjoint, and one reason for that was a grep (2026-09-23, issue #132)

Issue #132 counted the decompiled firmware's XDATA usage by grepping
`DAT_EXTMEM_` out of `ec/decompiled/*/*.c`: **1,134 distinct addresses in
14,399 references, six of them named**. The first number is right, the second
is an artefact, and the reading built on it — "99.5% of the registers the
firmware actually uses are `DAT_EXTMEM_0a56` and friends" — was not. It is
replaced here, and the replacement is smaller than it looks but not small.

`build_ec_decompile.py` applies `../ec/ghidra/xdata-symbols.csv` to the Ghidra
project *before* it exports the C. An address the symbol table can name is
therefore **not written as a `DAT_EXTMEM_` token anywhere in the export**:
`ec/decompiled/bank0/8749.c` line 97 reads
`if ((CPU_TEMP < 0x51) && (GPU_TEMP < 0x51))`, and there are 54 mentions of
`CPU_TEMP` across the EC programs and none of them under a `DAT_EXTMEM_043e`.
Reading both spellings — `../ec/tools/xdata_register_map.py` — gives

| | main EC | PD image | total |
|---|---:|---:|---:|
| distinct addresses | 1,063 | 157 | 1,172 |
| references | 13,937 | 864 | 14,801 |
| of which named from `registers.yaml` | 41 | 0 | 41 |

So the corrected claim is that **41 of the 1,063 XDATA addresses the main EC
touches carry a name, and 1,022 do not**. The blocking problem the issue
described is real and 96% of the register file is still `DAT_EXTMEM_xxxx`; what
was wrong was the size of the named minority, and with it any argument that the
firmware and `registers.yaml` are looking at the same bytes. They are nearly
disjoint corpora: 79 of `registers.yaml`'s 101 addresses appear in the
decompiled tree at all, 72 of them touched by the main EC and 7 only by the PD
image. (Corrected 2026-09-24, issue #181: this read "44 of `registers.yaml`'s
56 addresses", which was true when §3c was written and stopped being true when
`registers.yaml` grew to 101 entries without the census being regenerated. The
*other* number here — the 41 main-EC addresses the decompile spells by symbol —
is unchanged, and it is a different question: an address being in
`xdata-symbols.csv` and an address being *spelled* by that symbol in the
committed `.c` are two facts, and only the second one has moved.)

Two smaller corrections travel with it, both pinned by the tool's `--self-test`
so neither can drift unnoticed:

- **Nine of the issue's 14,399 references are this repository's own annotation
  text** quoting the decompile back at itself, in eight files —
  `ec/decompiled/bank0/B9DF.c` line 9 writes ``the decompiled C's
  `DAT_EXTMEM_0a56 = DAT_EXTMEM_1919` `` to make a point about that code. A
  comment is not the firmware touching an address, so the count is **14,390**.
- **`0x07D8`/`0x07D9`/`0x07DA` are not blind spots, and the grep was why they
  looked like them.** They are the worked example issue #132 proposed for this
  file, on the strength of `registers.yaml`'s `static_refs_main_ec: 1` against
  a `DAT_EXTMEM_`-only census showing none. Run both methods
  (`xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800`) and all
  three agree exactly: 1 main-EC site each, plus the PD-image sites §3a
  already accounted for. The reference is there, spelled
  `MODE_TCC_OFFSET_DEFAULTS_GAMING_0` and its two siblings, because that is
  what `registers.yaml` had already named the address. The same removes the
  apparent gap at `0x07A6` (7 byte sites, 15 C-level references, all under the
  symbol) and at `0x04A6` (3 and 3).

The census is still a lower bound, and the two addresses it genuinely misses
are worth naming because they fail differently, both inside
`bank0:0x94D0=copy_code_table_into_0730_07a7`. `0x0733`
(`MODE_PL_DEFAULTS_GAMING_DSTATE_3`) is spelled `&DAT_CODE_0733` — Ghidra
typed the value as a code pointer, and `xdata_register_map.py` deliberately
does not read `DAT_CODE_` tokens, because the same spelling covers common-area
*code* and importing it would claim an XDATA address on a token that says code.
`0x0735` (`MODE_PL_DEFAULTS_OFFICE_PL2_5`) is never spelled at all: it is
reached as `*(char *)(sVar5 + bVar2)` off a raw `sVar5 = 0x735` base with a
runtime index, which is the §4c indirect-addressing blind spot. Both are
"not found by this method" and neither is absent.

**What did not change:** no entry in `../ec/annotations/registers.yaml` moved
status, nothing was read on hardware, and no register is named or given a
purpose by any of this. A cluster in `../ec/annotations/xdata-clusters.csv` is
a co-occurrence in static code, not a meaning — that file's §6 is the
boundary, and reading a cluster is the follow-up issue's work.

### 3d. The 76 `0x07D1` sites, and what `DBD2` is next to `DBD1` (2026-09-24, issue #185)

§3b walked `0x07D0` and named the gap it left: `static-refs-audit.md` §6
closed by saying that `0x07D1`, the other half of the DSDT's `DBD1`/`DBD2`
pair, had never been walked site by site. That is done:
`../ec/annotations/ec-0x07d1-sites.md`, site table beside it as
`ec-0x07d1-sites.csv`. The gap sentence is retracted in place in that file,
§4a-4d style, and this is the finding the retraction is about.

The count reconciles the same way §3b's did — 76 rows, all `pd-image`, zero in
the EC firmware — and the two site sets turn out to be **completely
disjoint**, 0 shared file offsets of 76 and 254. That is a set question and
only a set operation answers it; no pair of counts could have.

The two bytes are the *same kind* of PD variable, and the evidence for that is
stronger than the issue expected. Both are read-mostly indices multiplied
against structure strides to address arrays. They share a stride (`0x5E`) and
an array base (`0x08FC`, indexed by `0x07D0` through its helper `0x34D9` and by
`0x07D1` at four of its own sites). And the walk turned up a shape that
bears on the pair directly: five of the 76 reach past their own byte through
`inc dptr`, four of them treating `0x07D1`+`0x07D2` as **one 16-bit
little-endian quantity** — `0xAD83` and `0xB38E` load the word into `R7`/`R5`,
and `0x3E91` stores the literal `0x9411`. The `0x07D0` half has the mirror
image of the same idiom at its own site `0xDACF`, which reads
`[0x07D0]`+`[0x07D1]` as a word — its CSV already scores it as a two-byte
walk, so nothing there needed correcting, only interpreting. So the PD
firmware holds the two bytes as adjacent halves of overlapping little-endian
windows.

**The divergence that is worth recording** is with the DSDT, not inside the
PD image. The field list declares `Offset (0x7D0), DBD1, 8, DBD2, 8, Offset
(0x7D3), , 4` (`dsdt.dsl:52248-52252`) — two independent 8-bit fields, with
`0x07D2` unnamed — while the PD firmware's 16-bit quantities straddle that
field boundary in both directions. **The DSDT's `DBD1`/`DBD2` pair is a pair
of the DSDT's own making, not a 16-bit quantity the PD firmware agrees with.**
Whether the two readings of the same physical bytes ever collide in practice
is not determined, and the answer is not reachable from a static walk.

**What did not change:** `0x07D1` keeps
`unknown-not-absent-DO-NOT-WRITE-BLIND`, and no `static_refs*` count moved — a
PD-image walk cannot move an EC-side grading, which is §3a's point restated.
Nothing was read on hardware, no register is named, and 76 is what
`trace_xdata_refs.py` found, which is a lower bound for §4c's reason: the
computed-`DPTR` blind spot means a byte reached through a register-held
address is not in that number, and would have read as "not found by this
method" rather than "absent" had there been none.

One correction travels with the regeneration above: the two census CSVs' `name`
column was stale, and §7 of
`../ec/annotations/xdata-register-map.md` now reconciles **101** addresses
instead of 56, with **12** main-EC gaps rather than 2. The ten new ones are all
inside `0x0400`-`0x0457` and all belong to the same `registers.yaml` growth;
**nothing here says why the census cannot see them**, and reconciling them is
its own issue.

### 3e. The ten `0xFFxx` addresses in `pd-001` are XDATA, and the encoding is what says so (2026-09-24, issue #181)

`pd-001` in `../ec/annotations/xdata-clusters.csv` is 34 addresses,
`0x00B6`-`0xFFE2`, the largest cluster in the `ITE8850-PD` program. Ten of the
34 sit in `0xFF80`, `0xFF84`, `0xFFC0`-`0xFFC2`, `0xFFD0`, `0xFFD1` and
`0xFFE0`-`0xFFE2` — inside the width of an SFR byte. The census counted them
because Ghidra wrote `DAT_EXTMEM_ff80` in `../ec/decompiled/pd/A8AE.c`, and
whether they are XDATA in the PD image's own space, a memory-mapped peripheral
window, or a decompiler typing a direct address as external memory decides
whether they belong in a register map at all. **They are XDATA.** The method
was the instruction encoding, over the committed image and the committed
`.asm`, and two arguments carry it.

**The structural one needs no decompile.** No 8051 direct-addressing opcode
takes a 16-bit operand. `MOV direct, ...` is `0x74`-`0x7F` / `0x84`-`0x87` /
`0xA5`-`0xA7` with an 8-bit `direct` byte, `MOV A,direct` is `0xE5`, `MOV
direct,A` is `0xF5`, and the bit forms are `0xC2`/`0xD2`/`0x20`/`0x22`/`0x40`/
`0x60`/`0xA0` with an 8-bit `bit` byte — all 2 or 3 bytes with the address in
one byte, in `../ec/tools/disasm8051.py`'s `OPCODE_LEN` table, which its own
`--self-test` pins. The only opcode whose operand is a full 16-bit immediate is
`0x90`, `MOV DPTR,#imm16`. So a `0xFFxx` value **cannot** be a direct address
whatever anything spelled it as, and the issue's premise — that `0xFF00`-`0xFFFF`
is "inside the 8051 direct-address/SFR range" — is loose in exactly the way that
made the question look open: the SFR range is 8 bits wide, `0x80`-`0xFF`, and
`0xFF80` is a 16-bit quantity that no direct-addressing mode can carry.

**The positive one is what the bytes do.** Each of the ten is loaded by
`mov DPTR,#imm16` and dereferenced by `movx` (`0xE0`/`0xF0`), and `movx` is the
instruction that names the external space:

```console
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xa8ae; pd 3' /tmp/pd.bin
            0x0000a8ae      c2af           clr ie.7
            0x0000a8b0      90ff80         mov dptr, #0xff80
            0x0000a8b3      e0             movx a, @dptr
$ r2 -a 8051 -e scr.color=0 -q -c 's 0xc6a9; pd 6' /tmp/pd.bin
            0x0000c6a9      90ffc0         mov dptr, #0xffc0
            0x0000c6ac      e0             movx a, @dptr
            0x0000c6ad      fe             mov r6, a
            0x0000c6ae      a3             inc dptr
            0x0000c6af      e0             movx a, @dptr
            0x0000c6b0      fd             mov r5, a
```

`disasm8051.py` over the same windows decodes them identically, and its
`--self-test` guards the tables against a change made while reading them.

**Three addresses are why the discrimination reads the `.asm` and not the
image.** `0xFFC1`, `0xFFD1` and `0xFFDB` are reached only by an `inc DPTR`
(`0xA3`) from the address below and are never a `MOV DPTR` operand, so a
`90 hi lo` byte scan finds their seeds and **cannot find them at all**. They are
three of the PD image's 23 census addresses at or above `0xF000` — 20 of which
a byte scan does find, and `0xFFDB` is not one of the issue's ten (it sits in
another cluster), so reading the issue's list alone would have made the count
twenty-one and the gap invisible. `xdata_register_map.py --self-test` now pins
all three by name and the 23 address for address, out of the committed
`../ec/decompiled/pd/*.asm`: no image, no Ghidra, no network.

**Two corrections ride along, because the issue quoted the annotation as its
premise and the premise was over-stated twice.** Both are settled by bytes
already committed, and both are corrected in place in
`../ec/annotations/ghidra-functions.csv` with the wrong wording left visible:

- **`0xAF` is a bit address, and the bit is `IE.7`.** `0xC2 AF` at `0xA8AE` is
  `CLR bit` and `0xD2 AF` at `0xA9BE` is `SETB bit` — not a direct address, as
  the `pd,0xA8AE` row said. A bit address `0xA8`+`n` is `IE.n`, so `0xAF` is
  `IE.7`, the global interrupt enable. It is **not** `PSW.EA`: `PSW` is SFR
  `0xD0`, and `EA` is not a `PSW` bit. `disasm8051.py` and `r2 -a 8051` both
  print `clr ie.7` and `setb ie.7`, and the repository's own `pd,0xEBBB` row
  already described `0xAF` that way — the `pd,0xA8AE` row was the outlier.
- **The routine ends `ret` (`0x22`), not `reti` (`0x32`).** So its
  clear-and-restore is the interrupt-masking idiom of a critical section, which
  a routine reached from an interrupt path also uses, and not evidence that
  `0xA8AE` is itself a vector. The row's "the pattern of an interrupt routine"
  is narrowed to what the two opcodes carry.

**What did not change, and what is still open.** `pd-001` keeps all 34
addresses and all 141 references: the two census CSVs' only content change is
the three `FUN_CODE_` functions now carrying hand names, and every address,
cluster, size, reference count, bucket count and function list is byte-identical.
**No `status:` in `../ec/annotations/registers.yaml` moved** — no static
disassembly can move one, and the file is not otherwise touched. Nothing was
read on hardware.

**The encoding settles the address space and stops there. `movx` does not
distinguish RAM from a memory-mapped peripheral window**, and no static method
here does. That question, and the live test that would settle it, are written
down in `../ec/annotations/pd-xdata-overlap.md` §5.3, §6 and §7 for a human
with the physical machine. **Nothing in this section states or implies that
test ran.** The two lower blocks in the same cluster, `0x00B6`-`0x00BE` and
`0x07C9`-`0x07CE`, were read against that file's §5 and §6 and found not to
bear on the boundary: the first is written by one PD routine and copied
out of `0xFFC0`-`0xFFC2`, the second is a `0x07CB` counter loop with a
`0x0945` gate, and neither is a base a pointer walk reaches `0x04A6` or
`0x07E2` from. `0x07CC`'s status vocabulary is #32's, the stride families
#75's, the `0x1253` pointer-add convention #69's, the unnamed DPTR-recipient
entries #67's, the `0x0832`/`0x083A` index writers #80's and the `0x07D8`
lightbar operand #45's; all are cited and stopped at, not reopened.

## 4. The charge limit: two retractions, in order

This is the part of the investigation that went wrong twice, in opposite
directions, before landing somewhere defensible. Both mistakes are kept
here verbatim-in-spirit because the *pattern* — trusting a single measurement
type as decisive — is the actual lesson.

### 4a. First claim: "the cap is proven, right now" — WRONG

Early in one session, `capacity` sysfs reported `100%`/`Full` while
`voltage_now` read 16.349 V on a 4S pack (4.087 V/cell). Reasoning at the
time: a genuinely full Li-ion cell rests at 4.15-4.20 V, so a lower resting
voltage while claiming "Full" was read as proof the Stationary/Trickle
profile was capping real charge below 100% and the gauge just hadn't caught
up.

**This was wrong, and the user caught it by pointing at an earlier session's
actual measurement.** A cell's voltage legitimately relaxes downward for a
while *after* charging stops normally, for any profile including 100%. A
below-4.20V resting voltage on AC proves nothing about a cap — it's
consistent with "charged to 100% a while ago and has since relaxed," which
is exactly what an uncapped charge looks like hours later. The right
instrument is `current_now` measured *while* `capacity` is climbing through
the claimed cap, not a resting voltage measured after the fact.

### 4b. The actual coulomb-counted evidence (from `evidence/battery-traces/`)

A prior session's 60-second-interval trace (`2026-09-09-profiles.csv`)
recorded full charge cycles under both `Trickle` and `Long_Life`. Current
draw at each capacity level:

| profile | 85% | 90% | 95% | 98% |
|---|---|---|---|---|
| Trickle | 1496 mA | 1326 mA | 1224 mA | 1020 mA |
| Long_Life | 1530 mA | 1292 mA | 1122 mA | 918 mA |

Over 1 A still flowing at 95% under both profiles, tapering smoothly to
100%. **No cap. No emulation either** (a genuinely emulated "fake" climb
would show current near zero while capacity still climbs — see the contrast
with real Windows behaviour in §4c). The three-profile mechanism, traced in
`ec/annotations/charge-profile-flow.md`, changes *how fast current tapers
near 100%* (a firmware constant used as a divisor/multiplier at EC
addresses `0xB2E2`/`0xB330`), not a hard stop.

### 4c. Second claim: "0x07B9 is definitively gone" — WRONG

A separate, earlier line of investigation concluded the numeric threshold
register `0x07B9` (`charge_control_end_threshold` in the driver) was
categorically unusable on this board, from four angles at once:

1. Zero direct references anywhere in the EC firmware image (static scan).
2. The DSDT's `ECMG` field list steps over exactly that byte
   (`evidence/acpi/dsdt.dsl`, `Offset(0x7B3)... Offset(0x7BA)` — 0x7B9 never
   named).
3. `uniwill-laptop`'s own `force=1` path explicitly masks
   `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` for un-validated boards.
4. Upstream `uniwill-laptop` issue #7: a TUXEDO engineer stated the charge
   *limit* feature (as opposed to charge *modes*) was, at the time,
   validated only on "Intel Project" Uniwill boards — this one is
   `PROJECT_ID_CML_GAMING`, not an Intel Project.

Separately, a live test (`force_charge_limit=1`, threshold written to 80,
confirmed readback `0x07B9 = 0x50`) **did not stop charging** — the trace in
`evidence/battery-traces/2026-09-09-threshold80.csv` shows charging past 93%
with the threshold nominally at 80.

Put together, this looked like a closed case: four static/structural
signals plus one live null-result, all pointing the same way.

**It wasn't closed.** The user's 2021 Windows screenshot
(`evidence/screenshots/2021-11-27-batteryinfoview-windows.png`) shows real
charging stopping at ~86%, followed by 2.5 minutes of the percentage
climbing to 100% at 0 mW with **falling** voltage — the actual signature of
gauge relaxation after a real stop, i.e. Windows genuinely caps charging on
this exact machine. And `windows/decompiled/v3.1.6.0/ECSpec.cs`
gives the reason all four static signals were misleading:

```csharp
public const ushort ADDR_BATTERY_CHARGE_LIMIT_UP   = 1977;  // 0x07B9
public const ushort ADDR_BATTERY_CHARGE_LIMIT_DOWN = 2000;  // 0x07D0
```

Windows writes **both** addresses as a pair (`Battery_Commands` enum:
`CHARGING_UP_LIMIT`, `CHARGING_DOWN_LIMIT`) every time it sets a limit. The
Linux-side live test only ever wrote the upper bound. Whatever the EC does
internally to enforce a cap, it may require both values, or the write
sequencing, or something else the pair-write triggers that a single write
doesn't. **This has not been tested and is the highest-value remaining
experiment** (see GitHub issues).

The four original signals are re-graded, not deleted, in
`ec/annotations/registers.yaml`:

- Static-scan zero-refs: downgraded from "proof of absence" to "not found by
  this method" — the scan only sees direct `MOV DPTR,#addr`; it cannot see
  pointer-based/indirect XDATA access, and `0x07B9` is a proven case of that
  blind spot (Windows demonstrably uses the address; the scan cannot find
  how).
- DSDT field-list gap: still true, but now understood as "ACPI can't reach
  it" rather than "the EC doesn't have it" — Windows doesn't go through
  ACPI for this at all, it talks to the EC via `ACPIDriver.sys`'s custom
  IOCTL (`windows/native/README.md`), a different path than the DSDT
  `OperationRegion`.
  *(**Correction, see §4e.** "Windows doesn't go through ACPI for this at
  all" is wrong: the custom IOCTL is `IOCTL_ACPI_EVAL_METHOD`, and the
  method it evaluates writes into the same `ECMG` region. "ACPI can't
  reach it" is also wrong — the byte is unnamed in the field list, not
  outside the window. The conclusion this bullet supports, that the gap
  is not evidence the EC lacks the register, survives both corrections.)*
- `force=1` masking: still literally true (the flag exists and masks the
  feature) but is a *driver policy choice*, not evidence about the
  hardware — the driver is being conservative, correctly, about a register
  nobody had validated yet.
- Upstream issue #7 "Intel Project only": now read as "nobody had tried the
  paired write on a non-Intel-Project board", not "the hardware can't do
  it."

### 4d. Static-scan validation (why the method is trusted at all, despite 4c)

Before the retraction in §4c, the same static-scan method was checked
against 20 registers with independently confirmed live behaviour — 15 known
to work, 5 known not to (from the manual per-feature testing in §2 plus the
lightbar-register nulls in §3). The scan predicted all 20 correctly.

That validation still stands; it just has a documented boundary now. The
method is reliable for direct-addressed 8051 code (the large majority of
what Keil C51 generates for simple register I/O) and blind to indirect
addressing. `0x07B9`/`0x07B0`-`0x07BE` is flagged in
`ec/annotations/registers.yaml` as a confirmed instance of the blind spot,
and `0x07D0` (254 references — the busiest address the scan found in the
whole `0x0780`-`0x07FF` range) is flagged **do-not-write-blind** until those
sites are actually disassembled, precisely because "used a lot" and "used
for a simple threshold byte" don't obviously fit together.

*(Those sites have since been disassembled — §3b. They are all in the PD
image, so the "used a lot" premise was never about this register; the
do-not-write-blind flag stays, for the reason in §3b rather than this one.)*

*(The per-image numbers behind this validation are tabulated in
`../ec/annotations/static-refs-audit.md` §3 — every address `registers.yaml`
holds whose status came from live observation, 14 of them. That set is not
provably the same 20: this validation was never enumerated register by
register here, and several §2 features (the fans, the touchpad toggle, USB
powershare) have no EC address anywhere in this repo, so they are named in the
audit as unresolvable rather than guessed at. "The scan predicted all 20
correctly" therefore still rests on the original testing notes; what is
re-derivable from committed files is the 14.)*

### 4e. The Windows write path, traced end to end

§4c says Windows "talks to the EC via `ACPIDriver.sys`'s custom IOCTL, a
different path than the DSDT `OperationRegion`." Both halves of that
sentence are now checked, and the second half needs correcting: it is a
different path than the DSDT's *named `ECMG` fields*, but it is still
ACPI, and it lands in the same region those fields describe.

`ACPIDriver.sys` and `ACPIDriverDll.dll` were statically disassembled
(`windows/native/ACPIDriver.sys.analysis.md`, and the `.dll` file beside
it; regenerate with `windows/tools/pe_triage.py` and
`windows/tools/disasm.sh`). The chain, each link decoded from a committed
file rather than inferred:

1. `ACPIDriverDll.dll!WriteEC(addr, val)` opens `\\.\ACPIDriver` and sends
   `DeviceIoControl` code `0x9C40A48C`, with `addr` as a 16-bit value at
   buffer offset 0 and `val` at offset 4.
2. `ACPIDriver.sys`'s handler for that code (`0x140002038`) packs those
   into an `ACPI_EVAL_INPUT_BUFFER_COMPLEX` naming method `ECRW` and
   forwards `IOCTL_ACPI_EVAL_METHOD` (`0x0032C004`) to `\Driver\ACPI`. The
   driver contains no port-I/O instruction and imports no port-I/O
   routine.
3. `evidence/acpi/dsdt.dsl:50504` implements `ECRW` as
   `MMRW(0xFE410000 + Arg0, One, Zero, Arg1)` — a byte write to physical
   memory. All 21 methods the driver can name exist as methods of
   `Device (INOU)`, `_HID "INOU0000"`.

So a Windows write to `0x07B9` is a byte written at physical
`0xFE4107B9`. That address is inside
`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`
(`dsdt.dsl:52193`) — the very field list §4c cites. Its offsets are EC
register addresses: `Offset(0x43E) CPTM` and `Offset(0x44F) VGAT` are the
`CPU_TEMP` and `GPU_TEMP` entries `registers.yaml` marks
`confirmed-working` against live hardware.

**What this re-grades.** §4c's second signal — "the DSDT's `ECMG` field
list steps over `0x7B9`" — was read as "ACPI can't reach it." It should
have been read as "the BIOS didn't give that byte a name." The window
covers it, and `ECRW` takes an arbitrary offset into the window, so ACPI
reaches it fine. This is the same shape of error as the other two in this
section: a gap in what one method can see, reported as a gap in the
hardware.

**What this does not change.** The failed live test still stands
unexplained by this. The Linux-side write went through `uniwill-laptop`
and read back correctly, so that path reaches the byte too; the paired
UP/DOWN write of §4c is still the untested variable, and nothing here
makes it more or less likely to work.

**What it opens.** `0xFE4107B9` and `0xFE4107D0` are plain physical
addresses in a region the BIOS already maps, so the paired write is
reachable on Linux without the vendor driver and without an ACPI method
call. Whether writing them that way behaves like the vendor path is a
live question on the physical machine — no such test has been run, and
none can be from here.

### 4f. The paired write, run live (2026-09-17) — does not stop charging either

The experiment §4c and §4e left open has now been run on the physical
machine, through the vendor's own path: byte writes at physical
`0xFE4107B9`/`0xFE4107D0` (`ec/tools/ecmem.py`, `/dev/mem` on the `ECMG`
window), read back both through the window and through the
`uniwill-laptop` regmap, and coulomb-counted with `current_now` every 10 s.
Log: `evidence/battery-traces/2026-09-17-limit-pair.csv` (script:
`linux/battery-trace/limit-pair-test`). AC plugged in throughout,
`0x07A6` = `0x20` (Trickle / Stationary profile active), kernel 7.2.6.

| phase | written | capacity | `current_now` | result |
|---|---|---|---|---|
| baseline | nothing | 79-80% | 1.94 A | charging |
| up60 | `0x07B9`=60 | 80-83% | 1.90 A | charging, 2 min |
| up60down55 | `0x07B9`=60, `0x07D0`=55 | 84-86% | 1.87 A | charging, 2 min |
| up60bit7down55 | `0x07B9`=0xBC (60 + bit 7), `0x07D0`=55 | 89-92% | 1.80 A | charging, 2 min |
| up95down90_below | `0x07B9`=95, `0x07D0`=90, set while at 93% | 93→98% | 1.77→1.67 A | charged straight through 95% |

Second session the same evening, after discharging to 56% so the cap
could be *armed from below* with margin, and to test two more hypotheses
(the profile in `0x07A6` gates the limit; the EC ignores the value and
stops at a fixed ~85% like the Windows screenshot):

| phase | written | `0x07A6` | capacity | `current_now` | result |
|---|---|---|---|---|---|
| armed56 Trickle | 60/55 | 0x20 | 57→62% | 2.01 A | through 60%, 3 min |
| armed56 Standard | 60/55 | 0x00 | 62→67% | 2.01 A | charging, 3 min |
| armed56 Long_Life | 60/55 | 0x10 | 67→72% | 2.01 A | charging, 3 min |
| armed72 hold | 60/55, untouched | 0x20 | 72→91% | 2.01→1.9 A | through 85%, no stop |

Every write read back correctly through both paths and stayed put (the EC
did not clear or rewrite either byte during any phase). Current never
stopped, never dropped below the normal taper, and `status` never left
`Charging`. The last phase tests the natural objection to the first four
(a cap set *below* the present level might not be expected to trigger a
stop, only to prevent one): armed from below, the pair was charged
through in five minutes at full taper current.

**What this establishes.** Writing the UP/DOWN pair as plain percentages,
with or without bit 7, from above or from below the cap, under all three
`0x07A6` profiles, held through 85%, at the physical address Windows'
`ECRW` lands on, does not by itself make this EC stop charging. That closes "the `uniwill-laptop` access path differs from the
vendor's" as an explanation for §4c: the window path behaves the same.

**What it does not establish.** It does not show the EC ignores the pair
in general. The values Windows actually writes are still unknown
(`BatteryProtection2`'s bodies are anti-tamper encrypted, issue #3), and
the write may be gated on something else the service also does: a
different `0x07A6` profile, a command/notify byte, or software-side
polling that never involved the EC enforcing anything. The Windows
screenshot in `evidence/screenshots/` remains the only evidence that a
cap exists on this machine at all.

**A second writer for `0x07D0`, found on the way.** The DSDT's `T1WR`
method (`evidence/acpi/dsdt.dsl:50676`, `Arg0 == 0x1173`) stores
`Arg1 * 8` into `DBD1` (`0x07D0`) and `Arg2 * 8` into `DBD2` (`0x07D1`),
and mirrors the same values into `\_SB.NPCF.AMAT` / `AMIT` before
`Notify (NPCF, 0xC0)`. `NPCF` is the NVIDIA platform-controller ACPI
device, and the neighbouring `0x1171` branch feeds `CTGP`/`UOCT`. So the
BIOS uses the `0x07D0`/`0x07D1` pair for a GPU power value in 1/8 W
units, not for a battery threshold. That is compatible with `ECSpec.cs`
naming `0x07D0` `BATTERY_CHARGE_LIMIT_DOWN` only if the EC image or the
service reuses the byte, or if the vendor constant is stale for this
board; which of those holds is not established. Either way, "resume
charging below X%" is now the *less* supported reading of the byte.

**Addendum 2026-09-23 (§4o, issue #131).** The question this paragraph
ends on — which of those holds — is now answered for the committed inputs,
and the three candidates come out differently. That the **EC image**
reuses the byte is *not* established either way: the census that §4o
describes covers Windows and ACPI, not the 8051 program, and that side is
#34 and #25. That the **service** reuses it is nearly answered: its one
committed writer, `BatteryProtection2.SetBatteryChargingLimit_Down`, is
`private` with no caller in the decrypted 3.1.39.0 tree, and no committed
Windows input calls `T1WR` at all — a search for a `T1WR 0x1173` caller
across the decompiled trees, every vendor binary's string table and the UWP
front end's PDB name table comes back empty, which is "not found by this
method", with the method, the search table and the list of inputs it could
not reach in **§4o**. That the **vendor constant is stale** is *not*
established by the same evidence: a constant whose only writer is never
called is not a name proved wrong, only one with nothing behind it here.
The reading of the byte is unchanged and now has the neighbouring branches
behind it. A line reference above is also off: the `Arg0 == 0x1173` branch
is `evidence/acpi/dsdt.dsl:50680-50691`, not `:50676` (`:50675` is the
`0x1172` branch).

### 4g. Watching the vendor stack instead of guessing at it (2026-09-18)

§4f ends by saying the values Windows actually writes are unknown, and §5
names "a Windows-side EC trace" as one of the two ways to find out. That
trace is now possible without installing anything. The vendor's driver is
already loaded on the machine (`UWACPIDriver.sys`, shipped with Control
Center Service 3.1.39.0) and `windows/native/` already decoded its
interface; `windows/tools/ecrw.py` is just that calling convention —
`\.\ACPIDriver`, IOCTL `0x9C40A488`/`0x9C40A48C` — and
`windows/tools/ec_watch.py` sweeps 2 KiB of EC space about 2.5 times a
second, fast enough to catch a settings write as it lands.

The driver present is not the build `windows/native/` analysed: that was
`ACPIDriver.sys` from the 3.1.6.0 era, this is a smaller `UWACPIDriver.sys`.
It creates the same `\DosDevices\ACPIDriver` symlink and carries all 21 of
the same IOCTL codes in its dispatch chain with `ECRR`/`ECRW` present as
method-name constants, which is why the documented convention still
applies — checked from the binary, not assumed.

**Why the reads are trusted.** `windows/tools/ec_validate.py` samples
battery terminal voltage from EC `0x0438/0x0439` and from the ACPI battery
driver (`root\wmi` `BatteryStatus`) at the same time. They never agree
instant-for-instant, because `BatteryStatus` serves a cached value — but
every WMI reading is an *exact copy* of one the EC held moments earlier.
Over a 10-sample run in which the EC figure took 7 distinct values between
13576 and 13849 mV, 10/10 WMI readings were exact copies of an EC value
already seen. Separately, while charging, EC `0x0434/0x0435` read 2040 mA
against `0x0438`'s 16021 mV — 32.68 W, against the ACPI driver's
independently reported 32.683 W. So `0x0434` is battery current in mA and
`0x0438` is terminal voltage in mV, and the coulomb-counting §4a requires
is available on Windows too.

**What the vendor's charge-limit UI actually writes: `0x07A6`, and
nothing else.** Control Center 3.1.39.0 offers three battery modes, named
in the UI "High capacity", "Balanced" and "Stationary" (internally
`HighCapacityMode`, `BalancedMode`, `HealthyMode`, driven over a loopback
MQTT topic `BatteryProtection/Control` — which is independent corroboration
for issue #4's premise). Cycling all three while watching `0x0700-0x07FF`
every 0.3 s for five minutes
(`evidence/ec-watch/2026-09-18-profile-switch-0700-07ff.csv`) produced
exactly three non-sensor changes, one per switch, all at the same address:

| UI mode | `0x07A6` | bits 4-5 |
|---|---|---|
| Stationary | `0x29` | `10` |
| High capacity | `0x09` | `00` |
| Balanced | `0x19` | `01` |

That is precisely the `bits: [4, 5]` encoding `registers.yaml` already
records for `OEM_4 (CHARGING_PROFILE_MASK)`, now confirmed from the vendor
side rather than from the driver's. The low nibble is a constant `0x09` on
this machine, which the Linux-side traces (that saw `0x00`/`0x10`/`0x20`)
did not carry; whether those bits mean anything is not established here.

**`0x07B9` and `0x07D0` were never written.** Over a separate sweep of the
whole `0x0000-0x07FF` space at 0.4 s intervals spanning the AC plug-in and
all three profile switches — 32499 recorded byte changes
(`evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`) — `0x07B9`,
`0x07D0` and `0x07D1` did not change once, and both read `0x00` throughout
while the vendor's own service was running with a battery mode active.

This is the observation §4f was missing, and it explains §4f's result
rather than deepening the mystery: writing the `ECSpec.cs` UP/DOWN pair did
nothing on Linux because *the vendor stack does not use that pair on this
machine either*. It expresses the whole battery-protection feature as one
profile byte and leaves the enforcement to the EC.

**Scope, carefully.** "Not written" here means not written during an AC
plug-in and three profile switches over about fifteen minutes. It is not
"never written": a threshold crossing, a service restart, a cold boot or a
Windows-side battery event could still touch them, and none of those was
in the window. `ECSpec.cs` naming the constants is still real. What has
been removed is the reading that the pair is the live mechanism the vendor
UI drives, which is what made issue #1 worth running.

**Repeated over a wider range, and one hypothesis killed.** The cycle was
run a second time while sweeping `0x0400-0x07FF`
(`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv`), for two
reasons. First, to check the first run had not simply been watching too
narrow a window: it had not — `0x07A6` is again the only settings-shaped
change, everything else that moved being slow sensor drift (voltage at
`0x0436`/`0x0438`, GPU temp at `0x044F`, the cycle counter at `0x04A6`
ticking 449 → 450 during the charge).

**CORRECTION to the `0x0436`/`0x0438` pairing in that sentence, added after
the page was swept (`ec/annotations/xdata-0400-045f.md` §8).** Calling
`0x0436` a voltage does not survive the capture it is citing.
`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` has `0x0436` moving
4 times — `0x70 → 0x84 → 0x98 → 0xAC → 0xC0`, exactly `+0x14` every ~35 s with
no scatter and `0x0437` never moving — and `0x0438` moving exactly **once**,
`0x97 → 0xAE` at 23:03:49. So the low byte stepping by a constant every 35
seconds is a periodic update, not a charge reading, and `0x0438` is the voltage
one, separately established three ways (§4g). `0x0436` is left unnamed pending
a live read beside WMI `RemainingCapacity`; `0x0438` is
`BAT_VOLTAGE_MV`.

*(**Addendum, 2026-09-23, issue #172.** The live read that correction is waiting
on is now instrumented, and still unrun. `windows/tools/ec_validate.py` carries
a `0x0436`/`0x0437` arm sampling the pair at 1 s beside the same WMI
`RemainingCapacity` the voltage arm already uses, under the same §4g rule and
the same one-directional guard; `linux/battery-trace/remain-capacity-probe` is
the read-only Linux equivalent, pairing the pair with `charge_now` and `capacity`
through the same `/dev/mem` window; and
`docs/hardware-tests/remain-capacity-0436.md` is the step-by-step, written for a
human at the machine. A run would produce three things: the exact-copy fraction,
whether the pair ever exceeded `0x0404`, and its scale against `0x0402`/`0x0403`.
Both probes check their address list against `0x0400-0x045F` in code rather than
in prose, so neither can reach the `0x0460-0x046F` fan-tach block (issue #94),
and both report without adjudicating — a counter fails the exact-copy test the
same way, and the comparison assumes both sides are mWh. **No run has happened,
so the question is exactly as open as it was: `0x0436`/`0x0437` is unnamed.)*

Second, to test a reading of `charge-profile-flow.md` §2 against the
running machine. That section traced the EC's profile handler statically:
`0xB2E2`/`0xB330` mask `0x07A6` bits 4-5, select 200 for Stationary or 100
for Balanced, multiply against `0x0A47`, and store to `0x0522`/`0x0523`.
Live, `0x0522`/`0x0523` reads `0x4010` = 16400 while the pack charges at
16255 mV, which invited a tidy story — 16.4 V on a 4-cell pack is
4.10 V/cell, the textbook longevity ceiling against 4.2 V/cell for a full
charge — and would have explained §4f in one stroke.

**It is wrong.** `0x0522`/`0x0523` did not change at all across all three
profile switches. Whatever selects that value, it is not re-derived from
`0x07A6` at the moment the profile changes, at least not at 43-46%
capacity mid-charge. The static trace is not contradicted — the handler
may only run near end-of-charge, or write the same value under these
conditions — but the appealing "the profile sets a charge-voltage ceiling"
reading has no support and is recorded here as refuted rather than
dropped, per §4a. `0x0A47` reads `0xFF`.

*(**Correction, 2026-09-19, §4l.** Half of this refutation was itself
wrong, in the §4c direction: a null result read as settling more than it
did. `0x0522/0x0523` **is** the charge-voltage target. The EC routine that
writes it (`ec/annotations/charge-target-derating.md`) subtracts a per-cell
derating from the pack's requested 17400 mV (`0x030E`), and 16.4 V is the
ceiling the pack actually plateaus at. What does not hold is "the profile
selects it". The profile only sets a *floor* on the derating (Stationary
≥200 mV/cell, Balanced ≥100), and on this pack an age tier of 250 mV/cell
already exceeds both. So `0x0522` not moving across profile switches was
exactly what the routine predicts, not evidence against it being a ceiling.
`0x0A47` reading `0xFF` is the host window not mapping that address (every
byte in `0x0A40-0x0A5F` reads `0xFF`), not the EC's value. In that routine
`0x0A47` is the cell count.)*

**Unexplained, and deliberately not interpreted.** At the instant AC was
connected, `0x0783` and `0x0784` both went `0x00` → `0x4B` (75) and
`0x0785` went `0x00` → `0xA5`. 75 is a suggestive number next to a
charge-threshold question and that is exactly the shape of the §4a
mistake, so it is recorded as an observation and nothing more; the three
bytes did not move when the profile changed, which is evidence against
their being the cap.

*(**Resolved, 2026-09-19.** They are CPU power limits, not battery values.
The DSDT names `0x0783`/`0x0784`/`0x0785` `APL1`/`APL2`/`APL4`
(`evidence/acpi/dsdt.dsl`, `ECMG` field list). `ECSpec.cs` names them
`ADDR_PL1/PL2/PL4_SETTING_VALUE` (1923-1925), and the decrypted service's
`SetPL1Value`/`SetPL2Value`/`SetPL4Value` write them
(`windows/decompiled/v3.1.39.0/ec-callsites.csv`). 75/75/165 W was the Turbo
power mode the machine was in that day. On 2026-09-19, in Gaming mode
after a BIOS reset, they read 60/60/165, matching
`ADDR_GAMING_PL1/PL2/PL4_DEFAULT_VALUE` at `0x0730-0x0732`.)*

### 4h. The UI→service command carries a mode name, not a threshold (2026-09-18, issue #4)

Issue #4 asked what `GamingCenter3_Cross` actually sends `GCUService` when
the user sets a charge limit, and whether it ever sends a numeric
"down"/resume value. Captured non-invasively from the loopback MQTT broker
(full protocol in `windows/mqtt-protocol.md`; evidence
`evidence/mqtt-capture/2026-09-18-profile-and-connect.{pcapng,jsonl}`), the
answer is that there is no numeric value on the wire at all. The entire
battery-protection command surface is one topic carrying one of three mode
names:

```
BatteryProtection/Control   {"Action":"PERFORMANCEDMODE"}   <- High capacity
BatteryProtection/Control   {"Action":"BALANCEDMODE"}       <- Balanced
BatteryProtection/Control   {"Action":"HEALTHYMODE"}        <- Stationary
BatteryProtection/Control   {"Report":"GET"}                <- query current
```

The three line up exactly with the `0x07A6` bit values §4g measured, which
ties the whole chain together end to end:

| UI label | MQTT `Action` | `0x07A6` bits 4-5 | telemetry `HealthProtectionStatus` |
|---|---|---|---|
| High capacity | `PERFORMANCEDMODE` | `00` (0x09) | — |
| Balanced | `BALANCEDMODE` | `01` (0x19) | — |
| Stationary | `HEALTHYMODE` | `10` (0x29) | `"2"` |

So: UI publishes `{"Action":"HEALTHYMODE"}` → `GCUService` sets `0x07A6`
bits 4-5 = `10` (the one EC byte §4g saw change) → the EC picks its taper at
`0xB2E2` (`charge-profile-flow.md`). `ECSpec.cs`'s
`Battery_Commands.CHARGING_UP_LIMIT`/`CHARGING_DOWN_LIMIT` and the
`0x07B9`/`0x07D0` numeric pair issue #1 is named after **appear nowhere in
this exchange**, which is independent confirmation, from a second
observation point, of §4g's finding that the vendor stack does not drive
that pair on this machine.

**On the polling question issue #4 raised.** `System/BatteryProtection` is
published periodically (the `Battry_LifePercentChange` tick), but it flows
*service → UI* and carries status, not a command:
`{"BatteryPowerStatus":1,"BatteryPercent":64,…,"HealthProtectionStatus":"2",
"TypeCAdaptorPrioritySwitch":"0","TypeCAdaptorPrioritySupport":false}`.
Nothing re-issues a charge command each tick over MQTT. That does not by
itself rule out `GCUService` poking the EC on its own timer without
publishing anything — but it removes the wire-level "software rewrites the
limit every tick" model as an explanation; the tick is telemetry.

**Scope.** This shows the UI→service protocol only. The mode→register
translation, and any numeric threshold `GCUService` may hold internally,
are inside `BatteryProtection2`, still anti-tamper encrypted (issue #3).
What #4 removes is the possibility that the number was passing over the
wire where a capture could see it: it is not. The auth triplet the broker
requires (`UWPClient_<N>` / `UWPClient_User_<N>` /
`UWPClient_Pwd888881772688_<N>`) is recorded in `windows/mqtt-protocol.md`
as protocol fact.

### 4i. The 2021 fake-charge, and three live attempts to reproduce it (2026-09-19)

`evidence/screenshots/2021-11-27-batteryinfoview-windows.png` is the only
evidence a charge cap ever existed on this machine, and read carefully it
shows something sharper than "a cap": a **fake charge**. Columns are time /
status / percent / capacity (Wh) / charge-rate (mW) / voltage (mV):

```
19:58:47  Charging  86.0%  44.445  4651  16.654   real charging, current flowing
19:58:47  Charging  88.0%  45.478     0  16.513   charge rate -> 0
19:59:47  Charging  92.0%  47.546     0  16.490   ...but percent keeps climbing
20:01:47  Charging 100.0%  51.680     0  16.490   "100%" reached at 0 mW
20:02:17  AC Power  100.0%  51.680     0  16.466   done
```

Charge rate is **0 mW from ~88% to 100%**, while the percentage climbs
88→100 in three minutes and the reported capacity rises 45.478→51.680 Wh
(exactly `percent × 51.68`). No real energy is entering the pack — the EC
holds true charge at ~86% and drives the gauge to 100%. That is why the
retraction in §4a matters in the vendor's own data: a percentage or a
resting voltage reads "100%, charged"; only the **rate/current** column
shows the charge actually stopped at 86%.

**This establishes the target signature precisely:** a working cap on this
machine looks like `current -> ~0 near 86% while capacity keeps climbing and
status stays Charging`. `battery_trace.py` logs exactly that pair
(`ec_current_ma` = EC 0x0434, and the ACPI `wmi_rate_mw`).

**It did not reproduce, in any of three live configurations today**
(`evidence/battery-traces/2026-09-18-windows-stationary.csv`, EC image
`GMxMGxx_11.800`, Control Center 3.1.39.0, Stationary/`HEALTHYMODE` = `0x07A6`
`0x29` throughout):

| configuration | what happened at ~86% |
|---|---|
| armed at initial plug-in (Stationary set, plugged at 28%, §4f-style) | charged through: 85% 952 mA → 91% 748 mA, smooth taper |
| after mid-charge profile cycling (§4g) | charged through, same taper |
| **clean unplug → discharge to 79% → replug, profile untouched** | charged through: 85% 1122 mA → 91% 816 mA, smooth taper |

The third row is the arm/replug test — the hypothesis that the EC only
latches the limit at charger-insertion, which would have explained why every
Linux write (all made while already plugged) failed. It is **refuted**: a
charger inserted with Stationary already armed and never touched afterward
still charges straight through 86% at full taper current. In every case
`ec_current_ma` and `wmi_rate_mw` decline together as a normal CC/CV taper —
never the flat-zero-with-rising-percent of 2021.

**What this establishes.** On this firmware + service combination the
vendor's own battery protection does not stop or fake charging at ~86% under
any profile or plug sequence tried. So "charge control doesn't work on
Linux" is not a Linux-driver gap: the mechanism that produced the 2021 cap
is not engaging under the current Windows stack either. The vendor UI's
entire battery-protection surface is the three profile modes (§4h, confirmed
over MQTT), and none of them caps here.

**What it does not establish, and the question it opens.** It does not show
the 2021 behaviour was imagined — the screenshot is real — only that the
present configuration does not produce it. The 2021 capture predates this
repo's committed inputs, and the difference is unidentified: a **different
Control Center version**, a **different EC image** (the live EC self-reports
`EcVersion = 1.18` in `HKLM\SOFTWARE\OEM\GamingCenter2\MyFanTable`, which is
not obviously the same provenance as the committed `GMxMGxx_11.800`), or a
BIOS setup difference are all candidates and none is ruled out. Identifying
which — ideally recovering the 2021-era EC/CC version that did cap — is the
next step for the charge-limit thread, and is a firmware-archaeology
question, not a driver one.

*(**Reframed, 2026-09-19, §4l.** "Does not stop or fake charging at ~86%" is
still what was measured. But "the vendor's own battery protection does not
cap" is too strong: the EC does cap, by charge voltage (16.4 V against the
pack's 17.4 V), and the 2021/2026 difference has an explanation in the
current firmware. No different EC image or CC version is needed to account
for it. The archaeology in #83 is no longer the only path.)*

### 4j. BIOS defaults, HDMI unplugged, Gaming mode (2026-09-19) — charges through, same as before

Two hypotheses for why the 2021 cap no longer engages were testable without
new firmware: a BIOS setting (#86), and something about the external
display. The owner loaded BIOS setup defaults and unplugged the HDMI monitor
before this session. The power mode was also different from §4i: Gaming,
the BIOS default, where §4i had run in Turbo (PL1/PL2 60/60 W vs 75/75 W,
`0x0783/0x0784`). So three things changed at once; that is acceptable only
because the result is a null.

Coulomb-counted from 63% with Stationary armed
(`evidence/battery-traces/2026-09-19-windows-bios-defaults.csv`, phase
`biosdefaults_nohdmi_stationary`, EC sampled every 10 s):

| capacity | 2026-09-18 (§4i) | 2026-09-19 (this run) |
|---|---|---|
| 65% | 1700 mA, 16466 mV | 1666 mA, 16466 mV |
| 75% | 1326 mA | 1326 mA |
| 86% | 918 mA | 952 mA |
| 88% | 850 mA | 884 mA |

The two runs match within one EC current step (34 mA) at every point.
There was no stop, no rate-to-zero, and no gauge jump. With BIOS setup at
defaults, no external display and the Gaming power mode, this machine
charges through ~86% exactly as it did under §4i's conditions. That rules
out "a non-default BIOS setting disabled the cap" and "the HDMI display
changes charging" for this configuration. It does not rule out a
*non-default* BIOS setting that would *enable* something; see §4l for why
that's no longer the leading question.

Also changed by the BIOS reset: `0x07A6` read `0x28` where §4g always saw
`0x29`, i.e. bit 0 cleared. Bits 4-5 (Stationary) were untouched. Several
vendor methods read-modify-write other bits of `0x07A6`
(`windows/decompiled/v3.1.39.0/ec-callsites.csv`: touchpad toggle, mic-mute
LED, `SetApExist`, `SetOverBoostByDynamicTemp`). Which one owns bit 0 was
not established.

The EC watch run during this charge was stopped at 86%, part-way through
(see `docs/related-projects.md`: on a sibling Uniwill board, reading the
fan-tachometer registers through `ECRR` stalled the fans).

### 4k. `BatteryProtection2` decrypted: what the vendor service actually does (issue #3)

The installed service (Control Center Service 3.1.39.0) was dumped from
memory after its anti-tamper had decrypted it (`windows/tools/dotnet_dump.py`,
`windows/decompiled/v3.1.39.0/README.md`). All 4951 method bodies parse
(3759 were ciphertext on disk), and the whole service now decompiles:
`windows/decompiled/v3.1.39.0/GCUService/`.
`GCUService.MySystem/BatteryProtection2.cs` settles what issue #3 asked:

- **The three modes are one read-modify-write of `0x07A6` bits 4-5 and
  nothing else.** `SetHealthProtectionHigh/Middle/Low()` write `00`/`01`/`10`
  and are the only EC writes on the mode path. This is §4g's observation,
  now from the source.
- **`SetBatteryChargingLimit_Up/Down` exist and are never called.** They are
  private, and no method of the class calls them. `Receive()` has no branch
  for `CHARGING_UP_LIMIT`/`CHARGING_DOWN_LIMIT`, even though the enum names
  them. The bodies are simple: `0x07B9 = (old & 0x80) | limit` (100 means
  "write 0"), and `0x07D0 = (old & 0x80) + limit` for 1-95. On this service
  version the numeric pair is dead code, which is why §4g never saw it
  written.
- **A second, firmware-side path exists but is also dead.** The
  `m_BatteryChargingLimit_Up/Down` and `m_BatteryLimitationMode` property
  setters call `NvramVariable.SetFwVars("ChargeMaximumLimit" /
  "ChargeMinimumLimit" / "BatteryLimitation", ...)`. Those are fields of
  `NVRAM_STRUCT`, which `UEFI_Firmware.dll` reads and writes as UEFI variable
  `UniWillVariable` `{9f33f85c-13ca-4fd1-9c4a-96217722c593}`. But
  `SetFwVars(string, byte)`'s `switch` has no case for those three names,
  so the write would leave the struct unchanged; and nothing calls the
  setters anyway (`LoadBatteryLimitationDefault()` is itself uncalled).
  Read live (`windows/tools/uefi_var.py`,
  `evidence/uefi/2026-09-19-UniWillVariable.{bin,txt}`, after the BIOS
  reset): all three bytes are 0. The variable is 180 bytes, exactly
  `NVRAM_STRUCT`'s size with C# default alignment, so the decode is
  unambiguous. Whether the BIOS *reads* those fields is a #86 question.
- **The service sets High capacity whenever it stops.** `Application_Exit` →
  `Disable()` and `Uninstall()` both call `SetHealthProtectionHigh()`.
  `Init()` re-applies the saved mode from the registry on start and on
  resume.
- `SetTypeCAdaptorSwitch` drives `0x07CC` bit 7 (`ADDR_COMPLEX_POWER_STATUS`),
  gated on `0x0742` bit 5 (`GetTypeCAdaptorPrioritySupport`). That is issue
  #8's `USB_C_POWER_PRIORITY`.

So the question §5 used to leave open, whether the cap is enforced by the
EC or by Windows software polling, has its answer for this version. The
service does not enforce anything. It sets a two-bit mode and leaves the
rest to the EC.

### 4l. The cap that is there: a charge-voltage target, derated by age (2026-09-19)

Every Windows and Linux trace in this repository plateaus at the same pack
voltage, **16466 mV**, while current tapers. That's constant-voltage
charging at about 4.12 V/cell (`2026-09-09-profiles.csv` under Trickle,
Long_Life and Standard; `2026-09-18-windows-stationary.csv`; this run). The
pack is a 4S high-voltage Li-ion pack: its smart-battery block at EC `0x0300`
reads manufacturer `BMS-GF`, design voltage 15200 mV (4 × 3.8 V), and
**requested ChargingVoltage 17400 mV** at `0x030E` (4 × 4.35 V). The EC's
charge target at `0x0522` is **16400 mV**, exactly 1000 mV less. So a cap
*is* in force, in volts rather than percent: the pack is charged to about
4.1 of its rated 4.35 V/cell.

`ec/annotations/charge-target-derating.md` decodes the routine that sets it
(bank 0 `0xB158`-`0xB38D`, the same function whose profile branches
`charge-profile-flow.md` §2 found):

```
target = requested_voltage - tier * cells
tier (mV/cell) = max( age tier from cycle count (150/250/350/450/550 -> 50..250),
                      age tier from a temperature-weighted "hours above 4.1 V/cell" counter,
                      200 if Stationary, 100 if Balanced, 0 if High capacity )
```

The live numbers pin it: 1000 mV over 4 cells is the **top tier, 250
mV/cell**. That is above both profile floors, which is why no profile
changes anything on this pack. That was also tested directly: switching to
High capacity in the CV phase at 88% (trace phase `cv88_switch_to_highcap`,
`0x07A6` = `0x08` for 5 minutes, then restored to `0x28`) left `0x0522` at
16400 and the taper unchanged.

This reconciles §4i with the 2021 screenshot without needing a different
firmware:

- In 2021 the pack was young, below every age tier, so Stationary's floor
  (200 mV/cell) set the target: 17400 − 800 = **16600 mV**. With today's
  +66 mV offset between the EC's reading and its target, that predicts about
  16.65 V at the plateau. The screenshot shows **16.654 V** while charging at
  86%.
- The gauge had learned "full" at a higher voltage. When the charge
  terminated at the lower ceiling, it smoothed RSOC up to 100% at zero
  current: the "fake charge". mech-forza-control documents the same
  gauge-learns-the-cap behaviour on another Uniwill board
  (`docs/related-projects.md`).
- By 2026 the age tier had passed the profile floor, the ceiling fell to
  16.4 V, and the gauge relearned "full" there. A capped charge now looks
  like an ordinary 0-100% charge, so there's no fake-charge signature left
  to see.

**Calibration.** The routine is a hand decode with a linear decoder, and its
entry point has no direct caller in the image (it's reached indirectly), so
when it runs is unresolved. `cells = 4` and `tier = 250` are inferred from
the decode plus the live target; the counter (`0x09C9`) and the cell count
(`0x0A47`) sit in EC RAM the host window doesn't map, so they can't be read
back. The 2021 reading rests on one screenshot. What *is* measured: 17400
requested, 16400 targeted, a 16466 mV plateau under every profile, and a
profile switch that moves nothing.

**What it means for the driver.** On this board, `charge_types`
(`0x07A6` bits 4-5) is a real control with an EC effect, but only as a
floor that age can overtake: Stationary means "at most 4.15 V/cell", not
"80%". `charge_control_end_threshold` (`0x07B9`) has no EC consumer found
by any method. The Mechrevo fix that makes `0x07B9` work on newer Uniwill
ECs relies on logic this image doesn't appear to contain
(`docs/related-projects.md`). Whether the host can override the target (a
write to `0x0522`, which the routine rewrites) was untested when this was
written; §4m now runs it, and the answer is no.

### 4m. The host cannot set the charge-voltage target: the EC owns 0x0522 (2026-09-21, issue #91)

§4l left one experiment for the hardware: does a host write to the
charge-voltage target `0x0522` stick, and does the charger follow it? Both
are now tested live on the physical machine (`windows/tools/charge_target_test.py`,
run elevated through the vendor driver, owner present). The tool only ever
*lowers* the target — a CV ceiling below the pack voltage can reduce charging
but never overcharge — and restores the original on exit.

**Which of the tool's branches are covered offline.** The three refusals, and
the restore in its `finally` that runs on a clean exit, on a read error and on
Ctrl-C, are pinned by `windows/tools/test_charge_target_test.py` against a fake
`ecrw` and a fake WMI line: no EC is opened, no register is read back, and no
`powershell` is spawned. Those are the branches no committed artifact
exercises, because all three live runs below took the write path. The suite is
coverage of the tool's control flow, and adds nothing to what this section
measured on the machine.

**A host write to `0x0522` does not persist, in any state tested.**

| run | state | writes that held |
|---|---|---|
| `stick_100pct` | AC, 91-93%, not charging (`0x0490`=0x0E) | 0 / 11 |
| `holdcheck_battery` | battery, 88%, re-asserted every 20 ms (`0x0490`=0x0E) | 0 / 3 |
| `follow_cv_highcap` | AC, charging in CV at 82-83%, High capacity, re-asserted every 20 ms (`0x0490`=0x0F) | 0 / 8 |

Every readback returned the EC's computed value (16400 mV), including the
readback taken microseconds after the write. A tighter diagnostic settles that
this is the EC reclaiming the byte, not a dead write path: writing `0x0522` =
16300 and then hammering **2000 back-to-back reads** (~101 µs each, ~200 ms
total) caught the written value **0 times**, while in the same run a control
write to the known-writable dead byte `0x07B9` = 0x5A read back correctly
(`held`). So the write path works this instant; `0x0522` specifically is
reclaimed faster than a single ~100 µs host round-trip. Whether the host write
lands-then-reverts or is dropped outright is not distinguished, but the
driver-relevant conclusion holds either way: **the host cannot hold `0x0522`
at a chosen value.**

Because the target can't be held, question 2 — does the charger follow
`0x0522`? — cannot be tested by override on this firmware. In the CV run the
charge current tapered on its ordinary SoC schedule (1360 → 1258 mA as
capacity rose 82 → 83%) with the pack pinned at 16466 mV throughout; it showed
no response to the reverted writes, as expected when the byte never actually
changed. The `0x0522`=16400 ↔ 16466 mV plateau relationship remains a
correlation (plus the decode in `charge-target-derating.md`), not a
host-demonstrated causation.

**Live confirmation of profile-independence, as a bonus.** The CV run was done
in **High capacity** mode (`0x07A6`=0x08, floor 0 mV/cell). The target read
16400 mV throughout — the same value seen under Stationary and Balanced —
which is the direct live confirmation of §4l's claim that on this aged pack
(age tier 250 mV/cell) no profile can lower the target.

**Who rewrites it (answers part of #89).** The derating routine at bank0
`0xB158` has no direct caller, but it is reached: the task-dispatch slot at
`0x8539` does `lcall 0xB12C`, which falls through `0xB141` (`jb acc.1,0xB158`
on `0x0490` bit 1) into `0xB158`. The *same* slot also `lcall`s `0xE010`,
a second `0x0522` writer that copies the pack's requested voltage (`0x030E`)
in before the derating overwrites it. So `0x0522` is (re)computed inside the
periodic task loop. The exact tick rate isn't measured from the image, but the
live <101 µs reclaim shows it is effectively continuous from the host's point
of view. (`0xB141`'s other branch, taken when `0x0490` bit 1 is clear, zeroes
the stress counter `0x09C9/0x09CA` — a partial data point for #90: the counter
is plain XDATA that the EC clears under that condition; whether it is persisted
to e-flash or the pack elsewhere was not determined here.)

**What this means for the driver.** There is no host-writable charge-limit
control on this EC image. `0x07B9`/`0x07D0` have no EC consumer (§4f, §4k) and
`0x0522` is EC-owned and un-writable from the host (this section). Capping
charge voltage on Linux by poking a register is not available on this
firmware; the cap is entirely internal to the EC. Evidence:
`evidence/battery-traces/2026-09-21-0522-{stick,holdcheck,follow}.csv`.

**Not closed by this.** Whether the charger *physically* tracks `0x0522`
(rather than, say, `0x030E`) is the remaining causation question. It can't be
reached by overriding the EC; the way to settle it is to read the charger IC's
programmed ChargingVoltage over SMBus directly (a follow-up, needing the
charger's SMBus map). See §4n.

### 4n. The charger is on the EC's private SMBus — the host can't read it (2026-09-23, issue #98)

#98 asked whether the charger IC's programmed ChargingVoltage can be read
directly over SMBus, to settle the §4m causation question by a read instead
of an override. The answer, from the ACPI topology plus a live anchor, is
that the charger is **not reachable from the host**, so this route is a dead
end — the outcome the issue told us to record if so.

**The pack and its charger are behind the EC.** The DSDT has a host SMBus
controller, `Device (SBUS)` at `_ADR 0x001F0004` (PCI `00:1f.4`), but its
body is only a `_DSM` for PCI config — **no battery or charger child
devices** (`evidence/acpi/dsdt.dsl:7809`). And `BAT0._BST` builds its status
buffer entirely from EC fields — `^^PCI0.LPCB.EC0.XST0..XST3`, `CYCN`, `XIF1`,
`XIF2` (`:53091`) — never from a host SMBus transaction. So the EC talks to
the smart battery/charger over its own private SMBus and mirrors the data
into EC RAM; the host reads that mirror, not the bus. The SBS block is live
at EC `0x0300`: `42 4D 53 2D 47 46` = "BMS-GF", the pack manufacturer.

**A host SMBus scan was not run.** RWEverything (`RwDrv.sys`) is installed and
its driver opens, so a scan is *possible*, but (a) ACPI shows the pack is
bridged, not on the host bus, and (b) a blind read sweep of the host SMBus
risks disturbing whatever *is* on it (SPD EEPROMs and the like) for no gain
given the topology. The one residual it could resolve — whether the pack also
sits on the host bus at the SBS address `0x0B` in addition to being
EC-bridged — is left for a deliberate, single-address read via RWEverything's
SMBus GUI, noted here rather than done blind. (Standalone `Rw.exe /Command`
runs produced no output in this session; its SMBus path is GUI-driven.)

**The correlation, re-anchored live (2026-09-23).** With the charger
unreadable, the §4m evidence stays correlational, and it still points one
way. Read together this session, on AC: the pack's requested ChargingVoltage
`0x030E` = `0x43F8` = **17400 mV**, the EC's CV target `0x0522` = `0x4010` =
**16400 mV**, and the live battery voltage `0x0438` = `0x4052` = **16466 mV**
— sitting at the EC's 16400 target (4.11 V/cell), a full 934 mV under the
pack's own 17400 request. The charger is holding to `0x0522`, not to `0x030E`.
That is consistent with the charger following the EC's target, but it remains
inference: the charger's own register was not read, and #91 already showed
the tie can't be broken by overriding `0x0522` from the host. So #98 closes
as *unreachable*; the causation question is answered only as far as the
matching plateau allows.

### 4o. Who calls `T1WR 0x1173` — not found by this method — and what `0x07D0` is on GM7MG7P (2026-09-23, issue #131)

§4f found a second writer for `0x07D0` and stopped one short of an answer:
"whether the EC image or the service reuses the byte, or if the vendor
constant is stale for this board … which of those holds is not
established." This takes both halves from committed inputs. The headline
is a negative, so it is written in the form the calibration rule
requires: **no caller of `T1WR` with `Arg0 = 0x1173` was found by this
method**, and the section says what the method was and what it could not
reach.

**The method.** `windows/tools/t1wr_callers.py`, in the spirit of
`windows/tools/ec_callsites.py`: it walks a fixed term list — `TempWrite*`,
`T1WR`/`T2WR`/`T3WR`, the six TMPREAD/TMPWRITE IOCTL codes `0x9C40A4D0` to
`0x9C40A4E4` in hex *and* in the decimal a C# `const uint` carries, the
`Arg0` values `0x1171`/`0x1172`/`0x1173`/`0x2273` in hex and decimal, the
`NPCF` objects `AMAT`/`AMIT`/`ATPP`/`CTGP`/`UOCT`/`DBAC`, and the field
names `DBD1`/`DBD2` — across every committed Windows input: the decompiled
trees as text, the vendor binaries by string table in ASCII **and**
UTF-16LE, and the `.appxsym` PDB's name table. A binary hit is counted only
inside a run of printable characters, so a hit means the name is spelled in
that file rather than that four bytes turned up somewhere. `--self-check`
asserts the table against the committed tree and exits non-zero on drift,
so the counts below are regenerable rather than remembered, and the
archives are expanded in memory — `vendor/` is committed input and nothing
is ever written under it. Note what the term list is *not* run against:
this repository's own prose. A hand `grep -rn 'TempWrite1\|0x1173\|AMAT'
windows/` hits the export table in `native/ACPIDriverDll.dll.analysis.md`
and, since this section, the files that describe this search — which is
why the census is scoped to inputs and why a raw grep is not the
instrument.

```console
$ python3 windows/tools/t1wr_callers.py --self-check
t1wr_callers: census matches the committed tree -- 7 text inputs, 8 binary inputs, 2 body censuses, and the service's only ACPIDriverDll P/Invoke is SMAPCTable
```

The same run, in full:

```console
T1WR(Arg0=0x1173) caller census. Every number is a hit count, not
an estimate. A zero means 'not found by this method'.

== text inputs: input | term | hits ==
decompiled/v3.1.39.0 (whole service, decrypted)                            2621482192   1
decompiled/v3.1.39.0 (whole service, decrypted)                            2621482196   1
decompiled/v3.1.39.0 (whole service, decrypted)                            2621482200   1
decompiled/v3.1.39.0 (whole service, decrypted)                            2621482204   1
decompiled/v3.1.39.0 (whole service, decrypted)                            2621482208   1
decompiled/v3.1.39.0 (whole service, decrypted)                            2621482212   1
decompiled/v3.1.6.0 (partial, anti-tamper)                                 (no term hit anywhere in this input)
decompiled/v3.9.18.0 (partial, anti-tamper)                                (no term hit anywhere in this input)
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  0x9C40A4D0   4
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  0x9C40A4D4   4
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  0x9C40A4D8   4
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  0x9C40A4DC   4
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  0x9C40A4E0   4
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  0x9C40A4E4   4
decompiled/native ACPIDriver.sys + ACPIDriverDll.dll (exports TempWrite1)  TempWrite*   12
decompiled/native GamingCenter3_Cross + GC3_launcher (the UWP component)   (no term hit anywhere in this input)
decompiled/native UEFI_Firmware + clrcompression                           (no term hit anywhere in this input)
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      0x1171       1
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      0x1172       1
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      0x1173       1
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      0x2273       1
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      AMAT         5
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      AMIT         2
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      ATPP         4
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      CTGP         2
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      DBAC         7
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      DBD1         2
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      DBD2         2
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      NPCF         54
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      T[123]WR     3
CONTROL evidence/acpi/dsdt.dsl (T1WR is defined here)                      UOCT         4

== binary inputs: string table, ASCII and UTF-16LE ==
vendor 3.1.39.0 GCUService.exe (shipped, bodies encrypted)  (no term hit in any string)
decompiled GCUService.dumped.exe (bodies decrypted)   (no term hit in any string)
vendor 3.1.6.0 UniwillService_3.1.6.0_STD.exe (installer)  (no term hit in any string)
vendor 3.9.18.0 setup.exe (installer)                 (no term hit in any string)
vendor 3.9.18.0 ACPIDriver.sys                        (no term hit in any string)
vendor 3.9.18.0 ACPIDriverDll.dll                     TempWrite*   3
vendor 3.9.18.0 GamingCenter3_Cross .msixbundle (UWP front end)  (no term hit in any string)
vendor 3.9.18.0 GamingCenter3_Cross .appxsym (PDB name table)  (no term hit in any string)

== readability probes on the binary inputs (not caller terms) ==
A name these inputs are known to carry -- a .NET method name from the
GPU feature area, or the driver device name for the native PEs. They
are counted so that a zero in the caller table above reads as 'the
name is not in there' rather than 'the scan did not reach the source'.
The text inputs need no such check: the DSDT control above is the
proof that the text scanner reaches a source that has the term.
vendor 3.1.39.0 GCUService.exe (shipped, bodies encrypted)  ACPIDriver x4, GpuConfigurableTGPTarget x1, GpuDynamicBoost x1
decompiled GCUService.dumped.exe (bodies decrypted)   ACPIDriver x4, GpuConfigurableTGPTarget x1, GpuDynamicBoost x1
vendor 3.1.6.0 UniwillService_3.1.6.0_STD.exe (installer)  (no probe hit -- source may be unread)
vendor 3.9.18.0 setup.exe (installer)                 (no probe hit -- source may be unread)
vendor 3.9.18.0 ACPIDriver.sys                        ACPIDriver x34
vendor 3.9.18.0 ACPIDriverDll.dll                     ACPIDriver x1
vendor 3.9.18.0 GamingCenter3_Cross .msixbundle (UWP front end)  FanViewModel x2, GpuConfigurableTGPTarget x5, GpuDynamicBoost x6, OverClock_SettingsView x5, UWP_Refactor x14
vendor 3.9.18.0 GamingCenter3_Cross .appxsym (PDB name table)  FanViewModel x2230, GpuConfigurableTGPTarget x12, GpuDynamicBoost x12, OverClock_SettingsView x624, UWP_Refactor x324

== readability census: .NET method-body headers ==
vendor 3.1.39.0 GCUService.exe (shipped)              tiny 1191  fat 1  invalid 3759  abstract/extern 349
decompiled GCUService.dumped.exe                      tiny 2630  fat 2321  invalid 0  abstract/extern 349

== readability census: ILSpy error markers in the .cs trees ==
decompiled/v3.1.39.0 (whole service, decrypted): 0 marker(s) in 0 of the .cs files
decompiled/v3.1.6.0 (partial, anti-tamper): 27 marker(s) in 1 of the .cs files
decompiled/v3.9.18.0 (partial, anti-tamper): 326 marker(s) in 15 of the .cs files

== [DllImport] surface of the decrypted service ==
  ACPIDriverDll.dll!SMAPCTable   GCUService/MyECIO/AcpiCtrl.cs:127

== unreadable by this method ==
The negative above is only as good as this list. Everything named
here is a place the search could not reach, not a place it looked
and found nothing.
  decompiled/v3.1.6.0 (partial, anti-tamper): 27 ILSpy error marker(s) across 1 .cs file(s), so every method body under them
    is unsearched. windows/antitamper/README.md; issue #3.
  decompiled/v3.9.18.0 (partial, anti-tamper): 326 ILSpy error marker(s) across 15 .cs file(s), so every method body under them
    is unsearched. windows/antitamper/README.md; issue #3.
  vendor 3.1.6.0 UniwillService_3.1.6.0_STD.exe (installer): no probe hit, because the payload is
    Inno-compressed inside the wrapper. What that payload
    contributes is already committed as the decompiled
    trees and the native decompiles; nothing else from the
    installer was read. windows/tools/extract.sh.
  vendor 3.9.18.0 setup.exe (installer): no probe hit, because the payload is
    Inno-compressed inside the wrapper. What that payload
    contributes is already committed as the decompiled
    trees and the native decompiles; nothing else from the
    installer was read. windows/tools/extract.sh.
  vendor 3.9.18.0 ACPIDriver.sys: its string table has none of the
    21 ACPI method names, because MSVC emits each one as a 4-byte
    immediate rather than a terminated string. The Ghidra decompile
    of the same file is a separate text input above and is where
    its IOCTL constants are covered.
  Not in this repository at all, and therefore not searched by
    anything above: firmware, including any ACPI component that
    defines \_SB.NPCF, which the DSDT only declares External
    (evidence/acpi/dsdt.dsl:54-65). A caller there would be
    invisible to every input in this table.
```

**The result.** Every `T1WR`-side term is zero in every Windows input.
`TempWrite*` appears in exactly one binary and one decompile across the
whole census — `ACPIDriverDll.dll`'s export directory, three hits for the
three exports, and the Ghidra decompile of the same file — which is the
definition, not a call. `0x9C40A4DC` appears only in the decompiles of the
driver and its wrapper, where it is the handler table. `0x1173`, its
decimal `4467`, and `AMAT`/`AMIT` occur nowhere in the census but the DSDT
control row, and that row is the proof the term set works: `T1WR` and
`AMAT` are *defined* in that file, and the scan finds them.

Two of the inputs are closed rather than merely searched:

- **`GCUService` 3.1.39.0 does not bind `TempWrite1`.** The whole service
  is committed with every method body decrypted, and its only
  `ACPIDriverDll.dll` P/Invoke in the entire tree is `SMAPCTable`
  (`windows/decompiled/v3.1.39.0/GCUService/MyECIO/AcpiCtrl.cs:127`) — the
  tool prints that row from a parse of the `[DllImport]` attributes, and
  `--self-check` fails if that ever changes. `IOCTL_GPD_ACPI_TMPWRITE1 =
  2621482204u` *is* declared at `AcpiCtrl.cs:93`, and the census finds that
  decimal spelled exactly once in the whole tree — at its own declaration.
  The private `WriteACPI(uint, int, int)` helper at `:373` is the only thing
  that sends one of these codes, and its one call site in the tree passes
  `2621482124u` (`IOCTL_GPD_ACPI_ECWRITE`, `:212`). "Declared and unused" is
  a different claim from "not searched", and this is the first. A .NET
  P/Invoke, including a late-bound `GetProcAddress`, has to carry the
  target name as a string, so the exclusion covers that too.
- **The UWP front end is not the caller either.** Its `.appxsym` PDB is a
  name source that survives method-body encryption, and its name table was
  read — the same scan finds `FanViewModel` 2230 times and
  `GpuDynamicBoost` 12 — with zero occurrences of `TempWrite1`, `T1WR`,
  `AMAT`, `AMIT`, `0x1173` or `0x9C40A4DC`. Its `.msixbundle` says the same
  (14 `UWP_Refactor`, 6 `GpuDynamicBoost`, no caller term), and so does the
  Ghidra decompile of its native component. Structurally that is what the
  architecture predicts: `windows/mqtt-protocol.md` records that the UI and
  the service do not touch the EC across the app boundary at all — they
  exchange JSON over a local MQTT broker and `GCUService` is the only party
  that reaches hardware — and `windows/README.md` has the UI as a sandboxed
  UWP app, which is what puts `\\.\\ACPIDriver` out of its reach. A
  behavioural prediction that the byte census independently matches, which
  is why it is worth more than either alone.

**What stayed unreadable**, in the tool's own words, and repeated here
because a negative is only as good as this list: the anti-tamper-encrypted
bodies in `v3.1.6.0` (27 ILSpy error markers, all in
`BatteryProtection2.cs`) and `v3.9.18.0` (326 markers across 15 files) —
issue #3. That is the sharp edge of the negative: the `v3.1.6.0` tree is
two files, and the one carrying the markers is the class whose
`SetBatteryChargingLimit_Down` is the service's only `0x07D0` writer, so
the miss there is a miss in exactly the class the question is about. The
two Inno installers' compressed payloads beyond what is already committed
(`windows/tools/extract.sh`); `ACPIDriver.sys`'s string table, which
carries none of the 21 ACPI method names because MSVC emits each as a
4-byte immediate rather than a terminated string — its Ghidra decompile is
a separate input in the table above and is where its IOCTL constants are
covered; and, outside the reach of any committed input, **firmware** —
including whatever defines `\_SB.NPCF`, which this DSDT only declares
`External` (`evidence/acpi/dsdt.dsl:54-65`). An ACPI component in firmware
is a perfectly ordinary place for a `T1WR` caller to live, and nothing in
this repository can see one.

**The other door, closed by the same search.** `ACPIDriver.sys` hardcodes
the method name per IOCTL (`movl $0x52524345,0x54(%rsp) ; MethodName =
'ECRR'`, `windows/native/ACPIDriver.sys.analysis.md:177`), so
`TempWrite1` is not the only way to reach `T1WR` — Windows' own
`IOCTL_ACPI_EVAL_METHOD` takes the name in the caller's buffer, which is
what the driver forwards to. A caller that took that route would still have
to carry `T1WR` and the value `0x1173`, and both are in the term list, so
that route is inside the same negative rather than outside it.

**The neighbouring branches, so GPU power is told apart from battery
code.** This is the part of the method §4f did not have, because it read
the `0x1173` branch in isolation. Every `Arg0` in the block, and what it
does:

| `Arg0` | `dsdt.dsl` | EC byte it writes | `NPCF` object it sets | gated on |
|---|---|---|---|---|
| `0x1171` | 50658-50665 | `CTWA` = `Arg1` (`0x0788`) | `CTGP` = 1, `UOCT` = `CTWA * 8` | — |
| `0x71` | 50667-50673 | — | `UOCT` = `CTWA * 8` (re-publish) | — |
| `0x1172` | 50675-50678 | — | `DBAC` = `Arg1` | — |
| **`0x1173`** | **50680-50691** | **`DBD1` = `Arg1 * 8` (`0x07D0`), `DBD2` = `Arg2 * 8` (`0x07D1`)** | `DBAC` = 0, `AMAT` = `DBD1`, `AMIT` = `DBD2` | — |
| `0x2273` | 50693-50698 | — | `ATPP` = `Arg1 * 8` | — |
| `0x73` | 50700-50717 | — | `DBAC` = 0, `ATPP` = `CPUA * 8` (`0x07D4`), `AMAT` = `DBAP * 8` (`0x07D5`) | `DBEN` (`0x07C4` bit 0 — **corrected, bit 3**) |
| `_Q84` | 52793-52811 | — | same as `0x73`'s then-branch | `DBEN`; raised by the EC, not by an ACPI client |
| `0x1176` | 50730-50733 | `CGCT` = `Arg1` (`0x07D7`) | Notify `PEGP` | — |

**CORRECTION to the `0x07C4` bit in the `0x73` row, added 2026-09-24
(issue #183). `DBEN` is bit 3, not bit 0.** The bit-0 reading above came
from counting the field list as if its unnamed bits were not there. The
DSDT ECMG field list at `evidence/acpi/dsdt.dsl:52238-52242` is

```
Offset (0x7C4),
    ,   3,
DBEN,   1,
    ,   1,
DBST,   1,
```

— three unnamed bits, then `DBEN`, then one unnamed, then `DBST`. So
`DBEN` is bit 3 and `DBST` is bit 5, and both ASL sites test the named
1-bit field (`If ((DBEN == One))`, at `dsdt.dsl:50702` and `:52796`)
rather than bit 0. The gate itself is unchanged: it is `DBEN` either way.
§4a's body and its table are left as written; this is the correction beside
them, not a rewrite. The `0x07C4` entry in `ec/annotations/registers.yaml`
and the walk in `ec/annotations/ec-07c4-07d5-sites.md` carry the corrected
bit, and §7c carries what the capture adds.

No branch in the table touches a battery or charge register. The
`0x1171`/`0x1172`/`0x1173`/`0x2273` selector family and the `0x73`/`_Q84`
query pair both end at the same `NPCF` objects, and the `0x73`/`_Q84` pair
reaches them from `CPUA`/`DBAP` at `0x07D4`/`0x07D5` rather than from
`0x07D0`. That is the strongest structural evidence available here that
`0x07C4`-`0x07D7` is a GPU dynamic-boost control block and not battery
state, and it is new relative to §4f.

Two things in the ASL are worth writing down because they are the kind of
detail a re-derivation would otherwise trip over. The `0x73`/`_Q84` path
gates on `DBEN` at `0x07C4` bit 0 (bit 3 — corrected above and in the
sentence that follows) and, when it is clear, sets `DBAC = 1`
instead — so the same method is both the publisher and the "not available"
signal. And `T1WR` has two `ElseIf ((Arg0 == 0x71))` branches: the first
(`:50657`) has an empty body and the second (`:50667`) has the work, so on
a first-match ASL chain the second is unreachable. The same holds for the
empty `0x83`/`0x86`/`0x87`/`0x74` slots: reserved selectors with no
implementation, which is what a generated ASL template looks like.

**The arithmetic bound.** `DBD1` is one byte and the branch stores
`Arg1 * 8` into it, so `Arg1` cannot exceed 31; likewise `Arg2` for
`DBD2`. That is arithmetic on the committed ASL and nothing more. It does
*not* say what the argument means — only that whatever it is, it is small
enough that the EC byte can hold eight times it.

**§4f's question, answered as far as the inputs allow.** The short form:
in every committed input, the only writer of `0x07D0` writes it as a GPU
power value, and `ADDR_BATTERY_CHARGE_LIMIT_DOWN` is a vendor constant with
no committed writer behind it on this machine. The long form, with the
citations:

- The DSDT writes `0x07D0` as a GPU power value, and the block it writes it
  into is GPU on the evidence of the neighbouring branches above.
- `ADDR_BATTERY_CHARGE_LIMIT_DOWN = 2000`
  (`windows/decompiled/v3.1.6.0/ECSpec.cs:387`) has exactly one writer in
  the decrypted service: `BatteryProtection2.SetBatteryChargingLimit_Down`
  (`windows/decompiled/v3.1.39.0/GCUService/GCUService.MySystem/BatteryProtection2.cs:347`,
  writing at `:356`, the only `0x07D0` write row in
  `windows/decompiled/v3.1.39.0/ec-callsites.csv`). That method is
  `private` and has no caller anywhere in the 3.1.39.0 tree — the same
  situation `registers.yaml` already records for its `0x07B9` sibling, and
  for the same reason: `private` plus no caller in a decrypted build is
  checkable, unlike a grep miss in an encrypted one. Note also *which* door
  it goes through: `EcCtrl.Write` → `AcpiCtrl.Write` →
  `WriteACPI(IOCTL_GPD_ACPI_ECWRITE)` → `ACPIDriverDll!WriteEC` → `ECRW`,
  the §4e path that writes the byte raw. It never touches `T1WR`, so the
  two writers of `0x07D0` found here are not two views of one mechanism.
- The service's *own* GPU dynamic-boost path does not go through `0x07D0`
  either. `GpuFeatures` writes `0x0743`/`0x0744`/`0x0745`/`0x0746` —
  enable bits, cTGP target, DB total-processing-power target, DB maximum TGP
  (`windows/vendor-ec-map.md:84-87`, and the `0x0743`-`0x0746` rows of
  `windows/decompiled/v3.1.39.0/ec-callsites-summary.csv`). The DSDT names
  that second block too, at `Offset (0x743)`: `GNEN`/`ECDC`, then `CTVA`,
  `DBCT`, `MXDB`, `MIDB` (`evidence/acpi/dsdt.dsl:52204-52212`). So there
  are two GPU-related blocks, one at `0x0743`-`0x0746` that the host writes
  and one at `0x07C4`-`0x07D7` that ACPI reads out to the NVIDIA device,
  and which way `0x07D0`/`0x07D1` sits relative to the second is not
  something the committed inputs settle. That is a follow-up, named below.

**What this does not establish.** It does not establish that `0x07D0` is
*not* also a charge threshold in the EC firmware. The census covers
Windows and ACPI, not the 8051 program; whether the main EC image acts on
`0x07D0` at all is the indirect-XDATA blind spot, #34, and the 254
`0x07D0` sites are the PD image's own variables, #25. A vendor constant
with no caller is not a name proved stale: the byte could still be a
threshold to firmware this repo cannot read. `registers.yaml` keeps the
status at `unknown-not-absent-DO-NOT-WRITE-BLIND` for that reason, and
`--self-check` in the tool asserts the census so a later dump that *does*
bind `TempWrite1` cannot pass unnoticed.

**The clobber hazard, recorded and not fixed.** Two decoded paths write
the same physical byte, `0xFE4107D0`: the vendor charge-limit write
(`ECRW`, §4e) and the GPU TGP write (`T1WR 0x1173`). They disagree about
scale as well: `ECRW` writes the byte raw, so a charge limit of 55% lands
as `0x37`, while `T1WR 0x1173` stores `Arg1 * 8`, so the largest value
that branch can produce (`Arg1` = 31) lands as `0xF8`. The byte's value
therefore carries a different meaning depending on which door wrote it, and
a reader of the byte cannot tell which. That is arithmetic on two decoded
paths, not an observed failure: no hardware was involved in establishing
any of it, and the live writes in §4f remain the only hands-on test this
byte has had — nothing here, and nothing there, observed a clash. One limit
on the hazard is worth stating rather than letting a reader assume
otherwise: **whether the GPU ever reads `0x07D0` is not established.**
`T1WR 0x1173` sets `AMAT` from its own argument in the same breath as it
writes the byte, so an `ECRW` write is not by itself a way to reach the
NVIDIA device through this ASL. The hazard is that two writers fight over
one byte whose meaning is not the same for both, and that the byte is not
safe to write blind — which is why `DO-NOT-WRITE-BLIND` stands.

There is a second, narrower version of the same hazard that needs no
assumption about firmware at all, because it is entirely inside the
committed ASL: **`AMAT` and `ATPP` each have two writers in the DSDT.**
`AMAT` is set from `DBD1` (`0x07D0`) by `T1WR 0x1173` and from `DBAP`
(`0x07D5`) by `T1WR 0x73` and by `_Q84`; `ATPP` is set from `Arg1` by
`0x2273` and from `CPUA` (`0x07D4`) by the same `0x73`/`_Q84` pair. Each
writer ends in the same `Notify (NPCF, 0xC0)`, so the value the NVIDIA
platform controller reads is whichever method ran most recently. This is a
statement about the ASL, checked against a committed file, not an
observation of a fault.

**Follow-ups this opens,** which is the point of writing the negative down
rather than closing on it:

- A Windows-side capture issue naming exactly what a human with the machine
  should observe: the loaded-module list at the moment `0x07D0` moves under
  a TGP or Dynamic Boost change, and an EC trace across the same change.
  That is the only route left to the caller if it is not in the committed
  inputs, and it is the step no cloud agent can take.
  *(2026-09-24, issue #184. That issue is open and the procedure it asked
  for is committed at
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`, beside
  `manual-fan-ctrl-0751-isolation.md`: an observe-only one-clock watcher of
  `0x07C4`-`0x07D7` together with `0x0743`-`0x0746`
  (`windows/tools/gpu_block_watch.py`), a written ProcMon/`\\.\ACPIDriver`
  `IOCTL`-code attribution half keyed on the two door codes the committed
  inputs already name — `0x9C40A4DC` (`T1WR`), which is in this section's
  own term list, and `0x9C40A48C` (`ECRW`), which is what
  `windows/tools/ecrw.py` opens every byte through — a blank result table,
  and a per-address citation list checked against the DSDT and
  `registers.yaml` by `windows/tools/test_gpu_block_watch.py`. **The
  observation is still not made** — it needs the physical machine, which no
  cloud agent has. The issue stays open for that reason and not because the
  preparation is missing.)*
  *** CORRECTION 2026-09-24 (issue #283), leaving the paragraph above as it
  was written: it says "#184. That issue is open", and #184 is closed.** It
  was the issue that asked for the procedure, and the procedure it asked for is
  committed; what is still open is the *run*, which #184's closure does not
  own and which is now issue #283's. The second stale pointer goes with it:
  that same paragraph credits the preparation as complete, and the grading half
  of it was not — #283 adds `ec/tools/grade_gpu_door.py`, the offline grader
  that applies the five capture-derived columns of that procedure's §5 table
  to a §3 capture and names the other five as not its own, plus
  `ec/tools/test_grade_gpu_door.py` over constructed fixtures. Both are
  exercised only against files written by hand; **no capture of this procedure
  has been taken and none has been graded.** No status moves on the strength of
  a grader that has never read a real capture, and nothing under `evidence/`
  comes from it.
- A register census for `0x07C4`-`0x07D7` (`DBEN`/`DBST`, `DBD1`/`DBD2`,
  `GFID`, `CPUA`/`DBAP`/`DBSP`/`CGCT`) in the shape this section gives
  `0x07D0`: which of the two GPU blocks the host writes, which ACPI reads
  out, and what `0x07D0`/`0x07D1` are doing in the middle. `0x07D1` now has
  a `registers.yaml` row and a reference split (76 sites, all PD image, none
  in the EC firmware — `ec/annotations/static-refs-audit.md` §6) but no
  per-site decode, and that is a real gap rather than a formality.
- A `uniwill-laptop`-side question feeding #96: if the charge-limit write
  path is revisited, should it read `0x07D0` before writing it? The answer
  depends on what a human observes, and the upstream correction in #96
  should not be written as though the byte has one meaning.

Cross-references, so this does not re-open what others own: #34 and #25 for
the EC firmware side, #3 for the still-encrypted 3.1.6.0/3.9.18.0 bodies,
#96 for the upstream correction this re-grade feeds, and #10 for the rule
that no stage opens a pull request against another repository.

`ec/annotations/registers.yaml` is updated in the same change: the `0x07D0`
entry is renamed to the DSDT's `DBD1` with the vendor constant kept in the
parenthetical, its note carries the result above, and `0x07D1` gets its own
row. Both keep `unknown-not-absent-DO-NOT-WRITE-BLIND`. §4f above is left
as written, with this section as the answer to the question it ends on.

## 5. Net status going into the issue tracker

*(**2026-09-19 update, read before the bullets below.** §4j–§4l change the
charge-limit bullet. The cap exists on the current firmware as a
charge-voltage target of 16.4 V (§4l), and the service-side question is
closed by the decrypted source (§4k). The bullets below are kept as
written.)*

*(**2026-09-23 update.** §4o narrows the first bullet further: the "one
place a numeric threshold could still hide" — `GCUService`/
`BatteryProtection2` — has been read in the *decrypted* 3.1.39.0 tree, and
`SetBatteryChargingLimit_Up/Down` are `private` with no caller, so on this
version there is no threshold there to find. Issue #3 still matters, for
the two older builds whose bodies are still ciphertext; and `0x07D0`'s
only committed writer turns out to be the ACPI DSDT's GPU branch, not the
service at all.)*


- Charging-cap-on-Linux is still an **open problem**, but much narrower.
  The paired `0x07B9`/`0x07D0` write was run (§4f) through the vendor's
  physical path and did not stop charging in any of five variants, ruling
  out "the access path differs". The Windows-side EC trace §4f named as the
  other route has now been taken (§4g, §4h): with the vendor service
  running, the only EC byte its battery-protection UI drives is the
  `0x07A6` profile mask, and the UI→service MQTT command carries a mode
  name (`HEALTHYMODE`/`BALANCEDMODE`/`PERFORMANCEDMODE`) with no numeric
  threshold at all. So the `0x07B9`/`0x07D0` pair is, on this machine, not
  the mechanism — which reframes issue #1 from "write the pair correctly"
  to "does any profile enforce a hard stop, and if so where is the
  threshold". The one place a numeric threshold could still hide is inside
  `GCUService`/`BatteryProtection2` (issue #3); it is no longer on the wire
  and not in the registry (`HKLM\SOFTWARE\OEM\GamingCenter2\BatteryProtection2`
  holds only `HealthProtectionStatus`, the mode index). The live coulomb-count
  that would have tested "does the profile stop charging at all" has now been
  run (§4i): it does **not** — Stationary charged smoothly through ~86% at
  full taper current from 28%, again after profile cycling, and again after a
  clean unplug/replug with the profile armed and untouched. The 2021
  fake-charge screenshot (charge rate → 0 at ~86%, gauge spoofed to 100%) did
  not reproduce in any configuration. So on this EC image + Control Center
  3.1.39.0 the vendor's own protection does not cap, which means the Linux
  gap is not a driver gap — the mechanism is not engaging on Windows either.
  The charge-limit thread now turns to firmware archaeology: identify the
  2021-era EC image / CC version that did cap (live EC self-reports
  `EcVersion = 1.18`, provenance vs the committed `GMxMGxx_11.800` unverified),
  rather than to writing any register on the current one.
- Lightbar is a **driver-scope problem, not a hardware problem** — claim
  `048D:6005` for `ite_8291_lb` and test.
  **2026-09-17 update:** static red/off now works through raw HID with the
  6010 sequence (§3); the user confirmed no keyboard change. An ID-only
  patch is insufficient: explicit 6005 command dispatch and driver lifecycle
  validation remain, so issue #5 is still open.
- Decrypting the anti-tamper-protected `BatteryProtection2` method bodies
  (`windows/antitamper/`) would settle both open EC questions
  (`0x07D0`'s real role, and whether enforcement is EC-side or
  polling-software-side) without any further live experimentation risk. The
  static route to `0x07D0` is now exhausted on the firmware side: §3b mapped
  every reference the image has and none of them is the EC's.
  *(**2026-09-19:** done for 3.1.39.0, §4k. The service turns out to write
  neither `0x07D0` nor `0x07B9`, and to enforce nothing itself.)*

## 6. Firmware identity and UEFI variables (2026-09-19, issues #84 and #86)

**The committed EC image is the one the committed BIOS package flashes.**
`vendor/bios-1.09/BIOS_1.09.zip` contains `GM7MG7P/GMxMGxx_11.800`,
byte-identical to `ec/firmware/GMxMGxx_11.800` (SHA-256 `158D1C64…99C4` for
both). The package's `ecflash.nsh` flashes it with
`IFUX64.efi GMxMGxx_11.800 0 1`. The live machine runs BIOS `N.1.09A08`
(2021-03-18), and SMBIOS Type 0 reports EC firmware **1.18**. The vendor's
`EcVersion` registry value is copied from exactly that
(`HardwareInfoCollect.getECInfo()` reads WMI `MS_SystemInformation.ECFirmwareMajor/MinorRelease`).
So the chain is: the BIOS 1.09 package ships `11.800`, and the machine
runs BIOS 1.09 with an EC reporting 1.18. Reading "11.800" as "1 18 00"
fits, but nothing here proves the running EC was flashed from this file
rather than a later one. That still needs #84's byte-level dump.

**The vendor flasher has no read mode.** `ifux64.efi` is "ITE Flash Utility
2.0.3". From its strings: it sends KBC `0xAD` and EC `0xDC`, enters ITE
follow mode, reads the SPI ID, then erases, programs and verifies. Its only
usage is `ifu <ec filename> [burn offset] [reset]`. The pieces of a read
path exist inside it (verify reads the flash back), but no dump option.
Dumping the live EC flash therefore needs either a follow-mode reader
written for the purpose, or an external SPI programmer. Both halt or bypass
the running EC and are human steps.

**Setup variables are not visible from the OS.**
`windows/tools/uefi_var.py list` (`evidence/uefi/2026-09-19-variable-list.txt`)
sees 114 runtime variables. `UniWillVariable`, `OcSetup`, `SetupCpuFeatures`
and `CpuSetupVolatileData` are among them. AMI's `Setup`, `SaSetup`,
`PchSetup`, `CpuSetup` and `MeSetup` are not: they are boot-services-only, so
neither Windows nor Linux can read or write them after boot. A live read of
a hidden setup option (#86) therefore has to happen pre-OS: a UEFI shell
with a `setup_var`-style tool, at offsets taken from the Setup IFR. The IFR
side is doable from committed files (`vendor/bios-1.09/`), and
`.github/actions/project-setup` now installs UEFIExtract and ifrextractor
for it. The extraction itself was not done this session.
*(**2026-09-23:** done. `bios/tools/bios_extract.py` regenerates the IFR
as `bios/ifr/Setup.en-US.ifr.txt`; §8 uses it.)*

**`UniWillVariable`** (`{9f33f85c-13ca-4fd1-9c4a-96217722c593}`, 180 bytes,
NV+BS+RT) is the settings block the vendor service shares with the BIOS;
the layout comes from the decrypted `NVRAM_STRUCT.cs`. Its battery bytes
(`BatteryLimitation`, `ChargeMaximumLimit`, `ChargeMinimumLimit`, offsets
0x30-0x32) read 0 after the BIOS load-defaults. Which of its fields the BIOS
consumes is not known.
*(**2026-09-23:** partly known now. `OemOcDxe` consumes
`MemoryOverClockSwitch` (0x33), the core-voltage fields and `ApExistFlag`,
and writes `OverClockRecoveryFlag` and the voltage ranges back (§8). The
battery bytes 0x30-0x32 are not among the fields it touches.)*

## 7. Power modes: what Office, Gaming and Turbo write (2026-09-23, issue #92)

The full trace, with file:line citations into the decrypted 3.1.39.0
service, is in `../windows/vendor-ec-map.md` under "Power modes". In short:

**A mode is a bundle, not a register.** On every switch, and on every AC ↔
battery change, `MyFanManager_RamFan1p5.SetUserProfile` writes:

- the fan-mode byte `0x0751` (Office `0xA0`, Gaming `0x00`, Turbo `0x10`);
- PL1/PL2/PL4 at `0x0783-0x0785` (35/35/165, 60/60/165, 75/75/165 W, or
  0/0/0 on battery), seeded from the EC's own per-mode default bytes;
- a 96-byte fan table at `0x0F00-0x0F5F`, bracketed by `0x07C6` bit 2;
- and, on AC, the same GPU cTGP/DynamicBoost bytes `0x0743-0x0746` in all
  three modes.

The "profiles 1-5" inside each mode are user slots that all start from the
same defaults. The Fn mode key is EC event `0xB0`, and the *service* picks
the next mode.

**Confirmed live, as the vendor's writes.** An AC plug-in and six Fn-key
switches were captured with `ec_watch.py` on `0x0700-0x07FF` and
`0x0F00-0x0F5F`, alongside a passive pcap of the vendor MQTT broker
(`../evidence/ec-watch/2026-09-23-power-mode-cycle-*`,
`../evidence/mqtt-capture/2026-09-23-power-mode-cycle.*`). Every predicted
byte landed. `windows/tools/fan_table_replay.py` shows all seven fan-table
states the capture passed through equal the tables the service announced
on `Fan/Table`, byte for byte. What this shows is that the vendor's writes
land, not that the EC acts on each byte. In particular, **nothing here says
what the EC does with `0x0751` alone**, because the service always wrote the
whole bundle. That's the question a Linux platform profile hinges on, and it
needs its own live test.

**New questions.**
- Who sets `0x07C6` bits 0-1 (DSDT `WMS0`, read back as NVIDIA Whisper
  Mode) on every switch into Office? No GCUService EC call site does.
- The EC answers a "give me your default fan table for mode N" handshake
  through a mailbox in `0x0F5D-0x0F5F`. The EC side of it is unread, and
  nobody has compared its answer against the stored JSONs.
- Upstream `uniwill-laptop` names `0x0786` a fan default, where the DSDT and
  the vendor use it as the CPU TCC offset. Upstream also treats `0x0742`
  bit 4 as "Turbo supported"; that bit is clear here, yet the vendor offers
  Turbo from `0x049F` bit 1.

### 7a. What the EC's own code does with `0x0751` (2026-09-23, issue #99)

§7 left the question that sizes a Linux `platform_profile`: the service
always writes the whole bundle, so what does the EC do with the mode byte
*alone*? The static half is now answered as far as a site scan can answer
it, in `../ec/annotations/manual-fan-ctrl-0751.md`, with the per-site table
in `../ec/annotations/manual-fan-ctrl-0751-sites.csv`.

All 29 direct reference sites are in the main EC image, and every one of
them touches `0x0751` and no other XDATA byte — nineteen reads that mask or
branch on the four bits upstream names (`TURBO` 4, `HIGH` 5, `BOOST` 6,
`USER` 7), seven read-modify-writes of those same bits, one blind write, two
whose `mov dptr` is staged before an unrelated test. Two results fall out:

- **Nothing carries a per-mode default into a PL register.** The twelve
  default bytes (`0x0730-0x0737`, `0x07A7-0x07AA`) have no read site
  anywhere in the image; every site found is the EC *writing* them, for the
  host to fetch — which is how the vendor uses them. The EC's only found
  writer of `0x0783-0x0785` is at `0xA833-0xA83B`, it writes zero, and it is
  gated on `AP_OEM` (`0x0741`) bit 0 — the host-present flag — not on the
  mode. That gate is the more interesting half for a driver, and *when* the
  routine runs is not established.
- **The EC agrees with the service on the encoding.** Its own Turbo path
  (`0xABE8`/`0xC741`, behind `0x049F` bit 1) produces `0x10`, and it sets a
  boot default off `BIOS_OEM_2` (`0x0782`) bit 4 — Gaming `0x00`, or `USER`
  set and `TURBO` cleared for Office. That is an independent confirmation of
  the values §7 took from the vendor's constants; it says nothing about
  whether the EC acts on a value the *host* wrote.

**§7's "the EC side of the `0x0F5D-0x0F5F` mailbox is unread" is now partly
read.** The handler at `0x888D` wants `0xFD`/`0xC9` as a magic in
`0x0F5D`/`0x0F5E` and a selector of 1-3 in `0x0F5F`, and copies two 48-byte
default fan tables out of CODE into `0x0F00` and `0x0F30`. Selector 3 is
Office and picks between two tables on `0x0782` bit 2, the "Office fan-table
type" bit whose vendor getter is never called. Comparing those built-in
tables against the vendor's announced ones is still nobody's work.

**None of this is a live test**, and the method is blind to indirect access
— the same scan reports zero direct sites for `0x0F00-0x0F5C`, a page the EC
provably writes through a computed `DPH`, which is §4d's blind spot showing
up on a second address. `MANUAL_FAN_CTRL` therefore stays `present-untested`.
`hardware-tests/manual-fan-ctrl-0751-isolation.md` is the procedure that
would settle it, written for a human with the machine and **not run**.

### 7b. The window stops at the branch: both arms of all 17 mode-bit branches (2026-09-23, issue #129)

§7a is a statement about an 8-instruction window around each of the 29 sites,
and the window ends at the first control-flow instruction. For 17 of them that
instruction *is* a conditional branch on a mode bit, so both arms were
unexamined when §7a was written — and the arms are where the code is. All 34
are now walked, with `ec/tools/walk_branch_arms.py` and the committed table
`../ec/annotations/manual-fan-ctrl-0751-arms.csv`; the per-site reading is §9
of `../ec/annotations/manual-fan-ctrl-0751.md`.

Three results, and the first is the one §7a was reaching for.

- **Both fan duty bytes are written on a path a `0x0751` bit
  selects.** `0x075B` at the `0x89E0` and `0xBB29` write sites, on the Fan
  Boost *not set* side of the `0x8942`/`0x899D` arms; `0x075C` at `0x8F0A`
  and `0x8F11`, on *both* arms of `0x8E8B` (USER). A byte scan puts these two
  bytes' write sites at five addresses in the main EC and the arms reach four
  of them; the fifth, `0x87C5`, is not reachable from any of the 34, which is
  the limit of the claim rather than a fact about the EC — issue #123 later
  found it to be a zero-clear rather than a fan-curve path, so the walk did
  not miss it. Neither address is
  in `registers.yaml` and
  neither has ever been confirmed, so this is **not** "the fan PWM bytes are
  the mode byte's effect" — it is that the EC stores to both bytes there, on a
  path chosen by one bit. That is the static prediction
  `hardware-tests/manual-fan-ctrl-0751-isolation.md` §4.4 was asking for: two
  named bytes to watch and a named bit to flip, instead of a pointer at
  `0x075B`/`0x075C` with no prior.

  **Correction (issue #123, 2026-09-24), leaving the bullet above as it was
  written.** Both addresses are now in `registers.yaml`, as `MAIN_FAN_L_DUTY`
  and `MAIN_FAN_R_DUTY`, and both are confirmed as to what they are: the
  vendor's `ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE`, read and halved by `FanInfo` and
  never written by it. So "fan PWM bytes" is the wrong name for them twice
  over — they are duty, and the vendor's PWM-named bytes are a different
  block (`0x0743`-`0x0747`, `0x0786`-`0x078D`). The EC keeps the value in
  `0x1804`/`0x1809` and publishes it through the `0xBB22`/`0xBB28` helper,
  with `0xC8` as the 100 % cap in the same doubled convention the fan table
  uses — the `/2` the vendor applies is the EC's own, not a display artefact.
  What the bullet actually claims still stands and is still only a static
  prediction: the EC stores to both, on a path one bit of `0x0751` selects.
  Whether the mode byte is a usable control is still the fixed-load
  experiment §4.4 asks for, and `0x0751` stays `present-untested`.
- **The Fan Boost arms gate on temperature, and the EC writes `0x0751` back.**
  `0x8942`'s BOOST-set arm reads `0x085F` against `0x3C` (60), `0x086C` against
  `0x50` (80), then `CPU_TEMP` `0x043E` and `GPU_TEMP` `0x044F` against `0x46`
  (70 °C) — and if both are under the limit, clears `BOOST` in the mode byte at
  `0x8990`. So there are now three paths on which the EC writes `0x0751`
  (§7a's two boot defaults, and this), and a host write need not persist. For
  a driver that is a first-order fact, and it is not in §7a.
- **§7a's no-PL-write conclusion survives the arms.** None of the 34 arms, nor
  any of the 137 callee rows at `--callee-depth 1`, stores to `0x0783-0x0785`.
  The arms do *read* `0x0784` and `0x0785` and branch on them, so the mode
  bits gate code that consults the power limits rather than setting them. Read
  and write are different claims and §7a's was about the write, so this
  refines it rather than correcting it — no retraction is warranted.

**Calibration, because the negatives are the deliverable.** Every arm reports
`status: complete` at the tool's default bounds, so "no arm found by this
method writes a PL" is not "the walk gave up first". The method's blind spots
are still named per row in the CSV — indirect `movx @Ri`, a `DPTR` built at run
time, a callee not followed — and one of them bit here in a way worth
recording: the bank1 `0x9432` arms hand `0x93B6`/`0x93E6` to `r2`/`r1` and
rebuild `DPTR` from them, so a tool tracking only `mov 0x82,a` would report
`0x93E6` as an XDATA register. It is a **CODE** pointer — the same blind spot
as §7a's computed `DPH`, on the other side of the same argument.

There is a method finding inside the tool worth its own line, because it is
the kind that silently corrupts a table: writing the PC-relative branches as
the range `0xB4-0xDF` treats `clr c` (`0xC3`) and `setb c` (`0xD3`) as
branches, and the walk then decoded the rest of a routine as `dec r0` /
`db 0x06`. The correct set is `disasm8051.REL_OPCODES`, which the tool imports
rather than restating, and `walk_branch_arms.py --self-test` now carries a
fixture that fails if the range comes back.

**None of this is a live test.** No register was read back and no hardware was
observed; there is no laptop on this runner. `MANUAL_FAN_CTRL` stays
`present-untested` and its `static_refs*` counts stay 29/29/0 — a static walk
cannot move them, and the status vocabulary reserves `confirmed-inert` for a
live three-value, both-service-states run that §7 of the isolation procedure
specifies.

**A partly-graded day cannot carry that `confirmed-inert` call, and the grader
that would read it now says so instead of implying it.** The closing summary of
`ec/tools/grade_0751_isolation.py` had two cases where a run has three, so a
three-value day with a withheld block printed "consistent with the static
prediction" over the 6 of its 8 windows it had actually read. Write-up:
`docs/findings/0751-grader-partial-grade-claims.md`.

### 7c. `0x07C4` moved on 2026-09-23, and the 15 EC-side sites of `0x07C4`-`0x07D5` (2026-09-24, issue #183)

**The observation, already in the tree and written down nowhere.** §7 cites
`evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv` for "every
predicted byte landed". That file has two rows for an address §7 does not
list, and §4o — which reads `0x07C4`-`0x07D7` as a GPU dynamic-boost control
block from the ASL alone — never mentions:

```
2026-09-23T17:57:51.161+02:00,0x07C4,0x08,0x28
2026-09-23T17:57:51.597+02:00,0x07C4,0x28,0x38
```

Two writes, 0.44 s apart, at the AC plug-in in the same capture where
`0x0743`, `0x0745` and `0x0746` land. The first sets bits 3 and 5; the
second sets bit 4.

**Scope, stated because it is easy to over-read.** This is one capture, one AC
plug-in and six Fn-key mode switches, watched passively. It is not an
observation of *who* wrote the byte: no committed input writes `0x07C4` at
all (`ec-callsites-summary.csv` has no `0x07C4` row, and `1988` is absent
from `windows/decompiled/v3.1.6.0/ECSpec.cs`, whose `ADDR_AP_OEM` constants
step straight from 1987 to `ADDR_AP_OEM_BYTE5 = 1989`), so the writer is the
EC firmware or firmware outside the committed inputs. And bit 3 — the bit
`DBEN` names, after the correction above — was **already set** in the `0x08`
baseline, so the first write is not evidence of the ASL's gate being opened
and the second is not evidence of it closing. Those are two writes with a
question attached, not a confirmation. No register was written or read back
to establish any of this; the file is quoted as a committed capture.

The same file's distinct-address set is `0x070A 0x070F 0x0714-0x0719
0x071A-0x071C 0x0743 0x0745 0x0746 0x0751 0x075B 0x075C 0x0783 0x0784
0x0785 0x07A6 0x07C4 0x07C6` — so **`0x07D0` and `0x07D1` did not move** at
all, across the plug-in and the six mode switches. That is new information
about the pair §4o re-graded, and it is recorded in both of their
`registers.yaml` entries. It is scoped to those events over that window, not
to "never written".

**The 15 EC-side sites, and what they are set from.** §4o closed with a
census as the next step and named the sharper one. The four addresses have
117 direct `MOV DPTR` sites between them, of which **15 are in the main EC
image** and 102 in the `ITE8850-PD` program with its own XDATA map — against
**zero** for `0x07D0`/`0x07D1`. That asymmetry is the point, and it is
opposite to the two §7a walked: `0x07C4` is 5 of its 8 sites in the EC
image, `0x07D4` 2 of 70.

`ec/annotations/ec-07c4-07d5-sites.md` walks all fifteen, with the site
table in `ec-07c4-07d5-sites.csv` beside it. The load-bearing results:

- **Eight of the fifteen are one routine**, entered at `0x83FF`, already
  named `sync_0788_and_07d4_from_09e9` and exported as
  `ec/decompiled/bank0/83FF.c`. It copies `0x09EA`→`CPUA` (`0x07D4`) and
  `0x09EB`→`DBAP` (`0x07D5`) when they differ, gated on `CTGP_DB_CTRL`
  (`0x0743`) bit 0 — and then sets bit 3 of `0x07C4` to follow bit 4 of the
  same byte (`orl a,#0x08` / `anl a,#0xf7`). **So `0x07D4`/`0x07D5` are set
  from `0x09EA`/`0x09EB`**, on the path this method finds. That the bit-3
  write is the ASL's `DBEN` gate is an inference from the bytes, recorded as
  one.
- **A second `0x07C4` writer sets bit 4**, at `0x94C0`
  (`set_07c4_bit4_from_r7`, `ec/decompiled/bank0/94C0.c`), and its one
  direct caller passes bit 1 of `0x0743`. Neither writer is the one that
  ran on 2026-09-23: `0x83FF`'s only caller is `0x8551`, inside the
  unresolved three-byte `lcall`/`ljmp` run at `0x851B` that §7a hit and
  deferred, so neither can be lined up against a capture timestamp.
- **`0x07D3`'s `GFID` field is written outright** with the values 3, 4, 5
  and 7 (`0x30`/`0x40`/`0x50`/`0x70`) by two sites in the routine entered at
  `0xD9FE`, selected by bits of `0x1666` and `0x166A`. The routine is named
  `seed_07d3_gfid_and_08xx_defaults` as of this change.
- **`0x07D5`'s other two EC-side writers store the immediate `0xFF`**, each in
  a reset-shaped run; neither run's entry point is determined by the methods
  used.

**Calibration, and the one negative worth its shape.** A byte-pattern hunt
for the `0x0F00` computed-`DPH` idiom retargeted at this page —
`addc a,#0x07 ; mov DPH,a` — finds **zero** hits in the EC image, while the
`0x0F00` control reproduces its eight exactly. That is a null, and §7a is the
reason to distrust one: a computed `DPH` and an indirect `movx @Ri` are
invisible to both that grep and the site scan, so the 15 is a floor, not a
total. All four entries are `present-untested` for the same reason §7a's
`0x0751` is — a static walk supplies real references and no live exercise,
and a passive capture showing a byte move is further from a live test than a
live run with a mechanism isolated would be.

**What this opens.** `0x09EA`/`0x09EB` (the source of `CPUA`/`DBAP`),
`0x166A` and `0x0743` bit 1 (the source of `0x07C4` bit 4) have no
`registers.yaml` entries, and the `0x851B` stub run is the gate on dating the
capture. All three are named as follow-ups in the walk's §9 rather than
answered here, and none of them is another repository's issue to answer.

## 8. The Memory Overclocking Menu is behind one `UniWillVariable` byte (2026-09-23)

**Result, confirmed live.** Setting `UniWillVariable.MemoryOverClockSwitch`
(offset 0x33) to 1 from Windows and rebooting makes a "Memory" entry appear
on the BIOS setup's Advanced page. It leads to Intel's full Memory
Overclocking Menu. The write:
`evidence/uefi/2026-09-23-MemoryOverClockSwitch-set.txt`, with before/after
dumps differing only at 0x33. The owner's report after the reboot:
`evidence/uefi/2026-09-23-memory-menu-observation.md`. The write tool is
`windows/tools/uniwill_set.py`, which backs up, changes one field, checks
the readback, and can restore. `uefi_var.py` stays read-only.

**Why it works, from the committed BIOS.** All of the following is
reproducible from `vendor/bios-1.09/BIOS_1.09.zip` with
`bios/tools/bios_extract.py`. That script produces the Setup IFR
(`bios/ifr/Setup.en-US.ifr.txt`) and Ghidra decompiles of the vendor
modules (`bios/decompiled/`). The module that matters is annotated in
`bios/decompiled/OemOcDxe.annotated.c`.

- The IFR has two routes to form `0x27B1` "Memory Overclocking Menu". One
  goes through Intel's own Advanced form `0x2718` → "OverClocking Performance
  Menu" (`0x27AA`) → "Memory". Form `0x2718` is referenced only from the stock
  root form `0x2710` and from a suppressed Ref, and it was not the Advanced
  page reached here. The other route is a vendor-added Ref "Memory" on the
  vendor Advanced form `0x2712`, which is the page setup displays. That Ref
  sits inside three conditions:
  - suppressed unless question `0xEC6` == 1, which is `Setup` offset
    **0x7D7**, the last byte of the 0x7D8-byte `Setup` store. It is a hidden
    numeric with no prompt;
  - suppressed if question `0x30B` == 0, which is `CpuSetup` offset 0x1B7,
    "OverClocking Feature". Its default is Enabled, both in the IFR and in
    the ROM's `StdDefaults` store (value 1);
  - suppressed and greyed out if `SystemAccess` == 1, i.e. in a
    user-password session.
- `Setup` is boot-services-only (§6), so the OS cannot set 0x7D7 directly.
  But `OemOcDxe` runs on every boot and, unless it takes the recovery path
  below, **copies `UniWillVariable[0x33]` into `Setup[0x7D7]`** (RVA 0x7A8).
  `UniWillVariable` is NV+BS+RT, so the OS can write it. That is the whole
  mechanism: the Control Center's memory-OC switch is also the BIOS menu's
  visibility bit.
- The menu itself stores into `SaSetup`: "Memory profile" at 0x134
  (Default / Custom / XMP1 / XMP2; the XMP choices are suppressed by
  `SaSetup[2]`, which reflects what the DIMMs' SPD offers), reference clock
  0x0C (133/100 MHz), ratio 0x0E (Auto, 3-31), QCLK odd ratio 0x0F, primary
  and secondary timings 0x10-0x23, "Realtime Memory Timing" 0x204, a
  "Turn Around Timing" subform, and **"Memory Voltage" at 0x03, a VDDQ
  override from 1.10 V to 1.65 V**. Whether the MRC on this i7-10875H (rated
  DDR4-2933) honours any of these, and whether the board can actually move
  VDDQ, has not been tested. The voltage knob is the one to leave alone
  until someone knows what the board's regulator does with it.

**Why Control Center has no working switch for it here.** The service
publishes `MEM_MemoryOverClockSupport` from `UniWillVariable[0x60]`
(`MyFanManager_RamFan1p5.cs`, `UpdateStatusToClient`). By its name, that is
the flag a client shows the toggle on. The UWP UI isn't decompiled in this
repo, so that last link is inferred. Live, 0x60 reads 0. The BIOS's own create-if-missing path in
`OemUniWillVariableDxe` initialises it to **1**, along with 0xFF in the
reserved bytes. The live variable has 0 in 0x60 and zeros in the reserved
bytes, so something rewrote the whole block after creation. Which writer
did that is not known. 0x60 was deliberately **left at 0** here. With it at
1, the service's `SetUserProfile()` calls
`SetMemoryOverClockSwitch(currentProfile.MEM.MemoryOverClockSwitch)`. It
runs from `Init()` and on every power-mode change, and it would put the
profile's saved 0 back. The
service's `DebugMode` registry value also forces the support flag to 1, but
the same block rewrites the SMAPC power table to PL1/PL2/PL4 = 120/120/165,
so it is not a safe way in. One caveat stands regardless: the service
caches the whole struct when it starts and writes the whole cached copy
back on any field change. A Control Center action taken before the next
boot can therefore revert 0x33.

**What else `OemOcDxe` does with the same switch.**
- **Overclocking recovery via the EC.** Before anything else it reads EC
  RAM 0x0741 with vendor EC commands `0xA3 07`, `0xA2 41`, `0xA4`, read port
  0x62. If bit 7 is set, it sets `CpuSetup[0x1B7]` ("OverClocking Feature")
  to 0 and `UniWillVariable.OverClockRecoveryFlag` (0x5C) to 1, then writes
  0x0741 back with bit 7 cleared (`0xA5`). On seeing that flag, the
  service (`DetectRecoveryFlagFromBiosVariable`) restores its own defaults
  and default fan tables, sets its default-notify flag, and clears the
  flag. With "OverClocking Feature" at 0 the
  "Memory" link is suppressed again, and only a Setup load-defaults (or the
  unreachable Intel page) turns it back on. The read-address/read/write
  meaning of `0xA2`-`0xA5` is inferred from use.
  `OemUniWillVariableDxe` uses the same sequence with low byte 0x40 to fill
  `ProjectID`, and EC 0x0740 is the confirmed `PROJECT_ID`, so the reading
  is consistent. It is not confirmed from the EC side. **Which EC code sets
  0x0741 bit 7, and on what condition (a failed POST? a watchdog?), is not
  known.** So this recovery path is not something to rely on yet. Bit 0 of
  the same byte is the known `AP_OEM` / "AP exist" bit (`registers.yaml`).
- **A GPIO write.** When the switch is 1 and "OverClocking Feature" is 1,
  on a CNL/CML-H PCH (it skips an LP one), it drives **GPP_B22**'s TX state
  high: PCR PID 0x6E, PadCfg DW0 at 0x8F0 bit 0. It does this only if the
  pad is host-owned, and it drops and restores the pad's TX lock through a
  P2SB sideband write (opcode 0x13). The embedded tables are Intel's
  `GPIO_GROUP_INFO` (group 1: PID 0x6E, PadCfg 0x790, 26 pads = GPP_B).
  Nothing in the module drives it low again when the switch is 0. What
  GPP_B22 is wired to on this board cannot be read from the BIOS. A DIMM
  voltage select would fit the name, but that is a guess, not a finding. It
  is observable, though: on Linux, `pinctrl-cannonlake` exposes GPP_B22's
  state under debugfs, so switch-0 vs switch-1 boots can be compared.
- **Core-voltage sync.** With `ApExistFlag` (0x5D) = 1 it copies the
  service's CPU core-voltage values into `CpuSetup`. "Core Voltage Offset"
  (0x1BD) and "Offset Prefix" (0x1BF) come from 0x3A or 0x64, chosen by
  `ICpuCoreVoltageOffsetRangeType` (0x66). "Core Voltage" (0x1C0) comes from
  0x34. It then rewrites the slider ranges 0x36 = 2000 and 0x3C = 100, which
  is why those two values are non-zero in every live dump.

**For Linux.** The switch is an ordinary runtime-writable UEFI variable. On
Linux it is `/sys/firmware/efi/efivars/UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593`
(a 4-byte attribute prefix, then the 180 bytes; the file is immutable
until `chattr -i`). So the same unlock needs no Windows at all. That route
has not been exercised; only the Windows write above has been.

**Open, and filed as follow-ups:** who sets EC 0x0741 bit 7; what GPP_B22
drives; who zeroes `MemoryOverClockSupport`; whether the menu's settings
take effect (a live test, starting with the XMP profile the DIMMs
advertise, never the voltage override first); and whether Intel's
Advanced form `0x2718` (with the CPU-side OverClocking Performance Menu)
can be reached without reflashing.

## 9. What the decompilers can and cannot do on this material (2026-09-23)

The Ghidra projects now exist for all three components, and building them
settled several questions that were assumptions before. These are
methodological results rather than findings about the hardware, and they are
recorded here because two of them are traps: a tool reported success, and
the output was worthless.

**Ghidra 12.1.3 does decompile this 8051 firmware.** The charge-target
routine at bank 0 `0xB1F0` comes out as recognisable C, and the project
holds 2,676 decompiled functions across the two banks, the common area and
the PD image (`ec/ghidra/README.md`, `ec/decompiled/index.csv`).

**But a raw 8051 import finds nothing at all.** Ghidra's 8051 SLEIGH has no
reset-vector concept, so import plus auto-analysis produces an *empty*
project — zero functions. Every function here is reached by seeding, and
how it was seeded is recorded per function in `ec/decompiled/index.csv`.
The first attempt at this work concluded that Ghidra could not decompile
8051 at all; that conclusion was wrong, and the cause is the next item.

**The decompiler can fail silently, and the failure looks like a result.**
Unpacking the Ghidra release with something that drops the exec bit (Python's
`zipfile` does) leaves the `decompile` and `sleigh` binaries under
`Ghidra/Features/Decompiler/os/linux_x86_64/` non-executable.
`DecompInterface.openProgram()` then returns false and `getLastMessage()`
is the **empty string**. From the
output that is indistinguishable from "this function will not decompile",
which is the same failure shape as the ConfuserEx anti-tamper trap in
`windows/antitamper/README.md` — and the first conclusion above was drawn
from exactly that. The exporters now raise it as a loud, specific failure,
and the build preflights the exec bit before starting a JVM. **Anyone
reading a decompile failure in this repository should rule this out before
concluding anything about the firmware.**

**Ghidra cannot usefully decompile the .NET assemblies.** It reports success
and emits `halt_baddata()`: `GCUService.dumped.exe` scores 400/400
"decompiled" against bodies containing `halt_baddata()` and "Unable to
resolve constructor". It does read .NET *method names* out of the metadata,
so the project is useful as a symbol and call-graph index, but the C is not
a decompilation and is not committed as one. `ilspycmd` is the tool for
managed code, and `windows/decompiled/v3.1.39.0/` already holds the fully
decrypted service. The encrypted original yields 8 functions against the
dump's 400+, which is the anti-tamper showing through the tool rather than
anything new about the anti-tamper.

**The UWP app ships a matching PDB that nobody had used.**
`vendor/control-center-3.9.18.0/GamingCenter3_Cross.UWP_3.9.18.0_x64.appxsym`
is a 144 MB `GamingCenter3_Cross.pdb` for the 27 MB native
`GamingCenter3_Cross.dll` inside the msixbundle. It matches, and Ghidra
reads full C++/WinRT type information out of it. It is slow — the
"PDB Function Internals" analyzer was still grinding past ten minutes, and
turning the analyzer off is what makes it usable. See
`windows/ghidra/native-binaries.csv`.

**The routine the charge-cap question turns on is invisible to a call
census.** `0xB158`, `charge_target_update`, has no `lcall` or `ljmp` to it
anywhere in the image: it is entered by `jb acc.1` from `0xB141` on XDATA
`0x0490` bit 1 (`ec/annotations/charge-target-derating.md`). A seeder built
from direct calls therefore omits the best-understood routine in the
firmware, and did. This is a general limit on any call-target census, and it
is why the annotation layer can also declare a function entry rather than
only annotate one.

**Two coverage numbers, and only one of them is coverage.** Bytes
disassembled is the honest figure; the sum of function body lengths is not,
because Ghidra's bodies overlap and the sum can exceed the image size. Both
are in `ec/ghidra/manifest.csv`, under `instruction_bytes` and `body_bytes`,
so a later reader cannot accidentally quote the second as the first.

**The BIOS holds 360 PE/TE modules; 12 had ever been decompiled.** There are
32 `Oem*` modules — the TongFang/Uniwill-authored set — and 20 had never
been touched, the largest being `OemServiceSmm` at 55 KB. Separately, the
Intel overclocking chain (`OverClockSmiHandler`, `OverclockInterface`,
`DxeOverClock`, `PeiOverClock`) had never been decompiled at all, and it is
the code behind the memory-overclocking menu §8 and issues #104/#115/#117/
#118/#119 are all working on. All 38 are decompiled now, 955 functions with
no failures; see `bios/README.md`.

**The 30-minute CI budget cannot hold a Ghidra rebuild**, so nothing in the
gates runs one. What runs on every commit is the cheap tier of
`.github/scripts/agent-gates.sh` — each tool's `--check` and `--self-test`,
which need no Ghidra and no network, plus a few structural checks that read
only committed text. The full end-to-end check against the hand reading in
`charge-target-derating.md` is opt-in
(`build_ec_decompile.py --self-test --oracle`). Two further opt-in steps live
behind `AGENT_GATES_DEEP=1` in `.github/scripts/agent-gates-deep.sh`; see §14
for what they are, what they cost, and what is lost while they are opt-in.

*(**Correction, 2026-09-23, §14b.** "The cheap half is each tool's `--check` and
`--self-test`" was true of the intent and not of one of the tools:
`decompile_native.py --check`'s listing parser matched **zero** lines of all
five committed Windows listings, because its regex capped addresses at 8 hex
digits and every x86-64 address there is 9. It had been reporting a pass over
a parse that had read nothing. The tier split that paragraph led to is real;
so is the reason it was needed, which is not the one given in issue #137 — see
§14's opening for which of that report's figures survive checking.)*

## 10. What the newly decompiled BIOS modules turned up (2026-09-23)

Decompiling the 26 vendor modules that had never been touched (BIOS §9)
answers one open question, corrects an assumption behind five others, and
leaves one loose. Each claim below is as-decompiled, and each is checkable
in the file cited.

**`PeiOverClock` is a protocol-registration stub, and it is not where the
overclocking is.** Issues #104, #115, #117, #118 and #119 all name it. The
module is 672 bytes; Ghidra decoded **53 bytes of it into 2 functions**, and
those 53 bytes are a PEIM that locates a protocol and registers an interface
(`bios/decompiled/PeiOverClock.c`, `bios/ghidra/index.csv`):

```c
int entry(void) { iVar1 = FUN_ffcfbb55(); if (-1 < iVar1) { iVar1 = 0; } return iVar1; }

void FUN_ffcfbb55(void) {
  ...
  (**(code **)(**(int **)(iStack_e + -4) + 0x18))(*(int **)(iStack_e + -4), &DAT_ffcfbbc0);
}
```

The `+ 0x18` vtable slot with a GUID argument is `InstallProtocolInterface`.
There is no overclocking logic in the module. The rest of its `.text` is
unreached CRT. Whatever the five issues are looking for, it is in
`DxeOverClock`, `OverClockSmiHandler`, `OverclockInterface` or
`OemOcDxe` — all four of which are now decompiled — and not here.

**`OemApControlDxe` is a third user of the same `0xA2`-`0xA5` EC command
sequence.** §8 reads that block as a vendor command
(`0xA3 07`, then `0xA2 lo`, then `0xA4`, `0xA5 val`) on the strength of
`OemOcDxe` and `OemUniWillVariableDxe`. `bios/decompiled/OemApControlDxe.c`
uses it a third time, verbatim:

```c
FUN_0000094c('b', 0xa3, 7);
FUN_0000094c('b', 0xa2, param_3);
FUN_0000094c('b', 0xa5, param_4);   /* and FUN_000007e8('b', 0xa4) */
```

`'b'` is the character `b`, the vendor's EC command prefix. Three
independent call sites for one sequence is stronger support for the reading
than two, and it is still not EC-side confirmation: nothing in the EC
firmware has been matched to this sequence, which is issue #114's question.

**`DxeOverClock`'s overclocking gate is real; what it gates on is not
settled.** The module fetches `CpuSetup` and then tests a byte of its own:

```c
lVar1 = (**(code **)(DAT_00002698 + 0x48))(u_CpuSetup_000025d0, &DAT_00002540,
                                          &DAT_00003460, &local_res10, &DAT_00002900);
if ((-1 < lVar1) && (DAT_00002ab7 != '\0')) { ... }
```

It is tempting to read `DAT_00002ab7` as a cached copy of
`CpuSetup[0x1B7]` — the "OverClocking Feature" byte that `OemOcDxe` clears on
EC-0x0741 recovery, and which would put the stock Advanced page behind the
same vendor byte as the vendor page's "Memory" link (§8). **That
identification is not established.** The literal `1B7` appears nowhere in
`DxeOverClock.c`; the only BIOS decompile that mentions it is `Setup.c`, the
HII module. A module static read after a `CpuSetup` fetch is suggestive and
nothing more — the byte could equally be a cached copy of some other offset,
or an independent flag. Settling it means finding what writes `0x2AB7`, which
is a question for the follow-up pass.

*(An earlier reading of this decompile named the gate `CpuSetup[0x1B7]`
directly. It is kept here rather than edited out because the reason it was
wrong is the point: a `CpuSetup` fetch followed by a static test reads like
a cached byte, and "reads like" is not "is".)*

## 11. Proving the disassembly is 1:1, and what it took (2026-09-23)

`ec/tools/verify_reassembly.py` re-encodes the committed EC listing with
`sdas8051` and compares the result to `ec/firmware/GMxMGxx_11.800`. Ghidra's
SLEIGH decodes; an assembler that never saw the firmware encodes; the firmware
arbitrates. **45,481 of 45,624 instructions re-encode to the exact bytes in
the image (99.69%), with no function in disagreement.** 2,576 of the 2,707
functions have every instruction verified; a further 73 have all but 143
between them. Reproduced unchanged on two SDCC versions (4.5.0 and 4.6.0,
`sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14`).

*(2,705 to 2,707 rows of the reassembly report, and 2,708 to 2,710 listings in
the index, with two seeded routines: issue #285's bank0 0xCC64, 58 instructions,
and issue #262's bank1 0xC1E7, 29 instructions, all re-encoded and 0 unchecked.
That is where 45,537 becomes 45,624 and 2,574 becomes 2,576. Both new rows in
`ec/ghidra/reassembly.csv` were measured with the runner's `sdas8051 02.00` and
the `assembler` column says so, because `05.50.4` is not reachable on a
GitHub-hosted runner; `ec/ghidra/README.md` says what a report holding two
assembler versions does and does not do.)*

*(A first pass reported 97.80% and 1,004 unchecked instructions. Four of the
seven opcodes in the "sdas8051 cannot express this" list were wrong: 0xC0 is
PUSH direct and not SETB bit, 0xC3 is CLR C and not CLR bit, 0x93 is MOVC
A,@A+PC and not MOVC A,bit, and 0x82 is ANL C,bit, which sdas8051 encodes
without a `/`. All four assemble correctly. So 712 of those 1,004 were never
gaps at all -- `clr CY` and `movc A, @A+DPTR` were the two commonest
instructions in the firmware and the report was calling both of them forms the
assembler refuses. The wrong number is left here rather than edited out
because the way it was found is the point: nothing failed, the check reported
zero mismatches throughout, and the only thing that surfaced it was printing
the composition of the "gaps" and looking at which instructions were in it.)*

The interesting part is not the number, it is the four bugs the check found in
*itself* before it got there. Each one produced a plausible-looking encoding
that was not the instruction in the firmware, and each would have been accepted
by a check that only asked "did the assembler run".

**1. Relative branches took an absolute address.** sdas8051's `jz` takes a raw
displacement. Handed `jz 0x0EC6` it emits the low byte of the address — a valid
byte for a completely different instruction. The listing's absolute target has
to be turned back into `target - (pc + size)` first. This alone accounted for
358 of the 928 original mismatches.

**2. Function bodies are not contiguous.** A 2-byte `jb` at `0x8058` is
followed by a 3-byte `lcall` at `0x805E`, with four bytes between them that
belong to no instruction in that function. sdas lays instructions out densely,
so without an `.org` at every gap it packs the `lcall` against the `jb` and
every later address shifts — 33 more mismatches, at addresses the decode never
claimed. The fix is to re-anchor, and to open a fresh `.area` rather than a
bare `.org` once the target moves outside the area (a bank-window function
reaches 32 KiB easily, and sdas answers a far `.org` with `.org in REL area`).

**3. Ghidra renders a direct address as the SFR it belongs to**, so direct
`0xE0` prints as `A`. sdas reads `A` as the accumulator: `88 E0` is
`MOV 0xE0,R0` in the firmware and came back as `E8`, `MOV R0,A`; `25 E0` is
`ADD A,0xE0` and came back as `add a,a`, which sdas rejects outright. The
decoder is not second-guessed — the operand is replaced by the literal byte
from the instruction's own encoding, which is what the decoder already
reported.

**4. `MOV direct,direct` (opcode 0x85) takes the source byte first.** `85 F0
00` is `MOV 0x00,0xF0`, not `MOV 0xF0,0x00`. Both decoders agree on this —
Ghidra's operand text and `disasm8051.py` — and the firmware confirms it. I had
the byte order backwards twice, which is the point: the check disagreed with
me, and two independent decoders plus the image settled it.

**A listing format that could not be parsed unambiguously.** The byte column
was objdump's shape — variable width, mnemonic at whatever column that left
it — and the 8051 has a reserved one-byte instruction the SLEIGH spells
`da A`. `da` is two hex digits, so

    D438  d4  da  A

reads equally as the one-byte instruction `d4` with mnemonic `da`, which is
what it is, and the two-byte instruction `d4 da` with mnemonic `A`, which it
is not. Five instructions in bank 0 are affected. The byte column is now
always three slots with `-` for a missing byte, and `-` is not a hex digit, so
the mnemonic cannot run into it.

It was found by a check that had not existed until this work: comparing every
byte of every committed listing against the firmware image, which needs no
assembler and therefore covers the instructions sdas8051 cannot express. The
first version of that check reported *zero* disagreements while
parsing 30% of each file, because the listings were the old format and the
parser the new one — so it now counts the lines beginning with an address and
fails if the parser does not get all of them. A parser that reads a third of a
file and finds nothing wrong in it is worse than one that reads none, because
it reports a pass.

**What sdas8051 cannot express, counted rather than skipped.** 143
instructions use forms it rejects, and the count means little on its own: 74
`AJMP`, 36 `ACALL`, 19 `MOV bit,C`, 13 `CPL bit` and one `DJNZ A`. `AJMP` and
`ACALL` are gaps for a different reason than the other three — sdas encodes
them differently from the 8051 manual (at PC `0x8044` the firmware and both
decoders agree `81 5D` is `ajmp 0x845D`; sdas emits `84 5D`) — and they are 110
of the 143 between them. Every one of these is named in the source rather than
filtered silently, because a filter that quietly drops a fraction of a percent
of the instruction stream turns a measured number into a flattering one. *(`SETB
bit` and `MOVC A,bit` were in this list on the first pass and are not gaps; the
correction and its numbers are in the italic paragraph above, and §14g records
the removal of that list from this file's forward text. Three further forms the
tool refuses are not in the 143 at all — `CLR bit`, `CJNE` on a direct address,
and the carry-with-immediate forms — because `BIT_UNSUPPORTED`, `GAP_FORMS` and
the `CJNE` rule in `to_sdas()` are the assembler's vocabulary rather than this
firmware's, and this image contains none of the three. §14g records the
correction, and how the composition was measured.)*

**Correction, 2026-09-23 (issue #157).** The 1,004 and the 2.2% in the
paragraph above are the retracted first-pass figures, left visible because the
paragraph above retracts them and a reader should be able to see what was
withdrawn. The settled numbers are **143 instructions, 0.31%**, and they are the
ones `reassembly.csv` carries. The form list in that paragraph is stale in the
same way and for the same reason: `SETB bit`, `MOVC A,bit` and `CLR bit` are
three of the four entries the parenthetical at the top of this section records
as having been misread — 0xC0 is PUSH direct, 0x93 is MOVC A,@A+PC, and 0xC3
is CLR C, so the `CLR bit` and `MOVC A,bit` there were never gaps at all.
(`MOV C,bit` and `MOV bit,C` are a different pair: 0xA2 assembles fine, while
0x92 is a real gap, and the paragraph above does not distinguish them.) The 143
are `MOV bit,C`, `CPL bit` and `DJNZ A`, plus `AJMP`/`ACALL` for the separate
reason given. `verify_reassembly.py` refuses three further forms that this
firmware happens not to contain — 0xC1 `CLR bit`, `CJNE` on a direct address
and the carry-with-immediate forms — so those are rules with no instance rather
than part of the 143. The 143 is unaffected by which SDCC build is on PATH —
§14g measures it against a second one and finds the same 143 on all 2,705 rows.

*(The 1,004 and the enumeration above are the first pass's, corrected in the
parenthetical earlier in this section. The current figure is **143** in **five**
forms, and they are not this list: `ajmp` and `acall` are 110 of the 143,
whereas `CLR bit`, `SETB bit`, `MOVC A,bit` and the carry-with-immediate forms
here are in none of it. §11a has the measured composition. Kept as written
because this paragraph is the shape of the mistake — a plausible list,
carried forward, wrong in both directions, and caught by nothing except
printing what is actually in the set.)*

**The claim this does not make.** That the C recompiles. Keil C51 generated
these bytes; SDCC does not emit Keil's code generation, and no amount of
annotation changes that. The 1:1 property here is that the committed
*disassembly* regenerates the binary, and the readable C sits on top of it
with a checkable correspondence. See `ghidra/README.md`.

### 11a. The 143 the re-encode could not reach, read by a second decoder (2026-09-23, issue #151)

The re-encode above has one hole, and it is the hole the `partial` and
`assembler-gap` outcomes name on their face: 143 instructions in five forms
`sdas8051` cannot express are excluded from it, and were read by no check at
all. `verify_reassembly.check_listing_bytes()` reaches them — it covers all
45,624 and needs no assembler — but a byte is not a mnemonic. A listing whose
bytes are right and whose text is wrong passes the byte check and fails the
re-encode, and for these 143 there was no re-encode to fail.

`ec/tools/verify_gap_text.py` closes it by asking a second decoder.
`ec/tools/disasm8051.py` shares no code with Ghidra's SLEIGH, which is the
same property that makes the 45,481 meaningful. For every instruction
`verify_reassembly.to_sdas()` declines, it decodes the instruction from the
firmware image at that instruction's own runtime address and compares the
result to the listing's text. **All 143 agree**, recorded individually in
`ec/ghidra/gap-text-check.csv` with both texts, both canonical forms, the
reason, and the verdict.

**The evidence is weaker than the re-encode's, and saying so is the point.**
The re-encode is constructive: an independent tool produces bytes and the
firmware arbitrates. This is comparative: two decoders, no code in common,
read the same byte column. The bytes were already settled by the byte check;
what is agreed here is the *text*. So a `disagree` would be a text error with a
known-correct answer, and an `agree` is two decoders having said the same
thing about bytes that are not in question. **The claim stays 45,481 of 45,624
(99.69%).** What changes is coverage: all 45,624 instructions are now read by
an independent check, and adding the two into a single 100% would assert
something neither establishes.

**Two decoders rarely spell an instruction the same way,** so the comparison
needs a canonical form, and the interesting part is what it may *not* fold.
Folded: case, whitespace, a bit operand's rendering (`psw.5` ≡ `0xd5` ≡
`acc.4`), a direct operand's (`A` ≡ `0xe0`). Not folded: the mnemonic, the bit
number, the direct byte, the immediate, a register, a branch's absolute target.
The operand's class is read from the opcode, never from the operand text,
because `clr 0x8e` is both CLR direct and CLR bit depending on the byte in
front of it — the same reason `BIT_UNSUPPORTED` is keyed by opcode. One
assertion carries the weight: `cpl 0xd5` against `cpl 0xe4` must come out a
**disagreement**, because a canonicaliser that folded the mnemonic would
report all 143 as agreeing and mean nothing by it.

**A `db` is never an agreement.** `disasm8051.py`'s mnemonic table is partial
by design, so a comparison against one could only match vacuously — and it did.
`mnemonic()` had no case for opcode `0x92`, so `mov 0xd5,CY` decoded as
`db 0x92` and 19 of the 143 would have "agreed" with a hole. The verdict for
a `db` on either side is `undecodable`, and `--self-test` asserts it.

**The set had never been written down correctly, in either direction.**
`ec/ghidra/README.md` named the 143 as `MOV bit,C`, `CPL bit`, `CLR bit`,
`CJNE` on a direct address, `DJNZ A` and the carry-with-immediate forms: it
omits `ajmp`/`acall`, which are **110 of the 143**, and names four forms that
are not in the measured set. Those four were residue of §11's retracted first
pass, copied forward when the number was fixed and the prose was not — the
same transcription this section describes above, one layer down. The corrected
figure is `ajmp` 74, `acall` 36, `mov <bit>,CY` 19, `cpl <bit>` 13, `djnz A`
1: **five forms**. Both the wrong list and the retracted 1,004 are corrected in
place in `ec/ghidra/README.md` rather than edited out, so they stay findable.

So the tool **recomputes** the set from `to_sdas()` on every run and never
carries a list — and every declined instruction records *which* predicate
declined it, with `--check` failing on a reason that has no cross-decode
handler. A sixth form cannot join the set silently. That is §11's failure
turned into a check, and it is the general form of the lesson: the first pass's
four wrong opcodes were found by nothing failing, only by printing the
composition of the gaps and reading it.

**The 84 rows are not the 73 `partial` ones.** 73 of them are; the other **11
are `assembler-gap` rows that also carry unchecked instructions**, which the
outcomes table does not say. Over all 84 the first unchecked instruction is
`ajmp` 43, `acall` 19, `mov` 13, `cpl` 8, `djnz` 1; over the 73 `partial` rows
alone it is 36 / 18 / 13 / 5 / 1. By program: `common` 62, `pd` 32, `bank0` 27,
`bank1` 22.

**Three things came out of the work that are not about the 143**, and all three
are holes rather than confirmations:

- **`disasm8051.py` mis-rendered all 180 committed `CLR direct` instructions.**
  `0xC2` was grouped with the bit forms, so its byte operand went through
  `bit_name()`: `clr 0x7f` printed as `clr 0x2f.7`, which claims to clear bit 7
  of internal RAM 0x2F rather than all eight bits of 0x7F — a different
  instruction, 180 times. Found by the oracle entry that keeps `0xC1` and
  `0xC2` apart, which is the only reason the two are distinguishable at all.
  None of the 180 is in the 143 (`0xC2` is a form `sdas8051` expresses, so they
  are inside the 45,481), which is exactly why nothing had noticed.
- **`0xA0`/`0xB0` are unresolved and this repository cannot resolve them.**
  Ghidra's SLEIGH, r2 and `sdas8051` all put `ORL C,/bit` at `0xA0` and `ANL
  C,/bit` at `0xB0`; the MCS-51 manual as reproduced in common references has
  them the other way round. Three tools agreeing is why `disasm8051.py` follows
  them, and none of them arbitrating the other two is why that is recorded
  rather than settled. All 12 occurrences are inside the 45,481, and the
  re-encode passes on them **because the decoder and the assembler agree, not
  because either is right** — the one shape of hole this tool structurally
  cannot see.
- **`0xC1` (`CLR bit`) is a latent hole, not a live one.** It matches none of
  the 143 and `disasm8051.py` can now decode it, but `sdas8051` assembles it as
  `CLR direct` — same length, no error — so a future export containing one would
  be excluded from the re-encode and read by nothing. It has no committed
  instance, so its encoding is stated in `--self-test` from the manual rather
  than transcribed from the image.

**What this does not do, stated so it is not assumed.** No register, no
`registers.yaml` status, no XDATA symbol, no function name, no Ghidra project
and no decompiled `.c` is touched: nothing in this issue bears on the
firmware's *behaviour*, only on whether a committed text says what its bytes
say. No Ghidra run was needed. And **nothing runs this per commit** — by cost
and by kind the new `--check` belongs in the cheap tier, but
`.github/scripts/agent-gates.sh` is a template-copied file and the pipeline
token has no `workflow` scope. The one-line `case` arm is named in
`ec/ghidra/README.md`; until a human lands it, the committed verdicts can go
stale in an otherwise-green commit, the same shape §14e records for the deep
tier.

## 12. The common-area de-duplication was deleting a PD function (2026-09-23)

The EC export groups a common-area function once, under `common`, when both
bank programs carry it identically. The grouping collected "everything that is
not bank0" as the rows to drop, and the PD image is a program too: a PD
function at `0x0012` shared an address, a name and a size with the EC's
`0x0012`, so it was folded into the common group and `pd/0012.c` and
`pd/0012.asm` were deleted with it.

**It is a real loss, not a cosmetic one.** The PD image is a separate 64 KiB
program with its own address space, its own vector table and its own XDATA map
(`ec/README.md`; `ec/annotations/lightbar-bat-flow.md` §2), so its `0x0012` is
unrelated to the EC's. Folding them together asserts an identity that does not
exist, and one PD function went missing from the tree.

**Every gate still passed**, and the reason is the part worth keeping: the
index row and the files it named were deleted *together*, so every
file-existence check still held. A row that is gone cannot point at a file that
is gone. Nothing in the pipeline was comparing what the exporter *reported*
against what the pipeline *kept*.

Two things now prevent it, and both are the general shape rather than the one
instance:

- the de-duplication pairs `bank0` with `bank1` and with nothing else;
- `--check` asserts that every function the manifest records from the export is
  still in the index. The manifest is what breaks the symmetry, because it
  carries the count the exporter measured before anything was de-duplicated.

**The same bug was also suppressing grouping it should have allowed.** The
condition guarding the fold asked whether *every* non-bank0 row matched bank0,
and the PD image's row was one of those. So a PD function at a common-area
address whose size differed from the EC's vetoed the fold entirely, and twelve
functions that both bank programs carry identically — `0x0000`, `0x0003`,
`0x000B`, `0x0013`, `0x001B`, `0x0023`, `0x0C7A`, `0x0EF3`, `0x10F1`,
`0x11C2`, `0x383A` — sat in `bank0/` and `bank1/` as two near-duplicates each
instead of one entry under `common/`. With the pairing narrowed to
bank0-versus-bank1 they group correctly, and the diff is 22 files moving to
`common/`.

Worth noting what the two sides of that address now show, because it is the
whole argument: the common `0x0000` is an 18-line thunk and the PD's is a
106-line `c_startup_idata_clear`. Same address, unrelated code, and before the
fix one of them was deleted for looking like the other.

`--self-test` reproduces the original failure on synthetic rows, and fails if
the pairing is widened again.

## 13. What is still not assembled (2026-09-23)

The three components have committed projects and decompiled output. This is the
part that is **not** done, measured rather than estimated, because a plan that
counts the remaining work from memory is how the earlier "~320 missing modules"
figure in the build plan got there and turned out to be wrong.

**The BIOS ROM, beyond the 38 vendor modules.** Unknown, and deliberately not
guessed. `uefiextract rom all` is the only way to enumerate it and the tool
measures that command at anywhere from 1.7 s to 49 min on this machine, so
`bios_extract.py` runs it only for `--mode rebuild-project`. The ROM dumps
cached from earlier runs are *partial* — 65 modules with an image body, but
`OemOcDxe`, `Setup`, `DxeOverClock` and `EcPs2Kbd` are all absent from them,
so the 65 is not a superset of the 38 and the difference is not 27. Getting
the real number means one full dump; it has not been run. What the cached dumps
do show is that the PEI/SMM material worth having is there: `S3Resume2Pei`,
`PiSmmCommunicationPei`, `RstSecPeim`, `TrustedDeviceSetupApp` and a TPM
policy module, none decompiled.

**The Windows native stack of v3.1.6.0.** Four binaries are not in the Ghidra
project: `NVControlSetting.dll`, `GPUInfoDLL.dll`, `DiskInfo64.dll` and
Microsoft's `devcon.exe`. All plain x86-64 with no anti-tamper, so they
decompile with the existing path — see
`windows/decompiled/v3.1.6.0/README.md`, which also records the more useful
result from the same extraction: the native EC-facing stack is byte-identical
between 3.1.6.0 and 3.9.18.0, so the difference between the two versions is
not in the driver, the driver wrapper or the firmware-bridge library.

**The packed managed services.** `GCUService.exe` at 3.1.6.0 and 3.9.18.0 both
encrypt their method bodies. `windows/tools/dotnet_dump.py` reads them out of a
*running* process, so there is no static route and this pipeline has neither
Windows nor the service running. The 3.9.18.0 dump is committed because a
machine with Windows produced it; producing the 3.1.6.0 one is the deliverable
for whoever has the hardware, and the command is the tool's `--help`.

**The 143 EC instructions sdas8051 cannot encode** — 0.31% of the instruction
stream. These are now read by a check: `ec/tools/verify_gap_text.py`
cross-decodes every one of them with `disasm8051.py`, which shares no code
with Ghidra's SLEIGH, and records the verdict per instruction in
`ec/ghidra/gap-text-check.csv`. All 143 agree. See §11a.

The set is **five forms, not the seven the prose here used to name**: `ajmp`
(74), `acall` (36), `mov <bit>,CY` (19), `cpl <bit>` (13) and one `djnz A`.
`ajmp`/`acall` are 110 of the 143 and were missing from every written account
of this set; `CLR bit`, `CJNE` on a direct address and the carry-with-immediate
forms are in none of it.

**The 1:1 claim is still 45,481 of 45,624 (99.69%), and this work does not
make it 100%.** `sdas8051` still cannot express those five forms and no tool
has changed that. What changed is coverage: every instruction in the committed
listing is now read by an independent check, the 143 by decoder agreement and
the 45,481 by re-encode. Those are not the same kind of evidence — the
re-encode is constructive, with the firmware arbitrating, while the cross-decode
is two decoders agreeing about text over bytes the byte check has already
settled — and adding them into one percentage would say something neither
establishes. The 1:1 claim would need a single check covering all 45,624, and
the honest way to get one is an encoder whose oracle is r2 or the firmware
bytes, not `sdas8051` agreeing with an agent's own table. Writing such an
encoder is still not started; §11 is the record of what happens when a gap list
is hand-built instead.

**Everything about the hardware.** No live test has been run in any of this.

## 14. The gate that was reading nothing, and reading it 10,000 times (2026-09-23, issue #137)

Issue #137 reported that `.github/scripts/agent-gates.sh` had grown past the
point where it is a quick check, and attributed the cost to its coverage checks
re-deriving coverage from the artefacts: "it re-hashes the 387 MB-scale Windows
project inputs and re-reads a **56 MB** decompiled C". The premise is right. Two
of the attributions are not, and the difference is worth recording, because
both read as measured and are not.

Checked against the code as it stood:

- **The 56 MB `.c` was never read.** The old `--check` touched
  `windows/decompiled/native/*.c` only through `os.listdir` and `os.path.isfile`
  — names, not contents. What *was* re-read per run was inside the committed
  zip: the inner `.msix` was read whole (17,009,272 bytes) once per msix target,
  three times, and each member then read whole on top of that — 51,027,816
  bytes of bundle plus 27,090,528 for `GamingCenter3_Cross.dll` alone. Real
  waste, and worth fixing, but not the file the report named, and small next to
  §14a.
- **50,887 instructions across 955 BIOS listings cost 0.33 s**, so that half of
  the cost attribution needs no correction at all. It was never the problem.

All timings below are this repository's own, taken on a GitHub-hosted runner on
2026-09-23 with a warm page cache, each step on its own. Where a figure is
someone else's it says so.

### 14a. The 955 BIOS listings cost 0.33 s. The 35 MB Windows listing cost the gate its wall clock

`bios_extract.py --check`, which parses all 50,887 instructions across 955
listings, measures **0.33 s**. It was never the problem. Its index names one
file per function — 955 rows, 955 distinct files — so there is nothing to
deduplicate.

`windows/ghidra/listing-index.csv` is 10,664 rows naming **5** distinct
`out_file` values, because this tool exports per program: one `.c` and one
`.asm` per binary, with a row per function pointing at it.
`decompile_native.py --check` iterated *rows*, so `ACPIDriverDll.asm`
(35,324,763 bytes), which 10,141 of those rows name, was opened and
regex-scanned 10,141 times — **358.2 GB** of text to re-derive what one pass
already knows. It now iterates distinct paths, and reports the distinct count
rather than the row count, so the number in the output says what was read.

**A listing index is a function index with a file column, and the row count is
not a file count.** That is worth knowing before writing a loop over one.

### 14b. The parse was vacuous: the regex matched zero lines in all five listings

`windows/tools/decompile_native.py` selected disassembly lines with
`^[0-9A-Fa-f]{4,8}\s+\S` — an address of 4 to 8 hex digits. Every image here
is x86-64, and `TongFang.addrKey()` only strips the `0x` and the address-space
prefix, so every address it emits is **9** digits (`140001000`).

Measured across the five committed listings:

| listing | address lines | widths present | matched by `{4,8}` |
|---|---|---|---|
| `ACPIDriver.asm` | 2,875 | 9 | **0** |
| `ACPIDriverDll.asm` | 473,710 | 9 | **0** |
| `UEFI_Firmware.asm` | 17,827 | 9 | **0** |
| `clrcompression.asm` | 8,239 | 9 | **0** |
| `GC3_launcher.asm` | 1 | 9 | **0** |

So `lines` was empty, `len(got) == len(lines)` held trivially, and `--check`
reported a pass over 358 GB of scanning in which it matched nothing. The
ceiling is now `{4,16}` — 16 is Ghidra's own widest address, so it is the
format's ceiling rather than a number fitted to today's five files. With it,
`--check` parses **502,652 instructions** where it previously parsed 0.

This is the failure the check's own comment warns about, and it is worth
keeping the sentence: *"a parser that reads a fraction of a file and finds
nothing wrong in it reports a pass."* A check that cannot fail is not a slow
check, it is an absent one that costs the most.

The EC and BIOS copies of the regex address 4-digit 8055 keys and 8-digit RVA
keys respectively, and are correct as written. They are separate constants in
separate tools and were not touched.

### 14c. The gate was red on `main` for three reasons, not one

The plan this work came from recorded that the gate exits non-zero on `main`,
and attributed it to a single stale assertion. It is three, in two files, and
none of them is fixed by making the gate faster — the point being that a gate
which has been red long enough stops being read as a gate at all.

1. **`decompile_native.py --self-test` asserted a 16-column manifest header.**
   `MANIFEST_HEADER` has 17 entries and the committed `manifest.csv` has 17:
   `notes` was added for the `not-in-project` row and the assertion was not
   updated. The assertion was the thing that was wrong; it now asserts 17 and
   the reason is in a comment beside it.
2. **`--check` failed "every decompilation has a listing beside it" on
   `GamingCenter3_Cross.c`.** True, and unfixable: that program is in
   `PROJECT_EXCLUDED` because its Ghidra database is 337 MB, so its `.asm`
   cannot be re-exported. The check now names the exception and prints it on
   every run rather than folding it into a pass.
3. **The "documented retention" carve-out never matched anything.** The comment
   above it says a `.c` for a program in `PROJECT_EXCLUDED` is accounted for by
   name, and the code built that name as `GamingCenter3_Cross.dll.c` — the
   binary's file name plus `.c`. The exporter writes the file under the
   **export label**, `GamingCenter3_Cross.c`. So the carve-out named a file
   nothing in the repository can ever write, and the check it was there to
   soften was red anyway.

Failure 2 and failure 3 are the same event seen from two sides: a retention
decision was made, one check learned about it, and the other was given a
carve-out whose name was wrong. The lesson is the boring one — a carve-out that
is never exercised is not a carve-out, and neither is a check that cannot fail.

### 14d. The EC self-test's 18 s was a redundant read, not the cross-decoder

Going in, the expectation was that `build_ec_decompile.py --self-test`'s cost
was `check_cross_decoder_agreement()`, which spawns `disasm8051.py` per sampled
function. Measured here it is **0.13 s**, and the self-test was **18.8 s**.

The 18.8 s was one line. A set comprehension sat *inside* the generator
expression of the "no EC bank or common annotation is seeded into the PD
program" check, so the set of PD-scope annotation addresses was rebuilt from
the whole annotations CSV once per seed row — 1,790 times, 22 s of
`csv.DictReader`. The EC-side set three lines above it had been hoisted
already; only the PD one had not. Hoisting both took the self-test to
**0.15 s**.

So the cross-decoder comparison is now behind `--cross-decoder` and runs in the
deep tier, but that is a statement about **where advisory output belongs**, not
about seconds: it is 0.13 s, it prints, and its result cannot fail the run in
either direction, which its own docstring has said all along.

**The generalisable half of this section is §14a and §14d together: two of the
three slow things were a loop over the wrong collection, and profiling found
them in a minute where reading the issue did not.** The cost was in the shape
of the code, not in the amount of work it was supposed to do.

**The comparison itself was moved, widened and recorded after this was
written.** Its 0.13 s was four hand-typed functions out of 2,710, two of which
compared nothing at all; the sample is now 1,920 functions derived from the
committed annotations, it prints its denominator, and its outcome is committed
to `ec/ghidra/cross-decoder.csv` and ratcheted by `--check` on every commit.
**§14i has the measured figures, the correction to the "40 straight-line
instruction(s)" this comparison used to print, and what the sample found.**

### 14e. What the split is, and what it costs while the deep tier is opt-in

The gate is now two scripts and one environment variable.
`.github/scripts/agent-gates.sh` is the cheap tier; `AGENT_GATES_DEEP=1` hands
off to `.github/scripts/agent-gates-deep.sh`, which re-runs the cheap tier
first and then adds the `sdas8051` re-encode and the cross-decoder
comparison. So `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh` is a single
command that checks everything, and the cheap tier prints that command's name on
every run whether it passed or failed.

| | before | after |
|---|---|---|
| whole gate, cheap tier | did not finish in 8 min 13 s (killed; all of it inside `decompile_native.py --check`) | **5.9 s** (5.88 / 5.85 / 5.89 over three runs) |
| `decompile_native.py --check` | did not finish in 8 min 13 s | **1.72 s** |
| `build_ec_decompile.py --self-test` | 18.77 s | **0.15 s** (0.27 s with `--cross-decoder`) |
| whole gate, deep tier (superset) | n/a | **9.53 s** |
| `verify_reassembly.py --check` | 0.45 s | 0.45 s (unchanged) |
| `bios_extract.py --check` | 0.33 s | 0.33 s (unchanged) |
| `sdas8051` re-encode alone | issue #137's figure: ~90 s | **4 s** here, `--jobs 4` |

**A later pair, and why the two differ (2026-09-24, issue #140).** The table
above was measured on 2026-09-23 and this change adds the cross-decoder
recomputation to both per-commit runs, so the "after" column there no longer
holds. Rather than overwrite a dated measurement, both halves were re-taken on
one runner, warm page cache, three runs each, against the pre-change file: the
table's own figures are from a different day's runner, and the pair below is
the before-and-after this change can be judged on. `--self-test` 0.42 s →
**0.59 s**, `--check` 0.22 s → **0.34 s**, `--self-test --cross-decoder` 0.55 s
→ **0.72 s**, whole cheap tier **9.6 s**. The ~0.13 s is the cross-decoder
comparison over 1,920 sampled functions, which §14i measures in full — and
which is a *cheaper* comparison than the four-function one it replaced, because
the per-function subprocess and the per-function full-index re-read are gone.

The deep tier is cheap **on this runner**; the 90 s is the issue reporter's
figure and the two are not the same measurement. What is deferred does not
change with the machine: it changes with whether anyone runs it.

**The deferral is a real reduction in what CI checks on every commit, and it is
not free.** The `sdas8051` re-encode is the strongest check the EC has — an
independent assembler encoding the committed listing back to bytes, which is
the difference between checking the bytes and checking the claim about them.
It no longer runs per commit, and **nothing in `.github/workflows/` runs it on
any schedule**, because the pipeline token has no `workflow` scope. The
schedule is prepared instead: `docs/ci/agent-gates-deep-schedule.yml` is the
workflow, ready to be copied into `.github/workflows/` by a human, and
`docs/agent-pipeline.md` records the intent so a re-copy of the template, or
whoever wires it, picks it up. Until that happens the coverage is opt-in and
off.

**What the split did open, and what closes it (2026-09-23, issue #139).** The
hole #138 left was that the two per-commit checks — the byte check and the
report/index check — are content-blind to a listing's *text*. A mnemonic or
operand edited in a `.asm` with a correct byte column passed both, because a
mnemonic is not a byte and nothing re-derived the report. The fix is a
`listing_digest` column in `ec/ghidra/reassembly.csv`, a 64-bit hash of each
listing's parsed instruction stream, compared by `verify_reassembly.py --check`
on every commit. Any of the 2,705 rows' text could be edited that way before
the change and every per-commit check would still have passed; now one of them
edited that way fails the cheap tier, with no assembler anywhere in the run.

So per-commit coverage **detects** listing-text drift where it previously
detected nothing. It still does not **verify** it: a digest that agrees means
the text has not moved since the report was measured, not that the text is
right, and a wrong mnemonic committed together with a re-reported digest is
caught by nothing automated here. Detecting a change is not verifying it, so
until the schedule lands **per-commit coverage remains less than before the
split** — smaller in scope, but not the re-encode. The cheap tier now catches
the edit a byte column cannot see; the tier that would say whether the edit was
an improvement still has to be asked for.

**What per-commit coverage gained, and what it still has not (2026-09-23, issue
#149).** The `listing_digest` column shipped with known answers.
`verify_reassembly.py --self-test` asserts the digest's canonical form, the
`compare_digests()` failure paths, `GAP_FORMS` and `BIT_UNSUPPORTED` —
including what the column exists to catch, a changed mnemonic under an
unchanged byte column, and a changed byte column — and until this change they
had no automated path at all. The cheap tier's case ran `--check` alone, and
the deep tier, the only other thing that runs the tool, invokes it as
`--work … --jobs 4` with no `--self-test`. So this was never a tier holding
them back pending the schedule: the deep tier did not cover them either,
scheduled or not, and there was no schedule to wait for. The case now runs
`--check && --self-test`, and they are per commit, at **0.04 s** over five runs
with a warm page cache here (0.22 s on the first run of a session, before
anything is cached) against the 5.9 s baseline in the table above.

The assertions are written before the self-test's no-assembler early exit, so
a runner without `sdas8051` reaches them and a failure there is still a red
gate. A runner *with* one assembles a four-instruction fixture of the
self-test's own after them — part of that 0.04 s, not the re-encode, and not
something the verdict turns on.

The scope is worth keeping straight, because it is easy to read this as
closing more than it does. These guard the **tool**, not the tree: that the
digest means what the column says it means, and that the comparison rejects
what it should. Detecting a listing-text edit is still the digest's job, still
per commit, and still not verification. Verifying the text is still the
re-encode's; it still does not run per commit and it still has no schedule.

One premise of the paragraph above was itself unestablished when it was
written, and is settled in §14f. The digests were taken without a re-encoding,
so whether they were of the listings the last full `--report` measured was an
open question, and "a digest that agrees means the text has not moved" rests on
the answer. It was the empty set — no `ec/decompiled/**/*.asm` text moved
between `08b72e2` and `a56b3bb` — so the column is anchored, and only the
correctness half of that paragraph is still open.

What was **not** deferred, deliberately: every check that opens a `.c` or an
`.asm`, the `DECOMPILER UNAVAILABLE` walks, the BIOS listing parse, the EC byte
check. Together those are about 1.2 s, and deferring them would mean a
silently-failed decompile or byte drift could land on `main` to save a second —
which is the "gate weakened rather than satisfied" outcome, not a satisfied
one. The always-on tier also **gained** structural checks: duplicate
`(program, addr)` keys, `strict=True` CSV parsing so a quoting error fails
instead of silently shortening a row, the manifest `mode:` vocabulary, and the
manifest's recorded function count against both indexes' row counts.

No wall-clock budget was added to the gate. The elapsed-seconds line is
printed, never asserted: a timing assertion in a gate is the flaky check that
gets switched off, and deleting the assertion would be the only fix anyone
reached for.

### 14f. The `listing_digest` migration is anchored: no listing text moved under it (2026-09-23, issue #150)

§14e added the column and, in doing so, left one question open without saying
it was open. `add_digest_column()` wrote each row's digest from the listing on
disk **without re-encoding**, which is the one shape that defeats the column: had
a listing's text been edited between the last full `--report` and the migration,
the migration would have digested the *edited* text, `--check` would recompute
that same digest and agree, and the detector would be re-armed on text nobody
re-encoded. The guard refuses a *second* run; it cannot audit the first. ".asm
files say do not edit" is a convention, and a convention is not evidence.

**It was the empty set.** The last commit to write a non-digest cell of
`ec/ghidra/reassembly.csv` is `08b72e2` ("1,769 named EC functions, and the
disassembly they are checked against", 2026-09-23), which by its own message is
the full `--report`: 45,394 of 45,537 instructions re-encoding to the firmware
bytes through `sdas8051`, 2,574 of 2,705 rows fully checked. `a56b3bb` is the
migration, and it changed nothing else in the file — parsed with
`csv.DictReader` and the `listing_digest` field dropped, all 2,705 rows are
identical to `08b72e2`'s and the header is the old one, so the two differ by the
column and by nothing beneath it. `08b72e2` therefore carries the anchors: 2,705
rows, `sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14` on every one, 45,394 checked +
143 unchecked, 2,574 `match` / 73 `partial` / 58 `assembler-gap`.

On a full clone, the comparison is two commands:

```
$ git diff --name-only 08b72e2 a56b3bb -- 'ec/decompiled/**/*.asm'
$ # no output
$ git log --name-only --format= 08b72e2..a56b3bb -- ec/decompiled
ec/decompiled/bank0/0EA2.c
```

**The empty output is a measurement, not a pathspec that quietly matches
nothing**, and that is worth showing rather than asserting: the same pathspec
returns all 2,705 listings over `8c7985e..08b72e2`, the window in which they
were last written, and two other spellings of it return zero here too. The one
`ec/decompiled` change the window does contain is `bank0/0EA2.c` in `cd3c7b0`, a
decompiled C export; the digest is over the parsed `.asm` instruction stream
(`digest_of()`), so a `.c` re-export cannot move one.

So the committed digests are of the listings the last full `--report` measured.
**What this does not establish is anything about those listings being right.**
The digests were still taken without a re-encode, so they attest to the measured
text and not to its correctness, and the paragraph in §14e above — a digest that
agrees means the text has not moved, not that the text is right — is unchanged
by any of this. What is closed is one instance of a question a future migration
still has to answer for itself, because the guard stops a second run and not the
first. The caveat in `ec/ghidra/README.md` is narrowed to that; it is not
deleted, and neither is this section's answer mistaken for the re-encode.

**The method is now a command** (2026-09-23, issue #159). The three commands
and the `csv.DictReader` comparison above were hand-run, and the next migration
will have to answer the same question; `ec/tools/verify_reassembly.py
--verify-provenance` takes the two revisions and runs all of it — the empty
`.asm` diff, the comparison with `listing_digest` dropped, and the positive
control over the window that last wrote the listings, so the empty can never
again be read as a pathspec matching nothing:

```
$ python3 ec/tools/verify_reassembly.py --verify-provenance \
      --base 08b72e2 --migration a56b3bb --listings-from 8c7985e
  revisions: listings written 8c7985e..08b72e2, migration 08b72e2..a56b3bb
  listing text: 0 of them changed over 08b72e2..a56b3bb; the same pathspec returns 2705 file(s)
  over 8c7985e..08b72e2, the window that last wrote them, so the first number is a measurement
  report: 2705 of 2705 row(s) identical once listing_digest is dropped (present in the
  base: no; in the migration: yes)
  the window touched 1 path(s) under ec/decompiled:
    ec/decompiled/bank0/0EA2.c
  PASS  the migration changed the column and nothing beneath it, and no listing text
  moved while it did.
```

The numbers are this section's: the 2,705 control, the empty diff, the
2,705/2,705. `--listings-from` is passed rather than defaulted, because
`8c7985e` is not `08b72e2`'s direct parent and the printed count should not
depend on it being one. It reads the two revisions out of the repository's
history, so it needs a full clone — the agent stages have one
(`fetch-depth: 0`) and `ci.yml`'s two checkouts do not; the mode says so in the
failure message and `docs/agent-pipeline.md` records it. What it prints is the
claim above and nothing more: the digests are of the text the last full
`--report` measured, and they attest to that text rather than verifying it.

That the mode can fail is from the same history rather than a fixture: pointed
at the window that *wrote* the listings (`--base 8c7985e --migration 08b72e2`)
it reports 2,705 changed listings and exits non-zero, and a revision this clone
does not have reproduces the history requirement. The drop-the-column
comparison behind it carries its own known answers in `--self-test` — an
agreeing pair, a pair differing beneath the column, a changed row count, a
renamed column, an empty side — because a comparison that compares nothing looks
exactly like a working one on a pair that agrees, and the pair above agrees.

### 14g. The nightly re-encode says which assembler answered and what moved (2026-09-23, issue #158)

§14e put the correctness question entirely onto the re-encode and §14f anchored
its digest column, and both left the re-encode itself unlanded. What was
missing was not accuracy but *legibility*: a bare `verify_reassembly.py` printed
two tallies and its exit status, so a nightly's entire output was a number with
no tool named against it and nothing to compare it to. Three things about that
run were unreadable, and all three were in the tool rather than in the schedule.

**1. The run never said which assembler produced it.** `assembler_version()` was
called from `write_report()` and nowhere else, so the bare verify path — the one
`agent-gates-deep.sh:61` runs — never mentioned the tool that answered.
`verify()` now calls it, prints both version strings, and compares them against
the `assembler` column of the committed report. **It warns rather than fails**,
because a version difference is the expected case: `project-setup` installs
Ubuntu's `sdcc` and does not install the nix shell the report was measured in.

**2. The run never compared itself to the committed report.** The bare run's
exit status is `mismatch == 0` and the committed report holds zero `mismatch`
rows, so the two agreed on the only value that gates the run and nothing
compared the rest. The run now prints its tally beside the committed one, with a
signed delta per category, and names each row whose `outcome` differs —
capped at 20 with an "and N more", the same shape `compare_digests()` already
used. The row key is `addr|program`, not `addr`: 54 addresses carry a row in
each of the two bank windows, so a key of `addr` alone would leave one row of
each of those 108 with nothing to compare against, and each would be printed as
a category that had moved. Four of the 54 — `0x031C`, `0x3A60`, `0x703A`,
`0xFF17` — are the ones whose instruction streams are identical as well, and
those four are what `ec/ghidra/README.md`'s "`listing_digest` is" section
records. This paragraph credited §14f with them and with being the reason the
key is compound; §14f names none of the four, and the count that makes the key
necessary is 54 rather than 4.

**3. `check()`'s summary line did not add up to its own total.** It counted
`match`, `assembler-gap` and `mismatch` and then printed "(of 2705)": 2,574 +
58 = 2,632. The 73 `partial` rows were in none of the three, and `partial` is
this file's own outcome. It now counts all four in a fixed order —
`2574 match, 73 partial, 58 assembler-gap, 0 mismatch (of 2705)` — and names,
without folding in, any row whose outcome is outside those four, so the line
describes the report it is summarizing. The four the committed report actually
holds; `check_one()` can also return `assembler-error`, `error`,
`missing-listing` or `empty-listing`, and a summary that dropped those would
reintroduce the same arithmetic error one row over.

**The evidence, transcribed from the run on this repository's runner.** Its
`sdas8051` is `/usr/bin/sdas8051`, reporting `02.00 + NoICE + SDCC mods`, against
the report's `05.50.4+NoICE+SDCCmods-WIP-R14`; the `NOTE` fires by design. The
tallies:

| | this run | committed |
|---|---|---|
| `match` | 2621 | 2574 |
| `partial` | 78 | 73 |
| `assembler-gap` | 6 | 58 |
| `mismatch` | 0 | 0 |
| `instructions_checked` | 45394 | 45394 |
| `instructions_unchecked` | 143 | 143 |

52 rows moved, all of them `assembler-gap` in the committed report and either
`match` (47) or `partial` (5) here. **Nothing about that says which assembler is
right**, and the run does not say so either: a moved category is a measurement,
"the assembler got better" is not, and nothing in this repository can support
the second — two ASxxxx builds are two different things being measured, and
which of them is right is a question about the disassembly.

**It also corrects a claim this file's tool made about itself.**
`assembler_version()`'s docstring said the match count "is not expected to move
with the version -- the firmware bytes are the arbiter". It moved, by 47. What
the firmware arbitrates is `mismatch`, which was 0 in both runs; which of
`match` and `assembler-gap` a row gets is decided by what the assembler can
express. The docstring now says that, with these numbers, rather than the
prediction that was wrong. `instructions_checked` did not move at all, which is
not guaranteed either — the forms this tool declines to translate are declined
before the assembler sees them, so most of that count is the tool's own
decision, and the remainder is the assembler's.

**And the composition of the 143, which §11 and `ec/ghidra/README.md` both had
wrong.** Each named six forms for the count, and three of them — `CLR bit`,
`CJNE` on a direct address, and the carry-with-immediate forms — account for
none of it, while the 110 `AJMP`/`ACALL` the same paragraphs demoted to a
clause "for a different reason" are three quarters of it. All three of the
unused forms are in `to_sdas()`'s refusal vocabulary; the vocabulary is the
assembler's, not this firmware's, and a list of refused forms without what each
contributes to the number is the shape of claim §4 is about. Replaying that
decision order over the 2,705 rows of `ec/decompiled/listing-index.csv` — the
parse `check_one()` does, naming the rule that returned `None` — gives 74
`ajmp`, 36 `acall`, 19 `mov 0x??, CY` (0x92), 13 `cpl 0x??` (0xB2) and one
`djnz A, 0xa581` at `0xa599`, which is 143. Both forward texts now carry that
composition. What is *not* claimed for it: no committed check recomputes it.
`--check` prints the 143 and not what is in it, so this is a measurement made
while writing the correction, and this section's closing question is where it
would become one.

**A fourth thing, found by running it: `--jobs 4` was not reproducible.** The
same committed inputs, on the same runner, gave `match` 2,579, 2,588, 2,590 and
2,591 across four runs, against 2,621 on every `--jobs 1` run, with `mismatch` 0
throughout. The scratch directories were handed out by `index % jobs`, which is
one per index *slot* and not one per thread: a pool holds whichever indices are
in flight, that set drifts as soon as one worker finishes early, and two
concurrent functions then assemble into one directory and overwrite each other's
`f.s51` and `f.lst`. The run reports `assembler-error` and "no bytes emitted at
..." for functions that were never wrong. Each function now gets its own
directory — 2,705 `mkdir`s, and the question is gone. This was not in the issue;
it was found by running the issue's own test, and it is fixed here because the
per-row comparison would otherwise have named the raced rows as rows that moved.

**The exit status is unchanged, on purpose, and that is a calibration rather than
an omission.** A version difference warns. A moved category is reported. Neither
fails: a branch that has re-reported its listings and not yet committed its CSV
moves the tally legitimately, and this tool cannot tell that from a regression,
so a scheduled run that failed on a difference nobody could action unattended
would be buying noise rather than a gate. `--limit` runs print the committed
tally as a labelled reference and compare nothing, because 40 rows are not a
disagreement with 2,705.

**The schedule keeps a record.** `docs/ci/agent-gates-deep-schedule.yml` now
tees its own output to `$RUNNER_TEMP/deep-gates.log` and uploads it with
`actions/upload-artifact` and `if: always()`, so a run that happened leaves an
artifact and a run that did not leaves none — which is the file's own comment
about GitHub dropping scheduled runs, guarded against. `set -o pipefail` is set
*before* the pipe, since the default `bash -e` does not set it and without it a
failing gate exits as `tee`'s zero. **Absence is observable, not failing**:
making a vanished run fail something needs a checker that runs when the
scheduled one did not, and the scheduler is the thing that drops runs. The
re-encode is still unscheduled, and nothing here should be read as closing that.

**The retracted first-pass numbers are no longer restated forward.** §11's
italic paragraph above is the record of that correction and is untouched. What
was removed is the *forward* restatement of the retracted figure
— in `ec/ghidra/README.md`, in three docstrings in `verify_reassembly.py`, and
in §11's own "what sdas8051 cannot express" paragraph, whose opcode list still
carried `SETB bit` and `MOVC A,bit`, the two forms §11 measured as assembling
correctly. A file that contradicts itself four lines from its own correction is
the problem §4 records, not the correction.

**What this opens.** A nightly that consistently moves `partial` /
`assembler-gap` against the committed report is telling you that the committed
numbers describe one ASxxxx and the runner has another, and the durable answer
may be for the report to record more than a version string — the assembler's
own gap behaviour, or a per-row check that says which form was refused and by
which build. That is not this change, and a version string plus a per-row diff
is the most a log-reading human can be given tonight.

**And one this raises without answering.** A committed report row whose outcome
is outside the four — `error`, `assembler-error` — is now named by the residual
rather than silently missing from the summary, and `check()` still passes it. A
report saying `error` probably should fail and does not. The new line makes the
question visible; it does not settle it.

### 14h. The re-encode under the assembler's a nightly actually has: 52 rows move, the 143 do not (2026-09-23, issue #157)

*(Merge note, 2026-09-24. This section was written in parallel with §14g
(issue #158) and was also numbered §14g on its branch; references to "§14g"
from issue #157's text — in `ec/ghidra/README.md`, in this section, and in
`evidence/ec-reencode/` — mean this section. The two measured the same runner
assembler independently and agree on the tallies. Both also found and fixed
the same `--jobs` race in `verify()`; the merged code keeps §14g's fix, one
scratch directory per function, run through this section's `run_rows()` so its
forced-race self-test still covers the dispatch.)*

**The two tallies are not the same, and the 52 rows that differ are not all
attributable to the assembler.** Three `--jobs 4` runs of one command over the
same 2,705 rows gave three different answers, and `--jobs 1` gave a fourth. That
is a race in `verify()`'s dispatch, and finding it was the point of the
exercise: the second measurement could not be taken until it was fixed. The fix
is in this PR, the per-row numbers below are all from the post-fix run, and the
durable record is `evidence/ec-reencode/2026-09-23-sdas8051-versions.md` with
the differing rows in `evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv`.

**The race.** `verify()` allocated one scratch directory per worker and then
indexed that list by *row* (`dirs[idx % jobs]`), which is not the same thing.
`ThreadPoolExecutor.map` hands the next row to whichever worker frees up first,
so rows 0 and 4 can be in flight together and both took `dirs[0]` — each
overwriting the other's `f.s51` before reading back a `f.lst` that was not its
own. The comment above the line read "one scratch dir per thread", so the
intent was right and the implementation was not, which is the shape this section
keeps finding. A row that reads back another row's listing reports `no bytes
emitted` for an address the assembler did place, and `assembler-error` when the
`.s51` it did not write is the one that failed. The fix on this branch was a
`threading.local()` directory allocated on each worker's first row (merged as
§14g's per-function directory instead — see the note above); the
self-test forces the pickup order that provokes the collision rather than
waiting for it to happen by luck, and fails against the old code. After it,
three `--jobs 4` runs produced three byte-identical CSVs, equal to `--jobs 1`.

**Which means the committed report may carry the same artefact.** `08b72e2`,
the commit that wrote `reassembly.csv`, records no `--jobs` value, so there is
no way to tell from history whether that run was serialised. Its 58
`assembler-gap` rows sit inside the range the race produced here — 37 to 65
across five `--jobs 4` runs of the same command. That is a reason to distrust
the *committed outcome columns*, not a demonstration that they are wrong: the
instruction columns, which the race cannot touch, are 45,394 and 143 on every
run of it. Settling it needs the nix assembler, which project-setup does not
install — the follow-up, below.

### The two measurements

Both are single-assembler, and each is labelled with the string that assembler
reports for itself.

| | committed `reassembly.csv` | this run |
|---|---|---|
| assembler | `sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14` | `sdas8051 02.00` |
| via | nix SDCC 4.6.0 | `.github/actions/project-setup`, SDCC 4.2.0 #13081, `/usr/bin/sdas8051` |
| `match` | 2,574 | 2,621 |
| `partial` | 73 | 78 |
| `assembler-gap` | 58 | 6 |
| `mismatch` / `assembler-error` | 0 / 0 | 0 / 0 |
| re-encoded | 45,394 of 45,537 (99.69%) | 45,394 of 45,537 (99.69%) |
| unchecked | 143 | 143 |

Six years apart in SDCC, and not the same ASxxxx: `02.00` is not a prefix of
`05.50.4`. The version string is not the whole identity in either direction —
§14e's reason for stamping it is unchanged — so the record carries
`sdcc --version`, the resolved real path and the raw banner beside the
comparison rather than the banner alone.

### Whether the set of unencodable instructions moves: it does not

**As this tool records it, per row, on all 2,705 rows: 0 rows differ in
`instructions_checked` or `instructions_unchecked`, and both sides total 45,394
and 143.** That is the answer to the question #151's 143 belongs to, and it is
the robust half of this section, because those two columns are computed by
`to_sdas()` in pure Python before the assembler is invoked at all. They are a
property of the committed listings and this tool's gap rules, not of which
ASxxxx is on PATH, and the race above cannot reach them either — 45,394 and
143 on every run of it, racy or not.

The limit is the tool's row model, not the comparison: a row records a count
and the *first* skipped address, not the full set of them. So the claim is
about the set as recorded per row, and not an address-level set identity that
was not computed. Producing that would mean threading the whole `skipped` list
through `check_one()`, which is a larger change than this issue earns.

### What did move: 52 rows, all one way

Every one of the committed report's 58 `assembler-gap` rows is accounted for:
47 re-encode completely under the apt build, 5 re-encode with the same 143
unchecked instructions between them, 6 stay gaps. None regressed. The 6 that
stay are the `ajmp` rows, which `GAP_MNEMONICS` excludes before the assembler
is consulted, so they are gaps by construction on both sides.

Those 52 rows carry `no bytes emitted at NNNN` in the committed report, and the
instruction at each named address is an ordinary one — `mov` (28), `lcall` (7),
`movx` (4), `clr` (3), `ret` (2), `ljmp` (2), and six singletons. An assembler
declining to place a `movx @DPTR,A` at the first instruction of a function is
not a statement about the form, which is the observation that made the race
worth chasing before the assembler difference was worth writing up.

**Two candidate causes, and this environment separates neither:** SDCC 4.2.0 may
accept forms 05.50.4 declines, and the committed rows may carry the race. Both
predict 52 gap rows. Re-running the nix assembler settles it and nix is out of
scope here, so the follow-up is to re-measure `reassembly.csv` with the pinned
nix build on a runner that has it, at the dispatch as it now stands. Until then
the honest statement is that 52 rows differ and this run cannot say why.

The 47 rows that become `match` are **not** new evidence for the 1:1 claim.
The committed report already asserts those bytes are what the firmware holds,
and `--check` compares all 45,624 instructions' bytes with no assembler at all.
What has moved is how much of the corpus an independent assembler gets to
confirm, not whether the bytes are right.

### The nightly

Both branches of the issue's either/or are settled by constraint, and the
measurement only sizes the note. Pinning the nix assembler means editing
`.github/actions/project-setup/action.yml`, which is under `.github/` and out
of scope. So the second branch applies, and
`docs/ci/agent-gates-deep-schedule.yml` gains one step before the deep-gates
step that resolves `sdas8051`, prints its path, its `sdcc --version` and its
banner, and prints the string the committed `reassembly.csv` names — read from
the file at run time, not hardcoded, so the note stays true as `ubuntu-latest`
drifts. It prints what it observed and asserts no fixed relationship; that
§14g's numbers are the comparison, and a future run that disagrees with them is
information rather than a failure of the note.

The re-encode itself now prints the resolved assembler path and its version on
every full run, so the nightly's log is self-labelling without a step at all.
`--emit-csv` exists so a nightly run can be compared row by row against the
committed report without writing to it; it refuses
`ec/ghidra/reassembly.csv` outright, and the refusal is what the self-test
asserts.

Two things the nightly is *not* told to do. It does not become a required
check, for §14e's reason. And its exit code is not the result: `main()` returns
non-zero only on `mismatch`, so a nightly that runs the apt assembler and gets
zero mismatches exits 0 whether or not its outcome columns agree with the
committed report's — which is why the numbers are read from the tallies and
not from `$?`.

Landing the schedule is still a human's one-line copy, and §14e still holds
that the re-encode is not per-commit.

### 14i. The cross-decoder comparison has a sample, a denominator and a record (2026-09-24, issue #140)

§14d closes with two claims about the cross-decoder comparison. One still
holds: it is cheap, and it sits behind `--cross-decoder` because of where
output belongs. The other one — the *reason* it was cheap — did not survive a
wider sample. **0.13 s is what four functions cost**, and the four were a
hardcoded list of addresses out of the 2,710 the export carries. Two of those
four compared nothing at all, which is §14b's failure one level up and is the
half of the problem that was not a speed question.

**The denominator (2026-09-24, this runner, warm page cache).** The sample is
now derived from committed data — every annotated function the listing index
carries (1,848), plus every eighth of the remaining 862, plus each program's
first non-annotated row — so all four programs are represented by construction
and the same inputs always give the same rows. Over that sample:

```
compared 1016 of 1957 functions, 940 vacuous; 701 agreed, 315 disagreed, 1 no-export
```

The annotated half is 1,848 rather than the 1,783 this section was first
measured over: issue #136 added 21 `common` interrupt-entry rows and issue
#134's call-graph tranche added 44 more (6 `bank0`, 5 `bank1`, 33 `common`), and
an annotated row is a backbone sample row, so they all join.
`ec/ghidra/cross-decoder.csv` is regenerated with `--report` for the same
reason, and the stride half is the other side of the same coin — 44 rows moving
out of the unannotated set is 44 fewer rows to stride, so the stride sample is
not the one it was. The `1 no-export` is that arithmetic landing on
`bank1 0x17FE`, whose listing-index row is `(no-instructions)`: the function
exists and is exported, and there is no listing for the comparison to read. It
is counted and reported rather than dropped, and it is a sampled row the
previous sample never reached — not a new gap in the export.

**CORRECTION 2026-09-24 (issue #255), to the `disagree` tally this section
first measured and to its composition further down.** The tally is now `701 agreed, 315
disagreed`, and the composition's "of the rest" is 167 distinct addresses
rather than 220, of which 129 have no `registers.yaml` entry rather than 127.
The cause is a defect in the comparison, not a change in the firmware or the
decompile: `_EXTMEM` matched only the `EXTMEM_` spelling, so a listing exported
under the `XDATA_####` name a register row gives it read as a `disagree`
against a C that names the address in so many words; and its character class
was lowercase-only while the two spellings disagree on case, so the uppercase
names were invisible to it even once the prefix matched. Issue #255 added such
a row (`XDATA_1664`), which is what exposed it -- 82 rows left the bucket, and
each left it because the C said the address. The count was wrong for every one
of those rows from the day its register row landed, so this corrects a figure
this section measured rather than superseding it; the sample, the denominator
and the method are unchanged and are not what is in question here. The 110 in
the `bl51_bank_select_*` sub-bucket below, against the 109 this section first
measured, is issue #134's tranche adding one more of them; the rest of the
movement is the fix's.

| program | sampled | compared | vacuous | disagree |
|---|---|---|---|---|
| bank0 | 698 | 440 | 258 | 96 |
| bank1 | 599 | 341 | 257 | 107 |
| common | 158 | 62 | 96 | 38 |
| pd | 502 | 173 | 329 | 74 |

**This is §14b's failure one level up, and it is why the line above is printed
on every run.** §14b is the Windows parser whose regex matched zero of 502,652
lines and reported a pass over 358 GB of scanning: *a parser that reads a
fraction of a file and finds nothing wrong in it reports a pass.* The
four-function sample was the same shape — **two of its four functions compared
nothing at all**, because their straight-line openings name no XDATA address,
and the run said so in the same form as a pass. 940 vacuous out of 1,957 is
the same property at a larger scale, and the denominator is what makes it
visible to whoever is reading.

**A correction to the "40 straight-line instruction(s)" the old output printed.**
The window was supposed to end at the first branch, by a list of branch
mnemonics matched against the line `disasm8051.py` prints — whose first column
is the address, so the match never fired on any line. Every sample therefore
decoded all 40 instructions, branches included, which is the desync this
comparison exists to avoid: past the first branch the `0x90` bytes it found
were operands of instructions the walk had lost track of. The terminator is now
`disasm8051.FLOW_OPCODES`, and the four known answers moved with it:

| | old (40 instructions, never stopped) | now (stops at the first flow instruction) |
|---|---|---|
| bank0 `0xB1F0` | 6 addresses, all named — `agree` | **7 instructions, 2 addresses** (`0x0A4E`, `0x0A4F`), `agree` |
| bank0 `0xB158` | 8 addresses, 4 named — `0x0438`, `0x0439`, `0x04A6`, `0x04A7` missing | **6 instructions, 3 addresses**, `0x0438`/`0x0439` missing |
| bank0 `0xBAE5` | 1 instruction, vacuous | unchanged, vacuous |
| common `0x707D` | 14 instructions, vacuous | 13 instructions, vacuous |

The fold the old output reported at `0x04A6`/`0x04A7` is real and still is —
those two bytes are read and handed to the big-endian store helper — but it is
past the first branch, so a straight-line window does not reach it.
`0xB158` still `disagree`s, on the first byte pair its opening does reach. The
old figures are left in the table because they are the evidence that the
terminator never fired; they are not what the tool prints now.

**The file offset was bank 0's, applied to everything.**
`file_off = 0x08000 + (start - COMMON_END)` is correct for `bank0` and,
because the common area is byte-identical in both banks, coincidentally correct
for `common`. It is wrong by a 32 KiB window for `bank1` and wrong by a whole
program for `pd`, and it would have kept reporting a clean result over the
wrong bytes. It is now `file_offset(program, addr)`, a lookup over the three
windows, with one known-answer anchor per program in `--self-test` — the first
`n` bytes of the committed `.asm` at that address must equal the firmware at
the offset the function returns — plus the negative half, that no other
program's offset returns the same bytes. The negative half is what makes the
four mean anything: without it an anchor that passes by coincidence is
indistinguishable from one that passes because the map is right.

**And the 1,920-row comparison is faster than the four-function one was.** The
old path spawned a `disasm8051.py` subprocess per function *and* re-read all
2,710 listing-index rows per function inside `function_size()`; the new one
imports the decoder, reads the listing index once, and reads the annotations
once. Measured the same way as the table above, each on this runner with a warm
page cache, three runs each, on the tree carrying issue #136's rows:

| | 2026-09-23 | before this change | after |
|---|---|---|---|
| `--self-test` | 0.15 s | 0.42 s | 0.59 s |
| `--check` | 0.19 s | 0.22 s | 0.34 s |
| `--self-test --cross-decoder` | 0.27 s | 0.55 s | 0.72 s |
| the comparison alone | 0.13 s (4 functions) | — | **0.10 s (1,920 functions)** |
| `--report` | n/a | n/a | 0.17 s |

So a 480× larger sample costs slightly less than the four-function one did, and
the ~0.13 s the comparison adds to each per-commit run is the price of reading
1,920 `.c` files the check already walks. The `--report` output is
byte-identical run to run (verified), which is what the ratchet needs.

**What a `disagree` is not.** 397 rows disagree and the bucket is not a defect
list, so the count is worth reading with its composition. **109** are the
`mov dptr,#imm; ljmp <BL51 stub>` bank-switch trampoline, whose C calls
`bl51_bank_select_1(0x88f0)` — the address is in the output as a literal
argument, but not as a symbol carrying its address, and the two spellings that
do carry one (`DAT_EXTMEM_####`, `XDATA_####`) are the whole vocabulary of
this comparison. Of the rest, 220 distinct addresses are involved
and **127 of them have no entry in `ec/annotations/registers.yaml`**, so they
cannot appear under either spelling in any C at all: a `disagree` there measures the
register map's coverage and says nothing about the decompiler. (The 397 and
the 220 are the pre-correction figures; the corrected tally and the 165 behind
it are recorded in the correction note above, and the 127 is unchanged.) Splitting the
bucket needs the byte-pair-folding case *enumerated* rather than described, and
guessing which of a function's C reads is a fold would manufacture the very
distinction the comparison is meant to measure. So the ratchet fires on
**change**, not on presence — which is issue #140's option A, and leaves its
option B to whoever does that enumeration.

**The 0x07D0 re-test, and one correction to the plan's version of it.** The
widened sample re-tests both blind-spot addresses. It finds 0x07D0 in seven
sampled PD functions' openings — `0x8576`, `0x8716`, `0x98A1`, `0xA571`,
`0xA678`, `0xAD3C`, `0xC2FA` — all of them `agree`: the linear decoder names
0x07D0 and so does the C. **All seven are in the PD image, and that is the half
of the question that was already answered.** §4 and `ec-0x07d0-sites.md` own
the PD's 254 sites (issue #25); the half still open is whether the *main EC
image* acts on 0x07D0 at all, which is the indirect-XDATA blind spot (#34) and
which this comparison cannot reach, because the EC image references 0x07D0 zero
times by this method. So the re-test confirms the widened comparison sees
0x07D0 where it is, and settles nothing about the byte the Windows stack writes.

The plan this came from named `pd 0x3478` as the opening to look at, and
**there is no function at `pd 0x3478`** — no listing row, no `.c` — so the
anchor is `pd 0xA678`, which is in the sample and does open `90 07 d0`.
0x04A6/0x04A7 is the other half, and the correction table above is its answer
under a window that stops at the first branch.

**The outcome is committed and ratcheted.** `ec/ghidra/cross-decoder.csv`,
1,957 rows, generated by `--report` and by nothing else, beside `manifest.csv`
and `reassembly.csv`. `--check` recomputes every row and fails on a row it does
not carry, a row it carries that the sample no longer has, or any cell that
moved; and it fails on a wholly vacuous or wholly unexported sample, which is
the §14b failure above encoded as an assertion rather than as a number to be
read. So the second half of what issue #140 reports — "the result is printed
and nothing else" — is closed, and the cost is the ~0.13 s in the table.

**One stale sentence, left visible.** `.github/scripts/agent-gates.sh` still
prints that this tier "does not run … the advisory cross-decoder comparison".
It no longer *prints* the run; it recomputes and ratchets on every row. Both
`.github/` files are template-copied and this change cannot land them (the
token has no `workflow` scope), so the wording is corrected in
`ec/ghidra/README.md` and here instead.

### 14j. The 56 MB `.c` is now read, and digested (2026-09-24, issue #141)

**Correction to the first bullet of §14.** It reads "**The 56 MB `.c` was never
read.** The old `--check` touched `windows/decompiled/native/*.c` only through
`os.listdir` and `os.path.isfile` — names, not contents." That was true of
#137's audit and of the tree it ran against. It is **no longer true of this
tree**, and the sentence is left above rather than edited out, because the
finding it records — a check that reads names instead of contents — is the
finding this work exists to act on.

`GamingCenter3_Cross.c` (56,693,822 bytes) is now read and SHA-256'd on every
`--check`, and so is every other committed `.c` in all three components.
Measured here, warm page cache, each step on its own:

| | committed `.c` | bytes | sha256, all of them |
|---|---|---|---|
| `ec/decompiled/` | 2,710 | 3,330,716 | 0.040 s |
| `bios/decompiled/` | 39 | 1,021,920 | 0.001 s |
| `windows/decompiled/native/` | 6 | 68,212,335 | 0.050 s |
| **total** | **2,755** | **72,564,971** | **0.091 s** |

So the open question #141 asked — is hashing the 68 MB of Windows C the slow
part — is measured and the answer is **no**. Dropping the check for being slow
is the exact mistake §14 exists to record, so the number goes here whether or
not it flatters the change.

`decompile_native.py --check` is **1.90 s** here (1.89 / 1.91 / 1.90 over three
runs), and the EC and BIOS checks are **0.37 s** and **0.34 s**. The whole
cheap-tier gate is **10.1 s** against a **9.33 s** baseline measured on this
same runner with the change stashed (9.33 / 9.28 / 9.40 over three runs), so
everything here costs about **0.8 s**. §14e's 5.9 s figure is a different
machine and is not comparable to either number; the delta is.

**Those figures, re-measured on the merged tree.** The two sections are
additive, so the EC's `--check` now does this section's digest and pairing work
*and* §14i's cross-decoder ratchet over 1,901 functions, and 0.37 s is no
longer what it costs. Re-taken here, warm page cache, three runs each, on the
tree carrying both:

| | what §14j recorded | merged tree |
|---|---|---|
| `build_ec_decompile.py --check` | 0.37 s | **0.48 s** (0.48 / 0.49 / 0.48) |
| `build_ec_decompile.py --self-test` | not measured here; §14i recorded 0.59 s | **0.77 s** (0.84 / 0.77 / 0.77) |
| `decompile_native.py --check` | 1.90 s | 1.88 s (1.88 / 1.87 / 1.92) — unchanged, this section does not touch it |
| `bios_extract.py --check` | 0.34 s | 0.34 s (0.34 / 0.37 / 0.34) — unchanged, likewise |
| whole cheap tier | 10.1 s | **11.1 s** (11.29 / 11.11 / 11.17) |

The Windows and BIOS rows are the control: this change is EC-side and index-
side, and the two components it does not touch did not move, which is what
makes the EC's 0.11 s readable as the sum of the two sections rather than as
runner drift. §14e's 5.9 s and §14i's 0.34 s are both still correct *of the
trees they measured*; neither is what the merged `--check` costs. The claim
this section rests on — that the cost is small and the direction is the point —
survives, and the whole tier is still ~11 s.

**And the first version of the Windows presence check cost 5.4 s, which is §14a
happening again.** It built each file's markers as a flat set of `(name, addr)`
pairs and then asked `any(a == addr for _n, a in markers)` once per row: 10,141
rows against 10,141 markers, 7.5 s for the whole check. The markers are keyed on
address now and each row is a dict lookup. The defect was invisible in the
output — the distinct-file count the check prints says 5 either way — so
`--self-test` pins the **shape** of the per-file container, reading it back out
of the module and asserting it is a dict keyed on address.

A wall-clock assertion was tried first and **would not have caught it**: the
quadratic form takes 0.18 s on that self-test's 2,000-row fixture, far inside
any bound loose enough not to be flaky on a loaded runner, while the real
regression was 5.4 s at 26× the work. A timing assertion loose enough to be
stable is loose enough to pass the thing it was written to catch; the structural
one fails on any machine, in milliseconds. **§14a is not only "do not read a file
once per row"; it is also "do not scan a collection once per row", and the fix
is keyed on whatever the join key is.**

**Two mechanisms, and they are not the same check.** Each tool's `check()` now
also pairs every index row to the function its `.c` declares — exists,
non-empty, and carrying the address (and, on EC and Windows, the name) the row
gives it. Coverage on the committed tree, all four measured, not assumed:

| | index rows | how a row finds its `.c` | address declared | name declared |
|---|---|---|---|---|
| EC | 2,710 | `out_file`, one `.c` per function | 2,710 | 2,710 |
| Windows | 10,664 | `out_file` is empty on every row; `program + ".c"` | 10,664 | 10,664 |
| BIOS | 955 | `out_file` names the module `.c` | 955 | 171 |

The BIOS name figure is **not a defect and is not asserted**. `bios/decompiled/
*.c` is the unedited `DecompAll` export, and `DecompAll` runs *before*
`ApplyAnnotations` (`bios_extract.py`, `post_scripts`), so by construction it
cannot carry annotation names. It is printed on every run so the number stays
auditable, and the 955 rows **classified** rather than sampled — naming a few
rows as though they were a special set is how a figure stops being checkable:

| | rows |
|---|---|
| name carried verbatim | 171 |
| unedited export still says `FUN_<addr>` | 754 |
| unedited export says `entry`, index has a specific name | 29 |
| unedited export says `thunk_FUN_00001130` | 1 |

The last group is one row, `OverClockSmiHandler 00005788 forward_to_00001130`.
The 29 are two of several, not a set of their own: `OemGlobalNvsDxe 00000370`
(`entry_dispatch`) and `PeiOverClock FFCFBB49` (`entry_clamp_status`) are two of
them. An earlier draft of this section named those two plus `Setup 0001DAC4
_wcsupr` as "the three rows that break the correlation"; `Setup 0001DAC4` does
**not** break it — the index says `_wcsupr` and the `.c` says `_wcsupr` — so
that list was wrong, and it was wrong in the direction this file's own rule is
about. The classification above replaces it.

**That pairing cannot reach `GamingCenter3_Cross.c` at all**, which is why the
digest is not the optional half of this issue. The file is the retained
decompile of a program in `PROJECT_EXCLUDED`; it appears in no index, and the
manifest row for it records `functions=0, mode=not-in-project`. So a check built
on index rows says nothing about it however thorough it is. A committed digest
does, which is why the artefact the issue singles out is now covered by
`windows/ghidra/c-digests.csv` and the other two components have the same file:
2,755 rows, `path,sha256,bytes`, one per committed `.c`, regenerable without
Ghidra by `--write-digests`.

Three calibration points, stated because the scope of this is easy to read as
larger than it is:

- **It catches accidental corruption, and it makes any accepted change to a
  decompile a changed digest row naming the file that moved.** That is
  *detectable and attributable*, and it is what forces the change through
  review; it is not the same as a readable diff of the `.c` itself. On the EC
  and BIOS those files stay ordinary text and do diff normally, so there it is
  both. The Windows tree is `-diff` (see below), so there the digest row is the
  whole of what a reviewer sees. It is **not** an anti-tamper control —
  `--write-digests` will re-bless a mangled file — and it is **not** proof that a
  decompile is a faithful reading of the firmware. §14e says the same about
  `listing_digest` and it is the same sentence.
- **It is not `verify_reassembly.py`'s mechanism.** That tool re-derives listing
  bytes from the firmware, a trusted input. The decompiled C has no such input to
  be re-derived from, so a committed digest is new here rather than a copy of an
  existing precedent.
- **The retained decompile keeps its printed carve-out in the listing check** —
  it genuinely has no machine code beside it, and nothing in this repository can
  change that — and is *digested* here rather than exempted. A carve-out that
  prints nothing and checks nothing is how a check stops meaning anything.

**One of the issue's premises was wrong, and saying so is part of the change.**
#141 reported that `build_ec_decompile.py:check()` and `bios_extract.py` open no
`.c` either. Both do, and have: the EC walks `ec/decompiled` for
`DECOMPILER UNAVAILABLE`, the BIOS does the same over `bios/decompiled` and
additionally opens each `LEGACY_MODULES` file to assert its `DecompAll` header
and its function count. Only `decompile_native.py` genuinely reached the Windows
C through `os.listdir`/`os.path.isfile` alone. That does not shrink the work, it
re-aims it: the EC and BIOS additions are about pairing an index row to the
function its `.c` declares, which nothing anywhere did, rather than about opening
a `.c` for the first time.

**Still not established: that any of it is right.** A digest that agrees means
the file has not moved since it was committed, not that the decompile means what
it says. The checks above are a floor against corruption, not a verification of
the C, and the tier that would say more is the same re-encode §14e discusses,
which is not per-commit.

## 15. The EC and BIOS indexes get the same structural guards (2026-09-23, issue #142)

§14e ended with the always-on tier having *gained* structural checks — but for
the Windows index only. `windows/tools/decompile_native.py` reads its committed
CSVs with `csv.DictReader(..., strict=True)`, rejects a row that did not come
out whole, rejects a `(program, addr)` key twice, compares the manifest's
recorded `functions` against both indexes' row counts, and reads the `mode`
column against a `MANIFEST_MODES` vocabulary. The other two read their committed
indexes and manifests with a default `DictReader`, and the BIOS compared no
manifest count against an index at all.

**The known answer, measured on the committed files, is clean.** That is the
point of stating it before the check exists, and the reason this is a guard
against drift rather than a bug hunt:

| | `index.csv` | `listing-index.csv` | manifest |
|---|---|---|---|
| EC (`ec/decompiled/`, `ec/ghidra/manifest.csv`) | 2,710 rows, 2,710 distinct `(program, addr)`, 0 dups, 0 short rows | 2,710 / 2,710, same | 4 rows, `functions` agrees with both indexes on every row and sums to 2,710; all `mode` = `export-only` |
| BIOS (`bios/ghidra/`) | 955 rows, 955 distinct keys, 0 dups, 0 short rows | 955 / 955, same | 38 rows, `functions` agrees with both indexes on every row and sums to 955; all `mode` = `export-only` |

Reproduce it, one command per component, with no Ghidra and no network:

```
python3 ec/tools/build_ec_decompile.py --work /tmp/x --check
python3 ec/tools/build_ec_decompile.py --work /tmp/x --self-test
python3 bios/tools/bios_extract.py   --work /tmp/x --check
python3 bios/tools/bios_extract.py   --work /tmp/x --self-test
```

Both `--check`s now print the counts they compared (`2710 index row(s), 2710
listing-index row(s), 4 manifest program(s)`, and the same shape for 955/955/38),
and both `--self-test`s assert the totals, so the table above is a fact the
repository re-checks rather than a paragraph somebody wrote once.

A later change widened the same four guards — strict read, a row that did not
come out whole, a key written twice, the file's own header — to the four
committed CSVs that are inputs to a run rather than scratch output of one: the
two annotation layers, the EC call-target census and the BIOS load map. The
known answer on those is clean as well, measured the same way, with the same
reader:

| file | records | header | short rows | duplicate keys |
|---|---|---|---|---|
| `ec/annotations/ghidra-functions.csv` | **1,769** | 8 columns | 0 | 0 on `(scope, addr)` |
| `bios/annotations/ghidra-functions.csv` | **788** | 8 columns | 0 | 0 on `(scope, addr)` |
| `ec/annotations/bank-call-targets.csv` | **5,998** | 12 columns | 0 | 0 on `(file_offset, target)` |
| `bios/ghidra/load-map.csv` | **38** | 6 columns | 0 | 0 on `program` |

**1,769 is not the 1,771 the follow-up issue quoted, and the difference is worth
a line rather than a quiet edit.** The EC annotations file is 1,772 physical
lines: one header, 1,769 records, and two extra physical lines belonging to one
record — `bank0,0x0EA2,timer1_counted_delay_using_0a56`, whose quoted `comment`
runs to three. 1,771 is that file's physical data-line count, which is what a
line count reports and not what a `DictReader` returns; the default reader and
`strict=True` both return the same 1,769 rows, so nothing about the parse as it
stands changes. The number `--self-test` pins is the record count, measured, and
the issue's figure is left on the record here for the same reason §4's wrong
claims are.

**The duplicate key is a normalised address, and that is asserted rather than
assumed.** Both annotation files spell an address both ways — 1,039 bare `0EA2`
rows against 730 `0x0B158` ones in the EC file, 210 and 578 in the BIOS one — so
a plain string key would call `0B158` and `0x0B158` two different functions and
miss the one duplicate this is looking for. Raw and normalised distinct-key
counts are equal for all three key-bearing committed files, and each
`--self-test` asserts that equality, which is what makes the normalisation a
fact about the data rather than an assumption about it.

**What a clean result means, precisely: the committed files carry no structural
fault today.** It is not evidence that the export has always been correct, it
says nothing about the firmware, and nothing here ran on the machine — this is
entirely committed-file checking, with no register read back and no behaviour
observed. Both this block and the one above it are guards against drift.

### 15a. What the guard is actually worth

Two failure shapes, both of which reach a committed index through the export
rather than through a hand edit — the inputs include `ghidra-functions.csv` and
`merge_annotation_shards.py`, and both indexes are rewritten from them on every
run.

- **A duplicated `(program, addr)`.** The row count then means something other
  than "number of functions", which is the only thing the manifest's count is
  compared against — and §12 is the worked example of what the manifest catches
  when the count is wrong.
- **A quoting error.** csv's default reader is forgiving about quoting in the one
  way that hides an error rather than raising it. Given a row `a,0012,"FUN,3`
  whose quote is never closed and the row `b,0020,FUN,3` after it, it returns
  **one** row: `name` is `FUN,3` with the whole next line appended, and `size`
  is `None`. Two rows of file read as one, and every count taken from it quietly
  smaller than the file. Under `strict=True` the same input raises. That `None`
  is visible if something looks for it, and nothing did.

### 15b. The EC already had half of this, which is a correction worth recording

The issue's summary said the EC "got none of it". That is right about
`strict=True`, the structural check and the mode vocabulary, and wrong about
coverage: `build_ec_decompile.py` already compared the manifest's `functions`
against `index.csv`'s row counts — but skipped `common` as "an export grouping,
not a program". The EC work was therefore to *extend and rehouse* that partial
check (add `listing-index.csv`, cover `common` too) rather than to write a
second one beside it. `common` is a grouping, and it is also 753 of the 2,710
rows in the index, which is more than a grouping may cost quietly. The BIOS
genuinely had none and got the whole set.

The Windows coverage check needs an `export_label()` because its manifest names
a binary and its index names an export label. **Neither the EC nor the BIOS
needs one**, and that was verified on the files rather than assumed: the
manifest's `program` set equals the index's exactly (the four EC program names,
the 38 BIOS module names), so the two join directly. A `--self-test` assertion
pins it in each tool, so a future manifest that starts disagreeing about the
join key fails as a failing assertion rather than as a coverage mismatch that
reads like drift.

### 15c. Three copies, on purpose, and what the gate costs

The four helpers are copied into each of the three drivers rather than factored
into a shared module: `windows/tools/` is not a direction an EC build script
should import from, the three column vocabularies differ, and a shared module
is a structural change this work did not ask for. The cost is three copies that
could drift, and the mitigation is that all three self-tests assert the same
properties, so a divergence surfaces as a failing assertion. A fourth driver
would be the moment to revisit that — worth its own issue then.

Timing, on this runner with a warm page cache, five runs each: the EC
`--check` is **0.19 s** and `--self-test` **0.13 s**; the BIOS `--check` is
**0.25 s** and `--self-test` **0.06 s**. The 0.24 s / 0.15 s the two EC READMEs
quoted are updated to the measured pair. The EC `--check` measured 0.19 s before
this change and 0.19 s after, so what was added — string comparisons over two
committed CSVs — is not what the cheap tier's cost is made of.

Widening the guards to the four annotation-side CSVs was measured the same way,
before and after, five runs each, both sides on one runner: the EC `--check`
**0.25 s → 0.27 s**, the EC `--self-test` **0.17 s → 0.20 s**, the BIOS
`--check` **0.33 s → 0.32 s**, the BIOS `--self-test` **0.08 s → 0.09 s**. So
strict-parsing 8,593 committed rows and keying them costs about 0.03 s on the EC
self-test and nothing measurable on the BIOS, which is not what the cheap tier's
cost is made of either.

Those pairs are also a correction worth leaving visible: the absolute figures in
the paragraph above do not reproduce at that precision on a later runner — the
unchanged tools measure 0.02–0.08 s slower across all four commands there, and of
the README figures only the BIOS `--check`'s 0.33 s reproduces exactly. Since
both sides of each pair above were measured the same way on the same machine,
the deltas are the figures that mean something, and replacing a README's absolute
with a number from a different runner would have imported the difference between
the two. `ec/ghidra/README.md` therefore records the measured 0.03 s its
`--self-test` figure moved rather than a new absolute, and
`bios/ghidra/README.md` is untouched: its `--check` did not move, and its
`--self-test` moved 0.01 s against a baseline that already differs from the
number it prints by that much.

Deliberately **not** widened to: the raw exporter CSVs — `index-raw.csv`,
`listing-raw.csv` — and the per-row reads of those inside the export path. They
are written into the scratch work dir on every run rather than committed, so a
fault in one is a fault in this run's output and not drift in a committed input,
and the committed index they feed is structurally guarded in its own right now.
Named here as a possible follow-up, not silently skipped.

Also outside this change, and named rather than quietly passed over: the readers
on the other side of the same annotation files.
`ghidra/scripts/ApplyAnnotations.java` is not a `DictReader` path and does not
behave like one. It joins lines until the quotes balance, which is what lets the
one multi-line record above parse as the single record it is, and it pads a short
row out to eight columns rather than failing on it — a deliberate tolerance for a
hand-written file that leaves the empty `signature` cell off, and a third set of
rules to impose on a pre-script all three components share.
`ec/tools/merge_annotation_shards.py`, which is where the EC annotations are
rewritten from a fan-out, already refuses a duplicate `(scope, addr)` and
asserts that it does in its own self-test. The gap there is the short row, and
closing it is a separate call on a tool this change did not otherwise touch.

## 16. The four offline suites are one command, and one of them was an ordering accident (2026-09-23, issue #162)

The repository's offline `unittest` suites were four files that no gate and no
workflow ran: `ec/tools/test_grade_0751_isolation.py` (16 tests),
`windows/tools/test_manual_fan_ctrl_probe.py` (17), `windows/tools/test_ec_watch.py`
(3) and `linux/lightbar/test_probe_6005.py` (4) — **40 tests, none of them
executed by CI**. A green pipeline proved three of the four compile, because the
cheap tier's `check_python_syntax` `py_compile`s the `windows/tools/*.py` and
`ec/tools/*.py` globs, and it ran none of them. `tools/run-tests.sh` is the one
command now: `bash tools/run-tests.sh` discovers every `test_*.py` under the
repository, runs each in a fresh interpreter, and exits non-zero on any failure.
`tools/README.md` is its documentation.

**The finding is what the runner had to be built around, and it is a real one
rather than a style choice.** Both `windows/tools` suites install a fake `ecrw`
into `sys.modules` with `setdefault`, and the two fakes are not the same shape:

- `test_manual_fan_ctrl_probe.py:38-40` — exports `Ec` only, which is all
  `manual_fan_ctrl_probe.py:63` imports.
- `test_ec_watch.py:86-89` — exports `Ec` and `EcError`, because
  `ec_watch.py:42` does `from ecrw import Ec, EcError`.

In one shared interpreter, whichever suite imports first wins that
`setdefault`, and the second one dies. Measured, on a scratch copy of
`windows/tools/` with the probe's suite renamed `test_aaa_probe_first.py` so it
sorts first:

```
$ python3 -m unittest discover -s "$scratch" -p 'test_*.py'
    from ecrw import Ec, EcError
ImportError: cannot import name 'EcError' from 'ecrw' (unknown location)
----------------------------------------------------------------------
Ran 18 tests in 0.383s
FAILED (errors=1)
```

18 rather than 20 because unittest synthesises a single `_FailedTest` for the
module that failed to import, so the `ec_watch` suite's three tests never
collected. The same copy under `bash tools/run-tests.sh "$scratch"` passes all
20, one interpreter per file.

**So both suites pass today only because `unittest` discovery sorts
`test_ec_watch` before `test_manual_fan_ctrl_probe`**, and the fuller fake wins.
That is an ordering accident, nothing asserts it, and a rename that reorders
them turns it into a red build the moment a runner exists to run it. It was
latent precisely because nothing ran them.

*(**Correction, 2026-09-24, issue #186.** The account above is what was measured
and it stands as history; the accident it describes is now defused. There is one
`windows/tools/ecrw_fake.py` carrying `Ec` and `EcError` over the real
`ecrw.py`'s whole surface, both suites `install()` it, and each still supplies
its own behaviour on top — `test_ec_watch.py`'s `EcError` *is* the shared one,
its `FakeEc` is its own, and the probe suite still patches `probe.Ec`. The
reproduction above re-run unchanged, on a scratch copy with the probe's suite
renamed `test_aaa_probe_first.py` so it still sorts first, now prints **Ran 20
tests / OK**; the mirror-image rename, `test_ec_watch.py` sorted last, also
prints **Ran 20 tests / OK**; and the shipped order does too. Two renames are
the honest bound of what a scratch copy can demonstrate, and the structural
argument is the one file both suites import. `ecrw.py` itself is unchanged — the
fake mirrors its surface, it does not replace it.*

*(**Scope note, 2026-09-24, added at merge.** The correction above holds for the
two suites that existed when #186 was written. Three suites merged in parallel
with it — `test_ec_validate.py`, `test_system_id_probe.py`,
`test_charge_target_test.py` — still install their own `ecrw` fakes with
`setdefault`, so the ordering hazard is not retired for them, and the
"insurance rather than load-bearing" reading of the per-file loop below does not
yet hold. Moving those three onto `ecrw_fake.install()` is an open follow-up.)*

Two consequences, and the second is the one to carry forward:

1. **The runner isolates per *file*.** Per-directory isolation would not have
   helped — both suites live in one directory — and neither would leaving it to
   discovery order. That reason is written into the script at the loop. With the
   correction above it is insurance rather than the thing keeping a red build
   away: the loop is what the *next* suite to reach for a fake of its own gets
   for free, and the comment at the loop now says so rather than only saying
   "do not simplify".
2. **The durable fix is to reconcile the two fakes**, and it is deliberately not
   done here: it edits two currently-passing suites this issue did not ask
   about. It is a follow-up, and the isolation is what keeps it from biting
   meanwhile. **Where that deferral ended:** issue #186 is that follow-up, and
   the reconciliation is `windows/tools/ecrw_fake.py`. The isolation stayed, as
   belt-and-braces.

**What this does and does not buy.** The suites are now one command a human or a
future gate can call, and the runner is shellchecked for free by the existing
`check_shellcheck` (which is why it is a shell script — `check_python_syntax`
globs only the four component `tools/` directories and would not have covered a
root `tools/*.py`). **It is not CI: no gate and no workflow calls it**, because
`agent-gates.sh` is copied from `ElDavoo/agent-pipeline` and the pipeline token
has no `workflow` scope. `docs/agent-pipeline.md` carries the one function and
one `gate` line that wire it in, and the runner prints its own scope on every
run so the deferral is visible in the output. The runner is **0.77 s** here
(0.76–0.77 s over five runs) against a cheap tier §14e records at 5.9 s on a
GitHub-hosted runner — two different machines, and the ratio rather than either
absolute is the argument that the wiring is cheap.

None of the 40 tests is hardware evidence. They mock device discovery, file
opening and ioctls against hand-built fixtures, and the two `windows/tools`
suites fake `ecrw` precisely so no Windows box is needed: no EC is opened, no
register is read back, and no HID node is touched. What they establish is that
the tools behave as specified on those fixtures, and nothing about the machine.

### 16a. A blank press at the mark prompt was a whole capture, not one window (2026-09-25, issue #474)

`windows/tools/ec_watch.py`'s mark prompt substituted `mark N` for an empty
label, and that label is one `parse_mark` cannot read: one unreadable mark
withholds the whole run rather than one block, because block attribution
rests entirely on the labels. The prompt now refuses a blank press, records
nothing, says so and asks again, and the contract is pinned in that suite's
`BlankMarkTests` rather than left as an accident of a `strip() or` default. The
grader is unchanged — the refusal was correct, and the place a mark should not
be invented is the prompt. Written up in
[ec_watch-marks.md](../windows/tools/ec_watch-marks.md), which also names the
two other tools still carrying the substitution.

## 17. The `main-ec-002` cluster is one 393-byte routine, counted 42 times over (2026-09-23, issue #179; id corrected by #253 and by the 2026-09-24 re-derivation)

**The id in this section's subject has been wrong twice, and every version of
the error is in the record.** Issue #179 asked about the cluster the committed
census called `main-ec-002`. Issue #4.3's census regeneration (#133 / #238)
renumbered it to `main-ec-003`, which is what this section's subject read until
the census was re-derived on the merged tree (2026-09-24), which put it back at
`main-ec-002` — `xdata-clusters.csv` row 3, 43 addresses and 4,966 references
over `0x0460`-`0x09CE`, which is this block. The cluster that had taken the old
`main-ec-002`'s meaning has itself split in that re-derivation. Its 28-address
half is row 4, `main-ec-003`, over `0x045C`-`0x1C3A`. Its 11-address half is
row 12, `main-ec-011`, over `0x045E`-`0x1F07`. The four-address remainder is row
50, `main-ec-049`. None of the three shares an address with this block. The ids
move because `xdata_register_map.py:1027` numbers clusters by size, which is the
hazard `ec/annotations/xdata-register-map.md` §5 records for its own table. The
wrong ids are left standing where they quote issue #179, per §4a;
`ec/tools/check_cluster_citations.py` is what holds the rest of the tree to the
census.

Issue #179 asked what the `main-ec-002` cluster is: 43 addresses, 4,965
references, 126 touching functions (the issue's figures; the census as
re-derived on 2026-09-24 records 4,966 and 127 for the same membership), nine of
the ten busiest addresses in the
firmware, and an empty `named_addrs` column. **Three of the issue's framings did
not survive the tree, a fourth number in it is a misreading of a column, and
the corrections are the substance of the answer rather than a footnote to it.**
The full reading is `ec/annotations/xdata-06c2-06db-timers.md`; this is the
summary and the corrections.

**1. The block is one routine, and the cluster's numbers are the artefact, not
the finding.** `bank1:0x8001`-`0x8189` is 393 bytes ending in a `ret` at
`0x8189`, and `ec/decompiled/index.csv` splits it into 42 exports whose sizes
sum to exactly 393. The boundaries tile the run with no gap and no overlap, 16
of the 42 listings hold exactly one instruction, and **all 42 `.c` files
decompile the whole body** — every one of them carries the final `0x08A8` block,
which starts at `0x8171`, 361 bytes past the smallest listing's own boundary at
`0x8008`. `8001.c` and `8018.c` differ in 12 lines out of 135 once the plate
comments come off.

`xdata_register_map.py` counts references by searching the decompiled C for
address tokens, and has no way to know 42 of those files are the same 393
bytes. Measured, per address: **4,784 of the 5,202 census tokens for the
sweep's 46 byte addresses come from those 42 overlapping exports — 92%**, and
4,642 of the 4,989 the 43 cluster rows sum to, **93%**. Per address the gap is
starker than the total:

| | census `refs` | direct `MOV DPTR,#addr` sites in the image |
|---|---:|---:|
| `0x0843` | 168 | **1** |
| `0x0844` | 168 | **1** |
| `0x06D6` | 148 | **1** |
| `0x0706` | 160 | **1** |
| `0x08A8` | 170 | **2** |
| all 43 | 4,989 | **345** |

**So "nine of the ten busiest addresses in the firmware" is a statement about
the export, not about the bytes.** None of those five is among the ten busiest
once the 42-fold count comes out. The largest of the 43 by direct sites is
`0x080D` at 78, and 74 of those are in the PD image.

**2. Seventeen of the issue's twenty "unnamed" functions already had rows, and
the three that did not were the only ones that had not.** `8008`, `8010` and
`8017` are the work; all three were `seed_basis=call-target`, `size=1`,
`annotated=no`, and each is now a row whose comment says in its own words that
the one-instruction boundary is the call-target scan's hypothesis — the wording
`8001`-`800F` already used. The 42 rows describe slices of one routine and that
is not fixed here: correcting the boundaries needs `--mode rebuild-project`,
which writes the 7 MB database and cannot merge alongside anything else.

**3. `bank1:0x1984` and `0x198A` are annotated bank-switch forwarders, and
their 45/126 and 41/126 figures are the `callees` name-frequency column**,
which `xdata-register-map.md` §6 already documents as over-counting depth. The
place worth reading was their targets, and that is where the finding is:
**`0xC1E7` is `bank0:test_1664_bit0`, already annotated, and `0xC10C` has no
exported function in any program.** `0x06D9` is the one countdown in the block
whose progress hangs off those two calls, and one of the two is a routine this
repository has not exported. That is the highest-value follow-up the block
hands back, and it needs a function seed.

> **Superseded by #255.** "`0xC10C` has no exported function in any program"
> was a census artefact, not a fact: it was unseeded, not undecodable. The
> twelve bytes at file `0x0C10C` decode by hand to **seven instructions in
> twelve bytes**, with no `MOV DPTR` in them at all — a thunk that `lcall`s
> `0xC0C9` and restates that callee's answer in R7. Those bytes are in **bank 0**,
> and the bank is load-bearing rather than incidental: `0x1984` is
> `mov DPTR,#0xc10c` / `ljmp 0x1100`, and the common-area stub at `0x1100` is the
> one `bank-call-audit.md` §2 records as selecting bank 0, so the `imm16` is
> resolved after the bank switch. Eight rows in `ghidra-variables.csv` and the
> `bank1,19A8` row in `ghidra-functions.csv` had read a forwarder's `imm16`
> against **bank 1** and called `0xC10C` and `0xC118` operand bytes inside
> bank-1's `FUN_CODE_c0a8`, and `0xC1E7` bank-1's `latch_0498_bit1_or_bit3`;
> all three are different code in bank 0, and those rows now carry the bank-0
> reading with the withdrawn version beside them. So the first
> gate is state-dependent and reads **bits 1 and 2 of `0x3202`**, not `0x06D9`
> and not anything else in the block, and the two gates of `0x06D9` sit in two
> different corners of the XDATA map. The wrong claim is left above rather than
> edited away, per §4a. The *export* is still outstanding and is not claimed
> here: `ec/ghidra/README.md` has why a new listing cannot be added from a
> runner, so `0xC10C` has no listing under `ec/decompiled/` and this rests on
> the twelve bytes and on `0xC0C9`'s own annotation.

**The reading itself.** 37 of the 43 are countdowns the same twenty
instructions walk over, 6 are what four of them do at zero, and the two the
clustering cut into `main-ec-123` and `main-ec-201` (`0x06C6`, `0x06CD`) are
countdowns the same routine decrements. The block is gated twice — on
`0x0440` (43 read sites, no direct `MOV DPTR` writer, value not established —
its one writer is the CODE-table scatter at bank1 `0xA530` that stores `0x00`
to it, `ec/annotations/xdata-0440-readers.md` §5) and on the two
predicate returns — with a third gate that is a `ret` rather than a test:
`0x06D6` is the only reload, loading 9 at zero and returning early otherwise,
so it is the rate control for the lower two-thirds of the sweep and the only
byte in the run whose period is legible from the code. 43 new rows in
`registers.yaml`, all `present-untested`, all named `XDATA_<addr>`.

**A correction to the record, in both directions.** The reload search was first
taken to find no writer outside the sweep for `0x06C2 0x06C3 0x06C5 0x06D6
0x0706 0x06D8 0x06DB 0x085B`. **`0x06D8` does have one** — `bank1:0x9800`, the
`mov A,#0x0A` / `movx @DPTR,A` in the body at `0x976E` that also loads `0x070B`
and `0x044C` — **and ten more addresses belong in the list**: `0x0621 0x0635
0x0638 0x0639 0x063A 0x06F3 0x0843 0x0844 0x0981 0x0982`. Taking the union of the two
methods that can find a writer at all, 17 of the 43 have none outside the sweep.
The wrong version is left in the annotation file rather than deleted.

**And the direction-classifier defect turns out to reshape the unit this issue
was scoped to**, which is why it is a follow-up and not this diff.
`ec/tools/xdata_register_map.py:277` accepts a comparison as an assignment
because `ASSIGN` at line 138 contains `"="` and `"== 0x12".startswith("=")`.
Regenerating the census with a one-line guard that rejects a bare `=` followed
by a second `=`: **833 references leave the `write` column across 210 of 1,172
addresses**, `0x08A8` goes from 84 reads / 44 writes to **126 / 2**, `0x0843`
from 84 / 42 to **126 / 0**, and **`main-ec-002` goes from 43 addresses /
4,966 references to 44 / 248** — a shape and not a row, since the guard's
output is not the committed census. Neither figure is right yet — both still
carry the 42-fold count above — but an issue scoped to "read `main-ec-002`"
would be scoped to a membership its own prerequisite changes. (The id in that
quoted scope is `main-ec-003` in the census as it stood when #253 corrected it,
and `main-ec-002` again since the 2026-09-24 re-derivation, per the correction
above; and the 44 / 248 it lands on is the size and reference count the old
`main-ec-002` carried, which is a coincidence of two numbers and not of a
membership — that block has since split, and `xdata-06c2-06db-timers.md` §6a
says so at the table.) The
issue's own "42 of its
comparisons are `==`" is a second, independent misreading:
`xdata-register-map.md` §4.1 defines `read+write` as "an `=` target whose
right-hand side names the same address", so those 42 are 42 read-modify-writes,
and per §1 all 42 come from the overlapping exports.

**What a clean result means, precisely.** The committed files carry no
structural fault, and every count in the new annotation is reproducible from
the committed image — `check_register_counts.py` recomputes all 129
`static_refs` keys the 43 rows add and fails on a mismatch, and
`gen_xdata_symbols.py --check` confirms the regenerated 144-row symbol table.
What that establishes is arithmetic about the decompiled text, not behaviour:
**no register was read, written or read back, no live test ran, and nothing
here is a `confirmed-*`.** A countdown the code decrements is not yet a
counter the EC keeps.

Deliberately **not** widened to: the direction-classifier fix, the census's
42-fold double count, the 42 wrong function boundaries, a name or a purpose for
the block or for any of the 43 bytes, or a live write to `0x0440` or any byte
in the sweep. Each is named in `ec/annotations/xdata-06c2-06db-timers.md` §6
and §8 with what it would take; the read-only procedure for a human with the
machine is that file's §7, and it is written down rather than run.

*(**Update, 2026-09-24, §17a.** The Linux half of that procedure has now been
run on the machine, read only. "Written down rather than run" held when this
section was written and is left as it was.)*

### 17a. The sweep, sampled live: `0x06D6` cycles once a second, and the host window cannot see a third of the block (2026-09-24, issue #257)

Run on the GM7MG7P from a local session at the owner's request, read only,
through the ECMG window with `ec/tools/ec_timer_capture.py`. The procedure,
the commands and the full result are in
`docs/hardware-tests/xdata-06c2-06db-sweep.md`. The four captures are
`evidence/ec-watch/2026-09-24-*`. Linux, no vendor service, AC, idle as far as
the EC is concerned. What the operator was doing on the machine was not recorded.

**`0x06D6` is a live ten-step countdown with a 0.997 s cycle, and the sweep at
`bank1:0x8001` runs every ~99.7 ms.** Across three captures (2 ms, 10 ms and
0.5 ms sampling; 120 s, 300 s and 60 s), every one of 4815 changes to
`0x06D6` is either a `-1` step or the `0 -> 9` reload the listing puts at
`0x8075`, with no other transition. The step is 100 ms by median (98-102 ms at
2 ms sampling), and the reload recurs every 0.997 s by mean. The code says each
pass changes `0x06D6` exactly once, so the step is the routine's own period, and
the part of the sweep below the `ret` at `0x8074` runs once per cycle. That is
the 10x relation the listing predicts, measured at 9.98. These are the two
numbers §7 of the annotation said no static read could supply.

**The host window maps `0x0000`-`0x07FF` and `0x0C00`-`0x0FFF` only.** A
read-only census of the 64 KiB mapping
(`evidence/ec-watch/2026-09-24-host-window-page-census.txt`) finds every byte of
`0x0800`-`0x0BFF` and of `0x1000` upward reading `0xFF`. That extends the
`0x0A40`-`0x0A5F` observation in §4g to whole pages, and it is consistent with
those pages being unmapped, not a claim about their contents. It costs this
block 16 bytes: `0x0890`, 13 of the 25 post-return countdowns, `0x080C` and
`0x0985`. It also costs **both of `0x06D9`'s gate bytes, `0x1664` and
`0x3202`, so the annotation's §7 step 3 cannot be run through ECMG as written.**
Every `registers.yaml` row in those ranges is in the same position, and §4e
says the vendor's `ECRW` path uses this window too.

**In the idle captures, none of the 24 in-window countdowns other than
`0x06D9` held anything but zero, so no rate could be measured from them.** They sat at `0x00`
for 300 s on idle Linux. The committed `2026-09-18` AC plug-in summary and the
Windows profile-switch capture show `0x06D6` moving and no other sweep byte.
That is "not reached on the paths watched", not "not a countdown" and not
absent. `0x0440` held at `0x07`, so its gate was open.

**`0x06D9` held at `0x03` for the whole of both captures that watched it**,
while the pass that reaches its gate ran 301 and 60 times. No decrement is
visible even at 0.5 ms. Either a gate stayed closed, or bank1 `0x982E` (which
stores exactly 3) undid each decrement within 0.5 ms. The in-window state bytes
favour the gate without proving it. `0x04FE` held at `0x00`, and on that value
the only exported jump into `0x9817` (from `0x976E`) needs `lcall 0x198A`, the
`0x1664` bit 0 test, to return non-zero. That is the same call that closes
`0x06D9`'s gate in the sweep. `0x0480` bit 0 set and `0x05F1 = 1` are what
`0x9817` leaves behind. So both readings point at `0x1664` bit 0 being set.
**That is inferred, not read**, and it holds only for the AC steady state
these captures were taken in. The hardware-test doc's §4 states what it
assumes, and the perturbation arm below narrows it on battery.

**Status moved: `XDATA_06D6`**, and after the perturbation and suspend arms
below, `XDATA_06D8`, `XDATA_070B` and `XDATA_06C5`, all to `confirmed-working`. For `0x06D6` it
means the code's model of the byte (decrement, reload with 9, one step per
pass) is what the live byte does. It does not name what the one-second cycle times. The other 39
stay `present-untested`. A byte that held still in a capture is not evidence
about what the EC does with it.

**The perturbation arm loaded two post-return countdowns and measured their
rate.** The owner did four actions at the machine: AC out, AC in, the Fn
power-mode key, and the lid. Marks were stamped from sysfs and the hotkey
device (`evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv`). **The AC
unplug loaded `0x06D8` and `0x070B` with `0x0A`**, 0.38 s before Linux saw the
AC go. Both then stepped down once per 1000 ms (median), 10.00 times the
`0x06D6` step, and all 24 decrements landed in the same 10 ms sample as a
`0x06D6` reload. That is the early return's prediction for a post-return byte,
measured. The in-window bytes of `0x976E` and `0x9817` changed the way their
`ghidra-functions.csv` annotations say, down to `0x0490` becoming
`(old OR 1) AND 0x77`. No pre-return countdown was loaded by anything, so the
100 ms half of the ratio is still unseen. The Fn key arrives as `KEY_F14`
(scan `0xb0`) and moved nothing the capture watched: `0x0751` held `0x10`. The
lid did not suspend the machine, because logind treats it as docked.
`XDATA_06D8` and `XDATA_070B` move to `confirmed-working` on the same narrow
scope as `0x06D6`. Both notes said "decremented on every pass", which is wrong
for a post-return byte, and each now carries a correction beside the original.

**It also reopens which gate holds `0x06D9`.** For 66.5 s on battery,
`0x05F0` and `0x0480` show `0x9817` was not entered, so its store of 3 did not
run. The only other writer found stores 5. `0x06D9` still stayed at 3 through
66 passes that reached its gate. So a gate was closed, and a rewrite by a known
writer is excluded for that window. But the pointer at `0x1664` bit 0 above came
from `0x9817` being live on AC, and on battery that premise fails. Which of the
two gates was closed on battery is not established
(`docs/hardware-tests/xdata-06c2-06db-sweep.md` §4a).

**Suspend to S3 and resume loaded a third one, `0x06C5`, from `0x00` to
`0x05`** (`evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv`). It then
stepped at the same once-per-cycle rate, all 5 decrements in the same 10 ms
sample as a `0x06D6` reload. `0x06C5` is one of the seventeen addresses the
annotation's §5 lists as having *no writer outside the sweep found by either
static method*. So this is one live instance of the blind spot that list was
always qualified by, and a note now sits beside the row. Across the suspend,
`0x06D6`'s residue was 1 (mod 10) where the awake rate predicts 3, so the sweep
did not run at its awake rate through the gap. How much it ran, a ten-step
counter cannot say. Nothing else watched moved, and still no pre-return
countdown was loaded. `XDATA_06C5` joins the three above at
`confirmed-working` on the same narrow scope, with the same "every pass"
correction.

**What this opens,** each now tracked. A run that loads a pre-return countdown
(#374); idle, AC, the Fn key, the lid and S3 did not, and the pre-return bytes
with known writers are listed in the hardware-test doc's §6. What wrote
`0x06C5` across the suspend (#376). A read path to `0x1664` and `0x3202`, if the
EC has one other than ECMG (#375). `0x0490` bit 3, set at AC plug-in by
something neither annotation covers (live rows on #241). A pass over
`registers.yaml` for every row the host window cannot reach (#377), since a live
read of any of them through this path returns `0xFF` whatever the EC holds. The
Windows arm with the Control Center started and stopped (#378). And handling
`KEY_F14` in the driver, if the mode key is to do anything on Linux.

## 18. The decompiler's variables, measured: most `param_N` are not parameters (2026-09-24, issue #133)

The function names say what the code does. The variable names still say what
the decompiler called them, and issue #133 wanted that swept. Before writing a
row, the counts were measured over the committed 2,708 `.c` files — and the
issue's headline figures are wrong for two of the three families it names.

| family | mentions | distinct names | **declarations** |
|---|---|---|---|
| `param_N` | 8,605 | 11 | **2,232** |
| `cVarN` | 3,436 | 11 | 391 |
| `bVarN` | 8,707 | 14 | 372 |
| `uVarN` | 1,451 | 11 | 218 |
| `sVarN` | 340 | — | 70 |
| `DAT_EXTMEM_NNNN` | 13,967 | 1,099 addresses | n/a (globals) |

> **RE-MEASURED 2026-09-25, issue #263. The table above stands as written, and
> its own method is not reproducible from the committed tree.** The counts are
> right for the export they were taken on; what could not be re-derived is *how*
> they were taken, so the figures above are kept rather than silently replaced.
> The re-measurement, over the export this issue's batch rebuilt, is
> `ec/tools/merge_annotation_shards.py --census` — a committed tool, so the
> numbers below are re-runnable rather than transcribed:
>
> | family | mentions | distinct names | **declarations** |
> |---|---|---|---|
> | `param_N` | 8,391 | 11 | **2,181** |
> | `bVarN` | 8,750 | 14 | 655 |
> | `cVarN` | 3,436 | 11 | 496 |
> | `uVarN` | 1,446 | 10 | 307 |
> | `sVarN` | 343 | 10 | 77 |
> | `pbVarN` | 1,709 | 12 | 7 |
>
> **2,710** `.c` files, of which 1,352 carry a placeholder in the code and 1,338
> declare one. **2,181** declared parameters (the signature's parameter list) and
> **1,601** declared locals (a declaration statement anywhere in the body), for
> **3,723** distinct (file, name) pairs. The two totals are not disjoint: 59
> placeholders are declared twice, once in the signature and once as a local, so
> adding the two lines does not give the total.
>
> **Three differences from the table above, and only one of them is a
> correction.** The `param_N` delta (−51) is the two batches: 86 of this issue's
> 88 rows committed a name in place of a placeholder, the other two are
> `kind=unresolved` and deliberately kept theirs, and the net is smaller because
> committing a signature moves *callers* too — see "The second batch" below. The
> local figures are higher, not lower (`cVarN` 391 → 496, `bVarN` 372 → 655),
> and the reason is the method, not the tree: this census counts a declaration
> statement **anywhere in the body**, because Ghidra emits some locals inside an
> inner block, while a parse of the leading declarations block alone gives 459
> and 586. A few hundred locals live below the top of the body and a reader has
> to name them either way. `pbVarN` appears in the new table and not the old one
> because the old table listed only four families and this one lists every family
> the placeholder pattern matches.
>
> **What is genuinely a correction is that the old figures cannot be
> re-derived at all.** Three methods were run against a pristine checkout of
> this section's own commit (`6ff6c6d2`, the parent of the change that added
> it) and none of them produces 2,232 / 1,725 / 3,957 / 1,950: the signature
> plus leading-declarations parse gives 2,304 / 1,443; the signature plus
> every declaration in the body gives 2,363 / 1,543; and distinct (file, name)
> pairs over mentions gives 2,305 / 1,914. The table is not withdrawn — it was
> measured, and the mention column still matches this census to within the two
> batches — but **its declaration column is no longer re-derivable from any
> committed input**, and a figure that cannot be re-derived is worth less than
> one a tool prints. That is the correction: quote `--census`, not the table.

**Two corrections to the issue, in place.** It reports "3,410 `param_N`" — 3,410
is the `cVarN` figure; `param_N` is the largest family at 8,605 mentions. And
its "~600 `uVarN`" is 1,451. Its `DAT_EXTMEM` figure of 14,399 is close as a
mention count but is 1,099 **distinct addresses**, which is the number that
matters: naming an address is one piece of work however often it is read.

**The number that sizes the job is declarations, not mentions.** 3,957 distinct
(file, variable) pairs — 2,232 parameters and 1,725 locals — across the 1,950
of 2,708 files that have any placeholder at all; 758 files (28.0%) have
nothing to rename. So this is roughly 2x the existing 1,769-row function sweep,
not "roughly an order of magnitude" as the issue estimates. That is the
difference between a plausible single PR and a fan-out, and it is why the first
batch below is bounded on a predicate rather than a round number.

### The second batch: a predicate the listing decides on its own, and what it decided

Issue #263 took the next batch on the family §18 above called "a fact rather
than a reading": every function whose own listing's **first** instruction that
touches the accumulator A is a `movx @DPTR, A`, so A still holds whatever it
held on entry. The boundary is measured by
`ec/tools/merge_annotation_shards.py --census`, and it is 88 functions
(bank0 55, bank1 17, pd 16) declaring 187 `param_N` between them.

**The predicate is a fact about A and not about a caller, and the difference
turned out to be most of the batch.** 37 rows are `kind=param` — a value that
arrives — 49 are `kind=artifact` where the decompiler promoted a constant or a
register copy to a parameter slot, and 2 are `kind=unresolved` with no name.
The cause is structural rather than a judgement call: Ghidra's function
boundaries on this firmware cut through straight-line code, **53 of the 88
listings contain no `ret` at all**, and inside a block A is produced by the
instruction before. `bank0,0xF079`–`0xF118` is one constant-writing block carved
into twelve entries and only two of them take a value that arrives.

`docs/findings/a-store-predicate-batch.md` has the batch, the three defects the
adversarial verification stage caught (all of which would have been confident
sentences about the wrong instruction), and the four `lcall` limits the census
turned out to have. Two of those belong in this section because they bear on
what §18 already claims:

- **A recorded `lcall` into the address is not evidence that a caller supplied
  the value.** Every readable caller of the `0xF079`–`0xF118` run sets A
  explicitly immediately before the call — a constant, a `clr A`, or a register
  copy — which is staging a value, not passing one.
- **The arity question moved again, in the direction #238 did not see.**
  Committing 88 signatures moved **28 functions this batch never annotated**:
  11 now pass more arguments (+25 declared parameters) and 17 pass fewer (−17).
  The census's net −78 against the −86 the renames account for is exactly that
  difference, which is why the per-address XDATA movement is six addresses and
  not 88. **The question is not settled here**; this is the second batch's data
  point, recorded and not resolved.

These counts move when the export is regenerated — a symbol rename changes a
mention count without changing a single declaration — so the declaration column
is the one to quote and re-measure, and the method is a structural parse of each
function's signature and locals block rather than a regex.

### Most of them are not parameters, and the repository already said so

45 rows in `ghidra-functions.csv` discuss a `param_N` by name, all of them
`hand-decoded` and all citing their `.asm`, and in most the prose concludes the
placeholder is a decompiler artifact:

- `bank0,0x901C` — "*param_1 is a pointer the decompiler invented, not a 8051
  calling convention*"
- `bank1,0x8DBC` — "*The decompiler's param_1 is the R7 result of 0x1984, not
  an argument passed in*"
- `pd,0x3A0E` — "*the C's return param_1 & 1 makes it look like a test on a
  parameter and is not what the instructions do*"
- `bank0,0xF141` — "*param_1/param_3/param_2 names do not correspond to the
  registers the instructions use*"

A sweep that gave every `param_N` a confident semantic name would manufacture
false precision on exactly the rows this repository has already flagged as
misleading. That is the `CLAUDE.md` §4 failure in a new place, and it is why
`ec/annotations/ghidra-variables.csv` carries a **`kind`** column rather than
only a `name`: `param`, `local`, `return` (the decompiler rendering a callee's
R7), `artifact` (it invented one), and `unresolved` — the listing does not say,
so the placeholder stays. The first batch is 39 `artifact`, 11 `return`, 5
`param` and 4 `unresolved` out of 60 rows across 46 functions, and that
distribution is the finding: **83% of these placeholders are not incoming
arguments at all** — 39 the decompiler invented, 11 a callee's R7 — and only 5
are a value arriving in A.

### The 4 `unresolved` rows, and why leaving a placeholder is an answer

`bank1,0xBD20`'s `param_1` corresponds to nothing in the instructions. The
listing calls 0x8898 and then tests the two returned bytes with a single
`orl A,B` at 0xBD26; the decompiler split that one test into
`cVar1 != 0 || param_1 != 0`, and which of A or B the second identifier is has
not been established. `bank1,0xC4AF` is the same shape with `orl A,B` at
0xC4B5, and its existing annotation already says "the decompiled C's param_1
does not appear anywhere in these instructions". Naming either would be a
confident sentence about a register the code does not touch, so both rows carry
`kind=unresolved` and **no name**, and the export still shows `param_1`.

That is a real result, not an unfinished row, and it is why `unresolved` is in
the vocabulary: a mechanism that costs nothing to say, and a check that refuses
an `unresolved` row carrying a name anyway.

### The mechanism, proved before 45 rows were written

Ghidra persists decompiler variable names in the program's database, so
`HighFunctionDBUtil.updateDBVariable()` on a `HighFunction` from a decompile
makes the *next* decompile emit the name. Proved end to end on the issue's own
worked example before anything else was written: `bank0,0x0EA2` was renamed
`param_1` → `ticks`, the real export-only build was run, and
`ec/decompiled/bank0/0EA2.c` came back with `ticks` in the signature and the
body and with no `param_1` anywhere in the code. The rename survives the
round-trip through the database into a *second* decompile, so the design holds
and the fallback in the plan — renaming on the `HighFunction` inside
`ExportDecompile.java` instead — is not needed.

`ApplyAnnotations.java` opens its `DecompInterface` **lazily**, only when the
program has at least one matching row, because a JVM start is ~15 s and the
BIOS and Windows builds have no variable layer at all.

### Unmatched variable rows are counted, not fatal — and the reason is the build itself

The opposite of function rows, and deliberately so. A function row is keyed on
an address, stable forever. A variable row is keyed on a decompiler
placeholder, which `--mode rebuild-project` **consumes**: once the name is
persisted, `param_1` no longer exists in the project, and rebuilding from the
same CSV would find nothing to rename. Making that an error would mean a
documented, routine operation breaks the build.

The concern behind the fatal rule — a stale annotation outliving the thing it
named — is still enforced, by a check that is stronger rather than weaker:
`--check` requires the committed `.c` at that `(scope, addr)` to contain the
row's `name` **and** to no longer contain its `key`. Bidirectional, so a typo'd
name and a consumed key are both caught, and it measures the output rather than
the script's own report.

One subtlety that made the check wrong on its first draft: the scan is over the
**code**, not the whole file. A function's own plate comment is allowed to name
the placeholder it is explaining — `0x901C`'s says "param_1 is a pointer the
decompiler invented" — and a whole-file check would refuse the very rows whose
comments say what the placeholder was.

### The variable layer is not a back door for `registers.yaml`

A variable row names a decompiler variable, never an XDATA address. Naming
addresses stays with `gen_xdata_symbols.py` and `registers.yaml`, and the
`status:` discipline behind them. Two locks: `--check` refuses any `name` that
appears in `xdata-symbols.csv`, and `ApplyAnnotations.java` refuses a `pd`-scoped
row whose name is an EC register name — the PD image has its own XDATA map
(`ec/annotations/lightbar-bat-flow.md` §2), so an EC register name there is a
first-class overclaim whatever else the row says.

### Two defects this surfaced, neither fixed here

*(Correction, 2026-09-24, issue #260: defect 1 is now fixed, below. The heading
is left as it was written — it describes the state at the end of the change this
section documents, and rewriting it would hide that the oracle was broken for
the whole time between.)*

1. **`--self-test --oracle` raises `NameError`.** It is documented in
   `ec/ghidra/README.md` as the acceptance check for the whole EC pipeline, and
   `self_test()` calls `opt_in_ghidra_oracle(args, work)`, which does not exist
   in the module — 32 functions are defined and it is not one of them, with a
   single repository-wide hit at the call site. The flag passes every other
   assertion and then dies. Nothing in CI invokes it, which is how it has been
   broken without announcing itself. Reported, not fixed: deciding what the
   oracle should assert about a whole export is its own piece of work, and
   bolting a plausible check onto a broken flag would make it look covered.

   *(Fixed, 2026-09-24, issue #260. `opt_in_ghidra_oracle()` exists and runs to
   completion; the paragraph above is left as it was written, because the
   decision it declined to take — what an oracle asserts about a whole export —
   is still the one not taken. What it asserts now is the two facts
   `ec/annotations/charge-target-derating.md` established by hand at bank-0
   `0xB1F0`, measured on a fresh export into the work directory: the listing
   carries an `lcall 0xbf08` at `0xB200`, and the C carries
   `DAT_EXTMEM_09c7 = DAT_EXTMEM_09c7 + 1;` immediately followed by
   `if (0x3b < DAT_EXTMEM_09c7)`. Both are matched on the address rather than on
   Ghidra's name for the callee — `FUN_CODE_bf08` is what `0xbf08` is called
   before an annotation renames it, and the committed export calls that routine
   `sub_0a4e_against_4d_with_borrow` — so a rename cannot fail the check and
   only a change in the code can. The same run then feeds the helper a copy of
   its own export with each fact removed and requires it to report that one and
   not the other, because a check nobody has seen fail is not a check.

   The "nothing in CI invokes it" is still true, and deliberately. A full export
   is minutes and the cheap tier is budgeted at 0.13 s with no Ghidra and no
   network, so the oracle is a **procedure** with a ready-to-paste block in
   `ec/ghidra/README.md` rather than a gate — the same treatment
   `verify_gap_text.py` got. A green commit therefore still says nothing about
   whether the oracle would pass.

   It reads `<work>/out/` and never `ec/decompiled/`, and pins `export-only`, so
   it cannot mutate the tree it is checking: `opt_in_ghidra_oracle()` does not
   call `write_outputs()`, which opens with `shutil.rmtree(OUTDIR)`. A missing
   or empty `B1F0.c`/`.asm` is a failure rather than a skip, since a silently
   empty export is one of the two states the check exists to catch.

   **On the function count.** The three figures that disagreed here are 22
   (`ec/ghidra/README.md`), 32 (the paragraph above), and 39 by `grep`. The
   measured value was **52** — `grep -c '^def ' ec/tools/build_ec_decompile.py`
   — quoted in both files with the command beside it, so it is re-derivable
   rather than a transcription that drifts again. It was **41** when this
   paragraph was written and moved to 52 with §14i, which is `41 - 2 + 13`:
   `function_size()` and `check_cross_decoder_agreement()` gone, and the
   thirteen that `file_offset()` through `degenerate_sample_problems()`
   replaced them with. In the tree carrying both §14i and §14j it is **56**,
   which is `52 + 4`: §14j's digest and index-pairing functions
   (`committed_c_files()`, `write_c_digests()`, `verify_c_digests()`,
   `c_presence_problems()`), none of which shares a name with the thirteen. The
   two older numbers are left above because they are part of the record of the
   defect; neither was ever a measurement.*
2. **The export was stale before this change.** 203 committed `.c` files still
   said `DAT_EXTMEM_0440` although `xdata-symbols.csv` has named that byte
   `XDATA_0440` since `8a90bc0` (#160) — that commit regenerated
   `xdata-symbols.csv` and not `ec/decompiled/`. Re-running the build here
   catches it up, which is why the diff touches 200-odd files for 60 variable
   names. Reconciling the function layer's own 25-row drift
   (`manifest.csv` `annotations_applied` totals 1,787 against 1,769 rows, with
   `annotations_unmatched` a hardcoded `0`) is separate work; the variable
   counters are read back from `apply-<program>.tsv` from the start so they do
   not start that way.

**No hardware or Windows test is claimed here.** This change is static: the
proof is the regenerated export, and nothing in it observes the machine.

**Merge note, 2026-09-24: applying the variable layer moved the XDATA census.**
When this was merged, `ec/tools/xdata_register_map.py` found the C-level census
down from 1,172 addresses / 14,801 references to 1,171 / 14,792. The branch
had not regenerated the census, so it was not measured here before. The
cause is the mechanism above: applying `ghidra-variables.csv` fixes a
function's signature, and for bank1 `0x9EA1` (`shift_pair_then_sum_and_divide_by_four`,
rows 28-31) that removed an argument at its call site. `bank1/E100.c` now calls
it with four arguments instead of five, and the dropped one was
`DAT_EXTMEM_0390`, the census's only reference to `0x0390`. Nine references
moved in all (`xdata-register-map.md` has the list). The instructions are
unchanged. The census's own caveat already covers this: a zero is "not found by
this method". But this is the first time an *annotation* has lowered the
census. So the open question is whether a variable row may change a caller's
arity, or whether ApplyAnnotations should rename without committing the
signature. The pins moved to the measured values, and nothing here settles
that question.

**Settled, 2026-09-24 (issue #259).** The question above is now decided, and
the answer is that a variable row **may** change a caller's arity. The note
above is left standing as written; this is the correction beside it, per §4's
pattern.

**What the nine actually are.** None of the seven addresses is gone from the
machine code. All of them still carry their `mov DPTR,#addr` site or sites in
`ec/firmware/GMxMGxx_11.800`, counted with `trace_xdata_refs.sites_for()` and
split per image exactly as `check_register_counts.py` splits it. What moved is
the *spelling*, because the census is a token pattern
(`xdata_register_map.py`'s `occurrence_re`: `DAT_EXTMEM_([0-9a-fA-F]{4})` plus
the names in `xdata-symbols.csv`) and cannot see an address the decompiler
spells as arithmetic or over register names. Per-address account, with the
`.asm` site counts and the citations:
`ec/annotations/xdata-register-map.md` §7.1.

**The dropped argument was not a parameter.** `0x9EA1` reads R1, R3, R4, R5, R6
and R7 and never names R2. The call site loaded `0x0390` into R2 —
`E100.asm:72`, a dead store, since `E100.asm:100` overwrites R2 with no
intervening read — and then handed the **address** on as R3:R4
(`E100.asm:73-74`), which `0x9EA1` reads at `9EA1.asm:19` and writes at
`:43`. The fifth argument the decompiler used to promote was an unconsumed
scratch register, so the committed four-argument signature is the one that
matches the listing and the row **corrected** the decompile. `0x0391` is alive
the same way at all three of its sites (`E237.asm:33`, `E100.asm:67`,
`DB0B.asm:101`).

**`0x0390` is a present byte, and it is not absent.** It has a
`registers.yaml` row (`XDATA_0390`, `present-untested`, one EC-side site, no
PD site). `present-untested` is the ceiling and not one step further: **no live
test was run**, and this is static analysis of committed text. `absent` and
`unknown-not-absent` are both wrong for it — the byte is read and written in the
machine code, and its `.asm` site is counted and pinned — because it is a
present byte whose *C-level reference* fell out of one method, which is a
third thing. `xdata_register_map.py --self-test` now asserts the site and the
absent census row together, so a zero cannot read as absence.

**The measurement, which is the part that was open.** The `XDATA_0390` row
makes `gen_xdata_symbols.py` name the byte, so `ApplyAnnotations.java`'s
`createData` now defines it. Re-running the export in the **default
export-only** mode moved no `.c` and no `manifest.csv` row: the export is
byte-identical to the committed tree, the decompiler still renders the pair as
`CONCAT11(r4_value,r3_value)`, and the census does **not** rise. So `ORACLE`
stays at 1,171 / 14,792 and `BUCKET_TOTALS` at `passed-to-call` 543 /
`address-taken` 270, and the census note and transcript in
`xdata-register-map.md` stand as committed. The other outcome the issue allowed
— the decompiler starting to spell `XDATA_0390` at the callee's two `movx`es —
did not happen.

**The rule, in one sentence: a variable row may change a caller's arity, and
that is a correction rather than a loss; the census counts C-level references
and is therefore a lower bound on the machine code; a pin moves only with a
measured reason recorded in the same change; and an address that leaves the
census is "not found by this method" until an `.asm` witness says otherwise.**
It is written in `ghidra/scripts/ApplyAnnotations.java` (comment only — no
behaviour changed), `ec/annotations/README.md`'s Variables section beside "The
rebuild asymmetry", and here.

**The `0x07C9` +1, which is the one that gained.** It is **not** an annotation
effect. Across the #238 merge the only one of the two files the census names for
this address that moved is `ec/decompiled/pd/7B14.c` (21 → 22
`DAT_EXTMEM_07c9` tokens); `EA67.c` and `7B14.asm` are byte-identical, and
`0x7B14` has no row in `ghidra-functions.csv` or `ghidra-variables.csv`, so no
annotation touched it. The added token is `cVar2 = DAT_EXTMEM_07c9;`, and the
old call's first argument, the constant `0x1c`, is gone from the C while
`7B14.asm:233-234` still shows `clr A` / `add A, #0x1c` building it — so by this
repository's own rule (`.asm` right, `.c` a reading) the new C is a *worse*
reading at that argument. The census gained a C-level token that does not
correspond to a new machine access. **What made Ghidra re-render the file is
not recorded in the committed tree** — there is no annotation on `0x7B14` to
point at — and that is the honest limit of the account rather than a mechanism
invented to close it.

**Two pre-existing defects, reported and not fixed here.** `build_ec_decompile
.py --self-test --oracle` raises `NameError` (`opt_in_ghidra_oracle` is called
at line 1583 and defined nowhere in the repository), so the oracle arm cannot be
run. And the committed Ghidra project is owned by `dave`
(`ec/ghidra/project/ec.rep/project.prp`), so `build_ec_decompile.py` fails for
any other user with `NotOwnerException` before it analyses anything; the
export-only run for this issue was made with the owner corrected in the scratch
copy only, and the committed file is byte-identical afterwards. Both want their
own issues.

**Merge note, 2026-09-25, issue #263: the census moved by one reference, and
the pins were already 26 behind.** The second batch above committed 88
signatures, and the XDATA census read over the rebuilt export is **1,171
distinct / 14,819 references** — main EC 13,961, PD 858. Measured against a
pristine checkout of the parent commit as well as against this branch, the two
do not agree about how much of that is this issue's:

| | pin said | pristine `main` | this branch | this change |
|---|---:|---:|---:|---:|
| refs | 14,792 | 14,818 | 14,819 | **+1** |
| main refs | 13,931 | 13,957 | 13,961 | +4 |
| PD refs | 861 | 861 | 858 | −3 |
| `named_in_tree` | 150 | 153 | 153 | 0 |
| `symbol_main` | 146 / 6,060 | 147 / 6,070 | 147 / 6,070 | 0 |
| `BUCKET_TOTALS` read | 8,317 | 8,333 | 8,341 | +8 |
| `BUCKET_TOTALS` passed-to-call | 543 | 538 | 534 | −4 |

**So `xdata_register_map.py --self-test` was already red on `main`** — 26
references and 3 named addresses of drift, found by running it against a clean
checkout rather than against this branch, and it is recorded here rather than
folded into the +1 because it is not this issue's. That is the first time the
tool's self-test has been run on a pristine parent in this repository, and the
policy it was written to test ("a pin moves only with a measured reason
recorded in the same change") needs the parent as much as it needs the change.
The pins are now set to what was measured, and the dated comment block in
`xdata_register_map.py` carries the two halves separately.

The +1 is the arity effect above, and the six addresses that moved are
accounted address by address in `ec/annotations/xdata-register-map.md` §7.2.
`ec/decompiled/bank1/19A8.c` was stale against its own `ghidra-functions.csv`
row — issue #255's correction landed without a re-export — and this build
caught it up; **measured on its own that file moves no census figure at all**,
so the whole +1 belongs to the 88 rows.

## 19. The map from mechanism to function, and the eleven stale evidence paths it fixed (2026-09-24, issue #136)

`../ec/annotations/subsystems.md` now exists, and the issue it closes asked for
it by that name. The interesting part is not the map.

**The plan's numbers were stale, so the census is measured rather than
transcribed.** Every count in §2 of that document was re-derived against the
committed tree, and five of the figures the plan carried did not survive:
`index.csv` exports 2710 functions and not 2708, `ghidra-functions.csv` holds
1848 rows and not 1769, the common area carries 76 annotated rows and not 22,
`ec/ghidra/xdata-symbols.csv` holds 178 names and not 61, and `registers.yaml`
holds 146 registers and not 29. (1,804 and 43 were this section's own figures
when it was written; issue #134's call-graph tranche added 44 rows, 33 of them
`common`.) The plan also said the 18-row gap between the index's
`annotated=yes` count and the CSV's row count was 1787 − 1769; measured, it is
1866 − 1848, and **18 is unchanged**, because the tree moved on both sides at
once. Had the plan's numbers been copied in, the document's own check would
have failed on the first run.

**The plan's row count was wrong too, in the direction that matters.** It
promised 19 annotation rows and listed 21 addresses: six vector targets, six
table entries, "six banked-target thunks" over a list of five, and four lone
`ret`s. All 21 are exported, unannotated functions, so 21 rows went in. The
arithmetic is worth recording because the plan's own summary used the wrong
number three times; the tree is what settles it.

**The claim that all six table entries reach the `0x1150`-`0x1168` group is
false for one of them.** `0x002B` tail-jumps to `0x05E7`, a lone `reti` one byte
past `0x05E6`, and not into that group at all. The table is 12 `ljmp` entries
interleaved with 4 lone `ret` bytes over `0x0000`-`0x002F`; the six already-named
forwarders hold the eight-byte-stride slots and the other six sit at an offset
those do not use.

**The three one-byte `reti` targets are not split epilogues, and that took bytes
to establish.** `0x052F`, `0x05E6` and `0x05E7` are each a single `reti`. Ghidra's
boundaries cut through straight-line code on this firmware, so the one-byte shape
is exactly what a split epilogue looks like, and three separate facts rule it
out: `0x0528`-`0x052E` is a run of `ret`s after a function ending in a `ret` at
`0x0527`; the byte before `0x05E6`, at `0x05E5`, is the timer1 handler's **own**
`reti`, since `0x05B6`'s body is 48 bytes and ends there; and `0x05E7`'s
predecessor is `0x05E6`. `ec/ghidra/reassembly.csv` records all three as `match`
and `verify_reassembly.py --check` reports 0 disagreements over 45,624
instructions, so this is a fact about the bytes. **The rows are still
`type: unresolved`**, and the map cites them with an `[unresolved]` marker,
because "the vector target is one `reti`" is not "int0 and serial 0 are
unimplemented" — whether the EC services those sources is a question about the
interrupt-enable registers, which none of those addresses reads.

**Eleven rows of `ghidra-functions.csv` were citing files that do not exist, and
the existence check now reaches all of them.** All eleven are `common` scope and
all eleven cite `ec/decompiled/bank0/` for a function the common-area de-dup (§12)
had already moved to `ec/decompiled/common/` — 22 dead paths, invisible until now,
because every existing gate asks whether an `evidence` cell is *named* and none
asked whether the path resolves. They are fixed here. This is the delete-the-row-and-
the-file hole the annotations README describes, reached from the other side: not
a row deleted with its file, but a file moved out from under a row that stayed.

**Correction to how they were found, and the gate change it produced.** This
paragraph first said the citation check *found* all eleven. It did not, and the
figure was doing more work than the tool behind it could carry. The existence
check iterated only the rows `subsystems.md` cites — 61 citations, 59 distinct
`(scope, addr)` keys — and five of the eleven (`common` `0x0C7A`, `0x0EF3`,
`0x10F1`, `0x11C2`, `0x383A`) are cited nowhere in the map, so the check as
written could not have flagged them. They came out of the same de-dup audit that
turned up the six the map does cite. The check is now widened from the cited
rows to every row of the file, which is what makes the claim true going forward,
and which a paragraph arguing that no gate asks whether an evidence path
resolves should have had from the start. The eleven were real either way; what
was overstated was the tool's reach, from 1,848 rows down to 59.

**Two smaller reconciliations, so the next reader does not have to redo them.**
`common` `0x1207` is a bare `ljmp 0x1100` and `common` `0x0512` is a two-byte
`ajmp 0x0003`; both are second instances of a name that already has a row
elsewhere. `0x1204`-`0x1207` is one six-byte `mov DPTR,#0xBF62` + `ljmp 0x1100`
thunk split in two by a call-target frame, with the second half inheriting the
first's name. `0x0512`'s name is right about where it goes — it really is a
second path to the int0 forwarder — but it exists because the byte scan found
`01 03` there, not because the vector table does. Whether either is a genuine
second copy is not established by the bytes alone.

**Also measured while writing it, and left alone here.** `pd-index-callers.csv`
has five rows of which **four** are `status: unresolved`, not all five; the fifth
found literal index loads. `ec/annotations/bank-call-audit.md`'s own note that
the BL51 stub at `0x1100` is reached by "350 of the 403 trampolines in
`0x1150`-`0x1ABC`" is a range-restricted count from the exporter and is not the
same measurement as the map's: over the whole export, by shape, 290 functions
are a `mov DPTR,#imm16` + `ljmp` pair and 282 of those name a BL51 stub (261 to
`0x1100`, 21 to `0x1114`), of which **82 are annotated**. Both numbers are
right about different sets; the map publishes the one it can recompute.

**The export-only build for this issue was made with the Ghidra owner supplied
on the command line** (`JAVA_TOOL_OPTIONS=-Duser.name=dave`), the same workaround
§18 describes and for the same reason: the committed project is owned by `dave`
(`ec/ghidra/project/ec.rep/project.prp`), so `build_ec_decompile.py` fails for
any other user with `NotOwnerException` before it analyses anything. No project
file was edited and the committed one is byte-identical afterwards. The gate that
would have caught this at the time is still not written.

**One row of `index.csv` changed for the wrong reason, and the reason is a
pre-existing defect.** 22 rows move `seed_basis` to `annotation`, and 21 of them
are correct: those are exactly the 21 new `common` rows, and `seed_rows()`'s
`STRENGTH` table puts `annotation` (0) ahead of `vector` and `vector-target`
(1), so a hand-written row is meant to take over as the recorded basis. The 22nd
is `pd` `0x0012`, and it should not have moved. The PD image's own vector table
is the six standard slots — `discover_vector_table()` over the PD bytes returns
offsets 0, 3, 11, 19, 27 and 35 and **no `0x12`** — so `seed_rows()` builds no PD
seed at that address at all. The value it records is borrowed, because
`ghidra/scripts/ExportDecompile.java`'s `readBasis()` keys the basis map on the
address string alone and never on the program, so a function at `0x0012` in the
PD image reads whichever program's row was written for `0x0012` — here the EC
common area's. The old value (`vector`) was borrowed the same way; this change
only swapped which program's answer it borrowed. It is the same class of
address-space confusion as §12, one row wide. **The fix is to key `readBasis()`
on `(program, addr)`**, and it is not made here because it would restate the
basis column across the whole index and wants its own verification.

## 20. What grounds a name, and what a group is (2026-09-24, issue #135)

The write-up is `docs/findings/name-basis-and-groups.md`; this is the summary.
Two separable things landed, and the second is deliberately weaker than the
first.

**`name_basis` is on all 1,848 EC rows and all 788 BIOS rows**, and it is the
first column in this repository that records what a *name* asserts rests on,
as opposed to `basis`, which records where the *comment* came from. Mandatory
and non-empty like `evidence`, refused by both build tools on the same
grounds: a name that asserts a mechanism with no recorded footing is a claim,
not a finding. EC distribution: 1,562 `code-shape`, 136 `ec-register`, 90
`register-map`, 52 `unresolved`, 4 `abi-symbol`, 4 `mixed`. (1,530 / 134 / 83 /
49 were this section's own figures; issue #134's 44 call-graph rows graded 33
`code-shape`, 7 `register-map`, 3 `unresolved` and 1 `ec-register`, and issue
#255 moves one cell from `code-shape` to `ec-register` for the reason the next
paragraph gives — re-run `grade_name_basis.py --report` for the tree's own
numbers.)

**One cell moved when #255 merged, and the rule is what moved it.**
`bank0 0xC1E7` `test_1664_bit0` was `code-shape` because `ec-register`
requires the address the *name* cites to be in `registers.yaml` as well as
present in the row's own `.asm` as a `mov DPTR,#imm` — and `0x1664` had no row,
so the second half could not be earned. #255 adds `XDATA_1664`, so both halves
hold and the committed cell is now `ec-register`: 1,562 and 136 rather than the
1,563 and 135 this section's distribution above carries without #255. (The
pair 1,529 and 135 was that same cell measured on the pre-#134 tree of 1,804
rows; #134's 44 call-graph rows and #255's one cell move the two counts
independently of each other.) `grade_name_basis.py --check` is what caught it,
which is the drift half doing the one job it exists for.

**The grading rule is deliberately asymmetric** — strongest footing actually
traceable to a committed input, else `code-shape` — and it is implemented in
`ec/tools/grade_name_basis.py` against the row's own committed `.asm` rather
than against its name, with `--check` re-grading the committed column so the
two cannot drift. The default points at the weak end on purpose: grading by
name-regex would overclaim, and grading the other way would under-claim.

**The footing has to come from the name, and one place got that wrong.** The
first grader also matched the `BL51`/`EDK` patterns against the row's
**comment**, and reported 57 EC and 43 BIOS `abi-symbol` rows. Measured, 101 of
those 105 `abi-symbol`/`mixed` rows took the token from the comment alone and
four from the name — the four `bl51_bank_select_N` stubs in `common`, which are
now the whole EC population. `load_dptr_88f0_tail_jump_1114` is the clearest
case: every token of the name describes two instructions, and its
`abi-symbol` grade came from a comment that itself says 0x1114 "is not present
in this decompiled tree, so what it does with DPTR is not decoded here." A
grade a prose comment can supply is not a grade of the name and is
unfalsifiable for the same reason rule 4 reads the name and not the comment.
The rest reclassify to `code-shape`, which strengthens rather than weakens the
argument above: the default points at the weak end on purpose.

**The issue's worked example is a negative finding, and that is the point.**
`bank0 0x0EA2` is **not** renamed to `delay_polling_0a56` and **not** graded
`code-shape`: 0x8E/0x8F are TCON.6/TF1, decoded and corroborated two ways, so
the grade is `register-map`. Getting there needed something the plan did not
anticipate — the name says `timer1` in *words* and never writes `0x8E`, so a
rule keyed on hex literals alone grades it `code-shape` and loses the decode.
**This is also where the "Reading left out" was taken as written:** no mass
renaming, which is the issue's own "or in the row" reading and avoids
re-symboling Ghidra to churn every generated header for a change the column
itself captures.

**The `pd` finding is enforced, not conventional.** A `pd`-scoped row may not
be graded `ec-register`, because the ITE8850-PD image is a separate 8051
program with its own XDATA map — a `MOV DPTR,#0x07E2` there is not a reference
to the EC register at 0x07E2. That is the third lock on the same door, and it
fires *independently* of the "must cite a registers.yaml address" rule: a pd
row naming an address that is in the map would pass that rule and still be an
overclaim. Verified by poisoning a pd row and watching both fire.

**The grouping layer is in, and it is honest about being weaker.** 1,848 EC
rows and 788 BIOS rows gain a `group`. The BIOS is module-first as the issue
says it should be — 666 of 788 rows are `group_basis=module` — and the EC is
seeded from the `type` column (33 `bank-switch` rows, 6 interrupt vectors) with
call-graph clustering for the rest: 1,016 rows in a connected component, 456
`ungrouped`. (1,804 / 866 / 576 and 30 bank-switch rows were this section's own
figures. Two separable things moved them, and quoting the old pair beside the
new one without saying which is which is the mistake the `--check` ratchet
exists to prevent: issue #134's 44 rows account for +56 components and −26
`ungrouped` on their own, and the `group_functions.py` correction below for
another +94 and −94. `--report` prints the tree's own numbers.)

**A `callgraph` group is a connected component, not a subsystem, and the tool
says so.** The largest holds 327 of the 1,848 rows, and three components are of
50 or more (`callgraph_bank0_0EA2` 327, `callgraph_bank1_1738` 321,
`callgraph_pd_0003` 303) — and every one of the three is a single scope, which
was not true of any of them before the correction below. That is a real
structural fact and a poor subsystem boundary, so the groups are named
`callgraph_<scope>_<addr>`, their size is in every row's comment, and `--report`
names any component of 50 or more. The `<scope>` is the component's **dominant**
scope, and holding it to that is a check: a component can span scopes because
the common area is reachable from any bank, so naming the token after the first
member described whichever row the union-find emitted first, and four of the
nineteen names were wrong that way — a 323-row component that is 316 bank1
rows, and a 145-row component that is 144 rows of the **separate ITE8850-PD
image** presenting as `common`, which is the same conflation the `pd` grade
rule above exists to stop. `--check` now refuses a `callgraph` name whose scope
token is not the dominant scope among its rows. **456 `ungrouped` is "not found
by this method", never "these have no subsystem"** — the same discipline
CLAUDE.md puts above every other rule, and the reason `ungrouped` is in the
vocabulary at all — **for 440 of them**. The other 16 were found by the method
and then cut by the proxy rule, which is a different reason and says so in their
comments and in `--report`'s split line; see
`docs/findings/group-proxy-populations.md`.

**The banking caveat is inherited without softening, and it is structural.**
Nothing in an `lcall` names a bank — bank0→bank1 and bank0→bank0 are the same
three bytes — so the graph never joins bank0 to bank1. The rule is not a filter
applied afterwards: the union never sees a cross-region edge, so there is no
cluster to reject later. Measured over the committed listings, bucket A = 999,
B = 1,474, C = 450 using `audit_call_targets.py`'s own `bucket_of()`; 27
cross-region edges are counted and reported, never merged. Every run prints
those numbers, so a small group count cannot read as a topology. (A = 973 and
B = 1,428 were this section's own figures, measured before issue #134's tranche
annotated 33 more of the common area — see below for why the claim needed more
than a recount.)

**And "never sees a cross-region edge" was true of the edges and not of the
nodes, which issue #134's tranche turned into a real failure rather than a
latent one.** A `common`-scoped row is one function both bank images carry, so
a bank0 caller and a bank1 caller that both reached it were two halves of *one*
node — and that node is a cross-region endpoint whatever the edges around it
are. With 43 of the common area annotated the committed groups happened to
pass: the one component that spanned both banks had a single `bank0` row in it
and that row was seeded, so the `callgraph` refusal had nothing to refuse. The
44th tranche row was enough — 673 rows in one component, and
`group_functions.py --check` refused it by name. The endpoint a bank caller
uses for a common-area target is now a per-region proxy node (`PROXY_SCOPE` in
`group_functions.py`), which keeps the relation the edge does carry — the
`bank0` functions sharing a common helper stay connected — and drops the one it
does not. That 673-row component splits into 327 `bank0` rows, 321 `bank1`
rows, 14 more in small single-scope components and 11 that no longer reach the
minimum size — and the separate ITE8850-PD program comes back together, which
is the clearest sign the split was the right one: its 187 `pd` rows were spread
over six components, two of them (`callgraph_pd_0180` at 144 `pd` rows and
`callgraph_pd_0050` at 26) holding most of it, and they are one
`callgraph_pd_0003` of 303 now. `cluster()`'s docstring carries the argument
and `--self-test` carries a fixture for it, because a check that had been
passing for the wrong reason is the failure mode this repository keeps warning
about. **The refusal was not weakened to accommodate the tranche**:
`cross_bank_groups` is unchanged, and the committed file now has nothing for it
to refuse for the right reason. **The 27 above is the smaller of the rule's two
discard populations** — the proxy cut 196 bank→common edges as well, and
`--report` now prints both and splits `ungrouped` by reason; see
`docs/findings/group-proxy-populations.md`.

**Nothing here is a behavioural claim, and no live test ran.** A group says
which routines are connected in the call graph, not what the EC does with them.
No hardware is reachable from a GitHub-hosted runner. The 2,636 comments were
not read by hand to infer subsystems: anything the seeds and the graph do not
support stays `ungrouped` rather than getting a plausible label.

**A plate-comment line moved a pinned citation, and the check caught it.**
`ec/annotations/xdata-0860-census-sites.csv` pins **line numbers** into the
committed `.c` files and `check_site_census.py` holds them, so the new
`name_basis:` line shifted 6 of its 7 sites and the check went red with the
right diagnosis. The refs were recomputed from the tool's own
`census_occurrences()` rather than blanket-shifted, and **only the line numbers
moved** — same sites, same per-site counts, same 17 occurrences. **A
plate-comment edit is not confined to the plate**, which is the one thing worth
knowing before the next annotation change.

**Two bugs are worth recording because both were silent.** The first grader's
`DPTR_IMM` pattern was case-sensitive and the listing spells `DPTR` and `0x`,
so XDATA detection was completely dead — and the report showed
`ec-register=0` across 1,804 rows, which reads as a *finding* rather than as a
broken pattern. It was caught only by the grader's own `--self-test` fixture.
A zero meaning "the method is broken" and a zero meaning "the method found
nothing" are the same number, which is the whole reason that self-test exists.

The second is the same shape with nothing silent about the number.
`grade_all()` wrote the computed grade straight over the `name_basis` key and
`check()` then compared that key **with itself**, so the drift half of
`--check` could not fail: hand-editing a committed grade to anything passed,
and the line it printed was reporting a tautology. The check that exists to
stop the column drifting from the rule was itself unable to notice it drift.
The committed cell and the computed grade are now separate keys, and
`--self-test` carries a fixture that poisons one and asserts the other refuses
it. It was found the unremarkable way: edit a committed cell and see whether
the gate that claims to hold it objects.

## 21. A `pd` caller's edge was attributed to a `common` row it never reached (2026-09-25, issue #471)

The write-up is `docs/findings/pd-common-address-attribution.md`; this is the
summary. One behavioural line in `cluster()` and the fixture that catches it.

`cluster()` recorded a caller's scope against an annotated `common` row
**before** it decided which branch the edge took. That was right for the
`common`→`common` case it documented — both ends are `common`, so the edge is
joined directly but the row was still reached from outside the banks, which is
what keeps it out of the 26 — and wrong for the other branch, because an
address carrying both a `common` row and a row of the caller's own scope is two
functions in two programs. A same-scope `pd` join takes the **`pd`** row as its
endpoint; `ec/decompiled/pd/0C7A.asm` is not `ec/decompiled/common/0C7A.asm`,
because the ITE8850-PD image is a separate program with its own address space.
The `common` row beside it was not an endpoint of that edge, and marking it
reached was the same conflation the `pd` grade rule and the dominant-scope
naming rule exist to prevent, in the bookkeeping rather than in the grouping.
The reach now moves onto the two branches that actually end at the `common`
row — with an explicit `scope == "common"` guard on the same-scope join, which
is load-bearing rather than cosmetic: dropping it takes `reached_only_by_bank`
from 26 to 35 and fails `--self-test`.

**No published figure moves, and that is the strongest claim available here.
`--report` is byte-identical before and after** (26 / 196 = bank0 126, bank1 69,
pd 1 / 36 targets / 115-81 / 456 = 440 + 16), both group CSVs regenerate
byte-identical, and `--check` still passes. **"Latent today" is the claim and it
is the one to preserve** — the defect is real, it is confined to branches that
did not target the `common` row, and no figure depends on it yet, because no
`common` row a `pd` caller reaches is also reached by a bank caller. Do not
upgrade that to "harmless": nine addresses carry both a `common` and a `pd` row,
and 38 `pd` listings have no `ghidra-functions.csv` row at all, so both halves
of the condition are properties of the current annotation state rather than of
the rule. The `common` rows at `0C7A`/`0EF3`/`10F1` keep their `ungrouped` /
"Not found by this method" comments — this change removes a reason they *could*
have been counted on and supplies no new one.

**The fixture the issue asked for cannot fail, which is the part worth keeping.**
"Assert a `pd` caller does not put the row in `reached_only_by_bank`" passes
against the very bug it is written for, because `reached_only_by_bank` is a
subset test that already discards any non-bank scope — a `pd`-only reach is
invisible to it either way. The reach is a set, so what discriminates is a
**bank** reach on the same row: `['bank0','pd']` is not a subset of the banks,
`['bank0']` is. The fixture is a `common` row and a `pd` row at one address with
both a bank0 caller and a `pd` caller, and it fails on the unfixed tool
(`[]`) and passes on the fix. `common 0x11C2`, which has no `pd` row beside it
and therefore a `pd` edge that genuinely targets it, keeps its
`['common','pd']` attribution and is pinned separately. A program-boundary rule
for `pd`→`common` edges is still open — `region_of()` has no vocabulary for one
— and the 7-edges-and-1-proxy ratio in
`docs/findings/group-proxy-populations.md` is unchanged.

## 22. The whole-block bracket was filed under whatever block the run named (2026-09-25, issue #475)

The write-up is `docs/findings/dump-pair-block-attribution.md`; this is the
summary. It is a reporting and attribution change: **no fixture was added, no
capture was re-read, and no register status moved.**

**`--dump-pair` is grouped by block now, the way `--dump` already was.** §6
stamps every dump with the `<value>` of the block it belongs to, and
`report_dumps()` has grouped on it since #457: on a `--block 0x10` run handed
the `a0` dumps it prints `belongs to block 0xA0, not the block under test
(0x10) -- not read for §4.6 here` and takes no readback. `report_dump_pairs()`
took the pairs with no block argument at all, so in the whole-day form §6
documents — one plain invocation over all three values — every window above the
section carried a `block:` line and the three brackets below it carried nothing.
A pair is filed by `dump_pair_block()`, which asks `dump_block()` per side
rather than re-implementing it: both names agreeing is `name`, one name and a
silent other side is that block's (`one-name`), neither is the `--block`
fallback (`flag`, so a pair that names its own block is never re-filed under
the run's flag), and **two names that disagree is an input error — named,
printed, not compared, and exit code unchanged**, on the same-file-twice
precedent, because the window report and the §4.6 readback the operator also
needs still get printed.

**A mis-filed bracket is not visible in its body, and that is the finding.**
The two pairs in `0751-isolation-run-multi-block/` read the same two bytes in
the opposite order (`0x10 -> 0xA0` and `0xA0 -> 0x10`), and the committed tool
prints **byte-identical** whole-block brackets for them apart from the file
names: `16 address(es) compared`, four `not covered by this pair`,
`other addresses that differ (1)` naming `0x0751` — *as an address only*, the
values being in the §4.6 readback, a different section. So the calibrated
claim is not that grouping makes a mis-filed bracket show up in the output; it
is that **the group line above it and the refusal to compare are the whole of
the attribution, and without them there is none.** The grouping is what makes
that attribution exist. `test_both_blocks_pairs_are_grouped_in_one_unscoped_run`
pins the identity, so the property cannot be lost quietly, and the scoped case
asserts on the label and on what is absent rather than on a value — there is no
value-level difference to find. Printing the differing addresses' *values* in
the bracket would have made it self-evident, and is not done: it changes a line
`differing_addresses()` reads flat and an existing test pins, and it cuts
against the "no third category" invariant in `report_dump_pairs`' own docstring.

**The heading is byte-identical** —
`=== whole-block dump pairs (§4.1-§4.3) ===` — and every line inside a pair
body keeps its indentation, because both §4.6 readers in the suite cut the
section on that heading and `group_body()` cuts the bodies on `    {name}:`.
`graded` counts only pairs compared in scope, so a `--block` run handed only
another block's pairs is 0 and the closing summary reports no whole-block
read. **No live run happened and none is implied**: every input is a committed
hand-written fixture and the tool's own output over it, `0x0751` stays
`present-untested`, and no line of this is a §7 verdict.

**Two follow-ups, both named rather than done.** `report_readback`'s
`--dump-pair` hint is still not block-aware — it can point a `--block 0x10` run
at an `a0` file — which is advice rather than a verdict and lives inside the
§4.6 section two tests pin. And a name disagreement stays exit code 0: the
argument is that `--block`/`--wrote` name the value under test for the whole
run, so one of them being wrong leaves no window in the report gradeable, which
is not true of one pair out of three — a change to the exit-code contract rather
than a report fix.
