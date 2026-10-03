# The prepared gate patches describe their tools, and the descriptions drift (issue #976)

`docs/ci/agent-gates-*.patch` is where a gate change waits to be landed.
`.github/scripts/agent-gates.sh` is copied from the agent-pipeline template and
the pipeline's push token has no `workflow` scope, so a branch editing it fails
at the *end* of a pull request; the change is prepared in a patch file instead,
and a human lands it by copying the `git apply` line out of its header. Each
patch carries the rule in two places: the header a human reads before applying,
and a comment at the call site that becomes the gate's permanent description
once it lands.

`tools/test_agent_gates_patches.py` holds the *applicability* of that set — every
patch applies alone, every ordered pair composes, the landed result parses and
is shellcheck-clean. It does not read what a patch says about the tool it
wires, and nothing else did either. That is the gap this write-up is about:
**a patch can apply perfectly, compose perfectly, and describe a checker that
has since changed.** The sentence it lands into the gate script outlives the
tool, and it is the sentence the next reader of that gate consults.

Issue #976 named two such descriptions in
`agent-gates-testdata-row-claims.patch` and asked for the rest of the set to be
censused rather than fixed, so each stale row below is reported and left alone.
Those two are corrected here, along with the same wording in
`docs/agent-pipeline.md`; the corrections land in the patch's own header, in its
gate comment and in that one file, with the superseded wording left visible per
`docs/findings.md` §4a-4d rather than silently replaced.

The table below covers every `docs/ci/agent-gates-*.patch` on this tree, which
is the whole of what that glob names. A patch with no figure this method can
compare is a row with the reason rather than an omission, and
`tools/test_gate_patch_descriptions.py` holds the coverage in both directions —
a new patch landing in `docs/ci/` is a red run until it is read.

## The correction, and what it was

Two claims in `docs/ci/agent-gates-testdata-row-claims.patch` described the
tool as it was not.

**The dated-refusal count.** The header said "Two of those entries are dated
refusals". `check_testdata_row_claims.py` prints
`under the five shapes and the three dated refusals`, and the three are
`two dated captures in one sentence`, `dated capture not found` and
`dated capture has no addr column` — `DATED_REFUSALS` beside `SHAPES`. The
third entry arrived with #990, which stopped reading the date's file set by
extension and started reading it for the column. The header's sentence is left
struck through with the correction beside it.

Note what the corrected sentence is *not* built from: a figure. It names
`shape_label()`, and says the label is derived from the two constants rather
than written out, because that is the property that stopped this drifting. A
count re-typed into a header is a value the next merge has to edit; a count
read off the constants is a sentence that stays true.

**The cheap tier's input trees.** The gate comment said the check is cheap
"because of what it reads -- the committed index, the committed tree under
`ec/tools/testdata/` and two annotation CSVs". It also globs
`evidence/ec-watch/<date>-*`: `CAPTURES` is built from `WATCH`, and
`captures_for()` resolves a bare date in a sentence against that directory.
The comment named three of four input trees, and the one it omitted is the one
that decides whether the check may be called cheap at all. Corrected in place,
naming the capture root and why it is there.

`git apply --check` still succeeds afterwards. Leaving the superseded wording
visible added lines inside hunk #1, whose header carries a new-file count, so
that count moved — the mechanical step, and the one thing in this change that
could silently have broken the patch's applicability.
`tools/test_agent_gates_patches.py` is what proves it did not, and it runs over
the whole set in every ordered pair rather than only this patch.

**The same wording in `docs/agent-pipeline.md`.** Item 10 carried the gate
comment's "two annotation CSVs" list, and is corrected here too: the cheap
tier's inputs now read "`ec/tools/testdata/`, two annotation CSVs, and the
captures under `evidence/ec-watch/` a bare date in a sentence resolves
against", with the reason in a parenthesis. It is the file whose job is to
carry descriptions across a template re-copy, so leaving it wrong would have
left the same false statement in the one place a re-copy picks it up. One
phrase, and nothing else in that file moved.

## The census, and how to re-derive it

Every figure below is read off a run on this tree, not copied. The commands
are in the last column; none of them needs hardware, Windows, or the firmware
image.

| patch | tool | what the patch says | what the tool says | reading |
|---|---|---|---|---|
| `agent-gates-testdata-row-claims.patch` | `check_testdata_row_claims.py --check` | "Two of those entries are dated refusals" | "under the five shapes and the three dated refusals" | **was stale; corrected here** |
| ″ | ″ | gate comment names three input trees | also globs `evidence/ec-watch/<date>-*` | **was stale; corrected here** |
| `agent-gates-0751-self-test.patch` | `grade_0751_isolation.py --self-test` | "the grader's 103 committed tests" | prints a different figure than the patch quotes | **stale, left** — #685, by that patch header's own sentence |
| `agent-gates-pin-table-rows.patch` | `check_pin_table_rows.py` | "105 rows place against 105 records and all seven classes are 0" | a larger row count, with classes non-zero | **stale, left** — see *Read and not corrected* |
| `agent-gates-capture-claims.patch` | `check_testdata_index.py`, `check_capture_claims.py` | "the two CSVs beside it" | the testdata tree holds many loose CSVs and `.txt` files; `check_capture_claims.py` also reads the prose corpus | **stale, left** — see the borderline readings above |
| `agent-gates-disasm8051-self-test.patch` | `disasm8051.py --self-test` | "18 instructions", "4 `REL_SITES`", "11 `BIT_SITES`", "36 assertions in all" | every printed figure agrees | **matches** |
| `agent-gates-gap-text-check.patch` | `verify_gap_text.py --check` | "the 143 instructions `sdas8051` cannot express" | "gap text verdicts: 143 agree" | **matches** |
| `agent-gates-0751-writer-census.patch` | `census_xdata_writers.py --check` | gate comment: "which of the 29 sites store"; header: "the ten writer sites", "ten byte fixtures" | "of 29 found by `sites_for()`", of 10 writer and 10 fixture sites | **matches** — the comment half is now held by the suite |
| `agent-gates-cross-decoder-disagreement.patch` | `cross_decoder_disagreement.py --check`, `--self-test` | "each of the five causes" | the run enumerates the closed vocabulary one label per line | **no figure to compare** — see below |
| `agent-gates-bank-map-score.patch` | `bank_map_score.py --check`, `firmware_regions.py --check` | "a block whose verdict is outside the three its classifier can produce" | `ERASED`, `NON_ERASED`, `UNCLASSIFIED` | **no figure to compare** — see below |
| `agent-gates-findings-frozen.patch` | `check_findings_frozen.py`, `gen_findings_index.py --check`, `check_no_append_logs.py`, `check_no_conflict_markers.py` | what `tools/README.md` and `docs/findings/test-line-pin-census.md` *were*: a hand-kept total with supersession notes under it, dated per-merge headings | neither document carries either shape now | **a record of a past tree**, not a claim about this one |
| `agent-gates-reassembly-bound-check.patch` | `reassembly_checked_bound.py --check` | "0.15 s here over three runs", "a cheap tier §14e's table records at 5.9 s" | the tool prints no timing; the 5.9 s is `docs/agent-pipeline.md`'s | **no figure to compare** — see below |

The commands:

```sh
python3 ec/tools/check_testdata_row_claims.py --check
python3 ec/tools/grade_0751_isolation.py --self-test
python3 ec/tools/check_pin_table_rows.py
python3 ec/tools/disasm8051.py --self-test
python3 ec/tools/verify_gap_text.py --check
python3 ec/tools/census_xdata_writers.py --check
python3 ec/tools/cross_decoder_disagreement.py --check
python3 ec/tools/bank_map_score.py --check
python3 ec/tools/firmware_regions.py --check
python3 ec/tools/check_findings_frozen.py
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/reassembly_checked_bound.py --check
git apply --check docs/ci/agent-gates-testdata-row-claims.patch
```

### The rows with nothing to compare, and why

A row reading **no figure to compare**, and `findings-frozen`'s, are not rows
this suite can assert, and each says why in `NOT_HELD`. The ones reading *no
figure to compare* quote a figure no tool prints: a count of module constants
spelled as a word (`bank-map-score`'s "three verdicts",
`cross-decoder-disagreement`'s "five causes"), and a timing on one runner
(`reassembly-bound-check`'s 0.15 s, which its own header calls one runner's
figure). That is the same derived-sum shape as the disasm row below, one level
up: a claim the tools' output does not spell as a figure cannot be compared
against it.

`findings-frozen` is different in kind. It quotes what `tools/README.md` and
`docs/findings/test-line-pin-census.md` looked like *before* the checks this
same patch wires removed the append logs — `tools/README.md`'s hand-kept total
and the supersession notes under it, the census file's dated per-merge headings.
Neither shape is in either document now, which is what those checks hold. Note
what that does and does not mean for the figures: the census file has grown
since, so "the dated headings are gone" is not "the file is shorter", and the
patch's line counts are a record of one past tree rather than a claim about
this one — there is nothing to re-derive and nothing to hold them to. Both
documents and the decision are written up in
`docs/findings/no-append-logs.md`, which the patch cites.

### The two borderline readings, stated rather than resolved

**`agent-gates-disasm8051-self-test.patch`'s "36 assertions in all" is a
derived sum, not a printed figure.** The tool prints its groups separately and
prints no total, so there is no line to compare that sentence against; adding
one would be a change to the tool to make a patch's prose checkable, which is
the tail wagging the dog. It is recorded as a sum over the groups the tool does
report, and it agrees. **A suite that cannot check it says so** rather than
passing on a coincidence.

**`agent-gates-capture-claims.patch`'s "the two CSVs beside it" is stale in a
way no printed figure captures.** The phrase counts files in the testdata tree,
and no tool prints that count, so a figure-comparing check cannot see it — it
is a census row here and not a row in
`tools/test_gate_patch_descriptions.py`'s `KNOWN_STALE`, because an exemption
nothing can judge is a hole with a comment on it. Its other half is the same
kind of claim: the gate comment names the two CSVs but not the prose corpus
`check_capture_claims.py` reads, though the header records `registers.yaml` as
the subject one sentence above. Reported here rather than corrected.

## What now holds a description to its tool

`tools/test_gate_patch_descriptions.py` is the check. It runs each wired tool as
a subprocess, reads the figure off the run, and requires the patch's header to
carry it; for each tool whose input trees it can name from the tool's own
module constants, it requires the gate comment to name each one. It is not
wired into `.github/scripts/agent-gates.sh` — a seventh `gate` line at a list
two patches already insert into is #956's problem, not this one's — and
`tools/run-tests.sh`, which is what `ci.yml`'s `tests` job runs, discovers it by
`find` like any other suite. Both are green.

The bound is stated rather than hidden, and it is the sibling's: **a claim
already wrong is exempt by construction; a new one is not.** The descriptions
the census found stale, and did not correct, are the ones `KNOWN_STALE`
silences: each keyed on the sentence the patch carries, and each naming the
file recording where the correction is tracked. Every key is held in both
directions, both read off a run: the quoted sentence must still be in the
patch, and the figure the tool prints must still differ from the one it quotes.
Correct a description anywhere and the key fails and says to drop it, which is
what makes the exemption an enumerated fact rather than a hole.

A key holds no figure of its own, and that is deliberate rather than an
omission: what the tool prints in place of a stale claim is for two of these a
count of this repository's own tests, which is a value every merge that adds a
test case has to edit — and a test table is not where anyone looks to edit one.
The run already answers the question a recorded figure would answer.

An owner is a file in this repository rather than an issue number. Two of these
descriptions were first attributed to issues that have since closed, which left
the suite reporting them as owned by work nobody was doing — a closed number is
indistinguishable from a live one by looking at it, and nothing here holds one
open. `test_every_stale_key_names_an_owner` therefore requires the owner to
name a file that is there, which is the part of that claim this repository can
check. Whether an issue is still open is a fact about GitHub, not about this
tree, and this suite does not reach GitHub to ask.

**The set is covered in both directions, and that is what makes the table a
census of the set rather than of itself.** `PATCHES` names what the suite
compares and `NOT_HELD` names what it does not and why, and a case holds each
against the tree both ways: a name pointing at a patch that is gone, and a patch
on disk that neither table names. The sibling asserts the same direction for
applicability and gives the reason in one line — a new one is picked up silently
by the glob. Without it, the first version of this table examined part of the
set and read as if it covered all of it, which is a scan that covered part of
the tree written up as if it covered the whole: the same defect as a zero-hit
scan called `absent`.

**What the suite does not check is prose**, and two things in particular. A
patch claiming a tool "catches regression X", or "is cheap because it reads
one CSV", is a reading. So is any figure a tool derives rather than prints —
which is why the disasm sum above is a census row and not a key. Not found by
this method, never absent.

**A tool's exit code is not asserted**, and the reason is the shape of the
claim rather than an oversight: what is held here is a description against a
figure, and a tool that exits non-zero can still print the figure its patch
quotes. `check_pin_table_rows.py` is the case in point — it exits 1 on this
tree, and the pin-table row above is where that reading lives. Asserting the
code would make this a second copy of every tool's own gate, and it would go
red here over a fact about the tool rather than about any description.

Every case named in the table below was checked against a mutation it is
supposed to catch, applied to the tree and reverted rather than asserted:

| mutation | case that went red |
|---|---|
| put the header's dated-refusal count back to two | `test_each_patch_carries_the_figure_its_tool_prints` |
| say four where the tool says three | same |
| say a site count the tool no longer prints | same |
| drop `evidence/ec-watch/` from the gate comment | `test_each_gate_comment_names_every_input_tree_its_tool_reads` |
| correct an enumerated stale claim | `test_every_stale_key_still_quotes_its_patch` |
| re-point a key at a sentence carrying the figure the tool now prints | `test_every_stale_key_is_still_wrong` |
| re-point a key at a sentence quoting no figure at all | same |
| give an owner back as a bare issue number | `test_every_stale_key_names_an_owner` |
| land a patch in `docs/ci/` that neither table names | `test_every_patch_on_disk_is_accounted_for` |
| let the header parse leak a line it should drop | `test_a_prose_half_with_no_claim_reads_as_empty` |

The cases not named here were not checked against a mutation, and saying so is
the point of naming the ones that were: `test_the_table_names_a_patch_that_exists`
and `test_each_named_root_constant_still_reads_as_it_did` are assertions about
the tree's shape rather than about a figure a tool moves, and the remaining
`ParseTests` cases check the parse against inline text whose expected value is
written out beside it.

## Read and not corrected

**`agent-gates-0751-self-test.patch`'s test count.** Its own header says the
other occurrences of the figure are #685's to correct, "deliberately not here,
so this issue and that one cannot both be editing the same sentences", and it
carries a chain of its own past figures as a per-commit record. Editing it here
would break that division of labour for no gain.

**`agent-gates-pin-table-rows.patch`'s row count, and more.** The header claims
the tool is green as prepared, with a specific figure and "all seven classes
are 0". On this tree the tool is **red** — `check_pin_table_rows.py` exits
non-zero, and the per-pin table carries unplaced rows and rows with no census
record. That is a live reconciliation failure rather than a stale sentence, and
reconciling it is follow-up work rather than a sentence to reword. It is also
worth naming here because of what it says about the class: **"it is green as
prepared, and that was measured" is a claim about a tree, and it is the one
kind of claim in this set that a landing would make real** — a patch that lands
a red gate is how a gate gets switched off. Nothing here claims the other
patches are green; each was run, and the run is in the table.

**`docs/findings.md` §76's closing "the patch is **not** touched — the CLI is
unchanged".** Same wrong reason as the sentence corrected here, one file over,
and §76 is a shared summary file that is closed to new sections and heavily
contended. Named, not edited.

**`docs/findings/testdata-third-column-claims.md`'s "six shapes".** Left
standing deliberately. It is the before-record that
`check_testdata_row_claims.py`'s docstring and
`testdata-row-claims-dated-capture.md` both cite, and `docs/findings.md` §76
already carries the live correction beside its own six-shape census.
Overwriting it would destroy the before that §4a-4d asks to be left visible.

## Nothing here touches hardware

Every command in the census runs over committed files. The CSVs and `.txt` files
under `evidence/ec-watch/` are read as text, which is what `carried_by()` already
does; no capture is opened in any sense that touches hardware, no register is
read back, and no `status:` in `ec/annotations/registers.yaml` moves, so that
file is not touched at all.

## Left open

- **The census is a snapshot of a tree, not a property of one.** Every figure
  here is a count that moves when a fixture, a test or a row lands — which is
  exactly why the corrected patch header names `shape_label()` instead of
  quoting it. The suite is what stops the descriptions going stale; this table
  is what says which were, and it is correct as of the tree it was measured on.
