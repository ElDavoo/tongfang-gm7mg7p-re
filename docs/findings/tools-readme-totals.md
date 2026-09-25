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
