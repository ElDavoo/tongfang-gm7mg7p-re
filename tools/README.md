# Repository tools

One thing lives here, and it is the one command that runs this repository's
offline `unittest` suites:

```sh
bash tools/run-tests.sh
```

## What it runs

Every `test_*.py` under the repository, found by `find` — not a hardcoded list,
so a suite in a directory that does not exist yet is picked up by having its
file committed. There are thirty-two today, 974 tests in all — both figures
are what the runner below prints, one line per suite and a total on its last
line — and each is a `unittest` suite standing in for a tool's own behaviour.
Re-derive them by running it rather than by editing this sentence. None of the
thirty was red on the 2026-09-25 run recorded at `64dbde19`; two were,
and stay named here as history rather than as state, because a reader who
took them as current would go looking for a red runner that is gone:
`ec/tools/test_check_site_census.py` and `ec/tools/test_xdata_cluster_names.py`,
both because their subject was stale. A third was red until #751 landed the row
for `ec/tools/test_inc_dptr_sites.py`, and this tree holds that row and the one
for `ec/tools/test_disasm8051.py` that #688 added:
`tools/test_readme_suite_table.py` is this table's own check, and a missing row
is the one step a runner that finds suites by `find` cannot do for itself — a
table missing either of those two rows would fail it. The totals above count
tests *run*, failing suites included, which is what the runner counts — and
*run* is not *collected*: a class whose `setUpClass` raises contributes none of
its own cases, and the error is not itself counted as one, so the same
`ec/tools/test_xdata_cluster_names.py` ran 21 of its 28 while it was red in
`TheGuardOffRegeneration` and runs 28 now, where an ordinary failing case runs
and is counted like any other. The total moves with *how* a suite was red and
not only with whether it was, so a suite going green does not add a knowable
number of cases to the figure.

The totals are not a pass and never were: what says whether a tree is green is
the runner's last line and its exit status, not a number kept in a file. On
2026-09-25 at `64dbde19` that last line read `All 30 suite(s) passed, 882
tests` and the runner exited 0.
*(Merged-tree note, 2026-09-25: `2ed6f030` (#822) added
`docs/findings/xdata-cluster-names-guard-off-recipe.md`, and on that tree one
suite is red — `ec/tools/test_check_cluster_citations.py`, whose
committed-prose case rejects `:220` of that new file, where one fenced block
prints a guard-off regeneration beside the committed census and so names
clusters from two rankings at once, and its `joined ['0x0464', '0x0465']` line
cites two bytes the committed census puts in `main-ec-145`, which is not one of
the eleven ids the block names. On `2ed6f030` the counts were still thirty
suites and 882 tests and the last line read `30 suite(s) run, 882 tests; one or
more FAILED` with the runner exiting 1. It is #822's file rather than this
file's and it reproduces on a clean checkout of `origin/main`, so it is named
here rather than fixed here: the `64dbde19` sentence above is still
true of `64dbde19`, and this is the paragraph that stops it reading as true of
the tree it is now sitting in.)*
*(Second merged-tree note, 2026-09-25, issue #846 at `964279dc`: on **that**
tree the counts were re-derived from a `bash tools/run-tests.sh` as thirty-one
suites and 934 tests, the new one being `ec/tools/test_walk_budget_census.py`
at 52. The last line read `31 suite(s) run, 934 tests; one or more FAILED` with
the runner exiting 1, and **the same suite was the red one**:
`ec/tools/test_check_cluster_citations.py`, on the same `:220` of the same
#822 file. It is red on a clean `origin/main` too, checked by stashing that
work and running the suite alone, so nothing there caused it and nothing there
fixes it. The `64dbde19` sentence is left reading as the record of that commit
rather than rewritten with figures from a different one.)*
*(Third merged-tree note, 2026-09-25, #846 and #801 together: the counts above
are re-derived from a `bash tools/run-tests.sh` on this tree — **thirty-two
suites and 974 tests**, which is 882 plus the two suites each side added:
`ec/tools/test_walk_budget_census.py` at 52 and
`ec/tools/test_check_citation_lines.py` at 40. The last line reads `32 suite(s)
run, 974 tests; one or more FAILED` with the runner exiting 1, and **the red one
is still `ec/tools/test_check_cluster_citations.py` and still the same `:220` of
the same #822 file** — confirmed again here by running that suite alone against
a worktree of clean `origin/main`, where it fails identically, so neither side
of this merge caused it and neither fixes it. Both of the new suites are green,
and a third note is here for the reason the second one was: the reason a suite
goes red while the merge is adding green ones is the kind of thing a totals
paragraph is for. On #801's side it was this branch's own first draft of its
correction block in `docs/findings/reset-vector-dptr-targets.md`, which tripped
that suite a second way by naming one address and four cluster ids in a single
`>`-quoted paragraph — `check_cluster_citations.py` splits prose into sentences
but a blockquote's `>` markers sit between the terminator and the next word, so
a quoted paragraph arrives as one unit. The draft was rewritten rather than the
suite loosened.)*
`docs/findings/0751-grader-self-test-gate.md` records the red set as it stood
and the follow-up issues that owned it, and
[`tools-readme-totals.md`](../docs/findings/tools-readme-totals.md)
records the run these figures are read off. Nothing here sets out to have
fixed either suite.
`test_readme_suite_table.py` checks the *set* of rows below and deliberately
not these counts — its docstring gives the reason — so the paragraphs above
are the only thing holding them, which is exactly why they have to be
re-derived by running the runner rather than by arithmetic on a diff.

> **Corrected 2026-09-25, issue #816.** The paragraph under "The totals are
> not a pass" is left as it was written, and **both of the suites this file
> names as red are green** on the tree this lands on. The first paragraph
> already says so — #821 (`90ac6d2c`) re-cast the two as history rather than
> as state, and #846 and #801 re-derived the counts above it — so what is left
> for this block to add is the half none of those sentences carries: *which*
> suite is red now, and that it is not either of the two named here.
> `ec/tools/test_check_site_census.py` was cleared by #752, which re-pinned
> the four `census_refs` cells onto the lines the corrected `bank0/D091.c`
> has; `ec/tools/test_xdata_cluster_names.py` was cleared by #753, which
> replaced its copy-and-patch recipe with `--no-eq-guard`. **The runner
> nonetheless still exits 1, on a third suite**, and that is the measurement:
>
> ```console
> $ bash tools/run-tests.sh
> ...
> ec/tools/test_check_cluster_citations.py: FAILED
> 32 suite(s) run, 974 tests; one or more FAILED.
> $ echo $?
> 1
> ```
>
> Its one failure is a cluster-membership claim in
> `docs/findings/xdata-cluster-names-guard-off-recipe.md:220` — #822's write-up,
> not this repository's runner being broken. `docs/findings.md` §52 records it
> and names it to that file's owner;
> `docs/findings/runner-red-suite-set.md` tracks the set, one suite wide. So
> "the runner exits 1" above is still true and is now true of a different line.
>
> **The suite and test counts in the two paragraphs above are deliberately left
> as they are**, and this correction does not update them. They are `32` and
> `974` — the *Third merged-tree note* above re-derived them for #801, which
> added `ec/tools/test_check_citation_lines.py` — and they are exactly what the
> runner still prints, as the transcript above shows, so leaving them alone is
> a decision rather than a patch over a stale number. (This block was first
> written against the tree #821 measured, where the paragraphs above read `30`
> and `882`; #846's note superseded those above it at `31` and `934` and
> #801's superseded that, so the block is re-pointed
> rather than left contradicting the sentence it sits under. The count of
> *red* suites is unchanged by either, and this is not the place it is argued.)
> What no check in the tree can see them is still the reason not to touch them:
> `test_readme_suite_table.py` compares the row *set* and nothing else and
> `tools/run-tests.sh` prints its totals and asserts none, a decision
> `docs/findings/runner-red-suite-set.md` sets out at length. **Re-derive them**
> by running the runner, which is what the first paragraph above already
> requires, and which is the whole reason the red/green claim beside it had to
> be re-measured too. `tools/README.md` also has no reason to know anything
> about prose: nothing written in this block can turn a suite red or green. The
> write-up is
> [`docs/findings/xdata-no-eq-guard-measured-state-correction.md`](../docs/findings/xdata-no-eq-guard-measured-state-correction.md).

| suite | what it stands in for |
|---|---|
| `ec/tools/test_bank1_e582_framing.py` | The byte facts behind the issue #680 reading that the `bank1,0xE582` entry is reached through 0xE580 and the census row at 0x9F03 is a displacement byte: the push/lcall/pop save-restore pair across the 0xE57E cut, `converges_from` on both halves of each site, and the `80 02` at 0x9F02 read as a `sjmp` whose displacement's landing address is the committed `9F04.asm` first instruction — asserted against the image rather than by re-running the scan that wrote the census, so a regenerated table that disagreed would fail rather than pass on a stale pair, plus that both annotation comments still carry the clause their `CORRECTION` replaces, that no entry is seeded at 0xE580, and that the phantom census row is deliberately left in place |
| `ec/tools/test_check_capture_claims.py` | `ec/tools/check_capture_claims.py`'s address-presence and row-count rules against the committed `evidence/ec-watch/*.csv` captures, and the line between what it checks and what it deliberately skips |
| `ec/tools/test_check_citation_lines.py` | `ec/tools/check_citation_lines.py`'s three rules over the line numbers the prose repeats out of the generated CSVs — the `xdata-086x-dispatch.md` site table and the `HAND_CHECKED["0x0860"]` comment against `xdata-0860-census-sites.csv`, and every `xdata-registers.csv`/`xdata-clusters.csv` line pointer in the two files its `ROW_SCOPE` names, each held to the row for the **address or cluster id** rather than to a table of expected line numbers, because a rank is not an identity — one case per way a citation can be wrong, and the cases a loosened test would let through: a table whose header lost the column, reported as not located rather than passing vacuously; a `—` cell over a CSV row that does cite; the merged `0x25CE4`/`0x25CFC` row read as one row and two sites; the `:49` shorthand bound to the file it follows and a bare list bound to the file named ahead of it; a header line and a line past EOF diagnosed as such; a rule that located nothing reporting that rather than returning clean; the two supersession shapes **skipped**, with the skip counted and `--verbose` naming it, and a live paragraph that merely mentions a correction still checked; the deliberate asymmetry between the per-site and the union rule, pinned from both sides; and that the committed prose and the committed census currently agree |
| `ec/tools/test_check_cluster_citations.py` | `ec/tools/check_cluster_citations.py`'s two rules against `ec/annotations/xdata-clusters.csv` — `main-ec-NNN`/`cluster_key`/`cluster_name` citations held to their membership, and a census row's hand-typed counts held to the CSV, pinned apart as well as together — and the line between what it checks and what it deliberately skips, so that a denial, singleton wording, a mention without a membership claim, a code address and a split written as a list are each skipped rather than checked and each rule that makes it conservative gets a case saying so, because a pointer-checker's failure mode is silence, plus that the tree's committed prose currently agrees with the committed census beside it |
| `ec/tools/test_check_site_census.py` | `ec/tools/check_site_census.py`'s vocabulary table, one case per row asserting the checker *rejects* that row's disagreement, plus the unsupported-claim, stale-citation, unjoined-pair and totals-drift clauses, `--check`'s exit code, and that the committed sweep, correspondence and census currently agree |
| `ec/tools/test_check_testdata_index.py` | `ec/tools/check_testdata_index.py`'s two directions between `ec/tools/testdata/README.md` and the tree under it, each rule that makes it strict and each that makes it conservative getting a case: a directory no index names is a gap, a self-indexed one is not (on a directory name the tool has never seen, so the clause is structural and not an exemption list), the trailing slash that stops `0751-isolation-run/` passing on a sibling's row, the `...-suffix.csv` and `*-glob` shorthands resolved by glob rather than by splicing, and a token whose shape matches no rule landing in `unresolved` without failing the run — plus the rule that the run's three tallies are read out of what it printed and are not a floor on the tree's size, a rule of its own with a case per clause: a tree with more of them than today and one with fewer are both green, and an empty tree, a rowless index beside a tree that has one, and one token per row are each refused on the clause that refused them |
| `ec/tools/test_check_testdata_row_claims.py` | `ec/tools/check_testdata_row_claims.py`'s rule over the **third** column of `ec/tools/testdata/README.md` — an address a row attributes to its fixture has to occur in a file that row names, across the whole set the first column resolves to rather than per file, so `0x075B` living in one of `0751-isolation-run-staged/`'s three CSVs is a claim the row makes and not a miss — with each of the six shapes pinned as a case from both sides: the page-boundary range, the `capture`/`page` word, the two-token watched-set span, the denial in both its spellings, the `ecrw.py dump` argument, the firmware code address filtered against `ghidra-functions.csv` minus `xdata-registers.csv`, and another capture's address told from a backticked date by its spelling; and the four-hex-digit width and the backticked-only predicate besides — then all nine rules dropped in turn and each asserted to make the committed tree check *more*, against the run as shipped rather than against a figure, so no added fixture row breaks any of them |
| `ec/tools/test_citation_callers.py` | `ec/tools/citation_callers.py`'s two predicates on the citing listing: all-`0xFF` detection including the `-`-pad spelling every 1-byte instruction uses, the `ret` that is a five-token line a fixed-width reader never sees, a two-byte instruction that is not a fill run, a listing with no instruction line at all asserted **not** fill, header lines that must not parse as code, and transfer-target extraction across all four forms — plus that `call_graph.parse_listing` and `citation_callers.transfers` agree token for token, so the two tools cannot drift on the listing grammar |
| `ec/tools/test_citation_frames.py` | `ec/tools/citation_frames.py`'s code/data frame test, on sentences taken from the committed annotations and truncated to the clause under test: the two that a whole-sentence rule gets backwards (`calls to 0x110A, 0x158E, …` is a code list, `the 0x07D0 sites` is a byte count), the `FILLER_BUDGET` limit stated as a rejection case, and the reason and population reporting |
| `ec/tools/test_citation_gap_scan.py` | `ec/tools/citation_gap_scan.py`'s window arithmetic and three verdicts, on the real committed bytes: the listing end read from the byte column so a bare `ret` has a length, the next entry taken from the citing row's **own** scope, the zero-byte gap whose window is the neighbour's head, and the 3 bytes of slack that let a straddling `lcall` complete where a window stopping at the boundary decodes nothing — plus the overrun guard (~~`disasm8051.decode()` still raises, which is why the tool walks the committed tables itself~~ **Corrected 2026-09-25, issue #679** — `decode()` stops rather than raising at the end of its buffer now, and `walk()` stays because it reports a window holding less than was asked for through `truncated` and carries the per-instruction map-unassigned flag), the `not-code` byte criterion against the looser `db` form, the scope-dependent boundary, and `--check` rejecting a CRLF table whose rows parse equal |
| `ec/tools/test_disasm8051.py` | `ec/tools/disasm8051.py`'s bounds contract, on hand-built windows: the end-of-buffer check running before the index it guards, so a caller over-asking a one-byte `ret` window for four instructions gets that `ret` and a stop rather than an `IndexError`; `start == len(d)` and the empty buffer decoding to nothing; a `stop_at_flow` walk reaching the end; and the neighbouring, older guard it must not have been folded into — a 2-of-3-byte `lcall` yielding nothing, and the `ret` before it kept while the `lcall` that does not fit is not decoded |
| `ec/tools/test_export_ownership.py` | `ec/tools/export_ownership.py`'s containment rule — the smaller body's statements at least `THRESHOLD` of the way into the larger, classes as connected components, one owner per class as the largest body with a tie to the lowest address — pinned one case per named rule, each asserting the direction a loosened rule would get backwards, so a class cannot quietly merge two routines that share a `return` or split one exported 42 ways, plus the refusals that stop `--check` and `--self-test` from answering for a derivation nobody committed, and the `--map` round trip through a scratch path |
| `ec/tools/test_grade_0751_isolation.py` | `ec/tools/grade_0751_isolation.py`, the §4 grader of the `0x0751` capture procedure, against the committed `testdata/` fixtures |
| `ec/tools/test_grade_gpu_door.py` | `ec/tools/grade_gpu_door.py`, the §5 grader of the `0x07D0` door capture: the ordering and its ms delta, both one-block shapes, a quiet capture, a byte that moved and came back, marks left unmerged, and the ten-column mapping |
| `ec/tools/test_grade_timer_sweep.py` | `ec/tools/grade_timer_sweep.py`, the grader of the `0x8001` counter-sweep capture: its before/after-return lists re-read from the firmware image, the `0x06D6` period and the 10x rate ratio on a constructed clean capture, a flat capture reported as held rather than absent, a second writer flagged, an unresolved step warned, and a suspend gap left out of the figures and counted mod 10 |
| `ec/tools/test_group_functions.py` | `ec/tools/group_functions.py`'s block assignment, and at its centre the refusal that makes the tool safe: nothing in an `lcall`/`ljmp` operand names a bank, so `bank0->bank1` and `bank0->bank0` are the same three bytes, and the decisive case is a same-region call and a cross-region call that are byte-identical and differ only in which bank the target happens to exist in — a tool that merged across one anyway would answer with a smaller, tidier, wrong number and nothing in its own output would say so — plus the `group_basis` vocabulary (a seed from `type`/vector/module outranking a cluster, an off-list basis refused), the cross-bank group refusal, and the committed group files passing their own `--check` |
| `ec/tools/test_inc_dptr_sites.py` | `ec/tools/inc_dptr_sites.py`'s half-split of a pair accessor: the 107 addresses `xdata_register_map.py`'s pair pass reaches only as the `inc DPTR` half, their 73 / 34 cut and the 34's 7 entered / 27 not, the 73's own 71 with no `MOV DPTR` site in any image against 2 in the pd image only (a site in the pd image is another program's byte at the same address number, so it is not a second site), and §4.7's ten named addresses as the head of the 73 with `0x0364` as the eleventh §4.7 does not name — every figure re-derived by the tool's own `build()` against the committed firmware and the committed decompiled tree rather than read off `xdata-inc-dptr-only.csv`, so a CSV edited to match a stale claim fails rather than satisfying the suite, and the committed table held against a fresh generation as the one direction a hand-edited file can fail; the census's *shape* rather than its figures (`census_refs` closing on the bucket columns, the 73 `pair-literal`-only and main-EC-only); the ten confirmed by a second entry point beside the tool's own table, a byte scan of the image and a real `main()` run; `0x0420` as the counter-example keeping the rule off the spelling of a literal first argument, the same hex reaching `add_full_product_to_dptr` whose committed `.asm` is `mul AB / add A,DPL / addc A,DPH / ret` with no `movx` — so the address space is a property of the callee's body — beside the positive half, that every accessor the table names still dereferences XDATA; and the refusal that keeps a tool keyed to three committed CSVs harmless, from both sides: `open` replaced by a tripwire raising on any write mode for every mode, an unidentified pd marker refused rather than reported as a 73 / 0 that would read as a finding, and the module's own AST walked for a write vector no case runs |
| `ec/tools/test_walk_branch_arms.py` | `ec/tools/walk_branch_arms.py`'s direction classification, bounds, refusals, and negative-result wording |
| `ec/tools/test_walk_budget_census.py` | `ec/tools/walk_budget_census.py` and the `trace_xdata_refs.walk_why()` it reports on: one hand-built byte fixture per terminator guard, each asserting the guard that fired *and* the one that did not, so a loop that swapped two guards cannot pass; that `walk()` still returns a bare list of triples and `classify()` still re-derives every committed table's `access` cell; that the terminator vocabulary is closed, so a sixth way to stop is refused rather than rendered into a cell `--check` would go green on; that the class A/B verdict reports `undecided` rather than picking a side when the `--extend` budget is too small to reach the access in question, which the committed data never exercises; the census `--check`'s exit code on the committed CSV, on a doctored one, and its refusal of a budget that CSV does not record; and the re-cut's own load-bearing claim, as a count over the pinned pre-change commit `e198fd9`'s copy of each table -- no `access` cell and no `window` cell changed, with the one pre-existing `disasm8051.py` mnemonic drift at `xdata-0400-045f-sites.csv` `0x11F16` named rather than left to be noticed, which is what the fifteen-address `0x086x` sweep reproducing its table byte for byte is the regression test for. The ref is a SHA rather than `HEAD` or `origin/main` because both of those hold the re-cut once this lands, and a baseline that already contains the change compares each table with itself and pins nothing; an unreadable baseline fails the test instead of skipping it, for the same reason |
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
| `tools/test_agent_gates_patches.py` | the prepared `docs/ci/agent-gates-*.patch` set against the committed `.github/scripts/agent-gates.sh`, which is the file those patches exist not to edit: the set on disk against the set the suite names, both directions and by name; each patch alone; every ordered pair applied in sequence, so no landing order has to be written down anywhere; the full set landing and the result still parsing under `bash -n` and `shellcheck`, because a patch that applies and yields broken shell is still wrong; that the folded capture-claims patch still carries both `check_capture_claims` and `check_testdata_index`, so a later re-cut cannot drop half of it quietly; and that each header's `git apply` line names the file the reader is holding. A case holds the working-tree gate script byte-identical to the committed one, so a local edit under `.github/` cannot quietly change what every other case measures. Every mutation goes to a `tempfile` scratch tree and nothing writes to `.github/` |
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
