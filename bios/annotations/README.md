# BIOS Ghidra annotations

`ghidra-functions.csv` is the editable layer over `bios/decompiled/`. A row
here names a function, says what it is for, and cites where that reading came
from; the build turns the rows into function names and comments in the Ghidra
project and into the generated `bios/decompiled/<Module>.annotated.c`. Editing
a `.c` by hand achieves nothing, because the next build overwrites it; a
one-line diff in this file is the whole improvement, and it is reviewable.

Same shape as `ec/annotations/ghidra-functions.csv`, header-only so
`csv.DictReader` reads it, and consumed by the same shared
`ghidra/scripts/ApplyAnnotations.java`.

## The columns

`scope,addr,name,signature,type,comment,evidence,basis,name_basis`

| column | what goes in it |
|---|---|
| `scope` | the Ghidra program name, i.e. the module: `OemOcDxe`. `ApplyAnnotations.java` compares on the file-name stem, so `OemOcDxe` matches a program Ghidra calls `OemOcDxe.efi` |
| `addr` | the function entry, in the module's own address space: an RVA for a PE32 module, an execute-in-place address for a TE one |
| `name` | the function name to apply. Empty leaves Ghidra's name alone |
| `signature` | recorded in the plate comment, **not** applied to the function's type system — see below |
| `type` | what kind of thing this is, from the vocabulary below |
| `comment` | the reading. One line: `ApplyAnnotations.java` reads the file a line at a time, so an embedded newline would be read as a short row and fail the build |
| `evidence` | mandatory, non-empty. A repo path, or several separated by `, `. An annotation without one is a claim, not a finding, and the build rejects it |
| `basis` | where the name came from, from the vocabulary below |
| `name_basis` | what the **name** asserts rests on — see below |

Two of the columns above count differently on purpose, and the difference is
not a bug. `index.csv`'s `annotated` says whether a function ended up with a
name that is not one of Ghidra's placeholders; the manifest's
`annotations_applied` counts rows that resolved to a function. A row with an
empty `name` resolves but renames nothing, so the two differ by the number of
nameless rows. Today that is two (`0x3D0` and `0x3EC`), so `OemOcDxe` shows 15
applied and 13 renamed.

## `basis`

| value | meaning |
|---|---|
| `hand-decoded` | a person read the disassembly, and the cited file records the reading |
| `inferred` | a reading. The export and the generated `.annotated.c` both say so next to it, which is the marker `bios/decompiled/OemOcDxe.annotated.c` has used since it was hand-written |
| `ghidra` | the name is what the bytes say; nothing is being claimed |

`inferred` is not decoration. A name that hardens into a fact is the failure
CLAUDE.md puts above every other rule, so the marker travels with the row into
`ApplyAnnotations.java`'s plate comment and into the generated file.

## `name_basis`

`basis` is about the provenance of the **comment**. `name_basis` is about the
epistemic footing of the **mechanism the name asserts** — a different axis, not
a rename, and the reason both columns exist. `bios_extract.py --check` holds
this file to the same closed vocabulary and the same four cross-field rules as
`ec/annotations/ghidra-functions.csv`, and imports them from
`ec/tools/grade_name_basis.py` rather than restating them, so the two files
cannot come to mean different things.

| value | the mechanism rests on |
|---|---|
| `register-map` | a decoded architectural register identity — a control register, an MSR, a PCI config port |
| `ec-register` | an XDATA address in the EC's `registers.yaml` — a BIOS row that names one is making a claim about the EC register map |
| `abi-symbol` | an EDK II type or protocol symbol rather than the bytes — `EFI_*`, a `g*Guid`, a protocol interface |
| `code-shape` | only the instruction sequence's shape |
| `mixed` | the name asserts two things with different footing |
| `unresolved` | the row is `type: unresolved` and the name is a placeholder claiming nothing |

**The grading rule is deliberately asymmetric: the strongest footing actually
traceable to a committed input, else `code-shape`.** The default points at the
weak end on purpose — grading by name-regex would overclaim, and grading the
other way would under-claim, which is its own inaccuracy. The rule is stated
rather than left in the tool so a later reader can re-derive any row and get
the same answer; `--report` prints the distribution over both files.

Measured over the 788 rows here: 729 `code-shape`, 43 `abi-symbol`, 9
`register-map`, 6 `unresolved`, 1 `mixed`.

## Groups: [`function-groups.csv`](function-groups.csv)

One row per annotated function — `scope,addr,group,group_basis,comment,
evidence` — and the layer `ghidra-functions.csv` does not have: which
functions work together. `group_basis` is closed: `type`, `vector`, `module`,
`callgraph`, `shared`, `ungrouped`.

**The BIOS is the module-first case, and it is nearly free.** 666 of the 788
rows are `group_basis=module`: the export is per-module and the module name is
a real structural layer, which is the better starting point the issue says
this side has. The remaining 122 come from the `type` column, the same way the
EC's are seeded. `ec/tools/group_functions.py` builds both files and `--check`
holds them.

**The no-cross-bank rule is a BIOS no-op, and it is kept anyway.** Nothing in
an `lcall` names a bank, so the EC side never joins bank0 to bank1; a UEFI
module's address space has no equivalent ambiguity, but a check that existed
on only one side of a vocabulary would be a rule meaning two different things.

**No group is a behavioural claim.** A module is where code lives, not what it
does. No hardware is reachable from a GitHub-hosted runner, so no live test is
claimed here.

## `type`

Not a machine-readable enum — nothing filters on it yet — but a controlled
vocabulary, so two rows describing the same kind of thing say the same word.
The BIOS values:

| value | what it means |
|---|---|
| `module-entry` | the routine a module's `entry` dispatches to, and the module's top-level behaviour |
| `nvram-write` | reads and writes UEFI variables (setup stores, `UniWillVariable`) |
| `gpio-pad` | touches a PCH GPIO pad, one way or another |
| `pcr-read` | reads a pad's ownership bits out of a PCR |
| `sbi` | a P2SB sideband transaction |
| `ec-io` | one of the ACPI-EC port helpers |
| `pch-select` | picks the H or -LP PCH table from the 00:1F.0 device ID |

## `signature` is recorded, not applied

`ApplyAnnotations.java` writes the signature into the function's plate comment
and does not touch the function's type system. That is deliberate and it is
also true on x86, where Ghidra *does* have a calling-convention model: these
are UEFI module binaries, not a program with a consistent prototype discipline,
the argument lists below come from a decompiler's stack-layout recovery, and a
wrong prototype applied to a function changes what the decompiler prints about
every caller. The text still reaches the export, where a human can act on it.

## The two build modes

Both are entry points on `bios/tools/bios_extract.py`; `bios/ghidra/README.md`
is the longer version.

```
# export-only (the default): copy the committed project, apply this CSV to the
# copy, re-export bios/decompiled/ and the .annotated.c files. The committed
# .rep is never opened for writing, so an annotation change is a CSV diff and a
# text diff. Needs neither UEFIExtract nor the ROM's module bodies.
python3 bios/tools/bios_extract.py --work /tmp/bios

# rebuild-project: re-import all 38 modules from the committed ROM and write
# bios/ghidra/project/ and bios/ghidra/load-map.csv. Rare -- a new module, a
# changed seed, or someone improving the project's own symbol table -- and it
# runs UEFIExtract, whose cost on this ROM is not predictable.
python3 bios/tools/bios_extract.py --work /tmp/bios --mode rebuild-project
```

## What is in here today

Fifteen rows, all `OemOcDxe`, transcribed from the hand-written
`bios/decompiled/OemOcDxe.annotated.c`.

- Ten carry a name the restatement asserts: `OemOcDxeMain` (0x4F8),
  `MemOcGpio` (0x5D8), `OcRecovery` (0x67C), `SyncOcVariables` (0x7A8),
  `PadOwnership` (0xC30), `SbiClearLockTx` (0xD2C), `SbiSetLockTx` (0xD80),
  and `IsPchLp` (0x1158), which the restatement asserts with a name that does
  not describe its return value — see the row's comment, which says so.
- Two carry an address and no name: the module entry (0x3D0) and the library
  constructors (0x3EC). The restatement names both in prose and gives them no
  symbol, so the row records the address and the reading and leaves Ghidra's
  name alone. An empty `name` is a normal value, not an oversight.
- Four name the ACPI-EC port helpers (0xDD4, 0xE4C, 0xED4, 0xF38) that the
  restatement describes as a group — "EC access (FUN_00000f38 / FUN_00000dd4
  / FUN_00000e4c / FUN_00000ed4)" — without naming individually, and one names
  0x119C, which the restatement labels `/* 0x119C */` and leaves unnamed.
  These five are new readings, so their `basis` is `inferred` and they are not
  in the restatement yet.

Because the restatement is hand-written and this file is transcribed from it,
the `evidence` column points at a file that is independent of it. That is the
point of the column.

## The drift guard

Two copies of one reading, kept side by side, can diverge. `bios/tools/
bios_extract.py --check` reads the function addresses each
`decompiled/*.annotated.c` names and fails if this file has no row at one of
them; and it fails the other way if a row marked `hand-decoded` — which means
the restatement records that reading — names something the restatement no
longer mentions. `inferred` rows are exempt from the second direction, because
a new reading is in no restatement by definition.

So: improve a reading in `OemOcDxe.annotated.c`, transcribe the change here in
the same commit, and `--check` will say so if one of the two is left behind.
The guard needs neither Ghidra nor the network.
