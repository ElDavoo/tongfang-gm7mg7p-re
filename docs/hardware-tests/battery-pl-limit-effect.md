# Does a power limit written on battery reach the clock

**Status: not run.** This procedure was written by the pipeline for a human at
the physical GM7MG7P. `CLAUDE.md` is explicit that the GitHub-hosted runners
cannot reach the hardware, and nothing below has been observed: no register has
been written, no register has been read back, and no result is recorded
anywhere in this repository. `0x0783`-`0x0785` hold the statuses they hold
today — a `status:` move needs a *behavioural observation*, and a prepared
procedure is not one.

The static finding this serves is
[`../findings/battery-pl-default-and-zero-semantics.md`](../findings/battery-pl-default-and-zero-semantics.md).
Its answers are that there is no separate battery PL block (`0x07A7`-`0x07AA`
is it, under two names), that the vendor's battery branch writes a hard-coded
literal `0` and consults no default block, and that **every direct read of
`0x0783`-`0x0785` found by that method is a presence test which skips the
store when the value is zero**. So zero means "no override", and the asymmetry
the issue opens — a driver writing zero versus the EC's own clear writing zero
— is not borne out.

What is left is the half that only hardware answers, and it is the half that
licenses the behaviour change: **does a non-zero limit written on battery
change anything?**

## 1. The question

One question, and it is a yes/no that a driver can act on:

> On battery, with the vendor's zero in place, does a **non-zero** value
> written to `0x0783`/`0x0784`/`0x0785` change the sustained clock or package
> power under a fixed battery load?

The static reading says the path is live, with one qualifier you have to carry
into how you read a result. Of the twelve read sites, **nine are gated on
`AP_OEM` (`0x0741`) bit 0** — each of the three blocks in
`apply_oem_overrides_then_fill_08xx` opens with a `0x0741` read and a
`jnb 0xe0`, at `0x96AD`, `0x97D1` and `0x98BD` in
`ec/decompiled/bank0/96AD.asm` — and **three are not**: the sites in
`compute_level_blocks_086b_086c_086e` sit in a routine that never reads
`0x0741`, so a PL override can reach `0x0866` whether or not a host agent has
announced itself. Nothing in the guards of any of the twelve compares an
AC-present or battery-present byte. So a non-zero write *should* propagate.
"Should" is the whole gap, and this run closes it — but which of the two groups
ran is `0x0741` bit 0 in the capture, so record it (§3a, §7).

**Two verdicts, and both are results:**

- **Yes** — the sustained clock or package power moves under a fixed load,
  consistently, in the write arm and not in the control. That licenses writing
  the PLs off AC, which is what
  [`../../linux/patches/gm7mg7p-power-profile/`](../../linux/patches/gm7mg7p-power-profile)
  currently declines to do.
- **No** — nothing moves, with the write accepted and read back, under both
  arms. That is a real answer about this machine and it does not mean the EC
  "ignores battery": it means the byte does not reach the clock by this route,
  and the driver needs a different one.

**What no run of this can settle.** The EC copies the PL into `0x08C0`-`0x08C6`
and `0x0866`/`0x0867`, and **page `0x0800` is not host-readable** — it reads 0
of 256 bytes non-`0xFF` in
`evidence/ec-watch/2026-09-24-host-window-page-census.txt`, and
`ec_timer_capture.py` refuses out-of-window addresses rather than let that
misreading through. So **the copy landing cannot be watched at all**, and
neither can anything downstream of it. This procedure therefore grades on
behaviour and says so, rather than staging a byte watch that would prove only
that the host cannot see it.

## 2. Before you start

- **Off AC for the entire block.** Not "unplugged for the interesting part" —
  off AC from before the first capture until after the last restore. Every
  address this touches is rewritten by the vendor on any AC event, and §2's
  ordering constraint is the whole reason.
- **Root, and `CONFIG_DEVMEM=y`.** `ec/tools/ecmem.py` maps physical
  `0xFE410000` through `/dev/mem`, the same window the DSDT's `ECRR` uses.
  Check the build first: `grep DEVMEM /boot/config-$(uname -r)`.
- **Battery charge above the run's duration.** This is a battery-load run and
  a flat battery is a confound, not a stress test. Record the charge at the
  start of each arm; a run that crosses a charge threshold is not comparable to
  one that does not.
- **A fixed load.** The verdict is about a limit under load, and an idle
  machine will not show one either way. Have a repeatable CPU load running for
  the whole of every arm — the same one, and note what it is. A fixed-load
  comparison has not been run on this machine before (§4 of
  [`../findings/power-profile-gm7mg7p.md`](../findings/power-profile-gm7mg7p.md)
  names it as still open), so this procedure supplies one.
- **How to observe clock and package power.** The EC bytes in §3's watch set
  do not include them; the EC has no host-visible PL register and the
  destination page is dark. Use the host's own readings — `turbostat`, or
  `/sys/class/thermal` plus `perf stat`, or `nvidia-smi -q -d PERFORMANCE` for
  the package figures on a machine with the discrete GPU — and record which.
  **What you use here is part of the result**: a clock reading taken from a
  tool with its own averaging window cannot see a step shorter than that
  window, and §7 asks for the window.
- **Which service class is loaded.** `v3.1.39.0` ships two generations of the
  fan manager. Both write a hard-coded zero to the PLs on battery, so this does
  not change what the vendor's battery state is — but they differ in what they
  *seed*, and that decides whether the vendor will re-assert the PLs and the
  profile during your arm. Nothing static settles which runs on this chassis.
  Check the loaded `GCUService` build and say which.

### The ordering constraint, which is not optional

The vendor rewrites the PL bundle on **every** AC ↔ battery change, from
`SetUserProfile`'s `g_ACLineStatus` branch, and again on resume and on service
start (`windows/vendor-ec-map.md`, "Power modes"). So:

- **Unplug first, then start capturing.** A capture that opens across the DC
  transition contains the transition, and the transition rewrites the very
  bytes under test. Wait for the machine to settle on battery, confirm it is
  on battery, and only then start.
- **The AC plug-in would contaminate every arm.** The capture in
  `evidence/ec-watch/` records the vendor re-applying the whole bundle ten
  seconds after the transition — `0x0743` at 17:57:41 from the UI, the
  service's own re-apply at 17:57:51. So if AC comes back at any point inside
  a window, everything after that mark is the vendor's, not yours. `--auto-mark`
  (§3) stamps the transition by itself, so a contaminated window is visible in
  the capture rather than only in your recollection.
- **Stay off AC until the restore is verified.** Restore in §5, then verify,
  then and only then plug back in.
- **Plan for a suspend.** A resume is one of the events that rewrites the
  bundle. Do not suspend mid-arm; if you must, the arm is void, say so and
  re-run it.

### Safety

**The ceiling is the vendor's own AC values, not the current battery reading.**
This arm has to write a *non-zero* PL — writing zero would test the state that
is already there — and on battery the current reading is zero, so "at or below
what it reads now" cannot be the rule for this procedure. What bounds the write
is what this machine is known to run at on AC: the service writes
75/75/165 Turbo, 60/60/165 Gaming and 35/35/165 Office
(`windows/vendor-ec-map.md`, "Power modes"). Each is one group of
`MODE_PL_DEFAULTS`: `0x07A7`-`0x07AA` is the **Turbo** group (`4B 4B A5 01` =
75/75/165), `0x0730`-`0x0733` is Gaming (`3C 3C A5 01`) and `0x0734`-`0x0737`
is Office (`23 23 A5 01`). Nothing in this repository establishes what the EC
clamps a PL request to, so the reference for what is sane is a value the vendor
itself writes on this machine — not a number chosen here.

**Start low, and start at or below 75/75/165.** The Gaming pair (60/60/165) is
the better first write of this arm precisely because it is below the highest
value the service ever writes; Office (35/35/165) is safer still and is enough
to answer §1. **That pair is the Gaming group at `0x0730`-`0x0732`, not
`0x07A7`-`0x07AA`** — the last is the Turbo group, and it holds the 75/75/165
*ceiling* rather than the low first write. Step 0 reads `0x0730`-`0x0732`, so
use what it reads rather than the numbers here, and if it reads something other
than `3C 3C A5`, write what it reads. **Do not invent a value above 75/75/165
for any reason.** A PL above what the chassis is validated for is a request for
power the cooling path is not sized for, and on battery there is no AC to fall
back on.

**Know what you are starting from.** The DC snapshot in
`evidence/ec-watch/2026-09-23-power-mode-snapshot-dc.txt` records
`0x0783`/`0x0784`/`0x0785` = `0x00` on battery with `0x07A7`-`0x07AA` =
`4B 4B A5 01`, but it is one capture on one day in Turbo. Step 0's read is what
this run actually starts from and what §5 restores to.

**Stay inside `0x0000`-`0x07FF`.** Every address in §3's watch set is inside
the host window this machine maps. `ec_timer_capture.py` refuses an address
outside it, and the refusal is the census, not a guess — a byte that read `0xFF`
for the whole run would be a byte the host cannot see, not a byte the EC left
alone.

**Do not read `0x0460`-`0x046F`.** The fan-tachometer page stalled the fans on
a sibling board, and both the OEM software and `uniwill-laptop` sleep 6 ms after
every EC access because of it ([`../related-projects.md`](../related-projects.md),
issue #94). Nothing in §3's watch set is on that page, and nothing in this
procedure needs it to be.

## 3. The run

Every address in the watch set, and what a change in it means:

| address | what it is | what a change means |
|---|---|---|
| `0x0783` `0x0784` `0x0785` | PL1 / PL2 / PL4, watts | the registers the arm writes |
| `0x07A7` `0x07A8` `0x07A9` `0x07AA` | the `MODE_PL_DEFAULTS` block the write-up names | the bytes `MODE_PL_DEFAULTS` is seeded from; a change means the EC's own copy moved |
| `0x075B` `0x075C` | `MAIN_FAN_L_DUTY` / R, percent | the fan's response to a changed limit — the visible consequence if the limit reached the cooling path |
| `0x043E` `0x044F` | `CPU_TEMP` / `GPU_TEMP` | the flat-load check (§4) and the confound guard |
| `0x0741` | `AP_OEM` bit 0 | not written here, but recorded for two reasons: it is what the EC's own PL clear is gated on, so a clear landing mid-arm is attributable, and it is the bit that decides how many of the twelve PL read sites run (§1) |

`0x0741` is in the set because the EC's clear at bank0 `0xA833` is a competing
writer of exactly the bytes under test, gated on that bit being clear. You are
not clearing it. If the PLs go to zero on their own during an arm and
`0x0741` bit 0 reads clear, that is the EC's clear and not your write — see
§7.

It is in the set for a second reason, which §1's reading depends on: the same
bit 0 gates nine of the twelve PL read sites. Recording it is what lets you say
afterwards which of the two groups an arm actually exercised, and §3a and §7
both turn on that.

### Step 0 — snapshot, read-only, before anything

```console
$ sudo python3 ec/tools/ecmem.py read 0x0730 0x0731 0x0732 0x0741 0x075B 0x075C 0x0783 0x0784 0x0785 0x07A7 0x07A8 0x07A9 0x07AA
```

`0x0730`-`0x0732` is in there for §2's sake: it is the Gaming group the first
write of §3 is taken from, and §2 says to use what it reads rather than the
numbers this document prints.

**This is not optional.** It is the only record of what the bytes held before an
arm disturbed them, the restore in §5 puts back what is in it, and Arm A's
"nothing written" baseline is only comparable against it. Write it down
somewhere the run will not overwrite.

### Step 1 — get off AC, and wait

Unplug. Confirm the machine is on battery by your OS's own means, then let it
settle — the vendor's re-apply lands seconds after the transition, and a
capture opened across it measures the vendor. Take a second `ecmem.py read`
when it has settled and note whether the PLs moved from Step 0; if they did,
the re-apply is still running and the block has not started yet.

### Step 2 — Arm A, the control: write nothing at all

```console
$ sudo python3 ec/tools/ec_timer_capture.py \
      --addrs 0x0741,0x075b,0x075c,0x043e,0x044f,0x0783,0x0784,0x0785,0x07a7,0x07a8,0x07a9,0x07aa \
      --interval 0.05 --seconds 900 --auto-mark --csv <date>-battery-pl-control.csv \
      --note "control arm: off AC, vendor service running, nothing written, fixed load running"
```

Same block, same length, same load, no write. **This arm is what makes Arm B
mean anything**: without it, a flat clock in Arm B is indistinguishable from a
machine that was thermally limited, throttled by the charger, or simply not
being asked for much. Arm A's purpose is to establish what this machine does
on battery with nothing written, on this day, at this charge, at this
temperature — which is a moving target and is exactly why it has to be
measured alongside rather than assumed.

`--auto-mark` is there to catch the things you did not do on purpose: it polls
the Mains supplies' `online`, the ACPI lid, and the boot-time/monotonic gap
(a suspend), and stamps each change. On a correctly-run block it will be
quiet, and **quiet is the result** — it says nothing transitioned underneath
you. Any `auto:` mark in Arm B is contamination and §7 says what to do with it.

Ten to fifteen minutes is a starting point, not a derived one. Run longer if
nothing separated; the honest report for a flat arm is the length it ran and
that it was flat.

### Step 3 — Arm B, the write arm

Seed one PL at a time and hold each long enough to read. **Do the writes with
the vendor service stopped** (§3a), or it may overwrite them for you and you
will be measuring the service.

Start at or below 75/75/165 per §2's ceiling. The command below uses the
service's own Gaming values, `0x3C 0x3C 0xA5` = 60/60/165, because they are
below the highest value the vendor ever writes and still far enough from zero to
be plainly visible in the capture. Those are the **Gaming** group's bytes at
`0x0730`-`0x0732`; take them from what `0x0730`-`0x0732` reads in Step 0 if it
differs, and never from `0x07A7`-`0x07AA`, which holds the Turbo 75/75/165
ceiling rather than the first write.

Spell the values `0x3c`, not `3c`: `ecmem.py` parses them with `int(v, 0)`, and
bare hex raises before it touches the EC.

```console
$ sudo python3 ec/tools/ecmem.py write 0x0783=0x3c 0x0784=0x3c 0x0785=0xa5
$ sudo python3 ec/tools/ecmem.py read 0x0783 0x0784 0x0785      # the readback, recorded
$ sudo python3 ec/tools/ec_timer_capture.py \
      --addrs 0x0741,0x075b,0x075c,0x043e,0x044f,0x0783,0x0784,0x0785,0x07a7,0x07a8,0x07a9,0x07aa \
      --interval 0.05 --seconds 900 --auto-mark --csv <date>-battery-pl-write.csv \
      --note "write arm: off AC, PLs seeded 60/60/165 from the Gaming block at 0x0730, fixed load running"
```

The `ecmem.py read` after the write is the **readback, and on its own it is not
a result** — see §7. Record it because without it you cannot tell a write that
was refused from one that was accepted and ignored, and those are different
answers.

Hold, then mark the write's end and let it run. If the machine's behaviour
changed, note when you noticed it by hand and cross-check that against the
capture's clock; the capture has no idea what you observed, and your note is
the only link between the two.

### Step 4 — one more value, if the day allows

Repeat Step 3 with a second value above the first, still inside §2's ceiling —
Office (35/35/165) or the Turbo pair (`4B 4B A5 01` = 75/75/165) are the natural
choices, or an intermediate value if you want to look for a scaling
relationship. A single value that moves proves the route; a second that moves
*differently* proves it is a limit rather than a switch, which is what a driver
wants to know. One value is the minimum that answers §1; two is what makes the
answer usable.

### Marks

`--mark` reads labels on stdin and stamps them, which is how you place your own
actions — especially the writes — inside the capture:

```console
$ { echo "arm B: seeding 0x0783/84/85 = 3c/3c/a5"; \
    sleep 900; echo "arm B: write held 900 s"; } \
  | sudo python3 ec/tools/ec_timer_capture.py ... --mark
```

`--auto-mark` and `--mark` compose; use both. A mark is when **Linux** saw the
action, not when the EC did, which is the tool's own docstring and the reason
a capture can place your actions but never time the EC's turn.

### Step 3a — the service-stopped pass

Run §3 Steps 2-4 a second time with the vendor Control Center service stopped
(`sc stop`, confirmed by the vendor UI being gone). Same shape, its own
`<date>`.

Two reasons, and the first is the one that matters: with the service running,
anything you see could be the service reacting rather than the EC acting; with
it stopped, whatever moves is the EC. The second is that the service raises no
event for a write it did not make, so a clean service-stopped run is the only
one where a PL you wrote is still your PL fifteen minutes later.

If the day only allows two passes, make them the control and the write with
the service stopped, and leave the service-running pass open — say that in the
report rather than reporting the two you ran as the whole procedure.

**Record `0x0741` bit 0 for this pass, and read the result through it.**
Stopping the service removes one writer of that bit, not necessarily both:
`registers.yaml`'s `AP_OEM` note records the vendor service setting it
(`MyEcCtrl.Set_APExistToEC`, called true on init and on `ModernOn`, and read
live as `0x01` with the service running) *and* `uniwill-laptop` setting it in
`uniwill_ec_init()`. So whether bit 0 reads clear here depends on whether that
driver is loaded — which is exactly why it is recorded rather than assumed.
Bit 0 clear does not make the arm void; it changes what a null from it means.
Clear leaves only the **three ungated sites** live, so a null then says the
write did not reach the clock *by the level-block path*, and says nothing about
the nine sites that did not run. A non-null still settles §1, because both
groups reach `0x0866`. §7 says what each case means.

### Step 3b — what this single-tool form does not cover

- **It cannot see the copy.** `0x08C0`-`0x08C6` and `0x0866`/`0x0867` are on
  page `0x0800`, which the host window does not map. There is no `--addrs`
  spelling of "did the EC copy your PL", and adding `--outside-window` would
  read `0xFF` for the whole run — a fact about the window, not about the EC.
- **It cannot time the EC's turn.** The scheduler's period is a count of
  entries, not a time, and the tick period is unestablished; §1 of
  [`pl-clear-0741-gate.md`](pl-clear-0741-gate.md) carries that refusal in
  full. A quiet window is "not moved by this method, within this window".
- **It does not separate the battery's own ceiling.** A flat clock in both arms
  may be the battery limiting, not the EC. That is what Arm A establishes — if
  Arm A is flat too, you have learned the machine's battery ceiling and not the
  EC's behaviour, and the report has to say which.

## 4. What to read off

Read each of these off the capture and your host-side observations together.
The capture alone cannot answer any of them.

1. **The two verdicts.** Did the sustained clock or package power move in Arm B
   relative to Arm A, under the same fixed load, on the same charge, at a
   comparable temperature? Write the numbers, not a summary of them.
2. **The flat-load check on `0x043E`.** If the die temperature differs between
   the arms by more than a few degrees, the arms are not comparable and the
   verdict is void until it is re-run at matched temperature. A limit that only
   shows up cold and not hot is not a limit; say so if that is what you saw.
3. **Fan duty at `0x075B`/`0x075C`.** A moved fan duty is the cooling path
   responding, which is the difference between "the limit reached the machine"
   and "the clock did not move for some other reason". It is corroboration,
   not the verdict.
4. **The PL registers.** Whether the write held for the whole arm, or whether
   something took them back. If they went to zero on their own and `0x0741`
   bit 0 read clear, that is the EC's own clear from bank0 `0xA833` and not
   your write — a different finding, and one that belongs with
   [`pl-clear-0741-gate.md`](pl-clear-0741-gate.md)'s arms rather than being
   read as "the write did not take".
5. **`0x07A7`-`0x07AA`.** These should not move. If they did, the EC's own
   default block was rewritten during your arm, which is a finding of its own
   about what touches them.

## 5. Restore, and do it even if an arm failed

```console
$ sudo python3 ec/tools/ecmem.py write 0x0783=0x00 0x0784=0x00 0x0785=0x00   # Step 0's values
$ sudo python3 ec/tools/ecmem.py read 0x0783 0x0784 0x0785 0x07A7 0x07A8 0x07A9 0x07AA
```

The three `0x00` are what the committed DC snapshot records, not a value to
assume: substitute whatever Step 0 read, in the same `0x..` spelling Step 3
uses.

`ecmem.py write` reads back after each write and prints both, so the second
command is the verification that the restore took. **If an arm failed halfway,
restore anyway** — a machine left with its PLs at a value nobody chose is a
machine whose behaviour nobody can explain.

Then verify the charge has not dropped below whatever it was at Step 0, and
**plug AC back in only after the restore is verified**, because the plug-in
rewrites the bundle and would hide a failed restore behind a correct-looking
final state.

## 6. Where the output goes

One capture per pass, under `evidence/ec-watch/`, named for the pass so a later
run does not collide with these:

```
evidence/ec-watch/<date>-battery-pl-control.csv
evidence/ec-watch/<date>-battery-pl-write.csv
```

Add a bullet for each to `evidence/README.md`. `ec_timer_capture.py` writes
`ts,addr,old,new` rows plus `#` comment lines carrying the date, kernel, AC
state, interval, address list and whatever `--note` said; every consumer in
this repository skips the comments, so leave them.

The host-side clock and power readings are **not** produced by any command
here — you take them from whatever tool you chose in §2 — so they belong in the
report's prose with their tool and averaging window named, not in a file the
commands do not write.

**Grade it with the committed checkers before writing anything up.**
`check_capture_claims.py` and `check_capture_dates.py` both read that
directory, and a capture written without them is the finding
`capture-claim-denial` exists to catch.

## 7. What a result has to say

`CLAUDE.md`'s calibration rule, where the human reading this will hit it:
**"a register write being accepted (readback matches) is not evidence the EC
acts on it."** A readback match is the `ecmem.py read` after the write. It is
the weakest thing in this file and it is not a verdict.

Concretely:

- **Clock or package power moved, control flat** → the limit reached the
  machine on battery. This is the answer that licenses the profile change, and
  the write-up has to carry the *scope*: the byte does X on this machine, on
  this battery, at this charge — not "PLs work on battery" as a general claim.
- **Nothing moved, write accepted and held** → the route does not reach the
  clock by this path. Say it in those words. "Not moved by this method, within
  this window", with the window and the load named. It is **not** evidence the
  EC cannot act on the PLs at all — the copy still cannot be seen (§3b) — so
  this is a driver-facing negative about one route, and it is a real result.
- **Nothing moved, and `0x0741` bit 0 read clear for the whole arm** → this is
  a null about the **three ungated sites only**. Nine of the twelve sites sit
  behind that bit and did not run, so this is not the same negative as a null
  with the bit set, and reporting it as one overstates the result. Say which
  sites were live, and that the nine were not exercised. A null with `0x0741`
  bit 0 **set** carries no such caveat: all twelve ran.
- **Both arms flat** → you have measured the battery's own ceiling, not the
  EC's behaviour. Inconclusive as to §1, and worth reporting anyway: it sizes
  what any driver could achieve here.
- **`0x043E` differed between arms** → the arms are not comparable and the
  verdict is void until re-run at matched temperature. Report the numbers and
  do not report a verdict.
- **The PLs went to zero on their own, `0x0741` bit 0 clear** → the EC's own
  clear fired during your arm. That is a race result, it belongs with
  [`pl-clear-0741-gate.md`](pl-clear-0741-gate.md), and Arm B's reading has to
  be redone without it.
- **An `auto:` mark in Arm B** → something transitioned underneath the run. If
  it is an AC event, the arm is void; say which mark it was.
- **Nothing anywhere, all arms** → report each arm's length, the load, the
  charge at start and end, and the host tool's averaging window. A null across
  all passes is a publishable result about *this machine* on battery, and it is
  not "the EC ignores battery PLs".

**Nothing in this repository implies any of these ran.** If you write it up,
the capture and the write-up are what a reader has; a verdict without them is
not one.

## 8. Related

- [`../findings/battery-pl-default-and-zero-semantics.md`](../findings/battery-pl-default-and-zero-semantics.md)
  — the static answers: the battery block's identity, the literal 0, the
  presence-test idiom, and the dark destination page.
- [`pl-clear-0741-gate.md`](pl-clear-0741-gate.md) — the competing writer, the
  same registers, AC-side.
- [`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md) —
  the model for the control arm and the service-stopped pass.
- [`../../linux/patches/gm7mg7p-power-profile/`](../../linux/patches/gm7mg7p-power-profile)
  — the driver work this run is a precondition for.