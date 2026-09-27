# The checkout-depth check is prepared for the cheap gate, in a patch that had to fold (issue #1033)

**Written 2026-09-26, against `d3304785`.** Every `.github/scripts/agent-gates.sh`
line below is that commit's and still reads, that file being unmoved since it.
The two `ec/tools/check_history_checkouts.py` pins are the exception: each was
first read on a later tree, so each carries the commit it was true of beside
the reading this branch lands on. Issue #1033 asked for a
`docs/ci/agent-gates-check-history-checkouts.patch` "following the shape of
`docs/ci/agent-gates-pin-table-rows.patch`". The shape is available for the
**function** and closed for the **`gate` line**, so the check and its gate line
went into `docs/ci/agent-gates-capture-claims.patch`, which already holds one of
each. This page is the measurement behind that, the two alternatives left out
and why, and the corrections to the issue's own line references. It is written
as a file rather than a paragraph in `docs/agent-pipeline.md` because #954,
#877, #921 and #777 each want the same table and should inherit it instead of
re-deriving the saturation.

**Nothing here is a hardware, firmware or Windows claim.** No image is opened,
no register is read back, no capture is taken, and no EC, BIOS or vendor
binary is touched anywhere below. Every figure is a count of lines and patches
over text committed in this repository, and the one thing this page cannot
claim is in its last section, where it says so.

## The premise, re-derived rather than quoted

`docs/findings/history-checkout-claims.md` records that the checker and its
suite are *"**Not in any gate** … It runs under `tools/run-tests.sh`"*, and the
issue's own reading of that is right on both counts. Checked on this tree:

- `.github/scripts/agent-gates.sh:297-303` is **seven `gate` lines**, and they
  are `registers.yaml`, `scan_refs.py smoke test`, `register counts`,
  `ghidra tooling`, `python syntax`, `shellcheck` and `doc links`. **Not one is
  a `test_*.py` suite and not one is `tools/run-tests.sh`**, and neither string
  appears anywhere else in the file either — the sole `test_*.py` in it is at
  `:257`, inside a comment explaining why a mode is refused, not a call.
- `tools/run-tests.sh` is named in the pipeline in **exactly one place**:
  `agent-conflicts.yml:249`, inside the `resolve` job's prompt, two lines below
  the `.github/scripts/agent-gates.sh` it is told to run. It is reached only
  when a merge leaves conflict markers to fix, and it is reached *as prose to
  an agent*, not as a `run:` step — which is also why
  `check_history_checkouts.py` does not count that job as a history reader
  (its own *"not found by this method"* list, §`What it does not find` of
  `history-checkout-claims.md`).

So the accident the tool exists to catch is caught in the per-commit gate only
by a *different* tool's failure message, and the message that names it is
reached by a local `run-tests.sh`, a conflicts run, or a human reading the
output. That is a real gap and it is what this page prepares a patch for. It is
not a claim that the gap has ever cost anything.

## The anchor table

**`docs/findings/prepared-gate-patches.md`'s collision table is not edited
here**; this is its extension, and the file it extends says where a new region
is held. A seven-line `gate` list has **eight** insertion points; the seven
`check_*()` definitions have **seven** gaps between them. Each candidate is a
one-line `gate` patch or a one-function patch, cut the way `git diff` cuts a
real one, and each is tried alone and in **both orders** against all six
committed patches.

The recipe, so a reader re-derives rather than trusts. It is run under
`bash`, and it was run verbatim against this tree on 2026-09-26, at the P3
anchor the fold uses: it cut a **553-byte** candidate, reported
`agent-gates-capture-claims.patch` as the one patch that does not compose **in
both orders**, and `composes` for the other five in both — which is the P3 row
of the table below, produced by the block rather than asserted beside it.

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

Three things in there are load-bearing, and each was wrong in the first draft
of this recipe — so they are spelled out rather than left for the next reader
to rediscover. The **edited file must be staged** before `diff --cached`:
unstaged, the candidate cuts 0 bytes, and a harness that reports a
non-composition per pair rather than aborting turns a *free* anchor into one
that looks held by all six patches — the opposite of what this table says.
**`-C` changes the base for relative paths**, so `git -C "$tmp" apply
docs/ci/P.patch` looks for `docs/ci/` *inside the scratch tree*, which holds
only `.github/scripts/`, and dies with `can't open patch`; the committed
patches are addressed from `$root` instead. And each order needs its **own
seeded tree**, so `seed` is re-run per order rather than reusing the one the
candidate was cut from, or the second order is really the first one twice.

### The `gate` list: eight anchors, none free

| anchor | the new line lands at | applies alone | fails to compose with |
|---|---|---|---|
| P0 | `:297`, before `gate 'registers.yaml'` | yes | pin-table-rows |
| P1 | `:298` | yes | pin-table-rows, capture-claims |
| P2 | `:299` | yes | pin-table-rows, capture-claims |
| P3 | `:300`, between `register counts` and `ghidra tooling` | yes | capture-claims |
| P4 | `:301` | yes | capture-claims |
| P5 | `:302` | yes | capture-claims, testdata-row-claims |
| P6 | `:303` | yes | testdata-row-claims |
| P7 | `:304`, after `gate 'doc links'` | yes | testdata-row-claims |

**Every one of the eight applies cleanly alone, and not one of them composes.**
That combination is the whole trap: a seventh patch would be green in
`git apply --check`, would be green on the one test a person runs before
trusting it, and would fail only at the moment a sibling landed — with a
context-mismatch message that reads like a stale patch rather than a
composition problem. It is the failure
`tools/test_agent_gates_patches.py` exists to catch, and the two patches that
demonstrate it are the reason `agent-gates-testdata-index.patch` no longer
exists.

P0, P3 and P7 are held because a committed patch inserts at exactly those
anchors. **P1, P2 and P4 are not free either**, which is the part worth
recording: they are two and one lines away from a held anchor, and a hunk's
three-line context window reaches over them. P6 and P7 are the only two whose
sole obstruction is the tail patch. "Re-anchor somewhere else in the list" is
therefore not a workaround at any of the eight, and the header says so.

### The function definitions: seven gaps, three free

| gap | the function would start at | applies alone | fails to compose with |
|---|---|---|---|
| G0 | `:68`, after `check_registers_yaml()` | yes | — |
| G1 | `:79`, after `check_scan_refs_smoke_test()` | yes | testdata-row-claims |
| G2 | `:87`, after `check_register_counts()` | yes | capture-claims |
| G3 | `:96`, after `check_python_syntax()` | yes | — |
| G4 | `:275`, after `check_ghidra_tooling()` | yes | — |
| G5 | `:283`, after `check_shellcheck()` | yes | pin-table-rows |
| G6 | `:297`, after `check_doc_links()` | yes | pin-table-rows |

G6 is the interesting row: it is the last gap before the `gate` list, and what
holds it is pin-table-rows' **`gate` hunk**, not a function hunk — its three
lines of trailing context are the head of the list, which is exactly P0's
region. A function and a `gate` line are not independent after all, at that
end of the file. Three of the seven are free (G0, G3, G4), so the function half
of this change would have had a home of its own; the `gate` half would not.

## The decision, and the two alternatives left out

**The check and its `gate` line go into `docs/ci/agent-gates-capture-claims.patch`**
— hunk 1 gains a third function, hunk 2 a third `gate` line at the P3 anchor
that patch already holds. This is #745's fold a second time, with the same
recorded reason, and `tools/test_agent_gates_patches.py`'s `FoldTests.REQUIRED`
grows a line per fold because a re-cut that keeps two functions and drops the
third applies cleanly, composes, passes `bash -n` and `shellcheck`, and loses a
gate in silence. That mutation was run against this change: the pre-fold version
of the patch is a *valid* patch (`git apply --check` exits 0) and turns the
suite red on exactly the two new lines.

The trigger the plan set for this decision is met and recorded: had a
standalone seventh file passed every ordered pair, it would have been created
instead. It does not, and the table above is why.

**The fold has one consequence outside `docs/ci/`, recorded here because the
next issue to fold a fourth check into this patch will hit the same step.** The
plan predicted that under the fold *"nothing new is cited"* — the declined
filename would appear nowhere, and `tools/check_doc_patch_refs.py`'s
`HISTORICAL` set would stay at two keys. It did not hold, for exactly the
opposite reason: the fold obliges the write-up to name what was asked for beside
what was prepared, `CLAUDE.md` §4a-4d, so `docs/ci/agent-gates-check-history-checkouts.patch`
is cited here at the top — genuinely absent from `docs/ci/`, genuinely cited, and
therefore a **third** `HISTORICAL` key. That set is an enumeration and not a
per-reference opt-out, so a sibling cannot just decline the citation; it adds a
key, and `tools/check_doc_patch_refs.py`'s docstring is where the reason lives.

**Left out: a seventh standalone patch.** Declined, and this is
`docs/agent-pipeline.md` item 13's decision reached from the other direction —
it declined to prepare `check_doc_patch_refs.py`'s patch because a seventh
`gate` line would need an anchor already held. A patch file in `docs/ci/` that
is **not** in `test_agent_gates_patches.py`'s `PATCHES` list is worse than no
patch: the glob would not pick it up, so nothing would check that it still
applies, and its `gate` line would fail against a sibling with a context error
that looks like staleness.

**Left out: renaming the patch to something naming three checks.** Rejected with
its cost, which is the same one #745 gave for two: at `d3304785` the filename is
cited **30 times across 13 markdown files** as this repository's canonical
account of the prepared-not-landed shape, most of them long shared files other
agent PRs are open against, and #1005 owns the prepared patches' index lines.
A rename would be more honest as a name and would touch every one of those for
no change in the file's role.

#1005 was the plan's first check and it was done: read out of the tracker on
2026-09-26 during review of this change, it is **open** and unlanded, so no
alternative index-line convention exists and the shape derived here stands.
What that check turned up instead is that **this change had re-cut the very
line #1005 is about, silently**. The fold moved
`docs/ci/agent-gates-capture-claims.patch`'s hunk header from
`index 125d6478..30df515a` to `index de5db1f..62dd622`, and
`git hash-object .github/scripts/agent-gates.sh` is
`de5db1fa8d648f517ee26776e6f6fc7b2d4d1deb` — the new old-side **is** the
committed blob, which is what #1005's table column asks. So the re-cut
**closes the `agent-gates-capture-claims.patch` row** of that table, one of the
three that named an old-side the repository does not contain. The other two
(`agent-gates-0751-self-test.patch` and `agent-gates-gap-text-check.patch`,
both still `125d647`) and the unindexed `agent-gates-testdata-row-claims.patch`
are #1005's to fix; this change does not touch them.

**What is still not established** is the half #1005 actually raises. The
new-side `62dd622` names the file *as it will be* after a human lands the
patch; it is not a blob in this repository, so it is verifiable only by
applying the patch and re-hashing. That is the reproducibility point #1005's
title turns on, and this change does not settle it — it is a one-line
`git apply` away, recorded here so the next reader does not have to re-derive
that it was checked at all.

## What was measured, and what a red run would mean

- `python3 ec/tools/check_history_checkouts.py` **exits 0 on the committed
  tree** — the "green as prepared" precondition #745 called the cheapest way
  to avoid landing a red gate. Re-measure it at the tip you land on.
- The check measures **0.18 s** (0.17–0.18 s over five runs on 2026-09-26)
  against a cheap tier `docs/agent-pipeline.md` records at **5.9 s**. Those are
  two different machines and the ratio, not either absolute number, is the
  point; the `tools/run-tests.sh` bullet of that file is where the caveat is
  written out, and items 6 and 12 use it the same way.
- The gate line keys on the tool's **own exit code**, so no test-suite
  machinery is needed for the patch to work. The landed function's comment says
  what a red run means, in the template's terms: either a checkout is shallower
  than the job using it needs — `depth_problems()` at
  `ec/tools/check_history_checkouts.py:468`, whose message ends *"the mode will
  report a history requirement rather than an answer"* — or a sentence in the
  two history-reading tools asserts a workflow's checkout depth without naming
  the job, which is #1009's own correction rule turned back on. The tool
  reports both at a `file:line`, so the reader is told which. **`:468` is this
  branch's; `:288` is `fe92940a`'s and `:247` is `d3304785`'s.** The first draft
  of this bullet gave `:288` bare, which resolves on `fe92940a` and on no other
  tree a reader of this page would be holding — the header names `d3304785` as
  the baseline. An unattributed `file:line` is what
  `test-line-pin-census.md` exists about, so both earlier readings stay written
  here beside the current one rather than dropped, per `../findings.md` §4a-4d.
- The red path is **cited, not re-run**: `ec/tools/test_check_history_checkouts.py`'s
  `test_a_gate_job_on_a_shallow_checkout_is_a_failure` already deletes
  `fetch-depth: 0` from a synthetic `gates` job on a scratch tree and watches
  the checker fail on it. No case was added to duplicate it.

## Two corrections to the issue's references

Both were checked against the files, and both belong in a diff rather than
being quietly dropped:

- The issue puts `main()` at `:1533-1555`. It is at **`:817-853`**
  (`ec/tools/check_history_checkouts.py`, 857 lines). The shape of the claim is
  right — `main()` returns 1 on any problem from `report()` — but a reader sent
  to `:1533` finds nothing. This section first answered **`:607-629`** in 633
  lines, which is `fe92940a`'s reading and not this branch's; `d3304785`, the
  commit the header above names as the baseline, reads **`:509-531`** in 535, so
  the correction was stale against the tree it claims to be written on as well
  as against the tip. Both earlier readings are left here beside the merged one
  rather than dropped, per `../findings.md` §4a-4d — and a correction that
  sends a reader to a line holding nothing is the same defect as the one it
  was correcting.
- The issue says the patch's comment should carry *"the same `fetch-depth: 0`
  note `ci.yml:37-38` carries"*. **`ci.yml:39` is the `fetch-depth: 0`**, and
  the note above it is at **`:33-34`**. The landed comment cites both, because
  a re-copy lands the missing depth and its comment together and a reader
  chasing a re-copy needs the pair.

## What is not claimed

- **That this invariant has ever been exercised in CI. It has not.** The
  prepared patch is not landed, and until a human runs `git apply` no commit
  runs this check at all. A workflow that says a job runs a gate is not an
  observation of that gate having run, and the patch is the evidence it *would*
  go red, not a record of a red run.
- **That a checkout this method cannot find is absent.** It is *not found by
  this method*: a checkout behind a composite action, a `fetch-depth` that is a
  `${{ }}` rather than a literal, a workflow that will not parse, a job
  reaching the gate from its prompt rather than a `run:` step — the
  `agent-conflicts.yml` `resolve` case above is real, not hypothetical — and
  anything outside `.github/workflows/`, `docs/ci/agent-gates-deep-schedule.yml`
  among them. That file is prepared rather than landed and states
  `fetch-depth: 0` at its own `:58`; it is outside the tool's glob, so it is
  not a row in the table the tool prints. The landed comment says so rather
  than implying the deep tier's schedule carries the check.
- **That the deep tier does not run it.** It does, indirectly and by design:
  `agent-gates-deep.sh` is a superset that runs the cheap tier first, so
  `AGENT_GATES_DEEP=1` reaches this line. What does not carry it is that tier's
  *schedule*, which runs on nothing.
- **That the eight anchors stay eight.** The list is a template-copied file
  and a re-copy may change it. Re-run the recipe above; `FoldTests` will fail
  if the patch has gone stale, and the header's anchor paragraph is what tells
  a re-cutter where the new material went.
- Any verdict of any tool, any register status, and any hardware or Windows
  fact.
