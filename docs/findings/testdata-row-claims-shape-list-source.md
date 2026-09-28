# The testdata row-claims shape list has one source, and the summary line reads it rather than restating it (issue #998)

`check_testdata_row_claims.py` decides, for every backticked `0xNNNN` in the
third column of `ec/tools/testdata/README.md`, whether it is a claim or a
refusal, and a refusal is one of a closed list of reasons. That list was
written down in seven places and nowhere in particular: the docstring's seven
bullets, two `reason_for()` branches that narrate their own position in it
("the seventh entry of the docstring's shape list"), a comment on
`DATED_CAPTURE` saying the same, two docstrings on either side of the
function, `main()`'s printed summary line with a `# Five, not seven:` comment
explaining why its own number is not the length of the list, a test asserting
a hand-typed sorted list of the five reasons that have a committed-tree
instance, and — in three files outside the tool — the same figures in
prose. Adding an eighth refusal was a six-file edit, and every one of them
was a place a reader could not check.

This change moves the list into a module constant and derives what restated
it. Nothing about what the tool *does* moves: the reasons, their order in
`reason_for()`, the verdicts, and the run's stdout are what they were, and
the diff of the run before and after is empty.

**Nothing here reads hardware.** The tool reads the committed index, the
committed fixtures under `ec/tools/testdata/`, the committed capture
filenames under `evidence/ec-watch/` and two committed annotation CSVs. No
EC, BIOS, Windows or laptop is involved, no image is loaded, and no live
observation is claimed or needed to close this.

## What was hand-kept, and where

| where | what it said |
|---|---|
| `check_testdata_row_claims.py` docstring | "the five shapes and the two dated refusals below"; "it is the seventh entry of the list below"; "an eighth entry appearing in the tree is a change to this docstring" |
| the same docstring, second half | "which is the sixth entry of the shape list above"; "**The seventh entry is a later decision**"; the last bullet's "as the sixth entry's are" |
| `DATED_CAPTURE`'s comment | "it is the seventh entry of the docstring's shape list" |
| `reason_for()` | "The seven in a fixed order… Six of them are a property of how the sentence is written … the seventh is the one that reads the file set" |
| `with_column()` | "whose docstring says an eighth entry appearing in the tree is a change to that docstring" |
| `closing_line()` | "A claim the five shapes passed over" |
| `main()` | the printed label, and a `# Five, not seven:` comment saying why the number is not the list's length |
| `test_the_committed_tree_exercises_every_shape` | a literal sorted list of the five instantiated reasons, and "**The count stays at five**" |
| `SkipsDeliberately`, `EachRuleIsLoadBearing` | "The five shapes, the two dated refusals"; "Three of the five shapes"; "The sixth and seventh entries of the shape list" |
| `test_a_two_date_sentence_is_refused_with_its_literals_in_neither_day` | "the same thing the other six shapes say when they pass a literal over" |
| `docs/ci/agent-gates-testdata-row-claims.patch` | "The five shapes and the two dated refusals" |
| `ec/tools/testdata/README.md` | "Five shapes are counted … along with both dated refusals" |
| `tools/README.md` | "with each of the five shapes and the dated-capture variant pinned as a case" |

The issue called it six files. It is five paths — the patch, the testdata
index, `tools/README.md`, the tool and its suite — with the tool's two
hand-kept *figures* in it, which is probably where the sixth came from. The
issue's line numbers are off against this tree for the same reason: the
figures are what moves when anything moves.

## What is derived now

**`SHAPES`** is a module-level ordered tuple of the seven reason strings, in
`reason_for()`'s own return order, and it is the one place the list is
written down. `reason_for()` still returns string literals rather than
reading an index into the tuple: a branch saying `return SHAPES[3]` is less
readable than the reason it returns, and the copy is a *checked* copy rather
than a second source — what checks it is the two-direction set difference in
the suite, described below.

**`DATED_REFUSALS`** is the pair of entries that read the file set rather than
the sentence, and the two the summary line counts apart from the rest, which
is the whole of what `# Five, not seven:` used to explain. It is the constant
the committed-tree case compares against, so "the two refusals that have no
instance" is a name with a value rather than a figure in a test body.

**`SHAPE_LABEL`** is the summary line's label, composed from
`len(SHAPES) - len(DATED_REFUSALS)` and `len(DATED_REFUSALS)` through
`count_word()`. The words cover zero through eight and a count outside that
range renders as a numeral, so a ninth shape reads "the 9 shapes" rather than
raising out of a line whose only job is to report: a reporting line must not
fail a run over a bookkeeping change.

The prose changed to a pointer, never to a smaller number. "The seventh entry
of the list below" is now the `two dated captures in one sentence` entry;
"the sixth entry of the shape list above" is the `dated capture not found`
entry; "as the sixth entry's are" is that same entry, and the sentence about
neither dated refusal having a committed instance now points at the case that
holds it. **Each bullet of the docstring's list opens with the string its
entry is**, so the prose and the constant are joinable by eye.

## The census behind the two-constant split

`python3 ec/tools/check_testdata_row_claims.py --check` on the committed tree:

```
shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
```

Five distinct reasons are instantiated, and the two dated refusals —
`dated capture not found` and `two dated captures in one sentence` — are not,
because the one dated sentence in the committed index names a single date and
that date resolves. That is a fact about this tree, not about the tool, so
`DATED_REFUSALS`'s value is a claim the census supports and the case below is
what keeps it honest. **If the census is ever re-run, the answer for a reason
with no instance is "not found by this method", never "absent"** — the same
wording the tool's own refusals use, and the one its stdout keeps verbatim.

## The run, before and after

Both runs of `python3 ec/tools/check_testdata_row_claims.py --check` on this
branch, `diff`ed:

```
30 claim(s) checked, 15 claiming row(s), 24 passed over under the five shapes and the two dated refusals, each of them: not checked, not absent
shapes: capture/window bound 16, denial 3, dump-command argument 2, watched-set span 2, firmware code address 1
```

Byte-identical, both lines included, and so is the rest of the run. That is
the evidence the wording survived being derived: the label is now computed
from two lengths, and it prints the same words it printed when it was typed.
The historical write-ups that quote this output
(`testdata-third-column-claims.md`, `testdata-row-claims-dated-capture.md`,
`testdata-row-claims-report-naming.md`,
`testdata-row-claims-multi-date-sentence.md`) stay true because it did, and
they are not edited here.

## The cases, and a demonstration that they have been seen red

`test_the_committed_tree_exercises_every_shape` no longer holds a literal
list. It compares the committed run's reasons against `SHAPES` in **both**
directions through one helper, `check_every_shape()`, and each direction's
message names the reasons in it rather than saying how many there are. The
expected value is `DATED_REFUSALS`.

Both directions are the assertion. The first catches a rule that has stopped
firing on the committed tree; the second catches a reason added to
`reason_for()` without being added to the constant. Each is driven from a
synthetic input as well, because the committed tree can only ever reach two
of the seven:

- `test_the_difference_names_a_reason_the_run_never_exercised` — a run
  exercising two shapes and both refusals, so three reasons in the list have
  no instance. A reason with an instance *somewhere* in the list is named.
- `test_the_difference_names_a_reason_shapes_does_not_list` — the committed
  run's own reasons plus one that is not in the list, so only the second
  direction fails and it is that one doing the failing.

Each was run against a perturbed tool, and each went red naming the reason
rather than with a changed count:

```
rule stopped firing:        these reasons are in SHAPES and nothing in the run
                           exercises them: ['dated capture not found', 'denial',
                           'two dated captures in one sentence']
a reason dropped from
SHAPES:                    the run produced these reasons and SHAPES does not
                           name them: ['denial']
an unlisted reason
produced by the run:       the run produced these reasons and SHAPES does not
                           name them: ['a reason nobody wrote down']
```

`TheShapeListHasOneSource` holds what the three constants owe each other
before any of that: no repeated entry and the refusals a subset, because
`shape_label()` subtracts one length from the other and a duplicate would
make the printed count wrong while the set difference still held; and the
numeral fallback, driven through `shape_label()` with a longer list rather
than by editing `SHAPES`, so the case says what a future entry would print
without this tree being changed to find out.

`test_the_run_reached_something` reads its label out of `ctrc.SHAPE_LABEL`
rather than re-spelling it, and that is joinability rather than a wording
guard: the case parses the summary line and splits each entry on `[:,]`, so
re-spelling the label in the test would be a fourth copy of the same string
free to drift from the run's. It follows the derivation, and so cannot fail
when the derivation changes — **the wording is pinned by
`test_the_label_falls_back_to_a_numeral_rather_than_raising`**, which
hard-codes `"the six shapes and the two dated refusals"`. What this case does
pin is the parse: a label carrying a comma or a colon splits into pieces the
`number, _, label` reading does not recover, and the entry goes missing from
`counts` and fails the case with "the run reached no passed-over literals".

## What this deliberately does not change

- **`reason_for()`'s branches and the docstring's bullet order still disagree
  with each other**, and they did before. The constant is ordered by
  `reason_for()` and the bullets are left exactly as they are. That is issue
  #987's ground — it owns the order, and this change does not take it. The
  two now read as a disagreement between a constant and a document rather than
  as three separate hand-kept positions, which is the part this change can
  honestly claim; whether one ordered constant settles #987 as well is a
  question for whoever lands second, re-deriving from whichever landed first.
- **#986** (`EachRuleIsLoadBearing` never opening `Result.missing`) is
  adjacent and untouched; the derived comparison is not folded into it.
- **The single-date path is byte-identical.** `captures_for()`,
  `carried_by()` and `carried_by_column()` are not edited at all, so the
  suites that load this tool — including `test_check_capture_names.py`, which
  pins `captures_for()`'s three-tuple return, and
  `test_measure_index_repair_visibility.py`, which runs the tool over both
  pre-repair trees — keep working because nothing structural moved.
- **No row of `ec/tools/testdata/README.md` is edited.** The paragraph below
  the table changes its counting words and nothing else, and the index stays
  valid to `check_testdata_index.py` because that check reads the first and
  third columns rather than this paragraph.
- **`ec/tools/xdata_register_map.py`'s "one of the five shapes"** is a
  different list — that tool's own hand-check catalogue over XDATA addresses
  — and is untouched. Named here so a sweep does not take it for this one.
- **The gate wiring stays unlanded.** `docs/ci/agent-gates-testdata-row-claims.patch`
  is prepared for a human to `git apply`, for the reason every file in
  `docs/ci/` is, and this change edits only the prose above its `diff --git`
  line; the hunks and their context are untouched.
- **No `status:` moves**, so `ec/annotations/registers.yaml` is not touched.

## The question this answers

`testdata-row-claims-multi-date-sentence.md` closed by asking whether the
instantiated subset should be *derived* rather than narrated, and said it
raised the question rather than answering it. It is derived now: the two
entries with no committed instance are `DATED_REFUSALS`, a name rather than a
comment, and the case that holds them is a set difference whose failure
message names a reason. That file keeps the question as it was asked, per the
rule that a retraction or a resolution goes in place rather than being edited
into the thing it corrects.
