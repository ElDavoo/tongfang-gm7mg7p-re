# The refusal contract's measured-state section, corrected against this tree (issue #816)

**Nothing here is a hardware claim, and nothing here is an EC finding.** No
register's `status:` changed, no register was read back, no image was opened and
no capture was taken; no laptop, EC or Windows machine is involved anywhere on
this page. Every figure below is a `unittest` run over committed text files or a
`grep` over committed prose, and every one of them is re-derivable by the
command that prints it. The two census CSVs, `xdata-cluster-names.csv`,
`xdata-0860-census-sites.csv` and `registers.yaml` are byte-untouched by this
work, and `ec/decompiled/**` was not regenerated.

#753 read
[`xdata-no-eq-guard-refusal-contract.md`](xdata-no-eq-guard-refusal-contract.md)
to decide between re-pointing the copy-and-`str.replace` recipe at
`xdata_register_map.py`'s current spelling and replacing the recipe with the
`--no-eq-guard` switch the tool already ships. It chose the flag, landed it, and
then — because the two sentences it had relied on sat in a long shared prose
file — **recorded them as superseded in
[`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md)
instead of editing them**, and wrote that *a reviewer can overrule that, and the
cost of doing so is one sentence each*.

This page is that reviewer. Six of the sentences are false against the tree
this lands on, two more describe a red set that no longer holds, and the
measured-state section those sentences sit in reads end to end as a record of a
runner state that has passed — for the three suites it is about, which is all it
is about. Each is corrected in place beside itself, dated and attributed,
carrying the number that replaced it. Nothing was rewritten and nothing was
deleted, per `../findings.md` §4a-4d, and the shape is the one the `#608`
correction block on the refusal-contract page already sets: the over-claim left
standing, and the reason it was wrong next to it. That block is named by its
issue rather than pinned to a line range, deliberately — this page's own first
blockquote added 16 lines to that file above it, which is precisely the
"`adding lines invalidates the pin" problem the next section is about, so a
`:NNN` written while drafting it was already wrong before the block landed.

**One qualification belongs at the top rather than at the bottom, because the
next four sections quote a runner that is not quite green.** The three
*failures* this page corrects sentences about are resolved and two of the three
suites are green, and the sentences about anything else are not its business.
But the tree this lands on still has one red suite —
`ec/tools/test_check_cluster_citations.py`, the third of those three, whose one
failure is on `xdata-cluster-names-guard-off-recipe.md:220`, which is **#822's**
write-up and not one of the pages below. It reproduces on a clean
`origin/main`, and `../findings.md` §52 already records it in a merged-tree note
and names it to that file's owner. Every transcript below is the merged tree's,
not the one this page was drafted against; the first draft measured against
`64dbde19`, before #822 landed.

## What the runner says on this tree

The figures below are the merged tree's, and they are **not** the ones this page
was drafted against. Measured first at `64dbde19` — the commit #753 landed, and
what this work's first draft started from — the runner printed
`All 30 suite(s) passed, 882 tests`. Seven commits had landed on `main` as of
`5111e309`, which is where this branch forked at the implement stage; **#854
(`e198fd98`), then #846 (`964279dc`), and then #801 (`72ff69d1`) landed after**,
so `origin/main` is now the last of those and `git merge-base origin/main HEAD`
returns it, with ten commits
since rather than seven (`git rev-list --count 64dbde19..origin/main`), three of
which changed a figure quoted on this page: #822 added a page that makes one
suite red, and #846 and #801 each added a suite of their own — 52 and 40 tests,
which together are exactly the `882 → 974` the totals line has moved. This page
adds no test, so the rest of the distance is accounted for. Re-deriving on the
tree this lands on:

```console
$ bash tools/run-tests.sh
...
ec/tools/test_check_cluster_citations.py: FAILED
FAIL: test_committed_prose_matches_committed_census (test_check_cluster_citations.TheCommittedTree.test_committed_prose_matches_committed_census)
AssertionError: 1 != 0 : docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0464 is not a member of any cluster this line names (`main-ec-002`, `main-ec-003`, `main-ec-004`, `main-ec-007`, `main-ec-013`, `main-ec-122`, `main-ec-125`, `main-ec-128`, `main-ec-214`, `main-ec-292`, `main-ec-297`); it is a member of `main-ec-145`
32 suite(s) run, 974 tests; one or more FAILED.
$ echo $?
1
$ git status --porcelain
                                    # empty: a red runner wrote nothing either
```

**The one red suite is the third of the three this page is about, and it is red
on a different line for a different reason.** `0x0465` is flagged beside
`0x0464` on the same line, both in #822's `xdata-cluster-names-guard-off-recipe.md`,
where the `:220` paragraph is a pasted `xdata_register_map.py` transcript — it
prints cluster ids of its own — sitting in the same paragraph as the addresses a
later sentence of it discusses. That is nothing to do with §26, which is what
the sentences below are about. The count, 48, is unaffected: `Ran 48 tests …
FAILED (failures=1)`, against the page's "46 tests, 1 failure", so `46 → 48` is
still the change in the count and only the *reason* for the failure has moved.
The three suites' own counts — 28, 45 and 48 — hold across every tree; the
totals line does not, and moved from 30/882 to 31/934 when #846 added
`ec/tools/test_walk_budget_census.py` at 52 tests, then on to 32/974 when #801
added `ec/tools/test_check_citation_lines.py` at 40. That is the argument below
made by another example.
*(**Corrected at the merge, 2026-09-25, #850.** The first clause is the one that
stopped being true. "The three suites' own counts — 28, 45 and 48 — hold across
every tree" is right about `45` and `48` and was right about `28` until #850
added `TheExportOwnershipClusters`'s two cases to
`ec/tools/test_xdata_cluster_names.py`, which measures **30**; the totals line
moves again for the same reason, to **`33 suite(s) run, 1020 tests`**, and the
red suite above is still the same one on the same #822 line. **#851 then added a
suite in the same window, so the tree this finally lands in reads
`34 suite(s) run, 1035 tests`**, and the `30` is the one figure of the three that
did not move. Every figure in
this block was re-derived on the tree this landed on and is left visible for the
same reason — it was true of that tree — and `runner-red-suite-set.md` is where
the rule that lets a count go stale without anything turning red is argued.)*

The three suites the retracted sentences are about, individually rather than
through the runner, so that a reader can re-run one and not wait for the whole
thirty-two:

```console
$ python3 -m unittest discover -s ec/tools -p 'test_xdata_cluster_names.py'
Ran 28 tests in 15.677s

OK
$ cd ec/tools && python3 -m unittest test_check_site_census
Ran 45 tests in 0.603s

OK
$ python3 -m unittest test_check_cluster_citations
FAIL: test_committed_prose_matches_committed_census (test_check_cluster_citations.TheCommittedTree.test_committed_prose_matches_committed_census)
Ran 48 tests in 0.250s

FAILED (failures=1)
$ cd ../.. && python3 ec/tools/check_cluster_citations.py
docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0464 is not a member of any cluster this line names (...); it is a member of `main-ec-145`
docs/findings/xdata-cluster-names-guard-off-recipe.md:220: 0x0465 is not a member of any cluster this line names (...); it is a member of `main-ec-145`
2 citation(s) disagree with ec/annotations/xdata-clusters.csv
$ echo $?
1
```

**The `Ran 93` of a two-module invocation is not a figure this page quotes,
because it is not a figure anyone would run.** One module is green and one is
not, so the combined `Ran 93` would read as a passing number; the two are run
separately above for that reason, and the counts decompose as **45**
`test_check_site_census` and **48** `test_check_cluster_citations`. The split is
one of the two things the issue got slightly wrong in a way worth recording: the
page's own "45 tests" for `test_check_site_census.py` is still exactly right,
and only the "1 failure" beside it is not. The suite whose count moved is the
other one, **46 → 48**.

**The checker's file-and-line total is not printed on a failing run**, so the
figure below is the corpus walk the same tool performs, not its own output line.
`check_cluster_citations.py` walks the repository's prose corpus, so every page
added to it moves both numbers: **112 files / 54972 lines** on the tree this
lands on, over which it finds 2 problems. That is the same rule as the runner's
totals — the figure belongs to the merge — but it cuts the other way from the
one this page is arguing. Here the count moving is not a stale number going
stale; it is new files being *checked*, which is the tool doing its job. A
corpus that did not grow when pages were added would be a corpus that was not
reading them: this page is one of the 112 files the walk reads, and both of the
disagreements it reports are on a single line of #822's write-up rather than on
this one, so being read is not the same as being flagged. (Three files have
joined the corpus since the first figure here was taken, in the same class and
none of them a correction to anything on this page: this one, plus
`walk-window-terminators.md`, #846's write-up, and
`prose-line-citations-held.md`, #801's, the last two having landed on `main`
while this page was open. The lines they brought with them are the same class of
movement as the runner's extra suites.)

**The total is a line count, so a page added after it was measured makes it
wrong — this one included.** `check()` returns `len(text.split("\n"))` per file
(`ec/tools/check_cluster_citations.py:500`, `:529`) and `main()` sums those
across every `.md` under `cc.ROOTS` (`:548-561`), so the figure is the corpus's
line count with nothing derived from content. The first write of it was 22 lines
short for exactly that reason: the fix round that followed it added 22 lines to
`xdata-no-eq-guard-refusal-contract.md`, a file inside the corpus, and nothing
re-ran the walk. The number above is re-derived on the tree as it now stands,
and re-deriving it is short enough to paste:

```console
$ python3 - <<'PY'
import os, sys
sys.path.insert(0, 'ec/tools')
import check_cluster_citations as cc
members, known, counts, by_key, by_name = cc.census(cc.CLUSTERS, cc.REGISTERS)
paths = []
for root in cc.ROOTS:
    for dirpath, dirnames, filenames in os.walk(os.path.join(cc.REPO, root)):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                  if f.endswith('.md')]
paths.sort()
read = sum(cc.check(p, members, counts, known, by_key, by_name)[1] for p in paths)
print(f'{len(paths)} files / {read} lines')
PY
112 files / 54972 lines
```

The sentences quoting it are quoting a measurement rather than a memory, so a
reader who gets a different number has a command to run rather than a
disagreement to settle. **Any edit to a page under `ec/`, `docs/` or
`evidence/` — this page among them — obliges a re-derivation before this number
is quoted again.**

The first draft of this section quoted a line the tool prints instead, and that
transcription was wrong in a way the rest of this page is about. It read
`103 files / 50859 lines, still exit 0`, but **no tree measured prints that**:
`check_cluster_citations.py` at `d87d877e` (#826) — the last commit it exits 0
on — prints `103 files / 50552 lines`, and at `2ed6f030` (#822), the nearest
tree by file count, the walk above covers `103 files / 50668 lines` while the
tool exits 1 on #822's own two citations, printing no totals of its own. The
file count was right for those two trees and wrong here, the line count was
right for none, and "still exit 0" was wrong on both, because the run that made
the checker red is #822's. So the number is derived from the walk rather than
transcribed, and the figure above is the merged tree's rather than any single
commit's.

**The totals are a property of the merge, not a durable claim, and the red set
is the only part of the sentence that is about anything.** A total moves when a
suite lands, when a case is added to one, and when a test is removed. That is the
choice
[`runner-red-suite-set.md`](runner-red-suite-set.md) makes explicitly by leaving
its own totals line out of its transcript, and
`0751-grader-self-test-gate.md:38-41` made it for the same figure earlier. So the
corrections below record the *set* — and the set is not empty on this tree, for
the one reason given above — and name the runner's line as the source, rather
than pinning `32` and `974` into five different prose files to be wrong six
times instead of once. That pasting a total into a file is precisely how the
sentence being corrected came to be wrong is the reason, and this page is its
own counter-example: `30`/`882` went stale between this branch being written
and `main` taking #846, and every transcript above that quoted it was
re-derived on the merged tree rather than carried over from the branch.

## Every sentence this corrects, and where its correction landed

The retracted text is quoted rather than pinned to a line number. That is not
stylistic: these corrections **add lines to the files they correct**, so any
`:NNN` aimed at one of these sentences is wrong on the way in.
`0751-grader-self-test-gate.md` is the worked example — #753 cited it as `:76`
and it was at `:109` — and that mistake is recorded in the
`xdata-cluster-names-guard-off-recipe.md` superseded-claims table precisely so
the next writer does not repeat it.

| page | what it said | what it says now |
|---|---|---|
| `xdata-no-eq-guard-refusal-contract.md`, claim-table row 1 | "that class has been in error in `setUpClass` since #528 and runs none of its six cases (see below), so of the two only the first is green today" | both halves are green; #753 dropped the recipe, the six cases run, and a seventh was added. A dated block after the table |
| same page, the red-set section's heading and first paragraph | "Three suites are already red on `main`, and one of them is this flag's doing" and "**19 of 22 suites passing**. All three failures reproduce byte-for-byte…" | all three failures it counts are resolved. The one suite still red is the third of those three, and is red on `#822`'s page rather than on anything here. A dated block after the paragraph |
| same page, `TheGuardOffRegeneration` | "**`test_xdata_cluster_names.py::TheGuardOffRegeneration` — 6 tests, none of which run, and 1 error in `setUpClass`.** The module reports `Ran 21 tests … FAILED (errors=1)`" | `Ran 28 tests … OK`, and the class runs seven cases. A dated block after the walk it describes |
| same page, the `GUARD` walk that follows it | the literal pair "**no longer exists in the tool**"; `store_target(text, start, end, eq_guard=True)` at `:1220`, `if eq_guard and stripped.startswith("==")` at `:1243`, `scan()` at `:1604`, `not args.no_eq_guard` at `:2292`; and the `setUpClass` `AssertionError` transcript | the suite no longer patches anything, so the walk describes a recipe that is not in the tree; and the four pins are **352 to 625 lines low** on this tree, by four different offsets — `:1572`, `:1595`, `:2168`, `:2917`. The same dated block |
| same page, the "only working route" paragraph | "**the accepted run in `test_xdata_register_map.py` is the only working scripted route to a guard-off census from the committed tree**" and "The fix belongs with the follow-up … it is **not** fixed here" | there are two routes; #753 **is** that follow-up and it chose the second half. A dated block after the paragraph |
| same page, the site-census paragraph | "**`test_check_site_census.py` — 45 tests, 1 failure.**" plus the 14 `bank0/D091.c` line disagreements attributed to **#503** | green at 45 — and the attribution is right, so only the state is corrected: #503's body-level edits are the whole of the drift, and **#752** re-pinned the four cells. A dated block after the paragraph |
| same page, the cluster-citations paragraph | "**`test_check_cluster_citations.py` — 46 tests, 1 failure.**" plus a `check_cluster_citations.py` transcript reporting `docs/findings.md:5520` | **48**, not 46; the transcript does not reproduce and **§26 is not what makes it red**. The one failure is on `xdata-cluster-names-guard-off-recipe.md:220`, which is #822's write-up. A dated block after the paragraph |
| `../ec/annotations/xdata-register-map.md`, in the sentence the write-up quotes | "`test_xdata_cluster_names.py` patches a literal `if stripped.startswith("==")` that the tool's `--no-eq-guard` switch grew an `eq_guard and` conjunct in front of" | the suite runs the committed tool with `--no-eq-guard`; and the `#752` block's "That leaves **one** suite of the two red" is now **neither**. A dated block after the `#752` one |
| `../findings.md` §29 | "19 of 22 suites", "all three failures", and "the accepted run in the new suite is currently the only working checked-in-suite route" | a dated **Updated** addendum after the `#608` one, which is the pattern that file already uses for a later issue correcting an earlier section |
| `../findings.md`, this issue's own summary | — | it is **§59**, not §51: #819 (§51) and #817 (§52) landed on `main` first and hold those numbers, #797's opcode-table census (`1b870484`) took §53, #820's re-derivation checklist §54, and #847's rel8 bound §55. #848's `--sites` address-range summary then took **§56** on `main` after this page was written, and #846's `walk()` stop-reason summary (`964279dc`) took **§57** in the same window. #801's prose-line-citation checker took **§58** (`72ff69d1`), also on `main` and also while this page was open — so this summary is renumbered three times, to the next free one, and lands below it. #817's §52 is also where the one red suite on this tree is recorded |
| `../tools/README.md` | "Two of the thirty are red in this tree and are left red here" and, under the heading "The totals are not a pass", the two named `FAILED` lines and "the runner exits 1" | both suites it names are green, and the runner still exits 1 — on `test_check_cluster_citations.py`, which is a third file's finding. A dated block after the paragraph. **The suite and test counts in those two paragraphs stay as they are** — see below. *(Re-pointed at the merge: #821 had already recast the first of those two sentences as history before this page was written, and #846 re-derived the counts, so the block is written against what the file now says rather than what it said when this table was drafted — the correction itself, which of the three suites is red, is unaffected by either)* |
| [`runner-red-suite-set.md`](runner-red-suite-set.md) | "Two suites fail on their subject", naming `test_check_site_census.py` and `test_xdata_cluster_names.py` and describing `TheGuardOffRegeneration`'s `setUpClass` as "rais[ing] before any case runs" | both are green. A dated section after the `#615` counts section, carrying the one suite that is *not* |
| [`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md) | the superseded-claims table's rows 2 and 3, whose "now" column promised the correction this page pays for | a closing paragraph under that table. Rows 1 and 4 are untouched: row 1 (#568 open) still stands as written, and row 4 was already corrected in place in a test file |

## Why #753 recorded two of them rather than editing, and what that cost

The decision is recorded in its own write-up and is not re-litigated here: the
two sentences sit in `ec/annotations/xdata-register-map.md` and
`xdata-no-eq-guard-refusal-contract.md`, both long shared prose files with agent
PRs open against the same tree, and #753 was landing a change to
`ec/tools/test_xdata_cluster_names.py` and one new case. A §4a-4d correction in
place is the repository's rule for a *wrong* claim; recording it in a sibling
write-up is the cheaper trade when the alternative is a merge conflict in the
middle of somebody else's PR.

The cost is exactly the sentence-counting that got the trade wrong, and it came
out at **six** rather than one, because the two sentences #753 recorded are not
independent of four others it did not record:

- The refusal-contract page's **measured-state section is one claim, not
  several.** Its heading says three suites are red; its first paragraph counts
  them; the next three paragraphs each name one and give its cause; and the
  last of them ends on "a reader running the runner will hit it". Correcting the
  three suite paragraphs and leaving the heading would have produced a page that
  said three suites were red and then, three paragraphs later, that none were.
- **The same "one working route" claim appears in two files**, and correcting
  one of them leaves the other asserting the opposite. It was in the
  refusal-contract page and in `../findings.md` §29, the summary *of* that page.
- **The "one of the two red" clause in the register map depends on a suite
  count it shares with the sentence directly above it.** #752 corrected the
  `test_check_site_census.py` half of that sentence and left the
  "That leaves **one** suite of the two red" it implies; #753 made the other
  half false without touching it, so the block that was correct when written is
  now wrong in a clause its own neighbour introduced.
- **And one correction points at a file that says the opposite.** The `#752`
  block nominates `runner-red-suite-set.md` as "the file that tracks the set", and
  that file's first section opens by naming both suites as red. Correcting the
  map while pointing at it would have pointed a reader straight back at the
  sentence being corrected.

None of that is an argument against the choice. It is the argument for this
page existing: the right place for a correction is known when the claim is
written, and unknowable when it is read. The lesson worth keeping is not "never
record instead of editing" — it is that a recorded correction is a **promise**,
and the cost of the promise is borne by whoever notices it was not kept.

## The sentence that survives, and why it is here

The refusal-contract page's paragraph on the recipe's history — *"That is the
third time this recipe has been re-pointed at a line number, which is itself the
argument for the flag"* — is **left byte-untouched**, and it is the reason this
page exists in its current shape.

It is the one claim in the measured-state section that #753 did not falsify but
acted on, and it is load-bearing for the repair rather than incidental to it.
The recipe had been re-pointed once for #302's parameterisation and again for
#566's move of the census into `census_and_groups()`; a third re-point, this time
against a line the recipe would also have had to keep finding, is what made the
argument for a flag conclusive rather than merely reasonable. And the pins in
this very branch are 352 to 625 lines stale, by four different offsets, for the
same reason the page's own `docs/findings.md:4885-4890` passage warns about —
*"say which tree a citation is measured against, or it drifts again."* The size
is the stronger half of the argument, not the weaker: a reader who assumed these
four moved together would be wrong about two of the four, because `:1604` and
`:2292` are not 352 lines low like the first pair but 564 and 625.
The sentence is a live instance of its own claim, and deleting it would have
removed the evidence.

## The open question, and what actually settles it

The issue recorded one thing it could not explain and asked for it to be
recorded rather than answered. Its framing, quoted rather than adopted:
*§26 of `../findings.md` still pairs `0x0800` with `main-ec-086`*, while *the
suite `test_check_cluster_citations.py` was green and the checker had exited 0
over 50,190 lines* — and the hypothesis it drew from that was *a change in what
the tree is checked for, not merely a moved line*.

**Both halves of that framing are wrong on the merged tree, and they are wrong
in a way worth separating.** The suite is no longer green and the checker no
longer exits 0 — but not over §26: both facts are #822's `0x0464`/`0x0465`, on
its own write-up, where a pasted tool transcript that prints cluster ids shares
a paragraph with the addresses a later sentence of it discusses. That is the
*same* rule §26 exercised, on different prose, which is why the two have to be
told apart before the question can be asked at all. So "is the tree still
checked for the same thing?" has to be asked about §26 alone, and the answer
for §26 is the same as it was on the base commit: the tree is checked for
exactly what it was, and §26 no longer makes the claim at all. What follows is
what settles that, and it is unchanged by #822 landing.

**Asking the tool's own `units()` what it makes of that paragraph settles it.**

```console
$ python3 - <<'PY'
import sys; sys.path.insert(0, 'ec/tools')
import check_cluster_citations as cc
text = open('docs/findings.md', encoding='utf-8').read()
for lineno, unit in cc.units(text):
    if not 6348 <= lineno <= 6369:
        continue
    ids = [i for i in ('main-ec-086', 'main-ec-104') if i in unit]
    hits = '0x0800' in unit
    if not (ids or hits):
        continue
    print(lineno, '| ids:', ids, '| names 0x0800:', hits,
          '| MEMBERSHIP hit:', bool(cc.MEMBERSHIP.search(unit)))
PY
6354 | ids: ['main-ec-086'] | names 0x0800: False | MEMBERSHIP hit: True
6357 | ids: [] | names 0x0800: True | MEMBERSHIP hit: False
```

Two facts, and the disagreement resolves into neither being wrong:

- **The surviving `main-ec-086` claim is true.** The committed
  `xdata-clusters.csv` row for `main-ec-086` reads `0x07FD 0x07FE 0x07FF` — the
  three bytes §26 says the routine steps over, which is what the sentence
  claims. Nothing in §26 needs correcting, which is why #564's finding was
  never filed and why this issue leaves that page alone.
- **The `0x0800` sentence no longer reads as a membership claim, and never gets
  as far as being one.** `units()` cuts the paragraph into sentences, and
  `0x0800` landed in the *next* one — so the unit naming the cluster id and the
  unit naming the address are not the same unit at all. The unit holding the
  address names no cluster id, and a unit that names none is dropped at
  `if not ids: continue` (`ec/tools/check_cluster_citations.py:503`) before the
  address is even collected. It would have been skipped again a few lines later
  as well, at `skip (no membership claim)` (`:514-517`), because it carries none
  of the `MEMBERSHIP` vocabulary — `\b(?:clustering|clusters?|members?)\b`
  (`:164`) — and the two skips agree. Either way the
  `0x0800`-in-`main-ec-104` reading never became a second claim: it is a bound,
  and the tool is right to leave a bound alone.

So the red case was a **prose** coincidence — one sentence holding both a
cluster id and `0x0800`, which the unit's membership word made the checker read
as an attribution — and §26 has since been reflowed so that it does not. The
checker's rules did not loosen; its input changed shape.

**The first draft of this section *was* that coincidence, and a full run of
`tools/run-tests.sh` caught it.** The first version of the heredoc above printed
each unit with `repr()`, because that is the obvious way to show what a unit
contains — and it printed §26's two sentences into a single joined block, which
put the id and `0x0800` into one unit of *this* file, next to the word "cluster"
that `repr()` carried along from the sentence. This paragraph, describing that
accident, then did the same thing a second time and turned the run red again.
So: `check_cluster_citations.py` reads a unit that names any address, any
cluster id and any membership word as a claim about the address — the
preposition rule at `:393` only chooses *which* id, and when it finds none the
check falls back to every id in the unit.

```console
$ python3 ec/tools/check_cluster_citations.py
docs/findings/xdata-no-eq-guard-measured-state-correction.md:184: <the checker's own
  message, which names both cluster ids and is NOT reproduced here — quoting it
  would be the fifth instance of the thing this block is about, and would turn
  this file red again on the next run>
1 citation(s) disagree with ec/annotations/xdata-clusters.csv
$ echo $?
1
```

The `:184` is the line the failure landed on *in the draft*, and two parts of
that output would not reproduce verbatim now: the line itself, because every fix
since has moved it, and the count, because the tree has since gained #822's
finding — the merged tree reports `2 citation(s)`, both on
`xdata-cluster-names-guard-off-recipe.md:220` and neither in this file. The
message is elided for the reason above rather than because it is long. The shape
is the point — the tool names a file, a line, and the two clusters, and that is
all a reader needs in order to go and get the rest.

That is worth more than the sentence it interrupted, and it is the sharpest
statement of the mechanism available: **quoting §26's sentence is enough to make
the suite red.** The red case was never about a rule being enforced; it is
reproduced by any page that reproduces the text, which is a property of a
prose-scanning citation checker and not a defect in it. On a green tree that
sentence is the only way to make the suite red; on this tree it is one of two
ways, and the other is #822's. The transcript above is in the form it is because
a form that dumps both sentences whole is *itself* a citation — it reports the
ids and the address per unit instead of the prose per unit, and the two facts
survive that change intact. The message quoted in the block above is the
checker's own, kept verbatim, and it is a fifth instance of the same thing: the
file that documents the rule cannot quote the rule's output. The check
`test_check_cluster_citations.py` has for this is the one that pins "the tree's
committed prose currently agrees with the committed census
beside it", and it is what made both drafts a failing run rather than a subtle
drift.

**One thing this turned up that is not this issue's**, recorded because it is
the same class of drift this page is about: the correction at
`../ec/annotations/xdata-register-map.md:1228` pins
`../tools/xdata_register_map.py:1582` as the `eq_guard and` line and `:4495-4499`
as the `--out-*` refusal, and both are now **13 lines low** — the line is at
`:1595` and the refusal at `:4508`. Those two agree with each other, which is
what a pair of pins written and re-pointed together does, and they want the
same treatment: a dated correction beside the pin, not a silent edit. They are
*not* the same drift as the refusal-contract page's four pins, which this page's
first draft wrongly shared the offset with: those are 352 to 625 lines low, by
four different offsets, so no single handful of commits explains both sets and a
correction filed for one does not discharge the other. It is a follow-up, not a
drive-by, and nothing else here depends on it.

## Left out on purpose

- **The one red case, `xdata-cluster-names-guard-off-recipe.md:220`** — it is
  #822's, it landed after this page was written, and `../findings.md` §52
  already names it to that file's owner in a merged-tree note. Fixing it here
  would be an unclaimed fix riding a prose-correction sweep, and it would also
  mean this page claimed a green suite it did not measure. It is named in five
  places above so that a reader is never left believing the runner exits 0.
- **`../ec/annotations/xdata-06c2-06db-timers.md`** — the issue's own
  instruction, and the right call. §6a's published figures still reproduce on
  this tree, and #753's `test_the_census_is_the_one_6a_measured` now *holds*
  them, which is the mechanism that keeps them from drifting again. #659 owns
  that page's other stale cells.
- **[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md)**
  — a deliberately preserved transcript of the retired recipe, labelled as one
  in its own heading, whose embedded `assert guard in s` no longer holds. That
  is what a record of a retired procedure is supposed to look like, and a
  transcript that had been made to run again would have stopped being a record.
- **§26's prose**, for the reason measured above: the `main-ec-086` claim is
  true, the `0x0800` sentence is a bound and not a claim, and there is nothing
  there to correct.
- **`../tools/README.md`'s suite and test counts.** They are `32` and `974` on this
  tree — #801 re-derived them in its own third merged-tree note, having added
  `ec/tools/test_check_citation_lines.py` at 40 tests to the `31` and `934` #846
  put there for `ec/tools/test_walk_budget_census.py` at 52, which had itself
  moved the `30` and `882` #821 wrote from `90ac6d2c` — and the runner still
  prints exactly
  that, so leaving them alone is a decision rather than a patch over a stale
  number. *(The "prints exactly that" held on `main` and the merge ended it:
  #850's two new cases in `test_xdata_cluster_names.py` made #850's merged tree
  read `1020`, and #851's suite, landing in the same window, makes this one read
  `1035`. The counts are left at `33`/`1018` and the fact is recorded here and
  in the correction blocks those two files carry, which is this page's own rule —
  re-derive on the tree you land on, do not rewrite a shared totals paragraph
  for a two-case delta — working.)* What no check in the tree can see them is
  unchanged and is still the
  reason: `tools/test_readme_suite_table.py` compares the row *set* and
  `tools/run-tests.sh` asserts no total. The correction blocks there and in
  `runner-red-suite-set.md` say so, and the file's own closing paragraph already
  requires the figures to be re-derived by running the runner rather than by
  arithmetic on a diff. That the figures moved again between this page being
  written and the tree it lands on is the same lesson, arriving on schedule.
- **Any new test.** The issue scopes this to prose, and that is right rather than
  merely convenient: a second check over prose nobody asserts on would duplicate
  a rule the tree made on purpose. `tools/test_readme_suite_table.py` compares
  the *set* of rows and deliberately not the counts, and `tools/run-tests.sh`
  prints its totals and asserts none — a check that pinned a red set would
  turn every added case into a failure, which is the trade
  `runner-red-suite-set.md:99-113` argues for at length.
- **A prepared upstream patch.** This change does not end at a
  `Wer-Wolf/uniwill-laptop` or `tuxudo-drivers` contribution, so there is
  nothing for a human to submit by hand and nothing was opened anywhere.

## What this does not say

No EC was opened, no register was read back, no image was read except as a
committed file, no capture was graded, and no hardware or Windows machine was
involved. The four transcripts above are `unittest` runs over committed text and
a citation checker over committed prose; a green suite is a statement about this
repository's files, not about the firmware. `XDATA_0860` stays
`present-untested`, and the `--no-eq-guard` refusals this page is adjacent to are
still worth pinning for the same reason they were worth pinning before: they stop
a run *before* it writes over a committed source of truth.
