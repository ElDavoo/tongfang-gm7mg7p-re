# The 0751 startup notice described two moments as one (issue #749)

The write-up for [issue
#749](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/749), which
followed #718 from the same chain. #718 gave `existing_mark_findings` a second
reader and recorded the fact in `windows/tools/ec_watch-marks.md` — *"The file
is read twice where it was read once"* — without saying whether the two reads
were the same moment. They were not. This closes that, and the close is one
`open()` rather than two.

Nothing here is evidence about the machine. No §3 run was performed, no
Windows box was reached, no EC was opened and no mark was typed. The whole of
the evidence is offline behaviour of a tool over hand-written rows in a
temporary directory, plus the committed fixtures in `ec/tools/testdata/`.

---

## The two reads, as the code stood

`existing_mark_findings` took the clean path like this:

| what | where (the tree #749 starts from) |
|---|---|
| `marks, _ = read_capture(path)` — the strict reader, and the marks the placement verdict is computed from | `:863` |
| `accepted = existing_mark_labels(path)` — a second `open()` of the same path, the lenient reader, and what the notice's first section lists | `:894` |
| `_, unplaced = assign_blocks(coalesce_marks(marks))` — placement computed from `:863`'s marks, not from the file `:894` just read | `:895` |
| `encoding = f.encoding` — a **second** open, inside the `UnicodeDecodeError` branch | `:872-873` |
| `existing_mark_labels(path)` on that branch — a **third** | `:878` |
| `refused_capture_rows(path)` on the `ValueError` path — a second again | `:880` |

**The issue's open counts are one high on the decode path, and the measured
figures are 2 and 3.** It called `f.encoding` a third open and the lenient
read a fourth; counting `builtins.open` against that module gives three, and
the clean path two. Which of them it started counting from is not worth
guessing at — the point is that the number in a write-up should be the one a
reader can reproduce, and `test_the_capture_is_opened_once_on_both_paths`
reproduces it.

Nothing serialised the two reads on the clean path. So the accepted list and
the placement verdict were two opens, microseconds apart, of a file that is
being appended to while it is read.

## The second writer is the premise, not a hazard the design tolerates

This is the part worth being exact about, because "a race" reads as a defect
to be removed and this one is a feature of the procedure.

- §3 runs **three** `--mark --csv` watchers, one per console, against the same
  capture. `coalesce_marks` joins the consoles' labels with `' / '`, and
  `MARK_MERGE_SECONDS = 5` (`:275`) exists precisely to fuse one action's marks
  into one window.
- `CsvSink.row` (`windows/tools/ec_watch.py:150-157`) flushes every row, so the
  other console's rows land as they are typed rather than at the end of a
  buffer.
- The lock at `windows/tools/ec_watch.py:146` is **per-instance**. Its own
  docstring says what it is for: so a mark cannot land in the middle of a
  change row on the stdin thread. It is not there to serialise two watchers,
  and nothing claims it is.

So the odds are low — two `open()` calls apart is a microsecond window, and no
case in this repository has been seen to land inside one. The point is not the
odds. It is that **nothing held the two answers to the same bytes**, and
`existing_mark_findings`' docstring made a single-moment claim about two
moments:

> On a file `read_capture` accepts this is exactly `existing_mark_labels`,
> called rather than written out again, so the success path grows no second
> label-extraction rule.

That sentence was false as written, and it was the sentence a later reader
would check the code against.

### The reachable defect, stated as it would print

If a row landed between the two reads, the notice could say:

- a mark in the **placement** section that the **accepted** section above it
  does not list — the placement pass saw it, `existing_mark_labels` ran before
  it; or
- the reverse — listed as accepted although the placement pass never saw it.

And the sharper case the issue names: a **half-written row** landing between
them. `read_capture` raises on it, `existing_mark_labels` names it as a label
with an empty one, and the two sections of one notice are describing different
files rather than one file at two instants.

None of this is observable from a test that runs a static fixture, which is
why the tests below stand a watcher in the middle of the read rather than
wait for the race.

## What changed

`ec/tools/grade_0751_isolation.py` only. One `open()`, one read, one row list,
and all three lists out of it.

**`capture_snapshot` (`:897`)** is the new reader. It opens the path in
**binary** once and reads it once — so there is no second open to be a second
moment — then decodes that one buffer with the format's codec. `capture_lines`
(`:927`) is the decode, as a `TextIOWrapper` over the buffer rather than
`raw.decode()` and a split, for two reasons that are both contract: the line
splitting is part of what `newline=""` means (universal newlines, terminators
kept, so `\r`, `\n` and `\r\n` all end a line, and `str.splitlines` would break
on a dozen characters perfectly legal inside a label), and **declaring the
codec `read_capture` declares** (#748) rather than inheriting this
interpreter's is what makes a `UnicodeDecodeError` from here the one
`read_capture` would have raised over the same bytes, on every box, rather
than one this tool decided to raise.

On a file that decodes, `decode_failure` is None and `rows` is every row
`csv.reader` reads. On one that does not, `decode_failure` is the exception
the decode raised and `rows` is **the same bytes** read leniently, for the
listing only.

**The per-row bodies are shared rather than copied.**

| new | what it holds | who calls it |
|---|---|---|
| `take_capture_row` (`:793`) | `read_capture`'s one row, unchanged: same order, same exceptions, same messages — and, since the merge with #748, the leading-BOM refusal #748 added to that body | `read_capture` (`:679`) and `existing_mark_findings` (`:947`) |
| `mark_labels_of` (`:838`) | `existing_mark_labels`' extraction, over rows rather than a path | `existing_mark_labels` (`:701`) and `existing_mark_findings` |
| `partition_capture_rows` (`:858`) | `refused_capture_rows`' conditions, over rows rather than a path | `refused_capture_rows` (`:744`) and `existing_mark_findings` |

So the docstring's "called rather than written out again" is now true by
construction rather than aspirational, and the strict verdict the notice prints
is `read_capture`'s own body run over rows it read itself.

`read_capture` keeps its signature, its open, its skip rule, its
raise-for-the-first-bad-row contract and its two-tuple.
`grade_gpu_door.py:421` and `check_capture_claims.py:514` unpack that tuple
and are untouched.

### The `f.encoding` read is gone, not argued for

`UnicodeDecodeError` carries the codec that failed in its own `.encoding`.
The refusal now names that, which is **strictly better** than a fresh open's
`.encoding`: it cannot disagree with the decode that failed, because it came
from it. And it removes an open outright rather than justifying keeping one.

Measured on this tree, a capture carrying a lone 0xE9 gives:

```
the grader's reader cannot decode a byte of this file in the utf-8 a capture
is defined to be, and raises before it reaches a row: 'utf-8' codec can't
decode byte 0xe9 in position 55: invalid continuation byte. A capture is
utf-8; this one is written in something else. Re-save it as utf-8, or re-run
the capture with a writer that declares the codec.
```

and `read_capture` on the same file raises exactly the quoted tail of the
first sentence. The first two clauses are #749's: the codec is the failing
decode's own, so it cannot name a codec other than the one that failed, and
naming it is no longer a third `open()` of a moving file. The trailing remedy
is #748's, which arrived in the same merge — with the codec a property of the
format rather than of the box reading it, a refusal carrying no remedy would
leave an operator holding a capture from another machine with nothing to do
about it. The snapshot decodes the whole buffer where `read_capture`'s text
layer decodes a chunk, so the `position` inside the exception can in principle
differ for a file larger than that chunk. Every committed fixture is far
smaller; the case that would expose it has not been written, and the property
that matters — that the encoding named is the one that failed — holds by
construction rather than by re-derivation.

### The `else` that can no longer fire is kept and reworded

#718's `else` branch, where the partition named no row although
`read_capture` had raised on one, was read as "the file moved between the two
reads". It cannot fire now: both readers run over one row list. A branch that
cannot fire is not the same as a branch that is not there, and silently
dropping a refusal is the worse failure, so it stays. Its comment no longer
calls it a file-moved guard; it says what it now is — a self-consistency
refusal, reachable only if the strict pass and the partition disagree about
the same rows, which is a rule drift rather than a file that changed.

## What this does **not** fix, stated plainly

- **The file still moves.** One `open()` is one moment, not a lock. A mark
  that lands after this call is still graded, by the whole-file grading later —
  which is exactly what the notice's closing paragraph already tells the
  operator ("the grader judges the whole file, so blocks 2 and 3 are expected
  to land here"), and nothing here changes that sentence.
- **It is not one *function* reading the file.** The skip rule — `#`, blank,
  `ts` header — is still spelled once per reader, in `read_capture` (`:695`)
  and again in `mark_labels_of` (`:871`), as it was in #548, and once more in
  each of the two places that need it over already-read rows. It is not
  unified here, and the count is the same as before. Two things hold the two
  readers to each other: `ExistingMarkLabelTests.test_the_skip_rule_is_read_captures_and_only_marks_come_back`
  and `measure_mark_provenance.py --self-test`, which runs both readers over
  all three shapes. This is still a duplication, and saying the file is read
  by one function would be the false claim in the other direction.

  > **Correction (2026-09-25, issue #750 merged on top), leaving the bullet
  > above as it was written.** The duplication it names is gone: the rule is
  > `skippable_row`, and `read_capture`, `mark_labels_of` and
  > `partition_capture_rows` call it. The line numbers above (`:695`,
  > `:871`) are this change's, and the rule's own body is at `:845` on the
  > merged tree. What is left un-unified is the rest of the shape — the
  > four-field test and the `MARK` branch — and the bullet's own reason for
  > leaving it holds and is #750's: they are three different contracts, so
  > merging them would delete the preflight rather than state the shape once.
  > The two tests named above still hold the three to each other; they now
  > guard the strictness rather than a spelling.
- **The partition's per-row wording is still its own.** The first refused row's
  reason is `read_capture`'s own exception, which `existing_mark_findings`
  puts there rather than re-deriving it. The rows after it are named by
  `partition_capture_rows`' re-applied conditions, whose **ordering** and
  per-row wording the anti-drift test holds. Only the first reason is shared
  verbatim; the rest are held, not delegated. Saying otherwise would overclaim
  the extraction.

## The tests, and what each one can catch

Four new cases in `ExistingMarkLabelTests`
(`ec/tools/test_grade_0751_isolation.py`), offline on fakes and hand-written
rows as the rest of that class is. The issue's own suggestion — a fixture that
appends from inside a patched `read_capture` — is deliberately **not** what
they do: after this change `existing_mark_findings` does not call
`read_capture`, so a stub there would go unused and pass for the wrong reason.
A false green is worse than no test. They hook `capture_snapshot`, the one
read that now exists.

1. **`test_the_capture_is_opened_once_on_both_paths`** wraps `builtins.open`
   and asserts exactly one open of the target path on the clean path and
   exactly one on the `UnicodeDecodeError` path (measured at 2 and 3 before
   the change). The count rather than the effect: the two reads differ from
   one only when the append happens to land between them, and a test that
   waits for that is a test that passes on a quiet filesystem.
2. **`test_a_row_that_lands_at_the_read_is_not_in_this_notice`** patches
   `capture_snapshot` with a wrapper that reads and *then* appends a
   well-formed mark carrying an unplaceable label, a minute out so it opens
   its own window. Asserts the notice describes the pre-append file in all
   three lists, and that a second, unpatched call *does* see the new row.
   Both directions, so a function that never looked at the file cannot pass by
   returning something constant.
3. **`test_a_half_written_row_at_the_read_is_refused_by_the_next_call`** is
   the sharper case: a half-written row lands at the read, so the notice
   reports the file it read with no refusal in it and the refusal appears on
   the next call. A second bad row is appended at the same instant in the
   second half, so a verdict re-read after the fact would name two rows where
   only one was there.
4. **`test_every_mark_the_notice_calls_unplaceable_is_one_it_accepted`** is
   the property the two reads could not hold, now held by construction: every
   `(ts, label)` the placement list names is one the accepted list holds. It
   is a property assertion rather than a defect detector — a file the race
   never touched would have passed it before the change too — and it is here
   because the issue asks for that sentence as an invariant, not because it
   distinguishes the two implementations.

`test_the_refusal_reasons_are_read_captures_own` is left **unchanged** and
still green. The shared body makes its first-reason property true by
construction; the test stays as the guard on the ordering and the per-row
wording the partition still spells itself.

Cases 1, 2 and 3 were run against the pre-#749 module — `git show
HEAD:ec/tools/grade_0751_isolation.py` loaded whole, with only
`existing_mark_findings` swapped back — and each fails there: `2 != 1` on the
open count, the appended row missing from the second call, and no
`ValueError` from `read_capture` on the file the wrapper was supposed to have
half-written. Case 4 passes against both, as above.

### The fallback that was available and not taken

The plan named a second route: freeze the file, one `shutil.copyfile` into a
`tempfile` directory, point every reader at the copy. It preserves every
message byte-for-byte with no rewrite and makes the `f.encoding` open
harmless, at the cost of a temp file in a tool that is otherwise pure
in-memory reads, plus a prefix rewrite of the path inside `read_capture`'s one
path-bearing message — which would have moved the anti-drift test's expected
text. The snapshot route was taken because it needs no temp file and leaves
every message alone. The fallback is recorded here so the choice is a
decision on the record rather than an accident.

## The line numbers moved again

#718's addendum has the table for its own change; this is the same measurement
taken again, for the same reason — a citation that silently retargets reads as
though the issue had been checked and found wrong about something that never
mattered.

This change inserts one block after `refused_capture_rows` and above
`existing_mark_findings`, for #718's merge-conflict reason, and moves the
bodies of `read_capture` and `existing_mark_labels` into the helpers. The
result is **not one-sided**: `import io` shifts everything below it by one,
the two extracted bodies pull the code above the new block up by ten, and the
new block then pushes everything below it down by 131.

**The third column is against the tree this change leaves as merged, not
against the branch's own tip.** #749 was rebased on #748, which declared
`utf-8` at the grader's readers and added a leading-BOM refusal to
`read_capture`'s row body; that body is `take_capture_row` here, so the BOM
check and its comment came with it, and #748's own lines push everything below
`read_capture` down further. The two movements are additive and both are
visible in the table.

| cited as | in the tree #749 starts from | in the merged tree |
|---|---|---|
| `import csv` (the top of the drift) | `:252` | `:252` — unmoved |
| `import io` | — did not exist | `:254` |
| `MARK_MERGE_SECONDS` | `:274` | `:275` |
| `read_capture` | `:678` | `:679` |
| `existing_mark_labels` | `:700` | `:701` |
| `refused_capture_rows` | `:739` | `:744` |
| `take_capture_row`, `mark_labels_of`, `partition_capture_rows`, `capture_snapshot`, `capture_lines` | — did not exist | `:793`, `:838`, `:858`, `:897`, `:927` |
| `existing_mark_findings` | `:802` | `:947` |
| `read_early_exits` | `:902` | `:1083` |
| `coalesce_marks` | `:985` | `:1173` |
| `unplaceable_marks` | `:1188` | `:1376` |
| `main`'s `read_capture(path)` / `read_early_exits(path)` | `:2506`, `:2515` | `:2694`, `:2703` |

The second column is this change's tree and is dated: #750 merged on top of it
and moved every line again, because it stated the row's skip rule and first
field once (`skippable_row`, `normalised_rows`) and put the open itself in
`capture_rows`. The same symbols on the merged tree are
`read_capture` `:852`, `existing_mark_labels` `:896`,
`refused_capture_rows` `:947`, `take_capture_row` `:1015`,
`mark_labels_of` `:1052`, `partition_capture_rows` `:1072`,
`capture_snapshot` `:1112`, `capture_lines` `:1155`,
`existing_mark_findings` `:1175`, `read_early_exits` `:1342`,
`coalesce_marks` `:1447`, `unplaceable_marks` `:1650`, and `main`'s two call
sites `:2968` and `:2977`. Those two changes are additive — #749 split the
readers' bodies out, #750 consolidated the shape — so nothing above is
withdrawn; the numbers simply moved a second time. The merged line numbers
`measure_mark_provenance.py` cites are re-anchored there, and that tool exits 0
on this tree.

Every citation in this file is from the merged tree, except the middle column,
which is against the tree the change starts from as the column says.

### The measurement tool's pins, and the problems it already had

`measure_mark_provenance.py` pins the grader's lines by number and checks each
pin still holds its quoted text, so this change retargets them — and the page
it checks them against,
[`0751-mark-provenance-shapes.md`](0751-mark-provenance-shapes.md), carries
the same numbers in its prose, its tables and a quoted tool run. All three
moved together, and all three were measured again after the merge.

> **Correction (2026-09-25, issue #749 review), leaving the sentence above as
> it was written.** "All three moved together" was true of the tables and the
> quoted tool run and false of the prose, and it is the sentence a reader is
> entitled to rely on. The tables and the quoted run were retargeted to the
> merged tree; seven prose anchors at six lines were not, so the page was
> internally inconsistent about the same function — `existing_mark_labels` at
> `:700` where the drift table above puts it at `:701`, the `(ts, label)` pair
> at `:735` where `mark_labels_of` now builds it at `:854`, `read_capture`'s
> explicit indexing at `:691` where it is now `:830`, and
> `system_id_probe.py:256` where that page's own census and its own item 1
> already said `:261`. They are retargeted, and every one of the page's own
> anchors has been re-read against this tree — the `:690` it quotes at the top
> is the issue's number, in a quotation of the issue, and is left as quoted.
> The anchors still standing are the non-#749 pins its addendum already
> records as DRIFT.
>
> Nothing caught it because `measure_mark_provenance.py` checks its own pins
> and never reads the page's prose, so a stale prose anchor is invisible to it
> and every grader pin reading `ok` says nothing about one. The addendum's
> DRIFT note covers the tool's pins for the same reason and does not extend to
> unchecked prose. The gap is in what the tool verifies, not in what it
> reports: the two are not the same set, and this is the first time they came
> apart on a page this change claimed to have re-measured.

Three things about that tool are worth recording, and none of them is a change
to its methodology:

- **`check_citations` crashed on the base tree.** It iterated `scan - named`
  unpacking three values from two-element tuples, so the moment a `MARK` site
  appeared that no citation names — which #718 had already caused — section 5
  ended in a `ValueError` traceback instead of the message its own docstring
  promises ("a row site the scan found and no citation names"). The unpacking
  is fixed here, because the command in the issue's own "what to show" list is
  meant to *report* moved pins and could not. Measured on the base tree with
  only that one-line fix, the tool reports **10** citation problems, 6 of them
  DRIFT pins.
- **Six of those ten were not #749's**, and were recorded rather than quietly
  fixed: `windows/tools/ec_watch.py:355`/`:254`/`:280` are pins that #718's
  insertions moved out from under (and `ec_watch.py:355` is additionally a
  site the scan no longer finds, with `ec_watch.py:446` the one it does), and
  the `MARK` string in #718's `refused_capture_rows` docstring is a site the
  base tree reported at `:760`. The one new site this change adds,
  `partition_capture_rows`' `if addr == "MARK":`, **is** cited. Correcting the
  other three in passing would have been a pin whose history nobody could
  read, so it is left as a follow-up.
- **The first pass at retargeting was one line low, and the tool said so on the
  branch's own tree.** Ten of the twelve grader pins this change moves were
  written one below the line they name — `if len(row) < 4:` at `:795` when
  `take_capture_row` puts it at `:796`, and likewise for the indexing, the
  partition's `MARK` test, `read_early_exits`, the phrase test and the census
  line. Measured on the branch as committed, the tool reports **22** problems,
  13 of them DRIFT and 10 of those the grader's own pins. The cause is not
  guessable and does not need to be: the pins are re-measured below rather
  than adjusted by the same one, and every grader pin now reads `ok`.

After the merge the follow-up is bigger, and the split is the same: **the
grader's own pins are re-measured here**, because they are this change's to
move, and **the pins #748 moved are left where #748 left them.** #748 added
`encoding="utf-8"` (and a BOM check) across the capture family, which shifted
`ec_watch.py`, `ec_timer_capture.py`, `grade_timer_sweep.py`,
`check_capture_claims.py`, `manual_fan_ctrl_probe.py`, `system_id_probe.py`,
`ec_timer_capture.py`'s `#` phrases and
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; #748's own write-up
recorded that as its tool's known red rather than retargeting pins from a
different issue, and that decision is not this change's to reverse.
`check_capture_encoding.py`, the tool #748 added, carries two
`ts,MARK,,label` sites of its own (`:166`, `:243`) that no citation names, and
`ec/tools/grade_0751_isolation.py:770` is the docstring site #748's addition
left where #718's had been. **What is measured on the merged tree, with the
grader's pins and the page re-transcribed, is 18 DRIFT pins and 37 citation
problems**; measured on this tree before that, it was 30 and 55, and all 12
of the extra DRIFT pins were the grader's.

## What this opens

**The same shape, one level down, with a heavier consequence.** `main` calls
`read_capture` at `:2694` and `read_early_exits` at `:2703` on the same
capture, so an early-exit row landing between those two reads is charged
against a block whose marks were read a moment earlier. Same hazard; a
contradictory *notice* is a line an operator reads at the start of a run, and a
contradictory *grade* is a block withheld at the end of a day. That is the
next question, not a half-fix smuggled in here. It is a real one: the fix is
the same snapshot, and the reason it is not in this change is that `main` has
read `read_capture`'s two-tuple out of the function ever since, and taking it
over one read is a change to the grader's own grading path with its own test
surface — not something to bundle into a notice fix.

**What a human still has to do, and has not.** §3's block-2 append against a
real `CsvSink`, and the notice printed against a real three-console capture,
are a step at the physical laptop. Nothing in this file should be read as
saying either happened.

---

## Where the rest of it lives

- `ec/tools/grade_0751_isolation.py` — the change, in `capture_snapshot`,
  `take_capture_row`, `mark_labels_of`, `partition_capture_rows` and
  `existing_mark_findings`.
- `ec/tools/test_grade_0751_isolation.py` — `ExistingMarkLabelTests`, where
  the four new cases sit beside #548's and #718's.
- `windows/tools/ec_watch-marks.md` — the addendum beside the #718 sentence
  that said the file is read twice.
- `docs/findings/0751-append-unchecked-marks.md` — the pointer from #718's
  addendum, whose drift table is left as it was written.
- `ec/tools/measure_mark_provenance.py` and
  `docs/findings/0751-mark-provenance-shapes.md` — the retargeted pins and the
  page they are checked against.
