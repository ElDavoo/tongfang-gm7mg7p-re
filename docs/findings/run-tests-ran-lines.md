# A suite that runs other suites, and which of its summary lines is its own (issue #1072)

The write-up for [issue
#1072](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/1072), which is
about `tools/run-tests.sh` taking a suite's test count from a `Ran N tests`
line in its transcript without saying that the transcript carried more than
one. What this branch changes is that one decision in the runner, a suite that
holds it, and this file.

**Nothing here is a hardware claim.** No register was read back, no capture was
opened, and no laptop, EC or Windows machine is involved. The evidence base is
`bash tools/run-tests.sh` over committed Python and the transcripts it prints.
The one suite whose real run is quoted reads the committed firmware image,
which is a file read.

## What the transcript actually carries

`unittest` prints one `Ran N tests` line per **run**, and a suite that runs
another suite by `subprocess` puts that run's summary on the same stream. So
the number of summary lines in a suite's transcript is not the number of suites
the runner ran, and reading one line out of several is a choice rather than a
lookup. On this tree, from the repository root:

```
$ python3 -m unittest discover -s ec/tools -p test_pd_image_census.py 2>&1 \
    | grep -E '^Ran'
Ran 1 test in 0.000s
Ran 1 test in 0.000s
Ran 55 tests in 9.482s
```

Three lines, and only the last is that suite's own run — the two one-case
figures are the throwaway suites it drives. How many cases that suite has of
its own is its own business and moves when a case is added, so it is not
repeated here; `bash tools/run-tests.sh ec/tools/test_pd_image_census.py`
prints it.

The mechanism behind the extra lines is that the suite drives them with
`subprocess.call([sys.executable, path])` — see `test_pd_image_census.py`'s
`test_self_test_runs_a_suite_and_hands_back_its_exit_code`, which writes both
files itself into a `TemporaryDirectory` and points
`pd_image_census.self_test()` at them. That is what puts their transcripts on
this stream: not a nested `unittest` import, and not `--self-test` on the tool.

**The mechanism this branch corrects in the runner's own comment.** The comment
`run-tests.sh` carried named `disasm8051.py --self-test` and a stub as the
source of the extra lines. That is not what happens: the suite calls
`pd_image_census.py`'s own `self_test()`, over files it writes, and both are
run by `subprocess`. A comment naming the wrong mechanism is the failure the
calibration rule is about, so it is corrected where it stood rather than
dropped.

## Why position was not enough to fix it

Taking the last line made the arithmetic stop dying, and left three things
wrong, none of them visible on a run that passed.

**A guess that looks like a lookup.** The last line is the suite's own run
*because* the suites it drives run inside its own cases. A suite that drove
them after its own summary would be first, and its transcript would be
byte-for-byte the same shape as this one's — three `Ran` lines, and nothing in
the output saying which is which. `tail -1` cannot tell those two suites apart,
and it silently picks one answer for both.

**The choice was invisible.** The per-suite line read
`test_x.py: 2 tests, passed` whether the 2 came from one summary line or was
chosen out of three. A reader has no way to tell a total that was looked up
from one that was picked, and the total is read off exactly this output.

**Nothing detected the shape.** A suite that started running other suites
tomorrow would be mis-summed the same way this one was, and the run would stay
green. That is the same defect `docs/findings/runner-red-suite-set.md` writes
about one layer up, where a figure of the wrong kind reads as a figure of the
right kind.

## What the runner does now

Per suite, over every summary line the transcript carries:

- **One line** — counted as before, and nothing extra printed. A suite that
  needed no decision should not look like it got one.
- **More than one, recorded** — the line named by the record counts, and the
  suite's own line says so, every run: how many summary lines the transcript
  carried, and which one was taken.
  `ec/tools/test_pd_image_census.py: 55 tests, passed; counted the last of 3
  summary lines` — the one nesting suite on this tree, and the only place the
  runner makes a choice today.
- **More than one, not recorded** — refused. A message to stderr names the
  suite, the number of summary lines it printed, and the one step that resolves
  it, and the run does not pass.

The record is `ran_line_for` in `run-tests.sh`, a `case` keyed on the path the
runner prints. It carries one entry on this tree.

**Why the record rather than a rule.** A rule keyed on the transcript cannot
work: the two shapes are identical in the output, so any rule that picks the
right line for one picks the wrong line for the other. Keying it on the suite
makes the choice something a person states and a reader can see, and it is
what lets a suite that nests the other way round get a *different recorded
answer* rather than a wrong one.

**Why adding an ordinary suite changes nothing.** The record is a list of
decisions, not a list of suites: a suite with one summary line never reaches
it. Only a suite that starts running other suites has to add a row, which is
the property rather than the cost.

**Why the refusal has its own clause in the last line.** It rides a tally
separate from the `failed` one, and it is never reported as *"one or more
FAILED"*. That clause is a claim about the red set, and this is not a red
suite — the suite passed. A shape defect reported as a red suite puts a figure
nobody can trust into the sentence that is trusted, which is the overclaim one
layer down.

**Why the run still does not assert a count.** `set -uo pipefail` and no `-e`,
as before. The counts are printed and never asserted, and the refusal is a
*shape* rule rather than a count rule: it fires on a transcript's shape, not on
how many tests a suite has, so it does not turn every added test into a
failure. That trade is the reason the totals are read off a run in the first
place, and this change does not invert it.

## The alternative not taken

The issue offers two fixes: the count comes from a per-suite driver the runner
owns, or the choice is stated and the multi-line suites are **named in the
output** with a guard that they are detected. This takes the second.

The first is the stronger fix and it is the only one that closes the
transcript-order ambiguity outright, rather than making the ambiguity a
recorded decision. It is not this branch because it is a new tool plus a new
invocation path for every suite in the tree: a driver that loads through
`TestLoader().discover()` changes the `sys.argv` every suite sees, and
re-examines the per-file interpreter isolation that `run-tests.sh`'s comment
calls insurance rather than a preference. The issue's acceptance criterion is
met by the second *with* the detection, which is what the suite below holds.

Recorded here so the next person who wants the driver finds the argument
rather than re-deriving it, and so the choice is visible as a choice.

## What holds it

`tools/test_run_tests_ran_lines.py`, found by the runner's own `find` with no
wiring. It runs the committed script against scratch trees, so the cases
below are subprocesses of the real runner rather than of a restatement of it:

- a plain suite's total is its own count and its line is unannotated — the
  negative control, since a rule that fired on every suite would satisfy the
  refusal and break this;
- a recorded nesting suite is counted by its own run, **not** by the sum of its
  summary lines, and its line names it, the number of lines, and the choice;
- an unrecorded one is refused with a non-zero exit and a message naming the
  path and the step — in the **same run** as the plain suite, which is still
  counted, so the refusal cannot be passing by refusing everything;
- every path in the record is a suite `find` discovers, read out of the script's
  own text rather than kept in the test. A relation, not a census: adding a
  suite moves nothing, and a record naming a suite that has gone is caught;
- and the real `ec/tools/test_pd_image_census.py` on its own, so the record is
  checked against the suite it was written for and not only against a fixture
  shaped like it.

Each of those fails on the runner it is there to catch. Verified by breaking
the runner four ways and re-running: dropping the record entry reddens the
recorded cases; making it sum every summary line reddens the sum assertion,
on the fixture and on the real suite alike; replacing the refusal with a
`tail -1` reddens the refusal cases and the paired plain suite together; and
a record edited to answer with a word the loop does not recognise is refused
like a missing one rather than quietly counting nothing.

**No case asserts how many suites or tests the tree has.** Every figure is
read off the run under test, so a suite that gains a case moves none of them.

## The reconciliation the issue asks for

The issue's "done looks like" asks the runner's `tests` figure to reconcile
against `python3 -m unittest discover`, run rather than differenced. The run,
from the repository root:

```
$ bash tools/run-tests.sh | tail -1
```

RECONCILE_TOTAL_PLACEHOLDER

The reconciliation is per file, because per file is what the runner does: it
gives every suite its own interpreter, and the loop that produces its total is
the same loop that discovers the suites. What the two readings agree on is the
property, and where they differ is the nesting suite — summing that suite's
three summary lines reports its own count plus the two throwaway runs, and the
runner reports its own count alone. Both figures are off the runs quoted above;
neither is restated here, because a suite's case count moves when a case is
added.

**What was not measured, and why.** A single whole-directory
`unittest discover -s ec/tools` is not the same thing the runner does, and the
runner's comment records that `windows/tools` is order-dependent in one
interpreter — `test_windows_tools_shared_interpreter.py` exists to hold that
down. A directory-wide discovery is therefore not a like-for-like comparison
for the per-file loop, and no figure from one is quoted here as though it were.
What the run *does* establish for the whole tree is the property this branch is
about: every suite that carries more than one summary line is named in the
output, and a run with no refusal clause is a run in which every such suite is
recorded.

## Citations this file leaves where they are

This branch moves lines in `run-tests.sh`, and findings files that cite it by
line number are now pointing at the wrong lines. They are left alone
deliberately: renumbering a citation inside a dated record rewrites a claim
about what a reader saw at the time, and every one of them is a shared-file
edit that another branch adding a suite also wants. The claims themselves are
unaffected — each points at a block that still exists, at a different line.

What moved is the counting block. The citations into it and its neighbours,
and where each points now:

| was | now | what it says | cited by |
|---|---|---|---|
| `70-72` | `162-168` | the tally is *tests run*, so a failing suite is counted too | `tools-readme-totals.md` |
| `77-79`, `75-79` | `170-175` | the counts are printed, never asserted | `docs/findings.md`, `testdata-index-suite-count-floor.md`, `tools-readme-totals.md`, `runner-red-suite-set.md` |
| `68-71` | `170-175` | the exit code decides pass or fail | `0751-grader-self-test-gate.md` |
| `89-94`, `89` | `193-198` | the `find` that discovers suites, and its prunes | `0751-grader-self-test-gate.md`, `xdata-names-file-census-anchor.md` |
| `97-102` | `200-211` | a run that found nothing is not a pass | `checkout-claim-corpus.md`, `history-checkout-claims.md` |
| `99` | `212-221` | the runner prints what it does not run | `0751-grader-self-test-gate.md` |

`docs/findings.md` is frozen by `check_findings_frozen.py`, which fails a
change to it, so its citation is named here rather than edited. The rest are
in dated records, where the claim is about what a reader saw at the time and
the correction belongs in this file rather than in the record.

