# Linux side

- **`nix/uniwill-laptop.nix`**, **`nix/power.nix`** — the NixOS packaging and
  system config used to build/load the out-of-tree driver on this machine
  (nixpkgs doesn't enable `CONFIG_X86_PLATFORM_DRIVERS_UNIWILL`) and apply a
  charge profile at boot. Config for a specific machine, included for
  reference/reproducibility, not meant to be reused verbatim elsewhere.
- **`battery-trace/`** — the sampling scripts used to produce
  `../evidence/battery-traces/*.csv`: polls `power_supply` sysfs plus
  `regmap` debugfs EC registers every 60s. This is what caught the
  "profile writes accepted, current doesn't actually stop" result in
  `../docs/findings.md` §4b — a `capacity`-only or single-snapshot check
  would have missed it.
  `battery-trace/limit-pair-test` is the 2026-09-17 paired
  `0x07B9`/`0x07D0` experiment (`../docs/findings.md` §4f); it writes
  through `../ec/tools/ecmem.py`, i.e. the physical `ECMG` window rather
  than the driver.
  `battery-trace/remain-capacity-probe` is the read-only 2026-09-23
  `0x0436`/`0x0437` question (`../docs/hardware-tests/remain-capacity-0436.md`):
  the same window, but it writes nothing and so has no restore arm. **It has
  not been run** — the pipeline has no machine — so `XDATA_0436_PAIR` is still
  a placeholder in `../ec/annotations/registers.yaml`.
- **`lightbar/`** — the narrowly targeted `048d:6005` raw-HID probe and
  offline tests. The 2026-09-17 live run produced red → off with no keyboard
  change; [notes and remaining driver work](lightbar/README.md). Static
  protocol control is confirmed, not complete `ite_8291_lb` integration.
- **`patches/`** — a small `uniwill-laptop` patch adding a module parameter
  to test the numeric charge-limit path instead of the charge-mode path.
  See `patches/README.md` for an important correction to its own commit
  comment.
