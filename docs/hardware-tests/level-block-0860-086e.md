# Are `0x086B`/`0x086C`/`0x086E` a fan speed or a power level?

**Status: not run (issue #252).** The pipeline that wrote this file has no
machine to run it on — `CLAUDE.md` is explicit that the GitHub-hosted runners
cannot reach the hardware. **No live read of `0x0860`-`0x086E` has happened on
this board.** Nothing in `../../ec/annotations/registers.yaml`,
[`../findings.md`](../findings.md) or
[`../../ec/annotations/xdata-086x-dispatch.md`](../../ec/annotations/xdata-086x-dispatch.md)
records one, and the `XDATA_086x` entries stay `present-untested` and
unnamed until a human runs this and commits the capture. The instrument
(`../../windows/tools/manual_fan_ctrl_probe.py --level-block`) and its offline
checks are committed; the reading is not. §7 says what a result has to say, and
**both** of §4.1's outcomes are reportable.

This is the runnable form of §10 of
[`xdata-086x-dispatch.md`](../../ec/annotations/xdata-086x-dispatch.md), which
is written down to be run later and has not been. Keep the two in step: §10
there is the question, this file is the procedure, and if they ever disagree
about a number, this file is the one a run is taken from.

**This file is the reference; the tool is the half that moves.** §3's command
is §3's cadence, and the probe's defaults are §3's numbers for that reason — the
defect issue #146 is about is the two carrying different ones. Neither makes an
interval safe, and §3b's second pass is a human's; see §2.

## 1. The question

`compute_level_blocks_086b_086c_086e` (`bank0:0x9D9B`, 627 bytes) computes three
result bytes from a five-byte working set reused by all three of its blocks.
The arithmetic is legible and the units are not: the same `0x0865` is written
from a per-mode seed in one routine and from the constants `0x48`/`0x4C` in
another, the same result byte is copied out to two unrelated destinations, and
nothing on that page names what the numbers are. The entries say
`UNITS NOT DETERMINED` and stay `XDATA_086x` rather than take a name that a
wrong unit would outlive.

So there are two readings and one block, and both are currently just readings.
Are `0x086B`/`0x086C`/`0x086E` a **fan speed** — a target the EC drives the fan
toward, which a Linux `platform_profile` would then have to reproduce, since it
drives the fan by writing the mode byte and a table and not by writing this — or
a **power level**, which is a different quantity with a different consumer? A
proportional relationship to fan speed across three or more modes would justify
the first name. A constant, or nothing resembling the fan curve, is a result
too and says the block is not a level at all. That is §4.1, and §7 says what
each outcome means for the entries.

`0x0860` itself is the selector the dispatch hangs on, and the run watches it
for the same reason: `0x00` and `0xFF` are its idle and busy marks, and a busy
mark in the capture is the dispatch happening while it was watched (§4.3).

**What this does not touch.** Issue #235 asks what `0x0440` and `0x06E6` are.
Those two bytes are in this capture — `0x06E6` because the gate needs it,
`0x0440` because the temperature sweep already covered `0x0400`-`0x045F` — and
§4.4 says to record what they held, and no more. One session, two documents:
[`xdata-0440-readers.md`](../../ec/annotations/xdata-0440-readers.md) is where
that question gets settled, and it is not folded in here.

## 2. Before you start

- **Windows, Control Center 3.1.39.0 installed, the vendor's ACPI driver
  present and started, an elevated shell.**
  `python windows\tools\ecrw.py read 0x0860` printing a value is the check; it
  needs `UWACPIDriver.sys` and nothing in this procedure writes the byte.
- **AC plugged in for the whole session.** The vendor service rewrites the whole
  bundle on every AC ↔ battery change (`../findings.md` §7), which would drown
  the thing being measured.
- **A fixed CPU load you can hold hard for the whole session.** A fan speed
  moves with the die, so a result byte read against a warming die and a cooling
  one are not comparable. Start it before the first run and hold it across all
  three; the probe prints `CPU_TEMP`/`GPU_TEMP` per arm precisely so a run
  whose load was not flat is visible rather than argued about.
- **A fan-speed readout that is not the EC, noted by hand.** This is the one
  piece of preparation the run genuinely needs, and it has a catch worth saying
  out loud: the EC page that would supply a tachometer is `0x0460`-`0x046F`, and
  **this procedure does not read it** (see the safety note below). So the
  reference is a reading taken by eye and written down next to the wall-clock
  time. On the Windows run of §3, that is the vendor Control Center's own fan
  RPM display — the same number the machine is sold on, and the one the
  `PRIMARY_FAN`/`SECONDARY_FAN` sysfs in [`../findings.md`](../findings.md) was
  confirmed against, on physical sound, on this board. If you are also doing a
  Linux pass on the same machine, that sysfs is the same quantity and a usable
  cross-check; it is not available during the Windows run, so do not plan
  around it.
  Note the reading and the time for **each** mode. The CSV carries no fan speed,
  so the times are all that is missing, and §4.1 is unreadable without them.
  - The weaker in-band proxy, free but second-best: `0x075B`/`0x075C` are the
    vendor's `ADDR_EC_MAIN_FAN_L/R_DUTY_BYTE` (issue #123) and are **already in
    the capture**. A duty is not a speed — it is what the fan is being asked for,
    not what it is doing — so use it to corroborate a direction, never to
    establish the relationship on its own, and say which of the two you read.
- **Three modes, not one.** §4.1's "across three or more modes" is the
  condition, and the vendor's three are the set: Office `0xA0`, Gaming `0x00`,
  Turbo `0x10`.
- **The current mode as the vendor UI reports it**, and the starting value of
  `0x0751`, written down. The probe prints both, but a mode the UI disagrees
  with is worth knowing about.
- **A way to stop the service**, for the second pass in §3: `sc stop` on the
  Control Center service, confirmed with the vendor UI gone. See §5's confound.

### Safety

**Do not read `0x0460`-`0x046F`.** Reading the fan-tachometer registers through
`ECRR` stalled the fans on a sibling board, and the OEM software and
`uniwill-laptop` both sleep 6 ms after every EC access because of it
([`../related-projects.md`](../related-projects.md), issue #94). The probe's
temperature sweep stops at `0x045F` and its `--level-block` adds nothing on that
page; both facts are asserted in the offline suite and again by
`manual_fan_ctrl_probe.py --self-test`, because a typo in an address list is the
only way onto it.

**Write `0x0751` only, and only `0x00`, `0x10` or `0xA0`** — the three values the
vendor service itself writes. **Nothing in the level block is written at all**:
`--level-block` is a read-only widening of the watch set, and the restore is in
the outermost `finally`, so it runs even if an arm blows up mid-run. Stopping
the run part-way is safe.

**On the rate.** `--interval`'s 0.5 s default is §3 of
[`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md)'s
starting point and nothing more: **no interval here is validated, and #94 is the
open work that would make these tools safe by default.** `ecrw.Ec.read` is one
`ECRR` `DeviceIoControl` per byte with nothing between calls, so
`--level-block` puts **222 reads in every sweep** against the committed run's
206 — the most `ECRR` traffic of any run in this repository, and the only
one on both a 222-byte sweep and a held load. The 0.5 s is the sleep *between*
sweeps, so the achieved rate is lower than 222/0.5 and nobody has measured it
against a driver. **If the fans audibly change during a run, stop it and raise
the interval.** A run that moved the fans itself measured the fans, not the
block. Halving the interval to 0.2 s — the lever §4.3 asks about — doubles the
per-second traffic, and is the operator's call rather than a recommendation.

## 3. The run

Three runs, one capture. `--csv` appends and the `MARK` rows name which arm each
row follows, so following this produces a single session's capture rather than
three files to reconcile.

```console
rem  <date> is that run's YYYY-MM-DD. §6 names the finished file the same way,
rem  so following this produces the §6 file with no rename step.
rem
rem  30 s per arm and --interval 0.5 are §3's numbers (0xA0/0x00/0x10 in that
rem  order). The no-op control arm and the restore are the tool's own: it holds
rem  a no-op arm, writes the target, holds, and restores 0x0751 in a finally,
rem  so there is nothing to press and nothing to put back by hand.
rem
rem  Sample rate: 222 ECRR reads every 0.5 s. See the safety note in §2.

python windows\tools\manual_fan_ctrl_probe.py 0xA0 30 --level-block ^
        --csv <date>-086x-level-block.csv
python windows\tools\manual_fan_ctrl_probe.py 0x00 30 --level-block ^
        --csv <date>-086x-level-block.csv
python windows\tools\manual_fan_ctrl_probe.py 0x10 30 --level-block ^
        --csv <date>-086x-level-block.csv
```

Each run prints its two arms, the temperatures, and — under `--level-block` —
the four readings of §4.2 and §4.3, reported and not graded. Note your fan-speed
reading and the time for each run as you go (§2).

**The second pass, which is the one that says whose write it was.** Repeat at
least the Office-vs-Turbo pair with the vendor service stopped, §3a of
[`manual-fan-ctrl-0751-isolation.md`](manual-fan-ctrl-0751-isolation.md): with
the service up, a `0x086x` move is not yet the EC's, because
`../findings.md` §7 records that the service rewrites the whole bundle on every
switch. With it stopped, whatever moves is the EC's. Use a separate file for
that pass so the two are not windowed together.

### Reading the capture

`--csv` writes the shape `ec_watch.py --mark --csv` writes and
`ec/tools/grade_0751_isolation.py` already reads, so the capture is the grader's
input with no conversion (issue #124):

```console
python ec\tools\grade_0751_isolation.py <date>-086x-level-block.csv
```

Know what that does with it before you read its output. Its `WATCHED` set is the
`0x0751` question only — PL1/PL2/PL4, the fan table, the reload mailbox and
`0x07C6` — so **`0x0860`-`0x086E` and `0x06E6` land in its deliberate "other
addresses, not graded here" bucket.** That is an honest landing for them, not a
gap to work around: teaching the grader about the level block is issue #124's
change, not this one's. The grader is useful here for what it does share — the
per-window `window delta` lines for `0x075B`/`0x075C` and the two temperatures,
which are the record of whether the load held flat across an arm.

## 4. What to read off

Four observations, in descending order of how much they carry. None of them is a
verdict on its own, which is why the grading is §7's job and not the tool's.
**The probe prints the two it can see from a sweep — §4.2 and §4.3. The other
two need the fan-speed reading taken by hand (§2), so they are a human reading
the capture.**

### 4.1 The three results against fan speed — the primary one

For each of the three modes, take `0x086B`, `0x086C` and `0x086E` at the end of
the write arm and set them beside the fan-speed reading you noted by hand.

**A proportional relationship across three or more modes is what would justify
a name; a constant, or nothing resembling the fan curve, is a result too and
would say the block is not a level** (§10 step 4 of
[`xdata-086x-dispatch.md`](../../ec/annotations/xdata-086x-dispatch.md), quoted
rather than paraphrased because the paraphrase is where this goes wrong). The
shape to look for is the three results moving *together* across modes and
tracking the curve rather than any one of them moving on its own. The three are
computed from different seeds and different overrides
(`0x0865`-`0x0869` → `0x086B`/`0x086C`/`0x086E`), so agreement between them is
evidence about the block and disagreement is evidence about one of the three.

The weakness, stated plainly: **proportional is not units.** A clean fan-shaped
relationship says the block is tracking a fan quantity; it does not say the
bytes are RPM, a percentage of full, or a PWM code. Naming them needs a second
source, and this run has none — §4.2's clamp constants are numbers the firmware
compares against, which is a reading of the *guard* and not a scale. So a
positive §4.1 buys a direction and a shape, and the units stay open in the
note even after the rename §7 asks for.

A result byte that never moves across all three modes is also a reading, and a
useful one: it says this mode byte is not what makes that byte move, which is a
question about the `0x0783`-`0x0785` overrides rather than about the fan.

### 4.2 The clamp cross-check — `0x086B`/`0x086C` only

§5 of [`xdata-086x-dispatch.md`](../../ec/annotations/xdata-086x-dispatch.md)
gives `0x086B` and `0x086C` the same three clamps, at `0x23`, `0x14` and `0x0F`,
each guarded by bit 7 of `0x0751` (`MANUAL_FAN_CTRL`) together with a different
pairing of bits 1 and 0 of `0x07C6` (`AP_OEM_6`). **If a result ever sits exactly
at one of those three values, the clamp is live**, and the two guard bytes at
that moment are a direct read of the guard conditions. Both are in the capture —
`0x0751` is the byte under test and `0x07C6` is in the committed watch set — so
this cross-check costs no new byte. Record which clamp value and under which
arm, because that is the observation §5's table predicts and nothing else in
this run tests.

**`0x086E` has no clamps at all** — §5's table says so, and the third block
caps nothing. A result sitting at `0x23`/`0x14`/`0x0F` on `0x086E` is a direct
read of the guard for the first two and **means nothing of the kind for the
third.** Keep the two apart when you write this up, and do not let a `0x23` on
`0x086E` become evidence for a clamp. The probe's summary prints the two cases
in different words for exactly this reason.

### 4.3 The `0x0860` busy mark

`0x0860 == 0xFF` is the busy mark and the transition is the dispatch in progress
(§4 of [`xdata-086x-dispatch.md`](../../ec/annotations/xdata-086x-dispatch.md)).
§10 step 3 asks for sub-second sampling to catch it, and 0.5 s is sub-second.
The probe's summary says whether it saw `0xFF` in each arm and which.

**The gap, which is the honest part: a busy mark that opens and closes between
two sweeps leaves no row at all.** The capture records transitions, not values,
so a `0x00 → 0xFF → 0x00` that completes inside one interval is invisible, and
"not seen" is "not found at this interval", never "does not happen" — per
`CLAUDE.md`, a static or sampled zero is *not found by this method*. The only
lever is `--interval`, at the traffic cost §2 names.

Note also that `0x0860` at `0xFF` in the **control** arm is the more interesting
of the two: it is a mark with no `0x0751` change under it, and it would say the
EC runs this dispatch on its own schedule.

### 4.4 The gates, free, and not this document's question

`bank0:0x9CA6` (`gate_06e6_442_then_sync_046a_from_086b`) is gated on `0x06E6`
being `1` plus bit 4 of `0x0442`, and reads `0x086B`. `--level-block` adds
`0x06E6` for that reason; `0x0440` and `0x0442` were already in the temperature
sweep. So the gates and the source are in this capture without a new byte for
them. **Record what they held in each arm and no more** — what `0x0440` and
`0x06E6` *are* is issue #235's question and
[`xdata-0440-readers.md`](../../ec/annotations/xdata-0440-readers.md)'s, and
§7 says what a `0x086x` result may and may not be read into on the strength of
them. One session serves both; two documents record it.

## 5. What this cannot settle

- **Whose write it was.** The main arm switches mode with the vendor service
  running, and `../findings.md` §7 records that the service writes the whole
  bundle on every switch. So a `0x086x` move in that arm is **not yet the EC's**,
  and the control arm does not separate this — the fan duty bytes it exists for
  drift on a warming die, which is a different confound. §3's service-stopped
  second pass is the arm that separates them, and a capture without it says
  "something wrote this while the mode changed", which is a weaker claim than
  "the EC wrote this". Whether the service writes any `0x086x` byte at all is
  answerable statically and is not asked here.
- **The `0x9CA6` sync, out of reach on purpose.** That routine syncs `0x046A`
  *from* `0x086B` — and `0x046A` is on the forbidden `0x0460`-`0x046F` page. **A
  run reads the gates and the source and never the destination, and the sync
  therefore cannot be confirmed live without breaking #94's rule.** What the
  capture shows instead: whether `0x086B` moved, and whether it moved under the
  gates. That is most of what is wanted and is not the same thing.
- **The units, even given a clean fan-shaped relationship** (§4.1). Proportional
  is not a unit, and a wrong unit baked into a symbol outlives the note that
  would correct it — which is why the entries stay `XDATA_086x` (§7).
- **A window is a window.** Three runs of 30 s each say nothing about the next
  suspend, AC transition, cold boot or EC reset, for the same reason
  `../findings.md` §4g scopes "not written" to the fifteen minutes it watched.
- **One machine, one firmware** (`GMxMGxx_11.800`). Nothing here generalises to a
  sibling board; see [`../related-projects.md`](../related-projects.md).
- **That a byte was read and held still is not a claim it does nothing.** The
  same asymmetry the grader's own closing paragraph prints: a byte that does not
  move inside a window may still move at the next event.
- **The `#99` question.** This run writes `0x0751` and watches what follows. It
  does not re-do the `0x0751`-alone isolation, and a result here must not be
  cited in support of that file's §7.

## 6. Where the output goes

Name the file the way the existing captures are named, so the two can be read
together:

```
evidence/ec-watch/<date>-086x-level-block.csv
```

`<date>` is that run's YYYY-MM-DD. `--csv` appends to a file that already
exists rather than replacing it, so a run stopped and resumed extends the
capture, and the three runs of §3 land in one file with their `MARK` rows
telling them apart. The service-stopped second pass goes in its own file
(`<date>-086x-level-block-service-stopped.csv`) rather than the same one, so the
grader does not window the two conditions together.

Add the file to `evidence/README.md`, which is the index every findings claim
cites through, and say in that entry what the run was: which modes, service up
or stopped, the fan-speed readings **and the times they were taken** (the CSV
carries no fan speed, and §4.1 is unreadable without them), the load, AC state
throughout, and the `--interval` used. None of that is in the capture.

## 7. What a result has to say

**Both outcomes of §4.1 are reportable and this file is not written as though
only one closes the issue.** Concretely:

- **§4.1 shows the three results moving together with fan speed across three or
  more modes.** The block is a fan-speed target. Rename the entries to say so,
  move `status:` to whatever the observation supports, and add `live` to
  `sources:` — this time with a capture behind it. **Say which fan-speed readout
  you used** (§2) and, because §4.1's relationship fixes a shape and not a
  scale, say that in the note too: a name is earned by the relationship, not by
  the relationship plus a guess at the units. Note that **`0x086C` has no
  `registers.yaml` entry at all** — the middle of the three results is the one
  the census did not enter — so naming it means adding one, in the same change,
  with the same `status:` discipline as the other two.
- **§4.1 shows a constant, or nothing resembling the fan curve.** The block is
  not a level. That is a finding, it is worth recording as one, and the entries
  say so rather than staying ambiguously unnamed. If one of the three tracks and
  the others do not, that is a result about *which* of them, and it belongs
  beside the others rather than averaged into them.
- **§4.1 is too short to say, or the arms are not comparable** (the load was not
  flat, the fan-speed readings were not taken, the service confound was not
  separated). The entries stay `present-untested` and `XDATA_086x`, the capture
  goes into `evidence/ec-watch/` anyway, and what was seen is recorded as what
  was seen. That is not a failed test.
- **Whichever way it lands, nothing else in the record is edited out.** A result
  bearing on `XDATA_0860` goes beside that entry's note in the same style the way
  `../findings.md` §4a's two retractions and §4l's correction are all still
  readable in place. Per `CLAUDE.md`: leave the wrong version visible with the
  correction next to it.

**`XDATA_0860`'s status does not follow from a result about the other three.**
The question here is whether the results are a level; `0x0860` is the selector,
and §4.3 is a separate observation about its busy mark. A result that names the
level says nothing about what `0x0860` is.

**A result here says nothing about `0x046A`.** §5 is the reason: the destination
of the `0x9CA6` sync is on the page this procedure does not read, so no live
read in this session can say whether that sync fires. A capture that shows
`0x086B` moving is a fact about `0x086B`.

**The generator is not hand-edited.** If a name or a status moves,
`ec/ghidra/xdata-symbols.csv` is regenerated from
`../../ec/annotations/registers.yaml` by `ec/tools/gen_xdata_symbols.py`
— never by hand, and in the same change as the entry, because the generator
reads the YAML and never writes it and a rename must not be able to imply a
status change.

**A run that never happens is not a failure of this file.** The entries keep
their placeholder, the status stays `present-untested`, and the issue stays open
— which is the case the issue itself describes.
