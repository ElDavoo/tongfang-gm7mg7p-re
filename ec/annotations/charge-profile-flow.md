# Charge-profile control flow (EC firmware `GMxMGxx_11.800`)

Traced with `ec/tools/make_bank_image.py` + `r2 -a 8051` (bank 0, file offset
`0x08000`). All addresses below are runtime addresses in that bank image.

## 1. Manual-control gate — `0xB12C`

Runs on some EC event tick. If `AP_OEM` (`0x0741`) bit 0
(`ENABLE_MANUAL_CTRL`) is clear, the profile is force-reset to High Capacity:

```
0xb12c   mov  dptr,#0x078e   ; FAN_CTRL |= CHARGING_PROFILE (0x08)
0xb12f   movx a,@dptr
0xb130   orl  a,#0x08
0xb132   movx @dptr,a
0xb133   mov  dptr,#0x0741   ; AP_OEM
0xb136   movx a,@dptr
0xb137   jb   acc.0,0xb141   ; if ENABLE_MANUAL_CTRL set, skip reset
0xb13a   mov  dptr,#0x07a6   ; OEM_4 (charging profile)
0xb13d   movx a,@dptr
0xb13e   anl  a,#0xcf        ; clear bits 4-5 -> High Capacity (0x00)
0xb140   movx @dptr,a
0xb141   ...
```

`uniwill-laptop` sets `ENABLE_MANUAL_CTRL` in `uniwill_ec_init()` and clears it
in `uniwill_shutdown()` — so this reset fires on every shutdown/module unload
by design. **The per-boot systemd unit that reapplies the profile is required
behaviour, not a workaround for a bug.**

## 2. Profile → current-limit selection — `0xB2B0`..`0xB35E`

Two near-identical blocks (`0xB2E2` and `0xB330`) read `OEM_4` and derive a
value in `R3` used later as a current limit multiplier/cap:

```
0xb2e2   mov  dptr,#0x07a6
0xb2e5   movx a,@dptr
0xb2e6   anl  a,#0x30        ; CHARGING_PROFILE_MASK, bits 4-5
0xb2e8   mov  r7,a
0xb2e9   cjne r7,#0x20,0xb2f0   ; profile == STATIONARY (0x20)?
0xb2ec   mov  r3,#0xc8          ;   yes -> R3 = 200
0xb2ee   sjmp 0xb35e
0xb2f0   ...                     ;   no -> falls through to more comparisons
...
0xb330   mov  dptr,#0x07a6
0xb333   movx a,@dptr
0xb334   anl  a,#0x30
0xb336   mov  r7,a
0xb337   cjne r7,#0x10,0xb33e   ; profile == BALANCED (0x10)?
0xb33a   mov  r3,#0x64          ;   yes -> R3 = 100
```

`R3` then feeds a multiply against a second EC value at `0xA47`
(`0xb35e: mov a,r3 / mov r7,a / mov dptr,#0x0a47 / ... / lcall 0x707d`), and
the result is written to `0x0522`/`0x0523` — **not** to any register the
`0x07B9`/`0x07D0` pair touches. This is a *separate* current-limiting path
from the numeric threshold Windows uses (see `docs/findings.md`).

Net effect confirmed on live hardware
(`evidence/battery-traces/2026-09-09-profiles.csv`): the profile changes how
fast charge current tapers as capacity approaches 100%, not a hard stop.
Both Trickle and Long_Life still show >1 A flowing at 95%.

## 3. What is NOT here

No code path in this function (or found so far anywhere in the image via
direct-DPTR scan) compares against `0x07B9` or reads/writes `0x07D0`. Given
the retraction in `docs/findings.md`, treat that as "not found by this
method" rather than "does not exist".

The 254 call sites referencing `0x07D0` — the step this section used to
point at as next — are now enumerated in [`ec-0x07d0-sites.md`](ec-0x07d0-sites.md).
All of them are in the `ITE8850-PD` image, none in the EC image, so they do
not add a `0x07D0` path to the flow traced above; the EC-side question is
unchanged and still needs the paired-write experiment in `docs/findings.md`
§5.
