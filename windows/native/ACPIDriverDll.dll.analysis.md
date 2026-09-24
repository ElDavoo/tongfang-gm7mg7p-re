# ACPIDriverDll.dll — static disassembly

File: `vendor/control-center-3.9.18.0/ACPIDriverDll.dll` (4,108,176 bytes,
PE32+, `IMAGE_SUBSYSTEM_WINDOWS_GUI`, image base `0x180000000`).

Produced on a Linux runner from the committed binary; nothing was loaded
or executed. Companion to
[`ACPIDriver.sys.analysis.md`](ACPIDriver.sys.analysis.md), which has the
kernel side and the DSDT cross-check.

## Reproducing the numbers

```
windows/tools/disasm.sh vendor/control-center-3.9.18.0/ACPIDriverDll.dll /tmp/dll.lst
python3 windows/tools/pe_triage.py \
    vendor/control-center-3.9.18.0/ACPIDriverDll.dll \
    --self-check --listing /tmp/dll.lst
```

```
file              vendor/control-center-3.9.18.0/ACPIDriverDll.dll
sections          6
import-dlls       17
import-symbols    609
exports           19
portio-candidates 21940
portio-confirmed  0
ioctl-constants   25
...
imm 0x07B9        0 operand(s)  ADDR_BATTERY_CHARGE_LIMIT_UP (ECSpec.cs)
imm 0x07D0        1 operand(s)  ADDR_BATTERY_CHARGE_LIMIT_DOWN (ECSpec.cs)
```

The listing is 27 MB and is not committed, for the reason
`windows/decompiled/**/inno/` is not: it regenerates from a committed
input with a committed tool in a few seconds.

## The size is MFC, not vendor code

4 MB for nineteen thin wrappers looks wrong until you read the imports:
`USER32` (223 symbols), `GDI32` (98), `gdiplus`, `UxTheme`, `OLEACC`,
`COMCTL32`, `oledlg`, plus a 1.3 MB `.rsrc`. This is a statically linked
MFC build — the PDB path is
`D:\Source\ControlCenter3\Service\DLL\ACPIDriverDll\x64\Release\ACPIDriverDll.pdb`.
The vendor's own code is the `0x3250`–`0x42D0` range of `.text`, about
4 KB of it. Nothing in this file suggests the DLL draws anything; the UI
framework is linked in and unused, which matters only because it is the
reason the noise floor of every scan below is so high.

## Exports — the API surface a caller binds to

19 exports, all named, all in the vendor's 4 KB range. The IOCTL column is
the `mov $imm,%edx` immediately before the `DeviceIoControl` call inside
each export; see the sibling file for what the kernel driver and then the
BIOS do with each.

| Ord | Export | RVA | IOCTL | ACPI method |
| --- | --- | --- | --- | --- |
| 1 | `ReadCMOS` | `0x003250` | `0x9C40A480` | `RCMS` |
| 14 | `WriteCMOS` | `0x003330` | `0x9C40A484` | `WCMS` |
| 2 | `ReadEC` | `0x003410` | `0x9C40A488` | `ECRR` |
| 15 | `WriteEC` | `0x0034F0` | `0x9C40A48C` | `ECRW` |
| 5 | `ReadMEMB` | `0x0035D0` | `0x9C40A490` | `MMRB` |
| 18 | `WriteMEMB` | `0x0036B0` | `0x9C40A498` | `MMWB` |
| 6 | `ReadPCI` | `0x003790` | `0x9C40A4A0` | `PCRD` |
| 19 | `WritePCI` | `0x003870` | `0x9C40A4A4` | `PCWD` |
| 3 | `ReadIO` | `0x003950` | `0x9C40A4C0` | `IORD` |
| 16 | `WriteIO` | `0x003A30` | `0x9C40A4C4` | `IOWD` |
| 4 | `ReadIndexIO` | `0x003B10` | `0x9C40A4C8` | `RIOP` |
| 17 | `WriteIndexIO` | `0x003BF0` | `0x9C40A4CC` | `WIOP` |
| 8 | `TempRead1` | `0x003CE0` | `0x9C40A4D0` | `T1RD` |
| 9 | `TempRead2` | `0x003DC0` | `0x9C40A4D4` | `T2RD` |
| 10 | `TempRead3` | `0x003EA0` | `0x9C40A4D8` | `T3RD` |
| 11 | `TempWrite1` | `0x003F80` | `0x9C40A4DC` | `T1WR` |
| 12 | `TempWrite2` | `0x004070` | `0x9C40A4E0` | `T2WR` |
| 13 | `TempWrite3` | `0x004160` | `0x9C40A4E4` | `T3WR` |
| 7 | `SMAPCTable` | `0x004230` | `0x9C40A500` | `SMRW` |

The driver implements two more codes, `0x9C40A494` (`MMRD`) and
`0x9C40A49C` (`MMWD`), that nothing here exports — the dword-wide siblings
of `ReadMEMB`/`WriteMEMB`.

**Who calls `TempWrite1` (2026-09-23, issue #131).** Not found by the
census in `../tools/t1wr_callers.py`, which is worth reading as part of
this table: the table above is the export directory, and an export is not a
use. Across every committed Windows input — the decompiled trees, every
vendor binary's string table in ASCII and UTF-16LE, the UWP front end's
`.msixbundle` and its `.appxsym` PDB name table — `TempWrite1` appears
only in this file's own export directory and in the Ghidra decompile of
it. The two closed results are worth naming: `GCUService` 3.1.39.0 is
committed fully decrypted and its only `ACPIDriverDll.dll` P/Invoke is
`SMAPCTable` (`../../decompiled/v3.1.39.0/GCUService/MyECIO/AcpiCtrl.cs:127`),
and the UWP front end reaches the service over MQTT rather than the EC.
What stayed unreadable — the still-encrypted 3.1.6.0/3.9.18.0 bodies, the
installer payloads, and anything in firmware — is listed in that tool's
output and in `../../docs/findings.md` §4o. A caller outside every
committed input is not excluded; a caller inside one is.

## `ReadEC` / `WriteEC` in full

`ReadEC` (`0x180003410`) takes the register address in `ecx` and returns
the byte in `al`:

```
180003428:  mov    %ecx,0x279872(%rip)    # 0x18027cca0   scratch[0] = addr
180003437:  lea    0x22f582(%rip),%rcx    # 0x1802329c0   L"\\.\\ACPIDriver"
180003446:  mov    $0xc0000000,%edx       ; GENERIC_READ|GENERIC_WRITE
18000344b:  movl   $0x3,0x20(%rsp)        ; OPEN_EXISTING
180003453:  lea    0x3(%r9),%r8d          ; FILE_SHARE_READ|FILE_SHARE_WRITE
180003457:  call   *0x1c83e3(%rip)        # CreateFileW
180003460:  cmp    $0xffffffffffffffff,%rax
180003474:  call   *0x1c8a4e(%rip)        # MessageBoxW(0, 0, L"INVALID_HANDLE_VALUE", 0)
1800034a2:  lea    0x2797f7(%rip),%r8     # 0x18027cca0   in and out buffer
1800034a9:  movl   $0x400000,0x28(%rsp)   ; nOutBufferSize
1800034b1:  mov    $0x9c40a488,%edx       ; IOCTL
1800034b6:  mov    $0x400000,%r9d         ; nInBufferSize
1800034c4:  call   *0x1c836e(%rip)        # DeviceIoControl
1800034cd:  call   *0x1c835d(%rip)        # CloseHandle
1800034d3:  movzbl 0x2797c6(%rip),%eax    # 0x18027cca0   return scratch[0]
```

`WriteEC` (`0x1800034F0`) is identical but stores the address at
`scratch+0x00` and the value at `scratch+0x04` before the call — which is
exactly the layout the kernel-side `ECRW` handler reads
(`SystemBuffer[0..1]` as a 16-bit address, `SystemBuffer[4]` as the byte).
The two binaries agree, independently decoded.

Three things in that sequence are the vendor's, not a convention:

- **The device is reopened per call.** `CreateFileW` … `DeviceIoControl` …
  `CloseHandle` runs on every single read and write, with no caching of
  the handle.
- **The declared buffer length is 4 MiB** (`0x400000`) for input and
  output, against a scratch global that is a handful of bytes, and the
  driver only ever reads 2 and writes 1. The IOCTLs are `METHOD_BUFFERED`,
  so the I/O manager allocates from that length; the driver's own handlers
  ignore it. Whether this is merely wasteful or actually fails under
  memory pressure is a runtime question, and not one this analysis can
  answer.
- **Failure is reported with a modal dialog.** The error path calls
  `MessageBoxW(NULL, NULL, L"INVALID_HANDLE_VALUE", 0)` — a UTF-16 string
  at RVA `0x2329E0` — and then returns 0, which for `ReadEC` is
  indistinguishable from a register that genuinely reads 0. That is the
  only use the MFC/USER32 surface gets in the vendor's own code.

## Strings that matter

| RVA | Encoding | Value |
| --- | --- | --- |
| `0x2329C0` | UTF-16LE | `\\.\ACPIDriver` |
| `0x2329E0` | UTF-16LE | `INVALID_HANDLE_VALUE` |
| `0x2428FC` | ASCII | `D:\Source\ControlCenter3\Service\DLL\ACPIDriverDll\x64\Release\ACPIDriverDll.pdb` |

`\\.\ACPIDriver` is the Win32 form of the `\DosDevices\ACPIDriver` symlink
the driver creates, so the two halves of the pair are confirmed to address
each other. Who calls *this* DLL is still not confirmed:
`GCUService.exe` is not committed (`../tools/extract.sh` extracts it from
the installer), so the presumption in `../README.md` that it is the caller
remains a presumption.

## Scan results, and why their raw numbers mean nothing here

- **Port I/O: 21,940 candidate bytes, 0 confirmed.** At 1.8 MB of `.text`
  a bare opcode-byte scan is pure noise. Adjudicated against the listing,
  four bytes decode as `IN`/`OUT` at a real instruction boundary
  (`0x026320`, `0x1A3A7C`, `0x1A3A98`, `0x1BF8BC`) and all four sit in
  4-byte-stride runs of image-relative code pointers — MSVC switch jump
  tables parked inside function bodies, which `.pdata` still covers. Spot
  check at `0x1A3A7C`: the preceding instruction is a `ret`, and the
  dwords there read `0x1A3AEE`, `0x1A3AEB`, … all inside `.text`.
  `pe_triage.py` classifies these itself, as `jump-table entry embedded in
  .text`; the classification is a heuristic, so it is worth saying that
  the stronger evidence is the same as on the driver side — no port-I/O
  routine is imported, and the only hardware access in the vendor's 4 KB
  is `DeviceIoControl`.
- **IOCTL constants: 25 found, 19 real.** The six others are recognisable
  compiler artefacts rather than anything vendor-specific:
  `0xE06D7363` is the MSVC C++ exception magic (`'msc'` + `0xE0`),
  `0xAAAAAAAB` and `0x92492493` are the reciprocal multipliers for
  division by 3 and by 7, and `0x8000FFFF`, `0xF7FFFFFF`, `0xFF7FFFFF` are
  bit masks. They pass the `CTL_CODE` shape test because that test cannot
  be tight enough to exclude every 32-bit constant.
- **`0x07D0`: one operand match, and it is not the EC register.** At
  `0x110598` it is `cmp $0x7d0,%ebx` guarding a `cmove` on a counter
  incremented by the preceding `inc %ebx` — a loop bound of 2000, inside
  MFC. `0x07B9` does not appear as an operand at all. Neither result says
  anything about the charge-limit registers, because this DLL is address
  agnostic by design: the caller passes the address in `ecx`.

## What this does not establish

- Nothing was executed. No handle was opened, no IOCTL was issued, no
  register was read back.
- The caller of these exports is unidentified, for the reason above.
- "No port I/O" is bounded by the method, exactly as in the sibling file:
  a listing scan plus an import scan cannot see access through a computed
  or indirect call, or through code produced at run time.
