# `reassembly.csv`'s `name` column describes the listing, so it is compared and not trusted

The write-up for [issue
#627](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/627), which asked
what the `name` column of [`../../ec/ghidra/reassembly.csv`](../../ec/ghidra/reassembly.csv)
is for and that the answer be held either way: compare it, or say it is
unverified and drop it. It is compared. This is why that is the whole of the
answer, what was already stale when the answer was written, and one thing the
measurement turned up that this change deliberately does not fix.

**Offline throughout.** No laptop, no Windows box, no EC register, no live
register read, and no assembler: every figure below is a read of two committed
CSVs and the listings they name, taken with the command shown beside it. Nothing
here is a hardware or firmware observation, because there is none.

## The decision, and the distinction that decides it

**The column describes the listing. It is not a measurement.** Everything else
in the row — `outcome`, `listing_digest`, `instructions_checked`,
`instructions_unchecked`, `assembler` — records what a re-encode observed at a
moment. `name` does not: `write_report()` copies the name the listing index held
at report time, and the index is itself a build product with its own `--check`.
Copying a value into a measured cell asserts an observation nobody made, which
is the hazard `add_digest_column()` is built to refuse and which
`check()`'s own failure text says out loud ("Copying the new digest into the
CSV by hand re-arms this check and verifies nothing"). Copying a value into
`name` asserts nothing at all: it restores agreement between a file and its
source.

That one distinction is the whole safety argument, and it is why the two
columns are now handled by two different kinds of writer. `--add-digest-column`
is **one-shot** — after the column exists, the only writer of a digest has to be
the run that measures it. `--refresh-name-column` is **repeatable**, because
re-copying a stale name re-establishes an agreement and re-arms no detector.

The issue offered dropping the column as the other defensible answer. It is
defensible; this change took the other one, because the column is the only
human-readable label the file carries over its rows of bare addresses, and
because the file it is copied from is a checked source of truth rather than a
second shadow that might itself have drifted — see the header agreement below.

**What the comparison establishes, and what it does not.** That the report and
the listing index still agree about what to call each function. Not that the
name is a *good* one. Naming a function is a judgement about what it does, and
the judgement belongs to the annotation and the disassembly; a name that agrees
with the index is a name the index wrote, in the same sense that a digest that
agrees is a digest the report was measured with. `compare_names()` says so in
its own docstring and the failure message says it again, because the failure
message is what a reader sees at the moment they are tempted to read a passing
line as a verified one.

## What was already stale, measured on the tree this change starts from

Read with a plain join on `(program, addr)`, and by the run that repairs it: the
count below is what `--refresh-name-column` printed when this change ran it, and
what `--check` reported as name disagreements on the tree before it.

- The two key sets were **identical** — 2,717 rows each, no orphan in either
  direction — so the disagreement that follows is not a shape problem.
- **181 rows disagreed on `name`**, all in one direction: the index holds a real
  name, the report holds the placeholder it had replaced. `FUN_CODE_0012` against
  `ret_only_0012`, `thunk_FUN_CODE_1150` against `table_entry_to_1150`. By
  program: `common` 114, `pd` 41, `bank1` 14, `bank0` 12. **176 of the 181**
  have an old name matching `^(FUN_CODE|thunk_FUN_CODE|CODE|FUNC)_` and **2** have
  a new one, so the drift is overwhelmingly "the report never learned a rename
  away from a placeholder" rather than a rename that moved. That pattern is a
  local check, not this repository's `isPlaceholderName()` — two drifted copies
  of which are a separate open item, named below — so it is measuring the shape
  of the old names and not applying the project's rule to them.
- **The `.asm` header carries the name too, and it agreed with the index for
  every row and every one of the 2,717** — 0 differences. The name is therefore
  stated twice in the tree and the two copies agree; the report was the only
  stale one. That is what makes the index a sound thing to compare against:
  a second copy that might itself have drifted would have made the check a
  comparison between two unverified things.

The header agreement is measured here and **not checked by this change**. It is
a claim about a different file from a different writer
(`ec/tools/build_ec_decompile.py`, beside its other export invariants), and it is
what justifies trusting the index rather than what this issue asked for. It is
recorded, not built.

The direction of the drift is the finding, and it is the one this repository
keeps meeting from the other side: the single column a rename moves is the
single column nothing verified, so a stale name in a build product was
indistinguishable from a correct one, and the only way to have learned how many
there were was to read the file.

## The change

**`--check` compares the name.** `compare_names()` is a sibling of
`compare_digests()` and returns failure tuples in the same six fields, so
`check()` prints the two kinds of failure through one printer and both count
against `MOVED_CAP`. A report row with **no** index row is named rather than
skipped and a **blank** name is named rather than read as agreement — the same
rule `compare_digests()` states, and the shape a checker fails in when it treats
"nothing to compare" as agreement. Neither counts towards the `compared` figure
on the summary line, because "compared" has to mean two values were put against
each other.

The line sits beside the digest line rather than inside it, because the two need
different repairs and one message cannot carry both: a stale digest is fixed by
re-reporting with the pinned assembler, and a stale name is fixed by copying the
index's spelling. The remediation pointer names `--refresh-name-column` for the
same reason `REPORT_COMMAND` names the re-report for the digest.

**`--refresh-name-column` writes that one cell and proves it.** Its guards are
the content of the change rather than the copying:

- It **proves it changed one column.** The report is read, written, read back,
  and every non-`name` cell of every row is required to be identical to what the
  first read gave; the header and the row order are compared too, since a writer
  that reordered rows has changed the report without changing a cell. Any
  difference and the original bytes are put back. The comparison is between two
  reads of the *file*, not between the dicts in between, so a quoting rule, a
  line terminator or a field the in-memory rows never saw still fails it.
- It **never computes a measurement.** No outcome, no digest, no
  `instructions_*` cell and no assembler version is recomputed. They are read
  and copied through, and the read-back fails the run if any of them moved. That
  is what keeps it clear of the hazard `refuses_committed_report()` names — a
  report written by a different assembler.
- It **refuses when the key sets disagree**, in both directions and before
  anything is written, because copying by key is otherwise a way to invent a name
  for a row with no listing and to leave an index row with no report row
  unmentioned. Both are already reported by `--check`; this must not paper over
  them.
- It **says what it moved** — the count, the file, and the first few rows with
  both spellings — so the diff is legible in review and the figure is one the
  PR can cite rather than assert.

`refuses_committed_report()` keeps its predicate and keeps refusing a per-row
write to the committed report. Its *message* said the file is "written by
`--report` and by nothing else", which stopped being true when this writer
arrived, so that one sentence was corrected in place, with the correction left
visible in the docstring. What the guard protects is the report's **results**,
and a name is not one.

The diff this issue asked for is the diff in
[`../../ec/ghidra/reassembly.csv`](../../ec/ghidra/reassembly.csv), and it is
the `name` column and nothing else — no outcome, no digest, no instruction
count, no assembler cell. It was produced by the flag, not by hand.

## The committed tree now passes

```
$ python3 ec/tools/verify_reassembly.py --check
  listing bytes: 45661 instruction(s) checked against the firmware, 0 disagreement(s)
  reassembly report: 2586 match, 73 partial, 58 assembler-gap, 0 listing-gap, 0 mismatch (of 2717)
  listing digests: 2717 compared against the committed report, 0 disagreement(s)
  listing names: 2717 compared against the listing index, 0 disagreement(s)
  all checks passed
```

The byte, digest and tally lines are unchanged from before this change, which is
the point: refreshing a copy moved a copy and moved no measurement. Before the
refresh the same run reported 181 name disagreements and failed; the fixture for
the other direction is `self_test()`'s, which drives a renamed listing, a blank
name, a row with no index row, a key set that disagrees in both directions, and a
report the writer cannot round-trip — none of them committed, so none of them is a
row another branch has to merge.

`agent-gates.sh` already runs `--check` and `--self-test` in the cheap tier, so
the comparison is enforced from the commit it lands on with no pipeline change.
`.github/scripts/` is template-copied and is not edited here, which is the reason
none was needed.

## A finding, measured and deliberately not fixed here

**Thirteen committed rows carry `sdas8051 02.00` where 2,704 carry
`sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14`.**

```
$ python3 - <<'EOF'
import csv, collections
rows = list(csv.DictReader(open("ec/ghidra/reassembly.csv", newline="")))
for v, n in collections.Counter(r["assembler"] for r in rows).items():
    print("%5d  %s" % (n, v))
EOF
 2704  sdas8051 05.50.4+NoICE+SDCCmods-WIP-R14
   13  sdas8051 02.00
```

This conflicts with
[`thunk-prefix-collision.md`](thunk-prefix-collision.md), "One generated file
could not be regenerated here, and why". That write-up records that the local
`02.00` run was **discarded**, and that "what replaced it is the seven `name`
cells" — but these thirteen rows have a `02.00` **assembler** cell, which is a
measured cell that a discarded run cannot have contributed. The two accounts
cannot both be complete descriptions of the committed file: either the run was
not discarded in the sense the paragraph means, or what replaced it was more
than seven `name` cells. Which of the two is wrong is not settled here, and
nothing below settles it.

Two things this change can say about it, and one it cannot:

- The thirteen rows are **disjoint from the 181**: no row whose name was stale
  is one of them. The two populations are separate, so the name refresh did not
  create this, remove it, or disturb it.
- `assembler` is a **measured** cell, so the distinction this change is built
  on is the sharpest available argument for it: `--refresh-name-column` cannot
  reach those thirteen rows' assembler cells even in principle, because it
  proves from the written file that nothing but `name` moved.
- **Which run produced them is not settled here.** The pinned
  `05.50.4+NoICE+SDCCmods-WIP-R14` is not installed on an agent runner, and
  answering the question means reading the file's own history — which commit
  last wrote each of the thirteen rows, and whether they were a partial run, a
  hand-merge or something else. That is a question for a human with the pinned
  tool and the full history, and it is raised as a follow-up with this
  measurement attached rather than guessed at here.

**Not fixed here, on purpose.** Re-reporting those rows needs the pinned
assembler, and a full `--report` against the runner's `02.00` would rewrite
almost every row of the file and change measurements in order to fix something
that is not a measurement. `assembler_version()` records what a different ASxxxx
does to the tallies: `match` 2,574 → 2,621, `assembler-gap` 58 → 6, `mismatch`
0 → 0. A measurement is not traded for a cleanup.

## Why a full `--report` is not the answer to a stale name

Because it re-measures everything to fix a copy, and this runner's assembler is
a different and older ASxxxx than the one the committed report was measured
with. `--refresh-name-column` exists so the repair does not have that price, and
so the price is visible: the guard that proves one column moved is what makes a
second writer of a build product safe here, and a `--report` offers no such
guarantee because it is entitled to move every cell.

## Out of scope, and named so the next reader does not have to guess

- **The `.asm` header ↔ listing-index name invariant**, measured here to hold
  for every row and not checked. Belongs beside `build_ec_decompile.py`.
- **The `program` quirk in the common-area headers** — 753 index rows say
  `common` where the `.asm` header spells `bank0`. Measured, unrelated to the
  name column, another issue.
- **Whether the names are good names.** A comparison holds the copy. The
  judgement is the annotation's, and re-reading it is not something a hash or a
  join can do.
- **Whether the disassembly is right.** Unchanged: that is the re-encode, and it
  has no schedule.
- **The placeholder-naming rules and the two drifted copies of
  `isPlaceholderName()`** — already flagged in
  [`thunk-prefix-collision.md`](thunk-prefix-collision.md) as a separate item.
  `refresh_name_column()` does not touch `ghidra/scripts/`: the pattern above is
  a local check written to describe the shape of what the report held, and
  applying the project's own predicate to those rows is that item's work, not
  this change's.
