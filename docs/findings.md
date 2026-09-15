# Findings

Research log for reverse-engineering charging behaviour, RGB lighting, and
other `uniwill-laptop` driver features on the PCSpecialist/TongFang
`GM7MG7P` (Uniwill `GM5MG7Y`). See `hardware-identity.md` for the board
identity and `../ec/annotations/registers.yaml` for the full register
cross-reference. This document is the narrative; that file is the data.

**This document includes two retractions of earlier conclusions in this same
investigation.** They're kept in, not edited out, because the *reason* each
one was wrong is itself a finding about the limits of the methods used.

## 1. Battery health, honestly

`charge_full` / `charge_full_design` = 2000/4100 mAh, 445 cycles. Genuinely
degraded — not a scaling artifact. This matters because the EC's own `_BIF`/
`_BST` ACPI methods (`evidence/acpi/dsdt.dsl`) deliberately mask early
capacity fade: below 50 cycles they report *design* capacity and rescale the
remaining-capacity reading to match; only at cycle ≥50 do they report the
true measured full-charge capacity. At 445 cycles, the numbers on this
machine are the honest ones.

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
- `ec/tools/scan_refs.py` is unchanged and still correct for what it claims to
  count. `ec/tools/trace_xdata_refs.py` splits a count per image. Every
  live-confirmed register in §2 does have references in the EC image
  (`BAT_CYCLE_COUNT`'s `0x04A6` has some in the PD image too, which changes
  nothing about a register confirmed live), so the §4d validation set is not
  affected by this.

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

## 5. Net status going into the issue tracker

- Charging-cap-on-Linux is an **open problem**, not a closed negative. The
  concrete next experiment (write both `0x07B9` and `0x07D0` together, then
  coulomb-count through the claimed cap exactly as in §4b) is unambiguous
  and cheap to run. §4e adds a second way to run it — the same pair at
  physical `0xFE4107B9`/`0xFE4107D0`, the address Windows' own writes land
  at — which would distinguish "the EC ignores this pair" from "the
  `uniwill-laptop` access path differs from the vendor's."
- Lightbar is a **driver-scope problem, not a hardware problem** — claim
  `048D:6005` for `ite_8291_lb` and test.
- Decrypting the anti-tamper-protected `BatteryProtection2` method bodies
  (`windows/antitamper/`) would settle both open EC questions
  (`0x07D0`'s real role, and whether enforcement is EC-side or
  polling-software-side) without any further live experimentation risk. The
  static route to `0x07D0` is now exhausted on the firmware side: §3b mapped
  every reference the image has and none of them is the EC's.
