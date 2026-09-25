# Repository tools

One thing lives here, and it is the one command that runs this repository's
offline `unittest` suites:

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. There are twenty-five today, 679 tests in all — both figures
are what the runner below prints, one line per suite and a total on its last
line — and each is a `unittest` suite standing in for a tool's own behaviour.
Re-derive them by running it rather than by editing this sentence.

| suite | what it stands in for |
|---|---|
| `ec/tools/test_bank1_e582_framing.py` | The byte facts behind the issue #680 reading that the `bank1,0xE582` entry is reached through 0xE580 and the census row at 0x9F03 is a displacement byte: the push/lcall/pop save-restore pair across the 0xE57E cut, `converges_from` on both halves of each site, and the `80 02` at 0x9F02 read as a `sjmp` whose displacement's landing address is the committed `9F04.asm` first instruction — asserted against the image rather than by re-running the scan that wrote the census, so a regenerated table that disagreed would fail rather than pass on a stale pair, plus that both annotation comments still carry the clause their `CORRECTION` replaces, that no entry is seeded at 0xE580, and that the phantom census row is deliberately left in place |
| `ec/tools/test_check_capture_claims.py` | `ec/tools/check_capture_claims.py`'s address-presence and row-count rules against the committed `evidence/ec-watch/*.csv` captures, and the line between what it checks and what it deliberately skips |
| `ec/tools/test_check_cluster_citations.py` | `ec/tools/check_cluster_citations.py`'s two rules against `ec/annotations/xdata-clusters.csv` — `main-ec-NNN`/`cluster_key`/`cluster_name` citations held to their membership, and a census row's hand-typed counts held to the CSV, pinned apart as well as together — and the line between what it checks and what it deliberately skips, so that a denial, singleton wording, a mention without a membership claim, a code address and a split written as a list are each skipped rather than checked and each rule that makes it conservative gets a case saying so, because a pointer-checker's failure mode is silence, plus that the tree's committed prose currently agrees with the committed census beside it |
| `ec/tools/test_check_site_census.py` | `ec/tools/check_site_census.py`'s vocabulary table, one case per row asserting the checker *rejects* that row's disagreement, plus the unsupported-claim, stale-citation, unjoined-pair and totals-drift clauses, `--check`'s exit code, and that the committed sweep, correspondence and census currently agree |
| `ec/tools/test_citation_callers.py` | `ec/tools/citation_callers.py`'s two predicates on the citing listing: all-`0xFF` detection including the `-`-pad spelling every 1-byte instruction uses, the `ret` that is a five-token line a fixed-width reader never sees, a two-byte instruction that is not a fill run, a listing with no instruction line at all asserted **not** fill, header lines that must not parse as code, and transfer-target extraction across all four forms — plus that `call_graph.parse_listing` and `citation_callers.transfers` agree token for token, so the two tools cannot drift on the listing grammar |
| `ec/tools/test_citation_frames.py` | `ec/tools/citation_frames.py`'s code/data frame test, on sentences taken from the committed annotations and truncated to the clause under test: the two that a whole-sentence rule gets backwards (`calls to 0x110A, 0x158E, …` is a code list, `the 0x07D0 sites` is a byte count), the `FILLER_BUDGET` limit stated as a rejection case, and the reason and population reporting |
| `ec/tools/test_citation_gap_scan.py` | `ec/tools/citation_gap_scan.py`'s window arithmetic and three verdicts, on the real committed bytes: the listing end read from the byte column so a bare `ret` has a length, the next entry taken from the citing row's **own** scope, the zero-byte gap whose window is the neighbour's head, and the 3 bytes of slack that let a straddling `lcall` complete where a window stopping at the boundary decodes nothing — plus the overrun guard (`disasm8051.decode()` still raises, which is why the tool walks the committed tables itself), the `not-code` byte criterion against the looser `db` form, the scope-dependent boundary, and `--check` rejecting a CRLF table whose rows parse equal |
| `ec/tools/test_export_ownership.py` | `ec/tools/export_ownership.py`'s containment rule — the smaller body's statements at least `THRESHOLD` of the way into the larger, classes as connected components, one owner per class as the largest body with a tie to the lowest address — pinned one case per named rule, each asserting the direction a loosened rule would get backwards, so a class cannot quietly merge two routines that share a `return` or split one exported 42 ways, plus the refusals that stop `--check` and `--self-test` from answering for a derivation nobody committed, and the `--map` round trip through a scratch path |
| `ec/tools/test_grade_0751_isolation.py` | `ec/tools/grade_0751_isolation.py`, the §4 grader of the `0x0751` capture procedure, against the committed `testdata/` fixtures |
| `ec/tools/test_grade_gpu_door.py` | `ec/tools/grade_gpu_door.py`, the §5 grader of the `0x07D0` door capture: the ordering and its ms delta, both one-block shapes, a quiet capture, a byte that moved and came back, marks left unmerged, and the ten-column mapping |
| `ec/tools/test_grade_timer_sweep.py` | `ec/tools/grade_timer_sweep.py`, the grader of the `0x8001` counter-sweep capture: its before/after-return lists re-read from the firmware image, the `0x06D6` period and the 10x rate ratio on a constructed clean capture, a flat capture reported as held rather than absent, a second writer flagged, an unresolved step warned, and a suspend gap left out of the figures and counted mod 10 |
| `ec/tools/test_group_functions.py` | `ec/tools/group_functions.py`'s block assignment, and at its centre the refusal that makes the tool safe: nothing in an `lcall`/`ljmp` operand names a bank, so `bank0->bank1` and `bank0->bank0` are the same three bytes, and the decisive case is a same-region call and a cross-region call that are byte-identical and differ only in which bank the target happens to exist in — a tool that merged across one anyway would answer with a smaller, tidier, wrong number and nothing in its own output would say so — plus the `group_basis` vocabulary (a seed from `type`/vector/module outranking a cluster, an off-list basis refused), the cross-bank group refusal, and the committed group files passing their own `--check` |
| `ec/tools/test_walk_branch_arms.py` | `ec/tools/walk_branch_arms.py`'s direction classification, bounds, refusals, and negative-result wording |
| `ec/tools/test_xdata_cluster_names.py` | `ec/tools/xdata_register_map.py`'s cluster identity: the `cluster_key` content hash, the `cluster_name` carry across a regeneration, `--map`, and the settling test that a cited cluster still resolves to the membership the prose describes |
| `ec/tools/test_xdata_register_map.py` | the `--no-eq-guard` and `--export-ownership` refusals of the same tool: the three refused combinations per flag plus one per half of the scratch-output `or`, each with every mode entry point replaced by a recorder — all nine of them, read out of `main()`'s own AST by `dispatch_names` as every bare-name call in `main()` that is not another call's argument, with a mode dispatched through an attribute asserted against rather than collected, so a tenth fails here rather than going unmocked — so a guard that moved below the dispatch fails the test instead of writing a census the committed CSVs do not match over them, and the two accepted runs, which write only into their `tempfile` |
| `windows/tools/test_manual_fan_ctrl_probe.py` | the fan-mode probe's two-arm byte script, its read-safety guard under `--level-block` and `--watch-page`, the three mark rows its `--csv` capture lands, that capture read back through the real `ec/tools/grade_0751_isolation.py` reader and then through its block walk as a whole grader run — one block, `intact`, three roles, every window printed, exit 0 — the mark set against the grader's own §6 forms, a crashed run's `#` row, `--watch-page`: that the flag is opt-in, that it is §3's three ranges rather than 448 addresses of the tool's own choosing, that it substitutes for `WATCH` instead of adding to it, that it writes nothing but `0x0751`, and that its capture still grades and keeps its ungraded rows on the grader's `other addresses that moved` line — and `--block`: the seven runs the watch set decomposes into, the page arm's three whole runs, that the block path reports exactly what the byte path does, that only the mode byte is left to a point read, and the 56/61 and 112/117 figures the banner and the self-test quote |
| `windows/tools/test_ec_watch.py` | the mark-CSV sweep and the mark landing between two change rows, that a blank press at the mark prompt records no row and takes no mark number while a padded label is still taken, plus `--block`: that it sweeps through `readmany`, that the flag is off by default, that the banner says the path is unverified, and that a range covering the fan-tach page is warned about rather than refused |
| `windows/tools/test_ecrw.py` | the real `ecrw.py`, on a fake `ctypes.WinDLL` standing in for kernel32: the `MMRD` IOCTL's little-endian physical address, the aligned-block decomposition of a range, the probe watch set's 56-IOCTL cost against the 52 a `206/4` suggests, the `--watch-page` set's 112 IOCTLs and its 448 bytes with no padding, all four watch sets cleared of the fan-tach page, the window's last in-window dword, an unaligned start's discarded lead, `dump --block` printing what the byte path prints, and the per-byte path's buffer byte for byte as it always was |
| `windows/tools/test_ec_validate.py` | the `ec_validate.py` `0x0436` capacity arm's exact-copy scoring, full-capacity bound, CSV, and `0x0400-0x045F` page assertion |
| `windows/tools/test_system_id_probe.py` | the `0x0456` probe's `store_scaled_quotient_0449` arithmetic, its branch labels, its address guard, and that it has no write path |
| `windows/tools/test_charge_target_test.py` | the charge-target tool's three refusals, the restore in its `finally`, and its CSV column set |
| `windows/tools/test_gpu_block_watch.py` | the GPU-block watcher's citation table against `evidence/acpi/dsdt.dsl` and `ec/annotations/registers.yaml`, the door procedure's own copy of that table against the tool, that copy's cross-reference column for the four census-covered rows against `ec/annotations/ec-07c4-07d5-sites.csv` and its `.md`, the door grader's third copy of the window bounds and DSDT names against the tool, its watch set, and its mark reaching the CSV |
| `windows/tools/test_ctgp_dben_probe.py` | the `0x07C4` `DBEN` probe's refusals, its two-arm byte script read back from a run that started with the value bit clear, the restore in its `finally`, its CSV column set, and the bit arithmetic pinned to `evidence/acpi/dsdt.dsl` and the `0x96AD`/`0x94C0`/`0x83FF` rows of `ec/annotations/ghidra-functions.csv` |
| `linux/lightbar/test_probe_6005.py` | the lightbar probe's ioctl encoding, dry run, and off-after-failure |
| `tools/test_readme_suite_table.py` | this table's own first column against what `find` discovers, both directions and by name: a discovered suite with no row and a row for a suite that is gone are different mistakes, and the half that broke is the one a missing row took. The *set* and nothing else — the descriptions are prose, and comparing counts would turn every added test into a failure. It is a discovered suite itself, so the invariant covers the file that checks it |

Committing a `test_*.py` is the whole of what it takes to be run. A row is
the one step the runner cannot do for it, because the second column is prose
— what the suite stands in for — and the runner has no reason to know any of
it. The row stays hand-written, and
[`tools/test_readme_suite_table.py`](test_readme_suite_table.py) is what
makes skipping it fail, by name, on a full run.

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
assert a count, the per-suite one or the total, because an expected count turns
every added test into a failure. That is the whole reason the two numbers
above are read off a run rather than kept by hand. A run that finds no suite
at all is a failure too, not a silent pass — the vacuous check is the same
defect the gate's listing parse had in `docs/findings.md` §14b.

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
