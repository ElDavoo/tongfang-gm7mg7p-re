# The vendor stack's local MQTT protocol (issue #4)

`GamingCenter3_Cross` (the UWP UI) and `GCUService` do not talk to the EC
directly across the app boundary. They exchange JSON over a local MQTT
broker hosted by `GCUBridge.exe`, and `GCUService` is the only party that
then reaches the hardware. This file documents that wire protocol as
captured on the machine, non-invasively, per issue #4. It is the map; the
battery-specific conclusion lives in `docs/findings.md` §4h.

## How it was captured

`GCUBridge.exe` listens on **TCP 13688** (`0.0.0.0`, so both loopback and
LAN). Capture is a plain packet sniff — nothing is injected, no client is
impersonated, the broker's own auth is never solved:

```
# Npcap with loopback support installed (Wireshark bundle is enough):
dumpcap -i \Device\NPF_Loopback -f "tcp port 13688" -a duration:150 -w cap.pcapng
python windows/tools/mqtt_decode.py cap.pcapng --out evidence/mqtt-capture/session.jsonl
```

Evidence: `evidence/mqtt-capture/2026-09-18-profile-and-connect.pcapng`
(raw) and its decode `…-profile-and-connect.jsonl`. Captured 2026-09-18
while cycling the battery modes in Control Center 3.1.39.0 and restarting
the UI.

## Transport

- MQTT 3.1.1 (`CONNECT` protocol name `MQTT`, level 4). The UI assembly
  also carries `MQIsdp` (3.1), but the observed handshakes are level 4.
- **Plaintext.** No TLS, no payload obfuscation. Every payload is a UTF-8
  JSON object.
- Request/response by topic-pair convention: a controller publishes
  `<Area>/Control` (often `{"Action":"GETSTATUS"}` or a setter), and the
  owner answers on `<Area>/Status` or `<Area>/Info`. There is no MQTT
  request-id; correlation is purely "next message on the paired topic".

## Authentication

`CONNECT` carries a client id, username and password, all three following
one template:

| field | value (observed) |
|---|---|
| client id | `UWPClient_<N>` |
| username | `UWPClient_User_<N>` |
| password | `UWPClient_Pwd888881772688_<N>` |

`<N>` is a small integer that increments across reconnects (3 and 10 were
seen in one session). `888881772688` is a fixed literal embedded in the
password. Other client identities exist as strings in the binaries
(`PluginClient`, `UWPSTDClient`, `UWPADATAClient`, `UWPIntelClient`,
`MyControlCenterUser`, …) and presumably follow the same
`X` / `X_User_<N>` / `X_Pwd888881772688_<N>` shape. A hand-rolled client
using a bare id like `UWPClient` is refused with CONNACK code 2
(identifier rejected) *before* auth, so the `_<N>` suffix and the
credential triplet are both required to attach — the reason the passive
sniff above is the route that works, rather than subscribing directly.

This is local-only IPC with a shared embedded secret; it is an app-identity
gate, not a security boundary, and it is recorded here as protocol fact,
not as a credential to use.

## Topic map (observed 2026-09-18)

Representative payloads; `GET`-family omitted where obvious.

| topic | direction | example payload |
|---|---|---|
| `BatteryProtection/Control` | UI → svc | `{"Action":"HEALTHYMODE"}` / `{"Report":"GET"}` |
| `System/BatteryProtection` | svc → UI | `{"BatteryPowerStatus":1,"BatteryPercent":64,"BatteryTime":-1,"BatteryFullTime":-1,"HealthProtectionStatus":"2","TypeCAdaptorPrioritySwitch":"0","TypeCAdaptorPrioritySupport":false}` |
| `Fan/Control` | UI → svc | `{"Action":"GETSTATUS"}`, `{"Action":"GET_FAN_SPEED_CURVE_SETTING"}` |
| `Fan/Status` | svc → UI | full profile: `OperatingMode`, `CPU_PL1/PL2/PL4`, `GPU_ConfigurableTGP*`, `GPU_DynamicBoost*`, `GPU_WhisperMode*`, … |
| `Fan/Table` | svc → UI | `{"Name":"M3T1","CPU":[{"ID":0,"UpT":0,"DownT":48,"Duty":0},…],"GPU":[…]}` |
| `Setting/Control` | UI → svc | `{"Action":"GETSTATUS"}` |
| `Setting/Status` | svc → UI | `WinKey`, `LightBar`, `UsbCharger`, `DGpu`, `NumPad`, `FnKey`, `TouchpadToggle`, `AcRecoverySwitch_*`, … (string enums) |
| `HidLightbar/Ctrl` | UI → svc | `{"Action":"GETSTATUS"}` |
| `HidLightbar/Status` | svc → UI | `{"solution":"ITE","type":"MEZone_Lighbar","brightNess":"3","powerStatus":"On",…}` |
| `Keyboard/Ctrl` `Keyboard/Status` | both | `{"solution":"ITE","type":"FourZone","ACBrightness":"3","DCBrightness":"0",…}` |
| `MyRgbLightbar/Control` | UI → svc | `{"Action":"GETSTATUS"}` |
| `Customize/Control` `Customize/Info` `Customize/SupportControl` `Customize/SupportInfo` | both | project/feature-support flags (mirror of `HKLM\SOFTWARE\OEM\GamingCenter2\ItemSupport`) |
| `Languages/Control` `Languages/Info` | both | `{"Action":"EnableTray"}`, language list |
| `OSDTpDectect/Language` | UI → svc | `{"OSDTpString":"Touchpad on,Touchpad off"}` |
| `System/Control` | UI → svc | `{"Action":"GetGraphicInfo"}`, `{"Action":"System_OFF"}` |
| `System/HardwareInfo` | svc → UI | `{"GraphicInfo":"…, Intel(R) UHD Graphics, NVIDIA GeForce RTX 3070 Laptop GPU"}` |

`HidLightbar/*` and `Keyboard/*` reporting `"solution":"ITE"` corroborates
the ITE-controller lightbar/keyboard path the `linux/lightbar/` and issue
#5 work is built on — the vendor UI itself names the controller vendor.

## Relevance to the other issues

- **Issue #4** (this file) is answered: the wire format is plaintext JSON
  MQTT, the battery command carries a *mode name and no numeric threshold*
  (`docs/findings.md` §4h), and the per-tick `System/BatteryProtection`
  telemetry carries status, not a re-issued command.
- **Issue #3** is narrowed but not closed: the MQTT layer shows what the UI
  asks for, but the mode → EC-register translation happens inside
  `GCUService`/`BatteryProtection2`, whose bodies are still anti-tamper
  encrypted. What #3 must still recover is that translation and any numeric
  thresholds it holds internally — the wire no longer hides them, the
  service does.
