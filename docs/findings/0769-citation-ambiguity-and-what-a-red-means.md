# A citation whose text several lines carry, and what a red from the tool that checks them means

**Nothing here is a hardware claim.** No EC was opened, no register was read,
no capture was taken and no §3 block was run. Every figure below is the output
of `python3 ec/tools/measure_mark_provenance.py` over the committed tree, and
the one case that had to be *built* to be seen is built in a temp file the tool
writes under `/tmp`.

Issue #769 asked for three things. Two are already done and recorded elsewhere;
what is left is the question its second bullet asks — **what should the tool do
with a red it is meant to report rather than gate on** — and a defect the issue
does not name, which is where the work went.

## What the issue's numbers were, and are not

The issue's `18` and `37` were real and were correct **on #749's fork point**.
They are not this tree's numbers and were not this change's: `0762-provenance-citation-reanchor.md`
is the record of the re-anchor that retired them, and
`docs/findings/0751-notice-two-moments.md` carries the correction. Every file
the issue names as a drifted pin is no longer a pin in the table. A reader who
finds `18`/`37` in `docs/findings.md` §16a and runs the tool expecting them will
get a clean run, and that discrepancy is recorded rather than papered over.

**What is not done, deliberately.** The re-anchor table on
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) is a record
of moves that have already happened. Re-typing its rows to match today's
numbers is the hand-kept churn `check_citation_lines.py`'s Rule 3 exists to
stop, and `check_page` deliberately holds that page at *file* granularity
rather than at a `:NNN` — see the correction at the foot of this file for the
one sentence in that page that says otherwise.

## The three-way reading of a citation, and why the third was invisible

`resolve()` finds a citation's line **by its quoted text**. That has been the
whole check since 2026-10-03, and it is right: a number held to the tree goes
stale on every merge that grows the cited file above it, and keeping it current
became the blocking finding of the pull requests that touched these graders.
But the function returned *one number*, and three different situations produce
one number:

| reading | what the file holds | what the number did |
|---|---|---|
| **at the line quoted** | the recorded line carries the text | nothing; the text confirmed it |
| **moved, unambiguous** | one line carries it | the text found its own line; the number is a stale hint |
| **ambiguous — the number cannot say which** | several lines carry it | the nearest one was chosen, and the choice is not reported |
| **gone** | no line carries it | the claim is failing, and `check_citations` fails the run |

The third was the defect. Its fallback is *the only disambiguator a pin has*,
and for a pin whose claim is about a position — "this reader calls that rule",
"that function holds this branch" — it is not sufficient. Nothing was wrong
with the tool's arithmetic; what was wrong was that it answered a question the
caller had to be asked and was not.

`grade_0751_isolation.py` spells `if skippable_row(row):` at every reader that
takes that rule — `ambiguous_citations()` prints the spellings, one run per
tree. The pins that quoted it each carried a claim about a different reader, and
each was resolved by whichever spelling sat nearest a number that was only a
hint. **Two of them landed in a reader their claim is not about, and the tool
printed `ok` on both** — the first naming its reader outright, the second by
description rather than by name, which is why only the first is machine-checkable
below:

| the pin claimed | it resolved into |
|---|---|
| `mark_labels_of takes that one skip rule, so existing_mark_labels -- which delegates its extraction to it -- cannot spell a second copy` | `read_capture` |
| `and so does the partition, over the notice's own read` | `mark_labels_of` |

The pin claiming `read_capture` was **right by accident of ordering** —
nothing about its claim placed it, and the next merge that grew the file above
it could have moved it. That is the shape the whole finding has: a green run
that was not evidence.

The suite's committed-tree case reproduces **the first of those two rows**,
plus the length-test pin that claimed `read_capture` and had to be re-worded.
The second row is outside the case, for the reason *What would still need
checking* gives: its claim names no function where the sentence starts, so the
rule has no subject to hold and skips the pin before comparing anything. The
case failing on the tree this file was written against is therefore not evidence
about that row — the tool's `ok?` is, and it is printed on every run.

**Why this is load-bearing rather than cosmetic.** The page's argument for why
the row's shape is safe to widen is *one skip rule, the readers call it, none
can spell a second copy*. The evidence for that argument was pointing at the
wrong lines, and the tool said the run was clean.

## What was done, and what a red from this tool means

`resolve_how()` now answers how, not only which: `exact`, `moved`,
`ambiguous` or `gone`, with every candidate line for the third. `resolve()` is
built on it and keeps its signature and its return, so the existing suite and
every other caller are untouched. Section 5 prints `ok`, `ok*` or `ok?` per
row and lists the candidates behind every `ok?`, and **the run still exits 0**.

**That is the deliberate answer to the issue's second bullet.** The
distinction being drawn is:

- a **failure** (exit 1) means the quoted text is gone from the file, or the
  row-site join does not close. The claim cannot be checked, and a page's prose
  rests on it.
- a **report** (`ok?`, exit 0) means the quoted text *is* present and the
  recorded number cannot say which carrying line is meant. Nothing is proven
  wrong.

Failing the second would also be self-defeating, and for a reason worth stating
plainly: a stale number is the state **almost every pin is in** after any merge
that grows a cited file above it. An exit-1 there would redden every such merge
— the churn Rule 3 was rewritten to stop, arriving by the citation table rather
than by the CSV rows. And collapsing the two would be the overclaim this
repository keeps refusing: *not found by this method* is not *the claim is
false*, and `gone` is a different statement from `ambiguous` in the other
direction — a citation whose text was found is not a broken one.

The claim is held where it *can* fail instead. Each pin now quotes the line in
its own function that names the rule **in words**, so the quoted text sits
inside the reader it is about and no number has to be right for it to:

| claim | now quoted from |
|---|---|
| `read_capture` takes that one rule | `read_capture`'s docstring, naming `skippable_row` |
| `mark_labels_of` takes that one rule | `mark_labels_of`'s docstring, naming the same |
| so does the partition | `partition_capture_rows`'s docstring, naming the same |

**What that trades, stated rather than left for a reader to find.** The call
site was the evidence and a docstring is a statement *about* it, so deleting the
call while leaving the prose would leave these green. Which test holds each
one is a measurement rather than an assumption, and taking it is what turned up
the gap this change had to close: deleting each of the three call sites in turn
and re-running the suite shows that `read_capture`'s and the partition's fail
cases (`test_the_refusal_reasons_are_read_captures_own` among them) while
**`mark_labels_of`'s failed nothing at all** — no case in
`test_grade_0751_isolation.py`, no failure of `--self-test`, and no red from
this tool's own run. The reason is in the fixture rather than in the reader:
the preflight's cases share a capture whose `#` line and header are both
dropped by a *second* rule on the way to the one under test, so deleting
`skippable_row` from `mark_labels_of` left every assertion true for the other
reason.

So the claim is now held where it can fail, by
[`test_grade_0751_skip_rule.py`](../../ec/tools/test_grade_0751_skip_rule.py)
— one case per reader, each at its own call site. Its fixture is a capture
carrying **a mark row the operator commented out by prefixing `#`**, which is
what `skippable_row`'s own docstring says the `#` test is for and the only
skippable row that is also a mark row: nothing but the skip rule stands between
it and a label the notice would print, so the case is true only while the rule
is. A `#` *annotation* line cannot do this job — it carries no `MARK` in its
second field, so `mark_labels_of`'s branch below the rule drops it either way,
which is exactly the redundancy that hid the gap. One case asserts that
separation directly, so a future change to the row shape that made the fixture
stop discriminating fails there rather than quietly leaving the other cases
true for a second reason.

Without the rule the three readers do not merely disagree, they each fail
differently: `read_capture` *refuses* the capture on a timestamp opening `#`,
the partition names the commented row a refused row, and the preflight lists it
as a label. Each case is written against its own reader's version of that.

A fourth pin needed only re-wording rather than re-anchoring: it claimed
`read_capture`'s length test and the line is in `take_capture_row`, which has
been that reader's own body since #749 split it out. The claim was true of the
rule and misnamed about the function.

## What is still ambiguous, and why that is the honest answer

`ambiguous_citations()` is the report, it is not empty on this tree, and this
section is the whole of what it prints. The remaining cases are **not**
defects, and pretending otherwise would be the opposite overclaim. Each one is
a text that more than one line of its file carries, so the nearest-line
fallback chose on distance and `ok?` says so; none of them is a claim shown to
be about the wrong function.

- **The tied spellings in `grade_0751_isolation.py`.** Every reader of a row
  spells the same test, so a pin quoting one spelling cannot name its reader by
  quoted text alone. Four spellings account for every reported row in this file:

  | the quoted text | it is spelled in | the pin is recorded at | it lands in |
  |---|---|---|---|
  | `if addr == "MARK":` | `take_capture_row` and `partition_capture_rows` | `:1485` | `take_capture_row` |
  | `if addr == "MARK":` | `take_capture_row` and `partition_capture_rows` | `:1678` | `partition_capture_rows` |
  | `if len(row) > 1 and row[1] == "MARK":` | `mark_labels_of` and `existing_mark_provenance` | `:1528` | `mark_labels_of` |
  | `if len(row) < 4:` | `take_capture_row` and `partition_capture_rows` | `:1413` | `take_capture_row` |
  | `ts, addr, old, new = row[0], row[1], row[2], row[3]` | `take_capture_row` and `partition_capture_rows` | `:1415` | `take_capture_row` |

  Where each lands is where its own claim points. The first three name one
  reader each, as their subject, and land in it; the `:1413` pin says the test
  `lives in take_capture_row` further along its claim and lands there too; the
  `:1415` pin names no function at all — its claim is that the row is read by
  explicit indexing rather than an unpack, which is a statement about the row
  and not about a reader. `:1413` is the pin this change re-worded rather than
  re-anchored; `:1415` is unchanged by it.

  That is also where the suite's rule below stops: it reads a claim's *subject*,
  so it checks the first three rows and skips the last two, because a reader
  named mid-sentence or not at all is not a subject. The blind side is stated
  under *What would still need checking* rather than left here to be inferred.

  The table's own comments already document the midpoint rule that keeps a tied
  pair on opposite sides, and that is a *choice of position that has to be
  maintained*, which is exactly what the `ok?` now makes visible on every run
  rather than leaving to a comment nobody reads.

- **The runbook's §3-block pins.** `--mark --label-vocab 0751 --csv` is carried
  by every §3 block of `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`,
  at `:163`, `:165` and `:167`. The two pins recorded at `:159` and `:161` name
  none of those three, so both report `ok?` and both land at `:163`. The third
  pin, recorded at `:163`, is **`exact` rather than ambiguous**: its own number
  is itself one of the carrying lines, so the text and the number agree and
  nothing had to be chosen. The two reported ones claim *holding the flag*, not
  which block the line is in, so no claim is falsified — only the number stops
  being a way to find the block. Editing a hardware procedure to make a
  citation prettier is not a change this repository should make, and leaving
  them reported is the honest outcome.

The suite's committed-tree case asserts that **no citation whose claim names a
function resolves into a different one** — the claim, not a count of pins. It
fails on the tree before this change and passes after. It is what stops the
`ok?` from being decorative later.

## What would still need checking

- The rule the suite uses reads a claim's **subject** — a function named where
  the sentence starts. A claim phrased so the function appears later in the
  sentence is not checked, deliberately: holding a `what` that merely *mentions*
  a function to the enclosing one would be a checker over prose rather than over
  the table. That is a blind side of the case, stated here rather than counted,
  and it is the blind side the second row of the wrong-rows table above falls
  into — a real mis-resolution that no assertion here reproduces.
- Citations into **nested** functions are not covered by the same case, for the
  same reason.
- Whether a docstring-quoted pin should ever be considered sufficient evidence
  is a question this change answers only for these three, and answers by holding
  a behavioural test behind each rather than by a rule. A pin whose function has
  no behavioural test behind it would need the call site back, and nothing here
  decides that — this file does not decide it in general, and did not decide it
  for `mark_labels_of` until a case existed that failed when its rule went.
  Whether the tool can *tell* the two situations apart is a separate question
  it does not answer at all: nothing in the run reports whether the function a
  docstring-quoted pin names has a test behind it, so the next re-anchor of
  this shape is on the same footing as this one, and the check that found the
  gap here was deleting the call site by hand rather than anything the tool
  does.
- **The 18/37 question is not re-opened.** Whether `findings.md` §16a and the
  issue agree is recorded in `docs/findings/0751-notice-two-moments.md`; this
  file does not restate either figure.