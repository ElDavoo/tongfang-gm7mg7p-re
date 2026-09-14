# ACPIDriver.sys / ACPIDriverDll.dll — not yet reverse engineered

Files: `vendor/control-center-3.9.18.0/ACPIDriver/{ACPIDriver.sys,ACPIDriver.inf,acpidriver.cat}`
and `vendor/control-center-3.9.18.0/ACPIDriverDll.dll`.

## What's known from static triage only (`strings`, `.inf` parsing)

- Binds to `ACPI\INOU0000` — the **same ACPI HID** `uniwill-laptop` matches
  in Linux (`vendor/.../ACPIDriver.inf`: `%*INOU0000.DeviceDesc% =
  ACPIDriver_Inst,ACPI\INOU0000`).
- `.inf` `Class=System`, i.e. a generic WDM/KMDF driver, not a bus/HID class
  driver.
- Log strings suggest a thin ACPI-method-evaluation shim: `ACPIDriver
  SendDownStreamIrp`, `ACPI_EVAL_OUTPUT_BUFFER_SIGNATURE`,
  `ACPIDriver UserBuffer[0..20]: %x` (a 21-DWORD IOCTL input/output buffer),
  `\Device\ACPIDriver`, `\DosDevices\ACPIDriver`, `\Driver\ACPI` (parent).
  Copyright string: `TONGFANG HONGKONG LIMITE[D]`.
- `ACPIDriverDll.dll` is presumably the userspace-facing wrapper
  `GCUService.exe` calls into (`DeviceIoControl` against
  `\\.\ACPIDriver`) rather than `GCUService` opening the device directly —
  not confirmed, no direct P/Invoke string found yet linking the two.

## What's not done

No actual disassembly. This is a native x86-64 PE (not .NET), so it needs
Ghidra/IDA/radare2 rather than ilspycmd. Given the userspace evidence
already gathered (`../decompiled/`, `../antitamper/`), the specific question
worth answering here is narrow: **does `ACPIDriver.sys` do anything besides
forward `_DSM`/custom ACPI method calls verbatim**, or does it also touch
`0x07B9`/`0x07D0` directly via port I/O rather than through ACPI? If it's
purely a passthrough, this file stops being interesting and the real logic
is confirmed to live in `GCUService.exe` (see `../README.md`).
