# Source-line citations, held to a named anchor instead of a line (issue #868)

Issue [#868](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/868) asked
for a checker for the pointer class `check_citation_lines.py` said was a
different tool, and named the sentence it had already found wrong:
`ec/annotations/xdata-086x-dispatch.md`'s live paragraph, which cited
`HAND_CHECKED["0x0860"]` and a "hand-checked direction oracle" assertion in
`ec/tools/xdata_register_map.py`. This is that checker, that sentence's
retraction, and the census of the class.

**None of this is a live test, and none of it is evidence about the firmware.**
The whole of it is a read of committed text: no EC is opened, no register is
read back, no capture is taken, and no laptop, EC or Windows machine is
involved. A line number into `ec/tools/xdata_register_map.py` is a statement
about a source file this repository reads, not an observation of a byte. No
`status:` moved — `XDATA_0860` stays `present-untested` — no count, bucket or
`refs:` figure moved, and no census CSV or Ghidra export was regenerated. The
census figures the dispatch page carries are unchanged, because only a claim
about their *provenance* was wrong.

## The sentence the issue found, and what it turned out to be

The issue's finding was that two pointers landed on the wrong code. Measured on
this tree, the stronger claim holds: **both cited subjects no longer exist.**
`HAND_CHECKED` is not in the tool at any line — not at the `:770` the sentence
gave, and not at the `:1399` the issue proposed instead. `COREADING_CHECKED`
went the same way. They were deleted, and the comment left where they stood
records why:

> The per-address hand oracles that stood here (`HAND_CHECKED` for the
> direction buckets, `COREADING_CHECKED` for the co-reading columns) held
> reference counts, and a count of an address moves whenever a routine that
> touches it is seeded. The direction rule is held by `CLASSIFIER_SHAPE`'s
> literal snippets above and by the corpus-wide invariant below.

So this is a **retraction and not a re-point**: there is no line that would
make the sentence true again, and the wrong figures stay visible in the
correction blockquote per §4a-4d. What the row's provenance actually is today is
worth stating plainly rather than leaving a reader to work out:

- `CLASSIFIER_SHAPE`'s literal snippets hold the classifier's **shapes**, on
  synthetic snippets — narrow, and not a count of any address;
- the corpus-wide direction invariant holds a **per-occurrence** property over
  the whole tree — that every occurrence the census buckets `write` or
  `read+write` has an assignment and not a `==` after the address, measured by a
  second pass that does not re-implement the classifier. Against the pre-fix
  classifier it fails naming `0x0860` and `0x0440`;
- what re-derives *these* figures per site is `check_site_census.py`'s
  correspondence against the census, which recomputes each bucket from the
  census's own `classify()`. That is a cross-check on the classifier's inputs,
  **not** an independent hand count.

Neither of the first two holds a per-address count, and the tool's own module
docstring says so in the same terms. Whether that is adequate support for
`0x0860`'s direction split is a judgement for the reader — but the sentence as
written claimed an independence that no longer exists, and that is what the
correction says.

**The issue's own replacement figures were stale too**, by the mechanism the
issue itself describes. Its `:1399` is inside `pair_sites`'s docstring, its
`:2250` is a `similar(...)` line in the cluster grouping, and the live paragraph
is not at the `:286-288` the issue read it at. Recorded rather than quietly
replaced, per the precedent of
[`xdata-no-eq-guard-citation-anchors.md`](xdata-no-eq-guard-citation-anchors.md)
and [`xdata-0860-note-live-pointers.md`](xdata-0860-note-live-pointers.md), both
of which say so in the same sentence as the correction.

## The two things about a source citation that decide the design

A source line has no id column. A generated-CSV row resolves against `addr` or
`cluster_id`, and a cluster against `cluster_key`; a source citation resolves
against a **named anchor** — a literal string of the target's own source.
`check_eq_guard_citations.py` established that for one mechanism's own pins and
named this issue as the owner of the general case, so this generalizes it
rather than inventing a second idea.

The design question was which of two things the general tool is, and **neither**
answer given works:

- **Hold the line.** Every merge that grows the target reddens every citation
  into it. That is the lock CLAUDE.md's "Cite code by name" and the unheld pin
  census are about, and it is why `check_citation_lines.py` loosened its Rule 3
  to note rather than fail, and why `check_eq_guard_citations.py` stopped
  requiring its `:NNN` to match.
- **Accept any line inside the named construct.** Looser than that Rule 3, and
  blind to the case that decided the design: the live sentence's `:770` *is* in
  the right file and lands on a comment in the module-level `NOT_IN_TREE` dict,
  in no function at all, while its
  claim is about a **region** ("pins exactly those buckets") rather than a line.

So the tool is a **span check against a declared anchor**: the anchor's span is
its own line and every following line indented past it, and the cited line must
fall inside it. Four verdicts, each pinned by a case in the suite:

| the anchor… | verdict |
|---|---|
| resolves uniquely, cited line **inside its span** | pass |
| resolves uniquely, cited line **outside its span** | **fail**, naming the anchor's current line |
| resolves uniquely, cited line inside but **not on its opening line** | **note** — the sentence claims a region, and failing it would be the line rule again |
| **gone, or no longer unique** | **fail**, naming the anchor |

The fourth row is deliberately a failure and not a skip: "the subject of this
sentence does not exist in the file it names" is not "not checked by this
method." **It is not, however, the row that reaches this issue's own sentence,
and saying so is the more useful half.** `HAND_CHECKED` was never declared as an
anchor, so on the pre-fix page the `:770` cell is **declined** rather than
failed — and that is the correct reading of it, not a hole in the tool: with no
declared anchor for the subject, there is nothing for that verdict to fire on,
and a citation naming a subject the tool does not declare *is* "not in this
tool's declared list, which is a different claim." Declaring a needle the target
does not contain would be worse than useless — it would redden the committed
tree permanently, for a subject this change has already retracted. What the run
does report against the pre-fix page is the **reworded-citation** verdict, a
different branch: the corrected prose no longer matches the locators written
against it. Both are pinned in the suite by running that page rather than a
synthetic anchor.

**The supersession boundary** is scoped to the quoted run and stated in the
docstring rather than left open: the two shapes `check_citation_lines.py` reads
off **raw** lines — any line of a paragraph opening `>`, or a paragraph opening
`CORRECTION` once `>`, `#`, `*`, `-` and whitespace are stripped — **copied
rather than imported**, because a tool reaching into a sibling for its vocabulary
is a tool whose subject is the sibling. The skip is counted and printed on every
run, so "checked nothing" cannot read as "found nothing".

## The census

`check_source_citations.py --census` prints it, per file, in three classes:
**live** (a present-tense claim about where code is), **quoted-superseded**
(meant to stay wrong per §4a-4d), and **declines to attribute** (a bare `:NNN`
whose sentence does not say what file it is a line of). The census is printed
rather than written down as a figure here, because a count of this repository's
own prose goes stale at the next merge and CLAUDE.md's "no totals of the
repository's own text" is the rule that says so. Per-file rows from the tree
this lands in:

| file | live | quoted-superseded | declines to attribute |
|---|---|---|---|
| `ec/annotations/xdata-086x-dispatch.md` | 1 | 4 | 26 |
| `docs/findings/xdata-no-eq-guard-citation-anchors.md` | 14 | — | 145 |
| `docs/findings/doc-figure-pin-audit.md` | 14 | — | 48 |
| `docs/findings/xdata-census-rederivation-checklist.md` | 13 | — | 61 |
| `ec/annotations/xdata-06c2-06db-timers.md` | 8 | 1 | 11 |
| `docs/findings/xdata-6a-direction-rows-pinned.md` | 6 | — | 43 |
| `docs/findings/xdata-4-4-identity-rederivation.md` | 5 | — | 18 |
| `docs/findings/xdata-no-eq-guard-refusal-contract.md` | 5 | 1 | 62 |
| `ec/annotations/xdata-register-map.md` | 4 | — | 25 |
| `docs/findings/xdata-cluster-names-guard-off-recipe.md` | 4 | — | 7 |
| `docs/findings/xdata-export-ownership-refusal-contract.md` | 3 | — | 1 |
| `docs/findings/xdata-names-file-census-anchor.md` | 3 | — | 8 |
| `docs/findings/xdata-ownership-main-keys-pin.md` | 3 | — | 16 |
| `ec/annotations/registers.yaml` | 1 | — | 85 |

Three things the census says that are worth more than the rows:

**The bare `:NNN` form dwarfs the attributable one.** Most source-line
citations in this repository are a bare number continuing a file the enclosing
sentence named, and this tool declines to attribute them: guessing which target
a bare number is a line of is the move it exists to refuse. That is why the
declines column is the large one, and why the declined count in a normal run is
a count of `<target>.py:NNN` sites *specifically*.

**A large share of the live cells name a subject the tool no longer holds.**
Reading each live sentence's own backticked identifiers against the tool
measures this rather than asserting it: `OWNERSHIP`, `BUCKET_TOTALS`,
`main_refs` and `own_main_refs` are named by live prose and present nowhere in
the file. `HAND_CHECKED` is the near-miss worth stating precisely — it survives
in the tool **only inside the comment that records its own removal**, so a grep
for it finds a hit and a reader following that hit finds a tombstone rather
than a table. Declaring an anchor for any of those subjects is what would put
them under the fourth verdict row — by the time a subject is gone that is a
correction to write, not a declaration to add, so the tool's own answer to them
today is the same as for `:770`: declined, and named here. They are **not**
corrected here — each is a retraction in its own file with its own correction
block, and this issue's scope is the dispatch page's sentence. They are recorded
here as the class's next work.

**Another cell was wrong, and is repointed here.** `xdata-4-4`'s `MAP_COLUMNS`
citation gave `:390-393`, which is a comment about a set walk, and `MAP_COLUMNS`
is at `:505-507`. The new tool caught it on its first run against the committed
tree, which is the cheapest evidence that the mechanism works: it found a live
stale cell in a file this issue never named.

## What this does not check

In the register `check_site_census.py` and `prose-line-citations-held.md` keep,
and the same caveat: every one of these is "not done by this method", never
"absent".

- **`ec/annotations/registers.yaml`, at all.** The reason is measured, not
  assumed, and it is the same one `check_citation_lines.py` records: a folded
  scalar holds no blank lines, so a whole `name:` entry is ONE paragraph whose
  `*** CORRECTION` marker sits mid-paragraph, and neither supersession shape
  fires on it. #870 fixed that entry's six cells by hand. A file this tool does
  not walk is reported as not walked.
- **A citation whose subject is a *different* construct inside the anchor's
  span.** Measured, not hypothetical: one live cell in `xdata-4-4` cites `:2723`
  for "a comment carrying 'the committed 427 ids'", and that string is in the
  tool well outside the span the declared anchor opens. A span is a region, not a
  subject — containment says the number is somewhere in the construct, and
  nothing here says which line of it the sentence meant. Holding that needs the
  cited line's own text, which is a per-file oracle this tool does not have. It
  is a false negative, and it is in the docstring rather than left to be found.
- **A `.c` citation.** `check_citation_lines.py`'s Rule 1 and
  `check_site_census.py` hold the decompile side; this holds pointers into
  source.
- **Any target outside `ANCHORS`, or any file outside `CITATIONS`.** Not read at
  all, which is "not done by this method" and never "there is nothing there".
- **Whether a cited number agrees with the figure the sentence attaches to
  it.** Held to being inside the right construct, nothing more.

## Scope, and what was deliberately not done

The declared scope is five anchors in one target and three declaring files, and
the tool prints every citation it holds, every one it declines and every one it
skips on each run — so the scope is visible rather than asserted.

- **`docs/findings.md`** is frozen; a summary section there is the one edit
  CLAUDE.md forbids. This file is its own write-up, which is what
  `gen_findings_index.py --check` needs.
- **`tools/README.md`'s suite table** was removed and a checker fails if it
  returns; the suite is discovered by `find` and described by its own docstring.
- **A prepared gate patch** for the new tool is out of scope, as the plan's
  issue says: the suite runs under `tools/run-tests.sh` meanwhile.
- **Widening `check_citation_lines.py`** beyond the one docstring bullet. Its
  own supersession vocabulary is a recorded decision another issue owns, and its
  docstring still describes it in its own terms.