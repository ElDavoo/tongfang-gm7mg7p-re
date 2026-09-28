# Both clone depths run: `--verify-provenance` measured rather than asserted (issue #421)

**Issue #421, filed automatically from #411. Written 2026-09-28.** #421 asked for
five corrections to the checkout-depth claim, and the tree has carried all of
them for two days by way of #1009 and the four issues that followed it. What was
left undone was the one clause of its own "done when" that is behavioural: *"a
full-clone checkout and a `--depth 1` checkout both behave correctly."* Nothing
in the tree ran the mode in either depth. This page records what the two clones
do when the mode is run in them, and the suite that now runs them.

## What #421 asked for, and where each of the five sites is

| #421's site | where it is now | state |
|---|---|---|
| `docs/agent-pipeline.md` item 3 | `docs/agent-pipeline.md:99-160` | heading names jobs rather than the file; the stale `ci.yml:34`/`:64` citations repointed to `ci.yml`'s `gates` job at `:39` and its `workflows` job at `:66-69`, and `agent-review.yml:64` to its `review` job at `:85`, all three verified against the committed workflows; the 2026-09-23 wording kept visible beside the 2026-09-24 decision block at `docs/agent-pipeline.md:149-160` |
| `docs/findings.md` §14f | `docs/findings.md:3531-3540` | corrected, with a *"(Corrected 2026-09-26, issue #1009 …)"* note quoting the old sentence, which is the `§4a-4d` pattern the issue asked for |
| `ec/tools/verify_reassembly.py`, the comment above `HISTORY_REQUIREMENT` | `ec/tools/verify_reassembly.py:1313-1320` | names the four `fetch-depth: 0` jobs and `ci.yml`'s `workflows` job as the default-depth one that never reaches the mode |
| `ec/tools/verify_reassembly.py`, the `HISTORY_REQUIREMENT` string | `ec/tools/verify_reassembly.py:1321-1327`, printed at `:1482` and `:1492` | reads *"… which is what ci.yml's `workflows` job uses, though that job runs no history reader"*; the `git fetch --unshallow` advice the issue asked to keep is still there |
| `ec/ghidra/README.md` | `ec/ghidra/README.md:806-822` | says **"which is why it *is* part of the per-commit gate"**, with the old sentence quoted beside it |

The site-by-site derivation, and the checker that re-derives the jobs from the
committed workflows, are in
[`history-checkout-claims.md`](history-checkout-claims.md). #421 is **not a
re-file of any of #1009, #1030, #1031, #1032, #1033 or #1034**; it is the
behavioural half those left.

## The gap: a fragment is not a run

`HISTORY_REQUIREMENT` was held as a **prose fragment** in
`ec/tools/history_checkout_sites.py` — a substring of the corrected sentence, so
that rewrapping the comment around it is not a change to its row. That is the
right way to hold a sentence in a checker, and it is not a way to know what the
mode prints. A fragment proves the words are still in the source. It cannot fail
if the failure path stops printing the block, and it never runs the mode.

Grepping the suites for an invocation found one hit, and it was a string inside
a synthetic workflow fixture at `ec/tools/test_check_history_checkouts.py:438`,
present so the checker could decide whether a job "runs a history reader" — not
a call. #421 names the printed string as the half that "matters most", because
that string is what reaches a human on a red `gates` run.

## What each depth actually prints

Both runs are the command `.github/scripts/agent-gates.sh:160-163` runs, and
both are pastes of what the tool printed, not of what it is expected to print.

**A full clone** — `git clone` against the local path, so the objects are
hardlinked:

```console
  revisions: listings written 8c7985e..08b72e2, migration 08b72e2..a56b3bb
  listing text: 0 of them changed over 08b72e2..a56b3bb; the same pathspec returns 2705 file(s)
  over 8c7985e..08b72e2, the window that last wrote them, so the first number is a measurement
  report: 2705 of 2705 row(s) identical once listing_digest is dropped (present in the
  base: no; in the migration: yes)
  the window touched 1 path(s) under ec/decompiled:
    ec/decompiled/bank0/0EA2.c
  PASS  the migration changed the column and nothing beneath it, and no listing text
  moved while it did.
```

Exit 0, and the `PASS` verdict is the one `docs/findings.md` §14f records. **The
figures are not asserted anywhere.** `2,705` is a number about the corpus, not a
verdict on the mode, and a figure written into a test is a value every commit
that moves the corpus has to edit — the trade CLAUDE.md names.

**A `--depth 1` clone** — `git init`, `git fetch --depth 1 file://<repo> HEAD`,
`git checkout FETCH_HEAD`:

```console
  FAIL cannot resolve the base revision '08b72e2' in this clone.
  This mode answers from the repository's history, so it needs a full
  clone: `git clone` without --depth, or `git fetch --unshallow` in one
  that is shallow. A default-depth checkout -- actions/checkout's default,
  which is what ci.yml's `workflows` job uses, though that job runs no
  history reader -- has neither revision, and a mode that carried on
  anyway would be auditing whatever happened to be checked out.
```

Exit 1, the unresolvable revision named, and `HISTORY_REQUIREMENT` printed
whole. The `file://` is there because git refuses `--depth` against a plain
local path, and the `init`-then-`fetch --depth 1` idiom is the one this
repository already documents for a throwaway tree at
`linux/patches/gm7mg7p-power-profile/README.md:38`.

## The suite

`ec/tools/test_verify_provenance_clone_depth.py`, four cases, and it is in no
gate: a suite needs no gate wiring, because `tools/run-tests.sh` discovers every
`test_*.py` by `find`. What it holds, in order:

- **The control.** Each clone is read back with `git rev-parse
  --is-shallow-repository` rather than assumed from the command that made it.
  Without it a `git fetch` that quietly fetched the whole history would leave a
  directory that resolves everything, and the depth-1 case would pass over a tree
  that is not the one it names. It is the same discipline
  `test_check_history_checkouts.py` uses by pasting the stale sentences
  verbatim rather than paraphrasing them.
- **The full clone answers**, exit 0, `PASS` present.
- **The depth-1 clone fails with the requirement**, exit 1, the revision named,
  and `HISTORY_REQUIREMENT` compared as the whole constant read out of *that*
  clone rather than as a substring of it — so the case is "the failure path
  prints the requirement" and not "prints something about clone depth".
- **The regression #421 filed**, on that same printed block.

**Cost, measured rather than assumed:** 7.8 s for all four cases on this runner —
about 1.4 s for the clone and 0.1 s for the mode in the full one, and about
5.7 s to fetch and check out the depth-1 tree. `docs/agent-pipeline.md:157`
records the mode itself at 1.7 s. Each clone is a ~500 MB checkout, so the two
are built once per run and shared, and both live under `tempfile` and never in
the working tree: `run-tests.sh` prunes `.git/`, `.claude/` and `vendor/` when
it counts, and `check_testdata_index.py` and `census_test_line_pins.py` walk
the tree.

## The floor the `ci.yml` assertion is

The fourth case asserts that the printed requirement **does not** carry the
pre-#421 wording —

```text
which is what ci.yml uses
```

— and **does** carry ``ci.yml's `workflows` job``. Both halves, because the
negative alone is a floor: a rewrite that dropped the `ci.yml` claim entirely
would pass it and leave the reader with no idea which checkout to look at.

**What it holds is the claim's shape, not its content.** Job ids here are
ordinary English words, so a sentence naming the *wrong* job passes this case
too. That is the same limit `history-checkout-claims.md` states about the
quotation rule this case's shape is borrowed from, and it is why the corrected
prose is held separately, and by value, in `history_checkout_sites.py`.

## The re-copy obligation, and two adjacent issues

#421's last paragraph notes the coupling: `agent-gates.sh` and `ci.yml`'s
`gates` job are both template-copied, so **the gate clause and the
`fetch-depth: 0` that job depends on have to be re-applied together**. That
obligation is recorded at `docs/agent-pipeline.md:214-232`, which names
`ci.yml:39` and `ci.yml:33-34` as landing together; it is pointed at rather than
restated here. The suite in this PR is *not* that clause — it does not make the
invariant a gate, and nothing here re-copies a template file.

#421 places this next to two open issues, and **this is adjacent to both rather
than a re-file of either**: [#331](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/331)
(the unlanded prepared arms) and
[#391](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/391) (the
`docs/agent-pipeline.md:226` list).

## What is not claimed

- **That `--verify-provenance` has ever passed in CI.** These cases run it
  locally, on a clone this suite builds. `history-checkout-claims.md` already
  disclaims the CI reading and this page does not override it: what `ci.yml`'s
  `gates` job asks for is a fact about the workflow, not about a runner.
- **That the mode is correct.** Exit 0 on the committed tree is what §14f
  recorded by hand, re-measured. The mode's own closing paragraph says what its
  `PASS` does not establish — the digests attest to the listings the last full
  `--report` measured, not to those listings being right, and the re-encode
  (§14e) is still the open part.
- **That the mode is red on no tree.** Only this tree, at these two depths, was
  run. A window that moved a listing, or a rewritten `HISTORY_REQUIREMENT`,
  would change what the cases see.
- **That `docs/findings.md` needs a pointer here.** It is frozen, and
  `check_findings_frozen.py` fails an added section. The generated
  `docs/findings/INDEX.md` entry is the repository's own pointer mechanism, and
  that is what #421's "add a short pointer from `docs/findings.md`" is satisfied
  by — a deliberate narrowing of the issue's instruction, taken because
  CLAUDE.md forbids the alternative.
