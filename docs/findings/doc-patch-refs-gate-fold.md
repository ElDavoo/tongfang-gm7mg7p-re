# `check_doc_patch_refs.py`'s `gate` line folds into the capture-claims patch, and the anchor tables the fold rests on are stale (issue #956)

**The decision was already made and recorded; this is the fold landing and the
measurement behind it being re-derived.** `docs/findings/history-checkouts-gate-wiring.md`
decided in #1033 that a `check_doc_patch_refs()` function and its `gate` line
would ride inside `docs/ci/agent-gates-capture-claims.patch` rather than in a
patch of its own, because the `gate` list admits no insertion point that
composes. #956 asked for a `docs/ci/agent-gates-doc-patch-refs.patch` anyway;
that filename is declined here, the content is folded into the existing patch,
and the decline is recorded beside what was prepared per `CLAUDE.md` §4a-4d —
which is what makes it a key in `tools/check_doc_patch_refs.py`'s `HISTORICAL`
set.

**The second thing here is a finding of its own, and it is the reason this
write-up exists rather than a one-line pointer from the patch's header:** the
anchor tables that decision rests on have drifted, and one of the gaps they call
free is no longer free. A reader who takes the recorded table for the current
one is sent to an anchor that reads available and is not.

**Nothing here is a hardware, firmware or Windows claim.** No image is opened,
no register is read back, no capture is taken. Every line number below is over
`.github/scripts/agent-gates.sh` as committed, and each table names the
command that prints it.

## The measurement

The recipe is `docs/findings/history-checkouts-gate-wiring.md`'s, run verbatim
against the committed `.github/scripts/agent-gates.sh` at the tree this branch
is on. It is repeated here whole, because a table the next reader cannot
re-derive is the defect this page is about.

```sh
root=$(git rev-parse --show-toplevel)   # patch paths resolve from the repository, not from $tmp
seed() { rm -rf "$1"; mkdir -p "$1/.github/scripts"
  git -C "$1" init -q . && cp "$root/.github/scripts/agent-gates.sh" "$1/.github/scripts/"
  git -C "$1" add -A
  git -C "$1" -c user.email=a@b -c user.name=c commit -qm base; }
tmp=$(mktemp -d); seed "$tmp"
# insert the new line at the anchor (P3 here: before `gate 'ghidra tooling'`), then
# stage it -- an unstaged edit is not in the index, so `diff --cached` would cut
# an empty candidate -- and cut the way a re-cut is cut:
sed -i "/^gate 'ghidra tooling'/i gate 'history checkouts'  check_history_checkouts" "$tmp/.github/scripts/agent-gates.sh"
git -C "$tmp" add -A && git -C "$tmp" diff --cached > "$tmp/cand.patch"
# and for every committed patch P, in a *fresh* copy of the seeded tree, both orders:
for P in "$root"/docs/ci/agent-gates-*.patch; do
  for order in cand-first P-first; do
    t=$(mktemp -d); seed "$t"
    if [ "$order" = cand-first ]; then set -- "$tmp/cand.patch" "$P"; else set -- "$P" "$tmp/cand.patch"; fi
    git -C "$t" apply "$1" 2>/dev/null && git -C "$t" apply --check "$2" 2>/dev/null \
      && echo "$(basename "$P") $order: composes" \
      || echo "$(basename "$P") $order: does not compose"
    rm -rf "$t"
  done
done
echo "candidate cut: $(wc -c < "$tmp/cand.patch") bytes"; rm -rf "$tmp"
```

Three things in there are load-bearing, and `history-checkouts-gate-wiring.md`
gives the reason for each: the edited file must be **staged** before
`diff --cached` (unstaged, the candidate cuts zero bytes and a harness that
reports per-pair rather than aborting turns a *free* anchor into one that looks
held by every patch); `git -C` **changes the base for relative paths**, so the
committed patches are addressed from `$root`; and each order needs its **own
seeded tree**, or the second order is the first one twice. The `gate` candidate
is one line and the function candidate is a comment, a three-line function and
its closing brace; the shapes differ, so the two tables below are not
interchangeable and each was cut in its own shape.

### The `gate` list: every insertion point, none free

A seven-line list admits eight insertion points. Each is named by the line the
new line would be inserted before, so a reader can find it with
`grep -n "^gate '" .github/scripts/agent-gates.sh`.

| anchor | the new line lands before | applies alone | fails to compose with |
|---|---|---|---|
| P0 | `:327`, `gate 'registers.yaml'` | yes | pin-table-rows |
| P1 | `:328` | yes | pin-table-rows, capture-claims |
| P2 | `:329` | yes | pin-table-rows, capture-claims |
| P3 | `:330`, between `register counts` and `ghidra tooling` | yes | capture-claims |
| P4 | `:331` | yes | capture-claims |
| P5 | `:332` | yes | capture-claims, testdata-row-claims |
| P6 | `:333` | yes | testdata-row-claims |
| P7 | `:334`, `gate 'doc links'` | yes | testdata-row-claims |

**Every one of the eight applies cleanly alone, and not one of them composes.**
That combination is the whole trap: a new patch is green on the one check a
person runs before trusting it, and fails only at the moment a sibling lands,
with a context-mismatch message that reads like staleness rather than a
composition problem. It is the failure `tools/test_agent_gates_patches.py`
exists to catch.

The recorded table says the same thing about the same set — this is not a
change of conclusion, it is a change of line numbers and of one G row's
composition result. P0, P1, P2, P4 and P5 are worth reading anyway: they are
one or two lines away from a held anchor, and a hunk's three-line context
window reaches over them. **"Re-anchor somewhere else in the list" is not a
workaround at any of the eight**, which is the sentence a re-cutter needs.

### The function definitions: seven gaps, two free

| gap | the function would start at | applies alone | fails to compose with |
|---|---|---|---|
| G0 | `:68`, after `check_registers_yaml()` | yes | — |
| G1 | `:79`, after `check_scan_refs_smoke_test()` | yes | testdata-row-claims |
| G2 | `:87`, after `check_register_counts()` | yes | capture-claims |
| G3 | `:96`, after `check_python_syntax()` | yes | bank-map-score |
| G4 | `:305`, after `check_ghidra_tooling()` | yes | — |
| G5 | `:313`, after `check_shellcheck()` | yes | pin-table-rows |
| G6 | `:327`, after `check_doc_links()` | yes | pin-table-rows |

G6 is the interesting row and it is unchanged: it is the last gap before the
`gate` list, and what holds it is pin-table-rows' **`gate`** hunk, not a function
hunk — its three lines of trailing context are the head of the list. A function
and a `gate` line are not independent at that end of the file, which is the
half of the pair a "put the function somewhere free" plan does not see.

**The function side is not saturated, and the two free gaps are not the two the
recorded table names.** G0 and G4 are free; the recorded table's third free gap,
G3, is now held by `docs/ci/agent-gates-bank-map-score.patch`, whose first hunk
is the blank line between `check_python_syntax()` and `check_ghidra_tooling()`.
That is the whole cost: the check's function half *would* have had a home of its
own, and its `gate` half would not, so the pair rides in the patch that already
holds an anchor of each.

## The drift, which is the finding

The recorded tables are `d3304785`'s, and that commit still resolves. Every
number above G3 in that table has since moved by **+30 lines**, and G0 through
G3 have not moved at all:

| | recorded at `d3304785` | measured on this tree |
|---|---|---|
| gate list | `:297-303` | `:327-333` |
| G0–G3 | `:68`, `:79`, `:87`, `:96` | unchanged |
| G4, G5, G6 | `:275`, `:283`, `:297` | `:305`, `:313`, `:327` |

The growth is inside `check_ghidra_tooling()`, which absorbed the
`check_gate_arm_coverage.py` call and comment block, then the
`check_status_vocabulary.py` tool-list entry and its `case` arm —
`git diff d3304785..HEAD -- .github/scripts/agent-gates.sh` is the command that
shows it, and it reports a clean `30 0`: every added line lands above the old
`:303` and below the old `:96`.

Note what is *not* in that script and so cannot be the cause:
`agent-gates-bank-map-score.patch` is **prepared, not landed**, so
`check_bank_map()` is not in the committed file at all. That is the same
prepared-not-landed state this write-up is about, and it is why a plausible
-sounding attribution for the drift is wrong.

**Non-uniform drift is the part worth writing down.** A single offset would be
a small annoyance; +30 for everything below one point and zero above it means
an offset applied to the recorded table produces *wrong* numbers for half of it
and right ones for the other half, with nothing to tell a reader which is which.
That is the same failure mode the issue that filed this found in
`docs/findings/prepared-gate-patches.md`'s collision table — a hunk offset
presented as a current line number — reproduced one level up. The generalisation
is the useful part: **a line number in a document is only true of a commit**, so
the honest citation is `file:line at <sha>`, and the honest table says which
commit it was measured on in the row rather than in a paragraph a reader may not
reach.

### Corrections to the recorded table and to the issue

Recorded beside what was measured, per `CLAUDE.md` §4a-4d, because a correction
that leaves the wrong figure invisible is not a correction:

- **The gate list is at `:327-333`, not `:297-303`.** Both the recorded page
  and issue #956's own table give `:297-303`; both are `d3304785`'s.
- **The function-gap drift is +30 for G4–G6 and zero for G0–G3.** The issue
  recorded "+15 for the last three G rows against +16 for the P rows", which
  cannot both be true of one contiguous growth — and neither figure is this
  tree's.
- **G3 is no longer free.** `agent-gates-bank-map-score.patch` holds it. This is
  a change in the *answer*, not only in the numbering, and it is the one that
  matters for anyone planning a fold.
- **The `seventh` is `d3304785`'s figure, and it is a count of a directory.**
  `PATCHES` in `tools/test_agent_gates_patches.py` is the index of what is
  prepared; read it rather than a number, which moves on every landing. That is
  also why this correction names no replacement figure — a larger count would
  be stale the same way and for the same reason.

## The fold, and what it costs

**`check_doc_patch_refs()` and its `gate` line go into
`docs/ci/agent-gates-capture-claims.patch`** — the function fourth in hunk 1,
after `check_history_checkouts()` and before `check_sweep_summary()`, and the
`gate` line last in hunk 2, below `gate 'sweep summary'`. Two halves at anchors
the patch already holds, so the pair composes by construction rather than by
luck. The patch's header carries the new check's reasoning and its own note that
the tables it cites are stale.

The costs, recorded because the next fold hits the same steps:

- **`FoldTests.REQUIRED` grows a line per fold.** A re-cut that keeps some
  functions and drops others still applies, still composes, still passes
  `bash -n` and `shellcheck`, and quietly loses a gate. This was **measured,
  not assumed**: a re-cut built by landing the patch, deleting the new function
  and its `gate` line from the result and re-cutting with `diff` — so it is a
  *valid* patch, not a broken one — applies cleanly, composes, parses and
  shellchecks, and turns **exactly the two new `FoldTests` subtests red and
  nothing else in the suite**. That is the case working; a mutation that broke
  the patch would have proved only that the suite notices a broken patch.
- **The declined filename becomes a key in `HISTORICAL`.** A fold obliges the
  write-up to name what was asked for beside what was prepared, and
  `check_doc_patch_refs.py`'s enumeration is keyed on the name — so the citation
  this page is required to make is what adds the key, not a separate edit.
- **The patch's name is now less accurate, not more.** It names none of the
  checks it carries, and each fold makes that worse.

### Rejected: a standalone patch

Declined for the reason the tables above measure, and for the one
`history-checkouts-gate-wiring.md` records from the other direction: a patch
file in `docs/ci/` that is not in `test_agent_gates_patches.py`'s `PATCHES` is
worse than no patch, because the glob would not pick it up, so nothing would
check that it still applies, and its `gate` line would fail against a sibling
with a context error that reads like staleness. Its own suite
(`tools/test_doc_patch_refs.py`) needs no such wiring — `tools/run-tests.sh`
discovers every `test_*.py` in the repository — which is worth saying, because
it is the question the issue's step 3 half-answers.

### Rejected: renaming the patch file

Rejected for the third time (#745, #1033, and again here), with the same cost:
the filename is cited across this repository's long shared markdown files as the
canonical account of the prepared-not-landed shape, and renaming it to name its
contents churns exactly the files `CLAUDE.md` says not to churn, to fix a name
that is not load-bearing. The pair to re-derive the current figure is
`grep -rc 'agent-gates-capture-claims\.patch' --include='*.md' .`, and
`check_doc_patch_refs.py` prints its own on every run. #1005 owns the prepared
patches' `index` lines and none of the others.

## What is not claimed

- **That any commit runs this check.** The patch is prepared, not landed.
  `.github/scripts/agent-gates.sh` is copied from the agent-pipeline template
  and the pipeline's push token has no `workflow` scope, so a branch editing it
  fails at the *end* of a PR rather than the start. **Until a human runs
  `git apply docs/ci/agent-gates-capture-claims.patch`, no commit runs
  `check_doc_patch_refs.py`**, and the next fold or rename repointed by hand
  arrives the way #745's did.
- **That the anchors above stay where they are.** The gate script is
  template-copied, and a re-copy may change it. Re-run the recipe.
- **That a patch `git apply --check` accepts is applicable in context.** That is
  the whole reason the composition results are here: every one of the eight
  `gate` candidates passes `--check` alone.
- **Anything about the laptop.** No EC, no BIOS, no capture, no register, no
  Windows box. Nothing here needs `needs-hardware-test` and no live run is
  implied.