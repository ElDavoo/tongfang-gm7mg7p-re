# `audit_call_targets.py --self-test` gets a gate arm, by folding into the one patch that already holds the tail (issue #1094)

**The issue asked for a new file, `docs/ci/agent-gates-audit-call-targets-self-test.patch`. That file cannot exist, and the reason is measured below rather than argued.** The tool's `--self-test` folds into `docs/ci/agent-gates-reassembly-bound-check.patch`, which already holds the only free region in `agent-gates.sh`. This is the same answer issue #1146 gave for `bank_call_regions.py`, and the same shape issue #1081 needs for `bank_attribution.py`: **one arm, not two.**

What this branch adds is **a prepared patch, not a line in the gate**. Nothing under `.github/` is edited, and CI does not run this until a human lands it with `git apply`. Nothing below is a register behaviour, a live test, or evidence about the laptop: the mode reads a committed firmware image and committed text, opens no capture, reads back no register, and **no new hardware observation is needed to close this issue.**

## The measurement that decides the shape

The issue's request is a standalone patch file. Before cutting one, the anchor was measured against a scratch copy of the committed `.github/scripts/agent-gates.sh`, and against the patch that already holds that region. Two candidate cuts, one for each tool, both at the tail of `check_ghidra_tooling()` after `done` and before `rm -rf "$scratch"`:

```
A alone  -> APPLIES        B alone  -> APPLIES
A then B -> COLLIDES      B then A -> COLLIDES
```

Each applies cleanly on its own and the pair fails in **both** orders. That is the silent failure shape [`prepared-gate-patches.md`](prepared-gate-patches.md) has recorded before: each patch still applies alone, so a human reaching for `git apply` lands one and only discovers the other will not follow at the point where the second is wanted.

A second anchor *inside* the tail was tried as well — the audit call cut before the `done` rather than after it, so the two calls would not share a pre-image window. It collides identically, in both orders. **There is no way to buy independence by moving the cut.**

So: **one arm, folded into `agent-gates-reassembly-bound-check.patch`.** The correction to the issue's request is stated here rather than quietly followed, which is the point of writing it down at all.

`tools/test_agent_gates_patches.py::CompositionTests` is what holds the set's composition, and it is why this was decided before the patch was cut rather than found at the end. Its `ArmRetentionTests` and `FoldTests` are the classes that hold a fold's halves; `tools/test_gate_arm_audit_call_targets.py` is where this fold's halves are held, in a separate file so a third branch adding to the same fold does not append to a shared long suite.

## The answer to #1081: one arm, not two

Issue #1081 covers the sibling arm for `ec/tools/bank_attribution.py`. The question it defers here is whether the two should be one arm or two, so a re-cut collision table is not written twice.

**One arm.** Both tools read the committed image, need no Ghidra and no network, and both take `<image> --self-test`. The reason is structural rather than a matter of taste: both want the same tail region, and §"the measurement" above shows what happens to two patches that do. #1081's tool folds into the same file.

**This is a fact to state in both write-ups rather than discover at merge time:** #1081's pull request and this one must serialise on `docs/ci/agent-gates-reassembly-bound-check.patch` and on the retention test that holds it. Two branches editing one patch file is a merge conflict, and unlike most conflicts in this repository it is not a line either side is willing to drop — both patches add the same tool's call at the same place.

A re-cut reads [`prepared-gate-patches.md`](prepared-gate-patches.md) for the collision table. (The issue says `docs/ci/prepared-gate-patches.md`; that path does not exist. The table is in `docs/findings/`, which is where that file records the row for this fold.)

## What the arm buys, and what it does not

**The premise this branch started from was false, and the correction is worth more than the arm.** The reasoning behind this fold was that `audit_call_targets.py`'s `--self-test` "runs nowhere … the mode is run by nothing on merge or on a sweep", and that its two block-framing checks are "the first thing in the tool that would notice a *different* dump". Both sentences are wrong, and the error came from the issue's own quoted text being repeated instead of checked against the tree.

`ec/tools/test_audit_call_targets.py` is committed on `main`. `tools/run-tests.sh` finds it by its `test_*.py` sweep, and `.github/workflows/ci.yml` runs that sweep on every push and pull request. It reads the committed image, calls `act.self_test()` on it, and asserts the status that call returns — and every check in that transcript, the two named here included, feeds the same counter that status is derived from. Measured by mutation, on the committed tree:

| mutation to `audit_call_targets.py` | `test_audit_call_targets.py` |
|---|---|
| the stride check's condition forced false | **red** |
| the zero-external-sites check's condition forced false | **red** |

So a dump that broke either check is already noticed on every sweep, before this arm exists. **The claim that the arm is what would first notice a different image is retracted here rather than left standing**, and the same sentence is corrected in the patch header, in `tools/test_gate_arm_audit_call_targets.py`, and in the pull request description.

What the arm does add is real, and it is one thing: **it runs the shipped command as a process rather than calling the function.** The suite calls `act.self_test(d)` in-process, so it never goes through `main()`, `argparse`, or the exit status — and a break in any of those is invisible to it. Also measured, on the committed tree:

| mutation to `audit_call_targets.py` | the shipped command | `test_audit_call_targets.py` |
|---|---|---|
| `--self-test` no longer dispatches to `self_test()` | exits 0, printing nothing | **green** |
| the `--self-test` flag itself is renamed | exits 2 | **green** |

The first is the sharp one: the tool's whole self-test stops running and the command a person would type reports success. That is the shape of failure the in-process suite cannot have, and it is the same distinction `test_call_graph_gaps.py` draws when it drives `--self-test` as a subprocess — "the arm that matters is the one that returns an exit code, and calling the function would not exercise the argument handling that reaches it."

That is a much smaller claim than the one this branch began with, and it is the one the patch now makes. Two of the transcript's checks are worth naming anyway, because they are what a *different* image would move, and both name themselves when they break:

- **the BL51 trampoline block's framing** — that its 403 entries are one 6-byte-stride run over `0x1150-0x1AC2`, which is what licenses the zero-external-sites answer beneath it;
- **that zero itself** — all 170 relative sites that resolve onto a trampoline entry have their own address inside the block, so none of them is a branch reaching it from outside.

Both are re-derived from the committed `ec/firmware/GMxMGxx_11.800` by the command below, and the committed image passes both today. Those two counts are properties of that image and the byte scan over it, not of this repository's text. **No second image has been tried and none is claimed** — the sweep would notice one breaking either check, and the arm would too, but neither has been run against a dump this repository does not commit.

## Why the arm is not in the tool loop

`audit_call_targets.py` takes a positional firmware path and **no `--work`**. The `*)` default in `check_ghidra_tooling()` runs `python3 "$tool" --work "$scratch" --check`, and the tool's argparse exits 2 on those flags. A tool in the loop reaching `*)` is `check_gate_arm_coverage.py`'s direction 1, which runs in the cheap tier today and would go red.

That is the placement reason. The composition reason is separate, and both are in the patch header: every position in the tool list and every line of the `gate` list is already another prepared patch's context. The tail is the one region left, and it is the right gate regardless — every arm of that loop is committed-text work under `python3`, and this tool and its image are both committed.

## The one thing to know before landing it

`check_gate_arm_coverage.py` **direction 3** reads a tool docstring that puts its tool *in* `.github/scripts/agent-gates.sh` and requires a `case` arm to satisfy the claim. A tail call is not a `case` arm. So a docstring that gained a gate-membership claim would go red against an arm that is landed and working — the opposite of what direction 3 is for.

This is the non-obvious way to break the fold, because the instinct on landing an arm is to write down that it is landed in the place that reads like the authority on the tool's own behaviour. **Neither docstring may gain a gate-membership claim.** Both name no gate path today, and that is what keeps the check green; the claim belongs in the patch header and here, which is where a reader comes to land the arm from. `tools/test_gate_arm_audit_call_targets.py::DocstringClaimTests` holds it, using the checker's own `claims()` predicate rather than a copy of it, so the suite and the gate cannot disagree about what a claim is.

## Cost

`audit_call_targets.py <image> --self-test` measures **3.78 s** over three runs here on 2026-10-04 (3.80 / 3.78 / 3.78), against a cheap tier that printed 47 s elapsed on the same runner.

One runner's figures, and they move by roughly a factor of two between runners, so the ratio is the durable part — the caveat `docs/agent-pipeline.md` item 6 gives for `call_graph.py`. **Correction to the reasoning this branch started from:** the plan that produced it called this "the largest single addition the gate has carried." Measured, it is not: `xdata_register_map.py --self-test` is 7.18 s over three runs on this runner (7.22 / 7.18 / 7.18) against this one's 3.78 s. It is a material addition and not a record one. The patch header carries the same correction rather than the figure it was handed.

## The test

`tools/test_gate_arm_audit_call_targets.py`, found by `tools/run-tests.sh` without registering anywhere, and `tools/README.md` gains no row because `tools/test_readme_suite_table.py` fails if that table grows one back.

The case that matters is the mutation. A re-cut that keeps `reassembly_checked_bound.py` and drops `audit_call_targets.py` is silent in every check the tree already had, and each of those was measured on the half-folded patch rather than assumed:

| property of the half-folded patch | holds? | caught by |
|---|---|---|
| `git apply` exits 0 | yes | nothing |
| composes in every ordered pair | yes | nothing |
| `bash -n` and `shellcheck` clean | yes | nothing |
| `check_gate_arm_coverage.py --check` green | yes | nothing |
| `tools/test_agent_gates_patches.py` | green | nothing |
| `tools/test_gate_arm_audit_call_targets.py` | **red** | this suite |

It is the only case in the tree that fails on that mutation, which is how it is known to be worth having. The suite builds the half-folded patch itself rather than asserting the property in prose, so the "it would have been silent" claim is measured on every run and not just at the time it was written.

## Not claimed

No live test ran, no register was read back, no second image was tried, and no capture or EC was opened. The guard is **prepared, not landed**: nothing under `.github/` is edited in this branch, and `tools/test_agent_gates_patches.py` knows nothing about a new patch name, which is the point of folding rather than adding a file.

`tools/check_doc_patch_refs.py` *is* edited, and one edit is worth naming here rather than leaving to the diff: it gains a `HISTORICAL` key for `agent-gates-audit-call-targets-self-test.patch`, the filename this issue asked for that deliberately is not on disk. That is the mechanism #1033's `agent-gates-check-history-checkouts.patch` already uses, and the enumeration is held in both directions — still absent from `docs/ci/`, still cited — so a patch reappearing under that name, or a reference being edited away, goes red. Its suite's pin moves with it and stays an exact set rather than a bare count.

## Re-deriving

```sh
python3 ec/tools/audit_call_targets.py ec/firmware/GMxMGxx_11.800 --self-test
python3 tools/test_gate_arm_audit_call_targets.py
python3 tools/test_agent_gates_patches.py
python3 tools/check_doc_patch_refs.py
python3 ec/tools/check_gate_arm_coverage.py --check
```