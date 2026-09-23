# BIOS 1.09 (AMI Aptio V, `N.1.09A08`)

Tool output derived from `vendor/bios-1.09/BIOS_1.09.zip`, plus the
annotations made on top of it. Everything under `ifr/` and `decompiled/`
except `*.annotated.c` is unedited tool output and regenerates with:

```
python3 bios/tools/bios_extract.py --work /tmp/bios \
    --uefiextract ~/.local/opt/bin/uefiextract \
    --ifrextractor ~/.local/opt/bin/ifrextractor \
    --ghidra ~/.local/opt/ghidra/support/analyzeHeadless --extract
```

That needs UEFIExtract, ifrextractor and Ghidra's `analyzeHeadless`, which
`.github/actions/project-setup` installs; the script's docstring shows the
Windows invocation. `--extract` regenerates `ifr/` and re-reads the ROM, and
UEFIExtract is the slow part — measured anywhere from 2 seconds to 49 minutes
on this machine across four runs of the same command, so the spread is load
and none of those numbers is a property of the firmware. Drop `--extract` and
the same command re-exports the decompiles from the committed Ghidra project
in about 40 seconds without touching the ROM at all, which is the mode to use
day to day. The script's two check modes need neither tool:

```
python3 bios/tools/bios_extract.py --work /tmp/bios --check
python3 bios/tools/bios_extract.py --work /tmp/bios --self-test
```

| Path | What |
|---|---|
| `ifr/Setup.en-US.ifr.txt` | The `Setup` driver's HII forms (ifrextractor 1.6.1, verbose): every setup question with its varstore, offset, options, defaults and suppress/grayout conditions, visible or not |
| `decompiled/<Module>.c` | Ghidra 12.1.3 decompiles of 38 modules: every `Oem*` module in the ROM, Intel's overclocking chain, `EcPs2Kbd` and `Setup`. **Unedited tool output** |
| `decompiled/OemOcDxe.annotated.c` | **Hand-written.** `OemOcDxe` with variable offsets resolved and named: the memory-OC menu gate, the EC 0x0741 bit 7 recovery path, the GPP_B22 write. The readable layer, and the reason it is not generated — see "Which layer is which" |
| `annotations/ghidra-functions.csv` | **Machine-readable**, transcribed from the file above, and what the build applies to the Ghidra project. `annotations/README.md` documents the columns |
| `ghidra/` | The Ghidra project, the headless scripts `bios_extract.py` uses, the index, the manifest and the load map. `ghidra/README.md` is the long version |
| `tools/bios_extract.py` | Regenerates the tool output |

## Which layer is which

Three layers, and they are not interchangeable.

- **`decompiled/<Module>.c` is unedited Ghidra output.** `FUN_000004f8`,
  `DAT_000019a0`, EDK2 pointer chains. It is what the tool produced and the
  build reproduces it byte for byte, so a diff in it means the tool or the
  input changed.
- **`decompiled/*.annotated.c` is the hand restatement.** The same code with
  `CpuSetup.OverclockingSupport = 0;` and
  `MmioOr32 (PCR (0x6E, 0x790 + 22 * 0x10), BIT0)` where the decompile has a
  five-deep function-pointer call. It is written by a person, for a reader, and
  **is not generated** — a generated version of it is the pointer chains again,
  which is the thing this layer exists to replace. That is why
  `bios/README.md`'s rule is "everything except `*.annotated.c` is unedited
  tool output": the exception is the readable layer, not a second exporter.
- **`annotations/ghidra-functions.csv` is the machine-readable layer.** One row
  per named function: address, name, type, the reading, its evidence and
  whether the name is a transcription or a fresh reading. It is what
  `bios_extract.py` applies to the Ghidra project, so the names and comments
  reach the index, the manifest and every future export.

The last two are two copies of one reading kept side by side, so they can
drift, and `bios/tools/bios_extract.py --check` is the guard: it reads the
addresses each restatement names as functions and fails if the CSV has no row
at one of them, and it fails in the other direction too if a row marked
`hand-decoded` — which means the restatement records that reading — names
something the restatement no longer mentions. The guard needs no Ghidra and no
network.

## Which 38 modules

Every `Oem*` module in the ROM — 32 of them, the TongFang/Uniwill-authored set
this repository is reverse engineering — plus Intel's overclocking chain
(`DxeOverClock`, `OverClockSmiHandler`, `OverclockInterface`, `PeiOverClock`),
plus `EcPs2Kbd`, plus `Setup`. The overclocking chain is reference code, not
vendor code, and it is here because issues #104, #115, #117, #118 and #119
name it and the memory-overclocking path cannot be read without it, not
because TongFang wrote it. `docs/findings.md` says there are 33 `Oem*`
modules and 21 that had never been decompiled; measured against
UEFIExtract's dump it is 32 and 20, with 26 modules outside the twelve that
had been done. `bios/ghidra/README.md` has the counts asserted so they cannot
drift again.

## Reading the IFR

Questions refer to variables by `VarStoreId`; the `VarStore` lines at the
top map an id to a name, GUID and size. The ones that matter most here:
`0x1` Setup (0x7D8 bytes), `0x12` CpuSetup (0x2BB), `0x17` SaSetup (0x21D),
`0x18` PchSetup (0x6EC), `0x37` SetupVolatileData. A condition like
`EqIdVal QuestionId: 0xEC6` refers to another question; search for
`QuestionId: 0xEC6, VarStoreId` to find the offset it reads. Hidden numerics
with an empty prompt are how the BIOS exposes such flags to conditions.

`Setup`, `CpuSetup`, `SaSetup`, `PchSetup` and `MeSetup` are
boot-services-only on this machine (docs/findings.md §6). The OS cannot
read or write them. `UniWillVariable` is runtime-writable, and vendor
modules copy some of its bytes into those stores at boot, which is how the
memory-overclocking menu gets unlocked (docs/findings.md §8).

## Default values

The ROM carries the factory defaults of each setup store as an NVAR
`StdDefaults` store. UEFIExtract dumps it under
`.../NVRAM external defaults/.../StdDefaults/<n> <Name>/body.bin` in its
`.dump` tree. It is not copied here; read it from a `bios_extract.py` work
directory.

## What the new modules show

Everything below is from the 26 modules this build added, read out of
`decompiled/`. Nothing here is a hardware observation: all of it is static
analysis of the committed zip.

**The Intel OC module is gated by the byte the vendor code clears.**
`DxeOverClock` at RVA `0x400` reads `CpuSetup` and returns immediately unless
`CpuSetup[0x1B7]` is non-zero. That is the same "OverClocking Feature" byte
`OemOcDxe` turns off in its recovery path (docs/findings.md §8), read here at
`0x2AB7` with `CpuSetup`'s data pointer at `0x2900`. So the stock Intel
Advanced page `0x2718` and its OverClocking Performance Menu `0x27AA`
(issue #119) are behind the same vendor-controlled byte as the vendor page's
own "Memory" link, not behind a separate mechanism. This is a reading of the
decompile, not a test of whether the page then appears.

**`OcSetup` is the overclocking state store.** 138 bytes (`0x8A`), a fifth
setup variable that `DxeOverClock` reads and writes alongside `Setup`,
`CpuSetup` and `SaSetup`. Its byte 0 is the state: 0 is the normal path, and
1 makes the module restore all four stores to their pre-overclock values and
reset. `docs/findings.md` already lists `OcSetup` among the 114 runtime
variables `windows/tools/uefi_var.py list` sees; its size and this role were
not known.

**`PeiOverClock` is a stub.** 672 bytes, two functions, 53 bytes
disassembled: the entry looks up a protocol and registers one callback, and
there is no overclocking code in it at all. The rest of `.text` is unreached
CRT (`memcpy`, `memset`, divide) and there is a 156-byte `.data` section.
It is part of the chain issues #104/#115/#117/#118/#119 name, and it is not
where the overclocking is.

**A PEI module reads the runtime `UniWillVariable`.** `OemDgpuBoardIDPei`
reads the whole 180-byte variable, replaces its first dword with one of ten
constants selected by a byte at `0xFF430039` — a fixed low block whose role
this pass did not establish — then walks a table of PCI functions until it
finds bus 0, device `0x1F`, function 3, and queues the constant against it
for two configuration-space writes. All ten constants share the low halfword
`0x1D05`. Which register inside `00:1F.3` it lands on is not recoverable
from this decompile, so the dGPU board ID is located, not explained. It does
mean the dGPU board identity is partly a *runtime variable* read before the OS
starts, which matters for #118.

**A third module speaks the same EC command set.** `OemApControlDxe` uses
`0xA3 07` / `0xA2 lo` / `0xA4` and `0xA5 value` over ports `0x62`/`0x66`, the
same sequence as `OemOcDxe` and `OemUniWillVariableDxe`. The reading of
`0xA2`-`0xA5` as EC RAM addressing (docs/findings.md §8) is now supported by
three independent users rather than one, which is worth something, and is
still not a confirmation from the EC side.

**`IsPchLp` does not describe its return value.** The name comes from the
hand-written `OemOcDxe.annotated.c` and is preserved as transcribed, but
`FUN_00001158` returns 1 when the `00:1F.0` device ID is *not* the -LP class
and the pad group has more than 22 pads. The call site's early return is what
inverts it, and the surrounding prose is right; the name is loose. The
discrepancy is recorded next to the row in
`annotations/ghidra-functions.csv` rather than quietly fixed, per CLAUDE.md.
