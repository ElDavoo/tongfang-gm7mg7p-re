# Ghidra: the BIOS firmware as a C codebase

**Status: built.** `project/` holds a Ghidra 12.1.3 project with all 38
modules `bios/tools/bios_extract.py` selects, `../decompiled/` holds their
unedited decompiles, and `../annotations/ghidra-functions.csv` is the editable
layer that improves both. 955 functions, 38 of 38 modules decompiled with zero
failures. `../decompiled/OemOcDxe.annotated.c` is the hand-written readable
restatement of one of them; it is not generated, and `../README.md` says which
layer is which.

## How to use it

```
# re-export from the committed project (about 40 s, leaves project/ alone)
python3 ../tools/bios_extract.py --work /tmp/bios \
    --ghidra ~/.local/opt/ghidra/support/analyzeHeadless

# rebuild the project itself from the ROM: a new module, a changed seed, or
# someone improving the project's own symbol table
python3 ../tools/bios_extract.py --work /tmp/bios --mode rebuild-project \
    --uefiextract ~/.local/opt/bin/uefiextract --ghidra ...

# also regenerate ../ifr/ (runs UEFIExtract, see the timing note below)
python3 ../tools/bios_extract.py --work /tmp/bios --extract --uefiextract ...

# what the gates check, with no Ghidra, no network and no UEFIExtract
python3 ../tools/bios_extract.py --work /tmp/bios --check
python3 ../tools/bios_extract.py --work /tmp/bios --self-test
```

`--check` and `--self-test` read only committed files, so they are cheap
enough for a gate — 0.33 s and 0.07 s respectively on a GitHub-hosted runner
(2026-09-23), all 50,887 instructions across the 955 listings included, so the
listing parse is not a reason to defer them. Neither opens the project. Both
run in the cheap tier of `.github/scripts/agent-gates.sh`; nothing here is
deferred to `AGENT_GATES_DEEP=1`.

## What is here

| Path | What |
|---|---|
| `project/bios.gpr`, `project/bios.rep/` | the Ghidra project: one program per module, named after its `.efi` |
| `modules/<TE module>.efi` | the five TE bodies, committed — see "Why the TE images are committed" |
| `load-map.csv` | per module: kind, image size, image SHA-256, and the address it is loaded at |
| `index.csv` | every function: module, address, name, size, how it was seeded, what is annotated, and the evidence for it |
| `manifest.csv` | per module: function/decompile/fail counts, bytes disassembled, body bytes, Ghidra version, input SHA-256 |
| `DecompAll.java`, `TeEntry.java` | the two scripts only this project needs |
| `../../ghidra/scripts/*.java` | the shared headless scripts, the same ones the EC and Windows projects use |
| `../annotations/ghidra-functions.csv` | **the editable layer.** Names, types, comments, evidence |

## Which 38 modules, and why

Every `Oem*` module in the ROM — 32 of them, the TongFang/Uniwill-authored
set that this repository is actually reverse engineering. Plus:

- **Intel's overclocking chain** — `DxeOverClock`, `OverClockSmiHandler`,
  `OverclockInterface`, `PeiOverClock`. Reference code, not vendor code, and
  here for the same reason the rest of the Intel and AMI modules are reference
  code: these are the modules issues #104, #115, #117, #118 and #119 name,
  and the memory-overclocking path cannot be read without them. They are in the
  set because those issues name them, not because TongFang wrote them.
- **`EcPs2Kbd`** — the PS/2 scan-code table the keyboard-light module reads.
- **`Setup`** — 842 KB of HII form engine. The IFR text in `../ifr/` comes out
  of the same binary, and the code that evaluates the forms is not the same
  thing as the text that describes them.

`docs/findings.md` §"Two coverage numbers" says there are 33 `Oem*` modules
and that 21 had never been decompiled. Measured against UEFIExtract's dump of
the committed zip, there are **32**, and **20** of them were untouched; 26
modules in total were outside the twelve that had been done. The counts
themselves are asserted in `--self-test` against the load map, so they cannot
drift again. Correcting that sentence is a `docs/` edit and was out of scope
here.

## The two shapes of module, and why the build looks the way it does

**PE32, 33 modules.** Ghidra's PE loader reads the machine type and the entry
point and auto-analysis finds the rest, so these need almost nothing from us —
one seed each, the entry point read out of the PE header. They go into **one**
`analyzeHeadless` invocation. Measured, on four small modules: 12.3 s in one
JVM against 29.3 s in four, so 2.4x, and the 17 s difference is three JVM
starts at ~5.7 s each. Across 38 modules that is minutes, not an hour.

**TE, 5 modules.** A stripped PE image with a 40-byte `VZ` header and no
loader of its own. `te_layout()` puts it at its execute-in-place address,
`ImageBase + StrippedSize - sizeof(TE header)`, and the entry point comes out
of the same header. `-loader` and `-loader-baseAddr` are per-invocation, not
per-file, so these are grouped by load address; on this ROM all five differ,
so that is five invocations of one module each.

**Both shapes are measured, not estimated** (`../tools/bios_extract.py` times
every invocation and prints it). A full `--mode rebuild-project` on this
machine:

| step | time |
|---|---|
| `uefiextract rom all` | see the note below |
| import + analyse 32 PE32 modules, one JVM | 85.6 s |
| import + analyse `Setup`, one JVM | 13.5 s |
| import + analyse 5 TE modules, 5 JVMs | 24.4 s |
| apply annotations + export 38 programs, one JVM | 36.0 s |
| **Ghidra total** | **159.5 s** |
| project size | 49 MB |
| `../decompiled/` | 1.1 MB |

So: 7 JVMs, 955 functions, zero decompile failures, and the twelve
`decompiled/*.c` files that existed before this build come out
**byte-identical** — checked on every run and reported, because a changed `.c`
is a diff a reviewer has to read and must not happen quietly.

**On UEFIExtract's time.** Across four runs of the identical command on this
machine it measured 1.7 s, 2025 s and 2941 s. The spread is machine load, not
the ROM, and none of those numbers is a property of the firmware. The only
thing to take from it is that it is not instant and not dependable, which is
why the default mode does not run it: it re-exports from the committed
project, and only `--mode rebuild-project` and `--extract` need the dump.

## Why the TE images are committed

`modules/` holds the five TE bodies, 11.6 KB in total. They are **committed
inputs**, like `vendor/`: the Ghidra build genuinely needs them, a TE image has
no loader Ghidra can apply, and 11.6 KB is not worth an extraction step at
every build. They are also the inputs whose addresses the build *derives* — the
execute-in-place address is `ImageBase + StrippedSize - sizeof(TE header)` and
not something read out of a header field — so committing them is what makes
the derivation checkable: `--self-test` runs `te_layout()` on the committed
`OemOcPei.efi` and asserts the load address and entry match the load map, and
that each committed image's SHA-256 matches too.

PE32 bodies are not committed. A PE loader reads the header, so they carry no
derived state, and they are 1.05 MB, most of it `Setup`.

## Two exporters, on purpose

`bios/decompiled/<Module>.c` is `DecompAll.java`'s output: the unedited
decompile, header line and all, and byte-identical to what was committed
before this build. `ExportDecompile.java` runs on the *renamed* program in the
same JVM and writes, to the work directory, the provenance header, the index
rows and the per-module counts that `index.csv` and `manifest.csv` are built
from.

`DecompAll.java` runs first, before `ApplyAnnotations.java` renames anything.
That order is the whole reason the twelve pre-existing files still match: an
export taken after the rename would carry `OemOcDxeMain` where the committed
file says `FUN_000004f8`.

The committed project is snapshotted **before** any annotation is applied, for
the same reason. `--mode rebuild-project` imports into a scratch project,
copies that to `project/`, and then does the export from a copy of the copy.
The committed `.rep` is therefore always the unedited analysis, and an
annotation change is a one-line CSV diff and a text diff rather than a 49 MB
binary one.

## The hand restatement is not generated

`../decompiled/OemOcDxe.annotated.c` is written by a person and stays that
way. It is the readable layer — `CpuSetup.OverclockingSupport = 0;` where the
decompile has a five-deep function-pointer call — and generating it from the
CSV gives back the decompile's own notation, which is the one thing the layer
exists to replace. The build does not write it.

What the build does instead is check the two against each other, in
`--check`: it reads the function addresses each `*.annotated.c` names and fails
if `../annotations/ghidra-functions.csv` has no row at one of them, and fails
the other way if a row marked `hand-decoded` — which means the restatement
records that reading — names something the restatement no longer mentions. The
restatement is the reading; the CSV is the machine-readable copy of it, and the
guard is what stops the copy going stale. No Ghidra and no network.

## The load map, and the one thing the shared scripts cannot do

`load-map.csv` records, per module, the kind, the image size, the image
SHA-256, the address the image is loaded at (TE only) and the entry point (both
kinds). The entries become the seed specification, and the basis travels into
`index.csv`, so a reader can tell a seeded function from one auto-analysis
found. The two bases here are `entry` (a fact in the image's own header) and
`annotation` (a person read it); anything else is `auto`.

The basis is matched by **string**, and `ExportDecompile.java` keys it on
`Address.toString()`, which zero-pads to the address space's width — eight
digits for x86:LE, whatever the value. So the spec writes `0x%08X`: `0x4F8`
would never match `000004F8` and every PE32 seed would silently come out as
`auto`. That is not a hypothetical; it is what the first build of this wrote,
and the only reason it is visible is that `index.csv` carries the basis
column at all.

One limit, asserted rather than discovered later: `SeedFunctions.java` and
`ApplyAnnotations.java` both parse an address with `Integer.parseInt(.., 16)`,
a **signed** 32-bit int. A TE entry such as `0xFFF823B9` is out of range, so a
TE address cannot go through either one. The TE entry is marked by
`TeEntry.java` instead — which also names the function `entry`, which is what
`OemOcPei.c` records — and the basis file still says where the address came
from. `--self-test` asserts that no annotation row needs a 64-bit address; if
one ever does, the fix is in the shared scripts, not here.

## What the build found

Two of the findings from the 26 modules this added bear on this file's own
subject:

- **`PeiOverClock` is a stub.** 672 bytes, two functions, 53 bytes
  disassembled: the entry looks up a protocol and registers one callback, and
  there is no OC code in it. The rest of `.text` is unreached CRT
  (`memcpy`/`memset`/divide) and the `.data` section. The module named in
  #104/#115/#117/#118/#119 as part of "the Intel overclocking chain" is not
  where the overclocking is.
- **`OcSetup` is the overclocking state store.** 138 bytes, a fifth setup
  variable alongside `Setup`, `CpuSetup` and `SaSetup`, and `DxeOverClock`
  uses its byte 0 as an apply/reset flag. `docs/findings.md` already listed
  `OcSetup` among the 114 runtime variables `uefi_var.py list` sees; its size
  and role were not known.

The rest of what the 26 new modules show — the `CpuSetup[0x1B7]` gate, the
PEI dGPU board ID, the third user of the `0xA2`-`0xA5` EC command set, and
the one place the old `OemOcDxe` reading is loose — is in `../README.md`
under "What the new modules show".

## Limits

- **`disassembled_bytes` is how far analysis reached, not how much is
  understood.** It is the honest figure and it is in `manifest.csv` under that
  name.
- **`body_bytes` is not coverage.** Ghidra's function bodies overlap, so the
  sum can exceed the image size. It is reported because it is what the
  decompiler walks, not because it measures anything.
- **The project reopens only in Ghidra 12.1.3**, the version
  `.github/actions/project-setup` installs. An upgrade means a rebuild.
- **The 12 pre-existing `decompiled/*.c` files are frozen.** If a future Ghidra
  version changes a single decompiled line, the build says so loudly and
  rewrites them. That is the right behaviour for a version upgrade and the
  wrong behaviour for an accidental change, which is why the comparison
  happens on every run.
