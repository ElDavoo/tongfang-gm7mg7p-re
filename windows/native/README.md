# ACPIDriver.sys / ACPIDriverDll.dll

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
- `ACPIDriverDll.dll` is the userspace-facing wrapper: it opens
  `\\.\ACPIDriver` and issues the driver's own IOCTLs, confirmed by
  disassembling both sides (below). That `GCUService.exe` is what calls
  *it* is still a presumption — no P/Invoke string links the two, and
  `GCUService.exe` is not committed here.

## What the disassembly found

Both binaries are now disassembled, statically, on Linux. Full write-ups:

- [`ACPIDriver.sys.analysis.md`](ACPIDriver.sys.analysis.md) — the kernel
  driver: sections, imports, PnP/dispatch structure, all 21 IOCTLs, and
  the DSDT cross-check.
- [`ACPIDriverDll.dll.analysis.md`](ACPIDriverDll.dll.analysis.md) — the
  userspace wrapper: 19 exports and the `DeviceIoControl` sequence behind
  each.

The tools are `../tools/pe_triage.py` (stdlib-only PE parser and scanner)
and `../tools/disasm.sh` (objdump/radare2 wrapper); every number quoted in
the write-ups regenerates from them.

**The question this file used to pose** — does the driver forward ACPI
method calls, or does it touch `0x07B9`/`0x07D0` itself via port I/O? —
has an answer, with one correction to how the question was framed.

It forwards. Every one of its 21 IOCTLs builds an
`ACPI_EVAL_INPUT_BUFFER_COMPLEX` and sends `IOCTL_ACPI_EVAL_METHOD`
(`0x0032C004`) down to `\Driver\ACPI`. No port-I/O instruction survives
adjudication against the disassembly, and no port-I/O routine is imported.
So the interesting logic does live in `GCUService.exe` userspace, as
issues #3/#4 assumed.

But "forwards `_DSM` verbatim" was the wrong picture of *what* it
forwards. The methods are a general hardware-access kit —
`ECRR`/`ECRW` (EC register read/write by 16-bit address), `IORD`/`IOWD`,
`RIOP`/`WIOP`, `MMRB`/`MMRD`/`MMWB`/`MMWD`, `PCRD`/`PCWD`, `RCMS`/`WCMS`,
`T1RD`…`T3WR`, `SMRW` — and all 21 are `Method`s of `Device (INOU)`
(`_HID "INOU0000"`) in the DSDT already committed at
`../../evidence/acpi/dsdt.dsl`. `ECRW(addr, val)` there resolves to a byte
write at physical `0xFE410000 + addr`, inside the same region the DSDT
maps as `OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`.

That matters for `../../docs/findings.md` §4c, which listed "the DSDT's
`ECMG` field list steps over `0x7B9`" as evidence the register was
unreachable: the byte is inside the mapped window, it just has no named
field, and `ECRW` takes an arbitrary offset into that window. See §4e
there for what does and does not follow from it.

## Still open

- Which process calls `ACPIDriverDll.dll` — `GCUService.exe` is not
  committed, so the presumption above is still a presumption.
- Whether a Linux write at `0xFE4107B9`/`0xFE4107D0` behaves like the
  vendor path. That needs the physical machine.
- `MMRD`/`MMWD` have IOCTLs and DSDT methods but no DLL export.
