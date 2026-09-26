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
73 pin(s) in 26 markdown file(s): 46 distinct spelling(s), 42 distinct resolved target(s)
  57 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 16 declined
  5 def test_, 11 assertion, 9 comment, 6 blank, 26 other (of the pins that resolve)
  read 146 markdown file(s) under the tree, excluding .git/vendor/ and docs/findings/test-line-pin-census.md; resolved against 35 test file(s) in it
  no claim is measured here: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
$ echo $?
0
```

**Correction, 2026-09-26, at the #888 merge: this census is 71 pins in 25 files,
not the 69 in 24 the block above first read after #850.** The block is re-run on
the merged tree and every count this page publishes is re-transcribed from it;
the `50`/`23` this page was written with and the `69`/`24` #850's merge measured
both stay visible in the list below rather than edited out of silence, per §4a-4d.
The movement is
[#888](xdata-moved-ranks-key-collision.md)'s write-up, one new markdown file, and
its two citations of the `> 300` floor. **One new file and two pins, and the two
pins are not the same claim twice**: they are two occurrences of one spelling,
written by-name (`test_xdata_cluster_names.py:563`), where the corpus already
spells the same span
by-path (`ec/tools/test_xdata_cluster_names.py:563`, in
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):324),
so the merged tree carries **one more spelling and no more target** — 44 → 45
spellings, 40 targets unchanged — while resolving goes 53 → **55** and the shape
count moves by exactly the two, `11` → `13` assertions. Nothing else moved: the
sixteen declined, the five `def test_`, the nine comments, the six blanks and the
twenty-two other are the same pins. Both new rows are in the per-pin table below
and both **carry**.

**A third merge sits beside that one and moves the numbers not at all, which is
the point worth making about it.** #891 (#900) also rewrote
`xdata-moved-ranks-fall.md`, and it put **no** `test_*.py:NNN` pin in it: the
run on the three-way merged tree is the block above, byte for byte, including
the `144` markdown files read. So the deltas below are #888's and #850's, and
this merge is the evidence that a change to one of the 25 files can leave the
whole class where it was — the same distinction the "one new spelling and no new
target" paragraph is about, one level up.

**And they carry for a reason the four #850 left behind do not, which is the
half of this that is a finding rather than arithmetic.** #850 moved the floor
from `:392` to `:563` and repointed one citation of five, so four sentences in two
other files still name where it was; this write-up's own two are repointed,
because they are *its own* — a file new to the census, born citing a line that
does not hold the claim is a wrong pin rather than a superseded record, and
§5 of that write-up says so at the length it deserves. So the class gains two
pins, **none of which joins the nine that do not carry**, and the only number
that moves is the shape split. The superseded `:392` is written bare here for
the reason [`../findings.md`](../findings.md) §65 gives: a correction that added
a 72nd pin to the census it is correcting would move the figure it reports.

*(**And at the #888 × #890 merge, two of those four sentences above stop being
true, which is the same class of failure the file is about, produced by the
merge rather than found in the tree.** The paragraphs above are #888's, measured
on #888's tree, and three claims in them do not survive #890 landing beside it:
the two new pins **no longer carry**, the shape split is `5/11/9/6/24` rather
than `5/13/9/6/22`, and the resolved-target count is **41** rather than 40.
The reason is one line moving. `assertGreater(len(moved), 300)` was at
`ec/tools/test_xdata_cluster_names.py:563` on #888's tree and is at **`:588`**
here — #890 put 25 lines into that file above it — so `:563` is now a fixture
line, and the two pins that were *born correct* are two pins that no longer
name what they cite. **That is the cascade this tool's docstring names, caught
in the act rather than in the tree**: a commit moved a line and left two
sentences naming where it was, and the only thing that noticed is a census
nobody runs. The verdict is therefore **`does not carry` for both rows in the
table below**, they are the two new entries in the eleven that do not carry,
and the class's carry count is **32 — unchanged from #850's tree and #890's,
because #888 added two rows that no longer carry to offset the two it added
that did.** The target count moves 40 → 41 because `:563` is a resolved target
`main` had never named, and the assertion split falls 13 → 11 for the same
reason: `:563` is `other` now, not `assertion`. Nothing here is repointed — the
file's own follow-up list below is where repointing lives, and these two rows
join finding 6 in it. **The `144` above is `145` here**: #890 added
`xdata-write-direction-correction.md` and #888 added
`xdata-moved-ranks-key-collision.md`.)*
> **These four figures moved three times, once for each of the merges that
> reached this one, and every time the cause is the tree rather than the
> tool.** #887
> published `50` pins in `23` files, `44` of them resolving and `15` landing on
> an assertion, over `141` markdown files; the #850/#887 merge above took that to
> `69`/`24`/`44`/`40` and `53`/`16`; **#900 then corrected this transcript's own
> `142` to the `143` its tree reads, without moving a pin — a hand-transcribed
> figure drifting, the same class of thing as the citing lines the tool cannot
> see, and named here rather than dropped**; and **this merge, measured here,
> takes the class to `71`/`25`/`45`/`41` and `55`/`16` over `145` markdown
> files.**
>
> **What #885 added is two occurrences of one spelling, and that is the whole of
> the move in occurrences.** Its own citations of
> `ec/tools/test_xdata_cluster_names.py:392` — one in
> [`../findings.md`](../findings.md) §69, for `> 300` staying put, and one in
> [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):446 — are
> **one spelling written twice**, and the target it names is one main's tree
> already carried. Occurrences, files and `resolves` each go up by two against
> `main` and `declined` stays at 16.
>
> **The spelling and target counts do move here, `44` → `45` and `40` → `41`,
> and neither side's merge moved them — the two sides simply never shared a
> tree.** #890 repointed 56 pins in `ec/tools/test_xdata_cluster_names.py` by
> +25, so `main` names that file's `:417` and `:412-414` where #885 still names
> `:392` and `:387-389`; the merged tree carries **both**, which is one more
> spelling and one more target than either side had alone. #885's own note below
> predicted `44`/`40` and was right for the tree it measured; this paragraph
> supersedes that figure rather than arguing with it, and the wrong version is
> left visible in the note per §4a-4d.
>
> **The two land on `other` rather than on the assertion, and that is #890's
> doing, not #885's — so they do not carry.** Both were written on a tree where
> `:392` was `self.assertGreater(len(moved), 300)`; #850 put 239 lines into that
> suite and moved it, #890 put 30 more in, and `:392` is now `decreased, {},` —
> the last line of the very assertion that holds *no* address's `write`
> decreasing. So **`other` goes 22 → 24, `comment` stays at 9 and `assertion`
> stays at 11**, and the two new rows in the per-pin table below are *does not
> carry* — the same defect as finding 6's four, for the same reason, arrived at
> by a different route. #885's own merge note below read `comment` 9 → 11 on the
> tree it measured, where `:392` was still a §2b comment; that reading is left
> beside this one for the same reason. The merge therefore finds two more stale
> pins, and it is this census that finds them, one merge after the four it
> already found for the identical reason. The suite's pinned figures move with
> the transcript and each pin says which addition moved it.
>
> **And at the `#888 × #885` merge, the two classes of new pin land beside each
> other and every count in the transcript above moves once more — `73` pins in
> `26` files, `46` spellings, `42` targets, `57` resolving, `16` declined,
> `5/11/9/6/26` over `146` markdown files read.** Each of those deltas is the sum
> of the two merges above it rather than a third cause: `main` contributed two
> occurrences of `test_xdata_cluster_names.py:563` and one new file, `#885`
> contributed two occurrences of `ec/tools/test_xdata_cluster_names.py:392` and
> one new file, and neither spelling or target was the other's. **The two sets of
> defective rows are disjoint**, `:563` in `xdata-moved-ranks-key-collision.md`
> (finding 7) and `:392` in [`../findings.md`](../findings.md) §69 and
> [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md) (finding 8),
> so the eleven neither merge had alone is **thirteen** and the carry count is
> **32** — the same number `main` had before either, reached twice over by adding
> four rows that do not carry. The shape split follows arithmetically: the two
> `:563` rows and the two `:392` rows are all `other` on this tree, so `other`
> goes 24 → **26** and nothing else moves. The superseded `71`/`25`/`45`/`41` and
> `5/11/9/6/24` are the records of the two trees above and stay visible per
> §4a-4d; the suite's pin carries a comment saying which addition moved it.

**Each count below is a different thing, and every one of them is printed**,
which is the only reason a census like this can be trusted: a headcount that
cannot be reconciled against itself is the failure it is measuring.

- **73 occurrences** — every pin, counted once per place it is written. Thirty
  spellings are written once, seven twice, eight three times and one five times
  (`ec/tools/test_xdata_cluster_names.py:473`, five times over), which is the
  whole of the gap: `7 + 16 + 4 = 27`, and `73 - 27 = 46`. *(`:448` is what this
  bullet named on #888's tree and is stale here: #890 repointed that spelling
  by +25 in the four files that carry it, and this file's own mentions of it
  are not counted by the census — the tool excludes this file — so nothing
  repointed them. The distribution beside it is unchanged and reproduces. The
  50/23/37/32 figures #887 published and the 69 this bullet read at the #850
  merge are the record of the trees they were measured on and stay visible here
  per §4a-4d; the gap was 13, then 25, then 26, and is 27 above. **The last step
  is the only one two merges have ever taken together**: the gap is 26 on each of
  the two trees alone and 27 on the tree carrying both, because the `:392` pair
  #885 wrote lands *beside* the `:417` pair #890's repoint created rather than
  replacing it.)*
- **46 distinct spellings** — the pin exactly as written, so `test_a.py:12` and
  `ec/tools/test_a.py:12` are two. This is the figure the issue's grep reported
  for a tree half this size and it is the one that moved least. *(`#885`'s own
  merge note read `45` and `#887` read `37`; the tree this bullet sits in
  carries `test_xdata_cluster_names.py:563` beside the `:392` pair `#885`
  added, so 46 is the sum of two unrelated additions rather than a third
  revision of the same one.)*
- **42 distinct resolved targets** — distinct `(file, span)` pairs after
  resolution, so the two spellings of one span are one target. **Both merges'
  four new pins are the whole of the move, 40 → 42**, and the two got there by
  opposite routes, which is why neither merge's note predicted the other's
  figure. On #888's tree the corpus already wrote the same span **by path** —
  `ec/tools/test_xdata_cluster_names.py:563` in
  [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):334
  — so the two new by-name pins arrived against a target that was already there
  and this count was argued not to move. **#890 repointed that by-path spelling
  by +25, to `:588`, and left the by-name one at `:563`**: the two no longer name
  the same line, so they are now two targets rather than one, and a figure two
  merges ago was measured as unmovable has moved by one. **#885's two arrived
  the other way** — `ec/tools/test_xdata_cluster_names.py:392`, which neither
  tree carried, so they added a target rather than splitting one. It is the same
  line moving as finding 7 below, counted from the other end, and a different
  line moving as finding 8.
- **26 files** carry at least one;
  [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) carries
  ten, [`doc-figure-pin-audit.md`](doc-figure-pin-audit.md) thirteen,
  [`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md)
  nine and [`../findings.md`](../findings.md) six.

**Two of the planning stage's numbers did not reproduce, and both are the
extractor's fault rather than the tree's.** The issue's own grep reported 37
distinct pins across 22 files; the plan built on it counted 49 occurrences over
the same 22, and **called 12 of those 49 an ambiguous `tools/` prefix**. This
tree carries **73 occurrences across 26 files** — twenty-three pins and three
files written since, two of them by [#888](xdata-moved-ranks-key-collision.md)'s
own write-up and two by `#885`'s (the corrections above) — and
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

**So the measured headcount of this class is 73 occurrences, 46 spellings, 42
resolved targets — and zero of the twelve the plan's scan called an ambiguous
prefix is one.** The figures that moved from the plan's are recorded as a defect
in the method that produced them rather than as a drift in the tree, and a census
that reports the wrong population with great confidence is worth less than no
census. The `50`/`23` and `69`/`24` this paragraph was written with are the
record of the two trees it was measured on, and stay visible beside the
`73`/`26` for the same reason they do everywhere else in this file.

### Verdicts, and what each one is not

| verdict | what it means | here |
|---|---|---|
| `resolves` | the file was found and the span is one it has | **57** |
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
| other | 26 | a `def` that is not a test, an assignment, a `setUpClass` body |

*(The split has now been measured five times and the only rows that have ever
moved are the assertions and `other`: **5 / 15 / 5 / 8 / 11 over 44** as the
issue was filed, **5 / 11 / 9 / 6 / 22 over 53** after #850, **5 / 13 / 9 / 6 / 22
over 55** on the #888 × #891 tree, **5 / 11 / 9 / 6 / 24 over 55** on the
#888 × #890 one, and the **5 / 11 / 9 / 6 / 26 over 57** above. The first four
are the record of the trees they were taken on and stay visible per §4a-4d. The
two that moved back are the `> 300` floor's own `assertGreater` and the `other`
row it became when #890 put 25 lines above it; the last step is arithmetic rather
than a fourth cause, being the two `:563` rows and the two `:392` rows the two
merges added between them, all four of which are `other` here. That a
figure this close to stable still moves at every one of the merges since
the issue was filed is the reason the distribution is printed on every run rather
than quoted once.)*

**Six of the 57 resolving pins land on a blank line**, and that is the house
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
| [`../findings.md`](../findings.md):9028 | `ec/tools/test_xdata_cluster_names.py:392` | by-path | other | **does not carry** |
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
| [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622 | `ec/tools/test_xdata_cluster_names.py:392` | by-path | other | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):15 | `ec/tools/test_xdata_cluster_names.py:417` | by-path | comment | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):415 | `test_xdata_cluster_names.py:417` | by-name | comment | **does not carry** |
| [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):427 | `test_xdata_cluster_names.py:412-414` | by-name | comment | **does not carry** |
| [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):212 | `test_xdata_cluster_names.py:563` | by-name | other | **does not carry** † |
| [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):323 | `test_xdata_cluster_names.py:563` | by-name | other | **does not carry** † |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):28 | `ec/tools/test_xdata_cluster_names.py:833` | by-path | other | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):132 | `test_xdata_cluster_names.py:149-153` | by-name | def test_ | carries |
| [`xdata-names-file-census-anchor.md`](xdata-names-file-census-anchor.md):149 | `test_xdata_cluster_names.py:845-851` | by-name | def test_ | carries |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):1341 | `../tools/test_xdata_cluster_names.py:54` | beside | other | **does not carry** |
| [`../../ec/annotations/xdata-register-map.md`](../../ec/annotations/xdata-register-map.md):2645 | `../tools/test_xdata_cluster_names.py:68-90` | beside | blank | carries |
| [`../../tools/README.md`](../../tools/README.md):159 | `test_xdata_cluster_names.py:303` | by-name | other | **records another line** |

**32 carry, 2 carry on the adjacent line, 13 do not carry, 10 record another line
on purpose, 16 are declined, and none is unresolvable.** *(Those are the counts
on the merged tree; the 27/3/1/6/7/6 this page was written with, the
32/3/0/9/10/16 #850's merge measured, the 34/2/9/10/16 #888's and the
32/2/11/10/16 #888 × #890's are the record of the trees they were taken on and
are kept in the sentence rather than deleted, per §4a-4d. Four moves, and the
fourth is the one worth reading twice: #850's took the class 50 → 69 pins, #888's
took it 69 → 71 by adding two rows that **carried** on its own tree, #890's
landing beside them took those same two rows to **`does not carry`** — so the
carry count is **32**, the same number `main` had before either of them, and the
headcount is two higher than it was — and #885's landing beside those added two
more rows that do not carry either, for the same reason and by a different route.
**The carry count is therefore 32 for the second time running and the headcount
is 73, four higher than `main` had**: four rows added, none of which carries.
The thirteen that do not carry are the nine #850 left, #888's two and #885's
two; see the correction under the transcript above and the note at the foot of
this file.)*
**"carries, adjacent"** is
a pin one line off the thing it names, and it is two of seventy-three because
this corpus writes *"is at `:1862`"* against a `def` on the next line. No rule can
decide whether that is a pin or a typo, which is the first reason the judgement
half is a table and not a verdict.
**The 9 → 11 is #885's and the 11 → 13 is this merge's, and the two new
citations are where #885's half of that lands in the table** — both in the *does
not carry* column rather than the *carries* one
their own write-up predicted, because `:392` is not where the assertion is on
this tree. One is [`../findings.md`](../findings.md) §69's, one is
[`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622's, and
together with finding 6's four they make six pins naming `:392`, `:417` or
`:412-414` for the `> 300` assertion, which is at **`:588`**. The two `:563`
pins of finding 7 name the same assertion a third way round and are **not** in
that six: they are counted apart precisely because they got wrong by a different
cause, a line moving rather than a line never having been the one named.

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

‡ **What the tree carrying both #890 and #900 moved, re-registered against it,
and still no count.** The *cited* targets are this branch's, because #890's 25
lines are what moved them; the *citing* lines are likewise this tree's, because
neither issue had them. Four rows re-registered: `xdata-moved-ranks-fall.md`'s
second and third at `:352` and `:364` on the branch and `:383` and `:395` on
main are at **`:404` and `:416`** here, and `../findings.md`'s `:7364` and
`:7425` and [`../../tools/README.md`](../../tools/README.md)'s `:157` — stale
on `main` before this branch, by #900's edits to those two files — are at
**`:7369`, `:7430` and `:159`**. **The one figure this branch does move is the
`read N markdown file(s)` line of the transcript above, `143` → `144`:** #890
added `docs/findings/xdata-write-direction-correction.md` and #900 added no
markdown file at all — its `142` → `143` was a correction of a stale
transcript, since the tool reports `143` on the tree this branch forked from as
well as on `main` — and the new file carries no `test_*.py:NNN` pin, which is
why 69/24/44/40 and 53/16 are untouched while the denominator moved. The three
prose places that name `tools/README.md:157` are repointed with the row.

**The "carries in part" row is gone from this tree, and the argument it carried
is not.** It was the sharpest of the three qualified values:
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):433
cited `:286` for *two* figures in the suite's docstring and named the second,
while [`../findings.md`](../findings.md):7190 says `:286` holds a third-generation
figure and `:286` was the second — **one line, two verdicts, and nothing
mechanical in the tree able to tell them apart**, which was the argument for the
split in one sentence. #850 repointed `:433` to `:307`, which carries, so
`:286` now has one verdict rather than two. The category is empty here and the
second half of the split is still right; what is lost is a worked example of it,
and it is named rather than papered over.

## The thirteen that do not carry

*(The nine this section was written with, the two the #888 × #890 merge added and
the two the #888 × #885 one added beside them are all below; the `9`s and the
`11`s in the lead paragraphs that this one replaces are kept visible in the
italicised notes under it rather than edited out, per `../findings.md` §4a-4d.)*

**Eight items below and thirteen pins, and the sixth is the reason the count is
not one higher than the items**: finding 1 was one of the six when this was
written and #850
repointed it into carrying, so it is kept struck through rather than deleted.
Finding 4 is one stale pin written twice, in two files, describing the same
removed constant; finding 6 is one moved assertion written **four** times across
**two** files; finding 7 is the same assertion written **twice** more by #888; and
finding 8 the same assertion written **twice** again by #885 — **eight pins
naming one line, in five files**, and the reason thirteen pins sit under eight
items. **The issue's own citing-line reference is not among
the thirteen** — it
was finding 1, and on this tree it carries, which is the one claim of the issue's
two that #850's own change turned into a `carries` rather than a
`does not carry`. Five of the thirteen carried over from the six this section
recorded; **four are #850's** (all four finding 6), **two are #888's** (both
finding 7) and **two are #885's** (both finding 8).
**Finding 7 is the eleventh and finding 8 the thirteenth, and they are the only
two a merge in this repository produced rather than found lying in the tree** —
two pins that were *born* correct and were made wrong, in the same commit that
made this file's own §2 transcription stale, by moving the line they name, and
two that were born correct against a line another branch had already moved. The
count is thirteen because four pins that carried on their own trees stopped
carrying here, not because anything about the other nine moved.

*(The lead paragraph as #850's merge wrote it — **six items and nine pins**, one
struck through, four new and all four #850's — is the record of that tree and is
carried in this note rather than edited out of the sentence above, per
`../findings.md` §4a-4d, and the heading's `9` is its record in the same way.
What moved at the #888 × #890 merge is the heading and the two sentences that
follow it, and nothing in the list below items 1–6 changed verdict; what moved
at the #888 × #885 one is the heading, those two sentences and the addition of
item 8. **The two sets are disjoint** — `:563` and `:392`
are different lines in different files — so nothing in finding 7 changed verdict
when finding 8 landed beside it.)*

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
5. **[`../findings.md`](../findings.md):7190** — `test_xdata_cluster_names.py:286`,
   cited for *"`…:286` carries a third-generation figure in its docstring"*.
   `:286` is `self.assertEqual(names, {})`; the third generation, *"427 clusters
   become 439, 48 … 379"*, is at `:307-309` and the second, *"430 → 439 with 64
   ranks intact and 366 changed"*, beside it. The sentence names neither.
6. **All four pins are one assertion, and #850 is what moved it.** **`> 300`** —
   `assertGreater(len(moved), 300)` — is at
   [`test_xdata_cluster_names.py:588`](../../ec/tools/test_xdata_cluster_names.py)
   on this tree, and the comment it rests on, *"a regeneration that renumbers
   nothing is not the case the identity columns exist for"*, is at `:584-585`.
   *(`:582-584` is what this item first recorded; the quoted comment is two
   lines, and `:582` is the `def test_the_regeneration_really_moves_the_ranks`
   above them. Re-opened against the merged file, where the two sit eleven lines
   lower than they did on #890's tree.)*
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
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):415** — `:417`, cited
     as *"**It is the first, and `> 300` stays at `test_xdata_cluster_names.py:417`,
     untouched.**"* — `:392` before #890's repoint
   - **[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):427** — `:412-414`, cited
     as *"the comment at `test_xdata_cluster_names.py:412-414` asks that a
     regeneration that renumbers nothing is not the case the identity columns
     exist for"*. `:412-414` is three lines of the §2b comment (`:387-389`
     before #890's repoint), and the comment being quoted is at `:584-585`.
   **The first three of the four are sentences this census would have caught
   before #850 landed and did not, because nothing ran it then** — which is this
   file's own argument, one merge later, and the strongest argument in it. The
   fourth is the same defect in a `def`-shaped span. None is repointed here: §7
   below says why, and the re-open condition is unchanged.
7. **NEW, and the only entry here a merge produced rather than found.** **Both
   pins are one line, written twice, in one file** —
   [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):212
   and `:323`, both naming `test_xdata_cluster_names.py:563` for
   `assertGreater(len(moved), 300)`. **On #888's tree that was correct**: the
   floor was at `:563` there, and §5 of that write-up goes at some length into
   why a file new to the census must cite a line that holds the claim rather
   than one a superseded record happens to mention. **#890 then put 25 lines
   into that suite above it, moving the floor to `:588`, and both pins now name
   `("0x0843", ("84", "42"), ("126", "0"))):` — a fixture line.** So the two
   sentences are defective in exactly the way item 6's four are, and they got
   there the same way, and neither #888 nor this census's author saw it happen:
   the pins were correct when written and the line moved underneath them. The
   `assertion` → `other` reclassification in §2's transcript and the `40` → `41`
   in its target count are the same two rows and nothing else. **Not repointed
   here**, for §7's reason; they are named in that follow-up list instead.


   **The last two bullets' citing lines are the second repointing of these two
   rows, and all three values stay in the table above rather than being
   deleted.** The file read `:319`/`:331` when this table was written; **#885,
   working from the pre-#889 base, repointed them to `:331`/`:343` and was right
   for its own tree**; **#900 repointed them to `:383`/`:395` and was right for
   its own**; and **#890's own twenty-five lines into the fall write-up put them
   at `:404`/`:416`, which is what the merged tree reads, re-measured by
   `--verbose` after the merge.** #885's forty-one lines into that write-up all
   land below `:395`, so its side did not move the pair a second time — which is
   where the two sides came out differently, and the `#885` merge note below says
   the same of it at length.
8. **NEW, and both pins are the same assertion finding 6 names, one merge
   later.** #885's merge added two more citations of
   `ec/tools/test_xdata_cluster_names.py:392`, one in
   [`../findings.md`](../findings.md) §69 and one in
   [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622, and
   **both were correct on the tree they were written on** — `:392` was the
   `assertGreater` there, and #885's own write-up says so and reports both as
   carrying. They are the same defect finding 6 records, arrived at without
   anyone moving a line: #850 moved the assertion in the same window, the two
   branches never shared a tree, and each was written against a `:392` that was
   right for it. **`:392` names a different line on every tree since** — a §2b
   comment where #885 read it, `decreased, {},` on the tree this file now sits
   in, where #890 has since put the assertion that no address's `write`
   decreases — so both land on a line that does not carry the claim, and land on
   a *different* wrong line on the two trees.

   **This is the sharpest result in the file, and it is a measure of the method
   rather than of either branch.** #885 predicted its own two pins would carry
   and the prediction was right *for its tree*; #850 predicted nothing and was
   right for its own; #888 predicted the same for its two and was right for
   *its* tree too, and wrong here for the mirror-image reason. None of the three
   was wrong. A census run only on the merged tree
   cannot tell a pin that was always wrong from one that a concurrent merge made
   wrong, so this section records the cause rather than the verdict alone: **six
   pins in four files now name `:392`, `:417` or `:412-414` for the `> 300`
   assertion, which is at `:588`**, four of them because #850 moved it and two
   because a
   branch written against the old line landed beside it; **and two more, in a
   fifth file, name `:563` for the same assertion, which is finding 7 and is
   counted apart because the line moved under those rather than having been
   moved before they were written.** None of the eight is repointed here,
   for the reason the follow-up list below gives.

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
twenty-six files' worth of edits against open agent PRs, and **every one of
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
   assertion, 9 a comment, **6 a blank line** and 26 something else. The
   citation means "the line where this claim is decided", and that line is the
   test header in 5 cases out of 57. A `def`-anchored rule is wrong; an
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
   verdicts, none of them mechanically decidable. Findings 7 and 8 make the same
   point from the other side: **eight sentences naming one assertion, written by
   three branches that never shared a tree, all of them right where they were
   written and all of them wrong here** — and nothing in a merged tree
   distinguishes the two cases.

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
Ran 41 tests in 0.877s

OK
$ bash tools/run-tests.sh
35 suite(s) run, 1076 tests; one or more FAILED.
```

**The one red suite is not this branch's.** It is
`ec/tools/test_check_cluster_citations.py`, 48 cases, on
`docs/findings/xdata-cluster-names-guard-off-recipe.md:220` with the same two
`0x0464`/`0x0465` cluster disagreements `tools/README.md` has named as
reproducing on a clean `origin/main` since #822. **Confirmed rather than assumed
at the #885 merge**: the same suite fails the same single case on a clean
`origin/main` worktree, and `check_cluster_citations.py` reports the same two
citations before and after this merge. This change touches no cluster,
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
**`69`** after #850's merge, **`71`** after #888's and **`73`** on the tree this
now lands in, for the reason the note at the foot of this file gives; the
exclusion is what keeps it from mattering, which is the point of an exclusion
rather than of the number — and it is **preventive rather than current** on this
tree, since `73` is not a figure §2b's tables hold, which is checked rather than
assumed.)*
§2b's own `unheld` marking disagreed with the measurement. *(That figure is:
**`71`** on the tree #885 merged into, `69` at the #850 merge and `50` when the
suite landed — for the reason the note at the foot of this file gives. `71`
collides with nothing in §2b, so the measurement below is re-run on the merged
tree and not carried over. The exclusion is what keeps the question from
mattering at all, which is the point of an exclusion rather than of the
number.)*

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
own `73` would have been searched like any other integer in `ec/tools/`.)*

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

**Correction to the sentence above, made at the #885 merge: it named three
places and the tree carried two.** Finding 6's third and fourth bullets were
repointed to `:383`/`:395`; **follow-up 1's `xdata-moved-ranks-fall.md` pin still
read `:331` in this note's own tree**, which was the pre-#889 value the same note
calls stale two paragraphs up. It reads `:395` now, and the `#885` merge note
below carries the third repointing. The claim was not "not found by this method"
— it was checked and the check came back short, which is the only kind of
correction §4a-4d is for.

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
eighteen is #891's tree, and this branch adds three more to it**, all
from the branch's new `xdata-write-direction-correction.md`, which cites the
write-up three times (`:116`/`:129`, `:148` and `:156-165`) and none of the
three moved. The seven that are this file's are still seven — three rows, three
bullets, follow-up 1 — at the re-registered lines above.

### Merged-tree note (2026-09-26, #888 landing beside #891)

**The block at the top of this file re-runs and every one of its numbers is
unchanged, and that is a measurement rather than an absence of one.** #888 and
#891 both rewrote `xdata-moved-ranks-fall.md`; #888's two new pins are already
counted in the `71`/`25`/`45`/`55` block, and #891's rewrite of the same file put
**no** `test_*.py:NNN` pin in it, so the three-way merge is that run byte for
byte — `144` markdown files read included. **The two merges' edits to that one
file therefore do not cancel**: #891 moved the two stale citing lines to `:383`
and `:395`, and #888's two added `cluster_key unique …` lines in §1–§2 plus its
six `ok` lines and their notes in §9 moved them again, to **`:394`** and
**`:406`** on the merged file. This file's table and finding 6's two bullets are
re-measured to those, and follow-up 1's `xdata-moved-ranks-fall.md` pin — which
the #891 note claimed to have repointed and did not — is repointed with them, so
the table and the prose agree for the second time in two merges.

**Two more citing lines were stale and are now fixed, both of them leftovers
rather than anything this merge broke.** Finding 5 and follow-up 1 both named
[`../findings.md`](../findings.md)`:7185` for the "third-generation" pin the table
above carries at **`:7190`**; the tool's own `--verbose` run puts it at 7190 and
both prose references now say so. **Three lines in
`xdata-moved-ranks-second-count.md`** named the fall file at `:458`, `:535` and
`:564` and are repointed to `:469`, `:546` and `:575` — its `:590` citation of
the §9 transcript is above every insertion and did not move, which is a useful
reminder that these citations are not all displaced together. None of this is
visible to the tool, which is the whole subject of the note above: **a citing
line is not a pin, and a pin census cannot see its own report go stale.** The
exclusion stays; the price is paid by re-reading, as it was the last two times.

**The verdicts, the nine that do not carry, the ten that record another line and
the re-open condition are all unchanged.** The re-run changes no *cited* line —
#850's `> 300` floor is at `:563` on this tree whichever file cites it — so the
table's readings are untouched and only its first column moved.

*(**And at the #888 × #890 merge, that last paragraph is the one that does not
survive, along with two of the citing lines above it.** `:563` was the floor on
#888's tree and is at `:588` here, so the re-run *does* change cited lines this
time, and in one file only: `ec/tools/test_xdata_cluster_names.py`. That is
enough to move three of this page's own numbers — the target count 40 → 41, the
shape split `5/13/9/6/22` → `5/11/9/6/24`, and the nine that do not carry → the
eleven, the two new ones being #888's own pins, which #888 measured as carrying
and this merge made not carry. It changes no verdict among the nine #850 left, so
the readings are still untouched where it matters; what moves is the two that
were born correct. **The citing lines moved too**, for the reason the paragraph
above spends itself on: `xdata-moved-ranks-fall.md`'s two stale ones are at
**`:415`** and **`:427`** on the merged file rather than `:394` and `:406`, the
`#891` note's `:383`/`:395` and this note's `:394`/`:406` both being the record
of the trees they were measured on. The table, finding 6's bullets, finding 7
and follow-up 1 are all re-measured to `:415`/`:427`, and
`xdata-moved-ranks-second-count.md`'s four fall-file anchors are repointed a
second time — `:469`/`:546`/`:575`/`:601` → **`:490`/`:567`/`:596`/`:622`** — while
its `:3`, for the fourth time running, is still above every insertion any of
these merges makes. `144` markdown files read becomes `145`.)*

## What is left, as follow-ups

1. **Repointing the citing prose**, which is the issue's own pointer and is not
   done here for the merge-conflict reason above. In the order the table gives
   them: [`0751-grader-block-scoping.md`](0751-grader-block-scoping.md):99 →
   `:2687`; [`0751-grader-unplaced-window-scope.md`](0751-grader-unplaced-window-scope.md):226
   → `:17`; the two `:54` pins → wherever `GUARD` now is, which is nowhere, so
   the sentence rather than the line is what needs rewriting;
   [`../findings.md`](../findings.md):7190's "third-generation" → the sentence
   has to distinguish `:307-309` from `:286` or drop one of the two; **and the
   four `> 300` pins of finding 6 → `:588`, with
   [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):427 → `:584-585`;
   and the two `:563` pins of finding 7 →
   [`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md):212
   and `:323` → `:588`, which is the same target the other four name.**
   **Each is one line in one file, which is why they are a follow-up and not a
   merge** — and the `> 300` four is a different kind of follow-up from the rest,
   because #850 is the change that made them stale and #850 is the change that
   would have caught them. It is a useful measurement rather than a defect: the
   same merge moved a line and left four sentences naming where it was.
   **Finding 7's two are a third kind of follow-up again, and the only one with
   a different author**: #850's four were stale in the tree when this census
   found them, whereas these two were *correct* when #888 wrote them and were
   made stale by #890's repoint landing beside it in this very merge. Nothing in
   #888 could have known, and nothing repointed them, because the file that
   carries them was new to the census and the tool that would have said so is
   not in any gate. That is this file's own argument — *no checker* — costing
   two pins, and it is the strongest evidence in it for a supersession marker.
   **And finding 8's two are a fourth kind again, and the only kind where no
   tree is wrong at any point.** Taken together the eight `> 300` pins are one
   follow-up with four causes: #850's four, #888's two and #885's two all →
   `:588`, with
   [`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):415 and `:427` →
   `:584-585`, and the two `:392` pins named in
   [`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):622 and
   [`../findings.md`](../findings.md) §69 → `:588`, which is the same target the
   other six name. #850 is the change that made four of them stale and the
   change that would have caught them; #890's repoint is the change that made
   the next two stale *after* they had been written correctly; and #885's merge
   added the last two against a `:392` that was right on the tree it was written
   on. It is a useful measurement rather than a defect: one merge moved a line
   and left four sentences naming where it was, a second moved it again and left
   two more born wrong, and a third branch then wrote two more against the same
   number without any of the three trees being wrong.
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

## The `#888` merge, 2026-09-26

*(This section records the **#888 × #891** merge, and it is kept whole. Three of
its claims do not survive #890 landing beside them — the target count, the shape
split and the "both carry" — and the section immediately below this one is where
that is taken back. The `40 targets unchanged`, `5/13/9/6/22`, the
"target not moving is the interesting half" paragraph and the "the nine that do
not carry stay nine" are the record of the tree #888 × #891 produced, per
`../findings.md` §4a-4d, and each is true of it.)*

**Two pins and one file, and this is the smallest move the census has recorded
between two of its own measurements.** #888 adds
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md), which
is new to the census, and that page cites the `> 300` floor twice. The run goes
**69 → 71 pins, 24 → 25 files, 44 → 45 spellings, 40 targets unchanged, 53 → 55
resolves, 16 declined unchanged, 5/11/9/6/22 → 5/13/9/6/22** — and every one of
those deltas is accounted for by the two citations, with no second cause.

**The target not moving is the interesting half, and it is a distinction worth
having rather than a coincidence.** The two new pins are two occurrences of *one*
spelling, written by-name (`test_xdata_cluster_names.py:563`), and the corpus
already writes that same span by-path
(`ec/tools/test_xdata_cluster_names.py:563`, in the checklist at `:324`) — so two
occurrences and a spelling arrive against a *target* that was already there. Had
the same page written the path, this merge would have moved **nothing at all**,
which is the cleanest possible demonstration that **a census's spelling count and
its target count are two measurements, not one**, and that a page adding a
citation can be invisible to the second while visible to the first.

**Both carry, and that is the second thing this merge is about.** #850 left four
sentences naming the floor at `:392` and recorded them here rather than repointing
them, for the reason *What is deliberately not done about them* gives: a drifted
pin inside an existing argument is a **superseded record**, and editing it would
delete the thing §4a-4d exists to preserve. #888's two are not that. They are a
page's *own* citations, in a file no other issue has read, written against the
tree this branch forked from and wrong the moment it landed — and a new file
born citing a line that does not hold its claim is a **wrong pin**, not a record.
So they are repointed to `:563`, the superseded `:392` stays written bare beside
them, and §5 of that write-up argues the distinction at the length it deserves.
The consequence for this census is one line: **the nine that do not carry stay
nine.** A merge that adds two citations and moves the defect count by zero is
worth more than one that adds two and moves it by two, and it is the argument for
keeping a class's superseded values visible that this file keeps having to make.

**What is deliberately not re-measured here, and why.** The wider `.py:NNN` class
under *What this does not check* — 373 occurrences, 229 targets, 34 files — is
**not** re-run at this merge either, for the same reason as the last: the
definition it was measured with is not committed, so re-deriving it would publish
a different measurement under the same name. What *is* true, and is an argument
rather than a measurement, is the narrow one: **#888 adds only `test_*.py:NNN`
pins, which are the excluded class, so its own two cannot move the wider figure
at all.** That is a fact about what #888 added, not a re-run, and the difference
is the reason it is written here as its own paragraph.

**The verdict is unchanged and so is the re-open condition.** Nine pins do not
carry and ten record another line, exactly as the `#850`/`#887` merge above left
them, and the argument is the one this file was written to make: the defect is
entirely in the line-*content* half, the supersession records are unmarked prose in
eight of ten shapes, and a checker built on either would redden on sentences that
are true. Nothing here moves that, and nothing here is a reason to soften it.

## The `#888` × `#890` merge, 2026-09-26

**One line moved, and it took three of the figures above with it.** #890's
commit put 25 lines into `ec/tools/test_xdata_cluster_names.py` above
`assertGreater(len(moved), 300)`, so the floor is at **`:588`** and not the
`:563` the section above measured. The census run on the merged tree is
**71 pins, 25 files, 45 spellings, 41 targets, 55 resolves, 16 declined,
5/11/9/6/24, 145 markdown files read** — and the three deltas are all the same
line:

- **the target count moves 40 → 41.** The section above's central observation was
  that #888's two by-name pins at `test_xdata_cluster_names.py:563` resolved to a
  target the corpus already had, because the checklist writes the same span
  **by path** at `ec/tools/test_xdata_cluster_names.py:563`. #890 repointed that
  by-path spelling by +25 to `:588` and left the by-name one at `:563`. They no
  longer name the same line, so they are two targets rather than one. **The
  distinction the section above draws still holds and no longer rescues the
  number**: a spelling count and a target count are two measurements, but the
  second one only stayed still for a merge that had not yet happened.
- **the shape split moves 5/13/9/6/22 → 5/11/9/6/24.** `:563` was an
  `assertion` on #888's tree because that is where the floor was, and is `other`
  here. Nothing about the pins changed; the line they name did.
- **the nine that do not carry become eleven.** #888's two were measured as
  carrying and are now **`does not carry`**, and the carry count is **32** —
  the same number `main` had before either merge, arrived at by a different
  route. They are finding 7, and follow-up 1 names them.

**This is the file's argument arriving as evidence, and it is worth being precise
about what it does and does not show.** It does *not* show the class is
checkable: two more defective sentences is not a rule, and a checker would still
have to decide what to do about the ten that record another line. It shows the
**cost of not running this census at all**, which is the cost the "no checker"
verdict below has been paying quietly for four merges. #888's write-up was
careful to cite `:563` *because* `:563` was right, and added a paragraph
explaining why a new file must not cite a line it merely mentions; #890 moved the
line anyway, in a commit that had no reason to know the sentence existed, and
nothing in the pipeline noticed. That is not a defect in #888's reasoning and not
a defect in #890's — it is the ordinary failure mode of `file:line` prose in a
repository where **56 pins were already stale** for the same reason before either
of them. The difference is that those 56 were wrong in the tree, and these two
became wrong in the merge, which is the version of the problem no amount of
re-reading a write-up catches.

**Not re-measured here**, for the same reason as the two sections above: the
wider `.py:NNN` class is not re-run, and #890's commit adds no `test_*.py:NNN`
pin, so it cannot move that figure either. The re-open condition and the ten that
record another line are unchanged, and the argument of *Why no checker* stands.

## The `#885` merge, 2026-09-26

*(This section records the tree `#885` merged into on its own, before #888's two
pins were in it, and it is kept whole. Every headline figure in it is lower
than the tree the section below this one measures — two occurrences, one file,
one spelling, one target and two resolving pins short of it — because the two
merges added four occurrences between them rather than because anything here is
in dispute; the correction under the transcript above is where that is taken
back.)*

**Two figures moved, and the cause is #885's two citations rather than anything
either merge did to the class.** #885's merge added two occurrences of one
spelling — `ec/tools/test_xdata_cluster_names.py:392`, once in
[`../findings.md`](../findings.md) §69 and once in
[`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md):446 (the table
above re-registers it at `:622`) — and that
is the whole of it in occurrences: **71 pins, 25 files, 45 spellings, 41 targets,
55 resolves,
16 declined, 5/11/9/6/24** over 145 markdown files, against 69/24/44/40/53/16/
5/11/9/6/22 on `main`. Occurrences, files and `resolves` each go up by two over
`main` and `declined` is untouched. Both counts were run
rather than derived: the tool on the merged tree and on a clean `origin/main`
worktree, which prints main's 69/24/44/40 exactly.

> **Correction to the two paragraphs below, at the tree this merge actually
> lands in, and it is the one place this file's own re-measure was wrong twice
> over.** This note originally read `44` spellings and `40` targets, on the
> reasoning that `main` already counted both the `:392` spelling and its target
> so neither could move. That is true of the tree #885 merged into and false of
> this one, and the reason is #890: its +25 repoint made `main` name
> `ec/tools/test_xdata_cluster_names.py:417` and `:412-414` where #885 still
> names `:392`, so the merged tree carries **both** sets — one more spelling and
> one more target than either side had. The same thirty lines moved `:392`
> itself from the §2b comment #885 read there to `decreased, {},`, so the second
> paragraph's `comment` 9 → 11 is really `other` 22 → 24, and `assertion` stays
> at 11 because `:392` is not an assertion on either tree. **#885 was right for
> the tree it measured and this is the record of that tree**, left per §4a-4d.

**The two land on `other`, and that is the finding.** `other` goes 22 → 24 and
`assertion` stays at 11, because `:392` is `decreased, {},` on this tree — the
last line of the assertion holding that no address's `write` decreases — and the
`> 300` assertion is at `:588`. **#885's own write-up predicted both of its pins
would carry and that prediction was right for the tree it was written on**, where
`:392` *was* the `assertGreater`. Finding 8 records this. It is the second time
this file has found stale pins and the first time it has found two that were
correct when written, which is the sharper case: **a merged tree cannot tell a
pin that was always wrong from one a concurrent merge made wrong**, and a checker
built on either would have to guess. The verdict column here records the cause as
well as the verdict for that reason, and the re-open condition is unchanged —
what would make a checker writable is a supersession marker, not a smarter
resolver.

**What is deliberately not re-measured here, and why.** The wider `.py:NNN` class
— 373 occurrences, 229 targets, 34 files — is not re-run, for the reason the
#850/#887 note above gives: it was measured with a scratch definition that is not
committed, so re-deriving it would publish a *different* measurement under the
same name. **#885's two new pins do not move it in any case**, because both name
a `test_*.py`, which is the class that wider census excludes.

**The `SELF_MODULES` exclusion did its job again, and over a figure that had
moved twice.** The census's committed-tree figure is `71` here and `69` on
`main`, and the `50` that collided with §2b is neither of those — it is the
figure the suite landed with, on the tree of #887's own merge.
`check_doc_figure_pins.py`
was re-run on the merged tree rather than carried over and reads
**18 figure(s), 18 measured held, 0 measured unheld** over
**190 literal(s) inside a check** — the same run `main` gives, and both figures
are in the exclusion's own shadow, which is the point of an exclusion rather than
of the number.

**What the merge did to this table's own citing column, which is a further
repointing and the one the census cannot see.** #900's commit landed between
this branch and `main` and moved two citing lines this file names, without moving
one pin — the same shape as the exclusion's price named in the `#891` note above,
paid again. `--verbose` re-run on the merged tree gives
[`../findings.md`](../findings.md):**8790** where this file said `8702` and
[`../../tools/README.md`](../../tools/README.md):**159** where it said `157`, and
gives `xdata-moved-ranks-fall.md` at `404`/`416` rather than the `383`/`395`
`main` had, so the
`:331`/`:343` this branch repointed those two to are superseded rather than
contradicted. All three are corrected in place, everywhere this file names them;
the
`#900` transcript correction from `142` to `143` is recorded in the blockquote at
the head of this file.

**Each side's repointing was right for the tree it measured, and this is the
second time this file has had to say so about a line number.** #885 read
`331`/`343` off a tree where those were correct; #900 read `383`/`395` off a tree
where those were; **#890's twenty-five lines into that write-up put them at
`404`/`416`, and that is what the merged tree reads** — the third repointing of
the same pair, and the reason the pair *did* move again where the `#900` merge
note below expected it not to is that #885's forty-one lines all land below
`:395` while #890's land above it. That is an accident of where the two
branches' insertions fell, not a
property of either. **The direction of the accident is the point, and it is the
one thing here that flipped:** on the tree #885 measured, #900's concurrent
change was harmless to this pair, and nothing in the tree would have said so if
it had not been; on the tree this merge lands in, #890's concurrent change moved
the pair a third time, and the sentence two paragraphs up that predicted it would
not is corrected above. **Nothing mechanical in either tree distinguishes the two
cases** — the same class of blindness finding 8 is about, with the direction
reversed.

## The `#888` × `#885` merge, 2026-09-26

**Two merges landed together, four pins came with them, and every headline figure
is the sum of the two sections above rather than a third cause.** The run on the
merged tree is **73 pins, 26 files, 46 spellings, 42 targets, 57 resolves, 16
declined, 5/11/9/6/26 over 146 markdown files read**, against 71/25/45/41/55/16/
5/11/9/6/24 over 145 on either side alone. **The four additions are disjoint** —
#888's two `test_xdata_cluster_names.py:563` in
[`xdata-moved-ranks-key-collision.md`](xdata-moved-ranks-key-collision.md) and
#885's two `ec/tools/test_xdata_cluster_names.py:392` in
[`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md) and
[`../findings.md`](../findings.md) §69, two new files between them — so no
spelling and no target is the other's and each count moves by the sum rather
than by an overlap neither merge could see coming.

**The two sets of new rows are defective for opposite reasons, and the table
counts them apart for that reason.** #888's two were correct on the tree they
were written on and #890's repoint made them wrong here (finding 7); #885's two
were correct on *their* tree and a branch that had already moved the line landed
beside them without either tree being wrong (finding 8). **The heading of that
section moves from eleven to thirteen, and the lead paragraph with it**, because
neither merge had alone had all four of the rows the other added. **Nothing in
findings 1–6 changed verdict**, and the two new items are on different lines in
different files, so there is no re-reading to do.

**The carry count is 32 for the second time running, and that is the part worth
sitting with.** `main` had 32 carrying rows and eleven that did not. The two
merges between then and now added four rows and none of them carries, so the
class is four pins larger and the defective share of the resolving pins larger
still — 13 of 57 against 11 of 55. **A merge that adds two citations and moves
the defect count by two is what both of these did**, and it is the argument the
`#888` section made for the opposite case, arriving anyway.

**What the merge did to this table's own citing column, which is a further
repointing and the one the census cannot see.** `--verbose` re-run on the merged
tree gives **`:9028`** for the `> 300` pin in [`../findings.md`](../findings.md)
§69 and **`:622`** for the one in
[`xdata-moved-ranks-427-pair.md`](xdata-moved-ranks-427-pair.md), against the
`8793` and `446` each side's own table carried, and both are re-registered
above. The `xdata-moved-ranks-fall.md` pair is **not** moved
a fourth time: `415`/`427` is what the merged tree reads, the same value the
#888 × #890 merge re-registered, because #885's forty-one lines into that write-up
all land below them — the same accident of where the branches' insertions fell
the `#885` section above describes, and it held this time.

**What is deliberately not re-measured here, and why.** The wider `.py:NNN` class
— 373 occurrences, 229 targets, 34 files — is not re-run, for the reason the
#850/#887 note gives: it was measured with a scratch definition that is not
committed. **Neither merge's new pins can move it in any case**, because all four
name a `test_*.py`, which is the class that wider census excludes. That is a
fact about what the two branches added, not a re-run, and the difference is the
reason it is written here as its own paragraph.

**The `SELF_MODULES` exclusion did its job a fourth time, over a figure that has
now moved three times.** The census's committed-tree figure is `73` here, `71` on
either side alone, `69` at the #850 merge and `50` when the suite landed, and
`check_doc_figure_pins.py` was re-run on the merged tree rather than carried
over: it reads **18 figure(s), 18 measured held, 0 measured unheld** over
**190 literal(s) inside a check**, the same run `main` gives. The suite's own pin
in `ec/tools/test_census_test_line_pins.py` carries a comment saying which
addition moved each figure, and the shape split is the fourth one it has had to
follow.

**The verdict is unchanged and so is the re-open condition.** Thirteen pins do
not carry and ten record another line, the defect is still entirely in the
line-*content* half, and the supersession records are still unmarked prose in
eight of ten shapes. Nothing here moves the argument, and nothing here is a
reason to soften it.


Submitting anything upstream is unaffected: this issue touches no driver and no
firmware, and the mission's eventual
`Wer-Wolf/uniwill-laptop`/`tuxedo-drivers` contribution stays a prepared patch
in this repository for a human to submit, per issue #10. Nothing is opened in
another repository.
