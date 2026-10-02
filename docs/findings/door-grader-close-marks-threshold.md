# The door grader's close-marks threshold is the 0751 grader's window, pinned rather than derived (issue #677)

A write-up for [issue
#677](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/677), opened by the
follow-ups pass.

**Nothing below is a hardware claim.** No EC is opened, no register is read or
read back, no capture is taken, no live run backs any number here, and no
register `status:` moves. The 5 s is a judgement about human pacing transcribed
from §3's *"Hold ~30 s after each action before the closing mark"*
(`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`), not a measurement of one,
and nothing in this change moves it or claims to.

## What the issue found

`grade_gpu_door.py` decides what its report calls close marks from
`CLOSE_MARKS_SECONDS`, and the note it prints at that moment explains itself by
making a claim about a constant in *another* file — *"The 0751 grader fuses
marks this close"*, against `grade_0751_isolation.MARK_MERGE_SECONDS`. That
sentence held one number in one file and a claim about a number in another, and
nothing in the tree related them.

The case that looks as though it covers this cannot see it move.
`test_close_marks_are_flagged_and_never_fused` runs the `CLOSE_MARKS` fixture,
whose marks are 1.0 s apart: its distance assertion, its wording and its
`fan.coalesce_marks` check all hold at *any* threshold above 1.0 s. Raise
`MARK_MERGE_SECONDS` to 30 and the door's literal stays 5, the fixture still
flags and the 0751 grader still fuses — while the sentence describing that
grader's fusing has become a claim about a grader that no longer fuses at that
distance, and nothing turned red. The issue is right that this is the fixture's
spacing rather than the fixture's job, and the case is left exactly as it is.

## Why the pin, and not the derivation

Both are offered and either would have been defensible. What decides it is what
turns red when the 0751 window moves, measured rather than argued — the mutation
table below carries the runs.

- **Derive** (`CLOSE_MARKS_SECONDS = fan.MARK_MERGE_SECONDS`). The door grader's
  flag threshold then follows a three-console *fuse* window, and a decision about
  one procedure's threshold is made by editing another procedure's constant. The
  door suite does go red when the window moves, but on
  `test_close_marks_are_flagged_and_never_fused` and
  `test_a_file_boundary_is_noted_where_the_two_captures_meet`, which hold the
  note byte for byte and so break on a string that happens to embed the number.
  Nothing names the relation that moved.
- **Pin.** The same move fails one named case,
  `test_the_restated_threshold_is_the_graders_window`, which is about the
  equality itself rather than about a string carrying the number, and a human
  decides whether the threshold should follow. This is #665's direction of pin
  verbatim: the door's copy is what follows the grader, not the other way round.

There is a second, independent argument, and it is this repository's own.
`grade_0751_isolation.py`'s comment on `CLOSE_GAP_SECONDS` declines to copy the
door grader's number because *"that one equals its own window meaningfully only
because that grader does not fuse, so its number says nothing about where a
fuse came close."* Derivation binds one procedure's threshold to another
procedure's constant permanently; a pin states the equality and checks it. A
derivation deletes the possibility of the two ever disagreeing, which is a
stronger claim than the evidence supports.

**The pin accepts the derived form.** The case asserts the two constants are
equal and does not care whether the door's is a literal or an assignment, so a
later change to `CLOSE_MARKS_SECONDS = fan.MARK_MERGE_SECONDS` still passes it
and still catches the literal being re-broken. Nothing is foreclosed; today's
disagreement is made loud rather than made impossible.

**The reasoning is written above the constant as well as here**, with the pin's
case named in it, because a reader who finds the literal is going to ask why it
is not simply `fan.MARK_MERGE_SECONDS` — this file already imports the grader,
after all. The comment is where that reader is.

## What the pin is

`test_the_restated_threshold_is_the_graders_window`, in `ReportTests` of
`ec/tools/test_grade_gpu_door.py`, holding three things:

| assertion | what it holds |
|---|---|
| `door.CLOSE_MARKS_SECONDS == door.fan.MARK_MERGE_SECONDS` | the restated threshold is the grader's own constant, read through the module's existing `fan` alias — the real grader, not a third copy of the number |
| the note carries `fuses marks within {fan.MARK_MERGE_SECONDS:g}s`, read through `unwrapped()` | the sentence *explaining* the threshold is printed from the same constant the threshold is, so the two cannot drift apart in the report |
| marks exactly `CLOSE_MARKS_SECONDS` apart are flagged and marks `CLOSE_MARKS_SECONDS + 0.5` apart are not | the `<=` edge, against this file's own constant rather than a number typed into the test — it stays green when the constant moves, and goes red only if the comparison stops being `<=` at the value it prints |

The second row is the one the issue asks for that the first cannot reach. A
broken pin is now visible twice: as a named red test, and as two disagreeing
numbers in one printed note — `inside the 8s flag threshold` beside `fuses
marks within 5s` — which a reader can see without reading a test log.

Both comparisons being `<=` (`report_close_marks` here, `coalesce_marks` in the
0751 grader) and the constants being pinned equal is what makes that sentence
exact at the edge: a gap of exactly the window is inside both.

The edge case builds its captures with the suite's existing `write_capture` in a
temporary directory, rather than adding a `testdata/` fixture. It reads the
constant, so it is a property of the comparison rather than a fixture nobody
would re-time; a committed fixture would have needed a `testdata/README.md` row
and would have moved `FIXTURES`, which
`test_every_door_fixture_is_one_this_suite_runs` holds equal to the directory.

## The mutations this was checked against

A case that passes both ways is not a pin. Each of these was made in a scratch
edit and reverted; none is a committed state.

| mutation | what turns red |
|---|---|
| `MARK_MERGE_SECONDS = 30` in `grade_0751_isolation.py` | `test_the_restated_threshold_is_the_graders_window`, by name, and nothing else — the issue's *Done* criterion |
| `CLOSE_MARKS_SECONDS = 8` (the literal drifting) | the new case, and the two cases holding `are 1.0s apart, inside the 5s flag threshold` byte for byte |
| `CLOSE_MARKS_SECONDS = fan.MARK_MERGE_SECONDS` (the derivation) with `MARK_MERGE_SECONDS = 30` | the same two byte-for-byte cases, and *not* the new case — the derivation cannot fail an equality it makes true by assignment |
| the `{fan.MARK_MERGE_SECONDS:g}s` interpolation deleted from the note (the explanation drifting off the constant) | the new case |
| `gap <= CLOSE_MARKS_SECONDS` loosened to `<` | the new case, on its `5s apart` edge |

## What this does not establish

- **Nothing about the machine.** The threshold is unchanged and was never
  measured; the pin asserts a relation between two named constants, which is a
  claim about the tree and not about a laptop.
- **Not a claim that 5 s is the right fuse window.** This change makes no such
  claim either way, and `docs/findings/0751-mark-gap-report.md` and
  `docs/findings/probe-hold-mark-merge.md` both already declined changing it:
  5 s is the 0751 grader's own value for its own three-console procedure.
- **The corner the derivation would have removed is still open, and the pin
  does not close it — it watches it.** `CLOSE_GAP_SECONDS`'s comment declines
  the door grader's number *because* that number means a window only because
  the door grader does not fuse. Set `MARK_MERGE_SECONDS` to exactly
  `CLOSE_GAP_SECONDS` and that reasoning stops being true for the door grader's
  copy too. Under the pin this now reddens a suite before such a change can
  land quietly; nothing here edits that file, and its comment stays accurate
  as written.
- **The constants are equal; the procedures are not interchangeable.** The pin
  asserts a number, and says nothing about whether the door grader should fuse
  or whether the two graders could be merged. They cannot: §3 of the 0751
  procedure runs one watcher per console and §3 of the door procedure runs one
  watcher on one console, which is what `grade_gpu_door.py`'s module docstring
  argues and what `report_close_marks` fuses nothing to preserve.

## Left out on purpose

- **Deriving the threshold instead of pinning it.** A one-line change the pin
  already accepts; not taken here, because it leaves nothing asserting the
  relation, so what a moved window turns red is a string rather than the
  equality.
- **Making the door grader fuse, or merging the two graders.** The issue
  forbids it and the module docstring argues the distinction; the door's §3 is
  "mark, act, hold, mark" on one console, and fusing would attribute the second
  action's movement to the first.
- **`ec/tools/grade_0751_isolation.py`.** Not one line of it, including its
  `CLOSE_GAP_SECONDS` comment. The pin's other end is the thing that is *not*
  edited, and issue #169 is open on that file, so an edit from here would
  collide for no gain.
- **A `testdata/` fixture, or re-timing the committed one.** The committed
  fixture's 1.0 s spacing cannot tell the number moved, and re-timing it to
  match the constant would make a fixture that can no longer fail; the `<=` edge
  is pinned against the constant itself, which is the property worth holding.
- **`tools/README.md`, `ec/tools/testdata/README.md`, and
  `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`.** Nothing in any of them
  becomes false — the fixture row already says the pair is 1.0 s apart *"inside
  `grade_0751_isolation.py`'s `MARK_MERGE_SECONDS`"*, which stays true at any
  value above 1.0 s — and all three are long shared files another change is
  likely to be editing.
- **`windows/tools/test_manual_fan_ctrl_probe.py`.** #665's pin is already
  there, as `test_the_restated_window_is_the_graders`. The door's is a parallel
  case rather than a shared one: each suite asserts its own copy against the
  grader, and neither reaches into the other.
- **`ec/annotations/registers.yaml`, the annotation CSVs, and every
  decompile.** Tool-side only; no register `status:` moves, which is true and is
  what the issue says.
- **A sweep of the tree for other restated grader constants.** Plausible that
  there are more — this one was found by a follow-up pass rather than by a scan
  — but a census is a finding nobody asked for, and putting a shared-file sweep
  in a change this small would collide for nothing. It is its own issue if it is
  wanted.

## Corrections to the issue as filed

Recorded here rather than left to be repeated, and neither is a disagreement
about the work:

- **The pin this follows is #665's, not #667's.** The issue's footer names
  #667, but the probe's pin — `test_the_restated_window_is_the_graders` in
  `windows/tools/test_manual_fan_ctrl_probe.py` — is #665's, and
  `docs/findings/probe-hold-mark-merge.md` is its write-up. #667 appears nowhere
  in the tree. `docs/findings/0751-mark-gap-report.md` recorded the same
  correction for the same mis-citation.
- **The line numbers are stale.** The issue's `:128`, `:281` and `:283-291` do
  not land on the symbols they name. Everything above is cited by symbol name
  instead, per CLAUDE.md's "cite code by name, not by line number" — a bare
  `file:NNN` in prose is true only until the next merge grows the file above it.
  The symbols are `CLOSE_MARKS_SECONDS`, `report_close_marks` and
  `coalesce_marks`.

## One committed pin re-anchored, as a consequence

`measure_mark_provenance.py` names every site its own write-up rests on as a
`(path, line, quoted text)` triple, and
`test_measure_mark_provenance_citations.py` re-reads each one and fails if the
line no longer carries the quoted text. One of them pinned the second consumer
of `read_capture`'s two-tuple, the line carrying
`m, c = fan.read_capture(path)`; the comment above `CLOSE_MARKS_SECONDS` grew
above it here, so that pin is re-anchored. The text it quotes and the claim it
makes are both unchanged, and
`docs/findings/0762-provenance-citation-reanchor.md` describes the
re-anchoring.

**Those comment lines are not the only reason the line moved.** `main` grew
`grade_gpu_door.py` above it independently, so this change is rebased onto
`main` and the pin is anchored against the merged tree rather than against this
branch's own base — anchored against the base, it would resolve here and point at
nothing once the two met. The other half of a re-anchor is the page:
`0751-mark-provenance-shapes.md`'s live table carries the new number, which is
what `check_page` reads, and without it the tool reports the citation as one the
two findings pages do not name.