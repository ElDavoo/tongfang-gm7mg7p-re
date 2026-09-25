# Isolating `0x0751`: does the EC act on the power-mode byte alone?

**Status: run 2026-09-23 (issue #99); the prediction held.** This procedure
was written by the pipeline for a human at the physical GM7MG7P, and then run
in an interactive session on that machine. Writing `0x0751` alone to each of
`0xA0`/`0x00`/`0x10` moved nothing else — not the PLs, not the fan table, not
`0x07C6`, not the GPU bytes — confirming the static prediction that the EC
does not derive the bundle from the mode byte. The run used the equivalent
single-tool form `windows/tools/manual_fan_ctrl_probe.py` (which watches the
same addresses and self-restores) rather than the three-`ec_watch` form in
§3; the raw log is `evidence/ec-watch/2026-09-23-0751-isolation.txt`, and the
result is folded into `MANUAL_FAN_CTRL` in `ec/annotations/registers.yaml`.
The one part §7 leaves open — whether the fan-mode bits scale fan behaviour
along the unchanged curve — was **not** settled (the run was near-idle); the
fixed-load comparison below is still worth doing. Issue #122 tightened that
re-run: §3 now opens with an explicit no-op control arm and sweeps
`0x0400-0x045F` for the EC's own temperature bytes, so the PWM reading is
taken against a measured die rather than an assumed one.
`windows/tools/manual_fan_ctrl_probe.py` implements both, so the single-tool
form runs the tightened procedure in one console. The re-run itself is
still **not** done — it needs the physical machine. The rest of this file is
the original procedure, kept for that re-run and for anyone reproducing the
test.

**This file is the reference; the tool is the half that moves.** The two used
to carry different numbers — §3's ~30 s hold and `--interval 0.5` against the
probe's 20 s and a hardcoded 0.3 s sweep — which is the defect issue #146 is
about. The probe now defaults to §3's numbers and takes `--interval` instead
of hardcoding a cadence. Neither that nor anything else here makes an interval
safe: §3's pacing note is unchanged, and the §4.4 grading is still a human's
call. §3b is the other half of the reconciliation — what the single-tool form
does *not* do, and what a run using it must still do by hand.

## 1. The question

`docs/findings.md` §7 established that a power mode is a *bundle*: on every
switch the vendor service writes `0x0751`, PL1/PL2/PL4 at `0x0783-0x0785`, a
96-byte fan table at `0x0F00-0x0F5F` and, on AC, the GPU bytes
`0x0743-0x0746`. Because it always writes all of it, the capture cannot say
what the EC does with `0x0751` on its own.

That decides the size of a Linux `platform_profile` implementation. If
`0x0751` alone is enough, the driver is small. If it is not, the driver has
to replay the PLs and a fan table the way the vendor does.

The static half of the question is answered as far as a site scan can answer
it, in `../../ec/annotations/manual-fan-ctrl-0751.md`: none of the 29
reference sites carries a per-mode default into a PL register or loads a fan
table, and the EC's only found writer of `0x0783-0x0785` is gated on
`AP_OEM` (`0x0741`) bit 0 rather than on the mode. **That prediction is what
this test is for.** A static scan cannot see indirect access — §6 of that
file is a worked counter-example on the fan-table page itself — so "the
EC does nothing with the byte alone" remains a hypothesis until it is
watched.

## 2. Before you start

- Windows, Control Center 3.1.39.0 installed, `ecrw.py`'s driver path
  working (`python windows\tools\ecrw.py read 0x0751` should print a value).
- **On AC for the whole run.** The vendor rewrites the whole bundle on every
  AC ↔ battery transition, which would drown the thing being measured.
- A fixed CPU load you can hold for the entire observation window — the
  point is that the fan and package power have a constant thermal input, so
  any movement is the EC's doing and not the workload's. Start it before the
  first sweep and stop it after the last. It is also why §3 paces the
  watchers: this is the run with the most `ECRR` traffic of any so far, and it
  is the only one held under load.
- A way to read CPU package power (HWiNFO, or `windows/tools/` equivalents).
  Note it by hand at the times you mark; it is not in the EC sweep.
  Temperature is — §3's third watcher covers `0x043E`/`0x044F`, both
  `confirmed-working` in `../../ec/annotations/registers.yaml`.
- **`ec/tools/grade_0751_isolation.py`, where §3's commands can reach it.**
  The three watchers below carry `--label-vocab 0751`, and that flag makes each
  of them read the label vocabulary out of that one file before it starts: a
  watcher that cannot find it refuses, above the CSV and long above the EC, and
  the refusal names every place it looked. A checkout has it already. A
  directory of `windows\tools\` copied onto a Windows box needs a copy of that
  file in the same directory as `ec_watch.py`, or `--grader <path>` naming it
  — the search order, and what a present-but-broken copy does, are in
  [`ec_watch-marks.md`](../../windows/tools/ec_watch-marks.md).
- **Either grading workflow is supported, and both need the same file.** Grade
  at the machine by running §6's command there, or bring the ten files back and
  run the same command from a checkout: `grade_0751_isolation.py` is
  stdlib-only and reads files rather than the machine, so §6's CSV + dump set
  grades identically either way. What the checkout *is* needed for is the
  command lines as written — §3's `python windows\tools\...` and §6's
  `python ec\tools\grade_0751_isolation.py` are both repo-relative — so a
  staged directory has to type its own paths. The tool half of §3 is the part
  that now works either way; the grader bullet above is what makes it start.
- Record the starting value of `0x0751`, and the current mode as the vendor
  UI reports it. `evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`
  is the format to copy for the snapshot.

### Safety

Per the issue this came from: **write `0x0751` only, and only `0x00`, `0x10`
or `0xA0`** — the three values the vendor service itself writes, so nothing
here puts a value into the EC that it has not already seen many times.
Restore the original byte after every step. Do not write the PLs, the fan
table or anything else as part of this test; the whole point is that
`0x0751` moves alone.

Do not sweep the fan-tach bytes — see issue #94.

## 3. The run, one variable at a time

Repeat the block below once per target value, and keep the runs separate.
Each is: snapshot, start the watchers, no-op control arm, one write, wait,
restore, stop. The control arm is not the restore step, and it is not
optional — §4.4 says what it is for.

```console
rem  <date> is that run's YYYY-MM-DD, and <value> is the value under test in
rem  this block, lower case and without 0x -- a0, 00 or 10. §6 names the
rem  finished files the same way, so following this list produces the §6 set
rem  with no rename step. The three CSVs are one file for all three blocks,
rem  because ec_watch.py appends to a --csv file that already exists and the
rem  marks say which write each row follows; the dumps are not, so they carry
rem  <value> and block 2 cannot overwrite block 1's.

rem  --- 0. snapshot, read-only ---
python windows\tools\ecrw.py dump 0x0700 0x0100 ^
        > <date>-0751-isolation-<value>-before-0700.txt
python windows\tools\ecrw.py dump 0x0F00 0x0060 ^
        > <date>-0751-isolation-<value>-before-0f00.txt
python windows\tools\ecrw.py dump 0x0400 0x0060 ^
        > <date>-0751-isolation-<value>-before-0400.txt

rem  --- 1. start all three watchers (three consoles), with the load running ---
rem  ---    --interval 0.5 is a starting point, not a validated-safe value;
rem  ---    see the pacing note below before leaving it there ---
rem  ---    --label-vocab 0751 is what makes the prompt check each label
rem  ---    against the grader's own parse; without it a label it cannot place
rem  ---    is recorded here and costs the whole run at grading time ---
python windows\tools\ec_watch.py --start 0x0700 --len 0x0100 --seconds 240 --interval 0.5 ^
       --mark --label-vocab 0751 --csv <date>-0751-isolation-0700-07ff.csv
python windows\tools\ec_watch.py --start 0x0F00 --len 0x0060 --seconds 240 --interval 0.5 ^
       --mark --label-vocab 0751 --csv <date>-0751-isolation-0f00-0f5f.csv
python windows\tools\ec_watch.py --start 0x0400 --len 0x0060 --seconds 240 --interval 0.5 ^
       --mark --label-vocab 0751 --csv <date>-0751-isolation-0400-045f.csv

rem  --- 2. control arm: let all three settle ~10 s, mark each, then write
rem  ---    the value already there back to itself and mark that as a no-op ---
rem  mark each console: settled
python windows\tools\ecrw.py write 0x0751=0x<current> --i-mean-it
rem  mark each console: no-op wrote 0x0751=0x<current>

rem  --- 3. hold ~30 s, mark each, then the write under test, mark ---
rem  mark each console: held
python windows\tools\ecrw.py write 0x0751=0xA0 --i-mean-it
rem  mark each console: wrote 0x0751=0xA0

rem  --- 4. watch for ~60 s; mark again at the end ---
rem  mark each console: watch over

rem  --- 5. restore, and mark once more ---
python windows\tools\ecrw.py write 0x0751=<original> --i-mean-it
rem  mark each console: restored 0x0751=0x<original>

rem  --- 6. after all three watchers exit ---
python windows\tools\ecrw.py dump 0x0700 0x0100 ^
        > <date>-0751-isolation-<value>-after-0700.txt
python windows\tools\ecrw.py dump 0x0F00 0x0060 ^
        > <date>-0751-isolation-<value>-after-0f00.txt
python windows\tools\ecrw.py dump 0x0400 0x0060 ^
        > <date>-0751-isolation-<value>-after-0400.txt
```

`--seconds 240` leaves room for what this section actually mandates — ~10 s
settle + ~30 s hold + ~60 s watch ≈ 100 s — plus three `ecrw.py write`
invocations and six mark rounds typed by hand across three consoles, which is
eighteen presses between the watchers starting and stopping. The old 150 s
left so little that a block run as written could run its last mark past the
end of a capture, and **a mark after the watcher has exited is written
nowhere.** A block whose final mark lands late is void; redo it. The check is
mechanical, not a matter of remembering: `ec_watch.py` prints
`=== N sweeps over Ms` and then every mark it recorded when it stops
(`../../windows/tools/ec_watch.py:335`), so the last label in that list is the
last mark the capture has. If it is not the restore, the block is short one.

The check over the capture is the one that survives into the record, and
`../../ec/tools/grade_0751_isolation.py` now makes it: it groups the marks
into blocks — one per write under test, opened by the no-op control arm and
closed by the restore — prints an `intact` or a `VOID` verdict for each, and
exits non-zero if any block is void. It reads the CSVs rather than the
terminal, and that is not a preference: `ec_watch.py` appends a mark to its
own list and prints it whether or not the CSV sink is still open
(`../../windows/tools/ec_watch.py:211-214` against the close at `:330-332`),
so the last label on the screen can be one the capture never received. The
by-eye check above is still the fastest one to do at the machine; run the
tool over the committed CSVs as well, before they are filed.

**And it checks the marks themselves, per block and per capture, before it
prints a window.** A window is every change after a mark up to the next one,
and which mark that is comes from the timestamps alone. So a mark one console
missed — or that two consoles spelled differently — raises nothing: that
console's rows are still filed under whichever window their timestamps fall
in, and the other two consoles' marks usually cover for it, which is what
makes the failure invisible rather than what prevents it. Nothing in the
result ties those rows to the arm whose mark went missing, so a no-op arm can
read as quiet for want of a mark rather than because nothing moved, and the
run reports that in the same format as a result. So §6's "the marks in all
three CSVs must carry the same labels" is checked rather than written down:
every action recorded in every capture, every capture spelling it the same
way, and every block's last mark its restore *in each capture* — per capture,
because a console that recorded only one block would otherwise make every
block in the day look complete. A block that fails any of those has its
windows left out and the exit code is 1, with the census naming which capture
is short and what it costs. The by-eye check above cannot do this: it is one
terminal, and the question is about three of them.

The `0x0400-0x045F` watcher is the EC's own temperature reading: `0x043E` is
`CPU_TEMP` and `0x044F` is `GPU_TEMP`, both `confirmed-working` in
`../../ec/annotations/registers.yaml`. It stops at `0x045F` on purpose — the
fan-tachometer bytes (`0x0460-0x046F`, issue #94) start right after, and
reading those through `ECRR` stalled the fans on a sibling board
(`../../docs/related-projects.md`). Every other byte in the range is context;
§4.5 says what to do with it, and
`../../ec/annotations/xdata-0400-045f.md` says what each of them *is* — 46 of
the 96 bytes have an entry in `../../ec/annotations/registers.yaml`, which is
44 entered by the sweep plus the two that were already there, `CPU_TEMP`
`0x043E` and `GPU_TEMP` `0x044F`. Those 46 bytes are carried as 41 entries,
because five are entered as 16-bit pairs. The other 50 are named there as
deliberately not entered, and 46 + 50 = 96, so a row this run prints is either
nameable or accounted for.

**Three concurrent watchers put more `ECRR` traffic on the bus than any run
before this one, and this is the only one held under a fixed load.** The
arithmetic is worth having in front of you: `ecrw.Ec.read`
(`../../windows/tools/ecrw.py:135`) is one `ECRR` `DeviceIoControl` per byte
with nothing between calls, and `ec_watch.py` reads every address in its range
once per sweep (`addrs`, `../../windows/tools/ec_watch.py:257`) with
`--interval` slept between sweeps (`ec_watch.py:307`), not between bytes. So
one sweep of each of the three watchers is `0x100 + 0x60 + 0x60 = 448` ECRR
reads, all three running at once, for as long as the block runs.
**448 is what this section's commands above do today, and it is what the
numbers quoted in the tool's own docstring mean.** The commands have no
`--block`, and the flag is off by default: issue #147 added a four-bytes-per-
IOCTL path to `ec_watch.py` and `ecrw.py` and left the per-byte read as what
these watchers do. If a run is taken with `--block` instead, the same three
ranges are `0x100/4 + 0x60/4 + 0x60/4 = 112` IOCTLs — all three ranges are
whole numbers of aligned 4-byte blocks — and that is a *call count*, not a
statement that the traffic is safe: the path has never been run against the
driver, and the one comparison a human can make is written out in
`../../windows/tools/manual_fan_ctrl_probe.py`'s docstring. The tool's
`--watch-page` computes the same 448 and the same 112 from the same three
ranges (issue #666), so a reader meeting two 448s is meeting one figure. Quote
448 for the run as written, 112 only for a `--block` run, and neither as a
safety claim.
`../../docs/related-projects.md` records the same mechanism stalling the fans
on a sibling board, where the OEM software sleeps 6 ms after every EC access,
and says to avoid bulk sweeps under load — which is the condition this run
creates on purpose. Stopping at `0x045F` means this is not that stall, but it
does not make the traffic small.

**There is no safe interval to hand you from here.** How long one IOCTL takes
is not measurable without the driver and the machine, issue #94 is the open
work to make these tools safe by default, and nothing in this repo measures
it. So the `--interval 0.5` in the commands above is a starting point and
nothing more. If the fans audibly change during a block, raise it and redo the
block: this procedure measures fan behaviour, and a block that moved the fans
itself is worth less than no block.

`--mark` is what makes the CSV readable afterwards: without a timestamp for
"I wrote it now", a byte that moves 400 ms later and one that moves 40 s
later look the same in the log. With `--csv` it writes each mark into the
capture itself as a `ts,MARK,,label` row, so the CSV is self-contained — type
what you just did as the label — one of the six forms the block above names,
`rem mark each console:` under each round — rather than keeping the timing
in separate notes. **A blank line records nothing: the mark prompt says so and
asks again**, so there is no such thing as an unnamed mark in a capture
([`../../windows/tools/ec_watch-marks.md`](../../windows/tools/ec_watch-marks.md)).
Mark the same action in all three consoles within a few
seconds of each other; the grader treats marks less than five seconds apart as
one action, which is what keeps three consoles from reporting one write as
three windows.

**Those six forms are now load-bearing rather than illustrative.** Three of
them are actions and carry a value after `0x0751=`: `no-op wrote ...`,
`wrote ...`, `restored ...`. Three are **stage boundaries** and carry none:
`settled`, `held`, `watch over`. The grader reads the leading word to tell the
control arm from the write under test, reads the value after `0x0751=` to name
the block the window belongs to, and reads a boundary as a mark that opens a
window without a write behind it. It refuses a mark that is none of the six —
quoting them back, because a window whose opening mark cannot be placed is a
window it cannot say what it is a window of. **As of 2026-09-25 (issue #474)
pressing Enter on a blank line is no longer one way this happens by
accident**: the mark prompt in
`ec_watch.py` (`Marker._loop`) refuses the press, records nothing, prints that
it did, and asks again. It used to substitute `mark N` for the empty label —
the `ec_watch.py:119` this paragraph cited until now — and the substitution was
the wrong half of the answer twice over: it wrote a label no form can parse,
which `unplaceable_marks` treats as fatal for the whole run rather than for
one block, and it made a mark nobody had described read as a mark somebody
had. What still produces the shape by accident is a mistyped digit in one of
the three consoles, and nothing but the comparison catches it: the merge joins
the three labels into `wrote 0x0751=0xA0 / wrote 0x0751=0x10` and the window
opens on that, while the timestamps are perfectly happy because the write
really did happen between the two marks. **As of 2026-09-25 (issue #531) a
second way to produce that shape by accident is refused at the prompt too**:
§3's three commands above carry `--label-vocab 0751`, and the mark prompt then
checks each label against the grader's own `parse_mark` — the same predicate
`unplaceable_marks` applies — refusing a label it cannot place at all, quoting
these six forms back, and asking again, with the blank press's notice and its
`no mark N taken` counting rule. A mistyped `=`, or the `0x` dropped from the
address, is that case. **The mistyped digit just named is not**, and the
comparison above is still what is for it: `0x0751=0xA` parses as a value of its
own, as does a value this run never wrote, because a per-line prompt cannot
know which values the run means to write or what its actions should be. None
of this has been run at a machine — the check, the notice and the counter are
offline behaviour of the tool against a fake EC, and a human at the laptop is
the one who would see the new prompt.

**As of 2026-09-25 (issue #472) the three boundary rounds have a label and a
place in the block, and they are optional rather than required.** A boundary
carries no value, so it cannot name a block; it joins the one already open and
waits for the next write if there is none, which is what the control arm does
too. A block recorded with all six rounds therefore reads
`settle, control, hold, write, watch, restore` on the grader's `roles` line,
and `--block` selects all six of its windows rather than the three an older
capture carries. **What a block recorded without `watch over` costs is stated
here rather than checked.** A window is every change after a mark up to the
next one, so the end-of-watch mark is what closes the write's ~60 s observation
window: without it the write's window runs on into the `restored` write, and
§4.4's control-vs-write comparison is taken over a window that contains the
restore. The grader does not refuse that block — a three-mark capture grades
exactly as it always did, and every fixture under
`../../ec/tools/testdata/0751-isolation-run-*/` but the staged one is a
three-mark capture — and the `roles` line says so on its face: a block that
reads `control, write, restore` is a block whose write window ran into its
restore, and the reader is the one who knows whether that matters for the day.

Values to run, one block each: `0xA0` (Office), `0x00` (Gaming), `0x10`
(Turbo). Start from a *different* mode each time — writing Turbo's `0x10`
while already in Turbo tests nothing.

The control arm writes the byte back to the value it already holds, so it
leaves the mode you started in, and the rule above is what makes the two
capture windows comparable: the only thing separating the control's from the
write's is the write. Label it `no-op wrote ...` and not `wrote ...`; the
grader windows on marks, and a control arm that reads like the write under
test is indistinguishable from it. This is the arm the 2026-09-23 run already
had in a weaker form, where the fan duty at `0x075B`/`0x075C` (issue #123:
`MAIN_FAN_L_DUTY`/`MAIN_FAN_R_DUTY`) moved as much under the no-op as
under a real mode change — thermally, which is why the fan half of the
question is still open.

### 3a. Repeat with GCUService stopped

Run the whole of §3 a second time with the vendor service stopped
(`sc stop` on the Control Center service, confirmed with the vendor UI
gone). Two reasons, both from the issue:

- with the service running, anything you see could be the service reacting,
  not the EC. With it stopped, whatever moves is the EC.
- the service raises no event for a write it did not make, but it can still
  re-assert the whole bundle at the next AC or resume event. If the byte
  you wrote silently reverts minutes later with the service running and
  persists with it stopped, that is the explanation and it is worth having
  in the record.

If the day only allows two arms, repeat at least the Office-vs-Turbo pair
(`0xA0` and `0x10`) with the service stopped. That pair settles both reasons
above — neither of them turns on which value was written — and it is the
minimum issue #122 asks for. It is not enough for §7's `confirmed-inert`,
which names all three values, so a two-arm run closes the re-assert question
and leaves the three-value sweep open.

### 3b. What the single-tool form does not cover

`../../windows/tools/manual_fan_ctrl_probe.py` runs §3's no-op control arm, the
write, and the restore in one console, and its defaults now match §3's hold
and cadence. It is not the whole procedure, and four things a §3 run needs
that a probe run does not produce are worth writing down, so that "the probe
does §3" is not read as "the probe does all of this file".

- **§3a's service-stopped pass.** The probe's two arms are two writes; it has
  no way to be told the vendor service is stopped, and stopping it is a human's
  step. §3a's second pass, at minimum the Office-vs-Turbo pair, is still a
  separate run with the service down.
- **§4.5's package-power notes.** No EC byte carries CPU package power, so no
  sweep in §3 or in the probe can show it. Read it from HWiNFO by hand at each
  mark, whichever form the block came from. The probe prints the two
  temperature bytes because those *are* in the sweep; it does not substitute
  for the power reading, and §7 keys `confirmed-working` on either.
- **The dump pairs.** The probe writes no dump at all, so a probe run has
  none of the pairs §3's steps 0 and 6 take. §4.6 has nothing to read
  without the `*-before-0700.txt` / `*-after-0700.txt` pair — the question
  "does `0x0751` still hold your value at the end of the window" needs
  those two range dumps, and `--dump` in
  `../../ec/tools/grade_0751_isolation.py` is what reads them. The
  whole-block read needs all three pairs, the `0x0700` one, the `0x0F00` one
  and the `0x0400` one, given as `--dump-pair`; take the two `0x0F00` dumps
  and the two `0x0400` dumps as well, or those halves of the read are simply
  not there — §4.5's temperatures are in the `0x0400` pair and in neither of
  the others. A probe run answers §4.4's PWM comparison and nothing else in
  §4.

  **Correction (issue #476, 2026-09-25), leaving the sentence above as it was
  written.** It held while a probe run wrote no CSV. A `--csv` capture does
  carry §4.1's `0x0783`-`0x0785` and §4.3's `0x07C6` — both in the probe's
  `WATCH` — and the tool sweeps §4.2's fan table and the `0x0400-0x045F`
  temperature range whole, so a probe run answers §4.1 through §4.4 and lacks
  only §4.5's by-hand power readings and §4.6's dump pairs, as the two
  bullets above say. The one part of that four it does *not* answer whole is
  §4.4's whole-page arm, which the next bullet takes up — and that last clause
  is itself narrowed by the next bullet's correction, for a `--watch-page` run
  rather than a default one.
- **§6's ten files, all but three of them.** A probe run with `--csv` produces
  the three CSVs' content and none of the other seven: no dumps and no
  snapshot, so §4.6 has nothing to read as the bullet above says, and there
  is nothing to index in `evidence/README.md` under those names. The three go
  into **one** appended file rather than §6's three, and the grader reads
  that one file with no conversion — but the three CSVs under one name are
  not three ranges of equal coverage. §4.1's `0x0783`-`0x0785` and §4.3's
  `0x07C6` are in `WATCH`, and §4.2's fan table and the `0x0400-0x045F`
  temperature range are swept whole, so those two of the three ranges are
  covered as §3 sweeps them. The `0x0700` one is not: `WATCH` reads 14 of
  that page's 256 addresses (`0x0743`-`0x0746`, `0x0751`, `0x075B`,
  `0x075C`, `0x0783`-`0x0787`, `0x07C5`, `0x07C6`) and nothing else in the
  page, where §3's `--start 0x0700 --len 0x0100` takes all of it. So on that
  range §6's split is a coverage difference and not only
  `ec_watch.py`'s one-console-per-file shape: §4.4's instruction to keep
  reading the whole `0x0700-0x07FF` sweep, and the neighbourhood around
  §4.1's bytes that instruction exists for, are what a probe run does not
  reproduce. Three things follow for the record. The windowed §4.1-§4.3 read
  therefore applies to a probe capture, §4.4's whole-page arm of it does not,
  and §4.6 does not. And with one capture there is no other console for a
  mark to be missing from and no second spelling to disagree with it, so the
  grader's cross-console checks do not run — its
  census says so in as many words rather than letting one capture pass a
  check it never ran. Each probe run appends a *complete* block (control,
  write, restore), so a three-value session is three blocks in one file and
  `--block <value>` takes them apart as it does for a §3 day. The capture is
  then the run's own log, as 2026-09-23's was, and §7 still has no dump
  behind it.

  **Correction (issue #666, 2026-09-25), leaving the bullet above as it was
  written.** Its `0x0700` half still describes a **default** probe run, and
  what it says is still true of one: `WATCH` reads 14 addresses of that page
  and `--watch-page` is off. A run taken with `--watch-page` does reproduce
  §4.4's whole-page arm, in one console, by sweeping `0x0700-0x07FF` whole in
  place of `WATCH`'s 14 — §3's first watcher over the same three ranges the
  probe's other two already sweep, so the sweep is §3's own
  `0x100 + 0x60 + 0x60 = 448` ECRR reads, or `112` with `--block` (all three
  ranges are 4-aligned there, so 112 is exactly the `448/4`). It is opt-in for
  the reason `--level-block` is: the **default** footprint stays as committed,
  rather than moving under a flag nobody reading a run knows about. The
  committed `2026-09-23` run was not taken at that default: its own header
  lists `WATCH` plus the fan table and no temperature range, so it swept
  **110**, and `TEMP` only joined the set the next day, with #143. **206 is
  the current default, and no committed run was taken at it.** 448 is 2.2x
  that default and 4.1x the 110 the committed run actually swept, on the one
  run §3 holds under a fixed load with #94 still the open question of what it
  does to a fan. **Nothing in the page is written** — the only byte
  this tool writes is `0x0751` in `{0x00, 0x10, 0xA0}`, whatever else is
  swept, which is what makes the wider sweep the same kind of read as the
  narrow one. §4.6 is unchanged by any of this: the page arm produces no dump
  pair either way, and §3a's service-stopped pass, §4.5's by-hand power
  readings and §6's seven non-CSV files are as absent from a `--watch-page`
  run as from a default one.
  **The flag has never been run** — not against the vendor driver, on this
  machine or any other — and every figure above is arithmetic over the tool's
  own watch set, pinned offline in `--self-test` and in
  `../../windows/tools/test_manual_fan_ctrl_probe.py`. The write-up is
  `../findings/probe-0700-whole-page-arm.md`.

And one difference in shape, which the numbers do not show. A §3 block is
~10 s settle + ~30 s hold + ~60 s watch, so ~100 s of observation in all, with
marks at both ends of each of those three stages. A probe block is one hold
per arm, ~30 s each by default: no separate settle and no separate post-write
watch, because the tool snapshots once before each arm and sweeps until the
hold is up. A probe block is also a shorter block, and a run that used only
the probe is not a §3 run that was quicker. What it reports is narrower than
§4.4's comparison, not the same number in a worse place: the probe prints
each arm's first value, last value and change count — the net, which is one
of the three figures on the grader's `window delta` line — where §4.4 keys
the control-vs-write comparison on total movement. A probe run's per-arm
change rows are printed as they happen, so a reader can sum them, but
nothing in the probe's own output does that summing; the §3 three-capture
form gets it printed for it by the grader.

What §3b lists is what the tool half is *specified* to do, and the tool half's
behaviour is checked offline: `windows/tools/test_manual_fan_ctrl_probe.py`
scripts both arms byte by byte, and `bash ../../tools/run-tests.sh` from the
repository root runs it along with every other `test_*.py` there
(`../../tools/README.md`). So the reader setting out for the machine is not
taking the tool's first run to the EC: the arms, the sweep and the `0x0751`
grader have all had a mocked, no-hardware pass, and none of it is evidence about
this machine — which is what §7's `present-untested` still waits on.

## 4. What to read off

For each run, from the three CSVs plus the by-hand power readings:

1. **`0x0783`, `0x0784`, `0x0785`** — do they move on their own after the
   `0x0751` write? The static prediction is no. If they *do*, note what they
   move to and compare against `0x0730-0x0737` (Gaming/Office PL defaults)
   and `0x07A7-0x07AA`; a match would be the copy mechanism the static scan
   did not find, and directly contradicts
   `../../ec/annotations/manual-fan-ctrl-0751.md` §5.
2. **`0x0F00-0x0F5F`** — does any of the fan table change? Prediction: no,
   because the EC's own table load is triggered by the `0x0F5D-0x0F5F`
   mailbox, not by `0x0751`. If the table *does* reload, capture it and run
   `windows/tools/fan_table_replay.py` against it.
3. **`0x07C6`** — the byte the vendor brackets its fan-table write with.
   Does it move by itself?
4. **Fan duty** under the fixed load. This is the one that decides whether
   `0x0751` alone is a usable control at all: if the fan curve changes with
   nothing else written, the EC acts on the byte. Issue #99 named
   `0x075B`/`0x075C` for it as unconfirmed PWM, and that is now settled
   (issue #123): they are the vendor's `ADDR_EC_MAIN_FAN_L_DUTY_BYTE` and
   `ADDR_EC_MAIN_FAN_R_DUTY_BYTE`, read and halved for display by
   `FanInfo.GetEcCpuFanDuty`/`GetEcGpuFanDuty`, and they have entries of
   their own in `ec/annotations/registers.yaml` as `MAIN_FAN_L_DUTY` and
   `MAIN_FAN_R_DUTY`. **That makes them the right two bytes to compare, and
   still the wrong two to write** — the vendor only ever reads them. Duty is
   what the EC publishes, not a control the host drives; the bytes the
   vendor calls PWM are a different block (`ADDR_MYFAN2_L*_PWM` at
   `0x0743`-`0x0747`, `ADDR_L*_PWM_DEFAULT_MYFAN3`/`_MYFAN2` at
   `0x0786`-`0x078D`), and the curve itself is the `0x0F00-0x0F5F` table.
   Do not write `0x075B` expecting the fan to turn.

   Keep reading the whole `0x0700-0x07FF` sweep rather than only those two.
   That instruction used to be there because the two addresses were
   unidentified; it stays because the neighbourhood is still the least
   mapped part of the page and `0x0786` in it is a live naming conflict —
   `EC_ADDR_FAN_DEFAULT` upstream, APTC/APTN in the DSDT and in 3.1.39.0,
   `ADDR_L1_PWM_DEFAULT_MYFAN3` in ECSpec, three names and no agreement
   (recorded in that register's own entry). The audible fan is evidence too —
   write down whether it changed, and when.

   **The single-tool form of that instruction is `--watch-page`** (issue
   #666): one console, the whole page swept, at 448 ECRR reads per sweep or
   112 `--block` IOCTLs — §3's own arithmetic over §3's own three ranges. It
   is opt-in, and a probe run without it still reads only 14 addresses of the
   page; §3b says what that costs and what it does not. The flag has never
   been run.

   **Where the static arms say to look first.**
   `../../ec/annotations/manual-fan-ctrl-0751.md` §9 walked both arms of all
   17 mode-bit branches and found that the EC stores to *both* candidate
   bytes on a path one of those bits selects: `0x075B` at the `0x89E0` and
   `0xBB29` write sites, on the Fan Boost **not set** side of the
   `0x8942`/`0x899D` arms, and `0x075C` at `0x8F0A` and `0x8F11`, on **both**
   arms of `0x8E8B` (USER). So the two arms of this procedure are not
   symmetric: the `0x00`
   and `0x10` blocks differ from the `0xA0` block in the USER bit, and the
   `0x8E8B` arm fires for USER either way. That is a prediction *for* this
   run — no hardware was involved in finding it — and what it changes is
   which comparison to make, not what counts as a result.

   **CORRECTION** (issue #123, 2026-09-24), leaving the paragraph above as
   it was written. The two addresses in it are identified now — they are the
   duty bytes, above — but the pairing by proximity does not survive. All
   three sites per address are now walked in `../../ec/annotations/registers.yaml`
   and `../../ec/annotations/static-refs-audit.md` §7. `0x89E0` and `0x8F11`
   do turn out to be a pair, because the `lcall` at `0x89EB` enters the
   `0x8F0F` routine that writes `0x075C`. `0x8F0A` is *not* the other half of
   that pair: it is the last write before the `ret` that ends the separate
   `0x8EE0` routine, which an `acall` from bank1 reaches at `0x10F0D` and
   `0x10F44`. Two further sites, not in the paragraph above, are the ones
   that zero both bytes — `0x87C5` and `0x87D5`, inside the clear run at
   `0x87B8`. None of this is the fan table: `0x0F00` and `0x0F20` have zero
   direct `MOV DPTR` sites, so the table is reached indirectly and
   `../../ec/annotations/manual-fan-ctrl-0751.md` §6 stays open.

   What does not change is what the run is for. These bytes move because the
   fan is doing its job, on a die whose temperature is the variable under
   test; §4.5's temperature pair is what tells the two apart, and nothing
   here makes a duty difference evidence that the EC acted on `0x0751`.

   The same §9 also found the Fan Boost arms gating on temperature rather
   than on a duty copy: the `0x8942` BOOST-**set** arm compares `CPU_TEMP`
   `0x043E` and `GPU_TEMP` `0x044F` against 70 °C and clears `BOOST` in
   `0x0751` itself if both are under it. **So a mode byte written by the
   host may not still hold the value you wrote at the next mark** — if
   `0x0751` has moved back, that is a finding, not a failed write, and it
   belongs next to the readback check in step 6.

   One thing deliberately *not* done: `0x0460`/`0x0468`, the fan-tachometer
   bytes these arms also read, are **not** added to any watcher. §3 stops
   that range at `0x045F` on purpose — reading the tach bytes through `ECRR`
   stalled the fans on a sibling board (`../related-projects.md`, issue
   #94). The static picture is therefore incomplete on that axis, and the
   cost of keeping it that way is lower than the cost of the alternative.

   **Then compare the control arm's capture window against the write's.**
   How far did `0x075B`/`0x075C` move between the no-op's mark and the next
   one? The grader prints it for you as a `window delta` line per window (§6)
   so the two arms are two numbers rather than two terminals of subtraction,
   but it does not compare them and does not say which is bigger — the call
   is yours.

   Read those two windows off the same block, which is why every one of them
   carries a `block:` line and `--block` takes the value under test rather
   than a position in the mark stream. It also means both windows are only
   there if the mark set held: a control arm whose mark is missing from one of
   the three CSVs has that console's rows filed under whichever window their
   timestamps fall in, and nothing in the report ties them to the arm — so
   this comparison could be between an arm and whatever ran before it. The
   grader refuses that case rather than printing the two numbers side by side,
   so a report you have is a report whose two arms are the two arms.

   **The comparison keys on *total movement*, not on the net.** The line
   carries three figures and they are not interchangeable. *Net* is the
   difference between where the byte opened the window and where it closed
   it — the cleanest summary of a clean monotonic step, and blind to any
   movement that came back. *Total movement* is the sum of the absolute steps
   the byte took inside the window, so it counts the whole path. *Max
   excursion* is the furthest it got from the value it opened at, and is
   the read for a write arm whose response is a ramp to a new duty
   *followed by wander*. The argument is the shape of the thing being
   measured, not arithmetic convenience: a fan's duty under a fixed load
   wanders with the die, and it wanders in **both** arms. The wander is
   common to both, so it cannot separate them, while a net swallows it
   entirely — a duty that climbs to a new curve and then wanders back down
   ends near where it started and nets to nearly nothing, which is exactly
   what a *ramping response* to the write looks like. What can separate the
   two arms is how far the byte actually travelled. A byte that held still
   prints as `net +0 … (0 changes)` rather than going missing, so a byte
   that was watched and stayed put is not read as a byte nobody watched.
   The net stays on the line because where a response really is a clean
   step, that is the figure to read, and because where the statistics
   disagree it is total that carries the answer.

   On 2026-09-23 that comparison is the whole reason the fan half stayed
   `present-untested`, and it is not re-litigated by this choice of figure:
   that capture recorded the PWM drift as monotonic
   (`../../evidence/ec-watch/2026-09-23-0751-isolation.txt`, "the same
   monotonic PWM drift"), and for a monotonic drift net, total and max are
   the same number. It was a probe run, not a §3 fixed-load block, so it
   has no capture windows to re-grade — see §3b. If the write window's
   movement is inside the control arm's run-to-run spread, that is the
   answer to record and the status does not move — per `../../CLAUDE.md`,
   an ambiguous result is a result, not a reason to pick the
   confident-sounding phrasing.
5. **CPU package power** under the same fixed load, by hand at each mark. If
   the PLs did not move but the power ceiling did, something other than
   `0x0783-0x0785` is enforcing it, and that is a new question, not a
   result. Temperature no longer needs an external tool: read it from the
   `0x0400-0x045F` CSV, and use it for the job §4.4 needs — showing the load
   was flat in both capture windows. A duty difference between the control arm
   and the write under test means something only if `0x043E` held steady
   across both; if it climbed through the pair, the difference is the die and
   not the byte. The rest of that page is sensors: read it for context, and
   do not read a power number out of it.

   **CORRECTION**, added after the page was swept
   (`../../ec/annotations/xdata-0400-045f.md`): *the rest of that page is
   sensors* is wrong, and the sentence above is left in place rather than
   edited out. Four bytes in `0x0400-0x045F` are electrical, and this
   watcher's own CSV prints them: `0x0434`/`0x0435` is battery current in mA
   and `0x0438`/`0x0439` is terminal voltage in mV, each established three
   independent ways (`../../ec/annotations/registers.yaml`,
   `../../docs/findings.md` §4g). `0x0448` and `0x0449` are those two divided
   by 100, computed by the firmware at bank1 `0xF416` and `0xF3D7`. The
   instruction above still stands for what this step is for — the page is
   context, and the deciding number in §4.5 is the die temperature, not a
   battery figure — but it is worth being precise about why you would not
   quote a power number from the pair even though you now could multiply
   those two bytes into watts: a figure the EC computes for itself is not a
   quantity a `0x0751` write is supposed to move, and §4.5's question is
   whether it does.
6. **Does `0x0751` still hold your value at the end of the window**, or did
   something put it back? Compare the block's `*-before-0700.txt` and
   `*-after-0700.txt` dumps (§6).

A run where *nothing* moves is a real result and should be recorded as one:
it would mean a Linux driver has to write the whole bundle, which is the
expensive answer and the one worth being sure of.

## 5. What this cannot settle

- One machine, one firmware version (`GMxMGxx_11.800`). Nothing here
  generalises to sibling boards; see `../related-projects.md`.
- A byte that does not move inside a 60 s window may still move at the next
  suspend, AC transition or EC reset. The window is a window.
- The `AP_OEM` (`0x0741`) bit-0 gate on the PL clear found statically
  (`../../ec/annotations/manual-fan-ctrl-0751.md` §4) is *not* exercised by
  this procedure — with Windows running, the vendor service holds that bit
  set. Testing it means clearing it deliberately, which is a separate test
  with its own safety argument, not a step to fold in here.

## 6. Where the output goes

Name the files the way the existing capture does, so a reader can pair them:

```
evidence/ec-watch/<date>-0751-isolation-0700-07ff.csv
evidence/ec-watch/<date>-0751-isolation-0f00-0f5f.csv
evidence/ec-watch/<date>-0751-isolation-0400-045f.csv
evidence/ec-watch/<date>-0751-isolation-<value>-before-0700.txt
evidence/ec-watch/<date>-0751-isolation-<value>-before-0f00.txt
evidence/ec-watch/<date>-0751-isolation-<value>-before-0400.txt
evidence/ec-watch/<date>-0751-isolation-<value>-after-0700.txt
evidence/ec-watch/<date>-0751-isolation-<value>-after-0f00.txt
evidence/ec-watch/<date>-0751-isolation-<value>-after-0400.txt
evidence/ec-watch/<date>-0751-isolation-snapshot.txt
```

`<date>` is that run's YYYY-MM-DD and `<value>` the value written in that
block, lower case and without `0x` (`a0`, `00`, `10`) — the same two
placeholders §3's commands take, spelled the same way so a filename carries
between the two without a rename. The three CSVs are one set for the whole
run: `ec_watch.py` appends to a `--csv`
file that already exists, and the marks say which write each row follows. The
dumps are per block and have to be, because they are whole-range reads with
no marks in them — nothing inside one says which write it brackets, so §3's
`>` would otherwise leave block 1 with block 2's bytes. That naming is also
what lets the grader say which block a `--dump` belongs to, which is the one
thing in a dump that says so; see the command below. The snapshot has to
say which mode each block started from and what was written, since nothing
else in the set says it. The marks in all three CSVs must carry the same
labels, must tell the control arm from the write under test, and must leave
every block ending on its restore. All three are checked, per block and per
capture, before a window is
printed — see §3, and the census the grader puts above the windows. The labels
are §3's six forms: the three that name a write and carry a value —
`no-op wrote 0x0751=0xA0`, `wrote 0x0751=0x10`, `restored 0x0751=0xA0` — and
the three stage boundaries that carry none, `settled`, `held`, `watch over`.
A boundary is one mark like any other to the checks above, so a `watch over`
one console missed or that two spelled differently withholds its block's
windows on exactly the terms a `wrote` would; a capture with none of the three
is not refused, and §3 says what a block without a `watch over` costs. **As of
2026-09-25 (issue #531) the forms are checked at the prompt as well**,
by `--label-vocab 0751` in §3's three commands, which runs this grader's own
`parse_mark` over each label as it is typed and refuses the ones it cannot
place — the same message, the same forms, the same counting rule. That is
offline behaviour of the tool against a fake EC, not a live run; what it moves
is the correction to where the day is still being spent, and what it promises
is that a label it accepts is one this grader can place. Both ends apply that
one predicate, so a label the prompt accepts and this grader later refuses
would be a bug in one of the two rather than a documented gap.

**A run that did not reach its hold.** `windows/tools/manual_fan_ctrl_probe.py`
records that in the capture itself, in one `#` row written from its
`except BaseException` handler just before the restore mark:

```
# the run ended early: 2026-09-25T14:31:02.480+02:00,manual_fan_ctrl_probe: RuntimeError: observation failed mid-run
```

The grader reads that one row, and it is the only `#` row it reads — a `#`
annotation you write by hand, which §6 above asks for on the snapshot, does not
carry the phrase and is still skipped. A row it can place against a mark
**withholds that block's windows and exits 1**: the block still holds its
restore (the probe restores from a `finally`), so it reads `intact` over an arm
that stopped at 5 s, and an arm that stopped at 5 s grades in the same format
as one that ran its hold. The rest of the day is unaffected, so a
`--block <value>` run for a value that did finish still passes, and a section
above the windows names every row with the window and block it fell in — all of
them, whether or not this run selected that block. A row with no readable
timestamp, or one stamped before the first mark, cannot be placed against any
arm at all: the run is then refused rather than partly reported, because a
window whose length the report cannot bound is not one to quote. Re-run that
block. **As of 2026-09-25 (issue #664)**; a capture taken with a probe older
than this carries the same row without a timestamp and is refused for that, so
such a capture needs the block re-run rather than an edit.

Add a header comment to the snapshot in the style of
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`: date, AC/battery,
mode, service running or stopped, what load was held, what was written, and
which mode each block started from. Then add the files to `evidence/README.md`,
which is the index every findings claim cites through.

`../../ec/tools/grade_0751_isolation.py` reads nine of the ten and
applies §4.1-§4.3 and §4.6 to them mechanically, which is a cheaper first
pass than doing it by eye. Which nine is worth stating outright, because a
file in this list that nothing consumes is a file an operator is being asked
to take for no reason:

- **The three CSVs and all six dumps are read by the tool.** The CSVs are
  the windowed read, one per mark; the two dumps of each of the three ranges
  are the whole-block read, given as one `--dump-pair`; and the `0x0700` pair
  is given a second time as the two `--dump`s §4.6's readback is taken from.
- **The snapshot is the human's.** Nothing in the tool reads it, because it
  is `#`-comment header text and `read_dump` skips comment lines rather than
  parsing them. It is in the set because §3's step 0 writes it and because
  it is the only record of which mode a block started from.

Pass one block's dumps, with the `after` one last — the §4.6 readback
check is taken from the final `--dump`, and before-then-after is the order
inside each `--dump-pair` too. Both are checked now rather than left to the
comment below: get the `--dump` order wrong and §4.6 says the readback was
not taken and names the pair that does cover `0x0751`; give a pair the same
file twice and it is named and not read, because a dump diffed against
itself proves nothing:

```console
rem  The 0x0700 pair is given twice on purpose, and not by accident of
rem  copy-paste: as the two --dump flags §4.6's readback is taken from, and
rem  again as one --dump-pair for the whole-block read. The two flags are
rem  independent -- --dump-pair does not feed §4.6, and the readback still
rem  comes from the last --dump of the block being graded -- so the 0x0700
rem  after-dump has to stay the last of that block's --dump flags. Putting
rem  the 0x0F00 dumps there instead would look tidier and quietly stop the
rem  readback: that range does not cover 0x0751. The tool now catches that
rem  and says so under §4.6, so this comment is the fallback rather than the
rem  only safeguard.
rem
rem  Run this once per value, with --block <value> added, and each run is one
rem  attachment. --block takes the value under test as hex with or without
rem  the 0x (0xA0, A0 and a0 are the same block), and a value that is in no
rem  block is an error rather than a run that quietly grades everything.
rem  --block and --wrote both name the value under test, so pass the same one
rem  to both; two different values is refused as the wrong command line it is.
rem
rem  The marks are checked before any window is printed: every action in all
rem  three CSVs, every capture spelling it the same way, and every block's
rem  last mark its restore in each capture. A block that fails is summarised
rem  where its windows would be and its windows are not printed, and the exit
rem  code is 1. A mark set that cannot support its windows is a hole in the
rem  record, not a quiet result -- see §3.
rem
rem  This path is repo-relative, and it is the only part of the grading that
rem  needs a checkout rather than the files: the grader is stdlib-only and
rem  reads these ten files rather than the machine, so running it here over
rem  the machine's copies and running it back in a checkout over the same ten
rem  give the same answer. §2 says which of the two §3 needs.
python ec\tools\grade_0751_isolation.py ^
        <date>-0751-isolation-0700-07ff.csv <date>-0751-isolation-0f00-0f5f.csv ^
        <date>-0751-isolation-0400-045f.csv ^
        --dump <date>-0751-isolation-<value>-before-0700.txt ^
        --dump <date>-0751-isolation-<value>-after-0700.txt ^
        --dump-pair <date>-0751-isolation-<value>-before-0700.txt ^
                     <date>-0751-isolation-<value>-after-0700.txt ^
        --dump-pair <date>-0751-isolation-<value>-before-0f00.txt ^
                     <date>-0751-isolation-<value>-after-0f00.txt ^
        --dump-pair <date>-0751-isolation-<value>-before-0400.txt ^
                     <date>-0751-isolation-<value>-after-0400.txt ^
        --block <value> --wrote <value>
```

Three values make three blocks, and the three CSVs are one set for the whole
run, so a plain invocation over them prints every block's windows, each
labelled with the block it falls in. `--block <value>` grades one block and
prints that block's windows alone, with its own `intact`/`VOID` verdict and
the same non-zero exit if that block is void or its mark set does not hold —
which is what makes this output something a fold-in can attach per block, one
attachment per value. The other blocks are not checked in such a run, and the
report says so, in the census and in the block section.

Marks in no block are not scoped by `--block` either, and the census says of
each that `--block` cannot select it. One of them — a label that is not one of
the forms named above — refuses the whole run rather than the block that
was selected, because the labels are the only thing that says which block a
window is a window of: one the grader cannot place could have been a write, in
which case the capture is holding a block it cannot name, or a restore typed
between a block's write and its restore, which would close that block early and
leave it void rather than `intact`. So a `--block` run over a capture carrying
one exits 1 however clean the block it printed was, and the closing summary
says so in a line of its own, in the place the count of withheld windows would
be — printed there whether or not anything was withheld, and so on its own when
nothing was.

The selector is the value rather than a block number because the value is
what §6 stamps every dump with, and a dump is a whole-range read with no
marks in it: the `<value>` in the file name is the only thing in it that says
which block it belongs to. So the grader reads each `--dump`'s block off its
own name, takes §4.6's readback from the last dump *of the block being
graded*, and names that block in the section. A `--block 0x10` run handed the
`a0` dumps says they belong to 0xA0 and takes no readback from them, rather
than putting 0xA0's byte under 0x10's windows. Where a dump's name carries no
value, the run falls back to `--block`/`--wrote` and says which it used.

The same rule covers the whole-block report, and it has to: a `--dump-pair`
bracket is wider than a window and answers the same question, so a pair
filed under the wrong block is a result about the wrong bytes rather than a
second reading of the right ones. Each pair is filed by the `<value>` in its
two file names — either one names the block and the other is silent, and two
that name different blocks is an input error, reported and not read rather
than resolved by picking one — and the section groups the pairs the way it
groups the dumps. A `--block 0x10` run handed the `a0` pair prints the
`belongs to block 0xA0, not the block under test (0x10) -- not read for
§4.1-§4.3 here` line in place of the bracket, and says that no `--dump-pair`
was given for 0x10, so the whole-block read for it was not taken. Note what
that refusal is *not*: the two blocks' brackets here are the same reading of
the same page in opposite directions and come out byte for byte identical, so
nothing inside a mis-filed bracket looks wrong. The group line above it is
the whole of the attribution.

§3a's service-stopped pass is a second run with its own `<date>`, not a fourth
block of this one: the Office/Turbo pair is required in both arms and §6's
names carry no arm, so the two passes' `<value>`-stamped dumps would overwrite
each other.

The `--dump-pair` report is a second, wider bracket on the same §4.1-§4.3
bytes, and it is worth having for what the windows cannot show: a byte that
moves after the final mark and before the after-dump, or that moves entirely
between two of `ec_watch.py`'s sweeps, is in the pair and in no change row.
Each pair covers one range, so each reports the groups it does not cover as
*not covered by this pair* — the fan table is in neither the `0x0700` nor the
`0x0400` dump, the PLs and the `0x07C6` bracket byte in neither the `0x0F00`
nor the `0x0400` one, the temperatures in neither the `0x0700` nor the
`0x0F00` one, and the fan duty in neither the `0x0F00` nor the `0x0400`
one. That names the §4.4/§4.5 context groups as well as the §4.1-§4.3 ones,
and for the same reason each time: "never read" is a different answer from
"read and did not move", and a group that went unprinted under a heading that
promises it would read as the second. It is a different bracket, not a
stronger one: a byte that moved and was back where it started by the
after-dump reads unchanged here whether or not the captures recorded it.
Each read has a gap the other does not close. An address one dump covers and
the other does not is a coverage gap, never a change, and the section emits
no status of its own.
`0x0F5D-0x0F5F`, the three bytes at the end of a `0x0F00-0x0F5F` dump, is
reported under a heading of its own rather than under §4.2's, because they
are the mailbox `../../ec/annotations/manual-fan-ctrl-0751.md` §6 decodes at
`0x888D` — `0xFD`/`0xC9` and a selector, written by the host to ask the EC to
copy a table — and the last three GPU duty slots, the tail of the row the
service writes. A difference there is a host poke and/or a written table, and
neither is §4.2's question, which is about `0x0F00-0x0F5C` alone. When §4.2
does have a change, the section names its own next step,
`../../windows/tools/fan_table_replay.py`.

A pair given the same file twice is the one input error this flag cannot see
on its own, so it is caught by path: the run names the pair, says both sides
are the same file, and prints no whole-block read for it at all. A dump
diffed against itself holds every byte equal by construction, so `unchanged`
there is a true statement about nothing. The `<value>-before-` /
`<value>-after-` naming is what keeps the two files apart to begin with, and
the tool now says so when a pair does not.

A capture given twice is the same mistake on the CSV list, and it is refused
outright where a repeated `--dump-pair` is only flagged and skipped, because
every section of this report is about the captures: there is no part of it
worth printing without them, and a skip would hand back a report that is
quietly a single-capture run. The census counts captures, so one console
would have been counted as two; the cross-console checks engage at two, so a
file agreeing with itself would have switched them on and satisfied them; and
the line saying they did not run would have been suppressed, which is the
line that exists to disclose a single-console run in the first place. The
repeat is caught by resolved path, so `x.csv` and `./x.csv` are one capture
and not two, and the census count and the one-capture notice key on the
distinct captures either way. Pass each of the three CSVs once.

It is a first pass and not the answer. It prints §4.4's fan duty bytes
and §4.5's temperature bytes per window so the control arm and the write can
be compared line for line, and it sums each of them into a `window delta`
line — first value, last value, the endpoint net, the total movement, the
max excursion, and how many times the byte moved inside the window. Every
context byte gets a line in every window, whether or not it moved, so a
byte that held still reads as a zero rather than as a missing line. §4.4
names which of the three figures the control-vs-write comparison keys on
and argues it from what a thermal wander looks like; the short form is that
they disagree exactly when a byte wanders, and a fan duty under a fixed load
wanders in both arms. The whole-block section prints the same duty pair, and —
because the `0x0400` pair is one of the three — §4.5's two temperature bytes
too, under the same *not graded here* heading: whether the die held across
the control arm and the write, read at the block's two ends rather than
inside one window. It still does not grade them and does not claim to. The
reason is not that the addresses are unidentified any more — issue #123
identified them. It is that a fan duty byte drifts on a warming die whether
or not anything wrote `0x0751`, so grading it would report "moved" on every
window including the no-op control, and telling those apart is what the
control arm in §3 measures and what a script cannot. Package power is in no capture and is
still yours to note by hand. The script says so in its own output and does
not emit a status.

## 7. What a result has to say

`MANUAL_FAN_CTRL` moves off `present-untested` only on a behavioural
observation, not on the write being accepted — `../../CLAUDE.md`, "a register
write being accepted (readback matches) is not evidence the EC acts on it".
Concretely:

- fan duty or package power moves under a fixed load, with nothing but
  `0x0751` written → `confirmed-working`, with the capture cited and the
  *scope* of the claim written out (the byte does X; it does not imply the
  PLs follow).
- nothing moves across all three values, both with and without the service,
  and the surrounding bytes stay put → `confirmed-inert` for the byte *as a
  standalone control*, which is the answer that sizes the Linux driver. Say
  it in those words; "inert" about one path is not "inert".
- mixed or ambiguous → it stays `present-untested` and the run goes into
  `evidence/` anyway with what was seen. That is not a failed test.
