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

*(One class of correction this section covers has a machine check behind it in
one place, which is a stronger guarantee than the convention alone: §6a's
re-derivation is held to its published figures by
`test_the_census_is_the_one_6a_measured`, and what a re-derivation costs and
what to do about it is
[`xdata-census-rederivation-checklist.md`](findings/xdata-census-rederivation-checklist.md).
The convention is unchanged by it — a superseded figure still stays visible with
the correction beside it.)*

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

**The withheld banner counted the run's own windows while the headers above it
numbered the day's.** A `--block` run that withheld anything printed "2 of the
2 window(s) above were not graded" directly under two headers numbered 4/8 and
5/8 — a denominator false about the windows printed above it, on every
attachment issue #380's §6 workflow produces. The banner now names both (the
block's 2 and the capture's 8); the whole-capture wording is byte-identical,
since there the two denominators are one number. Write-up:
`docs/findings/0751-grader-withheld-count-denominators.md`.

**The same sentence was also unqualified on a `--block` run, which withheld
nothing and so matched none of the cases above.** A clean block is graded
whole, so a `--block` run over one value of a day printed "consistent with the
static prediction" for a capture it had read 3 of 8 windows of — and, one
branch up, "That contradicts the static prediction" with nothing scoping it.
The closing summary now declines the capture-level comparison there too, and
still makes it over a `--block` run whose block *is* the whole capture.
Write-up: `docs/findings/0751-grader-block-scope-claims.md`.

**A `--block` run refused by a mark in no block said nothing about it, and the
exit code was the only sign.** The one refusal `--block` does not narrow — a
label the parse could not place, which is fatal for the whole run because
attribution rests entirely on the labels — was disclosed in the census and
nowhere else, so a run could print `intact`, print the clean closing sentence
and exit 1 with no sentence joining the two. The closing summary now prints the
reason in the place the withheld count would be, whether or not anything was
withheld. Write-up:
`docs/findings/0751-grader-block-scoping.md`.

**A window in no block was checked by one of §3's three per-window rules and
graded anyway.** `check_block_marks` iterates `block.windows`, and a window
`assign_blocks` could not place was passed to it by nobody — so a stray restore
two consoles spelled differently, or that one console never recorded, was named
by the census and then printed in full in the same confident format as a result,
counted in `graded`, and the run exited 0. The two agreement checks now reach
windows in no block as well; `void` does not and says why, since it is defined
over a block and a stray has none to be void in. The refusal is window-scoped
rather than run-wide, so a `--block` attachment is still decided by its own
block. Write-up:
`docs/findings/0751-grader-unplaced-window-checks.md`.

**And a window the run read is not automatically a window of a value under
test.** A mark in no block opens a window that grades — its rows are real and
there is no other arm to mis-file them under — and it is a window of nothing,
because a label is the only thing that attributes one. A plain unscoped run over
a day with a stray mark in it therefore reached the bare `else` and printed
"consistent with the static prediction" over a set that is not the whole
capture's windows of anything. The closing section now counts those windows
beside the unreadable-mark note and declines the capture-level comparison over
the rest — and on a run that also withheld a window, states the movement over
the graded windows that are a window of a value under test rather than over all
of them; the exit code is unchanged. Write-up:
`docs/findings/0751-grader-unplaced-window-scope.md`.

**And the same run, with something moving, scoped nothing at all.** The count
above is over the windows, not over the arms, and `3blocks-moved/` — the only
committed set where a byte moved — has no unattributed graded window, so no
committed run reached the combination. One `0x0784` row inside a block's write
window puts them together: the movement line printed with no denominator over
all 8 graded windows, 2 of which the count directly above had said are a
window of no value under test, and a whole-capture claim under that. The
`moved_groups` branch now states its scope where nothing was withheld and no
block was selected. It cannot narrow to the windows that belong to a value
under test, because `moved_groups` is a union of group names and carries no
window identity — the same row moved into an unattributed window leaves the
output byte-identical — so it names all 8, says the 2 are part of it, and
declines the capture-level comparison for the attribution reason rather than
the withheld reason. The attribution underneath is unchanged: scoping is not
retracting. Write-up:
`docs/findings/0751-grader-moved-unplaced-scope.md`.

**§3's three unlabelled mark rounds were a fourth class of mark, and the block
model had no place for them.** §3's command block asks for six mark rounds per
block and says so in its own `--seconds 240` paragraph, and only the three that
name a write had a label the grader could read: a stage round is the bare word,
`parse_mark` required a word followed by a space, so `settled`, `held` and
`watch over` came back `(None, None)`, went to `unplaced`, and
`unplaceable_marks` refused the run — exit 1, and a day taken as the runbook
prints it half graded. The three are now boundary roles carrying no
`0x0751=` value, filed against the block the control arm opens, so a block
reads `settle, control, hold, write, watch, restore` and `--block` selects six
windows. Boundaries are optional rather than required: a three-mark capture
grades as it always did, and what a block without a `watch over` costs — its
write's window runs into the restore — is stated in §3 and visible on the
`roles` line rather than checked. The refusal message now quotes all six forms
and takes the count from the tuple. Write-up:
`docs/findings/0751-stage-mark-labels.md`.

**Those 76 tests ran nowhere.** `grade_0751_isolation.py` had no `--check` and
no `--self-test`, so it was absent from `check_ghidra_tooling()`'s tool list —
and absent from it *and* without a mode, the loop's `*)` default would hand it
flags it does not have. It grows the `--self-test` entry point every other gated
tool has, and the two lines that wire it in are prepared at
`docs/ci/agent-gates-0751-self-test.patch` rather than landed; until a human
lands that patch, the suite still does not run per commit. The suite is not a
coverage claim:
it is a dozen refusal policies, each one a gate between a human's hardware day
and a wrong §7 call. The 76 is this merged tree's: 74 on the branch point
(`db6d7d2d`), 2 added by this branch, and none since — #530's
unplaced-window-scope cases predate it. Write-up:
`docs/findings/0751-grader-self-test-gate.md`.

**The grader dropped the probe's "the run ended early" row, and a 5-second arm
graded as a 30-second one.** `read_capture` skips every `#` row so an operator
can annotate a capture by hand, and `manual_fan_ctrl_probe.py`'s
`except BaseException` writes exactly such a row when a run stops — so the one
record that an arm did not reach its hold was the one row nothing could see.
The restore is in a `finally`, so its mark lands either way and the block reads
`intact`: the capture is short a *hold*, not a mark, and the void check has
nothing to notice. Over `multi-block/` with that row in one block's write
window, the report was `block 1/2: intact`, all six windows printed,
"consistent with the static prediction" — exit 0, a false green by the tool's
own standard. A row that can be placed is now charged to the block whose window
it fell in, withholds that block's windows and exits 1, and a section above the
windows names the row, the window and the block — printed whole under
`--block`, so a `--block 0x10` attachment over a day whose `0xA0` block crashed
still passes, which is the scoping §6's per-block command line needs. A row
that cannot be placed (no readable timestamp, none before the first mark, or a
window in no block) refuses the run, on `unplaceable_marks`' argument. The row
keeps its `#` prefix and gains a timestamp, so a hand `#` annotation is still
skipped — pinned byte for byte against the unmodified fixture — and the tag is
a second spelling of the grader's, equal by a case in the probe's suite and by
its `--self-test`. Six new grader cases, two new probe cases, and the probe's
own crash case rewritten: it asserted `rc == 0` over this capture. No register
status is in question. Write-up:
`docs/findings/0751-early-exit-row.md`.

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

**The `0x166A` half closed 2026-09-25 (issue #267);** the paragraph above is
left as it was written. `0x1665`, `0x1666` and `0x166A` now carry
`registers.yaml` rows — `XDATA_1665`, `XDATA_1666`, `XDATA_166A`, all
`present-untested` — with 6, 2 and 3 direct sites, all reads, and the bit
map in each note. `check_register_counts.py` reproduces all three from the
image. The other two thirds of the gap are untouched: `0x0743` bit 1 still
has no entry, and the `0x851B` stub run is still the gate on dating the
capture.

**And the question `0x07D3` was opened for has an answer this section did
not have: the ASL reads `GFID`.** The walk above could say the EC wrote four
distinct values and stop there. It can now be said which consumer
distinguishes them, and the answer is two consumers that disagree about how
many values matter. `Method (SMRW, 1)` at `dsdt.dsl:50764` compares GFID
against `0x07`, `0x05`, `0x03` and `0x06` (`dsdt.dsl:50772`, `50799`,
`50826`, `50854`), and each comparison picks a different pair of EC register
blocks, jointly with `PDIN` (4 bits at `Offset (0x74C)`,
`dsdt.dsl:52213`): GFID 7 → `ACPB`/`ACSB`, 5 → `ACPC`/`ACSC`, 3 →
`ACPD`/`ACSD`, 6 → `ACPE`, each arm also naming a 32-bit overlay. So on the
ASL side the two-bit select is genuinely four-way and chooses a register
*bank*. On the firmware side `0x94D0` collapses it: it tests for GFID == 3
alone and gives every other value the same seed pair, so there the select
behaves as a two-way choice. Neither corrects the other — they are
different consumers of one byte.

**The two-consumer count above is corrected here rather than edited** (issue
#267, fix round 1): there are **three** consumers of the byte in the committed
tree, and the third distinguishes *more* values than either of the other two —
so the answer is not two disagreeing about how many matter, it is two plus a
third, and the third is the finer-grained of the three. The vendor service
reads `0x07D3` outright:
`windows/decompiled/v3.1.39.0/GCUService/MyECIO/MyEcCtrl.cs:164`,
`AcpiModel.Read(GetType().Name, 2003, ref Data)`, and `2003 = 0x07D3`.
`GetSku()` (`:158-190`) masks the byte with `0xF0` and switches the high
nibble — `0x30`→`GN20_GPU_SKU.E3`, `0x40`→`E4`, `0x50`→`E5`, `0x60`→`MaxQ`,
`0x70`→`E7`, `0x80`→`P0`, `0x90`→`P1`, anything else `NA` — and
`IsHeroProject()` (`:192`) keys off `sku == GN20_GPU_SKU.MaxQ`. This is a
third *path*, not a restatement of the two above: it reaches the driver
through `AcpiModel.Read`, not the WMI `InvokeMethod("SMRW")` at
`WMIEC.cs:331-343`, and it reads the byte itself rather than a buffer the
select picks.

Four of those seven names are the four values the EC writes, in the same
order: GFID 3 / 4 / 5 / 7 → E3 / E4 / E5 / E7. The one the service calls
`MaxQ` is `0x60`, the value `SMRW` tests and that neither committed method
finds a writer for. The service's `ECSpec` name for the byte is
`ADDR_ModuleID`, defined as `2003` at
`windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs:389`,
`v3.1.6.0/ECSpec.cs:389` and `v3.9.18.0/Define/ECSpec.cs:389` — live code that
`GetSku()` reads, so the ASL's `GFID` and the service's `ADDR_ModuleID` are one
byte under two vocabularies.

**The "each comparison picks a different pair of EC register blocks" clause
above is retracted too**, and not only in the word "blocks": the `GFID == 0x06`
arm selects the single buffer `ACPE`, so "pair" was wrong for one arm of the
four. The three arms it does describe are pairs.

**The open question, restated with the SKU mapping in view (issue #267, fix
round 1).** What GFID 3 means to the GPU is still not answered by any of the
three consumers, and nothing here claims it is. What the third consumer adds
is that the three read one byte at three *widths* — the ASL's 3-bit `GFID`
field (`dsdt.dsl:52251-52253`), the service's `0xF0` mask, and `0x94D0`'s
high-nibble XOR — and that they do not quite coincide: the service's mask
includes bit 7, which the ASL's field list leaves unnamed. So the field being
a GPU-SKU selector is established in the *service's* vocabulary, from a
seven-value consumer; whether the GPU reads it that way, and what GFID 3 buys
it, is what
[`gpu-tgp-07c4-07d7-door.md`](hardware-tests/gpu-tgp-07c4-07d7-door.md) is for
— still **not run**, and nothing here reports an observation from it.

**The paragraph above is corrected here rather than edited** (issue #267, fix
round 1, 2026-09-25): it called the seven targets "EC register blocks" and
said the select "chooses a register *bank*". Two false negatives are retracted
with it: that the seven targets are not *declared* anywhere in the committed
inputs, and that `SMRW` "has no caller anywhere in the disassembly, so what
invokes it is not in the committed inputs". The committed tree contradicts
both, as the citations below show.
The seven are declared: `Name (ACPx, Buffer (n))` with initial contents at
`dsdt.dsl:50383` (`ACPB`), `50387` (`ACSB`), `50391` (`ACPC`), `50396` (`ACSC`),
`50401` (`ACPD`), `50406` (`ACSD`) and `50411` (`ACPE`) — 8 bytes for the first,
second and seventh, 12 for the other four. What `SMRW` does with one is a copy
in each direction, not a register access: `RWFG == 0xAA` stores `WRBF` (a
0x60-bit field of `Arg0` at offset 8) into the selected buffer and
`RWFG == 0xBB` lays a `CreateDWordField` over it at the caller's `REOF` index
and returns that DWord. So the select picks one of seven ASL buffers, not a
register bank; the seven carry five distinct initial patterns (ACPC matches
ACSC and ACPD matches ACSD byte for byte) and not one of the five, nor either
shared four-byte prefix `50 50 5F 00` / `78 78 A5 05`, occurs anywhere in
`ec/firmware/GMxMGxx_11.800` — the ASL's own values, not bytes read back from
the EC by anything committed. The caller is
committed too: `WMIEC.cs:331-343` opens a WMI `ManagementObject` on
`AcpiTest_MULong` (`ACPI\PNP0C14\1_1`), takes
`GetMethodParameters("SMRW")` / `InvokeMethod("SMRW", …)` and reads `Return`,
its `SMRW_CMD_READ = 187` / `SMRW_CMD_WRITE = 170` (`:23-31`) being the `0xBB`
and `0xAA` the ASL tests, and `windows/native/ACPIDriver.sys.analysis.md:328,400`
records the driver's `SMAPCTable` entry for `SMRW` and the 0x80-byte buffer it
marshals where the other twenty entries take integers. So the consumer is the
vendor service through the WMI ACPI driver, not something outside the tree.

Two asymmetries fall out of the pairing above and are recorded rather than
smoothed over: GFID 4 is written by the EC and tested by no arm, and GFID 6
is tested by an arm and written by nothing either committed method finds.
What makes GFID 3 special to the GPU is still open, and

[`gpu-tgp-07c4-07d7-door.md`](hardware-tests/gpu-tgp-07c4-07d7-door.md) is
the written procedure for it — marked **not run**, and nothing here reports
an observation from it.

**What is *not* established, corrected** (issue #267 fix round 1): the two
retracted negatives above are both replaced, and the claim that survives is
narrower than either. Not established is what the EC does with the buffer the
select lands on -- the copy crosses the ASL boundary, and nothing committed
shows the other end of it. Established, and not in doubt, is who invokes
`SMRW` and what it addresses. The two asymmetries above are unaffected and
stand.

**2026-09-25 (issue #264): the first of those is now closed, and the chain
is drawn.** `0x09EA`/`0x09EB` have carried `registers.yaml` rows
(`XDATA_09EA`/`XDATA_09EB`, both `present-untested`) since this paragraph was
written; the paragraph above is left as it was. Each has three direct `MOV
DPTR` sites, all EC-side and none in the PD image, and exactly one direct
writer — `0x96F8`/`0x9700` in `0x96AD`, copying `0x0745`/`0x0746` when
`CTGP_DB_CTRL` (`0x0743`) bit 0 is set. The one computed-`DPH` site aimed at
the `0x09` page is `0x83D6`, whose `DPTR` is bounded to `0x0990`-`0x09BE` and
so cannot reach them. That closes the four-hop GPU dynamic-boost path end to
end — the service's power-mode write, `0x96AD`, `0x83FF`, and the ASL that
publishes `CPUA * 8`/`DBAP * 8` to `NPCF.ATPP`/`NPCF.AMAT` — as one drawing
in `ec/annotations/ec-09e9-09eb-sites.md` §4, cross-referenced from
`ec/annotations/ec-07c4-07d5-sites.md` §3a.

**What the 2026-09-23 capture does and does not establish about it, which is
the second half of that issue.** It does not establish that the tail of the
chain ran, and it does not establish that it did not. `0x07D4` and `0x07D5`
have no rows in that file, but the file watched `0x0700`-`0x07FF` and so has
no observation of `0x09EA`/`0x09EB` — the "already equal" hypothesis has
nothing on either side of its comparison — and it is a sweep-based change log,
so a value held between two sweeps is not written down either. One thing it
does settle, from the committed `.asm` rather than from itself: for the
`0x07C4 = 0x28` state the compare at `0x8460` is not reached at all, because
`0x8459` jumps to the copy first, so "already equal" is not a reachable
explanation for that state. A third route the two-hypothesis framing skips:
`0x83FF` returns at `0x8405` (`0x080F` non-zero) or `0x840D` (`0xB9D8` returns
non-zero) before touching `0x07D4`, `0x07D5` or `0x07C4` at all, and neither
of those two bytes has an entry or is in the capture's window. **No `status:`
was promoted and none should be**: a byte that did not move is not evidence
the EC ignores it. The follow-ups this opens are `0x09E9`'s second writer,
`0x83D6`'s entry point, `0x080F`, `0xB9D8`, and a watcher window over
`0x09E9`-`0x09EB` — all carried in `ec/annotations/ec-09e9-09eb-sites.md` §6,
and the last of them recorded as a gap in
`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`, whose `WATCH` set covers
`0x07C4`-`0x07D7` and `0x0743`-`0x0746` and no `0x09xx` address, so the
procedure as written cannot separate the two readings.

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
arbitrates. **45,500 of 45,643 instructions re-encode to the exact bytes in
the image (99.69%), with no function in disagreement.** 2,580 of the 2,711
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

*(2,707 to 2,711 rows, and 2,710 to 2,714 listings, with issue #267's four
seeded bank0 routines 0xC278, 0xC2C2, 0xC33C and 0xC4E7. The 0xC278 seed lands
inside what was one function, so it splits that function in two rather than
only adding: 0xC26E keeps its row at 10 bytes and 0xC278 becomes a function of
its own, which is why the movement is +4 and not +3. That is where 45,624
becomes 45,643 and 2,576 becomes 2,580. The five rows involved -- those four
plus 0xC26E, whose listing text moved and so had to be re-measured -- carry
`assembler` `sdas8051 02.00` for the same reason the two above do, and the
report was *not* regenerated in full to get them: `--report` rewrites every
row, and a full re-run under `02.00` moves 52 outcomes that have nothing to
do with this issue and would replace the pinned baseline §14g and §14h measure.
The five were spliced in from a `02.00` run of `--emit-csv`, so their values
are the tool's, and `ec/ghidra/README.md` records the splice.)*

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
**The 1,920 above is §14f's figure, measured on the tree carrying issue #136's
rows, and it went stale in the passes after that — not from anything issue #470
did.** The committed report holds **1,983** rows on this tree: 1,978 before
either issue, +4 for issue #267's four seeded `bank0` routines and +1 for #470's
one `ghidra-functions.csv` row. The sample's backbone is every annotated row, so
both additions land in it. `ec/ghidra/cross-decoder.csv` is the current record
and is regenerated with `build_ec_decompile.py --report`, which prints the
denominator on every run.

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
| EC (`ec/decompiled/`, `ec/ghidra/manifest.csv`) | 2,714 rows, 2,714 distinct `(program, addr)`, 0 dups, 0 short rows | 2,714 / 2,714, same | 4 rows, `functions` agrees with both indexes on every row and sums to 2,714; all `mode` = `export-only` |
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

**2026-09-25 (issue #531): a label that was typed and is wrong is refused the
same way, and with the grader's own rule.** `ec_watch.py --mark
--label-vocab 0751` applies `parse_mark(label)[0] is not None` — the test
`unplaceable_marks` applies — to each label as it is typed, and quotes that
module's `REQUIRED_LABEL_FORMS` back rather than carrying a copy of either. It
is opt-in because `gpu_block_watch.py:59,166` imports that `Marker` and stamps
free-form labels through it; `system_id_probe.py:232` keeps a class of its own
of the same shape, still carrying the `strip() or` default at `:252` (#483,
#484, still open). It promises only that the grader can place the row: a value
the run never wrote still parses, and §3's three-console comparison is still
what catches it. Offline behaviour against a
fake EC; §3's commands carry the flag, and a human at the laptop sees the
prompt. Same file:
[ec_watch-marks.md](../windows/tools/ec_watch-marks.md).

**2026-09-25 (issue #549): the grader is now looked for in three places, and
the strictness is unchanged.** Since #531 the flag read
`ec/tools/grade_0751_isolation.py` by one hard-coded path, over a docstring
arguing the repository layout was not a dependency — a contradiction that
only stayed quiet because §2 never told the operator the file had to be
there, and a directory of tools staged onto a Windows box has no way to create
the path the refusal named. `--label-vocab 0751` now tries `--grader <path>`
(the only candidate when given), then the committed copy, then one beside
`ec_watch.py`; a candidate that is there and will not load refuses rather than
being skipped, so a staged copy cannot paper over a broken committed grader.
The refusal still happens above the CSV and the EC, and now names every place
it looked and both ways to satisfy it. What this settles is *which* dependency
is real, not that there is none: the layout is one of three places, and the
file existing somewhere is the real startup dependency for §3's three
commands. The grader is still loaded rather than copied, so the prompt cannot
drift from the grading. Both grading workflows are supported — the grader is
stdlib-only and reads files, not the machine, so §6's set grades identically at
the laptop or brought back — and §2 of the runbook now says so and lists the
file. Offline behaviour against a fake EC and temp directories; whether a
staged copy is where an operator puts it is a human's step. Same file:
[ec_watch-marks.md](../windows/tools/ec_watch-marks.md).

> **Correction (2026-09-25, issue #748), leaving the paragraph above as it was
> written.** "Grades identically at the laptop or brought back" was true of
> §6's committed set and was not a property of the format: every reader opened
> a capture with no `encoding=`, so a file whose bytes were written in another
> encoding was gradeable on one machine and refused on another. The capture
> format is now **`utf-8`, no BOM**, declared at all thirteen read and write
> sites, so the claim holds for a capture the format wrote and a foreign one is
> refused by name rather than half-decoded. Full argument and the measured
> corpus: [0751-capture-encoding.md](findings/0751-capture-encoding.md).

**2026-09-25 (issue #548): that check is a per-process fact, and a `--csv` is a
per-file one, so the tool now names the marks it is appending to.** `Marker`
checks a label as it is typed; `CsvSink` opens the path in append mode without
reading it, and §3 fixes the three CSVs as one set for the whole run. So a file
can already carry marks this process did not type and could not have checked —
a pre-flag run's, a console started without the flag, a watcher restarted
mid-block, a `manual_fan_ctrl_probe.py` capture — and `unplaceable_marks` is
fatal for the whole run over the whole file regardless. `--label-vocab 0751` on
a `--csv` that already holds MARK rows now says so, names them, and continues:
a warning and not a refusal, because §3's own blocks 2 and 3 are
supposed to find marks already there, and no process can check a mark another
one wrote. The predicate is *marks*, not *non-empty*, so a header-only or a
changes-only file stays quiet and block 1 stays quiet. The reader is
`grade_0751_isolation.py`'s `existing_mark_labels`, loaded by path on the same
load as `parse_mark`, and the grader's refusal, `build_windows` and the exit
code are unchanged. Offline behaviour against a fake EC; nothing here has met a
real §3 run. Written up in
[0751-append-unchecked-marks.md](findings/0751-append-unchecked-marks.md).

**2026-09-25 (issue #718): that notice named one list, and the list was written
entirely on the preflight's side of the disagreement with the grader.**
`existing_mark_labels` is deliberately the lenient reader, so a file of six good
marks and one half-written row printed as seven equally fine ones and the
closing sentence — true, and the only warning — could not say which of the seven
the run would be refused over. The notice now names the mark rows the grader's
own reader takes and the rows it will refuse the file over, each with the reason
from `read_capture` rather than from a rule copied into the prompt, plus what
`unplaceable_marks` reports it cannot place, in that function's own words and
worded as a group verdict (`parse_mark` reads the first `' / '`-separated part
that matches, so a window led by `settled` places over a second console's
unparseable label). The refused list covers all four reasons `read_capture`
raises over — short row, unreadable timestamp, hex that is not hex, a byte the
interpreter's encoding cannot decode — not only the two the issue named, and
names every bad row rather than the one the reader stops at. The encoding half
is reported as the verdict the running interpreter actually produced: measured
UTF-8 here, predicted cp1252 on a stock Windows Python, and the grader is
therefore not encoding-portable. The reader is a fourth name on the same load,
read inside the guard that already refused a grader which will not load, so a
staged copy that predates it is refused by path rather than by an
`AttributeError`. The grader's refusal, `build_windows` and the exit code are
unchanged, and a file the grader takes whole reads as it did before. Offline
behaviour against a fake EC and hand-written rows; no Windows box was reached,
and the notice has not been seen against a real §3 run. Addendum to the same
file: [0751-append-unchecked-marks.md](findings/0751-append-unchecked-marks.md).

**2026-09-25 (issue #749): that notice then described two moments as one, and
it now describes one.** #718 read the `--csv` twice — `read_capture` for the
placement verdict and `existing_mark_labels` for the list printed above it —
and the capture is a file three watchers append to by design (§3 runs one per
console, `CsvSink.row` flushes every row, the lock is per-instance), so a
notice could name a mark its own accepted list did not hold. `existing_mark_findings`
now opens the file once, reads the bytes once and feeds one row list to both:
`read_capture`'s per-row body and `existing_mark_labels`' extraction are
shared helpers it calls, so the strict verdict is the reader's own rather than
a second rule, and `f.encoding` — a third open — is gone in favour of the
failing decode's own `.encoding`, which cannot disagree with it. The file is
still being appended to: a mark landing after the call is still graded later
by the whole-file grading, and the skip rule is still spelled in both readers,
so this is one `open()` and not one function. The open count is asserted
rather than the effect, since the effect is only visible when the append lands.
Offline on hand-written rows; no §3 run and no Windows box. Written up in
[0751-notice-two-moments.md](findings/0751-notice-two-moments.md).

> **Correction (2026-09-25, issue #750 merged on top), leaving the rest of the
> entry as it was taken.** One clause is no longer true: *the skip rule is still
> spelled in both readers*. #750 took the rule out of both and put it in
> `skippable_row`, which `read_capture`, `mark_labels_of` and
> `partition_capture_rows` all call, and moved the open itself into
> `capture_rows`/`normalised_rows` — which `existing_mark_findings`'s one read
> also goes through, so the notice's row list and the readers' own agree about
> what a first field may look like. It is still one `open()` and not one
> function, because the four-field test and the `MARK` branch are three
> deliberate contracts rather than one rule. Everything else above — the shared
> helpers, the `.encoding` from the failing decode, the asserted open count —
> holds as written.

**2026-09-25 (issue #719): a fifth column on the MARK row measured against a
`# provenance` row, and nothing changed.** That notice cannot say which process
wrote a mark, and the ceiling is the format rather than the process — but
implementing either candidate is the *next* step, so this measures instead.
`ec/tools/measure_mark_provenance.py` scans the tree for every writer and
consumer of `ts,MARK,,label` rather than taking a list, and found four sites
the issue does not name: a third `Marker` in `system_id_probe.py`; a fourth
writer in `ec_timer_capture.py` at four sites, under a different label
convention; `test_manual_fan_ctrl_probe.py`'s two lines, the only committed
assertion of an exact column count and so the canary a widened shape trips
first; and `check_capture_claims.py`, which reads every committed capture.
50 committed fixtures holding 247 MARK rows, all four columns, and four
readers called on temp files, **both shapes cost zero** — the readers index
rather than unpack, and the issue's "`row[0..3]` unpacks" is explicit indexing
at `grade_0751_isolation.py:691`, so a fifth column is ignored where the
issue's reading predicts a `ValueError`. (That line number is this paragraph's
own tree, as the rest of it is — #749's split moved it to `:830`, #750's
consolidation to `:1044` and #771's docstring prose to `:1063`; the
measurement is quoted from
`0751-mark-provenance-shapes.md`, which is the half that is re-derived.) The one number the shapes differ on is
3-of-3 marks carrying provenance in their own row against 0-of-3, which is why
the page recommends the fifth column and states what it costs. It corrects the
issue's framing of the comment row as well: a `# provenance` row does bind to
the marks after it, by position, and the real cost is that
`existing_mark_labels` returns a flat `(ts, label)` list with no position to
recover. Three states, not two — absent, empty, populated — and a four-column
row must never read as "held no flag". Offline, over committed files and
constructed ones; no capture taken, no format changed, and implementing the
recommended shape is the next issue's. Written up in
[0751-mark-provenance-shapes.md](findings/0751-mark-provenance-shapes.md).

**2026-09-25 (issue #748): the capture format declares its encoding, so a
capture's bytes are a property of the format and not of the box that wrote
it.** The `ts,addr,old,new` format is **`utf-8`, no BOM**, declared at all
thirteen read and write sites — six readers in the grader, five writer
classes, and two further readers the issue's list missed
(`ec_timer_capture.Sink` is a fifth writer by its own docstring;
`check_capture_claims` and `grade_timer_sweep.load` are the seventh and
eighth readers). The strict/lenient split is unchanged and is what makes the
refusal safe: the three preflight readers keep `errors="replace"`, so the
startup notice still cannot die on a foreign byte, and the grading refuses
the file with the encoding and the remedy named. A capture already on disk in
another encoding is **refused, not decoded per row** — a per-row decode would
make the format's meaning a property of the reader again, which is the thing
being retired. Measured over the 62 committed captures: 36 carry a high byte,
**0 carry a BOM**, and all 62 decode as UTF-8, so the declaration admits the
whole corpus and refuses none of it — which is also why it is `utf-8` and not
`utf-8-sig`, whose write side would *emit* the BOM no committed file has. A
leading BOM is **not** retired by a plain `utf-8` declaration; it now gets a
refusal that names it rather than a complaint about `int("addr", 16)` on the
header. The Windows cp1252 case stays a **prediction from the documented
default with no box reached**; what the declaration retires is only its being
load-bearing. Offline: a count over two committed directories, a round-trip
through a temp directory, and a reader's behaviour on a constructed file.

> **The last sentence of that paragraph is superseded, leaving the measurement
> in it.** It read: *This makes an already-red `measure_mark_provenance.py`
> redder — 6 of its 37 pins were drifted before this change and 29 are after,
> measured both ways and recorded rather than hidden; that tool's crash and its
> re-anchoring are its own issue.* Both figures are confirmed here and
> unchanged, and both are measurements of the tool as committed: a bare
> `python3 ec/tools/measure_mark_provenance.py` reports them rather than
> raising, and reported both counts at the trees they were taken on. What has
> changed is the debt it left: the re-anchoring landed with #750 in this tree,
> all **44** citations resolve, as the #750 entry below counts them — and
> the two `check_capture_encoding.py` sites
> this issue added are cited rather than left as a gap in the census. Written
> up in [0751-capture-encoding.md](findings/0751-capture-encoding.md).

**2026-09-25 (issue #750): the shape of a capture row is stated once, and the
readers that still open a refused capture no longer blame its header.** The
skip rule — blank, `#`, `ts` header — was written out three times verbatim, and
a fourth reader read the same file. It is now a row stream (`capture_rows`,
which owns the open, each reader's decode policy and the first field) plus one
predicate (`skippable_row`) the three strict-side readers call; a stream and not
a filtered iterator, because `read_early_exits` *keeps* the rows the other three
drop (`EARLY_EXIT_TAG` opens with `#`). A leading U+FEFF is stripped from the
first field there, so a BOM'd capture is no longer reported as "the header row
has an unreadable timestamp" with a delete-the-header remedy.

> **One sentence of that paragraph is superseded by the issue above, and the
> reason it gave for its own decision is not the reason any more.** It read:
> *That is a shape-level strip and not `encoding="utf-8-sig"`, which would pin
> the open encoding the tree records as deliberately undecided.* The open
> encoding is no longer undecided — it is `utf-8`, declared — and
> `utf-8-sig` is still not used, for a different reason: the format says **no
> BOM**, so a codec that accepts one is a format change rather than a reader's
> convenience. The consequence is a division of labour the strip was not
> written for: the strict reader refuses a BOM'd capture as a *file*, by name,
> before it reads a row, and the shape is what the three preflights read such a
> capture *with*. The two agree on every file that exists, and the strip is
> redundant rather than wrong for the strict one. `path_starts_with_bom` is a
> seventh open in the grader and a binary one — three bytes, to answer a
> file-level question, declaring no `encoding=` — so the count of declared sites
> above is unchanged. **And the seventh open is not the only way the notice
> learns of a mark:** `existing_mark_findings` reads a capture once (#749), so
> it is told `has_bom` off the buffer it had to read anyway, by the same
> `starts_with_bom` test over those bytes. One question, two callers, one open
> either way.

The anti-drift guard is extended past the reasons to the shape: all four
readers on a fixture carrying `#` rows, blanks and a header; the partition's
accepted and refused lists on a file `read_capture` refuses; the BOM case with a
no-BOM control in it; and the `int()` order among a change row's three hex
fields, which that test's own comment recorded as unpinned. **The one of those
cases that changed is recorded in the tree rather than quietly dropped:**
`test_a_byte_order_mark_does_not_turn_the_header_into_a_bad_row` asserted that
`read_capture` *grades* a BOM'd capture, which #748's decision makes false. It
now asserts the merged contract — refused by name, and the preflights still
reading the header as the header — with the superseded expectation and the
reason for it left in the test's own comment.

Both edits moved the line numbers `measure_mark_provenance.py` cites, so its
rows are re-anchored here rather than in either PR: **44 citations, all
resolving**, which covers the six already red at the fork point, the 23 #748's
own edits drifted, the two new `check_capture_encoding.py` sites, and the
`path_starts_with_bom` line. The count is 44 because both branches' pins are
cited: #749's own at the lines the split left them at, and #750's skip-rule
citations are four — the predicate's body plus the three readers that call it,
`:845`, `:890`, `:1084` and `:1108` — where `origin/main` had two, the rule
written out twice at `:695` and `:871`. That 2 → 4 is worth 2 of the run and
the rest is this
branch's four newly cited sites, `grade_0751_isolation.py:986`, its
byte-order-mark refusal at `:886`, and `check_capture_encoding.py:166` and
`:243`: 38 rows on `origin/main`, + 2 for the rule, + 4 new sites, is 44. Its
citation check reports rather than raising — a bare
`python3 ec/tools/measure_mark_provenance.py` prints its rows and its problem
count and exits 1 while any row is red — so the 6/29 above and the 18/37
#749 recorded are both measurements of the tool as committed, and what
separates them is the tree and not the check. Re-anchoring is the whole of this
branch's change to that tool: `check_citations` and the `scan` it joins
against are byte-identical to `origin/main`, where the same command prints 38
rows, 18 of them `DRIFT`, and 37 citation problems before exiting 1. Offline
over hand-written rows and bytes; no capture taken, no
Windows box reached, and a Windows tool writing a BOM remains a prediction.
Written up in
[0751-capture-row-shape.md](findings/0751-capture-row-shape.md).

> **Correction (2026-09-25, issue #749 merged on top), leaving the measurement
> above as it was taken.** The two figures are right for this change and are
> not the tree's: #749 fixed the crash that made section 5 end in a
> `ValueError` instead of reporting anything, and re-measured the grader's own
> pins after this change's `encoding="utf-8"` moved them. The tree reported
> **18** drifted pins and **37** citation problems at that point, none of them a
> `grade_0751_isolation.py` line. Fifteen of the 18 were pins this change moved
> in the other capture files and were still where it left them, which is what
> the sentence above decided; the other three (`ec_watch.py:254`/`:280`/
> `:355`) were already drifted before either change. The split and the numbers
> are in `0751-notice-two-moments.md`.
>
> **And a second correction, because #750 then landed on the same tree and
> retired every one of them.** `measure_mark_provenance.py` now exits 0 on it:
> **0 drifted pins and 0 citation problems, all 44 citations resolving** and
> the row-site join closing both ways. The fifteen pins in the other capture
> files were drifted by #748 and #749 and are re-anchored by #750 as well —
> #748's retarget was never applied to them, and all 18 of them read `DRIFT`
> on `origin/main` after it merged. The paragraph above is left as #749 wrote
> it; this is the number a reader should use.

## 17. The `main-ec-003` cluster is one 393-byte routine, counted 42 times over (2026-09-23, issue #179; id corrected by #253, by the 2026-09-24 re-derivation, and again by #279 on 2026-09-25)

**The id in this section's subject has been wrong twice, and every version of
the error is in the record.** Issue #179 asked about the cluster the committed
census called `main-ec-002`. Issue #4.3's census regeneration (#133 / #238)
renumbered it to `main-ec-003`, which is what this section's subject read until
the census was re-derived on the merged tree (2026-09-24), which put it back at
`main-ec-002` — `xdata-clusters.csv` row 3, 43 addresses and 4,966 references
over `0x0460`-`0x09CE`, which is this block. The cluster that had taken the old
`main-ec-002`'s meaning has itself split in that re-derivation. Its 28-address
half is row 4, `main-ec-004`, over `0x045C`-`0x1C3A`. Its 11-address half is
row 12, `main-ec-012`, over `0x045E`-`0x1F07`. The four-address remainder is row
50, `main-ec-055`. None of the three shares an address with this block. The ids
move because `xdata_register_map.py:1654-1655` numbers clusters by size, which is
the hazard `ec/annotations/xdata-register-map.md` §5 records for its own table.
(`:1027`, the citation this replaces, never pointed at the sort on `main` either
— the key is at 1629 there, and 1027 is `return oper in ("DPH", "DPL")` — so
this corrects a long-stale citation rather than relocating a sound one.)
The
wrong ids are left standing where they quote issue #179, per §4a;
`ec/tools/check_cluster_citations.py` is what holds the rest of the tree to the
census.

> **(2026-09-25, issue #279: the ids moved once more, and this is where the
> current ones live.)** The census was re-derived again for this issue — 39 new
> `cluster_key`s among the main-EC rows, 380 → 389, and the ranking moved under
> them, by one at the top and by more down the tail — so **the 43-address /
> 4,966-reference sweep over `0x0460`-`0x09CE` is `main-ec-003` again**, the
> fourth name this block has carried after `main-ec-002` on 2026-09-23,
> `main-ec-003` under #253 and `main-ec-002` on 2026-09-24. That is why the
> subject line above names it and the sentences beside it do not. The old
> 44-address block's three remainders are the same memberships under their new
> rank slots: `main-ec-004` (28 addresses, `0x045C`-`0x1C3A`, was
> `main-ec-003`), `main-ec-012` (11, `0x045E`-`0x1F07`, was `main-ec-011`) and
> `main-ec-055` (4, was `main-ec-049`) — each one's `cluster_key` unchanged, so
> the key is what identifies a cluster across the move and a `main-ec-NNN` is
> only its rank (`annotations/xdata-cluster-names.csv` is keyed by it).
> **The renumbering this issue made is in the membership claims, not in the
> sentences that record what #179, #253 and #254 said** — those are left as
> they were written, per §4a, and this paragraph carries the current ids once
> instead of rewriting them.

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
4,642 of the 4,988 the 43 cluster rows sum to, **93%**. Per address the gap is
starker than the total:

| | census `refs` | direct `MOV DPTR,#addr` sites in the image |
|---|---:|---:|
| `0x0843` | 168 | **1** |
| `0x0844` | 168 | **1** |
| `0x06D6` | 148 | **1** |
| `0x0706` | 160 | **1** |
| `0x08A8` | 170 | **2** |
| all 43 | 4,988 | **345** |

*(CORRECTION, 2026-09-25, issue #256: this row read 4,989, and 4,988 is what
the committed CSVs sum to today. `xdata-06c2-06db-timers.md` §2a already carried
the correction — 4,988, a gap of 22 to the cluster row's 4,966, and the gap is
the five `program=both` members' PD references rather than staleness, 3 + 4 + 5
+ 2 + 8 — so this section was a reader's second place to find the wrong figure.
The wrong one stays visible per §4a. Issue #554 arrived at the same 4,988 from
the other direction and records it again; both corrections stand and neither
moved the figure.)*

**So "nine of the ten busiest addresses in the firmware" is a statement about
the export, not about the bytes.** None of those five is among the ten busiest
once the 42-fold count comes out. The largest of the 43 by direct sites is
`0x080D` at 78, and 74 of those are in the PD image.

*(**Update, 2026-09-25, issue #256: the census now knows 42 files are one
routine, and the paragraph above is no longer prose only.**
`xdata_register_map.py` carries a co-reading relation — two `.c` files in one
program naming the same eight or more XDATA addresses, grouped into connected
components per program — and the sweep is **one group of exactly 42** of them,
with a 19-address common core and §2's size pattern (393 listing bytes, 16
one-instruction listings) reproduced by `--self-test` rather than by a hand
count. `xdata-clusters.csv` publishes `co_reading_refs = 4,642` against this
cluster's 4,966, and `xdata-registers.csv` publishes `sources_beyond = 0` for
`0x0843`, `0x0844`, `0x08A8` and `0x06D6`, so the five rows above now have a
column that says the same thing the image's site counts say. **Nothing was
subtracted**: `refs` is still 168, 168, 148, 160 and 170, and no bucket,
cluster id or `cluster_key` moved, so the counts this section warns about are
unchanged — they are just no longer the only place the effect is written down.
The full reading, including the counter-example that keeps this a count of
files rather than a verdict, is `ec/annotations/xdata-register-map.md` §4.5.)*

**Update (2026-09-25, issue #554): the 42-fold count is now measured rather than
inferred, and the default is unchanged.** #256 above made the effect a column;
this makes it a switch. `ec/tools/export_ownership.py` derives which export
owns which body from the committed tree, `annotations/xdata-export-ownership.csv`
is the committed map, and `xdata_register_map.py --export-ownership` reads each
routine once from its owner. The numbers in the table above are what the
census says **by default, and they are unchanged** — the pass takes the census
from 14,822 references to **9,404** and these 43 rows from 4,988 to **460**,
with `0x0843` and `0x0844` going 168 → 4 and 42 touchers → 1, and with **no
address lost from the census**. So the paragraph above is confirmed rather than
overturned: those five addresses are not the firmware's busiest, and the tool
that shows it is committed and re-derivable. The 4,988 the register rows sum
to against this cluster row's 4,966 is the definitional split the correction
above describes — 22, the five `program=both` members' PD share — and it is
unchanged by the pass; `460` is what these 43 rows sum to with each routine
read once.

The default does not flip, because the pass is a containment heuristic over
decompiled text rather than a function boundary, and flipping it re-keys 35 of
the 430 clusters and breaks 5 of the 10 hand cluster names. The cause — the
exporter really having cut one routine into 42 functions — still needs
`--mode rebuild-project`, so the boundaries are not fixed here and this section
does not claim to have fixed them.
`ec/annotations/xdata-export-ownership.md` carries the measurement and what it
does not establish; `xdata-register-map.md` §4.6 carries the flip's cost.

**Update (2026-09-25, issue #555): the boundaries are now *known*, and fixing
them is a toolchain run rather than a question.** The write-up is
`docs/findings/counter-sweep-entry-set.md`; this is the summary. Of the 180
`bank1` census rows that target into `0x8001`-`0x8189`,
`ec/tools/counter_sweep_entry.py` scores each caller with
`disasm8051.converges_from()` and cross-checks it against the committed
listings: **exactly one** of the 180 is at an instruction start — a three-byte
call at `bank1:0xABB8` whose target is `0x8001`, 24 of 24 — and **135 of the
179 others are the `rel8` displacement byte of a `cjne`**, which the census's
`0x02`/`0x12` byte test cannot tell from an `ljmp` opcode. `0x8001` is itself a
frame boundary at 24 of 24 and the byte before it is the `ret` ending the
preceding routine. **One caller was confirmed by this method, which is not
"the only caller in the firmware" and not "179 absent calls"** — the rest are a
gap in a byte scan with a named blind spot, the same caveat
`ec/annotations/bank-call-audit.md` §1 has carried for the census as a whole.

**Five of the six boundaries the annotations argued about are refuted rather
than confirmed, `0x8001` is confirmed as the entry instead, and two of this
section's own framings go with them.** The three seeds `0x8008`, `0x8010`
and `0x8017` are **refuted rather than confirmed** — no site naming them scores
above 1 of 24. And 28 rows said the body runs `0x8018` to the `ret` at
`0x8189`; it runs `0x8001` to that same `ret`, 393 bytes rather than 370, the
23 extra being the `0x06C6` and `0x06CD` countdowns and the `0x06D1`
load-and-decrement that precede `0x8018`. The `0x80EF` row's "here the listing
and the body agree" is corrected narrowly rather than bluntly: its 94
instructions and 155-byte extent are right, and what is wrong is the
comparison — the body is 393 bytes, so that listing is its tail. The wrong
wording stands in every affected row with the correction beside it, per §4a.

**No figure in §2 or §2a moved, and the deletion and the re-export are
mechanically blocked rather than skipped.** `seed_rows()` takes the *union* of
the annotation rows and the census, and every one of the 42 annotation
addresses is also a census seed, so deleting them removes **no** seeds;
`--mode export-only` copies the committed project and cannot un-carve the 42
functions already in the 7 MB `.rep`; and the rebuild turns `bank1/8001.asm`
from 3 bytes to 393, which `verify_reassembly.py --check` fails in the cheap
gate until the pinned `sdas8051` regenerates a single-writer report no runner
can touch. The new page carries the exact recipe and a prediction to check it
against. So `xdata-06c2-06db-timers.md` §8 item 7 stays open with the
boundaries established, and `call-graph-callees.csv` did not drift, so it is
untouched. No `status:` in `registers.yaml` moves and no live test is implied:
this is a byte-frame and text measurement over committed inputs.

**2. Seventeen of the issue's twenty "unnamed" functions already had rows, and
the three that did not were the only ones that had not.** `8008`, `8010` and
`8017` are the work; all three were `seed_basis=call-target`, `size=1`,
`annotated=no`, and each is now a row whose comment says in its own words that
the one-instruction boundary is the call-target scan's hypothesis — the wording
`8001`-`800F` already used. The 42 rows describe slices of one routine and that
is not fixed here: correcting the boundaries needs `--mode rebuild-project`,
which writes the 7 MB database and cannot merge alongside anything else.

*(CORRECTION, 2026-09-25, issue #256: "were `seed_basis=call-target`" is true
of the state this section describes and **is not what `index.csv` says today**.
All 42 rows now read `seed_basis=annotation`, because #179's annotation rows
carried that field in with them. So a reader who opens `index.csv` to check the
boundary hypothesis finds a column that no longer records which hypothesis
produced the boundaries, and the wrong-but-benign conclusion to draw from it is
that the call-target scan was superseded. It was not: the boundaries are the
same hypotheses, recorded here and in `xdata-06c2-06db-timers.md` §2 rather than
in that column. **The evidence for the split is the size pattern and nothing
else** — 42 `index.csv` sizes summing to exactly 393 with 16 of them one
instruction — which is why #256's co-reading group table reports the byte total
and the one-instruction count per group and does not read `seed_basis` at all.)*

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
clustering cut into `main-ec-128` and `main-ec-214` (`0x06C6`, `0x06CD`) are
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
from 84 / 42 to **126 / 0**, and **`main-ec-003` goes from 43 addresses /
4,966 references to 44 / 248** — a shape and not a row, since the guard's
output is not the committed census. Neither figure is right yet — both still
carry the 42-fold count above — but an issue scoped to "read `main-ec-002`"
would be scoped to a membership its own prerequisite changes. (The id in that
quoted scope is `main-ec-003` in the census as it stood when #253 corrected it,
and `main-ec-002` again since the 2026-09-24 re-derivation, per the correction
above; and the 44 / 248 it lands on is the size and reference count the old
`main-ec-002` carried, which is a coincidence of two numbers and not of a
membership — that block has since split, and `xdata-06c2-06db-timers.md` §6a
says so at the table. §17's 2026-09-25 note records the third move: the same
membership is `main-ec-003` again, so the quoted scope resolves to this block
today while reading `main-ec-002` in the issue.) The
issue's own "42 of its
comparisons are `==`" is a second, independent misreading:
`xdata-register-map.md` §4.1 defines `read+write` as "an `=` target whose
right-hand side names the same address", so those 42 are 42 read-modify-writes,
and per §1 all 42 come from the overlapping exports.

> **Correction, 2026-09-25 (issue #254).** The paragraph above is kept as it was
> written and three of its claims do not survive re-measurement. The lead —
> "the direction-classifier defect reshapes the unit this issue was scoped to" —
> is **wrong**. The defect is real, it was fixed in issue #178, and it does
> **not** reshape this block: with the guard and without it, `main-ec-003` holds
> the same 43 addresses with the same 4,966 references, membership identical
> address for address, because the guard moves references *between* direction
> buckets and out of none of them — **0 of 1,171 addresses have a different
> `refs` total either way**. There is no 44-address / 248-reference cluster in
> either generation. An issue scoped to "read `main-ec-002`" is therefore scoped
> to a membership its own prerequisite leaves alone (§17's 2026-09-25 note
> records the third move of that id, back to `main-ec-003`, and both readings
> name this same membership). The guard's real reach is
> the two figures that did reproduce: 833 references leaving `write`, 210 of
> 1,171 addresses changing, and the `0x08A8` / `0x0843` rows.
> Both line citations were wrong against the tool as it now stands: the
> classifier is `store_target()` at `xdata_register_map.py:916`, its `==`
> rejection is at `:939`, and `ASSIGN` is at `:243` — not `:277` and not line
> 138, both of which land on comments in the current file. Those four are
> pinned to the head version of the tool. The first attempt at them was
> measured against `96bc8e89` and ran exactly four lines low, because the
> `--no-eq-guard` paragraph the round-3 fix added to the module docstring
> sits above `ASSIGN` and moves every citation below it by that much; say
> which tree a citation is measured against, or it drifts again. The 1,172 is
> 1,171 rows.
> The diff this called follow-up work has landed, and the census in the tree has
> been post-guard since. `xdata_register_map.py --no-eq-guard` now re-derives
> the before column from the committed tool, and
> `xdata-06c2-06db-timers.md` §6a carries the corrected measurement.

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
machine is that file's §7, and it is written down rather than run. (The
direction-classifier fix landed as #178 and the double count was measured by
#256, both noted above; the 42 boundaries and the rest are still open, and
nothing in this section is a claim that they are not.)

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

**Correction, 2026-09-25 (#261): the 25-row drift was three wrong statements
stacked, and the conclusion was the wrong one.** The sentence above is left as
written. Measured against the committed files by
`build_ec_decompile.py --check`, which now derives all three of the manifest's
function-layer counters offline and prints the ledger they come from:

| was read as | is actually |
|---|---|
| `annotations_applied` totals 1,787 against 1,769 rows, a gap of 25 | the gap is **18**, not 25 (1,787 − 1,769 = 18) — the label never matched even its own numbers. A later paragraph in §19 ("The plan's numbers were stale") had already re-measured the gap as 18 against a newer pair of totals, so the 25 was wrong twice over |
| the two totals are comparable, so their difference is drift | the label never described either figure. `annotations_applied` was the index's `annotated=yes` count (`ExportDecompile.java:129`, `isPlaceholderName(name) ? "no" : "yes"`) — exported functions whose symbol is no longer a Ghidra placeholder, **not** rows of `ghidra-functions.csv` that applied |
| 25 index rows "came to claim an annotation that is no longer in the CSV" | **zero** CSV rows are stale. All 1,872 resolve to an exported function, and `--check` already refuses one that does not |

The gap was never rows lost from the CSV. It is the difference between two
questions, and it decomposes exactly:

| quantity | value |
|---|---|
| rows in `ec/annotations/ghidra-functions.csv` | **1,872** |
| …that applied *and* are reported `annotated=yes` | **1,865** |
| …that applied but are reported `annotated=no` | **7** |
| exported functions named with **no** CSV row behind them | **25** |
| `functions_named`, the old `annotations_applied` figure | **1,890** = 1,865 + 25 |

1,872 − 7 + 25 = 1,890, and the 1,872 rows back exactly one index row each, so
the two sides are reconciled rather than merely compared. `build_ec_decompile.py
--check` prints both directions, the addresses, and the arithmetic; the table
above is that output, not a hand count.

> **Correction, 2026-09-25 (#602): the table above is #261's, kept as it was
> left, and two of its five rows have since moved.** The 7 became 0 and the
> 1,865 became 1,872, so the whole 7 has crossed from the unflagged column to
> the flagged one and `functions_named` is **1,897** = 1,872 + 25. The CSV row
> count and the 25 have not moved. The cause was the reserved namespace the
> "opposite error" paragraph below describes and deliberately did not act on;
> #602 acted on it by renaming seven rows, which is recorded at the end of that
> paragraph. `ec/annotations/subsystems.md` §2 carries the same correction
> against its own census.

**Correction, 2026-09-25 (#603, landing on top of #602): every figure in the
two tables above has moved again, and the mechanism is the one this section is
about.** The section is left as written. `build_ec_decompile.py --self-test`
pins these numbers by hand, and issue #603's 37-row tranche moved them on a
tree that had already taken #602's rename, so the unflagged column stays shut:

| quantity | as corrected by #261 | after #602 | after #603 (this tree) |
|---|---|---|---|
| rows in `ghidra-functions.csv` | 1,872 | 1,872 | **1,909** |
| …applied *and* reported `annotated=yes` | 1,865 | 1,872 | **1,909** |
| …applied but reported `annotated=no` | 7 | **0** | **0** |
| exported functions named with no CSV row | 25 | 25 | **26** |
| `functions_named` | 1,890 | 1,897 | **1,935** |
| `annotations_applied`, bank0 / bank1 / pd | 786 / 684 / 497 | 786 / 684 / 497 | **823 / 721 / 497** |

1,909 − 0 + 26 = 1,935 still closes exactly, which is the point: the gap is
never rows lost from the CSV, it is the difference between two questions, and
this tranche widened it by one rather than breaking it. **That one is worth
naming**, because it is a case the section's framing did not have: naming
`common 0x0A74` made the exporter rename the bare `ljmp 0x0A74` thunk at
`common 0x10FA` after it, so **37 rows moved 38 index rows** and the
`call-target` half of the 26 rose from 9 to 10. A derived name lands in the
index with no CSV row of its own — the same "second copy of a name"
`ec/annotations/subsystems.md` §2 enumerates, and this tranche is what made the
list twelve rather than eleven.

> **Addendum, 2026-09-25 (merged tree): the table's last column is #603's, and
> the tree carrying both also carries issue #267's four `bank0`-scoped
> `0x1665`/`0x1666`/`0x166A` rows, which landed alongside it, and issue #470's
> one `pd 0x11C2` row.** All three additions are `bank0`/`common`/`pd`-scoped and
> additive, so none of the table's structure moves — only the figures. Measured
> on the merged tree by `build_ec_decompile.py --self-test` and by the
> regenerated `ec/ghidra/manifest.csv`: 1,872 + 4 + 1 + 37 = **1,914** rows, all
> applied and all reported `annotated=yes`; `annotations_applied`
> **827 / 721 / 498**, because #267's four rows are `bank0`-scoped and add to
> bank0 alone while #470's one row is `pd`-scoped and adds to `pd` alone; and
> `functions_named` **697 / 605 / 135 / 503 = 1,940**, up 4 on bank0, 38 on
> `common` and 1 on `pd`, with no bank's own figure moving for #603. The 26
> named with no CSV row and the 0 unflagged are unchanged, so
> 1,914 − 0 + 26 = 1,940 still closes exactly. `ec/annotations/subsystems.md`
> §2 and §11 carry the same census, and both now read 1,914 / 1,940 rather than
> 1,909 / 1,935.

**The "7" is only 7 on an export that has caught up with the CSV.** Measured
against the export as this change first found it, the same `--check` reported
**24** applied-but-unflagged and named 1,873 functions, and the manifest was 17
short of what its own rows applied to. That was not a third statement to
correct; it was a stale measurement. The 17 extra are issue #561's
`ff_filler_not_a_function_*` rows, and the export those were counted against
predated the rows themselves — it still carried Ghidra's `FUN_CODE_7401`-style
placeholders at those addresses, so the ledger saw a name it could not match and
counted each row as unflagged. Re-exporting renames all 17 to the names their
rows chose, none of which `isPlaceholderName()` matches, and the count falls to
7 on its own. Two counters moving because the export was older than the CSV is
worth stating separately from a counter being wrong, because only the second one
is a defect in the reasoning.

**What the 25 are, and what they are not.** 18 of them carry names Ghidra
generated itself: `caseD_0` on eleven of bank1's switch dispatchers, one
`add_full_product_to_dptr` repeated across four `pd` addresses, and
`caseD_6` / `caseD_1` / `default` on three `seed_basis=call-target` rows.
`isPlaceholderName()` (`ExportDecompile.java:334-340`) lists `FUN_`, `LAB_`,
`SUB_` and `thunk_` and not `caseD_*` or `default`, so a perfectly automatic
name counts as "named". The other 7 are `seed_basis=call-target`
(`bank0 0x031C`, `0x805B`; `bank1 0x031C`, `0x703A`; `common 0x0512`, `0x1207`)
or `seed_basis=vector` (`pd 0x0000`, `c_startup_idata_clear`), and they carry
readable, mechanism-shaped names that **no script in `ghidra/scripts/` can
produce**: `SeedFunctions.java:100` calls `createFunction(a, null)` and so names
nothing, `ApplyAnnotations.java:212` renames only functions that have a CSV row
and these addresses have none, and `ExportDecompile.java` only reads
`f.getName()`. Since the export takes its names from the project it was handed
and the project is the committed one, those seven are symbols in the committed
`.rep` — by exhaustion of the repo's own export path, not by inspection of the
database. (A raw string search is not the way to show it, and it does not even
cut one way: `grep -ral` over the committed `.gbf` files finds **3 of the 7** —
`index_table_default` and `bl51_bank_select_0` in `~00000000.db/db.1.gbf` (the
latter also in `~00000001.db/db.1.gbf`), and `c_startup_idata_clear` in
`~00000002.db/db.1.gbf` — while missing the other four
(`poll_d6c2_then_branch`, `call_d2a3_then_d274`,
`write_r1_to_tmod_and_jump_8801`, `int0_vector_forwarder_to_052f`). A hit is
real; a miss proves nothing. "Not found by grep" is not "absent" — the same
caveat `ec/annotations/registers.yaml` carries. The three hits are positive
support for the same conclusion the exhaustion argument reaches, and the reason
the argument above rests on the export path rather than on grep is that grep is
not a reliable index in either direction.)

**This also corrects the issue's own attribution.** #261 quoted
`bank0,031C,poll_d6c2_then_branch` as "a function named by `SeedFunctions.java`
from a seed basis". The `seed_basis` column is right; the naming script is not
— `createFunction(a, null)` passes a null name, as above.

**And the opposite error, which the issue did not name.** 7 CSV rows *did*
apply and are reported `annotated=no`: bank1 `0xF113`–`0xF123`
(`thunk_to_f275`, `thunk_to_f290`, `thunk_to_f2ad`, `thunk_to_f2ca`,
`thunk_to_f2f3`, `thunk_to_f198`) and `pd 0x7059` (`thunk_call_122f`).
`isPlaceholderName()` matches any name starting `thunk_`, because that is how
Ghidra renders an auto-thunk, and these seven rows chose the prefix
themselves. This is why the ledger is two-way: a one-way count sees 25 extra
names and misses 7 undercounts. Narrowing `isPlaceholderName()` is a separate
judgement and deliberately **not** done here — the `thunk_` prefix genuinely
covers Ghidra's auto-thunks, and changing it would move the per-row `annotated`
column and the `[named]` marker across the whole export.

> **Answered, 2026-09-25 (#602): the judgement was made, and it went the other
> way.** The reasoning above was right about the prefix and wrong about where
> the fault was. The collision is in the row, not in the predicate: a
> hand-chosen name that starts with a prefix Ghidra owns has chosen a name out
> of the tool's reserved namespace, and the repository already had a convention
> for saying "forwarder" without borrowing it — `forward_to_<addr>`, which
> eleven rows carried before this change and seventeen after. The seven were
> renamed to that convention, with `pd 0x7059` taking `call_122f` because it is
> the one forwarder that is a bare `lcall` rather than an `ljmp`. Nothing in
> `ghidra/scripts/` was touched.
>
> The re-export moved `annotated` and `[named]` for exactly those seven rows and
> no others: `git diff` on `ec/decompiled/index.csv` is 7 rows, and the
> `git diff` on `ec/ghidra/c-digests.csv` is **8**, the eighth being
> `ec/decompiled/pd/B3ED.c`, the one committed `.c` that *calls* `pd 0x7059` and
> so carries the new name at its call site. That is the anti-regression
> evidence: no genuine Ghidra auto-thunk was moved off `annotated=no`, and
> nothing outside the seven and their one caller moved at all. The ledger
> closes `1,872 − 0 + 25 = 1,897` with the 25 unchanged at 15 auto / 9
> call-target / 1 vector.
>
> What the paragraph above got right, and what is now enforced rather than
> remembered: `thunk_` really is Ghidra's. A check
> (`ec/tools/grade_name_basis.py`'s `reserved_prefix_problems`, on the EC side
> only) refuses a committed row whose name is inside the namespace, and
> `build_ec_decompile.py --self-test` holds the Python list of prefixes against
> the Java it is transcribed from, so editing one without the other is a red
> self-test. Full account, including the two copies of `isPlaceholderName()`
> that had already drifted apart and the four BIOS rows that divergence
> explains: [`findings/thunk-prefix-collision.md`](findings/thunk-prefix-collision.md).

**The second clause described a bug this change fixes.** `annotations_unmatched`
was a literal `0` in `write_outputs()`, discarded from a report that
`ApplyAnnotations.java` had been filling in all along. It is now read back from
`apply-<program>.tsv` like the variable counters, and measured: **0** for all
four programs, from 1,872 rows that all resolve. The BIOS driver reaches the
same two numbers a different way — it derives them from the index rather than
from the report (`bios_extract.py:895-896,912-913,940-941`) and fails the build
on a non-zero unmatched count (`bios_extract.py:1241`) — so no manifest in this
repository carries a counter typed in as a constant. The EC is the one that was
discarding a figure its own exporter had already computed.

**The corrected columns.** `manifest.csv` now carries `annotations_applied` and
`annotations_unmatched` read back from the reports (786 / 684 / 497 across the
three programs; `common` borrows bank0's, as the variable counters always have),
plus a new `functions_named` (693 / 599 / 97 / 501) for the figure the old
`annotations_applied` name was really carrying. Note the new `annotations_applied`
sums to 1,967, not 1,872, and that is not drift either: `mine()`
(`ApplyAnnotations.java:375-379`) hands every `common`-scoped row to **both**
bank programs, so the 95 common rows are counted once per program (691 + 95 =
786 for bank0, 589 + 95 = 684 for bank1). There is no
`apply-common.tsv`; `common` is an export grouping the de-dup produces after the
fact. The number §18's paragraph was reaching for — functions carrying a real
name — is 1,890, and it now has a column that says so. `common` is the only
program whose `functions_named` moved with #561 (80 → 97): those 17 rows sit at
addresses both banks carry identically, so the de-dup exports each one once,
under `common`, and it lands there and nowhere else — which is the same folding
that makes the row count twice in `annotations_applied` and once here.

**The write-up for #602 is
[`docs/findings/thunk-prefix-collision.md`](findings/thunk-prefix-collision.md)**
— the rename, the two copies of `isPlaceholderName()` and the four BIOS rows
their divergence explains, and why the rule needed no exception list.

**No hardware or Windows test is claimed here.** This change is static: the
proof is the regenerated export, and nothing in it observes the machine.

**Correction, 2026-09-25 (#601): where those 25 names come from, and which of
the addresses are functions at all.** The argument above about *where* a symbol
lives is undisturbed. The inference drawn from it -- that a
`--mode rebuild-project` from the CSV alone could not reproduce the seven
readable names, because nothing in `ghidra/scripts/` writes them -- does not
follow, because the premise ranges over this repository's scripts and the
conclusion over Ghidra. What the committed bytes say is enough to answer the
question that was left open: **each of the seven is a body that is nothing but a
transfer of control into a function a CSV row already backs under the same
name**, so the name is the target's and the target's row is committed text.
Four more of the 25 have that shape with `lcall` rather than `ljmp`, so the
figure is 11, and the remaining 14 are Ghidra's own `switchD_*` namespace. Four
of the seven addresses are not function entry points at all -- each is a branch
displacement or an immediate that a byte scan read as an opcode -- which is why
no row is added for them. Whether a rebuild re-derives the names is still open,
and the one piece of evidence bearing on it points the other way: all seven are
`annotated=yes`, so none of them carries the `thunk_` form Ghidra gives an
auto-thunk. The write-up is
[`findings/named-without-a-row.md`](findings/named-without-a-row.md), the check
is `ec/tools/second_copy_census.py --check`, and `build_ec_decompile.py --check`
now prints the verdict beside each of the 25 and fails on one it cannot
account for. The counts in the table above are unchanged by it.

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

**The census's own write-up still said 1,172 / 14,801 / 14,792, and which one
was current (2026-09-25, issue #557).** Three mutually inconsistent totals in
`../ec/annotations/xdata-register-map.md`, none of them the committed one — the
CSVs, the tool, §6a above and `../ec/README.md` had all agreed on 1,171 / 14,819
already. Corrected in place against the committed CSVs, with every superseded
figure kept beside a correction naming its tree, and the rule for telling them
apart stated once at the top of that file. The measurement, the re-derivation
command, and the list of what superseded what are in
[`docs/findings/xdata-census-totals.md`](findings/xdata-census-totals.md) —
which is where the next census-dedup change edits.

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

**The shape census is held to a recount now (2026-09-25, issue #630).** §2's
shape-census paragraph states 160 `type: unresolved` rows and 279 names over six
prefixes, and until now it stated them in prose no gate could reach — which is
how #602's own recount found the same paragraph four figures out on a green
build. `build_ec_decompile.py --check` now derives it from
`ghidra-functions.csv` and refuses a row, an `of which` breakdown or the total
that disagrees with the recount, and the paragraph's inline prefix list has
become a table whose rows *are* the vocabulary: the `forward_to_*` family is a
shape-census item by the document's own account and is outside the total, which
an illustrative list could not say and a table says by construction. All three
of that document's census readers now skip a `>`-quoted line, so a correction
recorded beside a live figure stays where the document put it without the check
pinning the retracted number. The recount, the vocabulary decision and the
`#629` boundary are in
[`findings/shape-census-gate.md`](findings/shape-census-gate.md).

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
discard populations** — the proxy cut 195 bank→common edges as well, and
`--report` now prints both and splits `ungrouped` by reason; see
`docs/findings/group-proxy-populations.md`.

**The one `pd` proxy edge was a missing annotation, and the program-boundary
question it was read as is answered (2026-09-25, issue #470).** The 196 above is
195, because `pd 0xCB2A` → 0x11C2 no longer proxies: `pd 0x11C2` is now
`dispatch_code_table_2byte_key` and the edge joins it directly. It was never a
second kind of region — the proxy branch is reached when the target has no row
in the **caller's own** scope, so for a `pd` caller that means "no `pd` row",
and "no row" is *not found by this method*, never *absent from the PD program*.
`region_of()` needed no new vocabulary because it was never consulted. The
distinct `common` targets are 35 and the non-bank-reached bucket 80 edges; the
`callgraph_pd_0003` component is 414 while its rows carrying the name stay 303,
because the new row takes a `type=dispatch` seed and a seed outranks a cluster.
The two 32 KiB low areas of the dump agree on 503 of 32768 bytes, which is what
the two rows are not interchangeable looks like. Full write-up, the byte
comparison and the reproduction:
`docs/findings/pd-common-address-spaces.md`.

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

*** CORRECTION 2026-09-25 (issue #470), leaving the paragraphs above as they
were written.*** **The program-boundary question is answered and the answer is
that no such rule is needed.** `pd 0x11C2` is now
`dispatch_code_table_2byte_key`, so the one edge that carried this question is
joined directly and there is no longer a `pd` caller on the proxy line. The
proxy branch is reached when the target has no row in the **caller's own**
scope, and for a `pd` caller that means "no `pd` row" — a fact about
`ghidra-functions.csv`, not a second kind of region. `region_of()` was never
consulted for that edge, which is why it had nothing to say. The write-up is
`docs/findings/pd-common-address-spaces.md`.

Three figures in the paragraphs above moved with it, and each is a statement
about the tree rather than about the bug: **nine shared addresses → ten**
(`0x11C2` is the tenth), **38 unannotated `pd` listings → 37**, and
`common 0x11C2` no longer keeps a `['common','pd']` attribution, because it now
has a `pd` row beside it and the `pd` edge joins that row instead. The
`26 / 196 / 36 / 115-81 / 456` line is what that fix measured at the time and is
untouched; the current figures are 26, 195, 35, 115-80 and 478, and
`ec/annotations/call-graph.md` and `group-proxy-populations.md` carry the same
corrections. (The last of those, `ungrouped`, is 474 at `e30dbd2d` and 478 from
`d8525eae` on: +4 for issue #267's four `bank0` routines landing ungrouped, which
reached `main` before this branch was cut rather than arriving with the merge,
re-measured with `group_functions.py --report`.) **Everything this
section measured about the ordering bug is
unchanged** — the six same-scope joins, the `scope == "common"` guard, and the
fixture that fails on the unfixed tool.

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

## 23. A dump read was filed under a block whose windows the run had refused (2026-09-25, issue #499)

The write-up is `docs/findings/dump-reads-for-a-refused-block.md`; this is the
summary. It is a reporting and attribution change: **one fixture was added, no
capture was re-read, no EC was read, and no register status moved.**

`report_dumps()` and `report_dump_pairs()` were told a block's **value** and
never its **verdict**, so in §6's own per-block command form — the one #380's
run produces — a void block got its §4.6 readback and its whole-block bracket
read and printed in the usual result format, two sections after the block
section had refused its windows. The sharpest form is the closing section,
which said this output says **nothing** about §4.1-§4.3 for the block and then
reported a read of §4.1-§4.3 for it. **The read is kept and marked, not
withdrawn**: `the last dump still holds the written 0xA0` is a claim about two
files on disk and is true whatever the CSV mark set did, a void block does not
make the two dumps agree or stop covering the addresses, and refusal in this
tool is reserved for inputs that cannot bear the read. A block being void says
the capture is short a mark, not that these bytes were never in evidence.

**The verdict rides on the existing two-space group line, appended and never
moved** — the group line is the whole of the attribution, since the bracket
body itself cannot show which block it is about — and the bracket bodies and
section headings are byte-identical, so `group_body()`'s cut and the "no third
category" invariant both stand. `report_blocks`' inline restore check is now
`block_verdict()`, so the block section and the two dump sections cannot
disagree, and `verdicts_for()` is built from the **same block set
`report_blocks` checked**. That scoping is the load-bearing part and the easy
one to get wrong the helpful way: on a `--block 0xA0` run over `3blocks/`, a
group naming `0x10` gets the existing `not the block under test` line and **no
verdict at all**, because an index over every block would print "0x00 is VOID"
about a block the same report had said it did not check. A value in no block is
a third state, distinct from a block with nothing to mark, and says so.

**"Refused" has two reasons and the marker keys on both, which the issue did
not name.** `report_blocks` withholds on `block.problems`, not on the restore
check alone — a block can hold its restore and still be short an action earlier
in it — so a marker keyed on the restore alone would have left the same defect
standing for `missing-mark/` and `disagreeing-marks/`, where `block_verdict`
says `intact` and every window is withheld anyway. Those two now get
`its mark set does not hold, its windows were withheld above` beside the void
block's `VOID, ...`. It is the failure mode a "read and mark" change has while
looking like it landed: the void case is covered and the other refusal is not.

The `graded_pairs` sentence **stays** — the pair was compared, so the count does
not drop — and gains a scoped companion when the run graded no window at all,
on the same reasoning as the `moved_groups` companion above it. The exit code
is unchanged; a void block already returned 1. **No live run happened and none
is implied**: the reproduction is offline over hand-written fixtures, and §7's
`confirmed-inert` still needs #380's run.

## 24. A citation is a code frame, not an address (2026-09-24, issue #453)

The write-up is `docs/findings/citation-code-vs-data.md`; this is the
summary. `../ec/tools/call_graph.py` credited a comment to whatever anonymous
function its `0x` + 4-uppercase-hex-digit token resolved to, and on this
firmware that token is a function entry *and* an XDATA byte constantly — 0x07D0
is `FUN_CODE_07d0` in the index and `DBD1` in
`../ec/annotations/registers.yaml` — so **the top of the committed call-graph
ranking was a census of XDATA addresses**. `../ec/tools/citation_frames.py` now
gates each citation on whether a code frame governs the mention.

**The window is bounded and local, and that is the part worth keeping.** A
data veto over the whole sentence rejects a genuine list: seven `bank1`
comments read "then calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF", so a
sentence-wide veto would have thrown away 21 real citations to save 27 fake
ones — a larger corruption than the one being fixed. A code frame is
*necessary*, a data frame is a *veto*, and what neither settles is reported as
`undecided` rather than defaulted.

**The population, partitioned for the first time: 382 candidate
(callee, comment) pairs → 152 kept, 185 rejected, 45 undecided.** The guard
reports both discarded sets and never drops them, following the
`audit_call_targets.py` precedent, because a guard that silently discards what
it rejects cannot be told apart from one that rejects too much. The cited
callees drop from 141 to 99 and the citing comments from 315 to 142, so 45% of
the old citation count was a call at all.

**Two of the numbers are corrections, kept visible.** `common,07D0` is **2**
citations, not the 27 the table carried and not the 0 the issue argued for:
`common,018C` and `common,029B` both say "calls 0x07D0" and both listings
carry the `lcall` (`../ec/decompiled/common/018C.asm:40`, `029B.asm:50`), so
`cited_by` and `inbound` now *agree* — which is the check a guard zeroing all
27 would have failed. And `common,1606` has six citations, all `XDATA 0x1606`,
with **no `registers.yaml` row at all**, so a lookup against that file is not
the guard; 0x1C00 is the limit worth carrying, 20 comments naming it and no
row in the table at all, because no transfer reaches it.

**The largest slice is not lexical.** 45 of the 71 `pd`-scoped pairs name a
`common`/`bank` row and cannot: the dump holds two 8051 programs with separate
address spaces. **Three of those 45 read as a code frame**, so the
program-identity check does work no lexicon reaches — and the complementary
case (a bank comment citing a `common` row, which is legitimate) is
deliberately left to the frame test alone.

**What was still wrong, and it was not the guard:** the new ranks 1–3 were
`common,0F75`, `common,158E` and `common,1594`, 7 citations each, and all 21
came from the same seven `bank1` `0xFF`-fill comments whose text says the
decompiled body "is not supported by these instructions". Each citation does
read as a call to a code address; what the comment is attached to is fill, not
the reset path those calls live in. That is a second defect — the comment
refutes the decompile and still names its callees — and ~~it is the next thing
to fix~~. Nothing here is a behavioural claim: no register `status:` changed, no
listing was re-read, and no live test ran.

**Correction (2026-09-25, issue #525): the second defect is fixed, and this
section's partition is superseded.** The write-up is
`docs/findings/citing-listing-evidence.md`. `../ec/tools/citation_callers.py`
asks the *citing* row's own listing the half of the question a frame test
cannot see: seven `bank1` listings are an unbroken `0xFF` run, `mov R7, A`
repeated, and cannot make the calls their comments name. Those **21 pairs are
refused** as `fill-at-citer` and `common,0F75`/`0x158E`/`0x1594` now read
`cited_by=1` against their own `inbound=1`, with `citing` reduced to
`common:0070` — the real call, whose listing carries the `lcall` at
`../ec/decompiled/common/0070.asm:12-14`. The same listing evidence **credits
16** pairs the bounded frame window left `undecided`, so the partition moves
out of the same 382 candidates and the top of the ranking is no longer the fill
artifact. The new rank 1 is `common,07F0` at `cited_by == inbound == 3`, which
was not predicted and rests on `polls` in two of its three comments rather than
on a weak marker. One of the 16 credits is wrong — `bank0,D091`'s own comment
says the bytes it corroborates are a CODE table, not code — and that is
reported rather than tuned away, because the alternative conditions were each
fitted to that one known wrong answer. The seven fill comments are **not**
rewritten: substituting a name there would assert the call the comment denies.
**The merged partition is 148 / 206 / 28**, which is 153 / 185 / 44 (this
section as corrected by §25 below) with #525's two rules applied: −21 refused,
+16 credited, and the 28 the frame gate alone leaves undecided. §25 below
records the 153 / 185 / 44 this correction started from.

## 25. The 45 undecided pairs, settled one at a time (2026-09-25, issue #526)

The write-up is `docs/findings/citation-undecided-verdicts.md`; this is the
summary. §24's undecided population is the one `citation_frames.py` exists to
hand a human, and `report()` printed only its size. It now renders the
population the way the rejected one is, with each line carrying the frame
verdicts its mentions drew — an undecided `Candidate` has no reason to print,
so the line used to end in a bare `--`.

**One lexicon word, `sjmp`, and it moved exactly one pair.** `bank1,9B03` says
"it ends in an sjmp to 0x9B3C" and `../ec/decompiled/bank1/9B03.asm:31` is
`9B33 80 07 - sjmp 0x9b3c`, so the census goes **152/185/45 → 153/185/44** and
`call-graph-callees.csv` stays byte-identical (0x9B3C has no row in it: no form
in `TRANSFERS` reaches a PC-relative branch). `sjmp` belongs with `lcall`/
`ljmp`/`ajmp`/`acall` because a comment can name the listing mnemonic the
way it names `lcall` — and because `audit_call_targets.py`, `grade_name_basis.py`
and `disasm8051.py` already list `sjmp` in their branch families, so the
comment lexicon was the odd one out. **It is not a wider-reaching form than its
neighbours**: `sjmp` is `80 rel`, a signed 8-bit offset, and the committed
`80 07` is the whole of a 7-byte branch. The issue's title puts the gap in
`call_graph.py`'s `TRANSFERS`; it is not there, and adding it would have pulled
every intra-function short jump into the graph.

**The other 44 are readings, and the tool still reports them undecided** —
subject to the two signals §24's correction names, which between them settle 17
of the 45 in the tool's own terms. The 44 minus the 16 the citing listing's
transfer corroborates and the 1 this section's own lexicon word takes is the
**28** the merged tree reports; every one of those 28 carries a reading here.
They are settled on the listing or on the committed firmware bytes, not by a
wider window, and the write-up says so per row rather than leaving a reader to
discover it by counting 44 against a 45-row table. `FILLER_BUDGET` stays at 1 —
§24's own measurement is re-confirmed at that value, not moved.

**The rows are not all the same shape, which is the point of reading them.**
16 cite a transfer the citing listing carries and the window could not reach —
**and those 16 are exactly the pairs issue #525's `citation_callers.py` then
credited from the same listings**, which is two independent routes to one
answer; 7 are jump-table claims settled by reading the table bytes out of
`ec/firmware/GMxMGxx_11.800` (`0x8A80`, `0x9AD2`, `0xAD50`, `0xC90C`,
`0xD20D` — the last corroborated by the `lcall 0xCC2D` that follows it);
12 name another function's *body*, an *exit* or a comparable listing, where no
transfer is claimed in either direction; 8 are XDATA mentions and true
rejections; and 2 are neither — one is a code reading the *same comment*
retracts (`bank0,D091`'s ACALLs, which `decode_index_table.py --at 0x0D148`
reads as 12 well-formed table entries) and one is a resolver artifact
(`pd,E930 ← bank1,E924`, where the mention names a bank1 fall-through and the
index has no `bank1` row at that address to credit).

**Two of those are the reason a lexicon word needs its own evidence.** The
0xD673 pair is undecided only because the sentence writes "ACALLs" and
`CODE_VERB` has `acall` without the plural; adding the plural would credit a
claim its author withdrew — and issue #525's corroboration rule credits it
anyway, from the listing, which is the same overclaim arriving by another road.
That one wrong credit is recorded in
`docs/findings/citing-listing-evidence.md` rather than tuned away. Every word
this adds carries its evidence sentence and listing anchor in
`../ec/tools/test_citation_frames.py`. Nothing here is a behavioural claim: no
register `status:` changed, no listing was re-read, and no live test ran.

## 26. The reset vector's two DPTR-only bank-0 targets, read (2026-09-25, issue #559)

The write-up is `docs/findings/reset-vector-dptr-targets.md`; this is the
summary. The reset vector's two middle `lcall`s reach bank-0 code through
trampolines that carry their target as a `mov DPTR,#imm16` immediate, which is
why no call-target census row and no byte scan ever named them. Both were
seeded through `ghidra-functions.csv` and read. **`0xD89F` is a single `ret`
byte, and `0xD96C` is a real routine that clears XDATA `0x0100`–`0x0FFF` except
it steps over `0x07FD`, `0x07FE` and `0x07FF`** — 3,837 of 3,840 bytes, and
those three are the whole of the `main-ec-086` cluster. The `setb c` at
`0xD982` is what makes the second bound `0x0800` rather than the `0x07FF` its
own immediates spell out. Both score 24 of 24 on `disasm8051.py --converge`, so
neither is an operand byte. This corrects the issue's expectation of a real
routine at each: one is a bare `ret`, and it would join the 77 one-byte
`ret`-only listings already in the tree rather than be the first. The audit gap is a missing census of the 403 trampoline immediates, not
a wrong census, and the two read here license nothing for the other 401. No
register `status:` changed, the 2,710 index-row pin stands, and the export is
deferred to a pinned-toolchain run for the reason #255 gives. The 1,851
annotation-count pin this section quoted when it was written is 1,872 in the
merged tree, moved by issue #558's four rows (§27) and issue #561's seventeen
fill rows (§28), and re-pinned in `../ec/tools/build_ec_decompile.py`.

## 27. The corrected ranking's top four, read (2026-09-25, issue #558)

The write-up is `docs/findings/common-07f0-0f75-158e-1594-tranche.md`; this is
the summary. #525's `citation_callers.py` put four different addresses at the
top of `../ec/annotations/call-graph-callees.csv`, and this names all four:
`common,0x07F0` (`inc_xdata_0043_return_new`, `writer`), `common,0x0F75`
(`clr_xdata_0000_00ff_iram_20_bf_xdata_9000_97ff`, `init`), and the two BL51
stubs `common,0x158E` / `common,0x1594`
(`load_dptr_d89f_tail_jump_1100` / `load_dptr_d96c_tail_jump_1100`,
`bank-switch`). All four are `name_basis=code-shape`, which is forced rather
than chosen: `0x0043` has no `registers.yaml` row, and `load_dptr_*` names
deliberately carry no `bl51_` token.

**Three of the issue's readings of the bytes did not survive them, and the
wrong version is quoted beside the right one in the write-up rather than
quietly fixed.** `0x07F0` is six instructions, not seven. `0x0F75` has **three**
clear loops, not two, and all three bound on the pointer's *high* byte, so it
clears XDATA `0x0000`-`0x00FF` (256 bytes, not the 32 the issue's `0x20`
immediate suggests), **internal** RAM `0x20`-`0xBF` (160 bytes — the loop the
issue skips entirely), and XDATA `0x9000`-`0x97FF` (**2,048 bytes, not the 152**
the issue's `0x98` immediate suggests; `0x98` is compared against DPH, not DPL).
`0F75.c` agrees with the `.asm` on all three. The two stubs' `.c` files show a
`return;` that no `ret` in either listing backs — the decompiler reading a tail
`ljmp` as a call — and the rows do not repeat that shape. The method the issue
describes is issue **#255**, at `../ec/annotations/xdata-06c2-06db-timers.md` §4
and in the `bank1,0x19A8` row, so both immediates are **bank-0** addresses. The
48-forwarder census that row carries is still not re-measured against bank 0,
and **#465** is the open issue that tracks exactly that.

**The `0x1592`-`0x1593` question is settled, and the answer is that it was
never a gap.** They carry no listing line and no index row, which is the shape
an un-owned run would have, so they were read out of the firmware: at file
offset `0x1592` they are `11 00`, the last two bytes of `0x158E`'s own
`ljmp 0x1100` at `0x1591`, and the index's six-byte size for `0x158E` already
covers them. All four boundaries are hard ends — a `ret` plus the next index
row for the first two, an unbroken six-byte trampoline grid for the last two —
so the header's "this boundary is a hypothesis" caveat is off all four.

**No `registers.yaml` row for `0x0043` or `0x200B`, and the scans that would
write one are committed instead.** The issue made the rows conditional and they
are declined: `registers.yaml` is a claim about a register, and the preceding
tranche's own precedent in `call-graph.md` is that naming a helper is not one.
What a follow-up needs is the measurement, so the write-up carries
`scan_refs.py` / `trace_xdata_refs.py` output for both — `0x0043` at four
direct-`MOV DPTR` sites whose only reads among them are `0x07F0`'s own two,
`0x200B` written at all eighteen and not one of them reading — and that is the
whole of the input. That is bounded to the method the way
`../ec/annotations/xdata-086x-dispatch.md` bounds the same shape of negative: a
read reached through a computed DPTR leaves no direct-`MOV DPTR` site, so these
are "not found by this method", never "no consumer exists". The gap is issue
**#110**.

**The export this change regenerates had been one commit stale, and that is
why the diff is larger than four rows.** `a1d79a89` (#250, PR #504) changed
`../ec/ghidra/xdata-symbols.csv` and added three `ghidra-functions.csv` rows
without re-exporting, and `--check` does not catch that — it holds the `.c`
headers against `index.csv` and both against the annotations internally, and
both were self-consistent in the stale name. The re-export therefore moves
**seven** rows, not four, and `c-digests.csv` 38 rather than 4. Nothing was
hand-edited and nothing was reverted: the `.asm` instruction bodies are
byte-identical across the whole diff, and a second `--work` re-export leaves
`git status` clean.

**No live test is implied anywhere.** The counter, the three cleared regions and
the two bank selects are static readings of committed bytes, no register
`status:` moved, `../ec/ghidra/xdata-symbols.csv` is unchanged and
`gen_xdata_symbols.py` is a no-op on this tree. The follow-up for seeding
`0xD89F` / `0xD96C` — as `bank0` rows, per #255, which this section is what
earns — **has since been done**, by #559 and §26 above: it read both, and it
corrected the premise this section was filed against, that seeding a function
needs `--mode rebuild-project` and so cannot share a branch with another EC
change. `--mode export-only` seeds the scratch copy and exports from it, and the
committed `.rep` is never opened for writing. The two rows and their listings
are still uncommitted, for #559's own reason and not this one.

## 28. Every all-`0xFF` listing in the export, and the byte scan that made seventeen of them (2026-09-25, issue #561)

Thirty listings in `ec/decompiled` are an unbroken `0xFF` run — every
instruction line's first byte is `ff`, which the 8051 map fixes to `MOV R7, A`
and nothing else. Twelve carried a `ghidra-functions.csv` row saying so; **18
carried none**, and 17 of those are `common` listings inside one unprogrammed
band, `0x728F`-`0x7FFF` (3,441 bytes, all `0xFF`, measured — not the `0x7400` the
issue's title has, which is just the lowest address the scan seeded). The
eighteenth is `pd,0012`, issue #489's, deliberately left out of this diff.

**All seventeen were put there by a byte scan**, `seed_basis=call-target`
throughout, and `ec/annotations/bank-call-audit.md` §1 now says what that costs
in its own terms: 28 rows across the three regions name them, **not one at an
instruction boundary** — 22 inside another instruction, 6 at a site no committed
listing covers. A `12 74 01` read across a `jnz`'s rel8 and the next `mov`'s
immediate is a site no byte anchor decodes onto (`frame_onto` 0) and no call,
which is what the "upper bound" caveat on those listing headers means where it
actually bites.

Seventeen `ff_filler_not_a_function_*` rows land in
[`ghidra-functions.csv`](../ec/annotations/ghidra-functions.csv) — the `bank0`
siblings' name, because the verifiable fact is structural rather than a routine
waiting to be implemented, and because that spelling is what
`grade_name_basis.py --check` recomputes for `unresolved`. The record-count pins
move 1,855 → 1,872, `ec/annotations/function-groups.csv` gains the seventeen as
`ungrouped` (no typed seed, no component — the right answer for an address that
is not a function), and `ec/ghidra/cross-decoder.csv` is regenerated: all
seventeen come back `vacuous`, the tool's own 8051 decode finding no `MOV DPTR`
in any of them. **No Ghidra export runs in this change**, so the seventeen keep
`FUN_CODE_*` in the index and their listing headers until one does, and the
anonymous-name counts #458 measures do not move. One citation pair moves with
it — `common,375E ← common,7DF2`, from a new comment naming the instruction its
own byte match sits inside — and `call_graph.py`'s `fill-at-citer` veto rejects
it, so nothing is credited. That veto's rejection count is 0 on `main` and 1
with these rows; the twenty-one measured on the pre-#570 base tree are gone
because #558 named `common,0F75`, `0x158E` and `0x1594`, and a named callee is
not an anonymous one — not because the rule changed.

The band is measured; its cause is not. The same runtime addresses hold live
code in the PD program — 165 non-`0xFF` bytes across the seventeen spans, seven
`pd` exports inside the band, and `0x7421` is the `pd-xdata-overlap.md` §3.1
site — so "reserved region" and "linker artefact" both still fit every number,
and settling it needs a Keil linker map or a sibling dump this repository does
not have. The full census, its 30/29/1 split, the byte confirmation read from
the firmware, the provenance read back instruction by instruction, and the
cross-program comparison are in
[`docs/findings/ff-fill-census.md`](findings/ff-fill-census.md), all re-derived
by `python3 ec/tools/census_ff_fill.py` and pinned by its `--self-test`. Nothing
here is a behavioural claim: no register `status:` changed, no listing was
re-read, and no live test ran.

## 29. `--no-eq-guard`'s two refusals are pinned, and the tripwires are why (2026-09-25, issue #556)

The write-up is
`docs/findings/xdata-no-eq-guard-refusal-contract.md`; this is the summary.
`--no-eq-guard` carried three claims and only its first was tested; the two
refusals, which fire in `main()` before the mode dispatch and are the reason
the `xdata-06c2-06db-timers.md` §6a measurement stays re-derivable, now have
`../ec/tools/test_xdata_register_map.py`. **The refused cases replace all nine
mode entry points with recorders and assert that none of them ran**, which is
the claim rather than the consequence: a guard moved below the dispatch fails
the test instead of writing the pre-#178 census over
`annotations/xdata-registers.csv` and `annotations/xdata-clusters.csv`. The
count is nine rather than the six this work was written against because #566's
co-reading modes joined the dispatch, and a tripwire that named only the old
six would have let a relocated guard reach one of the three it did not mock.
Each mutation was run against a scratch copy of `ec/` to show the suite goes
red, and the mirror's census CSVs were byte-identical after every one — **a
failing run of this suite cannot damage the repository.** `tools/run-tests.sh`
is **19 of 22 suites** on this tree, and all three failures reproduce on a
pristine `HEAD`. Two are the ones this section is about: one of them,
`test_xdata_cluster_names.py::TheGuardOffRegeneration`, is a regression from
#528 itself, which threaded `eq_guard` through `store_target()` and so left the
sibling's "delete the `==` guard" recipe deleting a conditional rather than the
rejection — **the accepted run in the new suite is currently the only working
checked-in-suite route to a guard-off census**, and the fix is named in the
write-up rather than folded in here — and the other is
`test_check_site_census.py`'s `D091.c`
line-pin drift, which #503 caused. The third,
`test_check_cluster_citations.py`'s committed-prose case, is **main's own**:
§26 above pairs `0x0800` with `main-ec-086`, and the committed census puts
`0x0800` in `main-ec-104` instead. Which of the two is wrong — the name or the
membership claim — is a correction for #564 to make in place rather than one
this issue absorbs. Nothing here is an EC finding: no register
`status:` changed, no hardware was involved, and the committed census is
untouched. `--check` is now **green** — #566 regenerated the two CSVs, so
#326's symptom is gone from the tree this lands on, which is this issue's
requirement met ("this changed nothing about the verdict"). It does not make
the hazard sharper: `--check` is refused with `--no-eq-guard`, so it
regenerates guard-on and goes red on a guard-off file whether the check was
red before or green, and `check_cluster_citations.py` goes red with 45
disagreements. The refusals are still worth pinning because they stop the write
*before* it lands, but the failure they prevent is a loud one rather than a
silent one. #512 (the `--self-test` redness, which #566's gate comment names
and deliberately does not run) and #433, with the #504 naming backlog, are left
open.

**Updated 2026-09-25, issue #608.** The `TripwireCoverage` reader this section
describes was a `visit_Return`, so it held for a mode dispatched as a `return`
and for nothing else — a tenth mode in statement position was in neither the
recorded list nor `MODES`, and the suite stayed green with it unmocked. It now
reads statement position too; the write-up is
[`docs/findings/xdata-dispatch-tripwire-coverage.md`](findings/xdata-dispatch-tripwire-coverage.md).

**Updated 2026-09-25, issue #816 — the three failures this section names are
resolved, two of the three suites are green, and the third
"committed-prose case" below is not owed.** Three sentences
of this section are left standing and are now false, so this addendum is their
correction rather than a replacement: "19 of 22 suites", "all three failures
reproduce on a pristine `HEAD`", and "the accepted run in the new suite is
currently the only working checked-in-suite route".
#752 re-pinned the `census_refs` cells and cleared
`test_check_site_census.py`; #753 replaced the copy-and-patch recipe with
`--no-eq-guard` and cleared `test_xdata_cluster_names.py` along with the
`setUpClass` error this section attributes to #528. **The runner nonetheless
still exits 1**, on the third of the three suites this section names —
`ec/tools/test_check_cluster_citations.py` — and its one failure is on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220`, which is **#822's**
write-up and reproduces on a clean `origin/main`. `bash tools/run-tests.sh` gives
`32 suite(s) run, 974 tests; one or more FAILED` here, with
`git status --porcelain` empty afterwards, and §52's merged-tree note, further
down this file, is where that is recorded. There are now **two** working
scripted routes to a guard-off census rather than one, and #753 is the follow-up
this section says the fix "belongs with" — it read this page to choose, and
chose the flag over re-pointing the recipe. The §26 disagreement this section
calls **main's own** and hands to #564 is likewise not owed: `main-ec-086`'s
committed row really is `0x07FD 0x07FE 0x07FF`, so that claim is true. The
address `0x0800` now falls in a following sentence that names no cluster id at
all, so the checker drops that unit before it reads the address. The refusal
contract, `tools/README.md`,
`runner-red-suite-set.md` and
`../ec/annotations/xdata-register-map.md` each carry the same correction beside
the sentence it belongs to; the write-up is
[`docs/findings/xdata-no-eq-guard-measured-state-correction.md`](findings/xdata-no-eq-guard-measured-state-correction.md), and the summary is §59.

*(**Corrected at the merge, 2026-09-25, #850 beside #849.** The `974` above is
the count re-derived on `main` and it was exactly right there. Two merges are in
this tree: #849 adds `ec/tools/test_check_doc_figure_pins.py` at 44 cases and
#850 adds `TheExportOwnershipClusters`'s two cases to
`test_xdata_cluster_names.py`, so on the merged tree the runner reads
**`33 suite(s) run, 1020 tests; one or more FAILED`** — the same one red suite, on
the same #822 line, and the runner wrote nothing into the tree to get it. The
figure above stays visible because it was true of the tree it was measured on;
§66 is the other half. **#851 then added a suite in the same window, so the tree
this finally lands in reads `34 suite(s) run, 1035 tests; one or more FAILED`**,
on the same one red suite and the same #822 line. *(`34`/`1035` is #850's merged
tree and not this one: #887 added a suite, so this tree reads `35`/`1076` and
#850's two cases are in that too. The sequence and the seven places the
superseded figure is left standing are in
[`runner-red-suite-set.md`](findings/runner-red-suite-set.md), which is the file
that exists so this correction is written once rather than seven times.)* Three of the four numbers
here are records of three trees; the one that is the same on all of them is the
red suite. `runner-red-suite-set.md` is where the counts are argued
rather than pinned, and this is the merge being the reason that rule exists.)*

## 30. The call-graph tranche's twelve `unresolved` rows, retyped from their bytes (2026-09-25, issue #456)

Issue #134's tranche left twelve of its 44 rows at `type=unresolved` and
`call-graph.md` said so and stopped. All twelve are now typed from what their
own bytes do, and **the record count did not move — 1,877 before and 1,877
after** — because the entry the issue expected to be missing was not missing.
Full account in
[`call-graph-unresolved.md`](findings/call-graph-unresolved.md).

**The five boundary rows all turned out to be real entries, and the split Ghidra
cut is *after* the entry, not before it.** `ec/decompiled/index.csv` gives
`common 0x4A76` one byte with a second function at 0x4A77, `0x3B4E` three with
one at 0x3B51, `0x7177` four with one at 0x717B, and `0x0200` nineteen with one
at 0x0213 — and reading forward from the committed image each routine runs on
into the next function and returns. **What settles it is the caller side**: at
0x485B, 0x4868 and 0x492D a `lcall 0x4A76` is each followed by a separate
`lcall 0x4A4D`, which only makes sense if control comes back; and every transfer
the export shows reaching `0x0200` is an `ljmp`, never an `lcall`. `0x4A76` turns
out to be the first half of a two-stage computed goto into a **CODE** table at
0x4900, and `0x7177` a jump-table thunk that `common 0x05A6` reaches from
inside an interrupt epilogue.

**The caller-side question 0x9C47 was opened for has an answer, and 0xD2BE is the
same device.** 0x9AAD dispatches on XDATA 0x044B with cases 0, 1, 2, 3 and 4;
`0x9B4A` is the **default** arm, the other six `ljmp` sites are bail-outs from
inside a case whose test failed, and four more conditional branches land there
without a transfer. So every path means "this case's condition did not hold".
0xD2BE's five sites are all guards in `dispatch_on_0860` — 0x0860 zero, 0x0860
0xFF, or bit 0 of 0x1C00/0x1C11/0x1C29 set. Both typed `forwarder`, which is what
`bank1 0xA9B3` and `bank0 0x849C` already set for the same shape.

**Five of the six large bodies carried a claim the bytes refute, and the
corrections are in place.** 0xD757's "bits 0xE1 and 0xE3" are bit *addresses* —
bits 1 and 3 of the byte at XDATA 0x1500 — and its 0x103B-0x103F run and its
jump to 0x0200 are separate cases, not one; 0x8931's head skips nine bytes of
another function, not "the whole body", and its cascade names CPU_TEMP and
GPU_TEMP; 0xDE83's 0x3000 block is **not** outside the EC's XDATA map, and its
carry-set return is not reachable from its own writes; 0xE656's `jnb 0xF3` is no
PSW bit at all but bit 3 of the B register — bit 3 of the byte loaded from XDATA
`0x031C` — where the row had bit 0 of 0xF3; 0xCD80 tests bit 2 of 0x03FF where
the row said bit 0, and its body runs whenever the step is at or below the limit
rather than only on reaching it. **The step bound is the claim that did survive,
and the mask is what shows it**: `anl A, #0xfc` replaces R2 with 3 only when
`0x0397 & 0xFC == 0`, so a 0x0397 of 0 to 3 gives a step of exactly 3 and
anything larger passes through as itself, which is "at least 3" either way — what
the mask fixes is the condition, not the size. 0xBD45 is the sixth, and it only
adds: the 0x0497/0x0403/0x0539 consultation, which its old text never reached,
loads the same DPTR on both sides. 0xE656's trip count is also new — fixed at
eight entries by its own bytes.

One clause outside the twelve was corrected in place: `common 0x3B51` said its
high byte is added "through the carry", which its own `clr A` at 0x3B59 rules
out, and 0x3B4E's new reading depends on it. `ec/decompiled/` was re-exported
(73 files against `main`, **no instruction line changed**), the record pin holds
at 1,877 with its history comment recording that, `subsystems.md`'s census moved
169 → 157 and 269 → 267, and the four citation figures in `call-graph.md` were
re-measured because the new comments cite more addresses. **No register
`status:` changed, no `registers.yaml` row was added, no hardware was involved,
and no Ghidra project was written** — the export-only build copied the committed
project to scratch.

## 31. `--export-ownership`'s two refusals are pinned too, and the direction reverses (2026-09-25, issue #604)

The write-up is
`docs/findings/xdata-export-ownership-refusal-contract.md`; this is the
summary. The second census flag's pair of refusals — the same two guards, for
the same two reasons, immediately above the same dispatch as `--no-eq-guard`'s
— was held by nothing, and the gap was one flag short by accident rather than by
design: the tripwire mocks all nine of `main()`'s mode entry points and never
reads the flag argument, so it covers a second flag for free. The `Refusals`
cases now loop over both flags as `subTest` runs, so a failure names the flag it
is about and a duplicated class — the copy that stops being updated when a guard
is rewritten — cannot exist. **The accepted run is the one genuinely new piece,
and its direction is the mirror image of §29's:** `--no-eq-guard` removes a
rejection so the `write` total can only rise, while `--export-ownership` turns a
de-duplication pass *on* so the `refs` total can only fall (14,822 → 9,404). The
sibling's `assertGreater` is therefore not reusable here, and the new case
asserts `assertLess` and is named for the direction. Every figure is asserted
as a **relation**, never a count, and the pinned numbers stay on
`xdata-export-ownership.md` §4-§5: the sign, both sides of the `cluster_key`
renumbering (35 of 430 break, 395 survive) and of the hand names (5 of 10 break,
5 survive), and `no address is lost` — the one thing the pass must never do, and
the one `--self-test` cannot be the route to, for the same reason the flag is
refused with it. All four guards were broken in a scratch `ec/` copy to show
the suite goes red with `Lists differ: ['write'] != []` or `['check']` /
`['self_test']`, with the mirror's census CSVs byte-identical after each;
`--no-eq-guard`'s half stayed green throughout, because its guards are not what
was broken. `tools/run-tests.sh` is **21 of 23 suites, 609 tests** on this tree,
and the two failures are §29's own — `test_check_site_census.py`'s `D091.c`
line-pin drift and `test_xdata_cluster_names.py::TheGuardOffRegeneration` — both
of which reproduce on a pristine `main`. The two suites that had gone red since
§29 was written, `test_export_ownership.py`'s `FUN_CODE_7401` and
`test_check_cluster_citations.py`'s §26 prose, are green here because `main`
re-exported the tree under them in the meantime, not because this work absorbed
them. The census pair moved for the same reason and by the same hand: #267's
three `registers.yaml` rows take `refs` to 14,822 and the de-duplicated 9,404,
moving `read` by three on each side and nothing else. Every relation above is
unmoved by that, which is what relations are for. Nothing here is an EC
finding, no register `status:` changed, no census
CSV was regenerated, and `--check` is green before and after, which this issue's
requirement reads as "this changed nothing about the verdict". #591 (the
`export_ownership.py` tool in no gate), #512 and #528's recipe regression are
left open and untouched.

## 32. The export-ownership page's census figures are re-derived, seven cells corrected (2026-09-25, issue #654)

The write-up is
`docs/findings/xdata-export-ownership-page-census.md`; this is the summary.
`ec/annotations/xdata-export-ownership.md` measured what `--export-ownership`
does to the census on a tree from before #267, and had been left quoting it
after the tool's own `ORACLE` and `OWNERSHIP` were re-pinned for that change.
Every figure on the page is re-derived here from a fresh run of the two
commands the page's §5 already prints, and the page is edited only where that
run disagrees: **seven cells, all of them the census pair and the `read`
bucket**, now 14,822 / 9,404, 13,964 / 8,546 and 8,344 / 4,923. **The other
twenty-one re-derived and held**, which is the more useful half of the
result — the two `main-ec-003` rows, the `export_ownership.py` class figures
and the whole of §3's body-floor prose are all confirmed rather than assumed
away. The two cases where "the oracles say so" would not have been enough are
recorded for what they are: **main-EC `refs` is printed by no oracle-asserted
table** (§31's has no main-EC row) **and `--self-test` does not assert
`OWNERSHIP["main_refs"]`**, so it is read off each run's own per-group stdout
line; and **the two `main-ec-003` rows are in no oracle at all**, so they are
re-derived by taking the committed row's 43 addresses and reading them back
*by address* — a lookup on `cluster_id` is the wrong recipe, because the pass
renumbers the cluster and the id lands on a different membership. That recipe
was accepted only after it reproduced 4,988 and 4,966 on the default side,
which is the test of whether it is the right one. §31's deferral sentence stays
where it is, with the correction beside it, and no suite gained a pin: these
stay page measurements, for the reason §31's *Calibration* section gives. No
register `status:` changed, no census CSV was regenerated, both committed CSVs
are byte-identical before and after, and `--self-test`, `--check` and the
21-of-23 suite run are unchanged. #583, #614, #588, #582 and #591 are left
open; the same pre-#267 pair on `xdata-06c2-06db-timers.md`,
`xdata-register-map.md`, `ec/README.md:226` and the rest of this file's census
prose is #583's and is not touched here.

## 33. The 656 unannotated `common` functions, ordered, and the first 37 (2026-09-25, issue #603)

`ec/annotations/subsystems.md` §2 measured 656 of the 753 `common`-area
functions as unannotated — 87% of the program, the largest undecoded block in
this repository. A size is not a queue, and §2 said so itself. This is the
queue: `ec/tools/rank_common_runtime.py` orders the **455** rows no other open
issue owns, by inbound call-graph degree, then XDATA read+write weight, then
address, and the ordering is committed as
`ec/annotations/common-runtime-ranking.csv` so the next tranche is a cut over
that file rather than a re-derivation. The write-up is
`docs/findings/common-runtime-tranche.md`; this is the summary.

**The 455 is 656 minus 201**, and the 201 are #574's `0x1150`-`0x1ABC` block,
excluded **by address** and not by a hand-typed skip list — #555's
`bank1:0x8001`-`0x8189` window contributes **0** because the common area ends
at `0x7FFF` (printed as a measurement, not assumed), and #456's five boundary
rows all carry rows already. The block's unannotated rows run `0x116E`-`0x1800`,
not `0x1150`-`0x1ABC`: the two ends are already annotated, so #574's band is the
remaining two-thirds of a partly-filled block rather than a gap.

**The cut is `inbound >= 4` unioned with reachability from the vector table**, a
predicate over the ranking rather than a round number, and it took **37 rows and
999 bytes of listing**. Reachability is a *column*, not a fourth sort key: its
12 roots are `discover_vector_table()`'s own, it reaches 13 unannotated common
functions, and folding it into the sort would let a 1-inbound vector-reached
address outrank a 12-inbound one for a reason the reader has to hold in their
head. The census effect: `common` unannotated **656 → 618** (87% → 82%),
annotated **97 → 135**, annotation rows **1877 → 1914**, `unresolved` **157 →
160** — the `before` figures are the tree this branch forked from, which
already carries issue #456's twelve retypings and issue #470's one `pd 0x11C2`
row, so this tranche's own movement is **+37** rows and **+3** `unresolved`, and
the `after` figures are the tree this landed on, re-measured rather than added
up. A **38th** index row moved, `common 0x10FA` — a bare `ljmp 0x0A74` the
exporter renamed when the tranche named its target, so a thunk picked up a name
for the routine it jumps to.

**The one correction worth carrying into the tool:** the XDATA weight must be
read from `xdata-registers.csv`'s **`functions`** column, not
`functions_touched`. The latter is a *count*; reading it as a token list yields
a weight of exactly **0 for all 455 rows** — which looks like a measurement and
sorts the pool on its address alone while appearing to have consulted a second
signal. The self-test runs both columns and asserts the wrong one gives zero.
The same trap sits one column over in `call-graph-callees.csv`, where
**`callers`** is a count and **`citing`** is the token list.

**A rank is a ranking, not a reading, and the tranche says so in its rows.**
`common 0x355E` ranks **first** in the pool on twelve inbound — and its listing
is **one `ret` byte**, reached by twelve `ljmp` from exactly two callers: a
shared epilogue, not a mechanism. Inbound count does not guarantee smallness
either; nine of the 37 are over 16 bytes and five of them are large, and a large
row is not an unread one — four of the five carry a mechanism (`0x0C86` is the
`dispatch`, the other three `state`), with only `0x43A5` landing
`type: unresolved` because the bytes do not carry one, which is a correct
outcome rather than a failure.

**What the 37 turned out to be** is in the write-up; the two results the
ranking could not have predicted are the EC's **background dispatcher at
`0x0C86`** (195 bytes, eleven polled flag bits each with its own callee, fourteen
branches back to its own entry) and the **Timer 1 window** the `0x0E72`/`0x0E7D`
pair opens and closes around the `0x05B6` handler's body. `0x05E7` — the one
vector target §3 recorded as carrying no row and no citation — is in the tranche
by the reachability arm, and that blind spot is closed. No `registers.yaml` row
was added and no `status:` moved: the tranche's 37 listings reach **25** distinct
XDATA addresses — 24 loaded by a `mov DPTR,#imm`, plus `0x0A4E`, which no
immediate names and `0x2E9C` reaches by `inc DPTR` — and **not one** has an
`addr:` row in the map, so the generated `ec/ghidra/xdata-symbols.csv` is
untouched.

**Two defects in the annotation layer's own grading** surfaced and are *not*
fixed here, because each would re-grade rows across the whole file and is
merge-hostile: `grade_name_basis.py`'s `SFR_WORDS` pairs `timer0`/`tr0`/`tf0`
with `0x89`/`0x89`/`0x8A`, but `TR0` and `TF0` are `TCON.4` and `TCON.5`, i.e.
bit addresses `0x8C` and `0x8D`; and its `listing_facts` reads a
`mov R0,#0xNN` immediate as an SFR bit operand, so a name citing an indirect
internal-RAM base can earn a `register-map` grade on a value the architecture
says is not an SFR. The 37 rows' names are shaped around both, and the write-up
says so.

## 34. A `--csv` probe capture's mark spacing now has a guard at the tool's end (2026-09-25, issue #665)

Issue #665: `windows/tools/manual_fan_ctrl_probe.py` took `hold` with nothing
checking it, and at or under the grader's `MARK_MERGE_SECONDS` (5 s, where
equality coalesces) its three marks fold into one window — a capture with no
block to read out of. A `--csv` run under the floor is now refused with
`sys.exit(msg)` before the EC is opened, the constant is restated rather than
imported (the tool runs next to `ecrw.py`, off the repository layout) and
pinned against the real grader by its own suite, and a short hold with no
capture is deliberately *not* refused. No EC was opened and no register read.
Write-up: `docs/findings/probe-hold-mark-merge.md`.

## 35. The bytes a function boundary cut out of a citing listing, measured (2026-09-25, issue #560)

The write-up is `docs/findings/citation-gap-scan.md`; this is the summary.
`citation_callers.py` cannot reach a call that Ghidra's function boundary cut
out of the citing row's own export, and the population
`docs/findings/citing-listing-evidence.md` measured and could not classify — 99
citing rows, 124 `(callee, citer)` pairs — is it.
`ec/tools/citation_gap_scan.py`
walks the image bytes from each listing's end to three past the next exported
entry in its own scope, decodes that window with `disasm8051.py`, and returns
one of three verdicts: **2 `boundary-cut`, 121 `no-transfer`, 1 `not-code`**. The
issue's premise is the exception — **86 of the 99 rows have a zero-byte
window**, so for most of the population the question is the head of the
neighbouring export rather than bytes stranded between two. One boundary cut is
the issue's own `bank1,E57E` example, and it is also the ranking's **rank 3**:
`bank1,E5D6` reads `cited_by=3` / `inbound=1`, its one inbound being
`bank1,E5A7`'s `lcall` rather than the cut `lcall` at 0xE580. The second is
**§33's rank-1 row** — `common,355E`, the one-`ret` shared tail, whose 25-byte
gap to the next `common` export ends in that neighbour's `ljmp 0x3459`, so the
head-of-the-neighbour case the lead section describes turns out to carry a real
transfer. **32 of the 124 pairs** already have a same-scope transfer to their
callee booked to a neighbouring function, and **15 of the 90
`cited_by == inbound` agreements** in `call-graph-callees.csv` are carried that
way — the two columns counting different call sites. `call_graph.py` is
unchanged and its 1,841-row table is byte-identical; the issue asks what the
split means for the ranking, not for the ranking to move. *(Two corrections to
the plan's figures, both in §35's file: the plan measured 100 rows / 114 pairs;
five more comments took it to 105 / 123, and §33's 37-row tranche then took it
to 99 / 124 — that move runs both ways, its re-derived call graph dropping
twelve rows that no longer cite anything while six of its own new listings join
as citing rows. The predicate is unchanged, and the pins, the 9-and-one
zero-gap split among `common` citers and the commands are all there.)*

## 36. The `bank1,0xE582` entry is reached through 0xE580, and the census row at 0x9F03 is the phantom (2026-09-25, issue #680)

The write-up is `docs/findings/bank1-e582-entry-framing.md`; this is the
summary. Issue #680 asked which entry the contested `bank1,0xE582` routine is
actually reached through, and the answer is **0xE580**: the routine begins at
0xE57E with `push 0x07` and 0xE580 is the `lcall 0xE5D6` inside it, reading
*through* 0xE582 to complete itself. **The false positive is the other census
entry** — `bank-call-targets.csv:4420`'s `ljmp 0xE582` at 0x9F03, which is the
displacement byte of the `80 02 sjmp` at 0x9F02, and whose target `e5 82` is the
committed `bank1/9F04.asm` first instruction, `MOV A, DPL`. A linear decode from
0x9F01 rejoins that listing at its own head, so the misframed read is displaced
by a positive alternative rather than merely unbacked — `bank-call-audit.md` §9's
argument, on the same shape, and the reason that section adjudicates census rows
in prose: the table is `audit_call_targets.py --csv` output and regenerates byte
for byte, so **row 4420 is not edited**.

The limit travels with it. `frame_onto`/`frame_over` is "evidence about
framing, not proof of it" and `bank0,D091` is the standing warning that a data
island decodes as convincingly as code; what carries the reading is the byte
pattern, not the score. The `own_bank`/`other_bank` half of the two rows is
deliberately *not* counted as corroboration — `byte_class` is
`find_banks.py`'s `START_OPCODES` heuristic, "a scoring aid, not a decode", and
for a site whose byte *is* `0x12` the `entry` reading is true by construction.

Both `bank1,0xE57E` and `bank1,0xE582` carried the same now-false clause, so
both are corrected **in place** with the superseded wording left visible, in the
`common,0x158E` idiom; correcting only the row the issue names would have left
the pair contradicting itself a line apart. The two `.c` exports were
regenerated (`--mode export-only`, plate comment verbatim) and their two digest
rows rewritten. **No function entry is seeded at 0xE580** — it is the `lcall`
inside the forwarder, and seeding there would split it in half — so no
`--mode rebuild-project` is needed. Retiring the now-unjustified `0xE582`
entry *does* need one and is filed as the named follow-up, together with
crediting the 0xE580 `lcall` to the call graph, where `bank1,E5D6`'s
`inbound=1` is a known undercount. `call-graph-callees.csv` stays
byte-identical. No register `status:` moved, no hardware, no Windows.

## 37. The probe's watch set can be §3's first watcher, whole (2026-09-25, issue #666)

The write-up is `docs/findings/probe-0700-whole-page-arm.md`; this is the
summary. Issue #666 asked whether the `0x0751` probe should close §4.4's
whole-page gap, and both acceptable ends are now decidable against the
arithmetic §3 already prints: the page arm is **not a new traffic figure** but
§3's own three watchers in one process, `0x100 + 0x60 + 0x60 = 448` ECRR reads
and `112` `--block` IOCTLs over the same three ranges, so
`windows/tools/manual_fan_ctrl_probe.py --watch-page` reproduces §4.4 whole in
one console where a default run does not. It is **opt-in, takes no address and
substitutes** the page for the 14 of `WATCH` rather than adding to them (all 14
are inside the page, so adding would report a 270 no configuration sweeps), so
the tool's 206-read default stays as committed — the committed 2026-09-23 run
was taken at 110, its own header recording no temperature range, so 206 is
what a later run would sweep and no committed run was taken at it — the
fan-tach page stays unreachable by typing and by construction across all four
sets, and the only byte the tool writes is still `0x0751`. It is also the one
configuration where `block_ioctls` matches the naive division — 112 *is* the
448/4 the default's 56 is not — with no padding at all. **The flag has never
been run**: no EC, no Windows box, no vendor driver, on this machine or any
other, and no register `status:` moves — the page arm widens what a human can
observe, not what is known. The default's 87%-over-110 footprint is unchanged
and pinned, and the §3b note in the runbook keeps its text with a dated
correction beside it.

## 38. Whether the kept citation names the neighbour's call site, decided per row (2026-09-25, issue #681)

The write-up is `docs/findings/neighbour-edge-attribution.md`; this is the
summary. §35 measured that 15 of the 90 `cited_by == inbound` agreements are
carried by a transfer the graph books to a neighbouring function, and stopped
there: a `neighbour_edge` column said the two columns *could* be counting
different call sites without saying that any particular row does. **All 15 have
now been read one at a time**, on the *kept* citation rather than the population
pair — for 7 of the 15 those are different rows, and the population pair is a
rejected or undecided mention contributing nothing to `cited_by`.

**The split is 9 where the kept comment names the neighbour's own site and 6
where it names a different one**, and the mechanical screen for it — is the
`neighbour_edge` address in the callee's `citing` list? — comes out
**identical to the verdict on all 15 rows**. That is a measured fact about 15
rows rather than a rule, and it is the cheapest check a reader can run. The six
name, among others, 0xD607 where the graph books 0xD662, and 0x5A5A as the tail
of a data run where the graph books a real `lcall` at 0x0049. The two
population callees among the 90 that carry no such signal, `common,451A` and
`pd,06EA`, were read the same standard and both agree one-for-one, so **§35's
conclusion for them stands while its stated reason is corrected in place
beside the original**: the sentence is true of the kept citing row, not of the
population pair, which is a rejected data-frame mention whose own listing
carries no transfer. The file also records what a recovered edge would need
before it were credited — an independent re-measurement, a boundary that
survives a re-decode, and its own `call_graph.py --check`. No CSV moved, no
re-export, no register `status:`, no hardware. *(Two corrections to this
change's plan, both in that file: the plan put the population-pair count at 11
where the committed tables give 7, and read `bank1,DEC4`'s contrast mention as
the graph booking `9A78` as a caller — it books `DEA5`, and sides with the
comment's denial of its own site. The split, the verdicts and every site address
reproduced.)*

## 39. `spelled_as` is a union across programs, and the CSV now says which half is which (2026-09-25, issue #709)

The write-up is `docs/findings/xdata-spelled-as-union.md`; this is the
summary. `ec/annotations/xdata-registers.csv` records one `spelled_as` per
address, and on a `program=both` row that cell is every spelling *either*
program gives that address number. The file could not answer a per-program
question, and on one row it was wrong read that way: `0x04A3` reads
`DAT_EXTMEM+pair-literal`, while the main EC spells it `pair-literal` (7
references, all through an accessor) and the PD image spells it `DAT_EXTMEM`
(1). §4.7 of `ec/annotations/xdata-register-map.md` had the two numbers right
and the reconciliation living in a Python comment.

**The CSV now carries the per-program halves** in a new last column,
`spellings_by_program` — `main-ec=<spellings>` on a main-EC row, `pd=<…>` on a
pd one, `main-ec=<…>;pd=<…>` on a `both` one — so `0x04A3` reads
`main-ec=pair-literal;pd=DAT_EXTMEM`. It is **appended, not inserted beside
`spelled_as`**, because committed `awk -F,` commands in
`xdata-census-totals.md` and `xdata-export-ownership-page-census.md` read this
file by field position; `$6` still sums `refs` at 15,696 and `$7`-`$11` still
the five buckets. **The 58/156 and 59/155 are both still right** and are now
pinned side by side, with `PAIR_UNION_ONLY = (0x04A3,)` as their symmetric
difference and three `--self-test` assertions — all reading the committed file,
not a fresh generation — holding the column's contract on every row, the four
`both | DAT_EXTMEM+pair-literal` rows' real composition, and the
58 + 156 == 59 + 155 == 214 reconciliation. The 15 `both` rows whose halves
differ and the four `pair-literal` ones are in the write-up; so is the union
that **remains**, the `refs` and the direction buckets on a `both` row, with
the four rows' per-program reference figures rather than left to be found.
Nothing was retracted: no register `status:` moved, `xdata-clusters.csv` did
not change a byte, no re-export, no hardware, no Windows. The follow-up this
opens is per-program `refs` / bucket columns, and re-keying §2's `both` rows
per program, which would take that table's `distinct` total from 1,326 to
1,375 and invalidate three superseded-table blocks — its own change, with its
own corrections.

## 40. The 107 `inc DPTR`-only bytes: the rule stated, the 73 declined, all 107 accounted (2026-09-25, issue #707)

The write-up is `ec/annotations/xdata-inc-dptr-only.md`; this is the summary.
§4.7 of `ec/annotations/xdata-register-map.md` counted 107 addresses the pair
pass reaches *only* as the `inc DPTR` half of an accessor's pair, 73 of them with
no `MOV DPTR,#addr` encoding in the main EC, and declined to enter any — correctly,
since a rule change needs a decision and not a pass. This is the decision.

**The 107 are all accounted for: 73 declined, 7 already entered, 27 not.** The
73 is **71 + 2** — the two are `0x043B` and `0x04A5`, whose only `MOV DPTR` sites
are in the pd image, which is another program's byte at the same address number
and not a second site for the main EC's. The 27 have a main-EC site and no entry,
which is §6's existing rule applied consistently, and **none of the 27 is on the
`0x0400`-`0x045F` page** while all four page addresses among the 34 are already
entered — so no existing rule governs them and they are named as a follow-up
rather than entered on one. Every row is in
`ec/annotations/xdata-inc-dptr-only.csv`, produced by the new
`ec/tools/inc_dptr_sites.py`, whose `--check` regenerates in memory and diffs it
byte for byte with no Ghidra, no image and no hardware.

**The list needed a tool because the census CSV cannot answer the question.**
`scan()` folds a pair call's seed and its `+1` into one `pair-literal` row, so
174 of the 214 pair-reached rows have a `+1` neighbour spelled identically and
the seed/`+1` distinction exists only inside `pair_sites()`. On the committed
tree the two halves are **disjoint** — 107 + 107 == 214, measured on every run
rather than assumed — and the eleventh address in the 73 is `0x0364`: §4.7 names
**ten** and says "and 63 more", which closes on 73, while the issue's prose called
them eleven.

**The pair accessor is a second admitting encoding, and the 73 are declined
anyway** — on a ground that is about what the two files are *for*, not about what
either found. `registers.yaml` is what `gen_xdata_symbols.py`, the Ghidra project
and an upstream driver treat as the register list, and the census is a per-`.c`
lower bound on the machine code (an *upper* bound over the overlapping exports
§4.7 measures); admitting on it would make the census an authority on the thing it
is a lower bound for. The rule is edited into §6 of
`ec/annotations/xdata-0400-045f.md` **in place** rather than added beside it, so
the two are one rule and not two. `0x0420` is the counter-example that keeps the
rule narrow: the same bare-hex spelling, but `add_full_product_to_dptr` is
`mul AB / add A,DPL / addc A,DPH / ret` with **no `movx` at all**, so it
dereferences nothing and the address space is a property of the callee's body,
not of the token. **The issue's claim that "the 73 are not a census figure" is
retracted** — they are: 196 references, all `pair-literal`-only, main-EC only.

Nothing entered `registers.yaml`, no `status:` moved, no `static_refs*` count
moved, no `.asm` or `.c` was hand-edited, and no hardware or Windows machine was
involved. The test suite is **not** in `.github/scripts/agent-gates.sh` — that
file is under `.github/`, which this branch's push token cannot write, so the
registration is a human's change and the page says so rather than implying CI
runs it.

## 41. `ec/tools/testdata/README.md` is held to the tree under it, and the gate wiring is prepared (2026-09-25, issue #727)

The write-up is `docs/findings/testdata-index-check.md`; this is the summary.
The index over `ec/tools/testdata/` is what a change greps to learn which
fixture holds which grader case, it is written by hand, and nothing reads it, so
a directory it does not name and a row naming a path that is not on disk are both
invisible. `ec/tools/check_testdata_index.py` now holds the two files to each
other in both directions: a directory no index names is a gap, and a path the
index's table names that is not on disk is a miss. **Those two are the error
class, and not a repair history**: the index needed hand-repair twice, in #502
and #720, and both repairs were to a row's third column — the description — so
this check would have been green through both. Not claimed: that it would have
caught them.

**The merged tree is green, and that is the finding rather than a defect** —
13 directories, 12 named in the index, `call-graph/` self-indexed, 27 rows, 34
path tokens, 0 gaps, 0 misses, 0 unresolved. The issue is that nothing *checked*
that, not that anything is wrong; the gaps it now closes have simply never
occurred. `call-graph/` passes on a structural rule — a directory with its own
`README.md` — not on an exemption list, and the `...-suffix.csv` shorthand is
resolved by glob rather than by splicing, because a
check that false-positives on the abbreviations is worse than none. A token whose
shape matches no rule is reported as `unresolved` and does not fail the run: that
is the "not found by this method, never absent" line made mechanical.

**The suite is what runs today; the gate arm is not.** Its 28 cases hold the
refusals — a directory with no row, a row with no file, a prefix passing on a
sibling's row — and seven deliberate loosenings of the tool were each caught by
them. The cheap-tier wiring is prepared as half of
`docs/ci/agent-gates-capture-claims.patch` and a human lands it with `git apply
docs/ci/agent-gates-capture-claims.patch`; it shares that file with
`check_capture_claims.py` because the two `gate` lines sit at the same anchor
and cannot both be landed, in either order (issue #745). **Until then no commit
runs the check**, and `docs/agent-pipeline.md` carries it across a template re-copy as
its item 9. This is tooling hygiene, as the issue says: two committed files and a
directory listing, no capture opened, no EC, no hardware, and no claim that any
fixture is correct.

## 42. The testdata-index suite's three tallies are a property of a run, not of today's tree (2026-09-25, issue #744)

The write-up is `docs/findings/testdata-index-suite-count-floor.md`; this is
the summary. §41's suite asserted the committed tree's three tallies as
`assertEqual((directories, rows, tokens), (13, 27, 34))`, three lines under a
comment saying the opposite — "nothing says the numbers have to stay where they
are, only that a run reaching nothing fails" — so the correct response to the
event that branch was about, a fourteenth fixture directory arriving, was a bare
`(14, 28, 35) != (13, 27, 34)` from the one test named for reaching something,
while `test_the_committed_index_and_tree_agree` stayed green throughout because
the index and the tree did still agree. **The tool was never the thing that was
wrong**: `check_testdata_index.py:77-82` already stated "there is no floor on
either number … the suite asserts non-emptiness instead", as
`tools/run-tests.sh:77-79` declines the same trade about its own counts; after
this change that sentence is true rather than aspirational, and the tool file is
untouched.

The rule is now one root-parameterised method, so a run over a scratch tree and a
run over the committed tree are held to the same clause, and five cases pin it
from both sides: a tree carrying more of them than today and one carrying fewer
are both green — a new directory and a row added, a removed one and a row
dropped, with no integer anywhere to edit — while an empty tree, an index
carrying no row beside a tree that has one, and a tree with one token per row are
each refused, and each refusal asserts *which* clause said so. Three deliberate
weakenings of the replacement are each caught by the case naming them, and a
throwaway copy of the tree carrying a real fourteenth directory and a real row
for it is green at `(14, 28, 35)` with no committed fixture added. Still tooling
hygiene: strings in a `tempfile` and two committed files, no capture opened, no
EC, no hardware.

## 43. The prepared gate patches compose, and a test says so (2026-09-25, issue #745)

Each `docs/ci/agent-gates-*.patch` header says `git apply
docs/ci/agent-gates-<name>.patch`, "and that is the whole change", and
`docs/agent-pipeline.md` items 4, 5, 7 and 9 repeat it. Measured on this tree,
none of it held. `agent-gates-0751-self-test.patch` applied to nothing — and
**both** of its hunks were broken, not the one the issue named, because `git`
stops reporting at the first failure and the second hunk's trailing context had
moved 47 lines down the file. `agent-gates-capture-claims.patch` and
`agent-gates-testdata-index.patch` each applied cleanly alone and could not be
applied after one another in either order, because both inserted a function at
the same anchor below `check_register_counts()` and a `gate` line at the same
anchor in a seven-line list.

So the two are one file: `check_testdata_index()` folds into
`agent-gates-capture-claims.patch`, the second is deleted, and the six
references to it across four files are repointed. The 0751 patch is re-cut
whole against the committed blob and given the `index` line it was missing, and
item 4's long-documented-but-never-written `verify_gap_text.py` wiring is now a
third prepared patch. `tools/test_agent_gates_patches.py` holds the result: the
set on disk equals the set the suite names, each patch applies alone, every
ordered pair lands, the full set lands and still parses under `bash -n` and
`shellcheck`, the fold is still whole, and each header names its own file.

One thing the plan this branch was built from got wrong, found by running the
check rather than confirming the file existed: `verify_gap_text.py --check` was
**red**, on one stale `row_name` column left by a function rename. Preparing
item 4's patch without regenerating it would have prepared a trap — a human
following the header would have landed a red cheap gate, which is the cheapest
way to make a gate get switched off. The CSV is regenerated here by the tool's
own `--report`, one row and one column, no assembler.

The 0751 suite's count is 103, measured by running `--self-test`; the header
said 76 and the issue said 94, and neither was right for long. The other places
the figure appears are #685's, named by path in the write-up rather than
overwritten here. Write-up:
`docs/findings/prepared-gate-patches.md`.

## 44. §4.4's cluster-identity figures, re-run against the committed census (2026-09-25, issue #582)

The write-up is
[`xdata-4-4-identity-rederivation.md`](findings/xdata-4-4-identity-rederivation.md);
this is the summary. `ec/annotations/xdata-register-map.md` §4.4 opens by
promising that "Every number below is a command re-run over the committed tree"
and then quotes a census the tree no longer holds — the block was measured
against 427 clusters, and `xdata-clusters.csv` has held 439 since issue #279's
pair-accessor pass moved the clustering again — 427 → 430 at issue #327's
unnamed-callee pass, 430 → 439 at #279.
*(Correction, 2026-09-25, issue #582. This sentence used to read "the block was
measured against 427 clusters and `xdata-clusters.csv` has held 439 since issue
#256's regeneration, with issue #279's pair-accessor pass moving the clustering
again", which cannot both be true of the count and of the order. #256
(`88a0e0ba`) left `xdata-clusters.csv` at 430 rows and
`xdata-cluster-names.csv` at ten on either side of it — `git show
88a0e0ba^:…` against `git show 88a0e0ba:…` — and 430 → 439 with the names file
at nine is `6bf9c234`, #279. The wrong version is kept here rather than edited
out, per §4a; the full derivation is in
[`xdata-4-4-identity-rederivation.md`](findings/xdata-4-4-identity-rederivation.md)'s
"Which tree §4.4 was measured against".)*
Re-running the block's own recipe with the flag that now does what its
workaround did (`--no-eq-guard`, `xdata_register_map.py:4568`) gives 439 → 445,
124 ranks intact and 315 changed, 424 keys unchanged, 434 committed rows
reaching a new cluster, 15 clusters a key cannot carry (10 on overlap, 5 on
nothing), nine names carried and 430 committed clusters with a key and none.
Every superseded figure stays visible beside a correction naming the tree it
belongs to, which is the shape the section's own #256 and #279 corrections
already use, and §4.2's `479` — a half the console block beside it had already
left at `507` — is corrected the same way, closing both halves of
[`xdata-census-totals.md`](findings/xdata-census-totals.md)'s follow-up 4. The
census CSVs are inputs and stay untouched: the tool refuses `--no-eq-guard` with
the committed output paths, so the re-run is a report about the committed tree
and not a replacement for it. **Four of the five replacement figures issue #582
proposed do not survive a check against the committed tree**, and the 430 it
keeps citing is the tool's own `with no name 430` line rather than a row count —
the conflation the issue itself warns about one paragraph later, so the re-run's
figures are what the block now carries and the disagreement is written down
rather than pasted. Two things this pass found that are not figures:
`ec/tools/test_xdata_cluster_names.py` is **red on `main`**, because its `GUARD`
literal predates the parameterised guard at `xdata_register_map.py:1582` and
its two-largest case pairs ids with names a generation behind — reported, not
edited around, and a follow-up rather than a line to move inside a
documentation change; and `test_xdata_cluster_names.py:286` carries a
third-generation figure in its docstring, recorded rather than fixed.

## 45. The testdata index's `Feeds` column and its self-indexed nested tables are read too (2026-09-25, issue #746)

The write-up is
[`testdata-index-feeds-and-call-graph.md`](findings/testdata-index-feeds-and-call-graph.md);
this is the summary. §41's "Left out on purpose" list named four things, and its
first two were the same rule family as what shipped — a path the index names
has to be there — so they belong with it rather than as a new idea.
`ec/tools/check_testdata_index.py` now reads **four** sources instead of two and
prints **four** tallies instead of two: the top-level table's first column, its
`Feeds` column as tool references resolved against `ec/tools/`, and **every**
table in a self-indexed directory's own `README.md`, in the three shapes those
cells use — a relative `.asm` path resolved against the directory, a `X.csv` plus
one or more addresses looked up in that CSV's `addr` column and compared as hex
integers, and both joined by ` + `. The measured tree: 27 `Feeds` cells over 29
pointers in 3 shapes and 4 distinct tools, and one nested index of 3 tables / 19
rows / 21 checks, all resolved, 0 missing, 0 unresolved. The parser underneath
was rewritten onto one table walker located by a table's **shape** rather than by
a header name, which is what keeps the nested rule structural instead of an
exemption list — the same argument §41 makes for the self-indexed clause, and the
reason the next self-indexed directory needs no edit here.

**It found one wrong cell.** `call-graph/README.md:16` read
`` `decompiled/common/0EA2.asm` ``; the fixture carries
`decompiled/bank0/0EA2.asm` and both committed CSVs say `bank0` at that address.
Nothing read those tables, so the cell has been wrong since it was written. The
fix is the index, not the rule — one cell — and it is load-bearing: reverting it
turns the run red with a line naming the exact missing path. **That is a
decidable static fact about three committed files, and it says nothing about
what the fixture exercises and nothing about the EC.**

**Calibrated, in the two ways that matter here.** A nested address is compared
as a hex integer because one address has three spellings and all three are live
in the committed file (`0x0EA2`/`0EA2`, `0xDEAD`/`DEAD`, `0x0070`/`0070`) — a
string compare would report a miss on every one. And the CSV lookup checks
**existence, not identity**: a row that exists at the address resolves even if it
says something else, because "the row the index names is in the file it names" is
the invariant and "and it says the right thing" has a different owner. The cost
is written down rather than left implied: a typo to an address that happens to
exist in that CSV passes. Anything the two new readers cannot parse is
`unresolved` and does not fail the run, so "not found by this method" is never
reported as "absent".

**The suite is what runs today; the gate arm is still not.** 59 cases, up from
33, and the tallies are still not a floor — one root-parameterised method over
all four lines, with scratch trees either side of today's size both green. **All
fifteen deliberate loosenings are caught**: the seven §41 records re-run because
the parser was rewritten under them, and the eight this branch adds. The
cheap-tier wiring stays prepared in `docs/ci/agent-gates-capture-claims.patch`,
regenerated so the human's `git apply` still lands — the gate line, the command
and both hunk headers are unchanged, and only the comment at the call site grew
the two new kinds of pointer. **Until a human lands it, no commit runs the
check.** This is tooling hygiene: two markdown files, a directory listing and two
CSVs, no capture opened, no EC, no hardware, and no claim that any fixture is
correct.

## 46. The runner's red set: two suites, and the third of #162's blocker was a missing table row (2026-09-25, issue #751)

The write-up is
[`runner-red-suite-set.md`](findings/runner-red-suite-set.md); this is the
summary. `docs/findings/0751-grader-self-test-gate.md` says **two** of the
suites `tools/run-tests.sh` runs fail here, and three were failing: the two it
names, both of them failing on their own subject, and
`tools/test_readme_suite_table.py`, which was red because
`ec/tools/test_inc_dptr_sites.py` had no row in `tools/README.md`'s suite table
— the one step a runner that finds its suites by `find` cannot do for itself.
That row has landed and the check is green, the count in the sibling file is
corrected in place beside itself rather than edited out per the §4a-4d pattern,
and no suite or test total is quoted anywhere new, because a total is a property
of the merge. **What it changes for #162 is the size of its blocker**: three
suites in two kinds — two judgements about the decompile with their own issues,
and one piece of bookkeeping — so whoever lands the four-line wiring re-derives
the set and finds two. *(Correction, 2026-09-25, issue #819: it now finds
**none**. Both suites this section names are green, as is the third, and §46's
own companion file already reaches the empty set at
`0751-grader-self-test-gate.md:163-175`; the measurement is in
[`xdata-green-set.md`](findings/xdata-green-set.md).)* `tools/README.md:14`'s
own counts sentence is #615's, is out of date, and is invisible to every test by
design, because the table check compares the *set* and never the counts; it is
byte-untouched here. No register
`status:` moved, no `.asm` or `.c` was hand-edited, no gate was wired, and
nothing was read off a machine.

## 47. The testdata index's third column is now held to the fixtures it names (2026-09-25, issue #747)

The write-up is
[`testdata-third-column-claims.md`](findings/testdata-third-column-claims.md);
this is the summary. §41's check reads the index's first column, its `Feeds`
column and the nested tables, and §45 added the two it was missing — but the
**third** column, the description, is the one a reader opens the index to read
and the one that names the addresses each fixture is supposed to contain, and
both of the index's hand-repairs (#502, #720) were to that column. Every check
on the index was green through both. **Not claimed: that this would have
caught either** — what those two repairs changed is in the issues, not in the
tree, and neither has been read back as a diff this tool could have been run
over.

`ec/tools/check_testdata_row_claims.py` is a **new file**, not a mode on
`check_capture_claims.py`, for the reason that tool's docstring records, and
it imports the same `units()` so issue #273's fix to the splitting logic lands
once for all three. The rule is the sibling's invariant aimed at a different
prose/tree pair: **an address a row's third column attributes to its fixture
has to occur in a file that row names** — searched across the whole set the
first column resolves to, never per file, because `0x075B` is in one of
`0751-isolation-run-staged/`'s three CSVs and in neither of the other two
while the row names the directory.

**The census came first, and it is the deliverable either way.** Over all 27
rows: 17 carry at least one `0xNNNN` literal, 54 in all, and they split
**28 resolved / 26 unresolved** — 14 rows, 14 distinct addresses, 28 claims,
all present in the fixture their row names today. The 26 are a **closed list
of six shapes**, each with a case: a capture or window bound (16), a denial
(3), another capture's address (2), a dump-command argument (2), a watched-set
span (2), and a firmware code address (1). That sixth one is the census's own
find rather than the issue's, and it is why the code filter is
`ghidra-functions.csv` **minus** `xdata-registers.csv` rather than either
alone: on this firmware `0x07D0` is both `FUN_CODE_07d0` and a door byte, and
it is a claim in two rows. **The list is five shapes and a variant since #794**
— a bare date in a third-column sentence is now resolved against
`evidence/ec-watch/<date>-*` and its literals are held to those files rather
than passed over, so the sixth entry above is a dated capture that *resolves to
nothing*; the counts in this paragraph are a 2026-09-25 measurement and are
left exactly as they stand, and
[`testdata-row-claims-dated-capture.md`](findings/testdata-row-claims-dated-capture.md)
carries the re-derivation and the three decisions in the rule.

**Three readings were measured rather than assumed, and each one is a rule.**
No `MOVEMENT` predicate: 18 of the 54 literals sit in a sentence carrying none
of its verbs and most are genuine claims, and the width is four hex digits
because `0x50 -> 0x28` and `0xA0`/`0x10` are the values the dumps and mark
labels carry. And a denial is read in **two directions**, because the two
committed denials are written in opposite orders and a proximity window wide
enough to reach the trailing one also reaches forward over row 9's `0x0746` —
a claim that is true today. The tool is green on the committed tree under the
final rule; with the six shapes removed it is red on **4 rows with 5 missing
literals** and calls **54 of the 54** literals claims. The six rules overlap —
four literals are caught by two of them at once — so a single shape's drop is
not additive and no per-shape counts add up to that run.

**38 cases, nine of which are refusals**: every rule is dropped in turn and
each is asserted to make the run *check more*, against the run as shipped
rather than against a figure, so an added fixture row breaks none of them.
Four of the six shapes cannot turn the run red by being dropped — the literals
they exempt genuinely are in the files their rows name — and the suite says so
in its own class docstring rather than leaving it to be found. The committed
tree's tallies are asserted as **non-emptiness**, never as a floor. The gate
arm is prepared at `docs/ci/agent-gates-testdata-row-claims.patch`, a patch of
its own that composes with item 9's in any order (item 10), and **until a
human lands it no commit runs the check**. This is tooling hygiene: two
committed annotation CSVs, a markdown file and a directory of fixtures, no
capture opened, no EC, no hardware, and no claim that any fixture constructs
what its row says.

## 48. The `0x0860` census citations move; the counts do not (2026-09-25, issue #752)

The write-up is
[`xdata-0860-census-sites-relined.md`](findings/xdata-0860-census-sites-relined.md);
this is the summary. §46's runner is red on two suites, and the first of them,
`ec/tools/test_check_site_census.py`, is now green: the four `census_refs` cells
in `ec/annotations/xdata-0860-census-sites.csv` are re-derived against the
committed `ec/decompiled/bank0/D091.c`, which #180 hand-corrected on 2026-09-24
and whose header rewrite moved the body out from under them. **The counts do not
change — only the line numbers do** (`0x0D091` → `45,49`; `0x0D0EF` → `71,72`;
`0x0D117` → `75,76,77`; `0x0D144` → `84`), and each row is justified by the
occurrences on the lines it now cites rather than by being the old number plus
one. The judgement is forced rather than chosen, and the write-up gives the two
constraints that force it: all 17 occurrences and every bucket total are
unmoved, and the per-bucket-totals clause **never fired**, before the change or
after. **The shift is not uniform** — 1, 1, 1 and **2** — so a blanket `+1`
would have left `0x0D144` red; it is written down for that reason. Six stale
cells in `xdata-086x-dispatch.md`'s site-by-site table, and the same numbers
repeated in `xdata-register-map.md` and in `HAND_CHECKED["0x0860"]`'s comment,
move with them — two of the `D281`/`D289` cells had been stale *before* the
`#180` rewrite, which no check covers, and the write-up says so rather than
letting a green suite imply the prose was verified. `XDATA_0860` stays
`present-untested`: a `write x2` census count is evidence the decompile holds
two stores, not that the EC acts on the value. Still tooling hygiene — four CSV
cells, prose line numbers, and a dated addendum to §46's sibling file, no
capture opened, no EC, no hardware.

## 49. The decoder's oracle is prepared for the cheap gate, and the placements are not where you would put them (2026-09-25, issue #798)

The write-up is
[`disasm8051-self-test-gate.md`](findings/disasm8051-self-test-gate.md); this
is the summary. `ec/tools/test_disasm8051.py:3-6` names `disasm8051.py
--self-test` as "the oracle for the opcode and mnemonic tables", and §3e's
`:355-356` rests a load-bearing claim on the same mode — that no 8051
direct-addressing opcode takes a 16-bit operand, so a `0xFFxx` value
"**cannot** be a direct address whatever anything spelled it as" — saying of
the 256-entry `OPCODE_LEN` table that "its own `--self-test` pins" it. The mode
ran in no gate, in either tier. It is green today (0.02 s over five runs) and
it is not run today, so the wiring is prepared at
`docs/ci/agent-gates-disasm8051-self-test.patch` rather than landed, for item
4's reason. **Until a human applies it, no commit runs it, and the PR does not
claim CI does** — applying it to a scratch copy and running that is a different
claim, and says so.

It holds **five** groups, 36 assertions, not the three the issue names: the two
`charge-profile-flow.md` windows (18 instructions), 4 `REL_SITES`, 11
`BIT_SITES`, the `0xC1`/`0xC2` pair stated from the manual because an oracle
derived from the tool under test asserts nothing, and the `paged_target()` page
edge. What it does **not** hold is in the write-up and the patch header, and is
not optional: it is not a disassembler check, 18 of 256 `OPCODE_LEN` entries are
covered by transference, and it says nothing about `decode()`'s bounds contract,
whose own suite `tools/run-tests.sh` collects and **no gate calls** — so both
halves of this decoder's testing are ungated today, in two different ways. It
also arbitrates none of the `0xA0`/`0xB0` `ANL`/`ORL C,/bit` disagreement
`disasm8051.py:176-186` leaves open on purpose, where no committed instruction
is affected either way.

One thing a reader will want corrected: the tool-list entry goes at the **end**
of the `for tool in` list and the arm after `*xdata_register_map.py)`, so
neither is beside its semantic neighbour. That is placement-for-composition —
§43's suite applies the set in every ordered pair, and `:129` is the only line
in the list outside the other four patches' context windows — and tidying
either one back breaks every-ordered-pair landing while each patch still
applies cleanly alone. `tools/test_agent_gates_patches.py` gains the path and
one new case, `ArmRetentionTests`, because a re-cut that kept the list entry and
dropped the arm would pass every other case in the suite and hand the tool
`--work "$scratch"` back. The deep tier's cross-decoder ratchet is **not** here
(#774 owns it), and neither is a gate call for `tools/run-tests.sh` (#775/#773).
Still tooling hygiene: a patch, a test, and pointers — no capture opened, no EC,
no register read back, and no hardware observation needed.
## 50. The guard-off census is built by the flag now, and pinned to §6a's own figures (2026-09-25, issue #753)

The write-up is
[`xdata-cluster-names-guard-off-recipe.md`](findings/xdata-cluster-names-guard-off-recipe.md);
this is the summary. `ec/tools/test_xdata_cluster_names.py` errored in
`setUpClass` because its guard-off recipe deleted a frozen spelling of the `==`
guard that #528 gave an `eq_guard and` conjunct in front of, so the replace was
a no-op and the assertion caught it. The recipe is now the mechanism the tool
already ships — `--no-eq-guard`, which §6a measures with and
`xdata-no-eq-guard-refusal-contract.md:250-259` had already scoped as the fix —
and the six cases the error kept out run again. The issue's own repair
(re-point the literal) was the alternative; it is recorded in the write-up with
the reasons the flag won, one of which is that a `source.replace()` which
stops matching fails *silently*, which is the failure mode the issue exists to
stop. **§6a needed no correction**: every figure it publishes reproduces on this
tree, 833 / 210 of 1,326 / 0 of 1,326 from its own printed heredoc, so the diff
stays off that page. What is new is a seventh case holding the census to those
*published* figures rather than to a fresh run of the same recipe, and the
`> 300` moved-ranks floor is left where it is at 315 measured rather than
lowered to buy the headroom. Four sentences elsewhere that this makes false:
two are recorded in the write-up rather than edited, and two are corrected in
place — `docs/findings/0751-grader-self-test-gate.md:109` and
`ec/tools/test_xdata_register_map.py:9-12`. The first of those **stands as
written**: `gh issue view 568` shows #568 open since `2026-09-25T03:03:44Z`,
naming this defect and this flag, so #528's failure did have an owner; what it
lacked was a slot in the queue, and this issue is the re-file that supersedes
#568. No CSV, `registers.yaml` or `xdata_register_map.py` was edited, no gate
was wired, and nothing was read off a machine.

## 51. The green set is empty, and the status sentences that said otherwise now carry corrections beside them (2026-09-25, issue #819)

The write-up is
[`xdata-green-set.md`](findings/xdata-green-set.md);
this is the summary. Both modes of `ec/tools/xdata_register_map.py` exit 0 and
both suites that read its CSVs are green — and **two commits cleared them, not
one**: `23240095` (#752) for `test_check_site_census.py`, `64dbde19` (#753) for
`test_xdata_cluster_names.py`, which now runs the tool's own `--no-eq-guard`
instead of patching a copy of it. That is why the sentence naming both as red
for "their own separate reasons" was wrong twice over, each half for its own
reason. **Five sites across the two annotation pages were false, and each is
corrected beside itself rather than over it**, per §4a-4d: in
`ec/annotations/xdata-register-map.md`, "two other suites that read these CSVs
are red for their own separate reasons" and that block's own closing "that
leaves **one** suite of the two red"; in
`ec/annotations/xdata-06c2-06db-timers.md`, "neither is green today: both exit
1 on `main`", "**Neither mode is in `agent-gates.sh`'s tool list**" — false of
`--check` from #256, and contradicting `xdata-register-map.md:2582-2584` for as
long as it stood — and the page's second phrasing of the same claim. **The fifth
is the one the issue's table splits across two rows**, and correcting one copy
while leaving the next would have reproduced at
`xdata-register-map.md:2606` exactly the defect the issue is filed about; a
reviewer who prefers the issue's own count can drop that one blockquote and
nothing else moves. The empty set is therefore what
[`runner-red-suite-set.md`](findings/runner-red-suite-set.md) now tracks.
**Three sibling claims are named to their owner rather than absorbed here**:
the `--self-test` half of both pages is **#815**'s — the naming drift, the
gate's `--self-test` reason comment at
`.github/scripts/agent-gates.sh:218-234`, and the wiring decision — **#816**
owns its "only working scripted route to a guard-off census", which the same
`64dbde19` falsified, and **#817** owns `tools/README.md`'s "874 tests" and its
"two of the thirty are red". `agent-gates.sh` is named and not edited: it is
copied from `ElDavoo/agent-pipeline`, and #815's title covers it. No suite or
test total is quoted anywhere new, for the reason
[`runner-red-suite-set.md`](findings/runner-red-suite-set.md) gives when it
leaves the totals line out — a total is a property of the merge, and what the
corrections quote instead is one command each, which is what a re-derivation
actually runs. No `status:` moved, no CSV, YAML, tool, suite or gate script was
edited, no `.asm` or `.c` was hand-edited, no hardware or Windows step was
taken, and nothing was opened in another repository.

## 52. `tools/README.md`'s totals are re-derived from a run, and the red set behind the total is measured (2026-09-25, issue #817)

The write-up is
[`tools-readme-totals.md`](findings/tools-readme-totals.md); this is the
summary. The three paragraphs of `tools/README.md` that carry the runner's
figures were quoting a red set and a total the tree no longer has: `874` tests,
"two of the thirty are red in this tree", and a last line reading `30 suite(s)
run, 874 tests; one or more FAILED` with the runner exiting 1. A fresh
`bash tools/run-tests.sh` at `64dbde19` prints **`All 30 suite(s) passed, 882
tests`** and exits 0, so the paragraphs are rewritten from that run rather than
patched from a diff — and the diff will not close, because the two deltas the
tree names give 881 and 883 and straddle the measured 882, with an unnamed −1
between them. *(Merged-tree note: `2ed6f030` (#822) added
`xdata-cluster-names-guard-off-recipe.md`, and one suite is red on that tree —
`test_check_cluster_citations.py`, on `:220` of that new file — so the
**counts** this section re-derives still hold at thirty suites and 882 tests
while the **verdict** is `30 suite(s) run, 882 tests; one or more FAILED`. It
reproduces on a clean `origin/main`, it is #822's file, and it is named in
`tools/README.md` and in
[`tools-readme-totals.md`](findings/tools-readme-totals.md) rather than fixed
here.)* **The total moves with *how* a suite was red, not only with
whether it was, and that mechanism is now measured rather than assumed**: a
class whose `setUpClass` raises contributes none of its own cases to `Ran N` and
the error is not itself counted (28 → 21 on `test_xdata_cluster_names.py`,
measured in-process), where an ordinary failing case runs and is counted like
any other (28). The two sentences that were true of the old text — re-derive by
running the runner, and the totals are not a pass — are kept in place rather
than replaced, and "this branch adds" is de-anchored to `#688`, which merged
four commits ago. **No count assertion was added to
`test_readme_suite_table.py`**: comparing a prose figure to a live run is a
count gate wearing a different hat, and §46's "finds two" and this file's own
two `Left out on purpose` bullets are left as dated records. No gate was wired
(#162 is unblocked by the evidence, not by this branch), no `.github/` file was
touched, and nothing here was read off a machine.

## 53. The opcode-table bounds shape, censused, and the one comment that named the wrong reason (2026-09-25, issue #797)

The write-up is
[`opcode-len-bounds-census.md`](findings/opcode-len-bounds-census.md); this is
the summary. Issue #679 fixed one instance of *read a byte out of a buffer, then
index `OPCODE_LEN` with it, before checking the buffer's end*, and wrote the
shape down for the first time. This is the census of the rest of `ec/tools/` for
it: **one grep, 39 lines, 25 sites in 20 rows** — the six the issue named
are a subset, not the content — with a measured verdict per row and the other 14
lines accounted for as docstrings, constants, dict values, byte values already
in hand, or the adjacent `audit_call_targets.py` last-byte read. The three
classes come out differently,
as they should: **eight rows where the bound is `len(d)` or clamped to it need
no change at all** (every one already has the guard or the docstring `decode()`'s
fix established), and **ten where the bound is not `len(d)` at all** get a verdict
rather than a guard — seven bounded by a caller's number, two by a count, one by
a region — because a `len(d)` check there would be testing something
other than the loop's own invariant. The deliverable is
`ec/tools/trace_xdata_refs.py:241-242`, where the comment `# DPTR reloaded: ...`
described the **second** disjunct of the guard and was silent on the **first** —
the `i + 2 >= len(d)` test that holds the index in range, since the loop's own
bound is `max_insns` and not `len(d)`, and the loop's other `len(d)` test (at
`:230`) asks whether the *instruction* fits and so permits `i + n == len(d)`.
**Restated as comment lines only; the fifteen-address `--check` sweep exits 0
before and after, which is what makes it a regression test rather than a
formality.** The restatement is
load-bearing rather than cosmetic because the two disjuncts do not fire equally:
driven from all 262144 offsets of `ec/firmware/GMxMGxx_11.800` the `MOV_DPTR`
test fires 26257 times and the bounds check **10**, all from starts in the last
10 bytes, and no committed caller passes a start there — so a reader who
instruments the tool is actively invited to conclude the bounds check is dead
code. It is not; delete it and the loop raises. **The issue's own vector does not
reproduce and the correction is left visible beside it**: `b"\x01\x00\x01\x00\x01\x00"`
is described as three non-flow instructions, but `0x01` is `ajmp`
(`disasm8051.py:61`), so `walk()` breaks on the flow test at the first
instruction with the guard present *and* deleted. `b"\x00\x00\x00\x00"` does
work — two instructions with the guard, `IndexError` on the fifth iteration
without it. `pd_index_geometry.py:600-601` gets **no guard**: its window peaks at
`0x3002C` against a `0x40000`-byte image, so it did not raise over the range run
— which is a statement about this input, not about the code, and a guard
justified by "it cannot happen here" would be a guard justified by an assumption.

*(**Qualification, 2026-09-25, §56.** The "no guard" and the `:600-601` are both
superseded: `check_site_addr()` now refuses a `--sites` address outside
`0x0000-0xFFFF`, and the listing is `:636-637`. The reasoning above still stands
about what that new check is *not* — it tests the caller's argument, not this
image's 262144 bytes, so `0x3002C` is still what bounds a *legal* address's
window and the instruction boundary is still unchecked. The census's row 10 is
retracted in place beside itself; the write-up is
[`pd-sites-address-range.md`](findings/pd-sites-address-range.md).)*

Nothing here asserts any site "cannot raise", no live test ran, no capture was
opened, and no EC or hardware was involved; the sweep bounds the table the way
`ec/annotations/registers.yaml` bounds a zero-result scan, and the
`converges_from` retraction at `docs/findings/citation-gap-scan.md:443-446` and
`citation_gap_scan.py:26-46` both stay exactly as they are.

## 54. The census re-derivation's cost is written down where the procedure is (2026-09-25, issue #820)

The write-up is
[`xdata-census-rederivation-checklist.md`](findings/xdata-census-rederivation-checklist.md);
this is the summary. §50 added a test that goes **red because the census was
re-derived**, and the response to that lived only in a comment inside the test.
The three places the tree tells a person or an agent to re-derive that census did
not mention it, so the tripwire was a surprise rather than a known cost. Each of
them now carries a one-line pointer to the checklist, which is four pointers
because the issue's third site is two sentences on one page: the export
instruction in `ec/annotations/xdata-register-map.md`, §4d above, and in
`ec/annotations/xdata-06c2-06db-timers.md` both §6a's closing paragraph and the
#279 re-derivation note beside it.

The checklist names the seven figures `test_the_census_is_the_one_6a_measured`
holds §6a to, and — the half the test cannot do — **the eight more in §6a's table
and §6b's console block that no test holds and which therefore decay silently**
(**three of those eight rows already had a check when this section was written —
two of them wholly, by `--check`'s cell comparison and by
`ORACLE["distinct"]`/`OWNERSHIP["distinct"]`/`OWNERSHIP["clusters"]`, and the
`157`/`858` pair for the *default* census only. This section also credited the
`1218`/`9320` to `OWNERSHIP["main_distinct"]`/`["main_refs"]`, which no
assertion read; §66 is where that is corrected, and it is what takes the count
from four rows with a check to three. The checklist's §2b heading said "unpinned"
for all eight and §66 corrects that in place, per §4a-4d, and **all five rows it
left open are now held** — four of them by §66's own named assertions and the
`1218`/`9320` by §60's `check()`, which is the one #849 and #850 reached opposite
conclusions about. The figure §66 adds to the list is the guard-off pd cluster
count `51`, which §6a does not print at all**),
the tool's `BUCKET_TOTALS` five, the `xdata-cluster-names.csv` re-key, and the
`> 300` moved-ranks floor at its measured 315 with the argument for leaving it
there. It states the response as the order the work happens, `--check` first,
and it asserts nothing about what a re-derivation *would* produce: every figure
in it is today's snapshot, marked as one, the way §6a's own re-derivation note
is. One of the eight is commonly mis-transcribed — the console block reads
`1326 rows` / `440 rows`, `1218 / 9320 / 390` and `157 / 858 / 50`, where
`14,838` is §6b's own table cell rather than a per-program total, and where §66
adds that it is `ORACLE["main_refs"]` and is asserted — so the
checklist quotes the page and names the trap rather than the wrong figure. No
measurement moved, no CSV, `registers.yaml`, tool, gate or assertion was edited,
no re-export was run, and nothing was read off a machine.

## 55. What holds the rel8 displacement read in range, and the census's other two tools directories, measured (2026-09-25, issue #847)

The write-up is
[`rel8-displacement-bound.md`](findings/rel8-displacement-bound.md);
this is the summary. §53's census excluded
`ec/tools/audit_call_targets.py:171,315`'s
`d[i + OPCODE_LEN[op] - 1]` from its 20 rows as a different shape and handed
one question back: whether that pair wants a check of its own. The answer is
that it does, and not the one the issue offered first. The guard in front of
the read is `i + OPCODE_LEN[op] <= hi`, and `hi` is `region_bounds()` — a
**constant** from `REGIONS` in `trace_xdata_refs.py`, not a bound on `len(d)`.
What keeps the read in range is `main()`'s PD-marker check, which is a genuine
length floor because a Python slice never raises, and which sits three frames
from the read in a different module. A `len(d)` clamp in `relative_sites()`
is out on the merits: `hi` is a region bound and every loop in the tool is
region-relative, so the true invariant is `hi <= len(d)` — a property of the
call sites, not of the loop, which is the same reason §53 gave rows 11-20 a
measured verdict rather than a guard. So the change is a note on
`region_bounds()` (the consumer, not the table — four of the thirteen modules
importing from `trace_xdata_refs` import `REGIONS` by name, and the claim is
about how this one reads it) plus one `check()` in the existing `--self-test`
harness, labelled as beyond the issue's ask and not load-bearing for the
verdict. **The issue's two arithmetic figures are corrected and left visible**:
the marker is ten bytes, not five, so the slice ends at `0x2004A` and the floor
is `0x2004A`, not `0x20045`; and the margin past the highest index `hi` admits
is **32843**, not 33061. The reasoning is right in every step and the last two
numbers are not. A snippet truncating the image one byte past a 3-byte form
shows the guard admitting a site the read cannot serve, which is what makes
the verdict defensible later. The census's other stated gap is closed by
measurement rather than by assertion: `grep -rn 'OPCODE_LEN\[' --include=*.py
bios/tools windows/tools` returns nothing, and the stronger reason is
structural — `OPCODE_LEN` is defined once, in `ec/tools/disasm8051.py`, and
nothing under `bios/` or `windows/` imports `disasm8051` at all. That is a
negative result and is recorded as "not found by this method", naming the
directories and the commands. Two code edits, a docstring and a `check()`:
the tool's tables and its `--relative-csv` are byte-identical before and after.
The census's own citations of `:307,308` were re-run to `:314,315` rather than
left stale, since the docstring sits above them; its sweep count is unchanged
at 39. No EC, no hardware, no Windows, no capture, and no claim about what the
EC does — this is a property of Python walking a `bytes` object.

## 56. `--sites` refuses an out-of-region address, so the census's row-10 caveat is a statement about the code (2026-09-25, issue #848)

The write-up is
[`pd-sites-address-range.md`](findings/pd-sites-address-range.md); this is the
summary. §53's row 10 declined to guard `site_rows()` on principle — *a guard
justified by "it cannot happen on this image" is a guard justified by an
assumption* — and recorded in the same paragraph that **the code does not clamp
`addr`**, leaving a claim about the CLI on the reader's word. The code was worse
than the sentence: `--sites 0x1FFFF` raised a bare `IndexError` from inside the
listing loop. **`check_site_addr()` now refuses an address outside
`0x0000-0xFFFF` by name**, naming the region, its runtime range, its file range
and the value given, and `main()` turns it into `ap.error` and exit 2 — the same
shape `parse_span()`'s refusal already used for an out-of-range `--bases` /
`--strides` span. The census's principle is **not** overridden: the new check
tests the caller's *argument* and holds for any dump, where the guard row 10
declined would have rested on this image's 262144 bytes, and the two guards
behave differently on a different image, which is the test that separates them.
The instruction-boundary precondition deliberately **stays** a precondition,
since no byte says where a routine's instructions begin, so `site_rows()`'s
docstring now carries the two preconditions side by side so neither reads as the
only one. The census's row-10 sentence is retracted in place beside itself, and
its table cell, its reproduction block and follow-up 1 point here; the shared
file edits are a row, a retraction, a bullet, two commands and one line. **The
realised last read is `0x3000E`, not the `0x3002C` the census's cell called the
peak** — `0x3002C` is the worst case of fifteen three-byte instructions, and
every byte from `0x30000` to `0x40000` is `0xFF`, which also makes `0x1FFF1` the
first address that raised and not the `0x1FFFB` #848's issue put it at. That same
fill means `--sites 0x1FFF0` is now **refused as well**, since it was never a
16-bit runtime address, only an unchecked one. **#843's "the only two" is
twelve** under the literal `grep -n 'lo, _ = pd_bounds()'`, and **four** under
the narrower test its issue applies — the extra pair being `site_rows` and its
caller `print_sites`, the first of which is row 10. `--callers` was measured and
**exits 0** on the same input, `--helpers 0x1FFE9` still raises and is left
raising as the census's follow-up 1, and every mode's output on the legal range
is **byte-identical** before and after — a `diff` against the pre-change file,
not an impression, which is what makes it a regression test. No live test ran,
no register was read back, no capture was opened, and no hardware, EC, Windows,
Ghidra or `registers.yaml` row was involved.

## 57. `walk()`'s stop reason is a column, and the 45 rows its budget truncates are named (2026-09-25, issue #846)

The write-up is `docs/findings/walk-window-terminators.md`; this is the
summary. #805 measured that `trace_xdata_refs.walk()`'s loop is bounded by
`max_insns` and not by `len(d)`, and drove it from every one of the image's
262144 start offsets: `max_insns (8) exhausted` fires **119530** times. That is
a property of the file. What it means for the committed tables the same
function produces the `window` column of had never been asked, and it is now
measured and committed: **45 of 1288 rows across nine tables** are truncated,
all 45 listed in `ec/annotations/walk-budget-census.csv`, and **the issue's
"four rows change their `access` cell" is thirteen** — all four the issue names
are among them at exactly the values it quotes, so it is a correct subset, and
acting on "four" would have left nine cells silently wrong. The split is
mechanical and it is two findings, not one: for **ten** of the thirteen a
larger budget's cell would be a *miscount*, because a direct store to DPL/DPH
that `walk()`'s `d[i] == MOV_DPTR` guard cannot see sits in the instructions
the budget hides and the larger window files an indexed access under the site
register — `ec-0x07d0-sites.csv` `0x2C2FA` is the case, and
`pd-index-geometry.md`'s own `0x08F8 + R7×0x5E` decode plus
`pd_index_geometry.py --self-test` already refute the budget-64 reading of it.
For **three** the budget-8 window was simply short and the larger cell is the
same site's own further accesses, which is the issue's own "a site may have two
accesses" possibility and is right for two of its four. So the budget does not
move: raising it to 64 would put a wrong `access` cell into a committed table
for 10 of the 13.

`walk_why(d, start, max_insns) -> (insns, why)` now holds the loop and returns
the reason beside the instructions, and `walk()` is its first element with its
name, docstring and signature unchanged, so all nine call sites and the eleven
modules that import around it are byte-identical — the fifteen-address `0x086x`
sweep in #805's command 1 still reproduces `xdata-086x-dispatch-sites.csv` byte
for byte, and that is the regression test. The vocabulary is five tokens and is
**not invented**: each is a name #805's own reproducing snippet already prints,
and lifting them into the tool is what makes the new column and the 119530 one
measurement in two places rather than two vocabularies for one event. Six
tables gained an opt-in `terminator` column (mirroring `--census-column`, so
the default output and #800's table are untouched), and a `--check` against one
of them now names its own cause on stderr. **No `access` cell changed in any of
the six.** Exactly one `window` cell did —
`xdata-0400-045f-sites.csv` `0x11F16`, `db 0xa2` → `mov c,acc.0` — and that is
**pre-existing drift** in `disasm8051.py`'s mnemonic table, which reproduces on
clean `origin/main` and has nothing to do with this change; it is named in the
write-up and pinned by the suite rather than quietly fixed, because a re-cut
that moves a cell is the thing a reader has to be able to see. The census
refuses rather than guesses three times over: an unrecorded budget, a
terminator outside the vocabulary, and a class A/B verdict whose evidence the
`--extend` window does not reach (`undecided`, which the committed data never
hits and `--extend 9` does). **`registers.yaml` is untouched and no `status:`
changes** — this is about how a tool renders a window, and a re-cut table with
an `access` column looks enough like a register finding to say so. **#799 and
#800 are adjacent and neither is closed here**: #799's DPTR reassignment is
*inside a callee*, which no budget reaches and which the class A verdict
therefore says nothing about, and #800 owns the `0x086x` table's `census`
column. Prose inheriting a moving cell was checked rather than assumed: of the
issue's four addresses, `0x2E8D4`, `0x28B8B`, `0x0DD4A` and `0x2BECB` are
quoted in no pre-existing page (the two files this change adds quote them
themselves, which is this work talking to itself and not a page inheriting a
cell), and `0x2C2FA` is quoted only in
`pd-index-geometry.md`, not in the three pages the issue names. No capture was
opened, no register read back, and no EC, hardware, Windows or Ghidra involved.

## 58. The prose's line citations are repointed, and a check now holds them (2026-09-25, issue #801)

The write-up is
[`prose-line-citations-held.md`](findings/prose-line-citations-held.md); this
is the summary. Issue #801 named six cells across three files that had gone
stale when `6bf9c234` (#683) regenerated the census CSVs, and it named them as
one class rather than as six one-line corrections. The class is now a checker:
**`ec/tools/check_citation_lines.py`** holds the line numbers the prose repeats
out of a generated CSV to the row for the **address or cluster
id** they name — never to a table of expected line numbers, because a rank into
a file that keeps growing is not an identity, the argument
`check_cluster_citations.py` already makes at cluster length. Three rules: the
dispatch page's site table against `xdata-0860-census-sites.csv` per site, the
`HAND_CHECKED["0x0860"]` comment against the same CSV as an unordered union
(a deliberately *different* rule, insensitive to how the lines group into
sites, so a regrouping reddens the first and not the second), and every
`xdata-registers.csv`/`xdata-clusters.csv` line pointer in the two files its
`ROW_SCOPE` names.

**Eight cells moved and not one claim did.** `xdata-086x-dispatch.md`'s three
`xdata-registers.csv:662` → `:817`, `reset-vector-dptr-targets.md`'s `:583` →
`:738` and `:101` → `:105`, and two `xdata-clusters.csv:82` → `:87` the issue
did not reach and which `grep` over that file returns alongside the two it did.
Every figure in every one of the seven sentences is still exactly right, which
is the whole difficulty: a sentence citing the wrong row of a generated CSV
raises no error and miscounts nothing. `registers.yaml`'s three cells are
corrected by a dated `*** ADDENDUM` inside the existing note rather than by an
edit, and that file's three are **held by nothing**, because every live
sentence in that note is a `*** CORRECTION` paragraph and a rule that skipped
corrections would check nothing there. Stated as a decision, not a gap.

A paragraph announcing itself a correction is **skipped**, for the reason
`check_capture_claims.py` skips a denial: a quoted supersession is a denial of
currency, and §4a-4d requires the wrong figure to stay visible beside its
correction. The skip is counted and printed, so "checked nothing" cannot read
as "found nothing"; the run prints `26 citation(s) resolve to the row they
name, 8 skipped as superseded`, non-zero on both counts. The vocabulary is not
free, and this branch is where that showed: the correction written for
`reset-vector-dptr-targets.md` was first a table in the file's own voice, and
being live prose it was *checked* — by the new tool, against its own author's
superseded figures. It was rewritten as the blockquote §4a-4d's siblings use,
not loosened out of the checker. No `status:` moved (`XDATA_0860` is still
`present-untested`), no count moved, no CSV or Ghidra export was regenerated,
`check_site_census.py`'s output is byte-identical, and no EC, hardware or
Windows machine is involved anywhere: every input is a committed file.

## 59. The refusal contract's measured state, corrected against the tree that inherited it (2026-09-25, issue #816)

> **Numbering note, added at the merge.** This section was written as §57, and
> #846 (`964279dc`) took §57 on `main` while it was open, so it is renumbered
> to the next free number rather than left to collide. §57 is now #846's
> `walk()` summary above; the §29 addendum, the
> `xdata-cluster-names-guard-off-recipe.md` block, the register-map correction
> and the write-up's own table all point at **§59** for this one. §58 then went
> to #801 (`72ff69d1`, the prose-line-citation checker) on `main` in the same
> window, so this section is renumbered a second time and sits below it. A
> section number is a property of the merge in the same way the runner's totals
> are — see `runner-red-suite-set.md` — which is why the collision is recorded
> here rather than left for the next reader to find.
>
> **One figure below moved in the same merge, and this is where it is corrected.**
> The `28` for `test_xdata_cluster_names.py` was exact on `main`; #850 added
> `TheExportOwnershipClusters`'s two cases there, so the merged tree measures
> **30**. The runner's totals line moves on both merges in this tree rather than
> one: **1020** over thirty-three suites, not the `974` over thirty-two the §29
> addendum and this section's siblings were re-derived at, because #849's
> `ec/tools/test_check_doc_figure_pins.py` at 44 cases is in the tree as well.
> **#851 then added a suite in the same window, so the tree this finally lands in
> reads 1035 over thirty-four**, and `30` is the one figure of the three that did
> not move.
> `45` and `48` did not move, the red set is still the same one suite, and the
> failing line is still #822's. Left visible per §4a-4d because both were true of
> the tree they were measured on.

The write-up is
[`xdata-no-eq-guard-measured-state-correction.md`](findings/xdata-no-eq-guard-measured-state-correction.md);
this is the summary. §50 landed the flag and then, because the two sentences it
had relied on sat in long shared prose files, **recorded them as superseded in
its write-up rather than editing them** — offering that a reviewer could overrule
that at the cost of one sentence each. This is that reviewer, and the cost came
out at six, for a reason worth stating: the refusal contract's measured-state
section is **one claim, not several**. Its heading counts the red suites, its
next paragraph names the two behind the flag, and three paragraphs follow each
naming one and giving its cause; the "only working route" sentence appears in
the contract *and* in §29, which summarises it; and the register map's "one
suite of the two red" depends on a count its own neighbouring sentence had
already halved. Correcting the six suite-sentences and leaving the rest would
have left a page that contradicted itself three paragraphs down. Nothing was
rewritten or deleted — each correction is a dated block beside the sentence it
belongs to, quoting it rather than pinning a line number, because these
corrections add lines to the files they correct and a `:NNN` aimed at one of
them is wrong on arrival. **The three failures these sentences are about are
resolved, and two of the three suites are green** —
`test_xdata_cluster_names.py` and `test_check_site_census.py`, at 28 and 45
tests; the third, `test_check_cluster_citations.py`, is still red at 48 tests,
so the red set the contract's heading counted is down to the third of those
three rather than to none — and it is red on a *different* line for a
*different* reason. `bash tools/run-tests.sh` still exits 1 on this tree, on
`ec/tools/test_check_cluster_citations.py`, and the failing line is
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` — **#822's**
write-up, reproduced on a clean `origin/main` and recorded in §52's merged-tree
note above, which is why the figures here were re-derived rather than carried
over from the commit this work started at. One figure from the issue did not
move and one did — `45` was already right for `test_check_site_census.py` and
`46 → 48` is the real change, which is the split a reader pinning a single "it
is at N tests" would have got wrong.
**The open question came back answered, and not the way it was framed**: §26 is
not flagged *not* because the tree stopped being checked for the disagreement
but because §26 stopped making it. `main-ec-086`'s committed row really is
`0x07FD 0x07FE 0x07FF`, so that claim is true and #564 is owed nothing. The
address `0x0800` now falls in a following sentence that names no cluster id at
all, so its unit is dropped before the address is read. Measured
rather than
reasoned, and the sharper form is that **any** unit naming an address, a cluster
id and a membership word reads as a claim — so quoting §26's sentence is enough
to turn that suite red, which is how this write-up's own first draft
failed. The rules did not loosen, the prose changed shape, and the mechanism is
recorded with a citation rather than asserted. Also left standing, as
deliberately: the refusal contract's "the third time this recipe has been
re-pointed at a line number, which is itself the argument for the flag" — it is
the reasoning #753 acted on, and the four pins in that same paragraph are now
352 to 625 lines stale — four different offsets, `:1220`→`:1572`, `:1243`→`:1595`,
`:1604`→`:2168`, `:2292`→`:2917` — for the very reason it names. No tool, CSV,
`registers.yaml`
row or gate was edited, no image was opened, no register was read back, and no
new test was added: a check over prose nobody asserts on would duplicate a rule
the tree made on purpose.

## 60. The census checklist's held/unheld split is measured, and a constant that was a promise is now a check (2026-09-25, issue #849)

> **Numbering note, added at the merge.** This section was written as §59, and
> #816 (`2665a6a8`) took §59 on `main` while it was open, so it is renumbered
> to the next free number rather than left to collide. §59 is now #816's
> measured-state correction above, and this was the last section in the file as
> #849 landed it. It is not, as this note first said, the last one now: #851's
> summary renumbered from the same §59 in the same window, collided here a
> second time, and gave way to land as §61 below; #852's moved-rank measurement,
> renumbered from §60 for #849 taking it, followed it to the next free number
> and is **§62**.
> Nothing this branch wrote pointed at its own section number — the write-up,
> the checklist's correction block and both READMEs all name §2b, §3, §4a-4d
> and the issue numbers instead — so there was no reference to repoint.
> **#850's summary collided a third time, in this same merge**: it was written as
> §59, renumbered to the same next free number #851 took, and is renumbered once
> more, to §62 below, so §61 is #851's and §62 #850's. Its numbering note says
> so for itself. **Amended at the third merge: §62 is not #850's.** #852's
> measurement took that number in the same window, so #850's is renumbered once
> more to **§66**, the end of the file, and the sentence above is left as it was
> written per §4a-4d. §61 is #851's, §62 #852's, §63 #886's, §64 #713's, §65
> #887's and §66 #850's. A
> section number is a property of the merge in the same way the
> runner's totals are (see `runner-red-suite-set.md`), which is why the collision
> is recorded here rather than left for the next reader to find.
>
> **Amended at the fifth merge: §66 is not #850's either, and the owner list above
> is re-derived rather than moved.** #713 took §64 in the window before this one
> and #887's line-pin census (`bb4c1d27`) took §65 behind it, so #850's is at
> **§66** and the file ends there. Both amendments left their sentence as it was
> written per §4a-4d; only the owner list is re-derived, because it is a list of
> owners rather than a pointer at one of them, and a list that no longer lists
> every owner is wrong in a way a superseded record is not. #850's own numbering
> note carries the arithmetic from the other side.

The write-up is [`doc-figure-pin-audit.md`](findings/doc-figure-pin-audit.md); this
is the summary. §2b of the re-derivation checklist said **"Eight, unpinned"**,
and it was wrong in both directions: a re-deriver was being sent to redo the
seven figures the cheap gate already turns red on (five of §6b's console block,
and from §6a's table `43` and `4,966`, which `--check` does hold), and the
eleven that really were unheld were left looking like company.
**`9320` was the sharpest of those** — it
was `OWNERSHIP["main_refs"]`, a value in a constant thirty-six lines under that
constant's own *"the --self-test ownership block asserts all four rather than
leaving the promise to a reader"*, and **read by no check at all**. A value in a
constant is a pin-shaped thing; it is not one. One `check()` now asserts the
main-EC half of the export-ownership census against
`OWNERSHIP["main_distinct"]`/`["main_refs"]`, and `--self-test` prints it
(`ok  and its main-EC half is 1218 distinct / 9320 references … (got 1218/9320)`)
**measured rather than copied** — if it came back red that is a finding, not a
constant to edit to match. Since #823 a pin there is a CI failure, which is what
makes §2b's split a distinction with consequences.

The split is now a command's output.
`ec/tools/check_doc_figure_pins.py` resolves every figure in a named section's
tables to one of four verdicts with the `file:line` that decided it:
`held-by-assertion` (a module-level constant **whose key is read outside its own
span**), `held-by-check-literal`, `unheld`, or `not read by this method`, and
exits non-zero when the page's own marking disagrees. **Eighteen figures, eight
held, ten unheld**; the old "eight" counted table *rows*, and the issue's own
"five of nine" is not a count of anything on the page, so the measured count is
recorded rather than the issue's — the calibration rule applied to the issue as
well as to the page. Every `unheld` is **"not found by this method", never
"absent"**, and the four limits that have to be read with the verdicts are in
the docstring; the load-bearing one is that this tool's own suite is excluded
from the literal search, or `390` and `50` would measure held the moment a case
named them.

The wrong classification stays visible in §2b's correction block, quoted
verbatim per §4a-4d, beside the new one. Three things this opens: **pinning
`390` and `50`** is a new measurement rather than a correction of a false claim
and is the natural next issue (only their sum, the pinned `440`, is held — a
re-deriver can cross-check the pair by subtraction and cannot check either half
alone); the eight §6a subset sums are unheld for a different reason and are not
fixable the same way, since the guard-off census they come from is written to
`/tmp` and committed nowhere; and **wiring the tool into a gate is a human's
change** (`.github/` is out of an agent branch's reach — the plan stage's token
has no `workflow` scope), so it runs by hand where
`check_cluster_citations.py` stands today, and a case reads the gate script and
fails if the name appears there without this being updated with it. A checker
nobody runs is the shape of defect #819 was. `xdata-06c2-06db-timers.md` is not
touched: its `BUCKET_TOTALS` citation is named in §3 and **#838 owns stale pins
in this file family**. No live test ran, no register was read back, no image was
opened, and no hardware, EC, Windows, Ghidra or `registers.yaml` row was
involved.

*(Corrected at the merge, 2026-09-25, issue #850. **Two of the three things
above are closed and the count above has moved, and the wrong versions stay
visible per §4a-4d.** `390` and `50` are held, by a new
`TheExportOwnershipClusters` in `test_xdata_cluster_names.py`, so they are no
longer the natural next issue; the eight §6a subset sums are held too, by named
assertions in the same file — **and the second reason given for them not being
fixable was a reason about *this* checker, not about the census.** It read
`unheld` because the guard-off run is written to `/tmp` and committed nowhere,
so no committed cell existed for `--check` to compare; a case that builds the
same census in a temp dir and asserts the sums does not need a committed cell,
which is what the recipe's own comment about the refusal contract has been
saying. The measurable consequence is the count: §2b now reads **eighteen
figures, eighteen held, none unheld**, and `390` and `50` measuring `held` is
the literal-search limit above turning out to be real rather than theoretical —
a case naming them was all it took. What the all-held column does *not* cover
is in §66 and in §2b itself: the `157`/`858` pair, which is held for the
*default* census rather than for the run §6b prints it from, and the guard-off
`pd` cluster count `51`, which §6a does not print at all. The third thing above
stands: wiring the tool into a gate is still a human's change.)*

## 61. The carry line names the census it is a claim about (2026-09-25, issue #851)

> **Numbering note, added at the merge.** This summary was written as §59 and
> has been renumbered twice on the way. #816's refusal-contract measured-state
> summary (`2665a6a8`) took §59 on `main` while this was open, so this one moved
> to §60; #849's doc-figure-pin-audit summary (`a00fe940`) then took §60 on
> `main` in the same window, having renumbered from the same §59 for the same
> reason, so this one moves again to the next free number and sits below it. §59
> is now #816's, §60 #849's, and this is #851's at §61. The
> collision is recorded here rather than left for the next reader. Nothing else
> cites a number for this section: the write-up names the census and
> `carry_advice`, not a section, and the `§59` pointers in
> `xdata-cluster-names-guard-off-recipe.md`,
> `xdata-no-eq-guard-measured-state-correction.md` and `xdata-register-map.md`
> all belong to #816's summary above, so only the heading moves.
>
> **Amended at the second merge.** This note first said this was the last
> section in the file, and on the merged tree it is not: #852's moved-rank
> measurement (`xdata-moved-ranks-fall.md`) was written as §60, gave way to
> #849 taking §60, and then gave way again to this one taking §61, so it sits at
> **§62** below. It is left visible here rather than corrected out, because the
> two §61s are the same collision twice and the sequence is the record.
>
> **Amended again, for #850.** #850's summary collided with #852's over §62 in
> this same merge and, being the branch's own, is the one that gives way: it is
> at **§66**, past #886's §63, #713's §64 and #887's §65, so the "last section
> in the file" this note first claimed is now four sections away rather than
> none. §60's amendment above and §66's own numbering note record the collision
> and the correction from their two sides.

`ec/annotations/xdata-cluster-names.csv` is anchored to the **committed** census
— the two CSVs as committed, which is the run `--check` reproduces — and four
places said so without naming it as a mode or flag combination, so the one
sentence a reader needed in order to act was the sentence that carried no such
statement. The rule now on the line is that **a carry is a statement about the
run that printed it, and only a run whose cluster keys are the committed ones can
turn a carry into a re-key request**: `census_shape(args)` names the flags that
move the ids off the anchor (`--threshold`, `--no-eq-guard`,
`--export-ownership`; deliberately not `--no-writer-axis`, which clusters as a
default run does) and `carry_advice` keeps the old clause verbatim for the
committed census while any other shape names its flag, names the file, and says
it is not a re-key request. The `names:` tally and the `tie` line are
mode-independent and stayed as they were, and the committed shape's output is
byte-identical. The issue's second half is recorded as a decision and not built:
**no**, a membership that moved cannot keep resolving, because `cluster_key` is a
content hash of the membership — so `--self-test`'s stale-key check already
fires — and the open part is the `note` column, which nothing reads and which
would need either prose-scraping or a new column on the one file a human edits by
hand. The write-up is
[`xdata-names-file-census-anchor.md`](findings/xdata-names-file-census-anchor.md);
this is the summary, and it restates no measurement.

## 62. The guard-off moved-rank fall is measured, and §3's guess about it is refuted (2026-09-25, issue #852)

> **Numbering note, added at the merge.** This section was written as §60, and
> #849 (`a00fe940`) took §60 on `main` in the same window, so it is renumbered
> to the next free number rather than left to collide. §60 is now #849's
> held/unheld measurement above. It then gave way a second time, to #851's
> summary (`a02de81b`) taking §61, so it is **§62** and is the last section in
> the file. *(Its last clause is left as it was written per §4a-4d: §63
> (`#886`) landed behind it before this note was, #713's §64 behind that, #887's
> §65 behind that, #850's §66 behind that, and #885's §69 behind that, so
> §62 is not the last section in the file on any tree this note has been read
> on. The number itself is right.)* Nothing this branch wrote pointed at its own
> section number — the
> write-up, the checklist's correction block and the
> `xdata-4-4-identity-rederivation.md` note all name the issue, the write-up and
> the sections they measure instead — so there was no reference to repoint; the
> two notes that do name it, §60's and §61's above, were written by the merges
> that took the numbers and name §62. A section number is a property of the
> merge in the same way the runner's totals are (see
> `runner-red-suite-set.md`), which is why the collision is recorded here rather
> than left for the next reader to find.

The write-up is
[`xdata-moved-ranks-fall.md`](findings/xdata-moved-ranks-fall.md);
this is the summary. §54's checklist named the `> 300` floor, measured it at
315, recorded that the count had fallen once (**366 → 315**) and declined to say
why — "a re-derivation that lands addresses in already-large clusters would move
fewer membership sets, which is the obvious shape of it, but that is a guess and
not a measurement". This is the measurement, and **the guess is wrong on both
halves.**

**The 366 is re-derived, not carried.** The 430-row census is `e169a0e4`'s, whose
tool already carries `--no-eq-guard` (#528 is an ancestor), so the old pair needs
no copy-and-patch route; `git worktree add --detach` plus two census runs, all
writing to `/tmp`, reproduce **366 moved / 64 intact / 439 rows** exactly, and
the present tree gives **315 / 124 / 445**. No committed rank is missing from
either guard-off census, so both pairs' arithmetic closes — a fall, not two
different measurements.

**The flipped set, keyed on `cluster_key` and not on the rank**, is **71
moved-then-intact, 266 moved in both, 23 intact-then-moved, 40 intact in both**,
plus the one-sided key sets split by moved/intact as 29 and 26, which closes the
difference over four terms: `(71 − 23) + (29 − 26) = 51 = 366 − 315`. The 94
flipped clusters' **committed membership did not grow at all** — a key is a hash
of the membership, so all 400 keys the two committed censuses share have
byte-identical membership and the `grew` column is `0` on every row. Nor are they
"the large clusters": their size deciles are `1 1 1 1 2 2 4 4 5 6` against the
census's `1 1 1 1 1 1 2 2 4 5`, 5 of the 23 clusters of 8 addresses or more
flipped, and the largest, at 152 addresses, is not among them.

**What moved is the guard's membership delta, and the guard itself did not
change.** §6a's per-address triple is *identical* in both generations — 210
addresses whose `write` differs, 0 whose `refs` does, 833 references leaving
`write` — while the cluster-level total fell **1,623 → 1,030** address-slots. The
mean delta over the 71 clusters that went quiet is **7.66 → 0.00**; over the 23
that started, **0.00 → 3.65**. Across both pairs a moved rank is overwhelmingly a
**substitution** — 351 of 366 and 307 of 315 hold a guard-off row of the same
size, and 364 and 311 share *no address* with it — so `moved` counts a ranking
disagreement, not a magnitude of perturbation. **How far that is established**:
the flipped set is fully accounted for, 94 of 94 keys named and the arithmetic
closing; which re-partition change closed the delta on those 71 is *not*
derived, and is left as a follow-up rather than asserted.

**The hand-named clusters are not the explanation.** Exactly one of the nine
names moves in either pair — `mode-oem-init`, in **both**, and so not among the
94; `level-block-086x`, one of the two names a generation behind their ids, is
intact in both. Of §2a's 43 swept addresses, the cluster holding all of them is
`k733222e83898` (`counter-sweep`), intact in both pairs and not flipped; the only
swept address whose cluster moves is `0x080D`, in `ke928434f6676`, and that moved
in both pairs too. **Zero of the three holding clusters flipped.**

**`> 300` stays where it is**, decided from the measurement rather than from the
15 ranks of headroom: the re-derivation is one named commit whose 155 added
addresses are recorded, so `moved` is a property of a classifier generation
rather than a drift — and, stated as the limit of that, one observed
re-derivation is one data point, so this measurement does **not** claim `moved`
decays as the census grows. A future re-derivation moves it again and the
direction is not predicted. The floor, the class docstring's three figures and
every other assertion are unchanged; the deliverable is one new read-only tool
(`ec/tools/xdata_moved_ranks.py`, with `--self-test` over synthetic fixtures
rather than a new suite row) and five one-line pointers. No CSV, YAML, threshold
or gate was edited, no image was opened, no register was read back, and nothing
is opened in another repository.

**§62's open question has since been answered, and both mechanisms it named are
refuted** (issue #884). The write-up is
[`xdata-flip-cause-derivation.md`](findings/xdata-flip-cause-derivation.md). A
new `cause` mode on the same tool follows each moved rank's substitution into the
other generation's guard-off census, per cell, **beside the two cells that did
not flip** — which is what makes the counts decidable. **Rank displacement**
accounts for at most **10 of the 71** substitutions landing within two ranks —
**10 of the 60** that reappear, against **79 in 408** for the census as a whole
— so the flipped cell reappears and reorders at the population's rate. **The 155
added addresses** reach **0 of the 71's 273 substitution addresses** and **0 of
the 266 control's 450**, and **one key of the 23** (`ka01f369d385f`, whose
substitute is `0x036E 0x036F`) —
so across all 94 flipped keys the added set reaches exactly one. A third thing
is located and *not* claimed as a cause: at the same ranks the 71's
substitutions sat on the `0x03xx`–`0x05xx` page at **37.4% against 19.1%**, but
that gap is five size-9+ rows plus a row-size distribution the two cells do not
share, and it is written up with both against it. Two side results: the `pd`
side of both pairs is **byte-identical**, which is why none of the 94 is a `pd`
cluster; and **151 of the 155** added addresses are on the working page, not all
of them as `xdata-cluster-names.csv`'s note says — recorded beside the note
rather than edited into it. No threshold, CSV, YAML or gate moves, and
`xdata_moved_ranks.py`'s `pair` and `across` output is unchanged. The
`across --swept` summary's own second-holder count is derived differently by §63
below, which leaves its printed figure on the committed pair the same.

**Correction, 2026-09-26 (issue #889): the deciles above are read over a set
of 94 and 439 rows, and `deciles()` now says so — a floor of ten, below which
it returns the set itself instead of ten cells.** The figures are unchanged and
stand; what was wrong was the tool's own docstring, which claimed the
below-floor case was already handled when the body clamped the other way and
drew a set of two rows out across ten cells. Both of this section's reads are
far above the floor, so nothing quoted in it moves — §4's are the two the
section is *about*, and neither is a below-floor read. What the fix changes is
that the form can no longer be produced: §4 reads one of these strings against
the other cell for cell, and under the clamp a handful of keys was rendered on
a line of its own, indistinguishable from a real read, with only the input's
size to tell them apart. The tool's own A/B fixture did exactly that, printing
`2 2 2 2 2 2 2 2 2 2` for a flipped set of two clusters on every green
`--self-test` run. Five cases now pin the contract, three of which fail against
the code as it was, and one of them goes through `across_report` so the
*report* is held to it and not only the helper. The write-up is
[`xdata-decile-small-set-contract.md`](findings/xdata-decile-small-set-contract.md).
No figure, threshold, CSV or gate changes, and this section's `pair` and
`across` output is unchanged on the committed pair.

**The one-data-point limit above is confirmed, and the third point is not there
— see §69.** It is not there because neither 427-row commit can be paired: at
`e6c88864` the committed file is stale, and at `1fcd5f1e`, the only other one,
the census predates `cluster_key` and the pair tool cannot read it.

## 63. `--swept`'s second-holder count was taken over one generation, and the rows above it over both (2026-09-26, issue #886)

The write-up is
[`xdata-moved-ranks-second-count.md`](findings/xdata-moved-ranks-second-count.md);
this is the summary. A defect in the tool §62 added, in the summary line that
is supposed to describe the rows printed immediately above it.

**The row loop built each address's rows from the union of both generations'
holder indexes; the count read one of them.** `index_b.get(addr) or
index_a.get(addr)` falls through to A only when B's list is empty or missing,
so the second-holder count could only ever be B's — an address generation A
holds twice and B holds once printed **two rows** and counted as one. The other
numbers on the line were already union-based and right: `keys` is accumulated
from the rows, so `main-ec` holders were counted across both generations while
`second` was not. The disagreement needs `|B| <= 1 < |A ∪ B|`, and the reverse
asymmetry is invisible to it — which is why the fixture's shape is forced rather
than chosen.

**The fix derives the count from the rows instead of re-reading the indexes.**
The loop appends each address's `rows` to a list as it makes them and the
summary counts the entries with more than one row, so there is one definition of
"the rows for this address" and the line cannot drift from it again. It is a
list rather than a `{addr: rows}` map because the loop is over `sorted(addrs)`,
so a repeated address is counted once per visit rather than collapsed into one —
`--swept 0x0E 0x0E` over the shape the committed pair has is 4 rows and `2`
before and after, unchanged. The two sibling `b.get(k) or a[k]` reads at the
`pd_keys` and `complete` figures were examined and **deliberately left**: a key
is a content hash over the program and the membership, so a key in both censuses
carries the same membership either way and there is no disagreement to fix.

**A dedicated census pair in the tool's own `--self-test` is the fixture, and it
goes red.** Three rows — generation A holding one address under a `main-ec` and
a `pd` key, generation B under the `main-ec` key alone — reached through a
direct `flip_table()` call, plus one new check that counts the addresses which
printed more than one row, reads the figure back out of the tool's summary line
and requires the two equal, with the concrete `2` rows / `1` second holder
asserted alongside so a vacuous loosening still fails. With the old line
restored it prints `FAIL`; the self-test is 15 checks where it was 14, and the
other 14 print verbatim. The A/B pair above it **cannot** be the fixture — its
`0x0E` is held by two clusters in *both* generations, so `or` picks either
without consequence, and no existing check reads the `second` figure at all — so
a dedicated pair is why no existing line of the self-test changed and nothing had
to be corrected in §62's transcript. The issue's own alternative, mutating that
pair's B generation, is real but is a structural change rather than a one-cell
edit: `b_committed` is written from the same `committed_rows` list generation A
is, so the row has to be un-shared before it can move. Both routes were
measured; the dedicated one is taken.

> **Correction (2026-09-26, issue #884 merged below), leaving the paragraph above
> as it was written.** The count there — "15 checks where it was 14" — is what
> this section's own change made of the self-test, and it is still what it made
> of it: the count moved by one here, on `main`, on the tree #884 forked from.
> On the merged tree `python3 ec/tools/xdata_moved_ranks.py --self-test` prints
> **39 checks**: #884's `cause` mode added ten of its own to the same
> fixture block and they all print `ok`, #891 landed beside it with nine
> more after those, and #889 landed beside both with five more — those five
> print at 10–14, between the two halves of the first fifteen, so they are
> not in the tail — so the **25** this note first recorded is the 15 above plus
> those ten, and `25 + 9 + 5 = 39`. The 14 this section left verbatim are
> the 14 that still print verbatim, in the same order, ahead of both blocks. A
> count like
> this is a property of the merge in the same way a section number is — see the
> numbering note at §59 — so it is recorded here rather than left for the next
> reader to reconcile against a run. *(The 34 this note first carried is the
> same tool without #889's five beside it, and is left visible here per §4a-4d
> rather than edited out; the figure that stands is the one re-run on the tree
> this lands on.)* **#888 landed beside #891, and the run on that tree prints
> **45**, not the 39 above: its six `cluster_key`-collision cases are the last
> six the tool prints (`25 + 9 + 5 + 6 = 45`), and
> [`findings/xdata-moved-ranks-fall.md`](findings/xdata-moved-ranks-fall.md) §9
> carries the merged transcript. The 39 is left as it was written because it is
> true of the tree #891 measured.** Nothing else in this section moves: the
> fixture, the `FAIL` on the old line, the dedicated-pair argument and the
> measured `48 rows` / `5 second holder` figure are all unchanged by either
> merge; #884 adds a mode and #891 adds columns and a `--cell`, and **neither
> touches `swept_report()`**, which is byte-identical across the base commit,
> `main` and the merged tree.

**The committed figure does not move, and that is measured rather than assumed.**
§7's recipe re-derived from `e169a0e4` — the worktree, two guard-off census
runs into `/tmp`, then the 43-address `across --swept` — was run with the old
line and again with the new one: **48 rows for 43 addresses and `5
address(es) have a second holder` both times**, `diff` over the two 86-line
reports empty. On this pair the two `pd` holders are present in both
generations, so B's count and the union's are the same five — a latent
disagreement, not an observed wrong figure, and now a figure that cannot go
wrong. No CSV, YAML, threshold, `status:` or gate was edited, no `test_*.py` is
added so the runner's totals are unmoved by this section (34 suites and 1033
tests on the tree it merged into, 35 and 1076 on the tree it lands on, the
additions being #887's `ec/tools/test_census_test_line_pins.py` at 41 and
#850's two cases in `ec/tools/test_xdata_cluster_names.py` — see
`tools/README.md`'s ninth merged-tree note), the `> 300` floor
stays where §62's recipe put it, no image was opened, no register was read
back, and nothing is opened in another repository.

> **Correction, 2026-09-26, issue #885: the totals in that sentence are
> superseded, and it is left as written.** "34 suites and 1033 tests" was
> correct for the tree it was measured on and went stale on a later merge,
> because **#887's `ec/tools/test_census_test_line_pins.py` landed in the same
> merge window** at 41 tests. #885 corrected it to `34 + 1 = 35` suites and
> `1033 + 41 = 1074` tests; **that pair does not reproduce either, and the
> runner reads `35 suite(s) run, 1076 tests` on this tree, on a clean
> `origin/main` and on the fork point `d62730e1` alike** — so nothing in this
> merge, and nothing on `main` since the fork, moves the runner, and `1074` is
> a figure that reproduces on none of the three. Both superseded pairs stay
> visible here per §4a-4d rather
> than edited out; the corrected figure, with the same arithmetic spelled out,
> is in [`xdata-moved-ranks-427-pair.md`](findings/xdata-moved-ranks-427-pair.md)
> §8, beside the correction to
> [`xdata-moved-ranks-fall.md`](findings/xdata-moved-ranks-fall.md) §9, which is
> where the 34/1033 was first measured. A total is a property of the merge, the
> same reason a section number is.

## 64. `refs` and the five buckets are split per program, and `refs` itself does not move (2026-09-26, issue #713)

> **Numbering note, added at the merge.** This section was written as §63, and
> #886's `--swept` second-holder measurement (`32218840`) took §63 on `main` in
> the same window, so it is renumbered to the next free number rather than left
> to collide. §63 is now #886's summary above, and this is **§64** and is the
> last section in the file. *(It is not the last any more: §69, #885's 427-row
> pair, landed on top of it in the same window and renumbered itself out of the
> way below. The sentence is left as written and the correction put beside it
> rather than into it, per §4a-4d — the same treatment §62's note got, and §62's
> note is what this section's own is modelled on.)* Nothing this branch wrote
> pointed at its own section number — the write-up, the `ec/README.md` bullet
> and the three correction blocks all name the issue, the CSV, §2 of the map
> and §39 instead — so there was no reference to repoint. A section number is
> a property of the merge in
> the same way the runner's totals are (see `runner-red-suite-set.md`), which is
> why the collision is recorded here rather than left for the next reader to
> find.
>
> *(Its last clause is left as it was written per §4a-4d: **§64 is not the last
> section in the file on any tree this note has been read on.** #850's summary
> collided with this number in the same merge and, being the branch's own, is the
> one that gives way — first to **§65** and then once more, to **§66** below, and
> the file ends there. The two collisions are not the same one: #713 took §64 in
> the window before this note was, and #887's line-pin census (`bb4c1d27`) took
> §65 behind it, so the number #850 gives way to this time is #887's rather than
> this branch's own. The number itself is right, and so is the "no reference to
> repoint" clause: #713 still points at nothing of its own. §66's numbering note
> records both collisions and the correction from that side.)*

The write-up is
[`xdata-per-program-counts.md`](findings/xdata-per-program-counts.md);
this is the summary. §39 split what a `program=both` row *spells* and left
every *count* on it a sum, so `0x04A3` read 4 `read` / 3 `write` / 0 / 0 / 1 with
nothing saying the main-EC seven are 4 read + 3 write and the pd one is 1
address-taken — a reader looking for a writer saw three bank1 writes and a
single pd `address-taken` in one cell.

**`ec/annotations/xdata-registers.csv` now carries twelve more columns, 22–33**,
appended after `spellings_by_program`: `refs_<program>` and each of the five
buckets once per program, `_pd` and not `_pd_image` because this CSV's own
vocabulary is already `pd` (`registers.yaml` spells it the other way and the
divergence is recorded). Written on **every** row, not only the 49 `both` ones —
a column blank on 1,277 of 1,326 rows is a shape no `DictReader` consumer can
rely on, and it is what makes `refs == refs_main_ec + refs_pd` checkable
corpus-wide. **0 violations on all 1,326 rows.**

**`refs` on a `both` row is still the sum, and every published figure stands.**
Σ `refs_main_ec` is 14,838 and Σ `refs_pd` is 858, which is 15,696 — the per-
program totals the tool already pinned are each the single-program rows plus one
half of the `both` rows, and that identity is the cross-check that says the
columns split *this* census rather than re-counting it. The 1,202 the `both`
rows carry is 947 main-EC + 255 pd, and their buckets 546/165/212/16/8 against
95/74/2/56/28. `xdata-clusters.csv` regenerates **byte-identical**, which is the
strongest single statement that no reference was added, de-duplicated or
re-bucketed and the ranking is untouched.

**Four `--self-test` assertions** hold it, three reading the committed file as
#711's do and one deliberately against a fresh generation (a column wrong in
both the tool and the CSV is internally consistent and the others would pass
it): the per-row partition plus where the columns sit, the 15,912 cells against
`groups`, the aggregate reconciliation, and the four `pair-literal` rows to the
bucket. **Two of those four were already published per program** in
`xdata-spelled-as-union.md` and §2 of the map, so that assertion is checked
against prose nobody re-derived for this change. Every key of the new pin block
is read, per #849's rule. Both `--check` and `--self-test` are already gated
(`agent-gates.sh:261-262`, since #815), so none of this can be removed without
CI going red.

**Four places said no per-program count exists; all four were incomplete, not
wrong**, and they were not corrected the same way. The sibling page's "The union
that remains" got a dated correction *beside* the original rather than a silent
edit; the other three were in-place edits, which is what the issue's per-file
spec asked for and what actually landed — the `xdata-registers.csv` bullet in
`ec/README.md` and the `build()` comment that said "nothing here splits those"
both rewritten, and §2's "which `spellings_by_program` does not split" given a
naming clause pointing at columns 22–33. Nothing was retracted and no figure
moved: the numbers the sibling page publishes for `0x04A3` and `0x0834` are the
same ones these columns publish, and the two agree. §39's closing sentence is
left exactly as written, because the **re-keying half of that follow-up is
still open** — `xdata-register-map.md` §2's `both` rows per program, which
would take that table's `distinct` from 1,326 to 1,375 and invalidate its three
superseded-table blocks. That is the next issue, deliberately not this one: two
large edits to one long shared file is the merge conflict `CLAUDE.md`'s "new work
goes in new files" rule exists to prevent. Also not done, and named in the
write-up: the function-count columns (`readers`, `writers`, `co_reading`, …) and
`registers.yaml`'s 160 `static_refs_main_ec` / `static_refs_pd_image` entries,
which are a different method over different bytes. Two pre-existing stales were
found and left alone on purpose — `xdata-census-totals.md`'s `8341` bucket line
and `xdata-export-ownership-page-census.md`'s `md5sum` — neither caused by this
append. The positional readers `$6`, `$7`-`$11` and `$21` are re-run verbatim in
the write-up and print 15,696, `read 8826 write 3587 read+write 2482
passed-to-call 534 address-taken 267` and 214. No register `status:` moved, no
`registers.yaml` figure was refreshed, no image or Ghidra project was opened, no
gate was edited, no register was read back, and nothing is opened in another
repository.

## 65. Every `test_*.py:NNN` the markdown carries is censused, and the checker is declined on the measurement (2026-09-26, issue #887)

The write-up is
[`test-line-pin-census.md`](findings/test-line-pin-census.md);
this is the summary. §58's `check_citation_lines.py` holds pointers into the
generated CSVs and `check_cluster_citations.py` holds cluster claims; neither
reaches a line number written into a **test file**, which is what
`tools/README.md`'s eighth-thing paragraph said out loud: *"nothing checks a
citation into a test file, which is why the two pre-existing ones are still
wrong."* This is the census of that class, and it is a census rather than a check
on purpose — the tool renders no verdict on whether a line still carries its
claim, and exits 0 on a tree where every pin is wrong.

**Seventy-three occurrences, 46 distinct spellings and 42 distinct resolved
targets, across 26 markdown files**, all three printed on every run because a
census whose own headcount cannot be reconciled is the failure it is measuring.
Both of the issue's claims are confirmed exactly as filed, and its own
citing-line reference is not: the first pin is at `:403` and not at the
`:154-157` the issue places it. **Five of the six that do not carry the claim
they are cited for are new** — a comment quoted from `:2687` and cited at
`:2232-2233`, a `Path(__file__).parent` cited at the blank line above it, two
`:54` pins naming a `GUARD` constant #753 removed from the file, and a
"third-generation figure" that is the second — and each is named in the write-up
with where the line is. **No pin is spelled anywhere in this section**: prose
that writes a `test_*.py:NNN` is itself an occurrence of the class, so naming
the `> 300` floor's assertion would move the figure this sentence is reporting
— which is the same reason the census excludes its own write-up from its own
population. *(Measurements of that sentence, in the order they were taken, per
§4a-4d: **fifty in 23** as the issue was filed, **fifty-two in 24** after §68's
write-up
([`xdata-moved-ranks-key-collision.md`](findings/xdata-moved-ranks-key-collision.md))
put one new file and two `test_xdata_cluster_names.py` pins into the census,
**seventy-one in 25** on the #888 × #890 tree and the same **seventy-one in 25**
on the tree §69 merged into, and the **seventy-three in 26** above. The first
four are the record of the trees they were measured on, not figures in dispute;
the sentence above is re-derived from the run it now sits in. **Neither of §69's
two is among the six above, and on this tree neither carries either** — both
resolve, by path, to `decreased, {},` where §69's own tree had the
`assertGreater(len(moved), 300)` they are cited for. That is the same defect as
#850's four, arrived at by a different route, and
[`test-line-pin-census.md`](findings/test-line-pin-census.md)'s finding 8
records it.)*

*(Re-measured at the #850 merge, 2026-09-26, and **every figure above moved
because #850 moved the tree, not because the merge did**: the run on #850's own
tree and the run on the tree both issues are in are the same run, so #850's
nineteen new citations and its 239 lines into
`ec/tools/test_xdata_cluster_names.py` are the whole of it. It reads
**69 occurrences, 44 spellings and 40 resolved targets, across 24 markdown
files**, with 53 resolving and 16 declined against 44 and 6. **Nine pins do not
carry against six, and the four that are new are one defect**: #850 moved the
`> 300` floor from `:392` to `:563` and repointed one citation of five, so four
sentences in `xdata-flip-cause-derivation.md` and `xdata-moved-ranks-fall.md`
still name where it was. **The census is what found them, and that is the part
worth keeping**: they were wrong the moment #850 landed, on #850's own tree, and
nothing in this pipeline runs the census. The wrong version stays above per
§4a-4d.)*

*(And again at the #888 merge, one line later: **71 occurrences, 45 spellings
and 40 targets across 25 files**, 55 resolving and 16 declined, shapes
5/13/9/6/22. §68's write-up is the one new file, and its two pins on the `> 300`
floor are the two that move the class — but **one spelling and no target**,
because the floor at `:563` is already a target under the checklist's by-path
spelling and only the bare-module spelling is new. **Both of the two carry**, for
a reason #850's four do not: these are §68's own citations in a file new to the
census, so they are repointed to the line the floor is on now rather than left
naming where it was, and
[`xdata-moved-ranks-key-collision.md`](findings/xdata-moved-ranks-key-collision.md)
§5 says why that is a different thing from #850's decision. So the count of pins
that do not carry stays at **nine** and the count of records stays at **ten**;
only the shape split moves, `11` → `13` assertions. This summary names the two
without a resolvable spelling on purpose — a correction that added a 72nd pin to
the census it is correcting would move the figure it reports.)*

*(And again at the **#888 × #890** merge, one line later still, and this time
three of that paragraph's figures are the ones that move: **41** targets rather
than 40, shapes **5/11/9/6/24** rather than `5/13/9/6/22`, and **eleven** pins
that do not carry rather than nine. All three are the same line, and it is the
line those two pins name. `assertGreater(len(moved), 300)` was at `:563` of
`ec/tools/test_xdata_cluster_names.py` on the #888 × #891 tree and is at `:588`
here, so a pin the paragraph above calls *correct* is no longer correct, and the
"one spelling and no target" reasoning is what turns round on it: the by-path
spelling of that span **was** repointed by #890 to `:588` while the by-name one
stayed at `:563`, so the two no longer resolve to one target and the count that
was argued not to move moves by one. **The shape split follows for the same
reason** — `:563` was an `assertion` because that is where the floor was, and is
`other` here. The `71`, the `45`, the 55 resolving, the 16 declined and the
twenty-five files are unchanged, and so is the argument of the two paragraphs
below, which rests on the split between the line-content half and the
supersession half rather than on any of these counts. The two pins are written
bare above for the reason the paragraph says — spelling them out here would be
the 72nd pin in the class and would move the figure being reported. §65's
per-pin table, its finding 7 and its follow-up list carry the detail, and the
superseded `40`, `5/13/9/6/22` and `nine` stay above per §4a-4d, each true of the
tree it was measured on.)*
*(Re-measured again at the #885 merge, 2026-09-26, and **the sentence above is
wrong in a way this merge is what makes wrong**: it says #885's two pins both
resolve to the assertion, and on this tree they do not — because #850 moved the
assertion in the same window and neither branch shared a tree with the other.
Where #885 measured they landed on `:392` as a §2b comment, so `comment` went
9 → 11 there; **on the tree this section now lands in #890's thirty further
lines have turned `:392` into `decreased, {},`, so `other` goes 22 → 24 and
`comment` stays at 9** — the assertion itself is at `:588`. Either way the two
join the "does not carry" column at
**eleven against nine** rather than the carry column. The corrected run is
**71 occurrences, 25 files, 45 spellings, 41 targets, 55 resolves, 16 declined**,
measured by `python3 ec/tools/census_test_line_pins.py` on the merged tree
and on a clean `origin/main` worktree, which prints 69/24/44/40. **The 44 and
the 40 #885's own note predicted would not move, do**,
and the reason is #890 rather than this merge: its +25 repoint made `main` name
that file's `:417` and `:412-414` where #885 still names `:392`, so the tree
carries both and holds one more spelling and one more target than either side
had. **This is the first time the census has found two
pins that were correct where they were written**, and that is the sharper case:
a merged tree cannot distinguish a pin that was always wrong from one a
concurrent merge made wrong. Both are recorded in the write-up with the cause
beside the verdict, and the re-open condition is unchanged — what would make a
checker writable is a supersession marker, not a smarter resolver.)*

*(And again at the **#888 × #885** merge, where §69's two pins land beside §68's
rather than replacing them, and the figure is the sum of the two merges rather
than a third cause: **73 occurrences, 46 spellings and 42 targets across 26
files**, 57 resolving and 16 declined, shapes **5/11/9/6/26**. The four new
occurrences are disjoint — §68's two name `:563` in its own write-up and §69's
two name `:392` in the summary and in a second new file — so no spelling and no
target is the other's, and each count moves by the sum. **The two sets are
defective for opposite reasons and the write-up counts them apart**: §68's two
were correct where they were written and #890's repoint made them wrong;
§69's two were correct where they were written and a branch that had already
moved the line landed beside them, so **neither tree was wrong at any point**.
The pins that do not carry are therefore **thirteen**, the nine #850 left plus
both sets, and the carry count is **32** for the second time running against
`main`'s — four rows added, none of which carries. Nothing in the argument
below moves, which rests on the split between the line-content half and the
supersession half rather than on any of these counts.)*

*(**And again at issue #930, one line later, and this time all three of that
paragraph's figures go back the way they came — and the one it said could not
move is the one that does.** The follow-up list §65 names was worked: the two
by-name pins of finding 7 are repointed onto `:588`, the line the `> 300` floor
is on now, so both carry again. **It is measured on the tree the #885 × #771
merge produced rather than on the one that paragraph records**, because that
merge landed beside this pass: the run reads **105 occurrences, 78 spellings and
57 targets across 27 files**, 73 resolving and 32 declined, shapes
**5/19/10/6/33**, with **eleven** pins that do not carry and a carry count of 50
against the 48 that tree carried. The `assertion` shape is back because `:588`
is an `assertion`, the target count is back by one because `:588` was already a
target under the checklist's by-path spelling and `:563` has now lost the last
name it had, and the two rows are off the not-carrying list because they carry
again — a reading of the two cited lines, not a verdict from a tool. **The
`105`, the `27`, the `78`, the 73 and the 32 do not move**, and that is the
measurement that matters: two rows changed spelling and neither was added nor
deleted, so the correction did not add a pin to the census it is reporting on.
The run's **148** markdown files read is one more than the tree above, and one
file is all of the difference: this pass's own write-up,
[`findings/test-line-pin-repoint-563.md`](findings/test-line-pin-repoint-563.md),
which carries no `test_*.py:NNN` pin at all. **The six `> 300` pins of findings 6
and 8 are deliberately untouched in the same pass** and are #920's: they cite the
one `> 300` floor and name `:417`, `:412-414` and `:392` rather than `:588`,
which is both why they are stale and why this pass's repoint does not reach
them; they were stale in the tree when the census found them where these two
were correct when written, and doing all three at once would collapse the
distinction the eleven and the thirteen exist to record. The argument below —
the split between the line-content half and the supersession half — is
untouched, a repoint being a reading in a table rather than a property of the
class; line numbers are written bare for the reason the paragraph above gives.)*

**Two of the issue's extraction numbers did not reproduce, and both are the
scan's fault rather than the tree's.** Its "12 ambiguous `tools/` pins" are four
`windows/tools/` citations a prefix-recognising regex truncates into `tools/`
and two `../tools/…` paths `ec/annotations/xdata-register-map.md` writes
relative to itself — so the class has **no** unresolvable path on this tree, and
`out-of-range` and `ambiguous-path` are 0 as well. Every pin names a file that is
in it and a span it has: **the whole defect is in the line-content half.**

**The checker is declined, and the measurement is the argument rather than my
having to assert it.** Only 5 of the 57 resolving pins name a test's `def` line;
11 name an assertion, 9 a comment, 6 a blank line and 26 something else, so no
single anchor covers the class. And supersession in it is unmarked prose in at
least six shapes — a repoint list naming the stale value, a "deliberately not
fixed" bullet, a "the check caught it here" sentence, an "At the time of writing"
lead-in, a pin qualified by a commit, a dated findings section — of which the
two-shape vocabulary `check_citation_lines.py` already uses catches exactly one,
and the one it catches is a *correct* citation. *(Measurements of that
paragraph's shape split, per §4a-4d, none of them in dispute: **5 / 15 / 5 / 8 /
11 over 44** as the issue was filed, **5 / 11 / 9 / 6 / 22 over 53** after #850,
**5 / 13 / 9 / 6 / 22 over 55** on the #888 × #891 tree where §68's two repointed
citations are the only thing between the second and the third, **5 / 11 / 11 / 6 /
22 over 55** on the tree §69 measured, and the **5 / 11 / 9 / 6 / 26 over 57**
printed above. The supersession
records are eight unmarked shapes out of ten, of which the vocabulary catches two
and both are correct citations — so the argument is unchanged and the margin is
larger, which is the opposite of what a re-measure usually shows.)* A checker
would redden on
sentences that are true, which is the surest way to get a check switched off. The
re-open condition is written down: a supersession marker this class's authors
would use, or a decision that pins into a test file must name a `def`.

No citing prose is repointed here — twenty-six files' worth of edits against
open agent PRs, and both of the issue's two are already recorded in place under
§4a-4d — and the per-pin table is the hand-off for that pass. The wider
`.py:NNN` class (373 occurrences, 229 targets, 34 files) is measured for scope
and not censused, and is **not re-measured at any of the merges since**: it was
taken with a scratch definition that is not committed, so re-deriving it would
publish a *different* measurement under the same name. It stays the record of the
tree it was measured on, the same treatment the 50/23 and 52/24 above get. **The
part of that claim which does carry is the narrow one** — §68 and §69 between them
add only `test_*.py:NNN` pins, which are the *excluded* class, so their own four
cannot move the wider figure; that is an argument about what those two sections
added, not a re-run, and it is the distinction the write-up draws in the same
place. **One other shared file moved, a constant and a comment:**
`check_doc_figure_pins.py` reads an int inside any asserting call in `ec/tools/`
as a pin, so this census's own committed-tree figure — **`50` when the suite
landed**, `69` at the #850 merge, `71` once §68's and §69's pins are in — made
the checklist's
unrelated §2b `50` measure held and reddened #849's suite; its `SELF_MODULES`
tuple already carries the rule for exactly this, and adding the two census
modules to it puts §2b back at eight held and ten unheld and its printed
denominator back at the `175` the doc-figure audit quotes. *(Three later
measurements, per §4a-4d, and none is this paragraph being wrong about the
tree it was written on: the figure the suite pinned moved `50` → `52` when §68's
write-up joined the census, then to the **`71`** the #888 × #890 and #885 merges
each re-derived, and then to the **`73`** this tree re-derives, so the
collision is **preventive rather than current** — §2b measures the same **eight
held and ten unheld** with the exclusion in place as without it. #850 has since
moved §2b itself, to **eighteen held and none unheld over a `190` denominator**,
which is the correction §66 below and
[`doc-figure-pin-audit.md`](findings/doc-figure-pin-audit.md):123 record, and it
is why the `175` above is kept as written rather than restated. The exclusion is
the general rule and is kept; the suite's pin carries a comment saying what
moved it. `73` collides with nothing in §2b either, and the measurement is
re-run on the merged tree rather than carried over — it does not read eight-and-ten
because #850 gave each of the ten unheld figures a literal at an `assertEqual` and
moved the run: §2b reads `18 figure(s), 18 measured held, 0 measured unheld` over
`190 literal(s) inside a check` on this tree. *(Two later measurements, per §4a-4d
and neither a figure any verdict above rests on: the `190` is the run the tree
this paragraph was written on gave, #945's `test_check_pin_table_rows.py` takes
it to the **`194`** this branch's base re-derives, and #941's new suite to the
**`197`** this tree gives — the `18 measured held, 0 measured unheld` above
unchanged on all three runs.)*

**And a fifth axis on that same class, added by issue #941, because the four
published above are all properties of *where* a pin is written and the one that
decides how much damage an edit does is *which test file it names*.** The
write-up is
[`pin-table-by-cited-file.md`](findings/pin-table-by-cited-file.md); the tool is
`ec/tools/check_pin_table_by_cited_file.py` and it reads this census's own
`census()` rather than walking the markdown again, so its `resolves` and
`declined` columns reconcile back to the **73** and **32** above. **33 of the 73
resolving pins name a line in `ec/tools/test_xdata_cluster_names.py` and 21 in
`ec/tools/test_grade_0751_isolation.py` — 43 of the 105 occurrences on one suite
and 79 on two** — which is the number an edit above either file has to be paid
against, and the other half: **11 of the 37 indexed `test_*.py` are named by any
pin and 26 are named by none.** It renders no verdict and moves none of the
figures above; the concentration is the cost of an edit, not an accusation, and
the census's `carries` / `does not carry` table is untouched. *(Its own three
denominators moved by construction, since the new file is markdown and the new
suite is one of the 26: markdown read `149` → **`150`** and indexed test files
`36` → **`37`**, per §4a-4d and the same treatment the 50/23 and 52/24 above
get. The `105`, `27`, `78`, `57`, the shape split and the verdict tally do not
move at all, and `test_census_test_line_pins.py` is green against them.)*

*(And both of the figures that parenthetical gives for `main` are one short of
`main`'s own tree, measured here rather than asserted, because the same window
brought a second markdown file and a second suite and this note counted the
first of each. **A `git archive origin/main` extraction reads `151` markdown
files and `38` indexed test files**, against the `150` and `37` above, and
`census_test_line_pins.py` on the merge this section lands in reads **`152` and
`38`** — the one markdown file being #929's
[`xdata-moved-ranks-collision-scope.md`](findings/xdata-moved-ranks-collision-scope.md)
and the `38` being a suite either branch added and both added. **The pair this
note is actually about moves with them and is the half worth reading**: the
**11 named / 26 named by none** above becomes **11 named / 27 named by none** on
the merged tree, the `26` → `27` step being #777's `tools/test_doc_patch_refs.py`
rather than anything #941 wrote, and `ec/tools/test_check_pin_table_by_cited_file.py`'s
own index pin was re-set to the measured **38 / 11 / 27** with the reason in the
comment beside it. All four superseded values stay written per §4a-4d, and
[`findings/test-line-pin-census.md`](findings/test-line-pin-census.md) carries
the re-transcribed block and a per-merge section for it.*

*(Two of that note's three denominators are superseded by movement rather than by
anything being wrong, and the values stay written above per §4a-4d. #778's merge
(`77ce75df`) landed after the branch measured, so **`origin/main` now reads `152`
markdown files rather than the `151` above** — verified by extracting it again
rather than by differencing — and the tree this section lands in reads **`153`
and `38`**, the one file being #778's
[`xdata-two-largest-case-restatement.md`](findings/xdata-two-largest-case-restatement.md).
**`11` named and `27` named by none are unchanged by either**, because the file
that moved the corpus count carries one pin of its own and #929's carries none;
§74 carries the full correction and the extraction table. The suite the note
names is `tools/test_doc_patch_refs.py` — issue **#777**'s work, landed as
`24460001`, which is PR **#944** — so that #777 and #944 are two numbers for one
commit rather than two files.)*

No register `status:` moved, no `registers.yaml` figure was
refreshed, no CSV or `xdata-symbols.csv` was regenerated, no Ghidra project was
opened, no gate was edited, no register was read back, and nothing is opened in
another repository.

## 66. §6a's per-direction rows and §6b's cluster split are held, and the checklist's "eight unpinned" is a retraction (2026-09-25, issue #850)

> **Numbering note, added at the merge, and this one is renumbered five times
> over.** Written as §59, and #816 (`2665a6a8`) took §59 on `main` in the same
> window — it is two sections above now, and the §29 addendum,
> `xdata-cluster-names-guard-off-recipe.md`, the register map and
> `xdata-no-eq-guard-measured-state-correction.md` all point at **§59** for that
> one. #849's summary took the same next free number this one did, and so, at
> this merge, did #851's — so this summary is renumbered again, to **§62**, the
> only free number left, and the seven in-place pointers this issue adds (§29's
> merged-tree note, §54's parenthetical, five of them, and §60's correction
> above) are repointed with it. **§62 was not free on the tree this actually
> lands in**: #852's moved-rank measurement reached it in the same window, from
> the same §59, and #886 took §63 behind it. This summary is therefore
> renumbered once more, to **§64**, and the seven pointers carry **§64** with
> it. They are the exception here, and *not* left at §62 per §4a-4d, because the
> distinction is the point: each of the seven is a pointer at this summary, so a
> number that has become #852's is a wrong pointer rather than a superseded
> record, while the two `§62`s in the sentences above are the record of a number
> that was really taken and stay as they were written. §61 is #851's, §62
> #852's, §63 #886's and §64 #850's; §60's amendment and
> §61's record the same correction from the other side. A
> section number is a property of the merge in the same way the runner's totals
> are — see `runner-red-suite-set.md` — which is why the collision is recorded
> here rather than left for the next reader to find.
>
> **Renumbered a fourth time, and settled the way the third was: this one gives
> way again.** #713's per-program column split reached **§64** on `main` in the
> same window, written as §63 and renumbered for #886 taking that — so the
> `§64` three paragraphs above is not #850's, and **§64 is #713's and this is
> §65**, the last section in the file. #713's was already committed when the
> collision became visible, so the rule §60's numbering note set at the third
> merge applies unchanged a fourth time: the branch's own summary is what gives
> way, and every pointer this issue adds carries **§65** with it. **Eleven `§64`s
> were repointed, not the seven above**: the seven this issue adds, plus four
> written at earlier merges against a §64 that was free when this branch last
> ran — the owner list in §60's note, and the amendments §60, §61 and §62 each
> carry. One of those four is a different job from the other three, and is worth
> separating: a *pointer* at this summary moves, but §60's *list of owners* is
> re-derived rather than moved, so it reads "§64 #713's and §65 #850's" now and
> keeps a `§64` in it that is #713's. That is the only `§64` in the tree this
> issue added that still names a section that is not this one, and it is a list
> rather than a pointer by construction. #713's own note is left as it was
> written, with its "last section in the file" clause corrected in place beside
> it per §4a-4d.
>
> **Renumbered a fifth time, and settled the way the fourth was: this one gives
> way again.** #887's `test_*.py:NNN` line-pin census (`bb4c1d27`) reached **§65**
> on `main` in the same window — written as §64, and renumbered there for #713
> taking that — so the `§65` the amendment above settled on is not #850's, and
> **§65 is #887's and this is §66**, still the last section in the file. The
> rule §60's numbering note set at the third merge applies unchanged a fifth
> time, and for the same reason: #887's was already committed when this collision
> became visible, so the branch's own summary is what gives way, and every
> pointer this issue adds carries **§66** with it. **Fourteen `§65`s are
> repointed, not the eleven `§64`s above** — the eleven that amendment moved to
> §65, plus three more this issue adds in the same pass, which are named here
> for the first time because that amendment did not: the two in §64's numbering
> note above and the one in `tools/README.md`'s ninth-thing paragraph. One of the
> fourteen is still the odd job out, and it is the eleventh that amendment
> already named: §60's *list of owners* is re-derived rather than moved, so it
> reads "§65 #887's and §66 #850's" now, while §60's *amendment* beside it moves
> with the other thirteen. #887's section carries no numbering note of its own to
> correct in place — it landed on `main` with §65 already free, so it claims
> nothing about its own position and nothing about it has gone stale — and the
> collision is therefore recorded from this side only.
>
> *(One clause of the fifth amendment above is corrected in place at the next
> merge, the same treatment the fourth gave #713's: "**§65 is #887's and this is
> §66**, still the last section in the file" was true when it was written, and
> #888 took §66 in the same window and settled at **§67** — so §66 is no longer
> the last section. Its number does not move; only the clause about the end of
> the file is stale, and the reader it would mislead is one looking for the last
> section. #888's own note is the other side of this pair, and is left as it was
> written.)*
>
> *(And that one is corrected once more at the **#888 × #890** merge, where the
> outcome it names changed: **#888 settled at §68, not §67**, because #890 landed
> a §67 of its own between them. So this file's last section is **§68**, and there
> is now a §67 that is neither #888's nor #850's — #890's, about the `write` line's
> direction. The clause is stale in the same place and for the same reason it was
> the first time, which is the whole of what a section number is: a property of
> the merge rather than of the section. §66's own number does not move, and
> neither amendment above it is affected; #888's note carries its own half.)*

The write-up is
[`xdata-6a-direction-rows-pinned.md`](findings/xdata-6a-direction-rows-pinned.md);
this is the summary. §54's checklist named eight figures in §6a's table and
§6b's console block that no test held, and asked for the five of them that are
printed as *rows* to be held to the page that prints them. All five are now, by
`ec/tools/test_xdata_cluster_names.py`: four per-subset direction rows inside
`test_the_census_is_the_one_6a_measured` — `main-ec` `write` `3,948`/`3,206`,
`main-ec` `read` `7,189`/`7,935`, `pd` `write` `193`/`142`, `both` `write`
`279`/`239`, each with the `1,169`/`108`/`49` and `13,891`/`603`/`1,202`
denominators §6a prints beside it in the same assertion — plus a decomposition
asserting the three `write` deltas are the `742 + 51 + 40` the case's existing
`833` is the sum of, and §6b's `390`/`50` per-program cluster split in a new
`TheExportOwnershipClusters`. **That last one is a separate class on purpose:**
it is a different flag's census, and §50 describes the other class as holding
"a seventh case", so an eighth case there would falsify a published sentence.
Every one of the ten new expectations was perturbed in turn, the message
captured and the value reverted; the transcript is in the write-up, and each
message names its §6a/§6b line and carries the measured figure.

**The audit is the part that corrects something, and it is corrected twice.**
The issue is right that five figures were unheld; it does not say the others
were, and **on this tree three of the checklist's eight §2b rows already had a
check that held all or part of them** — `4,966` by `--check`'s cell-for-cell
comparison, `1326`/`440` by `ORACLE`/`OWNERSHIP` keys asserted in `--self-test`,
and `157`/`858` for the *default* census. So §2b's
heading, "**Eight, unpinned — these are the ones that decay silently**", was an
overclaim in exactly the shape §4 records twice, and it is corrected in place per
§4a-4d: the wrong count stays visible, both tables gain a "held by" column rather
than losing rows, and §2a gains the four rows this change moved from one to the
other. **Two rows stay open, and the first draft of this paragraph had it
backwards.** It credited `1218`/`9320` to `OWNERSHIP["main_distinct"]` /
`["main_refs"]` (`:1256`) "asserted at `:3840-3842`", but that assertion reads
`OWNERSHIP["distinct"]`/`["refs"]` — `1326`/`10178`, the census-wide pair — and
`grep -n 'OWNERSHIP\[' ec/tools/xdata_register_map.py` showed the `main_*` pair
read by nothing in the tree; `9,320` was asserted nowhere, and the `1218` that
is asserted is `ORACLE["main_distinct"]` (`:744`) for the **default** census,
beside `14,838` where §6b prints `9,320`. So that row was unheld rather than
partly held, and the count it was carrying is five/two/one, not four/two/two.
The `157`/`858` row is the one that is narrower than it looked — those two
*are* held, but by `ORACLE["extmem_pd_*"]`, which measures the **default**
census's token spellings; `OWNERSHIP` carries no `pd_*` key, so nothing holds
§6b's de-duplicated pair. The guard-off `pd` cluster count `51` is the third
figure left unheld, the missing other half of the `394` §2a pins.

*(Corrected at the merge, 2026-09-25: **the first of the two rows above is no
longer open, and the `main_*` pair this paragraph calls unread is read.** #849
landed in the same window and added the "and its main-EC half is" `check()` at
`ec/tools/xdata_register_map.py:4315-4319`, which reads `OWNERSHIP["main_distinct"]`
and `["main_refs"]` and compares them against the in-process export-ownership
census — §6b's own run, which is that row's subject, so it is a whole hold and
not a partial one. `grep -n 'OWNERSHIP\[' ec/tools/xdata_register_map.py` now
returns the `main_*` pair as read, and §60 above is that issue's own account of
why it had to be. **The two sides had reached opposite conclusions about the same
two keys from opposite ends** — #849 from "a value in a constant that nothing
reads is a promise wearing the costume of a pin", this section from "the key is
defined and read by nothing" — and both were right about the tree each was
measured on. What is left open is the `157`/`858` pair and, outside §2b's
tables, the `51`: the third figure above, which is the one this correction does
*not* touch. §2b and
[`xdata-6a-direction-rows-pinned.md`](findings/xdata-6a-direction-rows-pinned.md)
now say exactly that. The wrong versions stay visible per §4a-4d.)*

Nothing was flipped, re-keyed or regenerated: the `--export-ownership` default
stays off, `xdata-cluster-names.csv` keeps its 9 keys, both committed CSVs
reproduce with 0 differences, and both test runs pass scratch `--out-` paths
into a temp dir because each flag refuses to write anywhere else. No tool, CSV,
`registers.yaml` or gate was edited, `agent-gates.sh` still runs `--check` and
`--self-test` but not the unittest suites, and nothing was read off a machine —
no register, no image, no laptop, no Windows. `bash tools/run-tests.sh` read
`33 suite(s) run, 1020 tests; one or more FAILED` on the tree this change was
written on and read `34 suite(s) run, 1035 tests; one or more FAILED` on the tree
it lands in, #851 having added a suite in the same window — **and
`35 suite(s) run, 1076 tests` on the tree it actually lands in**, #887 having
added `ec/tools/test_census_test_line_pins.py` at 41 cases, so
[`runner-red-suite-set.md`](findings/runner-red-suite-set.md) carries the
sequence and `tools/README.md`'s first paragraph the current pair; the red suite is
`ec/tools/test_check_cluster_citations.py` on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220`, which is #822's
file, is red on a clean `origin/main`, and is named here rather than fixed here.

## 67. The 833 enters `write`, and the word "leaving" was the whole of the error (2026-09-26, issue #890)

**The figure is unchanged and one word was wrong, in four places, because a
tool printed it that way.** `xdata_moved_ranks.py pair`'s §6a line summed
**signed** `offreg - on` differences and printed the total under the label
"references leaving `write`". The tool's convention is committed →
guard-off, so a column that rises has references **entering** `write` and none
leaving — `--no-eq-guard` lifts the `==` rejection at
`xdata_register_map.py:1753` and lifting one exclusion only admits. A signed
sum of non-negative terms is a gross figure wearing a directional label, and
three committed pages carry the label: `xdata-06c2-06db-timers.md:785`,
`xdata-moved-ranks-fall.md:142` and `:150-159`. All three are corrected in
place, the wrong wording left visible per §4a-4d, and **the 833, the 210 and the
0 are byte-identical** — re-measured on this tree, per program and in total.

**Measured, not recalled.** Over the 1,326 committed rows: **210** addresses'
`write` rises, **0** falls, gross increase **833**, gross decrease **0**, net
**+833**, `refs` changes on **0**. The gross and the net coincide *because no
address decreases*, which is the property nothing held and the net alone cannot
show; it is now asserted per address by
`test_xdata_cluster_names.py::TheGuardOffRegeneration::test_the_census_is_the_one_6a_measured`.

**The tool reports gross movement in each direction beside the net**, from one
`write_movement()` helper the report and four new `--self-test` cases both
read — the line had no case at all before, because the only `pair_report()`
call in `self_test()` passed `registers=None`. A `closes:` line in the file's
existing `across_report` idiom marks `MISMATCH` if `write changes` and the
movement disagree.

**One correction to the issue's own arithmetic, stated because it is
arithmetic.** Its `sum(max(0, on - off))` would print **0** and discard the
833; and the closure it asked for, `entering + leaving == changed`, cannot
hold — one is a sum over references and the other a count of addresses, and
this census moves 833 across 210. The closure that is available is per address
(`len(entering) + len(leaving) == changed`), and that is what is printed. The
four pages that still carry the old wording as a *record* of a run, and the one
that carries the opposite convention correctly, are each named with a verdict
in the write-up. §62's summary at `:8091` says "leaving" and is left as the
shared-file edit it is; this section is the correction beside it.

> **Numbering note.** The plan this implements read §63 as the next free
> number, from a tree where §62 was last. Four sections have landed since
> (§63–§66), so this takes **§67**. No in-place pointer is renumbered by it:
> nothing elsewhere cites a number that this one took, and unlike the five
> renumberings §66's note records, there is no earlier summary competing for it.

The measurement, every carrier of the word with its verdict, the four new
self-test cases and the known-answer transcript are in
[`findings/xdata-write-direction-correction.md`](findings/xdata-write-direction-correction.md).
No image was opened, no register read back, no laptop, EC or Windows machine
involved; both censuses are committed text plus a regeneration into `/tmp`.
Nothing was re-derived: 210, 0, 833, 1,326 and 445 all reproduce, so §6a, §6b
and `xdata-moved-ranks-fall.md` keep their figures. `ec/tools/test_check_cluster_citations.py`
is red on this branch and was red before it, for the two `0x0464`/`0x0465`
disagreements §66 records; `bash tools/run-tests.sh` read 35 suites and 1,076
tests before this change with that one red, and the 43 `--self-test` checks
and 30 tests of `test_xdata_cluster_names.py` pass after it.
## 68. A duplicated `cluster_key` was a quieter number, and the count that read it is now keyed on the rank (2026-09-26, issue #888)

> **Numbering note, added at the merge, and this one gives way — twice.** Written
> as §66, and #850 (`e611e065`) took §66 on `main` in the same window — renumbered
> five times over to get there — so this summary was renumbered to §67. Then
> #890 (`bdfddcfd`) landed its own §67 above this one, the section immediately
> above it being the first §67 this branch's own file never carried. By the rule
> §66's note set and this note applied the first time — the summary already
> committed on `main` does not move, and the branch's own gives way — this
> section is **§68**, still the last section in the file.
> **Nothing else moves, because nothing pointed at the number.** Unlike the six
> earlier renumberings this issue adds no `§67` of its own: its write-up and the
> amendment it makes in `xdata-moved-ranks-fall.md` both cite `§62` (#852) and
> `§4a-4d`, and neither of those is this section, so the three references this
> issue *does* make to its own summary — in
> `xdata-moved-ranks-key-collision.md` §9 and the fall file's §9 — are repointed
> with it, and there is no pointer owed to a reader sent to the wrong place. A
> section number is a property of the merge in the same way the runner's totals
> are — see `runner-red-suite-set.md` — which is why the collision is recorded
> here rather than left for the next reader to find.
>
> *(And one clause of that note is corrected at the next merge, in the same place
> and for the same reason §66's was: "this section is **§68**, still the last
> section in the file" was true when it was written, and #885's §69 landed below
> it, so §68 is no longer the last section. **Its number does not move** — #885's
> is the branch's own summary and gives way, as the rule above says — and the
> correction is beside the clause rather than in it, per §4a-4d. The clause is
> the one a reader looking for the last section would be misled by, and the rest
> of the note is unaffected: nothing pointed at §68, and #885's own note records
> the same collision from the other side.)*

The write-up is
[`xdata-moved-ranks-key-collision.md`](findings/xdata-moved-ranks-key-collision.md);
this is the summary, and §62 is where a reader looking for this tool lands.

**The tool §62 added reported its headline number as the length of a map keyed
on `cluster_key`, and a map cannot report that it lost a row.** Two ranks of one
census carrying one content hash is not supposed to happen — and does not, in
any census this tree holds — but the dict comprehension behind
`moved_ranks()` would have made it one number smaller rather than an error, and
`intact` is derived from that number, so `moved + intact == |common|` would
have kept closing over it. That closure is §62's check that `366 + 64 = 430`, so
the one check that could have caught it could not. `keyed_by()`'s docstring is
where the precondition was written down, and its output is used as injective by
`flip_table()` and `swept_report()`; `moved_ranks()` was one function away from
the function documenting the assumption. A **second, unnamed** loss sat one line
below: the intact listing tested `cluster_key not in moved`, so an *intact*
rank sharing a key with a moved rank was dropped from a listing that was
supposed to show it.

**Measured, and no published figure moves.** Both pairs were regenerated exactly
as §62 §1–§2 prescribes — the `e169a0e4` worktree for the 430-row half, both
guard-off runs writing to `/tmp` — and the pre-change tool was diffed against
this one: the **whole** of the difference is one added line per `pair` block,
reading `cluster_key unique across the … committed row(s): 0 collision(s)`, and
`across`, `across --swept` and `cause` diff **empty**. `366/64` and `315/124`,
the **71/266/23/40** flip table, `closes: 366 - 315 = 51` over `(71 - 23) + (29
- 26)`, and the four §4 mean-delta cells all come back unchanged, and §62 §2's
two transcripts carry the new line so they still reproduce. All four censuses
the run read — 439, 430, 439 and 445 rows — measure 0 collisions over their
distinct keys.

**So this is a latent defect made reachable, not a wrong figure found in the
tree, and it is written up that way.** The fix is `moved_ranks()` keyed on
`cluster_id` — a rank is the key of the dict `clusters_of()` returns, so that
join cannot collapse — plus one `duplicate_keys()` helper checked at each of its
three uses: unconditionally in `pair`, beside the counts it qualifies, and
conditionally in `across`/`cause`/`--swept`, which are the key-indexed views and
say so when the key projection is not injective. **No refusal and no `--strict`
flag**, because once the count is rank-keyed `len(moved)`, the per-program split
and `intact` are all *correct* under a collision, and refusing would reject a run
whose headline number is right; what is left is a genuine ambiguity about which
rank a key names, which is a caveat to state. **No gate is wired**, for §62
§8's reason — a collided *committed* census already fails `xdata_register_map.py
--check`, which compares those CSVs cell for cell. `--self-test` goes from 25
checks to 31; the six added are the duplicated-key fixture the old suite could
not express, because `write_census()` takes a key per row and every fixture gave
each rank its own. The `> 300` floor, `TheContentKey`, every CSV, every figure
in §62 and every gate are unchanged, and nothing is opened in another
repository.

*(Re-measured at the merge, 2026-09-26, and the only figure that moves is the
`--self-test` headcount, because the two issues between this one and the tree it
lands in both added checks of their own: **30 to 36** on that tree rather than
25 to 31, the five in between being #889/#917's five `deciles()` cases, and the
six still this issue's. Re-run there it printed 36, `all checks
passed`; the committed census measures 439 rows over 439 distinct `cluster_key`
values and 0 collisions, as §62 records. §62's `--self-test` transcript is
re-transcribed to the same 36, with the arithmetic corrected to
`14 + 10 + 1 + 5 + 6 = 36` and the 5 attributed, per §4a-4d — the figure above is
left as it was written because it is true of the tree this issue was written
on.)*

*(Re-measured again at the #888 × #891 merge, and the **36 becomes 45** rather
than staying put, because #891's rank-shift block landed beside this one after
the measurement above was taken: nine more checks, printing at 31–39, ahead of
this issue's six at 40–45. `python3 ec/tools/xdata_moved_ranks.py --self-test` on
the merged tree prints **45**, `all checks passed`, and the committed census
still measures 439 rows over 439 distinct `cluster_key` values and 0
collisions — so nothing this section reports about the *tool's behaviour* moves,
only the headcount. `xdata-moved-ranks-fall.md` §9 carries the merged transcript
and closes the arithmetic as `14 + 10 + 1 + 5 + 9 + 6 = 45`; §62's correction
above carries the same figure against the 39 it first recorded. Both superseded
counts stay visible per §4a-4d, because each is true of the tree it was measured
on.)*

*(Re-measured a third time at the **#888 × #890** merge, and the **45 becomes
49**: #890's four `write_movement()` cases are already committed in the section
above and print at **21–24**, ahead of this issue's six, which move from 40–45
to **44–49**. `python3 ec/tools/xdata_moved_ranks.py --self-test` on the merged
tree prints **49**, `all checks passed`, and the committed census still measures
439 rows over 439 distinct `cluster_key` values and 0 collisions — so nothing
this section reports about the *tool's behaviour* moves, only the headcount, for
the third time running. `xdata-moved-ranks-fall.md` §9 carries the merged
transcript and closes the arithmetic as
**`14 + 10 + 1 + 5 + 9 + 4 + 6 = 49`**, the `4` being #890's; §62's correction
above carries the same figure against the 39 it first recorded. The 31, 36, 39
and 45 all stay visible per §4a-4d, because each is true of the tree it was
measured on.)*

*(Re-measured a fourth time at the **#929** merge, where the **49 becomes 53** —
and the only figure that moves is the headcount again, for the fourth time
running. §929's four checks print at **50–53**, after this issue's six at
44–49, and are the same six' own blind spot rather than a new subject: every
case in the suite was reached through a census with a mover in it, and §929
adds one whose only colliding rank is intact. Measured on the merged tree,
`python3 ec/tools/xdata_moved_ranks.py --self-test` prints **53**,
`all checks passed`, and all four censuses the §929 re-derivation read — 439,
430, 439 and 445 rows — measure **0 collisions** over their distinct keys, with
`across` and `across --swept` diffing **empty** against the pre-change tool. So
nothing this section reports about the *tool's behaviour* moves: the committed
census still measures 439 rows over 439 distinct `cluster_key` values and 0
collisions, and the `366/64` and `315/124`, the **71/266/23/40** and
`closes: 366 - 315 = 51` figures all come back unchanged.
`xdata-moved-ranks-fall.md` §9 carries the merged transcript and closes the
arithmetic as **`14 + 10 + 1 + 5 + 9 + 4 + 6 + 4 = 53`**. **What does move is
this section's own coverage claim**, and it is corrected in place in
[`xdata-moved-ranks-key-collision.md`](findings/xdata-moved-ranks-key-collision.md)
§3 rather than here: the check was made at three of six uses, over three of the
four censuses `keyed_by`'s call sites reach, and the guard-off census had none.
§74 below carries that, and §68's write-up's §2, §3, §6 and §7 carry the
corrections. The 31, 36, 39, 45 and 49 all stay visible per §4a-4d, because each
is true of the tree it was measured on.)*

## 69. The 427-row census is stale at `e6c88864` and unreadable at `1fcd5f1e`, and the guard's per-address effect is measured a third time (2026-09-26, issue #885)

> **Numbering note, added at the merge, then extended by each of the merges
> that followed.** This section was written as §63, and #886's `--swept`
> second-holder count (`32218840`) took §63 on `main` in the same window, so it
> was renumbered rather than left to collide; §63 is now #886's count fix
> above. It then gave way a second time, to #713's per-program split
> (`4151cb1c`) taking §64 on `main`, and a third to #887's `test_*.py:NNN`
> census (`bb4c1d27`) taking §65, so it is **§66** on the tree this note was
> first written for. A fourth collision, and the same rule as the first three —
> the branch's own summary gives way to whatever `main` already committed — makes
> it **§67**: #850's §6a/§6b summary took §66 on `main` in the same window and is
> a section above. A fifth collision, and the same rule again — #890's
> write-direction correction (`xdata-write-direction-correction.md`, PR #923)
> took §67 on `main` in the same window, so **this was §68** and #890's
> correction is a section above. **A sixth, and the same rule one last time:**
> #888's `moved_ranks()` key-collision summary
> (`xdata-moved-ranks-key-collision.md`) took **§68** on `main` in the same
> window, so **this is §69** and #888's section is the one immediately above
> this. It is the last section in the file. The
> references this branch added to its own number — the pointer closing §62, the
> parenthetical in §64's numbering note, and the ones in §65 above and in
> [`test-line-pin-census.md`](findings/test-line-pin-census.md) — all carry
> **§69** with it;
> nothing else the branch wrote named it, since the write-up, the checklist's
> correction block and the fall file's closing note name the issue and the
> write-up instead. §62's, §64's and §66's notes, each written at its own
> merge, and §68's, likewise call their section the last one in the file; that
> was true
> then, and is
> left visible with a correction beside it rather than edited into it, per
> §4a-4d. **§67's does not** — that note claims the number was free rather than
> that its section was last, which is why it needed no correction here and is
> not listed among the four.
>
> *(And this section's own note joins them at this merge, in the same place and
> for the same reason §68's was corrected: "It is the last section in the file"
> was true when it was written, and #771's summary landed below it, so §69 is no
> longer the last section. **Its number does not move** — #771's is that
> branch's own summary and gives way, as the rule three collisions up states —
> and the correction is beside the clause rather than in it, per §4a-4d. The
> sentence above counting the corrected notes at four is left as written rather
> than edited to five, for the same reason each of the four was. **Its own
> references are unaffected, and that is the half of the note this merge does
> not touch:** the pointer closing §62, the parenthetical in §64's note, and the
> ones in §65 above and in
> [`test-line-pin-census.md`](findings/test-line-pin-census.md) all name §69,
> which is still this section, because §69 is the number `main` already held
> and therefore the one that keeps it. The write-up's
> [`xdata-moved-ranks-427-pair.md`](findings/xdata-moved-ranks-427-pair.md)
> and §67's correction table are unaffected for the same reason.)*

> *(And one clause of the note above is corrected at this merge, in the same
> place and for the same reason §68's was: "so **this is §69** … It is the last
> section in the file" was true when it was written, and #929's collision-scope
> summary has landed below it, so §69 is no longer the last section. **That
> summary's own number gave way four times by the same rule the rest of this
> note sets** — to #885's §69, then #771's §70, then #942's §71, all in one
> window, #777's §72 in a later one, and #778's §73 in a later one still — so
> **§74**, and the file ends there.
> **§69's number does not move**, and the correction is beside the clause
> rather than in it, per §4a-4d. The clause is the one a reader looking for the
> last section would be misled by; nothing else in the note is affected: #888's
> section is still the one immediately above this one, and the six references
> below still carry **§69** with it.)*

The write-up is
[`xdata-moved-ranks-427-pair.md`](findings/xdata-moved-ranks-427-pair.md);
this is the summary. §62 named the limit of its own measurement — one observed
re-derivation, so one data point — and issue #885 asked for the measurement that
would narrow it, on the reasoning that the census had been re-derived more than
twice. **That premise holds — the census file has been committed at five sizes,
435, 426, 427, 430 and 439 rows, across 22 commits — and the third point is
still not available to take**, for a narrower reason than "427 was never
derived": neither 427-row commit can be paired.

**The issue's first check comes back negative, and the route that replaced it is
checkable.** `--no-eq-guard` (#528, `db6d7d2d`) is **not** an ancestor of
`e6c88864` — `git merge-base --is-ancestor` exits 1, where it exits 0 for
`e169a0e4` — and the flag appears nowhere in the 427-era tree. The route is
therefore a back-port, and it is verifiable rather than asserted: the guard's
`store_target`/`classify`/`scan` are **byte-identical** at `e6c88864` and at
#528's parent, so #528's diff fits with 12 hunks, no rejects, and a resulting
change set that is **line for line #528's own**; the patched tool's
`--self-test` differs from the unpatched tool's by exactly #528's two added
assertions. The issue's fallback — comparing against today's tree — was not
taken, because today's tool carries unrelated changes that would move the address
universe on their own.

**The 427-row census does not match its own tree, and the tree there already
derives the 430-row census.** At `e6c88864`, `--check` exits 1 (**428 on disk vs
431 generated**) and that commit's own `--self-test` fails its "the committed
CSVs match a fresh generation" line — a red check in the commit, not an artifact
of the patch. `e169a0e4` is green, and so are the 426-, 435- and 439-row
commits: of **seven** census commits spot-checked, the **two 427-row commits**
are the red ones. They are not the same defect — at `1fcd5f1e` the row count
matches and the content does not. *Why* either was committed that way is not
derived here and is left as a follow-up.

**Measured like for like, `e6c88864` and `e169a0e4` are the same census.** All
430 keys shared, no key on one side only, **430 of 430 with identical
membership** (and 439 of 439 on the guard-off side), differing only in rank
numbering on 17 and 18 keys and reference totals on 8. So `moved` is **366** in
both, `across` reports **0 flipped clusters** and a flipped-set distribution of
`no rows`, and the guard perturbs the **same 210 addresses**. Against the 439
pair the 427-era pair reproduces §62's 430-vs-439 table on **every cell but
one** — 400 keys shared, the same 71 / 266 / 23 / 40, the same 51 closing over
four terms, the same size distribution, the same mean deltas, the same twelve
flip rows. The exception is the `main-ec` rank-shift **range**, `-11 to +24`
against §62's `-8 to +15`: a rank shift is differenced against pair A's own
numbering, and the 427-era census numbers 17 keys differently, so that is the
one figure in the block that moves when the two pairs are the same census.

**The literal pair, and why it is not the number to bank.** Measured against the
committed file rather than the tree, `moved` is **379** — and that mixes the
guard with a stale file. The two separate cleanly, because the guard re-buckets
an occurrence already counted and so cannot move `refs`: guard 210 addresses /
**0** `refs`, staleness 9 addresses / **16** `refs`, literal 216 / 16, closing
**210 + 9 − 3 = 216** over the address sets and 0 + 16 − 0 = 16 over the `refs`.

**The direction question, answered.** The new figure is 366 — **equal** to the
430 figure, because it *is* the 430 measurement. It is neither above nor below,
it adds no point to 366 → 315, and the series is still **two** points. No
"and it decays", and no threshold edit: `> 300` stays at
`ec/tools/test_xdata_cluster_names.py:400`, the 15 ranks of headroom are as they
were, and the count that is the floor's remains **315**. The size sequence
427 → 430 → 439 is correct for the era it covers, but the census file has been
committed at **five** sizes in all — 435, 426, 427, 430 and 439 rows, 22 commits
— so the reason the series is two points is narrower than "427 was never
derived". `1fcd5f1e`, the only other 427-row commit, **does** derive 427 rows;
it is the census commit immediately before `e6c88864` added `cluster_key`, and
`xdata_moved_ranks.py` raises `KeyError: 'cluster_key'` on its census. Nine of
the 22 censuses predate `cluster_key` and none is readable by the pair tool, so
the era it can measure begins at `e6c88864` — the commit whose file is 427 rows
and whose tree is 430. The `1fcd5f1e` pair is **not measured here**, not
measured and found equal to 366, and back-porting `cluster_key` to reach it was
not taken.

**What did gain: §62's structural claim now rests on three measurements.** The
guard's per-address triple is **210 addresses, 0 `refs`, 833 references entering
`write`** in all three trees, across three tool generations, the newest reached
by inheriting the flag and the oldest by back-porting it — an independent check
of the claim the `> 300` floor rests on. The 155 addresses the 439 generation
adds are again **0** perturbed. The cluster-level delta's starting value, 1,623,
is likewise reproduced on the 427-era tree, 50 commits earlier than the tree the
fall is dated to, so it extends how far back that value reaches and says nothing
about what happens next. Its 1,030 end is #852's own 439-row pair and is not
re-measured here, and for the same reason as above neither end is an independent
observation of the fall from that tree — the third tree adds the reach of the
starting value, not a second witness to the fall.

> **Correction, 2026-09-26, at the #890 merge: the direction word in the
> paragraph above was *leaving*, and the figure is unchanged.** The tool's
> convention is committed → guard-off, so a `write` column that rises has
> references **entering** `write` and none leaving; §67 above is the correction
> of the label that carried the wrong word this far, and the per-occurrence
> census is in
> [`findings/xdata-write-direction-correction.md`](findings/xdata-write-direction-correction.md).
> **The 833, the 210 and the 0 are byte-identical** and all four of the three
> trees here still read the same triple — the word was wrong, the arithmetic
> never was. The wrong wording stays visible here per §4a-4d. **The `pair`
> transcripts in this section's write-up print the old wording and stay as
> written**: they are records of runs of a back-ported copy of the 427-era tool,
> which predates the correction, exactly as §67 leaves the older transcripts in
> the fall write-up.

> **Correction, 2026-09-26, at this merge: the floor's line number in the
> paragraph above was correct where it was written and is wrong here, and it is
> left in place rather than repointed.** #850 put 239 lines into
> `ec/tools/test_xdata_cluster_names.py` in the same window, so the
> `assertGreater(len(moved), 300)` this section and its write-up both cited at
> `:392` is at **`:563`** on the tree this branch merged into, and #890's later
> +25 repoint put it at **`:588`** on the tree this section now lands in.
> `:392` on that tree is a §2b comment. The wrong version is left visible per
> §4a-4d. **Nothing about the finding moves**:
> the floor is untouched, the 15 ranks of headroom stand and 315 is still the
> count that is the floor's, which is what the sentence is about. What changed is
> only the line a citation names, and **leaving it stale rather than repointing
> it is deliberate**: the pin's being *wrong* is the measurement
> [`test-line-pin-census.md`](findings/test-line-pin-census.md) records as
> finding 8 — one of two pins that were correct on the tree they were written
> against and are wrong on this one, which a merged tree cannot distinguish from
> a pin that was never right. That file's follow-up 1 gives the reason none of
> the eight is repointed: deciding *what a stale pin was meant to name* is a
> next pass's call. **The re-open condition there is unchanged** — what would
> make a checker writable is a supersession marker, not a smarter resolver.

No CSV, YAML, tool, threshold, assertion or gate was edited, no image was opened,
no register was read back, and nothing is opened in another repository. The one
patched file in this work is a copy of the 427-era tool inside a `/tmp` worktree
that has been removed. `check_cluster_citations.py` reports the same two
citations before and after this change, both **#822's** at
[`xdata-cluster-names-guard-off-recipe.md`](findings/xdata-cluster-names-guard-off-recipe.md):220.

## 70. The two path-taking readers are kept, and their docstrings name their callers (2026-09-26, issue #771)

> **Numbering note, added at the merge.** This section was written as §69, and
> #885's 427-row-pair summary took §69 on `main` in the same window, so it is
> renumbered to the next free number rather than left to collide. §69 is now
> #885's summary above — whose own note records this same collision from the
> other side, and whose "last section in the file" is corrected beside it rather
> than into it — and this is **§70** and is the last section in the file. *(And
> that clause is in exactly the position §68's and §69's were in: it is true of
> this merge, and the next section to land below this one corrects it beside
> itself rather than into itself, per §4a-4d. It is the sixth such note in this
> file and the second to arrive in one merge, which is what two branches adding a
> summary each in the same window looks like from here.)*
>
> *(And the clause above is corrected at this merge, in the same place and for
> the same reason §68's and §69's were: "this is **§70** and is the last section
> in the file" was true of the **#932** merge, and #929's collision-scope summary
> landed below it in the same window, so §70 is no longer the last section and
> the file ends at **§74**. **Its number does not move**, and the second collision
> runs the other way from the one this note opens with: #929's summary was
> written as §69 as well and gives way to *all five* — the §69 above, this §70,
> #942's §71, #777's §72 and #778's §73 — so it is renumbered **§74** below. The
> correction is beside the clause rather than
> in it, per §4a-4d, and the sentence above counting these at "the sixth such
> note" and "the second to arrive in one merge" is left as written rather than
> edited to the seventh and the third, for the same reason each of the six was.
> **Its own references are unaffected, and that is the half of the note this
> merge does not touch:** nothing in #771's write-up, in this section's body, in
> the two other edits this branch makes in this file, or in the four drift tables
> that moved with the twelve pins names this section's number, and the one line
> the census re-registered *at* this section —
> [`test-line-pin-census.md`](findings/test-line-pin-census.md)'s `:9046` — is
> moved again below by #929's added prose rather than by this section, which is
> what that file's own note for the row now says.)* **Nothing this branch
> wrote pointed at its own section number, so there was no reference to
> repoint**, and that is worth stating rather than left for the next reader to
> check: the write-up cites `docs/findings.md` §6a and §4a-4d and
> `0751-capture-encoding.md` §2 rather than this section, the two other edits
> this branch makes in this file name lines in a tool rather than a section (the
> `#771's docstring prose to :1063` and the `:1084`/`:1108`/`:986` repoint
> above), and no tool, test or gate reads a section number out of this file. A
> section number is a property of the merge in the same way the runner's totals
> are — see [`findings/runner-red-suite-set.md`](findings/runner-red-suite-set.md)
> — which is why the collision is recorded here rather than left for the next
> reader to find.

Write-up: [`0751-path-taking-reader-fates.md`](findings/0751-path-taking-reader-fates.md);
this is the summary.

**Both functions are kept, and the docstring that asserted a caller who does
not exist now names the three that do.** #749's split left
`refused_capture_rows` as an open-and-delegate whose last paragraph read
*"kept for a caller that holds a path rather than rows"* — naming no one, which
is the failure mode `0751-notice-two-moments.md` says it had already closed
for another docstring, recurring one function down in one the same merge added.

**The issue's own central claim is stale against this tree.** It greps for
`refused_capture_rows` and reports *"no caller, in production or in the
suite."* There are **three**, all in `test_grade_0751_isolation.py`, and the
write-up quotes the `grep -rn` that finds them. One of the three is
load-bearing rather than incidental: `existing_mark_findings` pastes
`read_capture`'s exception over the *first* reason, so the order of the checks
is only observable through a path-taking entry that does not paste it, which is
a property `refused_capture_rows` has and `existing_mark_findings` does not.
The deleted option was also the more expensive one: `0751-capture-encoding.md`
§2 is titled *"The sites, all thirteen"* and carries a row naming the function,
so deleting it would mean retracting a shared findings file's own count for a
function whose callers are real. Keeping it costs zero retractions.

**`existing_mark_labels` is a published API, not a test fixture**, and now says
so. Three things outside the grader's own suite depend on it:
`measure_mark_provenance.py`'s `families` oracle table, which the census run
consumes as well as `--self-test`; `ec_watch.py`'s `load_label_vocab`, which
reads its *name* into a liveness probe; and `ec_watch-marks.md`, which
documents it as the reader the prompt reaches.

**Two cross-references were describing where a body used to live**, in
`take_capture_row` and in `partition_capture_rows` — the latter crediting the
lenient read to the delegate into itself, which cannot be the source of a
reason it has already applied. Both now name the function whose body makes the
claim. The cross-references that name the *path* a reader takes were already
right and were deliberately left alone, and the anti-drift guard's test **body**
is untouched: #749 left it green on purpose and it is what holds
`partition_capture_rows` to `take_capture_row`. Two anchors the issue also named
are not recoverable — the `:690` is not on this tree at all — and are recorded
as checked and found rotten rather than reconstructed.

**One consequence the issue could not have predicted, and the reason this
section is not just a docstring edit.** `measure_mark_provenance.py` pins exact
line numbers into `grade_0751_isolation.py`, and this change is prose *in that
file*: growing four docstrings moved twelve pins and took the full census from
44 `ok` rows and exit 0 to 20 problems and exit 1. That is the tool working as
designed — its comment says a moved line is a mismatch *"whether it moved
because the file grew above it or because the claim was wrong, and the two need
a reader, not a guess"* — so the pins were **re-measured, not relaxed**, and
the four drift tables that quote them (`0751-mark-provenance-shapes.md`,
`0751-notice-two-moments.md`, `0751-capture-encoding.md`,
`0751-capture-row-shape.md`) moved with them. The *reader set* did not: 7
writers, 8 sites, 6 reader calls, 48 in-suite calls, the same as before, and
the tool exits 0 again. No EC was opened, no capture taken, no register read.

## 71. The per-pin table's four mechanical columns are reconciled against the run, and the fifth is still a reading (2026-09-26, issue #942)

**The gap was one join, and it had been missing since the census landed.**
`docs/findings/test-line-pin-census.md`'s per-pin table carries five columns and
`census_test_line_pins.py` computes four of them — the citing file, the citing
line, the cited target, the read kind and the shape — so only the verdict is a
judgement, and **nothing held the other four to the run.** A row whose citing
line quietly moved therefore kept reading as an ordinary row, and this
repository has paid for that by hand four times: #891 re-registered two citing
lines, #889's note moved two more, and #930 re-registered
`../findings.md:9046` → `:9077` in the very merge that landed the correction
above it. A merge that only *adds a paragraph* invalidates rows, and the only
signal was a person re-reading `--verbose` against 105 rows.

**`ec/tools/check_pin_table_rows.py` is that join.** Measured on the merged tree
before anything was changed and again by the tool afterwards: **106 rows, 106
records, 106 placed, and all seven classes 0** — 0 `unparsed-row`, 0
`unplaced-row`, 0 `row-without-record`, 0 `duplicate-key`, 0 `read-differs`, 0
`shape-differs`, 0 `path-differs`. Green on this tree because the table *does*
reconcile today; the point of a green check on a correct tree is that the next
drift is loud rather than the last one silent.

*(The `105` this section read when it was written is #778's merge, and the
paragraph is re-transcribed rather than the figure quietly replaced: that
issue's new write-up brings a pin with it and its edit to
`ec/tools/test_xdata_cluster_names.py` re-registered 33 others, so the census
went 105 → 106 and the per-pin table was re-derived from the merged tree's own
run to follow it. This is the coupling stated at the foot of this section being
paid one merge later, and it is worth reading as the cheapest possible instance
of it — **37 rows moved** and the loud signal was a tool, not a person. The
`37` is 33 re-registered target columns, **six** re-registered citing lines and
the one added row, and the six is three more than #778's own merge had: the
merge correction beside this paragraph is thirteen lines in
[`doc-figure-pin-audit.md`](findings/doc-figure-pin-audit.md), which moved the
three rows citing *that* file by the same thirteen. **A merge note that lands
above three pins costs exactly the three it moves**, which is the cheapest
possible instance of the same coupling, one file down.)*

**It reads no verdict cell, and it exits 0 on a tree where every verdict is
wrong.** That standing is what makes it safe in a gate, and the suite asserts
it twice over — once with every verdict cell nonsense, once with the cell
empty. So §65's *no checker* is **not** overturned: that section declines a rule
that *renders a verdict*, and this one renders none. A green run says the table
still describes the run; it says nothing about whether any of the 106 pins
carries its claim.

**One correction to the issue's own argument, in place per §4a-4d.** The
separate `path-differs` class was argued to catch a citing file moving to a
different directory. Measured, that does not survive the match key: a record's
`path` has exactly one source, `census.resolve()`, and the key pins both of its
inputs, so the re-derivation is an identity on a placed row and the case is
already caught by `read-differs`. The class is kept — it is the assertion that
fires if `census.resolve()` stops being a pure function of its inputs — and the
suite demonstrates it fires rather than leaving that as a claim.

Two findings about the table's own spelling came out of building it: the table
abbreviates the census's `beside-the-citing-file` as `beside`, and writes an em
dash where the census writes a bare hyphen in all 32 declined rows. Both are
carried as an alias map with the reason in a comment — normalising them in the
table would edit a shared, actively churning file for a cosmetic reason — and an
**unrecognised** cell is a reported problem rather than a pass, so a fourth
spelling fails rather than slips through. The citing cell also has two spellings
at 104 : 1, and a parser that took only the common one would have reported the
whole table unparsed.

**Not in any gate.** `.github/` is template-copied and the push token has no
`workflow` scope, so the wiring is prepared at
`docs/ci/agent-gates-pin-table-rows.patch` for a human to `git apply`, in a new
item 12 of `docs/agent-pipeline.md`, with its `gate` line at the *head* of the
list so it composes with item 5's and item 10's in either order —
`tools/test_agent_gates_patches.py` applies the set in every ordered pair, and
all six now land together, parse, and are shellcheck-clean. The suite
(`ec/tools/test_check_pin_table_rows.py`, 36 cases) needs no wiring to be run:
`tools/run-tests.sh` discovers every `test_*.py` in the repository.

**The coupling this adds, stated because it is a cost.** The census reads every
markdown file except the write-up above, so writing a `test_*.py:NNN` citation
into any other one now requires a new row in that table, and omitting one is a
`row-without-record`. Nothing in this section, in the write-up, or in the other
three files this issue touches spells one, deliberately, rather than growing the
table a row at a time.

The write-up is
[`docs/findings/pin-table-row-reconciliation.md`](findings/pin-table-row-reconciliation.md).
No image was opened, no capture taken, no register read back, and no laptop, EC
or Windows machine was involved: this is bookkeeping over committed text.

## 72. The names prose gives a prepared gate patch are held in both directions, and the two deliberate ones are an enumerated fact (2026-09-26, issue #777)

Write-up: [`doc-patch-reference-gate.md`](findings/doc-patch-reference-gate.md);
this is the summary.

**The gap.** `check_doc_links()` reads markdown *links* and nothing else, so it
finds 686 `.md` link references at `271389d` and **zero** references to a patch.
`docs/ci/agent-gates-*.patch` is named in prose 53 times across 16 markdown
files at that same commit — the tree the issue was filed against; the checker's
own run prints the current figure, which is the one to re-derive. A `git apply`
instruction a human copies out of a header is worth exactly as much as the name
beside it. `tools/test_agent_gates_patches.py` holds each patch *header's* `git
apply` line; the prose is a different surface and #745's fold broke it the same
way, by six manual edits across five files with nothing to notice a miss.
`tools/check_doc_patch_refs.py` holds both directions — a name in the prose
resolves to a file, a file on disk is named somewhere — and reads markdown
links onto a patch, which `check_doc_links` cannot see because its pattern ends
in `\.md`. There is one of those at `271389d` and **two on the merged tree**,
#942's `pin-table-row-reconciliation.md` having added a second beside this
issue's, so the self-test's link count is pinned to two and the census figure
above stays the one-commit measurement it is pinned to be.

**Four corrections to the issue, recorded as corrections.** Its 213 is 686 here
(the conclusion is unchanged). Its 34-across-9 is **53 across 16**, and the
difference is the **bare spelling** — a name with no `docs/ci/` in front of it,
which is 19 of the 53 and is how a table row's first cell has to be written; a
`docs/ci/`-only pattern would pass this tree while holding 64% of the references
and would not see three of the four deliberate ones at all. There are **8
glob-shaped** references describing the *set*, so the character class has to
exclude `*`. And the deliberate population is **4 references to 2 absent
names**, not "three of the 34" — only one of the issue's 34 qualified
references names an absent file, the other three being bare-spelled. The
`.py`-side population, three further references inside
`tools/test_agent_gates_patches.py`, is a follow-up: the checker is scoped to
`*.md`, and widening it would put this tool in a file #772 owns.

**The historical rule, and why it is an enumeration rather than a per-reference
opt-out.** Three of the four deliberate references are *records* — §43's sentence
about the collision, and a measured-results table row whose whole content is a
filename as it was — and `CLAUDE.md` §4a-4d says a superseded claim stays
visible with a correction beside it. Fencing them would move lines in two of the
most-cited files here, which is the defect `ec/tools/census_test_line_pins.py`
exists for. So the opt-out is a two-name set in the checker, keyed on the
**name** rather than `file:line` for the same reason, and it is held in **both**
directions: each key is still absent from `docs/ci/` and still cited by
markdown, both failures name the key, and a fourth absent name is refused. The
live direction is checked too — every patch on disk is cited — which is the half
that broke in `test_readme_suite_table.py`. **The bound is stated rather than
hidden: any new reference to one of those two names is exempt by construction.**

**Not in the gate, and that is a decision with a reason.** No
`docs/ci/agent-gates-*.patch` was added, because a seventh would need a `gate`
line at the same seven-line list's anchor where two patches already insert — two
patches that each apply alone and do not compose is what
`tools/test_agent_gates_patches.py` exists to catch, and §71's took the *head*
of that list for exactly this reason — and it would need adding to that suite's
held `PATCHES` set, which #772 owns.
[`findings/prose-line-citations-held.md`](findings/prose-line-citations-held.md)
took this exact decision for the `run-tests.sh` wiring; this follows that
precedent. The recipe is `docs/agent-pipeline.md` item 13, the renumbering
§71's item 12 forced on both. The **suite** needs no wiring at all:
`tools/run-tests.sh` finds every `test_*.py`, so
`tools/test_doc_patch_refs.py` is collected on a full run.

**Nothing here is a live test and nothing is evidence about the firmware.** It is
arithmetic over committed text: no EC opened, no register read back, no capture
taken, no `status:` moved, no hardware or Windows run implied. The gate wiring is
prepared rather than landed for the reason items 4 through 12 each give —
`.github/` is template-copied and the push token has no `workflow` scope — and
that is a change this branch does not make.
## 73. The two-largest case was green and vacuous, and it now derives the names a key cannot find (2026-09-26, issue #778)

> **Numbering note, added at the merge.** §70 records that it "is §70 and is
> the last section in the file", and predicts in the same breath that the next
> section to land below it corrects that clause beside itself rather than into
> itself. **Three** landed below it in this merge, and only one of them is this
> one: #942's per-pin reconciliation took **§71** on `main` in the same window
> and #777's prose-name census took **§72**, and neither says anything of §70's
> clause, so the correction is owed here and is placed here, in the same place
> and for the same reason §68's and §69's were, per §4a-4d. By the rule the
> earlier collisions set — the summary already committed on `main` does not move
> and the branch's own gives way — this section is **§73**, and it is the last
> section in the file. *(§70's clause is therefore true of this merge again,
> one merge later, and says itself it is a property of the merge rather than of
> the file.)*
>
> **And that clause is corrected once more at the `#929` × `#778` merge, in the
> same place and for the same reason §68's, §69's and §70's were.** #929's
> collision-scope summary
> ([`findings/xdata-moved-ranks-collision-scope.md`](findings/xdata-moved-ranks-collision-scope.md))
> landed below this one, and its own number gave way for a fifth time by the
> rule this note applies — written as §69, it has been renumbered to **§70**,
> **§71**, **§72** and now **§74** — so **this section keeps §73** and is no
> longer the last section in the file, and §74 is. **Its number does not
> move**, and the correction is beside the clause rather than in it, per
> §4a-4d. Nothing else in the note is affected: #942's §71, #777's §72 and this
> §73 are still the three sections between §70 and the end, in that order, and
> the paragraph below is about §70 and still holds.
>
> **Nothing pointed at the number that moved.** Nothing this branch wrote named
> §70, so there was no reference to §70 to repoint, and nothing named §71 or
> §72 either: the write-up cites §6a and this summary cites §4.4 and §50, none
> of which is this section, and no tool, test or gate reads a section number out
> of this file. A section number is a property of the merge in the same way the
> runner's totals are — see [`findings/runner-red-suite-set.md`](findings/runner-red-suite-set.md)
> — which is why the collision is recorded here rather than left for the next
> reader to find.

Write-up: [`xdata-two-largest-case-restatement.md`](findings/xdata-two-largest-case-restatement.md);
this is the summary.

**The issue's premise is stale and the defect behind it is worse than the one
it describes.** It opens with the suite red on `main`; #753 landed the
`--no-eq-guard` recipe and it reports `Ran 30 tests … OK`. So
`test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key` was
green, and passing for the wrong reason: its two hard-coded pairs are disjoint
clusters at **Jaccard 0.0000**, so it compared the largest cluster in the census
— which carries no name — against an unrelated one, and `assertNotEqual` on two
cluster keys is true of any two distinct clusters. It could not fail for the
reason its name claimed, which is why §4.4's correction predicted this and why
the fix is a restatement rather than a repair.

**It is a rename, not an addition.** The case is now
`test_every_name_the_key_cannot_find_is_carried_by_overlap`, and it selects the
`how == "overlap"` records of the tool's own `carry_names` over the two
censuses — eight `exact`, **one `overlap`** (`mode-oem-init`, 0.9681) and 436
`none`. It reads no cluster id and no name, so #279's pair-accessor pass, which
moved both typed names a generation behind, cannot break it again. §50's
published "a seventh case" is why it stays a seventh case rather than an
eighth: the count stays 30. The measured count is prose in the write-up, for
the reason `assertTrue(movers, …)` already gives.

**The negative control is what distinguishes it from the status quo.** Pointing
the derived set at `level-block-086x` — a cluster the key *does* find — turns it
red on `from_key != cluster_key`, naming the key that was found where overlap
was required. The old assertion satisfies that same edit.
## 74. The collision check covered the moving part of each census, and `keyed_by`'s docstring said it covered all of it (2026-09-26, issue #929)

> **Numbering note, added at the merge, then extended by the second, third and
> fourth collisions.**
> This section was written as §69, and #885's 427-row pair
> ([`xdata-moved-ranks-427-pair.md`](findings/xdata-moved-ranks-427-pair.md),
> PR #892) took §69 on `main` in the same window, so by the rule §62's note set
> and every one after it applied — the summary already committed on `main` does
> not move, and the branch's own gives way — this was renumbered to **§70**.
> **A second summary took §70 on `main` in the same window**, so the same rule
> applies one more time and for the same reason: #771's
> [`0751-path-taking-reader-fates.md`](findings/0751-path-taking-reader-fates.md)
> summary (PR #932) holds **§70**, this is **§71**, and the two sections it gave
> way to are the ones above it. **A third took §71 on `main` in the same
> window** — #942's
> [`pin-table-row-reconciliation.md`](findings/pin-table-row-reconciliation.md)
> summary (PR #945) holds **§71** — so the rule applies a third time and for the
> same reason: this is **§72**, the three sections it gave way to are the ones
> above it, and the file ends here. **A fourth took §72 on `main` in a later
> window** — #777's
> [`doc-patch-reference-gate.md`](findings/doc-patch-reference-gate.md) summary
> (PR #944) holds **§72** — so the rule applies a fourth time and for the same
> reason: this is **§73**, the four sections it gave way to are the ones above
> it. **A fifth took §73 on `main` in a later window still** — #778's
> [`xdata-two-largest-case-restatement.md`](findings/xdata-two-largest-case-restatement.md)
> summary (PR #947) holds **§73** — so the rule applies a fifth time and for the
> same reason: this is **§74**, the five sections it gave way to are the four
> above it and that one, and the file still ends here. **The five summaries are
> ordered by what
> `main` held first, not by which branch merged**, and that is the whole content
> of the rule — which is why neither §69's number above nor §70's moves, and why
> §70 records the collision beside its own "last section" clause rather than in
> it. **Everything else in this note still stands, because nothing else in it
> named the number.** The three references this branch makes to its own summary
> are the closing sentence of the fourth re-measurement note at the end of §68,
> the correction §69's numbering note carries beside its "last section" clause,
> and the one this branch adds to §70's numbering note beside the same clause;
> all three read "§70" as the branch first wrote them, "§71" on the tree #942
> merged into, "§72" on this branch's tip, and **§74** on the tree this lands in,
> and each is corrected in place rather than repointed, since none was committed
> anywhere. The write-up names §68, the
> property this one corrects, and §4a-4d, and none of those is this section. A
> section number is a property of the merge, the same reason the runner's totals
> are — see `runner-red-suite-set.md`.

The write-up is
[`xdata-moved-ranks-collision-scope.md`](findings/xdata-moved-ranks-collision-scope.md);
this is the summary, and §68 is where a reader looking for the property lands.

**§68's fix left the check covering a *subset* of each census it re-keys, and
`keyed_by()`'s docstring said it covered all of it.** The claim was *"every
caller of this prints `duplicate_keys()` over what it re-keyed rather than
relying on it"*, and measured it was three of six census re-keyings, over three
of the four censuses the seven call sites reach. `pair_report` printed the
precondition for its **committed** census only, so a run that read a pair
printed an unconditional clean bill of health for a census it had not looked at
— the guard-off one, which is the population every rate in `cause` is divided
by. `flip_table`'s `collapsed` ran `duplicate_keys` over the **moved** ranks, so
a committed census whose only collision was between two ranks that stayed put
reported nothing at all. And `swept_report` hand-rolled its own copy of the
collision sentence rather than calling the helper, which is how one site ended
up checked and another not.

**This is a fix to what a report *says*, and no published figure moves.** Both
pairs were regenerated exactly as §68 prescribes —
`xdata_register_map.py --no-eq-guard` writing to `/tmp` for both, and the
430-row half's decompiled tree read out with `git archive e169a0e4 | tar -x`
rather than by adding a worktree — and the pre-change tool (`git show
31f683e5:…`, this issue's base) was diffed against this one. **`across` and
`across --swept` diff empty; `pair` gains one line and `cause` gains two, and
every added line reads 0 collisions.** The empty diffs are the load-bearing
half: the whole-census check and the old moved-subset check are both empty on a
clean census, so widening the population is a superset rather than a change of
behaviour. **366/64** and **315/124**, the **71/266/23/40** flip table,
`closes: 366 - 315 = 51` over `(71 - 23) + (29 - 26)`, and the four §68 §4
mean-delta cells all come back unchanged, and all four censuses the run read —
439, 430, 439 and 445 rows — measure **0 collisions** over their distinct keys.
`xdata_register_map.py --check` passes, the CSVs are not touched, and the `> 300`
floor and `TheContentKey` are untouched.

**What changed:** `collision_line` grew a `label` and an `only_if_collision`
(the word `committed` was hardcoded in both f-strings, which is *why* the
guard-off censuses could not be pointed at the helper at all);
`pair_report` prints the line for **both** censuses it reads; `collapsed` is the
whole committed census rather than its moved ranks, which is the population the
cells above it are drawn from; `collapse_line` says "committed rank(s)" rather
than "moved rank(s)"; `swept_report` folded into the helper; and `cause` prints
both guard-off lines above the population they qualify. `keyed_by`'s docstring is
narrowed from "every caller" to the unit that is actually enforced — **the
view**, not the function, because seven call lines reach four censuses by more
routes than four.

**And the check is now reachable where it was not.** `--self-test` goes from 49
to **53**, and the four are the shape the six §68 added could not express: a
fixture whose *only* colliding rank is intact, so the property is exercised in
the census where it costs no count. The fourth case is the first that *holds*
`keyed_by`'s claim rather than restating it — one case running `pair`, `across`,
`--swept` and `cause` over a colliding census and asserting a line for each of
the six (view, census) pairs the docstring names. **It can go red, and that was
demonstrated by reverting each edit in a scratch copy:** four of the five
reverts (the `cause` lines, `pair`'s guard-off line, `swept_report`'s loop and
`collapse_line` returning `[]`) are red on the coverage case. **The `collapsed`
widening is the fifth and it is not** — the coverage case's census collides on a
key two of whose three ranks moved, so the line is emitted over the moved subset
too and the case stays green; case 2 is what holds that population.
[`xdata-moved-ranks-collision-scope.md`](findings/xdata-moved-ranks-collision-scope.md)
§7 carries the per-revert result. The one earlier check whose expectation moved
is amended in place, with
what it was left visible beside it: `4 moved rank(s)` became `6 committed
rank(s)` when the population widened, and the two movers, the four-term closure
and the absence of a `MISMATCH` are the same three assertions as before.

**Four shared files are amended in place rather than edited, per §4a-4d, and
none of the superseded text is edited down:**
[`xdata-moved-ranks-key-collision.md`](findings/xdata-moved-ranks-key-collision.md)
§2 (the "false negative" argument's reach, and three transcripts re-transcribed
because the swept line's wording and `collapsed`'s population changed), §3 (the
heading says three uses; it was three of six), §6 (the `holders_by_program()`
bullet reads as though `cause` were covered; it was covered over the moved ranks
alone) and §7 (the headcount);
[`xdata-moved-ranks-fall.md`](findings/xdata-moved-ranks-fall.md) §9 (the
transcript and its arithmetic, `14 + 10 + 1 + 5 + 9 + 4 + 6 + 4 = 53`, verified
byte-identical to the run by `diff`); this section; and `tools/README.md`'s
merged-tree note. **One pin is repointed** —
[`xdata-decile-small-set-contract.md`](findings/xdata-decile-small-set-contract.md)'s
`xdata_moved_ranks.py:436` for `deciles()`, correct before this change and not
after it. **Two already-stale pins are left alone**: `tools/README.md`'s
`:243` and `xdata-write-direction-correction.md`'s `:181` were already wrong on
this change's base `31f683e5`, and deciding what a drifted pin was meant to name
is a next pass's call and not a merge's.**

**Nothing here is a hardware claim, and no live observation closes any part of
it.** The tool reads committed CSVs and synthetic fixtures, opens no image, and
touches no firmware. `test_check_cluster_citations` is red, as it is on the base
`31f683e5` with the same single failure (#822's write-up at
`xdata-cluster-names-guard-off-recipe.md:220`); this change neither fixes it nor
adds to it, and the new file contributes nothing to it. `--self-test` being in
no gate is #921's and is untouched, and no `--strict` flag and no refusal were
added: the counts are correct under a collision, and what is ambiguous is which
rank a key names — a caveat to state, not a run to abort. Nothing is opened in
another repository.

**Three figures in this branch's own write-up did not survive the merge beside
it, and all three are corrected in place above with the wrong value left visible,
per §4a-4d.** None is a claim about the collision check itself; all three are
line numbers and a corpus count, and all three are recorded here because
`test-line-pin-census.md` is where a reader lands, not here.

**The `:9083` was 31 lines low, and the table row was right.** The `#929` merge
section of [`test-line-pin-census.md`](findings/test-line-pin-census.md) printed
`:9046 + 37 = :9083` for the `> 300` floor's citing line, and the row in the
per-pin table it says it registered was registered to **`:9114`** — the two
contradicted each other on the branch's own tree, and the table was the right one
of the two. The cause is the same one the census's own exclusion exists to
measure: the base was read off the tree *before* #930 and the run was taken on the
tree *after* it. `git show 84a89d9a:docs/findings.md` has that line at `:9046` and
`git show 271389d7:docs/findings.md` at `:9077`, so **`:9077 + 37 = :9114`** is
the whole arithmetic and `:9046 + 37 = :9083` double-counts #930's move. The
`:9081` first pass stays visible beside it, and the row needed no re-registration
because it was never wrong. **On the tree this section lands in the row reads
:9158` rather than `:9114`, and that is #946 rather than #929**: #946's summary
edit to §65 above adds **26** lines, all of them above the `> 300` floor's
citing line in this file and none of them below it, and this section's own
correction to the same §65 note adds **18** more, so
`:9077 + 37 + 26 + 18 = :9158` is the whole of that move, and
[`test-line-pin-census.md`](findings/test-line-pin-census.md)'s per-pin table is
re-registered to `:9158` with the `:9114` above left visible as the branch's own
value, per §4a-4d.

**`13dfc146` does not exist on any tree here.** The `#929` × `#930` section
names it as the branch commit its figures were read off, and the review round
rewrote it; the branch tip is **`706f8946`**, which resolves. That section's
`149` corpus count
is likewise **`150`** on the branch's tree, because #942 added
[`pin-table-row-reconciliation.md`](findings/pin-table-row-reconciliation.md) to
the corpus, and the re-transcribed block at the top of that file takes both its
markdown-file count (`149` → `150`) and its test-file count (`35` → `36`, #942's
`ec/tools/test_check_pin_table_rows.py`) with it. `tools/README.md` gets a
seventeenth merged-tree note for the same two figures. **On this tree both
figures move once more, to `152` and `38`**, the two markdown files being #941's
[`pin-table-by-cited-file.md`](findings/pin-table-by-cited-file.md) and #777's
[`doc-patch-reference-gate.md`](findings/doc-patch-reference-gate.md) and the
suite being #777's `tools/test_doc_patch_refs.py` on top of #941's
`ec/tools/test_check_pin_table_by_cited_file.py`. **The `150`/`36` above and
`main`'s own `150`/`37` are both left written**, and neither was a defect: they
are each true of the tree they were measured on, and each side counted from the
same `149`/`36` base without seeing the other's two files.

**What the merge did *not* move is the larger half, and it was re-measured
rather than assumed.** All six rows `#929`'s edits had shifted still reconcile on
the merged tree — `check_pin_table_rows.py` reads **105 rows, 105 records, 105
placed, and all seven classes 0**, the `:9158` row included — because #942's
additions to this file all landed *below* every citing line the census reads.
`xdata_moved_ranks.py --self-test` still reads **53**,
`xdata_register_map.py --check` still passes at 1326 register rows and 439 cluster
rows, the committed census is still 439 rows over 439 distinct `cluster_key`
values with 0 collisions, and the four drift-table anchors `tools/README.md`'s
notes name — `deciles()` at `:487`, `write_movement()` at `:257`, `fall.md`'s §7
heading at `:536` and this file's pin registered at `:487` — are where those
notes say they are. **The suite totals are the one figure the window moved that is not
about the census**, and `tools/README.md`'s "What it runs" sentence is corrected
in place for it: the runner reads **38 suites and 1161 tests** where the three
merged-tree notes above record thirty-five and 1076 and #929's seventeenth
records thirty-six and 1112, and `python3 -m unittest discover -s ec/tools`
reads **857** where the same note records 830. The steps are `194` on the base
`c68f89df`, `830` after #942's 36 cases from
`ec/tools/test_check_pin_table_rows.py`, `857` on `main` after #941's 27, and
`857` here after #777's 22 — **which is the same 857 twice**, since #777 added a
suite and the literal count `check_doc_figure_pins.py` reports is what #929's
`xdata_moved_ranks.py` moved, and the two are different tools' figures. `test_check_cluster_citations` is the single
failure, red on pristine `main` at `c68f89df` with the identical two
`0x0464`/`0x0465` disagreements at `:220` of #822's write-up.

**The one prose line this branch added above a citing line was
kept the same length as the line it replaced**, so the `:9114` above is the
branch's value and not a fourth one: §69's numbering-note correction gained a
clause and lost a line elsewhere to pay for it, which is why the section this one
is numbered for was §72 and not §71, and why nothing below had to be
re-registered *on this branch*. **On the merged tree it did have to be, and by
the other side's move rather than this one** — the paragraph above gives the
arithmetic. **The section numbers are unmoved by all of that**, which is the
half worth stating: `:9158` is a line number, and a line number is a property of
the merge for the same reason the section number is.

**One pin did move, and it is `tools/README.md`'s own `:159`, because the
correction this merge owed it is above it.** The sentence saying how many suites
the runner finds was stale the moment #942 added
`ec/tools/test_check_pin_table_rows.py` — `c68f89df` added the suite without
re-deriving that sentence, so the figure was wrong on `main` before this merge and
is corrected in place, thirty-eight and 1161 where it read thirty-five and 1076.
The repoint list below it moved `:159` → **`:166`** on the branch and to
`main`'s **`:168`** on `main`, and the merged tree reads **`:197`**: the two
sides' seven and nine lines, plus the twenty-two this merge's own two corrections to
to that sentence add beside both, is `159 + 9 + 7 + 22 = :197` and is the whole of
it. `test-line-pin-census.md`'s per-pin table, its supersession-shape legend and
the blocker argument that name the line are re-registered to `:197`; the
branch's sixteenth note, which says nothing either branch wrote lands above that
line, is true of the tree it measured and stays. **That is this merge's own breakage, and
it is recorded here for the reason the rest of this section records its pins: a
merge that only adds a paragraph invalidates a row, and the row is the evidence
that the paragraph landed where the pin checker could see it.**

**And the `#929` × `#778` merge that puts this section at `§74` moved three of the
figures above, and all three are corrected here with the superseded value left
written, per §4a-4d.** None of the three is about the collision check, and none
is a new pin: they are a line, a corpus denominator and a table headcount, and
they are recorded because
[`test-line-pin-census.md`](findings/test-line-pin-census.md) and
`tools/README.md` are where a reader lands rather than here.

**The `> 300` floor's citing line is `:9173`, not the `:9158` above, and its
target is `main`'s `:400` rather than the `:392` this section's own paragraph
names.** The move is this merge's own and it is prose all the way down: the §69
numbering-note correction above took two lines where it had one, and the §65
correction beside the re-derived census figures took fourteen more, so
`9158 + 1 + 14 = :9173` is the whole of it and both halves of it are
corrections this section carries. The `:400` is #778's own re-registration of
the target, and `main` was right to make it — `git show :1:docs/findings.md` and
`git show :3:docs/findings.md` both spell the line `:392`, at `:9103` and
`:9158` respectively, and `77ce75df` is what moved the spelling. So the merged
row is `../findings.md` at **`:9173`**, naming `test_xdata_cluster_names.py`'s
`:400`, which is what `census_test_line_pins.py --verbose` prints and what
`check_pin_table_rows.py` reconciles at **0 read-differs**. The `:9158` and the
`:392` above stay written, each true of the tree it was measured on, and
`:9077 + 37 + 26 + 18 = :9158` is still the whole of the branch's move.

**The corpus denominator is `153`, not the `152` above, and both sides' `152`
was one short of the merged tree for the same reason.** Each counted the other
branch's markdown file and not its own, and `git archive` extractions of
`24460001`, of `origin/main` at `77ce75df` and of this tree read **`151`**,
**`152`** and **`153`** through the census tool's own walk. The branch's
correction in `test-line-pin-census.md` which records `main`'s pair as one short
of its own tree at `151` was right about the tree it measured and is superseded
by `main` taking #778 rather than by anything being wrong. **The class itself is
unmoved through all of it** — `106` pins, `28` files, `79` spellings, `58`
targets, `74` resolves, `32` declined and the `5/19/10/6/34` split — because
#778's write-up brings exactly the one pin its own correction already counted
and #929's brings none.

**`check_pin_table_rows.py` reads `106` rows, not the `105` above**, by that same
one pin and for the same reason, and the other six rows the two sides disagreed
about are re-registered in place in
[`test-line-pin-census.md`](findings/test-line-pin-census.md) rather than added.

**The one claim in this section that does not survive is the drift-table anchor,
and it is a `#778` move rather than a `#929` one.**
`xdata-moved-ranks-fall.md`'s §7 heading is at **`:547`**, not the `:536` the
paragraph above calls one of four anchors that "are where those notes say they
are". #778 added an eleven-line "Confirmed and acted on" paragraph to that
write-up *above* the §7 heading, `536 + 11 = :547` is the whole of it, and it is
the only line in this merge that lands above an anchor four notes in
`tools/README.md` name. The other three are unmoved and were re-measured rather
than carried: `deciles()` at `:487`, `write_movement()` at `:257`, and this
file's registered pin at `:487`. `tools/README.md` carries a nineteenth
merged-tree note for the `:547`, the `536` staying written in the three notes
above it there, and the sentence this section's claim sits in is left as written
rather than edited, per §4a-4d — the correction belongs beside the number it
corrects, and that number appears in four places rather than one.

## 75. The guard-off generation's `cluster_key` distinctness had no case behind it, and three of the four censuses are behind one now (2026-09-26, issue #962)

The write-up is
[`xdata-guard-off-key-distinctness.md`](findings/xdata-guard-off-key-distinctness.md);
this is the summary. #929 made the collision precondition visible at every view
that re-keys a census, and the *producer* half of it reaches two of the four
censuses a view can re-key: `TheContentKey` reads the committed census and
`xdata_register_map.py --self-test` checks a fresh guard-on generation. Neither
can be pointed at a guard-off census, because `--no-eq-guard` is refused
together with `--check` and `--self-test` at `:4976-4978` and refused without
scratch outputs at `:4985-4987` — a correct refusal, and one this change leaves
where it is. That left the census `cause`'s rates divide by with nothing behind
it, which is what `xdata-moved-ranks-collision-scope.md` §5 recorded as "nothing
holds *its* key uniqueness between runs". **Three censuses are now held and one
is not.** The fourth, the 430-row pair at `e169a0e4`, needs that commit's
decompiled tree and is named as unheld in three places rather than counted
toward the three. `keyed_by`'s docstring said two in a voice that read as all of
them; it now names all four and says which.

**`test_xdata_cluster_names.py::TheGuardOffKeyDistinctness` is a sibling class,
not an eighth case in `TheGuardOffRegeneration`,** because §50 above calls that
class's seventh case "a seventh case" and an eighth would falsify a sentence
this change has no business touching. Three cases over the one `guard_off()`
regeneration the module already caches: the hold case, the registers/clusters
agreement `TheContentKey` holds for the committed pair, and the negative
control. **The predicate is `xdata_moved_ranks.py`'s own `duplicate_keys()`**,
reached by the same `importlib` route the module already uses for
`xdata_register_map.py`, so the suite's check and the report's printed line
cannot be two implementations. The failure message names the colliding keys
*and the ranks carrying each* rather than a bare count.

**No published figure moved.** All four rows of `xdata-moved-ranks-collision-scope.md`
§4 come back — 439, 430, 439 and 445 rows, each over as many distinct
`cluster_key` values, 0 collisions — and so do `366/64`, `315/124`,
`71/266/23/40` and `366 - 315 = 51`. §4 of the new write-up prints the command
that derives each row beside it, and the `git archive e169a0e4` extraction is
checked rather than assumed: a guard-on generation from it reproduces that
tree's 430-row census, which is how the archive is known to be the right input.

**`test_check_cluster_citations` is red exactly as on the base** — 48 tests, one
failure, #822's `xdata-cluster-names-guard-off-recipe.md:220` on `0x0464` and
`0x0465` — and this change adds no disagreement to it. `xdata_moved_ranks.py
--self-test` keeps its **53** checks and `xdata_register_map.py --check` and
`--self-test` both still exit 0; the coverage belongs in the default sweep,
which is the issue's point about #921. Nothing was read off a machine, no CSV
was edited, and no gate was wired.

**The per-pin table moved and was re-derived, and that is the cost worth
naming.** Correcting `guard_off()`'s docstring shifted every class body below
it, which moves where 25 registered `test_*.py:NNN` pins land. Their shape cells
were re-derived from the census's own `--verbose` run, the published `5/19/10/6/34`
landing-shape split moved to `0/16/22/5/31` as a consequence and both places that
pin it were re-derived rather than lowered, and **eight verdicts were re-read** —
the pins that moved off a `def test_` header or an assertion, which is why
`test-line-pin-census.md`'s "the eleven that do not carry" is now nineteen. The
citing prose is not repointed here, per that file's own §7; the repoints are
named in the new write-up's §6. The read column (`53/19/2/32`), the headcounts
(106 pins, 28 files, 79 spellings, 58 targets, 74 resolving, 32 declined) and
the red set are all unchanged, which is what makes the shape the one column a
line shift could move on its own.

## 76. The other-capture exemption is the narrowest shape rather than the widest, and the tool's own worst hole is a retraction (2026-09-26, issue #794)

> **Numbering note, added at the merge.** This section was written as §75, and
> #962's
> [`xdata-guard-off-key-distinctness.md`](findings/xdata-guard-off-key-distinctness.md)
> summary (PR #965) holds **§75** on `main` in the same window, so it is
> renumbered to the next free number rather than left to collide. §75 is now
> #962's summary above, and this is **§76**. That runs the same collision the
> other way round from the one §74's note opens with — there #929's summary
> gives way to five sections; here this branch's is the one that gives way, and
> the section that keeps the number is the one that landed on `main` first.
> **Its own references are unaffected, and that is the half of the note this
> merge does not touch:** nothing in #794's write-up, in this section's body, or
> in the seven lines this branch adds to §47 above names this section's number —
> the write-up cites §47, §4a and §4a-4d rather than this section, the §47 edit
> names lines in a file rather than a section, and no tool, test or gate reads a
> section number out of this file. **A "last section in the file" clause is
> left off rather than written**, since §74's numbering note already carries one
> and §75 does not correct it either: what this merge adds is a section *below*
> both of those, and a clause asserting a position is what the next merge has to
> contradict beside itself. The record of where the file ends stays §74's note,
> and its count is untouched by this merge: the five summaries that note counts
> are all at or above §74, and §76 is not one of them.

The write-up is
[`testdata-row-claims-dated-capture.md`](findings/testdata-row-claims-dated-capture.md);
this is the summary, and §47 is where a reader looking for the property lands.
`ec/tools/check_testdata_row_claims.py` named its own worst hole in its
docstring: the `another capture's address` shape passed over **every** literal
in a sentence naming a dated capture in running prose — *"the rule buys one
correct row at the price of not checking that sentence at all."* **The shape is
gone and a resolution is in its place.** A **bare** (unbackticked) date in a
third-column sentence is now resolved against `evidence/ec-watch/<date>-*` and
the sentence's literals are held to the files that date resolves to, so the two
literals the run reported under the shape are two `checked` claims instead.

**The census came first and the sizing is the whole of the cost.** Four date
tokens in `ec/tools/testdata/README.md`, of which two are bare and **one**
carries literals: row 7's `0x0F58`/`0x0F5C`. `evidence/ec-watch/` is flat and
dates every capture in its own filename, so `<date>-*` is a glob and not a
guess; `2026-09-23-*` resolves to **six** files and both addresses are in one of
them (`2026-09-23-power-mode-cycle-0f00-0f5f.csv`, 4 and 6 lines). The run goes
**28 → 30 resolved, 26 → 24 unresolved, 28 → 30 checked, 14 → 15 claiming
rows**, the `another capture's address 2` entry leaves the shapes line, and the
other five shapes' counts are byte-identical — which is what says the change
moved what it was meant to and nothing else. The tool now prints a per-date
block naming each literal with the file set it was checked against.

**Three decisions are in the rule and none of them was free.** `DATED_CAPTURE`
itself **does not change** — the spelling already told a *file* from a
*capture*, and it stops being a reason and becomes the selector of the file set.
The two file sets are **never unioned**: a union would let row 7 pass on its
own after-dump, which covers `0x0F00-0x0F5F`, so the suite pins one case that
fails if the date is ignored and another — the one shape of this change that can
turn the run red — that fails if the two are unioned. And the union is taken
**over the date**, not narrowed by a word in the prose, which would be the
parser guessing; the cost of that is one address in any of a date's six files
satisfying a claim about that date, and it is written down in the tool's
docstring and in the write-up rather than designed away.

**A date that resolves to nothing is today's `unresolved`, with the glob it
searched, and never `absent`** — the §4 calibration made mechanical, and the
sixth entry of the closed shape list with a case of its own. **The docstring's
own "widest exemption here" bullet is retracted in place**, wrong wording left
visible with the correction beside it per §4a, which is the pattern this
repository uses for a conclusion that was stated more strongly than its
evidence supported — the same failure §4a-4d records twice. `reason_for()` lost
its last branch, so the ordering argument that said none of the six needs the
file set is repaired rather than left standing on five.

**One suite case could not survive the change and did not.** `test_the_other_capture_rule`
asserted that loosening the rule makes the run check *more*; the direction is
now inverted, so it became a sibling helper asserting it checks **fewer** with
an empty capture root, and the class docstring says why the sign differs rather
than leaving a reader to wonder whether the assertion is weaker.
`test_the_committed_tree_exercises_every_shape` dropped the sixth name — the
committed tree has **five** shapes with instances, and a test naming a shape
the fix removed is a test that fails on the fix. **The per-date block is
asserted on scratch trees, not as a count on the committed one**: the dated
sentences there resolve, so an expected number would turn every dated sentence a
later PR adds into a failure. Three wrong implementations were applied to the
tool in place and the suite run over each — union, ignore-the-date, and
drop-the-reason — and each is red, so "the fix can fail" is demonstrated rather
than asserted.

**Nothing here is a hardware claim, and no live observation closes any part of
it.** No capture is *opened*: the CSVs and `.txt` files under
`evidence/ec-watch/` are read as text, exactly as `carried_by()` already reads a
fixture. **Not claimed: that this would have caught #502 or #720** — carried
forward from §47 verbatim, since both repairs were to this column and neither
has been read back as a diff this tool could have been run over. No `status:`
moved, so `ec/annotations/registers.yaml` is not touched; row 7's sentence in
`ec/tools/testdata/README.md` is **not edited**, because it is true, it is now
checked, and editing prose to make a tool green is what this repository forbids.
`docs/ci/agent-gates-testdata-row-claims.patch` is **not** touched — the CLI is
unchanged — and it remains a human's `git apply`, so no gate is wired here. No
`gh pr create` anywhere.
