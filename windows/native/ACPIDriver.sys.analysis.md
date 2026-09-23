# ACPIDriver.sys — static disassembly

File: `vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys`
(36,184 bytes, PE32+, `IMAGE_SUBSYSTEM_NATIVE`, image base `0x140000000`).

Everything below was produced on a Linux runner from the committed binary
with the two tools in `../tools/`. No driver was loaded and no IOCTL was
issued; see [the caveat section](#what-this-does-not-establish).

## Reproducing the numbers

```
windows/tools/disasm.sh vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys /tmp/sys.lst
python3 windows/tools/pe_triage.py \
    vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys \
    --self-check --listing /tmp/sys.lst
```

```
file              vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys
sections          7
import-dlls       2
import-symbols    32
exports           0
portio-candidates 66
portio-confirmed  0
ioctl-constants   21
  0x9C40A480
  ... (full list in the IOCTL table below)
  0x9C40A500
imm 0x07B9        0 operand(s)  ADDR_BATTERY_CHARGE_LIMIT_UP (ECSpec.cs)
imm 0x07D0        0 operand(s)  ADDR_BATTERY_CHARGE_LIMIT_DOWN (ECSpec.cs)
```

The listing itself is not committed, for the same reason
`windows/decompiled/**/inno/` is not: it is reproducible from a committed
input by a committed tool, and duplicating it would add 227 KB of
generated text. Excerpts quoted below carry their VA so they can be
checked against a freshly generated listing.

## Answer to the issue's question

**`ACPIDriver.sys` is an ACPI-method-evaluation shim, with no hardware
access of its own that this analysis can find — but the set of methods it
exposes is much wider than "`_DSM` passthrough", and includes a general EC
register read/write pair.**

Each of its 21 IOCTLs marshals its input into an
`ACPI_EVAL_INPUT_BUFFER_COMPLEX`, sets a fixed four-character method name,
and forwards `IOCTL_ACPI_EVAL_METHOD` (`0x0032C004`) down the device stack
to `\Driver\ACPI`. No path was found by which the driver itself touches a
port, PCI config space or a physical address; the *methods* it names do,
inside the BIOS —
and all 21 of them are in the DSDT already committed at
`evidence/acpi/dsdt.dsl`, where `ECRW(addr, val)` resolves to a byte write
at physical `0xFE410000 + addr`. So the charge-limit logic does live in
userspace (issues #3/#4), but the write path it uses is memory-mapped, not
port-mapped and not the `ECMG` named-field list.

On the specific question of port I/O: the byte scan found 66 candidate
`IN`/`OUT` opcode bytes, of which **zero survive adjudication against the
disassembly** — 65 are not instruction starts at all, and the one that
objdump does decode as `in (%dx),%al` (RVA `0x008320`) is the import
hint/name table in `INIT`, where `0xEC` is the ordinal hint for
`IoCreateDevice`. Consistent with that, the import table names no port-I/O
routine: there is no `READ_PORT_UCHAR`, no `WRITE_PORT_UCHAR`, no
`HalGetBusDataByOffset`, and no `HAL.dll` import at all.

## Header and sections

| Section  | RVA        | VSize     | Flags        |
| -------- | ---------- | --------- | ------------ |
| `.text`  | `0x001000` | `0x002A79` | `0x68000020` (code) |
| `.rdata` | `0x004000` | `0x000B9C` | `0x48000040` |
| `.data`  | `0x005000` | `0x0002C8` | `0xC8000040` |
| `.pdata` | `0x006000` | `0x00021C` | `0x48000040` |
| `PAGE`   | `0x007000` | `0x000931` | `0x60000020` (code) |
| `INIT`   | `0x008000` | `0x0004AC` | `0x62000020` (code) |
| `.reloc` | `0x009000` | `0x000024` | `0x42000040` |

Entry point RVA `0x002D80`. The PDB path left in the debug directory is
`E:\Project\Training\Rocky\ACPI Driver call BIOS\Backup\All\20200814\ACPIDriver\x64\Release\ACPIDriver.pdb`
— the vendor's own name for it is "ACPI Driver call BIOS", which is an
accurate description of what the disassembly shows.

## Imports — the load-bearing negative evidence

`ntoskrnl.exe` (28 symbols):

```
KeSetEvent  KeWaitForSingleObject  KeInitializeEvent
ExAllocatePool  ExFreePoolWithTag
MmMapIoSpace  MmUnmapIoSpace
IoAttachDeviceToDeviceStack  IoBuildDeviceIoControlRequest
IofCallDriver  IofCompleteRequest
IoCreateDevice  IoDeleteDevice  IoCreateSymbolicLink  IoDeleteSymbolicLink
IoDetachDevice
IoInitializeRemoveLockEx  IoAcquireRemoveLockEx  IoReleaseRemoveLockEx
IoReleaseRemoveLockAndWaitEx
PoCallDriver  PoStartNextPowerIrp
DbgPrint  DbgPrintEx
RtlInitUnicodeString  RtlCopyUnicodeString  RtlAppendUnicodeToString
RtlCompareUnicodeString
```

`WDFLDR.SYS` (4 symbols): `WdfVersionBind`, `WdfVersionUnbind`,
`WdfVersionBindClass`, `WdfVersionUnbindClass`. These come from the KMDF
stub library (the `FxStubInitTypes` / `FxStubBindClasses` strings are
Microsoft's, not the vendor's); the driver's own dispatch is plain WDM.

This is the import list of a filter driver that builds IRPs and sends them
down a stack. The only entry that looks like direct hardware access is
`MmMapIoSpace`, and it is not used for one — see below.

## `MmMapIoSpace` is PnP resource boilerplate, not an EC path

`MmMapIoSpace` has exactly one call site, at VA `0x140007862`, inside the
resource-parsing helper `0x1400077F4` that `IRP_MN_START_DEVICE` calls:

```
140007832:  cmp    %ebp,0x10(%rsi)        ; for each CM_PARTIAL_RESOURCE_DESCRIPTOR
14000783b:  movzbl (%r15),%ecx            ;   raw descriptor Type
14000783f:  sub    $0x1,%ecx              ;   CmResourceTypePort?
140007844:  movzbl (%rbx),%ecx            ;   translated descriptor Type
14000784c:  cmp    $0x2,%ecx              ;   ...translated to CmResourceTypeMemory?
140007858:  mov    0xc(%rbx),%edx         ;   u.Memory.Length
14000785e:  mov    0x4(%rbx),%rcx         ;   u.Memory.Start
140007862:  call   *-0x3820(%rip)         ;   MmMapIoSpace
140007868:  mov    %rax,(%rdi)            ;   ext->MappedBase
140007871:  movb   $0x1,0x28(%rdi)        ;   ext->IsMapped = TRUE
...
140007877:  movb   $0x0,0x28(%rdi)        ; port resource: keep the raw address
14000788e:  add    $0x14,%rbx             ;   stride 0x14 = sizeof(descriptor)
```

That is the textbook "a port resource the HAL translated into memory space
still has to be mapped" path from the WDM samples. The two
`MmUnmapIoSpace` call sites (`0x140007531`, `0x14000759B`) undo it on
`IRP_MN_REMOVE_DEVICE` and `IRP_MN_SURPRISE_REMOVAL`.

A search of the full listing for other reads of the stored base at
`ext+0x00` turned up none outside those two unmap calls: every one of the
21 IOCTL handlers reaches the hardware through `ext+0x18`, the attached
lower device object, not through `ext+0x00`. So the mapping appears to be
established and never dereferenced. "Appears" is doing real work in that
sentence — see the caveats.

## Device setup

`AddDevice` (`0x140007000`) creates `\Device\ACPIDriver`
(`FILE_DEVICE_UNKNOWN`, extension size `0x60`), symlinks it to
`\DosDevices\ACPIDriver`, attaches to the stack with
`IoAttachDeviceToDeviceStack`, and initialises a remove lock tagged
`'PORT'` (`0x54524F50`). It then calls `0x140001000`, which walks down the
device stack looking for a device object whose `DeviceType` field
(`DEVICE_OBJECT+0x48`) is `0x32` (`FILE_DEVICE_ACPI`) and whose
`DriverObject->DriverName` (`+0x38`) compares equal to the UTF-16 string
`\Driver\ACPI` at RVA `0x003670`, and stores the result at `ext+0x58` —
i.e. at start time it locates the real Windows ACPI driver underneath
itself.

`IRP_MJ_DEVICE_CONTROL` lands in `0x140007130`. `IRP_MJ_CREATE` (0) and
`IRP_MJ_CLOSE` (2) are completed with `STATUS_SUCCESS` by the
`test $0xfd,%al` at `0x1400071A1`; any other major function gets
`STATUS_NOT_IMPLEMENTED`. An unrecognised control code gets
`STATUS_INVALID_PARAMETER` (`0xC000000D`, `0x1400073DC`).

## How one handler works, in full

`ECRR` (`0x14000125C`), the handler for `IOCTL 0x9C40A488`, is
representative and is the one that matters for the charge-limit question:

```
14000125c:  ...                           ; DeviceExtension in rcx, Irp in rdx
140001284:  mov    0x18(%rdx),%rbx        ; rbx = Irp->AssociatedIrp.SystemBuffer
140001292:  mov    %esi,0x50(%rsp)        ; zero the input buffer
14000129b:  movl   $0x52524345,0x54(%rsp) ; MethodName  = 'ECRR'
1400012a3:  mov    $0x32c004,%edx         ; IOCTL_ACPI_EVAL_METHOD
1400012a8:  movl   $0x1,0x5c(%rsp)        ; ArgumentCount = 1
1400012b0:  lea    0x28(%rsi),%r9d        ; input length  = 0x28
1400012b9:  mov    (%rbx),%al
1400012bb:  mov    %al,0x64(%rsp)         ; Argument[0].Argument, low byte
1400012bf:  mov    0x1(%rbx),%al
1400012c2:  mov    %al,0x65(%rsp)         ;   ...and high byte
1400012cb:  movl   $0x14,0x28(%rsp)       ; output length = 0x14
1400012d8:  movl   $0x43696541,0x50(%rsp) ; ACPI_EVAL_INPUT_BUFFER_COMPLEX_SIGNATURE 'CieA'
1400012e0:  call   0x140001e88            ; SendDownStreamIrp
1400012eb:  cmpl   $0x426f6541,0x30(%rsp) ; ACPI_EVAL_OUTPUT_BUFFER_SIGNATURE 'AeoB'
1400012fb:  mov    0x40(%rsp),%al         ; Argument[0].Argument
140001305:  mov    %al,(%rbx)             ; back into SystemBuffer[0]
1400012ff:  movl   $0x4,(%rdi)            ; Irp->IoStatus.Information = 4
```

**The EC register address is 16-bit**, assembled from `SystemBuffer[0]`
(low) and `SystemBuffer[1]` (high) into one `ACPI_METHOD_ARGUMENT`. That
is the same 16-bit address space `ECSpec.cs`'s `0x07B9`/`0x07D0` live in
(`../decompiled/v3.1.6.0/ECSpec.cs`), not the 8-bit offset an ACPI
`OperationRegion(EC0, EmbeddedControl, ...)` would take.

`ECRW` (`0x140002038`) is the same shape with `ArgumentCount = 2`:
`Argument[0]` is the 16-bit address from `SystemBuffer[0..1]`,
`Argument[1]` is the byte value from `SystemBuffer[4]`.

`SendDownStreamIrp` (`0x140001E88`) is a synchronous forwarder:
`KeInitializeEvent(SynchronizationEvent)`,
`IoBuildDeviceIoControlRequest(0x0032C004, ext->LowerDevice, in, inLen,
out, outLen, FALSE, &event, &iosb)`, `IofCallDriver`, and on
`STATUS_PENDING` a `KeWaitForSingleObject`; it returns `iosb.Status`. It
has no other callers and no other control code.

## The complete IOCTL surface

Every code is `CTL_CODE(0x9C40, <function>, METHOD_BUFFERED,
FILE_WRITE_ACCESS)`. The dispatch is the compare chain at
`0x1400071B7`–`0x1400073DA`; the ACPI method name is the `movl` into
`0x54(%rsp)` in each handler. The right-hand column is the
`ACPIDriverDll.dll` export that sends the code (see
[`ACPIDriverDll.dll.analysis.md`](ACPIDriverDll.dll.analysis.md)).

| IOCTL | Fn | Handler | ACPI method | DLL export |
| --- | --- | --- | --- | --- |
| `0x9C40A480` | `0x920` | `0x1400010F8` | `RCMS` | `ReadCMOS` |
| `0x9C40A484` | `0x921` | `0x140001F54` | `WCMS` | `WriteCMOS` |
| `0x9C40A488` | `0x922` | `0x14000125C` | `ECRR` | `ReadEC` |
| `0x9C40A48C` | `0x923` | `0x140002038` | `ECRW` | `WriteEC` |
| `0x9C40A490` | `0x924` | `0x140001508` | `MMRB` | `ReadMEMB` |
| `0x9C40A494` | `0x925` | `0x1400015EC` | `MMRD` | *(none)* |
| `0x9C40A498` | `0x926` | `0x140002308` | `MMWB` | `WriteMEMB` |
| `0x9C40A49C` | `0x927` | `0x1400023FC` | `MMWD` | *(none)* |
| `0x9C40A4A0` | `0x928` | `0x1400016E4` | `PCRD` | `ReadPCI` |
| `0x9C40A4A4` | `0x929` | `0x140002508` | `PCWD` | `WritePCI` |
| `0x9C40A4C0` | `0x930` | `0x140001334` | `IORD` | `ReadIO` |
| `0x9C40A4C4` | `0x931` | `0x140002118` | `IOWD` | `WriteIO` |
| `0x9C40A4C8` | `0x932` | `0x14000142C` | `RIOP` | `ReadIndexIO` |
| `0x9C40A4CC` | `0x933` | `0x140002224` | `WIOP` | `WriteIndexIO` |
| `0x9C40A4D0` | `0x934` | `0x1400017DC` | `T1RD` | `TempRead1` |
| `0x9C40A4D4` | `0x935` | `0x1400018D4` | `T2RD` | `TempRead2` |
| `0x9C40A4D8` | `0x936` | `0x1400019CC` | `T3RD` | `TempRead3` |
| `0x9C40A4DC` | `0x937` | `0x140002614` | `T1WR` | `TempWrite1` |
| `0x9C40A4E0` | `0x938` | `0x140002748` | `T2WR` | `TempWrite2` |
| `0x9C40A4E4` | `0x939` | `0x14000287C` | `T3WR` | `TempWrite3` |
| `0x9C40A500` | `0x940` | `0x140001AC4` | `SMRW` | `SMAPCTable` |

Method name and IOCTL are both decoded constants; the DLL export column is
decoded from that binary's export directory and its own `mov $imm,%edx`.
Nothing in this table is inferred from the mnemonics — and the next
section checks every one of the 21 names against a DSDT that was dumped
from this machine independently of any of this.

## The methods exist, in the DSDT already committed here

All 21 names are `Method`s of `Device (INOU)` — `_HID` `"INOU0000"`, the
same device this driver binds to — in `evidence/acpi/dsdt.dsl`, which was
dumped from this machine before any of this analysis. That is
independent, checkable corroboration for the whole IOCTL table above:

```
$ grep -c 'Method (\(RCMS\|WCMS\|ECRR\|ECRW\|MMRB\|MMRD\|MMWB\|MMWD\|PCRD\|PCWD\|IORD\|IOWD\|RIOP\|WIOP\|T1RD\|T2RD\|T3RD\|T1WR\|T2WR\|T3WR\|SMRW\),' evidence/acpi/dsdt.dsl
21
```

`ECRR`/`ECRW` are three lines each (`dsdt.dsl:50497`):

```asl
Method (ECRR, 1, NotSerialized)
{
    Local0 = (0xFE410000 + Arg0)
    Local1 = MMRW (Local0, Zero, Zero, Zero)
    Return (Local1)
}

Method (ECRW, 2, NotSerialized)
{
    Local0 = (0xFE410000 + Arg0)
    MMRW (Local0, One, Zero, Arg1)
}
```

`MMRW` (`dsdt.dsl:50420`) opens a 4-byte `SystemMemory` `OperationRegion`
at the address it is handed and does an 8/16/32-bit read or write under
the `UWOL` mutex. **So an `ECRW` is a byte write to physical address
`0xFE410000 + <16-bit EC register address>`** — which is why the driver
marshals a 16-bit address, and why nothing in the driver or the DLL needs
a port instruction.

`0xFE410000` is not a new region: the DSDT already maps it as
`OperationRegion (ECMG, SystemMemory, 0xFE410000, 0x00010000)`
(`dsdt.dsl:52193`) — the `ECMG` field list `docs/findings.md` §4c cites.
Its offsets are the EC register addresses used everywhere else in this
repo; two that are independently confirmed on live hardware line up
exactly:

| ECMG field | Offset | `registers.yaml` |
| --- | --- | --- |
| `CPTM, 8` | `0x43E` | `CPU_TEMP`, `confirmed-working` |
| `VGAT, 8` | `0x44F` | `GPU_TEMP`, `confirmed-working` |

This settles what §4c's second signal — "the DSDT's `ECMG` field list steps
over `0x7B9`" — actually meant. The byte at `0x7B9` is inside the mapped
window; it simply has no *named field*. `ECRR`/`ECRW` take an arbitrary
offset into the same window, so ACPI can reach it perfectly well. What the
field list showed was a gap in the BIOS's naming, not a gap in reachability.

Two things that does **not** show, and that this PR does not claim:

- It does not explain the failed live test in §4c. The Linux-side write
  went through `uniwill-laptop` and read back correctly, so that path also
  reaches the byte; the paired UP/DOWN write is still the untested
  variable, and this analysis changes nothing about that.
- It does not establish that a Linux `ioremap`/`/dev/mem` write at
  `0xFE4107B9` behaves like the vendor path. That is a live experiment on
  the physical machine, and no such experiment has been run.

`SMRW` (`0x140001AC4`) is the odd one out: instead of integer arguments it
memcpys `0x80` bytes from the user buffer into a single
`ACPI_METHOD_ARGUMENT` with `Type = 2` (buffer) and `DataLength = 0x80`
(`movl $0x800002,0x60(%rsp)` at `0x140001B41`), then logs the first 21
DWORDs of the result — the `ACPIDriver UserBuffer[0..20]: %x` strings the
issue noticed, and the `ACPIDriver SMAPCTable` string at RVA `0x003A10`.
Note that it still writes `0x28` into the input buffer's `Size` field at
`0x140001B2C`, which does not match a `0x80`-byte argument; I have not
worked out whether the Windows ACPI driver ignores that field or whether
this is a latent bug in the vendor's driver, and nothing here depends on
the answer.

## What this does not establish

- **No behaviour was observed.** Nothing was loaded, no IOCTL was issued,
  no EC register was read or written back. `ECRR`/`ECRW` are read from a
  committed DSDT dump, which says what the BIOS *declares*; what actually
  happens at `0xFE4107B9` when the write lands is a live question.
- **"Zero port-I/O instructions" is a statement about this method.** A
  linear disassembly plus an import scan cannot see port access reached
  through a computed or indirect call, nor code generated at run time. It
  can and does see the absence of any port-I/O *import*, which is the
  stronger half of the argument, but neither half is proof of absence —
  the same discipline `ec/tools/scan_refs.py` documents for its own scan.
- **The `MmMapIoSpace` mapping being unused is a negative from a search.**
  I did not find a dereference of `ext+0x00`; a reader who finds one
  should correct this file in place rather than delete the claim.
- **Which userspace process sends these IOCTLs is still open in general, but
  two rows now have a committed answer.** The table above is the driver's
  *surface*, not a record of traffic. Since 2026-09-23 (issue #131)
  `../tools/t1wr_callers.py` searched every committed Windows input for
  `TempWrite1`, `T1WR` and the `0x9C40A4DC` code, and found the name only
  in `ACPIDriverDll.dll`'s export directory and in the Ghidra decompiles
  of these two files. `GCUService` 3.1.39.0, committed fully decrypted,
  binds only `SMAPCTable` from this DLL
  (`../../decompiled/v3.1.39.0/GCUService/MyECIO/AcpiCtrl.cs:127`). So the
  `T1WR` row has no committed caller, while the `ECRW` row has one: the
  same service, through `AcpiCtrl.Write` →
  `WriteACPI(IOCTL_GPD_ACPI_ECWRITE)` (`AcpiCtrl.cs:212`) → `WriteEC`. Both
  statements are bounded by the same list of unreadable inputs, which
  `../../docs/findings.md` §4o carries. A caller in firmware, or in a
  version of the service that is not committed, remains possible.
- **The DSDT is this machine's, not this BIOS image's.**
  `evidence/acpi/dsdt.dsl` is a live dump; `vendor/bios-1.09/BIOS_1.09.zip`
  has not been unpacked or compared against it.

## What this opens

- A Linux path to the charge-limit pair that needs no vendor driver and no
  ACPI method call: `0xFE4107B9` and `0xFE4107D0` are plain physical
  addresses in a region the BIOS already maps. Whether writing them there
  behaves like the vendor path is exactly the kind of claim that needs the
  physical machine, so the deliverable would be a script and a procedure,
  not a result.
- Whether `ECRW` validates the offset it is handed. The ASL above shows no
  bounds check on `Arg0` before it is added to `0xFE410000`, which is worth
  stating carefully rather than loudly: the window is `0x10000` wide, the
  driver only ever sends a 16-bit value, and what the *platform* does with
  an out-of-window `SystemMemory` access is not something a DSDT listing
  answers.
- `RIOP`/`WIOP` (index/data port pairs) and `PCRD`/`PCWD` (PCI config) are
  a wider hardware-access surface than the EC path, reachable from
  userspace through a symlink; scoping that is a separate question.
- `MMRD`/`MMWD` have IOCTLs and DSDT methods but no `ACPIDriverDll.dll`
  export, so either a caller other than that DLL exists, or they are
  vestigial.
