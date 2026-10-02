# What a rebuild from the committed inputs re-derives (issue #623)

[`named-without-a-row.md`](named-without-a-row.md) §6 is explicit that one
question is not answered: **whether `--mode rebuild-project` from the CSV alone
re-derives the names the export carries at addresses no annotation row backs.**
No rebuild was run there, because a rebuild writes the project database and that
is not something a write-up can do to the tree it is describing.

This runs one, in a scratch copy of the repository, and reads the answers back
out. The short form:

- **Six of the seven are re-derived exactly.** The name at each is the target's,
  and a rebuild from the committed inputs puts the same string there.
- **One is not, and it is a finding rather than an answer.**
  `bank1` `0x031C` comes back as `FUN_CODE_031c` — a Ghidra placeholder form at a
  rowless address, which is exactly the case §6 says it has no evidence about.
- **The four `pd` call sites are answered counterfactually.** A rebuild puts
  `call_10bc` at all four, not `add_full_product_to_dptr`, because the row that
  superseded the callee's name is itself a committed input. Which tool put the
  *original* string in the committed database is untouched by that and is not
  answered here.
- **The database is not reproducible from the committed inputs.** The rebuilt
  export is not identical to the committed one, and the sharpest instance is
  that nine `ghidra-functions.csv` rows resolve in the committed database and
  do not resolve in a rebuild from the same bytes. §7 reads those nine.

Nothing here was seen on hardware or in Windows, and no register was read. Every
input is a committed file; the one thing that was not committed — the rebuilt
export — was written to a scratch directory outside the repository and is
quoted, not landed.

**The run is cheap, which is the most reusable fact here.** The copy and the
whole three-program rebuild took **43 seconds** on the runner this was measured
on, from the copy's creation to the tool's exit. The 120-minute ceiling
`rebuild_provenance.py` carries by default was sized for a job that turned out
to be two orders of magnitude shorter. Nothing about the answer depends on the
ceiling; the fact that the measurement is repeatable in under a minute is worth
having on its own, because §6's question was left open partly because running it
looked expensive.

**Three runs, and they agree.** This was run three times on the same runner
with the same Ghidra 12.1.3 and the same Temurin 21 JVM. Every line of the Q1,
Q2, Q3 and Q4 output was byte-identical across all three, including the 245
differences and the one Q3 asks to be named. That is three runs agreeing, not a
determinism claim about other machines or other Ghidra builds, and it is what
lets §6 be read as a fact about the committed inputs rather than about one run.

## 1. The number in the issue is stale, and so is the plan's correction of it

The issue asks about "the 11 `target-of-a-transfer` names". It is seven, and
`python3 ec/tools/second_copy_census.py --check` says so on this tree:

```
7 row(s): 7 target-of-a-transfer, 0 ghidra-switch-entry, 0 unexplained
```

Five of the eleven left that population by taking a row of their own — `pd`
`0x0000` and the four `lcall 0x10BC` sites — and
[`named-without-a-row.md`](named-without-a-row.md) records that. **That is not a
question answered for them; it is the question dissolved**, because an address
is in the population precisely when no row backs it, and a row is the whole
reason each left.

The plan this was built from put the correction one step behind the tree: it
quotes `21 row(s): 7 target-of-a-transfer, 14 ghidra-switch-entry, 0
unexplained`, which was true before #631 widened `isPlaceholderName()` to
`caseD_` and `default` and sent the fourteen switch entries out of the
population without a single row changing. The seven are the same seven in both
readings. The figure here is the one `--check` prints now.

## 2. The run, and what it could not touch

`ec/tools/rebuild_provenance.py --run` does the whole thing, and the reason it
is a tool rather than a procedure is the safety invariant. In the committed
tree `build_ec_decompile.py` resolves `project_dir = PROJECT` — the committed
`ec/ghidra/project` — and `write_outputs()` opens with `shutil.rmtree(OUTDIR)`
where `OUTDIR` is the committed `ec/decompiled`. A rebuild run in the tree
destroys both the database `.gitattributes` makes git refuse to merge and every
exported `.c` and `.asm`. So the tool:

1. **refuses** a scratch path inside the repository, before anything is copied —
   a `--self-test` case, so it is exercised rather than merely present;
2. copies the tree (381 MB with `.git` excluded; 407 MB with the rebuild's own
   output in it) and runs the rebuild **in the copy**;
3. supplies the owner with `JAVA_TOOL_OPTIONS=-Duser.name=dave`, which edits no
   file anywhere, not even in the copy;
4. takes no diff at all unless the rebuild exited 0 **and** the copy's own
   manifest accounts for the copy's own export.

**Step 1 is what makes step 2 safe, and step 4 is what makes the answer
trustworthy.** A rebuild killed part-way leaves a short export behind, and a diff
against a short export produces a report full of differences that read exactly
like the finding being hunted — so a run that fails either test reports *not
measured* and exits non-zero. The answers stay open rather than being answered by
a truncated run.

**Step 3 is not a workaround for #572, and does not touch it.** The committed
`ec/ghidra/project/ec.rep/project.prp` carries
`<STATE NAME="OWNER" TYPE="string" VALUE="dave" />`, and `analyzeHeadless`
refuses the copy with `NotOwnerException: Project is owned by dave` otherwise.
The write-ups that used the option — `docs/findings.md`, and
[`pd-unannotated-listings.md`](pd-unannotated-listings.md) and
[`pd-07d0-accessor-stubs.md`](pd-07d0-accessor-stubs.md) — all name it, and
none of them edited the copy. #572 owns making it permanent inside the
tools; whether a one-off measurement can happen today is a different question,
and it could. The tool records which mechanism it used and prints the `.prp`
edit as a documented fallback for a JVM that will not take the option. **No
file in this repository is edited by the run** — `git status` over
`ec/ghidra/project`, `ec/decompiled` and `ec/ghidra/manifest.csv` is empty
afterwards, which is the check that matters.

## 3. Q1 — the seven transfer stubs, and the one that is not re-derived

Q1 is read off the `name` column at the census addresses in each tree, and the
population is derived from `second_copy_census.py` rather than transcribed, so
it is the same list `--check` prints.

| | address | committed name | rebuilt name | |
|---|---|---|---|---|
| `bank0` | `0x031C` | `poll_d6c2_then_branch` | `poll_d6c2_then_branch` | re-derived |
| `bank0` | `0x805B` | `index_table_default` | `index_table_default` | re-derived |
| `bank1` | `0x031C` | `call_d2a3_then_d274` | **`FUN_CODE_031c`** | **differs** |
| `bank1` | `0x703A` | `write_r1_to_tmod_and_jump_8801` | `write_r1_to_tmod_and_jump_8801` | re-derived |
| `common` | `0x0512` | `int0_vector_forwarder_to_052f` | `int0_vector_forwarder_to_052f` | re-derived |
| `common` | `0x10FA` | `rearm_timer1_then_set_bit_4_of_internal_41` | `rearm_timer1_then_set_bit_4_of_internal_41` | re-derived |
| `common` | `0x1207` | `bl51_bank_select_0` | `bl51_bank_select_0` | re-derived |

**So: a rebuild re-derives six of the seven, and the seventh is a finding
rather than a negative answer.** `bank1` `0x031C` comes back holding a Ghidra
placeholder — `FUN_CODE_`, one of the forms `isPlaceholderName()` in
`TongFang.java` tests for, read here by parsing that Java rather than by keeping
a second list of the prefixes. A placeholder at a rowless address is a name
**no committed input produces**, which is precisely the case §6 records having no
evidence about. It is reported here and not absorbed into the six.

The rebuilt row's own `annotated` column reads `no`, where the committed row
reads `yes`. That is the census's own predicate working: the row is out of the
population in the rebuilt tree because a name Ghidra wrote is not a
person-chosen name, which is the same route out of the population the fourteen
switch entries took in #631. **The rebuild reproduces the census's finding
rather than contradicting it.**

The obvious reading of that placeholder is the frame §5 already gives these
addresses, and this run does not settle it. §5 of
[`named-without-a-row.md`](named-without-a-row.md) calls all four of the
mid-instruction addresses *not function entry points* — `0x031C` is a
displacement byte inside `sjmp 0x031F` at `0x031B`, not an instruction start at
all — so a fresh analysis finding no function there to carry a name, and writing
one of its own, is consistent with that frame. **What the run does not
establish is why one re-derived and the other did not:** `bank1` `0x031C` and
`bank0` `0x031C` hold the same three bytes, `02 d2 36`, and the second came
back with the committed name. The question is left open here as §4's and §8's
are. The framing is §5's reading of the bytes, made by a linear walk; §5's
table is not restated here on the strength of a rebuild.

## 4. Q2 — the four `pd` call sites

| | address | committed name | rebuilt name | |
|---|---|---|---|---|
| `pd` | `0x3497` | `call_10bc` | `call_10bc` | re-derived |
| `pd` | `0x998B` | `call_10bc` | `call_10bc` | re-derived |
| `pd` | `0x9C1B` | `call_10bc` | `call_10bc` | re-derived |
| `pd` | `0x9C4D` | `call_10bc` | `call_10bc` | re-derived |

The issue asks *which tool puts `add_full_product_to_dptr` at the four call
sites*. **A rebuild cannot answer that as a historical question** — it can only
say what the committed inputs produce today, and what they produce is
`call_10bc`, because #489's rows are themselves committed inputs and they name
the call rather than the callee. The counterfactual is the answerable one and it
is worth having: **a rebuild from the committed inputs does not put
`add_full_product_to_dptr` at those four addresses.**

What the run does *not* say is which tool put that string into the committed
database before any row of this repository existed.
[`named-without-a-row.md`](named-without-a-row.md) §6 records that the string is
in `~00000002.db/db.1.gbf`, and this write-up leaves that exactly where it is.
A row that supersedes a name is not a row that explains it.

## 5. Q3 — the first difference, and what is behind it

The rebuilt export differs from the committed one. **`diff -r` is not the
reading**; the tool classifies every difference, because the question is which
*kind* of thing moved and a byte diff over the export answers neither. (The
block below is the tool's output reflowed for width, with the differences after
the first elided; the tallies and the first-difference line are its own.)

```
245 difference(s): 29 index-row, 30 listing-row, 28 manifest-column,
                  20 c, 23 asm, 56 missing-from-copy, 59 new-in-copy

the first, which is the one Q3 asks for:
  index-row  index.csv bank0 703A -- name: 'thunk_FUN_CODE_e722' -> 'FUN_CODE_703a'
```

**The first difference is of the least interesting kind there is, and saying so
is part of the answer.** It is a name changing from one Ghidra placeholder form
to another at an address no CSV row backs — `thunk_FUN_CODE_e722` becomes
`FUN_CODE_703a`. Neither string is a person-chosen name; the row is
`annotated=no` on both sides. A reader who took "the first differing file" as a
finding about the firmware would be reading a rename of Ghidra's own output as
though it were a change in what the code is.

The two index CSVs are compared row by row and the manifest column by column, so
a difference names the row and the field rather than a byte offset.

The manifest's own counters say which of these differences matter:

| program | `functions` | `seeds_applied` | `annotations_applied` | `annotations_unmatched` | `functions_named` |
|---|---|---|---|---|---|
| `bank0` | 750 → 748 | 1549 | 828 → 823 | **0 → 5** | 697 → 692 |
| `bank1` | 676 | 1487 | 725 → 721 | **0 → 4** | 594 → 589 |
| `common` | 753 → 750 | 1549 | 828 → 823 | 0 → 5 | 136 |
| `pd` | **541 → 546** | 541 | 541 | 0 | 541 |

(`common` borrows `bank0`'s counters by construction — it is an export grouping
rather than a program, and `build_ec_decompile.MANIFEST_PROGRAM_SOURCE` is where
that is said.)

Three things in that table are worth separating.

**`seeds_applied` does not move, anywhere.** The rebuild seeded from the same
seed set the committed database was seeded from, which is what keeps the other
two rows honest: `annotations_applied` falling is not a rebuild that seeded
differently.

**`annotations_unmatched` goes from 0 to 5 and 0 to 4.** This is the finding. In
the committed database every annotation row resolves to a function; in a rebuild
from the same bytes, nine do not. §7 reads those nine.

**`pd` gains five functions, all `seed_basis=auto`, none annotated.** A fresh
auto-analysis of the PD image finds five entry points the committed database's
analysis did not — at `0x6FBE`, `0x70B2`, `0x7194`, `0x9D51` and `0xF366`, all
carrying `FUN_CODE_` names. That is a real difference in what the two trees
contain, in the direction of the rebuild finding more, and it is **not** a claim
that the committed database is wrong about the PD image: a function the
committed analysis split differently can appear as several in a fresh one. It is
recorded here and not resolved.

## 6. Q4 — is the committed database reproducible from the committed inputs

**No, not entirely.** The rebuilt export is not byte-identical to the committed
one, so the committed `.gpr`/`.rep` carries analysis state that
`ec/firmware/GMxMGxx_11.800` plus `ghidra-functions.csv` and
`ghidra-variables.csv` do not re-derive.

This is the answer issue #623 called "a load-bearing fact for the mission's end
state", and it lands on the branch that makes provenance a question of its own.
What is **not** established by it is *how* the committed database acquired that
state. The candidates are ordinary: a hand sync, a later seed pass, or simply
Ghidra's incremental analysis accumulating function bodies over many runs on a
project that has been rebuilt and re-exported repeatedly. Nothing here
distinguishes them, and the nine rows in §7 are where the distinction would show
first.

The three runs agreeing (§ preamble) is evidence that the difference is a
property of the inputs rather than of one run. It is not evidence about which
of the three candidates above it is.

## 7. The nine rows a rebuild cannot resolve

These are the `annotations_unmatched` 5 + 4, and they are the sharpest thing the
run produced. Each is a `ghidra-functions.csv` row that resolves in the
committed database and does not resolve in a rebuild of the same bytes — so
there is no function at that address for the row to name.

| | address | row | the census's own frame read |
|---|---|---|---|
| `bank0` | `0x9000` | `ljmp_703d` | covered — inside `add a,#0x02` at `0x8FFF` |
| `bank0` | `0xE4F0` | `jump_to_f0a3` | entered — `ljmp 0xA374` at `0xE4ED` |
| `bank0` | `0xEDA4` | `mov_c_from_bit_0x22` | entered — `inc r6` at `0xEDA3` |
| `bank0` | `0xEF12` | `ajmp_0xe822` | covered — inside `mov r7,#0x01` at `0xEF11` |
| `bank0` | `0xF0A3` | `gate_on_a_then_set_0a56_block` | entered — `inc r7` at `0xF0A2` |
| `bank1` | `0xC322` | `xch_rrc_at_r0` | covered — inside `lcall 0xC613` at `0x14321` |
| `bank1` | `0xD236` | `call_d2a3_then_d274` | covered — inside `lcall 0xD018` at `0x15235` |
| `bank1` | `0xE582` | `read_code_pair_by_r7_index_then_call_889e` | covered — inside `lcall 0xE5D6` at `0x16580` |
| `bank1` | `0xF030` | `operand_of_mov_dptr_f02f` | covered — inside `mov dptr,#0xF0A1` at `0x1702F` |

The frame read is `second_copy_census.framing()` over the committed firmware —
the same 24-anchor linear walk §5 uses, not a new method. **The nine split, and
the split is the honest part of this table.**

**Six read `covered`: the address is inside a real instruction, not an
instruction start.** The framing docstring's own caveat applies to every line of
them — *"not found to be an instruction start by this read, which is not the
same as not being one."* The names corroborate without proving anything: one of
the nine is literally `operand_of_mov_dptr_f02f`, and the read puts `bank1`
`0xF030` inside the `mov dptr,#0xF0A1` at `0x1702F`.

**Three read `entered`: the address *is* an instruction start, and the framing
read does not explain their non-resolution.** For those, the mechanism is
visible in the rebuilt export's own function boundaries, and it is a different
one — the address is framed *inside* a larger function, so there is no function
standing at it:

| address | committed | rebuilt — what covers it |
|---|---|---|
| `bank0` `0xE4F0` | its own row, `0xE4F0`–`0xE4F2` | inside `init_0a4d_block_and_count`, `0xE4B9`–`0xE4FD` |
| `bank0` `0xEDA4` | its own row, `0xEDA4`–`0xEDA5` | inside `call_0ea2_with_0xfa`, `0xED9B`–`0xEDA5` |
| `bank0` `0xF0A3` | its own row, `0xF0A3`–`0xF0B0` | inside `FUN_CODE_f0a1`, `0xF0A1`–`0xF0B0` |

That second shape is what
[`nested-export-frames.md`](nested-export-frames.md) already censuses, and
[`named-without-a-row.md`](named-without-a-row.md) §8.2 asks in its row-backed
form whether the exporter should drop a nested function a CSV row backs. This
is an instance of that question from the other side: the exporter keeps backed
nested functions, and a *fresh* analysis does not produce them.

**What this establishes, and what it does not.** All nine are rows at addresses
that a rebuild finds no function entry point at — six because the address is
inside an instruction, three because a larger function covers it. That is the
same category §5 reaches from a linear walk, reached here by an independent
method, and §5's argument extends to nine addresses it never looked at. **It
does not establish that those nine rows are wrong.** A row at an address that is
not a function entry point is what §5 calls the wrong instrument for the job,
and the run is evidence that the instrument does not reach there — not evidence
that the rows should be deleted. Nothing in this write-up removes a row, and
`ghidra-functions.csv` is byte-untouched.

## 8. What this does not establish

- **Which tool put `add_full_product_to_dptr` in the committed database.** §4
  answers the counterfactual and leaves the history alone.
- **Why the committed database frames those nine the way it does.** §6 lists
  three candidates and nothing here chooses between them.
- **Whether the PD image's five extra functions are real.** §5 records them; a
  fresh analysis finding more entry points is not by itself a claim that the
  committed database missed them.
- **Anything about a Ghidra other than 12.1.3, a JVM other than Temurin 21, or a
  machine other than this runner.** Three runs agreeing is three runs.
- **The provenance of the seven names in the committed database.** The run
  answers whether the committed inputs re-derive them. Six do and one does not;
  that is a fact about the inputs, not about the tool that wrote the string.

## 9. Reproducing every number above

The offline half, no Ghidra and no network:

```
python3 ec/tools/rebuild_provenance.py --self-test   # the classifier and the refusal
python3 ec/tools/second_copy_census.py --check       # the population, per address
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/check_findings_frozen.py
python3 ec/tools/check_no_append_logs.py
python3 ec/tools/build_ec_decompile.py --work "$tmp" --check
```

The measurement, which needs Ghidra and a scratch directory outside the
repository:

```
python3 ec/tools/rebuild_provenance.py --run
```

`--self-test` is the one that matters for a reader who cannot run Ghidra. It
holds the two things that can be wrong on a machine that never runs a rebuild:
the diff classifier, over a fixture tree differing in exactly one `.c`, one
`.asm`, one `index.csv` row, one `listing-index.csv` row, three `manifest.csv`
columns and one file present on one side only — plus an identical pair, so the
empty answer is a shape the tool can produce and not only a failure; and the
partial-run guard, at both ends — a short row count, a non-zero exit, a missing
manifest and a program that was never exported are each refused, and a finished
run is let through. The refusal is exercised end to end: `--run` is pointed at a
scratch path inside a fixture repository and must refuse **before** creating
anything, which the test then asserts by the absence of the directory.

`rebuild_provenance.py` has **no `--check` mode, deliberately.** The answers
come from a rebuild, so there is nothing a gate could ratchet on without Ghidra
and a scratch copy per run; and what a `--check` *could* assert — that the
committed `.c` files and `manifest.csv` are unaltered — is already held by
`c-digests.csv` and `build_ec_decompile.py --check`. A second check of that here
would be a check that has quietly stopped checking anything else.

The tool is not wired into `.github/scripts/agent-gates.sh`, and cannot be from
an agent branch: that file is template-copied and this branch's token has no
`workflow` scope. It is invoked directly, exactly as `second_copy_census.py` is.

## 10. Follow-ups this opens

Stated rather than acted on, per the mission's rule that a finding which opens a
question says so.

1. **The provenance of the committed database is now a question of its own**
   (§6). Nine rows resolve there and not in a rebuild of the same bytes. Which
   of the three candidates in §6 it is, is settled by looking at how the
   committed project's function table got those boundaries — a question about
   the database's history, not about the bytes.
2. **The nine rows, and what should be done with them** (§7). They are outside
   the census population (they carry rows) and outside `grade_name_basis.py`'s
   vocabulary of bases, which has no value for "this address is not a function
   entry point". That is the same gap §7 of
   [`named-without-a-row.md`](named-without-a-row.md) names, now with nine
   instances instead of one argument.
3. **The PD image's five extra entry points** (§5). Whether they are five
   functions the committed database merged, or five it never found, is a
   reading of the PD image's bytes and is not this write-up's.
4. **§8's follow-ups are still open** and are not touched here — the four
   mid-instruction frames and the two nested frames that
   [`named-without-a-row.md`](named-without-a-row.md) §8 already lists. §3 and
   §7 corroborate the category from a second direction; neither settles an
   address.
