# `0x07C4` bit 3: is it the `DBEN` the ASL gates on, and does it follow `0x0743` bit 1

**Status: not run (issue #284).** This procedure was written by the pipeline
for a human at the physical GM7MG7P. No laptop and no Windows machine is
reachable from the runner that wrote it, so nothing below has been observed: no
register has been written, no register has been read back, and no result is
recorded anywhere in this repository. The instrument
(`../../windows/tools/ctgp_dben_probe.py`) and its offline checks are
committed; the reading is not. §7 says what a result has to say, and
`GPU_DYNAMIC_BOOST_STATUS` in `../../ec/annotations/registers.yaml` stays
`present-untested` until a human runs this and commits the capture — a
`status:` move is for a *behavioural observation*, and a prepared script is
not one.

**The two existing captures are not runs of this, and neither settles the
question.** `../../evidence/ec-watch/2026-09-23-ctgp-live.txt` is issue #8's
live write of `0x0743` measured against `nvidia-smi`; it drove **bit 2**
(cTGP enable), not bit 1, and it watched the dGPU's *enforced power limit*,
not `0x07C4`. The 2026-09-23 passive capture — the two `0x07C4` writes at an
AC plug-in quoted in `../../docs/findings.md` §7c and §4o — wrote nothing at
all and cannot attribute what it saw either. A clean readback from this
procedure settles nothing on its own; `../../CLAUDE.md`: a register write being
accepted (readback matches) is not evidence the EC acts on it.

**This file is the reference; the tool is the half that moves.**
`ctgp_dben_probe.py` defaults to §3's two arms and cadence, and the two are
held to each other by
`../../windows/tools/test_ctgp_dben_probe.py`, which fails if either drifts.
Neither is graded by a script, and the tool emits no status and no verdict.

## 1. The question

`0x07C4` is `GPU_DYNAMIC_BOOST_STATUS` in
`../../ec/annotations/registers.yaml`, and the DSDT ECMG field list at
`../../evidence/acpi/dsdt.dsl:52238-52242` names bit 3 `DBEN` and bit 5
`DBST`. The ASL's only use of the byte is to *test* `DBEN` — at
`dsdt.dsl:50702`, in `T1WR`'s `Arg0 == 0x73` branch, and at `dsdt.dsl:52796`,
in `_Q84` — and it never writes it. So a Linux driver exposing Dynamic Boost
has to know which bit the ASL is reading, and the committed rows say what
sets it:

| bit | role | what the committed rows make it |
|---|---|---|
| `0x0743` bit 0 | gate | the guard on `0x83FF`'s `0x07C4`/`0x07D4`/`0x07D5` block. Not the value the block acts on — reading it as one is the mistake §9 used to ask for. |
| `0x0743` bit 1 | value | what `0x96AD=apply_oem_overrides_then_fill_08xx` hands `0x94C0=set_07c4_bit4_from_r7` in R7, which ORs `0x10` into `0x07C4` or ANDs it with `0xEF` — so bit 1 becomes `0x07C4` **bit 4**. |
| `0x07C4` bit 3 | watched | what `0x83FF=sync_0788_and_07d4_from_09e9` "sets or clears … to follow bit 4", in the same block that copies `0x09EA`/`0x09EB` into `0x07D4`/`0x07D5` and under the same bit-0 guard. |

Every cell is a transcription of `../../ec/annotations/ghidra-functions.csv`
rows `0x96AD`, `0x94C0` and `0x83FF`, quoted above the tool's own docstring and
pinned to that file by the suite. **The gate and the value are different bits
of the same byte**, which is the whole reason §9's original instruction — flip
bit 0, watch bit 3 — could not have worked: it opens a gate onto a bit 4 that
never moved, and reports "nothing moved" while proving nothing.

The chain is **bit 1 → bit 4 → bit 3**, with **bit 0 only the gate** on the
routine that does the last hop. The question this procedure asks is the
behavioural half of that: *on this machine, with bit 0 held set, does setting
`0x0743` bit 1 put bit 3 of `0x07C4` up, and does clearing it put bit 3 back
down.* That the bit-3 write is `DBEN` is an inference from the bytes that
`../../ec/annotations/ec-07c4-07d5-sites.md` §3 records as one; this run is
the observation that would move it.

## 2. Before you start

- Windows, Control Center 3.1.39.0 installed, and `python windows\tools\ecrw.py
  read 0x0743` printing a value — the same proof
  [the `0x0751` procedure](manual-fan-ctrl-0751-isolation.md) §2 asks for, and
  it says the vendor driver is present and you are elevated.
- **On AC for the whole run.** The vendor rewrites the `0x0743`-`0x0746` block
  on every AC ↔ battery transition (`../../windows/vendor-ec-map.md`, "Power
  modes", issue #92), so a transition mid-run is a state change the test did
  not ask for, and on battery `0x0743` is `0x00` — the byte this procedure
  writes both arms of. The run itself will say which it found, but running on
  battery turns the test into "force `DB function control` on" and should be a
  deliberate second run, not the first.
- The Control Center service **running**, and left alone. It is the established
  writer of this block (issue #8), so a run with it stopped is a different
  question, not a cleaner one.
- Nothing in the vendor UI that touches GPU power or power mode during a run:
  both rewrite `0x0743`.
- Write down the starting values of `0x0743`, `0x07C4`, `0x07D4` and `0x07D5`
  from `ecrw.py read`, in the snapshot style of
  `../../evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt`. The probe
  prints them too; a snapshot is what §4's reading is checked against if the
  run has to be repeated.

### Safety

**This test writes one byte**, `0x0743`, and nothing else — `ctgp_dben_probe.py`
has no other write in it, which the offline suite asserts as a three-element
list. The original is read first and restored in a `finally`, so a Ctrl-C, a
`DeviceIoControl` failure or a crash between the arms all put it back; the
restore's own readback is printed. That is belt-and-suspenders: the vendor
rewrites the byte on the next power-mode event regardless, and §4m's `0x0522`
work measured the EC taking a host write back in under 100 µs.

The two arms are named for the bit they drive, and the tool prints the byte
each one resolves to before it writes anything:

- **arm A** is `0x0743 | 0x03` — bit 0 forced set, bit 1 set. On AC that is
  `0x03`, the value the vendor writes for the whole block, so arm A is close to
  a state this machine has already been in.
- **arm B** is `(0x0743 | 0x01) & ~0x02` — bit 0 still set, bit 1 cleared. This
  is the state on AC with Dynamic Boost off.
- Both preserve bits 2-7 of whatever the byte held, so **cTGP enable (bit 2)
  is never disturbed** and the run does not turn cTGP on or off as a side
  effect. Issue #8 measured what that bit does to the enforced power limit, and
  this run must not be the one that changes it.

Arm A on **battery** is different: `0x0743` is `0x00` there, so arm A forces
`DB function control` on for the length of the run, and the tool's banner says
so. That is why the first run is on AC.

**Four ECRR reads per sweep** — `0x0743`, `0x07C4`, `0x07D4`, `0x07D5` — so
4 `DeviceIoControl`s every interval with nothing between calls.
`ecrw.Ec.read` is one ECRR per byte, and `../related-projects.md` records that
mechanism stalling the fans on a sibling board, where the OEM software and
`uniwill-laptop` sleep 6 ms after every EC access. Four is far below
`../../windows/tools/gpu_block_watch.py`'s 24 and
`../../windows/tools/manual_fan_ctrl_probe.py`'s 206, and **"far below" is not
a safety argument.** No interval in this repository is validated (issue #94 is
the open work, and nothing here measures one). The `--interval 0.5` below is
§3's starting point and nothing more. If the fans audibly change, stop, raise
the interval, and redo the block.

## 3. The run

Two arms, one file, one clock. Without `--i-mean-it` the tool prints the byte
script and refuses without opening the EC, so the run can be read on a machine
that is not the subject:

```console
rem  --- 0. plan it: the byte 0x0743, as ecrw.py read it above ---
python windows\tools\ctgp_dben_probe.py --orig 0x03

rem  --- 1. read-only snapshot, before anything is written ---
python windows\tools\ecrw.py read 0x0743
python windows\tools\ecrw.py read 0x07C4
python windows\tools\ecrw.py read 0x07D4
python windows\tools\ecrw.py read 0x07D5

rem  --- 2. the run. --interval 0.5 is a starting point, not a
rem  ---    validated-safe one; see the pacing note above before leaving it
rem  ---    there. --seconds 30 is the per-arm hold.
python windows\tools\ctgp_dben_probe.py --seconds 30 --interval 0.5 ^
       --csv <date>-ctgp-dben-07c4-bit3.csv --i-mean-it
```

The tool writes arm A, samples for 30 s, writes arm B, samples for 30 s, and
restores the original byte in its `finally` — then prints the restore's
readback. Ctrl-C at any point does the same thing; there is nothing else to
stop cleanly. The run takes about a minute; the total runtime is not the
point, the two windows are.

**Every sample is a row**, and every row carries the arm it was taken in, the
byte that arm wrote, and the byte `0x0743` actually read back. The
`dben_b3` column is bit 3 of `dben_byte` on its own, so the CSV can be sorted
without re-deriving the bit. The two other watched bytes, `cpua` and `dbap`,
are there because `0x83FF` writes them in the same block: **if they move, the
routine ran.** A capture with a still `0x07C4` and a still `0x07D4`/`0x07D5`
is a capture where the routine may not have run at all, and that is a
different reading from one where it ran and left bit 3 alone.

The probe prints a sample line per sweep and the whole file is the record.
Take the run **twice**: once on AC as written, and once in the state where
`0x0743` is `0x00` (on battery, or after the vendor has cleared it), because
the gate and the value behave differently when the gate starts closed. The
second run's banner will say `bit 0 was clear`; write it to its own CSV, do
not append it to the first.

## 4. What to read off

1. **The `dben_b3` trajectory against the `mark` column.** That is the
   question, and it is a per-arm question: does bit 3 read 1 across arm A and
   0 across arm B, and when did it change? Read the transition against the arm
   boundary in the `mark` column rather than against the console scrollback.
2. **`0x07D4`/`0x07D5` across the same two windows.** This is the control the
   run gives itself. `0x83FF` copies `0x09EA`/`0x09EB` in the same block, so
   a capture where those two bytes move tells you the block was entered. A
   capture where nothing moved at all is weaker than "the block did not run":
   under the guard in §4.5 a quiet capture is also what a block that was
   entered and skipped looks like when bit 3 already followed bit 4. Either
   way it is "not moved by this method", not "bit 3 is dead".
3. **`ctrl_read` against `ctrl_written`.** For what it is worth: a `ctrl_read`
   that stays at the arm's byte says the host write held, which is not a
   result about `0x07C4` and is not a result about the EC acting on anything.
   A `ctrl_read` that came back at the original says the EC took the byte back,
   which would make the whole window moot and is worth recording either way.
4. **The restore line.** The last thing the tool prints is
   `restored 0x0743 -> 0xNN, readback = 0xNN`. If those differ, the vendor had
   rewritten the block under the run; note it and read the arms against that.
5. **The `cpua`/`dbap` values against the snapshot.** `0x83FF`'s block is
   entered when bit 0 of `0x0743` is set **and** any one of three things
   holds: bit 3 of `0x07C4` differs from bit 4, or `CPUA` differs from
   `0x09EA`, or `DBAP` differs from `0x09EB`. That is a **disjunction**, not
   a conjunction — `../../ec/decompiled/bank0/83FF.c:40-42`, and the three
   branch targets in `../../ec/decompiled/bank0/83FF.asm` at `0x8459`,
   `0x8465` and `0x8471`. The block is skipped only when all three already
   agree. So a window where `cpua`/`dbap` already held what `0x09EA`/`0x09EB`
   hold is **not** a window where the bit-3 write was never reached: arm A
   drives bit 4 while bit 3 is low, so bits 3 and 4 differ, the block is
   entered, and the copies then write back values identical to what is
   already there. `cpua`/`dbap` staying still while bit 3 moves is that
   case, and it is a positive. That is why §3 asks for the starting values —
   they are what tells that apart from a block that never ran.

## 5. What this cannot settle

- **The 2026-09-23 attribution.** `ec-07c4-07d5-sites.md` §8's open question is
  *who wrote `0x07C4`* on that date. This run writes `0x0743` from the host and
  watches; it produces no attribution for the vendor service, the EC firmware
  or anything else, and §8 stands. The two questions are independent and one
  more answer to the second does not touch the first.
- **What `0x09EA` and `0x09EB` are.** They are what `0x07D4`/`0x07D5` are
  copied from, neither has a `registers.yaml` entry, and a run that watches
  them does not say what they hold. Following their writers is separate work.
- **Whether `0x83FF` runs, or when.** `0x83FF`'s only caller is `0x8551`,
  inside the unresolved three-byte `lcall`/`ljmp` run at `0x851B` that
  `../../ec/annotations/bank-call-audit.md` has not resolved. **So no interval
  in §3 is validated**: if bit 3 does not move, a better guess for why is that
  the routine was not called in that window, not that the identification is
  wrong. This is the single largest caveat on a negative.
- **A byte that is quiet for the whole window is "not moved by this method,
  within this window."** Never "the routine does not run" and never "the bit
  is dead". `../../CLAUDE.md`'s retraction of the `0x07D4` claim (issue #265)
  and of the "this register doesn't exist" reading (§4c) are both about exactly
  this kind of overreach.
- **One machine, one firmware version** (`GMxMGxx_11.800`). Nothing here
  generalises to sibling boards; see `../related-projects.md`.
- **What the EC *does* with `0x07C4`.** The ASL reads it and publishes `DBAC`,
  `ATPP` and `AMAT` off `CPUA`/`DBAP` when `DBEN` is set, and that is
  established from the ASL. A bit-3 transition here is an observation about a
  bit the ASL gates on, not a decode of what the firmware computes.
- **A clean readback settles nothing.** `../../CLAUDE.md`: a register write
  being accepted (readback matches) is not evidence the EC acts on it. If both
  arms read back exactly what they wrote and `0x07C4` never moved, that is the
  §7 "nothing moved" outcome and it is a result. It is not a confirmation that
  the chain is inert.

## 6. Where the output goes

One CSV per run, named the way the existing captures are:

```
evidence/ec-watch/<date>-ctgp-dben-07c4-bit3-ac.csv
evidence/ec-watch/<date>-ctgp-dben-07c4-bit3-gate-closed.csv
```

`<date>` is that run's YYYY-MM-DD. The two runs are two files and have to be:
they are the same question asked with the gate starting open and starting
closed, and a single capture cannot hold both start states. A third run on a
different battery state gets a third file — do not append into an existing one,
and do not merge two files and read the union.

Add each capture to `evidence/README.md`, which is the index every findings
claim cites through.

`ctgp_dben_probe.py` reads nothing afterwards: the console lines it printed
*are* the mechanical read, and the CSV is the raw record. The rows are
`ts,mark,t_s,ctrl_written,ctrl_read,dben_byte,dben_b3,cpua,dbap` — every
sample of the run, not a change log, because the question is what the byte did
across a settle interval and a bit that goes up and comes back between two
sweeps reads as quiet in a `ts,addr,old,new` schema. `mark` names the arm on
every row, in the role `charge_target_test.py`'s `--phase` plays. Issue #168
owns grading a capture; there is no grader here and this tool emits no verdict.

The follow-on edits a run is for, named here so a later pass does not have to
re-derive them, and to be made **only after a capture exists**:

- `GPU_DYNAMIC_BOOST_STATUS` in `../../ec/annotations/registers.yaml` — the
  observed bit map in the note, and a `status:` move **only** on §7's terms.
  A `present-untested` that stays is a correct outcome.
- `ec/annotations/ec-07c4-07d5-sites.md` §3's "**The bit-3 logic is a real
  find, and the identification is an inference**" paragraph — if the run
  settles the identification, the inference stops being one and that sentence
  has to change. §9's bullet likewise. Both leave the wrong version visible
  with a correction beside it, per the `../../docs/findings.md` §4 convention.
- If the bit does **not** follow, the more likely finding is the one §5 names
  first: `0x83FF` was not called in that window, and `bank-call-audit.md`'s
  `0x851B` is the way in. That is a new issue, not a revision of this row.

## 7. What a result has to say

One bullet per outcome, each a scoped positive followed by an explicit
negation. A bullet that stops at the positive is how `present-untested` rows
turn into confident-sounding prose.

- **Bit 3 follows.** Bit 3 up in arm A and down in arm B, over the windows the
  capture holds, is a statement about this machine and this firmware:
  *setting `0x0743` bit 1 with bit 0 set moves `0x07C4` bit 3, and clearing it
  moves it back*. `0x07D4`/`0x07D5` moving in the same windows corroborates
  it but is **not** required: arm A drives bit 4 while bit 3 is low, so bits
  3 and 4 differ, the block is entered, and the copies can write back values
  identical to what is already there (§4.5). `cpua`/`dbap` still and bit 3
  moving is the same positive — say which of the two the capture shows, with
  the timestamps. It is **not** a statement that the chain is the only path to
  bit 3, and it is **not** by itself a statement that bit 3 is `DBEN` — that
  is the identification this run was for, and saying the identification is
  confirmed is the strongest form the evidence supports only if the bit-3
  transition lines up with the bit-1 write in the same window.
- **`0x07D4`/`0x07D5` moved, bit 3 did not.** The block was entered and left
  the bit where it was, which is a real result about *this window*. Because
  §4.5's guard is a disjunction, the copies can be what admits the block on
  their own — so the case to check is whether bit 3 already equalled bit 4:
  already following, with the bit-3 write reached and re-writing the value it
  already held. It is **not** a statement that bit 3 is unwritten, and it is
  **not** a statement that the identification is wrong.
- **Nothing moved, both arms.** A result, and a real one: bit 3 was not moved
  by this method within these windows, and `0x83FF` may simply not have run
  (§5). It leaves the `DBEN` identification **exactly as open as it was**, and
  the capture goes into `evidence/` with what was seen. Per
  `../../CLAUDE.md`, an honest negative is a result and closing the question
  because nothing moved is not.
- **Both arms read back exactly what they wrote and `0x07C4` was still.**
  This is the "nothing moved" case with the readback noted, and it is worth
  separating out loud precisely because it is the one that reads like a
  success. It settles **nothing** about whether the EC acts on the byte —
  `../../CLAUDE.md`, "a register write being accepted (readback matches) is
  not evidence the EC acts on it" — and the correct write-up is a negative
  with the readback recorded, not a confirmation.
- **Bit 3 moved in one arm only.** Report it as a one-armed observation and
  quote the sample, do not average it into a verdict. A bit that comes up and
  does not come back down is as consistent with an EC that latches a value as
  with one that mirrors it, and a second run decides between them, not a
  first-run reading.

---

**Running this is a human step on the physical GM7MG7P. This repository
contains no result from it.**
