# Does bit 0 of `0x07A6` clear, and on what?

**Status: not run.** The pipeline that wrote this file has no machine to run it
on — `CLAUDE.md` is explicit that the GitHub-hosted runners cannot reach the
hardware. Nothing below is an observation. Every live value this file quotes is
a prior capture cited as a prior observation, in the same way
[`oem4-bit-map-and-bit0.md`](../findings/oem4-bit-map-and-bit0.md) §7 quotes
`0x29` and `0x28`: *"No sweep was re-run; that is a human's job at the
machine."* The grading rule in §4 is written down **before** the run, which is
the point of writing it here rather than after seeing what happens.

No `status:` in `ec/annotations/registers.yaml` moves on the strength of this
file, and `0x06E2` gets no entry: a static instruction sequence and a planned
procedure are not a status. See §7 for what each outcome would and would not
license.

## 1. The question

`0x07A6` is `OEM_4` (`CHARGING_PROFILE_MASK`) in
`../../ec/annotations/registers.yaml:327`). Bits 4-5 are the vendor's
battery-protection profile and are the only bits with a decoded writer
(`BatteryProtection2.SetHealthProtection*` in
`windows/decompiled/v3.1.39.0/GCUService/GCUService.MySystem/BatteryProtection2.cs`).
Bit 0 is a different matter: it has one EC-side setter, and across the seven
reference sites no clearer and no reader was found by those scans
([`oem4-bit-map-and-bit0.md`](../findings/oem4-bit-map-and-bit0.md) §7).

**So: does bit 0 clear in response to a named event, and if so to which one?**
That is the whole question. It has one committed answer candidate and it is not
a run of this procedure.

### 1.1 What the disassembly says

The chain is four instructions long and it is worth writing out, because every
piece of the reasoning below is one of them:

- `../../ec/decompiled/bank0/AB6E.asm:24` — `AB90 20 e0 0a  jb 0xe0, 0xab9d`
  tests **bit 0 of `0x06E2`**.
- `../../ec/decompiled/bank0/AB6E.asm:25-28` — the fall-through path
  (`AB93`-`AB99`) reads `0x06E2`, `orl A,#0x01`, writes it back.
- `../../ec/decompiled/bank0/AB6E.asm:29` — `AB9A 12 ab 9e  lcall 0xab9e`.
- `../../ec/decompiled/bank0/AB9E.asm:7-9` — `AB9E mov DPTR,#0x782` /
  `ABA1 movx A,@DPTR` / `ABA2 30 e1 1b  jnb 0xe1, 0xabc0`, the **bit-1 gate on
  `0x0782`** (`BIOS_OEM_2`), which skips the setter when set.
- `../../ec/decompiled/bank0/AB9E.asm:24-27` — the setter proper:
  `mov DPTR,#0x7a6` / `movx A,@DPTR` / `orl A,#0x01` / `movx @DPTR,A`.

**"Rising edge" is an effect the EC produces, not a mechanism to look for.**
`jb` at `AB6E.asm:24` is a *level* test and there is no `jnb`/`ank`/`ajnb` edge
primitive anywhere in this path. The edge behaviour is derived from what
follows: if bit 0 is already set, `jb` skips straight to the `ret` at `0xAB9D`;
only on a 0→1 transition does control fall through to the set-if-clear
write-back and the `lcall`. `../../ec/annotations/ghidra-functions.csv:151`
states the same intent for `set_06e2_bit0_from_c412`. A reader who goes looking
for edge-detection hardware at `0xAB90` will not find any, and "one-shot on a
rising edge" as a *mechanism* is a claim these listings do not carry.

**And a static sequence shows the EC writes the bit, not that it acts on it.**
Per `../../CLAUDE.md`, a write being accepted is not evidence of behaviour.
This file's question is the behaviour half, which is why it needs a machine.

### 1.2 Two cited files do not exist

Issue #1200 cites `0x08505 -> 0xAB6E -> 0xAB9E`, and in the finding it quotes,
`0xABC0`. Neither `ec/decompiled/bank0/08505.asm` nor
`ec/decompiled/bank0/ABC0.asm` is in the tree — `find -iname` over the whole
repository returns nothing for either. `0x8505` exists as code (an `lcall
0xab6e` inside the `bank0-transfer-run` dispatcher at `0x8502`) but has no
exported listing, and `0xABC0` is **not a function entry**: it is 34 bytes
interior to `set_0751_and_07a6_bits` at `0xAB9E`, which
`../../ec/decompiled/index.csv:169` gives a length of 106 bytes. The
`AB9E.asm:24-27` citation above is the correct one and is what this file uses.

### 1.3 `0x07A7`-`0x07AA` is not a profile block beside `0x07A6`

Issue #1200 lists these four bytes "so a profile-block write beside `0x07A6` is
visible". They are not beside it in any sense that survives contact with
`../../ec/annotations/registers.yaml`: they are four of the twelve members of
`MODE_PL_DEFAULTS` (`:2133-2141`), the per-mode PL1/PL2/PL4/D-state defaults —
`0x0730`-`0x0737` for Gaming and Office, `0x07A7`-`0x07AA` for **Turbo**.
They share no name and no semantics with `OEM_4`, and the adjacency is a layout
coincidence.

That entry's note (`:2152-2157`) records something stronger and worth having
here: **all 18 EC-side sites of the twelve bytes are stores and none of them is
a read**, and `:1842-1844` says the same of the block as a whole. So they cannot
serve as a probe of `0x07A6` whatever a run shows — there is nothing on the
other end to compare a probe against.

They stay on the watch list for a better-stated reason, given in §4.2: a BIOS
load-defaults is a plausible trigger for a bulk EC defaults reload, and a move
of all four together is the signature of `copy_code_table_into_0730_07a7`
(`../../ec/annotations/ghidra-functions.csv:106`) rather than of four unrelated
writers.

### 1.4 `0x06E2` has never been read into `evidence/`

Verified: no `addr:` line in `../../ec/annotations/registers.yaml` contains
`06E`, in any case, and no range-typed `addr:` spans it. It appears only as a
CSV row (`../../ec/annotations/xdata-registers.csv:580`,
`0x06E2,main-ec,DAT_EXTMEM,0x06E1-0x06E4`) and in
`ghidra-functions.csv:151`'s prose. Across all of `evidence/ec-watch/` and
`evidence/battery-traces/` it appears nowhere at all — not as a change row, not
as a static read.

**That is "not found by this method", never "the register is undocumented."**
It is also a large part of why arm 2 exists: watching a byte nobody has ever
watched is the cheapest way to find out whether the `0x06E2` edge is a real
event or a path that never runs.

### 1.5 The two prior readings, and what the second of them is not

This run is compared against two committed readings, both cited here as prior
observations and neither re-run.

- **2026-09-19, `0x29` → `0x28`,** after a BIOS load-defaults: bit 0 cleared and
  nothing else in the byte moved. `docs/findings.md` §4j is the record. The
  value survives in `evidence/battery-traces/2026-09-19-windows-bios-defaults.csv`
  (its `ec_07a6` column reads `0x28` throughout the Stationary phase, then
  `0x08` in `cv88_switch_to_highcap` — see below).
- **2026-09-23, `0x29` → `0x09`,** the only `0x07A6` row in
  `evidence/ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv:5`.

**The second of those is not a bit-0 event at all.** Reading the two as the same
single-bit event — bit 0 clearing alone from `0x29` — would make the whole run
look like a re-run of something already known, and it does not survive
arithmetic.

`0x29` is `0b00101001` and `0x09` is `0b00001001`. Their XOR is `0b00100000`:
**bit 5** is what differs. Bit 0 is `1` in *both* values. The 2026-09-23 row is a
change to the **profile field**, bits 5-4 stepping `0b10` → `0b00` — Stationary
to High capacity — and not a bit-0 clear.

Nor is it an unexplained event. `evidence/ec-watch/2026-09-18-profile-switch-0700-07ff.csv`
carries the identical first step, and its three `0x07A6` rows read `0x29 → 0x09
→ 0x19 → 0x29`: the vendor UI walking all three protection profiles, exactly the
`0b10`/`0b00`/`0b01` encoding `../../ec/annotations/registers.yaml:346-349`
records. `0x29 → 0x09` in a capture is what a profile switch looks like.

So, stated as the evidence supports it:

- **Exactly one committed bit-0 clear exists**, the 2026-09-19 `0x29` → `0x28`,
  and it came from a **BIOS load-defaults**. That is what makes arm 3 the arm
  carrying the prediction, and it is why §4's table gives each arm a different
  one.
- The 2026-09-23 row is evidence about bits 5-4 and nothing else. It says
  nothing about bit 0.
- **The 2026-09-19 trace also records the profile moving.** Its `ec_07a6` column
  reads `0x28` for 134 rows and `0x08` for 51, the second block being the
  `cv88_switch_to_highcap` phase — `0x28` with bits 5-4 cleared. That is the
  profile writer again, and it is the same fact the 2026-09-18 capture records
  more cleanly. Worth having: the two mechanisms really do write the same byte
  independently, which is what makes a single-`0x07A6`-row capture ambiguous and
  what §4.2 separates.

### 1.6 The 2026-09-23 attribution, weakened to what the file supports

Issue #1200 writes that *"the 2026-09-23 capture shows a
power-mode event moving the byte"*. The file supports the transition and not the
attribution. That file has **zero** `MARK` rows, so nothing in it records what
the operator was doing at `17:57:47`. The nearest neighbouring activity is 2.1 s
later (`0x070F`/`0x071A`/`0x071B`/`0x071C`/`0x0783` at `17:57:49.970`–
`17:57:51.157`), and the file's own `0x0751` rows begin at `17:59:00`, 73 s
after the `0x07A6` row.

Write it as **"the byte moved `0x29` → `0x09` during a run that was a
power-mode cycle; which action it coincided with is not decidable from the
file"** — not as "a power-mode event moved it". Given §1.5 the profile field is
the better-supported reading of what moved, but the file does not say what the
operator did, and this file does not supply the missing answer.

## 2. Before you start

**This procedure writes nothing.** There is no `ecrw.py write` anywhere in §3
and no `--i-mean-it` on any line; every command is a read (`ecrw.py dump`) or a
watch (`ec_watch.py`). Nothing here can change a register, and the arm that
involves a BIOS reset is the reason that matters: it is the one thing that makes
a three-arm procedure ending in a reboot safe to hand to a person at a laptop.
The one write the operator does perform is the BIOS load-defaults itself, done
from setup, with the same risk as any other firmware reset.

- Windows, Control Center 3.1.39.0 installed, and `ecrw.py`'s driver path
  working — `python windows\tools\ecrw.py read 0x07A6` should print a value.
- **Record the starting value of `0x07A6` and of `0x0782`**, and the current
  power mode and battery-protection profile as the vendor UI reports them. A
  hand-written snapshot header in the snapshot style of
  `evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt` is the format to
  copy: date, AC or battery, power mode, profile, Control Center running or
  stopped, and what was done in each arm. That file is the record of the
  starting state, because nothing else in the set is.
- **Note whether the Control Center's battery-protection profile is Stationary,
  Balanced or High capacity** before arm 2. §1.1's chain and §4's predictions
  both turn on bits 5-4 holding or moving, and which way they were left is not
  recorded in any capture.

## 3. The run, three arms

Issue #1200 names four addresses. They need **two watchers**, and §3.1 says why
rather than leaving it arbitrary.

### 3.1 The addressing

- **`--start 0x0700 --len 0x0100`** carries `0x0782`, `0x07A6` and
  `0x07A7`-`0x07AA`. This is deliberately the same window as the committed
  `2026-09-23-power-mode-cycle-0700-07ff.csv`, so a re-run is directly
  comparable to the one `0x29` → `0x09` row. Comparability is worth more here
  than console count. All of `0x0700`-`0x07FF` was swept whole by that committed
  run, and the sibling-board `ECRR` stall is at `0x0460`-`0x046F`
  (`../related-projects.md`, issue #94), far outside this window.
- **`--start 0x06E0 --len 0x0020`** carries `0x06E2`, which has never been
  watched and has never been read into `evidence/` (§1.4). Nothing else in
  `0x06E0`-`0x06FF` is of interest, which is the point of stopping there.
- A single `--start 0x06E0 --len 0x00D0` would cover all four in one console.
  **Rejected on the comparability ground above**: a wider window produces a
  capture that is not the committed capture's window, and §4.2's read-off wants
  to line the two up. Stating the rejected option is what makes the choice
  visible rather than arbitrary.

**`--label-vocab` is deliberately not used.** `../../windows/tools/ec_watch.py:529`
hardcodes `--label-vocab` to `choices=("0751",)`, and `load_label_vocab` resolves
that one name to that one grader module. There is no `07a6` vocabulary, and
adding one means editing a shared tool *and* its 1,359-line test file — the
merge surface `CLAUDE.md` warns about — for a flag whose value here would be a
convenience.

**What that costs, stated plainly: without `--label-vocab` the mark prompt does
not check labels against a grader's parse.** §6's label table is the only thing
standing between the operator and a mistyped mark, and the operator has to read
it rather than be caught by it. See
[`ec_watch-marks.md`](../../windows/tools/ec_watch-marks.md), which is where the
tree already explains the free-form case.

```console
rem  <date> is that run's YYYY-MM-DD. §6 names the finished files the same way,
rem  so following this list produces the §6 set with no rename step. The two
rem  CSVs are ONE file each for the whole run, because ec_watch.py appends to a
rem  --csv file that already exists and the marks say which arm each row
rem  follows; the dumps are per-arm, because a dump is a whole-range read with
rem  no marks inside it and the filename is the only thing saying what it
rem  brackets.
rem
rem  --interval 0.5 is a starting point, not a validated-safe value; see the
rem  pacing note below before leaving it there.

rem  --- 0. the by-hand record, before anything is started (§2) ---
rem      hand-written, in the style of evidence/ec-watch/
rem      2026-09-23-power-mode-snapshot-dc.txt, to
rem      <date>-oem4-07a6-bit0-snapshot.txt

rem  --- 1. arm 3's "before", taken now so it brackets the reboot ---
rem     (taken here rather than in arm 3 so it is on the same machine state
rem      the watchers see, and so the operator has one place to start)
python windows\tools\ecrw.py dump 0x0700 0x0100 ^
        > <date>-oem4-07a6-bit0-load-defaults-before-0700.txt

rem  --- 2. both watchers, two consoles, covering arms 1 and 2 ---
python windows\tools\ec_watch.py --start 0x0700 --len 0x0100 --seconds 600 --interval 0.5 ^
       --mark --csv <date>-oem4-07a6-bit0-0700-07ff.csv
python windows\tools\ec_watch.py --start 0x06E0 --len 0x0020 --seconds 600 --interval 0.5 ^
       --mark --csv <date>-oem4-07a6-bit0-06e0-06ff.csv

rem  --- 3. arm 1, the no-op control: mark, wait ~120 s, mark ---
rem  mark each console: arm 1 control start
rem     ... change nothing at all for ~120 s ...
rem  mark each console: arm 1 control end

rem  --- 4. arm 2, the power-mode cycle: mark, cycle, settle, mark ---
rem  mark each console: arm 2 cycle start
rem     ... switch power mode with the vendor UI, and watch what it rewrites ...
rem  mark each console: arm 2 cycle end

rem  --- 5. stop both watchers (Ctrl-C), then arm 3 ---
rem     the reboot cannot be watched live; see the note before this block

rem  --- 6. arm 3's "after", on return from setup ---
python windows\tools\ecrw.py dump 0x0700 0x0100 ^
        > <date>-oem4-07a6-bit0-load-defaults-after-0700.txt

rem  --- 7. a fresh watcher on return, for the post-boot settle ---
rem     this is context for the dumps above, not the graded artifact
python windows\tools\ec_watch.py --start 0x0700 --len 0x0100 --seconds 180 --interval 0.5 ^
       --mark --csv <date>-oem4-07a6-bit0-0700-07ff.csv
rem  mark this console: arm 3 returned from setup
```

`--seconds 600` leaves room for what this section actually mandates — ~120 s
control + ~300 s power-mode cycle ≈ 420 s — plus four mark rounds typed by hand
across two consoles, which is eight presses, plus the settle time the operator's
own mode switch needs. **A `--seconds` that leaves no room for a hand-typed mark
is the defect [`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md)
§3 already records**, and a mark typed after a watcher has exited is written
nowhere. The check is mechanical: `ec_watch.py` prints `=== N sweeps over Ms`
and then every mark it recorded when it stops, so the last label in that list is
the last mark the capture has.

### 3.2 Arm 1 — the no-op control

Watch, change nothing, for the same duration as arm 2.

**It is not optional, and the reason is one sentence: without it, a transition
in arm 2 cannot be attributed to the event rather than to time passing.** The
same reason issue #122 tightened
[`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md) for its
own no-op arm.

Marks: `arm 1 control start`, `arm 1 control end`.

### 3.3 Arm 2 — the power-mode cycle

The operator's own power-mode switching, per this directory's existing
understanding of that event. **§1.5 changes what this arm predicts**: the one
committed power-mode-cycle capture moved the *profile* field, not bit 0. So this
arm's prediction is that bits 5-4 may move and **bit 0 should not** — which is
what makes it discriminating rather than a second attempt at arm 3.

Marks: `arm 2 cycle start`, `arm 2 cycle end`.

### 3.4 Arm 3 — the BIOS load-defaults, which is not a window

**Read this before the operator reaches §3's block 5, not after they reboot.**

`ec_watch.py` is a Windows process and this tree carries no persistence
mechanism to carry it across a reboot. **A load-defaults therefore cannot be
watched live, and §3 does not pretend otherwise.** The arm is a before/after
`ecrw.py dump` pair around the reboot — the pair
[`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md) §6
already mandates and `../../ec/tools/grade_0751_isolation.py --dump-pair` already
reads — plus a fresh ~180 s `--start 0x0700 --len 0x0100` watcher on return,
which catches the post-boot settle as context and not as the graded artifact.

This is the most substantive departure from #1200's framing, which lists all
three arms as watches. It has to be in the document rather than discovered by the
human at the machine.

**MARK placement.** One mark, on the post-boot watcher, recording that the return
happened. The reboot itself cannot be marked from a process that did not survive
it.

Marks: `arm 3 returned from setup` (post-boot watcher only).

### 3.5 Why the marks are on every arm boundary anyway

The capture should not add to issue #1189's count. Measured on this tree: of the
**10** committed `.csv` captures under `evidence/ec-watch/`, **8 carry no `MARK`
row**; across the whole **15**-file directory it is **13 of 15**. (Re-derive
rather than trust those figures — they move as captures land: `grep -L MARK
evidence/ec-watch/*.csv`. #1200's own denominator silently excluded the five
`.txt` captures, which is why both figures are given.)

Marks on every arm boundary are also what makes the graded windows *decidable*.
A window is the changes between two marks, so a missing mark makes an arm quiet
for want of a mark rather than because nothing moved — the failure
`0751-isolation-run-missing-mark` exists to exercise. Without marks on every
boundary, §4's table cannot be applied mechanically to a capture at all.

### 3.6 Bus traffic, and the interval

Two concurrent watchers over `0x100 + 0x20 = 288` bytes put **288 `ECRR` reads
per sweep pair** on the bus, for as long as the run lasts.
`ecrw.Ec.read` (`../../windows/tools/ecrw.py:149`) is one `ECRR`
`DeviceIoControl` per byte with nothing between calls, and `ec_watch.py` reads
every address in its range once per sweep with `--interval` slept *between*
sweeps, not between bytes. Both ranges are whole numbers of aligned 4-byte
blocks, so a `--block` run is `0x100/4 + 0x20/4 = 72` IOCTLs — a **call count,
not a statement that the traffic is safe**. The path has never been run against
the driver on this machine.

**There is no safe interval to hand you from here.** How long one IOCTL takes is
not measurable without the driver and the machine, issue #94 is the open work to
make these tools safe by default, and nothing in this repo measures it. If the
fans audibly change during a run, raise `--interval` and redo the run.

## 4. What to read off, and the rule — written down in advance

### 4.1 The prediction, named before the run

Stated per arm, because §1.5 showed the three arms do not predict the same thing:

| arm | prediction | where it comes from |
|---|---|---|
| 1, control | `0x07A6` does not move at all | the control's own definition |
| 2, power-mode cycle | bits 5-4 may move (`0b10` ↔ `0b00` ↔ `0b01`); **bit 0 does not** | the 2026-09-23 row moved bits 5-4 and left bit 0 set (§1.5) |
| 3, load-defaults | **bit 0 clears, and bits 5-4 hold** — `0x29` → `0x28` | the one committed bit-0 clear, `docs/findings.md` §4j |

The falsifiable form of arm 3 is the one that matters, and it is narrower than
"something happens": **bit 0 clears alone, and the rest of `0x07A6` is
untouched.** A byte that steps to `0x28` and back is a different result from one
that holds `0x28`, and §4.4 says how to tell them apart.

### 4.2 Read off, per arm

For each window between marks:

- The `0x07A6` rows, as `old` → `new`.
- **The net and the total.** *Net* is where the byte opened the window against
  where it closed it; *total* is the sum of the absolute steps it took inside.
  A byte that steps and returns has `net 0` and a non-zero total, and only the
  net makes a two-step move look like one. The distinction
  `0751-isolation-example-multi-move-0400-045f.csv` exists to hold.
- **Whether bits 5-4 moved separately from bit 0.** This is §1.5's finding made
  mechanical, and it is the difference between "bit 0 cleared" and "the profile
  changed, which also happens to clear a bit nobody is asking about".
- Whether `0x07A7`-`0x07AA` moved **as a four-byte group** (the
  `copy_code_table_into_0730_07a7` signature) or not at all. That function's own
  gate is bit 2 of `0x0782` (`../../ec/decompiled/bank0/94D0.asm:97,100` —
  `9575 mov DPTR,#0x782` / `957C jnb 0xe2, 0x9599`), which is inside the
  `0x0700`-`0x07FF` window, so the watcher covers the gate and the block
  together. `0x9D` read on 2026-09-23 has bit 2 set.

For arm 3: **the dump diff at `0x07A6` and nothing else.** The graded artifact is
the before/after pair, not the post-boot watcher.

**Anything at all moves in the control arm → the run is void.** Restate and
re-run. Without that clause a transition anywhere is unattributable, which is
the entire reason the control arm is in §3.

### 4.3 What each outcome means

- **Arm 3: bit 0 clears and holds, bits 5-4 still** → the 2026-09-19 observation
  reproduces, and §1.1's static chain gets its first live support for the
  *event*. Say what it does **not** license: one observation of a correlation is
  not the setter's identity, and it says nothing about whether `0x06E2` is what
  caused it here. "A BIOS load-defaults clears bit 0" is a reproducible claim
  about one machine; "the `0x06E2` edge is the mechanism" is not earned by it.
- **Arm 3: bit 0 clears and returns inside the session** → the clear is real and
  something set it back. That is a *third* mechanism in play (nothing found by
  the static scan has a clearer), and it is a bigger finding than the clear.
- **Arm 3: bit 0 does not clear** → the 2026-09-19 row does not reproduce, and
  the negative becomes load-bearing: the one committed bit-0 clear may have been
  a one-off. §4.6 says what a negative result is worth.
- **Arm 2: bits 5-4 move and bit 0 does not** → the 2026-09-23 and 2026-09-18
  captures reproduce as profile writes, and arm 2's contribution is to have
  *not* moved bit 0. This is a clean, expected result, not a failed arm.
- **Arm 2: bit 0 clears** → this would be the genuinely new observation, and the
  one the static chain would most want. Write it up as its own finding.
- **Nothing moves in any arm, control quiet** → the 2026-09-19 row is a one-off
  and the negative becomes load-bearing. This is an outcome CLAUDE.md's
  calibration section is about, and **it is a result, not a failed test.**

### 4.4 The two figures are not interchangeable

Stated here because §4.2 asks for both and a reader who has only ever seen one
will pick the wrong one. *Net* is the cleanest summary of a clean monotonic step
and is blind to any movement that came back. *Total movement* counts the whole
path. Where they disagree, the byte wandered — and a byte that climbed to a new
value and then wandered back ends near where it started and nets to nearly
nothing, which is exactly what a *ramping response* looks like. `0751`'s §4.4
argues the same point at length for a duty byte under load; it applies here
unchanged. A byte that held still reads as `net +0 … (0 changes)` rather than
going missing, so a byte that was watched and stayed put is not read as a byte
nobody watched.

### 4.5 What a second grader would check

Recorded here so the follow-up is a description rather than a re-derivation, and
so the choice not to build one is visible rather than an omission. This issue's
arms do not need one, for three reasons specific to this procedure:

1. **The arms do not produce the same kind of artifact.** Arm 3 is a dump pair,
   not a mark window (§3.4), so the
   `grade_0751_isolation.py` apparatus — block integrity, "every block ends on
   its restore", the cross-console mark census — is built for a shape that does
   not apply here.
2. **What is left to grade is three decidable facts over three small files**:
   the control arm quiet at `0x07A6`, arm 2's window, arm 3's dump diff.
   [`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md) §4
   states its rule in prose and §3 says the by-eye check "is the fastest one to
   do at the machine" — that is this tree's own precedent for a procedure
   before its grader grew, and the grader arrived later as separate issues (#146,
   #499, #531).
3. **A second grader is not one file.** It is `ec/tools/grade_07a6_bit0.py`, its
   `test_` suite, three or four `ec/tools/testdata/` fixtures, a row in
   `ec/tools/testdata/README.md` and a row in `tools/README.md`. That is three
   shared-table surfaces on a tree where several agent branches are already
   open, against a deliverable that is one document.

What it would check, concretely: that every arm boundary in every capture is one
of §6's five label forms; that each `MARK` is present in **both** CSVs of an arm
rather than one; that the control window's total movement at `0x07A6` is zero;
that the dump pair's `0x07A6` differs by exactly bit 0 and nothing else; and that
the CSV's marks and the dump pair's bracketing agree about which arm is which.

### 4.6 A run where nothing moves

That is a real result and should be recorded as one. It would mean the one
committed bit-0 clear does not reproduce on this machine under these
conditions, which is a fact about the register's behaviour and not about this
procedure. The capture goes into `evidence/ec-watch/` either way.

## 5. What this cannot settle

- **One machine, one firmware** (`GMxMGxx_11.800`). Nothing here generalises to
  sibling boards; see [`../related-projects.md`](../related-projects.md).
- **A window is a window.** A byte quiet for 300 s may move at the next
  suspend, AC transition or EC reset. §4.6 is about a bounded window and not
  beyond it.
- **`0x07A7`-`0x07AA` cannot serve as a probe of `0x07A6`** whatever this run
  shows, because `../../ec/annotations/registers.yaml:2152-2157` and `:1842-1844`
  record no read site for the block. Watching all four together says something
  about the *copy function*, and nothing about `0x07A6`.
- **The `0x0782` gate cannot be shown to be why anything fired.** Bit 1 read
  `0x9D` live on 2026-09-23
  (`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt:27`), which is bit 1
  **clear** — so the gate at `AB9E.asm:7-9` is *open* on this machine. A run in
  which the gate is open cannot distinguish "the gate was open" from "the gate
  is why it fired". Saying so in advance is the point of writing it here.
- **Whether the EC acts on the bit at all.** §1.1's chain shows the EC writes
  bit 0. Nothing in this procedure observes what the EC does with it, and
  §4.3's outcomes are all about *when it moves*, never about what it means.
- **`0x06E2`'s behaviour, if arm 2's window is empty.** No read site is
  recorded for it and nothing in `evidence/` has ever held it; a quiet window
  says the byte did not change, not that nothing reads it.

## 6. Where the output goes

Name the files the way the existing captures are named, so a reader can pair
them:

```
evidence/ec-watch/<date>-oem4-07a6-bit0-0700-07ff.csv
evidence/ec-watch/<date>-oem4-07a6-bit0-06e0-06ff.csv
evidence/ec-watch/<date>-oem4-07a6-bit0-load-defaults-before-0700.txt
evidence/ec-watch/<date>-oem4-07a6-bit0-load-defaults-after-0700.txt
evidence/ec-watch/<date>-oem4-07a6-bit0-snapshot.txt
```

`<date>` is the run's `YYYY-MM-DD`, flat in `evidence/ec-watch/`, dated in the
filename — the two properties `../../ec/tools/check_capture_names.py`'s docstring
names as the reasons that root is a flat, dated directory, and the shape
`check_capture_dates.py` will hold a capture to.

The two CSVs are one set for the whole run (`ec_watch.py` appends to an existing
`--csv`, and the marks say which arm each row follows). The dumps are per-arm,
because a dump is a whole-range read with no marks inside it and the filename is
the only thing saying what it brackets.

**A capture's header names five columns, not four.** `ec_watch.py:145-154`
writes `ts,addr,old,new,provenance` on a fresh file, a change row carries four,
and only a `MARK` row uses the fifth. So `ts,addr,old,new` is the *change-row*
shape and is right as far as it goes, but a new capture will not have a four-name
header. The 2026-09-23 file's four-name header predates the provenance column;
every reader in the tree drops the header row on `row[0] == "ts"`, so neither
shape costs anything.

### 6.1 The label forms

Fixed, because `--label-vocab` cannot check them (§3.1) and §6's table is the
only thing standing between a mistyped mark and an unplaceable window:

| when | label | typed into |
|---|---|---|
| arm 1 opens | `arm 1 control start` | both consoles |
| arm 1 closes | `arm 1 control end` | both consoles |
| arm 2 opens | `arm 2 cycle start` | both consoles |
| arm 2 closes | `arm 2 cycle end` | both consoles |
| arm 3, on return | `arm 3 returned from setup` | the post-boot watcher |

**Mark the same label in both consoles within a few seconds of each other.** A
mark one console missed is not an error `ec_watch.py` can see: that console's
rows are filed under whichever window their timestamps fall in, and nothing in
the capture ties them back to the arm whose mark went missing. The cross-console
comparison is the only thing that catches it, and §4.5's grader is where it
would be automated.

A blank line records nothing — the mark prompt says so and asks again
([`ec_watch-marks.md`](../../windows/tools/ec_watch-marks.md)) — so there is no
such thing as an unnamed mark in a capture.

**The snapshot is the human's, and nothing in §3 writes it.** §2's first bullet
asks the operator to write it by hand; §3's commands produce the other four
files. It is in the set because it is the only record of the starting AC state,
power mode and profile, and because `ecrw.py dump` does not carry any of that.
Add the finished files to `evidence/README.md`, the index every findings claim
cites through.

## 7. What a result has to say

`OEM_4` stays `confirmed-working-partially`
(`../../ec/annotations/registers.yaml:335`) whatever this run shows, and
`BIOS_OEM_2` stays `present-untested` (`:2108`). That is not a formality: bits
4-5 are the only bits with a decoded writer, and a run about bit 0 is not a run
about the profile control. `0x06E2` gets **no** `registers.yaml` entry from this
file under any outcome — a static instruction sequence and a planned procedure
are not a status.

What the run *can* settle, in the words a fold-in should use:

- **bit 0 clears on a BIOS load-defaults, reproducibly, and nothing else in the
  byte moves** → that is a **behavioural** attribution of the event, cited to the
  capture, with its scope written out: *a BIOS load-defaults clears bit 0 of
  `0x07A6` on this machine*. It still does not name the clearer, does not
  decode what the bit means to the EC, and does not promote the static claim in
  §1.1 beyond what it says. Record it in `docs/findings/` as its own finding —
  it is a new observation, not an edit to a `status:`.
- **bit 0 clears on a power-mode cycle** → a second, unexpected event, and the
  one worth the most attention, because §1.5 established that the one committed
  power-mode-cycle capture did *not* do this.
- **nothing moves anywhere, control quiet** → the 2026-09-19 `0x29` → `0x28` is
  **a one-off on this machine**, and the capture goes into `evidence/ec-watch/`
  saying so. Not a failed test, and not a reason to pick the
  confident-sounding phrasing.
- **mixed or ambiguous** → it stays where it is and the capture is filed with
  what was seen. That is the honest outcome whenever the control arm moved, and
  §4.2 makes it a void rather than a result.
