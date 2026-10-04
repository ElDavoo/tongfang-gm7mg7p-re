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
- **`acpi/`** — also the per-directory index for the interpreter excerpts
  fetched into it for issue #1337, each with its URL, revision, licence and
  retrieval date. See [`acpi/README.md`](acpi/README.md).
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
- **`ec-watch/2026-09-18-profile-switch-0700-07ff.csv`**,
  **`ec-watch/2026-09-18-profile-switch-0400-07ff.csv`**: the issue #4 run.
  Read-only Windows captures over the AC plug-in and all three Control Center
  battery modes, `0x0700-0x07FF` in the first and `0x0400-0x07FF` in the
  second, taken after the same cycle was repeated over the wider window. Each
  is one row per change, `ts,addr,old,new` from line 1. **Neither carries a
  `MARK` row**, so no row can be placed against a switch by the file: which
  row belongs to which of the three switches is read from the address and the
  ordering. Source for `docs/findings.md` §4g, including the
  `0x0436`/`0x0438` correction recorded there in place.
- **`ec-watch/2026-09-18-ac-plugin-sweep-summary.csv`**: a **derived**
  per-address summary, not a capture: `addr,change_count,first_old,last_new`,
  one row per address over `0x0000-0x07FF` sweeping at 0.4 s across the AC
  plug-in and the three mode switches on 2026-09-18. Its own `#` header is
  authoritative and carries three things worth reading before citing it — the
  32,499-row source log is **not committed**, the `change_count` column sums to
  a different figure and neither can be checked from this tree, and the columns
  carry no timestamp and no order, so an address with no row here is "not found
  to move in this file", never "never written". It holds no `MARK` row and
  could not: it is a per-address rollup of a log that is not here, so a mark
  could not be placed in it even had one been taken. Read by
  `ec/tools/grade_sweep_summary.py`; the schema and both blind spots are in
  `docs/findings/sweep-summary-schema.md`. Source for `docs/findings.md` §4g's
  `0x07B9`/`0x07D0`/`0x07D1` claim, which `ec/tools/check_capture_claims.py`
  holds to this file by its denial rule.
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
  next to this one. It is a console log rather than a capture in the grader's
  schema; `ec/tools/probe_log_to_capture.py` converts it, given an `--anchor`,
  and the conversion committed at
  `ec/tools/testdata/0751-isolation-probe-log/2026-01-01-0751-isolation-from-probe-log.csv`
  is the gradeable form — a transcription, with reconstructed timestamps and no
  control arm, as its own header says.
  `docs/findings/probe-log-capture-conversion.md` is what it does and does not
  establish.
- **`ec-watch/2026-09-24-06d6-reload-linux.csv`**,
  **`ec-watch/2026-09-24-06c2-06db-sweep-linux.csv`**,
  **`ec-watch/2026-09-24-06d9-hold-linux.csv`**: the issue #257 run. It is a
  read-only Linux capture of the `bank1:0x8001` counter sweep through the ECMG
  window (`ec/tools/ec_timer_capture.py`). The three files are `0x06D6` alone
  at 2 ms for 120 s; the 28 sweep bytes inside the host window at 10 ms for
  300 s; and `0x06D9` with the in-window state bytes of the `0x9817` routine
  at 0.5 ms for 60 s. AC connected, no vendor service, run from a local
  session on the laptop. Each file's `#` header carries its conditions and a
  `# baseline` line with the value of every watched byte. The data rows are
  one per change, as `ec_watch.py` writes them. **`ec-watch/2026-09-24-host-window-page-census.txt`**
  is the per-page count of non-`0xFF` bytes over the 64 KiB mapping
  (`ec_timer_capture.py --census`). Only `0x0000`-`0x07FF` and
  `0x0C00`-`0x0FFF` hold data. Source for the `XDATA_06D6` status,
  `docs/hardware-tests/xdata-06c2-06db-sweep.md`, and findings.md §17a. Graded
  with `ec/tools/grade_timer_sweep.py`.
  **`ec-watch/2026-09-24-06c2-06db-perturb-linux.csv`** is the same run's
  perturbation arm. It watches arm 2's 28 bytes, the `0x976E`/`0x9817` state
  bytes and `0x0751` at 10 ms while the owner unplugged and replugged AC,
  pressed the Fn power-mode key and closed and opened the lid. Its `MARK` rows
  were stamped by `--auto-mark` (AC and lid via sysfs, suspend via the
  boottime/monotonic gap; there was no suspend) and by
  `--mark-input /dev/input/event7`, so a mark is when Linux saw the action.
  Source for the `XDATA_06D8`/`XDATA_070B` statuses and that document's §4a.
  **`ec-watch/2026-09-24-06c2-06db-suspend-linux.csv`** watches the same 35
  bytes across a `systemctl suspend` to S3 (`mem_sleep=deep`) and a wake by the
  owner. A stdin `MARK` records the suspend command and `--auto-mark` the
  resume, with about 7.2 s in S3. The rows have a 12.3 s hole for the freeze,
  S3 and the thaw. Source for the `XDATA_06C5` status and that document's §4b.
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
  only rows that differ. Source for findings.md §14h.

## Mark provenance per capture

Whether a timing claim over a committed capture is **mechanical** or
**inferred** depends on one thing: whether the file carries `ts,MARK,,label`
rows to place a byte's move against. Where it does, the placement is
mechanical. Where it does not, the placement is an inference from the ordering
and the addresses — which is how
`docs/hardware-tests/gpu-tgp-07c4-07d7-door.md`'s CORRECTION block came to
retract "at the plug-in" for `0x07C4` in place. Nothing above said which
captures were in which class, and a reader could not tell.

**The count is the finding; a capture legitimately has none.** Every watcher
builds its `Marker` over a sink that is `None` without `--csv` and starts the
thread only under `--mark`, so a `MARK` row needs both flags; in
`ec/tools/ec_timer_capture.py` a mark comes from `--mark`, `--auto-mark` or
`--mark-input`. **No mark-free capture here records the flags it was taken
with** — the two that do record theirs say so in their own `#` headers — so
the last column says what the file is and that no mark was placed in it, and
stops there. The kinds below are kept distinct because merging them
would be a claim these files do not support. `.txt` files in `ec-watch/` are
outside this table by construction — it is over `*.csv` — and are reported as
out of scope by `ec/tools/check_capture_marks.py` rather than passed over in
silence.

| capture | `MARK` rows | why none, if none |
|---|---|---|
| `2026-09-18-ac-plugin-sweep-summary.csv` | 0 | Not a capture in this schema: a derived per-address summary (`addr,change_count,first_old,last_new`) rolled up from a 32,499-row log that is not committed. It carries no timestamp and no order, so no mark could be placed in it even had one been taken. |
| `2026-09-18-profile-switch-0400-07ff.csv` | 0 | A `ts,addr,old,new` change log with no mark in it: the writer places a `MARK` row only for a label typed at the keyboard, so a byte's move here cannot be placed against the mode switch by the file alone. |
| `2026-09-18-profile-switch-0700-07ff.csv` | 0 | The same, and the first of the two profile-switch cycles. |
| `2026-09-23-power-mode-cycle-0700-07ff.csv` | 0 | The same, over the `0x0700-0x07FF` half of the power-mode cycle. This is the file whose `0x07C4` rows `docs/hardware-tests/gpu-tgp-07c4-07d7-door.md` had to retract as "at the plug-in". |
| `2026-09-23-power-mode-cycle-0f00-0f5f.csv` | 0 | The same, over the `0x0F00-0x0F5F` fan-table half. |
| `2026-09-24-06c2-06db-perturb-linux.csv` | 6 | — |
| `2026-09-24-06c2-06db-suspend-linux.csv` | 2 | — |
| `2026-09-24-06c2-06db-sweep-linux.csv` | 0 | The same, and the two mark-bearing captures in this root are the arms of the same issue #257 run that used `--auto-mark` and `--mark-input`. |
| `2026-09-24-06d6-reload-linux.csv` | 0 | The same, the `0x06D6` arm of that run. |
| `2026-09-24-06d9-hold-linux.csv` | 0 | The same, the `0x06D9` arm. |

The counts come from `python3 ec/tools/measure_mark_provenance.py`, which
reports this class rather than dropping it, and
`python3 ec/tools/check_capture_marks.py` holds the table to the files. The
write-up is `docs/findings/capture-mark-provenance.md`. **This is not a claim
that any of these captures should have had marks, or that any was taken
without a mark flag** — it is a claim that a reader can now tell which of these
a timing claim may be made over mechanically. Re-taking any of them with a mark
flag needs the physical machine; see
`docs/hardware-tests/xdata-06c2-06db-sweep.md` for the arms specified to run.
