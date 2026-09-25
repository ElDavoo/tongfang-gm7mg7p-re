# §3's three unlabelled mark rounds were a fourth class of mark, and the block model had no place for them (issue #472)

The write-up for [issue
#472](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/472): §3's command
block asks for **six** mark rounds per block and the grader could read three
of them, so a capture taken exactly as the runbook prints is refused. This is
a change to what the tool can read, not to what it says about a register.
Nothing here is evidence about the machine.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §3 is the block and
§6 the file set and the labels.

---

## The reach, as the code stood

`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md:121-131` asks for six
rounds: mark after the settle, mark the no-op write, mark after the hold, mark
the write under test, "mark again at the end" of the ~60 s watch, and mark the
restore. Its own `--seconds 240` paragraph says so in as many words —
*"six mark rounds typed by hand across three consoles, which is eighteen
presses"* — so six was the intent and three was what the tool could read.

`parse_mark` matched a leading word only when it was followed by a space,
because all three forms it knew had to be followed by `0x0751=…`:

```python
        for role, word in MARK_FORMS:
            if not part.startswith(word + " "):
                continue
            m = MARK_VALUE.search(part)
            return (role, int(m.group(1), 16)) if m else (None, None)
    return None, None
```

A stage round is typed as the bare word, so it fell through to `(None, None)`,
`assign_blocks` filed it under `unplaced`, and `unplaceable_marks` — which is
fatal for the whole run, because an unreadable label could have been a `write`
and so can change which blocks there are at all — turned the exit code to 1.

Measured, on the committed fixture this change adds
(`ec/tools/testdata/0751-isolation-run-staged/`), against
`git show origin/main:ec/tools/grade_0751_isolation.py`:

```
    python3 ec/tools/grade_0751_isolation.py ec/tools/testdata/0751-isolation-run-staged/*.csv
```

```
  2026-01-01-0751-isolation-0700-07ff.csv at 2026-01-01 12:00:10+01:00: 'settled' is not one of the three forms §6 fixes (...)
  2026-01-01-0751-isolation-0700-07ff.csv at 2026-01-01 12:01:10+01:00: 'held' is not one of the three forms §6 fixes (...)
  2026-01-01-0751-isolation-0700-07ff.csv at 2026-01-01 12:02:40+01:00: 'watch over' is not one of the three forms §6 fixes (...)
```

and, at the end of the run:

```
  6 of the 12 window(s) above were not graded: ...
  None of the §4.1-§4.3 bytes moved in any of the 6 window(s) that were graded: ... this output does not make it over a run it only read part of ...
```

Exit **1**. The three action rounds in each block still place, so the day is
half graded rather than wholly refused — but §4.4's control-vs-write
comparison is taken over windows whose boundaries the operator set and the
grader could not honour, and the run is not the one the runbook describes.

## The decision

**A stage round is a fourth class of mark: a stage boundary — a mark that
closes one window and opens the next without being a write.** Three leading
words are added, each naming a stage and carrying no `0x0751=` value:

| label | role | where §3 types it |
|---|---|---|
| `settled` | `settle` | after the ~10 s settle, before the control arm |
| `held` | `hold` | after the ~30 s hold, before the write under test |
| `watch over` | `watch` | at the end of the ~60 s watch, before the restore |

A boundary joins the block the control arm opens, or waits for the next `write`
if none is open — which is the discipline `control` already used, and the
reason a boundary typed between two blocks does not join the first one. A block
therefore reads

```
    value under test 0xA0; roles settle, control, hold, write, watch, restore
```

and `--block 0xA0` selects six of that block's windows rather than the three an
older capture of the same block carries.

### The three options, and why this one

The issue offered three: additional roles, additional forms in
`REQUIRED_LABEL_FORMS`, or a way to mark a stage without opening an addressable
action. The first two are the same change seen from two sides and were taken
together — a role per boundary **is** a form per boundary, and
`REQUIRED_LABEL_FORMS` is what the refusal message and the `ec_watch.py` mark
prompt quote, so a role that is not in the tuple is a form the operator cannot
see the spelling of. The third was declined: a stage round still has to appear
in the capture as a row, and a label the parse cannot read is a window the
grader cannot say what it is a window of, which is the defect the whole check
exists to stop. Making a boundary a *different kind of row* would have made it
invisible to the agreement checks that make a three-console run worth taking.

### Why boundaries are optional

A three-mark capture still grades exactly as it did. This is the load-bearing
scoping choice, and it is what keeps every existing fixture under
`ec/tools/testdata/0751-isolation-run-*/` — and the probe's own two-mark
capture, `windows/tools/manual_fan_ctrl_probe.py`, which emits only `no-op
wrote …` and `wrote …` — behaving unchanged. It is also the narrowest reading
that delivers the issue's bar: *the §3 block as printed produces a capture the
grader grades rather than refuses*.

*(**Correction, 2026-09-25, issue #476.** The paragraph above is kept as it was
written, and its clause about the probe no longer describes the tool. The
probe writes a third mark — `restored 0x0751=…`, §3's step 5 — so a capture it
writes is `no-op wrote …`, `wrote …`, `restored …` rather than the two forms
quoted, and the real `ec/tools/grade_0751_isolation.py` reads that capture as
one `intact` block, roles `control, write, restore`, every window printed,
exit 0 — where the same run's two-mark capture, which is the shape the tool
used to write, comes back `VOID` with its windows withheld. The grading tool
is not what changed here; the capture is. The scoping choice this section
defends is untouched and this change confirms it rather than disturbs it:
boundaries are still optional, a capture carrying the three action marks
still grades exactly as it did, and the `0751-isolation-run-*/` fixtures
grade as they always have. What moved is the shape the probe *emits*, and its
third mark is a restore rather than a stage boundary — which is #476's
business, not #472's.)*

What it costs is stated in §3 rather than checked. A window is every change
after a mark up to the next one, so the end-of-watch mark is what closes the
write's ~60 s observation window; without it the write's window runs on into
the `restored` write and §4.4's comparison is taken over a window that
contains the restore. The block's `roles` line is the diagnostic: a block that
reads `control, write, restore` says on its face that it has no boundaries,
and a reader is better placed than a check to decide whether that matters for
the day. A *mandatory*-boundary check would reject captures this tool grades
today, and the issue did not ask for one.

### `unplaceable_marks` stays fatal

The issue names the fatality rule as a consequence rather than the defect, and
it is left alone. A legitimate §3 round landed in that set only because it had
no label; once the stage rounds are a real class, the legitimate case is gone.
A genuinely unreadable label — a typo, a blank-line `mark N` from a tool that
still substitutes one — still refuses the run, which is the tool's documented
conservative direction and is pinned by an existing test.

What did change is the message: it used to say *the three forms* and quote
three, and now quotes all six and takes the count from the tuple, so the count
lives in one place. That is the operator's whole remedy for an unplaceable
mark, and a blank press's operator used to be told three spellings of which
three were wrong.

## Two details that decide the shape

1. **A bare word cannot parse under the old matcher.** `part.startswith(word +
   " ")` is right for the three action forms, all of which are followed by
   `0x0751=…`, and wrong for a boundary, which is the word. `MARK_FORMS` is
   three-tuples now, `(role, word, takes_value)`, and the match is
   `part == word or part.startswith(word + " ")`. A stage word with a trailing
   annotation (`watch over the window`) still reads, and a dropped one does
   not.
2. **A boundary carries no value, so the role table has to say so.** The three
   existing roles take a value and return `(None, None)` when `MARK_VALUE` does
   not match; a boundary has to match with no value *at all*, and a matcher
   that inferred that from a regex not matching would make a missing value
   indistinguishable from a form that wants none. Hence the flag, and
   `BOUNDARY_ROLES` read off it rather than spelled beside it.

## Files

**New**

- `ec/tools/testdata/0751-isolation-run-staged/` — the six-round form §3
  prints, two blocks (`0xA0` then `0x10`), every mark in all three captures
  and spelled the same way. The `0x075B` rows sit on either side of the
  `watch over` mark, so *"the end-of-watch round closes the write window"* is
  arithmetic over the fixture and not an assertion: read with the mark, the
  write window is `0x68 -> 0x6B` over two changes and the boundary's is
  `0x6B -> 0x6D` over one; without it they are one window reading
  `0x68 -> 0x6D` over three, with the restore inside the bracket. It is *not*
  a prediction that a fan duty moves on either side of a watch.
- `docs/findings/0751-stage-mark-labels.md` — this file.

**Shared**

- `ec/tools/grade_0751_isolation.py` — `MARK_FORMS`, `REQUIRED_LABEL_FORMS`,
  `BOUNDARY_ROLES`, `parse_mark`, `assign_blocks`, the `unplaceable_marks`
  message, `UNREAD_MARK_NOTE`, the `Block` docstring, and the module
  docstring's paragraphs describing the block shape.
- `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` — §3's console block
  gains a `rem mark each console: <label>` line per round, all six; §3's
  "those three forms are load-bearing" paragraph is rewritten to cover six and
  to say what a block without a `watch over` costs; §6's form list and its
  requirement wording are updated. §3's `--seconds 240` arithmetic paragraph is
  **left alone** — it already says six, and is the runbook's own evidence that
  six was the intent.
- `ec/tools/test_grade_0751_isolation.py` — `section3_command()` beside the two
  §6 readers, `concrete()` extended with `<current>` and `<original>` (safe:
  §6's fenced file list, which shares that helper, contains neither), a
  `window_body()` cut, and six new cases.
- `ec/tools/testdata/README.md` — one table row and one paragraph.
- `docs/findings.md` — one summary line and this link.

**Also touched, and why**

`windows/tools/ec_watch.py` and `windows/tools/ec_watch-marks.md` are not in the
plan's file list, and both say *three forms* where the tool now says six. The
prompt's notice is `" / ".join(REQUIRED_LABEL_FORMS)`, so the notice block
quoted verbatim in `ec_watch-marks.md` is the one thing in that file this change
makes false, and a docstring that says the prompt quotes three is a false
statement about code. Five sentences and one quoted notice line were corrected
to drop the count rather than to restate it; no behaviour in either file
changed, and `windows/tools/test_ec_watch.py` reads
`grader.REQUIRED_LABEL_FORMS` in a loop, so its `RefusedLabelTests` cover the
three new forms without an edit.

**Deliberately not touched**

- `ec/README.md:299-303` — the tool's entry describes its scope and its
  `--dump-pair` contract, not its label vocabulary, and stays accurate.
- `windows/tools/manual_fan_ctrl_probe.py` and its suite — the probe emits only
  the two action forms, and optional boundaries leave its captures exactly as
  they are.

  **Correction (issue #476, 2026-09-25), leaving the bullet above as it was
  written.** Issue #476 changed both files this bullet names, so the claim
  about what the probe emits is out of date: it now writes the restore's mark
  as well, a capture it writes is three marks — `no-op wrote …`, `wrote …`,
  `restored …` — and that capture grades `intact`, roles `control, write,
  restore`, exit 0, where the two-mark shape the tool used to write comes
  back `VOID` with its windows withheld. The bullet's second half survives
  and this change is a confirmation of it: boundaries stayed optional, and a
  capture without them grades as it did. Only the probe's own output moved,
  and only by gaining the mark that closes its block.
- `ec/annotations/registers.yaml` — no register's status changes. This is
  capture plumbing; `MANUAL_FAN_CTRL` stays `present-untested`.
- `evidence/` — no capture is added. The run is a human's.

## What is pinned

`bash tools/run-tests.sh` from the repository root; `ec/tools/test_grade_0751_isolation.py`
goes 76 tests to 82, all passing under
`python3 -m unittest test_grade_0751_isolation` from `ec/tools/`.

| test | what it holds |
|---|---|
| `test_section3s_six_rounds_are_the_forms_the_grader_reads` | §3's `rem` lines resolve to six labels parsing to `settle, control, hold, write, watch, restore`; the roles §3 produces are exactly the roles `REQUIRED_LABEL_FORMS` produces; the three stage words are in that tuple by name; §6 names all six |
| `test_a_staged_six_round_run_is_graded_rather_than_refused` | exit 0, no `UNREADABLE`, no `NOT GRADED`, twelve windows in order, both blocks `intact`, the six-role line twice |
| `test_the_end_of_watch_round_closes_the_write_window` | the write window's `0x075B` figures and the boundary window's are different windows' — the substantive claim, read off a cut on the window header rather than a substring of the whole report |
| `test_a_stage_boundary_is_checked_like_any_other_mark` | a `watch over` dropped from one capture and one respelled in another each withhold block 1's six windows, name the capture and the consequence, and leave block 2 graded |
| `test_block_selects_all_six_windows_of_a_staged_block` | `--block 0xA0` prints six windows numbered where they are in the whole mark stream, and still declines the capture-level comparison |
| `test_a_capture_with_no_boundaries_still_grades_as_it_did` | `run/`, `multi-block/` and `3blocks/` read `[['control','write','restore']]`, `…×2` and `[['control','write','restore'],['control','write'],…]`, with the old exit codes |

The first of those is the one the issue is really asking for: it reads §3 and
§6 out of the runbook rather than restating them, so a runbook that renames,
reorders, adds or drops a round fails a test instead of a human's day. It is
the same shape `test_section6s_file_list_is_the_fixture_set` already uses, and
for the same reason.

Two existing assertions changed, both the same rewording: the unplaceable-label
test's message string and the one in `test_a_window_in_no_block_whose_marks_
agree_is_not_refused`, plus that test's name. The first also gained
`assertEqual(len(REQUIRED_LABEL_FORMS), 6)` and now walks six forms in the loop
it already had.

## **None of this is a live test.**

No EC and no laptop is reachable from a GitHub-hosted runner. Every figure in
this file is arithmetic over hand-constructed CSVs in `ec/tools/testdata/`,
reproducible offline with the command above. No live run, no register readback,
no hardware observation. What §3's six mark rounds would do on real consoles is
what this change makes the grader able to notice; the run that would show it is
#380's, and it stays a human's.
