# `0x0456` bit 6: which divisor does `store_scaled_quotient_0449` use, and does bit 7 move?

**Status: not run (issue #174).** This procedure was written by the pipeline
for a human at the physical GM7MG7P. No laptop and no Windows machine is
reachable from the runner that wrote it, so nothing below has been observed:
no register has been read back, no GPU state change has been made, and no
result is recorded anywhere in this repository. The instrument
(`../../windows/tools/system_id_probe.py`) and its offline checks are
committed; the reading is not. §7 says what a result has to say, and
`SYSTEM_ID` in `../../ec/annotations/registers.yaml` stays
`present-untested` until a human runs this and commits the capture.

There are two questions here and they are **independent**: the bit-6 half
needs no state change at all, and the bit-7 half is a separate pass over the
same loop. Do the bit-6 block first — if it goes wrong, the bit-7 block's
result is harder to read against a model that is already failing.

**This file is the reference; the tool is the half that moves.**
`system_id_probe.py` defaults to §3's cadence and the six addresses §3 names,
and the two are kept in step the way
[manual-fan-ctrl-0751-isolation.md](manual-fan-ctrl-0751-isolation.md) §3 and
its probe are. Neither is graded by a script, and the tool emits no status
and no verdict.

## 1. The question

`0x0456` is `SYSTEM_ID`. Upstream calls it `EC_ADDR_SYSTEM_ID` and reads bit
7 as `HAS_GPU` before exposing `GPU_TEMP` and `NVIDIA_CTGP_CONTROL`
(`uniwill-acpi.c:2820` and the `BIT(7)` at `:92`, at the ref quoted in
`../../ec/annotations/xdata-0400-045f.md` §9). The EC image has a consistent
shape and nothing more: of 12 sites, 9 are direct reads and nine of *those*
are bit tests — bit 7 at bank0 `0x8C69`/`0x93F4`/`0xC26E`, bit 6 at bank1
`0xF3C9`, bit 5 at bank0 `0xB38E` and behind `anl a,#0xe0` at bank1 `0x83E5`
— while the three writers assemble a capability byte, clearing bits 4-5 at
bank0 `0xAD65` and setting bit 6 then bit 7 at bank0 `0xDA81`. Bits 0-3 are
never touched. Upstream's bit layout is cited; it is not this repository's
finding, and §9 of that file already calls the `HAS_GPU` reading "a plausible
reading of a consistent shape, nothing more".

### The bit-6 half

Bit 6 is the better-defined one because the firmware uses it in a way that
leaves an arithmetic trace. `store_scaled_quotient_0449` (bank1 `0xF3D7`,
`../../ec/decompiled/bank1/F3D7.asm`) branches on **R7**, and the two arms are:

- **R7 == 0** — R3 = `0x64` (100), R4 = 0, read the pair at `0x0434`/`0x0435`,
  divide, write the quotient's **low** byte to `0x0449`.
- **R7 != 0** — call `0xF3C9`, which sets R3 to `0x22` or `0x44` from
  `0x0456` bit 6, R4 = 0, read `0x060C`/`0x060D`, mask the high byte with
  `0x03`, multiply the 16-bit value by 10, divide, write the same byte.

> **Correction (2026-10-03, issue #358).** The two bullets above originally
> said **high** byte, and that was wrong. `0xA5E6`'s dividend shift at
> `0xA5EE` touches `R1` before `R2`, and its epilogue at `0xA613` copies `R0`
> into `R1`, so `R1` holds the quotient's **low** byte and `0xF3D7` stores
> `R1`. The wrong reading is retracted, not deleted, and the derivation is in
> [`a5e6-r1-is-the-low-byte.md`](../../docs/findings/a5e6-r1-is-the-low-byte.md);
> `ec/tools/a5e6_quotient.py` establishes it by executing the committed
> listing against an independent model. The probe's arithmetic and its offline
> checks were corrected in the same pass.

R7 is set nowhere in that listing or in the `0x198A` trampoline it calls, so
**the run cannot observe which arm ran — it derives it.** For each sample,
`system_id_probe.py` computes what each arm would have written from the other
five bytes and checks that against the `0x0449` actually read. An arm that
reproduces the byte is an arm the sample is *consistent with*, which is a
weaker thing than having watched it run, and §5 says so again where a reader
needs it.

The bit-6 test is then not a pass/fail but two numbers side by side: the
divisor each matching `0x060C` sample implies, and what bit 6 said it should
have been. A sample that reproduces under `0x22` while bit 6 is clear is the
contradiction, and it is a per-sample observation that a single pass/fail
would have swallowed.

### The bit-7 half

Upstream's reading is that bit 7 tracks whether a dGPU is present. This
procedure does not test that; it records **whether bit 7 moves across whatever
GPU state change this machine actually offers**, and which changes it offers.
If it offers none, that is the recorded result and the block is marked as
such — per `../../CLAUDE.md`, an honest negative is a result, and leaving the
question open because no action was found is not.

This half bears on issue #104 (upstream prep for the capability bits). **If
bit 7 turns out not to be `HAS_GPU` on this board, that correction belongs in
this repository's prep patch for #104** — never as a `gh pr create` against
`Wer-Wolf/uniwill-laptop` or `tuxedo-drivers` from a stage here
(`../../CLAUDE.md`, "Nothing gets opened in another repository without
explicit approval"; issue #10 tracks that).

## 2. Before you start

- Windows, Control Center 3.1.39.0 installed, `ecrw.py`'s driver path
  working (`python windows\tools\ecrw.py read 0x0456` should print a value).
- **On AC for the whole run**, for the reason
  [manual-fan-ctrl-0751-isolation.md](manual-fan-ctrl-0751-isolation.md) §2
  gives: the vendor rewrites a bundle of bytes on every AC ↔ battery
  transition, and a transition mid-window would be a state change the test did
  not ask for. This is a read-only test, so nothing here can be blamed on a
  write.
- A way to change GPU state, or a way to record that you could not find one.
  §3's bit-7 block has a table; fill the availability column in before you
  start the block, not afterwards from memory.
- Record the starting value of all six bytes and the machine's power and GPU
  mode as the vendor UI reports them, in the snapshot style of
  `evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`.

### Safety

**This test writes nothing.** There is no `--i-mean-it` gate, no restore step
and no original value to record, because there is no write. The only hazard
is the read side, and it is the one
[manual-fan-ctrl-0751-isolation.md](manual-fan-ctrl-0751-isolation.md) §2
warns about: **do not sweep the fan-tach bytes `0x0460-0x046F`** (issue #94).
`system_id_probe.py` refuses any address outside `0x0400-0x045F` ∪
`{0x060C, 0x060D}` at argument-validation time, before the EC is opened, so
a `--start` that walks into the next page is stopped by the tool rather than
by this paragraph. That is why the guard is in the tool: a range flag is not
prose.

**Six ECRR reads per sweep.** `ecrw.Ec.read` (`../../windows/tools/ecrw.py:135`)
is one `ECRR` `DeviceIoControl` per byte with nothing between calls, and
`../related-projects.md` records the same mechanism stalling the fans on a
sibling board, where the OEM software and `uniwill-laptop` sleep 6 ms after
every EC access, and says to avoid bulk sweeps under load. Six reads a sweep
against the 206 `../../windows/tools/manual_fan_ctrl_probe.py` already sweeps
under load is much less traffic, and **"much less" is not a safety
argument.** There is no safe interval derivable without the driver and the
machine (#94 is the open work, and nothing in this repository measures one).
The `--interval 0.5` below is §3's starting point and nothing more. If the
fans audibly change during a block, stop, raise the interval, and redo the
block.

## 3. The run

Two blocks, run separately, in this order. Keep the CSVs separate: they are
different questions, and the marks are what say which is which.

### 3a. The bit-6 block

Nothing is changed. The block exists to give the arithmetic a steady window to
be checked against, and the **control arm** — the window between the first
two marks, in which you do nothing at all — is what makes any movement in the
later window attributable to something rather than to ambient drift. It is not
optional and it is not a formality; §4.1 says what it is for.

```console
rem  <date> is that run's YYYY-MM-DD. §6 names the finished files the same
rem  way, so following this list produces the §6 set with no rename step.

rem  --- 0. snapshot, read-only ---
python windows\tools\ecrw.py read 0x0456
python windows\tools\ecrw.py read 0x060C
python windows\tools\ecrw.py read 0x060D
python windows\tools\ecrw.py read 0x0449
python windows\tools\ecrw.py read 0x0434
python windows\tools\ecrw.py read 0x0435

rem  --- 1. start the probe; type a label + Enter to stamp a mark ---
rem  ---    --interval 0.5 is a starting point, not a validated-safe value;
rem  ---    see the pacing note above before leaving it there ---
python windows\tools\system_id_probe.py --seconds 300 --interval 0.5 ^
       --mark --csv <date>-system-id-0456-bit6.csv
```

With the probe running:

1. mark `block start`.
2. let it settle ~30 s. mark `control arm end`.
3. **do not touch anything for ~120 s.** mark `steady window end`. This is the
   control arm: if `0x0449` or the divisor inputs move here, that movement is
   ambient and every later window is read against it.
4. watch ~60 s. mark `block end`.
5. Ctrl-C. The probe prints its per-arm counts and the implied-divisor table,
   and lists its marks — the last label in that list is the last mark the
   capture has. **A blank press is not a mark**: the probe records nothing for
   one, prints a line saying so, and asks again, so an accidental Enter cannot
   put a label nobody typed into the capture. If a press is refused, the label
   you meant is still the next thing to type and the mark it takes is the same
   number.

`--seconds 300` leaves room for what this section mandates (~30 s settle +
~120 s hold + ~60 s watch ≈ 210 s) plus four marks typed by hand. A block run
as written must not run its last mark past the end of a capture, and **a mark
after the probe has exited is written nowhere.** The check is mechanical:
the probe prints every mark it recorded when it stops, so if the last label
is not `block end` the block is short one. Redo it.

Do the block at least once at a **different** battery state each time — once
discharging and once charging, say. Arm A divides battery current by 100, so
a run in which the pack never moves gives that arm a single input value and
nothing to divide. That is a design note, not a requirement: one block is a
result, and §5's first bullet is the honest reading of it.

### 3b. The bit-7 block

The same loop, and the operator performs each GPU state change the machine
offers, marking each one. **Record availability as you go** — a row marked
"not available on this machine" is a result, and it is the row that makes
"no way to change GPU state" a finding rather than a gap.

| candidate action | available here? | mark label if you do it |
|---|---|---|
| Control Center GPU-mode switch (Optimus / discrete only) | | `GPU mode -> discrete` |
| suspend / resume | | `suspend/resume` |
| driver reload, `nvidia-smi -r` | | `driver reload` |
| Fn-key power-mode cycle | | `power mode -> N` |

```console
python windows\tools\system_id_probe.py --seconds 300 --interval 0.5 ^
       --mark --csv <date>-system-id-0456-gpu-state.csv
```

Mark `block start`, let it settle ~30 s and mark, then work down the table:
perform the action, wait ~30 s, mark, move to the next. Leave ~60 s of quiet
at the end and mark `block end`. **If no row is available, run the block
anyway** — a settled, marked, empty window is the negative result, and it
costs two minutes. A `suspend` while the probe is running will drop the ECRR
handle; if the probe dies on resume, that is a finding too, and the surviving
rows up to it are still a capture.

`--mark` is what makes the CSV readable afterwards. With `--csv` each mark is
written into the capture itself as a `ts,MARK,,label` row, so the CSV is
self-contained — type what you just did as the label rather than keeping the
timing in separate notes. The per-sample rows carry all six bytes plus the
branch the arithmetic placed them on, so the CSV is the raw record and the
console lines are a convenience.

**The labels in §3 and §3b are free-form prose by design, and this tool takes no
`--label-vocab` to check them against.** `ec_watch.py` has one, and it refuses
a label the 0751 grader cannot read — but every label this procedure mandates
(`block start`, `control arm end`, `steady window end`, `block end`,
`GPU mode -> discrete`, `suspend/resume`, `driver reload`, `power mode -> N`)
is one that check would refuse, because none of them leads with a form in the
grader's `MARK_FORMS`. Nor is there a grader waiting on the result: as the
paragraph at the top says, neither this probe nor its output is graded by a
script. So there is nothing to check a mistyped label against, and a check that
could only refuse would cost you the labels this procedure tells you to type.
Write the label you would want to read in §4. `ec_watch.py`'s prompt has the
same rule for a blank press, and
[system-id-probe-mark-labels.md](../findings/system-id-probe-mark-labels.md) is
why.

### 3c. What neither block does

There is no restore, because nothing is written. There is no
`ec_watch.py --dump` pair, because the question is not whether a byte kept a
value — every sample in the CSV has all six bytes, which is a wider read than
any dump pair. And there is no service-stopped second pass as §3a of
[manual-fan-ctrl-0751-isolation.md](manual-fan-ctrl-0751-isolation.md) has:
with the vendor service stopped, `0x0449` would stop being rewritten and the
arithmetic would be comparing against a stale byte. **Run both blocks with the
Control Center service running** and note that you did.

## 4. What to read off

1. **The per-arm counts, and the control arm beside them.** The probe prints
   how many of the sweep's samples each arm reproduced, plus `both-arms` and
   `unexplained`. Read the control arm's numbers first: it is the window where
   you did nothing, so whatever it shows is the baseline the steady window has
   to beat. A pattern that is identical across the two is drift, not a
   branch.
2. **The implied divisor against bit 6.** The probe prints, per divisor, how
   many `0x060C`-arm samples imply it and how many of those bit 6 agreed with.
   This is the bit-6 answer and it is a count, not a verdict. Read it
   alongside §5's fourth bullet before drawing anything.
3. **Every `unexplained` and `both-arms` sample, with its raw six bytes.**
   These are printed as they happen and are in the CSV's `branch` column.
   They are the interesting rows, not noise: they are where the model and the
   machine disagree, and they are the ones a follow-up has to explain.
4. **The `0x0456` bit-7 trajectory against the marks.** The probe prints a
   line per bit-7 transition with its timestamp, and a count in its summary.
   Read it against §3b's marks: which transitions fall between `block start`
   and the mark for an action the table says you performed. Bit 7 moving
   across a GPU state change is an observation about that change; bit 7 not
   moving is an observation about the window, and §7 says what that is and is
   not worth.
5. **Which of `0x060C`/`0x060D` and `0x0434`/`0x0435` actually moved.** The
   probe's CSV has every sample, so a run where one input is flat is visible
   in a handful of seconds of `sort`/`uniq` over the `branch` column. A run
   whose inputs never move cannot distinguish the two arms from each other and
   says so; that is worth knowing before §7.

## 5. What this cannot settle

- One machine, one firmware version (`GMxMGxx_11.800`). Nothing here
  generalises to sibling boards; see `../related-projects.md`.
- A window is a window. A byte that does not move in a 60 s window may still
  move at the next suspend, AC transition or EC reset, and a bit that does not
  move across the actions this machine offers may track something else
  entirely.
- **The branch is derived, not observed.** The probe computes what each arm
  would have written and compares; it does not know what R7 held. A sample the
  arithmetic places is a sample the arm is *consistent with*, which is a
  necessary condition and not a sufficient one — a third writer of `0x0449`,
  or a different code path, would produce the same reading. **R7's origin
  stays unestablished by this run**, and finding the caller that sets it is a
  separate static question.
- **The one committed capture is no longer evidence against the model, and
  this test still does not decide which arm ran.** Under the reading this
  procedure originally carried, both arms returned `0x00` for any plausible
  input: `anl 0x02,#0x3` capped arm B's dividend low enough that its quotient
  never reached the stored byte, and arm A's division by 100 needed 25600 mA
  to leave `0`. In `evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv`
  the byte `0x0449` moved 238 times across the range `0x22` to `0x5A`, so under
  that reading none of its values was reachable at all. That was the model
  being wrong, not the machine, and the correction is issue #358.
  **Reachability is not a match**: pairing that capture nearest-in-time does
  not align two bytes that were not written at the same instant, so it
  establishes that the observed values are *possible* under the corrected
  reading and nothing about which arm produced any particular sample. The
  capture carries no `0x0456`, `0x0434` or `0x0435`, so it cannot exercise the
  bit-6 half either way, and **a run that comes back mostly `unexplained` is
  still a result** — now a question about which arm ran, rather than a
  question about which byte the arithmetic returns.
- `ec/tools/ecmem.py`'s record that `0x456` reads were cross-checked against
  the `uniwill-laptop` regmap debugfs dump is **not** a result of this test.
  Two software paths agreeing on a read is not a behavioural test, and
  `../../ec/annotations/xdata-0400-045f.md` §9 already says so; do not offer
  it as one.

## 6. Where the output goes

Name the files the way the existing captures do, so a reader can pair them:

```
evidence/ec-watch/<date>-system-id-0456-bit6.csv
evidence/ec-watch/<date>-system-id-0456-gpu-state.csv
evidence/ec-watch/<date>-system-id-0456-snapshot.txt
```

`<date>` is that run's YYYY-MM-DD. The two CSVs are one file per block and
have to be: they are different questions, and unlike the fan-ctrl procedure's
three watchers there is nothing to merge them across. The snapshot is the
human's, in the style of
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt` — date, AC or
battery, the six starting values, the Control Center service state, and for
§3b's block the availability column and which actions were performed. Add all
three to `evidence/README.md`, which is the index every findings claim cites
through.

`system_id_probe.py` reads none of the three afterwards: the summary it prints
at the end is the whole mechanical read, and the CSVs are what a later pass
would re-run it over. The rows are `ts,sweep,<six bytes>,branch,implied` for a
sample and `ts,MARK,,label` for a mark — the mark shape is
`ec/tools/grade_0751_isolation.py`'s and `ec_watch.py`'s, so a reader who has
met one has met both, and `grade_0751_isolation.py` will read the mark rows
if a future pass wants windowed arithmetic over them. It will not grade them:
the two captures have no `0x0751` in them.

The follow-on edits this run is for, named here so §6 of a future pass does
not have to re-derive them:

- `SYSTEM_ID` in `../../ec/annotations/registers.yaml` — the observed bit map
  in the note, and a `status:` move **only** on the terms §7 gives.
- The `0xF3D7` plate comment's bit-6 sentence, through
  `../../ec/annotations/ghidra-functions.csv` and a re-run. **Not** in
  `../../ec/decompiled/bank1/F3D7.c`, which is generated
  (`../../CLAUDE.md`, "The editable surface is the CSV, not the project").
  The same CSV row's "no entry in `registers.yaml`" clause is one of the seven
  stale plate comments `../../ec/annotations/xdata-0400-045f.md` §11 already
  records; fixing it properly is that file's rebuild follow-up, not this one.
- If bit 7 turns out not to be `HAS_GPU`, the correction goes into this
  repository's prep patch for #104. A stage here does not open a pull request
  against another repository under any circumstances.

## 7. What a result has to say

`SYSTEM_ID` moves off `present-untested` only on a behavioural observation,
not on a readback — `../../CLAUDE.md`, "a register write being accepted
(readback matches) is not evidence the EC acts on it". Concretely, and
scoped in words each time:

- **Bit 6.** `implied divisor` agreeing with bit 6 across the `0x060C`-arm
  samples is a statement about `0x0456` bit 6 and about
  `store_scaled_quotient_0449` at bank1 `0xF3D7`: *that bit selects the
  divisor, in the direction the listing reads*. It is **not** a statement that
  `0x0456` is a capability byte, and it does not upgrade the `HAS_GPU` reading
  — those are different bits and the bit-6 result says nothing about them. If
  the counts disagree, say that, and quote the disagreeing samples; the
  `unexplained` rows are usually the more informative half and a passing bit-6
  count beside a mostly-`unexplained` run is a result, not a success.
- **Bit 7, moving.** A transition that lands between `block start` and the
  mark for an action §3b's table says you performed is an observation that
  bit 7 tracks that action on this machine. Scope it to the action and the
  machine. It is not a statement that bit 7 *is* `HAS_GPU` — one transition
  across one action does not establish what the bit means, and upstream's
  name stays cited rather than supplied.
- **Bit 7, not moving.** A result about the window and the actions this
  machine offers, and **not** proof the bit is dead. `ramp_1804_1809_toward_0461_0469`
  (bank0 `0x8C46`, `../../ec/decompiled/bank0/8C46.asm`) reads bit 7 of
  `0x0456` to choose between `0x0461` and `0x0469`, so a second, fan-side
  reader exists and a still bit 7 is not a contradiction of anything. If the
  table in §3b came out empty, that is the headline: no GPU state change is
  reachable from this machine's software, and the question needs a different
  instrument, not a louder run.
- **Nothing matches.** A run that is entirely `unexplained` is a real result
  and goes into `evidence/` with what was seen. It says the model in §1 and
  this machine do not agree, and the next question is which of the two to
  re-derive — that is a new issue, not a reason to pick the
  confident-sounding phrasing. Mixed or ambiguous stays `present-untested`,
  and the capture is committed anyway. That is not a failed test.
