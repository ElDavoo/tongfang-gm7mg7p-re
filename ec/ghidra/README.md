# Ghidra: a C codebase for the EC

**Goal (docs/MISSION.md):** a C codebase that mirrors the EC firmware
function for function: decompiled from `../firmware/GMxMGxx_11.800`,
symbolized from `../annotations/registers.yaml`, and with every function
cited back to its bank and address. The vendor's source isn't available, so
this is its reconstruction. Tracked as issue #20.

**Status: built.** `project/` holds a Ghidra 12.1.3 project with the three
programs this firmware dump contains, `../decompiled/` holds 2,716
decompiled C files, and `annotations/ghidra-functions.csv` is the editable
layer that improves both. The five steps below are what it implements; the
sections after them are what it learned doing so.

## How to use it

```
# re-export from the committed project (seconds-to-minutes, leaves project/ alone)
python3 ../tools/build_ec_decompile.py --work /tmp/ec

# rebuild the project itself: new firmware, new seed, or a changed project symbol table
python3 ../tools/build_ec_decompile.py --work /tmp/ec --mode rebuild-project

# what CI checks, with no Ghidra and no network
python3 ../tools/build_ec_decompile.py --work /tmp/ec --check
python3 ../tools/build_ec_decompile.py --work /tmp/ec --self-test
python3 ../tools/build_ec_decompile.py --work /tmp/ec --self-test --cross-decoder  # advisory
python3 ../tools/build_ec_decompile.py --work /tmp/ec --self-test --oracle   # also runs Ghidra
```

`--self-test --oracle` is the acceptance check this file has always asked
for: it rebuilds and then asserts that the bank-0 routine at `0xB1F0` comes
out calling `FUN_CODE_bf08` and touching `EXTMEM 0x09c7`, the two facts
`../annotations/charge-target-derating.md` established by hand. That is Ghidra's
output compared against a human reading, made mechanical.

`--check` and `--self-test` are what the cheap gate tier runs, at 0.19 s and
0.13 s. `--cross-decoder` adds the advisory comparison against
`disasm8051.py`; it is 0.13 s, it prints rather than fails, and
`.github/scripts/agent-gates-deep.sh` is what passes the flag, so
`AGENT_GATES_DEEP=1` gets it. See `docs/findings.md` §14 — the self-test used
to take 18.8 s, and the cost was a set comprehension that re-read this
repository's annotations CSV once per seed row, not the cross-decoder.

## What is here

| Path | What |
|---|---|
| `project/ec.gpr`, `project/ec.rep/` | the Ghidra project: programs `bank0`, `bank1`, `pd` |
| `../decompiled/{common,bank0,bank1,pd}/<ADDR>.c` | one C file per function, named by address |
| `../decompiled/{common,bank0,bank1,pd}/<ADDR>.asm` | **the machine code, beside it.** Same address, same index row; see "The disassembly, and the 1:1 property" below |
| `../decompiled/index.csv` | every function: program, address, name, size, how it was seeded, what is annotated, and the evidence for it |
| `../decompiled/listing-index.csv` | the same rows again, `out_file` pointing at the `.asm`. Separate because the two files answer different questions and merging them would invite a reader to take a decompiled line for an instruction |
| `reassembly.csv` | per function, whether re-encoding the committed listing reproduces the firmware bytes, where it does not, and a `listing_digest` of the listing text so `--check` can see a text edit |
| `manifest.csv` | per program: function/decompile/fail counts, bytes disassembled, seed counts, Ghidra version, input SHA-256. The `common` row is an **export grouping**, not a fourth Ghidra program: those functions live in both bank programs and are emitted once |
| `xdata-symbols.csv` | generated XDATA names, from `../annotations/registers.yaml`. Never hand-edited |
| `xdata-overrides.csv` | the hand-maintained escape hatch for addresses the generator cannot name |
| `../annotations/ghidra-functions.csv` | **the editable layer.** Function names, types, comments, evidence |
| `../../ghidra/scripts/*.java` | the headless scripts, shared with the BIOS and Windows projects |

## The five steps, and what happened

1. **One flat 64 KiB image per CODE bank**, built by `../tools/make_bank_image.py`
   (bank 0 ← file `0x08000`, bank 1 ← `0x10000`). Unchanged from the original
   prescription.
2. **Each image is its own program**, imported with
   `-loader BinaryLoader -processor 8051:BE:16:default`. One JVM imports all
   three: they share a loader and a processor, and a JVM start is ~15 s.
3. **XDATA named from `registers.yaml`** before decompiling, so the output
   reads `PROJECT_ID` rather than `DAT_EXTMEM_0740`. 56 symbols.
4. **One C file per function, named by bank and address.** File names are keyed
   on the *address*, not the function name: names change as the reading
   improves, and a rename must not churn a file path in git. `index.csv` maps
   address to name.
5. **Banks cross-linked** through the BL51 trampolines, via the call-target
   census in `../annotations/bank-call-targets.csv`.

## What the build found that the plan did not know

**A raw 8051 import finds zero functions.** The 8051 SLEIGH has no reset-vector
concept, so import + auto-analysis produces nothing at all — measured, not
assumed. Seeding is not an optimisation here, it is the whole difference
between 0 and 2,716 functions. The seed set is written to a spec file the
`SeedFunctions.java` pre-script reads, and every seed carries a `basis` that
survives into the index:

| basis | what it is |
|---|---|
| `vector` | an entry in that program's own vector table |
| `vector-target` | the target of a vector table `LJMP` |
| `stub` | one of the four BL51 bank-switch stubs `0x1100/0x1114/0x1128/0x113C` |
| `call-target` | an `lcall`/`ljmp` target from `bank-call-targets.csv` |
| `annotation` | an entry declared in `../annotations/ghidra-functions.csv` |
| `auto` | found by auto-analysis, not seeded |

**Seeds are applied strongest-evidence-first, and that is load-bearing.** The
first seed at an address wins: a later one that lands inside the body it
created is rejected. `bank-call-audit.md` §1 is explicit that the call-target
census is a byte-scan upper bound whose framing is unresolved in places (issue
#57), and it shows. The census contains a target at `0x8055`, one byte into
the `mov dptr,#0x1904` that the same file identifies as the case-0 handler at
`0x8054`; seeded first, `0x8055` produced a function whose body swallowed
`0x8054` and the cited entry had nowhere to go. Seeded in evidential order —
`annotation`, then `vector`/`stub`, then `call-target` — the cited entry wins
and the phantom loses. Where a census target and a cited entry disagree by a
byte, the citation is the better evidence, and the build now says so in code
rather than in a comment.

**Annotation-declared entries are re-applied after auto-analysis.** Ghidra
removes some freshly created functions — the address gets absorbed into a
neighbouring body, or a switch analysis prunes it. For a census-derived seed
that is the analyser doing its job. For a seed a person wrote with a
citation, the citation should have the last word, so `SeedFunctions.java` runs
a second time as a post-script over the annotation rows alone. Never over the
census rows: re-seeding 1,400 byte-scan targets after analysis would undo
every heuristic Ghidra applied.

**Neither image's vector table is where the textbook says.** The EC's is
discovered, not assumed: it mixes 3-byte `LJMP` entries with 4-byte
`LJMP`+`RET` ones, has lone `RET` placeholders for unused vectors, and real
code begins at `0x002E` — 16 entries, alternating handler and trampoline
targets. The PD image's has six entries with `0xFF` padding between them. A
hardcoded list of 8051-standard offsets would have seeded the wrong addresses
on one image or the other, and the failure would have read as "the firmware has
no handler there" rather than as a wrong tool. `discover_vector_table()` in
`../tools/build_ec_decompile.py` walks the table instead.

**The PD image must not be seeded from the EC's tables.** It is a separate
program with its own address space, its own vectors and its own XDATA map
(`lightbar-bat-flow.md` §2). Seeding it with EC call targets put 561 seeds on
bytes that are not instruction starts in that program, and naming EC registers
there would be a first-class overclaim. It gets its own vectors and **zero**
XDATA symbols — asserted in the generator, in `ApplyAnnotations.java`, and in
the self-test.

**A branch-reached function is invisible to a call census, and the most
important routine in this firmware is one.** `0xB158`, `charge_target_update`,
is the routine the whole charge-cap question turns on. There is no `lcall` or
`ljmp` to it anywhere: it is entered by `jb acc.1` from `0xB141`
(`charge-target-derating.md`). A seeder built from direct calls alone leaves it
out of the project entirely — which is what happened on the first build. The
fix is the annotation layer: a row in `../annotations/ghidra-functions.csv`
declares a function entry, and the build seeds it. That is the loop working
as intended, on the routine `ec/annotations/` already understood.

**The decompile was checked against this repository's own decoder.**
`--self-test` runs `ec/tools/disasm8051.py` over each annotated function's
straight-line opening and compares the XDATA addresses it names with the ones
Ghidra's C names. At `0xB1F0` they agree on all six — two decoders that share
no code, on the operands. It is a report rather than a gate, because the
comparison is only meaningful in one direction: at `0xB158` the C names six of
the eight the linear decode sees, having folded the `0x04A7`/`0x04A6` byte
pair feeding the big-endian store helper into a single wide read. That is the
decompiler doing its job, and a gate that failed on it would be failing on
correct output.

**Coverage, honestly.** `manifest.csv` reports `instruction_bytes` — bytes
actually disassembled — and separately `body_bytes`, the sum of function body
lengths. The second is not a coverage figure: Ghidra's bodies can overlap, and
summing them can exceed the image size. The first, measured on this build:
bank 0's window 23,283 of 32,768 bytes, bank 1's 24,709, the common area
19,784, the PD image 10,296. Read those as "how much did analysis reach", not
as "how much is understood".

**102 call targets name no bank and were not seeded** (140 rows in the census,
102 distinct targets). They are common-area
call sites whose targets land in a `0x8000-0xFFFF` window, so the census cannot
say which bank. Applying them to both on a guess would disassemble from
addresses that are not function entries in one of them. They are reported
every build and left for issue #48.

**Ghidra's native decompiler can fail silently.** If the release was unpacked
by something that dropped the exec bit on
`Ghidra/Features/Decompiler/os/linux_x86_64/{decompile,sleigh}`, then
`DecompInterface.openProgram()` returns false and `getLastMessage()` is the
*empty string* — indistinguishable in the output from "this function will not
decompile", which is the same failure shape as the ConfuserEx anti-tamper trap
in `windows/antitamper/README.md`. `ExportDecompile.java` raises that as a
loud, specific failure, and the build preflights the exec bit before starting a
JVM. Do not read a `// decompile failed:` line as a statement about the
firmware until you have ruled this out.

## The disassembly, and the 1:1 property

Every function has a `.c` and an `.asm` at the same address, and
`../decompiled/listing-index.csv` names the second the way `index.csv` names
the first. The `.c` is a reading of the bytes; the `.asm` is the bytes, and
without it a reader who wants to check a decompilation has nothing to check it
against. `--check` refuses an export where either half is missing.

The 1:1 property is then something measurable rather than something asserted.
`../tools/verify_reassembly.py` takes the committed listing, re-encodes it with
`sdas8051` — SDCC's assembler, which never saw this firmware — and compares the
result against `../firmware/GMxMGxx_11.800`:

```
$ SDAS8051=$(nix build nixpkgs#sdcc && echo $out/bin/sdas8051) \
    python3 ../tools/verify_reassembly.py --work /tmp/ec --report

  reassembly, by function (2705 total):
    match            2574
    partial           73
    assembler-gap     58

  reassembly, by instruction:
    re-encode to the firmware bytes : 45394 of 45537 (99.69%)
    unchecked (sdas8051 cannot express the form): 143
```

**45,394 of 45,537 instructions re-encode to the exact bytes in the firmware,
and no function disagrees.** 2,574 of 2,705 have every instruction verified; a
further 73 have all but 143 between them.

The 143 are `MOV bit,C`, `CPL bit`, `CLR bit`, `CJNE` on a direct address,
`DJNZ A` and the carry-with-immediate forms. `CLR bit` is the only one the
assembler gets *silently* wrong rather than refusing -- it emits `CLR direct`,
a different instruction of the same length, with no error -- and the rest of
the list is safe because a refusal is a refusal. `docs/findings.md` §11 records
the first pass, which reported 97.80% because four opcodes in that list were
written from memory rather than measured.

Measured with `sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14` (SDCC 4.6.0), and
reproduced unchanged on 4.5.0. The version is in every row of
`reassembly.csv`, because the *gap* count is a property of the assembler and
the match count should not be: the firmware bytes are the arbiter either way. The remaining 1,004 (2.2%) are
instruction forms `sdas8051` cannot express — the bit-addressed `CLR bit`,
`SETB bit`, `CPL bit`, `MOV C,bit`, `MOV bit,C`, `MOVC A,bit`, `CJNE` on a
direct address, `DJNZ A`, and the carry-with-immediate forms — and every one of
them is named in the source rather than silently dropped.

Three things this does **not** mean, stated because the number invites the
wrong one:

- **It is not a claim about the C.** The decompiler is not in the loop. A
  decompilation can be wrong and this check still passes, which is correct: the
  C is a claim about what the machine code means, and the listing is the claim
  about the machine code.
- **It is not a claim that the C recompiles.** Keil C51 generated these bytes.
  SDCC does not emit Keil's code generation, and annotating the C does not
  change that. See `../../ghidra/README.md`.
- **`sdas8051` is not always right.** It encodes `AJMP`/`ACALL` differently from
  the 8051 manual, which is why those are gaps rather than mismatches; that was
  established by arbitrating against `../tools/disasm8051.py`, not by assuming.
  The two disagree about `MOV direct,direct`'s byte order in the same way, and
  `disasm8051.py` agrees with Ghidra there too.

What the check found on the way is in `../../docs/findings.md` §11; the four
translation bugs it took to get to a clean result are the argument for having
it at all.

## What `listing_digest` is, and what it does not prove

The re-encode above is the strongest check the EC has, and it was also the only
one that read the listing's *text* — the byte check passes a wrong mnemonic
outright, because a mnemonic is not a byte. So `reassembly.csv` now carries a
`listing_digest` per row, a 64-bit hash of the parsed instruction stream, and
`../tools/verify_reassembly.py --check` recomputes it for every committed
listing on every run. A mnemonic or operand edited in a `.asm`, with the byte
column left correct, now fails the cheap tier with no assembler:

```
$ # in ec/decompiled/bank0/031C.asm: `ljmp 0xd236` -> `sjmp 0xd236`, byte column untouched
$ python3 ../tools/verify_reassembly.py --check
  listing bytes: 45537 instruction(s) checked against the firmware, 0 disagreement(s)
  listing digests: 2705 compared against the committed report, 1 disagreement(s)
  FAIL bank0 031C poll_d6c2_then_branch (bank0/031C.asm): report says 38b4854aff7d69ca, bank0/031C.asm now digests to 180ddaa4dd467c12 -- the listing text changed after the report measured it
```

**A digest detects change; it does not verify the disassembly.** A digest that
agrees says the text has not moved since the report was measured. It does not
say the text is right, and nothing here can: a wrong mnemonic committed
together with a re-reported digest is caught by no automated check in this
repository, because the thing that would catch it is the re-encode, and the
re-encode still has no schedule. The column's name invites the second reading
more than the first, which is why this paragraph exists.

What it deliberately does not cover, and why: the digest is over the *parsed
instruction stream*, not the file's bytes. Case, internal whitespace and the
space after a comma are folded, so a re-wrap or a comment edit is not a change
to any claim and does not need an assembler run to resolve. Four *pairs* of rows
share a digest — the same function at the same address in both bank windows, at
`0x031C`, `0x3A60`, `0x703A` and `0xFF17`, whose instruction streams really are
identical. That is what the column means, not a collision: it identifies a
stream, and two rows can name the same one.

The column is written by `../tools/verify_reassembly.py` and by nothing else.
Never hand-edited, and never added by hand either — copying a new digest into
the CSV re-arms the detector without anyone checking the new text. Refreshing a
digest after a deliberate listing change means re-reporting, which needs the
pinned assembler from the command above:

```
$ SDAS8051=$(nix build nixpkgs#sdcc && echo $out/bin/sdas8051) \
    python3 ../tools/verify_reassembly.py --work /tmp/ec --report
```

`--add-digest-column` exists for the one migration that added the column to the
committed report, and refuses to run a second time. It is the honest way to do
that migration and also a trap worth naming: it adds digests from the listings
on disk **without re-encoding**, so the command itself cannot prove those are
the listings the report measured — proving that needs the same assembler, and
the one on a GitHub-hosted runner is a different and older ASxxxx, against
which a full report would rewrite every `assembler` cell and could move the gap
tallies above. That is why it is one-shot and why the tallies here are still the
nix-pinned measurement.

**For the committed column the history supplies the proof the command could
not** (2026-09-23, issue #150). `a56b3bb` changed nothing in this file but the
new column — drop `listing_digest` from its header and rows and all 2,705 are
identical to `08b72e2`'s, which is therefore the last commit to write a
non-digest cell and, by its own message, the last full `--report`. No listing
text moved in between:

```
$ git diff --name-only 08b72e2 a56b3bb -- 'ec/decompiled/**/*.asm'
$ # no output. The same pathspec returns all 2,705 files over
$ # 8c7985e..08b72e2, so it is matching and the set is empty, not unstated.
$ # The one ec/decompiled file the window touches is bank0/0EA2.c (cd3c7b0),
$ # a decompiled C export; the digest is over the .asm instruction stream.
```

So the digests are of the listings the last full `--report` measured, which is
the one thing the one-shot could not assert about itself. What stays open is
what it never could: they were taken without a re-encode, so they attest to the
measured text and not to its correctness — the paragraph above — and the guard
stops a second run, not the first. A future migration still answers this from
its own history. `docs/findings.md` §14f has the method.

## The annotation layer

`../annotations/ghidra-functions.csv`, header-only so `csv.DictReader` reads it
(`ec/README.md`): `scope,addr,name,signature,type,comment,evidence,basis`.

- **`scope`** — `bank0`, `bank1`, `pd`, or `common` for a function in
  `0x0000-0x7FFF` that is the same in both bank programs. A common-area
  function is exported once, so its address appears in no bank row: a
  `bank0`-scoped row for one is a scope rename, not a typo, and
  `../tools/merge_annotation_shards.py` does the rename rather than dropping
  the row.
- **`type`** — a controlled vocabulary, because an unchecked one becomes an
  unchecked claim: `entry init dispatch forwarder gate reader writer copy math
  logic serial sbi ec-io state delay bank-switch unresolved`, plus the
  module-specific `charge-target` the hand-written rows use. **`unresolved` is
  a result, not a failure**: a function whose role cannot be determined is
  correctly described as far as the bytes go and no further, and filling the
  gap with a plausible name is the one thing an annotation must never do.
- **`evidence`** — mandatory and non-empty. A repo path. An annotation without
  one is a claim, not a finding, and the build rejects it.
- **`basis`** — `hand-decoded` (the disassembly was read and the 8051
  operations reasoned about), `restatement` (what the decompiler's C says, no
  more), or `inferred` (a reading; the export says so next to it, the marker
  `bios/decompiled/OemOcDxe.annotated.c` already uses). The distinction
  matters because a decompilation is one reading of the bytes: reporting it as
  `restatement` is honest, and reporting it as `hand-decoded` is not.
- **`signature`** — recorded in the plate comment, **not applied** to the
  function's type system. Ghidra has no Keil C51 calling-convention model, so
  an applied prototype on 8051 code would be a guess sitting where a fact
  reads.

An address with no function is reported as `annotations_unmatched` and fails
the build, rather than being dropped. That is either a typo or a sign the
project needs `--mode rebuild-project`; the fix is to say which, not to let a
stale annotation outlive the thing it named. The current 67 rows all resolve
against the committed project.

**A row is a claim about a function boundary, and a source that declines to
claim one does not get a row.** `bank-call-audit.md` describes the window at
`0xA366` as a linear decode it traced no control flow through, and calls the
register naming in it "an address coincidence in a static read". Seeding a
function there split the function around it and asserted a boundary the source
explicitly disclaims, so the row was dropped rather than kept with a hedge.

**Two hand readings of the same routine are recorded as a disagreement, not
resolved by picking one.** `lightbar-bat-flow.md` reads PD `0x0FCB` as a
3-byte load into R0:R1:R2; `pd-0x38-consumers.md` reads it as four `MOVX`
reads into R0-R3. The merged row carries both, names neither, and says the
decompile settles it — which it now can, because the function is in the
project.

## Regenerating the XDATA symbols

`../tools/gen_xdata_symbols.py` reads `../annotations/registers.yaml` and
writes `xdata-symbols.csv`. It **never writes** `registers.yaml`: a `status:`
change is a human's, made with its own evidence in the same commit (CLAUDE.md),
and a symbol rename must not be able to imply one.

Multi-byte registers are named by address order — `MODE_PL_DEFAULTS_0`,
`MODE_PL_DEFAULTS_1` — and **never** `_LO`/`_HI`. `charge-target-derating.md`
reads the 16-bit stores as big-endian, but that is a hand reading, and a wrong
endianness suffix baked into a symbol name is an overclaim in the least
defensible place there is.

Addresses the generator cannot name are not silently dropped: it exits non-zero
and lists them, pointing at `xdata-overrides.csv`. That bounded list is the
to-do, not a bug to hide.

## Limits

- `body_bytes` is not coverage; see above.
- A `call-target` function boundary is a **hypothesis**. The census is a byte
  scan and an upper bound (`bank-call-audit.md` §1): a target can land inside
  a data table. Affected files carry a line saying so, and `index.csv` records
  the basis per row.
- Register names cover what `registers.yaml` documents. The C51 overlay locals
  at `0x0A47-0x0A51` and the derating counters at `0x09C7-0x09C9` are **not in
  it**, so they read `DAT_EXTMEM_*`. That is "not named by this method", not
  "not registers".
- The project reopens only in Ghidra 12.1.3, the version
  `.github/actions/project-setup` installs. A Ghidra upgrade means a rebuild.
- Bank 2 and bank 3 exist as stubs and are unused on this build; they are not
  imported.
