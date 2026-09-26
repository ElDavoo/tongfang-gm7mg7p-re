# The fixture CSVs' `evidence` column is resolved against the real tree, and eight cells that named nothing there are empty (issue #780)

The write-up for [issue
#780](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/780), which is the
fourth entry on [`testdata-index-feeds-and-call-graph.md`](testdata-index-feeds-and-call-graph.md)'s
"Left out on purpose" list. What this branch adds is **the same check, widened
once more**: `ec/tools/check_testdata_index.py` now reads the `evidence` column
of the CSVs a self-indexed directory's tables name, resolved against the
**repository root** — a third base beside `ec/tools/` for `Feeds` and the
self-indexed directory for a nested `.asm`. It found eight cells naming a path
the real tree does not have, and all eight are now empty.

**None of this is a live test, and none of it is a claim about the EC.** The
check reads two markdown files, a directory listing and two CSVs. No capture is
opened, no register is read, no machine is touched. A green run means the index
and the tree point at each other consistently — **not** that a fixture
constructs what its row says, which is the third column and what this tool
deliberately does not reach.

**Until a human lands the prepared patch, no commit runs the check.** The
cheap-tier wiring is still in `docs/ci/agent-gates-capture-claims.patch`, and
the gate line and the command in it are unchanged by this work; only the
comments at the call sites were widened to name the new kind of pointer.

## The measured state, on this tree, 2026-09-26

```
$ python3 ec/tools/check_testdata_index.py --check
13 testdata/ directories: 12 named in the index, 1 self-indexed, 0 gap(s)
27 table row(s), 34 path token(s): 34 resolved, 0 missing, 0 unresolved
27 Feeds cell(s), 29 tool pointer(s): 29 resolved, 0 missing, 0 unresolved
1 self-indexed README(s), 3 table(s), 19 row(s), 21 check(s): 21 resolved, 0 missing, 0 unresolved
2 fixture CSV(s), 0 with no `evidence` column, 10 evidence cell(s), 11 evidence path token(s): 11 resolved, 0 missing, 0 unresolved
```

Five lines where there were four, and the last one is this branch's. The
**first four are byte-identical to #746's output**, which is the point: a
direction added to a checker that perturbs the others is a direction nobody can
read the effect of. The fifth line grew a second count in the fix round, and
**what the first four carry is unchanged**; §"A CSV with no `evidence` column"
below says why the count is there. The figures, re-derived from the tool's own
output rather than copied from the issue:

| file | rows carrying an `evidence` value | path tokens (split on `;`) | absent before this |
|---|---|---|---|
| `ghidra-functions.csv` | 10 | 11 | 5 |
| `index.csv` | 8 | 8 | 3 |

**19 tokens, 8 absent, 5 distinct paths** — `bank0/0EA3.asm`, `common/0071.asm`,
`bank1/F6A0.asm`, `pd/10E0.asm`, `common/0D20.asm` — against a real tree of
**2,711** `.asm` files. This is a decidable fact about committed files, not a
scan's silence, and that is the whole of the calibration the direction claims.

**Post-fix, computed rather than estimated:** **2 CSVs, 10 cells carrying a
value, 11 tokens, 11 resolved, 0 missing, 0 unresolved**. Ten cells over eleven
tokens is the `;` split being load-bearing rather than theoretical —
`ghidra-functions.csv:2` is the one cell naming two pointers
(`ec/decompiled/bank0/0EA2.asm; ec/decompiled/bank0/0EA2.c`), and both exist.
The check is not vacuous on either side: a tally of zero would mean the rule
found nothing to read, and the suite's shared non-emptiness rule refuses that.

## The eight cells, and the decision for each

The issue says "fix **or** empty the five". This takes **empty, in all five
cases**, and the reasoning differs per case. Left out: a `synthetic` marker
column in the fixture CSVs, which the issue offers as the alternative — that is
a design call on a file `call_graph.py` reads, and an empty cell already says
what it needs to say given the fixture README's list, below.

### `ghidra-functions.csv:3` — `bank0,0EA3,mentions_absent_target`

**A digit slip, and the reason it is a finding rather than a typo fix.** The
issue frames this cell as a typo: it names `ec/decompiled/bank0/0EA3.asm` and
the real listing is `ec/decompiled/bank0/0EA2.asm`, which row 2's evidence
names correctly. That reading is half right and stops one step short. The row
is a **synthetic row** — its own comment says it exists "to pin that a comment
naming an address the listings do not carry produces no citation", and it names
`0xBEEF`, an address the fixture invents. **There is no real listing at `0x0EA3`
either**, so the cell was not nearly-right; it should never have been written.
Repointing it at `0EA2.asm` would make a `resolved` cell assert that this row's
decompilation is a *different function's* file — a false identity claim wearing
a green check. The empty cell is the honest one, and the digit slip is the
*reason* it was wrong rather than a different fix from the other four. That it
is a slip at all, and not an inherited 1978-style address, is the most
interesting fact here: the same class of wrong cell #746 caught at
`call-graph/README.md:16` (`common` for `bank0`), and the same class again a
column over.

### The other four — explicable, and now said rather than discovered

- **`common/0D20`** is already declared fixture-only at
  `ec/tools/testdata/call-graph/README.md:56-59` (before this branch) and is
  the subject of two of the fixture's own table rows.
- **`bank1/F6A0`** is declared "deliberately not one of them" at
  `call-graph/README.md:42` — the real `ec/decompiled/bank1/` holds seven
  listings of that all-`0xFF` shape and this address is *not* one of them, on
  purpose, so the assertion cannot rot into a list of seven.
- **`common/0071`** is a fixture-invented address. The neighbouring real
  `ec/decompiled/common/0070.asm` is present and `ec/decompiled/common/0071.asm`
  is not, anywhere in the tree.
- **`pd/10E0`** likewise. The real `ec/decompiled/pd/` holds 1,070 files and no
  `10E0`; the real `pd/10BC.asm` is `add_full_product_to_dptr` in
  `ec/annotations/ghidra-functions.csv`, a different function from the fixture's
  `keil_index_helper`.

All six addresses the fixture README now lists by name — `0x0D20`, `0x0D40`,
`0x0EA3`, `0x0071`, `0xF6A0`, `0x10E0` — have their `evidence` cell empty. The
sixth, `0x0D40`, never carried one; it is in the list because the row
`README.md:35` describes, and because a reader counting the emptied cells
should find the number the file explains.

## The rules, and why each reading was chosen

| source | cell shape | resolved by |
|---|---|---|
| `evidence` | `ec/decompiled/bank0/0EA2.asm` | the file exists under the **repository root** |
| `evidence` | `a.asm; b.c` | both, one per `;`-separated token |
| `evidence` | `` (empty) | **nothing** — a cell that carries no value yields no pointer |
| `evidence` | a named CSV with no `evidence` column | **`unresolved`** — one finding, counted against the CSV rather than the tokens |
| `evidence` | a token with no file extension (a URL, a range) | **`unresolved`**, note is the token |
| `evidence` | a cell naming a path the root does not hold | **`missing`** — and the run exits 1 |

**A third base, and it is the `REPO` global rather than a fresh `HERE/../..`.**
`repo_path()` reads the same global, so a run pointed at a scratch tree reports
scratch-relative paths instead of a `..` chain out of an unrelated root — which
is the trap `test_the_report_names_the_path_it_is_given` records, and which the
suite's `run_tool()` patches and restores in the same `finally` that already
restores `sys.argv`, `TESTDATA` and `INDEX`. `check()` reads the global **at
call time** rather than taking a `repo=REPO` default, as the comment on
`REPO` itself says: a default binds at def-time and silently defeats the patch.

**Which CSVs are read is structural, not an exemption list.** `nested_pointers()`
already recognises a `` `X.csv` `` part; it now records the names it recognises
into a set it appends to, and `nested_index()` reads each distinct name once.
So the next self-indexed directory carrying a CSV is covered with no edit here,
which is the same argument the self-indexed clause itself makes. Recording the
names *inside* the existing rule rather than with a second `.csv` shape test is
deliberate: a second copy is a second thing to keep in step.

**The alternative — walking every `*.csv` under `testdata/` — is left out for a
stated reason.** The twenty-odd loose fixtures at the top of the directory carry
no `evidence` column, and this tool's own calibration rule makes a column-less
CSV `unresolved`, so that reading would print about 25 `unresolved` lines on
every run for files no index promised anything about. Scoping discovery to
*named* CSVs is what makes "no `evidence` column" mean something.

**The column is read by name, not by position.** `evidence` is column 7 of 8 in
`ghidra-functions.csv` and column 10 of 12 in `index.csv`; a positional read is
right on the day it lands and wrong after the next column is added.
`test_the_column_is_read_by_name_and_not_by_position` pins it, and the mutation
run below shows what dropping the name costs.

**A `;`-separated cell is two pointers, and cells and tokens are tallied apart.**
`ghidra-functions.csv:2` names a listing and its `.c` side by side. Read whole,
the cell is one token no path rule can match and the run would be green for the
wrong reason — which is exactly the §14b defect `ParsesOnlyTheFirstColumn` is
about, one column over. Ten cells over eleven tokens is the split being visible
in the printed line.

**A finding's `where` is the fixture CSV, not the README.** Unlike a `Feeds` or
a nested finding, the disagreeing cell is in a *third* file from either index,
and reusing either of the other two paths would send a reader to a file that
does not contain the cell. `test_nothing_is_double_counted` now asserts three
distinct `where`s over the same `report()` call.

## A CSV with no `evidence` column, and what it counts against

**Correction, fix round 1 (issue #780).** The first version of this clause
recorded the column-less CSV as one more `unresolved` **token**, and the fifth
tally was derived by subtraction — `evidence_tokens - missing - unresolved`.
That is two populations being subtracted across, and a CSV with no column to
read contributes no token to subtract from: a scratch tree whose self-indexed
README named one column-less `index.csv` printed

```
1 fixture CSV(s), 0 evidence cell(s), 0 evidence path token(s): -1 resolved, 0 missing, 1 unresolved
```

0 tokens and −1 resolved, which contradicts itself in exactly the way the fifth
line exists to prevent — its own docstring gives it that purpose ("All five
tallies print whether or not they found anything, because a run that checked
nothing and a run that found nothing look the same from the exit code alone"),
and `0x0700-0x07FF` beside a negative count of resolved paths is a run that
checked nothing *and* found something. The committed tree never reached it —
both named CSVs have the column — which is the part that made it worth fixing
rather than noting: the tool's stated design is that the next self-indexed
directory is covered with no edit here, so a fixture carrying a column-less CSV
arrives at it rather than being written around it.

**The fix is that the two quantities subtract from the same population.** The
finding is now `evidence_columnless`, its own list on `Result` and `Nested` and
`Evidence`, counted against `evidence_csvs` and printed as its own number in
the fifth line. The tool's `unresolved` for this direction is now only the
token-shaped findings, so `tokens - missing - unresolved` cannot go below zero
however many CSVs have no column:

```
1 fixture CSV(s), 1 with no `evidence` column, 0 evidence cell(s), 0 evidence path token(s): 0 resolved, 0 missing, 0 unresolved
```

**The wording moved with it, and that is the same defect seen from the other
side.** The line used to read "the `evidence` column names `index.csv`, which
this tool cannot resolve to a path" — a column that is not in the file has named
nothing, and the leading clause is the part a reader skims. It now reads
``index.csv`` has no `evidence` column -- not checked, not absent.

**Both halves are pinned, and the second is the one that was missing.**
`test_a_csv_with_no_evidence_column_is_unresolved_and_not_missing` asserted the
`Result` fields and `report()`'s exit code, and never the printed line, so a
refusal whose *fields* were right and whose *printed form* was wrong went
unnoticed — the same gap §"The new cases, by rule" below is built to close. It
now runs the tool through `run_tool()` and asserts the parsed fifth line holds
`resolved == tokens - missing - unresolved`, the relation rather than today's
wording, so the case says what has to hold rather than what the string says.
Both mutations are caught: putting the finding back among the token findings
fails on the field assertion, and subtracting it from the tally as well — fields
right, line wrong — fails on the printed one.

## Calibration: what this clause does not claim

1. **`unresolved` stays the outcome for a shape this tool cannot read**, and
   the report line keeps saying *not checked, not absent*. Two shapes: a named
   CSV with no `evidence` column, and a token whose shape matches no path rule.
   The run still exits 0 in both. Reporting the first as a `missing` is how a
   checker starts inventing constraints — which is the same cost
   `testdata-index-feeds-and-call-graph.md` states for a nested CSV with no
   `addr` column.
2. **An empty value is a limit, not a verdict.** It yields no pointer at all —
   the shipped first-column behaviour that a cell with no backticked token
   yields no reference. A rule invented to read an empty value would be a parser
   guessing, and a guess here is a `missing` against the real tree. Six
   committed rows are in exactly this state and they are what keeps the rule
   honest: `test_a_row_with_no_evidence_value_yields_no_pointer` builds one and
   asserts the tally moves by zero and the report prints nothing at all.
3. **The `.c` extension is a pointer, not a decompile claim.**
   `ghidra-functions.csv:2` names `0EA2.c`; that file exists and the check says
   so and nothing more. No statement is made or implied about whether it is a
   *correct* reading of the function, and none could be read out of a green run.
4. **The whole clause is a decidable fact about committed files.** It says
   nothing about what the fixture exercises, nothing about `call_graph.py` — whose
   `--self-test` opens `index.csv` and `ghidra-functions.csv` through
   `csv.DictReader` (`ec/tools/call_graph.py:205,222`) and reads `r["addr"]`,
   `r["scope"]` and the `comment` column, and whose own `COLUMNS` (`:168`) names
   no `evidence`; the string appears in that file only in prose
   (`:13,63,96,107,285,640`) — and nothing about the EC. The self-test is
   **verified still green** with the eight cells emptied, run before and after
   the CSV edits so the comparison is a real one rather than an assumption.
5. **Existence, not identity, and the cost is worth stating.** The invariant is
   "the path the cell names is under the repository root and is on disk". A
   cell pointing at the *right* listing for the *wrong* row passes, exactly as
   a nested `X.csv` row that exists but says something else passes. That is the
   limit #746 recorded for the nested direction, inherited rather than
   reconsidered.

## What the refusals are, and how they were checked

69 cases, up from 59. The ones that matter are the **refusals themselves**,
which is the half a check that has quietly started accepting everything would
hide. The **four new rules** were each dropped in turn and the whole suite
re-run against each; **all four are caught** — and the counts below are a
property of these four mutation texts rather than of the rules they drop, for
the reason the prose beneath the table gives:

| the check refuses | caught by | the run |
|---|---|---|
| drop the `;` split (one cell, one token) | 5 cases | 69 tests, 5 failures |
| resolve against the fixture directory, not the root | 14 | 69 tests, 14 failures |
| read the column by position, not by name | 15 | 69 tests, 15 failures |
| turn `unresolved` into `missing` | 2 | 69 tests, 2 failures |

The last row is two because the rule has two `unresolved` shapes and they are
caught separately: `test_a_csv_with_no_evidence_column_is_unresolved_and_not_missing`
and `test_a_token_matching_no_path_rule_is_unresolved_and_does_not_fail`. A
mutation that only rewired the per-token one caught exactly one case, which is
what a table of counts has to be re-derived against rather than inherited.

**The new cases, by rule.** A real listing renamed is a `missing` naming the
cell, the file and the path it was read as, and it turns `report()`'s exit code
red; a row with no value yields no pointer and the report prints nothing; a CSV
with no `evidence` column is `unresolved` and the run still exits 0; the column
is read by name; a `;`-joined cell is two pointers over one cell; a path the
repository root does not hold is a `missing` even when the same relative path
*is* a file under `testdata/`; a token matching no path rule is `unresolved`; a
CSV named three times is read once; and a CSV nobody names is not read at all.

**The committed-tree cases** are what says the index and the tree currently
agree: a run reaches all five sources (13 directories / 12 named / 1
self-indexed, 27 rows / 34 first-column tokens, 27 `Feeds` cells / 29 tool
pointers, 1 nested index / 3 tables / 19 rows / 21 checks, 2 fixture CSVs /
10 evidence cells / 11 evidence tokens), every one of them non-zero, and
`rc == 0` — which is what makes the eight emptied cells load-bearing rather than
cosmetic. **The red case was run, not just asserted**: putting
`ec/decompiled/common/00EF.asm` into `index.csv`'s `common,00CF` cell gives

```
ec/tools/testdata/call-graph/index.csv: the `evidence` column names `ec/decompiled/common/00EF.asm` (read as `ec/decompiled/common/00EF.asm`), which is not on disk
1 disagreement(s) between ec/tools/testdata/README.md and the tree under it
```

and exit 1. Reverted, and the run is green again.

**The tallies are still not a floor.** `assert_the_run_reached_something` is one
root-parameterised method held to all five lines, and a scratch tree carrying
more of them than today and one carrying fewer are both green, with no integer
anywhere to edit. The three new labels are in that method rather than in a
second one, appended in the order the output prints so a refused case is refused
by the *first* thing it failed to reach. `ScratchIndex.self_indexed()` grew an
`evidence` column and a target under `self.repo` for exactly this reason: without
it the four `TheTalliesAreNotAFloor` cases stop reaching the fifth direction and
the shared helper refuses all four, which is the failure that class's own
docstring is about.

## The prepared patch

`docs/ci/agent-gates-capture-claims.patch` is regenerated. The `gate` line and
the command inside it are unchanged, and so are the **`gate` and command lines
and the old-side blob hash (`125d6478`)**, which is what governs whether the
patch still applies to the tree a human has. The new-side hash moves, because
the comments at both call sites do: the header comment and the function comment
each enumerated four directions and now enumerate five.

The two hunk headers move too, and the reason is mechanical rather than
editorial: the `check_testdata_index()` comment gained two lines, so its new-side
count is 38 rather than 36 and the second hunk's new-side start is 303 rather
than 301. Verified on this tree: `git apply --check` is clean, and
`python3 tools/test_agent_gates_patches.py` is green (it checks the set on disk
against the set the suite names both ways, each patch alone, every ordered pair,
and the whole set landing still parsing under `bash -n` and `shellcheck`).

**A note on the `index` line, because a reader will check it.** Both hashes in
it are stale against today's `main`, and were before this branch: the old-side
`125d6478` is not `main`'s `agent-gates.sh` blob, because #823 added an xdata
census arm to that file. The patch still applies, by context. The new-side hash
was computed the way the previous regeneration computed it — apply the patch to
the old-side blob the `index` line records, and hash the result — which
reproduces #746's `f7a613ea` exactly from #746's patch, so the two numbers are
comparable rather than each being a fresh convention.

## Left out on purpose

- **Landing the gate wiring.** `.github/scripts/agent-gates.sh` is copied from
  `ElDavoo/agent-pipeline` and this branch's push token has no `workflow`
  scope, so a branch editing it fails at the very end rather than at the start.
  The prepared patch is the established answer and applies unchanged if
  `.github/scripts/` ever becomes pushable. **Until then no commit runs the
  check**, and the PR says so in those words.
- **The `out_file` column.** The issue rules it out and the reason is stronger
  than "out of scope": its hit/miss profile is its own, and resolving it would
  make the run **red on the day it landed** — `ec/decompiled/common/05E8.c` and
  `.../00CF.c` exist, `.../DEAD.c` and `.../bank1/F6A0.c` do not (all four
  verified here). A check that false-positives is worse than no check, which is
  the condition #746 set on this whole direction.
- **The reverse direction for `evidence`.** A real `ec/decompiled/**` listing
  that no `evidence` cell names is still not checked — 2,711 `.asm` files, 11
  tokens. The check reads the direction the fixture points and never the one
  back; both are the "top-level files with no row" gap the shipped tool already
  declines, and this is the third instance of it.
- **The real tree's own `evidence` columns** —
  `ec/annotations/ghidra-functions.csv` and `ec/decompiled/index.csv`. Different
  owner, different rule, and a much larger tree: `pd,0x10BC`'s real value names
  three `ec/annotations/*.md` files rather than listings, so pointing this check
  at them is a piece of work in its own right. Named here so the next reader
  knows it was considered.
- **A `synthetic` marker column** in the fixture CSVs, the issue's alternative
  to emptying — a design call on a file `call_graph.py` reads, for no claim the
  empty cell does not already make.
- **`tools/README.md:644`**, which describes this suite as covering "two
  directions". It has said that since #746 and #747, both of which shipped
  without touching it. A write-up table row is a record of what its branch
  measured, which is the same reason `testdata-index-suite-count-floor.md` gives
  for leaving `testdata-index-check.md`'s counts alone. Named so the staleness
  is a decision rather than an oversight.
- **The three sibling write-ups are not edited.**
  `testdata-index-check.md`, `…-feeds-and-call-graph.md`, `…-suite-count-floor.md`
  and `…-third-column-claims.md` record what their branches measured; this file
  carries its own "Left out on purpose" and cross-references them, which is the
  convention `testdata-index-suite-count-floor.md` states about its own
  supersession.
- **Live hardware, Windows, the EC, the BIOS and the Windows vendor stack.**
  Nothing here reads a register, opens a capture or touches a machine, and no
  part of the PR may state or imply otherwise. **No live observation is needed
  to close this issue** — every artifact it checks is already committed.
- **Submitting anything upstream.** No issue or PR is opened against
  `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers` or anywhere else; that is issue
  #10's, for a human to submit by hand, and nothing in this work is an upstream
  deliverable.
