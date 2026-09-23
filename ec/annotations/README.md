# Function annotations

`ghidra-functions.csv` is the editable layer over `../decompiled/`. One row per
function: a name, a type, a sentence or four about what the code does, and a
citation for where that reading came from. `../tools/build_ec_decompile.py`
applies the rows to a copy of the project and re-exports, so a `.c` and its
`.asm` come out carrying the name and the comment.

**Never hand-edit a `.c` or an `.asm`.** They are generated, a rename churns a
file path, and the next build overwrites both. `CLAUDE.md` has the rule and
`../ghidra/README.md` has the method.

## The format

Header-only, no comment lines, so `csv.DictReader` reads it — the convention
`../README.md` sets out. Columns:

| column | |
|---|---|
| `scope` | `bank0`, `bank1`, `pd`, or `common` for a function in `0x0000-0x7FFF` that both bank programs carry identically. A common-area function is exported once, so its address is in no bank row: a `bank0`-scoped row for one is a scope rename, not a typo |
| `addr` | the function's entry address |
| `name` | `snake_case`, describing the behaviour |
| `signature` | recorded in the plate comment, **never applied**. Ghidra has no Keil C51 calling-convention model, so an applied prototype on 8051 code would be a guess sitting where a fact reads |
| `type` | the controlled vocabulary, below |
| `comment` | what the code does, concretely |
| `evidence` | mandatory, non-empty, `; `-separated repo paths |
| `basis` | `hand-decoded`, `restatement`, or `inferred` |

`type` is a closed list: `entry init dispatch forwarder gate reader writer copy
math logic serial sbi ec-io state delay bank-switch unresolved`, plus
`charge-target` for the hand-written charge-target rows and `module-entry`,
`gpio-pad`, `nvram-write`, `pcr-read`, `pch-select` where those apply.

**`unresolved` is a result, not a failure.** A function whose role cannot be
determined is correctly described as far as the bytes go and no further.
Filling that gap with a plausible name is the one thing a row must never do,
and `unresolved` is in the vocabulary so that saying so costs nothing.

`basis` distinguishes reading the machine code from reporting the decompiler's
opinion of it. A decompilation is one reading of the bytes; calling it
`hand-decoded` when the `.c` is all that was read is the overclaim this
repository's rules are about.

## The checks

`build_ec_decompile.py --check` runs in CI and refuses:

- a row with an empty `evidence` cell — a claim, not a finding;
- a row whose `(scope, addr)` resolves to no exported function — a typo, or a
  sign the project needs `--mode rebuild-project`. Say which; do not let a
  stale annotation outlive the thing it named;
- a manifest function count the index no longer accounts for. The manifest
  carries what the exporter measured before de-duplication, and the index what
  survived it, so a row that vanishes between the two is caught. It used not
  to be, which is how the PD image's `0x0012` went missing: the row and the
  files it named were deleted together, so every file-existence check still
  held.

## How the bulk rows were produced

The first 67 rows were written by hand. The rest came from a fan-out, and the
process is recorded because the result is only as good as it:

1. **Slice.** `ec/decompiled/index.csv` minus everything already annotated,
   grouped by program and address into shards of ~30 neighbouring functions, so
   an agent sees the code around a function and not just the function.
2. **Annotate.** One agent per shard reads each function's `.asm` *and* its
   `.c` and writes one CSV row per function. The `.asm` is the ground truth;
   the `.c` is one reading of it.
3. **Verify.** A second agent, seeing only the shard's CSV and the same
   listings, decides row by row whether the instructions support the comment.
   Reject only a factual problem — a register the listing does not touch, a
   mechanism with no documented register behind it, an operation the
   instructions do not contain. `unresolved` rows and comments that say what
   is *not* decoded are correct outcomes and are approved.
4. **Merge.** `../tools/merge_annotation_shards.py` applies the mechanical
   rules and the verifier's whitelist, and refuses a row that resolves to no
   function, duplicates an address, has an empty required field, carries a type
   outside the vocabulary, cites no path, or **names a register its own `.c`
   and `.asm` do not mention**. That last one is the calibrate-don't-overclaim
   rule made mechanical: at two thousand rows a single unsupported address is
   invisible, and a gate that only checks the cell is non-empty accepts it.

   The register rule is scoped to the words that name a memory space
   (`XDATA`, `EXTMEM`, `CODE`, `register`, …). An earlier version flagged every
   4-hex-digit run and rejected 535 of 967 rows for naming `0xFFFF` in
   sentences like "lies in the 0x8000-0xFFFF banked CODE window", which is
   about the memory map and not about the function. An address the function
   does not have is accepted when a neighbouring function or a callee the
   comment names establishes it, because Ghidra's boundaries on this firmware
   cut through straight-line code and a function that delegates its register
   work is making a true claim about a register in the callee.

5. **Disambiguate.** Two agents naming two different functions the same thing
   is usually right — several one-instruction `ret` stubs really are the same
   routine — but the name then does not identify a function, so it takes the
   low 16 bits of the address: `ret_only_8000`, not `ret_only_1`. Only swept
   rows are renamed; a name a person wrote is what everything else defers to.

`../tools/merge_annotation_shards.py --self-test` covers nine cases that must
be rejected and one that must survive, and CI runs it: a check that has
quietly stopped rejecting anything looks exactly like a check that is working.

## Adding a row by hand

Append it, with an `evidence` path, and re-run the build:

```
python3 ec/tools/build_ec_decompile.py --work /tmp/ec
```

The default mode copies the committed project to scratch and exports from the
copy, so the `.rep` is never opened for writing and an annotation change is a
one-line CSV diff rather than a 7 MB binary one. Only `--mode rebuild-project`
writes the project, and two branches that both rebuild one cannot merge.
