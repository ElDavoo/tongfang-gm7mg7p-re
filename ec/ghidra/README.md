# Ghidra: a C codebase for the EC

**Goal (docs/MISSION.md):** a C codebase that mirrors the EC firmware
function for function: decompiled from `../firmware/GMxMGxx_11.800`,
symbolized from `../annotations/registers.yaml`, and with every function
cited back to its bank and address. The vendor's source isn't available, so
this is its reconstruction. Tracked as issue #20.

**Status: built.** `project/` holds a Ghidra 12.1.3 project with the three
programs this firmware dump contains, `../decompiled/` holds 2,709
decompiled C files, and `annotations/ghidra-functions.csv` and
`annotations/ghidra-variables.csv` are the editable layers that improve
both. The five steps below are what it implements; the sections after them
are what it learned doing so.

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
for: it re-exports and then asserts two facts about the bank-0 routine at
`0xB1F0`, the two `../annotations/charge-target-derating.md` established by
hand. That is Ghidra's output compared against a human reading, made
mechanical. **What it asserts, what it runs against, and what invokes it are
spelled out below** — it is the one thing on this page that nothing in CI runs.

`--check` and `--self-test` are what the cheap gate tier runs, at 0.19 s and
0.13 s. The second figure is 0.03 s more since the annotation-side CSVs
(`../annotations/ghidra-functions.csv`, `../annotations/bank-call-targets.csv`)
gained strict structural guards — measured five runs each on one runner, before
and after; `docs/findings.md` §15c has the pairs. `--cross-decoder` adds the
advisory comparison against `disasm8051.py`; it is 0.13 s, it prints rather
than fails, and `.github/scripts/agent-gates-deep.sh` is what passes the flag,
so `AGENT_GATES_DEEP=1` gets it. See `docs/findings.md` §14 — the self-test
used to take 18.8 s, and the cost was a set comprehension that re-read this
repository's annotations CSV once per seed row, not the cross-decoder.

**`--self-test --oracle` is a procedure, not a gate, and that is the whole of
what invokes it.** It re-exports from the committed project into the `--work`
directory and then asserts two facts about bank-0 `0xB1F0`, the two
`../annotations/charge-target-derating.md` established by hand:

- the listing carries an `lcall 0xbf08` at `0xB200`; and
- the C carries `DAT_EXTMEM_09c7 = DAT_EXTMEM_09c7 + 1;` immediately followed by
  `if (0x3b < DAT_EXTMEM_09c7)` — the seconds counter and its 60-second
  threshold.

Both are matched on the address rather than on Ghidra's name for the callee.
`FUN_CODE_bf08` is what `0xbf08` is called before an annotation renames it, and
the committed export calls that same routine
`sub_0a4e_against_4d_with_borrow`; a check written against the name would fail
on the rename rather than on anything about the code. The increment and the
compare are one pattern rather than two, because either half alone is satisfied
by an unrelated line.

The run then feeds the same helper a copy of its own export with each fact
removed and requires it to report that one and not the other. A check that has
never been seen to fail is not a check, and this is the discipline
`variable_csv_problems()` is already exercised under in `--self-test`.

**What passing does and does not say.** It says Ghidra's output at one address
agrees with a human reading of the same bytes, made mechanical. It is not a
claim about the rest of the 2,708 files, and nothing in it is a claim the
decompiler is working — a missing or empty `B1F0.c`/`.asm` is a **failure**,
not a skip, because a silently empty export is one of the two states the check
exists to catch. `TongFang.openDecompiler()` throwing `DECOMPILER UNAVAILABLE`
is already loud from the Java side and needs no second guard here.

**What it runs against.** The export goes to `<work>/out/`, never to
`../decompiled/`: `opt_in_ghidra_oracle()` deliberately does not call
`write_outputs()`, which opens with `shutil.rmtree(OUTDIR)` and would delete and
regenerate the committed tree an acceptance check is checking. The mode is
pinned to `export-only` for the same reason one clause further out — the
committed `.gpr`/`.rep` is copied to `<work>/project-copy` and never opened for
writing, whichever way `--mode` was passed. `git status` being empty after a run
is the test for it.

**Not wired into CI, and why.** By cost and by kind it belongs in the deep tier,
not the cheap one: a full Ghidra export is minutes, and `agent-gates.sh` runs
the cheap mechanical half with no Ghidra and no network (0.13 s, and it says so).
But that script and `agent-gates-deep.sh` are both template-copied `.github/`
files this pipeline's token cannot land, so the block goes here for a human to
drop into `agent-gates-deep.sh` next to the cross-decoder one. It is a direct
invocation rather than a `case` arm, because that is the shape that file uses:

```sh
printf '\n=== Ghidra oracle (EC, bank0 0xB1F0) ===\n'
# Minutes, not seconds: a full export, which is why this is the deep tier and
# not agent-gates.sh's tool loop. See ec/ghidra/README.md for what it asserts.
python3 ec/tools/build_ec_decompile.py --work "$scratch" --self-test \
  --oracle || failed=1
```

Until then it runs when asked, and a green commit says nothing about whether it
would still pass. The same shape `../tools/verify_gap_text.py` is already in
below and `../../docs/findings.md` §14e records for the deep tier.

**One number, measured.** This module defines **41** functions —
`grep -c '^def ' ec/tools/build_ec_decompile.py`. Three files used to give three
different counts of it (22 here, 32 in `../../docs/findings.md` §18, 39 by the
`grep`); the `grep` is the only one of the three that is mechanically checkable,
so it is the one quoted.

## The two annotation layers

Both are hand-maintained CSVs, applied by the same script and regenerated by
the same build. `ghidra-functions.csv` names **functions**; `ghidra-variables.csv`
names **decompiler variables**. Two files, not one, because a function's row
*is* a function — `annotation_seeds()` reads every row's `addr` as a seed and
`join_index()` keys one row per `(scope, addr)` — and a function with eight
named parameters cannot be eight rows there.

The variable layer's `kind` column is the reason it is not just a rename
script. Most `param_N` in this export are not parameters: the decompiler
renders a callee's R7, a scratch register and an uninitialised DPTR as
parameters alike, and 45 rows of `ghidra-functions.csv` already say so about
their own. So the vocabulary is `param` / `local` / `return` / `artifact` /
`unresolved`, and `unresolved` — the listing does not say, leave the
placeholder — is a result, not a failure. `../annotations/README.md` has the
format, the vocabulary and what the checks refuse.

A name corrects the **identifier**, not the **signature**. Ghidra has no Keil
C51 calling-convention model, which is the same reason `signature` is
recorded and never applied, and `void foo(char ticks)` is still a lie about
how arguments reach a function. The first batch says "arrives in A" and stops
there.

## What is here

| Path | What |
|---|---|
| `project/ec.gpr`, `project/ec.rep/` | the Ghidra project: programs `bank0`, `bank1`, `pd` |
| `../decompiled/{common,bank0,bank1,pd}/<ADDR>.c` | one C file per function, named by address |
| `../decompiled/{common,bank0,bank1,pd}/<ADDR>.asm` | **the machine code, beside it.** Same address, same index row; see "The disassembly, and the 1:1 property" below |
| `../decompiled/index.csv` | every function: program, address, name, size, how it was seeded, what is annotated, and the evidence for it |
| `../decompiled/listing-index.csv` | the same rows again, `out_file` pointing at the `.asm`. Separate because the two files answer different questions and merging them would invite a reader to take a decompiled line for an instruction |
| `reassembly.csv` | per function, whether re-encoding the committed listing reproduces the firmware bytes, where it does not, and a `listing_digest` of the listing text so `--check` can see a text edit |
| `gap-text-check.csv` | per *instruction*: the 143 the re-encode cannot reach, each cross-decoded against `disasm8051.py` with its verdict. See "The 143, cross-decoded" below |
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

  assembler: sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14  (/nix/store/…-sdcc-4.6.0/bin/sdas8051, this run)
  committed: sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14  (ec/ghidra/reassembly.csv, 2705 rows)
    the committed report and this run used the same assembler

  reassembly, by function (2705 total):
    match            2574
    partial          73
    assembler-gap    58

  reassembly, by instruction:
    re-encode to the firmware bytes : 45394 of 45537 (99.69%)
    unchecked (sdas8051 cannot express the form): 143

  2574 function(s) have every instruction re-encode byte-exactly; 73 more have all but 143 instruction(s) verified.

  compared against the committed report (ec/ghidra/reassembly.csv):
    outcome               this run  committed
    match                     2574       2574
    partial                     73         73
    assembler-gap               58         58
    mismatch                     0          0
    rows                      2705       2705
    instructions checked     45394      45394
    instructions unchecked       143        143

  moved since the committed report: nothing

  wrote ec/ghidra/reassembly.csv
```

**The transcript is illustrative, and its numbers are the committed report's
own.** It was not re-run while this file was written: `project-setup` installs
Ubuntu's `sdcc` and does not install nix, so the pinned `sdas8051` is not
reachable on a GitHub-hosted runner, and the nix store path above is elided
because it is not reproducible here either. The two `assembler` lines and the
comparison table show the *shape* — what the tool prints when the run's numbers
and its assembler are the ones the report was measured with. A run on a
runner's own assembler prints a disagreement in place of that agreement, and the
paragraph below has what it says.

**45,394 of 45,537 instructions re-encode to the exact bytes in the firmware,
and no function disagrees.** 2,574 of 2,705 have every instruction verified; a
further 73 have all but 143 between them.

The 143 are 74 `AJMP`, 36 `ACALL`, 19 `MOV bit,C`, 13 `CPL bit` and one
`DJNZ A`. `AJMP` and `ACALL` are gaps because `sdas8051` encodes them
differently from the 8051 manual, and they are 110 of the 143 between them;
the other three it refuses outright. `CLR bit` is the one form the assembler
gets *silently* wrong rather than refusing -- it emits `CLR direct`, a
different instruction of the same length, with no error -- and that form is not
among the 143, because this firmware contains no `CLR bit`. Naming a refused
form is not the same as counting one: the tool refuses `CJNE` on a direct
address and the carry-with-immediate forms too, and this image has neither.
`docs/findings.md` §11 records the composition, the correction that produced it,
and the first pass, which reported 97.80% because four opcodes in its list were
written from memory rather than measured.

`ec/tools/verify_gap_text.py` recomputes that set from `to_sdas()` rather
than carrying a list, cross-decodes each of the 143 with `disasm8051.py` (all
143 agree; the verdict per instruction is in `gap-text-check.csv`), and its
`--check` fails if a gap reason appears that has no cross-decode handler.

Measured with `sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14` (SDCC 4.6.0), and
reproduced unchanged on 4.5.0. The version is in every row of
`reassembly.csv`, and the run now prints it against the committed one, because
the split between `match` and `assembler-gap` is a property of what the
assembler can express rather than of the firmware. Every form it cannot express
is named in the source rather than silently dropped, and the 143 above are what
that costs.

**A GitHub-hosted runner's `sdas8051` is a different and older ASxxxx**, so the
same command on a nightly run prints a disagreement where the transcript above
prints an agreement: this run's version string, the committed one, a `NOTE`
naming both, and a category-by-category comparison with the rows that moved
named individually. **That `NOTE` is expected, not a regression** — it is the
warning the version comparison exists to raise, and the run's exit status is
`mismatch == 0` and nothing else. Measured on this repository's runner, whose
`sdas8051` reports `02.00`: `match` 2,621 against 2,574 committed, `partial` 78
against 73, `assembler-gap` 6 against 58, 52 rows moved, `instructions_checked`
45,394 in both, and `mismatch` 0 in both. The version difference and the moved
categories are reported and neither is adjudicated: a branch that has re-reported
its listings and not yet committed the CSV moves the tally legitimately, and
this tool cannot tell that from a regression. `docs/findings.md` §14g has the
calibration, and the question it leaves open.

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

## The 143, cross-decoded

The re-encode is the strongest check the EC has and it has one hole: 143
instructions in five forms `sdas8051` cannot express are excluded from it, and
so were read by *no* check. The byte check reaches them — it covers all 45,537
and needs no assembler — but a byte is not a mnemonic, and a listing whose
bytes are right and whose text is wrong passes it.

`../tools/verify_gap_text.py` closes that by asking a second decoder.
`disasm8051.py` shares no code with Ghidra's SLEIGH, which is the same
property that makes the 45,394 meaningful. For every instruction
`verify_reassembly.to_sdas()` declines, it decodes the instruction **from the
firmware image** at that instruction's own runtime address and compares that
reading to the listing's text:

```
$ python3 ../tools/verify_gap_text.py --report
  gap text: 143 instruction(s) in 84 row(s) across 5 form(s); 45394 checked by re-encode
    BIT_UNSUPPORTED 0x92         19
    BIT_UNSUPPORTED 0xB2         13
    GAP_FORMS "djnz a,"          1
    GAP_MNEMONICS acall          36
    GAP_MNEMONICS ajmp           74
  verdicts: 143 agree
```

**All 143 agree.** `gap-text-check.csv` records each one individually — the
two texts, both canonical forms, why `to_sdas()` declined it, and the verdict —
so no instruction is folded into a total.

**This does not make the 1:1 claim 100%, and the number stays 45,394 of
45,537 (99.69%).** `sdas8051` still cannot express those five forms; nothing
about this work changes that. What changes is *coverage*: every instruction in
the committed listing is now read by an independent check — 45,394 by
re-encode, the 143 by decoder agreement. The two are not the same kind of
evidence and should not be added together into a single percentage. For the
45,394 an independent assembler encodes the listing back and the firmware bytes
arbitrate, constructively. For the 143 the bytes are already settled by the
byte check, and what is agreed is the *text*, between two decoders reading the
same byte column. It is a weaker form of the same claim, and it inherits the
byte check's premise rather than escaping it.

### How the two renderings are compared

Two decoders rarely spell an instruction the same way, so both sides are
reduced to `mnemonic op0|op1|...` first. Folded: case, whitespace, a bit
operand's rendering (`psw.5` ≡ `0xd5` ≡ `acc.4`) and a direct operand's
(`A` ≡ `0xe0`). Those are spelling. **Not** folded: the mnemonic, the bit
number, the direct byte, the immediate, a register, and a branch's absolute
target — those are the instruction. The operand's *class* comes from the
opcode, never from the operand text, because `clr 0x8e` is both CLR direct and
CLR bit depending on the byte in front of it. `--self-test` asserts that
`cpl 0xd5` against `cpl 0xe4` is a **disagreement**: a canonicaliser that
folded the mnemonic would report the whole set as agreeing and mean nothing.

A `db` on either side is `undecodable`, never `agree`. `disasm8051.py`'s
mnemonic table is partial by design, so a comparison against one could only
match vacuously. This was not hypothetical: `mnemonic()` had no case for
opcode `0x92`, so all 19 `mov <bit>,CY` decoded as `db 0x92` and would have
been "in agreement" with a hole.

### What it does not cover

- **It is comparative, not constructive.** Two decoders reading the same bytes
  can share a misreading. The re-encode cannot, because the firmware
  adjudicates; the byte check cannot, because the bytes are the question. A
  form both decoders get the same wrong way is invisible here, and the re-encode
  is blind to that too when the decoder and the assembler agree with each other
  — which is a real case, see `0xA0`/`0xB0` below.
- **The set is only what `to_sdas()` declines.** It is recomputed from that
  predicate on every run, so it cannot drift from the
  `instructions_unchecked` column of `reassembly.csv` — but it is also exactly
  that set, and an instruction `to_sdas()` expresses is not checked here. The
  re-encode has already read those.
- **`0xA0`/`0xB0` are unresolved.** Ghidra's SLEIGH, r2 and `sdas8051` all put
  `ORL C,/bit` at `0xA0` and `ANL C,/bit` at `0xB0`; the MCS-51 manual as
  reproduced in common references has them the other way round. Three tools
  agreeing is why `disasm8051.py` follows them, and none of them arbitrating
  the other two is why that is recorded rather than settled. No committed
  instruction is affected either way — all 12 occurrences are inside the 45,394,
  because those are two of the bit forms `sdas8051` *does* express. But it is
  the shape of hole this tool cannot see: the re-encode passes on them because
  the decoder and the assembler agree, not because either is right.
- **`0xC1` (`CLR bit`) has no committed instance**, so there is nothing in the
  image to cross-decode. It is in `verify_reassembly.BIT_UNSUPPORTED` and
  matches none of the 143, and it is the one form `sdas8051` gets *silently*
  wrong — it assembles `CLR direct`, the same length, with no error. A future
  export containing one would be excluded from the re-encode and read by
  nothing; `disasm8051.py` can now decode it, and closing the loop needs its
  own check.

### Running it

`--check` and `--report` need only `python3` and the committed firmware — no
assembler, unlike the `--report` next door — and take well under a second:

```
$ python3 ../tools/verify_gap_text.py --check
$ python3 ../tools/verify_gap_text.py --self-test
```

`gap-text-check.csv` is written by `--report` and by nothing else, exactly like
`reassembly.csv`'s columns. One honest difference: regenerating it *is* a
verification, not a re-arming. `--report` re-derives every `disasm_text` from
the current bytes and the current `disasm8051.py` tables, so a listing edit or a
decoder-table edit cross-checks the new text rather than pinning whatever it
now says.

**Nothing runs this per commit.** By cost and by kind it belongs in the cheap
tier, but `.github/scripts/agent-gates.sh` is a template-copied file and the
pipeline token has no `workflow` scope. The change is one `case` arm in
`check_ghidra_tooling()`, mirroring the `*verify_reassembly.py` one:

```sh
      *verify_gap_text.py)
        python3 "$tool" --check || rc=1
        ;;
```

plus `ec/tools/verify_gap_text.py` in the tool list above it. Until a human
lands that, this check runs when asked and the committed verdicts can go stale
in a commit that is otherwise green. That is the same shape
`../../docs/findings.md` §14e records for the deep tier.

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
nix-pinned measurement. Auditing what it wrote is a separate command,
`--verify-provenance` below, and it needs the full git history the two
revisions it names live in: `git clone` without `--depth`. The agent stages
check out with `fetch-depth: 0` and can run it; both of `ci.yml`'s checkouts
are default-depth and cannot resolve `08b72e2` at all, which is why it is a
full-clone command and not part of the per-commit gate.

**That warning has since been measured rather than predicted**
(`../../docs/findings.md` §14h, issue #157). The runner's `sdas8051` was
`05.50.4`'s contemporary — SDCC 4.2.0, `sdas8051 02.00`, six years older — and
a full report against it would indeed have rewritten every `assembler` cell. The
measured part is sharper than "could move the gap tallies above": of the
2,705 rows, **the 143 and the 45,394 are unchanged** — 0 rows differ in
`instructions_checked` or `instructions_unchecked`, because those two columns
come from `to_sdas()` in pure Python and not from the assembler — while **52
rows change `outcome`**, all of them `assembler-gap` becoming `match` or
`partial`. Those 52 are in `../../evidence/ec-reencode/2026-09-23-sdas8051-rowdiff.csv`.
So re-reporting against a different build moves *coverage*, not the byte
arithmetic, which is the distinction the `assembler` column exists to let a
reader make.

One caveat belongs here too, because this file is where a reader looks for the
tallies. §14h also found a race in `verify()`'s dispatch that made repeated
`--jobs 4` runs disagree, and the commit that wrote this report
(`08b72e2`) records no `--jobs` value, so whether the 58 `assembler-gap` rows
below carry that artefact is not settled from history. The 45,394 and the 143
cannot be affected — they are computed before the assembler runs — but the
outcome columns should be re-measured with the pinned nix build before they are
treated as settled.

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
its own history. `docs/findings.md` §14f has the method, and this runs it:

```
$ python3 ../tools/verify_reassembly.py --verify-provenance \
      --base 08b72e2 --migration a56b3bb --listings-from 8c7985e
  listing text: 0 of them changed over 08b72e2..a56b3bb; the same pathspec returns 2705 file(s)
  over 8c7985e..08b72e2, the window that last wrote them, so the first number is a measurement
  report: 2705 of 2705 row(s) identical once listing_digest is dropped (present in the
  base: no; in the migration: yes)
  PASS  the migration changed the column and nothing beneath it, and no listing text
  moved while it did.
```

`--listings-from` names the revision *before* the window that last wrote the
listings, and the count it prints is the positive control: the 2,705 above is
the same pathspec matching 2,705 files, which is what makes the zero next to it
a measurement rather than a pathspec matching nothing. A migration that moved a
listing, or touched any other cell of the report, fails with the file or the
cell named.

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
