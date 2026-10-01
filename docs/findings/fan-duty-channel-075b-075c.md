# The 0x14 between 0x075B and 0x075C is the EC's own constant, and the committed captures cannot name either fan (issue #247)

(Static reading and arithmetic over committed files: the three `evidence/ec-watch/`
captures, `ec/decompiled/bank0/`, `ec/annotations/` and `windows/decompiled/`.
No laptop, no EC and no Windows machine is involved — no register was read back
and nothing here is a live test of either byte. Every figure is
`ec/tools/fan_pair_correlation.py`'s output, and §8 names the command.)

## The claim

**Three things, and only the first is a result.**

1. **The difference `0x075B - 0x075C` is the EC's own bias constant, not a
   thermal difference between two fans.** Across all three committed
   `0x0700`-`0x07FF` captures the difference takes exactly two values — `0x00`
   and `0x14` — and `0x14` is the offset the hand-decoded `0x8DE0` subtracts
   from the first channel to produce the second. A difference that is
   *always* the firmware's own offset is that offset reaching the published
   bytes, not two fans in different thermal environments. §2.
2. **The temperature comparison the issue proposes cannot separate them, and
   the committed data says so rather than merely failing to.** One channel
   correlates with `CPU_TEMP` at 0.468 and the other at 0.507 — both weak, the
   gap inside the noise. `GPU_TEMP` moves three counts across the whole sweep,
   so it carries no signal to separate anything, and the tool refuses to print
   a coefficient against it rather than printing one. §3.
3. **The tachometer evidence is a real lead about the vendor's code and does
   not name a fan.** `GetEcGpuFanRpm` reads `0x046C`/`0x046B`; the EC writes
   `0x046C`/`0x046D` together. `0x046B` never moves in any committed capture.
   §4.

So: **`L` versus `R` versus CPU/GPU remains open**, and §6 names the live
observation that would decide it. This is the second of the two outcomes
issue #247 allows, taken because the first is not available from the committed
inputs — not because the analysis was too narrow to find it. §5 is why the
wider route was tried and still does not name a fan.

## 1. A correction to the issue's premise, beside the claim

Issue #247 says the two named captures "hold the surrounding `0x0700`-`0x07FF`
page, so the two channels can be compared against `CPU_TEMP` and `GPU_TEMP` in
the same sweeps". **They do not.** `2026-09-18-profile-switch-0700-07ff.csv`
and `2026-09-23-power-mode-cycle-0700-07ff.csv` record `0x0700`-`0x07FF` and
nothing else: neither file carries a row of `0x043E` or `0x044F`
(`test_the_two_captures_the_issue_names_carry_no_temperature`).

The comparison is possible in a third capture the issue does not name,
`2026-09-18-profile-switch-0400-07ff.csv`, which carries `0x043E` beside both
duty bytes. It is run there, and §3 is its result. Stated as a correction
rather than absorbed silently, because the issue's route is only as good as
the captures it assumes.

## 2. The `0x14` is the EC's own constant

**The measurement.** `0x075B - 0x075C`, taken at the instants the capture
records *both* bytes:

| capture | paired samples | `0x00` | `0x14` | any other value |
|---|---|---|---|---|
| `2026-09-18-profile-switch-0700-07ff.csv` | 449 | 347 | 102 | none |
| `2026-09-23-power-mode-cycle-0700-07ff.csv` | 297 | 297 | — | none |
| `2026-09-18-profile-switch-0400-07ff.csv` | 193 | 142 | 51 | none |

The claim is the *third column from the right*: no capture shows a value
outside `{0x00, 0x14}`. The power-mode sweep shows only `0x00` throughout,
which is a fact about that sweep and not a counterexample — the suite asserts
the subset and separately asserts that both sweeps which *do* carry a mode
switch show both values, because a subset test alone would also be satisfied
by a tool that reported `0x00` every time.

**Why that is the firmware's constant.** `0x8DE0` keeps the two channels in
`0x1804` and `0x1809` and publishes them. **Three** arms converge on the one
store at `0x8EFF`, and the difference between the published bytes is the
output of the comparison that chooses between them:

```
8EF0     90 18 04 mov      DPTR, #0x1804
8EF3     e0 - -   movx     A, @DPTR
8EF4     24 ec -  add      A, #0xec        ; 0xEC == -0x14
8EF6     80 07 -  sjmp     0x8eff
8EF8     90 18 04 mov      DPTR, #0x1804
8EFB     e0 - -   movx     A, @DPTR
8EFC     80 01 -  sjmp     0x8eff
8EFE     e4 - -   clr      A
8EFF     90 18 09 mov      DPTR, #0x1809
8F02     f0 - -   movx     @DPTR, A
```

(`ec/decompiled/bank0/8DE0.asm`, listing offsets.) `0x8EF0` subtracts the
constant, `0xEC` being `-0x14`, and it is the arm the `0x14` samples come
from.

**The `0x00` samples are the `0x8EF8` copy, not the `0x8EFE` clear.** An
earlier version of this write-up read the middle arm as absent and put the
`0x00` samples on `0x8EFE` instead, on the strength of the same routine's
committed annotation in `ec/annotations/ghidra-functions.csv` — "writes
`0x1809` as either 0 or `0x1804-0x14`", a two-valued summary that omits the
copy arm. The listing settles it the other way:

- `0x8EFE` clears `A`, so that arm publishes `0x1809 = 0x00`, and `0x8F0F`
  then copies that byte into the published `0x075C`. A clear at `0x8EFE`
  would therefore show up at `0x075C` as `0x00` — **and no row of `0x075C`
  is zero in any capture**, spanning 0x32-0xC7, 0x3C-0x84 and 0x33-0xC8.
- The `0x00` differences are equal-and-**non-zero** pairs: every one of the
  347, 297 and 142 equal-difference samples has `0x075B == 0x075C != 0`. That
  is the signature of `0x8EF8`, which copies `0x1804` through unchanged and
  so makes the two channels equal by construction.

So the difference is still firmware branch output — that part of the claim
stands — but it is the choice between the `0x8EF0` bias and the `0x8EF8`
copy, and `0x8EFE` is the third branch, the one the captures do not show.
A third branch that would publish a zero nobody recorded is a fact about the
branch, not evidence that the zero was never taken; it does not narrow the
reading of the two values that were, and the fan identification stays where
§6 leaves it.

**One correction worth making, because the plan this issue came from had it
wrong.** There are two `0x14` literals in `0x8DE0`, and they do different
things. `mov A, #0x14` at `8E01` stores into **`0x0672`** — a separate arming
byte that diverts the routine to `0xBEB4` — and is not the source of the
observed difference. The source is `add A, #0xec` at `8EF4` above. Both are in
the same routine, which is why the error is an easy one to make; the listing is
what settles it.

**What this does and does not establish.** It establishes that the `0x14` is
the EC's constant rather than a thermal difference — a difference that is
*always* exactly a firmware literal is that literal reaching the output. It
does **not** establish which physical fan either byte is, and it does not
establish that the two bytes are driven by the two fans' speeds: `0x075B` and
`0x075C` have other writers besides this path (`registers.yaml` records
`0x87C5`, `0x89E0`, `0xBB29` for the first and `0x87D5`, `0x8F0A`, `0x8F11`
for the second), so the observed difference is the net of whichever write ran
last, not a direct read of `0x1804` and `0x1809`.

**The method, because it is load-bearing.** The two series are paired at the
timestamps they **share**, not at the union of theirs. The EC publishes the two
bytes microseconds apart, so a union pairing reads one fresh value beside the
other's stale one: on the profile sweep it manufactures **nine** distinct
differences where the shared-timestamp pairing finds two, including `+1` and
`-1` that no instant ever held. `test_union_pairing_manufactures_differences`
holds that from the wrong side, so a reader who changed the method would see
the suite go red rather than find a tool that still appeared to work.

The bytes are read as carry-forward step functions throughout — a capture
records *changes only*, so a byte's value between two rows is inferred rather
than observed, and a change that happened and reverted between two rows leaves
no row at all. That is a named blind spot of every figure here, not a caveat
attached once at the top.

## 3. The temperature route cannot separate them

Run on `2026-09-18-profile-switch-0400-07ff.csv`, the one committed capture
carrying a temperature register beside both duty bytes. Each temperature step
is the anchor and each duty series is read forward to it, so every pair is
(duty, temperature) coexisting:

| duty byte | against | result |
|---|---|---|
| `0x075B` | `CPU_TEMP` (`0x043E`) | r = **+0.468** over 179 paired samples |
| `0x075C` | `CPU_TEMP` (`0x043E`) | r = **+0.507** over 179 paired samples |
| `0x075B` | `GPU_TEMP` (`0x044F`) | no coefficient — `GPU_TEMP` spans 2 counts (51-53) |
| `0x075C` | `GPU_TEMP` (`0x044F`) | no coefficient — same |

**The gap is inside the noise.** 0.468 against 0.507 over 179 samples is a
difference of 0.04, and the sampling uncertainty of a coefficient at that
sample size is of the same order — the two bytes are not distinguishable by
this measurement. Both are also *weak* correlations in absolute terms: duty
follows temperature because the EC's fan curve is driven by temperature, and
at r ≈ 0.5 neither byte is a clean readout of anything.

**`GPU_TEMP` is not measured, and the tool says so rather than printing a
number.** It records four rows spanning `0x33`-`0x35` across the whole sweep.
A Pearson coefficient against a register that moved two counts describes the
shape of a handful of coincidental samples, not a relationship — which is
precisely the overstatement issue #247 was opened to avoid. `MIN_TEMP_RANGE`
is `8`, chosen to sit between the two observed spans (`GPU_TEMP` 2,
`CPU_TEMP` 33), and it is a judgement about this data rather than a derived
statistical threshold: a reader who disagrees with it can read the coefficient
the tool declines to print and judge for themselves. The suite holds the floor
from both sides, because a test that reads the constant back from the tool
passes unchanged when someone lowers it.

**What follows.** The L/R-versus-CPU/GPU split issue #247 hoped to recover this
way is not recoverable this way. That is a stronger statement than "the
correlation was inconclusive", and it is the one the committed data supports.

## 4. The tachometer pair — a lead about the vendor's code, not a naming

Issue #247 reads the naming disagreement as propagating: `GetEcCpuFanRpm` /
`GetEcGpuFanRpm` read the tachometers CPU and GPU "by the same convention
that contradicts ECSpec's L/R". **The register file does not say that.**
`ECSpec.cs` names them `ADDR_EC_MAIN_FAN_RPM_BYTE1`/`BYTE2` (`0x0464`/
`0x0465`) and `ADDR_EC_SECOND_FAN_RPM_BYTE1`/`BYTE2` (`0x046C`/`0x046B`) —
*first* and *second*, an ordinal with no left/right and no CPU/GPU in it, and
byte-identical across `v3.1.6.0`, `v3.1.39.0` and `v3.9.18.0`. The L/R naming
is the duty bytes'; CPU/GPU is `FanInfo`'s method names. One codebase, two
naming conventions, and the tachs are on the ordinal one.

**But the two readings of the second tachometer disagree, and the EC settles
it against the service.** `store_r6_r7_to_046c_046d` writes one 16-bit value
across `0x046C` and `0x046D` — four instructions, `mov DPTR,#0x46c / mov
A,R6 / movx / inc DPTR / mov A,R7 / movx` (`ec/decompiled/bank0/E024.asm`) —
and `be16_046c_046d_minus_100` reads the same two back as one value,
subtracting 100 from `0x046D` and carrying into `0x046C`
(`ec/decompiled/bank0/BD6B.asm`). The EC's own cluster table puts
`0x046C`/`0x046D` together (`main-ec-138`, six routines) and puts `0x046B` in a
different one entirely — `main-ec-004`, alongside `0x046A`/`0x046E`/`0x046F`,
synced from `0x086B-0x086E` by `gate_06e6_442_then_sync_046a_from_086b`
(`ec/annotations/xdata-clusters.csv`).

**The committed captures agree with the EC.** `0x046B` has **no row at all** in
any of the three captures, so `GetEcGpuFanRpm`'s 1132/1131 read cannot be
assembled from committed evidence at all — one live byte beside one dead one
would be a measurement of neither, and the tool refuses it by name. Stated
per-capture rather than as "the byte is absent", per `CLAUDE.md`'s rule about
a scan that finds nothing.

Across the committed `0x0000-0x07FF` sweep
(`2026-09-18-ac-plugin-sweep-summary.csv` — the only committed record of how
often a byte moved, since the row log behind it is not committed):

| pair | change counts | same order of magnitude? |
|---|---|---|
| `0x0464`/`0x0465` (first tachometer) | 126 / 540 | yes — and this pair is not in dispute |
| `0x046C`/`0x046B` (as the service reads it) | 154 / **1** | no |
| `0x046C`/`0x046D` (as the EC writes it) | 154 / 536 | yes |

A 16-bit value from a spinning fan has a high byte that moves on the low
byte's carry, so the two change counts sit in the same order of magnitude; a
byte that moved **once** beside one that moved 154 is not the low half of what
its partner is. The test's factor of 8 is calibrated from the *undisputed*
first pair — 126 against 540 is a ratio of 4.3, so a rounder bound of 4 would
have excluded a pair the EC's own code supports, which is how a shape test
becomes worse than none.

**And the correlation, which is the reason this stays a lead.** Reconstructing
both tachometer readings as the big-endian 16-bit values the vendor's reads
assemble, over the **210** samples at which all four bytes are live,
`0x0464`/`0x0465` and `0x046C`/`0x046D` correlate at **r = 0.982**, agreeing
on a value in 4 of 210. Two independently-loaded fans do not track each other
that closely.

That number is **not** "the two fans are the same fan". It is what one
committed capture shows, over a carry-forward reconstruction with the blind
spot named in §2, and 4-of-210 agreement on the actual value shows the two
series are not the same series either. Both readings are near-perfectly
*proportional* and rarely *equal*, which is what a shared underlying signal
resampled through two different scalings would look like — and that is
precisely as far as the committed inputs go. (The sample count is 210 and not
the 36 an own-step-set pairing gives: comparing two series on *their own* step
sets measures how often each pair's halves happened to move together rather
than how the two values relate, and the suite holds the difference.)

**What this would take to close.** Either an EC-side read of how the second
tachometer's value is assembled and scaled, or a live tach read. Neither is in
this PR; it is recorded as a lead with its evidence and its own caveats, and it
is arguably its own issue.

## 5. Why the wider route was tried and still does not name a fan

Issue #247 offers two acceptable outcomes: a citation-backed answer, or an
explicit statement that the committed inputs cannot separate them. The first
is not available. §2 settles the `0x14`; §3 shows the temperature route
returns no separation; §4 shows the tachometer evidence is about the vendor's
pairing rather than about which fan is where. The honest result is the second,
and the narrow reading — record what the committed inputs support, name the
hardware step that would decide it — is what §6 gives.

## 6. The observation that would decide it

A human at the physical machine, and nothing in this repository can substitute
for it:

> Hold or unplug **one** fan while the machine runs. Watch `0x075B` and
> `0x075C`, and `0x0464`/`0x0465` against `0x046C`/`0x046D`. Whichever duty
> byte stops moving is that fan's. Repeat with the other fan.
>
> The step that matters is the second: it separates `0x046B` from `0x046D` as
> well, and §4 says the service reads the wrong one.

Then: the byte that moved with fan 1 is the L/R-or-CPU/GPU answer, and the
tachometer pair that moved with it settles which of ECSpec's readings is
right. Until that runs, the entry stays `present-untested` and the disagreement
stays visible — §7.

## 7. What this changes in `registers.yaml`

Both entries keep `status: present-untested`, and **neither `static_refs` nor
`sources:` moves**: this work adds no EC-side site, and the `3` stays a
direct-`MOV DPTR` count. A name is not a behaviour, and nothing here tests the
EC acting on these bytes. What changed is one claim in each note:

- the `MAIN_FAN_L_DUTY` note's "Live, both bytes move with the fan" paragraph
  now attributes the `0x14` to the `0x8DE0` branch that produces it, with the
  correction that the `0x14` literal at `8E01` arms `0x0672` and is not the
  source — `add A, #0xec` at `8EF4` is;
- its "The name is not settled" paragraph gains the temperature result: the
  comparison the issue proposed returns 0.468 against 0.507 on the one capture
  carrying a temperature, and `GPU_TEMP` spans two counts, so **the committed
  captures cannot decide it** — with the correction that the two captures the
  issue names carry no temperature register at all;
- the `MAIN_FAN_R_DUTY` note gains the same result, since it says everything
  said about the pair holds there, plus the tachometer pairing doubt, which is
  about its own `GetEcGpuFanRpm` neighbour rather than about the byte.

The `0x14` reading that was already in the note is not retracted — it was
recorded as "the offset the `0x8DE0` branch above produces", which is what §2
confirms. What §2 adds is the exclusion of the alternative reading (two fans in
different thermal environments), which the note had left open by not saying
which explanation it favoured. Nothing is corrected *over*; the PR #237 text
stays visible beside this.

## 8. Reproducing every figure

```sh
python3 ec/tools/fan_pair_correlation.py            # all three parts
python3 ec/tools/fan_pair_correlation.py --self-test
bash tools/run-tests.sh ec/tools                    # the suite
```

The write-up's figures are that tool's output against the three committed
captures and the committed sweep summary. Two of them are held as relations
rather than as thresholds, deliberately: the "no third value" claim is a subset
over three named captures, and the "does not separate" claim is a comparison
between two coefficients. Neither is a floor a future capture has to clear, and
neither is a count of the tree — `docs/findings/no-append-logs.md` is what that
rule is for.
