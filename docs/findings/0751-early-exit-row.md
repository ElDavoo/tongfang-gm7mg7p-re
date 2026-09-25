# The grader dropped the probe's "the run ended early" row, and a 5-second arm graded as a 30-second one (issue #664)

The write-up for [issue
#664](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/664): the row a
crashed `manual_fan_ctrl_probe.py` run writes into its own capture was the one
row the grader could not see, and the report it produced over that capture was
a clean exit 0. This is a change to what the tool can read and say about a
capture. Nothing here is evidence about the machine, and no register status
moves: `MANUAL_FAN_CTRL` stays `present-untested` and #663 still owns the run.

The procedure the tool grades against is
`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`; §3 is the block, §6
the file set and the labels.

---

## The reach, as the code stood

Two ends, each already in the tree.

The writer, `windows/tools/manual_fan_ctrl_probe.py`'s `except BaseException`
handler, which wraps both arms and whose `finally` restores 0x0751 and writes
the restore's mark whatever happened:

```python
    except BaseException as exc:
        if sink:
            sink.row([f"# the run ended early: {type(exc).__name__}: {exc}"])
        raise
```

The reader, `ec/tools/grade_0751_isolation.py`'s `read_capture`, which drops
it — deliberately, and for a reason this change must not break:

```python
        for row in csv.reader(f):
            if not row or row[0].startswith("#") or row[0] == "ts":
                continue
```

`build_windows` therefore never sees one, and neither does `assign_blocks`. The
row is the only record that the arm did not run to its hold, and the report had
no way to know it was there.

Measured, on `ec/tools/testdata/0751-isolation-run-multi-block/` with that row
written into the 0xA0 block's write window by hand, against
`git show HEAD:ec/tools/grade_0751_isolation.py`:

```
    python3 /tmp/before/grade_0751_isolation.py <the three captures>
```

```
  2026-01-01-0751-isolation-0700-07ff.csv: 6 mark(s), 15 change row(s)
```

and, at the end:

```
  block 1/2: intact -- last mark 'restored 0x0751=0x10' is the restore
    value under test 0xA0; roles control, write, restore
  ...
  None of the §4.1-§4.3 bytes moved in any window: consistent with the static
  prediction, for this capture's window only (§5: ...).
```

Exit **0**. A block whose write window was cut at 5 s of a 30 s hold came back
intact, its three windows printed, and the closing section compared the whole
capture to the static prediction — a false green by the tool's own standard, and
the one capture shape the probe can now produce that the grader was blind to by
construction.

The void check is not the gap, and this is the part worth being exact about.
The restore is in a `finally`, so its **mark** lands however the run died, the
block holds it, and `block_verdict` is `intact` by its own definition. The
capture is not short a *mark*; it is short a *hold*. The two facts read alike on
the block line, which is why the fix cannot be a stronger void check: there is
no mark missing to notice.

`windows/tools/test_manual_fan_ctrl_probe.py`'s
`test_a_crashed_run_records_why_and_still_closes_its_block` pinned the whole
consequence end to end, `rc == 0` and `block 1/1: intact` and a comment saying
*"Nothing in the report says the window is short"*. That case is rewritten by
this change rather than added to; the defect was in what it asserted.

## The decision

**A placed early-exit row is charged to the block whose window it fell in; that
block's windows are withheld; the exit code is 1. The row keeps its `#` prefix
and gains a timestamp.**

Three words in that sentence carry the rest.

**Charged to the block**, not to the window. `Block.problems` is the one list
the window loop, the block verdict, the marker on the two dump sections and the
exit code already read, and the new kind is appended to it as
`("early-exit", window, text)` — the same shape `check_block_marks` returns.
So the existing machinery withholds, counts, marks `NOT GRADED` and sets the
exit code, and there is no second store that can disagree with the first. §3
defines the block, the void check already withholds on it, and the capture
cannot say which arms *before* the cut are still worth reading — the control
arm in a crashed run did run its full hold, and it is not reported either.

**Placed**, by timestamp. The row is written between the arm's last sweep and
the restore's mark, so the last window at or before its timestamp is the one it
cut short. The timestamp is therefore the load-bearing part of the row's new
shape: without it the row says *that* a run ended and not *when*, and no window
in the report can be named as the short one. It is `now()` — the shape
`parse_ts` already reads from a mark row — stamped from the same clock as the
marks around it, which is what makes "between the write and the restore" a fact
about the file and not about the terminal.

**With its `#` prefix.** `read_capture` skips every `#` row so an operator can
annotate a capture by hand, and every committed fixture under
`ec/tools/testdata/` opens with a `#` block. Changing the skip would break the
invariant this change exists inside. The row is told apart by the phrase it
opens with, not by being a comment:

```
# the run ended early: 2026-09-25T14:31:02.480+02:00,manual_fan_ctrl_probe: RuntimeError: observation failed mid-run
```

Two CSV fields, the phrase and the stamp first, the writer's own name and the
exception in the second. A hand annotation does not carry the phrase and is
skipped exactly as before; `ec/tools/test_grade_0751_isolation.py`'s
`test_a_hand_annotated_capture_grades_exactly_as_it_did` pins that by
comparing the whole report of an annotated copy of `multi-block/` against the
unmodified fixture's, byte for byte with the directory swapped back.

## Why not the other readings

The issue offered three answers (surface it, withhold, refuse) and two
directions (change the reader, change the writer). This lands one of each. The
rest, declined with a reason:

- **Treat every `#` row as an early exit.** It would make a hand annotation
  refuse a run §6 explicitly invites the operator to annotate, and every
  committed fixture — each of which opens with a `#` block — would stop grading.
- **Print it and carry on** (surface only). That leaves a green exit over a
  5-second arm, which is the one outcome the issue rules out. The report would
  be *more* honest and still quotable as a §7 `confirmed-inert` input, which is
  the failure: §7's call is made on a report that says a capture is complete.
- **Refuse the whole invocation whenever any capture carries the row.** §6 runs
  one `--block <value>` per value and attaches the runs side by side, so that
  would fail every attachment of a good value because a different value in the
  same file crashed — the opposite of what that command line is for. The
  existing scoping rule already answers it: `void` and `withheld` are this run's
  selected block, so a `--block 0x10` run over a day whose `0xA0` block crashed
  prints block 2's windows and exits 0. The early-exit **section** prints whole
  anyway, naming the crashed block even when this run did not select it, exactly
  as `report_census` names unselected blocks.
- **Scope the refusal to one window rather than the block.** It would need a
  second per-window store beside `Block.problems` — the ordering accident
  `docs/findings.md` §16 is written about — and the block is the unit §3
  defines.
- **Change `read_capture` to return a third element.** It breaks
  `ec/tools/grade_gpu_door.py:421`, which imports this module and unpacks the
  two-tuple, and it edits the one function whose skip rule is the invariant.
  `read_early_exits` is a second reader over the rows `read_capture` drops.
- **Have the grader import the probe's constant.** `ecrw` binds kernel32 at
  import time, so importing the probe is Windows-only. The phrase is a second
  spelling, pinned equal by a case in the probe's offline suite and again by its
  `--self-test` — the arrangement `arm_labels` and `REQUIRED_LABEL_FORMS`
  already use. A drifted tag is not a quiet failure: the grader would match no
  row and every crashed run's capture would grade as one that finished.
- **Have the grader import the probe to *write* the row.** The probe is the
  writer. The grader reads files and has never written one.

## What the report can now say, and what it cannot

The calibration rule (`CLAUDE.md`; `docs/findings.md` §4) is that a sentence
here is a claim about *which files were handed in*, never about the machine.
Every sentence the new path can print, and the fact each rests on:

| printed | rests on |
|---|---|
| `<capture> (1 row(s)):` under `=== early-exit rows ===` | this file holds one row opening with the phrase |
| `in mark 2/6 ('wrote 0x0751=0xA0') of block 0xA0 (block 1 of 2)` | the last window at or before the row's timestamp, and that window's block |
| `…: manual_fan_ctrl_probe: RuntimeError: observation failed mid-run` | the row's own text, quoted; the grader does not parse it and does not claim to know who wrote it |
| `-- NOT GRADED, 1 problem(s): early-exit` | the block carries one problem of that kind |
| `block 1/2: intact` and `-- NOT GRADED, its windows are not printed` | the restore is there; the windows are withheld anyway. Two facts, printed as two |
| `this capture records the run ending early inside it, its windows were withheld above` (on the two dump sections) | the same two facts, carried to a read under that value |
| `NOT PLACED -- <why>` and the refusal on stderr | the row's timestamp does not place it: no readable stamp, no window at or before it, or a window in no block |

Two of those are deliberately *not* claims, and say so in words:

- The report never says the write arm *failed*, that the EC did anything, or
  that the value under test had no effect. A block whose run stopped is
  withheld, and `docs/findings.md` §4's two retractions are both a method
  reporting an absence as a fact — which is what "this capture does not contain
  a full window" would become if it were phrased as a result.
- The refusal for an unplaceable row says the row carries no readable
  timestamp, or that no mark is at or before it. It does not say the run did
  not finish, and it does not imply a timestamp was found and lost.

The exit-code sentence in the section is scoped rather than flat, because the
section prints whole under `--block` while the exit code is the selected
block's alone. The block section's note is the early-exit one rather than
`MARK_SET_NOTE`, since a block withheld here holds every mark it has and the
mark-set note would send the operator to a console that recorded all of them.

## The unplaceable row, and why it refuses the whole run

A row that places is a per-block decision. A row that cannot is not, and the
reason is `unplaceable_marks`'s: block attribution rests entirely on the labels
and on where each row falls in the mark stream, so a row that cannot be placed
leaves every block's completeness uncertifiable, not only the one it would have
landed in. `--block` narrows what is graded, not what is known. So the run
prints the section whole — the row is visible on the run that refuses it — and
returns 1 before the window report, in the register of the repeated-capture
refusal at `:1990`.

This is also the shape a capture taken with a probe *older than this change*
has: the same phrase, no timestamp. Such a capture is refused rather than
silently green, and the fix is to re-run that block (§6 now says so), not to
edit the row — a hand-added timestamp is a claim about when a run stopped that
nobody witnessed.

## The offline proof

No fixture was added: `ec/tools/testdata/` is untouched, which is what keeps the
hand-annotation regression meaningful, and every case is a temp copy of a
committed one with one row added.

```
    python3 -m unittest discover -s ec/tools -p 'test_grade_0751_isolation.py'
    python3 -m unittest discover -s windows/tools -p 'test_manual_fan_ctrl_probe.py'
```

82 grader cases before this change, 88 after (6 new); 47 probe cases before, 49
after (the crash case rewritten, two added). The new grader cases:

| case | what it is there for |
|---|---|
| `test_an_early_exit_row_withholds_the_block_it_falls_in` | the decision, end to end, with the a0 dumps so the marker on both file sections is pinned: block intact, three windows withheld, the other block's three printed, exit 1 |
| `test_a_hand_annotated_capture_grades_exactly_as_it_did` | the invariant, byte for byte against the unmodified fixture |
| `test_a_row_this_cannot_place_refuses_the_run` | the two unplaceable shapes and the reason each one gives; plus a row with a timestamp and no reason, which places |
| `test_a_capture_with_no_marks_still_names_its_early_exit_row` | the one path where the section never prints: the "no MARK rows" refusal returns first, and the row is the only record of a run that stopped |
| `test_the_check_does_not_wait_for_a_second_capture` | one capture is enough — the probe's own `--csv` output is one file |
| `test_a_block_run_of_a_good_value_passes_over_a_day_that_crashed` | the scoping that §6's per-block command line depends on |

and in the probe's suite, `test_the_early_exit_row_lands_in_the_arm_that_raised`
and `test_the_early_exit_tag_is_the_phrase_the_grader_reads`. The first of the
three originally written in this tree —
`test_a_crashed_run_records_why_and_still_closes_its_block` — asserted `rc == 0`
over exactly this capture. It now asserts `rc == 1` with the block's windows
withheld, and keeps everything that was not the decision: the restore still
lands, the three windows still exist, the write window really is shorter than a
full one, and the change-row count is the same either way.

One fixture change was needed to make that last assertion mean something. The
suite's `Clock` did not advance between two `now()` calls, so the row and the
restore's mark carried the same millisecond and the row placed in the restore's
window. A wall clock does not stand still between two calls, so the fake now
moves by the stamp resolution; the reader's rule is unchanged and is the one
`build_windows` already uses for every change row.

## What this opens, as a fact rather than a fix

- **`ec/tools/grade_gpu_door.py` has the same blind spot.** It reads the same
  probe captures through the same `read_capture` (`:421`) and so drops the same
  row. It is not in this change's scope and the decision may not be the same
  one — the row is now *visible* in a capture, so a follow-up can apply the
  rule there on its own terms. Worth saying plainly: this change makes the
  0751 report honest and leaves the other one as it was.
- **`windows/tools/ec_watch.py` writes no such row.** It has no crash handler
  at all, so a watcher killed mid-run leaves a capture that is short its last
  mark and nothing else — which the void check does catch. Giving it an early-exit
  row is a separate change with its own capture-format question, and is not
  needed for the defect above.
- **The gate that would run the grader's suite per commit is still prepared,
  not landed** (`docs/ci/agent-gates-0751-self-test.patch`). Until a human
  lands it, the suite's own `--self-test` is the proof, and the five new cases
  run nowhere per commit — the same gap
  [`0751-grader-self-test-gate.md`](0751-grader-self-test-gate.md) records.
- **`MANUAL_FAN_CTRL` is untouched**, and should be: this is what a report may
  say about a capture it read, not a register behaviour. #663 owns the run.

## Nothing here was run against hardware

No EC and no laptop is reachable from a GitHub-hosted runner. Every output
quoted above is from hand-constructed CSVs in `ec/tools/testdata/` and the fake
`ecrw_fake.py`, reproducible offline with the commands named. The probe's
`--self-test` is the mode a human runs at the box afterwards, and its own
closing line says what it is. No line of this change may be read as a report of
a capture taken on the machine or of a register's behaviour.
