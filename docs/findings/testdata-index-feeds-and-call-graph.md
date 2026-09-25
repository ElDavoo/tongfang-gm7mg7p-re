# The testdata index's `Feeds` column and its self-indexed nested tables are read too (issue #746)

The write-up for [issue
#746](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/746), which is the
first two entries on [`testdata-index-check.md`](testdata-index-check.md)'s
"Left out on purpose" list. What this branch adds is **the same check, widened**:
`ec/tools/check_testdata_index.py` reads the top-level table's `Feeds` column as
tool references, and reads **every** table in a self-indexed directory's own
`README.md`. It is an extension of the existing pointer checker and not a second
one, and it found one wrong cell on the way.

**None of this is a live test, and none of it is a claim about the EC.** The
check reads two markdown files, a directory listing and two CSVs. No capture is
opened, no register is read, no machine is touched. A green run means the index
and the tree point at each other consistently — **not** that a fixture
constructs what its row says, which is the third column and what this tool
deliberately does not reach.

**Until a human lands the prepared patch, no commit runs the check.** The
cheap-tier wiring is still in `docs/ci/agent-gates-capture-claims.patch`, and
the gate line and the command in it are unchanged by this work; only the
comment at the call site was widened to name the two new kinds of pointer.

## The measured state, on this tree, 2026-09-25

```
$ python3 ec/tools/check_testdata_index.py --check
13 testdata/ directories: 12 named in the index, 1 self-indexed, 0 gap(s)
27 table row(s), 34 path token(s): 34 resolved, 0 missing, 0 unresolved
27 Feeds cell(s), 29 tool pointer(s): 29 resolved, 0 missing, 0 unresolved
1 self-indexed README(s), 3 table(s), 19 row(s), 21 check(s): 21 resolved, 0 missing, 0 unresolved
```

Four lines where there were two, and the last two are this branch's. The figures,
re-derived from the tool's own output rather than copied from the issue:

| source | cells/rows | pointers checked | resolved today |
|---|---|---|---|
| top-level first column (shipped) | 27 rows | 34 tokens | 34, 0 missing, 0 unresolved |
| top-level `Feeds` column (**new**) | 27 cells | 29 pointers, 4 distinct tools | 29, 0 missing, 0 unresolved |
| `call-graph/README.md` (**new**) | 3 tables, 8 + 7 + 4 = 19 rows | 13 `.asm` paths + 7 CSV references naming 8 addresses = **21 checks** | 21, 0 missing, 0 unresolved |

The `Feeds` breakdown, from the committed table: `../grade_0751_isolation.py` in
16 cells, `../grade_gpu_door.py` in 6, `../grade_0751_isolation.py --dump-pair`
in 3, and `../check_capture_claims.py` with `../test_check_capture_claims.py` in
2. So 29 pointers over 27 cells, in **three shapes** (plain, flag-suffixed,
`via`-paired) over four distinct tool paths. The unit the check counts is the
pointer, not the path and not the cell.

The nested breakdown: 13 `.asm` paths and 7 CSV references, of which `index.csv`
is referenced twice — once at `0xDEAD` and once naming **two** rows at
`0x1400`/`0x1410` — and `ghidra-functions.csv` five times, at `0x0EA2`, `0x0070`,
`0x029B`, `0x0D20` and `0xF6A0`. That is 8 addresses over 7 references, and 21
checks. The count is **per reference**, not per cell, which is why 19 rows give
21 checks.

### Three figures the issue gives are not this tree's

Taken from the tool's own output rather than from the issue, because a number
that is wrong in a write-up is inherited by the next reader:

- The issue says the first `call-graph` table "would read ten rows and stop". It
  has **8**. The reader defect is exactly as described — `table_cells` returned
  after the first table that ended — and only the number differs.
- The issue says "all 22 `.asm` files … are committed". **24** are. The three
  tables name **13** of them. The checker's job is that a *named* pointer
  resolves, not that every file is named: the reverse direction is out of scope
  below, and 13 is the number that matters.
- The issue says the `Feeds` column carries "three distinct tool references".
  There are **4 distinct tool paths** in **3 shapes**. The unit the check counts
  is the path, so the tally is 29 pointers over 27 cells.

## The finding: a committed index cell naming a path that is not there

`ec/tools/testdata/call-graph/README.md:16` read
`` | `decompiled/common/0EA2.asm` | … | ``. No such file exists. Three
committed artifacts say `bank0`:

- the file on disk is `decompiled/bank0/0EA2.asm`, and there is no `common` one;
- `index.csv:2` is `bank0,0EA2,delay_calls_0ee8,…,ec/decompiled/bank0/0EA2.asm,,bank0/0EA2.c`;
- `ghidra-functions.csv:2` is `bank0,0EA2,…,ec/decompiled/bank0/0EA2.asm; …`.

**The fix is the index, not the rule**: the cell now reads
`` `decompiled/bank0/0EA2.asm` ``. The two CSVs, the file on disk and the
directory layout all agree, and the `common` spelling is the slip.

Nothing read that README's tables before this, so the cell has been wrong since
it was written. The one cell was undetected for the same reason the other twelve
were correct-by-luck rather than by checking: `grep` over the tree finds
`call_graph.py`, whose `--self-test` reads `index.csv`, `ghidra-functions.csv`
and the `.asm` files and never the README (its banner at `:698` names the
directory only), and `check_testdata_index.py`, which read the README for the
directory's *existence* through the self-indexed clause and stopped.

**What this is not.** It is a decidable static fact about three committed files.
It says nothing about what the fixture exercises, nothing about `call_graph.py`,
and nothing about the EC. The suite pins the corrected cell directly
(`test_the_committed_call_graph_readme_names_a_bank0_listing`), so the fix is in
the machine-checked layer and not only in this page.

## The two rules, and why each reading was chosen

| source | cell shape | resolved by |
|---|---|---|
| `Feeds` | `` `../grade.py` `` | the path exists beside the testdata root — `ec/tools/` |
| `Feeds` | `` `../grade.py --dump-pair` `` | the token cut at its first whitespace, then the same |
| `Feeds` | `` `../a.py`, via `../b.py` `` | both backticked tokens, each as above |
| `Feeds` | `` `a.py` + `b.py` `` | both, joined by ` + ` |
| nested | `` `decompiled/common/00CF.asm` `` | the file exists **in that directory**, not in `testdata/` |
| nested | `` `index.csv` row `0xDEAD` `` | a row whose `addr` column holds that address, compared as hex |
| nested | either of the above, joined by ` + ` | both, and a token naming two rows is two checks |
| nested | anything else | **`unresolved`** — counted, printed, not a failure |

**`Feeds` resolves against the parent, and consumes the `../`.** The cell writes
its path from the *fixture's* point of view: `../grade_0751_isolation.py` names
the fixture's sibling, which is a tool, not a fixture. So the leading `../` is
consumed and the name resolved against `os.path.dirname(root)` — `ec/tools/` for
the committed tree, and the temporary root for a scratch one, which is what
keeps the rule testable without hardcoding a directory the scratch cases do not
have. This is also what keeps the two columns distinct: a `Feeds` cell naming a
*fixture* resolves against `ec/tools/` and is a `missing`, which is the case
that replaces `test_the_feeds_column_is_not_a_fixture_path` and carries that
case's reasoning forward. The old case asserted a premise this issue overturns —
that the column is not read at all — so it is replaced rather than deleted.

**The whitespace cut is the whole of the flag-suffix rule, and it is not
optional.** Three committed rows carry `--dump-pair`; without the cut, the
committed tree reports three false misses on the day this lands, which is the
issue's own condition on the whole direction: *a check that false-positives is
worse than no check*. The cut is applied to every `Feeds` token, including one
with no flag, so it is one rule rather than two. The `via` clause needs no rule
of its own because both of its halves are backticked, and reading every
backticked token reads both.

**A `+`-joined `Feeds` cell needs no rule either** — it is the read-every-token
rule the first column already has. The committed index has no such cell, so that
one is pinned by a scratch case rather than claimed to be exercised.

**One table walker, and `table_cells` on top of it.** `markdown_tables(text)`
returns every markdown table in a file as `(header cells, data rows)` pairs. A
table starts at a `|` line immediately above a separator — every cell drawn from
`{-, :}` — and ends at the first line that does not open a cell, which keeps the
prose under a table out of it. `table_cells(index, column=1)` is a thin wrapper
that takes the table whose first header cell is `File` and returns one column of
it; `column` is counted from 1, the way a reader counts, so `column=2` is
`Feeds`.

Locating a table by its **shape** rather than by a header name is what keeps the
nested rule structural instead of an exemption list — the same argument
`testdata-index-check.md` makes for the self-indexed clause, and the reason the
next self-indexed directory needs no edit here. A rule keyed on a header string
would be a list of names to fall out of date, which is what the shipped
`call-graph/` clause is explicitly not.

**Addresses are compared as integers, because one address has three spellings.**
`0x0EA2` against `0EA2`, `0xDEAD` against `DEAD`, `0x0070` against `0070` — the
`0x` prefix, the case of the digits, and the zero padding, and **all three are
live in the committed file**. A string compare reports a miss on every one of
them, and the check would be wrong on the day it landed.

## Calibration: three things this deliberately does not claim

`CLAUDE.md`'s standing rule is that a static scan finding zero references means
"not found by this method" and never "absent". Three concrete applications:

1. **`unresolved` stays the outcome for a shape this tool cannot read**, in both
   new directions, and the report line keeps saying *not checked, not absent*.
   A part of a nested cell that is neither a path nor a `X.csv` is `unresolved`;
   so is a `X.csv` with no `addr` column — "this tool cannot read that shape" is
   not "the row is absent", and reporting the first as the second is how a
   checker starts inventing constraints. The run still exits 0 in both cases.
2. **The nested CSV lookup checks existence, not identity.** A row that exists
   at the address resolves even if it says something other than the cell claims,
   because "the row the index names is in the file it names" is the invariant
   and "and it says the right thing" is a question about the fixture with a
   different owner. The honest cost is worth stating: **a typo to an address
   that happens to exist in that CSV passes.** A green run should not be read as
   more than it is.
3. **The `0EA2` claim is what it is.** A committed index cell that names a path
   the tree does not have, decided from three committed artifacts. Not a claim
   about what the fixture exercises, and nothing about the EC.

**The nested direction's own blind spot**, which is the shipped first-column
behaviour and a limit rather than a new rule: a row whose cell holds no
backticked token yields no reference at all. A rule invented here would be a
parser guessing, so the limit is stated instead.

## What the refusals are, and how they were checked

59 cases, up from 33. The ones that matter are the **refusals themselves**, which
is the half a check that has quietly started accepting everything would hide.

The **15 deliberate loosenings** — the seven `testdata-index-check.md` records
for the shipped seven, re-run because the parser was rewritten underneath them,
plus the eight this branch adds — were applied one at a time and the suite
re-run against each. **All fifteen are caught.** Counts by loosening:

| the check refuses | caught by |
|---|---|
| drop the whitespace cut (no flag strip) | 5 cases, including the committed-tree ones |
| read only the first `Feeds` token (ignores `via` and ` + `) | 4 |
| stop the nested walk at the first table | 2, one of them the 3-table shape |
| compare the CSV address as a string (no `0x`/case/padding) | 10 |
| require the `addr` column but treat its absence as `missing` | 1 |
| resolve nested paths against `testdata/` instead of the directory | 10 |
| turn `unresolved` into `missing`, `Feeds` direction | 1 |
| turn `unresolved` into `missing`, nested direction | 3 |
| drop the trailing slash (#727) | 2 |
| drop the self-indexed clause (#727) | 21 |
| turn `unresolved` into `missing`, first column (#727) | 1 |
| splice the `...` instead of globbing it (#727) | 5 |
| read one token per cell (#727) | 5 |
| restrict the directory search to the table (#727) | 8 |
| count `__pycache__` (#727) | 1 |

A rule no case catches is a rule not pinned, and this is the discipline
`testdata-index-check.md` records for the shipped seven. Three of the eight new
ones are caught by a single case each, which is the number the plan's list of
refusals implies: each shape has one case that is about it and nothing else.

**The new cases, by rule.** `Feeds`: a tool that is not there is a `missing` and
not a first-column miss; a real tool beside the fixture root resolves; the flag
suffix is cut and the cell resolves (also asserted over the committed tree,
where three rows carry it); a `via` second half that is not there is its own
finding while the first resolves; a `+`-joined cell is read as both; a token
matching no rule is `unresolved` and the run does not fail. Nested: a second and
a third table are read (the 8/7/4 shape); an `.asm` path not on disk is a miss;
a CSV reference at an address the CSV does not hold is a miss; `0x` prefix, case
and padding are not spelling; a `+`-joined cell is read as both; a part matching
neither rule is `unresolved`; a CSV with no `addr` column is `unresolved`, not
`missing`; a CSV named with no address is `unresolved`; a named CSV that is not
there is a `missing`; a self-indexed README with no table reads no rows and
fails nothing; a directory the index *merely names* is not walked, so the two
reachability clauses stay distinct; and nothing is double-counted, since a
`Feeds` finding names `testdata/README.md` and a nested one names
`testdata/call-graph/README.md`.

**The committed-tree cases** are what says the index and the tree currently
agree: a run reaches all four sources (13 directories / 12 named / 1
self-indexed, 27 rows / 34 first-column tokens, 27 `Feeds` cells / 29 tool
pointers, 1 nested index / 3 tables / 19 rows / 21 checks), every one of them
non-zero, and `rc == 0` — which is what makes the `0EA2` fix load-bearing.
Reverting that one cell turns the run red with a line naming the exact path it
is missing, verified here.

**The tallies are still not a floor.** `assert_the_run_reached_something` is one
root-parameterised method held to all four lines, and a scratch tree carrying
more of them than today and one carrying fewer are both green, with no integer
anywhere to edit. The two new tallies are in that method, not in a second one:
the four scratch trees in `TheTalliesAreNotAFloor` grew a self-indexed
directory, because a self-indexed directory with no table reaches the third
direction not at all and a run that reached nothing is what the rule is about.
An empty tree is still refused, and the refusal still names `directories` first
— the order the output prints is the order the clauses are checked in, so a
case is refused by the *first* thing it failed to reach.

## The prepared patch

`docs/ci/agent-gates-capture-claims.patch` is regenerated. The `gate` line and
the command inside it are unchanged, and so are the two hunk headers and the
**old-side** blob hash (`125d647`), which is what governs whether the patch
still applies to the tree a human has. The new-side hash moves, because the
comment at the call site does: it now names the two new kinds of pointer beside
the two old ones, and `csv` beside `glob` in what the check reads.

Verified on this tree: `git apply --check` is clean; the body applied to a
scratch copy of the repository is `shellcheck`-clean; and a full cheap-tier run
of the patched script in that copy prints

```
=== testdata index ===
13 testdata/ directories: 12 named in the index, 1 self-indexed, 0 gap(s)
27 table row(s), 34 path token(s): 34 resolved, 0 missing, 0 unresolved
27 Feeds cell(s), 29 tool pointer(s): 29 resolved, 0 missing, 0 unresolved
1 self-indexed README(s), 3 table(s), 19 row(s), 21 check(s): 21 resolved, 0 missing, 0 unresolved
testdata index: passed
```

That copy's `ghidra tooling` arm fails at `cannot resolve the base revision
'08b72e2' in this clone` — the arm documented as needing a full clone. **The
unpatched script fails identically on the same copy**, so that is the scratch
copy's missing history and not the patch; the unpatched gate on the real tree is
green.

## Left out on purpose

- **Landing the gate wiring.** `.github/scripts/agent-gates.sh` is copied from
  `ElDavoo/agent-pipeline` and this branch's push token has no `workflow`
  scope, so a branch editing it fails at the very end rather than at the start.
  The prepared patch is the established answer — four items in
  `docs/agent-pipeline.md` took it before this — and it applies unchanged if
  `.github/scripts/` ever becomes pushable. **Until then no commit runs the
  check**, and the PR says so.
- **The reverse direction for either new source.** A `.py` under `ec/tools/`
  carrying no `Feeds` row, and a committed `.asm` (24 of them, 13 named) or CSV
  row carrying no table row. Both are the "top-level files with no row" gap the
  shipped tool already declines, for the same reason, and both are stated as
  limits.
- **Program/scope identity in the CSV lookup.** Requiring the row's
  `program`/`scope` column to match something the cell does not state would be
  inventing a constraint the index does not make. The cost is stated above.
- **A row whose cell holds no backticked token.** Yields no reference, matching
  the shipped first-column behaviour. A rule invented here would be a parser
  guessing; the limit is documented instead.
- **Checking that a `Feeds` tool actually consumes the fixture it names.** That
  is what `test_grade_0751_isolation.py` and `test_grade_gpu_door.py`'s existing
  on-disk equality assertions are for. This check answers one question only:
  does the tool the index names still exist under that name.
- **`docs/agent-pipeline.md` item 9.** Still true as written; the widened scope
  lives in the tool's docstring, the suite and this file. Editing a long shared
  doc for a sentence that remains correct is the conflict risk this repository
  asks agents to avoid.
- **`tools/README.md`'s counts sentence** (#615, already out of scope for #727
  and #744) and **`ec/tools/call_graph.py`** (its self-test never read the
  README and does not start now).
- **Live hardware, Windows, the EC, the BIOS and the Windows vendor stack.**
  Nothing here reads a register, opens a capture, or touches a machine, and no
  part of the PR may state or imply otherwise. No live observation is needed to
  close this issue: every artifact it checks is already committed.
- **Submitting anything upstream.** No issue or PR is opened against
  `Wer-Wolf/uniwill-laptop` or `tuxedo-drivers`; that remains issue #10's, for a
  human to submit by hand. Nothing in this work is an upstream deliverable.
