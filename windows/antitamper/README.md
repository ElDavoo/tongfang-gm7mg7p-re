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
