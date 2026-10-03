# Every writer of `UniWillVariable`, and which of them can explain offset 0x60

Issue #116 asked three things: list every writer of the `UniWillVariable` UEFI
variable in the BIOS and in the Windows service, say which of them writes
offset 0x60 (`MemoryOverClockSupport`), and report which writer(s) can produce
the observed block — 0x60 reading 0 with the 76 reserved bytes all zero — with
*established* kept apart from *possible*.

The enumeration is below. The verdict is a correction of the hypothesis the
issue was filed with, and the correction is in the issue's favour: the
hypothesis does not survive contact with the committed dumps.

**Nothing here is a live observation.** There is no hardware and no Windows
machine on this pipeline. Every byte claim is read out of a committed file, and
`tools/check_uniwill_writers.py` re-derives them; the write-up says which is
which.

## Two corrections, before the table

**1. The create-if-missing path is conditional, so "the BIOS created it as 1"
is not established for this machine.** In `OemUniWillVariableDxe`, the routine
`FUN_00000454` issues `GetVariable` (gRT slot `+0x48`) for `UniWillVariable` at
`0x49B` with size `0xB4` and attributes 7. The whole initialisation block —
including the 76-byte fill and the `SetVariable` at `0x609` — sits below the
`jns 0x60F` at `0x4CA`, which is the taken path when that status is
non-negative. It runs **only when the variable is absent**. Nothing in the tree
shows it ran here: an earlier BIOS, the factory, or the service itself could
have created the variable first. The issue's framing ("something rewrote the
whole block after creation") presupposes an event with no committed evidence
behind it.

**2. The issue's own candidate hypothesis is not what the committed dumps look
like.** A `GetFwVars()` returning `default(NVRAM_STRUCT)` followed by a
whole-struct `SetFwVars` would take `OemBoardSsid` to 0 and null the four 8-byte
lighting arrays. Every committed dump in `evidence/uefi/` carries `0x11171D05`
with those arrays fully populated, and the pair taken either side of one
deliberate change differs by a single byte. So the last whole-block write
carried a **warm** cache — and a warm cache preserves offset 0x60 and
`Reserved` exactly as it read them. The zeros are a property of the block *as
read*; the evidence is equally consistent with "0x60 was never 1" as with "0x60
was 1 and was later zeroed".

`docs/findings.md` §8 records that "which writer did that is not known". That
stays true, and no retraction is needed.

## The layout is computed, not carried

`NVRAM_STRUCT.cs` has **no** `[StructLayout]`, no `[FieldOffset]` and no `Pack`;
the only marshalling attributes are `ByValArray` on the four lighting arrays
(`SizeConst = 8`) and on `Reserved` (`SizeConst = 76`). So C# lays it out
sequentially, each scalar naturally aligned and a `byte[]` aligned to one.
Recomputed from the committed `.cs`, that is **180 bytes** with
`MemoryOverClockSupport` at **0x60**, `ApUseFlag` at 0x61, `OemDisplayMode` at
0x62 and `Reserved` at 0x68..0xB3; the packed figure would be 178, and 0x60
would then be 0x5F. The only padding is at 0x43 and 0x63. `python3
tools/check_uniwill_writers.py` recomputes this on every run and prints both
figures, so a field reorder in a later service build is a red run rather than a
write-up describing the old struct.

## BIOS writers

Resolved from `bios/decompiled/OemUniWillVariableDxe.asm` and from the buffer
each `SetVariable` is handed. The decompiled C cannot supply the offsets:
Ghidra names its stack locals after the entry frame pointer and these routines
rebuild `RBP` for themselves, so a local's name does not line up with its
displacement by eye. Measuring each displacement against the `Data` argument of
the `GetVariable` sidesteps that, and the arithmetic checks itself: the create
path's stores land exactly on field boundaries and skip precisely the two
padding bytes at 0x43 and 0x63, which no off-by-one reading would do.

**Every BIOS writer below except the first is a read-modify-write of the whole
180-byte block.** Each issues `GetVariable` for `0xB4` bytes, patches a handful
of offsets, and calls `SetVariable` with the same buffer. None of them assigns
0x60 and none touches `Reserved`.

| writer | whole block? | offsets assigned | 0x60? | `Reserved`? |
|---|---|---|---|---|
| `OemUniWillVariableDxe` `FUN_00000454` (create-if-missing) | yes, **from absent** | see below — the only assignment to 0x60 this sweep found | **writes 1** | fills `0x67..0xB2` with `0xFF` |
| `OemOcDxe` `OcRecovery` (`0x67C`) | yes, RMW, status unchecked | `+0x5C` `OverClockRecoveryFlag` = 1 | no | no |
| `OemOcDxe` `SyncOcVariables` (`0x7A8`) | yes, RMW, status unchecked | `+0x36` `ICpuCoreVoltageMaximum` = 2000, `+0x3C` `ICpuCoreVoltageOffsetMaximum` = 100, each a 32-bit store so the adjacent minimums become 0 | no | no |
| `OemServiceSmm` (SMM variable protocol; read at vtable slot `+0x00`, write at `+0x10`) | yes, warm RMW | `+0x0E` `TDRdata`; `+0x2F` `PowerMode`; `+0x0F`/`+0x17` `RGBKeyboard1A`/`RGBKeyboard08` (8 bytes each); `+0x1F`/`+0x27` `SmartLightbar1A`/`SmartLightbar08` (8 bytes each); `+0x04`,`+0x06`,`+0x07`,`+0x08`; `+0x0D` `ColorCalibrationSupport`; `+0x09`..`+0x0C` `RGBLightbarMode` and its three channels | no | no |
| `OemPowerModeDxe` (`0x494`) | yes, RMW of a **0xB4-byte variable** | one byte at `+0x2F`, holding 0 or 1 | no | no |

Several modules read the variable and never write it: `OemServiceDxe`,
`OemDgpuBoardIDDxe` and `OemKbLightDxe` issue only `GetVariable` (the
`SetVariable` in `OemKbLightDxe` is for a different variable, name `0xF10`), and
`OemDgpuBoardIDPei` uses the PEI read service.

**The two `OemOcDxe` writers do not check that their read succeeded.** Both
issue `GetVariable` for the block and call `SetVariable` on the same buffer
without testing the returned status, so a failed read would have them write back
whatever the frame held — for `OcRecovery` a stack buffer that nothing in the
function initialises beyond the one byte it patches. That is the one BIOS path in
this sweep that could put zeros in `Reserved` rather than carrying them, and it
is worth naming for that reason. It still cannot have produced the committed
dumps: an uninitialised frame would not also carry `OemBoardSsid` =
`0x11171D05` and four fully populated lighting arrays. `OemServiceSmm` does test
the status before writing, so its write-backs are genuinely warm.

### The create path's actual image, and why it is not what the dumps hold

Two things about it are worth stating precisely, because both are wrong in ways
a reader cannot see from the C.

**The `0xFF` fill is not aligned to `Reserved`.** It is 76 bytes starting at
offset **0x67** — one byte *before* `Reserved` — so it covers `FnKeyStatus`
plus `Reserved[0..74]` and leaves the last reserved byte, 0xB3, to whatever the
frame held. It is not "0xFF in the 76 reserved bytes". Three bytes of the block
are never assigned by this path at all: 0x43 and 0x63 because they are
alignment padding, and 0xB3 because the fill stops short of it.

**The store that writes 0x60 is 16 bits wide.** At `0x5CB` a single
`mov word ptr [RBP + -0x19], 0xff01` puts `0x01` at offset 0x60 **and `0xFF` at
0x61** (`ApUseFlag`). So the create path cannot produce the committed dumps
even in principle: every dump reads `OemBoardSsid` = `0x11171D05` and
`ApUseFlag` = 1 where this path writes `0xFFFFFFFF` and `0xFF`, `PowerMode`
reads 1 or 2 where this path writes `0xFF`, and the reserved region is all
zero where this path writes `0xFF` across most of it. That is not a small drift;
it is a different block.

### Two limits of this sweep, stated as such

- **Variable identity in every module but `OemOcDxe` is by name symbol and
  size, not by GUID bytes.** The listings cover `.text` only, so the 16 GUID bytes at
  each writer's GUID constant are not readable from the committed decompilation,
  and the DXE bodies inside `vendor/bios-1.09/BIOS_1.09.zip` are compressed, so
  resolving them needs `UEFIExtract`. `bios/annotations/ghidra-functions.csv`
  independently records `OemOcDxe`'s buffer as `UniWillVariable
  9f33f85c-…`; direct byte-level confirmation for the others is **not found by
  this method**.
- **`OemPowerModeDxe` writes its `0xB4` variable under raw address constants,
  not the `u_UniWillVariable_` symbol, so which variable it is was not
  established.** It is in the table because the size and the patch shape match;
  whether that size belongs to this variable is **not found by this method**.
  The one byte it patches is at `+0x2F` and holds 0 or 1, chosen by comparing a
  byte at ROM address `0xFF430034` — this routine's *other* EC read, of register
  `0x9F`, feeds the `Setup` variable rather than this one, which the decompiled
  C reads as though it did not.

## Windows writers

All of it is in `windows/decompiled/v3.1.39.0/GCUService/MyControlCenter/`.
That is the only decompiled `GCUService` in the tree: the other two version
trees hold no `GCUService` directory and no `NvramVariable` identifier at all —
**not found by this method**, rather than "identical" or "different", so
nothing below is claimed about them.

Every path funnels into `SetFwBufferTesting`, the only caller of `WriteUefi`.
It marshals the process-global `_fwvars` with no `Pack` — 180 bytes, the whole
block — and writes all of it. So the service is a whole-block writer by
construction, and the interesting question is what it holds when it does.

`GetFwVars()` **assigns `_fwvars` unconditionally**, including on both failure
paths: a `Monitor.TryEnter(NvramLock, 100)` timeout leaves the struct at
`default(NVRAM_STRUCT)`, and so does a `ReadUefi` throw. The method returns the
zeroed struct rather than signalling, so every caller proceeds as though the
read had succeeded.

**The service never assigns the field.** `MemoryOverClockSupport` is declared in
`NVRAM_STRUCT.cs` and appears in no `case` of any `SetFwVars` overload. The
places that write `1` into it — the profile loader and the read-back in
`LoadNvramVariableInfo`, in `MyFanManager_RamFan1p5.cs` — target
`NvramVariableInfo.MemoryOverClockSupport`, a static shadow field that is never
marshalled. The value survives a whole-block write only because the no-op `case`
falls through to the write, carrying the byte it read.

Three properties of the write set matter for the verdict:

- **Read-then-write, the ordinary case.** The cache is warmed once by
  `NvramVariable.Get()`, reached from `CustomizeCtrl.Init()` on the MQTT
  connection. Every `UserSet_*`, `LoadProfileAll`, `SetCpuCoreVoltageOffset`,
  `SetMemoryOverClockSwitch`, lighting and Fn-key site on that path is warm.
- **Write-with-no-read.** Launched with `-u`, `Application_Startup` takes the
  uninstall branch and shuts down without ever reaching the initialisation that
  warms the cache, then calls `m_MyFan?.Uninstall()` and
  `m_MySetting.Uninstall()`. The `Uninstall` methods in the
  `MyFanManager_RamFan1p5*` classes call `SetFwVars` with the cache still at its
  static initial value.
- **Reachable with a poisoned cache.** `Tdr2.Set()` calls `GetFwVars()` inside
  `Task.Run`, on a background thread, while `SetFwBufferTesting` takes only its
  own semaphore and never `NvramLock`. A `TryEnter` miss is silent — no log, no
  exception — and `GetFwVars` assigns the zeroed struct regardless. A writer on
  another thread can therefore be overtaken between its field assignment and the
  `StructureToPtr`. `SetFwBufferTesting` is `async void`, so the marshalling
  happens on a continuation: what gets written is what `_fwvars` holds at that
  moment, not at the call.

Two smaller notes. `SetFwVarsBuf` is declared and **never called**, so
`UpdateBufToFwVars` on application exit iterates three empty dictionaries.
And `BatteryProtection2.cs` passes `ChargeMaximumLimit`, `ChargeMinimumLimit`
and `BatteryLimitation`, none of which has a `case`: they write no field and
still perform a full-block `WriteUefi`.

## The verdict

| writer | can it produce the observed bytes? | on what evidence | what would promote it |
|---|---|---|---|
| `OemUniWillVariableDxe` create path | **No.** It writes 1 at 0x60, `0xFF` at 0x61 and `0xFF` across most of `Reserved`; the dumps have none of those. | listing, offsets resolved from the `Data` argument | nothing — its image is ruled out by the committed dumps |
| The other BIOS writers | **No**, on a warm read. Each preserves 0x60 and `Reserved` as read. | the read-patch-write shape, and the patched offsets | a read that was not warm would need explaining |
| `OemOcDxe` with a **failed** `GetVariable` | **Possible, and the only BIOS path that could put zeros there rather than carry them** — but not from an uninitialised frame, which could not also carry `OemBoardSsid` = `0x11171D05`. | neither status is tested; the buffer is a stack local | whether `GetVariable` for this variable can fail on a machine where it demonstrably exists |
| GCUService, warm cache | **No.** Carries the bytes it read, byte for byte. | the dumps are internally consistent with it — and equally with a block it never touched | — |
| GCUService, cold or poisoned cache, `-u` path or a `TryEnter` miss | **Possible, and not excluded.** It would zero `OemBoardSsid` and the lighting arrays; the dumps have neither. | no committed evidence places this before the dumps were taken | the live experiment: stop the service, note the block, start it, watch 0x60 and `Reserved` across a reboot |
| Some writer outside the committed tree — an earlier BIOS, the factory, a firmware-update tool | **Possible.** "0x60 was never 1" needs no writer at all; the create path is the only code here that sets it, and it is conditional. | the guard at `0x4CA`; the absence of any other assignment | a dump from a machine whose variable was never created, or an NVRAM image predating this BIOS |

So the answer to the issue's third bullet is: **no writer this sweep found
produces the observed block**, and the readings that survive are "0x60 was never
1", and — with nothing in the committed dumps placing it — a whole-block write
from a cold cache, whether the service's or `OemOcDxe`'s unchecked one. Between
the first two the evidence favours "0x60 was never 1". What moves the question
forward is not which writer did it: it is that the create path is conditional
and its image does not match the dumps, so the "something rewrote it after
creation" framing needs an event that has no committed evidence behind it.

## What would settle it, and what is not in this repository

The decisive experiment is a live one: with the service stopped, note the block;
start the service; watch 0x60 and `Reserved` across a reboot. That needs the
physical machine, which this pipeline does not have. `evidence/uefi/` holds dumps
taken at separate moments, and nothing here observes the EC, the BIOS or the
service running.

What *is* settled by committed inputs, and is now re-runnable:
`python3 tools/check_uniwill_writers.py --check` holds the layout, the state of
the dumps, the single-byte step between them, the guard, the offset and value
of the store that reaches 0x60, the extent of the `0xFF` fill, and the service's
absence of a `case` for the field. `--self-test` drives each of those against
the mutation it is meant to catch. Neither makes the verdict; they hold the
bytes the verdict rests on.