# The `0x07D0` door: what moves first under a GPU TGP change, and who opens it

**Status: not run.** This procedure was written by the pipeline for a human at
the physical GM7MG7P (issue #184), and **issue #278 owns the run** — the
capture, the ProcMon half and the observation. The watcher, the offline grader
(`../../ec/tools/grade_gpu_door.py`) and both offline suites are committed; the
observation is not. Nothing in this file reports a result, and nothing under
`evidence/` comes from it — the first capture of this kind will be a human's,
taken on that machine. The `0x07D0` live-write record in
`../../docs/findings.md` §4f (2026-09-17) is **not** a run of this procedure and
does not cover this block: it wrote `0x07D0` directly and watched what that
write did, which is the opposite question from which process moves the byte
when the Control Center's GPU page does.

The two committed captures are not a run of this either, and are named here so
nobody mistakes them for one: `evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`
(§4g) and `evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv` (§7)
swept this block across an AC plug-in and an Fn mode cycle. `0x07C0`-`0x07D7`
was quiet in both except `0x07C4` twice at the plug-in.

**CORRECTION** (issue #276, 2026-09-24), leaving the sentence above as it was
written. *"`0x07C0`-`0x07D7` was quiet in both except `0x07C4` twice at the
plug-in"* is wrong in both files, and the byte that makes it wrong is inside
the range the sentence itself names: `0x07C6`. Re-derived over the whole
24-address range rather than the two the sentence named:

- **`2026-09-18-ac-plugin-sweep-summary.csv`** carries exactly two rows in the
  block, `0x07C4,2,0x08,0x38` and `0x07C6,2,0x04,0x04` — adjacent lines in the
  summary. `0x07C6` is a **move**, not a byte that "held `0x04`": its
  `first_old` equals its `last_new` because it changed away and came back
  inside the window, which is the same endpoint-net blind spot §6 warns about.
  What the summary supports is a per-address change count and those two
  endpoints. It does **not** support the intermediate value, either timestamp,
  or the order — the 32,499-row log it summarizes is not committed, and its own
  header says so. "Quiet" is precisely the inference it cannot carry.
- **`2026-09-23-power-mode-cycle-0700-07ff.csv`** carries 20 rows in the block
  across its 2 m 48 s window (`17:57:41.307` → `18:00:29.856`): `0x07C4` twice,
  `0x07C6` **18 times** — the busiest byte in the block — running
  `17:57:51.162` → `18:00:06.264`. Its rows are the 1.1-2.0 s `0x04 -> 0x00`
  dips, and the `0x00 -> 0x03` / `0x03 -> 0x07` pair recurs at
  `17:59:01.681`/`17:59:02.144` and `17:59:52.049`/`17:59:52.740`. The `0 -> 3`
  bits-0-1 Office reading is `../../ec/annotations/registers.yaml` `AP_OEM_6`
  and `../../docs/findings.md` §7a's, recorded there; it is not re-derived here
  and is not this file's to support.
- **"at the plug-in" does not survive either.** `0x07C4`'s two rows sit at
  `17:57:51.161` and `17:57:51.597` — within a millisecond of the first
  `0x07C6` dip, and ~10 s *after* the `0x0743`/`0x0745`/`0x0746` bundle rows at
  `17:57:41.307`. The file is `ts,addr,old,new` from line 1 and carries no
  `MARK` rows (the watcher only writes those under `--mark`), so from this file
  the two rows cannot be placed at a plug-in at all, nor told apart from a mode
  switch.
- **The other 22 addresses in `0x07C0`-`0x07D7` get no row in either file.**
  That is "not found to move in these two windows" and nothing more: not
  "never written", not "the rest of the block is dead", and not evidence that
  the EC ignores them.

`0x07C6` is `AP_OEM_6` (`WMS0` b0-1; bit 2 upstream
`ENABLE_UNIVERSAL_FAN_CTRL`) and it keeps `present-untested` — a passive
capture showing a byte move is not a live test of it, which is that note's own
standing caveat. But it is the block's known mode-switch chatter, and §5's
"window delta" column and §6's three-way reading both turn on telling a
GPU-only change apart from the Fn bundle. The operator needs its per-capture
counts as the baseline that does that: `0x07C6` moving is the expected noise,
not the result, and a capture containing it should not be discarded for it.

A GPU-only TGP change is the one UI action neither bundle contains.

**One limit to read before the question, added 2026-09-25 (issue #264): this
procedure's watch set does not reach the middle of the boost path.** The chain
`0x0745`/`0x0746` → `0x09EA`/`0x09EB` → `0x07D4`/`0x07D5` → `ATPP`/`AMAT` runs
through page `0x09`, and `WATCH` covers `0x07C4`-`0x07D7` and
`0x0743`-`0x0746` only. So the run can say whether the `0x07C4`-`0x07D7` half
moved; it cannot separate "`0x83FF` did not run" from "it ran and found the
values already equal". §6 states this in full and names the amendment it would
need. The status line above is unchanged: **not run**.

## 1. The question

`../../docs/findings.md` §4o closes on a negative and leaves a hazard in it.
Two decoded paths write the same physical byte, `0xFE4107D0`: the vendor
charge-limit write over `ECRW` (§4e) and the DSDT's GPU TGP write, `T1WR
Arg0 == 0x1173`, which stores `Arg1 * 8` into `0x07D0`/`0x07D1`. They disagree
about scale — an `ECRW` write of a 55% limit lands as `0x37`, while `T1WR
0x1173` cannot produce more than `0xF8` — so the byte's value carries a
different meaning depending on which door wrote it, and a reader of the byte
cannot tell which. That is arithmetic on two decoded paths, **not an observed
failure**: nothing in §4o or §4f saw a clash, and the hazard remains a hazard
however the capture comes out.

The question this procedure asks is the *door*, not the register: **under a GPU
action that is not the Fn mode bundle, does `0x07C4`-`0x07D7` move, does
`0x0743`-`0x0746` move, which moves first, and which process issued the
`DeviceIoControl` that did it.** The two blocks are in one capture on purpose.
The service's own `GpuFeatures` class writes the `0x0743`-`0x0746` half
(`../../windows/vendor-ec-map.md:84-87`), and the DSDT names the same four bytes
as `GNEN`/`ECDC`, `CTVA`, `DBCT`, `MXDB` — so if the host half moves first, the
service moved; if the ACPI half moves first under a GPU-only change, nothing in
the committed tree says what did. Two `ec_watch.py` instances would put the two
halves in two files with two start times, which is exactly the cross-file
correlation this is trying to avoid.

**Out of scope, so it is not redone here.** The register-effect half of a
Control Center GPU action — which MQTT `*/Control` command reaches which EC
register — belongs to issue #87. This procedure performs the UI action and
records marks; it does not map the command, and it does not pair the action with
`mqtt_sniff` output beyond what §3 asks for. The grading of the capture, once
there is one, is `../../ec/tools/grade_gpu_door.py` — §5.

## 2. Before you start

- Windows, Control Center 3.1.39.0 installed, and `python windows\tools\ecrw.py
  read 0x07D0` printing a value — that is the same proof
  [the `0x0751` procedure](manual-fan-ctrl-0751-isolation.md) §2 asks for, and
  it says the vendor driver is present and you are elevated.
- An **elevated** shell. `ECRR` through `\\.\ACPIDriver` needs it, and so does
  most of ProcMon's stack capture.
- Sysinternals ProcMon (or WinDbg, per §4b) available and working.
- The **starting AC state written down**, and the starting value of `0x07D0`,
  `0x07D1`, `0x0743`-`0x0746` from `ecrw.py read`. The `ac plug` / `ac unplug`
  mark in §3 means what it says only if the operator knows which way it started.
- Not a fan test. This block does not include the fan-tachometer bytes
  (`0x0460`-`0x046F`) and never should; issue #94 is the open work on `ECRR`
  pacing, and `docs/related-projects.md` records bulk sweeps stalling the fans
  on a sibling board.

### Safety

**This procedure writes nothing.** `gpu_block_watch.py` has no write path at
all, and every action in §3 is a Control Center click or a cable. `0x07D0` and
`0x07D1` are `DO-NOT-WRITE-BLIND` in `../../ec/annotations/registers.yaml` and
that stands: the only hands-on test of `0x07D0` so far is §4f's, and it relaxed
the standing instruction by exactly as much as that note records and no further.
If a capture seems to need a write to complete it, it does not; write it up as
a gap instead.

## 3. The byte capture

One watcher, both windows, one clock:

```console
rem  --interval 0.25 is ec_watch.py's default and a starting point, not a
rem  validated-safe one: one ECRR per byte, 24 of them per sweep, with
rem  nothing between calls (#94). If the fans audibly change, stop, raise it
rem  and start again. The --csv path is resolved against whatever directory
rem  this runs in, so a bare filename leaves the capture there and nowhere
rem  else; §8 names where it belongs.
python windows\tools\gpu_block_watch.py --mark ^
        --csv evidence\ec-watch\<date>-gpu-door-07c4-07d7.csv
```

`gpu_block_watch.py` prints its watch table before it opens the driver, so the
console log and the CSV's sibling table both record what was watched:
`0x07C4`-`0x07D7` and `0x0743`-`0x0746`, each address's DSDT field name and its
current `registers.yaml` `status:`. `--names-only` prints that table and exits,
if you want to read it without the machine.

Type a label + Enter to stamp a mark; Ctrl-C to stop. Take these three actions,
each as **its own pair of marks with a hold between them** — mark, act, hold,
mark — the way §3 of
[the `0x0751` procedure](manual-fan-ctrl-0751-isolation.md) paces its own,
because a window that runs from one mark to the next is only one action if the
marks are far enough apart:

1. `gpu tgp <old>W-><new>W` — move the GPU TGP target in the Control Center's
   GPU page. The `W` is the unit the UI shows; record the old and new numbers
   as displayed.
2. `fn mode <old>-><new>` — switch Fn power modes. The service rewrites a whole
   bundle on a mode change (§7), `0x0743`-`0x0746` included, so this is the arm
   that tells a GPU-only write from a mode bundle.
3. `ac plug` or `ac unplug` — the AC transition, whichever the run needs.

Hold ~30 s after each action before the closing mark. `--seconds` defaults to
running until Ctrl-C, which is the right default here: the length of the run
does not matter, the marks inside it do. A mark typed after the watcher has
exited is written nowhere — `CsvSink` drops it rather than traceback
(`../../windows/tools/ec_watch.py:98-105`) — so the run's value is in its marks,
and the last label `gpu_block_watch.py` prints at the end is the last one the
capture holds.

**Both blocks in one file is the requirement, not a convenience.** The question
is an ordering, and an ordering across two captures is an ordering across two
start times. If a second run is needed, start a second *file* with its own
marks; do not merge two files and read the union.

## 4. The attribution capture

This is the part no committed input substitutes for, and it is why §3's capture
is not optional decoration: `../../docs/findings.md` §4o's `T1WR` census is a
negative over committed inputs, and a caller that is none of those inputs is
invisible to it by construction.

### 4a. ProcMon, the primary route

1. Start ProcMon before the actions. Filter **Operation is DeviceIoControl**
   *and* **Path ends with `\ACPIDriver`**; drop everything else, or the
   `.PML` will be dominated by the watcher's own `ECRR` traffic and by the rest
   of Windows.
2. Back the trace to a `.PML` (`File ▸ Save As`) with the marks from §3 still
   legible — write the mark labels and their timestamps on paper or in a text
   file next to the trace, because the `.PML` does not carry them.
3. For **each** §3 mark, read out of the capture:
   - the **PID**,
   - the **IOCTL code in the Detail column**,
   - the **stack**, if ProcMon's stack tracing is enabled for this capture.

The IOCTL code is the load-bearing part, and it is worth saying why in the
terms the committed inputs give. `ACPIDriver.sys` hardcodes the ACPI method name
per IOCTL — `movl $0x52524345,0x54(%rsp) ; MethodName = 'ECRR'`
(`../../windows/native/ACPIDriver.sys.analysis.md:177`) — and
`../../windows/native/ACPIDriverDll.dll.analysis.md:71-76` maps the codes:

| IOCTL | ACPI method | door |
|---|---|---|
| `0x9C40A488` | `ECRR` | EC read, raw 16-bit address |
| `0x9C40A48C` | `ECRW` | EC write, raw 16-bit address — the vendor charge-limit door (§4e) |
| `0x9C40A4D0` / `D4` / `D8` | `T1RD` / `T2RD` / `T3RD` | temp-read doors |
| `0x9C40A4DC` | `T1WR` | the `T1WR` door — the one `Arg0 == 0x1173` would come through |
| `0x9C40A4E0` / `E4` | `T2WR` / `T3WR` | the other two temp-write doors |

So an `ECRW` and a `T1WR` are told apart by **the handle that issued them**,
before anyone asks which byte moved. That is the whole of the "door" the
question is named for, and it is why the attribution capture is not a second
half of this procedure but the half that answers it.

4. At the moment of each mark, record the **loaded-module list** for the PID
   §4a.3 found:

   ```powershell
   Get-Process -Id <pid> | Select -Expand Modules     # or Listdlls.exe <pid>
   ```

   **Calibrate what this is worth.** A module loaded is not a call made. It
   distinguishes a JIT or reflectively-loaded caller from a plain one, and
   nothing more: a module that has been mapped since boot tells you nothing
   about this instant. What it is good for is the negative §4o's census could
   not close — if a module appears in this list that is not a process in the
   committed tree, that is a lead, and it is worth a new term set for
   `../../windows/tools/t1wr_callers.py`.

### 4b. WinDbg, if ProcMon's stack is not enough

Needs a kernel debugger session on the machine — a second step, not a
substitute you can skip to. `IRP_MJ_DEVICE_CONTROL` lands at `0x140007130` in
`ACPIDriver.sys`
(`../../windows/native/ACPIDriver.sys.analysis.md:162`); break there, inspect
the IRP and the stack, and read the control code the same way as ProcMon's
Detail column. The handler for `0x9C40A488` is `0x14000125C`, and §"How one
handler works, in full" of that file walks what the stack frame holds at that
point.

## 5. The blank result table

One row per §3 mark, filled in by the human who ran it. No example row is
given: an example row reads as an observation, and this repository is not where
that mistake is cheap.

| mark label | mark ts | `0x07C4`-`0x07D7` addresses moved (DSDT name) | `0x0743`-`0x0746` addresses moved | which block first, and by how many ms | ProcMon PID | process image | IOCTL code on the `\.\ACPIDriver` handle | modules loaded at that instant | verdict |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |
| | | | | | | | | | |
| | | | | | | | | | |

"Which block first" is the ordering the console summary prints, and the number
to put in the cell is that number read off the CSV rather than off the terminal
scrollback — which is what the grader's `which block moved first` line is, per
mark, where the console summary computes it once over the whole run. Its ms
figure is good to about one `--interval` (0.25 s by default), not to the
millisecond it is printed in: both timestamps are the sweeps that saw the
change, not the instant the byte moved. "Verdict" is the human's call against
§6, not the tool's: the grader prints a timing report and says so.

**Grade the capture before filling the table.** The offline grader for §3's
capture is `../../ec/tools/grade_gpu_door.py` (issue #283):

```console
python ec\tools\grade_gpu_door.py <date>-gpu-door-07c4-07d7.csv
```

It reads the file §3 writes as it stands — the same `ts,addr,old,new` rows and
`ts,MARK,,label` marks, one mark per window and none merged — and prints, per
mark, what moved in each block with its DSDT field-list name, which block moved
first and by how many ms, and a `net`/`total`/`max` line for all 24 watched
addresses whether or not they moved. It opens no EC, so it runs on any machine
with the repository checked out, including before the capture leaves the
Windows box.

**It fills five of this table's ten columns and names the five it does not.**
Columns 1-5 come out of the capture. Columns 6-9 — the ProcMon PID, the process
image, the IOCTL code on the `\.\ACPIDriver` handle and the loaded-module list
— are §4a's, read off a Windows `.PML` that no tool in this repository can
open, and column 10 is the human's call against §6. The grader prints that
split itself, so a table carrying only the first five cannot be mistaken for a
finished one.

## 6. What a result would settle, and what it would not

Written before the run, on purpose: the three-way reading below is what makes
the table's verdict column a judgement rather than a summary.

- **`0x07D0` moves under a GPU-only change, with no host `ECRW` at the mark** —
  evidence *for* the GPU reading of the byte, and the first thing anyone has
  observed rather than decoded. It does not establish that the EC acts on it:
  `T1WR 0x1173` sets `AMAT` from its own argument, not from the byte (§4o), so
  a movement with no visible host write is a question, not a confirmation.
- **Movement only when the Fn bundle runs** — a service write, and the
  `0x0743`-`0x0746` half is where to look for the one that did it. This is the
  result that changes the reading order least.
- **No movement at all, under all three actions** — the clobber hazard stays
  exactly as §4o records it: arithmetic on two decoded paths, not an observed
  failure. That is a result, and it moves §4o toward "a GPU power byte the
  BIOS writes" and toward the `AMAT`/`ATPP` double-writer hazard being
  arithmetically possible rather than reachable by any service the committed
  inputs can see.

The grader's per-window output is what these three are read against, and its
closing section says which of them a given capture can carry. It fills the
ordering half of the first — which block moved first, and by how many ms — and
has nothing to say about the `ECRW` half, which is §4a's. It names a capture in
which only one block moved as matching none of the three as written, rather
than picking the nearest one: a GPU-only change that moves the ACPI half alone
is not the second bullet either, and the verdict column is the human's. The
third is the quiet capture — three marks, thirty seconds apart, not one change
row — and the grader prints that as 24 zero lines per window rather than as
silence, because "nothing moved" and "nothing was recorded" have to be
different answers.

Two caveats belong next to the table rather than in a footnote.

- **The window delta is an endpoint net.** A byte that moves and comes back
  between two of the watcher's sweeps reads as quiet. A zero here is "not moved
  by this method under this action" — never "the GPU does not read it" — and
  read any zero through `../../ec/tools/grade_gpu_door.py` first: it prints
  `net`, `total` and `max` side by side for every address, and `total` is the
  figure that shows a move-and-return, which `net` cannot.
- **A readback is not an effect.** Nothing in this procedure checks whether the
  EC acted on a byte, and the table deliberately has no "readback OK ⇒
  confirmed" column. Do not add one. `../../CLAUDE.md`: a register write being
  accepted is not evidence the EC acts on it, and this run does not even write.

**A third caveat, added 2026-09-25 (issue #264): this procedure as written
cannot answer the `0x07D4`/`0x07D5` question it looks like it can.** The
GPU dynamic-boost path is four hops —
`0x0745`/`0x0746` → `0x09EA`/`0x09EB` → `0x07D4`/`0x07D5` → `ATPP`/`AMAT` —
drawn in full in `../../ec/annotations/ec-09e9-09eb-sites.md` §4. The middle
hop is on page `0x09`, and this procedure's watch set does not cover it:
`WINDOWS` in `../../windows/tools/gpu_block_watch.py` is `0x07C4`-`0x07D7` and
`0x0743`-`0x0746`, 24 addresses, **no `0x09xx` among them**.

So a run of this procedure can show that the `0x07C4`-`0x07D7` half did or did
not move, and that is worth having. It cannot separate the two readings of a
quiet `0x07D4`/`0x07D5` — "`0x83FF` did not run" versus "it ran and its
compare-before-write found them already equal to `0x09EA`/`0x09EB`" — because
that is a claim about a comparison between two values, and this procedure
would have an observation on only one side of it. The same gap applies to the
two committed captures §1 names: the 2026-09-23 file is
`0x0700`-`0x07FF`-scoped by its own filename, so `0x09E9`-`0x09EB` appear in
no row of it.

**The amendment this needs is a second watcher window over `0x09E9`-`0x09EB`
in the same session**, alongside the existing two, and that is a follow-up
rather than something to do here: extending `WATCH` would break the deliberate
24-address contract that `../../windows/tools/test_gpu_block_watch.py` pins —
"the check that stops the tool quietly growing into a third full-range
`0x0700`-`0x07FF` sweep, which is #94's problem to own" — and
`windows/tools/` is a different component whose `ECRR` pacing is #94's open
work. A human running this should know the limit before reading a zero, which
is what this paragraph is for. **Status: still not run.**

## 7. The citation list

Static, hand-checked into the tool's watch table and pinned there by
`../../windows/tools/test_gpu_block_watch.py`, which fails if any cell below
stops matching `../../evidence/acpi/dsdt.dsl` or
`../../ec/annotations/registers.yaml` — if this table's own status column
stops agreeing with the tool's, and if the EC-side cross-reference column of
the four rows the per-site census covers stops agreeing, in both directions,
with `../../ec/annotations/ec-07c4-07d5-sites.csv` and its `.md`. The DSDT
names and bits come from the `ECMG` field list at
`../../evidence/acpi/dsdt.dsl:52204-52212` and `:52238-52258`.

| addr | DSDT field (bit) | `registers.yaml` `status:` | EC-side cross-reference |
|---|---|---|---|
| `0x0743` | `GNEN` b0, `ECDC` b1 (`dsdt.dsl:52204`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, no `[writer]`-tagged site in the row |
| `0x0744` | `CTVA` (`dsdt.dsl:52207`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, no `[writer]`-tagged site in the row |
| `0x0745` | `DBCT` (`dsdt.dsl:52207`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, no `[writer]`-tagged site in the row |
| `0x0746` | `MXDB` (`dsdt.dsl:52207`) | `confirmed-working` — `CTGP_DB_CTRL` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, no `[writer]`-tagged site in the row |
| `0x07C4` | `DBEN` b3, `DBST` b5 (`dsdt.dsl:52238`) | `present-untested` — `GPU_DYNAMIC_BOOST_STATUS` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, writer `bank0:0x94C0=set_07c4_bit4_from_r7`; that is the one site the row's own tag names, not the only one in the image — `../../ec/annotations/ec-07c4-07d5-sites.md` §2-§4.1 is the full EC-image census: four sites in `bank0:0x83FF=sync_0788_and_07d4_from_09e9` (`bank0:0x843D` read, `bank0:0x844A` read, `bank0:0x8483` and `bank0:0x8490` read-modify-write of bit 3) and `bank0:0x94C1`, a read-modify-write of bit 4 inside `0x94C0=set_07c4_bit4_from_r7`, fed from bit 1 of `CTGP_DB_CTRL` by its one caller at `bank0:0x9711` |
| `0x07C5` | `WHMS` b5 (`dsdt.dsl:52243`) | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, writer `bank0:0xBB80=store_a_then_read_07c5` |
| `0x07C6` | `WMS0` b0-1 (`dsdt.dsl:52246`) | `present-untested` — `AP_OEM_6` | `xdata-registers.csv`: `main-ec`, `main-ec-002`, no `[writer]`-tagged site in the row |
| `0x07C7` | none declared | `unknown-not-absent` — `XDATA_07C7` | no row in `../../ec/annotations/xdata-registers.csv`; `../../ec/annotations/ec-07d6-07d7-sites.md` §1, §5 is the full census: **0** direct `MOV DPTR` sites in either image, which is "not found by this method" and not `absent` — §4c and #110 |
| `0x07C8` | none declared | `unknown-not-absent` — `XDATA_07C8` | no row in `../../ec/annotations/xdata-registers.csv`; `../../ec/annotations/ec-07d6-07d7-sites.md` §1, §5 is the full census: **0** direct `MOV DPTR` sites in either image, which is "not found by this method" and not `absent` — §4c and #110 |
| `0x07C9` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CA` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CB` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CC` | none declared | `present-untested` — `USB_C_POWER_PRIORITY` | `xdata-registers.csv`: `pd`, `pd-001`, writer `pd:0xF63F=store_r7_to_07cc_r5_to_0945` |
| `0x07CD` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CE` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-001`, no `[writer]`-tagged site in the row |
| `0x07CF` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-018`, no `[writer]`-tagged site in the row |
| `0x07D0` | `DBD1` (`dsdt.dsl:52248`) | `unknown-not-absent-DO-NOT-WRITE-BLIND` — `DBD1` | `xdata-registers.csv`: `pd`, `pd-027`, no `[writer]`-tagged site in the row (the row's own function tags are not a writer census; `../../ec/annotations/ec-0x07d0-sites.md` enumerates all 254) |
| `0x07D1` | `DBD2` (`dsdt.dsl:52248`) | `unknown-not-absent-DO-NOT-WRITE-BLIND` — `DBD2` | `xdata-registers.csv`: `pd`, `pd-026`, no `[writer]`-tagged site in the row |
| `0x07D2` | none declared | **no row** — see `../../ec/annotations/registers.yaml` | `xdata-registers.csv`: `pd`, `pd-016`, writers `pd:0x36F2`, `pd:0x68CE`, `pd:0xC755` |
| `0x07D3` | `GFID` b4-6 (`dsdt.dsl:52251`) | `present-untested` — `GFID` | `xdata-registers.csv`: `both`, `main-ec-002`, writers `bank0:0xBA46`, `pd:0xC755`; `../../ec/annotations/ec-07c4-07d5-sites.md` §2, §4.2 is the full EC-image census: `bank0:0x94D5` read (tests `GFID == 3`), `bank0:0xBA46=clear_low_nibble_07d3` a read-modify-write of the low nibble, and `bank0:0xDA2D` and `bank0:0xDA41` outright writes of `0x30`/`0x40`/`0x50`/`0x70` — `GFID` 3, 4, 5 and 7, branching on bit 4 of `0x166A` **within an arm chosen by bit 2 of `0x1666`** (issue #267 added the `0xDA22` outer select, which the first transcription of this block left out). Both selecting bytes now have rows — `XDATA_1666` and `XDATA_166A`, `present-untested`, 2 and 3 direct sites and all reads — and `0x1665` joined them as `XDATA_1665` with 6, its bit 6 setting or clearing bit 4 of `0x07A4` at `0xDA4F`. **What to watch, and why this row is here:** `GFID` is not EC-internal, unlike the three selectors — the ASL reads it in `Method (SMRW, 1)` (`dsdt.dsl:50764`), which compares it against `0x07`/`0x05`/`0x03`/`0x06` and with `PDIN` picks which of seven declared ACPI `Buffer`s to address (`ACPB`/`ACSB`/`ACPC`/`ACSC`/`ACPD`/`ACSD`/`ACPE`, `dsdt.dsl:50383-50414`), so a GPU-TGP change that moves `0x07D3` can change which buffer the OS addresses. Read it together with `0x0A51`/`0x0A52`, the seed pointer `0x94D0` derives from it, and with `0x07A4`, which `0x1665` bit 6 drives. The buffer is declared and `SMRW`'s caller is committed too (`WMIEC.cs:331-343` invokes it by name over WMI), so **what the EC does with the buffer the select lands on is not established** — that is the question this procedure exists to answer. *(issue #267 fix round 1: the seven buffers are declared at `dsdt.dsl:50383-50414` and `SMRW`'s caller is in the committed Windows decompilation, so the select picks an ASL buffer, not a register bank.*) |
| `0x07D4` | `CPUA` (`dsdt.dsl:52254`) | `present-untested` — `CPUA` | `xdata-registers.csv`: `both`, `main-ec-002`, writers `pd:0xD013`, `pd:0xEE68`; `../../ec/annotations/ec-07c4-07d5-sites.md` §2, §3 adds the two bank0 sites `xdata-registers.csv` does not name: `bank0:0x8460` read and `bank0:0x8477` write, both in `bank0:0x83FF=sync_0788_and_07d4_from_09e9` and both under the `CTGP_DB_CTRL` (`0x0743`) bit-0 guard, copying `[0x09EA]` in |
| `0x07D5` | `DBAP` (`dsdt.dsl:52254`) | `present-untested` — `DBAP` | `xdata-registers.csv`: `both`, `main-ec-002`, writers `pd:0xD013`, `pd:0xEE68`; `../../ec/annotations/ec-07c4-07d5-sites.md` §2, §3, §4.3 adds the four bank0 sites `xdata-registers.csv` does not name: `bank0:0x846C` read and `bank0:0x847F` write, both in `bank0:0x83FF=sync_0788_and_07d4_from_09e9`, copying `[0x09EB]` in; and `bank0:0xAD99` and `bank0:0xCC78`, both storing `0xFF`, the first inside `reset_xdata_flags_and_07d5_to_ff` and the second in a run of the same three instructions whose entry point is not determined |
| `0x07D6` | `DBSP` (`dsdt.dsl:52254`) | `unknown-not-absent` — `DBSP` | `xdata-registers.csv`: `pd`, `pd-028`, writers `pd:0xBECB`, `pd:0xF247`, `pd:0xF440`; `../../ec/annotations/ec-07d6-07d7-sites.md` §2, §3 is the full census: all **142** sites are `pd-image` and **none** is main-EC, so none of them is an EC-side reference — §1, §7 |
| `0x07D7` | `CGCT` (`dsdt.dsl:52254`) | `unknown-not-absent` — `CGCT` | `xdata-registers.csv`: `pd`, `pd-029`, writers `pd:0xABBF`, `pd:0xBECB`; `../../ec/annotations/ec-07d6-07d7-sites.md` §2, §3 is the full census: all **71** sites are `pd-image` and **none** is main-EC. The ASL writer the scan cannot see is `T1WR`'s `Arg0 == 0x1176` branch, `dsdt.dsl:50730-50733` — §7 |

Four notes on reading the table, each of which is a place a table like this
gets misread:

- **"No row" is a statement about `registers.yaml`, not about the address.** It
  is 8 of the 24, and it is the §4c retraction in table form
  (`../../docs/findings.md` §4c retracted a "does not exist" claim built on a
  zero-reference scan). 8 cells saying "no row" is the sentence most
  likely to be read back as 8 claims of absence; they are not. The per-site
  EC-side census of the six rows that do have one is
  `../../ec/annotations/ec-07c4-07d5-sites.md` and
  `../../ec/annotations/ec-07d6-07d7-sites.md`, which walk the fifteen
  main-EC sites of `0x07C4`/`0x07D3`/`0x07D4`/`0x07D5` and the 213 sites
  that `0x07D6`/`0x07D7` have in a *different* firmware image — a write
  *class* in the instruction stream, not evidence the EC acts on the byte.
  The four `0x07C7`/`0x07C8`/`0x07D6`/`0x07D7` rows are all
  `unknown-not-absent`, which is the status value for "the references that
  made it look present turned out to belong to the PD image" and is not a
  softer spelling of `absent`.
- **`0x07C4`'s `DBEN` is bit 3, not bit 0.** §4o writes the gate as "`DBEN`
  (`0x07C4` bit 0)"; the field list at `dsdt.dsl:52238-52242` allocates three
  unnamed bits before it, so `DBEN` is bit 3 and `DBST` bit 5. The bit column
  here is the field list's, and the suite checks it against the file rather than
  against prose. §4o's prose is left as written rather than edited from here.
- **`0x0743`'s bit semantics differ between the two sources, and both are
  right.** The DSDT field list names two bits (`GNEN` b0, `ECDC` b1); the
  `registers.yaml` note describes three (bit 0 DB function control, bit 1 DB
  enable, bit 2 cTGP enable). The name column is the field list's; the status
  column is `registers.yaml`'s. Neither file is corrected by this one.
- **The `xdata` columns name their file every time, including when the answer
  is no row.** A bare "none" is indistinguishable from a scan that did not run.
  `../../ec/annotations/xdata-registers.csv` and
  `../../ec/annotations/xdata-clusters.csv` are inputs this procedure only
  reads; `../../ec/ghidra/xdata-symbols.csv` is generated from
  `registers.yaml` and must never be hand-edited.

## 8. Where the output goes

Name the files the way the existing captures do, so a reader can pair them:

```
evidence/ec-watch/<date>-gpu-door-07c4-07d7.csv
evidence/ec-watch/<date>-gpu-door-07c4-07d7-marks.txt
evidence/ec-watch/<date>-gpu-door-procmon.pml
```

`<date>` is that run's YYYY-MM-DD — the same placeholder §3's command takes, so
following this list produces this set with no rename step. The CSV is the
capture itself, both blocks and every mark in one file; `CsvSink` opens it in
append mode (`../../windows/tools/ec_watch.py:91-96`), so a second run into the
same name extends the file rather than replacing it, which is also why the two
runs must not be merged by hand afterwards (§3).

The marks file is the one §4a.2 leaves unnamed. That step says to keep the
mark labels and their timestamps "on paper or in a text file next to the
trace" because the `.PML` carries none of them; the committed one is this
name, and it holds the same `ts  label` pairs the CSV already carries — as
text, so a reader looking for "what happened at 14:32" can grep it without
parsing a capture. If §3's three actions were each marked with an opening and
a closing label, they are here in that order, and that order is the whole of
§5's mark column.

The `.PML` is §4a.2's saved trace under the same `<date>-gpu-door-` prefix,
and it is the only one of the three that is not text: a ProcMon capture
records a stack walk, so the file is large and does not read in a diff. The
marks file is what pairs it to the CSV, which is why it is a separate artifact
rather than a comment in either.

Add all three to `evidence/README.md`, which is the index every findings claim
cites through, and say in that entry what the run was: the date, the starting
AC state (§2 asks for it written down), the TGP values as the UI showed them,
the Fn mode on each side of the mode switch, how long the capture ran, and the
three actions in the order they were taken. None of that is in the CSV, and
§5's rows are unreadable without it — a `gpu tgp 115W->130W` mark beside an
`ac plug` mark says nothing about either action if the run started on
battery.

No parser is needed to read the capture. The schema is `ts,addr,old,new` with
a mark as `ts,MARK,,label` — `ec_watch.py`'s own, and the one
`../../ec/tools/grade_gpu_door.py` and
`../../ec/tools/grade_0751_isolation.py` already read, which is what lets
§5's grader take this file as it stands. `gpu_block_watch.py` prints a
windowed summary at the end, and that summary is a timing report rather than a
grade: §5's ordering cell is read off the CSV, and
`../../ec/tools/grade_gpu_door.py` (issue #283) owns the reading.

## 9. What a result has to say

**A capture that shows a byte move is an observation of movement, not a live
test of the register.** That distinction is the whole of this section, and
`../../CLAUDE.md` states it for the neighbouring case — a register write being
accepted is not evidence the EC acts on it; this run does not even write, and
a byte appearing between two of the watcher's sweeps says only that it was
different at those two moments.

So, concretely:

- **`CPUA` (`0x07D4`) and `DBAP` (`0x07D5`) keep `present-untested`** in
  `../../ec/annotations/registers.yaml` whatever the capture shows, and the
  `0x07D0`/`0x07D1` pair keeps `unknown-not-absent-DO-NOT-WRITE-BLIND` on the
  same grounds. The reason is that file's own vocabulary rather than a
  judgement call: `confirmed-inert` is "write accepted, EC does not act on it
  (proven live)", which a run that writes nothing cannot reach, and
  `confirmed-working` is "live behaviour matches the driver's model", and
  there is no model here for a byte no driver drives. What a capture *can*
  produce is a note entry — *this byte moved under this action on this
  machine* — and that is worth having. Note what it does not settle: the EC
  copies these two from `0x09EA`/`0x09EB`
  (`../../ec/annotations/ec-07c4-07d5-sites.md` §3) and neither is in the
  watch set, so a row recording that `CPUA` moved says nothing about which
  side moved it. §4a is the half that narrows that, and only for a host
  write — an EC-internal one raises no `DeviceIoControl` to be captured.
  Record the movement; do not promote it. `GPU_DYNAMIC_BOOST_STATUS`'s own
  note already ends on that rule for the 2026-09-23 capture — "a passive
  capture showing a byte move is not a live test of it" — and a GPU-only TGP
  change in the capture does not move it either.
- **The `0x07D0`, `0x07D1` and `0x07C4` notes are updated from the committed
  capture file, in the same PR that adds it.** Each records only what
  `evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv` showed across
  an AC plug-in and six Fn mode switches, neither of them a GPU-only TGP
  change: `0x07C4` has the two rows it carries, and `0x07D0` and `0x07D1`
  did not move at all in that window — "not found to move here", scoped to
  those events, and not "never written". A run that contains the action none
  of them contains is the evidence that changes what they say. A note citing a
  file that is not in the same commit is a claim no reader can check, which is
  the same defect `evidence/README.md` being an index exists to prevent.
- **The grading is `../../ec/tools/grade_gpu_door.py`'s, not this section's.**
  That grader is committed (issue #283) and already fills §5's columns 1-5, so
  a returned capture is graded by a tool this repository already holds rather
  than by anything written for it here. The summary `gpu_block_watch.py` prints
  is a timing report and says so; §5's verdict column is the operator's call
  against §6; and §6's three-way reading is what that call is read against.
  Nothing in this section is a fourth reading to be applied instead.
- **Mixed, ambiguous, or empty is a result.** A run in which nothing moved
  leaves §4o where it is and says so; a run in which the two windows moved on
  different marks is a result the capture goes into `evidence/` with. Either
  way the capture is committed and this file's status header stays
  **not run** until a run it describes has actually been taken.

And a run that never happens is not a failure of this file. Nothing above is
written to be filled in, and no part of it reports anything: the header stays
"not run", the three notes keep the 2026-09-23 scope, and issue #278 stays
open until a human with the machine closes it.

## Cross-references

- **#87** owns mapping each MQTT `*/Control` command to its EC-register effect.
  The register-effect half of a Control Center GPU action is not repeated here.
- **`../../ec/tools/grade_gpu_door.py`** grades a §3 capture (issue #283), and
  fills §5's columns 1-5 while naming columns 6-10 as not its own. It emits a
  CSV in the schema `ec_watch.py`, `../../ec/tools/grade_0751_isolation.py`
  and it already read, so grading needs no parser written for this file. It
  states its own copy of the two window bounds and the 24 DSDT names because
  it cannot import `gpu_block_watch.py` — that module imports `ecrw`, which
  binds `kernel32` at import time, and an offline grader that imported it would
  load only on Windows. `../../windows/tools/test_gpu_block_watch.py` holds the
  two copies together, the same shape of hold as the one that caught this
  procedure's four stale cells in #266.
- **#96** and **#1** are what the answer feeds: the upstream correction must not
  be written as though `0x07D0` has one meaning, and the paired `0x07B9`/
  `0x07D0` write is still the experiment that would settle whether the byte is a
  threshold at all.
- **#8 / `ctgp_live_test.py`** established the `0x0743`-`0x0746` half
  host-side against `nvidia-smi`, and is the established *writer* for that
  block. It does not watch `0x07C4`-`0x07D7`, which is why this tool exists
  alongside it rather than instead of it.
- **#131 / §4o** is the census this procedure is the human half of, and
  `../../windows/tools/t1wr_callers.py --self-check` is what must still pass for
  its negative to mean what §4o says it means.
- **#94** owns `ECRR` pacing and is why `--interval` is a starting point here.
- **`../../ec/annotations/ec-07c4-07d5-sites.md`** is the per-site EC-side
  census of the `0x07C4`/`0x07D3`/`0x07D4`/`0x07D5` rows above, all fifteen of
  their main-EC sites. It supersedes the single-site credit this table gave
  `0x07C4` before, and it reads a write class, not an effect.
- **`../../ec/annotations/ec-07d6-07d7-sites.md`** is the same treatment for
  `0x07D6`/`0x07D7` and the two companion `0x07C7`/`0x07C8` cells, and it
  answers in one place what a per-site EC-side census cannot for these four:
  that all 213 of their sites are in the ITE8850-PD image and none is in the
  EC firmware at all, which is why their status is `unknown-not-absent`
  rather than `present-untested` even though §7's column is populated. §7 of
  that file is the ASL side the firmware scan is blind to by construction.

---

**Running this is a human step on the physical GM7MG7P. This repository
contains no result from it.**
