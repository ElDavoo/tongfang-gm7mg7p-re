# Shared Ghidra headless layer

Three components are reverse-engineered with Ghidra — the 8051 EC firmware,
the AMI/UEFI BIOS, and the Windows vendor binaries — and each has its own
committed project under `<component>/ghidra/project/`. What they share is
here: the scripts that seed a program, apply this repository's annotations
to it, and export the result. One implementation, because the provenance
header and the decompiler-availability guard must not exist in three places
that can drift.

| Script | Role |
|---|---|
| `scripts/SeedFunctions.java` | pre-script: disassemble and create functions at the seed addresses a spec file names, each with a `basis` saying why |
| `scripts/ApplyAnnotations.java` | post-script: apply function names, types, comments and XDATA labels from the annotation CSVs |
| `scripts/ExportDecompile.java` | post-script: decompile and write the C, the index rows, and the per-program counts |

Per-component drivers:

- `../ec/tools/build_ec_decompile.py` → `../ec/ghidra/README.md`
- `../bios/tools/bios_extract.py` → `../bios/ghidra/README.md`
- `../windows/tools/decompile_native.py` → `../windows/decompiled/native/README.md`

## The argument contracts

All three scripts take positional arguments, and the drivers build the files
they are given.

- `SeedFunctions.java <seed-spec.csv>` — header-only, columns
  `program,addr,basis`. Rows for other programs are skipped, so one spec
  drives a batched import of several programs. `basis` is one of `vector`,
  `vector-target`, `stub`, `call-target`, `annotation`; it survives into the
  index, because a function boundary that came from a byte-scan census is a
  hypothesis and a reader is entitled to know which boundaries are.
- `ApplyAnnotations.java <functions.csv|-> <xdata.csv|-> <report-dir>` —
  the report goes to `<report-dir>/apply-<program>.tsv`, one per program,
  because a batched run executes the script once per program and a single
  filename would leave only the last one's report. Pass `-` for a file that
  does not apply or does not exist yet.
- `ExportDecompile.java <outdir> <index.csv> per-function|per-program
  <context.txt> <seed-basis.csv|->` — appends tab-separated index rows and,
  per program, writes `<index.csv>.<program>.counts`. `<context.txt>` is
  `key=value` lines: `source`, `sha256`, `ghidra_version`, `generator`,
  `symbols`, `annotations`; they become the provenance header on every
  exported file.

## Two things to know before believing any output

**Ghidra's native decompiler can fail silently.** If the release was
unpacked by something that dropped the exec bit on
`Ghidra/Features/Decompiler/os/linux_x86_64/{decompile,sleigh}`, then
`DecompInterface.openProgram()` returns false and `getLastMessage()` is the
**empty string**. From the output alone that is indistinguishable from
"this function will not decompile" — the same failure shape as the
ConfuserEx anti-tamper trap in `windows/antitamper/README.md`.
`ExportDecompile.java` raises it as a loud, specific failure naming the
files to check, and the drivers preflight the exec bit before starting a
JVM. If you read a decompile failure anywhere in this repository, rule this
out before concluding anything about the firmware.

**Ghidra does not usefully decompile .NET.** It reports success and emits
`halt_baddata()`. It does read .NET method names from the metadata, so a
managed binary in a project is useful as a symbol and call-graph index, but
its C is not a decompilation. `ilspycmd` is the tool for managed code; see
`../windows/README.md`.

## The rule for agents

Improve a decompilation by editing a CSV under a component's
`annotations/`, never by hand-editing a `.gpr`, a `.rep` or a generated
`.c`. The CSVs review in a diff; the databases do not, and the next export
overwrites them. `CLAUDE.md` has the details.
