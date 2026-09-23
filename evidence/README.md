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
- **`ec-watch/2026-09-23-power-mode-cycle-0700-07ff.csv`**,
  **`ec-watch/2026-09-23-power-mode-cycle-0f00-0f5f.csv`**: every EC byte
  change in those two windows (`windows/tools/ec_watch.py`, 0.2 s sweeps)
  across an AC plug-in, a battery-protection change and six Fn-key
  power-mode switches, Office → Gaming → Turbo twice (Control Center
  3.1.39.0). **`ec-watch/2026-09-23-power-mode-cycle-0f00-final.txt`** is the
  fan-table window read back after the last switch, the anchor
  `windows/tools/fan_table_replay.py` replays from.
  **`ec-watch/2026-09-23-power-mode-snapshot-dc.txt`** holds read-only reads
  taken on battery just before. **`mqtt-capture/2026-09-23-power-mode-cycle.pcapng`**
  (with its decoded `.jsonl`) is a passive loopback capture of the vendor
  broker over the same window. Source for findings.md §7 and
  `windows/vendor-ec-map.md` "Power modes".
- **`ec-watch/2026-09-23-0751-isolation.txt`**: the issue #99 run that wrote
  `0x0751` alone, one block per value `0xA0`/`0x00`/`0x10`, from Turbo, with
  Control Center 3.1.39.0 running and GCUService+GCUBridge up, watching
  `0x0783-0x0787`, `0x07C5`, `0x07C6`, `0x0743-0x0746` and the `0x0F00-0x0F5F`
  fan table. Nothing but `0x0751` itself moved. It could **not** answer
  whether the fan-mode bits scale fan behaviour, which is the half of the
  question `MANUAL_FAN_CTRL` is still `present-untested` for: the run was
  near-idle, and the file's own closing note records that `0x075B`/`0x075C`
  drifted as much under a no-op control write (`0x10` → `0x10`) as under a
  real mode change, which is why the run puts that drift on the die rather
  than on the byte. The PWM rows are not in the capture, only that note.
  Source for the live half of the `MANUAL_FAN_CTRL` note in
  `ec/annotations/registers.yaml`; the fixed-load re-run that would settle
  the rest is §3 of `docs/hardware-tests/manual-fan-ctrl-0751-isolation.md`,
  is not done, and needs the physical machine. That file's §6 names the
  re-run's captures `<YYYY-MM-DD>-0751-isolation-…`, and they go in this index
  next to this one.
- **`uefi/2026-09-19-UniWillVariable.{bin,txt}`, `uefi/2026-09-19-variable-list.txt`**:
  the vendor's shared settings variable after a BIOS load-defaults, and
  every OS-visible UEFI variable. Source for findings.md §6.
- **`uefi/2026-09-23-UniWillVariable-{before,after}-memoc.bin`**,
  **`uefi/2026-09-23-MemoryOverClockSwitch-set.txt`**: the live write
  of `MemoryOverClockSwitch` (0x33) 0 → 1 with `windows/tools/uniwill_set.py`.
  The two dumps differ at that byte only.
- **`uefi/2026-09-23-memory-menu-observation.md`**: the owner's report
  that the BIOS setup's "Memory" (Memory Overclocking Menu) entry appeared
  after that write and a reboot. Source for findings.md §8's live result.
- **`ec-reencode/2026-09-23-sdas8051-versions.md`**: the EC listing
  re-encode run with the `sdas8051` that `.github/actions/project-setup`
  installs (SDCC 4.2.0, `sdas8051 02.00`) against the committed
  `ec/ghidra/reassembly.csv` (nix SDCC 4.6.0, `sdas8051
  05.50.4+NoICE+SDCCmods-WIP-R14`): the environment, both tallies, the
  row-by-row diff, and the reproduce commands. The 143-instruction
  unencodable set is identical on both sides and 52 of 2,705 rows change
  outcome, all from `assembler-gap` to better.
  **`ec-reencode/2026-09-23-sdas8051-rowdiff.csv`** holds those 52 rows, the
  only rows that differ. Source for findings.md §14g.
