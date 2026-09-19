# What the vendor service writes to the EC, from its decrypted source (issue #87)

Issue #87 asks for a command→register table, measured by driving each
MQTT `*/Control` command while `ec_watch.py` runs. Since 2026-09-19 the
service's source is decrypted (`decompiled/v3.1.39.0/`), so half of that
table can be read rather than measured. This file is that half: **static**.
Each row still needs its live confirmation before it becomes a
`confirmed-working` entry in `ec/annotations/registers.yaml`.

Regenerate the raw data with
`windows/tools/ec_callsites.py windows/decompiled/v3.1.39.0/GCUService`. It
produces `decompiled/v3.1.39.0/ec-callsites.csv` (868 sites, each with file,
line, class, method, read/write, address and the value expression) and
`ec-callsites-summary.csv` (per address). `ECSpec` constants are C# `const`,
so every call site carries its address as a literal. Only one helper
(`SingleZone.ReadECRAM/WriteECRAM`) takes the address as a parameter.

## Which classes run on this board

The service picks a class per platform. On the GM7MG7P (read 2026-09-19):

- `MyFanCtrl` (`Fan/Control`) → **`MyFanManager_RamFan1p5`**. `0x078E`
  bit 6 is set (live `0x6C`, "RamFan 1.5 supported"), `CML_Gaming` (`0x0F`)
  is not in `ProjectIdExtensions.CommercialProjectIDs`, and
  `HKLM\SOFTWARE\OEM\GamingCenter2\CustomizeTarget` = 1 (not 42).
- `MyFanTableCtrl` → **`FanTable_Manager1p5`**, by the same test.
- `MySettingCtrl` (`Setting/Control`) → `MySettingManager`, in every branch.
- `BatteryProtection/Control` → `BatteryProtection2`. See
  `docs/findings.md` §4k: the modes write `0x07A6` bits 4-5 only, and the
  `0x07B9`/`0x07D0` writers are never called.

`*_Intel`, `*_QC`, `*_RamFan1p5_CML/_NV/_Normal`, `MyFanManager` and
`FanTable_Manager`/`FanTable_Manager2` are other platforms' variants, and
their rows are left out below. They are still in the CSV, and some write
different addresses for the same feature. For example, `0x0743-0x0747`
holds GPU cTGP/DynamicBoost in `GpuFeatures` but fan L1-L5 PWM in
`MyFanManager_Intel`.

## MQTT topic → handler

From `MyControlCenter/App.cs` `Recieve()`:

| topic | handler |
|---|---|
| `Fan/Control` | `MyFanCtrl.Instance.Receive` → `MyFanManager_RamFan1p5.Receive` |
| `Setting/Control` | `m_MySetting.Recieve` → `MySettingManager` |
| `BatteryProtection/Control` | `BatteryProtection2.Instance.Receive` |
| `System/Control` | `m_MySystem.Receive` |
| `MyRgbLightbar/Control` | `MyRgbLightbarCtrl` (only when `m_sLightbarType == "2"`) |
| `Keyboard/Ctrl`, `HidLightbar/Ctrl` | `RGBKeyboard` / `HIDRGBLightbar` `.OnMqttMessage` (HID; both also touch `0x0782`) |
| `Display/Control`, `Customize/Control`, `ProcessControl/Control`, `Openvino/Control`, `Languages/Control`, `Service/Ctrl`, `Service/Close` | non-EC or service plumbing |

`Fan/Control` actions (`MyFanManager_RamFan1p5.Receive`): `GETSTATUS`,
`DEFAULT`, `FAN_BOOST_ON/OFF`, `OPERATING_GAMING_MODE` /
`OPERATING_OFFICE_MODE` / `OPERATING_TURBO_MODE` (optionally with a
`ProfileIndex`, which selects one of the `M<mode>P<profile>` bundles),
`SET/RESTORE_OPERATING_MODE_DETAIL`, `GET/SET/RESTORE_FAN_SPEED_CURVE_SETTING`,
`RESTORE_FAN_SPEED_CURVE_SETTING_ALL`, `SET_FAN_CONTROL_RESPECTIVE`,
`SET_DEFAULT_NOTIFY_OFF`, `SET_FAN_SAFETY_PROTECT_NOTIFY_OFF`,
`TestModeSwitch`. A power-mode command applies a whole bundle (PLs, TCC
offset, fan mode, GPU settings) through `SetOperatingModeProfileIndexThread`.
Which setters each bundle calls has not been traced.

## EC writes by the classes that run here

| class | method | writes | notes |
|---|---|---|---|
| `MyFanManager_RamFan1p5` | `SetFanMode`, `SetFanBoost` | `0x0751` | fan mode / boost |
| | `SetPL1Value` / `SetPL2Value` / `SetPL4Value` | `0x0783` / `0x0784` / `0x0785` | watts, DSDT `APL1/2/4` |
| | `SetCpuTccOffset` | `0x0786` | |
| | `SetFanSwitchSpeed` | `0x0787` | |
| | `SetCpuVrmCurrentLimit` | `0x0753`, `0x0754` | |
| | `SetGPUdstate`, `SetGPUdstateByGpuMode` | `0x078B` | |
| | `SetFanQuietModeEnable`, `SetOverBoostMode`, `SetPowerLedStatus`, `SetPowerStatus` | `0x07A5` | four features share this byte, bitwise |
| | `SetOverBoostByDynamicTemp` | `0x07A6` | the charge-profile byte, another bit |
| | `SkipOfficeModeSafetyProtect` | `0x07C5` | |
| `FanTable_Manager1p5` | `SetEcFanTable(_Cpu/_Gpu)`, `ClearFanTableAll` | `0x0F00-0x0F5F` | CPU table `0x0F00/10/20`, GPU `0x0F30/40/50` (the same bases `mech-forza-control` names up-temp/down-temp/duty) |
| | `RefreshDefaultFanTable` | `0x0F5D-0x0F5F` | |
| | `SetEcFanControlRespective` | `0x07C5` | |
| `GpuFeatures` | `SetGpuConfigurableTgpFunCtrlEnable`, `SetGpuDynamicBoostEnable`, `SetGpuDynamicBoostFunCtrlEnable` | `0x0743` | enable bits |
| | `SetGpuConfigurableTGPTarget` | `0x0744` | cTGP (issue #8, `NVIDIA_CTGP_CONTROL`) |
| | `SetGpuDynamicBoostTotalProcessingPowerTarget` | `0x0745` | |
| | `SetGpuDynamicBoostMaxinumTGP` | `0x0746` | |
| | `SetGpuWhisperModeMainSwitch` | `0x07C5` | |
| | `SetWhisperModeStatusDisable` | `0x07C6` | |
| `MySettingManager` | `SetFnKey` | `0x074E` | Fn lock |
| | `USB_Charger_ON/OFF` | `0x0767` | USB powershare (issue #7) |
| | `WinKeyLock_Trigger`, `LightBar_Trigger` | `0x0767` | same trigger byte |
| | `TouchpadToggle_ON/OFF`, `UserSetTouchPadLedStatus` | `0x07A6` | the charge-profile byte, another bit |
| | `Write_Support_BYTE` | `0x0766` | |
| `BatteryProtection2` | `SetHealthProtectionHigh/Middle/Low` | `0x07A6` bits 4-5 | the only live battery path |
| | `SetTypeCAdaptorSwitch` | `0x07CC` bit 7 | gated on `0x0742` bit 5, clear on this board |
| | `SetBatteryChargingLimit_Up/Down` | `0x07B9` / `0x07D0` | **never called** |
| `MyEcCtrl` | `Set_APExistToEC` | `0x0741` bit 0 | uniwill-laptop's `ENABLE_MANUAL_CTRL` |
| `MicMuteControl` | `SetLED` | `0x07A6` | yet another bit of `0x07A6` |
| `HIDKeyboard` | `AsyncBrignessToEC` | `0x078C` | keyboard backlight level |
| `MyRgbLightbarManager` | colour/effect setters | `0x0748-0x074B` | EC lightbar path; `docs/findings.md` §3 says this chassis uses HID instead |

The exact bit each method touches is in the value expression column of
`ec-callsites.csv`, and in the method body at the cited line.

## What's left for #87

- **Live confirmation**, one command at a time, with `ec_watch.py` limited to
  `0x0700-0x07FF`. Avoid sweeping the fan-tachometer bytes
  (`0x0464/0x0465/0x046C/0x046D`); see `docs/related-projects.md`, HydroControl
  §4.2.
- **Tracing the `M<mode>P<profile>` bundles**
  (`MyFanManager_RamFan1p5.TransferToName`, `SetOperatingModeProfileIndexThread`)
  to learn which setters each power mode calls, with which values. The
  owner reports three modes: Office, Gaming and Turbo, with Gaming the BIOS
  default. The live PL values seen so far are Turbo 75/75/165 W and Gaming
  60/60/165 W.
