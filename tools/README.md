# Repository tools

Two things live here: the command that runs this repository's offline
`unittest` suites, and one checker that runs beside them.

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. **There are forty-two today, 1270 tests in all** — both figures
*(The `1161` this sentence carried until #794, the `1165` it carried on #794's
own branch, the `1168` it carried at the `#962` × `#794` merge, the `1180` the
#979 branch proposed, the `1187` #780's own branch carried, the `1211` the
`#979` × `#985` merge re-derived it to, the `1221` and `1233` the two sides
of one merge each measured on their own tree, the `1243` the
`#979` × `#973` × `#780` merge re-derived it to, and the `1264` it carried on
#978's own, are all left visible per
[`../docs/findings.md`](../docs/findings.md) §4a-4d, each true of the tree it
was measured on: `1161 + 4 = 1165` and `1164 + 4 = 1168` are the four cases
`ec/tools/test_check_testdata_row_claims.py` gained, `1177 + 31 + 3 + 10 =
1221` is the `#979` × `#985` merge's arithmetic — `1177` being what `main` itself
reads at `368e9e52`, not the `1168` the sentence carried, so that step is off
`main` and not off the value above — with its four parts being #985's
thirty-one cases and its new `ec/tools/test_disasm8051_oracle.py`, #979's three
in `ec/tools/test_check_testdata_row_claims.py` and #780's ten in
`ec/tools/test_check_testdata_index.py`, and `1233 + 10 = 1243` is the
`#979` × `#973` × `#780` merge's, the ten being #780's again in the same suite
and the suite count unmoved at the `40` `main` already read — the same fact the
twenty-third note states about its own step, so **the two merges that first put
a suite on this sentence each put theirs on the side their counterpart had
none, and neither figure is derived by adding the other's**. **`1243 + 21 =
1264` is this merge's own**, the twenty-one being #978's own new
`ec/tools/test_measure_index_repair_visibility.py` and nothing else, so the test
count moved with the suite count rather than the suite count alone, and both are
a re-derivation by running the runner here rather than the addition either side
could have made: `939 + 21 = 960` is the same twenty-one under `python3 -m
unittest discover -s ec/tools`. **The suite count's step is `40` → `41`, and it
is a third single-suite step and not a fourth** — #985's
`ec/tools/test_disasm8051_oracle.py` and #973's `ec/tools/test_check_capture_names.py`
were the first two, and #780's ten above added cases to a suite it already
counted, which is why that merge's step left the `40` where it was.
**`1264 + 6 = 1270` is this branch's own**, the six being #845's new
`ec/tools/test_trace_xdata_refs.py` and nothing else, so the test count moved
with the suite count for the same reason #978's step above did, and both
figures are a re-derivation by running the runner here rather than the
addition this branch could have made: `960 + 6 = 966` is the same six under
`python3 -m unittest discover -s ec/tools`, over thirty suites rather than the
twenty-nine that `960` was measured on. **The suite count's step is `41` → `42`,
and it is a fourth single-suite step** — #985's, #973's and #978's were the
first three, and as each of those was, this one lands a suite that no write-up
cites by line, so nothing here is a pin into it and the 106 the pin census
counts is unmoved.
[`disasm8051-oracle-from-the-annotations.md`](../docs/findings/disasm8051-oracle-from-the-annotations.md)
is #985's write-up. **A merge has now added a suite where the steps before it
added none, and both sides of one did it**: `main` gained a commit after #780
forked, so thirty-eight became thirty-nine on the branch's own tree on #985's
`ec/tools/test_disasm8051_oracle.py`, and thirty-nine became forty here on
#973's `ec/tools/test_check_capture_names.py`. **"No merge added a suite" is
therefore superseded and left standing in the twenty-first note it was written
in**, true of every tree from `24460001` until `3e020cf4`, per §4a-4d. **The
`1180` is from before #982 — which implements #975 — was in the base, the
`1211` and the `1233` are re-derivations for trees #780 was not on, and the
`1187` is #780's own branch before `main` moved at all**: four figures, four
trees, none of them this one, which is why the sentence carries the arithmetic
and them side by side rather than any of them. Every figure
above is re-derived by
running the runner on the tree it is written on — see the twenty-second note
below for the `#979` × `#985` merge, the twenty-third for the `#979` × `#973`
one, the twenty-fourth for the `#929` × `#962` × `#794` × `#780` × `#985` ×
`#979` merge the branch carried, the twenty-fifth for the `#979` × `#973` ×
`#780` merge that sentence is written in, which is the first of the four that
carries a figure for a tree none of the three above measured, and the
twenty-eighth for this branch's own `#845` step.)*
are what the runner below prints, one line per suite and a total on its last
line — and each is a `unittest` suite standing in for a tool's own behaviour.
*(Corrected at the `#929` × `#942` merge, by running the runner as this sentence
asks rather than by editing it blind: #942 added
`ec/tools/test_check_pin_table_rows.py` and its 36 cases, so the **thirty-five
and 1076 this sentence carried until then are left visible here per
[`../docs/findings.md`](../docs/findings.md) §4a-4d** — they were true of every
tree up to `c68f89df`'s parent, and `c68f89df` is where the sentence first went
stale, since that commit added the suite without re-deriving this line.)*
Re-derive them by running it rather than by editing this sentence, which is
what the ninth merged-tree note below records this sentence being re-derived
by. The last re-derivation carries **two** suites rather than one — #942's
`ec/tools/test_check_pin_table_rows.py` at 36 and #777's
`tools/test_doc_patch_refs.py` at 22, on top of the eleventh note's thirty-five
and 1076 — and the **red set is unmoved** — the last line
reads `37 suite(s) run, 1134 tests; one or more FAILED` with the runner exiting
1, and the red one is still only `ec/tools/test_check_cluster_citations.py`, 48
tests, on the same `:220` of the same #822 file with the same two
`0x0464`/`0x0465` disagreements, re-checked there by running that suite alone
against a stashed clean `271389d` where it fails identically, so neither change
caused it nor fixes it.

*(And the re-derivation the paragraph above records is one suite short of the
tree this file sits in, and so is the branch's correction above it. **Neither
branch saw the other's suite**, and the two re-derivations landed in the same
window: the eleventh note's thirty-five and 1076 became **thirty-six and 1112**
for #929's #942 (`ec/tools/test_check_pin_table_rows.py`, 36 cases) and
**thirty-seven and 1134** for `main`'s #942 plus #777
(`tools/test_doc_patch_refs.py`, 22 cases), and the third suite in the window —
#941's `ec/tools/test_check_pin_table_by_cited_file.py` — is in neither
arithmetic. `main`'s own §65 note is where the same omission shows as a figure:
it reads *"11 of the **37** indexed `test_*.py`"* where the merged tree indexes
**38**. **The sentence above is re-derived by running the runner on the merged
tree rather than by adding the two figures up**, which is what this file's own
rule four paragraphs up asks for, and all three superseded values stay written
here per [`../docs/findings.md`](../docs/findings.md) §4a-4d. **"The last
re-derivation carries two suites" in the paragraph above is superseded with them
— it carries three — and "the red one is still only
`ec/tools/test_check_cluster_citations.py`" is confirmed rather than corrected:
the merged run reads `38 suite(s) run, 1161 tests; one or more FAILED` with that
one suite red, after this merge was briefly red on three others and repaired
them. The eighteenth note below carries the arithmetic.)*
None of the thirty was red on the 2026-09-25
run recorded at `64dbde19`; two were,
and stay named here as history rather than as state, because a reader who
took them as current would go looking for a red runner that is gone:
`ec/tools/test_check_site_census.py` and `ec/tools/test_xdata_cluster_names.py`,
both because their subject was stale. A third was red until #751 landed the row
for `ec/tools/test_inc_dptr_sites.py`, and this tree holds that row and the one
for `ec/tools/test_disasm8051.py` that #688 added:
`tools/test_readme_suite_table.py` is this table's own check, and a missing row
is the one step a runner that finds suites by `find` cannot do for itself — a
table missing either of those two rows would fail it. The totals above count
tests *run*, failing suites included, which is what the runner counts — and
*run* is not *collected*: a class whose `setUpClass` raises contributes none of
its own cases, and the error is not itself counted as one, so the same
`ec/tools/test_xdata_cluster_names.py` ran 21 of its 28 while it was red in
`TheGuardOffRegeneration` and runs 28 now, where an ordinary failing case runs
and is counted like any other. The total moves with *how* a suite was red and
not only with whether it was, so a suite going green does not add a knowable
number of cases to the figure.

The totals are not a pass and never were: what says whether a tree is green is
the runner's last line and its exit status, not a number kept in a file. On
2026-09-25 at `64dbde19` that last line read `All 30 suite(s) passed, 882
tests` and the runner exited 0.
*(Merged-tree note, 2026-09-25: `2ed6f030` (#822) added
`docs/findings/xdata-cluster-names-guard-off-recipe.md`, and on that tree one
suite is red — `ec/tools/test_check_cluster_citations.py`, whose
committed-prose case rejects `:220` of that new file, where one fenced block
prints a guard-off regeneration beside the committed census and so names
clusters from two rankings at once, and its `joined ['0x0464', '0x0465']` line
cites two bytes the committed census puts in `main-ec-145`, which is not one of
the eleven ids the block names. On `2ed6f030` the counts were still thirty
suites and 882 tests and the last line read `30 suite(s) run, 882 tests; one or
more FAILED` with the runner exiting 1. It is #822's file rather than this
file's and it reproduces on a clean checkout of `origin/main`, so it is named
here rather than fixed here: the `64dbde19` sentence above is still
true of `64dbde19`, and this is the paragraph that stops it reading as true of
the tree it is now sitting in.)*
*(Second merged-tree note, 2026-09-25, issue #846 at `964279dc`: on **that**
tree the counts were re-derived from a `bash tools/run-tests.sh` as thirty-one
suites and 934 tests, the new one being `ec/tools/test_walk_budget_census.py`
at 52. The last line read `31 suite(s) run, 934 tests; one or more FAILED` with
the runner exiting 1, and **the same suite was the red one**:
`ec/tools/test_check_cluster_citations.py`, on the same `:220` of the same
#822 file. It is red on a clean `origin/main` too, checked by stashing that
work and running the suite alone, so nothing there caused it and nothing there
fixes it. The `64dbde19` sentence is left reading as the record of that commit
rather than rewritten with figures from a different one.)*
*(Third merged-tree note, 2026-09-25, #846 and #801 together: the counts were
re-derived from a `bash tools/run-tests.sh` on **that** tree — **thirty-two
suites and 974 tests**, which is 882 plus the two suites each side added:
`ec/tools/test_walk_budget_census.py` at 52 and
`ec/tools/test_check_citation_lines.py` at 40. The last line read `32 suite(s)
run, 974 tests; one or more FAILED` with the runner exiting 1, and **the red one
was still `ec/tools/test_check_cluster_citations.py` and still the same `:220`
of the same #822 file** — confirmed again there by running that suite alone
against a worktree of clean `origin/main`, where it fails identically, so
neither side of that merge caused it and neither fixes it. Both of the new
suites were green, and a third note is here for the reason the second one was:
the reason a suite goes red while the merge is adding green ones is the kind of
thing a totals paragraph is for. On #801's side it was that branch's own first
draft of its correction block in
`docs/findings/reset-vector-dptr-targets.md`, which tripped that suite a second
way by naming one address and four cluster ids in a single `>`-quoted paragraph
— `check_cluster_citations.py` splits prose into sentences but a blockquote's
`>` markers sit between the terminator and the next word, so a quoted paragraph
arrives as one unit. The draft was rewritten rather than the suite loosened.)*
*(Fourth merged-tree note, 2026-09-25, issue #849 landing beside #846: the
figures were re-derived from a `bash tools/run-tests.sh` on **that** tree —
thirty-two suites and 978 tests. One change moved them, and only one: #849 adds
`ec/tools/test_check_doc_figure_pins.py` at 44 cases to the thirty-one suites
and 934 tests the second note measured, which already counted #846's
`ec/tools/test_walk_budget_census.py` at 52, so 934 + 44 = 978. The second
note's thirty-one and 934 are #846's tree, left reading as the record of that
commit the same way the `64dbde19` sentence is. The last line on that tree read
`32 suite(s) run, 978 tests; one or more FAILED` with the runner exiting 1, and
it was still **the same red suite**,
`ec/tools/test_check_cluster_citations.py`, on the same `:220` of the same #822
file — re-checked there on a clean `origin/main` worktree, where it fails
identically, so neither issue caused it and neither fixes it.)*
*(Fifth merged-tree note, 2026-09-25, issue #849 landing beside #801 rather than
beside #846 alone: the counts above are this merged tree's, re-derived from a
`bash tools/run-tests.sh` on it — **thirty-three suites and 1018 tests**. Both
merges are in that arithmetic, because the fourth note's tree carried #846 and
#849 and this one carries #846, #801 and #849: 978 + 40 = 1018, with #801's
`ec/tools/test_check_citation_lines.py` at 40 the one addition. The last line
reads `33 suite(s) run, 1018 tests; one or more FAILED` with the runner exiting
1, and the red one is still `ec/tools/test_check_cluster_citations.py` on the
same `:220` of the same #822 file — checked again here by running that suite
alone in a worktree of clean `origin/main`, where it fails with the same two
`0x0464`/`0x0465` cluster disagreements, so neither issue caused it and neither
fixes it. Both of the newly merged suites are green:
`test_check_citation_lines.py` at 40 and `test_check_doc_figure_pins.py` at
44.)*
*(Sixth merged-tree note, 2026-09-25, issue #851 landing beside #801 and #849:
the counts above are this merged tree's, re-derived from a `bash
tools/run-tests.sh` on it — **thirty-four suites and 1033 tests**, which is the
fifth note's 1018 plus #851's one new suite,
`ec/tools/test_xdata_carry_notice.py` at 15. The last line reads `34 suite(s)
run, 1033 tests; one or more FAILED` with the runner exiting 1, and the red one
is **still only** `ec/tools/test_check_cluster_citations.py` on the same `:220`
of the same #822 file — confirmed once more here by running that suite alone in
a worktree of clean `origin/main`, where it fails with the same two
`0x0464`/`0x0465` disagreements, so #851 neither caused it nor fixes it. The new
suite is green at 15.)*

*(A seventh thing this merge moved, recorded here because it is the kind that
survives a totals note: #851 added 80 lines to `ec/tools/xdata_register_map.py`
above every `check()` past `:2970`, and #849 had added 19 above the same
`check()`s from the other side, so **every `file:line` either issue cited into
that file was stale the moment the two landed together**. Both sides' citations
were re-measured against the merged file and repointed — #849's `:3260-3277` →
`:3339-3356` and five more in `doc-figure-pin-audit.md` and the checklist's §2b,
#851's `:4587-4592` → `:4606-4611` and a dozen more across six pages — and
`ec/tools/test_check_doc_figure_pins.py`'s two line pins with them, since a
suite that pins a line is the same defect a page that pins one is. That suite was
red for the duration and is green again; it is named here rather than left as a
detail of the diff because "the merge only renumbered some prose" is the reading
this file exists to make impossible.)*

*(Seventh merged-tree note, 2026-09-26, issue #852 landing beside #801, #849 and
#851: the counts above are this merged tree's, re-derived from a `bash
tools/run-tests.sh` on it — **thirty-four suites and 1033 tests**, which are the
sixth note's figures **unchanged**, because #852 adds no `test_*.py` and so no
row to the table below. The last line reads `34 suite(s) run, 1033 tests; one or
more FAILED` with the runner exiting 1, and the red one is **still only**
`ec/tools/test_check_cluster_citations.py`, 48 tests, on the same `:220` of the
same #822 file with the same two `0x0464`/`0x0465` disagreements — so #852
neither caused it nor fixes it. The paragraph above is #851's "seventh thing",
not a note: it is the seventh *item of this kind* rather than the seventh
merged-tree note, and the two are numbered from different things on purpose.)*

*(An eighth thing this merge moved, of the kind the paragraph above names.
#852's only edit to a code file is four lines added to
`ec/tools/test_xdata_cluster_names.py`'s `TheGuardOffRegeneration` docstring, at
`:291`, so **every `file:line` the tree cites into that file past `:291` was
stale the moment it landed** — and #851 (`a02de81b`) had already put nine lines
into `xdata-census-rederivation-checklist.md` above the guess its own new
write-up cites at `:184-187`. Every citation the two moves actually displaced
was re-measured against the merged files and repointed, both sides' and the new
write-up's: `test_xdata_cluster_names.py:303` → `:307` in four places,
`:387` → `:392` in the checklist and twice inside #852's own
`xdata_moved_ranks.py`, `:576` → `:581` and `:588-594` → `:592-598` in
`xdata-names-file-census-anchor.md`, and
`xdata-moved-ranks-fall.md`'s `:184-187` → `:193-196`. Two citations into the
same files were **already stale before either merge** — the `:355-370` in
`xdata-4-4-identity-rederivation.md` and the `:406-407` in
`xdata-census-self-test-gate.md` — and those are recorded in the first file's
"Deliberately not fixed" list rather than repointed, because deciding what a
drifted pin was meant to name is a next pass's call and not a merge's. What is
*not* held by any of this: nothing checks a citation into a test file, which is
why the two pre-existing ones are still wrong — and since #887 this paragraph is
no longer the only thing saying so:
[`docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
censuses the whole class and still checks none of it, because six of the seven
places that cite a stale pin on purpose do so in unmarked prose. *(Left as
written per §4a-4d: that census is of a tree, and on the tree this file now
sits in it reads **eight of the ten**, for the reason the ninth note below
gives.)*)*

*(A ninth thing this merge moved, and the largest displacement so far. #713
(`4151cb1c`) added the twelve per-program count columns to
`ec/annotations/xdata-registers.csv` and, with them, ~400 lines to
`ec/tools/xdata_register_map.py` — its pin block in the `ORACLE`/`OWNERSHIP`
region *and* four new `--self-test` assertions below every existing one — so
**every `file:line` #849 and #850 cited into that file was stale again**, and
this time the `ORACLE`/`OWNERSHIP` definition lines moved too, which the seventh
note above said they would not: `:649`/`:654`/`:655`/`:1264`/`:1292` →
`:738`/`:743`/`:744`/`:1414`/`:1442`, `:1212`/`:1228` → `:1362`/`:1378`,
`:3037`/`:3073`/`:3087` → `:3253`/`:3289`/`:3304`, `:3339-3356` → `:3555-3572`,
`:3485-3490` → `:3864-3869`, `:3927-3929` → `:4306-4308`, `:3936-3940` →
`:4315-4319`, `:3968-3975` → `:4347-4354`. Every one of those citations —
#849's, #850's and #850's new write-up's — was re-measured against the merged
file and repointed, in `doc-figure-pin-audit.md`, the checklist's §2b, the
§2a/§2b discussion, `xdata-6a-direction-rows-pinned.md`, `xdata-census-self-test-gate.md`
and `findings.md` §66. **The `check_doc_figure_pins.py` transcript at the top of
`doc-figure-pin-audit.md` was re-run rather than shifted**, and the two spans
`ec/tools/test_check_doc_figure_pins.py` pins were re-measured by #713 itself,
through two successive corrections (`:3339-3356` → `:3554-3571` → `:3555-3572`,
and `:3936-3940` → `:4360-4366`) — which is the same defect a page that pins a
line has, caught by the suite that exists to catch it. The **verdicts** are
unchanged: the run still reads `18 figure(s), 18 measured held, 0 measured
unheld`, and the only denominator that moved is `searched 9 module-level
constant(s)` → `10`, since #713's own `ORACLE` keys are what the tool now finds.
What none of this is: a fix for the pins this file already records as stale
before any of these merges — `:463` in `xdata-census-totals.md` and the `md5sum`
in `xdata-export-ownership-page-census.md`, both named in `findings.md` §64 and
both left where they are, for the reason the eighth note gives.)*

*(Eighth merged-tree note, 2026-09-25, issue #850 landing beside #801, #849 and
#851. **The counts below are that tree's, not this one's** — #887 has landed
since, and the ninth note gives this tree's. On that tree they are
**thirty-four suites and 1035 tests**, which is the
seventh note's 1033 plus #850's two cases. #850 adds no suite: it adds
`TheExportOwnershipClusters`'s two cases to `ec/tools/test_xdata_cluster_names.py`,
so **the suite count of thirty-four was unchanged**, which is the one figure of the
two #850 did not move. The last line read `34 suite(s) run, 1035 tests; one or
more FAILED` with the runner exiting 1, and the red one was **still only**
`ec/tools/test_check_cluster_citations.py` on the same `:220` of the same #822
file, with the same two `0x0464`/`0x0465` disagreements. **The two notes above
this one are kept in the order they landed rather than renumbered**, so the
numbering runs seventh (#852), the eighth-thing paragraph (also #852's), and then
this note — which is #850's, and is the eighth *note* only because it is the eighth
paragraph of this kind. #850's own write-up derived `33`/`1020` on a tree that
carried #801 and #849 but not #851, and that figure is recorded there as it stood
rather than rewriting the notes above this one for a two-case delta — the same
reason this file exists rather than arithmetic on a diff.)*

*(Ninth merged-tree note, 2026-09-26, the `#850`/`#887` merge, and it is the one
that re-derives the totals in the first paragraph rather than adding to them.
**Thirty-five suites and 1076 tests**, from a `bash tools/run-tests.sh` on this
tree. The seventh note's 1033 was already stale when #887 landed — #887 added
`ec/tools/test_census_test_line_pins.py` at 41 cases and the paragraph above never
moved, so `main` itself was reading *thirty-four* against a runner finding
thirty-five, and #850's two cases make the merged tree 1076. **The red set is
otherwise unmoved: still only `ec/tools/test_check_cluster_citations.py`**, 48
tests, on the same `:220` of the same #822 file with the same two
`0x0464`/`0x0465` disagreements — so neither #850 nor #887 caused it and neither
fixes it. **One suite that #887 added went red on the merge and is green again
here**, which is the eighth-thing paragraph's own subject rather than a new one:
`ec/tools/census_test_line_pins.py` pins the census's own committed-tree counts,
and #850's nineteen new `test_*.py:NNN` citations moved them from `50`/`37`/`32`
to `69`/`44`/`40`. That is a pin doing the job a pin is for — the tree changed
under a figure and the suite said so rather than the figure quietly becoming
wrong — and `check_doc_figure_pins.py` did **not** go red a second time, because
#887's `SELF_MODULES` exclusion already covers both census modules. The notes
above are kept in the order they landed rather than renumbered. Two carry a
merge-time correction rather than a renumber: the eighth, in its first clause, to
say that its counts are its tree's, and the eighth-thing paragraph, whose
"seven places" is a census of a tree rather than a constant — the same two
figures, and the same reason the notes are not renumbered.)*

*(Tenth merged-tree note, 2026-09-26, issue #891 landing beside #801, #849,
#850, #851, #852, #871, #887 and #889: the counts above are this merged tree's,
re-derived from a `bash tools/run-tests.sh` on it — **thirty-five suites and 1076
tests**, which are the ninth note's figures **unchanged**, because #891 adds no
`test_*.py` and no case to an existing one, and so no row to the table below.
The last line reads `35 suite(s) run, 1076 tests; one or more FAILED` with the
runner exiting 1, and the red one is **still only**
`ec/tools/test_check_cluster_citations.py`, 48 tests, on the same `:220` of the
same #822 file with the same two `0x0464`/`0x0465` disagreements. **This note
and the two things with it are renumbered rather than left as a second eighth
and a second ninth**: the notes above are kept in the order they landed, both
sides of this merge carried an eighth and a ninth of their own, and the #891
pair is tenth and eleventh here. The renumbering is this merge's own and the
figures in the paragraphs that follow are moved with it; the
"thirty-four / 1074" the branch recorded are its tree's, before #850's two cases
and #887's suite were beside it.)*
*(A tenth thing this merge moved, and the first one in this file a *suite*
caught rather than a pin. #891's only code file is
`ec/tools/xdata_moved_ranks.py`, and a new self-test case asserting that
`rank_of` reads a `pd-050` id as rank `50` put a bare int inside a `check()`
call — which `ec/tools/check_doc_figure_pins.py` reports as the
`held-by-check-literal` verdict for the figure **`50`**, the `pd` cluster count
that [`docs/findings/xdata-census-rederivation-checklist.md`](../docs/findings/xdata-census-rederivation-checklist.md)
§2b carries at its `390` / `50` row. `ec/tools/test_check_doc_figure_pins.py`
was red on **four** cases, and the fix was in the tool, not the gate: the case
now re-derives the rank from the id beside it rather than writing the expected
value out, which is `xdata_moved_ranks.py`'s own "restated rather than called"
idiom and leaves no int constant in the call. **The gate was right and the code
moved** — the audit cannot tell a rank off a synthetic id from the census's `pd`
count, and its docstring says exactly that. A suite going red here is the same
shape as the eighth-thing paragraph above, from the other end. **One clause of
this paragraph is the branch's tree and the merge has overtaken it**: the
collision was with a row §2b marked `unheld`, and #850 has since given that row
a named assertion, so on the merged tree `check_doc_figure_pins.py` reads
`390`/`50` as `held-by-check-literal` off `TheExportOwnershipClusters`, **marked
held**, §2b's own marking agrees, and the same collision cannot arise from that
row again. That was
re-run here rather than inferred from the marking; the suite is green on this
tree either way.)*
*(And the negative the eighth-thing paragraph is the reason to record, which
**as first written on the branch this merge had wrong**: #891 edits
`ec/tools/xdata_moved_ranks.py` and
`docs/findings/xdata-moved-ranks-fall.md`, and **five citations in the tree pin
a line into the write-up — all five in
`docs/findings/xdata-moved-ranks-second-count.md`, at its `:9`, `:122`, `:201`,
`:210` and `:260`, and none of them pins a line into the tool.** The count
comes from
`grep -rnoE 'xdata[_-]moved[_-]ranks[-_a-z]*\.(md|py)\)?:[0-9]+'
--include='*.md' --include='*.py' .`, which returns those five and nothing
else into that sibling and is the command to re-run. **That merge grew the
write-up from 577 lines to 719, 52 of them ahead of the four anchors it
repoints, so all four of the others went stale by +52, and not one of them
still named what its sentence names**: the write-up's `:394` read a §5 bullet
(`**No assertion is edited …**`), `:471` a §7 command line, and `:500` and
`:516` rows of §7's swept table. Each was re-measured against that merged file
and repointed, and `:3` is above every one of that merge's insertions, so it
did not move. **So the count is 5, not 0, and the negative as written
pointed the wrong way: the same grep run before the merge rather than after it
is what found the four, and nothing else in the tree would have run it.**
`ec/tools/check_citation_lines.py` does not catch any of it — its own docstring
scopes it to citations into generated CSVs and decompiled `.c` — so a citation
into a write-up is held by nothing but a note like this one, which is the
eighth-thing paragraph's whole argument arriving one file over. **Two pins are
deliberately left, both by the eighth-thing paragraph's own rule rather than
against it:** its `:184-187` → `:193-196` is the record of what #852's merge
did, the way its `:303` → `:307` is, and re-pointing that would falsify a
history rather than mend a citation; and in
`xdata-moved-ranks-second-count.md` the `577-line` and the `14`/`15` transcript
counts are #886's own record of what its change did, as wrong to rewrite from
here as the eighth-thing paragraph's pin is. What this diff did to a sibling's
prose is recorded here rather than edited into it — except where the line it
names moved, which is the next paragraph.)*
*(What the merges beside this one then did to that same record, because the note
above is only true of the tree it was written on. Re-run here on the merged
tree, the same grep returns **eighteen**, and it returns them for four
reasons. Five are the citations the note above re-points. One is #884's
[`xdata-flip-cause-derivation.md`](../docs/findings/xdata-flip-cause-derivation.md)
citing `xdata-moved-ranks-fall.md):3` as well. **Three are #889's**, in
[`xdata-decile-small-set-contract.md`](../docs/findings/xdata-decile-small-set-contract.md),
which did not exist on the branch's tree, and **all three went stale under
#891**: its two citations into the write-up, `:199` and `:220`, which are
repointed to `:208` and `:240` with the flipped-cluster header they name moved
from `:214` to `:234` and two `rank A` / `rank B` columns wider, and its one
citation into the tool, `xdata_moved_ranks.py:243`, which is `def deciles()` on
`main`, `:277` after #891 and `:332` on this branch beside it — it **records another line**. Seven are #887's own, in
[`docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md):
three rows of its per-pin table, three bullets of its finding-6 list and its
follow-up 1, which the `):NNN` end of the pattern catches precisely because the
first column of that table is a link followed by a line number. **And two are
this paragraph**, which quotes two of the citations it is counting — a note
recording a grep over the tree is two hits heavier once it is in it, so
**sixteen** is what
the same command returns with those two quotes deleted, and this one is written
to be re-runnable rather than to be right about a tree it is not in. The count
ran
**seven** on the tree the note above was written on, **nine** on the tree the
merge beside it landed on and **ten** on the tree the #891 note below was written
on, and the arithmetic of the four is those three, the three #889 added, the
four #887 added and the two this paragraph is.

`:3` is still above every insertion either merge makes, so it is the one
citation in the set that **no** re-derivation has ever moved. The write-up grew
by #891's 142 lines and by #889's twelve more on top of the 589 `origin/main`
held, and #889's twelve went in at `:328` — ahead of all four anchors, which is
the same displacement #891's 52 was, one merge later. The four the note above
repointed are therefore stale a
second time and are repointed again: `:446` → `:458`, `:523` → `:535`,
`:552` → `:564` and `:568` → `:580`, and the §9 transcript the last of those
names has itself been re-run since, which moves it to `:590` and leaves the
other three where they are. Each was re-opened against the merged
file, and each still names what its sentence names. The `14`/`15` counts the
note above left alone stayed left alone; what did move is the **`34`** in the
sibling's own merged-tree note, which existed to state the tree's current check
count and so had to be re-measured — the tool prints **39** now, `25 + 5 + 9`,
and the sentence above it there about the mutation being green "against all 25"
was re-run and is green against all 39. The two are different kinds of record
and the difference is the point: one is what a change did, the other is what
the tree is, and only the second one is a measurement to repeat.)*

*(A twelfth merged-tree note, 2026-09-26, issue #888 landing beside #891, and
this one is the same story the note above tells for the fourth time: **#888 also
rewrote `xdata-moved-ranks-fall.md`**, putting two `cluster_key unique …` lines
and a nine-line note into its §1–§2 blocks and six `ok` lines plus their notes
into §9, so **every anchor above the §9 transcript moved down eleven again**.
The four the note above repointed are repointed a third time — `:458` →
**`:469`**, `:535` → **`:546`**, `:564` → **`:575`**, `:590` → **`:601`** — and
each was re-opened against the three-way merged file and still names what its
sentence names; `:3` is unmoved for the fourth time running, which is the
strongest single piece of evidence in this file that a citing line is a
different kind of thing from a pin. `xdata-decile-small-set-contract.md`'s
three are moved with them (`:208` → `:219`, `:240` → `:252`, `:234` → `:245`),
plus its citation of the tool's own `deciles()`, `:277` → **`:381`**, which is
the only anchor in the set into the `.py` rather than the write-up. The check
count moves a fifth time: the tool prints **45** now, `25 + 5 + 9 + 6`, and the
**39** the note above records is left visible because it is true of the tree
#891 measured.*

*(A thirteenth, 2026-09-26, issue #890 landing beside #888, and the anchors move
a **fourth** time and the check count a sixth. #890 added `write_movement()` and
its four `--self-test` cases to `xdata_moved_ranks.py`, so the same three
quantities move again: the four fall-file anchors are now **`:490`**, **`:567`**,
**`:596`** and **`:622`** (`:469`/`:546`/`:575`/`:601` are the record of the
#888 × #891 tree, and `:458`/`:535`/`:564`/`:590` of the #891 one, and all three
sets are kept rather than overwritten); `xdata-decile-small-set-contract.md`'s
three are **`:240`** and **`:266`**/`:272` — the row and header its correction 1
names, which this note also corrects, the `:252`/`:245` the note above recorded
having been one line out on the row even on its own tree — and its citation of
the tool's own `deciles()` is **`:436`**, `:332` on `main` and `:381` on #888's.
`:3` is unmoved for the fifth time running, which is the point of printing it
each time. **The check count is `25 + 5 + 9 + 4 + 6 = 49`**: #890's four print at
21–24, ahead of #888's six, which move to 44–49. The **45** the note above
records is left visible because it is true of the tree #888 × #891 produced.
**Nothing else in this file moves**: `bash tools/run-tests.sh` reads
**thirty-five suites and 1076 tests**, the eleventh note's figures unchanged, and
the red suite is still `test_check_cluster_citations.py` — verified against a
pristine `bdfddcfd` worktree, so it is not this merge's.)*

*(Fourteenth merged-tree note, 2026-09-26, issue #929 landing beside the
`#888`/`#890` merge. **The check count is the one figure this merge moves, and
it is `25 + 5 + 9 + 4 + 6 + 4 = 53`**: #929's four print at 50–53, after
#888's six at 44–49. They are not a new subject — every case in the suite was
reached through a census with a mover in it, and these four are reached through
one whose *only* colliding rank is intact, plus the first case that holds
`keyed_by`'s docstring claim rather than restating it. **One earlier `ok` line
changed too**, which no previous merge in this series has done:
`xdata_moved_ranks.py`'s key-indexed check reads `three committed ranks on one
key, of which two moved` where it read `two moved ranks on one key`, because
`flip_table`'s `collapsed` population widened from the moved ranks to the whole
committed census.
**`xdata-decile-small-set-contract.md`'s citation of the tool's own
`deciles()`** moves from **`:436`** to **`:485`** — that pin was correct on the
tree this lands in's parent and is not correct on this one, and it is this
merge's own breakage, so it is repointed here. **Two already-stale pins are
deliberately not**: the `xdata_moved_ranks.py:243` this note above records, and
`xdata-write-direction-correction.md`'s `:181`, were already wrong on `main`
before this merge (`deciles()` is at `:485` and `write_movement()` at `:255`
here, and neither was at `:243`/`:181` on this merge's base `31f683e5` either),
and this file's own rule is that deciding what a drifted pin was meant to name
is a next pass's call and not a merge's. Those two are the ones this change can
see; it is not a claim that the family has no others. **Those two are decided
now**, and the sentence above is corrected beside itself rather than edited
down. `xdata_moved_ranks.py:243` is at `:487`, so the `:485` this note prints for
`deciles()` and the `:255` it prints for `write_movement()` are `:487` and
`:257` on the merged tree, and the `:485` this note says the
`xdata-decile-small-set-contract.md` pin was repointed *to* is likewise `:487`.
Each superseded value stays written, each true of the tree it was measured on.
**The two decisions differ because the two sentences differ**: `:372` is a
record of a past tree and **records another line**, while the parenthetical
above asserts the present tree and is simply wrong. The walk behind both — and
it corrects this note's own reading of them — is in
[`xdata-moved-ranks-pin-decisions.md`](../docs/findings/xdata-moved-ranks-pin-decisions.md).
**`xdata-decile-small-set-contract.md`:3` is unmoved for the sixth time
running**, which is the point of printing it each time; the
`xdata-moved-ranks-key-collision.md`:3-11`, `xdata-moved-ranks-fall.md`:3-11` and
`xdata-moved-ranks-fall.md`:490` anchors this move did not touch are likewise
left where they are. **Nothing else in this file moves**, and the red suite is
still `test_check_cluster_citations.py` — re-verified against a pristine
`31f683e5` tree, this merge's own base, rather than the `bdfddcfd` one the note
above used: `python3 -m unittest discover -s ec/tools` runs 794 tests on this
tree with the same single failure and the same two `0x0464`/`0x0465`
disagreements on `:220` of the #822 file, so #929 neither caused it nor fixes
it. `xdata_register_map.py --check` exits 0 over 1326 register rows and 439
cluster rows, and `test_xdata_cluster_names.py` runs 30 tests, OK, both
re-measured here rather than carried over.)*

*(Fifteenth merged-tree note, 2026-09-26, issue #929 landing beside #885. **Two
of the figures in the note above do not reproduce on this tree, and one anchor
was moved by the other side rather than by this merge.** The `:485` and `:255`
it gives for `deciles()` and `write_movement()` are each two short, and each
lands on a blank line: `def deciles(sizes):` is at **`:487`** and
`def write_movement(on, off):` at **`:257`**, with `:485` and `:255` the first
blank of the pair above each. **That is #929's own miss, not this merge's** —
the tool is byte-identical on #929's tip and here, `main` did not touch it, and
both values read the same on both trees, so the wrong pair stays visible above
per [`../docs/findings.md`](../docs/findings.md) §4a-4d rather than edited into
it.
`xdata-decile-small-set-contract.md`'s citation is repointed to `:487` in place
and carries the correction beside it, because a pointer that names the wrong
line is worth repairing even where the figure beside it is left alone.
**The `xdata-moved-ranks-fall.md`:490` anchor the note above says this move did
not touch has moved again**, from `:515` to **`:536`**, and is still a heading,
`## 7. The 43 swept addresses, per address`: **#885's twenty-five lines in that
file** landed at line 435 and pushed it down once, and #929's own §2 correction
beside the two `pair` transcripts pushed it down again. The other three anchors the
note lists — `xdata-decile-small-set-contract.md`:3`, and the two `:3-11`
headers — are unmoved. **`:490` is left reading as the value the note above
recorded**, per [`../docs/findings.md`](../docs/findings.md) §4a-4d rather than
edited into it: that is the treatment `:485` and `:255` above get and not the
one `xdata-decile-small-set-contract.md`'s citation gets, because that one is a
pin in a findings file that is still being read and this one is a line number
printed inside a dated note — which is what lets the next note say whether it
moved.
**Everything else in the note above re-measures on this tree and stands**: 794
tests from `python3 -m unittest discover -s ec/tools` with the same single
`test_check_cluster_citations` failure, `xdata_register_map.py --check` at 1326
register rows and 439 cluster rows, `test_xdata_cluster_names.py` at 30 tests,
and `census_test_line_pins.py` at **73 occurrences in 26 files, 46 spellings,
42 targets, 57 resolves, 16 declined** — byte-identical to a pristine
`origin/main` worktree, so #929's new file adds no pin and the figure
`../findings.md` §62 carries is still the one the run prints.)*

*(Sixteenth merged-tree note, 2026-09-26, issue #929 landing beside #771 (#932)
and beside #930 (#931), which landed in the same window.
**One figure in the note above does not reproduce on this tree, and it is the
census's, and the two merges beside this one are why rather than #929's.** The
`census_test_line_pins.py` run the fifteenth note transcribes — **73 occurrences
in 26 files, 46 spellings, 42 targets, 57 resolves, 16 declined** — is a
pristine `origin/main` run, and it was true of the `main` this branch was written
against. #771's summary landed in the same window and added one markdown file
carrying 32 records, so **`84a89d9a`, the `#885 × #771` merge, reads `105
occurrences in 27 markdown files, 78 distinct spellings, 58 distinct resolved
targets, 73 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 32
declined`, the 5/17/10/6/35 shape split, and `147` markdown files read** over the
`146` the note above's own tree read. **On the merged tree the run reads `57`
distinct resolved targets and the `5/19/10/6/33` split over `149` markdown files
read**, with the same `105` occurrences, `27` files, `78` spellings, `73` resolves
and `32` declined, and **`#930`, which landed on `main` and not on this branch, is
what moved those three rather than `#929` or `#771`**: its
repoint of the two `:563` pins is the whole of `58 → 57` and
`5/17/10/6/35 → 5/19/10/6/33`, as the `#930` note below records, and the two
markdown files that take the read count from `147` to `149` are `#930`'s and
`#929`'s, one each. **The `73` is a coincidence of arithmetic and not a shared
measurement** — it is `resolves` here and `resolves + declined` above, and
57 + 16 = 73 against 73 + 32 = 105. #929's own new file,
[`../docs/findings/xdata-moved-ranks-collision-scope.md`](../docs/findings/xdata-moved-ranks-collision-scope.md),
carries no `test_*.py:NNN` pin at all, so it moves **the read count by one and
the pinned-file count not at all** — `27` is `27` on `84a89d9a`, on `main` at
`271389d7` and here, which is the headcount the `#930` note reads too; the
fifteenth note's "so #929's new file adds no pin" is still true, and what changed
underneath it is what `origin/main` reads. **The superseded figures stay visible
above per [`../docs/findings.md`](../docs/findings.md) §4a-4d**, and
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
carries the re-transcribed block, the re-registered row and a per-merge section
for it — its `#929` × `#930` merge section is the one place in the tree that
holds the `57`/`5/19/10/6/33`/`149` reading, and it is the place to look rather
than this one. A local checkout also carries the untracked `.claude-pr/CLAUDE.md`
that the tool's directory walk reads, so the same run prints `150` there; the
figures here are the clean tree's, which is what that section's are too.*
**Everything else in the two notes above re-measures on this tree and stands**:
`xdata_moved_ranks.py --self-test` at **53** and the `25 + 5 + 9 + 4 + 6 + 4` sum,
`deciles()` at **`:487`** and `write_movement()` at **`:257`**,
`xdata-moved-ranks-fall.md`'s §7 heading at **`:536`**,
`xdata-decile-small-set-contract.md`:3 unmoved and the two `:3-11` headers
unmoved, `xdata_register_map.py --check` at **1326** register rows and **439**
cluster rows, `test_xdata_cluster_names.py` at **30** tests, and **794** tests
from `python3 -m unittest discover -s ec/tools` with the same single
`test_check_cluster_citations` failure — which is red with the identical message
on `main` at `84a89d9a` as well as on `31f683e5`, so the fifteenth note's
"re-verified against a pristine `31f683e5` tree" is not the whole of the check.
**The committed census is re-derived here rather than carried over: 439 rows over
439 distinct `cluster_key` values, 0 collisions**, and the 445-row guard-off
regeneration the tool reads comes back at **445** as well. **Nothing either
branch wrote lands above this file's `:159`**, which is the one pin in this class
`test-line-pin-census.md` registers from here.*

*(Seventeenth merged-tree note, 2026-09-26, issue #942 (#945) landing beside
#929. **One figure in the note above is one short, and it is the corpus
denominator rather than anything about pins: the clean tree's
`census_test_line_pins.py` run reads `150` markdown files where the sixteenth
note records `149`.** #942 added
[`../docs/findings/pin-table-row-reconciliation.md`](../docs/findings/pin-table-row-reconciliation.md)
to the corpus, and it carries no `test_*.py:NNN` pin — the same shape the note
above records for #929's own file, which is why this is the second merge in a row
whose whole move is a denominator. `census_test_line_pins.py` re-run on the tree
this merge produces reads **`105` occurrences in `27` markdown files, `78`
distinct spellings, `57` distinct resolved targets, `73` resolves, `32` declined,
the `5/19/10/6/33` shape split, over `150` markdown files read against `36` test
files** — so the `105`/`27`/`78`/`57`/`73`/`32` and the split are the sixteenth
note's figures unchanged and the `149` is the only one of the ten that moves.
**The `36` test files are one more than the `35` the
`../docs/findings/test-line-pin-census.md` re-transcription beside this records
for the `#929` × `#930` tree**, because #942 added
`ec/tools/test_check_pin_table_rows.py`. The `149` stays visible above per
[`../docs/findings.md`](../docs/findings.md) §4a-4d, and the sixteenth note's
"a local checkout … prints `150` there" is now the *clean* tree's figure, so a
local checkout reads `151` for the `.claude-pr/CLAUDE.md` reason that note gives.
**`test-line-pin-census.md` is the place to look rather than this one**, and its
`#929` × `#930` merge section carries the `150` in place beside the `149`.
**Nothing else in the three notes above moves**, and the two figures most likely
to be checked are re-measured rather than carried over:
`xdata_moved_ranks.py --self-test` still reads **53**, `deciles()` is at
**`:487`** and `write_movement()` at **`:257`**,
`xdata-moved-ranks-fall.md`'s §7 heading at **`:536`**, and
`xdata_register_map.py --check` at **1326** register rows and **439** cluster
rows. `check_pin_table_rows.py` — the tool #942 adds — reads
**105 rows, 105 records, 105 placed, all seven classes 0** on this tree.
**This file's own `:159` pin is the exception, and it moved because of the
correction above rather than because of anything #942 wrote:** the sentence that
needed correcting is seven lines *above* it, so the repoint list the pin names is
now at **`:166`**, and
`../docs/findings/test-line-pin-census.md`'s per-pin table, its supersession-shape
legend and the blocker argument that names the line are re-registered to `:166` in
place. **The sixteenth note's "nothing either branch wrote lands above this file's
`:159`" was true of the tree it measured and is left standing per
[`../docs/findings.md`](../docs/findings.md) §4a-4d** — it is this merge's own
correction that broke it, which is the sixth time this file's `:159`-line pin has
been the price of a note beside it, and the first where the note was the merge's
own rather than a neighbour's.
**The suite totals move with #942 and are re-derived rather than carried over:
this file's own "What it runs" sentence is corrected in place above, because it
is the one present-tense claim of them, and `bash tools/run-tests.sh` on this
tree reads `36 suite(s) run, 1112 tests; one or more FAILED` where the three
notes above record thirty-five and 1076.** `python3 -m unittest discover -s
ec/tools` reads **830** tests where the notes above read **794**, which is the
same 36 cases from the same one suite. **The single failure is
`test_check_cluster_citations` and it is red on pristine `main` at `c68f89df`
with the identical message** — the two `0x0464`/`0x0465` disagreements at `:220`
of #822's write-up that the notes above name — so it is a pre-existing failure
wearing a merge's name, and this merge neither caused it nor fixes it.*

*(Eighteenth merged-tree note, 2026-09-26, issue #929 (#933) landing beside #941
(#946) and #777 (#944). **Two of the figures in the note above do not reproduce
on this tree, and one of them is the note's own subject: the suite totals.** The
`36 suite(s) run, 1112 tests` and the `830` from `python3 -m unittest discover -s
ec/tools` are this merge's *base*, and on the tree this merge produces the runner
reads **`38 suite(s) run, 1161 tests`** and the `ec/tools` discovery reads
**`857`** — the `857` being `830 + 27`, #941's
`ec/tools/test_check_pin_table_by_cited_file.py`, and the `1161` being `1112 +
27 + 22`, those 27 plus #777's `tools/test_doc_patch_refs.py`. **That is also why
"What it runs" above is corrected a second time and carries three superseded
pairs**: the eleventh note's thirty-five and 1076, #929's thirty-six and 1112 and
`main`'s thirty-seven and 1134 are each true of the tree it was measured on, and
none of the three saw the other's suite, so the merged sentence is re-derived by
running the runner rather than by adding the three up. `main`'s own §65 note in
[`../docs/findings.md`](../docs/findings.md) has the same gap in a different
figure — it reads *"11 of the **37** indexed `test_*.py`"* where the merged tree
indexes **38** and **27** are named by none, and a `git archive origin/main`
extraction is where that one was checked rather than asserted.
**The `> 300` floor's citing line moved once more and the moved value is `:9158`
rather than `:9114`**: #946's §65 addition puts **26** lines above it in
[`../docs/findings.md`](../docs/findings.md) and this merge's own §65 correction
beside that note puts **18** more, so `9077 + 37 + 26 + 18 = :9158` is the whole
of it, and `test-line-pin-census.md`'s per-pin table, its supersession-shape
legend and its blocker argument are re-registered to it in place with the
`:9103` and `:9114` left written. **This file's own `:159` pin is the exception
again, and for the fourth time running**: `159 + 9 + 7 + 22 = :197` is where the
repoint list that pin names now sits — `main`'s nine lines above it, the
seventeenth note's seven, and the twenty-two the two "What it runs" corrections
above add beside both — and the three places that name it are re-registered to
`:197`. **Every other anchor the four notes above name is unmoved**, and each was
re-measured rather than carried: `xdata_moved_ranks.py --self-test` at **53**,
`deciles()` at **`:487`** and `write_movement()` at **`:257`**,
`xdata-moved-ranks-fall.md`'s §7 heading at **`:536`**,
`xdata_register_map.py --check` at **1326** register rows and **439** cluster
rows, `test_xdata_cluster_names.py` at **30** tests, and the committed census
re-derived at **439** rows over **439** distinct `cluster_key` values with **0**
collisions, the **445**-row guard-off regeneration included.
**The red set is the single suite the four notes above name, and it is the first
of them that had to be checked rather than assumed** — this merge was briefly red
on four, and the three it added were `test_census_test_line_pins.py`,
`test_check_pin_table_rows.py` and `test_check_pin_table_by_cited_file.py`: the
first two the two rows this merge re-registered, the third the one self-test pin
it moved. All three are green again. **The fourth, `test_check_cluster_citations`, is 48 tests with the
one failure, re-run here from a `git archive origin/main` extraction where it
fails identically** on the same `:220` of #822's write-up with the same two
`0x0464`/`0x0465` disagreements, so it is a pre-existing failure wearing a
merge's name for the ninth note running.*

*(Nineteenth merged-tree note, 2026-09-26, issue #778 (#947) landing beside #929
(#933). **Every anchor the note above re-measures is unmoved except one, and the
one that moved is the branch's rather than the merge's:
`xdata-moved-ranks-fall.md`'s §7 heading is at `:547`, not the `:536` four notes
in this file now record.** #778's merge added **eleven** lines to that write-up
*above* the §7 heading — a ten-line "Confirmed and acted on" paragraph beside the
two-largest case, plus its blank line — and it is the only change in this merge
that lands above a line this file's notes name. **`536 + 11 = :547` is the whole
of it**, and `536` stays written in the sixteenth, seventeenth and eighteenth
notes above, each true of the tree it measured on, per
[`../docs/findings.md`](../docs/findings.md) §4a-4d; none of the three is edited.
`docs/findings.md` §74, which asserts the four anchors are where these notes say
they are, is corrected in place beside the claim for the same reason.

**The other three re-measure unchanged, and so do the figures the note above
treats as its own**: `xdata_moved_ranks.py --self-test` at **53**,
`deciles()` at **`:487`** and `write_movement()` at **`:257`**,
`xdata_register_map.py --check` at **1326** register rows and **439** cluster
rows, `test_xdata_cluster_names.py` at **30** tests, and the committed census
re-derived at **439** rows over **439** distinct `cluster_key` values with **0**
collisions. **The suite totals are the note above's and they still hold**:
`bash tools/run-tests.sh` on this tree reads `38 suite(s) run, 1161 tests; one or
more FAILED` and `python3 -m unittest discover -s ec/tools` reads **857**, so
"What it runs" at the top of this section is **not** corrected a third time and
its three superseded pairs stay as they are. *(Corrected at the #962 × #794
merge, beside the clause rather than in it per
`../docs/findings.md` §4a-4d: it was not corrected a third time on **#778's**
tree, and it has been twice since — to `1165` by #794 and to **`1168`** on the
merged tree, with `1164` between them from #962. The `1161` and `857` above are
true of the tree this note measured, and the "three superseded pairs" it names
are now **five**; the twenty-first note below carries the merged figures and the
arithmetic.)* **The red set is the single suite
the notes above name**: `test_check_cluster_citations`, 48 tests, the one
failure, on the same `:220` of #822's write-up with the same two
`0x0464`/`0x0465` disagreements.

**This file's own `:159` pin does not move for the fifth time, and that is worth
saying rather than leaving to be assumed.** This note is below `:197` and the
`What it runs` sentence above it is unchanged by this merge, so
`159 + 9 + 7 + 22 = :197` still holds and the three places
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
names are still registered to `:197` — checked by running
`check_pin_table_rows.py` rather than by reading this paragraph, which reads
**106 rows, 106 records, 106 placed, all seven classes 0** on this tree. The
**106** is this merge's own: #778's write-up brings the one pin its
`test-line-pin-census.md` correction already counted, and the note above's
`105` is the tree before it landed. *(The `:197` in that sentence is true of
**#778's** tree and is corrected below, beside the sentence rather than in it:
`159 + 9 + 7 + 22 + 6 = :203` is the whole of it, and
`check_pin_table_rows.py` reads the row at `:203` on the merged tree with the
same **106 rows, 106 records, 106 placed, all seven classes 0** the sentence
above prints. The sentence above is left as written, per §4a-4d, and the
twenty-first note below carries the correction.)*

*(Twentieth merged-tree note, 2026-09-26, issue #962. **The runner reads
`38 suite(s) run, 1164 tests; one or more FAILED`, and
`python3 -m unittest discover -s ec/tools` reads `860`** — the note above's
`1161` and `857` plus the three cases this merge adds, and the suite count
unmoved at `38` because `ec/tools/test_xdata_cluster_names.py` was already
counted. **`test_xdata_cluster_names.py` is at `33` tests, from `30`:** the
three are `TheGuardOffKeyDistinctness`, a new class holding the guard-off
generation's `cluster_key` distinctness, its registers/clusters agreement, and
the negative control, over the one `guard_off()` regeneration the module
already cached. **The red set is the single suite the notes above name** —
`test_check_cluster_citations`, 48 tests, the one failure, on the same `:220`
of #822's `xdata-cluster-names-guard-off-recipe.md` with the same `0x0464` and
`0x0465` disagreements. No suite was added, none was removed, and
`xdata_moved_ranks.py --self-test` is at **53** and
`xdata_register_map.py --check` at **1326** register rows and **439** cluster
rows, all unchanged; the write-up is
[`../docs/findings/xdata-guard-off-key-distinctness.md`](../docs/findings/xdata-guard-off-key-distinctness.md),
whose §4 re-derives the committed census at **439** rows over **439** distinct
`cluster_key` values with **0** collisions and the guard-off regeneration at
**445** over **445**.*

*(**And the per-pin table moved with the tree, which is the cost this note
exists to name.** Adding a class to `test_xdata_cluster_names.py` and correcting
a docstring above it shifted every line below by 34, so **25 of the 106 rows
changed shape cell** and the published `5/19/10/6/34` landing-shape split moved
to `0/16/22/5/31`; both places that pin it were re-derived to the measured
value rather than loosened, and **eight verdicts that had gone stale were
re-read**, which is why `test-line-pin-census.md`'s "the eleven that do not
carry" reads nineteen. The headcounts are unmoved at **106 pins, 28 files, 79
spellings, 58 targets, 74 resolves, 32 declined**, the read column is unmoved at
`53/19/2/32`, and `check_pin_table_rows.py` still reads **106 rows, 106 records,
106 placed, all seven classes 0** — which is the control that says the delta is
where each pin lands and not what the corpus contains. **This file's own `:197`
pin does not move, and the one row it contributes is the only one of the 25 that
moved the right way** — the line it names now reads `assertion` where it read
`other`, landing on the `self.assertIn` in
`test_xdata_cluster_names.py::TheCarry::test_a_tie_is_reported_and_no_winner_is_picked`.
**Its citing line is unmoved and its claim about the old `:303` → `:307` is a
record of a past merge**, true of the tree it was measured on, and it is left
written rather than edited per `../docs/findings.md` §4a-4d; what moved is the
line it names, which is what the row above now says. **Named by class and case
rather than by line here on purpose**: a `test_*.py:NNN` in this note would be a
107th record with no table row, and the spelling that costs a row and not a
record is the one this file's own notes above have been steering away from.*

*(Twenty-first merged-tree note, 2026-09-26, issue #794. **The suite totals move
and nothing else does, and both figures are re-derived by running the two
commands the sentence above names rather than by editing it blind.** #794 adds
four cases to `ec/tools/test_check_testdata_row_claims.py` and no suite, so on
the tree this note was written against `bash tools/run-tests.sh` read
**`38 suite(s) run, 1165 tests; one or more FAILED`** where the note above read
`1161`, and `python3 -m unittest discover -s ec/tools` read **`861`** where the
same note read **`857`**. **It is renumbered and re-measured at the #962 × #794
merge, and the position matters: this note is below the twentieth rather than
beside the nineteenth,** because two summaries took "Nineteenth" in the same
window and #778's, which is the one `main` held first, keeps it — the same rule
`../docs/findings.md` §76's numbering note records for its own collision, in the
other direction. Placing it here is also what repairs the note above's own "the
note above reads" clause, which pointed at this one. **On this tree the two
figures are `38 suite(s) run, 1168 tests` and `864`**, and the arithmetic is
additive from both sides rather than from either: #962's `1164`/`860` plus this
issue's four cases is `1168`/`864`, measured by running both commands again
rather than by adding a diff, and the superseded `1165`/`861` stay written as
the pair that was true of this branch's own tree. **The red set is unchanged, and
it was re-checked here rather than carried**: the single suite the notes above
name, `test_check_cluster_citations`, 48 tests, the one failure, on the same
`:220` of #822's write-up with the same two `0x0464`/`0x0465` disagreements —
which is the state `main` and this branch each measured on their own tree
before either merged, so it is a re-derivation and not an assumption.
**"What it runs" above is corrected a **fourth** time, `1161` → `1164` → `1165`
→ **`1168`**, with every superseded value left visible beside it** per
[`../docs/findings.md`](../docs/findings.md) §4a-4d; the eleventh note's thirty-
five and 1076, #929's thirty-six and 1112, `main`'s thirty-seven and 1134 and
#778's thirty-eight and 1161 are each true of the tree they were measured on, and
none of the four saw another's suite or cases.*

**This file's own `:197` pin moves for the sixth time, and by +6, and this is
this issue's own doing.** The correction above adds six lines *above* `:197`, so
`197 + 6 = :203` and `159 + 9 + 7 + 22 + 6 = :203` is the whole arithmetic; the
row in [`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
is re-registered to `:203` with the `:197` above left written, per §4a-4d, and
`check_pin_table_rows.py` reads **106 rows, 106 records, 106 placed, all seven
classes 0** on this tree — checked by running the tool rather than by reading
this paragraph. **The `:203` is the merged tree's reading and it holds for the
same reason here as on that one**: `main` adds nothing above `:197`, so the `+6`
above is the whole of it on this tree too, and the row places against the run
at `:203` here and on #794 alone. **The suite-table row for that same file is
at `:1073` on this tree, and the `:945` above is a *third* value this note
carried and never re-derived** — `main` reads `:1001` and #794's own tree reads
`:985`, so the number was already stale on the branch that wrote it, which is
worth recording here rather than quietly replacing. The *description cell* is
what the check reads, and it is reworded in place as this note describes:
`ec/tools/test_check_testdata_row_claims.py`'s entry now describes five shapes
and a dated-capture variant rather than six, and the dated-capture rule is
asserted to make the run check *fewer* rather than *more*. The
`test_readme_suite_table.py` set check is unaffected either way, since it
compares the *set* of suites and neither merge adds one.
*(Twenty-fourth merged-tree note, 2026-09-26, the `#929` × `#962` × `#794` ×
`#780` × `#985` × `#979` merge. **The position matters before anything else, for
the reason the note above gives for its own:** two notes took "Twenty-first" in
the same window,
and #794's, which is the one `main` held first, keeps it — the same rule
`../docs/findings.md` §76's numbering note records for its own collision, in the
other direction. This note is placed below it rather than beside it, which leaves
the twenty-first's own "this note is below the twentieth rather than beside the
nineteenth" true as written. **That rule then applies a second time, to this
note's own number**, and this is the first place in this file it has had to:
two notes took "Twenty-second" in the same window, this one and the `#979` ×
`#985` note `main` committed, and the same rule gives the whole of the number to
`main` — so **that note keeps twenty-second**, with the superseded heading a
reader finds in the diff rather than here. **The same rule then applies a third
time, to this note's own number, and the twenty-second's reasoning is what
settles it rather than a new one:** `main` committed a "Twenty-third" of its
own for the `#979` × `#973` merge in the window after this note was written, and
the rule has said from the first of these three collisions that **the note
already committed on `main` keeps the whole number and the branch's own gives
way** — so `main`'s keeps twenty-third and **this one is twenty-fourth**, the
number it was first given left in the diff beside the reasoning that gave it.
**The file's notes are appended in merge order and are not in numeric order, so
the number moved twice and the paragraph did not move at all:** the
twenty-first is above this note, `main`'s twenty-second is below it, `main`'s
twenty-third is below that, and the eleventh already sat below a "twenty-second"
before this merge, so the ordering was the file's property and not either
collision's.

**The runner reads `39 suite(s) run, 1221 tests; one or more FAILED`, and
`python3 -m unittest discover -s ec/tools` reads `917`** — both re-derived by
running the two commands this file's own first note names rather than by adding
three diffs, and **neither the note above's `1168`/`864` nor the `1187`/`883` this
note carried on #780's own branch is the base, because `main` has moved
twice since the note above was written.** `origin/main` at `368e9e52` reads
`1177` and `873` of its own and at `3e020cf4` reads `1208` and `904`, each
measured the same way, so the arithmetic is `1208 + 3 + 10 = 1221` and
`904 + 3 + 10 = 917`. **The suite count moves for the first time in this run of
notes, `38` → `39`, and it moves because of `main` rather than because of
#780**: `3e020cf4` (#985) committed
`ec/tools/test_disasm8051_oracle.py` at 31 cases, so `1177 + 31 = 1208` is that
commit's own step. **The ten are still #780's alone, `59` → `69` in
`ec/tools/test_check_testdata_index.py`, which was already counted, and the three
between the two are #979's, `47` → `50` in
`ec/tools/test_check_testdata_row_claims.py`.** **Six
superseded pairs stay written, each
true of the tree it was measured on**, per
[`../docs/findings.md`](../docs/findings.md) §4a-4d: the `1211`/`907` `main`'s
twenty-second below re-derived for the tree #780 was not on, the `1218`/`914`
this note carried before #979's three cases were added to it, the
`1187`/`883` this note
carried on #780's own branch, the `1174`/`870` that branch's pre-merge tree read,
the `1165`/`861` #794's branch read, and the
`1164`/`860` the twentieth above names. **"What it runs" is therefore corrected a
fifth time, `1161` → `1164` → `1165` → `1168` → `1211` → `1221`, and the fourth
correction's own `1168` and this note's first `1187` are both now superseded** —
the sentence carries `1177 + 31 + 3 + 10 = 1221` beside them, and this is the first of
the five steps taken off `main` rather than off the value the sentence carried,
which is what makes the fourth one a record rather than a base. **It is also the
first of the five that adds a suite rather than cases to one**, so the "no merge
added a suite" clause is superseded in the two places that carry it: the
twenty-first note keeps it, written, true of every tree until `3e020cf4`, and
this note's own says below what #780 did and leaves #985's suite to the figures
above. Neither clause is edited out of silence, per §4a-4d.

**The red set is the single suite the notes above name, and it was re-checked
here rather than carried:** `test_check_cluster_citations`, 48 tests, the one
failure, on the same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md`
with the same two `0x0464`/`0x0465` disagreements, byte-identical to the same
failure in a `git archive origin/main` extraction — so this merge neither causes
it nor fixes it. *(That extraction is not a git tree, so
`ec/tools/test_walk_budget_census.py` reads red in it — its pinned baseline
`e198fd9` is fetched with `git show`, and a directory with no `.git` cannot
answer that — and green on the real tree, which is why the extraction is
evidence about the one suite above rather than a second run of the runner.)* No
suite was added **by #780**, none was removed, and the one `3e020cf4` added is
counted in the `39` above and changes nothing else here —
`xdata_moved_ranks.py --self-test` is at
**53** and `xdata_register_map.py --check` at **1326** register rows and **439**
cluster rows, all unchanged, and `check_testdata_index.py`'s own fifth-direction
line is unmoved at **2 fixture CSV(s), 0 with no `evidence` column, 10 evidence
cell(s), 11 evidence path token(s): 11 resolved, 0 missing, 0 unresolved** — the
first four lines byte-identical to before, re-run rather than carried. **Nothing
else this merge touched is a moving figure**: `check_pin_table_rows.py` reads 106
rows, 106 records, 106 placed and all seven classes 0, and the landing-shape
split is `0/15/22/5/32` — the twentieth's `0/16/22/5/31` with #780's one
assertion onto prose composed on top of it, which is the same composition
`test-line-pin-census.md`'s correction under its transcript records from the
other end. Named by suite and by count rather than by line here on purpose, for
the reason the note above gives.

**This file's own `:203` pin moves a ninth time, and by +24, and the move is
this note's own sentence rather than #780's.** The "What it runs" correction
above adds twenty-four lines above `:203` on this tree — three on #780's own
branch, seven more for #985's 31 cases and its suite beside #780's ten, three
more for the superseded-value clause added beside them, and **eleven more for
the two sides' figures having to be written side by side rather than one of
them**, which is this merge's own cost and not either branch's — so
`203 + 24 = :227` and
`159 + 9 + 7 + 22 + 6 + 24 = :227` is the whole arithmetic; the row in
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
is re-registered to `:227` with the `:216` this note carried, the `:206` and
`:203` above it, and `:1195` left written, per
§4a-4d, and
the tool reads **106 rows, 106 records, 106 placed, all seven classes 0** on
this tree — checked by running it rather than by reading this paragraph. **The
suite-table row for that same file is at `:1318` here, not the `:1317`, `:1315`
and `:1294` three earlier drafts of this note gave, nor the `:1156` it carried
on #780's own branch**, and the move is
the sum of four: `3e020cf4`
committed one row above it — `ec/tools/test_disasm8051_oracle.py`'s, at `:1295`
here — and this note, its corrected parenthetical and the twenty-second note's
supersession paragraph below the table added the rest. **Both
positions are measured on the merged tree and on `origin/main` at `abfe76e6`
rather than differenced**, by reading the two lines out of a `git archive`
extraction of each: `main` reads `:1160` for the suite-table row and `:203` for
the pin, and this tree reads `:1318` and `:227`, so `1160 + 158` and
`203 + 24`. The `1087` this note gave for `main` at `368e9e52` is a **fourth**
value for that denominator and the one that is furthest off: that commit reads
`:1100`, and the base reading `1100` rather than `1087` is itself the record of
a tree that wrote a number and did not measure it. **All of them stay written,
each true of the tree it was measured on — or, in `:1087`'s case, the tree it
was claimed for** — per §4a-4d, and none is edited into another. The
twenty-first's `:1073` and the three it names as never re-derived, `:945`,
`:1001` and `:985`, are the earlier values in that series. **The `:203` →
`:227` step above is moved by #985's one line only in the sense that it is not
moved by it at all**: that row is at `:1295`, below `:227`, so the two
corrections are independent and neither is arithmetic on the other — checked by
reading both lines rather than by assuming a merge's diff lands above a pin it
does not name.*

*(Eleventh merged-tree note, 2026-09-26, issue #891 landing beside the
`#850`/`#887` merge: the counts above are this merged tree's, re-derived from a
`bash tools/run-tests.sh` on it — **thirty-five suites and 1076 tests**, which
are the tenth note's figures **unchanged** and the ninth note's before them, so
this note moves neither of the two and says so rather than restating them as a
third derivation. The last line reads `35 suite(s) run, 1076 tests; one or more
FAILED` with the runner exiting 1, and the red one is **still only**
`ec/tools/test_check_cluster_citations.py`, 48 tests, on the same `:220` of the
same #822 file with the same two `0x0464`/`0x0465` disagreements, so #891
neither caused it nor fixes it. **The live sentence at the top of this section
was stale before this merge, and it is re-derived now** — which is the ninth
note's own finding reached from the other side rather than a new one: #849 and
#851 each brought a table row *and* a note re-deriving the two figures beside
it, and #887 brought a row with no note, so `origin/main` was already reading
"thirty-four today, 1033 tests" with thirty-five suites under it. That is this
file's own instruction — *re-derive them by running it rather than by editing
this sentence* — being the one step a merge that adds a row can skip, and the
sentence reads thirty-five and 1076 because the runner put them there rather
than because they were written down. The `1033 + 41 = 1074` the branch recorded
is that tree's arithmetic and stays in the tenth note's neighbourhood rather
than here, because on this tree the addition that lands is #850's two cases and
#887's forty-one together: `1035 + 41 = 1076`.)*

*(An eleventh thing this merge moved, and the first one in this file a *sibling's
own write-up* is the victim of. #887's
[`docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
gives every pin it censuses a row whose **first column is the citing line** — a
link to the citing file followed by `:NNN` — and the merged tree grew
`xdata-moved-ranks-fall.md`, so the two of its rows naming `:319` and `:331` went
stale by the displacement the notes above record for the four pins they
re-pointed, and `:15` is above every insertion this merge makes and did not
move. **Those two were already stale on `main`, by twelve lines rather than by
sixty-four**, because #889 put its note into that write-up at `:328` and the
census re-measured its counts without re-measuring a column its own tool cannot
see. Both were re-measured against the merged file and repointed — `:319` →
`:383` and `:331` → `:395` — and the census's own reconciled counts do **not**
move with them, which is the shape of the thing rather than a coincidence: a
citing line is not a pin. `census_test_line_pins.py` re-run on the merged tree
prints `69 pin(s) in 24 markdown file(s): 44 distinct spelling(s), 40 distinct
resolved target(s)` with `0 out-of-range`, and `test_census_test_line_pins.py`
is green. **Those three figures are the ninth note's and not the branch's**, and
the difference is worth naming rather than splitting: the branch wrote
`50` / `37` / `32` because #850's nineteen new `test_*.py:NNN` citations had not
landed on its tree, and #850's ninth note wrote `69` / `44` / `40` for the same
reason from the other side. **#891 itself moves none of the three**, because
every pin it edits is inside the census's own write-up and that file is excluded
from the census's own population — which is also why the negative the notes
above record stays a measurement of a *different* class, the plain-text grep the
census cannot see. That grep is the one the note two above gives the count for,
at **eighteen** here against **seven** and **ten** on the two trees those notes
were written on.)*

*(And at the #888 × #891 merge, the same sentence with the same two results. The
census's two citing lines move **again**, to `:394` and `:406`, because #888's
edits to the write-up sit above both; they are repointed a second time in the
census's own table and in the two places its prose names them. **Its own figures
move once, and only because of #888**: the run is now
`71 pin(s) in 25 markdown file(s): 45 distinct spelling(s), 40 distinct resolved
target(s)` with `55 resolves` and `16 declined` and shapes `5/13/9/6/22`, because
#888's write-up is one new markdown file carrying two new `test_xdata_cluster_names.py`
pins — one new spelling, no new target, and `test_census_test_line_pins.py` is
green against them. **#891 moves none of it**, which is the same negative the
paragraph above records and the reason the two merges' edits to one write-up
cancel in the census while not cancelling in the citations into it. The plain-text
grep is the one number this note re-derives: **twenty-one** on the three-way
merged tree against **eighteen**, **ten** and **seven** on the trees those notes
were written on — the three extra are #888's, and all three are one new file:
its own `xdata-moved-ranks-fall.md):3` in the framing line and the census's two
`xdata-moved-ranks-key-collision.md):NNN` rows beside them. **Nothing else
appears and nothing disappears**, which is the point of re-running a grep rather
than reasoning about it: #888 rewrote a write-up that four other files cite, and
the count moved by the number of times the new file is cited, not by the size
of the change.)*

*(And at the #888 × #890 merge, **that note's census figures are the ones that
do not survive, and the grep is the one that moves furthest.** #890 repointed
56 `test_*.py:NNN` pins by +25 and the census re-run reads
`71 pin(s) in 25 markdown file(s): 45 distinct spelling(s), 41 distinct resolved
target(s)` with `55 resolves`, `16 declined` and shapes `5/11/9/6/24` — the
`40` target and the `5/13/9/6/22` split in the note above being the record of the
tree #888 × #891 produced. **The reason is one line, and it is the two pins
#888's own write-up added**: `assertGreater(len(moved), 300)` was at `:563` of
`ec/tools/test_xdata_cluster_names.py` on that tree and is at `:588` here, so
the two by-name pins `:563` are now `other` rather than `assertion` and do not
carry — which is why the target count moves as well, since the by-path spelling
of the same span was repointed to `:588` and the two no longer share a target.
The census's own table, its finding 7 and its follow-up list are re-measured to
that in [`test-line-pin-census.md`](../docs/findings/test-line-pin-census.md),
which keeps the superseded figures visible; `test_census_test_line_pins.py` is
green against the new pins, which is why the pins there moved with them. **Both
line numbers in that paragraph are written bare and away from the file name on
purpose**: spelled as `test_*.py:NNN` they would be the 72nd pin in the class
and would move the very figure the census reports, which is the reason the
write-up gives for writing its own superseded `:392` the way it does. **The
plain-text
grep reads thirty on the merged tree**, against **twenty-four** on `bdfddcfd` and
**twenty-two** on #888's tip — re-run with the same command rather than reasoned
about, and most of the gap is this merge's own re-transcription of the census's
table, which is eleven of the thirty by file. The earlier figures — **twenty-one**,
**eighteen**, **ten** and **seven** — are the record of the trees they were taken
on.)*

*(**And at issue #930, that note's census figures are overtaken a second time, by
a correction rather than a merge.** The repoint that note declined to make has
been made by the follow-up list it pointed at: the two by-name pins now
name `:588`, where the `> 300` floor is, so the run reads
`105 pin(s) in 27 markdown file(s): 78 distinct spelling(s), 57 distinct resolved
target(s)` with `73 resolves`, `32 declined`, shapes `5/19/10/6/33` and
**148** markdown files read — against the `58` targets and the `5/17/10/6/35`
split of the `#885 × #771` block in
[`test-line-pin-census.md`](../docs/findings/test-line-pin-census.md), which is
the record of the tree this pass landed on and is named here rather than as a
neighbour because **neither merge after `#888 × #890` added a note to this
file**: the note above is the `#888 × #890` one, and its `41` and its
`5/11/9/6/24` are two merges further back still. **The three figures that did
not move are the ones worth reading twice.** `105`, `27` and `78` are identical
on both runs, because two rows changed spelling from one line number to another
and neither was added nor deleted: a correction that had introduced a pin while
correcting one would have shown up as a 79th spelling, and that is why the
superseded line number is written bare above and in every file this pass
touches. The `148` is the one figure that moves for a reason of its own — the
repoint's own write-up is a new markdown file — and it carries no
`test_*.py:NNN` pin, so the denominator moved and nothing else did.
**The plain-text grep is not re-derived here, and that is a decision rather than
an omission**: it is a different class, its command is not committed anywhere this
pass can re-run it from, and publishing a figure for it that no reader can
reproduce would be worse than leaving the note above's `thirty` standing as the
record of the tree it was taken on. What a re-derivation would have to show is
that the two repointed rows changed a line number and not a count, and the
census run above already shows exactly that.)*

`docs/findings/0751-grader-self-test-gate.md` records the red set as it stood
and the follow-up issues that owned it, and
[`tools-readme-totals.md`](../docs/findings/tools-readme-totals.md)
records the run these figures are read off. Nothing here sets out to have
fixed either suite.
`test_readme_suite_table.py` checks the *set* of rows below and deliberately
not these counts — its docstring gives the reason — so the paragraphs above
are the only thing holding them, which is exactly why they have to be
re-derived by running the runner rather than by arithmetic on a diff.

> **Corrected 2026-09-25, issue #816.** The paragraph under "The totals are
> not a pass" is left as it was written, and **both of the suites this file
> names as red are green** on the tree this lands on. The first paragraph
> already says so — #821 (`90ac6d2c`) re-cast the two as history rather than
> as state, and #846 and #801 re-derived the counts above it — so what is left
> for this block to add is the half none of those sentences carries: *which*
> suite is red now, and that it is not either of the two named here.
> `ec/tools/test_check_site_census.py` was cleared by #752, which re-pinned
> the four `census_refs` cells onto the lines the corrected `bank0/D091.c`
> has; `ec/tools/test_xdata_cluster_names.py` was cleared by #753, which
> replaced its copy-and-patch recipe with `--no-eq-guard`. **The runner
> nonetheless still exits 1, on a third suite**, and that is the measurement:
>
> ```console
> $ bash tools/run-tests.sh
> ...
> ec/tools/test_check_cluster_citations.py: FAILED
> 32 suite(s) run, 974 tests; one or more FAILED.
> $ echo $?
> 1
> ```
>
> Its one failure is a cluster-membership claim in
> `docs/findings/xdata-cluster-names-guard-off-recipe.md:220` — #822's write-up,
> not this repository's runner being broken. `docs/findings.md` §52 records it
> and names it to that file's owner;
> `docs/findings/runner-red-suite-set.md` tracks the set, one suite wide. So
> "the runner exits 1" above is still true and is now true of a different line.
>
> **The suite and test counts in the two paragraphs above are deliberately left
> as they are**, and this correction does not update them. They are `32` and
> `974` — the *Third merged-tree note* above re-derived them for #801, which
> added `ec/tools/test_check_citation_lines.py` — and they are exactly what the
> runner still prints, as the transcript above shows, so leaving them alone is
> a decision rather than a patch over a stale number. (This block was first
> written against the tree #821 measured, where the paragraphs above read `30`
> and `882`; #846's note superseded those above it at `31` and `934` and
> #801's superseded that, so the block is re-pointed
> rather than left contradicting the sentence it sits under. The count of
> *red* suites is unchanged by either, and this is not the place it is argued.)
> What no check in the tree can see them is still the reason not to touch them:
> `test_readme_suite_table.py` compares the row *set* and nothing else and
> `tools/run-tests.sh` prints its totals and asserts none, a decision
> `docs/findings/runner-red-suite-set.md` sets out at length. **Re-derive them**
> by running the runner, which is what the first paragraph above already
> requires, and which is the whole reason the red/green claim beside it had to
> be re-measured too. `tools/README.md` also has no reason to know anything
> about prose: nothing written in this block can turn a suite red or green. The
> write-up is
> [`docs/findings/xdata-no-eq-guard-measured-state-correction.md`](../docs/findings/xdata-no-eq-guard-measured-state-correction.md).
>
> **Corrected at the merge, 2026-09-25, #850 beside #849.** The transcript
> above and the counts in the two paragraphs are re-derived on `main` and were
> exact there. Two merges move them, and both are in this tree: #849 adds
> `ec/tools/test_check_doc_figure_pins.py` at 44 cases, and #850 adds
> `TheExportOwnershipClusters`'s two cases to
> `ec/tools/test_xdata_cluster_names.py`, so the merged tree reads
> **`33 suite(s) run, 1020 tests; one or more FAILED`** and
> `ec/tools/test_xdata_cluster_names.py` is at **30** tests. Everything else in
> this block stands: still one red suite, still
> `ec/tools/test_check_cluster_citations.py`, still #822's
> `xdata-cluster-names-guard-off-recipe.md:220`. The counts in the two
> paragraphs are left at `33`/`1018` and are now stale in the way this file's own
> first paragraph says a stale count should be handled — **re-derive by running
> the runner** — and this block is where the fact is recorded, rather than the
> paragraphs being rewritten for a two-case delta.
>
> *(Corrected once more at this merge, 2026-09-25, and the `33`/`1020` above
> stays visible because it was true of the tree #850 was written on. **That tree
> carried #801 and #849 but not #851, and #851 added a suite**, so the tree this
> block finally lands in reads `34 suite(s) run, 1035 tests` — the eighth
> merged-tree note above, and 1033 + 2 rather than 1018 + 2. The
> `test_xdata_cluster_names.py` figure of **30** is unaffected: it is 30 on both
> trees, and it is 30 here.)*

*(Twenty-second merged-tree note, 2026-09-26, issues #979 × #985. **The suite
totals move, and this is the merge that re-derives the sentence from a run
rather than from arithmetic**, which is what the note above leaves open. **On
the merged tree `bash tools/run-tests.sh` reads `39 suite(s) run, 1211 tests;
one or more FAILED` and `python3 -m unittest discover -s ec/tools` reads
`907`**, both measured here. Three steps, and **the middle one is a suite**:
`1177`/`873` at this merge's base `368e9e52` (#982), #985's thirty-one cases
and its new `ec/tools/test_disasm8051_oracle.py` taking that to `1208`/`904`,
and #979's three the last step to `1211`/`907`. The suite count is `38` at the
base and `39` from #985 on, so the suite count is the half that has to move
here — and it moves on the *other* side, which is the first time that is true
of a merge in this file.

**The branch's own `1180`/`876` and `38` are left visible above and are not
this merge's, and the reason is worth recording rather than the delta.** They
were measured on a tree from before #982 — which implements #975 — had landed in
the base, and this merge's counterpart on `main` is #985. So the count the
branch could not have known about is the suite, and the delta this issue
contributes is **+3 tests and no suite**: all three in
`ec/tools/test_check_testdata_row_claims.py`, which is `47` at the base and on
`origin/main` and `50` here. **Both sides were right to re-derive rather than
to add up**, and neither number here is carried from either side's own tree —
every figure in this note was measured by running the runner and the discovery
in a worktree of each of the three trees, the base `368e9e52`, clean
`origin/main` at `3e020cf4`, and the merged one.

**`1168` was already stale on `main` before this merge found it, and that is the
part worth keeping.** #982 added five cases to
`ec/tools/test_check_testdata_row_claims.py` and four to
`ec/tools/test_check_capture_claims.py` and did not re-derive the sentence, so
the base measures `1177`/`873` where the sentence read `1168` — measured by
running both commands in a clean worktree of that commit, so the `+9` is a run
and not a diff, which is the same rule this file states four paragraphs up and
the one that makes the steps above an arithmetic and not an assumption.

**The red set is unchanged, and it was re-checked here rather than carried** —
the single suite the notes above name, `test_check_cluster_citations`, 48
tests, the one failure, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements, each against `main-ec-145`. It fails identically on the base, on
the clean `origin/main` worktree and here, so neither #979 nor #985 caused it
and neither fixes it, and this merge adds no second red suite.

*(**Superseded at the `#979` × `#780` merge, beside this note rather than into
it: every figure here is true of the `#979` × `#985` tree and none of it is
this tree's.** The twenty-fourth note above re-derives the sentence for the tree
this file now sits in, and it reads `39 suite(s) run, 1221 tests` and `917` for
the discovery — `1211 + 10` and `907 + 10`, the ten being #780's, and
`python3 -m unittest discover -s ec/tools` measured rather than added. **The
`:203` clause two paragraphs below is superseded with them and left written
where it is**, per §4a-4d: the pin does not move at *this* note's merge, which is
true and measured — `203` is what `origin/main` at `abfe76e6` reads — and it does
move at the next one, for the reason the twenty-fourth note sets out. **The
`227` the branch's own tree read is not this tree's either**, because that
merge's two sides each moved the line again: `main` gained #973's correction
above the pin and this merge carries both sides' corrections, so the pin is at
**`:236`** here and `159 + 9 + 7 + 22 + 6 = :203` becomes
`159 + 9 + 7 + 22 + 6 + 33 = :236`. The `227` stays written here, true of the
tree it was measured on. The red-set paragraph is confirmed rather than
corrected: the single suite is still the only one in the tree this merge leaves
behind, re-checked by running the runner here — though the twenty-fifth note
below records the length of the merge during which a second suite was red, and
which.*

**This file's own `:203` pin does not move at this merge, and that is the
exception worth naming** — corrections have moved it before and this one does
not. "What it runs" above is corrected **in place within the lines it already
had**, so `159 + 9 + 7 + 22 + 6 = :203` still holds, the row in
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
is still registered to `:203` with no re-registration, and
`check_pin_table_rows.py` reads **106 rows, 106 records, 106 placed, all seven
classes 0** on this tree — checked by running the tool rather than by reading
this paragraph, and `:203` itself checked by reading the line rather than by
trusting the register, which still carries the repoint this row is registered
for. Both sides' edits land below it — #985's suite row at `~1076`, and this
note — which is the whole reason the pin holds, and this note sits below `:203`
for the same reason the twenty-first sits below the twentieth: a correction that
moves a registered pin to say a count is the merge-conflict hazard for a delta,
and the one thing this merge did not have to pay.*

*(Twenty-third merged-tree note, 2026-09-26, issues #979 × #973. **The suite
totals move again, and by exactly the step each side contributed.** On the merged
tree `bash tools/run-tests.sh` reads `40 suite(s) run, 1233 tests; one or more
FAILED`, measured here. The twenty-second note's `39`/`1211` is left visible
above per [`../docs/findings.md`](../docs/findings.md) §4a-4d, and it was true
of the tree it was measured on. The step is **one suite and twenty-two tests**,
and both halves are named rather than left to arithmetic: #973's new
`ec/tools/test_check_capture_names.py` is 19, and its three cases in
`ec/tools/test_check_testdata_row_claims.py` are the other three — so
`1211 + 19 + 3 = 1233`, and the suite count is `39 + 1 = 40`. **The suite count
now moves on the side the note above did not**, so the two notes name opposite
sides of their merges, and each was right about the tree it measured.

**The red set is still one suite, and it was re-checked rather than carried.**
`ec/tools/test_check_cluster_citations.py`, 48 tests, the same single failure on
the same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the
same two `0x0464`/`0x0465` disagreements against `main-ec-145`; it fails
identically on a clean `origin/main` worktree, so neither #979 nor #973 caused it
and neither fixes it, and this merge adds no second red suite.

**This file's own `:203` pin does not move here either, and the reason is the
one the note above gives.** The correction above is in place within the lines the
sentence already had, so `159 + 9 + 7 + 22 + 6 = :203` still holds — #973's edit
to this file is its one suite-table row at `~1126` and this note, and both land
below `:203`, the same way the twenty-second note sat below the twenty-first.
`check_pin_table_rows.py` still reads **106 rows, 106 records, 106 placed, all
seven classes 0**. The one figure in this file's neighbourhood that *did* move
is `test_check_pin_table_by_cited_file.py`'s own indexed/unpinned pin, re-set to
the measured **40 / 11 / 29**: #973's suite and #811's landed beside each other
rather than one replacing the other, and the comment beside that assert and
[`../docs/findings/pin-table-by-cited-file.md`](../docs/findings/pin-table-by-cited-file.md)
say why. The `11` does not move, because the pin count is still **106**.*

*(Twenty-fifth merged-tree note, 2026-09-26, issues #979 × #973 × #780. **The
sentence above is re-derived by running the runner rather than by adding the two
sides' figures up, and the arithmetic is written out only after that, as a
description of a number already measured rather than a way of arriving at one.**
On this merged tree `bash tools/run-tests.sh` reads `40 suite(s) run, 1243 tests;
one or more FAILED` and `python3 -m unittest discover -s ec/tools` reads `939`,
both measured here. The twenty-second note's `39`/`1211` and the twenty-third's
`40`/`1233` are left visible above per [`../docs/findings.md`](../docs/findings.md)
§4a-4d, and each was true of the tree it was measured on. **The one step is
#780's ten, and it is the same number from either side's tree:** `1233 + 10 =
1243` and `917 + 22 = 939` both land on what the merged run printed, with the
twenty-two being #973's `ec/tools/test_check_capture_names.py` at 19 and its
three cases in `ec/tools/test_check_testdata_row_claims.py`. The suite count is
the half that does **not** move, `40` on `main` and `40` here, because #780
adds cases to a suite it already indexed and no row to the table below — which
is also why `test_check_pin_table_by_cited_file.py`'s `40 / 11 / 29` needs no
correction here, unlike at the merge above.

**The red set is the single suite every note above names — but it was two for
the length of this merge, and the second is the one this note is here for.**
`ec/tools/test_check_cluster_citations.py` is the one all of them name: 48
tests, the single failure, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements against `main-ec-145`, confirmed here by running
it against a clean `origin/main` worktree, where it fails identically, so
neither #973 nor #780 caused it and neither fixes it, and this merge adds no
second red suite in the state the tree is left in. **The one it did add is
`ec/tools/test_check_pin_table_rows.py`**, 36 tests and three failures, and it
is the per-pin table's own register rather than a stale citation: the row for
`../../tools/README.md` registers the repoint list *inside* the eighth-thing
paragraph, and both sides' corrections to the "What it runs" sentence land
**above** it, so the line it names moved and the table did not move with it. The
tool read **1 `unplaced-row` and 1 `row-without-record`** with the stale line
still registered, and reads **106 rows, 106 records, 106 placed, all seven
classes 0** once the row is re-registered to `:236` — the arithmetic is what it
printed, not a guess at it, and it is the eighth-thing paragraph's argument
arriving as a red suite, which is the one thing in this note that is not a
figure the two sides' notes already carried.

**The `:203` pin moves again, and this is the biggest step it has taken.**
`main` reads `:203` and the branch's own tree read `:227`, and this tree reads
**`:236`** — so `159 + 9 + 7 + 22 + 6 = :203` becomes
`159 + 9 + 7 + 22 + 6 + 33 = :236`, the `+33` being the two sides' corrections
written side by side rather than one of them, which is the whole of this merge's
step on this line. Both superseded values stay written where they are.
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
carries the per-merge record of every one of those moves, and adds this one as
its own. **The `../findings.md` rows are unaffected**, for the reason every note
above gives: this merge's two edits to that file land at its `:9549` and at its
new §80, and every one of those four rows is above them, so no repoint is owed.
`check_pin_table_rows.py` reads **106 rows, 106 records, 106 placed, all
seven classes 0** with that row re-registered, and the two tools that read the
same table — `census_test_line_pins.py`'s own committed-tree census and
`check_pin_table_by_cited_file.py` — are green on this tree without a count
moving, because the row moved a line and not a record.*

*(Twenty-sixth merged-tree note, 2026-09-26, issue #978, the `#978` × `#979` ×
`#973` × `#780` merge. **Written below the twenty-fifth rather than beside it,
on the twenty-fourth's own rule** — "the note already committed on `main` keeps
the whole number and the branch's own gives way" — which that note states for
this file's numbers and `../docs/findings.md` §76's for this file's section
numbers, one merge after the other. The position is what does the work: the
twenty-fifth's own "the one it did add is …" and its `../findings.md` paragraph
are left uncorrected where they are, and neither has to be reopened to make room
for this one. That paragraph's conclusion — **the `../findings.md` rows are
unaffected** — is re-checked here rather than carried, and it holds for the same
reason it was given, extended to this merge's four edits: they land in
`docs/findings.md` at §41, §47, §76 and §79, every one of which is above the
four rows, and this merge's new section lands below them as §81 rather than at a
§80 of its own. No repoint is owed and none is made.

**The one figure the twenty-fifth's own step held still does move, and it is the
suite count.** The twenty-fifth reads `40` on `main` and `40` on its tree
"because #780 adds cases to a suite it already indexed and no row to the table
below"; that is still true of #780, and this merge is what moves the other half.
`ec/tools/test_measure_index_repair_visibility.py` landed beside #973's, and its
write-up cites the suite *by path* and never as
`test_measure_index_repair_visibility.py:NNN` — for #811's reason, since a line
pin would add a record and move the 106 / 79 / 58 in
`ec/tools/test_census_test_line_pins.py` and the 106-row table
`check_pin_table_rows.py` reconciles. So `suites()` indexes one more file, the
tail takes it, and the pinned count does not move: the measured triple is now
**41 / 11 / 30**, re-set in that suite's own comment with the **40 / 11 / 29**
left written above, true of every tree from #973's merge through the twenty-fifth
note's merge and false only of this one.

**Both counts in "What it runs" above are re-derived by running the runner on
this tree rather than by adding the two sides' figures up**, and the arithmetic
is written out only after that. The twenty-fifth's `40`/`1243` and `939` are
left visible above per [`../docs/findings.md`](../docs/findings.md) §4a-4d, each
true of the tree it was measured on. This tree reads `41 suite(s) run, 1264
tests; one or more FAILED` and `python3 -m unittest discover -s ec/tools` reads
`960`, both measured here. **The suite count is the half that moves**, `40`
becomes `41` and it moves by #978's one new file; **the test count moves with it
and by the same twenty-one**, `1243 + 21 = 1264` and `939 + 21 = 960`, so
"1243" and "939" are superseded by re-derivation rather than by the addition
either side could have made: #978 adds a suite of its own at 21 cases and adds
no case to any suite either side had already counted. **That is the whole step,
and it is a single-suite step for the third time in this run of notes** — #985's
`ec/tools/test_disasm8051_oracle.py`, #973's `ec/tools/test_check_capture_names.py`
and #978's `ec/tools/test_measure_index_repair_visibility.py` in that order, each
adding one file to a sentence whose count had been unmoved since `24460001`. The
twenty-first note's "no merge added a suite" clause stays superseded where it is,
true of every tree until `3e020cf4` and false of all three since.

**This file's own `:203` pin moves an eleventh time, and by +11, and this is the
first of the moves a reader could not have predicted from either side's tree.**
The twenty-fifth's correction is the largest step that row has had at `+33`; this
one is a fifth move of the same row and the smallest since the first two, because
only the "What it runs" parenthetical is above the pin and **eleven** of its lines
are this merge's own: the clause carrying `1243 + 21 = 1264` beside the `1233 +
10 = 1243` it supersedes, which exists only because the two merges' corrections
are written side by side rather than one replacing the other. So
`236 + 11 = :247` and `159 + 9 + 7 + 22 + 6 + 33 + 11 = :247` is the whole
arithmetic, **and the twenty-fifth's `:236` stays written above, true of the
`#979` × `#973` × `#780` tree it was measured on**, per §4a-4d. The row in
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)
is re-registered to `:247`, which adds this move as its own ninth record beside
the eight already there. The tool read **1 `unplaced-row` and 1
`row-without-record`** with `:236` still registered — checked by running it, not
predicted — and reads **106 rows, 106 records, 106 placed, all seven classes 0**
with `:247`. The census's own figures do not move, at **106 / 28 / 79 / 58** with
`74` resolving, `32` declined and the landing-shape split still `0/15/22/5/32`:
**`test_measure_index_repair_visibility.py:NNN` is declined rather than resolved**,
so the suite whose name this note spells with a line in it costs the table
nothing, which is the whole reason its write-up cites it by path.

**The red set is re-checked rather than carried, and this merge's is the
twenty-fifth's single suite with nothing added to it.**
`ec/tools/test_check_cluster_citations.py` — 48 tests, the one failure, on the
same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements against `main-ec-145` — is the one the notes
above name, and it fails identically on a clean `origin/main` worktree, so
neither #978 nor anything in the twenty-fifth's merge caused it. The suite the
twenty-fifth records as red for the length of that merge,
`ec/tools/test_check_pin_table_rows.py`, is green here, having been red only
while that merge's own re-registration was outstanding and **green again over a
row this merge moved a second time**: `check_pin_table_rows.py` reads **106 rows,
106 records, 106 placed, all seven classes 0**, and that is what this merge's four
`docs/findings.md` retirements and its new §81 cost it — nothing, because each
was written in place within the lines the sentence already had. Named by suite
and by count rather than by line here, for the reason the notes above give.*

*(Twenty-seventh merged-tree note, 2026-09-26, issue #978, the same `#978` ×
`#979` × `#973` × `#780` merge as the twenty-sixth. **Written below the
twenty-sixth rather than beside it, on the twenty-fourth's own rule**, and for
the same reason the twenty-sixth gives for sitting below the twenty-fifth: the
position is what does the work, and the twenty-sixth does not have to be reopened
to make room for this one. Two of its sentences are false on the tree it shipped
and both stay written above, each true of no tree rather than of the tree it was
measured on, per [`../docs/findings.md`](../docs/findings.md) §4a-4d.*

**A repoint was owed, four of them, and the reason the twenty-sixth gives for
saying none was is false on its own terms.** That reason is "they land in
`docs/findings.md` at §41, §47, §76 and §79, every one of which is above the four
rows". **What moves a pin is whether an edit adds lines above it, not which
section the edit is in**, and two of the four are not above the rows: §76's edit
is at [`../docs/findings.md`](../docs/findings.md):10063 and §79's at `:10426`,
both below the last of the four. The twenty-sixth's own measurement is what
settles it — the four `docs/findings.md` retirements it says cost the checker
"nothing, because each was written in place within the lines the sentence already
had", which is true of §47's alone. §41's retirement runs `3` lines to `5`,
§76's `6` to `8` and §79's `3` to `6`, and §81 adds `111` below all of it.

**Only §41's growth is above the four `../findings.md` rows, and it is `+2`.**
`docs/findings.md:7052-7056` is where "…so this check would have been green
through both. Not claimed: that it would have caught them." gives way to the
measurement beside it, below the two rows at `:4206` and `:4208` and above the
other four. So `7191 + 2 = :7193`, `7404 + 2 = :7406`, `7465 + 2 = :7467` and
`9207 + 2 = :9209`. §47's edit, at `:7286`, sits between `:7191` and the other
three and is `5` lines for `5`, so it moves nothing despite being above three of
them — the case that separates *the edit is above the pin* from *the edit changed
the line count above the pin*. The four superseded values stay written in
[`../docs/findings/test-line-pin-census.md`](../docs/findings/test-line-pin-census.md)'s
tenth note beside the four new ones, per §4a-4d, and its `still unaffected`
clause in this file's twenty-sixth is corrected there for the same reason.

**`ec/tools/test_check_pin_table_rows.py` was not green on the tree the
twenty-sixth shipped, and this note is what made it so rather than a prediction
that it would be.** The twenty-sixth records it green and records
`check_pin_table_rows.py` reading "**106 rows, 106 records, 106 placed, all seven
classes 0**". On the tree as committed it read **`FAILED (failures=3)`**, and the
checker read **102 placed** with **4 `unplaced-row`** and **4
`row-without-record`** — checked by running both here, against the same
`origin/main` worktree the twenty-sixth names for
`test_check_cluster_citations.py`, where the suite is `OK`. **The re-registration
above is the whole of the difference**: with it, the suite is `OK` at 36 cases and
`check_pin_table_rows.py` reads 106 rows, 106 records, 106 placed, all seven
classes 0, and the census's own figures are unmoved at **106 / 28 / 79 / 58** with
`74` resolving, `32` declined and the landing-shape split still `0/15/22/5/32` —
**re-derived by running `census_test_line_pins.py` on this tree rather than
carried**, which is the check the re-registration is run for, since a line moving
is not a record moving.

**The standing red set named above was wrong for this merge, and it is the
twenty-sixth's clause that makes it wrong rather than anything in the tree.** The
red set is the single suite `ec/tools/test_check_cluster_citations.py`, and it
fails identically on a clean `origin/main` worktree; `test_check_pin_table_rows.py`
joined it for the length of this merge and left it when the four rows were
re-registered. Named by suite and by count rather than by line here, for the
reason the notes above give.*

*(Twenty-eighth merged-tree note, 2026-09-26, issue #845. **The suite totals
move on this branch for the fourth single-suite step in a row**, and the
figures are this tree's, re-derived from a `bash tools/run-tests.sh` on it:
**forty-two suites and 1270 tests**, the new one being
`ec/tools/test_trace_xdata_refs.py` at 6 — `1264 + 6 = 1270`, and `960 + 6 =
966` is the same six under `python3 -m unittest discover -s ec/tools` over
thirty suites. The last line reads `42 suite(s) run, 1270 tests; one or more
FAILED` with the runner exiting 1, and the red one is **still only
`ec/tools/test_check_cluster_citations.py`**, on the same `:220` of the same
#822 file, which reproduces on a clean `origin/main` and is #830's. The
twenty-seventh's figures are left reading as the record of that tree, and the
`41` and `1264` this sentence carried until now stay in the parenthetical above
beside them, per [`../docs/findings.md`](../docs/findings.md) §4a-4d.)*

**A second pin in the tree moved with the suite, and it is the one a reader of
this file is most likely to be tracking.** #845 adds a `test_*.py` to
`ec/tools/`, and `suites()` in `ec/tools/census_test_line_pins.py` indexes
every one of them, so `ec/tools/test_check_pin_table_by_cited_file.py`'s
committed index figures go **41 / 11 / 30 → 42 / 11 / 31** — the tail takes the
new suite, the eleven named by a pin do not move, and the pin count stays
**106** because #845's write-up names the six cases by class and method and the
suite *by path*, never as `test_trace_xdata_refs.py:NNN`, for exactly the reason
#811's and #973's and #978's notes above give. That suite's own asserts are
re-set to the measured value rather than argued, with the superseded triple left
written above them in the same shape the sixth through tenth steps left theirs.*

**And the reason this note is longer than a re-derivation is that this branch
measured the totals line failing at its own job.** Deleting either of the two
guards `walk_why()` ends on, in a copy of the tree, and re-running this runner
over `ec/tools`, moves the **red set** — from one suite to two with the bounds
guard gone, and to three with the `d[i] == MOV_DPTR` guard gone — and moves the
**totals line by nothing at all**. All three runs print the byte-identical
`29 suite(s) run, 960 tests; one or more FAILED`, because the runner counts
tests *run* and a suite that goes red, or an `IndexError` that escapes a case
before its assertion runs, has not changed how much of it ran. That is the
paragraph above's standing ("the totals are not a pass and never were") at its
sharpest in this tree, and it is recorded here rather than only in
`../docs/findings/walk-bounds-guard-pinned.md` because this is the file a
reader watches the number in. **A reader watching this sentence to see whether
a tree is green is watching the wrong thing**; the red set is the verdict, and
[`../docs/findings/runner-red-suite-set.md`](../docs/findings/runner-red-suite-set.md)
is the page that argues why a total is a property of a merge rather than of any
suite.*

| suite | what it stands in for |
|---|---|
| `ec/tools/test_bank1_e582_framing.py` | The byte facts behind the issue #680 reading that the `bank1,0xE582` entry is reached through 0xE580 and the census row at 0x9F03 is a displacement byte: the push/lcall/pop save-restore pair across the 0xE57E cut, `converges_from` on both halves of each site, and the `80 02` at 0x9F02 read as a `sjmp` whose displacement's landing address is the committed `9F04.asm` first instruction — asserted against the image rather than by re-running the scan that wrote the census, so a regenerated table that disagreed would fail rather than pass on a stale pair, plus that both annotation comments still carry the clause their `CORRECTION` replaces, that no entry is seeded at 0xE580, and that the phantom census row is deliberately left in place |
| `ec/tools/test_census_test_line_pins.py` | `ec/tools/census_test_line_pins.py`'s population and its **standing as a census rather than a check**, which is the invariant the most: a run whose every pin is broken still exits 0, and a run that located nothing reports that and exits non-zero, one case each, so "found nothing" and "found nothing wrong" cannot read alike from the exit code. Around it, one case per way a pin is read wrongly — a `windows/tools/` prefix truncated into `tools/`, a `../tools/…` path written relative to the citing file, a bare module name two files could answer to (ambiguous, never guessed), a span that outruns its file, a span that opens on the blank line above what it is about (a real answer here, not a miss) — a fenced transcript declined and counted while the same pin in live prose beside it is read, and the census's own write-up excluded from its own population so the class's size is not a function of the report about it; and the committed tree's reconciled 106 / 79 / 58, per-verdict and per-shape, held from both sides — `71` after #885's two citations of the `> 300` floor's assertion merged under #888's, `45` / `41` because #890's +25 repoint left the tree carrying both that `:392` spelling and the `:417` one beside it, then #771's write-up alone took occurrences, files, spellings and targets to 105 / 27 / 78 / 58, so every count but the verdict and shape splits' total has moved at some merge, and #778's write-up took them the last step to 106 / 28 / 79 / 58 by adding one pin and repointing 33 others; the `57` that `58` is one more than is #930's repoint putting the two `:563` by-name rows back onto `:588`, which the checklist already named by path, so `:563` lost the last name it had — `out-of-range`, `unresolved-path` and `ambiguous-path` are 0 there and that is asserted as the measurement it is, not left to a prose figure |
| `ec/tools/test_check_doc_figure_pins.py` | `ec/tools/check_doc_figure_pins.py`'s four verdicts over a page's own tables, measured against the real `ec/tools/` rather than a stubbed tree — so the figures the checklist lists are asserted by value and a tree that changes under any of them fails here instead of quietly changing what the page claims — with the line between what it reads and what it declines, one case per shape: a thousands comma, two figures in one cell, a count with a noun after it, a hex address (stripped) beside the run that is not, a `0.5` threshold (not a figure), a `set(off) == set(on)` relation (declined, never failing), a `§2b` or `#849` reference (stripped), and a figure in a second cell (not read at all, so a prose cell's `1,169 addresses` is not a count); the four `file:line` rules no gate in this tree had, since `check_doc_links` only resolves relative `.md` links; and both directions demonstrated rather than asserted — a pinned figure marked unheld is reported, and a table that stops declaring a `verdict` column is reported too, because that second one would otherwise return the page to its pre-#849 state and report a clean run |
| `ec/tools/test_check_pin_table_by_cited_file.py` | `ec/tools/check_pin_table_by_cited_file.py`'s fifth axis on issue #887's pin census — **which test file a pin names, and which indexed suite none does** — with the standing that it is a breakdown rather than a check held from the output side, a run whose every pin is wrong still exits 0 and its report contains neither `carries` nor `does not carry`. Around it, one case per way a record can be charged to the wrong file: two spellings of one pin landing in one bucket, a line past the end charged to its file but not to `resolves`, a `grep -rn` transcript's `./` prefix normalised away as a *spelling* and not repaired as a path, a bare module name answered by the census's own index, two files of one base name refused rather than guessed, and a path nowhere in the tree landing in a named `unresolved-path` bucket instead of the file that shares its base name; each column reconciled back to `census()`'s own `RESOLVES` and `DECLINED` on a fixture that exercises every column and both buckets, so the breakdown cannot become a second set of numbers; the committed table held as a `{path: (resolves, declined)}` dict and the 44-of-106 / 80-of-106 concentration derived from it, so a merge that adds a pin to a fifth file moves a figure rather than reweighting the breakdown; the indexed/unpinned tail's length held as `len(suites())` minus the distinct resolved paths rather than frozen by name, since it moves every time a suite lands — including this one, which the suite asserts is in it |
| `ec/tools/test_check_capture_names.py` | `ec/tools/check_capture_names.py`'s two refusals over one listing of the capture root — a name carrying no `<YYYY-MM-DD>-` prefix, and a subdirectory in the root — which are the two properties nothing on the tree read and `captures_for()`'s `<date>-*` glob is a glob only while they hold, and its **standing as a census with a refusal in it**: read by hand the run prints the census and the refusals and exits 0, and only `--check` makes a refusal the verdict. Both fired on a scratch root rather than on the committed tree, which is conformant, each reported in its own vocabulary so "2 problems" cannot leave a reader guessing which premise stopped holding, and each message pinned to naming *what it costs* — a glob that cannot reach the file, or a glob that reaches a directory `carried_by()` skips. **The two costs demonstrated, not asserted**: an unprefixed capture is one `captures_for()` reports as a glob coming back empty, which this tool's own vocabulary calls `unresolved`, so the run stays green while checking strictly less; a subdirectory is one `glob.glob()` returns and the reader skips, so the sentence's literal comes back `missing` and sends a reader to fix the index's prose when the thing to fix is a directory. The declined alternative pinned as a refusal rather than left in prose (`power-mode-…-2026-09-23.csv` is out of reach, because the glob is `<date>-*`), a lookalike year accepted because the prefix is a shape and not a calendar, and `PREFIX` and `captures_for()`'s glob asserted to agree in both directions so the two readers of one rule cannot drift. The committed root's two tripwires assert **emptiness, not a figure** — no count of captures appears in either, so the corpus grows freely while a capture that loses its date prefix turns them red — and a root that cannot be listed is a broken census rather than three empty lists, the §14b defect `run-tests.sh` guards at the suite level |
| `ec/tools/test_check_capture_claims.py` | `ec/tools/check_capture_claims.py`'s address-presence and row-count rules against the committed `evidence/ec-watch/*.csv` captures, and the line between what it checks and what it deliberately skips, plus the file-granularity self-report #975 added — a file read in full that names no claim is named in `--verbose` and counted on a line of its own, and the two `--verbose` line shapes are asserted to partition the file total the summary prints rather than asserted against a figure |
| `ec/tools/test_check_pin_table_rows.py` | `ec/tools/check_pin_table_rows.py`'s reconciliation of the 105-row per-pin table against `census_test_line_pins.py`'s own run, and **its standing as a check on the four mechanical columns and not on the fifth**: a tree where every verdict cell is wrong still exits 0, and so does one where the verdict cells are empty, so the cell is demonstrably never read — the write-up's `*Why no checker*` declines a checker that renders verdicts and this is not it. One case per way it can fail (a citing line that moved, a shape that changed under a row, a record with no row, a row with no record, a run that placed nothing) and one per way a loosened version would slip through: both citing-cell spellings and the `†` marker kept in the message, the table's `beside` abbreviation honoured against the census's own constant, an unknown read cell reported rather than passed, a duplicate key reported rather than resolved to the first, an unparsed row reported and a two-header write-up refused, and a missing header or an unreadable file reported rather than passing vacuously — plus the white-box `path-differs` case, because that class is an identity on a placed row (the match key pins both inputs its re-derivation has) and a check only ever exercised by a tree that cannot occur is a check nothing has tested; the committed table held at 106 rows against 106 records, every class 0, and the read and shape cells held to the census's own vocabulary and split. **Not in any gate**: the prepared patch is `docs/ci/agent-gates-pin-table-rows.patch` |
| `ec/tools/test_check_citation_lines.py` | `ec/tools/check_citation_lines.py`'s three rules over the line numbers the prose repeats out of the generated CSVs — the `xdata-086x-dispatch.md` site table and the `HAND_CHECKED["0x0860"]` comment against `xdata-0860-census-sites.csv`, and every `xdata-registers.csv`/`xdata-clusters.csv` line pointer in the two files its `ROW_SCOPE` names, each held to the row for the **address or cluster id** rather than to a table of expected line numbers, because a rank is not an identity — one case per way a citation can be wrong, and the cases a loosened test would let through: a table whose header lost the column, reported as not located rather than passing vacuously; a `—` cell over a CSV row that does cite; the merged `0x25CE4`/`0x25CFC` row read as one row and two sites; the `:49` shorthand bound to the file it follows and a bare list bound to the file named ahead of it; a header line and a line past EOF diagnosed as such; a rule that located nothing reporting that rather than returning clean; the two supersession shapes **skipped**, with the skip counted and `--verbose` naming it, and a live paragraph that merely mentions a correction still checked; the deliberate asymmetry between the per-site and the union rule, pinned from both sides; and that the committed prose and the committed census currently agree |
| `ec/tools/test_check_cluster_citations.py` | `ec/tools/check_cluster_citations.py`'s two rules against `ec/annotations/xdata-clusters.csv` — `main-ec-NNN`/`cluster_key`/`cluster_name` citations held to their membership, and a census row's hand-typed counts held to the CSV, pinned apart as well as together — and the line between what it checks and what it deliberately skips, so that a denial, singleton wording, a mention without a membership claim, a code address and a split written as a list are each skipped rather than checked and each rule that makes it conservative gets a case saying so, because a pointer-checker's failure mode is silence, plus that the tree's committed prose currently agrees with the committed census beside it |
| `ec/tools/test_check_site_census.py` | `ec/tools/check_site_census.py`'s vocabulary table, one case per row asserting the checker *rejects* that row's disagreement, plus the unsupported-claim, stale-citation, unjoined-pair and totals-drift clauses, `--check`'s exit code, and that the committed sweep, correspondence and census currently agree |
| `ec/tools/test_check_testdata_index.py` | `ec/tools/check_testdata_index.py`'s two directions between `ec/tools/testdata/README.md` and the tree under it, each rule that makes it strict and each that makes it conservative getting a case: a directory no index names is a gap, a self-indexed one is not (on a directory name the tool has never seen, so the clause is structural and not an exemption list), the trailing slash that stops `0751-isolation-run/` passing on a sibling's row, the `...-suffix.csv` and `*-glob` shorthands resolved by glob rather than by splicing, and a token whose shape matches no rule landing in `unresolved` without failing the run — plus the rule that the run's three tallies are read out of what it printed and are not a floor on the tree's size, a rule of its own with a case per clause: a tree with more of them than today and one with fewer are both green, and an empty tree, a rowless index beside a tree that has one, and one token per row are each refused on the clause that refused them |
| `ec/tools/test_check_testdata_row_claims.py` | `ec/tools/check_testdata_row_claims.py`'s rule over the **third** column of `ec/tools/testdata/README.md` — an address a row attributes to its fixture has to occur in a file that row names, across the whole set the first column resolves to rather than per file, so `0x075B` living in one of `0751-isolation-run-staged/`'s three CSVs is a claim the row makes and not a miss — with each of the five shapes and the dated-capture variant pinned as a case from both sides: the page-boundary range, the `capture`/`page` word, the two-token watched-set span, the denial in both its spellings, the `ecrw.py dump` argument, the firmware code address filtered against `ghidra-functions.csv` minus `xdata-registers.csv`, and a bare date in prose resolved against `evidence/ec-watch/<date>-*` with its literals held to those files instead of passed over — a backticked date, by its spelling, still being a file the comparison is drawn from; and the four-hex-digit width and the backticked-only predicate besides — then all nine rules dropped in turn, eight asserted to make the committed tree check *more* and the ninth, the dated-capture resolution, to make it check *fewer*, against the run as shipped rather than against a figure, so no added fixture row breaks any of them; and, from #975, a claim about a capture being held to the `addr` column of the `.csv` members of the file set its date resolved to — a capture whose `#` header names an address and whose rows do not is a `missing`, a date of `.txt` dumps alone reporting that it has no column to read, and the rule pinned by reverting the claim to the textual read and watching that first case go green |
| `ec/tools/test_measure_index_repair_visibility.py` | `ec/tools/measure_index_repair_visibility.py`'s answer to a question the corpus carried unanswered for five issues — **what `check_testdata_row_claims.py` and `check_testdata_index.py` do over a hand-repair's pre-repair tree**, measured rather than assumed, and the three ways that number could be wrong quietly: the content-based `repair_rows()` detector that finds a third-column edit wherever it is and **refuses two images of different row counts rather than aligning them** (a pair with no such edit is "not found by this method", a different answer from a count of zero); the **post-repair control** that makes a pre-repair `missing` mean anything, and the one check the tool can fail on (exit 1); and the **runnability flag** that reports a row whose fixture the measured revision does not carry as *not runnable, because …* rather than folding its claims into a count. `git_lines()`/`resolve_revision()` return **None plus a reason** on failure, copied with attribution from `verify_reassembly.py`, so a git that failed cannot read as a tree with nothing in it. Scratch repositories built by the suite itself give the shape of the committed answer at a size where the answer is not in doubt: red before a repair, green after one, which is what makes the committed number falsifiable |
| `ec/tools/test_citation_callers.py` | `ec/tools/citation_callers.py`'s two predicates on the citing listing: all-`0xFF` detection including the `-`-pad spelling every 1-byte instruction uses, the `ret` that is a five-token line a fixed-width reader never sees, a two-byte instruction that is not a fill run, a listing with no instruction line at all asserted **not** fill, header lines that must not parse as code, and transfer-target extraction across all four forms — plus that `call_graph.parse_listing` and `citation_callers.transfers` agree token for token, so the two tools cannot drift on the listing grammar |
| `ec/tools/test_citation_frames.py` | `ec/tools/citation_frames.py`'s code/data frame test, on sentences taken from the committed annotations and truncated to the clause under test: the two that a whole-sentence rule gets backwards (`calls to 0x110A, 0x158E, …` is a code list, `the 0x07D0 sites` is a byte count), the `FILLER_BUDGET` limit stated as a rejection case, and the reason and population reporting |
| `ec/tools/test_citation_gap_scan.py` | `ec/tools/citation_gap_scan.py`'s window arithmetic and three verdicts, on the real committed bytes: the listing end read from the byte column so a bare `ret` has a length, the next entry taken from the citing row's **own** scope, the zero-byte gap whose window is the neighbour's head, and the 3 bytes of slack that let a straddling `lcall` complete where a window stopping at the boundary decodes nothing — plus the overrun guard (~~`disasm8051.decode()` still raises, which is why the tool walks the committed tables itself~~ **Corrected 2026-09-25, issue #679** — `decode()` stops rather than raising at the end of its buffer now, and `walk()` stays because it reports a window holding less than was asked for through `truncated` and carries the per-instruction map-unassigned flag), the `not-code` byte criterion against the looser `db` form, the scope-dependent boundary, and `--check` rejecting a CRLF table whose rows parse equal |
| `ec/tools/test_disasm8051.py` | `ec/tools/disasm8051.py`'s bounds contract, on hand-built windows: the end-of-buffer check running before the index it guards, so a caller over-asking a one-byte `ret` window for four instructions gets that `ret` and a stop rather than an `IndexError`; `start == len(d)` and the empty buffer decoding to nothing; a `stop_at_flow` walk reaching the end; and the neighbouring, older guard it must not have been folded into — a 2-of-3-byte `lcall` yielding nothing, and the `ret` before it kept while the `lcall` that does not fit is not decoded |
| `ec/tools/test_disasm8051_oracle.py` | the two hand transcriptions `disasm8051.py --self-test` is checked against, re-read from the committed `.md` files rather than trusted from the literal table — the parses on the real files (24 rows out of `charge-profile-flow.md` in the decoder's own dialect, the four `REL_SITES` addresses and the `0x8020`..`0x805e` escape block out of `bank-call-audit.md` §8 in r2's, with its box-drawing glyphs and its `$ ` prompts, and the two dialects' texts differing at the same address), and then **the mutations, which are the reason the file exists**: an operand re-transcribed, a row added inside a window, a row removed, and the same removal wearing an `...` elision, a §8 listing line deleted, a §8 byte column edited and a §8 target edited — each a named failure at the address that changed rather than a cascade one address to the right, which is why the windows compare by address and not by position; the three vacuity refusals (a window covering no parsed row, a file with no fence, a §8 with no heading) plus an unreadable file as a *reported problem* rather than a traceback, and one unreadable file not taking the other's verdict down; cwd-independence in process and through a `subprocess` of the prepared gate's own invocation, with the lazy import held by reading `disasm8051.py` up to `def self_test(`; and **the transcript contract** — the summary line and the four `REL_SITES` lines asserted byte for byte, because five committed transcripts quote them |
| `ec/tools/test_export_ownership.py` | `ec/tools/export_ownership.py`'s containment rule — the smaller body's statements at least `THRESHOLD` of the way into the larger, classes as connected components, one owner per class as the largest body with a tie to the lowest address — pinned one case per named rule, each asserting the direction a loosened rule would get backwards, so a class cannot quietly merge two routines that share a `return` or split one exported 42 ways, plus the refusals that stop `--check` and `--self-test` from answering for a derivation nobody committed, and the `--map` round trip through a scratch path |
| `ec/tools/test_grade_0751_isolation.py` | `ec/tools/grade_0751_isolation.py`, the §4 grader of the `0x0751` capture procedure, against the committed `testdata/` fixtures |
| `ec/tools/test_grade_gpu_door.py` | `ec/tools/grade_gpu_door.py`, the §5 grader of the `0x07D0` door capture: the ordering and its ms delta, both one-block shapes, a quiet capture, a byte that moved and came back, marks left unmerged, and the ten-column mapping |
| `ec/tools/test_grade_timer_sweep.py` | `ec/tools/grade_timer_sweep.py`, the grader of the `0x8001` counter-sweep capture: its before/after-return lists re-read from the firmware image, the `0x06D6` period and the 10x rate ratio on a constructed clean capture, a flat capture reported as held rather than absent, a second writer flagged, an unresolved step warned, and a suspend gap left out of the figures and counted mod 10 |
| `ec/tools/test_group_functions.py` | `ec/tools/group_functions.py`'s block assignment, and at its centre the refusal that makes the tool safe: nothing in an `lcall`/`ljmp` operand names a bank, so `bank0->bank1` and `bank0->bank0` are the same three bytes, and the decisive case is a same-region call and a cross-region call that are byte-identical and differ only in which bank the target happens to exist in — a tool that merged across one anyway would answer with a smaller, tidier, wrong number and nothing in its own output would say so — plus the `group_basis` vocabulary (a seed from `type`/vector/module outranking a cluster, an off-list basis refused), the cross-bank group refusal, and the committed group files passing their own `--check` |
| `ec/tools/test_inc_dptr_sites.py` | `ec/tools/inc_dptr_sites.py`'s half-split of a pair accessor: the 107 addresses `xdata_register_map.py`'s pair pass reaches only as the `inc DPTR` half, their 73 / 34 cut and the 34's 7 entered / 27 not, the 73's own 71 with no `MOV DPTR` site in any image against 2 in the pd image only (a site in the pd image is another program's byte at the same address number, so it is not a second site), and §4.7's ten named addresses as the head of the 73 with `0x0364` as the eleventh §4.7 does not name — every figure re-derived by the tool's own `build()` against the committed firmware and the committed decompiled tree rather than read off `xdata-inc-dptr-only.csv`, so a CSV edited to match a stale claim fails rather than satisfying the suite, and the committed table held against a fresh generation as the one direction a hand-edited file can fail; the census's *shape* rather than its figures (`census_refs` closing on the bucket columns, the 73 `pair-literal`-only and main-EC-only); the ten confirmed by a second entry point beside the tool's own table, a byte scan of the image and a real `main()` run; `0x0420` as the counter-example keeping the rule off the spelling of a literal first argument, the same hex reaching `add_full_product_to_dptr` whose committed `.asm` is `mul AB / add A,DPL / addc A,DPH / ret` with no `movx` — so the address space is a property of the callee's body — beside the positive half, that every accessor the table names still dereferences XDATA; and the refusal that keeps a tool keyed to three committed CSVs harmless, from both sides: `open` replaced by a tripwire raising on any write mode for every mode, an unidentified pd marker refused rather than reported as a 73 / 0 that would read as a finding, and the module's own AST walked for a write vector no case runs |
| `ec/tools/test_trace_xdata_refs.py` | `ec/tools/trace_xdata_refs.py`'s `walk()`/`walk_why()` bounds contract, on hand-built `common`-region buffers and reading no firmware image — the half `ec/tools/test_walk_budget_census.py` does not hold, which is *which instructions come back* where that suite holds *which guard fired*, so a walk that decoded wrongly for the right reason fails this one and passes that one, and the other way round. What it asserts: an over-ask yields what fitted, by offset and raw bytes rather than by mnemonic text, because the mnemonic table is `disasm8051.py`'s subject and `test_disasm8051.py`'s and a case coupled to its wording would go red for a change that is not a bounds defect; the same walk says the buffer ended it, kept as its own case so "it stopped" is attributable to the bounds check rather than to the budget or a flow opcode; `d[i] == MOV_DPTR` still ends a walk **and** the same fixture with the reload replaced by filler runs on to `budget_end(8)`, so neither line of the guard can go; and the loop's own bound is `max_insns` and not `len(d)`, one case and two fixtures holding the same bytes at 0x40 and at 7 bytes. Both call sites are then driven over a 7-byte fixture — `csv_table()`, whose `window` cell is asserted against what `walk_why()` returns rather than against a spelling and whose `terminator` cell can only come from a caller that has the reason, and `main()` as a subprocess over a file in a `tempfile.TemporaryDirectory()`, pinning exit 0, the printed window, the `window ended: end of buffer` line, and the stderr note a buffer with no PD marker produces, which is what keeps `common` in that output from reading as a claim about the real dump. Deleting either guard turns this suite red; the write-up is [`../docs/findings/walk-bounds-guard-pinned.md`](../docs/findings/walk-bounds-guard-pinned.md) |
| `ec/tools/test_walk_branch_arms.py` | `ec/tools/walk_branch_arms.py`'s direction classification, bounds, refusals, and negative-result wording |
| `ec/tools/test_walk_budget_census.py` | `ec/tools/walk_budget_census.py` and the `trace_xdata_refs.walk_why()` it reports on: one hand-built byte fixture per terminator guard, each asserting the guard that fired *and* the one that did not, so a loop that swapped two guards cannot pass; that `walk()` still returns a bare list of triples and `classify()` still re-derives every committed table's `access` cell; that the terminator vocabulary is closed, so a sixth way to stop is refused rather than rendered into a cell `--check` would go green on; that the class A/B verdict reports `undecided` rather than picking a side when the `--extend` budget is too small to reach the access in question, which the committed data never exercises; the census `--check`'s exit code on the committed CSV, on a doctored one, and its refusal of a budget that CSV does not record; and the re-cut's own load-bearing claim, as a count over the pinned pre-change commit `e198fd9`'s copy of each table -- no `access` cell and no `window` cell changed, with the one pre-existing `disasm8051.py` mnemonic drift at `xdata-0400-045f-sites.csv` `0x11F16` named rather than left to be noticed, which is what the fifteen-address `0x086x` sweep reproducing its table byte for byte is the regression test for. The ref is a SHA rather than `HEAD` or `origin/main` because both of those hold the re-cut once this lands, and a baseline that already contains the change compares each table with itself and pins nothing; an unreadable baseline fails the test instead of skipping it, for the same reason |
| `ec/tools/test_xdata_carry_notice.py` | which census a carry line is a claim about: `census_shape()` naming the flags that put a run's cluster ids off the committed pair the names file is anchored to — and refusing to name `--no-writer-axis`, which clusters as a default run does — `carry_advice()`'s committed clause pinned to the exact string the committed transcripts carry, and the two shapes' `print_carry` stderr asserted to differ in the overlap tails and nowhere else, so the `names:` tally and the tie line stay the mode-independent facts they are. In-process on a synthetic report: no census run, because the property is a function of the flags and not of the firmware |
| `ec/tools/test_xdata_cluster_names.py` | `ec/tools/xdata_register_map.py`'s cluster identity: the `cluster_key` content hash, the `cluster_name` carry across a regeneration, `--map`, and the settling test that a cited cluster still resolves to the membership the prose describes |
| `ec/tools/test_xdata_register_map.py` | the `--no-eq-guard` and `--export-ownership` refusals of the same tool: the three refused combinations per flag plus one per half of the scratch-output `or`, each with every mode entry point replaced by a recorder — all nine of them, read out of `main()`'s own AST by `dispatch_names` as every bare-name call in `main()` that is not another call's argument, with a mode dispatched through an attribute asserted against rather than collected, so a tenth fails here rather than going unmocked — so a guard that moved below the dispatch fails the test instead of writing a census the committed CSVs do not match over them, and the two accepted runs, which write only into their `tempfile` |
| `windows/tools/test_manual_fan_ctrl_probe.py` | the fan-mode probe's two-arm byte script, its read-safety guard under `--level-block` and `--watch-page`, the three mark rows its `--csv` capture lands, that capture read back through the real `ec/tools/grade_0751_isolation.py` reader and then through its block walk as a whole grader run — one block, `intact`, three roles, every window printed, exit 0 — the mark set against the grader's own §6 forms, a crashed run's `#` row, `--watch-page`: that the flag is opt-in, that it is §3's three ranges rather than 448 addresses of the tool's own choosing, that it substitutes for `WATCH` instead of adding to it, that it writes nothing but `0x0751`, and that its capture still grades and keeps its ungraded rows on the grader's `other addresses that moved` line — and `--block`: the seven runs the watch set decomposes into, the page arm's three whole runs, that the block path reports exactly what the byte path does, that only the mode byte is left to a point read, and the 56/61 and 112/117 figures the banner and the self-test quote |
| `windows/tools/test_ec_watch.py` | the mark-CSV sweep and the mark landing between two change rows, that a blank press at the mark prompt records no row and takes no mark number while a padded label is still taken, plus `--block`: that it sweeps through `readmany`, that the flag is off by default, that the banner says the path is unverified, and that a range covering the fan-tach page is warned about rather than refused |
| `windows/tools/test_ecrw.py` | the real `ecrw.py`, on a fake `ctypes.WinDLL` standing in for kernel32: the `MMRD` IOCTL's little-endian physical address, the aligned-block decomposition of a range, the probe watch set's 56-IOCTL cost against the 52 a `206/4` suggests, the `--watch-page` set's 112 IOCTLs and its 448 bytes with no padding, all four watch sets cleared of the fan-tach page, the window's last in-window dword, an unaligned start's discarded lead, `dump --block` printing what the byte path prints, and the per-byte path's buffer byte for byte as it always was |
| `windows/tools/test_ec_validate.py` | the `ec_validate.py` `0x0436` capacity arm's exact-copy scoring, full-capacity bound, CSV, and `0x0400-0x045F` page assertion |
| `windows/tools/test_system_id_probe.py` | the `0x0456` probe's `store_scaled_quotient_0449` arithmetic, its branch labels, its address guard, and that it has no write path |
| `windows/tools/test_charge_target_test.py` | the charge-target tool's three refusals, the restore in its `finally`, and its CSV column set |
| `windows/tools/test_gpu_block_watch.py` | the GPU-block watcher's citation table against `evidence/acpi/dsdt.dsl` and `ec/annotations/registers.yaml`, the door procedure's own copy of that table against the tool, that copy's cross-reference column for the four census-covered rows against `ec/annotations/ec-07c4-07d5-sites.csv` and its `.md`, the door grader's third copy of the window bounds and DSDT names against the tool, its watch set, and its mark reaching the CSV |
| `windows/tools/test_ctgp_dben_probe.py` | the `0x07C4` `DBEN` probe's refusals, its two-arm byte script read back from a run that started with the value bit clear, the restore in its `finally`, its CSV column set, and the bit arithmetic pinned to `evidence/acpi/dsdt.dsl` and the `0x96AD`/`0x94C0`/`0x83FF` rows of `ec/annotations/ghidra-functions.csv` |
| `linux/lightbar/test_probe_6005.py` | the lightbar probe's ioctl encoding, dry run, and off-after-failure |
| `tools/test_doc_patch_refs.py` | `tools/check_doc_patch_refs.py`'s two directions between the prose and `docs/ci/`, and the line between what it reads and what it declines: a name in the prose resolves to a file, a file on disk is named somewhere, and the parse cases that keep a loosened pattern from passing vacuously — both backtick spellings (the bare one is 31 of this tree's 70 references and is how a table row's first cell has to be written), a glob-shaped span and the `.yml` sibling refused by shape rather than by a list, a link resolved to its last path component, a URL refused, and one line in both spellings counted as two; the four refusals on trees small enough to read the whole finding list, each reported by name *and* by citing file; the live direction, which is the half that broke in the suite below; one case per historical name **in both directions** — still absent from `docs/ci/`, still cited by markdown — with the two ways an exemption rots demonstrated rather than asserted on a `tempfile` copy; the rename case, on a copy of the committed tree rather than a fixture, because "red for *every* stale reference" is a claim about this tree's references — every one of the renamed patch's references, list-compared against the tree's own, with the uncited rename reported separately; and that a discovery which found nothing exits non-zero rather than reading as a clean tree. No count is asserted, for the reason the suite below's docstring gives |
| `tools/test_agent_gates_patches.py` | the prepared `docs/ci/agent-gates-*.patch` set against the committed `.github/scripts/agent-gates.sh`, which is the file those patches exist not to edit: the set on disk against the set the suite names, both directions and by name; each patch alone; every ordered pair applied in sequence, so no landing order has to be written down anywhere; the full set landing and the result still parsing under `bash -n` and `shellcheck`, because a patch that applies and yields broken shell is still wrong; that the folded capture-claims patch still carries both `check_capture_claims` and `check_testdata_index`, so a later re-cut cannot drop half of it quietly; and that each header's `git apply` line names the file the reader is holding. A case holds the working-tree gate script byte-identical to the committed one, so a local edit under `.github/` cannot quietly change what every other case measures. Every mutation goes to a `tempfile` scratch tree and nothing writes to `.github/` |
| `tools/test_readme_suite_table.py` | this table's own first column against what `find` discovers, both directions and by name: a discovered suite with no row and a row for a suite that is gone are different mistakes, and the half that broke is the one a missing row took. The *set* and nothing else — the descriptions are prose, and comparing counts would turn every added test into a failure. It is a discovered suite itself, so the invariant covers the file that checks it |

Committing a `test_*.py` is the whole of what it takes to be run. A row is
the one step the runner cannot do for it, because the second column is prose
— what the suite stands in for — and the runner has no reason to know any of
it. The row stays hand-written, and
[`tools/test_readme_suite_table.py`](test_readme_suite_table.py) is what
makes skipping it fail, by name, on a full run.

`windows/tools/ecrw_fake.py` is a shared fixture rather than a suite — it is
the offline stand-in for the `ecrw` module, installed by
`test_manual_fan_ctrl_probe.py`, `test_ec_watch.py`, `test_gpu_block_watch.py`
and `test_ctgp_dben_probe.py`, and the `test_*.py` pattern above does not pick
it up, so it costs no suite count. `windows/tools/test_ecrw.py` is the odd one
out and installs nothing: it puts a fake `ctypes.WinDLL` in front of the real
`ecrw.py`, because a suite that only ever exercises the fake is not testing
the file whose arithmetic #147 is about.

Named directories run alone, which is what to reach for when editing one tool:

```sh
bash tools/run-tests.sh windows/tools
```

The exit status is non-zero if any suite failed, and the runner's per-file
output lines each carry what that suite ran. It prints what ran; it does not
assert a count, the per-suite one or the total, because an expected count turns
every added test into a failure. That is the whole reason the two numbers
above are read off a run rather than kept by hand. A run that finds no suite
at all is a failure too, not a silent pass — the vacuous check is the same
defect the gate's listing parse had in `docs/findings.md` §14b.

## One interpreter per file, and why that is not a preference

The `windows/tools` suites used to install a fake `ecrw` into `sys.modules`
with `setdefault`, and the fakes were not the same shape: some exported `Ec`
only, others `Ec` and `EcError`, and `ec_watch.py` imports both. In one shared
interpreter, whichever suite imported first won, and a tool that imports a name
the winner lacks died with `ImportError: cannot import name 'EcError' from
'ecrw'`. It passed only by sort-order accident, which nothing asserted.
`docs/findings.md` §16 has the reproduction.

**Issue #186 reconciled the two fakes that existed when it was written:**
`windows/tools/ecrw_fake.py` carries `Ec` and `EcError` over the real module's
whole surface, and `test_manual_fan_ctrl_probe.py`, `test_ec_watch.py`,
(since its merge) `test_gpu_block_watch.py` and (also since its merge)
`test_ctgp_dben_probe.py` `install()` it (by assignment, not `setdefault`).
Three suites that landed in parallel with it — `test_ec_validate.py` (`Ec`
only), `test_system_id_probe.py` and `test_charge_target_test.py` (`Ec` and
their own `EcError`) — still install their own fakes with `setdefault`, so a
single discovery run over `windows/tools` is still order-dependent for them.
Moving those three onto `ecrw_fake.install()` is a follow-up; until then the
per-file loop is load-bearing, not only insurance.

## What it does not run

- **No gate, no workflow.** CI runs `.github/scripts/agent-gates.sh`, which is
  copied from [`ElDavoo/agent-pipeline`](../docs/agent-pipeline.md) and cannot
  be edited here. `docs/agent-pipeline.md` carries the one-line call for a human
  or an upstream change; until then these suites are not per-commit coverage.
  The runner prints that on every run, the way the cheap tier prints its own
  deferral.
- **No hardware, and no evidence of any.** Every suite is offline by
  construction: device discovery, file opening and ioctls are mocked against
  hand-built fixtures, and the `windows/tools` suites fake `ecrw` — and,
  for the charge-target tool, the `powershell` call behind its WMI line —
  precisely so no Windows box is needed. No EC is opened, no register is read
  back, and no HID node is touched. `linux/lightbar/README.md` and each suite's
  own docstring say the same thing where the tool is described.
- **Not the decompiler tooling.** Those tools' `--check` and `--self-test` runs
  are the gate's, and they are a different set of files; see
  `docs/agent-pipeline.md`.
- **The checker is not in the gate either.**
  `check_doc_patch_refs.py` is a `--check`/`--self-test` tool of their shape and
  it is **not** wired into `.github/scripts/agent-gates.sh`, for the same
  template-copied-file reason: `docs/agent-pipeline.md` item 13 carries the
  recipe, and no `docs/ci/agent-gates-*.patch` was added, for the reason
  [`findings/prose-line-citations-held.md`](../docs/findings/prose-line-citations-held.md)
  set out for `run-tests.sh`. Its **suite** needs no wiring to be run at all —
  `tools/run-tests.sh` finds it, which is the whole of what a suite takes. What
  the gate would add is per-commit coverage of the prose, and nothing here
  claims it until a human lands the patch.
