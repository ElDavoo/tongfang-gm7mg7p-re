# The one real 0751 capture converts to a capture the grader reads (issue #124)

`evidence/ec-watch/2026-09-23-0751-isolation.txt` is the only real capture of
the `0x0751` isolation test this repository holds. It is also free-form console
text — a `=== write 0x0751=0xA0 (hold 20s) ===` line, a
`+ 0.0s  0x0751: 0x10 -> 0xA0` row per block, a `restored 0x0751 -> 0x10`
line, and a `SUMMARY:` block — and `grade_0751_isolation.py` reads
`ts,addr,old,new` plus `ts,MARK,,label`. The reader refused the file on its
first non-comment line, so the one run that matters was graded by eye. That is
the drift #120's own description set out to remove, arriving anyway.

`ec/tools/probe_log_to_capture.py` is the converter, and
`ec/tools/testdata/0751-isolation-probe-log/2026-01-01-0751-isolation-from-probe-log.csv`
is its output over that file, committed so the conversion is a diff rather than
a claim about what a tool would do.

**Nothing here is a claim about the machine.** The source is a 2026-09-23
artifact, this reads a file, no EC is opened and no register is read. No
`status:` in `ec/annotations/registers.yaml` moves, and `MANUAL_FAN_CTRL` stays
`present-untested` — the conversion makes an existing record readable and
establishes nothing new about `0x0751`.

## What the excerpt is, and why it is a transcription and not a capture

Three blocks, one per value, each a `===` line naming the write and a 20 s hold,
one `+ 0.0s` change row for `0x0751`, a restore, and a `SUMMARY:` line naming
the addresses that moved. Its own header records a run timestamp, the Control
Center version, the services running, and a watch set; its own closing note
records that the `0x075B`/`0x075C` PWM rows are "changes omitted above".

A transcription, on counts that are visible in the file rather than inferred:

- **The PWM rows are not in it.** The closing note says so. The grader prints a
  line of zeros for every §4.1-§4.3 address in every window and closes by
  calling the run consistent with the static prediction; over this file both are
  true and both are silent about the addresses the transcriber left out. A zero
  over an address with no row is a zero of the record, not a byte seen to hold
  still. `grade_0751_isolation.py`'s own `ZERO_SCOPE_NOTE` already carries a
  half of that — the sampling half — but not the omission half, and this is the
  case the two halves differ on.
- **It has no control arm.** There is no `no-op wrote` mark anywhere in it, so
  §4.4's control-vs-write comparison is not available over a capture derived
  from it. The tool does not write one to make the comparison runnable.
- **The rows are ones a person typed.** `0x0751: 0x10 -> 0xA0` at `+ 0.0s` is
  what the session recorded, not a sampled transition.

The derived file's `#` header carries each of those as a `caveat:` line, and a
fourth for the timestamps below, because a caveat the grader drops is a caveat
nobody reads and `read_capture` drops every `#` row. The header also indents the
source's own transcribed notes three spaces under a `#`, which is what stops a
note beginning `# the run ended early:` from becoming the one `#` row
`read_early_exits` takes instead of skipping — a header read as a crash would
charge every block's windows and withhold all of them over a file that records
none.

## What the conversion is faithful about, and what it assumes

Read the source and two of its four kinds of information are there and two are
not:

| | in the source | in the derived capture |
|---|---|---|
| which block a row belongs to | yes, the `===` line it sits under | unchanged |
| block order | yes | unchanged |
| a row's offset inside its block | yes, the `+ T.Ts` | unchanged, applied to the block's start |
| the absolute anchor | **no** — one stamp for the whole run | `--anchor`, required |
| the inter-block gap | **no** — in no line of the file | `--block-gap`, default 30 s |

`build_windows` files a change at exactly a mark's timestamp into that mark's
window, so `+ 0.0s` sits in the window the `===` line's mark opens, and the
restore is stamped at the block's own `hold` rather than at the gap: the hold is
in the source and the gap is not.

Both choices are named on the command line, written into the derived header
beside the source's real run timestamp, and `--anchor` is **required** rather
than defaulted — a default would let a reader believe a reconstructed timestamp
was an observed one, and the committed fixture is anchored at `2026-01-01T12:00:00`
both for that reason and because `ec/tools/testdata/README.md` requires an
obviously-placeholder date of everything in that directory.

The gap has exactly one property it has to have: two marks must end up further
apart than the grader's `MARK_MERGE_SECONDS`. Closer than that and
`coalesce_marks` folds a restore into the next write, the block walk reports a
day that never happened, and the file looks like a run rather than like a
mistake. So the converter refuses an anchor/gap pair that fails it, naming both
numbers and the constant it is measured against — read out of the grader by
path, as `ec_watch.py`'s `--label-vocab` does, so there is one spelling of it.

## The `SUMMARY` cross-check, and exactly what it proves

The transcriber wrote down, per block, which addresses moved and what they
became. That claim is checkable against the block's own change rows: same
address set, same first old value, same last new value. So the converter checks
it and **refuses** on a disagreement, naming the block and the address and
writing no output file.

This is the one thing the format honestly supports, and it is worth being exact
about what it is. Agreement says the two halves of one transcription are the
same claim. It does not say either is true of the machine, it does not extend
the record to the rows the transcriber omitted, and it cannot: the third block
of the committed file has an empty `SUMMARY:` and no change rows, and the two
agree trivially. What it replaces is a reader's eye, which is the step that was
being done by hand.

The one normalisation the conversion performs is the restore's spelling:
`restored 0x0751 -> 0x10` becomes `restored 0x0751=0x10`, because `MARK_VALUE`
needs the `=` and a label without one is a mark `parse_mark` cannot place. The
third block is **not** relabelled: the source writes `=== write 0x0751=0x10 ===`
for what is functionally a no-op, and calling that `no-op wrote` would be
inventing §3's control-arm form, which `parse_mark` reads as a different role
on purpose.

## What the derived capture grades as

`read_capture` over the file the converter writes returns exactly the
`(marks, changes)` pair it returns over any other capture — six marks and two
change rows here, and the suite asserts it by *grading* the file rather than by
checking the pair, so the reader doing the reading is the real one.

Run over the committed file, the real grader exits 0 and prints one window per
mark, three `intact` block verdicts naming `0xA0`, `0x00` and `0x10`, and
`None of the §4.1-§4.3 bytes moved in any window`. Those are the figures the
suite pins, and each is what it says and no more:

- `intact` is `parse_mark`'s read of the block's last mark. It says the capture
  can show the byte being put back. It says nothing about what the EC did.
- The zeros are zeros over a file with two change rows in it, both of them
  `0x0751`. Every fan-table and temperature address is a zero because there is
  no row for it — which is the third caveat in the header, and which the
  grader's own closing sentence does not carry. Making it carry would be a
  change to the grader's report rather than to this file's header, and that is
  the one edit to that file this does not make.
- The run graded is a write arm and a restore, per block. There is no control
  arm in it, so §7's call is not available from it, and the grader says as much
  in its own output about `confirmed-inert` needing all three values.

The report itself is **not** committed. It is long, most of it the grader's
per-address zeros, and it is generated from the capture by a second command;
committing it would add a value every unrelated grader change has to edit and
that no test reads byte for byte. The derived capture is committed instead,
because it is the converter's entire output, it is small, and comparing it
byte for byte makes a parser change a diff. `test_probe_log_to_capture.py`
regenerates it and grades it; the two commands below are the whole of the
manual version.

```sh
python3 ec/tools/probe_log_to_capture.py \
        evidence/ec-watch/2026-09-23-0751-isolation.txt \
        --anchor 2026-01-01T12:00:00 --out /tmp/derived.csv
python3 ec/tools/grade_0751_isolation.py /tmp/derived.csv
```

Both are stdlib-only and neither opens an EC.

## The two older captures, and what a refusal reads like

`2026-09-23-power-mode-cycle-0700-07ff.csv` and
`2026-09-18-profile-switch-0700-07ff.csv` predate the `MARK` row. Each exits 1
with `no MARK rows` on stderr, and `read_capture` over each returns no marks
and a non-empty change list — they are captures, and the refusal is about marks
rather than about the file being unreadable.

The third input, the log above, reached `read_capture` as an exception: it
raised `ValueError` out of `main`, so an operator who handed the grader a
console log got a traceback over an otherwise clean §6 file list. `main` now
catches it, prints the exception's own sentence — which is the reader's, so
`bom_refusal` and the short-row message keep exactly one spelling — and returns
1. `test_grade_0751_isolation.py`'s `UnreadableCaptureTests` holds that over
constructed files, so the grader's own suite keeps its "no real capture is
involved" property; the real log is driven from
`test_probe_log_to_capture.py`.

## What this does not settle

§3's fixed-load re-run is still §3, still needs the physical machine, and is
untouched by any of this. The rows the excerpt omitted cannot be put back by a
converter, and §4.4's comparison is unavailable over a capture derived from a
file with no control arm in it. `MANUAL_FAN_CTRL` is `present-untested` before
this and `present-untested` after it, and the reading it has been given — that
the drift under a no-op was as large as under a real mode change, so PWM motion
there is thermal — is a reading of the file's own note and not a measurement
this conversion adds to.

## Follow-ups this opens

- **The probe's format is now two formats.** The `--csv` capture and this
  legacy console log are different shapes with one grader, and only the first
  has a producer the next run uses. A log from before `--csv` exists needs this
  converter and a chosen anchor; the converter's own docstring is where that is
  said, and §6 of the runbook now names one capture format and its two
  producers rather than a third shape.
- **`README.md` in `evidence/` names the converter.** A reader arriving at the
  log through the evidence index can find the gradeable form from there.