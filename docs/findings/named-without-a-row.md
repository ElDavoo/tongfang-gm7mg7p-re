# The 25 functions that carry a name no CSV row wrote (issue #601)

`docs/findings.md` §18's correction of 2026-09-25 records 25 exported functions
whose name is not one any row of `ec/annotations/ghidra-functions.csv` wrote.
It splits them 18 automatic / 7 readable and then argues, by exhaustion of the
export path, that the readable seven are symbols already sitting in the
committed project. The argument is sound and §18 is not retracted here. What was
missing is the next question: **where does the name at each of those addresses
come from?** The answer turned out to be readable out of committed files, and it
is now a check rather than a hand-list —
`ec/tools/second_copy_census.py --check`, reached from the gate through
`build_ec_decompile.py --check`.

Everything below is a static reading of committed files. No register was read, no
machine was observed, and nothing here was seen in Windows. Every number is a
measurement over `ec/firmware/GMxMGxx_11.800` (SHA-256
`158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4`) and the
committed export. The one Ghidra run involved is the export-only re-export in
§9, which was run to confirm that this change leaves the generated tree alone;
it produced nothing new and is not the source of any claim above.

## 1. The two questions, and only one of them had an answer

Issue #601 asks for each of the seven either a `ghidra-functions.csv` row, or
the exemption recorded where the ledger reads it. The two halves of the
question that preceded it are worth keeping apart, because they have different
answers:

| | claim | standing after this |
|---|---|---|
| premise | no script in `ghidra/scripts/` renames a rowless address — `SeedFunctions.java:100` passes `createFunction(a, null)`, `ApplyAnnotations.java:212` renames only where a row resolved, `ExportDecompile.java` only reads `f.getName()` | **still true.** §18's exhaustion argument about *where the symbol lives* is undisturbed |
| conclusion | so a `--mode rebuild-project` from the CSV alone would not reproduce these names | **does not follow.** The premise is about this repository's scripts and says nothing about Ghidra's own analysis; see §6 |

What replaces the conclusion is a fact the original argument never asked for:
**the name at each of the seven is the name of a function a CSV row already
backs**, and the address's own bytes say which one.

## 2. The seven, read out of the committed listings

Each row is the committed listing's own line, and the target column is checked
against the firmware and against the target's committed row by the tool.

| address | bytes | instruction | target | the target's committed row |
|---|---|---|---|---|
| `bank0` `0x031C` `poll_d6c2_then_branch` | `02 d2 36` | `ljmp 0xD236` | `bank0` `0xD236` | `poll_d6c2_then_branch` |
| `bank0` `0x805B` `index_table_default` | `02 82 74` | `ljmp 0x8274` | `bank0` `0x8274` | `index_table_default` |
| `bank1` `0x031C` `call_d2a3_then_d274` | `02 d2 36` | `ljmp 0xD236` | `bank1` `0xD236` | `call_d2a3_then_d274` |
| `bank1` `0x703A` `write_r1_to_tmod_and_jump_8801` | `02 e7 22` | `ljmp 0xE722` | `bank1` `0xE722` | `write_r1_to_tmod_and_jump_8801` |
| `common` `0x0512` `int0_vector_forwarder_to_052f` | `01 03` | `ajmp 0x0003` | `common` `0x0003` | `int0_vector_forwarder_to_052f` |
| `common` `0x1207` `bl51_bank_select_0` | `02 11 00` | `ljmp 0x1100` | `common` `0x1100` | `bl51_bank_select_0` (`name_basis: abi-symbol`) |
| `pd` `0x0000` `c_startup_idata_clear` | `02 05 00` | `ljmp 0x0500` | `pd` `0x0500` | `c_startup_idata_clear` |

The same fact is visible from the other side, and it is the one worth having: a
body that is nothing but a transfer of control decompiles to what the transfer
reaches, so the stub's `.c` **is** the target's decompilation. Measured over the
seven, `ec/decompiled/<stub>.c` and `ec/decompiled/<target>.c` are identical
once each file's `//` header and the target's annotation plate are off — the
plate is the only reason they differ as files, and the target carries it because
it has a row. `second_copy_census.py --self-test` pins all seven.

`common` `0x0512` is a two-hop forwarder and the name is right about the end of
it: `ajmp 0x0003` reaches the int0 vector slot, and `common 0x0003` is
`ljmp 0x052F`, which is `int0_target_is_one_byte_reti` — a handler this
repository has already established is one `reti` byte
([`subsystems.md`](../../ec/annotations/subsystems.md) §3).

## 3. Four more of the 25, same shape, different transfer

The seven are the ones §18 named, and they are the ones the issue named. The
same read applied to the whole population finds **four more**: `pd` `0x3497`,
`0x998B`, `0x9C1B` and `0x9C4D`, each exactly `12 10 bc` — `lcall 0x10BC` — into
`pd` `0x10BC` `add_full_product_to_dptr`, which is a CSV row's function. A `mov
B,#0xNN` immediately precedes each, which is the argument setup for the helper
the call reaches.

So the honest figure is 11, not 7, and `ec/annotations/subsystems.md` §2 already
counted them: its hand-list of "the other 11 are second copies of a name that
does have a CSV row" is this set. That hand-list is now derived rather than
transcribed (§7).

The 14 that remain are Ghidra's own: the committed `.c` declares each inside a
`switchD_CODE:<addr>::` namespace — `caseD_0` at eleven bank1 addresses, plus
`caseD_6`, `caseD_1` and `default`. That is the namespace Ghidra's switch
analysis creates and the prefix `ExportDecompile.java:339` already keys
`isPlaceholderName()` on. §18 counted these 14 as automatic; that stands, and
§4 says what the bytes at them are *not* evidence of.

## 4. What the bytes are not evidence of

Measured over the 25: **23 of them begin with a single `ljmp` or `lcall`.**
Twelve of those reach somewhere real — `bank1 0x8A80` is `ljmp 0x8AA7`, and
`0x8AA7` is `clear_06f9_bits_0_3_then_call_abee` — while the name at the site is
still Ghidra's. So a classifier built on "it is a jump" would call 23 of 25
explained and explain none of the 12 it should not have. The discriminator is
the name *and* the row behind it, and the tool tries them in that order: name
equality against a row-backed target first, the switch namespace second,
`unexplained` only after both fail.

`unexplained` is a refusal, and `--check` fails on it. It means this method found
no mechanism for the name; it does not mean the name is absent, project-only or
automatic. The self-test's fixtures are what keep that bucket reachable — a
second copy that is not a transfer, a transfer whose target has no row behind
it, a transfer whose target is a row under another name, a transfer whose target
is at or above `0x8000` seen from the common area (where no byte says which bank
is mapped, so the read declines), a listing that disagrees with the firmware, and
a listing that is not there to disagree.

## 5. Where the frame is — the part that is new

The seven addresses carry a name because a transfer points at a row-backed
function. A second, independent question is whether the *frame* belongs there,
and the answer is not the same for all of them. It is read mechanically: does a
linear walk from the bytes to the left land on the address or step over it, and
if it lands, what committed function does the instruction that lands belong to.

| address | frame | the committed function it is measured against |
|---|---|---|
| `bank0` `0x031C` | `mid-instruction` | — the address is the displacement byte of the `sjmp 0x031F` at `0x031B` |
| `bank1` `0x031C` | `mid-instruction` | — the same three bytes; `0x031C` is in the common area |
| `bank1` `0x703A` | `mid-instruction` | — the displacement byte of the `jnc 0x703D` at `0x7039` |
| `common` `0x0512` | `mid-instruction` | — inside the `cjne a,#0x01,0x0517` at `0x0511` |
| `common` `0x1207` | `after-a-function` | `common 0x1204` `FUN_CODE_1204`, listed `0x1204`-`0x1206` |
| `pd` `0x0000` | `vector` | — the PD image's own first byte |
| `bank0` `0x805B` | `inside-a-function` | `bank0 0x8054` `index_case_00`, listed `0x8054`-`0x806B` |

**`mid-instruction` is the finding, and it is a claim about the bytes, stated
with its method.** For these four, all 24 anchors in the 24-byte window to the
left step over the address and none lands on it, and the instruction that covers
it is the one named in the table. The stronger half of the argument is that the
two readings are not equally good: under the frame's reading the byte *before*
each is a truncated opcode — `0x031B` would be a bare `80` (`sjmp`) with its
displacement byte taken by the frame, `0x7039` a bare `50` (`jnc`), `0x0511` a
bare `b4` (`cjne`) two bytes short — and under the other reading every
instruction in the window is whole. The window is code either way, which is what
rules out the other explanation `converges_from()`'s docstring offers for a site
nobody syncs onto: *"it may simply be preceded by data (a dispatch table,
padding) that no linear walk can decode into alignment"*. Read the linear
sequence at `0x0312`-`0x031F` and it is an if/else ending in `sjmp 0x031F` /
`setb 0x26.6`; at `0x7030`-`0x703C`, a three-arm dispatch on R3; at
`0x050D`-`0x0517`, a compare and two stores.

The consequence is narrow and worth stating precisely: **these four addresses
are not function entry points**, so the call-target byte scan that seeded them
matched a branch operand, not a call opcode. That is the blind spot
[`bank-call-audit.md`](../../ec/annotations/bank-call-audit.md) §1 already states
as a reason to treat the census as an upper bound, now with four named
instances. It is a separate piece of work from this issue and is left as a
follow-up (§8); nothing here edits a seed set, a listing or a CSV.

`bank0 0x805B` is the opposite case and the reason the boundary is asked per
address rather than per population. `ec/decompiled/bank0/8054.asm` already
contains the frame: `0x8058` is `jb 0xE7,0x805E` and `0x805B` is what execution
reaches when that branch is not taken. So `0x805B` is a genuine second entry
into `0x8274` — the default arm of the bank0 `0x8038` index dispatch, which is
exactly what the name says — drawn inside a function the export had already
framed. The name is right and the boundary is a second entry, and the two are
independent findings.

`common 0x1207` is the case `subsystems.md` §3 left open, and the committed
listing settles the framing half of it: `ec/decompiled/common/1204.asm` is
`90 bf 62` (`mov DPTR,#0xBF62`) and is its own exported row, so `0x1204`-`0x1207`
is one two-instruction six-byte thunk of the shape §4 describes, split in two by
a call-target frame, with the second half inheriting the first half's name.
Whether the common area carries a second copy of the stub or Ghidra split one
routine is a question about the vendor's linker output that the bytes here do not
decide; what the bytes decide is that the frame is at the second half of a
thunk, not at a second thunk.

## 6. What is still open: which tool wrote the name

**Not established: whether `--mode rebuild-project` from the CSV alone
re-derives these names.** No rebuild was run here — the export-only re-export in
§9 reuses the committed project and is not one — and this repository cannot
answer the question from text. What the bytes establish is the name's *value*:
it is the target's, and the target is a committed row. Which tool put that value
at the stub's address is a different question, and the two must not be run
together.

The one piece of evidence that bears on it points away from a rebuild
reproducing the names, and it is worth saying why rather than leaving it out.
`isPlaceholderName()` lists `thunk_` because that is how Ghidra renders an
auto-thunk (§18), and all seven of these rows are `annotated=yes`, which means
their names match none of `FUN_`, `LAB_`, `SUB_`, `thunk_`, `FUNCODE` or
`switchD_`. So the bare target name at the stub is not the form this Ghidra
produces for a transfer-only function on its own. That is an inference from the
exporter's own list and the index's `annotated` column, not a measurement of a
rebuild — it is the same kind of reasoning §18's exhaustion argument is, and no
stronger.

The issue's inference — that the premise about this repository's scripts implies
the conclusion about a rebuild — is the step that does not hold either way: the
premise ranges over `ghidra/scripts/`, the conclusion over Ghidra. Answering it
needs a rebuild in a scratch copy of the project, which writes the project
database and is therefore not something this change does; §18 already records
the `NotOwnerException` that a rebuild in place hits, and that defect is its own
issue.

**Also open: who named the four `pd` call sites.** Their name equals the CSV
row at `pd 0x10BC`, and the committed project holds that string
(`grep -c add_full_product_to_dptr` over `~00000002.db/db.1.gbf` finds it), but
no script here writes a name at a rowless address, so the same exhaustion
argument applies to them as to the seven. The census answers *what* the name is
worth; it does not claim to know which tool set it.

**A re-measurement of §18's grep, unchanged.** `index_table_default` and
`bl51_bank_select_0` are in `~00000000.db/db.1.gbf` and `~00000001.db/db.1.gbf`,
and `c_startup_idata_clear` is in `~00000002.db/db.1.gbf`; the other four of the
seven are in none of them. A hit is real and a miss proves nothing, which is
§18's own caveat and is why the argument above rests on the export path and not
on grep.

## 7. The branch taken, and why the other one was declined

The exemption branch, for all eleven — recorded where the ledger reads it
(`subsystems.md` §2) and made checkable. A row at a stub address has only two
possible contents and neither is an improvement:

- **Restate the target's name.** At an address whose committed bytes are one
  transfer and nothing else, that asserts a mechanism where the mechanism is the
  transfer, and it is a second row claiming a function the target's row already
  claims. It also breaks the grading rule in
  [`name-basis-and-groups.md`](name-basis-and-groups.md): the only footing at the
  stub is the jump, so `code-shape` is generous and the real basis — the
  target's row — is not a value the vocabulary has.
- **Rename the stub to describe the jump** (`tail_jump_to_d236`). That discards
  the link to the target, moves eleven `.c` files, `index.csv`, and the names
  that `findings.md` §18 and `subsystems.md` §2 both cite, and trades a correct
  pointer for a locally-true label.

There is now a third reason, and it is the one that decided it. For four of the
seven the address is **not a function entry point at all** (§5), so a row there
would assert a boundary the bytes contradict — a `ghidra-functions.csv` row is
the wrong instrument for recording something that is not a function.

`ghidra-functions.csv` is therefore byte-untouched by this change, which is also
what keeps `grade_name_basis.py --check` a clean no-op: the only committed file
whose grading could have moved is not one this change edits.

## 8. Follow-ups this opens

Stated here rather than acted on, per the mission's rule that a finding which
opens a question says so:

1. **The call-target census matched four branch operands.** `bank0 0x031C`,
   `bank1 0x031C`, `bank1 0x703A` and `common 0x0512` are `02`/`01` bytes that
   are a displacement or an immediate in a real instruction, and each is now an
   exported function that should not be. `bank-call-audit.md` §1 calls the
   census an upper bound; these four make the bound concrete, and the census
   itself, the seed set and the four listings are all untouched here.
2. **Two frames sit inside functions the export already framed** — `bank0 0x805B`
   inside `index_case_00`, `pd 0x9C4D` inside
   `read_xdata_to_r6_set_dptr_069a` — and `bank0 0x805B`'s is the branch-not-taken
   arm of a real test, so the export carries two overlapping functions. Whether
   the exporter should drop a nested function whose parent covers it is a
   question about `ExportListing.java`, not about these rows.
3. **One annotated row one byte away from `0x703A` may have the same problem.**
   `bank1 0x703F` `forwarder_to_e322` is a hand-decoded row whose comment reads
   *"Three bytes: ljmp 0xE322, with nothing executed here"*, `name_basis:
   code-shape`. Read linearly from `0x703D`, those three bytes are the `cjne
   r3,#0xFE,0x7042`'s displacement, a `movx a,@r1` and a `ret` — the same shape
   as the frame at `0x703A`, one arm of the same dispatch. That is this issue's
   read and nothing more: the row has a human citation, it is outside the
   population this census classifies, and **it is left exactly as it is**.
4. **The rebuild question** (§6), which needs a scratch project and a human.

## 9. Reproducing every number above

No Ghidra, no network, no scratch directory:

```
python3 ec/tools/second_copy_census.py --check      # the census, per address
python3 ec/tools/second_copy_census.py --self-test  # the readings and the refusals
python3 ec/tools/build_ec_decompile.py --work "$tmp" --check
python3 ec/tools/grade_name_basis.py --check
```

`build_ec_decompile.py --check` is unchanged in its numbers — 25
named-without-row, 7 applied-but-unflagged, 1,872 rows each backing one index
row, 1,890 functions named, 0 `annotation_ledger_mismatches()` — and now prints
the verdict beside each of the 25 and fails on an unexplained one.
`grade_name_basis.py --check` is a clean no-op, which is the evidence that
`ghidra-functions.csv` was not disturbed.

**The export-only re-export came back byte-identical.** Run in a copy of the
repository rather than in the tree, because `write_outputs()` opens with
`shutil.rmtree(OUTDIR)` and `OUTDIR` is the committed `ec/decompiled` — the
`--work` directory is where the project copy and Ghidra's output go, not where
the export lands. One step was needed first, and it is the one §18 predicts: the
committed `ec/ghidra/project/ec.rep/project.prp` is owned by `dave`, so
`analyzeHeadless` refuses the copy with `NotOwnerException: Project is owned by
dave`. Correcting the owner **in the copy only** and re-running gives 746 / 676
/ 753 / 535 functions across bank0 / bank1 / common / pd, 0 failed, and
`diff -r ec/decompiled` against the committed tree reports **0 differing files**
— `index.csv`, `listing-index.csv`, the 2,710 `.c` and the 2,710 `.asm` alike,
as does `ec/ghidra/manifest.csv`. No diff is the evidence that taking the
exemption branch left the export alone: this change edits nothing a Ghidra run
produces. A diff there would have been a finding to report, not to absorb.

The `NotOwnerException` itself is §18's own separate issue and is **not** fixed
here — the fix is editing a committed project database, which this repository
forbids.

`second_copy_census.py` is a new file and is not wired into
`.github/scripts/agent-gates.sh`: the check is reachable from the
already-gated `build_ec_decompile.py --check`, and CLAUDE.md sends pipeline-file
changes through `ElDavoo/agent-pipeline` upstream.
