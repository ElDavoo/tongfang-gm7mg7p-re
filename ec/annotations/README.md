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
| `name_basis` | what the **name** asserts rests on — see below |

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

## `name_basis`, and why it is not `basis`

`basis` is about the provenance of the **comment**. `name_basis` is about the
epistemic footing of the **mechanism the name asserts** — a different axis, not
a rename, and the reason both columns exist.

A name in this repository makes a claim. `load_dptr_88f0_tail_jump_1114` is a
true description of two instructions; `timer1_counted_delay_using_0a56` asserts
that a routine waits on Timer 1 overflow. Before this column nothing recorded
what the assertion rests on, so a name decoded from a register map read exactly
like a name guessed from instruction shape. `docs/findings/name-basis-and-groups.md`
has the account; §20 of `docs/findings.md` is the summary.

| value | the mechanism rests on |
|---|---|
| `register-map` | a decoded SFR/bit identity — 0x8E is TCON.6 = TR1. Checkable against `../tools/disasm8051.py`'s `bit_name()` and `BIT_SFR` |
| `ec-register` | an XDATA address in `registers.yaml` carrying a decoded name/status |
| `abi-symbol` | a toolchain or ABI symbol rather than the bytes — the BL51 bank-select stubs. The token must be in the **name**; a comment's mention of one is a claim about the comment |
| `code-shape` | only the instruction sequence's shape |
| `mixed` | the name asserts two things with different footing |
| `unresolved` | the row is `type: unresolved` and the name is a placeholder claiming nothing |

### The grading rule, which is deliberately asymmetric

**Strongest footing actually traceable to a committed input, else
`code-shape`.** The default points at the weak end on purpose. Grading by
name-regex would overclaim — a name containing `write` is not thereby grounded
in a register map — and grading the other way would under-claim, which is its
own inaccuracy.

It is stated here rather than left in the tool so **a later reader can
re-derive any row and get the same answer**, and
[`../tools/grade_name_basis.py`](../tools/grade_name_basis.py) implements
exactly this: it reads the row's own committed `.asm`, not its name, and
`--check` re-grades the committed column and fails on any disagreement.

Three consequences worth knowing before editing a row:

- **The listing is the discriminator, not the number.** `clr 0x8E` is a bit
  operand and `mov DPTR,#0x0080` is an XDATA byte, and a name saying `0x80`
  could be either. Only the committed bytes decide.
- **A name may assert an SFR in words.** `timer1_counted_delay_using_0a56`
  never writes `0x8E`, but "timer1" *is* a claim about TCON.6 = TR1. A rule
  keyed on hex literals alone grades it `code-shape` and loses the decode, so
  the grader recognises the word and corroborates it against the listing the
  same way.
- **A comment cannot supply the footing, for `abi-symbol` any more than for
  `register-map`.** `load_dptr_88f0_tail_jump_1114` is a true description of
  two instructions; a comment noting that Ghidra names 0x1114
  `bl51_bank_select_1` does not turn the name into an ABI citation, and a grade
  a prose comment can hand out is unfalsifiable in the same way rule 4 is
  about. The token has to be in the name. Four rows carry it — the
  `bl51_bank_select_N` stubs — and they are all of the `abi-symbol` population
  in the EC.

### What the checks refuse

`build_ec_decompile.py --check` runs in CI and adds four cross-field rules
beside the `evidence` guard, all four imported from `grade_name_basis.py` so
the tool that writes the column and the tool that checks it cannot disagree:

1. an empty `name_basis`, or one outside the vocabulary;
2. a row graded `ec-register` citing no address `registers.yaml` carries;
3. **a `pd`-scoped row graded `ec-register`** — the PD image is a separate
   8051 program with its own XDATA map, so a `MOV DPTR,#0x07E2` there is not a
   reference to the EC register at 0x07E2. This is the third lock on that door
   (`../tools/gen_xdata_symbols.py` never emitting pd rows, and
   `ghidra/scripts/ApplyAnnotations.java` refusing to apply one, are the
   first two), and it fires *independently* of rule 2: a pd row naming an
   address that is in the map would pass rule 2 and still be an overclaim.
4. a row graded `register-map` naming no address `bit_name()` decodes and no
   SFR in `BIT_SFR`. Rule 4 reads the **name, not the comment**, deliberately:
   a comment may discuss a decoded bit anywhere, and grading on it would make
   the grade unfalsifiable.

`bios_extract.py` holds the BIOS CSV to the same four rules, including the
`pd` rule, which cannot fire there — the BIOS has no PD image. It is carried
anyway because a rule that exists on only one side of a vocabulary is a rule
that means two different things.

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

It also passes over [`subsystems.md`](subsystems.md), the map from mechanism to
function, and refuses a citation there that resolves to no row of this file, one
whose `name` disagrees with the row's current name, a `type: unresolved` row
cited without the `[unresolved]` marker, and a census count that disagrees with a
recount.

## Groups: [`function-groups.csv`](function-groups.csv)

One row per annotated function — `scope,addr,group,group_basis,comment,
evidence` — and the layer `ghidra-functions.csv` does not have: which
functions work together. `../tools/group_functions.py` builds it and
`--check` holds it, refusing a `group_basis` outside the closed list
(`type`, `vector`, `module`, `callgraph`, `shared`, `ungrouped`), an annotated
function with no group, an **`evidence` path that is not on disk**, a
**`callgraph` name whose scope token is not its component's dominant scope**,
and a **`callgraph` group spanning two banks**.

The `evidence` guard is the one `build_ec_decompile.py` already applies to
`ghidra-functions.csv`, and it is here for the same reason: the group row
copies its citation from the annotation row, and this is the layer a reader
traces a group back through, so a citation that resolves to nothing is a dead
end in the one place the trace is meant to be followable. The separator is
load-bearing, which is how fifteen `OemOcDxe` rows read before the check
existed: a cell written `a.annotated.c, a.c` is one path, and one that is not
on disk. Nothing caught it, because nothing asked whether a path resolved.

**The banking caveat is the rule that matters here, and it is inherited from
[`audit_call_targets.py`](../tools/audit_call_targets.py) without
softening.** Nothing in an `lcall` names a bank — bank0→bank1 and bank0→bank0
are the same three bytes — so the tool never joins bank0 to bank1. The rule is
structural rather than a filter applied afterwards: the union never sees a
cross-region edge, so there is no cluster to reject later. Cross-region edges
are counted and reported (27 at the time of writing), never merged, and every
run prints the A/B/C populations so a small group count cannot read as a
topology.

**"Never sees a cross-region edge" needed a node as well as an edge, and the
node is a per-region proxy.** A `common`-scoped row is one function both bank
images carry, so a bank0 caller and a bank1 caller that both reach it are two
halves of *one* node, and joining them is a cross-region join however sound each
edge is. `PROXY_SCOPE` in `group_functions.py` gives each region its own
endpoint for a common-area target, so the callers that share a helper stay
connected inside their own bank and the banks are not. This is a correction, not
a design change: `--check` refused a 673-row component spanning both banks once
issue #134's tranche annotated 33 more of the common area, and the refusal was
right. `cluster()` carries the argument and `--self-test` carries a fixture for
it.

**A `callgraph` group is a connected component, not a subsystem.** The largest
holds 327 of the 1,848 rows. That is a real structural fact and a poor
subsystem boundary, so the groups are named `callgraph_<scope>_<addr>`, their
size is in each row's comment, and `--report` names any component of 50 or more.
The seeds — the `type` column, the interrupt table, and on the BIOS the module
— are the part of the layer that says what a group is *for*.

**The `<scope>` in that name is the component's dominant scope**, which is not
the same as its first member's: a component can hold rows from more than one
scope, because the common area is reachable from any bank. Naming it after the
first member described whichever row the union-find emitted first, and four of
the nineteen names were wrong that way — a 323-row component that is 316 bank1
rows read `callgraph_bank0_1803`, and a 145-row component that is 144 `pd` rows
read `callgraph_common_0EF3`. That second one is the sharp case: it hands a
reader 144 rows of the separate ITE8850-PD program under the token `common`,
which is the same conflation the `pd` grade rule above exists to prevent,
reintroduced through the naming layer. `--check` now refuses a `callgraph`
name whose scope token is not the dominant scope among the rows carrying it.

The three components of 50 or more on the committed tree are
`callgraph_bank0_0EA2` (327, all `bank0`), `callgraph_bank1_1738` (321, all
`bank1`) and `callgraph_pd_0003` (303, all `pd`). Every one being a single
scope is the visible consequence of the proxy correction: the separate
ITE8850-PD program's 187 clustered rows were two pieces that the shared common
node had been holding apart, and they are one of 303 now.

456 rows are `ungrouped`: no seed and no component at or above the minimum
size. That is *not found by this method*, never "these have no subsystem", and
`ungrouped` is in the vocabulary so saying so costs nothing. (576 when this was
written: issue #134's 44 rows took 26 out and the proxy correction took 94
more.) **16 of the 456 were found by the method and cut by the proxy rule**,
which is a different reason and says so in their comments and in `--report`'s
split line — see
[`docs/findings/group-proxy-populations.md`](../../docs/findings/group-proxy-populations.md).

**Which caller scopes reach a `common` row is recorded on the branch that
actually ends there, because a shared address is two functions.**
`cluster()` used to record a caller's scope against the `common` row at a
target address before it decided whether the edge was a same-scope join or a
proxy. For `common`→`common` that is right — both ends are `common`, so the
edge is joined directly but the row was still reached from outside the banks.
For a `pd` caller whose target also exists as a **`pd`** row it is not: the join
takes the `pd` row, and `ec/decompiled/pd/0C7A.asm`
(`mul_r7_r5_r4_into_r6r7`) is a different function from
`ec/decompiled/common/0C7A.asm` (`clear_low_nibble_of_1304`) because the
ITE8850-PD image is a separate program with its own address space. Nine
addresses carry rows from both, and `reached_only_by_bank` is a subset test
that only separates the two behaviours once a bank caller is on the same row —
which is why the `--self-test` fixture has one. **No published figure moves**:
the 26, the 196, the 36 targets and the 115/81 split are identical before and
after, because no `common` row a `pd` caller reaches is also reached by a bank
caller on this tree. `common 0x11C2`, which has no `pd` row beside it, keeps its
real `pd` reach. See
[`docs/findings/pd-common-address-attribution.md`](../../docs/findings/pd-common-address-attribution.md).

**No group is a behavioural claim.** A group says which routines are connected
in the call graph, not what the EC does with them. No hardware is reachable
from a GitHub-hosted runner, so no live test is claimed here.

The same pass refuses an `evidence` path that is not on disk, and it reads
**every row of this file**, not only the ones the map cites: the citation list
is the map's selection, and a row it happens not to quote is exactly where a
stale path can sit unseen. Eleven rows here were citing files that do not exist
— all `common` scope, all citing `ec/decompiled/bank0/` for a function the
common-area de-dup had already moved to `ec/decompiled/common/`. Five of the
eleven are on rows the map does not cite, which is what the wider reach is for;
the paths were stale and no earlier gate could see them, because the check
above only asks whether a path is *named*, not whether it exists.

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

An unmatched **function** row was meant to fail the build; an unmatched
**variable** row is reported and counted in the manifest, and deliberately not
fatal. A function row is keyed on an address, stable forever; a variable row is
keyed on a decompiler placeholder, which `--mode rebuild-project` **consumes** —
once the name is persisted into the project, `param_1` no longer exists there,
and rebuilding from the same CSV would find nothing to rename. Making that an
error would break a documented, routine operation, and it is the reason the
function row cannot simply be made fatal either without someone deciding what a
routine annotation edit should do. **As of 2026-09-25 (#261) neither is fatal:**
both layers report and count, and the function layer's count is now a real
number read back from the report rather than a literal `0`. Whether a non-zero
`annotations_unmatched` should fail `--check` is open. Typos are caught by the
`--check` above either way, which is stronger: it measures the committed output
rather than the script's say-so.

`ec/ghidra/manifest.csv` carries, for both layers, the counters read back from
`apply-<program>.tsv`: `annotations_applied` and `annotations_unmatched` for the
function layer, and `variables_functions` (how many functions a row decompiled
— the cost), `variables_applied` and `variables_unmatched` for the variable one.
`functions_named` sits beside them and is a different question: how many
exported functions carry a symbol that is not a Ghidra placeholder, which
`--check` derives from the index rather than from the report.

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

> **The "about 2,170" above is replaced by a counted figure, and the paragraph
> is left as it was written.** After the second batch below the export holds
> **2,181** declared `param_N` — `--census` output, not an estimate — and
> `docs/findings.md` §18 carries the per-family table with a correction, because
> the 2,232 and 1,725 this paragraph quotes are no longer re-derivable from any
> committed input. The estimate was close; the reason it is quoted as a count now
> is that a reader can re-run it.

### The second batch: a predicate, and what it decided

**88 more rows, bounded on a measured predicate rather than on prose.** The
boundary is every function whose own listing's **first** instruction that
touches the accumulator A is a `movx @DPTR, A` — so A still holds whatever it
held on entry, and the value stored is that. It is the one family the listing
decides alone, and it is countable from the committed `.asm`: run
`../tools/merge_annotation_shards.py --census` and the boundary, the filters
between the predicate and the batch, and the declaration census all print
themselves. The batch is bank0 55, bank1 17, pd 16, declaring 187 `param_N`
between them.

**37 `param`, 49 `artifact`, 2 `unresolved` — and that distribution is the
finding.** A value arriving in A is the minority case on this predicate,
because Ghidra's function boundaries on this firmware cut through
straight-line code: **53 of the 88 listings contain no `ret` at all**, and
inside a block A is produced by the instruction before. `bank0,0xF079`–
`0xF118` is one constant-writing block carved into twelve entries, and only
two of them take a value that arrives. So most of the batch is `artifact` rows
named for where the value really came from (`a88_from_8014`, `a0_from_b5c7`,
`a_from_8047`, `a_from_r5`), which is a **better** row than `value_a` would
have been. `docs/findings/a-store-predicate-batch.md` has the full account,
including the defect the verification stage caught three times: a
`mov DPTR,#imm` as the last instruction before an entry is **not** evidence
that nothing set A, because the `movx A,@DPTR` ahead of it in the same
two-instruction block is.

**The two short comment forms are both needed, and which one applies is a
measured fact rather than a matter of taste.** Where
`../bank-call-targets.csv` records an `lcall`/`ljmp` into the address, a
`param` row may say the caller left the value in A and cites that file beside
the `.asm`. Where nothing does, the comment says only that the value is the
accumulator's on entry and that these instructions do not say where it came
from. That second form is not a formality: **every readable caller of the
`0xF079`–`0xF118` run sets A explicitly immediately before the call** — a
constant, a `clr A`, or a register copy — which is staging a value, not
passing one, so the edge is evidence that the address is reached and not that
a caller supplied what is in A.

**The backlog figure, counted.** `2,181` declared parameters remain unnamed
after both batches, and `1,601` declared locals are blocked behind the XDATA
map. Both are `../tools/merge_annotation_shards.py --census` output over the
committed export; §18 of `docs/findings.md` has the per-family table and the
correction to the pre-#238 figures, which are kept there but are no longer
re-derivable from any committed input.

## The second pass: edges, not leaves

The sweep above works from `index.csv` minus everything already annotated, so
it names functions in address order and a comment ends up citing a callee by
bare address. Issue #134 asked for the other direction: start from the
addresses a comment already depends on, because a named function whose comment
says "calls 0x0EE8" is not explaining itself until 0x0EE8 has a name.

**The work list is `call-graph-callees.csv`**, and the tool that builds it is
`../tools/call_graph.py`. One row per callee in the graph: inbound count, the
breakdown by transfer form, how many of the callers are themselves named, and
which comments cite the address. The `annotated` column is the queue — the
`annotated=no` rows are what is left, and the `cited_by` ones are the subset a
sentence is actually blocked on.

**The ordering is citation-first, then inbound count**, and that is a
correction to the issue rather than a restatement of it. Issue #134 says the
natural order is by inbound reference count. Inbound is a good ranking and the
table keeps it as the tie-break inside a citation band — but the issue's own
claim that its worked example, 0x0EE8, comes out first on citations does not
reproduce: 0x0EE8 is cited by exactly one comment, the *lowest* positive count
in the set. `call-graph.md` has the positions. The short version for whoever
picks up the next tranche: **no metric would have selected 0x0EE8. It is named
because the issue asked for it**, and that is worth knowing before treating any
count on this list as a recommendation about what a function does.

**The shard / annotate / verify / merge path is the same one the first sweep
used**, unchanged, and the same mechanical rules apply. Two of them bite harder
here:

- **`unresolved` is the common outcome, not an exception.** A callee reached by
  many callers is not thereby a small callee: the first tranche's 44 rows
  include four that are 155-474 bytes and three more that are one to three
  instructions with no `ret` and no jump out, because Ghidra's function boundary on this
  firmware cuts through straight-line code. A row that says what the entry
  does and what is not decoded is a finished row.
- **A `common` callee's `scope` is `common`**, never the bank that reaches it
  most. Which bank executed a given common call site is not in the listing, so
  the graph reports `also_in` and never guesses.

**Naming a function removes its row from the work list, not from the table.**
`call-graph-callees.csv` keeps named callees with `annotated=yes` and their
inbound count intact, so `--check` still passes on the very pull request that
consumes a tranche. A table that listed only anonymous callees would lose the
row the annotation had just completed, and the check would fail on the change
it was written for.

**Comments keep their bare addresses.** 1,300 comments already cite an
already-named function by address, so substituting names into the tranche's
citing comments would leave the export inconsistent for no gain. Where a
sentence's point is *what* the callee is rather than where it lives, the name
is added alongside the address — `bank0,0x0EA2` reads "calls 0x0EE8
(timer1_load_th1_fd_tl0_clear_tf1_start)". The exception that matters: a
comment that writes an address while *rejecting* the decompile's claim about it
must keep the address, because naming the callee there would assert the call the
comment denies.

## Adding a row by hand

Append it, with an `evidence` path, and re-run the build:

```
python3 ec/tools/build_ec_decompile.py --work /tmp/ec
```

The default mode copies the committed project to scratch and exports from the
copy, so the `.rep` is never opened for writing and an annotation change is a
one-line CSV diff rather than a 7 MB binary one. Only `--mode rebuild-project`
writes the project, and two branches that both rebuild one cannot merge.
