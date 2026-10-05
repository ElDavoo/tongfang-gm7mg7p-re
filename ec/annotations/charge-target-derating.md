# Charge-voltage target and its age derating (EC firmware `GMxMGxx_11.800`)

This is the routine that sets the charger's **constant-voltage target**. As of
2026-09-19 it is the best-supported explanation of the "charge cap"
question in `docs/findings.md` §4 (§4l there has the narrative). Decoded
with `ec/tools/disasm8051.py` (linear decode, bank 0 at file `0x08000`) and
`ec/tools/trace_xdata_refs.py`. Addresses are bank-0 runtime addresses
unless marked `common`. Nothing here was produced by Ghidra. It's a hand
reading, and per `ec/ghidra/README.md` it's the first function the Ghidra
output should be checked against.

## 1. What it computes

```c
/* bank0 0xB158 .. 0xB38D. No direct lcall/ljmp to 0xB158 was found
 * (searched common + banks 0/1 for 12 B1 58 / 02 B1 58); it is reached
 * indirectly -- a function-pointer table or a BL51 trampoline. Unresolved.
 *
 * The indirect path was traced 2026-09-27 (issue #89), and it is neither of
 * the two mechanisms guessed above: common 0x0DFE -> 0x0E55 -> the far-call
 * stub 0x157C -> bank0 0x8539 -> bank0 0x853F -> bank0 0xB12C, which branches
 * here. See docs/findings/charge-target-caller-chain.md and 3 below. The
 * direct-call census above still finds nothing, and still will. */
void charge_target_update(void)
{
    /* Keil C51 overlay locals/parameters, XDATA 0x0A47..0x0A51.
     * Stored big-endian by helper 0xBB90 / 0xBD54 (hi byte first). */
    u16 vbat     = be16(xram[0x0439], xram[0x0438]);  /* 0x0A48: pack voltage, mV   (0xB158) */
    u16 cycles   = be16(xram[0x04A7], xram[0x04A6]);  /* 0x0A4C: cycle count         (0xB167) */
    u8  cells    = (cfg_0xBC8D() == 0xC0) ? 4         /* 0x0A47                      (0xB176) */
                 : (cfg_0xBC8D() == 0x80) ? 3 : 2;
    u16 v_hi     = cells * 4100;                      /* 0x0A4A: 4.1 V/cell, via mul16 common 0x707D (0xB195) */

    if (!check_0xB112()) return;                      /* 0xB1AB */
    if (!(xram[0x0490] & 0x04)) return;               /* 0xB1B4 */
    u16 mfg_date = be16(... 0x0315/0x0314 ...);       /* 0x0A4E: SBS ManufactureDate (0xB1BE) */

    /* One pack batch gets a head start (0xB1F0): a pack made between
     * 2018-11-01 (0x4D61) and 2020-07-01 (0x50E1), SBS date encoding,
     * has its stress counter forced to 14809 -- just over the 200 mV tier. */
    if (0x4D61 <= mfg_date && mfg_date <= 0x50E1 && stress <= 0x39D8)
        stress = 0x39D9;

    /* Stress counter (0xB211..0xB283): a seconds counter (0x09C7), then a
     * minutes counter (0x09C8) that only advances if, at the minute
     * boundary, vbat > cells*4100 mV. Every 60 such minutes add a
     * temperature-weighted amount to `stress` (battery temp in dK from
     * 0x04A2/0x04A3, helper 0xBAE5):
     *   < 3030 dK (~29.9 C)  -> +1     (0xB253: clr c; subb #0x0BD6)
     *   <= 3130 dK (~39.9 C) -> +3     (0xB26B: setb c; subb #0x0C3A)
     *   >  3130 dK           -> +7
     * The increment only happens while stress < 65000: helper 0xBCF5 ->
     * common 0x70FA computes 65000 - stress - 1 and 0xB24B skips on borrow. */
    if (++sec_0x09C7 >= 60) {
        sec_0x09C7 = 0;
        if (vbat > v_hi && ++min_0x09C8 >= 60) {
            min_0x09C8 = 0;
            if (stress < 65000)                              /* 0xB241 */
                stress += (batt_temp_dK <  3030) ? 1
                        : (batt_temp_dK <= 3130) ? 3 : 7;    /* common 0x70E4: BE add */
        }
    }
    /* stress is u16 big-endian at XDATA 0x09C9/0x09CA */

    if (!(xram[0x0490] & 0x01)) return;               /* 0xB286 */

    u16 v_req = be16(xram[0x030F], xram[0x030E]);     /* 0x0A50: pack's requested ChargingVoltage */
    u8  mv_per_cell = 0;                               /* R3 */
    if (v_req >= 500) {                                /* 0xB2A1: ignore an absent/zero request */
        if      (stress > 18144 || cycles >= 550)                 mv_per_cell = 250; /* 0xB2B3, helper 0xBD8B */
        else if (stress > 14808 || cycles >= 450 || profile == STATIONARY) mv_per_cell = 200; /* 0xB2CD, 0xBD98, 0xB2E2 */
        else if (stress > 11448 || cycles >= 350)                 mv_per_cell = 150; /* 0xB2F0 */
        else if (stress >  8136 || cycles >= 250 || profile == BALANCED)   mv_per_cell = 100; /* 0xB312, 0xB330 */
        else if (stress >  4800 || cycles >= 150)                 mv_per_cell =  50; /* 0xB33E */
    }
    /* profile = xram[0x07A6] & 0x30: 0x20 STATIONARY, 0x10 BALANCED, 0x00 HIGH CAPACITY */

    u16 target = v_req - mv_per_cell * cells;          /* 0xB35E..0xB389, mul16 common 0x707D */
    xram[0x0522] = target & 0xFF;                      /* little-endian, as the host sees it */
    xram[0x0523] = target >> 8;
}
```

The helper thresholds, exactly as encoded (each helper is entered with
`setb c`, so the compare is "strictly greater than"):

| tier (mV/cell) | stress counter `0x09C9` | cycles `0x0A4C` | profile floor |
|---|---|---|---|
| 250 | `> 0x46E0` (18144), `0xBD8B` | `>= 0x0226` (550) | — |
| 200 | `> 0x39D8` (14808), `0xBD98` | `>= 0x01C2` (450) | Stationary |
| 150 | `> 0x2CB8` (11448) | `>= 0x015E` (350) | — |
| 100 | `> 0x1FC8` (8136) | `>= 0x00FA` (250) | Balanced |
| 50 | `> 0x12C0` (4800) | `>= 0x0096` (150) | — |
| 0 | otherwise | | High capacity |

So the **battery profile is a floor, not a setting**. Stationary guarantees
at least 200 mV/cell below the pack's requested voltage and Balanced at
least 100. Beyond that, the EC derates by age, measured both as cycle count
and as temperature-weighted hours spent above 4.1 V/cell. For scale, the
250 tier needs `stress > 18144`: about 18144 h at under 30 °C, 6048 h at
30–40 °C, or 2592 h above 40 °C, spent above 4.1 V/cell. For a machine
kept plugged in near full, that's months, not years.

## 2. Cross-check against the running machine (2026-09-19)

| quantity | where | live value | source |
|---|---|---|---|
| pack requested ChargingVoltage | `0x030E/0x030F` LE | `0x43F8` = **17400 mV** (4 × 4.35 V) | `ecrw.py dump 0x0300 0x20` |
| charge target | `0x0522/0x0523` LE | `0x4010` = **16400 mV** | same session, and §4g's 2026-09-18 reads |
| cycle count | `0x04A6/0x04A7` LE | `0x01C2` = 450 | `ecrw.py`, and §4g |
| measured pack voltage in CV | `0x0438` | pinned at 16466 mV from ~65% to 93% | `evidence/battery-traces/2026-09-19-windows-bios-defaults.csv`, `2026-09-18-windows-stationary.csv`, `2026-09-09-profiles.csv` |
| `0x0A47`, `0x0A4C`, `0x09C9` | — | read back `0xFF` | not readable: the host's `0xFE410000` window does not map `0x0800-0x0DFF`, the same unmapped-`0xFF` signature HydroControl records for `0x0980-0x098F` |

17400 − 16400 = 1000 mV. `cells` can only be 2, 3 or 4, and 1000 is a
whole tier value only for 4 × **250**. So on this pack the EC sits at the
**maximum** derating tier. Cycles are 450, below the 550 needed for that
tier, so the tier must come from `stress > 18144`. That is an inference
from the decode plus the live target; the counter itself can't be read (row
above).

What this predicts, and what was then observed:

- **No profile changes the target on this pack**, because 250 exceeds both
  floors. Observed: switching Stationary → High capacity in the CV phase at
  88% (2026-09-19 12:01, trace phase `cv88_switch_to_highcap`) left
  `0x0522` at 16400 and the current on its normal taper (884 → 748 mA over
  5 minutes, 16466 mV throughout). Profile cycling on 2026-09-18 (§4g) also
  left `0x0522` unmoved. The 2026-09-09 Linux traces show the same 16466 mV
  plateau under Trickle, Long_Life and Standard. Reconfirmed 2026-09-21
  (issue #91): a full CV charge run in **High capacity** (`0x07A6`=0x08,
  floor 0 mV/cell) held `0x0522` at 16400 throughout, so even the highest
  profile does not raise the target on this pack.
- **2021 should have looked different**, with a young pack at low tiers. With
  Stationary at the 200 floor the target would have been 17400 − 800 =
  16600 mV. Today the EC's reading sits 66 mV above its target (16466 vs
  16400), which predicts about 16.65 V at the plateau. The 2021 screenshot
  (`evidence/screenshots/2021-11-27-batteryinfoview-windows.png`, §4i)
  shows **16.654 V** while still charging at 86%. That agreement is
  suggestive, not proof: one screenshot, a different tool (BatteryInfoView),
  and a pack whose 2021 tier is inferred, not read.

## 3. What it does not say (open questions)

- **When it runs (resolved 2026-09-21, issue #91; chain and dispatch
  extended 2026-09-27, issue #89).** `0xB158` has no *direct* caller, but the
  path in is now found: the task-dispatch run at `0x8539` does `lcall 0xB12C`,
  and `0xB12C` falls through `0xB141` (`jb acc.1,0xB158` on `0x0490` bit 1)
  into `0xB158`. The same run also `lcall`s `0xE010` — a second `0x0522`
  writer that copies the pack's requested `0x030E` in first, before the
  derating overwrites it. So the target is recomputed inside the periodic task
  loop, not on a function-pointer/trampoline as this file previously guessed.
  The exact tick rate is not read from the image, but live it is effectively
  continuous: a host write to `0x0522` is reclaimed within a single ~100 µs
  read (`docs/findings.md` §4m). That also answers "can the host override
  the target": no — `0x0522` is host-read-only.

  **Correction (2026-09-27, issue #89).** This paragraph and `docs/findings.md`
  §4m both said *the slot at* `0x8539` *does* `lcall 0xB12C`. That address is
  off by one slot: `0x8539` is `12 E0 10`, `lcall 0xE010`, and `0xB12C` is
  called from `0x853F` (`12 B1 2C`) — the next entry of the same stride-3 run,
  which is `0x8518`–`0x8559`, 22 entries. The claim is otherwise unchanged and
  is not withdrawn: `0xE010` and `0xB12C` are both in the run and both are
  dispatched together, which is the part that mattered. See
  [`docs/findings/charge-target-caller-chain.md`](../../docs/findings/charge-target-caller-chain.md)
  for the full chain, the dispatch above it (a timer-0 overflow flag polled at
  `0x0C86`, which calls a divide-down scheduler at `0x0D7B` whose inline case
  table selects this chain at case `0x0A`), and the methods that found
  nothing. The rate is still not established and none is claimed.
- **Whether `stress` survives an EC reset — answered 2026-10-03, issue #90.
  It does not.** `0x09C9/0x09CA` is XDATA RAM, and the EC's reset path zeroes
  it. That was already half on record: `0xB141`'s else-branch, taken when
  `0x0490` bit 1 is clear, explicitly zeroes `0x09C7`–`0x09CA`, and
  `docs/findings/reset-vector-dptr-targets.md` (#559) decoded a boot-time clear
  sweeping `0x0100`–`0x0FFF`. Both are now closed against the committed image by
  `ec/tools/boot_xdata_sites.py`, which executes the reset vector and reports a
  per-address verdict: all four counters read `cleared`, and every direct
  `MOV DPTR` site for them is in `bank0` between `0xB149` and `0xBD9E`, inside
  `0xB12C`'s routine and its helpers — none in `common`, `bank1` or `pd-image`.
  **"Not found by this method" is the limit, not "absent":** indirect and
  DPTR-handed stores are not searched, and the seven parameterised "zero N
  bytes at DPTR" helpers `xdata-0440-readers.md` §7.5 names are the concrete
  unsearched population. Full answer, including the per-address site counts and
  what a second boot-path XDATA clearer (`0x0F75`) contributes, in
  [`docs/findings/charge-derating-counters-not-persisted.md`](../../docs/findings/charge-derating-counters-not-persisted.md).

  **The advice this replaces was right for the wrong reason, and the sharper
  form is stronger, not weaker.** The old text said "don't treat an EC reset as
  a way to undo the derating", on the reasoning that persistence was
  unestablished. What is established is that a full EC power loss *does* reset
  the counter, so the derating falls back to the cycle-count tier (450 cycles →
  200 mV/cell → 16600 mV). It then **climbs back** at +1/h below 30 °C, +3/h at
  30–40 °C and +7/h above, only while the pack is above 4.1 V/cell — so the
  250 mV tier at `stress > 18144` returns after roughly 2,592 h near 40 °C. The
  derating is not a latch a reset clears; it is a function of accumulated
  high-voltage time. The practical advice is unchanged and now has a reason: an
  EC reset is not a user-facing operation on this machine, and on one that
  offered it, the counter would be back where it started within months.
- **`cfg_0xBC8D`** (the source of the 0xC0/0x80 cell-count selector) was
  not decoded. "4 cells" is backed by the pack's own 15200 mV design voltage
  (4 × 3.8 V) and by the 1000 mV arithmetic above, not by that helper.
- **`check_0xB112`** was not decoded. Two of the `0x0490` gate bits now have
  their place in the sequence: bank1 `0xB841` rewrites `0x0490` as old AND
  `0xF9`, clearing bits 1 and 2, and then stores `0x0000` to the 16-bit word at
  `0x04AE`/`0x04AF`; bank1 `0xB8E1` masks with `0x9F`, clearing bits 5 and 6,
  and zeroes `0x04BE`/`0x04BF` the same way. Bit 1 is the gate this page's
  `charge_target_update` is reached on (`0xB141`/`0xB145` in `bank0`), so the
  `0x04AE` word is zeroed on the same gate; bank1 `0xBFBB` increments that word
  once per `0x3C` ticks of the byte at `0x04AD`. What sets either bit is still
  not decoded. `0x0490` reads `0x0F` live, so bits 0 and 2 are both set — and so
  is bit 1, with bit 5 clear.
  [`docs/findings/xdata-04a0-04ae-04be-words.md`](../../docs/findings/xdata-04a0-04ae-04be-words.md)
  has the byte-level chain and the two `0x04A0` bytes' corrected provenance.
- **Consequence for "battery health".** The fuel gauge learns full-charge
  capacity from charges that now end at 4.1 V/cell. The 2000 mAh
  `charge_full` (§1, "~49% health") is therefore capacity to 4.1 V/cell,
  not to the pack's rated 4.35 V/cell. How much more a full-voltage charge
  would hold is unmeasured. Measuring it would mean charging above this
  target, which the EC prevents.

## 4. Related

- `charge-profile-flow.md` §2 traced the `0xB2E2`/`0xB330` profile branches
  of this same routine. It read R3 as a "current limit multiplier" and could
  not say what `0x0522` was. This file replaces that reading.
- `docs/related-projects.md`: `mech-forza-control` names `0x0522`
  `ADDR_BATTERY_CHARGE_TARGET` and `0x030E` `ADDR_BATTERY_BASE_VOLTAGE` on a
  newer Uniwill EC. Its README reports the same ~16.4 V ceiling on "most
  users'" machines ("below the charge limit voltage by 1V").
- `registers.yaml` entries for `0x0522`, `0x030E`, `0x04A6`.
