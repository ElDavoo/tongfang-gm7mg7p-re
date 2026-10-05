# `bank_attribution.py --self-test` gets a gate arm, by folding into the one patch that already holds the tail (issue #1081)

**The issue asked for a new file, `docs/ci/agent-gates-bank-attribution-self-test.patch`. That file cannot exist, and the reason is measured below rather than argued.** The tool's `--self-test` folds into `docs/ci/agent-gates-reassembly-bound-check.patch`, which already holds the only free region in `agent-gates.sh`. This is the same answer [`audit-call-targets-gate-arm.md`](audit-call-targets-gate-arm.md) gave for the sibling tool, and it is stated here as the other half of that fact rather than discovered at merge time.

What this branch adds is **a prepared patch, not a line in the gate**. Nothing under `.github/` is edited, and CI does not run this until a human lands it with `git apply`. Nothing below is a register behaviour, a live test, or evidence about the laptop: the mode reads a committed firmware image and committed text, opens no capture, reads back no register, and **no new hardware observation is needed to close this issue.**

## The measurement that decides the shape

The issue's request is a standalone patch file. Before cutting one, the anchor was measured against a scratch copy of the committed `.github/scripts/agent-gates.sh`, and against the patch that already holds that region — a cut of this tool's `if` block alone, against the same tail of `check_ghidra_tooling()` after `done` and before `rm -rf "$scratch"`:

```
standalone alone              -> APPLIES
fold, then standalone         -> COLLIDES (:297)
standalone, then fold         -> COLLIDES (:298)
```

Each applies cleanly on its own and the pair fails in **both** orders. That is the silent failure shape [`prepared-gate-patches.md`](prepared-gate-patches.md) has recorded before: each patch still applies alone, so a human reaching for `git apply` lands one and only discovers the other will not follow at the point where the second is wanted.

So: **one arm, folded into `agent-gates-reassembly-bound-check.patch`.** The correction to the issue's request is stated here rather than quietly followed, which is the point of writing it down at all. Verified on the folded result: it applies alone, composes with every other prepared patch in `docs/ci/` in both orders, the full set lands, and the result passes `bash -n` and `shellcheck`. `tools/test_agent_gates_patches.py::CompositionTests` is what holds that, and it is why this was decided before the patch was re-cut rather than found at the end.

**A consequence worth stating, because the issue says otherwise.** The issue carries an edit to `tools/test_agent_gates_patches.py`'s `PATCHES` list on the grounds that a new patch file turns that suite red. That clause holds only under the reading this measurement rejects: no new file exists, so the list is unchanged. What replaces it is a retention suite of its own, below.

## What the arm buys, and how that compares with the sibling's

The sibling fold's first cut claimed its arm was "what first notices a different dump", and `audit-call-targets-gate-arm.md` retracts that: `ec/tools/test_audit_call_targets.py` is committed, is found by `tools/run-tests.sh`, and already asserts the status its self-test returns. **That retraction does not transfer here, and the difference was measured rather than assumed** — but the difference is not the one an earlier cut of this section claimed, and naming it correctly is what the measurement below turns on.

There is no `ec/tools/test_bank_attribution.py`. `ec/tools/test_dispatch_edges.py` imports the module and drives it as a subprocess, but only with `--regions-csv` and `--pairs-csv`. The checks themselves are not unasserted, though: `ec/tools/test_bank_attribution_common_follow.py` is committed, is found by `tools/run-tests.sh`, runs in CI's `tests` job, and `TheSelfTest::test_it_passes` calls `self_test()` in-process over the committed image and asserts the status. The stub→bank decoding, the seed census and both hand-decoded pins are checks *inside* `self_test()`, so that one assertion covers all three. Measured on the committed tree:

| mutation to `bank_attribution.py` | shipped `--self-test` | `test_dispatch_edges.py` | `test_census_closure_functions.py` | `test_bank_attribution_common_follow.py` |
|---|---|---|---|---|
| `main()`'s `if args.self_test: return self_test(d)` no longer calls `self_test()` | exits 0, printing the tool's report with no `self-test passed` line | **green** | **green** | **green** |
| one hand-decoded pin's condition forced false | exits 1 | **green** | **green** | **red** — `TheSelfTest::test_it_passes` |

Neither mutation was left in the tree, and the last column's cells were measured
rather than carried over from the first two. **So the checks are already asserted in CI, transitively, and what nothing committed exercises is the shipped command's path** through `main()`, `argparse` and the exit status — `TheSelfTest` calls `self_test()` in-process and reaches none of the three, which is why the first row leaves it green. That is the gap the issue describes, and it is the gap this arm closes.

An earlier cut of this section generalised from the two suites its table named to the whole tree, and concluded the checks were "proven by `ec/annotations/bank-attribution.md` and by nothing else in this repository." That was wrong in the way CLAUDE.md's calibration rule is about: it had measured the two suites it named and read the result as a census of the suites it did not. The distinction that survives measurement is the shipped-command path, not the absence of any committed assertion — which is the same ground the sibling's retraction stands on, so this arm adds what the sibling's adds rather than more than it, and the earlier "unlike the sibling's" framing is withdrawn on both counts.

The first row is the sharp one, and **catching it takes both halves of what the arm reads.** A command that exits 0 having printed its report is green to `|| rc=1`, so the landed call writes the command's stdout to `$scratch` and greps it for the `self-test passed` line the tool prints on success. What the row measures is the tool falling through to its ordinary report path, not silence — so the failure a reader meets is a full, plausible-looking account of the image on stdout and a green gate, and that is the more dangerous of the two shapes precisely because nothing looks broken. (`return 0` in place of the dispatch does print nothing and is caught the same way; it is a different mutant and it is not the one named above.) The second row is caught by the status on its own. `tools/test_gate_arm_bank_attribution.py::ArmBehaviourTests` runs the landed block against a stub for each row rather than leaving this table to be the only evidence, the same arrangement the sibling suite uses for its own.

What the arm still does not catch, so that a green run is not over-read: **a self-test that prints its summary line with a check deleted from it.** The arm reads a status and a line; so does any in-process suite; neither counts the checks. That limit is why no claim here is a check count.

The checks themselves are re-derived from the committed `ec/firmware/GMxMGxx_11.800` by the command below, and the committed image passes today: the stub→bank decoding through `find_stubs()`, the seed census, the two hand-decoded pins `bank-attribution.md` §1 gives, the two `jmp @a+dptr` dispatch shapes §5 names, the four verdicts over both populations, and the per-run `bounds` column. **No second image has been tried and none is claimed.** It reads committed text and the committed image and nothing else.

## What it does not buy

**It does not settle the banking assumption the tool exists to attack.** That assumption is what `bank-call-audit.md` §4 calls out — of the distinct (caller bank, target) pairs, most are "both banks live", and "the assumption is what decides these, not the evidence." This arm re-derives the closure's arithmetic over bytes this repository commits. A green run means the closure reproduced what it recorded; it does not mean the closure is right about the machine. No capture was opened, no register was read back, and nothing in `ec/annotations/registers.yaml` moves.

## Why the arm is not in the tool loop

`bank_attribution.py` takes a positional firmware path and **neither `--work` nor `--check`** — `python3 ec/tools/bank_attribution.py --work /tmp --check` exits 2 on `unrecognized arguments`. The `*)` default in `check_ghidra_tooling()` runs `python3 "$tool" --work "$scratch" --check`, so a tool in the loop reaching `*)` is `check_gate_arm_coverage.py`'s direction 1, which runs in the cheap tier today and would go red.

That is the placement reason. The composition reason is separate: every position in the tool list and every line of the `gate` list is already another prepared patch's context. The tail is the one region left, and it is the right gate regardless — every arm of that loop is committed-text work under `python3`, and this tool and its image are both committed.

## The one thing to know before landing it

`check_gate_arm_coverage.py` **direction 3** reads a tool docstring that puts its tool *in* `.github/scripts/agent-gates.sh` and requires a `case` arm to satisfy the claim. A tail call is not a `case` arm. So a docstring that gained a gate-membership claim would go red against an arm that is landed and working — the opposite of what direction 3 is for.

This is the non-obvious way to break the fold, because the instinct on landing an arm is to write down that it is landed in the place that reads like the authority on the tool's own behaviour. **`bank_attribution.py`'s docstring names no gate path today, and that is what keeps the check green.** `tools/test_gate_arm_bank_attribution.py::DocstringClaimTests` holds it using the checker's own `claims()` predicate rather than a copy of it, so the suite and the gate cannot disagree about what a claim is.

## Cost

`bank_attribution.py <image> --self-test` measures between **0.91 s and 0.96 s** over five runs here on 2026-10-05, against a cheap tier that printed 40 s elapsed on this runner.

One runner's figures, and they move by roughly a factor of two between runners, so the ratio is the durable part — the caveat `docs/agent-pipeline.md` item 6 gives for `call_graph.py`. Against the calls the same fold already carries, `reassembly_checked_bound.py --check` and `audit_call_targets.py <image> --self-test`, this is the middle one on this runner; and it is **not** the largest arm the gate carries, since `xdata_register_map.py --self-test` measures 7.18 s on the sibling's runner.

## The test

`tools/test_gate_arm_bank_attribution.py`, found by `tools/run-tests.sh` without registering anywhere, and `tools/README.md` gains no row because `tools/test_readme_suite_table.py` fails if that table grows one back.

It is a **separate file** from `tools/test_gate_arm_audit_call_targets.py` rather than a class appended to it, for the reason CLAUDE.md gives: the sibling suite is shared, and two branches appending to one long suite collide at its last line. Its helpers are re-derived rather than imported, because they are that file's private API. The one thing it does import is `ec/tools/check_gate_arm_coverage.py`, and it imports the production checker rather than a test helper precisely because it is the authority on what a gate claim is.

The case that matters is the mutation, and it is **measured on the half-folded patch** rather than asserted in prose. A re-cut that keeps the two calls already there and drops this one is silent in every check the tree had, and each of those was measured rather than assumed:

| property of the half-folded patch | holds? | caught by |
|---|---|---|
| `git apply` exits 0 | yes | nothing |
| composes in every ordered pair | yes | nothing |
| `bash -n` and `shellcheck` clean | yes | nothing |
| `check_gate_arm_coverage.py --check` green | yes | nothing |
| `tools/test_agent_gates_patches.py` | green | nothing |
| `tools/test_gate_arm_bank_attribution.py` | **red** | this suite |

The suite builds the half-folded patch itself rather than asserting the property in prose, so the "it would have been silent" claim is re-derived every run. The second thing it holds is the arm's own behaviour: `ArmBehaviourTests` extracts the `if` block the patch lands, runs it under `bash` against a stub `bank_attribution.py` for each row of the mutation table above, and asserts the exit status each one has to produce.

## Not claimed

No live test ran, no register was read back, no second image was tried, and no capture or EC was opened. The guard is **prepared, not landed**: nothing under `.github/` is edited in this branch.

`tools/check_doc_patch_refs.py` *is* edited, and one edit is worth naming here rather than leaving to the diff: it gains a `HISTORICAL` key for `agent-gates-bank-attribution-self-test.patch`, the filename this issue asked for that deliberately is not on disk. That is the mechanism the sibling fold already uses, and the enumeration is held in both directions — still absent from `docs/ci/`, still cited — so a patch reappearing under that name, or a reference being edited away, goes red. Its suite's pin moves with it and stays an exact set rather than a bare count.

The issue also asks for "a short pointer from `docs/findings.md`". **That edit is not made**: CLAUDE.md freezes the file, `ec/tools/check_findings_frozen.py` fails an added section, and "no summary section, no pointer appended here" is the one edit it does not permit. This write-up is the record.

## Serialise with #1094

`docs/ci/agent-gates-reassembly-bound-check.patch` is edited by both this branch and #1094's, each adding a different tool's call at the same place in the same hunk. Two branches editing one patch file is a conflict neither side would choose to drop. `docs/findings/audit-call-targets-gate-arm.md` already records that half; this is the other.

## Re-deriving

```sh
python3 ec/tools/bank_attribution.py ec/firmware/GMxMGxx_11.800 --self-test
python3 tools/test_gate_arm_bank_attribution.py
python3 tools/test_agent_gates_patches.py
python3 tools/check_doc_patch_refs.py --check
python3 ec/tools/check_gate_arm_coverage.py --check
```
