# Anti-tamper / obfuscation notes

`GCUService.exe` (both v3.1.6.0 and v3.9.18.0) ships with a **ConfuserEx-style
anti-tamper mode**: at module load, a `<Module>` static constructor calls
several methods with invisible-Unicode names (`U+206E`, `U+202D`-family
formatting characters, not printable) that P/Invoke `kernel32!VirtualProtect`
and rewrite method bodies in memory before they first execute. On-disk, the
affected method bodies are ciphertext with invalid IL headers — ILSpy reports
things like:

```
//Invalid MethodBodyBlock: Invalid method header: 0xA0
```

or, more severely (seen on `GCUService.MySystem.BatteryProtection` in
v3.1.6.0), a metadata-table read that runs off the end of a heap and throws
before the type can be decompiled at all:

```
System.BadImageFormatException: Read out of bounds.
   at System.Reflection.Internal.MemoryBlock.PeekHeapReference(...)
```

## What's already known without breaking it

Anti-tamper only encrypts **method bodies**, not metadata. So for every
class, still visible on disk and reliable across both app versions:

- Full field/property/method **names and signatures** (types, parameter
  counts) — this is how `windows/decompiled/*/BatteryProtection2.cs` shows
  the complete method list (`SetBatteryChargingLimit_Up(int)`,
  `Battery_Commands` enum with `CHARGING_UP_LIMIT`/`CHARGING_DOWN_LIMIT`,
  etc.) even though every body is encrypted.
- **String literals** — `strings -e l` (UTF-16LE) on the raw `.exe` pulls
  every log-format string, MQTT topic name, and registry path verbatim; this
  is how the `LM_Manager|LB_Init for HidLightbar : ITE solution` string and
  the `HidLightbar/Ctrl` MQTT topics were found, and it works regardless of
  whether the method that contains the string decompiles.
- Classes that are **pure constant containers with no method bodies at
  all** decompile perfectly regardless of anti-tamper, because there's
  nothing to encrypt: `Define/ECSpec.cs`, `Define/BatteryLifeExtension.cs`,
  `Define/BIOS_PROJECT_ID.cs`, and the constant block at the top of
  `LightingModel/ITE_SPEC.cs` (its one real method, the constructor, *is*
  encrypted). This is the reliable way to find address tables and magic
  numbers in this codebase.
- Classes with real logic are **not** reliably spared. `LM_ITE_RGB.cs`
  (107 of ~140 methods encrypted) and `LM_Manager.cs` (18 of ~24) are
  protected about as heavily as `BatteryProtection2.cs` is — there is no
  "lighting is unprotected, battery is protected" split; anti-tamper
  appears to target most non-trivial method bodies fairly uniformly. What
  looked like a lighter touch on the lighting code was really just that
  its class names, enum values, and *method signatures* (e.g.
  `HID_Set_Color_14H(byte Index, byte R, byte G, byte B)`) survive the same
  way BatteryProtection2's do — readable, with an empty/garbled body.

## What the `.appxsym` PDB adds (2026-09-23, issue #131)

The section above is all about `GCUService.exe`. The UWP front end is a
different problem with the same shape, and there is a committed input
that partly answers it **offline, with no Windows machine**:
`vendor/control-center-3.9.18.0/GamingCenter3_Cross.UWP_3.9.18.0_x64.appxsym`
is a zip holding a 150 MB `GamingCenter3_Cross.pdb`.

A PDB carries **names**, and names are exactly what anti-tamper leaves
alone — the same reason the bullet above says field, method and parameter
names survive on disk. The front end's bodies are not readable here, but
its name table is. It is a compressed name heap, so what is in it is
types, methods, local variables and binding paths, not a list of dotted
display names, and the entries worth quoting are exactly what they look
like: `UWP_Refactor.ViewModels.FanViewModel+<ChangeLanguage>d__1197`,
`GpuDynamicBoostSwitch_Checked`, `<GpuDynamicBoostSwitch>i__Field`,
`GpuConfigurableTGPSwitch_UnChecked`, `OverClock_SettingsView_obj1_Bindings`.
`../tools/t1wr_callers.py` counts `FanViewModel` 2230 times,
`OverClock_SettingsView` 624, `UWP_Refactor` 324, `GpuDynamicBoost` 12 and
`GpuConfigurableTGPTarget` 12 — the GPU dynamic-boost feature area,
spelled out, in a module whose bodies this repo cannot read.

The tool counts those names as a **control** rather than as findings: the
same pass that hunts the caller terms prints them in their own section, and
`--self-check` fails outright if they ever all come back zero for this
input, because a zero caller-term result from a name table that was never
reached is worth nothing. A name-level census of an encrypted module still
cannot see a call, only a name that might belong to one. Here the control
is non-zero and the same PDB has no `ACPIDriverDll`, `TempWrite1`, `T1WR`,
`AMAT`, `AMIT` or `0x9C40A4DC` in it at all.

The method that reads it is `../tools/t1wr_callers.py`'s: the archive is
expanded **in memory**, never unpacked under `vendor/`, which is committed
input. If you want the name list itself, `strings` on the extracted PDB is
the one-liner; the tool exists so the *census* is re-runnable rather than
a paste from a terminal nobody can check.

## What's not done

Actually decrypting a method body requires either:

1. **Static**: locating and re-implementing the decrypt routine (the
   `VirtualProtect`-calling methods themselves are *not* obfuscated — they
   can't be, or the loader couldn't bootstrap — so this is tractable: dump
   their IL, work out the XOR/substitution scheme, apply it offline).
2. **Dynamic**: run `GCUService.exe` (needs Windows; it's a Win32 service,
   not UWP-sandboxed) under a debugger, break after the anti-tamper
   constructor has decrypted everything in memory, and dump the
   now-plaintext module. This is the standard approach for ConfuserEx
   anti-tamper and is well documented publicly for the general technique —
   not attempted here.

Approach 2 is the "tag: windows" item in the issue tracker — it needs a
Windows machine (a VM is fine) and is otherwise independent of everything
else in this repo.

**Done for Control Center Service 3.1.39.0 (2026-09-19, issue #3).** No
debugger was needed. The installed service was already running with its
bodies decrypted, so `../tools/dotnet_dump.py` read its image out of the
process and rebuilt it on the shipped file as a template.
`../tools/dotnet_bodies.py` confirms the result: 3759 invalid method-body
headers on disk, 0 in the dump. ConfuserEx also runs an **anti-dump** pass
that wipes the in-memory CLI header and metadata root (the `BSJB` signature
and stream names). The tool restores those from the shipped file, because
anti-tamper never changes metadata. Output:
`../decompiled/v3.1.39.0/` (whole service, `ilspycmd -p`). The same
procedure should work for 3.1.6.0/3.9.18.0 on a machine with those
versions running. It hasn't been tried; they are different builds with
different obfuscation strength (see "Version note").

## Version note

v3.1.6.0's `BatteryProtection2` is *more* obfuscated than v3.9.18.0's (40
vs. 18 undecompilable members) — so this is not a case of "grab the oldest
version to dodge the protection"; the protection predates both, and its
strength doesn't correlate cleanly with app version.

## Corrected claim

An earlier pass at this file asserted the lighting-model classes were
"classes the obfuscator's config didn't target" and decompiled "completely
clean." That was wrong — checked directly (grep for ILSpy's error markers
per file): `LM_ITE_RGB.cs` has 107 broken method bodies out of ~720 lines,
`LM_Manager.cs` has 18 out of ~99. The correct, narrower claim is in the
bullet list above: only bodyless constant classes are reliably clean.
