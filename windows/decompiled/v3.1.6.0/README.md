# v3.1.6.0 — what is in the oldest Control Center, and what can be done with it

`vendor/control-center-3.1.6.0/` is committed and had never been extracted.
This is what `innoextract -s -e` finds in it, measured 2026-09-23, and the
part of it that is reachable from a machine with no Windows on it.

The two `.cs` files beside this note (`BatteryProtection2.cs`, `ECSpec.cs`)
are the whole of what had been decompiled from this version. The rest of the
inventory is below.

## The native EC-facing stack did not change between the two versions

Every vendor binary that talks to the EC or to the firmware is **byte-identical**
between Control Center 3.1.6.0 and 3.9.18.0:

| binary | size | SHA-256 (first 16) | 3.9.18.0 |
|---|---|---|---|
| `ACPIDriver.sys` | 36,184 | `9749f1c57e37f4eb` | identical |
| `ACPIDriverDll.dll` | 4,108,176 | `345cff34994351e1` | identical |
| `UEFI_Firmware.dll` | 125,840 | `7fdff34f5411e919` | identical |

That is worth stating plainly because it bounds a question people ask: if the
machine behaves differently under the two versions, **the difference is not in
the driver, the driver wrapper, or the firmware-bridge library.** Those three
are the same binary. It is in the managed service, or in a component not in
this set — which is where to look next, and where not to.

## Four native binaries here are not in the Ghidra project

| binary | size | what |
|---|---|---|
| `NVControlSetting.dll` | 2,766,736 | NVIDIA control settings. The only NVID**A** control surface in either version, and therefore the most likely place a GPU overclocking or power-limit behaviour lives |
| `GPUInfoDLL.dll` | 2,551,696 | GPU model/identity queries |
| `DiskInfo64.dll` | 3,184,528 | disk identity; SMART-adjacent |
| `devcon.exe` | 91,064 | Microsoft's device-console utility, bundled so a helper can install `ACPIDriver.sys` without it |

They are plain x86-64 PE images with no anti-tamper, so they decompile with
the same `windows/tools/decompile_native.py` path as the 3.9.18.0 set — add the
row to `windows/ghidra/native-binaries.csv` and run the tool. They are not
added here because the Windows export is already the slowest thing in this
repository (the 27 MB `GamingCenter3_Cross.dll` alone), and adding four more
binaries to a batch that has not yet finished once is not a decision to make
quietly.

`shell32.dll` in `app/CreateShortcut/` is Microsoft's own, bundled for a
native helper. It is not vendor code and is not a target.

## The service itself is protected, and cannot be unpacked from here

`GCUService.exe` (1,496,440 bytes) is .NET and anti-tamper packed, same as the
3.9.18.0 one. `ilspycmd 9.1.0.7988 -lv CSharp8_0 -p` over it produces 80
files and 4,463 lines, and **every method body is empty**:

```csharp
public static int LimitToRange(this int value, int inclusiveMinimum, int inclusiveMaximum)
{
    //Invalid MethodBodyBlock: Invalid method header: 0xC0
}
```

So the type structure, namespaces and member signatures come out, and no
behaviour does. One type fails outright rather than coming out empty —
`LightingModel/LM_ITE_RGB.cs`, `System.BadImageFormatException: Read out of
bounds` — the same ilspycmd 9.1 defect that takes `SystrayComponent` three
members in the 3.9.18.0 set
([`../v3.9.18.0/managed/README.md`](../v3.9.18.0/managed/README.md)).

**Getting the bodies needs a Windows machine and is not something this
repository can do.** `windows/tools/dotnet_dump.py` reads the decrypted image
out of a *running* process's address space; there is no static route to it. The
2 `.cs` files that are here were produced that way, on a machine that had one.
The deliverable for anyone with the hardware is the command, which
`dotnet_dump.py --help` prints, plus the decompile; the result is a decrypted
`GCUService.exe` for 3.1.6.0 to diff against the 3.9.18.0 one, which is what
would actually answer "what changed between the versions" now that the native
half is known to be identical.

## Provenance

- `vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe`, SHA-256
  recorded by `innoextract`; the input is committed and not regenerated.
- `innoextract 1.9` (from nixpkgs), `-s -e`.
- `ilspycmd 9.1.0.7988`, `-lv CSharp8_0`, whole-project (`-p`).
- Managed/native classification by `is_managed_assembly()` in
  `../../tools/decompile_native.py`, not by a header heuristic.

Nothing here is committed to the repository except this note. The extraction
output is scratch, as it is for the other versions — `../../tools/extract.sh`
regenerates it, and `vendor/` is the committed input.
