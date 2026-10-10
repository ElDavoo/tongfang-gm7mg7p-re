# Charge-limit registers are not found to move in the AC plug-in sweep

Resolving the unresolved clause in `docs/findings/sweep-summary-schema.md`.

## The registers and their status

The six registers that the EC firmware literature and the BIOS identify as charge-limit are:

- `0x07B9` `CHARGE_CTRL` — numeric threshold (status: `unknown-not-absent`)
- `0x07D0` `DBD1` — ECSpec: `BATTERY_CHARGE_LIMIT_DOWN` (status: `unknown-not-absent-DO-NOT-WRITE-BLIND`)
- `0x07D1` `DBD2` — paired with 0x07D0 (status: `unknown-not-absent-DO-NOT-WRITE-BLIND`)
- `0x0522` / `0x0523` `CHARGE_TARGET_MV` — battery voltage target (status: `confirmed-working`)
- `0x030E` / `0x030F` `SBS_CHARGING_VOLTAGE` — SBS charging voltage (status: `present-untested`)

These are drawn from `ec/annotations/registers.yaml`, and that file is the tree's authority on the meaning of "charge-limit registers."

## The finding: they are not found to move in this file

The file `evidence/ec-watch/2026-09-18-ac-plugin-sweep-summary.csv` is a 211-second recording of a 0x0000-0x07FF EC memory sweep during an AC plug-in event. Its header claimed "every row for the charge-limit registers," but inspection of the 205 rows in the file shows **none of the six addresses above have a row**.

The file's rows are distributed across six page blocks — 0x00, 0x03, 0x04, 0x05, 0x06, 0x07 — so the six addresses are not in an unscanned range:
- 0x030E and 0x030F fall in page 0x03, which has rows
- 0x0522 and 0x0523 fall in page 0x05, which has rows
- 0x07B9, 0x07D0, and 0x07D1 fall in page 0x07, which has rows

Yet all six are absent from the file. By contrast, other charge-path registers in the same pages are present:
- 0x0743 (page 0x07): 1 change, 0x02 → 0x03 (moved once)
- 0x07A6 (page 0x07): 3 changes, 0x29 → 0x29 (moved and returned)

The absence is consistent: within the charge-limit register set, not one was found to move during this window.

## What this means

Per the calibration rule in CLAUDE.md, a missing row is passive observation — "not found to move in this file" — never evidence that the EC does not act on the byte or that it is not written. The file is a record of what the watcher saw, not a test of the EC's hardware behavior.

The honest reading is that **this 211-second AC plug-in capture is silent on the charge-limit registers**: they either held steady without change, or they moved but the watcher's 0.4-second sample interval missed every transition. Both are consistent with the data. What the data does not support is any claim about the EC's permanent handling of these registers.

The CSV header has been corrected in place to reflect this: the clause "plus every row for the charge-limit registers" has been struck and replaced with explicit address names and the note that they are "not found to move in this file," matching the language `sweep-summary-schema.md` uses for any address with no row.

## No `status:` changes

Per CLAUDE.md's calibration rule and the standing rule in issue #1699, this is a record of what a passive watcher saw, not a readback. No entry in `ec/annotations/registers.yaml` changes its `status:` as a result.
