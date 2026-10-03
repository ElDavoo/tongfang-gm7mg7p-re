# The census-regeneration exemption is keyed on the fenced block, not on the line inside it

(2026-10-03, issue #1454. Static reading and commands over committed text. No
capture opened, no EC, no hardware, no Windows. `status:` in
`ec/annotations/registers.yaml` is untouched.)

`check_cluster_citations.py` skips a unit whose fence runs
`ec/tools/xdata_register_map.py` under a flag that changes the census, because a
`main-ec-NNN` in such a block is a rank in a generation the reader cannot open.
The predicate that decides it read the tool name and the flag with a `[^\n]` gap
between them:

```python
REGENERATES = re.compile(
    r"xdata_register_map\.py[^\n]*--(?:no-eq-guard|export-ownership)\b")
```

`[^\n]` is the whole of the gap, so the flag had to be on **the same physical
line** as the tool name. The corpus does not write it that way.
`xdata-two-largest-case-restatement.md` writes it as a `subprocess.run` list
argument with the flag on the next line, twice, and
`xdata-cluster-key-round-trip.md` writes it that way once. Those blocks were not
scoped, which is the defect.

The gap is now `[\s\S]`. The fence, not the line, is the unit the exemption is
read in.

## Why the block is the boundary

`transcript_lines()` already did the joining. It hands `REGENERATES` the whole
body of each properly-paired block — `"\n".join(lines[open_at:close_at])` — so
the fence was the intended unit and only the pattern made it a line. Three
things follow for free, and each is a case:

- **The block is the ceiling.** Nothing in the pattern can reach past a closing
  fence, because the string it is searched in stops there. A predicate that
  searched the *file* would scope a claim in a neighbouring fence too; one that
  searches the block does not. The case puts the claim in a fence of its own,
  because a claim in running prose is reported either way and would check
  nothing.
- **A fence is still a paragraph boundary and still sentence-split.** That is
  #605's fix and it is untouched — `test_a_fence_is_still_split_into_sentences`
  holds unchanged. The widening is in the predicate, not in the walk.
- **An unterminated fence contributes no span at all**, so its lines go back to
  the ordinary walk (`pd-only-status-vocabulary.md` is the committed case).

## The accepted spellings, and which of them the old gap could not reach

A block can spell the command three ways, all of which appear in the committed
corpus and all of which the rule now accepts. Each is a fixture in
`TranscriptBlockScope` with a real membership error inside it:

| spelling | the flag falls on | `[^\n]` reaches it |
|---|---|---|
| `… xdata_register_map.py --no-eq-guard --out-clusters …` | the tool's line | yes |
| the same, continued with a backslash | the tool's line | yes |
| `subprocess.run([sys.executable, "ec/tools/xdata_register_map.py",` on one line, `"--no-eq-guard", …])` on the next | the following line | **no** |

**Perturbed, and watched for the red.** With `[^\n]` restored, the first two
stay green and the third goes red with **one reported problem** — the same
`MEMBERSHIP_ERROR` line the other cases carry, `0x06C6` held to `main-ec-003`
where the fixture census puts it nowhere. That asymmetry is the whole
justification for the third case existing; a case that cannot fail has not been
shown to check anything, and this is the page's own standard applied to itself.

**The rest were perturbed the same way**, each turning at least one case red:
the predicate searched in the whole *file* rather than the block body (the
ceiling case), the order dropped so a flag before the tool would also count (the
ordering case), `--map` admitted to the flag list, the flag dropped so the tool
name alone scopes, the flag alone scoping so the tool name is not required, and
the transcript skip removed from `skip_reason()`.

## What the widening does not do, and the decisions it takes

Two boundaries are stated rather than left to fall out of how the gap is
written, and each has a case.

**The tool name must come before the flag, in the same block.** Not symmetric:
an unordered predicate would also scope a block whose output names the flag
*first* and the tool it resolved anchors in, which is a block about where the
flag is defined rather than one that ran it. So the pattern stays ordered.

**Nothing in the committed corpus reaches that boundary**, which is why the case
for it is synthetic. The nearest shape is `xdata-no-eq-guard-citation-anchors.md`
— a `check_eq_guard_citations.py` transcript whose output names the flag before
the tool — but that block names the tool name again further down, so it is
scoped either way and the ordering makes no difference to it. Over every fence in
`ec/`, `docs/` and `evidence/`, an unordered predicate and the ordered one agree
on every block; the boundary is a decision about what the rule should mean, not
a repair of something the corpus gets wrong today.

**A flag in a block's output is scoped.** This is the decision the issue left
open, and the answer is *yes, it is*. The alternative — scope a command but not
its output — is not expressible over this corpus. `xdata-two-largest-case-
restatement.md` prints `main-ec-001 mode-oem-init -> jaccard=0.0000` as bare
output with no `>` prefix; `xdata-moved-ranks-427-pair.md` prints
`>   ok  --no-eq-guard flips exactly the 3 …`. A discriminator between those two
is a heuristic over whether a line starts with `>`, and an exemption keyed on
formatting rather than on what the block did is not one. **Deliberately not
added**, and revisited only against a corpus that writes its output
unambiguously, which is a different piece of work.

What the block is *about* is a separate question this rule does not ask, and
this widening is where the answer costs something. `--map` and `--check` are not
*scoping* flags — neither changes the census — but the scope is decided on the
block, so a block that runs the tool under a guard-off flag is passed over
whole and a membership claim printed by a `--map` or `--check` line beside it
goes with the rest. **That is new with this change, and only for the spelling
that puts the two commands on different lines**: with the `[^\n]` gap, a block
naming `--map` and naming `--no-eq-guard` on separate lines was not a match at
all, so the claim between them was adjudicated and reported. Reproduced by
running each tree's tool over one such block carrying a real membership error —
the suite's `MEMBERSHIP_ERROR` — and diffing: `problems: []` after this change,
one `membership` problem before it.

The committed corpus does not reach that shape, and the reason is worth more
than the fixture that pins it: **every committed block naming both a
census-changing flag and `--map`/`--check` puts the tool and the flag on one
physical line, so every one of them was already matched before this change** and
none of them moves the run's output. That is the same coincidence of today's
prose this page keeps returning to, and it is why `TranscriptBlockScope` now
carries the mixed fixture as well: the boundary needs a witness the corpus does
not supply.

**The other half is unchanged and is the half that is about the committed
census.** A block naming `--map` or `--check` and *no* flag that changes the
census is not scoped, and a membership claim in it is reported.

**The narrowing that would have kept the old sentence true was rejected, and
the corpus says why.** "A block naming `--map` or `--check` is not scoped by a
guard-off flag elsewhere in it" makes the pre-change wording accurate by
un-scoping blocks whose only `--map` mention is not a separate command at all:
`ec/annotations/xdata-register-map.md` runs
`--no-eq-guard … --map ec/annotations/xdata-clusters.csv` as **one** command, and
`--map` there is how that guard-off generation is diffed against the committed
census, so the block is a regeneration and not a claim about the committed one —
and `xdata_register_map.py` refuses `--no-eq-guard` with `--check` and
`--self-test` but **not** with `--map`, so that combination is a legal command
and not a slip. A second committed block names `--check` only in its output
(`xdata-no-eq-guard-citation-anchors.md` prints "the `--check`/`--self-test`
refusal"). Naming a committed-census command therefore does not mean the block
is about the committed census, and that narrowing would let a block escape the
exemption by mentioning one — the defect this issue is filed against, arriving
by another route.

**Both the tool name and a flag are needed.** Neither half alone scopes
anything, and the corpus has both halves alone: a transcript that passes
`--no-eq-guard` as a `git grep` argument names the flag and never the tool, and
a names-summary line names `(--export-ownership)` in running text inside a fence.
This is why the fix is not "search the file for the flag", and it is what stops
the widening from becoming a blanket fence-drop.

## What this changes on the tree, honestly: nothing the run prints

**This fix has no run-visible witness here, and the tool's own stated failure
mode is why that has to be said rather than glossed.** A claim that reads
correctly and means nothing is invisible.

`python3 ec/tools/check_cluster_citations.py` exits 0 before and after, and its
`skipped:` line reads the same both times — checked by running each tree's own
tool over one byte-identical copy of the corpus and diffing the two lines. The
reason is mechanical, and it is *not* that anything adjudicated the newly-scoped
blocks: the two `two-largest` blocks name `main-ec-001` and `main-ec-002` and no
other cluster id, but no unit inside either names a `0x` address at all, so each
is dropped at `if not addresses: continue` before `skip_reason()` is ever
reached. The other two newly-scoped blocks name no cluster id either. That is a
coincidence of today's prose, not a property of the rule.

**The one-line perturbation that shows the old tool was wrong**, then: put a
`0x` address that the registers CSV knows beside either
`main-ec-001 mode-oem-init -> jaccard=0.0000` line, and the pre-change tool
holds a guard-off generation's rank to the committed census — the red the issue
was filed for. The suite is what witnesses the fix, because a fixture cannot
depend on a page staying as it is.

**And the population is not a figure.** The walk that finds the blocks the
predicate matches is `fence_spans()` over the committed markdown; the run that
prints the skips is the command above. Neither a count of blocks nor a count of
files is recorded here, because a corpus that gains a write-up moves both, and a
number every merge has to edit is a number that will be wrong. What is a
property of the *rule* rather than of the tree is that it now matches every
spelling the corpus uses — and that is what the cases assert.

The correction this owes the page it supersedes is written there, in place:
`docs/findings/guard-off-transcript-scope.md` carried a block count as its own
measurement, and the count was the regex's rather than the corpus's.

## What this is not

- **Not a new tool, a new mode, or a new skip reason.** `SKIPS` keeps its three
  entries and `TheSkipListHasOneSource` is unchanged; the fix adds no reason, it
  widens the predicate that produces an existing one.
- **Not an EC, BIOS or Windows claim.** Every figure here is a command over
  committed markdown and two committed CSVs. No `status:` moved.
- **Not a change to the pages that were misread.**
  `xdata-two-largest-case-restatement.md` and `xdata-cluster-key-round-trip.md`
  are correct as written; the tool was reading them wrong. Rewriting a page to
  suit the old regex would hide the defect rather than fix it.
- **Not a fix for the other red suites.** They are separate defects with their
  own owners, and this branch does not claim to have moved any of them.