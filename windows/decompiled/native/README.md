# Native binaries — Ghidra decompilation

Ghidra 12.1.3 (headless) output for the vendor's **native** x64 PE images: the
Windows driver/wrapper pair, the UWP core, and the UEFI-firmware shim. This is
the reproducible decompile-and-count layer under the hand-written radare2
write-ups in [`../../native/`](../../native/) (`ACPIDriver.sys.analysis.md`,
`ACPIDriverDll.dll.analysis.md`); those are the prose, this is the numbers.

The target list lives in [`../../ghidra/native-binaries.csv`](../../ghidra/native-binaries.csv).
The Ghidra project is committed at `../../ghidra/project/`, as the EC's is
(`ec/ghidra/project/`), so `--mode export-only` can re-export from it without a
rebuild. `../../ghidra/manifest.csv` is the per-program summary: one row per
program with its Ghidra version, input SHA-256, loader, function count,
decompile count, and body bytes — enough to check the pipeline without opening
the project.

The decompilation is done by the **shared** scripts in
[`../../../ghidra/scripts/`](../../../ghidra/scripts/): `ExportDecompile.java`
(per-program mode: one `.c` per binary) and `ApplyAnnotations.java`. They carry
the repository's single provenance header and its single
decompiler-unavailability guard; this tool does not fork them. The one
Windows-only script is `windows/ghidra/scripts/DisablePdbAnalyzer.java` (the
PDB exists only here). The per-function index is `../../ghidra/index.csv`.

`GamingCenter3_Cross.exe` and `GamingCenter3_Cross.dll` share a file stem, so
the driver gives them distinct **export labels** via `context.txt` — the `.exe`
(the launcher stub) exports as `GC3_launcher.c`, the `.dll` as
`GamingCenter3_Cross.c`. The exporter throws `EXPORT LABEL COLLISION` rather
than letting one overwrite the other.

## Regenerating

```
python3 windows/tools/decompile_native.py                    # rebuild project + export
python3 windows/tools/decompile_native.py --mode export-only # re-export from the project
python3 windows/tools/decompile_native.py --check            # no Ghidra, no network
python3 windows/tools/decompile_native.py --self-test
python3 windows/tools/decompile_native.py --write-digests    # after a re-export
```

`--write-digests` regenerates `../../ghidra/c-digests.csv` from the `.c` files
on disk. It needs no Ghidra and no project, and it **refuses** to write a digest
for a zero-length `.c` — a truncated export is the fault the file exists to
catch, so it is not something to record a hash of — or for one that is a
symlink, since hashing follows the link and would record the target's bytes.

Run it after any re-export that legitimately changes a `.c`. **What a reviewer
then sees is the digest row, not a diff of the `.c`**: `GamingCenter3_Cross.c`
is 56 MB and carries `-diff` in `.gitattributes`, so git renders a change to it
as `Binary files differ` with no content. The digest row is what makes the
change attributable to a named file, and that is the property this buys; it is
not the same as a readable diff, and a change here should be reviewed by opening
the file, not by reading a diff of it.

Needs Ghidra 12.1.3 and a JDK 21 (`~/.local/opt/ghidra`, `~/.local/opt/jdk`,
or `GHIDRA_INSTALL_DIR` / `analyzeHeadless` on `PATH`). The two committed PEs
are read in place; the rest are materialised into a scratch dir by
`../tools/extract.sh` (the Inno leg goes through `nix-shell -p innoextract`).
The manifest is provenance by **Ghidra version + input SHA-256** and carries
**no timestamps** — a timestamp would make every rebuild a spurious diff.

`manifest.csv` enforces `functions == decompiled + failed` per program, and the
tool fails the run if that does not hold. It carries **two** byte columns, and
the difference matters: `instruction_bytes` is the number of bytes Ghidra
actually disassembled — the honest coverage figure. `body_bytes` is the sum of
function-body lengths, and function bodies **overlap**, so it can exceed the
image size; it is a measure of what the decompiler walked, not coverage. Only
`instruction_bytes` is a coverage number. The tool also refuses to write a
manifest unless every program the index says decompiled has its `.c` on disk and
every `.c` on disk is accounted for by the index — so a `.c` that is missing, or
one the index does not cover, is caught rather than read as a complete export.

`--check` also compares the manifest's recorded function count against **both**
indexes' row counts for the same export label, checks both indexes for
duplicate `(program, addr)` keys and rows that did not come out with the full
header, and enforces the `mode:` vocabulary. Those are the cheap structural
checks, over committed text only.

It then opens the `.c` files, which it previously did not do at all (the
per-function checks are §14j in `docs/findings.md`, and they correct a sentence
in §14 that said otherwise). Two of them:

- **Every index row is paired to the function its `.c` declares** — the file
  exists, is non-empty, and carries the `// ==== <name> @ <addr>` separator for
  the address and name the row gives it. Each distinct `.c` is read once, not
  once per row: `out_file` is empty on all 10,664 Windows rows, so a per-row read
  would re-read `ACPIDriverDll.c` 10,141 times. The run prints both counts
  (`10,664 index row(s) … across 5 distinct file(s)`) so the number in the output
  says what was read.
- **Every committed `.c` is checked against `../../ghidra/c-digests.csv`**, a
  committed SHA-256 and byte count per file. This is the half the pairing
  structurally cannot do: `GamingCenter3_Cross.c` is in no index row, so a check
  built on index rows says nothing about it however thorough it is. Regenerate
  with `--write-digests` (below) after a re-export.

The digest is a **corruption check, not a proof of correctness**: it catches a
truncated, half-overwritten or hand-edited decompile, and it forces any accepted
change to be a visible committed diff. It is not an anti-tamper control —
`--write-digests` will re-bless a mangled file — and a digest that agrees does
not mean the decompile is a faithful reading of the binary. That would need
machine code to check it against, which is the next paragraph.

The whole `--check` is **1.90 s** here (1.89 / 1.91 / 1.90 over three runs)
against the 1.72 s §14e recorded, so the two new C checks cost about 0.18 s
between them — parsing all 502,652 disassembly lines across the five listings
once each is about 0.3 s of it, and hashing all 68 MB of Windows C is **0.05 s**.
See `docs/findings.md` §14 for why it used to read one of those files 10,141
times, and what it was parsing while it did.

The first version of the presence check cost **5.4 s** here, and the reason is
worth recording because it is §14a's shape at a second address: it built the
markers as a flat set of `(name, addr)` pairs and then asked
`any(a == addr for _n, a in markers)` per row — 10,141 rows against 10,141
markers. The markers are keyed on address now, so each row is a dict lookup.

`--self-test` pins that **structurally**, by reading the per-file container back
out of the module and asserting it is a dict keyed on address — not by wall
clock, which was tried first and is not a guard in either direction. The
quadratic form takes 0.18 s on this file's 2,000-row fixture, so it sits far
inside any bound loose enough not to be flaky on a loaded runner, while the real
regression was 5.4 s at 26× the work; a timing assertion here would have passed
the regression it was written to catch. Asserting the container catches it on any
machine, in milliseconds.

One `.c` is deliberately without a listing beside it:
`GamingCenter3_Cross.c`, the 56 MB retained decompile of the program in
`PROJECT_EXCLUDED`. It is named on every `--check` run rather than folded into
a pass — the `.asm` cannot be re-exported, because the Ghidra database that
would produce it is 337 MB and does not fit in git. It **is** digested, though:
it keeps the printed carve-out for the listing gap it genuinely cannot close,
and is checked rather than exempted for the thing that can be.

## The PDB, and its cost

`vendor/control-center-3.9.18.0/GamingCenter3_Cross.UWP_3.9.18.0_x64.appxsym`
is a zip holding a 144 MB `GamingCenter3_Cross.pdb` that matches the 27 MB
native `GamingCenter3_Cross.dll`. It is a **real, matching symbol source** — the
one the PDB is there for — and it was used here to *verify* two things, both
measured rather than guessed:

- **The analyzer you have to disable is `"PDB Universal"`.** There is **no**
  analysis option literally called "PDB Function Internals"; setting it is
  silently a no-op (Ghidra logs "could not be found for this program"). The
  pre-script `windows/ghidra/scripts/DisablePdbAnalyzer.java` tries both names
  and prints which one actually stuck, so this is not folklore.
- **The cost.** Even with `"PDB Universal"` disabled, importing this 27 MB
  binary **with** its 144 MB PDB did not finish within 30 minutes on this
  machine (the `analyzeHeadless` leg was still running past the 1800 s timeout).

So the PDB leg is **opt-in, not the default build**: by default
`decompile_native.py` decompiles `GamingCenter3_Cross.dll` **without** its PDB
(the binary is still fully decompiled; it just has no PDB-derived type names),
which is what the committed manifest reflects — its `pdb_staged` column reads
`no`, so a reader cannot mistake "no symbols" for "nothing there". Pass
`--pdb` to stage the PDB and run the separate, slow, long-timeout PDB import.
That flag's path is exercised by the pre-script but **has not been run to
completion here** (the >30 min leg above is why it is opt-in); treat the PDB
export as untested rather than as a known-good output. This is a stated,
deliberate trade — a real symbol source the default build chooses not to pay
for — not a silent omission.

The `PDB_TIMEOUT_S` bound is real: the driver runs each `analyzeHeadless` in its
own process group and SIGKILLs the whole group on timeout, because the headless
launcher is a shell wrapper around a `java` grandchild that a naive
`subprocess` timeout would leave running.

## What is excluded, and why

- **Managed (.NET) assemblies** are not here and must not be added:
  `GCUService.exe`, `M2Mqtt.Net.dll`, `SystrayComponent.exe`, `EnableTray.exe`,
  `Colourful.dll`, and the rest. Ghidra reads .NET *method names* from
  metadata and nothing more — on `GCUService.dumped.exe` it reports 400/400
  "decompiled" while every body is `halt_baddata()` / "Unable to resolve
  constructor". That is an artifact of the tool, not a property of the code.
  Managed code is `ilspycmd`'s job; see [`../../tools/extract.sh`](../../tools/extract.sh)
  and [`../../decompiled/`](../). The orchestrator refuses to import a managed
  assembly even if one is added to the CSV by mistake.
- **Third-party natives** that ship inside the same installer —
  `DiskInfo64`, `NVControlSetting`, `GPUInfoDLL`, `Microsoft.Graphics.Canvas`
  — are excluded on purpose: they are not the vendor's code, so decompiling
  them adds bulk without moving the mission. They are not "not found"; they
  were deliberately left out.

## Decompiler availability is checked, not assumed

Ghidra's native decompiler can fail open: `DecompInterface.openProgram()`
returns false with `getLastMessage()` equal to the **empty string**. That looks
identical to "this code will not decompile" and is not. The tool's postScript
distinguishes the two — an empty-message open failure is tagged
`DECOMPILER_UNAVAILABLE` and aborts the run; a genuine per-function failure is
just counted into that program's `failed` column.

## What is in the committed project, and what is not

Five of the six binaries are in `../../ghidra/project/`. `GamingCenter3_Cross.dll`
is not, and the manifest says so in a row of its own with `mode:
not-in-project`.

The reason is a hard limit, not a choice. Ghidra's analysis database runs to
roughly fourteen times the size of the image it holds — a 4 MB DLL is a 59 MB
buffer file. `GamingCenter3_Cross.dll` is 27 MB, and its buffer file alone is
**337,182,720 bytes**. GitHub rejects any file over 100 MB, so the push fails
on it, and the alternatives are Git LFS, which this repository does not use and
which a reviewer cloning it would then need, or not committing the project at
all and re-analysing 30 minutes of x86-64 on every annotation change.

The decompiled C for it *is* committed — 56 MB of text, which fits. So the
analysis is not lost; what is lost is the ability to re-derive it without an
import, and the tool says which import to run.

Measured, on this machine, with two annotation sweeps also running:

| binary | functions | decompiled | failed | project buffer |
|---|---|---|---|---|
| `ACPIDriver.sys` | 55 | 55 | 0 | 1.8 MB |
| `ACPIDriverDll.dll` | 10,141 | 10,141 | 0 | 59 MB |
| `clrcompression.dll` | 60 | 60 | 0 | 2.0 MB |
| `UEFI_Firmware.dll` | 407 | 407 | 0 | 1.3 MB |
| `GamingCenter3_Cross.exe` | 1 | 1 | 0 | 3.9 MB |
| `GamingCenter3_Cross.dll` | 64,591 | 64,588 | **3** | 337 MB — **not committed** |

The three failures are in the manifest and the index, not rounded away. The
PDB leg is opt-in behind `--pdb`; the manifest records `pdb_staged` per program
so "decompiled without symbols" can never be read as "decompiled".
