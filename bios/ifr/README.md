# The BIOS 1.09 form-sets, as ifrextractor reads them

Every `*.en-US.ifr.txt` here is **unedited tool output**: ifrextractor 1.6.1's
`verbose` dump of one HII form-set, copied straight out of UEFIExtract's dump
of the committed ROM. The hand-written layers are this file,
`charge-questions.csv`'s companion write-up in
`docs/findings/ifr-charge-and-battery-options.md`, and
`bios/tools/ifr_census.py`, which reads these dumps and writes the CSV.

**Nothing in this directory is an observation of the running machine.** These
are static readings of a firmware image. `Setup`, `CpuSetup`, `SaSetup`,
`PchSetup` and `MeSetup` are boot-services-only on this board
(`docs/findings.md` §6, `evidence/uefi/2026-09-19-variable-list.txt`), so the
OS cannot read a value here, and nothing here says what this board currently
holds in any of them. Reading or changing one is a human's step at the physical
machine (issue #86).

## The input, and how to re-derive every file here

```
vendor/bios-1.09/BIOS_1.09.zip
  -> GM7MG7P/GMxMGxxN109A08.ROM
     SHA-256 dfe8047f35bb1125bbb45d69c96ad83d64e59dd5e50b8d88052c0db04a2d920e
```

That digest is the one `bios/tools/bios_extract.py` refuses to proceed without
(`ROM_SHA256`, and `extract_rom`/`build` both check it), so a ROM that has moved
cannot silently become the input to a new dump. `bios_extract.py --extract`
regenerates `Setup.en-US.ifr.txt` and re-reads the ROM for the decompiles; the
other eleven files here are **not** in that script, and the reason is
`bios/README.md`'s own rule — a new tool is a new file, not another mode bolted
onto an existing one.

The two commands, given a scratch directory:

```
UEFIExtract rom.bin all                       # -> rom.bin.dump/, 2 s to 49 min
ifrextractor <body> verbose                   # -> <body>.0.0.en-US.uefi.ifr.txt
```

**UEFIExtract's cost is not a property of the firmware.** The same command on
this machine measured 1.7 s, 2025 s and 2941 s in one session
(`bios/tools/bios_extract.py`'s docstring), and `bios/README.md` records the same
spread. Those are load, not ROM. Only the second command is needed to re-derive
a dump from a dump you already have.

## Which form-sets the ROM carries

Twelve, in twelve modules. Eleven of them besides `Setup`, and **none of the
eleven adds a charge or battery question** — `ifr_census.py` run over each of
them matches nothing but the plainest power words in a couple of `Subtitle`
warnings, which are not questions at all.

| dump | form-set | the body `ifrextractor` was run on, in `rom.bin.dump/` |
|---|---|---|
| `Setup.en-US.ifr.txt` | Setup | `0 5C60F367-…/76 Setup/1 PE32 image section/body.bin` |
| `FboGroupForm.en-US.ifr.txt` | FixedBootOrder Group Form | `0 5C60F367-…/140 FboGroupForm/1 PE32 image section/body.bin` |
| `HddAcousticDynamicSetup.en-US.ifr.txt` | Acoustic Management Configuration | `0 5C60F367-…/75 HddAcousticDynamicSetup/1 PE32 image section/body.bin` |
| `HttpBootDxe.en-US.ifr.txt` | HTTP Boot Configuration | `0 5C60F367-…/191 HttpBootDxe/1 PE32 image section/body.bin` |
| `Ip4Dxe.en-US.ifr.txt` | IPv4 Network Configuration | `0 5C60F367-…/198 Ip4Dxe/1 PE32 image section/body.bin` |
| `NvmeDynamicSetup.en-US.ifr.txt` | NVMe controller and Drive information | `0 5C60F367-…/104 NvmeDynamicSetup/1 PE32 image section/body.bin` |
| `PciDynamicSetup.en-US.ifr.txt` | PCI Subsystem Settings | `0 5C60F367-…/88 PciDynamicSetup/1 PE32 image section/body.bin` |
| `PciOutOfResourceSetupPage.en-US.ifr.txt` | !!!! PCI Resource ERROR !!!! | `0 5C60F367-…/90 PciOutOfResourceSetupPage/1 PE32 image section/body.bin` |
| `ReFlash.en-US.ifr.txt` | Recovery | `0 5C60F367-…/98 ReFlash/1 PE32 image section/body.bin` |
| `VlanConfigDxe.en-US.ifr.txt` | VLAN Configuration | `0 5C60F367-…/194 VlanConfigDxe/1 PE32 image section/body.bin` |
| `RaidDriver.en-US.ifr.txt` | Intel(R) Rapid Storage Technology | `0 5C60F367-…/292 RaidDriver/1 EE4E5898-…/0 PE32 image section/body.bin` |
| `6B237146-C179-4B5D-A52F-641BC0DFCACD.en-US.ifr.txt` | Realtek Ethernet Controller | `0 5C60F367-…/338 6B237146-…/0 Compressed section/0 PE32 image section/body.bin` |

`0 5C60F367-…` is the DXE firmware volume, itself nested inside the AMI
Setup wrapper `4 4F1C52D3-…`; the rest of each path is that volume's own
directory. Each dump's **first line names the SHA-256 of the body it was made
from**, so a reviewer can confirm the pairing in the table above without
re-running anything: read the digest out of the dump and hash the body.

Two of the twelve are named for something other than their module's form-set,
and the file names follow the module rather than the title:
`RaidDriver` is a module whose *nested* HII package is Intel's Rapid Storage
form-set, and `6B237146-C179-4B5D-A52F-641BC0DFCACD` is a FFS file UEFIExtract
reports with no `Text:` at all, so it has no module name to use and the file
GUID is what there is.

## How the twelve were found, and what was ruled out

The method is the one `bios_extract.py` already uses for `Setup` — a module's
own **image section** body, which is `image_body()`/`find_module()` in that
script — applied to the whole ROM:

1. **356** module names in the dump have a `PE32 image section` or
   `TE image section` as a direct child. `ifrextractor` was run on each of
   those bodies. **Ten** produce a form-set, `Setup` among them.
2. **23** FFS modules are compressed: their only top-level section is the
   GUID-defined wrapper, so the image is not there to read until UEFIExtract
   has decompressed it. `ifrextractor` was run on every nested `body.bin` of
   each. **One** produces a form-set — `RaidDriver`'s Intel RST package. The
   Realtek driver is a twelfth module of this shape, found by enumerating FFS
   files rather than by the `<n> <Name>` naming rule, because it is GUID-named.

**`AMITSE` and `AMITSESetupData` carry no HII package.** Both are in the second
group, both were checked at every nested level, and neither produced any output.
That is the answer to the question issue #95 asked about `AMITSE` specifically,
and it is scoped: *not found by this method, on this ROM, by this ifrextractor*.
It is not a claim that no `AMITSE` anywhere carries a form-set.

**The method that does not work, so nobody repeats it.** Handing
`ifrextractor` every `body.bin` in the dump — 2,813 of them — looks more
thorough and is not. Two of those bodies are the DXE firmware volume and the
volume that contains it, and `ifrextractor` scans a multi-megabyte blob for
package signatures and emits a slice per hit: 342 outputs, every one of them a
different digest, with form-set titles and `VarStore` names that belong to
different modules than the address ranges around them. One of those slices
carries the title *"Built-in EFI Shell"* over a
`HTTP_BOOT_CONFIG_IFR_NVDATA` store. None of the 342 is a form-set a firmware
would ever show, and all twelve real ones are found by the per-module pass
above. A dump is only a form-set when a single module is what was handed to the
tool.

## Defaults: the IFR's, not this machine's

`charge-questions.csv`'s `default_normal` and `default_mfg` columns are the
IFR's own `Default` statements (DefaultId 0x0 and 0x1), falling back to the
`OneOfOption` flagged `Default`/`MfgDefault` for the `OneOf` questions that
state it there instead. That is a statement about the IFR.

The ROM's **factory** values are a different thing: an NVAR `StdDefaults` store,
which UEFIExtract dumps to
`…/NVRAM external defaults/…/StdDefaults/<n> <Name>/body.bin` and which is
deliberately **not committed** (see `bios/README.md`, "Default values"). Nothing
in this directory or in `ifr_census.py` reads it, and no column here is a
statement about what this board currently holds. `docs/findings.md` §8 used the
two together for `CpuSetup[0x1B7]` and found they agreed; that was a
coincidence checked once, not a rule.

## `UniWillVariable`: not found in any form-set here

The runtime variable `UniWillVariable`, GUID
`{9f33f85c-13ca-4fd1-9c4a-96217722c593}`, appears **zero** times in
`Setup.en-US.ifr.txt`, and no `VarStore` line in it declares that name or that
GUID. No `HiiAddPackage` appears in any of the 39 committed decompiles either.

Method, named so the negative can be re-run: a case-insensitive substring search
for `UniWillVariable` and for `9f33f85c` over all twelve dumps in this directory,
and a case-insensitive search for `HiiAddPackage` over
`bios/decompiled/*.c` and `*.asm`. This is **not found by this method** — it is
a search of these twelve dumps and a symbol-level search of the decompiles this
repository has. It is not a claim about every module in the ROM, and it is not a
claim that no form-set anywhere references the variable.

The positive half is already recorded and is not re-derived here:
`docs/findings.md` §8 has `OemOcDxe` copying `UniWillVariable[0x33]` into
`Setup[0x7D7]` at boot, which is how a runtime variable gates a
boot-services-only one. **That consumer is DXE code, not a form-set.** A
form-set that could not see the byte would not need the copy, so the copy is
evidence for the opposite reading, not a counter-example to it.

## Reading a dump

```
python3 bios/tools/ifr_census.py                        # the charge/battery census
python3 bios/tools/ifr_census.py --offset Setup:0x4F3   # one offset
python3 bios/tools/ifr_census.py --question 0x2A6       # one question id
python3 bios/tools/ifr_census.py --match turbo          # any question, any term
python3 bios/tools/ifr_census.py --list-excluded        # what the vocabulary declined
python3 bios/tools/ifr_census.py --ifr <other>.ifr.txt  # the same code, another dump
python3 bios/tools/ifr_census.py --check                # the committed CSV is current
python3 bios/tools/ifr_census.py --self-test            # known answers, fixture IFR
```

`--check` and `--self-test` need neither the ROM nor UEFIExtract nor
ifrextractor. `--check` is the one to wire into a gate: it re-derives
`charge-questions.csv` from the committed `Setup.en-US.ifr.txt` and fails on any
difference, so the CSV is a derived artefact rather than a typed table.

`Setup.en-US.ifr.txt` is 27,301 lines, 207 forms and 3,659 questions that
address a variable store. Reading one question by hand is a `grep`:
`grep -n 'QuestionId: 0x2A6, VarStoreId' Setup.en-US.ifr.txt` prints the offset,
and the block above it prints the `SuppressIf` that decides whether the question
is shown at all.
