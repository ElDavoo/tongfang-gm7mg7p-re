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
