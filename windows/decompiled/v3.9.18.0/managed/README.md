# Managed vendor assemblies — ilspycmd 9.1.0.7988

These are the vendor's **managed** (.NET) assemblies from Control Center
3.9.18.0, decompiled whole. They sit beside [`../`](../), which holds the
partially anti-tamper-protected classes the same installer ships, and
beside the service itself at [`../../v3.1.39.0/`](../../v3.1.39.0/), which
is fully decrypted. None of the four here had ever been decompiled.

ilspycmd is the tool for this, and Ghidra is not: Ghidra reads .NET *method
names* out of the metadata and nothing more, reporting success while every
body comes out `halt_baddata()`. See [`../../../ghidra/`](../../../ghidra/) for the
native half and why the split is where it is.

| Assembly | What it is |
|---|---|
| `M2Mqtt.Net/` | the Control Center's MQTT client, 175 methods. The counterpart of [`../../../mqtt-protocol.md`](../../../mqtt-protocol.md) |
| `EnableTray/` | a small tray helper |
| `Colourful/` | a colour/UI helper |
| `SystrayComponent/` | the tray component: `Form1`, `MyRamFan1p5`, `Program`, `CustomizeNumber`, plus a resource class per UI language (thirteen of them) |

`SystrayComponent`'s resource files are translated UI strings in thirteen
languages, which is most of its bulk. They are here so the decompile is
complete and regenerable, not because a string table is a finding.

## Provenance

ilspycmd 9.1.0.7988 — the version `.github/actions/project-setup` pins,
because 9.1 is the last line that installs on .NET 8 — with `-lv CSharp8_0`,
which is the documented workaround for the whole-project (`-p`) crash on the
C#9 record types. Input SHA-256s and the exact commands are in
[`../../../tools/extract.sh`](../../../tools/extract.sh).

These are unedited tool output. Nothing here has been hand-edited, and a
diff means the tool or the input changed.

## Three members did not decompile, and are **not** here

`ilspycmd -p` over `SystrayComponent.exe` fails on exactly three members
with `System.BadImageFormatException: Read out of bounds`, and writes the
**containing file as 0 bytes** rather than partially:

- `SystrayComponent.SystrayApplicationContext.<SendToUWP>d__35.SetStateMachine`
  — one async state machine. Because of it,
  `SystrayApplicationContext.cs` is **absent from this tree**: the whole type
  came out empty, so the type's code was not obtained by this method. A
  whole-file and a `-t SystrayComponent.SystrayApplicationContext` pass
  both reproduce it, and the tool itself suggests updating to ilspycmd 11.x.
- `SystrayComponent.Resources_String.hu_hu` and
  `SystrayComponent.Resources_String.pt_br.get_strTrayBasicMode` — two
  resource members. Their `.cs` files came out 0 bytes and are not committed.

The zero-byte files were deleted rather than committed, because an empty
file in a decompiled tree reads as "this decompiled to nothing" when it
actually means "this failed", and that is the same silent failure
`../../../antitamper/README.md` exists to document. This paragraph is the
record.

Do not read anything into the gaps: `SystrayApplicationContext` is the tray
component's notification path to the UWP app, and the two resource members
are UI strings. Neither is where the fan or EC behaviour lives — that is
`MyRamFan1p5.cs` and `Form1.cs`, both present.
