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

The other occurrences are **left to #685**, which owns the figure, and are
named here by path so that issue does not have to re-find them. This is not
every occurrence in the tree — every sibling `docs/findings/0751-*.md`
write-up carries a count measured on its own commit, and there are more of
those than are worth listing here — but it is every one this branch looked at
directly:

- `docs/findings/0751-grader-self-test-gate.md` — six places: the measured
  table at `:86`, the reconciliation at `:101` and `:106`, the section heading
  at `:176`, the arithmetic at `:194`, and the `ghidra tooling` transcript at
  `:216`. These are a per-commit chain, each figure correct for the commit it
  was measured on, and #735 built them that way deliberately; overwriting them
  here would destroy the chain rather than fix a number.
- `docs/findings.md:2086` — "Those 76 tests ran nowhere." This one is
  **historical**, in the past tense, describing what issue #532's write-up said
  about its own branch at the time. It is not a live count claim and is not
  wrong; the plan named it as a stale figure to correct, and it is not one.
- `docs/findings/0751-grader-unplaced-window-scope.md:271` — "Ran 94 tests
  in 0.271s", under the `At the tip, 2026-09-25:` transcript. A count measured
  at a dated tip and correct for that commit; `:199`'s "72 tests on `main` and
  74 after" in the same file is the same kind of figure.
- `docs/findings/0751-stage-mark-labels.md:246` — "goes 76 tests to 82", under
  a `## What is pinned` heading that pins the suite size as issue #472 found
  it. A per-commit pin, not a live claim.

**Not found, though the plan expected them:** the plan recorded "two tool
docstrings" carrying the figure. A search of `ec/tools/*.py` and
`windows/tools/*.py` for a claimed suite size returns none — neither
`grade_0751_isolation.py` nor `test_grade_0751_isolation.py` states a count,
and `grade_0751_isolation.py:2432` parses the count *out* of the run rather
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

> **Corrected 2026-10-02, issue #789.** Every suite this section names is green
> on this tree, so what is above reads as a record of a runner state that has
> passed rather than as a list anybody should act on. **Nothing here was fixed
> by this correction** — each suite was fixed elsewhere, and the three
> paragraphs are left standing for the `../findings.md` §4a-4d reason. Three of
> their claims do need correcting against this tree, and each is about the claim
> rather than about a replacement number:
>
> - **`tools/test_readme_suite_table.py` is not outstanding work.** The row for
>   `ec/tools/test_inc_dptr_sites.py` landed and the check is green. The reason
>   the paragraph gives for not fixing it here — that "another agent PR may be
>   open against the same file" — is recorded as the reason that stopped
>   holding rather than deleted along with the sentence.
> - **The `794` has no owner left to propagate it.** The paragraph's last
>   sentence has `tools/README.md`'s counts re-derived from that run, but
>   `tools/README.md` **carries no total at all** now: its *What it runs*
>   section says there is deliberately none, and
>   `tools/test_readme_suite_table.py` fails a spelled-out total that comes
>   back. The figure is retired here rather than re-derived into this file, and
>   `tools/README.md` is not edited.
> - **The two survivors' reasons still hold and their colour does not.** Both
>   are green, fixed elsewhere, and
>   [`runner-red-suite-set.md`](runner-red-suite-set.md)'s *The two suites named
>   above are green* records which fix moved each. The paragraph above is kept
>   because the reasoning it records is what made leaving them alone the right
>   call on the tree it was written on.
>
> The total in the first paragraph is left visible for the same reason: it was
> true of the commit it was measured on, and a fresh one would be true only
> until the next suite lands.

**Where the set is maintained, and what this tree prints.**
[`runner-red-suite-set.md`](runner-red-suite-set.md) owns the runner's failing
set; this file is deliberately a pointer to it rather than a fourth
measurement of the same thing, which is the mechanism by which the paragraphs
above went stale in the first place. The run this correction rests on, against
committed blob `74269594`:

```console
$ bash tools/run-tests.sh          # 2026-10-02
...
                                    # no suite is printed as FAILED
$ echo $?
0
$ git status --porcelain
                                    # empty: a green runner wrote nothing either
```

**The totals line is left out on purpose**, for the reason
[`runner-red-suite-set.md`](runner-red-suite-set.md)'s *What fails, and why the
corrected text carries no number* gives: a suite or test total is a property of
the merge rather than of any suite, and pasting one into a file is how the total
above came to be wrong in the first place. Whoever needs that figure runs the
runner. Whoever lands the gate wiring re-derives the failing set at that moment
**rather than trusting this list either**, which is the rule
`runner-red-suite-set.md` already carries and the reason this section is not
where the set lives.

## A fifth patch, and two more regions a re-cut cannot use

**2026-09-25, issue #798.** The set is five now, and this section exists for
the same reason the file does: a future re-cut needs to know where it may cut.
`docs/ci/agent-gates-disasm8051-self-test.patch` is the new one, and the reason
it is *not* cut where a reader would put it is the reason this file is here.

The collision table from the top of this file, updated:

| region of `agent-gates.sh` | held by |
|---|---|
| tool list `:119-124` | `agent-gates-gap-text-check.patch` hunk 1 |
| tool list `:123-128` | `agent-gates-0751-self-test.patch` hunk 1 |
| arms `:162-167` | `agent-gates-gap-text-check.patch` hunk 2 |
| arms `:189-194` | `agent-gates-0751-self-test.patch` hunk 2 |
| `check_register_counts` region, `gate` list `:271-277` | capture-claims, testdata-row-claims |

The union of the two tool-list windows is `:119-128`, and **`:129` is the only
line in the list outside every one of them** — which is why the new patch splits
`windows/tools/decompile_native.py; do` rather than inserting a line above it,
and why its `case` arm goes at the far end of the arm list after
`*xdata_register_map.py)` rather than beside `*citation_gap_scan.py)`. List
order is cosmetic (the loop is over a `for tool in` word list and nothing reads
the order), so the cost is a placement that looks wrong and a header that has
to explain it. The alternative — tidying either placement back to where a
reader expects it — breaks every-ordered-pair landing, and the failure is
silent in the way that matters: **each patch still applies cleanly alone.**

The new patch adds a third way for a patch here to be half-right without
noticing, so the suite grew a case for it. `FoldTests` covers the folded
capture-claims patch; `ArmRetentionTests` covers this one, whose two halves
(tool-list entry, `case` arm) can each be dropped by a re-cut that still
applies, still composes, and still passes `bash -n` and `shellcheck` — because
the dropped arm is precisely what keeps the tool off the `*)` default, which
passes `--work "$scratch"`. Both halves were checked against that mutation
(§"The test" above records the same discipline for the fold); the new case is
the only one of fifteen that fails.

Written-up in [`disasm8051-self-test-gate.md`](disasm8051-self-test-gate.md).

**2026-09-26, issue #811 — this patch still needs no edit, and that is a
result, not an omission.** The mode was reading a committed image and a
hard-coded table while the patch's header and its `case` arm both said it also
read the two hand transcriptions in `ec/annotations/`. `self_test()` now
re-reads them, so both sentences became true of the code without the patch
changing: its two hunks, its `@@` line counts and its `ArmRetentionTests.REQUIRED`
string (which sits *below* the comment, at the arm body) are all still correct,
and `tools/test_agent_gates_patches.py` is still green unchanged — which is
itself the evidence the patch was not disturbed. **A future re-cut should not go
looking for a correction to make here.** Read with
[`disasm8051-oracle-from-the-annotations.md`](disasm8051-oracle-from-the-annotations.md).

## A seventh patch, in the one region the table above does not use

**2026-09-27.** `docs/ci/agent-gates-findings-frozen.patch` adds
`check_findings_frozen()`, which runs `ec/tools/check_findings_frozen.py`,
`ec/tools/gen_findings_index.py --check` and
`ec/tools/check_no_append_logs.py`. It is here for the same reason the
file is: a re-cut needs to know where it may cut.

| region of `agent-gates.sh` | used by this patch |
|---|---|
| between `check_shellcheck()` and `check_doc_links()` | the function |
| inside `check_doc_links()`, before its `return` | the one call |

**Correction, same day: this table previously said the patch took `the gate
list, after gate 'doc links'` for `the one gate line`, and it takes no such
line.** That was true of an earlier cut and stopped being true when the patch
was re-cut to add **no `gate` line at all**, because four prepared patches
write into that list and the windows their hunks need overlap — so a fifth
lands in one order and not the other, and `tools/test_agent_gates_patches.py`
checks every ordered pair. The function is called from inside
`check_doc_links()` instead, and no other patch in the set has that function
in any hunk's context window, which is the claim the pair test proves rather
than this table asserting. A reader checking a re-cut against the old row would
have gone looking for a `gate` line that is not there.

Both regions are outside the table's tool list, its arms, and the
`check_register_counts` `gate` list, so this patch's hunks have no context any
existing patch writes into, and the two compose in either order —
`tools/test_agent_gates_patches.py` proves it rather than the prose here
claiming it.

**The third call was folded into this patch rather than cut as an eighth.**
`check_no_append_logs.py` is about the same thing the other two are — documents
every change has to edit — and the region it would want is this patch's
function, so a separate patch would have been two patches writing into one
function, which is the ordering problem the header above describes. Three
checks in one function is the composition the pair test already covers.

**It is cut against the current file, and the six older ones are not.** Every
patch in this set whose hunk context has since drifted out of
`.github/scripts/agent-gates.sh` fails to apply — `test_each_patch_applies_on_its_own`
is red on `origin/main` for `agent-gates-0751-self-test.patch`,
`agent-gates-disasm8051-self-test.patch` and others, and the failure message is
the instruction: *"Re-cut it against the current file; the context a hunk needs
is whatever the file has today, not whatever it had when the patch was cut."*
That is a real and separate piece of work, and it is **not** done here — three
of the six do not add a function at all but rewrite lines inside existing ones,
so a re-cut is a per-patch reading rather than a mechanical splice. Until it is
done, the gate runs two tools and the other six checkers are not in it, which
is why a PR can merge with five failing offline suites and a green cheap tier.
**2026-09-27, issue #50 — a seventh tool folds into the disasm8051 patch, and
the set is six files still.** `data_regions.py --check --self-test` wants the
cheap gate, and the collision table above is unchanged by that: the tool-list
windows are held by the gap-text and 0751 hunks, and the only line outside
every one of them is still `:129`, the `windows/tools/decompile_native.py; do`
the disasm8051 hunk splits. A new patch would have to cut that same line to be
independently applicable, which means it could not compose with the disasm8051
patch in every ordered pair — and that failure is silent in the way that
matters: **each would still apply cleanly alone.** So the second tool folds into
`docs/ci/agent-gates-disasm8051-self-test.patch` rather than shipping a seventh
file, which is what this file prescribes for exactly this collision and what
`FoldTests` already does for the capture-claims pair.

The filename is kept for the reference-count reason recorded above for
`agent-gates-capture-claims.patch`: renaming a file seventeen citations across
eleven files name — re-measured 2026-09-27 on this tree, since the 9-across-6
figure this passage and the patch header carried was already stale on
`origin/main` — would churn exactly the long shared files `CLAUDE.md` says not
to churn, to fix a name that is not load-bearing. The header now says plainly
that it carries two tools, names both, and keeps the disasm8051-only text
beneath an `Original header, for ec/tools/disasm8051.py alone:` marker so the
older reasoning is not lost.

**A fold is a new way for a patch here to be half-right, so `ArmRetentionTests`
grew to match.** Both tools' four strings are now in `REQUIRED`, and the
disasm8051 list entry is pinned in its folded ` \`-continued form because
folding moved its `; do` to the line below — a re-cut that un-folds the two
would put `; do` back where the old single string expected it. The mutation
was checked rather than assumed: dropping only `data_regions.py`'s `case` arm
from the patch still **applies, still composes, and still passes every other
case in the suite**, because the dropped arm is precisely what keeps the tool
off the `*)` default. That is the same shape the `FoldTests` case was written
for and the same reason this class exists at all.

The second tool's arm runs `--check` as well as `--self-test`, unlike the
first's, because `data_regions.py --check` is the mode that actually holds
`ec/annotations/data-regions.yaml` to the committed image — seven spans, each
re-derived for stride, entry count and first/last value — while its
`--self-test` holds the refusals. It reads two committed files: no Ghidra, no
network, no assembler, no `r2`, no capture, no EC, and nothing about it is a
behavioural claim, which is why it belongs beside `check_register_counts` in
the cheap tier rather than anywhere deeper.

**The collision table's first four rows are now jointly held by two patches
rather than one.** They are not updated in place above, because that table is
a record of what was measured on the commit that measured it and this paragraph
is the update; a reader cutting a new hunk should read both. A future re-cut
that wants a third `ec/tools/` entry in the tool list has no free line left at
all, and the honest move at that point is upstream in
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline) rather
than a seventh local patch.

**2026-09-28, issue #772 — what this suite does once a patch is landed.** A
patch that has been applied and committed has, by definition, stopped
applying, so every "must apply" case above went red on the day the first
landing landed — the state every header in `docs/ci/` tells a human to create.
Each patch is now classified into one of four states from two facts it already
had (`git apply --check`, and whether the patch's added lines are in the
committed script), and the decision is **inversion rather than retirement**:
the patch file is kept after a landing as a record of what it was, its header
is marked `# LANDED in <sha>`, and a landed patch's expectation is "must
already be there" rather than "must apply". Retirement was the alternative and
is recorded with its one real advantage — that it needs no marker — so the
choice is reversible rather than merely asserted. The classifier, the
two-step landing procedure, and the six places elsewhere in the tree that
argue from "the `gate` list is seven lines long" and will need re-deriving
on the day are in
[`landed-gate-patch-state.md`](landed-gate-patch-state.md).

## A patch in the tail of `check_ghidra_tooling()`

**2026-10-01, issue #229.** `docs/ci/agent-gates-reassembly-bound-check.patch`
wires `ec/tools/reassembly_checked_bound.py --check` into the cheap tier, and
its placement answers a question the collision table above leaves open: **is
there anywhere left in `agent-gates.sh` a prepared patch can be cut that reads
like it belongs there?**

The answer for the two obvious places is no, and now exhaustively rather than
partly. Every gap in the `for tool in` list is already another patch's context
— `0751-self-test`, `gap-text-check` and `disasm8051-self-test` between them
cover the list from its head to its foot, and `0751-writer-census` writes into
the same function just above the `for` for the same reason — and the `gate`
list is jointly held by capture-claims, pin-table-rows and testdata-row-claims
from `gate 'registers.yaml'` to `gate 'doc links'`, the three being the only
patches that add a `gate` line at all. That is also what
`check_findings_frozen` moved out of `check_doc_links()` to avoid; its own
hunks sit either side of that function rather than in the list. The
paragraph above says the honest move at that point is upstream; that was about
a *third* `ec/tools/` entry in the tool list and stands.

What is new is that the free region is not empty. `check_ghidra_tooling()`'s
tail — after the `done`, before `rm -rf "$scratch"` — is reachable by no
prepared patch's hunk, and it is inside the gate this tool belongs to anyway:
every arm of that loop is a committed-text check under `python3` with no
assembler and no Ghidra, and `reassembly_checked_bound.py --check` reads the
committed report, the committed `.asm` listings and the standard library. So
this patch is one hunk, it composes with the rest of the set in every order,
and `tools/test_agent_gates_patches.py` holds both the set and that — its
`PATCHES` list is the index of what is prepared, and `len(PATCHES)` is the
number of patches, rather than a figure typed into this prose and re-derivable
from neither.

**The other half of the placement is `--check`'s polarity, and it is the thing
to know before landing it.** It fails on what a commit can fix — a cell that
does not hold an integer, a `detail` shape it does not recognise, an anchor it
could not read — and *prints* the overclaim rather than failing on it, because
the strict form would be red on the tree it is landed onto and would stay red
until issue #157 re-reports `ec/ghidra/reassembly.csv` under the pinned nix
build. That is the §"A deviation" heading above, arriving from the other
direction: a gate that is red on the day it lands is the cheapest way to get a
gate switched off, and `ec/tools/test_reassembly_checked_bound.py` holds the
strict form red on the committed tree so `--fail-on-overclaim` is not a flag
nobody can tell works. The census it derives from is
[`reassembly-checked-counts-comparisons.md`](reassembly-checked-counts-comparisons.md).
