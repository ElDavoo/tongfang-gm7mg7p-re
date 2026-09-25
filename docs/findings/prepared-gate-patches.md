# The prepared gate patches: the set composes, and a test says so

**2026-09-25, issue #745.** Every `docs/ci/agent-gates-*.patch` header carries
the same instruction — `git apply docs/ci/agent-gates-<name>.patch`, "and that
is the whole change" — and `docs/agent-pipeline.md` items 4, 5, 7 and 9 repeat
it. Measured on this tree before the branch, none of it held as written. This
is what was wrong, what was decided, and what now keeps it true.

The subject is a repository invariant, not a finding about the EC. Nothing here
reads firmware, opens a capture, or reads back a register. The test reads two
committed files and a patch set; the patches edit a shell script.

## What was measured, before anything was changed

Against committed blob `125d647833ae24a705c11e8836cedb7d17558560`
(`.github/scripts/agent-gates.sh`):

| patch | `git apply --check` |
|---|---|
| `agent-gates-0751-self-test.patch` | **exit 1** — `error: patch failed: .github/scripts/agent-gates.sh:123` |
| `agent-gates-capture-claims.patch` | **exit 0** |
| `agent-gates-testdata-index.patch` | **exit 0** |

`git apply --3way --check` on the 0751 patch also exits 1, and says
`repository lacks the necessary blob to perform 3-way merge` first. Two
reasons: the repository does not carry the base blobs, **and** the 0751 patch
carries no `index` line at all (the other two do) — so there is no base blob
for it to name even where one exists.

### Two corrections to the issue's reading, both from the file

**1. The 0751 patch had *two* broken hunks, not one.** The issue says hunk 2
"still finds" `*call_graph.py)` and that "only the tool-list hunk is broken."
Re-measured here by cutting each hunk into its own patch file and checking them
separately, hunk 2 fails too:

```
$ git apply --check <hunk 1 alone>
error: patch failed: .github/scripts/agent-gates.sh:123
$ git apply --check <hunk 2 alone>
error: patch failed: .github/scripts/agent-gates.sh:187
```

Hunk 2's *leading* context does match, at `:189-191`. Its *trailing* context
does not: the `*)`, the `# build_ec_decompile.py and bios_extract.py both take
--work` comment and the `python3 "$tool" --work "$scratch" --check` line it
needs now sit at `:238-240`, with the entire `*citation_gap_scan.py)` and
`*xdata_register_map.py)` arms that item 8's landing put at `:192-237` in
between. A hunk's pre-image must be contiguous, so hunk 2 fails too. `git`
stops reporting at the first failing hunk, which is what makes it look like
hunk 1 alone is affected. The patch was therefore re-cut **whole** against the
committed blob rather than repairing hunk 1.

**2. The issue's two "done" clauses are only jointly satisfiable one way.** It
asks for "every `docs/ci/agent-gates-*.patch` passes `git apply --check`
against the committed file" *and* "the set lands in some order a reader can
follow from the headers alone." A patch regenerated against an earlier patch's
output cannot pass `--check` against the committed file — it is unapplicable by
construction. So the issue's own second option (rebase the second on the first,
record an order) cannot meet its own first clause, and this takes the first:
**fold**.

## The collision is structural, not staleness

Both patches passed `--check` alone. They failed together because both hunks in
each edit the *same contiguous region*: hunk 1 at `@@ -84,6` with
`check_python_syntax() {` as trailing context, hunk 2 at the `gate` list after
`gate 'register counts'`. Two patches that edit one region cannot both be
independently applicable — whichever lands first inserts a line between the
other's leading and trailing context. Re-anchoring does not rescue it either:
the `gate` list is seven lines long, so any two insertions into it share a
context window and collide identically. **The two `gate` lines must ship in one
patch.**

## What was decided

**`check_testdata_index()` folds into
`docs/ci/agent-gates-capture-claims.patch`, and that filename is kept.** The
patch is re-cut against `125d647` carrying both `check_capture_claims()` and
`check_testdata_index()` and both `gate` lines; its header says plainly that it
carries both and names both tools. `docs/ci/agent-gates-testdata-index.patch`
is deleted, and every reference to it is repointed, in
`docs/agent-pipeline.md` (item 9), `docs/findings.md` (§41),
`docs/findings/testdata-index-check.md` and `ec/tools/testdata/README.md`.

*Why keep the `capture-claims` name rather than invent an honest one:*
reference counts. `agent-gates-capture-claims.patch` is cited **9 times across
6 files** as the repository's canonical account of the prepared-not-landed
shape — `docs/agent-pipeline.md` (items 5, 7), `ec/README.md`,
`docs/findings/0751-grader-self-test-gate.md` (×2),
`docs/findings/testdata-index-check.md` (×2), and the headers of *both* other
patches. Renaming it churns exactly the long shared files `CLAUDE.md` says not
to churn, to fix a name that is not load-bearing. Only the four files above
needed repointing. Left out on purpose: the alternative reading (a new
`agent-gates-claims-and-testdata.patch` name) — more honest as a name, 15
reference edits across 6 files including `docs/findings.md` and `ec/README.md`,
for no gain in the file's role.

**`agent-gates-0751-self-test.patch` is re-cut whole against `125d647`**, both
hunks, and given the `index` line it was missing so a future `--3way` has a
base blob to work from. Its arm keeps its place beside `*call_graph.py)`
(`:189`); only the context is re-cut.

**`docs/ci/agent-gates-gap-text-check.patch` is new**, for
`docs/agent-pipeline.md` item 4: the `verify_gap_text.py` path in the tool list
plus the `*verify_gap_text.py)` arm that item already specified verbatim. Item
4 had carried the recipe and the justification since issue #151 with no patch
file at all, so a human landing "the prepared gate wiring" had three files, two
of which were mutually exclusive and one of which existed only as prose.

**The three surviving patches touch disjoint regions** — 0751 and gap-text the
tool list and the `case` arms, capture-claims the `check_register_counts()`
region and the `gate` list — so each applies alone and they compose in any
order. That is asserted by the test, not by this paragraph.

## A deviation: `verify_gap_text.py --check` was red, and the item-4 patch would have landed a red gate

The plan this branch was built from recorded, as verified, that the tool
"is committed and `python3 ec/tools/verify_gap_text.py --check` exists."
Existence was true; **the check did not pass**:

```
FAIL bank0|D757|D783 row_name: report says 'FUN_CODE_d757', the live
     recompute is 'state_1500_1504_1510_1514_to_0200'
```

One row, one column. A function rename landed and
`ec/ghidra/gap-text-check.csv` was not regenerated since; the 143 cross-decode
verdicts themselves all agree. This is the same shape as the `xdata_register_map`
comment already in `.github/scripts/agent-gates.sh` — a generated CSV left stale
by a rename — and that comment's own reasoning is why this mattered:

> Adding the mode to this gate before that would turn the gate red for an
> unrelated cause, which is the cheapest way to make a gate get switched off.

So preparing item 4's patch without fixing it would have prepared a trap: a
human reaching for `git apply`, as the header instructs, would have landed a red
cheap gate. The regeneration is one row of one column, is a pure function of
committed inputs, needs no assembler, and is what the tool's own `--report`
exists for:

```sh
python3 ec/tools/verify_gap_text.py --report   # writes the one row
python3 ec/tools/verify_gap_text.py --check    # then: all checks passed
```

Both are in this branch. The patch's header carries the warning, so a reader
knows why the file moved.

## The test

`tools/test_agent_gates_patches.py`, collected by `tools/run-tests.sh` via
`find` with **no gate wiring** — which is the constraint the patch route exists
to work around. It runs `git` (already required by the cheap tier's
`--verify-provenance`, which needs a full clone) and only ever writes into
`tempfile` scratch trees.

1. **The set, both directions.** The `docs/ci/agent-gates-*.patch` files on
   disk equal a list held in the test, naming which mistake when they differ —
   the `test_readme_suite_table.py` pattern, for the same reason. A patch cannot
   be added or deleted without the test noticing.
2. **Each patch alone.** `git apply --check` against the committed
   `.github/scripts/agent-gates.sh`, seeded from the working-tree file, with a
   case asserting that file is byte-identical to
   `git show HEAD:.github/scripts/agent-gates.sh` where `.git` is present
   (`skipTest` with a printed reason where it is not — visible, never a silent
   pass). Without that case a local edit under `.github/` would quietly change
   what every other case measures.
3. **Every ordered pair** applied in sequence to a scratch tree, so any
   combination lands and no order has to be recorded anywhere.
4. **The full set** applied together, and the result checked with `bash -n`
   **and** `shellcheck` — a patch that applies but yields broken shell is still
   wrong, and `git apply` will not tell you.
5. **The fold is intact**: applying the capture-claims patch alone yields both
   `check_capture_claims` and `check_testdata_index` definitions and both `gate`
   lines, so a future re-cut that drops half fails rather than passing. A
   half-folded patch applies cleanly and passes cases 1-4; this is the only
   case that notices.
6. **Each header names its own path** in a `git apply docs/ci/…` line matching
   the file it came from — the issue's literal goal is that the instruction in
   each header is true, and that is checkable.

`docs/ci/agent-gates-deep-schedule.yml` is excluded deliberately, with a
comment saying why: it is a `cp` into `.github/workflows/`, not a patch, has no
pre-image to go stale against, and is order-independent.

Each case was checked against a mutation it is supposed to catch, because a
suite that cannot fail is worth nothing: a tool inserted into the tool list
(the template re-copy shape) fails cases 2 and 3; an unlisted fourth patch fails
case 1; a header repointed at another patch fails case 6; a re-cut that drops
`check_testdata_index` fails case 5; a patch that lands an unbalanced `case`
arm fails case 4's `bash -n`.

**Honest about what this is not:** the issue notes the cheap tier cannot check
patch staleness without gate wiring. That stays true — this suite is *not* in
the cheap tier, is not per-commit coverage, and the PR body will not claim
otherwise. It is what `tools/run-tests.sh` already is: a suite that runs when
someone runs it, and now fails loudly when a prepared patch has gone stale.

## The 0751 test-count figure, and what was left to #685

The 0751 header's `76` is stale, the issue says `94`, and
`grep -c 'def test_'` on the committed suite returns **103** — three numbers,
none of them the figure to carry. So it was measured, not copied:

```
$ python3 ec/tools/grade_0751_isolation.py --self-test
test_grade_0751_isolation.py: 103 tests, passed
```

and the header and `docs/agent-pipeline.md` item 7 now say **103**, with the
timing re-derived alongside it (0.25-0.26 s end to end over five runs; the 103
tests are 0.160 s of that).

The remaining occurrences are **left to #685**, which owns the figure, and are
named here by path so that issue does not have to re-find them:

- `docs/findings/0751-grader-self-test-gate.md` — six places: the measured
  table at `:86`, the reconciliation at `:101` and `:106`, the section heading
  at `:176`, the arithmetic at `:194`, and the `ghidra tooling` transcript at
  `:216`. These are a per-commit chain, each figure correct for the commit it
  was measured on, and #735 built them that way deliberately; overwriting them
  here would destroy the chain rather than fix a number.
- `docs/findings.md:2077` — "Those 76 tests ran nowhere." This one is
  **historical**, in the past tense, describing what issue #532's write-up said
  about its own branch at the time. It is not a live count claim and is not
  wrong; the plan named it as a stale figure to correct, and it is not one.

**Not found, though the plan expected them:** the plan recorded "two tool
docstrings" carrying the figure. A search of `ec/tools/*.py` and
`windows/tools/*.py` for a claimed suite size returns none — neither
`grade_0751_isolation.py` nor `test_grade_0751_isolation.py` states a count,
and `grade_0751_isolation.py:2390` parses the count *out* of the run rather
than asserting one. Recorded here rather than left for #685 to look for.

## Left red, and why

`bash tools/run-tests.sh` on this branch: **28 suites, 794 tests, three
failing** — all three red at `HEAD` before this branch, none of them touched by
it. Each was confirmed red in a pristine detached worktree at `HEAD` rather
than assumed from the working tree.

**`ec/tools/test_check_site_census.py`** (1 failure) and
**`ec/tools/test_xdata_cluster_names.py`** (1 error) are the two the 0751
write-up already records as red, and the plan this branch was built from
leaves them alone: the census's `census_refs` still cite `bank0/D091.c` lines
the census no longer has a `0x0860` occurrence on, and the cluster-names suite
reports that the `==` guard is no longer where §6a's recipe deletes it. Neither
reads a file this branch changes. Fixing them is separate work and folding it
in here would bury it.

**`tools/test_readme_suite_table.py`** (1 failure) is the third, and it is the
only one this branch *could* have fixed. `ec/tools/test_inc_dptr_sites.py` is a
discovered suite with no row in the table. It is not fixed here: the row's
second column is a prose description of what that suite stands in for, which is
its author's to write, and another agent PR may be open against the same file.
It is a one-line documentation fix for whoever owns that suite. The counts
`tools/README.md` quotes are re-derived from this run, as that README
instructs.
