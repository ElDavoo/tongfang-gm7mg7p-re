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

rem  --- 1. start all three watchers (three consoles), with the load running ---
rem  ---    --interval 0.5 is a starting point, not a validated-safe value;
rem  ---    see the pacing note below before leaving it there ---
python windows\tools\ec_watch.py --start 0x0700 --len 0x0100 --seconds 240 --interval 0.5 ^
       --mark --csv <date>-0751-isolation-0700-07ff.csv
python windows\tools\ec_watch.py --start 0x0F00 --len 0x0060 --seconds 240 --interval 0.5 ^
       --mark --csv <date>-0751-isolation-0f00-0f5f.csv
python windows\tools\ec_watch.py --start 0x0400 --len 0x0060 --seconds 240 --interval 0.5 ^
       --mark --csv <date>-0751-isolation-0400-045f.csv

rem  --- 2. control arm: let all three settle ~10 s, mark each, then write
rem  ---    the value already there back to itself and mark that as a no-op ---
python windows\tools\ecrw.py write 0x0751=0x<current> --i-mean-it

rem  --- 3. hold ~30 s, mark each, then the write under test, mark ---
python windows\tools\ecrw.py write 0x0751=0xA0 --i-mean-it

rem  --- 4. watch for ~60 s; mark again at the end ---

rem  --- 5. restore, and mark once more ---
python windows\tools\ecrw.py write 0x0751=<original> --i-mean-it

rem  --- 6. after all three watchers exit ---
python windows\tools\ecrw.py dump 0x0700 0x0100 ^
        > <date>-0751-isolation-<value>-after-0700.txt
python windows\tools\ecrw.py dump 0x0F00 0x0060 ^
        > <date>-0751-isolation-<value>-after-0f00.txt
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
(`../../windows/tools/ec_watch.py:176`), so the last label in that list is the
last mark the capture has. If it is not the restore, the block is short one.

The `0x0400-0x045F` watcher is the EC's own temperature reading: `0x043E` is
`CPU_TEMP` and `0x044F` is `GPU_TEMP`, both `confirmed-working` in
`../../ec/annotations/registers.yaml`. It stops at `0x045F` on purpose — the
fan-tachometer bytes (`0x0460-0x046F`, issue #94) start right after, and
reading those through `ECRR` stalled the fans on a sibling board
(`../../docs/related-projects.md`). Every other byte in the range is context;
§4.5 says what to do with it.

**Three concurrent watchers put more `ECRR` traffic on the bus than any run
before this one, and this is the only one held under a fixed load.** The
arithmetic is worth having in front of you: `ecrw.Ec.read`
(`../../windows/tools/ecrw.py:115`) is one `ECRR` `DeviceIoControl` per byte
with nothing between calls, and `ec_watch.py` reads every address in its range
once per sweep (`addrs`, `../../windows/tools/ec_watch.py:123`) with
`--interval` slept between sweeps (`ec_watch.py:149`), not between bytes. So
one sweep of each of the three watchers is `0x100 + 0x60 + 0x60 = 448` ECRR
reads, all three running at once, for as long as the block runs.
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
what you just did as the label (`no-op wrote 0x0751=0xA0`,
`wrote 0x0751=0x10`, `restored 0x0751=0xA0`) rather than keeping the timing
in separate notes. Mark the same action in all three consoles within a few
seconds of each other; the grader treats marks less than five seconds apart as
one action, which is what keeps three consoles from reporting one write as
three windows.

Values to run, one block each: `0xA0` (Office), `0x00` (Gaming), `0x10`
(Turbo). Start from a *different* mode each time — writing Turbo's `0x10`
while already in Turbo tests nothing.

The control arm writes the byte back to the value it already holds, so it
leaves the mode you started in, and the rule above is what makes the two
capture windows comparable: the only thing separating the control's from the
write's is the write. Label it `no-op wrote ...` and not `wrote ...`; the
grader windows on marks, and a control arm that reads like the write under
test is indistinguishable from it. This is the arm the 2026-09-23 run already
had in a weaker form, where `0x075B`/`0x075C` moved as much under the no-op as
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
- **The `*-before-0700.txt` / `*-after-0700.txt` dump pair.** The probe writes
  no dump, so §4.6 has nothing to read on a probe run: the question "does
  `0x0751` still hold your value at the end of the window" needs the two range
  dumps §3's steps 0 and 6 take, and `--dump` in
  `../../ec/tools/grade_0751_isolation.py` is what reads them. A probe run
  answers §4.4's PWM comparison and nothing else in §4.
- **§6's eight files.** A probe run produces none of them — no MARK-CSV, no
  dumps, no snapshot — so there is nothing to index in `evidence/README.md` and
  nothing for the grader to apply §4.1-§4.3 and §4.6 to. If the day is taken
  with the probe, the run stays a log the way 2026-09-23's did, and §7 has no
  capture behind it.

And one difference in shape, which the numbers do not show. A §3 block is
~10 s settle + ~30 s hold + ~60 s watch, so ~100 s of observation in all, with
marks at both ends of each of those three stages. A probe block is one hold
per arm, ~30 s each by default: no separate settle and no separate post-write
watch, because the tool snapshots once before each arm and sweeps until the
hold is up. The two forms produce the same *kind* of number — net movement per
arm, which is §4.4's comparison — but a probe block is a shorter block, and a
run that used only the probe is not a §3 run that was quicker.

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
4. **Fan PWM** under the fixed load. This is the one that decides whether
   `0x0751` alone is a usable control at all: if the fan curve changes with
   nothing else written, the EC acts on the byte. Issue #99 names
   `0x075B`/`0x075C` for it; neither address is in
   `ec/annotations/registers.yaml` and this repo has not confirmed them, so
   treat them as where to look first and read the whole `0x0700-0x07FF`
   sweep rather than only those two. The audible fan is evidence too —
   write down whether it changed, and when.
   **Then compare the control arm's capture window against the write's.**
   How far did `0x075B`/`0x075C` drift between the no-op's mark and the next
   one? On 2026-09-23 that number is the whole reason the fan half stayed
   `present-untested`. The grader prints it for you as a `window delta` line
   per window (§6) so the two arms are two numbers rather than two terminals
   of subtraction, but it does not compare them and does not say which is
   bigger — the call is yours. If the write window's movement is inside the
   control arm's run-to-run spread, that is the answer to record and the
   status does not move — per `../../CLAUDE.md`, an ambiguous result is a
   result, not a reason to pick the confident-sounding phrasing.
5. **CPU package power** under the same fixed load, by hand at each mark. If
   the PLs did not move but the power ceiling did, something other than
   `0x0783-0x0785` is enforcing it, and that is a new question, not a
   result. Temperature no longer needs an external tool: read it from the
   `0x0400-0x045F` CSV, and use it for the job §4.4 needs — showing the load
   was flat in both capture windows. A PWM difference between the control arm
   and the write under test means something only if `0x043E` held steady
   across both; if it climbed through the pair, the difference is the die and
   not the byte. The rest of that page is sensors: read it for context, and
   do not read a power number out of it.
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
evidence/ec-watch/<date>-0751-isolation-<value>-after-0700.txt
evidence/ec-watch/<date>-0751-isolation-<value>-after-0f00.txt
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
`>` would otherwise leave block 1 with block 2's bytes. The snapshot has to
say which mode each block started from and what was written, since nothing
else in the set says it. The marks in all three CSVs must carry the same
labels, and they must tell the control arm from the write under test:
`no-op wrote 0x0751=0xA0`, `wrote 0x0751=0x10`, `restored 0x0751=0xA0`.

Add a header comment to the snapshot in the style of
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`: date, AC/battery,
mode, service running or stopped, what load was held, what was written, and
which mode each block started from. Then add the files to `evidence/README.md`,
which is the index every findings claim cites through.

`../../ec/tools/grade_0751_isolation.py` reads those CSVs (and the
`*-before-0700.txt` / `*-after-0700.txt` dumps) and applies §4.1-§4.3 and
§4.6 to them mechanically, which is a cheaper first pass than doing it by
eye. Pass one block's dumps, with the `after` one last — the §4.6 readback
check is taken from the final `--dump`:

```console
python ec\tools\grade_0751_isolation.py ^
        <date>-0751-isolation-0700-07ff.csv <date>-0751-isolation-0f00-0f5f.csv ^
        <date>-0751-isolation-0400-045f.csv ^
        --dump <date>-0751-isolation-<value>-before-0700.txt ^
        --dump <date>-0751-isolation-<value>-after-0700.txt --wrote 0xA0
```

It is a first pass and not the answer. It prints §4.4's candidate PWM bytes
and §4.5's temperature bytes per window so the control arm and the write can
be compared line for line, and it sums each of them into a `window delta`
line — first value, last value, net, and how many times the byte moved inside
the window — so §4.4's deciding comparison is two numbers instead of two
terminals. It still does not grade them and does not claim to: an unconfirmed
PWM address drifting on a warming die moves whether or not anything wrote
`0x0751`, and telling those apart is what the no-op arm in §3 measures and
what a script cannot. Package power is in no capture and is still yours to
note by hand. The script says so in its own output and does not emit a
status.

## 7. What a result has to say

`MANUAL_FAN_CTRL` moves off `present-untested` only on a behavioural
observation, not on the write being accepted — `../../CLAUDE.md`, "a register
write being accepted (readback matches) is not evidence the EC acts on it".
Concretely:

- fan PWM or package power moves under a fixed load, with nothing but
  `0x0751` written → `confirmed-working`, with the capture cited and the
  *scope* of the claim written out (the byte does X; it does not imply the
  PLs follow).
- nothing moves across all three values, both with and without the service,
  and the surrounding bytes stay put → `confirmed-inert` for the byte *as a
  standalone control*, which is the answer that sizes the Linux driver. Say
  it in those words; "inert" about one path is not "inert".
- mixed or ambiguous → it stays `present-untested` and the run goes into
  `evidence/` anyway with what was seen. That is not a failed test.
