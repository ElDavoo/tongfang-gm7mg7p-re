# The figure-pins checker is prepared for the cheap gate, in a patch that had to fold (issue #877)

**Written 2026-10-04.** Issue #877 asked for a patch of its own in `docs/ci/`,
named for this tool, carrying its own `gate` line, plus a `PATCHES` entry in
`tools/test_agent_gates_patches.py`. **That shape is not available and refusing
it is the finding.** Every insertion point the `gate` list admits was cut and
applied in both orders against every other prepared patch, and none of them
composes — while each applies cleanly *alone*, which is the combination that
makes the failure silent in the way that matters. So the check folds into
`docs/ci/agent-gates-testdata-row-claims.patch` for the reason every other fold
in that directory is, and this page is the measurement behind it.

It is written as a file rather than a paragraph in `docs/agent-pipeline.md`
because #1033's
[`history-checkouts-gate-wiring.md`](history-checkouts-gate-wiring.md) is where
the pipeline doc already sends this class of question, and because the anchor
table below is the re-derivation rather than a claim to inherit.

**Nothing here is a hardware, firmware or Windows claim.** No image is opened,
no register is read back, no capture is taken, and no EC, BIOS or vendor binary
is touched anywhere below. Every figure is a count of lines and patches over text
committed in this repository, and the commands that produce them are in it.

## The premise, re-derived rather than quoted

[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md)'s *The standing: this tool
runs by hand* says the prepared route is "a `docs/ci/agent-gates-*.patch` plus a
set edit in `tools/test_agent_gates_patches.py`, and both are a human's change
and their own issue." That is right about the constraint and incomplete about the
shape, and the incompleteness is what this page measures.

Checked on this tree:

- `.github/scripts/agent-gates.sh`'s cheap tier is reached through
  `check_doc_links()`, whose `gate` line is the **last** in the list, and
  `.github/` is out of an agent branch's reach by construction — the push token
  has no `workflow` scope, so a branch editing it fails at the *end* of a run
  rather than at the start of it. `docs/agent-pipeline.md` carries that across a
  template re-copy.
- The prepared route therefore has to be a patch plus a set edit, and the set
  edit is `PATCHES` only if a **new file** exists. `PATCHES` is held against the
  `docs/ci/agent-gates-*.patch` glob in both directions, so a new file without
  the entry is red and an entry without a file is red; that pair is what makes
  "`PATCHES` gains the path" the *only* correct response to a new **file**, and
  it is the wrong response to a fold.

## The anchor table

**`docs/findings/prepared-gate-patches.md`'s collision table is not edited
here**; this is its extension, and #1033's table is its predecessor. The recipe
is #1033's, unchanged — each candidate is cut the way a re-cut is cut, tried
alone, and applied in **both orders** against every committed patch, each order
in its own freshly seeded tree. The three load-bearing details of that recipe are
spelled out there and hold: the edited file must be **staged** before
`diff --cached` (unstaged, the candidate cuts 0 bytes and a harness that reports
a non-composition per pair reads as *free*), `-C` changes the base for relative
paths (so committed patches are addressed from the repository root, not from the
scratch tree), and each order needs its own seed.

**A fourth detail is this one, and it cost a wrong table before it cost a right
one.** Each *candidate* needs its own seeded tree, not only each order within a
candidate: re-cutting the next candidate with `git checkout -- <file>` restores
from the **index**, which still holds the previous candidate's edit, so each
anchor's patch carries every earlier anchor's line and each one is blocked by
patches that do not actually reach it. The first version of the table below was
produced that way and overstated the obstruction — it read pin-table-rows and
capture-claims as holding anchors where one of them composes cleanly. A table
that overstates a blockage is the safe direction to be wrong in for a *landing*
and the wrong direction entirely for a table a future re-cutter cuts against, so
the numbers here are from the corrected sweep: **a fresh seed per candidate**.

The `gate` list: every insertion point it admits, and none of them free.

| anchor | the new line lands at | applies alone | fails to compose with |
|---|---|---|---|
| P0 | before `gate 'registers.yaml'` | yes | pin-table-rows |
| P1 | before `gate 'scan_refs.py smoke test'` | yes | capture-claims, pin-table-rows |
| P2 | after `gate 'scan_refs.py smoke test'` | yes | capture-claims, pin-table-rows |
| P3 | after `gate 'register counts'` | yes | capture-claims |
| P4 | before `gate 'python syntax'` | yes | capture-claims |
| P5 | before `gate 'shellcheck'` | yes | capture-claims, testdata-row-claims |
| P6 | before `gate 'doc links'` | yes | testdata-row-claims |
| P7 | after `gate 'doc links'` | yes | testdata-row-claims |

**Every one of them applies cleanly alone, and not one of them composes.**
That combination is the whole trap, and it is the reason
`docs/ci/agent-gates-testdata-index.patch` no longer exists. A patch of its own
would be green in `git apply --check`, green in the one check a person runs
before trusting a patch, and would fail only at the moment a sibling landed —
with a context-mismatch message that reads like staleness rather than
composition.

**This table agrees with #1033's, and that is a result rather than a
restatement.** #1033 measured the same anchors for a different check, on a
tree with more patches in the set than it had, and reached the same verdicts;
the re-derivation was run because a table is a record of the tree it was measured
on and not a map of where a hunk may be cut today. **The part worth carrying is
which anchors are held by an insertion point at that exact line and which are
only near one** — P0, P3 and P7 are the first kind, each of them the exact
insertion point of `pin-table-rows`, `capture-claims` and
`testdata-row-claims` respectively, and P1, P2, P4, P5 and P6 are the
second: each sits a line or two from a held anchor, and a hunk's three-line
context window reaches over it. **P6 reads as blocked with the rest and is
not**, and it is the one a re-cutter is most likely to get wrong — it sits
directly above P7's insertion point, one line below `gate 'doc links'`, so a
candidate cut there is measured against P7's hunk rather than its own.

**What tells the two kinds apart is the width the candidate is cut at, not
the verdict either width reports.** Cut it at `-U1` and again at `-U3`, apply
in both orders against the whole set at each width, and compare which patches
still block it: **the first kind is blocked in both landing orders at one line
of context; the second still lands at one line when the committed patch goes
first**, and fails only when the candidate goes first — the same failure `-U3`
reports for it, where the hunk's wider context reaches over its neighbour rather
than a held insertion point being in the way. All eight are blocked in both
orders at the width the table above reports them, so neither kind is a
workaround at any of the eight, and the patch's header says so.

The function half is not the constraint, and saying so is what makes the fold
cheap rather than a compromise. Cutting only the `check_doc_figure_pins()`
definition and applying it in both orders against the committed set:

| gap | the function would start at | applies alone | fails to compose with |
|---|---|---|---|
| before `check_scan_refs_smoke_test()` | yes | — |
| before `check_register_counts()` | yes | — |
| before `check_python_syntax()` | yes | capture-claims |
| before `check_ghidra_tooling()` | yes | bank-map-score |
| before `check_shellcheck()` | yes | testdata-row-claims |
| before `check_doc_links()` | yes | findings-frozen |

The gaps above `check_scan_refs_smoke_test()` and above `check_register_counts()`
are free, so a function-only patch could have shipped and been green — **which is
why a standalone patch is the trap rather than a partial solution.** It would have
landed a `check_*()` nothing calls: `bash -n` and `shellcheck` both pass on a
defined-but-ungated function, every ordered pair
composes, and the gate is exactly as blind as it is now. The `gate` line is the
half that cannot be had separately, and a check without one is not a check.

## The decision, and what was left out

**The check and its `gate` line fold into
`docs/ci/agent-gates-testdata-row-claims.patch`.** That patch already carries
other tools' checks and their `gate` lines, so this folds alongside them — the
same decision #1033 reached, from the same measurement. Its function hunk sits
beside `check_testdata_grader_claims()`'s at `check_shellcheck()`, and its
`gate` line is appended to the one that patch already carries.

`tools/test_agent_gates_patches.py`'s `FoldTests.REQUIRED_SECOND` grows by the
function definition and the `gate` line, and that is the whole of the coverage —
the same case that catches a fold catching a half-right landing, and the one
#1033's fold added its lines for. **Both directions of the half-loss were run,
not assumed:**

- dropping the `gate` line and keeping the function turns
  `test_the_second_fold_still_lands_both_halves` red **by name**, on that string
  and no other, and nothing else in the suite goes red;
- dropping the function and keeping the `gate` line turns the same case red on
  `check_doc_figure_pins() {`, again alone.

That is the case nobody-has-seen-go-red discipline `prepared-gate-patches.md`
records, and it is the reason the mutation is worth two minutes: a re-cut that
loses either half is a valid patch, applies, composes in every ordered pair, and
passes `bash -n` and `shellcheck`. A case that has never been seen to fail is
worth nothing, so both were run.

**Left out: the patch file of its own, and the `PATCHES` entry that goes with
it.** Declined on the measurement above, and shipping it anyway would have put a
patch in `docs/ci/` that fails `test_every_ordered_pair_lands` on the commit that
adds it — worse than no patch, for the reason #1033's write-up gives. **This
page does not spell the declined filename, and that is a consequence rather than
a preference:** `tools/check_doc_patch_refs.py` parses every patch name prose
names and reports one absent from `docs/ci/` as `STALE`, which is the right
answer here. The two ways out are a `HISTORICAL` key or dropping the name, and
that enumeration is for names that were *records* — a patch that shipped under a
name later folded away, kept visible so a reader can see what the file was. A
proposed name that never existed on disk is not that, so widening it would
exempt a string this branch never treated as a file.

**Left out: landing.** `.github/scripts/agent-gates.sh` is not this branch's to
edit, and applying the patch is a human's `git apply`. What a landing has to do
*beyond* the apply is in the patch's own header, because a reader holding the
patch is who has to know them:

1. `ec/tools/check_doc_figure_pins.py`'s docstring paragraph **"And what this
   tool is not"** says the tool is not in `.github/scripts/agent-gates.sh` and
   runs by hand. After the apply that is false, and the docstring is where a
   reader looks first.
2. `ec/tools/test_check_doc_figure_pins.py`'s
   `TheToolRunsByHand.test_it_is_not_in_the_cheap_gate` asserts the name is
   *absent* from the gate script, and `test_its_docstring_says_so` asserts the
   docstring still carries "not in `.github/scripts/agent-gates.sh`". **The apply
   turns the first red and leaves the second green** — measured, in a seeded
   tree with the patch applied, where the suite reports one failure and that
   case is it; add item 1's docstring rewrite and it is two. They are that
   tool's own honesty about its standing — the issue calls that honesty
   load-bearing, and [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) calls
   it the shape of defect #819. The rewrite points the same claim the other way.
3. `docs/findings/prepared-gate-patches.md` and `ec/README.md` record the patch
   as prepared, and both stop saying so at the landing.

**Doing (1) and (2) now would assert a gate that does not exist.** They are not
in this branch for the same reason the patch is not landed: one reads the
committed gate script and the other the docstring, and while the patch is
unlanded the standing they assert is the true one. The one that reads the gate
script turns red **by design** on the day of the apply; the one that reads the
docstring stays green until item 1's rewrite lands, and turns red if that
rewrite and the case are not made together.

## The precondition, and it is not met

**`check_doc_figure_pins.py` exits 1 on the committed tree**, so landing this
patch without fixing §2b first would put a red check in the cheap tier. That is
the `verify_gap_text.py --check` shape `prepared-gate-patches.md`'s *A deviation*
heading is about — "the cheapest way to make a gate get switched off" — and this
page records the disagreement rather than fixing it.

```console
$ python3 ec/tools/check_doc_figure_pins.py \
    docs/findings/xdata-census-rederivation-checklist.md --section 2b
…
docs/findings/xdata-census-rederivation-checklist.md §2b: the row marks 440 'held'; measured 'unheld' (no occurrence in ec/tools/*.py and no committed cell)
docs/findings/xdata-census-rederivation-checklist.md §2b: the section's own marking disagrees with the measurement on 10 point(s)
…
§2b: 18 figure(s), 14 measured held, 4 measured unheld, 0 not read by this method
$ echo $?
1
```

Two disagreements, and they are different kinds. **Some rows marked `held`
measure `unheld`** — no oracle entry, no literal inside a check, no cited
committed cell — and **others name a `file:line` that measures in a different
module** from the one they cite, which is the third of the three-way pin
resolution failing rather than the figure being unpinned. The run names every
row it objects to, so which is which is read rather than inferred; what matters
here is that the two kinds are different defects.

**Reconciling them is not this change's work, and the reason is ordering rather
than size.** §2b is a committed document that other changes move, and the tool
names the row and the pin for every disagreement, so the fix is a measurement
against a page rather than an edit made once. Landing first is what makes it
cheap; landing first without it puts red in CI. **Re-measure at the tip you land
on** — the figures in the transcript above are true of the tree this page was
written on and the disagreement is about text any of the suite landing below it
can move.

The tool's own verdict vocabulary is what keeps this readable rather than
alarming, and it is worth saying so in a document whose transcript is full of
`unheld` rows: an `unheld` is **"not found by this method", never "absent"**, and
every
row prints the `file:line` that decided it. `doc-figure-pin-audit.md`'s *What the
method cannot see* is the other half — the literal search is over every tool
module, so a figure that happens to equal an unrelated assertion's literal reads
as held, which is the safe direction to be wrong in and the reason the printed
`file:line` is not decoration.

## What this does not claim

- **That any gate runs this check.** It does not, and it will not until a human
  runs `git apply` and commits. Nothing here was executed by CI, and
  `.github/` was not touched by this change; the patch is the evidence a gate
  *would* go red, not a record of a red run.
- **That landing this is safe on its own.** It is not, and the patch's header
  says so in the terms a human holding the patch reads. The three edits above are
  part of landing, not after it, and the cases that assert the hand-run standing
  are what stop a landing that skips them from reading as a clean one.
- **That the anchor tables above stay true.** Both are records of trees they
  were measured on. Re-run #1033's recipe; `FoldTests` fails if the patch has
  gone stale, and its failure message is the instruction.
- **That a figure §2b reports `unheld` is unpinned.** Only that this search over
  committed text did not find one.
- Any verdict about the EC, the BIOS, the Windows stack, any register status, and
  any hardware or Windows fact.