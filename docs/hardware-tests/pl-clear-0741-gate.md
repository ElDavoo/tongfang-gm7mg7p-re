# Does the EC zero the PLs behind a driver, and does the vendor's own fan-table
# handshake overlap it

**Status: not run.** This procedure was written by the pipeline for a human at
the physical GM7MG7P. `CLAUDE.md` is explicit that the GitHub-hosted runners
cannot reach the hardware, and nothing below has been observed: no register has
been written, no register has been read back, and no result is recorded
anywhere in this repository. `0x0741`, `0x0782` and `0x0783`-`0x0785` hold the
statuses they hold today — a `status:` move is for a *behavioural
observation*, and a prepared procedure is not one.

The static finding this serves is
[`../findings/a7c8-dispatch-slot-and-pl-race.md`](../findings/a7c8-dispatch-slot-and-pl-race.md).
Its answer is that the host-writes-PLs / EC-zeroes-PLs race is **possible**:
the routine that zeroes PL1/PL2/PL4 is reached on two of the divide-down
scheduler's nine cases rather than once at boot, and `AP_OEM` (`0x0741`) bit 0
is a bit the EC revokes itself and — by the method that scan can reach — never
restores. What static evidence cannot reach is whether the two entry gates and
the bit's clear window are ever true **at the same time**, which is what this
run is for.

## 1. The question

Three separate things, in the order they matter. Arm C below is the control
for the second, and without it the second's negative means nothing.

1. **Does `0xA7C8` run at all after boot?** If it never runs, nothing below it
   matters and the race is not reachable on this machine however the bit is
   set. This is the cheapest arm and it gates the other two, because its
   witness (`0x0782` bit 5 going) is reached under every arm's conditions — see
   §3.
2. **When it runs with `0x0741` bit 0 clear, do the PLs actually go to zero?**
   The static decode says the four stores at `0xA833`-`0xA842` are on the path
   the `jb acc.0` at `0xA82F` fails to take. A write being stored is not
   evidence the EC acts on it, and this is the arm that would make it one.
3. **Does the vendor's `RefreshDefaultFanTableAll` overlap that?** The service
   deliberately parks `0x0741` bit 0 clear for the duration of its
   `RefreshDefaultFanTableAll` — at least 1.5 s, derived from its own
   `do { Thread.Sleep(500); ... } while (num != 3)` loop bounds and not
   measured. If the EC's turn lands inside that window, a Linux driver running
   alongside the vendor service loses its PLs with no error anywhere.

**What a run cannot settle.** The two entry gates are `[0x0780] != 0xA2` and
`[0x06E6] == 0x01`, both runtime facts about two bytes. A run that watches both
(§3) tells you their natural values on this machine, which is real progress and
is not the same as tracing what sets them — that is the follow-up the write-up
opens and it is one trace from `bank0 0xCC8E`/`0xCCD2`.

**And no rate.** `scheduler-divide-down-cycle.md` §5's four refusals travel
with this procedure: the scheduler's period in entries is a count and not a
time, the tick period is unestablished (`TMOD` at `0x89` is never read), and
the poller's own period against the flag is unestablished too. The poll
interval below is chosen to be short, not because it is known to resolve the
routine's turn. **A run that sees nothing over its window has learned "not
moved by this method, within this window" and nothing more.**

## 2. Before you start

- **Root, and `CONFIG_DEVMEM=y`.** `ec/tools/ecmem.py` maps physical
  `0xFE410000` through `/dev/mem` itself, the same window the DSDT's `ECRR`
  uses. Check the build first: `grep DEVMEM /boot/config-$(uname -r)`.
- **AC plugged in for the whole session.** The vendor service rewrites the PLs
  on every AC ↔ battery change, which would drown the thing being measured.
- **The current mode, and what the PLs read before anything is touched.**
  Write them down; §5's restore needs them and Arm B's comparison needs the
  "before".
- **Whether the vendor service is running**, and which way round you want each
  arm. Arms A and C are safe with it running. Arms B and D are cleaner with it
  stopped, and Arm D is the only one that *needs* it running.

### Safety

**Clearing `0x0741` bit 0 is the state the EC treats as "no host agent".** Two
things follow, and both are in the direction of *less* restriction rather than
more: `0xB13A` forces the manual-ctrl charge profile back to High Capacity,
and the PL clear at `0xA833` runs. So the register write is not the hazard —
**the PL clear it invites is.** On a laptop that means the CPU may drop to a
lower sustained power limit until you restore. That is a performance change,
not a stability one, and §5 restores it.

**Seed the PLs at or below what they already read.** Never above. A PL set
above what the machine is running now is a request for more power than the
chassis is validated for, and nothing in this repository establishes what the
EC clamps. The service's own values are the reference for what is sane:
60/60/165 Gaming, 75/75/165 Turbo, 35/35/165 Office
(`../findings.md` §7 / `windows/vendor-ec-map.md` "Power modes"). Seeding
0/0/0 is safe and is the most sensitive arm — it is Arm B's default.

**Do not read `0x0460`-`0x046F`.** Reading the fan-tachometer registers
through `ECRR` stalled the fans on a sibling board, and both the OEM software
and `uniwill-laptop` sleep 6 ms after every EC access because of it
([`../related-projects.md`](../related-projects.md), issue #94). Nothing in
§3's watch set is on that page.

**Nothing in the watch set is outside the host window.** `0x0741`, `0x06E6`,
`0x0780`, `0x0782`, `0x0783`, `0x0784`, `0x0785` and `0x078B` are all in
`0x0000`-`0x07FF`, which this machine maps
(`evidence/ec-watch/2026-09-24-host-window-page-census.txt`). A byte that
read `0xFF` for the whole run would be a byte the host cannot see, not a byte
the EC left alone — `ec_timer_capture.py` refuses out-of-window addresses
rather than letting that misreading happen.

**Arm D's trigger is destructive to the vendor's own state.**
`RefreshDefaultFanTableAll` is called from `FanTable_Refresh`
(`windows/decompiled/v3.1.39.0/GCUService/MyControlCenter.MyFan.FanTable/FanTable_Manager1p5.cs:227`,
and the CML partial at `:90`), and `FanTable_Refresh` is what `FanTable_Init`
calls in each of four branches: the EC version differs, the local JSONs are
invalid, they are all zero, or they are not found. The service logs which
branch it took — "EC is the different version", "The local data is invalid",
"The local data is all zero", "local fan table is not found" — and **that log
line is the cheapest way to confirm the trigger fired**, so capture it.
Forcing it by deleting or blanking the local JSONs makes the service rewrite
them from whatever the EC returns. **Back `UserFanTables\` up first**, and say
in your report that you did. If you would rather not, run Arm D as a passive
baseline (Arm D') instead and say that is what you did — a passive baseline
cannot answer question 3, and reporting it as though it could is the error this
section exists to prevent.

## 3. The run

Every address in the watch set, and why it is there:

| address | what it is | what a change means |
|---|---|---|
| `0x0741` | `AP_OEM`, bit 0 the gate | bit 0 clear is the state `0xA82B` fires in |
| `0x0780` | entry gate 1: `[0x0780] != 0xA2` | a change moves the routine's reachability |
| `0x06E6` | entry gate 2: `[0x06E6] == 0x01` | ditto |
| `0x0782` | `BIOS_OEM_2`, bits 0 and 5 the one-shot's two gates | **bit 5 disappearing is the host-visible proof the tail of `0xA7C8` ran**, provided bit 0 was set when it went |
| `0x0783` `0x0784` `0x0785` | PL1 / PL2 / PL4 | the registers at risk |
| `0x078B` | the fourth byte the clear writes | corroborates a clear with `0x0783`-`0x0785` |

`0x0782` bit 5 is the one worth explaining, because it is what makes question 1
answerable without guessing. `0xA80A`'s `anl a,#0xdf` consumes it, and it is
reached only when `0x0782` bit 0 **and** bit 5 are both set: the two `jnb`s at
`0xA802` and `0xA806` both read *this* register, not `0x0741`, and either one
clear jumps straight to `0xA82B`. `0x0741` is not consulted until `0xA82F`,
after that branch target, and bit 0 **clear** there is what lets the PL clear
run. So the bit's disappearance witnesses a pass of the routine's tail under
every arm alike, and not only Arm A's; what `0x0741` decides is whether that
same pass also zeroes the PLs, which is Arm B's witness rather than Arm A's.

### Arm A — does the routine run? (safe, service running)

Leave `0x0741` alone. Record `0x0782`'s bits 0 and 5 first — bit 0 is the
other half of the gate, so a bit-5 disappearance only means something against
the bit-0 value you started from.

```console
$ sudo python3 ec/tools/ecmem.py read 0x0741 0x0780 0x06E6 0x0782 0x0783 0x0784 0x0785 0x078B
$ sudo python3 ec/tools/ec_timer_capture.py \
      --addrs 0x0741,0x0780,0x06e6,0x0782,0x0783,0x0784,0x0785,0x078b \
      --interval 0.05 --seconds 600 --csv <date>-pl-armA.csv \
      --note "Arm A, vendor service running, AC, idle; watching for 0x0782 bit 5"
```

Ten minutes is a starting point, not a derived one — see §1 on rates. Run it
longer if nothing moved; the honest report for a quiet arm is the length you
ran it and that it was quiet.

### Arm B — does the PL clear fire?

Seed first, watch second. **Do Arm B's writes with the service stopped**, or
it will overwrite them for you and you will be measuring the service.

```console
$ sudo python3 ec/tools/ecmem.py write 0x0741=<bit0 clear> 0x0783=00 0x0784=00 0x0785=00 0x078b=00
$ sudo python3 ec/tools/ec_timer_capture.py \
      --addrs 0x0741,0x0780,0x06e6,0x0782,0x0783,0x0784,0x0785,0x078b \
      --interval 0.05 --seconds 600 --csv <date>-pl-armB.csv \
      --note "Arm B, bit 0 clear, PLs seeded 0/0/0"
$ sudo python3 ec/tools/ecmem.py read 0x0780 0x06e6        # the two gates, after the run
```

The PL reads of `0/0/0` are the **sensitive** arm: any non-zero value in the
capture that was not written by you is the EC putting one there, which is the
opposite event and is just as interesting. Record which way it went.

**If the two gates do not hold, say so and treat the arm as inconclusive.**
`0x0780 == 0xA2` or `0x06E6 != 0x01` means the routine's tail was never
reached, whatever the PLs did.

### Arm C — the control (this is what makes Arm B mean anything)

Identical to Arm B with `0x0741` bit 0 **set**, and a nonzero seed so a
write that took is visible:

```console
$ sudo python3 ec/tools/ecmem.py write 0x0741=<bit0 set> 0x0783=3c 0x0784=3c 0x0785=a5 0x078b=00
$ sudo python3 ec/tools/ec_timer_capture.py \
      --addrs 0x0741,0x0780,0x06e6,0x0782,0x0783,0x0784,0x0785,0x078b \
      --interval 0.05 --seconds 600 --csv <date>-pl-armC.csv \
      --note "Arm C, bit 0 set, PLs seeded 60/60/165"
```

`0x3C`/`0x3C`/`0xA5` are 60/60/165, the Gaming values already recorded live.
The prediction is that the PLs **stay**. If they do not, the capture is
watching something other than this routine — a different writer, or your seed
never took — and Arm B's result has to be re-read with that in hand.

### Arm D — the vendor's overlap

With the service running and the PLs as the service itself sets them, watch
across a fan-table refresh. Arm A's command with a longer window does this as
a passive baseline (Arm D'). The active version needs §2's trigger.

```console
$ sudo python3 ec/tools/ec_timer_capture.py \
      --addrs 0x0741,0x0780,0x06e6,0x0782,0x0783,0x0784,0x0785,0x078b,0x0f5d,0x0f5e,0x0f5f \
      --interval 0.05 --seconds 1800 --csv <date>-pl-armD.csv \
      --note "Arm D, service running; 0x0F5D-0x0F5F is the fan-table mailbox"
<then trigger RefreshDefaultFanTableAll, per section 2>
```

The three mailbox bytes are in the window and are the handshake's own
progress indicator — `0x0F5D`/`0x0F5E` holding `0xFD`/`0xC9` means the
handshake is in flight. **A PL going to zero while `0x0741` bit 0 reads clear
and the mailbox is in flight is the result this whole file exists for**, and it
is the one a driver has to defend against.

## 4. Marks

`--mark` reads labels on stdin and stamps them, which is how you mark the
write, the trigger, and anything you touched by hand:

```console
$ { echo "arm B: clearing 0741 bit 0, seeding PLs 0/0/0"; \
    sleep 0.5; \
    echo "trigger: deleted DefaultFanTable_*.json"; \
    sleep 300; echo "arm D done"; } \
  | sudo python3 ec/tools/ec_timer_capture.py ... --mark
```

A mark is when **Linux** saw the action, not when the EC did. That is stated
in the tool's own docstring and it is the reason the capture cannot be used to
time the EC's turn — only to place your actions inside it.

## 5. Restore, and do it even if an arm failed

```console
$ sudo python3 ec/tools/ecmem.py read 0x0741 0x0782 0x0783 0x0784 0x0785 0x078b
$ sudo python3 ec/tools/ecmem.py write 0x0783=<before> 0x0784=<before> 0x0785=<before> 0x078b=<before>
$ sudo python3 ec/tools/ecmem.py read 0x0741 0x0782 0x0783 0x0784 0x0785 0x078b
```

The pre-run `ecmem.py read` in §2 is not optional: it is the only record of
what the bytes held before an arm disturbed them, and the PL values to put
back are in it. `ecmem.py write` reads back after each write and prints both,
so the third command is the verification that the restore took. **If an arm
failed halfway, restore anyway** — a machine left with its PLs at zero is a
machine that throttles, and the person who finds it will not know why.

If the service is running it will rewrite the PLs on its own next mode switch
or AC event, so **restore the `0x0741` bit before the PLs**: a clear bit with
the service idle is the exposed state, and restoring the PLs into it is a race.

## 6. Where the output goes

One capture per arm, under `evidence/ec-watch/`, named for the arm so a
sixth arm later does not collide with these:

```
evidence/ec-watch/<date>-pl-armA.csv
evidence/ec-watch/<date>-pl-armB.csv
evidence/ec-watch/<date>-pl-armC.csv
evidence/ec-watch/<date>-pl-armD.csv
```

Add a bullet for each to `evidence/README.md`. `ec_timer_capture.py` writes
`ts,addr,old,new` rows plus `#` comment lines carrying the date, kernel, AC
state, interval, address list and whatever `--note` said; every consumer in
this repository skips the comments, so leave them.

**Grade it with the committed checkers before writing anything up.**
`check_capture_claims.py` and `check_capture_dates.py` both read that
directory, and `capture-claim-denial` is the finding a capture written without
one produces.

## 7. What a result has to say

One arm per bullet, each a scoped positive and never a bare "it worked".

- **`0x0782` bit 5 disappeared** — the tail of `0xA7C8` runs on this machine,
  and it is the same witness in every arm, because the gate is on `0x0782` and
  not on `0x0741`. Say how long after boot, and that it is a one-shot so there
  is **no second observation** of it: it witnesses the *first* pass only, and
  the PL clear's recurrence is not established by it.
- **`0x0783`-`0x0785` went to zero in Arm B** — the clear fires when bit 0 is
  clear. Name the gates' values at the time (`0x0780`, `0x06E6`), because
  without them the result does not say the routine was reachable.
- **Arm B quiet and the gates held** — the PL clear did not fire in this
  window. Write it as "not moved by this method, within this window", and give
  the window. It is **not** evidence the clear never fires.
- **Arm B quiet and a gate did not hold** — the routine's tail was never
  reached. Inconclusive, and the useful next datum is what that gate reads.
- **Arm C's PLs moved** — the seed did not take, or something other than
  `0xA7C8` writes them. Arm B's result is void until this is resolved.
- **Arm D caught a clear inside the handshake** — the vendor's own service
  produces the condition a Linux driver has to survive. That is a driver-facing
  finding and belongs in the `0x0741` row of `ec/annotations/registers.yaml`.
- **Nothing anywhere** — report the length of each arm and the gate values.
  A null across all four with the gates holding is a real, publishable result
  about *this machine*, and it is not "the EC does not clear the PLs".

## 8. Related

- [`../findings/a7c8-dispatch-slot-and-pl-race.md`](../findings/a7c8-dispatch-slot-and-pl-race.md)
  — the chain, the case table, and the race verdict this procedure tests.
- [`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md) —
  the `0x0751` isolation run, and the writer census §4 depends on. Its run
  predates this finding and its conclusions are unaffected by it.
- [`fan-table-defaults-0f5d.md`](fan-table-defaults-0f5d.md) — the same
  handshake, from the fan-table side. If you are running both, do this file's
  Arm D in the same session: that is the overlap question, and two separate
  sessions will not produce it.
- `ec/tools/ec_timer_capture.py`, `ec/tools/ecmem.py` (Linux) and
  `windows/tools/ecrw.py` (Windows) — the read and write paths. Both write
  through the same physical window, so either is a valid arm.
