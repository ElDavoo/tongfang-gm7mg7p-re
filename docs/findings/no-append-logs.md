# A document every merge must edit is a lock nobody holds, and this repository has now hit that three times

(2026-09-27. Static reading of committed files plus `git log` over the first
parent. No image is opened, no register is read back, and no laptop, EC or
Windows machine is involved: every figure below is a count of lines in files in
this repository, and each is given with the command that produces it.)

## The claim

**A shared document that every change is required to edit does not degrade
gracefully. It becomes a lock that nobody holds, and the symptom is always the
same: the second concurrent merge collides in the same hunk, and the resolution
is prose about the collision rather than the two changes themselves.**

This is not a hypothesis about documentation in general. It is a measurement of
this repository, taken three times, in three different files, over a period of
weeks. Each time the shape was the same, each time the file had to be rescued
by a different mechanism, and the three mechanisms are now all in the tree
holding the three cases:

| # | file | what every merge had to do | lines it reached | held by |
|---|---|---|---|---|
| 1 | `docs/findings.md` | append a summary section | 12,690 lines, 97 sections | `check_findings_frozen.py` |
| 2 | `tools/README.md` | correct a hand-kept total in place | 3,680 lines, of which **3,522 were correction notes** | `tools/test_readme_suite_table.py` |
| 3 | `docs/findings/test-line-pin-census.md` | append a dated `## The #NNN merge` section | 4,570 lines, of which **1,924 were sixteen dated sections** | `ec/tools/check_no_append_logs.py` |

The three are the same defect wearing different clothes, and the reason they are
worth one write-up rather than three is that **the fix is the same fix**: give
the document nothing to correct, and the collision has nowhere to happen.

## What each one cost, measured

**`docs/findings.md` — the section counter.** 51 clauses in the file read as
"the last section in the file", against a rule the file had itself written down
twice forbidding them. The count is now frozen at 97 and `check_findings_frozen.py`
fails an addition, a deletion, a renumbering and a reused number. The count is a
ceiling *and* a floor deliberately: a ceiling catches the addition, which is the
conflict, and cannot catch a deletion, because a file one section short is
indistinguishable from one that always was.

**`tools/README.md` — the hand-kept total.** The lead sentence read *"There are
forty-nine today, 1561 tests in all"*. Under it sat **22 supersession notes over
3,522 lines and 40,240 words** — 24% of the file — each one a paragraph
explaining the new arithmetic. Three details make this the clearest instance of
the three:

- **The note ordinals disagree with one another**: *ninth, tenth, third, fourth,
  fifth, sixth, sixth, seventh, seventh, ninth, tenth, seventh, ninth, tenth*.
  That is the signature of branches numbering their own note without seeing the
  others'.
- **Two of the notes are the same paragraph re-derived on opposite sides of one
  merge**, which is the collision itself, written down twice.
- **The chain had outlasted its own usefulness**: it records figures from trees
  that no longer exist, and one of them names a commit, `a9b3b90c`, that **is
  not an object in this repository at all**.

It is also the instance with the sharpest lesson attached, because
**`docs/findings/tools-readme-totals.md` already existed and had already
diagnosed it.** Issue #817 asked exactly this question and the write-up says
what is wrong with the sentence. The chain then grew anyway, for weeks. The
diagnosis was right and the fix was never made, because **the sentence was
still there to be corrected** — and a correct diagnosis does not remove the
thing it diagnoses. That is the argument for a gate over an argument in prose,
and it is the same argument `docs/findings.md` §4 makes about its own two
written-down rules being violated 51 times.

**`docs/findings/test-line-pin-census.md` — the per-merge section.** Sixteen
`## The #NNN merge, <date>` sections, one appended by every merge that touched
the per-pin table, 1,924 lines. At 22 edits in 40 merges it was the most
frequently edited document in the tree once `docs/findings.md` was frozen. It
also carried the shape one level down: **two table cells held 1,068 and 347
words**, tracking twenty and five re-registrations of a single row's line
number — every one of them caused by a *supersession note about the runner's
test totals* rather than by anything about the claim the row reconciles. One
row's line number had been moved by unrelated bookkeeping eleven times.

## Why the three mechanisms are the same mechanism

Each case is fixed by removing the thing there was to correct:

- `docs/findings.md` cannot be appended to, so there is no hunk to collide in.
- `tools/README.md` states no total, so there is no figure to re-derive, so
  there is no paragraph to append beneath it. The total is
  `bash tools/run-tests.sh`'s last line and the file says so.
- The census file's per-merge sections are gone, so a merge that re-anchors a
  row changes a row and nothing else.

In every case the content that was *reasoning* stayed and the content that was
*chronology* went to git, which already had it at every line.

## The same lock, in code

The three above are documents. The fourth instance is not one, and it is the
clearest of the four because it cost four PRs at once rather than one.

`ec/tools/test_check_pin_table_by_cited_file.py` asserted three numbers where
one is a claim:

```python
self.assertEqual(len(files), 59)
self.assertEqual(len(files) - len(tail), 12)
self.assertEqual(len(tail), 47)
```

The middle one is the finding: **twelve of the indexed suites are named by a
`test_*.py:NNN` somewhere in committed markdown.** That is a fact about the
corpus, it moves only when a write-up starts citing a line of a suite, and it
is the axis the method exists to hold. The outer two are a census of the tree.
Each takes one on every merge that lands a suite and its write-up, whichever
side of the tail the new suite starts on.

On 2026-09-27, with seven PRs open, **four of them had each bumped those two
numbers by one from a different fork base** — 56, 57, 57 and 58 — and each had
rewritten the comment above them to explain its own arithmetic. The file
conflicted in **18 of 21** branch pairs, and it was the only file in the tree
that conflicted broadly. Every resolution had to re-derive a number nobody had
claimed.

The comment block three lines above the assertions already recorded that the
same mistake had cost that method **351 lines** of step history in prose, and
had been cured. Three lines below the cure, a changelog had been appended
again. The prose was cut and the numbers stayed, because they looked like
figures rather than like a lock, and a figure in a test reads as a test.

The fix is the same one as the other three: **remove the thing there was to
edit.** The two absolutes are gone; the claim stays. Measured rather than
assumed — merging each of the four branches leaves `pinned` at 12 while files
and tail each take one (60 / 48 / 12 in all four merged trees), which is
exactly the axis and nothing else.

## What the contention produced, when it lost

A merge conflict that is committed rather than resolved is the worst thing this
repository can produce, and it is invisible by construction: git stores
`<<<<<<<` as ordinary content, so every merge after it treats the three lines
as text. `tools/README.md` carried one inside its own suite table from
`90287fec` (#1089) until #1163 removed it — and nothing noticed for the weeks
between. Not the review stage, not the gates, and not
`tools/test_readme_suite_table.py`, which asks whether every suite has a table
row and was therefore *satisfied* by a row sitting inside the block.

It nearly survived a second time, and the reason is worth stating because it is
the general hazard. The incoming side of that block had **dropped** a row the
outgoing side kept, and the mechanical resolution — `git checkout --theirs`,
the reflex — would have deleted `test_walk_flow_follow.py`'s entry and failed a
suite that was not watching. #1163's resolution is the correct one: it keeps
the corrected `test_walk_budget_census.py` row and re-adds the dropped one.
**Resolving a conflict is a reading, not a merge**, and
`ec/tools/check_no_conflict_markers.py` now holds the outer two markers against
every committed file. The `=======` is checked only in a file that carries one
of them, because markdown spells a setext heading with a line of `=` and a rule
that fires on correct text is a rule that gets deleted rather than fixed.

## The boundary, because a rule that misfires is worse than no rule

Two distinctions do all the work, and both were checked by firing the new tool
at text that should pass:

**A log is not a claim, and §4a-4d is about claims.** The rule that a wrong
version stays visible beside its correction is a good rule and it stays. It
applies to a charge-cap figure, an "this register is absent" reading, a
superseded count a reader would otherwise take at face value. It does not apply
to a record of what each merge did to a sentence — that is a log, and `git log
-p` is the log. **This distinction was got wrong the first time here**: the
`tools/README.md` chain was moved verbatim into a findings file "so nothing is
lost", which preserved nothing git had not and created a second copy the next
merge would have to keep in step. It was corrected the same day, and the file
now carries the rule and points at history instead.

**A section may cite a merge; a section may not *be* one.** Most sections in
this repository reference an issue or a merge while being about something else —
*Why no checker*, *What the merge moved, and what it did not* — and those are
sections of the document, not sections per merge. `check_no_append_logs.py`
requires both a merge word and an issue-or-date reference in the heading, and
has a third clause exempting headings that open with *why* / *what* / *how* /
*the measurement* and the rest of that list. It also strips inline code spans
first, so a document that **names** the marker it forbids is not one — without
that, `CLAUDE.md` and the tool's own docstring would each fail it, which is the
fastest route to a check everybody disables.

## Where the notes the rule cannot see ended up instead

`python3 ec/tools/check_no_append_logs.py` exits 0 on this tree, and a tree
carrying merge notes is not a contradiction — it is **a divergence of reach**.
Each of the three limits the rule states about itself leaves notes somewhere it
cannot see. They are decisions, not defects, and the notes are wanted; this
section is where they ended up, so the next branch that appends one knows where
the accumulation is and is not the first to find out.

- **`heading-depth`** — `HEADING` is `re.compile(r"^##\s+(\S.*?)\s*$")`, so a
  merge heading at `###` is a section per merge the rule never looks at.
  `docs/findings/test-line-pin-census.md` carries `###` merge headings at `:2887`
  and `:2945`, both out of the reach of the rule that removed that file's dated
  `##` sections on purpose.
- **`outside-scope`** — `is_findings()` exempts `docs/findings/` wholesale from
  the supersession rule. That is §4a-4d doing its job, and undoing it is nobody's
  business here. It is also the limit that leaves a findings document's own notes
  in the tree and out of the rule's reach at the same time.
- **`marker`** — the rule's vocabulary is one string,
  `SUPERSESSION = re.compile(r"\*\(Superseded\b")`. This repository's merge notes
  spell themselves `*(Merged-tree note …)*`, with an ordinal in front when a
  document grew more than one, and neither spelling matches.

Two of those are the failure above reproduced rather than a near miss.
`docs/findings/doc-figure-pin-audit.md` carries a run of them appended at one
spot — one unnumbered, then *Second*, *Third*, *Fourth* and *Fifth*, one per
merge — which is the same signature as `tools/README.md`, rebuilt in the
directory the rule exempts. And `docs/findings.md` carries inline notes of that
shape in the one file `check_findings_frozen.py` exists to close: the freeze
holds the section count and the numbering, and by its own docstring it does not
check prose inside a section, so an inline note is legal there and is where the
chain now grows.

**The notes are not the defect, and none of this is an argument for deleting
them.** §4a-4d is a real rule and a reader of a finding wants the history. What
the defect is, narrowly, is that the corrections accumulated where the rule
could not see them — so nothing ever told the branch that had just appended one
that it was appending another. **Widening the rule is not the fix**: reading
`###` and covering `docs/findings/` would fire on every note named above and turn
a green gate red on a tree that is not defective. The rule stands as written.

The rule for the next merge is already written down, in the section of
`docs/findings/test-line-pin-census.md` that holds its per-pin table:

> **Do not recreate the log.** A correction to this table is a row change plus,
> where the reasoning matters, a paragraph in the section it belongs to. It is
> not a new dated section.

A correction whose *subject* is a merge is still a correction: it belongs in the
section the claim it corrects lives in. This section is a worked instance of the
thing it forbids — a dated heading here would be one more note in
`docs/findings/test-line-pin-census.md`, out of the rule's reach in exactly the
way the ones named above are.

**And this list is a reading, not a census.** It was found by reading the
documents the rule walks, and every negative it carries is **not found by this
method**, never absent: setext headings are not read as headings by anything
here, a parenthetical note carrying neither the rule's vocabulary nor this
repository's merged-tree one is in neither population (`README.md:46` is one),
and a correction chain kept in a commit message is not in the documents at all —
`git log -p` is where that history is.

## What this does not claim

**Digits are not the problem, and a rule against them would be the wrong rule.**
The figures that describe *the machine* — `0xB158`, `0x6E78`, the 12,690 lines
of `docs/findings.md` — are the research output, and removing them would remove
the work. The figures that rotted were a different class: **counts of things in
this repository**, which change on nearly every merge and are therefore wrong
within one. Measured across the 199 markdown files in the tree, 161 of them
carry at least one such figure and there are **1,806 in total**. That is 531
fewer than the same scan found before this change, and the difference is worth
naming: `docs/findings/tools-readme-totals.md` held **430 of them on its own** —
the file this write-up's own first draft created, and then the single largest
concentration in the tree — and holds 42 now that the chain is in git where it
was already. `docs/findings.md` holds 263 and is frozen, so it is inert.

Of those 1,806, the ones that caused the three conflicts above number about
fifty. The rest are not harmful where they sit, because a per-topic write-up
under `docs/findings/` is one topic with one owner, not a place every merge
touches. **The dividing line is not "has a number in it" but "does every change
have to edit this line"**, and that is why the enforcement is a shape test over
headings and one marker rather than a scan for numerals.

`docs/findings.md` states a repository-counting figure 263 times and is not this tool's
business: it is frozen, so nobody can add to it and the repetition costs
nothing. That is the whole shape of the finding — **a number in a document
nobody can edit is harmless, and a number in a document everybody edits is a
merge conflict wearing a footnote.**

## Left open

- The census file's *prose* still restates the same four figures in roughly
  sixty places, some saying `106` and some `107`, each true of the tree it was
  measured on. A note at its head now says which set is this tree's. Cutting
  the rest is a larger edit than this change made and is not attempted here.
- `ec/tools/README.md` does not exist, so there is no inventory of tools there;
  `tools/README.md`'s table is the one, and it is now 176 lines with no total.
- Nothing yet prevents a *new* shared document from being introduced and then
  edited by every merge. The rule is in `CLAUDE.md` and the three cases are
  held; the fourth would be caught only once it had already grown, which is the
  same standing as every other gate here.
