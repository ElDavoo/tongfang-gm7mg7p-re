# A timing claim over a committed capture is mechanical or inferred, and the tree did not say which (issue #1189)

Every timing claim in this repository over a passive capture rests on one
thing: being able to place a byte's move against an event. Where the capture
carries `ts,MARK,,label` rows, that placement is mechanical — the row says
when. Where it carries none, the placement is an inference from the ordering
and the addresses, and the door procedure has already had to retract one such
inference in place: `0x07C4`'s two rows "at the plug-in" in
`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` are ~10 s *after* the
`0x0743`/`0x0745`/`0x0746` bundle, within a millisecond of an unrelated dip,
and the file says so by not saying anything.

**The defect was not that nobody wrote the fact down.** It is sharper than
that, and the difference is what this write-up is about:

1. **The tool's printed output contradicted its own page.**
   `measure_mark_provenance.py` printed `evidence/ec-watch: 2 file(s)` while
   `0751-mark-provenance-shapes.md`'s prose said 8 of that root's CSVs hold
   none. Both were true of their own subject and the tool is the one a reader
   runs. The page was carrying a fact in prose that the measurement could not
   reproduce, which is the arrangement `0751-mark-provenance-shapes.md` itself
   calls out as the reason everything in its console blocks is quoted rather
   than transcribed.
2. **The population was a property, not a directory.**
   `fixture_census()` appended a capture only `if marks:`, so a capture with no
   marks was not reported, not counted, and not flagged. The census's
   population was silently the files that have marks.

The measure of the first is that the split was already in the tree in prose and
had been; what was missing was a way to *keep* it, which is what the check
below is.

## What the census now reports, and what it does not decide

`fixture_census()` reports every committed `*.csv` under its two roots and
`main()` prints the result as **two classes** — the ones holding a `MARK` row
and the ones holding none — each with its own per-root split. Reproduce with:

```console
python3 ec/tools/measure_mark_provenance.py
```

**The second class is deliberately not called "the captures with no marks".**
`fixture_census()` walks `ec/tools/testdata/` as well as `evidence/ec-watch/`,
and the fixture root holds annotation CSVs that merely sit under it:
`call-graph/index.csv` and `call-graph/ghidra-functions.csv` are
`program,addr,name,…` / `scope,addr,name,…` tables, and
`call-graph-gaps/index.csv` and `bank-map-score/score-example-targets.csv` are
the same shape. A census that called that class "the captures with no marks"
would be claiming a file is a capture on the strength of its extension and its
directory. So the block reports each file's **schema** — the first field of its
first non-comment row — and lets the `ts` / `addr` / `program` distinction be
read rather than decided. That is also why the class is reported per root: the
two roots are not symmetric, and a single count over both would read as a
number of captures that it is not.

## Why a committed capture can have none, and what is actually recorded

The *possibility* is knowable from the writers' source, and no capture file
records it, because it is a fact about the command that wrote it. These gates
describe the writers as they are now, which is not every committed capture's
explanation: the four oldest predate the `MARK` row itself, and
"What the index records" below separates them.

- `windows/tools/ec_watch.py` builds its `Marker` over
  `sink = CsvSink(args.csv) if args.csv else None` and calls `marker.start()`
  only under `if args.mark:`. **A `MARK` row needs `--mark` *and* `--csv`** —
  both, because the thread that writes the row is one the flag starts and the
  sink it writes into is one the other creates.
- `windows/tools/gpu_block_watch.py` and `windows/tools/system_id_probe.py`
  gate the same two ways; the first imports `ec_watch`'s `Marker` rather than
  defining one, the second imports no `ec_watch` at all.
- `ec/tools/ec_timer_capture.py` takes a mark from `--mark`, `--auto-mark`
  (AC and lid from sysfs, suspend/resume from the boottime/monotonic gap) or
  `--mark-input` (an evdev node). **That the only mark-bearing captures under
  `evidence/ec-watch/` are two arms of the timer family's run is consistent
  with the gate and is not evidence of it** — see the calibration below.

Each of those six gates is a row in `measure_mark_provenance.py`'s `CITATIONS`
table, resolved by quoted text, so the claim that they gate the row is checked
rather than asserted — and `check_page` requires this tool's sibling write-ups
to name every file they cite, which is why
`windows/tools/gpu_block_watch.py` is now named in
`0751-mark-provenance-shapes.md`'s "The committed fixtures" section.

**None of this says a capture should have had marks.** A capture legitimately
has none, which is the whole reason the class is a class rather than a defect
list.

## What the index records, and what it deliberately does not

`evidence/README.md`'s reason column says **what each file is and that no mark
was placed in it** — not which command produced it. That distinction is the
calibration rule applied to this table rather than stated about it:

**No mark-free capture under `evidence/ec-watch/` records the flags it was
taken with.** The one capture that does is a mark-bearing one:
`2026-09-24-06c2-06db-perturb-linux.csv`'s `#` header says its `MARK` rows
"are stamped by `--auto-mark` … and `--mark-input /dev/input/event7`", and its
sibling `2026-09-24-06c2-06db-suspend-linux.csv` says a stdin `MARK` and
`--auto-mark` were used. Nothing says the same for the eight with none —
`grep -l -- '--mark\|--csv\|--auto-mark' evidence/ec-watch/*` returns only the
perturb capture. So "taken without `--mark`" would be a claim about a command
nobody wrote down, and it has two readings the file cannot separate: the flag
was not passed, or it was and no label was typed. `ec_watch.py`'s
`Marker._loop` blocks on `sys.stdin.readline()` and returns on EOF, so a run
with the flag and nothing typed produces exactly the file a run without it
produces. The table therefore records the mark count and the file's shape, and
a reader who needs the command has to ask the person who ran it.

**That leaves the four oldest captures with a different reason again, and the
table keeps it distinct.** For the `2026-09-18-*` and `2026-09-23-*` files the
gate is not the explanation, because there was no row for it to gate:
`eb495de3` ("record 0751-isolation marks in ec_watch's csv", 2026-09-23 18:41)
added `CsvSink` and the `ts,MARK,,label` row to `windows/tools/ec_watch.py`,
and before it the only mark handling was a `print(f"--- {now()}  MARK: {label}
---")` to stdout. Each of those four files' last row precedes that commit —
`22:59:55` and `23:05:13` on the 18th, `18:00:29` and `18:00:06` on the 23rd —
so no flag and no typed label would have produced a row in them. That is a
stronger statement than "taken without `--mark`", which leaves open that a
label could have been typed: for these four there was no row to type one into.
The tree already recorded it for two of them, in
`probe-log-capture-conversion.md`'s "The two older captures, and what a
refusal reads like" ("predate the `MARK` row"); the commit date carries the
other two. `ec/tools/ec_timer_capture.py` entered the tree on 2026-09-24 and
wrote none of the four.

This is why the classes get different cells rather than one merged sentence.
"The row did not exist yet" and "the flag was not passed" are each true
statements about why there is no `MARK` row here, and a reader told only the
second would go looking for a run to redo.

## What the check is for: a recorded reason, not marks

`ec/tools/check_capture_marks.py` holds `evidence/README.md` to one row per
committed `evidence/ec-watch/*.csv`, with the file's `MARK` row count and,
where it is zero, a reason. Four refusals, each a different mistake:

- **a capture with no row** — nothing records whether a timing claim over it is
  mechanical or inferred;
- **a count that disagrees with the file** — both numbers are named, so the
  staleness is visible in whichever direction it runs;
- **a `0` row with an empty reason** — the count is right and the reader still
  cannot tell why the absence is what it is. This is what makes the count
  column worth having: a checker holding counts alone would pass a corpus that
  says nothing;
- **a row for a file that is not on disk** — a renamed or dropped capture leaves
  a claim about a file nobody can open behind.

**The reason cells are not free text the check judges.** They are text a human
writes, and the check holds only their presence, so what they say is the
author's claim and not a checked fact. That is why the table's cells describe
the file's shape rather than the run's command line.

**A `.txt` capture is outside the rule by construction** — the scope is
`*.csv` — and is reported in the census line as out of scope rather than passed
over in silence, so "outside the rule" and "checked and conformant" do not read
the same. `check_capture_claims.py` reports a skipped `.txt` capture for the
same reason.

## The calibration this rests on

- **"Not found by this method", never "absent."** A file holding no `MARK` row
  is a file this census finds no mark in. That is not a claim about the
  machine, and nothing here is evidence that a mark could not have been taken —
  only that none was written.
- **The population is named as what it is.** Two committed directories, named
  in the output. "0 files with no marks" is a count over those two and never a
  census of every capture that exists anywhere.
- **The `check_page` boundary is named, not assumed.** That check holds the
  write-ups to the tool's citations; it holds nothing about the prose in this
  file, and nothing here is a claim about the firmware. No `status:` in
  `ec/annotations/registers.yaml` moved, no register was read, and no capture
  was taken.
- **Re-taking any of these captures with `--mark` needs the physical machine.**
  That is the actual fix for the underlying gap and it is not this change. The
  reason column is what makes the absence legible until then.

## What is not here

- **The writers were not changed to default `--mark` / `--auto-mark` on.** That
  is a behaviour change to tools that only run on Windows, and not asked for.
  The gates are recorded as cited facts instead.
- **The check is not wired into a gate.** `agent-gates.sh` is template-copied
  from `ElDavoo/agent-pipeline` and a line there is an upstream change; the
  suite needs no wiring, since `tools/run-tests.sh` finds it by `find`. The
  house shape for gating it is a prepared `docs/ci/agent-gates-*.patch` plus a
  row in `tools/test_agent_gates_patches.py`, and that is its own call.
- **The three unindexed `2026-09-18-*` captures got their index entries**, which
  is the third item the issue asked for. Their entries say what each file is and
  name its mark situation; the findings they are cited from are
  `docs/findings.md` §4g, and nothing there was edited.

## Reproduce

```console
python3 ec/tools/measure_mark_provenance.py           # both classes, per root
python3 ec/tools/check_capture_marks.py --check       # the index against the files
bash tools/run-tests.sh ec/tools                      # the suite, no wiring needed
```

Offline throughout: no EC, no laptop, no Windows machine, no capture taken, no
register read, no mark typed. The census is a count over committed files and the
check is a comparison between a markdown table and those same files.