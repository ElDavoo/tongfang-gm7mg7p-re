# A `--csv` probe run's `hold` is held to the grader's mark-merge window (issue #665)

The write-up for [issue
#665](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/665), which is
about `windows/tools/manual_fan_ctrl_probe.py` taking `hold` with nothing
checking it. `MARK_MERGE_SECONDS` is 5 s
(`ec/tools/grade_0751_isolation.py:260`) and `coalesce_marks` (`:651-680`)
closes a group at **exactly** the window (`:669`), so a `hold` at or under 5 s
folds this tool's three marks into one window — a capture with no block to read
out of it at all. **This is a tool-side guard and nothing more**: no EC is
opened, no register is read, no capture is taken, no register `status:` moves,
and no line of this change is a report about the machine.

## The reading taken: refuse, on the `--csv` path only

**Refuse rather than warn**, and the neighbouring file says the rule this
follows. `ec_watch.py`'s docstring states it as *"It refuses only what the
grader would refuse"*, and the contrast inside this neighbourhood is the one
that decides it:

| | `ec_watch.py --block` on a range covering the fan-tach page | this guard |
|---|---|---|
| what the tool knows | nothing about what a wider access does to that page | the marks are its own, one per arm, one `hold` apart |
| what the reader would do | unknown — the driver has never been asked | refuse the block: one window, no block |
| so | **warns** (`ec_watch.py`, the `--block` paragraph) | **refuses** |

`ec_watch.py` warns there because it cannot tell which captures its reader
cannot read. This tool can, and the failure is total and late: the operator
spends a hardware run and finds out at the grading. The house idiom for exactly
this shape is the whitelist two lines away — `sys.exit(msg)` **before** `Ec()`,
pinned by `test_target_outside_the_vendor_set_is_refused_before_opening_the_ec`
— and a short hold is the same class of thing: a value the tool will not
honour, not a typo. That is also why it is `sys.exit(msg)` and not
`ap.error`/`parser.error`: argparse's exit 2 is what a mistyped flag gets, and
`test_the_hold_refusal_is_not_a_usage_error` pins that the two stay apart.

**Conditional on `--csv`**, because that is the only path on which a `MARK` row
exists to be coalesced: `sink = MarkCsv(args.csv) if args.csv else None`
(`manual_fan_ctrl_probe.py`, in `main`), and every `sink.mark(...)` sits under
`if sink:`. A terminal-only run at `hold 3` writes no capture and has nothing
its reader could misread. **An unconditional floor would refuse a run that
cannot fail**, which is the overclaim `docs/findings.md` §4 and CLAUDE.md's
"calibrate, don't overclaim" exist to stop — so the narrowing is a case of its
own (`test_a_short_hold_without_a_capture_is_not_refused`), placed to make a
later widening to unconditional a visible disagreement rather than a quiet one.

**The threshold is `hold <= MARK_MERGE_SECONDS`.** Equality coalesces, because
`coalesce_marks` closes at `<=`, so a hold of exactly the window folds the
marks as surely as one under it. The rule lives in one named predicate,
`marks_clear(hold)` (`manual_fan_ctrl_probe.py:258`), so the guard, the
`--self-test` row and the suite all read it from the same place rather than
each restating a `<=`; both edges are pinned, the refusal at the window by
`test_a_hold_exactly_at_the_window_is_refused_too` and the acceptance half a
second above it by `test_a_hold_just_above_the_window_still_grades_clean`,
which runs the capture through the real grader and gets one intact block back.

**`hold` is judged alone, and that is the conservative side.** The real gap
between two marks is `hold` **plus** the re-snapshot between the arms — 206
ECRR reads, one `DeviceIoControl` per byte, plus the `--level-block` 16 when
they are on — and nothing in this repository has measured what that costs on
the machine. So a `hold` above the floor is the operator's decision again, not
a claim that the capture is safe, and the code comment on `marks_clear` says
so. Per CLAUDE.md, four matching readbacks are not evidence the EC acts on a
write, and a clear mark spacing is not evidence the reads between the marks are
free.

## The constant is restated, and what pins it

`MARK_MERGE_SECONDS = 5` sits at module scope beside this tool's other
constants (`manual_fan_ctrl_probe.py:226`) rather than being imported, and the
reason is the one already written into the file: **this tool runs next to
`ecrw.py` on a Windows box, where the repository layout is not something to
depend on** — which is why the grader is reached by path inside `self_test()`
(`importlib.util.spec_from_file_location`, and the comment above it) and not at
module scope. A guard that reached into `ec/tools/` would make `main()` depend
on a directory the operator does not have.

A restatement is only as safe as its pin, so
`test_the_restated_window_is_the_graders` asserts
`probe.MARK_MERGE_SECONDS == grader.MARK_MERGE_SECONDS` against the **real**
grader, imported by path the way the self-test imports it. **The direction of
the pin matters:** the probe's copy is what follows the grader, so a window
that moves in `grade_0751_isolation.py` fails the probe's suite and names
itself. The grader is not edited — 5 s is its own value and is right for its
own three-console procedure, where one action lands as several `MARK` rows
seconds apart.

## What changed, and the tests that hold it

`windows/tools/manual_fan_ctrl_probe.py` — five small edits: the constant; the
`marks_clear` predicate; the guard at `main():681`, after the `--self-test`
dispatch and before `Ec()`; the `hold` argument's help text, which names the
floor next to §3's ~30 s because the help is where the operator decides the
number; the docstring's hazard sentence, rewritten to name the guard and then
the failure it used to invite; and one `check()` row in `self_test()` — the row
a human with no driver can run.

`windows/tools/test_manual_fan_ctrl_probe.py` — seven cases, 47 to 54:

| case | what it holds |
|---|---|
| `test_a_short_hold_is_refused_before_opening_the_ec` | `hold 3 --csv` exits with the message, no EC opened, and no capture file left behind — the refusal is above the EC **and** above the sink |
| `test_a_hold_exactly_at_the_window_is_refused_too` | the `<=` edge, refused |
| `test_the_hold_refusal_is_not_a_usage_error` | the code is a message, not 2 — the distinction from a mistyped flag |
| `test_a_hold_just_above_the_window_still_grades_clean` | `MARK_MERGE_SECONDS + 0.5` runs, and the real `run_grader` returns exit 0, `block 1/1: intact`, three roles, three windows |
| `test_a_short_hold_without_a_capture_is_not_refused` | the narrowing, pinned |
| `test_the_restated_window_is_the_graders` | the restatement is the grader's own constant |
| `test_the_self_test_checks_the_hold_floor` | the `--self-test` row is one a human without the machine can run |

The default 30 s with `--csv` still running and still grading clean was already
covered and is not re-asserted here:
`test_the_default_hold_is_the_procedures_thirty_seconds` reads the default off
the banner, and `test_a_probe_capture_passes_the_real_grader_end_to_end` runs
it through the real grader for one intact block, three roles and exit 0.

Each of the seven was checked against a mutation of the tool, because a case
that passes both ways is not a pin: `<=` loosened to `<`, the `--csv`
condition dropped, the constant moved to 8, the guard relocated below `Ec()`
and again below the sink, the refusal changed to `ap.error`, and the
`--self-test` row deleted. Every one turns the suite red.

**The self-test is the row a human without the machine can run, and it was not
run on this branch's runner**: `python3 windows/tools/manual_fan_ctrl_probe.py
0xA0 --self-test` needs `ecrw`, which binds `kernel32` at import time
(`ecrw.py:70`) and so only loads on Windows. Here the same code path runs
through the suite instead, which installs `windows/tools/ecrw_fake.py` first —
`test_the_self_test_passes_without_opening_an_ec`,
`test_the_self_test_checks_the_hold_floor` and the rest. The claim is that it
passes offline on a fake, not that a human has run it on the Windows box.

## What this does not establish

- **No hardware, no Windows box, no EC.** No EC was opened, no register was
  read or read back, no capture was taken or graded against real data. Every
  case above runs against `ecrw_fake.py` and the committed grader over
  hand-built CSVs.
- **A `hold` above the floor is not a safety claim.** The floor is where the
  grader stops being able to read the capture, and nothing more. It says
  nothing about whether the reads are safe — #94 is the open question of what
  this traffic does to a fan, and this guard is not a step towards it, does not
  narrow it, and must not be described as improving it. `--interval` is
  untouched for the same reason: §3's cadence is a starting point.
- **The inter-arm re-snapshot's cost is unmeasured.** 206 ECRR reads sit
  between two marks, and nothing here has timed them on the machine, which is
  why the guard judges `hold` alone and on the conservative side.
- **The re-snapshot means a `hold` just over the floor is not exactly the
  floor.** The suite's fake clock puts the two arm marks `hold` apart and the
  write and restore marks slightly more; the real run adds the re-snapshot on
  top. The guard cannot see any of that, and says so.

## Left out on purpose

- **An override** (`ctgp_dben_probe.py`'s `--i-mean-it` is one, for a
  different reason — an unattended machine change, not a capture-shape
  argument). A flag that lets an operator write a capture the reader cannot read
  is the defect, not a feature. An operator who genuinely wants a short capture
  wants a different `MARK_MERGE_SECONDS` in the grader, and that is a decision
  about the grader's own procedure.
- **Changing the grader's window.** 5 s is the grader's and stays there; the
  probe adapts to it and the adaptation is pinned from the probe's side.
- **An unconditional floor**, and anything to do with `--interval`. See above.
- **`docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`** — §3 asks for a
  ~30 s hold and §3b describes the probe's defaults; both already clear the
  floor, so nothing in it becomes false. A long shared file, edited for no gain.
- **`ec/annotations/registers.yaml` and every annotations CSV.** No register
  status changes, which the issue says and which is true: this is tool-side
  only.
- **#639.** That is the §3 procedure's by-hand `rem mark each console:` boundary
  spacing across three consoles — a different lever, in a different file, with
  no line of §3 changed here. The two are both about `MARK_MERGE_SECONDS` and
  share nothing else: #639 is the operator pressing Enter three times, and this
  is the tool's own `hold` argument.
