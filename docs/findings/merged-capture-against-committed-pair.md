# The two committed sweep captures are refused for one address, and that address is the free-running counter (issue #1452)

[`grader-merged-capture-sources.md`](grader-merged-capture-sources.md) closed with
a claim about itself it had not checked: "Nothing here has been run against a
committed capture", and a two-file merge described as one command a person at
the machine can run. That command needs no machine. `grade_timer_sweep.py` is
offline, both captures are committed, and the run reads two files and stops.
This file is that run.

**Offline throughout.** No EC image is opened, no register is read back, no
suspend happened and no laptop was involved. Both captures are committed files
under `evidence/ec-watch/`; reading them is the whole method. Nothing here
re-verifies §4 of
[`xdata-06c2-06db-sweep.md`](../hardware-tests/xdata-06c2-06db-sweep.md), the
published 0.997 s period, or any per-byte level in
`ec/annotations/xdata-06c2-06db-timers.md` — a refusal on two headers cannot
move a claim those make about the sweep.

## The command, and what it printed

```console
$ cd ec/tools
$ python3 grade_timer_sweep.py \
    ../../evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv \
    ../../evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
```

**Exit 1, nothing on stdout, one sentence on stderr** naming exactly one
disagreement:

```
2 captures disagree about a figure a merged run can only take from one file, so no run was built: the `# baseline` level of 0x06D6 is 0x04 in '../../evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv' and 0x03 in '../../evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv', and one of them would have been reported as the level it held at, over a span that includes the other file. `load()` merges the rows of every file it is given, so there is no report of this run that can print both. Grade them one at a time, or re-take them so that they agree.
```

The path spellings are the ones the command line carried. They are the
`../../evidence/...` a reader gets from `ec/tools`; nothing is rewritten.

## The disagreement is real, and it is one address

Both files name the same 35 addresses in the same order, and both state the
same `# interval 0.01s`. So the interval clause has nothing to fire on and the
**level** clause fires alone — which is what the sentence says, and is the
discriminating detail: this is a refusal about a level, not about the pair.

Every address the two files give a `# baseline` level for agrees between them
**except `0x06D6`**:

| | `2026-09-24-06c2-06db-suspend-linux.csv` | `2026-09-24-06c2-06db-perturb-linux.csv` |
|---|---|---|
| `# baseline` timestamp | `21:33:45.873+02:00` | `21:18:30.366+02:00` |
| `0x06D6` level | `0x04` | `0x03` |
| `0x06D6` change rows | 1454 | 3706 |

So the two captures disagree by one step of one byte, taken 915.507 s apart,
and the run was refused over it. `0x06D6` carried 1454 rows in the suspend
capture and 3706 in the perturb capture, which is the shape of two sweeps of
different lengths rather than two views of one.

**The control is what pins the refusal to the disagreement.** The same two
committed files, copied and with `0x06D6`'s `# baseline` token made equal —
one token on one line, no timestamp and no row touched — grade, and exit 0:

```console
$ python3 grade_timer_sweep.py /tmp/…/suspend.csv /tmp/…/perturb.csv
capture: /tmp/…/suspend.csv, /tmp/…/perturb.csv
span 1072.671s (the union of the 2 captures given, which none of them covers), 5249 change rows, sample interval 0.01s (stated by 2 of 2 files), 35 addresses watched
```

The union clause and `stated by 2 of 2 files` are the two labels
`grader-merged-capture-sources.md` added, both reaching the report. So the
refusal is pinned to `0x06D6`'s level and not to being handed two captures:
the moment the two files agree about it, the same pair grades.

## The refusal is correct here, and that is the finding

`grader-merged-capture-sources.md`'s open question asks about a pair of
captures of **one** sweep either side of a suspend. These two are not that
pair, and the write-up says so itself:

- §4a and §4b of
  [`xdata-06c2-06db-sweep.md`](../hardware-tests/xdata-06c2-06db-sweep.md) are
  **two different runs ~15 minutes apart with four AC/key/lid actions between
  them** — AC out, AC in, one Fn power-mode key, lid closed and opened — and
  §4a's baseline differs from §4b's for the same reason `0x06D6`'s does here.
- The suspend happened **inside the suspend capture**, as a gap in one file
  with a `resumed` mark beside it. It is not a boundary between two files.

So this is "a merge of the wrong thing", and the tool refused it. **No defect
is shown.** What the run establishes is narrower and worth having: the merged
path's refusal behaves as designed against a real pair of committed captures,
and the design refuses on the level rather than on the interval, which is the
part a reader would have had to take on trust.

## Why `0x06D6` is the address that refuses, and why it is not a bug

**`0x06D6` is a free-running ten-step counter, so its baseline level is a
phase.** §4 of
[`xdata-06c2-06db-timers.md`](../../ec/annotations/xdata-06c2-06db-timers.md)
is explicit about the shape: a non-zero value is decremented at `0x806C` and
the routine returns at `0x8074`; a zero value is loaded with `9` at `0x8075`
and stored at `0x8077`, and the sweep continues. The reload is stated by the
code, not supplied by a reader, which is why it is legible as a period at all.

That makes the correction the issue's framing needs. `0x06D6` is **not** the
one byte whose baseline *cannot* agree between two captures taken at unrelated
times — it is the one whose baseline is least likely to. With ten possible
values, two captures that start at unrelated times agree **one time in ten**,
not never. The clause firing here is a consequence of that design rather than
a fault in it, and the next reader should expect it to fire on most real
two-file merges of this sweep: any pair taken apart in time will put `0x06D6`
at a different step unless it happens to land on the same one.

The other 34 are not free-running, and that is what keeps their levels stable
across unrelated times. Most are countdowns that ran down and held at `0x00`;
`0x06D9` is the exception among those, holding at `0x03` for both runs for the
reason §4 of the sweep procedure gives. The rest are the gate and state bytes
the sweep only reads — `0x0440`, `0x0480`, `0x0490`, `0x05F0`, `0x05F1`,
`0x04FE`, `0x0498` — and `0x0751`. Some of those *did* move during §4a's four
operator actions, which is the point: a byte moves when something asks it to,
so its level at the next unrelated start is the settled one again. `0x06D6`
moves on a timer with nobody asking, which is why its level at an unrelated
start is a fresh phase. That asymmetry is why one address carries the whole
refusal.

**No residue is derived from the gap, deliberately.** The two `# baseline`
timestamps are 915.507 s apart, which against the sweep's published period
pins the number of passes between them to a band of some tens rather than to a
value — and §4b of the sweep procedure already establishes that the rate does
not hold constant across a suspend. A residue fits inside that band and
nothing in these two files narrows it. The disagreement is reported as
measured; what it says about pass counts is left to whoever can measure the
gap directly.

## What a real merged-run instance would take

Nothing here needs the machine, and **that is what this file corrects**:
`grader-merged-capture-sources.md` described the two-file case as work for "a
person at the machine", and on this evidence it is not one.

A real instance of the merged path needs **two captures of one sweep, taken
either side of a suspend**: same `--interval`, the second capture's
`# baseline` stamped at its own t0 the way `ec_timer_capture.py` stamps it,
and the sweep's rate expected not to hold across the gap. That is a hardware
run — it needs a laptop, a real suspend and an operator — so it is a separate
issue and not this one. It depends on this measurement in one respect only: the
refusal's behaviour on a genuine pair should be measured before any report
shape is designed around the merged path, and this file is the first evidence
of what that behaviour is on a pair that should refuse.

The committed `evidence/ec-watch/` set holds no such pair, and §2 of the sweep
procedure is what settles it: every sweep capture there is its own
`ec_timer_capture.py` invocation, with its own `--seconds` and `--interval`.
Their wall-clock windows do not touch — the last of the three earlier ones ends
at 21:00:08, §4a's runs 21:18:30 to 21:24:39 and §4b's 21:33:45 to 21:36:23 —
so no two of them are one sweep seen twice, and the merged-run path **still has
no committed instance that is not a refusal**. A capture being shorter than the
`--seconds` it asked for does not make it half of another: **§4a's perturb
capture is SIGINT-stopped at 369.5 s rather than the 600 s it requested**, by
design and with its `# ended` line intact (the sweep procedure's §2 says so at
the capture, and its §4a at 369.5 s), and its last data row is 9.1 min before
§4b's first. It is one arm that was cut short on purpose, not the first half of
a longer sweep.

§4b's suspend capture is a single file whose gap the `resumed` mark already
handles. Every case in `ec/tools/test_grade_timer_sweep.py` besides this
suite's is therefore still constructed.

## How to re-check this

```console
cd ec/tools
python3 grade_timer_sweep.py \
    ../../evidence/ec-watch/2026-09-24-06c2-06db-suspend-linux.csv \
    ../../evidence/ec-watch/2026-09-24-06c2-06db-perturb-linux.csv
python3 test_grade_timer_sweep.py
```

**The evidence is the behaviour, not the pass count.** The command above exits
1 with an empty stdout and the one sentence quoted here; the graded control
exits 0 and its header carries the union clause and `stated by 2 of 2 files`.
`CommittedPairAgainstTheSuite` in that file holds the exit code, the address
and both values, the absence of the interval clause, the absence of every
other address from the sentence, and the control beside them. Nothing here
needs Ghidra, the Windows stack, or anything
`.github/actions/project-setup` installs beyond Python.
