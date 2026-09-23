# BIOS 1.09 (AMI Aptio V, `N.1.09A08`)

Tool output derived from `vendor/bios-1.09/BIOS_1.09.zip`, plus the
annotations made on top of it. Everything under `ifr/` and `decompiled/`
except `*.annotated.c` is unedited tool output and regenerates with:

```
python3 bios/tools/bios_extract.py --work /tmp/bios
```

That needs UEFIExtract, ifrextractor and Ghidra's `analyzeHeadless`, which
`.github/actions/project-setup` installs. The script's docstring shows the
Windows invocation.

| Path | What |
|---|---|
| `ifr/Setup.en-US.ifr.txt` | The `Setup` driver's HII forms (ifrextractor 1.6.1, verbose): every setup question with its varstore, offset, options, defaults and suppress/grayout conditions, visible or not |
| `decompiled/<Module>.c` | Ghidra 12.1.3 decompiles of the vendor `Oem*` modules that reference `UniWillVariable`, plus `OemOcPei` |
| `decompiled/OemOcDxe.annotated.c` | `OemOcDxe` with variable offsets resolved and named: the memory-OC menu gate, the EC 0x0741 bit 7 recovery path, the GPP_B22 write |
| `tools/bios_extract.py` | Regenerates the above |
| `ghidra/` | The headless scripts `bios_extract.py` uses |

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
