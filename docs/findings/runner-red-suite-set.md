# The runner's red set, and the third of #162's blocker that was a missing table row (issue #751)

The write-up for [issue
#751](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/751), which is
about `docs/findings/0751-grader-self-test-gate.md` counting the runner's
failing suites as **two** when three were failing. What this branch changes is
one row in a hand-written table, the sentence that counted the failures
corrected in place beside itself, and this file.

**Nothing here is a hardware claim.** No register was read back, no capture was
opened, and no laptop, EC or Windows machine is involved. The one suite this
branch describes reads the committed firmware image, and that is a file read,
not an observation of a machine. Every figure below is a `find`, a `git`, or
arithmetic over committed files.

## What fails, and why the corrected text carries no number

Two suites fail on their subject, and they are the two
`0751-grader-self-test-gate.md` already names — `ec/tools/test_check_site_census.py`
on 14 `census_refs` line disagreements against an `ec/decompiled/bank0/D091.c`
that was hand-corrected on 2026-09-24 for #180, and
`ec/tools/test_xdata_cluster_names.py` on #528's `==`-guard failure, which
raises in `setUpClass` before any case runs. A third was failing for a
different reason entirely: `tools/test_readme_suite_table.py`, because
`ec/tools/test_inc_dptr_sites.py` had no row.

```
$ bash tools/run-tests.sh            # before this branch
ec/tools/test_check_site_census.py: FAILED
ec/tools/test_xdata_cluster_names.py: FAILED
tools/test_readme_suite_table.py: FAILED
...                                  # the totals line is deliberately not quoted

$ bash tools/run-tests.sh            # after
ec/tools/test_check_site_census.py: FAILED
ec/tools/test_xdata_cluster_names.py: FAILED
...                                  # and again
```

**The two `FAILED` lines are the whole diff, and the totals line is left out on
purpose.** A total is a property of the merge, not a property of any suite: it
moves when a suite lands, when a case is added to one, and when a test is
removed, none of which has anything to do with what fails. `0751-grader-self-test-gate.md:38-41`
already made that choice for its own figure and this one inherits it — the
issue's own quoted total is not repeated here for the same reason, and pasting
it into a file is how the sentence being corrected came to be wrong in the first
place.

**What the third was, exactly.** `tools/run-tests.sh` finds its suites with
`find`, so a committed `test_*.py` is collected silently and runs. The one step
the runner cannot do for itself is writing the row beside it in
`tools/README.md`, and `test_readme_suite_table.py::test_every_discovered_suite_has_a_row`
is the check that says when that step was missed:

```
AssertionError: ['ec/tools/test_inc_dptr_sites.py'] is not false : tools/README.md
lists no row for 1 discovered suite(s):
  ec/tools/test_inc_dptr_sites.py
```

**No judgement about a decompile was involved.** The suite was green on its own
before this branch and is green now — 28 cases over the 107 / 73 / 34 / 27
figures `ec/annotations/xdata-inc-dptr-only.md` is written on, each re-derived
by the tool's own `build()` rather than read off the committed CSV. It was the
*index* that was stale, not the thing indexed. That distinction is the reason
the correction is a retraction of bookkeeping rather than a finding.

## The decomposition of #162's blocker, which is the part that outlives this branch

`docs/agent-pipeline.md` carries the four-line call that would put
`tools/run-tests.sh` in the cheap tier, and it is not landed because the runner
is red. That is a real blocker and it is still one, but it was **three suites
in two kinds**, and the two kinds want different owners:

| kind | suites | what unblocks it |
|---|---|---|
| a judgement about the decompile | `ec/tools/test_check_site_census.py`, `ec/tools/test_xdata_cluster_names.py` | each has its own issue and its own owner; one is whether the `census_refs` lines move or the counts change, which is not a mechanical edit |
| bookkeeping in the runner's own index | `tools/test_readme_suite_table.py` | one row in a hand-written table, landed here |

**Whoever lands #162 re-derives the failing set at that moment rather than
trusting this list**, and should expect two rather than three. That is the
useful part of the correction: the sentence the decision rests on was one low,
so the blocker it measured was one suite larger than the decision assumed, and
the extra one was the cheapest thing on the list. A reader who took "two" as
the size of the blocker would have been waiting on something already fixed.

The gate wiring is not landed by this branch for the two reasons that file
gives, and neither of them moved: `.github/scripts/agent-gates.sh` is copied
from `ElDavoo/agent-pipeline` and this pipeline's push token has no `workflow`
scope, and the runner is still red on the two judgement calls above.

## The counts sentence, and the check that deliberately cannot see it (#615)

`tools/README.md:14` carries its own "there are N today, M tests in all"
sentence. It is **out of date on this tree**, no test fails because of it, and
it is not this issue's to fix: the counts are #615's, and this issue is
explicitly told not to fold that in. The line is byte-untouched.

**The reason no test notices is a decision, not an oversight, and it is worth
stating because a green runner can be misread.** Three places say the same
thing:

- `tools/test_readme_suite_table.py:11-20` — the docstring says it compares the
  *set* and never the counts, because "an expected count turns every added test
  into a failure, which is the wrong trade", and then that the descriptions are
  prose the runner has no reason to know.
- `tools/README.md:58-63` — the table's closing paragraph says the row stays
  hand-written and the runner has no reason to know the descriptions.
- `tools/run-tests.sh:75-79` — the runner prints its totals and asserts none,
  for the same reason, one level up.

So a stale count is invisible to every check in the tree **by design**, and the
trade is deliberate: a wrong number nobody is blocked by is cheaper than a
right number that turns every added case red. `docs/findings/testdata-index-check.md:207-210`
records the same interaction for #727, where the table grew a row and the
counts did not move.

**One correction to the issue's own premise, because it is the reason the
interaction is smaller than it sounds.** The issue says adding a row "will move
those figures again". It does not, and cannot: the row documents a suite the
`find` had already discovered and the runner had already counted, so the
sentence's figures are untouched by it. What moves those figures is a new
`test_*.py`, or a case added to an existing suite — which is exactly what has
happened to them since they were written, and why they are out of date. Adding
rows to the table has never once moved them, because the table is not what the
runner reads.

**The other direction of the same check is green**, and was before this branch:
`test_every_row_names_a_discovered_suite` compares the same set the other way
round, so a row outliving its file would have failed too. One missing row fixes
the suite; the fix was not to loosen either assertion.

## The tool's issue is #707 in this tree, not #734

The issue body calls `ec/tools/inc_dptr_sites.py` "the tool #734's title
describes". Nothing in the tree mentions #734. The suite's own docstring
(`:1-3`), `ec/annotations/xdata-inc-dptr-only.md:1` and `docs/findings.md` §40
all say **#707** — the tool's own docstring names no issue at all — and the row
added here follows the tree rather than the issue. Recorded so a human can
settle it: if #734 turns out to be a later follow-up on the same tool, the
attribution is a one-clause edit in three files and nothing else here depends
on it.

## Left out on purpose

- **The two remaining red suites.** Each is another issue's, and one of them is
  a judgement about the decompile rather than a mechanical edit. Naming them is
  the point; fixing them is not, and the census follow-up in particular belongs
  to whoever owns #180's correction.
- **`tools/README.md:14`'s counts sentence** (#615), and `ec/README.md`, whose
  pointer to the runner carries no red/green claim and so has nothing to
  correct.
- **The gate wiring** (#162), as above: template-copied file, no `workflow`
  scope, and a runner still red on two suites that are not this issue's.
- **A new test.** `test_readme_suite_table.py` already checks this in both
  directions and by name, and it is the test — this branch is the input it was
  asking for. A second check over the same table would duplicate the runner's
  own printed-not-asserted rule, and the issue's "the row's description
  survives a re-read" clause is a reviewer step, not a mechanised one, for the
  reason `tools/README.md:58-63` gives: the descriptions are prose and the
  runner has no reason to know any of it.
- **Any upstream pull request**, and any live hardware, Windows, or EC/BIOS/
  Windows work. Nothing in this branch ends at an upstream contribution, so
  there is no prepared patch to hand over.

## Nothing else moved

No register `status:` moved, no `static_refs*` count moved, no `.asm` or `.c`
was hand-edited, `ec/annotations/registers.yaml` and
`ec/annotations/xdata-inc-dptr-only.csv` are untouched, no `.github/` file was
edited, and no gate was weakened. The change is a table row, a correction kept
beside the sentence it corrects, this file, and one appended section of
`docs/findings.md`. #162, #615, #528, #180's census follow-up and the grader's
own `--self-test` wiring are all still open.
