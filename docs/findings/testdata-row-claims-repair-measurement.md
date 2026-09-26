# What the two testdata checkers do over a hand-repair's pre-repair tree (issue #978)

The write-up for [issue
#978](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/978), which asked a
question the corpus had been carrying unanswered for five issues: the testdata
index has been repaired by hand twice, in #502 and #720, both times in a row's
**third column**, and every sentence that recorded the fact recorded the same
thing with it — *what those two repairs changed is in the issues, not in the
tree, and neither has been read back as a diff this tool could have been run
over*.

**The answer, measured rather than assumed: `check_testdata_row_claims.py` is
green over both pre-repair trees — 0 `missing` at row 24 for #502, and 0 at
rows 23 and 24 for #720 — and it is green because every row either repair
touched carried no address claim to be wrong about.** The repaired rows' third
columns spell **zero** backticked `0xNNNN` literals, before the repair and
after it. Both repairs rewrote prose about mark labels, `--block` counts and
which grader branch a run reaches; none of that is an address, and
`check_testdata_row_claims.py` reads addresses.

That is a **recorded blind spot with the reason it missed**, which is the
second of the two answers the issue offered. It is not "it would have caught
them", and it is not an absence of measurement either.

**Nothing here is a live test.** Both revisions are read out of this
repository's own history and the committed prose at each is read as text. No
capture is opened, no EC, no firmware image, no laptop, no Windows, and
nothing was read off a machine.

## The instrument

`ec/tools/measure_index_repair_visibility.py`, a new file. It reads a pair of
revisions, extracts each `ec/tools` into a scratch tree, and runs both
checkers in-process over the extracted one.

Three things about that are worth writing down, because the issue's own
suggested route — *"run `python3 ec/tools/check_testdata_row_claims.py
--check` against each with `check(root=...)` pointed at that tree"* — does not
work as written, and the reasons are the tool's design:

  * **Neither CLI can be pointed at a historical tree.** `main()` calls
    `check(captures=CAPTURES)` and `check(TESTDATA)` respectively, both at the
    module's own HEAD paths, and neither takes a root. The only route is the
    in-process call, which is what this tool makes.
  * **`ec/tools` is extracted whole, not `ec/tools/testdata/`.**
    `check_testdata_index.check()` sets `tools_root = os.path.dirname(root)` and
    resolves the `Feeds` column there. A bare `testdata/` extraction answers
    `feeds_missing` for every row of the table, which is 27 statements about
    how this file was written and not about either revision.
  * **The repairs are found by content, not by a list of which commits they
    were.** `repair_rows()` compares the two images' description cells through
    `check_testdata_index.table_cells(text, column=3)` — the sibling's own
    reader, never a second parser — so a third-column edit is found wherever it
    is. Naming the two revisions is the only input from outside the tree.

`git archive` piped into the standard library's streaming `tarfile`, rather
than the shell `tar` the corpus reaches for by hand
(`xdata-guard-off-key-distinctness.md`): `python3` is guaranteed by
`project-setup` and `tar` is declared nowhere.

## The measurement

Both runs, verbatim, on a full clone at `563488c4`:

```
$ python3 ec/tools/measure_index_repair_visibility.py --base 565b6f3c^ --repair 565b6f3c
pre-repair revision 565b6f3c^ -> 13a0236a62ea39aa0c3dae10639582416a83966b
post-repair revision 565b6f3c -> 565b6f3cc6b7739e0d9b4081327d2c41f05d2a7c
repair: 565b6f3cc6b7739e0d9b4081327d2c41f05d2a7c -- say in the closing summary why an unreadable mark refuses a --block run (#502)
rows whose description cell differs: 24
  row 24 -- `0751-isolation-run-unread-window/*.csv`
    backticked address literals in the description: 0 before, 0 after
    runnable at that revision: first column resolved to 3 file(s)
    pre-repair: 0 missing claim(s) in this row, of 28 checked over the whole index (0 missing tree-wide)
    post-repair: 0 missing claim(s) in this row, of 28 checked over the whole index (0 missing tree-wide)
control, pre-repair: 49 literal(s), 28 resolved, 0 missing, 21 unresolved, 21 passed over
control, check_testdata_index.py over the pre-repair tree: 0 gap(s), 0 path miss(es), 0 Feeds miss(es), 1 nested miss(es)
    not on disk at that revision: decompiled/common/0EA2.asm
control, post-repair: 49 literal(s), 28 resolved, 0 missing, 21 unresolved, 21 passed over
control, check_testdata_index.py over the post-repair tree: 0 gap(s), 0 path miss(es), 0 Feeds miss(es), 1 nested miss(es)
    not on disk at that revision: decompiled/common/0EA2.asm

$ python3 ec/tools/measure_index_repair_visibility.py --base 8f4f211f^ --repair 8f4f211f
pre-repair revision 8f4f211f^ -> 1e0bc0f2bb7625a0b6e03d77e8559161082ae8ac
post-repair revision 8f4f211f -> 8f4f211f2171e8a1ab2491eb56340f85eea4fbc9
repair: 8f4f211f2171e8a1ab2491eb56340f85eea4fbc9 -- name the no-block closing case in the two 0751 testdata entries (#720)
rows whose description cell differs: 23, 24
  row 23 -- `0751-isolation-run-unplaced-window/*.csv`
    backticked address literals in the description: 0 before, 0 after
    runnable at that revision: first column resolved to 3 file(s)
    pre-repair: 0 missing claim(s) in this row, of 30 checked over the whole index (0 missing tree-wide)
    post-repair: 0 missing claim(s) in this row, of 30 checked over the whole index (0 missing tree-wide)
  row 24 -- `0751-isolation-run-unread-window/*.csv`
    backticked address literals in the description: 0 before, 0 after
    runnable at that revision: first column resolved to 3 file(s)
    pre-repair: 0 missing claim(s) in this row, of 30 checked over the whole index (0 missing tree-wide)
    post-repair: 0 missing claim(s) in this row, of 30 checked over the whole index (0 missing tree-wide)
control, pre-repair: 53 literal(s), 30 resolved, 0 missing, 23 unresolved, 23 passed over
control, check_testdata_index.py over the pre-repair tree: 0 gap(s), 0 path miss(es), 0 Feeds miss(es), 1 nested miss(es)
    not on disk at that revision: decompiled/common/0EA2.asm
control, post-repair: 53 literal(s), 30 resolved, 0 missing, 23 unresolved, 23 passed over
control, check_testdata_index.py over the post-repair tree: 0 gap(s), 0 path miss(es), 0 Feeds miss(es), 1 nested miss(es)
    not on disk at that revision: decompiled/common/0EA2.asm
```

Both revisions are the ones the corpus already named: `565b6f3c` is the
`#498 as #502` anchor [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md)
publishes, and `docs/agent-pipeline.md` item 9 records #720's. Neither is a
merge commit — `git log --merges --oneline -- ec/tools/testdata/README.md`
returns **nothing** on this history, because the pipeline lands squashed — so
the shas came from `git log --format=%s` on the `(#502)` and `(#720)` subjects,
and the content detector then **confirmed** them independently: it found
third-column changes at exactly the rows those two subjects describe, row 24 for
#502 and rows 23 and 24 for #720, both `0751-isolation-*`.

## Why the number is zero, read rather than inferred

The three repaired rows are the only rows the number says anything about, and
their backticked tokens are the whole of the explanation. Row 24's cell, at
`565b6f3c^`, spelled three of them:

```
0751-isolation-run-unplaced-window/     a fixture path
'restored it somehow'                   a mark label
block: unplaced                         a status word the grader prints
```

`check_testdata_row_claims.py` reads a **backticked `0xNNNN`** as a claim
(`BACKTICKED` and `ADDRESS`, four hex digits and a boundary). A cell carrying
none has nothing to hold to a fixture, so it cannot go red however wrong it is
about the fixture. The same holds after each repair: #502's row gains
`` `--block 0xA0` ``, `intact` and `UNREAD_MARK_NOTE`, and #720's two rows gain
`UNPLACED_GRADED_NOTE`, `2 of the 8`, `1 of the 7` and `shown` — **0 literals
after, for all three rows.** `0xA0` is two hex digits and `ADDRESS` requires
four, so even the one token that looks like an address is not read as one.

**So the repairs were not misstatements about addresses that a checker would
have caught, and they were not omissions of an address a checker would have
wanted.** They were about what a fixture *demonstrates* — that a mark label is
unreadable, that a window belongs to no block, that a count is taken at the
print point rather than over `shown`. That is a different question from "does
this address occur in this file", and answering it is a different tool.

**The runnability flag is what makes this a measurement rather than a
non-result.** All three rows' first columns resolved to **3 files** at their
own pre-repair revisions, so none of them is the vacuous case — a row whose
fixture the repair had to add would fail every claim it has for the
uninteresting reason that the row resolves to nothing, and that is reported as
*"not runnable at that revision, because …"* and never folded into the count.
None of the three is.

## The controls, and the one number that is not zero

**`check_testdata_index.py` over the same trees is a control, not a candidate
answer.** It reads the first column, the `Feeds` column and the nested tables
and never the third, so by construction it could not have caught either repair.
Running it converts *"it would have been green through both"* from an assertion
into a measurement — and the measurement is **0 gaps, 0 path misses, 0 `Feeds`
misses and 1 nested miss, at both revisions.**

The nested miss is `call-graph/`'s own nested cell naming
`decompiled/common/0EA2.asm`, and it **is** a fact about both revisions: a stale
bank, in an index cell, naming a directory the tracked listing does not have.

```
$ git ls-tree -r --name-only 13a0236a -- ec/tools/testdata/call-graph/decompiled/ | grep 0EA2
ec/tools/testdata/call-graph/decompiled/bank0/0EA2.asm
$ git show 13a0236a:ec/tools/testdata/call-graph/README.md | grep 0EA2.asm | head -1
| `decompiled/common/0EA2.asm` | the issue's worked example: 2 `lcall`s to 0x0EE8, and a 2-byte `ajmp` to 0x5A43 |
```

The #720 pre-repair revision reads the same way, and so do both post-repair
revisions — the cell is untouched by both repairs, which is why this is the same
single miss in all four runs. **It is a decidable static fact about committed
files, not an artefact of extracting history**: the extraction supplies
`call-graph/` perfectly well, and the `common`/`bank0` disagreement is legible
in the very tree it was run over.

**It is also already found and fixed.**
[`testdata-index-feeds-and-call-graph.md`](testdata-index-feeds-and-call-graph.md)
reached this same reading from three committed artifacts and fixed it the index
way round rather than by loosening a rule — *"the fix is the index, not the
rule"* — and `1813fe98` (issue #746) repointed the cell to
`` `decompiled/bank0/0EA2.asm` ``. That is cited here as prior art rather than
re-decided. **It is unrelated to either repair**: it is why the control's one
non-zero is non-zero, and neither #502 nor #720 is in it.

`check_testdata_index.py`'s own green is therefore confirmed for everything it
reads, with that one miss stated rather than folded into a clean zero. At `HEAD`
the cell reads `decompiled/bank0/0EA2.asm` and the check is green outright —
`1 self-indexed README(s), 3 table(s), 19 row(s), 21 check(s): 21 resolved, 0
missing` — so what the four runs above measure is a residue those revisions
carried and `main` no longer has.

**The post-repair control is what makes the pre-repair number mean anything.**
A `missing` is only evidence if the same row is green *after* the repair;
without it, a red pre-repair run could be noise from a fixture that never
carried the byte. All three rows are green at their own repair revision, and the
tool exits **1** when they would not be — it has one failing check, and it is
the control, not the measurement. `verify_reassembly.py` runs its positive
control before its negative check for the same reason.

## Four limits, and the direction of the measurement

  * **Today's checker, over the old prose.** Neither checker existed at either
    revision, so there is no version of either to run. What ran is the
    committed one over a pre-repair `root`, and the **direction** is the whole
    of what the number means: a checker that is red on an old tree may be red
    for a reason the old tree's author would have called correct, and one that
    is green says only that *this rule over this text* is green. The reverse
    direction is not available and is not claimed.
  * **Only `root` moves.** The `functions`, `registers` and `captures` a run
    reads are the module-level HEAD paths of `check_testdata_row_claims.py` and
    are left there, so a pre-repair sentence's bare date resolves against
    HEAD's `evidence/ec-watch/`. The extraction puts an old `ec/tools` on disk
    only to give the `Feeds` column something to resolve against; **no file out
    of the extracted tree is ever executed or imported.**
  * **An unrunnable row is a stated limit, never a negative result** — the
    issue's own condition, and checked rather than assumed: the flag is
    reported per repaired row and none of the three tripped it.
  * **A full clone is required.** A revision that does not resolve is *"not
    measurable in this clone"*, with the command that failed, and exit 2 — never
    a count of zero. `HISTORY_REQUIREMENT` in the tool says so from what the
    workflows say today, and both `ci.yml:39` and every `agent-*.yml` stage
    check out with `fetch-depth: 0`.

**What is not claimed, beyond the above:** that the checker is right about
these rows. It is not asked. `check_testdata_row_claims.py`'s own docstring is
explicit that it does not ask whether a fixture is what its row says it is —
only whether an address a row attributes to a fixture occurs in a file that row
names. **A green run is not a claim that `0751-isolation-run-unread-window/`
carries the two block-less restores its row describes**, and nothing in this
measurement bears on that question either way.

## What the corpus changes

The disclaimer is retired **as a measured blind spot with its reason**, in
place, in the fourteen sentences across eight files that carried it — the two in
`check_testdata_row_claims.py`'s own docstring, `testdata/README.md`'s,
`check_testdata_index.py`'s, four in `docs/findings.md` (§41, §47, §76 and
§79's), one in `testdata-third-column-claims.md`, two each in
`testdata-row-claims-dated-capture.md` and `capture-filename-date-prefix.md`,
and `docs/agent-pipeline.md`'s item 10. Each keeps its claim that the repairs
were to the third column, drops the "nobody has looked", and points here. **The
handling is not uniform across the fourteen, and which is which is named rather
than left to a reader to find: four keep the old wording beside the correction** —
the `Superseded, 2026-09-26, by issue #978` blockquote in each of
`testdata-third-column-claims.md`, `testdata-row-claims-dated-capture.md` and
`capture-filename-date-prefix.md`, and §79's, which names the retired clause in
italics where it stood and says which sections it was carried forward from —
**and the other ten are replaced with a pointer to here rather than superseded
beside themselves.** The three blockquotes and §79 are the four that satisfy
`docs/findings.md` §4a-4d in its full sense; a replaced sentence satisfies the
half of it that asks the old claim not to survive unchallenged, which is why the
superseded wording is quoted in this write-up's opening paragraph rather than at
each of the ten sites — and why the three are named here by their opening words
rather than by line, on the reasoning
[`test-line-pin-census.md`](test-line-pin-census.md) measures.

**`ec/tools/testdata/README.md` is edited below its table, never in a
description cell.** Both checkers read table rows only (`table_cells`), so an
edit to the prose paragraph cannot move either tool's result — and the
replacement is kept free of backticked `0xNNNN` anyway, so it stays inert if
the paragraph is ever reflowed into the table. §4's rule — editing prose to
make a tool green is forbidden — is why the edit is a paragraph and not a cell.

**Nothing else moves.** No `status:` in `ec/annotations/registers.yaml`, no
`static_refs*` count, no fixture, no row, no capture, no `.asm`, no `.c`. No
`gh pr create` in any repository, and nothing here touches a driver.

## The test

`ec/tools/test_measure_index_repair_visibility.py`, discovered by
`tools/run-tests.sh` by `find` the moment it is committed, with no wiring.
Twenty-one cases, and what they are for is not the number — the repository's
standing rule is that an expected count turns every added fixture into a
failure — but the three ways it could be wrong quietly:

  * **the detector comparing nothing.** `repair_rows()` over images that
    differ, images that do not, a `Feeds`-only edit, a first-column edit, a
    reworded sentence that keeps every literal (the detector is about the cell,
    not the literals), and a pair whose row counts differ, which is **refused
    rather than aligned**;
  * **the shape of the committed answer, at a size where the answer is not in
    doubt.** Four cases build a scratch repository with `git init`, a commit
    whose row claims an address its fixture does not carry and a second that
    repairs it, and assert the run is **red before and green after** — the
    harness can return red, which is what makes the committed number
    falsifiable. The fifth builds the **vacuous case** (a row naming a fixture
    the pre-repair commit does not carry, added at the repair) and asserts it
    reads *unrunnable* and is counted in neither direction;
  * **a git that failed is not a tree with nothing in it.** `git_lines()`
    returns `None` with a reason for a bad revision, for a repository that is
    not there and for a `git` that is not on `PATH`, and the tool then reports
    *"not measurable in this clone"* at exit 2 rather than a count of zero.

The last class reads the two real repairs out of the committed history and
**skips** when this clone cannot resolve them, on the
`tools/test_agent_gates_patches.py` precedent and not
`test_walk_budget_census.py`'s assert-and-fail: the count is a number about
prose, and hardcoding it would fail the day a third repair is made. It asserts
the report is non-empty, that a row was found, that the checker was run and
reached something, and that the repaired rows are runnable at their own
revision — never how many.

## Left open, for the follow-up pass

  * **A checker that reads marks, not addresses.** The rows #502 and #720
    repaired are about mark labels, block membership and where a count is
    taken. Whether a fixture carries the mark its row describes is a real
    question with a different owner, and
    `test_grade_0751_isolation.py` already grades the *run* — the gap is
    between the index's prose and that grader, and this measurement does not
    close it.
  * **`verify_reassembly.py:1313-1319` still says** *"both of ci.yml's
    checkouts are default-depth"*. `ci.yml:39` is `fetch-depth: 0` now, with a
    comment saying so — which is why this write-up's fourth limit is worded
    from what the workflows say rather than carried over from that sentence. It
    is the same class of stale claim and the one a reader would copy when
    writing this tool, but correcting it belongs to its own issue.
