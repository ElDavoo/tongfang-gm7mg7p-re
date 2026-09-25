# `--label-vocab` checks a label as it is typed, a `--csv` is graded whole, and only one of those is per-process (issue #548)

The write-up for [issue
#548](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/548). Issue #531
gave `ec_watch.py` a check on the mark label as it is typed, and
`windows/tools/ec_watch-marks.md` states the promise in terms of a capture:
*"A capture taken under a promise the tool silently did not keep is #502's
failure caught a step later rather than a step earlier."* The code delivers a
narrower one, and the gap is between a process and a file. This is a change to
what a tool says at startup, not to what it can read. Nothing here is evidence
about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §3 is the block and
§6 the file set and the labels.

---

## The reach, as the code stood

`Marker._loop` checks each label where it is typed
(`windows/tools/ec_watch.py:337`), and that check is the whole of the #531
promise. It is a per-process fact, and everything around it is per-file:

- `CsvSink.__init__` opens `open(path, "a", newline="")` (`:126`) and never
  reads what is already there. It writes a header only when `tell() == 0`, so
  a file that exists with nothing in it is left without a header, and a file
  that exists with rows in it is appended to unconditionally.
- `unplaceable_marks` (`ec/tools/grade_0751_isolation.py:1025`) is fatal for
  the whole run, and `read_capture` (`:678`) reads whatever the file holds —
  all of it, not this run's share.
- `Marker._n` counts marks *this* process recorded (`ec_watch.py:306`), and
  the console numbers the operator reads come from it.

So a CSV already carrying an unchecked mark keeps it, and the run is still
refused whole after the day, from a prompt that said every label was fine. The
four ways a file comes to hold a mark no watcher checked:

1. a run taken before `--label-vocab` existed;
2. a console started without the flag — the three §3 watchers are three
   separate processes, and nothing forces the flag on all three;
3. a watcher restarted mid-block, appending into the file the first one left;
4. a `manual_fan_ctrl_probe.py` capture, which writes the same
   `ts,MARK,,label` row (`windows/tools/manual_fan_ctrl_probe.py:433-438`) and
   is only a *source* of a mark in somebody else's file.

§3a's service-stopped pass is not a fifth: it is a second run with its own
`<date>`, not a fourth block of §3's
(`manual-fan-ctrl-0751-isolation.md:904-907`), so a §3a pass on a fresh date
writes three new files and starts on empty ones. It is the one routine that
correctly *avoids* the collision, which is why the notice stays quiet for it.

And the runbook makes the collision ordinary rather than exotic, which is what
decides the fix. §3's own note
(`manual-fan-ctrl-0751-isolation.md:116-119`) is that the three CSVs are **one
file for all three blocks**, "because ec_watch.py appends to a --csv file that
already exists", and §6 says the same at `:713`. Blocks 2 and 3 are *supposed*
to find marks already there. The collision is the procedure.

### The issue's line numbers have drifted

Recorded rather than papered over, because a write-up that silently retargets
a citation reads as though the issue was checked and turned out to be wrong
about something that never mattered. Measured against the tree this change
starts from — the numbers above are the tree this change leaves *after #548
and #549 are both merged*, and they differ because the two of them insert code
above some of them:

| issue says | it is actually | in the tree this change starts from |
|---|---|---|
| `unplaceable_marks` at `:688` | `:688` is inside `read_capture` | `:986` |
| the check at `:195` | `:195` is `flush=True)` on the blank-press notice | `:197` |
| `CsvSink`'s `open` at `:95` | | `:95` |
| the probe's mark rows at `:225-252` | `:225-252` is `arm_labels` | `:433-438` |

Every other citation in this file and in the pull request is from the tree the
change leaves, except the citations quoted in this table, which are against the
tree the change starts from as its third column says. The ones that move are
the check `ec_watch.py:197` at base (`:337` at head), `CsvSink`'s `open` at
`:95` at base (`:126` at head), `load_label_vocab` at `:115` at base
(`:179` at head), `Marker._n` at `:166` at base (`:306` at head), and
`grade_0751_isolation.py:986-1006` at base (`:1025-1047` at head).

*Measured after the merge.* #548's own head carried `:259` for the check and
`:228` for `Marker._n` — eight low, because `warn_unchecked_marks`'s docstring
grew after they were written — and `:1015` for `unplaceable_marks`, ten low
for the same reason in the grader. Merging #549 moved every one of them again,
and the numbers here are the merged tree's. Nothing about the finding changed;
only the line the reader has to open.

## The decision

**The loud warning, not the refusal.** The issue offered both and said pick
one, and the runbook is what decides it: refusing a non-empty existing CSV
would refuse §3's own second block, which is that CSV. The tool would refuse
the procedure it documents.

The tool also *cannot know* whether the marks already in the file were checked.
Block 1's were — same flag. A pre-flag run's were not. A probe's never were
eligible. A process cannot see a file's past, and a warning that states the
boundary is the only honest answer available to one. What it does not do is
pretend to a stronger check than it has: it does not re-run `parse_mark` over
what it finds, because a label that parses is not the question — §3's
three-console comparison is, and a file that passes this preflight can still
be refused at the grading.

### The predicate: "already holds MARK rows", not "is not empty"

This is the tightening, and it is what makes the notice worth reading. A file
holding only a header, or only change rows, carries no unchecked label: a
change row is not a label, opens no block, and is not something any process
could have checked against §3's forms. §3's block-1 start legitimately appends
to exactly that and has to stay quiet. A predicate of `st_size` warns on a
fresh run's second console, which teaches the operator to skip the line.

Keying on the mark row is also what keeps the notice *informative*: a file that
holds two marks is a file whose block structure the grader will read, and the
labels are the only thing that says which block a window is a window of. That
is the same reason `unplaceable_marks` is fatal for the whole run rather than
one block.

### Left out on purpose: a suppression flag

A flag to silence it would be a way to wave through a collision the tool
provably cannot verify, and the cost of the notice is one line at the top of a
four-minute run — before the operator has typed a mark or spent a mark number.
Noted on the record so a later reader meets the argument rather than
re-deriving it and adding one by reflex.

## Two details that decide the shape

1. **The reader lives in the grader, not in `ec_watch.py`.** A mark row's
   shape and the skip rule are the grader's, and `load_label_vocab` exists
   precisely so the prompt carries no second copy that could drift from the
   thing that enforces it. `grade_gpu_door.py:421` and
   `manual_fan_ctrl_probe.py:697` already import this module's readers, so the
   arrangement is established rather than new. The new
   `existing_mark_labels` (`:700`) rides on the load `load_label_vocab` was
   already making, as a third return value.
2. **The timestamp stays text, and the reader does not raise on the content.**
   `read_capture` may raise — a short row, a `parse_ts` that cannot read a
   hand-edited timestamp, a byte the encoding cannot decode — and that is right
   for a capture that is going to be graded. It is wrong for a preflight:
   refusing to open a file would be the worst possible way to lose the one
   warning that says what is already in it. A capture that appends to a file
   works whether or not that file is one this grader could load, and the notice
   has to be printed in both cases. So the timestamp is returned as written, a
   truncated mark row comes back with an empty label, a change row is not
   parsed at all, and the read is `errors="replace"` — `CsvSink` appends to the
   same path without ever decoding it, so the bytes are whatever the writing
   process's locale wrote, and a lone 0xE9 would otherwise take the run down
   at startup on a file the run was about to append to perfectly well.

`unplaceable_marks`, `build_windows` and the exit code are unchanged. The
grader's refusal is correct and stays: block attribution rests entirely on the
labels, and forgiving the pre-existing marks would need the grader to know
which process wrote each one, which is not in the file.

## Files

**New**

- `docs/findings/0751-append-unchecked-marks.md` — this file.

**Shared**

- `ec/tools/grade_0751_isolation.py` — one new read-only function,
  `existing_mark_labels(path)`, placed directly after `read_capture`. Nothing
  existing changed.
- `windows/tools/ec_watch.py` — `load_label_vocab` returns the reader as a
  third value; the new `warn_unchecked_marks`; the startup check beside the
  refusals above it, before `CsvSink` (`:422`) and before `Ec` (`:434`);
  a module-docstring paragraph after the `--label-vocab` one, one usage line,
  and the `--label-vocab` help text.
- `windows/tools/test_ec_watch.py` — `AppendNoticeTests`, beside
  `RefusedLabelTests`, on that class's `FakeEc`/`FakeStdin`/`run_watch` shape.
- `ec/tools/test_grade_0751_isolation.py` — `ExistingMarkLabelTests`, beside
  `EarlyExitTests` (the other second-reader suite). Not a `MarkSetTests` case:
  that class is about block marks, and this reader is about a file's past.
- `windows/tools/ec_watch-marks.md` — a new section after *The refused label*,
  a paragraph in *The counting rule*, and two **dated corrections left in
  place** on the two sentences that read as a whole-capture promise.
- `docs/findings.md` — one dated paragraph and a link inside §16a, which
  already carries the #474 and #531 entries in that form. This file has no TOC;
  the inline link is the whole pointer convention.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` — two small dated
  additions, at §3's rem block (`:116-119`) and §6's one-set paragraph
  (`:713`), because that is the document which *mandates* the collision.

**Deliberately not touched**

- `windows/tools/manual_fan_ctrl_probe.py` — its marks come from `arm_labels`
  (§3's forms by construction) and it never runs `--label-vocab`. It is a
  source of a mark in someone else's file, which the new notice catches; it is
  not a file the notice would catch anything in.
- `windows/tools/system_id_probe.py:252` and `ec/tools/ec_timer_capture.py:162`
  — the same `strip() or` shape, already named as open in #483/#484 and in
  `ec_watch-marks.md`, and a different tool.
- `ec/annotations/registers.yaml` and the annotation CSVs — no register's
  status changes and no Ghidra annotation is involved.
- `evidence/` — no capture is added. The run is a human's.
- `.github/` — the token has no `workflow` scope, so no gate is added. The new
  cases run under the existing `tools/run-tests.sh` invocation.

## What is pinned

`bash tools/run-tests.sh windows/tools` and, from `ec/tools`,
`python3 -m unittest test_grade_0751_isolation`. Both offline, both on fakes;
no EC, no driver. `windows/tools/test_ec_watch.py` goes 21 tests to 29 and
`ec/tools/test_grade_0751_isolation.py` goes 88 to 92.

| test | what it holds |
|---|---|
| `test_a_file_already_holding_a_mark_is_named_at_startup` | the notice names the path, the count and the labels, once |
| `test_the_notice_is_above_the_file_and_the_ec_and_the_append_still_happens` | the notice precedes the baseline line (so it precedes `Ec()`), exit 0, and the pre-existing mark is still the first MARK row with this run's after it |
| `test_a_fresh_path_and_a_header_only_file_are_quiet` | §3's block-1 start, both forms, says nothing — and the header is not doubled |
| `test_a_file_of_change_rows_is_quiet` | the predicate is "holds marks", not "is not empty"; the fixture really does hold a row |
| `test_the_notice_says_what_was_not_checked_and_what_still_holds_the_day` | both halves, as separate assertions: not checked, and the file is graded whole |
| `test_the_files_marks_and_this_runs_counter_are_two_sequences` | two marks already in the file are named, a refused label still reads `no mark 1 taken`, and the file ends up with all three |
| `test_without_the_vocabulary_a_non_empty_file_says_nothing` | `gpu_block_watch.py` and every other append-only caller stay silent, and a free-form label is still recorded |
| `test_the_reader_is_the_graders_own` | `load_label_vocab` hands back the grader's function — asserted on `__module__`, the shape `test_manual_fan_ctrl_probe.py:905` uses for `read_capture`, and then on what it does |
| `ExistingMarkLabelTests.test_the_skip_rule_is_read_captures_and_only_marks_come_back` | `#`, blank and `ts` header skipped; change rows are not marks |
| `...test_a_row_read_capture_would_raise_on_comes_back_as_a_label` | a hand-edited timestamp and a truncated mark row come back rather than raising, and `read_capture` raises on that same file — the difference is the point |
| `...test_a_file_with_no_marks_comes_back_empty` | the quiet side, from the grader's side |
| `...test_read_capture_is_unchanged` | the reader is additive: `read_capture` still skips the same rows, returns `(marks, changes)` and still raises |

One placement note, so a reader does not go looking for it in the wrong
suite: the `__module__` assertion is in `test_ec_watch.py`, not in the grader's
own. That file loads the module as `grade_0751_isolation` — the name
`ec_watch.py` loads it under — so the assertion there is load-bearing. In
`test_grade_0751_isolation.py` the same module is loaded as `grade`, and the
identical assertion would pass for any function in sight.

## None of this is a live test.

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is offline behaviour of a tool against a fake EC and hand-written
CSV rows: no register was read, no capture was taken, no `registers.yaml`
`status:` moved, and the notice has not been seen against a real §3 run. What
it moves is where the operator finds out — at the top of a run they can still
stop, rather than a day later as a withheld run with no remedy. Running §3, or
§3a, at the machine is a human's step and stays one.

---

# Addendum, 2026-09-25 (issue #718): the notice names two lists, and the reasons are the grader's

The finding above is #548. This is the same notice, refined, and it is an
addendum rather than a second file because it is not a new investigation: it is
the same tool, the same file, and the same finding. What changes is that the
notice stopped being one list.

## The line numbers moved again, and the drift is one-sided

The table in *The issue's line numbers have drifted* above is left as it was
written, because it is a record of what was true at the time and editing it
would make it a record of nothing. This is the same measurement taken again, for
the same reason: a citation that silently retargets reads as though the issue
had been checked and found wrong about something that never mattered.

#718's insertion is a single block placed after `existing_mark_labels` and
directly above `read_early_exits`, which makes the drift **one-sided** — every
citation at or above that point is unmoved, and everything below it moves by
exactly 163 lines. That is a consequence of choosing the insertion point for
merge-conflict cost and then measuring, not the other way round.

| cited as | at the tree #718 starts from | in the tree #718 leaves |
|---|---|---|
| `read_capture`, `parse_ts`, `:690`, `MARK_MERGE_SECONDS` | `:678`, `:674`, `:690`, `:274` | **the same** — unmoved |
| `existing_mark_labels` | `:700` | **`:700`** — unmoved |
| `read_early_exits` | `:739` | `:902` |
| `coalesce_marks` | `:822` | `:985` |
| `build_windows` | `:854` | `:1017` |
| `parse_mark` | `:897` | `:1060` |
| `assign_blocks` | `:940` | `:1103` |
| `unplaceable_marks` | `:1025` | `:1188` |
| `ec_watch.py`: `load_label_vocab`, `warn_unchecked_marks` | `:179`, `:254` | `:185`, `:276` |

`ec_watch.py` is the one row where the drift is *not* uniform, and the table's
own two numbers are what say so. `load_label_vocab` moved down by six and
`warn_unchecked_marks` by twenty-two, both because the module docstring above
them grew; the second moves further only because its own body grew below
`load_label_vocab`'s. So the one-sided claim is about
`grade_0751_isolation.py`, where the insertion is a single block, and not
about the tree as a whole. Every citation in this addendum is from the tree the
change leaves, except the third column above, which is against the tree it
starts from as the column says.

## What the notice could not say

`existing_mark_labels` is deliberately the lenient reader, and the notice
printed everything it returned. On a file of six good marks and one
half-written row that is seven lines that all read the same, and a closing
sentence that is true and is the only warning — so an operator starting §3's
block 2 could be told there was a risk and could not tell which of the seven
rows it was. The preflight had just read the file, and the thing that decides
is the grader's own reader; the notice was written entirely on the preflight's
side of that disagreement.

`unplaceable_marks` was in the same position from the other end. The issue
called a bad label "fatal only when it leads its group", which describes the
symptom and not the mechanism: `coalesce_marks` joins the consoles' labels
with `' / '` and `parse_mark` returns on the first part whose leading word
matches one of §6's forms, so a group is fatal when *no* part matches one —
and equally when the first part that does match is an action form whose value
does not parse, which is a hand-edited `wrote 0x0751` with the `=0xA0` dropped
off. The rest of the group is never tried, so a second console's `settled`
rescues neither. A window led by `settled` places over a second console's
unparseable label. Neither the phrasing nor a per-label test went into the
code; the notice reports what `unplaceable_marks` returned.

## Two readings taken, and why

**The refused list covers every row that makes the file ungradable, not the
two the issue names.** The issue lists `len(row) < 4` at `:690` and `parse_ts`
on a hand-edited timestamp. `read_capture` also raises out of
`int(addr, 16)` / `int(old, 16)` / `int(new, 16)` on a malformed *change* row.
A notice that stopped at the two named reasons would report a file as checked
when the grading refuses it over the whole run. The widening is pinned by
`test_a_malformed_change_row_is_a_refused_row_too` and by the same case at the
prompt in `AppendNoticeTests`, so it is a decision on the record rather than
something a later reader has to infer from the code.

**All refused rows, not only the first.** `read_capture` stops at the first
bad row, so its own exception names one — and its text is quoted verbatim as
the reason for that row, which is the error the grading will raise. The
per-row conditions in `refused_capture_rows` then name the rest, so a file
holding more than one bad row after a half-finished write or a hand edit is a
list an operator can work down rather than a fix-one-re-run-meet-the-next
loop.

The two are held together by one test.
`test_the_refusal_reasons_are_read_captures_own` runs seven fixtures and
asserts that the first reason returned is the exception `read_capture` itself
raised, byte for byte. It is load-bearing, not decorative: dropping the
`parse_ts` check from the partition fails it. So does reordering it so a change
row's hex is read before its timestamp — the opposite of `read_capture`'s
order. That second one needs its own fixture to be visible at all, and the
shape of it is the whole point: `existing_mark_findings` replaces the *first*
row's reason with `read_capture`'s own exception, so a fixture whose only bad
row is the first one cannot see which check ran first, and six of these seven
could not. The seventh is a change row bad in both ways that is deliberately
**not** the first bad row, and the assertion is on that later row's reason —
the one the exception does not replace. Both mutations above were run against
the committed code in both directions: each fails the seventh fixture, and the
committed code passes all seven. That is what makes re-applying the conditions
beside `:689-696` a borrowed rule rather than a second one.

The order *among* the three `int()` calls is a different matter and is not
claimed anywhere: every fixture that reaches them has exactly one bad field, so
reordering those three would change no reason any fixture can see.
`read_capture` evaluates them left to right, this copies that, and neither the
test nor this addendum pretends the copy is held to it.

The three refusal messages the notice can quote, as `read_capture` actually
raises them, measured against this tree:

```
<path>: short row ['2026-01-01T12:01:00.000+01:00', 'MARK', '']
Invalid isoformat string: 'when i clicked'
invalid literal for int() with base 16: '0xzz'
```

Only the first names the row. `parse_ts` names the timestamp and `int()` names
the value, so for those two the notice pairs the exception with the row beside
it rather than expecting the exception to carry the row — which is why the
`ec_watch.py` case compares the sentence after the path rather than the whole
message, and why the prompt quotes a message that leads with a path it has
already printed on its own first line.

## What the notice says now, and what it still cannot

Three sections, in the reading order: the mark rows the strict reader takes;
the rows it will refuse the file over, each with its reason and the immediate
remedy; and what the grader's placement pass cannot place, in
`unplaceable_marks`'s own words. The counts are per list and never one total —
a file of two good marks and one short row reads "2 mark(s)" and "1 row(s)" —
and a file the grader takes whole reads exactly as it did in #548, byte for
byte.

Still a warning. `unplaced_window_problems`, the cross-console checks and the
block checks are outside it, and the notice says so: it is a preflight and not
a second grader, and a file it reports as clean can still be refused at the
grading, because the check that refuses it compares blocks and this looks at
one file. `read_capture`, `existing_mark_labels`, `coalesce_marks`,
`assign_blocks`, `unplaceable_marks`, `build_windows`, `main` and the exit code
are all unchanged. `test_read_capture_is_unchanged` is kept as it was and still
passes, and the change is additive — nothing existing was edited to make it
work.

A refused file reports no placement verdict and says so in one line, because a
label verdict needs a file the grader can read and one it cannot read is
already refused whole. The silence is called out rather than left to read as
"the labels are fine".

## The encoding question, measured rather than assumed

`read_capture` opens with `open(path, newline="")` and no `encoding=`, so it
decodes in the running interpreter's preferred encoding. **Measured**, under
the gate's Python 3.12 on ubuntu:

| interpreter's default | the 0xE9 at `test_grade_0751_isolation.py`'s byte fixture | what the notice says |
|---|---|---|
| UTF-8 (this tree's gate) | `UnicodeDecodeError` out of the loop | a file-level refusal, no row, the encoding named |
| cp1252 (**predicted** from the documented Windows default, not observed) | reads as `café` | the mark is accepted; no decode failure is claimed |

So the notice reports the verdict the interpreter it is running under actually
produced and names the encoding it produced it under. It never predicts another
interpreter's answer, and a mark that read comes back accepted rather than with
an invented failure. `test_a_byte_this_python_cannot_decode_reports_the_verdict_it_observed`
accepts either column and fails only if a failure is claimed where none
happened.

The consequence is worth writing down because it is a fact about two
interpreters rather than about a machine: **the grader is not
encoding-portable.** The same capture can be gradeable on the box it was taken
on and refused when it is brought back to a machine whose default differs. §6
grades the file set wherever it is graded, and the bytes `CsvSink` appended are
whatever the writing process's locale wrote, so which interpreter reads the
file is part of what the file means. This is a statement derived from two
measured/predicted interpreter behaviours, **not** an observation of a Windows
box. Confirming what a stock Windows Python 3.12 does with 0xE9 is a human's
step and the design does not wait for it.

## The encoding named is the one the interpreter used

`f.encoding`, read off the same `open` call `read_capture` makes, rather than a
re-derivation of which locale rule CPython applies. It cannot disagree with the
reader, where `locale.getpreferredencoding(False)` could in principle. The
assertion is against the codec name in the `UnicodeDecodeError` itself
(`e.encoding`), so the test is asking "did it name the encoding that actually
raised" and not "does it name the thing this function computes".

## A staged grader that goes stale

`load_label_vocab` now reads four names off the grader and the fourth is new,
so a copy staged beside `ec_watch.py` before #718 is a working grader that is
not a usable one. The four reads were outside the `try` that guards the load,
which made that a bare `AttributeError` naming the attribute and not the file —
and a staged tools directory holds a copy rather than a checkout to pull, so
the file is the actionable half. They are inside the `try` now, and the refusal
is the documented "there and will not load" one, naming the path. This is the
same argument #549 made for a grader that does not load, applied to one that
loads and is behind.

## Files

**New** — none. A new tool module would put a second copy of the mark-row shape
and the label predicate in the tree, which is the drift `load_label_vocab`
exists to prevent.

**Shared**

- `ec/tools/grade_0751_isolation.py` — **two** new read-only functions beside
  `existing_mark_labels` (`refused_capture_rows` and
  `existing_mark_findings`), one contiguous insertion directly above
  `read_early_exits`. Two rather than the one the plan expected: the partition
  is a loop with four checks in it, and inlining it would have put a
  seventy-line body inside the function that is supposed to be readable as a
  contract. Both are in the enforcing module, which is the point.
- `windows/tools/ec_watch.py` — four tight edits: `load_label_vocab` returns a
  fourth value and reads it inside the `try`; `warn_unchecked_marks` prints
  the split; the module-docstring paragraph and the `--label-vocab` help text.
- `ec/tools/test_grade_0751_isolation.py` — new cases in
  `ExistingMarkLabelTests`, beside the existing ones.
- `windows/tools/test_ec_watch.py` — new cases in `AppendNoticeTests`, one in
  `RefusedLabelTests`, plus `write_stub` and the two unpack sites.
- `windows/tools/ec_watch-marks.md` — the notice block re-rendered from the
  tool, the new sections, and **two dated corrections left in place** on
  sentences this change made incomplete.
- `docs/findings.md` — one dated paragraph in §16a.

**Deliberately not touched** — `ec/annotations/registers.yaml`, the annotation
CSVs, `ec/ghidra/**`, `windows/decompiled/**`, `evidence/**`, `vendor/**`,
`.github/**`, and `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`. That
runbook already points at `ec_watch-marks.md` for this at `:127` and `:280`,
and the issue's Done list does not name it; a reviewer who wants a line there
should say so rather than have it added silently. No register's `status:`
moved, no Ghidra project was involved, and no capture is added.

## What is pinned

`bash tools/run-tests.sh windows/tools` (46 cases in `test_ec_watch.py`, 7 of
them new) and, from `ec/tools`, `python3 -m unittest
test_grade_0751_isolation` (102, 8 new). Both offline, both on fakes; no EC, no
driver, no Windows box. `python3 ec/tools/grade_0751_isolation.py --self-test`
discovers the suite by filename, so the new cases are picked up with no gate
edit, and the count it prints decorates rather than decides. No test count is
pinned anywhere: `tools/test_readme_suite_table.py` compares the *set* of suite
files, and no suite file was added.

| test | what it holds |
|---|---|
| `...test_the_strict_readers_verdict_splits_the_marks_a_file_holds` | the issue's shape: six accepted, one refused, the row named |
| `...test_a_hand_edited_timestamp_is_a_refused_row_and_is_named` | a timestamp `parse_ts` genuinely rejects, and the exception quoted |
| `...test_the_refusal_reasons_are_read_captures_own` | the anti-drift guard, over seven fixtures, including two that pin the order of the checks |
| `...test_a_malformed_change_row_is_a_refused_row_too` | the widening past the issue's two named reasons |
| `...test_an_unplaceable_label_is_reported_from_the_graders_own_verdict` | the grader's message, and the `settled`/`garbage` group *not* reported |
| `...test_the_preflight_does_not_raise_on_any_of_them` | every hostile fixture, through both readers, nothing escapes |
| `...test_a_byte_this_python_cannot_decode_reports_the_verdict_it_observed` | either interpreter's verdict; fails only on a claimed failure that did not happen |
| `...test_on_a_file_the_strict_reader_accepts_the_two_readers_agree` | the clean file is unchanged, so #548's notice still reads as it did |
| `...test_a_file_with_no_marks_comes_back_empty` | the quiet side, from the new function too |
| `...test_read_capture_is_unchanged` | kept as it was; the reader is additive |
| `test_the_notice_splits_the_marks_it_takes_from_the_rows_it_refuses` | both sections end to end, the two counts, the verbatim reason, the remedy |
| `...test_the_notice_names_an_unplaceable_mark_from_the_graders_own_verdict` | the placement section, the group wording, the grader's message |
| `...test_a_file_the_notice_can_read_still_reads_as_one_count` | the clean notice is unchanged and the closing paragraph is verbatim |
| `...test_a_file_with_a_bad_row_still_prints_a_notice_rather_than_raising` | end to end through `main`, `rc == 0`, no traceback, the row still in the file |
| `...test_the_counts_are_two_lists_and_not_one_total` | two marks and one refused change row read "2" and "1" |
| `...test_a_refusal_of_the_file_itself_names_no_row_to_fix` | the encoding case: no row to edit, so no "fix the row" advice; and no failure claimed where none happened |
| `...test_a_grader_that_loads_and_lacks_a_name_is_refused_by_path` | the loads-but-lacks-a-name refusal, by path |
| `...test_the_reader_is_the_graders_own` | `__module__` on both readers, and the second's output on a real file |

A note on where the anti-drift assertion lives, because it is not where a
reader would look: the `__module__` checks are in `test_ec_watch.py`, not in
the grader's own suite. That file loads the module as
`grade_0751_isolation` — the name `ec_watch.py` loads it under — so the
assertion there is load-bearing. In `test_grade_0751_isolation.py` the same
module is loaded as `grade`, and the identical assertion would pass for any
function in sight.

## None of this is a live test either

Same as above and for the same reason: no EC, no laptop, no Windows box. Every
figure in this addendum is offline behaviour of a tool against a fake EC and
hand-written CSV rows under one interpreter. The two things a human at the
machine would add are whether a stock Windows Python 3.12 reads the 0xE9 (a
prediction, labelled as one) and what the notice looks like at the top of a
real §3 block 2. Neither is needed for the change to be right, because the
notice reports the verdict it observed.
