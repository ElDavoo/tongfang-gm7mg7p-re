# What the vendor service writes to the EC, from its decrypted source (issue #87)

Issue #87 asks for a command→register table, measured by driving each
MQTT `*/Control` command while `ec_watch.py` runs. Since 2026-09-19 the
service's source is decrypted (`decompiled/v3.1.39.0/`), so half of that
table can be read rather than measured. This file is that half: **static**.
Each row still needs its live confirmation before it becomes a
`confirmed-working` entry in `ec/annotations/registers.yaml`. The exception
is the power-mode section, which also carries a live capture: the vendor's
writes, observed landing (issue #92).

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
What each bundle writes is traced, and confirmed live, under
[Power modes](#power-modes-issue-92) below.

## EC writes by the classes that run here

| class | method | writes | notes |
|---|---|---|---|
| `MyFanManager_RamFan1p5` | `SetFanMode`, `SetFanBoost` | `0x0751` | fan mode / boost |
| | `SetPL1Value` / `SetPL2Value` / `SetPL4Value` | `0x0783` / `0x0784` / `0x0785` | watts, DSDT `APL1/2/4` |
| | `SetCpuTccOffset` | `0x0786` | |
| | `SetFanSwitchSpeed` | `0x0787` | |
| | `SetCpuVrmCurrentLimit` | `0x0753`, `0x0754` | AMD path only; not called on this Intel board |
| | `SetGPUdstate`, `SetGPUdstateByGpuMode` | `0x078B` | private and **never called** in this class |
| | `SetFanQuietModeEnable`, `SetOverBoostMode`, `SetPowerLedStatus`, `SetPowerStatus` | `0x07A5` | four features share this byte, bitwise; all private and **never called** in this class |
| | `SetOverBoostByDynamicTemp` | `0x07A6` | the charge-profile byte, another bit; private and **never called** in this class |
| | `SkipOfficeModeSafetyProtect` | `0x07C5` | private and **never called** in this class |
| `FanTable_Manager1p5` | `SetEcFanTable(_Cpu/_Gpu)`, `ClearFanTableAll` | `0x0F00-0x0F5F` | CPU table `0x0F00/10/20`, GPU `0x0F30/40/50` (the same bases `mech-forza-control` names up-temp/down-temp/duty) |
| | `RefreshDefaultFanTable` | `0x0F5D-0x0F5F` | |
| | `SetEcFanControlRespective` | `0x07C5` bit 7 | split CPU/GPU tables; upstream `SPLIT_TABLES` |
| `MyFanTableCtrl` | `SetFanControlByRamFan1p5` | `0x07C6` bit 2 | cleared before every fan-table write, set after; upstream `ENABLE_UNIVERSAL_FAN_CTRL` |
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
| | `SetBatteryChargingLimit_Up/Down` | `0x07B9` / `0x07D0` | **never called**; and `0x07D0` has no other writer anywhere in the committed Windows inputs — the DSDT's `T1WR 0x1173` branch is the only one, and it writes it as a GPU power byte (`docs/findings.md` §4o). The service's own GPU dynamic-boost writes are the `0x0743`-`0x0746` rows above, a different block |
| `MyEcCtrl` | `Set_APExistToEC` | `0x0741` bit 0 | uniwill-laptop's `ENABLE_MANUAL_CTRL` |
| `MicMuteControl` | `SetLED` | `0x07A6` | yet another bit of `0x07A6` |
| `HIDKeyboard` | `AsyncBrignessToEC` | `0x078C` | keyboard backlight level |
| `MyRgbLightbarManager` | colour/effect setters | `0x0748-0x074B` | EC lightbar path; `docs/findings.md` §3 says this chassis uses HID instead |

The exact bit each method touches is in the value expression column of
`ec-callsites.csv`, and in the method body at the cited line.

## Power modes (issue #92)

Traced from `MyFanManager_RamFan1p5.cs` and the classes it calls (paths below
are relative to `decompiled/v3.1.39.0/GCUService/`, and a bare `:line` means
`MyControlCenter.MyFan/MyFanManager_RamFan1p5.cs`). It was then confirmed
live on 2026-09-23: an AC plug-in, then six power-mode switches through the
Fn hotkey, Office → Gaming → Turbo twice. The raw captures are in
`evidence/ec-watch/2026-09-23-power-mode-cycle-*`,
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt` and
`evidence/mqtt-capture/2026-09-23-power-mode-cycle.*`. ✓ marks a row the
capture matches: the byte changed, or held, as the code predicts, in all six
switches (or at the plug-in, for the AC/battery rows).

### How a mode gets applied

Every entry point ends in `UserSet_Mode1/2/3` (`:613-649`) →
`SetUserProfile(mode)` (`:1712`):

- **UI:** `Fan/Control` `OPERATING_{GAMING,OFFICE,TURBO}_MODE` (`:278-316`)
  → `TransferToName` (`:2641`) → `SetOperatingModeProfileIndex` (`:2522`).
- **Fn hotkey:** the EC raises WMI event `0xB0` (`OSD_FanModeSwitch`,
  `MyControlCenter/WMIEC.cs:127`) → `ModeSwitchChanged` (`:487`) →
  `SetModeSwitchChange` (`:2745`). The *service* picks the next mode. With
  Turbo supported and `AppType` 1 it cycles Office → Gaming → Turbo → Office.
  That's the order the capture shows, and the capture has no `Fan/Control`
  command in it, so the UI played no part. Whether the EC also acts on the
  key by itself was not isolated: the service was running. Upstream
  `uniwill-laptop` maps the same event (`UNIWILL_OSD_PERFORMANCE_MODE_TOGGLE`
  = `0xB0`) to `KEY_F14`.
- **AC ↔ battery, resume, service start:** `PowerModeEvent.Changed`
  (`MyControlCenter/PowerModeEvent.cs:18`) → `PowerStatusChange` (`:476`) →
  `Init` (`:1508`) → `SetUserProfile` for the current mode.

`OperatingMode` 0 = Office, 1 = Gaming, 2 = Turbo (`OperatingModeString`,
`:2413`). `UserSet_Mode1` is Gaming (Turbo when
`HKLM\SOFTWARE\OEM\GamingCenter2\AppType` = 3; it is 1 here), `Mode2` is
Office, `Mode3` is Turbo. Each also stores the mode in the UEFI variable
`PowerMode`, which `syncBiosSettings` (`:1486`) reads back at start.

**The `P1`-`P5` in `M<mode>P<profile>` are user slots, not presets.**
`RefreshMode` (`:1349`) fills all five slots of a mode from the same
defaults. They only diverge once the user edits a slot in the UI, which marks it
`Activated` in `UserPofiles\Mode<m>_Profile<p>.json` next to
`GCUService.exe`. Slot 1 is what runs by default (`MainOption.json`
`*ProfileIndex` = 0). On this machine all 15 files hold the defaults. The
one exception is `Mode1_Profile1`: its GPU `TargetTemperature` is 0, which is
out of range, so `SetGpuTargetTemperature` ignores it.
`Mode1_Profile1` and `Mode3_Profile1` are `Activated` all the same.

### What `SetUserProfile` writes

| what | Office | Gaming | Turbo | code | live |
|---|---|---|---|---|---|
| `0x0751` fan mode | `0xA0` | `0x00` | `0x10` | `SetFanMode` `:1948`, constants; bit 6 is added when Fan Boost is on | ✓ |
| `0x0783/84/85` PL1/PL2/PL4, W | 35/35/165 | 60/60/165 | 75/75/165 | `SetPL*Value` `:2039-2052`; the slot's value, defaulted from EC bytes (next section) | ✓ PL1/PL2 moved, PL4 held `0xA5` |
| same, **on battery** | 0/0/0 | 0/0/0 | 0/0/0 | `:1783-1788` | ✓ `0x00` until the AC plug-in, then 75/75/165 |
| `0x0786` CPU TCC offset | `0x00` | `0x00` | `0x00` | `SetCpuTccOffset` `:2054`; only if the user enables `TccOffsetSwitch` does it write the offset with bit 7 set (DSDT `APTC`:7 + `APTN`:1) | ✓ held `0x00` |
| `0x0787` fan switch speed | `0x00` | `0x00` | `0x00` | `SetFanSwitchSpeedEnabled` `:1936`, off by default | ✓ held `0x00` |
| fan table `0x0F00-0x0F5F` | `M2T1` | `M1T1` | `M3T1` | `FanTable.SetFanTable` → `FanTable_Manager1p5.cs:287/556`; the `DefaultFanTable_*` copy instead while `0x07A5` bit 3 (fan safety protect) is set | ✓ byte for byte, see below |
| `0x07C6` bit 2 | cleared, then set | ← | ← | `MyFanTableCtrl.SetFanControlByRamFan1p5` (`MyControlCenter.MyFan.FanTable/MyFanTableCtrl.cs:116`) brackets the queued table write (`:76-83`) | ✓ low for 1-2 s per switch, back up as the table write ends |
| `0x07C5` bit 7 split tables | 0 | 0 | 0 | `SetEcFanControlRespective` (`FanTable_Manager1p5.cs:1006`), from the table's `FanControlRespective`, false in every default | ✓ held `0x00` |
| `0x0743` cTGP/DB control, on AC | `0x03` | `0x03` | `0x03` | `:1815-1855`, `GpuFeatures.cs:258-305`: bit 0 DB function control, bit 1 DB enable, bit 2 cTGP enable only if the user switches cTGP on | ✓ `0x00` → `0x03` at plug-in, then held |
| `0x0744` cTGP offset, on AC | `0x0A` | `0x0A` | `0x0A` | `GpuFeatures.SetGpuConfigurableTGPTarget` (`:270`): target − BIOS `DefaultTGP` = 125 − 115 W | ✓ held `0x0A` |
| `0x0745` / `0x0746` DB TPP / max, on AC | `0xFF` / 5 | ← | ← | `SetGpuDynamicBoostSwitch` `:1889`; 5 W, or 20 W on "Hero" SKUs (`:994-1001`) | ✓ `0`/`0` → `0xFF`/`5` at plug-in |
| GPU bytes on battery | `0x0743` = 0, `0x0745`/`0x0746` = 0; `0x0744` not written | ← | ← | `:1873-1880` | ✓ in the DC snapshot |
| NVIDIA Whisper Mode (NVAPI, not EC) | on | off | off | `SetGpuWhisperModeSwitchOnOFF` `:1905`, AC only | see below |
| UEFI variables | `PowerMode` = mode; `ICpuCoreVoltageOffsetValue`/`NegativeValue` = 0 | ← | ← | `:621-648`, `SetCpuCoreVoltageOffset` `:2334` | not checked |

"←" means the same as Office. GPU clock offsets (0) and target temperature
go through NVAPI (`GpuFeatures.cs:182-237`), not the EC.

**The AC plug-in has a second writer.** At 17:57:41, ten seconds before the
service's own re-apply, `0x0743` went `0x00` → `0x02` and `0x0745`/`0x0746`
went to `0xFF`/`5` in one sweep. The service's re-apply then set `0x0743`
bit 0 at 17:57:51. That first write came from the UI: it published
`Fan/Control` `SET_OPERATING_MODE_DETAIL` with `GpuDynamicBoostSwitch` = 1
0.18 s earlier, which runs `SetGpuDynamicBoostSwitch(1)` (`:817-837`)
without the bit-0 write. `evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`
shows the same `0x02` → `0x03` step.

**Not called, though defined in this class:** `SetPowerLedStatus`,
`SetFanQuietModeEnable`, `SetOverBoostMode`, `SetPowerStatus` (all `0x07A5`),
`SetOverBoostByDynamicTemp` (`0x07A6` bit 1), `SetGPUdstate*` (`0x078B`) and
`SkipOfficeModeSafetyProtect` (`0x07C5` bit 4). Each is `private`, and the
file's only reference to each is its definition. `SetCpuVrmCurrentLimit`
(`0x0753/0x0754`) runs only on the AMD path. In line with that, `0x07A5`,
`0x078B` and `0x0753/0x0754` never moved in the capture.

**Something else writes `0x07C6` bits 0-1** (DSDT `WMS0`). In every switch
into Office they went 0 → 3 1.1-1.4 s after `0x0751`, and back to 0 on the
way out. That lines up with the NVAPI Whisper Mode call and with
`WhisperMode/Status` flipping `GPU_WhisperModeSwitch`. `GpuFeatures.GetWisperModeStatus`
(`:369`) reads the bits back as the Whisper setting (3 = "quieter").
But no GCUService EC call site sets them: only
`SetWhisperModeStatusDisable` clears them, and it isn't on this path. The
DSDT never writes `WMS0` by name either. The writer is unidentified; the
NVIDIA driver is the obvious candidate, not a checked one.

### Capability and default bytes the service reads

| address | meaning | code | live |
|---|---|---|---|
| `0x049F` bit 1 | Turbo supported (ECSpec `ADDR_BIOS_INFO_3_BYTE`) | `MyEcCtrl.GetTurboModeSupport` (`MyECIO/MyEcCtrl.cs:84`) | `0x0A`: yes |
| `0x0782` bit 4 | default mode: 0 Office, 1 Gaming (upstream `DEFAULT_MODE`) | `GetDefaultMode` `:2143` | `0x9D`: Gaming, matching the owner's "BIOS default is Gaming" |
| `0x0782` bit 1 / bit 2 | Q-key / Office fan-table type (upstream `FAN_QKEY` / `FAN_TABLE_OFFICE_MODE`) | `:2120` / `:2131`, bit 2's getter unused | bit 1 = 0, bit 2 = 1 |
| `0x0730-0x0733` | Gaming PL1, PL2, PL4, D-state | `GetGamingPLDefaultValue` `:2244` | `3C 3C A5 01` |
| `0x0734-0x0737` | Office, same layout | `GetOfficePLDefaultValue` `:2261` | `23 23 A5 01` |
| `0x07A7-0x07AA` | Turbo, same layout. ECSpec calls these `ADDR_BATTERYSAVER_PL*`; this class reads them as Turbo | `GetTurboPLDefaultValue` `:2278` | `4B 4B A5 01` |
| `0x07D8/0x07D9/0x07DA` | TCC offset default, Gaming/Office/Turbo (ECSpec `ADDR_*_TCC_OFFSET_DEFAULT_VALUE`) | `GetTccDefaultValue` `:2308` | `05 05 05` |
| BIOS SmartAPC table (WMI) | UI slider bounds and the cTGP base | `LoadProfileAll` `:1004-1051`, cached in `HKLM\SOFTWARE\OEM\GamingCenter2\SMAPCTable` | PL1/PL2/PL4 max 120/120/165, TCC offset max 5, `DefaultTGP` 115, cTGP range 10, DynamicBoost max 15 |

The D-state bytes are read and stored but never written anywhere.

### Fan tables

`SetEcFanTable` (`FanTable_Manager1p5.cs:556`) writes 16 entries per fan.
The CPU rows are at `0x0F00`/`0x0F10`/`0x0F20` and the GPU rows at
`0x0F30`/`0x0F40`/`0x0F50`. Upstream calls the rows `*_TEMP_END_TABLE`,
`*_TEMP_START_TABLE` and `*_FAN_SPEED_TABLE`. The entries are skewed by one:
`0x0F00+i` gets entry `i+1`'s `UpT`, `0x0F11+i` gets entry `i`'s `DownT`,
and `0x0F20+i` gets entry `i`'s `Duty` × 2 (so
`0xC8` is 100 %). `SetEcFanTable` never writes `0x0F10` or `0x0F40`. Below
are the service's defaults, in the vendor's own field names, as `Fan/Table`
publishes them (°C, and duty in %). Only the used levels are shown:

| mode | fan | `UpT`, levels 1.. | `DownT`, levels 0.. | `Duty`, levels 0.. |
|---|---|---|---|---|
| Office `M2T1` | CPU | 53 57 59 61 63 67 69 71 | 48 50 60 62 64 68 70 72 | 0 30 30 35 45 48 50 55 55 |
| | GPU | 52 53 56 58 60 63 65 67 | 48 50 57 59 61 64 66 68 | 0 30 30 35 45 48 50 55 55 |
| Gaming `M1T1` | CPU | 53 57 59 61 63 65 67 75 80 | 48 50 58 60 62 64 66 69 79 | 0 30 30 35 45 48 50 55 70 85 |
| | GPU | 50 50 52 54 56 58 60 67 70 | 48 48 51 53 55 57 59 62 69 | 0 30 30 35 45 48 50 55 70 85 |
| Turbo `M3T1` | CPU | 53 57 59 61 63 65 67 75 80 83 | 48 50 58 60 62 64 66 69 79 82 | 0 30 30 35 45 48 50 55 70 85 100 |
| | GPU | 50 50 52 54 56 58 60 67 70 73 | 48 48 51 53 55 57 59 62 69 72 | 0 30 30 35 45 48 50 55 70 85 100 |

Unused levels are `255` (step thresholds) and repeat the last duty. So the
three modes share the lower curve. Office stops at 55 %, Gaming at 85 %, and
Turbo adds a 100 % level. `windows/tools/fan_table_replay.py` replays the
captured `0x0F00-0x0F5F` changes backwards from a read-back taken after the
last switch. All seven states it passes through (the starting table and one
per switch) equal the table the service published on `Fan/Table` for that
switch, byte for byte.

**Where the defaults come from.** When the EC version changes, or the local
JSONs are missing or invalid (`FanTable_Init`, `FanTable_Manager1p5.cs:75`),
the service asks the EC for its own table per mode (`RefreshDefaultFanTable`,
`:827`):

1. Clear `0x0741` bit 0.
2. Write the mode code to `0x0F5F`: 1 Turbo, 2 Gaming, 3 Office. Note that
   this is a third numbering.
3. Write `0xFD` to `0x0F5D` and `0xC9` to `0x0F5E`.
4. Poll every 500 ms until the EC has overwritten both (`IsReadyToRead`,
   `:814`), then read the window.
5. Set `0x0741` bit 0 again.

The mailbox is the last three GPU duty slots. That path didn't run in this
capture. The stored defaults (`UserFanTables\DefaultFanTable_*.json`, dated
2025-06-23) are presumably its output, but nobody has compared them against
what the EC returns today.

**The EC side of that handshake is decoded** (issue #99,
`../ec/annotations/manual-fan-ctrl-0751.md` §6). The handler at bank0
`0x888D` checks exactly the magic above, accepts `0x0F5F` only in 1-3, and
copies two 48-byte tables out of CODE into `0x0F00` and `0x0F30`. Its
selector 3 branch is the one that consults `0x0782` bit 2, the Office
fan-table type — so the EC agrees with step 2's numbering, derived here from
firmware rather than from the service's constants. Worth noting against
steps 1 and 5: the EC's PL1/PL2/PL4 clear at `0xA833` fires when `0x0741`
bit 0 is *clear*, which is the state the service deliberately parks the EC
in for this handshake. Whether the two ever overlap depends on when that
routine runs, which is unresolved.

### What this means for a Linux platform profile

- **A power mode is not one register on this board.** The vendor writes
  `0x0751`, PL1/PL2/PL4, a fan table and (on AC) the GPU bytes on every
  switch. **Open:** does the EC derive any of these from `0x0751` alone? For
  example, does it load its own table or PLs when `0x0751` changes? The
  capture can't tell, because the service always wrote everything. That
  decides whether a driver needs to write more than `0x0751`. **Static half
  answered** (issue #99, `../ec/annotations/manual-fan-ctrl-0751.md`): none
  of the 29 EC sites for `0x0751` touches another byte, the per-mode default
  blocks are never read by the EC, and the EC's own PL writer is gated on
  `AP_OEM` (`0x0741`) bit 0 rather than on the mode. So the expected answer
  is "a driver must write the bundle" — still unconfirmed live, and
  `../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` is the unrun
  test that would confirm it.
- A natural mapping is low-power = Office, balanced = Gaming (the EC's
  default mode), performance = Turbo, offered only when `0x049F` bit 1 is
  set. The values a driver would write can all be read back from the EC's
  own default bytes; none has to be hard-coded.
- On battery the vendor writes PL1/PL2/PL4 = 0. What 0 means to the EC
  (no override, or a literal 0 W that something else then replaces) is
  untested. Performance on battery hasn't been measured either.
- Upstream `uniwill-laptop` (`Wer-Wolf/uniwill-laptop` at `5a24248`,
  2026-08-29) defines `0x0751` (`EC_ADDR_MANUAL_FAN_CTRL`: `FAN_MODE_TURBO`
  bit 4, `FAN_MODE_HIGH` bit 5, `FAN_MODE_BOOST` bit 6, `FAN_MODE_USER`
  bit 7), `0x0782`, the PL registers and the fan-table rows. It uses none of
  them, and it has no platform profile. In those names the vendor's Office
  value `0xA0` is `USER | HIGH`, Turbo `0x10` is `TURBO`, and Gaming is 0.
- Upstream names `0x0786` `EC_ADDR_FAN_DEFAULT`, but both the DSDT
  (`APTC`/`APTN`) and this service treat it as the CPU TCC offset, with
  bit 7 as the enable.
- Upstream's cTGP init writes a DynamicBoost offset of 25 W to `0x0746`.
  This machine's BIOS caps DynamicBoost at 15 W, and the vendor writes 5 W
  (relevant to #8).

## What's left for #87

- **Live confirmation** of the other commands, one at a time, with
  `ec_watch.py` limited to `0x0700-0x07FF`. Avoid sweeping the
  fan-tachometer bytes (`0x0464/0x0465/0x046C/0x046D`); see
  `docs/related-projects.md`, HydroControl §4.2.
- The power-mode rows are confirmed (above), through the Fn-key path. The
  UI path (`Fan/Control` `OPERATING_*_MODE`) ends in the same
  `UserSet_Mode*` calls but was not driven live.
