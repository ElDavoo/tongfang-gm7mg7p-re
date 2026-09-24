# Windows userspace — decompilation scaffold

The vendor stack has three layers; only the middle one talks to the EC:

```
GamingCenter3_Cross (UWP app, sandboxed)
        │  MQTT (loopback :13688, plaintext JSON)  ← captured: mqtt-protocol.md, issue #4
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

- **`decompiled/v3.1.39.0/`**: the **whole service, decrypted**. This is
  the version installed on the machine (Control Center Service 3.1.39.0).
  It was dumped from the running process after its anti-tamper had
  decrypted it (`antitamper/README.md`, `tools/dotnet_dump.py`); every
  method body is present. Start here for anything about what the service
  actually does. Its README has the provenance and hashes.
  `vendor-ec-map.md` maps the service's EC writes (issue #87), and
  `docs/findings.md` §4k covers `BatteryProtection2`. The trees below are
  older, partial versions and were written before this one existed.
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
  per-percent-change hook). That hook was once read as evidence the cap is
  enforced by software polling; the 2026-09-18 MQTT capture (issue #4,
  `../docs/findings.md` §4h) shows the per-tick `System/BatteryProtection`
  message is service→UI *telemetry*, not a re-issued command, so the hook is
  not by itself evidence of software enforcement. Whether `GCUService` pokes
  the EC on its own timer is still open and lives inside these still-encrypted
  bodies (issue #3). Note the UI never sends a numeric limit over the wire at
  all — only a mode name — so any number `SetBatteryChargingLimit_Up/Down`
  carries is computed service-side, not received from the UI.
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

## Searching the whole Windows stack at once

The per-file decompiles above are the place to read *what the service
does*. To ask "does anything here call this, anywhere" — a P/Invoke, an
IOCTL constant, an ACPI selector, across all three trees, every vendor
binary's string table and the UWP front end's PDB name table, with a
readability census so the negative can be trusted — use
`tools/t1wr_callers.py`:

```console
python3 windows/tools/t1wr_callers.py             # the census
python3 windows/tools/t1wr_callers.py --verbose   # ...per file and per archive member
python3 windows/tools/t1wr_callers.py --self-check  # assert the numbers the docs quote
```

`decompiled/v3.1.39.0/` is the tree to search for behaviour: it is the
whole service with every method body decrypted. `v3.1.6.0/` and
`v3.9.18.0/` are partial — their signatures and constants are sound, their
method bodies are anti-tamper ciphertext (`antitamper/README.md`) — so a
hit in them is a hit and a miss in them is not a miss. The tool prints
that split as a readability census rather than leaving it to be assumed,
and `docs/findings.md` §4o is a worked negative from it.

## Native driver

`vendor/control-center-3.9.18.0/ACPIDriver/{ACPIDriver.sys,ACPIDriver.inf,acpidriver.cat}`
binds to `ACPI\INOU0000`, the exact device ID `uniwill-laptop` also matches.
Its `.inf` calls it a "System" class filter driver. Both it and
`ACPIDriverDll.dll` are now disassembled (`native/README.md`, and the two
analysis files it links): the driver is an IOCTL-to-ACPI-method-evaluation
shim with no port I/O of its own, so the charge-limit logic does live in
`GCUService.exe` userspace as assumed above. What it forwards, though, is
a general hardware-access kit rather than `_DSM` — 21 ACPI methods
including `ECRR`/`ECRW`, an EC register read/write pair addressed by
16-bit address, which the DSDT implements as a byte access at physical
`0xFE410000 + addr`. `tools/pe_triage.py` and `tools/disasm.sh` regenerate
every number in those write-ups.

## Talking to the EC from Windows

`tools/ecrw.py` is the raw door: `read`, `dump` and a guarded `write` over the
vendor driver's own `ECRR`/`ECRW` IOCTLs, one byte per call. `tools/ec_watch.py`
sweeps a range of it and reports what moved while you do something else in the
vendor UI, with `--mark` rows so the capture says when you acted. Both need the
physical machine, an elevated shell and the vendor driver present — nothing
below has been run from the pipeline that wrote it.

`tools/gpu_block_watch.py` is a third, and it is the narrow one: it watches
`0x07C4`-`0x07D7` and `0x0743`-`0x0746` — the two GPU blocks `docs/findings.md`
§4o leaves in a clobber hazard — **in one sweep, one CSV and one clock**, because
the question is which of the two moves first and two files with two start times
cannot answer it. It has no write path at all, and it prints its per-address
citation table (DSDT field name, current `registers.yaml` `status:`) before it
opens anything, so a capture records what it watched. Its procedure is
`../docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`; that procedure is **written
and not run** — the attribution half of it, which process opened which door, is
the step no cloud agent can take.

## Offline tests

Six of the tools carry offline `unittest` suites, and all of them run from
Linux with no Windows box, no EC and no vendor code:

```sh
bash tools/run-tests.sh            # from the repository root: every suite in the tree
bash tools/run-tests.sh windows/tools
```

`tools/test_manual_fan_ctrl_probe.py` scripts the probe's two arms byte by byte,
`tools/test_ec_watch.py` checks the mark lands in the CSV between the two
change rows, `tools/test_ec_validate.py` checks the `0x0436` capacity arm's
one-directional exact-copy scoring, its full-capacity bound, its CSV, and the
`0x0400-0x045F` page assertion that keeps it off the fan-tach block, and
`tools/test_charge_target_test.py` runs the charge-target tool's three
refusals, the restore in its `finally`, and its CSV columns — the branches
`docs/findings.md` §4m's committed artifacts never exercise, since all three
live runs took the write path. `tools/test_gpu_block_watch.py` checks the
watcher's citation table against the DSDT and `ec/annotations/registers.yaml`
— so a field rename or a status change there turns the suite red rather than
letting the table rot — and pins that a mark reaches the CSV in the same
schema. (`tools/test_system_id_probe.py` covers the `0x0456` probe;
`../tools/README.md` lists it.) All of them work by faking
`ecrw` — the module binds kernel32 at import time and only loads on Windows —
which is also what makes the arms scriptable; the charge-target suite fakes the
`powershell` call behind its WMI line as well. The probe, `ec_watch` and GPU-block
suites use the shared `tools/ecrw_fake.py`; the other three still carry fakes of their
own. `../tools/README.md` is the canonical home for the command, and records
why the runner gives each suite its own interpreter: until those three are
moved onto the shared fake, a single discovery over this directory is
order-dependent (`docs/findings.md` §16).

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
