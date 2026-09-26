# A claim about a capture is columnar, and a claim about a fixture is not (issue #975)

The write-up for [issue
#975](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/975), which asked
who owns the `addr`-column question
[`check_testdata_row_claims.py`](../ec/tools/check_testdata_row_claims.py) had
deferred, and why one skip in `check_capture_claims.py` was silent. What this
branch adds is **a census, an owner and a self-report**: a **dated** claim in
the testdata index's third column is now held to the `addr` column of the
`.csv` members of the file set its date resolved to, every other claim keeps
the textual read, and the capture checker now names and counts the files it
reads in full and finds nothing in.

**Nothing here is a live test, and no capture is opened.** It is index/prose
agreement over committed text, the same class of claim as
[`testdata-third-column-claims.md`](testdata-third-column-claims.md) and
[`testdata-row-claims-dated-capture.md`](testdata-row-claims-dated-capture.md):
the files under `evidence/ec-watch/` and `ec/tools/testdata/` are read as text
and as CSV, and no EC, no firmware image and no laptop is involved.

**Not claimed: that any third-column claim is wrong.** Row 7's two were and
remain `resolved`; the change is the question asked of them, not the answer.

## The census, measured on this tree, 2026-09-26

Everything here is read-only over committed text: the third column of
`ec/tools/testdata/README.md`, the committed captures, and the two tools' own
functions, re-derived from the tools rather than copied from the plan.

**1. The two readings, over the column's checked claims.** 30 claims are
checked, across **15 distinct rows**.

| reading | rows admitting at least one literal |
|---|---|
| textual — does the file carry `0xNNNN` anywhere, in any case | **15 of 15** |
| `addr`-column — only a `.csv` row's `addr` field counts, `#` headers dropped | **13 of 15** |

Exactly **3 of the 30 claims flip**, all one way (textual resolves, columnar
does not): row 6's `0x0784`, and row 8's **`0x0F5D` and `0x0F5F`**. **Zero**
flip the other way. Both flipping rows are the ones whose first column resolves
to a **`.txt`-only** set — 6 files for row 6, 4 for row 8, all `ecrw.py dump`
output with no column at all. There is no `addr` column to read, so a blanket
columnar rule would turn two currently-correct rows red.

> **This corrects the plan's figure, not the tool's.** The plan this branch was
> built from named row 8's second flipping literal `0x0F5C`. Row 8's literals
> are `0x0F5D`, `0x0F5F` and `0x888D`; `0x0F5C` is row 7's, the dated one. The
> count of three and the direction are unaffected, and no tool reads this line.

**2. The dated claims, which are the only ones this is about.** Row 7 carries
the only two, `0x0F58` and `0x0F5C`, and both are held to `2026-09-23-*` — six
files, four of them `ecrw.py dump` output with no column at all. Under **both**
readings both are `resolved`, and in the same file: `read_capture()` takes it
as 212 entries over 47 distinct addresses, of which `0x0F58` accounts for 4 and
`0x0F5C` for 6. That file is
`evidence/ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv`, schema
`ts,addr,old,new`. The other five files of the date carry neither literal: the
other `0700-07ff` capture, whose 22 distinct addresses sit elsewhere on the
page, and the four dumps.

**This corrects the issue's reasoning, not its conclusion.** The issue
attributes row 7's `resolved` to the union reaching all six files, `.txt`
included, and says the sibling "could not have held them". It could have: the
file that carries both is a `.csv`, and `main()` already indexes it. The
`.txt` half of the union is not what resolved them, and it contributes nothing
under either reading. The verdict is unchanged; the causal story was.

**3. Which of the issue's two claimed blockers is real.** Measured over the
**100 units** of the third column:

- `captures_in()` resolves a path in **0 of 100**. The date is the only file
  reference the column ever carries, and nothing reads it. This blocker is real
  and it is the whole one.
- `MOVEMENT` matches **49 of 100** — and of the 30 checked claims, **25 of
  30** have a unit carrying it, so **5 claims would be dropped** by that
  predicate (row 8's `0x0F5D`/`0x0F5F`, row 22's `0x0751` twice, row 25's
  `0x0751`). It is not a no-op, and it is not what made the column invisible.

> **This corrects the plan's figure, not the tool's.** The plan wrote "49 of
> 49", reading the third column as holding 49 units. It holds 100, and 49 is
> how many of them pass `MOVEMENT` — the number the plan needed was the
> denominator. The plan then concluded the predicate "is not a blocker" and
> planned no work against it. That conclusion is right — `captures_in()`
> already drops all 100 before `MOVEMENT` is consulted — but the supporting
> claim that the gate "drops nothing here" is false: it would drop 5 of the 30.

**4. What a blanket date rule in the sibling would cost.** This is the number
that decides the option. Over the corpus `check_capture_claims.py` walks
(`ROOTS`, **27,032 units** of free prose), **805 units in 104 files** carry a
bare date; **496 of those** name a date no capture carries, and the remaining
**309 units in 47 files** resolve to one. Holding each of those units' literals
to the `addr` column of its date's captures puts **124 literals MISSING
against 56 that hold**, and **17** of the misses are EC code addresses at or
above `0x8000` — above any XDATA page, and precisely what this tool's own
docstring says it has no census to filter against. Across 27,032 units, a bare
date is overwhelmingly a date of writing: the distinct dates in the corpus run
from `2018-11-01` to `2026-09-26`, and `docs/findings.md:505`'s `2021-11-27` is
not a capture at all.

> **This corrects the plan's figures.** It reported 230 units in 65 files, 92
> MISSING and **zero OK**. Measured, it is 309 units in 47 files, 124 MISSING
> and 56 OK — so the blanket rule is not quite the total wipeout the plan
> described (`0x07C4` in `ec/README.md` really is written to by a 2026-09-23
> capture, and the addr column has it), and it is still decisively out. The
> option the census picks is the same one.

**Option 1 is therefore out on the numbers**, and not narrowly: the scope it
names cannot be the whole corpus. **Option 3 is available but under-delivers**
— the narrower question is decidable today, over a committed file, with a
reader already in the tree.

## Decision: option 2, scoped to dated claims

`ec/tools/check_testdata_row_claims.py` holds a **dated** claim to the `addr`
column of the `.csv` members of the glob its date resolved to, and every other
claim keeps the textual read. The reader is `read_capture()`, **imported from
`check_capture_claims`** — the tool already imports `WATCH` from it, so the
import direction is the existing one and there is no cycle and no second
`#`-header/`change_count` parser.

The principle, which is the actual finding rather than a patch: **a claim about
a fixture is textual; a claim about a capture is columnar.** The tool's own
docstring is why this splits. Its reason for the textual read is that "a mark
label, a dump line and a change row are three ways a fixture carries an
address, and this column claims all three" — true of the mark labels rows 20,
22 and 25 claim, and of the `.txt` dump pairs rows 6 and 8 name, which have no
column. None of that holds for a real capture, where the `.csv` schema is
`ts,addr,old,new` and the column *is* the question. So the two questions are
not two weaknesses of one rule; they are two different claims, and the date in
the sentence is what tells them apart. The two flipping rows in census 1 are
the boundary of the rule and nothing else: they are `.txt`-only, so they stay
on the textual read, and the tool says so rather than resolving them by
accident.

**What this does to the run: nothing measurable.** Row 7's two are `resolved`
before and after, so the tallies stay `54 literal(s), 30 resolved, 0 missing,
24 unresolved` and `30 claim(s) checked, 15 claiming row(s)`, byte for byte.
What changes is the question being asked of them, from "does any of the date's
files carry the token anywhere" to "does a row with this in the `addr` column
exist". **The tallies being byte-identical is the check that the change moved
what it was supposed to move and nothing else**, in the same form
`testdata-row-claims-dated-capture.md` used for its five unchanged shape
counts.

**The `.txt` half of a resolved date becomes a reported fact, not a silent
drop.** A date resolving only to `.txt` files contributes no column, and that is
exactly the row-6/row-8 shape. The dated block already prints the file set —
`(6 capture(s) under evidence/ec-watch)` — and it becomes `(6 capture(s) under
evidence/ec-watch, 2 with an addr column)`. That is one clause in an existing
line, not a seventh entry in the closed shape list. The shape list stays closed
on purpose (its docstring: "a sixth shape appearing in the tree is a change to
this docstring, not an invitation to add a regex"), and a fact about a *file
set* is not a fact about a literal's spelling.

**The dated-capture-not-found shape is untouched**: an empty glob is an empty
glob.

## The silent skip (`check_capture_claims.py`)

Two changes, both about the tool reporting on itself and neither about its
scope:

1. `--verbose` gets a line for a **file** read in full that yielded no checked
   claim. On the tree as merged that is **145 of the 148 files** the tool
   walked, and the three that do yield are named in the existing
   `N claim(s) checked` lines. `ec/tools/testdata/README.md` becomes one of the
   145 **by name** instead of by absence. (This write-up is itself a file under
   `ROOTS`, so a run after this branch merges prints 146 of 149. The **claim**
   count is the one held still — 9 before and after, in the same three files —
   because that is the figure that says the surface did not move.)
2. The summary names how many files yielded no claim, on **its own line**.

**Which reading of the issue's "or" I took, and what I left out.** The issue
offers "a unit with no capture in it is worth one `--verbose` line" *or* a
count of files yielding no claim. I take the second and decline the first: the
corpus holds **27,032 units**, so a per-unit line is a ~27,000-line
`--verbose`, and the invisibility the issue names is at *file* granularity — "a
file that is read in full and yields nothing is indistinguishable, in
`--verbose` and in the summary, from a file that is not read at all". A
per-file line and a count are the bounded answer to exactly that sentence, and
they match the existing `148 files / 76217 lines / 9 capture claims checked`
line, which is already a self-report in this family. A per-unit line is left
out for this reason, not by oversight.

**One constraint the implement stage must not break:** the new count goes on
its **own line**, because
`test_check_capture_claims.py::test_committed_prose_matches_committed_captures`
parses the claim count out of the existing line by splitting on
`' lines / '`. Appending to that line breaks the case, and the shape of that
constraint is now a case of its own.

## What the refusals now hold, and how each was checked

`test_check_testdata_row_claims.py` was 42 cases and is 47;
`test_check_capture_claims.py` was 28 and is 32. Every case below is new; no
existing case was rewritten or weakened.

- `test_a_header_mention_is_not_a_row_and_the_claim_is_missing` — the case the
  issue asks for and the one that can fail: a capture naming `0x0F58` in a `#`
  header block and having no `addr` row for it is a `missing`, and the run's
  only red verdict. A `re.search` over the bytes finds the token on the first
  `#` line, so the case is sharp rather than incidentally green.
- `test_an_addr_row_resolves_even_with_the_address_also_in_the_header` — the
  other half, and what stops the case above being satisfied by a reader that
  refuses every address it finds in a comment. One header names two addresses,
  one of which has a row and one of which does not.
- `test_a_txt_only_date_reports_that_it_has_no_column_to_read` — the
  `, 0 with an addr column` clause, on a date resolving to one `.txt` dump.
- `test_the_rule_is_load_bearing_rather_than_asserted_to_be` — the refusal, in
  the suite's existing drop-it-in-turn form. Its direction is the one place
  this form differs: the other nine rules change how *many* claims are checked,
  this one changes a *verdict* while the count stays put, so the assertion is a
  flip and there is no count to compare.
- `test_the_dated_claims_resolve_in_the_addr_column` — the committed tree,
  asserted on the run as shipped rather than against a figure: each of row 7's
  two is `resolved` **and** is in the `addr` column of the date's captures, and
  fewer than all of that date's files have a column, so the run still
  exercises the `.txt` half.

**The header case was found passing for the wrong reason, and the fix is part
of the case.** The first version of `header_capture()` interpolated the address
into its `#` line as a bare integer, so the header read `# page swept at 3928`
and the textual reader found nothing either — the `missing` came from the
token being absent, not from the columnar read rejecting it. The helper now
writes `0x{a:04X}` like `a_csv()` does, and
`test_the_rule_is_load_bearing_rather_than_asserted_to_be` is what catches that
class of mistake: with the header genuinely carrying the token, the patched
reader satisfies the claim and the assertion fires.

**No floor on the committed tree, and specifically not on the dated block.**
Both the per-date breakdown and the new self-report counts are asserted as
*decompositions* — the two `--verbose` line shapes sum to the file total the
summary prints, and the summary's own count equals the number of
`no claim to check` lines — rather than as figures. A fixture, a prose file or
a dated sentence added later moves those numbers without breaking a case,
which is the same trade `docs/agent-pipeline.md` records against a floor.

## Not claimed here, and what this does not do

- **That a fixture or a capture is what its row says it is.** A `missing` is a
  disagreement between a claim and the bytes beside it, never a claim that a
  capture failed to record something.
- **Which of a date's files a sentence meant.** The union is over the date, and
  narrowing it by a word in the prose stays declined, as
  `testdata-row-claims-dated-capture.md` decided. A sentence claiming a byte of
  one capture is satisfied by that byte in any of the date's `.csv` files.
- **A second bare date in one sentence.** `DATED_CAPTURE` takes the first.
  There is no such sentence in the committed index; the limit is stated rather
  than met.
- **A blanket date rule over the whole corpus** (the issue's option 1 as
  written). Measured at 309 units in 47 files newly in scope, 124 literals
  MISSING against 56 that hold. Making it work is a separate piece of work
  needing a code-address census of the kind `check_cluster_citations.py` has
  and this tool does not. Named as the follow-up this PR opens.
- **Resolving the 496 units whose date names no capture, or the 124 that would
  go red.** Not claimed to be prose defects; census 4 says most bare dates in
  the corpus are not capture claims at all, and telling them apart is the work.
- **Repairing any fixture, row or capture.** Nothing is wrong today. The
  committed index's row 7 sentence is **not edited** — it is true, it is now
  checked more strictly than before, and editing prose to make a tool green is
  what this repository forbids.
- **Any change to `check_capture_claims.py`'s scope.** No new regex, no new
  capture source, no new predicate: the two lines added are a `--verbose` line
  and a summary count, and `main()`'s index is built exactly as before.
- **The gate wiring.** `docs/ci/agent-gates-testdata-row-claims.patch` and
  `docs/ci/agent-gates-capture-claims.patch` are **not touched** — both CLIs
  are unchanged — so both stay byte-identical and remain a human's
  `git apply`. `tools/test_agent_gates_patches.py` keeps holding them against
  `.github/scripts/agent-gates.sh`, which this branch does not edit. No gate is
  wired here and no commit runs either check in CI.
- **Live hardware, Windows, or the EC/BIOS/Windows stack.** Nothing here reads
  a register, opens a capture in any sense that touches hardware, or runs a
  capture-producing tool. No `status:` moved, so
  `ec/annotations/registers.yaml` is not touched at all.
- **Anything in another repository.** No PR or issue is opened anywhere; the
  upstream work the mission eventually means is unaffected by this change.

## A finding this PR names but does not fix

`check_capture_claims.py`'s docstring states the surface as "five
address-presence claims and two row counts" in two files; today's run reports
**9** claims across **three** files —
`docs/hardware-tests/xdata-06c2-06db-sweep.md` (2) is not mentioned. That drift
predates this issue and sits in a paragraph this change does not otherwise need
to touch, so the PR names it and leaves it for a follow-up rather than folding
a second, unrelated correction into a diff that is already touching two suites.
