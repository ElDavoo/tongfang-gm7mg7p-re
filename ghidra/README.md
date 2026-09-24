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
| `scripts/TongFang.java` | not a script: the context-file contract, the export-identity rules, the RFC4180 CSV split, Ghidra's function- and variable-placeholder lists, and the decompiler-availability guard, shared so they cannot drift |
| `scripts/SeedFunctions.java` | pre-script: disassemble and create functions at the seed addresses a spec file names, each with a `basis` saying why |
| `scripts/ApplyAnnotations.java` | post-script: apply function names, types, comments, XDATA labels and variable names from the annotation CSVs |
| `scripts/ExportDecompile.java` | post-script: decompile and write the C, the index rows, and the per-program counts |
| `scripts/ExportListing.java` | post-script: write the **disassembly** beside the decompile, and its own index rows |

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
- `ApplyAnnotations.java <functions.csv|-> <xdata.csv|-> <report-dir>
  [<variables.csv|->]` — the report goes to
  `<report-dir>/apply-<program>.tsv`, one per program, because a batched run
  executes the script once per program and a single filename would leave only
  the last one's report. Pass `-` for a file that does not apply or does not
  exist yet. The **fourth** argument is the variable layer, columns
  `scope,addr,key,name,kind,comment,evidence,basis`, where `key` is the
  decompiler placeholder being replaced; the EC driver passes
  `ec/annotations/ghidra-variables.csv` and the other two pass `-`, because a
  row in it is a reading of an 8051 decompiler's placeholder. The report gains
  `variables_functions` (how many functions a row decompiled — the cost),
  `variables_applied` and `variables_unmatched`.

  Three arguments is still accepted, so a driver that has not been updated
  keeps working; the variable layer is simply absent. Both the EC and BIOS
  drivers pass four.

  A variable row that matches nothing is **reported and counted, not fatal** —
  the opposite of a function row, and deliberately so. A function row is keyed
  on an address, stable forever. A variable row is keyed on a decompiler
  placeholder, which `--mode rebuild-project` **consumes**: once the name is
  persisted into the project, `param_1` no longer exists there, so rebuilding
  from the same CSV finds nothing to rename. Making that an error would mean a
  documented, routine operation breaks the build. A typo is caught instead, and
  more strongly, by the EC driver's `--check`, which measures the committed
  `.c` rather than the script's own say-so.
- `ExportDecompile.java <outdir> <index.csv> per-function|per-program
  <context.txt> <seed-basis.csv|->` — appends tab-separated index rows and,
  per program, writes `<index.csv>.<program>.counts`. `<context.txt>` is
  `key=value` lines: `source`, `sha256`, `ghidra_version`, `generator`,
  `symbols`, `annotations`; they become the provenance header on every
  exported file.
- `ExportListing.java` — the same five arguments and the same index columns,
  but it writes the instruction listing rather than a decompilation. It has no
  decompiler dependency at all, so it cannot fail the way `ExportDecompile`
  does.

## The disassembly beside the decompilation, and why

Every component ships two files per function (or per module, in the BIOS's
per-program shape): `<addr>.c` and `<addr>.asm`, plus a `listing-index.csv`
that names the `.asm` for the same rows `index.csv` names the `.c`.

The `.c` is a **reading** of the bytes. The decompiler decided what they mean
and the reader is shown only its conclusion, which is the right default for
breadth and the wrong default for trust: a wrong reading is indistinguishable
from a right one in the output. The `.asm` is the other half of the same fact,
so any claim in a `.c` can be checked against the code that produced it, and
an annotation row can cite instructions instead of citing a tool's opinion of
them.

They are one file in two senses and two files in another: same function, same
address, same index row — and `--check` refuses an export where either half is
missing, because a `.c` with no `.asm` is a reading with nothing to check it
against, and a listing row pointing at a missing file is staleness the C index
cannot see.

Format is objdump's, on purpose:

```
11A4     90 bf 2a   mov      DPTR, #0xbf2a
11A7     02 11 00   ljmp     0x1100
```

`addr  bytes  mnemonic  operands`, `;` for comments. A second, machine-only
format would be a second thing to keep in step, and nothing here needs one.

## The 1:1 property, and what it does and does not mean

`ec/tools/verify_reassembly.py` re-encodes the committed EC disassembly with
`sdas8051` (SDCC's assembler) and compares the result to
`ec/firmware/GMxMGxx_11.800`. Ghidra's SLEIGH decodes; an assembler that never
saw the firmware encodes; the firmware arbitrates. That check can fail, and
when it did it was the translation that was wrong four separate times — the
number below is only meaningful because of that.

**It is a claim about the machine code, not about the C.** The decompiler is
not in the loop: not read, not compared. A decompilation can be wrong and this
check still passes, which is correct — `ec/decompiled/*.c` is a claim about
what the machine code means, and a reading is not something a compiler can be
asked to reproduce byte for byte. What *is* reproducible is the disassembly,
and that is what the check establishes.

What is **not** claimed: that a compiler can be pointed at the readable C and
emit the firmware. Keil C51 generated these bytes, SDCC does not emit Keil's
code generation, and no amount of annotation changes that. The honest phrasing
is the one above — the ground truth is held in a form that regenerates the
binary, and the readable layer sits on top of it with a checkable
correspondence. See `ec/ghidra/README.md` for the measured numbers and
`docs/findings.md` §11 for what the check found on the way.

## Two things to know before believing any output

**Ghidra's native decompiler can fail silently.** If the release was
unpacked by something that dropped the exec bit on
`Ghidra/Features/Decompiler/os/linux_x86_64/{decompile,sleigh}`, then
`DecompInterface.openProgram()` returns false and `getLastMessage()` is the
**empty string**. From the output alone that is indistinguishable from
"this function will not decompile" — the same failure shape as the
ConfuserEx anti-tamper trap in `windows/antitamper/README.md`.
`TongFang.openDecompiler()` raises it as a loud, specific failure naming the
files to check, and the drivers preflight the exec bit before starting a
JVM. If you read a decompile failure anywhere in this repository, rule this
out before concluding anything about the firmware.

The guard lives in `TongFang.java` and not in the script that needs it,
which is the point of that file. It used to sit in `ExportDecompile.java`
alone — the file that exists so the check cannot drift did not have the
check, and `ApplyAnnotations.java` now opens a decompiler of its own and
would have carried a second copy. Any script that opens one calls
`TongFang.openDecompiler()`.

**Ghidra does not usefully decompile .NET.** It reports success and emits
`halt_baddata()`. It does read .NET method names from the metadata, so a
managed binary in a project is useful as a symbol and call-graph index, but
its C is not a decompilation. `ilspycmd` is the tool for managed code; see
`../windows/README.md`.

## Two ways a Ghidra invocation fails without saying so

Both of these cost real time here, and both look like something else.

**A repeated `-scriptPath` replaces the first, it does not accumulate.** Passing
`-scriptPath <shared> -scriptPath <windows>` leaves only `<windows>` on the
search path, so the shared post-scripts come back "Script not found" and
headless aborts with a non-zero exit. It is easy to believe otherwise,
because a test that only runs a script from the *second* directory passes
perfectly. Join them into one flag instead: `-scriptPath "<shared>;<windows>"`.
The separator is `;`; `:` is not split and silently leaves one path.

**A Ghidra install can lack a working decompiler and still look fine.** See
below — it is the same failure the ConfuserEx trap produces.

## The rule for agents

Improve a decompilation by editing a CSV under a component's
`annotations/`, never by hand-editing a `.gpr`, a `.rep` or a generated
`.c`. The CSVs review in a diff; the databases do not, and the next export
overwrites them. `CLAUDE.md` has the details.
