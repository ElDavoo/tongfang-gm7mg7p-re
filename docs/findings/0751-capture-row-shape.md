# One row stream for the 0751 capture readers, and a byte-order mark retired at the shape (issue #750)

The write-up for [issue
#750](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/750), which asks
for the shape of a capture row to exist once rather than three times, and for a
leading UTF-8 byte-order mark to stop being reported as a header row with an
unreadable timestamp.

**Offline throughout.** No EC, no laptop, no Windows box was reached. Every
figure below is this tree's own Python 3.12.14 on ubuntu reading hand-written
rows and bytes this repository wrote. That a Windows tool writes a BOM is a
**prediction**, not a case measured here, and the write-up says so wherever it
touches one.

## The three copies, as measured

At `c9e72c1`, the rule `not row or row[0].startswith("#") or row[0] == "ts"`
was written out three times, verbatim:

| line | function | what it re-stated |
|---|---|---|
| `:687` | `read_capture` | the skip rule; `len(row) < 4` at `:689`; the mark branch at `:692` |
| `:732` | `existing_mark_labels` | the skip rule; its own variant `len(row) > 1 and row[1] == "MARK"` at `:734` |
| `:776` | `refused_capture_rows` | the skip rule; `len(row) < 4` at `:778`; the mark branch at `:789` |

and a fourth reader, `read_early_exits` at `:922`, read the same file. #718's
Files section had argued that a second *module* would put a second copy of the
shape in the tree, and added a second *loop* in the same module instead. That
argument was right about the module and wrong about the count.

`read_early_exits` is not a fourth copy and cannot become one.
`EARLY_EXIT_TAG` is `"# the run ended early:"` (`:427`), so it **keeps**
exactly the rows the other three skip, and
`test_a_hand_annotated_capture_grades_exactly_as_it_did` already pins that. An
iterator that filtered `#` rows would drop every early-exit row in the tree and
grade every crashed run as one that finished.

## The guard held the reasons, not the shape

`test_the_refusal_reasons_are_read_captures_own`
(`test_grade_0751_isolation.py:3608` at `c9e72c1`) pins four refusal reasons,
their order, and the first reason byte for byte against the exception
`read_capture` raised. It holds what it claims. What it does not hold is the
shape:

- all seven of its fixtures open `'ts,addr,old,new'`, so the header case is
  pinned only as a side effect — without the skip, `int('addr', 16)` would
  raise on the header and every fixture would fail for the wrong reason;
- the only fixture that put a `#` row and a blank through the partition,
  `test_the_preflight_does_not_raise_on_any_of_them`'s `'only a comment':
  ['# a note', '']`, asserted `assertIsInstance(..., tuple)` — that nothing
  escapes, not what came back.

So a change to the skip rule on the partition path was invisible, and the
failure it makes is the one #718 set out to remove: the notice naming a row
the grading treats differently, in either direction.

Four cases now close it, in `ExistingMarkLabelTests`:

- `test_the_shape_agrees_across_all_four_readers` — one fixture carrying a `#`
  row, a blank, the header, a change row, two marks and an early-exit row, read
  by all four readers, asserted as lists. `read_capture`'s marks equal
  `existing_mark_labels`' pairs in order, `refused_capture_rows`' accepted
  equals `existing_mark_labels` on a file the strict reader accepts, and
  `read_early_exits` returns exactly the phrase rows.
- `test_on_a_file_the_strict_reader_refuses_the_partition_names_every_row` —
  the same fixture plus a bad row, with the accepted and refused rows written
  out literally. `read_capture` raises and returns nothing there, so the
  reader-side half of "the partition equals `read_capture`'s own view" is the
  existing first-reason equality, and the row is cross-checked against the row
  in the exception it raised.
- `test_a_byte_order_mark_does_not_turn_the_header_into_a_bad_row` — below.
- `test_a_change_row_bad_in_two_hex_fields_names_the_earlier_one` — closes a
  gap the anti-drift test's own comment records: the order *among* the three
  `int()` calls "is not pinned at all", because every fixture reaching them has
  exactly one bad field. A partition naming the `new` of a row whose `old` is
  also not hex would have passed that test.

## The BOM, measured before and after

With `EF BB BF` at offset 0, this tree's own reader and partition, at `c9e72c1`:

```
read_capture  -> ValueError: Invalid isoformat string: '\ufeffts'
partition     -> names ['\ufeffts', 'addr', 'old', 'new'],
                 reason "read_capture cannot read this timestamp: Invalid isoformat string: '\ufeffts'"
control, no BOM -> read_capture OK, 1 mark(s), 0 change(s)
```

and after this change, the same fixture:

```
read_capture  -> 1 mark(s), 0 change(s)
findings      -> accepted [('2026-01-01T12:00:00.000+01:00', 'settled')], refused [], unplaceable []
control, no BOM -> identical
```

**The `read_capture` line of that measurement is superseded by #748, and the
replacement is recorded here rather than the measurement being quietly
dropped.** The version written alongside the shape asserted that the strict
reader *grades* a BOM'd capture, which is what the strip bought: no reader saw
a bad timestamp and no row was named at all. #748 then declared the format
`utf-8` with **no BOM** — see
[`0751-capture-encoding.md`](0751-capture-encoding.md) — and under that
decision a byte-order mark is a *refusal of the file*, so the same fixture now
reads:

```
read_capture  -> ValueError: starts with a byte-order mark, so its first field is '﻿ts' ...
findings      -> accepted [('2026-01-01T12:00:00.000+01:00', 'settled')],
                 refused [(None, <that message>)], unplaceable []
control, no BOM -> identical
```

Which is the outcome this page was arguing for, reached the other way round. The
notice still does not name the header: `refused[0][0]` is `None`, so there is no
row to offer for deletion, and the reason names the mark and the remedy. What
the strip buys now is the half the refusal cannot: the three preflights still
read the file — `existing_mark_findings` calls them on a file the strict reader
refused — and for them the header is the header rather than a data row with an
unreadable timestamp. Both halves are the same invariant, reached by a file-level
check for the reader that may refuse and a row-level one for the readers that
may not.

So the notice would have printed the **header row** as a row with an
unreadable **timestamp**, and then, because a row is named, the remedy
`fix or delete the row(s) above before the run`. Deleting the header does make
the file grade — the advice works — but the operator is told a hand-edited
timestamp is at fault when one invisible byte at offset 0 is, and the row
offered for deletion is the one carrying the column names. The anti-drift
guard is *not* broken in that story: it did its job and the first reason still
matched `read_capture` byte for byte. The diagnosis was invented, because
nothing in the tree owned the shape of a row.

### The scan, and what it does not say

129 committed `.csv` files were scanned for a leading `EF BB BF`; **none**
carries one. That is a statement about a scan of committed files at this
commit, not "BOMs do not happen" — and it does not make the fixture
contrived either, because the file a watcher is about to append to is the
operator's own, not one of ours.

Whether a Windows tool writes one is a prediction. The issue's supporting
observation is that `windows/tools/ec_callsites.py:78` already opens
`encoding="utf-8-sig"` for exactly this reason and that `read_capture`'s
docstring invites the operator to hand-annotate a capture, which is what Excel
and Notepad do. Neither has been observed on this machine, and no capture
carrying a BOM was produced by one.

## Strip, not `encoding="utf-8-sig"`

The two options the issue offers are not equal here, and the difference is
whose decision each one takes.

`encoding="utf-8-sig"` decides what encoding the file is *read as*, and it
decides to *accept* a byte-order mark. The first of those was, when this page
was written, the open encoding decision the tree recorded as deliberately
undecided: `existing_mark_findings`' docstring, `ec_watch-marks.md`'s encoding
section, and the addendum's *The encoding question, measured rather than
assumed* in
[`0751-append-unchecked-marks.md`](0751-append-unchecked-marks.md), which
concludes "the grader is not encoding-portable" and leaves the choice open.

**That paragraph's premise is settled and the conclusion is unchanged.**
[#748](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/748) declared the
format `utf-8` at every reader and writer, so the open encoding is no longer
this tool's to leave open, and the specific worry recorded here — that pinning
would "turn one of those two columns into a failure and take the decision away
from the issue that owns it" — is what happened, deliberately, by an issue that
did own it. `test_a_byte_this_python_cannot_decode_reports_the_verdict_it_observed`
no longer accepts either column; it asserts the one there is.

`utf-8-sig` is still not used, and the reason is now a fact about the format
rather than about who decides: the format is `utf-8` **with no BOM**, and a
codec that silently accepts a mark the format does not have is a format change
made at a reader. Whether the format should ever accept one is a separate
question, and it is open — see the encoding page and `ec_watch-marks.md`, which
both say so in as many words.

The strip fixes the defect at the layer the defect is in: the header test. It
works under whatever encoding the interpreter picked, is orthogonal to that
decision, and became redundant-but-harmless for the strict reader the moment the
codec was pinned — which is what it was written to be. It lives in
`normalised_rows`, which `capture_rows` — the one place the four capture
readers open a file — goes through and so does `capture_snapshot`, the
notice's single read since #749. Within that scope no reader can be strict
about a mark in one and lenient about it in another, and
`existing_mark_labels` must not raise on a BOM'd file either, and does not.
Two readers outside the scope are named rather than left to a claim the tree
contradicts: `check_capture_encoding.py`'s `count` and
`grade_timer_sweep.py`'s `load` each spell the `ts`/`#` test out with no
strip, so a BOM'd header is a data row to both, and changing either is an edit
to its own skip rule. The grader's `path_starts_with_bom` opens the same file
again, in binary, for three bytes — to ask the file-level question a row
cannot — which `docs/findings.md` records as a seventh open, so
"`capture_rows` is where a capture is opened" is a claim about the four
readers rather than about the tree.

**Applied uniformly to every row's first field**, not only the first row. The
first three bytes of a file are the only place a BOM occurs in practice, so the
uniform rule and a file-level rule agree on every file that exists, and a
uniform rule is the one that can be written down once. One side effect worth
recording: a first-line `# the run ended early:` row was *missed* by
`read_early_exits` — a U+FEFF on the header made its phrase test false —
and after the change it is found.

### What the strip does not do

Under a single-byte locale the same three bytes decode to `ï»¿` (U+00EF
U+00BB U+00BF), which a U+FEFF strip does not catch. Repairing that is a
mojibake decoder, it is only reachable once the open's encoding is decided,
and it is a prediction about a Windows box rather than a measured case. UTF-8
is the only reading this change retires, and it is the reading the issue
measured and the reading this tree's own gate runs under.

**The prediction is withdrawn, because the open's encoding is now decided and
the case is unreachable rather than pending.** Every reader of a capture opens
with the declared `utf-8`, so there is no locale left under which `EF BB BF`
would decode to anything but U+FEFF, and no mojibake decoder is owed to anyone.
A file that *does* hold cp1252 bytes is refused whole by the strict reader, with
the codec and the remedy named, and reaches the preflights as U+FFFD — which is
a refusal the tree states, not a decoding it attempts to repair. What replaces
the prediction is a smaller measurement: 0 of the 62 committed captures carry a
BOM and all 62 decode as UTF-8.

## The one seam, and what deliberately stays per-reader

The shape is stated once, in three functions:

- `normalised_rows(rows)` — takes a leading U+FEFF off the first field of every
  row. Split out of `capture_rows` so the notice's one read and the four
  readers that stream a capture cannot disagree about what a first field may
  look like.
- `capture_rows(path, errors=None)` — a generator that owns the `open()`, the
  `newline=""` and the caller's decode policy, and applies the rule above. A
  **stream, not a filtered iterator**, for the reason above:
  `read_early_exits` keeps exactly the rows the other three drop. The two
  decode policies have to keep differing and are passed straight through: the
  strict readers open bare and let an undecodable byte raise out of the loop at
  the row it stopped on; the two preflights pass `errors="replace"` on purpose.
- `skippable_row(row)` — the one definition of what makes a row carry no data,
  called by `read_capture`, by `mark_labels_of` (which `existing_mark_labels`
  delegates its whole extraction to) and by `partition_capture_rows` (which
  `refused_capture_rows` delegates to in turn).

What deliberately stays per-reader, and is not a shortfall: the four-field test
and the branch that decides a row is a mark are **not** one rule. They are
three different contracts — a `ValueError` in `read_capture`, a tolerated short
row in `existing_mark_labels`, a *named refusal* in `refused_capture_rows` —
and #548/#718 made them different on purpose. Merging them would delete the
preflight. So "the shape exists once" here means the row's *identity* — what
makes it skippable rather than data, and what its first field is allowed to
look like — and the per-reader strictness is held by the extended guard rather
than by a shared function.

Two consequences of that, recorded in the docstrings rather than left to be
rediscovered:

- a `# the run ended early:` row can never be a refused row, because
  `skippable_row` takes it before the partition sees it, and it is not a mark
  row either — it is in neither list. That is the shape working: the row is
  read, by `read_early_exits`, and a crash row is a record about the run
  rather than a row of the capture;
- a fifth writer's shape still costs what the
  [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md)
  measurement says, because that is a different question from this one.

## What the change did not do, and the lines it moved

**The encoding decision itself** was out of scope here and cross-referenced
rather than duplicated; #748 has since made it, and this page's own section on
`utf-8-sig` records what that cost the argument above. The `ï»¿` reading was
recorded as a limit and is now unreachable, which is a different thing from a
limit retired by argument — it is retired by the codec no longer being a
variable. The sibling graders' own copies — `grade_timer_sweep.load`
(`ec/tools/grade_timer_sweep.py:115`/`:138`) and `ec_timer_capture.py`'s `#`
writer — are a different family with a different label convention. They
remain second copies, named here rather than merged. `read_dump` is a fifth
reader in the same module and a different file kind (`ecrw.py dump` text,
not a capture CSV); folding it into a capture row stream would be a category
error.

The line numbers this page and
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) cite moved
twice: once for this change and once for #748's, and the citation table in
`ec/tools/measure_mark_provenance.py` is re-anchored to the merged tree rather
than to either branch. Re-anchoring is the whole of the change to that tool —
`check_citations` and the `scan` it joins against are byte-identical to
`origin/main` — so the drift counts in `docs/findings.md` are two measurements
of two trees rather than two readings of one, and the coupling section below
gives both.

No committed fixture was added under `ec/tools/testdata/`: the new cases write
temp files like every case in the class, and a committed fixture would also
require a `check_testdata_index.py` index update for no gain. No test was
skipped and no gate was weakened.

### The drift record

Inserting above `read_capture` moved every citation at and below it, #748's
edits moved most of them again, and #749's split of the readers' bodies moved
them once more. The `at c9e72c1` column is the state the issue measured; the
`now` column is the merged tree, after all three:

| symbol | at `c9e72c1` | now |
|---|---|---|
| `EARLY_EXIT_TAG` | `:427` | `:428` |
| the skip rule | `:687`, `:732` (`:776` unquoted) | `:845` — `skippable_row`'s return |
| `read_capture` | `:678` | `:852` |
| its byte-order-mark refusal | — (added) | `:886` — `path_starts_with_bom(path)` |
| its call to the predicate | `:687` | `:890` |
| its length test | `:689` | `:1042` — `take_capture_row`, not `read_capture` |
| its explicit indexing | `:691` | `:1044` — same body |
| its mark branch | `:692` | `:1045` — same body |
| `existing_mark_labels` | `:700` | `:896` |
| its call to the predicate | `:732` | `:1065` — in `mark_labels_of`, which it delegates to |
| its `(ts, label)` pair | `:735` | `:1068` — same helper |
| the partition's docstring quoting the mark branch | — (added) | `:976` |
| `refused_capture_rows`' mark branch | `:789` | `:1099` — in `partition_capture_rows`, over the notice's own read |
| `read_early_exits` | `:902` | `:1342` |
| its phrase test | `:923` | `:1384` |
| the per-capture census line | `:2510` | `:2972` |
| `warn_unchecked_marks` | `ec_watch.py:276` | `ec_watch.py:288` |
| the notice's call into the reader | `ec_watch.py:339` | `ec_watch.py:361` |
| `Marker._loop`'s writer | `ec_watch.py:446` | `ec_watch.py:473` |
| `grade_timer_sweep.load`'s mark branch and phrase test | `:134`, `:135` | `grade_timer_sweep.py:138`, `:139` |
| `ec_timer_capture.py`'s four writers and its `#` writer | `:164`, `:199`, `:205`, `:227`, `:144` | `ec_timer_capture.py:169`, `:204`, `:210`, `:232`, `:149` |
| `system_id_probe.py`'s writer | `:256` | `system_id_probe.py:261` |
| `manual_fan_ctrl_probe.py`'s writer and its early-exit row | `:438`, `:922` | `manual_fan_ctrl_probe.py:443`, `:927` |
| the encoding check's own mark/change census and its constructed row | — (added by #748) | `check_capture_encoding.py:166`, `:243` |
| §3's three commands in the runbook | `…:152`, `:156`, `:159` | `…:152`, `:156`, `:159` — the file's §3 did not move |

Six of those left-column values are worth naming, because the numbers the *pins*
carried at `c9e72c1` were not the numbers the code was on: `CITATIONS` held
`read_early_exits` at `:739`, its phrase test at `:760`, the per-capture census
line at `:2347`, and `ec_watch.py` at `:254`, `:280` and `:355`, while the code
those pins named sat at `:902`, `:923`, `:2510` and `ec_watch.py:276`, `:339`,
`:446`. Those six are the red rows the next paragraph is about, and the two
columns here are code positions on both sides, not pins on the left.

`docs/findings/0751-append-unchecked-marks.md`'s one-sided drift claim and
`docs/findings.md` §16a's `#719` paragraph keep the numbers they were written
with: they are dated records, and this repository's rule is that such a record
is corrected beside, never edited. This table is that correction, one
generation on — and the `now` column is itself dated, which is the point.

### The coupling the issue does not name

`ec/tools/measure_mark_provenance.py` holds a `CITATIONS` table of path, line,
verbatim text and what-it-is rows for exactly the lines this change edits, and
asserts each one still reads as quoted. It also runs a whole-tree scan for
lines carrying the literal `"MARK"` and joins it against the citations both
ways. Re-anchoring the rows is in the same PR because a committed tool
asserting a line that no longer exists is the failure this repository's
calibration rule is about.

Two things were found there that are worth stating plainly rather than
absorbing into the change:

1. **The check does report, and this branch is what turned it green.** The
   citation check is neither silent nor unreachable: on `origin/main` a bare
   `python3 ec/tools/measure_mark_provenance.py` prints its **38** rows — 20
   `ok` and 18 `DRIFT` — and **37 citation problem(s)**, and exits 1. Those 18
   are #748's and #749's to have drifted, and are re-anchored below; on this
   tree the same command prints **44** rows, all `ok`, and exits 0.
   Re-anchoring the rows is the whole of the change to that tool —
   `check_citations` and the `scan` it joins against are byte-identical to
   `origin/main` — so the two counts differ because the file moved, not because
   the check changed.
2. **Six citation rows were already red** before this change, not the two
   the issue names. It named `read_early_exits` at `:739` and `:760`; the
   other four — `warn_unchecked_marks` at `ec_watch.py:254` and `:280`, the
   `Marker._loop` writer at `ec_watch.py:355`, and the per-capture census
   line at `grade_0751_isolation.py:2347` — were red for #719 and the commit
   after it and nothing named them. All six are re-anchored here, and two
   rows are added for sites the scan found and no citation named: the
   partition's own mark branch (`:1099` in the merged tree, `:973` on this
   branch), and its docstring's quotation of that branch (`:976`, `:928`),
   which is a place where the scan counts prose as a decision site.

   **#748 drifted twenty-three more**, by editing files this table cites
   without touching the table. The tool did say so — #748's own entry records
   the count as 6 drifted before its change and 29 after — and those are
   re-anchored here alongside the six, together with three rows this merged
   tree needs and neither branch had: `read_capture`'s byte-order-mark
   refusal, and the two `check_capture_encoding.py` sites #748 added, which
   the two-way join correctly flagged as a gap in the census.

   **#749 then moved the same table again**, splitting each reader's body out
   so the notice could run the strict rules over its own single read
   (`take_capture_row`, `mark_labels_of`, `partition_capture_rows`,
   `capture_snapshot`). That is why three of the rows above name a helper
   rather than the reader the issue quoted: `existing_mark_labels` no longer
   spells the skip rule at all, it delegates to `mark_labels_of`, which calls
   `skippable_row`; and the length test, the indexing and the mark branch are
   `take_capture_row`'s, which `read_capture` calls. #749's own pins are
   re-anchored at the lines the split left them at rather than dropped, and the
   merged table is the union of the two. The skip rule went from the two rows
   `origin/main` cited it on — `:695` and `:871`, the same test written out
   twice, in `read_capture` and in the reader the notice used — to the four
   this table holds: `skippable_row`'s body at `:845` and the three readers
   that call it, at `:890`, `:1065` and `:1086`. That 2 → 4 is worth 2 of the
   run; the other 4 are this branch's newly cited sites,
   `grade_0751_isolation.py:976`, its byte-order-mark refusal at `:886`, and
   `check_capture_encoding.py:166` and `:243`. So 38 rows on `origin/main`, + 2
   for the rule and + 4 new sites, is the **44** the tool prints. The tool
   now prints `ok` for all **44** rows and exits 0, and
   `docs/findings/0751-mark-provenance-shapes.md` names every one of them,
   which is what `check_page` holds it to.

The tool's own measurements — the shape costs, the `#` namespace argument, the
fixture census — are unchanged by either issue and are not re-derived here. Its
census of sites carrying `"MARK"` is *not* unchanged: it is 8 consumers rather
than 6, because #748 added two, and the page says which is which.

## How to re-check this

```console
python3 ec/tools/grade_0751_isolation.py --self-test      # 111 cases
python3 ec/tools/measure_mark_provenance.py               # 44 citations, exit 0
bash .github/scripts/agent-gates.sh
```

**Not run by anything today, and not fixed here.** `grep -rn 'grade_0751'
.github/` finds nothing: this suite runs per-commit only because a human
applies `docs/ci/agent-gates-0751-self-test.patch`. Until then a PR that breaks
one of these refusals still merges green. That gap is recorded, and landing
the patch is a human's step.

## What this leaves open

- The remaining second copies of the skip rule in the *other* family,
  `grade_timer_sweep.load` — now measurable as a census rather than a claim.
- Whether the *format* should ever accept a byte-order mark. #748 decided the
  codec and left this; the strip does not decide it and `utf-8-sig` is not used
  anywhere. The `ï»¿` case this page once listed here is gone rather than open:
  with the codec declared there is no reading of those bytes left to repair.
- Whether `refused_capture_rows` should ever share the four-field test, which
  would delete the preflight and is therefore not a question about sharing.
- Whether the cheap gate should run this suite per commit. The patch is
  prepared; a human lands it.
