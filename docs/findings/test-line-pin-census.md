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
69 pin(s) in 24 markdown file(s): 44 distinct spelling(s), 40 distinct resolved target(s)
  53 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 16 declined
  5 def test_, 11 assertion, 9 comment, 6 blank, 22 other (of the pins that resolve)
  read 144 markdown file(s) under the tree, excluding .git/vendor/ and docs/findings/test-line-pin-census.md; resolved against 35 test file(s) in it
  no claim is measured here: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
$ echo $?
0
```

**Each count below is a different thing, and every one of them is printed**,
which is the only reason a census like this can be trusted: a headcount that
cannot be reconciled against itself is the failure it is measuring.

- **69 occurrences** — every pin, counted once per place it is written. Four
  spellings (`ec/tools/test_disasm8051.py:3-6`,
  `ec/tools/test_xdata_cluster_names.py:307`, `:392` and
  `ec/tools/test_xdata_register_map.py:9-12`) are written in three or four files
  each, which is where the gap to 44 opens.
- **44 distinct spellings** — the pin exactly as written, so `test_a.py:12` and
  `ec/tools/test_a.py:12` are two. This is the figure the issue's grep reported
  for a tree half this size and it is the one that moved least.
- **40 distinct resolved targets** — distinct `(file, span)` pairs after
  resolution, so the two spellings of one span are one target.
- **24 files** carry at least one; [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md)
  carries ten, [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) thirteen and
  [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md) ten.

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

**So the measured headcount of this class is 69 occurrences, 44 spellings, 40
resolved targets — and zero of the twelve the plan's scan called an ambiguous
prefix is one.** The figures that moved from the plan's are recorded as a defect
in the method that produced them rather than as a drift in the tree, and a census
that reports the wrong population with great confidence is worth less than no
census.

### Verdicts, and what each one is not

| verdict | what it means | here |
|---|---|---|
| `resolves` | the file was found and the span is one it has | **53** |
| `out-of-range` | the file is there and the span ends past its end | 0 |
| `unresolved-path` | no such file under either reading | 0 |
| `ambiguous-path` | a bare module name two files in the tree could answer to | 0 |
| `declined` | a shape the reader refuses: the pin is inside a fenced block, so it is a **transcript of a run** and not a citation | **16** |

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

The sixteen `declined` are the tool's only refusal, and declining them is not a
guess: five are `ok …` lines of a literal-scan transcript in
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md), one is a
`grep` transcript in [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md),
and ten are `AssertionError:` lines of a perturbation transcript in
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) — five distinct targets,
each written twice.
**Every declined target is also cited in live prose in the same file** — that is
a case, not an observation, because a transcript that had become a file's only
citation of a line would make the count a quiet loss rather than a declined
duplicate.

### The landing shape, which is the finding

| shape | here | what a pin naming it is pointing at |
|---|---|---|
| `def test_` | **5** | the header of a test case |
| assertion | **11** | the `assertEqual`/`assertGreater` that decides the claim |
| comment | 9 | prose the case is annotated with |
| `blank` | 6 | nothing at all — the blank line above what the span is about |
| other | 22 | a `def` that is not a test, an assignment, a `setUpClass` body |

**Six of the 53 resolving pins land on a blank line**, and that is the house
spelling rather than a mistake: a span is written from the line *above* the thing
it is about. `ec/tools/test_disasm8051.py:3-6` is a module docstring that opens
on its own blank line; `ec/tools/test_grade_0751_isolation.py:16-20` is an import
block the same way; and `test_xdata_cluster_names.py:845-851` is a span that
begins on the blank above `def test_every_row_records_the_evidence_for_its_name`.
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
| [`../findings.md`](../findings.md):7190 † | `test_xdata_cluster_names.py:286` | by-name | assertion | **does not carry** |
| [`../findings.md`](../findings.md):7369 | `ec/tools/test_disasm8051.py:3-6` | by-path | blank | carries |
| [`../findings.md`](../findings.md):7430 | `ec/tools/test_xdata_register_map.py:9-12` | by-path | other | carries |
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
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):72 | `ec/tools/test_xdata_cluster_names.py:734` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):73 | `ec/tools/test_xdata_cluster_names.py:734` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):74 | `ec/tools/test_xdata_cluster_names.py:473` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):75 | `ec/tools/test_xdata_cluster_names.py:473` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):76 | `ec/tools/test_xdata_cluster_names.py:490` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):77 | `ec/tools/test_xdata_cluster_names.py:490` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):78 | `ec/tools/test_xdata_cluster_names.py:507` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):79 | `ec/tools/test_xdata_cluster_names.py:507` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):80 | `ec/tools/test_xdata_cluster_names.py:524` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):81 | `ec/tools/test_xdata_cluster_names.py:524` | — | — | **declined** (fenced) |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):177 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | other | **records another line** |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):181 | `ec/tools/test_xdata_cluster_names.py:473` | by-path | other | carries |
| [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):189 | `test_xdata_cluster_names.py:307` | by-name | other | **records another line** |
| [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md):71 | `ec/tools/test_disasm8051.py:52` | — | — | **declined** (fenced) |
| [`opcode-len-bounds-census.md`](opcode-len-bounds-census.md):122 | `test_disasm8051.py:52` | by-name | comment | carries |
| [`runner-red-suite-set.md`](runner-red-suite-set.md):103 | `tools/test_readme_suite_table.py:11-20` | by-path | other | carries |
| [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):25 | `ec/tools/test_check_testdata_index.py:413-415` | by-path | assertion | **records another line** |
| [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):145 | `ec/tools/test_check_site_census.py:449` | by-path | assertion | carries |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):392 | `test_xdata_cluster_names.py:54` | by-name | other | **does not carry** |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):403 | `test_xdata_cluster_names.py:651-666` | by-name | other | carries |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):433 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | other | carries |
| [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):446 | `ec/tools/test_xdata_cluster_names.py:355-370` | by-path | comment | **records another line** |
| [`xdata-6a-direction-rows-pinned.md`](xdata-6a-direction-rows-pinned.md):87 | `ec/tools/test_xdata_cluster_names.py:473` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):20 | `ec/tools/test_xdata_cluster_names.py:339` | by-path | def test_ | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):131 | `ec/tools/test_xdata_cluster_names.py:734` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):137 | `ec/tools/test_xdata_cluster_names.py:473` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):138 | `ec/tools/test_xdata_cluster_names.py:490` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):139 | `ec/tools/test_xdata_cluster_names.py:507` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):140 | `ec/tools/test_xdata_cluster_names.py:524` | by-path | other | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):156 | `ec/tools/test_xdata_cluster_names.py:339` | by-path | def test_ | carries |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):165 | `ec/tools/test_xdata_cluster_names.py:307` | by-path | other | **records another line** |
| [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):334 | `ec/tools/test_xdata_cluster_names.py:588` | by-path | assertion | carries |
| [`xdata-cluster-names-guard-off-recipe.md`](xdata-cluster-names-guard-off-recipe.md):376 | `ec/tools/test_xdata_register_map.py:9-12` | by-path | other | carries |
| [`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):377 | `test_xdata_cluster_names.py:417` | by-name | comment | **does not carry** |
| [`xdata-green-set.md`](xdata-green-set.md):283 | `ec/tools/test_xdata_cluster_names.py:339` | by-path | def test_ | carries |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):15 | `ec/tools/test_xdata_cluster_names.py:417` | by-path | comment | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):404 | `test_xdata_cluster_names.py:417` | by-name | comment | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):416 | `test_xdata_cluster_names.py:412-414` | by-name | comment | **does not carry** |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):28 | `ec/tools/test_xdata_cluster_names.py:833` | by-path | other | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):132 | `test_xdata_cluster_names.py:149-153` | by-name | def test_ | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):149 | `test_xdata_cluster_names.py:845-851` | by-name | def test_ | carries |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):1341 | `../tools/test_xdata_cluster_names.py:54` | beside | other | **does not carry** |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645 | `../tools/test_xdata_cluster_names.py:68-90` | beside | blank | carries |
| [`../../tools/README.md`](../../tools/README.md):159 | `test_xdata_cluster_names.py:303` | by-name | other | **records another line** |

**32 carry, 2 carry on the adjacent line, 9 do not carry, 10 record another line
on purpose, 16 are declined, and none is unresolvable.** *(Those are the counts
on the merged tree; the 27/3/1/6/7/6 they replace are the record of the tree
this was written on and are kept in the sentence rather than deleted, per
§4a-4d. The move is #850's, not this merge's — see the note at the foot of this
file.)* **"carries, adjacent"** is a pin one line off the thing it names, and it
is two of sixty-nine because this corpus writes *"is at `:1862`"* against a `def`
on the next line. No rule can decide whether that is a pin or a typo, which is
the first reason the judgement half is a table and not a verdict.

† **Two changes to the table, 2026-09-26 (issue #890), and neither moves a
count.** That issue put 25 lines into `ec/tools/test_xdata_cluster_names.py` at
`:365`, which is the cascade this tool's own docstring describes — "#852 put four
lines into `ec/tools/test_xdata_cluster_names.py` at `:291` and every `file:line`
the tree cited into that file past `:291` went stale in the same commit,
silently". **56 pins past that line were repointed by +25** across seven
markdown files, and the eight rows below whose *citing* line moved (this file
grew §2a's footnote and `xdata-moved-ranks-fall.md` grew its correction) were
re-registered against the new lines. The verdicts, the shapes, the 69/24/44 and
the 53/16 all come back identical, which is the check: a repoint that moved a
count would show here first. **The `7185` this row carried was already stale on
`origin/main` — the pin is at `7190` on a clean tree — and is corrected here
because this branch was in the file anyway, not because it caused it.**

‡ **What the #890/#900 merge moved, re-registered against the merged tree, and
still no count.** The *cited* targets are the branch's, because #890's 25 lines
are what moved them; the *citing* lines are the merged tree's, because neither
side had them. Four rows re-registered: `xdata-moved-ranks-fall.md`'s second and
third at `:352` and `:364` on the branch and `:383` and `:395` on main are at
**`:404` and `:416`** here, and `../findings.md`'s `:7364` and `:7425` and
[`../../tools/README.md`](../../tools/README.md)'s `:157` — stale on `main`
before this merge, by #900's edits to those two files — are at **`:7369`,
`:7430` and `:159`**. **The one figure the merge does move is the `read N
markdown file(s)` line of the transcript above, `143` → `144`:** #890 added
`docs/findings/xdata-write-direction-correction.md` and #900 added no markdown
file at all — its `142` → `143` was a correction of a stale transcript, since
the tool reports `143` on the tree this merge forked from as well as on `main` —
and the new file carries no `test_*.py:NNN` pin, which is why 69/24/44/40 and
53/16 are untouched while the denominator moved. The three prose places that
name `tools/README.md:157` are repointed with the row.

**The "carries in part" row is gone from this tree, and the argument it carried
is not.** It was the sharpest of the three qualified values:
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):433
cited `:286` for *two* figures in the suite's docstring and named the second,
while [`../findings.md`](../findings.md):7185 says `:286` holds a third-generation
figure and `:286` was the second — **one line, two verdicts, and nothing
mechanical in the tree able to tell them apart**, which was the argument for the
split in one sentence. #850 repointed `:433` to `:307`, which carries, so
`:286` now has one verdict rather than two. The category is empty here and the
second half of the split is still right; what is lost is a worked example of it,
and it is named rather than papered over.

## The nine that do not carry

**Six items below and nine pins, and the sixth is the reason the count is nine
and not ten**: finding 1 was one of the six when this was written and #850
repointed it into carrying, so it is kept struck through rather than deleted.
Finding 4 is one stale pin written twice, in two files, describing the same
removed constant, and finding 6 is one moved assertion written four times across
two files. **The issue's own citing-line reference is not among the nine** — it
was finding 1, and on this tree it carries, which is the one claim of the issue's
two that #850's own change turned into a `carries` rather than a
`does not carry`. Five of the nine carried over from the six this section
recorded; **four are new**, all four finding 6 and all four #850's.

1. ~~**[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):403**
   — `test_xdata_cluster_names.py:355-370`~~ — **repointed by #850 and now
   carrying.** It cited `:355-370`, which is §6a's assertion block, for
   `test_the_two_largest_cited_clusters_are_carried_by_overlap_not_by_key`; that
   case is at **`:630`** and #850 repointed the sentence to `:626-641`, which does
   contain it. The span opens four lines early on the previous case's message,
   which is a note rather than a defect: the claim is carried. **The issue places
   this pin at `:154-157`; it is at `:403`.** The claim is right and the line
   number was not, which is the whole argument, in the register
   `registers.yaml` and `check_cluster_citations.py` already use.
2. **[`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99** —
   `ec/tools/test_grade_0751_isolation.py:2232-2233`, cited for the sentence
   *"a capture carrying one is still fatal for the whole run however it got
   there."* That sentence is a **comment at `:2687`**, above
   `test_a_mark_that_is_not_one_of_the_forms_is_an_error`. `:2232-2233` is
   `self.assertEqual(section.count("from the <value> in these files' §6 names"), 2)`,
   which is about a different case entirely. **New when this was written — the
   issue did not name it**, and the file that names it is #498's, not this
   issue's.
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
   `--no-eq-guard` recipe used to patch. `:54` is now `with open(path,
   newline="") as f:`, and `GUARD` **is not in the file at all**: #753 dropped the
   copy-and-patch recipe and replaced it with `--no-eq-guard`. The same stale
   pin, written twice, in two files, both describing a recipe that no longer
   exists. *(`:54` was a blank line on the tree this was written on; #850's
   239 lines into the suite put a statement there. The pin is the same defect
   either way and is now wrong in a second way as well.)*
5. **[`../findings.md`](../findings.md):7185** — `test_xdata_cluster_names.py:286`,
   cited for *"`…:286` carries a third-generation figure in its docstring"*.
   `:286` is `self.assertEqual(names, {})`; the third generation, *"427 clusters
   become 439, 48 … 379"*, is at `:307-309` and the second, *"430 → 439 with 64
   ranks intact and 366 changed"*, beside it. The sentence names neither.
6. **NEW, and all four pins are one assertion.** **`> 300`** —
   `assertGreater(len(moved), 300)` — is at
   [`test_xdata_cluster_names.py:588`](../../ec/tools/test_xdata_cluster_names.py)
   on this tree, and the comment it rests on, *"a regeneration that renumbers
   nothing is not the case the identity columns exist for"*, is at `:582-584`.
   **#850 put 239 lines into that suite and repointed two citations — the
   checklist's `:183` and nothing else — so four pins elsewhere still name a
   line of §2b's comment for it.** They said `:392` and `:387-389` before #890
   repointed them by +25; **they now say `:417` and `:412-414`, and they are
   wrong in the same way for the same reason, which is that a +25 repoint moves
   a pin without changing what it names:**

   - **[`xdata-flip-cause-derivation.md`](xdata-flip-cause-derivation.md):377**
     — `:417`, cited as *"`assertGreater(len(moved), 300)` stays at
     [`test_xdata_cluster_names.py:417`]"*. `:417` is a comment about the
     guard-off pd cluster count `51` (`:392` before the repoint) and is not
     where `> 300` is.
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):15** — `:417`, cited
     as *"whether `> 300` at `ec/tools/test_xdata_cluster_names.py:417` still says
     what the comment beside it says it says"*.
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):404** — `:417`, cited
     as *"**It is the first, and `> 300` stays at `test_xdata_cluster_names.py:417`,
     untouched.**"* — `:392` before #890's repoint
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):416** — `:412-414`, cited
     as *"the comment at `test_xdata_cluster_names.py:412-414` asks that a
     regeneration that renumbers nothing is not the case the identity columns
     exist for"*. `:412-414` is three lines of the §2b comment (`:387-389`
     before #890's repoint), and the comment being quoted is at `:584`.

   **The first three of the four are sentences this census would have caught
   before #850 landed and did not, because nothing ran it then** — which is this
   file's own argument, one merge later, and the strongest argument in it. The
   fourth is the same defect in a `def`-shaped span. None is repointed here: §7
   below says why, and the re-open condition is unchanged.

## The ten that record another line, and why that is the blocker

These are **correct sentences about a line that has moved**, and the reason each
one is right is that `docs/findings.md` §4a-4d requires the superseded value to
stay visible beside its correction. A checker with no rule for them reddens on
sentences that are true, and [`prose-line-citations-held.md`](prose-line-citations-held.md)
§"The one judgement call" is explicit that this is *"the surest way to get a
check switched off, and then nothing would be left."*

**The class has at least eight unmarked shapes of supersession, and the two that
`check_citation_lines.py` already knows — a `>`-opened line and a paragraph
opening with `CORRECTION` — catch exactly two of the ten below, and the two they
catch are both sound citations.** That is the finding, and it is why the verdict
is no checker rather than a deferral:

| shape | where | caught by `check_citation_lines.py`'s vocabulary? |
|---|---|---|
| a repoint list naming the stale value, in running prose | [`../../tools/README.md`](../../tools/README.md):159 — `test_xdata_cluster_names.py:303` → `:307` in four places | **no** |
| a "deliberately not fixed" bullet naming the wrong pin | [`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):446 | **no** |
| a "the citation check caught it here" sentence | [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md):579 — `:513` named *because* it was the wrong line | **no** |
| an "At the time of writing, `file:NNN`:" lead-in to a quoted block | [`testdata-index-suite-count-floor.md`](testdata-index-suite-count-floor.md):25 | **no** |
| a pin qualified by a commit — *"…(`:3608` at `c9e72c1`)"* | [`0751-capture-row-shape.md`](0751-capture-row-shape.md):41 | **no** |
| a dated findings section describing the tree as it was | [`../findings.md`](../findings.md):4206 and `:4208`, §16's pre-#186 fakes | **no** |
| a blockquote correction naming the post-fix location | [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645 | yes — and it is one of the **carries** |
| a section kept whole per §4a-4d, so a pre-#850 value is quoted as it stood | [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):177 — `:307` inside *The residual* , which the branch's own header marks as a record of a tree the file no longer has | **no** |
| a merged-tree note naming both the old and the new value in one sentence | [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md):189 — *"were at `:307` on the pre-#850 file and are at `:339` on this one"* | **no** |
| the same sentence, quoted verbatim inside a `>` block | [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):165 | yes — and it is one of the **records** |

**Eight of the ten are invisible to the vocabulary that already works**, and the
two it does catch are correct sentences. That is not a rule waiting to be
written; it is a shape per author, and the last two rows are the proof that the
blockquote rule is not merely safe here but *insufficient*: the same superseded
value is caught or missed depending only on whether the sentence that quotes it
was written with a `>` in front of it. **The three #850 rows are the sharpest of
the ten**, because all three are the *same* sentence pattern in one tree's own
prose and the two ends of it are two different verdicts.

**What is deliberately not done about them.** Repointing the citing prose is
twenty-four files' worth of edits against open agent PRs, and **every one of
these ten is already recorded in place** — that is what makes each of them
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

1. **The pins are not one kind of thing.** 5 name a `def test_` line, 11 an
   assertion, 9 a comment, **6 a blank line** and 22 something else. The
   citation means "the line where this claim is decided", and that line is the
   test header in 5 cases out of 53. A `def`-anchored rule is wrong; an
   assertion-anchored rule is wrong; a blank-line-anchored rule is worse than
   both, because the blank is an artefact of the span convention and 6 of them
   move whenever a line is inserted one line above. **No single anchor covers
   them and the range form needs a third rule on top.**
2. **Supersession is unmarked prose in this class, and that is the blocker.**
   `check_citation_lines.py` gets away with a two-shape skip because a
   supersession there *has* a shape. Here it does not: eight of the ten
   records above are ordinary running prose or a bullet, and
   [`../../tools/README.md`](../../tools/README.md):159 cites `:303` **because
   `:303` is the stale value it is reporting**. A checker with no skip rule
   reddens on every one of the ten, and with the rule
   `check_citation_lines.py` already has it still reddens on eight more — the
   two it catches are the two `>`-opened rows, and both are correct sentences.
   *("reddens on two … and five more" is what this said with seven records and
   one `>`-opened row; the eight above is what the table now says, and the
   table is the thing a reader can check.)*
3. **A resolver has to read two spellings, and one of them is a judgement.**
   `ec/annotations/xdata-register-map.md`'s `../tools/…` is only a path once you
   know the page writes its paths relative to itself; a resolver that reads
   against the tree alone reports two sound pins as missing files. The tool here
   reads both and prints which answered, and a *checker* could not: it would have
   to pick, and a wrong pick reads as a broken citation.
4. **There is nothing for a file-level rule to catch.** `out-of-range` is 0,
   `unresolved-path` is 0 and `ambiguous-path` is 0. Every pin in the tree names
   a file that exists and a span it has. **The entire defect is in the
   line-*content* half**, and that half is the one a rule cannot make — as
   finding 6 above shows, one assertion and four sentences give four different
   verdicts, none of them mechanically decidable.

**So the tool ships as a census that renders no verdict and never fails on
drift**, and the re-open condition is written down rather than left to a later
reader: a checker becomes writable when **either** this class is taught a
supersession marker its own authors use — a `RECORDED:` prefix, say, which eight
of the ten records above could carry today with a two-word edit each —
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
35 suite(s) run, 1076 tests; one or more FAILED.
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
`ec/tools/test_xdata_cluster_names.py:339` to `:340` — the one-line change a
merge above the `def` makes — the tool reports the new landing and **still exits
0**. *(Re-run at the #850/#887 merge, because #850 is what moved the `def` from
`:307` to `:339`; the method, the shape change and the exit status are the same
three as the `:307` → `:308` pair this replaced, and the old pair is left here
as the record of the tree it was measured on per §4a-4d.)*

```console
$ python3 ec/tools/census_test_line_pins.py --verbose     # before
  docs/findings/xdata-green-set.md:283  ec/tools/test_xdata_cluster_names.py:339  resolves  …  the pin names the path (by-path)
      def test_    def test_the_census_is_the_one_6a_measured(self):
$ python3 ec/tools/census_test_line_pins.py --verbose     # after :339 -> :340
  docs/findings/xdata-green-set.md:283  ec/tools/test_xdata_cluster_names.py:340  resolves  …  the pin names the path (by-path)
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
committed-tree figures was **`50`** — so the moment the suite landed, the census's
own count made the checklist's §2b console-block cluster count `50` (an unrelated
figure that happens to be the same integer) measure `held-by-check-literal`, and
§2b's own `unheld` marking disagreed with the measurement. *(That figure is
**`69`** on the tree this now lands in, for the reason the note at the foot of
this file gives; the exclusion is what keeps it from mattering, which is the
point of an exclusion rather than of the number.)*

That is not a new defect: it is the one `check_doc_figure_pins.py` already
anticipates in its own `SELF_MODULES` comment — *"nothing mechanical can tell a
test that pins a figure against the census from one that pins it against this
tool's verdict about the census — they are the same call shape, and only the
second is circular"* — and #849's own audit would have hit the identical thing if
its suite had named `390`. The general rule is the one the exclusion already
states: **a module that publishes a figure another tool measures cannot also be
the evidence for it.** So the two census modules join that tuple, which is a
constant and a docstring line, and nothing else in that tool moves: on the tree
this was written on §2b went back to **eight held and ten unheld** with a printed
denominator of **`175 literal(s) inside a check`**, which is what
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) quotes, so that transcript
is still the record of the tree it was measured on. *(Neither figure is the
merged tree's, and neither is claimed to be: §2b reads **eighteen held, none
unheld** over **`190 literal(s)`** there because #850 gave each of the ten
unheld figures a literal at an `assertEqual`, which is a different cause with a
different answer. The exclusion did its job either way — without it the census's
own `69` would have been searched like any other integer in `ec/tools/`.)*

**The alternative was to write this suite so it never says `50`, and that is the
accommodation worth naming.** A count that avoids a search is a count that was
chosen to be invisible, and the next reader would have no way to know the figure
was shaped rather than measured. The exclusion is one line, it is the rule the
tool already states, and it costs a denominator that was going to move anyway.

### Merged-tree note (2026-09-26, #891 landing beside #887, #850 and #889)

**Two of this table's own citing lines went stale in the merge, and they are
repointed — which is follow-up 1 below happening to this write-up rather than to
the pages that follow-up names.** The first column is the *citing* line. The
two rows naming `xdata-moved-ranks-fall.md` said `:319` and `:331`, and the
citations they name now sit at `:383` and `:395`; the third row, `:15`, is above
every insertion either merge makes and did not move. **The two were already
stale on `main` before this merge, by twelve lines rather than by sixty-four**,
because #889 put its `deciles()` note into that write-up at `:328` — ahead of
both — and re-measured the census's counts and its `test_*.py` targets without
re-measuring this file's citing column, which the tool cannot see. That is the
exclusion below's price paid once already, and this merge is where it is paid
twice: the merged file names `:383` and `:395`, re-measured against the merged
file, and the three places this file's own prose names the same two citing lines
— finding 6's third and fourth bullets and follow-up 1's `xdata-moved-ranks-fall.md`
pin — are repointed with them so the table and the prose agree.

**Neither the tool's figures nor this table's verdicts move with any of it**,
and that is the shape of the defect rather than a coincidence: a citing line is
not a pin. `census_test_line_pins.py` re-run on the merged tree prints `69
pin(s) in 24 markdown file(s): 44 distinct spelling(s), 40 distinct resolved
target(s)` with `0 out-of-range`, `test_census_test_line_pins.py` is green, and
the verdicts are readings of the *cited* line, which no merge touched. **The
`50` / `37` / `32` this note first carried is the branch's tree**, measured
before #850's nineteen new `test_*.py:NNN` citations were beside it; the `69` /
`44` / `40` the suite pins is the merged tree's, and #891 moves neither.

**What found them was a recount of the sibling class, and the exclusion this
file makes is why nothing here did.** The grep over
`xdata-moved-ranks-fall.md` that `tools/README.md`'s merged-tree notes run
returns **eighteen** on this tree, and **seven of the eighteen are this
file's** — three rows of this table, three bullets of finding 6, and follow-up
1 — because the `):NNN` end of that pattern matches a link followed by a line
number exactly as it matches a citation. The census excludes its own write-up
from its own population, deliberately, so **a pin census cannot see its report
going stale**: the exclusion is right, and this is its price, named here beside
the repointed rows rather than left for the next reader to rediscover. Three
more of the eighteen are #889's three citations — two into this same write-up
(`xdata-decile-small-set-contract.md`'s `:199` and `:220`, stale by the same
insertions and repointed to `:208` and `:240`/`:234` for the same reason) and
one into the tool — which is a sibling's write-up this merge broke in the same
way it broke this one's, and `tools/README.md` carries the count. **The
eighteen is #891's tree, and the #890/#900 merge adds three more to it**, all
from the branch's new `xdata-write-direction-correction.md`, which cites the
write-up three times (`:116`/`:129`, `:148` and `:156-165`) and none of the
three moved. The seven that are this file's are still seven — three rows, three
bullets, follow-up 1 — at the re-registered lines above.

## What is left, as follow-ups

1. **Repointing the citing prose**, which is the issue's own pointer and is not
   done here for the merge-conflict reason above. In the order the table gives
   them: [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99 →
   `:2687`; [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226
   → `:17`; the two `:54` pins → wherever `GUARD` now is, which is nowhere, so
   the sentence rather than the line is what needs rewriting;
   [`../findings.md`](../findings.md):7185's "third-generation" → the sentence
   has to distinguish `:307-309` from `:286` or drop one of the two; **and the
   four `> 300` pins of finding 6 → `:588`, with
   [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):416 → `:582-584`.**
   **Each is one line in one file, which is why they are a follow-up and not a
   merge** — and the `> 300` four is a different kind of follow-up from the rest,
   because #850 is the change that made them stale and #850 is the change that
   would have caught them. It is a useful measurement rather than a defect: the
   same merge moved a line and left four sentences naming where it was.
2. **The wider `.py:NNN` class** — 373 occurrences, 229 targets, 34 files, on the
   measurement above. It is not owned by this census, not by #870 (which is
   `registers.yaml`'s six `xdata_register_map.py` pointers), and not by
   [`prose-line-citations-held.md`](prose-line-citations-held.md) follow-up 2
   (which is the prose → *source-line* checker beside `citation_frames.py`).
   Whatever censuses it inherits this tool's two readings, because a
   tree-only resolver reports two sound pins in one of those files as missing.
3. **A supersession marker for this class**, if the no-checker verdict above is
   ever revisited. Eight of the ten records are ordinary prose and could each
   carry a two-word marker today; a rule reading that marker is the difference
   between a writable check and a checker that reddens on the tree that records
   the drift it exists to catch.
4. **A markdown-to-markdown pin checker**, for
   [`xdata-census-self-test-gate.md`](xdata-census-self-test-gate.md):221's
   `:406-407` → `:446-447` and whatever else that class holds. The issue names
   this one and it is out of scope here for the reason in *What this does not
   check*; it belongs beside `check_citation_lines.py`, which already has the
   supersession vocabulary a markdown-to-markdown rule would need.
5. ~~**The `tools/README.md` totals paragraph is one suite short of the runner**
   and is left that way on purpose.~~ **Done at the #850/#887 merge, and the
   reason this follow-up gave for not doing it is the reason the merge had to.**
   Re-deriving the totals is [`tools-readme-totals.md`](tools-readme-totals.md)'s
   subject and #817's in general, and both #850 and #887 add a *case* or a suite
   without moving that paragraph — so the paragraph went stale twice, in two
   different directions, and the tree it now sits in disagrees with its own
   runner. The totals and the notes that re-derive them are corrected there at
   this merge; what is left of this follow-up is the standing rule the two
   branches agreed on and neither applied, which is that a branch adding a suite
   re-derives the totals in the same PR.

## The `#850`/`#887` merge, 2026-09-26

**Every figure in this file moved, and the mover is #850 rather than the merge.**
Running the tool against #850's own tree and against the tree both issues are in
gives **the same run** — 69 pins, 24 files, 44 spellings, 40 targets, 53
resolves, 16 declined, 5/11/9/6/22 — so nothing in the merge itself moved the
class and every difference from the 50/23/37/32 published above is #850's:
nineteen new `test_*.py:NNN` citations in the markdown (ten of them
`AssertionError:` lines inside a perturbation transcript, which is why `declined`
went 6 → 16 and nothing else did) and 239 lines added to
`ec/tools/test_xdata_cluster_names.py`, which is what displaced the pins already
in the tree. The counts above the transcript, the three tables, the per-pin table
and the suite's own pin in `ec/tools/test_census_test_line_pins.py` are all
re-measured to that run; the 50/23/37/32 and the 44/6 and 5/15/5/8/11 splits stay
visible in the tally sentence rather than being deleted, per §4a-4d.

**Four pins that carry became four that do not, and they are the sharpest thing
this merge found.** #850 put 239 lines into
`ec/tools/test_xdata_cluster_names.py` and repointed exactly one citation — the
checklist's `:183` — so the `> 300` floor and the comment it rests on moved from
`:392`/`:387-389` to `:563`/`:557-559` while four sentences in two other files
still name where they were. **This census is what found them, and the point is
not that a tool caught a merge but that the merge is the first thing that could
have:** the four were wrong the moment #850 landed, on #850's own tree, and
nothing in the pipeline runs this census. Finding 6 names each one. The seventh
sentence — `xdata-4-4-identity-rederivation.md`'s "Deliberately not fixed" entry
at `:446` — went stale a second time in the same merge for the same reason, since
#850 repointed the `:403` it describes; it is a **record** and it is marked as one
in the table, but its own `:459-473` is no longer where the case is either, and
that is named here rather than left for the next reader.

**What is deliberately not re-measured here, and why.** The wider `.py:NNN` class
under *What this does not check* — 373 occurrences, 229 targets, 34 files — is
**not** re-run on this tree. It was measured with a scratch definition that is not
committed, and the four narrower definitions it was reconciled against do not
reproduce it either, so re-deriving it here would mean publishing a *different*
measurement under the same name. It stays as the record of the tree it was
measured on, which is the same treatment the 50/23/37/32 above gets.

**The verdict is unchanged and so is the re-open condition.** Nine pins do not
carry against six, ten record another line against seven, and the argument is the
one this file was written to make: the defect is entirely in the line-*content*
half, the supersession records are unmarked prose in eight of ten shapes, and a
checker built on either would redden on sentences that are true. The
`SELF_MODULES` exclusion above is what stopped this merge from becoming a second
red, and the numbers it was chosen over have moved anyway — which is the argument
in *The one other file this branch had to touch* rather than a reason to soften
it.


Submitting anything upstream is unaffected: this issue touches no driver and no
firmware, and the mission's eventual
`Wer-Wolf/uniwill-laptop`/`tuxedo-drivers` contribution stays a prepared patch
in this repository for a human to submit, per issue #10. Nothing is opened in
another repository.
