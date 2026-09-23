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
disjoint corpora: 44 of `registers.yaml`'s 56 addresses appear in the
decompiled tree at all, 41 of them in the EC and 3 only in the PD image.

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
| `0x73` | 50700-50717 | — | `DBAC` = 0, `ATPP` = `CPUA * 8` (`0x07D4`), `AMAT` = `DBAP * 8` (`0x07D5`) | `DBEN` (`0x07C4` bit 0) |
| `_Q84` | 52793-52811 | — | same as `0x73`'s then-branch | `DBEN`; raised by the EC, not by an ACPI client |
| `0x1176` | 50730-50733 | `CGCT` = `Arg1` (`0x07D7`) | Notify `PEGP` | — |

No branch in the table touches a battery or charge register. The
`0x1171`/`0x1172`/`0x1173`/`0x2273` selector family and the `0x73`/`_Q84`
query pair both end at the same `NPCF` objects, and the `0x73`/`_Q84` pair
reaches them from `CPUA`/`DBAP` at `0x07D4`/`0x07D5` rather than from
`0x07D0`. That is the strongest structural evidence available here that
`0x07C4`-`0x07D7` is a GPU dynamic-boost control block and not battery
state, and it is new relative to §4f.

Two things in the ASL are worth writing down because they are the kind of
detail a re-derivation would otherwise trip over. The `0x73`/`_Q84` path
gates on `DBEN` at `0x07C4` bit 0 and, when it is clear, sets `DBAC = 1`
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
arbitrates. **45,394 of 45,537 instructions re-encode to the exact bytes in
the image (99.69%), with no function in disagreement.** 2,574 of the 2,705
functions have every instruction verified; a further 73 have all but 143
between them. Reproduced unchanged on two SDCC versions (4.5.0 and 4.6.0,
`sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14`).

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
assembler and therefore covers the 2.2% of instructions sdas8051 cannot
express. The first version of that check reported *zero* disagreements while
parsing 30% of each file, because the listings were the old format and the
parser the new one — so it now counts the lines beginning with an address and
fails if the parser does not get all of them. A parser that reads a third of a
file and finds nothing wrong in it is worse than one that reads none, because
it reports a pass.

**What sdas8051 cannot express, counted rather than skipped.** 1,004
instructions (2.2%) use forms it rejects: the bit-addressed `CLR bit`, `SETB
bit`, `CPL bit`, `MOV C,bit`, `MOV bit,C`, `MOVC A,bit`; `CJNE` on a direct
address; `DJNZ A`; and the carry-with-immediate forms. `AJMP` and `ACALL` are
in the same list for a different reason — sdas encodes them differently from
the 8051 manual (at PC `0x8044` the firmware and both decoders agree `81 5D` is
`ajmp 0x845D`; sdas emits `84 5D`). Every one of these is named in the source
rather than filtered silently, because a filter that quietly drops 2% of the
instruction stream turns a measured number into a flattering one.

**The claim this does not make.** That the C recompiles. Keil C51 generated
these bytes; SDCC does not emit Keil's code generation, and no amount of
annotation changes that. The 1:1 property here is that the committed
*disassembly* regenerates the binary, and the readable C sits on top of it
with a checkable correspondence. See `ghidra/README.md`.

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

**The 143 EC instructions sdas8051 cannot encode** — `MOV bit,C`, `CPL bit`,
`CLR bit`, `CJNE` on a direct address, `DJNZ A`, the carry-with-immediate
forms. 0.31% of the instruction stream. Closing them means writing an 8051
encoder here and cross-validating it against sdas8051 on the 45,394
instructions sdas8051 does encode, which is a defensible way to take the 1:1
claim to 100% but is a day's work for 143 instructions, so it is not started.

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
| EC (`ec/decompiled/`, `ec/ghidra/manifest.csv`) | 2,708 rows, 2,708 distinct `(program, addr)`, 0 dups, 0 short rows | 2,708 / 2,708, same | 4 rows, `functions` agrees with both indexes on every row and sums to 2,708; all `mode` = `export-only` |
| BIOS (`bios/ghidra/`) | 955 rows, 955 distinct keys, 0 dups, 0 short rows | 955 / 955, same | 38 rows, `functions` agrees with both indexes on every row and sums to 955; all `mode` = `export-only` |

Reproduce it, one command per component, with no Ghidra and no network:

```
python3 ec/tools/build_ec_decompile.py --work /tmp/x --check
python3 ec/tools/build_ec_decompile.py --work /tmp/x --self-test
python3 bios/tools/bios_extract.py   --work /tmp/x --check
python3 bios/tools/bios_extract.py   --work /tmp/x --self-test
```

Both `--check`s now print the counts they compared (`2708 index row(s), 2708
listing-index row(s), 4 manifest program(s)`, and the same shape for 955/955/38),
and both `--self-test`s assert the totals, so the table above is a fact the
repository re-checks rather than a paragraph somebody wrote once.

**What a clean result means, precisely: the committed files carry no structural
fault today.** It is not evidence that the export has always been correct, it
says nothing about the firmware, and nothing here ran on the machine — this is
entirely committed-file checking, with no register read back and no behaviour
observed.

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
second one beside it. `common` is a grouping, and it is also 753 of the 2,708
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

Deliberately **not** widened to: the annotations CSVs, the BIOS load map, the
raw exporter CSVs, or the per-row reads of those inside the export path. They
have their own guards (evidence citation non-empty, an annotation address that
resolves to an exported function), they are not "the EC and BIOS indexes", and
widening `strict=True` to them is a separate call with its own blast radius.
Named here as a possible follow-up, not silently skipped.
