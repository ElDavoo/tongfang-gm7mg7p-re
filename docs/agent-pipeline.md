# The automation pipeline

`.github/workflows/agent-*.yml`, `.github/actions/agent-stall/`,
`.github/actions/project-setup/`, `.github/scripts/agent-gates.sh`, and
`.github/ISSUE_TEMPLATE/` are copied from
[`ElDavoo/agent-pipeline`](https://github.com/ElDavoo/agent-pipeline)
(MIT licence — see that repository for the full text; not duplicated here
because a repo-root `LICENSE` file would read as covering everything in
this repo, including the `vendor/` binaries, which this project has no
right to license).

`.github/scripts/agent-gates-deep.sh` is **not** from the template — it is
this repository's own, added when the gate was split into two tiers (see
"What was customised for this repo" below). It is the one file under
`.github/scripts/` that a re-copy of the template would not bring back, so it
is the one to look for first when the upstream half of that change is done.

Read that repository's own `README.md` for how the pipeline works — issue
in, plan, implement, review, fix-loop against CI, squash-merge — and its
`CLAUDE.md` for what must not drift if it's ever re-copied. This document
only covers what's specific to *this* copy.

## What was customised for this repo

- **`.github/actions/project-setup/action.yml`** — installs the tools
  `ec/tools/` and the gates need: Python 3 + PyYAML, `radare2` (EC firmware
  disassembly), `sdcc`/`sdas8051` (round-trip-tested against the EC's 8051
  opcodes, see `ec/README.md`), `innoextract` (Windows installer
  extraction), and Ubuntu's preinstalled `shellcheck`.
- **`.github/scripts/agent-gates.sh`** — the cheap, mechanical checks:
  `ec/annotations/registers.yaml` parses and every entry has the required
  keys; every `ec/tools/*.py` at least imports cleanly and
  `scan_refs.py` reproduces one known reference count against the real
  firmware image (a smoke test, not just a syntax check); every decompiler
  tool's `--check` and `--self-test` pass, which is what stops the committed
  Ghidra exports going stale without a Ghidra run in the gate; every `*.sh`
  passes `shellcheck`; every relative link between this repo's `.md` files
  resolves. It also prints, on every run, the two checks it does **not** run
  and the one command that does — see the tier split below.
- **`.github/scripts/agent-gates.sh` + `agent-gates-deep.sh`, the two tiers**
  (2026-09-23, issue #137) — the gate is split by cost, and the split is
  `AGENT_GATES_DEEP=1` plus one extra script. The cheap tier
  (`agent-gates.sh`, what CI runs) is everything that is sub-second per step
  and every check that opens a `.c` or an `.asm`: measured at **5.9 s** for the
  whole script on a GitHub-hosted runner. The deep tier
  (`.github/scripts/agent-gates-deep.sh`) is a **superset** — it runs the cheap
  tier first, then the `sdas8051` re-encode and the advisory cross-decoder
  comparison — so `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh` is the
  single command that checks everything, and the cheap tier's closing note
  names that command on every run.
  Seven things to carry across if this file is ever re-copied from the template:
  1. **The deep tier needs a schedule, and it does not have one.** What runs
     where, as of 2026-09-23 (issue #139): per commit, on `push` to `main` and
     on every pull request, `ci.yml` runs the cheap tier bare, and the deep
     tier runs on **nothing** — no workflow in `.github/workflows/` calls it,
     because the pipeline token has no `workflow` scope. The workflow is
     prepared instead, at `docs/ci/agent-gates-deep-schedule.yml`: a nightly
     `schedule:` plus `workflow_dispatch`, and a human lands it with
     `cp docs/ci/agent-gates-deep-schedule.yml .github/workflows/agent-gates-deep.yml`.
     It runs the deep tier through its documented entry point and nothing
     else:
     `AGENT_GATES_DEEP=1 .github/scripts/agent-gates.sh`.
     It tees that run to a log and uploads it as an artifact with
     `if: always()` (issue #158), because the same file's own comment says
     GitHub delays and sometimes drops scheduled runs without telling anyone: a
     run that happened leaves an artifact behind and a run that did not leaves
     none, so "the nightly did not run" stays distinguishable from "the nightly
     found nothing". Absence is observable, not failing — making a vanished run
     fail something needs a checker that runs when the scheduled one did not.
     Until it is landed, the re-encode is opt-in, and the reason it is opt-in
     rather than dropped is in `docs/findings.md` §14e — which also records
     what per-commit coverage is still missing, and it is not nothing: since
     #139 the cheap tier carries a `listing_digest` per row of
     `ec/ghidra/reassembly.csv`, so a mnemonic or operand edited in a
     committed `.asm` fails per commit with no assembler. That *detects* the
     edit; verifying it is still the re-encode's job, and the re-encode is
     still unscheduled. Per-commit coverage is therefore less than before the
     split, and more than the split left it.
  2. **The cheap tier's checks were strengthened, not moved.** The Windows
     tool gained duplicate-key, strict-CSV, coverage and controlled-vocabulary
     checks; nothing that catches a stale or silently-failed export was
     deferred. The deep tier adds an independent re-derivation, it does not
     substitute for anything. `verify_reassembly.py --check` gained a third
     assertion for the same reason: it was added to the cheap tier, not
     promoted out of it, and its `--self-test` joined it there
     (2026-09-23, issue #149): the `*verify_reassembly.py)` case now runs
     `--check && --self-test`, the same shape as the `*decompile_native.py)`
     case, so the digest's known-answer assertions — the canonical form, the
     `compare_digests()` failure paths, `GAP_FORMS`, `BIT_UNSUPPORTED` — run
     per commit rather than only where a human asks for them. They sit
     before the self-test's no-assembler early exit, so that is true on a
     runner without `sdas8051` as well. The `--check` comparison still covers
     all 2,705 rows and the assertions still guard the tool rather than the
     tree. **A re-copy of `agent-gates.sh` from the template restores the
     `--check`-only case, so this has to be re-applied with it.** The
     re-encode of the committed listing is still the deep tier's, and is
     still unscheduled.
  3. **`--verify-provenance` needs a full git history, and `ci.yml` does not
     have one** (2026-09-23, issue #159). The mode audits a `listing_digest`
     migration against two committed revisions (`docs/findings.md` §14f), so
     how deep the clone is is part of its contract the way the assembler is part
     of `--report`'s: the agent stages check out with `fetch-depth: 0`
     (`agent-implement.yml:118`, `agent-fix.yml:116`, `agent-review.yml:64`)
     and can run it, while both of `ci.yml`'s checkouts (`:34`, `:64`) are
     default-depth, and `08b72e2` and `a56b3bb` do not resolve from one. It
     therefore fails there with its history requirement rather than auditing
     whatever happened to be checked out, and it is not in the gate for that
     reason. Putting it in the per-commit gate is a one-line
     `fetch-depth: 0` on those two checkouts that a human lands, and whether
     that is worth growing every checkout for — or whether the mode stays a
     full-clone command like `--add-digest-column` and `--report` — is the open
     question. It is not made here: `.github/` is template-copied and the
     pipeline token has no `workflow` scope, the same reason item 1's schedule
     is prepared rather than landed.
     **Decided 2026-09-24 (issue #407): it is in the per-commit gate.** A
     maintainer landed `fetch-depth: 0` on `ci.yml`'s `gates` checkout; the
     `workflows` job only lints YAML and stays shallow. `agent-gates.sh` runs
     `--verify-provenance --base 08b72e2 --migration a56b3bb --listings-from
     8c7985e` after `verify_reassembly.py`'s `--check` and `--self-test`, and
     `docs/ci/agent-gates-deep-schedule.yml`'s checkout is full-depth too, since
     the deep tier runs the cheap one first. The cost is a full clone per CI
     run (a 224 MiB pack over 202 commits at the time); the mode itself took
     1.7 s locally. The revision pair is fixed, so this re-audits the one
     committed migration on every run; it does not audit the next one. A
     future migration needs its own `--base`/`--migration` pair added here.
     A shallow local clone now fails this gate, as the mode intends.
  4. **`verify_gap_text.py --check` is not in the cheap tier yet, and should
     be.** Issue #151 (2026-09-23) added
     `ec/tools/verify_gap_text.py`, which cross-decodes the 143 instructions
     `sdas8051` cannot re-encode — the ones no assembler reaches, which were
     read by no check at all before it. By cost and by kind it belongs in the
     cheap tier: it needs only `python3` and the committed firmware, no
     assembler and no Ghidra, and takes well under a second. Adding it is a
     `case` arm in `check_ghidra_tooling()` mirroring the
     `*verify_reassembly.py` one, plus the path in the tool list above it:

     ```sh
           *verify_gap_text.py)
             python3 "$tool" --check || rc=1
             ;;
     ```

     It is not here because this is a template-copied file and the plan
     stage's push token has no `workflow` scope, so a branch editing it fails
     at the end of the PR rather than the start. **Until a human lands it,
     nothing runs `--check` per commit** and the committed verdicts in
     `ec/ghidra/gap-text-check.csv` can go stale in an otherwise-green commit
     — the same shape as item 1, and for the same reason. The command is named
     here so a template re-copy carries it.
  5. **`check_capture_claims.py --check` is not in the cheap tier yet, and
     should be** (2026-09-24, issue #277). It holds the prose's capture
     claims to the committed CSVs they name: an address a sentence attributes
     to `evidence/ec-watch/<file>.csv` has to have a row in that file, and a
     stated row count has to equal the real one. That class of claim has been
     wrong twice in `registers.yaml`'s history — issue #265, and the `0x07D4`
     clause issue #270 had to retract in place — and both were caught by a
     re-reading, because `check_register_counts.py` verifies the file's
     numeric keys from the image and never opens a `note:`. Adding it is a
     `check_capture_claims()` function and a `gate` line beside
     `check_register_counts`, and the whole of it is prepared at
     `docs/ci/agent-gates-capture-claims.patch`; a human lands it with
     `git apply docs/ci/agent-gates-capture-claims.patch`. Cheap tier for the
     same reason item 4 gives: it needs the committed CSVs and the standard
     library's `csv` module — no firmware image, no Ghidra, no assembler. It
     is not here for item 4's reason, template-copied file and no `workflow`
     scope on the token, and **until a human lands it, no commit runs it** and
     the next false capture claim merges the way the last two did. Its own
     suite (`ec/tools/test_check_capture_claims.py`) needs no wiring to be
     run at all: `tools/run-tests.sh` discovers every `test_*.py` in the
     repository, so it is already collected by the runner above.
  6. **`call_graph.py --check` and `--self-test` are added to the tool list
     in `check_ghidra_tooling`, and a re-copy drops both** (2026-09-24, issue
     #454). They hold the 1,841-row `ec/annotations/call-graph-callees.csv`
     against the committed `.asm` listings it is derived from: nothing
     re-derived that table before, so a hand-edited cell or a re-exported
     listing left 1,841 rows wrong with the gate green — the same quiet-drift
     shape the table is committed to prevent. The tool takes no `--work` and
     has no scratch dir, so it needs its own `case` arm, like
     `gen_xdata_symbols.py`'s, plus the path in the tool list above the loop:

     ```sh
           *call_graph.py)
             python3 "$tool" --check && python3 "$tool" --self-test || rc=1
             ;;
     ```

     Cheap tier for item 4's reason: both modes need only `python3` and the
     committed listings — no Ghidra, no network, no assembler — and together
     they measure **0.17 s** (0.16–0.17 s over three runs) here, against a
     cheap tier the paragraph above records at 5.9 s. It is in the cheap tier
     rather than the deep one for item 1's reason: the deep tier runs on
     nothing, so a check that must run per commit has to live where `ci.yml`
     already runs. The self-test's fixture assertions are the half that
     matters — a table with one cell altered and a table with its last row
     dropped both have to come back rejected, over the same `diff_table()`
     `--check` uses — because a check that has quietly started accepting
     everything looks exactly like a check that is working. That is why this
     one is `--self-test` in the arm rather than `--check` alone, unlike
     item 4's. **A re-copy of `agent-gates.sh` from the template restores the
     eight-tool list, so the path and the arm have to be re-applied with
     it.**
  7. **`grade_0751_isolation.py --self-test` is added to the tool list in
     `check_ghidra_tooling`, and a re-copy drops it**
     (2026-09-25, issue #532). The 0x0751 isolation grader's suite is the
     pinned record of a dozen refusal policies — a mark set that does not
     hold, a void block, a withheld window, a `--block` that named no block, a
     capture given twice, a mark no block can be attributed to — and each is a
     gate between a human's hardware day and a wrong §7 call. The tool had
     neither `--check` nor `--self-test`, so it was absent from the list *and*
     the `*)` default would have handed it flags it does not have. Adding the
     path above the loop and this arm is the whole of it:

     ```sh
           *grade_0751_isolation.py)
             python3 "$tool" --self-test || rc=1
             ;;
     ```

     No `--work` and no `--check`, for item 6's reason: the grader has a
     required capture positional and neither mode, and a mode it does not have
     is not a thing the gate should call. Unlike every other tool in the loop,
     its `--self-test` runs the committed `unittest` suite by name in a
     subprocess rather than a hand-written list of known answers, and refuses a
     discovery that matched nothing — `Ran 0 tests` exits 0 and prints `OK`,
     which from outside a gate is a pass. Cheap tier for item 4's reason: the
     committed CSVs under `ec/tools/testdata/` and the standard library's
     `unittest` — no firmware image, no Ghidra, no network, no assembler. It
     measures **0.32 s** end to end here (the 76 tests are 0.192-0.193 s of
     that, the rest interpreter start) on 2026-09-25, against a cheap tier the
     paragraph above records at 5.9 s; that is one runner's figure and the
     ratio is the point, as item 6 says of its own. The 76 is the merged
     tree's: 74 on the branch point (`db6d7d2d`), 2 added here, and none
     since — #530's unplaced-window-scope cases are already its ancestor.
     **Until a human lands it, no commit runs that suite and a PR that breaks
     one of those refusals still merges green.** It is not here for item 4's
     reason, template-copied file and no `workflow` scope on the token; the
     whole of it is prepared at
     `docs/ci/agent-gates-0751-self-test.patch` and lands with
     `git apply docs/ci/agent-gates-0751-self-test.patch`.
     **A re-copy of `agent-gates.sh` from the template restores the
     eight-tool list, so the path and the arm have to be re-applied with
     it.**
  8. **`citation_gap_scan.py --check` and `--self-test` are added to the tool
     list in `check_ghidra_tooling`, and a re-copy drops both**
     (2026-09-25, issue #560). The population the call-graph gate cannot
     reach — 99 citing rows and 124 `(callee, citer)` pairs whose call, if
     real, sits at an address Ghidra's function boundary cut out of the citing
     row's own export — was an estimate until this tool measured it, and an
     estimate that `docs/findings/citing-listing-evidence.md` and
     `../ec/annotations/call-graph.md` both quote. `--check` holds the
     124-row `ec/ghidra/gap-citation-scan.csv` against the current bytes, the
     current listings and the current `disasm8051.py` tables; `--self-test`
     pins the population, the three verdicts and the `bank1,E57E` cut from
     oracles stated in the committed listings and `bank-call-targets.csv`.
     Item 6's arm shape verbatim, because the shape is forced by the tool:
     no `--work`, no scratch dir, both modes needing only python3, the
     committed listings and the committed firmware:

     ```sh
           *citation_gap_scan.py)
             python3 "$tool" --check && python3 "$tool" --self-test || rc=1
             ;;
     ```

     Cheap tier for item 4's reason, and the bank images build in pure Python
     from the committed firmware, so it needs no Ghidra, no network and no
     assembler. **A re-copy of `agent-gates.sh` from the template restores the
     eight-tool list, so the path and the arm have to be re-applied with
     it.** Its unit suite,
     `ec/tools/test_citation_gap_scan.py`, needs no wiring to be run at all:
     `tools/run-tests.sh` discovers every `test_*.py` in the repository, so it
     is already collected by the runner below — the same state the four suites
     in that paragraph are in.
- **`tools/run-tests.sh`, and the gate line that would call it**
  (2026-09-23, issue #162) — the four offline `unittest` suites
  (`ec/tools/test_grade_0751_isolation.py`, `windows/tools/test_ec_watch.py`,
  `windows/tools/test_manual_fan_ctrl_probe.py`, `linux/lightbar/test_probe_6005.py`)
  are 40 tests in all and **no gate and no workflow runs any of them**. Until
  #162, a green pipeline proved those files compile — the cheap tier's
  `check_python_syntax` `py_compile`s three of the four — and nothing more.
  #162 lands the runner (`tools/README.md` has it) and the documentation, and
  **deliberately not the gate call**, because this script is copied from the
  template: the wiring is an upstream `agent-pipeline` change and a re-copy, and
  the pipeline token's lack of `workflow` scope bars the workflow side
  independently. The runner prints its own scope on every run, the way the cheap
  tier prints the deep tier's deferral, so the gap is visible in the output and
  not only here.

  The call is one function and one `gate` line, and this is the whole of it:

  ```bash
  check_unittest_suites() {
    bash tools/run-tests.sh
  }
  ...
  gate 'unittest suites'  check_unittest_suites
  ```

  The argument for landing it is cost: the runner is **0.77 s** here
  (0.76–0.77 s over five runs) against a cheap tier the table above records at
  **5.9 s** on a GitHub-hosted runner. Those are two different machines and the
  ratio, not either absolute number, is the point — sub-second against
  single-digit seconds is a one-line change, not a negotiation. Two things to
  carry across with it. The cheap tier's printed "what this tier does not run"
  note needs **no edit**: it names only the `sdas8051` re-encode and the
  advisory cross-decoder comparison, and adding the suites is a coverage
  increase rather than a deferral, so nothing it lists stops being true. And
  the wiring should not acquire a coverage floor of its own — the runner prints
  what ran and asserts no test count, for the reason §14e gives for the
  printed-not-asserted elapsed line, and a floor added here is the one that
  gets deleted after a bad afternoon.
- **`.github/workflows/agent-plan.yml`**'s `CUSTOMISE` section — added the
  hardware/Windows-access constraint from `CLAUDE.md`, so the plan stage
  scopes issues needing the physical laptop or a Windows box down to
  prep-work-only rather than planning a live test it cannot run.
- **`.github/workflows/agent-review.yml`**'s blocking list — the template
  ships example invariants from another project; this copy blocks on
  `CLAUDE.md`'s rules instead (overclaiming, implied live tests,
  silent retractions, `registers.yaml` conventions, anything opened outside
  this repository, `vendor/` changes). Extended for the decompilation work
  with: a hand-edit to generated decompile output or a committed Ghidra
  project where the change belongs in an annotations CSV (with
  `bios/decompiled/*.annotated.c` named as the hand-restated exception, whose
  machine-readable counterpart is `bios/annotations/ghidra-functions.csv`);
  an annotation row with no `evidence`; a decompile failure read as a
  statement about the firmware when Ghidra's decompiler can fail silently
  instead; and `ec/decompiled/` and `bios/decompiled/` added to the
  citable-evidence list, which `docs/findings.md` already cited.
- **One review per run in `agent-review.yml`** (2026-09-24, not in the
  template). The template's second, inline pass (the `code-review` plugin,
  posting as `claude[bot]`) is gone. The verdict pass now returns its
  findings as structured data: file, line, problem, fix, whether each one
  blocks, and what it re-checked itself. The workflow renders that data as the
  markdown body of the `github-actions[bot]` review, and the same text is the
  fix stage's payload. A re-copy of the template brings back the inline pass
  and the one-paragraph `summary` schema.
- **A third review verdict, `rejected`** (2026-09-24, not in the template).
  The review can close a pull request instead of fixing it forward, for when
  fixing the findings would mean starting over (wrong approach, misread issue,
  a false core claim). The `Reject` step in `agent-review.yml` closes the pull
  request with the push token and deletes its branch. It then puts the review
  and the rejected plan at the top of the issue body, and moves the issue from
  `agent:working` to `agent:queued`, so the retry sweep plans it again and the
  new plan reads why the last attempt failed. The second rejection of an issue
  (`MAX_REJECTIONS`, counted by `<!-- agent-rejected -->` markers) gets
  `agent:stuck` instead. Before this, the only ways out were ten fix rounds
  ending in a draft, or a human's `agent:stop`, and neither was a decision.
- **`Refs`, not `Closes`, for `needs-hardware-test` issues** (2026-09-24, not in
  the template). Both `agent-implement.yml` (opening the pull request) and the
  review's `Approve` step (rewriting the body into the squash message) write
  `Refs #N` for an issue with that label. Such a pull request is the
  preparation and the issue is the live run. Closing it on merge is how #184
  and #283 were closed with their runs never done.
- **`needs-hardware-test` opts an issue out of the pipeline** (2026-09-25, not
  in the template). `agent-plan.yml`'s triage refuses it, `agent-implement.yml`'s
  kill switch stops on it, and `agent-retry.yml`'s stall, implement and plan
  sweeps skip it. Before this, such issues were planned and implemented
  like any other, and since the run itself cannot happen on a runner, the PRs
  re-prepared finished preparation or described runs nobody did.
  `agent-followups.yml` now files the preparation for a run as a separate
  issue without the label. The `Refs`-not-`Closes` logic below is still in
  place, for an issue labelled after its PR was opened.
- **`MAX_OPEN_AGENT_PRS` is 2** (2026-09-24), in `agent-plan.yml` and
  `agent-retry.yml`, down from 5 in the entry below. With 5 open, most merges
  left the other agent PRs conflicting, since nearly all of them edit
  `docs/findings.md` or `registers.yaml`. `CLAUDE.md` and the plan and
  implement prompts also ask for new write-ups in new files, for the same
  reason.
- **Parallel agents, and `.github/workflows/agent-conflicts.yml`** (2026-09-24,
  not in the template). The `agent-pipeline` concurrency group is one per issue
  (`agent-pipeline/agent/issue-N`) instead of one for the whole pipeline, so up
  to `MAX_PARALLEL_AGENTS` (5, in `agent-retry.yml`) stages run at once and
  `MAX_OPEN_AGENT_PRS` is 5. `agent-retry.yml` fills free slots and is the only
  thing that hands them out. It runs hourly, on every push to main, and whenever
  an agent stage finishes, because GitHub dropped most of the hourly cron events.
  Its sweeps go in priority order: stalled runs, conflicting PRs, missing
  reviews, missing follow-up passes, and then the implement and plan queues.
  Follow-ups come before issues because a merge left without one for
  `LOOKBACK_DAYS` never gets one. Parallel branches conflict with each other as
  they merge. For each open agent PR that GitHub reports as `CONFLICTING`, the
  sweep dispatches `agent-conflicts.yml` with that PR, one run each, so that the
  run takes up exactly one slot. That run squash-merges the branch onto
  current main, has Claude resolve the conflicted tree (regenerating the EC's
  generated files rather than hand-merging them), and force-pushes one linear
  commit, bounded at three attempts per PR head before `agent:stuck`. A re-copy
  of the template's workflows has to carry all of this across.
- **`.github/workflows/agent-followups.yml`** — its prompt reads
  `docs/MISSION.md`, and its label set is this repository's. Added here specifically so the issue queue doesn't dry up
  while `docs/MISSION.md`'s goal is nowhere near done; see its own header
  comment for what it does and why it uses `AGENT_PUSH_TOKEN` rather than
  the default `GITHUB_TOKEN` to open issues.

Apart from the provider override below, everything else under
`.github/workflows/agent-*.yml` is an unmodified copy of the `agent-pipeline`
template. If it fixes a bug in one of those
files, re-copy it rather than patching around it here.

## Model provider (local override, 2026-09-17; re-applied with a new model 2026-09-23)

All eight `claude-code-action` steps use OpenRouter's Anthropic-compatible
endpoint (`https://openrouter.ai/api`), `--model stealth/space-bunny-alpha`,
and `--effort max`. Each step passes `secrets.OPENROUTER_API_KEY` as both the
`anthropic_api_key` input and `ANTHROPIC_AUTH_TOKEN`; the OAuth input is no
longer used. Both callers of the reusable `agent-fix.yml` forward the new
secret, and that workflow requires it.

The Opus/Sonnet/Haiku default-model environment variables and
`CLAUDE_CODE_SUBAGENT_MODEL` also select `stealth/space-bunny-alpha`, so the
review plugin's model aliases do not select other models.
`CLAUDE_CODE_EFFORT_LEVEL` is set to `max` for inherited configuration as well
as the explicit CLI flag, and `CLAUDE_CODE_MAX_CONTEXT_TOKENS` is set to
`950000`. These are requested settings; provider-side reasoning behaviour and
the actual context-window size are not verified by the local YAML checks — if
the endpoint advertises a smaller window than 950000 tokens, the larger value
is what the CLI is told to assume.

The model was `stealth/union-alpha` when this override was first committed on
2026-09-17, and `0bf971c` was reverted in full by `4bec8e4` on 2026-09-18
without replacing it. The 2026-09-23 re-application is the same change with
`stealth/space-bunny-alpha` in place of `stealth/union-alpha` and the context
token setting added.

Why the revert is not repeated: the model is rotated, and `union-alpha`'s
turn was simply over — the revert was routine re-pointing at a current
stealth model, not a diagnosis of a failure. As of 2026-09-23, a check of
OpenRouter's public model list (`GET https://openrouter.ai/api/v1/models`, no
auth needed) finds `stealth/space-bunny-alpha` and no entry containing
"union" among the 456 models returned, which is consistent with a retired
slug rather than a broken one. When the next stealth model is rotated in,
this section is what changes: the `--model` flag, the four
`ANTHROPIC_DEFAULT_*_MODEL` variables, `CLAUDE_CODE_SUBAGENT_MODEL`, and the
`docs/agent-pipeline.md` text here.

The same listing gives `stealth/space-bunny-alpha` a `context_length` of
1000000, so `CLAUDE_CODE_MAX_CONTEXT_TOKENS: 950000` leaves headroom under the
real window rather than exceeding it, and it advertises `reasoning_effort`
among its supported parameters, so `--effort max` maps to something the
endpoint accepts. Pricing is listed as zero for both prompt and completion.
Re-check the listing before assuming any of this still holds: these slugs
turn over, which is the whole reason the revert exists.

All eight steps also pass `--dangerously-skip-permissions`, as explicitly
requested for unattended CI. This bypasses Claude Code permission prompts;
`--allowedTools` is no longer a default-deny boundary. The existing explicit
`--disallowedTools` lists remain, but are not a sandbox or a guarantee that
shell commands cannot perform equivalent operations. Earlier workflow
comments describing the allowlist as the safety boundary predate this
override and no longer describe the effective configuration.

These are human-requested provider and CLI-permission overrides. GitHub
job permissions, approval gates, triggers, prompts and action pins are
unchanged. Preserve the overrides when re-copying the template. The
repository Actions secret `OPENROUTER_API_KEY` is set (added 2026-09-17);
the old `CLAUDE_CODE_OAUTH_TOKEN` is still present but is not a fallback.
No live OpenRouter workflow run was performed for this change to validate
the credentials or the model's availability on the endpoint.

## `claude.yml` — not from agent-pipeline, from `/install-github-app`

Anthropic's own Claude Code CLI has an `/install-github-app` setup command
that, independently of `agent-pipeline`, installs its standard quickstart
templates: an `@claude`-mention assistant (`claude.yml`) and an
automatic PR reviewer (`claude-code-review.yml`, since removed — see
`claude.yml`'s own header comment for why). Both originally used the same
`CLAUDE_CODE_OAUTH_TOKEN` secret that `agent-pipeline` needed, so running
that command was a reasonable way to get the secret set — but as shipped,
neither template knows `agent-pipeline` exists: `claude-code-review.yml`
duplicated `agent-review.yml`'s job outright, and `claude.yml` shared no
concurrency group with anything, so an `@claude` mention on an
agent-authored pull request would have run a second, fully independent
session in parallel with whatever the pipeline was doing on it.

`claude.yml` was kept — a mention-triggered conversation is a real
capability the autonomous pipeline doesn't have — but joined to the shared
`agent-pipeline` concurrency group (on the job, not the workflow), and
since the repository went public it only runs for a mention by the owner,
a member or a collaborator. The reasoning for both is in the comment at the
top of that file; don't restate it here where it can drift out of sync.

## Setup state

Everything the upstream README's setup section asks for is in place, as of
2026-09-15, when the repository went public:

- Both secrets (`CLAUDE_CODE_OAUTH_TOKEN`, `AGENT_PUSH_TOKEN`). The PAT is
  fine-grained, scoped to this repository only, with Contents, Pull
  requests, Issues and Actions write, and no `workflow` scope. Actions
  write is what `gh workflow run` needs; without it every hand-over from
  plan to implement fails with `HTTP 403: Resource not accessible by
  personal access token`.
- The labels, including `agent:queued`.
- The `agent-approval` environment, with the owner as required reviewer.
- A ruleset on `main`: pull request with one approval (stale approvals
  dismissed on push), required checks `gates` and `workflows`, no deletion
  or force-push, repository admins as bypass actors.
- Actions settings: default `GITHUB_TOKEN` read-only (every workflow
  declares its own permissions), Actions allowed to approve pull requests,
  approval required for workflow runs from any outside contributor's
  fork, auto-merge on, merged branches deleted.
- Issue and pull request creation limited to collaborators. The pipeline
  is unaffected: it creates issues and pull requests with
  `AGENT_PUSH_TOKEN`, which is the owner's.

While the repository was private, required environment reviewers and
rulesets were both unavailable on its billing plan, so the approval gate
enforced nothing and PR #21 merged without a completed review. Going
public is what closed both gaps.
