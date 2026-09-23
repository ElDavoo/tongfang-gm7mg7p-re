# Evidence

Raw data specific claims in `../docs/findings.md` cite directly, so they're
independently checkable rather than taken on faith:

- **`battery-traces/2026-09-09-profiles.csv`** — 60s-interval sysfs +
  regmap trace across full charge cycles under `Trickle` and `Long_Life`.
  Source for the current-taper table in findings.md §4b.
- **`battery-traces/2026-09-09-threshold80.csv`** — same, with
  `force_charge_limit=1` and `charge_control_end_threshold=80` set. Shows
  charging past 93% regardless (findings.md §4c).
- **`battery-traces/2026-09-17-limit-pair.csv`** — 10s-interval trace of
  the paired `0x07B9`/`0x07D0` write through the physical `ECMG` window
  (`ec/tools/ecmem.py`, `linux/battery-trace/limit-pair-test`): five
  value/order variants, all charged through. Source for findings.md §4f.
- **`screenshots/2021-11-27-batteryinfoview-windows.png`** — user-provided
  BatteryInfoView log from Windows on this exact machine, showing charging
  genuinely stop around 86% followed by a falling-voltage/zero-current
  climb to a reported 100% (gauge relaxation after a real stop — the
  opposite signature of what an uncapped charge looks like). The single
  piece of evidence that reopened the "0x07B9 is dead" conclusion.
- **`acpi/dsdt.dsl`** — full disassembled DSDT (`iasl`). Referenced for the
  `ECMG` operation-region field-list gap around `0x07B9` and the cycle-count
  gated capacity-rescaling logic in `_BIF`/`_BST`.
- **`hid/0003-048d-*.report_descriptor.bin`** — raw HID report descriptors
  for both on-board ITE 8291 devices, parseable for their usage
  page/usage (`0xFF12`/`0xFF03`) to confirm which is the keyboard and which
  is the lightbar.
- **`hid/2026-09-17-6005-6010-static.jsonl`** — live GM7MG7P raw-HID
  feature-request trace: the 6010 static-colour sequence applied to 6005,
  four 8-byte returns, with original `hid-generic` binding intact.
- **`hid/2026-09-17-6005-observation.md`** — the user's subsequent physical
  observation: default rainbow → red → dark, no keyboard change. Complements
  the machine trace, which ended before the visual report was received.
  Source for findings.md §3's 2026-09-17 static-control result; not evidence
  of complete kernel-driver or lifecycle support.
- **`uefi/2026-09-19-UniWillVariable.{bin,txt}`, `uefi/2026-09-19-variable-list.txt`**:
  the vendor's shared settings variable after a BIOS load-defaults, and
  every OS-visible UEFI variable. Source for findings.md §6.
- **`uefi/2026-09-23-UniWillVariable-{before,after}-memoc.bin`**,
  **`uefi/2026-09-23-MemoryOverClockSwitch-set.txt`**: the live write
  of `MemoryOverClockSwitch` (0x33) 0 → 1 with `windows/tools/uniwill_set.py`.
  The two dumps differ at that byte only.
- **`uefi/2026-09-23-memory-menu-observation.md`**: the owner's report
  that the BIOS setup's "Memory" (Memory Overclocking Menu) entry appeared
  after that write and a reboot. Source for findings.md §7's live result.
