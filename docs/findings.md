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

**Unexplained, and deliberately not interpreted.** At the instant AC was
connected, `0x0783` and `0x0784` both went `0x00` → `0x4B` (75) and
`0x0785` went `0x00` → `0xA5`. 75 is a suggestive number next to a
charge-threshold question and that is exactly the shape of the §4a
mistake, so it is recorded as an observation and nothing more; the three
bytes did not move when the profile changed, which is evidence against
their being the cap.

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

## 5. Net status going into the issue tracker

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
  holds only `HealthProtectionStatus`, the mode index). A live
  Stationary-charge coulomb-count from 28% is under way to test whether the
  profile stops charging at all (`evidence/battery-traces/2026-09-18-windows-stationary.csv`).
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
