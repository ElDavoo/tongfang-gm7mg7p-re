# Related projects: other people reverse-engineering Uniwill ECs

Other Uniwill/TongFang machines run the same vendor stack (GCUService, the
`INOU0000` ACPI device, ITE 8051 ECs with the same `0x07xx` settings window).
Their findings are worth checking before re-deriving something here. **None
of them is this machine.** Every row below says which EC and board it came
from, and a register meaning only transfers once it has been checked against
*this* image (`ec/firmware/GMxMGxx_11.800`, EC 1.18, ITE EC-V14.6, Intel CML
2020-21) or against this machine live.

Found 2026-09-19. Links were live that day.

## HydroControl: Eluktronics HYDROC-16 G1

<https://github.com/Gumwars/HydroControl>. A Linux replacement for the
Eluktronics Control Center (i9-14900HX / RTX 4090, a much newer Uniwill EC),
built on a patched `uniwill-laptop` plus `acpi_call` → `ECRR`/`ECRW`.
`DESIGN.md` is the part to read.

| their finding | status on this machine |
|---|---|
| `0x07B9` threshold is stored, read back, and **never enforced**. `CHARGE_CTRL_REACHED` (bit 7) never armed over a full cycle. They dropped `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` from their descriptor (DESIGN.md §3.2) | Same result here: `docs/findings.md` §4c/§4f/§4g |
| Neither Trickle nor Long_Life caps a single charge cycle; their pack charged to 4.21 V/cell under both | Ours plateaus at 4.12 V/cell under all three profiles. The reason on *this* EC is the age derating in `ec/annotations/charge-target-derating.md` |
| **Reading the fan-tachometer registers (`0x0464/0x0465/0x046C/0x046D`) through `ECRR` stalled the fans**; the OEM software and `uniwill-laptop` sleep 6 ms after every EC access (DESIGN.md §4.2) | **Relevant to `windows/tools/ec_watch.py`**, which sweeps those addresses without a delay. Not observed to stall fans here, but avoid bulk sweeps under load |
| `0x04xx` is a live read-back window: writes are accepted and silently discarded; `0x07xx` is the settings (write) window | Consistent with everything logged here so far |
| `0x0980-0x098F` reads as sixteen `0xFF`: unmapped host window | Same here for `0x09C0-0x09CF` and `0x0A40-0x0A5F` (2026-09-19) |
| `0x0741` bit 0 is the master switch above the TDP latch | Matches `charge-profile-flow.md` §1 and the vendor's `Set_APExistToEC` |

## mech-forza-control: MECHREVO Wujie 14XA ("Forza 14X", Ryzen 7 8845HS)

<https://github.com/minortex/mech-forza-control> (GPL-3.0). A Python
reimplementation of the GCU control center for a 2024 AMD Uniwill board.
It runs on Linux (`/proc/acpi/call`) and on Windows. Its EC window is at
`0xFED50000`, not this machine's `0xFE410000`. Read `docs/ec-register-map.md`,
`docs/llm/ec-battery-charging-findings.md` and `src/registers.py`.

| their finding | status on this machine |
|---|---|
| `0x0522` = `ADDR_BATTERY_CHARGE_TARGET`, `0x030E` = `ADDR_BATTERY_BASE_VOLTAGE` | Same addresses and meaning here: `0x030E` = 17400 mV requested by the pack, `0x0522` = 16400 mV target (2026-09-19). The routine linking them is decoded in `ec/annotations/charge-target-derating.md` |
| README: "most of users charge limit is limit to about 16.4v, which is below the charge limit voltage by 1V, making the battery can't be charged to full so the battery health drops quickly" | Exactly our numbers. On this EC the 1 V is the 250 mV/cell top derating tier |
| On their EC the profiles cap by percentage: Balanced ~80%, Health ~60% of design; the fuel gauge then learns the capped charge as "full" and needs a full cycle to relearn | The "gauge learns the cap" mechanism is how `charge-target-derating.md` §2 reads the 2021 screenshot. The percentage caps themselves are *their* firmware, not observed here |
| Vendor `BatteryProtection2` also writes UEFI `UniWillVariable` fields `BatteryLimitation`/`ChargeMaximumLimit`/`ChargeMinimumLimit` | Same struct here (`evidence/uefi/2026-09-19-UniWillVariable.txt`). In 3.1.39.0 that code is dead: `docs/findings.md` §4k |
| `0x0773`, `0x077E/0x077F`: a lower-limit shadow and a save handshake (`0xA5 0x78` / `0x55 0xAA`) | Here `0x0773` = `0xFF`, `0x077E/0x077F` = `00 00` (2026-09-19). No evidence yet that this EC has the feature |

## w568w's gists: the Mechrevo charge-limit deadlock and its fix

- <https://gist.github.com/w568w/957976b59906e0ce5d6c13ad342e1593>, "My
  battery charging limit fix for MECHREVO Wujie 14XA". A write-up plus a fix
  script, from a disassembly of EC 2.08/2.12.
- <https://gist.github.com/w568w/b2fc5f9d1f4dff13efe751abec27b396>, the
  discussion thread it links (cross-flashing another OEM's BIOS that has a
  Stored-Limit menu).
- <https://github.com/minortex/GX4HRXL-firmware>, the EC images it
  disassembled.

Their EC's logic, once a second: if neither `0x07C3` nor `0x0770` equals 4
or 5, fall back to a host-unwritable Stored Limit at `0x087F`. If that is
0 or above 100, disable charge control and **never read the live limit at
`0x07B9`**. Their fix writes `0x07B9`, pokes `0x07C3 = 4` for about 2 s so
the EC copies the limit to `0x087F` and sets the gate `0x0742` bit 2, then
restores `0x07C3`.

**Does it apply here? Not by any evidence found, and it is not safe to try
blind.** In this image (checked 2026-09-19 with `ec/tools/trace_xdata_refs.py`):

- `0x087F` has no direct reference. Neither does `0x07B9`, a known blind spot.
- `0x07C3` is compared against 1, 2, 6, 7, 0x0A and 0x0E; `0x0770` against
  4, 6, 7, 8, 9, 0x0A, 0x0C, 0x0E and 0x18. Both look like a board/state
  selector, not a charge-limit gate.
- The only write to `0x0742` sets bit 1, never bit 2.

Live values: `0x0742` = `0x02`, `0x07C3` = `0x00`, `0x0770` = `0xFF`.
Writing `0x07C3 = 4` would change a value this EC branches on in eight
places, for no demonstrated benefit.

## Upstream drivers (already in use here)

- [`Wer-Wolf/uniwill-laptop`](https://github.com/Wer-Wolf/uniwill-laptop):
  the target of this repository's eventual upstream patch (issue #10). Its
  issue #7 is the "charge limit validated only on Intel Project boards"
  statement that `docs/findings.md` §4c discusses.
- [`tuxedo-drivers`](https://gitlab.com/tuxedocomputers/development/packages/tuxedo-drivers):
  the `0x07A6` profile mapping (`0 => high capacity, 1 => balanced,
  2 => stationary`) and `ite_8291_lb` (issue #5).
