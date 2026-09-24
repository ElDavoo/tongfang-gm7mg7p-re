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

## Variables

`ghidra-variables.csv` is the same layer one level down: a hand-maintained
name for a **decompiler variable**, applied by the same script and regenerated
by the same build, so a `.c` comes out carrying it. Same conventions —
header-only, no comment lines, mandatory non-empty `evidence`, `basis` from the
same vocabulary.

**A separate file, not a column in this one.** A function's row *is* a function:
`build_ec_decompile.py`'s `annotation_seeds()` reads every row's `addr` as a
function seed, and `join_index()` keys one row per `(scope, addr)`. Eight
parameter rows for one function would inject eight seeds and overwrite seven
rows. Columns:

| column | |
|---|---|
| `scope`, `addr` | the **owning function's** entry address, same semantics as above |
| `key` | the decompiler placeholder being replaced — `param_1`, `cVar1` |
| `name` | `snake_case`; what the value is, from the listing. Empty only for `kind=unresolved` |
| `kind` | the controlled vocabulary, below |
| `comment` | why, concretely, and what is **not** decoded |
| `evidence` | mandatory, non-empty, the `.asm` first |
| `basis` | the same `hand-decoded` / `restatement` / `inferred` as above |

`kind` is a closed list: `param`, `local`, `return`, `artifact`, `unresolved`.

**Most of these are not parameters, and the closed list is why.** 45 rows in
`ghidra-functions.csv` already discuss a `param_N` by name, and in most the
prose concludes the placeholder is a decompiler artifact — `bank0,0x901C`'s
says "*param_1 is a pointer the decompiler invented, not a 8051 calling
convention*", and `bank1,0x8DBC`'s says "the decompiler's param_1 is the R7
result of 0x1984, not an argument passed in". A sweep that gave every
`param_N` a confident semantic name would manufacture false precision on
exactly the rows this repository has already flagged as misleading.

- `param` — a genuine incoming value. In the first batch this is a value
  arriving in **A**, the conventional 8051 argument register, and no further:
  Ghidra has no Keil C51 calling-convention model, so "arrives in A" is the
  whole of what the listing can say.
- `local` — a genuine local. Reserved; unused in the first batch, which is
  parameters only.
- `return` — the decompiler rendering a **callee's R7** as a parameter.
- `artifact` — the decompiler invented it: an uninitialised DPTR rendered as a
  pointer, or a scratch register (R1–R7) promoted to a parameter slot. Name it
  for what it actually is.
- `unresolved` — the listing does not say. **No name; the placeholder stays.**
  A result, not a failure, and exactly how `type=unresolved` behaves.

`unresolved` is not a hedge. Four rows in the first batch use it, and in each
the honest answer is that the identifier corresponds to nothing in the
instructions — `bank1,0xBD20`'s `param_1` exists only because the decompiler
split the listing's single `orl A,B` at 0xBD26 into two tests, and which of A
or B it is has not been established. Naming it anyway would be a confident
sentence about a register the code does not touch.

**The key is positional; the name is earned.** The key has to be positional —
it is how the script finds the variable — so all the weight is on `name`,
`kind`, `comment` and `evidence`. Naming by position (`param_1` → `local_1`)
produces something worse than `param_1`, because it looks finished.

### What the checks refuse

`build_ec_decompile.py --check` runs in CI and, for every row, requires the
committed `.c` at that `(scope, addr)` to contain the `name` as a whole word
**and** to no longer contain the `key`. That is bidirectional on purpose: a
typo'd name is not in the output, and a key the build has already consumed is
caught by the other half. It also refuses an empty `evidence`, a `kind` outside
the vocabulary, a `name` that is an EC XDATA register name (the variable layer
is not a back door for `registers.yaml`, and the PD image has its own XDATA
map), and a `kind=unresolved` row that carries a name anyway.

The scan is over the **code**, not the whole file. A function's own plate
comment is allowed to name the placeholder it is explaining — that sentence is
the reading, and it has to survive the rename it describes.

### The rebuild asymmetry, and why it is deliberate

An unmatched **function** row fails the build. An unmatched **variable** row is
reported and counted in the manifest, not fatal. A function row is keyed on an
address, stable forever; a variable row is keyed on a decompiler placeholder,
which `--mode rebuild-project` **consumes** — once the name is persisted into
the project, `param_1` no longer exists there, and rebuilding from the same CSV
would find nothing to rename. Making that an error would break a documented,
routine operation. Typos are caught by the `--check` above instead, which is
stronger: it measures the committed output rather than the script's say-so.

`ec/ghidra/manifest.csv` carries `variables_functions` (how many functions a
row decompiled — the cost), `variables_applied` and `variables_unmatched`, read
back from `apply-<program>.tsv`.

### A variable row may change a caller's arity, and that is a correction

The sibling rule to the one above, and the one an author is most likely to trip
over, because the effect lands somewhere they did not edit. **Applying a
variable row can change how many arguments a *caller* passes**: the signature
these rows drive is the one the call sites are then read against. The first
case was bank1 `0x9EA1` (rows 28-31 of the CSV), whose committed four-argument
signature dropped an argument at its call sites — and `bank1/E100.c` stopped
passing `DAT_EXTMEM_0390`, which was the XDATA census's only reference to that
byte, so `xdata_register_map.py`'s reference count fell by one and `0x0390`
left the census entirely.

The argument that went was not a parameter. `0x9EA1` reads R1, R3, R4, R5, R6
and R7 and never names R2, while the call site loaded `0x0390` into R2 and then
handed the **address** on as R3:R4 for the callee to read (`9EA1.asm:19`) and
write (`:43`). The fifth argument the decompiler used to promote was an
unconsumed scratch register. So the row corrected the decompile and the census
moved with it.

Three things follow, and all three are about how to read a count:

- **A C-level reference count is a lower bound on the machine code.** The
  census matches `DAT_EXTMEM_xxxx` tokens and symbol names, so it cannot see an
  address the decompiler spells as arithmetic or over register names — here as
  `CONCAT11(r4_value,r3_value)`. Do not read a lower count as fewer accesses.
- **A pin moves only with a measured reason recorded in the same change.**
  Re-run `--check`, take the number the tool reports, and say in the commit
  which way it moved and why. Issue #259 did exactly this: naming the byte
  (`XDATA_0390`) and re-running the export in default mode moved no `.c` and no
  `manifest.csv` row, so the pins did not move.
- **An address that leaves the census is "not found by this method"** until an
  `.asm` witness says otherwise — never "absent". `xdata_register_map.py
  --self-test` now pins that witness for `0x0390`, asserting the site in the
  `.asm` and the absent census row together so the two cannot drift apart.

Renaming *without* committing the signature was considered and rejected: it
would trade a correct decompile for a stable number and put a claim the `.asm`
contradicts into every future export. The address-by-address account is
`xdata-register-map.md` §7.1; `ghidra/scripts/ApplyAnnotations.java` carries
the same rule where the effect happens, and `docs/findings.md` §18 has it in
the findings record.

### The first batch

60 rows across 46 functions: every function whose existing `hand-decoded`
comment already names a `param_N`, which is a measurable boundary rather than a
round number, plus `bank0,0x0EA2` — the worked example the variable layer was
built and proved on. Transcribing those comments is neither guesswork nor
duplicated effort: the ground truth was already written, already cited, and in
most cases already says the C misleads.

39 `artifact`, 11 `return`, 5 `param`, 4 `unresolved`. The sweep's
orchestration is not automated — the shard/author/verifier loop is driven by
hand, exactly as the function sweep's is — but
`../tools/merge_annotation_shards.py --csv-kind variables` runs it, and refuses
the same seven things it refuses for functions.

**Left for follow-ups**, sized by *declarations* rather than mentions, because
a mention count is not the size of the job: the export holds 8,605 `param_N`
mentions across 2,232 declared parameters, and it is the 2,232 that have to be
read. After this batch about 2,170 parameters are unnamed, and the 1,725
declared locals are blocked behind the XDATA map — 1,099 distinct
`DAT_EXTMEM_NNNN` addresses appear in the export and the symbol layer names 7
of them, so a local that mirrors an unnamed register cannot honestly be named
before the register is. (Measured over the committed export; a regeneration
that renames a symbol moves the mention counts, which is why the declaration
counts are the ones quoted here.)

## Adding a row by hand

Append it, with an `evidence` path, and re-run the build:

```
python3 ec/tools/build_ec_decompile.py --work /tmp/ec
```

The default mode copies the committed project to scratch and exports from the
copy, so the `.rep` is never opened for writing and an annotation change is a
one-line CSV diff rather than a 7 MB binary one. Only `--mode rebuild-project`
writes the project, and two branches that both rebuild one cannot merge.
