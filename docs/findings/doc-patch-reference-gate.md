# The names prose gives a prepared gate patch, and what now holds them (issue #777)

Issue [#777](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/777) was
opened by the follow-up pass off #755. `check_doc_links()` reads markdown
*links* and nothing else, so it finds 686 `.md` link references and **zero**
references to a patch, while `docs/ci/agent-gates-*.patch` is named in prose 53
times across 16 markdown files — every figure in the census below measured at
`271389d`, and every one of those names worth exactly as much as the file it
names. A `git apply` instruction a human copies out of a header is only as true
as the name beside it, and the name is the part nothing held.

This adds `tools/check_doc_patch_refs.py` and its suite. It is a check over
committed text and nothing else.

**None of this is a live test, and none of it is evidence about the firmware.**
The failure being prevented is a stale name in a sentence, which is visible from
a checkout: no EC is opened, no register is read back, no capture is taken, no
`status:` in `registers.yaml` moved, no CSV or Ghidra export regenerated, and no
laptop, EC or Windows machine is involved anywhere below. The one prepared gate
patch this touches is none of them — `.github/scripts/agent-gates.sh` is
template-copied and the pipeline token has no `workflow` scope, so the wiring is
a recipe below rather than an edit.

## What the tree actually holds

Every figure is a `grep` on the tree at `271389d`, and the commands are here so
a reader re-derives them rather than trusting them.

```
$ grep -rEo '\]\(([^:)]+\.md)\)' --include='*.md' . | wc -l              # 686
$ grep -rEo '\]\(([^:)]+\.patch)\)' --include='*.md' .                    # 1
$ grep -rnoE '`(docs/ci/)?agent-gates-[A-Za-z0-9._-]+\.patch`' \
      --include='*.md' . | wc -l                                          # 53
$ grep -rlE '`(docs/ci/)?agent-gates-[A-Za-z0-9._-]+\.patch`' \
      --include='*.md' . | wc -l                                          # 16
$ grep -rnoE '`docs/ci/agent-gates-\*\.patch`' --include='*.md' . | wc -l   # 8
```

The per-file split, because which file a reference is in decides how expensive a
fold is:

| file | name references |
|---|---|
| `docs/findings/prepared-gate-patches.md` | 14 |
| `docs/findings.md` | 9 |
| `docs/agent-pipeline.md` | 6 |
| `docs/findings/disasm8051-self-test-gate.md` | 5 |
| `docs/findings/0751-grader-self-test-gate.md` | 4 |
| `ec/tools/testdata/README.md` | 2 |
| `docs/findings/xdata-decile-small-set-contract.md` | 2 |
| `docs/findings/testdata-index-feeds-and-call-graph.md` | 2 |
| `docs/findings/testdata-index-check.md` | 2 |
| `ec/README.md` | 1 |
| `docs/findings/testdata-third-column-claims.md` | 1 |
| `docs/findings/testdata-index-suite-count-floor.md` | 1 |
| `docs/findings/prose-line-citations-held.md` | 1 |
| `docs/findings/citation-gap-scan.md` | 1 |
| `docs/findings/0751-early-exit-row.md` | 1 |
| `docs/findings/0751-capture-row-shape.md` | 1 |

### Four corrections to the issue, stated rather than folded in

1. **`check_doc_links()`'s discovery finds 686 `.md` link references at
   `271389d`, not 213.** The issue's number is a measurement of an older tree.
   The conclusion it supports is unchanged: zero of them are `.patch`, because
   the pattern ends in `\.md`.

2. **The backticked population is 53 references across 16 files, not 34 across
   9.** The difference is the **bare spelling** —
   `` `agent-gates-capture-claims.patch` `` with no `docs/ci/` in front of it —
   which is 19 of the 53, and it is not optional: it is how a table row's first
   cell and a sentence naming one specific file have to be written.
   [`prepared-gate-patches.md`](prepared-gate-patches.md)'s measured-results
   table is a bare-spelled row, and so is its "Left out on purpose" sentence.
   **A checker built on the issue's `docs/ci/`-only pattern would pass this tree
   while holding 64% of the references, and would not see three of the four
   deliberate ones at all.** Discovery has to match both spellings.

3. **There are 8 glob-shaped references** — `` `docs/ci/agent-gates-*.patch` ``,
   one each in `tools/README.md`, `docs/findings.md`,
   `docs/findings/walk-window-terminators.md`, `doc-figure-pin-audit.md` and
   `disasm8051-self-test-gate.md`, and three in
   `docs/findings/prepared-gate-patches.md`. They are prose describing the
   *set*. A pattern loose enough to match a bare name matches these too, so the
   character class has to exclude `*`; the suite pins the shape so a future
   loosening fails rather than reports a file nobody named.

4. **The deliberate population is 4 markdown references to 2 distinct absent
   names**, not "three of the 34". `agent-gates-testdata-index.patch` at
   [`prepared-gate-patches.md`](prepared-gate-patches.md)'s table row, the
   paragraph under it, and `docs/findings.md` §43; plus
   `agent-gates-claims-and-testdata.patch` at that same write-up's "Left out on
   purpose" sentence. Only **one** of the issue's 34 qualified references names
   an absent file — the other three are bare-spelled and so sit outside its
   count. Separately, `tools/test_agent_gates_patches.py` names the deleted
   patch in three more places (its module docstring and the `FoldTests` failure
   message). That `.py` population is a follow-up, not something to widen this
   into: the checker is scoped to `*.md`, and a wider scan would put this tool
   inside a file issue #772 owns.

### The one genuinely new thing the issue's headline implies and does not mention

There is **a real markdown *link*** onto a patch —
`docs/findings/xdata-census-self-test-gate.md` →
`../ci/agent-gates-disasm8051-self-test.patch` — and
`check_doc_links()` cannot see it, because its pattern ends in `\.md`. It is
the census's one, and a link rather than prose is the class. **The merged tree
carries two**: #942 added `docs/findings/pin-table-row-reconciliation.md` →
`../ci/agent-gates-pin-table-rows.patch` beside it, which is why the checker's
own link assertion is pinned to two rather than the one this branch measured.
That is the case where extending the gate's *link* discovery, as the issue's
title asks, reaches something no prose grep would: a link is what a reader
clicks, so its breakage is a 404 rather than a sentence that quietly stopped
being true. The checker reads both spellings for that reason and for the
bare-spelling reason above.

## The historical-reference rule, decided

The issue offers two shapes: an explicit opt-out at the reference, or a
fenced/quoted span the reader can see is describing rather than instructing.
**The shape taken is a third one: an enumerated set in the checker, keyed on the
patch *name*.**

```python
HISTORICAL = {'agent-gates-testdata-index.patch',
              'agent-gates-claims-and-testdata.patch'}
```

Four reasons, and the fourth is the one that decides it.

1. **The opt-out has to be written into prose that is a record.** Three of the
   four deliberate references *are* history: §43's sentence describing the
   `capture-claims`/`testdata-index` collision, and the measured-results table
   row in [`prepared-gate-patches.md`](prepared-gate-patches.md) whose entire
   content is the name of a file as it was before the fold. `CLAUDE.md` §4a-4d
   is that a superseded claim stays visible with a correction beside it.
   Re-shaping a record so a checker can see it is that edit under another name.

2. **A fenced or quoted span is a presentation change, and this tree is full of
   `file:line` pins.** Fencing the table row and the §43 sentence moves lines in
   two of the most-cited files here, and
   `ec/tools/census_test_line_pins.py` exists because pins that move silently
   are the defect. The enumeration buys four untouched lines by editing **zero**
   of the sixteen citing files — which is also what keeps this PR modular.

3. **The enumeration is the only shape that can be checked in both directions**,
   which is the `tools/test_readme_suite_table.py` arrangement the issue names
   as the model and the reason that suite exists. For each key the suite asserts
   that it is *still absent* from `docs/ci/` — a patch by that name reappearing
   makes the entry stale — and that it is *still cited* by at least one markdown
   file, so the reference being edited away makes it stale. Both failures name
   the key. A fourth absent name is refused, so the exemption cannot widen
   silently. The checker refuses the same two conditions at run time rather than
   only in the suite: an exemption that has stopped earning its place and keeps
   passing is the silent-pass shape this repository keeps writing suites about.

4. **Keyed on the name, not `file:line`.** A line number moves under every edit
   to a growing file — the whole subject of the eighth-thing paragraph in
   `tools/README.md` — so a key that moves is a key that rots.

**The bound, stated not hidden:** any *new* reference to one of those two names
is exempt by construction. That is the intent. The exemption is two names wide
and held in both directions, and this is a cost of the shape rather than a defect
in it.

The **live** direction is checked too, mirroring the sibling: every patch in
`docs/ci/` must be cited by at least one markdown file. All six are, in 3–11
files each. A human adding a seventh prepared patch and documenting it nowhere
is the mirror failure, and it is the half that broke in the sibling.

**No count is asserted anywhere** — not by the check, not by the suite. The
reason is `tools/test_readme_suite_table.py`'s own docstring: an expected count
turns every added test into a failure. The suite asserts non-emptiness and
cleanliness instead, which are claims about the tree rather than about the tool.

## The check, and the refusals the suite pins

`tools/check_doc_patch_refs.py` — **standard library only**, which is the gate's
test: `argparse`, `collections`, `contextlib`, `io`, `re`, `shutil`, `sys`,
`tempfile` and `pathlib`, and no third-party import, so it costs a `python3` and
nothing to install. Two
modes in the house shape, `--check` (non-zero on a stale reference, an uncited
patch, a dead historical key, **or a discovery that found nothing**) and
`--self-test`, plus `--verbose` for the line number. It prints its scope and its
measured population on every run, the way `tools/run-tests.sh` prints what it
ran, because a reader holding only the exit code should still be able to tell a
clean tree from a pattern that stopped matching.

`tools/test_doc_patch_refs.py` — 22 cases, discovered by
`bash tools/run-tests.sh` with no wiring. Every case is a way the check can be
wrong in the direction that matters:

- **The parse, on inline text**, so the set comparison is not one bad regex away
  from passing vacuously: both backtick spellings, a glob-shaped span, the
  `.yml` sibling, a link resolved to its last path component, a URL refused,
  and one line in both spellings counted as two references.
- **The refusals, on trees small enough to read the whole finding list:** an
  absent name reported by name *and* by citing file, a fourth absent name
  refused, a patch nobody names reported, `--verbose` naming the line and the
  default not, and an empty tree refused rather than read as clean.
- **One case per historical key, in both directions** — still absent, still
  cited — plus one case demonstrating that each direction goes red when broken
  on a `tempfile` copy of the committed tree.
- **The rename case**, on a copy of the committed tree rather than a fixture,
  because "the gate goes red for *every* stale reference" is a claim about this
  tree's references. Renaming `agent-gates-0751-self-test.patch` there goes red
  on every one of that name's references across every file that carries one, and
  on the renamed file being uncited — the two reported separately, because a
  reader who fixed the first has not fixed the second. **Neither the self-test
  nor the suite prints how many there are**, and that is deliberate rather than
  an omission: the count is a function of the tree the run happened on, so
  quoting it here would add a reference to this file and make the next run read
  higher. What is pinned is the relation — every reference, list-compared
  against the tree's own — and the case separately refuses a target with one
  reference, so "every" cannot be satisfied by a degenerate population.
- **The committed tree**, measured rather than asserted: not empty, no stale
  reference, no uncited patch, no dead key, and both markdown links onto a
  patch resolving to files on disk.

Each case was checked against the mutation it is meant to catch. Dropping the
bare spelling from the pattern — the issue's own shape, and the one correction
above that matters most — turns **10 of the 22** red rather than quietly
shrinking the population.

## The gate wiring, prepared rather than landed

`.github/scripts/agent-gates.sh` is copied from the `agent-pipeline` template and
the pipeline's push token has no `workflow` scope, so a branch editing it fails
at the *end* of a PR rather than the start. `docs/agent-pipeline.md` items 4
through 12 each repeat that reason, and the recipe is item 13 in the same shape:
a `check_doc_patch_refs()` function and a `gate` line beside `check_doc_links`,
with the whole of it carried in the document so a template re-copy brings it
across.

By cost and kind it belongs in the cheap tier: it reads markdown and one
directory, needs only `python3` and the standard library, and opens no firmware,
no `.c` and no `.asm`.

**No `docs/ci/agent-gates-*.patch` was added for it, and that is a decision with
a reason rather than an omission.**
[`prose-line-citations-held.md`](prose-line-citations-held.md) took this exact
decision for the `tools/run-tests.sh` wiring and recorded it in prose; this
follows that precedent rather than inventing one. A seventh patch would need a
`gate` line at the same seven-line list's anchor where
`agent-gates-capture-claims.patch` and `agent-gates-testdata-row-claims.patch`
already insert — item 12 takes the *head* of that list for exactly this reason
— and two patches that each apply alone and do not compose is the failure
`tools/test_agent_gates_patches.py` exists to catch. The file would also have to
be added to that suite's held `PATCHES` set, which issue #772 owns. The prepared
patch is the right next step; a gate line here is not this issue's to land.

## The transcript

Read off a run on this tree, not carried forward. The census above is
`271389d`'s — 53 across 16, backticked names only — and this is the checker's
own measure of the merged tree, which counts the markdown links as references
too: **71 across 20**, the two links being #942's write-up and this issue's,
one each. The growth between them is this write-up, the new
`docs/agent-pipeline.md` item 13, and #942's
`agent-gates-pin-table-rows.patch` with its five citing files — every one of
which names patches in order to describe a check. That is the shape of the
growth the check is for, and it is why no figure above is a floor.

```console
$ python3 tools/check_doc_patch_refs.py --check
every `*.md` under the repository root, patch names against docs/ci/, 2 historical key(s) exempt
71 name reference(s) in 20 markdown file(s), 2 link(s) in 2 file(s); 2 historical key(s), 2 still absent and 2 still cited; 6 patch(es) in docs/ci/
$ echo $?
0
```

```console
$ python3 tools/check_doc_patch_refs.py --self-test
  ok   both spellings are read, the bare one included, and a link is a link
  ok   three references on that text, so neither the glob-shaped span nor the `.yml` sibling contributed one -- the `*` is outside the character class and the extension is part of the pattern
  ok   a line carrying one name in both spellings is two references, in the order they were written
  ok   an absent name is stale and the finding carries the name and the citing file
  ok   and the run is red
  ok   one of the two is on disk and one is not: only the absent one is stale
  ok   the live direction is the other half of the same run, and the patch that is on disk is cited, so nothing is uncited
  ok   a patch nobody can find is reported -- the direction that broke in test_readme_suite_table.py
  ok   and it is red
  ok   the default report names the name and the citing file
  ok   and --verbose names the line it is on

  ok   the copied tree holds agent-gates-0751-self-test.patch to rename
  ok   renaming it makes every reference to that name stale and nothing else stale
  ok   and every one of them is reported, in the order the tree holds them -- a check that stopped at the first would leave the rest to the manual sweep this exists to end. The count is deliberately not printed here: it is a count of references to the target *in whatever tree this was run on*, so pasting this line into a document would add one and make the next run read higher. `test_doc_patch_refs.py` is where the shape is pinned, and it pins it without a number too.
  ok   and the run is red: the stale references plus the renamed file, which is now uncited
  ok   while the copy before the rename is clean, so the red is the rename's and not the copy's

  ok   `agent-gates-claims-and-testdata.patch` is refused when it is restored: the exemption has stopped earning its place, and the failure names the key rather than counting it
  ok   `agent-gates-testdata-index.patch` is refused when it is un-cited: the exemption has stopped earning its place, and the failure names the key rather than counting it

  ok   a tree with no markdown naming a patch is found empty
  ok   and --check exits non-zero on it, so 'found nothing' cannot be read as 'found nothing wrong'

  ok   the committed tree is not empty: 71 name reference(s) in 20 file(s) and 6 patch(es) in docs/ci/
  ok   and the two markdown links onto a patch are found: docs/findings/pin-table-row-reconciliation.md, docs/findings/xdata-census-self-test-gate.md
  ok   and the committed tree is clean

  all assertions passed
$ echo $?
0
```

```console
$ python3 tools/test_doc_patch_refs.py
......................
----------------------------------------------------------------------
Ran 22 tests in 1.437s

OK
```

## What this does not do, and what a new question opens

- **The `.py` population.** `tools/test_agent_gates_patches.py` names the deleted
  patch in three more places. Recorded as a follow-up rather than widened into a
  file issue #772 owns.
- **Whether a reference's sentence is instructing or describing.** That is what
  `HISTORICAL` stands in for, at name granularity. The cost of getting it wrong
  is a false positive a reader can see and an edit to make — not a silent pass.
- **The patches themselves.** Whether each applies is
  `tools/test_agent_gates_patches.py`'s, and whether its header names itself is
  its case 6. The two hold different surfaces and do not edit the same case.
- **Anything about the laptop.** No EC, no capture, no register, no Windows box.
  Nothing here needs `needs-hardware-test` and no live run is implied.
