# Add DMI support for the PCSpecialist / TongFang GM7MG7P

Adds one `uniwill_device_descriptor` and one `uniwill_dmi_table` row. No
existing descriptor, row, field or bit is touched, so every other board in the
table behaves exactly as it does today.

```diff
+static struct uniwill_device_descriptor gm7mg7p_descriptor __initdata = {
+	.features = UNIWILL_FEATURE_FN_LOCK |
+		    UNIWILL_FEATURE_SUPER_KEY |
+		    UNIWILL_FEATURE_BATTERY_CHARGE_MODES |
+		    UNIWILL_FEATURE_CPU_TEMP |
+		    UNIWILL_FEATURE_GPU_TEMP |
+		    UNIWILL_FEATURE_PRIMARY_FAN |
+		    UNIWILL_FEATURE_SECONDARY_FAN |
+		    UNIWILL_FEATURE_NVIDIA_CTGP_CONTROL,
+};
+
+	{
+		.ident = "PCSpecialist GM7MG7P",
+		.matches = {
+			DMI_MATCH(DMI_SYS_VENDOR, "PCSpecialist"),
+			DMI_EXACT_MATCH(DMI_BOARD_NAME, "GM7MG7P"),
+		},
+		.driver_data = &gm7mg7p_descriptor,
+	},
```

## The board

| | |
|---|---|
| `sys_vendor` | `PCSpecialist` |
| `board_vendor` / `board_name` | `TongFang` / `GM7MG7P` |
| Uniwill platform name | `GM5MG7Y` (`FBM-GM5MG7Y0024PCS`) |
| BIOS | AMI `N.1.09A08`, 2021-03-18 |
| CPU / GPU | i7-10875H / RTX 3070 Laptop |
| EC | ITE-based, `ITE EC-V14.6` |
| ACPI HID | `INOU0000` |
| EC `PROJECT_ID` (`0x0740`) | `0x0F` = `PROJECT_ID_CML_GAMING` |

`PROJECT_ID` reads `0x0F` on this machine, which is the project id the driver
already calls `PROJECT_ID_CML_GAMING`. I did not add a `probe` callback to
assert it: `PCSpecialist` + `GM7MG7P` is already an unambiguous match, and
several existing entries take no callback either. If you would rather have the
project id checked at probe time, that is a small follow-up and I am happy to
add it.

## What the eight bits are claimed on

Each is backed by a live test on this machine, one feature at a time, with the
user observing rather than a batch write — an EC is a single shared resource,
and batch writes make cause impossible to attribute.

| bit | register | basis |
|---|---|---|
| `UNIWILL_FEATURE_FN_LOCK` | `0x074E` | F10 changes physical Fn-lock behaviour |
| `UNIWILL_FEATURE_SUPER_KEY` | `0x0768` | the Super key goes dead when locked |
| `UNIWILL_FEATURE_CPU_TEMP` | `0x043E` | cross-checked against `coretemp` |
| `UNIWILL_FEATURE_GPU_TEMP` | `0x044F` | cross-checked against `nvidia-smi` |
| `UNIWILL_FEATURE_PRIMARY_FAN` | `0x0464` | hwmon RPM matches physical sound |
| `UNIWILL_FEATURE_SECONDARY_FAN` | `0x046C` | hwmon RPM matches physical sound |
| `UNIWILL_FEATURE_NVIDIA_CTGP_CONTROL` | `0x0743`-`0x0746` | see below |
| `UNIWILL_FEATURE_BATTERY_CHARGE_MODES` | `0x07A6` | see the caveat below |

### `NVIDIA_CTGP_CONTROL` specifically

The cTGP path is the driver's `ctgp_offset` path: write `0x0744`, enable bit 2
of `0x0743`. Tested live against `nvidia-smi` on 2026-09-23 with the dGPU
`default_limit` at 115 W and `max` at 140 W: setting `0x0743` bit 2 with
`0x0744=0x0A` raised the *enforced* power limit from 120 W to 130 W within
about a second, and clearing it restored 120 W. That is the same arithmetic the
driver implements (enforced = default + DynamicBoost + cTGP offset), so the
path is validated on this board rather than assumed.

One caveat, stated because it is a limit on the claim rather than on the code:
setting `0x0746` (DB max) to 0 did **not** change the static enforced limit, so
`0x0746`'s effect is runtime/opportunistic and is not separately confirmed.
Worth knowing that this driver's cTGP init writes 25 to `0x0746`; this BIOS
caps DynamicBoost at 15 W and the vendor stack writes 5, so that write is
harmless here but the value is not one I would generalise from this machine.

### `BATTERY_CHARGE_MODES` is a taper, not a cap

Claimed deliberately, with the caveat attached so nobody re-derives it the hard
way: this changes the early-exit taper — a floor on the EC's per-cell
charge-voltage derating — and **does not cap charging at a percentage**. Under
both the Trickle and Long_Life profiles, battery traces still show >1 A flowing
at 95% capacity. The EC charges this pack to 16.4 V while the pack requests
17.4 V, so the profile floors that derating. If you want the feature to mean
"the user picked a charge profile", this is it; if you want a hard cap, that is
`UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` and it is a different register, below.

## What is *not* claimed, and why

Seven candidates are left out. Each exclusion is a live result, not a shrug.

- **`BATTERY_CHARGE_LIMIT` — excluded, deliberately.** The paired
  `0x07B9`/`0x07D0` write was run at the physical address Windows' own `ECRW`
  lands on, in five variants, and charging never stopped. Both candidate
  writers in the vendor service are private with no caller. What exists on
  this board is a 16.4 V charge-voltage target the EC owns and the host cannot
  set. Exposing a threshold sysfs that the EC does not honour would be worse
  than not having it. I am not claiming the register does not exist — the
  static scan that says "no references" is "not found by this method", and
  `0x07B0`-`0x07BE` is a known blind spot of it.
- **`LIGHTBAR` — excluded; wrong driver.** Every `0x0748`-`0x074B` register was
  written live with the animation running: every write landed, nothing visible
  changed, and there is no site in either firmware image. This chassis's
  lightbar is a USB HID device (`048D:6005`) on its own ID, so it belongs in
  `ite_8291_lb` — see the related project below — and not here.
- **`KEYBOARD_BACKLIGHT` — excluded.** The Fn+F6/F7 hotkey works, but that is
  the EC hotkey path; the software LED-class path it would expose is a
  separate, untested register. This board's backlight is 4-zone RGB
  (`048D:CE00`, usage page `0xFF12`) and the struct field is a single
  `kbd_led_max_brightness`. I have left `kbd_led_single_color` and
  `kbd_led_max_brightness` at their defaults rather than invent values: nobody
  should read this patch as a judgement that a plausible number is the right
  one. Whether this board needs those fields set at all is a question for
  someone with the hardware.
- **`TOUCHPAD_TOGGLE` — excluded.** Fn+F5 emits no WMI event at all on this
  board, so there is nothing for the driver to report.
- **`AC_AUTO_BOOT` — excluded.** The reference scan finds zero direct sites for
  `0x0726`. That is the whole of the claim, and a static zero is not proof of
  absence: the same scan has a documented blind spot. The real verdict is
  unknown and needs a live behavioural test.
- **`USB_POWERSHARE` — excluded.** The EC bit flips on write and the real-world
  effect is untested. A write the EC reads back correctly is evidence the byte
  is writable, not that the EC acts on it.
- **`USB_C_POWER_PRIORITY` — excluded.** All six reference sites for `0x07CC`
  are in the ITE8850-PD image rather than the EC firmware, so this is "the
  references that made it look present belong to a different program".

## A naming difference worth recording

Upstream defines `0x0786` as `EC_ADDR_FAN_DEFAULT` (`uniwill-acpi.c:254`, the
fan curve) and `0x078E` as `EC_ADDR_FAN_CTRL` (`:265`). The DSDT (`APTC`/`APTN`)
and the vendor stack both call `0x0786` a CPU TCC offset, and those two agree
with each other. The disagreement is between an unused constant and the
DSDT's reading rather than between two live users of the byte: at `5a24248`
neither upstream constant is referenced anywhere in the tree — each occurs
exactly once, at its own `#define` — so the driver has no write path to
`0x0786` and I have not set a fan curve for this board on the strength of a
constant that nothing reads. The fan claims above rest on the RPM observation,
not on the addresses agreeing.

## Cross-reference

`Wer-Wolf/uniwill-laptop` issue #7 reports an XMG `X6AR5xxW` with the same
"threshold write succeeds, charging does not stop" symptom. My finding is that
on this board `0x07B9` is written by Windows and read back, and that the cap
which does exist is a charge-voltage target in the EC rather than a
host-settable percentage. If that is useful for #7, it belongs in that thread
rather than here — I have not commented on it.

## Testing status, stated plainly

**The patched driver has not been compiled, and nothing here has been loaded on
a machine.** What was tested live is the EC behaviour listed above, on the
unpatched driver, one feature at a time. The patch itself is additive and
applies cleanly to `5a24248`:

```sh
git apply --check uniwill-acpi-dm-gm7mg7p.patch
```

Please treat "it builds and the eight bits appear in sysfs" as unverified. The
cTGP and charge-mode claims rest on observations of the EC, not of this patch.

## Related

The [HydroControl](https://github.com/Gumwars/HydroControl) project reached the
same conclusion about the charge limit on a sibling board (Eluktronics
HYDROC-16 G1): `0x07B9` is stored, read back, and never enforced, and they
dropped `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` from their descriptor for the
same reason. Their README also describes the vendor's own "charge limit" as a
16.4 V ceiling rather than a percentage, which matches what was measured here.
That is independent corroboration on different hardware, not a citation for the
finding above, which was measured on this machine.
