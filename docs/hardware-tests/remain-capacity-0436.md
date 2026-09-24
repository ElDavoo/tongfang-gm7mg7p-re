# Is `0x0436`/`0x0437` a remaining capacity, or a periodic counter?

**Status: not run.** The pipeline that wrote this file has no machine to run it
on — `CLAUDE.md` is explicit that the GitHub-hosted runners cannot reach the
hardware. The two probes below are preparation, the grading section is a human's,
and nothing in this file, in `ec/annotations/registers.yaml`, or in
`docs/findings.md` §4g says a live read of this pair has happened.

**This does not bear on `0x07B9`/`0x07D0`, issue #1.** That is the charge-limit
pair, these are a battery-state pair two hundred bytes away on a different page,
and no result below says anything about what those two writes do or do not
enforce. Keep them apart in the record as much as in the run.

## 1. The question

`ec/annotations/registers.yaml` carries `XDATA_0436_PAIR` as a deliberate
placeholder, and the placeholder is the interesting part. Upstream
`uniwill-laptop` names the pair `EC_ADDR_BAT_REMAIN_CAPACITY`
(`uniwill-acpi.c:79,81` at the ref quoted in `ec/annotations/xdata-0400-045f.md`
§9), and that is the only name anyone has. The one committed observation of
`0x0436` on this board does not read like a charge figure: in
`evidence/ec-watch/2026-09-18-profile-switch-0400-07ff.csv` the low byte steps
`0x70 → 0x84 → 0x98 → 0xAC → 0xC0`, exactly `+0x14` every ~35 s with no scatter
and `0x0437` never moving. `docs/findings.md` §4g groups `0x0436` with `0x0438`
as "voltage" and corrects that in place; what it corrects *to* is unnamed, on
purpose.

So there are two readings and one placeholder, and both readings are currently
just readings. Calling it a counter on the strength of the `+0x14` ramp is the
same error as calling it a capacity on the strength of upstream's name — one
observation, one guess, no more. The entry says so in as many words, and
`ec/annotations/xdata-0400-045f.md` §8 calls a live read beside an independent
second source the highest-value question this page opened. That is this file.

The capture from 2026-09-18 was taken while charging, at 43-46% capacity, with
the machine otherwise idle. It is exactly the wrong window to tell a charge
reading from a counter, and that is the whole reason this procedure exists.

## 2. Before you start

- **Either** arm will do. The Windows arm is the stronger one — only it can run
  §5.3's exact-copy test, because only WMI is an independent second source on
  the same box at the same time — and the Linux arm needs no Windows at all.
  Doing both is the most a single day buys.
- **Linux arm:** root, and `CONFIG_DEVMEM=y`.
  `ec/tools/ecmem.py` maps physical `0xFE410000` through `/dev/mem` itself,
  which is the same window the DSDT's `ECRR` uses (`docs/findings.md` §4e) and
  so the same bytes the Windows arm reads. On this machine the window is listed
  under `INTC1036:00` in `/proc/iomem` and `/dev/mem` access to it works despite
  `IO_STRICT_DEVMEM` (2026-09-17, kernel 7.2.6). Check the build before
  starting: `grep DEVMEM /boot/config-$(uname -r)`.
- **Windows arm:** the vendor's ACPI driver present and started, and an
  elevated shell. `python windows\tools\ecrw.py read 0x0436` printing a value
  is the check; it needs `UWACPIDriver.sys` from Control Center 3.1.39.0
  (`windows/tools/ecrw.py`'s docstring has the details).
- **AC plugged in and the pack charged** at the start. This is a discharge, and
  it is a long one.
- **A fixed CPU load you can hold for the entire window** and can hold *hard* —
  the discriminators in §5 are all about magnitude, and a light load that
  moves `charge_now` by tens of mWh gives a magnitude too small to compare
  against. Start it before the first sample, and do not let it vary: a load that
  ramps, throttles, or gets interrupted is a run whose deltas cannot be read.
- **A note of the wall-clock times** you pull AC and start and stop the load.
  Neither probe takes marks the way `ec_watch.py --mark` does, so this is by
  hand — the CSVs are timestamped, so the times are all that is missing.

## 3. The run, Windows arm

```console
rem  <date> is that run's YYYY-MM-DD. §7 names the finished file the same way,
rem  so following this produces the §7 set with no rename step.

rem  <samples> is however many seconds the discharge needs to fall by a few
rem  hundred mWh, at --interval 1. It is load-dependent and this file does not
rem  pick it: the requirement is a visible fall in charge_now, and a run that
rem  ends while charge_now is still flat is a run to extend and redo, not to
rem  grade.
python windows\tools\ec_validate.py --samples <samples> --interval 1 ^
        --csv <date>-0436-capacity.csv
```

The script runs two arms. The first is §4g's voltage test, unchanged, ten
samples at 2 s — that is the committed 10/10 and it is left exactly as it was.
It costs twenty seconds and it is what says the read path is still talking to
this EC before twenty minutes of capacity data goes into the same file. Read its
`INCONCLUSIVE` line if it prints one and fix that before the rest means anything.

The second arm is the one this file is for: `0x0436`/`0x0437` once a second
beside WMI `RemainingCapacity`, with `0x0404`/`0x0405` (the bound), `0x0402`/
`0x0403` (the scale) and `0x0434`/`0x0435` (current, so mW can be reconstructed
from the pack's own numbers) in the same CSV row.

Pull AC when you are ready and hold the load. The arm reports the
exact-copy fraction, the bound, and the distinct-value count when it stops, and
**it reports rather than concludes** — §5 is why, and the script says the same
thing in its own output.

## 4. The run, Linux arm

```console
sudo linux/battery-trace/remain-capacity-probe <date>-0436-capacity.csv
```

Three phases, each announced on stdout and marked in the CSV's `phase` column:
`baseline` (AC in, charged, idle), `discharge` (AC out, load running), and
`recovery` (AC back in, or the load stopped). Pull AC and start the load when
the `baseline done` line prints; put AC back when the `discharge done` line
prints.

The phase lengths are environment variables rather than arguments, so a run does
not have to be the default one: `BASELINE`, `DISCHARGE`, `RECOVERY` in samples
at 1 s each, and `STEP` for the interval.

This probe is **read-only**, which is the whole difference from its sibling
`linux/battery-trace/limit-pair-test`. That one writes `0x07B9`/`0x07D0` and
carries a restore phase because it has to; this one has nothing to restore, so
it cannot leave the EC altered, and there is no restore arm to grade. Stopping
it part-way is safe.

It closes with a per-phase first → last delta for three series side by side —
`charge_mwh` from sysfs, `ec_u16`, and `ec_u16` read *as* µWh — because the
EC's unit is not known and the whole point is to see whether the numbers line up
without assuming a conversion. It names which of them fell with `charge_mwh` and
prints the full-capacity bound, and it grades none of it.

### Safety: the fan-tach block

**Do not read `0x0460-0x046F`.** Reading the fan-tachometer registers through
`ECRR` stalled the fans on a sibling board, and the OEM software and
`uniwill-laptop` both sleep 6 ms after every EC access because of it
(`docs/related-projects.md`, issue #94). Both probes stop at `0x045F` and both
check the address list in code before they run a sample, because a typo in a
list is the only way either of them gets onto that page.

Neither probe is a bulk sweep — eight EC reads a second, against the 448 reads
per sweep `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md` §3 puts three
concurrent `ec_watch.py` watchers on — and neither sleeps 6 ms between reads,
because at this cadence the sleep would be the dominant cost. That is a
judgement, not a validated rate, and it is the judgement issue #94 exists to
replace. **If the fans audibly change during a run, stop it and raise the
interval.** A run that moved the fans itself measured the fans, not the battery.

## 5. What to read off

Four observations, in descending order of how much they carry. None of them is
a verdict on its own, which is why the grading is §8's job and not the scripts'.

### 5.1 The periodicity test — the primary one

Does the pair keep stepping by a **constant** delta at a **constant** interval
that does not change when the load does? `+0x14` every ~35 s is what the
committed capture shows, and that is the shape of a counter. A remaining
capacity does not step by a constant: its steps track the current, so they grow
under a heavier load and shrink under a lighter one, and they are not evenly
spaced in time. Take the deltas between consecutive samples in the CSV and look
at their spread. Evenly spaced with no scatter, load changes or not, is the
counter signature and it is the strongest single thing in a capture.

The weakness, stated plainly: a perfectly regular ramp is also what you would
see from a counter that is *not* what anyone expected, and regularity alone
cannot name the thing doing the counting. It says the pair does not track load.
It does not say what it is.

### 5.2 Direction and magnitude

Across the discharge window, does `ec_u16` fall, and by roughly what
`charge_now` (or WMI's `RemainingCapacity`) fell? Both are in the CSV per
sample, as the raw value, as mWh, and at the µWh scale, so the comparison does
not need a conversion decided in advance.

The weakness: **a direction match is not a magnitude match.** A counter that
steps downward across a discharge reads the same as a capacity that does. §5.1
is what separates them, and a run that reports a falling `ec_u16` without
checking its spacing has half a result. A *rising* `ec_u16` while the pack
discharges is the clean counter case, and needs no spacing check at all.

### 5.3 The exact-copy test — Windows arm only

The §4g rule: WMI serves a cached value, so it does not equal the EC
instant-for-instant, but it should *repeat*, exactly, a value the EC held
moments earlier. `ec_validate.py` credits a WMI reading only if the EC had
already shown that value earlier in the run, the same one-directional guard the
voltage arm uses, and prints `N/SAMPLES`.

The weakness is the important part, and it is stated here because it is the one
that makes a `0/N` mean nothing: **this test silently assumes both sides are
mWh.** If the EC's field is a percentage, or a raw ADC count, or units of
100 mWh, then no exact copy is expected and a `0/N` is *not* evidence against a
capacity — it is evidence that the assumption was wrong, which is a different
finding about a different thing. A counter also produces a `0/N`. So a high
fraction is worth something (it would mean the EC holds values Windows
independently reports, which a broken or misread path does not do by accident)
and a low fraction is worth nothing on its own.

### 5.4 The bound — the free one that falls out of the same capture

If the pair is a remaining capacity it cannot exceed the full capacity at
`0x0404`/`0x0405`. Both probes carry that reading in every row, and
`ec_validate.py` prints `ec_u16 <= full_capacity` as a yes/no.

The weakness: **the bound is one-directional.** A small periodic counter passes
it trivially — the committed capture's `0x70`–`0xC0` sits far below any full
capacity. "Never exceeded the bound" therefore settles nothing at all and is not
a result; "exceeded the bound" would be, and it would also mean the run was
near a full pack. Note also that `0x0404`/`0x0405` is itself
`present-untested` under upstream's `EC_ADDR_BAT_FULL_CAPACITY`, so a breach
would be a question about the bound as much as about the pair.

## 6. What this cannot settle

- **One machine, one firmware** (`GMxMGxx_11.800`). Nothing here generalises to a
  sibling board; see `docs/related-projects.md`.
- **The unit, even if it is a capacity.** Nothing in a discharge says whether
  the field is mWh, a percentage, or a scaled count. §5.3's exact-copy match
  would suggest mWh by *elimination*, since the two numbers would then be the
  same quantity — but that is a suggestion, and it needs the pack's own
  `charge_now` to agree on the scale, which is the comparison §5.2 exists to
  make.
- **A window is a window.** A run of ten minutes says nothing about the next
  phase transition, an AC event, or a cold boot, for the same reason
  `docs/findings.md` §4g scopes "not written" to the fifteen minutes it watched.
- **The counter, if there is one.** A run that says "periodic" has not found
  what is counting, what it counts, or what the `0x14` is. That is a new issue
  from the run, not a result of it.
- **The `0x07B9`/`0x07D0` pair.** Restated from the top because it is the most
  likely thing to fold into a findings edit by accident: this run says nothing
  about issue #1, and a result here must not be cited in §4c or §4f.

## 7. Where the output goes

Name the file the way the existing capture does, so the two can be read
together:

```
evidence/ec-watch/<date>-0436-capacity.csv
```

`<date>` is that run's YYYY-MM-DD. Both probes take the path as their first
argument, and `ec_validate.py --csv` appends to a file that already exists
(rather than replacing it), so a run stopped and resumed extends the capture
instead of overwriting it. Follow the argument in §3 or §4 and the file lands
under `evidence/ec-watch/` already named — no rename step, and no second file to
reconcile.

Add the files to `evidence/README.md`, which is the index every findings claim
cites through, and say in that entry what the run was: which arm, AC or battery
throughout, what load, how long, and the phase times. Neither CSV carries the
load, and it is the one thing §5.1 needs to judge a spacing.

## 8. What a result has to say

`XDATA_0436_PAIR` moves off `present-untested` only on what a capture shows,
and in the direction the capture points — not on the entry sounding tidier
afterwards. Concretely:

- **§5.1 says the steps are evenly spaced and load-independent, and §5.2 says
  the pair did not fall with the pack.** The pair is a periodic counter. Rename
  it to something that says so, `status:` to whatever the observation supports,
  and add `live` to `sources:` — this time with a capture behind it, which is
  the condition §8's note in the note is holding open.
- **§5.2 says it fell by a matching magnitude and §5.1 says the steps are
  irregular and load-dependent.** The pair is a remaining capacity and
  `EC_ADDR_BAT_REMAIN_CAPACITY` can be adopted, with the unit still unstated
  unless §5.3 also came out high.
- **The two disagree, or the run is too short to say.** It stays
  `present-untested`, the capture goes into `evidence/` anyway, and what was
  seen is recorded as what was seen. That is not a failed test.
- **Whichever way it lands, `docs/findings.md` §4g's CORRECTION paragraph stays
  where it is.** The `0x0436`/`0x0438` pairing correction is not edited out; a
  result that bears on it goes beside it, in the same style, the way §4a's two
  retractions and §4l's correction are all still readable in place. Per
  `CLAUDE.md`: leave the wrong version visible with the correction next to it.

And a run that never happens is not a failure of this file. The entry keeps its
placeholder, the status stays `present-untested`, and the issue stays open —
which is the case the issue itself describes.
