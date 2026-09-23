# Isolating `0x0751`: does the EC act on the power-mode byte alone?

**Status: run 2026-09-23 (issue #99); the prediction held.** This procedure
was written by the pipeline for a human at the physical GM7MG7P, and then run
in an interactive session on that machine. Writing `0x0751` alone to each of
`0xA0`/`0x00`/`0x10` moved nothing else — not the PLs, not the fan table, not
`0x07C6`, not the GPU bytes — confirming the static prediction that the EC
does not derive the bundle from the mode byte. The run used the equivalent
single-tool form `windows/tools/manual_fan_ctrl_probe.py` (which watches the
same addresses and self-restores) rather than the two-`ec_watch` form in §5;
the raw log is `evidence/ec-watch/2026-09-23-0751-isolation.txt`, and the
result is folded into `MANUAL_FAN_CTRL` in `ec/annotations/registers.yaml`.
The one part §7 leaves open — whether the fan-mode bits scale fan behaviour
along the unchanged curve — was **not** settled (the run was near-idle); the
fixed-load comparison below is still worth doing. The rest of this file is the
original procedure, kept for that re-run and for anyone reproducing the test.

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
  first sweep and stop it after the last.
- A way to read CPU package power (HWiNFO, or `windows/tools/` equivalents).
  Note it by hand at the times you mark; it is not in the EC sweep.
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
Each is: snapshot, start the watchers, one write, wait, restore, stop.

```console
rem  --- 0. snapshot, read-only ---
python windows\tools\ecrw.py dump 0x0700 0x0100  > before-0700.txt
python windows\tools\ecrw.py dump 0x0F00 0x0060  > before-0f00.txt

rem  --- 1. start both watchers (two consoles), with the load already running ---
python windows\tools\ec_watch.py --start 0x0700 --len 0x0100 --seconds 90 ^
       --mark --csv 0751-isolation-office-0700-07ff.csv
python windows\tools\ec_watch.py --start 0x0F00 --len 0x0060 --seconds 90 ^
       --mark --csv 0751-isolation-office-0f00-0f5f.csv

rem  --- 2. let both settle ~10 s, press Enter in each to mark, then write ---
python windows\tools\ecrw.py write 0x0751=0xA0 --i-mean-it

rem  --- 3. watch for ~60 s; mark again at the end ---

rem  --- 4. restore, and mark once more ---
python windows\tools\ecrw.py write 0x0751=<original> --i-mean-it

rem  --- 5. after both watchers exit ---
python windows\tools\ecrw.py dump 0x0700 0x0100  > after-0700.txt
python windows\tools\ecrw.py dump 0x0F00 0x0060  > after-0f00.txt
```

`--mark` is what makes the CSV readable afterwards: without a timestamp for
"I wrote it now", a byte that moves 400 ms later and one that moves 40 s
later look the same in the log.

Values to run, one block each: `0xA0` (Office), `0x00` (Gaming), `0x10`
(Turbo). Start from a *different* mode each time — writing Turbo's `0x10`
while already in Turbo tests nothing.

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

## 4. What to read off

For each run, from the two CSVs plus the by-hand power readings:

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
5. **CPU package power** under the same fixed load, by hand at each mark. If
   the PLs did not move but the power ceiling did, something other than
   `0x0783-0x0785` is enforcing it, and that is a new question, not a
   result.
6. **Does `0x0751` still hold your value at the end of the window**, or did
   something put it back? Compare `before-*` and `after-*`.

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
evidence/ec-watch/<YYYY-MM-DD>-0751-isolation-0700-07ff.csv
evidence/ec-watch/<YYYY-MM-DD>-0751-isolation-0f00-0f5f.csv
evidence/ec-watch/<YYYY-MM-DD>-0751-isolation-snapshot.txt
```

One set per value, or one pair of CSVs covering all three with the marks
distinguishing them — either is fine as long as the snapshot says which. Add
a header comment to the snapshot in the style of
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`: date, AC/battery,
mode, service running or stopped, what load was held, and what was written.
Then add the files to `evidence/README.md`, which is the index every
findings claim cites through.

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
