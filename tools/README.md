# Repository tools

One thing lives here, and it is the one command that runs this repository's
offline `unittest` suites:

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. There are twenty today, 551 tests in all — the count is
what the runner below prints, one line per suite — and each is a `unittest`
suite standing in for a tool's own behaviour. (539 before this branch merged
with main: issue #525 adds `test_citation_callers.py`, and main's #526 and
#531 add cases to `test_citation_frames.py`, `test_grade_0751_isolation.py`
and `test_ec_watch.py`.)

| suite | what it stands in for |
|---|---|
| `ec/tools/test_check_capture_claims.py` | `ec/tools/check_capture_claims.py`'s address-presence and row-count rules against the committed `evidence/ec-watch/*.csv` captures, and the line between what it checks and what it deliberately skips |
| `ec/tools/test_check_cluster_citations.py` | `ec/tools/check_cluster_citations.py`'s two rules against `ec/annotations/xdata-clusters.csv` — `main-ec-NNN`/`cluster_key`/`cluster_name` citations held to their membership, and a census row's hand-typed counts held to the CSV, pinned apart as well as together — and the line between what it checks and what it deliberately skips, so that a denial, singleton wording, a mention without a membership claim, a code address and a split written as a list are each skipped rather than checked and each rule that makes it conservative gets a case saying so, because a pointer-checker's failure mode is silence, plus that the tree's committed prose currently agrees with the committed census beside it |
| `ec/tools/test_check_site_census.py` | `ec/tools/check_site_census.py`'s vocabulary table, one case per row asserting the checker *rejects* that row's disagreement, plus the unsupported-claim, stale-citation, unjoined-pair and totals-drift clauses, `--check`'s exit code, and that the committed sweep, correspondence and census currently agree |
| `ec/tools/test_citation_callers.py` | `ec/tools/citation_callers.py`'s two predicates on the citing listing: all-`0xFF` detection including the `-`-pad spelling every 1-byte instruction uses, the `ret` that is a five-token line a fixed-width reader never sees, a two-byte instruction that is not a fill run, a listing with no instruction line at all asserted **not** fill, header lines that must not parse as code, and transfer-target extraction across all four forms — plus that `call_graph.parse_listing` and `citation_callers.transfers` agree token for token, so the two tools cannot drift on the listing grammar |
| `ec/tools/test_citation_frames.py` | `ec/tools/citation_frames.py`'s code/data frame test, on sentences taken from the committed annotations and truncated to the clause under test: the two that a whole-sentence rule gets backwards (`calls to 0x110A, 0x158E, …` is a code list, `the 0x07D0 sites` is a byte count), the `FILLER_BUDGET` limit stated as a rejection case, and the reason and population reporting |
| `ec/tools/test_grade_0751_isolation.py` | `ec/tools/grade_0751_isolation.py`, the §4 grader of the `0x0751` capture procedure, against the committed `testdata/` fixtures |
| `ec/tools/test_grade_gpu_door.py` | `ec/tools/grade_gpu_door.py`, the §5 grader of the `0x07D0` door capture: the ordering and its ms delta, both one-block shapes, a quiet capture, a byte that moved and came back, marks left unmerged, and the ten-column mapping |
| `ec/tools/test_grade_timer_sweep.py` | `ec/tools/grade_timer_sweep.py`, the grader of the `0x8001` counter-sweep capture: its before/after-return lists re-read from the firmware image, the `0x06D6` period and the 10x rate ratio on a constructed clean capture, a flat capture reported as held rather than absent, a second writer flagged, an unresolved step warned, and a suspend gap left out of the figures and counted mod 10 |
| `ec/tools/test_walk_branch_arms.py` | `ec/tools/walk_branch_arms.py`'s direction classification, bounds, refusals, and negative-result wording |
| `ec/tools/test_xdata_cluster_names.py` | `ec/tools/xdata_register_map.py`'s cluster identity: the `cluster_key` content hash, the `cluster_name` carry across a regeneration, `--map`, and the settling test that a cited cluster still resolves to the membership the prose describes |
| `windows/tools/test_manual_fan_ctrl_probe.py` | the fan-mode probe's two-arm byte script, its read-safety guard under `--level-block`, the mark rows its `--csv` capture lands, that capture read back through the real `ec/tools/grade_0751_isolation.py` reader, and `--block`: the seven runs the watch set decomposes into, that the block path reports exactly what the byte path does, that only the mode byte is left to a point read, and the 56/61 figures the banner and the self-test quote |
| `windows/tools/test_ec_watch.py` | the mark-CSV sweep and the mark landing between two change rows, that a blank press at the mark prompt records no row and takes no mark number while a padded label is still taken, plus `--block`: that it sweeps through `readmany`, that the flag is off by default, that the banner says the path is unverified, and that a range covering the fan-tach page is warned about rather than refused |
| `windows/tools/test_ecrw.py` | the real `ecrw.py`, on a fake `ctypes.WinDLL` standing in for kernel32: the `MMRD` IOCTL's little-endian physical address, the aligned-block decomposition of a range, the probe watch set's 56-IOCTL cost against the 52 a `206/4` suggests, the window's last in-window dword, an unaligned start's discarded lead, `dump --block` printing what the byte path prints, and the per-byte path's buffer byte for byte as it always was |
| `windows/tools/test_ec_validate.py` | the `ec_validate.py` `0x0436` capacity arm's exact-copy scoring, full-capacity bound, CSV, and `0x0400-0x045F` page assertion |
| `windows/tools/test_system_id_probe.py` | the `0x0456` probe's `store_scaled_quotient_0449` arithmetic, its branch labels, its address guard, and that it has no write path |
| `windows/tools/test_charge_target_test.py` | the charge-target tool's three refusals, the restore in its `finally`, and its CSV column set |
| `windows/tools/test_gpu_block_watch.py` | the GPU-block watcher's citation table against `evidence/acpi/dsdt.dsl` and `ec/annotations/registers.yaml`, the door procedure's own copy of that table against the tool, that copy's cross-reference column for the four census-covered rows against `ec/annotations/ec-07c4-07d5-sites.csv` and its `.md`, the door grader's third copy of the window bounds and DSDT names against the tool, its watch set, and its mark reaching the CSV |
| `windows/tools/test_ctgp_dben_probe.py` | the `0x07C4` `DBEN` probe's refusals, its two-arm byte script read back from a run that started with the value bit clear, the restore in its `finally`, its CSV column set, and the bit arithmetic pinned to `evidence/acpi/dsdt.dsl` and the `0x96AD`/`0x94C0`/`0x83FF` rows of `ec/annotations/ghidra-functions.csv` |
| `linux/lightbar/test_probe_6005.py` | the lightbar probe's ioctl encoding, dry run, and off-after-failure |

`windows/tools/ecrw_fake.py` is a shared fixture rather than a suite — it is
the offline stand-in for the `ecrw` module, installed by
`test_manual_fan_ctrl_probe.py`, `test_ec_watch.py`, `test_gpu_block_watch.py`
and `test_ctgp_dben_probe.py`, and the `test_*.py` pattern above does not pick
it up, so it costs no suite count. `windows/tools/test_ecrw.py` is the odd one
out and installs nothing: it puts a fake `ctypes.WinDLL` in front of the real
`ecrw.py`, because a suite that only ever exercises the fake is not testing
the file whose arithmetic #147 is about.

Named directories run alone, which is what to reach for when editing one tool:

```sh
bash tools/run-tests.sh windows/tools
```

The exit status is non-zero if any suite failed, and the runner's per-file
output lines each carry what that suite ran. It prints what ran; it does not
assert a count, because an expected count turns every added test into a
failure. A run that finds no suite at all is a failure too, not a silent pass —
the vacuous check is the same defect the gate's listing parse had in
`docs/findings.md` §14b.

## One interpreter per file, and why that is not a preference

The `windows/tools` suites used to install a fake `ecrw` into `sys.modules`
with `setdefault`, and the fakes were not the same shape: some exported `Ec`
only, others `Ec` and `EcError`, and `ec_watch.py` imports both. In one shared
interpreter, whichever suite imported first won, and a tool that imports a name
the winner lacks died with `ImportError: cannot import name 'EcError' from
'ecrw'`. It passed only by sort-order accident, which nothing asserted.
`docs/findings.md` §16 has the reproduction.

**Issue #186 reconciled the two fakes that existed when it was written:**
`windows/tools/ecrw_fake.py` carries `Ec` and `EcError` over the real module's
whole surface, and `test_manual_fan_ctrl_probe.py`, `test_ec_watch.py`,
(since its merge) `test_gpu_block_watch.py` and (also since its merge)
`test_ctgp_dben_probe.py` `install()` it (by assignment, not `setdefault`).
Three suites that landed in parallel with it — `test_ec_validate.py` (`Ec`
only), `test_system_id_probe.py` and `test_charge_target_test.py` (`Ec` and
their own `EcError`) — still install their own fakes with `setdefault`, so a
single discovery run over `windows/tools` is still order-dependent for them.
Moving those three onto `ecrw_fake.install()` is a follow-up; until then the
per-file loop is load-bearing, not only insurance.

## What it does not run

- **No gate, no workflow.** CI runs `.github/scripts/agent-gates.sh`, which is
  copied from [`ElDavoo/agent-pipeline`](../docs/agent-pipeline.md) and cannot
  be edited here. `docs/agent-pipeline.md` carries the one-line call for a human
  or an upstream change; until then these suites are not per-commit coverage.
  The runner prints that on every run, the way the cheap tier prints its own
  deferral.
- **No hardware, and no evidence of any.** Every suite is offline by
  construction: device discovery, file opening and ioctls are mocked against
  hand-built fixtures, and the `windows/tools` suites fake `ecrw` — and,
  for the charge-target tool, the `powershell` call behind its WMI line —
  precisely so no Windows box is needed. No EC is opened, no register is read
  back, and no HID node is touched. `linux/lightbar/README.md` and each suite's
  own docstring say the same thing where the tool is described.
- **Not the decompiler tooling.** Those tools' `--check` and `--self-test` runs
  are the gate's, and they are a different set of files; see
  `docs/agent-pipeline.md`.
