# `xdata_register_map.py --self-test` was switched off for a reason that had
# stopped being true, and nothing ran the census's oracles (2026-09-25, issue #815)

The XDATA register census is the one tool in this repository whose self-test is
the oracle for a large set of committed claims, and the cheap tier ran the
weaker of its two modes for reasons that had gone stale. This branch runs **both**
and rewrites the comment that gave the reason, in place, keeping the stale claim
visible next to a dated correction per [`../findings.md` §4a-4d](../findings.md).

**Nothing here is a register behaviour, a live test, or evidence about the
laptop.** `--check` and `--self-test` both read committed text only — the
decompiled tree, two annotation CSVs, and the 2,711 committed
`ec/decompiled/*/*.asm` that `--self-test` adds. No firmware image is opened, no
Ghidra project is touched, no register is read back, and no hardware or Windows
step is needed to close this issue.

## What was measured, on this runner

At `64dbde1`, from the repo root. The exit codes are the claim; the timings are
one runner's, and the third block says how much they can be trusted.

```console
$ python3 ec/tools/xdata_register_map.py --check | tail -1 ; echo $?
.../ec/annotations/xdata-clusters.csv: 439 rows match a fresh generation from the committed tree at threshold 0.5
0

$ python3 ec/tools/xdata_register_map.py --self-test | tail -1 ; echo $?
  all assertions passed
0
```

`--self-test` prints **101** assertion lines and ends `all assertions passed`.
`--check` prints the two CSV regeneration lines and exits 0. Neither run changes
the tree — `git status` is unchanged after both, which is what makes them safe to
put in a per-commit gate rather than only a local one.

## The retraction: `FUN_CODE_*` was not why the mode was off

The comment this branch replaces said, in its own emphatic words, that
`--self-test` was "**deliberately not run, and that is not an oversight**" and
"red on `main` for a reason no census change can clear", because the annotation
CSV named three functions that `ec/decompiled/index.csv` "still spells
`FUN_CODE_*`". That reason was **already untrue when it was written**, and it is
the same correction [`thunk-prefix-collision.md:271-289`](thunk-prefix-collision.md)
recorded from the rename side and left unwired. The three rows, as committed:

| address | `ec/decompiled/index.csv` | name |
|---|---|---|
| `bank1:0x9CE8` | `:996` | `seed_1c12_trio_or_update_1c11_1c15_1c16` |
| `bank1:0x9D53` | `:999` | `seed_1c12_trio_9f_or_run_0x9d7a_ladder` |
| `bank1:0xE2D3` | `:1333` | `dispatch_036c_low3_then_seed_1c00_block` |

```console
$ grep -n "FUN_CODE_9CE8\|FUN_CODE_9D53\|FUN_CODE_E2D3" ec/decompiled/index.csv ; echo $?
1
```

So the write it said would have to happen to clear the assertion — a
`build_ec_decompile.py` export-only run, rewriting the generated
`ec/decompiled/**` tree and belonging to whoever landed the renames — **was not
the mechanism**, and the warning about sweeping every later annotation into that
diff was warning about a run nobody needed to make. The annotation CSV's
agreement-with-`index.csv` assertion passes on the committed tree today.

The cost of leaving a well-documented deferral in place is the thing the cheap
tier's own doctrine names: *"a deferral nobody can see is a check that gets
dropped."* This one was unusually visible, and it was still wrong for long
enough that four separate files had repeated it. That is the finding, and the
gate arm is the fix.

## What the mode adds that `--check` cannot reach

`--check` is the whole reproducibility claim in one command and it is worth
keeping as a separate step — it diffs, so it names the file and line. It is not
the census's oracle. The old comment said so itself and then stopped there; these
are the assertions that were unreachable before this branch, all printed green
in the gate run above:

- **the corpus-wide direction invariant**, over 5,677 occurrences across 1,008
  distinct addresses — every one the census buckets `write` or `read+write` has
  an assignment rather than a `==` after the address, per address and not only in
  aggregate, and the only occurrences the second pass accepts and the census does
  not are the 2 `*`-dereference stores;
- **the tree-wide `==` direction**: none of the 838 `==` occurrences in the tree
  is bucketed as a store, which is §4.3's claim and the one the `--no-eq-guard`
  switch exists to measure against;
- **the §4.1 `BUCKET_TOTALS` pin** — `read 8826 / write 3587 / read+write 2482 /
  passed-to-call 534 / address-taken 267`, a hard-coded constant
  (`xdata_register_map.py:1212`) compared against a fresh generation, so it is a
  pin and not the run restating itself;
- **the whole export-ownership oracle** (`--export-ownership`): 1,326 distinct /
  10,178 references, its own five bucket totals, the guarantee that the pass
  **loses no address** ("if this ever names an address, an owner was not a
  superset of its non-owners"), and the 296 addresses whose `refs` it moves;
- **the renumber a guard flip would cause**: 440 clusters against the committed
  439, 400 of the committed `cluster_key`s surviving, 4 of the 9 hand names in
  `annotations/xdata-cluster-names.csv`. Without this, `--no-eq-guard` becomes a
  measurement whose consequences to the committed citations nobody checks;
- **the `NOT_IN_TREE` arithmetic** — the 17 addresses `xdata-symbols.csv` names
  and the census does not reach, so `175 named_in_tree` is `192 - 17` and not a
  number to be taken on trust, plus the calibration check that **none** of their
  reasons contains a word claiming the byte is gone (`absent`, `does not exist`,
  `no such`, `unused`, `never touched`, `dead`);
- **the 439-distinct-`cluster_key` check**, read back from the committed
  `xdata-clusters.csv` rather than from a fresh generation, so a key names a
  membership and not a rank and a citation resolves to one thing;
- **the name-carry and Jaccard checks** — every carried name's Jaccard
  re-measured from the CSVs, and every committed name either carried again or
  reported as a tie, so a name is never silently dropped.

The three worked examples it also carries (the `0x0402` and `0x0408` accessor
resolutions and the `0x0318` double-count shape) are the ones that keep the
accessor pass from inventing a phantom read; they are in the tool's own
`HAND_CHECKED`/`COREADING_CHECKED` tables and are noted here only so the list is
not read as the complete inventory.

## The refusals matter as much, and they are unchanged

The new line adds no flag, so the guards the census already has are exactly as
they were — but they are what makes the `&&` chain above safe to trust, and
**no gate calls `ec/tools/test_xdata_register_map.py`**, which is where they are
pinned:

- `--no-eq-guard` and `--export-ownership` are refused with `--check` and
  `--self-test` alike, because both are gates and a flag that can change a
  bucket without changing anything on disk must not be reachable inside a mode
  whose whole claim is that nothing changed;
- both are refused again unless given `--out-registers` and `--out-clusters`,
  so neither can reach the committed CSVs. The hazard the second refusal
  prevents is measurable: pointed at a scratch `--out-` pair, `--export-ownership`
  produces **440** clusters against the committed 439 — the renumber its own
  assertion pins, and a file that would not match the committed one. (An earlier
  version of the census tool's own test comment put that at "35 of the 430
  clusters and 5 of the 10 hand names"; the committed
  `annotations/xdata-cluster-names.csv` carries 9 names, and the 430 is long gone.
  The renumber to quote is the self-test's, re-derived, not this file's.)

The cheap tier now runs the assertions; it still does not run this suite, and
that is unchanged. `tools/run-tests.sh` collecting it is #773's.

## The cost, and whose runner it was measured on

| mode | here | issue #815's reporter | planning runner |
|---|---|---|---|
| `--check` | 2.03 s | 1.35 s | 2.49 s |
| `--self-test` | 5.11 s | 3.44 s | 6.17 s |

Three runners, a factor of about 1.9 between the fastest and the slowest, in
**both** modes — so the absolute figures are the runner's and the **ratio is the
durable part**: `--self-test` is about 2.5× `--check` on all three. What the
caller can rely on is the cheap tier's own total, which this branch measures at
**`All gates passed (21s elapsed)`** with both modes in it. The numbers above are
recorded because a later reader re-deriving them will not get the same ones, and
a comment that quotes a remembered figure is exactly the failure
[`../findings.md` §4](../findings.md) exists to prevent.

## The patch re-cut, which this change forced

`.github/scripts/agent-gates.sh` is what the other five prepared patches cut
their context against, and
[`../ci/agent-gates-disasm8051-self-test.patch`](../ci/agent-gates-disasm8051-self-test.patch)
hunk 2's context **is the arm body this branch changes**:

```
@@ -235,6 +236,34 @@ check_ghidra_tooling() {
       *xdata_register_map.py)
         python3 "$tool" --check || rc=1
         ;;
```

So the arm-body swap took that patch from applying to `patch does not apply at
:235`, and left it there. A **comment-only** edit above the arm would not have —
the hunk's context starts at the arm — which is why the comment is worth having
in the first place and why this is the one edit to the file that costs something.
The re-cut is a context refresh and nothing else: the new context line, the `@@`
numbers (`-235`→`-261`, `+236`→`+262` — the arm moved 26 lines because the
comment grew from 25 lines to 51), and the `index` line's pre-image blob, which is
now the gate script **as this branch leaves it**. The arm text, **hunk 1** and the
patch's own header are byte-identical: hunk 1 still reads `@@ -126,7 +126,8 @@`
against the same seven context lines, because the tool list above the arm did not
move. That is checkable without taking my word for it — the re-cut body is
`git diff`'s own output, and the diff between the two is the blob hash and one
`@@` line.

**The failure mode this exposed is the one a future re-cut needs to know about.**
`tools/test_agent_gates_patches.py` seeds its scratch trees from the *working
tree* and asserts that file is byte-identical to `git show HEAD:` of it, so a
branch whose deliverable **is** the gate script leaves 14 of its 15 cases green
and the fifteenth — `test_the_working_tree_gate_script_is_the_committed_one` —
failing by construction, with a message that reads "Commit it and re-cut the
patches, or drop the edit". Both halves of that instruction are needed and only
one is available inside a PR. Nothing was weakened to hide it; the case is
untouched, and the proof that it is green at the commit is in the PR body. The
per-pair composition cases, `bash -n` and `shellcheck` all pass on the re-cut,
so the re-cut is not a paper fix.

## Named, not edited

The issue's explicit instruction, and four places carry sentences this branch
makes false. None is edited here; each is a shared file another agent PR may be
open against, and the gate arm is the deliverable.

- [`../../ec/annotations/xdata-06c2-06db-timers.md:937-938`](../../ec/annotations/xdata-06c2-06db-timers.md)
  — "neither is green today: both exit 1 on `main`". Both exit 0. Its
  `:965-966` "red on `main` at the time of writing" is the same claim again.
- [`xdata-cluster-names-guard-off-recipe.md:289-292`](xdata-cluster-names-guard-off-recipe.md)
  — "the cheap tier not running the tool's `--check`/`--self-test`, which are
  red on `main`". The cheap tier runs both, and they are green.
- [`0751-grader-self-test-gate.md:344-350`](0751-grader-self-test-gate.md) and
  its merge note at `:181-183` — both say a branch editing
  `.github/scripts/agent-gates.sh` fails at the end of a PR for want of a
  `workflow` scope. **They are wrong about the scope and this branch is the
  counterexample**: `.github/scripts/` is pushable, only `.github/workflows/` and
  `.github/actions/` are not, which
  [`../../ec/annotations/xdata-register-map.md:2583-2584`](../../ec/annotations/xdata-register-map.md)
  already recorded. That file's own hedge — "If `.github/scripts/` turns out to be
  pushable, the patch applies unchanged and nothing is lost" — is now answered: it
  is pushable, and a branch editing it landed this arm.
- The **same claim in the header of the patch this branch re-cuts**,
  `../ci/agent-gates-disasm8051-self-test.patch:2-5`. Left as it is, per the
  instruction above, and recorded here instead. It is not a reason the patch
  should not be landed; it is a reason a *re-copy* of the template reverts this
  arm, which is the one consequence of landing it and the reason the change also
  wants to go to `ElDavoo/agent-pipeline` upstream. That submission is a
  `gh pr create` against another repository's slug, which this pipeline never does
  unattended, so it is left to a human with this file and the re-cut patch.
- `../findings.md` — **no pointer added**. This is a gate-wiring change with no
  new register, address or census fact; the long shared file is the worst
  merge-conflict surface in the repository, and this file is the record.
- [`../../ec/tools/xdata_register_map.py`](../../ec/tools/xdata_register_map.py) —
  **not edited at all.** The assertions are unchanged; what changed is what runs
  them. `ec/decompiled/**`, `ec/annotations/ghidra-functions.csv`,
  `xdata-clusters.csv` and `xdata-registers.csv` are all byte-identical, which is
  precisely what the now-also-wired `--check` continues to prove on every commit.

## What this does not establish

Nothing about the firmware, and nothing about the laptop. A register write being
accepted is not evidence the EC acts on it, and none of the 101 assertions is a
behavioural claim: they are counts, names, bucket directions and refusals,
checked against committed text.

Nor does it settle the questions the census leaves open. §4.3's invariant is an
arithmetic necessity over the decompiler's spelling, not a reading of the code;
`XDATA_0860` and the other `present-untested` rows are untouched; the two suites
that read these CSVs for their own reasons —
`ec/tools/test_xdata_cluster_names.py` and `ec/tools/test_check_site_census.py` —
are not fixed here, and
[`runner-red-suite-set.md`](runner-red-suite-set.md) is the file that tracks them.
The export-ownership oracle being green says the pass loses no address; it does
not say the 296 it moves should move.
