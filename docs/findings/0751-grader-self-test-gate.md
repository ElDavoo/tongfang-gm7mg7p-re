# The 0x0751 grader had 74 tests on main, no entry point, and no gate (issue #532)

The write-up for [issue
#532](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/532), which is
about `ec/tools/grade_0751_isolation.py` having a suite that nothing runs. What
this branch changes is a **mode** and a **prepared patch**: `grade_0751_isolation.py`
grows the `--self-test` entry point every other gated tool has, and the two lines
that would put it in `check_ghidra_tooling()` are prepared at
`docs/ci/agent-gates-0751-self-test.patch` rather than landed, for the reason
`docs/ci/agent-gates-capture-claims.patch` gives.

**Until a human lands that patch, the suite still does not run per commit, and
`grep -rn 'grade_0751\|test_grade' .github/` still returns nothing.** No
coverage is claimed here beyond what is already in the tree. Nothing below is a
register behaviour, a live test, or evidence about the machine: the suite reads
hand-built CSVs committed under `ec/tools/testdata/`, and no EC is opened, no
register read back, and no capture taken on a laptop.

## Which of the issue's two options, and why

**Option A, a `--self-test` mode on the grader.** Three reasons, the second and
third measured on this tree on 2026-09-25.

1. **It is the shape the gate already expects.**
   `check_ghidra_tooling` (`.github/scripts/agent-gates.sh:101`) is a
   per-tool loop over a named list, and every tool in it is called with its own
   modes. `grade_0751_isolation.py` is absent from that list *and* has neither
   `--check` nor `--self-test`, so the loop's `*)` default (`:190`) would hand
   it `--work "$scratch" --check` — flags it does not have. That is the root
   cause the issue names, and a `--self-test` is what removes it. The wiring is
   one list entry plus a `case` arm shaped like the existing
   `*merge_annotation_shards.py)` one: `--self-test` alone, no `--work`,
   because the grader has neither.

2. **Option B is red on this tree today.** Option B is "a gate case invoking
   `unittest discover` for the named suites", and `tools/run-tests.sh` already
   is that runner (issue #162). Run from the repo root it ends
   `one or more FAILED`, and **two** of the suites it runs fail here, neither
   of them this grader's. This write-up names those two by name rather than
   quoting a suite or test total, because the runner's own totals are a
   property of the merge and re-stale with the next suite to land.

   The first is `ec/tools/test_check_site_census.py::test_the_committed_join_holds`
   — 14 disagreements between `ec/annotations/xdata-086x-dispatch-sites.csv`,
   `ec/annotations/xdata-0860-census-sites.csv` and the committed decompile:

   ```
   check_site_census.py: 0x0D091 (mapped): census_refs cites bank0/D091.c:44, where the census has no 0x0860 occurrence -- the line moved, or the reference was dropped
   ...
   14 disagreement(s) between ec/annotations/xdata-086x-dispatch-sites.csv, ec/annotations/xdata-0860-census-sites.csv and the census
   ```

   The second is `ec/tools/test_xdata_cluster_names.py`, erroring in
   `setUpClass` — ``the `==` guard is not where §6a's recipe deletes it; the
   guard-off census this suite builds is not the one §6a measured``. That is
   #528's own finding, and `db6d7d2d` is this branch's point of departure, so
   the suite was already red this way when the branch was cut.

   The cause is visible in the file. `ec/decompiled/bank0/D091.c`'s header
   carries a `CORRECTION 2026-09-24, issue #180` note — the 40 bytes at
   `0xD14B` are a CODE table, not code — and rewriting that comment moved the
   body, so the lines `xdata-0860-census-sites.csv`'s `census_refs` cite
   (`D091.c:44`, `:48`, `:70`, `:74`, `:82`, and the partners in each range) no
   longer hold the occurrences, which now sit at 45, 49, 72, 77 and 84. The
   tool reports it in both directions — a cited line with no occurrence, and an
   occurrence no mapped site accounts for. Wiring the whole runner into a
   per-commit gate today would turn CI red for a drift unrelated to any PR
   under test, and it would buy that red with the runner's whole wall clock —
   12 s on 2026-09-25, against the 0.32 s item 3 measures for the grader
   alone. The runner prints no elapsed line of its own, so that is a
   wall-clock measurement rather than something it reports.

   The census one is a real finding and it becomes a **follow-up issue**; this
   branch does not fix it. Whether the refs move or the counts change is a
   judgement about the decompile, not a mechanical edit, and it belongs to
   whoever owns #180's correction. #528's `==`-guard failure already has its
   own issue on `main` and needs nothing from here. Either is also what makes
   #162's already-written four-line wiring the right next step rather than a
   near-term one.

3. **The cost is the cheapest in the repository.** Measured on this tree,
   2026-09-25, over three runs each:

   | | |
   |---|---|
   | `python3 -m unittest discover -s ec/tools -p 'test_grade_0751_isolation.py'` | `Ran 76 tests in 0.192-0.193s` |
   | `python3 ec/tools/grade_0751_isolation.py --self-test` end to end | **0.32 s** (0.32/0.32/0.33) |
   | the cheap tier, before and after the prepared patch is applied | `All gates passed` both times, at 11-12 s unpatched and 11 s patched |

   The issue quotes 0.100 s for the suite and that is a different machine.
   These are one runner's figures, recorded with the date for the reason
   `docs/agent-pipeline.md` item 6 records `call_graph.py`'s: the ratio, not
   either absolute number, is what a later agent raising the gate's runtime
   budget needs. 0.32 s against a cheap tier that reads 11-12 s here and is
   recorded at 5.9 s in `docs/agent-pipeline.md` is more than thirty times.
   That is also why the last row quotes an elapsed spread rather than a
   before-and-after: the mode's 0.32 s is below the one-second resolution the
   gate's own line prints, so those figures are one number seen more than
   once, not a measurement of what the mode adds.

   The 76 is this merged tree's count, and 74 of them predate the branch. The
   branch point is `db6d7d2d` (#528), and #530's unplaced-window-scope cases
   are already its ancestor — `git merge-base --is-ancestor b3f30987 db6d7d2d`
   is true, and `grep -c 'def test_'` against that commit's copy of
   `ec/tools/test_grade_0751_isolation.py` is 74, as it is at `origin/main`.
   The 2 above are this branch's, so 76 is 74 + 2 and no case arrived on
   `main` while the branch was open. Nothing in the suite asserts a count —
   see `tools/run-tests.sh:68-71` below — so each of the two landed without a
   test failing.

## What the suite pins, and why that is the reason to run it

The 74 tests this branch did not touch are the pinned record of the grader's
refusal policies, and each one is a gate between a human's hardware day and a
wrong §7 call — which is why they are worth a gate call rather than a note:

| refusal | what it stops |
|---|---|
| a capture given twice | one console counted as two, so a mark it never recorded reads as recorded |
| a mark set that does not hold (one capture short a mark, or two spellings of an action) | a no-op arm reading as thermally quiet for want of a mark |
| a block whose last mark is not the restore | a report that cannot show the byte being put back, graded whole anyway |
| a window in a block that failed its check | correct-as-arithmetic rows printed as if they were evidence |
| a mark whose label is not one of §6's three forms | a capture whose block structure cannot be attributed at all |
| a `--block` that named no block | a clean report printed over the wrong block's marks |
| a `--wrote`/`--block` pair naming different values | a run about a value the operator did not mean |
| `--wrote`/`--block` that is not a value | the same, one step earlier |
| a capture with no MARK rows | §4 applied to change rows that cannot be assigned to an arm |
| a `--dump-pair` naming one file twice | a read diffed against itself, holding every byte equal by construction |
| a §4.6 readback with no coverage of `0x0751` | a readback reported where none was taken |

A PR that breaks one of these merges green today. `grade_0751_isolation.py`'s
own docstring says the tool exists so a report never "says more than it read",
and the refusals are the product; the suite is the only thing that holds them.

## The change

### `ec/tools/grade_0751_isolation.py` — the mode

- **`self_test()`** runs `test_grade_0751_isolation.py` by
  `unittest discover`, in a subprocess, with `sys.executable` and `-s` set to
  the tool's own absolute directory (so it works from any cwd) and `-p` set to
  the suite's file name rather than `test_*.py` — `ec/tools/` holds other
  suites, and naming the file is what keeps the gate's cost this suite's.

  The subprocess is not incidental. `test_grade_0751_isolation.py:16-20` loads
  the grader a second time under the module name `grade` via
  `importlib.util.spec_from_file_location`; importing it in-process would leave
  `__main__` and the module under test as two copies of one file in one
  interpreter, which is the ordering-accident shape `docs/findings.md` §16 is
  written about.

- **Dispatch before `parse_args`, not after.** `main()` takes `csv` as
  `nargs="+"`, so `--self-test` with no capture is argparse's exit 2 today.
  Adding the flag to the parser and branching afterwards would mean relaxing the
  positional to `nargs="*"`, which changes the bare run's refusal — and the
  refusals are the thing the tool exists for. The parser and every existing exit
  code are byte-identical; `--self-test` is not an argparse option, it is read
  out of `argv` first. It stays discoverable through the module docstring,
  which *is* the argparse `description`, and through the `Usage:` block.
  `call_graph.py` and `grade_name_basis.py` dispatch after parsing only
  because neither has a required positional.

- **No test count is asserted.** The count unittest reports is printed and the
  exit code decides, for the reason `tools/run-tests.sh:68-71` gives: an
  expected count in a runner turns every added test into a failure. A
  discovery that matched **nothing** is the one exception, and it returns 1 —
  `Ran 0 tests` exits 0 and prints `OK`, which from outside a gate is
  indistinguishable from a suite that passed, and `tools/run-tests.sh:89-94`
  refuses the same empty glob one level up.

- **The mode prints its own deferral**, in the place and for the reason
  `agent-gates.sh:236` and `tools/run-tests.sh:99` each do: the suite is
  refusals over committed fixtures in `ec/tools/testdata/`, not §4 re-applied to
  a capture a human took.

### `ec/tools/test_grade_0751_isolation.py` — two cases, 74 to 76

Both guard what the mode could break, and both are in the suite the mode runs:

| test | what it holds |
|---|---|
| `test_the_self_test_mode_runs_the_committed_suite_and_exits_zero` | `--self-test` with no capture behind it reaches `self_test()` and never the parser; the discovery is `sys.executable -m unittest discover -s <this tool's directory> -p test_grade_0751_isolation.py`; the count is printed; the deferral is printed; a discovery that found nothing and one that failed both return 1, and what the discovery said is passed on rather than swallowed |
| `test_a_run_with_no_capture_is_still_argparse_s_usage_error` | `main([])` still raises `SystemExit(2)` with `the following arguments are required: csv` — the regression guard on the parser decision above |

The first drives the mode through its `run` seam rather than launching it,
because a case that ran the mode would have the mode run this suite, which
contains the case, which runs the mode. The real discovery is what
`python3 ec/tools/grade_0751_isolation.py --self-test` and the gate's `case` arm
do, and neither is this file.

**Those 74 are unchanged** — no assertion, message, or exit code of theirs was
edited, and they are the evidence that nothing else moved. They already
include #530's two unplaced-window-scope cases, which predate this branch, so
76 is 74 + 2 and not a count either side overwrote.

## The prepared patch

`docs/ci/agent-gates-0751-self-test.patch`, in the header-and-`git apply`
shape `docs/ci/agent-gates-capture-claims.patch` established. It adds
`ec/tools/grade_0751_isolation.py \` to the `for tool in` list and this arm:

```sh
      *grade_0751_isolation.py)
        python3 "$tool" --self-test || rc=1
        ;;
```

with a comment at the call site saying why it is cheap-tier (python3, the
standard library's `unittest`, and committed CSV fixtures — no firmware image,
no Ghidra, no network, no assembler) and what it holds. No `--check` and no
`--work` arm is invented for it: the grader has neither, and a mode it does not
have is not a thing the gate should call.

Verified on this tree: `git apply --check` is clean, `shellcheck` is clean on
the patched script, and a full patched gate run prints
`test_grade_0751_isolation.py: 76 tests, passed` inside the `ghidra tooling`
gate and ends `All gates passed` (11 s elapsed here, against 11-12 s
unpatched — the same one-second-resolution wall clock as the cost table above).
`.github/scripts/agent-gates.sh` itself is not edited by this branch — it is
template-copied, and the prepared
patch is the deliverable, so a reviewer can read the whole of what would land
without it landing.

## Left out on purpose

- **Landing the gate wiring.** `.github/scripts/agent-gates.sh` is copied from
  `ElDavoo/agent-pipeline` and this pipeline's push token has no `workflow`
  scope, so a branch editing it fails at the very end rather than at the start.
  The patch route is the established answer. If `.github/scripts/` turns out to
  be pushable, the patch applies unchanged and nothing is lost.
- **`tools/run-tests.sh` in the gate** (#162's step, the 4-line wiring already
  written down in `docs/agent-pipeline.md:257-263`). Left for the reason in
  finding (2): the runner is red today.
- **The `test_check_site_census.py` failure.** Pre-existing, unrelated to this
  grader, and a judgement about the decompile rather than a mechanical edit.
  Follow-up issue: the stale `census_refs` line numbers in
  `ec/annotations/xdata-0860-census-sites.csv` against a `bank0/D091.c` that
  was hand-corrected on 2026-09-24 for #180.
- **`tools/README.md`'s stale counts** ("seventeen today, 432 tests in all" —
  both are past, and the runner is red today on the two suites finding (2)
  names). Left to the same follow-up: it is a shared file, the number
  re-stales with the next suite, and the runner deliberately asserts no count.
  This file names the two failing suites instead of carrying a total that is
  already wrong. `docs/agent-pipeline.md:266`'s 0.77 s figure is #162's
  four-suite measurement; item 7 says so rather than contradicting it, and no
  existing line is edited.
- **Running the 0x0751 procedure on hardware.** No laptop is reachable from a
  runner. The suite is offline by construction over committed fixtures.
- **#512 and #416** — the same shape for a different tool and a different
  nightly; neither is this grader and neither is fixed by either option.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-built CSVs in `ec/tools/testdata/` or a
wall-clock measurement of this repository's own offline suites, reproducible
from the repo root with the commands shown, on 2026-09-25. No live run, no
register readback, no hardware observation; no line of this change may be read
as a report of a capture, and none is one. `MANUAL_FAN_CTRL` stays
`present-untested` with its `static_refs*` counts at 29/29/0, unchanged by
anything here.
