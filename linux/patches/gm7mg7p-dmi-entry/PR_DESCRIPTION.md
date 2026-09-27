# DMI entry: TongFang GM7MG7P (retail: PCSpecialist), PROJECT_ID 0x0F

Adds one row to the DMI match table for the TongFang `GM7MG7P` / `GM5MG7Y`
platform, sold retail by PCSpecialist as a `GM7MG7P` and re-badged by TongFang
as `GM5MG7Y` (`FBM-GM5MG7Y0024PCS`). Nothing else in the table is touched.

| | |
|---|---|
| `sys_vendor` | `PCSpecialist` |
| `board_vendor` / `board_name` | `TongFang` / `GM7MG7P` |
| EC `PROJECT_ID` (`0x0740`) | `0x0F` = `PROJECT_ID_CML_GAMING` |
| ACPI HID | `INOU0000` (same as the boards already in the table) |
| BIOS | AMI `N.1.09A08`, 2021-03-18 |

The `0x0F` is read off the machine, not inferred: EC `0x0740` returns `0x0F`,
and it agrees with the vendor's own `ITE_SPEC.EC_PROJECT_CML_Gaming` constant.
The table match is therefore the same shape as the existing CML entries.

## Features

One bit: `UNIWILL_FEATURE_BATTERY_CHARGE_MODES` (`charge_types`, EC `0x07A6`).

**Please read this before merging the feature bit, because it is easy to
misread as more than it is.** The charge modes do not cap charging. Writing
`00`/`01`/`10` (High Capacity / Balanced / Stationary) is accepted and the EC
picks a different early-exit current limit, but coulomb-counted traces with the
battery at 95% still show >1 A flowing under both Trickle and Long_Life. It is
a *taper*, not a limit, and a user switching to "Stationary" should not expect
charging to stop. This is stated in the driver's own interface expectations
and is why nothing here depends on it stopping.

## What is deliberately **not** claimed

Each of these was checked and left out. A short version, since the point of a
descriptor is to be able to trust what is in it:

- **`UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` is not claimed.** Two independent
  reasons. The threshold write is not the cap the vendor applies — what the
  vendor enforces is a charge-*voltage* target of 16.4 V, derated with age,
  and that byte is owned by the EC, so the host cannot set it. And writing the
  upper threshold together with the matching lower one — the pair the Windows
  service actually writes — was tried live in five variants and did not stop
  charging. This is not "we didn't get to it"; there is no cap behind the bit
  for it to expose.
- **The lightbar is not claimed, and is not this driver's to claim.** Writing
  the EC lightbar registers has no observable effect; the bar keeps animating
  its own pattern regardless. The real lightbar is a separate USB HID device
  (`048D:6005`, usage page `0xFF03`), so the EC path is the wrong mechanism on
  this chassis. It belongs to a different driver.
- **`AC_AUTO_BOOT`, `USB_POWERSHARE`, `USB_C_POWER_PRIORITY` and
  `NVIDIA_CTGP_CONTROL` are not claimed** — not tested on this board. A write
  being accepted and the EC bit flipping is not evidence the EC acts on it.
- **The keyboard brightness bit is not claimed**, though the hotkey works. The
  Fn+F6/F7 hotkeys are confirmed, but that is a WMI event, not the sysfs
  brightness interface. This board's backlight is a 4-zone RGB device
  (`048D:CE00`), and a single-brightness interface may well drive it wrongly.
  This is the one item here worth a maintainer's opinion: if the driver is
  known to handle these, adding the bit is a one-line change.

## Verification

What was checked, and what was not, stated plainly:

- The EC register statuses behind the claims above were established by
  reading registers on the machine and, for the temperature features, by
  cross-checking against `coretemp` and `nvidia-smi`.
- **The patched driver has not been loaded and the interface exercised on
  this machine.** No stage of the work that produced this had hardware access
  for a live run of the driver itself. The evidence is at the register level
  and at the vendor-service level, not at the driver's sysfs surface.
- A load-time check that the row matches is the obvious first thing to do
  before or alongside merging.

## Related, for whoever searches

Upstream issue #7 reports the same symptom on a different board (XMG
`X6AR5xxW`): the threshold write succeeds, readback matches, and charging does
not stop. What was found here is consistent with that report rather than
disagreeing with it — on this firmware the byte Windows writes is a
charge-voltage target the EC owns, not a host-writable percentage threshold. If
that holds for `X6AR5xxW` too it would be the missing piece there. It is worth
reading before anyone tries the same thing again on that board.

---

<!--
NOTES FOR THE SUBMITTER -- delete everything in this block before pasting.

The patch file itself is not in this repository yet, and that is the one thing
standing between this body and a submittable PR. It has to be cut against
uniwill-acpi.c at the pinned rev, and the driver source is not vendored here,
so the bit names and the table row syntax could not be read off the real file
rather than from memory. Inventing them is the one failure mode this whole
artifact is built to avoid, so nothing was invented.

linux/patches/gm7mg7p-dmi-entry/README.md has the commands, and
tools/check_dmi_descriptor.py --check will go green the moment the patch
lands. Run it before submitting.

One judgement call to review rather than inherit: this entry claims ONE
feature bit, because only one upstream bit spelling is recoverable from a
committed file in the source repository (the two charge ones, quoted in
linux/patches/README.md). Every other feature here is confirmed working at the
register level and is blocked purely on not being able to spell the bit. Once
the source is fetched, most of them become one-cell edits in feature-map.csv
and the descriptor grows. Do not read the one bit as a judgement that the rest
are unsupported.

Nothing in this repository has opened anything on Wer-Wolf/uniwill-laptop, and
nothing should without a human deciding to.
-->
