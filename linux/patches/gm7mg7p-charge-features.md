# The charge features this board can claim: a mode that is a voltage floor, and a limit with no EC consumer (GM7MG7P / GM5MG7Y)

Preparation for the upstream `Wer-Wolf/uniwill-laptop` contribution tracked by
issue #10, and the note that corrects the comment in
`uniwill-laptop-force_charge_limit.patch` beside it (see
[`README.md`](README.md) for that correction, which keeps the original wording
visible).
Nothing here is opened in another repository: the PR description in §4 is a
draft to be lifted by a human, per `CLAUDE.md`.

**There is no descriptor draft in this repository.** No file here contains a
`device_descriptor` struct, a DMI match row for this board, or a feature-bit
list — `docs/hardware-identity.md` holds the DMI *facts* and says outright that
the entry does not exist yet. So this is the *notes* half of the question: what
the descriptor should and should not claim, and the wording the upstream PR
description will carry once someone writes the patch proper.

*Corrected 2026-09-27, in place, with the paragraph above kept visible because
it is what was true when this file was written.* Every clause of it is now
false. Issue #10's deliverable exists: [`gm7mg7p-dmi-entry/`](gm7mg7p-dmi-entry/README.md)
holds a `uniwill_device_descriptor`, a `uniwill_dmi_table` row, the feature-bit
list, and the PR description this file was the notes for. The descriptor claims
**eight** bits, of which `UNIWILL_FEATURE_BATTERY_CHARGE_MODES` is one; the
charge rows in §1 below are carried into
[`feature-map.csv`](gm7mg7p-dmi-entry/feature-map.csv) with the same verdicts
and the same reasons, and `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` is still not
claimed. `docs/hardware-identity.md` is unchanged and its "not in
`uniwill-laptop`'s DMI match table" sentence is still exactly true — the entry
is *prepared*, not upstream. The write-up is
[`dmi-descriptor-evidence.md`](../../docs/findings/dmi-descriptor-evidence.md).

## 1. What the descriptor should claim

| feature bit | EC register | claim for this board | where the evidence is |
|---|---|---|---|
| `UNIWILL_FEATURE_BATTERY_CHARGE_MODES` (`charge_types`) | `0x07A6` bits 4-5 | **claim it**, and describe it as §3 describes it — a floor on a per-cell voltage derating, not a percentage cap | [`charge-target-derating.md`](../../ec/annotations/charge-target-derating.md) §1; `docs/findings.md` §4h, §4k, §4l |
| `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` (`charge_control_end_threshold`) | `0x07B9`, paired `0x07D0` | **do not claim it** — no EC consumer found by any method, and the vendor service never writes it | `docs/findings.md` §4c, §4f, §4k; §2 below |
| *(no bit — the charge target)* | `0x0522` | **not reachable from the host**, so it is not a feature bit at all; it is internal to the EC | `docs/findings.md` §4m |

Both charge rows already exist in
[`registers.yaml`](../../ec/annotations/registers.yaml) at their current
statuses — `0x07A6` `confirmed-working-partially`, `0x07B9`
`unknown-not-absent`. No status moves on the strength of this note, because it
adds no new evidence: it restates, in the shape the upstream patch needs, what
those two rows and `docs/findings.md` already record.

## 2. Why `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` is not claimed

Four independent lines, each re-runnable from the repository root. None of them
is "the register does not exist", and the difference matters — see the
calibration in §5.

**a. The static scan finds nothing, by a method with a documented blind
spot.** `scan_refs.py` prints its own caveat directly above the result, and
that caveat is the finding:

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07A6 0x07B9
This dump holds two 8051 programs; ec= counts sites in the EC firmware
(common area + CODE banks), pd= sites in the separate ITE8850-PD image,
whose XDATA map is unrelated. A pd-only count is not EC-side evidence.
A zero means 'not found by this scan', never 'absent' -- see the
indirect-addressing blind spot in docs/findings.md.

0x07A6  refs=7     ec=7     pd=0     referenced   in_data_region=0   0x07A6
0x07B9  refs=0     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x07B9
```

The last line's own label is the trap: the tool prints `ABSENT` in its status
column and prints the correction two lines above it. Quote both, or neither.
`0x07B9` is the one address in the tree flagged as a *confirmed* instance of
this blind spot — Windows demonstrably writes it and the scan cannot find how —
and the same scan correctly predicted the status of 20 registers with
independently confirmed live behaviour, of which 14 are re-derivable from
committed files (`docs/findings.md` §4d, and the correction it carries in
place). So this line is evidence about the method's reach, not about the
hardware.

**b. The partner byte is not the EC's to read either.** The other half of the
vendor's UP/DOWN pair:

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x07D0
0x07D0  refs=254   ec=0     pd=254   referenced in the PD image ONLY, not by the EC   in_data_region=0   0x07D0
```

254 references is the busiest address the scan found in the whole `0x0780`-`0x07FF`
range, and every one of them is in the separate ITE8850-PD image — a different
8051 program with an unrelated XDATA map. All 254 sites are enumerated in
[`ec-0x07d0-sites.md`](../../ec/annotations/ec-0x07d0-sites.md): 229 read, 15
write, 2 increment in place, the value multiplied against structure strides to
index arrays. That is a PD-firmware index/state variable. The EC firmware
references `0x07D0` zero times by this method.

**c. The vendor service, decrypted, has no caller for the write.** Control
Center Service 3.1.39.0 decompiles in full; `BatteryProtection2` holds the two
methods that would write the pair, and they are private with no caller anywhere
in the tree:

```console
$ grep -rn "SetBatteryChargingLimit_Up" windows/decompiled/v3.1.39.0/ --include=*.cs
windows/decompiled/v3.1.39.0/GCUService/GCUService.MySystem/BatteryProtection2.cs:322:	private void SetBatteryChargingLimit_Up(int limit)

$ grep -n 0x07B9 windows/decompiled/v3.1.39.0/ec-callsites.csv
33:GCUService.MySystem/BatteryProtection2.cs,327,GCUService.MySystem.BatteryProtection2,SetBatteryChargingLimit_Up,read,0x07B9,literal,1977,ref Data
34:GCUService.MySystem/BatteryProtection2.cs,329,GCUService.MySystem.BatteryProtection2,SetBatteryChargingLimit_Up,write,0x07B9,literal,1977,b2
35:GCUService.MySystem/BatteryProtection2.cs,338,GCUService.MySystem.BatteryProtection2,ReadBatteryChargingLimit_Up,read,0x07B9,literal,1977,ref Data
270:MyControlCenter/MyFanManager_QC.cs,1742,MyControlCenter.MyFanManager_QC,SetBatteryChargingLimit,read,0x07B9,literal,1977,ref Data
271:MyControlCenter/MyFanManager_QC.cs,1744,MyControlCenter.MyFanManager_QC,SetBatteryChargingLimit,write,0x07B9,literal,1977,b2
272:MyControlCenter/MyFanManager_QC.cs,1753,MyControlCenter.MyFanManager_QC,ReadBatteryChargingLimit,read,0x07B9,literal,1977,ref Data
```

One hit for the declaration and none for a call. The only other writer in the
service is `MyFanManager_QC.SetBatteryChargingLimit`, and that class is never
instantiated in this build: `MyFanCtrl` picks `MyFanManager` or a
`MyFanManager_RamFan1p5*` variant. `docs/findings.md` §4k.

**d. The pair was written live, in five phases over four distinct
value-pairs, and charging never stopped.** The experiment this line stands on
is `docs/findings.md` §4f (2026-09-17,
`evidence/battery-traces/2026-09-17-limit-pair.csv`): byte writes
at physical `0xFE4107B9`/`0xFE4107D0` — the address Windows' `ECRW` lands on,
so not a Linux-access-path artefact — as 60, 60 with bit 7, 95 armed from 93%,
and 60/55 armed at 56% under each of the three `0x07A6` profiles and then held
untouched from 72% through 91%. The first attempt wrote `0x07B9` alone, with
`0x07D0` left at `0x00`; the 72%→91% hold re-writes the same `0x3C`/`0x37`
pair as the profile phase rather than a further value-pair. Every write read
back correctly and stayed put. Current never stopped, never dropped below the
normal taper, and `status` never left `Charging`.

**What this does not establish, and what it does.** It does not show the EC
ignores the pair in general: the values Windows actually writes are still
unknown for this service version, and the write may be gated on something else
the service also does. It also does not reopen the 2021 Windows screenshot
(`evidence/screenshots/2021-11-27-batteryinfoview-windows.png`, §4i), which is
still the only evidence that a cap of some kind was ever enforced on this
machine. The conclusion drawn from all four lines is the modest one upstream
needs: **no EC consumer for `0x07B9` is found by any method, and the one
interface that would consume it has no caller.** A threshold that silently does
nothing is worse than an absent feature, because a user who sets it gets no
signal that it was ignored. HydroControl reached the same conclusion for the
same reason on a sibling board and dropped
`UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` from their descriptor
([`docs/related-projects.md`](../../docs/related-projects.md)).

The masking upstream's `force=1` already does is therefore *right* here, and it
is a driver policy choice rather than evidence about the hardware
(`docs/findings.md` §4c, re-graded point 3). It is not "not a loss" for the
reason this repository once gave, which is corrected in §5.

## 3. How `charge_types` actually behaves

`0x07A6` bits 4-5 is a real EC input with a decoded, non-trivial effect. The
routine is `charge_target_update` at bank 0 `0xB158`-`0xB38D`, decoded in
[`charge-target-derating.md`](../../ec/annotations/charge-target-derating.md)
§1, and it sets the charger's constant-voltage target:

```
target = pack's requested ChargingVoltage (0x030E) - derating_mV_per_cell * cell_count
```

**The profile is a floor on the derating, not a setting of it.** Stationary
guarantees at least 200 mV/cell below the pack's request, Balanced at least
100, High capacity 0. Beyond that floor the EC derates by age, measured two
ways — cycle count, and a temperature-weighted count of hours spent above
4.1 V/cell — and the age tier wins whenever it is higher:

| derating (mV/cell) | age trigger | profile floor at this tier |
|---|---|---|
| 250 | `> 18144` stress-hours, or `>= 550` cycles | — |
| 200 | `> 14808`, or `>= 450` cycles | **Stationary** |
| 150 | `> 11448`, or `>= 350` cycles | — |
| 100 | `> 8136`, or `>= 250` cycles | **Balanced** |
| 50 | `> 4800`, or `>= 150` cycles | — |
| 0 | otherwise | High capacity |

Two consequences that the percentage reading gets wrong:

- **The driver's preset names are the wrong way round for intuition, but the
  bit values are not a percentage.** `Standard` → `00`, `Long_Life` → `01`,
  `Trickle` → `10` on bits 4-5. A user selecting `Trickle` gets *at most*
  4.15 V/cell. That is a voltage ceiling expressed through a derating of the
  pack's own 4.35 V/cell request; it is not "80%", and there is no percentage
  anywhere in the EC code that computes it.
- **Age overtakes the profile.** On a pack past the 250 mV/cell tier, no
  profile value changes anything. On *this* pack that is the case: 450 cycles
  and a 16400 mV target against a 17400 mV request is exactly 4 × 250 mV/cell,
  the top tier, which is above both profile floors. The 450 cycles are what
  put it at the 200 tier, not the 250 one — that needs 550 — so the trigger for
  the top tier must be the stress-hours counter, which the host cannot read
  (see §5). Confirmed live and then again under High capacity (`0x07A6`=0x08)
  on 2026-09-21: `0x0522` held at
  16400 mV throughout a full CV charge run, and the measured pack voltage
  plateaued at 16466 mV under Trickle, `Long_Life` and `Standard` alike in the
  2026-09-09 trace
  ([`charge-target-derating.md`](../../ec/annotations/charge-target-derating.md)
  §2; `evidence/battery-traces/2026-09-09-profiles.csv`, and
  `evidence/battery-traces/2026-09-21-0522-follow.csv` for the 09-21 run).

The earlier reading of these branches — that the profile "selects a current
taper" — was wrong and is retracted in place in
[`charge-profile-flow.md`](../../ec/annotations/charge-profile-flow.md) §2.
`R3` is not a current-limit multiplier; it is the mV/cell derating, and
`[0x0A47]` is the cell count, not a second EC value.

## 4. Draft upstream PR description

Drafted to be lifted verbatim by whoever submits. Every sentence traces to a
file already committed here; the citations are left in so a reviewer can check
each one, and can be stripped when the text is lifted into the PR body.

> **Charge features for the GM7MG7P / GM5MG7Y descriptor**
>
> This board gets `UNIWILL_FEATURE_BATTERY_CHARGE_MODES` (`charge_types`, EC
> `0x07A6` bits 4-5) and deliberately does **not** get
> `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` (`charge_control_end_threshold`, EC
> `0x07B9`).
>
> `charge_types` is a real EC control here, and it is worth being precise about
> what it does, because its three presets do not mean what their names suggest.
> The preset selects a **floor on a per-cell charge-voltage derating**, not a
> percentage of capacity. The EC computes a constant-voltage target as
> `pack's requested ChargingVoltage - derating × cell_count`; `Standard` sets a
> floor of 0 mV/cell, `Long_Life` 100 mV/cell, `Trickle` 200 mV/cell. Cycle
> count and a temperature-weighted count of hours spent above 4.1 V/cell can
> push the derating higher, and when they do, no preset changes the target. On
> an aged pack — including this machine's, at 450 cycles and the top 250
> mV/cell tier, which here comes from the stress-hours counter rather than the
> cycle count — the profile makes no observable difference at all. Selecting
> `Trickle` on a fresh pack would mean "at most 4.15 V/cell", not "80%".
>
> `charge_control_end_threshold` is not claimed because no EC consumer for
> `0x07B9` was found by any method, and the vendor service never writes it. The
> static scan finds zero direct references — a method with a documented
> indirect-addressing blind spot that this very address is the confirmed
> instance of, and which correctly predicted 20 other registers' live
> behaviour (14 of them re-derivable from this tree's committed files), so
> this is "not found by this method" and not "absent". The
> paired `0x07D0` register is referenced 254 times, all in the separate
> ITE8850-PD image rather than the EC firmware. In the decrypted Control Center
> Service 3.1.39.0, `BatteryProtection2.SetBatteryChargingLimit_Up/_Down` are
> private with no caller, and the only other writer in the service lives in a
> class that build never instantiates. And when the pair was written live at
> the physical address Windows' own `ECRW` path lands on — 60 alone, 60 with
> bit 7, 95 set from 93%, and 60/55 armed at 56% and left untouched from 72%
> through 91% — the 60 alone and the 60-with-bit-7 were written from above
> their caps, the 95 and the 60/55 from below, and only the 60/55 was repeated,
> under each of the three `0x07A6` profiles. Charging never stopped and
> current never dropped below the normal taper.
>
> One caution for anyone who revives the limit path later. The `0x07D0` byte
> is deliberately **not** described here as a resume-charging threshold, and
> the upstream code should not assume it is one. The DSDT's `T1WR` method
> stores a GPU power value in that byte (in 1/8 W units, mirrored into the
> NVIDIA platform-controller ACPI device), and the vendor constant naming it
> `BATTERY_CHARGE_LIMIT_DOWN` has exactly one writer in the service, which is
> the never-called method above. No caller of `T1WR 0x1173` was found by the
> method that searched for one. Which of those holds is not established, so a
> limit path that writes `0x07D0` should read it back first rather than assume
> a value it did not put there.
>
> The charge-voltage target itself (`0x0522`) is not offered as a feature: the
> EC recomputes it continuously and the host cannot hold it — a write is
> reclaimed within a single ~100 µs read.

## 5. Calibration

What each kind of claim in §4 rests on, stated so a maintainer can discount
accordingly.

**Static, and re-runnable from committed inputs:** everything in §2a-§2c. The
scan counts, the service source, and the callersite table are all regenerable
with the commands quoted, against files in this tree. The vendor method bodies
are real decompiled source, not a summary of one.

**A hand decode, and checked as one:** §3's arithmetic comes from
`charge_target_update`, decoded by hand with a linear 8051 decoder rather than
by Ghidra. `charge-target-derating.md` says so in its own first paragraph and
names Ghidra as the cross-check that should come first. `cells = 4`,
`derating = 250 mV/cell`, and *which* age trigger put the pack in that tier
are inferred from the decode plus the live target, not read from the counters —
450 cycles reach the 200 tier and the observed 1000 mV gap means 250, so the
trigger is `stress > 18144`; the stress counter (`0x09C9`) and cell count
(`0x0A47`) sit in EC RAM the host window does not map and read back `0xFF`.

**Live, and cited rather than re-observed:** every live figure here comes from a
CSV already under `evidence/battery-traces/`, cited by path. Nothing in this
change was run against the physical laptop, and no register was read back for
it.

**Not established, and deliberately not claimed anywhere above:**

- Whether the EC image reuses `0x07D0` at all. The 2026-09-23 census
  (`docs/findings.md` §4o) covers Windows and ACPI inputs, not the 8051
  program; the EC side stays with #34 and #25.
- Whether the host can *read* a threshold, as opposed to write one. The
  question was not tested, and `0x07B9` reading `0x00` throughout a Windows
  session is scoped to that session's events, not to "never written".
- Whether a 2021-era EC image enforced a percentage cap. The 2021 screenshot
  is one capture from a different tool, with a pack whose tier then is
  inferred. The voltage reading predicts 16.65 V against the screenshot's
  16.654 V, which is suggestive agreement, not proof.
- Whether the age counters survive an EC power cycle. Don't treat a reset as a
  way to undo the derating.

**One correction this note carries forward.** `docs/findings.md` §4c recorded,
as a reason the masked charge limit was "not a loss", that the threshold byte
is not even mapped in ACPI and that the `ECMG` field list steps over it. §4e
corrected that: the byte is inside the window `ECRW` writes to, just unnamed in
the field list, and Windows reaches it through the ACPI method that lands in
the same region. The masking is still correct — it is upstream's own
conservative policy for unvalidated boards — but it does not rest on that
signal, and a descriptor that claimed the limit on the strength of it would be
claiming a refuted argument. The patch in this directory carried that
overclaim in its commit comment; see [`README.md`](README.md) for the
correction beside the original wording.
