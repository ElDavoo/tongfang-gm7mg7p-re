# `ec/tools/testdata/README.md` is now held to the tree under it (issue #727)

The write-up for [issue
#727](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/727), which is about
the index over `ec/tools/testdata/` being written by hand and nothing checking
it. What this branch adds is **a checker and a prepared patch**:
`ec/tools/check_testdata_index.py` walks the two directions an index and a tree
can disagree in, and the two lines that would put it in the cheap gate are
prepared at `docs/ci/agent-gates-capture-claims.patch` rather than landed, for
the reason that patch's own header gives. It has its own
`check_testdata_index()` there and not a patch to itself, since issue #745:
the two `gate` lines it needs were at the same anchor as
`check_capture_claims()`'s and could not both be landed.

**Until a human lands that patch, no commit runs the check.** What runs today is
`ec/tools/test_check_testdata_index.py`, which `tools/run-tests.sh` discovers by
`find` the moment its file is committed, and which holds the checker's own
refusals.

**None of this is a live test, and none of it is a claim that the fixtures are
right.** It is tooling hygiene, as the issue itself says. The check reads two
committed files and a directory listing; no capture is opened, no EC, no
firmware image, no laptop. A green run means the index and the tree point at each
other consistently — **not** that any fixture constructs what its row says it
does, which is what a reader opens the file for and what this tool deliberately
does not reach.

## The measured state, on this tree, 2026-09-25

```
$ python3 ec/tools/check_testdata_index.py --check
13 testdata/ directories: 12 named in the index, 1 self-indexed, 0 gap(s)
27 table row(s), 34 path token(s): 34 resolved, 0 missing, 0 unresolved
```

Thirteen directories: the twelve `0751-isolation-run*` sets and `call-graph/`.
Twelve are named in the index — eleven in a table row, and `0751-isolation-run/`
in prose at the bottom of the file — and the thirteenth is self-indexed. Twenty-
seven table rows, and 34 path tokens inside them, because six of the cells name
more than one fixture — five name two, `void-block-with-dumps` names three.

**What the run supports is the index's own invariant, and no more:** every path
the table's first column names is on disk, and every directory is reachable
from the index. Whether a row describes the fixture it names is the third
column, and nothing here reads it. The issue's own summary of the merged tree —
"all eleven `0751-isolation-run-*` directories are in fact indexed" — holds, and
this check is what would have said so before a person had to.

## The two directions

**Directory → index.** Every immediate subdirectory has to be reachable: the
top-level index carries its name *followed by a slash*, or the directory carries
its own `README.md`. Two details are load-bearing, and both are cases in the
suite:

- *The trailing slash.* `0751-isolation-run/` is a prefix of
  `0751-isolation-run-3blocks/`, so a bare substring test passes the former on
  the strength of the latter's row — and the former is the set §6 of the
  isolation procedure names and `test_grade_0751_isolation.py` holds equal
  against that section's file list. A check that got this wrong would pass the
  directory that equality turns on, on the strength of a row about a different
  fixture.
- *The whole file, not the table.* `0751-isolation-run/` is named in prose at the
  bottom of the index, not in a row, so a table-only scan would report a false
  gap on it. The same search also accepts a third-column cross-reference, which
  the committed index uses (`0751-isolation-run-void-block/` "below is that same
  void condition"); that is the trade the whole-file search makes, and a
  directory named in neither a cell nor a paragraph is still a gap.

**`call-graph/` is not an exemption.** The rule is structural — a directory with
its own `README.md` indexes itself — so the next self-indexed directory passes
with no edit to the tool, and there is no list of names to fall out of date. The
suite pins that with a directory named `a-directory-nobody-has-heard-of`, which
the tool has never seen, rather than by asserting that a string is absent from
the source; the committed `call-graph/` is named in the tool's docstring as the
case that motivated the clause, and in no code path.

**Index → tree.** The first column of the `File` table, every backticked token
in it, each resolved against the disk. The `Feeds` column is a tool reference
and the third is prose, so neither is read; a path in either would be a different
invariant with a different owner.

Every token in a cell is read, not one. That differs from
`tools/test_readme_suite_table.py`, whose single-token `fullmatch` is right for
its one-path-per-row table and would read six of these cells as no row at all —
the two-token ` + ` and the three-token `, ` shapes are the table's own.

| token shape | resolved by |
|---|---|
| `<dir>/<glob>` | the directory exists **and** the glob matches ≥1 entry inside it |
| `<dir>/` | the directory exists |
| a bare filename | `testdata/<filename>` exists |
| `...<suffix>` | `*<suffix>` globbed recursively under `testdata/` |
| a bare `*…` glob | the same, recursively |
| anything else | **`unresolved`** — counted, printed, not a failure |

## The `...` rule is the one the issue conditioned the whole direction on

The table writes `` `0751-isolation-example-fixed-load-0700-07ff.csv` +
`...-0400-045f.csv` ``. Splicing the first token's stem onto the second would
produce `0751-isolation-example-fixed-load-0700-07ff-0400-045f.csv`, which is
not on disk — a false gap on a row that has been true since the row was written.
The issue's condition is that "a check that false-positives on the
`...-0400-045f.csv` abbreviations is worse than none", so the abbreviation is
resolved as `*-0400-045f.csv` over the whole of `testdata/` instead. The
recursive walk is what makes that safe: the token does not say which directory
the file went in, and guessing at it is how a checker grows a false failure.

## `unresolved` is the calibration line, made mechanical

A token whose shape matches no rule is counted and printed and does not fail the
run. `CLAUDE.md`'s rule is that a static scan finding zero references means "not
found by this method" and never "absent"; a pointer-checker that reported its
own parser's blind spot as a broken index would be pushed to grow a rule for
whatever it could not read, and would end up inventing the thing it is checking.
The suite asserts the case — a `0x0700-0x07FF` in a first-column cell lands in
`unresolved`, the run still exits 0, and the report says *not checked, not
absent*.

## What the refusals are, and how they were checked

28 cases. The ones that matter are the **refusals themselves**, which is the
half a check that has quietly started accepting everything would otherwise hide:

| the check refuses | the case |
|---|---|
| a directory no index names | a scratch `testdata/` with a set and a row about something else |
| a directory indexed only by a prefix | `0751-isolation-run/` beside `0751-isolation-run-3blocks/`, the latter's row the only thing in the file |
| a bare filename that is not on disk | a row naming a fixture nobody committed |
| a `<dir>/<glob>` over a directory that is not there | the same shape, one level of `isdir` false |
| a `<dir>/<glob>` matching nothing in a directory that is | the case a "does the directory exist" reading of the shape would pass |
| an `...` abbreviation naming nothing real | the same token in a tree without the file, asserted `missing` with the pattern it was read as |

Seven deliberate loosenings of the tool were applied one at a time and the suite
was re-run against each: dropping the trailing slash, dropping the self-indexed
clause, turning `unresolved` into `missing`, splicing the `...` instead of
globbing it, reading one token per cell, restricting the directory search to the
table, and counting `__pycache__`. **All seven are caught** — the first by two
cases, the second by four, the third by two, the fourth by four, the fifth by
two, the sixth by five, the seventh by one. A suite that does not fail when the
rule it pins is removed is the same defect in the test as a check that does not
fail when the tree drifts.

## The prepared patch

This check has no patch of its own. It rides in
`docs/ci/agent-gates-capture-claims.patch`, which adds a
`check_testdata_index()` function beside `check_register_counts()` and one
`gate` line beside `register counts` alongside `check_capture_claims()`'s —
issue #745 folded the two together because they insert at the same two anchors
and so cannot both be landed, in either order. The comment at the call site
says why
it is cheap-tier (the committed tree under `ec/tools/testdata/` and the standard
library's `glob` — no firmware image, no Ghidra, no network, no assembler), what
it holds, and that it prints what it actually checked because "a run that checked
nothing and a run that found nothing look the same from the exit code alone".

Verified on this tree: `git apply --check` is clean, the body applied to a
scratch copy is `shellcheck`-clean, and a full cheap-tier run of the patched
script in a scratch copy of the repository prints

```
=== testdata index ===
13 testdata/ directories: 12 named in the index, 1 self-indexed, 0 gap(s)
testdata index: passed
```

(That copy carried no `.git`, so its `ghidra tooling` arm fails at
`verify_reassembly.py --verify-provenance` — the arm that is documented as
needing a full clone. That is the scratch copy's missing history, not the patch;
the unpatched gate on the real tree is green.)

The check itself measures **0.03 s** over three runs here, against a cheap tier
`docs/agent-pipeline.md` records at 5.9 s. That is one runner's figure and the
ratio is the point, the caveat `docs/agent-pipeline.md` item 6 records for
`call_graph.py`'s own.

## Left out on purpose

- **Landing the gate wiring.** `.github/scripts/agent-gates.sh` is copied from
  `ElDavoo/agent-pipeline` and the plan-stage push token has no `workflow`
  scope, so a branch editing it fails at the very end rather than at the start.
  The patch route is the established answer — four items in
  `docs/agent-pipeline.md` took it before this — and the patch applies unchanged
  if `.github/scripts/` ever becomes pushable.
- **`call-graph/README.md`'s own table.** A nested index of a different and
  harder shape: its rows name a `ghidra-functions.csv` row, not a path on disk.
  The check reads only the top-level table. Extending it is its own piece of
  work. **Done, in
  [`testdata-index-feeds-and-call-graph.md`](testdata-index-feeds-and-call-graph.md)
  (issue #746): every table in a self-indexed `README.md` is now walked, and a
  `.asm` path and a `X.csv` address are read in the shapes those cells use.
  Finding it turned up one cell that named a `common` listing the fixture
  carries under `bank0`.**
- **The `Feeds` column.** Tool references, not fixture paths, and a different
  invariant. **Done, in the same write-up:** the column is read as tool
  references resolved against `ec/tools/`, with the flag suffix cut and both
  halves of a `via` clause read. It is still not a fixture-path check, and
  resolving it against `testdata/` is what keeps the two columns distinct.
- **Direction 1 for top-level *files*.** The issue's first sentence is about
  directories. The twenty loose `*.csv`/`*.txt` files are covered in the other
  direction, as rows; a *new* one added beside them with no row is not caught
  until a row names it.
- **The fixtures themselves, and `test_grade_0751_isolation.py`.** None of them
  is wrong today. This issue is that nothing checked that; it is not a report
  that anything is.
- **`tools/README.md`'s counts sentence.** #615 is open on it. The table gained
  one row and the counts are untouched, and `test_readme_suite_table.py` compares
  the table's *set* and never the counts, so a stale count is not a test failure
  and not this branch's to fix.
- **Live hardware, Windows, or the EC/BIOS/Windows stack.** Nothing here reads a
  register, opens a capture, or touches a machine.
