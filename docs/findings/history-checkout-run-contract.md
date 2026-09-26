# The checkout-depth checker's exit code is its product, and the run crashed on the trees `--repo` exists for

**Issue #1037. Written 2026-09-26.** #1009 built
`ec/tools/check_history_checkouts.py` and gave it twenty-four cases; **#1034
added six more on `main` since, and a seventh arrived on `main` after this
page's branch was cut —
`test_the_table_turns_red_on_each_of_the_two_edits_it_exists_for`, measured by
diffing the two files' `def test_` lists rather than by counting — so it is
thirty-one today where this page's branch had thirty, and the gap this page
describes is unmoved** — every one of the thirty-one calls `report()` or one of
the functions under it, and **not one reaches `main()`**. So the exit code, the
`FAIL` lines, the `N problem(s)` summary and `--repo`'s default have no case
behind them, and deleting `if problems:` from `main()` leaves all thirty-one
green.
This page is what fixing that turned up: the run's own contract, and two defects
on its path that no existing case could see. The checker itself is unchanged in
what it measures and in what it reports; the tool's own write-up is
[`history-checkout-claims.md`](history-checkout-claims.md), and nothing on either
page is retracted.

## What was measured, before anything was decided

All of it offline, reproducible from the committed tree on this runner.

| command | result |
|---|---|
| `python3 -m unittest discover -s ec/tools -p test_check_history_checkouts.py` | `Ran 24 tests … OK` as #1009 left it; **31 on this tree**, the six #1034 added and the seventh above, still green and still reaching no `main()` |
| `python3 ec/tools/check_history_checkouts.py` (committed tree) | **exit 0**, empty stderr, the full report on stdout |
| the same with `--repo <pre-#1009-shaped scratch tree>` | **exit 1**, five `  FAIL ` lines on stderr, `check_history_checkouts.py: 5 problem(s).` — the same five records as `history-checkout-claims.md:208-216`, now reached through the run |
| `sed -i 's/    if problems:/    if False:/'` on a **copy** | the stale tree goes to **exit 0 with an empty stderr**, where the unmodified tool reads five problems. **The exit code is the whole of what the mutation removes, and nothing in the report-reading cases sees it** — 24 of them as #1009 left it, 30 on this page's branch, 31 on this tree |
| the same tool with no `--repo`, run from `cwd=/tmp` | prints the **committed** tree's nine checkouts and exits 0 — `REPO` is derived from `__file__` at `:110-111`, so the default is a fact about where the file lives rather than about the caller's directory |
| `--repo <tree whose `.github/workflows/` is empty>` | prints `no workflow was read … that is a broken census, not an empty one`, then **`AttributeError: 'list' object has no attribute 'values'`** in `report()`, exit 1 |
| `--repo <tree with no `.github/` at all>` | the same traceback, after `not listed (No such file or directory)` |

The last two rows are the same defect in the same block, and they are the
reason this page is not only about a missing test.

## The crash

**Every line number in this section is of the tool as #1009 left it** — that is
`d3304785`, the commit the crash was measured on, and the numbers are of that
file. **The two changes on top of it no longer move the rest by three.** The
edit below adds three lines inside `load_workflows()`, and #1034's landing on
`main` beside it adds forty-one above and sixty-odd below, so on this tree
`load_workflows()` is at `:264` rather than `:223`, the two failure paths are at
`:278`/`:280` rather than `:234`/`:236`, and the `AttributeError` site in
`report()` is at `:567` rather than `:470`. The section's own numbers stay as
measured, per [`../findings.md`](../findings.md) §4a-4d.

`load_workflows()` returns `(workflows, unreadable)` and documents it as such.
Every caller — `report():455`, `report():470`, `report():492`,
`depth_problems():255`, `workflow_names():353` — reads the first element as a
mapping. **Its two failure paths returned a list.** A tree whose
`.github/workflows/` cannot be listed, or holds no `*.yml`, therefore took the
run to an `AttributeError` — *after* the report had already printed its
`broken census, not an empty one` refusal, so the reader gets a refusal and a
traceback in that order.

**The committed tree cannot reach it**: **eleven** workflows are read, so
neither failure path runs. `--repo` exists for exactly the trees that can — a
scratch tree, a sparse checkout, a `git archive` extraction — and those are the
trees the crash was found on. `history-checkout-claims.md` records that
`report()`'s `:453-454` refusal was written for this case; it worked, and the
next block fell over.

Fixed by `return {}, [` on both paths, which is what the rest of the function
already returns on the path that works. The tool's *behaviour* on the committed
tree is unchanged, and so is the measured half, the reported half, and the rule
each asserts.

## A run that read nothing exited 0

With the crash gone, the same two trees printed the refusal and **exited 0**:
`main()` asks `report()` for two lists, and an empty census produces two empty
lists, and two empty lists is the passing shape. That is the §14b defect
(`docs/findings.md` §14b, the Windows parser whose regex matched zero of 502,652
lines and reported a pass over it) at the level of the process status: **"found
nothing" and "found nothing wrong" are the same exit code.**

`main()` now re-reads the census and refuses when it read no workflows at all:

```python
workflows, _unreadable = load_workflows(args.repo)
if not workflows:
    print("check_history_checkouts.py: no workflow was read, so the report "
          "above is not a measurement of this tree -- that is a broken "
          "census, not an empty one, and a run that read nothing does not "
          "pass.", file=sys.stderr)
    return 1
```

Three things about that, each of them a decision rather than a preference:

- **Keyed on zero workflows read, not on `unreadable` being non-empty.** A
  `broken.yml` that will not parse beside a conforming `ci.yml` is a tree one
  bad file short of complete, and it still gets a real measurement. That is
  what the report suite's *a workflow that will not parse is named and the rest
  still runs* case already holds; the run has to agree with it or the exit code
  is stricter than the thing it exits. **The case is named rather than cited as
  a `file:line`**, because a pin into a test file is a registered one
  (`docs/findings/test-line-pin-census.md`'s per-pin table) and one citation
  here would ripple its reconciled counts through four other suites for no
  reader who could not find the case by its name.
- **The re-read rather than a wider `report()`.** `report()`'s two-tuple is
  unpacked by two cases in the suite the issue says to leave alone, so handing
  the census back is a larger edit to a file this change has no reason to
  change. Eleven small YAML files parsed twice is nothing.
- **Why a 0 here would be worse than a crash.** #1033 wants a gate to key on
  this tool's return value, and a gate whose checker answers 0 for *I read no
  workflows* is a gate that passes a `git archive` extraction of the repository
  — because a checkout without `.github/` is exactly what a gate sees when the
  actions are not checked out. The house standing is the same one
  `check_pin_table_by_cited_file.py`'s `RunTests`, `check_capture_names.py`'s
  `--check` tier and `census_test_line_pins.py` all take.

**The alternative, recorded because the plan took this branch over it:** leave
the exit code alone and pin `0` for the empty census in a case whose comment
calls it a hole. That was declined because a later reader takes 0 as the
contract — which is the defect, in the one suite whose job is to hold the
contract. **Nothing here is a claim that such a gate exists.** No workflow and
no gate calls this tool today; #1033 is the consumer this shape is written for,
and it has not landed.

## The suite

`ec/tools/test_check_history_checkouts_run.py` — a new file rather than a fourth
class appended to the report-reading one, per `CLAUDE.md`'s new-file rule and
because several agent PRs are open against this tree: **this landing does not
edit that file at all**, which is what the issue asks for, and it is left free
for whichever sweep lands next. `tools/run-tests.sh` picks the new one up by
`find` with no edit to it, the same arrangement `test_disasm8051.py` /
`test_disasm8051_oracle.py` already use for one tool.

**"Byte-identical" was true of this page's branch and is not true of the merged
tree, and the reason is `main` rather than this change.** #1009's twenty-four
were byte-identical across this landing, and #1034 then added six cases to that
same file on `main` and a seventh followed, so the thirty-one on this tree are
not what this page's branch saw — its thirty. What the claim is for still
holds: no case in it reaches `main()`, so `if problems:` can be mutated with all
thirty-one staying green — re-measured on this tree, not carried, and the run is
the acceptance test below.

**Why subprocess and not the in-process `run_tool` harness the two sibling
checkers use** (#948's shape, in `test_check_pin_table_by_cited_file.py` and
`test_check_capture_names.py`). The product here is the *process* status and the
`sys.exit(main())` at the foot of the file, and an in-process case observes a
return value that nothing then turns into an exit code. `--repo`'s default is
worse: it is a fact about `__file__`, and the only in-process way to see it is to
patch the constant under test, which makes the case a statement about the
patched value. So one case runs the tool with **no `--repo` from inside the
stale tree** and asserts the *committed* tree's `ci.yml / gates / Checkout:
fetch-depth: 0` line — two facts in one case, `--repo`'s `default=REPO` and the
provenance of `REPO`, held against a cwd that would otherwise read 1 and exit 1.

**One copy of the four stale sentences, not two.** `STALE_DOCSTRING`,
`STALE_COMMENT`, `STALE_REQUIREMENT`, `STALE_SIBLING` and `CORRECTED_DOCSTRING`
are imported from the report suite, along with the `workflow()` builder and
`ScratchTree`. The import is the point rather than a saving: that suite's
docstring is explicit that a paraphrase which happens to name a job is a control
passing for the wrong reason, and a second copy is a second thing to drift from
the sources the first was pasted from.

Seven cases, one fact each:

| case | holds |
|---|---|
| `test_a_stale_tree_exits_one_with_the_failures_and_the_summary` | returncode 1, five `  FAIL ` lines on stderr, `ci.yml/gates` among them, `5 problem(s).` on stderr, `4 of the claims name no job, in 4 sentence(s)` and `ci.yml / gates / Checkout: depth 1` on stdout — **the stream split is the case** |
| `test_a_conforming_tree_exits_zero_with_an_empty_stderr` | returncode 0, **stderr empty**, both verdict lines on stdout. Exit 0 has to be a measurement, not a census that found nothing |
| `test_the_default_repo_is_this_repository_and_not_the_working_directory` | no `--repo`, `cwd` set to the stale tree, the committed tree's own line on stdout |
| `test_a_tree_whose_workflow_directory_is_empty_is_refused_and_does_not_crash` | returncode 1, `broken census, not an empty one` on **both** streams, **no `Traceback`** in stderr |
| `test_a_missing_workflow_directory_is_refused_the_same_way` | the second shape of the same clause: `not listed (No such file or directory)` on stdout, non-zero, no traceback |
| `test_one_workflow_that_will_not_parse_is_not_a_broken_census` | a conforming `ci.yml` beside a `broken.yml`: returncode 0, `broken.yml: not read` on stdout |
| `test_the_usage_block_is_this_tools_own_docstring` | `--help` exits 0, carries the docstring's own usage line with its columns (which only survives `RawDescriptionHelpFormatter`) and `--repo REPO  repository root to read (default: this one)` |

**Two of the seven cases pin a verdict line, and both are worded as #1034 left
them on `main`.** This page first wrote `4 of them name no job` and `every one
of them names the job it is about`; #1034 changed the rule to be judged per
*workflow* rather than per sentence and with it both summary lines —
`N of the claims name no job, in M sentence(s)` and `every one of them names
the job of every workflow it names`. The stale tree's numbers are unmoved (4
and 4, and the five problems), so the correction is the wording only; the
cases assert what the tool prints on this tree, and both spellings are one
`#1034` rename away from red.

**Two of the seven are red on the tool as #1009 left it** — the two
`BrokenCensusTests` cases above, on the `AttributeError` — and that is why they
are here rather than as a follow-up. Verified by running this suite against the
pre-fix tool in a copy of the tree: **5 passed, 2 failed**, the empty-directory
case first on `broken census, not an empty one` missing from a stderr carrying
the traceback instead, and the missing-directory case on `Traceback` unexpectedly
found in stderr. The other five pass either way, which is the honest shape of the
result: this suite did not go from all-green to all-green, it went from one
crash-uncovered to covered. **Re-measured on the merged tree**, where the
pre-fix tool is `origin/main`'s copy rather than `HEAD`'s — `HEAD` is this
branch, so `git show HEAD:` would name the fixed file and the check would pass
vacuously — and the result is the same 5 and 2.

## The acceptance test, and what it caught

The issue's own `Done` line, run:

```
$ sed -i 's/    if problems:/    if False:/' ec/tools/check_history_checkouts.py
$ python3 -m unittest discover -s ec/tools -p test_check_history_checkouts_run.py
...
FAIL: test_a_stale_tree_exits_one_with_the_failures_and_the_summary
AssertionError: 0 != 1
Ran 7 tests … FAILED (failures=1)
$ python3 -m unittest discover -s ec/tools -p test_check_history_checkouts.py
Ran 31 tests … OK
$ git checkout ec/tools/check_history_checkouts.py
```

**Re-run on this tree rather than carried**, and the `24` is the one figure the
branch's transcript had that `main` moved twice — the transcript's second half is
the report suite, which grew by six cases in #1034 and by one more since, and
both halves come out as written above (`31` where the branch recorded `24`, and
`30` on this page's branch). The first half is unmoved, which is the point of
the test: the mutation catches the run suite and nothing else.

Both halves, on a copy rather than the working tree. The mutation takes the
stale tree from **exit 1 with five `FAIL` lines to exit 0 with an empty
stderr**, and it is the stale-tree case that catches it — a conforming tree
exits 0 with and without the mutation, so only a tree the tool rejects
distinguishes the two. The report suite stays green — thirty-one on this tree,
thirty on this page's branch and twenty-four as #1009 left it — which is the
point: they read the report, and the report is unchanged.

## What is not claimed

- **That any gate or workflow runs this tool.** None does, before or after.
  `docs/ci/` holds **six** `agent-gates-*.patch` files and none for this
  checker. Six is a count taken rather than one carried: `ls docs/ci/*.patch`
  reads six here, and on `d3304785`, and on `origin/main`'s `5244f119` — and
  [`../findings.md`](../findings.md) already reasons about "a seventh", so
  this page's **five** was the outlier and it matched no tree this branch
  could have measured. It is the issue's plan's figure, brought here into a
  page whose stated value is that its figures were run, and it is left written
  with this correction beside it per §4a-4d rather than quietly overwritten.
  The half of the claim that carries the argument needs no number at all:
  **no patch under `docs/ci/` names `check_history_checkouts.py`.**
  `.github/scripts/agent-gates.sh` is copied from `ElDavoo/agent-pipeline`, so
  a gate call is an upstream change and a re-copy, not a line here. #1033 is
  the issue that wants one, and this page is written so it starts from a
  measured contract rather than an assumed one.
- **That the refusal makes a future gate safe.** It removes one vacuous 0. What
  a gate keyed on this exit code would still miss — a workflow that is read and
  is wrong in a way this tool's two rules do not name — is unchanged.
- **That `--verify-provenance` needs, or has, a full clone.** The tool derives
  depths from committed YAML and committed prose. A workflow saying a job runs
  a gate is not an observation of that gate having run, and the measurement
  table on the other page is a transcription of a tool's output rather than of a
  CI run.
- **Any claim about a job's real checkout depth beyond the tool's own
  derivation.** A checkout behind a composite action, one expressed through a
  `${{ }}`, and `agent-conflicts.yml`'s `resolve` job reaching the gate from its
  prompt rather than a `run:` step are all outside it — "not found by this
  method", per the caveat the other page spells out.
- **Any hardware, Windows, EC or BIOS evidence.** Nothing here needs a laptop.
  The scratch trees are hand-built, the YAML is committed, and no live test ran
  at any point in this change.
