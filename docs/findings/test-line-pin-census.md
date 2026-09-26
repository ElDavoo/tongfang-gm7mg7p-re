# The census of every `test_*.py:NNN` the markdown carries, and why nothing checks it (issue #887)

**Nothing here is a hardware claim, and nothing here is a firmware claim.** No
image is opened, no register is read back, no capture is taken, and no laptop, EC
or Windows machine is involved anywhere below. Every figure is a count of lines
in files in this repository, and the one command that produces them is in it.
Same framing as [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):10 — a
census of text about text.

Issue #887 asks two things: census the `file:line` pointers the committed
markdown writes into **test files** and say how many no longer name the line they
are cited for, and then say whether a checker is warranted. The first is this
file and the tool behind it. The second is a **no**, argued from the measurement
rather than guessed at, in *Why no checker* below.

## What the class is, and why it is not one of the two that are held

`ec/tools/check_citation_lines.py` (#801) holds pointers into the **generated
CSVs**, and `ec/tools/check_cluster_citations.py` (#822) holds cluster-id and
row claims. Neither reaches a line number written into a `.py` file, and
[`prose-line-citations-held.md`](prose-line-citations-held.md) §"What this does
not check" says so in its own bullet: *"A pointer into a source file, as against
one into a generated CSV… A different tool."*
[`../../tools/README.md`](../../tools/README.md)'s eighth-thing paragraph says the
same from the other end: *"nothing checks a citation into a test file, which is
why the two pre-existing ones are still wrong."* This is that other tool's
census, and the count it starts from.

## The measurement

`ec/tools/census_test_line_pins.py` reads every markdown file in the tree
(`vendor/` and this file excluded, both named on every run), finds every
`test_*.py:NNN`, resolves each one to a file and a line, and prints the counts:

```console
$ python3 ec/tools/census_test_line_pins.py
50 pin(s) in 23 markdown file(s): 37 distinct spelling(s), 32 distinct resolved target(s)
  44 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 6 declined
  5 def test_, 15 assertion, 5 comment, 8 blank, 11 other (of the pins that resolve)
  read 141 markdown file(s) under the tree, excluding .git/vendor/ and docs/findings/test-line-pin-census.md; resolved against 35 test file(s) in it
  no claim is measured here: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
$ echo $?
0
```

**Each count below is a different thing, and every one of them is printed**,
which is the only reason a census like this can be trusted: a headcount that
cannot be reconciled against itself is the failure it is measuring.

- **50 occurrences** — every pin, counted once per place it is written. Four
  spellings (`ec/tools/test_disasm8051.py:3-6`,
  `ec/tools/test_xdata_cluster_names.py:307`, `:392` and
  `ec/tools/test_xdata_register_map.py:9-12`) are written in three or four files
  each, which is where the gap to 37 opens.
- **37 distinct spellings** — the pin exactly as written, so `test_a.py:12` and
  `ec/tools/test_a.py:12` are two. This is the figure the issue's grep reported
  and it is the one that still holds on this tree.
- **32 distinct resolved targets** — distinct `(file, span)` pairs after
  resolution, so the two spellings of one span are one target.
- **23 files** carry at least one; [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md)
  carries ten and [`docs/findings.md`](../findings.md) five.

**Two of the planning stage's numbers did not reproduce, and both are the
extractor's fault rather than the tree's.** The issue's own grep reported 37
distinct pins across 22 files; the plan built on it counted 49 occurrences over
the same 22, and **called 12 of those 49 an ambiguous `tools/` prefix**. This
tree carries **50 occurrences across 23 files** — one pin written since — and
**none** of them ambiguous, for two reasons that are findings in their own right
and are the reason the tool is written the way it is:

1. **A scan that recognises `tools/` but not `windows/tools/` truncates the
   second into the first.** Four of the twelve are `windows/tools/…` citations
   — `windows/tools/test_ec_watch.py:145`,
   `windows/tools/test_system_id_probe.py:311` and two spellings of
   `windows/tools/test_manual_fan_ctrl_probe.py:508` — and a regex that treats
   `tools/` as the whole directory prefix cuts `windows/` off the front and
   reports four sound citations as pointing at files that do not exist. That is
   the defect this census exists to measure, one level down, and the tool takes
   the **whole** directory prefix with a lookbehind that stops it starting
   mid-path.
2. **The remaining two are not ambiguous, they are relative.** `ec/annotations/xdata-register-map.md`
   writes `../tools/test_xdata_cluster_names.py:54` and `:68-90` for its own
   neighbour, and `../../docs/findings/…` for its own page's siblings in the same
   sentence. Read against the tree those are missing paths; read against the
   citing file's own directory they are `ec/tools/…` and they are correct. The
   resolver therefore reads a path against the tree first and, only where the
   tree does not have it, beside the citing file — and says which of the two
   answered for every pin.

**So the measured headcount of this class is 50 occurrences, 37 spellings, 32
resolved targets — and zero of the twelve the plan's scan called an ambiguous
prefix is one.** The figures that moved are recorded as a defect in the method
that produced them rather than as a drift in the tree, and a census that reports
the wrong population with great confidence is worth less than no census.

### Verdicts, and what each one is not

| verdict | what it means | here |
|---|---|---|
| `resolves` | the file was found and the span is one it has | **44** |
| `out-of-range` | the file is there and the span ends past its end | 0 |
| `unresolved-path` | no such file under either reading | 0 |
| `ambiguous-path` | a bare module name two files in the tree could answer to | 0 |
| `declined` | a shape the reader refuses: the pin is inside a fenced block, so it is a **transcript of a run** and not a citation | **6** |

**Every negative here is "not read by this method", never "absent"** — the caveat
`ec/annotations/registers.yaml` carries for a static scan and
`check_cluster_citations.py` prints for a citation check. `unresolved-path` says
*no file of that name is at that path in this tree*, which is a statement about
a directory walk; `out-of-range` says *this span is not one the file has*, which
is a statement about a line count. Neither says anything about whether the claim
a pin was written for is true. **All three zeros are measurements, not gaps**:
every pin in the tree names a file that is in it, no cited span has outrun its
file, and no two `test_*.py` in the tree share a module name (held from the other
side by a case in the suite, because a `test_export_*.py` rename would put two
files of one name in the index and make every bare-name pin to that module
undecidable).

The six `declined` are the tool's only refusal, and declining them is not a guess:
five are `ok …` lines of a literal-scan transcript in
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) and one is a
`grep` transcript in [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md).
**Every declined target is also cited in live prose in the same file** — that is
a case, not an observation, because a transcript that had become a file's only
citation of a line would make the count a quiet loss rather than a declined
duplicate.

### The landing shape, which is the finding

| shape | here | what a pin naming it is pointing at |
|---|---|---|
| `def test_` | **5** | the header of a test case |
| assertion | **15** | the `assertEqual`/`assertGreater` that decides the claim |
| comment | 5 | prose the case is annotated with |
| `blank` | 8 | nothing at all — the blank line above what the span is about |
| other | 11 | a `def` that is not a test, an assignment, a `setUpClass` body |

**Eight of the 44 resolving pins land on a blank line**, and that is the house
spelling rather than a mistake: a span is written from the line *above* the thing
it is about. `ec/tools/test_disasm8051.py:3-6` is a module docstring that opens
on its own blank line; `ec/tools/test_grade_0751_isolation.py:16-20` is an import
block the same way; and `test_xdata_cluster_names.py:592-598` is a five-line span
that begins on the blank above `def test_every_row_records_the_evidence_for_its_name`.
**A checker for this class has to accept a blank line as a legitimate target**,
which is not a rule anyone writes down twice.

## The per-pin table

One row per occurrence, in the census's own order, so a reader can re-derive it
by running the tool and reading `--verbose`. The **verdict** column is a reading
and not a measurement: it is the answer to "does the line it names still carry
the claim it is cited for", which is the half no tool in this tree can make and
the half this table exists to record.

| citing | cited target | read | shape | verdict |
|---|---|---|---|---|
| `docs/agent-pipeline.md:345` | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries |
| [`../findings.md`](../findings.md):4206 | `test_manual_fan_ctrl_probe.py:38-40` | by-name | comment | **records another line** |
| [`../findings.md`](../findings.md):4208 | `test_ec_watch.py:86-89` | by-name | other | **records another line** |
| [`../findings.md`](../findings.md):7170 | `test_xdata_cluster_names.py:286` | by-name | other | **does not carry** |
| [`../findings.md`](../findings.md):7349 | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries |
| [`../findings.md`](../findings.md):7410 | `ec/tools/test_xdata_register_map.py:9-12` | by-path | other | carries |
| [`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md):221 | `test_manual_fan_ctrl_probe.py:905` | by-name | assertion | carries |
| [`0751-capture-row-shape.md`](0751-capture-row-shape.md):41 | `test_grade_0751_isolation.py:3608` | by-name | other | **records another line** |
| [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99 | `ec/tools/test_grade_0751_isolation.py:2232-2233` | by-path | assertion | **does not carry** |
| [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md):263 | `test_grade_0751_isolation.py:16-20` | by-name | blank | carries |
| [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226 | `ec/tools/test_grade_0751_isolation.py:16` | by-path | blank | **does not carry** |
| [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):310 | `ec/tools/test_grade_0751_isolation.py:1862` | by-path | comment | carries, adjacent |
| [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):426 | `ec/tools/test_grade_0751_isolation.py:2694` | by-path | comment | carries, adjacent |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):105 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | — | — | **declined** (fenced) |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):203 | `windows/tools/test_ec_watch.py:145` | by-path | assertion | carries |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):204 | `windows/tools/test_system_id_probe.py:311` | by-path | assertion | carries |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):231 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | by-path | other | carries |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):541 | `windows/tools/test_manual_fan_ctrl_probe.py:515` | by-path | assertion | carries |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):579 | `test_manual_fan_ctrl_probe.py:513` | by-name | assertion | **records another line** |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):618 | `windows/tools/test_manual_fan_ctrl_probe.py:508` | — | — | **declined** (fenced) |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):619 | `windows/tools/test_ec_watch.py:145` | — | — | **declined** (fenced) |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):620 | `windows/tools/test_system_id_probe.py:311` | — | — | **declined** (fenced) |
| [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):641 | `windows/tools/test_manual_fan_ctrl_probe.py:515` | — | — | **declined** (fenced) |
| [`bank1-e582-entry-framing.md`](bank1-e582-entry-framing.md):68 | `ec/tools/test_citation_gap_scan.py:109` | by-path | assertion | carries |
| [`disasm8051-self-test-gate.md`](disasm8051-self-test-gate.md):27 | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):155 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | def test_ | carries |
| [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md):71 | `ec/tools/test_disasm8051.py:52` | — | — | **declined** (fenced) |
| [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md):122 | `test_disasm8051.py:52` | by-name | comment | carries |
| [`runner-red-suite-set.md`](runner-red-suite-set.md):103 | `tools/test_readme_suite_table.py:11-20` | by-path | other | carries |
| [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):25 | `ec/tools/test_check_testdata_index.py:413-415` | by-path | assertion | **records another line** |
| [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):145 | `ec/tools/test_check_site_census.py:449` | by-path | assertion | carries |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):392 | `test_xdata_cluster_names.py:54` | by-name | blank | **does not carry** |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):403 | `test_xdata_cluster_names.py:355-370` | by-name | assertion | **does not carry** |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):433 | `ec/tools/test_xdata_cluster_names.py:286` | by-path | other | carries in part |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):446 | `test_xdata_cluster_names.py:355-370` | by-name | assertion | **records another line** |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):20 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | def test_ | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):98 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | def test_ | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):183 | `ec/tools/test_xdata_cluster_names.py:392` | by-path | assertion | carries |
| [`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):376 | `ec/tools/test_xdata_register_map.py:9-12` | by-path | other | carries |
| [`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):377 | `test_xdata_cluster_names.py:392` | by-name | assertion | carries |
| [`xdata-green-set.md`](xdata-green-set.md):283 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | def test_ | carries |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):15 | `ec/tools/test_xdata_cluster_names.py:392` | by-path | assertion | carries |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):319 | `test_xdata_cluster_names.py:392` | by-name | assertion | carries |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):331 | `test_xdata_cluster_names.py:387-389` | by-name | comment | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):28 | `ec/tools/test_xdata_cluster_names.py:581` | by-path | other | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):132 | `test_xdata_cluster_names.py:117-121` | by-name | def test_ | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):149 | `test_xdata_cluster_names.py:592-598` | by-name | blank | carries, adjacent |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):1341 | `../tools/test_xdata_cluster_names.py:54` | beside | blank | **does not carry** |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645 | `../tools/test_xdata_cluster_names.py:68-90` | beside | other | carries |
| [`../../tools/README.md`](../../tools/README.md):157 | `test_xdata_cluster_names.py:303` | by-name | other | **records another line** |

**27 carry, 3 carry on the adjacent line, 1 carries one of the two claims it is
cited for, 6 do not carry, 7 record another line on purpose, 6 are declined, and
none is unresolvable.** The two qualified values are worth what they say about the
tool's limits rather than about the tree:

- **"carries, adjacent"** is a pin one line off the thing it names, and it is
  three of fifty because this corpus writes *"is at `:1862`"* against a `def` on
  the next line. No rule can decide whether that is a pin or a typo, which is
  the first reason the judgement half is a table and not a verdict.
- **"carries in part"** is the sharpest of the three.
  [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):433
  cites `:286` for *two* figures in the suite's docstring, and `:286` is the
  second of them. **The same target read against
  [`../findings.md`](../findings.md):7170's sentence is "does not carry"**,
  because that one says `:286` holds a third-generation figure and `:286` is the
  second. One line, two verdicts, and nothing mechanical in the tree can tell
  them apart — which is the argument for the split in one sentence.

## The six that do not carry

Five numbered findings, six pins: the fourth is one stale pin written twice, in
two files, describing the same removed constant. **One of the six is the issue's
own** and it is confirmed here exactly as filed; the other five are new.

1. **[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):403**
   — `test_xdata_cluster_names.py:355-370`, cited for
   `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`. That
   case is at **`:459-473`**; `:355-370` is §6a's assertion block, the
   `(210, 1326)` and `(0, 1326)` pairs and the `0x08A8`/`0x0843` subtest, which
   pairs no ids at all. Already recorded in the same file's
   "Deliberately not fixed" list at `:446` and left unrepointed there on
   purpose. **The issue places this pin at `:154-157`; it is at `:403`.** The
   claim is right and the line number is not, which is the whole argument, in
   the register `registers.yaml` and `check_cluster_citations.py` already use.
2. **[`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99** —
   `ec/tools/test_grade_0751_isolation.py:2232-2233`, cited for the sentence
   *"a capture carrying one is still fatal for the whole run however it got
   there."* That sentence is a **comment at `:2687`**, above
   `test_a_mark_that_is_not_one_of_the_forms_is_an_error`. `:2232-2233` is
   `self.assertEqual(section.count("from the <value> in these files' §6 names"), 2)`,
   which is about a different case entirely. **New — the issue did not name it**,
   and the file that names it is #498's, not this issue's.
3. **[`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226**
   — `ec/tools/test_grade_0751_isolation.py:16`, cited for *"the suite locates
   its fixtures off `Path(__file__).parent`"*. `:16` is a **blank line**;
   `HERE = Path(__file__).parent` is at **`:17`**. Off by one, on the same file,
   one line above the span its sibling citation at
   [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md):263 gets right
   (`:16-20`, which does cover the `spec_from_file_location` block).
4. **[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):392**
   and **[`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):1341**
   — both name `test_xdata_cluster_names.py:54` for `GUARD`, the literal the
   `--no-eq-guard` recipe used to patch. `:54` is a **blank line** and `GUARD`
   **is not in the file at all**: #753 dropped the copy-and-patch recipe and
   replaced it with `--no-eq-guard`. The same stale pin, written twice, in two
   files, both describing a recipe that no longer exists.
5. **[`../findings.md`](../findings.md):7170** — `test_xdata_cluster_names.py:286`,
   cited for *"`…:286` carries a third-generation figure in its docstring"*.
   `:286` is the **second** generation — *"430 → 439 with 64 ranks intact and 366
   changed"*; the third, *"427 clusters become 439, 48 … 379"*, is at
   `:275-277`. The sentence names the wrong generation of two, one line apart in
   the same docstring.

## The seven that record another line, and why that is the blocker

These are **correct sentences about a line that has moved**, and the reason each
one is right is that `docs/findings.md` §4a-4d requires the superseded value to
stay visible beside its correction. A checker with no rule for them reddens on
sentences that are true, and [`prose-line-citations-held.md`](prose-line-citations-held.md)
§"The one judgement call" is explicit that this is *"the surest way to get a
check switched off, and then nothing would be left."*

**The class has at least six unmarked shapes of supersession, and the two that
`check_citation_lines.py` already knows — a `>`-opened line and a paragraph
opening with `CORRECTION` — catch exactly one of the seven below.** That is the
finding, and it is why the verdict is no checker rather than a deferral:

| shape | where | caught by `check_citation_lines.py`'s vocabulary? |
|---|---|---|
| a repoint list naming the stale value, in running prose | [`../../tools/README.md`](../../tools/README.md):157 — `test_xdata_cluster_names.py:303` → `:307` in four places | **no** |
| a "deliberately not fixed" bullet naming the wrong pin | [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):446 | **no** |
| a "the citation check caught it here" sentence | [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):579 — `:513` named *because* it was the wrong line | **no** |
| an "At the time of writing, `file:NNN`:" lead-in to a quoted block | [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):25 | **no** |
| a pin qualified by a commit — *"…(`:3608` at `c9e72c1`)"* | [`0751-capture-row-shape.md`](0751-capture-row-shape.md):41 | **no** |
| a dated findings section describing the tree as it was | [`../findings.md`](../findings.md):4206 and `:4208`, §16's pre-#186 fakes | **no** |
| a blockquote correction naming the post-fix location | [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645 | yes — and it is one of the **carries** |

**Six of the seven are invisible to the vocabulary that already works**, and the
one the vocabulary does catch is a sound citation. That is not a rule waiting to
be written; it is a shape per author, and the last row is the proof that the
blockquote rule is not merely safe here but *insufficient*.

**What is deliberately not done about them.** Repointing the citing prose is
twenty-three files' worth of edits against open agent PRs, and **every one of
these seven is already recorded in place** — that is what makes each of them
right, and
`xdata-4-4-identity-rederivation.md`'s own "Deliberately not fixed" list says
outright that deciding *what a drifted pin was meant to name* is a next pass's
call and not a merge's. This branch takes no position on that and edits no
citing prose. The table above is the hand-off.

## Why no checker

The issue asks whether one is warranted and says that if it needs a judgement
this issue does not make, to say so rather than shipping a checker that reddens
on the next merge. **It needs that judgement, and the measurement says so rather
than my having to assert it.** Four things, in the order they decide it:

1. **The pins are not one kind of thing.** 5 name a `def test_` line, 15 an
   assertion, 5 a comment, **8 a blank line** and 11 something else. The
   citation means "the line where this claim is decided", and that line is the
   test header in 5 cases out of 44. A `def`-anchored rule is wrong; an
   assertion-anchored rule is wrong; a blank-line-anchored rule is worse than
   both, because the blank is an artefact of the span convention and 8 of them
   move whenever a line is inserted one line above. **No single anchor covers
   them and the range form needs a third rule on top.**
2. **Supersession is unmarked prose in this class, and that is the blocker.**
   `check_citation_lines.py` gets away with a two-shape skip because a
   supersession there *has* a shape. Here it does not: six of the seven
   records above are ordinary running prose or a bullet, and
   [`../../tools/README.md`](../../tools/README.md):157 cites `:303` **because
   `:303` is the stale value it is reporting**. A checker with no skip rule
   reddens on two sentences that are correct, and with the rule
   `check_citation_lines.py` already has it still reddens on five more.
3. **A resolver has to read two spellings, and one of them is a judgement.**
   `ec/annotations/xdata-register-map.md`'s `../tools/…` is only a path once you
   know the page writes its paths relative to itself; a resolver that reads
   against the tree alone reports two sound pins as missing files. The tool here
   reads both and prints which answered, and a *checker* could not: it would have
   to pick, and a wrong pick reads as a broken citation.
4. **There is nothing for a file-level rule to catch.** `out-of-range` is 0,
   `unresolved-path` is 0 and `ambiguous-path` is 0. Every pin in the tree names
   a file that exists and a span it has. **The entire defect is in the
   line-*content* half**, and that half is the one a rule cannot make — as the
   "carries in part" row above shows, one line and two sentences give two
   different verdicts.

**So the tool ships as a census that renders no verdict and never fails on
drift**, and the re-open condition is written down rather than left to a later
reader: a checker becomes writable when **either** this class is taught a
supersession marker its own authors use — a `RECORDED:` prefix, say, which six
of the seven records above could carry today with a two-word edit each —
**or** a decision is taken that pins into a test file must name a `def` and be
held as one, which is a policy about how this repository writes citations
rather than a fact about the pins. Neither is a fact about the tree, so neither
is this issue's to decide, and the issue itself says so.

## What this does not check

In the same register as every other checker here, and the same caveat: each of
these is **"not done by this method", never "absent"**.

- **Whether the cited line still carries the claim.** The whole second half. It
  is this file's table and it was made by reading; the tool renders no verdict on
  it, and a tool that guessed at the second half would be exactly the overclaim
  `CLAUDE.md` forbids.
- **A `.py:NNN` pin into anything that is not a `test_*.py`.** Measured over the
  same files with the same extractor and the test class excluded: **373
  occurrences, 229 distinct `(file, line)` targets, 34 files** —
  `xdata_register_map.py` 77, `grade_0751_isolation.py` 46,
  `pd_index_geometry.py` 39, `ec_watch.py` 34. The planning stage's estimate of
  this wider class was 180 occurrences and 39 targets; **that does not reproduce
  under any of four narrower definitions I tried**, so the figure above is the
  one recorded and the estimate is not used. This class is not owned here either
  — see the follow-ups.
- **A pin written without a path**, the `:444-448` shorthand a page uses once the
  file is named in the sentence above. There is no file to resolve it against
  and reading it would mean guessing which of the thirty-five test files was
  meant.
- **A blockquote.** A `>`-opened line is read, not skipped, and
  [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645
  is the one pin in this class that a supersession skip would have passed over
  and that turns out to be **correct** — evidence that the skip is not merely
  safe here but insufficient.
- **A markdown-to-markdown pin.** The issue's second item is one —
  [`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md):221 cites
  `xdata-cluster-names-guard-off-recipe.md:406-407` for the sentence *"the cheap
  tier not running the tool's `--check`/`--self-test`, which are red on `main`"*,
  which is at **`:446-447`** (inside the bullet at `:445-448`);
  `:406-407` is two lines of a `>`-quoted paragraph about where that file's dated
  correction blocks are. **Both of the issue's claims are confirmed exactly as
  filed, and this one is not in this census** because the class here is a pin into
  a *test file*; a markdown-to-markdown checker is `check_citation_lines.py`'s own
  next step and is named as such below. The class is therefore **wider than
  `tools/README.md`'s eighth-thing paragraph says**, and a fix scoped to `.py`
  targets would miss this one.
- **Whether the prose is right about the claim even where the line is right.**
  Only that the line is the one the sentence was written for.

## Verified on this tree

```console
$ python3 ec/tools/census_test_line_pins.py
$ echo $?
0
$ python3 -m unittest discover -s ec/tools -p test_census_test_line_pins.py
.........................................
Ran 41 tests in 1.172s

OK
$ bash tools/run-tests.sh
35 suite(s) run, 1074 tests; one or more FAILED.
```

**The one red suite is not this branch's.** It is
`ec/tools/test_check_cluster_citations.py`, 48 cases, on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` with the same two
`0x0464`/`0x0465` cluster disagreements `tools/README.md` has named as
reproducing on a clean `origin/main` since #822. This change touches no cluster,
no CSV and no membership, and neither causes it nor fixes it.

The suite is 41 cases and it is the reason the two directions are demonstrated
rather than asserted: a run that located nothing reports it and exits non-zero,
**and** a run whose every pin is broken still exits zero, with a case for each.
`ec/annotations/registers.yaml` is untouched — no `status:` moved, no row edited,
no CSV or `xdata-symbols.csv` regenerated, no Ghidra export re-run, no
`.gpr`/`.rep` opened. **The census reads text.**

**Red demonstrated, not asserted.** On a scratch copy holding
`ec/tools/census_test_line_pins.py`, the real
`ec/tools/test_xdata_cluster_names.py` and the real
[`xdata-green-set.md`](xdata-green-set.md), moving that page's pin
`ec/tools/test_xdata_cluster_names.py:307` to `:308` — the one-line change a
merge above the `def` makes — the tool reports the new landing and **still exits
0**:

```console
$ python3 ec/tools/census_test_line_pins.py --verbose     # before
  docs/findings/xdata-green-set.md:283  ec/tools/test_xdata_cluster_names.py:307  resolves  …  the pin names the path (by-path)
      def test_    def test_the_census_is_the_one_6a_measured(self):
$ python3 ec/tools/census_test_line_pins.py --verbose     # after :307 -> :308
  docs/findings/xdata-green-set.md:283  ec/tools/test_xdata_cluster_names.py:308  resolves  …  the pin names the path (by-path)
      comment     # The only case in this class that holds the run to a published figure
$ echo $?
0
```

That is the [`prose-line-citations-held.md`](prose-line-citations-held.md)'s
`:817` → `:818` demonstration, on the class this issue exists to survive: **the
shape changed from a `def` to a comment and nothing turned red.** A checker here
would have had to decide whether that is a defect, which is the judgement above.

### The one other file this branch had to touch, and why

`ec/tools/test_check_doc_figure_pins.py` went **red on this branch landing**, with
five failures, and the cause is this suite rather than the tree:
`check_doc_figure_pins.py` searches *every* module in `ec/tools/` for an int
inside an asserting call and reads a hit as a pin, and one of this census's
committed-tree figures is **`50`** — so the moment the suite landed, the census's
own count made the checklist's §2b console-block cluster count `50` (an unrelated
figure that happens to be the same integer) measure `held-by-check-literal`, and
§2b's own `unheld` marking disagreed with the measurement.

That is not a new defect: it is the one `check_doc_figure_pins.py` already
anticipates in its own `SELF_MODULES` comment — *"nothing mechanical can tell a
test that pins a figure against the census from one that pins it against this
tool's verdict about the census — they are the same call shape, and only the
second is circular"* — and #849's own audit would have hit the identical thing if
its suite had named `390`. The general rule is the one the exclusion already
states: **a module that publishes a figure another tool measures cannot also be
the evidence for it.** So the two census modules join that tuple, which is a
constant and a docstring line, and nothing else in that tool moves: §2b is back
to **eight held and ten unheld**, and its printed denominator is back to the
**`175 literal(s) inside a check`** that [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md)
quotes, so that transcript is still the record of the tree it was measured on.

**The alternative was to write this suite so it never says `50`, and that is the
accommodation worth naming.** A count that avoids a search is a count that was
chosen to be invisible, and the next reader would have no way to know the figure
was shaped rather than measured. The exclusion is one line, it is the rule the
tool already states, and it costs a denominator that was going to move anyway.

## What is left, as follow-ups

1. **Repointing the citing prose**, which is the issue's own pointer and is not
   done here for the merge-conflict reason above. In the order the table gives
   them: [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99 →
   `:2687`; [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226
   → `:17`; [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):403
   and `:446` → `:459-473`; the two `:54` pins → wherever `GUARD` now is, which
   is nowhere, so the sentence rather than the line is what needs rewriting; and
   [`../findings.md`](../findings.md):7170's "third-generation" → the sentence
   has to distinguish `:275-277` from `:286` or drop one of the two. **Each of
   the first four is one line in one file, which is why they are a follow-up and
   not a merge.**
2. **The wider `.py:NNN` class** — 373 occurrences, 229 targets, 34 files, on the
   measurement above. It is not owned by this census, not by #870 (which is
   `registers.yaml`'s six `xdata_register_map.py` pointers), and not by
   [`prose-line-citations-held.md`](prose-line-citations-held.md) follow-up 2
   (which is the prose → *source-line* checker beside `citation_frames.py`).
   Whatever censuses it inherits this tool's two readings, because a
   tree-only resolver reports two sound pins in one of those files as missing.
3. **A supersession marker for this class**, if the no-checker verdict above is
   ever revisited. Six of the seven records are ordinary prose and could each
   carry a two-word marker today; a rule reading that marker is the difference
   between a writable check and a checker that reddens on the tree that records
   the drift it exists to catch.
4. **A markdown-to-markdown pin checker**, for
   [`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md):221's
   `:406-407` → `:446-447` and whatever else that class holds. The issue names
   this one and it is out of scope here for the reason in *What this does not
   check*; it belongs beside `check_citation_lines.py`, which already has the
   supersession vocabulary a markdown-to-markdown rule would need.
5. **The `tools/README.md` totals paragraph is one suite short of the runner**
   and is left that way on purpose. This change adds a suite and
   [`../../tools/README.md`](../../tools/README.md)'s table row for it, and
   nothing else in that file moves — re-deriving the totals is
   [`tools-readme-totals.md`](tools-readme-totals.md)'s subject and #817's in
   general, and a totals note is a nine-paragraph shared-file edit this branch
   has no reason to make.

Submitting anything upstream is unaffected: this issue touches no driver and no
firmware, and the mission's eventual
`Wer-Wolf/uniwill-laptop`/`tuxedo-drivers` contribution stays a prepared patch
in this repository for a human to submit, per issue #10. Nothing is opened in
another repository.
