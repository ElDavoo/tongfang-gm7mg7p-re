# The runner's totals, re-derived from a run, and why a red suite moves them (issue #817)

The write-up for [issue
#817](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/817), which is
about `tools/README.md` quoting a red set and a total the tree no longer has.
What this branch changes is the three paragraphs of that file that hold the
figures, and this file.

**Nothing here is a hardware claim.** No register was read back, no capture was
opened, no firmware image was interpreted, and no laptop, EC or Windows machine
is involved. The whole evidence base is two offline things: one invocation of
`bash tools/run-tests.sh` over committed Python, and one in-process measurement
of a suite's own `setUpClass`. Every figure below comes from one of those, and
the command that produced it is given. The measurement driver quoted in
[the mechanism section](#the-mechanism-behind-the-total-measured-not-asserted)
lives under `/tmp` and is **not** committed, because the issue scopes this
branch to prose and a committed driver would be a tool. It loads the suite by
path and patches one method in memory, so `git status` after running it shows
only this branch's own three files and no scratch.

## The run, and what everything else is quoted from

2026-09-25, from the repository root, on this branch's base at `64dbde19`:

```
$ bash tools/run-tests.sh
ec/tools/test_bank1_e582_framing.py: 10 tests, passed
ec/tools/test_check_capture_claims.py: 28 tests, passed
ec/tools/test_check_cluster_citations.py: 48 tests, passed
ec/tools/test_check_site_census.py: 45 tests, passed
ec/tools/test_check_testdata_index.py: 59 tests, passed
ec/tools/test_check_testdata_row_claims.py: 38 tests, passed
ec/tools/test_citation_callers.py: 13 tests, passed
ec/tools/test_citation_frames.py: 28 tests, passed
ec/tools/test_citation_gap_scan.py: 26 tests, passed
ec/tools/test_disasm8051.py: 7 tests, passed
ec/tools/test_export_ownership.py: 26 tests, passed
ec/tools/test_grade_0751_isolation.py: 111 tests, passed
ec/tools/test_grade_gpu_door.py: 15 tests, passed
ec/tools/test_grade_timer_sweep.py: 7 tests, passed
ec/tools/test_group_functions.py: 24 tests, passed
ec/tools/test_inc_dptr_sites.py: 28 tests, passed
ec/tools/test_walk_branch_arms.py: 36 tests, passed
ec/tools/test_xdata_cluster_names.py: 28 tests, passed
ec/tools/test_xdata_register_map.py: 23 tests, passed
linux/lightbar/test_probe_6005.py: 4 tests, passed
tools/test_agent_gates_patches.py: 15 tests, passed
tools/test_readme_suite_table.py: 6 tests, passed
windows/tools/test_charge_target_test.py: 10 tests, passed
windows/tools/test_ctgp_dben_probe.py: 38 tests, passed
windows/tools/test_ec_validate.py: 17 tests, passed
windows/tools/test_ec_watch.py: 47 tests, passed
windows/tools/test_ecrw.py: 21 tests, passed
windows/tools/test_gpu_block_watch.py: 25 tests, passed
windows/tools/test_manual_fan_ctrl_probe.py: 67 tests, passed
windows/tools/test_system_id_probe.py: 32 tests, passed

All 30 suite(s) passed, 882 tests.        # exit 0
```

**The red set is empty, and that is the finding the issue is about.** The
thirty is unchanged — `find` still discovers exactly thirty `test_*.py` and
`tools/README.md`'s table still has exactly thirty rows, so "there are thirty
today" was never wrong and the table is byte-untouched by this branch. The two
figures that were wrong are the total and the sentence naming the red set, and
this is not a first instance: `docs/findings/0751-grader-self-test-gate.md:165-178`
already records this same `All 30 suite(s) passed, 882 tests.` from #753's merge
note, so the number the file now quotes is corroborated by a second record in
the tree rather than resting on this one run.

**The red set is empty on the tree this was measured on, and it is one suite
red on the tree this merged into.** #822 (`2ed6f030`) added
`docs/findings/xdata-cluster-names-guard-off-recipe.md`, and its
`test_check_cluster_citations.py` case now fails on `:220` of that file — a
fenced block that prints a guard-off regeneration beside the committed census,
so it names clusters from two rankings at once while its `joined ['0x0464',
'0x0465']` line cites two bytes the committed census puts in `main-ec-145`,
which is not one of the eleven ids the block names. The two figures this file
is about do not move: still thirty suites, still 882 tests. The *verdict* does
— the merged tree's last line reads `30 suite(s) run, 882 tests; one or more
FAILED` — which is the distinction `tools/README.md` had already drawn for
itself, "the totals are not a pass", now doing real work. It reproduces on a
clean checkout of `origin/main` and it is #822's file rather than this issue's,
so it is named here and in `tools/README.md` and not fixed here.

The two formerly-red suites read `45` and `28` in the block above, and
`tools/test_readme_suite_table.py` — this table's own check, 6 tests — is green,
so the rewrite did not disturb the row set.

## Why the figures are not patched from a diff

The issue is explicit that the gap is not closed by arithmetic, and the
arithmetic is worth showing rather than asserting, because the natural
attempt fails in a way that is easy to miss.

The file said **874**. The two deltas the tree names do not account for the
difference:

- `ec/tools/test_xdata_cluster_names.py` went from **21 to 28** on this tree
  (measured below, and recorded at
  `0751-grader-self-test-gate.md:171-178` for the same suite), so
  `874 + 7 = 881` — one short of the 882 the runner prints.
- `ec/tools/test_check_cluster_citations.py` reads **48** in the block above and
  **46** in `docs/findings/xdata-no-eq-guard-refusal-contract.md:283`, so
  adding that named delta overshoots to **883**.

`881` and `883` straddle the measured `882`, so the two prose figures do not
decompose: there is a further −1 between the two measurements, at a place
nothing in the tree names. **That unnamed remainder is the point.** A reader who
patches the total from the deltas they can name will get a number that is
plausible, off by one, and indistinguishable from a correct one — which is
exactly the failure mode the sentence it would be patching already tells them
to avoid at `tools/README.md:46-49`. The figure is read off a run for that
reason and not because the run was convenient.

The per-suite figure in `xdata-no-eq-guard-refusal-contract.md:283` is **not**
corrected here. It is a dated run record on a named tree and this issue is not
its owner; it is cited only as the overshoot above.

## The mechanism behind the total, measured not asserted

`tools/README.md` already said the totals count tests *run*, failing suites
included, and `tools/run-tests.sh:70-72` gives the reason: a failure changes the
verdict, not how much of the suite ran. That is half the mechanism. The other
half is that **`run` is not `collected`**.

**What is already written down, and what is not.** The observation for one
suite is on record: `xdata-no-eq-guard-refusal-contract.md:225-227` says
`TheGuardOffRegeneration` is "6 tests, none of which run, and 1 error in
`setUpClass`" and that the module reports `Ran 21 tests … FAILED (errors=1)`.
What that file does not do — because it is about that tool's flag, not about
the runner's total — is state the rule, contrast it against an ordinary
failure, or note that the class has **seven** cases now that #753 added one. So
the sentence here is not the first record of the 21; it is the general rule the
21 is an instance of, and the first time the ordinary-failure case is measured
beside it.

A class whose `setUpClass` raises contributes none of its own cases to
`Ran N`, and the error is not itself counted as a test. An ordinary failing case
runs and is counted like any other. So the total moves with *how* a suite was
red and not only with whether it was — which is the sharper version of the
issue's own "the total is a function of the red set", and the reason a suite
going green does not add a knowable number of cases to the figure.

Measured on this tree, from the repository root, by loading
`ec/tools/test_xdata_cluster_names.py` by path (its own committed file, never
written to) and replacing one method in memory:

```python
import importlib.util, sys, unittest
from pathlib import Path

SUITE = Path('ec/tools/test_xdata_cluster_names.py').resolve()

def load(name):
    spec = importlib.util.spec_from_file_location(name, SUITE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def run(label, mod):
    suite = unittest.TestLoader().loadTestsFromModule(mod)
    with open('/dev/null', 'w') as sink:
        r = unittest.TextTestRunner(stream=sink, verbosity=0).run(suite)
    print(f'{label:<20} testsRun={r.testsRun:<4} errors={len(r.errors):<3}'
          f' failures={len(r.failures)}')

def boom(cls): raise RuntimeError('setUpClass refused')
def fail(self): self.fail('an ordinary failure')

run('green', load('tcn_green'))
m = load('tcn_setup'); m.TheGuardOffRegeneration.setUpClass = classmethod(boom)
run('setUpClass error', m)
m = load('tcn_fail'); m.TheNamesFile.test_names_are_unique = fail
run('ordinary failure', m)
```

```
green                testsRun=28   errors=0   failures=0
setUpClass error     testsRun=21   errors=1   failures=0
ordinary failure     testsRun=28   errors=0   failures=1
```

`TheGuardOffRegeneration` holds seven cases, and `21 = 28 − 7`: a `setUpClass`
error takes all seven out and is not itself a test, where an ordinary failure
leaves the count at 28 and changes only the verdict. **The mechanism is
measured rather than reasoned**, and it is the clause the rewritten paragraph
carries, with the 21 / 28 pair as its illustration.

**The 21 is `main`'s figure, not an invented one.** It is the same number
`0751-grader-self-test-gate.md:171-178` records for the suite against
`origin/main`'s copy, and it reconciles: `main` runs 27 − 6 = 21, and #753 added
the seventh case. That file is therefore consistent and is **not** corrected by
anything here.

## The de-anchored sentence, recorded rather than trimmed

The rewritten paragraph ended:

> …and is green in this tree, which holds that row and the one for
> `ec/tools/test_disasm8051.py` **this branch adds**:

`this branch` was written by #688, which is `0873c6cf` — four commits back on
this tree and merged long ago, so the clause is a present-tense claim about a
merge that is four commits in the past. It now reads **"that #688 added"**.

**This was a judgement call and it is flagged rather than made quietly.** The
clause is not one of the three regions the issue quotes. It is inside the
paragraph being rewritten, it is the same class of staleness the issue exists to
fix, and the alternative — leaving a "this branch" in a file that is merged —
would have meant shipping the rewrite with a false sentence still in it. The
de-anchoring is one clause long, and `git log -S` puts the row's provenance at
`0873c6cf` rather than at a guess.

## What the file said before, and what is kept

Per `../findings.md` §4a-4d, the wrong figures are not silently deleted — the
above is the record, and two sentences that were true of the old text survive
into the new text rather than being replaced:

- **"Re-derive them by running it rather than by editing this sentence."** Kept
  verbatim, and this run is the re-derivation it asks for.
- **"The totals are not a pass."** Kept in its weaker true form — *the totals
  were never the pass; the run's last line and its exit status are* — because
  the caveat is independent of the red set and remains true on a green tree.
- **"Both are red on each side of this merge and on `main` at `d9170a77`
  alike."** Deleted whole, with no replacement: `d9170a77` is #751's merge and
  the clause is a claim about a merge that is no longer either side of
  anything. Nothing is substituted for it, so a reader cannot mistake a
  paraphrase for a fresh claim.

**The paragraph about the row check stays verbatim.** `tools/README.md`'s
closing paragraph — the one saying `test_readme_suite_table.py` "checks the
*set* of rows below and deliberately not these counts" — is untouched, and it
is what makes the rest of this file possible: the prose above is the only thing
holding those numbers, which is why they come off a run.

## The pointer to the sibling write-up survives, for a new reason

The rewrite keeps a pointer to `0751-grader-self-test-gate.md`. When the
paragraph was written, the pointer said that file "records the causes and the
follow-up issues that own them" — true of a red set. With the red set empty
that would be a pointer to nothing, so it was re-pointed rather than kept or
cut: the file records **the red set as it stood** and the run that emptied it,
which is a live use, and it is the second record of the 882 quoted above.

## Left out on purpose

- **`0751-grader-self-test-gate.md`'s own two `Left out on purpose` bullets
  (`:351` and `:362`) and `../findings.md` §46's "finds two" (`:7204`).** All
  three name this paragraph set as stale, which is what sent the issue here. All
  three are dated records of what a merge said on 2026-09-25, and §4a-4d keeps
  them; they are named in this file rather than edited.
- **`docs/findings/testdata-index-suite-count-floor.md:204` (#759).** Its figure
  was copied *from* `tools/README.md:14` and needs the same re-derivation, on
  its own page. The issue says leave it, so it is left — and it is the next
  instance of the same drift, for whoever takes it.
- **`tools/README.md`'s `check_testdata_index.py` description (#782).** The
  issue cites it as `:31`, which is not where that description is: on the tree
  this branch started from, `:31` was inside the red-set paragraph and the row
  was `:47`, and this rewrite moves the row to `:57`. The same one-to-three-line
  drift the issue's other `tools/README.md` refs show. **Recorded for a human
  and not acted on** — #759 and #782 are both named out of scope, and folding
  them in is what the issue forbids.
- **`xdata-no-eq-guard-refusal-contract.md:283`'s "46 tests."** A dated run
  record on a named tree, cited above only as the overshoot. Not this issue's
  to correct.
- **The gate wiring for `tools/run-tests.sh` (#162).** This branch's measurement
  says the runner is no longer blocked by a failing suite, and it does **not**
  land the wiring: `.github/scripts/agent-gates.sh` is copied from
  `ElDavoo/agent-pipeline` and this pipeline's push token has no `workflow`
  scope. #162 is unblocked by the evidence here and owned by itself.
- **A new test, and a count assertion in `test_readme_suite_table.py`.** The
  issue forbids it, and
  `docs/findings/runner-red-suite-set.md:92-116` records why the trade is
  right: a check comparing a prose figure to a live run is a count gate wearing
  a different hat, and it would go red on every test-adding PR — the failure
  mode `tools/run-tests.sh:75-79` and that suite's own docstring both refuse.
  **Stated here so the absence of a check reads as a decision.** The trade is
  deliberate and it has a price: a stale count is invisible to every check in
  the tree by design, which is what let this drift in the first place, and
  `runner-red-suite-set.md:92-116` says so in the same words. A wrong number
  nobody is blocked by is cheaper than a right number that turns every added
  case red.
- **Any upstream pull request** (`Wer-Wolf/uniwill-laptop`, `tuxedo-drivers`,
  issue #10). Nothing here ends at an upstream contribution, so there is no
  prepared patch to hand over — and none is to be opened from here in any case.
- **Anything in `tools/README.md` beyond the three paragraphs**: the table, the
  `ecrw_fake.py` note, "One interpreter per file", and "What it does not run"
  are all still true and are all byte-untouched.
- **Any live hardware, Windows, EC or BIOS step.** None is involved and none is
  implied, and no laptop is reachable from this pipeline.

## Nothing else moved

No register `status:` moved, no CSV was edited, no `.asm` or `.c` was
hand-edited, `ec/annotations/registers.yaml` and
`ec/annotations/ghidra-functions.csv` are untouched, no gate was wired and none
was weakened, and no `.github/` file was touched — so the push token's missing
`workflow` scope is never invoked. The diff is three paragraphs of one shared
prose file, this file, and one appended section of `../findings.md`.

## The correction chain, moved here whole (2026-09-27)

**The three paragraphs #817 de-anchored kept growing anyway, and this is where
they went.** `tools/README.md`'s lead sentence — *"There are forty-nine today,
1561 tests in all"* — acquired **22 supersession notes across 3522 lines and
40,240 words** before this section, which is 24% of a 3,679-line file, and it is
reproduced below verbatim so that nothing is lost by removing it from there.
The figures in it are not corrected here and are not meant to be: each was true
of the tree it was measured on, which is the standing §4a-4d gives them, and
several name trees that are no longer reachable.

**Why it was removed rather than left.** It is not a stale sentence that one
correction would fix. It is a sentence that *every merge adding a suite must
edit*, in the same place, with the edit being "append a paragraph explaining the
new arithmetic" — so it is a conflict site by construction, and the resolutions
are what produced the 22 notes. The ordinals disagree with each other
(*ninth*, *tenth*, *third*, *fourth*, *sixth* twice, *seventh* twice …), which is
the signature of branches numbering their own note without seeing the others'.
Two of the notes are the same `## What it runs` section being re-derived on
opposite sides of one merge. And the chain had reached the point where its own
text records that a figure it cites — `a9b3b90c` — **is not an object in this
repository at all**, so a growing part of it is a record no one can re-run.

`tools/README.md` now states no total and points at `bash tools/run-tests.sh`,
whose last line is the total, and `tools/test_readme_suite_table.py` fails if a
spelled-out one comes back. The rule this chain kept re-deriving is now the only
thing in the file: **run the runner; do not edit the sentence.**

### The chain as it stood, verbatim

<!-- Everything below is a verbatim move from `tools/README.md` lines 12-3533 at
     2bc4d16a. Links were rewritten for this file's depth (`tools/` and
     `docs/findings/` are both two levels down, so only the `../docs/` prefix
     changes). Nothing is edited, re-derived or corrected. -->

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. **There are forty-nine today, 1561 tests in all** — both figures
*(Superseded a ninth time, by #54: `ec/tools/test_paged_trampoline_framing.py`
lands with **28** cases, so `46 + 1 = 47` and `1437 + 28 = 1465`, the step being
this one suite and nothing else. Measured here rather than carried, by the
per-file rule the note below gives — the runner still cannot total this tree —
and the `forty-six` and the `1437` stay written where each was measured, per
[`../findings.md`](../findings.md) §4a-4d. **The table gains its row
in the same change**, so the one suite `tools/test_readme_suite_table.py` still
reports as missing is the same one it reported before: #1058's
`ec/tools/test_pd_image_census.py`, which is not this change's to write.)*
*(Superseded a tenth time, by this merge, and **this is the second time in this
run that a suite lands on *both* sides of the same merge**, so the merged tree
is ahead of either side's own arithmetic and neither side's step describes it
alone. `origin/main` at `9bb8fca1` writes **`forty-seven` / `1481`** in this
lead and the branch writes **`forty-seven` / `1465`**, and the step from each is
one suite: #40's `ec/tools/test_walk_flow_follow.py` on one side and #54's
`ec/tools/test_paged_trampoline_framing.py` on the other. **Neither written
figure is its own tree's**, which is the standing the notes above already give:
`main`'s tree finds `48` suites, because #40 landed there and this lead was not
re-measured after it, and the branch's base carried neither #40's suite nor
`main`'s #1030 cases. **Measured on the tree this lands in,
`bash tools/run-tests.sh` reads `49 suite(s) run, 1561 tests`**, and the step
from `main` is the one suite this merge adds and nothing else — #54's
`ec/tools/test_paged_trampoline_framing.py` at **28** cases, so
`48 + 1 = 49` and `1533 + 28 = 1561`, the `1533` being `origin/main` at
`9bb8fca1` re-run with this landing's own `run-tests.sh` rather than differenced,
for the reason the thirtieth note below gives. #40's suite is already on `main`
and is **not** part of this merge's step, which is the one respect in which the
two sides are not mirror images and the same clause the ninth note gives for
`forty-six` → `forty-seven`. Every figure the notes above carry stays written
where it was measured on, per
[`../findings.md`](../findings.md) §4a-4d; the `forty-seven` in
particular is now a full landing behind on `main`, exactly as the fourth note
below already recorded for the `46` one landing earlier.)*
*(Superseded at the `#845` × `#974` merge, and **both sides of that merge moved
a figure, which no merge earlier in this run did**: `origin/main` at `0daac768`
(#974's) reads **`41 suite(s) run, 1271 tests`** and the merged tree read
**`42 suite(s) run, 1277 tests`**, the step being #845's one new suite
`ec/tools/test_trace_xdata_refs.py` at six cases, so `1271 + 6 = 1277`.)*
*(Superseded again at the `#845` × `#1009` merge, and **this is the first merge
in this run of notes with a suite on *both* sides of it**, so the merged tree
takes two suites and neither side's step describes it: `origin/main` at
`5881153d` (#845's) reads **`42 suite(s) run, 1277 tests`** and this tree reads
**`43 suite(s) run, 1301 tests`**, the step being the two new suites together —
#845's `ec/tools/test_trace_xdata_refs.py` at six cases and #1009's
`ec/tools/test_check_history_checkouts.py` at twenty-four — so
`1277 + 24 = 1301` and `43 - 42 = 1`. The `forty-two` and the `1277` the note
below records are left written, per
[`../findings.md`](../findings.md) §4a-4d, each true of the tree it was
measured on; the `1295` and the `1290` and the `1288` this change's own three
notes record stay written too, each pair true of a tree it was measured on, the
last of which — `a9b3b90c` — **is not an object in this repository at all**
(`git cat-file -t a9b3b90c` answers *Not a valid object name*), so that figure
is a record and not a reading anyone can re-run. **Every figure here is measured
by running the runner on the tree it is written about**, in a real
`git worktree` rather than differenced, because `test_measure_index_repair_visibility.py`
skips three cases where the clone is shallow and a `git archive` extraction is
exactly that. **The red set is still one suite, on every tree in this note and
neither side's doing**: `ec/tools/test_check_cluster_citations.py`, 48 tests, on
the same `:220` of the same #822 file with the same two `0x0464`/`0x0465`
disagreements — it fails identically on a pristine `git archive origin/main`
extraction — so neither #845 nor #974 nor #1009 caused it and none of them fixes
it.)*
*(Superseded a third time, by #1034, and **this is the first supersession in
this run whose step is cases on a suite already in the base** rather than a new
suite, so the suite count does not move: `origin/main` at `d3304785` reads
**`43 suite(s) run, 1301 tests`** and this tree reads
**`43 suite(s) run, 1307 tests`**, the step being six cases added to
`ec/tools/test_check_history_checkouts.py` and nothing else, so
`1301 + 6 = 1307` and `forty-three` is unchanged by it. **Every figure here is
measured by running the runner on the tree it is written about** and not
differenced, the reason the note above gives, on a working tree whose clone is
full — `git rev-parse --is-shallow-repository` answers *false* — so the three
cases `test_measure_index_repair_visibility.py` skips on a shallow one did run.
**The red set is still one suite, and #1034 neither caused it nor fixes it**:
`ec/tools/test_check_cluster_citations.py` alone, on the same `:220` of the same
#822 file, so the "one or more FAILED" the runner prints is that suite and not
this change's. The `1301` and the `997` the tenth note records stay written
above, each true of the tree it was measured on, per
[`../findings.md`](../findings.md) §4a-4d. **One citing line moved
rather than one pin being added**, which is the same step in the other
direction: this change's amendment to `history-checkout-claims.md` is eleven
lines above a pin of that file's, so its row in
[`test-line-pin-census.md`](test-line-pin-census.md)
was repointed from `:252` to `:262` and the reconciled count did not move — no
pin was added, so 107 rows answer 107 records as they did before. **This note
cost a second repoint, and of this file's own pin**: the row in the same table
for the `test_xdata_cluster_names.py` claim this file records moved `:341` →
`:370` under it — twice, the second being this note recording the first — which
the row itself now says in its verdict cell, in the established style. **The `106`
that suite's own row and that suite's docstring superseded at #778's merge is
left as it stands**; it is not this step's figure and no note here revises it.)*
*(Superseded a fourth time, by the `#1034` × `#1035` merge, and **this is the
first supersession in this run whose step is one case on a suite both sides
already had in the base**: `origin/main` at `fe92940a` (#1034's) reads
**`43 suite(s) run, 1307 tests`** and the merged tree reads
**`43 suite(s) run, 1308 tests`**, the step being #1034's six cases *and*
#1035's one, both on `ec/tools/test_check_history_checkouts.py` and nothing
else, so `1307 + 1 = 1308` and `forty-three` is still unchanged by it. The two
sides touched that one suite from opposite ends and neither side's figure is
the merged tree's: #1034's `1307` counted six cases against a base of `1301`
and #1035's `1301` predates them, so **the step is the sum of the two and
neither branch's arithmetic is a reading of this tree** — which is what the
`§4a-4d` rule above is for, and why all three figures stay written where they
are. **Every figure here is measured by running the runner on the tree it is
written about** and not differenced, on a working tree whose clone is full —
`git rev-parse --is-shallow-repository` answers *false* — so the three cases
`test_measure_index_repair_visibility.py` skips on a shallow one did run.
**The red set is unchanged, pre-existing, and neither side caused it or fixed
it**: `ec/tools/test_check_cluster_citations.py` alone, on the same `:220` of
the same #822 file, and it fails identically on a pristine
`git archive origin/main` extraction. **This note cost an eleventh
re-registration of this file's own pin**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records moved `:370` →
`:399` under it, by a note about a test total and not by anything to do with
that claim — **one move and not the pair #1034's cost**, because the shift this
note records was written correct the first time rather than corrected beside
itself, so nothing here moved the pin twice. **No pin was added, so the
reconciled count did not move**: 107 rows answer 107 records as they did
before.)*
*(Superseded a fifth time, by the `#1034` × `#1035` × `#1038` merge, and **the
reason this step is not the note above's is a `main` that has moved past the
pair both sides of it name**: `origin/main` at `8c51e6ed` (#1038's) reads
**`43 suite(s) run, 1308 tests`** and `1004` from
`python3 -m unittest discover -s ec/tools`, and this tree reads
**`43 suite(s) run, 1309 tests`** and `1005` from the same command, the step
being #1035's one case on `ec/tools/test_check_history_checkouts.py` and nothing
else, so `1308 + 1 = 1309` and `forty-three` is still unchanged by it. **The two
`1308`s are two different trees and the agreement is a coincidence rather than a
reading**, which is the one shape these notes have not carried yet and is worth
naming: #1038 added a case to `ec/tools/test_check_citation_lines.py` and did
not re-transcribe the totals, so **`main` measures `1308` while its own copy of
this file still reads `1307`** — and #1035's branch reached the same `1308` by
another route, off the `1307` #1034 left. **Neither figure is this tree's** and
the sum is, per [`../findings.md`](../findings.md) §4a-4d, so the `1308`
the note above wrote stays written where it is — true of the tree it was measured
on, and not this tree's by arithmetic. **Every figure here is
measured by running the runner on the tree it is written about** and not
differenced, the reason the notes above give, on a working tree whose clone is
full — `git rev-parse --is-shallow-repository` answers *false* — so the three
cases `test_measure_index_repair_visibility.py` skips on a shallow one did run.
**The red set is unchanged, pre-existing, and no side of this merge caused it or
fixed it**: `ec/tools/test_check_cluster_citations.py` alone, on the same `:220`
of the same #822 file, and it fails identically on a pristine `origin/main`
worktree that reads `1308` too — the two readings differing by the one case
under test and by nothing else. **This note cost a twelfth re-registration of
this file's own pin**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records moved `:399` →
`:431` under it, by a note about a test total and not by anything to do with that
claim. **No pin was added, so the reconciled count did not move**: 107 rows
answer 107 records as they did before.)*
*(Superseded a sixth time, by #1037 landing on `main` beside #1035 and #1039,
and **this is the first supersession in that run to move the suite count rather
than a case count**: the base this merge measures from, `8c51e6ed`, reads
**`43 suite(s) run, 1308 tests`** and `1004` from
`python3 -m unittest discover -s ec/tools`, `origin/main` at `5244f119` reads
**`43 suite(s) run, 1309 tests`** and `1005`, and this tree reads
**`44 suite(s) run, 1316 tests`** and `1012`, the step being one new suite
`ec/tools/test_check_history_checkouts_run.py` at seven cases, so
`1309 + 7 = 1316` and `forty-three` → `forty-four` is #1037's alone — the one
case `main` gained over the base is
`test_the_table_turns_red_on_each_of_the_two_edits_it_exists_for` in
`ec/tools/test_check_history_checkouts.py` (30 → 31, measured by diffing the
two files' `def test_` lists), and a case on a suite already counted is not a
suite. **The branch this note came from measured against a `main` that has
since moved**, so its `43`/`1308`, `1004` and `1315` are left written where the
thirty-sixth note writes them, each true of the tree it was measured on, per
§4a-4d; **`1315` is this landing's own branch's figure and `1316` is this
tree's**, and the difference is that one case landing on `main` beside it, not
a disagreement. **The `1307` the third note records was
exactly right for the tree it was written on** — re-measured at `fe92940a`,
#1034's own commit, which reads `43`/`1307` and `1003` — and `8c51e6ed` reads
`1308`/`1004` rather than that because **#1038 landed on top of it** and added
`test_a_correction_marker_inside_a_yaml_entry_is_still_checked` to
`ec/tools/test_check_citation_lines.py`: one case, on a suite #1034 had already
counted, so `1307 + 1 = 1308` is #1038's step and not a correction of #1034's.
**The red set is unchanged across all of them**:
`ec/tools/test_check_cluster_citations.py` alone, and none of #1035, #1038,
#1039 or #1037 causes or fixes it. **This note cost a thirteenth re-registration
of this file's own pin**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records moved `:431` →
`:467` under it, by a note about a test total and not by anything to do with
that claim, and **one move and not a pair** — the shift this note records was
written correct the first time, the way the fifth note's was. **No pin was
added, so the reconciled count did not move**: 107 rows answer 107 records as
they did before.)*
*(Superseded a sixth time, by #1032, and **the `1307` the third note above
carries was already one behind its own tree when that merge found it** —
measured, not differenced, on a
clean worktree of each side: `d3304785` (#1009's) reads **`43` / `1301`**,
`fe92940a` (#1034's) reads **`43` / `1307`**, `origin/main` at `8c51e6ed` reads
**`43` / `1308`**, and the branch's tree reads **`43` / `1316`**. So the `1307` is true
of `fe92940a` and not of `main`'s tip, the one case being #1038's addition to
`ec/tools/test_check_citation_lines.py`, and the step this merge records is
`1308 + 8 = 1316`: eight cases on `ec/tools/test_check_history_checkouts.py`
(30 → 38), which is the whole difference between the two trees' per-suite
counts — every other suite reads the same number on both sides — and so
`forty-three` is unchanged by it a second time running. The `1301`, the `1307`
and the `1301` the tenth note records stay written where each was measured, per
[`../findings.md`](../findings.md) §4a-4d. **One citing line moved
again rather than one pin being added**: this merge's amendment to
`history-checkout-claims.md` is *above* the pin of that file's and is the whole
of the step, so the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
reads **`:278`** — `262` on `main` and `278` on the branch, which agree — and the
reconciled count did not move: 107 rows
answer 107 records as they did before. **The red set is still one suite, and
#1032 neither caused it nor fixes it**: `ec/tools/test_check_cluster_citations.py`
alone, on the same `:220` of the same #822 file, re-checked on a clean
worktree of `origin/main` at `8c51e6ed` and on the branch's, red with the
identical message in both.)*
*(Superseded a seventh time, by the `#1034` × `#1035` × `#1038` × `#1032` merge,
and **this is the first supersession in this run with a change on the branch side
and another on the `main` side touching the same suite**: `origin/main` at
`5244f119` (#1039's) reads **`43 suite(s) run, 1309 tests`** and `1005` from
`python3 -m unittest discover -s ec/tools`, and this tree reads
**`43 suite(s) run, 1317 tests`** and `1013` from the same command, the step being
#1032's eight cases on `ec/tools/test_check_history_checkouts.py` (31 → 39) and
nothing else, so `1309 + 8 = 1317` and `forty-three` is still unchanged by it a
third time running. **Neither side's figure is a reading of this tree and the sum
is**, and that is the first time in this run the two sides of one step have
touched the same suite rather than two different ones: #1039's `1309` counted one
case against the `1308` #1034 left and #1032's `1316` counted eight against that
same `1308`, so both arrive at the merged tree from a common base neither could
see. All four figures stay written where each was measured, per
[`../findings.md`](../findings.md) §4a-4d. **Every figure here is
measured by running the runner on the tree it is written about** and not
differenced, the reason the notes above give, on a working tree whose clone is
full — `git rev-parse --is-shallow-repository` answers *false* — so the three cases
`test_measure_index_repair_visibility.py` skips on a shallow one did run. **The
red set is unchanged, pre-existing, and no side of this merge caused it or fixed
it**: `ec/tools/test_check_cluster_citations.py` alone, on the same `:220` of the
same #822 file, and it fails identically on a clean `origin/main` worktree at
`5244f119` that reads `1309` too — the two readings differing by the eight cases
under test and by nothing else. **This note cost this file's own pin two cells
rather than one**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records reads **`:490`**
here, where `main`'s copy reads `:431` and the branch's reads `:394` — `:431 + 25
= :456` is #1032's sixth note landing above it on this tree, and `:456 + 34 =
:490` is this note — the thirteenth and fourteenth re-registrations, two notes
about test totals having moved it and nothing about the
`test_xdata_cluster_names.py` claim the row reconciles. **No pin
was added, so the reconciled count did not move**: 107 rows answer 107 records as
they did before.)*
*(Superseded an eighth time, by the `#1037` × `#1032` merge, and **this is the
first note in this chain whose tree is not one the runner can total at all**,
which is a fact about the command the sentence above names rather than about
either side's arithmetic.** `origin/main` at `560752b2` measures **`46
suite(s) run, 1429 tests`** and `1067` from
`python3 -m unittest discover -s ec/tools`, and this tree measures **`46
suite(s) run, 1437 tests`** and `1075` from the same command, the step being
#1032's eight cases on `ec/tools/test_check_history_checkouts.py` (31 → 39) and
nothing else, so `1429 + 8 = 1437`, `1067 + 8 = 1075` and `forty-six` is
unchanged by it a fourth time running. **The `forty-four` and the `1316` the
sentence carries are left written where they were measured, and they are two
suites behind even `main`**: #1058 (`ec/tools/test_pd_image_census.py`, 55
cases) and #1060 (`bios/tools/test_ifr_census.py`, 58 cases) each committed a
suite and neither re-transcribed the total, so `1316 + 55 + 58 = 1429` and
`44 + 2 = 46` is the shape of the drift, per
[`../findings.md`](../findings.md) §4a-4d — **which is also why
the figure above is the first one in this chain read off a run rather than off
a side's own sentence.**

**The runner does not print that total, and does not print one at all on this
tree.** `tools/run-tests.sh:73` adds every `Ran N test` line its `sed` finds,
and `ec/tools/test_pd_image_census.py` runs nested unittests whose transcripts
reach the same stream, so `n` holds three numbers and the arithmetic dies on it
— `tools/run-tests.sh: line 73: tests + 1`, then `1`, then `55: syntax error in
expression`. The loop counts the suite before it tallies, so the run dies on the
twenty-eighth and the `28 suite(s) run, 911 tests` printed on the way out is the
twenty-seven ahead of it — the same twenty-seven on `origin/main`, which dies at
`903`. **Every figure in this note was therefore measured by the runner's own
loop with the last `Ran` line taken rather than every one, per file**, on full
clones of both sides (`git rev-parse --is-shallow-repository` answers *false*),
and the `46` is the 46 `test_*.py` files `find` returns — the runner's own rule,
and the one `tools/test_readme_suite_table.py` checks the table's first column
against. *(That count is `47` on the tree this note was measured on, `46 + 1`
for #54's `ec/tools/test_paged_trampoline_framing.py`; the `46` stays written
because the figures around it were measured on the tree that had it. **On the
tree this lands in it is `49`, `47 + 2`**, the two being #40's
`ec/tools/test_walk_flow_follow.py` and #54's, and this note's own `46` is three
behind it — the same standing the note above records for the lead's figures,
each true of the tree it was measured on per
[`../findings.md`](../findings.md) §4a-4d.)*

**The red set on this tree is four suites and none of the four is this
merge's**: `ec/tools/test_check_cluster_citations.py` (the long-standing one, on
the same `:220` of the same #822 file),
`ec/tools/test_check_doc_figure_pins.py`
(`test_a_hex_address_is_not_a_figure_and_the_run_beside_it_is`),
**`ec/tools/test_check_pin_table_rows.py`, which is three cases rather than one
and is the fourth suite for a reason worth naming — it reconciles
[`test-line-pin-census.md`](test-line-pin-census.md),
the very file this merge's note edits, so the omission was in a checker over a
file this change touches rather than over an unrelated one**:
`test_the_committed_table_reconciles_and_exits_zero` (`rc 1 != 0`, six
unplaced-row/row-without-record pairs),
`test_the_committed_table_places_something` (`101 != 107`) and
`test_every_class_is_zero_on_the_committed_tree`; and
`tools/test_readme_suite_table.py`
(`test_every_discovered_suite_has_a_row`), red because #1058 committed a suite
without the table row that test asks for. All four fail identically on a clean
`origin/main` worktree at **`58f43ee7`**, which is both that worktree's tip and
this branch's own merge base — measured there rather than carried, and the runner
aborts on both trees — so the set is `main`'s and this merge neither grew nor
shrank it. **None of the four is repaired here**: the missing row is #1058's to
write, the other three are not this merge's to move, and a merge that quietly
repaired them would leave the next reader unable to tell which of the
four were ever green.)*

*(Superseded a seventh time, at the `#1008` × `#1009` merge, **renumbered from
the fourth its own branch gave it because `main` held that number first with two
of its own, the same collision the thirty-sixth note records from the other
direction and the same rule: the one `main` held first keeps it. Every figure in
it stays as it was measured on the `#1008` × `#1009` tree, per
[`../findings.md`](../findings.md) §4a-4d, and none of the four is
this tree's — the notes below carry what this tree reads — and **this is the
second merge in this run whose base is `main`'s tip rather than either side's
fork point** — #1013 and #1034 both landed on `main` after the `#1008` branch
forked, so `main` was carrying two summaries this branch never saw. **The step is
one suite and thirty-seven cases, and all of it is #1008's**: `origin/main` at
`fe92940a` reads **`43 suite(s) run, 1307 tests`** and **`1003`** from
`python3 -m unittest discover -s ec/tools`, both measured in a clean
`origin/main` worktree, and this tree reads **`44 suite(s) run, 1344 tests`** and
**`1040`**, so `1307 + 37 = 1344`, `1003 + 37 = 1040` and `43 + 1 = 44`, the
thirty-seven being #1008's `ec/tools/test_census_index_third_column_edits.py` and
nothing else. **#1008's own side read `43` / `1314` and `1010`**, off a fork
point of `5881153d` that `main` had already moved past, and that pair stays
written per [`../findings.md`](../findings.md) §4a-4d — it measures the
branch's tree and not this one, and **it is the first pair in this run the merge
had to supersede without adding anything to it**, because both `main` steps landed
on the far side of the base it was measured from. **The figures above are
re-derived by running the runner on this tree rather than by adding the two
sides up**, the rule the twenty-fifth note below states, and **every one of them
is measured by running the runner on the tree it is written about** on a working
tree whose clone is full — `git rev-parse --is-shallow-repository` answers
*false* — so the three cases `test_measure_index_repair_visibility.py` skips on a
shallow one did run. **The red set is one suite, and this merge was briefly the
reason it was two**: `ec/tools/test_check_cluster_citations.py` alone, 48 tests,
on the same `:220` of the same #822 file, failing identically on a pristine
`git archive origin/main` extraction, so neither #1008 nor #1013 nor #1034 caused
it and none of them fixes it; `ec/tools/test_check_pin_table_rows.py` read
`FAILED (failures=4)` while the `../../tools/README.md` row in
[`test-line-pin-census.md`](test-line-pin-census.md)
still named the line this file carried before the merge, and is green again with
the re-registered row — the property the re-registration is run for. **Six rows
of the per-pin table moved a citing line and no row was added**, which is
#1034's shape one merge later: #1008 put nine lines into `docs/findings.md` above
`§41`'s correction and eight more above `§47`'s, one into
`docs/agent-pipeline.md` and a block here, so **the census's `107` / `80` / `59`
are unmoved by it** — the same pins read at their new lines, none added and none
removed — and the six rows are re-registered to the measured values rather than
argued. **The `106` the note above records stays written**; #1013 and #1034
superseded it and this note is their successor.)*
*(Superseded an eighth time, at the `#1008` × `#1039` merge, and **the step is
one suite and thirty-eight cases, of which thirty-seven are #1008's and one is
#1039's** — the first note here whose step belongs to neither side alone.
`origin/main` at `5244f119` reads **`43 suite(s) run, 1309 tests`** and **`1005`**
from `python3 -m unittest discover -s ec/tools`, both measured by running the two
commands in a clean `origin/main` worktree, and this tree reads
**`44 suite(s) run, 1346 tests`** and **`1042`**, so `1309 + 37 = 1346`,
`1005 + 37 = 1042` and `43 + 1 = 44`: the thirty-seven are #1008's
`ec/tools/test_census_index_third_column_edits.py` and nothing else, and the one
is #1039's case on `ec/tools/test_check_history_checkouts.py`, which landed on
`main` after the `#1008` branch forked and so is in this tree's base rather than
in either side's step. **The sixth note's `1344` and `1040` stay written and are
not this tree's**, true of the `#1008` × `#1009` tree per
[`../findings.md`](../findings.md) §4a-4d, as do the fifth's `1309` and
`1004` and the branch's own `1345` and `1041`. **Every figure here is measured by
running the runner on the tree it is written about** and not differenced, the rule
the notes above give, on a working tree whose clone is full —
`git rev-parse --is-shallow-repository` answers *false* — so the three cases
`test_measure_index_repair_visibility.py` skips on a shallow one did run.
**The red set is one suite, pre-existing, and no side of this merge caused it or
fixed it**: `ec/tools/test_check_cluster_citations.py` alone, 48 tests, on the
same `:220` of the same #822 file, failing identically in the clean `origin/main`
worktree above. **This note cost a re-registration of this file's own pin**: the
row in [`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records moved `:431` →
`:575` under it, by two notes about the suite totals and not by anything to do
with that claim — **one move and not a pair**, because both notes recorded their
own shift correctly the first time. **No pin was added, so the reconciled count
did not move**: 107 rows answer 107 records as they did before.)*
*(Superseded a ninth time, at the `#1008` × `#1037` merge, and **the step is one
suite and thirty-seven cases on each side at once — the first note here whose
figures are half one landing's and half the other's, and the second in this run
with a `test_*.py` on both sides.** `origin/main` at `f6480168` (#1037's) reads
**`44 suite(s) run, 1316 tests`** and **`1012`** from
`python3 -m unittest discover -s ec/tools`, both measured by running the two
commands in a clean `origin/main` worktree, and this tree reads
**`45 suite(s) run, 1353 tests`** and **`1049`**, so `1316 + 37 = 1353`,
`1012 + 37 = 1049` and `44 + 1 = 45`: the thirty-seven are #1008's
`ec/tools/test_census_index_third_column_edits.py` and nothing else, and **#1037's
seven are already inside this tree's base rather than in either side's step**,
for the reason the eighth note gives for #1039's one case. **The eighth note's
`1346` and `1042`, the seventh's `1344` and `1040`, and the sixth's `1316` and
`1012` stay written** and none of them is this tree's, each true of the tree it
was measured on per [`../findings.md`](../findings.md) §4a-4d.
**Every figure here is measured by running the runner on the tree it is written
about** and not differenced, the rule the notes above give, on a working tree
whose clone is full — `git rev-parse --is-shallow-repository` answers *false* —
so the three cases `test_measure_index_repair_visibility.py` skips on a shallow
one did run. **The red set is one suite, pre-existing, and no side of this merge
caused it or fixed it**: `ec/tools/test_check_cluster_citations.py` alone, 48
tests, on the same `:220` of the same #822 file, failing identically in the clean
`origin/main` worktree above. **`ec/tools/test_check_pin_table_rows.py` was the
second red suite and is the one this merge had to fix rather than carry**: it read
`FAILED (failures=1)` on the `../../tools/README.md` row, whose citing line this
merge moved to the value the census reports on this tree, and it is green with
the re-registered row — the property the re-registration is run for.
**`ec/tools/test_check_pin_table_by_cited_file.py`'s pinned triple moves to a
figure neither side held**, `45` indexed / `12` named / `33` named by none,
because both suites join the tail and neither is named by a pin, so the named
count holds at the `12` both sides read and only the tail's own figure moves.
**This note cost a re-registration of this file's own pin**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records is re-registered to
the line this tree carries, by three supersession notes and not by anything to do
with that claim. **No pin was added, so the reconciled count did not move**: 107
rows answer 107 records as they did before.)*
*(Superseded a tenth time, at the `#1008` × `#1060` merge, and **it is the first
supersession here whose two figures could not be read off one run of
`tools/run-tests.sh`, because that runner no longer finishes on either tree.**
`ec/tools/test_pd_image_census.py` — #1058's, `517be444` — runs two further
suites as subprocesses to prove it can see a red one, so it prints **three**
`Ran N tests` lines where the runner's tally expects one: `n` comes back
multiline and `tests + ${n:-0}` on `tools/run-tests.sh`:73 is a shell syntax
error, so the run aborts at `ec/tools/test_measure_index_repair_visibility.py`
with `28 suite(s) run, 903 tests` on `main` and `29` / `940` here and prints no
total at all. **That is `main`'s and not this merge's** — a clean `origin/main`
worktree at `560752b2` aborts on the same line with the same error — and it is
**not fixed here**, the arithmetic being `main`'s to change rather than a
landing's to carry; it is named here for the follow-up pass. **So the two
figures above are counted by running every suite the way the runner does and
summing, and the `ec/tools` figure by `python3 -m unittest discover -s ec/tools`
which still prints normally.** `origin/main` at `560752b2` (#1060) reads
**`46`** suites, **`1429`** tests and **`1067`**, and this tree reads **`47`**,
**`1466`** and **`1104`**: `1429 + 37 = 1466`, `1067 + 37 = 1104` and
`46 + 1 = 47`, and the thirty-seven and the one are #1008's
`ec/tools/test_census_index_third_column_edits.py` and nothing else.
**`main`'s own `forty-four` / `1316` / `1012` were already stale on `main` by two
suites and a hundred and thirteen tests** — `517be444` (#1058) and `560752b2`
(#1060) each landed a suite in this window, #1058's at 58 cases and #1060's at
55 — so **none of that gap is this merge's to attribute**; the ninth note's
`45` / `1353` / `1049` and its `1316` / `1012` stay written, each true of the
tree it was measured on per [`../findings.md`](../findings.md)
§4a-4d, and so does every figure the notes above them record.

**The red set is three suites, all pre-existing, and every one of them fails
identically in the clean `origin/main` worktree above, so none of them is this
merge's and none is fixed by it**: `ec/tools/test_check_cluster_citations.py` —
48 tests, the same single failure on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md`; `ec/tools/test_check_doc_figure_pins.py`
— 44 tests, `test_a_hex_address_is_not_a_figure_and_the_run_beside_it_is` at
`:304` wanting `86` **unheld** where the run says **held-by-check-literal**; and
`tools/test_readme_suite_table.py` — 6 tests,
`test_every_discovered_suite_has_a_row` naming **#1058's
`ec/tools/test_pd_image_census.py`**, which is #1058's own landing adding a suite
and not the row that goes with it. **The third is the runner's broken arithmetic
and this suite's red row being the same landing**, and both are named rather than
fixed here for the reason the paragraph above gives.
**`ec/tools/test_check_pin_table_by_cited_file.py`'s pinned triple moves to a
figure neither side held** — `47` indexed / `12` named / `35` named by none —
and the merge is what makes it neither: `main` at `560752b2` reads exactly
`46` / `12` / `34` with the pin already set to it, and #1008's suite is indexed
and named by no committed pin, so the tail takes it. **No pin was added, so the
reconciled count did not move**: 107 rows answer 107 records as they did before.)*
*(Superseded by the `#1008` × `#1032` × `#1033` merge, and **this is the first
supersession in this run with a suite on both sides of it in the same window, so
the two chains of ordinals above run into each other and both are left written.**
`main`'s chain reads *sixth*, *seventh*, *eighth* and #1008's reads *seventh*,
*eighth*, *ninth* and *tenth*, each headed by the merge it describes, so the
merged file carries two `*(Superseded a seventh time...)*` notes and two
`*(...an eighth time...)*` notes rather than one of each. **That is not a
renumbering anybody can perform**, because the ordinals are cited by position
elsewhere in this file — *"the thirty-sixth note"*, *"the twenty-fifth note
below"* — and moving one would break a reference that is itself a record. **So
the merged tree's figures are stated here once and the two chains are left as
each side wrote them**, per [`../findings.md`](../findings.md) §4a-4d:
`origin/main` at `560752b2` reads **`46` suites, `1429` tests** and `1067` from
`python3 -m unittest discover -s ec/tools`, #1008's branch reads **`47`**,
**`1466`** and **`1104`**, `origin/main` at `48887fa0` reads **`46`** and
**`1437`**, and **this tree reads `47` suites, 1474 tests and `1112`** —
`1437 + 37 = 1474`, `1075 + 37 = 1112` and `46 + 1 = 47`, and the whole
thirty-seven and the one are #1008's
`ec/tools/test_census_index_third_column_edits.py` at thirty-seven cases and
nothing else — **#1032's eight on
`ec/tools/test_check_history_checkouts.py` (31 → 39) are already inside
`48887fa0`'s `1075`, which is the point the two chains meet at**. **Neither
side's total is this tree's and the arithmetic from `origin/main` is**: #1008's
`1466` was
`1429 + 37` off a base that had not taken #1032's eight, and `main`'s own
`1437` is `1429 + 8`, the same `+8` counted from the other side. **The two
chains' intermediate figures — the `forty-four`/`1316`/`1012`, the `45`/`1353`/
`1049`, the `46`/`1429`/`1067` and the `47`/`1466`/`1104` — all stay written
where each was measured on**, and the `forty-six` and the `1437` the sentence
carried until this note are `48887fa0`'s own.

**The two figures are counted the way the branch's tenth note counts them and not
by reading one run**, because `tools/run-tests.sh` still aborts on
`ec/tools/test_pd_image_census.py`'s three `Ran` lines — `main`'s arithmetic, and
`48887fa0` aborts on the same line with the same error. **`1112` is
`python3 -m unittest discover -s ec/tools`, which prints normally**, and `1474`
is the sum over the same per-file loop the runner runs, taking each suite's own
last `Ran` line rather than every one.

*(Superseded at the `#1008` × `#873` merge, and **the suite count is the only
figure of the three this merge can re-measure**, so the note says half of what
its predecessors say. **`forty-seven` → `forty-eight`**, counted two independent
ways — `find . -name 'test_*.py'` and the `48 indexed test file(s)` that
`ec/tools/check_pin_table_by_cited_file.py` prints — against `47` on
`origin/main` at `5672042a` and `47` on #873's own branch, so **the `+1` is
#873's `ec/tools/test_check_eq_guard_citations.py` alone** and this tree carries
#1008's `ec/tools/test_census_index_third_column_edits.py` as well. **The test
total is not restated and `1474` stays written where it stands**: the runner
aborts before printing one for the reason the paragraph above gives, so this tree
has no figure the way this chain counts one, and a number derived any other way
would be a different measurement wearing this one's name. The chains are left as
each side wrote them, per [`../findings.md`](../findings.md) §4a-4d, and
the full re-run is
[`test-line-pin-census.md`](test-line-pin-census.md).)*

*(Superseded at the `#1008` × `#1030` × `#873` merge, and **this is the first
supersession in this run on a tree where the runner reaches a total, so all three
figures are restated and the test total this chain has declined to name since the
`#1008` × `#1032` × `#1033` merge is named here.** **`forty-eight` →
`forty-nine`, `1551` tests, and `1189` from
`python3 -m unittest discover -s ec/tools`**, counted the way the notes above
count them — `origin/main` at `9bb8fca1` reads `48` suites, `1533` tests and
`1171`, so `1533 + 18 = 1551` and `1171 + 18 = 1189`, and the whole eighteen is
#873's `ec/tools/test_check_eq_guard_citations.py` and nothing else.** The `+1`
suite over each side is that side's counterpart and the two are different suites,
#40's `ec/tools/test_walk_flow_follow.py` and #873's, neither of them named by a
committed line pin for #811's reason the notes above give, so both sides reached
the same `48` while each was counting a landing the other had yet to make, and
that they agree is not a cross-check. **The note above's "`tools/run-tests.sh`
still aborts" is stale on this tree and stays written**, the runner having been
repaired on `main` at `86778274` — `sed … | tail -1` takes the suite's own summary
rather than every one, so `ec/tools/test_pd_image_census.py`'s three `Ran` lines no
longer stop the tally. The `forty-seven`, the `forty-eight` and the `1474` stay
written where they were written, each true of the tree it was measured on, per
[`../findings.md`](../findings.md) §4a-4d, and the full re-run is
[`test-line-pin-census.md`](test-line-pin-census.md).)*

**The red set is three suites and every one of them is pre-existing on both
sides, re-checked rather than carried**: `ec/tools/test_check_cluster_citations.py`
(48 tests, the same single failure on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md`), `ec/tools/test_check_doc_figure_pins.py`
(44 tests, `test_a_hex_address_is_not_a_figure_and_the_run_beside_it_is` at
`:304`), and `tools/test_readme_suite_table.py` (6 tests,
`test_every_discovered_suite_has_a_row` naming #1058's
`ec/tools/test_pd_image_census.py`). **None is fixed here and none is caused
here** — the third is #1058's row to write, and a merge that quietly repaired it
would leave the next reader unable to tell which of the three were ever green.
`ec/tools/test_check_pin_table_rows.py`, red with three failures on the merge
base `58f43ee7` and repaired on `main` by #1076, **is green here** and stays
green: the six rows this merge had to re-registered are re-registered to the
lines the tool reads, so 107 rows answer 107 records with all seven classes `0`.

**`ec/tools/check_pin_table_by_cited_file.py`'s pinned triple holds at `47`
indexed / `12` named / `35` named by none**, which is the figure the branch's
tenth note already reached from the other side and `main`'s `46` / `12` / `34`
does not, for the reason that note gives: #1008's suite is indexed and named by
no committed pin, so the tail takes it. **No pin was added, so the reconciled
count did not move**: 107 rows answer 107 records as they did before.)*

*(Superseded a ninth time, at the `#1042` × `#1035` × `#1038` × `#1039` ×
`#1030` merge, and **this is the first supersession in this run whose two sides
both wrote cases into a suite `main` already had, so the step is the sum of the
two and neither side's arithmetic is a reading of this tree**: `origin/main` at
`5244f119` reads **`43 suite(s) run, 1309 tests`** and this tree reads
**`43 suite(s) run, 1315 tests`**, so `1309 + 6 = 1315` and `forty-three` is
still unchanged by it, the six being #1030's six in
`ec/tools/test_check_history_checkouts.py` and nothing else — that suite
reading **31 cases on `main` and 37 here**, and both sides' additions landing in
it from opposite ends, `main`'s six #1042 cases in `ProseTests` and its own
`TheTwoEdits` class against #1030's six `ProseTests` cases and its new
`ec/tools/history_checkout_sites.py`. **`python3 -m unittest discover -s
ec/tools` agrees on the step and is where the six are counted**: `1005` on
`main`, `1011` here. **The red set is unchanged, pre-existing, and no side of
this merge caused it or fixed it**: `ec/tools/test_check_cluster_citations.py`
alone, 48 tests, on the same `:220` of the same #822 file with the same two
`0x0464`/`0x0465` disagreements, re-run here and on a pristine
`git archive origin/main` extraction and **identical once the traceback's
absolute tree path and the elapsed-time line are normalised** — the two fields
that differ on every run, so the raw outputs are not byte-identical, though the
suite, checker, CSV and prose are. The "one or more FAILED" the runner prints is
that suite and not this merge's. **One
row of the pin table moved rather than one pin being added**, and it is this
file's own corpus denominator's row rather than a claim's: the row for
`history-checkout-claims.md`'s single pin moved `:288` (on #1030's branch) and
`:262` (on `main`) to **`:298`**, the sum of the two sides' additions above it,
and the census re-run on this tree names `298`. **This note cost a fourteenth
re-registration of this file's own pin**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records moved `:431` →
`:463` under it, by a note about a test total and not by anything to do with that
claim — one move again rather than a pair, because this note records its own
shift the first time it is written. **No pin was added, so the
reconciled count did not move**: 107 rows answer 107 records, all 107 placed and
every class 0, as they did before.)*
*(Superseded a tenth time, at the `#1070` × `#1060` × `#1058` × `#1043` ×
`#1030` merge, and **this is the first supersession in this run whose step and
whose suite count come from different sides, so neither side's arithmetic is a
reading of this tree**: `origin/main` at `58f43ee7` reads
**`46 suite(s) run, 1429 tests`** and `1067` from
`python3 -m unittest discover -s ec/tools`, and this tree reads
**`46 suite(s) run, 1435 tests`** and `1073`, so `1429 + 6 = 1435` and
`1067 + 6 = 1073`, the six being #1030's six in
`ec/tools/test_check_history_checkouts.py` and nothing else — that suite reading
**31 cases on `main` and 37 here** — while **the suite count's step is `main`'s
and this landing's is none**: `44` → `46` is #1058's
`ec/tools/test_pd_image_census.py` and #1060's `bios/tools/test_ifr_census.py`
landing on `main` beside it, neither of which wrote a note here, so **the
`44`/`1316` and `1012` the sixth note records are `#1043`'s figures and this
landing's own branch read `43`/`1315` off a `main` carrying neither suite**.
#1030 adds no suite of its own — `ec/tools/history_checkout_sites.py` is a tool
one suite reads rather than a `test_*.py` — so a case on a suite already counted
is not a suite, and `forty-six` is `main`'s own figure. **The ninth note's
`1315` stays written beside the sixth's `1316`**, each true of the tree it was
measured on per §4a-4d as the `1309` and `1308` above them are, and this landing
is neither the `#1042` × `#1035` × `#1038` × `#1039` × `#1030` merge nor the one
the sixth note came from. **The red set is two suites, both re-checked rather
than carried and both red identically on a clean worktree of `origin/main` at
`58f43ee7`**: `ec/tools/test_check_cluster_citations.py` on the same `:220` of
the same #822 file every note above names, and
`ec/tools/test_check_doc_figure_pins.py`, the second **new since the sixth note
and #1058's rather than this landing's**. **A third was red on `main` and is not
red here**, `ec/tools/test_readme_suite_table.py` on #1058's suite having landed
with no row in the table below; that row is added and the runner's own crash on
the same suite is repaired, both in the thirty-seventh note below rather than in
this paragraph — the first because a suite table's row is the file's own
inventory, the second because this paragraph sits above the pin. **This note cost
a fifteenth re-registration of this file's own pin**: the row in
[`test-line-pin-census.md`](test-line-pin-census.md)
for the `test_xdata_cluster_names.py` claim this file records moved `:467` →
`:543` under it — seventy-six lines added above it by the ninth note and
this one, both about a test total and neither about that claim — and **one move
and not a pair** again, this note recording its own shift the first time it is
written, the way the fifth, sixth and ninth did. **No pin was added, so the
reconciled count did not move**: 107 rows answer 107 records, all 107 placed and
every class 0, as they did before.)*

*(Superseded at the `#1008` × `#1032` × `#1033` × `#1030` merge, and **this is
the third merge in this run whose two chains of ordinals run into each other,
and the first that collides at more than one ordinal** — the unnumbered
`#1008` × `#1032` × `#1033` note records a pair of `seventh`s and a pair of
`eighth`s, and this one adds a second `ninth` and a second `tenth`, so **the
merged file carries two notes at each of those four ordinals and none of the
eight is renumbered**. `#1008`'s chain reads *seventh* through *tenth* and then
an unnumbered note and #1030's reads *ninth* and *tenth*, each headed by the
merge it describes, and **the ordinals are cited by position elsewhere in this
file** — *"the thirty-sixth note"*, *"the twenty-fifth note below"* — so
renumbering one would break a reference that is itself a record. **Every figure
the sixteen notes above carry stays written where it was measured on**
([`../findings.md`](../findings.md) §4a-4d); none of them is this
tree's.*

**`bash tools/run-tests.sh` on this tree reads `47 suite(s) run, 1481 tests; one
or more FAILED**, and `python3 -m unittest discover -s ec/tools` reads `1119`** —
both re-measured here, on a full clone (`git rev-parse --is-shallow-repository`
answers *false*), for the reason the thirty-fifth note gives, and the runner
reaches a total at all because of the `tail -1` repair the thirty-seventh note
records, which came in with this landing. **`origin/main` at `5672042a` reads
`47` / `1474` / `1112`** and #1030's branch reads `46` / `1443` / `1081`, both
re-run on clean worktrees — `main`'s with this landing's runner, its own copy
aborting — so `1474 + 7 = 1481` and `1112 + 7 = 1119`, the seven being #1030's
seven in `ec/tools/test_check_history_checkouts.py` and nothing else, that suite
reading **39 cases on `main`, 45 on #1030's branch, and 46 on this tree**.

**The suite count's step is `main`'s and this landing's is none**, and that is the
one respect in which the two chains are not mirror images: `forty-six` →
`forty-seven` is #1008's `ec/tools/test_census_index_third_column_edits.py` at
thirty-seven cases, which `main` landed and #1030's branch never saw, while
#1030 adds none — `ec/tools/history_checkout_sites.py` is a tool one suite reads
rather than a `test_*.py`, and a tool is not a suite. **Neither side's arithmetic
is a reading of this tree, and this is the first step in that chain where one
side's tree *is* the other's base** rather than a fork neither could see: every
earlier collision added two deltas to a common ancestor, and this one adds #1030's
seven to a `main` that has itself already been merged with #1008, #1032 and #1033.
**The `forty-six` and the `1443` #1030's branch's own lead sentence carried, and
the `forty-seven` and the `1474` the unnumbered `#1008` note wrote are
`5672042a`'s**, each true of the tree it was measured on.

**The red set is two suites, and neither of the two is this merge's.** `ec/tools/test_check_cluster_citations.py` — 48 tests, the same single failure on the same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` — is the one every note above names and none of them fixes, and `ec/tools/test_check_doc_figure_pins.py` is the second, 44 tests, `test_a_hex_address_is_not_a_figure_and_the_run_beside_it_is` at `:304` reading `86` as `held-by-check-literal` where it wanted `unheld`, which is **#1058's** disagreement on its own `pd-image.md` figure rather than anything here. **A third is red on `main` and is not red here** — `tools/test_readme_suite_table.py`, on #1058's suite landing with no row in this file's table below, and the row came in with this landing — and `ec/tools/test_check_pin_table_rows.py` is green on both sides' trees and stays green here **only because the row below is re-registered to the line this tree carries**: it reconciles [`test-line-pin-census.md`](test-line-pin-census.md), the very file this merge's census row edits, so a tree carrying either side's `:873` or `:660` against this file's own lines would take it red. **That is the property the re-registration is run for, and neither of the two reds is fixed here or caused here** — the first is #822's to fix, the second is #1058's reading of its own page, and a merge that quietly repaired them would leave the next reader unable to tell which were ever green.

**The census and its two neighbours are re-run rather than carried.**
`census_test_line_pins.py` reads **107 pins in 29 markdown files, 80 spellings,
59 targets, 75 resolves against 32 declined, the `0/15/22/5/33` split, over `182`
markdown files read and `47` test files**; `check_pin_table_by_cited_file.py`
reads **47 indexed / 12 named / 35 named by none**; and `check_pin_table_rows.py`
reads **107 rows, 107 records, 107 placed, all seven classes 0**. **The pin,
spelling, target, verdict and shape counts are unmoved by either side's step**,
which is what keeps the 107-row table reconciling at 107: `main` reads `181`
markdown files against this tree's `182`, the step being #1030's own
`history-checkout-site-identity.md` for the third time and not one record, and
both read `47` test files. **The index triple moves to `47` / `12` / `35` and no
column crosses a table** — #1008's suite is indexed and named by no committed
pin, so the named count holds at the `12` both sides read and only the tail's
own figure moves, the cheap direction the thirty-ninth note describes.

**One row of the per-pin table moved rather than one pin being added, and it is
a re-registration of a citing line.** `tools/README.md`'s own row reads `:873`
on `main` and `:660` on #1030's branch and **`:1026`** here, a third figure
neither side held: **`873 + 76 + 74 + 3 = 1026`** from `main` and
**`660 + 289 + 74 + 3 = 1026`** from the branch, the `76` #1030's two supersession
paragraphs at the head of this file, the `74` this note, the `3` the blank lines
separating the two chains, and the `289` `main`'s own step from `:584` read whole.
**The `history-checkout-claims.md` row is the one row here that did *not* move**,
and naming that is worth more than a second figure would be: it reads `:291` on
`main` and **`:327` on both #1030's branch and this tree**, so a merge that
re-registered rows by rule would have written a line no tool placed.
**That is the nineteenth re-registration for the `tools/README.md` row by either
side's count, and the fifth in a row that is a `suite totals` re-registration
rather than one of the claim it reconciles** — the `:490`, the `:584`, the `:695`
and the `:873` and the `:1026` are all a note about how many tests the runner
ran, and not one about the claim. The move is re-run rather than differenced:
`check_pin_table_rows.py` places all 107 with it, seven classes `0`.
*(The `1161` this sentence carried until #794, the `1165` it carried on #794's
own branch, the `1168` it carried at the `#962` × `#794` merge, the `1180` the
#979 branch proposed, the `1182` the #974 branch proposed beside it, the `1187`
#780's own branch carried, the `1211` the `#979` × `#985` merge re-derived it to,
the `1216`, `1221`, `1233`, `1238` and `1243` the four two-sided merges before
`#974`'s measured between them, the `1248` and `1264` that merge's own two sides
measured apart, the `1269` the two commands read on the `#978` × `#974` tree, the
`1270` and `1272` this merge's own two sides measured apart in their turn, are
all left visible per
[`../findings.md`](../findings.md) §4a-4d, each true of the tree it
was measured on: `1161 + 4 = 1165` and `1164 + 4 = 1168` are the four cases
`ec/tools/test_check_testdata_row_claims.py` gained, `1177 + 31 + 3 + 10 =
1221` is the `#979` × `#985` merge's arithmetic — `1177` being what `main` itself
reads at `368e9e52`, not the `1168` the sentence carried, so that step is off
`main` and not off the value above — with its four parts being #985's
thirty-one cases and its new `ec/tools/test_disasm8051_oracle.py`, #979's three
in `ec/tools/test_check_testdata_row_claims.py` and #780's ten in
`ec/tools/test_check_testdata_index.py`, `1233 + 10 = 1243` is the
`#979` × `#973` × `#780` merge's, the ten being #780's again in the same suite
and the suite count unmoved at the `40` `main` already read — the same fact the
twenty-third note states about its own step — and **`1233 + 10 + 5 = 1248` is
#974's side of the `#780` × `#974` merge**, the ten again #780's ten in that same
suite and the five #974's five in `ec/tools/test_check_testdata_row_claims.py`,
**with the suite count unmoved at the `40` `main` already read on *both* sides** —
the count moves on #985's side at the twenty-second note, on #973's at the
twenty-third, and on neither side there, which is the same fact the twenty-third
note states about its own step and the twenty-ninth about #974's, so **the two
merges that first put a suite on this sentence each put theirs on the side their
counterpart had none, and neither figure is derived by adding the other's**.
**The `1238` and the `1243` are the `#780` × `#974` merge's two sides measured
apart, each adding only its own contributor to the `1233` the two shared, and the
`1248` is the one figure there that added both** — measured by running the runner
on that tree first and written down afterwards, the rule the twenty-fifth note
below states and the thirty-first applies. **`1243 + 21 = 1264` is `#978`'s side
of the `#978` × `#974` merge** and `1233 + 10 + 5 = 1248` is the other's, both
left written where each was measured per
[`../findings.md`](../findings.md) §4a-4d. **#1008's own tree's
figures are `1314` and `1010` over forty-three suites, re-derived by running both
commands on it rather than by adding the two sides up, and that merge is the
first in this run that put a `test_*.py` on *both* sides at once**: #845's
`ec/tools/test_trace_xdata_refs.py` at six cases and #1008's
`ec/tools/test_census_index_third_column_edits.py` at thirty-seven. **Its base was
`main`'s, and the tip at the time rather than the branch's fork point** — a clean
`origin/main` worktree at `5881153d` measured `1277` and `973` over forty-two
suites, so `1277 + 37 = 1314` and `973 + 37 = 1010` and the suite count's step was
`42` → `43`, the thirty-seven being #1008's suite and nothing else. **The same
three figures were additive from the other side as well, which is the first time
on this sentence that they are**: the branch's own `1308` and `1004` plus #845's
six is `1314` and `1010` too, so that merge had no figure to choose between and
the sentence above is a re-derivation rather than a pick. **On this tree the
figures are `1346` and `1042` over forty-four suites, and none of the numbers
above is one of them** — #1013, #1034, #1035, #1038 and #1039 all landed on
`main` after that fork point, so the merged tree adds to `5244f119`'s `1309` and
`1005` and not to `fe92940a`'s `1307` and `1003`, nor to `5881153d`'s `1277` and
`973`; the sixth note under the sentence above carries the arithmetic and both
bases for the `#1008` × `#1009` tree, and the seventh carries this one's. **Main's own version of the sentence the paragraph above replaces
is left written here, per [`../findings.md`](../findings.md) §4a-4d,
each claim of it true of the tree it was measured on**: *"**This tree's figures
are `1277` and `973`, re-derived by running both commands here rather than by
adding the two sides up**: a clean `origin/main` worktree at `0daac768` measures
`1271` and `967`, so `1271 + 6 = 1277` and `967 + 6 = 973`, the six being #845's
six in its new `ec/tools/test_trace_xdata_refs.py` and nothing else"*; *"**The
`1271` and `967` this sentence carried until now are therefore not superseded at
all — they are the base this merge adds to**, and the arithmetic above is the one
a reader can reproduce from `origin/main` as it stands"*; and *"**Each of the two
`+1` steps is one-sided, and this merge is the first with a suite on either side
of it**: #978's suite is the only `test_*.py` the `#978` × `#974` merge added and
#845's is the only one this one did, so the thirty-first's own figure would have
read `40` and `1248` where this one reads `42` and `1277`, and a run that had
taken the thirty-second's side rather than this one would have read `41` and
`1271` — the same one-sidedness the twenty-second and twenty-third notes record,
and the reason `test_readme_suite_table.py`'s set check needed no correction on
either branch and needs none here either."* **That last one is superseded in its
turn and is the reason this paragraph exists in the shape it does**: the
`#1008` × `#845` merge is a later tree, its step is one-sided as the four before
it were, and the merge *around* it now has a suite on both sides again — so
"the first merge in this run with a suite on either side of it" is true of the
`#845` × `#974` tree and of no tree after it, and the paragraph above says which
merge is which.

**Both sides' own figures stay written where each was measured**, per
[`../findings.md`](../findings.md) §4a-4d: the thirty-fourth note's
`1277` and `973`, off a clean `origin/main` at `0daac768` measuring `1271` and
`967` so that `1271 + 6 = 1277` and `967 + 6 = 973` with the six #845's, and
#1008's `1308` and `1004`, off that same `1271` and `967` by a different
thirty-seven — the first re-derivation on this sentence whose whole arithmetic is
one suite added to a figure the previous note had already re-derived on this same
tree rather than two sides' apart. **The `1271` and `967` are on this tree neither
side's superseded value but the common ancestor of both sides' bases**, which is a
third thing for that pair to be and is why the thirty-fourth note calls them "the
base this merge adds to" while the branch calls them superseded: both readings are
true of the tree each was written on, and here they are the one pair of figures a
reader can add *either* side's step to. **And it is not the `39b32188` the
paragraph beside this one measured from**, because #981 took `main`
from `1266` and `962` to the same `1271` and `967` in the same week: its five
cases are in `ec/tools/test_check_testdata_row_claims.py` where #974's five were,
so the two fives are not the same five and only the figure is common to both
trees. **What that merge superseded is the attribution rather than the figure**:
`1266 + 5 = 1271` is the `#844` × `#974` tree's own reading and `main` reached
the same number by a different step, so the sentence's own arithmetic no longer
describes how `origin/main` arrived there — the same "a base that was stale
before use" the thirty-second note corrected in the other direction, and the
`1269` and `965` it records stay written there beside this, each true of the tree
it was measured on, per §4a-4d, and still superseded, which **both sides say for
the same reason**: they were the addition on a `1243` base that was stale before
use, `main` reading `1266` where its own sentence said `1264`.

**The suite count's step is `42` → `43`, and it is a fifth single-suite step and
not a sixth** — #985's `ec/tools/test_disasm8051_oracle.py`, #973's
`ec/tools/test_check_capture_names.py`, #978's
`ec/tools/test_measure_index_repair_visibility.py` and #845's
`ec/tools/test_trace_xdata_refs.py` were the first four, in that order, and each
of those four added a suite and no figure, so this is the same shape as the steps
before it. **The step is one-sided where all four of those were, and the merge
around it is not**: #1008's suite is the only `test_*.py` this landing added and
#845's is the only one the base already carried, so `1271 + 37 = 1308` and
`1277 + 37 = 1314` are one step read on two trees rather than two steps on one.
**The earlier step is `40` → `41`, and it is a third single-suite step and not a
fourth** — #985's `ec/tools/test_disasm8051_oracle.py` and #973's
`ec/tools/test_check_capture_names.py` were the first two, and #780's ten above
added cases to a suite it already counted, which is why that merge's step left
the `40` where it was. **It moves on `main`'s side alone**: #978's suite is the
only `test_*.py` either side of *that* merge added, so the thirty-first's own
figure would have read `40` and `1248` where the thirty-second's reads `41` and
`1271` — the same one-sidedness the twenty-second and twenty-third notes record,
and the reason `test_readme_suite_table.py`'s set check needed no correction on
either branch and needs none here either. **The other side of each of those two
merges moved the test count alone**, and #974's five cases in
`ec/tools/test_check_testdata_row_claims.py` are that half twice over: at the
`#978` × `#974` merge they moved a suite #978 had already indexed, and at the
`#845` × `#974` merge they moved a suite #845's own tree already indexed.
**#845's own side read `1270` and `966`, and the `#844` × `#845` merge read
`1272` and `968`** — `1264 + 6` and `960 + 6` over thirty suites, then the same
six plus #844's two — all four left written in the thirty-fourth note below, each
true of the tree it was measured on, per §4a-4d.

*(And one clause the branch wrote above the thirty-second's step does not survive
this merge, so it is corrected beside itself rather than into it, on the rule
§4a-4d sets. "**It moves on neither side of anything**: this landing adds one
suite and touches no workflow, so there is no second figure to disagree with it"
was true of the branch's own tree, where nothing else had moved; on the tree it
lands in, `main` has taken a suite of its own in the same window, so the sentence
carries **two** figures that agree rather than one and no rival — the opposite
situation, and the reason the totals above are re-derived by running the runner
instead of stepped from either side's own. **The thirty-fourth note's "each of
the two `+1` steps is one-sided, and this merge is the first with a suite on
either side of it" is left standing**, because it is a record of the `#845` ×
`#974` tree and this is a different merge; the first merge in this run with a
suite on both sides is this one rather than either of them.)*
[`disasm8051-oracle-from-the-annotations.md`](disasm8051-oracle-from-the-annotations.md)
is #985's write-up. **A merge has now added a suite where the steps before it
added none, and both sides of one did it**: `main` gained a commit after #780
forked, so thirty-eight became thirty-nine on the branch's own tree on #985's
`ec/tools/test_disasm8051_oracle.py`, and thirty-nine became forty here on
#973's `ec/tools/test_check_capture_names.py`. **"No merge added a suite" is
therefore superseded and left standing in the twenty-first note it was written
in**, true of every tree from `24460001` until `3e020cf4`, per §4a-4d. **The
`1180` and the `1182` are both from trees before #982 — which implements #975 —
and #979 were in the base, the `1211`, the `1216`, `1221` and `1233`, the
`1238`, the `1243`, the `1248`, `1264`, `1269`, `1270` and `1272` are
re-derivations for trees the branch that wrote each one down was not on, and the
`1187` is #780's own branch before `main` moved at all**: seventeen
figures, seventeen trees, none of them this one, which is why the sentence carries
the arithmetic and them side by side rather than any of them. Every figure
above is re-derived by
running the runner on the tree it is written on — see the twenty-second note
below for the `#979` × `#985` merge, the twenty-third for the `#979` × `#973`
one, the twenty-fourth for the `#929` × `#962` × `#794` × `#780` × `#985` ×
`#979` merge #780 carried, the twenty-fifth for the `#979` × `#973` × `#780`
merge both sides of this one built on, the thirty-first for the `#780` × `#974`
merge, the thirty-second for the `#978` × `#974` one, the thirty-third for the
`#844` × `#974` one, and the thirty-fourth for this one — the last being the
second to stop at two sides' figures and add its own to them, which is the same
one term more the thirty-second added to the thirty-first's, and the first to add
them to a base `main` itself had already moved. The thirty-second is
also the first note here to record **both sides owning a number**, because `main`
took twenty-six and twenty-seventh before that branch did: **those two keep their
numbers and the branch's own four give way** to the twenty-eighth, twenty-ninth,
thirtieth and thirty-first, on the rule the twenty-fourth states and every note
after it applies. **The thirty-fourth is written on a tree where that had already
happened twice over**, so the number #845's own note was first given is taken
again and that note is renumbered here rather than left as a second twenty-eighth
— the same collision the tenth note records from the other direction, and the same
rule: the one `main` held first keeps it. Every figure inside it is its own
tree's and unmoved by the rename, which is what makes the renumber cost it
nothing but its name.)*
are what the runner below prints, one line per suite and a total on its last
line — and each is a `unittest` suite standing in for a tool's own behaviour.
*(Corrected at the `#929` × `#942` merge, by running the runner as this sentence
asks rather than by editing it blind: #942 added
`ec/tools/test_check_pin_table_rows.py` and its 36 cases, so the **thirty-five
and 1076 this sentence carried until then are left visible here per
[`../findings.md`](../findings.md) §4a-4d** — they were true of every
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
here per [`../findings.md`](../findings.md) §4a-4d. **"The last
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
[`docs/findings/test-line-pin-census.md`](test-line-pin-census.md)
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
that [`docs/findings/xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
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
[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md)
citing `xdata-moved-ranks-fall.md):3` as well. **Three are #889's**, in
[`xdata-decile-small-set-contract.md`](xdata-decile-small-set-contract.md),
which did not exist on the branch's tree, and **all three went stale under
#891**: its two citations into the write-up, `:199` and `:220`, which are
repointed to `:208` and `:240` with the flipped-cluster header they name moved
from `:214` to `:234` and two `rank A` / `rank B` columns wider, and its one
citation into the tool, `xdata_moved_ranks.py:243`, which is `def deciles()` on
`main`, `:277` after #891 and `:332` on this branch beside it — it **records another line**. Seven are #887's own, in
[`docs/findings/test-line-pin-census.md`](test-line-pin-census.md):
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
[`xdata-moved-ranks-pin-decisions.md`](xdata-moved-ranks-pin-decisions.md).
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
per [`../findings.md`](../findings.md) §4a-4d rather than edited into
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
recorded**, per [`../findings.md`](../findings.md) §4a-4d rather than
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
[`xdata-moved-ranks-collision-scope.md`](xdata-moved-ranks-collision-scope.md),
carries no `test_*.py:NNN` pin at all, so it moves **the read count by one and
the pinned-file count not at all** — `27` is `27` on `84a89d9a`, on `main` at
`271389d7` and here, which is the headcount the `#930` note reads too; the
fifteenth note's "so #929's new file adds no pin" is still true, and what changed
underneath it is what `origin/main` reads. **The superseded figures stay visible
above per [`../findings.md`](../findings.md) §4a-4d**, and
[`test-line-pin-census.md`](test-line-pin-census.md)
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
[`pin-table-row-reconciliation.md`](pin-table-row-reconciliation.md)
to the corpus, and it carries no `test_*.py:NNN` pin — the same shape the note
above records for #929's own file, which is why this is the second merge in a row
whose whole move is a denominator. `census_test_line_pins.py` re-run on the tree
this merge produces reads **`105` occurrences in `27` markdown files, `78`
distinct spellings, `57` distinct resolved targets, `73` resolves, `32` declined,
the `5/19/10/6/33` shape split, over `150` markdown files read against `36` test
files** — so the `105`/`27`/`78`/`57`/`73`/`32` and the split are the sixteenth
note's figures unchanged and the `149` is the only one of the ten that moves.
**The `36` test files are one more than the `35` the
`test-line-pin-census.md` re-transcription beside this records
for the `#929` × `#930` tree**, because #942 added
`ec/tools/test_check_pin_table_rows.py`. The `149` stays visible above per
[`../findings.md`](../findings.md) §4a-4d, and the sixteenth note's
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
`test-line-pin-census.md`'s per-pin table, its supersession-shape
legend and the blocker argument that names the line are re-registered to `:166` in
place. **The sixteenth note's "nothing either branch wrote lands above this file's
`:159`" was true of the tree it measured and is left standing per
[`../findings.md`](../findings.md) §4a-4d** — it is this merge's own
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
[`../findings.md`](../findings.md) has the same gap in a different
figure — it reads *"11 of the **37** indexed `test_*.py`"* where the merged tree
indexes **38** and **27** are named by none, and a `git archive origin/main`
extraction is where that one was checked rather than asserted.
**The `> 300` floor's citing line moved once more and the moved value is `:9158`
rather than `:9114`**: #946's §65 addition puts **26** lines above it in
[`../findings.md`](../findings.md) and this merge's own §65 correction
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
[`../findings.md`](../findings.md) §4a-4d; none of the three is edited.
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
`../findings.md` §4a-4d: it was not corrected a third time on **#778's**
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
[`test-line-pin-census.md`](test-line-pin-census.md)
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
[`xdata-guard-off-key-distinctness.md`](xdata-guard-off-key-distinctness.md),
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
written rather than edited per `../findings.md` §4a-4d; what moved is the
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
`../findings.md` §76's numbering note records for its own collision, in the
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
[`../findings.md`](../findings.md) §4a-4d; the eleventh note's thirty-
five and 1076, #929's thirty-six and 1112, `main`'s thirty-seven and 1134 and
#778's thirty-eight and 1161 are each true of the tree they were measured on, and
none of the four saw another's suite or cases.*

**This file's own `:197` pin moves for the sixth time, and by +6, and this is
this issue's own doing.** The correction above adds six lines *above* `:197`, so
`197 + 6 = :203` and `159 + 9 + 7 + 22 + 6 = :203` is the whole arithmetic; the
row in [`test-line-pin-census.md`](test-line-pin-census.md)
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
`../findings.md` §76's numbering note records for its own collision, in the
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
[`../findings.md`](../findings.md) §4a-4d: the `1211`/`907` `main`'s
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
`e198fd9` at the time, `5672042a` since #36 moved the pin, is fetched with
`git show`, and a directory with no `.git` cannot
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
[`test-line-pin-census.md`](test-line-pin-census.md)
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

*(Twenty-eighth merged-tree note, 2026-09-26, issue #974 landing beside #982.
**It is the twenty-eighth and not the twenty-second, or the twenty-third, or the
twenty-fourth, or the twenty-fifth, or the twenty-sixth, or the twenty-seventh,
because #811's, #979's, #973's and #780's merges took those first four numbers on
`main` while this branch was open, and #978's took the other two in this merge's
own window** — the same
collision the tenth note records from the other direction, and the same rule:
the one `main` held first keeps it, and this note is renumbered rather than
left as a second twenty-second. **The number it was first given on its own
branch was the twenty-third, and that stays written here** — it is what the
file read on `origin/agent/issue-974` and the arithmetic below is that note's
own. **"What it runs" above is corrected a fifth
time, `1168` → `1182`, and the `1168` stays written here** per
[`../findings.md`](../findings.md) §4a-4d — it was true of the tree
it was measured on, `26e970d5`, and it is the figure this file carried through
both commits that landed after it. **The arithmetic is additive from three
trees, not two, and only the merged run is the authority**: the base's `1168`,
`#982`'s **nine** cases (five in `ec/tools/test_check_testdata_row_claims.py`
and four in `ec/tools/test_check_capture_claims.py` — the second suite is #982's
own silent-skip self-report, and it is why the merged total moves fourteen
rather than ten) and this issue's **five**, is `1168 + 9 + 5 = 1182`, and
`python3 -m unittest discover -s ec/tools` reads **`878`** where the note above
reads `864`. Both are measured by running both commands on this tree, not
arithmetic on a diff. **The red set is unchanged, and it was re-checked here
rather than carried**: the single suite every note above names,
`test_check_cluster_citations`, 48 tests, the one failure, on the same `:220`
of `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements — the state `main` measured before this merge,
so it is a re-derivation and not an assumption, and neither branch caused it
nor fixes it. **No pin moved on this branch's own tree, and that was a placement
decision rather than an accident**: this note is below the eighth-thing
paragraph at `:203` rather than beside the twenty-first, so the one
`tools/README.md` row in the per-pin table still placed and the twenty-first
note's own `+6` arithmetic was untouched. **It does move on the merge with
#979 × #985**, because the twenty-second note below re-derives the same
sentence and its correction is longer; the twenty-ninth note carries the
`+3` and the re-registration. The table row for
`ec/tools/test_check_testdata_row_claims.py` **is** reworded in place,
appending this issue's cases to #975's rather than replacing either; the census
population is unmoved at 106 pins in 28 files, 79 spellings and 58 resolved
targets, so nothing here added a citation for the per-pin table to place. #974's
own write-up is the record of what it measured;
`../findings.md` §84 is the summary and says the same — **§79** on the
tree this note measured, renumbered four times since, once by the thirtieth
note below because `main` took that number for #973, once at the `#780` ×
`#974` merge because `main` holds **§80** for #780, once at the `#978` ×
`#974` merge because `main` holds **§81** for #978, once at the `#843` ×
`#974` merge because `main` holds **§82** for #843, and once more at this merge
because `main` holds **§83** for #844.*

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
[`docs/findings/test-line-pin-census.md`](test-line-pin-census.md)
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
that in [`test-line-pin-census.md`](test-line-pin-census.md),
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
[`test-line-pin-census.md`](test-line-pin-census.md), which is
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
[`tools-readme-totals.md`](tools-readme-totals.md)
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
> [`docs/findings/xdata-no-eq-guard-measured-state-correction.md`](xdata-no-eq-guard-measured-state-correction.md).
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
[`test-line-pin-census.md`](test-line-pin-census.md)
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
above per [`../findings.md`](../findings.md) §4a-4d, and it was true
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
[`pin-table-by-cited-file.md`](pin-table-by-cited-file.md)
say why. The `11` does not move, because the pin count is still **106**.*
> **Corrected beside the paragraph above on the #974 merge, per
> [`../findings.md`](../findings.md) §4a-4d — the pin *does* move
> there, and this merge's saving was placement rather than a shorter edit.**
> #974 re-derived the same sentence from the other side, and the two corrections
> together are longer than the lines they replaced, so the citing line this
> paragraph names is at **`:206`**: `203 + 3` is the whole of it, and the row
> in
> [`test-line-pin-census.md`](test-line-pin-census.md)
> is re-registered to `:206` in place, with the `:203` above left written
> because it is true of the tree this note measured. `check_pin_table_rows.py`
> reads **106 rows, 106 records, 106 placed, all seven classes 0** again on that
> tree, re-run rather than carried. **What the paragraph above got right is
> what made the move cheap**: this note sits far below the pin and #974's does
> too, so the three lines that moved it came out of the sentence's own
> correction and not out of either note. The twenty-ninth note below carries
> the arithmetic, and the thirty-first carries the merged tree's, with the
> thirty-second carrying this tree's.*

*(Twenty-ninth merged-tree note, 2026-09-26, issue #974 landing beside the
`#979` × `#985` merge. **The number this note was first given, the twenty-fourth,
belongs to `main`'s own note above**, which held it before this branch opened its
own, so the rule the tenth note records from the other direction gives the whole
of it to `main` and this one is renumbered — **every figure below is unchanged by
that, because they are this note's tree's and not this file's numbering.** **The
`twenty-seventh` it carried on its own tree is superseded beside that, and this
is its second renumber**: `main` took twenty-six and twenty-seventh for #978 in
this merge's window, so the twenty-sixth, twenty-seventh, twenty-eighth and
twenty-ninth this branch carried all give way and this one lands on the
twenty-ninth — `main`'s own twenty-sixth and twenty-seventh stay reading as its
own, and the twenty-eighth above keeps the branch's first of the four.
**The suite totals move once more and only the test count
does, and the merged run is the authority rather than either side's figure.**
`bash tools/run-tests.sh` on this tree reads **`39 suite(s) run, 1216 tests; one
or more FAILED`** and `python3 -m unittest discover -s ec/tools` reads
**`912`**. The step this issue contributes is **+5 tests and no suite**, all
five in `ec/tools/test_check_testdata_row_claims.py` — `50` on this merge's base
`3e020cf4` and `55` here — so the arithmetic from the note above is `1211 + 5 =
1216` and `907 + 5 = 912`, both measured by running the two commands on this
tree and not by adding a diff. **The suite count is unmoved at `39`**, because
#974 adds no `test_*.py`, which is the same shape as #962's step in the
twentieth note and the opposite of #985's: for the fourth merge running, the two
sides of this one could not have seen each other's suite, and only one of them
had one to see.

**The `1182` and `878` the twenty-eighth note above records are that branch's
tree and stay written.** They were measured before #982 — which implements #975 — and
#979 were in the base, exactly as the twenty-second note records of its
counterpart's `1180`/`876`, and neither number is carried into the sentence
above. **That note is renumbered to the twenty-eighth** because both sides of
this merge took "twenty-second" while their branches were open, and the one
`main` held first keeps it — the same rule the twentieth note records from the
other direction, and the same rule that moves it on once more at the merge above.

**This file's own `:203` pin moves, for the seventh time, and by +3.** The
correction to "What it runs" above is longer than the lines it replaced —
neither side's fit in place once both are in — so the citing line this file's
per-pin row names is at **`:206`**. The row in
[`test-line-pin-census.md`](test-line-pin-census.md)
is re-registered to `:206` in place, together with its supersession-shape legend
row and the blocker argument that names the same line, with the `:203` left
written per [`../findings.md`](../findings.md) §4a-4d.
`check_pin_table_rows.py` reads **106 rows, 106 records, 106 placed, all seven
classes 0** on this tree — run, not read off the paragraph above — and
`census_test_line_pins.py` reads **106 pins in 28 files, 79 spellings, 58
targets, 74 resolves, 32 declined**, the population the note above records and
this merge does not move: #974's write-up and this note cite no `test_*.py:NNN`
pin, so nothing was added for the table to place.

**The red set is the single suite the notes above name, and this merge added a
second red suite and repaired it**, which is the eighth-thing paragraph's own
subject rather than a new one: `test_check_pin_table_rows` went red on three of
its cases the moment the merged sentence was longer than the one that note
registered, and green again once the row was re-registered to `:206` — a pin
doing the job a pin is for. **The failure that remains is not this merge's**:
`test_check_cluster_citations`, 48 tests, one failure, on the same `:220` of
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements, which the notes above re-checked on the base and on clean
`origin/main` before either branch merged.

**The suite-table row for `ec/tools/test_check_testdata_row_claims.py` is
reworded in place once more**, this merge appending #974's cases to the ones
#975 and #979 already added rather than replacing any of them, and
**`test_readme_suite_table.py`'s set check is unaffected again**, since it
compares the *set* of suites and neither side adds one. **And
`docs/findings.md`'s numbering moved**, which is the one thing in this merge
that is a rename rather than a correction: this branch's summary was `§77` and
`main` held `§77` for #811 and `§78` for #979 while it was open, so the summary
is **§79** on the tree this note measured, and the two references this branch
added to it — here and in its own write-up — are repointed with it. **The
thirtieth note below renumbers it once more**, because `main` has since taken
`§79` for #973, **the `#780` × `#974` merge renumbers it a fourth time to §81,
because `main` holds §80 for #780, the `#978` × `#974` merge renumbers it a
fifth time to §82 because `main` holds §81 for #978, the `#843` × `#974` merge
renumbers it a sixth time to §83 because `main` holds §82 for #843 as well, and
this merge renumbers it a seventh time to §84, because `main` holds §83 for
#844** — the same rule each time, and `main`'s §80 stays reading as #780's, its
§81 as #978's, its §82 as #843's and its §83 as #844's.*

*(Thirtieth merged-tree note, 2026-09-26, issue #974 landing on the #979 ×
#973 merge, which is the fifth merge of this issue and the second in a row
whose two sides each re-derived the same sentence. **The number this note was
first given, the twenty-fifth, belongs to `main`'s own note below**, so the same
rule renumbers this one and leaves every figure below, which is this note's
tree's, where it was. **The suite totals move
again, and this time only the test count does.** `bash tools/run-tests.sh` on
this tree reads **`40 suite(s) run, 1238 tests; one or more FAILED`**, and the
step from the twenty-third note's `40`/`1233` is **+5 tests and no suite**,
which is #974's five cases and nothing else: the base already had #973's suite
and its three cases, so `1233 + 5 = 1238` and `40 + 0 = 40`, both measured by
running the runner on this tree rather than by adding a diff. The branch's own
`39`/`1216` and the twenty-second note's `39`/`1211` stay written for the trees
they measured.

**`docs/findings.md`'s summary is renumbered a third time and the pin moves
again, and both are consequences of the same thing** — two sections arriving
with the same number and neither side's correction fitting in place:

- **§79 → §80, then §80 → §81, then §81 → §82, then §82 → §83, then §83 →
  §84.** `main`
  committed §79 for #973
  first, and this file's own numbering rule is that the summary already on
  `main` does not move and the branch's gives way, so #974's summary is **§80** on
  this note's tree. The two references the branch added to it — the sentence in
  the twenty-ninth note above and one in its own write-up — are repointed, and
  §79 is left reading as #973's. **At the `#780` × `#974` merge it gives way once
  more, to §81, because `main` holds §80 for #780**, and the three references —
  those two and the one in the twenty-eighth note above — are repointed again;
  `main`'s §80 stays reading as #780's. **At the `#978` × `#974` merge it gives
  way a fifth time, to §82, because `main` holds §81 for #978 as well**,
  **a sixth time to §83 at the `#843` × `#974` one, because `main` holds §82 for
  #843**, and **a seventh time to §84 at this merge, because `main` holds §83 for
  #844**, each repointing the same three references once more. `main`'s §81 stays
  reading as #978's, its §82 as #843's and its §83 as #844's.
- **`:206` → `:208`.** The twenty-ninth note's own `+3` was true of a merge
  whose sentence correction was longer than the lines it replaced; this tree's
  carries *three* such corrections stacked, and the citing line lands at
  **`:208`** — checked by reading the line rather than by trusting this
  paragraph, which is the same rule the twenty-third note states. The row in
  [`test-line-pin-census.md`](test-line-pin-census.md)
  is re-registered to `:208`, with the `:203` and the `:206` left written per
  [`../findings.md`](../findings.md) §4a-4d — a third value for one
  pin, which is the fourth time this file has held more than two. **The
  thirty-first note below carries the fourth, for the merged tree this note's
  `:208` was measured on and not this one, and the thirty-second carries the
  fifth, for the tree this file now sits in.**

**`test_check_pin_table_rows` went red on three of its cases and was repaired
by that re-registration**, so the red set this note leaves is the one every note
above names and one of them fixes: `ec/tools/test_check_cluster_citations.py`,
48 tests, one failure, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements, re-checked here on this tree rather than carried. **The suite
count is `40` and `test_readme_suite_table.py`'s set check is unaffected**,
since it compares the *set* of suites and this merge adds none.

*(Twenty-fifth merged-tree note, 2026-09-26, issues #979 × #973 × #780. **The
sentence above is re-derived by running the runner rather than by adding the two
sides' figures up, and the arithmetic is written out only after that, as a
description of a number already measured rather than a way of arriving at one.**
On this merged tree `bash tools/run-tests.sh` reads `40 suite(s) run, 1243 tests;
one or more FAILED` and `python3 -m unittest discover -s ec/tools` reads `939`,
both measured here. The twenty-second note's `39`/`1211` and the twenty-third's
`40`/`1233` are left visible above per [`../findings.md`](../findings.md)
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
[`test-line-pin-census.md`](test-line-pin-census.md)
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
this file's numbers and `../findings.md` §76's for this file's section
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
left visible above per [`../findings.md`](../findings.md) §4a-4d, each
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
[`test-line-pin-census.md`](test-line-pin-census.md)
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
measured on, per [`../findings.md`](../findings.md) §4a-4d.*

**A repoint was owed, four of them, and the reason the twenty-sixth gives for
saying none was is false on its own terms.** That reason is "they land in
`docs/findings.md` at §41, §47, §76 and §79, every one of which is above the four
rows". **What moves a pin is whether an edit adds lines above it, not which
section the edit is in**, and two of the four are not above the rows: §76's edit
is at [`../findings.md`](../findings.md):10063 and §79's at `:10426`,
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
[`test-line-pin-census.md`](test-line-pin-census.md)'s
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

*(Thirty-first merged-tree note, 2026-09-26, issues #780 × #974. **This is the
first note in the run that is not one side's tree: both sides' corrections to
the sentence above are in it, so every figure here is this merge's and neither
side's, and the two sides' own measurements are left written above per
[`../findings.md`](../findings.md) §4a-4d rather than replaced.**
**The `twenty-ninth` it carried on its own tree gives way here**, on the rule every
note after the twenty-fourth applies: `main` took twenty-six and twenty-seventh
for #978 in this merge's window, so the branch's own four give way to the
twenty-eighth, twenty-ninth, thirtieth and thirty-first while `main`'s two stay
reading as its own. Every figure below is that note's tree's and unmoved by the
rename, which is why the rename costs this note nothing but its name.*
`bash tools/run-tests.sh` on this tree reads **`40 suite(s) run, 1248 tests; one
or more FAILED`** and `python3 -m unittest discover -s ec/tools` reads
**`944`**, both measured by running the two commands here before the arithmetic
below was written, which is the rule the twenty-fifth note states and the one
this file's first note has kept since. **The two steps are #780's ten in
`ec/tools/test_check_testdata_index.py` and #974's five in
`ec/tools/test_check_testdata_row_claims.py`, and they are the same number from
either side's tree:** `1233 + 10 + 5 = 1248` and `939 + 5 = 944` both land on
what the merged run printed. The `1238` and the `1243` are the two sides
measured apart, each adding only its own contributor to the `1233` they shared,
and **the `1248` is the first figure in this run that adds both sides' steps to
each other** — the twenty-fifth note's own reason for not deriving its number
from the two it had, applied here to two figures rather than one. **The suite
count is the half that does not move, `40` on `main`, `40` on #780's tree, `40`
on the branch's and `40` here**, because neither side adds a `test_*.py`, which
is why `test_readme_suite_table.py`'s set check is unaffected for the fifth merge
running and why `check_pin_table_by_cited_file.py`'s `40 / 11 / 29` needs no
correction either.

**The `:203` pin moves for the tenth time, and the step is the merged sentence's
own.** `main` reads `:236` and the branch's own tree read `:208`, and this tree
reads **`:249`** — so `159 + 9 + 7 + 22 + 6 = :203` becomes
`159 + 9 + 7 + 22 + 6 + 33 + 13 = :249`, the `+33` being the two sides'
corrections written side by side at the merge above and the `+13` being this
one, where neither side's parenthetical fit in place and both had to be carried
with the merged figure beside them. That is the fifth value this one pin has
held, and the second time this file has held more than two. The row in
[`test-line-pin-census.md`](test-line-pin-census.md)
is re-registered to `:249` together with its supersession-shape legend row and
its blocker argument, with the `:203`, the `:206`, the `:208` and the `:236`
all left written where they are. `check_pin_table_rows.py` reads **106 rows,
106 records, 106 placed, all seven classes 0** with it, and
`census_test_line_pins.py` reads **106 pins in 28 files, 79 spellings, 58
targets, 74 resolves, 32 declined** with the landing-shape split `0/15/22/5/32`
— every one of them unmoved, because this merge moved a line and not a record, a
count or a shape.

**The red set was two for the length of this merge, and the second is the one
this note is here for, exactly as it was at the merge above.** The suite every
note above names is `ec/tools/test_check_cluster_citations.py`: 48 tests, the
single failure, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements against `main-ec-145`, re-checked here rather than carried, so
neither #780 nor #974 caused it and neither fixes it. **The one this merge did
add is `ec/tools/test_check_pin_table_rows.py`**, 36 tests and four failures
while the sentence above still carried both sides' figures and the row still
named `:236`: the tool read **1 `unplaced-row` and 1 `row-without-record`**, and
reads 106 / 106 / 106 with every class 0 once the row is re-registered to
`:249`. **Four failures rather than the three the notes above record is this
merge's own arithmetic, not a new defect** — one more sentence correction above
the pin is one more case that cannot be reconciled while the row is stale, and
the case that fails is the same one the eighth-thing paragraph has been about
since the twenty-first note. It is also why the placement argument those notes
make is the one this note follows: this note sits below the pin, so the `+13`
came out of the sentence's own parenthetical and not out of it.

**`docs/findings.md`'s numbering moved a fourth time on this merge, and the two
sides' sections are both kept.** `main` held **§80** for #780, so the branch's
gave way to **§81**, and the three references the branch added to it — the
sentences in the twenty-eighth and twenty-ninth notes above and the one in
`docs/findings/testdata-row-claims-report-naming.md` — were repointed with it.
`main`'s §80 was left reading as #780's. **The three notes this branch carried
are renumbered to the twenty-eighth, twenty-ninth and thirtieth**, because
`main` held the twenty-third, twenty-fourth and twenty-fifth first, and every
figure inside them is that note's own tree's and unmoved by the rename. **On
the tree this file now sits in the branch's summary gave way once more, to
§82, because `main` held §81 for #978 as well** — the same rule a fifth time,
`main`'s §81 left reading as #978's, and the thirty-second note below carries the
record from this end. **The `../findings.md` rows are unaffected again**, for the
reason every note above gives: this merge's edits to that file land at its
`:9549` and at its new section, `:10491` on, and every one of the six rows the
per-pin table registers against that file — `:4206`, `:4208`, `:7191`, `:7404`,
`:7465` and `:9207` — is above both, so no repoint is owed. **That is still true
on the merged tree, and the half of it that is `main`'s is the twenty-seventh
note's own finding rather than a new one**: #978's four edits to that file land
at `:7053-7056` (the `+2` that note measures), `:7286`, `:10086` and `:10493`,
and both new sections land below the last of them — so four of the six rows move
and two do not, and the four are the ones the twenty-seventh note registered, at
`:7193`, `:7406`, `:7467` and `:9209`.

**Nothing else this merge touched is a moving figure, and all of it was re-run
rather than carried:** `xdata_moved_ranks.py --self-test` is at **53**,
`xdata_register_map.py --check` at **1326** register rows and **439** cluster
rows, and `check_testdata_index.py`'s own fifth-direction line is unmoved at
**2 fixture CSV(s), 0 with no `evidence` column, 10 evidence cell(s), 11 evidence
path token(s): 11 resolved, 0 missing, 0 unresolved** — #974's change is in
`check_testdata_row_claims.py` and reads none of those files.
`check_testdata_row_claims.py` itself reads **`27 table row(s), 17
literal-bearing: 54 literal(s), 30 resolved, 0 missing, 24 unresolved`**, the
tallies every write-up about this issue quotes, with the dated block naming
`2026-09-23-power-mode-cycle-0f00-0f5f.csv` as the carrier of both of row 7's
literals and the closing line reading **28 with the fixtures their row names, 2
with the captures a bare date in their sentence names** — neither moved by the
merge, which is the point #974's write-up makes about them.*

*(Thirty-second merged-tree note, 2026-09-26, issues #978 × #974. **This is the
first note in this run that sits below every other merge's rather than beside one,
the first whose arithmetic is **three** figures where each of the two before it
had two, and the first to re-register a line that three trees had already named
three different ways.** `main`'s twenty-sixth and twenty-seventh are above it,
and above them the branch's own, renumbered to the twenty-eighth through
thirty-first on the rule every note after the twenty-fourth states; `main`'s two
keep their numbers and their text, and the branch's four keep every figure inside
them, which is the whole reason a rename costs a note nothing but its name. **Every figure below is
this tree's and was measured on it before the arithmetic was written down**,
which is the rule the twenty-fifth note states and the thirty-first applied to
two figures rather than one.

`bash tools/run-tests.sh` on this tree reads **`41 suite(s) run, 1269 tests; one
or more FAILED`** and `python3 -m unittest discover -s ec/tools` reads
**`965`**. **The two sides' own figures are left written where they are**, the
twenty-sixth's `1243 + 21 = 1264` and the thirty-first's `1233 + 10 + 5 = 1248`,
each true of the tree it was measured on, per
[`../findings.md`](../findings.md) §4a-4d — and **both build on the same
`1233` and the same `939`**, so `1243 + 21 + 5 = 1269` and `939 + 21 + 5 = 965`
are the two merges' steps added to their shared base, and each lands on what the
merged run printed. **The suite count moves `40` → `41` and it moves on `main`'s
side alone**: #978's `ec/tools/test_measure_index_repair_visibility.py` at 21
cases is the only `test_*.py` either side added, and #974's five cases went into
`ec/tools/test_check_testdata_row_claims.py`, which the branch's own tree already
indexed. **So a run that had taken the thirty-first's side of the sentence rather
than this one would read `40` and `1248` where this one reads `41` and `1269`** —
the arithmetic is the same three terms in a different grouping and the count is
not, and that is the whole of what one-sidedness costs a totals sentence.

*(Corrected on the `#844` × `#974` merge this note now sits in, by running both
commands on this tree rather than by editing the figures blind: **the `1269` and
the `965` above are the `#978` × `#974` tree's own and stay written per
[`../findings.md`](../findings.md) §4a-4d, but on this tree the same
two commands read `41 suite(s) run, 1271 tests; one or more FAILED` and `967`**,
re-measured here and not carried — the whole of what the thirty-third note below
already recorded. The step is **`+5` tests and no suite**, and it is all of
#974's five cases in `ec/tools/test_check_testdata_row_claims.py`: a clean
`origin/main` worktree at `39b32188` reads `41`/`1266` and `962` against this
tree's `41`/`1271` and `967`.

**What needed correcting was the provenance as well as the number, and "each
lands on what the merged run printed" is the clause that was wrong.**
`1243 + 21 + 5 = 1269` and `939 + 21 + 5 = 965` were the addition either side
could have made — which is what the "What it runs" paragraph above said in the
same breath that they were not — and their shared `1233`/`939` base was stale
before either was added to: **#1011's two new cases in
`ec/tools/test_walk_branch_arms.py` took `main` from `1264` to `1266` after the
last renumber, and `main`'s own sentence still reads `1264`** at its
`tools/README.md:14` on `39b32188`. The corrected paragraph above derives from
a base measured here rather than one added to, which is the twenty-fifth note's
rule.)*

**The `:203` pin moves a twelfth time, by `+32`, and this is the second step above
`+30`.** `main` reads `:247` and the branch's own tree read `:249`, and this tree
reads **`:279`** — so `159 + 9 + 7 + 22 + 6 + 33 = :236` becomes
`159 + 9 + 7 + 22 + 6 + 33 + 11 + 32 = :279`, the `+11` being the twenty-sixth's
and the `+32` this one's. **The whole `+32` came out of the sentence's own
parenthetical and not out of any note**, because every note here sits below the
pin and the twenty-eighth through thirty-first are four renumbers rather than
four additions: the fourteen-figure superseded list both sides' histories add up
to, the `1243 + 21 = 1264` clause beside the `1233 + 10 + 5 = 1248` that
superseded it, and the three-figure arithmetic and the count of superseded values
that go with it. The row in
[`test-line-pin-census.md`](test-line-pin-census.md)
is re-registered to `:279`, with its supersession-shape legend row and its
blocker argument, and **the `:203`, the `:206`, the `:208`, the `:236`, the
`:247` and the `:249` are all left written where they are** — a sixth value for
one pin, and the third time this file has held more than two. **The tool read
`1 unplaced-row` and `1 row-without-record` with every superseded value put back
in the table — `:208`, `:236`, `:247`, `:249` and `:278` in turn, each run rather
than predicted — and reads 106 rows, 106 records, 106 placed, all seven classes 0
with `:279`**, the arithmetic being what it printed rather than a guess at it. `census_test_line_pins.py` reads **106 pins in
28 files, 79 spellings, 58 targets, 74 resolves, 32 declined**, the landing-shape
split still `0/15/22/5/32` and 41 indexed test files: **re-derived by running it
on this tree rather than carried**, which is the check a re-registration is run
for, since a line moving is not a record, a count or a shape moving.

**`check_pin_table_by_cited_file.py` reads `41 / 11 / 30`**, so the thirty-first's
"needs no correction either" clause is superseded beside itself rather than edited
into: the `40 / 11 / 29` it left standing was true of its own tree, and the step
is #978's suite and nothing else.

**The red set is two, and the second is the one this note is here for, as it was
at the merge below.** `ec/tools/test_check_cluster_citations.py` — 48 tests, the
single failure, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements against `main-ec-145` — fails identically on a clean `origin/main`
worktree, re-checked here rather than carried, so neither #978 nor #974 caused it
and neither fixes it. `ec/tools/test_check_pin_table_rows.py` joined it at
**three** of its 36 cases while the row still named a superseded line, and is
green with `:279`. **The three is not the thirty-first's four, and the reason is
worth more than the figure: it is three whatever value the row names.** The row
was put back to `:208`, `:236`, `:247`, `:249` and `:278` in turn and the suite
run over each, and the checker read `1 unplaced-row` and `1 row-without-record`
and the suite `FAILED (failures=3)` in all five, so **the count is a function of
the row being stale and not of how far its value is from the line the file
reads** — which is not what the thirty-first's own explanation says, and that
explanation is corrected beside itself here rather than in it, per §4a-4d. The
**four** is left written there as that note's tree's, and so is the claim that
one more stacked correction above the pin is one more red case. Named by suite
and by count rather than by line, for the reason every note above gives.

**`docs/findings.md`'s numbering moved a fifth time and both sections are kept.**
`main` holds **§81** for #978, so #974's summary gave way to **§82** — the same
rule the four before it applied, `main`'s §81 left reading as #978's, and the
three references the branch added repointed with it, in the twenty-eighth and
twenty-ninth notes above and in
`docs/findings/testdata-row-claims-report-naming.md`.

**And a sixth time at the `#843` × `#974` merge.** `main` holds
**§82** for #843 — the count-bounded-walk summary — so the number that
rename produced is taken too, and #974's summary gives way again to **§83**. The
same rule, the same three references repointed again, `main`'s §82 left reading
as #843's, and #843's own section is the one that keeps its number because it is
the one already committed on `main`.

**And a seventh time at the `#844` × `#974` merge, which is the one the
thirty-third note below records rather than this one.** `main` holds **§83** for
#844 — the bounds-check summary — so the
number that rename produced is taken too, and #974's summary gives way again to
**§84**. The same rule, the same three references repointed again, `main`'s §83
left reading as #844's, and #844's section keeps its number for #844's reason.
**Nothing else in this file moves with it**:
the renumber touches prose, and no row of the per-pin table registers a section
number, which the tool's own "no verdict cell was read" line is the standing
check for. **The four `../findings.md`
rows the census table registers moved on `main`'s side at the merge above and are
not moved again here**: they read `:7193`, `:7406`, `:7467` and `:9209` on this
tree, with `:4206` and `:4208` unmoved, because #978's four edits to that file
land at `:7053-7056` (the `+2` the twenty-seventh note measures), `:7286`,
`:10086` and `:10493`, and both new sections land below the last of the six
rows — the twenty-seventh note's own finding, re-run here rather than carried
and confirmed by `check_pin_table_rows.py` placing all 106 rows, and the one
thing in this merge that neither side could have predicted alone.

**Everything else this merge touched is not a moving figure, and all of it was
re-run rather than carried**: `xdata_moved_ranks.py --self-test` is at **53**,
`xdata_register_map.py --check` at **1326** register rows and **439** cluster
rows, `check_testdata_index.py`'s fifth-direction line unmoved at **2 fixture
CSV(s), 0 with no `evidence` column, 10 evidence cell(s), 11 evidence path
token(s): 11 resolved, 0 missing, 0 unresolved**, and
`check_testdata_row_claims.py` at **`27 table row(s), 17 literal-bearing: 54
literal(s), 30 resolved, 0 missing, 24 unresolved`** with the dated block naming
`2026-09-23-power-mode-cycle-0f00-0f5f.csv` and the closing line reading **28
with the fixtures their row names, 2 with the captures a bare date in their
sentence names**. **The suite count is the one figure here a reader cannot get
from either side's note alone**, and the per-suite counts are the check that it
was read rather than assumed:
`ec/tools/test_check_testdata_row_claims.py` reads **58** here, on `main`'s tree
and on the branch's alike, because #978 added a suite and no case to it, while
`ec/tools/test_check_testdata_index.py` reads **69** and
`ec/tools/test_measure_index_repair_visibility.py` **21** — the twenty-first of
them `59` before #943 and the twenty-second new.

**One figure in the table below was wrong on `main` and is corrected here rather
than left**, for the reason the twenty-fifth note's own rule gives: the
`test_check_pin_table_rows.py` row read **105-row** per-pin table where the
committed table holds **106** rows, which the same row's own last clause states
twenty words later and which `check_pin_table_rows.py` prints as `106 table
row(s)`. **The `105` is left visible in this note per §4a-4d** — it was true of
the tree that row was written on, and what the merge did was make the row
register, which is the first time a reader following it could have checked the
number against the tool that prints it.*

*(Thirty-third merged-tree note, 2026-09-26, issues #844 × #974. **This is the
merge the seventh rename belongs to, and it is the one where #844 moved nothing
any note above measures** — worth saying on its own, because every other merge in
this file's run moved something.)*

**The numbering moved a seventh time and both sections are kept whole.** `main`
holds **§83** for #844 — the bounds-check summary — so #974's summary gives way
to **§84**, the same rule the six before it applied, `main`'s §83 left reading as
#844's, and the same three references repointed with it: the twenty-eighth and
twenty-ninth notes above and
`docs/findings/testdata-row-claims-report-naming.md`. **#844's own numbering
note is the record from its side** and says the same thing about #843's §82.

**`bash tools/run-tests.sh` reads `41 suite(s) run, 1271 tests; one or more
FAILED`** — re-run here, not carried. The step from the thirty-second's
`40`/`1238` is **`+1` suite and `+33` tests, and it is `main`'s side of this merge
rather than #974's**: #974 still contributes `+5` and no suite, which is what
`origin/main` reading `41`/`1266` against this tree's `41`/`1271` shows. #844
brought `ec/tools/test_walk_branch_arms.py` and its two new `BoundTests` cases,
and `check_testdata_row_claims.py` is **untouched by it at 58** — the figure the
thirty-second and every note above it records, and the one that matters here,
since a merge that added a case to that suite would have moved all six of the
figures below at once.

**The six mutations of `check_testdata_row_claims.py` were re-applied in place on
this tree and the suite re-run over each, and every one of the six reproduces the
number the thirty-second recorded**: the committed root again **2**, the carrier
dropped **2**, the first-match short-circuit back in both readers **1**, the date
ignored **19**, the split collapsed **2** to the row's own count and **3** to the
combined one, and a dated claim reverted to the textual read **1**. The tool is
byte-identical to the tree's afterwards, checked with `diff` rather than assumed.
**#844 moved none of them, and the decomposition the write-up gives for the 19 —
this branch's four, plus the twelve #979 reds on its own tree, plus #984's three
that ask what the run read out of the root — still accounts for all of them here.**

**The census and the pin table are unmoved, and re-run rather than carried.**
`census_test_line_pins.py` reads **106 / 28 / 79 / 58** with `74` resolving, `32`
declined, the landing-shape split still `0/15/22/5/32` and 41 indexed test files;
`check_pin_table_by_cited_file.py` reads **41 / 11 / 30**; and
`check_pin_table_rows.py` reads **106 row(s) against 106 record(s), 106 placed,
all seven classes 0** — which is the standing check that the `../findings.md`
rows the table registers are still placed, and it holds with #844's §83 and §84
both added below the last of them. **The `tools/README.md` row stays at `:279`**
and `ec/tools/test_check_pin_table_rows.py` is **green at 36**, as the twelfth
note of [`test-line-pin-census.md`](test-line-pin-census.md)
records: this merge edits the thirty-second and twenty-ninth notes and adds this
one, all of them **below** `:279`, and the arithmetic that produced the value
touches nothing above it.

**The standing red set is one, and it is the one every note above names.**
`ec/tools/test_check_cluster_citations.py` — 48 tests, the single failure, on the
same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements against `main-ec-145` — **re-checked on a clean
`origin/main` worktree and red there identically**, so it is neither #844's nor
#974's and neither fixes it.

*(Thirty-fifth merged-tree note, 2026-09-26, issues #845 × #1009, and it is
**the first in this run with a `test_*.py` on both sides of it**, which is why
neither the thirty-fourth's arithmetic nor the thirty-second's describes this
tree. **Everything the note above records is left written per
[`../findings.md`](../findings.md) §4a-4d, each true of the tree it
measured on** — and it keeps thirty-fifth rather than the thirty-fourth its
branch first gave it, because `main` held thirty-fourth first and the tenth
note's rule applies from the other direction. **The base this note measures
from is `5881153d` (#845's), where the thirty-fourth's was `0daac768`, and
that is the whole difference between the two steps.**)*

**The runner reads `43 suite(s) run, 1317 tests; one or more FAILED`, and
`python3 -m unittest discover -s ec/tools` reads `1013`** — both re-run on this
tree, both measured in a real `git worktree` rather than differenced, because
`test_measure_index_repair_visibility.py` skips three cases where the clone is
shallow and a `git archive` extraction is exactly that. **`1309 + 8 = 1317` and
`1005 + 8 = 1013`**, the eight being #1032's cases on
`ec/tools/test_check_history_checkouts.py` and nothing else, against #1039's
`1308 + 1 = 1309` and `1004 + 1 = 1005`, whose one was a case on that **same**
suite, #1038's one on `ec/tools/test_check_citation_lines.py`, #1034's six on
`ec/tools/test_check_history_checkouts.py` inside the base this
step measures from rather than beside it, and #1009's `1277 + 24 = 1301` and
`973 + 24 = 997`, whose twenty-four were that merge's one new suite. **The suite
count does not move at this step** — it is
**`42` → `43` and that step is #1009's alone**, #845's suite having been in the
base this note measures from rather than beside it, and every change since
#1009's being in suites that were already counted — the one-sidedness
the twenty-second and twenty-third notes record in the other direction, and why
`test_readme_suite_table.py`'s set check needed no correction on any of the six
sides. **This step is the first in this run whose two sides touched the same
suite**, so **neither side's arithmetic is a reading of this tree and the sum
is** — #1039's `1309` counted one case against the `1308` #1034 left and #1032's
`1316` counted eight against that same `1308`, on one suite in both cases. Every
earlier step's two sides had gone to different suites, and their arithmetic was
right for the same reason: #1034's `1307` counted six against a base of `1301`,
#1035's own branch read `1301` before those six existed, and #1038's `1308`
counted one against the `1307` #1034 left but on `test_check_citation_lines.py`
rather than on the other two's suite — so no two of those three figures were
ever one apart by accident, and all of them stay written above, each true of the
tree it was measured on, per §4a-4d. **The `1301` and
the `997` this sentence carried until #1034 stay written
in the parenthetical above**, and so do the `1308` and the `1004` it carried at
the `#1034` × `#1035` merge, now in that merge's own note, the `1309` and the
`1005` it carried at the `#1034` × `#1035` × `#1038` merge, now in that one's,
and the `1316` and the `1012` the branch measured, now in the sixth note at the
head of this section; as do the `1295` and
the `991` its branch measured
and the `1288` — whose
commit, `a9b3b90c`, **is not an object in this repository at all** (`git
cat-file -t a9b3b90c` answers *Not a valid object name*), so that figure is a
record rather than a reading anyone can re-run. **Every superseded figure in
that trail is behind `main`'s own tip**, which #1039 moved on to `1309` and
`1005` — the notes at the head of this section carry the measurement for each
revision, and the one this sentence carried until #1032 was `1307`/`1003` — so
each stays written here rather than being deleted, because each was true of the
tree it was measured on and `main` is a tree this repository has had since.

**One attribution in the fourth note at the head of this section does not survive
the per-suite reading, and the correction is here rather than there.** That note
gives the `1307` → `1308` step to *#1034's six cases and #1035's one, both on
`ec/tools/test_check_history_checkouts.py`*, and the two trees differ by one case
on `ec/tools/test_check_citation_lines.py` instead: that suite is 40 at
`fe92940a` and 41 at `8c51e6ed`, while `test_check_history_checkouts.py` is 30 at
both — 24 → 30 between `d3304785` and `fe92940a`, which is #1034's six, and
unmoved after. **The `1308` the note gives is right and only the attribution is
early**, so both stay written per
[`../findings.md`](../findings.md) §4a-4d; #1035's case on
`test_check_history_checkouts.py` is real and is the `1308` → `1309` step the
fifth note records — it simply landed in `5244f119`, one commit later than that
note places it, which is the same "`1307` behind `main`'s tip" shape the sixth
note above measures from the other side. **Nothing in the merged tree's own
figures moves with it**, which is what a mis-attribution is rather than a
mis-measurement, and the per-suite count is the thing that caught it — a total
taken from the runner cannot tell the two apart.

**The red set is unchanged and
pre-existing**: `ec/tools/test_check_cluster_citations.py` alone, on the same
`:220` of the same #822 file, and neither #1034, #1035, #1038 nor #1039, nor
#1032 nor any merge of them, caused it or fixes it.

**The `tools/README.md` row in the per-pin table moved with the sentence rather
than with a note, and this merge's step came out of the sentence's own
parenthetical.** The thirty-fourth records that its own row moved with the
sentence and calls the change the thirteenth in
[`test-line-pin-census.md`](test-line-pin-census.md);
**the fourteenth is this one**, and the reason is the same: every merged-tree
note in this file sits below the pin, while the parenthetical above does not.
`check_pin_table_rows.py` reads **107 rows, 107 records, 107 placed, all seven
classes 0** on the merged tree, measured rather than derived.

**The census and the by-cited-file axis are re-run rather than carried.**
`census_test_line_pins.py` reads **107 pins in 29 files, 80 spellings, 59
targets, 75 resolves against 32 declined, the `0/15/22/5/33` split, over `171`
markdown files read and `43` test files**; and
`check_pin_table_by_cited_file.py` reads **43 indexed / 12 named / 31 named by
none**. **Its branch measured `42` / `12` / `30`, and the merged tree differs on
two of the three**, because two suites were indexed rather than one — #845's and
#1009's, both cited by no line — while the named count takes the same `12` that
#1009's write-up's one pin is responsible for, since it names
`ec/tools/test_measure_index_repair_visibility.py` and that suite had none
before. **The tail comes to the same `31` the thirty-fourth arrived at by a
different route**: there by adding a suite, here by adding a suite and a
crossing. `ec/tools/test_check_pin_table_by_cited_file.py`'s
asserts are re-set to the measured triple rather than argued, with all three
superseded ones left written above them. **The `166` markdown files this
paragraph carried until this merge is the one figure in it that was a record
rather than a reading, and it is left written only in the sense that every other
superseded figure here is** — it had already stopped being true of `main` before
this merge, and nothing in the tree turned red, because the census's own count
of the population is a by-product of what it reports and no assertion holds it.
`origin/main` at `8c51e6ed` reads `169` and the `#1034` × `#1035` × `#1038`
merge's tree reads `170`, the step being that merge's own two new write-ups —
#1038's `xdata-0860-note-live-pointers.md` and #1035's
`committed-checkout-triples-held.md` — so **that `170` is measured and the `166`
was correct of a tree none of this run has**. **Re-measured on the two trees
this merge can name, the step splits in two and only one of the halves is on
`main`**: `origin/main` at `5244f119` reads `170` and this tree reads **`171`**,
and #1038's write-up is in the `169` that `8c51e6ed` already carries, so the
`169` → `170` step on `main`'s linear history is
[`committed-checkout-triples-held.md`](committed-checkout-triples-held.md)
alone. **The `170` the sentence above records and the `170` `main` reads are
therefore the same figure reached from two different pairs of commits, which is
a coincidence of arithmetic rather than a shared tree**, and both stay written
per [`../findings.md`](../findings.md) §4a-4d — the shape the fifth note
at the head of this section records for the two `1308`s, on the same two sides.
The step this merge records is then #1032's own
[`history-checkout-prompt-reach.md`](history-checkout-prompt-reach.md)
entering the corpus and citing no `test_*.py:NNN` of its own — so **the `171` is
measured, and it is the same asymmetry the sentence above describes from the
other end: a write-up that brings a denominator and no record, which is why
every other figure in this paragraph is unmoved by it.**

**And the `171`, the `43` and the `31` are a reading of the branch rather than of
this tree, so the sentence above is left written and corrected here rather than
edited.** Its run was against `origin/main` at `5244f119`, which reads `170`
markdown files and `43` test files — the `170 + 1 = 171` is that tree's own step
and the `43` was its inventory, both true where they were measured. **`main`
carried the base six files past that commit before this merge**: #1037
(`f6480168`) `+1`, #1058 (`517be444`) `+3` and #1060 (`560752b2`) `+2` on the
markdown axis and one suite each on the other, `43` → `44` → `45` → `46`, so the
merge base reads `176` markdown files and `46` test files. **Re-run on the merged
tree the census reads the same eight figures over `177` markdown files and `46`
test files** — `176 + 1 = 177`, the `+1` being this issue's own write-up again —
and `check_pin_table_by_cited_file.py` reads **`46` indexed / `12` named / `34`
named by none**, which is the triple the line above carries as `43` / `12` /
`31`. **So "the `171` is measured" is true of the tree that run was made on and
not of this one**, and the `43` and the `31` are behind for the reason the
`forty-four` and the `1316` give above: suites landed and the total was not
re-transcribed, and no assertion holds the census's own count of its own
population, so nothing in the tree turned red. **The `107`, the `29`, the `80`,
the `59`, the `75`, the `32` and the `0/15/22/5/33` split are unmoved by all of
it** — six write-ups and three suites moved the population and not one record —
and both readings stand written, per
[`../findings.md`](../findings.md) §4a-4d.

**The numbering moved a ninth time, and `main`'s is the one that does not
move.** **§84** is #974's summary, landed by `0daac768` (whose subject line
reads `(#981)`, a pipeline collision artifact rather than the section's issue),
and **§85 is #845's**, landed by `5881153d`. #1009's own summary gives way twice
over and is **§86** — to #974's §84 first, as its branch recorded, and then to
#845's §85 here. **The clause the thirty-fourth's own correction above rests on
is left as written and is true of the tree it measured**: neither §83 nor §84
carries a "last section in the file" clause of its own, and #1009's §86 does not
either — so the same correction is owed a second time, and it is
`../findings.md` §73's that carries it.

**The red set is still the one suite every note above names**, and it is
re-checked rather than carried: `ec/tools/test_check_cluster_citations.py`, 48
tests, the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` and the same two `0x0464`/`0x0465`
disagreements, failing identically on a pristine `git archive origin/main`
extraction — so neither #845 nor #974 nor #1009 caused it and none of them fixes
it.*

*(Thirty-sixth note, 2026-09-26, issue #1037, **measured on the merged tree** —
`#1034`, `#1038` and `#1039` landed on `main` beside it, so this note is a
merged-tree note like the thirty-five above and not the one-sided note its own
branch drafted. **Everything the branch recorded is left written per
[`../findings.md`](../findings.md) §4a-4d, each true of the tree it
measured on**, and named as such below, and `main` has moved under two of the
figures it quotes — where this note and that one disagree, the `8c51e6ed` figure
is the record and the `5244f119` one is this tree's.)*

**The runner reads `44 suite(s) run, 1316 tests; one or more FAILED`, and
`python3 -m unittest discover -s ec/tools` reads `1012`** — both re-run on this
tree, in a full clone (`git rev-parse --is-shallow-repository` answers *false*),
for the reason the thirty-fifth gives. **`1309 + 7 = 1316` and `1005 + 7 =
1012`**, the seven being #1037's one new suite
`ec/tools/test_check_history_checkouts_run.py` and nothing else, against
`origin/main` at `5244f119` reading `43`/`1309` and `1005`; and `1301 + 7 =
1308` and `997 + 7 = 1004` is **the branch's own arithmetic against the base
`d3304785`**, which lands on `1308`/`1004` — the same pair main's own note above
measured at `8c51e6ed`, from the other side. That agreement is arithmetic, not a
reading: `d3304785` → `fe92940a` is #1034's six, `fe92940a` → `8c51e6ed` is
#1038's one, `8c51e6ed` → `5244f119` is the seventh case
`test_the_table_turns_red_on_each_of_the_two_edits_it_exists_for`, and this
landing's seven are a new suite, so no one of those four figures is a reading of
this tree and the sum is. **The suite count's step is `43` → `44` and it is
#1037's alone** — every case the three landings on `main` added was a case on a
suite already counted, and none of them added a suite. The `1301`/`997` the
thirty-fifth records, the `1308`/`1004` this landing's branch measured, and the
`1315`/`1011` the branch's own note recorded all stay written above and in the
supersession paragraph at the top of this file, each true of the tree it was
measured on, per §4a-4d.

**The report suite is not what this landing's branch found, and the reason is
`main` rather than this change.** The branch recorded
`test_check_history_checkouts.py` as **still 24 and still green, byte-identical**;
it is **31** on this tree, the six #1034 added on `main` beside it and the
seventh that followed — `thirty` on this landing's own branch, and both written
here rather than one of them, per §4a-4d. This landing still does not edit that
file, and the property the claim is for holds on the merged tree rather than by
carry — re-measured, not assumed: **all thirty-one read the report and none
reaches `main()`**, so the issue's `sed -i 's/    if problems:/    if False:/'`
still leaves the whole file green and still turns the new suite red on the
stale-tree case alone. Both halves of that are re-run here on a full copy of the
tree rather than a `git archive` extraction, because a copy missing `.github/`
turns the report suite's own committed-tree cases red for a reason that has
nothing to do with the mutation.

**The red set is one suite again, and it is re-checked rather than carried.**
`ec/tools/test_check_cluster_citations.py` — 48 tests, the single failure, on the
same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements, failing identically on a clean worktree of
`origin/main` at `5244f119` — so neither #1034, #1038, #1039 nor #1037 caused
it and none of them fixes it. **Two suites went red while this landing was being built
and neither is left red, and the two are not the same kind of event**:
`ec/tools/test_check_pin_table_by_cited_file.py` went red on the indexed-suite
count, which is the mechanical consequence of adding any suite at all, and its
`assert`s are re-set to the measured triple below;
`ec/tools/test_check_pin_table_rows.py` went red on a **line pin into
`ec/tools/test_check_history_checkouts.py`** the new write-up cited, and that
one was avoidable — see the census paragraph below. Both are named here because
the first is a chore and the second is a decision a later reader would otherwise
have to re-make.

**The census and the by-cited-file axis are re-run rather than carried, and two
of the figures the thirty-fifth records moved for a reason worth writing down.**
`census_test_line_pins.py` reads **107 pins in 29 markdown files, 80 spellings,
59 targets, 75 resolves against 32 declined, the `0/15/22/5/33` split, over
`171` markdown files read and `44` test files**; `check_pin_table_by_cited_file.py`
reads **44 indexed / 12 named / 32 named by none**; and `check_pin_table_rows.py`
reads **107 rows, 107 records, 107 placed, all seven classes 0**. **Only the two
file counts moved from the thirty-fifth's `166` and `43`**, and they moved by
three pages and one suite rather than the one page and one suite the branch
recorded: `167` at `d3304785`, `169` at the base `8c51e6ed`, **`170` at
`origin/main`'s `5244f119`** after #1034's
`history-checkout-claim-per-workflow.md`, #1038's
`xdata-0860-note-live-pointers.md` and #1035's
`committed-checkout-triples-held.md`, and **`171` here** with this landing's
`history-checkout-run-contract.md`; `43` indexed test files through `main` and
`44` here. The pin, spelling, target, verdict and shape counts are unmoved
through all four, which is what keeps the 107-row table reconciling at 107.

**That is a decision, and the decision is why the write-up names a test case
instead of citing a line.** #1037's
`docs/findings/history-checkout-run-contract.md` first cited
`ec/tools/test_check_history_checkouts.py` `:255` for the report suite's "one
unreadable file beside a conforming one is still a measurement" case, and
`check_pin_table_rows.py` refused it: a pin into a test file is a registered
one, and adding a record moves the 107 / 80 / 59 above and the 107-row table
itself. The page names the case by name instead — the same choice #845's own
write-up made two issues ago, and for #811's reason. **The alternative was to add
the row and re-derive every figure above, which is a large edit to four
shared-file tests for one citation**, and `CLAUDE.md` asks for small edits to
shared files precisely because other PRs are open against them.
`ec/tools/test_check_pin_table_by_cited_file.py`'s `assert`s are re-set to the
measured `44 / 12 / 32` rather than argued, with all three superseded triples
left written above them — and that triple is **the one the branch measured too**,
so this landing's edit to that suite survives the merge without a second
re-measure, `main` itself still reading `43 / 12 / 31`. **This note cost a fifth
repoint of this file's own pin, and the sixth supersession paragraph at the top
of this file cost it the fourth.** The row for the `test_xdata_cluster_names.py`
claim this file records stood at `:431` on `origin/main` and is at `:467` here:
thirty-six lines added above it by that sixth paragraph, and by nothing to do
with the claim the row reconciles. The branch recorded `:387`, off a `main` that
had not yet carried the fourth and fifth paragraphs, and `:279` before that,
which was already the wrong line on its own tree — `:341` there — so this row
has now moved five times at merges that were not about it, and the row's verdict
cell says so in the established style, keeping `:387` written beside it per
§4a-4d. `check_pin_table_rows.py` reconciles **107 rows against 107 records, all
seven classes 0**, re-measured rather than carried.
*(Thirty-seventh merged-tree note, 2026-09-26, issues #1008 × #845, **and it is
renumbered from the thirty-fifth its branch first gave it because `main` held that
number first** — the note above took it for the `#845` × `#1009` tree, the same
collision the tenth note records from the other direction and the same rule.
**Every figure in this note is left as it was measured, per
[`../findings.md`](../findings.md) §4a-4d, and none of the three is this
tree's**; the notes below carry what this tree reads. **The first
merge in this run with a `test_*.py` on both sides at once**, and the sentence
above is re-derived for it rather than stepped: `bash tools/run-tests.sh` on
*that* tree read **`43 suite(s) run, 1314 tests; one or more FAILED`** and
`python3 -m unittest discover -s ec/tools` read **`1010`**, both measured by
running the two commands there before the arithmetic was written down. **The step
is additive from either side, which is the first time on this sentence that it
is**: a clean `origin/main` worktree at `5881153d` read `1277` and `973` over
forty-two suites, so `1277 + 37 = 1314` and `973 + 37 = 1010` with the
thirty-seven #1008's, and #1008's own `1308` and `1004` plus #845's six is the
same pair. **The thirty-fourth's `1277`/`973` and #1008's `1308`/`1004` stay
written above**, each true of the tree it was measured on, per
[`../findings.md`](../findings.md) §4a-4d, and the `1271`/`967` both
sides built on is the pair a reader can still add either side's step to.

**The red set is one, and this merge was briefly the reason it was two.**
`ec/tools/test_check_cluster_citations.py` — 48 tests, the single failure, on the
same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements against `main-ec-145` — reproduces on a clean
`origin/main` worktree at `5881153d`, re-run here rather than carried, so neither
#1008 nor #845 caused it and neither fixes it.
`ec/tools/test_check_pin_table_rows.py` read `FAILED (failures=4)` while the
`../../tools/README.md` row in the per-pin table still named `:312`, and is
**green at 36** with `:354`: the parenthetical above the pin is what moved it, by
both sides' step, and the four is a function of the row naming a line this file
no longer has rather than a count of anything — the property the re-registration
is run for, and the eighteenth note's own measurement.

**Two pins in the tree moved with the suite, and the one a reader of this file is
most likely tracking is re-registered.** `suites()` in
`ec/tools/census_test_line_pins.py` indexes every `test_*.py`, so
`ec/tools/test_check_pin_table_by_cited_file.py`'s committed index figures go
**42 / 11 / 31 → 43 / 11 / 32** — two suites, not one, and that is the first time
on this axis: #845's `ec/tools/test_trace_xdata_refs.py` and #1008's
`ec/tools/test_census_index_third_column_edits.py` each landed beside #978's on
their own side, each measured `42 / 11 / 31` against a tree the other side's
suite was not on, and each was right. Neither is named by a pin, so the pin count
stays **106** and `len(files) - len(tail)` stays **11**; that suite's own asserts
are re-set to the measured value rather than argued, with the superseded triple
left written in the same shape the sixth through tenth steps left theirs. **The
`tools/README.md` row in the per-pin table is now the fourteenth change
[`test-line-pin-census.md`](test-line-pin-census.md)
records, and the eighth value one pin has carried** — `:279` → `:292` → `:312` →
`:354`, the middle two being the two sides' own — which corrects the thirty-fourth
note's "the thirteenth change … the seventh re-registration for that one row"
above without editing it, on the rule §4a-4d sets. The census's own **106 / 79 /
58 are unmoved**: both write-ups cite their suite *by path* and never as
`<module>.py:NNN`, so the same pins are read at their new lines and none was
added or removed, and `check_pin_table_rows.py` reads **106 rows, 106 records,
106 placed, all seven classes 0**.*

*(Thirty-eighth merged-tree note, 2026-09-26, issues #1008 × #1009. **The step
from the note above is one suite and thirty-seven cases, and it is entirely
#1008's** — #1013 and #1034 both landed on `main` after that branch forked, so
nothing on `main`'s side of this merge is a figure this tree did not already
carry. `bash tools/run-tests.sh` on this tree reads **`44 suite(s) run, 1344
tests; one or more FAILED`** and `python3 -m unittest discover -s ec/tools` reads
**`1040`**, both re-measured here; a clean `origin/main` worktree at `fe92940a`
reads **`43` / `1307`** and **`1003`**, so `1307 + 37 = 1344`, `1003 + 37 = 1040`
and `43 + 1 = 44`. **The notes above's `1314` and `1010` stay written and are
neither of them this tree's**, true of the `#1008` × `#845` tree per
[`../findings.md`](../findings.md) §4a-4d, and the thirty-fifth note's
`1307` and `1003` stay written for the `#845` × `#1009` × `#1034` tree the same
way. **This
is the first merge in this run with no figure to choose between**: the two sides'
steps do not compose, because `main`'s two commits are already inside the base
this tree was built from, so the sentence under "What it runs" is a
re-derivation rather than a sum — the rule the twenty-fifth note below states,
applied for the second time and for a different reason than the first.*

**The red set is one suite, and this merge was briefly the reason it was two.**
`ec/tools/test_check_cluster_citations.py` — 48 tests, the single failure, on the
same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md` with the same two
`0x0464`/`0x0465` disagreements against `main-ec-145` — is red identically on a
pristine `git archive origin/main` extraction and in the clean `origin/main`
worktree above, re-checked here rather than carried, so neither #1008 nor #1013
nor #1034 caused it and none of them fixes it. The other was
`ec/tools/test_check_pin_table_rows.py` at `FAILED (failures=4)`, and it is
**green at 36** now that the per-pin table's rows are re-registered: the row whose
count moved is the `../../tools/README.md` one, **`:370` → `:478`**, four of those
lines being a supersession note for the suite totals in this very file and none of
them about the claim that row reconciles. **Six rows moved a citing line and none
was added**, so the census's own **107 / 29 / 80 / 59** are unmoved by this merge
— the same pins read at their new lines — and `check_pin_table_rows.py` reads
**107 rows, 107 records, 107 placed, all seven classes 0**.

**The index triple moves once more, and to a figure neither side held.**
`ec/tools/test_check_pin_table_by_cited_file.py` reads **`44` indexed / `12` named
/ `32` named by none**, and the thirty-fifth's `43` / `11` / `32` and the
thirty-sixth's `43` / `11` / `32` each stay written for the tree they measured.
The step is `43 + 1 = 44` and `32 + 1 - 1 = 32`: #1008's suite joins the tail,
and #1009's pin — the one that put `ec/tools/test_measure_index_repair_visibility.py`
into the named table — is still in the tree, so the named count holds at the `12`
`main` reached and the tail's own figure is unmoved from the thirty-sixth's. That
suite's asserts are re-set to the measured triple rather than argued, with all
three superseded ones left written in the same shape the sixth through tenth steps
left theirs, and the comment above them records all three merges' steps rather
than this one's alone.*
*(Thirty-ninth merged-tree note, 2026-09-26, issues #1008 × #1037, and **the step
is one suite and thirty-seven cases of #1008's alone** — #1037's seven are already
in this tree's base rather than in either side's step, for the reason the
thirty-eighth note gives for #1039's one case. `bash tools/run-tests.sh` on this
tree reads **`45 suite(s) run, 1353 tests; one or more FAILED`** and
`python3 -m unittest discover -s ec/tools` reads **`1049`**, both re-measured
here; a clean `origin/main` worktree at `f6480168` reads **`44` / `1316`** and
**`1012`**, so `1316 + 37 = 1353`, `1012 + 37 = 1049` and `44 + 1 = 45`. **The
eighth note's `1346` and `1042`, the seventh's `1344` and `1040` and the sixth's
`1316` and `1012` stay written and none of them is this tree's**, each true of
the tree it was measured on per
[`../findings.md`](../findings.md) §4a-4d. **Every figure here is
measured by running the runner on the tree it is written about** and not
differenced, the rule the notes above give, on a working tree whose clone is full
— `git rev-parse --is-shallow-repository` answers *false* — so the three cases
`test_measure_index_repair_visibility.py` skips on a shallow one did run.

**The red set is one suite, pre-existing, and this merge was briefly the reason
it was two.** `ec/tools/test_check_cluster_citations.py` — 48 tests, the single
failure, on the same `:220` of #822's `xdata-cluster-names-guard-off-recipe.md`
with the same two `0x0464`/`0x0465` disagreements — is red identically in the
clean `origin/main` worktree above, so neither #1008 nor #1037 caused it and none
of them fixes it. The other was **`ec/tools/test_check_pin_table_rows.py` at
`FAILED (failures=1)`**, and **it is the first merge in this run whose red set
grew by a suite rather than by a stale citing line**: the `../../tools/README.md`
row in the per-pin table named the line this file carried on `origin/main`, and
this merge added three supersession paragraphs above it — #1008's, this one's and
#1037's own — so the row is re-registered to the line this tree carries rather
than to either side's. **No pin was added and none removed**, so the census's own
**107 / 29 / 80 / 59** are unmoved by this merge — the same pins read at their new
lines — and `check_pin_table_rows.py` reads **107 rows, 107 records, 107 placed,
all seven classes 0**.

**The index triple moves once more, to `45 / 12 / 33`, and this is the first step
on it that adds a suite on each side at once.** `origin/main` reads `44` indexed /
`12` named / `32` named by none and this tree reads **`45` / `12` / `33`**: both
#1008's `ec/tools/test_census_index_third_column_edits.py` and #1037's
`ec/tools/test_check_history_checkouts_run.py` are indexed and **neither is named
by a committed pin, so neither crosses a table** and the named count holds at the
`12` `main` reached. **That is the property the re-registration is run for and
the reason the second suite cost no re-reading**: a suite in the tail moving is the
cheap direction, and this merge moved it twice. That suite's asserts are re-set to
the measured triple rather than argued, with all four superseded ones left written
in the same shape the sixth through eighth steps left theirs, and the comment
above them records every merge's step rather than this one's alone.*

*(Thirty-seventh note, 2026-09-27, issues `#1070` × `#1060` × `#1058` ×
`#1043` × `#1030`, **measured on the merged tree** — four landings on `main`
beside this one, so like the thirty-six above it is a merged-tree note and not
the one-sided note #1030's own branch drafted. **Everything that branch recorded
is left written per [`../findings.md`](../findings.md) §4a-4d, each
true of the tree it measured on**, and `main` has moved under every figure it
quotes — where this note and that one disagree, the `5244f119` figure is the
record and the `58f43ee7` one is this tree's.)*

**The runner reads `46 suite(s) run, 1435 tests; one or more FAILED`, and
`python3 -m unittest discover -s ec/tools` reads `1073`** — both re-run here, in
a full clone (`git rev-parse --is-shallow-repository` answers *false*), for the
reason the thirty-fifth gives. **The suite count's step is `44` → `46` and it is
`main`'s rather than this landing's**: #1058's `ec/tools/test_pd_image_census.py`
and #1060's `bios/tools/test_ifr_census.py` are two new suites, and #1030 adds
none — `ec/tools/history_checkout_sites.py` is a tool one suite reads rather
than a `test_*.py`, and a case on a suite already counted is not a suite. **The
case step is #1030's alone**, `ec/tools/test_check_history_checkouts.py`
reading **31 cases on `main` and 37 here**, so `1429 + 6 = 1435` on the runner
and `1067 + 6 = 1073` on the discover command, and the suite count is `46` on
both. **`origin/main` reads `1429` only with the runner repair the last
paragraph gives applied to it as well** — its own copy of the runner stops at
`28 suite(s) run, 903 tests` and prints no total, so the figure this note
compares against is a reading of a tree one line different from `58f43ee7`'s
and is named as such rather than quoted as `main`'s. The `43`/`1315` and
`1005`/`1011` #1030's branch recorded, the `44`/`1316` and `1012` the sixth note
records and the `43`/`1309` and `1005` the seventh all stay written above, each
true of the tree it was measured on, per §4a-4d.

**Two of `main`'s four landings are not in the count the notes above were
measured against, and the head sentence moves because of them rather than
because of this merge.** The `forty-four` the sixth note wrote was `main`'s at
`5244f119`; the four commits since added two suites, **seven** markdown files
(the census's own file count, `170` → `177`) and one more table row, and not
one of them wrote a note here. `main` itself
reads `46` today and says `forty-four` — **its own copy of this sentence is one
merge behind its own suite count**, the same shape the third note records for
`1308` against `1307`, and the same reason a figure here is measured by running
the runner rather than differenced.

**The red set is two suites, both pre-existing on `origin/main` at `58f43ee7`
and neither of them this landing's.** `ec/tools/test_check_cluster_citations.py`
— 48 tests, the single failure in it, on the same `:220` of #822's
`xdata-cluster-names-guard-off-recipe.md` with the same two `0x0464`/`0x0465`
disagreements against `main-ec-145`, the one every note above names and the one
none of them fixes. And `ec/tools/test_check_doc_figure_pins.py`, whose
`test_a_hex_address_is_not_a_figure_and_the_run_beside_it_is` reads `86` as
`held-by-check-literal` where it expected `unheld` — **new since the sixth note,
and #1058's rather than this landing's**: it is the checker disagreeing with a
figure on the `pd-image.md` that commit added, and which side of the
disagreement is right is a reading of #1058's page rather than an edit this
merge should make. Re-checked rather than carried: both fail identically on a
clean worktree of `origin/main` at `58f43ee7`.

**Two of `main`'s four landings left work undone that this merge's own tree
shows, and both are recorded here rather than left for a reader to find.** The
first is `ec/tools/test_pd_image_census.py` landing at #1058 with no row in the
table below, which is the one step the inventory cannot do for itself:
`tools/test_readme_suite_table.py` was red on `main` for exactly that, and the
row is added here — written from the suite's own docstring, with the gate note
that suite carries. The second is the runner itself: **a suite that *runs* other
suites prints their summaries too**, so `ec/tools/test_pd_image_census.py`'s
three `Ran N tests` lines — `1`, `1` and its own `55` — reached
`run-tests.sh`'s tally as three numbers, `$((tests + ${n:-0}))` died on a syntax
error, and **the runner stopped partway through and printed no total at all**,
on `main` as much as here. `sed … | tail -1` is the fix and it is the suite's
own summary that is wanted; without it every figure this file quotes is
unreachable on a tree carrying that suite, which is a §14b failure mode one
level up. Neither of the two is a change to a check — the suite table is the
set, and the runner still reports its totals rather than asserting them.

**The census and the by-cited-file axis are re-run rather than carried.**
`census_test_line_pins.py` reads **107 pins in 29 markdown files, 80 spellings,
59 targets, 75 resolves against 32 declined, the `0/15/22/5/33` split, over `178`
markdown files read and `46` test files**; `check_pin_table_by_cited_file.py`
reads **46 indexed / 12 named / 34 named by none**; and `check_pin_table_rows.py`
reads **107 rows, 107 records, 107 placed, all seven classes 0** — the last of
those three **green on this tree and red on `origin/main`**, where six rows
citing `docs/findings.md` carry the lines that tree had before #1058, #1060 and
#1070 added theirs. The pin, spelling, target, verdict and shape counts are
unmoved on both sides, which is what keeps the 107-row table reconciling at 107;
`main` reads `177` markdown files and this tree `178`, the step being #1030's
own `history-checkout-site-identity.md` for the second time, and both read `46`
test files and `12`/`34` on the by-cited-file axis.

**This file's own row of the per-pin table moved again, and the row says so in
the established style.** It stands at `:543`, having read `:431` before either
of the two notes above, `:466` on #1030's branch and `:467` on `main`: **`:467`
→ `:543` under this merge**, by the three supersession paragraphs at the top of
this file, the **fifteenth** re-registration for that row and again by a note
about a test total rather than by anything to do with the
`test_xdata_cluster_names.py` claim it reconciles. **The other row this merge
moved is `history-checkout-claims.md`'s**, `:262` on `main` and `:288` on
#1030's branch to **`:298`** here, the sum of the two sides' additions above
it, and the census page's correction records it in the same sentence.
`check_pin_table_rows.py` reconciles **107 rows against 107 records, all seven
classes 0**, re-measured rather than carried.

*(Thirty-eighth note, 2026-09-27, the `#1032`/`#1040` × `#1076` × `#1030`
merge, **measured on the merged tree** — and the step is a case step again
rather than a suite step, because `main` has taken two commits since the
thirty-seventh above was measured and **neither of them added a suite**.)*

**The runner reads `46 suite(s) run, 1443 tests; one or more FAILED`, and
`python3 -m unittest discover -s ec/tools` reads `1081`** — both re-run here, in
a full clone (`git rev-parse --is-shallow-repository` answers *false*), for the
reason the thirty-fifth gives, and the runner reaches a total at all because
the repair the thirty-seventh records came in with this landing.
`origin/main` at `a6a7df7a` reads **`1437`** and `1075` from those same two
commands — **the `1437` with this landing's `tools/run-tests.sh` dropped into
`main`'s tree**, since `main`'s own copy of the runner still stops at
`28 suite(s) run, 911 tests` and prints no total at all, so that figure is a
reading of a tree one file different and is named as such rather than quoted as
`main`'s — and `agent/issue-1030` at `85a324ec` reads **`1435`** and `1073`, so
**`1437 + 6 = 1443` and `1075 + 6 = 1081`**, the six being #1030's six in
`ec/tools/test_check_history_checkouts.py` and nothing else, that suite
reading **39 cases on `main`, 37 on the branch and 45 here**. **The suite count
does not move at this step** — the same `forty-six` the step above it recorded,
because #1032's eight cases are a case step and #1076's
`ec/tools/bank_attribution.py` is a tool rather than a `test_*.py`, and a
tool is not a suite. The `1435` and the `1073` the thirty-seventh records and
the `1429` it measured them against all stay written where they were measured,
per [`../findings.md`](../findings.md) §4a-4d, as do the `1315`, the
`1316`, the `1317` and the `1437` the paragraphs at the head of this file carry.

**The red set on this tree is two suites, and this landing is what took
`main`'s third away rather than what caused one.** `origin/main` at `a6a7df7a`
is red on `ec/tools/test_check_cluster_citations.py` and
`ec/tools/test_check_doc_figure_pins.py` — the two the thirty-seventh names,
each on the same disagreement and each re-checked on a clean worktree rather
than carried — and on `tools/test_readme_suite_table.py`, which #1030's row for
`bios/tools/test_ifr_census.py` cleared, the thirty-seventh having recorded why
that row was missing. **The six `../findings.md` rows reconcile at `main`'s
lines rather than the branch's**, because #1030's write-up to that file lands
at its `:11553` here, below all six, so the merged tree reads what `main` reads and
the branch's `:4230`-side reading is left written in the census page's own
correction. The runner's "one or more FAILED" is those two suites and not this
merge's.

**The census and the by-cited-file axis are re-run rather than carried.**
`census_test_line_pins.py` reads **107 pins in 29 markdown files, 80
spellings, 59 targets, 75 resolves against 32 declined, the `0/15/22/5/33`
split, over `180` markdown files read and `46` test files**;
`check_pin_table_by_cited_file.py` reads **46 indexed / 12 named / 34 named by
none**; and `check_pin_table_rows.py` reads **107 rows, 107 records, 107
placed, all seven classes 0**. The `178` the thirty-seventh recorded is **one
behind again**, `180` being `179` on `main` at `a6a7df7a` plus #1030's own
write-up for the third time — the same shape that note records for the
`forty-four` against `forty-six`, and the same reason: neither of `main`'s two
commits wrote a note here.

**Two rows of the per-pin table moved rather than one pin being added, and both
are re-registrations of a citing line.** `history-checkout-claims.md`'s single
pin reads `:278` on `main` and `:298` on #1030's branch and **`:314`** here,
the sum of the two sides' additions above it — #1032's sixteen-line correction
blockquote against #1030's two sections — and `tools/README.md`'s own row reads
`:584` on `main` and `:543` on #1030's branch and **`:660`** here: **`584 + 76 =
:660`**, and all seventy-six are the five supersession paragraphs at the head
of this file that **neither side's tree carried in full** — `main`'s three under
#1032 and #1037 against the branch's two under #1030, every one of them about a
test total and none of them about the `test_xdata_cluster_names.py` claim the
row reconciles. **This note costs that row nothing, being written below it.**
The census page's own correction records both rows in the same sentence.

