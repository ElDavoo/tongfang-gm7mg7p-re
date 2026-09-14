# Windows userspace — decompilation scaffold

The vendor stack has three layers; only the middle one talks to the EC:

```
GamingCenter3_Cross (UWP app, sandboxed)
        │  MQTT (loopback, "GCU2" broker)         ← evidence/traces would help here
        ▼
GCUService.exe (Win32 service, full trust)         ← EC/HID access lives here
        │  DeviceIoControl
        ▼
ACPIDriver.sys (kernel driver, ACPI\INOU0000)       ← same ACPI HID Linux uniwill-laptop binds to
```

`vendor/control-center-3.9.18.0/` and `vendor/control-center-3.1.6.0/` hold
the installers as shipped by PCSpecialist/TongFang. `tools/extract.sh`
reproduces the extraction from those into plain PE/.NET assemblies.
`decompiled/` holds the ilspycmd output already produced (see below);
`antitamper/` documents why some of it is incomplete and how to go further.

## Decompiled sources

- **`decompiled/v3.1.6.0/ECSpec.cs`** — the single most useful
  file in this repo for the charge-limit question. Fully clean decompile,
  gives the complete EC address table the Windows service uses, including
  `ADDR_BATTERY_CHARGE_LIMIT_UP = 0x07B9` and `ADDR_BATTERY_CHARGE_LIMIT_DOWN
  = 0x07D0` — the pair `uniwill-laptop` only half-implements (see
  `../docs/findings.md`).
- **`decompiled/v3.1.6.0/BatteryProtection2.cs`** /
  **`decompiled/v3.9.18.0/BatteryProtection2.cs`** — same class,
  two app versions, both partially anti-tamper protected (see
  `antitamper/README.md`). Method *signatures* survive intact even where
  bodies don't: `Battery_Commands` enum (`GET`, `CHARGING_UP_LIMIT`,
  `CHARGING_DOWN_LIMIT`, `RECOVERY`, `TYPE_C_ADAPTOR_PRIORITY_SWITCH_ON/OFF`),
  `SetBatteryChargingLimit_Up/Down(int)`, `Battry_LifePercentChange` (a
  per-percent-change hook — evidence the cap is enforced by software polling
  capacity changes, not purely in EC firmware).
- **`decompiled/v3.9.18.0/LightingModel/{ITE_SPEC,LM_ITE_RGB,LM_Manager}.cs`**
  — like `BatteryProtection2`, these are anti-tamper protected (see
  `antitamper/README.md`) and most method *bodies* don't decompile. What
  does survive, reliably, is constants (no method body = nothing to
  encrypt) and method *signatures*. That's still enough to confirm the
  lightbar is an ITE 8291 HID device (`VID=0x048D`,
  `USAGE_PAGE_Ligbar=0xFF03`) rather than an EC-mapped peripheral:
  `ITE_SPEC.cs`'s constant block (`EC_PROJECT_CML_Gaming = 15` matches this
  board's live `PROJECT_ID`; `EC_RGBKBBKL_LEVEL_DOWN/UP = 177/178` matches
  the WMI hotkey codes observed live) plus the HID command set visible from
  `LM_ITE_RGB.cs` method signatures alone (`HID_Set_Effect_Type_08H`,
  `HID_Set_Color_14H(byte Index, byte R, byte G, byte B)`, etc. — standard
  ITE 8291 protocol, same family `tuxedo-drivers`' `ite_8291_lb` already
  implements for other PIDs). The `LM_Manager|LB_Init for HidLightbar : ITE
  solution` log string that first pointed at this was pulled with
  `strings -e l` on the raw `.exe`, independent of decompilation working at
  all — see `antitamper/README.md`.
- **`decompiled/v3.9.18.0/Define/{BatteryLifeExtension,BIOS_PROJECT_ID,ECSpec}.cs`**
  — small supporting constant classes, all clean.

## Native driver

`vendor/control-center-3.9.18.0/ACPIDriver/{ACPIDriver.sys,ACPIDriver.inf,acpidriver.cat}`
binds to `ACPI\INOU0000`, the exact device ID `uniwill-laptop` also matches.
Its `.inf` calls it a "System" class filter driver; log strings (`ACPIDriver
SendDownStreamIrp`, `ACPI_EVAL_OUTPUT_BUFFER_SIGNATURE`) indicate it's a thin
IOCTL-to-ACPI-method-evaluation shim, not where the charge-limit logic
lives — that's consistent with the logic living in `GCUService.exe`
(userspace) as found above. Not yet actually disassembled (it's a native PE,
needs Ghidra/IDA/r2, not ilspycmd); see `native/README.md`.

## What's proven vs. what needs a Windows box

Everything above was done **without running any vendor code** — pure static
analysis of files already on this Linux machine. The next real step,
decrypting the anti-tamper-protected method bodies to see the *actual*
charge-limit write sequence and enforcement logic, needs either deep offline
work on the encryption scheme or running `GCUService.exe` under a debugger
on Windows (a VM is enough — it's a plain Win32 service, not requiring the
UWP sandbox or real hardware for static bytes to fall out in memory, though
confirming it *behaves* correctly obviously does need the real EC). See the
issue tracker, tagged `windows`.
