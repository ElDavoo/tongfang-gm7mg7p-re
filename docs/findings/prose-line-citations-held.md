# The prose's line citations, and what now holds them (issue #801)

Issue [#801](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/801) was
opened by the follow-up pass off #791, naming six cells across three files that
had gone stale. What this branch changes is those cells, one more in a fourth
file's class that the issue did not reach, and a checker that holds the class.

**None of this is a live test, and none of it is evidence about the firmware.**
The failure is arithmetic over committed text: no EC is opened, no register is
read back, no capture is taken, and no laptop, EC or Windows machine is
involved anywhere below. `ec/decompiled/bank0/D091.c` is a file this repository
reads, and a line number into it is a statement about a decompilation, not an
observation of a byte. `XDATA_0860` stays `present-untested`, no count moved,
no `status:` moved, and no CSV or Ghidra export was regenerated.

## The eight cells, and what each one was pointing at

Every one of these is a *rank* into a file that keeps growing, and every one
rests on a claim that is still exactly right. That combination is what makes
the class worth a tool rather than four more one-line corrections: a sentence
citing the wrong row of a generated CSV produces no error, no wrong count, and
nothing for a reader to notice. The page reads as well with `:662` as with
`:817`.

| file | the cell | said | is | the claim it carries, and what the old line held |
|---|---|---|---|---|
| `ec/annotations/xdata-086x-dispatch.md` | §3's opening paragraph | `xdata-registers.csv:662` | `:817` | `refs: 17` — right, and `:662` is the `0x077E` row |
| `ec/annotations/xdata-086x-dispatch.md` | the PD-image row of §3's site table | `xdata-registers.csv:662` | `:817` | its `0x0860` row is `main-ec` — right |
| `ec/annotations/xdata-086x-dispatch.md` | §3's closing sentence | `xdata-registers.csv:662` | `:817` | the per-bucket totals — right |
| `docs/findings/reset-vector-dptr-targets.md` | the bound operand | `xdata-registers.csv:583` | `:738` | `0x0800` is a known XDATA address — right, and `:583` is the `0x06E6` row |
| `docs/findings/reset-vector-dptr-targets.md` | the same sentence | `xdata-clusters.csv:101` | `:105` | `0x0630 0x06C4 0x0800` is `main-ec-104` — right, and `:101` is `main-ec-100` |
| `docs/findings/reset-vector-dptr-targets.md` | "the skip window is exactly the cluster" | `xdata-clusters.csv:82` | `:87` | `main-ec-086` is `0x07FD 0x07FE 0x07FF` — right, and `:82` is `main-ec-081` |
| `docs/findings/reset-vector-dptr-targets.md` | the hand re-check | `xdata-clusters.csv:82` | `:87` | the same cluster, reached from the other direction |
| `ec/annotations/registers.yaml` | the `XDATA_0860` note, three cells | `:662`, `D281.c:18`/`D289.c:17`, `xdata_register_map.py:359`/`:1490-1496` | `:817`, `D281.c:19`/`D289.c:18`, `:1399`/`:3606-3619` | see "the `registers.yaml` addendum" below |

The first three are the issue's item 1, the fourth and fifth its item 3, and
the sixth and seventh are the one it did not name. The sixth is in the same
file and the same class as the issue's own item, and `grep -n 'csv:'` over
`reset-vector-dptr-targets.md` returns exactly those four cells and no other —
so fixing the two the issue named and leaving the other two would have left
that file half-corrected in a way a reader could not see. The eighth is
`registers.yaml`, discussed on its own below because its fix is not a cell
edit.

Three of the seven in the two markdown files also exist in the *content-stale*
form the issue named for `registers.yaml`: `xdata-086x-dispatch.md`'s site
table names `D281.c:19` and `D289.c:18` and the `HAND_CHECKED["0x0860"]`
comment names them too. Those two were already correct in those two files —
`#752` fixed them there and the same numbers went stale only in
`registers.yaml`'s copy of them. They are listed here because that is the
evidence for the shape of the fix below: the *content* is held in both
in-scope files, and the `registers.yaml` instance of it is held by nothing.

## The two links in the chain, and the one that was not there

The chain is decompile → CSV → prose, and it now has two links where it had
one. Neither re-derives the other's measurement, because a second copy of the
same measurement is how two copies drift.

- `check_site_census.py` (existing) reads the sweep's `access` cell out of
  `xdata-086x-dispatch-sites.csv`, the bucket out of
  `xdata-0860-census-sites.csv`, and the occurrences out of its own
  `census_occurrences()` — which borrows `load_index`, `load_symbols`,
  `occurrence_re`, `strip_comments` and `classify` from
  `xdata_register_map.py` rather than re-grepping, so the line numbers it
  checks are the reader's own. It answers *does this cited line still hold the
  occurrence the map claims*.
- `check_citation_lines.py` (new) answers *does the prose's pointer still name
  the row the map recorded*. It reads the same `xdata-0860-census-sites.csv`
  and the generated CSVs, and it never opens the decompile.

A third thing was not there and is still not: **a general prose → source-line
checker**, for `registers.yaml:3013`'s `:359` and `:1490-1496`, the `:1399`
the addendum writes, and the same `:770`/`:2250-2256` pair in
`xdata-086x-dispatch.md`'s "What the census says". That is a different tool
with its own false-positive surface, it belongs beside `citation_frames.py`,
and it is named as a follow-up rather than promised here.

## The one judgement call: what counts as superseded

Issue item 4 asked what to record if a check over a markdown table proved too
brittle. **It did not, and the decision recorded here is the one the tool
makes**, with the reasoning, because the same three files will drift again on
the next `D091.c` header rewrite and the next reader needs to know what the
check's edges are.

Two things could have been brittle and neither is. The table is located
*structurally* — the markdown table whose header carries a `C occurrence(s)`
cell, unique in that file — rather than by line number, so a rewrite that moves
the table moves the check with it, and a table whose column is renamed is
**reported as not located** rather than passing vacuously. And the comparison
is set equality over parsed `(file, line)` pairs, not substring matching, which
is no more brittle than the two prose checkers the repository already runs.
Issue item 4's fallback — take the six edits alone — was therefore not
needed, and taking it would have left the next rewrite to drift silently for
the same reason this one did.

The harder half of the decision is the supersession vocabulary, and it is the
part worth arguing. A paragraph that announces itself a correction is **skipped,
not checked**, and this is not a workaround. It is the same skip
`check_capture_claims.py` already makes for a unit asserting a capture did not
move, and `check_cluster_citations.py` for a denial: **a quoted supersession
is a denial of currency.** `docs/findings.md` §4a-4d *requires* the superseded
figure to stay visible as text beside its correction, so a checker that read
those paragraphs would be red on its own corrected tree — which is the surest
way to get a check switched off, and then nothing would be left. Two shapes,
both read off the raw lines because the marker is markup a sentence splitter
has already thrown away: any line opening with `>`, and a paragraph opening
with `CORRECTION` once `>`, `#`, `*`, `-` and whitespace are stripped. That
second shape covers the `# CORRECTION (...)` comment in
`xdata_register_map.py` and the `*** CORRECTION ...` block in `registers.yaml`
— one sentence in two languages.

The skip is never silent. The run prints how many citations it checked *and*
how many it skipped, so "checked nothing" cannot read as "found nothing" from
the exit code, and a rule that located nothing at all reports that rather than
returning clean. On this tree the run prints `26 citation(s) resolve to the row
they name, 8 skipped as superseded` — non-zero on both counts, and the skips
are named by `--verbose` with the reason for each.

**The vocabulary is not free, and this branch is where that showed.** The
correction written for `reset-vector-dptr-targets.md` was a table, in the
file's own voice, quoting the superseded figures as §4a-4d requires. Being
live prose rather than a blockquote, it was *checked* — and the checker
correctly reported its own author's wrong numbers. A second version, as a
blockquote, was skipped as intended. Neither shape is wrong on its own terms,
but only one of them means "this has been corrected" to anything reading the
file, and that is why the tool keys on shape and not on a word.

## Coverage, stated plainly

**All seven markdown cells are held, and the two content-stale values are held
twice.** Broken down by what holds what, out of the 26 citations the run
checks:

- **Rule 3 holds seven** — the three `xdata-registers.csv:662` cells and the
  `:583`, plus the one `xdata-clusters.csv:NNN` cell for `main-ec-104` and the
  two for `main-ec-086`. `ROW_SCOPE` declares `main-ec-086` and `main-ec-104`
  separately for that file, so a `:NNN` that is neither row fails and the
  report names both.
- **Rule 1 holds nine**, one per site offset in the dispatch page's table,
  including the two the census is structurally blind to.
- **Rule 2 holds ten**, the union of lines the `HAND_CHECKED["0x0860"]`
  comment names.
- The two `D281.c:19`/`D289.c:18` values are held in **both** in-scope files —
  the site table under Rule 1 and the `HAND_CHECKED` comment under Rule 2 —
  even though the `registers.yaml` instance of them is held by nothing.
- **`registers.yaml`'s three cells are held by nothing**, and saying so is the
  honest thing rather than a promise: every live sentence in that note *is* a
  `*** CORRECTION` paragraph, because §4a-4d and the 2026-09-24 block both
  require the superseded figure to stay as text. A rule that skipped
  corrections would check nothing there; a rule that did not would redden on
  the quoted predecessor. This is a property of the file's convention, not a
  gap in the checker, and it is why that file's three cells are fixed by hand.
- The eight **skipped** citations are eight cells that are wrong on purpose:
  three in the dispatch page's correction blockquotes, three in the one this
  branch added to `reset-vector-dptr-targets.md`, and two inside the two dated
  `CORRECTION` paragraphs above `HAND_CHECKED["0x0860"]`.

The remaining source-file pointers named above are held by nothing either, and
are the follow-up.

## The `registers.yaml` addendum

`registers.yaml` is the source of truth and CLAUDE.md keeps it a single file,
so the fix is in place rather than in a new one — a dated `*** ADDENDUM`
inside the existing `note:` block, quoting the superseded figures verbatim so
§4a-4d is satisfied, naming `:817`, `D281.c:19`/`D289.c:18`, `:1399` and
`:3606-3619`, and stating which of them no check holds.

The addendum also names six pointers the 2026-09-24 block quotes and this
branch does **not** correct: `:165`, `:505`, `:515-516`, `:523`, `:524-525`
and `:258-259`. They are stale for the same reason — the module has grown a
great deal since that block was written, and `ASSIGN` is now at `:359` and
`store_target()` at `:1572`, not the `:243` and `:916` the block's own
successor claims. Correcting them would mean a second correction inside a
block that is itself a quoted correction, in the one file whose convention
makes that unreadable. They are recorded as the follow-up instead. The four
an earlier draft of the addendum also listed — `:138`, `:277` and the
`:1872-1878`/`:1901-1907` pair — are not in that block at all: all four are
quoted in `xdata-086x-dispatch.md`'s own correction blockquotes, so the
dispatch page is where their record belongs. **Not one of the counts, buckets
or `status:` values in that note moved**, and the entry is still
`present-untested`.

## What this does not check

In the same register as `check_site_census.py`'s own list, and the same
caveat: every one of these is "not done by this method", never "absent".

- **`registers.yaml`, at all.** See above — its convention makes "live
  pointer" undecidable by shape, and the reasoning is the decision, not an
  excuse.
- **A pointer into a source file**, as against one into a generated CSV. The
  `:359`, `:770`, `:1399`, `:1490-1496`, `:2250-2256` family. A different tool.
- **The other `xdata-registers.csv:NNN` in the tree.** Seven files carry the
  form and `ROW_SCOPE` names the two this walks. Of the five it does not,
  `docs/findings/xdata-0860-census-sites-relined.md` holds the `:662` that is
  the *record* of what #752 found and is meant to stay wrong,
  `ec/annotations/registers.yaml` is the cell above, and the three this branch
  added — `docs/findings.md` §58, `ec/README.md` and this write-up — carry the
  form to name the cell being repointed rather than as a live pointer.
- **A citation in a file outside `ROW_SCOPE`.** Those files are not read at
  all.
- **A claim the prose makes about a direction.** `check_site_census.py`'s
  territory, and its docstring's "the prose" bullet is corrected in place to
  say which half of it is now covered and which is not.
- **Whether a cited line still holds the right code**, and the fourteen
  addresses other than `0x0860`, and the PD image.

## Where the check runs, and where it does not

It runs under `bash tools/run-tests.sh`, with no wiring: committing
`test_*.py` and adding the `tools/README.md` row is the whole of it, which is
what `test_readme_suite_table.py` is for. It is **not** run by
`.github/scripts/agent-gates.sh`, and no prepared patch was added for it.
That is a decision with a reason rather than an omission: the repository's
shape for a gate change is a prepared patch under `docs/ci/`, and a new one
would need a `gate` line at the same seven-line list's single anchor where
`agent-gates-capture-claims.patch` already inserts — two patches that each
apply alone and do not compose, which is the failure
`tools/test_agent_gates_patches.py` exists to catch. Re-merging those is
`docs/findings/prepared-gate-patches.md`'s subject, not this issue's, and
adding the file would also mean editing that suite's held `PATCHES` set. The
run is cheap (a few hundred milliseconds over five committed files) and by cost
and kind it belongs in the cheap tier, so the prepared patch is the right next
step rather than a gate line here.

## Verified on this tree

`python3 ec/tools/check_citation_lines.py` exits 0 with
`26 citation(s) resolve to the row they name, 8 skipped as superseded`.
Before the repoint, on the same tree, it reported exactly the seven stale cells
above and nothing else — the figures in this write-up's first table are what
it named, which is the check agreeing with a person who read the files.
`python3 -m unittest discover -s ec/tools -p test_check_citation_lines.py` runs
40 cases green, including the committed-tree case, and was verified to go red
on two of them when a single `:817` in the dispatch page was changed to `:818`
— a regenerated CSV inserting one row above `0x0860`, which is the event this
whole issue exists to survive.

`check_site_census.py` is unchanged, and its output is byte-identical. Its
`0x0860` line begins `0x0860: 7 site(s) agree across both methods, 2 unchecked
(other program), 17 occurrence(s) accounted for once each ...` — the tail past
the ellipsis is the per-bucket breakdown, and all of it is unchanged too. A
diff there would be a bug in this branch, since it reads two CSVs this branch
does not touch.
`xdata_register_map.py --check` still reproduces both generated CSVs from the
committed tree. `registers.yaml` parses, and `XDATA_0860` is still
`present-untested`.

## What is left, as follow-ups

1. **A prose → source-line checker**, for the `:359`/`:770`/`:1399`/`:1490-1496`/
   `:2250-2256` family. A different tool with its own false-positive surface,
   beside `citation_frames.py`.
2. **The six `xdata_register_map.py` pointers inside `registers.yaml`'s
   2026-09-24 block**, which this branch names and does not correct.
3. **A prepared gate patch** for `check_citation_lines.py`, once
   `docs/findings/prepared-gate-patches.md`'s re-merge has an anchor to
   insert at.
4. **`xdata-cluster-names-guard-off-recipe.md:220`**, which is red in
   `test_check_cluster_citations.py` and is #822's file rather than this
   issue's. It is named in `tools/README.md`'s merged-tree note and
   reproduces on `origin/main`; nothing here fixes it and nothing here
   caused it.

Submitting anything upstream is unaffected: this issue touches no driver, and
the mission's eventual `Wer-Wolf/uniwill-laptop` / `tuxedo-drivers`
contribution stays a prepared patch in this repository for a human to submit,
per issue #10.
