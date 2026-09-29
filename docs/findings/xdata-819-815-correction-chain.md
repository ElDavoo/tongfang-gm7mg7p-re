# Two gate claims #819 corrected were settled by #815 and #823, and eleven pins across the chain no longer land (issue #836)

The write-up for [issue
#836](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/836), about a
correction that asserted a gate state and left a decision open, both of which
have since been settled. What this branch changes is two dated paragraphs
beside those sentences and this file. **No tool, no CSV, no YAML, no suite and
no gate script is edited** — the whole content is that eleven line pins in this
chain no longer name the sentences they are about, and that one disagreement
between two write-ups now has a written answer.

**Nothing here is a hardware claim.** No register was read back, no image was
opened, no capture was taken, and no laptop, EC or Windows machine is involved.
Every figure below is a line number or a `git grep` transcript over committed
text, and the command that produces each one is in it. Nothing here establishes
anything about the firmware: `XDATA_0860` stays `present-untested` and no
`status:` in `ec/annotations/registers.yaml` moved.

## The measurement

The `#815` change, landed as #823, rewrote the comment over the census arm in
`.github/scripts/agent-gates.sh` and changed what that arm runs, so every pin
into that file from this chain is re-derived here rather than shifted by
arithmetic. Re-derived 2026-09-28, from the repo root:

```console
$ git grep -n 'ec/tools/xdata_register_map.py' -- .github/scripts/agent-gates.sh
.github/scripts/agent-gates.sh:127:              ec/tools/xdata_register_map.py \

$ git grep -n -e 'wired `--check`' -e 'used to be deliberately not run' \
    -e 'honest description' -- .github/scripts/agent-gates.sh
.github/scripts/agent-gates.sh:217:      # since it was written; issue #256 wired `--check` and issue #815 wired
.github/scripts/agent-gates.sh:220:      # **`--self-test` used to be deliberately not run, and the reason it gave
.github/scripts/agent-gates.sh:254:      # checks. So the honest description of what is gated here is no longer the

$ sed -n '262,263p' .github/scripts/agent-gates.sh
      *xdata_register_map.py)
        python3 "$tool" --check && python3 "$tool" --self-test || rc=1
```

| what | line now | what this chain said |
|---|---|---|
| the `for tool in` list entry | `:127` | `:127` — **the one surviving pin** |
| the `*xdata_register_map.py)` arm | `:262-263`, reading `--check && … --self-test` | `:235-236`, `--check` only |
| the comment above that arm | `:211-261` | `:210-234` |
| the "deliberately not run" reason | `:220-233` | `:218-234` |
| the arm's own closing sentence | `:254-255`, "no longer the two CSVs" | `xdata-green-set.md`'s parenthetical says `:253-254` |

**`:138` is unaffected, and is not a pin that moved.** It is still the
`*decompile_native.py)` case, which is what
[`xdata-green-set.md`](xdata-green-set.md) says it is, and the finding that the
issue's own body named the wrong case still stands.

## The pin-drift census

This is the finding. The chain's pins drift in three files, in both directions —
some too early, some too late — and one of them names a claim that **has already
been corrected in place** by the issue that owned it. Each row was located by the
sentence's own text, not by the line the pin gives.

| # | the pin | what is at that range now | where the sentence it names is |
|---|---|---|---|
| 1 | `ec/annotations/xdata-06c2-06db-timers.md`, #819 blockquote → `agent-gates.sh:235-236` | inside the comment block over the census arm | the `*xdata_register_map.py)` case at `:262-263` |
| 2 | same → `agent-gates.sh:210-234` | — | the comment above that arm, `:211-261` |
| 3 | same → `agent-gates.sh:218-234` | — | the reason paragraph inside that comment, `:220-233` |
| 4 | `docs/findings/xdata-green-set.md` table row → `xdata-register-map.md:2586` | the `read` / `passed-to-call` call-site paragraph | the `--self-test` bullet further down the same file |
| 5 | same file, owning-issues table → `xdata-register-map.md:2585-2591` | the same call-site paragraph | the same bullet |
| 6 | `docs/findings/xdata-green-set.md` table row → `xdata-cluster-names-guard-off-recipe.md:289-292` | *"Where the old table's two `changed` rows came from."* | `:445-448`, under **What this does not do** |
| 7 | `docs/findings/xdata-green-set.md` parenthetical → `agent-gates.sh:261-263` | the comment's last line and the arm | `:262-263` |
| 8 | same parenthetical → `agent-gates.sh:253-254` | — | `:254-255`; the range does not contain the quoted words at all |
| 9 | `docs/findings/xdata-census-self-test-gate.md` → `xdata-cluster-names-guard-off-recipe.md:406-407` | the `#816` "Closed" blockquote | `:445-448` — the same sentence as row 6 |
| 10 | same file → `xdata-06c2-06db-timers.md:972-973` | a console fence | `:993` |
| 11 | same file → `xdata-06c2-06db-timers.md:1031-1032` | **this branch's own `#836` correction paragraph** — see below | `:1079` |

**Rows 1–3 are corrected in place** by the dated paragraph this branch appends
inside that file's existing #819 blockquote, which names the arm by its content
for exactly the reason the pins do not survive. **Rows 4–8 are corrected** by the
dated note this branch adds under
[`xdata-green-set.md`](xdata-green-set.md)'s superseded-claims table, which
quotes the sentences and points at this census. **Rows 9–11 are found, named, and
not corrected here**: they are all in
`docs/findings/xdata-census-self-test-gate.md`, a second shared file that a
concurrent branch is as likely to be editing, and a pin that is named is a
follow-up rather than a silent merge conflict. That is a scope decision and it is
recorded as one.

**Row 11 is the one pin in this list this branch moved itself, and the table above
is transcribed on the merged tree rather than on the tree this branch was written
on.** Appending the `#836` correction to `ec/annotations/xdata-06c2-06db-timers.md`
adds 27 lines at that file's `:1022`, and everything below it moves by that much:
`:1031-1032` no longer names the no-op reproduction paragraph but this branch's
own correction, and the sentence the pin is about — *"red on `main` at the time of
writing"* — is at `:1079`, not `:1052`. **No other pin in the tree is affected**:
rows 1–9 name files this branch does not edit, and a `git grep` for the pins into
the timers file puts every one of them that is not this row's at `:989` or below —
above the append, and unmoved by it. The
pin in `xdata-census-self-test-gate.md` is itself left alone, being in the file
rows 9–11 say is not edited here, so a reader checking it there should shift it by
the same 27 lines. **That is the drift this census measures, reproduced by the
census itself** — which is the right place for it to show up rather than in a
reader's line numbers, and it is recorded rather than quietly re-derived.

**Two further pins are deliberately left out of the count, and the difference
between them and rows 7 and 8 is the whole point of the list.** `xdata-green-set.md`
carries the pre-#823 pins `:235-236` and `:210-234` in its main sentence as well
as in the parenthetical beneath it, and that parenthetical already says they are
the pre-#823 file — so they are recorded as superseded by the text sitting next to
them, which is the only thing that makes a pin safe to leave. Rows 7 and 8 are the
same sentence's *post*-#823 half, and they are counted, because that parenthetical
states them as current positions and both are a line early.

**This census is a measurement with a date on it, not a standing link.** It says
what eleven pins did on this tree; nothing depends on their staying that way, and
the corrections it justifies quote their sentences rather than reproduce its
numbers. The boundary is explicit: it covers the pins naming sentences in the
`#819`/`#815` chain, and **it is not a sweep of every line pin in the family** —
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md)'s **A `file:line` check, of
a kind this tree did not have** already records that nothing mechanical held a pin
in this repository before that issue, so treat an unlisted pin as *not found by
this method* rather than as correct.

## The recorded decision

Two write-ups disagree about whether
`xdata-cluster-names-guard-off-recipe.md`'s **No gate is wired.** bullet — *"No
gate is wired. `tools/run-tests.sh` is not in CI, and closing that gap — along
with the cheap tier not running the tool's `--check`/`--self-test`, which are
red on `main`"* — is a live claim at all.
[`xdata-green-set.md`](xdata-green-set.md)'s row judged it *"a **closed**
issue's write-up; its 'What this does not do' records that PR's scope, not a live
claim"*, and
[`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md) — the write-up
`#815` filed and #823 landed — lists the same sentence among the four it names
without editing, in a section headed **Named, not edited**.

**The decision: take the first position. The bullet is a record of what that
branch did not do, and it stays unedited.** Three reasons, in the order they
carry weight. The heading names what the bullet *is* — **What this does not
do** — and a bullet under that heading is a statement about one branch's diff
rather than a standing claim about the tree. The write-up is a closed issue's,
`#753`'s, so it sits on exactly the ground on which `xdata-green-set.md`'s own
two `xdata-no-eq-guard-refusal-contract.md` rows and its two
`0751-grader-self-test-gate.md` rows were already left alone: the same precedent,
applied consistently, is what makes that table mean anything. And the sentence
has one half that `#815` made false and one it did not, sitting together in one
statement about one branch — which is what a scope statement looks like.

**One clause of it is not settled by this decision, and is named rather than
resolved.** The bullet's `tools/run-tests.sh` half says *"is not in CI"*, and
`git grep -n 'run-tests' -- .github/workflows/` returns one hit:
`.github/workflows/agent-conflicts.yml` runs `bash tools/run-tests.sh` after
resolving a conflict. So that half is not literally true either, while what the
bullet reaches for — that no gate the tree's green or red turns on runs the whole
suite — is, and `#162` is still open for it. **Which of the two the sentence
means is a question about a closed write-up, and it is the same question this
decision is about, not a smaller one that can be answered beside it.** Nothing
here claims the workflow refutes the bullet; it is named because a decision that
rests on "one half of it is still true" has to notice that it is not.

**The pin is corrected either way.** A row whose pin misses its target cannot be
checked by anyone who takes the other side, so the two rows that name this
sentence — `xdata-green-set.md`'s and `xdata-census-self-test-gate.md`'s — point
at the sentence by its text, and this census records where it actually is
(`:445-448`, not `:289-292` and not `:406-407`). Deciding the question and
finding the sentence are two different acts and only the second is
uncontroversial.

**What would overturn it, and what it would cost.** A reader who holds that *any*
sentence asserting a live gate state is a live claim, whatever section it sits
under, has the better of that argument on the page's own wording — the bullet
does say in the present tense that no gate is wired, and the cheap tier now runs
both modes. Overturning this is **one dated blockquote in the recipe page**, in
the `> **(Correction, …)**` form used everywhere else in this chain, added
inside that section rather than under it. It is not done here because the
sentence's owner is a closed issue and the pin was the part that was actually
broken.

## Why the issue's own line numbers are not a source either

The issue locates the timers blockquote at `:946`; the blockquote opens fifty-five
lines later than that. In `xdata-green-set.md` it gives `:119`/`:130`/
`:132-136`/`:139-142` for four things that are the two `#815` rows of the
superseded-claims table, the paragraph under that table, and the file's **The
five sentences corrected in place, and where** rule — off by about fifty-five
lines there too. Its pin for the recipe sentence, `:405-408`, lands inside the
`#816` "Closed" blockquote rather than on the bullet. **The issue names the recipe
sentence correctly and locates it wrongly, which is the exact failure the issue is
filed about** — and the reason the four green-set places are named by their
headings here rather than by the numbers this file could quote for them is that
two dated additions have since moved them once already, which is the drift this
file is about reproducing.

So: every sentence in this chain was located by `git grep` on a fragment shorter
than the sentence, and every line number in this file was re-derived on the tree
this branch lands in. A pattern that wraps across lines prints nothing and is
**not** evidence of absence — `xdata-green-set.md`'s own test section is the
worked example, and the discipline is stated there rather than repeated here.

## What this does not do

- **The recipe page's sentence.** Decided above, not edited.
- **Rows 9–11 of the census**, all in `xdata-census-self-test-gate.md`. Named,
  not corrected, for the scope reason given.
- **`docs/findings.md`.** Frozen at §97 and held by
  `check_findings_frozen.py`; the one edit that file does not permit is a
  helpful summary section, and none is added here.
- **`ec/annotations/xdata-register-map.md`.** It already carries the `#815` and
  `#816` corrections in place and is not stale; the rows that cite it are.
- **`.github/scripts/agent-gates.sh`.** Copied from `ElDavoo/agent-pipeline`, and
  the decision a change there would carry has already been taken. `.github/scripts/`
  *is* pushable — only `.github/workflows/` and `.github/actions/` are not — so
  that is a reason not to, not a reason it cannot be.
- **`tools/run-tests.sh`'s wiring** (#162), and the `workflow`-scope premise the
  old green-set paragraph rests its last sentence on. The premise is already
  answered against itself, in
  `xdata-census-self-test-gate.md` and in
  [`xdata-green-set.md`](xdata-green-set.md)'s own *Left out on purpose* list; it
  is named in the correction rather than argued here.
- **Any tool, CSV or `registers.yaml` row**, any issue closure, and anything
  opened in another repository. Submitting upstream is a human's step in every
  case, and #10 stays where it is.

## The test that proves it works

Prose held to the tree. Every command is `git grep`, `python3` or `bash`; nothing
needs Ghidra, an image, a network or the hardware.

The claim under correction, against the merged gate script:

```console
$ git grep -n -- '--self-test' -- .github/scripts/agent-gates.sh
$ git grep -n 'ec/tools/xdata_register_map.py' -- .github/scripts/agent-gates.sh
```

The first is twenty lines and the second is one; between them they print the
arm reading `--check && … --self-test`, the comment saying that
`--self-test` *"used to be deliberately not run, and the reason it gave is no
longer true"*, the sentence ending *"no longer the two CSVs"*, and the
`for tool in` list entry at `:127`. The transcript at the top of this file is the
subset of those two that decides the table there.

That nothing was reworded or deleted — each false sentence is still findable by
a pattern **shorter than the sentence**, each followed by a dated block naming
this issue:

```console
$ git grep -n "genuinely not" -- ec/annotations/
$ git grep -n "that is #815's to decide" -- ec/annotations/
$ git grep -n "deliberateness is unchanged" -- docs/findings/
```

The first pattern is two words where the phrase it stands for is five, and it is
two rather than five **because the five wrap across a line break** — the
`"genuinely not in the gate"` the issue used prints nothing at all, which is the
trap the last section of this file is about.

And that the decision is findable by text rather than by pin:

```console
$ git grep -n "What this does not do" -- docs/findings/xdata-819-815-correction-chain.md
```

The gates that must stay green are
`python3 ec/tools/gen_findings_index.py --check`,
`python3 ec/tools/check_findings_frozen.py`,
`python3 ec/tools/check_no_append_logs.py`,
`python3 ec/tools/check_no_conflict_markers.py`, and
`bash .github/scripts/agent-gates.sh` — whose `doc links` gate resolves every
relative `.md` link, so every file this one names has to exist.

**`bash tools/run-tests.sh` is red on this tree and is not made greener by this
change.** It fails on
`ec/tools/test_check_cluster_citations.py::TheCommittedTree::test_committed_prose_matches_committed_census`
with three disagreements: the two at
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` that the `#820`
correction records, and one more since appeared at
`ec/annotations/xdata-register-map.md:2004` — *"census count disagrees for
`main-ec-002`: 31 named addresses in the census, 27 in the row"*. This branch
touches neither the suite nor either line, and adds no fourth disagreement. The
count moving from two to three is recorded as an observation, not corrected: a
disagreement about a printed transcript in a closed write-up is a judgement about
a record, and `xdata-green-set.md` already defers exactly that judgement for the
same two lines.
