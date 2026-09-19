# GCUService, Control Center Service 3.1.39.0: decrypted decompile

This is the whole `GCUService.exe` of the Control Center Service installed on
the GM7MG7P itself (`DisplayVersion 3.1.39.0`, installed 2025-05-04; the
executable's own `FileVersion` is `1.0.2.70`). Unlike the `v3.1.6.0/` and
`v3.9.18.0/` trees, **the method bodies here are decrypted**. The
anti-tamper described in `../../antitamper/README.md` was not broken
statically. The module was read out of the running service after its
`<Module>.cctor` had already decrypted it in place: the README's
"approach 2", done without a debugger.

## Provenance

| file | what it is | SHA-256 |
|---|---|---|
| `../../../vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe` | the shipped file, copied from `C:\Program Files\OEM\Control Center\UniwillService\MyControlCenter\` | `178953B081593B69E30A0728C9E5935ED63FA36FF1CE6DBDC654D7548B6E3E20` |
| `GCUService.dumped.exe` | the same file with each section's raw data replaced by the running process's copy (`windows/tools/dotnet_dump.py`, 2026-09-19, service PID 8056) | `14EB87D6BF3D3F28743417F568D11A164D927FED48AA94B910F23EBDE8A4A8B5` |
| `GCUService/` | `ilspycmd 9.1.0.7988 -p -r "<install dir>\MyControlCenter" GCUService.dumped.exe` | |

What the dump changed, as `dotnet_dump.py` reported it:

- section `bp Z` (RVA `0x2000`, `0xAEE0C` bytes, the section holding the
  method bodies): 713491 bytes differ between disk and memory, in 2802 runs;
- `.text` and `.rsrc`: identical to disk once the anti-dump damage below is
  put back;
- restored from the shipped file because the running copy had been wiped
  (ConfuserEx anti-dump; `ConfusedByAttribute.cs` in the tree is the
  obfuscator's own marker): 9 bytes of the CLI header, 27 bytes of the
  metadata root.

What that did to the method bodies (`windows/tools/dotnet_bodies.py`, which
parses every MethodDef's ECMA-335 body header):

| | tiny | fat | invalid | no body |
|---|---|---|---|---|
| shipped `GCUService.exe` | 1191 | 1 | **3759** | 349 |
| `GCUService.dumped.exe` | 2630 | 2321 | **0** | 349 |

Some methods whose on-disk header parses as "tiny" are still ciphertext that
happens to look valid. For example, `BatteryProtection2::SystemEvents_PowerModeChanged`
(RVA `0x3A5BC`) reads on disk as a 22-byte tiny body (header byte `0x5A`), and
in the dump as a 473-byte fat body with a local-variable signature. So the on-disk "valid"
count overstates what was ever readable. `ilspycmd` produced no
`Invalid MethodBodyBlock` or `BadImageFormatException` marker anywhere in the
tree.

## Reproducing

Only the decompile step can be reproduced from committed files alone:

```
ilspycmd -p -o out -r <dir holding the service's dependency DLLs> GCUService.dumped.exe
```

The dependency DLLs (`M2Mqtt.Net.dll`, `Newtonsoft.Json.dll`, ...) only
resolve type names; they are not committed here. Regenerating
`GCUService.dumped.exe` itself needs the service running on Windows:
`dotnet_dump.py --name GCUService.exe --out GCUService.dumped.exe --report`,
elevated.

Reading of what this code does is deliberately not in this file. It goes in
`docs/findings.md`, cited back to paths in this tree.
