# A fifth `provenance` column on the mark row, and the reader that makes it worth writing (issue #739)

#719 measured two shapes for the question `warn_unchecked_marks` says it
cannot answer — which process wrote this mark — and recommended one. This is
that recommendation implemented: a fifth column on the `ts,MARK,,label` row,
written by three of the four writers that write the row in this tree —
`manual_fan_ctrl_probe.py` is the fourth and is left alone on purpose, decided
below — and a reader that returns the column *and the position of the row
holding it*.

The measurement is [`ec/tools/measure_mark_provenance.py`](../../ec/tools/measure_mark_provenance.py)
and its write-up is
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md). Nothing
below re-argues the choice; the four grounds for it are there, and they are
re-run over this tree rather than quoted.

**Nothing here has been run at a machine.** No EC, no laptop and no Windows
box is reachable from a runner. No capture was taken, no mark was typed, no
register was read and no §3 block was run. Every figure below is offline
behaviour of a reader over a temp file, or a count over committed files. The
three commands in
[§3 of the runbook](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md)
are where a human later sees a populated column, and that is their step.

---

## The four writer decisions, one by one

The measurement's "Its costs" section is explicit that three of the four
writers must be decided rather than left to drift, so here they are, each
with the line that decided it.

### 1. `windows/tools/ec_watch.py` `Marker._loop` — widened, and the column is populated

`windows/tools/ec_watch.py:509` now writes
`self._sink.row([ts, "MARK", "", label, self._provenance or ""])`, and
`Marker.__init__` at `windows/tools/ec_watch.py:454` takes a defaulted
`provenance=None` that `main` fills in at `windows/tools/ec_watch.py:578`
when `--label-vocab` is given and passes at `windows/tools/ec_watch.py:589`.
`--label-vocab` is the only flag in the tree that produces a populated
column, because it is the only one that says the process is checking
anything.

*(Re-anchored at issue #762, from `:493`/`:438`/`:562`/`:573`, which are the
lines this page carried on the tree #739 landed on and which
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) still quotes
in its frozen section-5 transcript. Nothing about the decision changed; the
four lines moved. #739's own after/before table below is left as it was
written, because it is the record of that change rather than of this one.)*

**What the column holds is `prog=<basename of argv[0]> label-vocab=<name>`,
and that is a decision rather than a shortened `sys.argv`.** Three reasons, and
the first is the one that settles it:

- A raw join would carry commas, path bytes that are not the format's declared
  `utf-8`, and a length no reader needs. `prog=` and `label-vocab=` are the two
  facts a reader of a capture cannot get any other way.
- The `pid=` the measurement's own `PROVENANCE` sample carried is **gone**, and
  its sample changed with it. Nothing in this repository reads a pid, and one
  would make two captures of the same run differ for a reason no reader could
  use — which would make a committed capture irreproducible for nothing.
- The tool's constructed captures hold what the writers hold, not a shape
  nobody writes. That is the same complaint its `write_capture` makes about a
  hand-joined row a few lines above, applied one level up.

`Path(sys.argv[0]).name` rather than `sys.argv[0]` for the same reason: a
staged `C:\tools\ec_watch.py` and a checkout's `ec_watch.py` are the same
program, and a column that differed by a directory would be saying something
about where a tool was staged rather than about what it checked.

**The default is the load-bearing part, not an omission.** `Marker` is
imported at module scope by `gpu_block_watch.py:59,166`, which constructs
`Marker(sink)` with nothing to put in a fourth argument. If the column were
written only when there is something to say, that caller's marks would come
back as *not recorded* — state 1 — where the honest answer is state 2, *held
no flag*. Those two are different claims about different things, and the whole
reason the three states are states is that they are different. So the column
is written always, empty when there is nothing to say.

### 2. `windows/tools/system_id_probe.py` `Marker._loop` — widened, empty column

`windows/tools/system_id_probe.py:268` writes the fifth field as `""`. The
column is a shape and this process has no `--label-vocab` to record, which is
state 2 rather than a gap in the change.

Its `CSV_HEADER` at `windows/tools/system_id_probe.py:111` is a **different
schema** — `ts,sweep,0x…,branch,implied` — and is deliberately not touched;
see *The header* below. Its `CsvSink` at `windows/tools/system_id_probe.py:221`
writes that header and nothing else, and it shares no code with
`ec_watch.py`'s.

This writer imports no `ec_watch.Marker`, so scoping the change to
`ec_watch.Marker._loop` would not have reached it. That was the measurement's
point 1 and it is why the decision is written down here rather than made by
omission.

### 3. `ec/tools/ec_timer_capture.py`, four sites — widened, empty column

`ec/tools/ec_timer_capture.py:177`, `:212`, `:218` and `:240`. A different
capture family, in files the 0751 grader would also open, read by
`grade_timer_sweep.py:354` under a different label convention
(`resumed` at `ec/tools/grade_timer_sweep.py:355`).

That reader indexes `r[1]` and `r[3]` and never `r[4]`, so the cost of the
column here is zero — which was the measurement's point 2, and the reason to
widen rather than leave a second four-column writer in the same shape. What
this family gets from the change is smaller and real: a capture taken after
it is distinguishable from one taken before it, by a field rather than by a
date in a filename.

`Sink.__init__` at `ec/tools/ec_timer_capture.py:150` writes no header — the
header is written in `main`, at `ec/tools/ec_timer_capture.py:321`, and is
covered below.

### 4. `windows/tools/manual_fan_ctrl_probe.py` `MarkCsv.mark` — **not** widened

`windows/tools/manual_fan_ctrl_probe.py:450` is unchanged, and this is a
decision rather than an oversight. Four reasons, in the order they decided
it:

- **The format's own documentation already anticipates it.** The
  measurement's backward-compatibility section lists state 1 as "a pre-change
  file, **or a probe capture under this scope**"
  ([`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md), under
  *Backward compatibility: three states, not two*). A four-column row from
  this writer therefore already has a documented reading, and a populated
  column could never appear there to contradict it.
- **It holds no flag, so the column would be empty there too.** Its labels
  come from `arm_labels` at `windows/tools/manual_fan_ctrl_probe.py:389` in a
  process that never runs `--label-vocab`. Widening it would add a field to
  every mark it writes in order to say nothing, and it would move a fourth
  writer's captures from state 1 to state 2 for no reader's benefit.
- **It would make two committed assertions fail**,
  `windows/tools/test_manual_fan_ctrl_probe.py:513` and `:515`, which is the
  canary working and not an argument against anything — see below.
- **The runbook cause it stands for stays open either way.** That capture is
  reason (d) in the runbook's four ways a file comes to hold an unchecked
  mark, and a fifth column does not resolve it: nothing in the file can say
  what §3's forms are checked against when the process that wrote it holds no
  vocabulary. That is a separate issue; see *What not widening costs* below.

**The tripwire for whichever issue does widen it is named here, so it is
found rather than rediscovered:** `mark_rows` at
`windows/tools/test_manual_fan_ctrl_probe.py:508` filters on
`len(r) == 4` and `:515` asserts `self.assertEqual(len(row), 4, row)`. Those
two lines are the first thing that fails, and `:508` fails *silently* — it
returns an empty list rather than raising, so a suite that only counted the
result would see zero marks and pass.

---

## The reader: `existing_mark_provenance`

`ec/tools/grade_0751_isolation.py:1091`, placed immediately after
`mark_labels_of` so the row's shape is stated in one place rather than two.
It returns `(row_ordinal, ts, label, provenance)` per mark row.

**It lives in the grader and not in a writer, and that is #548's rule rather
than a preference.** The prompt loads this module by path precisely so no
second copy of a rule can drift from the thing that enforces it; a reader
that returned the column from a writer would be exactly the copy
`load_label_vocab`'s lookup of the grader's four names exists to stop. The
shape of a mark row is the grader's, and so is the shape of the column on it.

Three things about the return value, each of which the docstring states and
`MarkProvenanceTests` pins:

- **`row_ordinal` is a row ordinal and not a line number.** It is 0-based
  over every row `csv.reader` yields — the header, the `#` rows and the blank
  lines included, all of which `skippable_row` drops. The two differ on a
  hand-annotated capture, because a quoted CSV field can carry an embedded
  newline: `MarkProvenanceTests.test_the_ordinal_is_a_row_ordinal_and_not_a_line_number`
  is the one mark at one position and two lines. A reader can produce the
  ordinal from the rows it already has; a line number would have to re-open
  the file as text and re-derive the record boundaries `csv` is what decided
  them by.
- **`None` and `""` are different values, and that is the whole of what the
  column is for.** `None` is the column absent, `""` is the column present
  and empty, and the text is present and populated. **A four-column row can
  therefore never be read as "this process did not hold the flag."** It reads
  as *not recorded*, which is a weaker claim about a different thing; a
  reader that conflated them would turn a pre-change capture into evidence
  about a console that was never asked.
- **The preflight contract is carried over**, not re-decided. It is built on
  `capture_rows(path, errors="replace")` and `skippable_row`, so it does not
  raise on anything `read_capture` refuses — a short row, a timestamp
  `parse_ts` cannot read, a byte outside the declared codec — and does not
  die on the file's encoding. A two-column mark row comes back as
  `(N, ts, "", None)`, matching `mark_labels_of`'s tolerance in both defaults
  and neither of them touching the timestamp: the label is defaulted to `""`
  and the provenance to `None`, and the timestamp is passed through, because
  it is the one field every row has and the caller is here to read it. The
  reason is
  `existing_mark_labels`' and it is unchanged: the file is one a watcher is
  about to append to, and a preflight that would not open it loses the one
  warning the notice exists to print.

**One function, not a `mark_provenance_of(rows)` beside it.** No second
caller needs the rows form, and `existing_mark_labels`' pair of that shape
exists only because `existing_mark_findings` re-reads the file; this reader
has one caller, and the tool's own self-test is that caller.

**The skip rule and the `MARK` predicate are spelled in its own body**, as
the third and fourth such spellings do. The guard against that drifting is a
test rather than a refactor: `MarkProvenanceTests` at
`ec/tools/test_grade_0751_isolation.py:5021` holds this reader to
`mark_labels_of` over **every committed fixture** under `ec/tools/testdata/`,
so a mark this reaches and a mark the notice lists cannot part. That is the
same idiom `ExistingMarkLabelTests` uses, and the same reason: merging the
three contracts would delete the preflight rather than state the shape once.

**It is deliberately not in `measure_mark_provenance.py`'s `families` table.**
That table drives the assertion that *no* reader's result differs under
either shape, and this reader's whole purpose is that its result does — it
is printed under the table instead, as its own line in section 3, and checked
in `--self-test` beside the same comparison rather than inside it. Adding it
to `families` would fail the self-test the issue requires to stay green.

**What a populated column is not: "this label was checked."** It is *a
process that said it was checking, wrote this*. The per-label verdict is
`parse_mark` and `unplaceable_marks`, which already exist, are per-label, and
know nothing about who typed what. `warn_unchecked_marks` says nothing new and
this change does not promise the operator a better warning: the notice at
`windows/tools/ec_watch.py:295` still builds its list from
`existing_mark_findings`, which still returns `(ts, label)` pairs. What landed
is the column and the reader that can see it, not a consumer.

---

## The header, which the issue does not name

`windows/tools/ec_watch.py:155` writes
`["ts", "addr", "old", "new", "provenance"]` on a new file, and
`ec/tools/ec_timer_capture.py:321` does the same for the timer family.
**The consequence, stated plainly: a new capture has a five-name header over
four-field change rows, because the fifth field is a mark-row field.** Change
rows are unchanged — `ts,addr,old,new`, four fields, as before.

That is the right trade rather than a compromise, and the reason is that
every reader in the tree drops the header anyway. `skippable_row` at
`ec/tools/grade_0751_isolation.py:1123` takes it on `row[0] == "ts"`, and so do
`grade_timer_sweep.py:352` and `check_capture_encoding.py:164` with their own
spelling of the same test. A name the change rows do not use costs none of
them, and a header that named four would document a five-field mark row
wrongly, which is the failure this column's whole point is to avoid.

**This is a format change the measurement did not record.** Its section 2
counts a header as present or absent per fixture and never asks what the
header *says*, and its section 1 scans for `"MARK"` and does not match a
header line. Both are blind sides of scans that were written to answer
different questions; the one that is worth naming is that "the writer writes
a header" was not in the census at all until the second header was found here.

`windows/tools/system_id_probe.py:221` writes its own `CSV_HEADER` and is
deliberately **not** widened: `ts,sweep,0x…,branch,implied` is a different
schema whose names are not this row's names, and adding `provenance` to it
would be a claim about columns that file does not have. Naming it in the
tool's citation table is what makes "left alone" a decision rather than an
omission.

---

## The census had a blind side, and widening this row found the other three

The measurement looked for the one committed assertion of an exact column
count and named `windows/tools/test_manual_fan_ctrl_probe.py:515` as the
canary. **The order of failures is not what the issue's framing says, and
that is worth correcting while the sites are still fresh.** The lines below
are where each assertion stands *after* the repair; "breaks when" is what
happened to the version that was there before it.

| site | what the line reads now | what it did when the row gained a field |
|---|---|---|
| `windows/tools/test_ec_watch.py:135` | the header equality, naming five columns | it asserted `ts,addr,old,new` — four names |
| `windows/tools/test_ec_watch.py:138` | the mark row in a row-list assertion, with its trailing comma | the list ended at the label, so the row's text did not match |
| `windows/tools/test_ec_watch.py:179` | the fifth field read off the raw row by index, in the test split out for it | it was a **four**-way unpack, and a five-field row raises `ValueError: too many values to unpack (expected 4)` **before any assertion in the test runs** |
| `windows/tools/test_ec_watch.py:270` | the same row list, in the blank-press class | the same |
| `windows/tools/test_ec_watch.py:443` | the same row list in a run holding `--label-vocab`, compared without the fifth field | the row's fifth field named whichever runner invoked the suite, so a literal list of rows could not hold it |
| `windows/tools/test_gpu_block_watch.py:1145` | the header equality, naming five columns | it asserted four names — `gpu_block_watch.py:59,166` imports `CsvSink` and `Marker` from `ec_watch` and constructs `Marker(sink)` |
| `windows/tools/test_gpu_block_watch.py:1148` | the mark row, with its trailing comma | the list ended at the label |
| `windows/tools/test_system_id_probe.py:322` | the mark row, with its trailing comma | the assertion's right side was the four-field row |
| `windows/tools/test_system_id_probe.py:341` | the capture handed to `grader.read_capture`, where `test_ec_watch.py:179` was a five-way unpack | a four-way unpack |
| `windows/tools/test_manual_fan_ctrl_probe.py:508` | `mark_rows`'s `len(r) == 4` filter | **unchanged**, and it would fail *silently* — an empty list rather than an exception |
| `windows/tools/test_manual_fan_ctrl_probe.py:513` | the header equality, four names | **unchanged** — only if the probe is widened, which this change does not do |
| `windows/tools/test_manual_fan_ctrl_probe.py:515` | `self.assertEqual(len(row), 4, row)` | **unchanged**, and the loudest of the three: it is the first to raise |

So the *first* failure of the three suites the change actually breaks is an
assertion rather than the exception, and it is in `test_ec_watch.py` rather
than in the file the measurement named. Reproduced with `origin/main`'s
`test_ec_watch.py` checked back over the widened writers, then
`python3 windows/tools/test_ec_watch.py -v`, the order is
`BlankMarkTests.test_a_blank_press_writes_no_row_and_leaves_the_real_mark_alone`
**FAIL** on the row list at `:241`, then
`MarkCsvTests.test_mark_lands_in_the_csv_between_the_change_rows` **FAIL** on
the header equality at `:135`, then
`MarkCsvTests.test_mark_row_parses_as_the_grader_expects` **ERROR**
`ValueError: too many values to unpack (expected 4)` at the four-way unpack the
table names at `:179`, and last
`RefusedLabelTests.test_a_refused_label_writes_no_row_and_leaves_the_real_mark_alone`
**FAIL** on the row list at `:414`. `test_gpu_block_watch.py` raises nothing at
all: with the same writers over `origin/main`'s test file, the one assertion
the change breaks there is its own header equality.

**The exception is still the finding, and the `:179` row's per-test claim
stands as the run shows it.** The unpack raises before its own test reaches an
assertion, so it is the one failure here that no row-text assertion would have
caught, and it is the one the canary scan cannot see — that scan matches one
literal line in one file, and the tree spells the same fact as a four-way
tuple unpack in two of them, the second in `test_system_id_probe.py`. What the
run corrects is the *order*, not the exception: the scan looked for one
spelling of "an exact column count" and the tree has three more, none of
which is that spelling.

This is the fourth spelling of the same fact this tree keeps producing: the
measurement's own census found seven writers where a hand-typed list would
have found two, its literal scan missed the single-quoted `'MARK'`
assertions, its call scan missed the consumers that only count, and its
canary scan missed the unpacks. **None of these is a defect in the scans**,
which were each written to answer one question. The generalisation is the one
worth keeping: a census's coverage is a property of the pattern it matches,
and "the tree has more of this than the scan says" is the default outcome of
writing the pattern before looking at what the tree holds.

---

## The issue's line numbers had drifted, and the real ones are above

Every line in the issue's text is a line that has since moved. Recorded here
rather than silently re-pinned, so a reader who goes looking for `:355` knows
what happened to it:

- `ec_watch.py:355` (`Marker._loop`) was already stale before this change:
  it read `windows/tools/ec_watch.py:433`, and is `:450` now. The issue's
  `:254` for `warn_unchecked_marks` read `:288` and is `:295`; `:361` read
  `:368` and is `:368` — that one had not moved. The tool's table had
  re-anchored `:473`/`:288`/`:361` after #718, #748 and #749; this change
  moved them again and the table moved with them.
- `system_id_probe.py:256` was already stale before this change: the writer
  read `:261` and is `:268` now.
- `ec_timer_capture.py:164`, `:199`, `:205`, `:227` are `:169`, `:204`,
  `:210`, `:232` before this change.
- `grade_0751_isolation.py:735` (`existing_mark_labels`) is `:896`, and the
  flat `(row[0], row[3])` list the issue names is built in `mark_labels_of` at
  `:1087`, not at `:735`.
- `measure_mark_provenance.py:457` (`CITATIONS`) and `:621`/`:647`
  (`check_citations`/`check_page`) are the tool's own, and the most volatile
  lines in the tree: they are `:518`, `:705` and `:731` now. Named by
  function rather than by line below, deliberately.
- **One pin in the tool had already drifted on `main` before this change and
  was not this change's to move:** `check_capture_claims.py:514` read
  `DRIFT` against this tree, the call being at `:576`. It is re-anchored
  here so the tool is green, and it is named here because a pin corrected in
  passing is a pin whose history cannot be read.

---

## The pins this change moved

`measure_mark_provenance.py` re-reads every site at the line quoted, and
`check_page` holds the write-ups to the tool's output, so a pin that moved has
to be named by a page that says it moved. This is that page for the pins the
change moved; the *before* column is what
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md) quotes, and
it is left there rather than edited, because that page is the record of a
measurement and this one is the record of a format change. The three rows at
the foot of the table are the exception, and the paragraph below them says
what makes them one.

| after | before |
|---|---|
| `windows/tools/ec_watch.py:155` | — (the header is new to the census) |
| `windows/tools/ec_watch.py:295` | `:288` |
| `windows/tools/ec_watch.py:368` | `:361` |
| `windows/tools/ec_watch.py:493` | `:473` |
| `windows/tools/system_id_probe.py:268` | `:261` |
| `ec/tools/ec_timer_capture.py:157` | `:149` |
| `ec/tools/ec_timer_capture.py:177` | `:169` |
| `ec/tools/ec_timer_capture.py:212` | `:204` |
| `ec/tools/ec_timer_capture.py:218` | `:210` |
| `ec/tools/ec_timer_capture.py:240` | `:232` |
| `ec/tools/ec_timer_capture.py:321` | — (the header is new to the census) |
| `ec/tools/grade_0751_isolation.py:1195` | — (the reader is new) |
| `ec/tools/grade_0751_isolation.py:1218` | `:1108` |
| `ec/tools/grade_0751_isolation.py:1231` | `:1121` |
| `ec/tools/grade_0751_isolation.py:1474` | `:1364` |
| `ec/tools/grade_0751_isolation.py:1516` | `:1406` |
| `ec/tools/grade_0751_isolation.py:3105` | `:2994` |
| `ec/tools/check_capture_claims.py:576` | `:514` (drifted before this change) |
| `windows/tools/test_ec_watch.py:159` | `:145` |
| `windows/tools/test_system_id_probe.py:343` | `:341` (and `:311` before #739) |
| `windows/tools/test_ec_watch.py:1205` | `:1134` (landed at `:1168` and `:1176`) |

**The last three rows are this change's edits to the two test files, and every
one of them is a pin two write-ups this change does not own also carry** — two
in [`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md), one in
[`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md). The
widened rows put lines into both files above what those three pins name, which
moved what each of them landed on: two assertions became a `comment` and a
`def test_` header, which left the census's per-pin table recording `carries`
for lines that no longer held the sentence they were cited for. The `before`
column is what each read, and these three are the exception the paragraph
above names: the shapes page's live prose is re-anchored rather than left,
because leaving it would leave a citation naming a line that no longer holds
what it is cited for. The two fenced transcripts that print the same three
lines move with the prose — which is the note at the head of
`0751-path-taking-reader-fates.md` and
`test_every_declined_pin_is_also_cited_in_live_prose` between them, and a
declined pin whose line nothing else names is a lost record rather than a
declined duplicate. The rule is what holds; the two sides move together.

**`:1205` is a third landing, and each is this change's own doing.** The
repair of `test_a_run_holding_the_vocabulary_names_itself_in_the_mark_row` put
comment lines into `test_ec_watch.py` above it, and a later change on the same
issue put more there by reading both mark-row tests through the grader, which
is what carried `:1168` to `:1176` and then to `:1205` — named here because a
pin moved by this change's own later edit is the one kind of drift the table
above cannot show by itself. Its `before` column stays `:1134` because that is
where the line stood on `origin/main`, and a before/after pair records where a
pin came from and where it ends rather than each hop: the two re-anchored
write-ups moved with it, and `0751-path-taking-reader-fates.md`'s `grep`
transcript now prints `:1205` too, which is what a transcript is for.

With that done, the census over a tree carrying this page moved out reads
`origin/main` figure for figure — `106` records, `28` files, `79` spellings,
`58` targets, `74` resolves against `32` declined, the `0/14/22/5/33` split —
so this change's edits to the two test files leave no drift behind them. The
step from there to this tree is this page's own records, and
`ec/tools/test_census_test_line_pins.py` carries the arithmetic.

*(Correction, same day and same issue: "figure for figure" was true when this
was written and is not now, and the two records that broke it are the ones
re-running [`0751-path-taking-reader-fates.md`](0751-path-taking-reader-fates.md)'s
second transcript added — the grader suite's twelfth `existing_mark_labels`
line, which this change's own edits to that suite created. With this page
moved out the run reads `108` records, `28` files, `81` spellings, `59`
targets, `75` resolves against `33` declined, the `0/14/22/5/34` split, which
is `origin/main` plus exactly those two: `+2` records, `+2` spellings, `+1`
target and `+1` resolve (a declined pin resolves to nothing, so only the
live-prose twin is a target) and `+1` `other`. **The `origin/main` figures stay
written above and are the record of the tree they were measured on.** The
paragraph's claim is not that the run comes back to `origin/main` — it is that
nothing is left over to attribute to somebody, and the two records that are
there are the transcript's and are named in the row above. A control that had
to be re-measured to stay a control is worth the sentence saying so.)*

The shapes page's own transcripts — sections 1, 2, 3 and 5 — are the
measurement's as taken, and they are a quotation of a run rather than a live
view. Re-run the tool rather than trusting them; that is what the page says
about itself, and this change is the case it was written for. Two lines of the
section-5 transcript are the exception, and they are the two this change's
re-anchoring of the tool's own `CITATIONS` moved: a transcript naming a line
the tool no longer cites would leave the page disagreeing with the tool about
the tool's own output, which is the one thing a quotation is for. That
re-anchoring is this change's own: the tool cited the two `assertEqual` tuple
unpacks that reading the mark row through the reader deleted, so its two
`CITATIONS` rows now name the single-quoted MARK assertions that outlived them,
one in each suite.

---

## What a populated column does and does not say

**It says:** which program wrote the mark, and that that program held
`--label-vocab 0751` when it did. Those are the two facts a reader cannot
get another way, and they separate a `gpu_block_watch.py` mark from an
`ec_watch.py` one, and a mark typed under the vocabulary from one typed
without it.

**It does not say which console wrote a mark, and cannot.** §3 runs three
consoles, all three of them `python windows\tools\ec_watch.py … --mark
--label-vocab 0751`
([`../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`](../../docs/hardware-tests/manual-fan-ctrl-0751-isolation.md):158-163),
and the field is built from the program name and the vocabulary alone
(`windows/tools/ec_watch.py:562`) — so all three write the byte-identical
`prog=ec_watch.py label-vocab=0751`. Two of `warn_unchecked_marks`'s four
arrivals also collapse: a console started without the flag and a
`gpu_block_watch.py` capture both write an empty field, and are one value in
the file rather than two. So the four arrivals are three distinguishable
values, not four, and the one a §3 operator most wants — *which of my three
windows did I type this in* — is not among them. The three captures are told
apart by their `--csv` filenames.

**It does not say:** that the label was checked, or that the mark is
placeable, or that the block it sits in is the block the operator intended.
Those are `parse_mark` and `unplaceable_marks`, and they are per-label. A
consumer that printed this column as a checking verdict would be reporting
something the file does not contain — which is why the reader's own docstring
says it in those words and the tests do not assert anything about labels
through it.

**It is not a claim about the machine.** Nothing in this change was observed
at a laptop. The four states of a capture's usefulness to a reader — absent,
empty, populated, and *never written by a human* — are all decided by what a
program writes into a file, and a program writing into a file is the whole of
what has been verified.

---

## What is out of scope, and what is left open

- **`manual_fan_ctrl_probe.py`**, decided against above with the tripwire
  named. A follow-up issue, not this one.
- **Any consumer.** Displaying provenance in the notice, grading on it, a
  `--check-provenance` mode: the reader is the deliverable, the consumer is
  the next issue. This change promises the operator no better warning and
  delivers none.
- **Re-recording the two committed timer captures** in
  `evidence/ec-watch/`. They stopped being representative the day a capture is
  taken with the new shape, which is a hardware run. The honest statement is
  that they are stale as *examples* of the format, not that they are wrong:
  they are four-column mark rows, and the reader reads them as state 1, which
  is the correct reading of a four-column row.
- **The committed fixtures.** The 50 mark-bearing captures are **48 under
  `ec/tools/testdata` and 2 under `evidence/ec-watch`**, the split section 2
  of the tool above already prints (`48 file(s), 239 MARK row(s)` and
  `2 file(s), 8 MARK row(s)`), and all 50 hold four-column mark rows and all
  50 still read the same. **That last half has a check behind it, and the tool
  is not the one this section used to name.** `check_capture_claims.py`'s
  `read_capture` index is built from `WATCH = "evidence/ec-watch"` alone
  (`ec/tools/check_capture_claims.py:181`, the one call at `:607`), and a run
  there reports *9 capture claims checked against 10 committed captures*: it
  reads the two, and never the 48. What walks the 48 is
  `MarkProvenanceTests.test_it_agrees_with_the_reader_the_notice_lists_marks_from`
  in `ec/tools/test_grade_0751_isolation.py`, which reads every
  `testdata/**/*.csv`, holds `existing_mark_provenance` to the `(ts, label)`
  pairs `mark_labels_of` returns from the same file, and counts the marks it
  saw — so a walk that found no captures cannot pass over the corpus.
  `check_testdata_row_claims.py` is the other committed tool that opens those
  fixtures, through `read_capture` at its `:656`. Either way the fixture set
  is not inert to the format change, only unchanged by it.
- **Anything outside this repository.** No issue and no pull request is opened
  anywhere else, and this change does not end at an upstream contribution.
- **`.github/`.** The push token has no `workflow` scope, so no gate is wired
  for the repaired suites or the tool's new cases. `agent-gates.sh` is a file
  copied from `ElDavoo/agent-pipeline` and a gate call is an upstream change
  and a re-copy, not a line here — the same reason
  `0751-mark-provenance-shapes.md` left its self-test ungated.

## Re-deriving this

```console
python3 ec/tools/measure_mark_provenance.py              # the tables, re-run
python3 ec/tools/measure_mark_provenance.py --self-test  # checked rather than printed
python3 ec/tools/test_grade_0751_isolation.py            # MarkProvenanceTests walks the 48
bash tools/run-tests.sh                                  # the suites the change touches
python3 ec/tools/check_capture_claims.py                 # its 10 captures, 2 mark-bearing
```

Every one of these is offline: temp files and committed captures. None of them
opens an EC, and none of them is evidence about the machine.

**What `run-tests.sh` actually reports on this tree, since a green run is a
claim and not a default.** Three of the four suites that assert something about
the mark row's columns are green — `test_ec_watch.py` 48 tests OK,
`test_system_id_probe.py` 32 OK, and `test_manual_fan_ctrl_probe.py` 67 OK,
which is the canary staying green. The fourth, `test_gpu_block_watch.py`, ends
`FAILED (failures=4)`: all four about `0x07C5` in `dsdt.dsl` against
`ec/annotations/registers.yaml`, and the same four fail on an `origin/main`
worktree, so what this change repaired in that suite is not what the four are.
`ec/tools/test_check_pin_table_rows.py` is the fifth suite this change touches
and it goes the other way: three failures on `origin/main`, two here. The one
that stops failing is `test_the_committed_table_places_something`, whose own
comment re-derives `placed` at `127` and records the
`docs/agent-pipeline.md:409`-`:410` pair as pre-existing; the two that remain
are that same unplaced row seen from the other side —
`test_every_class_is_zero_on_the_committed_tree` and
`test_the_committed_table_reconciles_and_exits_zero`. A reduction, not a
lowering.

---

## What not widening costs

Decision 4 above is right for its four reasons and it is not free, and this is
the bill. `manual_fan_ctrl_probe.py` keeps the four-column mark row, so
from this change on a probe capture and an `ec_watch.py` one are
distinguishable by a field, where before the change nothing but the tool that
wrote a file separated them. That is the same *taken after the change / taken
before it* property the timer family is widened for, and this writer is left on
the other side of it deliberately rather than by oversight.

Two pieces of prose had to follow, and both are in this change. `ec_watch.py:58`
lists a probe capture among the four ways a file comes to hold a mark this
process did not type, and called it "the same `ts,MARK,,label` row" — still
true of the field count, no longer true of the row, so it now says the writer
stamps "that row and no fifth field". And the probe's own two docstrings, which
said `--csv` writes what `ec_watch.py --mark --csv` writes, now say it keeps the
four-column row on purpose, so a capture from either tool is identifiable by its
shape alone. Neither is a behaviour change; both are the format change being
stated where a reader of one file would otherwise be misled by the other.

The cost is bounded and it is the tripwire already named in decision 4 above, so
whichever issue does widen this writer fails there first, and fails on the
column count rather than on anything this page added.
